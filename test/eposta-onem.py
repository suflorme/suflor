#!/usr/bin/env python3
# E-posta takibi, üç kova (S262, 9 Kasım; aktarici/eposta-takip.py): bekleyen (senden cevap bekleyen) · donus (dönüş beklediğin) · bilgi (yalnız sayı).
# Kurgu veri (gerçek kişi yok): CC'de kalan, > 5 alıcılı, yüksek hacimli tek yönlü gönderen → bilgi; karşılıklı yazışmalı doğrudan soru → bekleyen; istekli giden → donus,
# bilgi amaçlı giden → yok; 14 günden eski düşer; düzey siki/dengeli/genis; onemli_kisi/onemsiz_gonderen kalıcı; Claude'a yalnız ad/konu/özet gider; alıcı ham listesi + yardımcının bayrakları.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/eposta-onem.py      (kaldı → çıkış 1)
import collections, datetime, json, os, re, shutil, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
os.environ["SUFLOR_TEST_ET_DONGU_YOK"] = "1"
AT = "@"; A = lambda k, d="ornek.test": k + AT + d; BEN = A("ben")
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="etonem-")
SIMDI = datetime.datetime(2026, 11, 11, 12, 0).astimezone()  # çarşamba
def gun(g, saat=10): return (datetime.datetime(2026, 11, 11, saat, 0) - datetime.timedelta(days=g)).astimezone().isoformat()
CAGRI = []; KAYITLI = {}
class Beyin:
    tur = "claude-code"
    @staticmethod
    def secim(ayar, is_): return {"tur": Beyin.tur, "model": None}
MOD = {"hata": None}
def sahte_model(istem, amac=None, soru=None, maske=None):  # zincir bloklarını okur; kural: son satır "sen" → onay varsa donus_bekliyorsun; "açıklama" → baskasi_cevapladi; sözleşme → 3; onay → 2; yoksa bilgi
    CAGRI.append(istem)
    if MOD["hata"]: return None, MOD["hata"]
    out = []
    for blk in istem.rsplit("<veri>", 1)[1].split("</veri>")[0].split("[zincir ")[1:]:
        zid = blk.split("]", 1)[0]; sat = [l for l in blk.splitlines() if l.startswith("- ")]; son = sat[-1] if sat else ""; k = blk.casefold()
        if "açıklama" in k: d, a = "baskasi_cevapladi", 0
        elif "kahve" in k and " sen → " in son: d, a = "donus_bekliyorsun", 1  # düşük öncelikli dönüş (katlı satır)
        elif "ekstra" in k and " sen → " not in son: d, a = "senden_bekleniyor", 1  # düşük öncelikli gelen (sıkı düzeyde katlı satır)
        elif " sen → " in son: d, a = ("donus_bekliyorsun", 2) if "onay" in k else ("bilgi", 0)
        elif "özleşme" in k: d, a = "senden_bekleniyor", 3
        elif "onay" in k: d, a = "senden_bekleniyor", 2
        else: d, a = "bilgi", 0
        out.append({"id": zid, "durum": d, "aciliyet": a, "neden": f"Somut istek var ({d})"})
    return json.dumps(out), None
AYAR = {"soz_gece": False, "eposta_oku": True, "ad": "Deniz T", "eposta_adres": BEN, "eposta_claude_siralama": False}
def ayar_yaz(deg):  # relay'in ayar_yaz'ının yerine: bellekteki AYAR'a yazar, çağrıyı kaydeder
    for k, v in deg.items(): AYAR[k] = list(v); KAYITLI[k] = list(v)
    return {"ok": True}
NS = {"__name__": "et", "collections": collections, "re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "BASE": T, "AYAR": AYAR, "POSTA": {"iletiler": [], "durum": "ok"},
      "_t": lambda tr, en: tr, "ARAYUZ_DILI": "tr", "bildirim": lambda *a, **k: None, "seslendir": lambda m, **k: None, "toplanti_var": lambda: False, "aktif_dosya": lambda: None, "gizli_acik": lambda: False,
      "SOHBET": {"acik": False}, "BEYIN": Beyin, "eylem_model": sahte_model, "posta_vt_kisiler": lambda: [], "posta_govde_al": lambda ids, kar=None: {}, "posta_kullanici_sorusu": lambda: True,
      "_yapi_mod": lambda: None, "ayar_yaz": ayar_yaz}
