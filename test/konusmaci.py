#!/usr/bin/env python3
# Toplantı sonu konuşmacı yeniden etiketleme (v0.24.0): yalıtılmış aktarıcıya üç karşı konuşmacının Whisper satırlarını ses iziyle (yapay,
# kişi başına taban + gürültü) ve iki kişinin altyazı satırlarını gönderir. Canlı adlar bilerek karışık. Denetim: ses izi .sesizi.log'a gider,
# .jsonl'e girmez · `konusmaci` her kişiyi tek kümeye ve altyazı adına bağlar, altyazısız kişi "Karşı taraf 1" · .jsonl değişmez · `dokum --goster`
# düzeltilmiş adları kullanır · `--geri` eşlemeyi kaldırır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konusmaci.py      (kaldı → çıkış 1; whisper-venv gerekir)
import base64, datetime, json, os, random, shutil, subprocess, sys, tempfile, time, urllib.request
import struct

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-kn-"); PORT = 8793; URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None):
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                               headers={"X-Suflor-Anahtar": anahtar()})
    return json.load(urllib.request.urlopen(q, timeout=5))
def tc(*a):
    return subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", URL, *a],
                          capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=120)
random.seed(7)
def birim(v): n = sum(x * x for x in v) ** 0.5; return [x / n for x in v]
TABAN = {k: birim([random.gauss(0, 1) for _ in range(192)]) for k in "ABC"}
def iz(k):  # float16 base64 (işçinin gönderdiği biçim)
    v = birim([t + random.gauss(0, 0.04) for t in TABAN[k]]); return base64.b64encode(struct.pack(f"<{len(v)}e", *v)).decode()
utc = lambda t: datetime.datetime.utcfromtimestamp(t).isoformat(timespec="milliseconds") + "Z"
BASLIK = "Konuşmacı Deneme"
# sıra: A ve B dönüşümlü, C sonda; canlı adlar karışık (A'nın bir kısmı "Karşı taraf 2", B'nin bir kısmı A'nın adı)
SIRA = list("ABABABABABAB") + list("CCCC")
CANLI = {"A": ["Ayşe Yılmaz", "Karşı taraf 2", "Ayşe Yılmaz", "Karşı taraf 2", "Ayşe Yılmaz", "Ayşe Yılmaz"],
         "B": ["Ayşe Yılmaz", "Bora Kaya", "Karşı taraf 3", "Bora Kaya", "Bora Kaya", "Ayşe Yılmaz"], "C": ["Karşı taraf 2"] * 4}
