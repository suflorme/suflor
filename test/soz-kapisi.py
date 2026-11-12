#!/usr/bin/env python3
# Tek söz kapısı (aktarici/soz-kapisi.py; 9 Kasım): engeller (gizli, toplantı, sessiz, mesai, gece), öncelik, aralık, günlük bütçe, tekrar önleme, kuyruk (sonra → yeniden değerlendirme,
# geçerlilik), sunuş/sonuç kaydı (metin yok), otomatik yoksay, yeniden başlatma, /status "soz" alanı ve olcum.py isabet. Birim: kapı yalıtılmış ad alanında, sahte saatle (gerçek bildirim/ses yok).
# Kaynak uçları (/proaktif, /eposta-onemli, /toplanti-hatirlat, /yaklasan-tarihler) → soz_sonuc bağlantısı: test/proaktif-oneri.py, toplanti-hatirlat.py, eposta-takip.py, kisisel-tarihler.py.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/soz-kapisi.py      (kaldı → çıkış 1)
import datetime, importlib.util, json, os, re, shutil, sys, tempfile, threading, time
sys.dont_write_bytecode = True; os.environ["SUFLOR_TEST_SOZ_DONGU_YOK"] = "1"
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="soz-kapisi-")
SAAT = {"t": datetime.datetime(2026, 11, 11, 11, 0).timestamp()}  # Çarşamba 11:00 (mesai içi)
def dk(n): return n * 60
def kur(ad="a", **ek):
    d = os.path.join(T, ad); os.makedirs(d, exist_ok=True); lock = threading.Lock(); bil = []
    def write(pairs):
        for yol, metin in pairs:
            with open(yol, "a", encoding="utf-8") as f: f.write(metin)
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": {}, "BASE": d, "LOCK": lock, "write": write, "SOHBET": {"acik": False},
          "bildirim": lambda *a, **k: bil.append(a), "gizli_acik": lambda: False, "toplanti_var": lambda: False, "aktif_dosya": lambda: None, "sessiz_acik": lambda: False,
          "calisma_saatleri": lambda: ({0, 1, 2, 3, 4}, 540, 1080), "_t": lambda tr, en: tr, "print": lambda *a, **k: None}
    ns.update(ek); ns["BIL"] = bil; ns["D"] = d; ns["SOZ_SAAT"] = lambda: SAAT["t"]  # sahte saat açılışta da (kapı SOZ_SAAT'i önceden tanımlıysa korur)
    exec(compile(open(os.path.join(KOD, "aktarici", "soz-kapisi.py"), encoding="utf-8").read(), "soz-kapisi.py", "exec"), ns)
    return ns
def satirlar(N):
    try: return [json.loads(l) for l in open(os.path.join(N["D"], "soz.jsonl"), encoding="utf-8") if l.strip()]
    except OSError: return []
def sayac():
    c = {"n": 0}
    def f(): c["n"] += 1
    return c, f

# --- temel: şimdi, kayıt, metin ve ham anahtar yazılmaz ---
N = kur("temel"); c, f = sayac()
r = N["soz_aday"]("gun_ici", "Gizli içerikli cümle Ayşe Hanım", anahtar="gec:s17 Ayşe", oncelik=1, kip="sor", teslim=f)
ok("temel: şimdi, teslim bir kez çalıştı", r["karar"] == "simdi" and c["n"] == 1 and r["id"].startswith("z"), r)
ls = satirlar(N); ham = open(os.path.join(N["D"], "soz.jsonl"), encoding="utf-8").read()
ok("kayıt: sunuldu satırı (kaynak, öncelik, kip, karar), METİN ve ham anahtar yok", len(ls) == 1 and ls[0]["olay"] == "sunuldu" and ls[0]["karar"] == "simdi" and ls[0]["kaynak"] == "gun_ici" and ls[0]["kip"] == "sor"
   and "Ayşe" not in ham and "s17" not in ham and "içerik" not in ham and len(ls[0]["a"]) == 10, ham)
