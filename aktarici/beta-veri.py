# Suflor.me aktarıcı bölümü: Beta geliştirme verisi (S141, 23 Ekim). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır
# (bolum("beta-veri")): AYAR, STATE, BASE, LOCK, teshis, teshis_gonder, aktif_dosya, toplanti_kimlik, kisilikler … relay.py'nin. import etme.
# Beta kullanıcısı gönüllü geliştirme katılımcısıdır: kullanım, hız ve hata SAYILARI geliştiriciye gider (beta şartı, ayarla kapanmaz).
# Asla gitmez: döküm; kart, soru ve cevap metni; kişi, toplantı, proje, dosya ve asistan adı; e-posta; takvim; ses; ses izi; ekran görüntüsü.
# Buradaki her paket teshis.temizle() izin listesinden geçer (bilinmeyen anahtar "?n", bilinmeyen seçenek "?", serbest metin sözlük süzgecinde).
# 1) Olay sayacı: günlük satırı (teshis_satir → beta_satir) ve birkaç işlev sarmalayıcısı olayın yalnız ADINI ve ZAMANINI tutar
#    (canli/beta-olay.json; satırın kendisi tutulmaz). Toplantı kimliği (dosya adının özeti) → platform, baş/son.
# 2) Haftalık paket: biten ISO haftası için bir kez — kullanım (kullanim.py, olcum.py kullanim ile aynı kural), toplantı sayısı/süresi/
#    platformu, özellik kullanımı, kalite, maliyet (Claude/Gemini çağrı ve simge), ayar profili.
# 3) Toplantı sonu paketine kalite ölçüleri (beta_kalite; relay.py _toplanti_paketi çağırır).
def _kul_yukle():  # kullanim.py aktarıcının yanında (kurulum.py KOPYA); yalnız birkaç dosya kopyalayan testlerde kod klasöründen
    import importlib.util
    for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        y = os.path.join(d, "kullanim.py")
        if d and os.path.isfile(y):
            sp = importlib.util.spec_from_file_location("kullanim", y); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
    return None
_KUL = _kul_yukle()
def _zeka_yukle():  # zeka.py (kurulum.py KOPYA) — haftalık pakette yalnız sayı: işlev puanları ve kullanıcının 1–5 puanları
    import importlib.util
    for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        y = os.path.join(d, "zeka.py")
        if d and os.path.isfile(y):
            try: sp = importlib.util.spec_from_file_location("zeka_beta", y); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
            except Exception: return None
    return None
_ZK = _zeka_yukle()
def _beta_zeka(bas, son):
    if not _ZK: return None
    try: return _ZK.beta_ozet(BASE, bas, son)
    except Exception: return None

BETA_FP = os.path.join(BASE, "beta-olay.json")
BETA = {"olay": [], "toplanti": {}, "hafta": [], "yazildi": 0.0}
BETA_K = threading.Lock()
BETA_OLAY_EN_COK = 6000
BETA_TEST = bool(os.environ.get("SUFLOR_TEST_BETA"))  # test/beta-veri.py: haftalık paket hemen, bu haftanın sayılarıyla
try:
    _b = json.load(open(BETA_FP, encoding="utf-8"))
    BETA.update(olay=[x for x in _b.get("olay", []) if isinstance(x, list) and len(x) == 2][-BETA_OLAY_EN_COK:],
                toplanti={k: v for k, v in (_b.get("toplanti") or {}).items() if isinstance(v, dict)}, hafta=list(_b.get("hafta") or [])[-60:])
except (OSError, ValueError, AttributeError): pass
def beta_olay(ad):
    with BETA_K: BETA["olay"].append([round(time.time(), 1), ad]); del BETA["olay"][:-BETA_OLAY_EN_COK]
def _beta_yaz():
    with BETA_K: veri = {"olay": BETA["olay"], "toplanti": dict(list(BETA["toplanti"].items())[-400:]), "hafta": BETA["hafta"]}
    try:
        gec = BETA_FP + ".tmp"; json.dump(veri, open(gec, "w", encoding="utf-8")); os.replace(gec, BETA_FP); BETA["yazildi"] = time.time()
    except OSError: pass
