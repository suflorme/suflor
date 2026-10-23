#!/usr/bin/env python3
# Beyin katmanı Aşama 0 (aktarici/beyin.py, v0.121.1): yapay zekâ çağrılarının argümanları v0.121.0'dakiyle birebir aynı mı (Konuş, çeviri, telaffuz,
# brifing, proje kartı; ayarsız ve eski ayar anahtarlarıyla), "beyin" ayarı (iş başına model, bilinmeyen uyarlayıcı → claude-code), ölçüm alanları,
# Claude yolu, sahte claude ile tek çağrı; çağrı yerlerinde elle kurulmuş `claude -p` argümanı kalmadı mı; __pycache__ yazılmıyor mu.
# Aşama 1 (v0.122.0): openai-uyumlu uyarlayıcı sahte OpenAI uyumlu sunucuya karşı (Google'a gidilmez) — ayar seçimi, adres sınırı, araçlar (kök sınırı,
# sembolik bağ kaçışı, gizli bilgi, Türkçe katlamalı satır arama), MCP istemcisi ve yapılandırma denetimi, araç döngüsü → Claude Code stream-json, düşünce
# imzasının geri gitmesi, önbellek/maliyet, HTTP hatası, bağlantının yeniden kullanılması; Brifing.app --beyin (deneme derlemesi, FIFO) ve reddettikleri.
# Aşama 2: tek çağrı (tek_cagri, `beyin.py tek`: JSON kipi, kipi tanımayan sağlayıcıda kipsiz yeniden, hata is_error, boş cevap), araçsız açık süreç (çeviri:
# araç tanımı/notu yok, assistant olayı), iş başına destek, yedek seçimi (claude_secim, yedek_var, yedek: false, günlük satırı).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/beyin.py      (~15 sn; kaldı → çıkış 1)
import contextlib, http.server, importlib.util, io, json, os, re, shutil, socket, subprocess, sys, tempfile, threading, time

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("beyin_t", os.path.join(KOD, "aktarici", "beyin.py")); BY = importlib.util.module_from_spec(sp); sp.loader.exec_module(BY)
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)

# --- v0.121.0'daki ifadeler (çağrı yerlerinden kopya; karşılaştırma tabanı) ---
def eski_yalin(A):
    return ["--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--tools", "Read,Grep,Glob"] if A.get("claude_yalin", True) else []
def eski_effort(A):
    e = str(A.get("konus_effort") or "").strip().lower()
    return ["--effort", e] if e in ("low", "medium", "high", "xhigh", "max") else []
