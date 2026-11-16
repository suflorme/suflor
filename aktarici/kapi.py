# Suflor.me aktarıcı bölümü: Claude kapısı (K1, 16 Kasım 2026; tasarım ../planlar/claude-kapisi-tasarim-20261116.md §3, §5 K1, §6). Ayrı modül değildir — relay.py bunu kendi ad
# alanında çalıştırır (bolum("kapi"), eylem-menu'den önce): AYAR, BASE, LOCK, write, gizli_acik, toplanti_var, aktif_dosya, sessiz_acik, calisma_saatleri, SOHBET, _KS … relay.py'nin ve öbür
# bölümlerin (çağrı anında aranır; yoksa o kural atlanır). import etme. Python 3.9 uyumlu.
# Amaç: Claude'a giden tek çağrılar (K1: değerlendiriciler + eylem_model'i kullanan işler; K2 v0.244.0: giriş yoklaması, sürüm denetimi, telaffuz, kesişim, brifing, prova) tek kapıdan geçer; izin, tekrar önleme, eşzamanlılık ve kayıt tek yerde.
#   kapi_iste(is_turu, cagri, *, karma=None, coz=None) → {"sonuc": tamam|okunamadi|hata|engel, "neden", "ham", "hata", "cozum", "maliyet", "sure_ms", "olculdu"}
#     cagri: argümansız işlev → (ham, hata) (eylem-menu.py _eylem_cagri). coz: isteğe bağlı ham → çözülmüş cevap (boşsa "okunamadi"). karma: girdi karması (aday kimlikleri).
#   Sıra: 1) izin (kapi_engel; ÇAĞRIDAN ÖNCE) 2) tekrar önleme (iş + karma) 3) arka plan işi ön plan turu bitene dek bekler, ortak sıraya (KAPI_SEM, 2) girer; ön plan sırayı atlar
#         4) çağrı (thread-local KAPI_YEREL: içteki eylem_model kapıya yeniden girmez; claude_json satırı buraya bırakır) 5) tek satır kayıt claude-cagri.jsonl.
#   İzin tablosu KAPI_TABLO (iş türü → kurallar). plan "arka" (kendiliğinden) / "on" (kullanıcı istedi). Arka plan: gizli kip, toplantı sürüyor, (sessiz: True ise) sessiz mod,
#     (saat "mesai") mesai dışı (ayar calisma_saatleri) ve gece (soz_gece_bas/bit, 22–07) ile ortak günlük tavan (ayar arka_gunluk_usd; yoksa degerlendir_gunluk_usd, o da yoksa 3 $).
#     Tek saat istisnası gece düşünmesi (dusunme ve onun turunda koşan mutabakat; karar 16 Kasım): saat kuralı yok, tavana girer. Ön plan (eylem, talimat, e-posta taslağı) tavansız, saatsiz.
#     saglayici "claude": metin yalnız claude-code uyarlayıcısına (S141/S222 e-posta); başka sağlayıcı seçiliyse claude-code ile çağrılır, o da yoksa engel.
#   Tekrar önleme: okunamayan/hatalı cevapta aynı karma 30 dk → 2 sa → 8 sa sorulmaz (engel "tekrar"); başarılıda tablo tekrar_sn (değerlendiriciler 30 dk) Claude çağrılmaz,
#     son başarılı cevap döner (sonuc "onbellek", maliyet 0; v0.243.1).
#   HTTP istek iş parçacığında (relay ThreadingHTTPServer) arka plan işi beklemez: Konuş turu sürüyorsa ya da sıra doluysa hemen engel (v0.243.1). Bellekte (yeniden başlatmada sıfırlanır).
#   Kayıt: claude-cagri.jsonl satırı claude_json biçiminde + sonuc, neden, plan, bekleme_ms (eski alanlar korunur). Engeller satır YAZMAZ: sayaç (/status kapi) + canli/kapi.jsonl'e
#     saatte en çok bir özet satırı (iş|neden → sayı; metin yok).
# Ayarlar (yalnız ayar.json): arka_gunluk_usd, kapi_es (2), calisma_saatleri, soz_gece / soz_gece_bas / soz_gece_bit (söz kapısıyla ortak).
import hashlib

