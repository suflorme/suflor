#!/usr/bin/env python3
# Eylem menüsü (ortak karar katmanı, yerel; yapi.py kayit_eylem / eylem_menu / taslak_icerik / gundem_adaylari / son_geri_alinabilir + aktarici/eylem-menu.py): her eylem tam bir olay yazar,
# Geri al son olayı döndürür (art arda bir öncekine iner), gizli toplantı kaydında hiçbir eylem (Claude dahil) çalışmaz, taslak bağlantıları doğru (mailto gövdesi yok, msteams: derin bağlantı) ve
# hiçbir şey gönderilmez, ata + kimlik e-postası, gündem taslağıyla tutarlılık, Claude'a çalıştır yalnız kaydı gönderir ve sonucu yorum olarak bağlar, aktarıcı ucu (sahte model, sahte takvim).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/eylem-menu.py      (~3 sn; ağ, Claude, aktarıcı ve gerçek veri yok)
import datetime, json, os, re, sqlite3, sys, tempfile, time, urllib.parse
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="suflor-eylemmenu-"); AY = os.path.join(T, "ayar.json")
json.dump({"ad": "Ayşe Deneme"}, open(AY, "w")); os.environ["SUFLOR_AYAR"] = AY
import yapi
AT = chr(64); hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def dokum(C, ad, gizli=False):
    open(os.path.join(C, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n" + ("| 10:00:05 | **GİZLİ** | açıldı | |\n" if gizli else ""))
def db(C): return sqlite3.connect(os.path.join(C, "karar-grafi.sqlite"))
def olay_say(C): return db(C).execute("SELECT COUNT(*) FROM olay").fetchone()[0]
def son_olaylar(C, n): return [r for r in db(C).execute("SELECT olay_id, tur, kaynak FROM olay ORDER BY saat DESC LIMIT ?", (n,))][::-1]
C = os.path.join(T, "canli"); os.makedirs(C)
D1, G = "2026-11-03-1000-Haftalik-Butce", "2026-11-04-1500-Ozel"; dokum(C, D1); dokum(C, G, True)
yapi.graf_yaz(C, {"baslik": "Haftalık bütçe", "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-10", "saat": "10:10:00"},
    {"tur": "karar", "metin": "Tedarikçi Mart'ta seçilecek", "kim": "Can Örnek", "saat": "10:07:00", "netlik": "ortuk"},
    {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Can Örnek", "saat": "10:14:00"},
    {"tur": "soz", "metin": "Listeyi getirecek", "sahip": "Zeynep Kaya", "tarih": "2026-11-07", "saat": "10:13:00"}]}]}, D1 + ".md")
