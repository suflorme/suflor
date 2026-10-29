#!/usr/bin/env python3
# Konuş'ta iki süreç yuvası ve önceden açma (v0.96.0; aktarici/bas-konus.py konus_yuva_degis, konus_yedek_kapat, _yedek_canli, konus_on_ac).
# Sahte süreçlerle (claude açılmaz, ~0 sn): özel süreç bekler, ortak cevap boş yuvadan yeni süreç ister; özel soru gelince bekleyen özel süreç geri gelir
# (okuyucu numarası, defter ve maliyet sayacıyla); ölü bekleyen süreç kapanır; önceden açma tur sürerken ve ayar kapalıyken açmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konus-yuva.py
import ast, os, sys, threading
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read())
AD = {"konus_yuva_degis", "konus_yedek_kapat", "_yedek_canli", "konus_on_ac"}
sec = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in AD) or (isinstance(d, ast.Assign) and any(getattr(t, "id", "") in ("KONUS_P", "_KS_YEDEK") for t in d.targets))]
class App:
    def __init__(s, canli=True): s.canli = canli
    def poll(s): return None if s.canli else 0
    def wait(s, timeout=None): s.canli = False
class W:
    def __init__(s): s.kapali = False
    def close(s): s.kapali = True
ACILAN = []
def konus_ac():
    w, a = W(), App(); ns["_KS"].update(w=w, app=a, nesil=ns["_KS"].get("nesil_en", 0) + 1, ozel_gitti=False, maliyet=0, sayac=0); ns["_KS"]["nesil_en"] = ns["_KS"]["nesil"]; ACILAN.append(w); return True
ns = {"threading": threading, "time": __import__("time"), "subprocess": __import__("subprocess"), "os": os, "print": lambda *a, **k: None, "AYAR": {}, "KONUS": {"durum": "kapali"},
      "_KS": {"w": None, "app": None, "tur": None, "kilit": threading.Lock(), "nesil_en": 0}, "claude_yolu": lambda: "/x", "konus_beyin_var": lambda: True, "BRIFING_APP": KOD, "konus_ac": konus_ac, "kaynak_dar": lambda: False}
ns["konus_canli"] = lambda: bool(ns["_KS"]["w"]) and ns["_KS"]["app"] is not None and ns["_KS"]["app"].poll() is None
exec(compile(ast.Module(sec, []), "bas-konus.py", "exec"), ns)
K, Y = ns["_KS"], ns["_KS_YEDEK"]
konus_ac(); K.update(ozel_gitti=True, defter_md="/d.md", sayac=2, maliyet=0.05); ozel_w, ozel_n = K["w"], K["nesil"]
ns["konus_yuva_degis"]("ortak")
ok("ortak cevap: özel süreç bekleyen yuvada (kapatılmadı), etkin yuva boş", Y.get("w") is ozel_w and not ozel_w.kapali and K["w"] is None and not K.get("ozel_gitti") and K.get("defter_md") is None)
konus_ac(); ortak_w = K["w"]
ok("yeni ortak sürecin okuyucu numarası bekleyenden farklı", K["nesil"] != ozel_n)
ns["konus_yuva_degis"]("özel")
ok("özel soru: bekleyen özel süreç geri geldi (okuyucu numarası, defter, sayaç, maliyet onunla)", K["w"] is ozel_w and K["nesil"] == ozel_n and K["defter_md"] == "/d.md" and K["sayac"] == 2 and K["maliyet"] == 0.05 and K["ozel_gitti"])
ok("ortak süreç şimdi bekliyor", Y.get("w") is ortak_w and not ortak_w.kapali and not Y.get("ozel_gitti"))
Y["app"].canli = False; ns["konus_yuva_degis"]("ortak")
ok("ölü bekleyen süreç: kapatılır, etkin yuva boşalır, özel süreç bekler", ortak_w.kapali and K["w"] is None and Y.get("w") is ozel_w)
ns["konus_yedek_kapat"]("boşta"); ok("bekleyen süreç boşta kapanır", ozel_w.kapali and not Y)
n = len(ACILAN); K["tur"] = {"x": 1}; ok("önceden açma: tur sürerken açmaz", ns["konus_on_ac"]("deneme") is False and len(ACILAN) == n)
K["tur"] = None; ns["AYAR"]["konus_on_ac"] = False; ok("önceden açma: ayar kapalıyken açmaz", ns["konus_on_ac"]("deneme") is False and len(ACILAN) == n)
ok("önceden açma: varsayılan kapalı (beta profili)", ns["AYAR"].pop("konus_on_ac", None) is False and ns["konus_on_ac"]("deneme") is False and len(ACILAN) == n)
ns["AYAR"]["konus_on_ac"] = True; ok("önceden açma: açar, panodaki durum değişmez", ns["konus_on_ac"]("deneme") is True and len(ACILAN) == n + 1 and ns["KONUS"]["durum"] == "kapali")
ok("önceden açma: süreç açıkken ikinciyi açmaz", ns["konus_on_ac"]("deneme") is False and len(ACILAN) == n + 1)
print("konuş yuva: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