exec(compile(open(os.path.join(KOD, "aktarici", "eposta-takip.py"), encoding="utf-8").read(), "eposta-takip.py", "exec"), NS)
N = lambda f: NS[f]
def g(id_, adres, konu, gn, ozet="", al=None, tur=None, sayi=None, ad="", **k):  # gelen
    x = {"id": id_, "t": gun(gn), "adres": adres, "konu": konu, "kutu": "imap://X/INBOX", "okundu": True, "gonderilen": False}
    if ozet: x["ozet"] = ozet
    if ad: x["ad"] = ad
    if al is not None: x.update(gelen_alici=al, gelen_tur=tur if tur is not None else [0] * len(al), alici_sayi=sayi if sayi is not None else len(al))
    return dict(x, **k)
def s(id_, alici, konu, gn, ozet=""): return {"id": id_, "t": gun(gn), "adres": BEN, "konu": konu, "kutu": "imap://X/Sent", "okundu": True, "gonderilen": True, "alici": alici, "ozet": ozet}
def kovalar(a): return ({o["id"] for o in a["bekleyen"]}, {o["id"] for o in a["donus"]})
POS = [
    s(90, [A("ayla")], "Eski yazışma", 40),                                                                        # ayla ile karşılıklı yazışma → ilişki
    s(91, [A("kerem")], "Eski yazışma", 40),
    g(1, A("ayla"), "Fiyat onayı gerek mi?", 2, ad="Ayla K", al=[BEN], tur=[0]),                                       # doğrudan, kural: soru işareti → bekleyen
    g(2, A("ayla"), "Toplantı notları?", 2, ad="Ayla K", al=[A("kerem"), BEN], tur=[0, 1]),                            # yalnız CC → bilgi
    g(3, A("ayla"), "Duyuru: kim gelebilir?", 2, ad="Ayla K", al=[A(f"u{i}") for i in range(6)] + [BEN], tur=[0] * 7, sayi=9),  # > 5 alıcı → bilgi
    g(5, A("kerem"), "Taslak sözleşme", 1, ad="Kerem Y", ozet="Taslak ekte, bakar mısın", al=[BEN], tur=[0]),          # doğrudan + rica → bekleyen
    s(6, [A("kerem")], "Teklif için onay verir misiniz?", 6),                                                      # giden, istek, dönüş yok, 4 iş günü → donus
    s(7, [A("kerem")], "Bilgi: toplantı notları ektedir", 6),                                                      # giden, bilgi amaçlı → yok
    g(8, A("ayla"), "Eski soru?", 15, ad="Ayla K", al=[BEN]),                                                      # 15 gün → düşer
    s(9, [A("kerem")], "Çok eski teklif sorusu?", 15),                                                             # 15 gün giden → düşer
    g(10, A("ayla"), "Fiyat ne olur?", 1, ad="Ayla K"),                                                            # alıcı bilgisi yok → eski kural: bekleyen
    g(11, A("yabanci"), "Merhaba, görüşelim mi?", 1, ad="Yabancı", al=[BEN]),                                     # ilişki yok → yalnız genis
    s(12, [A("ayla")], "Takvim sorusu?", 6), g(13, A("ayla"), "Re: Takvim sorusu?", 2, ad="Ayla K", al=[BEN]),      # giden, cevap geldi → donus değil
]
POS += [g(100 + i, A("satis", "firma.test"), f"Haftalık rapor {i}?", 2 + i, ad="Satış", al=[BEN]) for i in range(12)]  # 12 ileti / 30 gün, hiç yazmadın → hacim
NS["_et_kayit_kelimeleri"] = lambda: []
def an(pos=POS, **k): return N("et_analiz")(pos, SIMDI, kayit_kelime=[], **k)
a = an(); b, d = kovalar(a)
ok("alıcı doğrudan + soru/rica + ilişki → bekleyen (1, 5); alıcı bilgisi olmayan eski kural (10)", {"1", "5", "10"} <= b)
ok("yalnız CC (2) ve > 5 alıcı (3) bekleyen değil", not ({"2", "3"} & b))
ok("yüksek hacimli tek yönlü gönderen (12 ileti, hiç yazmadın) bekleyen değil", not any(str(i) in b for i in range(100, 112)))
ok("bilgi sayısı: CC + çok alıcı + hacim (12; 8 numara 14 günden eski, sayılmaz)", a["bilgi_sayi"] == 14 and a["bilgi_detay"].get("cc") == 1 and a["bilgi_detay"].get("cok_alici") == 1 and a["bilgi_detay"].get("hacim") == 12)
ok("istekli giden → donus (4 iş günü)", d == {"6"} and a["donus"][0]["gun"] == 4 and a["donus"][0]["yon"] == "giden")
ok("bilgi amaçlı giden (7), cevabı gelen giden (12), 15 günlük giden (9) donus değil", not ({"7", "9", "12"} & d))
ok("14 günden eski gelen (8) düşer", "8" not in b)
ok("ilişkisiz gönderen (11) dengeli düzeyde bekleyen değil", "11" not in b)
ok("yön ve gün alanları; legacy: onemli = bekleyen, cevapsiz gelen + giden", all(o["yon"] == "gelen" and "gun" in o for o in a["bekleyen"]) and a["onemli"] == a["bekleyen"] and any(c["yon"] == "giden" for c in a["cevapsiz"]))
# --- ham alıcı listesi ve yardımcının bayrakları --------------------------------------------------------------------------------------------------
ben = {BEN}
ok("_et_dogrudan: To → True, CC → False, > 5 alıcı → False, listede yok → None, bilgi yok → None", N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[BEN], tur=[0]), ben) is True and N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[A("k"), BEN], tur=[0, 1]), ben) is False
   and N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[BEN], tur=[0], sayi=8), ben) is False and N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[A("k")], tur=[0]), ben) is None and N("_et_dogrudan")(g(1, A("x"), "k", 1), ben) is None)
