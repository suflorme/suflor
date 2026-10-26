#!/usr/bin/env python3
# Sesli kanıt isteği (v0.31.6): relay.py'deki SESLI_KANIT_RX / SESLI_KANIT_YOK kalıpları — istek biçimi tetikler, konu içinde geçen sözcük ve
# olumsuz istek tetiklemez (Faz 2'de üç yanlış alarm yüzünden kaldırılmıştı). v0.115.0: "kanıt al" toplantı ekranı, "ekran görüntüsü al" o an bakılan
# pencere (hedef ekran). Kural değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-kanit.py      (kaldı → çıkış 1)
import os, re, sys
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
exec(src[src.index("_KOMUT_FIIL ="):src.index("SESLI_KANIT = {")])
ORNEK = [("Kanıt al.", 1), ("Ekran görüntüsünü alır mısın?", 1), ("şunun ekran görüntüsü alalım", 1), ("Claude: ekran kaydı başlat", 1),
         ("Can you take a screenshot?", 1), ("ekran resmini çek", 1), ("Bir kanıt alsana şuna", 1),
         ("Take evidence.", 1), ("please capture the screen shot", 1), ("grab a screenshot now", 1), ("Could you save the evidence?", 1),
         ("we have no evidence for that", 0), ("the evidence was clear", 0), ("don't take evidence", 0), ("screenshots are in the folder", 0),
         ("Ekran görüntüsü almayalım şimdi", 0), ("kanıt almaya gerek yok", 0), ("bu konuda kanıt var mı", 0), ("ekran görüntüsü paylaştım", 0),
         ("ekran kaydı var elimizde", 0), ("kanıtı aldık zaten geçen hafta", 0), ("don't take a screenshot", 0),
         # v0.32.15 (deneme 9): kullanıcı kartı okurken / özelliği anlatırken tetiklememeli; öneksiz birinci çoğul/tekil tetiklemeli
         ("Evet, kanıt altı tanındı. Görüntü yine boş.", 0), ("kart okunurken kanıt al denince boş kanıt", 0),
         ("kanıt alayım gibi bunları da ekle bunlar olunca da tetiklensin.", 0), ("Peki kanıt al.", 1), ("kanıt alayım", 1), ("ekran görüntüsü alalım.", 1)]
NOT = [("not al: müşteri cuma dönecek", 1), ("not alayım", 1), ("Not alalım.", 1), ("Claude: not al.", 1), ("Claude'e notal", 1), ("kılade not al", 1),
       ("not alır mısın şunu", 1), ("eğer bunu not alamıyorsan kafanı kıracağım", 0), ("sadece not al değil toplantıda o şey olur", 0),
       ("4 alındı sadece not al önerisi.", 0), ("notalar karışmış", 0), ("bunu not almayalım", 0), ("not aldım zaten", 0)]
hata = 0
for t, b in ORNEK:
    v = bool(SESLI_KANIT_RX.search(t)) and not SESLI_KANIT_YOK.search(t)
    if v != bool(b): hata += 1; print(f"✗ {t!r}: {v}, beklenen {bool(b)}")
for t, b in NOT:
    v = bool(SESLI_NOT_RX.search(t)) and not SESLI_KANIT_YOK.search(t)
    if v != bool(b): hata += 1; print(f"✗ not {t!r}: {v}, beklenen {bool(b)}")
