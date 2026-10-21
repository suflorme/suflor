#!/usr/bin/env python3
# Kutuya yazılan (pano, mini pano, eklenti penceresi) not mu soru mu: toplantı oturumu (izle) izliyorsa Claude karar verir — yazı dökümde
# not olarak kalır ve sorular.jsonl'e tur "girdi" ile düşer (izle GİRDİ olayı); izlemiyorsa eski kural (başta ? → soru). ⌘Enter (soru: true)
# her zaman soru. Yalıtılmış aktarıcıya sırayla gönderir; yanıtı, sorular.jsonl'i ve dökümü denetler.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/girdi.py      (kaldı → çıkış 1)
import glob, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-gi-"); PORT = bos_port(8793); URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None, izle=False):
    h = {"X-Suflor-Anahtar": anahtar(), **({"X-Suflor-Istemci": "izle"} if izle else {})}
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET", headers=h)
    return json.load(urllib.request.urlopen(q, timeout=5))
sorular = lambda: [json.loads(l) for l in open(os.path.join(canli, "sorular.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(canli, "sorular.jsonl")) else []
dokum = lambda: "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(canli, "*.md")))
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    istek("/ingest", {"meeting": {"title": "Girdi Deneme"}, "source": "transcript", "entries": [{"id": "s/1", "speaker": "Deniz", "time": "10:00", "text": "başlıyoruz"}]})
    a = istek("/girdi", {"text": "bütçe tablosu cuma günü hazır olacak"})
    kontrol("Claude izlemiyor: düz yazı not", a.get("tur") == "not" and not sorular())
    b = istek("/girdi", {"text": "? geçen hafta ne karar vermiştik"})
    kontrol("Claude izlemiyor: başta ? soru (eski kural yedek)", b.get("tur") == "soru" and sorular()[-1].get("tur") is None)
    istek("/status", izle=True)  # izle yoklaması: toplantı oturumu izliyor
    c = istek("/girdi", {"text": "teslim tarihi neydi"})
    q = sorular()[-1]
    kontrol("Claude izliyor: kutudaki yazı Claude'a iletildi (tur girdi)", c.get("tur") == "iletildi" and q.get("tur") == "girdi" and q.get("text") == "teslim tarihi neydi")
    kontrol("iletilen yazı dökümde not olarak var, ayrıca 'CLAUDE’A SORU' satırı yok", "teslim tarihi neydi" in dokum() and "CLAUDE’A SORU** | teslim" not in dokum())
    kontrol("panoda bekleyen soru olarak görünür (45 sn içinde)", any(x.get("id") == q["id"] for x in istek("/cards").get("questions", [])))
    d = istek("/girdi", {"text": "bunu kesin sor", "soru": True})
    kontrol("⌘Enter (soru: true) Claude izlerken de doğrudan soru", d.get("tur") == "soru" and sorular()[-1].get("tur") is None)
    e = istek("/girdi", {"text": "https://example.com/plan"})
    kontrol("bağlantı yazılınca bağlam kaynağı olur, Claude'a girdi olarak gitmez", e.get("tur") == "bağlam" and sorular()[-1].get("tur") is None)
    kontrol("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"girdi: {sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
