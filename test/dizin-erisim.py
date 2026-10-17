#!/usr/bin/env python3
# Arama dizini, okunamayan proje klasöründe kayıt silmez (17 Ekim: aktarıcı launchd altında Masaüstü'nü okuyamıyor, os.walk sessizce boş
# dönüyordu; 10 dk'lık ön arama turu dizini 101 bin parçadan 301'e indirdi). Engeli chmod 000 ile taklit eder: kök okunamazken parça sayısı
# değişmez, alt klasör okunamazken yalnız o klasörün kayıtları korunur, gerçekten silinen dosya yine düşer, _canli güncellenmeye devam eder.
# Dış sözlük (.tsv, ayar sozluk_kaynagi) dizin turunda uygulama klasörüne kopyalanır; proje okunamazken sözlük kopyadan okunur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dizin-erisim.py      (kaldı → çıkış 1)
import importlib.util, json, os, shutil, sys, tempfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-dizin-"); P = os.path.join(T, "proje"); C = os.path.join(T, "canli")
for d in ("a", "b", "soz"): os.makedirs(os.path.join(P, d))
os.makedirs(C); os.symlink(C, os.path.join(P, "_canli"))  # gerçekteki gibi _canli kısayol
for d, f in (("a", "bir.md"), ("a", "iki.md"), ("b", "uc.md")):
    open(os.path.join(P, d, f), "w", encoding="utf-8").write(f"# {f}\n\nYedekleme planı ve bütçe görüşmesi {f} içinde geçiyor.\n")
open(os.path.join(P, "a", "bir.md"), "a", encoding="utf-8").write("Kubernetes kümesi taşınacak.\n")
TSV = os.path.join(P, "soz", "duzeltme_sozlugu_oneri.tsv")
open(TSV, "w", encoding="utf-8").write("yanlis\tdogru\nküpernetis|kubernetis\tKubernetes (altyapı)\n")
canli_yaz = lambda ad: open(os.path.join(C, ad), "w", encoding="utf-8").write(json.dumps({"speaker": "Deniz", "time": "10:00", "text": "yedekleme bütçesi"}) + "\n")
canli_yaz("2026-10-17-deneme.jsonl")
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "uygulama": os.path.join(T, "uyg"), "proje": P, "ortak": os.path.join(T, "yok"), "sozluk_kaynagi": "soz", "haric": ["soz"]}, open(ay, "w"))
os.environ["SUFLOR_AYAR"] = ay; sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("baglam_deneme", os.path.join(KOD, "baglam.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
c = m.baglan()
dosyalar = lambda: sorted(r[0] for r in c.execute("SELECT yol FROM dosya"))
parca = lambda: c.execute("SELECT COUNT(*) FROM parca").fetchone()[0]
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
try:
    kontrol("dizinden önce dış sözlük kopyası yok", not os.path.exists(m.SOZLUK_KOPYA))
    m.guncelle(c); ilk, ilk_p = dosyalar(), parca()
    kontrol("dizin turu dış sözlüğü uygulama klasörüne kopyaladı", os.path.exists(m.SOZLUK_KOPYA) and open(m.SOZLUK_KOPYA, encoding="utf-8").read() == open(TSV, encoding="utf-8").read())
    kontrol("ilk dizin: 3 belge + _canli", ilk == ["_canli/2026-10-17-deneme.jsonl", "a/bir.md", "a/iki.md", "b/uc.md"] and ilk_p >= 4 and getattr(m, 'ERISILEMEYEN', None) == [])
    os.chmod(P, 0)
    try:
        m.guncelle(c)
        soz = m.sozluk(); bul = m.ara("küpernetis taşınacak", n=5, guncel=False)
    finally: os.chmod(P, 0o755)
    kontrol("proje okunamazken sözlük kopyadan okundu, yanlış yazımla arama buldu",
            any(d == "Kubernetes" for d, _ in soz) and any(r[1] == "a/bir.md" for r in bul[0]) and "Kubernetes" in str(bul[1]), str(bul[1]))
    kontrol("proje okunamazken kopya korundu", os.path.exists(m.SOZLUK_KOPYA))
    kontrol("proje kökü okunamazken hiçbir kayıt silinmedi", dosyalar() == ilk and parca() == ilk_p)
    kontrol("okunamayan kök bildirildi", getattr(m, 'ERISILEMEYEN', None) == [""])
    tur = json.load(open(m.DB + ".tur.json", encoding="utf-8"))
    kontrol("son tur izi yazıldı (aktarıcı yardımcının sonucunu buradan okur)", tur.get("erisilemeyen") == [""] and tur.get("t", 0) > 0)
    os.chmod(os.path.join(P, "a"), 0); os.remove(os.path.join(P, "b", "uc.md")); canli_yaz("2026-10-17-yeni.jsonl")
    try: m.guncelle(c)
    finally: os.chmod(os.path.join(P, "a"), 0o755)
    kontrol("alt klasör okunamazken yalnız onun kayıtları korundu, silinen dosya düştü, yeni _canli girdi",
            dosyalar() == ["_canli/2026-10-17-deneme.jsonl", "_canli/2026-10-17-yeni.jsonl", "a/bir.md", "a/iki.md"])
    kontrol("okunamayan alt klasör bildirildi", getattr(m, 'ERISILEMEYEN', None) == ["a"])
    open(TSV, "a", encoding="utf-8").write("doker\tDocker\n"); os.utime(TSV, (1, 1)); m.guncelle(c)
    kontrol("dış sözlük değişince kopya ve bellekteki sözlük yenilendi", any(d == "Docker" for d, _ in m.sozluk()))
    os.remove(TSV); os.remove(os.path.join(P, "a", "iki.md")); m.guncelle(c)
    kontrol("kaynak silinince kopya da silindi", not os.path.exists(m.SOZLUK_KOPYA) and not any(d == "Kubernetes" for d, _ in m.sozluk()))
    kontrol("erişim dönünce silinen dosya düştü, bildirim temizlendi", "a/iki.md" not in dosyalar() and "a/bir.md" in dosyalar() and getattr(m, 'ERISILEMEYEN', None) == [])
    kontrol("arama yine buluyor", bool(m.ara("yedekleme bütçe", n=5, guncel=False)[0]))
finally:
    for d in (P, os.path.join(P, "a")):
        try: os.chmod(d, 0o755)
        except OSError: pass
    c.close(); shutil.rmtree(T, ignore_errors=True)
print(f"dizin erişim: {len(hatalar)} sorun" if hatalar else "dizin erişim: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
