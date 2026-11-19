# Suflor.me aktarıcı bölümü: DIŞ ÇIKIŞ kapısı (19 Kasım 2026; mimari denetim 4 R1/R2/R5, bulgular B2–B4). Ayrı modül değildir — relay.py bunu kendi ad alanında
# çalıştırır (bolum("cikis"), bolum("web-kapi")'den hemen sonra): AYAR, BASE, STATE, gizli_acik, kapi_gizli, aktif_dosya, katilimci_gorulen, katilimci_coz, dis_katilimcilar,
# VT_BELLEK, KIMLIK_VT, dosya_yaz_esz, web_suzgec_kur / web_metin_suphe / web_getir_suphe (web-kapi.py) … çağrı anında aranır. import etme. Python 3.9 uyumlu.
# Amaç: Claude DIŞINDAKİ her dış çıkış (Gemini, web, Basecamp, Anımsatıcılar, Firestore, Tazı, beta teşhisi, GitHub raporu …) ağa çıkmadan HEMEN ÖNCE tek yerden sorulur:
#   cikis_izin(hedef, tur, veri=None) → (ok, neden). Claude çağrıları ayrı kapıda (kapi.py kapi_model; gizli kipte hepsi kapalı).
# Gizli kip VARSAYILAN KAPALI (fail-closed): kapi_gizli / gizli_acik yoksa ya da hata verirse gizli sayılır. Bilinmeyen hedef → ret.
#
# Hedef tablosu — gizli kipte (S91 "tamamen kör ve sağır") ne olur:
#   hedef          | kural            | giden                                         | gizli kipte
#   gemini_tts     | S83/S87          | okunacak metin → Gemini TTS                   | RET (v0.89.0: gizli toplantıda Gemini kapalı)
#   gemini_api     | S186             | toplantı ses arşivi → Gemini hakem (geliştirici)| RET (S186: gizli satırlı döküm de gitmez)
#   saglayici      | S146             | OpenAI uyumlu sağlayıcı (bağlantı denemesi)   | RET (gizli kipte hiçbir yapay zekâ yok)
#   web_arama      | S208/S257        | arama sorgusu (yalnız ad + konu)              | RET (S208/S257: gizli kipte web yok) + metin kapısı (aşağıda)
#   web_getir      | S208/S257        | adres (yol/sorgu dahil)                       | RET + adres ve yol metni kapısı
#   basecamp       | S282 (S227)      | okuma isteği (belirteç yenileme dahil)        | RET (S227: gizli toplantı gitmez; okuma da beklesin)
#   animsatici     | S258             | iş metni, tarih → Mac Anımsatıcılar (iCloud)  | RET (S258: gizli toplantı işi gitmez; tur bekler)
#   firestore      | S222 + A3/A7     | karar/iş olayları (ortak katman)              | RET (eşitleme imleçle sonra kaldığı yerden sürer)
#   drive, kaggle  | S153/S186/S222   | geliştirme verisi                              | RET
#   bilgi_kaynagi  | S171             | okuma aracına sorgu parametresi               | RET
#   tazi           | S321             | Tazı hizmeti (ağa yalnız ad + alan adı)       | RET (gizli toplantı içeriği Tazı'ya gitmez)
#   toplanti_ses   | S91 (v0.89.0)    | yapay ses → toplantıya (BlackHole)            | RET
#   github_rapor   | S141 içerik sınırı (B4) | teshis.sade'den geçmiş teknik rapor    | RET
#   beta           | S141             | teknik sayaçlar (teshis.temizle)              | YALNIZ teknik sayaç türleri geçer: CIKIS_BETA_TEKNIK (hata, kurulum, haftalık,
#                  |                  |                                               | toplantı sonu sayıları); kullanıcı metni taşıyan "sorun"/"geri_bildirim" RET
# Web metin kapısı (gizli kip kapalıyken de): web-kapi.py web_metin_suphe / web_getir_suphe — uzunluk, e-posta, 5+ haneli sayı, bilinen iç kişi adı (kayıt veritabanı
#   VT_BELLEK, kimlik eşlemesi KIMLIK_VT, toplantıda konuşanlar, takvim katılımcıları; S208 gereği dış katılımcının adı serbest), güncel dökümden 6 sözcüklük alıntı.
#   Süzgeç (yalnız özet, metin yok) canli/cikis-suzgec.json'a 0600 yazılır: Konuş kancası (konus-web-kanca.py, ayrı süreç) oradan okur.
# Sayaçlar yalnız sayı: cikis_view() (/status için). Engel günlüğe hedef|neden başına ilk kez ve her 50'de bir yazılır (metin yok).
import hashlib
CIKIS_TABLO = {
    "gemini_tts": "S83/S87", "gemini_api": "S186", "saglayici": "S146", "web_arama": "S208/S257", "web_getir": "S208/S257",
    "basecamp": "S282/S227", "animsatici": "S258", "firestore": "S222/A7", "drive": "S153/S222", "kaggle": "S153/S186",
    "bilgi_kaynagi": "S171", "tazi": "S321", "toplanti_ses": "S91", "github_rapor": "S141", "beta": "S141",
}
CIKIS_BETA_TEKNIK = {"hata", "kurulum", "haftalik", "toplanti_sonu"}  # gizli kipte de giden beta paket türleri (teshis.py SABIT["tur"]; yalnız sayı/seçenek)
CIKIS = {"gecti": {}, "engel": {}}
CIKIS_KILIT = threading.Lock()
CIKIS_NEDEN_EN = {"gizli kip": "private mode", "bilinmeyen hedef": "unknown destination"}
_CIKIS_SUZ = {"t": 0.0, "d": None, "imza": None}
CIKIS_SUZGEC_SN = 15     # süzgeç en çok bu kadar bayat
CIKIS_DONGU_SN = 20      # kanca dosyasının tazelenme aralığı
CIKIS_DOKUM_BAYT = 24000  # güncel dökümün okunan sonu

