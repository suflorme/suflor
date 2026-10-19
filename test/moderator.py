#!/usr/bin/env python3
# Toplantı moderatörü (v0.83.0, S93; aktarici/moderator.py): komut kalıpları, gündem (cümleden / agenda.json), süre, görev sırası (başla → sessiz kalana söz →
# uzun konuşanı toparla → süre dolunca özet → itiraz süresi → sonraki madde → kapanış), kullanıcı komutları (sonraki, özetle, bekle/devam, süre, bırak),
# meşgulken görev verilmez, toplantı bitince kapanır, toplantıya söyle kapalıyken başlamaz. Bölüm dosyası yalıtılmış ad alanında, sahte döküm ve Konuş ile.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/moderator.py
import os, re, sys, time, json, datetime, threading
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["SUFLOR_TEST_MOD_HIZLI"] = "1"; os.environ.pop("SUFLOR_TEST_BASLAT", None)
hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
DOKUM, GOREV, SESLI, SECILEN = [], [], [], []
D = {"top": True, "sessiz": 5.0, "agenda": {"items": []}}
ns = {"__name__": "moderator", "os": os, "re": re, "time": time, "json": json, "datetime": datetime, "threading": threading,
      "AYAR": {"ad": "Deniz T", "toplantiya_ses": True}, "asistan_toplanti": lambda: ns["AYAR"].get("toplantiya_ses") is True, "STATE": {}, "_KS": {"tur": None}, "OT": {}, "OT_SON": ("iptal", "okundu", "kesildi", "soylenmedi", "okunamadi"),
      "TS": {"p": []}, "_t": lambda a, b: a, "tail": lambda n=200: list(DOKUM), "agenda": lambda: D["agenda"], "toplanti_var": lambda: D["top"],
      "kanal_sessizlik": lambda: D["sessiz"], "kisilik_sec": lambda ad: SECILEN.append(ad), "kisilik_ad": lambda: "ATLAS", "seslendir": lambda m, kuyruk=False: SESLI.append(m),
      "_konus_kur": lambda **k: None, "_konus_sor": lambda metin, tur: GOREV.append((metin, tur)),
      "_epoch": lambda t: datetime.datetime.fromisoformat(str(t)).timestamp(), "_saat": lambda s: datetime.datetime.now() + datetime.timedelta(minutes=30)}
exec(compile(open(os.path.join(KOD, "aktarici", "moderator.py"), encoding="utf-8").read(), "moderator.py", "exec"), ns)
M = ns["MOD"]; M["isci"] = True  # döngü iş parçacığı yerine adımlar elle
def satir(kim, metin, once_sn=0.0, kanal="karsi"):
    DOKUM.append({"speaker": kim, "text": metin, "kanal": kanal, "at": datetime.datetime.fromtimestamp(time.time() - once_sn).isoformat()})
def adim(n=1):
    for _ in range(n):
        ns["_mod_adim"]()
        if GOREV and ns["_KS"]["tur"]: ns["_KS"]["tur"] = None  # sahte Konuş: cevap hemen söylendi
def son(): return GOREV[-1][0] if GOREV else ""

# 1) komut kalıpları
k = ns["MOD_BASLA_RX"]
bak("başlatma kalıpları tanınır", all(k.search(x) for x in ("toplantıyı sen yönet", "Toplantının yönetimini sana bırakıyorum", "moderatörlüğü üstlen", "bundan sonra toplantıyı sen yönet lütfen", "moderatör sen ol", "please run the meeting")))
bak("sıradan cümle başlatma sayılmaz", not any(k.search(x) for x in ("toplantıyı kim yönetiyor?", "yönetim kurulu toplantısı ne zaman", "bu toplantı çok uzun")))
bak("gündem cümleden: 'gündem: bütçe, takvim ve riskler'", ns["_mod_gundem_coz"]("Toplantıyı sen yönet, gündem: bütçe, takvim ve riskler.") == ["Bütçe", "Takvim", "Riskler"])
D["agenda"] = {"items": ["1 Bütçe onayı — karar çıksın", "2 Yeni ofis takvimi", {"text": "3) Riskler"}]}
bak("gündem agenda.json'dan (sıra no ve ' — beklenen' atılır)", ns["_mod_gundem_dosya"]() == ["Bütçe onayı", "Yeni ofis takvimi", "Riskler"])
bak("süre: 'toplam 30 dakika' 3 maddeye 10'ar dk, 'her madde 5 dakika' 5 dk", ns["_mod_sure"](3, "toplam 30 dakika") == 600 and ns["_mod_sure"](3, "her madde 5 dakika") == 300)

# 2) toplantıya söyle kapalıyken başlamaz; açıkken MATLAS'le başlar
ns["AYAR"]["toplantiya_ses"] = False
bak("asistanlar toplantıda konuşmuyorken başlamaz, kulağa söyler (S94 ayar adı)", ns["moderator_komut"]("toplantıyı sen yönet", "MATLAS") is True and not M["acik"] and SESLI and "Asistanlar toplantıda konuşsun" in SESLI[-1])
ns["AYAR"]["toplantiya_ses"] = True
ns["moderator_komut"]("toplantıyı sen yönet, gündem: bütçe ve takvim, her madde 1 dakika", "MATLAS")
bak("başladı: MATLAS, 2 madde, madde başına 60 sn", M["acik"] and M["kisilik"] == "MATLAS" and M["maddeler"] == ["Bütçe", "Takvim"] and M["sure_sn"] == 60)
adim()
bak("ilk görev 'başla': ilk madde ve gündem istemde, kişilik seçildi, otonom yol", "«Bütçe»" in son() and "Gündem: 1) Bütçe (şu an); 2) Takvim" in son() and SECILEN[-1] == "MATLAS" and GOREV[-1][1]["otonom"] and GOREV[-1][1]["kaynak"] == "moderator")
bak("istem: sesli kısım toplantıya okunur, iç not yok", "doğrudan toplantıya okunur" in son() and "iç not" in son())

