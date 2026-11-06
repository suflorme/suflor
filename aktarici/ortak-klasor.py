# Suflor.me aktarıcı bölümü: Ortak klasör — ortak karar katmanı A3 (Drive pilotu; planlar/ortak-karar-mimarisi-20261105.md §4 P1). Ayrı modül değildir — relay.py bunu kendi
# ad alanında çalıştırır (bolum("ortak-klasor")): AYAR, BASE, threading, _yapi_mod, kimlik_ben/kimlik_coz (kimlik.py) relay.py'nindir. Mantık yapi.py'de (ortak_*), burada ince katman:
#   ayar ortak_klasor (yol; yoksa kapalı, hiçbir şey yazılmaz/okunmaz), ortak_gecmis (true: ayar açılmadan önceki kayıtlar da gider; varsayılan kapalı).
#   60 sn'de bir tur: bu Mac'in yeni karar/iş olayları <klasör>/olaylar/<e-posta>/<cihaz>/<YYYY-AA>.jsonl'e eklenir, başkalarınınki okunur.
#   GET  /ortak (anahtarlı, VERI_GET) → durum, sayılar, uygulanmayan değişiklikler, denetim (ortak klasörde gizli/deneme kaydı var mı)
#   POST /ortak {"islem": "esitle"} (anahtarlı) → hemen bir tur
# Ağ yok: yalnız yerel dosya sistemine yazılır (Drive masaüstü uygulaması eşitler). Kimlik şirket e-postası (kimlik_ben); yoksa ya da kişisel posta alan adıysa kapalı kalır
# (beta kurulumunda açılmaz). Gizli/deneme toplantının kaydı yazma anında yapi._paylasilmaz ile elenir. Beta paketine hiçbir alan girmez.
ORTAK_ARALIK_SN = 60
ORTAK_KISISEL = ("gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "msn.com", "yahoo.com", "icloud.com", "me.com", "mac.com", "yandex.com", "proton.me", "protonmail.com", "aol.com")
ORT = {"durum": "kapali", "son": None, "sonuc": None, "hata": None, "denetim": None}
_ORT_KILIT = threading.Lock()

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
def ortak_esitle(neden="dongu"):
    kl = ortak_klasor()
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
def _ortak_dongu():
    time.sleep(5)
    while True:
        try: ortak_esitle()
        except Exception as e: print(f"ORTAK: döngü ({e.__class__.__name__})")
        time.sleep(ORTAK_ARALIK_SN)
def ortak_view():  # GET /ortak
    y = _yapi_mod(); kl = ortak_klasor(); v = {"ok": True, "acik": bool(kl), "klasor": kl or "", "kimlik": ortak_kimlik() or "", "durum": ORT["durum"] if kl else "kapali",
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
