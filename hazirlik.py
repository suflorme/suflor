#!/usr/bin/env python3
# Proje hazırlığı — sihirbazın B–F ekranlarının arka ucu (T6; planlar/proje-hazirligi.md §1). kurulum.py bunu alt süreç olarak çağırır
# (ayar SUFLOR_AYAR'dan; sihirbaz "Kuruyorum"dan sonra ayar değiştiği için modül kurulum.py'ye yüklenmez).
#   python3 hazirlik.py ozet               → JSON: iş durumu, tarama özeti, hariç/klasör listeleri, süre tahmini, kart taslağının özeti
#   python3 hazirlik.py tara               → yalnız tarama (B ekranı; hariç işareti değişince yeniden)
#   python3 hazirlik.py calis [--kart]     → tara → çevir → dizinle → anlam dizini → (istenirse) proje kartı; sihirbaz kapansa da sürer
#   python3 hazirlik.py kart               → kart taslağının tamamı (E ekranı)
#   python3 hazirlik.py kart-onayla        → stdin JSON {"cikar": {bölüm: [sıra no]}, "terimler": [terim]} → proje-karti.json + sözlük
# Durum <uygulama>/hazirlik.json; iş kilidi <uygulama>/hazirlik.kilit (Brifing yardımcısının dizin turu kilit tutuluyken çevirme/gömme yapmaz).
# Toplantı başlarsa çevirme/gömme/kart durur (baglam.toplantida); kalan iş Brifing yardımcısının 10 dk'lık turlarında sürer, kart sonra panodan.
import argparse, collections, fcntl, importlib.util, json, os, sys, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.abspath(__file__))
def _yukle(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(KOD, dosya)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
B = _yukle("suflor_baglam_hz", "baglam.py")
UYG = B.AYAR["uygulama"]; DURUM = os.path.join(UYG, "hazirlik.json"); KILIT = os.path.join(UYG, "hazirlik.kilit")
# süre tahmini (sn): görüntü ölçüm (17 Ekim, 43 görüntü: ortanca 0,9 sn, ort. 1,4); PDF/sunum tahmin; gömme 18.349 parça 3–5 dk → ~75 parça/sn;
# kart 201 belge 15 dk (4 paralel) → ~4,5 sn/belge, 9,33 $ → ~0,05 $/belge (Sonnet karşılığı)
CEVIR_SN = {".pdf": 8.0, ".pptx": 5.0}; CEVIR_GORUNTU_SN = 1.4; GOMME_PARCA_SN = 75.0; KART_BELGE_SN = 4.5; KART_BELGE_USD = 0.05
KART_TURLER = {"belge", "sunum", "gorusme", "tablo"}

def yaz(d):
    os.makedirs(UYG, exist_ok=True)
    with open(DURUM + ".tmp", "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
    os.replace(DURUM + ".tmp", DURUM)
def oku():
    try: return json.load(open(DURUM, encoding="utf-8"))
    except (OSError, ValueError): return {}
def calisiyor():
    try:
        with open(KILIT, "a") as k:
            try: fcntl.flock(k, fcntl.LOCK_EX | fcntl.LOCK_NB); return False
            except OSError: return True
    except OSError: return False

def gomme_sayisi():
    # gömülmüş parça sayısı: <uygulama>/gomme/p*.id.npy başlıklarından (numpy sistem Python'unda yok; .npy = 10 baytlık ön ek + başlık + int64 dizi)
    n = 0
    for f in os.listdir(B.GOMME) if os.path.isdir(B.GOMME) else []:
        if not (f.startswith("p") and f.endswith(".id.npy")): continue
        try:
            with open(os.path.join(B.GOMME, f), "rb") as h: on = h.read(12)
            bas = 10 + int.from_bytes(on[8:10], "little") if on[6] == 1 else 12 + int.from_bytes(on[8:12], "little")
            n += (os.path.getsize(os.path.join(B.GOMME, f)) - bas) // 8
        except (OSError, IndexError): pass
    return n
def tahmin(r, c):
    # tarama raporu + çevirme önbelleği → kalan iş ve süre (sn)
    cevir_n, cevir_sn = collections.Counter(), 0.0
    for d in r.get("dosyalar") or []:
        ext = os.path.splitext(d["yol"])[1].lower()
        if ext not in B.CEVIR_UZ or d.get("gizli") or d.get("kopya_of") or d.get("hata"): continue
        if os.path.exists(B._onbellek_yol(d["sha256"])): continue
        cevir_n[ext] += 1; cevir_sn += CEVIR_SN.get(ext, CEVIR_GORUNTU_SN)
    # dizinlenecek metin: dizinde olmayan ya da değişmiş dosyalar (boyuttan kabaca 700 karakterlik parça); gömme eksikleri ayrıca
    dizinde = {y: (m, b) for y, m, b in c.execute("SELECT yol, mtime, boy FROM dosya")}
    yeni_parca = 0
    for d in r.get("dosyalar") or []:
        if d.get("gizli") or d.get("kopya_of") or d.get("hata"): continue
        ext = os.path.splitext(d["yol"])[1].lower()
        if ext not in B.UZANTI or dizinde.get(d["yol"]) == (d["mtime"], d["boy"]): continue
        yeni_parca += max(1, int(d["boy"] * (0.35 if ext in (".docx", ".xlsx") else 1.0) / B.PARCA))
    yeni_parca += sum(n for n in cevir_n.values()) * 3
    gomme_eksik = max(0, c.execute(f"SELECT count(*) FROM parca p JOIN dosya d ON d.yol = p.yol WHERE {B.gomme_kosul()}").fetchone()[0] - gomme_sayisi())
    gomme_n = gomme_eksik + yeni_parca if os.path.isdir(os.path.join(B.AYAR["ortak"], "anlam-modeller")) and os.path.exists(B.CEVIR_PY) else 0
    kart_belge = sum(1 for d in r.get("dosyalar") or [] if d.get("gecerli") and not d.get("gizli") and not d.get("kopya_of") and not d.get("hata")
                     and d.get("kaynak_turu") == "asil" and B.tur_bul(d["yol"]) in KART_TURLER and not d["yol"].startswith("_canli/"))
    kart_belge = min(kart_belge, 300)
    sn = cevir_sn + yeni_parca / 400.0 + gomme_n / GOMME_PARCA_SN
    return {"cevir": dict(cevir_n), "cevir_n": sum(cevir_n.values()), "parca_yeni": yeni_parca, "gomme_n": gomme_n,
            "kart_belge": kart_belge, "kart_sn": round(kart_belge * KART_BELGE_SN), "kart_usd": round(kart_belge * KART_BELGE_USD, 2),
            "sn": round(sn), "cevirme_kurulu": os.path.exists(B.CEVIR_PY)}

def klasorler(r):
    # proje kökündeki klasörler: dosya sayısı ve boyut (B ekranında "dizine alma" işareti için); ayarla hariç olanlar da listede
    k = collections.defaultdict(lambda: [0, 0])
    for d in r.get("dosyalar") or []:
        ust = d["yol"].split("/", 1)[0] if "/" in d["yol"] else ""
        if ust: k[ust][0] += 1; k[ust][1] += d["boy"]
    haric = set(B.AYAR.get("haric") or [])
    try: tum = sorted(x for x in os.listdir(B.PROJE) if os.path.isdir(os.path.join(B.PROJE, x)) and not x.startswith(".") and x not in B.HARIC_GENEL)
    except OSError: tum = sorted(k)
    return [{"ad": a, "dosya": k[a][0] if a in k else 0, "boy": k[a][1] if a in k else 0, "haric": a in haric} for a in tum]

def ozet():
    r = {}
    try: r = json.load(open(B.TARA_RAPOR, encoding="utf-8"))
    except (OSError, ValueError): pass
    out = {"is": dict(oku(), calisiyor=calisiyor()), "proje": B.PROJE, "bos": None, "tarama": None}
    if r and r.get("proje") == B.PROJE:
        s = r["sayilar"]; c = B.baglan()
        out["bos"] = s["dosya"] == 0
        out["tarama"] = {"t": r["t"], "sayilar": s, "haric": r["haric"][:200], "okunamayan": r["okunamayan"][:100],
                         "surum_gruplari": r["surum_gruplari"][:50], "kopyalar": r["kopyalar"][:50], "kaynak_turu": r["kaynak_turu"][:200],
                         "dahil": list(B.AYAR.get("dahil") or []), "asil": list(B.AYAR.get("asil") or []), "klasorler": klasorler(r)}
        out["tahmin"] = tahmin(r, c)
        out["dizin"] = {"dosya": c.execute("SELECT count(*) FROM dosya").fetchone()[0], "parca": c.execute("SELECT count(*) FROM parca").fetchone()[0],
                        "cevrilen": sum(1 for d in r.get("dosyalar") or [] if os.path.splitext(d["yol"])[1].lower() in B.CEVIR_UZ and d.get("sha256") and os.path.exists(B._onbellek_yol(d["sha256"])))}
    tk = kart_ozet()
    if tk: out["kart"] = tk
    return out

def _kart_mod(): return _yukle("suflor_kart_hz", "proje-karti.py")
def kart_ozet():
    try: k = json.load(open(os.path.join(UYG, "proje-karti-taslak.json"), encoding="utf-8"))
    except (OSError, ValueError): return None
    onay = None
    try: onay = json.load(open(os.path.join(UYG, "proje-karti.json"), encoding="utf-8")).get("onay")
    except (OSError, ValueError): pass
    return {"t": k.get("t"), "belge": k.get("belge"), "aday": k.get("aday"), "maliyet_usd": k.get("maliyet_usd"), "durdu": k.get("durdu"),
            "hata": len(k.get("hatalar") or []), "onay": onay if onay and onay.get("t", 0) >= (k.get("t") or 0) else None,
            "sayilar": {b: len(k.get(b) or []) for b in ("kisiler", "kurumlar", "kararlar", "tarihler", "acik_isler", "sozluk")}}

def kart_tam():
    K = _kart_mod()
    try: k = json.load(open(K.TASLAK, encoding="utf-8"))
    except (OSError, ValueError): return {"yok": True}
    duz = {y for y in {s[0] for m in k.get("sozluk") or [] for s in m.get("kaynaklar") or []} if y.count("/") <= 1 and K.DUZENLI_RX.match(os.path.basename(y))}
    sec = sorted((m for m in k.get("sozluk") or [] if K.sozluk_aktarilir(m, duz)), key=lambda m: (not ({x[0] for x in m.get("kaynaklar") or []} & duz), -len({x[0] for x in m.get("kaynaklar") or []})))
    oneri = {m["terim"] for m in sec[:K.SOZ_AKTAR_EN_COK]}
    for m in k.get("sozluk") or []: m["oneri"] = m["terim"] in oneri
    k.pop("belge_ozetleri", None); k["sozluk_en_cok"] = K.SOZ_AKTAR_EN_COK
    return k

def kart_onayla(duzen):
    K = _kart_mod(); k = json.load(open(K.TASLAK, encoding="utf-8"))
    for bol, sira in (duzen.get("cikar") or {}).items():
        if bol in ("kisiler", "kurumlar", "kararlar", "tarihler", "acik_isler", "sozluk") and isinstance(k.get(bol), list):
            at = {int(i) for i in sira if str(i).lstrip("-").isdigit()}; k[bol] = [x for i, x in enumerate(k[bol]) if i not in at]
    k.pop("belge_ozetleri", None)
    terimler = duzen.get("terimler")
    return K.onayla(k, kim="sihirbaz", terimler=None if terimler is None else [str(t) for t in terimler])

def calis(kart=False):
    os.makedirs(UYG, exist_ok=True)
    kf = open(KILIT, "a")
    try: fcntl.flock(kf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: print("hazırlık zaten sürüyor", file=sys.stderr); return 2
    d = {"pid": os.getpid(), "t0": int(time.time()), "evre": "tara", "kart_istendi": bool(kart), "adim": {}, "t": int(time.time())}
    def evre(e, **k): d.update(evre=e, t=int(time.time()), **k); yaz(d)
    def ilerle(ad, n, toplam): d["adim"][ad] = {"n": n, "toplam": toplam}; d["t"] = int(time.time()); yaz(d)
    yaz(d)
    try:
        c = B.baglan(); r = B.tara(c)
        d["tarama"] = {"dosya": r["sayilar"]["dosya"]}
        if r["sayilar"]["dosya"] == 0: evre("bitti", sonuc={"bos": True}); return 0
        evre("cevir"); cv = B.cevir(c, ilerleme=lambda n, t: ilerle("cevir", n, t))
        d["cevir"] = {k: cv[k] for k in ("cevrildi", "hata", "kalan", "durdu", "gizli_dosya", "gizli_parca", "onbellekte")}
        evre("dizin"); B.guncelle(c)
        evre("gomme"); g = B.gomme(c, ilerleme=lambda n, t: ilerle("gomme", n, t))
        d["gomme"] = g
        durdu = cv.get("durdu") if cv.get("durdu") and "ortamı yok" not in str(cv.get("durdu")) else None
        if B.toplantida(): durdu = "toplantı başladı"
        if kart and not durdu:
            evre("kart"); K = _kart_mod()
            t = K.cikar(ilerleme=lambda n, tp: ilerle("kart", n, tp))
            d["kart"] = {k: t.get(k) for k in ("belge", "aday", "maliyet_usd", "durdu", "sure_sn")}; d["kart"]["hata"] = len(t.get("hatalar") or [])
            if t.get("durdu"): durdu = t["durdu"]
        sat = c.execute("SELECT count(*), coalesce(sum(parca), 0) FROM dosya").fetchone()
        sonuc = {"belge": sat[0], "parca": sat[1], "cevrilen": cv["cevrildi"] + cv["onbellekte"], "gizli_parca": cv.get("gizli_parca", 0)}
        evre("durdu" if durdu else "bitti", sonuc=sonuc, durdu=durdu)
        return 0
    except Exception as e:
        evre("hata", hata=f"{e.__class__.__name__}: {str(e)[:200]}"); raise
    finally:
        fcntl.flock(kf, fcntl.LOCK_UN); kf.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ozet"); sub.add_parser("tara"); sub.add_parser("kart"); sub.add_parser("kart-onayla")
    cl = sub.add_parser("calis"); cl.add_argument("--kart", action="store_true")
    A = ap.parse_args()
    if A.cmd == "ozet": print(json.dumps(ozet(), ensure_ascii=False))
    elif A.cmd == "tara":
        if calisiyor(): print(json.dumps({"ok": False, "hata": "sürüyor"})); sys.exit(0)
        r = B.tara(); print(json.dumps({"ok": True, "dosya": r["sayilar"]["dosya"]}))
    elif A.cmd == "kart": print(json.dumps(kart_tam(), ensure_ascii=False))
    elif A.cmd == "kart-onayla": print(json.dumps(kart_onayla(json.load(sys.stdin)), ensure_ascii=False))
    else: sys.exit(calis(A.kart))
