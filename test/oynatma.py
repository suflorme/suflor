#!/usr/bin/env python3
# Suflor.me — döküm oynatma regresyon testi (Faz 2 güvence ağı).
# Yapay bir toplantıyı (oynatma-veri.json) yalıtılmış bir aktarıcıya (relay.py) ve izle'ye (toplanti-claude.py) hızlandırılmış
# saatle oynatır; aktarıcının yazdığı dosyaları, HTTP yanıtlarını (pano HTML'i dahil) ve izle olaylarını normalleştirip
# test/oynatma-beklenen.json ile karşılaştırır. Gerçek _canli, ayar, dizin ve canlı aktarıcıya dokunmaz (geçici klasör, port 8799).
#   python3 test/oynatma.py            karşılaştır (fark varsa çıkış kodu 1)
#   python3 test/oynatma.py --kaydet   beklenen sonucu yeniden yaz (bilinçli davranış değişikliğinden sonra)
#   --hiz 20 (sahte saat katsayısı) · --sakla (geçici klasörü silme) · --port 8799
import argparse, collections, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
BURA = os.path.dirname(os.path.abspath(__file__)); KOK = os.path.dirname(BURA)
ap = argparse.ArgumentParser(); ap.add_argument("--kaydet", action="store_true"); ap.add_argument("--hiz", type=float, default=20)
ap.add_argument("--sakla", action="store_true"); ap.add_argument("--port", type=int, default=8799)
A = ap.parse_args(); K = A.hiz; PORT = A.port; URL = f"http://127.0.0.1:{PORT}"
VERI = json.load(open(os.path.join(BURA, "oynatma-veri.json"), encoding="utf-8"))
BEKLENEN = os.path.join(BURA, "oynatma-beklenen.json")

# Hızlandırılmış saat: aktarıcı ve izle aynı sahte saati kullanır (sahte = T0 + (gerçek - T0) * K)
SAAT = r'''import os, sys, time, datetime, runpy, threading
T0 = float(os.environ["HIZ_T0"]); K = float(os.environ["HIZ_K"])
_t, _s, _m = time.time, time.sleep, time.monotonic; M0 = _m()
time.time = lambda: T0 + (_t() - T0) * K
time.monotonic = lambda: M0 + (_m() - M0) * K
time.sleep = lambda s: _s(max(0, s) / K)
time.localtime = (lambda lt: (lambda s=None: lt(time.time() if s is None else s)))(time.localtime)
class FDT(datetime.datetime):
    @classmethod
    def now(cls, tz=None): return cls.fromtimestamp(time.time(), tz)
    @classmethod
    def today(cls): return cls.fromtimestamp(time.time())
class FD(datetime.date):
    @classmethod
    def today(cls): return cls.fromtimestamp(time.time())
datetime.datetime = FDT; datetime.date = FD
sys.dont_write_bytecode = True
sys.argv = sys.argv[1:]; sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
runpy.run_path(sys.argv[0], run_name="__main__")
'''

def kur(T):
    kod = os.path.join(T, "kod"); os.makedirs(kod)
    for f in ("relay.py", "toplanti-claude.py", "baglam.py", "teshis.py", "manifest.json"):
        if os.path.exists(os.path.join(KOK, f)): shutil.copy(os.path.join(KOK, f), kod)
    for d in ("marka", "pano"):
        if os.path.isdir(os.path.join(KOK, d)): shutil.copytree(os.path.join(KOK, d), os.path.join(kod, d))
    open(os.path.join(kod, "saat.py"), "w").write(SAAT)
    uyg = os.path.join(T, "uygulama"); canli = os.path.join(uyg, "canli")
    for d in (canli, os.path.join(T, "proje"), os.path.join(T, "ortak")): os.makedirs(d)
    ayar = {"alan": "Test", "ad": VERI["ben"], "port": PORT, "uygulama": uyg, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "ortak"),
            "yerel_ses": False, "teshis": False, "dil": "tr"}
    json.dump(ayar, open(os.path.join(T, "ayar.json"), "w"), ensure_ascii=False)
    return kod, canli

