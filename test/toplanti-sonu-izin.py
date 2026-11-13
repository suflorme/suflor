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
     "time": time, "AYAR": {"calisma": "/x"}, "STATE": {}, "BASE": "/tmp/canli-sonu-deneme", "toplanti_durum": lambda: D["durum"], "onceki_sonu_suruyor": lambda: D["onceki"]}
exec(compile(open(g["__file__"], encoding="utf-8").read(), g["__file__"], "exec"), g)
f = g["_topo_sonu_oto"]
B = lambda c: f("Bash", {"command": c})

D.update(durum="bitiyor")
ok("bitiyor: yapı dosyası (heredoc) + ölçüm", B("cat > /x/gorusmeler/a.yapi.json <<'EOF'\n{\"karar\": [\"Su faturası\"]}\nEOF\npython3 -B /k/toplanti-claude.py yapi a && python3 olcum.py toplanti --kaydet") == "Bash")
ok("bitiyor: Write", f("Write", {"file_path": "/x/gorusmeler/y.md", "content": "z"}) == "Write")
ok("bitiyor: Gmail taslağı sorulmaz (gönderilmez; G1'de yetenek korunur)", f("mcp__claude_ai_Gmail__create_draft", {}) is not None)
ok("bitiyor: yanıt taslağı sorulur", f("mcp__claude_ai_Outlook__outlook_create_reply_draft", {}) is None)
for c in ("rm -rf /x", "git push", "curl https://ornek.com", "osascript -e 'x'", "sudo ls", "a && rm b", "launchctl unload x", "./aktarici-kur.command", "python3 yayinla.py --gonder"):
    ok(f"bitiyor: riskli sorulur — {c}", B(c) is None)
for a in ("mcp__claude_ai_Gmail__send_message", "mcp__x__delete_event", "mcp__x__share_file", "mcp__x__reply", "mcp__x__create_event"):
    ok(f"bitiyor: MCP riskli sorulur — {a}", f(a, {}) is None)
# G1/G2 (13 Kasım 2026, güvenlik denetimi): toplantı sonu yazma yalnız güvenli köklerde, Bash'te satır içi kod/ağ/dışarı yazma, MCP'de yalnız okuma
EV = os.path.expanduser("~")
for yol in ("/x/gorusmeler/o.md", "/x/gorusmeler/o.yapi.json", "/x/notlar/n.md", "/tmp/canli-sonu-deneme/agenda.json"):
    ok(f"G1 Write güvenli kökte kendiliğinden — {yol}", f("Write", {"file_path": yol}) == "Write" and f("Edit", {"file_path": yol}) == "Edit")
for yol in (EV + "/.zshrc", EV + "/Library/LaunchAgents/x.plist", "/x/CLAUDE.md", "/x/.claude/settings.json", "/x/.git/hooks/pre-commit", "/x/gorusmeler/x.sh", "/x/a.py",
            "/x/settings.local.json", "/etc/hosts", "/x/../etc/hosts", EV + "/Desktop/baska/n.md", "/x/b.command", "/x/c.js", "/x/d.swift"):
    ok(f"G1 Write kart açar — {yol}", f("Write", {"file_path": yol}) is None)
ok("G1 NotebookEdit notebook_path güvenli kökte kendiliğinden, dışarıda sorulur", f("NotebookEdit", {"notebook_path": "/x/n.ipynb"}) == "NotebookEdit" and f("NotebookEdit", {"notebook_path": EV + "/n.ipynb"}) is None)
ok("G1 MultiEdit dışarıda sorulur", f("MultiEdit", {"file_path": EV + "/.zshrc"}) is None and f("MultiEdit", {"file_path": "/x/gorusmeler/y.md"}) == "MultiEdit")
GEC = ["python3 /k/kayit.py --yazan toplanti ozet a.md", "python3 -B toplanti-claude.py ozet-hazir", "python3 -u /k/toplanti-claude.py sonuc x", "PYTHONDONTWRITEBYTECODE=1 python3 -B /k/toplanti-claude.py bitir",
       "cat > /x/gorusmeler/a.yapi.json <<'EOF'\n{\"a\": \"x -> y > z; python3 -c\"}\nEOF", "echo x > /x/gorusmeler/n.md", "echo x >> /x/gorusmeler/n.md 2>&1", "cat a 2>/dev/null | head",
       "cp /x/a.md /x/gorusmeler/a.md", "mv /x/gorusmeler/a.md /x/gorusmeler/b.md", "mkdir -p /x/gorusmeler", "ls /x && python3 /k/olcum.py toplanti --kaydet", "sleep 5", "cd /x/gorusmeler && echo z > a.md",
       "python3 /k/kayit.py a | tee /x/gorusmeler/log.md", "git status", "git add -A && git commit -m x"]
