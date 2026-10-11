#!/usr/bin/env python3
# Suflor.me kurulum sihirbazı — yerel sunucu (yalnız 127.0.0.1). Tarayıcıdaki sihirbaz (sihirbaz/) bu uçlarla konuşur:
# Mac denetimi, modellerin arka planda inmesi, Claude Code denetimi, profil (Claude'un hazırladığı çalışma notu), dosya
# yükleme, klasör seçimi, takvim izni ve son kurulum (ayar.json, proje klasörü, /toplanti komutu, aktarıcı). Durum
# ~/Library/Application Support/Suflor/kurulum.json'da: sekme kapanırsa sihirbaz kaldığı adımdan sürer.
#   python3 kurulum.py [--port 8770] [--ac]     (--ac: tarayıcıda aç)
# Kurulumun geri kalanı da burada (tek kurulum komutu; .command dosyaları bunları çağıran tek satırlık sarmalayıcı):
#   python3 kurulum.py kur        aktarıcıyı kurar / günceller (Mac açılışında kendiliğinden başlar)   ← aktarici-kur.command
#   python3 kurulum.py kaldir     otomatik başlatmayı kaldırır (veri yerinde kalır)                      ← aktarici-kur.command --kaldir
#   python3 kurulum.py modeller   yerel modeller ve Python ortamı (olanı yeniden kurmaz)                ← modeller-kur.command
#   python3 kurulum.py guncelle   son sürümü alır (git klonu: git pull; değilse açık depodan), kurar     ← guncelle.command
# Deneme: SUFLOR_EV=<geçici klasör> ev klasörünü değiştirir (ayar, uygulama, proje oraya yazılır; aktarıcı kurulmaz).
import argparse, shlex, datetime, getpass, json, os, platform, re, secrets, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.dont_write_bytecode = True

KOD = os.path.dirname(os.path.abspath(__file__))
EV = os.environ.get("SUFLOR_EV") or os.path.expanduser("~")
DENEME = bool(os.environ.get("SUFLOR_EV"))
DESTEK = os.path.join(EV, "Library", "Application Support", "Suflor")
AYAR_YOL = os.path.join(DESTEK, "ayar.json")
KAYIT = os.path.join(DESTEK, "kurulum.json")
YUKLEME = os.path.join(DESTEK, "kurulum")
ORTAK = "/Users/Shared/Suflor"
PY = "/usr/bin/python3"
A = None  # komut satırı (aşağıda, __main__)

def sh(*c, zaman=20):
    try: return subprocess.run(list(c), capture_output=True, text=True, timeout=zaman).stdout.strip()
    except Exception: return ""
def oku_json(yol, vars_=None):
    try: return json.load(open(yol, encoding="utf-8"))
    except Exception: return vars_ if vars_ is not None else {}
_YAZ = threading.Lock()
def yaz_json(yol, d):
    with _YAZ:  # sihirbaz art arda kaydeder; aynı geçici dosyaya iki iş parçacığı yazmasın
        os.makedirs(os.path.dirname(yol), exist_ok=True); tmp = f"{yol}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, yol)
def ayar(): return oku_json(AYAR_YOL)
def gen(p): return os.path.expanduser(p.replace("~", EV, 1)) if p.startswith("~") else p

# ---------- Mac ----------
_MAC = {}
def mac():
    if not _MAC:
        mv = platform.mac_ver()[0] or "0"
        _MAC.update(islemci=sh("sysctl", "-n", "machdep.cpu.brand_string") or platform.machine(), arm=platform.machine() == "arm64",
                    macos=mv, macos_ok=int(mv.split(".")[0]) >= 14, bellek_gb=round(int(sh("sysctl", "-n", "hw.memsize") or 0) / 2 ** 30),
                    python=platform.python_version() if sys.version_info >= (3, 9) else None)
    teams = [a for a in ("Microsoft Teams.app", "Microsoft Teams (work or school).app", "Microsoft Teams classic.app") if os.path.isdir(os.path.join("/Applications", a))]
    return dict(_MAC, disk_gb=round(shutil.disk_usage(EV).free / 2 ** 30), chrome=os.path.isdir("/Applications/Google Chrome.app"), teams_uygulama=bool(teams))

# ---------- Claude Code ----------
CLAUDE = {"giris": None, "surum": None, "t": 0, "neden": None, "yol": None, "yol_t": 0, "kabuk_yolu": None}
def claude_yolu():
    # eski yerel kurulum (~/.claude/local) ve npm yolları da; hiçbiri yoksa kullanıcının kabuğuna sorulur
    for p in (shutil.which("claude"), os.path.join(EV, ".local/bin/claude"), os.path.join(EV, ".claude/local/claude"), "/opt/homebrew/bin/claude",
              "/usr/local/bin/claude", os.path.join(EV, ".npm-global/bin/claude")):
        if p and os.path.exists(p): return p
    if not DENEME and CLAUDE.get("kabuk_yolu") is None:
        v = sh(kabuk_rc()[1], "-lic", "command -v claude", zaman=10).splitlines()
        CLAUDE["kabuk_yolu"] = v[-1].strip() if v and os.path.isabs(v[-1].strip()) and os.path.exists(v[-1].strip()) else ""
    return CLAUDE.get("kabuk_yolu") or None
# (kişisel hesap kurulumu, 5 Ekim) Claude'un kurulum betiği ~/.local/bin'i Terminal'in arama yoluna eklemiyor — sihirbaz
# programı tam yolundan bulup "kurulu" diyordu, Terminal'de `claude` "command not found" veriyordu. Kullanıcının kabuğu sorulur.
def kabuk_rc():
    k = os.path.basename(os.environ.get("SHELL") or "/bin/zsh")
    return os.path.join(EV, ".bash_profile" if k == "bash" else ".zshrc"), ("/bin/bash" if k == "bash" else "/bin/zsh")
def terminalde_var():
    if time.time() - CLAUDE["yol_t"] > 60 or CLAUDE["yol"] is None:
        ort = dict(os.environ, HOME=EV, ZDOTDIR=EV) if DENEME else None  # deneme: kabuk deneme ev klasörünün .zshrc'sini okur
        try: v = subprocess.run([kabuk_rc()[1], "-lic", "command -v claude"], capture_output=True, text=True, timeout=10, env=ort, stdin=subprocess.DEVNULL).stdout.strip()
        except Exception: v = ""
        CLAUDE.update(yol=bool(v), yol_t=time.time())
    return CLAUDE["yol"]
YOL_SATIRI = 'export PATH="$HOME/.local/bin:$PATH"  # Suflor.me kurulumu: Claude Code komutu'
def yola_ekle():
    rc = kabuk_rc()[0]
    try: eski = open(rc, encoding="utf-8").read()
    except OSError: eski = ""
    if YOL_SATIRI not in eski:
        with open(rc, "a", encoding="utf-8") as f: f.write(("" if not eski or eski.endswith("\n") else "\n") + YOL_SATIRI + "\n")
    CLAUDE["yol"] = None
def claude_durum():
    p = claude_yolu()
    if p and (not CLAUDE["surum"] or time.time() - CLAUDE["t"] > 60): CLAUDE.update(surum=(sh(p, "--version", zaman=15).split() or [None])[0], t=time.time())
    if CLAUDE["giris"] is None: k = oku_json(KAYIT); CLAUDE.update(giris=k.get("claude_giris"), neden=k.get("claude_neden"))
    return {"kurulu": bool(p), "surum": CLAUDE["surum"] if p else None, "giris": CLAUDE["giris"], "neden": CLAUDE["neden"],
            "yolda": terminalde_var() if p else None}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