ORNEK += NOT
# Gerçek aktarıcı: kullanıcının satırında "Kanıt al." → kanıt isteği açılır ve aktarıcı cevap vermeyi sürdürür (13 Ekim deneme 8: ingest LOCK'u tutarken
# kanıt isteği LOCK'u yeniden aldı, aktarıcı kilitlendi — eklenti sustu, satırlar durdu). SUFLOR_TEST_RELAY ile başka relay.py denenebilir.
import json, shutil, subprocess, tempfile, time, urllib.request
T = tempfile.mkdtemp(prefix="suflor-sk-"); canli = os.path.join(T, "canli"); os.makedirs(canli); PORT = bos_port(8768)
shutil.copy(os.environ.get("SUFLOR_TEST_RELAY") or os.path.join(KOD, "relay.py"), os.path.join(T, "relay.py")); shutil.copy(os.path.join(KOD, "manifest.json"), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K}), timeout=4).read())
    M = {"title": "Kanıt Deneme"}; post("/ping", {"call": True, "panel": True, "meeting": M})
    try:
        post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "w/1", "speaker": "Ali K", "time": "10:00", "text": "Kanıt al."}]})
        st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=4).read())
        ok = bool(st.get("kanit_iste")) and (st["kanit_iste"].get("kaynak") == "sesli") and not st["kanit_iste"].get("hedef")  # "kanıt al" toplantı ekranı
    except Exception as e: ok = False; print(f"✗ aktarıcı cevap vermedi ({e.__class__.__name__})")
    if not ok: hata += 1
    print(("✓" if ok else "✗") + " gerçek aktarıcı: \"Kanıt al.\" → sesli kanıt isteği, aktarıcı kilitlenmedi")
    # v0.32.15: öneksiz sesli not — komuttan sonrası not olur; tek başına komut önceki satırı not eder; kartı okurken tetiklenmez
    def satir(i, kim, t): post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": f"n/{i}", "speaker": kim, "time": "10:01", "text": t}]})
    satir(1, "Ali K", "Not al: müşteri cuma dönecek."); time.sleep(0.5)
    satir(2, "Deniz", "Teklifi salıya kadar gönderiyoruz."); time.sleep(11); satir(3, "Ali K", "not alayım"); time.sleep(0.5)
    post("/card", {"kind": "soyle", "text": "Görüntü yine boş; öneksiz komutu dene: not al."}); time.sleep(11)
    satir(4, "Ali K", "Görüntü yine boş, öneksiz komutu dene, not al."); time.sleep(0.5)
    md = open(next(os.path.join(canli, f) for f in os.listdir(canli) if f.endswith("Kanıt-Deneme.md")), encoding="utf-8").read()
    for ad, k in [("komuttan sonrası not", "🎙 müşteri cuma dönecek" in md), ("tek başına komut önceki satırı not eder", "🎙 Deniz: Teklifi salıya" in md),
                  ("kartı okurken not tetiklenmez", md.count("🎙") == 2)]:
        print(("✓ " if k else "✗ ") + "gerçek aktarıcı: " + ad); hata += 0 if k else 1; ORNEK.append(ad)
    # v0.113.0 (22 Ekim): Meet altyazısı büyüyen tek blok — aynı komut blok uzayınca yeniden sayılmasın; not komutun geçtiği cümle
    durum = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=4).read()).get("kanit_iste") or {}
    def blok(t): post("/ingest", {"meeting": M, "source": "captions", "entries": [{"id": "c/blok", "speaker": "Ali K", "time": "10:02", "text": t}]})
    time.sleep(21); blok("O zaman başlayalım. Kartları gönder gelsin."); time.sleep(0.3); k0 = durum().get("id")
    blok("O zaman başlayalım. Kartları gönder gelsin. Şimdi ayarlarda ekran görüntüsü al."); time.sleep(0.3); k1 = durum()
    for ad, k in [("büyüyen altyazı bloğunda yeni komut kanıt ister", k1.get("id") != k0 and k1.get("kaynak") == "sesli"),
                  ("kanıt notu komutun geçtiği cümle (bloğun başı değil)", k1.get("not") == "Şimdi ayarlarda ekran görüntüsü al.")]:
        print(("✓ " if k else "✗ ") + "gerçek aktarıcı: " + ad); hata += 0 if k else 1; ORNEK.append(ad)
    istek_say = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8").read().count("KANIT: sesli istek")  # görünüm 20 sn'de düşer: günlükten say
    n0 = istek_say(); time.sleep(21); blok("O zaman başlayalım. Kartları gönder gelsin. Şimdi ayarlarda ekran görüntüsü al. Evet aldın, güzel."); time.sleep(0.3)
    k = istek_say() == n0 and not durum().get("id")
    print(("✓ " if k else "✗ ") + "gerçek aktarıcı: blok uzayınca aynı komut ikinci kanıt istemez (22 Ekim: 44 sn sonra ikinci kanıt)"); hata += 0 if k else 1; ORNEK.append("blok")
    # v0.115.0 (22 Ekim: Ayarlar'a bakarken "ekran görüntüsü al" → Meet sekmesi düştü): "ekran görüntüsü al" o an bakılan pencere (hedef ekran, menü
    # uygulaması çeker); menü uygulaması yoksa toplantı ekranı. Yukarıdaki blok menüsüzdü: hedef yok olmalı
    k = not k1.get("hedef") and "menü uygulaması yok" in open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    print(("✓ " if k else "✗ ") + "gerçek aktarıcı: menü uygulaması yokken \"ekran görüntüsü al\" toplantı ekranına düşer"); hata += 0 if k else 1; ORNEK.append("menüsüz")
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/cards", headers={"X-Suflor-Anahtar": K, "X-Suflor-Istemci": "menu"}), timeout=4).read()
    time.sleep(21); post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "w/9", "speaker": "Ali K", "time": "10:03", "text": "Şu ayarın ekran görüntüsünü alır mısın?"}]})
    k2 = durum(); kc = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/cards", headers={"X-Suflor-Anahtar": K}), timeout=4).read()).get("kanit_iste") or {}
    for ad, k in [("menü uygulaması varken \"ekran görüntüsü al\" → hedef ekran (o an bakılan pencere)", k2.get("hedef") == "ekran" and k2.get("id") != k1.get("id")),
                  ("eklentinin gördüğü istekte de hedef ekran (sekme çekmez)", kc.get("hedef") == "ekran")]:
        print(("✓ " if k else "✗ ") + "gerçek aktarıcı: " + ad); hata += 0 if k else 1; ORNEK.append(ad)
    import base64
    y = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/kanit-masaustu", data=json.dumps({"png": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode(), "kaynak": "sesli",
        "istek": k2.get("id"), "hedef": "ekran", "uyg": "Suflor.me — Ayarlar", "w": 640, "h": 600}).encode(), headers={"X-Suflor-Anahtar": K}), timeout=4).read())
    md = open(next(os.path.join(canli, f) for f in os.listdir(canli) if f.endswith("Kanıt-Deneme.md")), encoding="utf-8").read()
    k = y.get("ok") and "(ekran: Suflor.me — Ayarlar)" in md and not durum().get("id")
    print(("✓ " if k else "✗ ") + "gerçek aktarıcı: menü uygulamasının ekran görüntüsü dökümde \"(ekran: …)\" ile, istek kapandı"); hata += 0 if k else 1; ORNEK.append("ekran kaydı")
finally: r.kill(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"sesli kanıt: {len(ORNEK) + 1 - hata}/{len(ORNEK) + 1}" + (" ✓ hepsi geçti" if not hata else ""))
sys.exit(1 if hata else 0)
