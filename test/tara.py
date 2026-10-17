#!/usr/bin/env python3
# Proje hazırlığı T1 — tarama (`baglam.py tara`): yapay klasörde birebir kopya, sürüm grubu (ad kökü + içerik benzerliği), tarihli adların
# yanlış gruplanmaması, kilit dosyası, adla hariç tutma, parolalı/bozuk dosya, kaynak türü kuralları, dizindeki dosya alanları, SHA önbelleği,
# okunamayan klasörde kayıt korunması.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tara.py      (kaldı → çıkış 1)
import importlib.util, json, os, shutil, sys, tempfile, time, zipfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-tara-"); P = os.path.join(T, "proje")
def yaz(k, metin="", ikili=None, gun=0):
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True)
    with open(y, "wb") as f: f.write(ikili if ikili is not None else metin.encode("utf-8"))
    t = time.time() - 86400 * 30 + gun * 86400; os.utime(y, (t, t)); return y
def docx(metin):
    import io
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>"); z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:r><w:t>{metin}</w:t></w:r></w:p></w:body></w:document>")
    return b.getvalue()
def xlsx(satirlar):  # en küçük geçerli xlsx (satır içi metin hücreleri)
    import io
    b = io.BytesIO(); hucre = lambda v: f'<c t="inlineStr"><is><t>{v}</t></is></c>'
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook><sheets><sheet name="Liste" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData>" + "".join(f'<row r="{i}">' + "".join(hucre(v) for v in sat) + "</row>" for i, sat in enumerate(satirlar, 1)) + "</sheetData></worksheet>")
    return b.getvalue()
uzun = lambda tohum, n=120: " ".join(f"{tohum}{i % 17} sözcük{i} bütçe yedekleme planı madde{i}" for i in range(n))
TEKLIF = uzun("teklif")
# birebir kopya
yaz("belgeler/rapor.docx", ikili=docx("Yıllık rapor metni " * 40), gun=1)
yaz("belgeler/rapor (1).docx", ikili=docx("Yıllık rapor metni " * 40), gun=5)
yaz("eski/rapor.docx", ikili=docx("Yıllık rapor metni " * 40), gun=6)
# sürüm grubu: benzer içerik, üç ad biçimi; en yenisi geçerli
yaz("belgeler/teklif-v1.md", TEKLIF, gun=1); yaz("belgeler/teklif-v2.md", TEKLIF + " ek madde fiyat", gun=2); yaz("belgeler/Teklif_final.md", TEKLIF + " ek madde fiyat son hali", gun=3)
# aynı kök, ilgisiz içerik → grup yok
yaz("belgeler/plan-v1.md", uzun("altyapı"), gun=1); yaz("belgeler/plan-v2.md", uzun("pazarlama kampanya", 90), gun=2)
# yalnız tarihle adlandırılmış ve tarihli seri → grup yok (içerik benzer olsa da)
yaz("notlar/20261016-1200.txt", uzun("gunluk"), gun=1); yaz("notlar/20261017-1200.txt", uzun("gunluk") + " küçük fark", gun=2)
yaz("notlar/toplanti-2026-10-16.md", uzun("pazartesi gündem"), gun=1); yaz("notlar/toplanti-2026-10-17.md", uzun("salı satış"), gun=2)
# içeriği henüz okunamayan (PDF, T2'ye kadar): sürüm işaretli ad gruplanır, tarihli ad gruplanmaz
yaz("sunum/sunum-v1.pdf", ikili=b"%PDF-1.4 bir", gun=1); yaz("sunum/sunum-v2.pdf", ikili=b"%PDF-1.4 iki", gun=2)
yaz("sunum/brosur-2026-10-16.pdf", ikili=b"%PDF-1.4 uc", gun=1); yaz("sunum/brosur-2026-10-17.pdf", ikili=b"%PDF-1.4 dort", gun=2)
# tarihli adlı Excel: içerik benzerse sürüm (geçerli en yenisi), farklıysa değil
LISTE = [["Ad", "Birim", "Görev"]] + [[f"Kişi{i}", f"Birim{i % 5}", f"görev tanımı {i} rapor hazırlama"] for i in range(60)]
yaz("liste/alici-listesi-20261009.xlsx", ikili=xlsx(LISTE), gun=1); yaz("liste/alici-listesi-20261010.xlsx", ikili=xlsx(LISTE + [["Yeni", "Birim9", "ek görev"]]), gun=2)
yaz("liste/satis-20261009.xlsx", ikili=xlsx([["Ürün", "Adet"]] + [[f"Ürün{i}", str(i)] for i in range(40)]), gun=1)
yaz("liste/satis-20261010.xlsx", ikili=xlsx([["Şehir", "Ciro"]] + [[f"Şehir{i}", str(i * 7)] for i in range(40)]), gun=2)
# kilit dosyası, sistem dosyası, hariç klasör
yaz("belgeler/~$rapor.docx", ikili=b"kilit"); yaz("belgeler/.DS_Store", ikili=b"\0"); yaz("_yedek/eski.md", "yedek")
# adla hariç tutma
for k in (".env", "anahtarlar/sunucu.pem", "anahtarlar/imza.key", "belgeler/parolalar.xlsx", "ik/Maaş-tablosu.csv", "ik/salary-2026.xlsx", "tarama/kimlik-on.jpg",
          "tarama/Pasaport.pdf", "belgeler/sifre-listesi.txt"):
    yaz(k, ikili=(b"%PDF-1.4 " if k.endswith(".pdf") else b"") + k.encode())
