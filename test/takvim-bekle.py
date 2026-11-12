#!/usr/bin/env python3
# Takvim döngüsünün bekleme süresi (12 Kasım): yaklaşan toplantı varken sık, izin yokken 30 dk, geçici hatada bir kez 5 dk sonra yeniden dene.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/takvim-bekle.py
import datetime, os, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); HATA.extend([] if k else [ad])
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ad = {"datetime": datetime, "TAKVIM_SN": 300, "TAKVIM_TAM": {}}
exec(kod[kod.index("TAKVIM_SN_YAKIN = "):kod.index("def _takvim_dongu():")], ad)
bekle = ad["takvim_bekle_sn"]; simdi = datetime.datetime.now(datetime.timezone.utc); iso = lambda s: (simdi + datetime.timedelta(seconds=s)).isoformat()
ok("toplantı yok: normal aralık (300 sn)", bekle("ok") == 300)
ad["TAKVIM_TAM"] = {"a": {"baslangic": iso(7200)}}; ok("2 saat sonra toplantı: sık yenileme (120 sn)", bekle("ok") == 120)
ad["TAKVIM_TAM"] = {"a": {"baslangic": iso(-1800)}}; ok("yarım saat önce başlamış: sık yenileme", bekle("ok") == 120)
ad["TAKVIM_TAM"] = {"a": {"baslangic": iso(6 * 3600)}}; ok("6 saat sonra: normal aralık", bekle("ok") == 300)
ad["TAKVIM_TAM"] = {"a": {"baslangic": "bozuk"}}; ok("bozuk başlangıç: hata vermez, normal aralık", bekle("ok") == 300)
ok("izin yok: 30 dk", bekle("izin_yok") == 1800)
ok("zaman aşımı ilk kez: 5 dk sonra yeniden (eskiden 30 dk)", bekle("zaman_asimi", 1) == 300)
ok("zaman aşımı üst üste: 30 dk", bekle("zaman_asimi", 2) == 1800)
print("takvim bekleme:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
