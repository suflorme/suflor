#!/usr/bin/env python3
# Suflor.me — Kesişim F2 (12 Kasım 2026): arka plan çözücü. Tasarım: ../planlar/kesisim-mimari-20261111.md §4–5.
#   python3 -B kesisim-coz.py kos-coz [--canli DIR]    (kesişim koşusu + çözücü; günlük zamanlayıcının çağırdığı)
#   python3 -B kesisim-coz.py coz [--canli DIR]        (var olan kesisim.json'u çöz)
#   python3 -B kesisim-coz.py geri-al ID [--canli DIR] (bir düzeltmeyi geri al)
# Akış: kesisim.json'daki "önemli" bulgular (çelişki, belirsiz, kişi için eksik) → TEK toplu model çağrısı (varsayılan Opus; aktarici/beyin.py claude -p yolu, yeni bağımlılık yok)
#   → her bulgu için karar: duzelt | arastir | birak + gerekçe + güven.
#   duzelt:  S293 (12 Kasım): çözücü ŞİMDİLİK YALNIZ SUFLOR TARAFINDA karar verir. proje veritabanı öneri kuyruğuna (kayit.py oneri) YAZMA KAPALI: ayar kesisim_coz_oh true olsa bile oh_fn verilmedikçe
#            çağrı yapılmaz; kapalıyken proje veritabanını ilgilendiren düzeltme yalnız "proje veritabanına yazılacaktı (kapalı)" diye kaydedilir (durumda oh_bekleyen). Tazı tarafı: tazi.py dosya (yeni öğe, geri alma = öğeyi kapat).
#   arastir: Tazı kuyruğuna (aday + sorgu günlüğü; aktarıcıdan çağrılınca tazi_kos hızlı tarama). Ertesi koşuda yeniden değerlendirilir; 3 koşuda sonuçsuz kalırsa "çözülemeyen önemli" olur.
#   birak:   bir kez not edilir; bulgu id'si kesisim-coz-durum.json "birak"a girer, kesisim.kos o id'yi bir daha üretmez.
# Sınırlar: silme yok · kişi/iletişim alanında yalnız kaynaklı ve kanıt düzeyi ≥ 2 (B) · karar/iş kayıtlarına dokunulmaz · günlük düzeltme tavanı (ayar kesisim_coz_tavan, 5) · güven < 0.7 düzeltme olmaz (araştır'a düşer)
#   · her düzeltme <canli>/kesisim-coz.jsonl'da geri alınabilir olay satırı (t, id, karar, eylem, guven, geri_al; metin YOK).
# Çıktı: kesisim.json "cozum": {tarih, duzeltilen, arastirilan, birakilan, cozulemeyen_onemli: [{id, ozet, neden}], oh_kapali, model, aday}.
# Gizlilik: yalnız geliştiricide (ayar kesisim_cozucu; yoksa gelistirici_mi) ve gizli toplantı kapalıyken; kişisel/sağlık kaydı kesisim.py'de zaten bulguya girmez. Metin bağlamı Claude'a gider (güven alanı, S222).
import argparse, datetime, importlib.util, json, os, re, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.abspath(__file__))
if KOK not in sys.path: sys.path.insert(0, KOK)
import kesisim

TAVAN_VARSAYILAN, GUVEN_ESIK, EN_COK_ADAY, ARASTIR_EN_COK = 5, 0.7, 30, 3
KARARLAR = ("duzelt", "arastir", "birak")
BOLUMLER = ("iz", "iddia", "zaman")                 # kimlik yazılmaz (eski hükmü siler); çelişki/bayrak/soru Tazı'nın kendi işi
YASAK_KAYIT = ("karar/", "is/", "gorev/", "is_", "karar_")   # karar ve iş kayıtlarına dokunulmaz (kaynak kaydı bu öneklerden biriyse düzeltme olmaz)
KISI_RX = re.compile(r"(?i)(e-?posta|eposta|telefon|iletişim|iletisim|adres)")
KAYNAK_RX = re.compile(r"^(https?://\S{4,300}|[^\s].{3,200})$")

