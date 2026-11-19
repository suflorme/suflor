#!/usr/bin/env python3
# pano-denetim.py: mevcut ağaç temiz geçer; kopyada kaçışsız kesme işareti (pano/js betik dosyaları, pano.html satır içi betiği, eklenti JS'i)
# ve dosyalar arası hata (birleşik pano/js) yakalanır.
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
    # pano.html'in betiği pano/js/NN-ad.js'de (adım 4): hata dosya ve satırıyla gösterilir, birleşik denetim aynı hatayı ikinci kez saymaz
    pj = pd.pano_js_dosyalari(T); ok("pano/js dosyaları bulunur (sıralı)", len(pj) >= 10 and pj == sorted(pj))
    hf = next(f for f in pj if "L('" in open(f, encoding="utf-8").read()); s = open(hf, encoding="utf-8").read(); i = s.index("L('")
    open(hf, "w", encoding="utf-8").write(s[:i + 3] + "Bu Teams'te çalışır " + s[i + 3:])
    h = pd.denetle(T); ok("pano/js dosyasında kaçışsız kesme yakalanır", len(h) == 1 and h[0].startswith(os.path.relpath(hf, T) + ":"))
    if h:
        satir = int(h[0].split(":")[1].split()[0]); ok("satır numarası enjekte satırı gösterir", s.count("\n", 0, i) + 1 - 1 <= satir <= s.count("\n", 0, i) + 3)
    open(hf, "w", encoding="utf-8").write(s)
    # dosyalar tek tek temiz ama birlikte hatalı: aynı üst düzey let iki dosyada (tek <script> olarak sunulur)
    open(pj[0], "a", encoding="utf-8").write("let kImza=1\n")
    h = pd.denetle(T); ok("dosyalar arası hata (iki kez let) birleşik denetimde yakalanır", len(h) == 1 and h[0].startswith("pano/js (birleşik)"))
    shutil.copy(os.path.join(KOD, "pano", "js", os.path.basename(pj[0])), pj[0])
    s = open(os.path.join(T, "pano", "pano.html"), encoding="utf-8").read(); i = s.index("<script>", s.index("__ANAHTAR__"))
    open(os.path.join(T, "pano", "pano.html"), "w", encoding="utf-8").write(s[:i + 8] + "const x = 'a'b';" + s[i + 8:])
    h = pd.denetle(T); ok("pano.html satır içi betikte kaçışsız kesme yakalanır", len(h) == 1 and h[0].startswith(os.path.join("pano", "pano.html") + ":"))
    shutil.copy(os.path.join(KOD, "pano", "pano.html"), os.path.join(T, "pano", "pano.html"))
    ok("kopya yeniden temiz", pd.denetle(T) == [])
    open(os.path.join(T, "content.js"), "a").write("\nconst x = 'a'b';\n")
    h = pd.denetle(T); ok("eklenti JS hatası yakalanır", len(h) == 1 and h[0].startswith("content.js:"))
    ok("komut satırı çıkış kodu 1", os.system(f'{sys.executable} -B "{os.path.join(KOD, "pano-denetim.py")}" "{T}" >/dev/null') != 0)
finally: shutil.rmtree(T, ignore_errors=True)
print("TAMAM" if not HATA else f"{len(HATA)} hata"); sys.exit(1 if HATA else 0)
