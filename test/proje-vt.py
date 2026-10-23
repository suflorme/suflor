#!/usr/bin/env python3
# v0.121.0 — proje veritabanı (baglam.py proje_vt_guncelle, <uygulama>/proje.db) ve yeni belge biçimleri, yalıtılmış klasörde (gerçek ayara dokunmaz):
#   Excel (sütun yeri, başlık öncesi satırlar, tarih biçimi, iki sayfa), noktalı virgüllü CSV (Türkçe sayı ve tarih), TSV → t_ tabloları; SQL toplamı doğru;
#   baştaki sıfırlı kod metin kalır; gizli bilgi hücresi [gizli]; artımlı güncelleme (değişmeyen dosya yeniden yazılmaz, okunamayan dosyanın tablosu korunur,
#   silinen dosyanın tablosu düşer); onaylı proje kartı → kisi/karar/acik_is/olay/terim/proje; kayıt veritabanı ayarlıysa kurulmaz;
#   .doc/.rtf/.odt (macOS textutil) aranır; noktalı virgüllü CSV aramada sütunlara bölünür; toplantı oturumu `tc proje` ve `tc vt-sor`, MCP vt_sor
#   proje veritabanını okur, KAYIT satırı karttan; Konuş'un vt_yol/proje kartı istemi; beta sayaçları yalnız sayı. ~5 sn, model yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/proje-vt.py      (kaldı → çıkış 1)
import importlib.util, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, zipfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path[0] = KOD  # toplanti-claude.py dilimindeki `import baglam` test/baglam.py'yi (sınama) değil kodu alsın
T = tempfile.mkdtemp(prefix="suflor-pvt-"); P = os.path.join(T, "proje"); U = os.path.join(T, "uyg"); os.makedirs(os.path.join(P, "tablolar")); os.makedirs(os.path.join(U, "canli"))
AY = os.path.join(T, "ayar.json"); json.dump({"uygulama": U, "proje": P, "ortak": os.path.join(T, "ortak-yok"), "anlam_arama": False}, open(AY, "w"))
os.environ["SUFLOR_AYAR"] = AY
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f"   [{ek}]" if ek and not k else ""))
    if not k: HATA.append(ad)

