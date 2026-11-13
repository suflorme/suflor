#!/usr/bin/env python3
# Güncelleme/kurulum toplantı, sohbet ya da Konuş cevabı sürerken başlamaz (v0.77.4 kurulum.py mesgul + aktarici-kur.command; v0.77.5 guncelle
# ve panodaki "Güncelle" — relay.py guncelle_baslat). Sahte durumla, dosyaya ve ağa dokunmadan (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/guncelle-mesgul.py
import ast, os, shutil, sys
sys.dont_write_bytecode = True
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]  # test/ yola girmesin (eski test/platform.py standart modülü gölgeliyordu)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k else f"  [{ek}]"))
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
g.update(subprocess=SP, modeller_dene=lambda: CAGRI.append(("modeller_dene",)), say=lambda *a, **k: None, whispercpp_baslat=lambda: None, whispercpp_durum=lambda: {}, ayar=lambda: {},
         urllib=type("U", (), {"request": type("Q", (), {"urlopen": staticmethod(lambda *a, **k: (_ for _ in ()).throw(OSError("yok")))})}))
g["guncelleme_sonrasi"]()
ok(f"guncelleme_sonrasi sırası: kur → modeller_dene {CAGRI}", CAGRI[:2] == [("run", ["kurulum.py", "kur"]), ("modeller_dene",)])
g["subprocess"] = type("SP2", (), {"run": staticmethod(lambda c, *a, **k: type("R", (), {"returncode": 1})), "DEVNULL": None})
try: g["guncelleme_sonrasi"](); r = ""
except SystemExit as e: r = str(e)
ok("kur başarısızsa alt komut hata ile çıkar", "geliştiriciye" in r)

# 2) relay.py guncelle_baslat: panodaki düğme toplantı, sohbet ve Konuş cevabında reddeder; boşta güncelleme betiğini başlatır
_g = {f.name: f for f in ast.parse(open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()).body if isinstance(f, ast.FunctionDef)}
fn, fo = _g["guncelle_baslat"], _g["guncelle_oturum_mesgul"]
class P:
    def __init__(self, *a, **k): BASLADI.append(a)
for ad, durum, beklenen in [("boşta", {}, True), ("web toplantısı", {"top": True}, False), ("masaüstü toplantısı", {"masaustu": {"toplantida": True}}, False),
                            ("sohbet açık", {"sohbet": True}, False), ("Konuş konuşuyor", {"konus": "konusuyor"}, False), ("Konuş hazır", {"konus": "hazir"}, True),
                            ("oturum toplantı sonunda", {"to": {"durum": "calisiyor", "sonu": True}}, False), ("oturum cevap bekliyor", {"to": {"durum": "bekliyor", "acik_soru": True}}, False),
                            ("oturum izin bekliyor", {"to": {"durum": "bekliyor", "izinler": [{"id": "x"}]}}, False), ("oturum işi bitmiş", {"to": {"durum": "bekliyor"}}, True)]:
    BASLADI = []
    n = {"guncelleme_view": lambda: {"durum": "var"}, "toplanti_var": lambda d=durum: bool(d.get("top")), "STATE": {"masaustu": durum.get("masaustu")},
         "SOHBET": {"acik": bool(durum.get("sohbet"))}, "KONUS": {"durum": durum.get("konus", "kapali")}, "_t": lambda tr, en: tr,
         "_kod_dir": lambda: "/tmp", "GUN_LOG": os.devnull, "GUN": {"son": "9.9.9"}, "SURUM": "0.0.1", "datetime": __import__("datetime"),
         "os": os, "subprocess": type("S", (), {"Popen": P, "DEVNULL": None, "STDOUT": None}), "print": lambda *a, **k: None, "toplanti_oturum_view": lambda d=durum: d.get("to")}
    exec(compile(ast.Module([fo, fn], []), "relay.py", "exec"), n); r = n["guncelle_baslat"]()
    ok(f"pano Güncelle · {ad} → {r}", bool(r.get("ok")) == beklenen and bool(BASLADI) == beklenen)

