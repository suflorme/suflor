#!/usr/bin/env python3
# Yakın ses kapısı — ölçüm kipi (v0.80.7, aktarici/sohbet.py _kapi_olc/_kapi_yaz): sohbette her tur için arka plan ve konuşma düzeyi, yakın oran ve kapının
# vereceği karar günlüğe ve canli/sohbet-kapi.jsonl'e yazılır; hiçbir şey engellenmez. Sahte pencere düzeyleriyle (~1 sn, aktarıcı açılmaz).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kapi-olcum.py
import ast, collections, datetime, json, math, os, sys, threading
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "sohbet.py"), encoding="utf-8").read())
govde = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in ("_kapi_olc", "_kapi_yaz", "_giris_turu"))
         or (isinstance(d, ast.Assign) and any(isinstance(h, ast.Tuple) and any(getattr(e, "id", "") == "SOHBET_KAPI_ORAN" for e in h.elts) for h in d.targets))]
YAZ, SAT = [], []
os.environ["SUFLOR_TEST_BASLAT"] = "1"
g = {"SOHBET": {}, "collections": collections, "WH_SR": 16000, "AKIS_PENCERE": 800, "math": math, "datetime": datetime, "json": json, "os": os, "struct": None,
     "LOCK": threading.Lock(), "BASE": "/canli", "write": lambda p: YAZ.extend(p), "print": lambda *a, **k: SAT.append(" ".join(map(str, a)))}
exec(compile(ast.Module(govde, []), "sohbet.py", "exec"), g)
def tur(arka_duzey, kon_duzey, kon_pay):  # 10 sn arka plan ısınması + 3 sn tur (0,5 sn'lik parçalar, 10 pencere)
    g["SOHBET"].clear()
    for _ in range(20): g["_kapi_olc"]([arka_duzey * (0.6 + 0.8 * (i % 5) / 4) for i in range(10)], 250)
    g["SOHBET"].pop("kapi", None)
    for _ in range(6): g["_kapi_olc"]([kon_duzey if i < kon_pay * 10 else arka_duzey for i in range(10)], 250)
    del SAT[:], YAZ[:]; g["_kapi_yaz"]("tur bitti")
    return json.loads(YAZ[0][1]) if YAZ else None, (SAT[0] if SAT else "")
o, s = tur(300, 3000, 0.8)
ok(f"yakın ses (arka plandan ~20 dB yüksek): kapı geçerdi — {s[:110]}", o and o["karar"] == "geçerdi" and o["fark_db"] > 15 and o["mikrofon"] == "deneme")
o2, s2 = tur(300, 3000, 0.8)
ok("satır canli/sohbet-kapi.jsonl'e gider (yalnız sayılar)", o2 is not None and set(o2) >= {"at", "sn", "arka", "kon", "fark_db", "oran", "karar", "sonuc", "mikrofon"})
o3, s3 = tur(1500, 1700, 0.8)
ok(f"arka plan kadar yüksek konuşma: kapı keserdi — {s3[:110]}", o3 and o3["karar"] == "keserdi" and abs(o3["fark_db"]) < 4)
del YAZ[:]; g["SOHBET"]["kapi"] = {"ham": 3, "yakin": [1, 1], "arka": [300], "kon": [900]}; g["_kapi_yaz"]("tur bitti")
ok("çok kısa tur (< 0,4 sn konuşma) yazılmaz", YAZ == [] and "kapi" not in g["SOHBET"])
ok("ölçüm davranışı değiştirmez: _kapi_olc hiçbir şey döndürmez, ses değişmez", g["_kapi_olc"]([500] * 10, 250) is None)
print("kapı ölçümü: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