def yaz_baslangic(canli, t0):
    loc = lambda s: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0 + s))
    json.dump({"title": VERI["baslik"], "items": VERI["gundem"], "baslangic": loc(0), "bitis": loc(20 * 60), "dil": "tr"},
              open(os.path.join(canli, "agenda.json"), "w"), ensure_ascii=False)
    json.dump({"toplanti": VERI["baslik"], "kartlar": VERI["hazir"]}, open(os.path.join(canli, "hazir.json"), "w"), ensure_ascii=False)
    json.dump({"terimler": VERI["sozluk"]}, open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)

def istek(yol, govde=None, bas=None):
    r = urllib.request.Request(URL + yol, data=None if govde is None else json.dumps(govde).encode(), method="GET" if govde is None else "POST",
                               headers=dict(bas or {}, **({"Content-Type": "application/json"} if govde is not None else {})))
    return urllib.request.urlopen(r, timeout=5).read()

def bekle_hazir():
    for _ in range(100):
        try: istek("/status"); return
        except Exception: time.sleep(0.1)
    raise SystemExit("aktarıcı açılmadı")

# --- Normalleştirme: zaman, kimlik ve sürüm gibi her koşuda değişen değerler maskelenir --------------------------------
MASKE = [(re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?"), "<AN>"),
         (re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}"), "<TARIH>"), (re.compile(r"\d{4}-\d{2}-\d{2}"), "<GUN>"),
         (re.compile(r"\b[0-9a-f]{32}\b"), "<ANAHTAR>"), (re.compile(r"\b[kqe]\d{13}[0-9a-f]{0,4}\b"), "<ID>"), (re.compile(r"\b1[6-9]\d{8}(\.\d+)?\b"), "<EPOCH>"),
         (re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b"), "<SAAT>")]
def maskele(s, surum=None):
    if surum: s = s.replace(surum, "<SURUM>")
    for rx, y in MASKE: s = rx.sub(y, s)
    return s
def sekil(o):  # JSON'un anahtar ve tür iskeleti (değerler her koşuda değişir)
    if isinstance(o, dict): return {maskele(k): sekil(v) for k, v in sorted(o.items())}
    if isinstance(o, list): return [sekil(o[0])] if o else []
    return type(o).__name__
OLAY_RX = re.compile(r"^([A-ZÇĞİÖŞÜ]{2,}(?: (?:[A-ZÇĞİÖŞÜ]{2,}|▶))*)")
def olay_turu(l):
    m = OLAY_RX.match(l); return m.group(1).strip() if m else None

def kos():
    T = tempfile.mkdtemp(prefix="suflor-oynatma-"); kod, canli = kur(T)
    t0 = time.time(); yaz_baslangic(canli, t0)
    env = dict(os.environ, HIZ_T0=str(t0), HIZ_K=str(K), PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"))
    py = sys.executable
    rl = subprocess.Popen([py, "saat.py", "relay.py", "--dir", canli, "--port", str(PORT)], cwd=kod, env=env,
                          stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    iz = None
    try:
        bekle_hazir()
        iz = subprocess.Popen([py, "-u", "saat.py", "toplanti-claude.py", "--dir", canli, "--relay", URL, "izle"], cwd=kod, env=env,
                              stdout=open(os.path.join(T, "izle.log"), "w"), stderr=subprocess.STDOUT)
        tc = lambda *a: subprocess.run([py, "saat.py", "toplanti-claude.py", "--dir", canli, "--relay", URL, *a], cwd=kod, env=env,
                                        capture_output=True, text=True, timeout=20)
        M = {"title": VERI["baslik"]}; n = 0; son_ping = 0; sorular = []; son_kart = None; hatalar = []
        for o in sorted(VERI["olaylar"], key=lambda o: o["t"]):
            hedef = t0 + o["t"] / K
            while time.time() < hedef:
                if time.time() - son_ping > 0.5: istek("/ping", {"meeting": M, "panel": True, "rows": n, "call": True, "ver": "test"}); son_ping = time.time()
                time.sleep(min(0.05, max(0, hedef - time.time())))
            if "satir" in o:
                n += 1; kim, metin = o["satir"]; sn = o["t"]
                istek("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": f"o/{n}", "speaker": kim, "time": f"{sn // 60:02d}:{sn % 60:02d}", "text": metin}]})
            elif "whisper" in o:
                n += 1; kim, kanal, metin, sure = o["whisper"]; sn = int(o["t"]); t0w = t0 + o["t"]
                istek("/ingest", {"meeting": M, "source": "whisper", "entries": [{"id": f"w/{n}", "speaker": kim, "time": f"{sn // 60:02d}:{sn % 60:02d}", "text": metin,
                                                                               "kanal": kanal, "t0": t0w, "t1": t0w + sure}]})
            elif "soru" in o:
                q = json.loads(istek("/ask", {"text": o["soru"]})).get("question") or {}; sorular.append(q.get("id"))
            elif "not" in o: istek("/note", {"meeting": M, "text": o["not"]})
            elif "komut" in o: istek("/komut", {"tur": o["komut"], "meeting": M})
            elif "kart" in o:
                a = [x.replace("SORU1", sorular[0] if sorular else "") for x in o["kart"]]
                r = tc("kart", *a); m = re.search(r"kart gönderildi: (\S+)", r.stdout)
                if m: son_kart = son_kart or m.group(1)  # ✓ ilk karta (eski adla gönderilen "sor")
                else: hatalar.append("kart: " + (r.stdout + r.stderr)[-300:])
            elif "etiket" in o:
                r = tc("etiket", *o["etiket"])
                if r.returncode: hatalar.append("etiket: " + r.stderr[-300:])
            elif "ack" in o and son_kart: istek("/card-ack", {"id": son_kart, "status": "yapildi"})
            elif "gundem" in o:
                r = tc("gundem", str(o["gundem"]))
                if r.returncode: hatalar.append("gundem: " + r.stderr[-300:])
            elif "acik" in o:
                r = tc("acik", "ekle", *o["acik"])
                if r.returncode: hatalar.append("acik: " + r.stderr[-300:])
        # toplantı biter: izle'nin son paketi için 60 sahte sn daha nabız, sonra 3 sahte dk panel kapalı
        for panel, sure in ((True, 60), (False, 180)):
            son = time.time() + sure / K
            while time.time() < son: istek("/ping", {"meeting": M, "panel": panel, "rows": n, "call": panel, "ver": "test"}); time.sleep(0.25)
        surum = json.loads(istek("/status"))["surum"]
        http = {}
        for yol in ("/", "/hazirlik", "/mini"):
            try: b = istek(yol).decode()
            except Exception as e: http[yol] = f"HATA {e}"; continue
            http[yol] = {"uzunluk": len(maskele(b, surum)), "sha": hashlib.sha256(maskele(b, surum).encode()).hexdigest()[:16]}
        http["/status"] = sekil(json.loads(istek("/status"))); http["/cards"] = sekil(json.loads(istek("/cards")))
        http["/agenda"] = json.loads(istek("/agenda"))
        for k in ("baslangic", "bitis"): http["/agenda"][k] = "<AN>"
        http["/hazirlik.json"] = sekil(json.loads(istek("/hazirlik.json")))
    finally:
        for p in (iz, rl):
            if p: p.terminate()
        for p in (iz, rl):
            if p:
                try: p.wait(5)
                except subprocess.TimeoutExpired: p.kill()
    DEGISKEN = {"heartbeat.json", "kart-anahtari.txt", "olcum.jsonl"}  # anahtar rastgele, nabız/ölçüm zamana bağlı
    dosyalar = {}
    for kok, _, fs in os.walk(canli):
        for f in sorted(fs):
            yol = os.path.relpath(os.path.join(kok, f), canli)
            if f in DEGISKEN: dosyalar[maskele(yol)] = "<var>"; continue
            try: dosyalar[maskele(yol)] = maskele(open(os.path.join(kok, f), encoding="utf-8").read(), surum).splitlines()
            except UnicodeDecodeError: dosyalar[maskele(yol)] = "<ikili>"
    izle = [l.rstrip("\n") for l in open(os.path.join(T, "izle.log"), encoding="utf-8")]
    turler = collections.Counter(t for t in map(olay_turu, izle) if t)
    metinler = [o["satir"][1] for o in VERI["olaylar"] if "satir" in o] + [o["whisper"][2] for o in VERI["olaylar"] if "whisper" in o]
    gorulen = sum(1 for m in metinler if any(m[:40] in l for l in izle))
    hata_izle = [l for l in izle if "Traceback" in l or "Error" in l]
    hata_relay = [l for l in open(os.path.join(T, "relay.log"), encoding="utf-8") if "Traceback" in l]
    sonuc = {"surum_maskeli": True, "dosyalar": dict(sorted(dosyalar.items())), "http": http, "izle_turleri": dict(sorted(turler.items())),
             "izle_satir_kapsami": f"{gorulen}/{len(metinler)}", "hatalar": hatalar + hata_izle + [l.strip() for l in hata_relay]}
    if A.sakla: print("geçici klasör:", T)
    else: shutil.rmtree(T, ignore_errors=True)
    return sonuc, surum

def yol_farki(x, y, yol=""):  # iki JSON arasındaki farklı yollar (kısa rapor için)
    if isinstance(x, dict) and isinstance(y, dict):
        return [f for k in sorted(set(x) | set(y)) for f in yol_farki(x.get(k), y.get(k), f"{yol}.{k}")]
    return [] if x == y else [f"{yol or '.'}: {json.dumps(x, ensure_ascii=False)[:120]} → {json.dumps(y, ensure_ascii=False)[:120]}"]
def karsilastir(b, s):
    f = []
    for k in sorted(set(b["dosyalar"]) | set(s["dosyalar"])):
        x, y = b["dosyalar"].get(k), s["dosyalar"].get(k)
        if x == y: continue
        if x is None or y is None: f.append(f"dosya {'yeni' if x is None else 'kayıp'}: {k}"); continue
        if isinstance(x, list) and isinstance(y, list):
            import difflib
            d = [l for l in difflib.unified_diff(x, y, lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]
            f.append(f"dosya farklı: {k}\n    " + "\n    ".join(d[:12]) + ("\n    …" if len(d) > 12 else ""))
        else: f.append(f"dosya farklı: {k}")
    for k in sorted(set(b["http"]) | set(s["http"])):
        if b["http"].get(k) != s["http"].get(k): f.append(f"http farklı: {k}\n    " + "\n    ".join(yol_farki(b["http"].get(k), s["http"].get(k))[:12]))
    bt, st = b["izle_turleri"], s["izle_turleri"]
    for k in sorted(set(bt) | set(st)):
        x, y = bt.get(k, 0), st.get(k, 0)
        # paket sınırları gerçek zamanlamaya bağlı: SATIRLAR/SÜRE/DURUM sayısında oynama olur; tür kaybı ya da büyük fark hatadır
        if (x == 0) != (y == 0) or abs(x - y) > max(2, 0.4 * max(x, y)): f.append(f"izle olayı {k}: önce {x}, şimdi {y}")
    if b["izle_satir_kapsami"] != s["izle_satir_kapsami"]: f.append(f"izle satır kapsamı: önce {b['izle_satir_kapsami']}, şimdi {s['izle_satir_kapsami']}")
    if s["hatalar"]: f.append("hatalar:\n    " + "\n    ".join(s["hatalar"][:10]))
    return f

if __name__ == "__main__":
    t = time.time(); s, surum = kos()
    print(f"oynatma: aktarıcı v{surum}, {round(time.time() - t)} sn · izle olayları {s['izle_turleri']} · satır kapsamı {s['izle_satir_kapsami']}")
    if A.kaydet:
        json.dump(s, open(BEKLENEN, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("beklenen sonuç yazıldı:", BEKLENEN)
        if s["hatalar"]: print("UYARI — hatalar:", *s["hatalar"], sep="\n  ")
        sys.exit(0)
    if not os.path.exists(BEKLENEN): sys.exit("beklenen sonuç yok: önce --kaydet")
    fark = karsilastir(json.load(open(BEKLENEN, encoding="utf-8")), s)
    if fark: print("FARK VAR:"); print("\n".join("  " + x for x in fark)); sys.exit(1)
    print("GEÇTİ: dosyalar, HTTP yanıtları ve izle olayları beklenenle aynı")