ok("teslim işlevi verilmezse varsayılan bildirim (kaynak başlığıyla)", N["soz_aday"]("eposta", "2 yeni e-posta", anahtar="x1", oncelik=3)["karar"] == "simdi" and N["BIL"] and N["BIL"][-1][1] == "E-posta" and N["BIL"][-1][2] == "2 yeni e-posta", N["BIL"])
ok("öncelik/kip sınırlanır (saçma değer çökmez)", N["soz_aday"]("sistem", "x", anahtar="x2", oncelik="abc", kip="yok", teslim=lambda: None)["karar"] in ("simdi", "sonra", "bastirildi"))

# --- tekrar önleme ---
N = kur("tekrar"); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=50); c, f = sayac()
a1 = N["soz_aday"]("eposta", "a", anahtar="ayni", teslim=f); a2 = N["soz_aday"]("eposta", "a", anahtar="ayni", teslim=f)
ok("tekrar: aynı anahtar ikinci kez sunulmaz (teslim bir kez), önceki kimlik döner", a1["karar"] == "simdi" and a2["karar"] == "bastirildi" and a2["neden"] == "tekrar" and a2["id"] == a1["id"] and c["n"] == 1 and len(satirlar(N)) == 1, (a1, a2))
ok("aynı anahtar başka kaynakta ayrı söz", N["soz_aday"]("gun_ici", "a", anahtar="ayni", teslim=f)["karar"] == "simdi")
SAAT["t"] += 6 * 3600 + 5
ok("tekrar süresi (6 sa) dolunca yeniden sunulabilir", N["soz_aday"]("eposta", "a", anahtar="ayni", teslim=f)["karar"] == "simdi" and c["n"] == 3)
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- aralık ve öncelik ---
N = kur("aralik"); c, f = sayac(); c3, f3 = sayac()
r1 = N["soz_aday"]("gun_ici", "bir", anahtar="b1", teslim=f); r2 = N["soz_aday"]("eposta", "iki", anahtar="b2", teslim=f)
ok("aralık: ikinci acil olmayan söz 20 dk dolana dek bekler (sonra, aralık dolmadı)", r1["karar"] == "simdi" and r2["karar"] == "sonra" and r2["neden"] == "aralık dolmadı" and c["n"] == 1, (r1, r2))
ok("acil (öncelik 3) aralığı aşar", N["soz_aday"]("toplanti_hatirlat", "acil", anahtar="b3", oncelik=3, teslim=f3)["karar"] == "simdi" and c3["n"] == 1)
ok("kuyruktaki aynı anahtar 'kuyrukta' döner, ikinci kayıt oluşmaz", N["soz_aday"]("eposta", "iki", anahtar="b2", teslim=f)["neden"] == "kuyrukta" and N["soz_view"]()["kuyruk"] == 1)
SAAT["t"] += dk(19); ok("19 dk: dakikalık tur hâlâ bekletir", N["soz_tur"]()["teslim"] == 0 and c["n"] == 1)
SAAT["t"] += dk(2); tr = N["soz_tur"]()
ok("21 dk: dakikalık tur kuyruktakini teslim eder", tr["teslim"] == 1 and c["n"] == 2 and N["soz_view"]()["kuyruk"] == 0, tr)
ok("kayıtta sunuldu(sonra) → teslim (bekleme süreli) akışı", [(x["olay"], x.get("karar")) for x in satirlar(N) if x["kaynak"] == "eposta"] == [("sunuldu", "sonra"), ("teslim", None)] and satirlar(N)[-1]["bekleme_sn"] >= 1200, satirlar(N))
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- günlük bütçe ---
N = kur("butce"); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=2); c, f = sayac()
rs = [N["soz_aday"]("eposta", "m", anahtar="k%d" % i, teslim=f)["karar"] for i in range(4)]
ok("bütçe 2: üçüncü ve dördüncü bastırıldı", rs == ["simdi", "simdi", "bastirildi", "bastirildi"] and c["n"] == 2, rs)
ok("acil bütçeyi aşar", N["soz_aday"]("sistem", "x", anahtar="k9", oncelik=3, teslim=f)["karar"] == "simdi")
v = N["soz_view"]()
ok("/status soz: sunulan, bastırılan, kuyruk, bütçe", v == {"sunulan": 3, "bastirilan": 2, "bayat": 0, "kuyruk": 0, "butce": 2, "kalan": 0}, v)
SAAT["t"] += 86400; N["soz_tur"]()
ok("ertesi gün sayaç sıfırlanır, bütçe yeniden", N["soz_view"]()["sunulan"] == 0 and N["soz_aday"]("eposta", "m", anahtar="yeni", teslim=f)["karar"] == "simdi")
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- gizli kip ---
N = kur("gizli", gizli_acik=lambda: True); c, f = sayac()
r = N["soz_aday"]("eposta", "x", anahtar="g1", oncelik=3, teslim=f)
ok("gizli kip: acil bile sunulmaz; kayıt, kuyruk, sayaç yok", r["karar"] == "bastirildi" and r["neden"] == "gizli kip" and c["n"] == 0 and satirlar(N) == [] and N["soz_view"]()["kuyruk"] == 0 and N["soz_view"]()["bastirilan"] == 0, r)
r2 = N["soz_aday"]("sistem", "x", anahtar="g2", oncelik=3, teslim=f)
ok("gizli kip: sistem uyarısı kayıtsız hemen gösterilir", r2["karar"] == "simdi" and c["n"] == 1 and satirlar(N) == [], (r2, c))
ok("gizli kipte dakikalık tur hiçbir şey yapmaz", N["soz_tur"]() == {"teslim": 0, "gecti": 0, "yoksay": 0, "bastirildi": 0, "bayat": 0})
g = {"a": False}; N = kur("gizli2", gizli_acik=lambda: g["a"]); N["AYAR"]["soz_aralik_dk"] = 0
dur = {"v": True}; N["toplanti_var"] = lambda: dur["v"]; c, f = sayac()
N["soz_aday"]("eposta", "m", anahtar="q1", teslim=f); g["a"] = True; dur["v"] = False; SAAT["t"] += 300
ok("kuyruktaki söz gizli kip sürerken teslim edilmez, gizli bitince edilir", N["soz_tur"]()["teslim"] == 0 and c["n"] == 0 and (g.__setitem__("a", False) or N["soz_tur"]()["teslim"] == 1) and c["n"] == 1)
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- toplantı, sessiz mod, mesai, gece ---
N = kur("engel"); N["AYAR"]["soz_aralik_dk"] = 0; top = {"v": True}; N["toplanti_var"] = lambda: top["v"]; c, f = sayac()
r = N["soz_aday"]("eposta", "m", anahtar="t1", oncelik=2, teslim=f)
ok("toplantı sürerken ilgisiz aday bekler (öncelik 2 dahil)", r["karar"] == "sonra" and r["neden"] == "toplantı sürüyor" and c["n"] == 0, r)
ok("toplantıyla ilgili aday geçer", N["soz_aday"]("gun_ici", "m", anahtar="t2", teslim=f, ek={"toplantiyla_ilgili": True})["karar"] == "simdi")
ok("acil toplantıda da gider", N["soz_aday"]("toplanti_hatirlat", "m", anahtar="t3", oncelik=3, teslim=f)["karar"] == "simdi")
top["v"] = False; ok("toplantı bitince kuyruktaki teslim edilir", N["soz_tur"]()["teslim"] == 1)
N = kur("sessiz"); N["AYAR"]["soz_aralik_dk"] = 0; N["sessiz_acik"] = lambda: True; c, f = sayac()
ok("sessiz mod: öncelik 0–2 bekler, acil geçer", N["soz_aday"]("eposta", "m", anahtar="s1", oncelik=2, teslim=f)["neden"] == "sessiz mod" and N["soz_aday"]("kisisel_tarih", "m", anahtar="s2", teslim=f)["neden"] == "sessiz mod"
   and N["soz_aday"]("sistem", "m", anahtar="s3", oncelik=3, teslim=f)["karar"] == "simdi" and c["n"] == 1)
