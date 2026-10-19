#!/usr/bin/env python3
# Pocket TTS ile yerel Türkçe ses (aktarici/pocket-ses.py + pocket-isci.py, S93): ses adı çözümü, alperiox için rakam → yazı, duygu eşlemesi (yalnız wite),
# gerçek işçiyle iki modelde okuma (ilk ses, parça), okuma kesilince kalan parçalar çalınmaz, bilinmeyen ses → False (çağıran Piper/Mac'e düşer), kişilik
# başına ses seçimi (S92 + S93: Gemini toplantıya, kişiliğin yerel_ses'i Pocket). Ses çalınmaz (SUFLOR_TEST_PIPER_SESSIZ). Yollar kodda değil: ayardaki
# pocket_python / pocket_hf ya da SUFLOR_POCKET_PYTHON / SUFLOR_POCKET_HF; yoksa gerçek işçi kısmı atlanır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/pocket.py      (kaldı → çıkış 1)
import json, os, re, subprocess, sys, tempfile, threading, time, types
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT = bos_port(8791)
os.environ["SUFLOR_TEST_PIPER_SESSIZ"] = "1"
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try: AY = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
except (OSError, ValueError): AY = {}
PY = os.environ.get("SUFLOR_POCKET_PYTHON") or AY.get("pocket_python"); HF = os.environ.get("SUFLOR_POCKET_HF") or AY.get("pocket_hf")
GERCEK = bool(PY and HF and os.path.exists(os.path.expanduser(PY)) and os.path.isdir(os.path.expanduser(HF)))
HATA = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-pocket-")
AYAR = {"ses_motoru": "piper", "pocket_python": PY or "/yok/python", "pocket_hf": HF or "/yok", "uygulama": T}
TON = {"ad": None}
ns = {"AYAR": AYAR, "ARAYUZ_DILI": "tr", "A": types.SimpleNamespace(port=PORT), "_UYG": KOD, "_APP": T, "__file__": os.path.join(KOD, "relay.py"), "BASE": T, "deneme_aktarici": lambda: True,
      "_ilk": lambda *y: next((x for x in y if os.path.exists(x)), y[-1]), "os": os, "re": re, "json": json, "time": time, "threading": threading, "subprocess": subprocess,
      "kisilikler": lambda: [{"yerel_ses": "pocket:alperiox:female_2", "ses": "gemini:Kore"}, {"yerel_ses": "pocket:wite:male_1", "ses": "gemini:Charon"}],
      "ton_bul": lambda m: TON["ad"]}
for b in ("piper-ses.py", "pocket-ses.py"): exec(compile(open(os.path.join(KOD, "aktarici", b), encoding="utf-8").read(), b, "exec"), ns)
ad = ns["pocket_ses_adi"]
bak("ses adı: pocket:alperiox:female_2 / wite / boş ses / bilinmeyen model",
    (ad("pocket:alperiox:female_2"), ad("wite:male_1"), ad("pocket:wite"), ad("pocket:yok:x"), ad("")) == ("alperiox:female_2", "wite:male_1", "wite:female_2", None, None))
bak("önceden yüklenecek sesler: iki kişiliğin yerel sesi", ns["pocket_kisilik_sesleri"]() == ["alperiox:female_2", "wite:male_1"])
pm = ns["pocket_metin"]
for g, s, b in [("Bütçe 1.250.000 liraya çıktı.", "alperiox:female_2", "Bütçe bir milyon iki yüz elli bin liraya çıktı."),
                ("Teslim 24 Ekim'de, saat 14:30'da.", "alperiox:female_2", "Teslim yirmi dört Ekim'de, saat on dört otuzda."),
                ("Oran 3,5 arttı, %12 oldu.", "alperiox:female_2", "Oran üç virgül beş arttı, yüzde on iki oldu."),
                ("Bütçe 1.250.000 liraya çıktı.", "wite:male_1", "Bütçe 1.250.000 liraya çıktı.")]:
    v = pm(g, s)
    if v != b: bak(f"metin {g!r} ({s}) → {v!r} (beklenen {b!r})", False)
bak("alperiox: rakam yazıya (wite kendisi okur)", not [h for h in HATA if h.startswith("metin")])
du = ns["pocket_duygu"]
TON["ad"] = "kotu_haber"; d1 = du("Maalesef iptal oldu."); TON["ad"] = None
bak("duygu: Claude tonu → üzgün, ünlem → mutlu, hayret → şaşkın, düz → yok",
    (d1, du("Harika haber, kabul ettiler!"), du("Gerçekten mi? Bütçe iki katı mı?"), du("Toplantı yarın.")) == ("üzgün", "mutlu", "şaşkın", None))
# kişilik başına ses seçimi: brifing-ses.py'deki kisilik_sesi taklit ortamda
src = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
ks = re.search(r"^def kisilik_sesi\(.*?(?=^def )", src, re.S | re.M).group(0)
K = {"k": None, "izin": False, "pocket": True, "piper": True}
kn = {"AYAR": AYAR, "ARAYUZ_DILI": "tr", "kisilik": lambda: K["k"], "gemini_izinli": lambda t=False: K["izin"] or t, "gemini_acik": lambda: False,
      "piper_acik": lambda: AYAR.get("ses_motoru") == "piper", "pocket_var": lambda: K["pocket"], "pocket_ses_adi": ad, "pocket_varsayilan": ns["pocket_varsayilan"], "ses_secimi": lambda: None}
