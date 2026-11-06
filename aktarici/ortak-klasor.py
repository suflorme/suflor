# Suflor.me aktarıcı bölümü: Ortak klasör — ortak karar katmanı A3 (Drive pilotu; planlar/ortak-karar-mimarisi-20261105.md §4 P1). Ayrı modül değildir — relay.py bunu kendi
# ad alanında çalıştırır (bolum("ortak-klasor")): AYAR, BASE, threading, _yapi_mod, kimlik_ben/kimlik_coz (kimlik.py) relay.py'nindir. Mantık yapi.py'de (ortak_*), burada ince katman:
#   ayar ortak_klasor (yol; yoksa kapalı, hiçbir şey yazılmaz/okunmaz), ortak_gecmis (true: ayar açılmadan önceki kayıtlar da gider; varsayılan kapalı).
#   60 sn'de bir tur: bu Mac'in yeni karar/iş olayları <klasör>/olaylar/<e-posta>/<cihaz>/<YYYY-AA>.jsonl'e eklenir, başkalarınınki okunur.
#   GET  /ortak (anahtarlı, VERI_GET) → durum, sayılar, uygulanmayan değişiklikler, denetim (ortak klasörde gizli/deneme kaydı var mı)
#   POST /ortak {"islem": "esitle"} (anahtarlı) → hemen bir tur
# A7 (6 Kasım): ayar ortak_tasima = "firestore" ise aynı olaylar Drive yerine Cloud Firestore'dan paylaşılır (ortak_bulut.py; ayar firestore_proje/_istemci_id/_alanlar, Anahtar Zinciri girişi `ortak_bulut.py
# kur|katil`). Döngü: pano son 60 sn'de yoklandıysa ya da toplantı sürüyorsa 5 sn, değilse 30 sn (ayar ortak_firestore_aralik_sn her ikisini ezer). Ağ yalnız bu yolda ve yalnız firestore_alanlar içindeki şirket
# e-postasıyla; günlüğe yalnız sayı ve hata sınıfı. GET /ortak ek alanları: tasima, firestore {proje, giris, eposta, gecikme_ortanca, gecikme_p90, son_hata}.
# Drive yolunda ağ yok: yalnız yerel dosya sistemine yazılır (Drive masaüstü uygulaması eşitler). Kimlik şirket e-postası (kimlik_ben); yoksa ya da kişisel posta alan adıysa kapalı kalır
# (beta kurulumunda açılmaz). Gizli/deneme toplantının kaydı yazma anında yapi._paylasilmaz ile elenir. Beta paketine hiçbir alan girmez.
ORTAK_ARALIK_SN = 60
ORTAK_KISISEL = ("gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "msn.com", "yahoo.com", "icloud.com", "me.com", "mac.com", "yandex.com", "proton.me", "protonmail.com", "aol.com")
ORT = {"durum": "kapali", "son": None, "sonuc": None, "hata": None, "denetim": None}
FS_HIZLI_SN, FS_YAVAS_SN, FS_PANO_SN = 5, 30, 60
_ORT_KILIT = threading.Lock()

def ortak_tasima():  # "drive" (varsayılan) | "firestore"; ayar dosyadan taze okunur (ortak_bulut.py kur/katil aktarıcıyı yeniden başlatmadan etkili olsun)
    try: t = str(ayar_oku().get("ortak_tasima") or "drive")
    except Exception: t = "drive"
    return "firestore" if t == "firestore" else "drive"
def _bulut_mod():  # ortak_bulut.py aktarıcıyla aynı klasörde kurulur; yoksa Firestore yolu "hata" der
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ortak_bulut; return ortak_bulut
    except ImportError: return None
def ortak_klasor():
    y = str(AYAR.get("ortak_klasor") or "").strip()
    return os.path.expanduser(y) if y else None
def ortak_kimlik():  # → şirket e-postası ya da None (kişisel posta alan adı sayılmaz)
    try: ep = kimlik_ben()[1] if "kimlik_ben" in globals() else None
    except Exception: ep = None
    return ep if ep and ep.split("@")[-1] not in ORTAK_KISISEL else None
def _ort_kimlik_f(ad):  # rolde e-postası olmayan ad → yalnız emin eşleme (Kişiler'e gidilmez, kayıt yazılmaz)
    if "kimlik_coz" not in globals(): return None
    r = kimlik_coz(ad, kisiler=False, yaz=False)
    return r.get("eposta") if r.get("eposta") and (r.get("guven") or 0) >= 0.9 else None
def _ort_firestore(neden):
    ep = ortak_kimlik(); ORT["tasima"] = "firestore"
    if not ep: ORT.update(durum="kimlik_yok", hata=None); return ORT  # şirket e-postası yoksa hiçbir şey gitmez (beta kurulumunda açılmaz)
    bm = _bulut_mod(); y = _yapi_mod()
    if not bm or not y: ORT.update(durum="hata", hata="ortak_bulut.py yok"); return ORT
    a = ayar_oku(); h = bm.hazir(a)
    if h != "hazir": ORT.update(durum={"ayar_eksik": "ayar_eksik", "giris_yok": "giris_yok"}.get(h, "kapali"), hata=None); return ORT
    try:
        if not bm.alan_izinli(ep, a.get("firestore_alanlar") or []): ORT.update(durum="alan_disi", hata=None); return ORT  # kişisel posta / izinli alan dışı: hiç bağlanma
    except Exception: ORT.update(durum="alan_disi", hata=None); return ORT
    with _ORT_KILIT:
        try:
            r = bm.esitle(BASE, a, ep, str(a.get("ad") or ""), a.get("ortak_gecmis") is True, _ort_kimlik_f, y)
            ORT.update(durum="ok", son=r["zaman"], sonuc=r, hata=None, denetim=None, gecikme=r.get("gecikme"), proje=str(a.get("firestore_proje") or ""), eposta=ep)
            d, i = r["disari"], r["iceri"]
            if d["yazilan"] or i["alinan"] or i["bozuk"] or d.get("genisleyen"):  # günlüğe yalnız sayı (metin/ad/e-posta yazılmaz)
                print(f"ORTAK (firestore): {neden} · yazılan {d['yazilan']} · alınan {i['alinan']} · çift {i['cift']} · bozuk {i['bozuk']} · genişleyen {d.get('genisleyen', 0)} · atlanan {sum(d['atlanan'].values())}")
        except bm.FsHata as e:
            ORT.update(durum={"ag": "ag_yok", "giris_yok": "giris_yok", "yetki": "giris_yok", "alan": "alan_disi", "eposta": "kimlik_uyumsuz"}.get(e.sinif, "hata"), hata=e.sinif, proje=str(a.get("firestore_proje") or ""))
            print(f"ORTAK (firestore): tur yapılamadı ({e.sinif})")
        except Exception as e:
            ORT.update(durum="hata", hata=e.__class__.__name__); print(f"ORTAK (firestore): tur yapılamadı ({e.__class__.__name__})")
    return ORT
def _ort_deneme():  # deneme aktarıcısı (başka canli klasörü ya da port; teshis.DENEME) gerçek ayarı okusa da hiçbir taşımayla paylaşmaz, ağa çıkmaz
    try:
        if "teshis" in globals() and teshis and teshis.DENEME: return True
        return os.path.realpath(BASE) != os.path.realpath(os.path.join(os.path.expanduser(AYAR["uygulama"]), "canli")) or int(A.port) != int(AYAR["port"])  # relay.py'deki DENEME koşulu (teshis yoksa da)
    except Exception: return True  # emin olunamıyorsa paylaşma
def ortak_esitle(neden="dongu"):
    if _ort_deneme(): ORT.update(durum="deneme", hata=None); return ORT
    if ortak_tasima() == "firestore": return _ort_firestore(neden)
    ORT["tasima"] = "drive"; kl = ortak_klasor()
    if not kl: ORT.update(durum="kapali", hata=None); return ORT
    ep = ortak_kimlik()
    if not ep: ORT.update(durum="kimlik_yok", hata=None); return ORT  # şirket e-postası yoksa hiçbir şey yazılmaz
    if not os.path.isdir(kl): ORT.update(durum="klasor_yok", hata=None); return ORT
    y = _yapi_mod()
    if not y: ORT.update(durum="hata", hata="yapi.py yok"); return ORT
    with _ORT_KILIT:
        try:
            r = y.ortak_esitle(BASE, kl, ep, str(AYAR.get("ad") or ""), AYAR.get("ortak_gecmis") is True, _ort_kimlik_f)
            ORT.update(durum="ok", son=r["zaman"], sonuc=r, hata=None, denetim=len(y.ortak_denetim(BASE, kl)))
            d, i = r["disari"], r["iceri"]
            if d["yazilan"] or i["alinan"] or i["bozuk"] or ORT["denetim"]:  # günlüğe yalnız sayı (metin/ad yazılmaz)
                print(f"ORTAK: {neden} · yazılan {d['yazilan']} · alınan {i['alinan']} · çift {i['cift']} · bozuk {i['bozuk']} · atlanan {sum(d['atlanan'].values())}" + (f" · DENETİM {ORT['denetim']}" if ORT["denetim"] else ""))
        except Exception as e:
            ORT.update(durum="hata", hata=e.__class__.__name__); print(f"ORTAK: tur yapılamadı ({e.__class__.__name__})")
    return ORT
def _ort_aralik():  # Drive'da 60 sn aynen; Firestore'da pano son 60 sn'de yoklandıysa ya da toplantı sürüyorsa 5 sn, değilse 30 sn
    if ortak_tasima() != "firestore": return ORTAK_ARALIK_SN
    try: sabit = float(ayar_oku().get("ortak_firestore_aralik_sn") or 0)
    except (TypeError, ValueError): sabit = 0
    if sabit > 0: return sabit
    try: topl = bool(toplanti_var()) if "toplanti_var" in globals() else False
    except Exception: topl = False
    return FS_HIZLI_SN if topl or time.time() - (STATE.get("_pano_t") or 0) < FS_PANO_SN else FS_YAVAS_SN
def _ortak_dongu():
    time.sleep(5)
    while True:
        try: ortak_esitle()
        except Exception as e: print(f"ORTAK: döngü ({e.__class__.__name__})")
        time.sleep(_ort_aralik())
def _ort_firestore_view():  # GET /ortak, ortak_tasima = firestore (metin/ad yok; e-posta kullanıcının kendisi)
    y = _yapi_mod(); bm = _bulut_mod(); a = ayar_oku(); proje = str(a.get("firestore_proje") or ""); ort, p90 = (ORT.get("gecikme") or (None, None))
    h = bm.hazir(a) if bm else "ayar_eksik"; durum = ORT["durum"] if ORT.get("tasima") == "firestore" else {"hazir": "bekliyor", "giris_yok": "giris_yok", "ayar_eksik": "ayar_eksik"}.get(h, "kapali")
    v = {"ok": True, "tasima": "firestore", "acik": h != "kapali", "klasor": "", "kimlik": ortak_kimlik() or "", "durum": durum, "son": ORT["son"], "hata": ORT["hata"], "denetim": None,
         "firestore": {"proje": proje, "giris": h == "hazir", "eposta": ORT.get("eposta") or "", "gecikme_ortanca": ort, "gecikme_p90": p90, "son_hata": ORT["hata"]}}
    if y and bm and h != "kapali":
        try:
            d = y._ortak_durum(BASE).get("firestore", {}).get(proje, {})
            v.update(yazilan=int(d.get("yazilan") or 0), alinan=int(d.get("alinan") or 0), kisiler=list(d.get("kisiler") or []), reddedilen=y.ortak_reddedilen(BASE))
            if ORT["sonuc"]: v["son_tur"] = {"atlanan": ORT["sonuc"]["disari"]["atlanan"], "cift": ORT["sonuc"]["iceri"]["cift"], "bozuk": ORT["sonuc"]["iceri"]["bozuk"], "yarim": 0}
        except Exception as e: v["hata"] = e.__class__.__name__
    return v
def ortak_view():  # GET /ortak
    if _ort_deneme(): return {"ok": True, "acik": False, "tasima": ortak_tasima(), "durum": "deneme", "klasor": "", "kimlik": "", "son": None, "hata": None, "denetim": None}
    if ortak_tasima() == "firestore": return _ort_firestore_view()
    y = _yapi_mod(); kl = ortak_klasor(); v = {"ok": True, "tasima": "drive", "acik": bool(kl), "klasor": kl or "", "kimlik": ortak_kimlik() or "", "durum": ORT["durum"] if kl else "kapali",
                                               "son": ORT["son"], "hata": ORT["hata"], "denetim": ORT["denetim"]}
    if kl and y:
        try:
            d = y._ortak_durum(BASE).get("klasorler", {}).get(os.path.realpath(kl), {})
            v.update(yazilan=int(d.get("yazilan") or 0), alinan=int(d.get("alinan") or 0), kisiler=list(d.get("kisiler") or []), reddedilen=y.ortak_reddedilen(BASE))
            if ORT["sonuc"]: v["son_tur"] = {"atlanan": ORT["sonuc"]["disari"]["atlanan"], "cift": ORT["sonuc"]["iceri"]["cift"], "bozuk": ORT["sonuc"]["iceri"]["bozuk"], "yarim": ORT["sonuc"]["iceri"]["yarim"]}
        except Exception as e: v["hata"] = e.__class__.__name__
    return v
def ortak_islem(p):  # POST /ortak
    p = p if isinstance(p, dict) else {}
    if p.get("islem") != "esitle": return {"ok": False, "err": "islem: esitle"}
    ortak_esitle("elle"); return ortak_view()
threading.Thread(target=_ortak_dongu, daemon=True).start()
