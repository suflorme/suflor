#!/usr/bin/env python3
# Kişi modeli + tek bağlam kurucu (9 Kasım, mimari adım 1): aktarici/kisi-modeli.py — profil tek kaynak (kart = profil), öğrenilenler (yalnız eklenir, durumlar),
# baglam_paketi dilimleri/bütçe/önbellek, gizlilik süzgeci (gizli kip, gizli toplantı, deneme), Konuş isteminde öğrenilenler, toplantı oturumu bloğu. Süreç açılmaz, Claude yok.
# Nötr adlar (Atlas, Deniz); gerçek profil/not depoya girmez.   PYTHONDONTWRITEBYTECODE=1 python3 test/kisi-modeli.py      (kaldı → çıkış 1)
import datetime, json, os, re, secrets, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.realpath(tempfile.mkdtemp(prefix="kisimodeli-")); canli = os.path.join(T, "canli"); os.makedirs(canli)
hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
LOG = []; yazilan = []
def write(pairs):
    for y, m in pairs:
        with open(y, "a", encoding="utf-8") as f: f.write(m)
        yazilan.append(y)
simdi = datetime.datetime.now().astimezone().replace(hour=14, minute=5, second=0, microsecond=0)
def iso(dt): return dt.isoformat(timespec="seconds")
kd = os.path.join(T, "atlas.md"); open(kd, "w", encoding="utf-8").write("---\nad: Atlas\ngorunen_ad: Atlas\nhitap_bicimi: sen\nuslup_birebir: Kısa ve sıcak, espri hafif.\n---\nAdın Atlas.\n")
class SahteYapi:
    gizli = set()
    def bugun_veri(self, base, ad):
        return {"kendi": [{"metin": "Teklifi gönder", "gecikti": True, "kalan_gun": -2}, {"metin": "Bütçeyi kapat", "kalan_gun": 0}, {"metin": "Raporu oku", "kalan_gun": 5}, {"metin": "Eski iş", "geride": True}],
                "baskalari": [{"kim": "Deniz", "metin": "x"}], "teyit": [1, 2]}
    def gizli_mi(self, base, dosya): return dosya in self.gizli
yapi = SahteYapi()
AYAR = {"ad": "Deniz T", "alan": "Deneme", "uygulama": T, "kisilik": kd, "calisma_saatleri": "09:00-18:00"}
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "secrets": secrets, "print": lambda *a, **k: LOG.append(" ".join(map(str, a))),
      "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": canli, "LOCK": threading.Lock(), "write": write, "TOP": [False], "KONUS": {"soru": None}, "AYAR": AYAR, "_KS": {},
      "_ONARA": {"kilit": threading.Lock()}, "_onara_mod": lambda: None, "GIZLI": {"acik": False}, "_yapi_mod": lambda: yapi, "_DENEME_AD": re.compile(r"(?i)deneme|test"),
      "TAKVIM_TAM": {}, "SON": [], "_zaman": lambda s: datetime.datetime.fromisoformat(s)}
ns["gizli_acik"] = lambda: ns["GIZLI"]["acik"]; ns["toplanti_var"] = lambda: ns["TOP"][0]
def notlar_oku():  # notlar.py'deki okuyucunun aynısı (silme satırı dahil)
    ls, sil = [], set()
    try:
        for l in open(os.path.join(canli, "notlar.jsonl"), encoding="utf-8"):
            o = json.loads(l)
            if o.get("sil"): sil.add(o["sil"])
            elif o.get("id") and o.get("metin"): ls.append(o)
    except OSError: pass
    return [o for o in ls if o["id"] not in sil]
