#!/usr/bin/env python3
# Suflor.me kurulum sihirbazı — yerel sunucu (yalnız 127.0.0.1). Tarayıcıdaki sihirbaz (sihirbaz/) bu uçlarla konuşur:
# Mac denetimi, modellerin arka planda inmesi, Claude Code denetimi, profil (Claude'un hazırladığı çalışma notu), dosya
# yükleme, klasör seçimi, takvim izni ve son kurulum (ayar.json, proje klasörü, /toplanti komutu, aktarıcı). Durum
# ~/Library/Application Support/Suflor/kurulum.json'da: sekme kapanırsa sihirbaz kaldığı adımdan sürer.
#   python3 kurulum.py [--port 8770] [--ac]     (--ac: tarayıcıda aç)
# Deneme: SUFLOR_EV=<geçici klasör> ev klasörünü değiştirir (ayar, uygulama, proje oraya yazılır; aktarıcı kurulmaz).
import argparse, shlex, datetime, getpass, json, os, platform, re, secrets, shutil, subprocess, sys, tempfile, threading, time, urllib.request
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
ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8770); ap.add_argument("--ac", action="store_true"); A = ap.parse_args()

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
    # v0.13.5: eski yerel kurulum (~/.claude/local) ve npm yolları da; hiçbiri yoksa kullanıcının kabuğuna sorulur
    for p in (shutil.which("claude"), os.path.join(EV, ".local/bin/claude"), os.path.join(EV, ".claude/local/claude"), "/opt/homebrew/bin/claude",
              "/usr/local/bin/claude", os.path.join(EV, ".npm-global/bin/claude")):
        if p and os.path.exists(p): return p
    if not DENEME and CLAUDE.get("kabuk_yolu") is None:
        v = sh(kabuk_rc()[1], "-lic", "command -v claude", zaman=10).splitlines()
        CLAUDE["kabuk_yolu"] = v[-1].strip() if v and os.path.isabs(v[-1].strip()) and os.path.exists(v[-1].strip()) else ""
    return CLAUDE.get("kabuk_yolu") or None
# v0.13.3 (kişisel hesap kurulumu, 5 Ekim): Claude'un kurulum betiği ~/.local/bin'i Terminal'in arama yoluna eklemiyor — sihirbaz
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
    # v0.13.3: başarısızlığın nedeni saklanır ve sihirbazda gösterilir (önceden yalnız "oturum açılmamış ya da denetlenmedi")
    p = claude_yolu(); neden = None
    if not p: CLAUDE.update(giris=False, neden={"tur": "yok"}); return
    try:
        r = subprocess.run([p, "-p", "Yalnız TAMAM yaz."], capture_output=True, text=True, timeout=90, cwd=tempfile.gettempdir(), stdin=subprocess.DEVNULL)
        ok = r.returncode == 0 and "TAMAM" in r.stdout.upper()
        if not ok:
            satirlar = [x.strip() for x in _ANSI.sub("", (r.stderr or "") + "\n" + (r.stdout or "")).splitlines() if x.strip()]
            ham = " · ".join(satirlar[-2:])[:240] or f"çıkış kodu {r.returncode}"
            abone = re.search(r"credit balance|subscription|usage limit|quota|billing|plan does not|upgrade", ham, re.I)  # v0.13.5
            giris = re.search(r"log ?in|/login|not logged|authenticat|api key|oauth|credential|unauthori", ham, re.I)
            neden = {"tur": "abonelik" if abone else "giris" if giris else "hata", "ham": ham}
    except subprocess.TimeoutExpired: ok = False; neden = {"tur": "zaman"}
    except Exception as e: ok = False; neden = {"tur": "hata", "ham": str(e)[:240]}
    CLAUDE.update(giris=ok, neden=neden)
    k = oku_json(KAYIT); k["claude_giris"] = ok; k["claude_neden"] = neden; yaz_json(KAYIT, k)  # sunucu yeniden başlasa da hatırlansın

