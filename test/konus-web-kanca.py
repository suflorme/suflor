# Konuş web kancası (G3, 13 Kasım 2026): örnek PreToolUse girdileriyle izin/red denetimi.
import os, sys, json, subprocess, tempfile
K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aktarici", "konus-web-kanca.py")
def calistir(ad, url, canli):
    gir = {"tool_name": ad, "tool_input": {"url": url} if ad == "WebFetch" else {"query": url}}
    r = subprocess.run([sys.executable, "-I", "-B", K, canli], input=json.dumps(gir), capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "allow"
bos = tempfile.mkdtemp(); gizli = tempfile.mkdtemp(); open(os.path.join(gizli, "gizli.json"), "w").write("{}")
for u, bek in [("https://www.example.com/about", "allow"), ("https://www.google.com/search?q=x", "allow"), ("http://127.0.0.1:8765/status", "deny"),
               ("https://example.com/" + "aB3dE5gH7jK9mN1pQ3sT5vX7zA9cE1gH3jK5mN7pQ9sT1vX3zA5cE7g", "deny")]:
    assert calistir("WebFetch", u, bos) == bek, (u, bek)
assert calistir("WebFetch", "https://www.example.com/about", gizli) == "deny"
assert calistir("WebSearch", "hava", gizli) == "deny" and calistir("WebSearch", "hava", bos) == "allow"
print("konus-web-kanca: tamam")
# konus_args: kanca yalnız web açıkken ve Brifing kancayı tanıyorsa (kanca=True); komut brifing.swift'in beklediğiyle aynı
import types, shlex
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BY = types.ModuleType("beyin_kanca"); BY.__file__ = os.path.join(KOD, "aktarici", "beyin.py"); exec(compile(open(BY.__file__, encoding="utf-8").read(), BY.__file__, "exec"), BY.__dict__)
def ayar_of(a): return json.loads(a[a.index("--settings") + 1])
B = tempfile.mkdtemp()
acik = ayar_of(BY.konus_args({}, "i", "", None, B, "sonnet", None, True, None, True))
assert list(acik["hooks"]) == ["PreToolUse"] and acik["hooks"]["PreToolUse"][0]["matcher"] == "WebFetch|WebSearch" and "env" in acik
kom = acik["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
assert kom == f"/usr/bin/python3 -I -B {shlex.quote(os.path.realpath(K))} {shlex.quote(os.path.realpath(B))}", kom
assert "hooks" not in ayar_of(BY.konus_args({}, "i", "", None, B, "sonnet", None, False, None, True)), "web kapalı"
assert "hooks" not in ayar_of(BY.konus_args({}, "i", "", None, B, "sonnet", None, True, None, False)), "eski Brifing"
assert "hooks" not in ayar_of(BY.konus_args({}, "i", "", None, B, "sonnet", None, True))
# konus_kanca_destek: işaretli kaynak/kayıt
src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
import re, hashlib
rx = re.search(r'KONUS_KANCA_RX = re.compile\((r"[^"]*")\)', src); assert rx
assert re.search(eval(rx.group(1)), open(os.path.join(KOD, "brifing.swift"), encoding="utf-8").read()), "brifing.swift işareti"
print("konus-web-kanca: konus_args tamam")
