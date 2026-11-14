#!/usr/bin/env python3
# Ses düzeyinde parça başı yankı tanıma (aktarici/whisper-hat.py YANKI-TANIMA bloğu + yt_parca): ben parçası Whisper'a gitmeden aynı aralıktaki karşı sesle
# tutarlılık (200–4000 Hz) ve kayma ölçülür; ≥ 0,5 yankı, < 0,1 yankısız, arası "ara" (sözcük düzeyi süzgeç). Yapay sinyallerle: gecikmeli + oda süzgeçli
# karşı ses = yankı; bağımsız ses = kullanıcı; karışım = çift konuşma; karşı sessiz; tampon eksik / hesap hatası → None (eski metin yolu). Ardından,
# bu Mac'te varsa 13 Kasım 02.27 gerçek hoparlör kaydının 12 ben parçası çevrimdışı oynatılır ve ölçüm raporundaki kararla kıyaslanır (ses depoya girmez;
# kayıt yoksa o bölüm atlanır; başka kayıt için YT_KAYIT=<ses arşivi klasörü>).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yanki-tanima.py      (kaldı → çıkış 1; numpy yoksa whisper-venv Python'uyla kendini yeniden açar)
import ast, collections, glob, json, math, os, re, subprocess, sys, tempfile, threading, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try: import numpy as np
except ImportError:
    py = "/Users/Shared/Suflor/whisper-venv/bin/python"
    if os.path.exists(py) and not os.environ.get("YT_ICERDE"): os.environ["YT_ICERDE"] = "1"; os.execv(py, [py, "-B", __file__])
    print("yanki-tanima: numpy yok, atlandı"); sys.exit(0)