def eski_onek(A):
    if A.get("konus_onek_sabit", True) is False: return []
    return ["--settings", json.dumps({"env": {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS": "1"}})]
def eski_konus(A, istem, vt, BASE, VT="mcp__suflorvt__vt_sema,mcp__suflorvt__vt_sor"):
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--allowedTools", "Read,Grep,Glob" + ("," + VT if vt else ""), "--add-dir", BASE, "--append-system-prompt", istem] + (["--mcp-config", vt] if vt else []) + \
           (eski_yalin(A) or ["--no-session-persistence"]) + ["--model", str(A.get("konus_model") or "sonnet")] + eski_onek(A) + eski_effort(A)
def eski_ceviri(A, istem):
    return ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--model", str(A.get("ceviri_model") or "haiku"),
            "--tools", "", "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--system-prompt", istem]
def eski_telaffuz(A, istem): return ["-p", istem, "--output-format", "json", "--model", "sonnet"] + eski_yalin(A)
def eski_brifing(A, istem, BASE, yalin):
    return ["-p", istem, "--allowedTools", "Read,Grep,Glob", "--add-dir", BASE, "--output-format", "json"] + (eski_yalin(A) if yalin else []) + \
           (["--model", str(A["claude_model"])] if A.get("claude_model") else [])
def eski_kart(model):
    return ["-p", "--output-format", "json", "--model", model, "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--tools", ""]

AYARLAR = [{}, {"claude_yalin": False}, {"konus_model": "opus", "ceviri_model": "sonnet", "claude_model": "opus", "kart_model": "haiku"},
           {"konus_effort": "Low", "konus_onek_sabit": False}, {"konus_effort": "yok"}, {"claude_yalin": True, "konus_effort": "high", "konus_model": "fable"}]
fark = []
for A in AYARLAR:
    for vt in (None, "/x/canli/konus-mcp.json"):
        ek = "mcp__suflorvt__vt_sema,mcp__suflorvt__vt_sor" if vt else ""
        if BY.konus_args(A, "İSTEM", ek, vt, "/x/canli") != eski_konus(A, "İSTEM", vt, "/x/canli"): fark.append(("konus", A, vt))
    if BY.ceviri_args(A, "Çevir") != eski_ceviri(A, "Çevir"): fark.append(("ceviri", A))
    if BY.telaffuz_args(A, "Okunuş") != eski_telaffuz(A, "Okunuş"): fark.append(("telaffuz", A))
    for y in (True, False):
        if BY.brifing_args(A, "Brifing", "/x/canli", y) != eski_brifing(A, "Brifing", "/x/canli", y): fark.append(("brifing", A, y))
    m = BY.secim(A, "proje_karti")["model"]
    if m != (A.get("kart_model") or "sonnet") or BY.kart_args(m) != eski_kart(A.get("kart_model") or "sonnet"): fark.append(("kart", A))
kontrol(f"argümanlar v0.121.0 ile birebir ({len(AYARLAR)} ayar × Konuş/çeviri/telaffuz/brifing/kart)", not fark, str(fark[:3]))

# --- "beyin" ayarı ---
A = {"konus_model": "opus", "beyin": {"varsayilan": {"tur": "claude-code"}, "konus": {"model": "haiku"}, "ceviri": {"tur": "gemini", "model": "x"}}}
kontrol("beyin ayarı: iş başına model eski anahtardan önce", BY.secim(A, "konus") == {"tur": "claude-code", "model": "haiku"}, str(BY.secim(A, "konus")))
e = io.StringIO()
with contextlib.redirect_stderr(e): s1 = BY.secim(A, "ceviri"); s2 = BY.secim(A, "ceviri")
kontrol("bilinmeyen uyarlayıcı → claude-code, tek uyarı", s1["tur"] == "claude-code" and e.getvalue().count("BEYİN:") == 1, e.getvalue())
kontrol("bozuk beyin ayarı (liste/metin) bugünkü yola düşer", BY.secim({"beyin": ["x"], "ceviri_model": "sonnet"}, "ceviri") == {"tur": "claude-code", "model": "sonnet"}
        and BY.secim({"beyin": {"konus": "opus"}}, "konus")["model"] == "sonnet")
AYAR_IS = {"beyin": {"varsayilan": {"tur": "openai-uyumlu", "saglayici": "gemini", "model": "gemini-3.8-flash", "effort": "low"},
               "konus": {"tur": "openai-uyumlu", "saglayici": "ollama", "model": "qwen3.5:4b-q4_K_M"}}}
s3 = BY.secim(AYAR_IS, "konus"); s4 = BY.secim(AYAR_IS, "ceviri") if "ceviri" in BY.DESTEK.get("openai-uyumlu", ()) else None
kontrol("iş başına sağlayıcı: varsayılanın model/effort/saglayici alanı işe sızmaz", s3.get("saglayici") == "ollama" and s3.get("model") == "qwen3.5:4b-q4_K_M"
        and s3.get("effort") is None and (s4 is None or s4.get("saglayici") == "gemini"), f"{s3} {s4}")
kontrol("brifing: model ayarı yoksa --model yok", "--model" not in BY.brifing_args({}, "b", "/x"))

# --- ölçüm ---
j = {"usage": {"input_tokens": 10, "cache_read_input_tokens": 90, "cache_creation_input_tokens": 5, "output_tokens": 7}, "total_cost_usd": 0.0123}
kontrol("kullanim: giriş = giriş + okunan + yazılan; çıktı, maliyet", BY.kullanim(j) == {"giris": 105, "okunan": 90, "cikti": 7, "maliyet": 0.0123}, str(BY.kullanim(j)))
kontrol("kullanim: boş sonuç", BY.kullanim({}) == {"giris": 0, "okunan": 0, "cikti": None, "maliyet": 0})

# --- Claude yolu ve sahte claude ile tek çağrı (sahte uyarlayıcı) ---
T = tempfile.mkdtemp(prefix="suflor-beyin-"); SAHTE = os.path.join(T, "claude")
open(SAHTE, "w").write("#!/usr/bin/env python3\nimport sys, json\ngirdi = sys.stdin.read()\n"
                       "print(json.dumps({'result': 'yankı: ' + girdi.strip(), 'args': sys.argv[1:], 'usage': {'input_tokens': 3, 'output_tokens': 2}, 'total_cost_usd': 0.001}))\n")
os.chmod(SAHTE, 0o755)
kontrol("claude_yolu: ayardaki yol önce", BY.claude_yolu({"claude": SAHTE}) == SAHTE)
kontrol("claude_yolu: çalıştırılamayan ayar yolu atlanır", BY.claude_yolu({"claude": os.path.join(T, "yok")}) != os.path.join(T, "yok"))
r = BY.tek(SAHTE, BY.kart_args("sonnet"), "merhaba", T, 30); o = json.loads(r.stdout)
kontrol("tek: istem stdin'den, argümanlar sırasıyla, json çıktı", o["result"] == "yankı: merhaba" and o["args"] == eski_kart("sonnet") and BY.kullanim(o)["giris"] == 3, r.stdout[:200])

# --- çağrı yerleri katmandan geçiyor ---
oku = lambda y: open(os.path.join(KOD, y), encoding="utf-8").read()
kalan = [y for y in ("aktarici/bas-konus.py", "aktarici/ceviri.py", "aktarici/brifing-ses.py", "proje-karti.py") if re.search(r'"--model",|"--output-format", "(stream-)?json"', oku(y))]
kontrol("Konuş/çeviri/telaffuz/brifing/kart argümanı yalnız beyin.py'de", not kalan, str(kalan))
kontrol("çağrı yerleri BEYIN/BY kullanıyor", all(x in oku(y) for y, x in (("aktarici/bas-konus.py", "BEYIN.konus_args"), ("aktarici/ceviri.py", "BEYIN.ceviri_args"),
        ("aktarici/brifing-ses.py", "BEYIN.telaffuz_args"), ("aktarici/brifing-ses.py", "BEYIN.brifing_args"), ("proje-karti.py", "BY.kart_args"))))
kontrol("toplantı oturumuna dokunulmadı (K3)", "BEYIN" not in oku("aktarici/toplanti-oturum.py"))
kontrol("teshis.py KOD_DOSYALARI'nda beyin.py", '"beyin.py"' in oku("teshis.py"))
kontrol("aktarici/ altında __pycache__ yok", not os.path.exists(os.path.join(KOD, "aktarici", "__pycache__")))

# === Aşama 1: openai-uyumlu ===
kontrol("adres sınırı: https ya da yalnız bu Mac'te http", BY.adres_uygun("https://x.example/v1") and BY.adres_uygun("http://127.0.0.1:11434/v1")
        and not BY.adres_uygun("http://x.example/v1") and not BY.adres_uygun("https://u:p" + chr(64) + "x.example/v1") and not BY.adres_uygun("ftp://x") and not BY.adres_uygun(""))
A = {"gemini_anahtar": "suflor-gcloud", "beyin": {"konus": {"tur": "openai-uyumlu", "saglayici": "gemini", "model": "gemini-3.8-flash", "effort": "low"},
                                                   "ceviri": {"tur": "openai-uyumlu", "saglayici": "gemini", "model": "gemini-3.8-flash"}}}
e = io.StringIO()
with contextlib.redirect_stderr(e): sk, sc = BY.secim(A, "konus"), BY.secim(A, "ceviri")
kontrol("gemini: hazır adres, anahtar öğesi ayardan, fiyat tablodan", sk["tur"] == "openai-uyumlu" and sk["adres"].startswith("https://generativelanguage.googleapis.com/")
        and sk["anahtar"] == "suflor-gcloud" and sk["fiyat"] == [0.75, 0.075, 3.75] or sk["fiyat"] == (0.75, 0.075, 3.75) and sk["effort"] == "low", str(sk))
kontrol("Aşama 2: çeviri de openai-uyumlu; yedekte Claude modeli (gemini adı claude'a gitmez)", sc["tur"] == "openai-uyumlu" and sc["yedek"] is True
        and BY.claude_secim(A, "ceviri") == {"tur": "claude-code", "model": "haiku"} and BY.ceviri_args(A, "Ç", "haiku")[BY.ceviri_args(A, "Ç", "haiku").index("--model") + 1] == "haiku", str(sc))
with contextlib.redirect_stderr(io.StringIO()):
    sb = BY.secim({"beyin": {"brifing": {"tur": "openai-uyumlu", "saglayici": "gemini", "model": "m"}}}, "brifing")
kontrol("sesli brifing (rafta) yalnız claude-code; telaffuz ve proje kartı openai-uyumlu", sb["tur"] == "claude-code" and set(BY.DESTEK["openai-uyumlu"]) == {"konus", "ceviri", "telaffuz", "proje_karti"})
kontrol("yedek_var: Claude Code kurulu ve yedek: false değilse; claude-code seçiminde yok", BY.yedek_var({"claude": SAHTE}, sk) and not BY.yedek_var({"claude": os.path.join(T, "yok"), "PATH": ""}, dict(sk, yedek=False))
        and not BY.yedek_var({"claude": SAHTE}, {"tur": "claude-code"}) and not BY.yedek_var({"claude": SAHTE}, dict(sk, yedek=False)))
y_ = BY.yedek_satiri("ceviri", sk, "HTTP 503:\n çok   yoğun")
kontrol("yedek günlük satırı tek satır, sağlayıcı + model + kısa neden", y_ == "BEYİN: yedek — ceviri: gemini gemini-3.8-flash olmadı (HTTP 503: çok yoğun) → claude-code", y_)
with contextlib.redirect_stderr(io.StringIO()):
    so = BY.secim({"beyin": {"konus": {"tur": "openai-uyumlu", "saglayici": "ollama", "model": "qwen3.5:4b"}}}, "konus")
    sx = BY.secim({"beyin": {"konus": {"tur": "openai-uyumlu", "adres": "http://10.0.0.5/v1", "model": "m"}}}, "konus")
kontrol("ollama: yerel adres, anahtarsız, maliyet 0 (fiyat yok)", so["adres"] == "http://127.0.0.1:11434/v1" and so["saglayici"] == "ollama" and not so["anahtar"] and not so["fiyat"], str(so))
kontrol("yerel ağdaki http adresi reddedilir → claude-code", sx == {"tur": "claude-code", "model": "sonnet"}, str(sx))
kontrol("ayar yoksa Konuş claude-code (varsayılan değişmedi)", BY.secim({}, "konus") == {"tur": "claude-code", "model": "sonnet"})
u = BY.istem_uyarla("gerekirse Read, Grep, Glob ile oku. dökümde Grep ile ara (output_mode content, -i, head_limit 60, en az iki); Read ile aç. Readme dosyası")
kontrol("istem: Claude araç adları Suflor araçlarına, Grep seçenekleri düşer", u == "gerekirse oku, ara, listele ile oku. dökümde ara ile ara (en az iki); oku ile aç. Readme dosyası", u)

# araçlar
K1 = os.path.join(T, "proje"); K2 = os.path.join(T, "canli"); D = os.path.join(T, "dis"); [os.makedirs(x) for x in (K1, K2, D)]
open(os.path.join(K1, "dokum.md"), "w").write("\n".join(["[00:01] Ayşe: Merhaba", "[00:02] Ali: BÜTÇE konusunu konuşalım", "[00:03] Ayşe: ışık ve şemsiye", "[00:04] Ali: tamam"]))
open(os.path.join(D, "gizli.md"), "w").write("dış dosya"); os.symlink(os.path.join(D, "gizli.md"), os.path.join(K1, "bag.md"))
open(os.path.join(K2, "not.txt"), "w").write("şifre: Abc12345!x\n"); open(os.path.join(K1, "resim.png"), "wb").write(b"\x89PNG\x00")
AR = BY.Araclar([K1, K2], K1, kod=KOD)
kontrol("oku: satır numaralı, aralık", AR.oku("dokum.md", 2, 2) == "     2\t[00:02] Ali: BÜTÇE konusunu konuşalım\n     3\t[00:03] Ayşe: ışık ve şemsiye", AR.oku("dokum.md", 2, 2))
kontrol("oku: kök dışı yol, sembolik bağla kaçış, .. reddedilir", "dışında" in AR.oku(os.path.join(D, "gizli.md")) and "dışında" in AR.oku("bag.md") and "dışında" in AR.oku("../dis/gizli.md"))
kontrol("oku: ikinci kök (canli) tam yolla; gizli bilgi gösterilmez", "gösterilmedi" in AR.oku(os.path.join(K2, "not.txt")), AR.oku(os.path.join(K2, "not.txt")))
kontrol("oku: görüntü okunmaz", "okunamaz" in AR.oku("resim.png"))
kontrol("ara(dosya): Türkçe katlamalı, büyük/küçük harf yok, | ile çok sözcük", AR.ara("butce|SEMSIYE", "dokum.md") == "2:[00:02] Ali: BÜTÇE konusunu konuşalım\n3:[00:03] Ayşe: ışık ve şemsiye", AR.ara("butce|SEMSIYE", "dokum.md"))
kontrol("ara(dosya): kök dışı dosya reddedilir", "dışında" in AR.ara("dış", os.path.join(D, "gizli.md")))
kontrol("listele: kökte, sembolik bağ dışarı gitmez", AR.listele("**/*.md") == "dokum.md", AR.listele("**/*.md"))
kontrol("listele: .. reddedilir", "izinli değil" in AR.listele("../dis/*.md"))

# MCP: yapılandırma denetimi ve istemci (sahte sunucu)
tc = os.path.join(KOD, "toplanti-claude.py"); my = os.path.join(K2, "konus-mcp.json")
def mcpyaz(args, env=None, cmd="/usr/bin/python3"): json.dump({"mcpServers": {"suflorvt": {"command": cmd, "args": args, "env": env or {"PYTHONDONTWRITEBYTECODE": "1"}}}}, open(my, "w"))
mcpyaz(["-I", "-B", tc, "--dir", K2, "vt-mcp"]); iyi = BY.mcp_dogrula(my, KOD, K2)
mcpyaz(["-I", "-B", tc, "--dir", K2, "vt-sema"]); k1 = BY.mcp_dogrula(my, KOD, K2)
mcpyaz(["-I", "-B", tc, "--dir", K2, "vt-mcp"], cmd="/bin/sh"); k2 = BY.mcp_dogrula(my, KOD, K2)
mcpyaz(["-I", "-B", tc, "--dir", K2, "vt-mcp"], env={"PATH": "/x"}); k3 = BY.mcp_dogrula(my, KOD, K2)
kontrol("MCP yapılandırması: yalnız toplanti-claude.py vt-mcp, /usr/bin/python3, izinli ortam", iyi and iyi[0][-1] == "vt-mcp" and not k1 and not k2 and not k3 and not BY.mcp_dogrula(my, KOD, K1))
SM = os.path.join(T, "sahte-mcp.py")
open(SM, "w").write("import json,sys\nfor l in sys.stdin:\n m=json.loads(l); i=m.get('id')\n if i is None: continue\n y=m['method']\n"
                    " r={'protocolVersion':'2024-11-05'} if y=='initialize' else {'tools':[{'name':'vt_sor','description':'SELECT','inputSchema':{'type':'object','properties':{'sorgu':{'type':'string'}},'required':['sorgu']}}]} if y=='tools/list'"
                    " else {'content':[{'type':'text','text':'sonuç: '+m['params']['arguments'].get('sorgu','')}]}\n print(json.dumps({'jsonrpc':'2.0','id':i,'result':r}),flush=True)\n")
M = BY.Mcp([sys.executable, SM])
kontrol("MCP istemcisi: tools/list, tools/call", [a["name"] for a in M.araclar] == ["vt_sor"] and M.cagir("vt_sor", {"sorgu": "SELECT 1"}) == "sonuç: SELECT 1")

# sahte OpenAI uyumlu sunucu
GELEN, BAG = [], set(); CEVAP = {"kip": "arac"}
def sse_govde(parcalar): return "".join("data: " + json.dumps(p, ensure_ascii=False) + "\n\n" for p in parcalar) + "data: [DONE]\n\n"
class Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        BAG.add(self.client_address[1]); g = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); GELEN.append({"yol": self.path, "yetki": self.headers.get("Authorization"), "g": g})
        if CEVAP["kip"] == "429":
            b = b'{"error":{"code":429,"message":"Resource exhausted"}}'; self.send_response(429); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if not g.get("stream"):  # tek çağrı (Aşama 2): JSON kipini tanımayan sağlayıcı kipi 400'le reddeder
            if CEVAP.get("kipsiz") and g.get("response_format"):
                b = b'{"error":{"message":"response_format not supported"}}'; self.send_response(400); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
            icerik = "" if CEVAP.get("bos") else json.dumps({"Teams": "Tims"}) if g.get("response_format") or CEVAP.get("kipsiz") else "düz metin"
            b = json.dumps({"choices": [{"message": {"role": "assistant", "content": icerik}}], "usage": {"prompt_tokens": 2000, "completion_tokens": 40, "prompt_tokens_details": {"cached_tokens": 1000}}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        arac_var = any(m.get("role") == "tool" for m in g["messages"][-3:])
        if CEVAP["kip"] == "arac" and not arac_var:  # 1. çağrı: düşünme + parçalı araç çağrısı (index, düşünce imzası)
            p = [{"choices": [{"delta": {"reasoning_content": "dosyaya bakayım"}}]},
                 {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "type": "function", "function": {"name": "ara", "arguments": "{\"sorgu\": \"bütçe\","}, "extra_content": {"google": {"thought_signature": "imza1"}}}]}}]},
                 {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": " \"dosya\": \"dokum.md\"}"}}]}, "finish_reason": "tool_calls"}]},
                 {"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 0}}}]
        else:
            p = [{"choices": [{"delta": {"content": "Bütçe konusunu "}}]}, {"choices": [{"delta": {"content": "Ali açtı.\n---\nKaynak: dokum.md"}, "finish_reason": "stop"}]},
                 {"choices": [], "usage": {"prompt_tokens": 1200, "completion_tokens": 30, "prompt_tokens_details": {"cached_tokens": 1000}}}]
        b = sse_govde(p).encode(); self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
def bos_port():
    s_ = socket.socket(); s_.bind(("127.0.0.1", 0)); p_ = s_.getsockname()[1]; s_.close(); return p_
PORT = bos_port(); SV = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Sahte); SV.handle_error = lambda *a: None; threading.Thread(target=SV.serve_forever, daemon=True).start()
ADRES = f"http://127.0.0.1:{PORT}/v1"
IST = {"beyin": {"tur": "openai-uyumlu", "model": "gemini-3.8-flash", "saglayici": "gemini", "adres": ADRES, "anahtar": "x", "effort": "low", "fiyat": [0.75, 0.075, 3.75]},
       "sistem": "Sen asistansın. Gerekirse Read, Grep, Glob ile oku.", "kokler": [K1, K2], "cwd": K1}
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = "deneme-anahtar"
cik = io.StringIO(); O = BY.Oturum(IST, cikis=cik, mcp=M)
O.calis(io.StringIO(json.dumps({"type": "user", "message": {"role": "user", "content": "Soru: bütçeyi kim açtı?"}}) + "\n"))
ol = [json.loads(l) for l in cik.getvalue().splitlines()]; ev = [x.get("event") or {} for x in ol if x["type"] == "stream_event"]; son = ol[-1]
kontrol("akış: init (model) → message_start → düşünme → tool_use adı Grep → input_json_delta → stop → tool_result → metin → sonuç",
        ol[0]["type"] == "system" and ol[0]["model"] == "gemini-3.8-flash" and [e.get("type") for e in ev][:2] == ["message_start", "content_block_start"]
        and ev[1]["content_block"]["type"] == "thinking" and any(e.get("type") == "content_block_start" and (e.get("content_block") or {}).get("name") == "Grep" for e in ev)
        and "".join((e.get("delta") or {}).get("partial_json") or "" for e in ev) == '{"sorgu": "bütçe", "dosya": "dokum.md"}'
        and any(x["type"] == "user" and "BÜTÇE" in x["message"]["content"][0]["content"] for x in ol)
        and "".join((e.get("delta") or {}).get("text") or "" for e in ev) == "Bütçe konusunu Ali açtı.\n---\nKaynak: dokum.md" and son["type"] == "result", json.dumps(ol, ensure_ascii=False)[:600])
