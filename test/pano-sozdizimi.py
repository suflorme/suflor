#!/usr/bin/env python3
# pano-denetim.py: mevcut ağaç temiz geçer; kopyada kaçışsız kesme işareti (pano.html satır içi betiği ve eklenti JS'i) yakalanır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/pano-sozdizimi.py
import importlib, os, shutil, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
sys.path.insert(0, KOD); pd = importlib.import_module("pano-denetim")
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
if not pd.node_bul(): print("UYARI: node yok, test atlandı"); sys.exit(0)
ok("mevcut ağaç temiz", pd.denetle(KOD) == [])
T = tempfile.mkdtemp(prefix="pano-sozdizimi-")
try:
    for d in ("pano", "sihirbaz"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
    shutil.copy(os.path.join(KOD, "content.js"), T)
    s = open(os.path.join(T, "pano", "pano.html"), encoding="utf-8").read(); i = s.index("L('")
    open(os.path.join(T, "pano", "pano.html"), "w", encoding="utf-8").write(s[:i + 3] + "Bu Teams'te çalışır " + s[i + 3:])
    h = pd.denetle(T); ok("pano.html'de kaçışsız kesme yakalanır", len(h) == 1 and h[0].startswith(os.path.join("pano", "pano.html") + ":"))
    if h:
        satir = int(h[0].split(":")[1].split()[0]); ok("satır numarası enjekte satırı gösterir", s.count("\n", 0, i) + 1 - 1 <= satir <= s.count("\n", 0, i) + 3)
    shutil.copy(os.path.join(KOD, "pano", "pano.html"), os.path.join(T, "pano", "pano.html"))
    open(os.path.join(T, "content.js"), "a").write("\nconst x = 'a'b';\n")
    h = pd.denetle(T); ok("eklenti JS hatası yakalanır", len(h) == 1 and h[0].startswith("content.js:"))
    ok("komut satırı çıkış kodu 1", os.system(f'{sys.executable} -B "{os.path.join(KOD, "pano-denetim.py")}" "{T}" >/dev/null') != 0)
finally: shutil.rmtree(T, ignore_errors=True)
print("TAMAM" if not HATA else f"{len(HATA)} hata"); sys.exit(1 if HATA else 0)
