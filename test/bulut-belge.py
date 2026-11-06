#!/usr/bin/env python3
# Buluttaki proje klasörü ve Google belgeleri (v0.200.0): sahte Google sunucusu (belirteç + files.export), sahte .gdoc/.gsheet/.gslides kısayolları,
# yalnız-bulut benzetimi (UF_NODUMP bayrağı SF_DATALESS yerine; "indirme" = bayrağı kaldırma, "boşaltma" = bayrağı koyma).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bulut-belge.py      (kaldı → çıkış 1)
import http.server, importlib.util, io, json, os, shutil, stat, subprocess, sys, tempfile, threading, time, zipfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-bulut-")
P = os.path.join(T, "Library", "Mobile Documents", "com~apple~CloudDocs", "proje")  # iCloud yolu: bulut_birak buna göre `brctl evict` der
os.makedirs(P)
def yaz(k, metin="", ikili=None):
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True)
    with open(y, "wb") as f: f.write(ikili if ikili is not None else metin.encode("utf-8"))
    t = time.time() - 86400 * 20; os.utime(y, (t, t)); return y
def docx(metin):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>"); z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:r><w:t>{metin}</w:t></w:r></w:p></w:body></w:document>")
    return b.getvalue()
def xlsx(sayfalar):  # {sayfa: satırlar}
    b = io.BytesIO(); hucre = lambda v: f'<c t="inlineStr"><is><t>{v}</t></is></c>'
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", "<workbook><sheets>" + "".join(f'<sheet name="{a}" sheetId="{i}" r:id="rId{i}"/>' for i, a in enumerate(sayfalar, 1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", "<Relationships>" + "".join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sayfalar) + 1)) + "</Relationships>")
        for i, sat in enumerate(sayfalar.values(), 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", "<worksheet><sheetData>" + "".join(f'<row r="{n}">' + "".join(hucre(v) for v in r) + "</row>" for n, r in enumerate(sat, 1)) + "</sheetData></worksheet>")
    return b.getvalue()
def kisayol(ad, kimlik, uzanti):  # Drive for desktop biçimi: içinde yalnız JSON
    yaz(f"{ad}.{uzanti}", json.dumps({"": "UYARI! BU DOSYAYI DÜZENLEMEYİN.", "doc_id": kimlik, "resource_key": "", "email": "ali" + "@" + "ornek.test"}))

# ---------- sahte Google ----------
ID = {"gdoc": "A" * 12 + "doc1", "gslides": "B" * 12 + "sld1", "gsheet": "C" * 12 + "sht1", "red": "D" * 12 + "red1"}
ICERIK = {"doc": "Tedarik sözleşmesi taslağı: teslim tarihi 15 Aralık, ödeme vadesi 45 gün.", "sld": "Yıllık plan sunumu\nHedef: yeni depo açılışı ve lojistik birleştirme",
          "sht": {"Satış": [["Ürün", "Adet"], ["Palet", "14"], ["Raf", "9"]], "Gider": [["Kalem", "Tutar"], ["Kira", "1200"]]}}
SUNUCU = {"istek": [], "token": 0, "gecerli_yenileme": "yenileme-" + "x" * 30}
class Google(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); f = self.rfile.read(n).decode(); SUNUCU["token"] += 1
        if "refresh_token=" + SUNUCU["gecerli_yenileme"] not in f: self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"invalid_grant"}'); return
        b = json.dumps({"access_token": "erisim-belirteci", "expires_in": 3600}).encode(); self.send_response(200); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path); kimlik = u.path.split("/")[4]; mime = parse_qs(u.query)["mimeType"][0]; SUNUCU["istek"].append(kimlik)
        if self.headers.get("Authorization") != "Bearer erisim-belirteci": self.send_response(401); self.end_headers(); return
        if kimlik == ID["red"]: self.send_response(404); self.end_headers(); return
        if kimlik == ID["gdoc"]: g, tur = ICERIK["doc"].encode("utf-8-sig"), "text/plain"
        elif kimlik == ID["gslides"]: g, tur = ICERIK["sld"].encode(), "text/plain"
        elif kimlik == ID["gsheet"]: g, tur = xlsx(ICERIK["sht"]), "application/octet-stream"
        else: self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", tur); self.end_headers(); self.wfile.write(g)
