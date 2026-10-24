# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("claude-giris")); import edilmez. bas-konus.py'den sonra yüklenir.
# --- Claude Code girişinin düşmesi (v0.130.0, kullanıcı 24 Ekim: 13.16'da Konuş beş soruda sessiz kaldı — "OAuth session expired and could not be refreshed") ------
# 1) Claude çağrısı hata dönünce metni günlüğe yazılır (claude_hata_bildir; önceden yalnız panoda bir an görünüyordu).
# 2) Hata giriş hatasıysa (GIRIS_RX) giriş "düştü" sayılır: günlükte bir satır, bir kez sesli uyarı (yerel ses) ve Mac bildirimi, Konuş satırında kalıcı uyarı.
#    Başarılı ilk çağrı girişi "tamam"a döndürür (günlükte "geri geldi").
# 3) Yoklama: GIRIS_YOKLA_SN'de (30 dk) bir, son başarılı Claude çağrısı daha eskiyse ve Konuş boştaysa en ucuz deneme çağrısı (telaffuz yolu, Brifing.app,
#    tek sözcük cevap). `claude auth status` kullanılmaz: yalnız kayıtlı girişe bakıyor, süresi dolmuş oturumu "giriş var" sayıyor. Ayar claude_giris_yokla: false kapatır.
#    Sağlayıcı Claude Code değilse (ayar beyin) yoklanmaz. Kayıt: canli/claude-cagri.jsonl "is": "giris" (yalnız sayılar).
GIRIS = {"durum": None, "t": 0.0, "hata": None, "son_ok": 0.0, "son_yokla": 0.0, "yokluyor": False}
GIRIS_RX = re.compile(r"authenticat|oauth|not logged in|/login|log ?in again|invalid (?:api )?key|credential|unauthori[sz]ed|\b401\b", re.I)
GIRIS_YOKLA_SN = float(AYAR.get("claude_giris_yokla_dk") or 30) * 60
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
        if "yerel_uyari" in globals() and AYAR.get("konusma", True): yerel_uyari(_t(*GIRIS_UYARI))
        if "bildirim" in globals(): bildirim("Suflor.me", _t("Claude oturumu düştü", "Claude session expired"), _t("Terminal'de claude yazıp /login ile giriş yap.", "Open Terminal, run claude and /login."))
    if "_konus_kur" in globals() and KONUS.get("durum") not in ("dinliyor", "yaziya", "dusunuyor", "konusuyor"): _konus_kur(durum="hata", hata=_t(*GIRIS_SATIR))
def claude_giris_yokla(zorla=False):  # → True: giriş çalışıyor, False: düşmüş, None: yoklanmadı
    if GIRIS["yokluyor"] or (not zorla and (AYAR.get("claude_giris_yokla") is False or os.environ.get("SUFLOR_AYAR"))): return None
    if BEYIN.secim(AYAR, "telaffuz")["tur"] != "claude-code": return None
    cl = claude_yolu()
    if not cl or not os.path.isdir(BRIFING_APP): return None
    GIRIS.update(yokluyor=True, son_yokla=time.time())
    cikti = os.path.join(BASE, "giris-cikti.json"); istek = os.path.join(BASE, "giris-istek.json"); t0 = time.time()
    try:
        if os.path.exists(cikti): os.remove(cikti)
        args = BEYIN.telaffuz_args(AYAR, "Yalnız şunu yaz: tamam", BEYIN.claude_secim(AYAR, "telaffuz")["model"])
        fd = os.open(istek, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump({"claude": cl, "args": args, "cwd": BASE, "cikti": cikti, "sure": 60}, f, ensure_ascii=False)
        subprocess.run(["open", "-g", "-W", "-n", "-a", BRIFING_APP, "--args", "--istek", istek], capture_output=True, timeout=120)
        try: ham = open(cikti, encoding="utf-8").read(); os.remove(cikti)
        except OSError: print("CLAUDE GİRİŞ: yoklama cevap vermedi"); return None
        try: j = json.loads(ham)
        except ValueError: print("CLAUDE GİRİŞ: yoklama çıktısı okunamadı"); return None
        claude_json(ham, "giris", t0, bool(claude_yalin()), "claude-code")  # başarı/hata bildirimi claude_json'da
        if not isinstance(j, dict) or not j.get("is_error"): return True
        return False if GIRIS["durum"] == "dustu" else None
    except (OSError, subprocess.TimeoutExpired) as e: print(f"CLAUDE GİRİŞ: yoklama yapılamadı ({e.__class__.__name__})"); return None
    finally:
        GIRIS["yokluyor"] = False
        try: os.remove(istek)
        except OSError: pass
def _giris_nobet():
    time.sleep(120)  # aktarıcı açılışı otursun
    while True:
        try:
            s = time.time(); bosta = A.port == int(AYAR["port"]) and not _KS.get("tur") and KONUS.get("durum") not in ("dinliyor", "yaziya", "dusunuyor", "konusuyor")
            if bosta and s - GIRIS["son_ok"] >= GIRIS_YOKLA_SN and s - GIRIS["son_yokla"] >= GIRIS_YOKLA_SN: claude_giris_yokla()
        except Exception as e: print(f"CLAUDE GİRİŞ: nöbet hatası {e.__class__.__name__}")
        time.sleep(60)
if not os.environ.get("SUFLOR_AYAR") and not os.environ.get("SUFLOR_TEST_BASLAT"): threading.Thread(target=_giris_nobet, daemon=True).start()
