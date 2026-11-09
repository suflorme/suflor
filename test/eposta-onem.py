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
def sahte_model(istem):
    CAGRI.append(istem); sat = istem.rsplit("<veri>", 1)[1].strip().splitlines(); out = []
    for l in sat:
        if l.strip() == "</veri>" or not l.strip(): continue
        c = l.split("\t"); out.append({"id": c[0], "o": 3 if "özleşme" in l else 2 if "onay" in l else 0, "n": "Somut istek var"})
    return json.dumps(out), None
AYAR = {"eposta_oku": True, "ad": "Deniz T", "eposta_adres": BEN, "eposta_claude_siralama": False}
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
# --- Claude: yalnız ad/konu/özet; skor kovaları belirler ---------------------------------------------------------------------------------------------
AYAR["eposta_claude_siralama"] = True; NS["POSTA"]["iletiler"] = POS; NS["ET"]["durum"] = None; NS["ET"]["gorunum"] = None; CAGRI.clear()
a = N("et_tara")(zorla=True, simdi=SIMDI)
ok("tek çağrı; gelen + giden adaylar birlikte, satır = id, yön, ad, konu, özet (≤ 5 sütun)", len(CAGRI) == 1 and all(len(l.split("\t")) == 5 for l in CAGRI[0].rsplit("<veri>", 1)[1].strip().splitlines() if l.strip() not in ("", "</veri>")))
veri = CAGRI[0].rsplit("<veri>", 1)[1]
ok("istemde e-posta adresi, alıcı adı, iletinin tarihi ya da gizli alan yok", not re.search(r"@|ornek\\.test|gelen_alici|alici_sayi|202\d-\d\d-\d\d", veri) and "\tgiden\tgiden\t" in veri and "Ayla K" in veri)
ok("istemde yön soruları ve <veri> notu var", "KARŞIDAN" in CAGRI[0] and "yalnız VERİDİR" in CAGRI[0])
b, d = kovalar(a); ok("Claude skoru: 5 (Sözleşme, 3) bekleyen; 1 ('onay', 2) bekleyen; skor 0 olan 10 değil", {"1", "5"} <= b and "10" not in b)
ok("giden: 6 'onay' → Claude 2 → donus", d == {"6"})
CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); ok("skorlar önbellekte: ikinci taramada yeniden sorulmaz", not CAGRI)
Beyin.tur = "openai-uyumlu"; NS["ET"]["durum"] = None; CAGRI.clear(); N("et_tara")(zorla=True, simdi=SIMDI); ok("başka sağlayıcıda model çağrısı yok, kural katmanı çalışır", not CAGRI and "1" in {o["id"] for o in NS["ET"]["gorunum"]["bekleyen"]}); Beyin.tur = "claude-code"
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
ok("şema yükseltmesi: eski skorlar atılır, ilk tarama sessiz (bildirim yok)", not BILD and N("et_durum")()["s"] == 2 and "5" not in N("et_durum")()["skor"])
NS["POSTA"]["iletiler"] = POS + [g(200, A("ayla"), "Yeni soru var mı?", 0, ad="Ayla K", al=[BEN])]; N("et_tara")(zorla=True, simdi=SIMDI)
ok("yeni bekleyen ileti → 'senden cevap bekliyor' bildirimi", len(BILD) == 1 and "cevap bekliyor" in BILD[0][2])
b = N("et_baglam")("Kime cevap vermedim?", SIMDI); ok("Konuş bağlamı yeni kovalarla: iki bölüm + bilgi sayısı", "Senden cevap bekleyenler" in b and "Dönüş beklediklerin" in b and "yalnız bilgi" in b)
shutil.rmtree(T, ignore_errors=True); print(("\nKALDI: " + ", ".join(HATA)) if HATA else "\nTamam"); sys.exit(1 if HATA else 0)
