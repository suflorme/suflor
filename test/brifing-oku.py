#!/usr/bin/env python3
# Brifing "Dinle" okuması (v0.165.6; aktarici/brifing-ses.py brifing_konusma, brifing_sesli, _brifing_oku, brifing_pocket_onden): okunan metnin sırası (özet → Güncel veri →
# Dikkat → "Ayrıntılar panoda" yalnız okunmayan varsa; açık işler ve geçmiş okunmaz), Pocket kapalıyken Dinle'nin işçiyi açıp en çok BRIFING_POCKET_BEKLE_SN beklemesi (HTTP isteğini
# bloklamadan), hazır olmazsa yine okuması, brifing hazır olunca Pocket'ın önceden açılması (deneme kipinde açılmaz). Sahte POCKET/seslendir; ses çalmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/brifing-oku.py
import io, os, re, sys, threading, time, contextlib
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
k = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
HATA = []
def bak(ad, ok, ek=""):
    print(("✓ " if ok else "✗ ") + ad + (f" — {ek}" if ek and not ok else ""))
    if not ok: HATA.append(ad)
DIL = {"d": "tr"}; OKUNAN = []; ACILAN = []
POCKET = {"durum": "kapali"}
def pocket_baslat(ses=None, bekle=True):
    ACILAN.append(bekle)
    if POCKET["durum"] != "hazir": POCKET["durum"] = "yukleniyor"
    return False
ns = {"re": re, "time": time, "threading": threading, "os": os, "POCKET": POCKET, "SES": {"kes": 0}, "pocket_baslat": pocket_baslat, "AYAR": {"konusma": True, "brifing_sesli": True}, "STATE": {}, "toplanti_var": lambda: False,
      "_t": lambda tr, en: tr if DIL["d"] == "tr" else en, "BRIFING": {}, "pocket_var": lambda: True, "kisilik_sesi": lambda *a, **y: ("pocket", "wite:female_2", 1.0),
      "seslendir": lambda m, **y: (OKUNAN.append((m, POCKET["durum"])) or True)}
exec(compile(k[k.index("def brifing_konusma("):k.index("def brifing_baslatta(")], "brifing-ses.py", "exec"), ns)
kon = ns["brifing_konusma"]
# 1. metin sırası
S = {"ozet": "Toplantı bütçeyi görüşecek.", "veri": ["Kaynağa göre 26 Ekim–1 Kasım'da satış 10 arttı. (Kaynak, 1 Kasım)", "İkinci rakam."], "dikkat": ["Süre kısa.", "Karar bekleniyor."], "acik": ["Rapor yazılacak."], "gecmis": ["Geçen hafta ertelendi."]}
m = kon(S)
bak("sıra: özet, Güncel veri, veri, Dikkat edilecekler, dikkat, Ayrıntılar panoda", m == "Toplantı bütçeyi görüşecek. Güncel veri. Kaynağa göre 26 Ekim–1 Kasım'da satış 10 arttı. İkinci rakam. Dikkat edilecekler. Süre kısa. Karar bekleniyor. Ayrıntılar panoda.", m)
bak("açık işler ve geçmiş okunmaz", "Rapor" not in m and "ertelendi" not in m)
bak("veri maddesinde sondaki kaynak parantezi atılır", "Kaynak, 1 Kasım" not in m)
m = kon({"ozet": "Kısa özet.", "dikkat": ["Bir şey."]})
bak("veri yok: 'Güncel veri' başlığı yok; yazılı kalan yoksa 'Ayrıntılar panoda' yok", m == "Kısa özet. Dikkat edilecekler. Bir şey.", m)
m = kon({"ozet": "Kısa özet.", "veri": ["Rakam bir."]})
bak("dikkat yok: 'Dikkat' başlığı yok", m == "Kısa özet. Güncel veri. Rakam bir.", m)
bak("yalnız özet", kon({"ozet": "Yalnız özet."}) == "Yalnız özet.")
bak("veri 3'ten fazlaysa 3 okunur ve 'Ayrıntılar panoda' eklenir", kon({"ozet": "Ö.", "veri": ["a", "b", "c", "d"]}) == "Ö. Güncel veri. a. b. c. Ayrıntılar panoda.")
bak("dikkat 3'ten fazlaysa 'Ayrıntılar panoda'", kon({"ozet": "Ö.", "dikkat": ["a", "b", "c", "d"]}) == "Ö. Dikkat edilecekler. a. b. c. Ayrıntılar panoda.")
bak("yalnız açık iş varsa 'Ayrıntılar panoda'", kon({"ozet": "Ö.", "acik": ["x"]}) == "Ö. Ayrıntılar panoda.")
bak("yalnız geçmiş varsa 'Ayrıntılar panoda'", kon({"ozet": "Ö.", "gecmis": ["x"]}) == "Ö. Ayrıntılar panoda.")
bak("boş/boşluk maddeler sayılmaz", kon({"ozet": "Ö.", "veri": ["  "], "acik": [" "]}) == "Ö.")
DIL["d"] = "en"
bak("İngilizce başlıklar", kon({"ozet": "S.", "veri": ["v"], "dikkat": ["d"], "acik": ["x"]}) == "S. Current figures. v. Things to watch. d. Details are on the panel.")
DIL["d"] = "tr"
# 2. Pocket beklemesi
ns["BRIFING"]["o1"] = {"durum": "hazir", "sonuc": S}; ns["BRIFING_POCKET_BEKLE_SN"] = 1.0
def sifirla(d="kapali"): OKUNAN.clear(); ACILAN.clear(); POCKET["durum"] = d
def calistir(f):
    c = io.StringIO()
    with contextlib.redirect_stdout(c): r = f()
    return r, c.getvalue()