SAAT["t"] = datetime.datetime(2026, 11, 14, 11, 0).timestamp()  # Cumartesi
N = kur("mesai"); N["AYAR"]["soz_aralik_dk"] = 0; c, f = sayac()
ok("mesai dışı (hafta sonu): normal bekler, önemli (2) geçer, acil geçer", N["soz_aday"]("kisisel_tarih", "m", anahtar="m1", teslim=f)["neden"] == "mesai dışı"
   and N["soz_aday"]("eposta", "m", anahtar="m2", oncelik=2, teslim=f)["karar"] == "simdi" and N["soz_aday"]("sistem", "m", anahtar="m3", oncelik=3, teslim=f)["karar"] == "simdi")
N["calisma_saatleri"] = lambda: ({0, 1, 2, 3, 4, 5, 6}, 0, 1439); SAAT["t"] = datetime.datetime(2026, 11, 11, 23, 30).timestamp()
N = kur("gece", calisma_saatleri=lambda: ({0, 1, 2, 3, 4, 5, 6}, 0, 1439)); N["AYAR"]["soz_aralik_dk"] = 0; c, f = sayac()
ok("gece (22–07): öncelik 0–2 bekler, acil geçer", N["soz_aday"]("eposta", "m", anahtar="n1", oncelik=2, teslim=f)["neden"] == "gece" and N["soz_aday"]("sistem", "m", anahtar="n2", oncelik=3, teslim=f)["karar"] == "simdi")
N["AYAR"]["soz_gece"] = False; ok("ayar soz_gece false → gece engeli yok", N["soz_aday"]("eposta", "m", anahtar="n3", oncelik=2, teslim=f)["karar"] == "simdi")
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()
N = kur("asistan"); N["AYAR"]["soz_aralik_dk"] = 0; N["SOHBET"]["acik"] = True; c, f = sayac()
ok("asistan meşgulken 'sor/onayla' kipi bekler, 'bildir' gider", N["soz_aday"]("gun_ici", "m", anahtar="a1", kip="sor", teslim=f)["neden"] == "asistan meşgul" and N["soz_aday"]("eposta", "m", anahtar="a2", kip="bildir", teslim=f)["karar"] == "simdi")

