#!/usr/bin/env python3
# 28 Ekim (teams-duzelt): ben_kod/ben_neden — mikrofon açık ve ses parçaları akıyorsa "akiyor" (konuşan yok), "sorun" yalnız parça da gelmiyorsa;
# veri_yok kanalındaki ben kodu yanlış "mikrofon sorunu" kartına yol açmasın. Başlat seçimsiz: S166'da geri alındı (hiçbir uygulama açılmaz, pano platform sorar).
import os, re, sys, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
src = s[s.index("def ben_kod():"):s.index("def whisper_view")]
ST = {"mic": {}, "whisper": {"kanallar": {}}}
ns = {"STATE": ST, "time": time, "WH_AKIS_SN": 20, "_t": lambda tr, en: tr}; exec(src, ns)
ok_ = []
def ok(ad, c): print(("✓ " if c else "✗ ") + ad); ok_.append(c)
now = time.time()
ST["mic"] = {"t": now, "on": True, "sessiz": False, "hata": ""}
ST["whisper"]["kanallar"]["ben"] = now - 2
ok("mikrofon açık + parça akıyor → akiyor", ns["ben_kod"]() == "akiyor" and "konuşan yok" in ns["ben_neden"]())
ST["whisper"]["kanallar"]["ben"] = now - 60
ok("mikrofon açık + parça yok → sorun", ns["ben_kod"]() == "sorun" and "ses gelmiyor" in ns["ben_neden"]())
ST["mic"]["sessiz"] = True; ok("sessizde → sessiz", ns["ben_kod"]() == "sessiz")
ST["mic"].update(sessiz=False, on=False); ok("kapalı → kapali", ns["ben_kod"]() == "kapali")
ST["mic"].update(on=True, hata="x"); ok("hata → hata", ns["ben_kod"]() == "hata")
r = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
ok("Başlat seçimsiz hiçbir platforma düşmez (S166)", "son_tanin_platform" not in r)
print("SONUÇ:", "hepsi geçti" if all(ok_) else "başarısız"); sys.exit(0 if all(ok_) else 1)
