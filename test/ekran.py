#!/usr/bin/env python3
# v0.187.0 (5 Kasım): paylaşılan ekranın yazısı → toplantı oturumu (izle "EKRAN n") ve Konuş bağlamı. aktarici/ekran.py, metin-tani.swift --bolge,
# relay.py kanit() → kanit_isle, toplanti-claude.py izle değişince koştur:   PYTHONDONTWRITEBYTECODE=1 python3 test/ekran.py   (~30 sn)
# Bölüm 1 (süreç içi): özet kuralı, tekrar ayıklama ("KANIT k ile aynı"), Konuş bağlamı ve gizli toplantı.
# Bölüm 2 (uçtan uca): yalıtılmış aktarıcı + gerçek Apple Vision; yalnız bölge okunur (altyazı dışarıda), ekran.jsonl, izle'de EKRAN olayı, gizli toplantıda kanıt/EKRAN yok.
import base64, datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
T = tempfile.mkdtemp(prefix="ekran-")
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)

# --- Bölüm 1: süreç içi ------------------------------------------------------------------------------------------
YAZILAN = []; GIZLI = {"acik": False}; AKTIF = {"f": "2026-11-05-1000-Deneme.md"}
ns = {"os": os, "json": json, "re": re, "subprocess": subprocess, "time": time, "datetime": datetime, "LOCK": threading.RLock(), "BASE": T,
      "AYAR": {"uygulama": T}, "_t": lambda tr, en: tr, "gizli_acik": lambda: GIZLI["acik"], "aktif_dosya": lambda: AKTIF["f"],
      "write": lambda pairs: YAZILAN.extend(pairs)}
exec(compile(open(os.path.join(KOD, "aktarici", "ekran.py"), encoding="utf-8").read(), "ekran.py", "exec"), ns)
oz = ns["ekran_ozet"](["Çeyrek sunumu", "Ajanda", "x", "Müşteri: Deneme Yapı A.Ş.", "bu satır uzun bir açıklama metni " * 3, "Bütçe 1.250.000 TL", "Çeyrek sunumu"]
                      + [f"dolgu satırı numarasız {i} " * 2 for i in range(40)])
ok("özet ≤ 600 karakter", len(oz) <= 600)
ok("özette başlık, firma adı ve sayı var; tek harf ve tekrar yok", "Çeyrek sunumu" in oz and "Deneme Yapı A.Ş." in oz and "1.250.000" in oz and oz.count("Çeyrek sunumu") == 1 and " x " not in f" {oz} ")
ok("özet ekrandaki sırayı korur", oz.index("Çeyrek") < oz.index("Müşteri") < oz.index("Bütçe"))
md = os.path.join(T, AKTIF["f"]); kj = os.path.join(T, "kanit", AKTIF["f"][:-3], "ekran.jsonl")
kay = lambda n, o: ns["ekran_kaydet"](md, f"kanit/x/{n}.png", n, "10:0" + str(n), o)
kay(1, "Ajanda · Müşteri: Deneme Yapı A.Ş. · Bütçe 1.250.000 TL"); kay(2, "Ayarlar penceresi · Kaydet · İptal")
kay(3, "Ajanda · Müşteri: Deneme Yapı A.Ş. · Bütçe 1.250.000 TL"); kay(4, "Ajanda · Müşteri: Deneme Yapı A.Ş. · Bütçe 1.250.000 TL")
recs = [json.loads(t) for p, t in YAZILAN if p == kj]
ok("ekran.jsonl: 3 olay (1 yeni, 2 açılır pencere, 3 dönüş = 'KANIT 1 ile aynı'; 4 öncekiyle aynı → yok)",
   [r.get("n") for r in recs] == [1, 2, 3] and recs[2].get("ayni") == 1 and "ozet" not in recs[2] and recs[0]["ozet"].startswith("Ajanda"))
b = ns["ekran_baglam"]()
ok("Konuş bağlamı: son ekran (KANIT 4) özeti", "KANIT 4" in b and "Deneme Yapı A.Ş." in b)
GIZLI["acik"] = True; ok("gizli toplantıda Konuş bağlamına ekran girmez", ns["ekran_baglam"]() == ""); GIZLI["acik"] = False
AKTIF["f"] = None; ok("süren toplantı yokken bağlam yok", ns["ekran_baglam"]() == ""); AKTIF["f"] = "2026-11-05-1000-Deneme.md"
ns["EKRAN_SON"][AKTIF["f"]]["t"] -= 16 * 60; ok("15 dk'dan eski ekran bağlama girmez", ns["ekran_baglam"]() == "")
ok("bölge süzgeci: geçersiz/küçük bölge atılır", ns["_bolge_temiz"]({"x": 0.1, "y": 0.1, "w": 0.01, "h": 0.5}) is None and ns["_bolge_temiz"]({"x": "a"}) is None
   and ns["_bolge_temiz"]({"x": 0.2, "y": 0.1, "w": 0.9, "h": 0.5}) == {"x": 0.2, "y": 0.1, "w": 0.8, "h": 0.5})

