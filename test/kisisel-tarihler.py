#!/usr/bin/env python3
# Yaklaşan kişisel tarihler (S243; aktarici/kisisel-tarihler.py, takvim.swift --tarihler, relay /yaklasan-tarihler): sahte yardımcı çıktısı, izinsiz hâl, tekilleştirme,
# tarih sınırları (29 Şubat, yıl geçişi), yoksay, kutlama taslağı (gönderim yok), hatırlatma zamanı, sesle "doğum gününü hatırlat". Swift çağrılmaz; yapay adlar, ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisisel-tarihler.py
import os, re, sys, json, time, datetime, tempfile, urllib.parse, subprocess, threading
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
oku = lambda *y: open(os.path.join(KOD, *y), encoding="utf-8").read()
EP = lambda k: k + chr(64) + "ornek.test"
D = datetime.date
tmp = tempfile.mkdtemp(); bild = []; sesli = []; acilan = []
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "urllib": urllib, "subprocess": subprocess, "AYAR": {}, "BASE": tmp, "_t": lambda tr, en: tr,
      "bildirim": lambda *a, **k: bild.append(a[2]), "seslendir": lambda m, **k: sesli.append(m), "toplanti_var": lambda: False, "gizli_acik": lambda: False,
      "SOHBET": {"acik": False}, "eposta_tur": lambda: "mailto", "eposta_ben": lambda: EP("ben"), "kisi_eposta": lambda ad: EP("ayse") if "Ayşe" in ad else None}
exec(compile(oku("aktarici", "kisisel-tarihler.py"), "kisisel-tarihler.py", "exec"), ns)
class _SabitTarih(datetime.date):  # modülün "bugün"ü testin sabit günü (6 Kasım 2026): gerçek tarihe bağlı kalan taslak/yoksay sınamaları günle bozulmasın
    @classmethod
    def today(cls): return D(2026, 11, 6)
class _SabitDt(datetime.datetime):
    @classmethod
    def now(cls, tz=None): return datetime.datetime(2026, 11, 6, 12, 0)
ns["datetime"] = type("dt", (), {"date": _SabitTarih, "datetime": _SabitDt, "timedelta": datetime.timedelta, "time": datetime.time, "timezone": datetime.timezone})
H = lambda g, **k: dict({"durum": "ok", "izinler": {"kisiler": True, "takvim": True, "animsaticilar": True}, "kisiler": [], "dogum_takvimi": [], "suflor": [], "etkinlikler": [], "animsaticilar": []}, **k)
hes = lambda ham, bugun, ufuk=14, y=None: ns["kt_hesapla"](ham, bugun, ufuk, y)
# --- pencere ve yinelenme
b = D(2026, 11, 6)
l = hes(H(0, kisiler=[{"ad": "Ayşe Yılmaz", "dogum": {"ay": 11, "gun": 8, "yil": 1990}, "tarihler": []}]), b)
kontrol(f"doğum günü: pencere içinde, yaş metinde, biçim tarih/tur/metin/kisi: {l}", len(l) == 1 and set(l[0]) == {"tarih", "tur", "metin", "kisi"} and l[0]["tarih"] == "2026-11-08" and l[0]["tur"] == "dogum_gunu" and "36. yaş" in l[0]["metin"] and l[0]["kisi"] == "Ayşe Yılmaz")
kontrol("bugün dahil, ufuk son günü dahil, ufuktan sonrası yok", [x["tarih"] for x in hes(H(0, kisiler=[{"ad": "A B", "dogum": {"ay": 11, "gun": 6}}, {"ad": "C D", "dogum": {"ay": 11, "gun": 20}}, {"ad": "E F", "dogum": {"ay": 11, "gun": 21}}]), b)] == ["2026-11-06", "2026-11-20"])
kontrol("dün geçti → bu yıl değil, ufukta da yok", hes(H(0, kisiler=[{"ad": "A B", "dogum": {"ay": 11, "gun": 5}}]), b) == [])
l = hes(H(0, kisiler=[{"ad": "Yıl Geçişi", "dogum": {"ay": 1, "gun": 3, "yil": 2000}}]), D(2026, 12, 25))
kontrol(f"yıl geçişi: 25 Aralık'ta 3 Ocak ertesi yıl bulunur, yaş ertesi yıla göre: {l}", len(l) == 1 and l[0]["tarih"] == "2027-01-03" and "27. yaş" in l[0]["metin"])
kontrol("29 Şubat: artık olmayan yılda 28 Şubat, artık yılda 29 Şubat", [x["tarih"] for x in hes(H(0, kisiler=[{"ad": "Artık Gün", "dogum": {"ay": 2, "gun": 29, "yil": 2000}}]), D(2027, 2, 20))] == ["2027-02-28"]
        and [x["tarih"] for x in hes(H(0, kisiler=[{"ad": "Artık Gün", "dogum": {"ay": 2, "gun": 29, "yil": 2000}}]), D(2028, 2, 20))] == ["2028-02-29"])
