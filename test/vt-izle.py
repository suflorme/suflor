#!/usr/bin/env python3
# v0.62.0 (proje hazırlığı T0) — kayıt veritabanı önbelleklerinin Konuş'tan bağımsız yazılması: toplanti-claude.py vt-izle (tablo yapısı, kişi adları,
# değişme saati, sorgu sonuçları; tek kopya kilidi) ve aktarıcının yardımcıyı açma kararı (vt_izle_bak: önbellek eskiyse, en çok 5 dk'da bir).
# Geçici veritabanı ve ayarla; gerçek ayar ve _canli'ye dokunmaz (~3 sn). vt-izle ya da tetikleme değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/vt-izle.py
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-vt-izle-"); proje, canli = os.path.join(T, "proje"), os.path.join(T, "canli")
os.makedirs(proje); os.makedirs(canli)
DB = os.path.join(proje, "kayit.db"); con = sqlite3.connect(DB)
con.executescript("CREATE TABLE kisi (id TEXT PRIMARY KEY, ad TEXT, lakap TEXT, sifre TEXT); INSERT INTO kisi VALUES ('a','Vedran Kaya','Vedo','gizli1');")
con.commit(); con.close()
json.dump({"alan": "Test", "ad": "Deneme", "port": 8795, "uygulama": os.path.join(T, "uyg"), "proje": proje, "ortak": os.path.join(T, "ortak"), "dil": "tr",
           "veritabani": {"yol": "kayit.db", "kisiler": "SELECT ad || coalesce(','||lakap,''), ad FROM kisi"}}, open(os.path.join(T, "ayar.json"), "w"))