# --- geçerlilik: süresi dolan düşer ---
N = kur("gecerli"); N["AYAR"]["soz_aralik_dk"] = 0; N["sessiz_acik"] = lambda: True; c, f = sayac()
N["soz_aday"]("kisisel_tarih", "m", anahtar="e1", teslim=f, gecerli_sn=600); SAAT["t"] += 700; tr = N["soz_tur"]()
ok("gecerli_sn dolunca söz düşer (gecti), teslim hiç çalışmaz, kayıt var", tr["gecti"] == 1 and c["n"] == 0 and N["soz_view"]()["kuyruk"] == 0 and [x["olay"] for x in satirlar(N)] == ["sunuldu", "gecti"], satirlar(N))
ok("kuyruk dosyası güncel (boş)", json.load(open(os.path.join(N["D"], "soz-kuyruk.json"))) == [])
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- teslim iptali ve hatası ---
N = kur("iptal"); N["AYAR"]["soz_aralik_dk"] = 0
r = N["soz_aday"]("eposta", "m", anahtar="i1", teslim=lambda: False)
ok("teslim False dönerse söz iptal: sayaç geri alınır, iptal kaydı", r["karar"] == "bastirildi" and r["neden"] == "teslim iptal" and N["soz_view"]()["sunulan"] == 0 and satirlar(N)[-1]["olay"] == "iptal")
def bozuk(): raise ValueError("x")
ok("teslim hata verirse kapı çökmez", N["soz_aday"]("eposta", "m", anahtar="i2", teslim=bozuk)["karar"] == "simdi")