ok("tür numarası kayık olsa da (1 = To, 2 = CC) en küçük tür To sayılır", N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[A("k"), BEN], tur=[1, 2]), ben) is False and N("_et_dogrudan")(g(1, A("x"), "k", 1, al=[BEN, A("k")], tur=[1, 2]), ben) is True)
ok("yalnız yardımcı bayrakları (ham liste yok): ben_kime / ben_cc", N("_et_dogrudan")({"ben_kime": True, "alici_sayi": 2}, ben) is True and N("_et_dogrudan")({"ben_kime": False, "ben_cc": True}, ben) is False)
# --- düzeyler ----------------------------------------------------------------------------------------------------------------------------------------
AYAR["eposta_onem_duzeyi"] = "genis"; bg, dg = kovalar(an()); ok("genis: ilişki şartı yok (11 girer), CC/çok alıcı/hacim hâlâ bilgi", "11" in bg and not ({"2", "3"} & bg))
AYAR["eposta_onem_duzeyi"] = "siki"; bs, ds = kovalar(an()); ok("siki: Claude yokken yalnız VIP (kimse yok) → bekleyen boş; donus yalnız VIP alıcı + kalıp", bs == set() and ds == set())
AYAR["eposta_vip"] = ["Ayla K"]; bs, ds = kovalar(an()); ok("siki + VIP: VIP gönderenin doğrudan iletileri (1, 10); CC'deki VIP (2) hâlâ bilgi", {"1", "10"} <= bs and "2" not in bs and "5" not in bs)
AYAR.pop("eposta_vip"); AYAR["eposta_onem_duzeyi"] = "dengeli"
AYAR["eposta_onem_gun"] = 30; b30, d30 = kovalar(an()); ok("eposta_onem_gun 30: 15 günlük gelen (8) ve giden (9) geri gelir", "8" in b30 and "9" in d30); AYAR["eposta_onem_gun"] = 14
AYAR["eposta_cevapsiz_gun"] = 5; _, d5 = kovalar(an()); ok("eposta_cevapsiz_gun 5: 4 iş günlük giden donus değil", d5 == set()); AYAR.pop("eposta_cevapsiz_gun")
# --- Claude: zincir bağlamı; yalnız ad/göreli zaman/özet; değerlendirme kovaları belirler ---------------------------------------------------------
AYAR["eposta_claude_siralama"] = True; NS["POSTA"]["iletiler"] = POS; NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; CAGRI.clear()
a = N("et_tara")(zorla=True, simdi=SIMDI)
veri = CAGRI[0].rsplit("<veri>", 1)[1] if CAGRI else ""
ok("tek çağrı; her aday zincir bir blok ([zincir id] konu + kronolojik satırlar)", len(CAGRI) == 1 and veri.count("[zincir ") >= 4)
ok("istemde e-posta adresi, alıcı adı, mutlak tarih ya da iç alan yok; gönderen adı ve 'sen' var", not re.search(r"@|ornek\\.test|gelen_alici|alici_sayi|202\\d-\\d\\d-\\d\\d", veri) and "Ayla K" in veri and " sen → " in veri and "gün önce" in veri)
ok("istemde beş durum, aciliyet ve <veri> notu var", all(d in CAGRI[0] for d in ("senden_bekleniyor", "baskasi_cevapladi", "cozuldu", "donus_bekliyorsun")) and "aciliyet" in CAGRI[0] and "yalnız VERİDİR" in CAGRI[0])
b, d = kovalar(a); ok("değerlendirme: 5 (sözleşme, aciliyet 3) ve 1 (onay, 2) bekleyen; bilgi denen 10 değil", {"1", "5"} <= b and "10" not in b)
ok("sıra aciliyet × tazelik: 5 (3, 1 gün) 1'in (2, 2 gün) önünde; öğede durum/aciliyet/neden", [o["id"] for o in a["bekleyen"]].index("5") < [o["id"] for o in a["bekleyen"]].index("1")
   and next(o for o in a["bekleyen"] if o["id"] == "5")["aciliyet"] == 3 and next(o for o in a["bekleyen"] if o["id"] == "5")["durum"] == "senden_bekleniyor" and "Somut istek" in a["bekleyen"][0]["neden"])
