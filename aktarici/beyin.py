# Suflor.me beyin katmanı (Aşama 0, v0.121.1; tasarım ~/Desktop/Suflor/planlar/beyin-saglayici.md): yapay zekâ çağrılarının tek giriş noktası.
# Ayrı modüldür (relay.py'nin ad alanında bölüm olarak çalışmaz): aktarıcı (brifing-ses.py BEYIN) ve proje-karti.py importlib ile yükler. Python 3.9 uyumlu.
# İşler: konus, ceviri, telaffuz, brifing, proje_karti. Toplantı oturumu bilerek dışarıda (K3: Claude Code'da kalır, aktarici/toplanti-oturum.py).
# İki uyarlayıcı: claude-code (`claude -p`; abonelik, önbellek tam; varsayılan) ve v0.122.0'dan (Aşama 1) openai-uyumlu (Gemini'nin OpenAI uyumlu ucu, OpenAI,
# Ollama, LM Studio). Aşama 1 (v0.122.0) Konuş; Aşama 2: tek çağrılar da (proje kartı, telaffuz: tek_cagri / `beyin.py tek`; çeviri: araçsız açık süreç).
# Yedek (§3.8): sağlayıcı hata ya da zaman aşımı verirse ve Claude Code kuruluysa o iş bir kez Claude Code ile yapılır (çağıran yerde; günlükte "BEYİN: yedek").
# Çıktı Claude Code'un json / stream-json biçimidir ve iç protokol olarak kalır: okuyucular
# (bas-konus.py _konus_oku, ceviri.py, brifing-ses.py claude_json) sağlayıcı değişse de aynı satırları okur.
# Ayar (isteğe bağlı): "beyin": {"varsayilan": {"tur": "claude-code"}, "<iş>": {"tur": …, "model": …}}. Yoksa eski anahtarlar (konus_model,
# ceviri_model, kart_model, claude_model) ve bugünkü varsayılanlar — ayarsız kurulumda argümanlar v0.121.0'dakiyle birebir aynı (test/beyin.py).
# openai-uyumlu: {"tur": "openai-uyumlu", "saglayici": "gemini"|"openai"|"ollama"|"lmstudio" (adres hazır) ya da "adres": "https://…/v1", "model": …,
# "anahtar": Anahtar Zinciri öğe adı (dosyaya anahtar yazılmaz; gemini'de yoksa ayar gemini_anahtar), "effort": reasoning_effort, "fiyat": [giriş, önbellek, çıkış] $/M belirteç,
# "yedek": false → hata olunca Claude Code'a düşmez}.
import glob as _glob, http.client, json, os, re, shutil, ssl, subprocess, sys, threading, time, urllib.parse, uuid

UYARLAYICILAR = ("claude-code", "openai-uyumlu")
ISLER = ("konus", "ceviri", "telaffuz", "brifing", "proje_karti")
DESTEK = {"claude-code": ISLER, "openai-uyumlu": ("konus", "ceviri", "telaffuz", "proje_karti")}  # sesli brifing rafta (S87): yalnız claude-code
VARSAYILAN_MODEL = {"konus": "sonnet", "ceviri": "haiku", "telaffuz": "sonnet", "brifing": None, "proje_karti": "sonnet"}
ESKI_ANAHTAR = {"konus": "konus_model", "ceviri": "ceviri_model", "brifing": "claude_model", "proje_karti": "kart_model"}
HAZIR = {"gemini": "https://generativelanguage.googleapis.com/v1beta/openai", "openai": "https://api.openai.com/v1",
         "ollama": "http://127.0.0.1:11434/v1", "lmstudio": "http://127.0.0.1:1234/v1"}
# $/M belirteç (giriş, önbellekten okunan, çıkış — düşünme dahil). Kaynak ai.google.dev/gemini-api/docs/pricing, erişim 23.10.2026 (ücretli katman);
# 3.8 Flash 1 Ocak 2027'de iki katına çıkıyor. Yerel adreste 0. Bilinmeyen modelde ayardaki "fiyat"; o da yoksa 0 (kayıtta maliyet 0 görünür).
FIYAT_MTOK = {"gemini-3.8-flash": (0.75, 0.075, 3.75), "gemini-3.6-flash": (0.75, 0.075, 3.75), "gemini-3.5-flash-lite": (0.30, 0.03, 2.50),
              "gemini-3.1-flash-lite": (0.25, 0.025, 1.50)}
_UYARILDI = set()

def _uyar(anahtar, metin):
    if anahtar not in _UYARILDI: _UYARILDI.add(anahtar); sys.stderr.write(metin + "\n")
def adres_uygun(a):  # ağ sınırı: https (sağlayıcının adresi) ya da yalnız bu Mac'teki http (yerel model); kullanıcı adı/sorgu yok
    try: u = urllib.parse.urlsplit(str(a or ""))
    except ValueError: return False
    if u.username or u.password or u.query or u.fragment or not u.hostname: return False
    return u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1"))
