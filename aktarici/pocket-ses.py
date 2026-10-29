# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("pocket-ses")); import edilmez. piper-ses.py'den sonra yüklenir (piper_okunur, tr_sayi, PIPER_OYNAT).
# --- Pocket TTS ile yerel Türkçe ses (S93, 19 Ekim) -----------------------------------------------------------------------------------
# 19 Ekim kör puanlamasında (testler/yerel-ses-arastirma-20261019, 11 ses × 4 soru) ilk 3'ün üçü Pocket; Piper sonuncu. Gemini toplantıya ayrıldığı için
# (S92) kullanıcının duyduğu ses ve toplantı dışı her okuma yerel: kişilikte "yerel_ses: pocket:<model>:<ses>" (ör. pocket:alperiox:female_2,
# pocket:wite:male_1) ya da ayar ses_motoru: pocket + pocket_ses. Ayar pocket_python (torch + pocket_tts ortamı) ve pocket_hf (modellerin
# HF_HOME'u) yoksa, dosya yoksa ya da işçi hata verirse Mac sesine düşülür (sıra Pocket → Mac → Piper; 19 Ekim). Model dosyaları depoda değil (kullanıcı indirir;
# wite-tech CC-BY-4.0 atıfla, alperiox MIT). İşçi (pocket-isci.py) ilk okumada açılır, boşta kapanır (28 Ekim; ayrıntı aşağıda).
# Hız ayarı yok (Pocket'ın tek konuşma hızı; doğal hızı Elif'le aynı, 5,2 hece/sn). Duygu etiketi yalnız wite modelinde: Claude'un <ton:…>'u ya da
# cümlenin kendisinden (ünlem → mutlu, hayret kalıbı → şaşkın). Ses ve metin Mac'ten çıkmaz.
if "ses_basladi" not in globals():  # v0.95.0: çalma anı ölçümü brifing-ses.py'de; bu bölüm tek başına yüklenince (testler) etkisiz
    def ses_basladi(kayit=None): pass
# 28 Ekim (mimari plan C / K4): işçi İLK okuma isteğinde açılır (aktarıcı açılırken değil; toplantıda motor Pocket ise toplantı başlayınca önceden), yalnız istenen sesin
# modeli yüklenir (Türkçe tek model; İngilizce yalnız İngilizce okuma isteyince), pocket_bos_dk (10) dk kullanılmazsa kapanır. Açılış arka planda: hazır olana dek
# pocket_oku hemen False döner, çağıran Mac sesine düşer (ilk cümle beklemez). Cevap zaman aşımı işçiyi ÖLDÜRMEZ: istek bırakılır, art arda POCKET_ZA_N zaman
# aşımında ya da işçi ölünce yeniden başlatılır, yeniden başlatmalar arasında bekleme katlanır (15, 30, 60 … en çok 600 sn). Yükleme iki hesap arasında kilitli (agir-kilit.py).
if "agir_kilit_al" not in globals():
    _ak = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aktarici", "agir-kilit.py"); exec(compile(open(_ak, encoding="utf-8").read(), _ak, "exec"), globals())
POCKET = {"p": None, "durum": "kapali", "hata": None, "bekleyen": {}, "iptal": set(), "n": 0, "kilit": threading.Lock(), "baslat_t": 0.0, "sr": 24000,
          "zs": 0, "yavas": False, "son": 0.0, "sonraki_t": 0.0, "yk": 0, "izleyici": False, "on_toplanti": None}
POCKET_CEVAP_SN = 15; POCKET_ZA_N = 3; POCKET_IZLE_SN = 30; POCKET_YUKLE_SN = 300
POCKET_ISCI = _ilk(os.path.join(_UYG, "pocket-isci.py"), os.path.join(_APP, "pocket-isci.py"))
POCKET_GECICI = os.path.join(tempfile.gettempdir(), f"suflor-pocket-{A.port}")
POCKET_MODELLER = ("wite", "alperiox", "en")  # v0.101.3: en = İngilizce temel model (İngilizce cümleler, kişilikte yerel_ses_en)
def pocket_var(): return ARAYUZ_DILI == "tr" and bool(AYAR.get("pocket_python")) and bool(AYAR.get("pocket_hf"))
def pocket_acik(): return AYAR.get("ses_motoru") == "pocket" and pocket_var()
def pocket_ses_adi(s):  # "pocket:alperiox:female_2" / "alperiox:female_2" → "alperiox:female_2"; geçersizse None
    s = str(s or "").strip()
    if s.startswith("pocket"): s = s[6:].lstrip(":")
    m, _, ad = s.partition(":")
    return f"{m}:{ad.strip() or ('mary' if m == 'en' else 'female_2')}" if m in POCKET_MODELLER else None
