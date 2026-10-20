# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("pocket-ses")); import edilmez. piper-ses.py'den sonra yüklenir (piper_okunur, tr_sayi, PIPER_OYNAT).
# --- Pocket TTS ile yerel Türkçe ses (S93, 19 Ekim) -----------------------------------------------------------------------------------
# 19 Ekim kör puanlamasında (testler/yerel-ses-arastirma-20261019, 11 ses × 4 soru) ilk 3'ün üçü Pocket; Piper sonuncu. Gemini toplantıya ayrıldığı için
# (S92) kullanıcının duyduğu ses ve toplantı dışı her okuma yerel: kişilikte "yerel_ses: pocket:<model>:<ses>" (ör. pocket:alperiox:female_2,
# pocket:wite:male_1) ya da ayar ses_motoru: pocket + pocket_ses. Ayar pocket_python (torch + pocket_tts ortamı) ve pocket_hf (modellerin
# HF_HOME'u) yoksa, dosya yoksa ya da işçi hata verirse Mac sesine düşülür (sıra Pocket → Mac → Piper; 19 Ekim). Model dosyaları depoda değil (kullanıcı indirir;
# wite-tech CC-BY-4.0 atıfla, alperiox MIT). İşçi (pocket-isci.py) aktarıcı açılırken bir kez yüklenir (iki model ~4,6 sn) ve açık kalır.
# Hız ayarı yok (Pocket'ın tek konuşma hızı; doğal hızı Elif'le aynı, 5,2 hece/sn). Duygu etiketi yalnız wite modelinde: Claude'un <ton:…>'u ya da
# cümlenin kendisinden (ünlem → mutlu, hayret kalıbı → şaşkın). Ses ve metin Mac'ten çıkmaz.
if "ses_basladi" not in globals():  # v0.95.0: çalma anı ölçümü brifing-ses.py'de; bu bölüm tek başına yüklenince (testler) etkisiz
    def ses_basladi(kayit=None): pass
POCKET = {"p": None, "durum": "kapali", "hata": None, "bekleyen": {}, "iptal": set(), "n": 0, "kilit": threading.Lock(), "baslat_t": 0.0, "sr": 24000}
POCKET_ISCI = _ilk(os.path.join(_UYG, "pocket-isci.py"), os.path.join(_APP, "pocket-isci.py"))
POCKET_GECICI = os.path.join(tempfile.gettempdir(), f"suflor-pocket-{A.port}")
POCKET_MODELLER = ("wite", "alperiox")
def pocket_var(): return ARAYUZ_DILI == "tr" and bool(AYAR.get("pocket_python")) and bool(AYAR.get("pocket_hf"))
def pocket_acik(): return AYAR.get("ses_motoru") == "pocket" and pocket_var()
def pocket_ses_adi(s):  # "pocket:alperiox:female_2" / "alperiox:female_2" → "alperiox:female_2"; geçersizse None
    s = str(s or "").strip()
    if s.startswith("pocket"): s = s[6:].lstrip(":")
    m, _, ad = s.partition(":")
    return f"{m}:{ad.strip() or 'female_2'}" if m in POCKET_MODELLER else None
def pocket_varsayilan(): return pocket_ses_adi(AYAR.get("pocket_ses")) or "wite:female_2"
def pocket_kisilik_sesleri():  # işçi açılırken önceden yüklenecek sesler (kişiliklerin yerel sesleri + ayardaki)
    s = []
    try: kk = kisilikler()
    except Exception: kk = []
    for k in kk:
        for a in (k.get("yerel_ses"), k.get("ses")):
            v = pocket_ses_adi(a) if str(a or "").startswith("pocket") else None
            if v and v not in s: s.append(v)
    if AYAR.get("ses_motoru") == "pocket" and pocket_varsayilan() not in s: s.append(pocket_varsayilan())
    return s
def pocket_view():
    return {"durum": POCKET["durum"], "hata": POCKET["hata"]} if pocket_var() else None
