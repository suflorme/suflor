#!/usr/bin/env python3
# Toplantı oturumunda salt okuyan kabuk komutu sorulmaz (6 Kasım; 5 Kasım ölçümü: `find` için 113 sn izin beklendi, olaylar kuyrukta kaldı).
# aktarici/toplanti-oturum.py `_topo_salt_okur`: izinli komut listesi + yasak seçenek/yönlendirme; şüphede sorulur. Ayar toplanti_salt_okur_onaysiz: false kapatır.
# İzin beklemesinin günlük satırı (`_topo_bekleme_kaydi`, izle-olay.json) da burada.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/salt-okur-izin.py
import io, json, os, re, shlex, sys, tempfile, threading, time, contextlib
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="salt-")
g = {"__name__": "topo_test", "__file__": os.path.join(KOD, "aktarici", "toplanti-oturum.py"), "json": json, "os": os, "re": re, "shlex": shlex, "threading": threading,
     "time": time, "AYAR": {}, "STATE": {}, "BASE": T, "toplanti_durum": lambda: "suruyor", "onceki_sonu_suruyor": lambda: False}
exec(compile(open(g["__file__"], encoding="utf-8").read(), g["__file__"], "exec"), g)
f = g["_topo_salt_okur"]
B = lambda c: f("Bash", {"command": c})

GECER = ["find . -name x", "grep -rn a b", "ls -la", "cat x | head", "find ~/Desktop -name '*.md' -mtime -2 2>/dev/null | head -20",
         "rg -n 'bütçe' gorusmeler/", "ls -la /tmp && wc -l a.md", "cd gorusmeler && grep -l 'x' *.md | sort | uniq -c", "head -50 a.md; tail -5 b.md",
         "sed -n '10,40p' a.md", "stat -f %m a.md", "mdfind -onlyin ~/Desktop 'kMDItemDisplayName == \"*rapor*\"'", "file a.pdf", "wc -l < a.md",
         "grep -c x a 2>&1 | head -3", "/usr/bin/find . -type f -name '*.json'", "jq '.items[] | {a: .b}' agenda.json", "du -sh .", "grep -n 'foo$' a.txt",
         "sqlite3 -readonly proje.db \"SELECT ad FROM kisi LIMIT 5\"", "sqlite3 -readonly proje.db .tables", "echo bitti"]
SORULUR = ["find . -delete", "find . -exec rm {} \;", "find . -execdir cat x ';'", "cat a > b", "cat a >> b", "sed -i '' 's/a/b/' x", "sed -n '1p;w out' x",
           "sed 's/a/b/' x", "rm x", "rm -rf /tmp/x", "curl https://ornek.com", "git push", "git log", "sqlite3 db \"UPDATE t SET a=1\"",
           "sqlite3 -readonly db \"DELETE FROM t\"", "sqlite3 db \"SELECT 1\"", "sqlite3 -readonly db \"SELECT writefile('x', 'y')\"", "sqlite3 -readonly db \".shell ls\"",
           "cat x | sqlite3 -readonly db", "cat x | tee y", "ls | xargs rm", "ls; rm x", "ls && python3 -c 'print(1)'", "echo $(rm x)", "echo `rm x`",
           "find . -name \"$(rm x)\"", "find . $'-delete'", "find . {-delete,-print}", "ls &", "(ls)", "ls\nrm x", "sort -o out in", "sort -no out in",
           "rg --pre ./x pat", "uniq a b", "cat <<EOF\nx\nEOF", "diff <(ls a) <(ls b)", "awk '{print > \"x\"}' a", "cat a 2>err.txt", "X=1 ls",
           "open x", "osascript -e 'x'", "python3 a.py", "ls 'açık", "find . -fprint out", "find . -ok rm {} ';'", "cat a >| b", "echo x > /dev/nullx"]
for c in GECER: ok(f"geçer — {c}", B(c) is not None)
for c in SORULUR: ok(f"sorulur — {c!r}", B(c) is None)
ok("Bash dışı araç bu kurala girmez", f("Write", {"file_path": "/tmp/x"}) is None)
ok("günlük açıklaması yalnız komut adları", B("find /gizli/yol -name x | head") == "Bash find | head")
g["AYAR"]["toplanti_salt_okur_onaysiz"] = False
ok("ayar kapalı: sorulur", B("ls -la") is None)
g["AYAR"].pop("toplanti_salt_okur_onaysiz")

# _topo_izin'de dal: salt okuyan Bash sorulmadan, yazan Bash izin_iste'ye gider
gonderilen, sorulan = [], []
g.update(_topo_gonder=lambda o: gonderilen.append(o) or True, _t=lambda tr, en: tr, gizli_acik=lambda: False, izin_metni=lambda a, gi: a, arac_cumlesi=lambda a, gi: a,
         izin_iste=lambda *a, **k: sorulan.append(a) or "i1", izin_bekle=lambda iid: "reddedildi", _topo_mesaj=lambda *a, **k: None)
def izin(c):
    gonderilen.clear(); sorulan.clear(); out = io.StringIO()
    with contextlib.redirect_stdout(out): g["_topo_izin"]({"request_id": "r1", "request": {"tool_name": "Bash", "input": {"command": c}}})
    return gonderilen[-1]["response"]["response"]["behavior"], bool(sorulan), out.getvalue()
