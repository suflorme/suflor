#!/usr/bin/env python3
# Toplantı yokken pano kutusu (v0.117.0, S136; aktarici/notlar.py): not Notlar defterine (canli/notlar.jsonl), soru toplantı dışı asistana yazılı
# (konus_yazili); sahte "Toplantı" dökümü açılmaz, pano toplantı görünümüne geçmez. Başlat/gündem son 30 dk'daysa eski yol (yeni toplantıya).
# /status notlar, /notlar silme (yalnız pano). Yalıtılmış aktarıcı; Claude çağrılmaz (Brifing.app yok — yalnız yönlendirme denenir).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/notlar.py      (kaldı → çıkış 1; ~5 sn)
import glob, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8769)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-notlar-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
def istek(yol, govde=None, anahtar=True, koken=True):
    h = {"Content-Type": "application/json"}
    if anahtar: h["X-Suflor-Anahtar"] = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    if koken: h["Origin"] = f"http://127.0.0.1:{PORT}"
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=None if govde is None else json.dumps(govde).encode(), headers=h, method="GET" if govde is None else "POST")
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except urllib.error.HTTPError as e: return {"_kod": e.code}
log = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8").read()
dokumler = lambda: [f for f in glob.glob(os.path.join(canli, "*.md"))]
try:
    for _ in range(60):
        if "çalışıyor" in log(): break
        time.sleep(0.2)
    g = istek("/girdi", {"text": "Ayşe'ye fiyatı sor"})
    bak("toplantı yokken not: Notlar defterine (tur defter)", g.get("ok") is True and g.get("tur") == "defter")
    sat = [json.loads(l) for l in open(os.path.join(canli, "notlar.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(canli, "notlar.jsonl")) else []
    bak("notlar.jsonl'de not var", len(sat) == 1 and sat[0]["metin"] == "Ayşe'ye fiyatı sor" and sat[0]["id"].startswith("n"))
    bak("sahte 'Toplantı' dökümü açılmadı", dokumler() == [])
    s = istek("/status")
    bak("/status notlar listesi, pano toplantı görünümünde değil", [x["metin"] for x in s.get("notlar") or []] == ["Ayşe'ye fiyatı sor"] and s.get("aktif") is False)
    g = istek("/girdi", {"text": "?Yarınki toplantının gündemi ne"})
    bak("toplantı yokken '?' soru: asistana yazılı (tur asistan)", g.get("tur") == "asistan" and "KONUŞ: yazılı soru" in log())
    time.sleep(0.5); g = istek("/girdi", {"text": "Command Enter ile soru", "soru": True})
    bak("Command + Enter sorusu da asistana (dökümde soru yok)", g.get("tur") in ("asistan",) and dokumler() == [])
    bak("anahtarsız /notlar silme reddedilir", istek("/notlar", {"sil": sat[0]["id"] if sat else "x"}, anahtar=False, koken=False).get("_kod") in (401, 403))
    bak("başka kökenden /notlar silme reddedilir", istek("/notlar", {"sil": sat[0]["id"] if sat else "x"}, koken=False).get("_kod") == 403)
    d = istek("/notlar", {"sil": sat[0]["id"] if sat else "x"})
    bak("pano notu siler, /status'ta kalmaz", d.get("ok") is True and not istek("/status").get("notlar"))
    bak("olmayan notu silme: ok false", istek("/notlar", {"sil": "nyok"}).get("ok") is False)
    json.dump({"title": "Yeni toplantı", "items": ["Bütçe"]}, open(os.path.join(canli, "agenda.json"), "w"))  # Başlat/gündem: toplantı hazırlanıyor
    g = istek("/girdi", {"text": "hazırlık notu"})
    bak("gündem yeni yazılmışsa not eski yoldan (tur not; Faz B: toplantı açılınca dökümüne, şimdilik bekler — sahte 'Toplantı' dosyası yok)", g.get("tur") == "not" and dokumler() == [])
    bak("aktarıcıda hata yok", "Traceback" not in log())
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("notlar: ✓ hepsi geçti" if not hata else f"notlar: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