ok("giden: 6 'onay' → donus_bekliyorsun → donus", d == {"6"})
ok("durum sayıları görünümde (bilgi en az 1), değerlendirilmeyen yok", (a.get("durum_sayi") or {}).get("bilgi", 0) >= 1 and a["degerlendirilmedi"] == 0 and not any(o["degerlendirilmedi"] for o in a["bekleyen"] + a["donus"]))
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); ok("değişiklik yok → ikinci taramada çağrı yok (önbellek: zincir + son ileti)", not CAGRI)
Beyin.tur = "openai-uyumlu"; NS["ET"]["durum"] = None; CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI)
ok("başka sağlayıcıda model çağrısı yok, kural katmanı çalışır, 'değerlendirilmedi' işareti yok", not CAGRI and "1" in {o["id"] for o in NS["ET"]["gorunum"]["bekleyen"]} and not any(o["degerlendirilmedi"] for o in NS["ET"]["gorunum"]["bekleyen"])); Beyin.tur = "claude-code"
# --- uç yanıtı ----------------------------------------------------------------------------------------------------------------------------------------
AYAR["eposta_claude_siralama"] = False; NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; v = N("et_view")()
ok("görünüm: bekleyen, donus, bilgi_sayi, ozet_sayi (= bekleyen sayısı), geriye uyum onemli/cevapsiz, iç alan yok", v["izin"] and v["ozet_sayi"] == len(v["bekleyen"]) and v["bilgi_sayi"] == 14 and v["onemli"] == v["bekleyen"] and isinstance(v["cevapsiz"], list)
   and not any(k.startswith("_") for o in v["bekleyen"] + v["donus"] + v["cevapsiz"] for k in o))