# 3) v0.238.3: sihirbazın "Kuruyorum" adımı (tamamla) toplantı sürerken aktarıcı kurulumunu başlatmaz, net hata verir; boştayken kurulumu çalıştırır (sahte süreç, geçici ev)
import tempfile
EVG = tempfile.mkdtemp(prefix="suflor-mesgul-"); os.environ["SUFLOR_EV"] = EVG
sys.argv = ["kurulum.py"]; k = {"__name__": "kurulum_tamamla", "__file__": os.path.join(KOD, "kurulum.py")}
exec(compile(open(k["__file__"], encoding="utf-8").read().split('if __name__ == "__main__":')[0], "kurulum.py", "exec"), k)
os.environ.pop("SUFLOR_EV", None); k["DENEME"] = False; CAGRI = []
class _R: returncode = 0; stdout = ""; stderr = ""
k["subprocess"] = type("S", (), {"run": staticmethod(lambda *a, **b: (CAGRI.append(a), _R())[1]), "Popen": staticmethod(lambda *a, **b: None), "DEVNULL": None})
k["claude_yolu"] = lambda: None
for dil in ("tr", "en"):
    CAGRI.clear(); k["aktarici"] = lambda y: {"extension": {"call": True, "age_s": 3}}; r = k["tamamla"]({"ad": "Deneme"}, dil)
    ok(f"tamamla ({dil}) · toplantı sürerken aktarıcı kurulmaz, aktarici=kotu, hata metni toplantıyı söyler", not CAGRI and r.get("aktarici") == "kotu" and ("toplantı" if dil == "tr" else "meeting") in r.get("hata", ""))
CAGRI.clear(); k["aktarici"] = lambda y: {}; r = k["tamamla"]({"ad": "Deneme"}, "tr")
ok("tamamla · toplantı yokken kurulum çalışır (aktarici=iyi)", len(CAGRI) == 1 and r.get("aktarici") == "iyi" and not r.get("hata"))
shutil.rmtree(EVG, ignore_errors=True)

# 4) 13 Kasım: toplantıda yeniden başlatma yok — kurulum.py aktarici_yeniden_baslat (meşgulse bekleyen işaret, değilse planlı işaret + kickstart) ve
#    aktarıcıdaki bekleyen yeniden başlatma döngüsü (aktarici/beta-veri.py _yb_*; sahte durumla, gerçek launchctl çalışmaz)
import json, subprocess, tempfile, time
_u = tempfile.mkdtemp(prefix="suflor-yb-"); _pl = os.path.join(_u, "x.plist"); open(_pl, "w").write("x"); CK = []
class _Rr: returncode = 0; stdout = ""; stderr = ""
g.update(DENEME=False, yollar=lambda: {"uygulama": _u, "port": 1}, plist_yolu=lambda: _pl, gui=lambda: "gui/501", sessiz=lambda *c, **kw: (CK.append(c), _Rr())[1])
BEK, PLN = os.path.join(_u, "yeniden-baslat-bekliyor.json"), os.path.join(_u, "planli-acilis.json")
g["mesgul"] = lambda: "web toplantısı sürüyor"; CK.clear()
r = g["aktarici_yeniden_baslat"]("ayar")
ok("yardımcı · meşgulken kickstart çağrılmaz, ertelendi", r == "ertelendi" and not CK)
b = json.load(open(BEK)) if os.path.exists(BEK) else {}
ok("yardımcı · meşgulken bekleyen işaret yazılır (yalnız zaman ve neden), planlı işaret yazılmaz", set(b) == {"t", "neden"} and b["neden"] == "ayar" and abs(b["t"] - time.time()) < 5 and not os.path.exists(PLN))
g["mesgul"] = lambda: ""; os.remove(BEK); CK.clear()
r = g["aktarici_yeniden_baslat"]("ses")
pj = json.load(open(PLN)) if os.path.exists(PLN) else {}
ok("yardımcı · boştayken planlı işaret yazılır ve kickstart çağrılır", r == "yapildi" and pj.get("neden") == "ses" and CK == [("launchctl", "kickstart", "-k", "gui/501/" + g["LABEL"])] and not os.path.exists(BEK), (r, CK, pj))
os.remove(PLN); CK.clear(); g["DENEME"] = True
ok("yardımcı · DENEME'de hiçbir şey yapmaz", g["aktarici_yeniden_baslat"]("ayar") == "yok" and not CK and not os.path.exists(PLN) and not os.path.exists(BEK))
g["DENEME"] = False; g["plist_yolu"] = lambda: os.path.join(_u, "yok.plist")
ok("yardımcı · ajan (plist) kurulu değilse hiçbir şey yapmaz", g["aktarici_yeniden_baslat"]("ayar") == "yok" and not CK and not os.path.exists(BEK))
g["plist_yolu"] = lambda: _pl
# ayar kaydedenler yardımcıyı kullanır: toplantıda takvim/e-posta/anımsatıcı kaydı başarılı, kickstart yok, bekleyen işaret var
g["ayar_degistir"] = lambda fn: (fn({}), True)[1]; g["mesgul"] = lambda: "web toplantısı sürüyor"
for ad, cagri in (("takvim_ayarla", lambda: g["takvim_ayarla"](["ben" + chr(64) + "example.com"], [])), ("eposta_ayarla", lambda: g["eposta_ayarla"]("gmail", "")), ("animsatici_ayarla", lambda: g["animsatici_ayarla"](True, "L"))):
    CK.clear()
    if os.path.exists(BEK): os.remove(BEK)
    r = cagri()
    ok(f"{ad} · toplantıda kayıt başarılı, kickstart yok, bekleyen işaret var", r.get("ok") is True and not CK and os.path.exists(BEK), (r, CK))