def claude_denetle():
    # başarısızlığın nedeni saklanır ve sihirbazda gösterilir (önceden yalnız "oturum açılmamış ya da denetlenmedi")
    p = claude_yolu(); neden = None
    if not p: CLAUDE.update(giris=False, neden={"tur": "yok"}); return
    try:
        r = subprocess.run([p, "-p", "Yalnız TAMAM yaz."], capture_output=True, text=True, timeout=90, cwd=tempfile.gettempdir(), stdin=subprocess.DEVNULL)
        ok = r.returncode == 0 and "TAMAM" in r.stdout.upper()
        if not ok:
            satirlar = [x.strip() for x in _ANSI.sub("", (r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if x.strip()]
            ham = " · ".join(satirlar[-2:])[:240] or f"çıkış kodu {r.returncode}"
            abone = re.search(r"credit balance|subscription|usage limit|quota|billing|plan does not|upgrade", ham, re.I)
            giris = re.search(r"log ?in|/login|not logged|authenticat|api key|oauth|credential|unauthori", ham, re.I)
            neden = {"tur": "abonelik" if abone else "giris" if giris else "hata", "ham": ham}
    except subprocess.TimeoutExpired: ok = False; neden = {"tur": "zaman"}
    except Exception as e: ok = False; neden = {"tur": "hata", "ham": str(e)[:240]}
    CLAUDE.update(giris=ok, neden=neden)
    k = oku_json(KAYIT); k["claude_giris"] = ok; k["claude_neden"] = neden; yaz_json(KAYIT, k)  # sunucu yeniden başlasa da hatırlansın

# ---------- modeller (arka planda modeller-kur.command) ----------
MODEL = {"durum": None, "yuzde": 0, "mesaj": "", "p": None}
GEREKEN_GB = 3.3
def modeller_hazir():
    return (os.path.exists(f"{ORTAK}/whisper-venv/bin/python") and os.path.isdir(f"{ORTAK}/whisper-modeller/hub") and
            os.path.exists(f"{ORTAK}/ses-modeller/spkrec-ecapa-voxceleb/ecapa-mlx.npz"))  # ses-venv yok
def _boyut(yol):
    n = 0
    for k, _, fs in os.walk(yol):
        for f in fs:
            try: n += os.lstat(os.path.join(k, f)).st_size
            except OSError: pass
    return n
_BOY = {"t": 0, "gb": 0}
def _gunluk_son():
    try: sat = [x.strip() for x in open(os.path.join(DESTEK, "modeller-kur.log"), encoding="utf-8", errors="replace").read().splitlines()[-40:] if x.strip()]
    except OSError: return ""
    son = [x for x in sat if re.search(r"hata|error|uyarı|not:|gerekli|failed|denied|no space", x, re.I)] or sat
    return son[-1][:200] if son else ""
def modeller_durum():
    if modeller_hazir(): return {"durum": "hazir", "yuzde": 100}
    # modeller ortak klasörde; başka macOS hesabı kurduysa ve eksikse bu hesap tamamlayamaz (yazma izni yok)
    if os.path.isdir(ORTAK) and not os.access(ORTAK, os.W_OK) and not DENEME:
        return {"durum": "hata", "yuzde": 0, "tur": "baska_hesap", "mesaj": ORTAK}
    if MODEL["p"] is None: return {"durum": "yok", "yuzde": 0}
    if MODEL["p"].poll() is not None and not modeller_hazir():
        return {"durum": "hata", "yuzde": MODEL["yuzde"], "tur": "kurulamadi", "mesaj": _gunluk_son()}
    if time.time() - _BOY["t"] > 5: _BOY.update(t=time.time(), gb=_boyut(ORTAK) / 2 ** 30)
    MODEL["yuzde"] = min(99, round(100 * _BOY["gb"] / GEREKEN_GB)); return {"durum": "iniyor", "yuzde": MODEL["yuzde"]}
def modeller_baslat():
    if modeller_hazir() or (MODEL["p"] and MODEL["p"].poll() is None): return  # biten (hatalı) işlem varsa yeniden başlatılır
    if DENEME: return
    os.makedirs(DESTEK, exist_ok=True)
    MODEL["p"] = subprocess.Popen([PY, "-u", os.path.abspath(__file__), "modeller"], stdout=open(os.path.join(DESTEK, "modeller-kur.log"), "a"),
                                  stderr=subprocess.STDOUT, start_new_session=True)

# ---------- aktarıcı (kurulduysa) ----------
# v0.14.0 yerel anahtar: aktarıcının okuma uçları anahtar ister — bu hesabın aktarıcısına (ayardaki port) giden her isteğe başlık.
# Başka porttaki aktarıcıya (aynı Mac'te diğer hesap) anahtar gitmez; yoklama orada yalnız "yanıt var mı"ya bakar (401 de yanıttır).
def _anahtar():
    try: return open(os.path.join(yollar()["uygulama"], "canli", "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
class _AnahtarEkle(urllib.request.BaseHandler):
    def http_request(self, r):
        if r.full_url.startswith(f"http://127.0.0.1:{yollar()['port']}/") and not r.has_header("X-suflor-anahtar"): r.add_header("X-Suflor-Anahtar", _anahtar())
        return r
urllib.request.install_opener(urllib.request.build_opener(_AnahtarEkle()))
def _yanit_var(url, sn):
    try: urllib.request.urlopen(url, timeout=sn); return True
    except urllib.error.HTTPError: return True  # 401/403: aktarıcı orada
    except Exception: return False
def aktarici(yol):
    port = ayar().get("port")
    if not port: return None
    try: return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}{yol}", timeout=2))
    except Exception: return None
def eklenti():
    # önceden yalnız Teams sekmesindeki eklentinin nabzı sayılıyordu — Teams açık değilse sihirbaz bu adımda bekleyip kalıyordu.
    # Eklentinin arka planı aktarıcıyı dakikada bir (ve yüklenince hemen) yoklar; aktarıcı bunu "eklenti_kurulu" olarak tutar.
    s = aktarici("/status") or {}; x = s.get("extension") or {}; k = s.get("eklenti_kurulu") or {}
    nabiz = x.get("age_s") is not None and x["age_s"] < 30; arka = k.get("age_s") is not None and k["age_s"] < 90
    # bu Mac'te başka hesabın aktarıcısı da çalışıyorsa eklenti hangisine yazacağını sorar (Suflor.me simgesi → alan seç)
    coklu = sum(1 for p in range(8765, 8769) if p != ayar().get("port") and _acik(p)) > 0 if s else False
    return {"bagli": nabiz or arka, "surum": (x.get("ver") if nabiz else k.get("ver")) if (nabiz or arka) else None, "coklu": coklu, "alan": s.get("alan")}
def _acik(p): return _yanit_var(f"http://127.0.0.1:{p}/status", 0.6)
def yerel_ses():  # karşı ses yardımcısı kuruldu mu (kur adımında gösterilir)
    s = aktarici("/status") or {}; y = s.get("yerel_ses") or {}
    return {"kurulu": bool(y.get("kurulu")), "durum": y.get("durum")} if s else None
def takvim():
    t = aktarici("/takvim")
    if not t: return {"durum": "kurulmadi"}
    a = ayar(); tj = oku_json(os.path.join(gen(a.get("uygulama") or "~/Library/Application Support/Suflor"), "takvim.json"))
    tk = {}
    for e in tj.get("olaylar", []):
        if e.get("takvim"): tk[f'{e["takvim"]} · {e.get("hesap") or ""}'] = {"ad": e["takvim"], "hesap": e.get("hesap") or ""}
    return {"durum": t.get("durum"), "takvimler": list(tk.values()), "adaylar": takvim_adaylari(a) if t.get("durum") == "ok" else [],
            "adresler": a.get("takvim_adreslerim"), "olaylar": [{"saat": o["saat"], "bitis": o["bitis_saat"], "baslik": o["baslik"], "platform": o.get("platform")} for o in t.get("olaylar", [])]}

# Takvim adresleri: Takvim'e başkalarının paylaşılan takvimleri de eklenebiliyor ve macOS orada takvim sahibini "sen" sayıyor; aktarıcı
# yalnız kullanıcının adreslerinin davetli/düzenleyen olduğu toplantıları gösterir (ayar takvim_adreslerim). Adaylar takvim
# yardımcısından (--adaylar, son ve gelecek 30 gün) arka planda bir kez alınır; sihirbaz durum yoklaması beklemesin.
_ADAY = {"liste": None, "is": None}
def takvim_adaylari(a):
    if _ADAY["liste"] is not None or DENEME: return _ADAY["liste"] or []
    if _ADAY["is"] is None:
        def al():
            uyg = os.path.join(gen(a.get("uygulama") or "~/Library/Application Support/Suflor"), "Suflor Takvim.app")
            cikti = os.path.join(tempfile.gettempdir(), f"suflor-takvim-aday-{os.getuid()}.json")
            try:
                subprocess.run(["open", "-g", "-W", "-a", uyg, "--args", "--cikti", cikti, "--once", "720", "--sonra", "720", "--adaylar"], timeout=90, capture_output=True)
                j = oku_json(cikti); os.remove(cikti)
            except Exception: j = {}
            _ADAY["liste"] = [{k: x.get(k) for k in ("adres", "ad", "takvim", "hesap", "sayi")} for x in j.get("adaylar") or [] if "@" in str(x.get("adres"))]
        _ADAY["is"] = threading.Thread(target=al, daemon=True); _ADAY["is"].start()
    return None  # henüz alınmadı
def takvim_ayarla(adresler, cikar):  # takvim ekranı kurulumdan sonra: ayara yaz, aktarıcı yeniden okusun (takvimi yeniden okur)
    a = ayar()
    if not a: return {"ok": False}
    ad = [str(x).strip().lower() for x in adresler or [] if re.fullmatch(r"[^\s@,]+@[^\s@,]+\.[^\s@,]+", str(x).strip())]
    a["takvim_adreslerim"] = list(dict.fromkeys(ad)); a["takvim_haric"] = [str(x) for x in cikar or []]; yaz_json(AYAR_YOL, a)
    if not DENEME: sessiz("launchctl", "kickstart", "-k", f"{gui()}/{LABEL}")
    return {"ok": True}

# ---------- profil: Claude'un çalışma notu (taslak) ----------
# Sihirbaz 17 → 10 ekran (8 Ekim): ayrı "Seni böyle tanıdım" ekranı yok. Kurulum bitince bağımsız süreç (`kurulum.py profil`,
# sihirbaz kapansa da sürer) proje klasöründeki dökümlerden ve profil alanlarından notu yazar: CLAUDE.md'ye "(taslak)" başlıkla;
# ilk toplantının sonunda /toplanti kullanıcıya gösterip onay ister. Terimler ayarın whisper_terimler'ine eklenir (aktarıcı
# yeniden başlayınca, ör. güncellemede, ipucuna girer).
PROFIL_ISTEM = {"tr": """Sen Suflor.me'nin kurulum yardımcısısın. Suflor.me, kullanıcının toplantılarını canlı izleyip ona kısa kartlarla ne
sorması, neyi belirtmesi gerektiğini söyleyen bir asistan. Aşağıda kullanıcının kurulumda verdiği bilgiler ve varsa geçmiş görüşme
dökümlerinin yolları var (Read ile oku). Bunlardan kullanıcı için bir "çalışma notu" çıkar: kim olduğu, rolü, toplantı türleri,
kartlarda neye öncelik verilmesi ve neyle rahatsız edilmemesi gerektiği. 120–220 kelime, düz Türkçe, madde değil kısa paragraflar;
uydurma bilgi yazma, bilmediğini yazma. Ayrıca konuşma tanımanın doğru yazması gereken özel adları ve terimleri (kişi adları,
sistem ve ürün adları, kısaltmalar) en çok 30 tane çıkar; genel kelimeleri (tedarikçi, stok, fatura gibi) ve Suflor.me'yi yazma.
Yalnız şu JSON'u yaz, başka hiçbir şey yazma: {"not": "...", "terimler": ["...", "..."]}""",
               "en": """You are Suflor.me's setup assistant. Suflor.me follows the user's meetings live and tells them in short cards what to ask
and what to point out. Below is what the user gave during setup and, if any, paths to past meeting transcripts (read them with Read).
Write a "working note" about the user: who they are, their role, their meetings, what cards should prioritise and what should not
interrupt them. 120–220 words, plain English, short paragraphs, no invented facts, leave out what you don't know. Also list up to 30
special names and terms speech recognition must spell correctly (people, systems, products, acronyms); leave out common words
(supplier, stock, invoice) and Suflor.me.
Output only this JSON and nothing else: {"not": "...", "terimler": ["...", "..."]}"""}
PROFIL_BASLIK = {"tr": "## Ben ve işim", "en": "## About me and my work"}
def profil_gerekli(c):  # yalnız adla not yazılmaz (uydurmaya iter); döküm ya da bir profil alanı gerekir
    return not c.get("kartsiz") and (bool(c.get("gorusmeler")) or any(c.get(k) for k in ("rol", "is_alani", "araclar_ek", "kisiler")))
def profil():  # komut satırı: kurulum.py profil — kurulum.json'daki cevaplar + proje/gorusmeler → CLAUDE.md taslak notu
    a = ayar(); k = oku_json(KAYIT); c = k.get("cevap") or {}; dil = a.get("dil") or k.get("dil") or "tr"; cl = claude_yolu()
    proje = gen(a.get("proje") or "~/Suflor"); cm = os.path.join(proje, "CLAUDE.md")
    if not cl or not os.path.isfile(cm) or not profil_gerekli(c): say("profil: gerek yok ya da Claude/CLAUDE.md yok"); return
    if PROFIL_BASLIK[dil] in open(cm, encoding="utf-8").read(): say("profil: not zaten var"); return
    ornek = {os.path.basename(f) for f in glob_ornek(dil)}; gd = os.path.join(proje, "gorusmeler")
    dosyalar = [os.path.join(gd, f) for f in sorted(os.listdir(gd)) if f in set(c.get("gorusmeler") or []) and f not in ornek][:5] if os.path.isdir(gd) else []
    alanlar = {x: c.get(x) for x in ("ad", "rol", "sirket", "is_alani", "araclar_ek", "kisiler") if c.get(x)}
    istem = PROFIL_ISTEM[dil] + "\n\nBİLGİLER:\n" + json.dumps(alanlar, ensure_ascii=False, indent=1) + ("\n\nDOSYALAR:\n" + "\n".join(dosyalar) if dosyalar else "")
    try:
        r = subprocess.run([cl, "-p", istem, "--allowedTools", "Read", "--add-dir", gd], capture_output=True, text=True, timeout=300, cwd=proje)
        m = re.search(r"\{.*\}", r.stdout, re.S); j = json.loads(m.group(0)) if m else {}
    except Exception as e: say(f"profil: Claude çağrısı başarısız ({e.__class__.__name__})"); return
    metin = str(j.get("not") or "").strip()
    terimler = [str(x)[:60] for x in (j.get("terimler") or []) if not str(x).lower().startswith("suflor")][:30]
    if not metin: say("profil: Claude not döndürmedi"); return
    s = open(cm, encoding="utf-8").read()
    if PROFIL_BASLIK[dil] in s: return  # bu arada kullanıcı yazdıysa dokunma
    bugun = datetime.date.today().isoformat()
    s = s.rstrip() + f"\n\n{PROFIL_BASLIK[dil]} " + ("(taslak)\n" if dil == "tr" else "(draft)\n") + \
        (f"_Kurulumda Claude hazırladı ({bugun}). İlk toplantının sonunda onaylanınca başlıktaki \"(taslak)\" silinir; istediğin zaman düzenleyebilirsin._\n\n" if dil == "tr" else
         f"_Drafted by Claude during setup ({bugun}). Once you approve it after your first meeting, \"(draft)\" is removed from the heading; edit it any time._\n\n") + metin + "\n"
    kisiler = [x.strip() for x in str(c.get("kisiler") or "").split(",") if x.strip()]
    if kisiler: s += ("\nSık görüştüğüm kişiler: " if dil == "tr" else "\nPeople I meet often: ") + ", ".join(kisiler) + "\n"
    open(cm, "w", encoding="utf-8").write(s)
    if terimler: a = ayar(); a["whisper_terimler"] = list(dict.fromkeys((a.get("whisper_terimler") or []) + terimler))[:60]; yaz_json(AYAR_YOL, a)
    say(f"profil: taslak not yazıldı ({len(metin.split())} kelime, {len(terimler)} terim)")
def teshis_ayarla(acik):  # Kuruyorum ekranındaki anahtar kurulumdan sonra değişirse: ayara yaz, aktarıcı yeniden okusun
    a = ayar()
    if not a or a.get("teshis") is (acik is True): return {"ok": True}
    a["teshis"] = acik is True; yaz_json(AYAR_YOL, a)
    if not DENEME: sessiz("launchctl", "kickstart", "-k", f"{gui()}/{LABEL}")
    return {"ok": True}

# ---------- son kurulum ----------
def bos_port():
    for p in range(8765, 8770):
        if not _yanit_var(f"http://127.0.0.1:{p}/status", 1): return p
    return 8770
def tamamla(c, dil):
    sonuc = {"ayar": "bekle", "proje": "bekle", "not": "bekle", "aktarici": "bekle"}
    eski = ayar(); proje = gen(c.get("proje") or "~/Suflor")
    terim_cikar = set(c.get("terim_cikar") or [])
    terimler = [x for x in (c.get("terimler") or []) if x not in terim_cikar]
    araclar = list(dict.fromkeys((c.get("araclar") or []) + [x.strip() for x in str(c.get("araclar_ek") or "").split(",") if x.strip()]))
    kisiler = [x.strip() for x in str(c.get("kisiler") or "").split(",") if x.strip()]
    a = dict(eski)
    a.update({"alan": eski.get("alan") or (c.get("sirket") or "Kişisel"), "ad": c.get("ad") or eski.get("ad") or "", "port": eski.get("port") or bos_port(),
              "uygulama": eski.get("uygulama") or "~/Library/Application Support/Suflor", "proje": proje, "ortak": ORTAK, "kod": KOD, "dil": dil,
              "komut_sablondan": eski.get("komut_sablondan", True), "durum_belgesi": eski.get("durum_belgesi") or "belgeler/DURUM.md",
              "rol": c.get("rol") or "", "sirket": c.get("sirket") or "", "is_alani": c.get("is_alani") or "", "kartsiz": bool(c.get("kartsiz")),
              "ek_sistem": list(dict.fromkeys((eski.get("ek_sistem") or []) + araclar)),
              "whisper_terimler": list(dict.fromkeys((eski.get("whisper_terimler") or []) + araclar + kisiler + terimler))[:60],
              "takvim_haric": [x for x in (c.get("takvim_cikar") or [])], "takvim_adreslerim": [x for x in (c.get("takvim_adres") or eski.get("takvim_adreslerim") or [])],
              "teshis": c.get("teshis") is True})  # beta teşhis izni (teshis.py; adres teshis_adres ya da varsayılan)
    a.setdefault("claude_model", "sonnet")
    if claude_yolu() and not a.get("claude"): a["claude"] = claude_yolu()  # aktarıcı panodan başlatırken aynı Claude
    try: yaz_json(AYAR_YOL, a); sonuc["ayar"] = "iyi"
    except Exception as e: sonuc.update(ayar="kotu", hata=f"Ayar yazılamadı: {e}"); return sonuc
    try:
        for k in ("belgeler", "gorusmeler", "_kanit", "_arsiv", ".claude/commands"): os.makedirs(os.path.join(proje, k), exist_ok=True)
        dold = {"{{ALAN}}": a["alan"], "{{AD}}": a["ad"], "{{PORT}}": str(a["port"]), "{{PROJE}}": proje, "{{KOD}}": KOD}
        def doldur(kaynak, hedef):
            s = open(os.path.join(KOD, "sablon", kaynak), encoding="utf-8").read()
            for k, v in dold.items(): s = s.replace(k, v)
            open(hedef, "w", encoding="utf-8").write(s)
        if not os.path.exists(os.path.join(proje, "CLAUDE.md")): doldur("CLAUDE.md", os.path.join(proje, "CLAUDE.md"))
        doldur("toplanti.md", os.path.join(proje, ".claude", "commands", "toplanti.md"))
        g = os.path.join(YUKLEME, "gorusmeler")
        if os.path.isdir(g):
            for f in os.listdir(g): shutil.copy2(os.path.join(g, f), os.path.join(proje, "gorusmeler", f))
        if c.get("ornek"):
            for f in glob_ornek(dil): shutil.copy2(f, os.path.join(proje, "gorusmeler", os.path.basename(f)))
        sonuc["proje"] = "iyi"
    except Exception as e: sonuc.update(proje="kotu", hata=f"Proje klasörü kurulamadı: {e}"); return sonuc
    # çalışma notu: bağımsız süreçte (sihirbaz kapansa da sürer); kurulum.json bu çağrıdan önce kaydedildi
    sonuc["not"] = "bos"
    if profil_gerekli(c) and claude_yolu() and (not DENEME or os.environ.get("SUFLOR_PROFIL_DENE")):
        yaz_json(KAYIT, dict(oku_json(KAYIT), cevap=c, dil=dil))
        subprocess.Popen([PY, os.path.abspath(__file__), "profil"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True); sonuc["not"] = "iyi"
    if DENEME: sonuc["aktarici"] = "iyi"; return sonuc
    r = subprocess.run([PY, os.path.abspath(__file__), "kur"], capture_output=True, text=True, timeout=300)
    sonuc["aktarici"] = "iyi" if r.returncode == 0 else "kotu"
    sonuc["uyarilar"] = [x.strip()[:220] for x in (r.stdout + r.stderr).splitlines() if x.strip().startswith("UYARI")][:4]
    if r.returncode: sonuc["hata"] = "Arka plan hizmeti kurulamadı: " + (r.stdout + r.stderr).strip().splitlines()[-1][:200] if (r.stdout + r.stderr).strip() else "bilinmeyen hata"
    return sonuc
def glob_ornek(dil):
    d = os.path.join(KOD, "ornekler"); return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(f"-{dil}.md")] if os.path.isdir(d) else []

# ---------- dış uygulamalar ----------
def ac(hedef):
    a = ayar()
    if hedef == "python": subprocess.Popen(["xcode-select", "--install"])
    elif hedef == "chrome-indir": subprocess.Popen(["open", "https://www.google.com/chrome/"])
    elif hedef == "claude-kur":
        f = os.path.join(tempfile.gettempdir(), "suflor-claude-kur.command")
        open(f, "w").write("#!/bin/bash\necho 'Suflor.me — Claude Code kuruluyor…'\ncurl -fsSL https://claude.ai/install.sh | bash\n"
                           "echo; echo 'Şimdi Claude açılıyor: hesabınla giriş yap, sonra bu pencereyi kapatıp kuruluma dön.'\n"
                           "\"$HOME/.local/bin/claude\" || claude\n")
        os.chmod(f, 0o755); yola_ekle(); subprocess.Popen(["open", "-a", "Terminal", f])
    elif hedef == "claude-yol": yola_ekle()
    elif hedef == "claude-giris" and claude_yolu():  # Claude'u tam yoluyla Terminal'de açar. v0.13.5: adımlar sihirbazın dilinde
        en = oku_json(KAYIT).get("dil") == "en"
        yonerge = ("Suflor.me — signing in to Claude Code\n  1. Claude opens below. If it asks you to sign in, follow the prompts;\n     if it doesn't, type /login and press Return.\n"
                   "  2. Sign in with the account that has your Claude subscription (Pro or higher).\n  3. When it says you're signed in, type /exit.\n"
                   "  4. Go back to the setup wizard; it checks again by itself.\n  Note: being signed in to the Claude desktop app doesn't count — Terminal needs its own sign-in.") if en else \
                  ("Suflor.me — Claude Code'a giriş\n  1. Aşağıda Claude açılıyor. Giriş isterse yönergeyi izle;\n     istemezse /login yazıp Return'e bas.\n"
                   "  2. Claude aboneliğinin olduğu hesapla (Pro ya da üstü) giriş yap.\n  3. Girişin tamamlandığını görünce /exit yaz.\n"
                   "  4. Kurulum sihirbazına dön; kendisi yeniden denetler.\n  Not: Claude masaüstü uygulamasındaki giriş sayılmaz — Terminal'in kendi girişi gerekir.")
        f = os.path.join(tempfile.gettempdir(), "suflor-claude-giris.command")
        open(f, "w").write("#!/bin/bash\ncat <<'YONERGE'\n" + yonerge + "\nYONERGE\necho\n" + f"exec {shlex.quote(claude_yolu())}\n")
        os.chmod(f, 0o755); subprocess.Popen(["open", "-a", "Terminal", f])
    elif hedef == "takvim-izin":
        uyg = os.path.join(gen(a.get("uygulama") or "~/Library/Application Support/Suflor"), "Suflor Takvim.app")
        if os.path.isdir(uyg): subprocess.run(["open", "-W", "-a", uyg, "--args", "--cikti", os.path.join(os.path.dirname(uyg), "takvim.json")], timeout=150)
        try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{a.get('port')}/takvim-yenile", data=b"{}", method="POST"), timeout=3); time.sleep(4)
        except Exception: pass
    elif hedef == "ses-izni": subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AudioCapture"])
    elif hedef == "internet-hesaplari": subprocess.Popen(["open", "x-apple.systempreferences:com.apple.Internet-Accounts-Settings.extension"])
    elif hedef == "teams-dene": subprocess.Popen(["open", "-a", "Google Chrome", "https://teams.microsoft.com/v2/"])
    elif hedef == "chrome-eklentiler": subprocess.Popen(["open", "-a", "Google Chrome", "chrome://extensions"])
    elif hedef == "eklenti-klasoru": subprocess.Popen(["open", "-R", os.path.join(KOD, "manifest.json")])
    elif hedef == "pano" and a.get("port"):
        # pano yerel anahtarı kendi deposuna alır: aktarıcıdan tek kullanımlık adres (anahtar komut satırına yazılmaz)
        try: url = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{a['port']}/tek-kullanim", data=b"{}", method="POST"), timeout=3))["url"]
        except Exception: url = f"http://127.0.0.1:{a['port']}/"
        subprocess.Popen(["open"] + (["-a", "Google Chrome"] if os.path.isdir("/Applications/Google Chrome.app") else []) + [url])  # pano Chrome'da; threading.Timer(3, lambda: os._exit(0)).start()
def klasor_sec():
    r = sh("osascript", "-e", 'POSIX path of (choose folder with prompt "Suflor.me proje klasörü")', zaman=300)
    return r.rstrip("/") if r else None

# ---------- sunucu ----------
STATIK = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
          ".svg": "image/svg+xml", ".woff2": "font/woff2", ".png": "image/png"}
# yerel anahtar. 127.0.0.1 bu Mac'teki her kullanıcıya ve programa açık; Origin/Host denetimi tarayıcıyı durdurur ama
# curl'ü durdurmaz (5 Ekim: diğer macOS hesabından kurulum durumu okunabildi). Sihirbazı açan süreç (kurulum.py --ac, bu kullanıcı)
# adresi ?k=<anahtar> ile açar; sunucu anahtarı HttpOnly çereze koyup temiz adrese yönlendirir. /api/* ve sayfa çerez ister.
ANAHTAR = secrets.token_urlsafe(24); CEREZ = "suflor_kurulum"
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _cerezli(self):
        for p in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = p.strip().partition("=")
            if k == CEREZ and secrets.compare_digest(v, ANAHTAR): return True
        return False
    def _kapali(self):
        b = ("<!doctype html><meta charset=utf-8><title>Suflor.me</title><body style='font:15px/1.5 -apple-system,system-ui;max-width:520px;margin:15vh auto;padding:0 16px'>"
             "<h2 style='font-weight:400'>Suflor.me kurulum sihirbazı</h2><p>Bu sayfa yalnız sihirbazı başlatan bağlantıyla açılır. Kaldığın adımdan sürdürmek için "
             "kurulum komutunu Terminal'de yeniden çalıştır:</p><pre style='white-space:pre-wrap;background:#f1f1ee;padding:10px;border-radius:8px'>"
             "curl -fsSL https://raw.githubusercontent.com/suflorme/suflor/main/kur.sh | bash</pre>"
             "<p style='color:#777'>To continue the setup wizard, run the install command above in Terminal again.</p>").encode()
        self.send_response(403); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _json(self, o, kod=200):
        b = json.dumps(o, ensure_ascii=False).encode(); self.send_response(kod); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _kaynak(self):
        o = self.headers.get("Origin") or self.headers.get("Referer") or ""
        return not o or o.startswith((f"http://127.0.0.1:{A.port}", f"http://localhost:{A.port}"))
    def _host(self):
        # (güvenlik denetimi D6) DNS rebinding — başka alan adı 127.0.0.1'e çözülse de Host başlığı o alan adı olur
        return (self.headers.get("Host") or "").lower() in (f"127.0.0.1:{A.port}", f"localhost:{A.port}")
    def do_GET(self):
        if not self._host(): return self._json({"hata": "host"}, 403)
        yol, _, sorgu = self.path.partition("?")
        if yol in ("/", "/index.html", "/sihirbaz/index.html"):
            k = dict(x.split("=", 1) for x in sorgu.split("&") if "=" in x).get("k")
            if k and secrets.compare_digest(k, ANAHTAR):  # açılış bağlantısı: çerez + temiz adres (anahtar geçmişte kalmasın)
                self.send_response(302); self.send_header("Set-Cookie", f"{CEREZ}={ANAHTAR}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400")
                self.send_header("Location", "/" + ("?" + "&".join(x for x in sorgu.split("&") if not x.startswith("k=")) if "&" in sorgu else "")); self.end_headers(); return
            if not self._cerezli(): return self._kapali()
        elif yol.startswith("/api/") and not self._cerezli(): return self._json({"hata": "anahtar"}, 403)
        if yol == "/api/durum":
            a = ayar()
            return self._json({"mac": mac(), "claude": claude_durum(), "modeller": modeller_durum(), "eklenti": eklenti(), "takvim": takvim(), "yerel_ses": yerel_ses(),
                               "kod": KOD, "proje": a.get("proje") or "~/Suflor", "varsayilan_ad": a.get("ad") or sh("id", "-F") or getpass.getuser(), "deneme": DENEME})
        if yol == "/api/kayit": return self._json(oku_json(KAYIT))
        if yol in ("/", "/index.html"): yol = "/sihirbaz/index.html"
        if yol.startswith(("/sihirbaz/", "/marka/")):
            f = os.path.realpath(os.path.join(KOD, yol.lstrip("/")))
            if f.startswith(KOD + os.sep) and os.path.isfile(f) and os.path.splitext(f)[1] in STATIK:
                b = open(f, "rb").read(); self.send_response(200); self.send_header("Content-Type", STATIK[os.path.splitext(f)[1]])
                self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b); return
        self._json({"hata": "yok"}, 404)
    def do_POST(self):
        if not self._host(): return self._json({"hata": "host"}, 403)
        if not self._kaynak(): return self._json({"hata": "köken"}, 403)  # yalnız sihirbaz sayfası
        if not self._cerezli(): return self._json({"hata": "anahtar"}, 403)
        yol, _, sorgu = self.path.partition("?"); n = int(self.headers.get("Content-Length") or 0); govde = self.rfile.read(n) if n else b""
        if yol == "/api/yukle":
            q = dict(x.split("=", 1) for x in sorgu.split("&") if "=" in x); tur = q.get("tur"); ad = os.path.basename(urllib.request.unquote(q.get("ad") or "dosya"))
            if tur not in ("gorusme", "linkedin") or not ad or len(govde) > 30 * 2 ** 20: return self._json({"hata": "dosya"}, 400)
            d = os.path.join(YUKLEME, "gorusmeler" if tur == "gorusme" else "linkedin"); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, ad), "wb").write(govde); return self._json({"ok": True})
        p = json.loads(govde or b"{}")
        if yol == "/api/kaydet": yaz_json(KAYIT, dict(oku_json(KAYIT), dil=p.get("dil"), adim=p.get("adim"), cevap=p.get("cevap") or {}, t=time.time())); return self._json({"ok": True})
        if yol == "/api/modeller/baslat": modeller_baslat(); return self._json(modeller_durum())
        if yol == "/api/claude/denetle": claude_denetle(); return self._json(claude_durum())
        if yol == "/api/teshis": return self._json(teshis_ayarla(p.get("acik")))
        if yol == "/api/takvim": return self._json(takvim_ayarla(p.get("adresler"), p.get("cikar")))
        if yol == "/api/kur/tamamla": return self._json(tamamla(p.get("cevap") or {}, p.get("dil") or "tr"))
        if yol == "/api/klasor-sec": return self._json({"yol": klasor_sec()})
        if yol == "/api/ac": ac(str(p.get("hedef") or "")); return self._json({"ok": True})
        self._json({"hata": "yok"}, 404)

