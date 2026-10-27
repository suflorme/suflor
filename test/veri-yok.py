#!/usr/bin/env python3
# Faz D (S162, v0.147.0) — "toplantı var, veri yok": toplantı sürerken (eklenti çağrıda) hiçbir kanaldan satır gelmezse /status veri_yok {sn, kanallar}, günlükte bir kez
# "VERİ YOK:", panoda sarı uyarı; satır gelince kalkar; satır yine kesilirse yeniden çıkar; toplantı yokken ve gizli kipte çıkmaz; /status veri_kanal satır akışını söyler.
# aktarici/saglik.py, ingest'te veri_satiri ya da pano durum() değişince koştur:  PYTHONDONTWRITEBYTECODE=1 python3 test/veri-yok.py
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8782)
T = os.path.realpath(tempfile.mkdtemp(prefix="veriyok-")); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "konusma": False, "yerel_ses": False, "oto_toplanti": False, "tepki_sesleri": os.path.join(T, "yok")}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
LOG = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(LOG, "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0"))
U = f"http://127.0.0.1:{PORT}"; L = lambda: open(LOG, encoding="utf-8").read()
def istek(yol, g=None):
    k = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k}
    if yol in ("/komut",): h["Origin"] = U
    q = urllib.request.Request(U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
    return json.load(urllib.request.urlopen(q, timeout=10))
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        if kosul(): return True
        time.sleep(0.3)
    return False
NABIZ = {"a": False}
def nabiz():
    while True:
        try:
            if NABIZ["a"]: istek("/ping", {"ver": "0.147.0", "meeting": {"title": "Deneme"}, "panel": False, "rows": 0, "platform": "teams", "call": True, "captions": False})
        except Exception: pass
        time.sleep(1)
vy = lambda: istek("/status").get("veri_yok")
try:
    ok("aktarıcı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")), 20)); time.sleep(1.5)
    threading.Thread(target=nabiz, daemon=True).start()
    ok("toplantı yokken veri_yok yok", vy() is None)
    NABIZ["a"] = True
    ok("toplantı yeni başladı: henüz uyarı yok", bekle(lambda: (istek("/status").get("extension") or {}).get("call"), 8) and vy() is None)
    ok("satır gelmeyince veri_yok çıktı", bekle(lambda: vy() is not None, 15))
    v = vy() or {}
    ok(f"veri_yok sn ve kanallar (altyazı, ben, karşı): {v}", v.get("sn", 0) >= 6 and {"altyazi", "ben", "karsi"} <= set(v.get("kanallar") or {}))
    ok("günlükte VERİ YOK bir kez", L().count("VERİ YOK: toplantı sürüyor") == 1)
    time.sleep(3); ok("günlük tekrarlanmadı", L().count("VERİ YOK: toplantı sürüyor") == 1)
    istek("/ingest", {"meeting": {"title": "Deneme"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Deniz Yıldız", "time": "10:00", "text": "Merhaba"}]})
    ok("satır gelince uyarı kalktı", vy() is None)
    ok("günlükte 'kalktı (satır geldi)'", bekle(lambda: "VERİ YOK: kalktı (satır geldi)" in L(), 5))
    vk = istek("/status").get("veri_kanal") or {}; ok(f"veri_kanal: altyazı akıyor (satır geldi) ama ben/karşı akmıyor: {vk}", vk.get("altyazi") is True and not vk.get("karsi") and not vk.get("ben"))
    ok("satır yine kesilince uyarı yeniden çıktı", bekle(lambda: vy() is not None, 15))
    ok("ikinci kesinti ikinci kez günlüğe", bekle(lambda: L().count("VERİ YOK: toplantı sürüyor") == 2, 5))
    istek("/ingest", {"meeting": {"title": "Deneme"}, "source": "whisper", "entries": [{"id": "w/1", "speaker": "Deniz T", "time": "10:05", "text": "Evet", "kanal": "karsi"}]})
    vk = istek("/status").get("veri_kanal") or {}; ok(f"Whisper karşı satırı karşı kanalı akıtır: {vk}", vk.get("karsi") is True and vy() is None)
    # gizli kip: Suflor hiçbir şey dinlemez, uyarı çıkmaz
    time.sleep(7); ok("tekrar kesildi", vy() is not None)
    istek("/komut", {"tur": "gizli"}); time.sleep(1); ok("gizli kipte veri_yok yok", vy() is None); istek("/komut", {"tur": "gizli"})
    NABIZ["a"] = False
    ok("toplantı bitince veri_yok kalktı", bekle(lambda: vy() is None, 15))
    # pano: sarı uyarı metni kaynakta
    pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read(); ok("pano durum() veri_yok uyarısı", "s.veri_yok" in pano and "Toplantı sürüyor ama {n} sn'dir döküm gelmiyor" in pano)
finally:
    r.terminate(); time.sleep(0.5); shutil.rmtree(T, ignore_errors=True)
print("\nSONUÇ: " + ("hepsi geçti" if not HATA else f"{len(HATA)} başarısız: {HATA}")); sys.exit(1 if HATA else 0)
