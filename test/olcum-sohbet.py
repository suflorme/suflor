#!/usr/bin/env python3
# olcum.py sohbet (Konuş Aşama 2 Adım 6): yapay sohbet-olay.jsonl + claude-cagri.jsonl ile özet sayıları, hedef kıyası, yetersiz veri, metinsizlik.
# Gerçek aktarıcı, ses ya da model yok. Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/olcum-sohbet.py
import datetime, importlib.util, json, os, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("olcum_t", os.path.join(KOD, ".claude", "skills", "suflor-olcum", "olcum.py")); OL = importlib.util.module_from_spec(sp); sp.loader.exec_module(OL)
S = {"gec": 0}
def ok(ad, c, d=""):
    print(("PASS " if c else "FAIL ") + ad + ("" if c else f"  → {d}")); S["gec"] += 0 if c else 1
T = tempfile.mkdtemp(); OL.CANLI = T
simdi = datetime.datetime.now().astimezone()
at = lambda dk: (simdi - datetime.timedelta(minutes=dk)).isoformat(timespec="seconds")
def yaz(ad, rows): open(os.path.join(T, ad), "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

# --- 1) veri yok: hata yok, yetersiz veri ---
o = OL.sohbet_ozet(7); md = OL.sohbet_md(o)
ok("veri yok: dakika 0, oranlar yetersiz veri, düşme 0", o["toplam"]["dakika"] == 0 and o["toplam"]["yanlis_10dk"] is None and o["dusme_toplam"] == 0 and "yetersiz veri" in md, md)

# --- 2) yapay veri: hoparlör 20 dk, kulaklık 10 dk ---
ol = [{"at": at(60), "olay": "sohbet_sure", "sure_ms": 20 * 60000, "yerel": True, "hoparlor": True},
      {"at": at(30), "olay": "sohbet_sure", "sure_ms": 10 * 60000, "yerel": True, "hoparlor": False},
      {"at": at(5), "olay": "sohbet_sure", "sure_ms": 99 * 60000, "yerel": False, "hoparlor": False}]  # yerel olmayan sohbet dakikaya girmez
for ms in (500, 600, 700, 800, 900): ol.append({"at": at(50), "olay": "araya_girme", "sinif": "dur", "kaynak": "tstt", "tepki_ms": ms, "hoparlor": True})
ol += [{"at": at(50), "olay": "araya_girme", "sinif": "baska", "kaynak": "whisper", "tepki_ms": 900, "hoparlor": True},
       {"at": at(49), "olay": "araya_girme", "sinif": "baska", "kaynak": "tstt", "tepki_ms": 700, "hoparlor": False, "onaydi": True}]
ol += [{"at": at(48), "olay": "olasi_yanlis", "sinif": "baska", "kaynak": "whisper", "tepki_ms": 900, "hoparlor": True}] * 2 + [{"at": at(40), "olay": "olasi_yanlis", "hoparlor": False}]
ol += [{"at": at(47), "olay": "kacan_aday", "sure_ms": 800, "hoparlor": True}] * 4
ol += [{"at": at(46), "olay": "onay_gecti", "sure_ms": 500, "kaynak": "tstt", "hoparlor": True}] * 8 + [{"at": at(45), "olay": "onay_gecti", "hoparlor": False}] * 2
ol += [{"at": at(44), "olay": "bolunen_soru", "gecikme_ms": 900, "hoparlor": True}] * 3 + [{"at": at(43), "olay": "bolunen_soru", "gecikme_ms": 400, "hoparlor": False}]
ol += [{"at": at(42), "olay": "yerel_dusme", "neden": "cal_basladi_yok"}] * 2 + [{"at": at(41), "olay": "yerel_dusme", "neden": "say_OSError"}]
ol += [{"at": at(60 * 24 * 30), "olay": "kacan_aday", "hoparlor": True}]  # pencere dışı
yaz("sohbet-olay.jsonl", ol)
cg = []
for i in range(10): cg.append({"at": at(50 - i), "is": "bas-konus", "tur_turu": "sohbet", "yerel": True, "cikis": "hoparlör", "soz_bitis_ses_ms": 1500 + 10 * i})
for i in range(6): cg.append({"at": at(30 - i), "is": "bas-konus", "tur_turu": "devam", "yerel": True, "cikis": "kulaklık", "soz_bitis_ses_ms": 1400 + 10 * i})
for i in range(6): cg.append({"at": at(20 - i), "is": "bas-konus", "tur_turu": "sohbet", "yerel": False, "cikis": "kulaklık", "soz_bitis_ses_ms": 1450 + 10 * i})
cg.append({"at": at(10), "is": "bas-konus", "tur_turu": "bas", "yerel": False, "cikis": "kulaklık", "soz_bitis_ses_ms": 900})  # basılı tutma: sohbet kıyasına girmez
yaz("claude-cagri.jsonl", cg)
o = OL.sohbet_ozet(7); T_, H_, K_ = o["toplam"], o["hoparlör"], o["kulaklık"]
ok("dakika: toplam 30, hoparlör 20, kulaklık 10 (yerel olmayan sayılmaz)", (T_["dakika"], H_["dakika"], K_["dakika"]) == (30.0, 20.0, 10.0), o)
ok("araya girme: 7 (dur 5, başka 2); pencere dışı olay yok", (T_["araya_girme"], T_["araya_girme_dur"], T_["araya_girme_baska"]) == (7, 5, 2), T_)
ok("dur tepkisi ortanca 700 ms, p90 900 ms", (T_["dur_tepki_ms"]["ortanca"], T_["dur_tepki_ms"]["p90"], T_["dur_tepki_ms"]["n"]) == (700.0, 900.0, 5), T_["dur_tepki_ms"])
ok("olası yanlış 3 → 10 dk başına 1,0 (toplam), hoparlör 2/20 dk → 1,0, kulaklık 1/10 dk → 1,0", (T_["yanlis_10dk"], H_["yanlis_10dk"], K_["yanlis_10dk"]) == (1.0, 1.0, 1.0), (T_, H_, K_))
ok("kaçan 4 → toplam 1,33; hoparlör 2,0; kulaklık 0", (T_["kacan_10dk"], H_["kacan_10dk"], K_["kacan_10dk"]) == (1.33, 2.0, 0.0), (T_["kacan_10dk"], H_["kacan_10dk"], K_["kacan_10dk"]))
ok("bölünen 4 → toplam 1,33 /10 dk", T_["bolunen"] == 4 and T_["bolunen_10dk"] == 1.33, T_)
ok("erken kapanış: toplam 4/16 tur = 0,25; hoparlör 3/10 = 0,3; kulaklık 1/6", (T_["tur"], T_["erken_kapanis"], H_["erken_kapanis"], K_["tur"]) == (16, 0.25, 0.3, 6) and K_["erken_kapanis"] == round(1 / 6, 3), (T_, H_, K_))
ok("hı hı: 10 geçti, 1 kesti (onaydi) → kesmez %91", (T_["onay_gecti"], T_["onayda_kesme"], T_["onay_kesmez"]) == (10, 1, 0.909), T_)
ok("yerel düşme 3 (cal_basladi_yok 2, say_OSError 1)", o["dusme_toplam"] == 3 and o["dusme"] == {"cal_basladi_yok": 2, "say_OSError": 1}, o["dusme"])
sb = o["soz_bitis_ses"]
ok("söz bitişi: yerel n 16 (bas turu ve yerel olmayan ayrı), yerel değil n 6", (sb["yerel"]["n"], sb["yerel_degil"]["n"]) == (16, 6), sb)
ok("söz bitişi kıyas: yerel ortanca − yerel değil ≤ 100 ms → gerilemedi", sb["durum"] == "tamam" and abs(sb["fark_ms"]) <= 100, sb)
md = OL.sohbet_md(o)
ok("md: tablo, AŞILDI (yanlış ve kaçan toplam üst sınırda/aşmış), yetersiz veri yok", "| Ölçüt | Hedef |" in md and "Kaçan söz" in md and "AŞILDI" in md and "gerilemedi" in md, md)
ok("md: dur tepkisi 700 ms hedef 0,6 sn aşıldı", "700 / 900 ms (5) AŞILDI" in md, md)

# --- 3) söz bitişi geriledi ---
cg2 = [dict(r, soz_bitis_ses_ms=r["soz_bitis_ses_ms"] + 400) if r.get("yerel") else r for r in cg]; yaz("claude-cagri.jsonl", cg2)
o2 = OL.sohbet_ozet(7)
ok("söz bitişi: yerel 400 ms yavaş → geriledi", o2["soz_bitis_ses"]["durum"] == "geriledi" and o2["soz_bitis_ses"]["fark_ms"] > 300, o2["soz_bitis_ses"])
ok("md: geriledi görünür", "GERILEDI" in OL.sohbet_md(o2).upper(), OL.sohbet_md(o2))

# --- 4) metinsizlik: olaylarda metin alanı yok (kaynak kod denetimi) ---
src = open(os.path.join(KOD, "aktarici", "sohbet.py"), encoding="utf-8").read()
import re
cagrilar = re.findall(r"_ag_olay\(([^\n]*)", src)
ok("sohbet.py: ölçüm olayı çağrıları var ve 'metin' alanı taşımıyor", len(cagrilar) >= 6 and not any("metin" in c for c in cagrilar), cagrilar)
bk = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ok("bas-konus.py: claude-cagri satırına cikis ve yerel eklenir", "_konus_cikis_yerel(tur)" in bk and '("cikis", "yerel")' in bk)
bv = open(os.path.join(KOD, "aktarici", "beta-veri.py"), encoding="utf-8").read(); ts = open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read()
ok("beta paketine girmez: beta-veri.py ve teshis.py sohbet-olay / araya_girme anmaz", "sohbet-olay" not in bv and "araya_girme" not in bv and "sohbet-olay" not in ts)
print(f"\n{'TAMAM' if not S['gec'] else str(S['gec']) + ' HATA'}"); sys.exit(1 if S["gec"] else 0)