exec(ks, kn); sec = lambda **a: kn["kisilik_sesi"](**a)[:2]
KIS = {"ses": "gemini:Kore", "yerel_ses": "pocket:alperiox:female_2"}; AYAR.update(piper_python="/x/python", piper_model="/x/model.onnx")  # yalnız seçim (dosyaya bakılmaz)
K["k"] = KIS; a1 = sec(); a2 = sec(toplantiya=True)
K["pocket"] = False; a3 = sec(); K["pocket"] = True
AYAR["ses_motoru"] = "mac"; a4 = sec(); AYAR["ses_motoru"] = "piper"
K["k"] = None; AYAR.update(ses_motoru="pocket", pocket_ses="wite:male_1"); a5 = sec(); AYAR.update(ses_motoru="piper"); AYAR.pop("pocket_ses")
K["k"] = {"ses": "gemini:Charon"}; a6 = sec()
AYAR.pop("piper_python"); AYAR.pop("piper_model")
bak("kişilik sesi: toplantı dışı → Pocket, toplantıya → Gemini, Pocket yoksa → Mac (Piper değil), Ses 'Mac' → Mac, ayar pocket → pocket_ses, yerel_ses yok → Piper",
    (a1, a2, a3, a4, a5, a6) == (("pocket", "alperiox:female_2"), ("gemini", "Kore"), ("mac", None), ("mac", None), ("pocket", "wite:male_1"), ("piper", None)))
# "hı hı" (tepki_cal): Piper ayarında da kişiliğin yerel sesi Pocket ise onay Pocket'la; Gemini/Mac dalları eskisi gibi
import ast; tc = ast.get_source_segment(src, next(f for f in ast.parse(src).body if isinstance(f, ast.FunctionDef) and f.name == "tepki_cal"))
OKU = []
tn = {"AYAR": {"konusma": True}, "os": os, "threading": threading, "GEMINI_ONAY": ("Hı hı.",), "piper_acik": lambda: True, "pocket_oku": lambda m, **a: OKU.append((m, a.get("ses"))),
      "KM": [("pocket", "wite:male_1", 1.0)], "tepki_sec": lambda t: None}
tn["kisilik_sesi"] = lambda: tn["KM"][0]
exec(tc, tn); os.environ.pop("SUFLOR_TEST_BASLAT", None)
r1 = tn["tepki_cal"]("alindi"); time.sleep(0.2); r2 = tn["tepki_cal"]("bekleme")
tn["KM"][0] = ("piper", None, 1.0); r3 = tn["tepki_cal"]("alindi")
bak("hı hı: Piper ayarında Pocket kişiliği onayı Pocket'la okur; bekleme ve Piper kişiliğinde klip yok", (r1, r2, r3, OKU) == (True, False, False, [("Hı hı.", "wite:male_1")]))
if not GERCEK: print("pocket: gerçek işçi kısmı atlandı (pocket_python / pocket_hf yok)")
else:
    try:
        t = time.time(); ok = ns["pocket_oku"]("Merhaba, toplantı başladı. Bütçe 1.250.000 lira.", ses="alperiox:female_2")
        bak(f"ilk okuma işçiyi açar (iki model önceden) ve biter ({time.time() - t:.1f} sn)", ok is True and ns["POCKET"]["durum"] == "hazir")
        t = time.time(); ok = ns["pocket_oku"]("Harika haber, müşteri teklifi kabul etti!", ses="wite:male_1")
        bak(f"ikinci okuma (wite, mutlu) ilk ses {ns['POCKET'].get('ilk', 9):.3f} sn ≤ 0,15 sn", ok is True and ns["POCKET"].get("ilk", 9) <= 0.15)
        rss = int(subprocess.run(["ps", "-o", "rss=", "-p", str(ns["POCKET"]["p"].pid)], capture_output=True, text=True).stdout.strip() or 0) / 1024
        bak(f"işçi belleği {rss:.0f} MB ≤ 2.000 MB (iki model)", 0 < rss <= 2000)
        n = {"i": 0}
        def iptal(): n["i"] += 1; return n["i"] > 2
        uzun = " ".join(["Bu uzun bir cümle, okuma yarıda kesilince kalan parçalar çalınmamalı."] * 6)
        t = time.time(); ok = ns["pocket_oku"](uzun, ses="alperiox:female_2", iptal=iptal)
        bak(f"okuma kesilince döner ({time.time() - t:.2f} sn)", ok is True and time.time() - t < 3)
        time.sleep(1.5)
        kalan = [f for f in os.listdir(ns["POCKET_GECICI"]) if f.endswith(".wav")] if os.path.isdir(ns["POCKET_GECICI"]) else []
        bak(f"kesilen okumanın parçaları silindi (kalan {len(kalan)})", not kalan)
        bak("bilinmeyen ses örneği → False (Piper/Mac'e düşer), işçi açık kalır",
            ns["pocket_oku"]("Deneme.", ses="alperiox:yok_ses") is False and ns["POCKET"]["p"].poll() is None)
        AYAR["pocket_hf"] = "/yok"; ns["POCKET"]["p"].terminate(); time.sleep(0.5); ns["POCKET"].update(p=None, durum="kapali", hata=None)
        bak("model klasörü yoksa False (Mac sesine düşülür)", ns["pocket_oku"]("Deneme.") is False and ns["POCKET"]["durum"] == "yok")
    finally:
        p = ns["POCKET"].get("p")
        if p and p.poll() is None: p.terminate()
print("pocket:", "GEÇTİ" if not HATA else f"KALDI ({len(HATA)})")
sys.exit(1 if HATA else 0)
