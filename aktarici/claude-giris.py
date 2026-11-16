# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("claude-giris")); import edilmez. bas-konus.py'den sonra yüklenir.
# --- Claude Code girişinin düşmesi (v0.130.0, kullanıcı 24 Ekim: 13.16'da Konuş beş soruda sessiz kaldı — "OAuth session expired and could not be refreshed") ------
# 1) Claude çağrısı hata dönünce metni günlüğe yazılır (claude_hata_bildir; önceden yalnız panoda bir an görünüyordu).
# 2) Hata giriş hatasıysa (GIRIS_RX) giriş "düştü" sayılır: günlükte bir satır, bir kez sesli uyarı (yerel ses) ve Mac bildirimi, Konuş satırında kalıcı uyarı.
#    Başarılı ilk çağrı girişi "tamam"a döndürür (günlükte "geri geldi").
# 3) Yoklama (v0.244.0, Claude kapısı K2 — seyrek): son başarılı Claude çağrısı ve son yoklama 3 saatten (claude_giris_yokla_dk) eskiyse, Konuş boştayken ve kapı izin verirken
#    (mesai içinde, toplantı dışında; gece yok) haiku ile tek sözcük cevaplı deneme (Brifing.app, kapi_brifing). Sağlığı asıl her çağrının sonucu besler (claude_json → claude_ok/hata).
#    Sürüm değişince (relay.py claude_surum_bak) aynı yoklama zorla=True ile; ayrı -p denemesi yok. Eskiden 30 dk'da bir, gece dahil (haftada ~200 çağrı). `claude auth status` kullanılmaz: yalnız kayıtlı girişe bakıyor, süresi dolmuş oturumu "giriş var" sayıyor. Ayar claude_giris_yokla: false kapatır.
#    Sağlayıcı Claude Code değilse (ayar beyin) yoklanmaz. Kayıt: canli/claude-cagri.jsonl "is": "giris" (yalnız sayılar).
GIRIS = {"durum": None, "t": 0.0, "hata": None, "son_ok": 0.0, "son_yokla": 0.0, "yokluyor": False}
GIRIS_RX = re.compile(r"authenticat|oauth|not logged in|/login|log ?in again|invalid (?:api )?key|credential|unauthori[sz]ed|\b401\b", re.I)
GIRIS_YOKLA_SN = float(AYAR.get("claude_giris_yokla_dk") or 180) * 60  # v0.244.0: 30 → 180 dk; yalnız mesai içinde (kapı "giris"), sonuç: iş günü sabahı bir yoklama
GIRIS_MODEL = str(AYAR.get("claude_giris_model") or "haiku")
GIRIS_UYARI = ("Claude oturumu düşmüş; sorulara cevap veremiyorum. Terminal'de claude yazıp giriş yapman gerekiyor.",
               "The Claude session has expired, so I can't answer. Open Terminal, type claude and log in.")
GIRIS_SATIR = ("Claude oturumu düşmüş — Terminal'de claude yazıp /login ile giriş yap", "Claude session expired — open Terminal, run claude and /login")
def claude_giris_view(): return {"durum": GIRIS["durum"], "t": GIRIS["t"] or None, "hata": GIRIS["hata"]} if GIRIS["durum"] else None
def claude_ok():  # başarılı Claude çağrısı
    GIRIS["son_ok"] = time.time()
    if GIRIS["durum"] == "dustu":
        print(f"CLAUDE GİRİŞ: geri geldi ({(time.time() - GIRIS['t']) / 60:.0f} dk sonra)")
        if KONUS.get("durum") == "hata" and KONUS.get("hata") == _t(*GIRIS_SATIR): KONUS.update(durum="kapali", hata=None)
    GIRIS.update(durum="tamam", hata=None)
def claude_hata_bildir(metin, is_="konus"):  # Claude çağrısı is_error döndü → günlük; giriş hatasıysa uyarı
    m = " ".join(str(metin or "").split())[:200] or "boş cevap"
    print(f"CLAUDE: hata ({is_}) — {m}")
    if GIRIS_RX.search(m): claude_giris_dustu(m, is_)
