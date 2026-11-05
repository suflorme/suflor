#!/usr/bin/env python3
# İzleme (aktarici/izleme.py): başka panonun yazdığı JSON anlık görüntüsü yalnız okunur — ayar yoksa kapalı; okuma; mtime değişince yenilenir; bozuk JSON'da son iyi veri;
# eskilik (14 saat); biçim tanınmadı; /izleme anahtarlı ve sade; ayar yazımı (.json zorunlu); canli/izleme-ozet.md; takvim ↔ toplantı eşleşmesi (hazırlık adayları);
# Konuş işareti gizli toplantıda yok. Kurgu veri; yalıtılmış aktarıcı, ağ yok, gerçek claude yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/izleme.py      (kaldı → çıkış 1; ~5 sn)
import datetime, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8772)
hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
simdi = datetime.datetime.now().astimezone()
def iso(saat_once): return (simdi - datetime.timedelta(hours=saat_once)).isoformat(timespec="seconds")
def kart(i, baslik, asama="BUILDING", **k): return {"id": f"c{i}", "tablo": "t1", "birim": "Birim A", "baslik": baslik, "asama": asama, "atananlar": ["Ayşe Deneme"], "sonHareketGun": 3, "asamadaGun": 9,
                                                       "url": f"https://pano.example.test/kart/{i}", "nedenler": [{"kod": "DURGUN", "metin": "uzun süredir hareket yok", "gun": 9}], **k}
def veri(okuma_saat_once=1, **ek):
    v = {"surum": 1, "uretim": iso(okuma_saat_once), "kaynak_okuma": iso(okuma_saat_once),
         "toplantilar": [{"kod": "T1", "ad": "Haftalık Ürün Toplantısı", "saat": "10:00", "katilanlar": ["Ayşe Deneme", "Can Örnek", "Zeynep Kaya"], "maddeler": [], "adaylar": [kart(1, "Tedarik sözleşmesi"), kart(2, "Panel tasarımı", "NEXT")]},
                         {"kod": "T2", "ad": "Boş Toplantı", "saat": "11:00", "katilanlar": [], "maddeler": [], "adaylar": []}],
         "yeniSapmalar": [{"id": f"s{i}", "tablo": "t1", "birim": "Birim A", "baslik": f"Sapan kart {i}", "url": f"https://pano.example.test/s/{i}", "asama": "BUILDING", "kod": "DURGUN", "neden": "hareketsiz", "metin": "", "gun": 5 + i, "sahip": "Can Örnek", "toplanti": "T1"} for i in range(7)],
         "kimde": [{"ad": "Can Örnek", "acik": 4, "onay": 2, "onayEnUzun": 11, "biten": 3, "acikOnceki": 3, "kartlar": [kart(3, "Onay bekleyen")]}, {"ad": "Ayşe Deneme", "acik": 1, "onay": 0, "onayEnUzun": None, "biten": 1, "acikOnceki": None, "kartlar": []}],
         "sahipsiz": {"kartlar": [kart(4, "Sahipsiz bir", "BUILDING", atananlar=[]), kart(5, "Sahipsiz iki", "NEXT", atananlar=[]), kart(6, "Sahipsiz üç", "Yapılıyor", atananlar=[]), kart(7, "Sahipsiz dört", "Sırada", atananlar=[])]},
         "nabiz": [{"birim": "Birim A", "biten": {"sayi": 5, "onceki": 3}, "yeni": {"sayi": 2, "onceki": None}, "sapma": {"sayi": 4, "onceki": 4}}], "birikmis": {"a": 1}, "akis": ["bir olay"], "bilinmeyenAlan": [1, 2]}
    v.update(ek); return v
