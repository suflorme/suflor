#!/usr/bin/env python3
# Konuş ön araması (S47, v0.40.0; aktarici/bas-konus.py konus_onara): soru Claude'a gitmeden baglam.py dizininde aranır, en iyi parçalar dosya yolu ve
# kesitle bağlam bloğuna eklenir. Geçici proje klasörü + dizin: doğru dosya ilk sırada, kesitte aranan bilgi, < 3 sözcüklü/kısa soruda blok yok,
# arama dizini güncellemez ve hızlı (< 300 ms), Türkçe büyük İ / sözlük biçimleri bozulmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/onara.py
import os, sys, json, shutil, tempfile, time, threading, importlib.util
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-onara-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
proje = os.path.join(T, "proje"); os.makedirs(os.path.join(proje, "notlar"))
open(os.path.join(proje, "notlar", "yedekleme-politikasi.md"), "w").write("# Yedekleme politikası\n\nGünlük yedek her gece saat 02:00'de alınır. Sorumlu Ayla Örnek; geri yükleme denemesi ayda bir.\n")
open(os.path.join(proje, "notlar", "butce.md"), "w").write("# Bütçe\n\nPazarlama bütçesi üçüncü çeyrekte yüzde on artırıldı. Onaylayan Deniz Test.\n")
for i in range(30): open(os.path.join(proje, "notlar", f"dolgu-{i}.md"), "w").write(f"# Not {i}\n\nToplantı notu {i}: genel konular, takvim, ekip.\n")
json.dump({"alan": "Deneme", "ad": "Deniz T", "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor"}, open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json"); os.environ["SUFLOR_TEST_BASLAT"] = "1"; sys.dont_write_bytecode = True
try:
    # bas-konus.py'nin ön arama bölümü, relay ad alanı yerine küçük taklitle (bölüm dosyası relay.py'nin ad alanında çalışır; __file__ relay.py yanında)
    src = open(os.path.join(K, "aktarici", "bas-konus.py"), encoding="utf-8").read()
    g = {"os": os, "sys": sys, "time": time, "threading": threading, "_t": lambda tr, en: tr, "__file__": os.path.join(K, "relay.py")}
    exec(src[src.index("# --- Hızlı bilgi (S47"):src.index("def konus_baglam(")], g)
    m = g["_onara_mod"](); bak("baglam.py yüklendi", m is not None)
    t = time.time(); m.guncelle(m.baglan()); print(f"   dizin kuruldu ({time.time() - t:.2f} sn)")
    t = time.time(); b = g["konus_onara"]("Yedekleme hangi saatte alınıyor, sorumlusu kim?"); sn = time.time() - t
    print("   " + b.replace("\n", "\n   ")[:600])
    bak("blok başı ve sonu", b.startswith("[Ön arama") and b.rstrip().endswith("[/Ön arama]"))
    bak("ilk sonuç doğru dosya", b.split("\n")[1].find("yedekleme-politikasi.md") > 0)
    bak("kesitte aranan bilgi (02:00, Ayla)", "02:00" in b and "Ayla" in b)
    bak(f"hızlı ({sn * 1000:.0f} ms < 300)", sn < 0.3)
    bak("kısa soruda blok yok ('saat kaç')", g["konus_onara"]("Saat kaç?") == "")
    bak("tek içerik sözcüğünde blok yok ('bütçe ne?')", g["konus_onara"]("Bütçe ne?") == "")
    b2 = g["konus_onara"]("Pazarlama bütçesi ne kadar artırıldı?")
    bak("ikinci soru doğru dosya", "butce.md" in b2.split("\n")[1] and "yüzde on" in b2)
    open(os.path.join(proje, "notlar", "yeni.md"), "w").write("# Yeni\n\nKarbon ayak izi raporu cuma günü teslim.\n")
    bak("arama dizini güncellemez (yeni dosya ön aramada yok)", "yeni.md" not in g["konus_onara"]("Karbon ayak izi raporu ne zaman teslim?"))
    m.guncelle(m.baglan())
    bak("güncellemeden sonra yeni dosya bulunur", "yeni.md" in g["konus_onara"]("Karbon ayak izi raporu ne zaman teslim?"))
finally:
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("ön arama: ✓ hepsi geçti" if not hata else f"ön arama: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
