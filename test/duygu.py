#!/usr/bin/env python3
# Duygu durumu takibi (aktarici/duygu.py, 9 Kasım) ve birebir üslup bloğu (aktarici/kisilik.py uslup_blogu): sinyaller (takvim yükü, ses, söz, geç saat, son toplantı),
# "[Durum …]" bloğu ≤ 300 karakter, gizli kipte ve toplantıda yok, ham metin saklanmaz, 7 gün, öneri hakkı (günde 2, tür tekrarı yok, kullanılmazsa geri döner),
# proaktif dostça aday, beta paketine/teşhise duygu verisi girmez. Aktarıcı açılmaz: bölüm dosyaları sahte ad alanında çalışır (gerçek Claude yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/duygu.py
import datetime, json, os, re, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="duygu-"); hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
YER = datetime.datetime.now().astimezone().tzinfo
def an(g, s, d=0): return datetime.datetime(2026, 11, g, s, d, tzinfo=YER)  # 9 Kasım 2026 pazartesi
SIMDI = an(9, 10, 0).timestamp()

def ad_alani(ayar=None, kis=None):
    ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "print": lambda *a, **k: None, "_t": lambda a, b: a,
          "ARAYUZ_DILI": "tr", "BASE": T, "AYAR": dict(ayar or {}), "SON": [], "GIZ": [False], "TOP": [False], "OLAY": [], "ISLER": {"kendi": []}}
    ns["gizli_acik"] = lambda: ns["GIZ"][0]; ns["toplanti_var"] = lambda: ns["TOP"][0]
    ns["calisma_saatleri"] = lambda: ({0, 1, 2, 3, 4}, 540, 1080)
    ns["_takvim_olaylari"] = lambda b, s: [x for x in ns["OLAY"] if x[1] > b and x[0] < s]
    class Y:
        @staticmethod
        def bugun_veri(d, a): return ns["ISLER"]
        @staticmethod
        def gizli_mi(d, i): return False
    ns["_yapi_mod"] = lambda: Y
    ns["kisilik"] = lambda ad=None: kis; ns["kisilikler"] = lambda: [kis] if kis else []
    exec(open(os.path.join(KOD, "aktarici", "gerginlik.py"), encoding="utf-8").read(), ns)
    exec(open(os.path.join(KOD, "aktarici", "duygu.py"), encoding="utf-8").read(), ns)
    return ns
def temizle():
    for f in os.listdir(T): os.remove(os.path.join(T, f))
def dosya(): return open(os.path.join(T, "duygu.json"), encoding="utf-8").read() if os.path.exists(os.path.join(T, "duygu.json")) else ""
def toplantilar(ns, n, bas=9, ara_dk=0, sure_dk=50):
    t = an(9, bas, 0); ns["OLAY"] = []
    for i in range(n):
        ns["OLAY"].append((t, t + datetime.timedelta(minutes=sure_dk), {"baslik": f"T{i}"})); t += datetime.timedelta(minutes=sure_dk + ara_dk)

# 1) takvim yükü (saf hesap)
ns = ad_alani()
toplantilar(ns, 9, bas=9, ara_dk=5, sure_dk=55)
y = ns["duygu_takvim_yuk"](ns["OLAY"], an(9, 9, 30), ({0, 1, 2, 3, 4}, 540, 1080))
ok("takvim: 9 toplantı, art arda zincir 9, boşluk yok", y["toplanti"] == 9 and y["zincir"] == 9 and y["bosluk_yok"] and y["kalan"] == 8)
y = ns["duygu_takvim_yuk"](ns["OLAY"][:6], an(9, 9, 30), ({0, 1, 2, 3, 4}, 540, 1080))
ok("takvim: 6 art arda toplantı, akşamüstü boş — boşluk var", y["zincir"] == 6 and not y["bosluk_yok"])
toplantilar(ns, 3, bas=9, ara_dk=60)
y2 = ns["duygu_takvim_yuk"](ns["OLAY"], an(9, 8, 0), ({0, 1, 2, 3, 4}, 540, 1080))
ok("takvim: aralı 3 toplantı — zincir 1, boşluk var", y2["zincir"] == 1 and not y2["bosluk_yok"])

