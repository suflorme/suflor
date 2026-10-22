#!/usr/bin/env python3
# Oturumlar arası commit/kurulum protokolü (S104, oturum.py): geçici git deposunda — sahiplik çakışması, kanca başkasının dosyasını ve başkasının kilidini
# durdurur, kendi dosyasını geçirir; kurulum kaydedilmemiş kodda ve başkasının kilidinde durur; işaret yoksa (beta kullanıcısı) hiçbiri devreye girmez (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/oturum.py
import os, shutil, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="oturum-"); shutil.copy(os.path.join(KOD, "oturum.py"), T)
def sh(*a, ad=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    e.pop("SUFLOR_OTURUM", None)
    if ad: e["SUFLOR_OTURUM"] = ad
    return subprocess.run(list(a), cwd=T, capture_output=True, text=True, env=e)
ot = lambda *a, ad=None: sh(sys.executable, "-B", "oturum.py", *a, ad=ad)
try:
    sh("git", "init", "-q"); open(os.path.join(T, "a.py"), "w").write("a\n"); open(os.path.join(T, "b.py"), "w").write("b\n")
    sh("git", "add", "."); sh("git", "commit", "-qm", "ilk")
    open(os.path.join(T, "a.py"), "a").write("x\n")
    ok("işaret yokken kurulum denetimi geçer (beta kullanıcısı)", ot("--kurulum").returncode == 0)
    ok("kur: işaret + kanca", ot("kur").returncode == 0 and os.path.exists(os.path.join(T, ".git", "suflor-protokol")) and "oturum.py" in open(os.path.join(T, ".git", "hooks", "pre-commit")).read())
    ok("sahiplen: bir", ot("sahiplen", "bir", "a.py").returncode == 0)
    r = ot("sahiplen", "iki", "a.py"); ok("sahiplen: başkasının dosyası durur", r.returncode == 2 and "bir" in r.stdout)
    sh("git", "add", "a.py"); r = sh("git", "commit", "-qm", "iki", ad="iki")
    ok("kanca: başkasının dosyası commit'e giremez", r.returncode != 0 and "başka oturumun" in r.stdout + r.stderr)
    r = sh("git", "commit", "-qm", "adsız"); ok("kanca: adsız commit de başkasının dosyasını alamaz", r.returncode != 0)
    r = ot("--kurulum"); ok("kurulum: kaydedilmemiş kod varken durur, sahibini söyler", r.returncode == 1 and "a.py" in r.stdout and "bir" in r.stdout)
    r = sh("git", "commit", "-qm", "bir", ad="bir"); ok("kanca: kendi dosyası geçer", r.returncode == 0)
    ok("kurulum: temiz klasörde geçer", ot("--kurulum").returncode == 0)
    # v0.117.1: izlenmeyen dosya yalnız kurulumun kopyaladığı yerdeyse durdurur (kurulum.py KOPYA; okunamazsa hepsi durdurur)
    open(os.path.join(T, "notlar.txt"), "w").write("x\n")
    ok("kurulum: kurulum.py yokken izlenmeyen dosya durdurur (eski davranış)", ot("--kurulum").returncode == 1)
    open(os.path.join(T, "kurulum.py"), "w").write('KOPYA = ["relay.py", "aktarici/", "pano/", "marka/*.svg"]\n'); sh("git", "add", "kurulum.py"); sh("git", "commit", "-qm", "kurulum")
    ok("kurulum: kopyalanmayan yerdeki izlenmeyen dosya durdurmaz", ot("--kurulum").returncode == 0)
    os.makedirs(os.path.join(T, "aktarici")); open(os.path.join(T, "aktarici", "yeni.py"), "w").write("x\n")
    r = ot("--kurulum"); ok("kurulum: aktarici/ altındaki izlenmeyen dosya durdurur (canlıya gider)", r.returncode == 1 and "aktarici/yeni.py" in r.stdout)
    os.remove(os.path.join(T, "aktarici", "yeni.py")); os.makedirs(os.path.join(T, "marka")); open(os.path.join(T, "marka", "a.svg"), "w").write("x\n")
    ok("kurulum: desene uyan izlenmeyen dosya (marka/*.svg) durdurur", ot("--kurulum").returncode == 1)
    os.remove(os.path.join(T, "marka", "a.svg")); os.remove(os.path.join(T, "notlar.txt"))
    ok("kilit: bir alır", ot("kilit", "bir", "v1 yayın").returncode == 0)
    r = ot("kilit", "iki", "v2"); ok("kilit: başkasındayken durur", r.returncode == 2 and "bir" in r.stdout)
    r = ot("--kurulum", ad="iki"); ok("kurulum: başkasının kilidinde durur", r.returncode == 1 and "kilidi" in r.stdout)
    ok("kurulum: kilit sahibi kurabilir", ot("--kurulum", ad="bir").returncode == 0)
    ok("yayın: başkasının kilidinde durur, sahibi yayınlar", ot("--yayin", ad="iki").returncode == 1 and ot("--yayin", ad="bir").returncode == 0)
    open(os.path.join(T, "b.py"), "a").write("y\n"); sh("git", "add", "b.py"); r = sh("git", "commit", "-qm", "iki b", ad="iki")
    ok("kanca: başkasının kilidi açıkken commit durur (sürüm çakışmasın)", r.returncode != 0 and "kilidi" in r.stdout + r.stderr)
    ok("coz: başkası çözemez", ot("coz", "iki").returncode == 2)
    ok("coz: sahibi çözer", ot("coz", "bir").returncode == 0)
    ok("kilit çözülünce commit geçer", sh("git", "commit", "-qm", "iki b", ad="iki").returncode == 0)
    ok("birak: kayıt kalkar, başkası sahiplenebilir", ot("birak", "bir").returncode == 0 and ot("sahiplen", "iki", "a.py").returncode == 0)
    ok("durum çalışır", "Yayın kilidi: boş" in ot("durum").stdout)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("oturum: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