ns["_notlar_oku"] = notlar_oku; ns["gun_devir_oku"] = lambda s=None: ns["DEVIR"]; ns["DEVIR"] = []
src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
exec(open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read(), ns); exec(src[src.index("KONUS_ISTEM = {"):src.index("# --- Hızlı bilgi")], ns)
exec(open(os.path.join(KOD, "aktarici", "bellek.py"), encoding="utf-8").read(), ns)
exec(open(os.path.join(KOD, "aktarici", "kisi-modeli.py"), encoding="utf-8").read(), ns)
rel = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read(); tsh = open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read()
ok("relay.py bölümü bellek'ten sonra yükler; teshis KOD_DOSYALARI'nda; bellek.py kendisi yüklemez", rel.index('bolum("bellek")') < rel.index('bolum("kisi-modeli")') < rel.index('bolum("bas-konus")') and '"kisi-modeli.py"' in tsh and 'bolum("kisi-modeli")' not in open(os.path.join(KOD, "aktarici", "bellek.py"), encoding="utf-8").read())
bp, kaynak = ns["baglam_paketi"], open(os.path.join(KOD, "aktarici", "kisi-modeli.py"), encoding="utf-8").read()
ok("bölüm dosyasında '_' ile başlayan dosya yok, yeni depo yok (jsonl yalnız ogrenilen)", "ogrenilen.jsonl" in kaynak and not any(f.startswith("_") for f in os.listdir(os.path.join(KOD, "aktarici"))))

# --- 1) profil: tek kaynak ------------------------------------------------------------------------------------------------------------------
vars_yol = os.path.join(T, "profil.md")
ok("profil yolu: ayar kisilik_bellek yokken <uygulama>/profil.md", ns["profil_yol"]() == vars_yol and not ns["profil_var"]())
ok("profil yok: kart yok (kullanici_karti None), kart_istem boş, pakette yalnız ayardaki ad", ns["kullanici_karti"]() is None and ns["kart_istem"]() == "" and "Ad: Deniz T" in bp("brifing", dilimler=["profil"]))
yol, yeni = ns["profil_kur"]()
ok("profil_kur: yoksa kurar (ad/alan/saat), 0600, ikinci çağrıda dokunmaz", yeni and yol == vars_yol and os.stat(yol).st_mode & 0o777 == 0o600 and "Ad: Deniz T" in open(yol).read() and "09:00-18:00" in open(yol).read() and ns["profil_kur"]() == (yol, False))
ok("profil kurulunca kart = profil: kullanici_karti ve kart_istem aynı dosyayı okur", "Ad: Deniz T" in (ns["kullanici_karti"]() or "") and "[Kullanıcı kartı" in ns["kart_istem"]())
open(vars_yol, "w", encoding="utf-8").write("# Profil\n## Kim\n- Deniz, ürün sorumlusu. [kendisi]\n## Yalnız Atlas\n- OZEL-SIR\n## Tercih\n- Kısa cevap sever.\n")
os.utime(vars_yol, (time.time() + 5, time.time() + 5))
p = bp("brifing", dilimler=["profil"])
ok("profil dosyası değişince hem kart hem paket yenisini görür; 'Yalnız' bölümü pakete girmez", "ürün sorumlusu" in p and "Kısa cevap" in p and "OZEL-SIR" not in p and "ürün sorumlusu" in ns["kart_istem"]())
alt = os.path.join(T, "eski-kart.md"); open(alt, "w", encoding="utf-8").write("## Eski kart\n- ESKI-KART-ISARET\n"); AYAR["kisilik_bellek"] = alt
ok("ayar kisilik_bellek varsa o dosya profildir (kopyalanmaz); profil.md okunmaz", ns["profil_yol"]() == alt and "ESKI-KART-ISARET" in bp("brifing", dilimler=["profil"]) and "ürün sorumlusu" not in bp("brifing", dilimler=["profil"]))
del AYAR["kisilik_bellek"]; os.utime(vars_yol, (time.time() + 9, time.time() + 9))
ok("konus_gecmis varsayılanı profil varlığına bağlı", ns["konus_gecmis_acik"]())
yas = "# P\n" + "\n".join(f"- satır {i} " + "x" * 80 for i in range(100)); open(vars_yol, "w", encoding="utf-8").write(yas); os.utime(vars_yol, (time.time() + 12, time.time() + 12))
pp = bp("brifing", dilimler=["profil"]); ok("uzun profil amaca göre satır sınırında kesilir (brifing ≤ 1200) ve kapanış etiketi korunur", len(pp) <= 1200 and pp.rstrip().endswith("[/Kullanıcı profili]") and "…" in pp)
ok("toplantı amacında profil ≤ 3000", len(bp("toplanti", dilimler=["profil"])) <= 3000)
open(vars_yol, "w", encoding="utf-8").write("# Profil\n## Kim\n- Deniz, ürün sorumlusu. [kendisi]\n## Yalnız Atlas\n- OZEL-SIR\n## Tercih\n- Kısa cevap sever.\n"); os.utime(vars_yol, (time.time() + 15, time.time() + 15))

