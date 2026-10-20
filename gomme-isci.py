#!/usr/bin/env python3
# Anlama göre arama işçisi (proje hazırlığı T4; planlar/proje-hazirligi.md §2 Adım 3). <ortak>/cevir-venv'de çalışır; model
# intfloat/multilingual-e5-base (MIT) <ortak>/anlam-modeller'dan, ağ kapalı. İki kip (baglam.py yönetir):
#   --dizinle: dizin.sqlite'taki aranabilir parçaların (baglam.py'nin verdiği koşul) gömmesi eksik olanları 2.048'lik paketlerle hesaplar;
#              her paket diske yazılır (<uygulama>/gomme/pNNNNN.npy float16 + .id.npy + .crc.npy), en çok --paket-sinir paketten sonra
#              çıkar (bellek tazelensin; baglam.py yeniden açar), toplantı başlarsa (nabız dosyası) paketler arasında durur. Kaldığı yerden sürer.
#   --sunucu:  modeli ve gömmeleri bellekte tutar, Unix soketinden sorgu alır: {"q", "k"} → {"sonuc": [[parça no, benzerlik], …], "ms"}.
#              Tek kopya (kilit dosyası); gömme klasörü değişince yeniden yükler; --bos-dk dakika sorgu gelmezse kapanır.
# Gömmenin hangi parçaya ait olduğu parça no + metin CRC'siyle denetlenir (silinen parçanın numarası yeni parçaya verilirse eski gömme kullanılmaz).
import argparse, fcntl, glob, json, os, socket, sqlite3, sys, time, zlib

ORTAK = os.environ.get("SUFLOR_ORTAK") or "/Users/Shared/Suflor"
MODEL_KOK = os.path.join(ORTAK, "anlam-modeller")
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1"); os.environ.setdefault("HF_HOME", MODEL_KOK)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
MODEL = "intfloat/multilingual-e5-base"; PAKET = 2048
SURUM = 2  # gömme biçimi (2: parçanın başında dosya başlığı — gerçek proje ölçümünde anlam araması 17 → 24/46); değişince eski gömmeler silinir
def gunluk(*m): print(time.strftime("%H:%M:%S"), *m, file=sys.stderr, flush=True)

def model_ac():
    import torch
    from sentence_transformers import SentenceTransformer
    aygit = "mps" if torch.backends.mps.is_available() else "cpu"
    m = SentenceTransformer(MODEL, device=aygit); m.max_seq_length = 512
    if aygit == "mps": m = m.half()
    return m, aygit
def crc(t): return zlib.crc32(t.encode("utf-8", "replace"))

def mevcut(klasor):
    import numpy as np
    ids, crcs, dosya = [], [], []
    for f in sorted(glob.glob(os.path.join(klasor, "p*.id.npy"))):
        k = f[:-len(".id.npy")]
        try: i, c = np.load(f), np.load(k + ".crc.npy")
        except (OSError, ValueError): continue
        ids.append(i); crcs.append(c); dosya.append(k)
    return ids, crcs, dosya

def toplantida(nabiz):
    try:
        h = json.load(open(nabiz, encoding="utf-8"))
        return bool((h.get("meeting") or (h.get("extension") or {}).get("call")) and time.time() - os.stat(nabiz).st_mtime < 600)
    except (OSError, ValueError, AttributeError): return False

SIKISTIR_EN_AZ, SIKISTIR_ORAN = 2000, 0.3
def sikistir(a, ids, crcs, dosya):
    # v0.97.6 (sistem analizi §3.5): değişen/silinen parçanın eski gömmesi pakette kalıyordu (20 Ekim: 47.647 satırın 28.675'i, %60) — sunucu her açılışta
    # hepsini okuyup ayıklıyordu. Eski satır ≥ SIKISTIR_EN_AZ ve ≥ %30 ise geçerli satırlar (parça no + metin CRC'si tutan, her parçanın en yenisi) yeni
    # paketlere yazılır, eski paketler silinir. Sunucu durum.json değişince bir kez yeniden yükler (yazım bitmeden yüklemez).
    import numpy as np
    if not ids: return ids, crcs, dosya
    I, C = np.concatenate(ids), np.concatenate(crcs)
    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True); gecerli = {i: crc(t) for i, t in c.execute("SELECT id, metin FROM parca") if t}; c.close()
    tut = np.array([gecerli.get(int(i)) == int(cc) for i, cc in zip(I, C)], dtype=bool)
    _, ilk = np.unique(I[tut][::-1], return_index=True); sec = np.sort(np.flatnonzero(tut)[::-1][ilk])
    eski = len(I) - len(sec)
    if eski < SIKISTIR_EN_AZ or eski < SIKISTIR_ORAN * len(I): return ids, crcs, dosya
    E = np.vstack([np.load(k + ".npy") for k in dosya])
    if len(E) != len(I): gunluk("sıkıştırma atlandı: paket boyları tutmuyor"); return ids, crcs, dosya
    no = max(int(os.path.basename(k)[1:6]) for k in dosya) + 1
    for b in range(0, len(sec), PAKET):
        j = sec[b:b + PAKET]; k = os.path.join(a.klasor, f"p{no:05d}")
        for son, veri in ((".npy", E[j]), (".crc.npy", C[j]), (".id.npy", I[j])):
            with open(k + son + ".tmp", "wb") as f: np.save(f, veri)
            os.replace(k + son + ".tmp", k + son)
        no += 1
    for k in dosya:  # önce .id.npy: yarım silinen paket görünmez
        for son in (".id.npy", ".crc.npy", ".npy"):
            try: os.remove(k + son)
            except OSError: pass
    json.dump({"t": time.time(), "model": MODEL, "surum": SURUM}, open(os.path.join(a.klasor, "durum.json"), "w"))
    gunluk(f"sıkıştırıldı: {len(I)} → {len(sec)} satır ({eski} eski), {len(dosya)} → {no - int(os.path.basename(dosya[-1])[1:6]) - 1} paket")
    ids, crcs, dosya = mevcut(a.klasor); return ids, crcs, dosya

