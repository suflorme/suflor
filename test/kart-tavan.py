#!/usr/bin/env python3
# Kart tavanı (v0.32.12): soruya bağlı olmayan SÖYLE/NOT araya en çok kart_tavan_sn'de bir girer; pencere içinde gelenler gizli bekler
# ve pencere dolunca birlikte görünür (kart atılmaz). DUR, CEVAP, onay ve fısıltılı kart beklemez. Yalıtılmış aktarıcı, tavan 3 sn.
# Aynı aktarıcıda sistem izi (v0.32.12): toplantı sürerken canli/sistem-izi.jsonl'e ısı/pil/bellek (test kipinde 2 sn'de bir).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kart-tavan.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-tavan-"); PORT = bos_port(8793); URL = f"http://127.0.0.1:{PORT}"; W = 3
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "proje"))
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "yok"),
           "kart_tavan_sn": W}, open(ay, "w"))
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_HIZLI="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=ENV)
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None):
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                               headers={"X-Suflor-Anahtar": anahtar()})
    try: return json.loads(urllib.request.urlopen(q, timeout=5).read())
    except urllib.error.HTTPError as e: return {"kod": e.code}
kart = lambda tur, metin, **k: istek("/card", dict({"kind": tur, "text": metin}, **k)).get("card") or {}
gorunen = lambda: [c["id"] for c in istek("/cards").get("cards", [])]
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    istek("/ping", {"meeting": {"title": "Tavan deneme"}, "call": True, "panel": True, "rows": 1})
    istek("/ingest", {"meeting": {"title": "Tavan deneme"}, "source": "transcript", "entries": [{"id": "t/1", "speaker": "Deniz T", "time": "10:00", "text": "merhaba"}]})
    a = kart("soyle", "Bütçeyi sor")
    kontrol("ilk SÖYLE hemen görünür", a.get("id") in gorunen() and not a.get("tavan_t"))
    b = kart("not", "Rakam teklifte farklı"); c = kart("soyle", "Takvimi netleştir")
    g = gorunen()
    kontrol("pencere içindeki NOT ve SÖYLE gizli", b["id"] not in g and c["id"] not in g)
    kontrol("ikisi aynı toplu gösterimde (aynı tavan_t, ~3 sn sonra)", b.get("tavan_t") and b["tavan_t"] == c.get("tavan_t") and 1 < b["tavan_t"] - time.time() <= W)
    d = kart("dur", "Şifreyi okuma"); q = istek("/ask", {"text": "kaç kişi?"}).get("question", {}).get("id")
    e = kart("cevap", "Sekiz kişi", reply_to=q); f = kart("soyle", "Evet de", fisilti="evet de"); o = kart("soyle", "Toplantıyı kaydet", onay=True)
    s = kart("soyle", "Fiyatı sor", reply_to=q)
    g = gorunen()
    kontrol("DUR, CEVAP, fısıltılı, onay ve soruya bağlı SÖYLE beklemez", all(x["id"] in g and not x.get("tavan_t") for x in (d, e, f, o, s)))
    time.sleep(max(0, b["tavan_t"] - time.time()) + 0.3)
    g = gorunen()
    kontrol("pencere dolunca bekleyenler birlikte göründü (kart kaybolmaz)", b["id"] in g and c["id"] in g)
    h = kart("not", "Yeni bilgi")
    kontrol("toplu gösterimin hemen ardından gelen kart yeniden bekler", h.get("tavan_t") and h["id"] not in gorunen() and h["tavan_t"] - time.time() > 1.5)
    iz_yol = os.path.join(canli, "sistem-izi.jsonl")
    si = [json.loads(l) for l in open(iz_yol)] if os.path.exists(iz_yol) else []
    kontrol(f"sistem izi toplantıda yazıldı (ısı, güç, boş bellek) → {si[-1] if si else None}",
            bool(si) and all(k in si[-1] for k in ("isi", "guc", "bellek_bos")) and si[-1]["isi"] in (0, 1, 2, 3))
    tc = subprocess.run([sys.executable, "toplanti-claude.py", "--dir", canli, "--relay", URL, "kart", "soyle", "Başka soru"], cwd=T, capture_output=True, text=True, env=ENV)
    kontrol("tc kart: 'TAVAN: n sn sonra görünür' der", "TAVAN:" in tc.stdout and "sn sonra görünür" in tc.stdout)
    md = "".join(open(os.path.join(canli, x), encoding="utf-8").read() for x in os.listdir(canli) if x.endswith(".md"))
    kontrol("dökümde bekleyen kart ⏳ işaretli", "Rakam teklifte farklı | ⏳ tavan |" in md)
finally:
    r.terminate()
    try: r.wait(5)
    except subprocess.TimeoutExpired: r.kill()
    shutil.rmtree(T, ignore_errors=True)
print("GEÇTİ" if not hatalar else f"KALDI: {len(hatalar)} — " + "; ".join(hatalar))
sys.exit(1 if hatalar else 0)
