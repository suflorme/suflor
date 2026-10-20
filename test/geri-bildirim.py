#!/usr/bin/env python3
# Geri bildirim dosyasının ortak klasöre güvenli yazımı (güvenlik denetimi O2, v0.97.3: toplanti-claude.py gb_yaz, GUNLUK_HARIC).
# Herkese yazılabilir klasörde hazır duran sembolik bağ izlenmez, var olan dosya ezilmez; "Kişiler düğmesi" günlük satırı rapora girmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/geri-bildirim.py      (kaldı → çıkış 1)
import contextlib, importlib.util, io, json, os, shutil, stat, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-gb-"); canli, ortak = os.path.join(T, "canli"), os.path.join(T, "ortak"); os.makedirs(canli); os.makedirs(os.path.join(ortak, "geri-bildirim"))
json.dump({"alan": "Test", "ad": "Deneme", "port": 8790, "uygulama": os.path.join(T, "uyg"), "ortak": ortak, "teshis": False, "dil": "tr"}, open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json")
sys.path.insert(0, KOD); sys.argv = ["tc", "--dir", canli, "acik"]
spec = importlib.util.spec_from_file_location("tc", os.path.join(KOD, "toplanti-claude.py")); m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
try:
    d = m.GB_DIR(); hedef = os.path.join(T, "kurban.txt"); open(hedef, "w").write("dokunulmamalı")
    fp = os.path.join(d, "20261020-1200-Test-kim.md"); os.symlink(hedef, fp)
    y = m.gb_yaz(fp, "rapor 1")
    kontrol("sembolik bağ izlenmedi, hedef dosya değişmedi", open(hedef).read() == "dokunulmamalı" and os.path.islink(fp))
    kontrol("yeni dosya ayrı adla yazıldı (-2)", y.endswith("-kim-2.md") and open(y).read() == "rapor 1" and not os.path.islink(y))
    kontrol("izin 0644 (geliştirici öbür hesaptan okur)", stat.S_IMODE(os.stat(y).st_mode) == 0o644)
    y2 = m.gb_yaz(fp, "rapor 2")
    kontrol("var olan dosya ezilmedi (-3)", y2.endswith("-kim-3.md") and open(y).read() == "rapor 1")
    kontrol("Kişiler düğmesi satırı rapor günlüğüne girmez", m.GUNLUK_HARIC.search("2026-10-20 12:00:00 EKLENTİ: Kişiler düğmesi · Kişiler (3) · sayı 3")
            and not m.GUNLUK_HARIC.search("2026-10-20 12:00:00 EKLENTİ: nabız"))
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