yapi.graf_yaz(C, {"baslik": "Özel", "tarih": "2026-11-04", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "Gizli iş", "sahip": "Can Örnek"}, {"tur": "karar", "metin": "Gizli karar", "netlik": "ortuk"}]}]}, G + ".md")
v = yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); K = {x["metin"]: x for x in v["kayitlar"]}
IS, KARAR, SORU, SOZ = K["Tabloyu güncelle"]["id"], K["Tedarikçi Mart'ta seçilecek"]["id"], K["KDV dahil mi?"]["id"], K["Listeyi getirecek"]["id"]
def _id(metin, onek): return onek + str(db(C).execute("SELECT id FROM kayit WHERE metin = ?", (metin,)).fetchone()[0])
GIZLI_IS, GIZLI_KARAR = _id("Gizli iş", "s"), _id("Gizli karar", "k")
IS_KID = yapi.ortak_kayit(C, IS)["kayit_id"]; GIZLI_KID = yapi.ortak_kayit(C, GIZLI_IS)["kayit_id"]  # özet yeniden yazılınca yerel kimlik (s1) düşebilir; kalıcı kimlik kalır
bak("gizli toplantının kayıtları listede yok", not any("Gizli" in x["metin"] for x in v["kayitlar"]))
# sahte bağımlılıklar
KIM = []
def kimlik_f(ad, **kw): KIM.append(ad); return {"Zeynep Kaya": {"eposta": "zeynep.kaya" + AT + "firma.test", "kaynak": "takvim", "guven": 0.95, "adaylar": []}, "Deniz": {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": ["deniz.a" + AT + "firma.test", "deniz.t" + AT + "firma.test"]}}.get(ad, {"eposta": None, "kaynak": None, "guven": 0.0, "adaylar": []})
SIMDI = datetime.datetime(2026, 11, 5, 12, 0).astimezone()
def ev(i, saat, baslik, kisiler=(), **ek): return dict({"id": i, "baslik": baslik, "baslangic": (SIMDI.replace(hour=saat[0], minute=saat[1]) + datetime.timedelta(days=saat[2] if len(saat) > 2 else 0)).isoformat(), "kisi_sayisi": 3,
                                                       "katilimcilar": list(kisiler), "kisiler": [{"ad": k, "eposta": ""} for k in kisiler]}, **ek)
TAKVIM = [ev("gecmis", (9, 0), "Geçmiş"), ev("t1", (15, 0), "Satış haftalık", ["Emre Kural"]), ev("t2", (16, 0), "Tedarik", ["Zeynep Kaya"]), ev("tg", (14, 0), "Tüm gün", tum_gun=True), ev("tr", (13, 0), "Reddedilen", reddettin=True),
          ev("tp", (13, 30), "Paylaşılan", paylasilan=True), ev("tek", (13, 40), "Tek kişi", kisi_sayisi=1), ev("yarin", (10, 0, 1), "Yarın", ["Zeynep Kaya"])]
def eylem(kimlik, e, p=None, **k): return yapi.kayit_eylem(C, kimlik, e, p, kimlik_f=kimlik_f, takvim=TAKVIM, simdi=SIMDI, **k)
def tek_olay(ad, kimlik, e, p=None, tur=None, ek=0, **k):  # eylem tam bir olay yazar (ek = ek olaylar)
    n = olay_say(C); r = eylem(kimlik, e, p, **k); d = olay_say(C) - n
    bak(f"{ad}: ok, tam bir olay" + (f" ({tur})" if tur else ""), r.get("ok") and d == 1 + ek and r.get("olay") and (not tur or son_olaylar(C, 1 + ek)[-1][1] == tur), (r, d))
    return r
# --- menü bilgisi ---
m = yapi.eylem_menu(C, IS, TAKVIM, kimlik_f, SIMDI)
bak("iş menüsü: yapıldı, iptal, ertele, gündem, ata, taslaklar, Claude, tarihçe; Geri al yok (yalnız oluşturma olayı)", m["ok"] and m["eylemler"] == ["yapildi", "iptal", "ertele", "gundem", "ata", "eposta", "teams", "claude", "tarihce"] and m["geri_al"] is None, m)
bak("karar menüsü: onayla/reddet; soru: cevaplandı", yapi.eylem_menu(C, KARAR, TAKVIM)["eylemler"][:2] == ["onayla", "reddet"] and yapi.eylem_menu(C, SORU, TAKVIM)["eylemler"][0] == "cevaplandi")
bak("gündem adayları: geçmiş, tüm gün, reddedilen, paylaşılan, tek kişilik yok; saat sırası", [a["id"] for a in m["gundem"]] == ["t1", "t2", "yarin"], m["gundem"])
bak("sahip (Can Örnek) için kimlikten e-posta yok → eşlenmedi", m["sahip"]["ad"] == "Can Örnek" and not m["sahip"].get("eposta"))
# --- her eylem bir olay ---
r = tek_olay("ertele", IS, "ertele", {"vade": "2026-11-20", "neden": "tedarikçi gecikti"}, "ertelendi"); bak("ertele: vade değişti", r["kayit"]["vade"] == "2026-11-20")
bak("aynı vade yeniden: olay yok", eylem(IS, "ertele", {"vade": "2026-11-20"})["olay"] is None)
bak("ertele: karar ertelenemez, vade boş olmaz", not eylem(KARAR, "ertele", {"vade": "2026-11-20"})["ok"] and not eylem(IS, "ertele", {})["ok"])
r = tek_olay("gündeme ekle (önerilen toplantı)", IS, "gundem", {}, "gundeme_eklendi"); bak("gündem: sıradaki uygun toplantı (t1) seçildi, izdüşümde", r["toplanti"]["id"] == "t1" and r["kayit"]["gundem"]["etkinlik"] == "t1", r)
bak("gündem: bilinmeyen toplantı reddedilir", not eylem(IS, "gundem", {"etkinlik": "yok"})["ok"])
gt = yapi.gundem_taslagi(C, [], "Ayşe Deneme", "", datetime.date(2026, 11, 5), etkinlik="t1")
bak("gündem taslağı tutarlı: eklenen iş t1 taslağında, t2'de değil", [m_["metin"] for m_ in gt["maddeler"]] == ["Tabloyu güncelle"] and gt["maddeler"][0]["eklendi"]
    and yapi.gundem_taslagi(C, [], "Ayşe Deneme", "", datetime.date(2026, 11, 5), etkinlik="t2")["maddeler"] == [])
r = tek_olay("ata + kimlik e-postası", IS, "ata", {"sahip": "Zeynep Kaya"}, "is_atandi"); bak("ata: e-posta kimlikten, kaynak bilgisi", r["eposta"] == "zeynep.kaya" + AT + "firma.test" and r["kimlik"]["kaynak"] == "takvim" and r["kayit"]["roller"]["sahip"]["eposta"].startswith("zeynep.kaya"), r)
r = tek_olay("ata (e-posta elle)", SOZ, "ata", {"sahip": "Bora Kaya", "eposta": "Bora.Kaya" + AT + "Firma.test"}, "is_atandi"); bak("elle e-posta küçük harfe, kimlik sorulmaz", r["eposta"] == "bora.kaya" + AT + "firma.test" and "Bora Kaya" not in KIM)
r = tek_olay("ata (eşlenemeyen)", IS, "ata", {"sahip": "Deniz"}, "is_atandi"); bak("eşlenemeyen: e-posta boş, adaylar döner (tahmin yok)", r["eposta"] is None and len(r["kimlik"]["adaylar"]) == 2)
bak("ata: kişi yoksa hata", not eylem(IS, "ata", {})["ok"])
eylem(IS, "ata", {"sahip": "Zeynep Kaya"})
tek_olay("karar onayla", KARAR, "onayla", {}, "karar_onaylandi"); bak("onay sonrası menüde onayla/reddet yok", "onayla" not in yapi.eylem_menu(C, KARAR, TAKVIM)["eylemler"])
tek_olay("karar reddet (onaylı karar yeniden)", KARAR, "reddet", {}, "karar_reddedildi"); bak("iş onaylanamaz", not eylem(IS, "onayla")["ok"])
tek_olay("soru cevaplandı", SORU, "cevaplandi", {}, "durum_degisti"); tek_olay("soru yeniden açıldı", SORU, "ac", {}, "durum_degisti")
tek_olay("iş yapıldı", SOZ, "yapildi", {}, "durum_degisti"); bak("söz yapıldı = tutuldu", yapi.ortak_kayit(C, SOZ)["durum"] == "tutuldu"); tek_olay("iş yeniden açıldı", SOZ, "ac", {}, "durum_degisti")
# --- taslaklar: gönderme yok ---
n = olay_say(C); r = eylem(IS, "eposta", {}); t = r["taslak"]
bak("e-posta taslağı: alıcı sahibin adresi, konu ve gövde kayıttan; olay taslak_hazirlandi", r["ok"] and t["alicilar"] == ["zeynep.kaya" + AT + "firma.test"] and "Tabloyu güncelle" in t["govde"] and t["govde"].startswith("Merhaba Zeynep,") and "20 Kasım" in t["govde"]
    and t["konu"].startswith("İş: Tabloyu") and olay_say(C) == n + 1 and son_olaylar(C, 1)[0][1] == "taslak_hazirlandi", (r, t))
u = urllib.parse.urlsplit(t["teams"]); q = urllib.parse.parse_qs(u.query)
bak("Teams taslağı: msteams:/l/chat/0/0, users = alıcı, message önceden dolu", t["teams"].startswith("msteams:/l/chat/0/0?users=zeynep.kaya" + AT + "firma.test&message=") and "Tabloyu güncelle" in q["message"][0] and q["users"] == ["zeynep.kaya" + AT + "firma.test"], t["teams"])
r2 = eylem(IS, "teams", {"alicilar": ["a" + AT + "x.test", "B" + AT + "x.test"]}); bak("Teams: verilen alıcılar, birden çoğu virgülle", r2["taslak"]["teams"].startswith("msteams:/l/chat/0/0?users=a" + AT + "x.test,b" + AT + "x.test&message="))
r3 = eylem(KARAR, "eposta", {}); bak("alıcısı olmayan taslak: boş alıcı, alici_yok işareti, yine olay", r3["ok"] and r3["alici_yok"] and r3["taslak"]["alicilar"] == [] and "karar" in r3["taslak"]["konu"].lower() and "users=&message=" in r3["taslak"]["teams"], r3)
bak("taslak içinde teyit eki ve satır sonu bozulmaz; özel karakter kodlanır", "Merhaba" in yapi.taslak_icerik({"tur": "is", "metin": "a&b=c #1 (teyit bekliyor — x)", "baslik": "T", "tarih": "2026-11-05"}, "teams", ["x" + AT + "y.test"], "Ali")["teams"] is False
    or "a%26b%3Dc" in yapi.taslak_icerik({"tur": "is", "metin": "a&b=c #1 (teyit bekliyor — x)", "baslik": "T", "tarih": "2026-11-05"}, "teams", ["x" + AT + "y.test"], "Ali")["teams"])
en = yapi.taslak_icerik({"tur": "is", "metin": "Update the table", "baslik": "Weekly", "tarih": "2026-11-05"}, "eposta", ["x" + AT + "y.test"], "Ali", dil="en"); bak("İngilizce taslak", en["govde"].startswith("Hi Ali,") and en["konu"].startswith("Task:"))
# --- Claude'a çalıştır ---
ISTEMLER = []
def model_f(istem): ISTEMLER.append(istem); return "1) Özet: tablo güncellenecek.\n2) Yapılacaklar: …\n3) Taslak: Merhaba Zeynep …", None
n = olay_say(C); r = eylem(IS, "claude", model_f=model_f)
bak("Claude'a çalıştır: sonuç yorum olarak kayda bağlandı (kaynak claude, uretici claude), tek olay", r["ok"] and olay_say(C) == n + 1 and son_olaylar(C, 1)[0][1:] == ("yorum_eklendi", "claude") and "Özet" in r["metin"], r)
istem = ISTEMLER[0]; bak("istem yalnız kaydı içerir: metin, toplantı, sahip adı; e-posta ve döküm yok; veri etiketi", "Tabloyu güncelle" in istem and "Zeynep Kaya" in istem and AT not in istem and "merhaba" not in istem and "<veri>" in istem and "talimat" in istem)
mm = yapi.eylem_menu(C, IS, TAKVIM); yk = [o for o in mm["tarihce"] if o["tur"] == "yorum_eklendi"]
bak("tarihçede Claude notu görünür (metniyle, 'Claude hazırlık notu ekledi')", yk and yk[-1]["metin"].startswith("1) Özet") and "Claude hazırlık notu ekledi" in yk[-1]["ozet"], yk)
bak("Claude hatası: olay yok, hata döner", (lambda r_: not r_["ok"] and olay_say(C) == n + 1 and r_["err"] == "zaman aşımı")(eylem(IS, "claude", model_f=lambda i: (None, "zaman aşımı"))))
bak("Claude yok (model_f verilmedi): hata", not eylem(IS, "claude")["ok"])
# --- gizli kayıtta hiçbir eylem çalışmaz ---
n = olay_say(C); ISTEMLER.clear()
ret = [eylem(g, e, p, model_f=model_f) for g in (GIZLI_IS, GIZLI_KARAR) for e, p in (("claude", {}), ("ertele", {"vade": "2026-12-01"}), ("ata", {"sahip": "X Y"}), ("eposta", {}), ("teams", {}), ("gundem", {}), ("onayla", {}), ("yapildi", {}))]
bak("gizli toplantı kaydı: Claude'a çalıştır dahil hiçbir eylem çalışmaz, olay ve model çağrısı yok", all(not r_["ok"] and r_["err"] == "gizli" for r_ in ret) and olay_say(C) == n and not ISTEMLER)
bak("gizli kayıt için menü de yok", yapi.eylem_menu(C, GIZLI_IS, TAKVIM)["err"] == "gizli")
# --- Geri al ---
mm = yapi.eylem_menu(C, IS, TAKVIM); bak("menüde Geri al: son geri alınabilir olay (taslak ve Claude notu sayılmaz)", mm["geri_al"] and "atad" in mm["geri_al"]["ozet"] or mm["geri_al"] and mm["geri_al"]["ozet"], mm["geri_al"])
ol = yapi.tarihce(C, IS); son = yapi.son_geri_alinabilir(C, IS)
n = olay_say(C); r = eylem(IS, "geri_al"); bak("Geri al: son olay döndü, günlük yalnız eklendi", r["ok"] and olay_say(C) == n + 1 and r["geri_alinan"] == son["olay_id"] and len(r["geri"]) == 1, r)
son2 = yapi.son_geri_alinabilir(C, IS); bak("art arda Geri al bir öncekine iner (geri alınan ve geri alma atlanır)", son2 and son2["olay_id"] != son["olay_id"] and "geri_al" not in son2["veri"], (son, son2))
vade0 = yapi.ortak_kayit(C, IS)["vade"]
for _ in range(12):  # hepsini geri al: sonunda yalnız oluşturma kalır, Geri al kalkar
    if not eylem(IS, "geri_al")["geri"]: break
bak("tümü geri alınınca kayıt ilk hâlinde: vade 2026-11-10, Geri al yok", yapi.ortak_kayit(C, IS)["vade"] == "2026-11-10" and yapi.eylem_menu(C, IS, TAKVIM)["geri_al"] is None and yapi.ortak_kayit(C, IS)["durum"] == "acik")
bak("başka kaydın olayı geri alınamaz", not eylem(SORU, "geri_al", {"olay_id": ol[-1]["olay_id"]})["ok"])
bak("kayit_eylem: bilinmeyen eylem ve kayıt", not eylem(IS, "uc")["ok"] and not eylem("s99999", "ertele", {"vade": "x"})["ok"])
# --- onay süresi göstergesi (liste) ---
l2 = yapi.kayit_listesi(C, "Ayşe", datetime.date(2026, 11, 5)); kk = [x for x in l2["kayitlar"] if x["tur"] == "karar"]
bak("kayit_listesi: sahip e-postası, gündem ve alt iş alanları var", all(k_ in x for x in l2["kayitlar"] for k_ in ("sahip_eposta", "gundem", "alt")))
D2 = "2026-11-03-1100-Ek-Toplanti"; dokum(C, D2)
yapi.graf_yaz(C, {"baslik": "Ek toplantı", "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "karar", "metin": "Yeni bekleyen karar", "kim": "Can Örnek", "saat": "10:20:00", "netlik": "ortuk"}]}]}, D2 + ".md")
l3 = [x for x in yapi.kayit_listesi(C, "Ayşe", datetime.date(2026, 11, 6))["kayitlar"] if x["metin"] == "Yeni bekleyen karar"]
bak("bekleyen kararda onay süresi: 3. gün hatırlat", l3 and l3[0]["onay"]["hatirlat"] is True and l3[0]["onay"]["durum"] == "bekliyor", l3)
# --- aktarıcı bölümü (aktarici/eylem-menu.py): sahte ad alanı ---
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "AYAR": {"ad": "Ayşe Deneme"}, "BASE": C, "TAKVIM_TAM": {e["id"]: e for e in TAKVIM}, "kimlik_coz": kimlik_f,
      "_yapi_mod": lambda: yapi, "_t": lambda a, b: a, "claude_yolu": lambda: None, "BRIFING_APP": os.path.join(T, "yok.app"), "BEYIN": None}
exec(compile(open(os.path.join(KOD, "aktarici", "eylem-menu.py"), encoding="utf-8").read(), "eylem-menu.py", "exec"), ns)
ns["eylem_model"] = lambda istem: ("Aktarıcı notu", None)  # bölüm model çağrısını kendi tanımladı; test sahtesi geri konur
g = ns["kayit_menu_view"]("/kayit-menu?id=" + IS_KID); bak("kayit_menu_view: menü bilgisi", g["ok"] and g["kayit"]["kayit_id"] == IS_KID and "ertele" in g["eylemler"], g)
bak("kayit_menu_view: id yok / kayıt yok", not ns["kayit_menu_view"]("/kayit-menu")["ok"] and not ns["kayit_menu_view"]("/kayit-menu?id=s99999")["ok"])
r = ns["kayit_eylem_islem"]({"id": IS_KID, "eylem": "ertele", "vade": "2026-12-24"}); bak("kayit_eylem_islem: ertele", r["ok"] and r["kayit"]["vade"] == "2026-12-24")
r = ns["kayit_eylem_islem"]({"id": IS_KID, "eylem": "claude"}); bak("kayit_eylem_islem: Claude'a çalıştır (bölümün model işlevi)", r["ok"] and r["metin"] == "Aktarıcı notu", r)
r = ns["kayit_eylem_islem"]({"id": IS_KID, "eylem": "eposta"}); bak("kayit_eylem_islem: taslak, alici_yok işareti", r["ok"] and "taslak" in r)
bak("kayit_eylem_islem: gizli ve bozuk girdi", ns["kayit_eylem_islem"]({"id": GIZLI_KID, "eylem": "claude"})["err"] == "gizli" and not ns["kayit_eylem_islem"]({"eylem": "ertele"})["ok"] and not ns["kayit_eylem_islem"]({"id": IS_KID})["ok"])
bak("kayit_eylem_islem: yazan kullanıcı (ad:…), kaynak eylem", db(C).execute("SELECT yazan, kaynak FROM olay WHERE tur = 'ertelendi' ORDER BY saat DESC LIMIT 1").fetchone() == ("ad:Ayşe Deneme", "eylem"))
# --- kayıt veritabanı adresleri → kimlik modülü (/vt-bellek kisi_adres; aktarici/sozluk-ogren.py vt_bellek_al) ---
import collections, hashlib, threading
ns2 = {"re": re, "os": os, "json": json, "time": time, "collections": collections, "hashlib": hashlib, "threading": threading, "AYAR": {"ad": "Ayşe Deneme"}, "BASE": C, "kisi_bul": lambda ad: {"durum": "ok", "kisiler": []},
       "TAKVIM_TAM": {}, "TAKVIM_GEC": {"olaylar": [], "pay": []}}
exec(compile(open(os.path.join(KOD, "aktarici", "kimlik.py"), encoding="utf-8").read(), "kimlik.py", "exec"), ns2)
try:
    exec(compile(open(os.path.join(KOD, "aktarici", "sozluk-ogren.py"), encoding="utf-8").read(), "sozluk-ogren.py", "exec"), ns2)
    r = ns2["vt_bellek_al"]({"adlar": [], "terimler": [], "kisi_adres": [["Tolga Er, Tolgay", "tolga.er" + AT + "firma.test"], ["Adres Yok", ""]]})
    c = ns2["kimlik_coz"]("Tolgay", kisiler=False)
    bak("/vt-bellek kisi_adres: kayıt veritabanı adresi kimlik modülüne yüklenir (kaynak vt)", r["ok"] and c["eposta"] == "tolga.er" + AT + "firma.test" and c["kaynak"] == "vt" and ns2["vt_bellek_view"]()["kimlik"] >= 1, (r, c))
    ns2["vt_bellek_al"]({"adlar": ["X"], "terimler": []}); bak("kisi_adres alanı yoksa yüklü adresler silinmez", ns2["kimlik_coz"]("Tolgay", kisiler=False)["eposta"] == "tolga.er" + AT + "firma.test")
except Exception as e_: bak(f"/vt-bellek kisi_adres testi çalıştırılamadı ({e_.__class__.__name__}: {e_})", False)
# --- Teams/e-posta taslağı: kendi işi, e-postasız sahip, okunur tarih ---
yapi.graf_yaz(C, {"baslik": "Ekip toplantısı", "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "is", "metin": "Davet gönderilecek", "sahip": "Ayşe Deneme", "tarih": "2026-11-12", "saat": "10:20:00"},
    {"tur": "is", "metin": "Rapor hazırlanacak", "sahip": "Deniz Bilinmez", "tarih": "2026-11-12", "saat": "10:21:00"}]}]}, "2026-11-05-1000-Ekiucular.md"); dokum(C, "2026-11-05-1000-Ekiucular")
yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); KEND = _id("Davet gönderilecek", "s"); BILINMEZ = _id("Rapor hazırlanacak", "s")
mk = yapi.eylem_menu(C, KEND, TAKVIM, kimlik_f=kimlik_f)
bak("kendi işinde menüde e-posta/Teams taslağı yok, kendi işareti var", mk["ok"] and mk["kendi"] and "teams" not in mk["eylemler"] and "eposta" not in mk["eylemler"] and "ata" in mk["eylemler"], mk["eylemler"])
rk = eylem(KEND, "teams", {}); bak("kendi işine Teams taslağı reddedilir, olay yazılmaz", not rk["ok"] and "senin" in rk["err"], rk)
mb = yapi.eylem_menu(C, BILINMEZ, TAKVIM, kimlik_f=kimlik_f)
bak("e-postası bilinmeyen sahip: menüde Teams pasif ve nedeni yazılı", mb["ok"] and not mb["kendi"] and "teams" in mb["eylemler"] and "e-postası yok" in mb["pasif"].get("teams", ""), mb)
n = olay_say(C); rb = eylem(BILINMEZ, "teams", {}); bak("e-postasız sahide Teams: boş Kime açılmaz, neden yazılı, olay yok", not rb["ok"] and "e-postası yok" in rb["err"] and olay_say(C) == n, rb)
re_ = eylem(BILINMEZ, "eposta", {}); bak("e-postasız sahide e-posta taslağı alici_yok işaretiyle", re_["ok"] and re_["alici_yok"], re_)
tt = yapi.taslak_icerik({"tur": "is", "metin": "12 Kasım toplantı davetini göndermek", "baslik": "Ekip — Dönüşüm (Karar ve Rol İnceleme)", "tarih": "2026-11-05", "vade": "2026-11-12"}, "teams", ["can" + AT + "x.test"], "Can Örnek", dil="tr")
mesaj = urllib.parse.parse_qs(urllib.parse.urlsplit(tt["teams"]).query)["message"][0]
bak("Teams metni: okunur tarih, toplantı adı tekrarı yok, ham tarih yok", "5 Kasım toplantısından" in mesaj and "Organizasyonel" not in mesaj and "2026-" not in mesaj and mesaj.startswith("Merhaba Can,") and "vade: 12 Kasım" in mesaj, mesaj)
# --- uçtan uca denemede bulunanlar (6 Kasım): bozuk tür girdisi kayda yazılmaz; karar menüsünde Teams nedeni doğru kişiyi söyler, adres kimlikten çözülürse pasif olmaz ---
n = olay_say(C); vade0 = yapi.ortak_kayit(C, KEND)["vade"]
bak("ertele: liste/sözlük vade kayda \"['x']\" olarak yazılmaz", not eylem(KEND, "ertele", {"vade": ["x"]})["ok"] and not eylem(KEND, "ertele", {"vade": {"a": 1}})["ok"] and yapi.ortak_kayit(C, KEND)["vade"] == vade0 and olay_say(C) == n)
bak("ata: sözlük ad kayda \"{'a': 1}\" olarak yazılmaz", not eylem(KEND, "ata", {"sahip": {"a": 1}})["ok"] and olay_say(C) == n and yapi.ortak_kayit(C, KEND)["roller"]["sahip"]["ad"] == "Ayşe Deneme")
bak("ertele: çok uzun serbest metin 20 karaktere kırpılır", eylem(BILINMEZ, "ertele", {"vade": "x" * 200})["kayit"]["vade"] == "x" * 20)
yapi.graf_yaz(C, {"baslik": "Karar toplantısı", "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "karar", "metin": "Bütçe ikiye bölünecek", "kim": "Can Örnek", "saat": "10:30:00", "netlik": "ortuk"}]}]}, "2026-11-05-1100-Karar.md"); dokum(C, "2026-11-05-1100-Karar")
yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); KR = _id("Bütçe ikiye bölünecek", "k")
mk0 = yapi.eylem_menu(C, KR, TAKVIM, kimlik_f=kimlik_f); yapi.ata(C, KR, {"isteyen": {"ad": "Can Örnek"}, "onaylayan": {"ad": "Ayşe Deneme"}}); mk1 = yapi.eylem_menu(C, KR, TAKVIM, kimlik_f=kimlik_f)
bak("karar, kimse yok: alıcı yok nedeni", "alıcısı yok" in mk0["pasif"].get("teams", ""), mk0["pasif"])
bak("karar, onaylayan kullanıcı: Teams pasif, neden 'kararı isteyenin' (muhatap isteyen)", "teams" in mk1["eylemler"] and "isteyenin e-postası yok" in mk1["pasif"].get("teams", ""), mk1["pasif"])
eylem(KR, "ata", {"sahip": "Zeynep Kaya", "eposta": "", "rol": "onaylayan"}); yapi.ata(C, KR, {"onaylayan": {"ad": "Deniz Bilinmez"}})
mk2 = yapi.eylem_menu(C, KR, TAKVIM, kimlik_f=kimlik_f)
bak("karar, onaylayan adresi yok: Teams pasif, neden 'onaylayanın'", "onaylayanın e-postası yok" in mk2["pasif"].get("teams", ""), mk2["pasif"])
yapi.ata(C, KR, {"onaylayan": {"ad": "Zeynep Kaya"}}); mk3 = yapi.eylem_menu(C, KR, TAKVIM, kimlik_f=kimlik_f)
bak("karar, onaylayanın adresi kimlik modülünden çözülür: Teams pasif değil (POST'la aynı yol)", mk3["pasif"] == {} and eylem(KR, "teams", {})["ok"], mk3["pasif"])
yapi.graf_yaz(C, {"baslik": "Sahipsiz", "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "Sahibi olmayan iş", "saat": "10:40:00"}]}]}, "2026-11-05-1200-Sahipsiz.md"); dokum(C, "2026-11-05-1200-Sahipsiz")
yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); SP = _id("Sahibi olmayan iş", "s"); mp = yapi.eylem_menu(C, SP, TAKVIM, kimlik_f=kimlik_f)
n = olay_say(C); rp = eylem(SP, "teams", {})
bak("sahipsiz iş: Teams pasif ve nedeni 'alıcısı yok; Ata ile kişi ekle', POST aynı nedeni verir, olay yok", "alıcısı yok" in mp["pasif"].get("teams", "") and not rp["ok"] and "Ata ile" in rp["err"] and olay_say(C) == n, (mp["pasif"], rp))
# --- 7 Kasım: "kendi" önce e-postaya bakar; ilk adı kullanıcıyla aynı başka kişinin işinde taslak seçenekleri görünür ---
yapi.graf_yaz(C, {"baslik": "Ad benzeri", "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "is", "metin": "Soyadı farklı Ayşe'nin işi", "sahip": "Ayşe Doruk", "tarih": "2026-11-12", "saat": "10:50:00"},
    {"tur": "is", "metin": "Yalnız ilk adla yazılmış iş", "sahip": "Ayşe", "tarih": "2026-11-12", "saat": "10:51:00"}]}]}, "2026-11-05-1300-Adbenzeri.md"); dokum(C, "2026-11-05-1300-Adbenzeri")
yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); AD2 = _id("Soyadı farklı Ayşe'nin işi", "s"); AD1 = _id("Yalnız ilk adla yazılmış iş", "s")
m2 = yapi.eylem_menu(C, AD2, TAKVIM, kimlik_f=kimlik_f)
bak("ilk adı aynı, soyadı farklı kişinin işi kendi sayılmaz: e-posta/Teams taslağı menüde", m2["ok"] and not m2["kendi"] and "eposta" in m2["eylemler"] and "teams" in m2["eylemler"], m2["eylemler"])
m1 = yapi.eylem_menu(C, AD1, TAKVIM, kimlik_f=kimlik_f)
bak("yalnız ilk ad ('Ayşe') ve grafta aynı ilk adlı başka biri var: kendi sayılmaz", m1["ok"] and not m1["kendi"] and "eposta" in m1["eylemler"], m1["eylemler"])
bak("yalnız ilk ad, aynı ilk adlı başka kimse bilinmiyorsa kendi", yapi.kendi_mi("Ayşe", "", ["Ayşe Deneme", "Can Örnek"]) and not yapi.kendi_mi("Ayşe", "", ["Ayşe Doruk"]))
json.dump({"ad": "Ayşe Deneme", "eposta_adres": "ayse.deneme" + AT + "firma.test"}, open(AY, "w")); time.sleep(0.01); os.utime(AY, (time.time() + 5, time.time() + 5))
bak("e-posta önce: adı aynı ama adresi farklı olan kendi değil; adresi kullanıcınınki olan (adı farklı yazılmış olsa da) kendi",
    not yapi.kendi_mi("Ayşe Deneme", "ayse.d" + AT + "baska.test") and yapi.kendi_mi("A. Deneme", "ayse.deneme" + AT + "firma.test") and yapi.kendi_mi("Ayşe Deneme", ""))
