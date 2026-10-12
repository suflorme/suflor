#!/usr/bin/env python3
# Masaüstü toplantıda kullanıcının mikrofonu (v0.30.0): menü uygulamasının POST /ses-masaustu parçası yalnız masaüstü toplantı sürerken ve
# mikrofon sessizde değilken "ben" kanalına girer; anahtarsız istek reddedilir; tarayıcıda toplantı varken ya da eklenti son 3 sn'de "ben"
# parçası verdiyse atılır; hoparlörle (kulaklık yok) /status masaustu_mic.kulaklik false. Yalıtılmış aktarıcı, sessiz PCM (Whisper işi doğmaz).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/masaustu-mic.py      (kaldı → çıkış 1)
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-mm-"); PORT = 8793; URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_KOKEN="http://sahte.test"))
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None, anahtarli=True, koken=None):
    h = {"X-Suflor-Anahtar": anahtar()} if anahtarli else {}
    if koken: h["Origin"] = koken
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET", headers=h)
    try: return json.load(urllib.request.urlopen(q, timeout=5))
    except urllib.error.HTTPError as e: return {"_kod": e.code}
PCM = base64.b64encode(b"\0" * 32000).decode()  # 1 sn sessizlik
def parca(): return istek("/ses-masaustu", {"t": int(time.time() * 1000), "pcm": PCM, "aygit": "MacBook Pro Mikrofonu"})
def mm(): return istek("/status").get("masaustu_mic") or {}
def masaustu(toplantida, sessiz=None):
    istek("/masaustu", dict({"uygulama": "Teams", "toplantida": toplantida, "baslik": "Deneme | Kurum | a" + "@" + "b.c | Microsoft Teams"}, **({} if sessiz is None else {"sessiz": sessiz})))
hata = []
def bak(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hata.append(ad)
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    bak("anahtarsız istek reddedilir", istek("/ses-masaustu", {"pcm": PCM}, anahtarli=False).get("_kod") == 401)
    bak("toplantı yokken parça atılır", parca().get("bekle") is True and mm().get("parca") == 0)
    istek("/ses-masaustu", {"olay": "acildi", "aygit": "MacBook Pro Mikrofonu"})
    masaustu(True, False)
    v = parca(); bak("masaüstü toplantıda, mikrofon açık: ben kanalına girer", v.get("ok") is True and not v.get("bekle") and mm().get("parca") == 1)
    s = mm(); bak("/status masaustu_mic akıyor + aygıt", s.get("akiyor") is True and s.get("aygit") == "MacBook Pro Mikrofonu")
    bak("hoparlörle: kulaklik false (panoda 'Kulaklık önerilir')", s.get("kulaklik") is False)
    masaustu(True, None); v = parca(); bak("sessiz bilinmiyorsa gönderilir (web davranışı)", not v.get("bekle") and mm().get("parca") == 2)
    masaustu(True, True); v = parca(); bak("sessizdeyken atılır", v.get("bekle") is True and mm().get("parca") == 2)
    masaustu(True, False)
    istek("/ses", {"kanal": "ben", "t": int(time.time() * 1000), "pcm": PCM}, koken="http://sahte.test")
    v = parca(); bak("eklenti son 3 sn'de ben verdiyse atılır (çift satır yok)", v.get("eklenti") is True and mm().get("parca") == 2)
    time.sleep(3.2); v = parca(); bak("3 sn sonra yeniden girer", not v.get("eklenti") and mm().get("parca") == 3)
    istek("/ping", {"meeting": {"title": "Tarayıcı toplantısı"}, "call": True, "panel": False, "rows": 0}, koken="http://sahte.test")
    v = parca(); bak("tarayıcıda toplantı varken atılır", v.get("bekle") is True and mm().get("parca") == 3)
    istek("/ses-masaustu", {"olay": "kapandi"})
    log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    bak("günlükte açıldı/kapandı satırları", "MASAÜSTÜ MİKROFON: açıldı · MacBook Pro Mikrofonu" in log and "MASAÜSTÜ MİKROFON: kapandı" in log)
    bak("aktarıcıda hata yok", "Traceback" not in log)
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"masaüstü mikrofon: {len(hata)} sorun" if hata else "masaüstü mikrofon: ✓ GEÇTİ")
sys.exit(1 if hata else 0)