kontrol("sonuç: iki tur, kullanım toplamı (okunan = cached_tokens), maliyet fiyattan",
        son["num_turns"] == 2 and son["usage"] == {"input_tokens": 1200, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 0, "output_tokens": 50}
        and abs(son["total_cost_usd"] - (1200 * 0.75 + 1000 * 0.075 + 50 * 3.75) / 1e6) < 1e-6 and not son["is_error"] and BY.kullanim(son)["giris"] == 2200, str(son))
g1, g2 = GELEN[0], GELEN[1]
kontrol("istek: /v1/chat/completions, Bearer anahtar (Anahtar Zinciri'nden), akış + kullanım, reasoning_effort, araçlar (ara/oku/listele + MCP vt_sor)",
        g1["yol"] == "/v1/chat/completions" and g1["yetki"] == "Bearer deneme-anahtar" and g1["g"]["stream"] and g1["g"]["stream_options"] == {"include_usage": True}
        and g1["g"]["reasoning_effort"] == "low" and [t["function"]["name"] for t in g1["g"]["tools"]] == ["ara", "oku", "listele", "vt_sor"])
kontrol("istem uyarlandı ve araç notu eklendi", "oku, ara, listele ile oku" in g1["g"]["messages"][0]["content"] and "[Araçlar]" in g1["g"]["messages"][0]["content"])
am = [m for m in g2["g"]["messages"] if m.get("tool_calls")]
kontrol("2. çağrı: araç çağrısı + düşünce imzası geri gitti, araç sonucu tool iletisi", am and am[0]["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "imza1"}}
        and g2["g"]["messages"][-1]["role"] == "tool" and g2["g"]["messages"][-1]["tool_call_id"] == "c1")
kontrol("kalıcı bağlantı: iki çağrı tek TCP bağlantısında", len(BAG) == 1, str(BAG))
CEVAP["kip"] = "metin"; GELEN.clear(); cik.truncate(0); cik.seek(0)
O.calis(io.StringIO(json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "ikinci soru"}]}}) + "\n"))
s2 = [json.loads(l) for l in cik.getvalue().splitlines()][-1]
kontrol("ikinci soru aynı oturumda: geçmiş korunur, maliyet süreç başına birikimli", len(GELEN) == 1 and GELEN[0]["g"]["messages"][-1]["content"] == "ikinci soru"
        and any(m.get("role") == "tool" for m in GELEN[0]["g"]["messages"]) and s2["total_cost_usd"] > son["total_cost_usd"])