# --- 2) öğrenilenler ----------------------------------------------------------------------------------------------------------------------
ogy = os.path.join(T, "ogrenilen.jsonl")
ok("öğrenilenler boşken liste boş, paket dilimi boş", ns["ogrenilenler"]() == [] and bp("konus", dilimler=["ogrenilen"]) == "")
a = ns["ogren_ekle"]("Sabah toplantılarını sevmiyor", "konuşma 5 Kasım"); b = ns["ogren_ekle"]("Cuma günleri uzaktan çalışır", "not 7 Kasım", "onayli"); a2 = ns["ogren_ekle"]("sabah toplantılarını sevmiyor", "başka")
ok("ogren_ekle: id döner, aynı metin tekrar eklenmez, dosya 0600", a and b and a == a2 and len(open(ogy).read().splitlines()) == 2 and os.stat(ogy).st_mode & 0o777 == 0o600)
ok("ogren_ekle: boş metin / geçersiz durum / gecersiz ile ekleme reddedilir", ns["ogren_ekle"]("", "x") is None and ns["ogren_ekle"]("abc", "x", "yok") is None and ns["ogren_ekle"]("abc", "x", "gecersiz") is None)
l = ns["ogrenilenler"](); ok("ogrenilenler: onaylı önce, her kayıtta kaynak+tarih+durum", [k["id"] for k in l] == [b, a] and all(k.get("kaynak") and k.get("tarih") and k["durum"] in ("otomatik", "onayli") for k in l))
ns["ogren_durum"](a, "gecersiz"); sat0 = len(open(ogy).read().splitlines())
ok("ogren_durum gecersiz: listeden düşer ama dosyada silinmez (yalnız eklenir)", [k["id"] for k in ns["ogrenilenler"]()] == [b] and sat0 == 3 and a in open(ogy).read() and "Sabah toplantılarını" in open(ogy).read())
ns["ogren_durum"](a, "onayli"); ok("durum geri alınabilir (geçersiz → onaylı), bilinmeyen id/durum False", [k["id"] for k in ns["ogrenilenler"]()][:2] == [b, a] or {k["id"] for k in ns["ogrenilenler"]()} == {a, b}); ok("bilinmeyen id ya da durum reddedilir", ns["ogren_durum"]("yok", "onayli") is False and ns["ogren_durum"](a, "yok") is False)
ok("ogrenilenler(en_cok) sınırlar", len(ns["ogrenilenler"](1)) == 1)
ns["GIZLI"]["acik"] = True; ok("gizli kipte ogren_ekle yazmaz", ns["ogren_ekle"]("gizli bilgi", "x") is None and "gizli bilgi" not in open(ogy).read()); ns["GIZLI"]["acik"] = False
op = bp("konus", dilimler=["ogrenilen"]); ok("paket: öğrenilenler dilimi kaynaklı, tarihli, onaylı işaretli", "Sabah toplantılarını sevmiyor (konuşma 5 Kasım" in op and "onaylı" in op and "[/Öğrenilenler]" in op)

# --- 3) Konuş isteminde öğrenilenler ve değişim damgası -----------------------------------------------------------------------------------
ist = ns["konus_istem"]()
ok("Konuş istemi: kart ve öğrenilenler (sabit istemde), kural cümlesi, 'Yalnız' bölümü yok", "[Kullanıcı kartı" in ist and "[Öğrenilenler" in ist and ist.index("[Kullanıcı kartı") < ist.index("[Öğrenilenler") and "karşı tarafa okunan cevapta kullanma" in ist and "OZEL-SIR" not in ist)
d0 = ns["kart_damga"](); ns["ogren_ekle"]("Rapor özetlerini madde madde ister", "konuşma 8 Kasım"); ok("öğrenilen eklenince kart_damga değişir (Konuş süreci yenilenir)", ns["kart_damga"]() != d0)