# --- öğrenme: kalıcı --------------------------------------------------------------------------------------------------------------------------------
r = N("et_islem")({"islem": "onemsiz_gonderen", "id": "5"}); ok("onemsiz_gonderen: gönderenin iletileri bekleyenden düştü, bilgiye girdi, ayara ve dosyaya yazıldı", r["ok"] and "5" not in {o["id"] for o in r["bekleyen"]} and r["bilgi_sayi"] >= 15 and A("kerem") in KAYITLI["eposta_onemsiz"] and A("kerem") in json.load(open(os.path.join(T, "eposta-takip.json")))["onemsiz"])
NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; ok("yeniden yüklenince de kalıcı (dosyadan)", "5" not in {o["id"] for o in N("et_view")()["bekleyen"]})
AYAR.pop("eposta_onemsiz", None); ok("ayar listesi silinse bile dosyadaki liste geçerli", "5" not in {o["id"] for o in N("et_view")()["bekleyen"]})
r = N("et_islem")({"islem": "onemli_kisi", "id": "11"}); ok("onemli_kisi: adres eposta_vip'e eklendi (VIP sayılır) ve ileti ilişkisizken de bekleyen", r["ok"] and A("yabanci") in KAYITLI["eposta_vip"] and "11" in {o["id"] for o in r["bekleyen"]})
r = N("et_islem")({"islem": "onemli_kisi", "adres": "yok-adres"}); ok("geçersiz adres reddedilir", r["ok"] is False)
r = N("et_islem")({"islem": "onemsiz_gonderen", "id": "999"}); ok("bilinmeyen ileti kimliği reddedilir", r["ok"] is False)
r = N("et_islem")({"islem": "yoksay", "id": "1"}); ok("yoksay ve ertele eskisi gibi çalışır", r["ok"] and "1" not in {o["id"] for o in r["bekleyen"]})
AYAR["eposta_vip"] = [f"v{i}" + AT + "x.test" for i in range(20)]; r = N("et_islem")({"islem": "onemli_kisi", "adres": A("yeni")}); ok("VIP listesi doluysa (20) açık hata", r["ok"] is False and "dolu" in r["err"])
# --- hatırlatma: eski bildirim sürümünden gelen durum sessiz görülür --------------------------------------------------------------------------------
AYAR.pop("eposta_vip"); BILD = []; NS["bildirim"] = lambda *x, **k: BILD.append(x)
open(os.path.join(T, "eposta-takip.json"), "w").write(json.dumps({"yoksay": {}, "ertele": {}, "bildirilen": {"o1": "x"}, "skor": {"5": {"o": 0, "n": "eski"}}, "ilk": True}))
NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; N("et_tara")(zorla=True, simdi=SIMDI)
ok("şema yükseltmesi: eski skorlar atılır, ilk tarama sessiz (bildirim yok)", not BILD and N("et_durum")()["s"] == 3 and "5" not in N("et_durum")()["skor"] and isinstance(N("et_durum")()["zd"], dict))
NS["POSTA"]["iletiler"] = POS + [g(200, A("ayla"), "Yeni soru var mı?", 0, ad="Ayla K", al=[BEN])]; N("et_tara")(zorla=True, simdi=SIMDI)
ok("yeni bekleyen ileti → 'senden cevap bekliyor' bildirimi", len(BILD) == 1 and "cevap bekliyor" in BILD[0][2])
b = N("et_baglam")("Kime cevap vermedim?", SIMDI); ok("Konuş bağlamı yeni kovalarla: iki bölüm + bilgi sayısı", "Senden cevap bekleyenler" in b and "Dönüş beklediklerin" in b and "yalnız bilgi" in b)
# --- S263: zincir bağlamı (kullanıcının gerçek örneğinin kurgu karşılığı) ------------------------------------------------------------------------
# Z1: dış kişi sana soru sordu, ekip arkadaşı (sen CC'de) zincirde açıklamayı yaptı → değerlendirmeyle düşer; kural tek başına "başkası yazmış" der.
# Z2: sen cevapladın → kural düşürür, Claude'a hiç gitmez. Z3: senden imza bekleniyor → bekleyen.
def zg(id_, z, adres, konu, gn, ozet, al, tur, ad, saat=10): return dict(g(id_, adres, konu, gn, ozet=ozet, al=al, tur=tur, ad=ad), zincir=z, t=gun(gn, saat))
def zs(id_, z, alici, konu, gn, ozet, saat=10): return dict(s(id_, alici, konu, gn, ozet), zincir=z, t=gun(gn, saat))
ZPOS = [zs(300, "400", [A("dis1", "musteri.test"), A("dis2", "musteri.test"), A("dis3", "musteri.test")], "Tanışma", 40, "Merhaba"),  # ilişki (40 gün: aday değil)
        zg(301, "501", A("dis1", "musteri.test"), "Hesap ekstresi?", 2, "Hesap ekstresini paylaşır mısınız?", [BEN], [0], "Dış Bir"),
        zg(302, "501", A("ekip", "ornek.test"), "Re: Hesap ekstresi?", 1, "Gerekli açıklamayı yaptım, ekstre ekte.", [A("dis1", "musteri.test"), BEN], [0, 1], "Ekip Arkadaş"),
        zg(311, "502", A("dis2", "musteri.test"), "Tarih?", 2, "Toplantı tarihini onaylar mısın?", [BEN], [0], "Dış İki"),
        zs(312, "502", [A("dis2", "musteri.test")], "Re: Tarih?", 1, "Perşembe uygun."),
        zg(321, "503", A("dis3", "musteri.test"), "Sözleşme imzası?", 1, "Sözleşmeyi bugün imzalayabilir misin? Kopyası " + A("arsiv", "musteri.test") + " adresinde.", [BEN], [0], "Dış Üç")]