yapi.ata(C, AD2, {"sahip": {"ad": "Ayşe Deneme", "eposta": "ayse.d" + AT + "baska.test"}}); m3 = yapi.eylem_menu(C, AD2, TAKVIM, kimlik_f=kimlik_f)
bak("menü: sahibin adı kullanıcınınkiyle aynı ama e-postası başka → taslak seçenekleri var, Teams pasif değil", not m3["kendi"] and "teams" in m3["eylemler"] and m3["pasif"] == {}, (m3["kendi"], m3["pasif"]))
json.dump({"ad": "Ayşe Deneme"}, open(AY, "w")); os.utime(AY, (time.time() + 10, time.time() + 10))
# --- 7 Kasım: karar taslağı metni (onaylanmış metin) — onaylayan kullanıcıysa kararı isteyene "onayladım", değilse onaylayana "onayını bekliyor" ---
def msj(r): return urllib.parse.parse_qs(urllib.parse.urlsplit(r["taslak"]["teams"] if "taslak" in r else r["teams"]).query)["message"][0]
KX = {"tur": "karar", "metin": "Bütçe 120 bin", "tarih": "2026-11-05"}
bak("karar taslağı (kullanıcı onaylayan): onaylanmış metin aynen", msj(yapi.taslak_icerik(KX, "teams", ["can" + AT + "x.test"], "Can Örnek", dil="tr", ben_onayladi=True))
    == 'Merhaba Can, 5 Kasım toplantısındaki kararı onayladım: "Bütçe 120 bin". Uygulamaya geçebilirsin. Eklemek istediğin bir şey varsa yazar mısın?')
