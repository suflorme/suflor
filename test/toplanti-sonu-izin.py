#!/usr/bin/env python3
# Toplantı sonu izinleri sorulmaz (5 Kasım): toplantı bitiyor/bitti ve oturum toplantı sonu işlerindeyken araç izni kendiliğinden verilir;
# silme, push, ağ/sistem komutu ve MCP'de gönder/sil/paylaş türü araçlar yine sorulur; toplantı sürerken eskisi gibi sorulur; ayar kapatır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti-sonu-izin.py
import json, os, re, shlex, sys, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
D = {"durum": "bitiyor", "onceki": False}
g = {"__name__": "topo_test", "__file__": os.path.join(KOD, "aktarici", "toplanti-oturum.py"), "json": json, "os": os, "re": re, "shlex": shlex, "threading": threading,
     "time": time, "AYAR": {}, "STATE": {}, "BASE": "/tmp", "toplanti_durum": lambda: D["durum"], "onceki_sonu_suruyor": lambda: D["onceki"]}
exec(compile(open(g["__file__"], encoding="utf-8").read(), g["__file__"], "exec"), g)
f = g["_topo_sonu_oto"]
B = lambda c: f("Bash", {"command": c})

D.update(durum="bitiyor")
ok("bitiyor: yapı dosyası (heredoc) + ölçüm", B("cat > /x/gorusmeler/a.yapi.json <<'EOF'\n{\"karar\": [\"Su faturası\"]}\nEOF\npython3 -B /k/toplanti-claude.py yapi a && python3 olcum.py toplanti --kaydet") == "Bash")
ok("bitiyor: Write", f("Write", {"file_path": "/x/y.md", "content": "z"}) == "Write")
ok("bitiyor: Gmail taslağı", f("mcp__claude_ai_Gmail__create_draft", {}) is not None)
for c in ("rm -rf /x", "git push", "curl https://ornek.com", "osascript -e 'x'", "sudo ls", "a && rm b", "launchctl unload x", "./aktarici-kur.command", "python3 yayinla.py --gonder"):
    ok(f"bitiyor: riskli sorulur — {c}", B(c) is None)
for a in ("mcp__claude_ai_Gmail__send_message", "mcp__x__delete_event", "mcp__x__share_file", "mcp__x__reply", "mcp__x__create_event"):
    ok(f"bitiyor: MCP riskli sorulur — {a}", f(a, {}) is None)
ok("bitiyor: bilinmeyen araç sorulur", f("WebFetch", {"url": "https://x"}) is None)

D.update(durum="bos", onceki=True)
ok("bitti (önceki toplantının sonu sürüyor): verilir", B("python3 x.py sonuc") == "Bash")
D.update(durum="bos", onceki=False)
ok("toplantı yok: sorulur", B("python3 x.py sonuc") is None)
D.update(durum="suruyor", onceki=True)
ok("yeni toplantı sürüyor: sorulur", B("python3 x.py sonuc") is None)
D.update(durum="bitiyor"); g["AYAR"]["toplanti_sonu_onaysiz"] = False
ok("ayar kapalı: sorulur", B("python3 x.py sonuc") is None)
print("hepsi geçti" if not HATA else f"{len(HATA)} hata"); sys.exit(1 if HATA else 0)