kontrol("29 Şubat doğumlu: 29 Aralık'ta ufuk 90 gün → ertesi yıl 28 Şubat (artık olmayan) pencere dışı, 1 Mart'a taşmaz", hes(H(0, kisiler=[{"ad": "Artık Gün", "dogum": {"ay": 2, "gun": 29}}]), D(2026, 12, 29), 30) == [])
kontrol("geçersiz tarih (31 Nisan) çökmez, atlanır", hes(H(0, kisiler=[{"ad": "Bozuk", "dogum": {"ay": 4, "gun": 31}}]), b) == [])
kontrol("yılsız doğum günü: yaş yok", "yaş" not in hes(H(0, kisiler=[{"ad": "Yılsız", "dogum": {"ay": 11, "gun": 7}}]), b)[0]["metin"])
l = hes(H(0, kisiler=[{"ad": "Çift Yıl", "dogum": {"ay": 11, "gun": 7, "yil": 1604}}]), b)
kontrol("yer tutucu yıl (1604) yaş üretmez", len(l) == 1 and "yaş" not in l[0]["metin"])
# --- diğer kaynaklar ve tekilleştirme
ham = H(0, kisiler=[{"ad": "Ayşe Yılmaz", "dogum": {"ay": 11, "gun": 8, "yil": 1990}, "tarihler": [{"etiket": "evlilik yıldönümü", "yildonumu": True, "ay": 11, "gun": 12}]}],
        dogum_takvimi=[{"baslik": "Ayşe Yılmaz'ın doğum günü", "tarih": "2026-11-08"}, {"baslik": "Veli Kara's Birthday", "tarih": "2026-11-09"}],
        suflor=[{"baslik": "Ali'yi ara", "tarih": "2026-11-07", "saat": "10:30"}], animsaticilar=[{"baslik": "Ali'yi ara", "tarih": "2026-11-07"}, {"baslik": "Vergi", "tarih": "2026-11-10", "saat": "09:00"}],
        etkinlikler=[{"baslik": "Şirket pikniği", "tarih": "2026-11-11"}])
l = hes(ham, b)
kontrol(f"aynı kişi Kişiler + doğum günleri takvimi → tek satır: {[ (x['tarih'], x['tur']) for x in l]}", [x["kisi"] for x in l if x["tur"] == "dogum_gunu"].count("Ayşe Yılmaz") == 1)
kontrol("takvim başlığından ad çıkar (Türkçe ek ve İngilizce)", any(x["kisi"] == "Veli Kara" and x["tarih"] == "2026-11-09" for x in l))
kontrol("yıldönümü ayrı tür, etiketle", any(x["tur"] == "yildonumu" and x["tarih"] == "2026-11-12" and "evlilik yıldönümü" in x["metin"] for x in l))
kontrol("Suflor hatırlatması + aynı başlıklı Anımsatıcı tek satır (saatli olan kalır)", [x["metin"] for x in l if x["tur"] == "hatirlatma" and x["tarih"] == "2026-11-07"] == ["Ali'yi ara (10:30)"])
kontrol("Anımsatıcı saatli, tüm gün etkinliği etkinlik türünde", any(x["metin"] == "Vergi (09:00)" for x in l) and any(x["tur"] == "etkinlik" and x["metin"] == "Şirket pikniği" for x in l))
kontrol("sıralama tarihe göre", [x["tarih"] for x in l] == sorted(x["tarih"] for x in l))
kontrol("yoksay anahtarıyla kayıt düşer", all(x["kisi"] != "Ayşe Yılmaz" or x["tur"] != "dogum_gunu" for x in hes(ham, b, 14, {"2026-11-08|dogum_gunu|ayse yilmaz"})))
# --- uç: izinsiz hal, kapalı, ufuk
cagri = []
def yardimci(yanit):
    def f(args, istek=None): cagri.append(list(args)); return yanit
    return f