bak("karar taslağı (onaylayan başkası): onaylanmış metin aynen", msj(yapi.taslak_icerik(KX, "teams", ["can" + AT + "x.test"], "Can Örnek", dil="tr", ben_onayladi=False))
    == 'Merhaba Can, 5 Kasım toplantısındaki karar: "Bütçe 120 bin". Onayını bekliyor. İtirazın varsa yazar mısın?')
t0 = yapi.taslak_icerik(dict(KX, tarih=""), "eposta", ["can" + AT + "x.test"], "Can Örnek", dil="tr", ben_onayladi=True)
bak("tarihsiz karar: 'toplantısındaki' düşer; e-posta gövdesi aynı cümleler, büyük harfle", msj(t0) == 'Merhaba Can, kararı onayladım: "Bütçe 120 bin". Uygulamaya geçebilirsin. Eklemek istediğin bir şey varsa yazar mısın?'
    and t0["govde"] == 'Merhaba Can,\n\nKararı onayladım: "Bütçe 120 bin". Uygulamaya geçebilirsin. Eklemek istediğin bir şey varsa yazar mısın?\n\nTeşekkürler' and t0["konu"] == "Karar: Bütçe 120 bin", t0)
e1 = msj(yapi.taslak_icerik(KX, "teams", ["can" + AT + "x.test"], "Can Örnek", dil="en", ben_onayladi=True)); e2 = msj(yapi.taslak_icerik(KX, "teams", ["can" + AT + "x.test"], "Can Örnek", dil="en", ben_onayladi=False))
bak("karar taslağı İngilizce: iki durum, okunur tarih", e1 == 'Hi Can, I\'ve approved the decision from the November 5 meeting: "Bütçe 120 bin". You can go ahead. Is there anything you\'d like to add?'
    and e2 == 'Hi Can, the decision from the November 5 meeting: "Bütçe 120 bin". It\'s awaiting your approval. If you have any objections, could you let me know?', (e1, e2))