yaz("belgeler/sifreleme-politikasi.md", "Şifreleme politikası belgesi"); yaz("belgeler/kimlik-dogrulama-sureci.md", "Kimlik doğrulama süreci")
# parolalı ve bozuk
yaz("belgeler/sozlesme.docx", ikili=b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 600)
yaz("belgeler/korumali.pdf", ikili=b"%PDF-1.7\n1 0 obj <<>> endobj\ntrailer << /Root 1 0 R /Encrypt 5 0 R >>\n%%EOF")
yaz("belgeler/bozuk.xlsx", ikili=b"bu bir excel degil")
yaz("belgeler/bos.md", ""); yaz("veri/bos.db", "")  # boş dosyalar birbirinin kopyası sayılmaz
# kaynak türü
yaz("veri/disa/kisi.csv", "ad,rol\nDeniz,yonetici\n"); yaz("Export/sistemler.json", '{"a": 1}'); yaz("veri/durum-20261016-1200.csv", "a,b\n1,2\n")
yaz("veri/gorunum.xlsx", ikili=docx("tablo")); yaz("tablolar/butce.xlsx", ikili=docx("bütçe")); yaz("tablolar/butce.md", "| bütçe |")
yaz("belgeler/proje-ozeti.md", "Proje özeti"); yaz("analiz/bulgular.md", "bulgular")
yaz("belgeler/sartname.docx", ikili=docx("Şartname metni")); yaz("belgeler/sartname.pdf", ikili=b"%PDF-1.4 sartname")
# T3: arama önceliği ve harf katlaması
KARS = "Lojistik karşılaştırma: Bursa ve Sakarya depolarında yükleme süresi ölçüldü, Sakarya daha hızlı çıktı."
yaz("belgeler/karsilastirma.md", KARS + " Ayrıntı ekte.", gun=2); yaz("belgeler/karsilastirma-ozeti.md", KARS, gun=2)
yaz("belgeler/sube.md", "IZMIR ŞUBESİ açılışı ve ILGAZ deposu (OCR çıktısı gibi büyük harf)", gun=2)
yaz("veri/disa/stok-durumu.csv", "urun,adet\nPalet kaldırıcı,14\n")
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "uygulama": os.path.join(T, "uyg"), "proje": P, "ortak": os.path.join(T, "yok"), "analiz_klasorleri": ["analiz/"],
           "veritabani": {"yol": "yok.db", "disa_aktarim": ["veri/gorunum.xlsx"]}}, open(ay, "w"))
