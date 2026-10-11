#!/usr/bin/env python3
# Faz 3–4 — sessiz mod, kart erteleme, "Ne diyeyim?", sözler defteri ve eylem kuyruğu. Yalıtılmış aktarıcı (SUFLOR_TEST_HIZLI: özet bekleme ve gündemsiz erteleme 2 sn) + izle.
#   Sessiz: Option + Shift + M (/komut sessiz) açar/kapatır; sessizde SÖYLE/NOT bekler, DUR ve soruya CEVAP geçer; bitince izle
#   SESSİZ BİTTİ der; --sessiz-ozet kartı bekleyenleri kapatır; özet gelmezse bekleyenler 2 sn sonra tek tek görünür.
#   Ertele: /card-ack "ertele" kartı gizler; gündemde ▶ değişince (ya da gündemsizde süre dolunca) "geri" alanıyla döner.
#   Ne diyeyim?: /komut ozet → izle NE DİYEYİM (son 2 dk, gündem); --cevap kartı "replik" + "durum" alanıyla, sessizde de geçer.
#   Sözler: soz ekle / liste / kapat, tarih denetimi, hazirlik --kim açık sözleri getirir.
#   Eylem kuyruğu: eylem ekle (anahtarsız 401), sunulmadan "hepsi" onaylanmaz, sun → numaralı liste, sohbetten onay (sıra no) ve
#   panodan red, bekle UYGULA/YAPMA, sonuc yalnız onaylanana, dökümde EYLEM satırı, yeniden başlayınca kuyruk durur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/faz3.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-ss-"); PORT = 8792; URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "proje"))
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "yok")}, open(ay, "w"))
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_HIZLI="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=ENV)
iz = None; olaylar = []
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None):
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                               headers={"X-Suflor-Anahtar": anahtar()})
    try: return json.loads(urllib.request.urlopen(q, timeout=5).read())
    except urllib.error.HTTPError as e: return {"kod": e.code}
