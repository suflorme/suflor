#!/usr/bin/env python3
# Canlı çeviri (aktarici/ceviri.py, v0.27.0; ayar ceviri: true). Yalıtılmış aktarıcı, deneme çevirmeni (SUFLOR_TEST_CEVIRI: Claude çağrılmaz):
# karşı tarafın İngilizce Whisper satırı çevrilir, panonun /status tail'inde "ceviri" alanı, <toplantı>.ceviri.jsonl'e yazılır, .jsonl değişmez ·
# Türkçe satır ve kullanıcının kendi satırı çevrilmez · ayar kapalıyken çevrilmez · dil tahmini tablosu. İsteğe bağlı gerçek Claude denemesi:
# SUFLOR_CEVIRI_GERCEK=1 (az kota: tek öbek).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ceviri.py      (kaldı → çıkış 1; ~15 sn)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8779
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
def calistir(ceviri=True, gercek=False):
    T = tempfile.mkdtemp(prefix="suflor-cv-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "ceviri": ceviri}, open(ay, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
    if not gercek: env["SUFLOR_TEST_CEVIRI"] = "1"
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def istek(yol, v=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K})
        return json.loads(urllib.request.urlopen(q, timeout=40).read())
    return r, T, canli, istek
def satirlar(istek):
    t = time.time()
    istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [
        {"id": "wh/karsi/1", "speaker": "John", "time": "10:00:00", "text": "We can ship the new version on Monday if the tests pass.", "kanal": "karsi", "t0": t, "t1": t + 3},
        {"id": "wh/karsi/2", "speaker": "Ayşe", "time": "10:00:05", "text": "Bence bu hafta bitiremeyiz, çok iş var.", "kanal": "karsi", "t0": t + 5, "t1": t + 8},
        {"id": "wh/ben/1", "speaker": "Ali K", "time": "10:00:10", "text": "Okay, and what about the budget for this?", "kanal": "ben", "t0": t + 10, "t1": t + 12}]})
r, T, canli, istek = calistir()
try:
    satirlar(istek); time.sleep(3.5)
    tl = {x["id"]: x for x in istek("/status")["tail"] if x.get("id")}
    bak("İngilizce karşı satır çevrildi (tail'de ceviri)", tl.get("wh/karsi/1", {}).get("ceviri", "").startswith("[çeviri] We can ship"))
    bak("Türkçe karşı satır çevrilmedi", "ceviri" not in tl.get("wh/karsi/2", {}))
    bak("kullanıcının kendi satırı çevrilmedi", "ceviri" not in tl.get("wh/ben/1", {}))
    cv = [f for f in os.listdir(canli) if f.endswith(".ceviri.jsonl")]
    bak(".ceviri.jsonl yazıldı, .jsonl'de ceviri yok", cv and "ceviri" not in open(os.path.join(canli, cv[0].replace(".ceviri.jsonl", ".jsonl")), encoding="utf-8").read())
    bak("/status ceviri: açık, 1 satır", (istek("/status").get("ceviri") or {}).get("n") == 1)
finally: r.terminate(); r.wait(5)
shutil.rmtree(T, ignore_errors=True)
r, T, canli, istek = calistir(ceviri=False)
try:
    satirlar(istek); time.sleep(3.5)
    bak("ayar kapalıyken çevrilmez", not any("ceviri" in x for x in istek("/status")["tail"]))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
if os.environ.get("SUFLOR_CEVIRI_GERCEK"):
    r, T, canli, istek = calistir(gercek=True)
    try:
        satirlar(istek); t = time.time(); tr = ""
        while time.time() - t < 40 and not tr:
            time.sleep(1); tr = next((x.get("ceviri", "") for x in istek("/status")["tail"] if x.get("id") == "wh/karsi/1"), "")
        print(f"   gerçek Claude: {time.time() - t:.1f} sn · {tr}")
        bak("gerçek Claude çevirisi Türkçe", any(c in tr for c in "çğıöşü") or "Pazartesi" in tr)
    finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("çeviri: ✓ hepsi geçti" if not hata else f"çeviri: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
