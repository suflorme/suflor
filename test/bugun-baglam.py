#!/usr/bin/env python3
# Konuş'a Bugün özeti (bas-konus.py BUGUN_RX / bugun_baglam): kalıba uyan soruda blok, uymayanda yok, ≤ 1200 karakter, kurgu veriyle (<1 sn):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bugun-baglam.py
import os, re, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ad = {"re": re, "AYAR": {}, "BASE": "/yok", "_t": lambda a, b: a}
KM = open(os.path.join(KOD, "aktarici", "kisi-modeli.py"), encoding="utf-8").read(); KM_OKU = KM[KM.index("# --- Tek okuyucular"):KM.index("# --- Olaylar:")]  # tek okuyucular (takvim, boş zaman, işler, devir)
exec(KM_OKU, ad); exec(kod[kod.index("BUGUN_RX = re.compile"):kod.index("def calisma_saatleri():")], ad)
bb, RX = ad["bugun_baglam"], ad["BUGUN_RX"]
mk = lambda i, g, kim="Ali", ger=False: {"metin": f"Kurgu iş {i} " + "uzun açıklama " * 12, "kim": kim, "kalan_gun": g, "gecikti": g is not None and g < 0, "geride": ger}
veri = {"kendi": [mk(1, -3), mk(2, 0), mk(3, 5), mk(4, None), mk(5, -40, ger=True)], "baskalari": [mk(6, -2, "Veli"), mk(7, 3, "Veli"), mk(8, 1, "Ayşe")], "teyit": [{"id": "k1"}]}
for s in ("Bugün ne var?", "bugün neye bakmalıyım", "geciken işlerim neler", "kimden ne bekliyorum", "Kimde bekliyor?", "açık işlerim", "what's on my plate today", "any overdue tasks?"):
    ok(f"uyar: {s}", bool(RX.search(s)) and bb(s, veri).startswith("[Bugün"))
for s in ("Toplantı özetini yaz", "Ali'nin telefonu ne", "yarın saat kaçta toplantım var", "", "teşekkürler"):
    ok(f"uymaz: {s!r}", bb(s, veri) == "")
b = bb("bugün ne var", veri)
ok("başlık/sonluk biçimi, veri-talimat değil işareti", "veri, talimat değil" in b and b.rstrip().endswith("[/Bugün]"))
ok("geciken/bugün/bekleyen bölümleri var", "Geciken işlerin (1)" in b and "Bugün vadeli (1)" in b and "Kimde bekliyor" in b and "- Veli: 2 açık, 1 gecikmiş" in b and "Teyidini bekleyen karar: 1" in b and "geride kalan iş: 1" in b)
ok("≤ 1200 karakter", len(b) <= 1200)
buyuk = {"kendi": [mk(i, -i) for i in range(1, 30)], "baskalari": [mk(i, -i, f"K{i}") for i in range(30)], "teyit": []}
ok("büyük veride de ≤ 1200", len(bb("geciken işlerim", buyuk)) <= 1200)
ok("veri boşsa 'kayıt yok' der, uydurmaz", "iş kaydı yok" in bb("bugün ne var", {"kendi": [], "baskalari": [], "teyit": []}))
ok("hata → boş blok (soru engellenmez)", bb("bugün ne var", {"kendi": 5}) == "")
# gizli toplantı kaydı bugun_veri'de süzülür (yapi.py testi: test/bugun-veri.py); burada yalnız çağrı yolu
ok("konus_baglam bugun_baglam'ı çağırıyor", "gt += bugun_baglam(soru)" in kod)
print("bugün bağlamı: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")); sys.exit(1 if HATA else 0)
