#!/usr/bin/env python3
# Okurken ben kanalı parça kapanışı (aktarici/whisper-hat.py Kanal.besle, WH_SESSIZ_OKUMA_MS; 3 Kasım "Bir dakika" 2,0 sn'de durdurdu): asistan okurken ben kanalında
# parça 0,45 sn sessizlikte kapanır, okumuyorken ve karşı kanalda 0,7 sn; kısa parça (≥ 0,4 sn konuşma) yine kuyruğa girer. Yapay PCM, ses/model yok (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/okuma-sessizlik.py
import ast, collections, math, os, queue, struct, sys, time, types
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
a = ast.parse(open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read())
ad = {"WH_SR", "WH_KARE", "WH_SESSIZ_MS", "WH_SESSIZ_OKUMA_MS", "WH_ON_MS", "WH_MAX_SN", "WH_MIN_KONUSMA_MS", "WH_BOSTA_KAPAT_SN", "WH_AKIS_SN", "WH_GUVENCE_SN", "WH_ATLA_SN", "WH_DIP_BLOK", "_rms", "Kanal"}
sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in ad) or (isinstance(n, ast.ClassDef) and n.name in ad) or (isinstance(n, ast.Assign) and any(
    (getattr(x, "id", None) in ad) or (isinstance(x, ast.Tuple) and any(getattr(e, "id", None) in ad for e in x.elts)) for x in n.targets))]
OKUMA = [False]
ns = {"collections": collections, "time": time, "audioop": None, "STATE": {"whisper": {"kanallar": {}, "kanal_son_parca": {}, "parca": {}, "kuyruk": 0}}, "WH_Q": queue.Queue(), "okuma_suruyor": lambda: OKUMA[0]}
exec(compile(ast.Module(sec, []), "whisper-hat.py", "exec"), ns)
def kapanis(kanal, okuma, konusma_sn=1.0):  # → konuşma bitişinden parçanın kuyruğa girdiği ana kadar sn (yok: None)
    OKUMA[0] = okuma; ns["WH_Q"].queue.clear(); k = ns["Kanal"](kanal); t = 1000.0; kare = lambda g: struct.pack("<h", g) * 320
    for _ in range(100): k.besle(kare(60), t, "b"); t += 0.02  # taban
    for i in range(int(konusma_sn / 0.02)): k.besle(kare(int(4000 * math.sin(i))), t, "b"); t += 0.02
    bitis = t
    for i in range(100):
        k.besle(kare(60), t, "b"); t += 0.02
        if not ns["WH_Q"].empty(): return t - bitis
    return None
n = kapanis("ben", False); ok(f"okumuyorken ben parçası 0,7 sn sessizlikte kapanır ({n:.2f} sn)", n is not None and 0.65 <= n <= 0.75)
n = kapanis("ben", True); ok(f"asistan okurken ben parçası 0,45 sn'de kapanır ({n:.2f} sn)", n is not None and 0.4 <= n <= 0.5)
n = kapanis("karsi", True); ok(f"okurken karşı kanal değişmez, 0,7 sn ({n:.2f} sn)", n is not None and 0.65 <= n <= 0.75)
n = kapanis("ben", True, 0.5); ok(f"okurken 0,5 sn'lik kısa konuşma yine parça olur ({n})", n is not None)
print("okuma-sessizlik: " + ("✓ hepsi geçti" if not HATA else "✗ " + "; ".join(HATA))); sys.exit(1 if HATA else 0)
