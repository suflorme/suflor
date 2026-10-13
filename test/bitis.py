#!/usr/bin/env python3
# Toplantı bitişi (v0.27.2): aktarıcı bitişi kendisi algılar (/status toplanti_bitti), izle "TOPLANTI BİTTİ" olayını bir kez verir. Deneme kipinde
# (SUFLOR_TEST_HIZLI) toplantı sinyali penceresi 6 sn, satırsız bekleme 8 sn. Senaryolar: eklenti sinyali kopar ama toplantı uygulaması mikrofonu
# tutuyor (ses yardımcısı "dinliyor") → bitmez · yardımcı "bekliyor" (mikrofon bırakıldı) → bitti · yeniden katılınca sıfırlanır · yardımcı yokken
# 8 sn satırsız → bitti (yedek kural) · izle olayı bir kez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bitis.py      (kaldı → çıkış 1; ~60 sn)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8769
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
def kur(yardimci):
    T = tempfile.mkdtemp(prefix="suflor-bt-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
    if yardimci: os.makedirs(os.path.join(T, "Suflor Ses.app"))
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1"))
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    SK = open(os.path.join(T, "ses-anahtari.txt")).read().strip() if yardimci else ""
    def post(yol, v, k=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": k or K})
        return json.loads(urllib.request.urlopen(q, timeout=10).read())
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    nabiz = lambda d, tepe=0, uyg="Chrome": post("/ses-yerel", {"nabiz": True, "durum": d, "tepe": tepe, "uygulama": uyg, "surum": "t", "kurma": 0}, SK)
    return T, canli, r, post, st, nabiz
M = {"title": "Bitiş Deneme"}
T, canli, r, post, st, nabiz = kur(True)
iz = None
try:
    post("/ping", {"call": True, "panel": True, "meeting": M}); nabiz("dinliyor")
    post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Ayşe", "time": "10:00", "text": "merhaba"}]})
    md = st()["file"]
    iz = subprocess.Popen([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "izle", "--aralik", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    for _ in range(9): time.sleep(1); nabiz("dinliyor"); post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": f"a/{_+2}", "speaker": "Ayşe", "time": "10:00", "text": f"satır {_}"}]})
    bak("sinyal koptu (9 sn ping yok) ama uygulama mikrofonu tutuyor: bitmedi", not st().get("toplanti_bitti"))
    nabiz("bekliyor"); time.sleep(2.5)
    tb = st().get("toplanti_bitti") or {}
    bak(f"mikrofon bırakıldı: bitti ({tb.get('neden')})", tb.get("file") == md and "mikrofonu bıraktı" in (tb.get("neden") or ""))
    time.sleep(3)
    # izle bitişten sonra yeniden başlarsa eski bitişi yeni olay gibi vermez (13 Ekim deneme 8)
    iz2 = subprocess.Popen([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "izle", "--aralik", "1"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    time.sleep(4); iz2.terminate(); o2 = iz2.communicate(timeout=10)[0]
    bak("yeniden başlayan izle eski bitişi olay olarak vermez", "TOPLANTI BİTTİ" not in o2 and "bitti saymıştı" in o2)
    post("/ping", {"call": True, "panel": True, "meeting": M}); nabiz("dinliyor"); time.sleep(1.5)
    bak("yeniden katıldı: sıfırlandı", not st().get("toplanti_bitti"))
    for _ in range(9): time.sleep(1); nabiz("bekliyor")
    tb2 = st().get("toplanti_bitti") or {}
    bak("ikinci kez bitti", tb2.get("file") == md)
finally:
    time.sleep(3)
    if iz: iz.terminate(); out = iz.communicate(timeout=10)[0]
    else: out = ""
    r.terminate(); r.wait(5)
olay = [l for l in out.splitlines() if "TOPLANTI BİTTİ" in l]
bak(f"izle: TOPLANTI BİTTİ olayı ({len(olay)} kez; ilk bitiş + yeniden katılıştan sonraki)", len(olay) == 2 and "mikrofonu bıraktı" in olay[0])
shutil.rmtree(T, ignore_errors=True)
# 13 Ekim deneme 8: eklenti sustu, satır gelmiyor ama toplantı uygulaması ses çıkarıyor → bitmez; ses kesilince "satır yok" ile biter.
# Masaüstü uygulaması toplantı dışı bildirse de (hiç toplantıda değildi) neden "masaüstü penceresi kapandı" yazılmaz.
T, canli, r, post, st, nabiz = kur(True)
try:
    post("/masaustu", {"uygulama": "Teams", "toplantida": False})
    post("/ping", {"call": True, "panel": True, "meeting": M}); nabiz("dinliyor", 2000)
    post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "c/1", "speaker": "Ayşe", "time": "10:00", "text": "merhaba"}]})
    for _ in range(14): time.sleep(1); nabiz("dinliyor", 2000); post("/masaustu", {"uygulama": "Teams", "toplantida": False})
    bak("eklenti sustu, satır yok ama toplantı sesi akıyor: bitmedi", not st().get("toplanti_bitti"))
    for _ in range(12): time.sleep(1); nabiz("dinliyor", 0); post("/masaustu", {"uygulama": "Teams", "toplantida": False})
    tb = st().get("toplanti_bitti") or {}
    bak(f"ses de kesildi: bitti, neden masaüstü penceresi değil ({tb.get('neden')})", tb.get("neden") and "masaüstü" not in tb["neden"])
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
# masaüstü: "Ayrıl" görünmüyor ama Teams sesi sürüyor → toplantıda sayılır; ses kesilince (4 sn) toplantı dışı (deneme 8: 78 sn boşluk)
T, canli, r, post, st, nabiz = kur(True)
try:
    post("/masaustu", {"uygulama": "Teams", "toplantida": True, "baslik": "Bitiş Deneme | Microsoft Teams"}); nabiz("dinliyor", 2000, "Teams")
    post("/masaustu", {"uygulama": "Teams", "toplantida": False}); time.sleep(1)
    for _ in range(4): nabiz("dinliyor", 2000, "Teams"); y = post("/masaustu", {"uygulama": "Teams", "toplantida": False}); time.sleep(1)
    bak("tutma sırasında yanıtta tut (menü uygulaması mikrofonu ve kanıtı sürdürür)", (y or {}).get("tut") is True)
    m = st().get("masaustu") or {}
    bak("Ayrıl yok, Teams sesi sürüyor: toplantıda sayıldı", m.get("toplantida") is True and "toplantı sesi sürüyor" in open(os.path.join(T, "relay.log")).read())
    for _ in range(6): nabiz("dinliyor", 0, "Teams"); post("/masaustu", {"uygulama": "Teams", "toplantida": False}); time.sleep(1)
    bak("Teams sesi kesildi: toplantı dışı, tut yok", (st().get("masaustu") or {}).get("toplantida") is False
        and post("/masaustu", {"uygulama": "Teams", "toplantida": False}).get("tut") is False)
    post("/masaustu", {"uygulama": "Teams", "toplantida": True, "baslik": "Bitiş Deneme | Microsoft Teams"}); nabiz("bekliyor")
    post("/masaustu", {"uygulama": "Teams", "toplantida": False}); time.sleep(0.5)
    bak("ses yardımcısı dinlemiyorsa tutulmaz", (st().get("masaustu") or {}).get("toplantida") is False)
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
# masaüstü toplantı penceresi gerçekten kapanınca neden doğru yazılır
T, canli, r, post, st, nabiz = kur(True)
try:
    post("/masaustu", {"uygulama": "Teams", "toplantida": True, "baslik": "Bitiş Deneme | Microsoft Teams"}); nabiz("dinliyor")
    post("/ingest", {"meeting": {"title": "Bitiş Deneme"}, "source": "transcript", "entries": [{"id": "d/1", "speaker": "Ayşe", "time": "10:00", "text": "merhaba"}]})
    post("/masaustu", {"uygulama": "Teams", "toplantida": False}); nabiz("bekliyor")
    for _ in range(10): time.sleep(1); nabiz("bekliyor"); post("/masaustu", {"uygulama": "Teams", "toplantida": False})
    tb = st().get("toplanti_bitti") or {}
    bak(f"masaüstü penceresi kapandı: neden doğru ({tb.get('neden')})", "masaüstü toplantı penceresi kapandı" == tb.get("neden"))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
T, canli, r, post, st, nabiz = kur(False)
try:
    post("/ping", {"call": True, "panel": True, "meeting": M})
    post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "b/1", "speaker": "Ayşe", "time": "10:00", "text": "merhaba"}]})
    time.sleep(15); tb = st().get("toplanti_bitti") or {}
    bak(f"yardımcı yokken yedek kural: satırsız → bitti ({tb.get('neden')})", "satır yok" in (tb.get("neden") or ""))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("bitiş: ✓ hepsi geçti" if not hata else f"bitiş: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
