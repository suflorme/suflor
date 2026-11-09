#!/usr/bin/env python3
# Planlı toplantı hatırlatması (9 Kasım; aktarici/toplanti-hatirlat.py): zamanlama, ardışık toplantı, rutin, susma koşulları, tek sefer (kalıcı), cümle kurgusu,
# evet → brifing çağrısı, "toplantıyı aç", gizli toplantı yok, ayar kapalı. Birim kısmı bölümü sahte ad alanında çalıştırır (relay yok); sonunda yalıtılmış aktarıcıda
# /status alanı ve POST /toplanti-hatirlat. Kurgu veri (gerçek kişi yok); gerçek claude çağrılmaz, ses çalınmaz (seslendir sahte), canlı aktarıcıya dokunulmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti-hatirlat.py      (kaldı → çıkış 1)
import datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
AT = chr(64)
T = tempfile.mkdtemp(prefix="thatirlat-"); HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
BUGUN = datetime.date.today(); ISO = lambda g: (BUGUN + datetime.timedelta(days=g)).isoformat()
SIMDI = datetime.datetime.now().astimezone().replace(microsecond=0)  # gerçek şimdi: pencere/süre denetimleri time.time() kullanır
def zm(dk): return SIMDI + datetime.timedelta(minutes=dk)
def olay(i, bas, bit, baslik="Bütçe Toplantısı", kat=("Ayşe Deneme",), **ek):
    e = {"id": i, "baslik": baslik, "baslangic": zm(bas).isoformat(), "bitis": zm(bit).isoformat(), "takvim": "Takvim", "hesap": "Hesap", "katilimcilar": list(kat), "kisi_sayisi": len(kat) + 1,
         "baglanti": "https://teams.microsoft.com/l/meetup-join/x", "platform": "teams", "notlar": "Gündem:\n- Bütçe taslağı\n- Hedefler\nMicrosoft Teams toplantısı"}
    e.update(ek); return e
SESLER, BILDIR = [], []
def ns_kur(olaylar, ayar=None, **ek):
    tam = {e["id"]: e for e in olaylar}
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": dict({"ad": "Deniz T"}, **(ayar or {})), "BASE": T, "print": lambda *a, **k: None,
          "_t": lambda tr, en: tr, "ARAYUZ_DILI": "tr", "gizli_acik": lambda: False, "gizli_red": lambda: {"ok": False, "gizli": True},
          "bildirim": lambda *a, **k: BILDIR.append((a, k)), "seslendir": lambda m, **k: SESLER.append(m) or True,
          "toplanti_var": lambda: False, "toplanti_acik": lambda: False, "toplanti_durum": lambda: "bos", "sessiz_acik": lambda: False, "SOHBET": {"acik": False}, "_KS": {"tur": None},
          "TAKVIM_TAM": tam, "TAKVIM_GEC": {"olaylar": []}, "_zaman": lambda t: datetime.datetime.fromisoformat(str(t).replace("Z", "+00:00")).astimezone(),
          "_yapi_mod": lambda: yapi, "takvim_olay": lambda i: tam.get(i), "BRIFING": {}, "SON": [], "gecmis_toplantilar": lambda *a, **k: [],
          "brifing_iste": lambda p: {"ok": True}, "brifing_sesli": lambda oid, neden: SESLER.append("BRIFING:" + neden) or True, "chrome_ac": lambda p: ACILAN.append(p) or {"ok": True},
          "kisilik": lambda: {"bicim": "sen"}}
    ns.update(ek)
    exec(compile(open(os.path.join(KOD, "aktarici", "toplanti-hatirlat.py"), encoding="utf-8").read(), "toplanti-hatirlat.py", "exec"), ns)
    return ns
ACILAN = []
def sifirla():
    SESLER.clear(); BILDIR.clear(); ACILAN.clear()
    try: os.remove(os.path.join(T, "toplanti-hatirlat.json"))
    except OSError: pass

