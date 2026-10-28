#!/usr/bin/env python3
# Yerel ses yardımcısının "izin" uyarısı ve yeniden kurma kaydı (v0.20.4): 1 dk hep sıfır ses tek başına uyarı değildir (karşı taraf
# sessiz olabilir); uyarı için karşı tarafın konuştuğuna kanıt gerekir (altyazıda başka birinin satırı ya da eklentinin sekme sesi).
# v0.155.0: kanıt sıfırlar başladıktan sonra gelmeli; o sırada karşı taraf konuşursa yardımcıdan yeniden kurma istenir (nabız yanıtında yeniden_kur).
# Aktarıcıda yerel_ses_* / karsi_konusuyor / ses_al değişince koştur (~2,5 dk; sahte nabız, gerçek yardımcı gerekmez):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yerel-ses.py
import base64, json, os, shutil, struct, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8792)
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
    # v0.155.0 (28 Ekim Teams web, paylaşım sonrası): karşı taraf konuştu, SONRA herkes sustu — sessizlikten önceki satır "izin" kanıtı sayılmaz
    post("/ingest", {"meeting": {"title": "Deneme"}, "source": "captions", "entries": [{"id": "c/3", "speaker": "Deniz T", "time": "00:03", "text": "son sözüm bu"}]})
    istek = []; t0 = time.time()
    while time.time() - t0 < 66: toplanti(); istek.append(nabiz(akis=True).get("yeniden_kur")); time.sleep(5)
    ok("sessizlikten önce konuşan karşı taraf + 1 dk sıfır: izin yok (dinliyor)", durum() == "dinliyor")
    ok("gerçek sessizlikte yeniden kurma istenmez", not any(istek))
    post("/ingest", {"meeting": {"title": "Deneme"}, "source": "captions", "entries": [{"id": "c/4", "speaker": "Deniz T", "time": "00:04", "text": "duyuyor musun"}]})
    y1 = nabiz(akis=True)
    ok("sıfır ses sürerken karşı taraf konuştu: yeniden kurma istenir", y1.get("yeniden_kur") is True and "yardımcıdan yakalamayı yeniden kurması istendi (örnek geliyor)" in log())
    ok("aynı istek 45 sn içinde yinelenmez", not nabiz(akis=True).get("yeniden_kur"))
    ok("sessizlik sırasında konuşma + 1 dk sıfır: izin, geçiş günlükte", durum() == "izin" and "YEREL SES: dinliyor → izin · Chrome ·" in log() and "örnek geliyor" in log())
    nabiz(tepe=1200); ok("ses gelince yine kalkar", durum() == "dinliyor")
    nabiz(kurma=1, kurma_neden="ses çıkaran yeni süreç")
    ok("yeniden kurma aktarıcı günlüğünde nedeniyle", "ses yakalama yeniden kuruldu (ses çıkaran yeni süreç; toplam 1)" in log())
    nabiz(kurma=1); ok("aynı sayı tekrar yazılmaz", log().count("ses yakalama yeniden kuruldu") == 1)
    ks = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["yerel_ses"].get("kisma") or {}
    ok("kısma kipi /status'ta (ayar kapalı, etkin değil)", ks() == {"ayar": False, "etkin": False})
    nabiz(kis_kipi=True); ok("kısma kipi etkin: /status ve günlük", ks().get("etkin") is True and "kısma kipi etkin" in log())
    nabiz(); ok("kısma kipi bitti: /status", ks().get("etkin") is False)
    ok("deneme aktarıcısı gerçek yardımcıyı başlatmadı", "yardımcı başlatıldı" not in log())
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); shutil.rmtree(T, ignore_errors=True)
print("yerel ses:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