ENV = dict(os.environ, SUFLOR_AYAR=os.path.join(T, "ayar.json"), PYTHONDONTWRITEBYTECODE="1")
tc = lambda *a, **k: subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, *a], env=ENV, capture_output=True, text=True, **k)
oku = lambda f: json.load(open(os.path.join(canli, f), encoding="utf-8"))
try:
    r = tc("vt-izle", "--bir")
    ok("vt-izle --bir: dört önbellek yazıldı", all(os.path.exists(os.path.join(canli, f)) for f in ("vt-sema.txt", "vt-mt.json", "vt-adlar.json", "vt-sonuc.json")) and r.returncode == 0)
    ok("tablo yapısı, gizli sütun işaretli", "kisi (tablo, 1 satır)" in open(os.path.join(canli, "vt-sema.txt")).read() and "sifre [gizli]" in open(os.path.join(canli, "vt-sema.txt")).read())
    ok("kişi ve takma adlar", set(oku("vt-adlar.json")["adlar"]) == {"Vedran Kaya", "Vedo"})
    m = oku("vt-mt.json"); ok("değişme saati ve denetim anı", abs(m["mt"] - os.path.getmtime(DB)) < 1 and time.time() - m["kontrol"] < 10)
    ok("önbellek dosyaları yalnız sahibine açık (0600)", all(oct(os.stat(os.path.join(canli, f)).st_mode & 0o777) == "0o600" for f in ("vt-sema.txt", "vt-mt.json", "vt-adlar.json")))
    # önbellekteki sorgu veritabanı değişince yeniden çalışır
    json.dump({"SELECT count(*) AS n FROM kisi": {"t": 0, "kontrol": 0, "mt": 0, "sonuc": "n\n0\n(1 satır)"}}, open(os.path.join(canli, "vt-sonuc.json"), "w"))
    con = sqlite3.connect(DB); con.execute("INSERT INTO kisi VALUES ('b','Selin Ak',NULL,'x')"); con.commit(); con.close()
    tc("vt-izle", "--bir"); s = oku("vt-sonuc.json")["SELECT count(*) AS n FROM kisi"]
    ok("veritabanı değişince önbellekteki sorgu yeniden çalıştı ve adlar güncellendi", "\n2\n" in s["sonuc"] and time.time() - s["kontrol"] < 10 and "Selin Ak" in oku("vt-adlar.json")["adlar"])
    p = subprocess.Popen([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "vt-izle", "--sure", "60"], env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5); r2 = tc("vt-izle", "--bir"); p.terminate(); p.wait()
    ok("tek kopya: ikincisi çalışmaz", "zaten çalışıyor" in r2.stdout)
    ok("kilit süreç bitince bırakılır", "zaten" not in tc("vt-izle", "--bir").stdout)
    a2 = json.load(open(os.path.join(T, "ayar.json"))); a2.pop("veritabani"); json.dump(a2, open(os.path.join(T, "ayar.json"), "w"))
    ok("veritabanı ayarlı değilse hiçbir şey yazmaz", "ayarlı değil" in tc("vt-izle", "--bir").stdout)
    # --- aktarıcının yardımcıyı açma kararı (vt_izle_bak), sahte saat ve sahte "open" ile ---------------------------------------------------
    kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
    acilan = []
    class SP:
        DEVNULL = None
        @staticmethod
        def Popen(k, **_): acilan.append(k)
    app = os.path.join(T, "Suflor Brifing.app"); os.makedirs(app)
    ad = {"os": os, "json": json, "time": time, "subprocess": SP, "print": lambda *a: None, "BASE": canli, "BRIFING_APP": app,
          "AYAR": {"veritabani": {"yol": "kayit.db"}, "uygulama": T}, "threading": None}
    bol = kod[kod.index("# --- Veritabanı önbelleği yardımcısı"):kod.index("def _vt_izle_dongu(")]
    exec(bol, ad); bak = ad["vt_izle_bak"]; os.remove(os.path.join(canli, "vt-mt.json"))
    t0 = 1_000_000.0
    ok("önbellek yoksa yardımcı açılır (--vt-izle <canli>)", bak(t0) and acilan[-1][-2:] == ["--vt-izle", canli] and "-g" in acilan[-1])
    ok("5 dk dolmadan yeniden açılmaz", not bak(t0 + 120) and len(acilan) == 1)
    json.dump({"mt": 1, "kontrol": t0 + 300}, open(os.path.join(canli, "vt-mt.json"), "w"))
    ok("önbellek tazeyse açılmaz", not bak(t0 + 400) and len(acilan) == 1)
    ok("önbellek 150 sn'den eskiyse (ve 5 dk geçtiyse) yeniden açılır", bak(t0 + 300 + 151) and len(acilan) == 2)
    ad["BASE"] = os.path.join(T, "baska"); bak2 = ad["vt_izle_bak"]; ad["_VTI"]["t"] = 0
    ok("deneme aktarıcısı (canli/ uygulama klasöründe değil) yardımcıyı açmaz", not bak2(t0 + 5000) and len(acilan) == 2); ad["BASE"] = canli
    ad["AYAR"] = {}; ok("veritabanı ayarlı değilse açılmaz", not bak(t0 + 2000) and len(acilan) == 2)
    ad["AYAR"] = {"veritabani": {"yol": "kayit.db"}}; shutil.rmtree(app); ok("yardımcı kurulu değilse açılmaz", not bak(t0 + 3000) and len(acilan) == 2)
    # --- panodaki izin uyarısı (proje_erisim_view) ------------------------------------------------------------------------------------------
    ad.update(_t=lambda a, b: a, _ONARA={"eris": None}); exec(kod[kod.index("VT_IZIN_SN = "):kod.index("# --- Ad düzeltmesi")], ad); pv = ad["proje_erisim_view"]
    ad["_VTI"].update(durum=True, t=t0); ok("her şey yolundaysa uyarı yok", pv(t0 + 1000) is None)
    ad["_VTI"].update(durum=False, t=t0); ok("yardımcı yeni açıldıysa (3 dk dolmadan) uyarı yok", pv(t0 + 60) is None)
    u = pv(t0 + 200); ok("açıldıktan 3 dk sonra önbellek hâlâ eskiyse: veritabanı uyarısı + izin yolu", u and "kayıt veritabanını okuyamıyor" in u["uyari"] and "Dosyalar ve Klasörler" in u["yol"])
    ad["_VTI"].update(durum=True); ad["_ONARA"]["eris"] = ([""], "hata"); u = pv(t0 + 200)
    ok("yardımcı belgeleri dizinleyemediyse: proje belgeleri uyarısı", u and u["uyari"].endswith("proje belgelerini okuyamıyor"))
    ad["_ONARA"]["eris"] = ([""], "tamam"); ok("yardımcı dizinlediyse uyarı yok", pv(t0 + 200) is None)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("vt-izle:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