def xlsx_yaz(yol, sayfalar):  # küçük .xlsx (stdlib): {"ad": [[hücre…]]}; hücre: str | sayı | ("tarih", excel_seri) — sütun harfli, boş hücre atlanır
    z = zipfile.ZipFile(yol, "w")
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("xl/styles.xml", '<styleSheet><numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/></numFmts>'
               '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="164"/></cellXfs></styleSheet>')
    wb, rel = [], []
    for i, (ad, satirlar) in enumerate(sayfalar.items(), 1):
        wb.append(f'<sheet name="{ad}" sheetId="{i}" r:id="rId{i}"/>'); rel.append(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>')
        rows = []
        for r, sat in enumerate(satirlar, 1):
            cs = []
            for c, h in enumerate(sat):
                ref = chr(65 + c) + str(r)
                if h is None or h == "": continue
                if isinstance(h, tuple): cs.append(f'<c r="{ref}" s="{2 if r % 2 else 1}"><v>{h[1]}</v></c>')
                elif isinstance(h, (int, float)): cs.append(f'<c r="{ref}"><v>{h}</v></c>')
                else: cs.append(f'<c r="{ref}" t="inlineStr"><is><t>{h}</t></is></c>')
            rows.append(f'<row r="{r}">{"".join(cs)}</row>')
        z.writestr(f"xl/worksheets/sheet{i}.xml", f'<worksheet><sheetData>{"".join(rows)}</sheetData></worksheet>')
    z.writestr("xl/workbook.xml", f'<workbook xmlns:r="r"><sheets>{"".join(wb)}</sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels", f'<Relationships>{"".join(rel)}</Relationships>'); z.close()

xlsx_yaz(os.path.join(P, "tablolar", "butce-2026.xlsx"), {
    "Bütçe": [["Bütçe 2026 (taslak)"], [], ["Kalem", "Tutar (TL)", "Tarih", "Sorumlu", "Kod"],
              ["Kira", 12500, ("t", 46327), "Ayşe Yılmaz", "007"], ["Elektrik", 830.5, ("t", 46331), "", "012"],
              ["Yazılım", 4200, ("t", 46357), "Kemal", "Şifre: Kis2024!Portal"], ["", None, None, None, None]],
    "Personel": [["Ad", "Birim", "Kıdem"], ["Ayşe Yılmaz", "Lojistik", 4], ["Kemal Demir", "IT", 2]]})
open(os.path.join(P, "tablolar", "satis.csv"), "w", encoding="utf-8").write("Bölge;Satış;Tarih\nİzmir;1.250,50;03.10.2026\nAnkara;980;04.10.2026\n")
open(os.path.join(P, "tablolar", "stok.tsv"), "w", encoding="utf-8").write("Ürün\tAdet\nVida\t1200\nSomun\t300\n")
html = os.path.join(T, "a.html"); open(html, "w", encoding="utf-8").write('<html><head><meta charset="utf-8"></head><body><h1>Depo notu</h1>'
                                                                          "<p>Rize lojistik merkezi Kasım'da devreye giriyor; sorumlu Gülşen.</p></body></html>")
for e in ("doc", "rtf", "odt"): subprocess.run(["/usr/bin/textutil", "-convert", e, html, "-output", os.path.join(P, f"not-{e}.{e}")], check=True, capture_output=True)

sp = importlib.util.spec_from_file_location("baglam_pvt", os.path.join(KOD, "baglam.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)
c = B.baglan(); B.guncelle(c)
v = sqlite3.connect(B.PROJE_VT)
tab = {r[0]: r for r in v.execute("SELECT * FROM tablolar")}
ok("tablolar: Excel'in iki sayfası + CSV + TSV ayrı tablo, kaynak dosyası ve özgün başlık katalogda",
   set(tab) == {"t_butce_2026_butce", "t_butce_2026_personel", "t_satis", "t_stok"} and tab["t_butce_2026_butce"][1] == "tablolar/butce-2026.xlsx"
   and "tutar_tl = Tutar (TL)" in tab["t_butce_2026_butce"][4], str(tab)[:300])
b = v.execute("SELECT satir, kalem, tutar_tl, tarih, sorumlu, kod FROM t_butce_2026_butce ORDER BY satir").fetchall()
ok("Excel: başlık öncesi satırlar atlanır, satır no kaynaktaki, tarih biçimli sayı ISO tarih (iki biçim), boş satır yok",
   [r[0] for r in b] == [4, 5, 6] and b[0][3] == "2026-11-01" and b[1][3] == "2026-11-05" and b[1][4] in ("", None), str(b))
ok("SQL toplamı doğru (17.530,5), tutar sayı", v.execute("SELECT sum(tutar_tl), typeof(tutar_tl) FROM t_butce_2026_butce").fetchone() == (17530.5, "integer"))
ok("baştaki sıfırlı kod metin kalır, gizli bilgi hücresi [gizli]", [r[5] for r in b] == ["007", "012", "[gizli]"], str([r[5] for r in b]))
s_ = v.execute("SELECT bolge, satis, tarih FROM t_satis ORDER BY satir").fetchall()
ok("noktalı virgüllü CSV: Türkçe sayı (1.250,50 → 1250.5) ve gg.aa.yyyy → ISO", s_ == [("İzmir", 1250.5, "2026-10-03"), ("Ankara", 980, "2026-10-04")], str(s_))
ok("TSV sayıları", v.execute("SELECT sum(adet) FROM t_stok").fetchone()[0] == 1500)
ok("proje.db yalnız sahibine açık (0600)", os.stat(B.PROJE_VT).st_mode & 0o777 == 0o600)
v.close()
# aramada: .doc/.rtf/.odt metni, noktalı virgüllü CSV sütunlara bölünmüş
r, _ = B.ara("Rize lojistik merkezi", n=8, guncel=False); yollar = {x[1] for x in r}
ok(".doc, .rtf, .odt (macOS textutil) dizinde ve aranır", {"not-doc.doc", "not-rtf.rtf", "not-odt.odt"} <= yollar, str(yollar))
r, _ = B.ara("Ankara satış", n=3, guncel=False)
ok("noktalı virgüllü CSV aramada 'Bölge: Ankara · Satış: 980'", any("Bölge: Ankara · Satış: 980" in x[4] for x in r), str([x[4] for x in r])[:200])
# artımlı: değişmeyen dosya yeniden yazılmaz; değişen yalnız kendisi; okunamayan korunur; silinen düşer
r1 = B.proje_vt_guncelle(c)
ok("değişiklik yoksa yeniden yazılmaz", r1.get("degismedi") is True and r1.get("tablo") == 4, str(r1))
time.sleep(0.01); open(os.path.join(P, "tablolar", "satis.csv"), "a", encoding="utf-8").write("Bursa;400;05.10.2026\n"); B.guncelle(c)
k = json.load(open(B.PROJE_VT_KAYIT)); v = sqlite3.connect(B.PROJE_VT)
ok("değişen CSV yeniden yazıldı (3 satır), Excel'e dokunulmadı", v.execute("SELECT count(*) FROM t_satis").fetchone()[0] == 3 and k["tablo"] == 4); v.close()
y = os.path.join(P, "tablolar", "stok.tsv"); os.utime(y, (time.time() + 10, time.time() + 10)); os.chmod(y, 0)
try: B.guncelle(c); v = sqlite3.connect(B.PROJE_VT); n = v.execute("SELECT count(*) FROM t_stok").fetchone()[0]; v.close()
finally: os.chmod(y, 0o644)
ok("okunamayan dosyanın eski tablosu korunur", n == 2)
os.remove(y); B.guncelle(c); v = sqlite3.connect(B.PROJE_VT)
ok("silinen dosyanın tablosu ve katalog satırı düşer", not v.execute("SELECT 1 FROM sqlite_master WHERE name='t_stok'").fetchone() and not v.execute("SELECT 1 FROM tablolar WHERE tablo='t_stok'").fetchone()); v.close()
# onaylı proje kartı → tablolar
kart = {"kip": "genel", "belge": 3, "ozet": "Depo taşıma projesi: İzmir şubesi Kasım'da yeni depoya geçiyor.", "onay": {"t": int(time.time()), "kim": "kullanici"},
        "kisiler": [{"ad": "Ayşe Yılmaz", "takma_adlar": ["Ayşe"], "roller": ["proje yöneticisi"], "kurumlar": ["Lojistik"], "kaynaklar": [["plan.md", "s1"]]},
                    {"ad": "Kemal Demir", "takma_adlar": [], "roller": ["IT"], "kurumlar": [], "kaynaklar": [["plan.md", ""]]}],
        "kurumlar": [{"ad": "Lojistik", "kaynaklar": [["plan.md", "s1"]]}],
        "kararlar": [{"ne": "Depo Gebze'ye taşınacak", "ne_zaman": "2026-11-01", "kim": ["Ayşe Yılmaz"], "kaynaklar": [["plan.md", "s2"]]}],
        "tarihler": [{"ne": "Açılış", "tarih": "2026-11-15", "kaynaklar": [["plan.md", "s3"]], "celiski": {"tarih": ["2026-11-15", "2026-11-20"]}}],
        "acik_isler": [{"is": "Sözleşme imzası", "sahip": ["Kemal Demir"], "tarih": "2026-10-30", "kaynaklar": [["plan.md", "s4"]]},
                       {"is": "Şifre: Kis2024!Portal sıfırlanacak", "sahip": [], "tarih": "", "kaynaklar": []}],
        "sozluk": [{"terim": "Gebze Lojistik Merkezi", "aciklama": "yeni depo", "kaynaklar": [["plan.md", "s2"]]}]}
json.dump(dict(kart, onay=None), open(B.PROJE_KART, "w")); B.guncelle(c); v = sqlite3.connect(B.PROJE_VT)
ok("onaysız kart veritabanına girmez", not v.execute("SELECT 1 FROM sqlite_master WHERE name='kisi'").fetchone() and B.proje_ozeti() == ""); v.close()
json.dump(kart, open(B.PROJE_KART, "w")); os.utime(B.PROJE_KART, (time.time() + 20, time.time() + 20)); B.guncelle(c); v = sqlite3.connect(B.PROJE_VT)
ok("onaylı kart: kisi, karar, acik_is (gizli madde [gizli]), olay (çelişki), terim, proje",
   v.execute("SELECT ad, roller, kaynak FROM kisi ORDER BY ad").fetchall()[0] == ("Ayşe Yılmaz", "proje yöneticisi", "plan.md @s1")
   and [r[0] for r in v.execute("SELECT ne FROM acik_is")] == ["Sözleşme imzası", "[gizli]"] and "2026-11-20" in v.execute("SELECT celiski FROM olay").fetchone()[0]
   and v.execute("SELECT count(*) FROM terim").fetchone()[0] == 1 and "İzmir" in v.execute("SELECT ozet FROM proje").fetchone()[0]); v.close()
oz = B.proje_ozeti()
ok("proje özeti: özet, kişiler, açık işler (gizli madde tek başına düşer), kararlar", "Depo taşıma" in oz and "Ayşe Yılmaz (proje yöneticisi)" in oz
   and "Açık işler: Sözleşme imzası — Kemal Demir (2026-10-30)" in oz and "Kis2024" not in oz and "Gebze" in oz, oz)
# toplantı oturumu: tc proje / tc vt-sor / MCP vt_sor / KAYIT satırı
tc = lambda *a: subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", os.path.join(U, "canli"), *a], capture_output=True, text=True, timeout=30,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
o = tc("proje").stdout
ok("tc proje: kart özeti + tablolar (kaynak notu)", "Proje özeti" in o and "Sözleşme imzası" in o and "t_butce_2026_butce" in o and "kisi (tablo" in o, o[:300])
o = tc("vt-sor", "SELECT round(sum(tutar_tl), 1) AS toplam FROM t_butce_2026_butce").stdout
ok("tc vt-sor proje veritabanında toplam", "17530.5" in o, o)
p = subprocess.Popen([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", os.path.join(U, "canli"), "vt-mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
for m in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "vt_sor", "arguments": {"sorgu": "SELECT ne FROM karar"}}}):
    p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush(); cevap = p.stdout.readline()
p.stdin.close(); p.wait(timeout=10)
ok("MCP vt_sor (Konuş'un aracı) proje veritabanını okur", "Gebze" in cevap, cevap[:200])
ad = json.load(open(os.path.join(U, "canli", "vt-adlar.json"))).get("adlar") if os.path.exists(os.path.join(U, "canli", "vt-adlar.json")) else []
ok("kişi adları Konuş ad düzeltmesine (vt-adlar.json) karttan", "Ayşe Yılmaz" in ad and "Ayşe" in ad, str(ad))
kod_tc = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read()
ns = {"os": os, "re": re, "json": json, "sys": sys, "time": time, "PROJE": P, "AYAR": json.load(open(AY))}
exec(kod_tc[kod_tc.index("VT = AYAR.get(\"veritabani\")"):kod_tc.index("VT_GIZLI = re.compile")], ns)
ns["AYAR"]["uygulama"] = U
ok("KAYIT satırı karttan ('proje kartı, kullanıcı onaylı'), adı geçen kişi", any("proje kartı, kullanıcı onaylı" in l for l in ns["vt_kayit"]("Kemal Demir sözleşmeyi ne zaman imzalar?"))
   and any("Kemal Demir — IT" in l for l in ns["vt_kayit"]("Kemal Demir sözleşmeyi ne zaman imzalar?")), str(ns["vt_kayit"]("Kemal Demir sözleşmeyi ne zaman imzalar?")))
# Konuş: vt_yol / proje kartı istemi (kod dilimi)
kod_k = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
nk = {"os": os, "time": time, "json": json, "re": re, "BASE": os.path.join(U, "canli"), "print": lambda *a: None, "_t": lambda tr, en: tr, "AYAR": {"proje": P, "uygulama": U}, "_KS": {}}
exec(kod_k[kod_k.index("VT_TAZE_SN = "):kod_k.index("BRIFING_YASAK = ")], nk)
ok("Konuş: kayıt veritabanı yoksa proje.db (vt_yol), kayıt veritabanı varsa o; proje_vt: false kapatır",
   nk["vt_yol"]() == os.path.join(U, "proje.db") and nk["vt_proje_mi"]() and (nk["AYAR"].update(veritabani={"yol": "kayit.db"}) or nk["vt_yol"]() == os.path.join(P, "kayit.db"))
   and not nk["vt_proje_mi"]() and (nk["AYAR"].pop("veritabani") and nk["AYAR"].update(proje_vt=False) or nk["vt_yol"]() is None))
nk["AYAR"].pop("proje_vt", None)
nk.update({"_onara_mod": lambda: B, "ARAYUZ_DILI": "tr", "BRIFING_YASAK": ("Bash", "Write", "Edit")})
exec(kod_k[kod_k.index("def proje_kart_mt():"):kod_k.index("def konus_istem(")], nk)
ok("Konuş istemine proje kartı özeti girer; yardımcının yasak sözcüğü varsa girmez", "Sözleşme imzası" in nk["proje_ozeti_istem"]()
   and (nk.update(BRIFING_YASAK=("Sözleşme",)) or nk["proje_ozeti_istem"]() == "") and nk["proje_kart_mt"]() == os.path.getmtime(B.PROJE_KART))
ist = kod_k[kod_k.index("def konus_istem("):kod_k.index("# --- Hızlı bilgi")]
ok("Konuş istemi: proje veritabanı açıklaması (t_ tabloları SQL'le) ve kart değişince süreç yenilenir",
   "pvt = vt_proje_mi()" in ist and "satırları kendin toplama" in ist and "oz = proje_ozeti_istem()" in ist and '"proje kartı değişti"' in kod_k)
# beta sayaçları: yalnız sayı; teshis süzgecinden geçer
kod_b = open(os.path.join(KOD, "aktarici", "beta-veri.py"), encoding="utf-8").read()
now = time.time(); iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S+03:00", time.localtime(t))
gec = [{"at": iso(now - 60), "soru": "Ayşe'nin işi ne?", "sesli": "Kayıtlarda bunu bulamadım."}, {"at": iso(now - 50), "soru": "kaç?", "sesli": "Toplam 17.530 lira."},
       {"at": iso(now - 9e5), "soru": "eski", "sesli": "bulamadım"}]
nb = {"re": re, "os": os, "json": json, "AYAR": {"uygulama": U}, "_jsonl": lambda ad: gec if ad == "konus-gecmis.jsonl" else [{"t": now - 30, "soru": "x", "sorgu": ["SELECT 1"]}],
      "_ts": lambda r, k="at": (time.mktime(time.strptime(r[k][:19], "%Y-%m-%dT%H:%M:%S")) if isinstance(r.get(k), str) else r.get(k)),
      "beta_say": lambda ad, b, s: {"on_arama": 5, "on_arama_bos": 2}.get(ad, 0)}
exec(kod_b[kod_b.index("BULAMADI_RX = "):kod_b.index("def _beta_olaylar(")], nb)
bi = nb["_beta_bilgi"](now - 3600, now + 1); pv = nb["_beta_proje_vt"]()
import teshis
tm = teshis.temizle({"kalite": {"bilgi": bi}, "proje_vt": pv})
ok("beta: Konuş cevabı, 'bulamadım', veritabanı sorgusu, ön arama/boş sayıları; proje veritabanı büyüklüğü — süzgeçten aynen (yalnız sayı/seçenek)",
   bi == {"konus_cevap": 2, "bulamadi": 1, "veritabani_sorgu": 1, "on_arama": 5, "on_arama_bos": 2} and pv["kuruldu"] and pv["tablo"] == 3 and pv["kart_kisi"] == 2
   and tm == {"kalite": {"bilgi": bi}, "proje_vt": pv} and "Ayşe" not in json.dumps(tm, ensure_ascii=False), json.dumps(tm, ensure_ascii=False))
ok("beta: ön arama boş günlük satırı sayaç kalıbına uyuyor", "ön arama sonuç yok" in kod_k and re.search(r'"on_arama_bos", re\.compile\(r"\^KONUŞ: ön arama sonuç yok"\)', kod_b))
# kayıt veritabanı ayarlıysa proje veritabanı kurulmaz
U2 = os.path.join(T, "uyg2"); os.makedirs(os.path.join(U2, "canli")); AY2 = os.path.join(T, "ayar2.json")
json.dump({"uygulama": U2, "proje": P, "ortak": os.path.join(T, "ortak-yok"), "anlam_arama": False, "veritabani": {"yol": "kayit.db"}}, open(AY2, "w"))
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "baglam.py"), "proje-vt"], capture_output=True, text=True, timeout=60, env=dict(os.environ, SUFLOR_AYAR=AY2, PYTHONDONTWRITEBYTECODE="1"))
ok("kayıt veritabanı ayarlıysa proje.db kurulmaz, özet boş", "kapalı" in r.stdout and not os.path.exists(os.path.join(U2, "proje.db")), r.stdout + r.stderr[-200:])
shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not HATA else 'KALDI: ' + str(len(HATA))}")
sys.exit(1 if HATA else 0)
