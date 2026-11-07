#!/usr/bin/env python3
# A1 bağlayıcı sözleşmesi (baglayici.py): ayar çözümü (yeni şema baglayici.kayit + eski veritabani.*/kayit_*), kayıt veritabanı (SqliteKayit), proje.db (ProjeVT),
# aktarıcı tarafı önbellek okuyucusu, güvenlik (yazma SQL'i, çoklu komut, gizli sütun), bayraklar, is_satiri ↔ yapi.belge_onerileri.
# Geçici klasörde yapay veriyle; gerçek ayara, canli klasörüne ve proje verisine dokunmaz. ~2 sn, model yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/baglayici.py      (kaldı → çıkış 1)
import contextlib, copy, hashlib, io, json, os, shutil, sqlite3, sys, tempfile, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import baglayici as B

T = tempfile.mkdtemp(prefix="suflor-bag-")
proje, uyg, canli = os.path.join(T, "proje"), os.path.join(T, "uyg"), os.path.join(T, "canli")
for d in (proje, uyg, canli): os.makedirs(d)
sonuc = []
def ok(ad, kosul, ayrinti=""):
    sonuc.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad + ("" if kosul or not ayrinti else f"  [{str(ayrinti)[:300]}]"))

def ayar_yaz(a):
    y = os.path.join(T, "ayar.json"); json.dump(a, open(y, "w"), ensure_ascii=False, indent=1); return y
TEMEL = {"alan": "Test", "port": 1, "uygulama": uyg, "proje": proje}
Q = {"kisiler": "SELECT ad || coalesce(', ' || lakap, ''), ad || ' — ' || gorev FROM kisi",
     "kisi_adres": "SELECT ad || coalesce(', ' || lakap, ''), eposta FROM kisi WHERE eposta IS NOT NULL",
     "gorevler": "SELECT metin, sahip, vade, konum FROM gorev", "sistemler": "SELECT ad FROM sistem"}
ESKI = dict(TEMEL, veritabani=dict({"yol": "kayit.db", "kurallar": ["kural bir"]}, **Q),
            kayit_komutu=["/usr/bin/python3", "betik.py"], kayit_alt_komutlar=["ekle"], kayit_sure_sn=20)
YENI = dict(TEMEL, baglayici={"kayit": {"tur": "sqlite_kayit", "ad": "Kayıt veritabanı", "acik": True, "yol": "kayit.db", "sorgular": dict(Q), "kurallar": ["kural bir"],
                                     "yazma": {"komut": ["/usr/bin/python3", "betik.py"], "alt_komutlar": ["ekle"], "sure_sn": 20}}})