# 3) meşgulken görev yok
n = len(GOREV); ns["_KS"]["tur"] = {"x": 1}; M["t_madde"] = time.time() - 50; ns["_mod_adim"](); ns["_KS"]["tur"] = None
bak("Konuş meşgulken görev verilmez", len(GOREV) == n)

# 4) sessiz kalana söz: Kerem toplantıda konuştu ama bu maddede konuşmadı; %40 geçti
satir("Kerem A", "Merhaba herkese", once_sn=200); satir("Ayşe Y", "Bütçe konusunda şunu söyleyeyim", once_sn=1)
M.update(t_madde=time.time() - 30, t_son_mudahale=0); adim()
bak("sessiz kalana söz: Kerem'e davet", "Kerem A bu maddede henüz konuşmadı" in son())
n = len(GOREV); M["t_son_mudahale"] = 0; adim()
bak("aynı kişiye hemen yeniden davet yok", len(GOREV) == n or "Kerem" not in son())

# 5) uzun konuşan: Ayşe 5 sn'dir kesintisiz (deneme eşiği 4 sn), iki katılımcı var
DOKUM.clear(); satir("Kerem A", "Tamam", once_sn=40); [satir("Ayşe Y", f"uzun anlatım {i}", once_sn=6 - i) for i in range(6)]
M.update(t_madde=time.time() - 30, t_son_mudahale=0, son_davet={"Kerem A": time.time()}); adim()
bak("uzun konuşanı nazikçe toparla: Ayşe", "Ayşe Y uzun süredir" in son())

# 6) süre doldu + sessizlik → özet; özet okununca itiraz süresi, sonra sonraki madde
D["sessiz"] = 2.0; M.update(t_madde=time.time() - 61, t_son_mudahale=0); adim()
bak("süre dolunca özet + karar + onay sorusu", "«Bütçe» maddesinin süresi doldu" in son() and "Onaylıyor musunuz" in son() and M["faz"] == "karar")
adim(); bak("özet okundu: itiraz süresi başladı, hemen geçilmez", M["faz"] == "karar" and M["t_karar"] > 0)
D["sessiz"] = 0.5; M["t_karar"] = time.time() - 5; adim(); bak("biri konuşuyorsa (sessizlik < 3 sn) geçilmez", M["faz"] == "karar")
D["sessiz"] = 4.0; adim(); bak("itiraz süresi bitti, sessizlik: sonraki madde", M["i"] == 1 and M["faz"] == "ac")
adim(); bak("ikinci madde açıldı", "«Takvim»" in son() and "Sıradaki maddeyi aç" in son())

# 7) kullanıcı komutları
n = len(GOREV)
bak("'bekle' görevleri durdurur", ns["moderator_komut"]("bekle biraz") and M["bekle"]); M.update(t_madde=time.time() - 100, t_son_mudahale=0); adim(); bak("beklerken görev yok", len(GOREV) == n)
bak("'devam et' sürdürür", ns["moderator_komut"]("devam et") and not M["bekle"])
s0 = M["sure_sn"]; ns["moderator_komut"]("3 dakika daha süre ver"); bak("'3 dakika daha süre ver' +180 sn", M["sure_sn"] == s0 + 180)
bak("'özetle' özet ister", ns["moderator_komut"]("özetle") and M["faz"] == "ozet_iste"); adim(); bak("özet görevi verildi", "«Takvim» maddesinin süresi doldu" in son())
adim(); M.update(t_karar=time.time() - 5); adim(2)
bak("son madde bitince kapanış: kararlar, teşekkür, yönetim Deniz'e", "Gündem bitti" in son() and "Deniz'e geri ver" in son())
adim(); bak("kapanış söylendi: moderatör kapandı", not M["acik"] and "gündem bitti" in (M["neden"] or ""))

# 8) sonraki madde komutu, bırakma, toplantı bitince kapanma, gündemsiz
ns["moderator_komut"]("yönetimi sana bırakıyorum, gündem: A konusu, B konusu ve C konusu", "MATLAS"); adim()
bak("'sonraki madde': özetsiz geçer", ns["moderator_komut"]("sonraki maddeye geçelim") and (adim() or True) and M["i"] == 1)
bak("'yönetimi geri alıyorum' kapatır", ns["moderator_komut"]("tamam yönetimi geri alıyorum") and not M["acik"])
D["agenda"] = {"items": []}; ns["moderator_komut"]("toplantıyı sen yönet", "MATLAS"); adim()
bak("gündem yoksa katılımcılara ne konuşmak istediklerini sorar", "Gündem verilmedi" in son() and M["maddeler"] == [])
bak("gündemsizken sonradan 'gündem: X ve Y' verilebilir", ns["moderator_komut"]("gündem: fiyat ve teslim") and M["maddeler"] == ["Fiyat", "Teslim"] and M["faz"] == "ac")
D["top"] = False; adim(); bak("toplantı bitince kapanır", not M["acik"] and "toplantı bitti" in M["neden"])
bak("kapalıyken komut Claude'a gider (False)", ns["moderator_komut"]("sonraki madde") is False)
v = ns["moderator_view"](); bak("durum görünümü (pano/status)", v and v["acik"] is False and v["neden"])
print("moderatör: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı")); sys.exit(1 if hata else 0)
