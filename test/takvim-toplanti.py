#!/usr/bin/env python3
# v0.166.0 — panodaki takvimden toplantı oluşturma: POST /takvim-toplanti (aktarici/talimat.py takvim_toplanti). Anahtar/köken, önizleme (davetli çözümü), girdi sınırları,
# URL'de başlık/saat/davetli, deneme kipinde açma (SUFLOR_TEST_BASLAT). Kota yok, Whisper yok (~5 sn):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/takvim-toplanti.py
import datetime as dt, json, os, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse
EP = lambda k, a: k + chr(64) + a  # adres kaynakta yazılmaz (açık depo taraması)
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8788); HATA = []
def ok(ad, k, ayr=None):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad); ayr is not None and print("   ", ayr)
T = tempfile.mkdtemp(prefix="takvim-toplanti-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
s0 = dt.datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "u1", "baslik": "Eski toplantı", "baslangic": (s0 + dt.timedelta(days=1)).isoformat(), "bitis": (s0 + dt.timedelta(days=1, hours=1)).isoformat(), "tum_gun": False,
           "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayşe Demir"], "kisi_sayisi": 2, "kisiler": [{"ad": "Ayşe Demir", "eposta": EP("ayse.demir", "ornek.test")}]}]}, open(os.path.join(T, "takvim.json"), "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); ORG = f"http://127.0.0.1:{PORT}"
    def post(v, anahtar=True, origin=True):
        h = {"Content-Type": "application/json"}
        if anahtar: h["X-Suflor-Anahtar"] = K
        if origin: h["Origin"] = ORG
        try: return 200, json.loads(urllib.request.urlopen(urllib.request.Request(ORG + "/takvim-toplanti", data=json.dumps(v).encode(), method="POST", headers=h), timeout=10).read())
        except urllib.error.HTTPError as e: return e.code, {}
    gel = (dt.datetime.now() + dt.timedelta(days=2)).replace(hour=14, minute=30, second=0, microsecond=0); Z = gel.strftime("%Y-%m-%dT%H:%M")
    ok("anahtarsız 401", post({"baslik": "x", "zaman": Z}, anahtar=False)[0] == 401)
    ok("anahtarlı ama panosuz (Origin yok) 403", post({"baslik": "x", "zaman": Z}, origin=False)[0] == 403)
    k, o = post({"onizle": True, "baslik": "Bütçe", "zaman": Z, "dk": 45, "davetli": ["Ayşe", "Bilinmeyen Kişi", EP("ali", "firma.test")]})
    d = {x["ad"]: x["eposta"] for x in o.get("davetli", [])}
    ok("önizleme: kayıtlı ad çözülür, bilinmeyen adresi yok, e-posta aynen", k == 200 and d.get("Ayşe") == EP("ayse.demir", "ornek.test") and d.get("Bilinmeyen Kişi") is None and "Bilinmeyen Kişi" in d and d.get(EP("ali", "firma.test")) == EP("ali", "firma.test"), o)
    u = urllib.parse.unquote(o.get("url", ""))
    ok("önizleme URL'si: başlık, başlangıç–bitiş (45 dk), davetli adresleri", "Bütçe" in u and gel.strftime("%Y%m%dT%H%M00") + "/" + (gel + dt.timedelta(minutes=45)).strftime("%Y%m%dT%H%M00") in u
       and EP("ayse.demir", "ornek.test") in u and EP("ali", "firma.test") in u and "Bilinmeyen" in u, u)
    k, o = post({"onizle": True, "zaman": Z, "davetli": []})
    ok("önizleme başlıksız çalışır, geçmiş değil", k == 200 and o.get("ok") and o.get("gecmis") is False and o.get("davetli") == [])
    ok("geçmiş saat önizlemede işaretli", post({"onizle": True, "zaman": "2020-01-01T10:00"})[1].get("gecmis") is True)
    kot = [("zaman biçimi", {"baslik": "x", "zaman": "yarın 10"}), ("geçersiz tarih", {"baslik": "x", "zaman": "2026-13-45T10:00"}), ("zaman yok", {"baslik": "x"}),
           ("süre 4", {"baslik": "x", "zaman": Z, "dk": 4}), ("süre 481", {"baslik": "x", "zaman": Z, "dk": 481}), ("süre metin", {"baslik": "x", "zaman": Z, "dk": "30"}),
           ("başlık 301", {"baslik": "x" * 301, "zaman": Z}), ("davetli 21", {"baslik": "x", "zaman": Z, "davetli": [f"k{i}" for i in range(21)]}), ("davetli liste değil", {"baslik": "x", "zaman": Z, "davetli": "ali"}),
           ("davetli öğesi sayı", {"baslik": "x", "zaman": Z, "davetli": [5]}), ("başlıksız oluştur", {"zaman": Z}), ("geçmiş saat", {"baslik": "x", "zaman": "2020-01-01T10:00"})]
    for ad, v in kot:
        k, o = post(v); ok(f"reddedilir: {ad}", k == 200 and o.get("ok") is False and o.get("err"), o)
    ok("sınırda geçerli: 300 karakter başlık, 20 davetli, 5 ve 480 dk", all(post({"onizle": True, "baslik": "x" * 300, "zaman": Z, "dk": dk, "davetli": [f"k{i}" for i in range(20)]})[1].get("ok") for dk in (5, 480)))
    # oluşturma: ac=false (Chrome panosu) sayfayı açmaz, URL verir; ac=true (Mac penceresi) deneme kipinde açar
    log = lambda: open(os.path.join(T, "relay.log"), errors="replace").read()
    k, o = post({"baslik": "Planlama", "zaman": Z, "dk": 60, "davetli": ["Ayşe"], "ac": False}); time.sleep(0.3)
    ok("ac=false: URL döner, aktarıcı sayfayı açmaz", o.get("ok") and o.get("acildi") is False and "Planlama" in urllib.parse.unquote(o.get("url", "")) and "toplantı sayfası" not in log(), o)
    k, o = post({"baslik": "Planlama", "zaman": Z, "dk": 60, "davetli": ["Ayşe"], "ac": True}); time.sleep(0.5)
    ok("ac=true: deneme kipinde sayfa açıldı (günlükte URL: başlık, saat, davetli)", o.get("ok") and o.get("acildi") and "TALİMAT (deneme): toplantı sayfası" in log() and "Planlama" in urllib.parse.unquote(log())
       and EP("ayse.demir", "ornek.test") in urllib.parse.unquote(log()), o)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); shutil.rmtree(T, ignore_errors=True)
print("takvim toplantı:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
