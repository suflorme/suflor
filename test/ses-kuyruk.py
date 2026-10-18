#!/usr/bin/env python3
# Ses kuyruğu işçisi (aktarici/brifing-ses.py _ses_isci): her öğe doğru çalıcıya gider — ("dosya", yol) → afplay, ("g", metin, ses, üslup) → Gemini,
# düz metin → Mac sesi. v0.80.1: Gemini parçası da demet olduğu için dosya sanılıp afplay'e gidiyordu; sesli cevap hiç duyulmuyordu (deneme kipinde
# seslendir kuyruğa girmeden döndüğü için öteki testler görmedi). Sahte çalıcılarla, ses çalınmaz (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-kuyruk.py
import ast, os, sys, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read())
fn = [f for f in agac.body if isinstance(f, ast.FunctionDef) and f.name in ("_ses_metin", "_ses_isci")]
CALAN = []
class P:  # sahte afplay/say süreci
    def __init__(self, k, **a): self.k = k; self.stdin = self; self.yazi = b""
    def write(self, b): self.yazi += b
    def close(self): CALAN.append(("mac", self.yazi.decode()))
    def wait(self):
        if self.k[0] == "/usr/bin/afplay": CALAN.append(("afplay", self.k[1]))
def deneme(gemini_acik, motor="mac", q=None, bekle=3):
    del CALAN[:]
    n = {"SES": {"q": q or [("dosya", "/tepki.caf"), ("g", "Gemini cümlesi.", "Charon", "dostça"), "Mac cümlesi."], "isci": True, "kes": 0}, "GEMINI_BIRLESIK_EN_COK": 600, "SES_K": threading.Condition(),
         "subprocess": type("S", (), {"Popen": P, "DEVNULL": None, "PIPE": None}), "kisilik_sesi": lambda m=None: (m or motor, None, 1.0), "gemini_var": lambda: gemini_acik,
         "gemini_oku": lambda metin, **a: (CALAN.append(("gemini", metin, a.get("ses"), a.get("uslup"))), True)[1], "etiket_sil": lambda m: m, "kisilik": lambda: {},
         "piper_oku": lambda *a, **k: False, "piper_hiz": lambda: 1.0, "SES_TABAN_HIZ": 180, "print": lambda *a, **k: None, "time": time, "os": os}
    exec(compile(ast.Module(fn, []), "brifing-ses.py", "exec"), n)
    threading.Thread(target=n["_ses_isci"], daemon=True).start()
    for _ in range(100):
        if len(CALAN) >= bekle: break
        time.sleep(0.01)
    return list(CALAN)
c = deneme(True)
ok(f"Gemini açık: tepki → afplay, Gemini parçası → Gemini (sesi ve üslubuyla), düz metin → Mac: {c}",
   c == [("afplay", "/tepki.caf"), ("gemini", "Gemini cümlesi.", "Charon", "dostça"), ("mac", "Mac cümlesi.")])
c = deneme(False)
ok(f"Gemini yok: Gemini parçası Mac sesiyle okunur, hiçbir parça afplay'e dosya diye gitmez: {c}",
   c == [("afplay", "/tepki.caf"), ("mac", "Gemini cümlesi."), ("mac", "Mac cümlesi.")])
# v0.80.8: kuyrukta bekleyen aynı ses ve üsluptaki Gemini parçaları tek istekte; ses ya da üslup değişince ayrı; 600 karakter sınırı
c = deneme(True, q=[("g", "Bir.", "Charon", "u"), ("g", "İki.", "Charon", "u"), ("g", "Üç.", "Charon", "u2"), ("g", "Dört.", "Kore", "u2")], bekle=3)
ok(f"birleştirme: aynı ses+üslup tek istek, değişince ayrı: {c}", c == [("gemini", "Bir. İki.", "Charon", "u"), ("gemini", "Üç.", "Charon", "u2"), ("gemini", "Dört.", "Kore", "u2")])
uzun = "x" * 350 + "."
c = deneme(True, q=[("g", uzun, "Charon", "u"), ("g", uzun, "Charon", "u"), ("g", "Son.", "Charon", "u")], bekle=2)
ok(f"birleştirme sınırı (600 karakter): {[len(x[1]) for x in c]}", [len(x[1]) for x in c] == [351, 356])
print("ses-kuyruk: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