def dizinle(a):
    import numpy as np
    os.makedirs(a.klasor, exist_ok=True)
    try: eski = json.load(open(os.path.join(a.klasor, "durum.json"))).get("surum")
    except (OSError, ValueError): eski = None
    if eski != SURUM:
        for f in glob.glob(os.path.join(a.klasor, "p*.npy")): os.remove(f)
    ids, crcs, dosya = sikistir(a, *mevcut(a.klasor))
    var = set(zip(np.concatenate(ids).tolist(), np.concatenate(crcs).tolist())) if ids else set()
    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    aday = [(i, t, b) for i, t, b in c.execute(f"SELECT p.id, p.metin, COALESCE(d.baslik, '') FROM parca p JOIN dosya d ON d.yol = p.yol WHERE {a.kosul} ORDER BY p.id")
            if t and (i, crc(t)) not in var]
    c.close()
    sonuc = {"eksik": len(aday), "yapilan": 0, "paket": 0, "durdu": None}
    if not aday: print(json.dumps(sonuc)); return 0
    m, aygit = model_ac(); t0 = time.time()
    no = max([int(os.path.basename(f)[1:6]) for f in glob.glob(os.path.join(a.klasor, "p*.id.npy"))] or [-1]) + 1
    import torch
    for b in range(0, len(aday), PAKET):
        if a.nabiz and toplantida(a.nabiz): sonuc["durdu"] = "toplantı"; break
        if sonuc["paket"] >= a.paket_sinir: sonuc["durdu"] = "paket sınırı"; break
        if a.sure and time.time() - t0 > a.sure: sonuc["durdu"] = "süre"; break
        p = aday[b:b + PAKET]
        E = m.encode(["passage: " + ((bas + " — ") if bas and bas not in t[:200] else "") + " ".join(t.split())[:2000] for _, t, bas in p], batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float16)
        if aygit == "mps": torch.mps.empty_cache()
        k = os.path.join(a.klasor, f"p{no:05d}")
        for son, veri in ((".npy", E), (".crc.npy", np.array([crc(t) for _, t, _ in p], dtype=np.int64)), (".id.npy", np.array([i for i, _, _ in p], dtype=np.int64))):
            with open(k + son + ".tmp", "wb") as f: np.save(f, veri)
            os.replace(k + son + ".tmp", k + son)  # .id.npy en son: yarım paket okunmaz
        no += 1; sonuc["paket"] += 1; sonuc["yapilan"] += len(p)
        gunluk(f"paket {no - 1}: {len(p)} parça · {sonuc['yapilan'] / (time.time() - t0):.0f} parça/sn")
    sonuc["sure_sn"] = round(time.time() - t0, 1)
    json.dump({"t": time.time(), "model": MODEL, "surum": SURUM}, open(os.path.join(a.klasor, "durum.json"), "w"))
    print(json.dumps(sonuc)); return 0