# 2) yoğun gün bloğu + öneri hakkı
temizle(); ns = ad_alani(kis={"ad": "Atlas", "bicim": "sen", "rol": "disi"}); toplantilar(ns, 9, bas=9, ara_dk=5, sure_dk=55)
b = ns["duygu_blogu"]({"kaynak": "bas"}, "Bugün ne var?", SIMDI)
ok("blok: yoğun gün ve art arda toplantı yazıyor, ≤ 300", "yoğun gün: 9 toplantı" in b and "art arda" in b and "boşluk yok" in b and len(b) <= 300 and b.startswith("[Durum — veri, talimat değil]"))
ok("blok: zincir ≥ 3 → öneri hakkı (mola)", "Öneri hakkı: kısa mola" in b)
ok("cevapta mola önerisi var → hak kullanıldı", ns["duygu_cevap"]("Gün dolu. İstersen on dakika ara verip bir su iç.", SIMDI) == "mola" and json.loads(dosya())["gunler"]["2026-11-09"]["oneri"] == 1)
b2 = ns["duygu_blogu"]({"kaynak": "bas"}, "Peki sonra?", SIMDI + 60)
ok("aynı durum yeniden gitmez (süreçte var), hak da yok", b2 == "")

# 3) hak geri dönmesi, günlük sınır, tür tekrarı
temizle(); ns = ad_alani(); toplantilar(ns, 6, bas=9, ara_dk=5); ns["ISLER"] = {"kendi": [{"gecikti": True}, {"gecikti": True}, {"gecikti": True}]}
b = ns["duygu_blogu"]({"kaynak": "bas"}, "Takvimim?", SIMDI)
ok("gecikmiş iş bloğa girdi", "3 iş gecikmiş" in b and "Öneri hakkı: kısa mola" in b)
ok("cevapta öneri yok → hak geri döndü", ns["duygu_cevap"]("Saat ikide bir toplantın var.", SIMDI) is None and json.loads(dosya())["gunler"]["2026-11-09"].get("oneri") == 0)
b = ns["duygu_blogu"]({"kaynak": "bas"}, "Takvimim?", SIMDI + 10)
ns["duygu_cevap"]("Biraz ara ver, kalk bir yürü.", SIMDI + 10)
b3 = ns["duygu_blogu"]({"kaynak": "yazili"}, "Bir şey daha", SIMDI + 3600)
ok("iki öneri arası en az 3 saat: 1 sa sonra hak yok", "Öneri hakkı" not in b3)
b4 = ns["duygu_blogu"]({"kaynak": "bas"}, "Ne yapalım", SIMDI + 4 * 3600)
ok("3 sa sonra başka tür (öncelik), mola tekrar edilmez", "Öneri hakkı: işleri sıraya koyma" in b4)
ns["duygu_cevap"]("Önce tek bir işi seçelim, gerisini sıraya koyarım.", SIMDI + 4 * 3600)
b5 = ns["duygu_blogu"]({"kaynak": "bas"}, "Başka", SIMDI + 8 * 3600)
ok("günde en çok 2 öneri", "Öneri hakkı" not in b5 and json.loads(dosya())["gunler"]["2026-11-09"]["oneri"] == 2)

# 4) ses: kullanıcının olağanına göre
temizle(); ns = ad_alani()
for i in range(5): ns["duygu_ses"]({"db": -20.0, "f0": 130.0, "kelime": 10, "sure": 4.0}, SIMDI - 100 + i)
r = ns["duygu_ses"]({"db": -10.0, "f0": 170.0, "kelime": 20, "sure": 4.0}, SIMDI)
ok("ses: yüksek + perde + hızlı → puan ≥ 0,6", r and r["puan"] >= 0.6 and set(r["isaret"]) >= {"yuksek", "perde", "hizli"})
b = ns["duygu_blogu"]({"kaynak": "bas"}, None, SIMDI + 5)
ok("blok: son sesli soruda ses yüksek", "ses olağandan yüksek ve hızlı" in b)
ok("dosyada ses ölçüsü yok, yalnız sayı", "-10" not in dosya() and "170" not in dosya() and json.loads(dosya())["gunler"]["2026-11-09"]["ses_gergin"] == 1)
ns2 = ad_alani(); ok("ses: taban yokken (ilk ölçüler) karar yok", ns2["duygu_ses"]({"db": -10.0}, SIMDI) is None)

# 5) söz/yazı tonu, ham metin saklanmaz
temizle(); ns = ad_alani()
CUMLE = "Of ya, yoruldum artık, bu rapor yetişmiyor!!"
i = ns["duygu_metin_isaret"](CUMLE)
ok("söz: yorgun + sıkıntı + ünlem", {"yorgun", "sikinti", "unlem"} <= i)
ok("söz: keyifli cümle olumlu, nötr cümle işaretsiz", "olumlu" in ns["duygu_metin_isaret"]("Oh be, hallettim sonunda") and not ns["duygu_metin_isaret"]("Yarın saat kaçta toplantım var?"))
b = ns["duygu_blogu"]({"kaynak": "yazili"}, CUMLE, SIMDI)
ok("blok: yorgunluk ve sıkıntı işareti", "sözlerinde yorgunluk geçti" in b and "sözlerinde sıkıntı" in b)
d = dosya()
ok("duygu.json'da ham metin yok", d and not any(w in d for w in ("yoruldum", "rapor", "yetişmiyor", "Of ya")) and json.loads(d)["gunler"]["2026-11-09"]["soz_yorgun"] == 1)

