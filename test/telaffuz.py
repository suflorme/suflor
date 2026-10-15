#!/usr/bin/env python3
# Telaffuz (v0.32.1): aktarici/brifing-ses.py telaffuz() — sabit sözlükteki (aktarici/telaffuz-sozluk.json) İngilizce sözcükler Türkçe yazımla
# değişir (Türkçe ek korunur, büyük harfle başlayan sözcüğün okunuşu da büyük harfle başlar),
# okunan metinde bilinmeyen yabancı görünümlü sözcükler kuyruğa girer (Türkçe sözcükler girmez), telaffuz_ekle sonrası yeni okunuş kullanılır.
# Claude çağrısı yok. Kural ya da liste değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/telaffuz.py      (kaldı → çıkış 1)
import os, re, sys, json, time, threading, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
BASE = tempfile.mkdtemp(prefix="suflor-telaffuz-"); ARAYUZ_DILI = "tr"
_f = __file__; __file__ = os.path.join(KOD, "relay.py")  # bölüm relay.py'nin ad alanında çalışır: sözlük yolu relay.py'nin yanındaki aktarici/
exec(src[src.index("def _telaffuz_sozluk"):src.index("def telaffuz_adaylari")]); __file__ = _f
hata = 0
def bak(ad, v, b):
    global hata
    if v != b: hata += 1; print(f"✗ {ad}: {v!r}, beklenen {b!r}")
# 1) sabit liste, ek korunur, büyük/küçük harf
bak("Teams'te", telaffuz("Toplantıyı Teams'te yapalım."), "Toplantıyı Tims'te yapalım.")
bak("Zoom tek ünlü", telaffuz("Zoom'a geçelim"), "Zum'a geçelim")
bak("meeting", telaffuz("Yarınki meeting saat 10'da, deadline cuma."), "Yarınki miting saat 10'da, dedlayn cuma.")
bak("kısaltma yalnız büyük harfle", telaffuz("IP adresi verildi, ip atlamak yok, OK."), "Ay pi adresi verildi, ip atlamak yok, Okey.")
bak("Türkçe dokunulmaz", telaffuz("Bütçe onayını bekliyoruz."), "Bütçe onayını bekliyoruz.")
bak("Mac sesi: doğru okuduğu sözcüğe dokunulmaz, okuyamadığına sözlük (v0.39.2)", telaffuz("Teams'te meeting var, feedback ve KPI tablosu hazır.", mac=True), "Teams'te meeting var, fidbek ve Ki pi ay tablosu hazır.")
bak("Piper: aynı cümlede hepsine sözlük", telaffuz("Teams'te meeting var, feedback ve KPI tablosu hazır."), "Tims'te miting var, fidbek ve Ki pi ay tablosu hazır.")
bak("uzun ünlü şapkayla (v0.39.1, Mac sesi)", telaffuz("Cevabı şöyle: hesabını kontrol ettim, kağıt lazım."), "Cevâbı şöyle: hesâbını kontrol ettim, kâğıt lâzım.")
# 1b) sözlük dosyası okundu, büyük harf korunur (Piper küçük harfle başlayanı yeni cümle saymaz); Türkçe i → İ
bak("sözlük dosyası", len(TELAFFUZ) > 200 and TELAFFUZ.get("Teams") == "Tims", True)
bak("büyük harf korunur", telaffuz("Feedback'leri topladık. Deadline cuma."), "Fidbek'leri topladık. Dedlayn cuma.")
bak("küçük harf aynen", telaffuz("bu feedback iyi"), "bu fidbek iyi")
bak("kısaltma büyük harf", telaffuz("Toplantı bitti. KPI tablosu hazır."), "Toplantı bitti. Ki pi ay tablosu hazır.")
bak("Türkçe büyük İ", telaffuz("Toplantı bitti. Influencer listesi hazır."), "Toplantı bitti. İnfluensır listesi hazır.")
# 2) bilinmeyen yabancı sözcük kuyruğu
_TEL_BEK["q"].clear()
telaffuz("Bunu Ali ile Hubspot üzerinden konuşalım, sonra Biweekly kickoff yaparız. KDV dahil, aile toplantısı yok.")
q = list(_TEL_BEK["q"])
for w in ("Hubspot", "Biweekly", "kickoff", "KDV", "Ali"): bak(f"kuyrukta {w}", w in q, True)
for w in ("Bunu", "ile", "konuşalım", "sonra", "yaparız", "dahil", "toplantısı", "yok"): bak(f"kuyrukta değil {w}", w in q, False)
_TEL_BEK["q"].clear(); telaffuz("Hubspot yine geldi.")
bak("ikinci kez sorulmaz", _TEL_BEK["q"], [])
telaffuz("Toplantı bitti. Sonra bakarız.")
bak("cümle başı büyük harf Türkçe", _TEL_BEK["q"], [])
# 3) telaffuz_ekle → sonraki okumada kullanılır, telaffuz.json (elle) önce gelir
telaffuz_ekle({"Hubspot": "Habspot", "Biweekly": "Bayvikli"})
bak("oto okunuş", telaffuz("Hubspot'ta Biweekly var"), "Habspot'ta Bayvikli var")
json.dump({"Hubspot": "Hab spat"}, open(os.path.join(BASE, "telaffuz.json"), "w")); _TEL["re"] = None
bak("elle düzeltme önce", telaffuz("Hubspot"), "Hab spat")
print(f"telaffuz: " + ("✓ hepsi geçti" if not hata else f"{hata} hata"))
sys.exit(1 if hata else 0)