def beta_say(ad, bas, son):
    with BETA_K: return sum(1 for t, a in BETA["olay"] if a == ad and bas <= t < son)
# günlük satırı → olay adı (satırın metni tutulmaz). Kalıp değişirse bu tablo da: olcum.py deneme aynı satırları okur.
BETA_RX = [("dur", re.compile(r"^ASİSTAN: '.*, dur'$")), ("sus_kisayol", re.compile(r"^ASİSTAN: sustu")),
           ("hitap_yinelenen", re.compile(r"^KONUŞ: aynı hitap sorusu")), ("kanit", re.compile(r"^KANIT \d+: ")),
           ("gizli", re.compile(r"^GİZLİ: açıldı")), ("moderator", re.compile(r"^MODERATÖR: başladı")),
           ("zaman_asimi", re.compile(r"^KONUŞ: .*zaman aşımı")),
           ("on_arama", re.compile(r"^KONUŞ: ön arama \d+ sonuç")), ("on_arama_bos", re.compile(r"^KONUŞ: ön arama sonuç yok")),
           ("oto_izin", re.compile(r"^İZİN: otomatik — "))]  # v0.121.0: proje bilgisine ulaşma
def beta_satir(l):
    for ad, rx in BETA_RX:
        if rx.search(l): beta_olay(ad); return
# kullanıcının açtığı özellik (kapatma sayılmaz): sarmalayıcı yalnız sonucu okur
def _beta_sar(ad, olay, acildi):
    fn = globals().get(ad)
    if not fn or getattr(fn, "_beta", False): return
    def sar(*a, **k):
        r = fn(*a, **k)
        try:
            if acildi(r): beta_olay(olay)
        except Exception: pass
        return r
    sar._beta = True; globals()[ad] = sar
_beta_sar("sessiz_degistir", "sessiz", lambda r: r is True)
_beta_sar("sesli_ceviri_degistir", "sesli_ceviri", lambda r: bool(r and r[0]))
# 13 Kasım: planlı açılış ayrımı + bekleyen yeniden başlatma. Kurulum sihirbazı/güncelleme/aktarici-kur aktarıcıyı yeniden başlatmadan önce
# <uygulama>/planli-acilis.json yazar ({t, neden}: ayar | ses | kurulum | guncelleme | bekleyen); açılışta 10 dk içindeyse "acilis_planli", yoksa
# beklenmedik "acilis" sayılır — kalite.cokme yalnız beklenmedikleri sayar. Toplantı sürerken ayar kaydı yeniden başlatmayı yapmaz, yerine
# <uygulama>/yeniden-baslat-bekliyor.json bırakır (kurulum.py aktarici_yeniden_baslat); toplantı/sohbet bitince buradaki döngü uygular. Paket dosyada yalnız zaman ve kategori.
# --- yeniden-baslat başlangıç (test/beta-veri.py ve test/guncelle-mesgul.py bu bölümü metin olarak çıkarıp sınar) ---
YB_BEKLEYEN = os.path.join(AYAR["uygulama"], "yeniden-baslat-bekliyor.json")
YB_PLANLI = os.path.join(AYAR["uygulama"], "planli-acilis.json")
YB_LABEL = "local.suflor.aktarici"  # kurulum.py LABEL
YB_PLANLI_SN = 600
_YB = {"bos": 0}
def _yb_json(fp):
    try: j = json.load(open(fp, encoding="utf-8"))
    except (OSError, ValueError): return {}
    return j if isinstance(j, dict) else {}
def _yb_yaz(fp, neden):
    try:
        gec = fp + ".tmp"; json.dump({"t": round(time.time()), "neden": neden}, open(gec, "w", encoding="utf-8")); os.replace(gec, fp); return True
    except OSError: return False
def _yb_sil(fp):
    try: os.remove(fp)
    except OSError: pass
def _beta_acilis_say():
    t = _yb_json(YB_PLANLI).get("t")
    planli = isinstance(t, (int, float)) and not isinstance(t, bool) and -5 <= time.time() - t <= YB_PLANLI_SN  # kurulum zamanı saniyeye yuvarlar: biraz ileride görünebilir
    _yb_sil(YB_PLANLI); _yb_sil(YB_BEKLEYEN)  # bu açılış bekleyen yeniden başlatmayı zaten karşıladı
    beta_olay("acilis_planli" if planli else "acilis")