def _pocket_okuyucu(p):
    for satir in p.stdout:
        try: o = json.loads(satir)
        except ValueError: continue
        if "hazir" in o:
            if o.get("hazir"): POCKET.update(durum="hazir", hata=None, sr=int(o.get("sr") or 24000)); print(f"POCKET: hazır ({o.get('sn')} sn, {', '.join(o.get('modeller') or []) or 'model isteğe göre'})")
            else: POCKET.update(durum="hata", hata=str(o.get("hata") or "?")[:200]); print(f"POCKET: yüklenemedi — {POCKET['hata']}")
            continue
        kim = o.get("id")
        if kim in POCKET["iptal"]:  # okuma kesildi: kalan parçalar çalınmadan silinir
            if o.get("wav"):
                try: os.remove(o["wav"])
                except OSError: pass
            if o.get("bitti") or o.get("hata"): POCKET["iptal"].discard(kim)
            continue
        q = POCKET["bekleyen"].get(kim)
        if q: q.put(o)
    if POCKET["p"] is p: POCKET.update(p=None, durum="hata" if POCKET["durum"] != "kapali" else "kapali")
    for q in list(POCKET["bekleyen"].values()): q.put({"hata": "işçi kapandı"})
def pocket_baslat():
    with POCKET["kilit"]:
        p = POCKET["p"]
        if p and p.poll() is None: return True
        if not pocket_var(): return False
        py, hf = os.path.expanduser(str(AYAR["pocket_python"])), os.path.expanduser(str(AYAR["pocket_hf"]))
        eksik = next((y for y in (py, hf, POCKET_ISCI) if not os.path.exists(y)), None)
        if eksik:
            if POCKET["hata"] != "yok": print(f"POCKET: dosya yok ({os.path.basename(eksik)}) — Mac sesi")
            POCKET.update(durum="yok", hata="yok"); return False
        if time.time() - POCKET["baslat_t"] < 30 and POCKET["durum"] == "hata": return False  # art arda çöken işçiyi zorlamaz
        POCKET["baslat_t"] = time.time(); POCKET["durum"] = "yukleniyor"
        try:
            p = subprocess.Popen([py, "-I", "-B", POCKET_ISCI, POCKET_GECICI, ",".join(pocket_kisilik_sesleri())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=dict(os.environ, HF_HOME=hf, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
        except OSError as e:
            POCKET.update(durum="hata", hata=e.__class__.__name__); print(f"POCKET: başlatılamadı ({e.__class__.__name__}) — Mac sesi"); return False
        POCKET["p"] = p; threading.Thread(target=_pocket_okuyucu, args=(p,), daemon=True).start()
    son = time.time() + 30
    while POCKET["durum"] == "yukleniyor" and time.time() < son: time.sleep(0.05)
    return POCKET["durum"] == "hazir"
# Duygu (yalnız wite): Claude'un tonu (TON_USLUP adları) ya da cümlenin kendisi. alperiox etiket bilmez (gönderilmez).
POCKET_TON = {"kotu_haber": "üzgün", "sakin": "sakin", "yumusak": "sakin", "ciddi": "sakin"}
POCKET_SASKIN_RX = re.compile(r"^\s*(?:gerçekten mi|ciddi misin|vay(?: be)?|hadi ya|aa+|nasıl yani|emin misin|sahi mi|yok artık)\b", re.I)
def pocket_duygu(metin):
    t = POCKET_TON.get(ton_bul(metin) or "")
    if t: return t
    if POCKET_SASKIN_RX.search(metin or ""): return "şaşkın"
    if (metin or "").rstrip().endswith("!"): return "mutlu"
    return None
def _rakam_yazi(m):  # alperiox rakam okuyamaz (19 Ekim: "1.250.000"da cümleyi kesti) → yazıya; piper_okunur'dan sonra kalan rakamlar
    return re.sub(r"(?<![\d,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?![\d.]\d)", lambda x: tr_sayi(x.group(1).replace(".", "")) + (" virgül " + tr_sayi(x.group(2)) if x.group(2) else ""), m)
def pocket_metin(metin, ses):
    m = piper_okunur(metin)
    return _rakam_yazi(m) if ses.startswith("alperiox") else m
def pocket_oku(metin, ses=None, iptal=None, kayit=None, duygu=None):
    # metni Pocket'la okur; bitince True. Hiçbir parça çalınamadıysa False (çağıran Mac sesine düşer). ses: "wite:male_1" / "alperiox:female_2"
    # (yoksa ayardaki); iptal(): True dönerse kalan parçalar çalınmaz; kayit["p"]: çalan süreç (ses_durdur keser).
    ses = pocket_ses_adi(ses) or pocket_varsayilan()
    if not metin or not pocket_var() or not pocket_baslat(): return False
    if duygu is None and ses.startswith("wite"): duygu = pocket_duygu(metin)
    metin = pocket_metin(metin, ses)
    POCKET["n"] += 1; kim = f"k{POCKET['n']}"; q = queue.Queue(); POCKET["bekleyen"][kim] = q; calinan = 0; oyn = None; sure = 0.0; t0 = time.time(); sr = POCKET.get("sr") or 24000
    def kapat(bekle):
        if not oyn: return
        try: oyn.stdin.close()
        except (OSError, ValueError): pass
        if bekle:
            try: oyn.wait(timeout=max(1.0, sure - (time.time() - t0)) + 5)
            except subprocess.TimeoutExpired: pass
        if oyn.poll() is None: oyn.terminate()
    try:
        sessiz = bool(os.environ.get("SUFLOR_TEST_PIPER_SESSIZ"))
        if not sessiz and os.access(PIPER_OYNAT, os.X_OK):
            try:
                oyn = subprocess.Popen([PIPER_OYNAT, str(sr)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if kayit is not None: kayit["p"] = oyn
            except OSError: oyn = None
        try: POCKET["p"].stdin.write(json.dumps({"id": kim, "metin": metin, "ses": ses, "duygu": duygu if ses.startswith("wite") else None}, ensure_ascii=False) + "\n"); POCKET["p"].stdin.flush()
        except (OSError, AttributeError, ValueError): kapat(False); return False
        while True:
            try: o = q.get(timeout=15)
            except queue.Empty: print("POCKET: cevap gelmedi (15 sn)"); kapat(calinan > 0); return calinan > 0
            if o.get("hata"): print(f"POCKET: hata — {str(o['hata'])[:120]}"); kapat(calinan > 0); return calinan > 0
            if o.get("bitti"):
                kapat(True)
                if o.get("n"): print(f"POCKET: {ses}{' · ' + duygu if duygu and ses.startswith('wite') else ''} · {len(metin)} karakter · ilk ses {POCKET.get('ilk', 0):.2f} sn")
                return calinan > 0 or o.get("n") == 0
            if "ilk" in o: POCKET["ilk"] = o["ilk"]
            if iptal and iptal():
                POCKET["iptal"].add(kim); kapat(False)
                try: os.remove(o["wav"])
                except OSError: pass
                return True
            try:
                if sessiz: calinan or ses_basladi(kayit); calinan += 1
                elif oyn:
                    with wave.open(o["wav"]) as w: b = w.readframes(w.getnframes())
                    try: oyn.stdin.write(b); oyn.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError): POCKET["iptal"].add(kim); return True  # çalıcı kesildi (ses_durdur)
                    if not calinan: ses_basladi(kayit)  # v0.95.0: ilk ses parçası çalıcıda
                    calinan += 1; sure += len(b) / 2 / sr
                else:
                    pr = subprocess.Popen(["/usr/bin/afplay", o["wav"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if kayit is not None: kayit["p"] = pr
                    if not calinan: ses_basladi(kayit)
                    pr.wait(); calinan += 1
            except (OSError, wave.Error): kapat(False); return calinan > 0
            finally:
                try: os.remove(o["wav"])
                except OSError: pass
    finally: POCKET["bekleyen"].pop(kim, None)
def yerel_oku(metin, kisa=False):  # fısıltı, sesli çeviri: o anki kişiliğin yerel sesi; okunamazsa False (çağıran Mac sesine düşer). Pocket kişiliğinde Piper denenmez
    km, kv = kisilik_sesi()[:2]
    if km == "pocket": return pocket_oku(metin, ses=kv)  # sıra Pocket → Mac → Piper (19 Ekim)
    return piper_oku(metin, piper_hiz(kisa=kisa))
if pocket_var() and not deneme_aktarici(): threading.Thread(target=pocket_baslat, daemon=True).start()  # ilk okuma beklemesin