os.environ["SUFLOR_TEST_BASLAT"] = "1"; os.environ["SUFLOR_TEST_TARIH"] = "1"
ns["_takvim_yardimci"] = yardimci({"durum": "izin_yok", "hata": "izin yok"}); ns["_KT"].update(t=0, ham=None)
v = ns["kt_view"](True, b); kontrol(f"izin yok: ok true, izin false, boş liste, çökmez: {v}", v["ok"] is True and v["izin"] is False and v["tarihler"] == [] and "ufuk" in v)
ns["_takvim_yardimci"] = yardimci({"durum": "hata", "hata": "Suflor Takvim.app yok"}); v = ns["kt_view"](True, b)
kontrol("yardımcı yok → izin false, hata metni, çökmez", v["ok"] and v["izin"] is False and v["tarihler"] == [])
ns["_takvim_yardimci"] = yardimci(H(0, izinler={"kisiler": False, "takvim": True, "animsaticilar": False}, etkinlikler=[{"baslik": "Piknik", "tarih": "2026-11-08"}]))
v = ns["kt_view"](True, b); kontrol("kısmi izin: izin true, izinler ayrı, okunanlar gelir", v["izin"] is True and v["izinler"] == {"kisiler": False, "takvim": True, "animsaticilar": False} and len(v["tarihler"]) == 1)
ns["_takvim_yardimci"] = yardimci(ham); n = len(cagri); v = ns["kt_view"](True, b); ns["kt_view"](False, b)
kontrol("önbellek: ikinci çağrıda yardımcı yeniden çalışmaz; ufuk ayarı --tarihler'e gider", len(cagri) == n + 1 and cagri[-1] == ["--tarihler", "14"])
ns["AYAR"]["kisisel_tarih_ufuk"] = 30; ns["kt_view"](False, b); kontrol("ufuk ayarı değişince yeniden okur", cagri[-1] == ["--tarihler", "30"] and ns["kt_view"](False, b)["ufuk"] == 30)
ns["AYAR"]["kisisel_tarih_ufuk"] = 9999; kontrol("ufuk 1–90 ile sınırlı", ns["kt_ufuk"]() == 90); ns["AYAR"]["kisisel_tarih_ufuk"] = "x"; kontrol("bozuk ufuk → 14", ns["kt_ufuk"]() == 14); ns["AYAR"].clear()
ns["AYAR"]["kisisel_tarihler"] = False; n = len(cagri); v = ns["kt_view"](True, b); kontrol("ayar kisisel_tarihler: false → kapalı, yardımcı çağrılmaz", v.get("kapali") and v["tarihler"] == [] and len(cagri) == n); ns["AYAR"].clear()
ns["_takvim_yardimci"] = yardimci(ham); ns["_KT"].update(t=0, ham=None, ufuk=0)
# --- yoksay + taslak
v = ns["kt_view"](True, b); r = ns["kt_islem"]({"islem": "taslak", "tarih": "2026-11-08", "kisi": "Ayşe Yılmaz"})
kontrol(f"taslak: doğum günü için, alıcı bulundu, gönderim yok (yalnız taslak açılır): {r}", r.get("ok") and r.get("alici") is True and r.get("kanal") == "eposta")
u, adres, kanal = ns["kt_taslak_url"]("Ayşe Yılmaz"); kontrol("e-posta taslağı: alıcı e-postası adreste, metin kutlama; mailto", u.startswith("mailto:" + urllib.parse.quote(EP("ayse"))) and "Do%C4%9Fum" in u and kanal == "eposta")
u, adres, kanal = ns["kt_taslak_url"]("Veli Kara", "teams"); kontrol("Teams taslağı: sohbet bağlantısı, alıcısız da açılır", u.startswith("https://teams.microsoft.com/l/chat/0/0?users=&message=") and adres is None and kanal == "teams")
kontrol("taslak: doğum günü olmayan kayıt için reddedilir", ns["kt_islem"]({"islem": "taslak", "tarih": "2026-11-12", "kisi": "Ayşe Yılmaz"})["ok"] is False)
kontrol("taslak: kötü biçimli istek reddedilir", ns["kt_islem"]({"islem": "taslak", "tarih": "yarın"})["ok"] is False and ns["kt_islem"]({"islem": "gonder", "tarih": "2026-11-08"})["ok"] is False)
ns["toplanti_var"] = lambda: True; kontrol("toplantıda taslak açılmaz", ns["kt_islem"]({"islem": "taslak", "tarih": "2026-11-08", "kisi": "Ayşe Yılmaz"}).get("err") == "toplantida"); ns["toplanti_var"] = lambda: False
ns["gizli_acik"] = lambda: True; kontrol("gizli kipte taslak yok", ns["kt_islem"]({"islem": "taslak", "tarih": "2026-11-08", "kisi": "Ayşe Yılmaz"})["ok"] is False); ns["gizli_acik"] = lambda: False
kontrol("yoksay: kayıt bir daha listelenmez, dosyaya yazılır (0600)", ns["kt_islem"]({"islem": "yoksay", "tarih": "2026-11-08", "kisi": "Ayşe Yılmaz"})["ok"] and
        all(not (x["tur"] == "dogum_gunu" and x["kisi"] == "Ayşe Yılmaz") for x in ns["kt_view"](False, b)["tarihler"]) and oct(os.stat(os.path.join(tmp, "kisisel-tarihler.json")).st_mode)[-3:] == "600")
