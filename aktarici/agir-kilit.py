# Bölüm dosyası: relay.py'nin ad alanında çalışır (whisper-hat.py / pocket-ses.py başında exec edilir); gomme-isci.py de aynı dosyayı kendi ad alanına yükler. Bağımlılığı yok.
# --- Ağır model yükleme kilidi (28 Ekim, mimari plan C / K4) -----------------------------------------------------------------------------
# İki macOS hesabı aynı Mac'te açıkken Whisper, Pocket ve gömme modeli aynı anda yüklenince takas doldu (27 Ekim 21:45: Whisper 121 sn'de açıldı).
# Kural: ağır model YÜKLERKEN ortak bir kilit tutulur; ikincisi bekler. Model yüklendikten sonra kilit bırakılır (çalışırken kilit yok).
# Kilit = ortak dizinde tek dosya (fcntl.flock — süreç ölünce çekirdek kendiliğinden bırakır) + içinde {hesap, pid, model, t} (günlük için).
# Bekleme tavanlıdır (toplantıdaki Whisper'ı aç bırakmasın); tavan dolarsa ya da kilidin içindeki zaman 10 dk'dan eskiyse (bayat: takılmış yükleyici)
# kilit atılır ve yükleme kilitsiz sürer. Dizin yazılamıyorsa kilit atlanır. Yerleşim /Users/Shared (herkese yazılır); iki hesap da aynı dizini görmeli.
import os, sys, time, json, fcntl, getpass, contextlib
AGIR_KILIT_DIZIN = os.environ.get("SUFLOR_AGIR_KILIT") or "/Users/Shared/suflor-agir-kilit"
AGIR_KILIT_BAYAT_SN = 600
def _ak_dizin():
    try:
        os.makedirs(AGIR_KILIT_DIZIN, mode=0o777, exist_ok=True)
        try: os.chmod(AGIR_KILIT_DIZIN, 0o777)  # umask'e rağmen; yalnız sahibi yapabilir, değilse zaten yazılabilir
        except OSError: pass
        return AGIR_KILIT_DIZIN if os.access(AGIR_KILIT_DIZIN, os.W_OK | os.X_OK) else None
    except OSError: return None
def _ak_oku(fd):
    try: os.lseek(fd, 0, os.SEEK_SET); return json.loads(os.read(fd, 4096) or b"{}")
    except (OSError, ValueError): return {}
def agir_kilit_al(model, bekle_sn=120, log=print):
    # → kilit tutamacı (agir_kilit_birak'a verilir) ya da None (kilitsiz sürülür: dizin yok, bekleme tavanı, bayat). Hesap/pid bilgisi dosyaya yazılır.
    d = _ak_dizin()
    if not d: return None
    try:
        fd = os.open(os.path.join(d, "yukleme.lock"), os.O_RDWR | os.O_CREAT, 0o666)
        try: os.fchmod(fd, 0o666)
        except OSError: pass
    except OSError: return None
    ben = getpass.getuser(); son = time.time() + bekle_sn; bildirdi = False
    while True:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
        except OSError:
            b = _ak_oku(fd); yas = time.time() - float(b["t"]) if b.get("t") else 0  # bilgi henüz yazılmadıysa taze
            if yas > AGIR_KILIT_BAYAT_SN:  # tutan süreç yaşıyor ama 10 dk'dır yüklüyor: takılmış sayılır, beklenmez
                log(f"AĞIR KİLİT: {b.get('model') or '?'} yüklemesi {yas / 60:.0f} dk'dır sürüyor (bayat) — beklenmeden {model} yükleniyor"); os.close(fd); return None
            if not bildirdi:
                kim = f"öteki hesap ({b.get('hesap')})" if b.get("hesap") and b.get("hesap") != ben else "başka bir yükleme"
                log(f"AĞIR KİLİT: {kim} {b.get('model') or 'model'} yüklüyor, {model} için bekleniyor"); bildirdi = True; t_bekle = time.time()
            if time.time() > son:
                log(f"AĞIR KİLİT: {bekle_sn:.0f} sn beklendi, {model} kilitsiz yükleniyor"); os.close(fd); return None
            time.sleep(0.25)
    try: os.ftruncate(fd, 0); os.lseek(fd, 0, os.SEEK_SET); os.write(fd, json.dumps({"hesap": ben, "pid": os.getpid(), "model": model, "t": round(time.time(), 1)}).encode())
    except OSError: pass
    if bildirdi: log(f"AĞIR KİLİT: {model} sırası geldi ({time.time() - t_bekle:.0f} sn bekledi)")
    return fd
def agir_kilit_birak(fd):
    if fd is None: return
    try: os.ftruncate(fd, 0)
    except OSError: pass
    try: fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError: pass
    try: os.close(fd)
    except OSError: pass
@contextlib.contextmanager
def agir_kilit(model, bekle_sn=120, log=print):
    fd = agir_kilit_al(model, bekle_sn, log)
    try: yield fd
    finally: agir_kilit_birak(fd)
