#!/usr/bin/env python3
# 6 Kasım: EKRAN olaylarının toplu gönderimi (toplanti-claude.py izle: ekran_birlestir/ekran_ek, ayar ekran_toplu_sn, varsayılan 45; 0 = eski davranış).
# Değişince koştur:   PYTHONDONTWRITEBYTECODE=1 python3 test/ekran-toplu.py   (~40 sn; Swift/Vision gerekmez, ekran.jsonl doğrudan yazılır)
# Bölüm 1: saf birleştirme (en son tam, aradakiler kısa, geri dönüş katlama). Bölüm 2: yalıtılmış aktarıcı + izle — ilk EKRAN hemen, aradakiler birikir,
# süre dolunca tek olay, başka olay (soru) yanında gider, süre 0 = eski, toplantı bitince birikim kaybolmaz.
import ast, datetime, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []; T = tempfile.mkdtemp(prefix="ekran-toplu-")
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)

# --- Bölüm 1 -----------------------------------------------------------------------------------------------------
src = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read(); ag = {"ekran_toplu_sn": "x"}
ns = {"os": os, "AYAR": ag}
for n in ast.parse(src).body:
    if isinstance(n, ast.FunctionDef) and n.name in ("ekran_toplu_sn", "ekran_ilk_satir", "ekran_birlestir"): exec(compile(ast.Module([n], []), "tc", "exec"), ns)
ok("ekran_toplu_sn: geçersiz → 45", ns["ekran_toplu_sn"]() == 45.0); ag["ekran_toplu_sn"] = 0; ok("ekran_toplu_sn: 0 → 0", ns["ekran_toplu_sn"]() == 0.0); ag["ekran_toplu_sn"] = 30; ok("ekran_toplu_sn: 30", ns["ekran_toplu_sn"]() == 30.0)
R = lambda n, o=None, **k: {"n": n, "saat": f"10:0{n}", "gorsel": f"kanit/x/{n}.png", **({"ozet": o} if o else {}), **k}
oz = {1: "Ajanda · Bütçe 1.250.000 TL", 2: "Ayarlar penceresi · Kaydet", 3: "Satış raporu · Q3 · 14 müşteri", 4: "Ajanda · Bütçe 1.250.000 TL"}
b = ns["ekran_birlestir"]([R(2, oz[2]), R(3, oz[3]), R(4, ayni=1), R(5, ayni=1), R(6, "Son slayt · Teşekkürler")], oz, "/d")
ok("en son ekran tam özetle başta", b.startswith('EKRAN 6 (10:06): "Son slayt · Teşekkürler"') and "/d/kanit/x/6.png" in b)
ok("aradakiler kısa (yalnız ilk satır), tam özet tekrar etmez", 'EKRAN 2 (10:02) "Ayarlar penceresi"' in b and 'EKRAN 3 (10:03) "Satış raporu"' in b and "Q3" not in b and "Kaydet" not in b)
ok("geri dönüşler tek satırda katlanır (KANIT 1 (2×))", b.count("KANIT 1") == 1 and "KANIT 1 (2×)" in b)
ok("toplu sayısı yazılır", "5 ekran değişti" in b)
b2 = ns["ekran_birlestir"]([R(2, oz[2]), R(4, ayni=1)], oz, "/d")
ok("son kayıt geri dönüşse önceki özet yeniden verilir", 'EKRAN 4 (10:04): KANIT 1 ile aynı yazı' in b2 and "Bütçe 1.250.000" in b2 and 'EKRAN 2 (10:02) "Ayarlar penceresi"' in b2)
b3 = ns["ekran_birlestir"]([R(2, oz[2], gorsel_neden="tablo")], oz, "/d")
ok("görsel ağırlıklı ipucu korunur", "GÖRSEL AĞIRLIKLI (tablo)" in b3 and ns["ekran_birlestir"]([], oz, "/d") == "")

