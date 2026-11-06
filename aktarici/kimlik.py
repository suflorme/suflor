# Kimlik (ortak karar katmanı A1, planlar/ortak-karar-mimarisi-20261105.md §2): kişi adı → şirket e-postası (küçük harf).
# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("kimlik")); import edilmez. Kullandığı ad alanı: re, os, json, time, AYAR, BASE; isteğe bağlı: TAKVIM_TAM, TAKVIM_GEC, kisi_bul.
# Kaynak sırası: kullanıcı (ayar) → takvim katılımcıları (ad+e-posta) → Mac Kişiler (kisi_bul; yalnız okuma) → kayıt veritabanı kişi adresleri (kimlik_vt_yukle ile bellekte)
#   → e-posta adresinin yerel kısmı (ad.soyad@). Belirsizlikte tahmin yok: birden çok aday → eposta None + adaylar. Sorma arayüzü yok: kimlik_eslenemeyen() listesi.
# Kalıcı kayıt canli/kimlik.json (0600): elle düzeltme (kalıcı), önbellek (14 gün), birleşik adlar, kimlik_birlesti olay günlüğü. Veri yalnız bu Mac'te; beta paketine girmez.
KIMLIK_ONBELLEK_GUN = 14
KIMLIK_ISIM_DEGIL = {"ekip", "herkes", "belirsiz", "bilinmiyor", "yok", "tbd", "takim", "ekibi", "hepsi", "kimse", "?", "-", "diger", "digerleri", "all", "everyone", "team", "unknown"}
_KIM_EPOSTA_RX = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
KIMLIK_VT = {}  # {ad anahtarı (sözcük dizisi): {eposta}} — kimlik_vt_yukle doldurur (aktarıcı kayıt veritabanını okuyamaz; yardımcı gönderir)
_KIM_DURUM = {"dosya": None, "mt": None, "d": None, "takvim_t": 0.0, "takvim": None}

def _kim_katla(s):  # Türkçe harf katlama: İıÇçĞğÖöŞşÜü → i/c/g/o/s/u; küçük harf
    import unicodedata
    s = str(s or "").replace("İ", "i").replace("I", "i").replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
def _kim_sozcukler(ad):  # "Kaya, Bora (Firma)" / "bora.kaya" → ["bora", "kaya"]
    ad = _KIM_EPOSTA_RX.sub(" ", str(ad or "")); ad = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", ad)
    if ad.count(",") == 1 and all(p.strip() for p in ad.split(",")): a, b = ad.split(","); ad = b + " " + a  # Exchange "Soyad, Ad"
    return re.findall(r"[a-z]+", _kim_katla(ad))
def _kim_anahtar(ad): return " ".join(_kim_sozcukler(ad))
def _kim_ep(x):
    x = str(x or "").strip().lower().strip("<>;,. ")
    return x if _KIM_EPOSTA_RX.fullmatch(x) and not x.endswith("@imip.me.com") else None  # imip.me.com: iCloud davet rölesi, kişinin adresi değil

# ---- kalıcı kayıt ------------------------------------------------------------------------------------------------------------
def _kim_yol(): return os.path.join(BASE, "kimlik.json")
def _kim_oku():
    yol = _kim_yol()
    try: mt = os.stat(yol).st_mtime
    except OSError: mt = None
    if _KIM_DURUM["d"] is not None and _KIM_DURUM["dosya"] == yol and _KIM_DURUM["mt"] == mt: return _KIM_DURUM["d"]
    try: d = json.load(open(yol, encoding="utf-8"))
    except (OSError, ValueError): d = {}
    if not isinstance(d, dict): d = {}
    for k in ("adlar", "birlesik"):
        if not isinstance(d.get(k), dict): d[k] = {}
    if not isinstance(d.get("olaylar"), list): d["olaylar"] = []
    d["surum"] = 1; _KIM_DURUM.update(dosya=yol, mt=mt, d=d); return d