# --- 4) olaylar ve paket dilimleri ---------------------------------------------------------------------------------------------------------
bugun0 = simdi.replace(hour=0, minute=0)
ns["TAKVIM_TAM"].update({"a": {"baslik": "Haftalık görüşme", "baslangic": iso(simdi + datetime.timedelta(hours=1)), "bitis": iso(simdi + datetime.timedelta(hours=2))},
                         "b": {"baslik": "Yarınki sunum", "baslangic": iso(bugun0 + datetime.timedelta(days=1, hours=10)), "bitis": iso(bugun0 + datetime.timedelta(days=1, hours=11))},
                         "c": {"baslik": "Uzak toplantı", "baslangic": iso(bugun0 + datetime.timedelta(days=5, hours=10)), "bitis": iso(bugun0 + datetime.timedelta(days=5, hours=11))}})
pk = bp("toplanti", dilimler=["bugun"], simdi=simdi)
ok("bugun: tarih/saat, bugün+yarın takvimi (uzak olay yok), bugün/geciken işler", "14:05" in pk and "Haftalık görüşme" in pk and "Yarınki sunum" in pk and "Uzak toplantı" not in pk and "Teklifi gönder" in pk and "gecikti 2" in pk and "Bütçeyi kapat" in pk and "Raporu oku" not in pk)
pk = bp("toplanti", dilimler=["isler"], simdi=simdi)
ok("isler: diğer açık işler, teyit bekleyen, başkasında bekleyen; geride kalan yok", "Raporu oku" in pk and "Teyidini bekleyen karar: 2" in pk and "Başkalarında bekleyen" in pk and "Eski iş" not in pk and "Teklifi gönder" not in pk)
nd = os.path.join(canli, "notlar.jsonl")
def nota(i, metin, gun_once): open(nd, "a", encoding="utf-8").write(json.dumps({"id": i, "at": iso(datetime.datetime.now() - datetime.timedelta(days=gun_once, minutes=1)), "metin": metin}) + "\n")
nota("n1", "Tedarikçi fiyat listesini cuma bekle", 0); nota("n2", "Annemi pazar günü ara", 1); nota("n3", "Eski ve unutulmuş not", 9)
pk = bp("konus", dilimler=["notlar"]); ok("notlar: son 3 gün (eski not yok), kullanıcıya özel uyarısı", "Tedarikçi fiyat" in pk and "Annemi pazar" in pk and "Eski ve unutulmuş" not in pk and "karşı tarafa okunan cevapta kullanma" in pk)
pk = bp("brifing", dilimler=["notlar"], soru="Tedarikçi toplantısı"); ok("brifing/talimat gibi amaçlarda yalnız soruyla ilgili notlar", "Tedarikçi fiyat" in pk and "Annemi" not in pk)
pk = bp("konus", dilimler=["notlar"], soru="annemi ne zaman arayacaktım"); ok("Konuş'ta soruyla ilgili not öne alınır (hepsi gelir)", pk.index("Annemi") < pk.index("Tedarikçi"))
open(nd, "a", encoding="utf-8").write(json.dumps({"sil": "n1"}) + "\n"); ok("silinen not pakete girmez", "Tedarikçi" not in bp("konus", dilimler=["notlar"]))
gk = os.path.join(canli, "konus-gecmis.jsonl")
def gec(soru, sesli, **ek): open(gk, "a", encoding="utf-8").write(json.dumps(dict({"at": iso(datetime.datetime.now()), "soru": soru, "sesli": sesli}, **ek)) + "\n")
gec("Yarın ne var?", "Sunum var."); gec("Gizli toplantı sorusu", "gizli cevap", gizli=True); gec("Toplantı içi soru", "toplantı cevabı", toplanti="2026-11-09 10-00 Haftalık.md")
pk = bp("konus", dilimler=["son_konusma"]); ok("son_konusma: toplantı dışı sorular; gizli ve toplantı içi satır yok", "Yarın ne var?" in pk and "Gizli toplantı" not in pk and "Toplantı içi" not in pk)
ns["DEVIR"] = [{"metin": "Haftalık görüşme: karar 2, iş 3."}]; ok("gun_devri: bugünkü devir metni", "Haftalık görüşme: karar 2" in bp("toplanti", dilimler=["gun_devri"]))
ns["SON"].extend([{"baslik": "Eski planlama", "dosya": "2026-11-08 Planlama.md", "at": "2026-11-08T10:00:00", "cikti": {"karar": 3}}, {"baslik": "Gizli görüşme", "dosya": "GIZLI.md", "at": "2026-11-08T12:00:00"},
                  {"baslik": "Deneme toplantısı", "dosya": "d.md", "at": "2026-11-09T09:00:00"}]); yapi.gizli.add("GIZLI.md")