# --- sonuç kaydı ---
N = kur("sonuc"); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=50); c, f = sayac()
a = N["soz_aday"]("gun_ici", "m", anahtar="r1 gizli", teslim=f); b = N["soz_aday"]("eposta", "m", anahtar="r2", teslim=f); k_ = N["soz_aday"]("kisisel_tarih", "m", anahtar="r3", teslim=f)
ok("sonuç: kimlikle kabul", N["soz_sonuc"](a["id"], "kabul")["ok"] and satirlar(N)[-1] == dict(satirlar(N)[-1], olay="sonuc", sonuc="kabul", otomatik=False, id=a["id"]))
ok("sonuç: ilk gerçek sonuç kazanır (ikinci işlem yazılmaz)", N["soz_sonuc"](a["id"], "ret")["ok"] is False and [x["sonuc"] for x in satirlar(N) if x["olay"] == "sonuc"] == ["kabul"])
ok("sonuç: anahtarla ertele", N["soz_sonuc"]("r2", "ertele")["ok"] and satirlar(N)[-1]["sonuc"] == "ertele" and satirlar(N)[-1]["id"] == b["id"])
ok("sonuç: 'kaynak:<ad>' o kaynağın sunulan sonuçsuz sözüne", N["soz_sonuc"]("kaynak:kisisel_tarih", "ret")["ok"] and satirlar(N)[-1]["id"] == k_["id"] and N["soz_sonuc"]("kaynak:kisisel_tarih", "ret")["ok"] is False)
ok("sonuç: bilinmeyen söz ve geçersiz sonuç hata vermez", N["soz_sonuc"]("yok", "kabul")["ok"] is False and N["soz_sonuc"](a["id"], "belki")["ok"] is False)
ok("sonuç kaydında anahtar özeti var, ham anahtar yok", "gizli" not in open(os.path.join(N["D"], "soz.jsonl"), encoding="utf-8").read())

# --- otomatik yoksay ---
N = kur("yoksay"); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=50); c, f = sayac()
y1 = N["soz_aday"]("gun_ici", "m", anahtar="y1", teslim=f); y2 = N["soz_aday"]("eposta", "m", anahtar="y2", teslim=f, ek={"yoksay_sn": 120}); N["soz_sonuc"](y2["id"], "kabul")
SAAT["t"] += 130; tr = N["soz_tur"]()
ok("kaynağın süresi (eposta ek yoksay_sn 120) dolmadan sonuç gelen yoksay olmaz", tr["yoksay"] == 0)
SAAT["t"] += 1800; tr = N["soz_tur"]()
ok("gun_ici 30 dk içinde işlem görmezse otomatik yoksay", tr["yoksay"] == 1 and satirlar(N)[-1] == dict(satirlar(N)[-1], olay="sonuc", sonuc="yoksay", otomatik=True, id=y1["id"]), satirlar(N)[-1])
ok("otomatik yoksaydan sonra gelen gerçek sonuç yine yazılır (yoksay ezilir)", N["soz_sonuc"](y1["id"], "kabul")["ok"] is True)
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- yeniden başlatma: tekrar önleme, sonuç çözümü, kuyruk varsayılan bildirimle ---
N = kur("yeniden"); N["AYAR"].update(soz_aralik_dk=0); c, f = sayac(); N["soz_aday"]("gun_ici", "bir", anahtar="d1", teslim=f)
N["sessiz_acik"] = lambda: True; N["soz_aday"]("eposta", "iki iki", anahtar="d2", teslim=f); N["soz_sonuc"]  # d2 kuyrukta
N2 = kur("yeniden")  # aynı klasör: yeni süreç
N2["AYAR"].update(soz_aralik_dk=0)
ok("yeniden başlatma: dün/az önce sunulan anahtar tekrarlanmaz (soz.jsonl'den)", N2["soz_aday"]("gun_ici", "bir", anahtar="d1", teslim=f)["neden"] == "tekrar")
ok("yeniden başlatma: kuyruk dosyasından yüklenir, aynı anahtar 'kuyrukta'", N2["soz_view"]()["kuyruk"] == 1 and N2["soz_aday"]("eposta", "iki iki", anahtar="d2", teslim=f)["neden"] == "kuyrukta")
ok("yeniden başlatma: sunulmuş söz kaynak ref ile sonuçlanır", N2["soz_sonuc"]("kaynak:gun_ici", "ret")["ok"])
SAAT["t"] += 60; tr = N2["soz_tur"]()
ok("kuyruktaki söz yeniden başlatmadan sonra varsayılan bildirimle teslim edilir", tr["teslim"] == 1 and N2["BIL"] and N2["BIL"][-1][1] == "E-posta" and N2["BIL"][-1][2] == "iki iki", N2["BIL"])
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