os.environ["SUFLOR_AYAR"] = ay; sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("baglam_tara", os.path.join(KOD, "baglam.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
c = m.baglan()
try:
    m.guncelle(c); r = m.tara(c); s = r["sayilar"]
    d = {x["yol"]: x for x in r["dosyalar"]}
    kontrol("rapor dosyası yazıldı (0600)", os.path.exists(m.TARA_RAPOR) and (os.stat(m.TARA_RAPOR).st_mode & 0o777) == 0o600)
    kontrol("her dosyada yol/tür/boyut/zaman/SHA-256", all(len(x["sha256"] or "") == 64 and x["boy"] >= 0 and x["mtime"] and x["tur"] for x in d.values()))
    kontrol("kilit (~$), sistem dosyası ve _yedek taramada yok", not any("~$" in k or ".DS_Store" in k or k.startswith("_yedek") for k in d)
            and s["atlanan"].get("kilit dosyası") == 1 and s["atlanan"].get("sistem dosyası") == 1, json.dumps(s["atlanan"]))
    kontrol("birebir kopya: rapor.docx asıl, '(1)' ve eski/ kopyası kopya", d["belgeler/rapor (1).docx"]["kopya_of"] == "belgeler/rapor.docx"
            and d["eski/rapor.docx"]["kopya_of"] == "belgeler/rapor.docx" and d["belgeler/rapor.docx"]["kopya_of"] is None and s["kopya"] == 2, json.dumps(r["kopyalar"]))
    g = {x["ad"]: x for x in r["surum_gruplari"]}
    tg = [x for x in r["surum_gruplari"] if x["gecerli"] == "belgeler/Teklif_final.md"]
    kontrol("sürüm grubu: teklif v1/v2/final tek grup, geçerli en yenisi", len(tg) == 1 and sorted(tg[0]["eski"]) == ["belgeler/teklif-v1.md", "belgeler/teklif-v2.md"]
            and d["belgeler/teklif-v1.md"]["gecerli"] == 0 and d["belgeler/Teklif_final.md"]["gecerli"] == 1, json.dumps(r["surum_gruplari"]))
    kontrol("aynı kök, ilgisiz içerik (plan-v1/v2): grup yok", d["belgeler/plan-v1.md"]["surum_grubu"] is None and d["belgeler/plan-v2.md"]["surum_grubu"] is None)
    tarihli = ["notlar/20261016-1200.txt", "notlar/20261017-1200.txt", "notlar/toplanti-2026-10-16.md", "notlar/toplanti-2026-10-17.md",
               "sunum/brosur-2026-10-16.pdf", "sunum/brosur-2026-10-17.pdf"]
    kontrol("tarihli adlarda yanlış gruplama 0", all(d[k]["surum_grubu"] is None and d[k]["gecerli"] == 1 for k in tarihli),
            ", ".join(k for k in tarihli if d[k]["surum_grubu"]))
    kontrol("içeriği okunamayan sürüm işaretli PDF'ler gruplandı", d["sunum/sunum-v1.pdf"]["surum_grubu"] and d["sunum/sunum-v1.pdf"]["gecerli"] == 0 and d["sunum/sunum-v2.pdf"]["gecerli"] == 1)
    kontrol("tarihli adlı Excel: benzer içerik sürüm grubu (geçerli en yenisi), farklı içerik grup değil",
            d["liste/alici-listesi-20261009.xlsx"]["gecerli"] == 0 and d["liste/alici-listesi-20261010.xlsx"]["gecerli"] == 1
            and d["liste/satis-20261009.xlsx"]["surum_grubu"] is None and d["liste/satis-20261010.xlsx"]["surum_grubu"] is None)
    kontrol("toplam: 3 sürüm grubu, 4 eski sürüm", s["surum_grubu"] == 3 and s["eski_surum"] == 4, f"{s['surum_grubu']}/{s['eski_surum']}")
    gizli = {x["yol"] for x in r["haric"]}
    beklenen = {".env", "anahtarlar/sunucu.pem", "anahtarlar/imza.key", "belgeler/parolalar.xlsx", "ik/Maaş-tablosu.csv", "ik/salary-2026.xlsx",
                "tarama/kimlik-on.jpg", "tarama/Pasaport.pdf", "belgeler/sifre-listesi.txt"}
    kontrol("adla hariç tutma: anahtar, parola, maaş, kimlik taraması", gizli == beklenen, f"fazla {sorted(gizli - beklenen)} eksik {sorted(beklenen - gizli)}")
    kontrol("'şifreleme' ve 'kimlik doğrulama' belgesi hariç değil", d["belgeler/sifreleme-politikasi.md"]["gizli"] == 0 and d["belgeler/kimlik-dogrulama-sureci.md"]["gizli"] == 0)
    ok = {x["yol"]: x["hata"] for x in r["okunamayan"]}
    kontrol("parolalı docx/pdf, bozuk xlsx ve boş dosya işaretlendi; boşlar kopya değil", ok.get("belgeler/sozlesme.docx") == "parolali" and ok.get("belgeler/korumali.pdf") == "parolali"
            and ok.get("belgeler/bozuk.xlsx") == "bozuk" and "belgeler/rapor.docx" not in ok and ok.get("belgeler/bos.md") == "bos"
            and d["veri/bos.db"]["kopya_of"] is None, json.dumps(ok))
    kt = {k: x["kaynak_turu"] for k, x in d.items()}
    kontrol("dışa aktarım: disa/ ve Export/ klasörü, tarih-saat damgalı csv, ayardaki yol",
            [kt[k] for k in ("veri/disa/kisi.csv", "Export/sistemler.json", "veri/durum-20261016-1200.csv", "veri/gorunum.xlsx")] == ["disa_aktarim"] * 4)
    kontrol("türetilmiş: aynı adlı xlsx'in md'si, docx'in pdf'i, 'özeti' adı, analiz klasörü",
            [kt[k] for k in ("tablolar/butce.md", "belgeler/sartname.pdf", "belgeler/proje-ozeti.md", "analiz/bulgular.md")] == ["turetilmis"] * 4)
    kontrol("asıl: özgün belgeler ve tarihli döküm/not", [kt[k] for k in ("tablolar/butce.xlsx", "belgeler/sartname.docx", "belgeler/teklif-v1.md", "notlar/toplanti-2026-10-16.md")] == ["asil"] * 4)
    sat = dict(c.execute("SELECT yol, gecerli FROM dosya WHERE yol LIKE 'belgeler/teklif%' OR yol LIKE 'belgeler/Teklif%'").fetchall())
    sha = c.execute("SELECT sha256, kaynak_turu FROM dosya WHERE yol='tablolar/butce.md'").fetchone()
    kontrol("dizindeki dosya satırına alanlar yazıldı", sat == {"belgeler/teklif-v1.md": 0, "belgeler/teklif-v2.md": 0, "belgeler/Teklif_final.md": 1}
            and sha and len(sha[0] or "") == 64 and sha[1] == "turetilmis", f"{sat} {sha}")
    kontrol("birebir kopya ve adla hariç dizinde değil, asıl dizinde", not c.execute("SELECT 1 FROM dosya WHERE yol IN ('belgeler/rapor (1).docx', 'eski/rapor.docx', 'belgeler/sifre-listesi.txt', 'ik/Maaş-tablosu.csv')").fetchone()
            and c.execute("SELECT 1 FROM dosya WHERE yol='belgeler/rapor.docx'").fetchone())
    os.remove(os.path.join(P, "belgeler/rapor.docx")); m.tara(c); m.guncelle(c)
    kontrol("asıl silinince kopyası dizine girdi", c.execute("SELECT count(*) FROM dosya WHERE yol IN ('belgeler/rapor (1).docx', 'eski/rapor.docx')").fetchone()[0] == 1)
    yollar = lambda q, **k: [x[1] for x in m.ara(q, n=10, guncel=False, **k)[0]]
    kontrol("T3: eski sürümler sonuçta yok, yalnız geçerli", yollar("teklif bütçe yedekleme") == ["belgeler/Teklif_final.md"] * len(yollar("teklif bütçe yedekleme")) and yollar("teklif bütçe yedekleme"),
            str(yollar("teklif bütçe yedekleme")))
    kontrol("T3: eski=True ile eski sürümler de", {"belgeler/teklif-v1.md", "belgeler/teklif-v2.md"} <= set(yollar("teklif bütçe yedekleme", eski=True)))
    kontrol("T3: veritabanı kipinde dışa aktarım sonuçta yok, disa=True ile var", not yollar("palet kaldırıcı") and yollar("palet kaldırıcı", disa=True) == ["veri/disa/stok-durumu.csv"],
            f"{yollar('palet kaldırıcı')} {yollar('palet kaldırıcı', disa=True)}")
    kontrol("T3: aynı metinde asıl kaynak türetilmişin önünde", yollar("Sakarya yükleme süresi")[:2] == ["belgeler/karsilastirma.md", "belgeler/karsilastirma-ozeti.md"], str(yollar("Sakarya yükleme süresi")))
    kontrol("T3: I/İ/ı katlaması (büyük harfli OCR metni)", all(yollar(q) == ["belgeler/sube.md"] for q in ("İzmir şubesi", "izmir", "Ilgaz", "ılgaz deposu")),
            str([yollar(q) for q in ("İzmir şubesi", "izmir", "Ilgaz", "ılgaz deposu")]))
    m.VT_KIPI = False
    kontrol("T3: veritabanı kipi dışında dışa aktarım sonuçta (geride)", yollar("palet kaldırıcı") == ["veri/disa/stok-durumu.csv"])
    m.VT_KIPI = True
    yaz("belgeler/teklif-v1.md", TEKLIF + " değişti", gun=4); m.guncelle(c)
    kontrol("dosya değişip yeniden dizinlenince eski tarama alanı boş", c.execute("SELECT sha256 FROM dosya WHERE yol='belgeler/teklif-v1.md'").fetchone()[0] is None
            and c.execute("SELECT sha256 FROM dosya WHERE yol='belgeler/teklif-v2.md'").fetchone()[0] is not None)
    say = [0]; asil = m._sha256
    def sayan(y): say[0] += 1; return asil(y)
    m._sha256 = sayan; r2 = m.tara(c); m._sha256 = asil
    kontrol("SHA önbelleği: yalnız değişen dosya yeniden okundu", say[0] == 1, f"{say[0]} okuma")
    kontrol("değişen dosya yeni sürümde: grubun geçerlisi oldu", c.execute("SELECT gecerli, sha256 IS NOT NULL FROM dosya WHERE yol='belgeler/teklif-v1.md'").fetchone() == (1, 1))
    os.chmod(os.path.join(P, "notlar"), 0)
    try: r3 = m.tara(c)
    finally: os.chmod(os.path.join(P, "notlar"), 0o755)
    kalan = {x[0] for x in c.execute("SELECT yol FROM tarama WHERE yol LIKE 'notlar/%'")}
    kontrol("okunamayan klasörün tarama kayıtları korundu ve bildirildi", len(kalan) == 4 and r3["sayilar"]["erisilemeyen"] == ["notlar"], f"{kalan} {r3['sayilar']['erisilemeyen']}")
    os.remove(os.path.join(P, "belgeler/plan-v2.md")); m.tara(c)
    kontrol("silinen dosya taramadan düştü", not c.execute("SELECT 1 FROM tarama WHERE yol='belgeler/plan-v2.md'").fetchone())
    print(m.tara_ozet(r))
finally:
    try: os.chmod(os.path.join(P, "notlar"), 0o755)
    except OSError: pass
    c.close(); shutil.rmtree(T, ignore_errors=True)
print(f"tarama: {len(hatalar)} sorun" if hatalar else "tarama: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