yapi.ata(C, KR, {"onaylayan": {"ad": "Zeynep Kaya"}}); r1 = eylem(KR, "teams", {})
bak("uçtan uca: onaylayan başkası → taslak ona, 'Onayını bekliyor'", r1["ok"] and "Onayını bekliyor" in msj(r1) and msj(r1).startswith("Merhaba Zeynep,"), r1)
yapi.ata(C, KR, {"onaylayan": {"ad": "Ayşe Deneme", "ben": True}, "isteyen": {"ad": "Zeynep Kaya"}}); r2 = eylem(KR, "teams", {})
bak("uçtan uca: onaylayan kullanıcı → taslak kararı isteyene, 'kararı onayladım'", r2["ok"] and "kararı onayladım" in msj(r2) and msj(r2).startswith("Merhaba Zeynep,"), r2)
print("ÖRNEK:", mesaj)
# --- Acil toplantı (aktarici/eylem-menu.py: _at_*, toplanti_hazirla): menüde seçenek, davetliler, üç platformun bağlantısı, olay ---
D3 = "2026-11-02-1000-Acil-Deneme"; dokum(C, D3)
yapi.graf_yaz(C, {"baslik": "Acil deneme", "tarih": "2026-11-02", "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "is", "metin": "Fiyat & teklif: ürün özeti #1 (şğüıöç)", "sahip": "Zeynep Kaya", "saat": "10:01:00"},
    {"tur": "is", "metin": "Kendi işim", "sahip": "Ayşe Deneme", "saat": "10:02:00"},
    {"tur": "is", "metin": "Adresi olmayan iş", "sahip": "Bilinmez Kişi", "saat": "10:03:00"},
    {"tur": "karar", "metin": "Acil karar metni", "kim": "Zeynep Kaya", "saat": "10:04:00", "netlik": "ortuk"}]}]}, D3 + ".md")
yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5))
AI, AK, AB, AR = _id("Fiyat & teklif: ürün özeti #1 (şğüıöç)", "s"), _id("Kendi işim", "s"), _id("Adresi olmayan iş", "s"), _id("Acil karar metni", "k")
ZEP = "zeynep.kaya" + AT + "firma.test"
ns["AYAR"].pop("toplanti_platformlari", None); ns["AYAR"].pop("zoom_baglanti", None)
ma = ns["kayit_menu_view"]("/kayit-menu?id=" + AI)
bak("acil toplantı: iş menüsünde seçenek (Claude'dan önce), platformlar varsayılan sırada", ma["ok"] and "toplanti" in ma["eylemler"] and ma["eylemler"].index("toplanti") == ma["eylemler"].index("claude") - 1
    and ma["toplanti"]["platformlar"] == ["teams", "meet", "zoom"], ma)
bak("davetli: sahip e-postasıyla (kimlik eşlemesinden), e-posta eksiği yok", ma["toplanti"]["davetli"] == [{"ad": "Zeynep Kaya", "eposta": ZEP}] and ma["toplanti"]["eposta_yok"] == [], ma["toplanti"])
mk = ns["kayit_menu_view"]("/kayit-menu?id=" + AK)
bak("kendi işimde kullanıcı davetliden çıkar (davetli yok)", "toplanti" in mk["eylemler"] and mk["toplanti"]["davetli"] == [] and mk["toplanti"]["eposta_yok"] == [], mk.get("toplanti"))
mb = ns["kayit_menu_view"]("/kayit-menu?id=" + AB)
bak("e-postası olmayan kişi davetliye girmez, adıyla belirtilir", mb["toplanti"]["davetli"] == [] and mb["toplanti"]["eposta_yok"] == ["Bilinmez Kişi"], mb["toplanti"])
yapi.ata(C, AR, {"onaylayan": {"ad": "Ayşe Deneme", "ben": True}, "isteyen": {"ad": "Zeynep Kaya"}}); mr = ns["kayit_menu_view"]("/kayit-menu?id=" + AR)
bak("karar: isteyen ve onaylayan aranır, kullanıcı (onaylayan) hariç", "toplanti" in mr["eylemler"] and [d["eposta"] for d in mr["toplanti"]["davetli"]] == [ZEP], mr["toplanti"])
yapi.kayit_durum(C, AI, "yapildi"); bak("kapanmış işte seçenek yok", "toplanti" not in ns["kayit_menu_view"]("/kayit-menu?id=" + AI)["eylemler"]); yapi.kayit_durum(C, AI, "acik")
mg = ns["kayit_menu_view"]("/kayit-menu?id=" + GIZLI_IS); bak("gizli toplantı kaydında menü de seçenek de yok", not mg["ok"] and "toplanti" not in json.dumps(mg))
n = olay_say(C); rg = ns["kayit_eylem_islem"]({"id": GIZLI_IS, "eylem": "toplanti", "platform": "teams"}); bak("gizli kayda toplantı kurulmaz, olay yok", not rg["ok"] and rg["err"] == "gizli" and olay_say(C) == n, rg)
# bağlantılar (saf işlev; saat sabit: 12:00 yerel → +30 dk)
x = yapi.ortak_kayit(C, AI); dv = [{"ad": "Zeynep Kaya", "eposta": ZEP}, {"ad": "Can Örnek", "eposta": "can" + AT + "x.test"}]; th = ns["toplanti_hazirla"]
tt = th(x, "teams", dv, simdi=SIMDI); u = urllib.parse.urlsplit(tt["url"]); q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
bak("Teams: planlama ekranı (teams.microsoft.com/l/meeting/new), sorgu doğru kodlu (Türkçe, &, #, boşluk)", u.scheme == "https" and u.netloc + u.path == "teams.microsoft.com/l/meeting/new"
    and q["subject"] == ["Acil: Fiyat & teklif: ürün özeti #1 (şğüıöç)"] and "&teklif" not in tt["url"] and "#" not in tt["url"] and q["attendees"] == [ZEP + ",can" + AT + "x.test"], tt["url"])