KAPI_YEREL = threading.local()
KAPI_SAAT = globals().get("KAPI_SAAT") or time.time  # testlerde sahte saat (önceden tanımlıysa korunur)
KAPI_KILIT = threading.RLock()
KAPI_TEKRAR_HATA_SN = (1800, 7200, 28800)
KAPI_BEKLE_SN, KAPI_SIRA_SN, KAPI_OZET_SN = 60, 180, 3600
KAPI_ARKA_EK = ("giris", "kesisim-coz")  # tavanla durdurulmayan (giriş yoklaması) ya da eski adlı (K2 öncesi kesişim) arka plan satırları: harcamaları yine ortak toplama sayılır
_KAPI_ARKA = {"plan": "arka", "gizli": True, "toplanti": True, "sessiz": False, "saat": "mesai", "tavan": True, "saglayici": None, "tekrar_sn": 1800}
_KAPI_ON = {"plan": "on", "gizli": False, "toplanti": False, "sessiz": False, "saat": None, "tavan": False, "saglayici": None, "tekrar_sn": 0}
KAPI_TABLO = {
    "degerlendir:gun_ici": dict(_KAPI_ARKA, sessiz=True),
    "degerlendir:toplanti_sonrasi": dict(_KAPI_ARKA, sessiz=True),
    "degerlendir:belge_oneri": dict(_KAPI_ARKA),
    "degerlendir:is_kopya": dict(_KAPI_ARKA, bekle_sn=10),  # v0.243.2: IK["kilit"] tutulurken çağrılır; /is-kopya uçları uzun beklemesin
    "degerlendir:eposta": dict(_KAPI_ARKA, saglayici="claude", bekle_sn=10),  # v0.243.2: ET["kilit"] tutulurken çağrılır; e-posta uçları uzun beklemesin
    "degerlendir:mutabakat": dict(_KAPI_ARKA, saat=None, tekrar_sn=0),  # gece düşünme turunun parçası (dusunme.py dus_tur çağırır); günde bir kendi denetimiyle
    "dusunme": dict(_KAPI_ARKA, saat=None, tekrar_sn=0),  # tek saat istisnası (03–06 penceresi kendi bölümünde)
    "eylem": dict(_KAPI_ON),
    "talimat": dict(_KAPI_ON),
    "eposta_taslak": dict(_KAPI_ON, saglayici="claude"),
    # v0.244.0 (Claude kapısı K2): kalan arka plan işleri ve Brifing.app'li ön plan işleri
    "giris": dict(_KAPI_ARKA, gizli=False, tavan=False, tekrar_sn=0),  # seyrek giriş yoklaması (claude-giris.py): içerik yok; toplantıda, gece ve mesai dışında yok (karar 16 Kasım)
    "telaffuz:sozluk": dict(_KAPI_ARKA, tekrar_sn=0),  # sözlük değişince toplu okunuş tamamlama
    "telaffuz": dict(_KAPI_ARKA, toplanti=False, saat=None, tekrar_sn=0),  # okunan metindeki bilinmeyen sözcükler: konuşmayı besler (toplantıda ve akşam Konuş'ta da); gizli kipte yok
    "kesisim": dict(_KAPI_ARKA, tekrar_sn=0),  # günlük kesişim çözücü (relay.py kesisim_tur → kesisim-coz.py model_cagir); 07:45 yerine fiilen mesai başında
    "brifing": dict(_KAPI_ON),
    "prova": dict(_KAPI_ON),
    # v0.246.0 (K4): doğrudan açanlar ve kalıcı süreçlerin AÇILIŞI. Araştırma tek çağrı (kapi_iste; gizli kipte yok, S208 toplantı sınırı kendi bölümünde).
    # Kalıcı süreçler (Konuş, çeviri, toplantı oturumu) yalnız açılışta kapi_ac'tan geçer: izin + sayaç; tur içi akış, sıra ve satır kaydı kendi bölümlerinde (çift sayım yok).
    "arastirma": dict(_KAPI_ON, gizli=True),
    "konus-ac": dict(_KAPI_ON),  # gizli kipte de açılır (Konuş'un kendi gizli kuralları web/bilgi parçalarında)
    "ceviri-ac": dict(_KAPI_ON),
    "toplanti-ac": dict(_KAPI_ON),  # toplantı oturumu yalnız toplantıda çalışır: toplantı kuralı yok; yeniden açılış (bekçi) da buradan
}
# Kapı dışında kalan (bilerek): kurulum sihirbazı (kurulum.py giriş denemesi ve profil; hazirlik.py → proje-karti.py proje kartı — ayrı süreç, kullanıcı başlatır, kendi satırı
# "proje-karti"), kesisim-coz.py'nin tek başına (komut satırı) kipi, toplantı oturumunun Terminal'e alınması (claude --resume; kullanıcı yürütür).
KAPI = {"engel": {}, "engel_yazilan": {}, "ozet_t": 0.0, "son_neden": {}, "tekrar": {}, "usd": {"gun": "", "usd": 0.0}, "on": 0, "aktif": 0, "n": 0,
        "gun": {"tarih": "", "cagri": 0, "tamam": 0, "okunamadi": 0, "hata": 0, "engel": 0}}