ALTYAZI = {"A": "Ayşe Yılmaz", "B": "Bora Kaya"}  # C'nin altyazısı yok
hatalar = []
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    t = time.time() - 600; say = {k: 0 for k in "ABC"}; gercek = {}
    for n, k in enumerate(SIRA):
        t0, t1 = t, t + 3.0; t += 15.0; i = f"wh/karsi/{n}"; gercek[i] = k
        e = {"id": i, "speaker": CANLI[k][say[k]], "time": "10:00", "text": f"{k} kişisinin {say[k] + 1}. cümlesi", "kanal": "karsi", "t0": t0, "t1": t1, "iz": iz(k)}
        say[k] += 1
        istek("/ingest", {"meeting": {"title": BASLIK}, "source": "whisper", "capturedAt": utc(t1), "entries": [e]})
        if k in ALTYAZI:
            istek("/ingest", {"meeting": {"title": BASLIK}, "source": "captions", "capturedAt": utc(t1 + 3),
                              "entries": [{"id": f"cap/{n}", "speaker": ALTYAZI[k], "time": "10:00", "text": "altyazı"}]})
    # iki kişili canlı parça (hızlı söz devri): parça izi A'ya yakın, bölümler A (2 sn, 3 sözcük) + B (1,6 sn, 2 sözcük); canlı ad A
    istek("/ingest", {"meeting": {"title": BASLIK}, "source": "whisper", "capturedAt": utc(t + 4), "entries": [
        {"id": "wh/karsi/karisik", "speaker": "Ayşe Yılmaz", "time": "10:04", "text": "bir iki üç dört beş", "kanal": "karsi", "t0": t, "t1": t + 4,
         "iz": iz("A"), "bol": [{"s": 0.0, "e": 2.0, "n": 3, "iz": iz("A")}, {"s": 2.4, "e": 4.0, "n": 2, "iz": iz("B")}]}]})
    t += 15
    istek("/ingest", {"meeting": {"title": BASLIK}, "source": "whisper", "capturedAt": utc(t), "entries": [
        {"id": "wh/ben/1", "speaker": "Kullanıcı", "time": "10:05", "text": "ben kanalı", "kanal": "ben", "t0": t, "t1": t + 2}]})
    time.sleep(0.5)
    md = next(f for f in os.listdir(canli) if f.endswith(".md") and f[:2] == "20")
    kok = os.path.join(canli, md[:-3])
    jl_once = open(kok + ".jsonl", encoding="utf-8").read()
    if '"iz"' in jl_once: hatalar.append(".jsonl'e ses izi girdi")
    try: izs = [json.loads(l) for l in open(kok + ".sesizi.log", encoding="utf-8")]
    except OSError: izs = []
    if len(izs) != len(SIRA) + 1: hatalar.append(f".sesizi.log {len(izs)} satır (beklenen {len(SIRA) + 1})")
    if not any(x.get("bol") for x in izs): hatalar.append("bölüm izleri .sesizi.log'a yazılmadı")
    if any(x["id"] == "wh/ben/1" for x in izs): hatalar.append("ben kanalının izi yazıldı")
    o = tc("konusmaci", md)
    if o.returncode: hatalar.append(f"konusmaci çıkış {o.returncode}: {o.stderr[-300:]}")
    print(o.stdout.strip())
    try: es = json.load(open(kok + ".konusmaci.json", encoding="utf-8"))
    except Exception as x: es = {"ad": {}}; hatalar.append(f"eşleme dosyası yok ({x})")
    bek = {"A": "Ayşe Yılmaz", "B": "Bora Kaya", "C": "Karşı taraf 1"}
    yanlis = [(i, es["ad"].get(i), bek[k]) for i, k in gercek.items() if es["ad"].get(i) != bek[k]]
    if yanlis: hatalar.append(f"yanlış ad {len(yanlis)}: {yanlis[:4]}")
    if len(es.get("kume") or {}) != 3: hatalar.append(f"küme sayısı {len(es.get('kume') or {})} (beklenen 3)")
    if "wh/ben/1" in es["ad"]: hatalar.append("ben satırı eşlemeye girdi")
    if es["ad"].get("wh/karsi/karisik") != "Ayşe Yılmaz": hatalar.append(f"iki kişili satırın ana adı {es['ad'].get('wh/karsi/karisik')!r} (beklenen süresi uzun olan Ayşe)")
    if [b.get("ad") for b in (es.get("bol") or {}).get("wh/karsi/karisik", [])] != ["Ayşe Yılmaz", "Bora Kaya"]: hatalar.append(f"iki kişili satır bölünmedi: {es.get('bol')}")
    if open(kok + ".jsonl", encoding="utf-8").read() != jl_once: hatalar.append(".jsonl değişti")
    d = tc("dokum", md, "--goster")
    if d.returncode: hatalar.append(f"dokum çıkış {d.returncode}: {d.stderr[-300:]}")
    for ad in ("Ayşe Yılmaz", "Bora Kaya", "Karşı taraf 1"):
        if ad not in d.stdout: hatalar.append(f"dökümde yok: {ad}")
    if "Karşı taraf 2" in d.stdout or "Karşı taraf 3" in d.stdout: hatalar.append("dökümde eski canlı ad kaldı")
    sat = [l for l in d.stdout.splitlines() if "bir iki üç" in l or "dört beş" in l]
    if not (len(sat) == 2 and "Ayşe Yılmaz" in sat[0] and "bir iki üç" in sat[0] and "dört" not in sat[0] and "Bora Kaya" in sat[1] and "dört beş" in sat[1]):
        hatalar.append(f"dökümde iki kişili satır bölünmedi: {sat}")
    tc("konusmaci", md, "--geri")
    if os.path.exists(kok + ".konusmaci.json"): hatalar.append("--geri eşlemeyi kaldırmadı")
finally:
    r.terminate(); r.wait(5)
    if not hatalar: shutil.rmtree(T, ignore_errors=True)
print("✓ konuşmacı yeniden etiketleme" if not hatalar else "✗ " + "\n✗ ".join(hatalar) + f"\n(deneme klasörü: {T})")
sys.exit(1 if hatalar else 0)
