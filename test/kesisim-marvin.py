#!/usr/bin/env python3
# Kesişim dilimi (12 Kasım, F4 Marvin dilimi): kisi-modeli.py `_km_kesisim_metni` + bas-konus.py `kesisim_tur_notu`/KESISIM_KURAL. Sahte kesisim.json; relay.py'nin
# gerçek `kesisim_sayfa_veri`'si kaynaktan alınıp çalıştırılır. Süreç/port/Claude yok.   PYTHONDONTWRITEBYTECODE=1 python3 test/kesisim-marvin.py   (kaldı → çıkış 1)
import datetime, json, os, re, sys, tempfile, threading, time, secrets
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.realpath(tempfile.mkdtemp(prefix="kesmarvin-")); canli = os.path.join(T, "canli"); os.makedirs(canli)
hata = []; LOG = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
simdi = datetime.datetime.now().astimezone().replace(hour=14, minute=5, second=0, microsecond=0)
bugun = simdi.date().isoformat()
st = {"gel": True, "gizli": False}
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "secrets": secrets, "print": lambda *a, **k: LOG.append(" ".join(map(str, a))),
      "_t": lambda a, b: b if ns["ARAYUZ_DILI"] == "en" else a, "ARAYUZ_DILI": "tr", "BASE": canli, "AYAR": {"uygulama": T}, "_KS": {}, "TAKVIM_TAM": {}, "SON": []}
ns["gelistirici_mi"] = lambda: st["gel"]; ns["gizli_acik"] = lambda: st["gizli"]
rel = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
i = rel.index("def kesisim_sayfa_veri()"); j = rel.index("def kesisim_geri_al(")
exec(rel[i:j], ns)
exec(open(os.path.join(KOD, "aktarici", "kisi-modeli.py"), encoding="utf-8").read(), ns)
bs = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
exec(bs[bs.index("def kesisim_tur_notu"):bs.index("def konus_istem(")], ns)
bp = ns["baglam_paketi"]
def yaz(olusturma=None, bul=None, cozum=None, olay=None, sor=None):
    olusturma = olusturma or simdi.replace(tzinfo=None).isoformat(timespec="seconds")
    bul = bul if bul is not None else [{"id": f"{n:08x}", "ozet": f"Bulgu {n}: Atlas projesinde tarih iki yerde farklı", "kaynaklar": [{"sistem": "oh"}, {"sistem": "tazi"}]} for n in range(1, 7)]
    c = cozum if cozum is not None else {"tarih": bugun, "duzeltilen": 3, "arastirilan": 2, "birakilan": 0, "cozulemeyen_onemli": sor or []}
    json.dump({"olusturma": olusturma, "bulgular": bul, "kaynaklar": [], "cozum": c}, open(os.path.join(canli, "kesisim.json"), "w", encoding="utf-8"), ensure_ascii=False)
    olay = olay if olay is not None else [{"id": "00000001", "eylem": "tazi_dosya_eklendi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds"), "geri_al": True},
                                           {"id": "00000002", "eylem": "tazi_dosya_eklendi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")},
                                           {"id": "00000003", "eylem": "tazi_dosya_eklendi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")},
                                           {"id": "00000002", "eylem": "geri_alindi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")},
                                           {"id": "00000004", "eylem": "tazi_kuyruga_alindi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")},
                                           {"id": "00000005", "eylem": "tazi_kuyruga_alindi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")}]
    open(os.path.join(canli, "kesisim-coz.jsonl"), "w", encoding="utf-8").write("".join(json.dumps(o) + "\n" for o in olay))
