#!/usr/bin/env python3
# aktarici/sozluk.py sozluk_uygula birim testi (3 Kasım, sözlük 1. aşama): kurgu sozluk.json + bölüm dosyasının ad alanında çalıştırılması (relay.py gibi, import yok).
# Kesmeli ek kısa biçimde de kabul, kesmesiz ek kısa biçimde yanlış pozitif sayılır (düzeltmez), tireli/çok sözcüklü biçim, bağlam/işaret kipleri.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sozluk-uygula.py      (kaldı → çıkış 1)
import json, os, re, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="sozluk-uygula-")
TER = [
 {"dogru": "GitHub", "yanlis": ["git hub"]},                       # çok sözcüklü, uzun
 {"dogru": "Zorbi", "yanlis": ["zorv", "zorva"]},                   # kısa (4) ve uzun (5) biçim
 {"dogru": "Kasadar", "yanlis": ["kasa ar"]},                   # son sözcük 2 harf, tireyle de eşleşir
 {"dogru": "Kasa-Ar", "yanlis": ["vot-ar"]},                        # tireli yazılmış biçim
 {"dogru": "Kalendix", "yanlis": ["kalendiks"]},                 # uzun tek sözcük
 {"dogru": "Toplu Pano", "yanlis": ["toplu bano"], "kip": "baglam", "baglam": ["ekran", "modül"]},
 {"dogru": "Stoksink", "yanlis": ["stok sink"], "kip": "isaret"},
 {"dogru": "Shoppy Fay", "yanlis": ["shopi fey"]}, {"dogru": "Fay", "yanlis": ["fey"]},  # uzun biçim önce
]
json.dump({"terimler": TER}, open(os.path.join(T, "sozluk.json"), "w"))
src = open(os.path.join(KOD, "aktarici", "sozluk.py"), encoding="utf-8").read()
ns = {"re": re, "os": os, "json": json, "BASE": T, "print": lambda *a: None}
exec(src[:src.index('# Sesli "Claude:"')], ns)
u = lambda t: ns["sozluk_uygula"](t, "x")
HATA = []; N = [0]
def ok(ad, k):
    N[0] += 1; print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
ok("düz biçim", u("git hub depoda")[0] == "GitHub depoda")
ok("çok sözcüklü, kesmeli ek ('git hub'da')", u("git hub'da yok")[0] == "GitHub'da yok")
ok("çok sözcüklü, kesmesiz ek ('git hubda') uzun biçimde kabul", u("git hubda yok")[0] == "GitHub'da yok")
ok("kısa biçim (4) kesmeli ek: zorv'e → Zorbi'e (ek harfiyle)", u("zorv'e söyledim")[0] == "Zorbi'e söyledim")
ok("kısa biçim büyük harf/özgün ek korunur: Zorv'nin → Zorbi'nin", u("Zorv'nin ekibi")[0] == "Zorbi'nin ekibi")
ok("kısa biçim kesmesiz ek DÜZELTMEZ (yanlış pozitif koruması): zorvle, zorvler", u("zorvle konuştum")[0] == "zorvle konuştum" and u("zorvler geldi")[0] == "zorvler geldi")
ok("kısa biçim ekiz: zorv → Zorbi", u("zorv geldi")[0] == "Zorbi geldi")
ok("uzun biçim kesmeli ek: zorva'ya", u("zorva'ya")[0] == "Zorbi'ya")
ok("uzun tek sözcük kesmesiz ek: kalendiksda → Kalendix'da", u("kalendiksda var")[0] == "Kalendix'da var")
ok("uzun tek sözcük kesmeli ek: Kalendiks'den", u("Kalendiks'den")[0] == "Kalendix'den")
ok("tireli: KASA-AR → Kasadar", u("KASA-AR kuruldu")[0] == "Kasadar kuruldu")
ok("tireli, kesmeli ek: KASA-AR'den → Kasadar'den (ek özgün harfle)", u("KASA-AR'den aldık")[0] == "Kasadar'den aldık")
ok("tireli yanlış biçim, kesmeli ek: vot-ar'den → Kasa-Ar'den", u("vot-ar'den")[0] == "Kasa-Ar'den")
ok("son sözcüğü kısa biçimde kesmesiz ek DÜZELTMEZ: 'kasa arada'", u("kasa arada kaldı")[0] == "kasa arada kaldı")
ok("zaten doğru biçime dokunmaz", u("GitHub'da ve Kasadar'den")[0] == "GitHub'da ve Kasadar'den" and u("Zorbi'e")[0] == "Zorbi'e")
ok("bağlam kipi: bağlam yokken yalnız şüpheli", u("toplu bano iyi")[0] == "toplu bano iyi" and u("toplu bano iyi")[1] == [{"bicim": "toplu bano", "dogru": "Toplu Pano", "durum": "supheli"}])
ok("bağlam kipi: bağlam varsa düzeltir", u("ekran toplu bano'da")[0] == "ekran Toplu Pano'da")
ok("işaret kipi: hiç düzeltmez, şüpheli", u("stok sink bozuk") == ("stok sink bozuk", [{"bicim": "stok sink", "dogru": "Stoksink", "durum": "supheli"}]))
ok("uzun biçim önce: 'shopi fey' → Shoppy Fay (Fay'a bölünmez); tek 'fey' → Fay", u("shopi fey iyi")[0] == "Shoppy Fay iyi" and u("fey iyi")[0] == "Fay iyi")
ok("kısa biçim sözcük sınırı: 'feyda' dokunulmaz, kesmesiz ek yok", u("feyda var")[0] == "feyda var")
ok("olay kaydı: duzeltildi", u("zorv'e")[1] == [{"bicim": "zorv'e", "dogru": "Zorbi", "durum": "duzeltildi"}])
print(f"{N[0] - len(HATA)}/{N[0]}"); sys.exit(1 if HATA else 0)
