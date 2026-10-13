#!/usr/bin/env python3
# Anlık uyarılar (aktarici/anlik.py, Faz 6 #7–8): karşı satırda kullanıcının adı (ekli biçim) → /cards "anlik" (Adın geçti — kim) · aynı satırın
# düzeltmesi yeniden uyarmaz · adın içinde geçen sözcük ("Alinin" değil "alın" türü) uyarmaz · kullanıcının kendi satırı uyarmaz · kullanıcı 95 sn
# kesintisiz konuşunca bir kez "uzun konuşma" · araya ≥ 4 sözcüklük karşı satır girince sayaç sıfırlanır, kısa onay ("evet") sıfırlamaz ·
# /status'ta da var · ayar adin_gecti: false ve uzun_konusma_sn: 0 kapatır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/anlik.py      (kaldı → çıkış 1; ~15 sn)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8768
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
def kur(ek=None):
    T = tempfile.mkdtemp(prefix="suflor-an-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    ay = os.path.join(T, "ayar.json"); json.dump(dict({"alan": "Deneme", "ad": "Kerem S", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, **(ek or {})), open(ay, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def istek(yol, v=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K})
        return json.loads(urllib.request.urlopen(q, timeout=10).read())
    return r, T, istek
n = [0]
def satir(istek, kim, metin, kanal, t0, t1, id_=None):
    n[0] += 1
    istek("/ingest", {"meeting": {"title": "Anlık Deneme"}, "source": "whisper", "entries": [{"id": id_ or f"wh/{kanal}/{n[0]}", "speaker": kim, "time": "10:00:00",
          "text": metin, "kanal": kanal, "t0": t0, "t1": t1}]})
an = lambda istek: istek("/cards").get("anlik")

r, T, istek = kur()
try:
    t = time.time() - 100
    satir(istek, "Karşı taraf 1", "Bunu Kerem'in ekibi hazırlasın", "karsi", t, t + 2, "wh/karsi/ad1")
    a = an(istek) or {}
    bak("karşı satırda ad (ekli) → Adın geçti — kim", a.get("tur") == "ad" and "Karşı taraf 1" in a.get("metin", "") and "Kerem'in ekibi" in a.get("ayrinti", ""))
    i1 = a.get("id")
    bak("/status'ta da anlik", (istek("/status").get("anlik") or {}).get("id") == i1)
    satir(istek, "Karşı taraf 1", "Bunu Kerem'in ekibi hazırlasın lütfen", "karsi", t, t + 2, "wh/karsi/ad1")
    bak("aynı satırın düzeltmesi yeni uyarı vermez", (an(istek) or {}).get("id") == i1)
    satir(istek, "Karşı taraf 2", "Keremoğlu değil, kereste tarafında", "karsi", t + 3, t + 5)
    bak("adın içinde geçtiği başka sözcük uyarmaz", (an(istek) or {}).get("id") == i1)
    satir(istek, "Kerem S", "Kerem olarak ben söylüyorum", "ben", t + 6, t + 8)
    bak("kullanıcının kendi satırı uyarmaz", (an(istek) or {}).get("id") == i1)
    # uzun konuşma: 10–60 sn arası konuşma, kısa onay sayacı sıfırlamaz, sonra 4+ sözcük sıfırlar
    for k in range(6): satir(istek, "Kerem S", "bir iki üç dört beş altı", "ben", t + 10 + k * 10, t + 18 + k * 10)
    satir(istek, "Karşı taraf 1", "evet", "karsi", t + 60, t + 61)
    bak("60 sn: uzun konuşma uyarısı yok", (an(istek) or {}).get("tur") != "uzun")
    for k in range(4): satir(istek, "Kerem S", "devam ediyorum konuşmaya", "ben", t + 70 + k * 8, t + 77 + k * 8)
    a = an(istek) or {}
    bak("kısa onaya rağmen ~95 sn kesintisiz → uzun konuşma (bir kez)", a.get("tur") == "uzun" and "konuşuyorsun" in a.get("metin", ""))
    iu = a.get("id"); satir(istek, "Kerem S", "hâlâ devam", "ben", t + 96, t + 98)
    bak("ikinci uyarı yok", (an(istek) or {}).get("id") == iu)
    satir(istek, "Karşı taraf 1", "Peki şunu sorayım o zaman", "karsi", t + 99, t + 100)
    for k in range(3): satir(istek, "Kerem S", "yeni konu", "ben", t + 100 + k * 5, t + 104 + k * 5)
    bak("4+ sözcüklük karşı satır sayacı sıfırladı", (an(istek) or {}).get("id") == iu)
    bak("günlükte ANLIK satırları", open(os.path.join(T, "relay.log"), encoding="utf-8").read().count("ANLIK: ") == 2)
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)

r, T, istek = kur({"adin_gecti": False, "uzun_konusma_sn": 0})
try:
    t = time.time() - 100
    satir(istek, "Karşı taraf 1", "Kereme soralım", "karsi", t, t + 2)
    for k in range(12): satir(istek, "Kerem S", "konuşuyorum konuşuyorum", "ben", t + 3 + k * 8, t + 10 + k * 8)
    bak("ayarla kapalı: uyarı yok", an(istek) is None)
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("anlık: ✓ hepsi geçti" if not hata else f"anlık: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