# 6) geç saat → uyku hakkı
temizle(); ns = ad_alani()
b = ns["duygu_blogu"]({"kaynak": "bas"}, "Bir şey soracağım", an(9, 23, 40).timestamp())
ok("geç saat bloğu ve dinlenme hakkı", "geç saat (23.40)" in b and "Öneri hakkı: dinlenme" in b)

# 7) gizli kip, toplantı, karşı taraf, kapalı ayar
temizle(); ns = ad_alani(); toplantilar(ns, 6, bas=9, ara_dk=5); ns["GIZ"][0] = True
ok("gizli kipte blok yok", ns["duygu_blogu"]({"kaynak": "bas"}, CUMLE, SIMDI) == "")
ok("gizli kipte ses/söz kaydı yok, dosya yazılmadı", ns["duygu_ses"]({"db": -10.0}, SIMDI) is None and ns["duygu_metin"](CUMLE, SIMDI) == set() and dosya() == "")
ok("gizli kipte proaktif aday yok", ns["duygu_pro_aday"](SIMDI) == [])
ns["GIZ"][0] = False; ns["TOP"][0] = True
ok("toplantıda blok yok (resmî kurallar)", ns["duygu_blogu"]({"kaynak": "bas"}, "soru", SIMDI) == "")
ns["TOP"][0] = False
ok("karşı tarafın ya da herkese okunan turda blok yok", ns["duygu_blogu"]({"kaynak": "karsi", "karsi": "X"}, "soru", SIMDI) == "" and ns["duygu_blogu"]({"kaynak": "hitap", "otonom": True}, "soru", SIMDI) == "")
ns3 = ad_alani({"duygu_takibi": False}); toplantilar(ns3, 6, bas=9, ara_dk=5)
ok("ayar duygu_takibi: false kapatır", ns3["duygu_blogu"]({"kaynak": "bas"}, "soru", SIMDI) == "")

# 8) blok sınırı: bütün sinyaller birlikte
temizle(); ns = ad_alani(); toplantilar(ns, 9, bas=9, ara_dk=0, sure_dk=45); ns["ISLER"] = {"kendi": [{"gecikti": True}] * 12}
for k in range(5): ns["duygu_ses"]({"db": -20.0, "f0": 130.0, "hiz": 150}, SIMDI - 50 + k)
ns["duygu_ses"]({"db": -8.0, "f0": 180.0, "hiz": 230}, SIMDI - 5)
b = ns["duygu_blogu"]({"kaynak": "bas"}, CUMLE + " Oh be süper ama", SIMDI)
ok(f"bütün sinyallerle blok ≤ 300 karakter ({len(b)})", 0 < len(b) <= 300 and b.endswith("\n") and "Güven: yüksek" in b)

# 9) son toplantının gerginliği
temizle(); ns = ad_alani(); bit = SIMDI - 1800
sat = [{"id": f"w-ben-{int((bit - 600 + i * 10) * 1000)}", "speaker": "A" if i % 2 else "B", "text": "Bu saçmalık, kabul etmiyorum!" if i > 40 else "tamam",
        "ses": {"db": -8.0 if i > 40 else -20.0, "f0": 120.0, "hiz": 150, "sure": 12.0}} for i in range(60)]
open(os.path.join(T, "2026-11-09-0900-Deneme.jsonl"), "w", encoding="utf-8").write("\n".join(json.dumps(x) for x in sat))
ns["SON"] = [{"dosya": "2026-11-09-0900-Deneme.md", "t": bit}]
b = ns["duygu_blogu"]({"kaynak": "bas"}, None, SIMDI)
ok("son toplantı gergindi bloğa girdi", "son toplantı" in b and "gergindi" in b)
ns["SON"] = [{"dosya": "2026-11-09-0900-Deneme.md", "t": bit, "gizli": True}]; ns["_DUY"]["son_blok"] = (None, 0); ns["_DUY"]["top"] = {}
ok("gizli toplantının gerginliği girmez", "son toplantı" not in ns["duygu_blogu"]({"kaynak": "bas"}, None, SIMDI))