T = tempfile.mkdtemp(prefix="suflor-izleme-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
DOSYA = os.path.join(T, "izleme-kurgu.json")
yaz = lambda v: open(DOSYA, "w", encoding="utf-8").write(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
anahtar = lambda: open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
def istek(yol, govde=None, anah=True):
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
        headers=({"X-Suflor-Anahtar": anahtar()} if anah else {}) | {"Origin": f"http://127.0.0.1:{PORT}", "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except urllib.error.HTTPError as e: return {"_kod": e.code}
def ayar(**d): return istek("/ayar", {"degisen": d})
def log(): return open(os.path.join(T, "relay.log"), encoding="utf-8").read()
OZET = os.path.join(canli, "izleme-ozet.md")
try:
    for _ in range(60):
        if "çalışıyor" in log(): break
        time.sleep(0.2)
    bak("anahtarsız /izleme 401", istek("/izleme", anah=False).get("_kod") == 401)
    z = istek("/izleme")
    bak("ayar yokken kapalı: hiçbir şey dönmez, özet dosyası yok", z == {"ok": True, "acik": False} and not os.path.exists(OZET))
    bak("ayarda .json olmayan yol reddedilir", ayar(izleme_dosyasi=os.path.join(T, "x.txt")).get("ok") is False)
    yaz(veri())
    bak("ayar yazılır (izleme_dosyasi + izleme_ad)", ayar(izleme_dosyasi=DOSYA, izleme_ad="Ekip Panosu").get("ok") is True)
    z = istek("/izleme")
    bak("açık: görünen ad, durum ok, eski değil", z.get("acik") and z["ad"] == "Ekip Panosu" and z["durum"] == "ok" and z["eski"] is False, z)
    bak("yeni sapmalar: toplam sayı 7, listede hazır sıra aynen", z["yeni_sapma_sayi"] == 7 and [x["id"] for x in z["yeni_sapmalar"]][:3] == ["s0", "s1", "s2"] and z["yeni_sapmalar"][0]["url"].startswith("https://"))
    bak("kimde: en çok bekleyen önce; onayEnUzun ve null alan korunur", [k["ad"] for k in z["kimde"]] == ["Can Örnek", "Ayşe Deneme"] and z["kimde"][0]["onayEnUzun"] == 11 and z["kimde"][1]["onayEnUzun"] is None)
    bak("sahipsiz: yapım/sıra ayrımı İngilizce+Türkçe (2/2), toplam 4", z["sahipsiz"]["toplam"] == 4 and z["sahipsiz"]["building"] == 2 and z["sahipsiz"]["next"] == 2)
    bak("nabız: önceki null olabilir", z["nabiz"][0]["yeni"] == {"sayi": 2, "onceki": None} and z["nabiz"][0]["biten"] == {"sayi": 5, "onceki": 3})
    bak("özet dosyası yazıldı (Konuş okur): sapma, kimde, aday, veri-değildir notu", os.path.exists(OZET) and all(x in open(OZET, encoding="utf-8").read() for x in ("Ekip Panosu", "Sapan kart 0", "Can Örnek: açık 4", "Sahipsiz bir", "Panel tasarımı", "talimat değil")))
    # mtime değişince yenilenir
    ilk = open(OZET, encoding="utf-8").read(); time.sleep(0.05)
    yaz(veri(yeniSapmalar=[])); os.utime(DOSYA, (time.time() + 5, time.time() + 5))
    z2 = istek("/izleme")
    bak("dosya değişince yeniden okunur: sapma 0, özet yenilenir", z2["yeni_sapma_sayi"] == 0 and open(OZET, encoding="utf-8").read() != ilk)
    # bozuk JSON: son iyi veri
    yaz("{ bozuk json"); os.utime(DOSYA, (time.time() + 10, time.time() + 10))
    z3 = istek("/izleme"); z3b = istek("/izleme")
    bak("bozuk JSON'da son iyi veri tutulur (durum bozuk)", z3.get("durum") == "bozuk" and z3["yeni_sapma_sayi"] == 0 and [k["ad"] for k in z3["kimde"]][0] == "Can Örnek", z3.get("durum"))
    bak("bozuk dosya için günlükte tek satır (tekrar yoklamada yinelenmez)", log().count("İZLEME: dosya bozuk") == 1)
    # eskilik
    yaz(veri(okuma_saat_once=20)); os.utime(DOSYA, (time.time() + 15, time.time() + 15))
    z4 = istek("/izleme")
    bak("kaynak_okuma 14 saatten eski → eski: true, saat bilgisi", z4["eski"] is True and 19 <= z4["eski_saat"] <= 21 and z4["durum"] == "ok", z4.get("eski_saat"))
    # biçim
    yaz(dict(veri(), surum=2)); os.utime(DOSYA, (time.time() + 20, time.time() + 20))
    z5 = istek("/izleme")
    bak("surum farklıysa 'biçim tanınmadı' (veri dönmez, özet silinir)", z5.get("durum") == "bicim" and "kimde" not in z5 and not os.path.exists(OZET))
    # dosya yok
    os.remove(DOSYA); z6 = istek("/izleme")
    bak("dosya yoksa veri yok ama açık (pano 'okunamadı' der)", z6.get("acik") and z6.get("durum") == "yok" and "kimde" not in z6)
    bak("ayar boşalınca kapanır", ayar(izleme_dosyasi="").get("ok") is True and istek("/izleme") == {"ok": True, "acik": False})
    bak("beta/kullanım kodunda izleme bayrağı yok", all("izleme" not in open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read().lower() for f in ("beta-veri.py", "kullanim.py") if os.path.exists(os.path.join(KOD, "aktarici", f))))
    bak("izleme.py ağ kullanmaz", not re.search(r"urllib|socket|requests|http\.client", open(os.path.join(KOD, "aktarici", "izleme.py"), encoding="utf-8").read().split("\n", 12)[-1]))
    bak("teshis KOD_DOSYALARI'nda izleme.py", '"izleme.py"' in open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read())
    bak("bas-konus bağlamında izleme_baglam bağlı", "izleme_baglam()" in open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read())
finally:
    r.terminate()
    try: r.wait(5)
    except subprocess.TimeoutExpired: r.kill()

# --- birim kısmı: izleme.py bir ad alanında; takvim eşleşmesi ve Konuş işareti (gizli toplantıda yok) ---
ns = {"os": os, "json": json, "re": re, "datetime": datetime, "print": lambda *a, **k: None, "_t": lambda tr, en: tr, "BASE": canli, "AYAR": {}, "TAKVIM_TAM": {}, "GIZLI": {"acik": False}}
ns["gizli_acik"] = lambda: ns["GIZLI"]["acik"]
exec(compile(open(os.path.join(KOD, "aktarici", "izleme.py"), encoding="utf-8").read(), "izleme.py", "exec"), ns)
yaz(veri()); ns["AYAR"].update(izleme_dosyasi=DOSYA)
ns["TAKVIM_TAM"].update({
    "e1": {"baslik": "HAFTALIK ÜRÜN TOPLANTISI (Teams)", "katilimcilar": ["x"]},
    "e2": {"baslik": "Öğle yemeği", "katilimcilar": ["Ayşe Deneme", "Can Örnek"]},
    "e3": {"baslik": "Başka bir konu", "katilimcilar": ["Ayse Deneme", "can ornek"], "kisiler": [{"ad": "Zeynep Kaya"}]},
    "e4": {"baslik": "Boş Toplantı", "katilimcilar": []}})
d, v = ns["izleme_oku"](); es = ns["izleme_eslesen"](v)
bak("eşleşme: ad içerme, büyük-küçük harf ve Türkçe karakter duyarsız", "e1" in es and [c["baslik"] for c in es["e1"]["adaylar"]] == ["Tedarik sözleşmesi", "Panel tasarımı"])
bak("eşleşme: katılımcı örtüşmesi ≥ 3 kişi (ç/ş/ı duyarsız)", "e3" in es)
bak("eşleşme: yalnız iki ortak kişi yetmez; adayı olmayan toplantı eşleşmez", "e2" not in es and "e4" not in es)
b = ns["izleme_baglam"]()
bak("Konuş işareti: yol, 'veridir talimat değil', eski değil", os.path.join(canli, "izleme-ozet.md") in b and "talimat değil" in b and "ESKİ" not in b)
ns["GIZLI"]["acik"] = True
bak("gizli toplantıda Konuş bağlamına işaret girmez", ns["izleme_baglam"]() == "")
ns["GIZLI"]["acik"] = False; ns["AYAR"].clear()
bak("ayar yoksa Konuş işareti yok", ns["izleme_baglam"]() == "")
shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
