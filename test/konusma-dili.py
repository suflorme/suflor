#!/usr/bin/env python3
# Konuşma dili (v0.73.0, aktarici/kisilik.py konusma_dili): kişilik dosyasında "konusma_dili: evet" ise okunan cümlede 1./2. kişi kip ekleri günlük söyleniş
# (okuyacağım → okuyacam, bakıyorum → bakıyom); ortaç ("okuyacağım kitap"), belirtme eki ("söyleyeceğimi") ve "yorum" bozulmaz. Kural değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konusma-dili.py
import os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = {"v": {"kdili": True}}; ns = {"re": re, "ARAYUZ_DILI": "tr", "kisilik": lambda: K["v"]}
s = open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read(); exec(s[s.index("_KD_SON ="):], ns)
T=[("Okuyacağım, sonra söylerim.","Okuyacam, sonra söylerim."),("Bakıyorum.","Bakıyom."),("Geliyor musun?","Geliyon mu?"),
("Biliyorsun, bu iş zor.","Biliyon, bu iş zor."),("Yarın gideceğim ama geç.","Yarın gidecem ama geç."),("Bunu yapacağız.","Bunu yapacaz."),
("Okuyacağım kitap bu.","Okuyacağım kitap bu."),("Bu yorum güzel.","Bu yorum güzel."),("Yorumum şu.","Yorumum şu."),
("Bilmiyorum.","Bilmiyom."),("Gidiyoruz.","Gidiyoz."),("Anlıyor muyum?","Anlıyom mu?"),("Söyleyeceğimi unuttum.","Söyleyeceğimi unuttum."),
("Takviminde üç toplantı var.","Takviminde üç toplantı var."),("Hallederim, merak etme.","Hallederim, merak etme."),("Görüyorum ki yorulmuşsun.","Görüyom ki yorulmuşsun."),
("İzleyeceğim","İzleyecem"),("Yapacağım iş çok.","Yapacağım iş çok."),("Koyuyorum.","Koyuyom.")]
h = 0
for g, b in T:
    c = ns["konusma_dili"](g); ok = c == b; h += not ok; print(("✓ " if ok else "✗ ") + f"{g!r} → {c!r}" + ("" if ok else f"  (beklenen {b!r})"))
K["v"] = {"kdili": False}; ok = ns["konusma_dili"]("Bakıyorum.") == "Bakıyorum."; h += not ok; print(("✓ " if ok else "✗ ") + "konuşma dili kapalı kişilikte değişmez")
K["v"] = None; ok = ns["konusma_dili"]("Bakıyorum.") == "Bakıyorum."; h += not ok; print(("✓ " if ok else "✗ ") + "kişilik yokken değişmez")
print("GEÇTİ" if not h else f"KALDI: {h}"); sys.exit(1 if h else 0)