try:
    # --- P1: ayar ------------------------------------------------------------------------------------------------------------------------
    # 1. ayar boş, proje.db yok
    ok("1. ayar boş, proje.db yok: yukle() == [], etkin_vt() None", B.yukle(dict(TEMEL)) == [] and B.etkin_vt(dict(TEMEL)) is None)
    # 2. ayar boş, proje.db var
    pdb = os.path.join(uyg, "proje.db"); c = sqlite3.connect(pdb)
    c.executescript("CREATE TABLE kisi (ad TEXT, takma_adlar TEXT, roller TEXT, kurumlar TEXT, kaynak TEXT);"
                    "INSERT INTO kisi VALUES ('Deneme Kisi', 'Deneme', 'Satış', 'Örnek AŞ', 'a.xlsx');"); c.commit(); c.close()
    e = B.etkin_vt(dict(TEMEL))
    ok("2. proje.db varsa etkin_vt().tur == 'proje'; proje_vt: false ile None", e is not None and e.tur == "proje" and B.etkin_vt(dict(TEMEL, proje_vt=False)) is None
       and B.yukle(dict(TEMEL)) == [])
    # 3. eşdeğerlik
    hata = io.StringIO()
    with contextlib.redirect_stderr(hata): ce, cy = B.ayar_coz(ESKI), B.ayar_coz(YENI)
    ok("3. yalnız eski anahtarlar ile yalnız yeni şema: ayar_coz birebir aynı", ce == cy and ce["kayit"]["yol"] == "kayit.db" and ce["kayit"]["yazma"]["sure_sn"] == 20
       and ce["kayit"]["sorgular"] == Q and not hata.getvalue(), json.dumps([ce, cy], ensure_ascii=False))
    # 4. ikisi birden, farklı
    IKI = copy.deepcopy(ESKI); IKI["baglayici"] = {"kayit": {"yol": "yeni.db", "sorgular": {"gorevler": "SELECT 1, 2"}}}
    hata = io.StringIO()
    with contextlib.redirect_stderr(hata): c1 = B.ayar_coz(IKI); c2 = B.ayar_coz(IKI)
    satir = hata.getvalue().splitlines()
    ok("4. ikisi birden: yeni kazanır, eksik alan eskiden; gölgeleme satırı bir kez (alan başına)",
       c1 == c2 and c1["kayit"]["yol"] == "yeni.db" and c1["kayit"]["sorgular"]["gorevler"] == "SELECT 1, 2" and c1["kayit"]["sorgular"]["kisiler"] == Q["kisiler"]
       and c1["kayit"]["kurallar"] == ["kural bir"] and sum("baglayici.kayit.yol eski anahtarı gölgeliyor" in s for s in satir) == 1
       and sum("baglayici.kayit.sorgular.gorevler" in s for s in satir) == 1 and len(satir) == 2, satir)
    # 5. acik:false
    KAPALI = copy.deepcopy(ESKI); KAPALI["baglayici"] = {"kayit": {"acik": False}}
    ok("5. acik:false: bağlayıcı yok, eski anahtar da okunmaz", B.ayar_coz(KAPALI) == {} and B.yukle(KAPALI) == [] and B.etkin_vt(dict(KAPALI, proje_vt=False)) is None)
    # 6. ayar dosyası değişmez
    y = ayar_yaz(IKI); h0, m0 = hashlib.sha256(open(y, "rb").read()).hexdigest(), os.path.getmtime(y)
    with contextlib.redirect_stderr(io.StringIO()):
        a = json.load(open(y)); B.ayar_coz(a); B.yukle(a); B.etkin_vt(a); [b.kisiler() for b in B.yukle(a) if "kisiler" in b.yetenekler()]
    ok("6. ayar dosyası çağrılardan sonra bayt bayt aynı", hashlib.sha256(open(y, "rb").read()).hexdigest() == h0 and os.path.getmtime(y) == m0 and a == IKI)

    # --- P2: kayıt veritabanı ve proje.db okuması ------------------------------------------------------------------------------------------------------
    DB = os.path.join(proje, "kayit.db"); c = sqlite3.connect(DB)
    c.executescript("""PRAGMA journal_mode=WAL;
    CREATE TABLE kisi (id TEXT, ad TEXT, lakap TEXT, gorev TEXT, eposta TEXT, durum TEXT, tur TEXT, guncelleme TEXT);
    INSERT INTO kisi VALUES ('a','Deneme Bir','Bir','Finans','bir\x40ornek.test,bir2\x40ornek.test','Aktif','kisi','2026-11-01'),
                            ('b','Deneme Iki',NULL,'Depo',NULL,'Aktif','kisi',NULL), ('c','Eski Kayit',NULL,'-',NULL,'Birleştirildi','kisi',NULL);
    CREATE TABLE kisi_takma (kisi_id TEXT, ad TEXT, baglam TEXT);
    INSERT INTO kisi_takma VALUES ('a','Birci',NULL), ('a','bir\x40ornek.test',NULL), ('a','Yanlis','adı değil');
    CREATE TABLE dis_firma (ad TEXT, son_gorulme TEXT); INSERT INTO dis_firma VALUES ('Ornek Firma', NULL);
    CREATE TABLE sistem (ad TEXT, guncelleme TEXT); INSERT INTO sistem VALUES ('Depo Takip', NULL);
    CREATE TABLE ajan (ad TEXT); INSERT INTO ajan VALUES ('Yardimci Ajan');
    CREATE TABLE gorev (metin TEXT, sahip TEXT, vade TEXT, konum TEXT);
    INSERT INTO gorev VALUES ('Fatura akışını yeniden kontrol et', 'Deneme Bir', '2026-11-20', 'd1'), ('Depo sayımını tamamla ve raporla', 'Deneme Iki', NULL, 'd2');
    CREATE TABLE hesap (id TEXT, ad TEXT, sifre TEXT); INSERT INTO hesap VALUES ('h1','Panel','GIZLI-DEGER');
    CREATE VIEW v_hesap AS SELECT id, ad, sifre, (sifre IS NOT NULL) AS dolu FROM hesap;""")
    c.commit(); c.close()
    with contextlib.redirect_stderr(io.StringIO()): kv = B.etkin_vt(ESKI)
    ki = kv.kisiler(); k1 = next((k for k in ki if k["ad"] == "Deneme Bir"), {})
    ok("7a. kayıt veritabanı kisiler(): ad + kaynak, takma ve adresler ayrılmış", kv.tur == "sqlite_kayit" and all(k.get("ad") and k.get("kaynak") == "kayit" for k in ki)
       and k1.get("takma") == ["Bir"] and k1.get("adresler") == ["bir\x40ornek.test", "bir2\x40ornek.test"] and k1.get("ozet") == "Deneme Bir — Finans", ki)
    isl = kv.acik_isler("Deneme Bir")
    ok("7b. acik_isler(kişi) sahibe göre süzer; kayıt biçimi", len(kv.acik_isler()) == 2 and len(isl) == 1 and isl[0]["vade"] == "2026-11-20"
       and isl[0]["durum"] == "acik" and isl[0]["kaynak"] == "kayit" and isl[0]["konum"] == "d1", isl)
    # terimler(): eski _vt_terimler çıktısıyla birebir (aynı sorgu, aynı biçim)
    import pathlib
    con = sqlite3.connect(pathlib.Path(DB).resolve().as_uri() + "?mode=ro", uri=True); rows = con.execute(B.VT_TERIMLER_SORGU).fetchall(); con.close()
    eski_t = [{"terim": str(r[0]).strip(), "tur": str(r[1] or "") if len(r) > 1 else "", "takma": [x.strip() for x in str((r[2] if len(r) > 2 else "") or "").split("|") if x.strip()]}
              for r in rows if r and r[0] and str(r[0]).strip()]
    tr = kv.terimler()
    ok("7c. terimler() biçimi eski _vt_terimler ile aynı; birleştirilmiş kişi ve 'adı değil' takması yok", tr == eski_t and {"terim": "Deneme Bir", "tur": "kisi", "takma": ["Birci"]} in tr
       and not any(t["terim"] == "Eski Kayit" for t in tr) and {"terim": "Yardimci Ajan", "tur": "sistem", "takma": []} in tr, tr)
    yy = []
    for ad, f in (("kararlar", kv.kararlar), ("belgeler", kv.belgeler)):
        try: f(); yy.append(False)
        except B.YetenekYok: yy.append(True)
    ok("7d. kararlar() sorgu yoksa, belgeler() her zaman YetenekYok; yetenekler kümesi", all(yy) and "kararlar" not in kv.yetenekler()
       and {"kisiler", "acik_isler", "terimler", "sor"} <= kv.yetenekler())
    # 8. değişme saati
    mt0 = kv.degisim_zamani(); time.sleep(0.05)
    c = sqlite3.connect(DB); c.execute("PRAGMA journal_mode=WAL"); c.execute("INSERT INTO sistem VALUES ('Yeni Sistem', NULL)"); c.commit()
    mt1 = kv.degisim_zamani(); c.close()
    yok = B.SqliteKayit({"yol": "yok.db"}, proje=proje, uygulama=uyg)
    ok("8. degisim_zamani() WAL'daki yazmada büyür; dosya yoksa None", mt0 and mt1 and mt1 > mt0 and yok.degisim_zamani() is None, (mt0, mt1))
    # 9. okunamayan yol
    yok.sorgular = dict(Q)
    try: r9 = (yok.satirlar("sistemler"), yok.kisiler(), yok.acik_isler(), yok.terimler()); ist = None
    except Exception as ex: r9, ist = None, ex
    ok("9. okunamayan yol: istisna yok, [] döner, son_hata dolu", ist is None and r9 == ([], [], [], []) and yok.son_hata, (ist, r9, yok.son_hata))
    # 10. güvenlik: bağlayıcı üzerinden de
    red = []
    for q in ("DELETE FROM sistem", "SELECT 1; DELETE FROM sistem", "WITH x AS (SELECT 1) INSERT INTO sistem(ad) SELECT 'z' FROM x"):
        kv.sorgular["deneme"] = q; red.append(kv.satirlar("deneme") == [])
        try: kv.sor(q); red.append(False)
        except B.BaglayiciHata: red.append(True)
    gz = []
    for q in ("SELECT sifre AS x FROM hesap", "SELECT upper(sifre) FROM hesap", "WITH v_hesap AS (SELECT sifre AS ad FROM hesap) SELECT ad FROM v_hesap",
              "SELECT sifre AS w FROM v_hesap", "SELECT hex(sifre) FROM hesap"):
        try: r = kv.sor(q)
        except B.BaglayiciHata as ex: r = str(ex)
        gz.append("GIZLI" not in r and "47495A" not in r)
    c = sqlite3.connect(DB); n = c.execute("SELECT count(*) FROM sistem").fetchone()[0]; c.close()
    ok("10. güvenlik: yazma SQL'i, çoklu komut reddedilir (satirlar + sor); gizli sütun açık dönmez; şemada [gizli]; veritabanı değişmedi",
       all(red) and all(gz) and n == 2 and "sifre [gizli]" in kv.sema_metin() and "Panel\t1" in kv.sor("SELECT ad, dolu FROM v_hesap"), (red, gz, n))
    # 11. önbellek okuyucusu
    json.dump({"kisiler": [{"adlar": ["Deneme Bir", "Bir"], "adresler": ["bir\x40ornek.test"]}], "t": 1}, open(os.path.join(canli, "vt-kisi-adres.json"), "w"))
    json.dump({"satirlar": [["Fatura akışını yeniden kontrol et", "Deneme Bir", "2026-11-20", "d1"], ["Depo sayımını tamamla", "Deneme Iki", "", "d2"]], "t": 1},
              open(os.path.join(canli, "vt-gorevler.json"), "w"))
    json.dump({"mt": 1234.5, "kontrol": round(time.time())}, open(os.path.join(canli, "vt-mt.json"), "w"))
    ob = B.onbellek_okuyucu(canli, {"adlar": ["Deneme Bir", "Bir", "Deneme Iki"], "terimler": [{"terim": "Depo Takip", "tur": "sistem", "takma": []}]})
    ok_ = ob.kisiler(); o1 = next((k for k in ok_ if k["ad"] == "Deneme Bir"), {})
    taze = ob.degisim_zamani()
    json.dump({"mt": 1234.5, "kontrol": round(time.time()) - 200}, open(os.path.join(canli, "vt-mt.json"), "w"))
    ok("11. OnbellekOkuyucu aynı sözleşme; vt-mt.json 150 sn'den eskiyse None", o1.get("adresler") == ["bir\x40ornek.test"] and o1.get("kaynak") == "kayit"
       and len(ob.acik_isler()) == 2 and len(ob.acik_isler("Deneme Iki")) == 1 and ob.terimler()[0]["terim"] == "Depo Takip" and taze == 1234.5
       and ob.degisim_zamani() is None and ob.ayricalikli_okuma is False, (ok_, taze))
    # 12. bayraklar
    ic = B.SqliteKayit({"yol": os.path.join(uyg, "ic.db")}, proje=proje, uygulama=uyg)
    elle = B.SqliteKayit({"yol": "kayit.db", "ayricalikli_okuma": False}, proje=proje, uygulama=uyg)
    ok("12. bayraklar: uygulama dışı kayıt veritabanı ayrıcalıklı, içindeki değil, ayarda açıkça verilebilir; ProjeVT değil; iki_yonlu False",
       kv.ayricalikli_okuma is True and ic.ayricalikli_okuma is False and elle.ayricalikli_okuma is False and e.ayricalikli_okuma is False
       and kv.iki_yonlu is False and e.iki_yonlu is False)
    # 13. yazma: oner() doğrular (yazmaz), yaz() yalnız oner çıktısını sahte çalıştırıcıya birebir argümanla verir
    YZ = dict(ESKI, kayit_bayraklar=["--kuru"]); yb = B.yazan(YZ)
    def hata(kayit):
        try: yb.oner(kayit); return None
        except B.BaglayiciHata as ex: return ex.args[0]
    kotu = [hata({"alt": "sil", "argumanlar": ["x"]}), hata({"alt": "ekle", "argumanlar": ["--tehlikeli"]}), hata({"alt": "ekle", "argumanlar": ["a"] * 21}),
            hata({"alt": "ekle", "argumanlar": ["a" * 2001]}), hata({"alt": "ekle", "argumanlar": [1]}), hata({"alt": "ekle"}), hata({"alt": "ekle", "argumanlar": [], "fazla": 1})]
    iyi = yb.oner({"alt": "ekle", "argumanlar": ["Deneme işi", "--kuru"]})
    cagri = []
    def sahte(komut, arg): cagri.append((komut, arg)); return True, {"ok": True, "cikti": "tamam"}
    onaysiz = None
    try: yb.yaz({"komut": "proje_kayit", "alt": "ekle", "argumanlar": ["x"]}, sahte)
    except B.BaglayiciHata as ex: onaysiz = ex.args[0]
    dis = yb.yaz(iyi, sahte)
    h1 = h2 = None
    try: yb.yaz(iyi, lambda k, a: (False, "yardımcı yok"))
    except B.BaglayiciHata as ex: h1 = ex.args
    try: yb.yaz(iyi, lambda k, a: (True, {"ok": False, "hata": "x"}))
    except B.BaglayiciHata as ex: h2 = ex.args[0]
    ok("13. oner(): izinsiz alt komut/bayrak, 21 argüman, uzun/metin olmayan argüman, eksik/fazla alan reddedilir; yaz() sahteye birebir argümanla gider, onaysız öneriyi reddeder",
       kotu == ["alt_izinli_degil", "bayrak_izinli_degil", "arguman_liste", "arguman_liste", "arguman_liste", "arguman_uymuyor", "arguman_uymuyor"]
       and iyi["komut"] == "proje_kayit" and cagri == [("proje_kayit", {"alt": "ekle", "argumanlar": ["Deneme işi", "--kuru"]})] and onaysiz == "onaysiz_oneri" and dis is None
       and h1 == ("calistirilamadi", "yardımcı yok") and h2 == "betik_hata", (kotu, cagri, onaysiz, h1, h2))
    ok("13b. yazma ayarı: yeni şema = eski anahtarlar; yazma yoksa yazan() None ve oner() reddeder; durum_guncelle YetenekYok; sure_sn taşınır",
       B.yazan(YENI).yazma_ayari() == dict(B.yazan(ESKI).yazma_ayari()) and B.yazan(YZ).yazma_ayari()["bayrak"] == ["--kuru"] and B.yazan(YZ).yazma_ayari()["sure"] == 20
       and B.yazan(TEMEL) is None and B.yazan(dict(ESKI, kayit_alt_komutlar=["kötü komut"])) is None and B.yazan(dict(ESKI, kayit_komutu=["python3"])) is None
       and B.yazan(dict(YENI, baglayici={"kayit": dict(YENI["baglayici"]["kayit"], acik=False)})) is None)
    try: yb.durum_guncelle("1", "yapildi"); dg = False
    except B.YetenekYok: dg = True
    ok("13c. durum_guncelle A1'de YetenekYok; yazma ayarı ve okuma yolu birbirinden bağımsız (yol olmadan yazan() çalışır)", dg and B.yukle(dict(TEMEL, kayit_komutu=["/usr/bin/python3", "b.py"], kayit_alt_komutlar=["ekle"])) == []
       and B.yazan(dict(TEMEL, kayit_komutu=["/usr/bin/python3", "b.py"], kayit_alt_komutlar=["ekle"])) is not None)
    # 14. is_satiri ↔ yapi.belge_onerileri
    import yapi
    ham = kv.satirlar("gorevler"); d1, d2 = os.path.join(T, "bo1"), os.path.join(T, "bo2"); os.makedirs(d1); os.makedirs(d2)
    r_ham = yapi.belge_onerileri(d1, vt_isler=[list(r) for r in ham]); r_yeni = yapi.belge_onerileri(d2, vt_isler=[B.is_satiri(i) for i in kv.acik_isler()])
    tem = lambda r: [{k: v for k, v in o.items() if k != "id"} for o in r.get("oneriler", [])]
    ok("14. is_satiri() çıktısıyla belge_onerileri bugünkü sonucu verir", tem(r_ham) == tem(r_yeni) and len(tem(r_ham)) == 2, (tem(r_ham), tem(r_yeni)))
    # proje.db sözleşmesi (beta yolu): kisiler, terimler yok
    pk = e.kisiler()
    try: e.terimler(); pt = False
    except B.YetenekYok: pt = True
    ok("ProjeVT: kisiler() karttan, terimler() YetenekYok, satirlar('kisiler') eski sorguyla aynı", pk and pk[0]["ad"] == "Deneme Kisi" and pk[0]["takma"] == ["Deneme"]
       and pk[0]["kaynak"] == "proje" and pt and e.satirlar("kisiler")[0][1] == "Deneme Kisi — Satış · Örnek AŞ (kaynak: a.xlsx)", pk)
    # eski VT görünümü
    g = B.EskiGorunum(kv); g["yol"] = "yok.db"; gy = kv.yol; g["yol"] = "kayit.db"
    gb = B.EskiGorunum(B.bos(proje))
    ok("EskiGorunum: VT['yol'] yazılınca bağlayıcı değişir; bağlayıcı yoksa boş sözlük", gy == "yok.db" and g.get("kisiler") == Q["kisiler"] and g.get("proje_vt") is None
       and B.EskiGorunum(e).get("proje_vt") is True and gb.get("yol") is None and dict(gb) == {})
finally:
    shutil.rmtree(T, ignore_errors=True)
k = sonuc.count(False)
print("bağlayıcı: " + ("✓ hepsi geçti" if not k else f"✗ {k} kaldı") + f" ({len(sonuc) - k}/{len(sonuc)})")
sys.exit(1 if k else 0)