CEVAP["kip"] = "429"; cik.truncate(0); cik.seek(0); n0 = len(O.gecmis)
with contextlib.redirect_stderr(io.StringIO()): O.calis(io.StringIO(json.dumps({"type": "user", "message": {"role": "user", "content": "üçüncü"}}) + "\n"))
s3 = [json.loads(l) for l in cik.getvalue().splitlines()][-1]
kontrol("HTTP 429 → sonuç is_error + ileti, geçmiş geri alındı", s3["is_error"] and "429" in s3["result"] and len(O.gecmis) == n0, str(s3))
kontrol("araçlı oturum: her model cevabından sonra Claude Code gibi assistant olayı (metin / tool_use)", any(x["type"] == "assistant" and x["message"]["content"][0]["type"] == "tool_use" and x["message"]["content"][0]["name"] == "Grep" for x in ol)
        and any(x["type"] == "assistant" and x["message"]["content"][0].get("text", "").startswith("Bütçe") for x in ol))

# === Aşama 2: araçsız açık süreç (çeviri) ===
CEVAP["kip"] = "metin"; GELEN.clear(); cik2 = io.StringIO()
OC = BY.Oturum(dict(BY.ceviri_istek({"beyin": {"ceviri": {"tur": "openai-uyumlu", "adres": ADRES, "model": "gemini-3.8-flash", "saglayici": "gemini", "anahtar": "x"}}}, "Sen çevirmensin. Read ile okuma yok."),
                    kokler=[]), cikis=cik2, mcp=M)