kontrol("yoksay: olmayan kayıt reddedilir", ns["kt_islem"]({"islem": "yoksay", "tarih": "2026-11-08", "kisi": "Kimse"})["ok"] is False)
# --- hatırlatma: bir gün önce ve sabah
ns["gelistirici_mi"] = lambda: True  # geliştirici kurulumu: ayar yoksa 09:00 (eski davranış); beta davranışı aşağıda ayrıca sınanır
ns["_KT"].update(yoksay=None); os.remove(os.path.join(tmp, "kisisel-tarihler.json")); ns["_KT"]["yoksay"] = None
simdi = datetime.datetime(2026, 11, 7, 9, 30); bild.clear(); ns["_KT"].update(t=0, ham=None)
n = ns["kt_hatirlat_tur"](simdi); kontrol(f"bir gün önce: yarınki doğum günü + bugünkü hatırlatma (2 bildirim; etkinlik yok): {bild}", n == 2 and any(c.startswith("Yarın: Ayşe") for c in bild) and any(c.startswith("Bugün: Ali'yi ara") for c in bild) and not any("piknik" in c.lower() for c in bild))
kontrol("aynı hatırlatma ikinci kez gitmez", ns["kt_hatirlat_tur"](simdi) == 0 and len(bild) == 2)
# --- tek söz kapısı (aktarici/soz-kapisi.py) ile: öncelik 2 (mesai beklemez; sessiz mod, toplantı, gece geçerli), kayıtta kişi adı yok, sonuç kaydı
_KTD = os.path.join(tmp, "kisisel-tarihler.json"); _kt_once = open(_KTD, "rb").read() if os.path.exists(_KTD) else None
os.environ["SUFLOR_TEST_SOZ_DONGU_YOK"] = "1"; _sz = datetime.datetime(2026, 11, 7, 9, 30).timestamp(); _sol = {"sessiz": False}
def kapi_yukle():
    for k in [k for k in ns if k.startswith(("soz", "SOZ", "_soz")) and k != "_soz_sonuc_g"]: del ns[k]
    for f_ in ("soz.jsonl", "soz-kuyruk.json"):
        try: os.remove(os.path.join(tmp, f_))
        except OSError: pass
    ns.update(threading=threading, LOCK=threading.Lock(), write=lambda pairs: [open(y, "a", encoding="utf-8").write(m) for y, m in pairs], sessiz_acik=lambda: _sol["sessiz"], aktif_dosya=lambda: None,
              calisma_saatleri=lambda: ({0, 1, 2, 3, 4}, 540, 1080), SOZ_SAAT=lambda: _sz); ns["AYAR"]["soz_aralik_dk"] = 0
    exec(compile(oku("aktarici", "soz-kapisi.py"), "soz-kapisi.py", "exec"), ns)
