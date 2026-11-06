#!/usr/bin/env python3
# Aynı soruya tek cevap (aktarici/bas-konus.py soru_yine_mi / _asistan_sor): 5 Kasım toplantısında karşı tarafın "X mıydı?" sorusu iki farklı konuşmacı adıyla
# ("X mıydı?", "X mıydı? Teşekkür ediyorum.", "X mıydı? Çok nazik seni.") üç kez geldi → iki cevap kartı. Kurgu sorular, gerçek örneğin biçimi. Farklı sorular birleşmemeli.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tek-kart.py
import os, re, sys, time, threading
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad, flush=True); HATA.append(ad) if not k else None
src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
bas = src.index("SORU_YINE_SN = "); son = src.index("def _asistan_sor(")
BIRINCI = src.index("def _asistan_sor("); bitis = src.index("_HITAP_SON = {", BIRINCI)
CAGRI = []; KS = {"tur": None}
ns = {"re": re, "time": time, "threading": threading, "_KS": KS, "ASISTAN_BEKLE_SN": 30, "LAT": {}, "LAT_ESKI_SN": 60, "AYAR": {}}
ns.update(otonom_acik=lambda: False, _konus_kur=lambda **k: None, _konus_sor=lambda m, t: CAGRI.append(m), kisilikler=lambda: [], kisilik_sec=lambda a: None)
exec(compile(src[bas:son], "bas-konus-parca", "exec"), ns)
exec(compile(src[BIRINCI:bitis], "bas-konus-sor", "exec"), ns)
def sor(s, kaynak="karsi", kim="X"):
    n = len(CAGRI); ns["_asistan_sor"](s, {"kaynak": kaynak, "ad": "Asistan", "karsi": kim}); time.sleep(0.05); return len(CAGRI) - n
yine = ns["soru_ayni_mi"]; kok = ns["_soru_kokleri"]
S1 = "Marvel'in asistanı mıydı normalde?"
ok("kökler: Türkçe harf/büyük küçük harf/ek duyarsız", kok("SELİM Bey'in sorusuna") == kok("selim bey'in sorusunu") or kok("Sorusunu soruyor") == kok("sorusuna soruyor"))
ok("aynı soru + sonuna eklenen selam aynı sayılır", yine(kok(S1), kok(S1 + " Teşekkür ediyorum.")) and yine(kok(S1), kok(S1 + " Çok nazik seni.")))
ok("farklı soru aynı sayılmaz (konu aynı, istek farklı)", not yine(kok("Toplantı ne zaman biter?"), kok("Toplantı ne zaman biter ve kim katılacak, ayrıca gündem nedir?")))
ok("tamamen farklı soru", not yine(kok(S1), kok("Panel'ta chat sayısı var mı?")))
ok("çok kısa (2 kök) soru birleştirilmez", not yine(kok("Evet mi?"), kok("Evet mi yoksa hayır mı?")))
ok("aynı kökte ama ters/başka ek sözcüklü uzun soru birleşmez", not yine(kok("Kerem Bey'in saydığı riskler neydi?"), kok("Kerem Bey'in saydığı riskler neydi, hangisi en ciddi, kim sorumlu, ne zaman kapanır?")))
# gerçek akış: 19:41:22 → 19:41:31 (farklı konuşmacı adı) → 19:41:32 (sıraya girecekti)
ok("ilk soru Claude'a gider", sor(S1, kim="Kerem") == 1)
ok("9 sn sonra aynı soru (+ 'Teşekkür ediyorum', başka konuşmacı adı) ikinci cevap üretmez", sor(S1 + " Teşekkür ediyorum.", kim="ümit") == 0)
ns["_KS"]["tur"] = {"kaynak": "karsi"}  # önceki cevap sürerken gelen: sıraya girmeden elenir (iki kart bu yoldan çıkmıştı)
ok("cevap sürerken gelen üçüncü varyant da sıraya girmez", sor(S1 + " Çok nazik seni.", kim="ümit") == 0 and True)
ns["_KS"]["tur"] = None
ok("yalnız bir çağrı yapıldı", len(CAGRI) == 1)
ok("farklı soru normal gider", sor("Bu hafta hangi risk en ciddi?", kim="ümit") == 1)
# zaman penceresi
t0 = time.time(); ns["_SORU_SON"].clear()
ok("pencere içinde (60 sn) benzer: önceki döner", ns["soru_yine_mi"]("Panel'ta chat sayısı var mı bugün?", "karsi", t0) is None and ns["soru_yine_mi"]("Panel'ta chat sayısı var mı bugün? Lütfen", "karsi", t0 + 60) is not None)
ok("pencere dışında (160 sn) yeniden sorulabilir", ns["soru_yine_mi"]("Panel'ta chat sayısı var mı bugün? Lütfen bak", "karsi", t0 + 160) is None)
ns["_SORU_SON"].clear()
ok("kullanıcının kendi hitabı bu denetime girmez (cevapsız kalınca bilerek yineler; konus_hitap'ın 20 sn denetimi ayrı)", ns["soru_yine_mi"]("Beni duyuyor musun", "hitap", t0) is None and ns["soru_yine_mi"]("Beni duyuyor musun", "hitap", t0 + 10) is None and not ns["_SORU_SON"])
print("\nSONUÇ:", "TAMAM" if not HATA else f"{len(HATA)} hata: {HATA}"); sys.exit(1 if HATA else 0)