def pocket_varsayilan(): return pocket_ses_adi(AYAR.get("pocket_ses")) or "wite:female_2"
def pocket_kisilik_sesleri():  # işçi açılırken önceden yüklenecek sesler (kişiliklerin yerel sesleri + ayardaki)
    s = []
    try: kk = kisilikler()
    except Exception: kk = []
    for k in kk:
        for a in (k.get("yerel_ses"), k.get("ses"), k.get("yerel_ses_en")):
            v = pocket_ses_adi(a) if str(a or "").startswith("pocket") else None
            if v and v not in s: s.append(v)
    if AYAR.get("ses_motoru") == "pocket" and pocket_varsayilan() not in s: s.append(pocket_varsayilan())
    return s
def pocket_onyukle(ses=None):  # işçi açılırken ısıtılacak tek ses: istenen; yoksa kişiliklerin ilk Türkçe sesi (İngilizce hiçbir zaman önceden yüklenmez)
    v = pocket_ses_adi(ses) if ses else None
    return [v] if v else [x for x in pocket_kisilik_sesleri() if not x.startswith("en:")][:1]
def pocket_view():
    return {"durum": POCKET["durum"], "hata": POCKET["hata"], "yavas": POCKET["yavas"]} if pocket_var() else None
def pocket_bos_sn():
    try: d = float(AYAR.get("pocket_bos_dk", 10))
    except (TypeError, ValueError): d = 10.0
    return d * 60 if d > 0 else 0  # 0 = hiç kapanmaz
def _pocket_geri_cekil(neden, oldur=False):  # yeniden başlatma bekleme çizelgesi: 15, 30, 60 … 600 sn (art arda; başarılı okuma sıfırlar)
    n = POCKET["yk"]; bek = min(600, 15 * 2 ** n); POCKET["yk"] = n + 1; POCKET["sonraki_t"] = time.time() + bek
    with POCKET["kilit"]:
        p = POCKET["p"]
        if oldur:
            POCKET.update(p=None, durum="hata", hata=neden[:200])
            if p and p.poll() is None:
                try: p.terminate()
                except OSError: pass
    print(f"POCKET: {neden} — işçi en erken {bek} sn sonra yeniden açılır")
def _pocket_zaman_asimi():  # bir isteğe cevap gelmedi: işçi yaşıyor, isteği bırak; art arda POCKET_ZA_N olursa yeniden başlat
    POCKET["zs"] += 1; POCKET["yavas"] = True; POCKET["hata"] = f"yanıt vermiyor ({POCKET['zs']}/{POCKET_ZA_N})"
    p = POCKET["p"]; yasiyor = bool(p and p.poll() is None)
    print(f"POCKET: cevap gelmedi ({POCKET_CEVAP_SN} sn) — işçi {'yaşıyor, öldürülmedi' if yasiyor else 'kapanmış'} ({POCKET['zs']}/{POCKET_ZA_N})")
    if not yasiyor: POCKET.update(p=None, durum="hata"); _pocket_geri_cekil("işçi kapanmış")
    elif POCKET["zs"] >= POCKET_ZA_N: _pocket_geri_cekil(f"art arda {POCKET_ZA_N} zaman aşımı", oldur=True)
def pocket_kapat(neden):  # işçiyi temiz kapat (stdin) ve belleği bırak; durum "kapali": sonraki okuma yeniden açar
    with POCKET["kilit"]:
        p = POCKET["p"]; POCKET.update(p=None, durum="kapali", hata=None, yavas=False, zs=0)
    if p:
        try: p.stdin.close()
        except (OSError, ValueError): pass
        try: p.wait(timeout=5)
        except Exception:
            try: p.kill()
            except OSError: pass
    print(f"POCKET: işçi kapatıldı ({neden})")
