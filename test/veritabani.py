#!/usr/bin/env python3
# Kayıt veritabanı bağlantısının regresyon testi (ayar "veritabani"; toplanti-claude.py vt_sorgu / sistemler / vt_kayit /
# hazirlik --kim). Geçici klasörde yapay bir SQLite veritabanı ve ayar kurar; gerçek ayar, _canli ve proje verisine dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/veritabani.py      (kaldı → çıkış 1)
import contextlib, importlib.util, io, json, os, shutil, sqlite3, subprocess, sys, tempfile
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT = bos_port(8796)

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-vt-")
proje, canli = os.path.join(T, "proje"), os.path.join(T, "canli")
os.makedirs(proje); os.makedirs(canli)
DB = os.path.join(proje, "kayit.db")
con = sqlite3.connect(DB)
con.executescript("""
CREATE TABLE sistem (id TEXT PRIMARY KEY, ad TEXT, sahip TEXT, erisen INTEGER);
INSERT INTO sistem VALUES ('fatura','Fatura Paneli / Tahsilat','Finans',4), ('depo','Depo Takip','Operasyon',7),
                          ('depo-api','Depo Takip — entegrasyon','Teknik',2);
CREATE TABLE kisi (id TEXT PRIMARY KEY, ad TEXT, lakap TEXT, gorev TEXT);
INSERT INTO kisi VALUES ('ayse','Ayşe Deneme','Ayşe','Finans yöneticisi'), ('can','Can Örnek',NULL,'Depo sorumlusu');
CREATE TABLE karar (no INTEGER PRIMARY KEY, ozet TEXT);
CREATE TABLE hesap (id TEXT PRIMARY KEY, ad TEXT, sifre TEXT);
INSERT INTO hesap VALUES ('h1','Fatura yönetici','GIZLI-DEGER-1'), ('h2','Depo','GIZLI-DEGER-2');
CREATE VIEW v_hesap AS SELECT id, ad, sifre, (sifre IS NOT NULL) AS dolu FROM hesap;
""")
con.commit(); con.close()
AYAR = {"alan": "Test", "ad": "Deneme Kullanici", "port": PORT, "uygulama": os.path.join(T, "uyg"), "proje": proje,
        "ortak": os.path.join(T, "ortak"), "yerel_ses": False, "teshis": False, "dil": "tr",
        "veritabani": {"yol": "kayit.db", "sistemler": "SELECT ad FROM sistem",
                       "sistemler_kart": "SELECT ad, ad || ' — sahip: ' || sahip || ' · erişen ' || erisen FROM sistem",
                       "kisiler": "SELECT ad || coalesce(','||lakap,''), ad || ' — ' || gorev FROM kisi"}}
json.dump(AYAR, open(os.path.join(T, "ayar.json"), "w"), ensure_ascii=False)
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json"); os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

