#!/usr/bin/env python3
# Kesişim F1 (kesisim.py): yapay proje veritabanı (sqlite) + yapay Tazı dizini (tazi.indeksle ile kurulur, şema uyumu da sınanır) → beklenen bulgu seti. Her tür için olumlu ve olumsuz durum,
# id kararlılığı, durum taşıma (yeni → sürüyor → kapandı, ertelendi korunur), gizlilik süzgeci (#53, gizli kip, beta), salt okuma, okunamayan veritabanı, belirsiz aday teslimi, süre.
# Ağ ve port yok. PYTHONDONTWRITEBYTECODE=1 python3 test/kesisim.py   (kaldı → çıkış 1)
import datetime, hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOD)
os.environ["TAZI_VT"] = "-"; os.environ.pop("TAZI_DIR", None)
T0 = tempfile.mkdtemp(prefix="suflor-kesisim-ayar-"); os.environ["SUFLOR_AYAR"] = os.path.join(T0, "ayar.json"); json.dump({}, open(os.environ["SUFLOR_AYAR"], "w"))  # gerçek izleme listesi/ayar karışmasın
import baglayici, kesisim, tazi

T = tempfile.mkdtemp(prefix="suflor-kesisim-")
VT, TD, CANLI = os.path.join(T, "vt.db"), os.path.join(T, "tazi"), os.path.join(T, "canli")
os.makedirs(CANLI); os.makedirs(os.path.join(TD, "dosya"))
SIMDI = datetime.datetime(2026, 11, 12, 8, 0, 0)
hata = []
AT = "@"   # tarama düz e-posta kalıbını yakalıyor; adresler çalışma anında birleştirilir
def ok(ad, c, ek=""):
    print(("ok   " if c else "KALDI ") + ad + ("" if c else f"  {ek}"))
    if not c: hata.append(ad)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

# ---------- yapay proje veritabanı ----------
con = sqlite3.connect(VT)
con.executescript("""
CREATE TABLE kisi (id TEXT PRIMARY KEY, ad TEXT NOT NULL, lakap TEXT, gorev TEXT, ekip TEXT, konum TEXT, gorusme_kodu TEXT, durum TEXT, tur TEXT DEFAULT 'kisi', kaynak TEXT, notlar TEXT, guncelleme TEXT);
CREATE TABLE kisi_takma (kisi_id TEXT, ad TEXT NOT NULL, baglam TEXT);
CREATE TABLE hesap (adres TEXT PRIMARY KEY, kisi_id TEXT, tur TEXT, alan_adi TEXT, workspace_durum TEXT, son_giris TEXT, iki_adim TEXT, iki_adim_tarih TEXT, yonetici_rolu TEXT, teyit TEXT, kaynak TEXT, notlar TEXT, guncelleme TEXT);
CREATE TABLE dis_firma (alan_adi TEXT PRIMARY KEY, ad TEXT, tur TEXT, ilk_gorulme TEXT, son_gorulme TEXT, temas TEXT, etkinlik_sayisi INTEGER, web_ozet TEXT, kaynak_url TEXT, risk_not TEXT, guven TEXT, guncelleme TEXT);
CREATE TABLE takvim_etkinlik (id TEXT PRIMARY KEY, seri_id TEXT, baslangic TEXT, sure_dk INTEGER, baslik TEXT, duzenleyen TEXT, katilimcilar TEXT, takvimler TEXT, tekrar TEXT, ic_dis TEXT, dis_alanlar TEXT, kisisel_adres TEXT, toplanti_id TEXT, okuma TEXT, kaynak TEXT);
CREATE TABLE guncelleme_onerisi (id INTEGER PRIMARY KEY, tarih TEXT NOT NULL, metin TEXT NOT NULL, kisi TEXT, sistem TEXT, alan TEXT, deger TEXT, tur TEXT DEFAULT 'beyan', kaynak TEXT, link TEXT, durum TEXT NOT NULL DEFAULT 'bekliyor', sonuc TEXT, yazan TEXT, kayit_zamani TEXT, islenme TEXT);
CREATE TABLE celiski (id INTEGER PRIMARY KEY, kisi_id TEXT, sistem TEXT, kayittaki_ifade TEXT, neden TEXT, cozum TEXT, durum TEXT DEFAULT 'Açık', kaynak TEXT);
CREATE TABLE ayar (anahtar TEXT PRIMARY KEY, deger TEXT, guncelleme TEXT);
CREATE TABLE okuma (id INTEGER PRIMARY KEY, kaynak TEXT, zaman TEXT, satir INTEGER, ozet TEXT);
CREATE TABLE olay (id INTEGER PRIMARY KEY, tarih TEXT, metin TEXT, kaynak TEXT, link TEXT, karar_no INTEGER, yazan TEXT, kayit_zamani TEXT);
""")
con.executemany("INSERT INTO kisi(id,ad,durum,tur) VALUES(?,?,?,?)", [("ali", "Ali Veli", "Aktif", "kisi"), ("kerem", "Kerem Demir", "Aktif", "dis"), ("eski", "Eski Kisi", "Birleştirildi", "kisi")])
con.executemany("INSERT INTO hesap(adres,kisi_id,tur,alan_adi) VALUES(?,?,?,?)", [("ali" + AT + "sirket.test", "ali", "sirket", "sirket.test"), ("kerem" + AT + "disbir.test", "kerem", "dis", "disbir.test"), ("ali" + AT + "gmail.com", "ali", "kisisel", "gmail.com")])
con.executemany("INSERT INTO dis_firma(alan_adi,ad,web_ozet,kaynak_url,guncelleme) VALUES(?,?,?,?,?)", [
    ("alfa.test", "Alfa Teknoloji GmbH", "Hannover merkezli siber güvenlik hizmetleri sağlayıcısı, olay müdahalesi ve izleme", "https://alfa.test", "2026-09-01T10:00"),
    ("beta.test", "Beta Lojistik", "İstanbul merkezli lojistik ve gümrük danışmanlığı şirketi", "https://beta.test", "2026-11-05T10:00")])