ns = {"re": re, "math": math, "collections": collections, "threading": threading}
agac = ast.parse(open(os.path.join(KOD, "aktarici", "sozluk.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name in ("_nc", "sade")], []), "sozluk", "exec"), ns)
kod = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
exec(kod.split("# YANKI-TANIMA-BASLA", 1)[1].split("# YANKI-TANIMA-BITIS", 1)[0], ns)
SR = ns["YT_SR"]; KT, tani = ns["KarsiTampon"], ns["yt_tani"]
hata = []
def bak(ad, k, ek=""): print(("✓ " if k else "✗ ") + ad + (f"  [{ek}]" if ek and not k else (f"  ({ek})" if ek else ""))); hata.append(ad) if not k else None
bak("varsayılan eşikler: üst 0,5, alt 0,1, kayma ±400 ms", (ns["YT_UST"], ns["YT_ALT"], ns["YT_KAYMA_MS"]) == (0.5, 0.1, 400))

# --- yapay sinyaller ---------------------------------------------------------------------------------------------------
rng = np.random.default_rng(7)
def konusma(sn, seviye_db=-26):  # konuşmaya benzer: renkli gürültü × hece zarfı (3–5 Hz) × arada sessizlik
    n = int(sn * SR); x = np.convolve(rng.normal(size=n + 64), np.hanning(5), "same")[:n]
    t = np.arange(n) / SR; zarf = np.abs(np.sin(2 * np.pi * 3.7 * t + rng.uniform(0, 6))) ** 1.5 * (np.sin(2 * np.pi * 0.4 * t + rng.uniform(0, 6)) > -0.6)
    x = x * zarf; return (x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 10 ** (seviye_db / 20)).astype(np.float32)
def oda(x, gecikme_ms, kazanc_db=-19, sonum_ms=40):  # hoparlör → oda → mikrofon: gecikme, sönümlü yansıma, hafif doğrusalsızlık
    L = int(sonum_ms / 1000 * SR); ir = rng.normal(size=L) * np.exp(-np.arange(L) / (L / 4)); ir[0] += 3; ir /= np.sqrt(np.sum(ir ** 2))
    y = np.convolve(x, ir)[:len(x)]; d = int(gecikme_ms / 1000 * SR)
    y = np.roll(y, d); y[:d] = 0 if d > 0 else y[:d]
    if d < 0: y[d:] = 0
    y = np.tanh(y * 3) / 3; return (y * 10 ** (kazanc_db / 20)).astype(np.float32)
def pcm(x): return (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
def tampon_kur(x, T0, paket_sn=0.5, eksik=(), titresim_ms=0):  # karşı sesi aktarıcıya geldiği gibi: duvar saatli paketler (damga titreşimiyle)
    tb = KT(); p = int(paket_sn * SR)
    for i, a in enumerate(range(0, len(x), p)):
        if i not in eksik: tb.ekle(T0 + a / SR + rng.uniform(-titresim_ms, titresim_ms) / 1000, pcm(x[a:a + p]))
    return tb
T0 = 1_800_000_000.0; SURE = 20.0
karsi = konusma(SURE); gurultu = (rng.normal(size=len(karsi)) * 10 ** (-72 / 20)).astype(np.float32)
def parca(mik, a, b): return pcm(mik[int(a * SR):int(b * SR)]), T0 + a, T0 + b
def dene(ad, mik, a, b, bek, tb=None, **k):
    r = tani(*parca(mik, a, b), tb or tampon_kur(karsi, T0), np, **k)
    bolge = r and r["bolge"]; bak(f"{ad} → {bek}", bolge == bek, f"tutarlılık {r.get('tutarlilik')}, kayma {r.get('kayma_ms')} ms" if r else "karar yok"); return r

yanki80 = oda(karsi, 80) + gurultu
r = dene("yalnız yankı (80 ms, −19 dB, oda + doğrusalsızlık), 3 sn", yanki80, 5, 8, "yanki")
bak("kayma 80 ms bulunur (±3 ms)", r and abs(r["kayma_ms"] - 80) <= 3, r and r["kayma_ms"])
for g in (250, -100):
    r = dene(f"yalnız yankı, kayma {g:+d} ms", oda(karsi, g) + gurultu, 5, 8, "yanki")
    bak(f"kayma {g:+d} ms bulunur (±3 ms)", r and abs(r["kayma_ms"] - g) <= 3, r and r["kayma_ms"])
# kısa (< 1 sn) yankı ara bölgeye düşer (raporun yöntemi: 0,25 sn dolgu kısa parçada tutarlılığı düşürür; gerçek kayıtta 0,84 sn yankı 0,31) — zararsız:
# Whisper + sözcük süzgeci. Dolgusuz hesap eşikleri değiştirir (çift konuşma da yükselir), ölçümsüz değiştirilmedi.
dene("kısa yankı parçası (0,8 sn) ara bölgede (yankısız değil)", yanki80, 10.1, 10.9, "ara")
kul = konusma(SURE, -26)
dene("yalnız kullanıcı, karşı konuşuyor (yankı yok, kulaklık)", kul + gurultu, 5, 8, "yankisiz")
dene("yalnız kullanıcı, kısa (0,8 sn)", kul + gurultu, 12.2, 13.0, "yankisiz")
yanki_db = 10 * np.log10(np.mean(yanki80[5 * SR:8 * SR] ** 2))
cift = yanki80 + kul / np.sqrt(np.mean(kul[5 * SR:8 * SR] ** 2)) * 10 ** ((yanki_db + 6) / 20)
r = dene("çift konuşma (kullanıcı yankıdan +6 dB)", cift.astype(np.float32), 5, 8, "ara")
bak("çift konuşmada tutarlılık 0,1–0,5", r and 0.1 <= r["tutarlilik"] < 0.5, r and r["tutarlilik"])
sessiz_karsi = (rng.normal(size=len(karsi)) * 10 ** (-70 / 20)).astype(np.float32)
r = dene("karşı sessiz (−70 dBFS), kullanıcı konuşuyor", kul + gurultu, 5, 8, "yankisiz", tb=tampon_kur(sessiz_karsi, T0))
bak("karşı sessizde tutarlılık hesaplanmaz (neden karsi_sessiz)", r and r.get("neden") == "karsi_sessiz" and "tutarlilik" not in r)
dene("1 sn'lik paketlerle de yankı", yanki80, 5, 8, "yanki", tb=tampon_kur(karsi, T0, 1.0))
r = dene("paket damgaları ±60 ms titrerken de yankı (tampon bitişik dizer)", yanki80, 5, 8, "yanki", tb=tampon_kur(karsi, T0, 0.5, titresim_ms=60))
bak("titreşimde tutarlılık titreşimsizle aynı (±0,02)", r and abs(r["tutarlilik"] - tani(*parca(yanki80, 5, 8), tampon_kur(karsi, T0), np)["tutarlilik"]) <= 0.02, r and r["tutarlilik"])
# geri düşüş: karar yok → None (aktarıcı parçayı işaretsiz Whisper'a verir, metin süzgeci eskisi gibi)
bak("tampon boş → None", tani(*parca(yanki80, 5, 8), KT(), np) is None)
bak("tampon yok → None", tani(*parca(yanki80, 5, 8), None, np) is None)
bak("karşı paketlerinin yarısı gelmemiş → None", tani(*parca(yanki80, 5, 8), tampon_kur(karsi, T0, eksik=set(range(0, 40, 2))), np) is None)
bak("parça karşı tamponundan eski (30 sn dışı) → None", tani(*parca(yanki80, 1, 3), tampon_kur(np.concatenate([karsi, karsi, karsi]), T0), np) is None)
# yt_parca: hesap hata verirse None ve günlüğe bir satır
yp = {"AYAR": {}, "STATE": {"whisper": {"yanki_tanima": {}}}, "_YT": {"sg": None, "baglasim": None, "n_yanki": 0, "kayma": None, "hata_t": 0.0}, "time": time, "KARSI_TAMPON": tampon_kur(karsi, T0), "YT_KAYMA_MS": 400}
yp.update({k: ns[k] for k in ("yt_tani", "YT_UST", "YT_ALT")})
for ad in ("_yt_sayi", "yt_parca"): exec(re.search(r"^def " + ad + r"\(.*?(?=^\S)", kod, re.M | re.S).group(0), yp)
class Bozuk:
    def __getattr__(self, a): raise RuntimeError("bozuk numpy")
yp["_yt_np"] = lambda: Bozuk(); is_ = dict(zip(("pcm", "t0", "t1"), parca(yanki80, 5, 8)))
bak("yt_parca: hesap hata verirse None (eski yol)", yp["yt_parca"](is_) is None)
yp["_yt_np"] = lambda: None; bak("yt_parca: numpy yoksa None", yp["yt_parca"](is_) is None)
yp["_yt_np"] = lambda: np; r = yp["yt_parca"](is_)
bak("yt_parca: çalışınca yankı, kayma ve bağlaşım tahmini saklanır", r and r["bolge"] == "yanki" and yp["_YT"]["kayma"] is not None and yp["_YT"]["baglasim"] is not None, r)
yp["AYAR"]["yanki_tanima_ust"] = 0.99; bak("yt_parca: üst eşik ayardan (0,99 → ara)", yp["yt_parca"](is_)["bolge"] == "ara")
# §7(e) ayarları varsayılan kapalı; açılınca ara bölgede çalışır
yb = ns["yt_bolge"]
bak("kısa parça eşiği varsayılan kapalı (0,8 sn, 0,31 → ara)", yb(0.31, 0.8, None) == "ara" and yb(0.31, 0.8, None, kisa_ust=0.3) == "yanki" and yb(0.31, 1.5, None, kisa_ust=0.3) == "ara")
bak("fazla enerji denetimi varsayılan kapalı (+1 dB → ara); açılınca ±5 dB yankı, +8 dB ara", yb(0.3, 2, 1.0) == "ara" and yb(0.3, 2, 1.0, enerji_db=5) == "yanki" and yb(0.3, 2, 8.0, enerji_db=5) == "ara")
# süre
tb = tampon_kur(karsi, T0); t = time.time()
for i in range(20): tani(*parca(yanki80, 5, 8 + (i % 3)), tb, np)
ms = (time.time() - t) / 20 * 1000; bak("parça başı hesap < 100 ms (3–5 sn parça)", ms < 100, f"{ms:.1f} ms")

# --- ara bölge sözcük süzgeci -------------------------------------------------------------------------------------------
cik, sd = ns["yt_sozcuk_cikar"], ns["sade"]
K = lambda t: [x for x in (re.sub(r"\W+", "", sd(w)) for w in t.split()) if x]
bak("ara: yankı öbeği çıkar, kullanıcının sözü kalır", cik("Bütçeyi gelecek hafta netleştireceğiz tamam ben bakarım", K("Bütçeyi gelecek hafta netleştireceğiz, teklif cuma gelir.")) == "tamam ben bakarım")
bak("ara: tamamı yankıysa '' (yankı sayılır)", cik("Merhabalar herkese.", K("Teşekkür ederim. Merhabalar herkese.")) == "")
bak("ara: tek ortak sözcük çıkmaz (kendi cevabı)", cik("Evet sözleşmeyi ben gönderirim", K("Sözleşmeyi siz mi göndereceksiniz?")) == "Evet sözleşmeyi ben gönderirim")
bak("ara: karşı metni yoksa metin olduğu gibi", cik("Tamam bakarım", []) == "Tamam bakarım")
bak("ara: kalan yalnız kısa sözcükse '' (ve, de)", cik("ve teklif cuma gelir", K("teklif cuma gelir")) == "")

# --- aktarıcı akışı (whisper-hat.py "Yankı ayıklama" bölümü, sahte çevreyle): bölgeye göre metin süzgeci, bekletme, atma, geri düşüş ----------------
import queue
yaz = []; olay = []
ak = {"re": re, "time": time, "threading": threading, "queue": queue, "os": os, "math": math, "collections": collections, "sade": ns["sade"], "_ORT": "/yok",
      "STATE": {"whisper": {"yanki": 0, "kanallar": {"karsi": time.time(), "ben": time.time()}, "kuyruk": 0}}, "AYAR": {}, "KANALLAR": {}, "WH_Q": queue.Queue(), "WH_AKIS_SN": 20,
      "kisilikler": lambda: [], "_log": lambda *a: None, "ses_arsivi_yaz": lambda *a: None, "beta_olay": olay.append,
      "_whisper_yaz": lambda is_, metin, ses=None, model=None: yaz.append((is_["id"], metin))}
ak.update({k: v for k, v in ns.items() if k.startswith(("yt_", "YT_", "Karsi"))})
exec(kod.split("# --- Yankı ayıklama ---", 1)[1].split("\n", 1)[1].split("\ndef _whisper_yaz(", 1)[0], ak)
def ben_is(id_, t0, t1, bolge=None, neden=None):
    d = {"id": id_, "kanal": "ben", "t0": t0, "t1": t1}; d.update({"yt_bolge": bolge} if bolge else {}); d.update({"yt": {"bolge": bolge, "neden": neden}} if neden else {}); return d
ak["YANKI_KARSI"].append((10.0, 13.0, ak["_yk"]("Bütçeyi gelecek hafta netleştireceğiz, teklif cuma gelir."), K("Bütçeyi gelecek hafta netleştireceğiz, teklif cuma gelir.")))
wy = ak["whisper_yaz"]; ECHO = "Bütçeyi gelecek hafta netleştireceğiz teklif cuma gelir"
bak("akış: bölgesiz (geri düşüş) yankı metni eskisi gibi atılır", wy(ben_is("a", 10.1, 13.0), ECHO) == "yanki")
bak("akış: karşı sessizken (yankısız) aynı metin atılmaz, bekletilmez", wy(ben_is("b", 10.1, 13.0, "yankisiz", "karsi_sessiz"), ECHO) == "satir" and yaz[-1] == ("b", ECHO))
# 14 Kasım: tutarlılık düşük ama karşı konuşuyorsa (ör. web'de Chrome AEC artığı) eski metin süzgeci güvence olarak çalışır
bak("akış: tutarlılıkla yankısız ama karşı konuşurken metin süzgeci yine çalışır", wy(ben_is("b2", 10.1, 13.0, "yankisiz"), ECHO) == "yanki")
bak("akış: ara bölgede yankı sözcükleri çıkar, kullanıcının sözü yazılır", wy(ben_is("c", 10.1, 13.0, "ara"), "Bütçeyi gelecek hafta netleştireceğiz tamam ben bakarım") == "satir" and yaz[-1] == ("c", "tamam ben bakarım"), yaz[-1])
bak("akış: ara bölgede tamamı yankıysa atılır (yankı sayılır)", wy(ben_is("d", 10.1, 13.0, "ara"), ECHO) == "yanki")
ak["KANALLAR"]["karsi"] = type("K", (), {"konusuyor": True, "t0": 20.0})()
r1 = wy(ben_is("e", 20.2, 23.0, "ara"), "Teklif cuma gelir mi bilmiyorum ama ben bakarım")
ak["KANALLAR"]["karsi"].konusuyor = False
ak["YANKI_KARSI"].append((20.0, 23.0, ak["_yk"]("teklif cuma gelir mi"), K("teklif cuma gelir mi")))
ak["_yanki_bosalt"](zorla=True)
bak("akış: ara bölge karşı satırı beklenirken bekletilir, gelince yalnız yankı sözcükleri çıkar", r1 == "bekletildi" and yaz[-1] == ("e", "bilmiyorum ama ben bakarım"), (r1, yaz[-1]))
bak("akış: ara bölgede kırpılan sayılır", ak["STATE"]["whisper"]["yanki_tanima"]["kirpilan"] == 2, ak["STATE"]["whisper"]["yanki_tanima"])
# yankı tanıma iş parçacığı: yankı Whisper'a gitmez, kullanıcı sözü yankısız işaretle gider; karşı akmıyorsa / ayar kapalıysa parça doğrudan WH_Q'ya
ak["_yt_np"] = lambda: np; ak["_YT"]["sg"] = None
simdi = time.time(); KT0 = simdi - SURE + 1
for a in range(0, len(karsi), SR // 2): ak["KARSI_TAMPON"].ekle(KT0 + a / SR, pcm(karsi[a:a + SR // 2]))
def yt_is(id_, mik, a, b): p_, t0, t1 = parca(mik, a, b); return {"id": id_, "kanal": "ben", "t0": t0 - T0 + KT0, "t1": t1 - T0 + KT0, "pcm": p_, "kuyruga": time.time()}
bak("akış: karşı akarken ben parçası yankı tanımaya alınır", ak["yt_kuyruga"](yt_is("y1", yanki80, 5, 8)) and ak["yt_kuyruga"](yt_is("y2", kul + gurultu, 12, 15)))
t = time.time(); gelen = []
while time.time() - t < 5 and len(gelen) < 1:
    try: gelen.append(ak["WH_Q"].get(timeout=0.2))
    except queue.Empty: pass
time.sleep(0.3); yt_ = ak["STATE"]["whisper"]["yanki_tanima"]
bak("akış: yankı parçası Whisper kuyruğuna girmez, yankı sayılır", ak["WH_Q"].empty() and yt_["atlanan_whisper"] == 1 and yt_["yanki"] == 1 and ak["STATE"]["whisper"]["yanki"] >= 1, yt_)
bak("akış: kullanıcı parçası yankısız işaretle Whisper kuyruğunda", len(gelen) == 1 and gelen[0]["id"] == "y2" and gelen[0].get("yt_bolge") == "yankisiz", [g.get("yt_bolge") for g in gelen])
bak("akış: beta'ya yalnız bölge sayacı (yanki_tanima_yanki/yankisiz + yanki)", "yanki_tanima_yanki" in olay and "yanki_tanima_yankisiz" in olay and all(isinstance(x, str) for x in olay), olay)
ak["AYAR"]["yanki_tanima"] = False; bak("akış: ayar yanki_tanima false → parça doğrudan Whisper'a", not ak["yt_kuyruga"](yt_is("y3", yanki80, 5, 8)))
ak["AYAR"].pop("yanki_tanima"); ak["STATE"]["whisper"]["kanallar"]["karsi"] = time.time() - 60
bak("akış: karşı kanal akmıyorsa parça doğrudan Whisper'a", not ak["yt_kuyruga"](yt_is("y4", yanki80, 5, 8)))
ak["STATE"]["whisper"]["kanallar"]["karsi"] = time.time(); ak["_yt_np"] = lambda: None; ak["yt_kuyruga"](yt_is("y5", yanki80, 5, 8))
try: g = ak["WH_Q"].get(timeout=3)
except queue.Empty: g = {}
bak("akış: numpy yoksa parça işaretsiz Whisper'a (geri sayılır)", g.get("id") == "y5" and "yt_bolge" not in g and ak["STATE"]["whisper"]["yanki_tanima"]["geri"] == 1)

# --- gerçek kayıt: 13 Kasım 02.27, masaüstü Teams, MacBook hoparlörü, 12 ben parçası --------------------------------------------
# Ölçüm raporu §7(e): 540, 543, 549, 554, 557, 560. sn yankı; 630. sn (0,84 sn, 0,31) ara; 189, 576, 580, 585, 619. sn yankısız.
BEKLENEN = {540: "yanki", 543: "yanki", 549: "yanki", 554: "yanki", 557: "yanki", 560: "yanki", 630: "ara", 189: "yankisiz", 576: "yankisiz", 580: "yankisiz", 585: "yankisiz", 619: "yankisiz"}
D = os.environ.get("YT_KAYIT") or next(iter(sorted(glob.glob(os.path.expanduser("~/Library/Application Support/*/canli/ses-arsivi/2026-11-13-0227-*")))), None)
def wav_oku(y):  # 16 bit PCM WAV (afconvert WAVE_FORMAT_EXTENSIBLE yazar; wave modülü onu açmaz) → ilk kanal int16
    b = open(y, "rb").read(); i = 12; kanal = 1; veri = None
    while i + 8 <= len(b):
        ad, boy = b[i:i + 4], int.from_bytes(b[i + 4:i + 8], "little")
        if ad == b"fmt ": kanal = int.from_bytes(b[i + 10:i + 12], "little"); assert int.from_bytes(b[i + 12:i + 16], "little") == SR and int.from_bytes(b[i + 22:i + 24], "little") == 16
        elif ad == b"data": veri = b[i + 8:i + 8 + boy]; break
        i += 8 + boy + (boy & 1)
    return np.frombuffer(veri[:len(veri) // (2 * kanal) * 2 * kanal], np.int16).reshape(-1, kanal)[:, 0].copy()
if not D or not os.path.isdir(D) or not os.path.exists(os.path.join(D, "parcalar.jsonl")): print("– gerçek kayıt yok, oynatma atlandı")
else:
    gec = tempfile.mkdtemp(prefix="yt-")
    def tam(ad):  # tam kayıt (toplantı sonunda AAC 32 kb/sn m4a'ya çevrilir) → 16 kHz WAV
        w = os.path.join(D, f"tam-{ad}.wav")
        if os.path.exists(w): return w
        w = os.path.join(gec, ad + ".wav"); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", os.path.join(D, f"tam-{ad}.m4a"), w], check=True, capture_output=True); return w
    kw, bw = tam("karsi"), tam("ben")
    try: TT0 = json.load(open(os.path.join(D, "tam.json")))["t0"]
    except (OSError, ValueError, KeyError): TT0 = 1794526072.35  # bu kaydın tam.json'u m4a dönüşümünde kalmadı; değer ölçüm kopyasından
    # Mikrofon da tam kayıttan alınır (raporun yöntemi: iki kanal aynı kodekten ve aynı zaman çizgisinden). Ham parça WAV'ı (Whisper'a giden) AAC'li karşıyla
    # kıyaslanınca tutarlılık düşük çıkıyor (yankıda 0,27–0,61): kodek iki kanala farklı biçimde dokunmuş olur; o sonuç yalnız bilgi olarak yazılır.
    k = wav_oku(kw); bt = wav_oku(bw); dogru = 0; n = 0
    for l in open(os.path.join(D, "parcalar.jsonl"), encoding="utf-8"):
        p = json.loads(l)
        if p.get("kanal") != "ben": continue
        sn = int(p["t0"] - TT0); bek = next((v for s, v in BEKLENEN.items() if abs(s - sn) <= 1), None)
        tb = KT(); a0 = max(0, int((p["t0"] - TT0 - 12) * SR)); a1 = min(len(k), int((p["t1"] - TT0 + 2) * SR))
        for a in range(a0, a1, SR // 2): tb.ekle(TT0 + a / SR, k[a:min(a + SR // 2, a1)].tobytes())
        b0 = int(round((p["t0"] - TT0) * SR)); b1 = int(round((p["t1"] - TT0) * SR))
        r = tani(bt[b0:b1].tobytes(), p["t0"], p["t1"], tb, np) or {}
        h = tani(wav_oku(os.path.join(D, p["dosya"])).tobytes(), p["t0"], p["t1"], tb, np) or {}
        n += 1; ok = r.get("bolge") == bek; dogru += ok
        print(f"   {'✓' if ok else '✗'} {sn:4d}. sn {p['sn']:4.2f} sn eski sonuç {p['sonuc']:8s} → {r.get('bolge')} (beklenen {bek}; tutarlılık {r.get('tutarlilik')}, kayma {r.get('kayma_ms')} ms"
              f"{', karşı sessiz' if r.get('neden') else ''}; ham parçayla: {h.get('bolge')} {h.get('tutarlilik') or ''})")
    bak(f"gerçek kayıt: {dogru}/{n} parça raporla aynı karar", n == 12 and dogru == 12, f"{dogru}/{n}")
print("yankı tanıma: ✓ hepsi geçti" if not hata else f"yankı tanıma: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