# S212: görsel ağırlıklı işareti, görüntü yolu, tekrar, gizli toplantı
G = ns["ekran_gorsel"]
ok("görsel işareti: yazı yok / az yazı", G([]) == "yazı yok" and G(["Q3"]) == "yazı yok" and G(["Satış grafiği", "Q1 Q2 Q3"]) == "az yazı")
ok("görsel işareti: çok sayı", G(["Gelir %d" % (1000 + i) + " 2024 12,5 30" for i in range(8)]) == "çok sayı")
ok("görsel işareti: tablo", G([f"Bölge {c} adlı uzun satır metni 12 34 56" for c in "ABCDEF"] + ["Toplam açıklama metni burada devam eder"]) in ("tablo", "çok sayı"))
ok("görsel işareti: yazı ağırlıklı slayt işaretsiz", G(["Bu slaytta uzun bir açıklama paragrafı var ve sayı içermiyor sadece metin"] * 8) == "")
YAZILAN.clear(); ns["EKRAN_YAZILAN"].clear(); ns["EKRAN_SON"].clear()
ns["ekran_kaydet"](md, "kanit/x/7.png", 7, "10:07", "Satış grafiği · Q3", "az yazı")
ns["ekran_kaydet"](md, "kanit/x/8.png", 8, "10:08", "Satış grafiği · Q3", "az yazı")
ns["ekran_kaydet"](md, "kanit/x/9.png", 9, "10:09", "", "yazı yok"); ns["ekran_kaydet"](md, "kanit/x/10.png", 10, "10:10", "", "yazı yok")
ns["ekran_kaydet"](md, "kanit/x/11.png", 11, "10:11", "Slayt başlığı uzun metin", "")
r2 = [json.loads(x) for p_, x in YAZILAN if p_ == kj]
ok("görsel ekran kaydı: gorsel_neden + yol; tekrar ve boş tekrar yazılmaz", [r["n"] for r in r2] == [7, 9, 11] and r2[0]["gorsel_neden"] == "az yazı" and r2[1]["gorsel_neden"] == "yazı yok" and r2[0]["gorsel"] == "kanit/x/7.png" and "gorsel_neden" not in r2[2])
ns["EKRAN_SON"][os.path.basename(md)] = {"n": 9, "saat": "10:09", "t": time.time(), "ozet": "", "gorsel": "kanit/x/9.png", "gorsel_neden": "yazı yok"}
b = ns["ekran_baglam"](); ok("Konuş bağlamına görüntü yolu girer (görsel ağırlıklı)", os.path.join(T, "kanit/x/9.png") in b and "Read" in b)
ns["EKRAN_SON"][os.path.basename(md)]["gorsel_neden"] = ""; ok("yazı ağırlıklı ekranda yol yok", "kanit/x" not in ns["ekran_baglam"]())
GIZLI["acik"] = True; YAZILAN.clear(); ns["ekran_kaydet"](md, "kanit/x/12.png", 12, "10:12", "Gizli ekran", "az yazı")
ok("gizli toplantıda ekran.jsonl'e (görüntü yolu dahil) yazılmaz", not YAZILAN); GIZLI["acik"] = False
src = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read()
ok("izle: gorsel_neden varsa 'GÖRSEL AĞIRLIKLI' + Read talimatı", "GÖRSEL AĞIRLIKLI ({r['gorsel_neden']})" in src and "Read ile oku, en çok 2 cümle" in src)