b, s, gl = izin("find . -name x | head")
ok("izin: find kendiliğinden (soru yok, günlükte İZİN: salt-okur)", b == "allow" and not s and "İZİN: salt-okur, kendiliğinden — Bash find | head" in gl)
# izin beklerken izle'nin olayları: izle-olay.json'daki anlardan bekleme penceresine düşenler sayılır
t0 = time.time()
json.dump({"pid": 1, "n": 3, "t": [t0 - 100, t0 + 0.01, t0 + 0.02]}, open(os.path.join(T, "izle-olay.json"), "w"))
g["izin_bekle"] = lambda iid: (time.sleep(0.05), "reddedildi")[1]
b, s, gl = izin("rm x")
ok("izin: rm sorulur", b == "deny" and s)
ok("günlükte İZİN BEKLEME (kuyrukta 2 olay)", re.search(r"İZİN BEKLEME: Bash \d+\.\d sn · kuyrukta 2 olay \(en eskisi \d+\.\d sn\) · kutudan 0 ileti", gl) is not None)

# G2 (13 Kasım 2026, güvenlik denetimi): gizli bilgi yolu okuması ve veri taşıyabilecek WebFetch adresi karta düşer
EV = os.path.expanduser("~")
for c in ("cat ~/.ssh/id_ed25519", "cat " + EV + "/.aws/credentials", "grep -r x ~/.ssh", "ls ~/.gnupg", "head -3 ~/Library/Keychains/login.keychain-db", "cat < ~/.ssh/id_rsa", "cd ~/.ssh && cat id_rsa", "grep -rn x ~", "cat ./.env"):
    ok(f"G2 salt-okur: gizli yol sorulur — {c}", B(c) is None)
for c in ("cat ~/Desktop/Claude\\ outputs/notlar.md", "ls ~/Desktop", "grep -rn x gorusmeler/"):
    ok(f"G2 salt-okur: sıradan yol kendiliğinden — {c}", B(c) is not None)
def izin_ac(ad, gi):
    gonderilen.clear(); sorulan.clear(); out = io.StringIO()
    with contextlib.redirect_stdout(out): g["_topo_izin"]({"request_id": "r2", "request": {"tool_name": ad, "input": gi}})
    return gonderilen[-1]["response"]["response"]["behavior"], bool(sorulan), out.getvalue()
g.update(topo_web_acik=lambda: True, izin_bekle=lambda iid: "onaylandi", izin_metni=lambda a, gi=None: "metin")
g["AYAR"].pop("bilgi_onaysiz", None)
ok("G2 Read ~/.ssh/id_ed25519 sorulur", izin_ac("Read", {"file_path": "~/.ssh/id_ed25519"})[:2] == ("allow", True))
ok("G2 Read proje dosyası sorulmaz", izin_ac("Read", {"file_path": os.path.join(KOD, "manifest.json")})[:2] == ("allow", False))
ok("G2 Grep ev klasörü ve Glob gizli desen sorulur", izin_ac("Grep", {"pattern": "x", "path": "~"})[1] and izin_ac("Glob", {"pattern": "~/.ssh/*"})[1] and izin_ac("Glob", {"pattern": "*", "path": EV + "/.aws"})[1])
ok("G2 Grep/Glob proje klasörü sorulmaz", not izin_ac("Grep", {"pattern": "x", "path": KOD})[1] and not izin_ac("Glob", {"pattern": "test/*.py", "path": KOD})[1])
ok("G2 WebFetch genel sayfa sorulmaz", izin_ac("WebFetch", {"url": "https://www.example.com/about"})[:2] == ("allow", False))
BASE64 = "https://www.example.com/p/" + "QWxhZGRpbjpPcGVuU2VzYW1lU2VjcmV0S2V5MTIzNDU2Nzg5MGFiY2RlZg"
b, s_, gl = izin_ac("WebFetch", {"url": BASE64})
ok("G2 WebFetch uzun kodlu yol sorulur, neden günlükte", b == "allow" and s_ and "İZİN: web adresi soruluyor — " in gl)
metinler = []
g["izin_iste"] = lambda tur, ne, ay=None, **k: metinler.append(ne) or "i2"
izin_ac("WebFetch", {"url": BASE64})
ok("G2 kartta neden görünür", metinler and "Dikkat" in metinler[-1] and "kodlanmış" in metinler[-1])
g["izin_iste"] = lambda *a, **k: sorulan.append(a) or "i1"
ok("G2 önceki WebFetch onayından sonra da şüpheli adres yeniden sorulur", izin_ac("WebFetch", {"url": BASE64})[1] and izin_ac("WebFetch", {"url": BASE64})[1]
   and not izin_ac("WebFetch", {"url": "https://www.example.com/baska"})[1])
ok("G2 uzun sorgu sorulur", izin_ac("WebFetch", {"url": "https://a.com/x?q=" + "a" * 100})[1])
ok("G2 WebFetch localhost yine reddedilir (kart yok)", izin_ac("WebFetch", {"url": "http://localhost:8765/status"})[:2] == ("deny", False))
ok("G2 WebSearch değişmedi", izin_ac("WebSearch", {"query": "firma"})[:2] == ("allow", False))
print("hepsi geçti" if not HATA else f"{len(HATA)} hata"); sys.exit(1 if HATA else 0)