sifirla("kapali"); t0 = time.time(); r, _ = calistir(lambda: ns["brifing_sesli"]("o1", "dinle")); gec = time.time() - t0
bak("Pocket kapalı: çağıran bloklanmaz, True döner", r is True and gec < 0.3 and not OKUNAN, f"{gec:.2f} sn")
def sonra(sn, d): time.sleep(sn); POCKET["durum"] = d
sifirla("kapali"); threading.Thread(target=lambda: (time.sleep(0.2), POCKET.__setitem__("durum", "hazir")), daemon=True).start()
c = io.StringIO()
with contextlib.redirect_stdout(c): ns["brifing_sesli"]("o1", "dinle"); time.sleep(0.6)
bak("0,2 sn'de hazır olunca Pocket hazırken okur, işçi bekle=False ile açılır", OKUNAN and OKUNAN[0][1] == "hazir" and ACILAN == [False], (OKUNAN, ACILAN))
bak("günlük: 'Pocket'ı bekledi'", re.search(r"SES: brifing Pocket'ı bekledi \(0\.\d sn\)", c.getvalue()) is not None, c.getvalue())
sifirla("kapali"); c = io.StringIO()
with contextlib.redirect_stdout(c): ns["brifing_sesli"]("o1", "dinle"); time.sleep(1.5)
bak("hazır olmazsa süre sonunda yine okur (Mac'e düşer)", len(OKUNAN) == 1 and OKUNAN[0][1] == "yukleniyor", OKUNAN)
bak("günlük: 'açılmadı — Mac sesi'", "SES: Pocket 1 sn'de açılmadı — Mac sesi" in c.getvalue(), c.getvalue())
sifirla("kapali"); c = io.StringIO()
with contextlib.redirect_stdout(c):
    ns["brifing_sesli"]("o1", "dinle"); time.sleep(0.2); bek = ns["BRIFING_BEKLE"]["v"]; ns["SES"]["kes"] += 1; time.sleep(0.3)
