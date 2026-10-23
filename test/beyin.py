#!/usr/bin/env python3
# Beyin katmanı Aşama 0 (aktarici/beyin.py, v0.121.1): yapay zekâ çağrılarının argümanları v0.121.0'dakiyle birebir aynı mı (Konuş, çeviri, telaffuz,
# brifing, proje kartı; ayarsız ve eski ayar anahtarlarıyla), "beyin" ayarı (iş başına model, bilinmeyen uyarlayıcı → claude-code), ölçüm alanları,
# Claude yolu, sahte claude ile tek çağrı; çağrı yerlerinde elle kurulmuş `claude -p` argümanı kalmadı mı; __pycache__ yazılmıyor mu.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/beyin.py      (kaldı → çıkış 1)
import contextlib, importlib.util, io, json, os, re, shutil, sys, tempfile

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
shutil.rmtree(T, ignore_errors=True)
print(f"\n{'KALDI: ' + str(len(hatalar)) if hatalar else 'GEÇTİ'}"); sys.exit(1 if hatalar else 0)