pk = bp("konus", dilimler=["toplantilar"]); ok("toplantilar: gizli toplantı ve deneme yok", "Eski planlama" in pk and "karar 3" in pk and "Gizli görüşme" not in pk and "Deneme" not in pk)
pk = bp("toplanti", dilimler=["kimlik"]); ok("kimlik: kişilik adı, sen hitabı, üslup; kartlar toplantı kurallarına göre", "Adın Atlas" in pk and "«sen»" in pk and "Kısa ve sıcak" in pk and "kartlar toplantı kurallarındaki biçimde" in pk)
ok("kişilik yokken kimlik 'Suflor'", "Adın Suflor" in (lambda: (AYAR.update(kisilik=""), ns["_KIS_D"].clear(), bp("toplanti", dilimler=["kimlik"]), AYAR.update(kisilik=kd), ns["_KIS_D"].clear())[2])())

# --- 5) amaç varsayılanları ve bütçe --------------------------------------------------------------------------------------------------------
for amac in ("konus", "toplanti", "brifing", "talimat", "kayit", "degerlendir"):
    pk = bp(amac, simdi=simdi); ok(f"amaç {amac}: boş değil, bütçe içinde ({len(pk)} karakter)", pk and len(pk) <= ns["KM_AMAC"][amac][1])
ok("amaç kümeleri: talimat/kayit yalnız profil+öğrenilen; toplantı kimlik+gün bağlamı", "[Bugün" not in bp("talimat", simdi=simdi) and "[Notlar" not in bp("kayit", simdi=simdi) and "[Asistan kimliği" in bp("toplanti", simdi=simdi) and "[Bugün" in bp("toplanti", simdi=simdi) and "[Asistan kimliği" not in bp("konus", simdi=simdi))
ok("en_cok_kr toplam bütçeyi ezer", len(bp("toplanti", en_cok_kr=900, simdi=simdi)) <= 900 and len(bp("toplanti", en_cok_kr=900, simdi=simdi)) > 0)
ok("dilimler sırası KM_ONCELIK'e göre, bilinmeyen dilim yok sayılır", (lambda t: t.index("[Kullanıcı profili") < t.index("[Bugün"))(bp("konus", dilimler=["bugun", "profil", "yok"], simdi=simdi)))

# --- 6) gizlilik süzgeci: tek yerde ---------------------------------------------------------------------------------------------------------
ns["GIZLI"]["acik"] = True; pk = bp("toplanti", simdi=simdi)
ok("gizli kip: yalnız kimlik/profil/öğrenilenler; bugün, işler, notlar, konuşma, devir, toplantılar yok", "[Asistan kimliği" in pk and "[Kullanıcı profili" in pk and "[Öğrenilenler" in pk and not any(x in pk for x in ("[Bugün", "[Açık işler", "[Notlar", "Haftalık görüşme", "Yarın ne var", "Eski planlama")))
ok("gizli kipte açıkça istenen içerik dilimleri de dönmez", bp("konus", dilimler=["notlar", "son_konusma", "gun_devri", "toplantilar", "bugun", "isler"], simdi=simdi) == "")
ns["GIZLI"]["acik"] = False
ok("gizli kip kapanınca içerik geri gelir", "[Bugün" in bp("toplanti", simdi=simdi))

# --- 7) önbellek ----------------------------------------------------------------------------------------------------------------------------
say = {"n": 0}; asil = ns["_km_notlar"]
def say_notlar(): say["n"] += 1; return asil()
ns["_km_notlar"] = say_notlar
bp("konus", dilimler=["notlar"]); n1 = say["n"]; bp("konus", dilimler=["notlar"]); bp("konus", dilimler=["notlar"])
ok("önbellek: dosya değişmedikçe not dilimi yeniden kurulmaz", say["n"] == n1 and n1 >= 1)
nota("n4", "Yeni eklenen not", 0); os.utime(nd, (time.time() + 20, time.time() + 20)); bp("konus", dilimler=["notlar"])
ok("önbellek: dosya değişince yeniden kurulur ve yeni not görünür", say["n"] == n1 + 1 and "Yeni eklenen not" in bp("konus", dilimler=["notlar"]))
ns["_km_notlar"] = asil
t0 = time.time()
for _ in range(200): bp("konus", dilimler=["profil", "ogrenilen", "notlar"])
ok(f"sıcak paket ≤ 2 ms (200 çağrı {1000 * (time.time() - t0):.0f} ms; Konuş ilk ses gecikmesi)", (time.time() - t0) / 200 < 0.002)