# ---------- kur / kaldir / modeller / guncelle (komut satırı) ----------
# macOS, launchd'nin başlattığı programların Masaüstü'ne erişimini engeller: aktarıcı ve veri klasörü ~/Library/Application
# Support/Suflor (ayar: uygulama) altında durur, proje klasöründeki _canli oraya kısayoldur. Aktarıcının yanına kopyalanan her
# şey KOPYA'da (tek liste; yeni bir dosya aktarıcıya gerekiyorsa yalnız buraya eklenir).
LABEL = "local.suflor.aktarici"
KOPYA = ["relay.py", "aktarici/", "manifest.json", "whisper-isci.py", "toplanti-claude.py", "teshis.py", "pano/", "marka/*.svg", "marka/yazi/*.woff2"]
KALKAN = ["ses-isci.py"]  # eski kurulumdan kalan; uygulama klasöründen silinir (ses izi Whisper işçisinde)
ESKI_BETIK = ["kur.command", "relay-baslat.command"]  # tek kurulum komutuyla kalktı; açık depodan güncellemede kod klasöründen silinir
TAKVIM_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>local.suflor.takvim</string><key>CFBundleName</key><string>Suflor Takvim</string>
  <key>CFBundleExecutable</key><string>SuflorTakvim</string><key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string><key>LSUIElement</key><true/>
  <key>NSCalendarsFullAccessUsageDescription</key><string>Suflor.me bugünkü toplantılarını bulmak, gündemini ve katılımcılarını toplantı asistanına vermek için takvimini okur. Hiçbir şey değiştirmez, bu Mac dışına göndermez.</string>
  <key>NSCalendarsUsageDescription</key><string>Suflor.me bugünkü toplantılarını bulmak için takvimini okur. Hiçbir şey değiştirmez.</string>
