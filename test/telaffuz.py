#!/usr/bin/env python3
# Telaffuz (v0.32.1): aktarici/brifing-ses.py telaffuz() — sabit listedeki İngilizce sözcükler Türkçe yazımla değişir (Türkçe ek korunur),
# okunan metinde bilinmeyen yabancı görünümlü sözcükler kuyruğa girer (Türkçe sözcükler girmez), telaffuz_ekle sonrası yeni okunuş kullanılır.
# Claude çağrısı yok. Kural ya da liste değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/telaffuz.py      (kaldı → çıkış 1)
import os, re, sys, json, time, threading, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
BASE = tempfile.mkdtemp(prefix="suflor-telaffuz-"); ARAYUZ_DILI = "tr"
exec(src[src.index("TELAFFUZ = {"):src.index("def telaffuz_adaylari")])
hata = 0
def bak(ad, v, b):
    global hata
    if v != b: hata += 1; print(f"✗ {ad}: {v!r}, beklenen {b!r}")
# 1) sabit liste, ek korunur, büyük/küçük harf
bak("Teams'te", telaffuz("Toplantıyı Teams'te yapalım."), "Toplantıyı Tims'te yapalım.")
bak("Zoom tek ünlü", telaffuz("Zoom'a geçelim"), "Zum'a geçelim")
bak("meeting", telaffuz("Yarınki meeting saat 10'da, deadline cuma."), "Yarınki miting saat 10'da, dedlayn cuma.")
bak("Türkçe dokunulmaz", telaffuz("Bütçe onayını bekliyoruz."), "Bütçe onayını bekliyoruz.")
# 2) bilinmeyen yabancı sözcük kuyruğu
_TEL_BEK["q"].clear()
telaffuz("Bunu Ali ile Hubspot üzerinden konuşalım, sonra Weekly sync yaparız. KDV dahil, aile toplantısı yok.")
q = list(_TEL_BEK["q"])
for w in ("Hubspot", "Weekly", "sync", "KDV", "Ali"): bak(f"kuyrukta {w}", w in q, True)
for w in ("Bunu", "ile", "konuşalım", "sonra", "yaparız", "dahil", "toplantısı", "yok"): bak(f"kuyrukta değil {w}", w in q, False)
_TEL_BEK["q"].clear(); telaffuz("Hubspot yine geldi.")
bak("ikinci kez sorulmaz", _TEL_BEK["q"], [])
telaffuz("Toplantı bitti. Sonra bakarız.")
bak("cümle başı büyük harf Türkçe", _TEL_BEK["q"], [])
# 3) telaffuz_ekle → sonraki okumada kullanılır, telaffuz.json (elle) önce gelir
telaffuz_ekle({"Hubspot": "Habspot", "Weekly": "Vikli"})
bak("oto okunuş", telaffuz("Hubspot'ta Weekly var"), "Habspot'ta Vikli var")
json.dump({"Hubspot": "Hab spat"}, open(os.path.join(BASE, "telaffuz.json"), "w")); _TEL["re"] = None
bak("elle düzeltme önce", telaffuz("Hubspot"), "Hab spat")
print(f"telaffuz: " + ("✓ hepsi geçti" if not hata else f"{hata} hata"))
sys.exit(1 if hata else 0)
