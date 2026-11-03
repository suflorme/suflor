#!/usr/bin/env python3
# whisper-isci.py buyuk_harf_duzelt: tamamı büyük harfli Türkçe çıktıyı küçültür (gerçek model yüklemez, anında).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/buyuk-harf.py
import importlib.util, json, os, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("wi", os.path.join(KOD, "whisper-isci.py"))
try:
    wi = importlib.util.module_from_spec(sp); sp.loader.exec_module(wi)
except ImportError as e: print("whisper-isci.py yüklenemedi (bağımlılık):", e); sys.exit(0)
I = "AWS, IAM, MFA, Google Workspace."
T = [("BÜPÇE KAÇ LİRA?", "tr", I, "Büpçe kaç lira?"),
     ("BÜTÇE KAÇ LİRA? AWS MALİYETİ NE?", "tr", I, "Bütçe kaç lira? AWS maliyeti ne?"),
     ("IŞIK NEREDE. İNCİR NE ZAMAN?", "tr", "", "Işık nerede. İncir ne zaman?"),
     ("Bütçe kaç lira?", "tr", I, "Bütçe kaç lira?"),
     ("AWS.", "tr", I, "AWS."), ("TAMAM", "tr", "", "TAMAM"),
     ("AWS IAM", "tr", I, "AWS IAM"), ("OK", "tr", "", "OK"),
     ("WHAT IS THE BUDGET?", "en", I, "WHAT IS THE BUDGET?"),
     ("", "tr", I, ""), ("Bütçe AWS için kaç lira?", "tr", I, "Bütçe AWS için kaç lira?")]
# R17 (3 Kasım): istemde olmayan sözlük kısaltması (5. alan = işçiye giden "kisaltma") büyük kalır; yoksa küçülür (eski davranış)
T += [("SKU KAÇ ADET?", "tr", I, "Sku kaç adet?", None), ("SKU KAÇ ADET?", "tr", I, "SKU kaç adet?", ["SKU", "QXT"]),
      ("QXT İÇİN SKU BÜTÇESİ NE?", "tr", "", "QXT için SKU bütçesi ne?", ["SKU", "QXT"]), ("SKU.", "tr", "", "SKU.", ["SKU"])]
k = 0
for g, d, i, b, *ek in T:
    c = wi.buyuk_harf_duzelt(g, d, i, *ek); ok = c == b; k += not ok
    print(("tamam " if ok else "KALDI ") + repr(g) + " -> " + repr(c) + ("" if ok else "  beklenen " + repr(b)))
# aktarıcı tarafı: sozluk_kisaltmalari (whisper-hat.py) sözlüğün tamamı büyük harfli sözcüklerini (≥ 2 harf) verir
T2 = tempfile.mkdtemp(prefix="buyuk-harf-")
json.dump({"terimler": [{"dogru": "SKU", "yanlis": ["siku"]}, {"dogru": "ZQ Deneme Grubu", "yanlis": []}, {"dogru": "GitHub", "yanlis": []}, {"dogru": "A", "yanlis": []}, {"dogru": "Kasa-Ar", "yanlis": []}]}, open(os.path.join(T2, "sozluk.json"), "w"))
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read(); a = src.index("_KISALTMA = "); b = src.index("def istem_metni")
ns = {"os": os, "json": json, "BASE": T2}; exec(src[a:b], ns)
kl = ns["sozluk_kisaltmalari"](); ok2 = kl == ["SKU", "ZQ"]; k += not ok2
print(("tamam " if ok2 else "KALDI ") + "sozluk_kisaltmalari -> " + repr(kl))
print("sonuç:", "geçti" if not k else f"{k} kaldı"); sys.exit(1 if k else 0)