con.executemany("INSERT INTO takvim_etkinlik(id,baslangic,baslik,dis_alanlar,okuma) VALUES(?,?,?,?,?)", [
    ("ev1", "2026-11-13T10:00", "Alfa görüşmesi", '["alfa.test","gama.test","gmail.com","sirket.test"]', "2026-11-09T08:39"),
    ("ev2", "2026-11-20T10:00", "Delta toplantısı", '["delta.test"]', "2026-11-09T08:39"),
    ("ev3", "2026-11-14T10:00", "Doktor randevusu", '["ozel.test"]', "2026-11-09T08:39"),
    ("ev4", "2026-12-30T10:00", "Uzak toplantı", '["uzak.test"]', "2026-11-09T08:39")])
con.executemany("INSERT INTO guncelleme_onerisi(id,tarih,metin,kisi,sistem,durum,yazan,kayit_zamani) VALUES(?,?,?,?,?,?,?,?)", [
    (1, "2026-11-01", "Hesap eksik: x" + AT + "sirket.test", None, "Magaza", "bekliyor", "rutin", "2026-11-01T09:00"),
    (2, "2026-11-11", "Yeni hesap önerisi", None, "Slack", "bekliyor", "rutin", "2026-11-11T20:00"),
    (3, "2026-10-01", "Ali sağlık raporu nedeniyle izinli", "ali", "IK", "bekliyor", "rutin", "2026-10-01T09:00"),
    (4, "2026-10-02", "eski işlenmiş", None, "Slack", "islendi", "rutin", "2026-10-02T09:00")])
con.executemany("INSERT INTO celiski(id,kisi_id,sistem,kayittaki_ifade,neden,durum) VALUES(?,?,?,?,?,?)", [
    (1, "ali", "Magaza", "CMO", "Unvan iki kayıtta farklı: CMO ile Board Member.", "Açık"),
    (2, "ali", "Slack", "x", "kapanmış çelişki", "Kapandı"),
    (3, "ali", "IK", "y", "Hastane raporu ile kayıtlı izin tarihi tutmuyor", "Açık")])
