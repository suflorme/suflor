#!/usr/bin/env python3
# Beta profili tek kaynak (10 Kasım): kurulum sihirbazının profil notu asistanın okuduğu profil dosyasına yazılır (kisi-modeli.py profil_yol ile aynı yol);
# CLAUDE.md'deki bölüm (ilk toplantı onay adımı için) kalır; kullanıcının yazdığı profile dokunulmaz. Sahte Claude, geçici klasör.
# Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/profil-notu.py
import ast, datetime, json, os, re, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read(); a = ast.parse(src)
AD = {"profil", "profil_gerekli", "profil_dosyasi", "profil_nota_yaz"}; VAR = {"PROFIL_BASLIK", "PROFIL_KR", "PROFIL_ISTEM"}
sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in AD) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in VAR for x in n.targets))]
T = tempfile.mkdtemp(); proje = os.path.join(T, "calisma"); uyg = os.path.join(T, "uygulama"); os.makedirs(os.path.join(proje, "gorusmeler")); os.makedirs(uyg)
cm = os.path.join(proje, "CLAUDE.md"); open(cm, "w").write("# Çalışma klasörü\n")
AY = {"dil": "tr", "calisma": proje, "uygulama": uyg}; CEVAP = {"ad": "Deniz T", "rol": "satın alma müdürü", "kisiler": "Aylin K, Berk Y"}
NOT = "Deniz satın alma müdürü. " + "Tedarikçi toplantılarında vade ve fiyat öne çıkar. " * 80
say_log = []
def sahte_run(*a_, **k): return subprocess.CompletedProcess(a_, 0, stdout=json.dumps({"not": NOT, "terimler": ["Akbank", "Suflor.me"]}), stderr="")
sp = type("SP", (), {"run": staticmethod(sahte_run), "PIPE": None})
ns = {"os": os, "re": re, "json": json, "datetime": datetime, "subprocess": sp, "ayar": lambda: AY, "oku_json": lambda y: {"cevap": CEVAP}, "KAYIT": "x", "claude_yolu": lambda: "/bin/claude",
      "gen": lambda p: os.path.expanduser(p), "say": say_log.append, "glob_ornek": lambda d: [], "ayar_degistir": lambda f: None}
exec(compile(ast.Module(sec, []), "kurulum.py", "exec"), ns); hata = 0
def ok(ad, c):
    global hata; hata += not c; print(("✓ " if c else "✗ ") + ad)
py = os.path.join(uyg, "profil.md")
ok("profil_dosyasi: ayar yoksa <uygulama>/profil.md", ns["profil_dosyasi"](AY) == py)
ok("profil_dosyasi: ayar kisilik_bellek önde", ns["profil_dosyasi"](dict(AY, kisilik_bellek=os.path.join(T, "k.md"))) == os.path.join(T, "k.md"))
# 1) profil dosyası yok → oluşur, not içinde, sınır içinde, CLAUDE.md'de yalnız gösterici
ns["profil"]()
p = open(py).read(); c = open(cm).read()
ok("profil dosyası oluştu (0600), başlık + not + kişiler", os.stat(py).st_mode & 0o777 == 0o600 and "## Ben ve işim (taslak)" in p and "satın alma müdürü" in p and "Aylin K" in p)
ok("profil dosyası ≤ 3000 karakter", len(p) <= 3000)
ok("CLAUDE.md'de bölüm eskisi gibi duruyor (onay adımı için), profil dosyasıyla aynı metin", "## Ben ve işim (taslak)" in c and "Tedarikçi toplantılarında" in c and c.split("## Ben ve işim")[1] == p.split("## Ben ve işim")[1])
# 2) ikinci çalışma: değişmez
ns["profil"](); ok("ikinci çalışmada profil ve CLAUDE.md değişmedi", open(py).read() == p and open(cm).read() == c)
# 3) kullanıcının yazdığı profil: dokunulmaz, not CLAUDE.md'ye eski gibi
os.remove(py); open(py, "w").write("# Profil\n\n## Kim\n- Deniz, satın alma\n\n## Öncelikler\n- Vade\n"); open(cm, "w").write("# Çalışma klasörü\n")
ns["profil"](); ok("kullanıcı yazdıysa profil dosyası aynı kaldı", open(py).read().startswith("# Profil\n\n## Kim\n- Deniz, satın alma") and "taslak" not in open(py).read())
ok("kullanıcı yazdıysa not yine de CLAUDE.md'de (kayıp yok)", "Tedarikçi toplantılarında" in open(cm).read())
# 4) kurulumun boş iskeleti (profil_kur çıktısı): not eklenir
iskelet = "# Profil\n\n## Kim\n- Ad: Deniz T\n\n## Çalışma düzeni\n- (henüz yazılmadı)\n\n## Öncelikler ve tercihler\n- (henüz yazılmadı)\n"
open(py, "w").write(iskelet); open(cm, "w").write("# Çalışma klasörü\n"); ns["profil"]()
p4 = open(py).read(); ok("iskelet profile not eklendi, iskelet korundu, ≤ 3000", p4.startswith(iskelet.rstrip()) and "## Ben ve işim (taslak)" in p4 and len(p4) <= 3000)
# 5) ayar kisilik_bellek: o dosyaya yazılır
kb = os.path.join(T, "baska", "kart.md"); AY["kisilik_bellek"] = kb; open(cm, "w").write("# Çalışma klasörü\n"); ns["profil"]()
ok("kisilik_bellek yoksa oraya oluşturulur", os.path.exists(kb) and "satın alma müdürü" in open(kb).read())
# 6) asistanın okuyucusu (kisi-modeli.py) bu dosyayı görür: profil_yol aynı çözüm
km = open(os.path.join(KOD, "aktarici", "kisi-modeli.py"), encoding="utf-8").read()
ok("kisi-modeli.py profil_yol aynı iki yolu kullanıyor (kisilik_bellek, <uygulama>/profil.md)", 'AYAR.get("kisilik_bellek")' in km and 'os.path.join(AYAR["uygulama"], "profil.md")' in km)
print("profil-notu: ✓ hepsi geçti" if not hata else f"profil-notu: ✗ {hata} hata"); sys.exit(1 if hata else 0)