OC.calis(io.StringIO(json.dumps({"type": "user", "message": {"role": "user", "content": "1. Hello Read, Grep"}}) + "\n"))
oc = [json.loads(l) for l in cik2.getvalue().splitlines()]; g0 = GELEN[0]["g"] if GELEN else {}
kontrol("çeviri: araçsız (tools/tool_choice yok, MCP kullanılmaz), sistem istemi ve ileti uyarlanmadan, araç notu yok",
        "tools" not in g0 and "tool_choice" not in g0 and g0.get("messages", [{}])[0].get("content") == "Sen çevirmensin. Read ile okuma yok." and g0["messages"][-1]["content"] == "1. Hello Read, Grep", str(g0)[:300])
kontrol("çeviri: assistant olayı sonuçtan önce (okuyucu metni oradan alır), sonuç başarılı", [x["type"] for x in oc if x["type"] in ("assistant", "result")] == ["assistant", "result"]
        and oc[-1]["is_error"] is False, str([x["type"] for x in oc]))
M.kapat()

# === Aşama 2: tek çağrı ===
b2 = {"tur": "openai-uyumlu", "model": "gemini-3.8-flash", "saglayici": "gemini", "adres": ADRES, "anahtar": "x", "effort": "low", "fiyat": [0.75, 0.075, 3.75]}
GELEN.clear(); j1 = BY.tek_cagri(b2, "Okunuşlar: [\"Teams\"]", json_kip=True)
kontrol("tek_cagri: akışsız, JSON kipi, effort; sonuç Claude Code json biçiminde (result, usage, maliyet)", GELEN and GELEN[0]["g"]["stream"] is False and GELEN[0]["g"]["response_format"] == {"type": "json_object"}
        and GELEN[0]["g"]["reasoning_effort"] == "low" and j1["result"] == '{"Teams": "Tims"}' and not j1["is_error"] and j1["saglayici"] == "gemini"
        and BY.kullanim(j1) == {"giris": 2000, "okunan": 1000, "cikti": 40, "maliyet": round((1000 * 0.75 + 1000 * 0.075 + 40 * 3.75) / 1e6, 6)}, str(j1))