AYAR.pop("eposta_onemsiz", None); AYAR["eposta_claude_siralama"] = True; NS["POSTA"]["iletiler"] = ZPOS; NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None
try: os.remove(os.path.join(T, "eposta-takip.json"))
except OSError: pass
r0 = N("et_analiz")(ZPOS, SIMDI, kayit_kelime=[], durum={"yoksay": {}, "ertele": {}}, deger={}, beklenen=True); b0 = {o["id"]: o for o in r0["bekleyen"]}
ok("kural (değerlendirme yok): Z1 listede ama 'değerlendirilmedi' ve neden 'başkası yazmış'; Z2 (sen cevapladın) yok; Z3 var", "301" in b0 and b0["301"]["degerlendirilmedi"] and "başkası" in b0["301"]["neden"] and "311" not in b0 and "321" in b0)
ok("Claude adayları: Z1 ve Z3 (Z2 cevaplandığı için aday değil); aday zincirin son ≤ 6 iletisi", sorted(x["zincir"] for x in r0["adaylar"]) == ["z:501", "z:503"] and [str(y["id"]) for y in next(x for x in r0["adaylar"] if x["zincir"] == "z:501")["iletiler"]] == ["301", "302"])
CAGRI.clear(); a = N("et_tara")(zorla=True, simdi=SIMDI); veri = CAGRI[0].rsplit("<veri>", 1)[1] if CAGRI else ""; b, d = kovalar(a)
ok("tek çağrı, iki zincir bloğu; Z1 bloğunda iki satır kronolojik (önce dış kişi → sana, sonra ekip arkadaşı CC'li)", len(CAGRI) == 1 and veri.count("[zincir ") == 2
   and veri.index("Dış Bir → sana") < veri.index("Ekip Arkadaş") and "sen CC'de" in veri and "502" not in veri)
