#!/usr/bin/env python3
# Bağlam kaynakları (aktarıcı): kutudaki bağlantı ve dosya yolu (boşluklu, tırnaklı), gizli klasör reddi, panoya bırakılan dosya
# (anahtar), Başlat formundaki "Bağlam" alanı (tanınmayan satır reddi), yeni toplantıda arşiv ve kimlik sayacı. Yalıtılmış aktarıcı;
# sahte ayar ve sahte claude (SUFLOR_TEST_BASLAT: Terminal açılmaz). v0.14.0: yerel anahtar (okuma 401, geçişte anahtarsız yazma,
# tek kullanımlık sayfa adresi, kanıt ?k=) ve onay kartı (#76: yalnız anahtarla, karta dokunmak onay değil). Deneme dosyaları ev klasöründe (kural: yalnız ev/bağlı disk),
# sonda silinir.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/baglam.py      (kaldı → çıkış 1)
import base64, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-bg-"); PORT = 8793; URL = f"http://127.0.0.1:{PORT}"; PANO = URL
EVD = os.path.expanduser("~/Library/Caches/Suflor-baglam-deneme"); os.makedirs(os.path.join(EVD, "iki kelime"), exist_ok=True)
belge = os.path.join(EVD, "iki kelime", "teklif özeti.pdf"); open(belge, "wb").write(b"%PDF-1.4 deneme")
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "proje"))
stub = os.path.join(T, "claude-sahte"); open(stub, "w").write("#!/bin/sh\necho \"$@\"\n"); os.chmod(stub, 0o755)
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "yok"), "claude": stub}, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
def anahtar():
    try: return open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: return ""
def istek(yol, govde=None, koken=None, anh=True, ham=False):
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                               headers=dict({"Origin": koken} if koken else {}, **({"X-Suflor-Anahtar": anahtar()} if anh else {})))
    try:
        b = urllib.request.urlopen(q, timeout=5).read(); return b.decode() if ham else json.loads(b)
    except urllib.error.HTTPError as e: return {"kod": e.code}