sj = lambda: [json.loads(l) for l in open(os.path.join(tmp, "soz.jsonl"), encoding="utf-8") if l.strip()]
ns["_KT"]["bildirilen"] = {}; bild.clear(); kapi_yukle(); n = ns["kt_hatirlat_tur"](simdi)
kontrol("kapı: hatırlatmalar kapıdan geçer (cumartesi mesai dışı ama öncelik 2 beklemez), kayıtta kaynak/öncelik var, kişi adı yok",
        n == 2 and len(bild) == 2 and [(x["kaynak"], x["oncelik"], x["karar"]) for x in sj()] == [("kisisel_tarih", 2, "simdi")] * 2 and "Ayşe" not in open(os.path.join(tmp, "soz.jsonl"), encoding="utf-8").read())
ns["_KT"]["bildirilen"] = {}; bild.clear(); _sol["sessiz"] = True; kapi_yukle(); n = ns["kt_hatirlat_tur"](simdi)
kontrol("kapı: sessiz modda söz bekler (bildirilmez, işaretlenmez), mod kalkınca dakikalık tur teslim eder",
        n == 0 and not bild and ns["soz_view"]()["kuyruk"] == 2 and (_sol.update(sessiz=False) or ns["soz_tur"]()["teslim"] == 2) and len(bild) == 2 and len(ns["_KT"]["bildirilen"]) == 2)