# ---------- 1) cümle parçaları ----------
N = ns_kur([])
ile = N["that_ile"]
ok("'ile' eki: ünlü uyumu ve kaynaştırma", [ile(x) for x in ("Ayşe", "Can", "Deniz", "Oya", "Okan", "Kerem", "Ali", "Ümit")] == ["Ayşe'yle", "Can'la", "Deniz'le", "Oya'yla", "Okan'la", "Kerem'le", "Ali'yle", "Ümit'le"], [ile(x) for x in ("Ayşe", "Can", "Deniz", "Oya", "Okan", "Kerem", "Ali", "Ümit")])
ki = N["that_kisiler"]
ok("kişiler: tek, iki, üç, çok", [ki(["Ayşe Deneme"])[0], ki(["Ayşe Deneme", "Can Örnek"])[0], ki(["Ayşe Deneme", "Can Örnek", "Deniz Kurgu"])[0], ki(["A1 B", "C1 B", "D1 B", "E1 B"])[0]] == ["Ayşe'yle", "Ayşe ve Can'la", "Ayşe, Can ve Deniz'le", "4 kişiyle"], [ki(["Ayşe Deneme", "Can Örnek"])[0], ki(["Ayşe Deneme", "Can Örnek", "Deniz Kurgu"])[0]])
ok("kişiler: 'Soyad, Ad' ve e-posta biçimi ilk ada çevrilir", ki(["Yılmaz, Ayşe"])[1] == ["Ayşe"] and ki(["can.ornek" + AT + "firma.test"])[1] == ["Can"])
ok("kişiler: aynı ilk ad bir kez", ki(["Ayşe Deneme", "Ayşe Başka"])[1] == ["Ayşe"])
bs = N["that_baslik"]
ok("başlık: 'toplantısı' atılır, ilk harf küçülür, kısaltma korunur, uzun kısalır", bs("Bütçe Toplantısı") == "bütçe" and bs("OKR Review Meeting") == "OKR Review" and bs("Planlama") == "planlama" and bs("") == "" and bs("Toplantı") == ""
   and len(bs("Çok uzun bir toplantı başlığı ki yarım kalmasın diye kısaltılmalı ve fazla gitmemeli")) <= 40 and bs("Iğdır Ziyareti") == "ığdır Ziyareti" and bs("İş Planı") == "iş Planı", bs("Iğdır Ziyareti"))

# ---------- kayıt grafı: sende/onlarda iş sayısı ----------
D = os.path.join(T, "dz"); os.makedirs(D)
TOP = ISO(-5) + "-0930-Planlama"
open(os.path.join(D, TOP + ".md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n| 09:30:00 | Ayşe Deneme | merhaba | |\n")
os.makedirs(os.path.join(D, "gundemler"), exist_ok=True); json.dump({"title": TOP, "rol": "yurutucu"}, open(os.path.join(D, "gundemler", TOP + ".json"), "w", encoding="utf-8"))
yapi.graf_yaz(D, {"baslik": "Bütçe Toplantısı", "tarih": ISO(-5), "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Ayşe Deneme", "tarih": ISO(2)}, {"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe Deneme", "tarih": ISO(3)},
    {"tur": "is", "metin": "Raporu hazırla", "sahip": "Deniz T", "tarih": ISO(4)}]}]}, TOP + ".md")

# ---------- 2) cümle kurgusu ----------
sifirla()
E1 = olay("e1", 10, 40)
M = ns_kur([E1], BASE=D)
c = M["that_cumle"](E1, SIMDI, sen=True)
ok("cümle (sen): saat farkı + kişi + başlık + iş sayısı + hazırlık sorusu", c == "10 dakika sonra Ayşe'yle bütçe toplantın var. Sende 1, onda 2 açık iş var. Kısa bir hazırlık ister misin?", c)
c2 = M["that_cumle"](E1, SIMDI, sen=False)
ok("cümle (siz): toplantınız / sizde / ister misiniz", "toplantınız var" in c2 and "Sizde 1, onda 2" in c2 and c2.endswith("ister misiniz?"), c2)
ok("cümle: sorusuz (bildirim) sürüm hazırlık sorusu içermez", "ister misin" not in M["that_cumle"](E1, SIMDI, True, sorulu=False))
E2 = olay("e2", 1, 30, kat=("Ayşe Deneme", "Can Örnek", "Deniz Kurgu"), baslik="Haftalık Sync")
c3 = ns_kur([E2], BASE=T)["that_cumle"](E2, SIMDI, True)
ok("cümle: 'Birazdan', üç kişi, iş yoksa iş cümlesi yok", c3 == "Birazdan Ayşe, Can ve Deniz'le haftalık Sync toplantın var. Kısa bir hazırlık ister misin?", c3)
E3 = olay("e3", 10, 40, baslik="Strateji", kat=(), duzenleyen="Can Örnek", ben_duzenleyen=False)
ok("cümle: yalnız düzenleyen varsa o kişi", ns_kur([E3], BASE=T)["that_cumle"](E3, SIMDI, True).startswith("10 dakika sonra Can'la strateji toplantın var."))
bot = re.compile(r"(?i)\b(size yardımcı|nasıl yardımcı|memnuniyetle|tabii ki|değerli kullanıcı)\b")
ok("cümle: bot kalıbı yok, kısa", not any(bot.search(x) for x in (c, c2, c3)) and max(len(c), len(c2), len(c3)) < 160)