def cikis_gizli():  # → True: gizli kip açık YA DA belirlenemiyor (fail-closed)
    for ad in ("kapi_gizli", "gizli_acik"):
        f = globals().get(ad)
        if callable(f):
            try: return bool(f())
            except Exception: return True
    return True

def _cikis_say(tur, hedef, neden=""):
    k = hedef + ("|" + neden if neden else "")
    with CIKIS_KILIT:
        d = CIKIS[tur]; d[k] = d.get(k, 0) + 1; n = d[k]
    if tur == "engel" and (n == 1 or n % 50 == 0): print(f"ÇIKIŞ: {hedef} engellendi — {neden} ({n})")

def cikis_izin(hedef, tur, veri=None):  # → (ok, neden). tur: veri sınıfı / alt iş (beta'da paket türü); veri: web hedeflerinde sorgu ya da adres
    hedef = str(hedef or ""); tur = str(tur or "")
    if hedef not in CIKIS_TABLO: _cikis_say("engel", hedef or "?", "bilinmeyen hedef"); return False, "bilinmeyen hedef"
    if cikis_gizli() and not (hedef == "beta" and tur in CIKIS_BETA_TEKNIK):
        _cikis_say("engel", hedef, "gizli kip"); return False, "gizli kip"
    if hedef in ("web_arama", "web_getir"):
        try:
            suz = cikis_suzgec()
            r = (web_getir_suphe(veri, suz) if hedef == "web_getir" else web_metin_suphe(veri, suz))
        except Exception as e: r = ("Web denetimi yapılamadı.", "The web check could not run.")
        if r:
            CIKIS_NEDEN_EN[r[0]] = r[1]; _cikis_say("engel", hedef, "metin"); return False, r[0]
    _cikis_say("gecti", hedef); return True, ""

def cikis_neden(neden):  # cikis_izin nedeni → arayüz dilinde metin
    n = str(neden or "")
    f = globals().get("_t")
    return f(n, CIKIS_NEDEN_EN.get(n, n)) if callable(f) else n

# --- Web süzgeci: bilinen adlar ve güncel dökümün özeti (metin tutulmaz) ---------------------------------------------------------------------------------
def _cikis_cagir(ad, *a):
    f = globals().get(ad)
    if not callable(f): return None
    try: return f(*a)
    except Exception: return None
def _cikis_dokum():  # → (dosya yolu ya da None): süren toplantı, yoksa son 12 saatte yazılmış son toplantı (Konuş'ta son toplantının dökümü de alıntılanmasın)
    d = _cikis_cagir("aktif_dosya") or (globals().get("STATE") or {}).get("file")
    if not d: return None
    yol = d if os.path.isabs(str(d)) else os.path.join(BASE, str(d))
    try:
        if time.time() - os.path.getmtime(yol) > 12 * 3600 and not _cikis_cagir("aktif_dosya"): return None
    except OSError: return None
    return yol
