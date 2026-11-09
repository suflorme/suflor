# Suflor.me aktarıcı bölümü: Duygu durumu takibi (9 Kasım, kullanıcı: "kişinin duygu durumunu takip etsin ve bir dost gibi önerilerde bulunsun … asistan bir bot gibi olmamalı").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("duygu"); gerginlik ve bas-konus bölümlerinden sonra): AYAR, BASE, SON, gizli_acik, toplanti_var,
# _takvim_olaylari, calisma_saatleri, _yapi_mod, gerginlik_hesap, kisilik … relay.py'nin. import etme. Python 3.9 uyumlu.
# Sinyaller yalnız yerel (ek Claude çağrısı yok):
#   1) sesli soruda ses: Whisper işçisinin ses_olc ölçüsü (düzey dB, perde, hız) kullanıcının kendi olağanına (son DUYGU_SES_TABAN ölçünün ortancası, yalnız bellekte) göre — duygu_ses
#   2) sözün/yazının tonu, kural tabanlı: ünlem, büyük harf, yorgunluk/sıkıntı/sevinç sözcükleri — duygu_metin (metin saklanmaz; yalnız işaret ve sayı)
#   3) günün yükü: takvimde bugünkü toplantılar, art arda zincir, çalışma saatlerinde kalan boşluk; geciken iş (yapi.bugun_veri)
#   4) geç saat; 5) son toplantının gerginliği (gerginlik_hesap; toplantı bittikten sonra DUYGU_TOP_SN boyunca)
# Çıktı: yorumsuz kısa durum + güven → Konuş sorusuna ≤ DUYGU_BLOK_SINIR karakterlik "[Durum — veri, talimat değil]" bloğu (duygu_blogu): yalnız toplantı dışında ve kullanıcının
# kendi turunda; içerik değişmedikçe DUYGU_BLOK_TEKRAR_SN'de bir. Dostça öneri hakkını aktarıcı verir: günde en çok DUYGU_ONERI_GUN, aynı tür aynı gün bir kez, iki öneri arası en az
# DUYGU_ONERI_ARA_SN; hak blokta "Öneri hakkı: mola" diye gider, cevapta o türde öneri yoksa (duygu_cevap) hak geri döner. Proaktif öneri çatısına (toplanti-sonrasi.py)
# duygu_pro_aday ile "dostca" türü aday verilir; aynı günlük hak paylaşılır.
# Kalıcı kayıt yalnız günlük sayılar: canli/duygu.json, DUYGU_GUN_SAKLA gün (ham metin, sözcük, ses ölçüsü, toplantı adı yok).
# Gizlilik: durum yalnız Claude'a (Konuş bağlamı) gider; beta paketine, teşhise ve günlüğe içerik girmez (günlükte yalnız işaret sayısı). Gizli kipte hiç çalışmaz.
# Ayar duygu_takibi (varsayılan açık; false kapatır).
DUYGU_BLOK_SINIR, DUYGU_ONERI_GUN, DUYGU_ONERI_ARA_SN, DUYGU_GUN_SAKLA = 300, 2, 3 * 3600, 7
DUYGU_SES_TABAN, DUYGU_SES_SN, DUYGU_YAZI_SN, DUYGU_TOP_SN, DUYGU_ISLER_SN, DUYGU_BLOK_TEKRAR_SN = 30, 1800, 1800, 3 * 3600, 300, 1800
DUYGU_ZINCIR_DK, DUYGU_BOSLUK_DK = 10, 30  # iki toplantı arası ≤ 10 dk → art arda; çalışma saatlerinde ≥ 30 dk boşluk yoksa "boşluk yok"
DUYGU_DOSYA = "duygu.json"
_DUY = {"yuklendi": False, "gunler": {}, "ses": [], "ses_son": None, "yazi": [], "isler": (0.0, None), "top": {}, "hak": None, "son_blok": (None, 0.0), "kilit": threading.Lock()}
DUYGU_YORGUN = re.compile(r"(?i)\b(yoruldum|yorgunum|yorgun\w*|bitkin\w*|tükendim|tükenmiş\w*|uykusuz\w*|uyuyamadım|uykum var|halsiz\w*|enerjim yok|"
                          r"tired|exhausted|worn out|sleepy|drained)\b")