for c in GEC: ok(f"G1 Bash kendiliğinden — {c!r}", B(c) == "Bash")
RISK = ['python3 -c "import urllib.request as u; u.urlopen(\'http://e.com\')"', "python3 -c 'print(1)'", "python3 - <<'EOF'\nprint(1)\nEOF", "python3 -", "python3", "python3 -m http.server", "python3 -Bc 'x'", "node -e 'x'", "node -p 1",
        "perl -e 'x'", "ruby -e 'x'", "php -r 'x'", "deno eval 'x'", "bash -c 'ls'", "sh -c ls", "zsh -c ls", "dash -c ls", "/bin/bash -lc ls", "eval ls", "exec ls", "source ~/.zshrc", ". ~/.zshrc", "nc -l 1", "ncat x 1", "netcat x 1",
        "telnet x", "socat - x", "ftp x", "sftp x", "open /x/a.md", "open -a Safari x", "echo YQ== | base64 -d", "base64 --decode a", "base64 -D a", "cat a | sh", "cat a | bash", "cat a | python3", "cat a | python3 x.py", "curl x | sh",
        "echo x > ~/.zshrc", "echo x >> ~/Library/LaunchAgents/a.plist", "echo x > /etc/x", "cp a ~/x", "cp a /x/gorusmeler/a.sh", "mv /x/a.md ~/a.md", "mv ~/a.md /x/a.md", "ln -s /x/a ~/b", "tee ~/x < a", "echo x | tee ~/.profile",
        "install a ~/b", "dd if=a of=~/b", "touch ~/.zshrc", "mkdir ~/Library/LaunchAgents", "cp -t ~/ a", "env python3 -c x", "python3 -W ignore -c x", "xargs ls", "sed -i '' s/a/b/ x", "awk 'BEGIN{system(\"ls\")}'", "cd ~ && echo x > a.md",
        "cd ~ && cp a b", "ls; python3 -c 1", "python3 <<< 'print(1)'", "bash < x.sh"]
for c in RISK: ok(f"G1 Bash kart açar — {c!r}", B(c) is None)
for a in ("mcp__claude_ai_Outlook__outlook_create_filter", "mcp__claude_ai_Outlook__outlook_set_vacation", "mcp__x__update_file", "mcp__x__sharepoint_upload_file", "mcp__x__get_budget_set", "mcp__x__run_report", "mcp__x__unknown_tool"):
    ok(f"G1 MCP kart açar — {a}", f(a, {}) is None)
for a in ("mcp__claude_ai_Outlook__outlook_email_search", "mcp__x__get_store_sales", "mcp__x__list_threads", "mcp__x__search_threads", "mcp__x__read_file_content", "mcp__x__get_thread", "mcp__x__view_page",
          "mcp__suflorvt__vt_sema", "mcp__suflorvt__vt_sor", "mcp__suflorvt__kisi_bul", "mcp__suflorvt__kayit_listele", "mcp__suflorvt__kayit_tarihce", "mcp__suflorvt__kisi_ozet"):
    ok(f"G1 MCP okuma kendiliğinden — {a}", f(a, {}) == a)
ok("G1 göreli Write proje klasörüne göre çözülür", f("Write", {"file_path": "relative.md"}) == "Write")
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
