#!/usr/bin/env python3
# Beta geri bildirimi #36-4 — Konuş önceki soru-cevabı süreç değişse de bilsin (konus_gecmis_ekle / konus_gecmis_blogu, _KS["gseq"]) ve öznesiz
# "araştır ve bana bilgi ver" araştırma kipine girmesin (ar_tetik). Kota yok, süreç yok (<1 sn):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konus-baglam.py
import os, re, sys, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ad = {"re": re, "time": time, "AYAR": {}, "_KS": {"gseq": 0}, "_t": lambda a, b: a}
exec(kod[kod.index("KONUS_GECMIS = []"):kod.index("def konus_canli(")], ad)
ekle, blok, KS, G = ad["konus_gecmis_ekle"], ad["konus_gecmis_blogu"], ad["_KS"], ad["KONUS_GECMIS"]
tur = lambda **k: {"kaynak": "yazili", "bellek_kapsam": "ortak", **k}
n1 = ekle("Bu kitap ne anlatıyor?", "Kitap bir ailenin üç kuşağını anlatır.\n---\nAyrıntı satırı", "ortak")
b = blok(tur())
ok("yeni/yuvası değişen süreç (gseq 0): önceki soru-cevap bloğu gider, '---' ayrıntısı gitmez", "Önceki soru: Bu kitap ne anlatıyor?" in b and "üç kuşağını" in b and "Ayrıntı satırı" not in b)
ok("aynı süreçte ikinci kez gitmez (süreç gördü)", blok(tur()) == "" and KS["gseq"] == n1)
n2 = ekle("Nereden satın alabilirim?", "Kitapçılardan.", "ortak"); KS["gseq"] = n2  # bu sürecin kendi cevabı
ok("kendi cevapladığı tur tekrar gitmez", blok(tur()) == "")
KS["gseq"] = 0  # yuva değişti: öteki süreç hiçbirini görmedi
b = blok(tur()); ok("öteki süreçte iki tur birlikte, sırayla", b.index("Bu kitap") < b.index("Nereden"))
KS["gseq"] = 0; ekle("araştırma konusu", "Araştırma özeti burada.", "ortak"); ekle("a", "b", "ortak"); ekle("c", "d", "ortak")
ok("en çok 3 tur gider", blok(tur()).count("Önceki soru:") == 3)
KS["gseq"] = 0; e = ekle("Kartın özel bölümünden soru", "Özel cevap.", "ozel")
ok("özel kapsamlı tur ortak soruya girmez", "Özel cevap" not in blok(tur(bellek_kapsam="ortak")))
KS["gseq"] = 0; ok("özel kapsamlı soruya girer", "Özel cevap" in blok(tur(bellek_kapsam="ozel")))
KS["gseq"] = 0
ok("karşı taraf / moderatör / özet / karsi turu geçmişi görmez", all(blok(tur(kaynak=k)) == "" for k in ("karsi", "moderator", "ozet")) and blok(tur(karsi="Ali")) == "")
for e in G: e["t"] -= 700
KS["gseq"] = 0; ok("10 dakikadan eski tur gitmez", blok(tur()) == "")
ok("boş soru ya da cevap kaydedilmez", ekle("", "x") is None and ekle("x", "") is None)
# araştırma tetikleyicisi
src = open(os.path.join(KOD, "aktarici", "web-arastirma.py"), encoding="utf-8").read(); ar2 = {"BASE": "/yok", "AYAR": {}, "os": os}
exec(src[src.index("import re as _re_ar"):src.index("def ar_acik(")], ar2)
at = ar2["ar_tetik"]
ok("'araştır ve bana bilgi ver' araştırma kipine girmez (normal Konuş, geçmişi görür)", at("araştır ve bana bilgi ver") is None and at("araştır bana bilgi ver") is None)
ok("gerçek araştırma isteği hâlâ konu çıkarır", at("Kuzey Ege rüzgar santralleri hakkında araştırma yap") is not None and at("araştır Kuzey Ege rüzgar santralleri") == "Kuzey Ege rüzgar santralleri")
print("konuş bağlamı: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")); sys.exit(1 if HATA else 0)