# ---------- modeller (arka planda modeller-kur.command) ----------
MODEL = {"durum": None, "yuzde": 0, "mesaj": "", "p": None}
GEREKEN_GB = 4.3
def modeller_hazir():
    return (os.path.exists(f"{ORTAK}/whisper-venv/bin/python") and os.path.isdir(f"{ORTAK}/whisper-modeller/hub") and
            os.path.exists(f"{ORTAK}/ses-venv/bin/python") and os.path.exists(f"{ORTAK}/ses-modeller/emotion2vec_plus_base/model.pt"))
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
    # v0.13.5: modeller ortak klasörde; başka macOS hesabı kurduysa ve eksikse bu hesap tamamlayamaz (yazma izni yok)
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
    MODEL["p"] = subprocess.Popen([os.path.join(KOD, "modeller-kur.command")], stdout=open(os.path.join(DESTEK, "modeller-kur.log"), "a"),
                                  stderr=subprocess.STDOUT, start_new_session=True)

# ---------- aktarıcı (kurulduysa) ----------
def aktarici(yol):
    port = ayar().get("port")
    if not port: return None
    try: return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}{yol}", timeout=2))
    except Exception: return None
def eklenti():
    # v0.13.5: önceden yalnız Teams sekmesindeki eklentinin nabzı sayılıyordu — Teams açık değilse sihirbaz bu adımda bekleyip kalıyordu.
    # Eklentinin arka planı aktarıcıyı dakikada bir (ve yüklenince hemen) yoklar; aktarıcı bunu "eklenti_kurulu" olarak tutar.
    s = aktarici("/status") or {}; x = s.get("extension") or {}; k = s.get("eklenti_kurulu") or {}
    nabiz = x.get("age_s") is not None and x["age_s"] < 30; arka = k.get("age_s") is not None and k["age_s"] < 90
    # v0.13.5: bu Mac'te başka hesabın aktarıcısı da çalışıyorsa eklenti hangisine yazacağını sorar (Suflor.me simgesi → alan seç)
    coklu = sum(1 for p in range(8765, 8769) if p != ayar().get("port") and _acik(p)) > 0 if s else False
    return {"bagli": nabiz or arka, "surum": (x.get("ver") if nabiz else k.get("ver")) if (nabiz or arka) else None, "coklu": coklu, "alan": s.get("alan")}
def _acik(p):
    try: urllib.request.urlopen(f"http://127.0.0.1:{p}/status", timeout=0.6); return True
    except Exception: return False
def yerel_ses():  # v0.13.5: karşı ses yardımcısı kuruldu mu (kur adımında gösterilir)
    s = aktarici("/status") or {}; y = s.get("yerel_ses") or {}
    return {"kurulu": bool(y.get("kurulu")), "durum": y.get("durum")} if s else None
def takvim():
    t = aktarici("/takvim")
    if not t: return {"durum": "kurulmadi"}
    a = ayar(); tj = oku_json(os.path.join(gen(a.get("uygulama") or "~/Library/Application Support/Suflor"), "takvim.json"))
    tk = {}
    for e in tj.get("olaylar", []):
        if e.get("takvim"): tk[f'{e["takvim"]} · {e.get("hesap") or ""}'] = {"ad": e["takvim"], "hesap": e.get("hesap") or ""}
    return {"durum": t.get("durum"), "takvimler": list(tk.values()),
            "olaylar": [{"saat": o["saat"], "bitis": o["bitis_saat"], "baslik": o["baslik"], "platform": o.get("platform")} for o in t.get("olaylar", [])]}