def yerel_mi(a): return urllib.parse.urlsplit(str(a or "")).hostname in ("127.0.0.1", "localhost", "::1")
def secim(ayar, is_):  # → {"tur": uyarlayıcı, "model": ad ya da None} (+ openai-uyumlu'da saglayici, adres, anahtar, effort, fiyat)
    b = ayar.get("beyin") if isinstance(ayar.get("beyin"), dict) else {}
    s = {}
    for k in ("varsayilan", is_):
        if isinstance(b.get(k), dict): s.update(b[k])
    if isinstance(b.get(is_), dict) and b[is_].get("tur"): s = dict(b[is_])  # işin kendi sağlayıcısı: varsayılanın model/saglayici alanı sızmasın (Adım 4 bulgusu)
    tur = str(s.get("tur") or "claude-code")
    if tur not in UYARLAYICILAR or is_ not in DESTEK[tur]:  # bilinmeyen ya da bu işi henüz yapamayan uyarlayıcı → bugünkü yol, bir kez uyarı
        _uyar((is_, tur), f"BEYİN: '{tur}' uyarlayıcısı {is_} için yok — claude-code kullanılıyor"); tur, s = "claude-code", {}
    if tur == "openai-uyumlu":
        sg = str(s.get("saglayici") or "").lower(); adres = str(s.get("adres") or HAZIR.get(sg) or "").rstrip("/"); model = s.get("model")
        if not adres_uygun(adres) or not model:
            _uyar((is_, "adres"), f"BEYİN: {is_} için openai-uyumlu ayarı eksik ya da adres izinli değil (https ya da 127.0.0.1) — claude-code kullanılıyor")
            tur, s = "claude-code", {}
        else:
            an = s.get("anahtar") or (ayar.get("gemini_anahtar") or "suflor-gemini" if sg == "gemini" else None)
            f = s.get("fiyat") if isinstance(s.get("fiyat"), list) and len(s.get("fiyat")) == 3 else None
            return {"tur": tur, "model": str(model), "saglayici": sg or ("yerel" if yerel_mi(adres) else "diger"), "adres": adres,
                    "anahtar": str(an) if an else None, "effort": str(s["effort"]) if s.get("effort") else None,
                    "fiyat": [float(x) for x in f] if f else (None if yerel_mi(adres) else FIYAT_MTOK.get(str(model))), "yedek": s.get("yedek", True) is not False}
    model = s.get("model") or ayar.get(ESKI_ANAHTAR.get(is_) or "") or VARSAYILAN_MODEL.get(is_)
    return {"tur": tur, "model": str(model) if model else None}
def claude_secim(ayar, is_):  # yedek için Claude Code seçimi: "beyin" ayarındaki model başka sağlayıcınınsa kullanılmaz (eski anahtar ya da varsayılan)
    s = secim(ayar, is_)
    if s["tur"] == "claude-code": return s
    m = ayar.get(ESKI_ANAHTAR.get(is_) or "") or VARSAYILAN_MODEL.get(is_)
    return {"tur": "claude-code", "model": str(m) if m else None}
def yedek_var(ayar, sec):  # sağlayıcı hata verdi: Claude Code'la bir kez denenebilir mi (ayarda yedek: false değil ve Claude Code kurulu)
    return sec.get("tur") == "openai-uyumlu" and sec.get("yedek", True) is not False and bool(claude_yolu(ayar))
def yedek_satiri(is_, sec, neden):  # günlükte tek satır (metin yok: yalnız sağlayıcı, model ve hatanın kısası)
    return f"BEYİN: yedek — {is_}: {sec.get('saglayici') or sec.get('tur')} {sec.get('model')} olmadı ({' '.join(str(neden or 'hata').split())[:120]}) → claude-code"