try: KAPI_ES = max(1, min(8, int(AYAR.get("kapi_es") or 2)))
except (TypeError, ValueError): KAPI_ES = 2
KAPI_SEM = threading.BoundedSemaphore(KAPI_ES)  # tek çağrılar için ortak sıra (arka plan bekler; ön plan yer yoksa atlar)

def kapi_kural(is_turu):  # → kural sözlüğü; bilinmeyen değerlendirici türü arka plan, öbürleri ön plan (davranış korunur)
    r = KAPI_TABLO.get(str(is_turu))
    if r: return r
    return _KAPI_ARKA if str(is_turu).startswith("degerlendir") else _KAPI_ON
def kapi_is_turu(is_adi=None, amac=None):  # eylem_model argümanlarından iş türü (çağıranlar değişmeden)
    if is_adi: return str(is_adi)
    return {"talimat": "talimat", "eposta": "eposta_taslak", "degerlendir": "degerlendir:diger"}.get(str(amac or ""), "eylem")
def kapi_saglayici(is_turu=None):  # "claude" = yalnız claude-code uyarlayıcısı (S141); None serbest
    return kapi_kural(is_turu if is_turu is not None else getattr(KAPI_YEREL, "is_turu", None) or "eylem").get("saglayici")

def _kapi_say(ad, v, lo, hi):
    try: x = float(AYAR.get(ad, v))
    except (TypeError, ValueError): x = float(v)
    return min(float(hi), max(float(lo), x))
def _kapi_g(ad):  # relay/bölüm işlevi (yoksa None)
    f = globals().get(ad); return f if callable(f) else None
def _kapi_cagir(ad, v=False):
    f = _kapi_g(ad)
    if not f: return v
    try: return f()
    except Exception: return v
def _kapi_gun(t): return datetime.date.fromtimestamp(float(t)).isoformat()
def _kapi_mesai(simdi):
    try: g, b, e = calisma_saatleri()
    except Exception: g, b, e = {0, 1, 2, 3, 4}, 540, 1080
    d = datetime.datetime.fromtimestamp(simdi)
    return d.weekday() in g and b <= d.hour * 60 + d.minute < e
def _kapi_gece(simdi):  # söz kapısıyla aynı ayarlar (soz_gece false kapatır)
    if AYAR.get("soz_gece") is False: return False
    b, e = int(_kapi_say("soz_gece_bas", 22, 0, 23)), int(_kapi_say("soz_gece_bit", 7, 0, 23)); h = datetime.datetime.fromtimestamp(simdi).hour
    return (h >= b or h < e) if b > e else (b <= h < e)
def kapi_toplanti(): return bool(_kapi_cagir("toplanti_var") or _kapi_cagir("aktif_dosya", None))
def kapi_on_mesgul():  # Konuş turu, açık sohbet ya da süren ön plan çağrısı
    try:
        s = globals().get("SOHBET") or {}; k = globals().get("_KS") or {}
        return bool(s.get("acik") or k.get("tur") or KAPI["on"] > 0)
    except Exception: return False