ns["_KT"]["bildirilen"] = {}; bild.clear(); ns["toplanti_var"] = lambda: True; kapi_yukle()
kontrol("kapı: toplantıdayken söz bekler", ns["kt_hatirlat_tur"](simdi) == 0 and not bild and ns["soz_view"]()["kuyruk"] == 2); ns["toplanti_var"] = lambda: False
kapi_yukle(); ns["_KT"]["bildirilen"] = {}; bild.clear(); ns["kt_hatirlat_tur"](simdi); _yk = ns["kt_islem"]({"islem": "yoksay", "tarih": "2026-11-08", "kisi": "Ayşe Yılmaz"})
kontrol("kapı: yoksay düğmesi → sonuç ret (kaynak kisisel_tarih)", _yk.get("ok") is True and sj()[-1]["olay"] == "sonuc" and sj()[-1]["sonuc"] == "ret" and sj()[-1]["kaynak"] == "kisisel_tarih")
for k in [k for k in ns if k.startswith(("soz", "SOZ", "_soz")) and k != "_soz_sonuc_g"]: del ns[k]  # sonraki bölümler kapısız (eski) yolu sınar
(open(_KTD, "wb").write(_kt_once) if _kt_once is not None else (os.path.exists(_KTD) and os.remove(_KTD))); ns["_KT"]["yoksay"] = None; ns["_KT"]["bildirilen"] = {}; bild.clear()  # yoksay işlemi önceki duruma döner
ns["_KT"].update(yoksay=None, bildirilen=None); os.remove(os.path.join(tmp, "kisisel-tarihler.json")); ns["_KT"]["yoksay"] = None; bild.clear()
kontrol("günün sabahı: saatten önce sessiz", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 8, 59)) == 0)
n = ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 0)); kontrol(f"günün sabahı 09:00'da 'Bugün: …doğum günü': {bild}", n >= 1 and any(c.startswith("Bugün: Ayşe") for c in bild))
kontrol("sesli ayar kapalıyken sesli okuma yok", not sesli); ns["AYAR"]["kisisel_tarih_sesli"] = True; ns["_KT"]["bildirilen"] = {}; ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 5)); kontrol("sesli açık: kısa sesli okunur", len(sesli) >= 1)
sesli.clear(); bild.clear(); ns["_KT"]["bildirilen"] = {}; ns["toplanti_var"] = lambda: True; kontrol("toplantıdayken hatırlatma yok (bildirilmez, sonra denenir)", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 5)) == 0 and not bild and not sesli); ns["toplanti_var"] = lambda: False
ns["gizli_acik"] = lambda: True; kontrol("gizli toplantıda hatırlatma yok", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 5)) == 0); ns["gizli_acik"] = lambda: False
ns["AYAR"]["kisisel_tarih_hatirlat"] = False; kontrol("ayar kisisel_tarih_hatirlat: false kapatır", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 5)) == 0); ns["AYAR"].clear()
# beta varsayılanı: ayar girilmemişse saat boş, bildirim yok; liste ve sesle hatırlat sürer; saat girilince çalışır; geliştiricide 09:00
ns["AYAR"].clear(); ns["gelistirici_mi"] = lambda: False; ns["_KT"]["bildirilen"] = {}; bild.clear(); ns["toplanti_var"] = lambda: False
kontrol("beta, ayar yok: _kt_saat() None", ns["_kt_saat"]() is None)
kontrol("beta, ayar yok: saatli hatırlatma bildirimi yok (bir gün önce de sabah da)", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 7, 9, 30)) == 0 and ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 30)) == 0 and not bild)
ns["AYAR"]["kisisel_tarih_saat"] = "  "; kontrol("beta, boşluk/boş ayar da boş sayılır", ns["_kt_saat"]() is None); ns["AYAR"].clear()
kontrol("beta: tarihler listede görünmeye devam eder (kt_hesapla)", len(hes(H(0, kisiler=[{"ad": "Ayşe Yılmaz", "dogum": {"ay": 11, "gun": 8, "yil": 1990}}]), D(2026, 11, 7))) == 1)
kontrol("beta: sesle 'doğum gününü hatırlat' takvim saatinde 09:00'a döner (kullanıcının açık isteği)", ns["_kt_saat"](True) == (9, 0))
ns["AYAR"]["kisisel_tarih_saat"] = "08:15"; ns["_KT"]["bildirilen"] = {}; kontrol("beta, saat girilince hatırlatma çalışır", ns["_kt_saat"]() == (8, 15) and ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 8, 20)) >= 1 and bool(bild)); ns["AYAR"].clear()
ns["gelistirici_mi"] = lambda: True; kontrol("geliştirici, ayar yok: 09:00 (eski davranış değişmedi)", ns["_kt_saat"]() == (9, 0))
ns["_KT"]["bildirilen"] = {}; bild.clear(); kontrol("geliştirici, ayar yok: 09:00'da hatırlatma gider", ns["kt_hatirlat_tur"](datetime.datetime(2026, 11, 8, 9, 0)) >= 1 and bool(bild)); ns["_KT"]["bildirilen"] = {}; bild.clear()
ns["AYAR"]["kisisel_tarih_saat"] = "07:30"; kontrol("hatırlatma saati ayarı", ns["_kt_saat"]() == (7, 30)); ns["AYAR"]["kisisel_tarih_saat"] = "zz"; kontrol("bozuk saat → 09:00", ns["_kt_saat"]() == (9, 0)); ns["AYAR"].clear()
# --- Konuş bağlamı
ns["_KT"].update(t=0, ham=None, yoksay=None); bag = ns["kisisel_tarih_baglam"]("bu hafta kimin doğum günü var")
kontrol("Konuş: doğum günü sorusunda tarih listesi bağlama eklenir", "Yaklaşan kişisel tarihler" in bag and "Ayşe Yılmaz" in bag)
kontrol("Konuş: 'yarın neyi unutmamalıyım' eşleşir; ilgisiz soruda boş", "Yaklaşan" in ns["kisisel_tarih_baglam"]("yarın neyi unutmamalıyım") and ns["kisisel_tarih_baglam"]("toplantı özeti ver") == "")
ns["gizli_acik"] = lambda: True; kontrol("Konuş: gizli toplantıda bağlam yok", ns["kisisel_tarih_baglam"]("kimin doğum günü var") == ""); ns["gizli_acik"] = lambda: False
ns["_takvim_yardimci"] = yardimci({"durum": "izin_yok", "hata": "x"}); ns["_KT"].update(t=0, ham=None); kontrol("Konuş: izin yoksa kullanıcıya izni söyletir", "izni yok" in ns["kisisel_tarih_baglam"]("doğum günü var mı")); ns["_takvim_yardimci"] = yardimci(ham)
# --- sesle hatırlat
ham2 = H(0, kisiler=[{"ad": "Ayşe Yılmaz", "dogum": {"ay": 3, "gun": 14, "yil": 1990}}, {"ad": "Ayşe Kaya", "dogum": {"ay": 5, "gun": 1}}, {"ad": "Veli Kara", "dogum": {"ay": 11, "gun": 9}}, {"ad": "Ali Düz", "dogum": None}])
ns["_KT"].update(t=time.time(), ham=ham2, ufuk=14)
for s_, beklenen in (("Veli'nin doğum gününü hatırlat", "Veli Kara"), ("Veli Kara'nın doğum gününü bana hatırlat", "Veli Kara"), ("Claude, Veli'nin doğum gününü hatırlat", "Veli Kara")):
    r = ns["kt_sesli_hatirlat"](s_, b, ham2); kontrol(f"sesle hatırlat: {s_!r} → {r}", r == (f"{beklenen} — doğum günü", "2026-11-09T09:00"))