# --- Bölüm 2: uçtan uca --------------------------------------------------------------------------------------------
if not shutil.which("swiftc"): print("atlandı (bölüm 2): swiftc yok")
else:
    PORT = bos_port(8792); canli = os.path.join(T, "canli"); os.makedirs(canli)
    ikili = os.path.join(T, "Suflor Metin.app", "Contents", "MacOS", "SuflorMetin"); os.makedirs(os.path.dirname(ikili))
    subprocess.run(["swiftc", "-O", "-o", ikili, os.path.join(KOD, "metin-tani.swift")], check=True, capture_output=True)
    # deneme görüntüsü: sol üstte "slayt" yazısı, sağ altta "altyazı" satırı (bölge dışında kalmalı). --deneme-resim metni (60,60)'tan yazar;
    # satır boşluklarıyla sağ alta itmek yerine iki görüntü birleştirilmez: ikinci satırı uzun boşlukla sağa iteriz.
    g1, g2 = os.path.join(T, "g1.png"), os.path.join(T, "g2.png")
    subprocess.run([ikili, "--deneme-resim", g1, "Müşteri Deneme Yapı\nBütçe 1.250.000 TL\n\n\n\n\n\n\nAltyazı konuşma satırı"], check=True)
    subprocess.run([ikili, "--deneme-resim", g2, "Ayarlar penceresi açık"], check=True)
    ust = {"x": 0, "y": 0, "w": 1, "h": 0.45}
    o = json.loads(subprocess.run([ikili, g1, "--bolge", "0,0,1,0.45"], capture_output=True, text=True).stdout)
    ok("metin-tani --bolge: yalnız bölgedeki yazı (altyazı satırı yok)", any("Bütçe" in s for s in o["satirlar"]) and not any("Altyazı" in s for s in o["satirlar"]))
    ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "ekran_toplu_sn": 0}, open(ay, "w"))  # kanit_metin yok (varsayılan); ekran_toplu_sn 0 = her EKRAN hemen (eski davranış; toplu: test/ekran-toplu.py)
    R = os.path.join(T, "kod"); os.makedirs(R)
    for f in ("relay.py", "manifest.json", "toplanti-claude.py", "yapi.py", "taahhut.py", "baglam.py"):
        if os.path.exists(os.path.join(KOD, f)): shutil.copy(os.path.join(KOD, f), R)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(R, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(R, "pano"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=R, env=env, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    iz = None
    try:
        for _ in range(50):
            if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
        def uc(yol, v=None): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K}), timeout=20).read())
        uc("/ingest", {"meeting": {"title": "Ekran toplantısı"}, "source": "transcript", "entries": [{"id": "e/1", "speaker": "Ayla K", "time": "10:00", "text": "Sunuma bakalım."}]})
        iz = subprocess.Popen([sys.executable, "-u", "toplanti-claude.py", "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "izle"], cwd=R, env=env,
                              stdout=open(os.path.join(T, "izle.log"), "w"), stderr=subprocess.STDOUT)
        log = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8").read()
        izl = lambda: open(os.path.join(T, "izle.log"), encoding="utf-8").read()
        def bekle(f, sn=40):
            t = time.time()
            while time.time() - t < sn:
                if f(): return True
                time.sleep(0.3)
            return False
        bekle(lambda: "İZLEME BAŞLADI" in izl() or "DOSYA:" in izl(), 30)
        kanit = lambda g, b=ust: uc("/kanit-masaustu", {"png": base64.b64encode(open(g, "rb").read()).decode(), "kaynak": "pano", **({"paylasim": {"olcek": 1, "bolge": b}} if b else {})})
        ok("kanıt 1 (bölgeli) kaydedildi", kanit(g1).get("ok"))
        ej = lambda: os.path.join(canli, "kanit", next(f for f in os.listdir(canli) if f.endswith(".md"))[:-3], "ekran.jsonl")
        ok("ekran.jsonl'de EKRAN 1 özeti (bölgedeki yazı; altyazı satırı yok)", bekle(lambda: os.path.exists(ej()) and "1.250.000" in open(ej()).read()) and "Altyazı" not in open(ej()).read())
        ok("izle'de EKRAN 1 olayı (özet + talimat)", bekle(lambda: re.search(r"^EKRAN 1 \(\d\d:\d\d:\d\d\): \".*1\.250\.000.*\" · paylaşılan ekranda", izl(), re.M) is not None))
        kanit(g2); bekle(lambda: "EKRAN 2" in izl(), 30)
        kanit(g1)
        ok("açılır pencere kapanıp dönünce: 'EKRAN 3 … KANIT 1 ile aynı yazı'", bekle(lambda: re.search(r"^EKRAN 3 \([\d:]+\): KANIT 1 ile aynı yazı", izl(), re.M) is not None))
        md_ = open(os.path.join(canli, next(f for f in os.listdir(canli) if f.endswith(".md")))).read()
        ok(".md'ye metin satırı yazılmadı (kanit_metin kapalı), .jsonl'e EKRAN girmedi",
           "KANIT 1 metni" not in md_ and "1.250.000" not in open(os.path.join(canli, next(f for f in os.listdir(canli) if f.endswith(".jsonl") and f.startswith("20")))).read())
        kanit(g2, None); time.sleep(4)
        ok("bölgesiz kanıt (menü uygulaması): EKRAN üretilmez", "EKRAN 4" not in izl() and "EKRAN 4" not in log())
        uc("/komut", {"tur": "gizli"}); time.sleep(0.5)
        g = kanit(g1); time.sleep(4)
        ok("gizli toplantıda kanıt (ve EKRAN) yok", g.get("gizli") and "KANIT 5" not in log() and "EKRAN 5" not in izl())
        ok("aktarıcıda ve izle'de hata yok", "Traceback" not in log() and "Traceback" not in izl())
    finally:
        for p in (iz, r):
            if p: p.terminate(); p.wait()
if HATA: print("izle/relay günlükleri:", T)
else: shutil.rmtree(T, ignore_errors=True)
print("ekran yazısı:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
