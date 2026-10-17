#!/usr/bin/env python3
# Toplantı içi fısıltı (v0.27.0, ayar fisilti: true). Yalıtılmış aktarıcı (deneme kipi: ses çalınmaz, günlüğe "FISILTI (deneme)"):
# DUR kartı ilk 4 sözcükle okunur · fısıltı metni verilen SÖYLE kartı okunur, verilmeyen okunmaz · iki fısıltı arası beklenir (deneme 2 sn) ·
# kulaklık yokken okunmaz · toplantı yokken okunmaz · ayar kapalıyken okunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/fisilti.py      (kaldı → çıkış 1; ~25 sn)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8781)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
def calistir(fisilti=True, kulaklik="1"):
    T = tempfile.mkdtemp(prefix="suflor-fs-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "fisilti": fisilti}, open(ay, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK=kulaklik))
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(yol, v):
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    log = lambda: [l.split("FISILTI", 1)[1].strip() for l in open(os.path.join(T, "relay.log"), encoding="utf-8") if "FISILTI" in l]
    return r, T, post, log
r, T, post, log = calistir()
try:
    post("/card", {"kind": "dur", "text": "Toplantı yokken okunmamalı"}); time.sleep(0.8)
    bak("toplantı yokken okunmaz", not log())
    post("/ping", {"call": True, "panel": True, "meeting": {"title": "Fısıltı Deneme"}})
    post("/card", {"kind": "dur", "text": "Yedekleri sor, süre doluyor ve konu açık"}); time.sleep(0.8)
    bak("DUR kartı ilk 4 sözcükle okunur", log()[-1:] == ["(deneme): Yedekleri sor, süre doluyor"])
    post("/card", {"kind": "dur", "text": "Hemen ikinci kart"}); time.sleep(0.8)
    bak("2 sn dolmadan ikincisi okunmaz", "20 sn dolmadı" in " ".join(log()[-1:]))
    time.sleep(2.2); n = len(log())
    post("/card", {"kind": "soyle", "text": "Fısıltısız söyle kartı"}); time.sleep(0.8)
    bak("fısıltı metni olmayan SÖYLE kartı okunmaz", len(log()) == n)
    post("/card", {"kind": "soyle", "text": "Ayşe bütçeyi sordu: cevap 120 bin", "fisilti": "Bütçe yüz yirmi bin"}); time.sleep(0.8)
    bak("fısıltı metni verilen kart okunur", log()[-1:] == ["(deneme): Bütçe yüz yirmi bin"])
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
for ad, kw in (("kulaklık yokken okunmaz", {"kulaklik": "0"}), ("ayar kapalıyken okunmaz", {"fisilti": False})):
    r, T, post, log = calistir(**kw)
    try:
        post("/ping", {"call": True, "panel": True, "meeting": {"title": "Fısıltı Deneme"}}); post("/card", {"kind": "dur", "text": "Okunmamalı bu kart"}); time.sleep(0.8)
        bak(ad, not [x for x in log() if x.startswith("(deneme)")])
    finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("fısıltı: ✓ hepsi geçti" if not hata else f"fısıltı: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