GELEN.clear(); j2 = BY.tek_cagri(b2, "özetle", sistem="Sistem")
kontrol("tek_cagri: JSON kipi istenmezse response_format yok; sistem iletisi başta", "response_format" not in GELEN[0]["g"] and GELEN[0]["g"]["messages"][0] == {"role": "system", "content": "Sistem"} and j2["result"] == "düz metin")
CEVAP["kipsiz"] = True; GELEN.clear(); j3 = BY.tek_cagri(b2, "x", json_kip=True); CEVAP["kipsiz"] = False
kontrol("tek_cagri: JSON kipini tanımayan sağlayıcıda (400) bir kez kipsiz", len(GELEN) == 2 and "response_format" not in GELEN[1]["g"] and j3["result"] == '{"Teams": "Tims"}' and not j3["is_error"], str(j3))
CEVAP["bos"] = True; j4 = BY.tek_cagri(b2, "x"); CEVAP["bos"] = False
CEVAP["kip"] = "429"; j5 = BY.tek_cagri(b2, "x"); CEVAP["kip"] = "metin"
j6 = BY.tek_cagri(dict(b2, adres="http://127.0.0.1:9/v1"), "x", zaman=3)
kontrol("tek_cagri: boş cevap, HTTP 429 ve bağlantı hatası istisna değil is_error (çağıran yedeğe düşer)", j4["is_error"] and "boş" in j4["result"] and j5["is_error"] and "429" in j5["result"]
        and j6["is_error"] and "ConnectionRefused" in j6["result"], f"{j4['result']} | {j5['result']} | {j6['result']}")