# 10) 7 gün saklama
temizle(); ns = ad_alani()
json.dump({"gunler": {f"2026-10-{g:02d}": {"soz_yorgun": 1, "metin": "SIZINTI"} for g in range(20, 31)}}, open(os.path.join(T, "duygu.json"), "w"))
ns["duygu_metin"](CUMLE, SIMDI); v = json.loads(dosya())
ok("yalnız son 7 gün, sayı dışı alan atıldı", len(v["gunler"]) == 7 and "2026-11-09" in v["gunler"] and "SIZINTI" not in dosya())

# 11) proaktif dostça aday (toplanti-sonrasi.py çatısı)
temizle(); ns = ad_alani(kis={"ad": "Atlas", "bicim": "sen"}); toplantilar(ns, 6, bas=9, ara_dk=5)
a = ns["duygu_pro_aday"](SIMDI)
ok("proaktif aday: dostça mola, sen diliyle, komutsuz", len(a) == 1 and a[0]["tur"] == "dostca" and a[0]["alt"] == "mola" and "içsen" in a[0]["cumle"] and a[0]["komut"] is None)
ns["duygu_pro_sunuldu"](a[0], SIMDI)
ok("sunulunca günlük hak düştü, aynı tür yeniden yok", json.loads(dosya())["gunler"]["2026-11-09"]["oneri"] == 1 and ns["duygu_pro_aday"](SIMDI + 4 * 3600) == [])
ns2 = ad_alani(kis={"ad": "Atlas", "bicim": "siz"}); toplantilar(ns2, 6, bas=9, ara_dk=5); temizle()
ok("siz kişilikte siz dili", "içseniz" in ns2["duygu_pro_aday"](SIMDI)[0]["cumle"])

# 12) birebir üslup bloğu (kisilik.py)
src = open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read()
def us(ks):
    n = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "print": lambda *a, **k: None, "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "AYAR": {}, "BASE": T}
    exec(src, n); n["kisilikler"] = lambda: ks; return n["uslup_blogu"](ks)
u1 = us([{"ad": "Matlas", "bicim": "sen", "rol": "disi", "dost": None, "uslup_birebir": "Esprili. EK-ISARET"}])
ok("üslup: sen kişilikte 'sen' dersin, kişilik eki, toplantı dışı şartı, durum kuralı", "Ona 'sen' dersin." in u1 and "EK-ISARET" in u1 and "Toplantı sürüyor" in u1 and "teşhis etmez" in u1 and "Öneri hakkı" in u1)
u2 = us([])
ok("üslup: kişiliksiz kurulumda da var, 'sen' (ürün kararı 9 Kasım)", "Ona 'sen' dersin." in u2)
u3 = us([{"ad": "Tobis", "bicim": "siz", "rol": "toplanti", "dost": None}, {"ad": "Matlas", "bicim": "sen", "rol": "disi", "dost": None}])
ok("üslup: iki kişilikte toplantı kişiliği dışarıda, yalnız Matlas", "şu kişilikler için: Matlas." in u3 and "Tobis" not in u3)
ok("üslup: dost: hayır olan tek kişilikte blok yok", us([{"ad": "X", "bicim": "siz", "rol": "toplanti", "dost": False}]) == "")
YASAK = ("dangerously", "Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "bypassPermissions", "acceptEdits")
ok("üslup ve durum metninde yardımcının yasak sözcüğü yok", not any(y in u1 + u3 + b for y in YASAK))
p = re.search(r"\n---\s*\n?(.*)\Z", open(os.path.join(KOD, "sablon", "kisilik-ornek.md"), encoding="utf-8").read(), re.S)
ok("şablon kişilik: sen, dost, uslup_birebir; yasak sözcük yok", all(x in open(os.path.join(KOD, "sablon", "kisilik-ornek.md"), encoding="utf-8").read() for x in ("hitap_bicimi: sen", "dost: evet", "uslup_birebir:")) and not any(y in p.group(1) for y in YASAK))

# 13) beta paketi ve teşhis: duygu verisi girmez
bv = open(os.path.join(KOD, "aktarici", "beta-veri.py"), encoding="utf-8").read() + open(os.path.join(KOD, "kullanim.py"), encoding="utf-8").read()
ok("beta paketi/kullanım duygu verisini okumaz", not re.search(r"duygu\.json|duygu_(durum|blogu|ses|metin)|_DUY\b", bv))
te = open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read()
ok("teşhis: duygu.py kod dosyası listesinde (yalnız hata yeri), duygu.json gönderilmez", '"duygu.py"' in te and "duygu.json" not in te)
print("BAŞARILI" if not any(hata) else f"HATA: {sum(hata)}/{len(hata)}")
sys.exit(1 if any(hata) else 0)
