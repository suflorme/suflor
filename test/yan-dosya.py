#!/usr/bin/env python3
# Toplantı dosyası seçimi yan dosyaları (.ceviri.jsonl …) saymaz (v0.29.4; 12 Ekim deneme 6: çeviri dosyası en yeni olduğu için aktarıcı yeniden
# başlayınca süren toplantıya bağlanamadı → toplantı üç dosyaya bölündü; izle "…ceviri.md"yi toplantı sandı). Aktarıcının restore_state'i ve
# toplanti-claude.py'nin dosya seçimi denenir.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yan-dosya.py      (kaldı → çıkış 1; ~5 sn)
import datetime, json, os, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8778)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-yd-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
g = datetime.date.today().strftime("%Y-%m-%d"); kok = os.path.join(canli, f"{g}-0338-Deneme")
open(kok + ".md", "w").write("# Deneme\n"); open(kok + ".jsonl", "w").write(json.dumps({"id": "a/1", "speaker": "Ali K", "time": "03:38", "text": "deneme", "at": datetime.datetime.now().isoformat()}) + "\n")
time.sleep(0.05); open(kok + ".ceviri.jsonl", "w").write(json.dumps({"id": "a/1", "ceviri": "test"}) + "\n")  # en yeni dosya yan dosya
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
try:
    for _ in range(50):
        if "çalışıyor" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): break
        time.sleep(0.2)
    log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    bak("aktarıcı yeniden başlayınca toplantı dökümüne bağlandı (yan dosyaya değil)", f"{g}-0338-Deneme.md" in log and "ceviri" not in log.split("Durum kuruldu", 1)[-1].split("\n", 1)[0])
    o = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", "http://127.0.0.1:1", "ekranlar"], capture_output=True, text=True, env=env, timeout=30)
    bak("toplanti-claude.py en yeni toplantıyı seçti (…ceviri.md değil)", f"{g}-0338-Deneme.md" in (o.stdout + o.stderr) and "ceviri" not in (o.stdout + o.stderr))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("yan dosya: ✓ hepsi geçti" if not hata else f"yan dosya: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
