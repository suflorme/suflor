#!/usr/bin/env python3
# 28 Ekim gerçek Teams testi (üç düzeltme): (a) okurken kullanıcının altyazı satırındaki durdurma sözü okumayı keser (okunan metinde geçiyorsa kesmez);
# (b) yalnız addan oluşan askıdaki hitaba ilk devam 7 sn, ad ses benzeri yazılsa da ("Malmis") hitap olur, gündelik sözcük olmaz; (c) gecikme satırı turdan dolar.
# Adlar uydurma. Kaynaklar yalıtılmış ad alanında koşar:   PYTHONDONTWRITEBYTECODE=1 python3 test/hitap-ses.py
import ast, os, re, sys, time, threading
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok_ = []
def ok(ad, c): print(("✓ " if c else "✗ ") + ad); ok_.append(bool(c))
def oku(*y): return open(os.path.join(KOD, *y), encoding="utf-8").read()
def secim(kaynak, adlar, atamalar=()):
    agac = ast.parse(kaynak)
    return [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in atamalar for x in n.targets))]
KIS = {"v": {"ad": "Malvis", "hitap": ["Malvis"], "rol": "toplanti"}}
ns = {"re": re, "time": time, "print": lambda *a: None, "_ad_listesi": lambda: {"malbin": {"Malvin"}}, "kisilikler": lambda: [KIS["v"]]}
sec = secim(oku("aktarici", "kisilik.py"), (), ("KISILIK_SOZ_ETME", "KISILIK_ISTEK", "KISILIK_GIRIS")) + \
      secim(oku("aktarici", "bas-konus.py"), ("_ad_anahtar", "_ad_mesafe"), ("_AD_HARF",)) + \
      secim(oku("aktarici", "sozluk.py"), ("hitap_ses_duzelt", "hitap_aski", "hitap_yalniz_ad", "_hitap_adlari", "_hitap_alt", "_hitap_rx", "hitap_aski_bitti", "hitap_askida"),
            ("HITAP_ASKI", "HITAP_ASKI_SN", "HITAP_DEVAM_SN", "HITAP_AD_DEVAM_SN", "HITAP_ONCE_N", "HITAP_EN_COK_SN", "HITAP_EN_COK_SOZ", "HITAP_ONCE", "HITAP_AD"))
exec(compile(ast.Module(sec, []), "t", "exec"), ns)
d = ns["hitap_ses_duzelt"]
# (b) ses benzeri ad
ok("'Malmis beni duydun mu?' → Malvis", d("Malmis beni duydun mu?") == "Malvis beni duydun mu?")
ok("'malviz' tek sözcük", d("malviz") == "Malvis")
ok("giriş sözcüğünden sonra: 'Tamam, Malvish, bak.'", d("Tamam, Malvis bak.") == "Tamam, Malvis bak." and d("Peki Malbis, bak.") == "Peki Malvis, bak.")
ok("cümle başı ikinci cümle: 'Evet. Malmis, dinle'", d("Evet. Malmis, dinle") == "Evet. Malvis, dinle")
for s in ("Malzeme listesi hazır mı?", "Mallar geldi mi?", "Merhaba nasılsınız?", "Mermer fiyatı ne?", "Malvin geldi mi?", "Bugün malvis kaç kart var?", "Biz malmis dedik."):
    ok(f"yanlış pozitif yok: {s!r}", d(s) == s)
ok("cümle ortasındaki benzer sözcük değişmez", d("Bunu Malmis söyledi.") == "Bunu Malmis söyledi.")
ok("kısa ad (4 harf) bulanık eşleşmez", (KIS.__setitem__("v", {"ad": "Sera", "hitap": ["Sera"], "rol": "toplanti"}), d("Sara, bak.") == "Sara, bak.")[1])
KIS["v"] = {"ad": "Malvis", "hitap": ["Malvis"], "rol": "toplanti"}
# (b) 7 sn pencere
ha = ns["hitap_aski"]; now = time.time()
ok("yalnız ad askıya alınır", ha("Malvis", now, now + 1) is None and ns["HITAP_ASKI"]["metin"] and ns["HITAP_ASKI"]["pen"] == 7.0)
b = ha("beni duydun mu?", now + 6, now + 8)
ok("5 sn sonra gelen soru birleşir (askıdaki hitaba devam)", b and b.startswith("Malvis,") and "duydun mu?" in b)
ha("Malvis", now + 20, now + 21); b2 = ha("beni duydun mu?", now + 29.5, now + 31)
ok("8 sn sonra gelen soru birleşmez", b2 is None)
ns["HITAP_ASKI"].update(metin=None); ha("Malvis, beni duydun mu", now + 40, now + 42)
ok("ad + soru aynı satırda: eski davranış (askıya yalnız noktalamasız ≤ 6 sözcük), pen 2 sn", ns["HITAP_ASKI"]["pen"] == 2.0)
# (a) okurken altyazıdan durdurma
src = oku("aktarici", "otonom.py")
ns2 = {"re": re, "time": time, "okuma_suruyor": lambda: True, "kisilikler": lambda: [KIS["v"]], "sade": lambda x: re.sub(r"\W", "", x.lower()),
       "KENDI_SES": [], "YANKI_LOCK": threading.Lock(), "_kok_ayni": lambda a, b: a == b}
exec(compile(ast.Module(secim(oku("aktarici", "bas-konus.py"), (), ("ASISTAN_DUR_RX",)) + secim(src, ("okuma_dur_soz",)), []), "t", "exec"), ns2)
f = ns2["okuma_dur_soz"]
ok("'Bir dakika.' okurken durdurur", f("Bir dakika.", time.time() - 6) is True)
ns2["KENDI_SES"].append((time.time() - 3, time.time() + 5, ["lütfen", "bir", "dakika", "bekleyin"]))
ok("söz okunan metinde geçiyorsa durdurmaz", f("Bir dakika.", time.time() - 6) is False)
ns2["KENDI_SES"].clear(); ns2["okuma_suruyor"] = lambda: False
ok("okuma sürmüyorsa etkisiz", f("Bir dakika.", time.time() - 6) is False)
rl = oku("relay.py"); i = rl.index("ALTYAZI_SON.append((time.time(), kim_))")
ok("relay: ben altyazı satırı okuma_dur_soz'a gider", 'kim_ == ben_adi() and "okuma_dur_soz" in globals() and okuma_dur_soz(text' in rl[i:i + 600])
# (c) gecikme satırı: otonom_sun turu parametre alır; tur _KS'den silinmiş olsa da lat dolar
ok("otonom_sun tur parametresi alır ve çağıran verir", "def otonom_sun(cevap, kaynak, kim=None, ad=None, tur=None)" in src and "tur_ = tur or _KS.get(\"tur\") or {}" in src and
   'tur.get("ad") or tur.get("kisi"), tur)' in oku("aktarici", "bas-konus.py"))
print("SONUÇ:", "hepsi geçti" if all(ok_) else "başarısız"); sys.exit(0 if all(ok_) else 1)