def paket(**k): return bp("konus", dilimler=["kesisim"], simdi=simdi, **k)
# 1) içerik
sor = [{"id": "0000000a", "ozet": "Atlas sözleşmesinin bitiş tarihi kayıtta 30 Kasım, Tazı'da 15 Aralık", "neden": "celiski"}, {"id": "0000000b", "ozet": "İkinci önemli soru", "neden": "x"}, {"id": "0000000c", "ozet": "Üçüncü soru (görünmemeli)", "neden": "x"}]
yaz(sor=sor); p = paket()
ok("dilim var: düzeltilen 2 (geri alınan sayılmaz), 2 araştırılan, örnek satırı", "[/Çapraz kontrol (Kesişim)]" in p and "Bugün düzeltilen: 2" in p and "Araştırılan: 2" in p and "Bulgu 3:" in p)
ok("geri alınmış (00000002) örnekte yok", "Bulgu 2:" not in p)
ok("sormam gerekenler en çok 2 madde", "Sana sormam gerekenler" in p and p.count("\n- ") == 2 and "Üçüncü soru" not in p)
ok("sorma görevi var (bugün sorulmadı)", ns["KM_KS_SORU_ISARET"][0] in p)
ok("bütçe: dilim ≤ 900 karakter", len(p) <= 900); print("  dilim", len(p), "karakter")
# 2) bütçe sınırı: çok uzun özet kesilir
yaz(sor=[{"id": "0000000a", "ozet": "x" * 900, "neden": "x"}, {"id": "0000000b", "ozet": "y" * 900, "neden": "x"}], bul=[{"id": f"{n:08x}", "ozet": "z" * 900, "kaynaklar": []} for n in range(1, 7)])
ok("uzun özetlerde dilim 800 karakteri aşmaz", 0 < len(paket()) <= 800)
yaz(sor=sor); ok("toplam bütçe küçükken (en_cok_kr=500) dilim kesilir, başlık/kapanış durur", 0 < len(bp("konus", dilimler=["kesisim"], simdi=simdi, en_cok_kr=500)) <= 560)
# 3) soruldu işareti
yaz(sor=sor); n = ns["kesisim_tur_notu"](paket())
ok("kesisim_tur_notu günlüğe satır yazar", any(re.fullmatch(r"KONUŞ: kesişim dilimi \d+ karakter", l) for l in LOG))
ok("sorma görevi giden turda işaret yazıldı", ns["kesisim_soruldu_mu"](simdi) and os.path.isfile(os.path.join(canli, "kesisim-soruldu.json")))
p2 = paket(); ok("işaretten sonra dilim 'bugün soruldu' der, görev yok", "Bugün soruldu" in p2 and ns["KM_KS_SORU_ISARET"][0] not in p2)
ok("dün işaretlendiyse bugün yeniden sorulur", ns["kesisim_soruldu_mu"](simdi + datetime.timedelta(days=1)) is False)
n0 = len(LOG); ns["kesisim_tur_notu"](p2); ok("görev yoksa işaret dosyası değişmez ama günlük satırı yine yazılır", len(LOG) == n0 + 1)
ns["kesisim_tur_notu"]("başka bir paket"); ok("dilimsiz pakette günlük satırı yok", len(LOG) == n0 + 1)
# 4) bayat
yaz(olusturma=(simdi - datetime.timedelta(hours=40)).replace(tzinfo=None).isoformat(timespec="seconds"), sor=sor); pb = paket()
ok("36 saatten eski → tek satır 'bugün koşmadı', örnek/soru yok", "koşmadı" in pb and "Bugün düzeltilen" not in pb and "Sana sormam" not in pb and pb.count("\n") <= 3)
yaz(olusturma=(simdi - datetime.timedelta(hours=30)).replace(tzinfo=None).isoformat(timespec="seconds")); ok("30 saatlik veri bayat sayılmaz", "Bugün düzeltilen" in paket())
# 5) kapılar
yaz(sor=sor); st["gel"] = False; ok("beta (geliştirici değil) → dilim boş", paket() == "")
st["gel"] = True; st["gizli"] = True; ok("gizli kip → dilim boş (önbellek eski içeriği vermez)", paket() == ""); st["gizli"] = False
ok("gizli kip kapanınca dilim geri gelir", "Bugün düzeltilen" in paket())
os.remove(os.path.join(canli, "kesisim.json")); ok("kesisim.json yok → boş", paket() == "")
yaz(sor=sor); os.remove(os.path.join(canli, "kesisim-coz.jsonl")); ok("jsonl yok → çökmez, düzeltilen 0", "Bugün düzeltilen: 0" in paket())
# 6) amaçlar
yaz(sor=sor)
ok("toplantı amacında varsayılan yok", "Kesişim" not in bp("toplanti", simdi=simdi) and "kesisim" not in ns["KM_AMAC"]["toplanti"][0])
ok("konuş amacında varsayılan var", "kesisim" in ns["KM_AMAC"]["konus"][0] and "Kesişim" in bp("konus", simdi=simdi))
ok("brifing/talimat/e-posta/kayit amacında yok", all("Kesişim" not in bp(a, simdi=simdi) for a in ("brifing", "talimat", "eposta", "kayit")))
ok("eylem-menu kayıt turu dilimi dışlar", '"kesisim")]' in open(os.path.join(KOD, "aktarici", "eylem-menu.py"), encoding="utf-8").read())
ok("gizli kipte kesisim KM_GIZLI_SERBEST dışı (iki kat süzgeç)", "kesisim" not in ns["KM_GIZLI_SERBEST"])
# 7) kişisel/sağlık kaydı: kesisim.py süzer; dilim yalnız bulgu özetini taşır (kayıt dosyası ham metni yok)
ok("kesisim.py kişisel/sağlık süzgeci duruyor (OZEL_RX; dilim tekrar süzmez)", "OZEL_RX" in open(os.path.join(KOD, "kesisim.py"), encoding="utf-8").read())
# 8) İngilizce
ns["ARAYUZ_DILI"] = "en"; ns["_KM_ONB"].clear(); pe = paket(); ok("İngilizce dilim ve sorma görevi", "Cross-check (Kesişim)" in pe and "Fixed today" in pe)
ns["ARAYUZ_DILI"] = "tr"
# 9) istem kuralı yalnız bas-konus.py kodunda
ok("istem kuralı kodda (KESISIM_KURAL tr+en), yalnız Kesişim açıkken eklenir", set(ns["KESISIM_KURAL"]) == {"tr", "en"} and "Çapraz kontrol (Kesişim)" in ns["KESISIM_KURAL"]["tr"]
   and re.search(r'if "kesisim_sayfa_veri" in globals\(\) and gelistirici_mi\(\) and not gizli_acik\(\): t \+= KESISIM_KURAL', bs))