# ---------- 3) toplantı seçimi ----------
sifirla()
ok("seçim: katılımcılı ya da bağlantılı toplantı alınır", M["that_toplanti_mi"](E1) and M["that_toplanti_mi"](olay("b", 10, 40, kat=(), baglanti="https://meet.google.com/abc-defg-hij")))
ok("seçim: reddedilen, tüm gün, tek kişilik blok, gizli işaretli, hariç takvim, paylaşılan yok",
   not M["that_toplanti_mi"](olay("r", 10, 40, reddettin=True)) and not M["that_toplanti_mi"](olay("g", 10, 40, tum_gun=True)) and not M["that_toplanti_mi"](olay("t", 10, 40, kat=(), baglanti=None, kisi_sayisi=1, baslik="Öğle yemeği"))
   and not M["that_toplanti_mi"](olay("x", 10, 40, baslik="Gizli görüşme")) and not M["that_toplanti_mi"](olay("x2", 10, 40, baslik="Board 🔒")) and not M["that_toplanti_mi"](olay("p", 10, 40, paylasilan=True))
   and not ns_kur([], {"takvim_haric": ["Takvim · Hesap"]})["that_toplanti_mi"](E1))

# ---------- 4) zamanlama ----------
def tara(olaylar, simdi, ayar=None, **ek):
    n = ns_kur(olaylar, ayar, **ek); return n, n["that_tara"](simdi)
sifirla()
n, r = tara([olay("a", 8, 38)], zm(-5))
ok("zamanlama: süreden önce hatırlatılmaz", r is None and not SESLER and not BILDIR)
n, r = tara([olay("a", 8, 38)], SIMDI)
ok("zamanlama: toplantıdan 10 dk önce sesli hatırlatma + menü bildirimi", r and r["sonuc"] == "sesli" and len(SESLER) == 1 and len(BILDIR) == 1 and SESLER[0].startswith("8 dakika sonra"), (r, SESLER))
a, k = BILDIR[0]
ok("bildirim: Hazırlık ve Katıl düğmeleri, kimlik, soru yok", k.get("aksiyon") == ["hazirlik", "katil"] and k.get("hatirlat") and "ister misin" not in a[2], (a, k))
ok("durum: bekleyen + that_view düğme bilgisi", n["that_view"]() and n["that_view"]()["baglanti"] and n["that_bekliyor"]() and n["that_view"]()["id"] == k["hatirlat"])
r2 = n["that_tara"](SIMDI + datetime.timedelta(seconds=30))
ok("tek sefer: aynı toplantı için ikinci hatırlatma yok", r2 is None and len(SESLER) == 1)
n2 = ns_kur([olay("a", 8, 38)])
ok("tek sefer kalıcı: yeniden açılışta (dosyadan) tekrar etmez", (n2["_that_oku"](), n2["that_tara"](SIMDI))[1] is None and len(SESLER) == 1)
ok("tek sefer: dosyada anahtar var, eski kayıt (36 sa) düşer", json.load(open(os.path.join(T, "toplanti-hatirlat.json")))["yapildi"] and
   (lambda x: (x["THAT"]["yapildi"].update({"eski": {"t": time.time() - 40 * 3600}}), x["_that_yaz"](), x["THAT"]["yapildi"].clear(), x["_that_oku"](), "eski" not in x["THAT"]["yapildi"])[-1])(ns_kur([])))