def pocket_izle_bir():  # boşta kapanma + toplantıda önceden açma; izleyici her POCKET_IZLE_SN'de bir çağırır
    p = POCKET["p"]; now = time.time(); bos = pocket_bos_sn()
    if bos and "kaynak_dar" in globals() and kaynak_dar(): bos = min(bos, 60)  # C fazı: Mac dar/kritikken Pocket 1 dk boşta kalınca kapanır (toplantı motoruysa aşağıda açık kalır)
    if p and p.poll() is None and POCKET["durum"] == "hazir" and not POCKET["bekleyen"] and bos and now - POCKET["son"] > bos:
        ts = toplanti_ses_motoru()[0] if "toplanti_ses_motoru" in globals() else None
        if not ("toplanti_var" in globals() and toplanti_var() and ts == "pocket"): pocket_kapat(f"{bos / 60:.0f} dk kullanılmadı, bellek boşaltıldı")  # toplantıda Pocket konuşmacıysa açık kalır
    if not ("toplanti_var" in globals() and "toplanti_ses_motoru" in globals() and "TOPLANTI" in globals()): return
    a = TOPLANTI.get("aktif"); kim = a.get("dosya") if a else None
    if not (kim and toplanti_var()): POCKET["on_toplanti"] = None; return
    if POCKET["on_toplanti"] == kim: return  # toplantı başına bir kez (boşta kapandıysa toplantıda yeniden zorlanmaz)
    POCKET["on_toplanti"] = kim; ts = toplanti_ses_motoru()
    if ts[0] == "pocket" and pocket_var() and not (POCKET["p"] and POCKET["p"].poll() is None): print("POCKET: toplantı başladı, motor Pocket — önceden açılıyor"); pocket_baslat(ses=ts[1], bekle=False)
def _pocket_izleyici():
    while True:
        time.sleep(POCKET_IZLE_SN)
        try: pocket_izle_bir()
        except Exception as e: print(f"POCKET: izleyici hatası ({e.__class__.__name__})")
def pocket_izleyici_baslat():
    with POCKET["kilit"]:
        if POCKET["izleyici"]: return
        POCKET["izleyici"] = True
    threading.Thread(target=_pocket_izleyici, daemon=True).start()
def _pocket_okuyucu(p):
    for satir in p.stdout:
        try: o = json.loads(satir)
        except ValueError: continue
        if "hazir" in o:
            if o.get("hazir"): POCKET.update(durum="hazir", hata=None, yavas=False, zs=0, son=time.time(), sr=int(o.get("sr") or 24000)); print(f"POCKET: hazır ({o.get('sn')} sn, {', '.join(o.get('modeller') or []) or 'model isteğe göre'})")
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
    if POCKET["p"] is p:
        bekleniyordu = POCKET["durum"] != "kapali"; POCKET.update(p=None, durum="hata" if bekleniyordu else "kapali")
        if bekleniyordu: _pocket_geri_cekil("işçi beklenmedik kapandı")
    for q in list(POCKET["bekleyen"].values()): q.put({"hata": "işçi kapandı"})