kart = lambda tur, metin, **k: (istek("/card", dict({"kind": tur, "text": metin}, **k)).get("card") or {}).get("id")
gorunen = lambda: [c["id"] for c in istek("/cards").get("cards", [])]
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
def bekle_olay(parca, sn=8):
    son = time.time() + sn
    while time.time() < son:
        if any(parca in o for o in olaylar): return True
        time.sleep(0.2)
    return False
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    istek("/ingest", {"meeting": {"title": "Sessiz deneme"}, "source": "transcript", "entries": [{"id": "s/1", "speaker": "Deniz T", "time": "10:00", "text": "merhaba"}]})
    iz = subprocess.Popen([sys.executable, "toplanti-claude.py", "--dir", canli, "--relay", URL, "izle", "--aralik", "2"], cwd=T, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, env=ENV)
    threading.Thread(target=lambda: [olaylar.append(l.rstrip()) for l in iz.stdout], daemon=True).start()
    kontrol("izle başladı", bekle_olay("İZLEME BAŞLADI"))

    # --- sessiz ---
    y = istek("/komut", {"tur": "sessiz"})
    kontrol("sessiz açıldı (10 dk)", y.get("ok") and (y.get("sessiz") or {}).get("acik") and 590 <= y["sessiz"]["kalan_sn"] <= 600)
    kontrol("izle: SESSİZ olayı", bekle_olay("SESSİZ: Deniz sessiz istedi"))
    soyle = kart("soyle", "Bütçeyi sor"); not_ = kart("not", "Rakam teklifte farklı")
    dur = kart("dur", "Şifreyi okuma"); q = istek("/ask", {"text": "kaç kişi?"}).get("question", {}).get("id")
    cevap = kart("cevap", "12 kişi", reply_to=q)
    g = gorunen()
    kontrol("sessizde SÖYLE ve NOT görünmüyor", soyle not in g and not_ not in g)
    kontrol("sessizde DUR ve soruya CEVAP görünüyor", dur in g and cevap in g)
    kontrol("bekleyen sayısı 2", len((istek("/cards").get("sessiz") or {}).get("tutulan") or []) == 2)
    y = istek("/komut", {"tur": "sessiz"})
    kontrol("ikinci basış sessizi kapattı", y.get("ok") and not (y.get("sessiz") or {}).get("acik") and "kapandı" in y.get("metin", ""))
    kontrol("bitişten hemen sonra bekleyenler hâlâ gizli (özet bekleniyor)", soyle not in gorunen())
    kontrol("izle: SESSİZ BİTTİ olayı bekleyen iki kartla", bekle_olay("SESSİZ BİTTİ: 2 kart bekliyor"))
    ozet = kart("soyle", "Sessizdeyken: bütçeyi sor; teklif rakamı farklı", sessiz_ozet=True)
    v = istek("/cards"); g = [c["id"] for c in v["cards"]]
    kontrol("özet kartı görünüyor, bekleyenler kapandı", ozet in g and soyle not in g and not_ not in g)
    kontrol("özetlenenler 'son kapananlar'da yok", not any(c["id"] in (soyle, not_) for c in v.get("closed", [])))
    kontrol("izle: özetlenen kart için KART olayı yok", not any("Bütçeyi sor" in o and o.startswith("KART") for o in olaylar))
    # özet gelmezse bekleyenler 2 sn sonra görünür
    istek("/komut", {"tur": "sessiz"}); k2 = kart("soyle", "Takvimi teyit et"); istek("/komut", {"tur": "sessiz"})
    kontrol("özetsiz: bitişte gizli", k2 not in gorunen())
    time.sleep(2.5)
    kontrol("özetsiz: 2 sn sonra tek tek göründü (kart kaybolmaz)", k2 in gorunen())

    # --- ertele (gündemli) ---
    json.dump({"title": "Sessiz deneme", "items": ["Bütçe", "Takvim", "Riskler"]}, open(os.path.join(canli, "agenda.json"), "w"))
    istek("/agenda-aktif", {"i": 0})
    e1 = kart("soyle", "Riskleri sorarken yedekleri de sor")
    kontrol("ertele kabul edildi", istek("/card-ack", {"id": e1, "status": "ertele"}).get("ok") is True)
    v = istek("/cards")
    kontrol("ertelenen kart gizli, sayaç 1", e1 not in [c["id"] for c in v["cards"]] and v.get("ertelenen") == 1)
    kontrol("izle: KART ⏸ olayı (gündemde)", bekle_olay("KART ⏸ sonraya bırakıldı (gündemde sıradaki maddede"))
    kontrol("ertelenmiş kart ikinci kez ertelenemez", istek("/card-ack", {"id": e1, "status": "ertele"}).get("ok") is False)
    time.sleep(2.5)
    kontrol("gündemli: süre (2 sn) tek başına geri getirmez", e1 not in gorunen())
    istek("/agenda-aktif", {"i": 1})
    v = istek("/cards"); c = next((c for c in v["cards"] if c["id"] == e1), {})
    kontrol("sıradaki maddeye geçince geri geldi ('geri' alanı, en sonda)", c.get("geri") and v["cards"][-1]["id"] == e1 and v.get("ertelenen") == 0)
    kontrol("izle: KART ↩ geri geldi olayı", bekle_olay("KART ↩ geri geldi"))
    istek("/card-ack", {"id": e1, "status": "ertele"}); istek("/agenda-tick", {"i": 1, "v": True, "label": "Takvim"})
    kontrol("gündem maddesi ✓ işaretlenince de geri geldi", e1 in gorunen())
    # --- ertele (gündemsiz) ---
    os.remove(os.path.join(canli, "agenda.json"))
    e2 = kart("dur", "Ekranı paylaşma"); istek("/card-ack", {"id": e2, "status": "ertele"})
    kontrol("gündemsiz: ertelenen gizli", e2 not in gorunen())
    time.sleep(2.5)
    kontrol("gündemsiz: süre dolunca geri geldi", e2 in gorunen())
    kontrol("izle: KART ⏸ olayı (süreyle)", bekle_olay("KART ⏸ sonraya bırakıldı (5 dk sonra"))

    # --- Ne diyeyim? (sessizde de geçer) ---
    istek("/komut", {"tur": "sessiz"})
    y = istek("/komut", {"tur": "ozet"}); q = next((q for q in istek("/cards").get("questions", []) if q.get("tur") == "ozet"), {})
    kontrol("Ne diyeyim? istendi (bekleyen soru, onay metni)", q.get("id") and "Ne diyeyim" in y.get("metin", ""))
    kontrol("izle: NE DİYEYİM olayı + SON 2 DK", bekle_olay("NE DİYEYİM " + str(q.get("id"))) and bekle_olay("SON 2 DK"))
    out = subprocess.run([sys.executable, "toplanti-claude.py", "--dir", canli, "--relay", URL, "kart", "cevap", "Takvimi şimdi netleştirelim mi?",
                          "--durum", "Takvim konuşuluyor", "--cevap", q.get("id", "")], cwd=T, env=ENV, capture_output=True, text=True).stdout
    c = next((c for c in istek("/cards")["cards"] if c.get("text") == "Takvimi şimdi netleştirelim mi?"), {})
    kontrol("replik kartı sessizde görünüyor (replik + durum, soru satırı yok)", c.get("replik") and c.get("durum") == "Takvim konuşuluyor" and "q" not in c)
    kontrol("cevaplanan istek bekleyenlerden düştü", not any(x.get("id") == q.get("id") for x in istek("/cards").get("questions", [])))
    istek("/komut", {"tur": "sessiz"})
    # --- sözler defteri ---
    tc = lambda *a: subprocess.run([sys.executable, "toplanti-claude.py", "--dir", canli, "--relay", URL, *a], cwd=T, env=ENV, capture_output=True, text=True)
    a1 = tc("soz", "ekle", "Yedek raporunu gönderecek", "--kim", "Ayla Örnek", "--tarih", "2026-01-05").stdout
    a2 = tc("soz", "ekle", "Erişim listesini paylaşacak", "--kim", "Deniz T").stdout
    kontrol("soz ekle: kimlik, kişi, geçen tarih işareti", a1.startswith("s1 [acik] Ayla Örnek") and "GEÇTİ" in a1 and a2.startswith("s2 [acik]"))
    kontrol("soz ekle: --kim yoksa ve tarih bozuksa red", tc("soz", "ekle", "x").returncode != 0 and tc("soz", "ekle", "x", "--kim", "a", "--tarih", "5.1").returncode != 0)
    tc("soz", "kapat", "s2")
    kontrol("soz liste: yalnız açıklar; --hepsi kapananı da", "s2" not in tc("soz", "liste").stdout and "s2 [tutuldu]" in tc("soz", "liste", "--hepsi").stdout)
    hz = tc("hazirlik", "--kim", "Ayla").stdout
    kontrol("hazirlik --kim: açık söz ve hazır kart yönergesi", "kapanmamış sözler (Ayla)" in hz and "s1 [acik]" in hz and "durumunu sor" in hz and "s2" not in hz)
    # --- eylem kuyruğu ---
    e1 = tc("eylem", "ekle", "kayit", "Karar: yedek raporu haftalık", "--ayrinti", "kayit.py karar 'yedek raporu haftalık'").stdout
    kontrol("eylem ekle: kuyrukta (bekliyor)", "kuyruğa eklendi" in e1 and "[Kayıt · bekliyor]" in e1)
    kontrol("eylem ekle: ekip mesajı türü", "[Ekip mesajı · bekliyor]" in tc("eylem", "ekle", "mesaj", "Proje — durum notu", "--ayrinti", "Bu hafta yedek raporu").stdout)
    kontrol("eylem ekle: bilinmeyen tür reddedildi", tc("eylem", "ekle", "sil", "x").returncode != 0)
    try: urllib.request.urlopen(urllib.request.Request(URL + "/eylem", data=b'{"tur":"kayit","baslik":"x"}', method="POST"), timeout=3); kod = 200
    except urllib.error.HTTPError as e: kod = e.code
    kontrol("anahtarsız /eylem 401", kod == 401)
    ev = istek("/cards").get("eylem") or {}
    kontrol("toplantı sırasında 2 bekleyen, sunulmamış", ev.get("bekleyen") == 2 and not ev["liste"][0]["sunuldu"])
    kontrol("sunulmadan 'hepsi' onaylanmaz", istek("/eylem-karar", {"id": "hepsi", "durum": "onaylandi"}).get("n") == 0)
    tc("eylem", "ekle", "takip", "Ayla — takip e-postası", "--ayrinti", "Kime: Ayla (adres yok)\nKonu: Toplantı\n\nMerhaba Ayla,")
    su = tc("eylem", "sun").stdout
    kontrol("eylem sun: 3 iş, numaralı liste, ayrıntı içinde", "3 iş panoda" in su and "\n1. " in su and "2. " in su and "Kime: Ayla (adres yok)" in su)
    ids = [x["id"] for x in istek("/cards")["eylem"]["liste"]]
    kontrol("sohbetten onay (sıra no 1)", "1 iş onaylandı" in tc("eylem", "onay", "1").stdout)
    b1 = tc("eylem", "bekle", "--sn", "3").stdout
    kontrol("bekle: UYGULA + ayrıntı, bekleyen 2", "UYGULA: " + ids[0] in b1 and "kayit.py karar" in b1 and "bekleyen 2" in b1)
    istek("/eylem-karar", {"id": ids[1], "durum": "reddedildi"}); istek("/eylem-karar", {"id": ids[2], "durum": "reddedildi"})
    b2 = tc("eylem", "bekle", "--sn", "3").stdout
    kontrol("bekle: reddedilen YAPMA, kuyruk kapandı, eskisi tekrar verilmez", "YAPMA: " + ids[1] in b2 and "kuyruk kapandı" in b2 and ids[0] not in b2)
    kontrol("sonuc: reddedilene yazılmaz", "kaydedilemedi" in tc("eylem", "sonuc", ids[1]).stdout)
    tc("eylem", "sonuc", ids[0], "--not", "karar #81 yazıldı")
    x0 = istek("/cards")["eylem"]["liste"][0]
    kontrol("sonuc: yapıldı + not panoda", x0["durum"] == "yapildi" and x0["sonuc"] == "karar #81 yazıldı")
    md = open(os.path.join(canli, next(f for f in os.listdir(canli) if f.endswith(".md"))), encoding="utf-8").read()
    kontrol("dökümde EYLEM satırı", "**EYLEM** | kuyruğa (Kayıt): Karar: yedek raporu haftalık" in md)
    kontrol("dökümde SESSİZ, ⏸ ve ↩ satırları", "**SESSİZ** | açıldı" in md and "**SESSİZ** | bitti (kullanıcı kapattı)" in md and "**KART ⏸ sonra**" in md and "**KART ↩ geri geldi**" in md)
    istek("/komut", {"tur": "sessiz"}); k3 = kart("soyle", "Kayıt sonrası")
    kontrol("bilinmeyen komut 400", istek("/komut", {"tur": "yok"}).get("kod") == 400)
    log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    kontrol("aktarıcıda hata yok", "Traceback" not in log)
    kontrol("izle'de hata yok", not any("Traceback" in o or "AKTARICI YANIT VERMİYOR" in o for o in olaylar))
finally:
    if iz: iz.terminate(); iz.wait(5)
    r.terminate(); r.wait(5)
    # yeniden başlatma: bellekteki sessiz durumu kaybolur, bekleyen kart görünür (kart kaybolmaz)
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay2.log"), "w"),
                         stderr=subprocess.STDOUT, env=ENV)
    try:
        for _ in range(50):
            try: istek("/status"); break
            except Exception: time.sleep(0.1)
        kontrol("yeniden başlayınca sessizde bekleyen kart görünür", k3 in gorunen())
        kontrol("yeniden başlayınca eylem kuyruğu ve kararlar duruyor", [x["durum"] for x in (istek("/cards").get("eylem") or {}).get("liste", [])] == ["yapildi", "reddedildi", "reddedildi"])
    except NameError: pass
    finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"faz3: {len(hatalar)} sorun" if hatalar else "faz3: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