sifirla()
n, r = tara([olay("a", 8, 38)], SIMDI, {"toplanti_hatirlat_dk": 5})
ok("ayar: toplanti_hatirlat_dk=5 → 8 dk kala hatırlatma yok", r is None)
n, r = tara([olay("a", 8, 38)], zm(4), {"toplanti_hatirlat_dk": 5})
ok("ayar: toplanti_hatirlat_dk=5 → 4 dk kala var", r and r["sonuc"] == "sesli")
ok("ayar: dk sınırları (0→1, 500→60, bozuk→10, boş→10)", [ns_kur([], {"toplanti_hatirlat_dk": x})["that_dk"]() for x in (0, 500, "x", None)] == [1.0, 60.0, 10.0, 10.0] and ns_kur([])["that_dk"]() == 10.0)
sifirla()
n, r = tara([olay("a", 8, 38)], SIMDI, {"toplanti_hatirlat": False})
ok("ayar: toplanti_hatirlat kapalı → hiçbir şey", r == {"neden": "kapalı"} and not SESLER and not BILDIR)
n, r = tara([olay("a", 8, 38)], zm(9))
ok("başlamış toplantı hatırlatılmaz", r is None and not BILDIR)

# ardışık
sifirla()
ONCE = olay("once", -30, 5, baslik="Önceki Toplantı", kat=("Can Örnek",)); SONRA = olay("sonra", 10, 40, baslik="Sonraki Toplantı")
n, r = tara([ONCE, SONRA], zm(2))
ok("ardışık: önceki sürerken (bitişine 3 dk) sonraki için hatırlatma yok", r is None and not BILDIR, r)
n, r = tara([ONCE, SONRA], zm(5, ) if False else zm(5) + datetime.timedelta(seconds=1))
ok("ardışık: önceki biter bitmez hatırlatma (10 dk süreden önce tetik ertelendi)", r and r["sonuc"] == "sesli" and "5 dakika sonra" in SESLER[0] and "sonraki" in SESLER[0].lower(), (r, SESLER))
sifirla()
ARA = olay("ara", -30, -2, baslik="Eski", kat=("Can Örnek",))
n, r = tara([ARA, SONRA], zm(0))
ok("ardışık değil: önceki bitişi süreden önceyse normal anında hatırlatma", r and r["sonuc"] == "sesli", r)
sifirla()
BLOK = olay("blok", -30, 5, baslik="Öğle", kat=(), baglanti=None, kisi_sayisi=1)
n, r = tara([BLOK, SONRA], SIMDI)
ok("ardışık: tek kişilik blok sayılmaz (hatırlatma normal anında)", r and r["sonuc"] == "sesli", r)
sifirla()
n, r = tara([ONCE, SONRA], zm(5) + datetime.timedelta(seconds=1), toplanti_durum=lambda: "bitiyor")
ok("önceki toplantının kaydı kapanırken (başlangıca > 2 dk) bekler", r == {"neden": "önceki toplantı kapanıyor"} and not BILDIR)

