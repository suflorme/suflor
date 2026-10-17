#!/usr/bin/env python3
# Konuş süreci bilerek kapatılınca (tur sınırı, kişilik/toplantı değişimi) eski sürecin okuyucusu çıkarken yeni sorunun turunu silmemeli ve panoya
# "Claude süreci kapandı" yazmamalı (v0.70.1); beklenmedik çıkışta hata yine yazılır. aktarici/bas-konus.py'nin kendi tanımları AST ile alınır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/surec-yenileme.py      (kaldı → çıkış 1)
import ast, os, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
agac = ast.parse(open(os.path.join(KOD, "aktarici/bas-konus.py"), encoding="utf-8").read())
sec = [n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name in ("konus_kapat", "_konus_oku")]
KUR = []; ns = {"json": __import__("json"), "print": lambda *a, **k: None, "_t": lambda a, b: a, "KONUS": {"durum": "hazir"}, "_konus_kur": lambda **k: KUR.append(k)}
exec(compile(ast.Module(sec, []), "bas-konus.py", "exec"), ns)
bos = tempfile.NamedTemporaryFile(delete=False); bos.close()  # okuyucu hemen dosya sonuna gelir (süreç çıktı)
hata = 0
def ok(ad, k):
    global hata; hata += not k; print(("✓ " if k else "✗ ") + ad)
class W:
    def close(self): pass
# 1) bilerek kapatıldı, yeni soru geldi, yeni süreç henüz açılmadı (nesil aynı)
ns["_KS"] = {"w": W(), "app": None, "tur": None, "nesil": 5}; KUR.clear()
ns["konus_kapat"]("tur sınırı", durum_koru=True); tur = {"metin": ""}; ns["_KS"]["tur"] = tur
ns["_konus_oku"](bos.name, 5)
ok("bilerek kapatılan sürecin okuyucusu: hata yok, yeni sorunun turu duruyor", not any(k.get("durum") == "hata" for k in KUR) and ns["_KS"]["tur"] is tur)
# 2) beklenmedik çıkış (kapatılmadı): hata yazılır, tur temizlenir
ns["_KS"] = {"w": W(), "app": None, "tur": {"metin": ""}, "nesil": 6, "kapali_nesil": 5}; KUR.clear()
ns["_konus_oku"](bos.name, 6)
ok("beklenmedik çıkış: panoda hata, tur silindi", any(k.get("durum") == "hata" for k in KUR) and ns["_KS"]["tur"] is None)
# 3) yeni süreç açıldıktan sonra eski okuyucu: nesil farklı, dokunmaz
ns["_KS"] = {"w": W(), "app": None, "tur": {"metin": ""}, "nesil": 7, "kapali_nesil": 6}; KUR.clear()
ns["_konus_oku"](bos.name, 6)
ok("eski nesil okuyucusu yeni sürece dokunmaz", not KUR and ns["_KS"]["tur"])
os.remove(bos.name)
print("GEÇTİ" if not hata else f"KALDI: {hata}"); sys.exit(1 if hata else 0)