def _beta_acilis_donem(bas, son):  # (beklenmedik, planlı) açılış sayısı
    return beta_say("acilis", bas, son), beta_say("acilis_planli", bas, son)
def _yb_mesgul():  # kurulum.py mesgul() ile aynı ölçüt (orada /status'tan, burada doğrudan durumdan); hata → meşgul say
    try:
        if eklenti_cagri() or masaustu_toplantida() or toplanti_var(): return True
        if (sohbet_view() or {}).get("acik"): return True
        if KONUS.get("durum") in ("yaziya", "dusunuyor", "konusuyor"): return True
        o = toplanti_oturum_view() or {}; od = o.get("durum")
        if od in ("calisiyor", "aciliyor") or o.get("izin") or o.get("izinler"): return True
        if od in ("bekliyor", "izliyor") and o.get("acik_soru"): return True
        if od == "bekliyor" and o.get("sonu"): return True
    except Exception: return True
    return False
def _yb_bizim():  # yalnız bu aktarıcıyı yöneten launchd ajanı (deneme aktarıcısı gerçek ajanı yeniden başlatmasın): plist bu veri klasörünü ve portu içerir
    try: m = open(os.path.expanduser(f"~/Library/LaunchAgents/{YB_LABEL}.plist"), encoding="utf-8").read()
    except OSError: return False
    return os.path.abspath(BASE) in m and f"<string>{A.port}</string>" in m and not BETA_TEST
