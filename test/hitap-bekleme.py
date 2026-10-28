#!/usr/bin/env python3
# 28 Ekim (kullanıcı isteği): karşı kanal akarken kullanıcının asistana seslendiği satır yankı için 4 sn bekletilmez; hitapsız satır yine bekletilir,
# gelmiş karşı satırının yankısı yine atılır. whisper_yaz kaynağı yalıtılmış ad alanında koşar.
import os, re, sys, threading, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
src = s[s.index("def whisper_yaz("):s.index("def _whisper_yaz(")]
yazilan = []
class Zamanlayici:
    def __init__(self, *a, **k): pass
    def start(self): pass
ns = {"STATE": {"whisper": {"kanallar": {}}}, "time": time, "re": re, "threading": type("T", (), {"Timer": Zamanlayici, "Thread": threading.Thread}),
      "WH_AKIS_SN": 20, "YANKI_LOCK": threading.Lock(), "KENDI_SES": [], "YANKI_KARSI": [], "YANKI_BEKLEYEN": [],
      "_yk": lambda m: m.lower().split(), "_kendi_mi": lambda m, k: False, "_yanki_mi": lambda m, k: m[2] == k[2], "_yanki_say": lambda m: None,
      "_karsi_bekleniyor": lambda t0, t1: True, "_yanki_bosalt": lambda: None, "_whisper_yaz": lambda is_, m, *a: yazilan.append(m),
      "_hitap_alt": lambda: "(?:SERA|LALE)"}
exec(src, ns)
ok_ = []
def ok(ad, c): print(("✓ " if c else "✗ ") + ad); ok_.append(c)
now = time.time(); ns["STATE"]["whisper"]["kanallar"]["karsi"] = now - 1
def is_(): return {"kanal": "ben", "t0": now - 2, "t1": now}
ok("hitaplı satır hemen yazılır", ns["whisper_yaz"](is_(), "Tamam. Sera, bugün toplantım var mı?") == "satir" and yazilan[-1].startswith("Tamam"))
ok("hitapsız satır bekletilir", ns["whisper_yaz"](is_(), "bugün toplantım var mı") == "bekletildi" and len(ns["YANKI_BEKLEYEN"]) == 1)
ok("ad başka sözcüğün parçasıysa hitap sayılmaz", ns["whisper_yaz"](is_(), "seralar geldi") == "bekletildi")
ns["YANKI_KARSI"].append((now - 2, now, ["sera", "nasılsın"]))
ok("gelmiş karşı satırının yankısı hitaplı olsa da atılır", ns["whisper_yaz"](is_(), "Sera nasılsın") == "yanki")
print("SONUÇ:", "hepsi geçti" if all(ok_) else "başarısız"); sys.exit(0 if all(ok_) else 1)
