#!/usr/bin/env python3
# Ses izi hafızası canlıda (aktarici/whisper-hat.py kume_iz_ekle, v0.27.0): altyazı oyu olmayan karşı küme ≥ 8 sn konuşunca hafızadaki
# kişiye benziyorsa onun adını alır; < 8 sn'de ad yok; hafızada olmayan kişi adsız; aynı ad iki kümeye verilmez; altyazı oyu hafızadan önce
# gelir; ses_izi_hafiza: false kapatır; kume_sifirla temizler. Aktarıcının kendi tanımları AST ile alınır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hafiza-canli.py      (kaldı → çıkış 1)
import ast, base64, json, math, os, random, shutil, struct, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-hc-")
ns = {"base64": base64, "struct": struct, "math": math, "os": os, "json": json, "AYAR": {}, "BASE": T, "print": lambda *a: None}
ADLAR = {"kume_adi", "_iz_coz", "_hafiza_kisi", "kume_iz_ekle", "kume_sifirla"}
agac = ast.parse(open(os.path.join(KOD, "aktarici/whisper-hat.py"), encoding="utf-8").read())
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in ADLAR) or (isinstance(n, ast.Assign) and any(
    getattr(x, "id", None) in {"KUME_AD", "KUME_BEKLEYEN", "CAP_OY", "KUME_IZ", "KUME_HAFIZA", "_HAF"} or (isinstance(x, ast.Tuple) and any(getattr(e, "id", "").startswith("HAFIZA") for e in x.elts)) or getattr(x, "id", None) in {"KUME_IZ"} for x in n.targets))]
exec(compile(ast.Module(sec, []), "whisper-hat.py", "exec"), ns)
random.seed(3)
def birim(v): n = math.sqrt(sum(x * x for x in v)); return [x / n for x in v]
TABAN = {k: birim([random.gauss(0, 1) for _ in range(192)]) for k in "ABCD"}
def iz(k, g=0.35): return base64.b64encode(struct.pack("<192e", *birim([t + random.gauss(0, g / 14) for t in TABAN[k]]))).decode()
def hafiza(**kisi): json.dump({a: {"iz": iz(k, 0.1), "sn": 300} for a, k in kisi.items()}, open(os.path.join(T, "ses-izi-hafiza.json"), "w"))
hata = []
def bak(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad); hata.append(ad) if not kosul else None
hafiza(**{"Ayşe Yılmaz": "A", "Bora Kaya": "B"})
ka, kn = ns["kume_adi"], ns["kume_iz_ekle"]
kn("k1", iz("A"), 3.0); kn("k1", iz("A"), 3.0)
bak("< 8 sn: ad yok", ka("k1") is None)
kn("k1", iz("A"), 3.0)
bak("≥ 8 sn: k1 → Ayşe (hafızadan)", ka("k1") == "Ayşe Yılmaz")
for _ in range(4): kn("k2", iz("C"), 3.0)
bak("hafızada olmayan kişi adsız", ka("k2") is None)
for _ in range(4): kn("k3", iz("A"), 3.0)
bak("aynı ad ikinci kümeye verilmez", ka("k3") is None)
ns["KUME_AD"]["k4"] = {"Bora Kaya": 3}
for _ in range(4): kn("k4", iz("A"), 3.0)
bak("altyazı oyu hafızadan önce", ka("k4") == "Bora Kaya")
for _ in range(4): kn("k5", iz("B"), 3.0)
bak("altyazının verdiği ad (Bora) hafızadan ikinci kez verilmez", ka("k5") is None)
ns["kume_sifirla"]()
bak("kume_sifirla temizler", ka("k1") is None and not ns["KUME_IZ"])
ns["AYAR"]["ses_izi_hafiza"] = False
for _ in range(4): kn("k1", iz("A"), 3.0)
bak("ses_izi_hafiza: false iken ad yok", ka("k1") is None)
ns["AYAR"].clear(); ns["kume_sifirla"](); open(os.path.join(T, "ses-izi-hafiza.json"), "w").write("{bozuk")
for _ in range(4): kn("k1", iz("A"), 3.0)
bak("bozuk hafıza dosyası çökmeye yol açmaz", ka("k1") is None)
shutil.rmtree(T, ignore_errors=True)
print("hafıza canlı: ✓ hepsi geçti" if not hata else f"hafıza canlı: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