# ---------- profil: Claude'un çalışma notu ----------
PROFIL = {"durum": None, "metin": "", "terimler": []}
PROFIL_ISTEM = {"tr": """Sen Suflor.me'nin kurulum yardımcısısın. Suflor.me, kullanıcının toplantılarını canlı izleyip ona kısa kartlarla ne
sorması, neyi belirtmesi gerektiğini söyleyen bir asistan. Aşağıda kullanıcının kendini anlattığı cevaplar ve varsa LinkedIn
profili ile geçmiş görüşme dökümleri var (dosya yolları verildiyse Read ile oku). Bunlardan kullanıcı için bir "çalışma notu" çıkar:
kim olduğu, rolü, toplantı türleri, kartlarda neye öncelik vermesi ve neyle rahatsız edilmemesi gerektiği. 120–220 kelime,
düz Türkçe, madde değil kısa paragraflar; uydurma bilgi yazma. Ayrıca konuşma tanımanın doğru yazması gereken özel adları ve
terimleri (kişi adları, sistem ve ürün adları, kısaltmalar) en çok 30 tane çıkar.
Yalnız şu JSON'u yaz, başka hiçbir şey yazma: {"not": "...", "terimler": ["...", "..."]}""",
               "en": """You are Suflor.me's setup assistant. Suflor.me follows the user's meetings live and tells them in short cards what to ask
and what to point out. Below are the user's answers about themselves and, if provided, their LinkedIn profile and past meeting
transcripts (read the files with Read if paths are given). Write a "working note" about the user: who they are, their role,
their meetings, what cards should prioritise and what should not interrupt them. 120–220 words, plain English, short paragraphs,
no invented facts. Also list up to 30 special names and terms speech recognition must spell correctly (people, systems, products, acronyms).
Output only this JSON and nothing else: {"not": "...", "terimler": ["...", "..."]}"""}
def profil_olustur(cevap, dil):
    p = claude_yolu()
    if not p or cevap.get("kartsiz"): PROFIL.update(durum="yok"); return
    PROFIL.update(durum="calisiyor")
    def is_():
        alanlar = {k: cevap.get(k) for k in ("ad", "rol", "sirket", "is_alani", "araclar", "araclar_ek", "kisiler", "s1", "s2", "s3", "s4", "linkedin_metin") if cevap.get(k)}
        dosyalar = [os.path.join(YUKLEME, "linkedin", f) for f in os.listdir(os.path.join(YUKLEME, "linkedin"))] if os.path.isdir(os.path.join(YUKLEME, "linkedin")) else []
        dosyalar += [os.path.join(YUKLEME, "gorusmeler", f) for f in sorted(os.listdir(os.path.join(YUKLEME, "gorusmeler")))[:5]] if os.path.isdir(os.path.join(YUKLEME, "gorusmeler")) else []
        istem = PROFIL_ISTEM.get(dil, PROFIL_ISTEM["tr"]) + "\n\nCEVAPLAR:\n" + json.dumps(alanlar, ensure_ascii=False, indent=1) + \
            ("\n\nDOSYALAR:\n" + "\n".join(dosyalar) if dosyalar else "")
        try:
            r = subprocess.run([p, "-p", istem, "--allowedTools", "Read", "--add-dir", YUKLEME], capture_output=True, text=True, timeout=240, cwd=YUKLEME if os.path.isdir(YUKLEME) else tempfile.gettempdir())
            m = re.search(r"\{.*\}", r.stdout, re.S); j = json.loads(m.group(0)) if m else {}
            PROFIL.update(durum="hazir" if j.get("not") else "hata", metin=str(j.get("not") or "").strip(), terimler=[str(x)[:60] for x in (j.get("terimler") or [])][:30])
        except Exception as e: PROFIL.update(durum="hata", metin="", terimler=[])
    threading.Thread(target=is_, daemon=True).start()

# ---------- son kurulum ----------
def bos_port():
    for p in range(8765, 8770):
        try: urllib.request.urlopen(f"http://127.0.0.1:{p}/status", timeout=1)
        except Exception: return p
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
              "takvim_haric": [x for x in (c.get("takvim_cikar") or [])],
              "teshis": c.get("teshis") is True})  # v0.12.0 beta teşhis izni (teshis.py; adres teshis_adres ya da varsayılan)
    a.setdefault("claude_model", "sonnet")
    if claude_yolu() and not a.get("claude"): a["claude"] = claude_yolu()  # v0.13.5: aktarıcı panodan başlatırken aynı Claude
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
    try:
        cm = os.path.join(proje, "CLAUDE.md"); s = open(cm, encoding="utf-8").read(); baslik = "## Ben ve işim" if dil == "tr" else "## About me and my work"
        metin = str(c.get("profil_metin") or "").strip()
        if metin and baslik not in s:
            s = s.rstrip() + f"\n\n{baslik}\n" + (f"_Kurulum sihirbazında hazırlandı ({datetime.date.today().isoformat()}); düzenleyebilirsin._\n\n" if dil == "tr" else
                                                  f"_Drafted by the setup assistant ({datetime.date.today().isoformat()}); edit freely._\n\n") + metin + "\n"
            if kisiler: s += ("\nSık görüştüğüm kişiler: " if dil == "tr" else "\nPeople I meet often: ") + ", ".join(kisiler) + "\n"
            open(cm, "w", encoding="utf-8").write(s)
        sonuc["not"] = "iyi"
    except Exception as e: sonuc.update(**{"not": "uyari"})
    if DENEME: sonuc["aktarici"] = "iyi"; return sonuc
    r = subprocess.run([os.path.join(KOD, "aktarici-kur.command")], capture_output=True, text=True, timeout=300)
    sonuc["aktarici"] = "iyi" if r.returncode == 0 else "kotu"
    sonuc["uyarilar"] = [x.strip()[:220] for x in (r.stdout + r.stderr).splitlines() if x.strip().startswith("UYARI")][:4]  # v0.13.5
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
    elif hedef == "claude-yol": yola_ekle()  # v0.13.3
    elif hedef == "claude-giris" and claude_yolu():  # v0.13.3: Claude'u tam yoluyla Terminal'de açar. v0.13.5: adımlar sihirbazın dilinde
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
    elif hedef == "ses-izni": subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AudioCapture"])  # v0.13.5
    elif hedef == "internet-hesaplari": subprocess.Popen(["open", "x-apple.systempreferences:com.apple.Internet-Accounts-Settings.extension"])
    elif hedef == "teams-dene": subprocess.Popen(["open", "-a", "Google Chrome", "https://teams.microsoft.com/v2/"])
    elif hedef == "chrome-eklentiler": subprocess.Popen(["open", "-a", "Google Chrome", "chrome://extensions"])
    elif hedef == "eklenti-klasoru": subprocess.Popen(["open", "-R", os.path.join(KOD, "manifest.json")])
    elif hedef == "pano" and a.get("port"):
        subprocess.Popen(["open"] + (["-a", "Google Chrome"] if os.path.isdir("/Applications/Google Chrome.app") else []) + [f"http://127.0.0.1:{a['port']}/?tur"])  # v0.12.5: pano Chrome'da; threading.Timer(3, lambda: os._exit(0)).start()