# 10) canlıda gitmeyen durum (12 Kasım, v0.233.0): tek Marvin toplantı rolünde + Roxie → eski bellek_kapsam toplantı dışında da "ortak" diyordu, dilim hiç kurulmuyordu. Düzeltme bellek.py'de; burada kaynak + davranış
yaz(sor=sor); LOG.clear()
bk = open(os.path.join(KOD, "aktarici", "bellek.py"), encoding="utf-8").read()
ok("kesisim, notlar/gun_plani ile tek çağrıda; ayrı kapı yok", 'dilimler=["notlar", "gun_plani", "kesisim"], soru=ms)' in bs and "nb = kesisim_tur_notu(nb)" in bs and "kesisim_tur_paketi" not in bs)
ok("bellek_kapsam toplantı sürüp sürmediğine bakar", 'tur["toplantida"] if "toplantida" in tur' in bk and "toplanti_var" in bk)
yaz(olay=[{"id": "00000004", "eylem": "tazi_kuyruga_alindi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")}]); q = paket()
ok("bugün düzeltilen sıfır olsa da Araştırılan satırı gider", "Araştırılan: 1" in q and "Bugün düzeltilen: 0" in q)
# 11) düzeltme özeti ~200 karakterde kesilir (110'da yarıda kalıyordu), bütçe 800
uz = "Atlas firması: kaynaklar ayrışıyor — " + "ayrıntı " * 12
yaz(bul=[{"id": f"{n:08x}", "ozet": uz + str(n), "kaynaklar": []} for n in range(1, 4)], olay=[{"id": f"{n:08x}", "eylem": "tazi_dosya_eklendi", "t": simdi.replace(tzinfo=None).isoformat(timespec="seconds")} for n in range(1, 4)]); q = paket()
ok("düzeltme özeti 110'dan uzun (≈130+ karakter tam), ≤ 800 bütçe, en çok 2 örnek", uz[:130].strip() in q and len(q) <= 800 and q.count("ayrışıyor") == 2)
print("\nKALAN: %d" % sum(hata)); sys.exit(1 if any(hata) else 0)
