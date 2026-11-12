#!/usr/bin/env python3
# Konuşma algılayıcı (Konuş Aşama 2, Adım 3; vad-isci.py + aktarici/vad.py): Silero VAD v6.2.3 gerçek modelle. Sessizlik düşük, konuşma yüksek olasılık,
# konuşma başı/sonu olayları, 512'den kısa öbeklerde artan örnek taşıması, model yokken düzgün "yok", istemci sarmalayıcısı, öbek başına gecikme.
# Gerçek model (AGIR_TESTLER; toplantı/sohbet sürerken bekler):  PYTHONDONTWRITEBYTECODE=1 python3 test/vad-isci.py   (~10 sn)
# Kayıt: ../_yedek/test-araclari/hoparlor-yanki/kayit3/ (yoksa konuşma sınamaları atlanır, sessizlik/model-yok yine koşar).
import base64, json, os, queue, statistics, subprocess, sys, threading, time, wave
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bosport  # noqa: F401  (AGIR_TESTLER: canlı Suflor meşgulse bekler)
import numpy as np
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
ORTAK = "/Users/Shared/Suflor"
PY = os.path.join(ORTAK, "smart-turn-venv", "bin", "python"); MODEL = os.path.join(ORTAK, "ses-modeller", "silero-vad", "silero_vad.onnx")
ISCI = os.path.join(KOD, "vad-isci.py"); SHA = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
KAYIT = os.path.join(os.path.dirname(KOD), "_yedek", "test-araclari", "hoparlor-yanki", "kayit3")
SR = 16000
class Isci:  # vad-isci.py'yi sürer; satır okuma zaman aşımlı
    def __init__(s, model):
        s.p = subprocess.Popen([PY, "-I", "-B", ISCI, model], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        s.q = queue.Queue(); threading.Thread(target=lambda: [s.q.put(l) for l in s.p.stdout], daemon=True).start(); s.n = 0
    def al(s, zaman=15):
        try: return json.loads(s.q.get(timeout=zaman))
        except queue.Empty: return None
    def sor(s, pcm=None, **kw):
        s.n += 1; g = dict(kw, id=s.n)
        if pcm is not None: g["pcm"] = base64.b64encode(pcm.tobytes()).decode()
        s.p.stdin.write(json.dumps(g) + "\n"); s.p.stdin.flush(); return s.al()
    def kapat(s):
        try: s.p.stdin.close(); s.p.wait(timeout=5)
        except Exception: s.p.kill()
def oku(ad):  # wav (int16 ya da float32) → int16 16 kHz mono; wave modülü float'u açmaz, RIFF elle okunur
    ham = open(os.path.join(KAYIT, ad), "rb").read(); i = 12; fmt = None; veri = b""
    while i + 8 <= len(ham):
        ad_, n = ham[i:i + 4], int.from_bytes(ham[i + 4:i + 8], "little")
        if ad_ == b"fmt ": fmt = (int.from_bytes(ham[i + 8:i + 10], "little"), int.from_bytes(ham[i + 10:i + 12], "little"), int.from_bytes(ham[i + 12:i + 16], "little"), int.from_bytes(ham[i + 22:i + 24], "little"))
        elif ad_ == b"data": veri = ham[i + 8:i + 8 + n]; break
        i += 8 + n + (n & 1)
    tur, kn, sr, bit = fmt
    a = np.frombuffer(veri, np.float32 if tur == 3 else np.int16)
    if kn > 1: a = a[:len(a) // kn * kn].reshape(-1, kn)[:, 0]
    a = a.astype(np.float32) * (1.0 if tur == 3 else 1 / 32768)
    if sr != SR: a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)
    return (np.clip(a, -1, 1) * 32767).astype(np.int16)
def akit(isci, a, oz=1600):  # 100 ms öbeklerle; tüm cevapları döndür
    cv = [isci.sor(a[i:i + oz]) for i in range(0, len(a), oz)]; return cv
ok("model dosyası var ve SHA-256 sabitlenen sürümle (v6.2.3) aynı", os.path.isfile(MODEL) and __import__("hashlib").sha256(open(MODEL, "rb").read()).hexdigest() == SHA)
ok("kod: işçi sabitler (512 pencere, 64 bağlam) ve istemci aynı SHA'yı taşır", "512, 64" in open(ISCI, encoding="utf-8").read() and SHA in open(os.path.join(KOD, "aktarici", "vad.py"), encoding="utf-8").read())
# 1. model yok → {"yok": true}, çıkış temiz
i = Isci("/yok/silero.onnx"); a = i.al(10); i.p.wait(timeout=10)
ok("model yokken işçi 'yok' der ve temiz çıkar (çökmez)", a == {"yok": True} and i.p.returncode == 0)
# 1b. bozuk model → hata satırı
boz = os.path.join(os.environ.get("TMPDIR", "/tmp"), "vad-bozuk.onnx"); open(boz, "wb").write(b"degil")
i = Isci(boz); a = i.al(10); i.p.wait(timeout=10); os.remove(boz)
ok("bozuk model dosyasında 'hata' der, çıkar", bool(a and a.get("hata")) and i.p.returncode == 0)
if not os.path.isfile(MODEL): print("✗ model yok: gerçek model sınamaları koşamadı"); sys.exit(1)
I = Isci(MODEL); h = I.al(30); ok("işçi hazır", h == {"hazir": True})
# 2. sessizlik
sess = np.zeros(SR * 2, np.int16); rng = np.random.RandomState(1); gur = (rng.randn(SR * 2) * 30).astype(np.int16)  # ~ −60 dBFS oda gürültüsü
cv = akit(I, sess); pp = [x for c in cv for x in c["p"]]
ok(f"sessizlikte olasılık düşük (en yüksek {max(pp):.3f} < 0,1), olay yok", max(pp) < 0.1 and not any(c["olay"] for c in cv) and not cv[-1]["konusma"])
I.sor(sifirla=True); cv = akit(I, gur); pp = [x for c in cv for x in c["p"]]
ok(f"hafif gürültüde olasılık düşük (en yüksek {max(pp):.3f} < 0,3), olay yok", max(pp) < 0.3 and not any(c["olay"] for c in cv))
# 3. 512'den kısa öbekler: artan örnek taşınır, toplam pencere sayısı doğru
I.sor(sifirla=True); n = 0
for k in range(0, 1000, 100): n += len(I.sor(sess[k:k + 100])["p"])
ok(f"100 örneklik öbekler: 1000 örnekten {n} pencere (=1000//512=1), artan taşınır", n == 1)
c = I.sor(sess[:12]); ok("toplam 1012 örnek → ikinci pencere 1024'te: 12 örnek daha pencere üretmez, 12 daha üretir", len(c["p"]) == 0 and len(I.sor(sess[:12])["p"]) == 1)
# 4. gerçek konuşma
if os.path.isdir(KAYIT):
    veri = {}
    for ad in ("kisa_mert.wav", "kisa_var_ham.wav"):
        if os.path.exists(os.path.join(KAYIT, ad)): veri[ad] = oku(ad)
    ok("kayıt örnekleri bulundu", bool(veri))
    for ad, a in veri.items():
        I.sor(sifirla=True); cv = akit(I, a); pp = np.array([x for c in cv for x in c["p"]]); ol = [o for c in cv for o in c["olay"]]
        ok(f"{ad}: konuşma var ({len(a) / SR:.1f} sn) — en yüksek olasılık {pp.max():.2f} ≥ 0,9 ve %{100 * (pp >= 0.5).mean():.0f} pencere ≥ 0,5", pp.max() >= 0.9 and (pp >= 0.5).mean() > 0.05)
        bas = [o for o in ol if o["o"] == "basla"]; bit = [o for o in ol if o["o"] == "bitti"]
        ok(f"{ad}: en az bir 'basla' olayı ve olaylar sıralı (basla/bitti dönüşümlü, zaman artan)", len(bas) >= 1 and all(ol[k]["t"] <= ol[k + 1]["t"] and ol[k]["o"] != ol[k + 1]["o"] for k in range(len(ol) - 1)) and ol[0]["o"] == "basla")
        print(f"   {ad}: {len(bas)} başla, {len(bit)} bitti; ilk başla {bas[0]['t'] / 1000:.2f} sn" if bas else "")
# 5. sentetik: sessizlik + konuşma (kayıttan alınan 2 sn) + sessizlik → olay zamanları
    k_ = veri.get("kisa_mert.wav") if veri.get("kisa_mert.wav") is not None else next(iter(veri.values()), None)
    if k_ is not None:
        pp_ = np.array([x for c in (I.sor(sifirla=True), ) for x in c["p"]]); I.sor(sifirla=True)
        cvk = akit(I, k_); pk = np.array([x for c in cvk for x in c["p"]]); ilk = int(np.argmax(pk >= 0.5)) * 32  # kaydın kendi konuşma başı (ms)
        I.sor(sifirla=True)
        dolgu = np.zeros(SR * 1, np.int16); a = np.concatenate([dolgu, k_, np.zeros(SR * 2, np.int16)]); cv = akit(I, a); ol = [o for c in cv for o in c["olay"]]
        bas = [o for o in ol if o["o"] == "basla"]
        ok(f"1 sn sessizlik sonrası konuşma başı: ilk 'basla' ≈ {1000 + ilk} ms (±150), bulunan {bas[0]['t'] if bas else None}", bool(bas) and abs(bas[0]["t"] - (1000 + ilk)) <= 150)
        ok("kayıt sonrası 2 sn sessizlikte son olay 'bitti', durum konuşma değil", bool(ol) and ol[-1]["o"] == "bitti" and not cv[-1]["konusma"])
# 6. parametre: eşik 0,99 → çok az/hiç başla; sifirla durumu sıfırlar
        I.sor(sifirla=True); cv = akit(I, k_[:SR * 3], 1600); ilk_p = cv[0]["p"]
        I.sor(sifirla=True); cv2 = akit(I, k_[:SR * 3], 1600)
        ok("sıfırla sonrası aynı ses aynı olasılıkları verir (durum taşınmıyor)", [c["p"] for c in cv] == [c["p"] for c in cv2])
        I.sor(sifirla=True, esik=0.999); cv3 = akit(I, k_); b3 = sum(1 for c in cv3 for o in c["olay"] if o["o"] == "basla")
        I.sor(sifirla=True, esik=0.5); cv4 = akit(I, k_); b4 = sum(1 for c in cv4 for o in c["olay"] if o["o"] == "basla")
        ok(f"eşik parametresi etkili: 0,999 → {b3} başla ≤ 0,5 → {b4} başla", b3 <= b4)
# 7. gecikme: 100 ms (1600 örnek, 3 pencere) ve 32 ms (tek pencere) öbek
    I.sor(sifirla=True); ms100 = []; ms32 = []
    a = k_ if k_ is not None else sess
    for k in range(0, min(len(a), SR * 8) - 1600, 1600):
        t = time.perf_counter(); c = I.sor(a[k:k + 1600]); ms100.append(((time.perf_counter() - t) * 1000, c["ms"]))
    for k in range(0, 512 * 100, 512):
        t = time.perf_counter(); c = I.sor(a[k:k + 512]); ms32.append(((time.perf_counter() - t) * 1000, c["ms"]))
    d1 = statistics.median(x[0] for x in ms100); d1i = statistics.median(x[1] for x in ms100); d2 = statistics.median(x[0] for x in ms32); d2i = statistics.median(x[1] for x in ms32)
    print(f"   gecikme: 100 ms öbek ortanca {d1:.1f} ms (işçi içi {d1i:.1f}, en çok {max(x[0] for x in ms100):.1f}); 32 ms öbek ortanca {d2:.1f} ms (işçi içi {d2i:.1f}, en çok {max(x[0] for x in ms32):.1f})")
    ok("100 ms öbeğin gidiş-dönüş gecikmesi ortanca < 25 ms (gerçek zamandan çok hızlı)", d1 < 25)
I.kapat()
# 8. istemci sarmalayıcısı (aktarici/vad.py): relay ad alanını taklit eden sözlükte çalıştır
ns = {"os": os, "json": json, "time": time, "base64": base64, "queue": queue, "threading": threading, "subprocess": subprocess, "_ORT": ORTAK, "_UYG": KOD, "_APP": KOD,
      "_ilk": lambda *y: next((x for x in y if os.path.exists(x)), y[-1]), "WH_SR": SR}
exec(compile(open(os.path.join(KOD, "aktarici", "vad.py"), encoding="utf-8").read(), "vad.py", "exec"), ns)
ok("istemci: hazır olmadan vad_olasilik None döner", ns["vad_olasilik"](b"\0" * 1024) is None)
ok("istemci: vad_baslat True", ns["vad_baslat"]() is True)
t = time.time()
while ns["VAD"]["durum"] != "hazir" and time.time() - t < 20: time.sleep(0.1)
ok("istemci: işçi hazır oldu", ns["VAD"]["durum"] == "hazir")
r = ns["vad_olasilik"](sess[:3200].tobytes()); ok("istemci: sessizlik → son < 0,1, 6 pencere, konuşma yok", bool(r) and r["son"] < 0.1 and len(r["p"]) == 6 and r["konusma"] is False)
if os.path.isdir(KAYIT) and k_ is not None:
    ns["vad_sifirla"](); r = None
    for k in range(0, len(k_), 3200):
        r = ns["vad_olasilik"](k_[k:k + 3200].tobytes()); got = r and r["konusma"]
        if got: break
    ok("istemci: gerçek konuşmada 'konusma' True olur", bool(got))
ok("istemci: vad_sifirla True", ns["vad_sifirla"]() is True)
ns["vad_kapat"](); ok("istemci: vad_kapat sonrası vad_olasilik None", ns["vad_olasilik"](b"\0" * 1024) is None)
# 9. istemci: model yok
ns2 = dict(ns); ns2["VAD"] = None; ns3 = {k: v for k, v in ns.items() if k != "VAD"}; 
os.environ["SUFLOR_VAD_MODEL"] = "/yok/silero.onnx"; exec(compile(open(os.path.join(KOD, "aktarici", "vad.py"), encoding="utf-8").read(), "vad.py", "exec"), ns3); del os.environ["SUFLOR_VAD_MODEL"]
ok("istemci: model yokken vad_baslat False, durum 'yok', vad_olasilik None", ns3["vad_baslat"]() is False and ns3["VAD"]["durum"] == "yok" and ns3["vad_olasilik"](b"\0" * 1024) is None)
print("\nTAMAM" if not HATA else f"\nBAŞARISIZ: {len(HATA)}"); sys.exit(1 if HATA else 0)