con.executemany("INSERT INTO ayar VALUES(?,?,?)", [("capraz_yargi_son", "2026-11-01T08:00", "2026-11-01T20:00"), ("basecamp_son", "2026-11-12", "2026-11-12T06:00"), ("kontrol_gunluk", "kapali", "2026-11-11T00:07")])
con.execute("INSERT INTO okuma(kaynak,zaman,satir,ozet) VALUES('Yonetim API (KONTROL)','2026-11-10T22:35',60,'x')")
con.commit(); con.close()

# ---------- yapay Tazı (tazi.indeksle ile: şema uyumu) ----------
def dosya(ad, ogeler):
    kid = tazi.slug(ad)
    json.dump({"kayit": kid, "son_no": len(ogeler), "ogeler": [dict({"no": i, "kaynak": "", "tarih": "", "eklendi": "2026-11-01", "durum": "acik"}, **o) for i, o in enumerate(ogeler, 1)]},
              open(os.path.join(TD, "dosya", kid + ".json"), "w"), ensure_ascii=False)
aday = [{"ad": "Alfa Teknoloji", "alanlar": ["alfa.test"], "neden": "elle", "tarih": "2026-09-01"},
        {"ad": "Beta Lojistik Hizmetleri", "alanlar": ["beta.test"], "neden": "elle", "tarih": "2026-09-01"},
        {"ad": "Zeta Danışmanlık", "alanlar": ["zeta.test"], "neden": "elle", "tarih": "2026-11-01"},
        {"ad": "Kerem Demir", "alanlar": [], "neden": "elle", "tarih": "2026-11-01"},
        {"ad": "Ali Veli", "alanlar": [], "neden": "elle", "tarih": "2026-11-01"}]
json.dump(aday, open(os.path.join(TD, "aday.json"), "w"), ensure_ascii=False)
dosya("Alfa Teknoloji", [{"bolum": "kimlik", "metin": "Fabrika zemini boyası ve kaplama üretimi yapan aile şirketi, Bursa", "derece": "B"},
                         {"bolum": "celiski", "metin": "Veritabanı kaydı siber güvenlik diyor; sicil boya üreticisi gösteriyor. Sicil doğrulanmalı.", "derece": "B", "kaynak": "https://sicil.test/alfa"}])
dosya("Beta Lojistik Hizmetleri", [{"bolum": "kimlik", "metin": "İstanbul merkezli lojistik ve gümrük danışmanlığı şirketi, liman hizmetleri", "derece": "B"},
                                   {"bolum": "bayrak", "metin": "Yeni bayrak: alan adı yakın zamanda yenilendi", "derece": "C", "eklendi": "2026-11-12"}])
dosya("Zeta Danışmanlık", [{"bolum": "kimlik", "metin": "Danışmanlık firması", "derece": "C"}])
dosya("Kerem Demir", [])
def b(kayit, anahtar, tur, derece, ilk, durum="yeni"):
    return {"anahtar": anahtar, "kayit": kayit, "tur": tur, "alt": "x", "deger": f"{tur} değeri", "onceki": None, "ozet": f"{tur} özeti", "kaynak": "https://x.test/" + anahtar, "tarih": ilk,
            "derece": derece, "ilk_gorulme": ilk, "son_gorulme": ilk, "durum": durum, "tarama": ilk.replace("-", ""), "kid": "claude"}
bul = [b("alfa-teknoloji", "a1", "gonderi", "C", "2026-11-12"), b("alfa-teknoloji", "a2", "haber", "B", "2026-11-12"), b("alfa-teknoloji", "a3", "dns", "A", "2026-11-12"),
       b("beta-lojistik-hizmetleri", "b1", "gonderi", "C", "2026-10-01")]
