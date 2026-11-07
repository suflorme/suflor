#!/usr/bin/env python3
# Toplantı sonrası proaktif hatırlatma (5 Kasım; aktarici/toplanti-sonrasi.py): özet hazır + toplanti_sonrasi_hatirlat_dk sonra yapı dosyasından açık uçlar
# (tarihsiz/sahipsiz iş, teyit bekleyen karar, açık soru) → bildirim + /status proaktif (panoda Bugün'de "Bakalım") + isteğe bağlı sesli söyleme.
# Kurgu veri (gerçek kişi yok). Yalıtılmış aktarıcı, gerçek claude çağrılmaz (claude yolu yok), canlı aktarıcıya dokunulmaz. Süre 0,03 dk (~2 sn).
#   Beklenen: bildirim + durum · bir kez · gizli/deneme/yeni toplantı/Kararlar'a bakılmış/açık uç yok/ayar 0'da atlanır · Bakalım asistana gider · sesli yalnız ayarla.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti-sonrasi.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="tsonrasi-"); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
proje = os.path.join(T, "proje"); os.makedirs(proje)
class Uc:
    def __init__(s, ad, **ayar):
        s.port = bos_port(8792); s.d = os.path.join(T, ad); os.makedirs(s.d); s.log = os.path.join(T, ad + ".log")
        yol = os.path.join(T, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Deniz T", "port": s.port, "uygulama": T, "proje": proje, "ortak": os.path.join(T, "yok"), "claude": "/yok/claude", "konus_on_ac": False,
                        "pocket_python": "/yok/python", "pocket_hf": "/yok"}, **ayar), open(yol, "w"))
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=T, stdout=open(s.log, "w"), stderr=subprocess.STDOUT,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"))
        for _ in range(80):
            if os.path.exists(os.path.join(s.d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); s.h = {"X-Suflor-Anahtar": open(os.path.join(s.d, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{s.port}"}
    def post(s, yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=20).read())
    def status(s): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}/status", headers=s.h), timeout=10).read())
    def metin(s): return open(s.log, encoding="utf-8").read()
    def bekle(s, f, sn=8):
        t0 = time.time()
        while time.time() - t0 < sn:
            if f(): return True
            time.sleep(0.2)
        return False
    def son(s, ad, baslik, ogeler, **ek):  # özet hazır: yapı dosyasıyla
        yol = os.path.join(T, ad + ".md"); open(yol, "w").write("# özet\n")
        return s.post("/son-toplanti", dict({"ozet": yol, "baslik": baslik, "dosya": ad + ".md", "cikti": {"karar": 1, "is": 5},
                                             "yapi": {"baslik": baslik, "maddeler": [{"baslik": "Gündem", "ogeler": ogeler}]}}, **ek))
    def kapat(s): s.p.terminate(); s.p.wait(timeout=10)
ACIK = [{"tur": "is", "metin": "Teklifi gönder", "sahip": "Ayşe Örnek", "tarih": "2026-11-12"}, {"tur": "is", "metin": "Sözleşmeyi gözden geçir", "sahip": "Ayşe Örnek"},
        {"tur": "is", "metin": "Tedarikçiyi ara"}, {"tur": "is", "metin": "Raporu hazırla", "tarih": "2026-11-20"}, {"tur": "is", "metin": "Bütçeyi güncelle"},
        {"tur": "karar", "metin": "Lansman ocakta", "netlik": "ortuk"}, {"tur": "karar", "metin": "Fiyat sabit", "netlik": "acik"},
        {"tur": "soru", "metin": "KDV dahil mi?"}, {"tur": "soru", "metin": "Sözleşme tarihi?", "cevap": "1 Aralık"}]
# tarihsiz 3 (Sözleşme, Tedarikçi, Bütçe), sahipsiz 2 (Tedarikçi, Bütçe), ... Rapor: Raporu hazırla tarihli ama sahipsiz de → sahipsiz 3
try:
    A = Uc("a", toplanti_sonrasi_hatirlat_dk=0.03)
    A.son("toplanti-1", "Planlama görüşmesi", ACIK)
    ok("süre dolmadan hatırlatma yok", A.status().get("proaktif") is None)
    ok("süre dolunca durum alanı gelir", A.bekle(lambda: A.status().get("proaktif")))
    pr = A.status().get("proaktif") or {}
    ok("cümle: toplantı adı, sayılar, Bakalım mı?", "Planlama görüşmesi" in pr.get("cumle", "") and "3 işin tarihi yok" in pr["cumle"] and "3 işin sahibi yok" in pr["cumle"] and "1 karar teyit bekliyor" in pr["cumle"] and "1 açık soru var" in pr["cumle"] and pr["cumle"].endswith("Bakalım mı?"))
    ok("menü bildirimi gitti", "BİLDİRİM (deneme): Açık uçlar" in A.metin())
    ok("ayar kapalıyken açık uç cümlesi sesli söylenmedi", "karakter · Planlama görüşmesi:" not in A.metin())
    A.post("/son-toplanti", {"ozet": os.path.join(T, "toplanti-1.md"), "baslik": "Planlama görüşmesi", "dosya": "toplanti-1.md", "yapi": {"maddeler": [{"baslik": "g", "ogeler": ACIK}]}})
    time.sleep(3.5); ok("aynı toplantı ikinci kez hatırlatılmaz", A.metin().count("PROAKTİF: Planlama görüşmesi:") == 1)
    r = A.post("/proaktif", {"islem": "sor", "id": "yok"}); ok("bilinmeyen kimlikle Bakalım reddedilir", r.get("ok") is False)
    r = A.post("/proaktif", {"islem": "sor", "id": pr["id"]})
    ok("Bakalım: soru asistana yazılı gider, durum kalkar", r.get("ok") is True and "yazılı soru" in A.metin() and A.status().get("proaktif") is None)
    # gizli: özet gelse de hatırlatma yok
    A.post("/komut", {"tur": "gizli"}); A.son("toplanti-2", "Gizli toplantı", ACIK); time.sleep(3.5)
    ok("gizli toplantıda hatırlatma yok", "atlandı — gizli toplantı" in A.metin() and A.status().get("proaktif") is None)
    A.post("/komut", {"tur": "gizli"})
    # deneme
    A.son("toplanti-3", "Deneme toplantısı", ACIK); time.sleep(3.5)
    ok("deneme toplantısında hatırlatma yok", "atlandı — deneme toplantısı" in A.metin())
    A.son("toplanti-3b", "Haftalık görüşme", ACIK, **{}); A.status()
    # kullanıcı Kararlar ve işler'e baktı
    A.post("/proaktif", {"islem": "gordu"}); A.son("toplanti-4", "Planlama", ACIK); A.post("/proaktif", {"islem": "gordu"}); time.sleep(3.5)
    ok("Kararlar ve işler açılmışsa atlanır", "atlandı — kullanıcı Kararlar ve işler'e baktı" in A.metin())
    # açık uç yok
    A.son("toplanti-5", "Kısa görüşme", [{"tur": "is", "metin": "Notu ilet", "sahip": "Ayşe Örnek", "tarih": "2026-11-12"}, {"tur": "karar", "metin": "Devam", "netlik": "acik"}]); time.sleep(3.5)
    ok("açık uç yoksa hatırlatma yok", "atlandı — açık uç yok" in A.metin())
    # yeni toplantı başladı
    A.son("toplanti-6", "Toplantı altı", ACIK)
    A.post("/ping", {"meeting": {"title": "Yeni toplantı"}, "panel": True, "rows": 1})
    A.post("/ingest", {"meeting": {"title": "Yeni toplantı"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Ayşe Örnek", "time": "02:10", "text": "merhaba"}]})
    time.sleep(3.5)
    ok("yeni toplantı başlamışsa atlanır", "atlandı — yeni toplantı başlamış" in A.metin() or "PROAKTİF: Toplantı altı:" not in A.metin())
    A.kapat()
    # sesli ayar açık
    B = Uc("b", toplanti_sonrasi_hatirlat_dk=0.03, toplanti_sonrasi_sesli=True)
    B.son("toplanti-7", "Ürün toplantısı", ACIK)
    ok("sesli ayar açıkken tek cümle seslendirilir", B.bekle(lambda: "PROAKTİF: Ürün toplantısı:" in B.metin()) and B.bekle(lambda: "karakter · Ürün toplantısı:" in B.metin(), 5))
    B.kapat()
    # ayar 0: kapalı
    C = Uc("c", toplanti_sonrasi_hatirlat_dk=0)
    C.son("toplanti-8", "Kapalı", ACIK); time.sleep(2.5)
    ok("ayar 0'da hiçbir şey yapılmaz", "PROAKTİF" not in C.metin() and C.status().get("proaktif") is None)
    ok("ayar şemada: Ayarlar'da görünür", "toplanti_sonrasi_hatirlat_dk" in C.status()["ayarlar"]["deger"] and "toplanti_sonrasi_sesli" in C.status()["ayarlar"]["deger"])
    C.kapat()
    # yeniden başlayınca bekleyen planlanır
finally:
    for n in ("A", "B", "C"):
        try: globals()[n].p.kill()
        except Exception: pass
print("\nTÜM TESTLER GEÇTİ" if not HATA else f"\n{len(HATA)} test kaldı: {HATA}"); shutil.rmtree(T, ignore_errors=True); sys.exit(1 if HATA else 0)