ti = os.path.join(T, "tek-istek.json"); json.dump(dict(BY.tek_istek({"beyin": {"telaffuz": dict(b2)}}, "telaffuz", "Okunuş", json_kip=True), zaman=20), open(ti, "w"))
r_ = subprocess.run([sys.executable, "-I", "-B", os.path.join(KOD, "aktarici", "beyin.py"), "tek", ti], capture_output=True, text=True, env=dict(os.environ, SUFLOR_TEST_BEYIN_ANAHTAR="deneme-anahtar"))
try: jt = json.loads(r_.stdout)
except ValueError: jt = {}
kontrol("beyin.py tek: istek dosyası → tek json satırı (anahtar istekte yok)", jt.get("result") == '{"Teams": "Tims"}' and "deneme-anahtar" not in open(ti).read() and json.load(open(ti))["beyin"]["anahtar"] == "x", r_.stdout[:200] + r_.stderr[:200])
json.dump({"beyin": dict(b2, adres="http://10.0.0.9/v1"), "istem": "x"}, open(ti, "w"))
r_ = subprocess.run([sys.executable, "-I", "-B", os.path.join(KOD, "aktarici", "beyin.py"), "tek", ti], capture_output=True, text=True)
kontrol("beyin.py tek: izinsiz adres reddedilir (çıkış 3)", r_.returncode == 3 and not r_.stdout)

