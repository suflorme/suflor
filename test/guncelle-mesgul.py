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
         ({"konus": {"durum": "dusunuyor", "sohbet": {"acik": False}}}, "Konuş cevabı"), ({"konus": {"durum": "hazir", "sohbet": {"acik": False}}}, ""), (None, ""),
         ({"toplanti_oturum": {"durum": "calisiyor", "sonu": True}}, "toplantı sonu işlerini yapıyor"), ({"toplanti_oturum": {"durum": "calisiyor"}}, "Toplantı oturumu çalışıyor"),
         ({"toplanti_oturum": {"durum": "bekliyor", "acik_soru": True, "soru": {"secenek": ["A"]}}}, "cevabını bekliyor"),
         ({"toplanti_oturum": {"durum": "bekliyor", "izin": 1, "izinler": [{"id": "x"}]}}, "izin cevabını bekliyor"),
         ({"toplanti_oturum": {"durum": "bekliyor", "sonu": True}}, "toplantı sonu işlerini yapıyor"), ({"toplanti_oturum": {"durum": "izliyor", "acik_soru": False}}, ""),
         ({"toplanti_oturum": {"durum": "bekliyor", "acik_soru": False, "sonu": False}}, ""), ({"toplanti_oturum": {"durum": "kapali"}}, ""), ({"toplanti_oturum": None}, "")]
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

# 1a) 3 Kasım: kurulum eski veritabanı yardımcısını (Suflor Brifing.app --vt-izle <canli> ve Python alt süreci) kapatır — yalnız bu canli klasörünün; Brifing'in başka kipleri, başka canli ve başka kullanıcının kopyası değil
import tempfile
_t = tempfile.mkdtemp(prefix="suflor-vtizle-"); C1 = os.path.join(_t, "Application Support", "Uyg", "canli"); C2 = os.path.join(_t, "Application Support", "Uyg2", "canli")
os.makedirs(C1); os.makedirs(C2); A1 = os.path.dirname(C1)
BR = A1 + "/Suflor Brifing.app/Contents/MacOS/SuflorBrifing"; PY_ = "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python"
PS = [f"101 {BR} --vt-izle {C1}", f"102 {PY_} -I -B {A1}/toplanti-claude.py --dir {C1} vt-izle",                         # eşleşir: bu canli
      f"103 {BR} --vt-izle {C2}", f"104 {PY_} -I -B {os.path.dirname(C2)}/toplanti-claude.py --dir {C2} vt-izle",           # başka canli klasörü
      f"105 {BR} --kip toplanti --dir {C1}", f"106 {BR}", f"107 {BR} --acik-surec {C1}",                                  # Brifing'in başka kipleri
      f"108 {PY_} -I -B {A1}/toplanti-claude.py --dir {C1} izle", f"109 /usr/bin/claude -p --dir {C1} vt-izle sorusu",     # izle ve Konuş süreçleri
      f"110 {BR} --vt-izle {C1}/ek", f"111 {BR} --vt-izle {C1}x", "bozuk satir", f"112 {BR} --vt-izle {C1}/"]            # önek/sonek benzerleri değil; sondaki eğik çizgi aynı klasör
ok("vt-izle süreç seçimi: bu canli'nin yardımcısı + Python alt süreci (boşluklu 'Application Support' yolu, sondaki /)", g["vt_izle_surecleri"](PS, C1) == [101, 102, 112])
ok("vt-izle süreç seçimi: başka canli klasörü yalnız kendi sürecini eşler", g["vt_izle_surecleri"](PS, C2) == [103, 104])
ok("vt-izle süreç seçimi: toplantı/açık süreç/izle/Konuş kipleri ve bozuk satır eşleşmez", not set(g["vt_izle_surecleri"](PS, C1)) & {105, 106, 107, 108, 109, 110, 111} and g["vt_izle_surecleri"]([], C1) == [])
_oldkill = os.kill; _oldsessiz = g["sessiz"]; _oldsay = g["say"]; OLDU = []
g["sessiz"] = lambda *c, **k: type("R", (), {"stdout": "\n".join(PS), "returncode": 0})(); g["say"] = lambda *a, **k: None
os.kill = lambda pid, sig: OLDU.append((pid, sig))
try: n = g["vt_izle_kapat"](C1)
finally: os.kill = _oldkill; g["sessiz"] = _oldsessiz; g["say"] = _oldsay
ok("vt_izle_kapat: yalnız eşleşen süreçlere SIGTERM", n == 3 and OLDU == [(101, 15), (102, 15), (112, 15)])
_kur = inspect.getsource(g["kur"]) if "inspect" in globals() else __import__("inspect").getsource(g["kur"])
ok("kur(): vt_izle_kapat kodu ve imzaları yerleştirdikten sonra çalışır", 0 < _kur.index("copytree") < _kur.index("imzala(imz)") < _kur.index("vt_izle_kapat(canli)"))
ok("aktarici-kur.command meşgul denetimini kurulumdan önce yapar", (lambda t: t.index("kurulum.py\" mesgul") < t.index("kurulum.py\" kur"))(open(os.path.join(KOD, "aktarici-kur.command"), encoding="utf-8").read()))
shutil_ = __import__("shutil"); shutil_.rmtree(_t, ignore_errors=True)

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
