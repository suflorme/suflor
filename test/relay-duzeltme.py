# relay.py düzeltmeleri (18 Kasım): sabit port açmaz; ilgili parçaları ast ile çıkarıp çalıştırır.
# 1) /kimlik yol çakışması  2) günlük satırı yapışması (_Saatli)  3) gizli.json atomik yazım + bozukta AÇIK  4) HTML güvenlik başlıkları
import ast, datetime, io, json, os, re, sys, tempfile, threading, time
K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relay.py")
SRC = open(K, encoding="utf-8").read(); AG = ast.parse(SRC)
hata = []
def ok(ad, c):
    print(("ok   " if c else "HATA ") + ad); c or hata.append(ad)
def sinif(ad): return next(n for n in AG.body if isinstance(n, ast.ClassDef) and n.name == ad)
def islev(ad): return next(n for n in AG.body if isinstance(n, ast.FunctionDef) and n.name == ad)
def kod(*dugumler): return compile(ast.Module(list(dugumler), []), K, "exec")

# 2) günlük
g = {"threading": threading, "datetime": datetime, "teshis_satir": lambda l: None}
exec(kod(sinif("_Saatli")), g)
cikti = io.StringIO(); S = g["_Saatli"](cikti)
def is_(k):
    for i in range(1500): print(f"T{k} satir {i} " + "x" * (i % 17), file=S)
ts = [threading.Thread(target=is_, args=(k,)) for k in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]
satirlar = cikti.getvalue().split("\n")
ok("son satır boş (tam satırla bitti)", satirlar[-1] == ""); satirlar = satirlar[:-1]
ok("12000 satır", len(satirlar) == 12000)
ok("her satırda saat öneki ve tek ileti", all(re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d T\d satir \d+ x*", l) for l in satirlar))
c2 = io.StringIO(); S2 = g["_Saatli"](c2); S2.write("a"); S2.write("b\nc\n"); S2.write("d")
ok("parça parça yazım tek saatli satır, yarım satır tutulur", re.fullmatch(r"[\d\- :]{19} ab\n[\d\- :]{19} c\n", c2.getvalue()) is not None)

# 3) gizli kip
src = SRC[SRC.index("GIZLI = {"):SRC.index("GIZLI_YUT = ")]
src = src.replace('GIZLI_FP = os.path.join(BASE, "gizli.json")', 'GIZLI_FP = os.path.join(BASE, "gizli.json")')
yazilan = []
def calistir(dosya_icerik):
    d = tempfile.mkdtemp(); fp = os.path.join(d, "gizli.json")
    if dosya_icerik is not None: open(fp, "w").write(dosya_icerik)
    ns = {"os": os, "json": json, "time": time, "BASE": d, "print": lambda *a: yazilan.append(" ".join(map(str, a)))}
    exec(src, ns); return ns["GIZLI"]["acik"]
ok("gizli.json yok → kapalı", calistir(None) is False)
ok("gizli.json geçerli → açık", calistir('{"bas": 123.0}') is True)
yazilan.clear(); ok("gizli.json bozuk → AÇIK (güvenli taraf)", calistir("{bozuk") is True)
ok("bozukta günlük satırı yazıldı", any("durum dosyası okunamadı — güvenli tarafta açık başlatıldı" in y for y in yazilan))
gd = src[:0]; GD = SRC[SRC.index("def gizli_degistir"):SRC.index("    if ac:  # süren her şey hemen kesilir")]
ok("gizli_degistir atomik yazar (dosya_yaz_esz, 0o600)", "dosya_yaz_esz(GIZLI_FP" in GD and "0o600" in GD and "json.dump" not in GD)
ok("silme yolu FileNotFoundError'ı yutar", "except FileNotFoundError" in GD)
d = tempfile.mkdtemp(); ge = {"os": os, "json": json, "threading": threading}; exec(kod(islev("gecici_ad"), islev("dosya_yaz_esz")), ge)
fp = os.path.join(d, "gizli.json"); ge["dosya_yaz_esz"](fp, {"bas": 1.0}, 0o600)
ok("dosya 0o600 ve geçerli JSON", oct(os.stat(fp).st_mode & 0o777) == "0o600" and json.load(open(fp)) == {"bas": 1.0})

# 1) /kimlik
dg = next(n for n in sinif("H").body if isinstance(n, ast.FunctionDef) and n.name == "do_GET") if any(n.name == "H" for n in AG.body if isinstance(n, ast.ClassDef)) else None
if dg is None:  # işleyici sınıfının adı farklıysa do_GET'i bul
    dg = next(m for c in AG.body if isinstance(c, ast.ClassDef) for m in c.body if isinstance(m, ast.FunctionDef) and m.name == "do_GET")
gk = ast.get_source_segment(SRC, dg)
ilk = gk.index('"/kimlik"')
ok("/kimlik?n= yalnız n varken anahtarsız imza döner", 'kimlik_imza(m.group(1))' in gk[ilk - 200:ilk + 600] and "if m:" in gk[ilk - 200:ilk + 600])
ok("n'siz /kimlik 400 dönmüyor (anahtarlı ?ad= işleyicisine düşer)", '"/kimlik":' in gk and gk.count('"/kimlik"') == 2 and "self._json({\"ok\": False}, 400)" not in gk[ilk - 200:ilk + 600])
ok("/kimlik VERI_GET'te (anahtarsız n'siz istek 401)", re.search(r'VERI_GET = \{[^}]*"/kimlik"', SRC) is not None)

# 4) HTML başlıkları
hs = ast.get_source_segment(SRC, next(m for c in AG.body if isinstance(c, ast.ClassDef) for m in c.body if isinstance(m, ast.FunctionDef) and m.name == "_html"))
class Sahte:
    def __init__(s): s.h = {}; s.out = b""; s.wfile = io.BytesIO()
    def send_response(s, c): s.c = c
    def send_header(s, k, v): s.h[k] = v
    def end_headers(s): pass
ns = {}; exec(hs.replace("    def _html", "def _html", 1).replace("\n    ", "\n"), ns)
o = Sahte(); ns["_html"](o, b"<html>")
ok("X-Frame-Options SAMEORIGIN (menü paneli aynı kökten iframe)", o.h.get("X-Frame-Options") == "SAMEORIGIN")
ok("CSP yalnız frame-ancestors 'self'", o.h.get("Content-Security-Policy") == "frame-ancestors 'self'")
ok("Cache-Control no-store, Referrer-Policy, nosniff", o.h.get("Cache-Control") == "no-store" and o.h.get("Referrer-Policy") == "no-referrer" and o.h.get("X-Content-Type-Options") == "nosniff")
ok("HTML gövdesi ve uzunluk", o.wfile.getvalue() == b"<html>" and o.h["Content-Length"] == "6")
ok("üç HTML sayfası da _html ile gider", 'text/html; charset=utf-8' not in SRC.replace("self.send_header(\"Content-Type\", \"text/html; charset=utf-8\")", "", 1))
sys.exit(1 if hata else 0)