# --- 8) toplantı oturumu bloğu --------------------------------------------------------------------------------------------------------------
tsrc = open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read()
tns = dict(ns); tns["_gd_deneme"] = lambda konu=None, *a, **k: bool(konu and "deneme" in konu.lower())
exec(tsrc[tsrc.index("def topo_kisi_blogu"):tsrc.index("def toplanti_oturum_ac")], tns)
b1 = tns["topo_kisi_blogu"]("Haftalık görüşme", True); b2 = tns["topo_kisi_blogu"]("Haftalık görüşme", False); b3 = tns["topo_kisi_blogu"]("Deneme toplantısı", True)
ok("toplantı oturumu yeni: kimlik + profil + öğrenilenler + bugün/işler/devir", all(x in b1 for x in ("[Asistan kimliği", "[Kullanıcı profili", "[Öğrenilenler", "[Bugün", "[Açık işler", "[Bugünkü toplantılardan devir")) and b1.startswith("\n\n"))
ok("kaldığı yerden açılış (--resume): yalnız kararlı kısım (kimlik/profil/öğrenilen), zamana bağlı gün bağlamı yok", "[Asistan kimliği" in b2 and "[Bugün" not in b2 and "[Notlar" not in b2)
ok("deneme toplantısında gerçek iş/not/devir yok (kimlik ve profil var)", "[Asistan kimliği" in b3 and "[Açık işler" not in b3 and "[Notlar" not in b3 and "devir" not in b3)
d2 = {"print": print}; exec(tsrc[tsrc.index("def topo_kisi_blogu"):tsrc.index("def toplanti_oturum_ac")], d2); ok("paket yokken (bölüm yüklü değil) boş döner", d2["topo_kisi_blogu"]("x", True) == "")

# --- 9) eylem_model: amaç verilince istemin başına paket (talimat düzeltme, kayıt eylemi, e-posta değerlendirmesi ortak kapısı) -------------------------------
esrc = open(os.path.join(KOD, "aktarici", "eylem-menu.py"), encoding="utf-8").read(); gelen = []
class Beyin:
    def secim(self, a, i): return {"tur": "openai"}
    def yedek_var(self, a, s): return False
ens = dict(ns); ens.update(BEYIN=Beyin(), claude_yolu=lambda: None, BRIFING_APP="/yok", beyin_tek=lambda i, sec, istem, **k: (gelen.append(istem) or ("tamam", {"x": 1})), EYLEM_ZAMAN_SN=5)
exec(esrc[esrc.index("def eylem_model"):esrc.index("def _kem_id")], ens)
ens["eylem_model"]("ISTEM-GOVDE"); ens["eylem_model"]("ISTEM-GOVDE", amac="kayit"); ens["eylem_model"]("ISTEM-GOVDE", amac="talimat", soru="x")
ok("eylem_model: amaçsız çağrı istemi değiştirmez; kayit/talimat amacında başına profil+öğrenilenler paketi gelir, gövde sonda", gelen[0] == "ISTEM-GOVDE" and gelen[1].endswith("\nISTEM-GOVDE") and "[Kullanıcı profili" in gelen[1] and "[Bugün" not in gelen[1] and "[Öğrenilenler" in gelen[2])
gelen.clear(); ens["eylem_model"]("ISTEM-GOVDE", amac="kayit", maske=lambda t: t.replace("ürün sorumlusu", "[MASKE]")); ok("eylem_model: çağıranın maskesi pakete uygulanır (e-posta için)", "[MASKE]" in gelen[0] and "ürün sorumlusu" not in gelen[0])
ns["GIZLI"]["acik"] = True; gelen.clear(); ens["eylem_model"]("ISTEM-GOVDE", amac="kayit"); ns["GIZLI"]["acik"] = False
ok("gizli kipte paket yine yalnız profil/öğrenilen (içerik yok)", "[Bugün" not in gelen[0] and "[Notlar" not in gelen[0])

print(f"\n{sum(1 for h in hata if not h)} geçti, {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