def claude_giris_dustu(m, is_):
    if GIRIS["durum"] != "dustu":
        GIRIS.update(durum="dustu", t=time.time(), hata=m)
        print(f"CLAUDE GİRİŞ: düştü ({is_}; son başarılı çağrı {datetime.datetime.fromtimestamp(GIRIS['son_ok']).strftime('%d.%m %H.%M') if GIRIS['son_ok'] else 'bilinmiyor'}) — {m}")
        def teslim():
            if "yerel_uyari" in globals() and AYAR.get("konusma", True): yerel_uyari(_t(*GIRIS_UYARI))
            if "bildirim" in globals(): bildirim("Suflor.me", _t("Claude oturumu düştü", "Claude session expired"), _t("Terminal'de claude yazıp /login ile giriş yap.", "Open Terminal, run claude and /login."))
        if "soz_aday" in globals(): soz_aday("sistem", "claude-giris", anahtar="claude-giris", oncelik=3, kip="bildir", teslim=teslim, gecerli_sn=1800)  # tek söz kapısı: sistem uyarısı acil (yalnız gizli kip durdurur)
        else: teslim()
    if "_konus_kur" in globals() and KONUS.get("durum") not in ("dinliyor", "yaziya", "dusunuyor", "konusuyor"): _konus_kur(durum="hata", hata=_t(*GIRIS_SATIR))
def claude_giris_yokla(zorla=False):  # → True: çalışıyor, False: çağrı yapıldı ama olmadı (giriş düşmüş, hata, yanıt yok), None: yoklanmadı (kapı engeli, claude-code yok)
    # v0.244.0 (Claude kapısı K2): tek Brifing.app istemcisi (kapi_brifing) ve kapı ("giris": mesai içinde, toplantı dışında; gece yok), haiku. zorla: ayar kapalılığını aşar, kapı kuralını aşmaz.
    if GIRIS["yokluyor"] or (not zorla and (AYAR.get("claude_giris_yokla") is False or os.environ.get("SUFLOR_AYAR"))): return None
    if not zorla and BEYIN.secim(AYAR, "telaffuz")["tur"] != "claude-code": return None  # sürüm denetimi (zorla) seçili beyinden bağımsız claude-code'u dener
    cl = claude_yolu()
    if not cl or not os.path.isdir(BRIFING_APP): return None
    GIRIS.update(yokluyor=True)
    try:
        def cagri():
            GIRIS["son_yokla"] = time.time(); t0 = time.time()
            ham = kapi_brifing({"claude": cl, "args": BEYIN.telaffuz_args(AYAR, "Yalnız şunu yaz: tamam", GIRIS_MODEL), "cwd": BASE, "sure": 60}, "giris", 60)
            if ham is None: print("CLAUDE GİRİŞ: yoklama cevap vermedi"); return None, "cevap yok"
            metin, olc = claude_json(ham, "giris", t0, bool(claude_yalin()), "claude-code", GIRIS_MODEL)  # başarı/hata bildirimi (claude_ok / claude_hata_bildir) claude_json'da
            if olc is None: print("CLAUDE GİRİŞ: yoklama çıktısı okunamadı"); return None, "çıktı okunamadı"
            return (None, "hata") if olc.get("hata") or GIRIS["durum"] == "dustu" and GIRIS["t"] >= t0 else (metin, None)
        r = kapi_iste("giris", cagri)
        if r["sonuc"] == "engel": return None
        return r["sonuc"] == "tamam"  # gerçek çağrı yapıldı: hata/okunamadı → False (sürüm denetimi uyarır; giriş hatasıysa claude_json zaten "düştü" dedi)
    except Exception as e: print(f"CLAUDE GİRİŞ: yoklama yapılamadı ({e.__class__.__name__})"); return None
    finally: GIRIS["yokluyor"] = False
def giris_yoklanmali(s=None):  # seyrek yoklama koşulu (nöbet ve testler): ana port, Konuş boşta, kapı izin veriyor, son başarılı çağrı ve son yoklama GIRIS_YOKLA_SN'den eski
    s = s or (KAPI_SAAT() if "KAPI_SAAT" in globals() else time.time())
    if A.port != int(AYAR["port"]) or _KS.get("tur") or KONUS.get("durum") in ("dinliyor", "yaziya", "dusunuyor", "konusuyor"): return False
    if s - GIRIS["son_ok"] < GIRIS_YOKLA_SN or s - GIRIS["son_yokla"] < GIRIS_YOKLA_SN: return False
    return not ("kapi_engel" in globals() and kapi_engel("giris", s))  # gece, mesai dışı, toplantı: sormadan bekler (engel sayacı şişmesin)
def _giris_nobet():
    time.sleep(120)  # aktarıcı açılışı otursun
    while True:
        try:
            if giris_yoklanmali(): claude_giris_yokla()
        except Exception as e: print(f"CLAUDE GİRİŞ: nöbet hatası {e.__class__.__name__}")
        time.sleep(60)
if not os.environ.get("SUFLOR_AYAR") and not os.environ.get("SUFLOR_TEST_BASLAT"): threading.Thread(target=_giris_nobet, daemon=True).start()