# --- Ortak arka plan tavanı ---------------------------------------------------------------------------------------------------------------------------
def kapi_tavan_usd():
    v = AYAR.get("arka_gunluk_usd")
    if v is None:
        try: d = float(AYAR.get("degerlendir_gunluk_usd", 3))
        except (TypeError, ValueError): d = 3.0
        return d if d > 0 else 3.0  # değerlendirici kapalıysa (0) öbür arka plan işleri bugünkü 3 $ ile
    return _kapi_say("arka_gunluk_usd", 3, 0, 1000)
def kapi_arka_mi(is_):
    return kapi_kural(is_).get("plan") == "arka" and kapi_kural(is_).get("tavan") or str(is_) in KAPI_ARKA_EK
def _kapi_usd_yukle(simdi=None):  # bugünün arka plan harcaması: günde bir claude-cagri.jsonl'in sonundan, sonra bellekte artar
    g = _kapi_gun(simdi or KAPI_SAAT()); u = KAPI["usd"]
    if u["gun"] == g: return u
    u.update(gun=g, usd=0.0)
    try:
        with open(os.path.join(BASE, "claude-cagri.jsonl"), "rb") as f:
            boy = os.fstat(f.fileno()).st_size; ofs = max(0, boy - 4 * 1024 * 1024); f.seek(ofs); sat = f.read().decode("utf-8", "replace").splitlines()
        if ofs: sat = sat[1:]
    except OSError: sat = []
    for l in sat:
        if g not in l[:200]: continue
        try: r = json.loads(l)
        except ValueError: continue
        if isinstance(r, dict) and str(r.get("at") or "")[:10] == g and kapi_arka_mi(r.get("is")):
            try: u["usd"] += float(r.get("maliyet") or 0)
            except (TypeError, ValueError): pass
    return u
def kapi_tavan_asildi(simdi=None): return _kapi_usd_yukle(simdi)["usd"] >= kapi_tavan_usd()

# --- İzin ---------------------------------------------------------------------------------------------------------------------------------------------
def kapi_engel(is_turu, simdi=None, tavan=True):  # → None (çağrılabilir) ya da neden. ÇAĞRIDAN ÖNCE; kaynaklar ön denetim için de çağırır (toplanti-sonrasi.py _pro_engel)
    r = kapi_kural(is_turu); simdi = float(simdi or KAPI_SAAT())
    if r.get("gizli") and _kapi_cagir("gizli_acik"): return "gizli kip"
    if r.get("plan") == "arka":
        if r.get("toplanti") and kapi_toplanti(): return "toplantı sürüyor"
        if r.get("sessiz") and _kapi_cagir("sessiz_acik"): return "sessiz mod"
        if r.get("saat") == "mesai":
            if _kapi_gece(simdi): return "gece"
            if not _kapi_mesai(simdi): return "mesai dışı"
        if tavan and r.get("tavan") and kapi_tavan_asildi(simdi): return "günlük tavan"
    if r.get("saglayici") == "claude" and _kapi_g("claude_yolu") and not _kapi_cagir("claude_yolu", ""): return "sağlayıcı (yalnız Claude)"
    return None

# --- Kayıt --------------------------------------------------------------------------------------------------------------------------------------------
def _kapi_satir_yaz(satirlar):  # claude-cagri.jsonl (relay write düzeni; LOCK alınamazsa yine dener)
    if not satirlar: return
    metin = "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in satirlar)
    try:
        with LOCK: write([(os.path.join(BASE, "claude-cagri.jsonl"), metin)])
    except Exception as e: print(f"KAPI: kayıt yazılamadı ({e.__class__.__name__})")
def _kapi_engel_say(is_turu, neden, simdi):  # satır yok: sayaç + günlükte neden değişince tek satır + saatte en çok bir özet (canli/kapi.jsonl)
    with KAPI_KILIT:
        _kapi_gun_sifirla(simdi); a = f"{is_turu}|{neden}"
        KAPI["engel"][a] = KAPI["engel"].get(a, 0) + 1; KAPI["gun"]["engel"] += 1
        ilk = KAPI["son_neden"].get(is_turu) != neden; KAPI["son_neden"][is_turu] = neden
        yaz = simdi - KAPI["ozet_t"] >= KAPI_OZET_SN
        if yaz:
            fark = {k: n - KAPI["engel_yazilan"].get(k, 0) for k, n in KAPI["engel"].items() if n - KAPI["engel_yazilan"].get(k, 0) > 0}
            KAPI["engel_yazilan"] = dict(KAPI["engel"]); KAPI["ozet_t"] = simdi
    if ilk: print(f"KAPI: {is_turu} — {neden}")
    if yaz and fark and not _kapi_cagir("gizli_acik"):
        try:
            with LOCK: write([(os.path.join(BASE, "kapi.jsonl"), json.dumps({"t": round(simdi, 1), "z": datetime.datetime.fromtimestamp(simdi).isoformat(timespec="seconds"), "olay": "engel_ozet", "sayi": fark}, ensure_ascii=False) + "\n")])
        except Exception: pass