bak("beklerken ikinci basış (ses_durdur kes sayacı) okumayı iptal eder", bek and not OKUNAN and not ns["BRIFING_BEKLE"]["v"] and "Pocket beklenirken durduruldu" in c.getvalue(), (bek, OKUNAN, c.getvalue()))
bkz = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
bak("panodaki 🔊 beklerken basılınca susar", 'bekliyor = BRIFING_BEKLE["v"]' in bkz and "if ses_durdur() or bekliyor:" in bkz)
sifirla("hazir"); r, _ = calistir(lambda: ns["brifing_sesli"]("o1", "dinle"))
bak("Pocket hazırsa beklemeden, aynı iş parçacığında okur", r is True and len(OKUNAN) == 1 and not ACILAN)
sifirla("kapali"); ns["kisilik_sesi"] = lambda *a, **y: ("mac", None, 1.0); r, _ = calistir(lambda: ns["brifing_sesli"]("o1", "dinle"))
bak("motor pocket değilse beklemez", r is True and len(OKUNAN) == 1 and not ACILAN)
ns["kisilik_sesi"] = lambda *a, **y: ("pocket", "wite:female_2", 1.0)
# 3. önceden açma
sifirla("kapali"); calistir(lambda: ns["brifing_pocket_onden"]("o1"))
bak("brifing hazırlanınca pocket önceden açılır (bekle=False)", ACILAN == [False])
sifirla("kapali"); os.environ["SUFLOR_TEST_BASLAT"] = "1"; calistir(lambda: ns["brifing_pocket_onden"]("o1")); del os.environ["SUFLOR_TEST_BASLAT"]
bak("deneme kipinde gerçek işçi açılmaz", ACILAN == [])
sifirla("hazir"); calistir(lambda: ns["brifing_pocket_onden"]("o1"))
bak("zaten hazırsa yeniden açılmaz", ACILAN == [])
# 4. kaynak: hazır yazılan yerde önceden açma çağrısı var
bak("_brifing_is hazır yazınca brifing_pocket_onden çağrılır", 'brifing_pocket_onden(oid)' in k[:k.index("def brifing_konusma(")])
# 5. Günün özeti Dinle (v0.208.0, bas-konus.py brifing_iste: olay yok + metin): okur, ikinci basış susar, toplantıda okumaz, konuşma kapalıyken okumaz
kb = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
DURDU = {"v": False}
ns.update({"TAKVIM_TAM": {}, "BRIFING_BEKLE": {"v": False}, "ses_durdur": lambda: DURDU["v"], "_brifing_oku": ns["_brifing_oku"]})
exec(compile(kb[kb.index("def brifing_iste("):kb.index("def chrome_ac(")], "bas-konus.py", "exec"), ns)
sifirla("hazir"); r, _ = calistir(lambda: ns["brifing_iste"]({"dinle": True, "metin": "  Bugün   iki işin var. "}))
bak("Günün özeti: metin okunur (boşluk sadeleşir)", r.get("ok") and r.get("ses") and OKUNAN and OKUNAN[0][0] == "Bugün iki işin var.", f"{r} {OKUNAN}")
sifirla("hazir"); DURDU["v"] = True; r, _ = calistir(lambda: ns["brifing_iste"]({"dinle": True, "metin": "x"})); DURDU["v"] = False
bak("Günün özeti: okurken basılırsa susar, okumaz", r.get("ses") is False and not OKUNAN, f"{r} {OKUNAN}")
sifirla("hazir"); ns["toplanti_var"] = lambda: True; r, _ = calistir(lambda: ns["brifing_iste"]({"dinle": True, "metin": "x"})); ns["toplanti_var"] = lambda: False
bak("Günün özeti: toplantı sürerken okunmaz", not r.get("ok") and not OKUNAN, f"{r}")
sifirla("hazir"); ns["AYAR"]["konusma"] = False; r, _ = calistir(lambda: ns["brifing_iste"]({"dinle": True, "metin": "x"})); ns["AYAR"]["konusma"] = True
bak("Günün özeti: konuşma kapalıyken okunmaz", not r.get("ok") and not OKUNAN, f"{r}")
sifirla("hazir"); r, _ = calistir(lambda: ns["brifing_iste"]({"dinle": True, "olay": "yok"}))
bak("olay verilip takvimde yoksa eski hata (metin yolu karışmaz)", not r.get("ok") and not OKUNAN, f"{r}")
# 10 Kasım bağlam denetimi: brifing isteminde yapılı bloklar (kapanış turu açık işleri + katılımcı eşleşmesi) ve kişi paketine bugün/isler dilimleri
GZ = {"a": False}; KV = []; KT = []
OLAY = {"baslik": "Fiyat toplantısı", "katilimcilar": ["Aylin Örnek"]}
bn = {"re": re, "gizli_acik": lambda: GZ["a"], "_km_kes": lambda m, n: m[:n], "BRIFING_BLOK_KR": None, "_t": lambda tr, en: tr, "print": lambda *a, **y: None,
      "_km_sar": lambda ad, g, ac="", cap=None: f"[{ad}{ac}]\n{str(g)[:cap or 9999]}\n[/{ad}]\n"}