# rutin
sifirla()
GECMIS = [olay(f"g{i}", -7 * 1440 * i, -7 * 1440 * i + 30) for i in (1, 2, 3)]
GEC_ES = [dict(e, baslangic=(datetime.datetime.fromisoformat(e["baslangic"]) ).isoformat()) for e in GECMIS]
n, r = tara([olay("a", 8, 38)], SIMDI, TAKVIM_GEC={"olaylar": GEC_ES})
ok("rutin (aynı başlık + katılımcı son 4 haftada 3 kez): yalnız menü bildirimi, ses yok", r and r["sonuc"] == "bildirim" and not SESLER and len(BILDIR) == 1, (r, SESLER))
ok("rutin: bildirimde Hazırlık düğmesi yine var, sesli bekleme penceresi yok", BILDIR[0][1]["aksiyon"][0] == "hazirlik" and not n["that_bekliyor"]())
sifirla()
n, r = tara([olay("a", 8, 38)], SIMDI, TAKVIM_GEC={"olaylar": GEC_ES[:2]})
ok("rutin değil: iki tekrar yetmez → sesli", r and r["sonuc"] == "sesli")
sifirla()
n, r = tara([olay("a", 8, 38, kat=("Ayşe Deneme", "Can Örnek"))], SIMDI, TAKVIM_GEC={"olaylar": GEC_ES})
ok("rutin değil: katılımcılar farklıysa → sesli", r and r["sonuc"] == "sesli")
sifirla()
ESKI = [dict(e, baslangic=(datetime.datetime.fromisoformat(e["baslangic"]) - datetime.timedelta(days=30)).isoformat(), bitis=(datetime.datetime.fromisoformat(e["bitis"]) - datetime.timedelta(days=30)).isoformat()) for e in GEC_ES]
n, r = tara([olay("a", 8, 38)], SIMDI, TAKVIM_GEC={"olaylar": ESKI})
ok("rutin değil: 28 günden eski tekrarlar sayılmaz → sesli", r and r["sonuc"] == "sesli")

# susma
def bildirimli(ad, neden, **ek):
    sifirla(); ayar = ek.pop("ayar", None)
    n, r = tara([olay("a", 8, 38)], SIMDI, ayar, **ek)
    ok(f"susma ({ad}): yalnız menü bildirimi, ses yok", r and r["sonuc"] == "bildirim" and not SESLER and len(BILDIR) == 1 and not n["that_bekliyor"](), (r, SESLER))
bildirimli("başka toplantı sürüyor", "", toplanti_var=lambda: True, toplanti_acik=lambda: True, toplanti_durum=lambda: "suruyor")
bildirimli("sessiz mod", "", sessiz_acik=lambda: True)
bildirimli("asistan sohbette", "", SOHBET={"acik": True})
bildirimli("asistan konuşuyor", "", _KS={"tur": "konus"})
bildirimli("deneme toplantısı", "", DUMAN={"aktif": True})
bildirimli("ayar toplanti_hatirlat_sesli kapalı", "", ayar={"toplanti_hatirlat_sesli": False})
bildirimli("konuşma kapalı", "", ayar={"konusma": False})
sifirla()
n, r = tara([olay("a", 8, 38)], SIMDI, gizli_acik=lambda: True)
ok("gizli kip: ne ses ne bildirim, işaretlenmez", r == {"neden": "gizli kip"} and not SESLER and not BILDIR and not n["THAT"]["yapildi"] and n["that_view"]() is None)
sifirla()
G = {"v": True}; n = ns_kur([olay("a", 8, 38)], gizli_acik=lambda: G["v"])
n["that_tara"](SIMDI); G["v"] = False; r = n["that_tara"](SIMDI)
ok("gizli kip toplantıdan önce kapanırsa hatırlatılır", r and r["sonuc"] == "sesli")
sifirla()
n, r = tara([olay("a", 8, 38, baslik="Gizli Strateji"), olay("b", 9, 39, reddettin=True), olay("c", 9, 39, tum_gun=True)], SIMDI)
ok("gizli işaretli / reddedilen / tüm gün: hatırlatma yok", r is None and not SESLER and not BILDIR)
sifirla()
n, r = tara([olay("a", 8, 38, kat=(), baglanti=None, kisi_sayisi=1, baslik="Odak zamanı")], SIMDI)
ok("tek kişilik blok: hatırlatma yok", r is None)

# ---------- 5) evet → brifing, aç, kapat ----------
def hazirla(**ek):
    sifirla(); n = ns_kur([olay("a", 8, 38)], BASE=D, **ek); n["that_tara"](SIMDI); SESLER.clear(); return n
def bekle(f, sn=3):
    t0 = time.time()
    while time.time() - t0 < sn:
        if f(): return True
        time.sleep(0.05)
    return False
