#!/usr/bin/env python3
# Ağır işçiler (28 Ekim, mimari plan C / K4): iki hesap yükleme kilidi (aktarici/agir-kilit.py), Pocket tembel açılış + tek model + boşta kapanma + zaman aşımında
# yaşatma ve artan bekleme (aktarici/pocket-ses.py), Whisper cevap zaman aşımında yaşatma/artan bekleme (aktarici/whisper-hat.py `_isci_cevap`,
# `_isci_zaman_asimi`, `_isci_geri_cekil`), gömme modelinin kilidi (gomme-isci.py `_kilit`). Sahte işçilerle — gerçek model yüklenmez, ses çalınmaz, ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/agir-isci.py      (kaldı → çıkış 1)
import ast, json, os, queue, re, subprocess, sys, tempfile, threading, time, types
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-agir-"); KD = os.path.join(T, "kilit"); os.environ["SUFLOR_AGIR_KILIT"] = KD
KILIT_PY = os.path.join(KOD, "aktarici", "agir-kilit.py")

# ---- 1. yükleme kilidi -------------------------------------------------------------------------------------------------------------------
kn = {"__file__": KILIT_PY}; exec(compile(open(KILIT_PY, encoding="utf-8").read(), KILIT_PY, "exec"), kn)
def tut(sn, ad="whisper"):  # başka süreç kilidi tutar (öteki hesap yerine)
    p = subprocess.Popen([sys.executable, "-B", "-c", f"import sys,time\nns={{'__file__':{KILIT_PY!r}}}\nexec(compile(open({KILIT_PY!r}).read(),'k','exec'),ns)\n"
                          f"fd=ns['agir_kilit_al']({ad!r},5,print)\nprint('TUTULDU',flush=True)\ntime.sleep({sn})\nns['agir_kilit_birak'](fd)"],
                         stdout=subprocess.PIPE, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    p.stdout.readline(); return p  # TUTULDU gelene dek
g = []
h = tut(2.0); t = time.time(); fd = kn["agir_kilit_al"]("pocket", 10, g.append); gec = time.time() - t; h.wait()
bak(f"kilit: tutan varken bekler ({gec:.1f} sn), sırası gelince alır, günlükte 'bekleniyor' + 'sırası geldi'", fd is not None and 1.0 < gec < 4 and any("bekleniyor" in x for x in g) and any("sırası geldi" in x for x in g))
b = json.load(open(os.path.join(KD, "yukleme.lock"))); kn["agir_kilit_birak"](fd)
bak("kilit dosyasına hesap/pid/model yazılır", b.get("pid") == os.getpid() and b.get("model") == "pocket" and b.get("hesap"))
bak("kilit dizini ve dosyası iki hesabın da yazabileceği izinde (0777 / 0666)", (os.stat(KD).st_mode & 0o777, os.stat(os.path.join(KD, "yukleme.lock")).st_mode & 0o777) == (0o777, 0o666))
g = []; h = tut(4.0); t = time.time(); fd = kn["agir_kilit_al"]("pocket", 1, g.append); gec = time.time() - t
bak(f"bekleme tavanı: dolunca kilitsiz sürer ({gec:.1f} sn), günlükte neden", fd is None and 0.8 < gec < 2.5 and any("kilitsiz" in x for x in g))
g = []; eski = kn["AGIR_KILIT_BAYAT_SN"]; kn["AGIR_KILIT_BAYAT_SN"] = -1; t = time.time(); fd = kn["agir_kilit_al"]("pocket", 10, g.append); gec = time.time() - t; kn["AGIR_KILIT_BAYAT_SN"] = eski
bak(f"bayat kilit (tutan 10 dk'dan uzun yüklüyor) beklenmeden atılır ({gec:.2f} sn)", fd is None and gec < 0.8 and any("bayat" in x for x in g))
h.terminate(); h.wait()
open(os.path.join(KD, "yukleme.lock"), "w").write(json.dumps({"hesap": "x", "pid": 99999999, "model": "whisper", "t": time.time() - 5000}))  # sahibi ölmüş, bilgi eski
t = time.time(); fd = kn["agir_kilit_al"]("gomme", 10, g.append); gec = time.time() - t
bak(f"sahibi ölmüş kilit (süreç yok) beklemeden alınır ({gec:.2f} sn)", fd is not None and gec < 0.8 and json.load(open(os.path.join(KD, "yukleme.lock")))["model"] == "gomme"); kn["agir_kilit_birak"](fd)
with kn["agir_kilit"]("w", 5, print) as fd: ic = fd is not None
bak("bağlam yöneticisi alır ve bırakır (hemen yeniden alınabilir)", ic and (lambda f: (kn["agir_kilit_birak"](f), f is not None)[1])(kn["agir_kilit_al"]("w", 1, print)))
gs = ast.get_source_segment(open(os.path.join(KOD, "gomme-isci.py"), encoding="utf-8").read(), next(f for f in ast.parse(open(os.path.join(KOD, "gomme-isci.py"), encoding="utf-8").read()).body if getattr(f, "name", "") == "_kilit"))
gn = {"os": os, "__file__": os.path.join(KOD, "gomme-isci.py")}; exec(gs, gn); gk = gn["_kilit"]()
bak("gömme işçisi kilidi aktarici/agir-kilit.py'den yükler", callable(gk))

# ---- 2. Pocket (sahte işçi) ---------------------------------------------------------------------------------------------------------------
SAHTE = os.path.join(T, "uyg"); os.makedirs(SAHTE)
open(os.path.join(SAHTE, "pocket-isci.py"), "w").write('''import sys, os, json, time, wave
gecici, onyukle = sys.argv[1], sys.argv[2]; os.makedirs(gecici, exist_ok=True)
open(os.environ["FAKE_ONY"], "a").write(onyukle + "\\n")
time.sleep(0.3); print(json.dumps({"hazir": True, "sn": 0.3, "sr": 24000, "modeller": []}), flush=True)
for satir in sys.stdin:
    g = json.loads(satir); kim = g["id"]
    if "yavas" in g["metin"]: time.sleep(1.6)
    yol = os.path.join(gecici, kim + "-0.wav")
    with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\\x00\\x00" * 2400)
    print(json.dumps({"id": kim, "parca": 0, "wav": yol, "sure": 0.1, "ilk": 0.01}), flush=True); print(json.dumps({"id": kim, "bitti": True, "n": 1, "sn": 0.1}), flush=True)
''')
AYAR = {"ses_motoru": "pocket", "pocket_python": sys.executable, "pocket_hf": T, "uygulama": T, "pocket_bos_dk": 10}
TOP = {"var": False, "ses": ("pocket", "wite:male_1")}; TOPLANTI = {"aktif": None}
ns = {"AYAR": AYAR, "ARAYUZ_DILI": "tr", "A": types.SimpleNamespace(port=bos_port(8792)), "_UYG": SAHTE, "_APP": T, "__file__": os.path.join(KOD, "relay.py"), "BASE": T, "deneme_aktarici": lambda: True,
      "_ilk": lambda *y: next((x for x in y if os.path.exists(x)), y[-1]), "os": os, "re": re, "json": json, "time": time, "threading": threading, "subprocess": subprocess,
      "kisilikler": lambda: [{"yerel_ses": "pocket:wite:female_2", "yerel_ses_en": "pocket:en:mary"}, {"yerel_ses": "pocket:alperiox:female_2", "yerel_ses_en": "pocket:en:michael"}],
      "ton_bul": lambda m: None, "toplanti_var": lambda: TOP["var"], "toplanti_ses_motoru": lambda: TOP["ses"], "TOPLANTI": TOPLANTI}
os.environ["SUFLOR_TEST_PIPER_SESSIZ"] = "1"; os.environ["FAKE_ONY"] = os.path.join(T, "onyukle.log")
for b_ in ("piper-ses.py", "pocket-ses.py"): exec(compile(open(os.path.join(KOD, "aktarici", b_), encoding="utf-8").read(), b_, "exec"), ns)
P = ns["POCKET"]; ONY = os.path.join(T, "onyukle.log")
def bekle(kos, sn=8):
    son = time.time() + sn
    while not kos() and time.time() < son: time.sleep(0.05)
    return kos()
def oku(m="normal", **k): top = []; r = ns["pocket_oku"](m, topla=top, **k); return r
ns["POCKET_CEVAP_SN"] = 0.5
bak("aktarıcı açılırken işçi açılmaz (tembel açılış)", P["p"] is None and P["durum"] == "kapali" and not os.path.exists(ONY))
bak("onyukle: istenen ses tek; yoksa kişiliklerin ilk Türkçe sesi, İngilizce hiç", (ns["pocket_onyukle"]("wite:male_1"), ns["pocket_onyukle"](), ns["pocket_onyukle"]("pocket:en:michael")) == (["wite:male_1"], ["wite:female_2"], ["en:michael"]))
t = time.time(); r = oku("merhaba", ses="wite:male_1"); gec = time.time() - t
bak(f"ilk okuma beklemez: işçi hazır değil → False hemen ({gec:.2f} sn), açılış arka planda başladı", r is False and gec < 0.5 and P["durum"] in ("yukleniyor", "hazir"))
bak("işçi arka planda hazır olur", bekle(lambda: P["durum"] == "hazir"))
bak("yalnız istenen ses yüklenir (önceden yükleme listesi tek öğe)", open(ONY).read().split() == ["wite:male_1"])
bak("hazır işçiyle okuma başarılı", oku("merhaba", ses="wite:male_1") is True and P["yavas"] is False)
pid1 = P["p"].pid
# zaman aşımında yaşat
r1 = oku("yavas bir", ses="wite:male_1")
bak("zaman aşımı: okuma False, işçi ÖLDÜRÜLMEDİ, durum yavaş/yanıt vermiyor", r1 is False and P["p"] and P["p"].poll() is None and P["yavas"] and str(P["hata"]).startswith("yanıt vermiyor") and ns["pocket_view"]()["yavas"] is True)
bak("geç gelen parça silinir, bekleyen isteğe bağlanmaz", bekle(lambda: not [f for f in os.listdir(ns["POCKET_GECICI"]) if f.endswith(".wav")] and not P["iptal"], 4))
bak("zaman aşımından sonra normal cevap yavaş durumunu kaldırır", oku("tamam", ses="wite:male_1") is True and not P["yavas"] and P["hata"] is None and P["zs"] == 0)
oku("yavas iki", ses="wite:male_1"); oku("yavas uc", ses="wite:male_1"); P["zs"] = 2; t0 = time.time()
oku("yavas dort", ses="wite:male_1")
bak("art arda 3 zaman aşımında işçi yeniden başlatılmak üzere kapatılır, bekleme 15 sn", P["p"] is None and P["durum"] == "hata" and 10 < P["sonraki_t"] - time.time() <= 15.5 and P["yk"] == 1)
t = time.time(); r = oku("normal", ses="wite:male_1")
bak("bekleme sürerken okuma hemen False döner, yeni işçi açılmaz", r is False and time.time() - t < 0.5 and P["p"] is None)
P["sonraki_t"] = 0; oku("normal", ses="wite:male_1"); bekle(lambda: P["durum"] == "hazir")
bak("bekleme dolunca işçi yeniden açılır", P["durum"] == "hazir" and P["p"].pid != pid1)
P["zs"] = 2; oku("yavas bes", ses="wite:male_1")
bak("ikinci art arda yeniden başlatmada bekleme katlanır (başarılı okuma yok → 30 sn)", P["p"] is None and 25 < P["sonraki_t"] - time.time() <= 30.5 and P["yk"] == 2)
P["sonraki_t"] = 0; oku("normal", ses="wite:male_1"); bekle(lambda: P["durum"] == "hazir"); oku("normal", ses="wite:male_1")
bak("başarılı okuma bekleme çizelgesini sıfırlar", P["yk"] == 0)
# işçi dışarıdan ölürse
P["p"].kill(); bekle(lambda: P["p"] is None)
bak("işçi beklenmedik ölürse durum hata ve yeniden başlatma bekler (zorlanmaz)", P["durum"] == "hata" and P["sonraki_t"] > time.time() and oku("normal", ses="wite:male_1") is False and P["p"] is None)
P["sonraki_t"] = 0; P["yk"] = 0
# boşta kapanma
oku("normal", ses="wite:male_1"); bekle(lambda: P["durum"] == "hazir"); pr = P["p"]
AYAR["pocket_bos_dk"] = 10; P["son"] = time.time(); ns["pocket_izle_bir"]()
bak("boşta kapanma: süre dolmadan kapanmaz", P["durum"] == "hazir")
AYAR["pocket_bos_dk"] = 0.01; P["son"] = time.time() - 5; ns["pocket_izle_bir"]()
bak("boşta kapanma: süre dolunca işçi kapanır, bellek bırakılır", P["durum"] == "kapali" and P["p"] is None and bekle(lambda: pr.poll() is not None, 6))
oku("normal", ses="wite:male_1"); bak("kapandıktan sonra okuma işçiyi yeniden açar", bekle(lambda: P["durum"] == "hazir"))
AYAR["pocket_bos_dk"] = 0; P["son"] = time.time() - 99999; ns["pocket_izle_bir"]()
bak("pocket_bos_dk = 0 → hiç kapanmaz", P["durum"] == "hazir")
# toplantı: motor Pocket ise toplantı başlayınca önceden, boşta kapanma toplantı bitince de çalışır
AYAR["pocket_bos_dk"] = 0.01; ns["pocket_kapat"]("test"); P["on_toplanti"] = None
TOP["var"] = True; TOPLANTI["aktif"] = {"dosya": "t1.md"}; ns["pocket_izle_bir"]()
bak("toplantı başlayınca motor Pocket ise işçi önceden açılır (okuma beklemeden)", bekle(lambda: P["durum"] == "hazir"))
P["son"] = time.time() - 5; ns["pocket_izle_bir"]()
bak("toplantıda Pocket konuşmacıyken boşta kapanmaz", P["durum"] == "hazir")
TOP["var"] = False; TOPLANTI["aktif"] = None; ns["pocket_izle_bir"]()
bak("toplantı bitince boşta kapanma çalışır", P["durum"] == "kapali" and P["on_toplanti"] is None)
TOP["var"] = True; TOPLANTI["aktif"] = {"dosya": "t2.md"}; TOP["ses"] = ("gemini", "Kore"); ns["pocket_izle_bir"](); time.sleep(0.3)
bak("toplantıda motor Gemini ise Pocket önceden açılmaz", P["durum"] == "kapali")
TOP["var"] = False; TOPLANTI["aktif"] = None
# iki hesap kilidi Pocket yüklemesinde
AYAR["pocket_bos_dk"] = 10; h = tut(2.0, "whisper"); t = time.time(); oku("normal", ses="wite:male_1")
bak("öteki hesap yüklerken Pocket açılışı kilidi bekler (okuma yine beklemez)", time.time() - t < 0.5 and P["durum"] == "yukleniyor")
bak("kilit bırakılınca Pocket yüklenir", bekle(lambda: P["durum"] == "hazir", 8) and time.time() - t > 1.5); h.wait()
ns["pocket_kapat"]("test sonu")

# ---- 3. Whisper: cevap zaman aşımı ---------------------------------------------------------------------------------------------------------
wsrc = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read(); wt = ast.parse(wsrc); parcalar = []
for n in wt.body:
    ad = getattr(n, "name", None); hd = [t.id for t in getattr(n, "targets", []) if isinstance(t, ast.Name)]
    if ad in ("_isci_geri_cekil", "_isci_zaman_asimi", "_isci_cevap") or "_ISCI" in hd or "WH_CEVAP_SN" in hd or "WH_ZA_N" in hd or "WH_GERI_CEKIL_MAX" in hd: parcalar.append(ast.get_source_segment(wsrc, n))
KAPAT = []
class Pr:
    def __init__(s, canli=True): s.canli = canli
    def poll(s): return None if s.canli else 1
wn = {"time": time, "queue": queue, "json": json, "threading": threading, "STATE": {"whisper": {"yavas": False, "hata": None}}, "_isci_kapat": lambda neden: (KAPAT.append(neden), wn["_ISCI"].update(p=None, satirlar=None))}
exec("\n".join(parcalar), wn); I = wn["_ISCI"]; W = wn["STATE"]["whisper"]; wn["WH_CEVAP_SN"] = 0.4
I["satirlar"] = queue.Queue(); I["satirlar"].put(json.dumps({"id": "eski", "text": "geç"})); I["satirlar"].put(json.dumps({"id": "n1", "text": "doğru"}))
bak("cevap: önceki isteğin geç gelen cevabı atlanır, kendi cevabı döner", wn["_isci_cevap"]("n1").get("text") == "doğru")
t = time.time(); j = wn["_isci_cevap"]("n2", 0.3)
bak(f"cevap: zaman aşımı → zaman_asimi işareti ({time.time() - t:.1f} sn)", j.get("zaman_asimi") is True)
I["satirlar"].put(None); bak("cevap: işçi kapandı → hata", wn["_isci_cevap"]("n3").get("hata") == "işçi kapandı")
I.update(p=Pr(True), satirlar=queue.Queue()); wn["_isci_zaman_asimi"]({"kanal": "karsi"}); wn["_isci_zaman_asimi"]({"kanal": "karsi"})
bak("Whisper: 1–2 zaman aşımı işçiyi öldürmez, durum yavaş/yanıt vermiyor", not KAPAT and W["yavas"] and W["hata"].startswith("yanıt vermiyor (2/3)") and I["zs"] == 2)
wn["_isci_zaman_asimi"]({"kanal": "karsi"})
bak("Whisper: art arda 3. zaman aşımında yeniden başlatılır, bekleme 15 sn", KAPAT == ["art arda 3 zaman aşımı"] and 10 < I["sonraki"] - time.time() <= 15.5 and I["yk"] == 1)
I.update(p=Pr(True)); bek = []
for n in range(5): wn["_isci_geri_cekil"](f"d{n}"); bek.append(round(I["sonraki"] - time.time()))
bak(f"Whisper: art arda yeniden başlatmalarda bekleme katlanır ve 300 sn'de durur ({bek})", bek == [30, 60, 120, 240, 300])
I.update(p=Pr(False), yk=0, zs=0); KAPAT.clear(); wn["_isci_zaman_asimi"]({"kanal": "ben"})
bak("Whisper: işçi gerçekten ölmüşse zaman aşımında hemen yeniden başlatma yoluna girer", KAPAT == ["işçi kapanmış"])
I["yk"] = 0; wn["_isci_geri_cekil"]("hata", ilk_hemen=True)
bak("Whisper: işçinin bildirdiği ilk hatada bekleme yok (eski davranış), ikincisinde var", I["sonraki"] - time.time() < 0.5 and (wn["_isci_geri_cekil"]("hata", ilk_hemen=True), I["sonraki"] - time.time() > 10)[1])

import shutil; shutil.rmtree(T, ignore_errors=True)
print("agir-isci:", "GEÇTİ" if not HATA else f"KALDI ({len(HATA)})")
sys.exit(1 if HATA else 0)