</dict></plist>
"""
SES_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>local.suflor.ses</string><key>CFBundleName</key><string>Suflor Ses</string>
  <key>CFBundleExecutable</key><string>SuflorSes</string><key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.13.0</string><key>LSUIElement</key><true/><key>LSMinimumSystemVersion</key><string>14.4</string>
  <key>NSAudioCaptureUsageDescription</key><string>Suflor.me toplantıdaki karşı tarafın sesini yazıya dökmek için toplantı uygulamasının sesini alır. Ses kaydedilmez, bu Mac dışına gönderilmez.</string>
</dict></plist>
"""
BRIFING_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>local.suflor.brifing</string><key>CFBundleName</key><string>Suflor Brifing</string>
  <key>CFBundleExecutable</key><string>SuflorBrifing</string><key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string><key>LSUIElement</key><true/>
  <key>NSDesktopFolderUsageDescription</key><string>Suflor.me toplantı öncesi brifingi hazırlarken proje klasöründeki belgeleri ve geçmiş görüşmeleri okur. Hiçbir şey değiştirmez; metin yalnız Claude'a gider.</string>
  <key>NSDocumentsFolderUsageDescription</key><string>Suflor.me toplantı öncesi brifingi hazırlarken proje klasöründeki belgeleri okur. Hiçbir şey değiştirmez; metin yalnız Claude'a gider.</string>