# --- olcum.py isabet ---
yol = os.path.join(KOD, ".claude", "skills", "suflor-olcum", "olcum.py")
sp = importlib.util.spec_from_file_location("olcum_t", yol); OL = importlib.util.module_from_spec(sp); sp.loader.exec_module(OL)
OL.CANLI = os.path.join(T, "isabet"); os.makedirs(OL.CANLI)
t0 = time.time() - 3600
def satir(olay, i, k, **ek): return json.dumps(dict({"olay": olay, "id": i, "kaynak": k, "a": "abc", "t": t0}, **ek)) + "\n"
open(os.path.join(OL.CANLI, "soz.jsonl"), "w").write("".join([
    satir("sunuldu", "1", "gun_ici", karar="simdi"), satir("sonuc", "1", "gun_ici", sonuc="kabul"),
    satir("sunuldu", "2", "gun_ici", karar="simdi"), satir("sonuc", "2", "gun_ici", sonuc="yoksay", otomatik=True),
    satir("sunuldu", "3", "gun_ici", karar="sonra"), satir("teslim", "3", "gun_ici"), satir("sonuc", "3", "gun_ici", sonuc="ret"),
    satir("sunuldu", "4", "eposta", karar="sonra"), satir("gecti", "4", "eposta"),
    satir("sunuldu", "5", "eposta", karar="bastirildi", neden="günlük bütçe"),
    satir("sunuldu", "6", "eposta", karar="simdi"), satir("sonuc", "6", "eposta", sonuc="yoksay", otomatik=True), satir("sonuc", "6", "eposta", sonuc="ertele"),
    satir("sunuldu", "7", "kisisel_tarih", karar="simdi"),
    json.dumps({"olay": "sunuldu", "id": "8", "kaynak": "eposta", "a": "x", "t": time.time() - 9 * 86400, "karar": "simdi"}) + "\n",  # 7 günden eski: sayılmaz
]))
o = OL.isabet_ozet(7); g = o["kaynak"]["gun_ici"]; e = o["kaynak"]["eposta"]
ok("isabet: gun_ici sunuldu 3 · kabul 1 · yoksay 1 · ret 1 · kabul oranı 0,33", (g["sunuldu"], g["kabul"], g["yoksay"], g["ret"], g["kabul_orani"]) == (3, 1, 1, 1, 0.33), g)
ok("isabet: eposta sunuldu 1 · bastırıldı 2 (süresi dolan + bütçe) · ertele 1 (ilk gerçek sonuç yoksay'ı ezer)", (e["sunuldu"], e["bastirildi"], e["ertele"], e["yoksay"]) == (1, 2, 1, 0), e)
ok("isabet: sonuçsuz sunulan 'bekleyen', 7 günden eski sayılmaz, toplam", o["kaynak"]["kisisel_tarih"]["bekleyen"] == 1 and o["toplam"]["sunuldu"] == 5 and o["toplam"]["bastirildi"] == 2 and o["soz"] == 7, o["toplam"])
ok("isabet_md tablo üretir", "| gun_ici | 3 |" in OL.isabet_md(o) and "kabul oranı" in OL.isabet_md(o))
ok("isabet: kayıt dosyası yoksa boş sonuç", (lambda: (setattr(OL, "CANLI", os.path.join(T, "yokyok")), OL.isabet_ozet(7)["soz"])[1])() == 0)

# --- 10 Kasım: bildirim başlığı — söz kapısından geçen asistanın adıyla, sistem uyarısı Suflor.me ---
import ast
_kaynak = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read(); _agac = ast.parse(_kaynak)
_fn = next(n for n in _agac.body if isinstance(n, ast.FunctionDef) and n.name == "bildirim")
# --- G1: teslimden önce doğrulama (dogrula) ---
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()
N = kur("dogrula"); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=50); c, f = sayac(); gecerli = {"v": True}; cagri = {"n": 0}
def dg():
    cagri["n"] += 1; return gecerli["v"]