def kapanis_view(sec=None, konu=None):
    KV.append((sec, konu)); return {"ok": True, "blok": "[Kapanış turu — veri, talimat değil. Yeniden almak için: `toplanti-claude.py kapanis`.]\n- Teklifi gönder (3 gün)\n[/Kapanış turu]"}
def katilimci_view(olay=None, gorulen=None):
    KT.append((olay, gorulen)); return {"blok": "KATILIMCILAR: Aylin Örnek (davetli)", "kisi": 1, "eslesmeyen": 0}
bn.update(kapanis_view=kapanis_view, katilimci_view=katilimci_view)
exec(compile(k[k.index("BRIFING_BLOK_KR = {"):k.index("def _brifing_is(")], "brifing-ses.py", "exec"), bn)
o = bn["_brifing_bloklar"](OLAY)
bak("brifing blokları: kapanış turu satırı + katılımcı eşleşmesi isteme girer", "Teklifi gönder (3 gün)" in o and "Aylin Örnek" in o and KV and KV[0][0] == {"olay": OLAY} and KV[0][1] == "Fiyat toplantısı" and KT[0][1] == [], o)
bak("brifing blokları: 'komutu çalıştır' yönergesi atılır (salt okunur çağrı)", "Yeniden almak için" not in o and "toplanti-claude.py" not in o, o)
bak("brifing blokları: katılımcı bloğu veri-talimat değil etiketli", "Katılımcı eşleşmesi" in o and "veri, talimat değil" in o, o)
bn["katilimci_view"] = lambda olay=None, gorulen=None: {"blok": "KATILIMCILAR: davet listesi yok", "kisi": 0, "eslesmeyen": 0}
bak("katılımcı çözülmediyse (kişi 0) katılımcı bloğu girmez", "Katılımcı eşleşmesi" not in bn["_brifing_bloklar"](OLAY))
bn["katilimci_view"] = katilimci_view; GZ["a"] = True; n_kv = len(KV)
bak("gizli kipte hiçbir blok yok ve kayıt okunmaz", bn["_brifing_bloklar"](OLAY) == "" and len(KV) == n_kv); GZ["a"] = False
def patlak(*a, **y): raise RuntimeError("x")
bn["kapanis_view"] = patlak; bn["katilimci_view"] = patlak
bak("blok kurucusu hata verirse brifing durmaz (boş döner)", bn["_brifing_bloklar"](OLAY) == "")
bn.pop("kapanis_view"); bn.pop("katilimci_view")
bak("modül yüklü değilse (kapanış turu/kimlik bölümü yok) boş döner", bn["_brifing_bloklar"](OLAY) == "")
bak("brifing: _brifing_is paketten sonra blokları ekler", 'kisi += _brifing_bloklar(olay)' in k and k.index("kisi += _brifing_bloklar(olay)") < k.index("BRIFING_ISTEM[dl].format"))
bak("istemde kayıt kaynaklı açık işler önce yazılır (tr/en yönergesi)", "kaynağı «kayıt»" in k and "source «record»" in k)
print(f"\n{len(HATA)} hata" if HATA else "\nhepsi geçti"); sys.exit(1 if HATA else 0)
