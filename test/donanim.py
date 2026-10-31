#!/usr/bin/env python3
# Sihirbazın donanım denetimi (S173): Intel durur, Apple Silicon 16 GB altı uyarı, 16 GB ve üstü tamam. Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/donanim.py
import ast, os, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = ast.parse(open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read()); ns = {}
sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name == "donanim_durum") or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) == "BELLEK_KARARLI_GB" for x in n.targets))]
exec(compile(ast.Module(sec, []), "kurulum.py", "exec"), ns); d = ns["donanim_durum"]; hata = 0
for arm, gb, bek in ((False, 32, "intel"), (False, 8, "intel"), (True, 8, "az_bellek"), (True, 15, "az_bellek"), (True, 16, "tamam"), (True, 32, "tamam")):
    ok = d(arm, gb) == bek; hata += not ok; print(("✓" if ok else "✗") + f" arm={arm} {gb} GB → {d(arm, gb)}")
js = open(os.path.join(KOD, "sihirbaz", "sihirbaz.js"), encoding="utf-8").read()
for k in ("m_az:", "m_intel:", 'data-donanim="intel"', 'data-donanim="az-bellek"'):
    ok = js.count(k) >= (2 if k.endswith(":") else 1); hata += not ok; print(("✓" if ok else "✗") + f" sihirbazda {k} (TR+EN)")
print("donanım: ✓ hepsi geçti" if not hata else f"donanım: ✗ {hata} hata"); sys.exit(1 if hata else 0)
