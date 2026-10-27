#!/usr/bin/env python3
# Güncelleme/kurulum toplantı, sohbet ya da Konuş cevabı sürerken başlamaz (v0.77.4 kurulum.py mesgul + aktarici-kur.command; v0.77.5 guncelle
# ve panodaki "Güncelle" — relay.py guncelle_baslat). Sahte durumla, dosyaya ve ağa dokunmadan (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/guncelle-mesgul.py
import ast, os, sys
sys.dont_write_bytecode = True
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]  # test/ yola girmesin (eski test/platform.py standart modülü gölgeliyordu)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)

# 1) kurulum.py: mesgul() durum tablosu + guncelle() mesgulken durur, --zorla geçer
sys.argv = ["kurulum.py"]; g = {"__name__": "kurulum_deneme", "__file__": os.path.join(KOD, "kurulum.py")}
exec(compile(open(g["__file__"], encoding="utf-8").read().split('if __name__ == "__main__":')[0], "kurulum.py", "exec"), g)
TABLO = [({}, ""), ({"extension": {"call": True, "age_s": 5}}, "web toplantısı"), ({"extension": {"call": True, "age_s": 500}}, ""),
         ({"masaustu": {"toplantida": True}}, "masaüstü toplantısı"), ({"konus": {"durum": "dinliyor", "sohbet": {"acik": True}}}, "sohbet açık"),
         ({"konus": {"durum": "dusunuyor", "sohbet": {"acik": False}}}, "Konuş cevabı"), ({"konus": {"durum": "hazir", "sohbet": {"acik": False}}}, ""), (None, "")]
for s, b in TABLO:
    g["aktarici"] = lambda y, s=s: s; r = g["mesgul"]()
    ok(f"mesgul {s} → {r!r}", (b in r) if b else r == "")
g["aktarici"] = lambda y: {"konus": {"durum": "dinliyor", "sohbet": {"acik": True}}}
try: g["guncelle"]("/yok/deneme.tar.gz"); r = ""
except SystemExit as e: r = str(e)
ok(f"guncelle sohbet açıkken durur: {r[:60]!r}", r.startswith("Güncellenmedi: sohbet açık") and "Hiçbir dosya değişmedi" in r)
try: g["guncelle"]("/yok/deneme.tar.gz", zorla=True); r = ""
except SystemExit as e: r = str(e)
ok(f"--zorla denetimi geçer (sonra olmayan kaynak → indirilemedi): {r[:40]!r}", r.startswith("İndirilemedi"))
ok("guncelle.command --zorla'yı iletir", '"$@"' in open(os.path.join(KOD, "guncelle.command"), encoding="utf-8").read())
ok("aktarici-kur.command mesgul'e bakar", "kurulum.py\" mesgul" in open(os.path.join(KOD, "aktarici-kur.command"), encoding="utf-8").read())

# 1b) Faz A (S162): güncelleme sonrası adımlar YENİ kodla, ayrı süreçte (alt komut guncelleme-sonrasi) — eski sürümün kodu modeller_dene'yi yürütmüyordu
import inspect
ok("guncelle() sonrası adımları alt komuta devreder (kendisi modeller_dene çağırmaz)", "guncelleme-sonrasi" in inspect.getsource(g["guncelle"]) and "modeller_dene()" not in inspect.getsource(g["guncelle"]))
ok("alt komut komut satırında tanımlı", "guncelleme-sonrasi" in open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read().split('if __name__ == "__main__":')[1])
CAGRI = []
class SP:
    DEVNULL = None
    @staticmethod
    def run(c, *a, **k): CAGRI.append(("run", [os.path.basename(x) for x in c[1:3]])); return type("R", (), {"returncode": 0})
g.update(subprocess=SP, modeller_dene=lambda: CAGRI.append(("modeller_dene",)), say=lambda *a, **k: None, ayar=lambda: {},
         urllib=type("U", (), {"request": type("Q", (), {"urlopen": staticmethod(lambda *a, **k: (_ for _ in ()).throw(OSError("yok")))})}))
g["guncelleme_sonrasi"]()
ok(f"guncelleme_sonrasi sırası: kur → modeller_dene {CAGRI}", CAGRI[:2] == [("run", ["kurulum.py", "kur"]), ("modeller_dene",)])
g["subprocess"] = type("SP2", (), {"run": staticmethod(lambda c, *a, **k: type("R", (), {"returncode": 1})), "DEVNULL": None})
try: g["guncelleme_sonrasi"](); r = ""
except SystemExit as e: r = str(e)
ok("kur başarısızsa alt komut hata ile çıkar", "geliştiriciye" in r)

# 2) relay.py guncelle_baslat: panodaki düğme toplantı, sohbet ve Konuş cevabında reddeder; boşta güncelleme betiğini başlatır
fn = next(f for f in ast.parse(open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()).body if isinstance(f, ast.FunctionDef) and f.name == "guncelle_baslat")
class P:
    def __init__(self, *a, **k): BASLADI.append(a)
for ad, durum, beklenen in [("boşta", {}, True), ("web toplantısı", {"top": True}, False), ("masaüstü toplantısı", {"masaustu": {"toplantida": True}}, False),
                            ("sohbet açık", {"sohbet": True}, False), ("Konuş konuşuyor", {"konus": "konusuyor"}, False), ("Konuş hazır", {"konus": "hazir"}, True)]:
    BASLADI = []
    n = {"guncelleme_view": lambda: {"durum": "var"}, "toplanti_var": lambda d=durum: bool(d.get("top")), "STATE": {"masaustu": durum.get("masaustu")},
         "SOHBET": {"acik": bool(durum.get("sohbet"))}, "KONUS": {"durum": durum.get("konus", "kapali")}, "_t": lambda tr, en: tr,
         "_kod_dir": lambda: "/tmp", "GUN_LOG": os.devnull, "GUN": {"son": "9.9.9"}, "SURUM": "0.0.1", "datetime": __import__("datetime"),
         "os": os, "subprocess": type("S", (), {"Popen": P, "DEVNULL": None, "STDOUT": None}), "print": lambda *a, **k: None}
    exec(compile(ast.Module([fn], []), "relay.py", "exec"), n); r = n["guncelle_baslat"]()
    ok(f"pano Güncelle · {ad} → {r}", bool(r.get("ok")) == beklenen and bool(BASLADI) == beklenen)

print("guncelle-mesgul: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