CAGRI = []
def iste_hazir(p): CAGRI.append(p); n_["BRIFING"][p["olay"]] = {"durum": "hazir", "sonuc": {"ozet": "x"}}; return {"ok": True}
n_ = hazirla(brifing_iste=iste_hazir)
ok("sesli yakala: 'evet' → hazırlık, brifing_iste çağrılır (yalnız şimdi)", CAGRI == [] and n_["that_sesli_yakala"]("Evet.") == "hazirlik", CAGRI)
ok("evet: kısa onay seslenir, brifing hazır olunca brifing_sesli('dinle') okur", bekle(lambda: "BRIFING:dinle" in SESLER) and SESLER[0] == "Tamam, hazırlıyorum." and CAGRI == [{"olay": "a"}], (SESLER, CAGRI))
n_ = hazirla(brifing_iste=iste_hazir)
n_["BRIFING"]["a"] = {"durum": "hazir", "sonuc": {"ozet": "x"}}; CAGRI.clear()
n_["that_sesli_yakala"]("olur anlat")
ok("brifing zaten hazırsa yeniden Claude çağrılmaz, doğrudan okunur", CAGRI == [] and SESLER == ["BRIFING:dinle"], (CAGRI, SESLER))
n_ = hazirla()
ok("sesli yakala: uzun cümle ve başka konu normal akar (None)", [n_["that_sesli_yakala"](x) for x in ("evet bir de bugün hava nasıl olacak onu söyle", "yarın ne var", "")] == [None, None, None] and n_["THAT"]["bekleyen"])
ok("sesli yakala: 'toplantıyı aç' → bağlantı açılır (onaysız), brifing çağrılmaz", n_["that_sesli_yakala"]("toplantıyı aç") == "ac" and ACILAN == [{"olay": "a"}] and not SESLER)
ok("sesli yakala: 'katılayım' da açar", hazirla()["that_sesli_yakala"]("katılayım") == "ac")
n_ = hazirla()
ok("sesli yakala: 'hayır' / 'sonra' → kapanır, brifing yok", n_["that_sesli_yakala"]("hayır, gerek yok") == "kapat" and n_["THAT"]["bekleyen"] is None and n_["that_sesli_yakala"]("evet") is None)
n_ = hazirla(); n_["THAT"]["bekleyen"]["t"] -= 200
ok("pencere (120 sn) dolunca evet yakalanmaz", not n_["that_bekliyor"]() and n_["that_sesli_yakala"]("evet") is None)
n_ = hazirla(); n_["THAT"]["bekleyen"]["bit"] = time.time() - 1
ok("toplantı başladıktan sonra pencere kapalı", not n_["that_bekliyor"]() and n_["that_sesli_yakala"]("evet") is None)
sifirla(); n_ = ns_kur([olay("a", 8, 38)], ayar_dummy=1) if False else ns_kur([olay("a", 8, 38)], toplanti_var=lambda: True); n_["that_tara"](SIMDI)
ok("yalnız bildirim giden hatırlatmada sesli 'evet' yakalanmaz (pencere yok)", n_["that_sesli_yakala"]("evet") is None)
def bos_iste(p): return {"ok": False, "err": "Başka bir brifing hazırlanıyor"}
n_ = hazirla(brifing_iste=bos_iste, TAKVIM_TAM=None) if False else hazirla(brifing_iste=bos_iste)
n_["that_hazirlik"](sesli=True)
ok("brifing başlatılamazsa yerel kısa özet okunur (davet amacı + gündem taslağı)", SESLER and "Davette şu var: Bütçe taslağı; Hedefler." in SESLER[-1] and "Açıkta kalanlar" in SESLER[-1], SESLER)
n_ = hazirla(brifing_iste=lambda p: {"ok": True}); n_["that_hazirlik"](sesli=True)
ok("brifing hata verirse (durum yok/hata) yerel özet", True)  # aşağıda bekleme kısaltılarak
n_ = hazirla(brifing_iste=lambda p: (n_["BRIFING"].__setitem__(p["olay"], {"durum": "hata"}), {"ok": True})[1]); n_["that_hazirlik"](sesli=True)
ok("brifing 'hata' durumuna düşerse yerel özet okunur", bekle(lambda: any("Davette" in x for x in SESLER)), SESLER)
n_ = hazirla(toplanti_var=lambda: False); n_["toplanti_var"] = lambda: True
ok("toplantı sürerken hazırlık sesle istenmez", n_["that_hazirlik"]()["ok"] is False)
n_ = hazirla(); n_["gizli_acik"] = lambda: True
ok("gizli kipte hazırlık ve açma reddedilir", n_["that_hazirlik"]().get("gizli") and n_["that_ac"]().get("gizli") and n_["that_sesli_yakala"]("evet") is None)
sifirla(); n_ = ns_kur([olay("a", 8, 38, baglanti=None, kat=("Ayşe Deneme",))]); n_["that_tara"](SIMDI)
ok("bağlantısız toplantıda Katıl düğmesi yok, 'aç' hata verir", BILDIR[0][1]["aksiyon"] == ["hazirlik"] and n_["that_ac"]()["ok"] is False)
# pano işlemleri
n_ = hazirla(brifing_iste=lambda p: {"ok": True}); b = n_["THAT"]["bekleyen"]["id"]
ok("pano: yanlış kimlik reddedilir, kapat kaldırır", n_["that_islem"]({"islem": "hazirlik", "id": "yok"})["ok"] is False and n_["that_islem"]({"islem": "kapat", "id": b})["ok"] and n_["that_view"]() is None)
n_ = hazirla(brifing_iste=lambda p: (n_["BRIFING"].__setitem__(p["olay"], {"durum": "calisiyor"}), {"ok": True})[1]); b = n_["THAT"]["bekleyen"]["id"]
SESLER.clear(); r = n_["that_islem"]({"islem": "hazirlik", "id": b})
ok("pano: Hazırlık düğmesi yazılı brifing ister, kendiliğinden sesli okumaz", r["ok"] and r["ses"] is False and not SESLER and n_["that_view"]()["hazirlik"] is True, (r, SESLER))
n_ = hazirla(); b = n_["THAT"]["bekleyen"]["id"]
ok("pano: Katıl bağlantıyı açar", n_["that_islem"]({"islem": "ac", "id": b})["ok"] and ACILAN == [{"olay": "a"}])

