#!/usr/bin/env python3
# Toplantı adı geç gelince döküm tek dosyada kalıyor mu (7 Ekim: ilk Whisper satırı adsız geldi, 1 satırlık "…-Toplantı.md" ayrı
# kaldı). Yalıtılmış aktarıcıya sırayla adsız, adlı, yeniden adsız ve başka adlı satır gönderir; dosyaları ve /status'u denetler.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yer-tutucu.py      (kaldı → çıkış 1)
import glob, json, os, shutil, subprocess, sys, tempfile, time, urllib.request

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-yt-"); PORT = 8794; URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
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
    satir(1, "adsız ilk satır"); satir(2, "adlı satır", "Haftalık Plan"); satir(3, "yeniden adsız")
    s = istek("/status")
    if s.get("meeting") != "Haftalık Plan": hatalar.append(f"adsız satırdan sonra süren ad {s.get('meeting')!r}")
    satir(4, "başka toplantı", "İkinci Toplantı")
    md = sorted(os.path.basename(f) for f in glob.glob(os.path.join(canli, "*.md")))
    if len(md) != 2 or "Toplantı.md" in [m[16:] for m in md]: hatalar.append(f"dosyalar: {md}")
    plan = [m for m in md if m.endswith("Haftalık-Plan.md")]
    if plan:
        m = open(os.path.join(canli, plan[0]), encoding="utf-8").read()
        if not m.startswith("# Canlı transkript — Haftalık Plan\n"): hatalar.append("başlık yeni adla güncellenmedi")
        for t in ("adsız ilk satır", "adlı satır", "yeniden adsız"):
            if t not in m: hatalar.append(f"satır eksik: {t}")
        if "başka toplantı" in m: hatalar.append("ikinci toplantının satırı birinciye yazıldı")
    if istek("/status").get("meeting") != "İkinci Toplantı": hatalar.append("ikinci toplantı süren toplantı olmadı")
    if "Traceback" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): hatalar.append("aktarıcıda hata (relay.log)")
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"yer tutucu: {len(hatalar)} sorun" + "".join(f"\n  KALDI: {h}" for h in hatalar) if hatalar else "yer tutucu: ✓ adsız ilk satırlar adı gelen toplantının dosyasında; ikinci toplantı ayrı")
sys.exit(1 if hatalar else 0)