# Brifing.app --beyin (deneme derlemesi; FIFO) — kurulu paket iskeleti gerekir
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): print("— Brifing.app --beyin atlandı (paket ya da swiftc yok)")
else:
    U = os.path.join(T, "uyg"); C = os.path.join(U, "canli"); os.makedirs(os.path.join(U, "aktarici")); os.makedirs(C)
    shutil.copy(os.path.join(KOD, "aktarici", "beyin.py"), os.path.join(U, "aktarici")); app = os.path.join(U, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
    subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
    subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
    def brifing(ist, soru=True):
        gir, cik_ = os.path.join(C, "konus-giris.fifo"), os.path.join(C, "konus-cikis.fifo"); y = os.path.join(C, "konus-istek.json")
        for f in (gir, cik_):
            if os.path.exists(f): os.remove(f)
            os.mkfifo(f, 0o600)
        json.dump(dict(ist, giris=gir, cikis=cik_), open(y, "w"))
        p = subprocess.Popen(["open", "-g", "-W", "-n", "-a", app, "--args", "--beyin", y], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sat, sonuc = [], {}
        def oku_():
            try:
                with open(cik_, encoding="utf-8") as r:
                    for l in r: sat.append(json.loads(l))
            except OSError: pass
        th = threading.Thread(target=oku_, daemon=True); th.start(); w = None; t0 = time.time()
        while time.time() - t0 < 15 and p.poll() is None:
            try: w = os.open(gir, os.O_WRONLY | os.O_NONBLOCK); break
            except OSError: time.sleep(0.05)
        if w is None:  # uygulama girişi açmadan çıktı: reddetti (open -W çıkış kodunu geçirmez)
            p.wait(timeout=10)
            try: os.close(os.open(cik_, os.O_WRONLY | os.O_NONBLOCK))  # okuyucu iş parçacığı takılı kalmasın
            except OSError: pass
            return "red", sat
        os.set_blocking(w, True); f = os.fdopen(w, "w")
        if soru: f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "Soru: bütçe?"}}) + "\n"); f.flush()
        t0 = time.time()
        while time.time() - t0 < 20 and not any(x.get("type") == "result" for x in sat): time.sleep(0.1)
        f.close(); p.wait(timeout=15); th.join(5); return p.returncode, sat
    CEVAP["kip"] = "arac"; GELEN.clear()
    IB = dict(IST, kokler=[U, C], cwd=U)
    rc, sat = brifing(IB)
    kontrol("Brifing --beyin: beyin.py FIFO'larla çalıştı, araç döngüsü ve sonuç geldi, giriş kapanınca çıktı",
            any(x.get("type") == "result" and not x.get("is_error") and x["num_turns"] == 2 for x in sat) and rc == 0, f"rc={rc} {str(sat)[:300]}")
    kontrol("Brifing --beyin: anahtar istekte yok, beyin.py'nin ortamından (deneme değişkeni) geldi", GELEN and GELEN[0]["yetki"] == "Bearer deneme-anahtar" and "deneme-anahtar" not in open(os.path.join(C, "konus-istek.json")).read())
    for ad, bozuk in (("dış ağda http", dict(IB, beyin=dict(IB["beyin"], adres="http://10.1.2.3/v1"))), ("bilinmeyen anahtar", dict(IB, claude="/bin/sh")),
                      ("tür claude-code", dict(IB, beyin=dict(IB["beyin"], tur="claude-code"))), ("var olmayan kök", dict(IB, kokler=["/yok/klasor"])),
                      ("başka klasördeki mcp", dict(IB, mcp=my))):
        rc, _ = brifing(bozuk, soru=False)
        kontrol(f"Brifing --beyin reddeder: {ad} (beyin.py çalışmaz)", rc == "red", f"rc={rc}")
SV.shutdown()
shutil.rmtree(T, ignore_errors=True)
print(f"\n{'KALDI: ' + str(len(hatalar)) if hatalar else 'GEÇTİ'}"); sys.exit(1 if hatalar else 0)
