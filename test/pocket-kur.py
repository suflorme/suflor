# Sihirbazdan Pocket yerel Türkçe ses kurulumu (kurulum.py pocket_kur/pocket_baslat/pocket_durum, yerel_ses_bul): sahte Python ile — ağ yok, gerçek indirme
# yok. Adımlar (ortam → model → deneme açılışı → ayar), hata yolunda ayarın değişmemesi ve isteğin kalması, kurulu olanın yeniden kurulmaması,
# elle verilen yolun ve ses_motoru seçiminin korunması, ikinci hesabın ortak klasördeki kurulumu bulması, deneme sihirbazının indirmemesi.
# Gerçek kurulum (PyPI + Hugging Face'ten ~1,3 GB, ~2 dk; geçici ortak klasöre, sonra silinir): SUFLOR_POCKET_GERCEK=1 — canlı toplantıda bekler (bosport AGIR_TESTLER).
# Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/pocket-kur.py
import os, sys, json, tempfile, shutil, importlib.util, stat
KOD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV = tempfile.mkdtemp(prefix="pocket-kur-"); os.environ["SUFLOR_EV"] = EV; sys.dont_write_bytecode = True
os.environ.pop("SUFLOR_TEST_POCKET", None)
sp = importlib.util.spec_from_file_location("kurulum", os.path.join(KOD, "kurulum.py")); K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
ORT = os.path.join(EV, "ortak"); os.makedirs(ORT); K.ORTAK = ORT
if os.environ.get("SUFLOR_POCKET_GERCEK"):
    import time; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: F401 — canlı toplantı sürerken bekler
    if os.path.isdir("/Users/Shared/Suflor/python312"): os.symlink("/Users/Shared/Suflor/python312", os.path.join(ORT, "python312"))  # 17 MB'ı yeniden indirme
    t = time.time(); sonuc = K.pocket_kur(ORT); sn = time.time() - t; a = K.ayar(); vpy, hf = K.pocket_yollar(ORT)
    iyi = sonuc and a.get("pocket_python") == vpy and a.get("pocket_hf") == hf and K.pocket_hazir(ORT)
    print(("✓ " if iyi else "✗ ") + f"gerçek kurulum {sn:.0f} sn, {sum(K._boyut(y) for y in (os.path.join(ORT, 'pocket-venv'), hf)) / 2 ** 30:.2f} GB, ayar yazıldı, deneme açılışı geçti")
    shutil.rmtree(EV, ignore_errors=True); sys.exit(0 if iyi else 1)
CAGRI = os.path.join(EV, "cagri.log")
SAHTE = f"""#!/usr/bin/python3
import os, sys
a = sys.argv[1:]; kok = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
open({CAGRI!r}, "a").write(" ".join(a[:3]) + "\\n")
if a[:2] == ["-m", "venv"]:
    os.makedirs(os.path.join(a[2], "bin")); y = os.path.join(a[2], "bin", "python"); open(y, "w").write(open(sys.argv[0]).read()); os.chmod(y, 0o755); sys.exit(0)
if a[:2] == ["-m", "pip"]:
    if "-r" in a: open(os.path.join(kok, "kuruldu"), "w").write(open(a[a.index("-r") + 1]).read())
    sys.exit(0)
if a and a[0] == "-c" and "version_info" in a[1]: sys.exit(0)
if a and a[0] == "-c" and "importlib.metadata" in a[1]: sys.exit(0 if os.path.exists(os.path.join(kok, "kuruldu")) else 1)
if a and a[0] == "-c" and "snapshot_download" in a[1]:
    if os.environ.get("SAHTE_HATA") == "model": sys.exit(1)
    d = os.path.join(os.environ["HF_HOME"], "hub", "models--" + a[2].replace("/", "--"), "snapshots", a[3]); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "model.safetensors"), "w").write("x"); sys.exit(0)
if a and a[0].endswith("pocket-isci.py"):
    sys.stdin.readline(); print('{{"hazir": true}}'); print('{{"id": "d", "bitti": true, "n": 1}}'); sys.exit(0)
sys.exit(2)
"""
os.makedirs(os.path.join(ORT, "python312", "bin")); PY312 = os.path.join(ORT, "python312", "bin", "python3.12")
open(PY312, "w").write(SAHTE); os.chmod(PY312, 0o755)
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
def cagrilar():
    try: return open(CAGRI).read().splitlines()
    except OSError: return []
