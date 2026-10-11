# Suflor.me aktarıcı bölümü: Panodan dosyadan döküm. Ayrı modül değildir — relay.py bunu kendi ad alanında, eski yerinde çalıştırır (bolum("dosyadan")):
# STATE, LOCK, AYAR, write, _t … relay.py'nin; buradaki tanımlar da relay.py'ye aittir. import etme. Python 3.9 uyumlu.
# --- Panoya bırakılan ses/video → dosyadan döküm (10 Ekim) ------------------------------------------------------------------
# Pano önce /dosyadan-karar {islem: sor} ile sorar (toplantı, meşgul, biçim, disk), sonra dosyayı ham gövdeyle (base64'süz, 40 MB sınırı
# yok) POST /dosyadan'a akıtır → canli/dosyadan/<ad> (geçici; iş bitince silinir) → `toplanti-claude.py dosyadan` arka planda (Whisper
# ayrı süreçte). Toplantı sürerken başlamaz; aynı anda tek iş. Çıktı: proje klasörü korunan klasörde değilse <proje>/gorusmeler, değilse
# canli/dokum/ (launchd Masaüstü/Belgeler'e yazamaz; denemek izin penceresi açabilir). Aynı adlı döküm varsa panoda Üzerine yaz / Vazgeç
# (dosya o arada bekler, yeniden yüklenmez). İş sürerken toplantı başlarsa süreç grubu durdurulur (SIGSTOP; işlemci boşalır, bellek kalır),
# toplantı bitince (eklenti 60 sn nabız göndermeyince) kaldığı yerden sürer (SIGCONT). Süreç grubu kimliği canli/dosyadan/surec.pid'de:
# aktarıcı duraklatılmış işin ortasında yeniden başlarsa açılışta kalan grup kapatılır (durdurulmuş süreç yoksa sonsuza dek bellekte kalırdı).
SES_UZANTI = (".m4a", ".mp4", ".mov", ".m4v", ".wav", ".mp3", ".aac", ".caf", ".aif", ".aiff", ".3gp")
DOSYADAN_GB = 4
DOSYADAN = {}; DOSYADAN_KILIT = threading.Lock()
def dosyadan_view():
    return {k: DOSYADAN.get(k) for k in ("durum", "ad", "adim", "blok", "toplam", "md", "yer", "var", "hata", "durakli")} if DOSYADAN.get("durum") else None
def _dosyadan_pid(): return os.path.join(BASE, "dosyadan", "surec.pid")
def _dosyadan_sinyal(pr, *sig):
    for g in sig:
        try: os.killpg(pr.pid, g)
        except OSError: pass
def _dosyadan_bekci(pr):  # iş sürerken toplantı başlarsa duraklat, bitince sürdür
    import signal
    while pr.poll() is None and DOSYADAN.get("p") is pr and DOSYADAN.get("durum") == "calisiyor":  # Vazgeç'te çık: kapanan süreci yeniden durdurmasın
        t = toplanti_var()
        if t and not DOSYADAN.get("durakli"):
            _dosyadan_sinyal(pr, signal.SIGSTOP); DOSYADAN["durakli"] = True; print("DOSYADAN: toplantı başladı — duraklatıldı")
        elif not t and DOSYADAN.get("durakli"):
            _dosyadan_sinyal(pr, signal.SIGCONT); DOSYADAN["durakli"] = False; print("DOSYADAN: toplantı bitti — sürüyor")
        time.sleep(1)
def dosyadan_artik_temizle():  # açılışta: önceki aktarıcıdan kalan (belki duraklatılmış) iş ve geçici dosyalar
    import signal
    try: pid = int(open(_dosyadan_pid()).read().strip())
    except (OSError, ValueError): pid = 0
    if pid:
        k = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
        if "toplanti-claude.py" in k and " dosyadan " in k:  # kimlik başka sürece geçmişse dokunma
            for g in (signal.SIGCONT, signal.SIGTERM):
                try: os.killpg(pid, g)
                except OSError: pass
            threading.Timer(3, lambda: [os.killpg(pid, signal.SIGKILL) for _ in [0] if subprocess.run(["ps", "-axo", "pgid="], capture_output=True, text=True).stdout.split().count(str(pid))]).start()
            print("DOSYADAN: önceki aktarıcıdan kalan iş kapatıldı")
    shutil.rmtree(os.path.join(BASE, "dosyadan"), ignore_errors=True)