bg = lambda: json.load(open(os.path.join(canli, "baglam.json"), encoding="utf-8"))
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
try:
    for _ in range(50):
        try: istek("/status"); break
        except Exception: time.sleep(0.1)
    istek("/ingest", {"meeting": {"title": "Eski toplantı"}, "source": "transcript", "entries": [{"id": "s/1", "speaker": "Deniz", "time": "10:00", "text": "merhaba"}]})
    y = istek("/girdi", {"text": "şu sayfaya bak https://ornek.example/rapor?x=1."})
    kontrol("kutudaki bağlantı bağlam oldu (tür 'bağlam', sondaki nokta atıldı)", y.get("tur") == "bağlam" and bg()["kaynaklar"][-1]["deger"] == "https://ornek.example/rapor?x=1")
    istek("/girdi", {"text": f'"{belge}"'})
    kontrol("tırnak içindeki boşluklu dosya yolu bağlam oldu", bg()["kaynaklar"][-1].get("deger") == os.path.realpath(belge))
    gizli = os.path.expanduser("~/.zshrc") if os.path.isfile(os.path.expanduser("~/.zshrc")) else os.path.expanduser("~/.bash_profile")
    y = istek("/girdi", {"text": gizli})
    kontrol("gizli dosya bağlam olmadı (yalnız not)", y.get("tur") == "not" and len(bg()["kaynaklar"]) == 2)
    y = istek("/girdi", {"text": "? https://soru.example/a ne diyor"})
    kontrol("soru olarak giden bağlantı ayrıca bağlam olmadı", y.get("tur") == "soru" and len(bg()["kaynaklar"]) == 2)
    veri = base64.b64encode(b"Bilgi notu").decode()
    kontrol("anahtarsız dosya bırakma reddedildi", istek("/baglam-dosya", {"ad": "not.txt", "veri": veri}, PANO, anh=False).get("kod") == 401)
    kontrol("anahtarlı ama pano dışı kökenden dosya bırakma reddedildi", istek("/baglam-dosya", {"ad": "not.txt", "veri": veri}).get("kod") == 403)
    y = istek("/baglam-dosya", {"ad": "../../kötü ad.txt", "veri": veri}, PANO)
    yol = bg()["kaynaklar"][-1]["deger"] if y.get("ok") else ""
    kontrol("anahtarlı dosya bağlam klasörüne yazıldı (ad temizlendi)", y.get("ok") and yol.startswith(os.path.join(canli, "baglam") + "/") and open(yol, "rb").read() == b"Bilgi notu" and "/../" not in yol)
    kontrol("/cards bağlam listesini veriyor", [x["kaynak"] for x in istek("/cards").get("baglam", [])] == ["kutu", "kutu", "birak"])
    y = istek("/baslat", {"konu": "Yeni — dış", "baglam": "https://yeni.example/sunum\nbu satır kaynak değil"}, PANO)
    kontrol("Başlat: tanınmayan bağlam satırı reddedildi", y.get("ok") is False and "tanınmadı" in (y.get("err") or "") and len(bg()["kaynaklar"]) == 3)
    ag = os.path.join(canli, "agenda.json"); json.dump({"title": "Eski", "baslangic": "21:48", "bitis": "22:18", "items": ["madde"]}, open(ag, "w"))
    os.utime(ag, (time.time() - 86400, time.time() - 86400))  # dünden kalan gündem
    y = istek("/baslat", {"konu": "Yeni — dış", "baglam": f"https://yeni.example/sunum\n{belge}"}, PANO)
    a_ = json.load(open(ag)); sec = json.load(open(os.path.join(canli, "takvim-secilen.json")))
    kontrol("Başlat (takvimsiz): dünkü gündemin saati şimdiye çekildi, maddeler kaldı; seçimde başlangıç/bitiş var",
            a_["baslangic"] == time.strftime("%H:%M") and a_["items"] == ["madde"] and sec.get("baslangic") and sec.get("bitis"))
    k = bg()["kaynaklar"]
    kontrol("Başlat: eski toplantının kaynakları arşive, yeniler eklendi", y.get("ok") and [x["kaynak"] for x in k] == ["baslat", "baslat"]
            and len(open(os.path.join(canli, "baglam-arsiv.jsonl"), encoding="utf-8").read().splitlines()) == 3)
    kontrol("kimlik sayacı arşivden sonra sürüyor (b4, b5)", [x["id"] for x in k] == ["b4", "b5"])
    # --- v0.14.0 yerel anahtar ---
    k_ = anahtar(); TEAMS = "https://teams.microsoft.com"
    kontrol("anahtarsız okuma 401 (/status, /cards, /taslak, /hazirlik.json)", all(istek(y_, anh=False).get("kod") == 401 for y_ in ("/status", "/cards", "/taslak", "/hazirlik.json")))
    kontrol("pano kökeni taklit edilse de anahtarsız okuma 401", istek("/status", anh=False, koken=PANO).get("kod") == 401)
    sayfa = istek("/", anh=False, ham=True)
    kontrol("pano kabuğu anahtarsız açılır, anahtar içermez", isinstance(sayfa, str) and "SUFLOR_ANAHTAR" in sayfa and k_ not in sayfa and "__SAYFA_ANAHTAR__" not in sayfa)
    u = istek("/tek-kullanim", {"yol": "/hazirlik"}).get("url") or ""
    kontrol("tek kullanımlık adres anahtarsız alınamaz", istek("/tek-kullanim", {}, anh=False).get("kod") == 401)
    s1 = istek(u.replace(URL, ""), anh=False, ham=True); s2 = istek(u.replace(URL, ""), anh=False, ham=True)
    kontrol("tek kullanımlık adres anahtarı bir kez gömer", "/hazirlik?t=" in u and k_ in s1 and k_ not in s2)
    kontrol("kanıt görseli: yanlış ?k= 401", istek("/kanit/x/y.png?k=" + "0" * 48, anh=False).get("kod") == 401)
    kontrol("geçiş: eski eklentinin anahtarsız yazması kabul", istek("/ping", {"panel": True}, TEAMS, anh=False).get("ok") is True)
    kontrol("geçiş: panoda 'eklenti eski' işareti", (istek("/status").get("anahtarsiz") or {}).get("tur") == "eklenti")
    kontrol("geçiş: eski eklentiye /takvim yalnız sürüm", set(istek("/takvim?v=0.13.45", anh=False)) == {"surum", "toplanti", "anahtar_gerekli"})
    kontrol("anahtarsız Başlat reddedildi", istek("/baslat", {"konu": "x"}, PANO, anh=False).get("kod") == 401)
    c = (istek("/card", {"kind": "soyle", "text": "kayit.py olay 'deneme' yazılsın mı?", "onay": True}).get("card") or {})
    kontrol("onay kartı açıldı", c.get("onay") is True and any(x["id"] == c.get("id") and x.get("onay") for x in istek("/cards").get("cards", [])))
    kontrol("onay: anahtarsız Onayla 401", istek("/card-ack", {"id": c.get("id"), "status": "onaylandi"}, TEAMS, anh=False).get("kod") == 401)
    kontrol("onay: karta dokunmak (okundu) kapatmaz", istek("/card-ack", {"id": c.get("id"), "status": "okundu"}).get("ok") is False)
    kontrol("onay: anahtarlı Onayla geçti", istek("/card-ack", {"id": c.get("id"), "status": "onaylandi"}, PANO).get("ok") is True)
    son = json.loads(open(os.path.join(canli, "kartlar.jsonl"), encoding="utf-8").read().splitlines()[-1])
    kontrol("onay kaydı 'yetkili' işaretli", son.get("status") == "onaylandi" and son.get("yetkili") is True)
    kontrol("onay: ikinci kez Reddet geçmez", istek("/card-ack", {"id": c.get("id"), "status": "reddedildi"}, PANO).get("ok") is False)
    kontrol("normal kartta Onayla geçmez", istek("/card-ack", {"id": (istek("/card", {"kind": "soyle", "text": "x"}).get("card") or {}).get("id"), "status": "onaylandi"}).get("ok") is False)
    kontrol("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True); shutil.rmtree(EVD, ignore_errors=True)
print(f"bağlam: {len(hatalar)} sorun" if hatalar else "bağlam: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