def sunucu(a):
    import numpy as np
    kilit = open(a.soket + ".kilit", "w")
    try: fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: gunluk("başka sunucu çalışıyor"); return 0
    m, aygit = model_ac(); m.encode(["query: ısınma"], normalize_embeddings=True); gunluk(f"model açıldı ({aygit})")  # ilk sorgu ~0,7 sn: açılışta
    # v0.92.1: tek kısa sorgu 20 Ekim'de MPS'te 72–75 ms, işlemcide 21–25 ms (yarım duyarlık GPU'ya tek tek gönderim pahalı). Sunucu yalnız sorgu gömer:
    # açılışta ikisi de ölçülür, hızlı olan kalır (toplu dizinleme MPS'te sürer). Gömmeler normalize; aygıt farkı benzerlikte yalnız sayısal gürültü.
    if aygit == "mps":
        def olc():
            ms = []
            for q in ("fatura ödeme listesi", "sunucu yedekleri kimde", "yarınki toplantının gündemi ne", "izin onayı", "kampanya bütçesi"):
                t = time.time(); m.encode(["query: " + q], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False); ms.append((time.time() - t) * 1000)
            return sorted(ms)[2]
        g = olc(); m = m.to("cpu").float(); m.encode(["query: ısınma"], normalize_embeddings=True); c_ = olc()
        if g < c_: m = m.to("mps").half()
        else: aygit = "cpu"
        gunluk(f"sorgu aygıtı: {aygit} (mps {g:.0f} ms, işlemci {c_:.0f} ms)")
    D = {"mt": None}
    def yukle():
        mt = os.stat(os.path.join(a.klasor, "durum.json")).st_mtime if os.path.exists(os.path.join(a.klasor, "durum.json")) else 0
        if D["mt"] == mt: return
        ids, crcs, dosya = mevcut(a.klasor)
        if not ids: D.update(mt=mt, v=(np.zeros((0, 768), np.float32), np.zeros(0, np.int64))); return
        I = np.concatenate(ids); C = np.concatenate(crcs); E = np.vstack([np.load(k + ".npy") for k in dosya]).astype(np.float32)
        c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        gecerli = {i: crc(t) for i, t in c.execute("SELECT id, metin FROM parca")}; c.close()
        tut = np.array([gecerli.get(int(i)) == int(cc) for i, cc in zip(I, C)], dtype=bool)
        _, ilk = np.unique(I[tut][::-1], return_index=True)  # aynı parça iki pakette: en yenisi
        sec = np.flatnonzero(tut)[::-1][ilk]
        D.update(mt=mt, v=(E[sec], I[sec])); gunluk(f"gömme yüklendi: {len(sec)} parça (eski/geçersiz {len(I) - len(sec)})")
    try: yukle()
    except Exception as e: gunluk(f"ilk yükleme hatası: {e.__class__.__name__} — 5 sn sonra yeniden")  # sıkıştırma o an paket siliyorsa
    D.setdefault("v", (np.zeros((0, 768), np.float32), np.zeros(0, np.int64)))
    import threading
    def izle():  # gömme klasörü değişince arka planda yeniden yükle (v0.70.2: sorgu içinde yükleme ~1 sn sürüyor, Konuş 0,25 sn bekleyip boş dönüyordu)
        while True:
            time.sleep(5)
            try: yukle()
            except Exception as e: gunluk(f"yeniden yükleme hatası: {e.__class__.__name__}")
    threading.Thread(target=izle, daemon=True).start()
    try: os.remove(a.soket)
    except OSError: pass
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.bind(a.soket); os.chmod(a.soket, 0o600); s.listen(8); s.settimeout(min(30, max(1, a.bos_dk * 60 / 2)))
    son = time.time()
    while time.time() - son < a.bos_dk * 60:
        try: b, _ = s.accept()
        except socket.timeout: continue
        try:
            b.settimeout(2); veri = b""
            while not veri.endswith(b"\n"):
                x = b.recv(65536)
                if not x: break
                veri += x
            o = json.loads(veri or b"{}"); t = time.time()
            E_, I_ = D["v"]
            if o.get("q") and len(I_):
                q = m.encode(["query: " + o["q"][:1000]], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0].astype(np.float32)
                sk = E_ @ q; k = min(int(o.get("k") or 100), len(sk)); en = np.argpartition(-sk, k - 1)[:k]; en = en[np.argsort(-sk[en])]
                cevap = {"sonuc": [[int(I_[j]), round(float(sk[j]), 4)] for j in en], "ms": round((time.time() - t) * 1000, 1)}
            else: cevap = {"sonuc": [], "parca": int(len(I_))}
            b.sendall((json.dumps(cevap) + "\n").encode()); son = time.time()
        except Exception as e:
            try: b.sendall((json.dumps({"hata": f"{e.__class__.__name__}: {str(e)[:120]}"}) + "\n").encode())
            except OSError: pass
        finally: b.close()
    gunluk("boşta kaldı, kapanıyor")
    try: os.remove(a.soket)
    except OSError: pass
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizinle", action="store_true"); ap.add_argument("--sunucu", action="store_true")
    ap.add_argument("--db", required=True); ap.add_argument("--klasor", required=True); ap.add_argument("--kosul", default="1")
    ap.add_argument("--nabiz"); ap.add_argument("--paket-sinir", type=int, default=4); ap.add_argument("--sure", type=float)
    ap.add_argument("--soket"); ap.add_argument("--bos-dk", type=float, default=30)
    a = ap.parse_args()
    sys.exit(dizinle(a) if a.dizinle else sunucu(a) if a.sunucu and a.soket else 2)