def _cikis_kaynak():  # → (adlar, metinler, izinli)
    adlar, izinli, metin = [], [], []
    vt = globals().get("VT_BELLEK") or {}
    adlar += [a for a in (vt.get("adlar") or []) if isinstance(a, str)]
    adlar += [a for a in (globals().get("KIMLIK_VT") or {}) if isinstance(a, str)]
    adlar += [a for a in (_cikis_cagir("katilimci_gorulen") or []) if isinstance(a, str)]
    fp = os.path.join(BASE, "takvim-secilen.json")  # seçili toplantının davetlileri: dosya değişince yeniden çözülür (kişi kaydı araması pahalı)
    try: mt = os.path.getmtime(fp)
    except OSError: mt = None
    if _CIKIS_SUZ.get("olay_mt") != mt:
        oa, oi = [], []
        try: olay = (json.load(open(fp, encoding="utf-8")) or {}).get("olay") or {}
        except (OSError, ValueError, AttributeError): olay = {}
        if olay:
            r = _cikis_cagir("katilimci_coz", olay, []) or {}
            oa = [str(k.get("ad")) for k in list(r.get("kisiler") or []) + list(r.get("eslesmeyen") or []) if isinstance(k, dict) and k.get("ad")]
            dk = _cikis_cagir("dis_katilimcilar", olay)
            if dk: oi = [str(k.get("ad")) for k in (dk[0] or []) if isinstance(k, dict) and k.get("ad")]  # S208: dış katılımcıyı araştırmak serbest
        _CIKIS_SUZ.update(olay_mt=mt, olay_ad=oa, olay_izinli=oi)
    adlar += _CIKIS_SUZ.get("olay_ad") or []; izinli += _CIKIS_SUZ.get("olay_izinli") or []
    yol = _cikis_dokum()
    if yol:
        try:
            with open(yol, "rb") as f:
                boy = os.fstat(f.fileno()).st_size; f.seek(max(0, boy - CIKIS_DOKUM_BAYT)); metin.append(f.read().decode("utf-8", "replace"))
        except OSError: pass
    return adlar, metin, izinli
def cikis_suzgec(zorla=False):  # → süzgeç sözlüğü (önbellekli, CIKIS_SUZGEC_SN)
    if not zorla and _CIKIS_SUZ["d"] is not None and time.time() - _CIKIS_SUZ["t"] < CIKIS_SUZGEC_SN: return _CIKIS_SUZ["d"]
    a, m, i = _cikis_kaynak()
    d = web_suzgec_kur(a, m, i); _CIKIS_SUZ.update(t=time.time(), d=d)
    return d
def cikis_suzgec_yaz():  # Konuş kancası için canli/cikis-suzgec.json (0600); gizli kipte yalnız {"gizli": true}
    d = {"gizli": True} if cikis_gizli() else dict(cikis_suzgec(zorla=True))
    imza = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
    fp = os.path.join(BASE, "cikis-suzgec.json")
    if imza == _CIKIS_SUZ["imza"] and os.path.exists(fp): return False
    d["t"] = round(time.time())
    try:
        if callable(globals().get("dosya_yaz_esz")): dosya_yaz_esz(fp, d, 0o600)
        else:
            tmp = fp + f".{os.getpid()}.tmp"
            with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f: json.dump(d, f)
            os.replace(tmp, fp)
        _CIKIS_SUZ["imza"] = imza; return True
    except OSError as e: print(f"ÇIKIŞ: süzgeç dosyası yazılamadı ({e.__class__.__name__})"); return False
def _cikis_dongu():
    time.sleep(3)  # öbür bölümler (web-kapi, kimlik, toplanti) yüklensin
    while True:
        try: cikis_suzgec_yaz()
        except Exception as e: print(f"ÇIKIŞ: süzgeç döngüsü ({e.__class__.__name__})")
        time.sleep(CIKIS_DONGU_SN)
def cikis_view():  # /status için yalnız sayı
    with CIKIS_KILIT: return {"gecti": dict(CIKIS["gecti"]), "engel": dict(CIKIS["engel"]), "gizli": cikis_gizli()}

# teshis (beta kanalı) ayrı modül: gönderimden önce bu kapıyı sorsun (teshis.CIKIS_IZIN; yoksa teshis kendi fail-closed dosya denetimini yapar)
try:
    if globals().get("teshis") is not None: teshis.CIKIS_IZIN = cikis_izin
except Exception: pass
if "BASE" in globals() and not os.environ.get("SUFLOR_CIKIS_DONGU_YOK"): threading.Thread(target=_cikis_dongu, daemon=True).start()