def _dosyadan_ad(ad):
    return re.sub(r"[^\w.\- ]", "_", os.path.basename(str(ad or "")))[:120].strip(" .")
def _dosyadan_cikti():
    ev = os.path.expanduser("~")
    korunan = [os.path.join(ev, x) for x in ("Desktop", "Documents", "Downloads", "Library/Mobile Documents")]
    p = os.path.realpath(AYAR["proje"])
    if not any(p == k or p.startswith(k + "/") for k in korunan):
        for y in (os.path.join(p, "gorusmeler"), p):
            if os.path.isdir(y) and os.access(y, os.W_OK): return y
    y = os.path.join(BASE, "dokum"); os.makedirs(y, exist_ok=True); return y
def dosyadan_sor(ad, boyut):  # yüklemeden önce: başlayabilir mi
    if not _dosyadan_ad(ad).lower().endswith(SES_UZANTI): return _t("ses/video değil (m4a, mp4, mov, wav, mp3…)", "not audio/video (m4a, mp4, mov, wav, mp3…)")
    if toplanti_var(): return _t("toplantı sürüyor — dosyadan döküm toplantı bitince (canlı döküm yavaşlamasın)", "a meeting is on — transcribe the file after it (so the live transcript is not slowed)")
    if DOSYADAN.get("durum") in ("yukleniyor", "calisiyor", "var"): return _t("başka bir dosyanın dökümü sürüyor", "another file is being transcribed")
    if not 0 < boyut <= DOSYADAN_GB << 30: return _t(f"dosya boş ya da {DOSYADAN_GB} GB'tan büyük", f"file empty or larger than {DOSYADAN_GB} GB")
    if shutil.disk_usage(BASE).free < boyut + (2 << 30): return _t("diskte yer yok (dosya + 2 GB gerekir)", "not enough disk space (file + 2 GB needed)")
    return None
def dosyadan_al(h, n):  # h: istek işleyicisi; gövde ham dosya (n bayt)
    import urllib.parse
    ad = _dosyadan_ad(urllib.parse.unquote(str(h.headers.get("X-Suflor-Ad") or "")))
    with DOSYADAN_KILIT:
        err = dosyadan_sor(ad, n)
        if err: return {"ok": False, "err": err}
        DOSYADAN.clear(); DOSYADAN.update(durum="yukleniyor", ad=ad, at=time.time())
    kl = os.path.join(BASE, "dosyadan"); os.makedirs(kl, exist_ok=True); yol = os.path.join(kl, ad); kalan = n
    try:
        with open(yol, "wb") as f:
            while kalan > 0:
                b = h.rfile.read(min(kalan, 1 << 20))
                if not b: break
                f.write(b); kalan -= len(b)
        if kalan: raise OSError("eksik")
        try: os.utime(yol, (time.time(), int(h.headers.get("X-Suflor-Tarih") or 0) / 1000 or time.time()))  # dökümün saati dosya tarihinden
        except ValueError: pass
    except OSError as e:
        try: os.remove(yol)
        except OSError: pass
        DOSYADAN.clear(); print(f"DOSYADAN: yükleme yarıda ({e.__class__.__name__})"); return {"ok": False, "err": _t("dosya aktarılamadı", "file transfer failed")}
    print(f"DOSYADAN: {ad} alındı ({round(n / 1048576, 1)} MB) · döküm başlıyor")
    threading.Thread(target=_dosyadan_calis, args=(yol, False), daemon=True).start()
    return {"ok": True, "ad": ad}