VPY, HF = K.pocket_yollar(ORT)
try:
    kontrol("başta kurulu değil; durum 'yok'", not K.pocket_kurulu() and K.pocket_durum()["durum"] == "yok")
    d = K.pocket_baslat()
    kontrol("deneme sihirbazı indirmez, yalnız isteği kaydeder", K.ayar().get("pocket_iste") is True and K.POCKET["p"] is None and not cagrilar())
    # model indirilemezse
    os.environ["SAHTE_HATA"] = "model"
    kontrol("model inmezse: False, ayara yol yazılmaz, istek kalır", K.pocket_kur(ORT) is False and not K.ayar().get("pocket_python") and K.ayar().get("pocket_iste"))
    c = cagrilar()
    s1 = [next((i for i, x in enumerate(c) if x.startswith(k)), -1) for k in ("-m venv", "-m pip install", "-c import sys; from huggingface_hub")]
    kontrol("sıra: venv → pip (gereksinim dosyası) → model; deneme açılışına gelmez", -1 not in s1 and s1 == sorted(s1) and not any("pocket-isci.py" in x for x in c)
            and "pocket-tts==3.3.0" in open(os.path.join(ORT, "pocket-venv", "kuruldu")).read())
    open(K._pocket_log(), "w").write("→ ses modeli…\nNot: doğal Türkçe ses kurulamadı (ses modeli indirilemedi) — asistan Mac sesiyle konuşur\n")
    d = K.pocket_durum()
    kontrol("durum 'hata' ve kısa neden", d["durum"] == "hata" and "indirilemedi" in d["mesaj"])
    del os.environ["SAHTE_HATA"]; open(CAGRI, "w").close()
    kontrol("yeniden deneme: kurulu ortam korunur, yalnız model + deneme açılışı; True", K.pocket_kur(ORT) is True and
            not any(x.startswith("-m") for x in cagrilar()) and any("pocket-isci.py" in x for x in cagrilar()))
    a = K.ayar()
    kontrol("ayar: pocket_python/pocket_hf ortak klasörde, ses_motoru pocket, istek silindi",
            a.get("pocket_python") == VPY and a.get("pocket_hf") == HF and a.get("ses_motoru") == "pocket" and "pocket_iste" not in a)
    kontrol("kurulu sayılıyor; durum 'hazir'", K.pocket_kurulu() and K.pocket_durum()["durum"] == "hazir")
    open(CAGRI, "w").close(); K.pocket_kur(ORT); c = cagrilar()
    kontrol("kurulu olan yeniden kurulmaz (yalnız deneme açılışı)", not any("venv" in x or "pip" in x or "snapshot" in x for x in c) and any("pocket-isci.py" in x for x in c))
    # elle verilen çalışan yol ve başka ses motoru korunur
    elle = os.path.join(EV, "elle-python"); open(elle, "w").write(SAHTE); os.chmod(elle, 0o755)
    K.ayar_degistir(lambda a: a.update(pocket_python=elle, ses_motoru="gemini", pocket_iste=True)); K.pocket_kur(ORT); a = K.ayar()
    kontrol("elle verilen çalışan yol ve ses_motoru gemini korunur", a["pocket_python"] == elle and a["ses_motoru"] == "gemini")
    # ikinci hesap: ayarı boş hesap ortak klasördeki kurulumu bulur
    b = {}; y = K.yerel_ses_bul(b, ORT)
    kontrol("ikinci hesap: yerel_ses_bul ortak klasördeki pocket-venv'i bulur", b.get("pocket_python") == VPY and b.get("pocket_hf") == HF and "pocket_python" in y)
    # asistan adımı: kurulu değilken seçilen ses yalnız indirme istendiyse yazılır (S135; kurulana kadar aktarıcı Mac sesine düşer)
    shutil.rmtree(os.path.join(ORT, "pocket-modeller")); K.ayar_degistir(lambda a: [a.pop(k, None) for k in ("pocket_python", "pocket_hf", "ses_motoru", "pocket_iste")] and None)
    a1 = {"ad": "Ayşe"}; K.asistan_uygula(a1, {"asistan": {"liste": [{"ad": "Defne", "ses": "kadin"}]}}, "tr")
    kontrol("istek yokken kadın sesi seçilse de Mac sesi (dosyada yerel_ses yok)", "yerel_ses" not in open(K.gen(a1["kisilik"]), encoding="utf-8").read() and "ses_motoru" not in a1)
    a2 = {"ad": "Ayşe", "pocket_iste": True}
    K.asistan_uygula(a2, {"asistan": {"iki": True, "liste": [{"ad": "Ece", "ses": "erkek"}, {"ad": "Nil", "ses": "mac"}]}}, "tr")
    m1, m2 = (open(K.gen(a2[k]), encoding="utf-8").read() for k in ("kisilik", "kisilik_toplanti_disi"))
    kontrol("indirme istendiyse: erkek sesi dosyada, öbür asistan Mac'te kalır, ses_motoru pocket", "yerel_ses: pocket:wite:male_1" in m1 and "yerel_ses: mac" in m2 and a2.get("ses_motoru") == "pocket")
    kontrol("İngilizce kurulumda Pocket sesi yazılmaz", (lambda a3: (K.asistan_uygula(a3, {"asistan": {"liste": [{"ad": "Mia", "ses": "kadin"}]}}, "en"), "yerel_ses" not in open(K.gen(a3["kisilik"]), encoding="utf-8").read())[1])({"ad": "Ann", "pocket_iste": True}))
    # ikinci hesapta ortak klasör yazılamazsa kurmaya kalkmaz
    shutil.rmtree(os.path.join(ORT, "pocket-venv")); os.chmod(ORT, stat.S_IRUSR | stat.S_IXUSR); open(CAGRI, "w").close()
    kontrol("ortak klasör yazılamıyorsa: False, hiçbir komut çalışmaz", K.pocket_kur(ORT) is False and not cagrilar())
    os.chmod(ORT, 0o755)
finally:
    os.chmod(ORT, 0o755); shutil.rmtree(EV, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