def _iso(d): return d.isoformat(timespec="seconds")
def _kisalt(m, n): m = " ".join(str(m or "").split()); return m if len(m) <= n else m[:n - 1].rstrip() + "…"
def _sayi(v, varsayilan, alt, ust):
    try: return max(alt, min(ust, int(v)))
    except (TypeError, ValueError): return varsayilan

def acik_mi(ayar, gelistirici):
    v = (ayar or {}).get("kesisim_cozucu")
    return v if isinstance(v, bool) else bool(gelistirici)

# ---------- durum ve olay günlüğü ----------
def _durum_yol(canli): return os.path.join(canli, "kesisim-coz-durum.json")
def durum_oku(canli):
    d = kesisim._json_oku(_durum_yol(canli), {})
    for k in ("birak", "arastir", "duzelt", "oh_bekleyen", "gun"): d.setdefault(k, {})
    return d
def durum_yaz(canli, d): kesisim._yaz_atomik(_durum_yol(canli), json.dumps(d, ensure_ascii=False, indent=1))
def olay_yaz(canli, simdi, bid, karar, eylem, guven=None, geri_al=None):
    o = {"t": _iso(simdi), "id": bid, "karar": karar, "eylem": eylem}
    if guven is not None: o["guven"] = round(float(guven), 2)
    if geri_al: o["geri_al"] = geri_al
    with open(os.open(os.path.join(canli, "kesisim-coz.jsonl"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "a", encoding="utf-8") as f: f.write(json.dumps(o, ensure_ascii=False) + "\n")

# ---------- aday seçimi, istem, yanıt ----------
def onemli(b):
    return b.get("tur") == "celiski" or bool(b.get("belirsiz")) or (b.get("tur") == "eksik" and str(b.get("varlik", "")).startswith("kisi:"))
def adaylar(sonuc, durum, simdi):
    """önemli, kapanmamış, bırakılmamış, son 7 günde düzeltilmemiş bulgular; belirsizler önce"""
    son = simdi - datetime.timedelta(days=7)
    secilen = []
    for b in sonuc.get("bulgular") or []:
        if b.get("durum") == "kapandi" or not onemli(b) or b["id"] in durum["birak"]: continue
        z = kesisim._zaman((durum["duzelt"].get(b["id"]) or {}).get("tarih"))
        if z and z >= son: continue
        secilen.append(b)
    secilen.sort(key=lambda b: (not b.get("belirsiz"), b.get("tur") != "celiski", b["id"]))
    return secilen[:EN_COK_ADAY]

SISTEM = """Sen Suflor.me'nin Kesişim çözücüsüsün. Bir şirketin iç kayıtları (veritabanı: vt) ile dış firma/kişi araştırma dosyaları (Tazı: tazi) arasında kural motorunun bulduğu uyuşmazlıkları karara bağlarsın.
Her bulgu için TAM BİR karar ver:
- duzelt: doğru bilgi belli ve kaynakla kanıtlı. Düzeltme Tazı dosyasına yeni bir not olarak yazılır ("hedef": "tazi", "duzeltme": {"bolum": "iz"|"iddia"|"zaman", "metin": ≤ 300 karakter, "kaynak": bağlantı ya da kaynak adı, "derece": "A"|"B"|"C"}). İç kayıt (vt) yanlışsa "hedef": "oh" ver ve aynı "duzeltme"yi doldur; o yazılmaz, yalnız kaydedilir.
- arastir: kanıt yetmiyor; dış araştırma kuyruğuna girsin.
- birak: fark önemsiz ya da iki bilgi de doğru (ör. iç unvan ile dış unvan, aynı firmanın iki adı).
Kurallar: uydurma yok; yalnızca verilen veriye dayan. Kaynağın yoksa duzelt verme. Kişi ve iletişim bilgisinde (e-posta, telefon, ad) en az B dereceli kaynak yoksa arastir ver. Emin değilsen düşük güven yaz.
Çıktı YALNIZ şu JSON: {"kararlar":[{"id":"…","karar":"duzelt|arastir|birak","gerekce":"tek cümle","guven":0.0-1.0,"hedef":"tazi|oh","duzeltme":{…}}]} — duzelt dışında hedef ve duzeltme yazma. Her id için bir satır."""
def istem_olustur(adaylar_):
    ver = [{"id": b["id"], "tur": b["tur"], "varlik": b["varlik"], "ozet": b["ozet"], "kaynaklar": b.get("kaynaklar"), "kanit": b.get("kanit"), "karsilastirma": b.get("karsilastirma"),
            "onerilen_eylem": b.get("onerilen_eylem")} for b in adaylar_]
    return SISTEM + "\n\nBULGULAR:\n" + json.dumps(ver, ensure_ascii=False)
def yanit_oku(metin):
    """model metni → {id: karar sözlüğü}; geçersiz satırlar atılır"""
    m = re.search(r"\{.*\}", str(metin or ""), re.S)
    try: j = json.loads(m.group(0)) if m else {}
    except ValueError: return {}
    cikti = {}
    for k in (j.get("kararlar") if isinstance(j, dict) else None) or []:
        if not isinstance(k, dict) or k.get("karar") not in KARARLAR or not isinstance(k.get("id"), str): continue
        try: g = max(0.0, min(1.0, float(k.get("guven"))))
        except (TypeError, ValueError): g = 0.0
        cikti[k["id"]] = {"karar": k["karar"], "gerekce": _kisalt(k.get("gerekce"), 200), "guven": g, "hedef": "oh" if k.get("hedef") == "oh" else "tazi",
                          "duzeltme": k.get("duzeltme") if isinstance(k.get("duzeltme"), dict) else {}}
    return cikti

def _beyin():
    sp = importlib.util.spec_from_file_location("suflor_beyin", os.path.join(KOK, "aktarici", "beyin.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def model_cagir(ayar, istem, canli=None, simdi=None):
    """tek toplu çağrı (araçsız claude -p, istem stdin'den); → model metni ya da None (claude yok / hata)"""
    try:
        by = _beyin(); cl = by.claude_yolu(ayar)
        if not cl: return None
        model = str(ayar.get("kesisim_cozucu_model") or "opus")
        p = by.tek(cl, by.kart_args(model), istem, tempfile.gettempdir(), 900)
        j = json.loads(p.stdout or "{}")
        if canli:   # ölçüm: yalnız sayılar (claude-cagri.jsonl biçimi)
            k = by.kullanim(j)
            with open(os.open(os.path.join(canli, "claude-cagri.jsonl"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "is": "kesisim-coz", "saglayici": "claude-code", "model": model, "api_ms": j.get("duration_api_ms"),
                                    "maliyet": round(k["maliyet"], 4), "giris": k["giris"], "hata": bool(j.get("is_error"))}) + "\n")
        return None if j.get("is_error") else str(j.get("result") or "")
    except Exception as e:
        sys.stderr.write(f"KESİŞİM ÇÖZÜCÜ: model çağrısı olmadı ({e.__class__.__name__})\n"); return None

# ---------- Tazı yolu ----------
def tazi_cagir(args, tazi_dizin=None, tazi_py=None, zaman=30):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if tazi_dizin: env["TAZI_DIR"] = tazi_dizin
    try:
        p = subprocess.run([sys.executable, "-B", tazi_py or os.path.join(KOK, "tazi.py")] + args, capture_output=True, text=True, timeout=zaman, env=env)
        return p.returncode, (p.stdout or "").strip()
    except Exception as e: return 125, e.__class__.__name__
def _tazi_kid(b):
    for k in b.get("kaynaklar") or []:
        if k.get("sistem") == "tazi" and k.get("kayit"): return str(k["kayit"]).split("#")[0]
    return None
def _yasak_kayit(b): return any(str(k.get("kayit", "")).startswith(YASAK_KAYIT) for k in b.get("kaynaklar") or [] if k.get("sistem") == "vt")
def _kisi_alani(b): return str(b.get("varlik", "")).startswith("kisi:") or bool(KISI_RX.search(str(b.get("ozet", ""))))

def duzelt_kontrol(b, k):
    """düzeltme uygulanabilir mi → (True, duzeltme sözlüğü) ya da (False, neden)"""
    d = k.get("duzeltme") or {}
    metin, kaynak = " ".join(str(d.get("metin") or "").split()), str(d.get("kaynak") or "").strip()
    bolum, derece = d.get("bolum") if d.get("bolum") in BOLUMLER else "iz", str(d.get("derece") or "").upper()
    if _yasak_kayit(b): return False, "karar_is_kaydi"
    if k["guven"] < GUVEN_ESIK: return False, "guven_dusuk"
    if not metin or len(metin) > 400: return False, "metin"
    if not kaynak or not KAYNAK_RX.match(kaynak): return False, "kaynaksiz"
    if _kisi_alani(b) and (int((b.get("kanit") or {}).get("duzey") or 0) < 2 or derece not in ("A", "B")): return False, "kisi_kanit_b_alti"
    if derece not in ("A", "B", "C", "D"): derece = "C"
    return True, {"bolum": bolum, "metin": metin, "kaynak": kaynak[:300], "derece": derece}

def coz(canli, ayar=None, sonuc=None, model_fn=None, tazi_fn=None, kuyruk_fn=None, oh_fn=None, simdi=None, tazi_dizin=None, yaz=True):
    """→ cozum sözlüğü (kesisim.json'a da yazılır). model_fn(istem) → metin|None; tazi_fn(args) → (rc, çıktı); kuyruk_fn(ad, alan) → durum metni (tazi_kos kipi: basladi|bekliyor|zaten|tavan|dolu|…);
    oh_fn(bulgu, duzeltme) yalnız ayar kesisim_coz_oh true iken çağrılır (S293: varsayılan kapalı, çağıran vermez)."""
    ayar = ayar if isinstance(ayar, dict) else {}
    simdi = simdi or datetime.datetime.now()
    bugun = simdi.date().isoformat()
    sonuc = sonuc if sonuc is not None else kesisim._json_oku(os.path.join(canli, "kesisim.json"), {})
    durum = durum_oku(canli)
    tavan = _sayi(ayar.get("kesisim_coz_tavan"), TAVAN_VARSAYILAN, 0, 50)
    oh_acik = ayar.get("kesisim_coz_oh") is True and callable(oh_fn)
    tazi_fn = tazi_fn or (lambda a: tazi_cagir(a, tazi_dizin))
    ad_tablo = {}
    def tazi_ad(b):   # arastir için Tazı kaydı adı + alan: dosya kaydından, yoksa varlığın alan adından
        kid = _tazi_kid(b)
        if kid and not ad_tablo:
            ad_tablo.update(kesisim._tazi_oku(os.path.expanduser(tazi_dizin or os.environ.get("TAZI_DIR") or kesisim.TAZI_VARSAYILAN))["kayit"])
        k = ad_tablo.get(kid) if kid else None
        if k: return k["ad"], (k["alanlar"] or [None])[0], kid
        v = str(b.get("varlik", ""))
        if v.startswith("firma:"): return v[6:], v[6:], kid
        return None, None, kid
    if durum["gun"].get("tarih") != bugun: durum["gun"] = {"tarih": bugun, "duzeltme_n": 0}
    cozum = {"tarih": bugun, "duzeltilen": 0, "arastirilan": 0, "birakilan": 0, "cozulemeyen_onemli": [], "oh_kapali": 0, "model": "yok", "aday": 0}
    adaylar_ = adaylar(sonuc, durum, simdi); cozum["aday"] = len(adaylar_)
    haritadaki = {b["id"]: b for b in adaylar_}
    def cozulemedi(b, neden):
        if onemli(b): cozum["cozulemeyen_onemli"].append({"id": b["id"], "ozet": _kisalt(b.get("ozet"), 170), "neden": neden})
    kararlar = {}
    if adaylar_:
        metin = (model_fn or (lambda i: model_cagir(ayar, i, canli, simdi)))(istem_olustur(adaylar_))
        kararlar = yanit_oku(metin) if metin else {}
        cozum["model"] = "ok" if kararlar else "hata"
    for bid, b in haritadaki.items():
        k = kararlar.get(bid)
        if not k: cozulemedi(b, "karar_yok"); continue
        durum.setdefault("kararlar", {})[bid] = {"t": _iso(simdi), "karar": k["karar"], "guven": round(k["guven"], 2), "gerekce": k["gerekce"]}
        karar = k["karar"]
        if karar == "birak":
            durum["birak"][bid] = {"t": _iso(simdi), "gerekce": k["gerekce"]}; cozum["birakilan"] += 1
            olay_yaz(canli, simdi, bid, "birak", "bastirildi", k["guven"]); continue
        if karar == "duzelt":
            tamam, d = duzelt_kontrol(b, k)
            if not tamam:
                if d in ("guven_dusuk", "kaynaksiz", "kisi_kanit_b_alti"): karar = "arastir"; olay_yaz(canli, simdi, bid, "duzelt", "engellendi:" + d, k["guven"])
                else: olay_yaz(canli, simdi, bid, "duzelt", "engellendi:" + d, k["guven"]); cozulemedi(b, d); continue
            elif k["hedef"] == "oh":   # S293: proje veritabanı tarafı kapalı — yalnız kaydet
                durum["oh_bekleyen"][bid] = {"t": _iso(simdi), "duzeltme": d}
                if oh_acik:
                    try: oh_fn(b, d); olay_yaz(canli, simdi, bid, "duzelt", "oh_oneri_yazildi", k["guven"]); durum["duzelt"][bid] = {"tarih": _iso(simdi)}; cozum["duzeltilen"] += 1; continue
                    except Exception: pass
                cozum["oh_kapali"] += 1; olay_yaz(canli, simdi, bid, "duzelt", "oh_yazilacakti_kapali", k["guven"]); continue
            else:
                kid = _tazi_kid(b)
                if not kid: olay_yaz(canli, simdi, bid, "duzelt", "engellendi:tazi_kaydi_yok", k["guven"]); cozulemedi(b, "tazi_kaydi_yok"); continue
                if durum["gun"]["duzeltme_n"] >= tavan: olay_yaz(canli, simdi, bid, "duzelt", "engellendi:tavan", k["guven"]); cozulemedi(b, "tavan"); continue
                rc, cikti = tazi_fn(["dosya", "--kim", kid, "--bolum", d["bolum"], "--metin", "[kesişim] " + d["metin"][:380], "--kaynak", d["kaynak"], "--derece", d["derece"]])
                m = re.search(r"eklendi: #(\d+)", cikti or "")
                if rc != 0 or not m: olay_yaz(canli, simdi, bid, "duzelt", "hata:tazi", k["guven"]); cozulemedi(b, "tazi_hata"); continue
                durum["gun"]["duzeltme_n"] += 1; durum["duzelt"][bid] = {"tarih": _iso(simdi)}; cozum["duzeltilen"] += 1
                olay_yaz(canli, simdi, bid, "duzelt", "tazi_dosya_eklendi", k["guven"], {"sistem": "tazi", "kim": kid, "kapat": int(m.group(1))}); continue
        if karar == "arastir":   # (duzelt'ten düşenler dahil)
            ad, alan, kid = tazi_ad(b)
            a = durum["arastir"].setdefault(bid, {"ilk": bugun, "n": 0})
            if not ad: olay_yaz(canli, simdi, bid, "arastir", "engellendi:hedef_yok", k["guven"]); cozulemedi(b, "arastirma_hedefi_yok"); continue
            if a.get("son") != bugun:
                if kuyruk_fn: d_ = str(kuyruk_fn(ad, alan) or "")
                else:
                    tazi_fn(["aday", "--ad", ad, "--neden", "elle"] + (["--alan", alan] if alan else [])); d_ = "basladi"
                if d_ in ("tavan", "dolu", "kapali", "gizli", "bos", "yok"): olay_yaz(canli, simdi, bid, "arastir", "engellendi:" + d_, k["guven"]); cozulemedi(b, "tazi_" + d_); continue
                tazi_fn(["sorgu", "--istek", "Kesişim: " + _kisalt(b.get("ozet"), 120), "--kim", kid or ad, "--yapan", "zamanli"])
                a["n"] += 1; a["son"] = bugun
                olay_yaz(canli, simdi, bid, "arastir", "tazi_kuyruga_alindi", k["guven"])
            cozum["arastirilan"] += 1
            if a["n"] >= ARASTIR_EN_COK: cozulemedi(b, "arastirma_sonucsuz")
    if yaz:
        durum_yaz(canli, durum)
        sonuc["cozum"] = cozum
        kesisim._yaz_atomik(os.path.join(canli, "kesisim.json"), json.dumps(sonuc, ensure_ascii=False, indent=1))
    return cozum

def geri_al(canli, bid, tazi_fn=None, simdi=None, tazi_dizin=None):
    """son düzeltme olayını geri al (Tazı: öğeyi kapat; silme yok) → True/False"""
    simdi = simdi or datetime.datetime.now()
    tazi_fn = tazi_fn or (lambda a: tazi_cagir(a, tazi_dizin))
    olay = None
    try:
        for l in open(os.path.join(canli, "kesisim-coz.jsonl"), encoding="utf-8"):
            try: o = json.loads(l)
            except ValueError: continue
            if o.get("id") == bid and o.get("geri_al") and o.get("eylem") == "tazi_dosya_eklendi": olay = o
    except OSError: return False
    if not olay: return False
    g = olay["geri_al"]
    rc, _ = tazi_fn(["dosya", "--kim", str(g["kim"]), "--kapat", str(g["kapat"]), "--sonuc", "kesişim düzeltmesi geri alındı"])
    if rc != 0: return False
    olay_yaz(canli, simdi, bid, "duzelt", "geri_alindi")
    d = durum_oku(canli); d["duzelt"].pop(bid, None); d["gun"]["duzeltme_n"] = max(0, int(d["gun"].get("duzeltme_n") or 0) - 1); durum_yaz(canli, d)
    return True

def kos_ve_coz(canli, ayar=None, gizli_fn=None, gelistirici=None, simdi=None, vt=None, tazi_dizin=None, **kw):
    """günlük akış: kesişim koşusu, hemen ardından çözücü. Kapalıysa/gizliyse/geliştirici değilse {"atlandi": neden}"""
    ayar = ayar if isinstance(ayar, dict) else {}
    gizli_fn = gizli_fn or (lambda: False)
    g = gelistirici if gelistirici is not None else kesisim.gelistirici_mi(ayar)
    if not g: return {"atlandi": "gelistirici_degil"}
    if not acik_mi(ayar, g): return {"atlandi": "kapali"}
    if gizli_fn(): return {"atlandi": "gizli"}
    s = kesisim.kos(canli, vt, tazi_dizin, ayar=ayar, simdi=simdi, gizli=False, yaz=True, gelistirici=g)
    if s.get("atlandi"): return s
    if gizli_fn(): return {"atlandi": "gizli"}   # koşu sürerken gizli toplantı açıldıysa model çağrısına gidilmez
    return coz(canli, ayar, s, simdi=simdi, tazi_dizin=tazi_dizin, **kw)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Kesişim F2: arka plan çözücü")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for ad in ("kos-coz", "coz"): sub.add_parser(ad).add_argument("--canli")
    g = sub.add_parser("geri-al"); g.add_argument("id"); g.add_argument("--canli")
    a = ap.parse_args(argv)
    ayar = kesisim._json_oku(os.path.expanduser(os.environ.get("SUFLOR_AYAR") or kesisim.AYAR_VARSAYILAN), {})
    canli = a.canli or os.path.join(kesisim.baglayici._klasor(ayar, "uygulama", "~/Library/Application Support/Suflor"), "canli")
    if a.cmd == "geri-al": ok = geri_al(canli, a.id); print("geri alındı" if ok else "geri alınamadı"); return 0 if ok else 1
    if a.cmd == "coz":
        if not acik_mi(ayar, kesisim.gelistirici_mi(ayar)): print("atlandı: kapali"); return 0
        r = coz(canli, ayar)
    else: r = kos_ve_coz(canli, ayar)
    print(json.dumps(r, ensure_ascii=False)); return 0

if __name__ == "__main__":
    sys.exit(main())