ok("Claude'a adres gitmez (ne gönderen ne alıcı adresi, ne alan adı; özetteki adres de maskeli)", "@" not in veri and "musteri.test" not in veri and "ornek.test" not in veri and "[adres]" in veri)
ok("zincirde başkası cevapladı → bekleyenden düşer, durum sayısında görünür", "301" not in b and a["durum_sayi"].get("baskasi_cevapladi") == 1)
ok("kullanıcı cevapladı → düşer", "311" not in b and "312" not in d)
ok("senden bekleniyor (aciliyet 3) → bekleyen, neden Claude'dan", b == {"321"} and a["bekleyen"][0]["aciliyet"] == 3 and "senden_bekleniyor" in a["bekleyen"][0]["neden"])
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); ok("değişiklik yok → 0 çağrı", not CAGRI)
NS["POSTA"]["iletiler"] = ZPOS + [zg(322, "503", A("dis3", "musteri.test"), "Re: Sözleşme imzası?", 0, "Hatırlatma: imza bekliyoruz.", [BEN], [0], "Dış Üç", saat=9)]
CAGRI.clear(); a = N("et_tara")(zorla=True, simdi=SIMDI); veri = CAGRI[0].rsplit("<veri>", 1)[1] if CAGRI else ""
ok("zincire yeni ileti → yalnız o zincir yeniden sorulur (tek çağrı, tek blok)", len(CAGRI) == 1 and veri.count("[zincir ") == 1 and "Hatırlatma" in veri and "Hesap" not in veri and kovalar(a)[0] == {"322"})
NS["POSTA"]["iletiler"] = ZPOS + [zg(330 + i, f"6{i:02d}", A(f"k{i}", "musteri.test"), f"Konu {i} onay?", 1, "Onay verir misin?", [BEN], [0], f"Kişi {i}") for i in range(30)] + \
                          [zs(399, "700", [A(f"k{i}", "musteri.test") for i in range(5)], "Tanışma 2", 40, "x"), zs(398, "701", [A(f"k{i}", "musteri.test") for i in range(5, 30)][:5], "Tanışma 3", 40, "x")]