r = N["soz_aday"]("eposta", "1 e-posta bekliyor", anahtar="d1", teslim=f, dogrula=dg)
ok("G1 şimdi: doğrulama geçerse teslim, doğrulama bir kez çağrıldı", r["karar"] == "simdi" and c["n"] == 1 and cagri["n"] == 1, r)
gecerli["v"] = False; r = N["soz_aday"]("eposta", "2 e-posta bekliyor", anahtar="d2", teslim=f, dogrula=dg)
ok("G1 şimdi: doğrulama False → teslim yok, bastırıldı: bayat", r["karar"] == "bastirildi" and r["neden"] == "bayat" and c["n"] == 1, r)
ok("G1 kayıt: bastirildi neden bayat satırı + /status bayat sayacı, sunulan sayılmaz", satirlar(N)[-1]["olay"] == "bastirildi" and satirlar(N)[-1]["neden"] == "bayat" and N["soz_view"]()["bayat"] == 1 and N["soz_view"]()["sunulan"] == 1, (satirlar(N)[-1], N["soz_view"]()))
def patla(): raise RuntimeError("x")
ok("G1: doğrulama hata verirse söz yine teslim edilir (sessizce yutulmaz)", N["soz_aday"]("eposta", "3", anahtar="d3", teslim=f, dogrula=patla)["karar"] == "simdi" and c["n"] == 2)
ok("G1: doğrulama None dönerse teslim", N["soz_aday"]("eposta", "4", anahtar="d4", teslim=f, dogrula=lambda: None)["karar"] == "simdi" and c["n"] == 3)
# kuyruk: sessiz modda bekler, teslim anında doğrulanır
ses = {"v": True}; N = kur("dogrula-kuyruk", sessiz_acik=lambda: ses["v"]); N["AYAR"].update(soz_aralik_dk=0, soz_gunluk_butce=50); c, f = sayac(); c2, f2 = sayac(); gecerli = {"v": True}
r1 = N["soz_aday"]("eposta", "a", anahtar="q1", teslim=f, dogrula=lambda: gecerli["v"]); r2 = N["soz_aday"]("toplanti_sonrasi", "b", anahtar="q2", teslim=f2)
ok("G1 kuyruk: iki söz sessiz modda bekler", r1["karar"] == "sonra" and r2["karar"] == "sonra" and N["soz_view"]()["kuyruk"] == 2)
ok("G1 kuyruk dosyası: yalnız doğrulamalı söz 'dogrula' işaretli (işlev yazılmaz)", [q.get("dogrula") for q in json.load(open(os.path.join(N["D"], "soz-kuyruk.json")))] == [True, None])
gecerli["v"] = False; ses["v"] = False; SAAT["t"] += 60; tr = N["soz_tur"]()
ok("G1 kuyruk: teslim anında bayatlayan düşer, ötekisi teslim edilir (bayat söz aralığı tüketmez)", tr["bayat"] == 1 and tr["teslim"] == 1 and c["n"] == 0 and c2["n"] == 1 and N["soz_view"]()["kuyruk"] == 0, tr)
ok("G1 kuyruk kaydı: bastirildi (bayat) satırı, teslim satırı yok", [(x["olay"], x.get("neden")) for x in satirlar(N) if x["kaynak"] == "eposta"] == [("sunuldu", "sessiz mod"), ("bastirildi", "bayat")], satirlar(N))
# yeniden başlatma: doğrulamalı söz eski metinle teslim edilmez
ses["v"] = True; N = kur("dogrula-yb", sessiz_acik=lambda: ses["v"]); N["AYAR"].update(soz_aralik_dk=0)
N["soz_aday"]("eposta", "eski metin", anahtar="y1", dogrula=lambda: True); N["soz_aday"]("gun_ici", "dogrulamasiz", anahtar="y2")
N2 = kur("dogrula-yb", sessiz_acik=lambda: False); N2["AYAR"].update(soz_aralik_dk=0); SAAT["t"] += 60; tr = N2["soz_tur"]()
ok("G1 yeniden başlatma: doğrulamalı söz kuyruğa alınmaz (bayat: yeniden başlatma), doğrulamasız varsayılan bildirimle gider", tr["teslim"] == 1 and [b[2] for b in N2["BIL"]] == ["dogrulamasiz"]
   and any(x["olay"] == "bastirildi" and x.get("neden") == "bayat: yeniden başlatma" for x in satirlar(N2)), (tr, N2["BIL"]))
