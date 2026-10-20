#!/usr/bin/env python3
# Brifing yardımcısının izin sınırı (güvenlik denetimi O3, v0.97.4; brifing.swift): Masaüstü izni bu yardımcıda — istek dosyasıyla izni ödünç almak
# zorlaşsın: imzasız "claude" reddedilir, argümanlar izin listesinden (yazma/komut aracı, kanca açan --settings, başka klasör --add-dir, başka MCP sunucusu
# yok), istek/çıktı/FIFO uygulama klasörünün altında aynı klasörde. Kurulu sürüm (imza denetimli) gerçek claude'la API'ye gitmeden denenir: boş girişle
# açık süreç kipi — claude soru almadan çıkar. Deneme derlemesi (-D SUFLOR_DENEME) sahte claude'la aktarıcının gerçek argüman kümelerini kabul eder.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/brifing-izin.py      (swiftc gerekir, ~40 sn)
import json, os, shutil, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not shutil.which("swiftc"): sys.exit("atlandı: swiftc yok")
T = os.path.realpath(tempfile.mkdtemp(prefix="brifing-izin-")); U = os.path.join(T, "uyg"); C = os.path.join(U, "canli")
for d in (C, os.path.join(U, "paket"), os.path.join(U, "paket-d"), os.path.join(T, "bin")): os.makedirs(d)
ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)
kur, den = os.path.join(U, "paket", "SuflorBrifing"), os.path.join(U, "paket-d", "SuflorBrifing")  # paketsiz ikilide uygulama klasörü = bir üst (U)
for ik, ek in ((kur, []), (den, ["-D", "SUFLOR_DENEME"])):
    r = subprocess.run(["swiftc", "-O", *ek, "-o", ik, os.path.join(KOD, "brifing.swift")], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-800:]); sys.exit("derlenemedi")
sahte = os.path.join(T, "bin", "claude"); open(sahte, "w").write("#!/bin/sh\necho SAHTE-CALISTI >> \"$(dirname \"$0\")/iz\"\n"); os.chmod(sahte, 0o755)
gercek = next((y for y in (os.path.expanduser("~/.local/bin/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude") if os.path.isfile(y)), None)
open(os.path.join(U, "toplanti-claude.py"), "w").write("")
def calistir(ik, args, claude=None, klasor=C, ek=None, sure=30):
    gir, cik = os.path.join(klasor, "g"), os.path.join(klasor, "c"); open(gir, "w").close(); open(cik, "w").close()
    ist = dict({"claude": claude or sahte, "args": args, "cwd": T, "cikti": os.path.join(klasor, "cikti.json"), "giris": gir, "cikis": cik, "sure": 20}, **(ek or {}))
    y = os.path.join(klasor, "istek.json"); json.dump(ist, open(y, "w"))
    try: os.remove(os.path.join(T, "bin", "iz"))
    except OSError: pass
    return subprocess.run([ik, "--istek", y], capture_output=True, timeout=sure).returncode
def sahte_calisti(): return os.path.exists(os.path.join(T, "bin", "iz"))
MCP = os.path.join(C, "konus-mcp.json")
def mcp_yaz(komut="/usr/bin/python3", tc=os.path.join(U, "toplanti-claude.py"), env=None):
    json.dump({"mcpServers": {"suflorvt": {"command": komut, "args": ["-B", tc, "--dir", C, "vt-mcp"], "env": env or {"PYTHONDONTWRITEBYTECODE": "1"}}}}, open(MCP, "w"))
mcp_yaz()
KONUS = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
         "--allowedTools", "Read,Grep,Glob,mcp__suflorvt__vt_sema,mcp__suflorvt__vt_sor", "--add-dir", C, "--append-system-prompt", "istem", "--mcp-config", MCP,
         "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands", "--no-session-persistence", "--tools", "Read,Grep,Glob",
         "--model", "sonnet", "--settings", json.dumps({"env": {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS": "1"}}), "--effort", "medium"]
BRIFING = ["-p", "Toplantı bağlamı: …", "--allowedTools", "Read,Grep,Glob", "--add-dir", C, "--output-format", "json", "--model", "claude-opus-5-5"]
try:
    # deneme derlemesi: aktarıcının gerçek argüman kümeleri geçer, sahte claude çalışır
    kontrol("Konuş argümanları kabul (sahte claude çalıştı)", calistir(den, KONUS) != 3 and sahte_calisti())
    kontrol("brifing argümanları kabul", calistir(den, BRIFING) != 3 and sahte_calisti())
    kontrol("telaffuz argümanları kabul", calistir(den, ["-p", "adlar", "--output-format", "json", "--model", "sonnet"]) != 3 and sahte_calisti())
    for ad, args in [("Bash aracı", ["-p", "x", "--allowedTools", "Read,Bash"]), ("Write --tools", ["-p", "x", "--tools", "Write"]),
                     ("izinsiz kip", ["-p", "x", "--dangerously-skip-permissions"]), ("izin kipi", ["-p", "x", "--permission-mode", "bypassPermissions"]),
                     ("kanca açan --settings", ["-p", "x", "--settings", json.dumps({"hooks": {"PreToolUse": []}})]),
                     ("--settings dosya yolu", ["-p", "x", "--settings", os.path.join(C, "a.json")]),
                     ("--settings izin listesi", ["-p", "x", "--settings", json.dumps({"env": {}, "permissions": {"allow": ["Bash"]}})]),
                     ("başka klasör --add-dir", ["-p", "x", "--add-dir", "/"]), ("ikinci konumsal argüman", ["-p", "x", "fazla"]),
                     ("bilinmeyen bayrak", ["-p", "x", "--agents", "{}"]), ("--model'de boşluk", ["-p", "x", "--model", "a b"])]:
        kontrol(f"reddedildi: {ad}", calistir(den, args) == 3 and not sahte_calisti())
    for ad, kw in [("başka komut", {"komut": sahte}), ("başka betik", {"tc": os.path.join(T, "kotu.py")}), ("ortam değişkeni", {"env": {"PYTHONPATH": T}})]:
        mcp_yaz(**kw); kontrol(f"MCP reddedildi: {ad}", calistir(den, KONUS) == 3 and not sahte_calisti())
    mcp_yaz()
    os.makedirs(os.path.join(T, "disari")); kontrol("istek uygulama klasörü dışında → red", calistir(den, BRIFING, klasor=os.path.join(T, "disari")) == 3)
    kontrol("çıktı başka klasörde → red", calistir(den, BRIFING, ek={"cikti": os.path.join(T, "x.json")}) == 3 and not sahte_calisti())
    # kurulu sürüm: imza denetimi
    kontrol("kurulu sürüm: imzasız 'claude' reddedildi", calistir(kur, BRIFING) == 3 and not sahte_calisti())
    if gercek:
        kontrol("kurulu sürüm: imzalı claude geçer (boş girişle çıkar, API yok)", calistir(kur, ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--no-session-persistence"], claude=gercek, sure=60) != 3)
        kontrol("kurulu sürüm: imzalı claude'da da yasak argüman reddedilir", calistir(kur, ["-p", "x", "--allowedTools", "Bash"], claude=gercek) == 3)
    else: print("(gerçek claude yok — imzalı claude denemesi atlandı)")
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