def _kim_yaz(d):
    yol = _kim_yol(); d["olaylar"] = d["olaylar"][-100:]
    try:
        fd = os.open(yol + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(yol + ".tmp", yol); _KIM_DURUM.update(dosya=yol, mt=os.stat(yol).st_mtime, d=d)
    except OSError as e: print(f"KİMLİK: kayıt yazılamadı ({e.__class__.__name__})"); _KIM_DURUM["d"] = None
def _kim_simdi(): return time.strftime("%Y-%m-%dT%H:%M:%S")

# ---- kaynaklar ----------------------------------------------------------------------------------------------------------------
def kimlik_ben():  # kullanıcı: (ad sözcükleri, e-posta ya da None)
    a = AYAR; ep = None
    for x in [a.get("eposta_kimlik"), a.get("eposta_adres")] + list(a.get("takvim_adreslerim") or []):
        ep = _kim_ep(x)
        if ep: break
    return _kim_sozcukler(a.get("ad")), ep
def _kim_alan():
    ep = kimlik_ben()[1]; return ep.split("@")[1] if ep else None
def _kim_ekle(idx, ad, ep, kaynak):
    k = _kim_anahtar(ad); ep = _kim_ep(ep)
    if k and ep: idx.setdefault(k, {}).setdefault(ep, kaynak)
def _kim_takvim_indeks():  # {anahtar: {eposta: kaynak}} (takvim ad+e-posta çiftleri), {…} (adsız adreslerin yerel kısmı)
    simdi = time.time()
    if _KIM_DURUM["takvim"] is not None and simdi - _KIM_DURUM["takvim_t"] < 30: return _KIM_DURUM["takvim"]
    g = globals(); olaylar = list((g.get("TAKVIM_TAM") or {}).values()); tg = g.get("TAKVIM_GEC") or {}
    olaylar += list(tg.get("olaylar") or []) + list(tg.get("pay") or []) + list((g.get("TAKVIM_PAY") or {}).values())
    idx, yerel, adli = {}, {}, set()
    for e in olaylar:
        if not isinstance(e, dict): continue
        for k in e.get("kisiler") or []:
            if isinstance(k, dict): _kim_ekle(idx, k.get("ad"), k.get("eposta"), "takvim"); adli.add(_kim_ep(k.get("eposta")))
        for x in e.get("katilimci_eposta") or []:
            ep = _kim_ep(x)
            if ep and ep not in adli: yerel_ad = re.sub(r"[._\-+]+", " ", ep.split("@")[0]); _kim_ekle(yerel, yerel_ad if len(_kim_sozcukler(yerel_ad)) >= 2 else "", ep, "eposta_yerel")
    _KIM_DURUM.update(takvim=(idx, yerel), takvim_t=simdi); return _KIM_DURUM["takvim"]
def kimlik_takvim_sifirla(): _KIM_DURUM.update(takvim=None, takvim_t=0.0)
def kimlik_vt_yukle(satirlar):  # [(adlar "Ad,lakap,…", adresler "a@x,b@y"), …] → bellekte; çıktı: yüklenen kişi sayısı
    KIMLIK_VT.clear(); n = 0
    for r in satirlar or []:
        if not r or len(r) < 2 or not r[1]: continue
        eps = [e for e in (_kim_ep(x) for x in str(r[1]).split(",")) if e]; alan = _kim_alan()
        if alan and len(eps) > 1 and any(e.endswith("@" + alan) for e in eps): eps = [e for e in eps if e.endswith("@" + alan)]  # hesap/giriş adreslerinden şirket adresi
        for ad in re.split(r"[,/]", str(r[0] or "")):
            if len(_kim_sozcukler(ad)) >= 1 and eps:
                for e in eps: KIMLIK_VT.setdefault(_kim_anahtar(ad), {}).setdefault(e, "vt")
        n += 1 if eps else 0
    return n

# ---- eşleme -------------------------------------------------------------------------------------------------------------------
def _kim_uyum(q, kt):  # q (sorulan), kt (kayıttaki) sözcük listeleri → "tam" | "kismi" | None
    if q == kt: return "tam"
    if len(q) == 1: return "kismi" if kt and q[0] == kt[0] else None  # yalnız ilk ad
    if len(kt) < 2 or q[0] != kt[0]: return None
    if len(q[-1]) == 1 and kt[-1].startswith(q[-1]) and len(q) == 2: return "kismi"  # "Ayla K" ~ "Ayla Kaya"
    if q[-1] == kt[-1] and (set(q) <= set(kt) or set(kt) <= set(q)): return "kismi"  # ara ad bir yanda eksik: "Ayla Kaya" ~ "Ayla Nur Kaya"
    return None
def _kim_ara(q, idx):  # → (tam: {ep: kaynak}, kismi: {ep: kaynak})
    tam, kismi = {}, {}
    for k, eps in idx.items():
        u = _kim_uyum(q, k.split())
        if u == "tam": tam.update(eps)
        elif u: kismi.update(eps)
    return tam, kismi
def _kim_kisiler(ad):  # Mac Kişiler (kisi_bul): ad eşleşen kişiler; kişide birden çok adres varsa kullanıcının alan adlıları
    kb = globals().get("kisi_bul")
    if not kb: return {}
    try: o = kb(ad)
    except Exception: return {}
    if not isinstance(o, dict) or o.get("durum") != "ok": return {}
    alan = _kim_alan(); idx = {}
    for c in o.get("kisiler") or []:
        eps = [e for e in (_kim_ep(x) for x in c.get("eposta") or []) if e]
        if alan and len(eps) > 1 and any(e.endswith("@" + alan) for e in eps): eps = [e for e in eps if e.endswith("@" + alan)]
        for e in eps: _kim_ekle(idx, c.get("ad") or "", e, "kisiler")
    return idx
def kimlik_coz(ad, kisiler=True, yaz=True):  # → {"eposta": str|None, "kaynak": str|None, "guven": float, "adaylar": [str]}
    ham = str(ad or "").strip(); bos = {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": []}
    m = _KIM_EPOSTA_RX.search(ham)
    if m: return {"eposta": m.group(0).lower(), "kaynak": "ad_icinde", "guven": 1.0, "adaylar": []}
    q = _kim_sozcukler(ham)
    if not q or " ".join(q) in KIMLIK_ISIM_DEGIL: return dict(bos, kaynak="kisi_degil")
    d = _kim_oku(); k = " ".join(q); gor = set()
    while k in d["birlesik"] and k not in gor: gor.add(k); k = d["birlesik"][k]  # kimlik_birlesti: iki ad aynı kişi
    kay = d["adlar"].get(k)
    if kay and kay.get("kaynak") == "elle" and kay.get("eposta"): return {"eposta": kay["eposta"], "kaynak": "elle", "guven": 1.0, "adaylar": []}
    if kay and kay.get("eposta") and kay.get("guven", 0) >= 0.9 and (time.time() - kay.get("t", 0)) < KIMLIK_ONBELLEK_GUN * 86400:
        return {"eposta": kay["eposta"], "kaynak": kay.get("kaynak"), "guven": kay.get("guven"), "adaylar": [], "onbellek": True}
    q = k.split()  # birleşik hedefe göre ara
    sonuc = _kim_coz_kaynaklar(q, kisiler)
    if sonuc["eposta"] and yaz:
        d["adlar"][k] = {"ad": ham[:80], "eposta": sonuc["eposta"], "kaynak": sonuc["kaynak"], "guven": sonuc["guven"], "tarih": _kim_simdi(), "t": round(time.time())}
        _kim_yaz(d)
    return sonuc
def _kim_sistem(ep): return ep.endswith(".onmicrosoft.com")  # kiracı takma adresi: şirket e-postası değil, başka kaynakta şirket adresi varsa o seçilir
def _kim_daralt(q, eps):  # birden çok adres: adla uyumlu yerel kısım (ad… ya da soyad içeren), sonra tek şirket alan adlısı; hâlâ çoksa olduğu gibi
    eps = set(eps)
    if len(eps) < 2: return eps
    ilk, son = q[0], q[-1]
    kanit = {e for e in eps if (len(ilk) >= 3 and re.sub(r"[^a-z]", "", e.split("@")[0]).startswith(ilk)) or (len(q) > 1 and len(son) >= 3 and son in re.sub(r"[^a-z]", "", e.split("@")[0]))}
    if kanit: eps = kanit
    alan = _kim_alan(); sirket = {e for e in eps if alan and e.endswith("@" + alan)}
    return sirket if len(eps) > 1 and len(sirket) == 1 else eps
def _kim_coz_kaynaklar(q, kisiler):
    ben, ben_ep = kimlik_ben(); takvim, yerel = _kim_takvim_indeks(); kaynaklar = []
    if ben and ben_ep: kaynaklar.append(("ayar", True, lambda: {" ".join(ben): {ben_ep: "ayar"}}))
    kaynaklar.append(("takvim", True, lambda: takvim))
    if kisiler: kaynaklar.append(("kisiler", True, lambda: _kim_kisiler(" ".join(q))))
    kaynaklar.append(("vt", False, lambda: KIMLIK_VT)); kaynaklar.append(("eposta_yerel", False, lambda: yerel))  # güvenilir olmayan kaynak kısmi eşleşmede yarışmaz
    kismi_g, kismi_d = {}, {}; belirsiz = None; sistem_adresi = None
    for ad, guvenilir, al in kaynaklar:
        tam, ks = _kim_ara(q, al()); tam = _kim_daralt(q, tam) if tam else set()
        if len(tam) == 1:
            ep = next(iter(tam)); g = 1.0 if ad == "ayar" else 0.6 if ad == "eposta_yerel" else 0.95
            if _kim_sistem(ep): sistem_adresi = sistem_adresi or (ep, ad); continue
            if belirsiz and ep not in belirsiz: return {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": sorted(set(belirsiz) | {ep})[:6]}
            return {"eposta": ep, "kaynak": ad, "guven": g, "adaylar": []}
        if len(tam) > 1: belirsiz = belirsiz or tam; continue
        for e in ks: (kismi_g if guvenilir else kismi_d).setdefault(e, ad)
        if len(kismi_g) > 1: break  # ikinci aday çıktı: sonraki kaynak belirsizliği çözmez, Kişiler'e boşuna gidilmez
    if belirsiz: return {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": sorted(belirsiz)[:6]}
    if sistem_adresi: return {"eposta": sistem_adresi[0], "kaynak": sistem_adresi[1], "guven": 0.6, "adaylar": []}
    havuz = kismi_g or {e: k for e, k in kismi_d.items()}
    if kismi_g: havuz = kismi_g
    elif kismi_d: havuz = {e: kismi_d[e] for e in _kim_daralt(q, set(kismi_d))}
    if len(havuz) == 1:
        ep, ad = next(iter(havuz.items())); return {"eposta": ep, "kaynak": ad, "guven": 0.5 if ad == "eposta_yerel" else 0.75 if len(q) > 1 else 0.7, "adaylar": []}
    return {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": sorted(havuz)[:6]}
def kimlik_toplu(adlar, kisiler=True):  # {ad: kimlik_coz sonucu}; kayıt dosyası bir kez yazılır
    out = {}
    for a in list(dict.fromkeys(str(x).strip() for x in adlar or [] if str(x).strip()))[:200]: out[a] = kimlik_coz(a, kisiler)
    return out
def kimlik_duzelt(ad, eposta):  # elle düzeltme (kalıcı); eposta boşsa elle kaydı siler
    k = _kim_anahtar(ad)
    if not k: return {"ok": False, "hata": "ad yok"}
    d = _kim_oku()
    if not eposta: d["adlar"].pop(k, None); _kim_yaz(d); return {"ok": True, "silindi": True}
    ep = _kim_ep(eposta)
    if not ep: return {"ok": False, "hata": "geçersiz e-posta"}
    d["adlar"][k] = {"ad": str(ad).strip()[:80], "eposta": ep, "kaynak": "elle", "guven": 1.0, "tarih": _kim_simdi(), "t": round(time.time())}; _kim_yaz(d)
    return {"ok": True, "eposta": ep}
def kimlik_birlestir(ad1, ad2):  # iki adı aynı kişi say (ad2 → ad1); e-posta ad1'inkidir, yoksa ad2'ninki ad1'e geçer
    k1, k2 = _kim_anahtar(ad1), _kim_anahtar(ad2)
    if not k1 or not k2 or k1 == k2: return {"ok": False, "hata": "iki farklı ad gerekir"}
    d = _kim_oku()
    while k1 in d["birlesik"]: k1 = d["birlesik"][k1]
    if k1 == k2: return {"ok": False, "hata": "zaten birleşik"}
    d["birlesik"][k2] = k1
    for k, v in list(d["birlesik"].items()):
        if v == k2: d["birlesik"][k] = k1
    e2 = d["adlar"].pop(k2, None)
    if e2 and e2.get("eposta") and not (d["adlar"].get(k1) or {}).get("eposta"): e2 = dict(e2, ad=str(ad1).strip()[:80]); d["adlar"][k1] = e2
    d["olaylar"].append({"olay": "kimlik_birlesti", "ad1": str(ad1).strip()[:80], "ad2": str(ad2).strip()[:80], "tarih": _kim_simdi()}); _kim_yaz(d)
    return {"ok": True, "hedef": k1}

# ---- kayıtlardaki eşlenemeyenler (yalnız okuma) --------------------------------------------------------------------------------
def _kim_sahipler(gun, dizin=None):  # son gun günün karar grafı kayıtlarında sahip (yoksa kim) adları → {ad: kayıt sayısı}
    import sqlite3, pathlib, datetime
    yol = os.path.join(dizin or BASE, "karar-grafi.sqlite")
    if not os.path.exists(yol): return {}
    sinir = str((datetime.datetime.now() - datetime.timedelta(days=int(gun))).date()); out = {}
    try:
        c = sqlite3.connect(pathlib.Path(yol).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            for ad, n in c.execute("SELECT coalesce(nullif(trim(sahip),''), nullif(trim(kim),'')) a, count(*) FROM kayit WHERE tarih >= ? GROUP BY a", (sinir,)):
                if ad: out[str(ad).strip()] = int(n)
        finally: c.close()
    except sqlite3.Error: return {}
    return out
def kimlik_olcum(gun=30, dizin=None, kisiler=True):  # → {"toplam_ad", "kisi_degil", "eslenen", "eslenemeyen": [{ad, kayit, adaylar, neden}], "kaynak": {kaynak: sayı}, "kayit_orani"}
    sahip = _kim_sahipler(gun, dizin); ben, _ = kimlik_ben(); kaynak, es, kd, sayi_es, sayi_top = {}, [], 0, 0, 0
    for ad, n in sorted(sahip.items(), key=lambda x: -x[1]):
        r = kimlik_coz(ad, kisiler)
        if r["kaynak"] == "kisi_degil": kd += n; continue
        sayi_top += n
        if r["eposta"]: kaynak[r["kaynak"]] = kaynak.get(r["kaynak"], 0) + 1; sayi_es += n
        else: es.append({"ad": ad, "kayit": n, "adaylar": r["adaylar"], "neden": "belirsiz" if r["adaylar"] else "bulunamadi"})
    return {"toplam_ad": len(sahip), "kisi_degil_kayit": kd, "eslenen_ad": sum(kaynak.values()), "eslenemeyen": es, "kaynak": kaynak, "kayit_orani": round(sayi_es / sayi_top, 3) if sayi_top else None, "ad_orani": round(sum(kaynak.values()) / (sum(kaynak.values()) + len(es)), 3) if (kaynak or es) else None}
def kimlik_eslenemeyen(gun=30, dizin=None, kisiler=True): return kimlik_olcum(gun, dizin, kisiler)["eslenemeyen"]
def kimlik_view(ad=None, gun=30):  # GET /kimlik[?ad=<ad>]: ad verilirse tek çözüm, yoksa eşlenemeyenler
    if ad: return kimlik_coz(ad)
    return {"eslenemeyen": kimlik_eslenemeyen(gun)}

# ---- toplantı katılımcıları (6 Kasım: 5 Kasım toplantısında asistan katılımcıları yanlış saydı) -----------------------------------
# Kök neden: takvim olayında katılımcılar adres adres gelir (aynı kişi iki alan adıyla iki satır: ad+onmicrosoft adresi, ayrıca adsız ikinci adres; kisi_sayisi
# düzenleyeni de sayar) ve toplantı oturumu bunları kişi kayıtlarına bakmadan okuyup 7 "katılımcı" saydı; kayıt eşlemesini ancak ikinci denemede yaptı.
# Şimdi aktarıcı eşlemeyi kendisi yapar ve hazır bir "KATILIMCILAR" bloğu verir: davetliler (takvim) + toplantıda görülen konuşmacılar, kişi kayıtlarıyla
# (canli/vt-kisi-adres.json = ad, lakap, adresler; posta_vt_kisiler) eşleştirilmiş, bir kişinin bütün adresleri tek satırda; eşleşmeyen açıkça "eşleşmedi".
# Kayıtta bazı adresler birden çok kişide görünür (ortak/yönlendirme adresi): adres tek başına yetmez, adres + ad/lakap/yerel kısım puanı toplanır; tek puan
# lideri yoksa "belirsiz" (tahmin yok). Yalnız okuma; veri bu Mac'te kalır (blok toplantı oturumuna ve izle olayına gider, dosyaya 0600 yazılır).
KAT_YER_DEGIL = {"karsi", "taraf", "konusmaci", "speaker", "unknown", "bilinmeyen", "katilimci", "guest", "misafir", "sen", "you", "siz"}
KAT_UNVAN = {"ceo", "coo", "cto", "cmo", "cfo", "cio", "ciso", "cpo", "cro", "cso", "vp", "gm"}
KAT_HITAP = {"bey", "hanim", "hn", "sayin"}
KAT_SERBEST_POSTA = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com", "live.com", "googlemail.com", "me.com"}
def _kat_kayit(k):  # vt-kisi-adres satırı {adlar, adresler} → {"ad", "adlar": [sözcük listeleri], "tek": {tek sözcüklü takma adlar}, "adresler", "rol"}
    adlar = [str(x) for x in k.get("adlar") or []]; adres = [e for e in (_kim_ep(re.sub(r"\s*\(.*$", "", str(x))) for x in k.get("adresler") or []) if e]
    ad = (adlar[0].split(" · ")[0] if adlar else "").strip(); asil = _kim_sozcukler(ad)
    if not asil or not adres: return None
    sozler, tek, roller = [asil], set(), []
    for x in adlar:
        for parca in x.split(" · "):
            p = parca.strip()
            if not p or ":" in p or ";" in p or len(p) > 40: continue  # "Hitap: …" ve kayıt notu kırıntıları ad değildir
            t = _kim_sozcukler(p)
            if len(t) == 1 and t[0] in KAT_UNVAN: roller.append(p.upper()); continue
            t = [w for w in t if w not in KAT_HITAP]
            if not t or len(t) > 4 or any(ch.isdigit() for ch in p): continue
            if t not in sozler: sozler.append(t)
            if len(t) == 1 and len(t[0]) >= 3: tek.add(t[0])
    if len(asil) > 1:
        for w in tek:
            if w != asil[0]: sozler.append([w, asil[-1]])  # takma ad + soyad ("Ali" → "Ali Kaya")
    return {"ad": ad, "asil": asil, "adlar": sozler, "tek": tek | {asil[0]}, "adresler": adres, "rol": next(iter(dict.fromkeys(roller)), None)}
def _kat_puan(kay, ad_q, ep):  # bir davetliye (ad sözcükleri, e-posta) bu kişi kaydının uyum puanı
    p = 0
    if ep and ep in kay["adresler"]: p += 2
    if ad_q:
        u = [_kim_uyum(ad_q, t) for t in kay["adlar"]]
        if "tam" in u: p += 3
        elif "kismi" in u: p += 1
    if ep and _kat_yerel_uyar(kay, ep): p += 2
    return p
def _kat_yerel_uyar(kay, ep):  # adresin yerel kısmı kişinin bir takma adı, bir adının ilk sözcüğü ya da ad+soyad birleşimi mi (ortak/yanlış kayıtlı adresi ayıklar)
    yerel = re.sub(r"[^a-z]", "", ep.split("@")[0])
    return bool(yerel) and (yerel in kay["tek"] or any(len(t[0]) >= 4 and t[0] == yerel for t in kay["adlar"]) or yerel == "".join(kay["asil"]) or yerel == kay["asil"][0] + kay["asil"][-1])
def _kat_bul(kayitlar, ad, ep):  # → (kayıt | None, adaylar [ad])
    q = _kim_sozcukler(ad) if ad and not _KIM_EPOSTA_RX.search(str(ad)) else []
    pu = sorted(((_kat_puan(k, q, ep), i) for i, k in enumerate(kayitlar)), reverse=True)
    pu = [x for x in pu if x[0] >= 2]
    if not pu: return None, []
    if len(pu) == 1 or pu[0][0] > pu[1][0]: return kayitlar[pu[0][1]], []
    return None, [kayitlar[i]["ad"] for s, i in pu if s == pu[0][0]][:4]
def _kat_ben_mi(ad, ep):
    ben, ben_ep = kimlik_ben(); q = _kim_sozcukler(ad) if ad and not _KIM_EPOSTA_RX.search(str(ad)) else []
    return bool((ep and ben_ep and ep == ben_ep) or (len(q) >= 2 and ben and _kim_uyum(q, ben) in ("tam", "kismi")))  # tek ad başka bir kişi olabilir
def _kat_gercek_ad(ad):
    q = _kim_sozcukler(ad)
    return bool(q) and q[0] not in KAT_YER_DEGIL and not (len(q) == 1 and q[0] in KAT_YER_DEGIL)
def katilimci_coz(olay, gorulen=None, kayitlar=None):
    """olay: takvim olayı (kisiler, katilimci_eposta, katilimcilar, duzenleyen, ben_duzenleyen); gorulen: toplantıda konuşan adlar; kayitlar: kişi kayıtları (yoksa posta_vt_kisiler).
    → {"kisiler": [{ad, rol, adresler (davetli), kayitta (davette olmayan adresler), davetli, gorundu}], "eslesmeyen": [{ad, eposta, davetli, gorundu, adaylar}], "ben": ad, "adres_sayisi", "satir_sayisi"}"""
    if kayitlar is None: kayitlar = (globals().get("posta_vt_kisiler") or (lambda: []))()
    kayitlar = [x for x in (_kat_kayit(k) for k in kayitlar if isinstance(k, dict)) if x]
    olay = olay if isinstance(olay, dict) else {}
    satirlar = []  # (ad | None, eposta | None) — takvim her adresi ayrı satır verir; ad ve adres aynı kişi için iki satırda da olabilir
    for k in olay.get("kisiler") or []:
        if isinstance(k, dict): satirlar.append((str(k.get("ad") or "").strip() or None, _kim_ep(k.get("eposta"))))
    gorulen_ep = {s[1] for s in satirlar if s[1]}
    for x in olay.get("katilimci_eposta") or []:
        ep = _kim_ep(x)
        if ep and ep not in gorulen_ep: satirlar.append((None, ep))
    if not satirlar:
        for x in olay.get("katilimcilar") or []:
            ep = _kim_ep(x); satirlar.append((None if ep else str(x).strip() or None, ep))
    adresler_say = len({s[1] for s in satirlar if s[1]})
    kisiler, eslesmeyen, ben_ad = {}, {}, None
    for ad, ep in satirlar:
        if ad and _KIM_EPOSTA_RX.fullmatch(ad.strip().lower()): ad = None  # takvim adres yokluğunda adres yerine adres yazar
        if not ad and not ep: continue
        if _kat_ben_mi(ad, ep): ben_ad = ben_ad or (ad if ad and not _KIM_EPOSTA_RX.search(ad) else None); continue  # düzenleyen/kullanıcı davetli satırında da çıkar
        kay, aday = _kat_bul(kayitlar, ad, ep)
        if kay and kay["asil"] == kimlik_ben()[0]: continue
        if kay:
            d = kisiler.setdefault(kay["ad"], {"ad": kay["ad"], "rol": kay["rol"], "adresler": [], "davetli": True, "gorundu": False, "_kay": kay})
            if ep and ep not in d["adresler"]: d["adresler"].append(ep)
            continue
        anahtar = _kim_anahtar(ad) or ep
        d = eslesmeyen.setdefault(anahtar, {"ad": ad, "eposta": [], "davetli": True, "gorundu": False, "adaylar": []})
        if ep and ep not in d["eposta"]: d["eposta"].append(ep)
        d["ad"] = d["ad"] or ad; d["adaylar"] = sorted(set(d["adaylar"]) | set(aday))
    # adsız eşleşmeyen adres, aynı kişinin adlı satırıyla birleşir (adres yerel kısmı eşleşmeyen adlı kişiyle aynı: "ali@" + "Ali Kaya")
    for a in list(eslesmeyen):
        d = eslesmeyen.get(a)
        if not d or d["ad"] or not d["eposta"]: continue
        yerel = re.sub(r"[^a-z]", "", d["eposta"][0].split("@")[0])
        hedef = [x for k, x in eslesmeyen.items() if x is not d and x["ad"] and yerel and len(yerel) >= 3 and _kim_sozcukler(x["ad"])[:1] == [yerel]]
        if len(hedef) == 1: hedef[0]["eposta"] += [e for e in d["eposta"] if e not in hedef[0]["eposta"]]; del eslesmeyen[a]
    # toplantıda görülenler (konuşmacı adları): kayıtla eşleşirse davetliyle aynı kişi
    for ad in gorulen or []:
        if not _kat_gercek_ad(ad) or _kat_ben_mi(ad, None): continue
        kay, aday = _kat_bul(kayitlar, ad, None)
        if kay:
            d = kisiler.setdefault(kay["ad"], {"ad": kay["ad"], "rol": kay["rol"], "adresler": [], "davetli": False, "gorundu": True, "_kay": kay}); d["gorundu"] = True; continue
        q = _kim_sozcukler(ad); es = next((x for x in eslesmeyen.values() if x["ad"] and _kim_uyum(q, _kim_sozcukler(x["ad"])) in ("tam", "kismi")), None)
        if es: es["gorundu"] = True; continue
        eslesmeyen.setdefault("g:" + _kim_anahtar(ad), {"ad": ad, "eposta": [], "davetli": False, "gorundu": True, "adaylar": aday})
    for d in kisiler.values():
        kay = d.pop("_kay"); d["kayitta"] = [e for e in kay["adresler"] if e not in d["adresler"] and not _kim_sistem(e) and e.split("@")[1] not in KAT_SERBEST_POSTA and (_kat_yerel_uyar(kay, e) or any(len(t[0]) >= 4 and re.sub(r"[^a-z]", "", e.split("@")[0]).startswith(t[0]) for t in kay["adlar"]))][:3]  # davidmut@ ~ David
        d["adresler"].sort(key=lambda e: (_kim_sistem(e), e))
    return {"kisiler": sorted(kisiler.values(), key=lambda d: (not d["davetli"], d["ad"])), "eslesmeyen": list(eslesmeyen.values()), "ben": ben_ad or olay.get("duzenleyen") or kimlik_ben()[0] and " ".join(kimlik_ben()[0]) or None,
            "adres_sayisi": adresler_say, "satir_sayisi": len(satirlar), "kisi_sayisi_takvim": olay.get("kisi_sayisi")}
def katilimci_blogu(r):
    """katilimci_coz çıktısı → asistana verilecek KATILIMCILAR bloğu (düz metin)."""
    if not r or (not r["kisiler"] and not r["eslesmeyen"]): return "KATILIMCILAR: davet listesi ve görülen konuşmacı yok (takvimsiz toplantı); kişi sorulursa «bilmiyorum» de, tahmin etme."
    dav = [d for d in r["kisiler"] if d["davetli"]]; dav_es = [d for d in r["eslesmeyen"] if d["davetli"]]
    satir = ["KATILIMCILAR (takvim daveti + toplantıda görülenler, kişi kayıtlarıyla eşleştirilmiş; kişi sayısını bu listeden say, adres sayısından değil):"]
    satir.append(f"- Davet: {r['adres_sayisi']} adres → {len(dav)} kişi eşleşti" + (f", {len(dav_es)} eşleşmedi" if dav_es else "") + f"; kullanıcı ({r['ben'] or 'sen'}) düzenleyen olarak ayrıca."
                 + (f" (Takvimin 'kişi sayısı' {r['kisi_sayisi_takvim']}: düzenleyen dahil, adres sayar.)" if r.get("kisi_sayisi_takvim") else ""))
    for d in r["kisiler"]:
        durum = ("davetli" if d["davetli"] else "davette yok") + (" · toplantıda görüldü" if d["gorundu"] else (" · henüz konuşmadı" if d["davetli"] else ""))
        satir.append(f"- {d['ad']}" + (f" ({d['rol']})" if d["rol"] else "") + (" — " + ", ".join(d["adresler"]) if d["adresler"] else "") + f" — {durum}"
                     + (f" · kayıtta ayrıca: {', '.join(d['kayitta'])}" if d["kayitta"] else ""))
    for d in r["eslesmeyen"]:
        ad = d["ad"] or "(adsız)"; ek = ", ".join(d["eposta"])
        durum = ("davetli" if d["davetli"] else "davette yok") + (" · toplantıda görüldü" if d["gorundu"] else "")
        satir.append(f"- EŞLEŞMEDİ: {ad}" + (f" — {ek}" if ek else "") + f" — {durum}; kişi kaydında yok" + (f" (olası: {', '.join(d['adaylar'])}; ayırt edilemedi)" if d["adaylar"] else "") + " — kim olduğunu uydurma, sorulursa böyle söyle.")
    return "\n".join(satir)
def katilimci_gorulen(dosya=None):  # toplantıda konuşan adlar (yakalanan satırlar, en çok konuşandan): aktif toplantı dosyasının konuşma payı
    g = globals(); d = dosya or (g["aktif_dosya"]() if g.get("aktif_dosya") else None); p = (g.get("PAY") or {}).get(d) if d else None
    return [k for k, _ in sorted(((p or {}).get("top") or {}).items(), key=lambda x: -x[1])] if p else []
def katilimci_view(olay=None, gorulen=None):  # GET /katilimcilar: {"blok": metin, "kisi": n, "eslesmeyen": n, "t"}; olay yoksa takvim-secilen.json'daki
    if olay is None:
        try: olay = (json.load(open(os.path.join(BASE, "takvim-secilen.json"), encoding="utf-8")) or {}).get("olay") or {}
        except (OSError, ValueError): olay = {}
    r = katilimci_coz(olay, katilimci_gorulen() if gorulen is None else gorulen); blok = katilimci_blogu(r)
    return {"ok": True, "blok": blok, "kisi": len(r["kisiler"]), "eslesmeyen": len(r["eslesmeyen"]), "t": round(time.time()), "veri": r}