DUYGU_SIKINTI = re.compile(r"(?i)(\b(stres\w*|gergin\w*|bunaldım|bunalmış\w*|sinir\w*|bıktım|bıkmış\w*|sıkıldım|berbat|rezalet|felaket|kafayı yiyeceğim|"
                           r"yetişmiyor|yetiştiremiyorum|yetiştiremeyeceğim|boğuldum|batıyorum|of+|uf+|offf\w*|ya+ ?bu ne|hiçbir şey yolunda|"
                           r"stress\w*|overwhelm\w*|annoy\w*|frustrat\w*|fed up|awful|terrible|ugh+)\b)")
DUYGU_OLUMLU = re.compile(r"(?i)\b(süper|harika|mükemmel|şahane|oh be|sevindim|yaşasın|hallettim|bitirdim|başardım|helal|çok iyi|keyfim yerinde|"
                          r"great|awesome|amazing|nailed it|finally done|so happy)\b")
DUYGU_TUR = ("uyku", "mola", "oncelik", "ertele")  # öneri türleri, öncelik sırasıyla
# cevapta o türde öneri yapıldı mı (yoksa hak geri döner); kural tabanlı, kaba
DUYGU_TUR_RX = {"uyku": re.compile(r"(?i)\b(uyu\w*|yat\w*|dinlen\w*|yarına bırak\w*|yarın devam|sleep|rest|call it a (day|night)|tomorrow)\b"),
                "mola": re.compile(r"(?i)\b(mola|ara ver\w*|nefes al\w*|su iç\w*|bir su|kalk\w*|yürü\w*|hava al\w*|kahve|çay|dinlen\w*|break|stretch|water|breathe|walk)\b"),
                "oncelik": re.compile(r"(?i)\b(öncelik\w*|önce \w+|sıraya koy\w*|sırala\w*|tek (bir )?iş\w*|birini seç\w*|en önemli\w*|priorit\w*|one thing|first)\b"),
                "ertele": re.compile(r"(?i)\b(ertele\w*|ileri (bir )?(güne|tarihe) al\w*|cumaya al\w*|yarına al\w*|kaydır\w*|postpone|push (it )?back|move it to)\b")}

def duygu_acik(): return AYAR.get("duygu_takibi", True) is not False and not gizli_acik()

def _duy_tarih(simdi=None): return datetime.date.fromtimestamp(simdi or time.time()).isoformat()
def _duy_yukle():
    if _DUY["yuklendi"]: return
    _DUY["yuklendi"] = True
    try:
        with open(os.path.join(BASE, DUYGU_DOSYA), encoding="utf-8") as f: v = json.load(f)
        g = v.get("gunler") if isinstance(v, dict) else None
        if isinstance(g, dict): _DUY["gunler"] = {str(k): {a: b for a, b in d.items() if isinstance(b, (int, float)) or (a == "oneri_tur" and isinstance(b, list))} for k, d in g.items() if isinstance(d, dict)}
    except (OSError, ValueError, AttributeError, TypeError): pass
def _duy_yaz():
    gunler = dict(sorted(_DUY["gunler"].items())[-DUYGU_GUN_SAKLA:]); _DUY["gunler"] = gunler
    y = os.path.join(BASE, DUYGU_DOSYA)
    try:
        with open(y + ".tmp", "w", encoding="utf-8") as f: json.dump({"surum": 1, "aciklama": "günlük sayılar; metin yok", "gunler": gunler}, f, ensure_ascii=False)
        os.replace(y + ".tmp", y)
    except OSError: pass
def _duy_gun(simdi=None):
    _duy_yukle(); return _DUY["gunler"].setdefault(_duy_tarih(simdi), {})
def _duy_say(alan, n=1, simdi=None, yaz=True):
    g = _duy_gun(simdi); g[alan] = max(0, int(g.get(alan) or 0) + n)
    if yaz: _duy_yaz()
