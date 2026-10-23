# Suflor.me beyin katmanı (Aşama 0, v0.121.1; tasarım ~/Desktop/Suflor/planlar/beyin-saglayici.md): yapay zekâ çağrılarının tek giriş noktası.
# Ayrı modüldür (relay.py'nin ad alanında bölüm olarak çalışmaz): aktarıcı (brifing-ses.py BEYIN) ve proje-karti.py importlib ile yükler. Python 3.9 uyumlu.
# İşler: konus, ceviri, telaffuz, brifing, proje_karti. Toplantı oturumu bilerek dışarıda (K3: Claude Code'da kalır, aktarici/toplanti-oturum.py).
# Bugün tek uyarlayıcı var: claude-code (`claude -p`; abonelik, önbellek tam). Çıktı Claude Code'un json / stream-json biçimidir ve iç protokol olarak
# kalır: okuyucular (bas-konus.py _konus_oku, ceviri.py, brifing-ses.py claude_json) sağlayıcı değişse de aynı satırları okur.
# Ayar (isteğe bağlı): "beyin": {"varsayilan": {"tur": "claude-code"}, "<iş>": {"tur": …, "model": …}}. Yoksa eski anahtarlar (konus_model,
# ceviri_model, kart_model, claude_model) ve bugünkü varsayılanlar — ayarsız kurulumda argümanlar v0.121.0'dakiyle birebir aynı (test/beyin.py).
import json, os, shutil, subprocess, sys

UYARLAYICILAR = ("claude-code",)
ISLER = ("konus", "ceviri", "telaffuz", "brifing", "proje_karti")
VARSAYILAN_MODEL = {"konus": "sonnet", "ceviri": "haiku", "telaffuz": "sonnet", "brifing": None, "proje_karti": "sonnet"}
ESKI_ANAHTAR = {"konus": "konus_model", "ceviri": "ceviri_model", "brifing": "claude_model", "proje_karti": "kart_model"}
_UYARILDI = set()

def secim(ayar, is_):  # → {"tur": uyarlayıcı, "model": ad ya da None}
    b = ayar.get("beyin") if isinstance(ayar.get("beyin"), dict) else {}
    s = {}
    for k in ("varsayilan", is_):
        if isinstance(b.get(k), dict): s.update(b[k])
    tur = str(s.get("tur") or "claude-code")
    if tur not in UYARLAYICILAR:  # Aşama 0: başka uyarlayıcı yok — bugünkü yol, bir kez uyarı
        if (is_, tur) not in _UYARILDI: _UYARILDI.add((is_, tur)); sys.stderr.write(f"BEYİN: '{tur}' uyarlayıcısı yok ({is_}) — claude-code kullanılıyor\n")
        tur = "claude-code"
    model = s.get("model") or ayar.get(ESKI_ANAHTAR.get(is_) or "") or VARSAYILAN_MODEL.get(is_)
    return {"tur": tur, "model": str(model) if model else None}

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
def konus_args(ayar, sistem, ek_araclar="", mcp=None, ek_dizin=None):  # açık süreç (Brifing.app FIFO kipi): stream-json giriş/çıkış, parça parça metin
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--allowedTools", "Read,Grep,Glob" + ("," + ek_araclar if ek_araclar else ""), "--add-dir", ek_dizin, "--append-system-prompt", sistem] + (["--mcp-config", mcp] if mcp else []) + \
           (yalin(ayar) or ["--no-session-persistence"]) + ["--model", secim(ayar, "konus")["model"]] + konus_onek_ayar(ayar) + konus_effort(ayar)
def ceviri_args(ayar, sistem):  # açık süreç, araçsız (Popen; stdin/stdout stream-json)
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--model", secim(ayar, "ceviri")["model"],
            "--tools", "", "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--system-prompt", sistem]
def telaffuz_args(ayar, istem):  # tek çağrı (Brifing.app), json çıktı
    return ["-p", istem, "--output-format", "json", "--model", secim(ayar, "telaffuz")["model"]] + yalin(ayar)
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
