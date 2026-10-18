#!/usr/bin/env python3
# Sorunun Claude'a gitme gecikmesi (v0.80.4; 18 Ekim ölçümü ~3,2 sn = son parçanın yazıya dökülmesi + ön arama, art arda):
# (1) aktarici/bas-konus.py _akis_kesim — 3 sn'den kısa kuyruk ≥ 0,6 sn duraksamada kesilir, 0,35 sn'lik cümle içi duraksamada kesilmez;
# (2) onara_onceden / onara_al — duraksamada başlayan ön arama, soru ve kapsam aynıysa yeniden aranmadan kullanılır, değilse yeniden aranır.
# Sahte ses ve sahte arama; aktarıcı açılmaz (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/akis-onceden.py
import array, ast, math, os, sys, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read())
def al(*adlar):  # işlevler + modül düzeyindeki sabit atamaları
    govde = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in adlar)
             or (isinstance(d, ast.Assign) and any(isinstance(h, ast.Tuple) and any(getattr(e, "id", "").startswith("AKIS_") for e in h.elts) for h in d.targets))]
    return compile(ast.Module(govde, []), "bas-konus.py", "exec")
SR = 16000
def ses(sn, genlik):  # konuşma: 220 Hz, genlik hece gibi 0,1 sn'de bir iner çıkar (gürültü tabanı konuşmanın altında ölçülsün); küçük genlik: sessizlik
    return array.array("h", (int(genlik * (1.0 if (i // 1600) % 3 else 0.25) * math.sin(2 * math.pi * 220 * i / SR)) for i in range(int(sn * SR)))).tobytes()
def rms(b):
    a = array.array("h"); a.frombytes(b); return int((sum(x * x for x in a) / max(1, len(a))) ** 0.5)

# (1) kesim kuralı
n = {"WH_SR": SR, "_rms": rms, "AKIS": {"esik": None}}
exec(al("_akis_kesim"), n)
k = n["_akis_kesim"]
b = bytearray(ses(1.6, 3000) + ses(0.65, 30))
ok("1,6 sn konuşma + 0,65 sn duraksama (toplam < 3 sn) → kesilir", k(b, 0) is not None)
b = bytearray(ses(1.6, 3000) + ses(0.4, 30))
ok("1,6 sn konuşma + 0,4 sn duraksama → kesilmez (cümle içi)", k(b, 0) is None)
b = bytearray(ses(0.3, 3000) + ses(0.8, 30))
ok("0,3 sn ses + 0,8 sn duraksama (kısa ses) → kesilmez", k(b, 0) is None)
b = bytearray(ses(3.2, 3000) + ses(0.4, 30))
ok("3,2 sn konuşma + 0,4 sn duraksama → kesilir (eski kural)", k(b, 0) is not None)
b = bytearray(ses(2.0, 3000) + ses(0.7, 30)); kes = k(b, 0)
ok(f"kesim duraksamanın içinde (konuşma kesilmez): {kes} bayt", kes is not None and 2.0 * SR * 2 <= kes <= len(b))

# (2) önceden ön arama
ARA = []
def onara(ms, kapsam):
    ARA.append((ms, kapsam)); time.sleep(0.2); g["_ONARA"]["son_tur"] = "gorusme"; return f"[Ön arama] {ms}"
g = {"_ONARA": {}, "konus_onara": onara, "kisilik_hitap_bul": lambda m: (None, None), "kisilik": lambda: None, "konus_ad_duzelt": lambda m: (m.replace("Alinin", "Ali'nin"), []),
     "bellek_kapsam": lambda tur, kis: None, "threading": threading, "time": time, "print": lambda *a, **k: None}
exec(compile(ast.Module([d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in ("onara_onceden", "onara_al")) or
                         (isinstance(d, ast.Assign) and any(getattr(h, "id", "") == "_ONCEDEN" for h in d.targets))], []), "bas-konus.py", "exec"), g)
g["onara_onceden"]("Alinin son görüşmesi ne zaman")
time.sleep(0.05); t = time.time(); r = g["onara_al"]("Ali'nin son görüşmesi ne zaman", None); bek = time.time() - t
ok(f"aynı soru: önceden başlayan sonuç kullanıldı, arama 1 kez, bekleme {bek * 1000:.0f} ms (< 200 ms arama süresi)",
   r == ("[Ön arama] Ali'nin son görüşmesi ne zaman", "gorusme") and len(ARA) == 1 and bek < 0.2)
del ARA[:]
g["onara_onceden"]("Alinin son görüşmesi ne zaman"); time.sleep(0.3)
r = g["onara_al"]("Ali'nin son görüşmesi ne zaman ve kim katıldı", None)
ok("soru değişti (kuyruk yeni sözcük getirdi): yeniden arandı", r[0].endswith("kim katıldı") and len(ARA) == 2)
del ARA[:]
g["onara_onceden"]("Bütçe ne durumda acaba"); time.sleep(0.3)
r = g["onara_al"]("Bütçe ne durumda acaba", "ortak")
ok("kapsam farklı (ortak): yeniden arandı", len(ARA) == 2)
del ARA[:]; r = g["onara_al"]("Bütçe ne durumda acaba", "ortak")
ok("önceden arama yokken eskisi gibi bir kez aranır", len(ARA) == 1 and r[1] == "gorusme")
print("akış + önceden ön arama: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