</dict></plist>
"""
def yollar():  # ayar.json'dan; yoksa varsayılanlar
    v = {"port": 8765, "uygulama": "~/Library/Application Support/Suflor", "proje": "~/Suflor", "ortak": ORTAK}; v.update(ayar())
    y = {k: os.path.expanduser(str(v[k])) for k in ("uygulama", "proje", "ortak")}; y["port"] = int(v["port"]); return y
def say(*m): print(*m, flush=True)
def sessiz(*c, **k):  # sonucu önemsiz komut (bash'teki "|| true")
    try: return subprocess.run(list(c), capture_output=True, text=True, **k)
    except Exception: return None
def zorunlu(*c, **k):  # başarısızsa kurulum durur (bash'teki set -e)
    r = subprocess.run(list(c), **k)
    if r.returncode: sys.exit(f"HATA: {os.path.basename(str(c[0]))} başarısız (çıkış {r.returncode})")
    return r
def kopyala(kaynak, hedef):  # cp gibi: var olan dosyanın izinleri korunur, yeni dosya kaynağın izinlerini alır
    var = os.path.exists(hedef); shutil.copyfile(kaynak, hedef)
    if not var: shutil.copymode(kaynak, hedef)
def gui(): return f"gui/{os.getuid()}"
def plist_yolu(): return os.path.join(EV, "Library", "LaunchAgents", LABEL + ".plist")
def aktarici_durdur():  # yalnız bu hesabın aktarıcısı (diğer hesabınki çalışmaya devam eder)
    sessiz("launchctl", "bootout", f"{gui()}/{LABEL}"); sessiz("pkill", "-u", str(os.getuid()), "-f", "relay.py --dir"); time.sleep(1)

def ecapa_donustur(ort, onbellek=True):  # ses izi (ECAPA) ağırlıkları MLX için bir kez; ortak klasör yazılamıyorsa hesabın önbelleğine
    ek = os.path.join(ort, "ses-modeller", "spkrec-ecapa-voxceleb"); vpy = os.path.join(ort, "whisper-venv", "bin", "python")
    cache = os.path.join(EV, "Library", "Caches", "Suflor", "ecapa-mlx.npz")
    if not os.path.isfile(os.path.join(ek, "embedding_model.ckpt")) or os.path.isfile(os.path.join(ek, "ecapa-mlx.npz")): return
    if onbellek and (os.path.isfile(cache) or not os.access(vpy, os.X_OK)): return
    hedef = os.path.join(ek, "ecapa-mlx.npz")
    if onbellek and not os.access(ek, os.W_OK): os.makedirs(os.path.dirname(cache), exist_ok=True); hedef = cache
    r = sessiz(vpy, os.path.join(KOD, "whisper-isci.py"), "--ecapa-donustur", os.path.join(ek, "embedding_model.ckpt"), hedef,
               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if not r or r.returncode:
        say("Not: ses izi ağırlıkları dönüştürülemedi — konuşmacı ayırma kapalı, Whisper çalışır" + (" (modeller-kur.command dener)" if onbellek else ""))
    sessiz("chmod", "go+r", hedef)
def whisper_8bit(ort):  # Whisper turbo'nun 8 bit kopyası yerelde bir kez üretilir (indirme yok, ~1 dk, 824 MB); aktarıcı varsa onu kullanır
    hub = os.path.join(ort, "whisper-modeller", "hub"); t = sorted(glob_(os.path.join(hub, "models--mlx-community--whisper-large-v3-turbo", "snapshots", "*")))
    q8 = os.path.join(hub, "models--suflor--whisper-large-v3-turbo-q8", "snapshots", "yerel")
    if not t or os.path.isfile(os.path.join(q8, "weights.safetensors")) or not os.access(hub, os.W_OK): return
    say("→ Whisper 8 bit modeli hazırlanıyor (bir kez, ~1 dk)…")
    r = sessiz(os.path.join(ort, "whisper-venv", "bin", "python"), os.path.join(KOD, "whisper-isci.py"), "--whisper-nicemle", t[0], q8,
               env=dict(os.environ, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
    if r and r.returncode == 0: sessiz("chmod", "-R", "go+rX", os.path.join(hub, "models--suflor--whisper-large-v3-turbo-q8"))
    else: say("Not: 8 bit model hazırlanamadı — tam model kullanılır")
def glob_(desen):
    import glob; return glob.glob(desen)

def derle(uyg, kaynak, ikili_ad, plist):  # Swift yardımcısı: kaynak ikiliden yeniyse (ya da ikili yoksa) derlenir; True = yeni derlendi
    ikili = os.path.join(uyg, "Contents", "MacOS", ikili_ad); kay = os.path.join(KOD, kaynak)
    if not shutil.which("swiftc"): return False
    if os.access(ikili, os.X_OK) and os.path.getmtime(kay) <= os.path.getmtime(ikili): return False
    os.makedirs(os.path.dirname(ikili), exist_ok=True)
    open(os.path.join(uyg, "Contents", "Info.plist"), "w", encoding="utf-8").write(plist)
    # (güvenlik denetimi D3) derleme günlüğü sabit /tmp yolunda değil, kullanıcının geçici klasöründe benzersiz dosyada
    fd, gunluk = tempfile.mkstemp(prefix=f"suflor-{ikili_ad.lower()}-derleme.")
    with os.fdopen(fd, "w") as g: r = subprocess.run(["swiftc", "-O", "-o", ikili, kay], stdout=subprocess.DEVNULL, stderr=g)
    if r.returncode: return gunluk
    os.remove(gunluk); return True
def yerel_imza():  # yerel-imza.sh (kalıcı yerel imza); kurulamazsa "-" = geçici imza
    r = sessiz("/bin/bash", "-c", '. "$1"; yerel_imza', "_", os.path.join(KOD, "yerel-imza.sh"))
    return (r.stdout.strip() if r else "") or "-"
def imzala(uygulamalar):
    # kalıcı yerel imza — geçici imza her derlemede değişip izni (takvim, ses kaydı) düşürüyordu. Uygulama başka imzayla imzalıysa
    # yeniden imzalanır; kimlik bir kez değişir, sonra hep aynı kalır.
    imza = None
    for u in uygulamalar:
        if not os.path.isdir(os.path.join(u, "Contents", "MacOS")): continue
        imza = imza or yerel_imza()
        m = sessiz("codesign", "-dv", "--verbose=2", u)
        if imza != "-" and m and f"Authority={imza}" in (m.stdout + m.stderr).splitlines(): continue
        r = sessiz("codesign", "-s", imza, "--force", u)
        if r and r.returncode == 0:
            say(f"UYARI: yerel imza kurulamadı — geçici imza; izin her derlemede yeniden istenebilir ({os.path.basename(u)})" if imza == "-" else
                f"{os.path.basename(u)} yerel imzayla imzalandı (izin aynı imzada korunur; ilk kez imzalandıysa macOS bir kez sorar)")

def kaldir():
    sessiz("launchctl", "bootout", f"{gui()}/{LABEL}")
    if os.path.exists(plist_yolu()): os.remove(plist_yolu())
    say(f"Otomatik başlatma kaldırıldı. Veri {os.path.join(yollar()['uygulama'], 'canli')} içinde duruyor (proje klasöründeki _canli kısayolu çalışmaya devam eder).")

def kur():
    if DENEME: sys.exit("Deneme kipinde (SUFLOR_EV) aktarıcı kurulmaz.")
    Y = yollar(); app, port = Y["uygulama"], Y["port"]; canli = os.path.join(app, "canli"); desk = os.path.join(Y["proje"], "_canli")
    # bozuk relay.py kurulursa KeepAlive çöken aktarıcıyı döngüde kaldırmaya çalışır: önce sözdizimi
    import ast
    try: [ast.parse(open(y, encoding="utf-8").read()) for y in [os.path.join(KOD, "relay.py")] + sorted(glob_(os.path.join(KOD, "aktarici", "*.py")))]
    except Exception as e: sys.exit(f"HATA: relay.py sözdizimi hatalı ({e}) — kurulum yapılmadı, çalışan aktarıcı olduğu gibi bırakıldı.")
    for f in ("pano.html", "hazirlik.html", "yazi.css", "dil.js", "anahtar.js"):
        if not os.path.isfile(os.path.join(KOD, "pano", f)): sys.exit(f"HATA: pano/{f} eksik — kurulum yapılmadı, çalışan aktarıcı olduğu gibi bırakıldı.")
    os.makedirs(app, exist_ok=True)
    # geri bildirim raporları için ortak klasör — iki macOS hesabı da yazar (herkes yazar, yapışkan bit: yalnız sahibi siler)
    gb = os.path.join(Y["ortak"], "geri-bildirim")
    try: os.makedirs(gb, exist_ok=True); os.chmod(gb, 0o1777)
    except OSError: pass
    # veri klasörü: proje klasöründe gerçek _canli klasörü varsa bir kez taşı, yerine kısayol bırak
    if os.path.isdir(desk) and not os.path.islink(desk):
        aktarici_durdur()
        if os.path.exists(canli): sys.exit(f"HATA: {canli} zaten var, taşıma yapılmadı.")
        shutil.move(desk, canli); os.symlink(canli, desk); say(f"Veri taşındı: {canli}  (kısayol: {desk})")
    os.makedirs(canli, exist_ok=True)
    # yeni hesapta proje klasöründe _canli kısayolu yoksa kur (Claude geçmiş toplantıları oradan arar)
    if not os.path.lexists(desk) and os.path.isdir(os.path.dirname(desk)): os.symlink(canli, desk); say(f"Kısayol: {desk} → {canli}")
    for k in KOPYA:
        if k.endswith("/"):  # klasör: eski kopya silinip yenisi konur
            shutil.rmtree(os.path.join(app, k), ignore_errors=True)
            shutil.copytree(os.path.join(KOD, k), os.path.join(app, k), copy_function=shutil.copy, ignore=shutil.ignore_patterns(".DS_Store"))
            continue
        for f in (sorted(glob_(os.path.join(KOD, k))) if "*" in k else [os.path.join(KOD, k)]):
            h = os.path.join(app, os.path.relpath(f, KOD)); os.makedirs(os.path.dirname(h), exist_ok=True); kopyala(f, h)
    for k in KALKAN:
        if os.path.isfile(os.path.join(app, k)): os.remove(os.path.join(app, k))
    ecapa_donustur(Y["ortak"]); whisper_8bit(Y["ortak"])
    # beta teşhis sözlüğü (kodun kendi günlük metinlerinden üretilir)
    with open(os.path.join(app, "teshis-sozluk.txt"), "w") as g:
        subprocess.run([PY, os.path.join(KOD, "teshis.py"), "--sozluk", KOD], stdout=g, stderr=subprocess.DEVNULL, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    # takvim yardımcısı (Mac Takvim → takvim.json); takvim izni uygulamaya verilir (ilk açılışta sorulur)
    tak = os.path.join(app, "Suflor Takvim.app"); r = derle(tak, "takvim.swift", "SuflorTakvim", TAKVIM_PLIST)
    if r is True: say(f"Takvim yardımcısı derlendi: {tak}")
    elif r: say(f"UYARI: takvim yardımcısı derlenemedi ({r}) — takvim özelliği kapalı kalır")
    # yerel ses yardımcısı: toplantı uygulamasının sesini (karşı taraf) Core Audio process tap ile alır. macOS 14.4+; izin
    # "Sistem Sesi Kaydı" uygulamaya verilir — yalnız ilk kurulumda sorulur, güncellemede aynı yerel imzayla izin korunur
    ses = os.path.join(app, "Suflor Ses.app"); ses_ilk = not os.access(os.path.join(ses, "Contents", "MacOS", "SuflorSes"), os.X_OK); ses_yeni = False
    mac_s = tuple(int(x) for x in (platform.mac_ver()[0] or "0").split(".")[:2] + ["0"])[:2]
    if mac_s >= (14, 4):
        r = derle(ses, "ses-yardimcisi.swift", "SuflorSes", SES_PLIST)
        if r is True:
            say(f"Ses yardımcısı derlendi: {ses}"); ses_yeni = True
            sessiz("pkill", "-u", str(os.getuid()), "-x", "SuflorSes")  # eski kopya kapanır, aktarıcı yenisini açar
        elif r: say(f"UYARI: ses yardımcısı derlenemedi ({r}) — karşı ses için Suflor.me simgesi → Karşı taraf → Aç ile devam")
    # brifing yardımcısı: toplantı öncesi brifingin claude -p çağrısı (aktarıcı Masaüstü'ndeki proje klasörünü okuyamaz; izin uygulamaya sorulur)
    brf = os.path.join(app, "Suflor Brifing.app"); r = derle(brf, "brifing.swift", "SuflorBrifing", BRIFING_PLIST)
    if r is True: say(f"Brifing yardımcısı derlendi: {brf}")
    elif r: say(f"UYARI: brifing yardımcısı derlenemedi ({r}) — panodaki Brifing kapalı kalır")
    imzala([tak, ses, brf])
    from xml.sax.saxutils import escape as x
    log = os.path.join(EV, "Library", "Logs", "suflor-aktarici.log")
    os.makedirs(os.path.dirname(plist_yolu()), exist_ok=True)
    open(plist_yolu(), "w", encoding="utf-8").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>{x(app)}/relay.py</string><string>--dir</string><string>{x(canli)}</string><string>--port</string><string>{port}</string>
  </array>
  <key>WorkingDirectory</key><string>{x(app)}</string>
  <key>EnvironmentVariables</key><dict>
    <key>PYTHONDONTWRITEBYTECODE</key><string>1</string><key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>{x(log)}</string>
  <key>StandardErrorPath</key><string>{x(log)}</string>
</dict></plist>
""")
    # elle başlatılmış bir aktarıcı portu tutuyorsa kapat, ajanı yeniden yükle
    aktarici_durdur()
    zorunlu("launchctl", "bootstrap", gui(), plist_yolu()); time.sleep(2)
    try: urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=3)
    except Exception:
        say(f"UYARI: aktarıcı yanıt vermiyor. Günlük: {log}")
        try: say("".join(open(log, encoding="utf-8", errors="replace").readlines()[-5:]).rstrip())
        except OSError: pass
        sys.exit(1)
    say(f"Aktarıcı çalışıyor → http://127.0.0.1:{port}/  (Mac açılışında kendiliğinden başlar, çökerse yeniden kalkar)")
    # ilk kurulumda izin penceresi şimdi çıksın, toplantının ortasında değil — aktarıcı yeniden başlatıldıktan SONRA (önceden izin
    # beklenirken pencere kapatılırsa aktarıcı eski sürümde kalıyordu); en çok 2 dk beklenir, sihirbazın "Kuruyorum" adımı takılmasın
    if ses_yeni and ses_ilk:
        say("Sistem sesi kaydı izni: macOS 'Suflor Ses' için izin sorarsa İzin Ver de (Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı). En çok 2 dk beklenir; aktarıcı zaten çalışıyor.")
        p = subprocess.Popen(["open", "-g", "-W", "-a", ses, "--args", "--izin"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try: p.wait(120)
        except subprocess.TimeoutExpired: p.kill()

def modeller():
    # Yerel modeller ve Python ortamı — yeni Mac'te ya da bozulunca; olanı yeniden kurmaz. İnternet yalnız burada gerekir; aktarıcı
    # modelleri çevrimdışı açar (HF_HUB_OFFLINE=1). İki macOS hesabında ortak klasör (ayar "ortak"): başka hesap kurduysa bu hesap
    # yalnız okur — eksik yoksa hiçbir şey indirmez. Sürümler 2 Ekim 2026'da çalışan kurulumdan sabitlendi.
    #   whisper-venv: mlx-whisper (Apple GPU) ~760 MB · whisper-modeller: whisper-large-v3-turbo ~1,6 GB (+ yerel 8 bit ~0,8 GB)
    #   ses-modeller: speechbrain/spkrec-ecapa-voxceleb ~85 MB → ecapa-mlx.npz (konuşmacı ayırma, Whisper işçisinde MLX ile)
    ort = yollar()["ortak"]; vpy = os.path.join(ort, "whisper-venv", "bin", "python")
    try: os.makedirs(ort, exist_ok=True)
    except OSError: pass
    if not os.access(ort, os.W_OK): say(f"Not: {ort} başka bir hesabın — yalnız denetlenecek, kurulum yapılmayacak.")
    bos = shutil.disk_usage(EV).free // 2 ** 30
    if bos < 6: sys.exit(f"Diskte {bos} GB boş — en az 6 GB gerekli. Yer açıp yeniden çalıştır.")
    ok = lambda py, kod: bool((r := sessiz(py, "-c", kod)) and r.returncode == 0)
    # modeller önce GitHub Release'ten (ayar model_deposu, yoksa açık depo; etiket modeller-v1; gh oturumu), SHA-256 doğrulanarak;
    # olmazsa Hugging Face'ten. Python ortamı her zaman sabit sürümlerle kurulur (taşınamaz).
    rel, depo = "modeller-v1", ayar().get("model_deposu") or "suflorme/suflor"
    def rel_indir(ad):
        if not shutil.which("gh") or not ((r := sessiz("gh", "auth", "status")) and r.returncode == 0): return False
        t = tempfile.mkdtemp(); say(f"→ {ad} GitHub'dan indiriliyor…")
        try:
            if subprocess.run(["gh", "release", "download", rel, "-R", depo, "-p", ad, "-p", "SHA256SUMS", "-D", t]).returncode: return False
            import hashlib
            bek = next((l.split()[0] for l in open(os.path.join(t, "SHA256SUMS")) if l.split()[-1:] == [ad]), None)
            h = hashlib.sha256()
            with open(os.path.join(t, ad), "rb") as f:
                for parca in iter(lambda: f.read(1 << 20), b""): h.update(parca)
            if not bek or h.hexdigest() != bek: say("  doğrulama tutmadı"); return False
            return subprocess.run(["tar", "-xf", os.path.join(t, ad), "-C", ort]).returncode == 0
        finally: shutil.rmtree(t, ignore_errors=True)
    if ok(vpy, "import mlx_whisper"): say("✓ whisper-venv var")
    else:
        say("→ whisper-venv kuruluyor…"); zorunlu(PY, "-m", "venv", os.path.join(ort, "whisper-venv"))
        zorunlu(vpy, "-m", "pip", "install", "-q", "--upgrade", "pip")
        zorunlu(vpy, "-m", "pip", "install", "-q", "mlx-whisper==0.4.3", "mlx==0.29.3", "numpy==2.0.2")
    hf = dict(os.environ, HF_HOME=os.path.join(ort, "whisper-modeller"))
    if os.path.isdir(os.path.join(ort, "whisper-modeller", "hub", "models--mlx-community--whisper-large-v3-turbo")): say("✓ Whisper modeli var")
    elif not rel_indir("suflor-whisper-large-v3-turbo.tar"):
        say("→ Whisper modeli Hugging Face'ten indiriliyor (~1,6 GB)…")
        zorunlu(vpy, "-c", "from huggingface_hub import snapshot_download as s; s('mlx-community/whisper-large-v3-turbo')", env=hf)
    ek = os.path.join(ort, "ses-modeller", "spkrec-ecapa-voxceleb"); os.makedirs(os.path.dirname(ek), exist_ok=True)
    if os.path.isfile(os.path.join(ek, "embedding_model.ckpt")): say("✓ ses izi modeli var")
    else:
        say("→ ses izi modeli Hugging Face'ten indiriliyor (~85 MB)…")
        zorunlu(vpy, "-c", "import sys; from huggingface_hub import snapshot_download as s; s('speechbrain/spkrec-ecapa-voxceleb', local_dir=sys.argv[1], "
                "allow_patterns=['embedding_model.ckpt', 'hyperparams.yaml'])", ek)
    if os.path.isfile(os.path.join(ek, "ecapa-mlx.npz")): say("✓ ses izi ağırlıkları (MLX) var")
    else: ecapa_donustur(ort, onbellek=False)
    whisper_8bit(ort)
    say("→ Deneme: modeller çevrimdışı açılıyor mu…")
    zorunlu(vpy, "-c", "import numpy as np, mlx_whisper; mlx_whisper.transcribe(np.zeros(16000, np.float32), "
            "path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='tr'); print('✓ Whisper açılıyor')", env=dict(hf, HF_HUB_OFFLINE="1"))
    sessiz("chmod", "-R", "go+rX", ort)  # diğer hesap okuyabilsin
    say("Tamam. Şimdi: ./aktarici-kur.command")

def surum(kok):
    try: return json.load(open(os.path.join(kok, "manifest.json"), encoding="utf-8"))["version"]
    except Exception: return "?"
def guncelle(kaynak=None):
    # İki kurulum biçimi: git klonu (.git var → git pull) ya da tek satır kurulum (kur.sh; .git yok → açık depodan tar).
    # Kod güncellenince kurulum YENİ kodla yapılır (bu dosya da değişmiş olabilir). kaynak: deneme için tar.gz yolu ya da adresi.
    depo = "suflorme/suflor"
    if os.path.isdir(os.path.join(KOD, ".git")) and not kaynak:
        g = lambda *c: subprocess.run(["git", "-C", KOD, *c], capture_output=True, text=True)
        kirli = g("status", "--porcelain", "--untracked-files=no").stdout
        if kirli.strip(): sys.exit("Kod klasöründe kaydedilmemiş değişiklik var — güncelleme yapılmadı:\n" + g("status", "--short").stdout)
        once = g("rev-parse", "--short", "HEAD").stdout.strip()
        if subprocess.run(["git", "-C", KOD, "pull", "--ff-only", "-q"]).returncode: sys.exit("git pull başarısız — güncelleme yapılmadı.")
        sonra = g("rev-parse", "--short", "HEAD").stdout.strip()
        say(f"✓ zaten güncel ({sonra})" if once == sonra else f"✓ güncellendi: {once} → {sonra}\n" + g("log", "--oneline", f"{once}..{sonra}").stdout.rstrip())
    else:
        import io, tarfile
        once = surum(KOD); url = kaynak or f"https://codeload.github.com/{depo}/tar.gz/refs/heads/main"
        say(f"→ son sürüm indiriliyor ({url if kaynak else 'github.com/' + depo})")
        gecici = tempfile.mkdtemp()
        try:
            try:
                veri = open(url, "rb").read() if os.path.isfile(url) else urllib.request.urlopen(url, timeout=120).read()
                with tarfile.open(fileobj=io.BytesIO(veri), mode="r:gz") as t:
                    for u in t.getmembers():  # üst klasör (suflor-main/) atılır; dışarı yazan yol kabul edilmez
                        parca = u.name.split("/", 1)
                        if len(parca) < 2 or not parca[1] or parca[1].startswith("/") or ".." in parca[1].split("/") or not (u.isfile() or u.isdir()): continue
                        u.name = parca[1]; t.extract(u, gecici)
            except Exception as e: sys.exit(f"İndirilemedi ({e}) — internet bağlantısını denetle, sonra yeniden çift tıkla. Hiçbir dosya değişmedi.")
            if not (os.path.isfile(os.path.join(gecici, "manifest.json")) and os.path.isfile(os.path.join(gecici, "relay.py"))):
                sys.exit("İndirilen paket eksik — güncelleme yapılmadı.")
            sonra = surum(gecici)
            if once == sonra: say(f"✓ zaten güncel (v{sonra}) — yine de aktarıcı ve komut yenileniyor")
            # kod dosyaları güncellenir; kullanıcının bu klasöre koyduğu başka bir şey silinmez (yalnız kalkan eski betikler)
            for k, _, fs in os.walk(gecici):
                for f in fs:
                    h = os.path.join(KOD, os.path.relpath(os.path.join(k, f), gecici)); os.makedirs(os.path.dirname(h), exist_ok=True)
                    shutil.copy2(os.path.join(k, f), h)
        finally: shutil.rmtree(gecici, ignore_errors=True)
        for f in ESKI_BETIK:
            if os.path.isfile(os.path.join(KOD, f)) and not os.path.isfile(os.path.join(KOD, ".git", "HEAD")): os.remove(os.path.join(KOD, f))
        for f in glob_(os.path.join(KOD, "*.command")) + glob_(os.path.join(KOD, "*.sh")): os.chmod(f, os.stat(f).st_mode | 0o111)
        sessiz("xattr", "-dr", "com.apple.quarantine", KOD)
        if once != sonra: say(f"✓ güncellendi: v{once} → v{sonra}")
    if subprocess.run([PY, os.path.join(KOD, "kurulum.py"), "kur"]).returncode:
        say("\nUYARI: aktarıcı kurulamadı — kod güncellendi ama çalışan aktarıcı eski sürümde kalmış olabilir.")
        sys.exit(f"Bu pencerenin yukarısındaki hatayı geliştiriciye ilet ya da {KOD}/aktarici-kur.command dosyasına çift tıkla.")
    # kişisel hesapta kod v0.13.6 iken çalışan aktarıcı v0.13.2'de kalmıştı — sürümler karşılaştırılır
    try: calisan = json.load(urllib.request.urlopen(f"http://127.0.0.1:{yollar()['port']}/status", timeout=3)).get("surum", "?")
    except Exception: calisan = "?"
    if calisan != surum(KOD):
        say(f"UYARI: çalışan aktarıcı v{calisan}, kod v{surum(KOD)}. {KOD}/aktarici-kur.command dosyasına çift tıkla; düzelmezse Mac'i yeniden başlat.")
    else: say(f"✓ aktarıcı v{calisan} çalışıyor")
    a = ayar()
    if a.get("komut_sablondan"):  # kendi komutunu yazan alan (komut_sablondan yok): dokunma; eskisi .eski olarak kalır
        proje = os.path.expanduser(a["proje"]); hedef = os.path.join(proje, ".claude", "commands", "toplanti.md")
        s = open(os.path.join(KOD, "sablon", "toplanti.md"), encoding="utf-8").read()
        for k, v in {"{{ALAN}}": a["alan"], "{{AD}}": a["ad"], "{{PORT}}": str(a["port"]), "{{PROJE}}": proje, "{{KOD}}": KOD}.items(): s = s.replace(k, v)
        if os.path.isdir(os.path.dirname(hedef)):
            if os.path.exists(hedef) and open(hedef, encoding="utf-8").read() != s: shutil.copy(hedef, hedef + ".eski")
            open(hedef, "w", encoding="utf-8").write(s); say("✓ /toplanti komutu şablondan yenilendi")
    say("Chrome eklentisi toplantı yokken bir dakika içinde kendini yeniler. Açık bir Teams sekmesi varsa onu yenile.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Suflor.me kurulumu: komutsuz sihirbaz; kur | kaldir | modeller | guncelle")
    ap.add_argument("is_", nargs="?", choices=["kur", "kaldir", "modeller", "guncelle", "profil"], metavar="kur|kaldir|modeller|guncelle|profil")
    ap.add_argument("--port", type=int, default=8770); ap.add_argument("--ac", action="store_true")
    ap.add_argument("--kaynak", help="guncelle: açık depo yerine bu tar.gz (deneme)"); A = ap.parse_args()
    if A.is_: {"kur": kur, "kaldir": kaldir, "modeller": modeller, "guncelle": lambda: guncelle(A.kaynak), "profil": profil}[A.is_](); sys.exit(0)
    os.makedirs(DESTEK, exist_ok=True)
    # port doluysa (ör. diğer macOS hesabının sihirbazı) sonrakini dene — önceden ikinci sihirbaz açılmıyor, kur.sh
    # tarayıcıda öbür hesabın sihirbazını açıyordu
    for port in range(A.port, A.port + 10):
        try: s = ThreadingHTTPServer(("127.0.0.1", port), H); A.port = port; break
        except OSError: continue
    else: sys.exit(f"Suflor.me kurulum sihirbazı: {A.port}–{A.port + 9} portlarının hepsi dolu")
    print(f"Suflor.me kurulum sihirbazı: http://127.0.0.1:{A.port}/" + ("  (deneme: " + EV + ")" if DENEME else ""), flush=True)
    if A.ac:  # sihirbaz Chrome'da açılır (eklenti adımı Chrome ister; varsayılan tarayıcı Safari olabilir) — Chrome yoksa varsayılan
        cr = next((y for y in ("/Applications/Google Chrome.app", os.path.join(EV, "Applications/Google Chrome.app")) if os.path.isdir(y)), None)
        subprocess.Popen(["open"] + (["-a", cr] if cr else []) + [f"http://127.0.0.1:{A.port}/?k={ANAHTAR}"])
    elif DENEME: print(f"  açılış: http://127.0.0.1:{A.port}/?k={ANAHTAR}", flush=True)
    s.serve_forever()