def _dosyadan_calis(yol, uzerine):
    tc = next((y for y in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "toplanti-claude.py"),
                           os.path.join(os.path.expanduser(str(AYAR.get("kod") or "")), "toplanti-claude.py")) if os.path.isfile(y)), None)
    cikti = _dosyadan_cikti()
    DOSYADAN.update(durum="calisiyor", adim=_t("ses hazırlanıyor", "preparing audio"), blok=None, toplam=None, var=None, hata=None)
    if not tc: return _dosyadan_bitir(yol, hata=_t("toplanti-claude.py yok — aktarici-kur.command", "toplanti-claude.py missing — aktarici-kur.command"))
    k = [sys.executable, "-u", tc, "--dir", BASE, "--relay", f"http://127.0.0.1:{A.port}", "dosyadan", yol, "--zorla", "--cikti", cikti] + (["--uzerine"] if uzerine else [])
    try: p = subprocess.Popen(k, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", start_new_session=True,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1"))
    except OSError as e: return _dosyadan_bitir(yol, hata=str(e)[:160])
    DOSYADAN.update(p=p, durakli=False); md, son = None, ""
    try:
        with open(_dosyadan_pid(), "w") as f: f.write(str(p.pid))
    except OSError: pass
    threading.Thread(target=_dosyadan_bekci, args=(p,), daemon=True).start()
    for l in p.stdout:
        l = l.strip()
        if not l: continue
        son = l
        if m := re.search(r"blok (\d+)/(\d+)", l): DOSYADAN.update(blok=int(m[1]), toplam=int(m[2]), adim=None)
        elif m := re.match(r"ses ([\d.]+) dk", l): DOSYADAN.update(adim=_t(f"{m[1]} dk ses · Whisper yüklendi", f"{m[1]} min audio · Whisper loaded"))
        elif m := re.match(r"Döküm yazıldı: (.+?\.md) ", l): md = m[1]
    p.wait(); DOSYADAN.pop("p", None); DOSYADAN["durakli"] = False
    try: os.remove(_dosyadan_pid())
    except OSError: pass
    if DOSYADAN.get("durum") != "calisiyor": return  # Vazgeç
    if md:
        DOSYADAN["yer"] = "canli/dokum" if os.path.dirname(md) == os.path.join(BASE, "dokum") else os.path.dirname(md).replace(os.path.expanduser("~"), "~", 1)
        bildirim("Suflor.me", _t("Döküm hazır", "Transcript ready"), os.path.basename(md))
        return _dosyadan_bitir(yol, md=md)
    if "zaten var" in son:  # dosya bekler; panoda Üzerine yaz / Vazgeç
        DOSYADAN.update(durum="var", var=os.path.basename(son.split(": ", 1)[-1].split(",")[0].strip())); print(f"DOSYADAN: aynı adlı döküm var ({DOSYADAN['var']})"); return
    _dosyadan_bitir(yol, hata=(son or _t("döküm yarıda kaldı", "transcription stopped"))[:200])
def _dosyadan_bitir(yol, md=None, hata=None):
    try: os.remove(yol)
    except OSError: pass
    DOSYADAN.update(durum="bitti" if md else "hata", md=md, hata=hata, adim=None, yol=None)
    print(f"DOSYADAN: " + (f"bitti · {os.path.basename(md)}" if md else f"hata · {hata}"))
def dosyadan_karar(p):
    i = p.get("islem")
    if i == "sor":
        try: err = dosyadan_sor(p.get("ad"), int(p.get("boyut") or 0))
        except ValueError: err = "boyut"
        return {"ok": not err, "err": err}
    with DOSYADAN_KILIT:
        d = DOSYADAN.get("durum"); yol = os.path.join(BASE, "dosyadan", DOSYADAN.get("ad") or "-")
        if i == "uzerine" and d == "var":
            threading.Thread(target=_dosyadan_calis, args=(yol, True), daemon=True).start(); DOSYADAN["durum"] = "calisiyor"; return {"ok": True}
        if i == "vazgec" and d in ("var", "calisiyor"):
            pr = DOSYADAN.get("p"); DOSYADAN["durum"] = "iptal"
            if pr:  # SIGCONT + SIGTERM (Whisper işçisi de aynı grupta); SIGTERM'ü yok sayan multiprocessing izleyicisi 3 sn sonra SIGKILL'le
                import signal  # sinyal numarası değil adı: macOS'ta 18 SIGTSTP'dir (Linux'ta SIGCONT)
                _dosyadan_sinyal(pr, signal.SIGCONT, signal.SIGTERM); threading.Timer(3, _dosyadan_sinyal, (pr, signal.SIGKILL)).start()
            try: os.remove(yol)
            except OSError: pass
            DOSYADAN.clear(); print("DOSYADAN: vazgeçildi"); return {"ok": True}
        if i == "kapat" and d in ("bitti", "hata"): DOSYADAN.clear(); return {"ok": True}
        if i == "ac" and d == "bitti" and os.path.isfile(DOSYADAN.get("md") or ""):
            if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"AÇ (deneme): döküm {os.path.basename(DOSYADAN['md'])}"); return {"ok": True}
            k = subprocess.run(["open"] + (["-a", str(AYAR["ozet_uygulama"])] if AYAR.get("ozet_uygulama") else []) + [DOSYADAN["md"]], capture_output=True, text=True, timeout=15)
            return {"ok": not k.returncode, "err": (k.stderr or "").strip()[:160]}
    return {"ok": False, "err": _t("bu durumda yapılamaz", "not possible now")}
