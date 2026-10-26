#!/usr/bin/env python3
# v0.136.0 — güncellemede eski sürümden kalan dosyalar: önceki imzalı listede (IMZA/dosyalar.sha256) olup yenisinde olmayan ve özeti
# değişmemiş dosya silinir; kullanıcının koyduğu ya da değiştirdiği dosya, kısayol ve liste dışı yol kalır. İki uygulama aynı kuralla:
# kurulum.py eski_dosyalari_temizle (guncelle.command) ve kur.sh'deki bash bloğu (# eski-dosya-basi … sonu). Geçici klasörde (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/eski-dosya.py
import ast, hashlib, os, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""))
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read())
ns = {"os": os}; exec(compile(ast.Module([n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name in ("imza_listesi", "eski_dosyalari_temizle")], []), "kurulum.py", "exec"), ns)
sha = lambda b: hashlib.sha256(b).hexdigest()
ESKI = {"relay.py": b"yeni surumde de var", "ses-isci.py": b"kalkan betik", "pano/hazirlik.html": b"kalkan sayfa", "test/platform.py": b"kalkan test",
        "degisti.py": b"orijinal", "kisayol.py": b"hedef", "kur.command": b"kalkan ama kullanici degistirdi"}
YENI = {"relay.py": b"yeni surumde de var", "pano/pano.html": b"yeni"}
def liste(d): return "SHA256 başlık\n" + "".join(f"{sha(b)}  {y}\n" for y, b in d.items())
def kur(kok):
    for y, b in ESKI.items():
        os.makedirs(os.path.dirname(os.path.join(kok, y)) or kok, exist_ok=True); open(os.path.join(kok, y), "wb").write(b)
    open(os.path.join(kok, "degisti.py"), "wb").write(b"kullanici degistirdi")       # özet farklı → kalır
    open(os.path.join(kok, "kur.command"), "wb").write(b"baska icerik")              # özet farklı → kalır
    os.remove(os.path.join(kok, "kisayol.py")); os.symlink("/etc/hosts", os.path.join(kok, "kisayol.py"))  # kısayol → kalır
    open(os.path.join(kok, "kullanicinin.txt"), "wb").write(b"benim")                 # listede yok → kalır
    open(os.path.join(kok, "pano", "pano.html"), "wb").write(YENI["pano/pano.html"])  # yeni sürümün dosyası (guncelle önce kopyalar)
    os.makedirs(os.path.join(kok, "IMZA"), exist_ok=True); open(os.path.join(kok, "IMZA", "dosyalar.sha256"), "w").write(liste(ESKI))
def beklenen(kok, ad):
    ok(f"{ad}: kalkan ve değişmemiş dosyalar silindi", not any(os.path.exists(os.path.join(kok, y)) for y in ("ses-isci.py", "pano/hazirlik.html", "test/platform.py")))
    ok(f"{ad}: boş kalan test/ klasörü kalktı, pano/ duruyor", not os.path.exists(os.path.join(kok, "test")) and os.path.isdir(os.path.join(kok, "pano")))
    ok(f"{ad}: yeni sürümde de olan, kullanıcının değiştirdiği, kısayol ve listede olmayan dosya kaldı",
       all(os.path.lexists(os.path.join(kok, y)) for y in ("relay.py", "degisti.py", "kur.command", "kisayol.py", "kullanicinin.txt")))
T = tempfile.mkdtemp(prefix="eski-dosya-")
try:
    k1 = os.path.join(T, "py"); os.makedirs(k1); kur(k1)
    yeni_m = os.path.join(T, "yeni.sha256"); open(yeni_m, "w").write(liste(YENI))
    sil = ns["eski_dosyalari_temizle"](k1, ns["imza_listesi"](os.path.join(k1, "IMZA", "dosyalar.sha256")), ns["imza_listesi"](yeni_m))
    ok("kurulum.py: silinen listesi", sorted(sil) == ["pano/hazirlik.html", "ses-isci.py", "test/platform.py"], str(sil))
    beklenen(k1, "kurulum.py")
    ok("kurulum.py: önceki liste yoksa hiçbir şey silinmez", ns["eski_dosyalari_temizle"](k1, ns["imza_listesi"](os.path.join(T, "yok")), {}) == [])
    k2 = os.path.join(T, "sh"); os.makedirs(k2); kur(k2)
    src = open(os.path.join(KOD, "kur.sh"), encoding="utf-8").read(); blok = src[src.index("# eski-dosya-basi"):src.index("# eski-dosya-sonu")]
    r = subprocess.run(["bash", "-c", blok], env=dict(os.environ, KOD=k2, M=yeni_m), capture_output=True, text=True, timeout=30)
    ok("kur.sh: blok hatasız", r.returncode == 0, r.stderr[-300:])
    ok("kur.sh: silinenleri yazdı", r.stdout.count("eski dosya kaldırıldı") == 3, r.stdout)
    os.path.isdir(os.path.join(k2, "test")) and not os.listdir(os.path.join(k2, "test")) and os.rmdir(os.path.join(k2, "test"))  # bash boş klasörü bırakır (zararsız)
    beklenen(k2, "kur.sh")
finally: shutil.rmtree(T, ignore_errors=True)
print("eski-dosya: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
