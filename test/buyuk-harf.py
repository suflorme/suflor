#!/usr/bin/env python3
# whisper-isci.py buyuk_harf_duzelt: tamamı büyük harfli Türkçe çıktıyı küçültür (gerçek model yüklemez, anında).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/buyuk-harf.py
import importlib.util, os, sys
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
k = 0
for g, d, i, b in T:
    c = wi.buyuk_harf_duzelt(g, d, i); ok = c == b; k += not ok
    print(("tamam " if ok else "KALDI ") + repr(g) + " -> " + repr(c) + ("" if ok else "  beklenen " + repr(b)))
print("sonuç:", "geçti" if not k else f"{k} kaldı"); sys.exit(1 if k else 0)