def _pocket_ac(py, hf, onyukle):  # arka planda: kilit → işçi → hazır; her çıkışta durum "yukleniyor"dan çıkar
    t0 = time.time(); kilit = agir_kilit_al("pocket", 120, print); p = None
    try:
        try:
            p = subprocess.Popen([py, "-I", "-B", POCKET_ISCI, POCKET_GECICI, ",".join(onyukle)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=dict(os.environ, HF_HOME=hf, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
        except OSError as e:
            POCKET.update(durum="hata", hata=e.__class__.__name__); print(f"POCKET: başlatılamadı ({e.__class__.__name__}) — Mac sesi"); _pocket_geri_cekil("işçi başlatılamadı"); return
        with POCKET["kilit"]: POCKET["p"] = p
        threading.Thread(target=_pocket_okuyucu, args=(p,), daemon=True).start()
        while POCKET["durum"] == "yukleniyor" and p.poll() is None and time.time() - t0 < 90: time.sleep(0.05)
    finally: agir_kilit_birak(kilit)  # model yüklendi (ya da 90 sn geçti): ikinci hesap/model sırasını alsın
    if POCKET["durum"] == "yukleniyor" and p and p.poll() is None:  # yavaş yükleme (takas): öldürme, 300 sn'ye dek bekle
        print(f"POCKET: yükleme {time.time() - t0:.0f} sn'yi geçti (yavaş), bekleniyor")
        POCKET["yavas"] = True
        while POCKET["durum"] == "yukleniyor" and p.poll() is None and time.time() - t0 < POCKET_YUKLE_SN: time.sleep(0.2)
        if POCKET["durum"] == "yukleniyor" and p.poll() is None: _pocket_geri_cekil(f"yükleme {POCKET_YUKLE_SN} sn'de bitmedi", oldur=True)
def pocket_baslat(ses=None, bekle=True):
    # işçiyi (yoksa) arka planda açar; bekle=True ise en çok 30 sn hazır olmasını bekler. → hazır mı. pocket_oku bekle=False kullanır (okuma Mac sesine düşer).
    with POCKET["kilit"]:
        p = POCKET["p"]
        if not (p and p.poll() is None) and POCKET["durum"] != "yukleniyor":
            if not pocket_var(): return False
            py, hf = os.path.expanduser(str(AYAR["pocket_python"])), os.path.expanduser(str(AYAR["pocket_hf"]))
            eksik = next((y for y in (py, hf, POCKET_ISCI) if not os.path.exists(y)), None)
            if eksik:
                if POCKET["hata"] != "yok": print(f"POCKET: dosya yok ({os.path.basename(eksik)}) — Mac sesi")
                POCKET.update(durum="yok", hata="yok"); return False
            if time.time() < POCKET["sonraki_t"]: return False  # art arda çöken/yanıt vermeyen işçiyi zorlamaz (bekleme katlanır)
            POCKET["baslat_t"] = time.time(); POCKET["durum"] = "yukleniyor"; POCKET["yavas"] = False; POCKET["son"] = time.time()
            threading.Thread(target=_pocket_ac, args=(py, hf, pocket_onyukle(ses)), daemon=True).start()
    pocket_izleyici_baslat()
    if bekle:
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
    if ses.startswith("en:"): return metin  # İngilizce model sayı, saat ve yüzdeyi kendisi okur; Türkçe okunuş kuralları uygulanmaz
    m = piper_okunur(metin)
    return _rakam_yazi(m) if ses.startswith("alperiox") else m
def pocket_pcm(metin, ses=None):  # v0.113.0: toplantıya okunacak ses (24 kHz 16 bit PCM, toplanmış) — çalınmaz; olmazsa None
    parcalar = []
    return b"".join(parcalar) if pocket_oku(metin, ses=ses, topla=parcalar) and parcalar else None
def pocket_oku(metin, ses=None, iptal=None, kayit=None, duygu=None, topla=None, bekle=False):
    # metni Pocket'la okur; bitince True. Hiçbir parça çalınamadıysa False (çağıran Mac sesine düşer). ses: "wite:male_1" / "alperiox:female_2"
    # (yoksa ayardaki); iptal(): True dönerse kalan parçalar çalınmaz; kayit["p"]: çalan süreç (ses_durdur keser).
    ses = pocket_ses_adi(ses) or pocket_varsayilan()
    if not metin or not pocket_var() or not pocket_baslat(ses=ses, bekle=bekle): return False  # işçi hazır değilse (tembel açılış, boşta kapanma) False: çağıran Mac sesine düşer
    POCKET["son"] = time.time()
    if duygu is None and ses.startswith("wite"): duygu = pocket_duygu(metin)
    if ses.startswith("en:"): duygu = None
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
        sessiz = bool(os.environ.get("SUFLOR_TEST_PIPER_SESSIZ")) and topla is None
        if not sessiz and topla is None and os.access(PIPER_OYNAT, os.X_OK):
            try:
                oyn = subprocess.Popen([PIPER_OYNAT, str(sr)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if kayit is not None: kayit["p"] = oyn
            except OSError: oyn = None
        try: POCKET["p"].stdin.write(json.dumps({"id": kim, "metin": metin, "ses": ses, "duygu": duygu if ses.startswith("wite") else None}, ensure_ascii=False) + "\n"); POCKET["p"].stdin.flush()
        except (OSError, AttributeError, ValueError): kapat(False); return False
        while True:
            try: o = q.get(timeout=POCKET_CEVAP_SN)
            except queue.Empty: POCKET["iptal"].add(kim); _pocket_zaman_asimi(); kapat(calinan > 0); return calinan > 0  # işçi öldürülmez; geç gelen parçalar silinir
            if o.get("hata"): print(f"POCKET: hata — {str(o['hata'])[:120]}"); kapat(calinan > 0); return calinan > 0
            if o.get("bitti"):
                POCKET.update(zs=0, yavas=False, son=time.time(), hata=None if POCKET["hata"] and POCKET["hata"].startswith("yanıt") else POCKET["hata"])
                if POCKET["yk"]: POCKET["yk"] = 0
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
                if topla is not None:
                    with wave.open(o["wav"]) as w: topla.append(w.readframes(w.getnframes()))
                    calinan += 1
                elif sessiz: calinan or ses_basladi(kayit); calinan += 1
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
if pocket_var() and not deneme_aktarici(): pocket_izleyici_baslat()  # 28 Ekim: açılışta işçi açılmaz (bellek); ilk okumada ya da toplantıda motor Pocket ise toplantı başlayınca açılır