open(os.path.join(TD, "bulgular.jsonl"), "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in bul))
il = [{"kayit": "kerem-demir", "tur": "eposta", "deger": "ali" + AT + "sirket.test", "kaynak": "imza", "derece": "A", "tarih": "", "eklendi": "2026-11-01"},
      {"kayit": "ali-veli", "tur": "eposta", "deger": "ali.yeni" + AT + "sirket.test", "kaynak": "imza", "derece": "B", "tarih": "", "eklendi": "2026-11-01"},
      {"kayit": "beta-lojistik-hizmetleri", "tur": "telefon", "deger": "+90 212 000 00 00", "kaynak": "imza", "derece": "A", "tarih": "", "eklendi": "2026-11-12"}]
open(os.path.join(TD, "iletisim.jsonl"), "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in il))
json.dump({"kayitlar": {"alfa-teknoloji": {"tarih": "2026-09-20"}, "beta-lojistik-hizmetleri": {"tarih": "2026-11-10"}, "zeta-danismanlik": {"tarih": "2026-11-10"}}}, open(os.path.join(TD, "son.json"), "w"))
tazi.indeksle(TD, "-")
# fixture'ı "taze" göster: tazi.db meta saatini koşu saatine çek (indeksle gerçek saati yazar)
c = sqlite3.connect(os.path.join(TD, "tazi.db")); c.execute("UPDATE meta SET v=? WHERE k='son_indeks'", ("2026-11-12T07:50:00",)); c.commit(); c.close()
os.utime(VT, (SIMDI.timestamp(), SIMDI.timestamp()))

# izlenecek rutinler ayardan gelir (kod rutin adı taşımaz); gerçek ayar.json'a dokunulmaz
AYAR = {"kesisim_rutinler": [
    {"ad": "rutin-capraz-yargi", "iz": ["ayar:capraz_yargi_son"], "esik_sa": 36, "aciklama": "günlük 20:00"},
    {"ad": "rutin-eposta-kontrolu", "iz": ["ayar:basecamp_son", "rutin"], "esik_sa": 36, "aciklama": "2 saatte bir; yalnız yazdığı zaman iz bırakır (eşik geniş)"},
    {"ad": "rutin-takvim-haftalik", "iz": ["takvim"], "esik_sa": 192, "aciklama": "haftalık"},
    {"ad": "rutin-yonetim-kontrol", "iz": ["okuma:KONTROL"], "kapali": "ayar:kontrol_gunluk", "esik_sa": 36, "aciklama": "günlük"}]}
def calistir(canli=CANLI, simdi=SIMDI, **kw): return kesisim.kos(canli, VT, TD, ayar=AYAR, simdi=simdi, gelistirici=True, **kw)
def kume(s): return {(b["tur"], b["varlik"], b["id"][:0] + (b["kaynaklar"][0]["kayit"] if b["kaynaklar"] else "")) for b in s["bulgular"] if b["durum"] != "kapandi"}
def bul_(s, tur, varlik=None, parca=""):
    return [b for b in s["bulgular"] if b["tur"] == tur and (varlik is None or b["varlik"] == varlik) and parca in b["ozet"] and b["durum"] != "kapandi"]

h_oh, h_tz = {p: sha(p) for p in (VT, os.path.join(TD, "tazi.db"))}, {f: sha(os.path.join(TD, f)) for f in ("aday.json", "bulgular.jsonl", "iletisim.jsonl", "son.json")}
s1 = calistir()
tur_say = s1["ozet"]["tur"]
print("tür sayıları:", tur_say)
ok("beklenen küme: tür başına tam bulgu sayısı", tur_say == {"celiski": 4, "eksik": 6, "bayat": 2, "bekleyen": 1, "yeni": 4, "rutin": 1}, tur_say)

# ---- çelişki ----
ok("celiski+: Tazı açık çelişkisi → veritabanı kaydıyla iki kaynak", len(bul_(s1, "celiski", "firma:alfa.test", "kaynaklar ayrışıyor")) == 1 and
   {k["sistem"] for k in bul_(s1, "celiski", "firma:alfa.test", "kaynaklar ayrışıyor")[0]["kaynaklar"]} == {"tazi", "vt"})
ok("celiski+: e-posta başka kişiye ait (ad Kerem, adres Ali'nin)", len(bul_(s1, "celiski", "kisi:kerem", "başka bir kişiye")) == 1)
ok("celiski+: veritabanının açık çelişki kaydı tek şemada", len(bul_(s1, "celiski", "kisi:ali", "açık çelişki kaydı")) == 1)
ok("celiski-: kapalı veritabanı çelişkisi yok", not [b for b in s1["bulgular"] if "kapanmış" in b["ozet"]])
ok("celiski-: Beta için çelişki yok (ad içeriyor, açıklama örtüşüyor)", not bul_(s1, "celiski", "firma:beta.test"))
bel = [b for b in s1["bulgular"] if b["belirsiz"]]
ok("belirsiz+: Alfa açıklamaları örtüşmüyor → belirsiz aday, karşılaştırma a/b dolu", len(bel) == 1 and bel[0]["varlik"] == "firma:alfa.test" and bel[0]["karsilastirma"]["a"]["sistem"] == "vt" and bel[0]["karsilastirma"]["b"]["sistem"] == "tazi")
ad = kesisim.belirsiz_adaylar(s1)
ok("belirsiz: F2 teslim biçimi {id, metin, veri{a,b,kaynaklar,kanit}}", len(ad) == 1 and set(ad[0]) == {"id", "metin", "veri"} and ad[0]["id"] == bel[0]["id"] and ad[0]["veri"]["a"]["metin"] and ad[0]["veri"]["b"]["metin"])
ok("kanit: ortak ölçek en zayıf halka (Tazı B + K2 → B/2)", bul_(s1, "celiski", "firma:alfa.test", "kaynaklar ayrışıyor")[0]["kanit"]["duzey"] == 2 and bul_(s1, "celiski", "kisi:ali")[0]["kanit"] == {"ham": "K1", "duzey": 1})

# ---- eksik ----
ok("eksik+: takvimdeki dış alan dis_firma'da yok (gama.test)", len(bul_(s1, "eksik", "firma:gama.test", "dis_firma tablosunda yok")) == 1)
ok("eksik+: takvimdeki dış alan için Tazı kaydı yok (gama.test, delta.test)", len(bul_(s1, "eksik", "firma:gama.test", "Tazı kaydı yok")) == 1 and len(bul_(s1, "eksik", "firma:delta.test", "Tazı kaydı yok")) == 1)
ok("eksik+: Tazı firması veritabanında yok (zeta.test)", len(bul_(s1, "eksik", "firma:zeta.test", "kayıtlı değil")) == 1)
ok("eksik+: Tazı iletişim e-postası veritabanında yok (Ali Veli)", len(bul_(s1, "eksik", "kisi:ali", "hesap kayıtlarında yok")) == 1)
ok("eksik-: tüketici/şirket alanı ve pencere dışı etkinlik atlanır (gmail.com, sirket.test, uzak.test)", not [b for b in s1["bulgular"] if any(x in b["varlik"] for x in ("gmail.com", "sirket.test", "uzak.test"))])
ok("eksik-: alfa.test dis_firma'da ve Tazı'da var → eksik yok", not bul_(s1, "eksik", "firma:alfa.test"))

# ---- bayat ----
ok("bayat+: yarın toplantı, Tazı taraması 30 günden eski (alfa.test)", len(bul_(s1, "bayat", "firma:alfa.test", "Tazı dosyasının son taraması")) == 1)
ok("bayat+: yarın toplantı, dis_firma 30 günden eski (alfa.test)", len(bul_(s1, "bayat", "firma:alfa.test", "dis_firma kaydı")) == 1)
ok("bayat-: 14 gün penceresi içinde ama 3 günden uzak toplantıda (delta) bayat denmez", not bul_(s1, "bayat", "firma:delta.test"))
ok("bayat-: kaynaklar taze → kaynak bayatlığı bulgusu yok", not bul_(s1, "bayat", "sistem:Proje veritabanı") and all(k["durum"] != "bayat" for k in s1["kaynaklar"] if k["ad"] in ("Proje veritabanı (son değişiklik)", "Tazı dizini (tazi.db)")))

# ---- yeni ----
ok("yeni+: Tazı son 24 saat bulguları (teknik dns hariç) tek satırda", len(bul_(s1, "yeni", "firma:alfa.test", "2 yeni bulgu")) == 1)
ok("yeni+: Tazı dosyasına yeni bayrak (Beta)", len(bul_(s1, "yeni", "firma:beta.test", "yeni bayrak")) == 1)
ok("yeni+: yeni iletişim bilgisi (Beta)", len(bul_(s1, "yeni", "firma:beta.test", "yeni iletişim")) == 1)
ok("yeni+: rutinden son 24 saatte açılan öneri (id 2)", len(bul_(s1, "yeni", None, "Yeni hesap önerisi")) == 1)
ok("yeni-: eski bulgu (Beta 1 Ekim) yeni sayılmaz", not [b for b in bul_(s1, "yeni", "firma:beta.test") if "yeni bulgu" in b["ozet"]])

# ---- bekleyen ----
ok("bekleyen+: 3 günden eski öneri (id 1)", len(bul_(s1, "bekleyen", None, "Hesap eksik")) == 1 and "10 gündür" in bul_(s1, "bekleyen", None, "Hesap eksik")[0]["ozet"])
ok("bekleyen-: dünkü öneri (id 2) ve işlenmiş (id 4) bekleyen değil", not bul_(s1, "bekleyen", None, "Yeni hesap") and not bul_(s1, "bekleyen", None, "eski işlenmiş"))

# ---- rutin sağlığı ----
ok("rutin+: capraz-yargi 36 saatten eski", len(bul_(s1, "rutin", "sistem:rutin-capraz-yargi")) == 1)
ok("rutin-: eposta taze, kontrol kapalı (bulgu yok, kaynakta 'kapali'), takvim taze", not bul_(s1, "rutin", "sistem:rutin-eposta-kontrolu") and not bul_(s1, "rutin", "sistem:rutin-yonetim-kontrol") and
   any(k["ad"] == "rutin-yonetim-kontrol" and k["durum"] == "kapali" for k in s1["kaynaklar"]) and not bul_(s1, "rutin", "sistem:rutin-takvim-haftalik"))
ok("kaynak tazeliği json'da: ad, son_okuma, beklenen_sn", all({"ad", "son_okuma", "beklenen_sn", "durum"} <= set(k) for k in s1["kaynaklar"]) and any(k["ad"].startswith("Tazı dizini") for k in s1["kaynaklar"]))

# ---- gizlilik (#53) ----
metin = open(os.path.join(CANLI, "kesisim.json"), encoding="utf-8").read().casefold()
ok("gizlilik: sağlık/özel kayıt çıktıya girmez (öneri, çelişki, takvim başlığı)", not any(x in metin for x in ("sağlık", "hastane", "doktor", "ozel.test")) and s1["suzulen"]["ozel"] == 3, s1["suzulen"])
g = kesisim.kos(os.path.join(T, "g"), VT, TD, ayar=AYAR, simdi=SIMDI, gizli=True, gelistirici=True)
ok("gizlilik: gizli toplantıda hiçbir şey işlemez/yazmaz", g == {"atlandi": "gizli"} and not os.path.exists(os.path.join(T, "g")))
g = kesisim.kos(os.path.join(T, "g2"), VT, TD, ayar=AYAR, simdi=SIMDI, gelistirici=False)
ok("gizlilik: geliştirici değilse (beta) çalışmaz/yazmaz", g == {"atlandi": "gelistirici_degil"} and not os.path.exists(os.path.join(T, "g2")))
bos = os.path.join(T, "bos-kod"); os.makedirs(bos)
os.environ["SUFLOR_TEST_KOD"] = bos
ok("gelistirici_mi: .git'siz kod klasörü + ayar yok → False; ayar gelistirici:true → True", kesisim.gelistirici_mi({}) is False and kesisim.gelistirici_mi({"gelistirici": True}) is True)
del os.environ["SUFLOR_TEST_KOD"]

# ---- salt okuma ----
ok("salt okuma: veritabanı, tazi.db ve Tazı dosyaları koşudan sonra baytı baytına aynı",
   sha(VT) == h_oh[VT] and sha(os.path.join(TD, "tazi.db")) == h_oh[os.path.join(TD, "tazi.db")] and all(sha(os.path.join(TD, f)) == v for f, v in h_tz.items()))
bk = baglayici._Sqlite(VT, {}, "")
bk._calistir("INSERT INTO kisi(id,ad) VALUES('zz','Yazilmamali')")
ok("salt okuma: baglayici mode=ro yazmayı reddeder", bool(bk.son_hata) and not sqlite3.connect(VT).execute("SELECT 1 FROM kisi WHERE id='zz'").fetchall(), bk.son_hata)
kaynak = open(os.path.join(KOD, "kesisim.py"), encoding="utf-8").read()
import re
ok("salt okuma: kesisim.py'de yazan SQL yok", not re.search(r"(?i)\b(insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+table|create\s+table|indeksle\()", kaynak))

# ---- id kararlılığı, durum taşıma ----
ids1 = {b["id"] for b in s1["bulgular"]}
ok("durum: ilk koşuda hepsi yeni, jsonl'de yalnız geçiş satırları (metin yok)", all(b["durum"] == "yeni" for b in s1["bulgular"]) and
   all(set(json.loads(l)) == {"t", "id", "tur", "durum"} for l in open(os.path.join(CANLI, "kesisim.jsonl"))))
n1 = len(open(os.path.join(CANLI, "kesisim.jsonl")).readlines())
s2 = calistir(simdi=SIMDI + datetime.timedelta(hours=3))
ok("id kararlılığı: aynı veride aynı id kümesi", {b["id"] for b in s2["bulgular"]} == ids1)
ok("durum taşıma: ikinci koşuda sürüyor, ilk_gorulme korunur, jsonl büyümez", all(b["durum"] == "suruyor" and b["ilk_gorulme"] == SIMDI.isoformat() for b in s2["bulgular"]) and len(open(os.path.join(CANLI, "kesisim.jsonl")).readlines()) == n1)
# ertelendi korunur
dj = json.load(open(os.path.join(CANLI, "kesisim.json")))
hedef = bul_(s2, "bekleyen", None, "Hesap eksik")[0]["id"]
for b in dj["bulgular"]:
    if b["id"] == hedef: b["durum"] = "ertelendi"
json.dump(dj, open(os.path.join(CANLI, "kesisim.json"), "w"), ensure_ascii=False)
s3 = calistir(simdi=SIMDI + datetime.timedelta(hours=4))
ok("durum taşıma: ertelendi sonraki koşuda korunur", [b for b in s3["bulgular"] if b["id"] == hedef][0]["durum"] == "ertelendi")
# kapandı: öneri 1 işlendi
c = sqlite3.connect(VT); c.execute("UPDATE guncelleme_onerisi SET durum='islendi' WHERE id=1"); c.commit(); c.close()
s4 = calistir(simdi=SIMDI + datetime.timedelta(hours=5))
k = [b for b in s4["bulgular"] if b["id"] == hedef]
ok("durum taşıma: kaynaktan kalkan bulgu kapandı olur, bir koşu sonra düşer", len(k) == 1 and k[0]["durum"] == "kapandi" and s4["ozet"]["kapandi"] == 1 and
   any(json.loads(l)["id"] == hedef and json.loads(l)["durum"] == "kapandi" for l in open(os.path.join(CANLI, "kesisim.jsonl"))))
s5 = calistir(simdi=SIMDI + datetime.timedelta(hours=6))
ok("durum taşıma: kapandı bir sonraki koşuda listeden düşer", hedef not in {b["id"] for b in s5["bulgular"]})
c = sqlite3.connect(VT); c.execute("UPDATE guncelleme_onerisi SET durum='bekliyor' WHERE id=1"); c.commit(); c.close()
os.utime(VT, (SIMDI.timestamp(), SIMDI.timestamp()))

# ---- bayat kaynak / okunamayan veritabanı / boş Tazı ----
s6 = kesisim.kos(os.path.join(T, "c6"), VT, TD, ayar=AYAR, simdi=SIMDI + datetime.timedelta(days=6), gelistirici=True)
ok("bayat+: veritabanı 48 sa, Tazı dizini 4 gün hareketsiz (6 gün sonra) → kaynak bayatlığı", len(bul_(s6, "bayat", "sistem:Proje veritabanı")) == 1 and len(bul_(s6, "bayat", "sistem:Tazı dizini")) == 1)
ok("rutin+: eposta rutini ve Tazı rutini sessiz", len(bul_(s6, "rutin", "sistem:rutin-eposta-kontrolu")) == 1 and len(bul_(s6, "rutin", "sistem:tazi-toplanti-dosyalari")) == 1)
s7 = kesisim.kos(os.path.join(T, "c7"), os.path.join(T, "yok.db"), TD, ayar=AYAR, simdi=SIMDI, gelistirici=True)
ok("Veritabanı okunamazsa: çökmez, 'okunamadı' bayat bulgusu, Tazı kuralları sürer (Tazı çelişkisi var)", len(bul_(s7, "bayat", "sistem:Proje veritabanı", "okunamadı")) == 1 and bool(bul_(s7, "celiski", None, "kaynaklar ayrışıyor")))
s8 = kesisim.kos(os.path.join(T, "c8"), VT, os.path.join(T, "tazi-yok"), ayar=AYAR, simdi=SIMDI, gelistirici=True)
ok("Tazı dizini yoksa: çökmez, veritabanı kuralları sürer (bekleyen, rutin)", bool(bul_(s8, "bekleyen")) and not [b for b in s8["bulgular"] if "tazi" in {k["sistem"] for k in b["kaynaklar"]}])
ok("Tazı yokken dizin oluşturulmadı (yazma yok)", not os.path.exists(os.path.join(T, "tazi-yok")))

# ---- hız ve CLI ----
ok("hız: tam koşu < 10 sn", s1["sure_sn"] < 10, s1["sure_sn"])
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "kesisim.py"), "kos", "--canli", os.path.join(T, "cli"), "--vt", VT, "--tazi", TD, "--json"], capture_output=True, text=True, env=env)
try: cj = json.loads(r.stdout)
except ValueError: cj = {}
ok("CLI: kos --json geçerli JSON, kesisim.json yazıldı", r.returncode == 0 and cj.get("surum") == 1 and os.path.isfile(os.path.join(T, "cli", "kesisim.json")), r.stderr[-300:])
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "kesisim.py"), "kos", "--canli", os.path.join(T, "cli2"), "--vt", VT, "--tazi", TD, "--kuru"], capture_output=True, text=True, env=env)
ok("CLI: --kuru dosya yazmaz", r.returncode == 0 and not os.path.exists(os.path.join(T, "cli2", "kesisim.json")), r.stdout[-200:])
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "kesisim.py"), "belirsiz", "--canli", os.path.join(T, "cli3"), "--vt", VT, "--tazi", TD], capture_output=True, text=True, env=env)
ok("CLI: belirsiz aday listesi JSON", r.returncode == 0 and isinstance(json.loads(r.stdout), list) and len(json.loads(r.stdout)) == 1, r.stdout[-200:])
shutil.rmtree(T, ignore_errors=True); shutil.rmtree(T0, ignore_errors=True)
if hata: print("KALDI:", hata); sys.exit(1)
print("tamam")