# --- Bölüm 2 -----------------------------------------------------------------------------------------------------
def kos(toplu, sen):
    PORT = bos_port(8791); canli = os.path.join(T, f"canli{toplu}"); os.makedirs(canli)
    ay = os.path.join(T, f"ayar{toplu}.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "ekran_toplu_sn": toplu}, open(ay, "w"))
    Rk = os.path.join(T, f"kod{toplu}"); os.makedirs(Rk)
    for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "yapi.py", "baglam.py"):
        if os.path.exists(os.path.join(KOD, f)): shutil.copy(os.path.join(KOD, f), Rk)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(Rk, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(Rk, "pano"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=Rk, env=env, stdout=open(os.path.join(T, f"relay{toplu}.log"), "w"), stderr=subprocess.STDOUT); iz = None
    try:
        for _ in range(50):
            if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
        uc = lambda yol, v=None: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K}), timeout=20).read())
        uc("/ingest", {"meeting": {"title": "Ekran toplu"}, "source": "transcript", "entries": [{"id": "e/1", "speaker": "Ayla K", "time": "10:00", "text": "Sunuma bakalım."}]})
        iz = subprocess.Popen([sys.executable, "-u", "toplanti-claude.py", "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "izle"], cwd=Rk, env=env, stdout=open(os.path.join(T, f"izle{toplu}.log"), "w"), stderr=subprocess.STDOUT)
        izl = lambda: open(os.path.join(T, f"izle{toplu}.log"), encoding="utf-8").read()
        def bekle(f, sn=30):
            t = time.time()
            while time.time() - t < sn:
                if f(): return True
                time.sleep(0.2)
            return False
        bekle(lambda: "DOSYA:" in izl(), 30)
        md = next(f for f in os.listdir(canli) if f.endswith(".md")); kj = os.path.join(canli, "kanit", md[:-3], "ekran.jsonl"); os.makedirs(os.path.dirname(kj), exist_ok=True)
        def yaz(n, o=None, ayni=None):
            with open(kj, "a", encoding="utf-8") as f: f.write(json.dumps({"at": datetime.datetime.now().isoformat(timespec="seconds"), "n": n, "saat": f"10:0{n}", "gorsel": f"kanit/x/{n}.png", **({"ayni": ayni} if ayni else {"ozet": o})}, ensure_ascii=False) + "\n")
        say = lambda: len(re.findall(r"^EKRAN \d+ \(", izl(), re.M))
        sen(uc, yaz, izl, bekle, say, md, canli)
        ok(f"[{toplu}] izle'de hata yok", "Traceback" not in izl())
    finally:
        for p in (iz, r):
            if p: p.terminate(); p.wait()

def toplu3(uc, yaz, izl, bekle, say, md, canli):
    yaz(1, "Ajanda · Bütçe 1.250.000 TL")
    ok("ilk EKRAN beklemeden gider (talimatla)", bekle(lambda: re.search(r'^EKRAN 1 \([^)]*\): ".*1\.250\.000.*" · paylaşılan ekranda', izl(), re.M) is not None, 10))
    yaz(2, "Ayarlar penceresi · Kaydet"); yaz(3, "Satış raporu · Q3 · 14 müşteri"); yaz(4, ayni=1); yaz(5, "Plan slaytı · Teslim 15 Kasım")
    time.sleep(1.5)
    ok("süre dolmadan aradaki EKRAN'lar gelmez", say() == 1)
    ok("süre dolunca tek olayda birleşik gelir", bekle(lambda: "EKRAN 5 (10:05): \"Plan slaytı" in izl(), 10) and say() == 2)
    t = [l for l in izl().splitlines() if l.startswith("EKRAN 5 ")][0]
    ok("birleşik olay: ara görülenler + geri dönüş + toplu sayısı", "ara görülenler" in t and 'EKRAN 2 (10:02) "Ayarlar penceresi"' in t and "KANIT 1 (1×)" in t and "4 ekran değişti" in t and "Q3" not in t)
    # başka olay (soru) varken: ekran onun yanında gider, ek uyanma yok
    yaz(6, "Rakip analizi · Pazar payı %12"); yaz(7, "Yol haritası · Q1")
    time.sleep(0.6); onceki = say()
    uc("/girdi", {"text": "? şu an hangi slayttayız", "soru": True})
    ok("soru gelince bekleyen ekran onun yanında gider", bekle(lambda: "EKRAN 7 (10:07)" in izl(), 8) and say() == onceki + 1)
    s = izl(); i7 = s.index("EKRAN 7 (10:07)"); ig = s.rfind("GİRDİ", 0, len(s)) if "GİRDİ" in s else s.rfind("SORU")
    ok("soru ve ekran aynı çıktı bloğunda (soru ekrandan önce)", 0 <= ig < i7 and s.count("EKRAN 7 (10:07)") == 1)
    time.sleep(4.5)
    ok("birikim sıfırlandı: süre dolunca yinelenmez", izl().count("EKRAN 7 (10:07)") == 1 and say() == onceki + 1)
    # toplantı biterken birikim kaybolmaz
    yaz(8, "Kapanış · Sorular"); yaz(9, "Teşekkürler slaytı")
    time.sleep(0.5); uc("/toplanti", {"islem": "bitir"})
    ok("toplantı bitince biriken ekran gönderilir (bitti olayından önce ya da süreyle)", bekle(lambda: "EKRAN 9 (10:09)" in izl(), 12))

def sifir(uc, yaz, izl, bekle, say, md, canli):
    yaz(1, "Ajanda · Bütçe 1.250.000 TL"); yaz(2, "Ayarlar penceresi · Kaydet"); yaz(3, ayni=1)
    ok("0 = eski davranış: her EKRAN hemen, ayrı olay", bekle(lambda: re.search(r"^EKRAN 3 \([^)]*\): KANIT 1 ile aynı yazı", izl(), re.M) is not None, 10) and say() == 3 and "toplu:" not in izl())

kos(3, toplu3); kos(0, sifir)
if HATA: print("günlükler:", T)
else: shutil.rmtree(T, ignore_errors=True)
print("ekran toplu:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
