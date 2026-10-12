#!/usr/bin/env python3
# Sesli kanıt isteği (v0.31.6): relay.py'deki SESLI_KANIT_RX / SESLI_KANIT_YOK kalıpları — istek biçimi tetikler, konu içinde geçen sözcük ve
# olumsuz istek tetiklemez (Faz 2'de üç yanlış alarm yüzünden kaldırılmıştı). Kural değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-kanit.py      (kaldı → çıkış 1)
import os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
exec(src[src.index("SESLI_KANIT_RX ="):src.index("SESLI_KANIT = {")])
ORNEK = [("Kanıt al.", 1), ("Ekran görüntüsünü alır mısın?", 1), ("şunun ekran görüntüsü alalım", 1), ("Claude: ekran kaydı başlat", 1),
         ("Can you take a screenshot?", 1), ("ekran resmini çek", 1), ("Bir kanıt alsana şuna", 1),
         ("Ekran görüntüsü almayalım şimdi", 0), ("kanıt almaya gerek yok", 0), ("bu konuda kanıt var mı", 0), ("ekran görüntüsü paylaştım", 0),
         ("ekran kaydı var elimizde", 0), ("kanıtı aldık zaten geçen hafta", 0), ("don't take a screenshot", 0)]
hata = 0
for t, b in ORNEK:
    v = bool(SESLI_KANIT_RX.search(t)) and not SESLI_KANIT_YOK.search(t)
    if v != bool(b): hata += 1; print(f"✗ {t!r}: {v}, beklenen {bool(b)}")
print(f"sesli kanıt: {len(ORNEK) - hata}/{len(ORNEK)}" + (" ✓ hepsi geçti" if not hata else ""))
sys.exit(1 if hata else 0)
