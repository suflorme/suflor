#!/usr/bin/env python3
# v0.60.0 — Konuş ad düzeltmesi (konus_ad_duzelt, _ad_anahtar): Whisper'ın yanlış yazdığı adlar soru Claude'a gitmeden bilinen adlarla düzelir
# (b/v, c/k/ç, z/s, ie/i, çift harf); doğru yazılmış ad, Türkçe harf farkı, sıradan sözcük ve birden çok ada uyan sözcük değişmez.
# Adlar uydurma. Ad düzeltme kuralı değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ad-duzelt.py
import json, os, re, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="ad-duzelt-")
json.dump({"terimler": [{"dogru": "Lizzie", "yanlis": []}, {"dogru": "Zentra", "yanlis": ["zentira"]}]}, open(os.path.join(T, "sozluk.json"), "w"))
json.dump({"adlar": ["Vedran Kaya", "Juliana", "Jolene", "Shelby (Destek)", "Ömer", "Selin", "Elvan", "Elcan", "Deniz"]}, open(os.path.join(T, "vt-adlar.json"), "w"))
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
sz = {"re": re, "os": os, "json": json, "BASE": T, "print": lambda *a: None}
src = open(os.path.join(KOD, "aktarici", "sozluk.py"), encoding="utf-8").read(); exec(src[:src.index('# Sesli "Claude:"')], sz)
ad = {"re": re, "time": time, "json": json, "os": os, "BASE": T, "print": lambda *a: None, "_onara_mod": lambda: None, "kisilik": lambda: {"hitap": ["Orvo"]}, "kisilikler": lambda: [{"hitap": ["Orvo"]}],
      "sozluk_uygula": sz["sozluk_uygula"], "_t": lambda a, b: a}
exec(kod[kod.index("# --- Ad düzeltmesi"):kod.index("# --- Bekleme cümlesi")], ad)
d = lambda q: ad["konus_ad_duzelt"](q)
ok("b/v: 'Bedran' → Vedran", d("Bedran iskonto taleplerinde nasıl karar veriyor?") == ("Vedran iskonto taleplerinde nasıl karar veriyor?", [("Bedran", "Vedran")]))
ok("büyük harf + ek: 'LİZİ'ye' → Lizzie'ye", d("LİZİ'ye ne dedi?")[0] == "Lizzie'ye ne dedi?")
ok("ie/i, çift harf: 'Lizi' → Lizzie", d("Bunu Lizi mi söyledi?")[0] == "Bunu Lizzie mi söyledi?")
ok("bir harf farkı: 'Juliyana' → Juliana", d("Juliyana ne yapıyor?")[0] == "Juliana ne yapıyor?")
ok("ş/sh: 'Şelbi' → Shelby (veritabanı takma adı, parantez ayrılır)", d("Şelbi ne dedi?")[0] == "Shelby ne dedi?")
ok("ilk harf ses çifti (j/h): 'Holene' → Jolene; 'Hakan' gibi uzak sözcük değişmez", d("Bunu Holene mi söyledi?")[0] == "Bunu Jolene mi söyledi?" and d("Bunu Hakan mı söyledi?")[1] == [])
ok("sözlük de uygulanır: zentira → Zentra", "Zentra" in d("zentira sipariş akışı nasıl?")[0])
ok("Türkçe harf farkı değişmez (Ömer / Omer)", d("Omer ne zaman fark etti?")[1] == [] and d("Ömer ne zaman fark etti?")[1] == [])
ok("iki ada uyan sözcük değişmez (Elvan / Elcan → 'Elzan')", d("Bunu Elzan mı söyledi?")[1] == [])
ok("doğru ad, sıradan sözcük ve cümle başı değişmez", all(d(q)[1] == [] for q in ("Selin ne dedi?", "Sen kimsin?", "Bir bayram kampanyası var mı?", "Deniz kıyısında toplantı", "Bende yok", "Benim adım ne?")))
ok("kişilik hitap adı bilinen ad sayılır ('Orvo' değişmez)", d("Orvo, bugün ne var?")[1] == [])
n = ad["konus_ad_notu"]([("Bedran", "Vedran")])
ok("bağlam notu duyulanı ve düzelteni yazar", "'Bedran' → 'Vedran'" in n and n.startswith("[Ad düzeltmesi"))
ok("düzeltme yoksa not yok", ad["konus_ad_notu"]([]) == "")
import shutil; shutil.rmtree(T, ignore_errors=True)
print("ad düzeltmesi:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