_src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read().split('if __name__ == "__main__":')[0]
ok("kurulum.py · kickstart yalnız yardımcıda (meşgul denetimsiz çağrı kalmadı)", _src.count('"kickstart"') == 1 and '"kickstart"' in inspect.getsource(g["aktarici_yeniden_baslat"]))
ok("kurulum.py · aktarici_durdur planlı işaret yazar (kur/aktarici-kur yolu)", "planli_isaretle" in inspect.getsource(g["aktarici_durdur"]))
for f_ in (BEK, PLN):
    if os.path.exists(f_): os.remove(f_)
g["DENEME"] = False; CK.clear(); _dp = {}
class _SP2:
    DEVNULL = None
    @staticmethod
    def run(c, *a, **kw): _dp.update(kw); return type("R", (), {"returncode": 1})
g["subprocess"] = _SP2
try: g["guncelleme_sonrasi"]()
except SystemExit: pass
ok("guncelleme_sonrasi · kur alt süreci neden=guncelleme ile başlar", (_dp.get("env") or {}).get("SUFLOR_YB_NEDEN") == "guncelleme")
_planli_ayr = []
g["subprocess"] = subprocess
os.environ["SUFLOR_YB_NEDEN"] = "guncelleme"; g["planli_isaretle"]("guncelleme"); pj = json.load(open(PLN)); os.remove(PLN)
ok("planli_isaretle · neden kaydı", pj["neden"] == "guncelleme")

# 4b) aktarıcı tarafı: bölümü metin olarak çıkar, sahte relay globals'ında sına
_bv = open(os.path.join(KOD, "aktarici", "beta-veri.py"), encoding="utf-8").read()
_bol = _bv.split("# --- yeniden-baslat başlangıç", 1)[1].split("# --- yeniden-baslat bitiş ---")[0].split("\n", 1)[1]
_bu = tempfile.mkdtemp(prefix="suflor-yb2-"); OLAY = []; BAS = []
G = {"json": json, "os": os, "time": time, "threading": None, "AYAR": {"uygulama": _bu}, "BASE": os.path.join(_bu, "canli"), "A": type("A", (), {"port": 8765}), "BETA_TEST": False,
     "beta_olay": lambda a: OLAY.append(a), "beta_say": lambda a, b, c: 0,
     "eklenti_cagri": lambda: None, "masaustu_toplantida": lambda: False, "toplanti_var": lambda: False, "sohbet_view": lambda: {"acik": False}, "KONUS": {"durum": "hazir"}, "toplanti_oturum_view": lambda: None}