r = ns["kt_sesli_hatirlat"]("Ayşe Yılmaz'ın doğum gününü hatırlat", b, ham2); kontrol("tam adla belirsizlik çözülür; pencere dışı (yarım yıl sonra) da bulunur", r == ("Ayşe Yılmaz — doğum günü", "2027-03-14T09:00"))
kontrol("ad belirsiz (iki Ayşe) → None (Claude'a gider)", ns["kt_sesli_hatirlat"]("Ayşe'nin doğum gününü hatırlat", b, ham2) is None)
kontrol("Kişiler'de yok / doğum günü kaydı yok → None", ns["kt_sesli_hatirlat"]("Kimse'nin doğum gününü hatırlat", b, ham2) is None and ns["kt_sesli_hatirlat"]("Ali'nin doğum gününü hatırlat", b, ham2) is None)
kontrol("ilgisiz cümle → None", ns["kt_sesli_hatirlat"]("yarın Ali'yi aramamı hatırlat", b, ham2) is None)
# talimat.py bağlantısı: talimat_yakala önce bunu dener, ortak onay yolundan geçer
tl = oku("aktarici", "talimat.py")
kontrol("talimat_yakala kt_sesli_hatirlat'ı çağırır ve 'yapilacak' + zaman ile onay yoluna verir", 'kt_sesli_hatirlat(metin)' in tl and 'talimat_kuyruk("yapilacak", None, kh[0], metin, kaynak, zaman=kh[1])' in tl)
# --- Swift ve bağlantılar
sw = oku("takvim.swift"); ku = oku("kurulum.py"); rl = oku("relay.py")
kontrol("takvim.swift: --tarihler, üç izin ayrı, yazma çağrısı yok (CNSaveRequest, save, remove, saveReminder)", '"--tarihler"' in sw and "requestFullAccessToReminders" in sw and "izinler" in sw and "CNSaveRequest" not in sw[sw.index("func tarihlerOku"):sw.index("if let g = tarihGun")] and "store.save" not in sw[sw.index("func tarihlerOku"):sw.index("if let g = tarihGun")] and "store.remove" not in sw[sw.index("func tarihlerOku"):sw.index("if let g = tarihGun")])
kontrol("TAKVIM_PLIST: NSRemindersFullAccessUsageDescription var", "NSRemindersFullAccessUsageDescription" in ku)
kontrol("relay: /yaklasan-tarihler VERI_GET'te, GET ve POST bağlı, bölüm yüklü, hatırlatma döngüsü başlar", '"/yaklasan-tarihler"' in re.search(r"VERI_GET = \{[^}]*\}", rl).group(0) and 'yol == "/yaklasan-tarihler"' in rl and 'kt_islem(p)' in rl and 'bolum("kisisel-tarihler")' in rl and "_kt_dongu" in rl)
kontrol("relay AYAR_PANO: ayar adları", all(f'"{k}"' in rl[rl.index("AYAR_PANO = {"):rl.index("def kisilik_listesi")] for k in ("kisisel_tarihler", "kisisel_tarih_ufuk", "kisisel_tarih_hatirlat", "kisisel_tarih_sesli", "kutlama_kanali")))
kontrol("relay ayarlar_view: kisisel_tarih_saat betada boş, geliştiricide 09:00 (görünüm ve varsayılan)", rl.count('"09:00" if gelistirici_mi() else ""') == 2 and 'd["kisisel_tarih_saat"]' in rl and 'vars_["kisisel_tarih_saat"]' in rl)
bk = oku("aktarici", "bas-konus.py"); kontrol("Konuş bağlamı kisisel_tarih_baglam çağırır", "kisisel_tarih_baglam(soru)" in bk)
print("\nSONUÇ: " + ("hepsi geçti" if not hatalar else f"{len(hatalar)} hata: {hatalar}")); sys.exit(1 if hatalar else 0)