def klasor_sec():
    r = sh("osascript", "-e", 'POSIX path of (choose folder with prompt "Suflor.me proje klasörü")', zaman=300)
    return r.rstrip("/") if r else None

# ---------- sunucu ----------
STATIK = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
          ".svg": "image/svg+xml", ".woff2": "font/woff2", ".png": "image/png"}
# v0.13.3: yerel anahtar. 127.0.0.1 bu Mac'teki her kullanıcıya ve programa açık; Origin/Host denetimi tarayıcıyı durdurur ama
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
        # v0.12.3 (güvenlik denetimi D6): DNS rebinding — başka alan adı 127.0.0.1'e çözülse de Host başlığı o alan adı olur
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
        if yol == "/api/profil": return self._json({k: PROFIL[k] for k in ("durum", "metin", "terimler")})
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
        if not self._cerezli(): return self._json({"hata": "anahtar"}, 403)  # v0.13.3
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
        if yol == "/api/profil/olustur": profil_olustur(p.get("cevap") or {}, p.get("dil") or "tr"); return self._json({"ok": True})
        if yol == "/api/kur/tamamla": return self._json(tamamla(p.get("cevap") or {}, p.get("dil") or "tr"))
        if yol == "/api/klasor-sec": return self._json({"yol": klasor_sec()})
        if yol == "/api/ac": ac(str(p.get("hedef") or "")); return self._json({"ok": True})
        self._json({"hata": "yok"}, 404)

if __name__ == "__main__":
    os.makedirs(DESTEK, exist_ok=True)
    # v0.13.3: port doluysa (ör. diğer macOS hesabının sihirbazı) sonrakini dene — önceden ikinci sihirbaz açılmıyor, kur.sh
    # tarayıcıda öbür hesabın sihirbazını açıyordu
    for port in range(A.port, A.port + 10):
        try: s = ThreadingHTTPServer(("127.0.0.1", port), H); A.port = port; break
        except OSError: continue
    else: sys.exit(f"Suflor.me kurulum sihirbazı: {A.port}–{A.port + 9} portlarının hepsi dolu")
    print(f"Suflor.me kurulum sihirbazı: http://127.0.0.1:{A.port}/" + ("  (deneme: " + EV + ")" if DENEME else ""), flush=True)
    if A.ac:  # v0.13.4: sihirbaz Chrome'da açılır (eklenti adımı Chrome ister; varsayılan tarayıcı Safari olabilir) — Chrome yoksa varsayılan
        cr = next((y for y in ("/Applications/Google Chrome.app", os.path.join(EV, "Applications/Google Chrome.app")) if os.path.isdir(y)), None)
        subprocess.Popen(["open"] + (["-a", cr] if cr else []) + [f"http://127.0.0.1:{A.port}/?k={ANAHTAR}"])
    elif DENEME: print(f"  açılış: http://127.0.0.1:{A.port}/?k={ANAHTAR}", flush=True)
    s.serve_forever()
