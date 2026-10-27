#!/usr/bin/env python3
# Faz A (S162, v0.146.0) — eklenti toplantıyı tanımasa da ses yardımcısı + takvim/Başlat ile toplantı tanınır, oturum açılmaz (kota harcamadan, Brifing.app gerekmez):
#  1) takvimde yakın toplantı yokken yerel ses "bekle" döner (toplantı sayılmaz)
#  2) takvimde ±15 dk içinde toplantı varken (bağlantısız da olsa) ses toplantı sayılır: "bekle" yok, toplantı dosyası açılır
#  3) yalnız mikrofon + takvim güvenilir değil: toplantı oturumu açılmaz, panoda "Toplantı algılandı — Claude'u başlat" onay kartı çıkar
#  4) karttaki Onayla → baslat çalışır (günlükte "öneri onaylandı"), kart kapanır; ikinci toplantıda Reddet → oturum açılmaz
#  5) heartbeat.json eklenti nabzı olmadan da zamanlayıcıyla yazılır
# aktarici/oto-toplanti.py, relay.py yerel_ses_al ya da heartbeat döngüsü değişince:  PYTHONDONTWRITEBYTECODE=1 python3 test/oto-mikrofon.py
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8783)
T = os.path.realpath(tempfile.mkdtemp(prefix="otomik-")); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
os.makedirs(os.path.join(T, "Suflor Ses.app"))  # yerel_ses_durum "yok" demesin (yalnız dizin denetlenir)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('#!/usr/bin/env python3\nimport json, sys\nif sys.argv[1:2] == ["auth"]: print(json.dumps({"loggedIn": True}))\n'); os.chmod(sahte, 0o755)
simdi = datetime.datetime.now().astimezone(); iso = lambda d: d.isoformat(timespec="seconds")
def takvim(olaylar): json.dump({"durum": "ok", "olaylar": olaylar}, open(os.path.join(T, "takvim.json"), "w"), ensure_ascii=False)
olay = lambda i, ad, b, s: {"id": i, "baslik": ad, "baslangic": iso(simdi + datetime.timedelta(minutes=b)), "bitis": iso(simdi + datetime.timedelta(minutes=s)),
                            "tum_gun": False, "takvim": "İş", "platform": None, "baglanti": None, "katilimcilar": ["Deniz Yıldız"], "kisi_sayisi": 2}
takvim([olay("e0", "Akşam görüşmesi", 240, 270)])
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje,
                                               "ortak": "/Users/Shared/Suflor", "claude": sahte, "konusma": False}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
LOG = os.path.join(T, "relay.log")
def ac(): return subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(LOG, "a"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTO="1", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0"))
r = ac()
U = f"http://127.0.0.1:{PORT}"; L = lambda: open(LOG, encoding="utf-8").read()
def istek(yol, g=None, anahtar="kart-anahtari.txt", origin=False):
    k = open(os.path.join(canli if anahtar.startswith("kart") else T, anahtar)).read().strip(); h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k}
    if origin: h["Origin"] = U
    q = urllib.request.Request(U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
    return json.load(urllib.request.urlopen(q, timeout=10))
def ses_nabiz(): return istek("/ses-yerel", {"nabiz": True, "durum": "dinliyor", "uygulama": "Safari", "surum": "0", "tepe": 500}, "ses-anahtari.txt")
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        try:
            if kosul(): return True
        except Exception: pass
        time.sleep(0.3)
    return False
try:
    ok("aktarıcı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")) and os.path.exists(os.path.join(T, "ses-anahtari.txt")), 20))
    time.sleep(1.5)
    # 5) heartbeat eklenti nabzı olmadan da yazılır
    hb = os.path.join(canli, "heartbeat.json"); m0 = os.path.getmtime(hb) if os.path.exists(hb) else 0
    ok("heartbeat.json zamanlayıcıyla yazılır (eklenti yok)", bekle(lambda: os.path.exists(hb) and os.path.getmtime(hb) > m0 + 1.5, 12))
    ses_nabiz()
    # 1) yakın toplantı yok
    yan = istek("/ses-yerel", {"kanal": "karsi", "pcm": ""}, "ses-anahtari.txt")
    ok(f"takvimde yakın toplantı yokken ses işlenmez ({yan})", yan.get("bekle") is True)
    # 2-3) takvimde şimdi başlayan toplantı
    r.terminate(); r.wait(8); takvim([olay("e1", "Deniz ile proje", -3, 27)]); r = ac()  # takvim açılışta okunur
    ok("aktarıcı yeniden açıldı", bekle(lambda: os.path.exists(os.path.join(T, "ses-anahtari.txt")) and "çalışıyor" in L(), 20)); time.sleep(1.5)
    for _ in range(6): ses_nabiz(); time.sleep(0.5)
    ok("toplantı tanındı (mikrofon + takvim)", bekle(lambda: "OTO: toplantı tanındı — Deniz ile proje" in L(), 15))
    yan = istek("/ses-yerel", {"kanal": "karsi", "pcm": ""}, "ses-anahtari.txt")
    ok(f"eklenti tanımasa da ses toplantı sayılır ({str(yan)[:60]})", not yan.get("bekle"))
    ok("oturum açılmadı: güvenilir sinyal yok", bekle(lambda: "güvenilir sinyal yok" in L(), 8) and "toplantı oturumu açıldı" not in L())
    def kartlar(): return [c for c in istek("/cards").get("cards", []) if c.get("onay")]
    ok("panoda 'Toplantı algılandı' onay kartı", bekle(lambda: any("Toplantı algılandı" in c["text"] for c in kartlar()), 8))
    # 4) Onayla → baslat
    c = next(c for c in kartlar() if "Toplantı algılandı" in c["text"])
    ok("kart onaylandı", istek("/card-ack", {"id": c["id"], "status": "onaylandi"}, origin=True).get("ok") is True)
    ok("Onayla → baslat çalıştı", bekle(lambda: "OTO: öneri onaylandı — toplantı oturumu açıldı" in L() or "BAŞLAT: Deniz ile proje" in L(), 10))
    ok("kart kapandı", not any("Toplantı algılandı" in c["text"] for c in kartlar()))
    ok("aktarıcıda hata yok", "Traceback" not in L())
finally:
    r.terminate()
    try: r.wait(5)
    except Exception: r.kill()
    shutil.rmtree(T, ignore_errors=True)
print("oto-mikrofon: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