N3 = kur("dogrula-yb"); ok("G1 yeniden başlatma: kuyruk dosyasında düşen söz kalmaz, bayat sayacı kayıttan geri yüklenir", N3["soz_view"]()["kuyruk"] == 0 and N3["soz_view"]()["bayat"] == 1, N3["soz_view"]())
SAAT["t"] = datetime.datetime(2026, 11, 11, 11, 0).timestamp()

def _gercek_bildirim(adi):  # relay.py'nin gerçek bildirim() işlevi, menü uygulaması "açık" gibi; STATE["bildirim"] çıktısı okunur
    ns = {"time": time, "AYAR": {}, "STATE": {"_menu_son": time.time()}, "kart_bildir": lambda: None, "print": lambda *a, **k: None, "os": os, "subprocess": None, "threading": threading}
    if adi: ns["asistan_ad"] = lambda: adi
    ns["_BILDIRIM_YEREL"] = threading.local()
    exec(compile(ast.Module([_fn], []), "relay-bildirim", "exec"), ns); return ns
def _kapi_gercek(adi):
    g = _gercek_bildirim(adi)
    N = kur("bas" + str(adi), bildirim=g["bildirim"], _BILDIRIM_YEREL=g["_BILDIRIM_YEREL"]); return N, g
N, g = _kapi_gercek("Marvin")
N["soz_aday"]("eposta", "2 yeni e-posta", anahtar="b1", oncelik=3)  # varsayılan teslim
ok("başlık: söz kapısı varsayılan teslimi asistanın adıyla, alt satır tür", g["STATE"]["bildirim"]["baslik"] == "Marvin" and g["STATE"]["bildirim"]["alt"] == "E-posta", g["STATE"].get("bildirim"))
N["soz_aday"]("gun_ici", "Cümle", anahtar="b2", oncelik=3, teslim=lambda: N["bildirim"]("Suflor.me", "Öneri", "Cümle"))  # kaynak koduna benzer: teslim işlevi doğrudan çağırır
ok("başlık: teslim işlevinin kendi bildirim çağrısı da asistanın adıyla", g["STATE"]["bildirim"]["baslik"] == "Marvin" and g["STATE"]["bildirim"]["alt"] == "Öneri")
N["soz_aday"]("sistem", "claude-giris", anahtar="b3", oncelik=3, kip="bildir", teslim=lambda: N["bildirim"]("Suflor.me", "Claude oturumu düştü", "x"))
ok("başlık: sistem kaynaklı söz Suflor.me kalır", g["STATE"]["bildirim"]["baslik"] == "Suflor.me" and g["STATE"]["bildirim"]["alt"] == "Claude oturumu düştü", g["STATE"].get("bildirim"))
g["bildirim"]("Suflor.me", "Güncelleme", "x")
ok("başlık: söz kapısı dışı doğrudan bildirim (sistem uyarısı) Suflor.me", g["STATE"]["bildirim"]["baslik"] == "Suflor.me")
ok("başlık: teslimden sonra bayrak sıfırlanır", getattr(g["_BILDIRIM_YEREL"], "asistan", False) is False)
N2, g2 = _kapi_gercek(None)
N2["soz_aday"]("gun_ici", "Cümle", anahtar="b4", oncelik=3)
ok("başlık: kişiliksiz kurulumda asistan adı çözülemezse Suflor", g2["STATE"]["bildirim"]["baslik"] == "Suflor", g2["STATE"].get("bildirim"))

shutil.rmtree(T, ignore_errors=True)
print("\nTÜM TESTLER GEÇTİ" if not HATA else f"\n{len(HATA)} test kaldı: {HATA}"); sys.exit(1 if HATA else 0)