sv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Google); threading.Thread(target=sv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{sv.server_address[1]}"

# ---------- proje ----------
kisayol("Sözleşme", ID["gdoc"], "gdoc"); kisayol("Plan", ID["gslides"], "gslides"); kisayol("Satış", ID["gsheet"], "gsheet"); kisayol("Kapalı", ID["red"], "gdoc")
yaz("notlar/yerel.md", "Yerel not: depo kapasitesi toplantısı.")
BULUT_MD = "Bulut notu: Sakarya deposu sevkiyat takvimi kesinleşti."
yaz("bulut/not.md", BULUT_MD); yaz("bulut/rapor.docx", ikili=docx("Bulut raporu bütçe revizyonu madde")); yaz("bulut/tablo.xlsx", ikili=xlsx({"Liste": [["Kişi", "Birim"], ["Ali", "Lojistik"], ["Ece", "Satın alma"]]}))
yaz("bulut/film.mp4", ikili=b"\0" * 5000); yaz("bulut/sifre-listesi.txt", "gizli"); yaz("bulut/buyuk.md", "Büyük bulut dosyası. " * 5000)
ay = os.path.join(T, "ayar.json")
AYARLAR = {"alan": "Deneme", "uygulama": os.path.join(T, "uyg"), "proje": P, "ortak": os.path.join(T, "yok"), "google_istemci_id": "istemci-kimligi"}
json.dump(AYARLAR, open(ay, "w"))
os.environ.update(SUFLOR_AYAR=ay, SUFLOR_GOOGLE_API=URL, SUFLOR_GOOGLE_TOKEN_URL=URL + "/token"); os.environ.pop("SUFLOR_GOOGLE_YENILEME", None); os.environ.pop("SUFLOR_GOOGLE_BELIRTEC", None)
sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("baglam_bulut", os.path.join(KOD, "baglam.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
m._zincir_oku = lambda oge: ""  # gerçek Anahtar Zinciri'ne dokunma
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
def ara_var(c, sorgu, yol): return any(r[1] == yol for r in m.ara(sorgu, n=20, guncel=False)[0])
def pvt(sorgu):
    v = m._pvt_baglan()
    try: return v.execute(sorgu).fetchall()
    finally: v.close()
BAYRAK = stat.UF_NODUMP; BULUT_YOL = {os.path.join(P, k) for k in ("bulut/not.md", "bulut/rapor.docx", "bulut/tablo.xlsx", "bulut/film.mp4", "bulut/sifre-listesi.txt", "bulut/buyuk.md")}
def bulutla(yollar):
    for y in yollar: os.chflags(y, BAYRAK)
m.SF_DATALESS = BAYRAK  # gerçek SF_DATALESS yalnız dosya sağlayıcısında: UF_NODUMP bulut yer tutucusu yerine
CAT, EVICT = [], []
gercek_run = subprocess.run
def sahte_run(a, *x, **k):
    if a and a[0] == "/bin/cat": CAT.append(a[1]); os.chflags(a[1], 0); return subprocess.CompletedProcess(a, 0)  # okumak indirir
    if a and a[0] == "/usr/bin/brctl": EVICT.append(a[2]); os.chflags(a[2], BAYRAK); return subprocess.CompletedProcess(a, 0)  # evict: yeniden yalnız bulutta
    return gercek_run(a, *x, **k)
c = m.baglan()
try:
    # 1) kimlik yok: Google belgeleri sessizce adıyla sayılır, hata yok, önbellek yazılmaz
    r = m.cevir(c); s = m.tara(c)["sayilar"]
    kontrol("kimlik yok: Google ağına istek gitmedi, çökmedi", not SUNUCU["istek"] and not m.google_hazir() and r["hata"] == 0, str(SUNUCU["istek"]))
    kontrol("kimlik yok: dört kısayol dizinde yalnız adıyla (parçasız), uzantısız ad", c.execute("SELECT count(*) FROM dosya WHERE parca=0 AND yol LIKE '%.g%'").fetchone() == (4,)
            and c.execute("SELECT baslik FROM dosya WHERE yol='Sözleşme.gdoc'").fetchone() == ("Sözleşme",))
    kontrol("kimlik yok: sayaç — 4 belge, 0 okundu, 4 kimlik yok", s["google_belge"] == 4 and s["google_okundu"] == 0 and s["google_kimlik_yok"] == 4, json.dumps(s))
    kontrol("kimlik yok: kalan işe sayılmaz (sihirbaz takılmaz)", r["kalan"] == 0, str(r["kalan"]))
    kontrol("kimlik yok: tür belge/tablo/sunum", [m.tur_bul(k) for k in ("a.gdoc", "a.gsheet", "a.gslides")] == ["belge", "tablo", "belge"] or m.tur_bul("a.gsheet") == "tablo")

    # 2) kimlik var: metinler önbelleğe ve dizine, E-Tablo sayfaları proje veritabanına
    os.environ["SUFLOR_GOOGLE_YENILEME"] = SUNUCU["gecerli_yenileme"]; m._G.update(belirtec=None, bitis=0, yenileme=False)
    r = m.cevir(c); s = m.tara(c)["sayilar"]
    kontrol("kimlik var: 3 belge okundu, reddedilen 1 erişim yok", r["google"].get("okundu") == 3 and r["google"].get("erisim_yok") == 1, json.dumps(r["google"]))
    kontrol("Doküman düz metin olarak aranır (BOM temiz)", ara_var(c, "ödeme vadesi", "Sözleşme.gdoc") and not c.execute("SELECT 1 FROM parca WHERE metin LIKE '%﻿%'").fetchone())
    kontrol("Slayt metni aranır", ara_var(c, "lojistik birleştirme", "Plan.gslides"))
    kontrol("E-Tablo satırları aranır (Satış!2)", ara_var(c, "Palet", "Satış.gsheet"))
    t = dict(pvt("SELECT tablo, satir_sayisi FROM tablolar"))
    kontrol("E-Tablo her sayfa için t_… tablosu (proje.db)", t.get("t_satis_satis") == 2 and t.get("t_satis_gider") == 1, str(t))
    kontrol("tablodan toplam hesaplanır", pvt("SELECT sum(adet) FROM t_satis_satis") == [(23,)], str(pvt("SELECT * FROM t_satis_satis")))
    kontrol("reddedilen belge adıyla duruyor (parçasız), önbellek yok", c.execute("SELECT parca FROM dosya WHERE yol='Kapalı.gdoc'").fetchone() == (0,)
            and s["google_okundu"] == 3 and s["google_erisim_yok"] == 1, json.dumps(s))
    kontrol("önbellek 0600, kısayol dosyası değişmedi", all((os.stat(os.path.join(dp, f)).st_mode & 0o777) == 0o600 for dp, _, fs in os.walk(m.ONBELLEK) for f in fs))
    kontrol("tür adı: .gsheet tablo", c.execute("SELECT tur FROM dosya WHERE yol='Satış.gsheet'").fetchone() == ("tablo",))
    n_ist = len(SUNUCU["istek"])
    r = m.cevir(c); r2 = SUNUCU["istek"][n_ist:]
    kontrol("hemen ardından yeniden çekilmez (12 sa, reddedilen 6 sa beklenir)", not r2, str(r2))

    # 3) içerik değişince dizin ve tablo güncellenir
    ICERIK["doc"] = "Tedarik sözleşmesi revize: teslim tarihi 2 Ocak, depozito yüzde yirmi."; ICERIK["sht"]["Satış"].append(["Sepet", "7"])
    m.AYAR["google_yenile_sa"] = 0.00001; time.sleep(0.2)
    r = m.cevir(c); m.guncelle(c); m.proje_vt_guncelle(c)
    kontrol("değişen Doküman yeniden dizinde (eski metin gitti)", ara_var(c, "depozito yüzde", "Sözleşme.gdoc") and not ara_var(c, "ödeme vadesi", "Sözleşme.gdoc"), json.dumps(r["google"]))
    kontrol("değişen E-Tablo yeni satırıyla proje.db'de", pvt("SELECT sum(adet) FROM t_satis_satis") == [(30,)], str(pvt("SELECT * FROM t_satis_satis")))
    m.AYAR.pop("google_yenile_sa")

    # 4) kimlik geçersiz (yenileme belirteci reddedildi) → sessiz, mevcut önbellek ve dizin bozulmaz
    SUNUCU["gecerli_yenileme"] = "baska-" + "y" * 30; m._G.update(belirtec=None, bitis=0); m.AYAR["google_yenile_sa"] = 0.00001; time.sleep(0.2)
    r = m.cevir(c); m.AYAR.pop("google_yenile_sa")
    kontrol("geçersiz kimlik: çökmeden adıyla/önceki içerikle sürer", r["google"].get("kimlik_yok", 0) >= 1 and ara_var(c, "depozito yüzde", "Sözleşme.gdoc"), json.dumps(r["google"]))
    kontrol("geçersiz kimlik: tek günlük satırı için sayaç yazıldı", json.load(open(m.GOOGLE_DURUM))["kimlik_yok"] >= 1)
    SUNUCU["gecerli_yenileme"] = os.environ["SUFLOR_GOOGLE_YENILEME"]
    ham = open(m.GOOGLE_DURUM).read()
    kontrol("durum dosyasında belirteç/kimlik yok", "erisim-belirteci" not in ham and SUNUCU["gecerli_yenileme"] not in ham and "ornek.test" not in ham)

    # 5) yer tutucu (bayraklı) Google kısayolu yine okunur; normal bulut dosyası okunmaz
    bt = {os.path.join(P, "Plan.gslides")}
    st = os.stat(os.path.join(P, "Plan.gslides")); os.chflags(os.path.join(P, "Plan.gslides"), BAYRAK); st = os.stat(os.path.join(P, "Plan.gslides"))
    kontrol("bayraklı .gslides 'bulutta' sayılmaz, bayraklı .pdf sayılır", not m.bulutta_dosya(st, ".gslides") and m.bulutta_dosya(st, ".pdf")); os.chflags(os.path.join(P, "Plan.gslides"), 0)

    # 6) normal bulut dosyaları: ayar kapalıyken adıyla (eski davranış aynen)
    bulutla(BULUT_YOL); subprocess.run = sahte_run
    m.guncelle(c, yeniden=True); r = m.cevir(c); s = m.tara(c)["sayilar"]  # yeniden: dosyalar bayraklıyken dizinlensin
    kontrol("ayar kapalı: hiçbir bulut dosyası indirilmedi", not CAT and s["bulutta"] == 6 and s["bulut_indirilen"] == 0, f"{CAT} {s}")
    kontrol("ayar kapalı: dizine girecek 4 dosya yalnız adıyla (parçasız)", c.execute("SELECT count(*) FROM dosya WHERE yol LIKE 'bulut/%' AND parca=0").fetchone() == (4,), str(c.execute("SELECT yol, parca FROM dosya WHERE yol LIKE 'bulut/%'").fetchall()))
    # 7) ayar açık ama eşik aşıldı: onay gelene kadar indirme yok, onay bekliyor
    m.AYAR.update(bulut_indir=True, bulut_indir_mb=0.05)
    o = m.bulut_ozet(c)
    kontrol("eşik: 4 aday (film/gizli ad hariç), toplam boyut eşiğin üstünde → onay gerek", o["n"] == 4 and o["onay_gerek"] and o["mb"] > 0.05, json.dumps(o))
    r = m.cevir(c); s = m.tara(c)["sayilar"]
    kontrol("eşik aşıldı: indirme yok, onay bekliyor sayacı 1", not CAT and s["bulut_onay_bekliyor"] == 1 and json.load(open(m.BULUT_DURUM))["onay_bekliyor"] is True, f"{CAT} {s}")
    # 8) onay verildi: indirilir, metni çıkar, iCloud'daki yeniden buluta bırakılır
    m.AYAR["bulut_indir_onay_mb"] = 10
    r = m.cevir(c); s = m.tara(c)["sayilar"]
    ad = {os.path.basename(y) for y in CAT}
    kontrol("onaydan sonra yalnız dizine girecek türler indirildi (md, docx, xlsx, büyük md)", ad == {"not.md", "rapor.docx", "tablo.xlsx", "buyuk.md"}, str(ad))
    kontrol("film.mp4 ve şifre adlı dosya hiç indirilmedi", not any(x in " ".join(CAT) for x in ("film.mp4", "sifre-listesi")))
    kontrol("indirilenlerin metni dizinde (aranır)", ara_var(c, "Sakarya deposu sevkiyat", "bulut/not.md") and ara_var(c, "bütçe revizyonu", "bulut/rapor.docx") and ara_var(c, "Lojistik", "bulut/tablo.xlsx"))
    kontrol("xlsx tablosu proje.db'ye girdi (boşaltılmadan önce okundu)", any(t.startswith("t_tablo") for t in dict(pvt("SELECT tablo, satir_sayisi FROM tablolar"))), str(pvt("SELECT tablo FROM tablolar")))
    kontrol("metni çıkan dosyalar yeniden yalnız buluta bırakıldı (brctl evict)", {os.path.basename(y) for y in EVICT} == ad and all(m.bulutta(os.stat(y)) for y in EVICT), str(EVICT))
    kontrol("taramada indirilen sayısı 4, adla sayılan değil", s["bulut_indirilen"] == 4 and c.execute("SELECT count(*) FROM tarama WHERE yol LIKE 'bulut/%' AND hata='bulutta'").fetchone() == (2,), json.dumps(s))
    kontrol("boşaltılmış dosya gerçek özetle kayıtlı, içerik dizinde duruyor", c.execute("SELECT sha256 NOT LIKE 'bulut:%', hata IS NULL FROM tarama WHERE yol='bulut/not.md'").fetchone() == (1, 1)
            and c.execute("SELECT parca > 0 FROM dosya WHERE yol='bulut/not.md'").fetchone() == (1,))
    # 9) sonraki turlarda yeniden indirilmez
    n_cat, n_ev = len(CAT), len(EVICT); r = m.cevir(c); m.guncelle(c); m.tara(c)
    kontrol("ikinci tur: yeniden indirme/boşaltma döngüsü yok", len(CAT) == n_cat and len(EVICT) == n_ev and ara_var(c, "Sakarya deposu sevkiyat", "bulut/not.md"), f"{len(CAT) - n_cat} indirme")
    # 10) dosya bulutta değişirse yeniden: kayıt eskidi
    yaz("bulut/not.md", BULUT_MD + " Ek: Mersin rotası."); os.chflags(os.path.join(P, "bulut/not.md"), BAYRAK)
    r = m.cevir(c)
    kontrol("bulutta değişen dosya yeniden indirilip okundu", len(CAT) == n_cat + 1 and ara_var(c, "Mersin rotası", "bulut/not.md"), str(len(CAT) - n_cat))
    # 11) Drive for desktop yolu: boşaltma komutu yok → dosya açık kalır, sayılır
    eski_p = m.PROJE; m.PROJE = os.path.join(T, "CloudStorage", "GoogleDrive-x", "proje"); os.makedirs(m.PROJE)
    shutil.copy(os.path.join(P, "bulut/rapor.docx"), os.path.join(m.PROJE, "r.docx")); n_ev = len(EVICT)
    kay = m._json_oku(m.BULUT_KAYIT, {}); kay["kayit"]["r.docx"] = {"mtime": 1, "boy": 1, "sha": "a" * 64, "evict": True}; m._json_yaz(m.BULUT_KAYIT, kay)
    b, a = m.bulut_birak(); m.PROJE = eski_p
    kontrol("Drive yolunda brctl çağrılmaz, açık kalan sayılır", len(EVICT) == n_ev and a >= 1, f"{b},{a}")
    m.AYAR.pop("bulut_indir")
    kontrol("tara özeti Google ve bulut satırını yazar", "Google belgesi: 4" in m.tara_ozet(m.tara(c)))
finally:
    subprocess.run = gercek_run
    c.close(); sv.shutdown(); shutil.rmtree(T, ignore_errors=True)
print(f"bulut-belge: {len(hatalar)} sorun" if hatalar else "bulut-belge: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