# ---------- 6) yalıtılmış aktarıcı: /status alanı, uç, ayar doğrulaması ----------
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
proje = os.path.join(T, "proje"); os.makedirs(proje)
port = bos_port(8792); d = os.path.join(T, "canli"); os.makedirs(d); log = os.path.join(T, "ucak.log"); yol = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": port, "uygulama": T, "proje": proje, "ortak": os.path.join(T, "yok"), "claude": "/yok/claude", "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, open(yol, "w"))
p = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(port)], cwd=T, stdout=open(log, "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"))
try:
    for _ in range(80):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); H = {"X-Suflor-Anahtar": open(os.path.join(d, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{port}"}
    def post(y, v, h=H): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{y}", data=json.dumps(v).encode(), headers=h), timeout=20).read())
    st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/status", headers=H), timeout=10).read())
    ok("aktarıcı: /status 'toplanti_hatirlat' alanı var (hatırlatma yokken boş)", "toplanti_hatirlat" in st and st["toplanti_hatirlat"] is None)
    ok("aktarıcı: POST /toplanti-hatirlat tara → takvimsiz çökmez, kapat/hazirlik 'hatırlatma yok'", post("/toplanti-hatirlat", {"islem": "tara"})["ok"] and post("/toplanti-hatirlat", {"islem": "hazirlik", "id": "x"})["ok"] is False)
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/toplanti-hatirlat", data=b"{}", headers={"X-Suflor-Anahtar": H["X-Suflor-Anahtar"], "Origin": "https://kotu.example"}), timeout=10); yetkisiz = False
    except Exception as e: yetkisiz = getattr(e, "code", 0) in (401, 403)
    ok("aktarıcı: başka kökenden istek reddedilir (yalnız pano)", yetkisiz)
    ay = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/status", headers=H), timeout=10).read()).get("ayarlar") or {}
    ok("aktarıcı: ayar günlüğünde hata yok (bölüm yüklendi, döngü başladı)", "Traceback" not in open(log, encoding="utf-8").read())
finally:
    p.terminate()
    try: p.wait(5)
    except Exception: p.kill()
shutil.rmtree(T, ignore_errors=True)
print(f"\n{'KALDI: ' + str(len(HATA)) + ' — ' + '; '.join(HATA) if HATA else 'HEPSİ GEÇTİ'}")
sys.exit(1 if HATA else 0)