def _yb_baslat():
    import subprocess
    subprocess.Popen(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{YB_LABEL}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
def _yb_dene(bos_gerek=2):  # dakikada bir: bekleyen işaret varsa ve art arda bos_gerek yoklamada meşgul değilse yeniden başlat
    if not os.path.exists(YB_BEKLEYEN): _YB["bos"] = 0; return "yok"
    if _yb_mesgul(): _YB["bos"] = 0; return "mesgul"
    _YB["bos"] += 1
    if _YB["bos"] < bos_gerek: return "bekle"
    if not _yb_bizim(): _yb_sil(YB_BEKLEYEN); return "bizim_degil"
    _yb_yaz(YB_PLANLI, "bekleyen"); _yb_sil(YB_BEKLEYEN); _yb_baslat(); return "yeniden"
def _yb_dongu():
    time.sleep(60)
    while True:
        try: _yb_dene()
        except Exception as e: print(f"BETA: yeniden başlatma denetimi hata {e.__class__.__name__}")
        time.sleep(60)
# --- yeniden-baslat bitiş ---
_beta_acilis_say()  # aktarıcı açıldı (toplantı sırasında beklenmedik açılış = çökme)
threading.Thread(target=_yb_dongu, daemon=True).start()

def _beta_platform():
    a = TOPLANTI.get("aktif") or {}  # Faz B: toplantının kendi platformu (kayıt); masaüstü uygulaması ayrıca sayılır
    if masaustu_toplantida(): return "masaustu"
    p = str(a.get("platform") or "")
    return p if p in ("teams", "meet", "zoom") else "bilinmeyen"
def _beta_toplanti_izle():  # dakikada bir: süren toplantının kimliği → platform, baş, son (ad tutulmaz)
    f = aktif_dosya()
    if not f: return
    k = toplanti_kimlik(f); simdi = round(time.time())
    with BETA_K:
        r = BETA["toplanti"].setdefault(k, {"bas": simdi, "platform": "bilinmeyen"})
        r["son"] = simdi; p = _beta_platform()
        if p != "bilinmeyen":  # v0.136.0: aynı dosyada iki platform (Meet + masaüstü Teams) → en çok dakika geçen; önceden son görülen yazılıyordu
            dk = r.setdefault("dk", {}); dk[p] = dk.get(p, 0) + 1; r["platform"] = max(dk, key=dk.get)
        r["ceviri"] = r.get("ceviri") or bool("ceviri_acik" in globals() and ceviri_acik())

def _yuzde(xs, q): xs = sorted(xs); return round(xs[min(len(xs) - 1, int(len(xs) * q))], 1) if xs else None
def _ort(xs): return {"n": len(xs), "ortanca": _yuzde(xs, .5), "p90": _yuzde(xs, .9)} if xs else {"n": 0}
def _jsonl(ad):
    out = []
    for l in _KUL.kayit_satirlari(BASE, ad):
        try: out.append(json.loads(l))
        except ValueError: pass
    return out
def _ts(r, k="at"):
    try: return _KUL.zaman(r[k]) if isinstance(r.get(k), str) else float(r[k])
    except (KeyError, TypeError, ValueError): return None
def _beta_konus(rows):  # bas-konus satırları → ilk ses/ilk metin (ms) ve 10 sn'yi aşan cevap oranı
    ses = [r["ses_ms"] for r in rows if isinstance(r.get("ses_ms"), (int, float))]
    ilk = [r["ilk_ms"] for r in rows if isinstance(r.get("ilk_ms"), (int, float))]
    uzun = [r for r in rows if max(r.get("ses_ms") or 0, r.get("ilk_ms") or 0) > 10000]
    return {"cevap": len(rows), "ilk_ses_ms": _ort(ses), "ilk_metin_ms": _ort(ilk), "on_sn_ustu_yuzde": round(100 * len(uzun) / len(rows)) if rows else None,
            "hata": sum(1 for r in rows if r.get("hata"))}
def _beta_sistem(bas, son):  # sistem izi (toplantıda dakikada bir): en az boş bellek, en çok takas
    si = [x for x in _jsonl("sistem-izi.jsonl") if isinstance(x.get("t"), (int, float)) and bas <= x["t"] < son]
    bb = [x["bellek_bos"] for x in si if isinstance(x.get("bellek_bos"), (int, float))]; sw = [x["swap_gb"] for x in si if isinstance(x.get("swap_gb"), (int, float))]
    return {"olcum": len(si), "bellek_bos_en_az": min(bb) if bb else None, "takas_gb_en_cok": max(sw) if sw else None,
            "isi_ciddi_dk": sum(1 for x in si if (x.get("isi") or 0) >= 2)}
# v0.121.0: proje bilgisine ulaşma — Konuş cevabının "bulamadım" türünden olması yerelde sayılır (soru/cevap metni gitmez), veritabanı sorgusu sayısı,
# ön aramanın boş dönmesi; proje veritabanının büyüklüğü (tablo/satır sayısı, kart var mı). Yeniden sıralayıcı ve tablo işinin gerekliliği bu sayılardan.
BULAMADI_RX = re.compile(r"bulamad|kayıtta (yok|bulun)|bilgi(m)? yok|göremiyorum|elimde (yok|bilgi)|couldn'?t find|could not find|no record|don'?t have (that|any) information", re.I)
def _beta_bilgi(bas, son):
    g = [r for r in _jsonl("konus-gecmis.jsonl") if bas <= (_ts(r) or 0) < son]
    sq = [r for r in _jsonl("konus-sorgu.jsonl") if bas <= (_ts(r, "t") or 0) < son]
    return {"konus_cevap": len(g), "bulamadi": sum(1 for r in g if BULAMADI_RX.search(str(r.get("sesli") or "") + " " + str(r.get("ayrinti") or ""))),
            "veritabani_sorgu": len(sq), "on_arama": beta_say("on_arama", bas, son), "on_arama_bos": beta_say("on_arama_bos", bas, son)}
def _beta_proje_vt():
    b = _baglayici_mod()
    if b and (b.ayar_coz(AYAR).get("kayit") or {}).get("yol"): return {"kayit_vt": True, "kuruldu": False}  # yalnız seçenek ve sayı (teshis.temizle: "tur" sabit değerli anahtar)
    try: k = json.load(open(os.path.join(AYAR["uygulama"], "proje-vt.json"), encoding="utf-8"))
    except (OSError, ValueError): return {"kayit_vt": False, "kuruldu": False}
    kart = k.get("kart") if isinstance(k.get("kart"), dict) else {}
    return {"kayit_vt": False, "kuruldu": True, "tablo": int(k.get("tablo") or 0), "satir": int(k.get("satir") or 0), "kart": bool(kart),
            "kart_kisi": int(kart.get("kisi") or 0), "kart_is": int(kart.get("acik_is") or 0), "kart_karar": int(kart.get("karar") or 0)}
def _beta_olaylar(bas, son):
    return {a: beta_say(a, bas, son) for a in ("dur", "sus_kisayol", "hitap_yinelenen", "kanit", "sessiz", "sesli_ceviri", "gizli", "moderator", "zaman_asimi", "sorun", "hata")}

YANKI_ESIK_ADET, YANKI_ESIK_YUZDE = 20, 50  # en az 20 yankı ve oran > %50 → "hoparlor_yankisi"
def _beta_yanki(yanki, ben, tanima=None):  # v0.238.3: ben kanalına sızıp karşıyla aynı olduğu için atılan parçalar / (atılan + ben satırı); yalnız sayı ve seçenek
    top = yanki + ben; oran = round(100 * yanki / top) if top else None
    r = {"yanki": yanki, "ben_satir": ben, "yanki_oran_yuzde": oran,
         "ses_yolu": "hoparlor_yankisi" if (yanki >= YANKI_ESIK_ADET and oran is not None and oran > YANKI_ESIK_YUZDE) else "normal"}
    if tanima and any(tanima.values()): r["tanima"] = {k: int(tanima.get(k) or 0) for k in YANKI_TANIMA_BOLGE}  # ses düzeyinde yankı tanıma: bölge başına parça sayısı
    return r
YANKI_TANIMA_BOLGE = ("yanki", "ara", "yankisiz")  # whisper-hat.py _yt_dongu beta_olay("yanki_tanima_<bölge>")
def beta_kalite(f, bas, son, metin, gec):
    """Toplantı sonu paketine kalite: satır gecikmesi, ilk ses, hitap, yinelenen soru, dur, 10 sn üstü cevap, hata/çökme, bellek/takas."""
    if not (bas and son and _KUL): return {}
    sg = [_KUL.zaman(x["at"]) - x["t1"] for x in metin if isinstance(x.get("t1"), (int, float)) and isinstance(x.get("at"), str)]
    kon = [r for r in _jsonl("claude-cagri.jsonl") if r.get("is") == "bas-konus" and r.get("toplantida") and bas - 60 <= (_ts(r) or 0) <= son + 120]
    o = _beta_olaylar(bas, son + 60)
    return {"satir_gecikme_sn": _ort([round(x, 2) for x in sg if -5 < x < 600]), "konus": _beta_konus(kon),
            "hitap": sum(1 for r in kon if r.get("kaynak") == "hitap"), "karsi_hitap": sum(1 for r in kon if r.get("kaynak") == "karsi"),
            "olay": o, "cokme": _beta_acilis_donem(bas + 30, son + 60)[0], "yeniden_planli": _beta_acilis_donem(bas + 30, son + 60)[1],
            "ses": _beta_yanki(beta_say("yanki", bas, son + 60), sum(1 for x in metin if x.get("kanal") == "ben"), {b: beta_say("yanki_tanima_" + b, bas, son + 60) for b in YANKI_TANIMA_BOLGE}),
            "kart_cevap_on_sn_ustu_yuzde": round(100 * sum(1 for x in gec if x > 10) / len(gec)) if gec else None,
            "sistem": _beta_sistem(bas, son + 60), "platform": (BETA["toplanti"].get(toplanti_kimlik(f)) or {}).get("platform")}

def _beta_profil():
    ks = kisilikler() if "kisilikler" in globals() else []
    bic = {k.get("bicim") for k in ks}; tarz = set()
    for k in ks:
        m = k.get("metin") or ""
        tarz.add("rahat" if ("Ton (rahat)" in m or "Tone (relaxed)" in m) else "olculu" if ("Ton (ölçülü)" in m or "Tone (measured)" in m) else "elle")
    tek = lambda s: (next(iter(s)) if len(s) == 1 else "karisik") if s else None
    return {"ses_motoru": str(AYAR.get("ses_motoru") or "mac"), "arayuz": "en" if AYAR.get("dil") == "en" else "tr", "tema": str(AYAR.get("tema") or "sistem"),
            "asistan_sayisi": len(ks), "hitap_bicimi": tek(bic), "tarz": tek(tarz), "kurulum_profil": "hafif" if AYAR.get("profil") == "hafif" else "tam", "whisper_motor": wh_motor() if "wh_motor" in globals() else str(AYAR.get("whisper_motor") or "mlx"),
            "toplantiya_ses": AYAR.get("toplantiya_ses") is True, "konusma": AYAR.get("konusma", True) is not False,
            "proje_karti": os.path.exists(os.path.join(AYAR["uygulama"], "proje-karti.json")), "takvim": (STATE.get("takvim") or {}).get("durum"),
            "animsatici": AYAR.get("animsatici") is True, "animsatici_sayi": anim_say() if "anim_say" in globals() else 0}  # S258: yalnız açık/kapalı ve eşlenen iş SAYISI; iş metni, liste adı gitmez
def _beta_cpp(bas, son):  # S188: whisper.cpp açılışları (canli/whisper-cpp-acilis.jsonl, whisper-hat wh_cpp_kaydet) — yalnız sonuç, hata sınıfı ve süre; yol, ileti gitmez
    rs = [r for r in _jsonl("whisper-cpp-acilis.jsonl") if bas <= (_ts(r) or 0) < son]
    ok = [r for r in rs if r.get("sonuc") == "basarili"]; sn = lambda r, k: float(r[k]) if isinstance(r.get(k), (int, float)) else None
    ilk = [sn(r, "acilis_sn") for r in ok if r.get("coreml_ilk") and sn(r, "acilis_sn") is not None]
    return {"acilis": len(rs), "basarili": len(ok), "yedek": len(rs) - len(ok),
            "cpp_hata": dict(collections.Counter(str(r.get("hata") or "diger") for r in rs if r.get("sonuc") != "basarili")),
            "acilis_sn": _ort([x for x in (sn(r, "sn") for r in ok) if x is not None]), "coreml_ilk_sn": max(ilk) if ilk else None,
            "calisan_motor": (STATE.get("whisper") or {}).get("motor") or None}
def _beta_maliyet(bas, son, toplanti_dk):
    cg = [r for r in _jsonl("claude-cagri.jsonl") if bas <= (_ts(r) or 0) < son]
    isler = {}
    for r in cg:
        ad = str(r.get("is") or "").replace("-", "_")
        ad = ad if ad in teshis.SAYIM["claude_is"] else "diger"
        x = isler.setdefault(ad, {"cagri": 0, "giris": 0, "cikti": 0, "onbellek_yaz": 0, "onbellek_oku": 0, "dolar": 0.0})
        x["cagri"] += 1; x["dolar"] += float(r.get("maliyet") or 0)
        for k, ks in (("giris", ("giris",)), ("cikti", ("cikti", "cikis")), ("onbellek_yaz", ("yazim", "onbellek_yaz")), ("onbellek_oku", ("onbellek_oku",))):
            x[k] += sum(int(r.get(a) or 0) for a in ks if isinstance(r.get(a), (int, float)))
    for x in isler.values(): x["dolar"] = round(x["dolar"], 3)
    tp = isler.get("toplanti") or {}; trs = [r for r in cg if r.get("is") == "toplanti"]; n_top = len(trs)
    toplanti_dk = sum(float(r.get("sure_dk") or 0) for r in trs) or toplanti_dk  # oturumun kendi süresi (maliyet kaydı); yoksa olay kaydından
    gm = [r for r in _jsonl("gemini-ses.jsonl") if bas <= (_ts(r, "t") or 0) < son]
    return {"claude": isler, "toplanti_basi_dolar": round(tp["dolar"] / n_top, 3) if n_top else None,
            "dakika_basi_dolar": round(tp["dolar"] / toplanti_dk, 4) if tp and toplanti_dk else None,
            "gemini": {"istek": len(gm), "karakter": sum(int(r.get("karakter") or 0) for r in gm), "ses_sn": round(sum(float(r.get("ses_sn") or 0) for r in gm)),
                       "ilk_ses_sn": _ort([r["ilk_ses"] for r in gm if isinstance(r.get("ilk_ses"), (int, float))])}}

def _hafta_sinir(ad):  # "2026-H43" → (pazartesi 00:00, sonraki pazartesi 00:00) yerel saat
    y, w = int(ad[:4]), int(ad[6:])
    bas = datetime.datetime.fromisocalendar(y, w, 1); return bas, bas + datetime.timedelta(days=7)
def beta_haftalik_paket(ad):
    b, s_ = _hafta_sinir(ad); bas, son = b.timestamp(), s_.timestamp()
    ku = _KUL.haftalik(BASE, 1, os.path.join(BASE, "kullanim-etiket.jsonl"), simdi=s_)
    hk = next((h for h in ku["haftalar"] if h["hafta"] == ad), None) or {}
    with BETA_K: tps = [v for v in BETA["toplanti"].values() if bas <= (v.get("son") or 0) < son]
    sure = [round((v["son"] - v["bas"]) / 60) for v in tps if v.get("son") and v.get("bas")]
    pl = collections.Counter(v.get("platform") or "bilinmeyen" for v in tps)
    soru = [r for r in _jsonl("sorular.jsonl") if bas <= (_ts(r) or 0) < son]
    kon = [r for r in _jsonl("claude-cagri.jsonl") if r.get("is") == "bas-konus" and bas <= (_ts(r) or 0) < son]
    o = _beta_olaylar(bas, son)
    return {"hafta": ad, "kullanim": {k: v for k, v in hk.items() if k != "hafta"}, "kart_turu": ku["kart_turu"],
            "toplantilar": {"sayi": len(tps), "sure_dk_toplam": sum(sure), "sure_dk": _ort(sure), "platformlar": dict(pl), "ceviri": sum(1 for v in tps if v.get("ceviri"))},
            "ozellik": {"ne_diyeyim": sum(1 for r in soru if r.get("tur") == "ozet"), "kanit": o["kanit"], "sessiz": o["sessiz"], "sesli_ceviri": o["sesli_ceviri"],
                        "canli_ceviri_toplanti": sum(1 for v in tps if v.get("ceviri")), "gizli": o["gizli"], "moderator": o["moderator"], "dur": o["dur"]},
            "kalite": {"konus": _beta_konus(kon), "hitap_yinelenen": o["hitap_yinelenen"], "zaman_asimi": o["zaman_asimi"], "acilis": beta_say("acilis", bas, son), "acilis_planli": beta_say("acilis_planli", bas, son),
                       "hata": o["hata"], "sorun": o["sorun"], "sistem": _beta_sistem(bas, son), "bilgi": _beta_bilgi(bas, son)},
            "maliyet": _beta_maliyet(bas, son, sum(sure)), "profil": _beta_profil(), "whisper_cpp": _beta_cpp(bas, son),
            "proje": teshis.proje_olcu(AYAR.get("proje"), AYAR["uygulama"]), "proje_vt": _beta_proje_vt(), "zeka": _beta_zeka(bas, son)}  # klasör türü + son taramanın sayıları (klasör değişebilir)
def _beta_haftalik():
    simdi = datetime.datetime.now()
    ad = _KUL.hafta_adi(simdi) if BETA_TEST else _KUL.hafta_adi(simdi - datetime.timedelta(days=7))  # biten hafta
    if ad in BETA["hafta"] or not teshis or not teshis.acik(AYAR): return
    if BETA_TEST and not os.path.exists(os.path.join(BASE, "beta-haftalik-simdi")): return  # test kendi işaretiyle tetikler
    if not BETA_TEST and (time.time() - _BASLANGIC < 600 or toplanti_var()): return  # açılıştan hemen sonra ve toplantıda değil
    p = beta_haftalik_paket(ad)
    r = teshis_gonder("haftalik", p, anahtar=("haftalik", ad))
    if r.get("ok") or r.get("durum") in ("kuyrukta", "gonderildi", "bekliyor"):
        with BETA_K: BETA["hafta"].append(ad)
        print(f"BETA: haftalık paket {ad} kuyrukta")
def _beta_dongu():
    time.sleep(2 if BETA_TEST else 60)
    while True:
        try:
            _beta_toplanti_izle()
            _beta_haftalik()
            _beta_yaz()
        except Exception as e: print(f"BETA: hata {e.__class__.__name__}")
        time.sleep(2 if BETA_TEST else 60)
if _KUL: threading.Thread(target=_beta_dongu, daemon=True).start()
else: print("BETA: kullanim.py yok — haftalık paket gönderilmez")