bak("Teams: saat aralığı tam 30 dk, ISO + saat dilimi farkı; gündem notunda metin ve kaynak toplantı", datetime.datetime.fromisoformat(q["endTime"][0]) - datetime.datetime.fromisoformat(q["startTime"][0]) == datetime.timedelta(minutes=30)
    and datetime.datetime.fromisoformat(q["startTime"][0]) == SIMDI and "Gündem: Fiyat & teklif" in q["content"][0] and "Acil deneme (2 Kasım)" in q["content"][0], q)
tm = th(x, "meet", dv, simdi=SIMDI); u = urllib.parse.urlsplit(tm["url"]); q = urllib.parse.parse_qs(u.query)
d1, d2 = q["dates"][0].split("/"); f = lambda t: datetime.datetime.strptime(t, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
bak("Meet: Google Takvim şablonu, UTC aralık 30 dk ve şimdiye denk, davetliler add'da, gündem details'te", u.netloc + u.path == "calendar.google.com/calendar/render" and q["action"] == ["TEMPLATE"] and f(d1) == SIMDI.astimezone(datetime.timezone.utc)
    and f(d2) - f(d1) == datetime.timedelta(minutes=30) and q["add"] == [ZEP + ",can" + AT + "x.test"] and "Kaynak: Acil deneme (2 Kasım) toplantısı" in q["details"][0] and q["text"][0].startswith("Acil: "), tm["url"])
tz = th(x, "zoom", dv, simdi=SIMDI)
bak("Zoom (bağlantı ayarda yok): zoom.us/start açılır, davet metni panoya (konu, davetliler, gündem)", tz["url"] == "https://zoom.us/start" and ZEP in tz["kopyala"] and "Gündem: Fiyat" in tz["kopyala"] and tz["kopyala"].startswith("Acil: "), tz)
tz2 = th(x, "zoom", dv, simdi=SIMDI, zoom_baglanti="https://firma.zoom.test/j/123?pwd=a b"); q = urllib.parse.parse_qs(urllib.parse.urlsplit(tz2["url"]).query)
bak("Zoom (bağlantı ayarda): Takvim şablonu, bağlantı yer ve gündem notunda", "calendar.google.com" in tz2["url"] and "kopyala" not in tz2 and q["location"] == ["https://firma.zoom.test/j/123?pwd=a b"] and "Zoom: https://firma.zoom.test" in q["details"][0], tz2["url"])
te = th(x, "teams", [], simdi=SIMDI, en=True); bak("İngilizce konu ve gündem; davetlisiz bağlantı bozulmaz", urllib.parse.parse_qs(urllib.parse.urlsplit(te["url"]).query)["subject"][0].startswith("Urgent: ") and "attendees=&" in te["url"] and "Agenda: " in te["gundem"] and "November 2" in te["gundem"], te)
uz = th(dict(x, metin="x" * 300), "teams", dv, simdi=SIMDI); bak("konu kısaltılır", len(uz["konu"]) <= 120, len(uz["konu"]))
# uç: olay, geri alınmazlık, ayar sırası
n = olay_say(C); r = ns["kayit_eylem_islem"]({"id": AI, "eylem": "toplanti", "platform": "meet"}); son = son_olaylar(C, 1)[-1]
bak("POST toplanti: bağlantı döner, tam bir olay, kaynak eylem, adres olayda yok", r["ok"] and r["toplanti"]["platform"] == "meet" and r["toplanti"]["davetli"] == 1 and olay_say(C) == n + 1 and son[2] == "eylem"
    and ZEP not in str(db(C).execute("SELECT veri FROM olay ORDER BY saat DESC LIMIT 1").fetchone()[0]) and "Geri al" not in str(r), (r, son))
bak("toplantı olayı Geri al'a girmez (menüde geri_al onu göstermez)", (yapi.son_geri_alinabilir(C, AI) or {}).get("olay_id") != r["olay"], r["olay"])
ns["AYAR"]["toplanti_platformlari"] = ["Zoom", "teams", "yok", "zoom"]; ms = ns["kayit_menu_view"]("/kayit-menu?id=" + AI)
bak("ayar: platform sırası (ilk varsayılan), bilinmeyen ve yinelenen düşer", ms["toplanti"]["platformlar"] == ["zoom", "teams"], ms["toplanti"])
rv = ns["kayit_eylem_islem"]({"id": AI, "eylem": "toplanti"}); bak("platform verilmezse ayardaki ilki", rv["ok"] and rv["toplanti"]["platform"] == "zoom" and rv["toplanti"]["url"] == "https://zoom.us/start", rv)
rm = ns["kayit_eylem_islem"]({"id": AI, "eylem": "toplanti", "platform": "meet"}); bak("ayarda olmayan platform reddedilir", not rm["ok"], rm)
ns["AYAR"]["zoom_baglanti"] = "javascript:alert(1)"; bak("zoom_baglanti yalnız https", ns["_at_zoom"]() == "")
ns["AYAR"].pop("toplanti_platformlari", None); ns["AYAR"].pop("zoom_baglanti", None)
print("\nhepsi geçti" if not hata else f"\nKALDI: {len(hata)}"); sys.exit(1 if hata else 0)
