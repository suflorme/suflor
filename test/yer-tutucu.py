#!/usr/bin/env python3
# Faz B (v0.149.0): toplantının adı geç gelse de (ilk satırlar adsız) döküm tek dosyada, dosya adı açılışta bir kez verilir ve değişmez (eski yer tutucu
# birleştirme dosyayı yeniden adlandırıyordu). Eklentinin gönderdiği sayfa başlığı ("Haftalık Plan", "İkinci Toplantı") ad olmaz, yeni dosya açmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yer-tutucu.py      (kaldı → çıkış 1)
import glob, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-yt-"); PORT = bos_port(8794); URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
def anahtar():  # v0.14.0 yerel anahtar (aktarıcı açılınca yazar)
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None):
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                               headers={"X-Suflor-Anahtar": anahtar()})
    return json.load(urllib.request.urlopen(q, timeout=5))
def satir(i, metin, baslik=None):
    istek("/ingest", dict({"source": "transcript", "entries": [{"id": f"s/{i}", "speaker": "Deniz", "time": "10:00", "text": metin}]},
                          **({"meeting": {"title": baslik}} if baslik else {})))
hatalar = []
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    satir(1, "adsız ilk satır"); ilk = sorted(os.path.basename(f) for f in glob.glob(os.path.join(canli, "*.md")))
    satir(2, "adlı satır", "Haftalık Plan"); satir(3, "yeniden adsız"); satir(4, "başka başlıklı satır", "İkinci Toplantı")
    md = sorted(os.path.basename(f) for f in glob.glob(os.path.join(canli, "*.md")))
    if len(md) != 1 or md != ilk: hatalar.append(f"dosyalar: {ilk} → {md}")
    else:
        m = open(os.path.join(canli, md[0]), encoding="utf-8").read()
        for t in ("adsız ilk satır", "adlı satır", "yeniden adsız", "başka başlıklı satır"):
            if t not in m: hatalar.append(f"satır eksik: {t}")
        if "Haftalık" in md[0] or "İkinci" in md[0]: hatalar.append(f"sayfa başlığı dosya adına girdi: {md[0]}")
    s = istek("/status")
    if s.get("meeting") != (s.get("toplanti") or {}).get("ad") or s.get("meeting") in ("Haftalık Plan", "İkinci Toplantı"): hatalar.append(f"süren ad {s.get('meeting')!r}")
    if "Traceback" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): hatalar.append("aktarıcıda hata (relay.log)")
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"yer tutucu: {len(hatalar)} sorun" + "".join(f"\n  KALDI: {h}" for h in hatalar) if hatalar else "yer tutucu: ✓ ad geç gelse de tek dosya, dosya adı değişmedi, sayfa başlığı ad olmadı")
sys.exit(1 if hatalar else 0)