AYAR["eposta_onem_duzeyi"] = "genis"; CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); n1 = len(CAGRI); blk1 = CAGRI[0].count("[zincir ") if CAGRI else 0
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); n2 = len(CAGRI); blk2 = CAGRI[0].count("[zincir ") if CAGRI else 0
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); n3 = len(CAGRI)
ok(f"turda en çok 1 çağrı, en çok 25 zincir; kalanlar sonraki turda, sonra 0 ({n1}/{blk1}, {n2}/{blk2}, {n3})", n1 == 1 and blk1 == 25 and n2 == 1 and blk2 == 5 and n3 == 0)
AYAR["eposta_onem_duzeyi"] = "dengeli"
MOD["hata"] = "kota"; NS["POSTA"]["iletiler"] = ZPOS; NS["ET"]["durum"] = None; os.remove(os.path.join(T, "eposta-takip.json")); CAGRI.clear()
a = N("et_tara")(zorla=True, simdi=SIMDI); bh = {o["id"]: o for o in a["bekleyen"]}
ok("Claude hata → kural sonucu görünür, her öğede 'değerlendirilmedi'; boş hata yok", len(CAGRI) == 1 and {"301", "321"} <= set(bh) and all(o["degerlendirilmedi"] for o in bh.values()) and a["degerlendirilmedi"] == 2)
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); ok("hata sonrası aynı aday kümesi hemen yeniden sorulmaz (0 çağrı)", not CAGRI)
v = N("et_view")(); ok("uç: öğede degerlendirilmedi alanı ve sayaç", v["degerlendirilmedi"] == 2 and all("degerlendirilmedi" in o and "aciliyet" in o and "durum" in o for o in v["bekleyen"]))
BILD.clear(); NS["POSTA"]["iletiler"] = ZPOS + [zg(340, "504", A("dis1", "musteri.test"), "Yeni soru onay?", 0, "Onaylar mısın?", [BEN], [0], "Dış Bir", saat=9)]; N("et_tara")(zorla=True, simdi=SIMDI)
ok("değerlendirilmemiş yeni öğe için bildirim yok (değerlendirme bekler)", not BILD)
MOD["hata"] = None; NS["ET"]["hata_kume"] = None; N("et_tara")(zorla=True, simdi=SIMDI)
ok("değerlendirme gelince bildirim: 'senden cevap bekliyor'", len(BILD) == 1 and "cevap bekliyor" in BILD[0][2])
bg = N("et_baglam")("Önemli e-postam var mı?", SIMDI); ok("Konuş bağlamı: listeden düşen 'başkası cevaplamış' sayısı ve öğe nedeni", "başkası cevaplamış" in bg and "Somut istek" in bg)
# yedek gruplama (zincir alanı yok): konu kökü + katılımcı kesişimi
YP = [{k: v for k, v in x.items() if k != "zincir"} for x in ZPOS]; zk = N("et_zincirler")(YP, {BEN}); zz = {str(x["id"]): zk[id(x)] for x in YP}
ok("yedek gruplama: 'Re:' atılır + ortak katılımcı → aynı zincir (301, 302; 311, 312); farklı konu ayrı (321)", zz["301"] == zz["302"] and zz["311"] == zz["312"] and zz["321"] not in (zz["301"], zz["311"]))
ok("yedek gruplama: aynı konu, ortak katılımcı yok → ayrı zincir", len(set(N("et_zincirler")([g(1, A("a1"), "Rapor", 1, al=[BEN]), g(2, A("b1"), "Re: Rapor", 1, al=[BEN])], {BEN}).values())) == 2)
r1 = N("et_analiz")(YP, SIMDI, kayit_kelime=[], durum={"yoksay": {}, "ertele": {}}, deger={}, beklenen=True)
ok("zincir alanı olmadan da kullanıcı cevabı (311) düşer, başkasının cevabı (301) işaretlenir", "311" not in {o["id"] for o in r1["bekleyen"]} and "başkası" in next(o for o in r1["bekleyen"] if o["id"] == "301")["neden"])
# --- düşük öncelikli (katlı satır): dengeli düzeyde aciliyet 1'lik dönüş gizlenir ama "dusuk"te görünür; özet sayacı ve bildirim etkilenmez ----------------------------------------------
AYAR["eposta_claude_siralama"] = True; MOD["hata"] = None; BILD.clear()
NS["POSTA"]["iletiler"] = POS + [s(900, [A("ayla")], "Kahve toplantısı notları", 6), g(901, A("ayla"), "Ekstra onay", 1, ad="Ayla K", al=[BEN])]; NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; NS["ET"]["hata_kume"] = None
a9 = N("et_tara")(zorla=True, simdi=SIMDI); v9 = N("et_view")()
ok("dusuk: aciliyet 1'lik dönüş (900) donus'ta değil, 'dusuk'te (yon giden, aciliyet 1, neden dolu)", "900" not in {o["id"] for o in v9["donus"]} and any(o["id"] == "900" and o["yon"] == "giden" and o["aciliyet"] == 1 and o["neden"] for o in v9["dusuk"]))
ok("dusuk: özet sayacı bekleyen sayısına eşit (dusuk girmez), iç alan yok", v9["ozet_sayi"] == len(v9["bekleyen"]) and not any(k.startswith("_") for o in v9["dusuk"] for k in o))
ok("dusuk: 'dusuk' öğesi için taslak/ertele işlenir (ET idler)", "900" in NS["ET"]["idler"] and N("et_islem")({"islem": "ertele", "id": "900"})["ok"])
NS["ET"]["durum"] = None; AYAR["eposta_onem_duzeyi"] = "siki"; NS["ET"]["gorunum"] = None; v9 = N("et_view")()
ok("dusuk: sıkı düzeyde aciliyet 1'lik gelen (901) bekleyen değil, 'dusuk'te", "901" not in {o["id"] for o in v9["bekleyen"]} and any(o["id"] == "901" and o["yon"] == "gelen" for o in v9["dusuk"])); AYAR["eposta_onem_duzeyi"] = "dengeli"
shutil.rmtree(T, ignore_errors=True); print(("\nKALDI: " + ", ".join(HATA)) if HATA else "\nTamam"); sys.exit(1 if HATA else 0)
