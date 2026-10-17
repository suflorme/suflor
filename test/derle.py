#!/usr/bin/env python3
# v0.63.0 — kurulum.py derle: Swift yardımcısı kaynağın içeriği (SHA-256, derleme.json) değişince derlenir; dosya saati yanıltmaz
# (başka kopyadan kurulumda eski kaynak yeni saatle derlenince sonraki kurulum güncel kaynağı atlıyordu). Kaydı olmayan eski kurulumda bir kez saat kuralı.
# Gerçek swiftc ile küçük bir kaynak (~20 sn). kurulum.py derle değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/derle.py
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or ".") != os.path.dirname(os.path.abspath(__file__))]  # test/platform.py standart platform modülünü gölgeliyor
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
if not shutil.which("swiftc"): print("swiftc yok — atlandı"); sys.exit(0)
sp = importlib.util.spec_from_file_location("kurulum_deneme", os.path.join(KOD, "kurulum.py")); K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
T = tempfile.mkdtemp(prefix="suflor-derle-"); K.KOD = T; uyg = os.path.join(T, "app", "Deneme.app"); ikili = os.path.join(uyg, "Contents", "MacOS", "Deneme")
kay = os.path.join(T, "deneme.swift")
yaz = lambda m: open(kay, "w").write(f'print("{m}")\n')
cikti = lambda: subprocess.run([ikili], capture_output=True, text=True).stdout.strip()
kayit = lambda: json.load(open(os.path.join(T, "app", "derleme.json")))
try:
    yaz("bir"); ok("ikili yoksa derlenir, içerik kaydı yazılır", K.derle(uyg, "deneme.swift", "Deneme", "<plist/>") is True and cikti() == "bir" and "Deneme" in kayit())
    ok("kaynak değişmediyse derlenmez", K.derle(uyg, "deneme.swift", "Deneme", "<plist/>") is False)
    os.utime(kay, (time.time() + 100, time.time() + 100))
    ok("yalnız saat değişince derlenmez", K.derle(uyg, "deneme.swift", "Deneme", "<plist/>") is False)
    yaz("iki"); os.utime(kay, (time.time() - 3600, time.time() - 3600))
    ok("kaynak değişti ama saati eski (başka kopyadan kurulum): yine derlenir", K.derle(uyg, "deneme.swift", "Deneme", "<plist/>") is True and cikti() == "iki")
    os.remove(os.path.join(T, "app", "derleme.json")); os.utime(kay, (time.time() - 3600, time.time() - 3600))
    ok("kaydı olmayan eski kurulum: saat kuralı, kayıt yazılır, derlenmez", K.derle(uyg, "deneme.swift", "Deneme", "<plist/>") is False and kayit().get("Deneme"))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("derle:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