def _ortanca(x): x = sorted(x); return x[len(x) // 2] if x else None

# --- 1) sesli soruda ses ---------------------------------------------------------------------------------------------------------------------------
def duygu_ses(o, simdi=None):  # o: {"db", "f0", "hiz" ya da "kelime"+"sure"} (whisper-isci ses_olc). → {"puan", "isaret"} ya da None (ölçü yok, kapalı ya da taban yok)
    if not duygu_acik() or not isinstance(o, dict): return None
    simdi = simdi or time.time(); o = dict(o)
    if not o.get("hiz") and o.get("kelime") and o.get("sure"): o["hiz"] = round(float(o["kelime"]) / max(0.5, float(o["sure"])) * 60)
    olc = {k: float(o[k]) for k in ("db", "f0", "hiz") if isinstance(o.get(k), (int, float)) and o[k]}
    if not olc: return None
    with _DUY["kilit"]:
        onceki = list(_DUY["ses"]); _DUY["ses"] = (onceki + [olc])[-DUYGU_SES_TABAN:]
        taban = {k: _ortanca([x[k] for x in onceki if k in x]) for k in ("db", "f0", "hiz") if sum(1 for x in onceki if k in x) >= 4}
        if not taban: _duy_say("ses_olcum", simdi=simdi); return None
        isaret = []
        if "db" in olc and "db" in taban:
            if olc["db"] > taban["db"] + 6: isaret.append("yuksek")
            elif olc["db"] < taban["db"] - 6: isaret.append("alcak")
        if "f0" in olc and "f0" in taban and olc["f0"] > taban["f0"] * 1.2: isaret.append("perde")
        if "hiz" in olc and "hiz" in taban:
            if olc["hiz"] > taban["hiz"] * 1.3: isaret.append("hizli")
            elif olc["hiz"] < taban["hiz"] * 0.7: isaret.append("yavas")
        p = round(min(1.0, 0.4 * ("yuksek" in isaret) + 0.3 * ("perde" in isaret) + 0.3 * ("hizli" in isaret)), 2)
        _DUY["ses_son"] = {"t": simdi, "puan": p, "isaret": isaret}
        _duy_say("ses_olcum", yaz=False, simdi=simdi)
        if p >= 0.6: _duy_say("ses_gergin", yaz=False, simdi=simdi)
        if "alcak" in isaret and "yavas" in isaret: _duy_say("ses_dusuk", yaz=False, simdi=simdi)
        _duy_yaz()
    if isaret: print(f"DUYGU: sesli soru — {len(isaret)} işaret (puan {p})")  # günlüğe yalnız sayı
    return {"puan": p, "isaret": isaret}

# --- 2) sözün/yazının tonu --------------------------------------------------------------------------------------------------------------------------
def duygu_metin_isaret(metin):  # saf: metin → işaret kümesi (yorgun, sikinti, olumlu, unlem, buyuk); metin saklanmaz
    s = str(metin or ""); i = set()
    if DUYGU_YORGUN.search(s): i.add("yorgun")
    if DUYGU_SIKINTI.search(s): i.add("sikinti")
    if DUYGU_OLUMLU.search(s): i.add("olumlu")
    if s.count("!") >= 2 or "!!" in s: i.add("unlem")
    if len(re.findall(r"\b[A-ZÇĞİÖŞÜ]{4,}\b", s)) >= 2: i.add("buyuk")
    return i
def duygu_metin(metin, simdi=None):  # Konuş sorusu (ses ya da yazı) → işaretler; bellekte (zaman, işaret), günlük sayılar dosyada
    if not duygu_acik() or not metin: return set()
    simdi = simdi or time.time(); i = duygu_metin_isaret(metin)
    with _DUY["kilit"]:
        _DUY["yazi"] = [x for x in _DUY["yazi"] if simdi - x[0] <= DUYGU_YAZI_SN][-20:] + ([(simdi, frozenset(i))] if i else [])
        for k in ("yorgun", "sikinti", "olumlu"):
            if k in i: _duy_say("soz_" + k, yaz=False, simdi=simdi)
        if i: _duy_yaz()
    return i

# --- 3) günün yükü ---------------------------------------------------------------------------------------------------------------------------------
def _duy_dt(simdi): return datetime.datetime.fromtimestamp(simdi).astimezone()
def duygu_takvim_yuk(olaylar, simdi_dt, saatler=None):  # saf: [(başlangıç, bitiş, olay)] (bugünün) → {"toplanti", "kalan", "zincir", "bosluk_yok"}
    ol = sorted([(b, s) for b, s, e in olaylar if not (e or {}).get("tum_gun") and not (e or {}).get("reddettin")], key=lambda x: x[0])
    out = {"toplanti": len(ol), "kalan": sum(1 for b, s in ol if b > simdi_dt), "zincir": 0, "bosluk_yok": False}
    z = 1 if ol else 0; en = z
    for (b0, s0), (b1, s1) in zip(ol, ol[1:]):
        z = z + 1 if (b1 - s0).total_seconds() <= DUYGU_ZINCIR_DK * 60 else 1; en = max(en, z)
    out["zincir"] = en
    g, gb, ge = saatler or ({0, 1, 2, 3, 4}, 540, 1080)
    if simdi_dt.weekday() in g:
        g0 = simdi_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        bas, son = max(simdi_dt, g0 + datetime.timedelta(minutes=gb)), g0 + datetime.timedelta(minutes=ge)
        if bas < son and out["kalan"]:
            imlec, bos = bas, False
            for b, s in ol:
                if s <= imlec: continue
                if b >= son: break
                if (b - imlec).total_seconds() >= DUYGU_BOSLUK_DK * 60: bos = True; break
                imlec = max(imlec, s)
            if not bos and (son - imlec).total_seconds() >= DUYGU_BOSLUK_DK * 60: bos = True
            out["bosluk_yok"] = not bos
    return out
def _duy_takvim(simdi):
    f = globals().get("_takvim_olaylari")
    if not f: return None
    d = _duy_dt(simdi); g0 = d.replace(hour=0, minute=0, second=0, microsecond=0)
    try: ol = f(g0, g0 + datetime.timedelta(days=1))
    except Exception: return None
    try: sa = calisma_saatleri() if "calisma_saatleri" in globals() else None
    except Exception: sa = None
    return duygu_takvim_yuk(ol, d, sa)
def _duy_isler(simdi):  # → {"gecikmis", "bugun"} ya da None; DUYGU_ISLER_SN önbellekli (karar grafı okuması her soruda olmasın)
    t, v = _DUY["isler"]
    if v is not None and simdi - t < DUYGU_ISLER_SN: return v
    y = _yapi_mod() if "_yapi_mod" in globals() else None
    if not y: return None
    try: b = y.bugun_veri(BASE, str(AYAR.get("ad") or ""))
    except Exception: return None
    k = [x for x in (b or {}).get("kendi") or [] if not x.get("geride")]
    v = {"gecikmis": sum(1 for x in k if x.get("gecikti")), "bugun": sum(1 for x in k if not x.get("gecikti") and x.get("kalan_gun") == 0)}
    _DUY["isler"] = (simdi, v); return v

# --- 5) son toplantının gerginliği -----------------------------------------------------------------------------------------------------------------
def _duy_son_toplanti(simdi):  # → {"duzey", "puan"} (biten toplantının en gergin 3 dakikası) ya da None; dosya + mtime başına bir kez hesaplanır
    if "gerginlik_hesap" not in globals(): return None
    r = next((x for x in reversed(globals().get("SON") or []) if isinstance(x, dict) and x.get("dosya")), None)
    if not r or simdi - float(r.get("t") or 0) > DUYGU_TOP_SN or r.get("gizli"): return None
    y = _yapi_mod() if "_yapi_mod" in globals() else None
    try:
        if y and y.gizli_mi(BASE, str(r["dosya"])[:-3] if str(r["dosya"]).endswith(".md") else str(r["dosya"])): return None
    except Exception: pass
    jl = os.path.join(BASE, str(r["dosya"]).replace(".md", ".jsonl"))
    try: mt = os.path.getmtime(jl)
    except OSError: return None
    k = (jl, mt)
    if k in _DUY["top"]: return _DUY["top"][k]
    try: sat = [json.loads(x) for x in open(jl, encoding="utf-8").read().splitlines() if x.strip()]
    except (OSError, ValueError): return None
    zs = [z for z in (_gergin_zaman(x) for x in sat) if z] if "_gergin_zaman" in globals() else []
    en = None
    if zs:
        t = min(zs) + 180
        while t <= max(zs) + 180:
            g = gerginlik_hesap(sat, simdi=t)
            if en is None or g["puan"] > en["puan"]: en = {"duzey": g["duzey"], "puan": g["puan"]}
            t += 180
    _DUY["top"] = {k: en}; return en

# --- durum, blok, öneri hakkı ---------------------------------------------------------------------------------------------------------------------
def duygu_durum(simdi=None):  # → {"parca": [(öncelik, metin)], "kategori": küme, "guven", "sinyal": {...}}; okuma (öneri hakkı vermez)
    simdi = simdi or time.time(); parca, kat, sin = [], set(), {}
    tk = _duy_takvim(simdi); sin["takvim"] = tk
    if tk and tk["toplanti"]:
        yogun = tk["toplanti"] >= 5 or tk["zincir"] >= 3 or (tk["bosluk_yok"] and tk["kalan"] >= 2)
        if yogun: kat.add("yuk")
        m = _t(f"{'yoğun gün: ' if yogun else 'bugün '}{tk['toplanti']} toplantı ({tk['kalan']} kaldı)", f"{'busy day: ' if yogun else 'today '}{tk['toplanti']} meetings ({tk['kalan']} left)")
        if tk["zincir"] >= 2: m += _t(f", {tk['zincir']} art arda", f", {tk['zincir']} back to back")
        if tk["bosluk_yok"]: m += _t(", arada boşluk yok", ", no gap left")
        parca.append((1 if yogun else 5, m))
    isl = _duy_isler(simdi); sin["isler"] = isl
    if isl and isl["gecikmis"]:
        parca.append((2, _t(f"{isl['gecikmis']} iş gecikmiş", f"{isl['gecikmis']} tasks overdue")))
        if isl["gecikmis"] >= 2: kat.add("is")
    s = _DUY["ses_son"]
    if s and simdi - s["t"] <= DUYGU_SES_SN and s["isaret"]:
        i = s["isaret"]; sin["ses"] = s
        if s["puan"] >= 0.6: kat.add("ses"); parca.append((1, _t("son sesli soruda ses olağandan yüksek ve hızlı", "last spoken question louder and faster than usual")))
        elif "alcak" in i and "yavas" in i: kat.add("ses"); parca.append((2, _t("son sesli soruda ses olağandan alçak ve yavaş", "last spoken question quieter and slower than usual")))
    yz = [x for x in _DUY["yazi"] if simdi - x[0] <= DUYGU_YAZI_SN]
    if yz:
        say = {k: sum(1 for _, i in yz if k in i) for k in ("yorgun", "sikinti", "olumlu", "unlem", "buyuk")}; sin["soz"] = say
        if say["yorgun"]: kat.add("soz"); parca.append((1, _t("sözlerinde yorgunluk geçti", "mentioned being tired")))
        if say["sikinti"] or say["buyuk"] or say["unlem"] >= 2: kat.add("soz"); parca.append((2, _t("sözlerinde sıkıntı işareti", "signs of frustration in wording")))
        if say["olumlu"] and not (say["yorgun"] or say["sikinti"]): parca.append((3, _t("sözleri keyifli", "upbeat wording")))
    d = _duy_dt(simdi)
    if d.hour >= 23 or d.hour < 5: kat.add("saat"); parca.append((1, _t(f"geç saat ({d.strftime('%H.%M')})", f"late hour ({d.strftime('%H:%M')})")))
    top = _duy_son_toplanti(simdi); sin["toplanti"] = top
    if top and top["duzey"] != "sakin":
        kat.add("toplanti"); parca.append((2, _t(f"son toplantı {'gergindi' if top['duzey'] == 'gergin' else 'biraz gergindi'}", f"last meeting was {'tense' if top['duzey'] == 'gergin' else 'a little tense'}")))
    duygu_kat = kat & {"ses", "soz", "toplanti"}
    guven = "yuksek" if len(kat) >= 3 else "orta" if len(kat) == 2 else "dusuk"
    return {"parca": sorted(parca, key=lambda x: x[0]), "kategori": kat, "duygu": duygu_kat, "guven": guven, "sinyal": sin}

def duygu_oneri_turu(d, simdi=None):  # → öneri türü ya da None; hak kuralları (günlük sınır, tür tekrarı, ara) burada
    simdi = simdi or time.time(); g = _duy_gun(simdi); kat = d["kategori"]; isl = d["sinyal"].get("isler") or {}; tk = d["sinyal"].get("takvim") or {}
    if int(g.get("oneri") or 0) >= DUYGU_ONERI_GUN: return None
    if simdi - float(g.get("oneri_son_t") or 0) < DUYGU_ONERI_ARA_SN: return None
    guclu = "saat" in kat or (tk.get("zincir") or 0) >= 3 or len(kat) >= 2
    if not guclu: return None
    aday = []
    if "saat" in kat: aday.append("uyku")
    if "yuk" in kat or d["duygu"]: aday.append("mola")
    if (isl.get("gecikmis") or 0) >= 3 or ((isl.get("gecikmis") or 0) >= 1 and "yuk" in kat): aday.append("oncelik")
    if (isl.get("gecikmis") or 0) >= 1 and "yuk" in kat: aday.append("ertele")
    kul = set(g.get("oneri_tur") or [])
    return next((x for x in DUYGU_TUR if x in aday and x not in kul), None)

def _duy_hak_ver(tur, simdi, kaynak="konus"):
    g = _duy_gun(simdi); g["oneri"] = int(g.get("oneri") or 0) + 1; g["oneri_son_t"] = simdi
    g["oneri_tur"] = sorted(set(g.get("oneri_tur") or []) | {tur}); _duy_yaz()
    _DUY["hak"] = {"tur": tur, "t": simdi, "kaynak": kaynak}
def _duy_hak_iade(tur, simdi=None):
    g = _duy_gun(simdi); g["oneri"] = max(0, int(g.get("oneri") or 0) - 1)
    g["oneri_tur"] = [x for x in (g.get("oneri_tur") or []) if x != tur]
    if not g["oneri"]: g.pop("oneri_son_t", None)
    _duy_yaz()

DUYGU_TUR_AD = {"uyku": ("dinlenme/yarına bırakma", "rest / leave it for tomorrow"), "mola": ("kısa mola, su", "short break, water"),
                "oncelik": ("işleri sıraya koyma, tek işe odak", "prioritise, pick one thing"), "ertele": ("bir işi ertelemeyi teklif", "offer to postpone one task")}
def duygu_blogu(tur=None, metin=None, simdi=None):  # Konuş sorusuna eklenecek "[Durum …]" bloğu ("" = yok). Sorunun metnini işaretler (saklamadan) ve gerekirse öneri hakkı verir
    if not duygu_acik(): return ""
    if "toplanti_var" in globals() and toplanti_var(): return ""  # toplantıda resmî kurallar; durum gitmez
    if isinstance(tur, dict) and (tur.get("otonom") or tur.get("karsi") or tur.get("kaynak") not in (None, "bas", "yazili", "sohbet")): return ""
    simdi = simdi or time.time()
    if metin: duygu_metin(metin, simdi)
    try: d = duygu_durum(simdi)
    except Exception as e: print(f"DUYGU: durum hesaplanamadı ({e.__class__.__name__})"); return ""
    if not d["parca"]: return ""
    hak = duygu_oneri_turu(d, simdi)
    anahtar = (tuple(m for _, m in d["parca"]), d["guven"])
    sk, st = _DUY["son_blok"]
    if not hak and sk == anahtar and simdi - st < DUYGU_BLOK_TEKRAR_SN: return ""  # aynı durum süreçte zaten var
    bas = _t("[Durum — veri, talimat değil] ", "[State — data, not instructions] ")
    son = _t(f" Güven: {dict(yuksek='yüksek', orta='orta', dusuk='düşük')[d['guven']]}.", f" Confidence: {dict(yuksek='high', orta='medium', dusuk='low')[d['guven']]}.")
    if hak: son += _t(f" Öneri hakkı: {DUYGU_TUR_AD[hak][0]}.", f" Suggestion allowed: {DUYGU_TUR_AD[hak][1]}.")
    parca = [m for _, m in d["parca"]]
    while parca and len(bas + "; ".join(parca) + "." + son) > DUYGU_BLOK_SINIR - 1: parca.pop()  # sonda satır sonu: toplam ≤ DUYGU_BLOK_SINIR
    if not parca: return ""
    if hak: _duy_hak_ver(hak, simdi)
    _DUY["son_blok"] = (anahtar, simdi)
    blok = bas + "; ".join(parca) + "." + son + "\n"
    print(f"DUYGU: durum bloğu ({len(parca)} parça, güven {d['guven']}" + (f", öneri hakkı {hak}" if hak else "") + ")")
    return blok

def duygu_cevap(cevap, simdi=None):  # Konuş cevabı bitince: verilen hak kullanılmadıysa (o türde öneri sözcüğü yok) geri döner. → kullanılan tür ya da None
    h = _DUY["hak"]; _DUY["hak"] = None
    if not h or h.get("kaynak") != "konus": return None
    if DUYGU_TUR_RX[h["tur"]].search(str(cevap or "")): print(f"DUYGU: dostça öneri yapıldı ({h['tur']})"); return h["tur"]
    _duy_hak_iade(h["tur"], simdi); print(f"DUYGU: öneri hakkı kullanılmadı, geri döndü ({h['tur']})"); return None

# --- proaktif öneri çatısına (toplanti-sonrasi.py pro_gun_tara) dostça aday -------------------------------------------------------------------------------
DUYGU_PRO_CUMLE = {  # (sen, siz, en); {n}: art arda toplantı ya da geciken iş sayısı
    "mola": ("Bugün {n} toplantı art arda geldi. On dakika kalkıp bir su içsen iyi gelir; ben buradayım.",
             "Bugün {n} toplantı art arda geldi. On dakika kalkıp bir su içseniz iyi gelir; ben buradayım.",
             "{n} meetings back to back today. Ten minutes and a glass of water would do you good; I'm here."),
    "oncelik": ("{n} iş gecikmiş, gün de dolu. İstersen bugün için tek birini seçelim, gerisini sıraya koyarım.",
                "{n} iş gecikmiş, gün de dolu. İsterseniz bugün için tek birini seçelim, gerisini sıraya koyarım.",
                "{n} tasks are overdue and the day is full. Want to pick just one for today? I'll queue the rest."),
    "ertele": ("Gün sıkışık görünüyor. Geciken işlerden birini ileri bir güne alalım mı?",
               "Gün sıkışık görünüyor. Geciken işlerden birini ileri bir güne alalım mı?",
               "The day looks tight. Shall we move one of the overdue tasks to a later day?")}
def _duy_bicim():
    k = kisilik() if "kisilik" in globals() else None
    return "en" if ARAYUZ_DILI == "en" else "siz" if k and k.get("bicim") != "sen" else "sen"  # kişiliksiz: sen (9 Kasım)
def duygu_pro_aday(simdi=None):  # → [aday] (en çok bir; toplanti-sonrasi.py aday biçiminde, komutsuz) ya da []
    if not duygu_acik(): return []
    simdi = simdi or time.time()
    try: d = duygu_durum(simdi)
    except Exception: return []
    t = duygu_oneri_turu(d, simdi)
    if t not in DUYGU_PRO_CUMLE: return []  # uyku proaktif sunulmaz (mesai dışında çatı zaten susar)
    tk = d["sinyal"].get("takvim") or {}; isl = d["sinyal"].get("isler") or {}
    n = (tk.get("zincir") or 0) if t == "mola" else (isl.get("gecikmis") or 0)
    if t == "mola" and (n or 0) < 2: return []
    c = DUYGU_PRO_CUMLE[t][{"sen": 0, "siz": 1, "en": 2}[_duy_bicim()]].format(n=n)
    return [{"anahtar": f"duygu:{t}:{_duy_tarih(simdi)}", "tur": "dostca", "alt": t, "cumle": c, "komut": None, "arg": None}]
def duygu_pro_sunuldu(a, simdi=None):  # pro_gun_tara dostça adayı sunduğunda: günlük hak düşer (Konuş'la ortak)
    if isinstance(a, dict) and a.get("tur") == "dostca" and a.get("alt"):
        _duy_hak_ver(a["alt"], simdi or time.time(), kaynak="pro"); _DUY["hak"] = None
