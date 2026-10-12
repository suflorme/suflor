# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("piper-ses")); import edilmez.
# --- Piper ile yerel Türkçe seslendirme (S36, S37) -----------------------------------------------------------------------------------
# Ayar "ses_motoru": "piper" + "piper_python" (Piper'ın Python ortamı) + "piper_model" (.onnx) varsa Türkçe okumalar (sesli çeviri,
# fısıltı, sesli özet, brifing, bas-konuş cevabı, "yazayım mı?") Piper'la okunur; ayar yoksa, dosya yoksa, arayüz dili Türkçe değilse ya da
# işçi hata verirse Mac sesine (say) düşülür. Ses dosyası depoda değildir (lisansı belirsiz; yalnız kullanıcının kendi kurulumu — S37).
# İşçi (piper-isci.py) aktarıcı açılırken bir kez yüklenir (~0,6 sn, ~0,35 GB) ve açık kalır; metin cümle cümle üretilir, ilk cümle hazır
# olunca çalınmaya başlar (afplay). Hız: "piper_hiz" (özet, cevap; varsayılan 1,0), "piper_hiz_kisa" (çeviri özü, fısıltı; varsayılan 1,15).
# Ses ve metin Mac'ten çıkmaz.
import queue, tempfile
PIPER = {"p": None, "durum": "kapali", "hata": None, "bekleyen": {}, "iptal": set(), "n": 0, "kilit": threading.Lock(), "baslat_t": 0.0}
PIPER_ISCI = _ilk(os.path.join(_UYG, "piper-isci.py"), os.path.join(_APP, "piper-isci.py"))
PIPER_GECICI = os.path.join(tempfile.gettempdir(), f"suflor-piper-{A.port}")
def piper_acik():
    return AYAR.get("ses_motoru") == "piper" and ARAYUZ_DILI == "tr" and bool(AYAR.get("piper_python")) and bool(AYAR.get("piper_model"))
def piper_hiz(kisa=False):
    try: return float(AYAR.get("piper_hiz_kisa" if kisa else "piper_hiz") or (1.15 if kisa else 1.0))
    except (TypeError, ValueError): return 1.15 if kisa else 1.0
def piper_view():
    return {"motor": "piper" if piper_acik() else "mac", "durum": PIPER["durum"] if piper_acik() else None, "hata": PIPER["hata"] if piper_acik() else None}
def _piper_okuyucu(p):
    for satir in p.stdout:
        try: o = json.loads(satir)
        except ValueError: continue
        if "hazir" in o:
            if o.get("hazir"): PIPER.update(durum="hazir", hata=None); print(f"PIPER: hazır ({o.get('sn')} sn)")
            else: PIPER.update(durum="hata", hata=str(o.get("hata") or "?")[:200]); print(f"PIPER: yüklenemedi — {PIPER['hata']}")
            continue
        kim = o.get("id")
        if kim in PIPER["iptal"]:  # okuma kesildi: kalan cümlelerin dosyaları çalınmadan silinir
            if o.get("wav"):
                try: os.remove(o["wav"])
                except OSError: pass
            if o.get("bitti") or o.get("hata"): PIPER["iptal"].discard(kim)
            continue
        q = PIPER["bekleyen"].get(kim)
        if q: q.put(o)
    if PIPER["p"] is p: PIPER.update(p=None, durum="hata" if PIPER["durum"] != "kapali" else "kapali")
    for q in list(PIPER["bekleyen"].values()): q.put({"hata": "işçi kapandı"})
def piper_baslat():
    with PIPER["kilit"]:
        p = PIPER["p"]
        if p and p.poll() is None: return True
        if not piper_acik(): return False
        py, model = str(AYAR["piper_python"]), str(AYAR["piper_model"])
        eksik = next((y for y in (py, model, PIPER_ISCI) if not os.path.exists(y)), None)
        if eksik:
            if PIPER["hata"] != "yok": print(f"PIPER: dosya yok ({os.path.basename(eksik)}) — Mac sesi")
            PIPER.update(durum="yok", hata="yok"); return False
        if time.time() - PIPER["baslat_t"] < 30 and PIPER["durum"] == "hata": return False  # art arda çöken işçiyi zorlamaz
        PIPER["baslat_t"] = time.time(); PIPER["durum"] = "yukleniyor"
        try:
            p = subprocess.Popen([py, "-I", "-B", PIPER_ISCI, model, PIPER_GECICI], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, encoding="utf-8", env=dict(os.environ, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
        except OSError as e:
            PIPER.update(durum="hata", hata=e.__class__.__name__); print(f"PIPER: başlatılamadı ({e.__class__.__name__}) — Mac sesi"); return False
        PIPER["p"] = p; threading.Thread(target=_piper_okuyucu, args=(p,), daemon=True).start()
    son = time.time() + 20
    while PIPER["durum"] == "yukleniyor" and time.time() < son: time.sleep(0.05)
    return PIPER["durum"] == "hazir"
def piper_oku(metin, hiz=1.0, iptal=None, kayit=None):
    # metni Piper'la okur; bitince True. Hiçbir parça çalınamadıysa False (çağıran Mac sesine düşer). iptal(): True dönerse kalan cümleler
    # çalınmaz; kayit["p"]: çalan afplay süreci (ses_durdur keser).
    if not metin or not piper_acik() or not piper_baslat(): return False
    PIPER["n"] += 1; kim = f"s{PIPER['n']}"; q = queue.Queue(); PIPER["bekleyen"][kim] = q; calinan = 0
    try:
        try: PIPER["p"].stdin.write(json.dumps({"id": kim, "metin": metin, "hiz": hiz}, ensure_ascii=False) + "\n"); PIPER["p"].stdin.flush()
        except (OSError, AttributeError, ValueError): return False
        while True:
            try: o = q.get(timeout=15)
            except queue.Empty: print("PIPER: cevap gelmedi (15 sn)"); return calinan > 0
            if o.get("hata"): print(f"PIPER: hata — {str(o['hata'])[:120]}"); return calinan > 0
            if o.get("bitti"): return calinan > 0 or o.get("n") == 0
            if iptal and iptal():
                PIPER["iptal"].add(kim)
                try: os.remove(o["wav"])
                except OSError: pass
                return True
            try:
                if os.environ.get("SUFLOR_TEST_PIPER_SESSIZ"): calinan += 1
                else:
                    pr = subprocess.Popen(["/usr/bin/afplay", o["wav"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if kayit is not None: kayit["p"] = pr
                    pr.wait(); calinan += 1
            except OSError: return calinan > 0
            finally:
                try: os.remove(o["wav"])
                except OSError: pass
    finally: PIPER["bekleyen"].pop(kim, None)
if piper_acik() and not deneme_aktarici(): threading.Thread(target=piper_baslat, daemon=True).start()  # ilk okuma beklemesin