exec(compile(_bol, "beta-veri-yb", "exec"), G)
BEKA, PLNA = G["YB_BEKLEYEN"], G["YB_PLANLI"]
G["_yb_baslat"] = lambda: BAS.append(1); G["_yb_bizim"] = lambda: True
ok("döngü · bekleyen işaret yokken hiçbir şey yapmaz", G["_yb_dene"]() == "yok" and not BAS)
G["_yb_yaz"](BEKA, "ayar")
for ad, d in (("web toplantısı", {"eklenti_cagri": lambda: {"x": 1}}), ("masaüstü toplantısı", {"masaustu_toplantida": lambda: True}), ("kayıt süren toplantı", {"toplanti_var": lambda: True}),
              ("sohbet", {"sohbet_view": lambda: {"acik": True}}), ("Konuş cevabı", {"KONUS": {"durum": "dusunuyor"}}),
              ("toplantı oturumu çalışıyor", {"toplanti_oturum_view": lambda: {"durum": "calisiyor"}}), ("oturum izin bekliyor", {"toplanti_oturum_view": lambda: {"durum": "bekliyor", "izin": 1}}),
              ("oturum toplantı sonu", {"toplanti_oturum_view": lambda: {"durum": "bekliyor", "sonu": True}}), ("durum okunamıyor (hata)", {"sohbet_view": lambda: 1 / 0})):
    eski = {k_: G[k_] for k_ in d}; G.update(d); BAS.clear()
    r = G["_yb_dene"](); r2 = G["_yb_dene"]()
    ok(f"döngü · {ad} sürerken yeniden başlatmaz, bekleyen işaret kalır", r == r2 == "mesgul" and not BAS and os.path.exists(BEKA), (r, r2)); G.update(eski)
ok("döngü · boş: ilk yoklamada beklenir (art arda iki boş yoklama gerekir)", G["_yb_dene"]() == "bekle" and not BAS and os.path.exists(BEKA))
G["eklenti_cagri"] = lambda: {"x": 1}; G["_yb_dene"](); G["eklenti_cagri"] = lambda: None
ok("döngü · araya giren meşgul yoklama sayacı sıfırlar", G["_yb_dene"]() == "bekle" and not BAS)
r = G["_yb_dene"]()
pj = json.load(open(PLNA)) if os.path.exists(PLNA) else {}
ok("döngü · iki boş yoklamadan sonra yeniden başlatır: planlı işaret (bekleyen) yazılır, bekleyen işaret silinir", r == "yeniden" and BAS == [1] and pj.get("neden") == "bekleyen" and not os.path.exists(BEKA), (r, pj))
G["_yb_yaz"](BEKA, "ayar"); G["_YB"]["bos"] = 5; G["_yb_bizim"] = lambda: False; BAS.clear()
ok("döngü · ajan bu aktarıcının değilse (deneme) yeniden başlatmaz, işareti siler", G["_yb_dene"]() == "bizim_degil" and not BAS and not os.path.exists(BEKA))
G["_yb_bizim"] = lambda: True
# açılış: planlı işaret taze → acilis_planli; yok/eski → acilis; bekleyen işaret açılışta silinir
for ad, hazir, bek in (("taze işaret", lambda: G["_yb_yaz"](PLNA, "ayar"), "acilis_planli"), ("işaret yok", lambda: None, "acilis"),
                       ("eski işaret (11 dk)", lambda: json.dump({"t": time.time() - 660, "neden": "ayar"}, open(PLNA, "w")), "acilis"),
                       ("bozuk işaret", lambda: open(PLNA, "w").write("{"), "acilis"), ("gelecekteki zaman", lambda: json.dump({"t": time.time() + 3600}, open(PLNA, "w")), "acilis")):
    for f_ in (PLNA, BEKA): 
        if os.path.exists(f_): os.remove(f_)
    hazir(); G["_yb_yaz"](BEKA, "ayar"); OLAY.clear(); G["_beta_acilis_say"]()
    ok(f"açılış · {ad} → {bek}, işaretler silinir", OLAY == [bek] and not os.path.exists(PLNA) and not os.path.exists(BEKA), OLAY)
_yb_kod = _bv.split("# --- yeniden-baslat bitiş ---")[1].split("\n")
ok("beta-veri · açılışta sayım ve döngü iş parçacığı yerinde", any(l.startswith("_beta_acilis_say()") for l in _yb_kod) and any("_yb_dongu" in l and "Thread" in l for l in _yb_kod))
shutil.rmtree(_u, ignore_errors=True); shutil.rmtree(_bu, ignore_errors=True)

print("guncelle-mesgul: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
