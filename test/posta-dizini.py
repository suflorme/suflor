#!/usr/bin/env python3
# Geri bildirim posta kutusu hedefi: ikinci macOS hesabında ortak yol hesaba özel yedeğe (Suflor-ortak) düşse bile raporlar
# paylaşılan kutuya (<paylaşılan>/geri-bildirim, 1777) gider; kutu yoksa (beta kullanıcısı) ya da ortak yol elle verilmişse davranış değişmez.
# Sahte paylaşılan klasör SUFLOR_TEST_PAYLASILAN ile verilir; gerçek kutuya yazılmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/posta-dizini.py      (kaldı → çıkış 1)
import contextlib, importlib.util, io, os, re, shutil, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-pd-"); pay = os.path.join(T, "Shared", "Suflor"); os.makedirs(pay)
yedek = os.path.join(T, "ev", "Library", "Application Support", "Suflor-ortak"); os.makedirs(yedek)
os.environ["SUFLOR_TEST_PAYLASILAN"] = pay; os.environ["SUFLOR_EV"] = os.path.join(T, "ev")
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json"); open(os.environ["SUFLOR_AYAR"], "w").write("{}")
sys.path.insert(0, KOD)
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
def yukle(ad, dosya, argv=None):
    sys.argv = argv or [ad]; sp = importlib.util.spec_from_file_location(ad, os.path.join(KOD, dosya)); m = importlib.util.module_from_spec(sp)
    with contextlib.redirect_stdout(io.StringIO()): sp.loader.exec_module(m)
    return m
try:
    k = yukle("kurulum_t", "kurulum.py"); tc = yukle("tc_t", "toplanti-claude.py", ["tc", "--dir", T, "acik"])
    src = open(os.path.join(KOD, "aktarici", "duman.py"), encoding="utf-8").read()
    ns = {"os": os}; exec(re.search(r"def posta_dizini\(ortak\):.*?\n    return [^\n]*\n", src, re.S).group(0), ns); dm = ns["posta_dizini"]
    kutu = os.path.join(pay, "geri-bildirim")
    for ad, f in (("kurulum", k.posta_dizini), ("toplanti-claude", tc.posta_dizini), ("duman", dm)):
        kontrol(f"{ad}: kutu yokken (beta) hesaba özel yol korunur", f(yedek) == os.path.join(yedek, "geri-bildirim"))
    os.makedirs(kutu); os.chmod(kutu, 0o1777)
    for ad, f in (("kurulum", k.posta_dizini), ("toplanti-claude", tc.posta_dizini), ("duman", dm)):
        kontrol(f"{ad}: ikinci hesapta (Suflor-ortak) paylaşılan kutuya gider", f(yedek) == kutu)
        kontrol(f"{ad}: paylaşılan ortak yol aynen kalır", f(pay) == kutu)
        el = os.path.join(T, "baska"); kontrol(f"{ad}: elle verilen başka ortak yol değişmez", f(el) == os.path.join(el, "geri-bildirim"))
    os.chmod(kutu, 0o555)
    if os.geteuid() != 0: kontrol("kutu yazılamazsa hesaba özel yola düşer", k.posta_dizini(yedek) == os.path.join(yedek, "geri-bildirim"))
    os.chmod(kutu, 0o1777)
    kontrol("toplanti-claude GB_DIR ikinci hesapta paylaşılan kutu", tc.__dict__["GB_DIR"]() != "" and tc.posta_dizini(yedek) == kutu)
finally:
    os.system(f"chmod -R u+w '{T}'"); shutil.rmtree(T, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} geçti"); sys.exit(0 if all(ok) else 1)