def _kapi_gun_sifirla(simdi):
    g = _kapi_gun(simdi)
    if KAPI["gun"]["tarih"] != g: KAPI["gun"] = {"tarih": g, "cagri": 0, "tamam": 0, "okunamadi": 0, "hata": 0, "engel": 0}; KAPI["engel"] = {}; KAPI["engel_yazilan"] = {}
def kapi_dosya(klasor, on_ek, uzanti="json"):  # çağrı başına benzersiz istek/çıktı dosyası (eşzamanlı iki iş birbirinin cevabını almaz)
    with KAPI_KILIT: KAPI["n"] += 1; n = KAPI["n"]
    return os.path.join(klasor, f"{on_ek}-{os.getpid()}-{n}-{secrets.token_hex(3) if 'secrets' in globals() else int(time.time() * 1000) % 100000}.{uzanti}")
def kapi_brifing(ist, on_ek, zaman, klasor=None):  # v0.244.0: tek Brifing.app istemcisi (eskiden 5 kopya). ist: {"claude","args","cwd","sure"}; → ham çıktı metni ya da None (cevap yok)
    d = klasor or BASE; os.makedirs(d, exist_ok=True); cikti, istek = kapi_dosya(d, on_ek + "-cikti"), kapi_dosya(d, on_ek + "-istek")  # çağrı başına benzersiz
    fd = os.open(istek, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(dict(ist, cikti=cikti), f, ensure_ascii=False)
    kapi_gercek_cagri()
    try: subprocess.run(["open", "-g", "-W", "-n", "-a", BRIFING_APP, "--args", "--istek", istek], capture_output=True, timeout=float(zaman) + 30)
    except (OSError, subprocess.TimeoutExpired): pass
    finally:
        try: os.remove(istek)
        except OSError: pass
    try:
        with open(cikti, encoding="utf-8") as f: ham = f.read()
        os.remove(cikti); return ham
    except OSError: return None
def kapi_olcum_birak(o):  # claude_json çağırır: kapı içindeyse satırı yazmak yerine kapıya bırakır (True), değilse False
    ls = getattr(KAPI_YEREL, "olc", None)
    if getattr(KAPI_YEREL, "is_turu", None) and isinstance(ls, list): ls.append(o); return True
    return False
def kapi_gercek_cagri():  # eylem-menu _eylem_cagri: gerçek uyarlayıcı çalıştı (ölçüm satırı yoksa da kayıt yazılsın)
    if getattr(KAPI_YEREL, "is_turu", None): KAPI_YEREL.gercek = True

# --- Kapı ---------------------------------------------------------------------------------------------------------------------------------------------
def kapi_istek_parcacigi():  # relay'in HTTP istek iş parçacığı mı (socketserver ThreadingMixIn process_request_thread)? Orada bekleme yapılmaz
    try: return getattr(getattr(threading.current_thread(), "_target", None), "__name__", "") == "process_request_thread" or bool(getattr(KAPI_YEREL, "beklemesiz", False))
    except Exception: return False
def kapi_karma(*parcalar): return hashlib.sha1(json.dumps(parcalar, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:16]
def _kapi_sonuc(sonuc, neden="", **ek): return dict({"sonuc": sonuc, "neden": neden, "ham": None, "hata": None, "cozum": None, "maliyet": None, "sure_ms": None, "olculdu": False}, **ek)
def kapi_iste(is_turu, cagri, *, karma=None, coz=None):
    is_turu = str(is_turu); r = kapi_kural(is_turu); arka = r.get("plan") == "arka"; simdi = float(KAPI_SAAT())
    neden = kapi_engel(is_turu, simdi)
    if neden: _kapi_engel_say(is_turu, neden, simdi); return _kapi_sonuc("engel", neden)
    ka = f"{is_turu}|{karma}" if karma else None
    if ka:
        with KAPI_KILIT: h = KAPI["tekrar"].get(ka)
        if h and simdi < h["bitis"]:
            if h.get("tamam"):  # v0.243.1: başarılı cevabın tekrar penceresi → Claude çağrılmaz, SON BAŞARILI CEVAP döner (maliyet 0); yedeğe düşüp kararı tersine çevirmesin
                with KAPI_KILIT: _kapi_gun_sifirla(simdi); KAPI["gun"]["onbellek"] = KAPI["gun"].get("onbellek", 0) + 1
                return _kapi_sonuc("onbellek", "tekrar", ham=h.get("ham"), cozum=h.get("cozum"), maliyet=0.0, sure_ms=0, olculdu=True)
            _kapi_engel_say(is_turu, "tekrar", simdi); return _kapi_sonuc("engel", "tekrar")
    t_bas = time.time(); sem = False
    if arka:
        bekle = not kapi_istek_parcacigi(); en_cok = float(r.get("bekle_sn") or KAPI_BEKLE_SN)  # v0.243.2: kilit tutan işlerde (e-posta, iş kopyası) bekleme kısa
        while bekle and kapi_on_mesgul() and time.time() - t_bas < en_cok: time.sleep(0.5)
        if kapi_on_mesgul(): _kapi_engel_say(is_turu, "asistan meşgul", simdi); return _kapi_sonuc("engel", "asistan meşgul")
        if not (KAPI_SEM.acquire(timeout=min(KAPI_SIRA_SN, float(r.get("bekle_sn") or KAPI_SIRA_SN))) if bekle else KAPI_SEM.acquire(blocking=False)): _kapi_engel_say(is_turu, "sıra dolu", simdi); return _kapi_sonuc("engel", "sıra dolu")
        sem = True
        neden = kapi_engel(is_turu)  # beklerken toplantı başlamış, gizli kip açılmış olabilir
        if neden: KAPI_SEM.release(); _kapi_engel_say(is_turu, neden, simdi); return _kapi_sonuc("engel", neden)
    else:
        sem = KAPI_SEM.acquire(blocking=False)  # ön plan sırayı atlar: yer yoksa da çağrılır
        with KAPI_KILIT: KAPI["on"] += 1
    bekleme = round((time.time() - t_bas) * 1000)
    KAPI_YEREL.is_turu, KAPI_YEREL.olc, KAPI_YEREL.gercek = is_turu, [], False
    with KAPI_KILIT: KAPI["aktif"] += 1
    t0 = time.time()
    try:
        try: ham, hata = cagri()
        except Exception as e: ham, hata = None, e.__class__.__name__
        olc, gercek = list(KAPI_YEREL.olc or []), bool(KAPI_YEREL.gercek)
    finally:
        KAPI_YEREL.is_turu, KAPI_YEREL.olc, KAPI_YEREL.gercek = None, None, False
        with KAPI_KILIT:
            KAPI["aktif"] -= 1
            if not arka: KAPI["on"] -= 1
        if sem: KAPI_SEM.release()
    sure = round((time.time() - t0) * 1000)
    cozum = None
    if hata: sonuc = "hata"
    elif olc and olc[-1].get("hata"): sonuc = "hata"
    elif coz is not None:
        try: cozum = coz(ham) if ham else None
        except Exception: cozum = None
        sonuc = "tamam" if cozum else "okunamadi"
    else: sonuc = "tamam" if str(ham or "").strip() else "okunamadi"
    neden = str(hata)[:60] if hata else ("çıktı okunamadı" if sonuc == "okunamadi" else "")
    # tekrar önleme
    if ka:
        with KAPI_KILIT:
            if sonuc == "tamam":
                if r.get("tekrar_sn"): KAPI["tekrar"][ka] = {"bitis": simdi + float(r["tekrar_sn"]), "n": 0, "tamam": True, "ham": ham, "cozum": cozum}  # cevap bellekte (dosyaya yazılmaz)
                else: KAPI["tekrar"].pop(ka, None)
            else:
                n = int((KAPI["tekrar"].get(ka) or {}).get("n") or 0) + 1
                KAPI["tekrar"][ka] = {"bitis": simdi + KAPI_TEKRAR_HATA_SN[min(n, len(KAPI_TEKRAR_HATA_SN)) - 1], "n": n}
            if len(KAPI["tekrar"]) > 500:
                for k in sorted(KAPI["tekrar"], key=lambda k: KAPI["tekrar"][k]["bitis"])[:100]: KAPI["tekrar"].pop(k, None)
    # kayıt: claude_json'un bıraktığı satır(lar) + sonuç; ölçüm satırı yoksa ama gerçek çağrı yapıldıysa kısa satır
    mal = round(sum(float(o.get("maliyet") or 0) for o in olc), 4) if olc else None
    for i, o in enumerate(olc):
        son = i == len(olc) - 1
        o.update(sonuc=sonuc if son else "hata", neden=neden if son else "yedek", plan="arka" if arka else "on", bekleme_ms=bekleme)
        if not o.get("is"): o["is"] = is_turu
    if not olc and gercek and hata:  # gerçek çağrı cevapsız kaldı (ör. Claude yanıt vermedi): sağlık için kısa satır; ölçümsüz düz metin cevapta (yalnız sahte/eski yol) satır yok
        olc = [{"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "is": is_turu, "saglayici": "claude-code", "sure_ms": None, "duvar_ms": sure, "maliyet": 0.0, "giris": 0,
                "cikti": 0, "onbellek_oku": 0, "onbellek_yaz": 0, "onbellek_yaz_1s": 0, "onbellek_orani": None, "hata": True, "sonuc": sonuc if sonuc != "tamam" else "hata", "neden": neden or "ölçüm yok",
                "plan": "arka" if arka else "on", "bekleme_ms": bekleme}]
    _kapi_satir_yaz(olc)  # yalnız sayılar (bugünkü claude_json gibi gizli kipte de)
    with KAPI_KILIT:
        _kapi_gun_sifirla(simdi); KAPI["gun"]["cagri"] += 1; KAPI["gun"][sonuc] = KAPI["gun"].get(sonuc, 0) + 1
        if arka and mal: _kapi_usd_yukle(simdi)["usd"] += mal
        KAPI["son_neden"].pop(is_turu, None)
    return _kapi_sonuc(sonuc, neden, ham=ham, hata=hata, cozum=cozum, maliyet=mal, sure_ms=sure, olculdu=bool(olc and mal is not None))

def kapi_ac(is_turu):  # K4: kalıcı sürecin açılışı → None (açılabilir) ya da neden. Bekleme ve sıra yok (Konuş gecikmesine dokunmaz); satır yok, sayaç bugun.acilis
    is_turu = str(is_turu); simdi = float(KAPI_SAAT()); neden = kapi_engel(is_turu, simdi)
    if neden: _kapi_engel_say(is_turu, neden, simdi); return neden
    with KAPI_KILIT:
        _kapi_gun_sifirla(simdi); a = KAPI["gun"].setdefault("acilis", {}); a[is_turu] = a.get(is_turu, 0) + 1
    return None
def kapi_view():  # /status "kapi"
    simdi = float(KAPI_SAAT())
    with KAPI_KILIT:
        _kapi_gun_sifirla(simdi); g = dict(KAPI["gun"])
        en = sorted(KAPI["engel"].items(), key=lambda kv: -kv[1])[:8]
    u = _kapi_usd_yukle(simdi)
    gi = globals().get("GIRIS")  # v0.244.0: sağlık tek yoldan (her çağrının sonucu + seyrek yoklama; claude-giris.py)
    sag = {"durum": gi.get("durum"), "son_ok": round(gi["son_ok"]) if gi.get("son_ok") else None, "son_yokla": round(gi["son_yokla"]) if gi.get("son_yokla") else None} if isinstance(gi, dict) else None
    return {"bugun": g, "arka_usd": round(u["usd"], 3), "tavan_usd": kapi_tavan_usd(), "aktif": KAPI["aktif"], "engel": dict(en), "tekrar_bekleyen": sum(1 for h in list(KAPI["tekrar"].values()) if h["bitis"] > simdi), "saglik": sag}