def yukle():  # toplanti-claude.py'yi modül olarak (zararsız "acik" komutuyla) yükler
    sys.path.insert(0, KOD); sys.argv = ["tc", "--dir", canli, "acik"]
    spec = importlib.util.spec_from_file_location("tc", os.path.join(KOD, "toplanti-claude.py")); m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    return m

ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
try:
    m = yukle(); mt0 = os.path.getmtime(DB)
    ad = m.sistemler()
    kontrol("sistem adları veritabanından (bölünmüş adlar dahil)", all(x in ad for x in ("fatura paneli", "tahsilat", "depo takip")))
    k1 = "\n".join(m.vt_kayit("Tahsilat tarafında kim yetkili?"))
    kontrol("SORU'da geçen sistemin KAYIT satırı", "KAYIT (kayit.db" in k1 and "Fatura Paneli / Tahsilat — sahip: Finans" in k1)
    k2 = m.vt_kayit("Depo Takip entegrasyon ayarını Ayşe mi yaptı?")
    kontrol("en çok 2 satır, uzun eşleşme önce, kişi de eklenir", len(k2) == 3 and "Depo Takip — entegrasyon" in k2[1] and "Ayşe Deneme" in k2[2])
    kontrol("ilgisiz soruda KAYIT satırı yok", m.vt_kayit("Toplantı kaçta bitiyor?") == [])
    for sor, q in [("DELETE", "DELETE FROM sistem"), ("iki komut", "SELECT 1; DELETE FROM sistem"),
                   ("WITH ile yazma", "WITH x AS (SELECT 1) INSERT INTO karar(no) SELECT 9 FROM x")]:
        m.VT["deneme"] = q; kontrol(f"yazma sorgusu reddedildi ({sor})", m.vt_sorgu("deneme") == [])
    c = sqlite3.connect(DB)
    kontrol("veritabanı değişmedi", os.path.getmtime(DB) == mt0 and c.execute("SELECT count(*) FROM sistem").fetchone()[0] == 3
            and c.execute("SELECT count(*) FROM karar").fetchone()[0] == 0); c.close()
    # O4 (v0.97.2): gizli sütun takma adla, ifade içinde, alt sorguda, WHERE'de, CTE ve görünümden okunamaz; görünümün iç işleyişi sürer
    for sor, q in [("AS takma adı", "SELECT sifre AS x FROM hesap"), ("ifade içinde", "SELECT upper(sifre) || '' FROM hesap"),
                   ("alt sorgu", "SELECT (SELECT sifre FROM hesap LIMIT 1) AS y"), ("CTE", "WITH c AS (SELECT sifre AS z FROM hesap) SELECT z FROM c"),
                   ("CTE görünüm adıyla", "WITH v_hesap AS (SELECT sifre AS ad FROM hesap) SELECT ad FROM v_hesap"),
                   ("özyinelemeli CTE", "WITH RECURSIVE r(n, s) AS (SELECT 1, (SELECT sifre FROM hesap LIMIT 1) UNION ALL SELECT n+1, s FROM r WHERE n < 2) SELECT s FROM r"),
                   ("görünümden takma adla", "SELECT sifre AS w FROM v_hesap"), ("substr/hex", "SELECT hex(substr(sifre,1,3)) h FROM hesap"),
                   ("json", "SELECT json_object('a', sifre) j FROM hesap")]:
        try: r = m.vt_sor_metin(q)
        except m.VtHata as e: r = str(e)
        kontrol(f"gizli sütun açık dönmez ({sor})", "GIZLI" not in r and "47495A" not in r)
    r = m.vt_sor_metin("SELECT count(*) n FROM hesap WHERE sifre LIKE 'GIZLI%'")
    kontrol("WHERE ile değer tahmini yapılamaz (0 satır sayılır)", r.split("\n")[1] == "0")
    r = m.vt_sor_metin("SELECT ad, dolu FROM v_hesap ORDER BY id")
    kontrol("görünüm kendi içinde gizli sütunu kullanabilir, öbür sütunlar açık", "Fatura yönetici\t1" in r)
    kontrol("sema'da [gizli] işareti sürer", "sifre [gizli]" in m.vt_sema_metin())
    for sor, q in [("ATTACH", "SELECT * FROM pragma_database_list"), ]:
        try: r = m.vt_sor_metin(q); kontrol(f"tablo değerli pragma reddedildi ({sor})", False)
        except m.VtHata: kontrol(f"tablo değerli pragma reddedildi ({sor})", True)
    m.VT["yol"] = "yok.db"; m._VT_ON.clear()
    kontrol("veritabanı yoksa sessizce boş (eski davranış)", m.vt_sorgu("sistemler") == [] and m.vt_kayit("Tahsilat?") == [])
    h = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "hazirlik", "--kim", "Ayşe"],
                       capture_output=True, text=True, timeout=120, env=os.environ).stdout
    kontrol("hazirlik --kim başında kişi kartı", "## Ayşe: kişi kartı (kayit.db)" in h and "Ayşe Deneme — Finans yöneticisi" in h)
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