# --- claude-code uyarlayıcısı ----------------------------------------------------------------------------------------------------
def claude_yolu(ayar):  # relay.py claude_yolu ile aynı arama sırası (ayardaki yol önce)
    for y in [ayar.get("claude"), os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude", shutil.which("claude")]:
        if y and os.path.isfile(os.path.expanduser(y)) and os.access(os.path.expanduser(y), os.X_OK): return os.path.expanduser(y)
    return None
# Yalın `claude -p` (karar #83–84): kişisel ayar, bağlayıcı (MCP), komut ve oturum kaydı yüklenmez; proje ayarı kalır. Ayar claude_yalin: false → tam çağrı.
YALIN = ["--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence"]
def yalin(ayar):
    return YALIN + ["--tools", "Read,Grep,Glob"] if ayar.get("claude_yalin", True) else []
# Konuş (v0.90.0 reçete 1): proje CLAUDE.md'si ve git bilgisi ilk kullanıcı mesajına girip önbelleği bozuyordu → Konuş sürecinde kapalı (ortam değişkeni
# --settings env ile; Brifing.app yalnız bu iki anahtara izin verir). Ayar konus_onek_sabit: false eski davranış. konus_effort: low|medium|high|xhigh|max.
def konus_onek_ayar(ayar):
    if ayar.get("konus_onek_sabit", True) is False: return []
    return ["--settings", json.dumps({"env": {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS": "1"}})]
def konus_effort(ayar):
    e = str(ayar.get("konus_effort") or "").strip().lower()
    return ["--effort", e] if e in ("low", "medium", "high", "xhigh", "max") else []
def konus_args(ayar, sistem, ek_araclar="", mcp=None, ek_dizin=None, model=None):  # açık süreç (Brifing.app FIFO kipi): stream-json giriş/çıkış, parça parça metin; model: yedekte Claude modeli
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--allowedTools", "Read,Grep,Glob" + ("," + ek_araclar if ek_araclar else ""), "--add-dir", ek_dizin, "--append-system-prompt", sistem] + (["--mcp-config", mcp] if mcp else []) + \
           (yalin(ayar) or ["--no-session-persistence"]) + ["--model", model or secim(ayar, "konus")["model"]] + konus_onek_ayar(ayar) + konus_effort(ayar)
def ceviri_args(ayar, sistem, model=None):  # açık süreç, araçsız (Popen; stdin/stdout stream-json); model: yedekte Claude modeli
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--model", model or secim(ayar, "ceviri")["model"],
            "--tools", "", "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--system-prompt", sistem]
def telaffuz_args(ayar, istem, model=None):  # tek çağrı (Brifing.app), json çıktı; model: yedekte Claude modeli
    return ["-p", istem, "--output-format", "json", "--model", model or secim(ayar, "telaffuz")["model"]] + yalin(ayar)
def brifing_args(ayar, istem, ek_dizin, yalin_mi=True):  # tek çağrı + Read/Grep/Glob (sesli brifing, rafta)
    m = secim(ayar, "brifing")["model"]
    return ["-p", istem, "--allowedTools", "Read,Grep,Glob", "--add-dir", ek_dizin, "--output-format", "json"] + (yalin(ayar) if yalin_mi else []) + (["--model", m] if m else [])
def kart_args(model):  # tek çağrı, araçsız, istem stdin'den
    return ["-p", "--output-format", "json", "--model", model, "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands",
            "--no-session-persistence", "--tools", ""]
def tek(cl, args, girdi=None, cwd=None, zaman=300):  # tek çağrıyı çalıştırır → subprocess.CompletedProcess (stdout = json çıktı)
    return subprocess.run([cl] + args, input=girdi, capture_output=True, text=True, timeout=zaman, cwd=cwd)

# --- ölçüm ------------------------------------------------------------------------------------------------------------------------
def kullanim(j):  # sonuç satırı (json / stream-json "result") → sayılar; canli/claude-cagri.jsonl alanları buradan
    u = j.get("usage") or {}
    return {"giris": sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
            "okunan": u.get("cache_read_input_tokens") or 0, "cikti": u.get("output_tokens"), "maliyet": j.get("total_cost_usd") or 0}

# --- openai-uyumlu uyarlayıcısı (Aşama 1, v0.122.0) --------------------------------------------------------------------------------
# Konuş'un açık süreci: Brifing.app `--beyin <istek>` bu dosyayı `/usr/bin/python3 -I -B beyin.py calis <istek>` ile çalıştırır (Masaüstü izni uygulamada).
# Giriş Claude Code'un stream-json kullanıcı iletileri (FIFO'dan), çıkış Claude Code'un stream-json olayları (§3.2): Konuş'un okuyucusu değişmez.
# Araç döngüsü burada; araçlar Suflor'un kendi salt okunur araçları (§3.4): ara (dizin ya da tek dosyada satır), oku, listele (yalnız istekteki kökler) ve
# vt_sema/vt_sor (istemci tarafında MCP: toplanti-claude.py vt-mcp'ye stdio; sağlayıcı araca bağlanmaz). Akışta araç adları Claude Code'unkiler
# (Read/Grep/Glob/mcp__suflorvt__*): ölçüm ve bekleme cümlesi aynı. Anahtar Anahtar Zinciri'nden (öğe adı istekte; anahtar dosyaya/komut satırına yazılmaz).
ARAC_TUR_EN_COK = 8  # bir soruda en çok model çağrısı (son çağrıda araç kapalı → cevap)
OKU_SATIR, OKU_KAR, ARA_SATIR = 400, 40000, 60
CLAUDE_ADI = {"ara": "Grep", "oku": "Read", "listele": "Glob"}
GORUNTU_UZ = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tif", ".tiff", ".bmp", ".pdf"}
_TR = str.maketrans({"İ": "i", "I": "ı", "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
def katla(t): return t.replace("İ", "i").replace("I", "ı").lower().translate(_TR)

def anahtar_oku(ad):  # Anahtar Zinciri → anahtar ("" = yok). Deneme: SUFLOR_TEST_BEYIN_ANAHTAR
    if os.environ.get("SUFLOR_TEST_BEYIN_ANAHTAR") is not None: return os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"]
    if not ad or not re.match(r"^[A-Za-z0-9._-]{1,64}$", str(ad)): return ""
    try: return subprocess.run(["/usr/bin/security", "find-generic-password", "-s", str(ad), "-w"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): return ""

def istem_uyarla(t):  # Claude Code araç adları → Suflor'un araçları (istem ve bağlam bloğundaki yönergeler; Grep seçenekleri burada yok)
    t = re.sub(r"\s*\(?output_mode content, -i, head_limit 60, ", " (", t)
    t = re.sub(r"\bRead, Grep, Glob\b", "oku, ara, listele", t)
    t = re.sub(r"\bGrep/Glob/Read\b", "ara/listele/oku", t)
    t = re.sub(r"\bGrep\b", "ara", t); t = re.sub(r"\bGlob\b", "listele", t)
    return re.sub(r"\bRead(?= ile| aracı| the| that| around|,)", "oku", t)
ARAC_NOTU = {"tr": ("\n\n[Araçlar] ara(sorgu): proje dizininde arar (sözcük + anlam), en iyi parçaları dosya yolu ve konumuyla verir; ara(sorgu, dosya): yalnız o dosyada "
                    "sözcüklerden birini içeren satırları satır numarasıyla verir (büyük/küçük harf ve Türkçe harf farkı yok; boşlukla ya da | ile birden çok sözcük). "
                    "oku(yol, satir, adet): dosyayı satır numaralı okur. listele(desen): dosya adı deseni (ör. **/*.md). Yollar proje klasörüne göre ya da tam yol. "
                    "Araçlar yalnız okur; dosyaya yazamaz, komut çalıştıramaz."),
             "en": ("\n\n[Tools] ara(sorgu): searches the project index (words + meaning), returns the best passages with path and position; ara(sorgu, dosya): lines in "
                    "that file containing any of the words, with line numbers (case and Turkish letters ignored; several words separated by spaces or |). "
                    "oku(yol, satir, adet): reads a file with line numbers. listele(desen): file-name pattern (e.g. **/*.md). Paths relative to the project folder or absolute. "
                    "Tools only read; they can't write files or run commands.")}

def arac_tanimlari(mcp_araclar=()):
    t = [{"type": "function", "function": {"name": "ara", "description": "Proje dizininde ya da tek bir dosyada ara (salt okunur).",
          "parameters": {"type": "object", "properties": {"sorgu": {"type": "string", "description": "aranacak sözcükler"},
                         "dosya": {"type": "string", "description": "isteğe bağlı: yalnız bu dosyada satır ara"},
                         "n": {"type": "integer", "description": "dizinde en çok sonuç (varsayılan 8)"}}, "required": ["sorgu"]}}},
         {"type": "function", "function": {"name": "oku", "description": "Bir dosyayı satır numaralı oku (salt okunur).",
          "parameters": {"type": "object", "properties": {"yol": {"type": "string"}, "satir": {"type": "integer", "description": "başlangıç satırı (1'den)"},
                         "adet": {"type": "integer", "description": f"satır sayısı (en çok {OKU_SATIR * 2})"}}, "required": ["yol"]}}},
         {"type": "function", "function": {"name": "listele", "description": "Dosya adı desenine uyan dosyalar (en yeni önce).",
          "parameters": {"type": "object", "properties": {"desen": {"type": "string"}}, "required": ["desen"]}}}]
    for a in mcp_araclar:
        t.append({"type": "function", "function": {"name": a["name"], "description": str(a.get("description") or "")[:1000],
                  "parameters": a.get("inputSchema") or {"type": "object", "properties": {}}}})
    return t

class Araclar:  # salt okunur, kök sınırlı
    def __init__(self, kokler, cwd, kod=None):
        self.kokler = [os.path.realpath(os.path.expanduser(k)) for k in kokler if k]; self.cwd = os.path.expanduser(cwd or (kokler or ["/"])[0])
        self.kod = kod or os.path.dirname(os.path.dirname(os.path.abspath(__file__))); self._baglam = None
    def yol(self, y):  # → gerçek yol ya da None (kök dışı, sembolik bağla kaçış)
        y = os.path.expanduser(str(y or "").strip())
        if not y: return None
        g = os.path.realpath(y if os.path.isabs(y) else os.path.join(self.cwd, y))
        return g if any(g == k or g.startswith(k + os.sep) for k in self.kokler) else None
    def baglam(self):
        if self._baglam is None:
            try:
                import importlib.util; sys.dont_write_bytecode = True
                sp = importlib.util.spec_from_file_location("suflor_baglam", os.path.join(self.kod, "baglam.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); self._baglam = m
            except Exception as e: sys.stderr.write(f"BEYİN: baglam.py yüklenemedi ({e.__class__.__name__})\n"); self._baglam = False
        return self._baglam or None
    def gizli(self, metin):
        m = self.baglam()
        try: return m.gizli_bilgi(metin) if m and hasattr(m, "gizli_bilgi") else None
        except Exception: return None
    def ara(self, sorgu="", dosya=None, n=8):
        sorgu = str(sorgu or "").strip()
        if not sorgu: return "sorgu boş"
        if dosya:
            g = self.yol(dosya)
            if not g or not os.path.isfile(g): return f"dosya yok ya da izinli klasörlerin dışında: {dosya}"
            ks = [katla(k) for k in re.split(r"[\s|]+", re.sub(r"\\[bswd]|[\\^$()\[\]{}.*+?]", " ", sorgu)) if len(k) >= 2]
            if not ks: return "aranacak sözcük yok"
            try: sat = open(g, encoding="utf-8", errors="replace").read().splitlines()
            except OSError as e: return f"okunamadı ({e.__class__.__name__})"
            bul = [(i, s) for i, s in enumerate(sat, 1) if any(k in katla(s) for k in ks)]
            o = [f"{i}:{s[:400]}" for i, s in bul[:ARA_SATIR]]
            if self.gizli("\n".join(o)): return "sonuçta gizli bilgi işareti var (şifre/kart/IBAN) — gösterilmedi"
            return ("\n".join(o) + (f"\n(sonuç kesildi: {len(bul)} satırın {ARA_SATIR}'ı; sözcükleri daralt)" if len(bul) > ARA_SATIR else "")) if o else "eşleşme yok"
        m = self.baglam()
        if not m: return "dizin kullanılamıyor"
        try: rows, ek = m.ara(sorgu, n=max(1, min(int(n or 8), 15)), guncel=False)
        except Exception as e: return f"arama hatası ({e.__class__.__name__})"
        if not rows: return "sonuç yok"
        o = [f"[{i}] {tur} · {tarih} · {baslik} · {yol}{(' @' + konum) if konum else ''}{(' · ' + kim) if kim else ''}\n    {m.kesit(metin, sorgu, ek, 500)}"
             for i, (pid, yol, konum, kim, metin, tur, tarih, baslik, s) in enumerate(rows, 1)]
        return "\n".join(x for x in o if not self.gizli(x)) or "sonuç yok"
    def oku(self, yol="", satir=1, adet=None):
        g = self.yol(yol)
        if not g: return f"dosya izinli klasörlerin dışında ya da yol boş: {yol}"
        if os.path.isdir(g): return "bu bir klasör; listele aracını kullan"
        if not os.path.isfile(g): return f"dosya yok: {yol}"
        if os.path.splitext(g)[1].lower() in GORUNTU_UZ: return "görüntü/PDF bu araçla okunamaz; bağlamdaki metin satırlarına ya da ara aracına bak"
        try:
            with open(g, "rb") as f: b = f.read(4_000_000)
        except OSError as e: return f"okunamadı ({e.__class__.__name__})"
        if b"\x00" in b[:8000]: return "metin dosyası değil; ara aracıyla dizinde ara"
        sat = b.decode("utf-8", errors="replace").splitlines()
        try: bas = max(1, int(satir or 1)); n = max(1, min(int(adet or OKU_SATIR), OKU_SATIR * 2))
        except (TypeError, ValueError): bas, n = 1, OKU_SATIR
        o, kar = [], 0
        for i in range(bas, min(len(sat), bas + n - 1) + 1):
            x = f"{i:>6}\t{sat[i - 1][:1000]}"; kar += len(x)
            if kar > OKU_KAR: o.append(f"(kesildi; devamı için satir={i})"); break
            o.append(x)
        if not o: return f"dosya {len(sat)} satır; {bas}. satır yok"
        m = self.gizli("\n".join(o))
        return f"bu bölümde gizli bilgi işareti var ({m}) — gösterilmedi" if m else "\n".join(o)
    def listele(self, desen=""):
        desen = str(desen or "").strip()
        if not desen or ".." in desen.split("/"): return "desen boş ya da izinli değil"
        taban = desen if os.path.isabs(os.path.expanduser(desen)) else os.path.join(self.cwd, desen)
        bul = []
        for y in _glob.iglob(os.path.expanduser(taban), recursive=True):
            if "/.git/" in y or not os.path.isfile(y) or not self.yol(y): continue
            bul.append(y)
            if len(bul) >= 2000: break
        bul.sort(key=lambda y: -os.path.getmtime(y))
        rel = [os.path.relpath(y, self.cwd) if y.startswith(self.cwd + os.sep) else y for y in bul[:100]]
        return "\n".join(rel) + (f"\n(ilk 100; toplam {len(bul)})" if len(bul) > 100 else "") if rel else "eşleşme yok"

def mcp_dogrula(yapi_yolu, kod, istek_klasor):  # → (komut, ortam) ya da None: yalnız toplanti-claude.py vt-mcp (Brifing.app'in konus-mcp.json denetimiyle aynı)
    try:
        if os.path.realpath(yapi_yolu) != os.path.join(os.path.realpath(istek_klasor), "konus-mcp.json"): return None
        o = json.load(open(yapi_yolu, encoding="utf-8")); v = o["mcpServers"]["suflorvt"]
        if set(o) != {"mcpServers"} or set(o["mcpServers"]) != {"suflorvt"} or v.get("command") != "/usr/bin/python3": return None
        a = v.get("args") or []
        if len(a) != 6 or a[:2] != ["-I", "-B"] or os.path.realpath(a[2]) != os.path.realpath(os.path.join(kod, "toplanti-claude.py")) or a[3] != "--dir" \
           or os.path.realpath(a[4]) != os.path.realpath(istek_klasor) or a[5] != "vt-mcp": return None
        e = v.get("env") or {}
        if not set(e) <= {"PYTHONDONTWRITEBYTECODE", "SUFLOR_VT_SEMA_YOK", "SUFLOR_AYAR"} or not all(isinstance(x, str) for x in e.values()): return None
        return ["/usr/bin/python3"] + a, e
    except (OSError, ValueError, KeyError, TypeError, AttributeError): return None

class Mcp:  # istemci tarafında MCP (stdio, satır başına JSON-RPC)
    def __init__(self, komut, ortam=None):
        self.p = subprocess.Popen(komut, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=dict(os.environ, **(ortam or {})), bufsize=1)
        self.n = 0; self.kilit = threading.Lock()
        self.istek("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "suflor-beyin", "version": "1"}})
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); self.p.stdin.flush()
        self.araclar = (self.istek("tools/list", {}) or {}).get("tools") or []
    def istek(self, yontem, param):
        with self.kilit:
            self.n += 1; self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": yontem, "params": param}) + "\n"); self.p.stdin.flush()
            for l in self.p.stdout:
                try: m = json.loads(l)
                except ValueError: continue
                if m.get("id") == self.n:
                    if m.get("error"): raise RuntimeError(str(m["error"].get("message"))[:300])
                    return m.get("result")
            raise RuntimeError("araç sunucusu kapandı")
    def cagir(self, ad, arg):
        r = self.istek("tools/call", {"name": ad, "arguments": arg}) or {}
        return "\n".join(str(x.get("text") or "") for x in r.get("content") or [] if isinstance(x, dict))
    def kapat(self):
        try: self.p.stdin.close(); self.p.wait(timeout=3)
        except Exception: self.p.kill()

class Baglanti:  # kalıcı HTTP(S) bağlantısı (TLS el sıkışması her soruda tekrarlanmasın); kopunca bir kez yeniden
    def __init__(self, adres, anahtar, zaman=120):
        u = urllib.parse.urlsplit(adres); self.https = u.scheme == "https"; self.host, self.port = u.hostname, u.port; self.yol = u.path.rstrip("/")
        self.anahtar = anahtar; self.zaman = zaman; self.c = None; self.kilit = threading.Lock()
    def _ac(self):
        self.c = http.client.HTTPSConnection(self.host, self.port, timeout=self.zaman, context=ssl.create_default_context()) if self.https else \
            http.client.HTTPConnection(self.host, self.port, timeout=self.zaman)
        self.c.connect()
    def isit(self):
        with self.kilit:
            try:
                if self.c is None: self._ac()
            except (OSError, http.client.HTTPException): self.c = None
    def post(self, yol, govde, akis=True):
        b = json.dumps(govde, ensure_ascii=False).encode()
        h = {"Content-Type": "application/json", "Accept": "text/event-stream" if akis else "application/json"}
        if self.anahtar: h["Authorization"] = "Bearer " + self.anahtar
        with self.kilit:
            for deneme in (0, 1):
                try:
                    if self.c is None: self._ac()
                    self.c.request("POST", self.yol + yol, body=b, headers=h); return self.c.getresponse()
                except (OSError, http.client.HTTPException):
                    try: self.c.close()
                    except Exception: pass
                    self.c = None
                    if deneme: raise
    def kapat(self):
        try: self.c and self.c.close()
        except Exception: pass

def http_hatasi(kod, govde):  # → kısa hata metni (sağlayıcının iletisi; yoksa gövdenin başı)
    try: m = (json.loads(govde) if govde.strip().startswith(("{", "[")) else {})
    except ValueError: m = {}
    m = m[0] if isinstance(m, list) and m else m
    return f"HTTP {kod}: {str((m.get('error') or {}).get('message') if isinstance(m, dict) and isinstance(m.get('error'), dict) else '') or govde[:200]}"[:300]

def sse(r):  # SSE satırları → JSON parçaları ([DONE]'da biter; yanıt sonuna kadar okunur ki bağlantı yeniden kullanılsın)
    while True:
        l = r.readline()
        if not l: return
        l = l.decode("utf-8", errors="replace").strip()
        if not l.startswith("data:"): continue
        d = l[5:].strip()
        if d == "[DONE]": r.read(); return
        try: yield json.loads(d)
        except ValueError: continue

def _js(a):
    try: o = json.loads(a or "{}"); return o if isinstance(o, dict) else {}
    except ValueError: return {}

class Oturum:  # Konuş'un açık süreci: kullanıcı iletisi başına araç döngüsü, Claude Code stream-json olayları
    def __init__(self, istek, cikis=None, mcp=None, baglanti=None):
        self.b = istek["beyin"]; self.out = cikis or sys.stdout; self.kimlik = str(uuid.uuid4()); self.maliyet = 0.0
        self.arac_var = istek.get("araclar", True) is not False  # Aşama 2: çeviri araçsız (araclar: false — araç tanımı, araç notu ve istem uyarlaması yok)
        self.araclar = Araclar(istek.get("kokler") or [], istek.get("cwd"))
        self.mcp = mcp if self.arac_var else None; self.mcp_adlar = {a["name"] for a in (self.mcp.araclar if self.mcp else [])}
        self.tanim = arac_tanimlari(self.mcp.araclar if self.mcp else ()) if self.arac_var else []
        dil = "en" if istek.get("dil") == "en" else "tr"
        self.gecmis = [{"role": "system", "content": istem_uyarla(str(istek.get("sistem") or "")) + ARAC_NOTU[dil] if self.arac_var else str(istek.get("sistem") or "")}]
        self.http = baglanti or Baglanti(self.b["adres"], anahtar_oku(self.b.get("anahtar")))
        threading.Thread(target=self.http.isit, daemon=True).start()  # Claude Code'un önceden açılan süreci gibi: bağlantı ilk sorudan önce hazır
    def yaz(self, o): self.out.write(json.dumps(o, ensure_ascii=False) + "\n"); self.out.flush()
    def ev(self, e): self.yaz({"type": "stream_event", "event": e, "session_id": self.kimlik})
    def calistir(self, ad, arg):
        try:
            if ad in self.mcp_adlar: return self.mcp.cagir(ad, arg)
            if ad == "ara": return self.araclar.ara(arg.get("sorgu"), arg.get("dosya"), arg.get("n") or 8)
            if ad == "oku": return self.araclar.oku(arg.get("yol") or arg.get("file_path"), arg.get("satir") or 1, arg.get("adet"))
            if ad == "listele": return self.araclar.listele(arg.get("desen") or arg.get("pattern"))
            return f"bilinmeyen araç: {ad}"
        except Exception as e: return f"araç hatası ({e.__class__.__name__}: {str(e)[:200]})"
    def claude_adi(self, ad): return "mcp__suflorvt__" + ad if ad in self.mcp_adlar else CLAUDE_ADI.get(ad, ad)
    def _cagri(self, son):  # bir model çağrısı → (metin, araç çağrıları, kullanım, bitiş nedeni)
        g = {"model": self.b["model"], "messages": self.gecmis, "stream": True, "stream_options": {"include_usage": True}}
        if self.tanim: g["tools"] = self.tanim
        if son and self.tanim: g["tool_choice"] = "none"
        if self.b.get("effort"): g["reasoning_effort"] = self.b["effort"]
        r = self.http.post("/chat/completions", g)
        if r.status != 200: raise RuntimeError(http_hatasi(r.status, r.read().decode("utf-8", errors="replace")))
        self.ev({"type": "message_start", "message": {"model": self.b["model"], "role": "assistant"}})
        acik = {"i": -1, "tur": None}; metin, araclar, u, neden = "", {}, {}, None
        def kapat():
            if acik["tur"]: self.ev({"type": "content_block_stop", "index": acik["i"]}); acik["tur"] = None
        def blok(tur, cb):
            if acik["tur"] == tur and tur != "tool_use": return
            kapat(); acik["i"] += 1; acik["tur"] = tur; self.ev({"type": "content_block_start", "index": acik["i"], "content_block": cb})
        for c in sse(r):
            if c.get("usage"): u = c["usage"]
            for ch in c.get("choices") or []:
                d = ch.get("delta") or {}; neden = ch.get("finish_reason") or neden
                dus = d.get("reasoning_content") or d.get("reasoning")
                if isinstance(dus, str) and dus:
                    blok("thinking", {"type": "thinking", "thinking": ""}); self.ev({"type": "content_block_delta", "index": acik["i"], "delta": {"type": "thinking_delta", "thinking": dus}})
                if isinstance(d.get("content"), str) and d["content"]:
                    blok("text", {"type": "text", "text": ""}); metin += d["content"]
                    self.ev({"type": "content_block_delta", "index": acik["i"], "delta": {"type": "text_delta", "text": d["content"]}})
                for tc in d.get("tool_calls") or []:
                    f = tc.get("function") or {}; k = tc.get("index")
                    if k is None: k = next((x for x, a in araclar.items() if tc.get("id") and a["id"] == tc.get("id")), len(araclar))
                    if k not in araclar:
                        araclar[k] = {"id": tc.get("id") or f"call_{uuid.uuid4().hex[:12]}", "ad": f.get("name") or "", "arg": "", "ek": tc.get("extra_content")}
                        blok("tool_use", {"type": "tool_use", "id": araclar[k]["id"], "name": self.claude_adi(araclar[k]["ad"]), "input": {}}); araclar[k]["blok"] = acik["i"]
                    a = araclar[k]
                    if tc.get("extra_content"): a["ek"] = tc["extra_content"]  # Gemini 3: düşünce imzası araç sonucuyla geri gider
                    if f.get("arguments"):
                        a["arg"] += f["arguments"] if isinstance(f["arguments"], str) else json.dumps(f["arguments"], ensure_ascii=False)
                        if acik["tur"] == "tool_use" and acik["i"] == a["blok"]:
                            self.ev({"type": "content_block_delta", "index": a["blok"], "delta": {"type": "input_json_delta", "partial_json": f["arguments"] if isinstance(f["arguments"], str) else json.dumps(f["arguments"], ensure_ascii=False)}})
        kapat(); self.ev({"type": "message_stop"})
        bl = ([{"type": "text", "text": metin}] if metin else []) + [{"type": "tool_use", "id": a["id"], "name": self.claude_adi(a["ad"]), "input": _js(a["arg"])} for _, a in sorted(araclar.items())]
        if bl: self.yaz({"type": "assistant", "message": {"model": self.b["model"], "role": "assistant", "content": bl}, "session_id": self.kimlik})  # Claude Code gibi: çeviri okuyucusu bunu bekler
        return metin, [araclar[k] for k in sorted(araclar)], u, neden
    def soru(self, icerik):  # bir kullanıcı iletisi → olaylar + sonuç satırı
        t0 = time.time(); api_ms = 0; n = 0; top = {"giris": 0, "okunan": 0, "cikis": 0}; metin_hepsi = ""; hata = None; bas = len(self.gecmis)
        self.yaz({"type": "system", "subtype": "init", "model": self.b["model"], "session_id": self.kimlik, "tools": [self.claude_adi(t["function"]["name"]) for t in self.tanim],
                  "saglayici": self.b.get("saglayici")})
        self.gecmis.append({"role": "user", "content": istem_uyarla(icerik) if self.arac_var else icerik})
        try:
            while n < ARAC_TUR_EN_COK:
                n += 1; t1 = time.time()
                metin, araclar, u, _ = self._cagri(son=n == ARAC_TUR_EN_COK); api_ms += round((time.time() - t1) * 1000); metin_hepsi += metin
                gi = int(u.get("prompt_tokens") or 0); ok = int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0); ci = int(u.get("completion_tokens") or 0)
                top["giris"] += gi - ok; top["okunan"] += ok; top["cikis"] += ci
                f = self.b.get("fiyat")
                if f: self.maliyet += ((gi - ok) * f[0] + ok * f[1] + ci * f[2]) / 1e6
                if not araclar: self.gecmis.append({"role": "assistant", "content": metin}); break
                self.gecmis.append({"role": "assistant", "content": metin or "", "tool_calls": [dict({"id": a["id"], "type": "function", "function": {"name": a["ad"], "arguments": a["arg"] or "{}"}},
                                                                                                    **({"extra_content": a["ek"]} if a.get("ek") else {})) for a in araclar]})
                for a in araclar:
                    try: arg = json.loads(a["arg"] or "{}")
                    except ValueError: arg = {}
                    s = self.calistir(a["ad"], arg if isinstance(arg, dict) else {})
                    self.yaz({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": a["id"], "content": s}]}, "session_id": self.kimlik})
                    self.gecmis.append({"role": "tool", "tool_call_id": a["id"], "name": a["ad"], "content": s})
        except Exception as e:
            hata = f"{self.b.get('saglayici') or 'sağlayıcı'}: {e.__class__.__name__ if not isinstance(e, RuntimeError) else ''} {e}".replace("  ", " ").strip()
            del self.gecmis[bas:]; sys.stderr.write(f"BEYİN: hata — {hata}\n")
        self.yaz({"type": "result", "subtype": "error_during_execution" if hata else "success", "is_error": bool(hata), "result": hata or metin_hepsi, "num_turns": n,
                  "duration_ms": round((time.time() - t0) * 1000), "duration_api_ms": api_ms, "session_id": self.kimlik, "total_cost_usd": round(self.maliyet, 6),
                  "usage": {"input_tokens": top["giris"], "cache_read_input_tokens": top["okunan"], "cache_creation_input_tokens": 0, "output_tokens": top["cikis"]}})
    def calis(self, giris):
        for l in giris:
            try: j = json.loads(l)
            except ValueError: continue
            if j.get("type") != "user": continue
            c = (j.get("message") or {}).get("content")
            c = c if isinstance(c, str) else "".join(str(x.get("text") or "") for x in c or [] if isinstance(x, dict) and x.get("type") == "text")
            if c.strip(): self.soru(c)

# --- tek çağrı (Aşama 2): proje kartı (JSON kipi), telaffuz; araçsız, akışsız. Sonuç Claude Code'un --output-format json satırı biçiminde
# (result, is_error, usage, total_cost_usd, duration_ms): okuyucular (proje-karti.py, brifing-ses.py claude_json) aynı. Hata istisna değil, is_error.
TEK_ZAMAN = 180
def tek_cagri(b, istem, sistem=None, json_kip=False, zaman=TEK_ZAMAN, baglanti=None):
    t0 = time.time(); http_ = baglanti or Baglanti(b["adres"], anahtar_oku(b.get("anahtar")), zaman); metin, hata, u, api_ms = "", None, {}, 0
    g = {"model": b["model"], "messages": ([{"role": "system", "content": sistem}] if sistem else []) + [{"role": "user", "content": istem}], "stream": False}
    if b.get("effort"): g["reasoning_effort"] = b["effort"]
    if json_kip: g["response_format"] = {"type": "json_object"}
    try:
        while True:
            t1 = time.time(); r = http_.post("/chat/completions", g, akis=False); govde = r.read().decode("utf-8", errors="replace"); api_ms += round((time.time() - t1) * 1000)
            if r.status == 400 and "response_format" in g: g.pop("response_format"); continue  # JSON kipini tanımayan sağlayıcı: istemdeki "yalnız JSON" kuralı yeter
            if r.status != 200: raise RuntimeError(http_hatasi(r.status, govde))
            j = json.loads(govde); break
        m = ((j.get("choices") or [{}])[0] or {}).get("message") or {}; c = m.get("content")
        metin = c if isinstance(c, str) else "".join(str(x.get("text") or "") for x in c or [] if isinstance(x, dict))
        u = j.get("usage") or {}
        if not metin.strip(): hata = f"{b.get('saglayici') or 'sağlayıcı'}: boş cevap"
    except Exception as e:
        hata = f"{b.get('saglayici') or 'sağlayıcı'}: {e.__class__.__name__ if not isinstance(e, RuntimeError) else ''} {e}".replace("  ", " ").strip()[:300]
    finally:
        if not baglanti: http_.kapat()
    gi = int(u.get("prompt_tokens") or 0); ok = int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0); ci = int(u.get("completion_tokens") or 0)
    f = b.get("fiyat"); maliyet = ((gi - ok) * f[0] + ok * f[1] + ci * f[2]) / 1e6 if f else 0.0
    return {"type": "result", "subtype": "error_during_execution" if hata else "success", "is_error": bool(hata), "result": hata or metin, "num_turns": 1,
            "duration_ms": round((time.time() - t0) * 1000), "duration_api_ms": api_ms, "total_cost_usd": round(maliyet, 6), "model": b["model"], "saglayici": b.get("saglayici"),
            "usage": {"input_tokens": gi - ok, "cache_read_input_tokens": ok, "cache_creation_input_tokens": 0, "output_tokens": ci}}
def tek_istek(ayar, is_, istem, sistem=None, json_kip=False):  # `beyin.py tek <istek>` (aktarıcı alt süreçle çalıştırır: ağa aktarıcının kendisi bağlanmaz)
    b = secim(ayar, is_)
    return {"beyin": {k: b.get(k) for k in ("tur", "model", "saglayici", "adres", "anahtar", "effort", "fiyat")}, "is": is_, "istem": istem, "sistem": sistem, "json": bool(json_kip)}
def tek_main(istek_yolu):
    istek = json.load(open(istek_yolu, encoding="utf-8")); b = istek.get("beyin") or {}
    if b.get("tur") != "openai-uyumlu" or not adres_uygun(b.get("adres")) or not b.get("model"): sys.stderr.write("BEYİN: istek uygun değil\n"); return 3
    sys.stdout.write(json.dumps(tek_cagri(b, str(istek.get("istem") or ""), istek.get("sistem"), bool(istek.get("json")), int(istek.get("zaman") or TEK_ZAMAN)), ensure_ascii=False) + "\n")
    return 0
def ceviri_istek(ayar, sistem, dil="tr"):  # çevirinin açık süreci (`beyin.py calis`, Brifing.app'siz: dosya okumaz): araçsız
    b = secim(ayar, "ceviri")
    return {"beyin": {k: b.get(k) for k in ("tur", "model", "saglayici", "adres", "anahtar", "effort", "fiyat")}, "sistem": sistem, "araclar": False, "kokler": [], "cwd": "/", "dil": dil}

def konus_istek(ayar, sistem, mcp, kokler, cwd, giris, cikis, dil="tr", sure=7200):  # Brifing.app --beyin isteği (anahtarın kendisi yok, yalnız öğe adı)
    b = secim(ayar, "konus")
    return {"beyin": {k: b.get(k) for k in ("tur", "model", "saglayici", "adres", "anahtar", "effort", "fiyat")}, "sistem": sistem, "mcp": mcp,
            "kokler": [os.path.expanduser(k) for k in kokler if k], "cwd": os.path.expanduser(cwd), "giris": giris, "cikis": cikis, "dil": dil, "sure": sure,
            **({"ayar": os.environ["SUFLOR_AYAR"]} if os.environ.get("SUFLOR_AYAR") else {})}

def calis_main(istek_yolu):
    istek = json.load(open(istek_yolu, encoding="utf-8")); b = istek.get("beyin") or {}
    if b.get("tur") != "openai-uyumlu" or not adres_uygun(b.get("adres")) or not b.get("model"): sys.stderr.write("BEYİN: istek uygun değil\n"); return 3
    kod = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); mcp = None
    if istek.get("ayar"): os.environ["SUFLOR_AYAR"] = str(istek["ayar"])  # deneme aktarıcısı (Brifing.app yalnız deneme derlemesinde kabul eder)
    if istek.get("mcp") and istek.get("araclar", True) is not False:
        d = mcp_dogrula(istek["mcp"], kod, os.path.dirname(os.path.realpath(istek_yolu)))
        if not d: sys.stderr.write("BEYİN: araç sunucusu yapılandırması reddedildi\n")
        else:
            try: mcp = Mcp(*d)
            except Exception as e: sys.stderr.write(f"BEYİN: araç sunucusu açılamadı ({e.__class__.__name__})\n")
    o = Oturum(istek, mcp=mcp)
    try: o.calis(sys.stdin)
    finally:
        o.http.kapat()
        if mcp: mcp.kapat()
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "calis": sys.exit(calis_main(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == "tek": sys.exit(tek_main(sys.argv[2]))
    sys.exit("kullanım: beyin.py calis|tek <istek.json>")
