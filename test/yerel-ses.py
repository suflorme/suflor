#!/usr/bin/env python3
# Yerel ses yardımcısının "izin" uyarısı ve yeniden kurma kaydı (v0.20.4): 1 dk hep sıfır ses tek başına uyarı değildir (karşı taraf
# sessiz olabilir); uyarı için karşı tarafın konuştuğuna kanıt gerekir (altyazıda başka birinin satırı ya da eklentinin sekme sesi).
# Aktarıcıda yerel_ses_* / karsi_konusuyor / ses_al değişince koştur (~75 sn; sahte nabız, gerçek yardımcı gerekmez):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yerel-ses.py
import base64, json, os, shutil, struct, subprocess, sys, tempfile, time, urllib.error, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8792
T = tempfile.mkdtemp(prefix="yerel-"); canli = os.path.join(T, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "Suflor Ses.app"))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")) and os.path.exists(os.path.join(T, "ses-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); SK = open(os.path.join(T, "ses-anahtari.txt")).read().strip()
    def post(yol, v, k=K):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": k}), timeout=10).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    durum = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["yerel_ses"]["durum"]
    log = lambda: open(os.path.join(T, "relay.log")).read()
    toplanti = lambda: post("/ping", {"call": True, "panel": True, "meeting": {"title": "Deneme"}})
    nabiz = lambda **e: post("/ses-yerel", dict({"nabiz": True, "durum": "dinliyor", "tepe": 0, "uygulama": "Chrome", "surum": "0.20.4", "kurma": 0}, **e), SK)
    toplanti(); nabiz()
    ok("nabızla dinliyor", durum() == "dinliyor")
    t0 = time.time()
    while time.time() - t0 < 66: toplanti(); nabiz(); time.sleep(5)
    ok("1 dk sıfır ses, karşı taraf konuşmuyor: uyarı yok (dinliyor)", durum() == "dinliyor")
    post("/ingest", {"meeting": {"title": "Deneme"}, "source": "captions", "entries": [{"id": "c/1", "speaker": "Ali K", "time": "00:01", "text": "kendi satırım"}]})
    ok("yalnız kendi altyazı satırı: uyarı yok", durum() == "dinliyor")
    post("/ingest", {"meeting": {"title": "Deneme"}, "source": "captions", "entries": [{"id": "c/2", "speaker": "Deniz T", "time": "00:02", "text": "karşı taraf konuşuyor"}]})
    ok("karşı taraf altyazıda konuşuyor, yardımcı sıfır: izin", durum() == "izin")
    nabiz(tepe=1200); ok("ses gelince izin kalkar", durum() == "dinliyor")
    nabiz(kurma=1, kurma_neden="ses çıkaran yeni süreç")
    ok("yeniden kurma aktarıcı günlüğünde nedeniyle", "ses yakalama yeniden kuruldu (ses çıkaran yeni süreç; toplam 1)" in log())
    nabiz(kurma=1); ok("aynı sayı tekrar yazılmaz", log().count("ses yakalama yeniden kuruldu") == 1)
    ok("deneme aktarıcısı gerçek yardımcıyı başlatmadı", "yardımcı başlatıldı" not in log())
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); shutil.rmtree(T, ignore_errors=True)
print("yerel ses:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
