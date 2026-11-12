#!/usr/bin/env python3
# Kesişim sayfası (F3, 12 Kasım): GET /kesisim (sayfa kabuğu, anahtarsız), GET /kesisim.json (anahtarlı; düzeltmeler / araştırmalar / sorulacak / bırakılanlar / kaynaklar, ham kod yok),
# POST /kesisim geri_al (yalnız pano kökeni + anahtar; kesisim-coz.py geri_al → sahte tazi.py'ye "--kapat N"), geliştirici değilse 404/kapalı, gizli kipte kapalı, ?t= tek kullanımlık anahtar gömme.
# Kurgu veri; yalıtılmış aktarıcı + sahte tazi.py; gerçek _canli'ye dokunmaz, ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kesisim-sayfa.py      (kaldı → çıkış 1)
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8774)
hata = []
def bak(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else f"  — {ek}"))
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-kesisim-sayfa-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
for f in ("relay.py", "manifest.json", "kesisim.py", "kesisim-coz.py", "baglayici.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
CAGRI = os.path.join(T, "tazi-cagri.txt")
open(os.path.join(T, "tazi.py"), "w").write(f"import sys\nopen({CAGRI!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n")  # sahte Tazı: çağrıyı yazar, başarılı döner
def yaz(ad, v): open(os.path.join(canli, ad), "w", encoding="utf-8").write(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
SIMDI = datetime.datetime.now().replace(microsecond=0); BUGUN = SIMDI.date().isoformat()
I = {k: (k * 16)[:16] for k in "abcdef"}  # hex kimlikler
ks = lambda *s: [{"sistem": x, "kayit": "k", "baglanti": "x"} for x in s]
yaz("kesisim.json", {"olusturma": SIMDI.isoformat(), "kaynaklar": [{"ad": "Proje veritabanı", "son_okuma": None, "yas_sn": 3 * 3600, "durum": "ok"}, {"ad": "Tazı dizini", "son_okuma": None, "yas_sn": 200000, "durum": "ok"}, {"ad": "Kapalı kaynak", "yas_sn": None, "durum": "kapali"}],
    "bulgular": [{"id": I["a"], "tur": "celiski", "varlik": "firma:ornek.test", "ozet": "Ornek Firma: web sitesi adresi iki kaynakta farklı.", "kaynaklar": ks("tazi", "vt")},
                 {"id": I["b"], "tur": "eksik", "varlik": "kisi:7", "ozet": "Deniz Kurgu için telefon numarası kayıtta yok.", "kaynaklar": ks("vt")},
                 {"id": I["c"], "tur": "celiski", "varlik": "firma:belirsiz.test", "ozet": "Belirsiz Firma: kuruluş yılı çelişiyor.", "kaynaklar": ks("tazi")},
                 {"id": I["d"], "tur": "celiski", "varlik": "firma:yok.test", "ozet": "Çözülemeyen Firma: sahibi belirsiz.", "kaynaklar": ks("vt")},
                 {"id": I["e"], "tur": "celiski", "varlik": "firma:birak.test", "ozet": "Bırakılan Firma: eski bir ayrıntı.", "kaynaklar": ks("tazi")}],
    "cozum": {"tarih": BUGUN, "duzeltilen": 1, "arastirilan": 1, "birakilan": 1, "cozulemeyen_onemli": [{"id": I["d"], "ozet": "Çözülemeyen Firma: sahibi belirsiz.", "neden": "karar_yok"}]}})
yaz("kesisim-coz.jsonl", "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in [
    {"t": (SIMDI - datetime.timedelta(minutes=30)).isoformat(), "id": I["a"], "karar": "duzelt", "eylem": "tazi_dosya_eklendi", "guven": 0.9, "geri_al": {"sistem": "tazi", "kim": "ornek-firma", "kapat": 12}},
    {"t": (SIMDI - datetime.timedelta(hours=2)).isoformat(), "id": I["b"], "karar": "duzelt", "eylem": "tazi_dosya_eklendi", "guven": 0.8, "geri_al": {"sistem": "tazi", "kim": "deniz-kurgu", "kapat": 13}},
    {"t": (SIMDI - datetime.timedelta(hours=1, minutes=50)).isoformat(), "id": I["b"], "karar": "duzelt", "eylem": "geri_alindi"},
    {"t": (SIMDI - datetime.timedelta(minutes=20)).isoformat(), "id": I["c"], "karar": "arastir", "eylem": "tazi_kuyruga_alindi", "guven": 0.8},
    {"t": (SIMDI - datetime.timedelta(minutes=19)).isoformat(), "id": I["d"], "karar": "arastir", "eylem": "tazi_kuyruga_alindi", "guven": 0.8},
    {"t": (SIMDI - datetime.timedelta(minutes=18)).isoformat(), "id": I["e"], "karar": "birak", "eylem": "bastirildi", "guven": 0.9}]))
yaz("kesisim-coz-durum.json", {"birak": {I["e"]: {"t": SIMDI.isoformat(), "gerekce": "önemsiz"}}, "arastir": {}, "duzelt": {}, "oh_bekleyen": {}, "gun": {"tarih": BUGUN, "duzeltme_n": 1}})
ay = os.path.join(T, "ayar.json")
def baslat(gel=True):
    json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "gelistirici": gel}, open(ay, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_KESISIM_DONGU_YOK="1")
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "a"), stderr=subprocess.STDOUT, env=env)
    for _ in range(80):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1); break
        except Exception: time.sleep(.25)
    return p
def anh(): return open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
def ist(yol, govde=None, pano=True, anahtar=True):
    h = {"Content-Type": "application/json"}
    if anahtar: h["X-Suflor-Anahtar"] = anh()
    if pano: h["Origin"] = f"http://127.0.0.1:{PORT}"
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=None if govde is None else json.dumps(govde).encode(), method="GET" if govde is None else "POST", headers=h)
    try:
        r = urllib.request.urlopen(q, timeout=15); b = r.read()
        return {"_kod": r.status, "_b": b} if yol in ("/kesisim",) and govde is None else dict(json.loads(b), _kod=r.status)
    except urllib.error.HTTPError as e: return {"_kod": e.code}
r = baslat()
try:
    k = ist("/kesisim", anahtar=False)
    bak("sayfa kabuğu anahtarsız açılır, arayüz metinleri ve anahtar betiği gömülü", k["_kod"] == 200 and "/*__" not in k["_b"].decode() and "SUFLOR_EN" in k["_b"].decode() and "X-Suflor-Anahtar" in k["_b"].decode())
    bak("sayfada ham kod/alan adı yok (kaynak adı Türkçe, neden eşlemesi)", "Tazı dosyasına işlendi" in k["_b"].decode() and "karar_yok" in k["_b"].decode())
    bak("veri ucu anahtarsız 401", ist("/kesisim.json", anahtar=False).get("_kod") == 401)
    j = ist("/kesisim.json")
    bak("açık; bugün 1 düzeltme (geri alınan sayılmaz), 1 araştırma", j.get("acik") is True and j["duzeltilen"] == 1 and j["arastirilan"] == 1, j)
    bak("düzeltme satırı: ne, nerede, ne zaman, kaynaklar, geri alınabilir", [x["id"] for x in j["duzeltmeler"]] == [I["a"]] and j["duzeltmeler"][0]["yer"] == "tazi" and j["duzeltmeler"][0]["kaynaklar"] == ["tazi", "vt"] and j["duzeltmeler"][0]["geri"] and "Ornek Firma" in j["duzeltmeler"][0]["ozet"])
    bak("araştırılanlar: yalnız çözülemeyen/bırakılan olmayan", [x["id"] for x in j["arastirmalar"]] == [I["c"]])
    bak("sorulacak: çözülemeyen önemli + neden kodu; bırakılanlar ayrı", [x["id"] for x in j["sorulacak"]] == [I["d"]] and j["sorulacak"][0]["neden"] == "karar_yok" and [x["id"] for x in j["birakilan"]] == [I["e"]])
    bak("kaynaklar: kapalı olan yok, yaş saniye", [x["ad"] for x in j["kaynaklar"]] == ["Proje veritabanı", "Tazı dizini"] and j["kaynaklar"][1]["yas_sn"] == 200000)
    bak("ham metin sızmaz: gerekçe/geri_al ayrıntısı yanıtta yok", "önemsiz" not in json.dumps(j, ensure_ascii=False) and "ornek-firma" not in json.dumps(j))
    bak("geri al: pano kökeni yoksa 403", ist("/kesisim", {"islem": "geri_al", "id": I["a"]}, pano=False).get("_kod") == 403)
    bak("geri al: anahtarsız 401", ist("/kesisim", {"islem": "geri_al", "id": I["a"]}, anahtar=False).get("_kod") == 401)
    bak("geri al: geçersiz kimlik reddedilir", ist("/kesisim", {"islem": "geri_al", "id": "../x"}).get("ok") is False and not os.path.exists(CAGRI))
    g = ist("/kesisim", {"islem": "geri_al", "id": I["a"]})
    bak("geri al: tazi dosya --kim ornek-firma --kapat 12 çağrıldı, ok", g.get("ok") is True and "dosya --kim ornek-firma --kapat 12" in open(CAGRI).read(), g)
    j2 = ist("/kesisim.json")
    bak("geri alınan düzeltme listeden düşer, sayı 0", j2["duzeltilen"] == 0 and j2["duzeltmeler"] == [])
    bak("ikinci geri al: ok değil", ist("/kesisim", {"islem": "geri_al", "id": I["a"]}).get("ok") is False)
    # gizli kip
    r.terminate(); r.wait()
    # tek kullanımlık anahtar
    r = baslat()
    t = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/tek-kullanim", data=b"{}", method="POST", headers={"X-Suflor-Anahtar": anh(), "Origin": f"http://127.0.0.1:{PORT}"}), timeout=5).read())["url"]
    tk = t.split("?t=")[1]; yol = "/kesisim?t=" + tk
    b1 = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{yol}", timeout=5).read().decode(); b2 = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{yol}", timeout=5).read().decode()
    bak("?t= tek kullanımlık: ilk açılışta anahtar gömülü, ikincide boş", anh() in b1 and anh() not in b2)
    r.terminate(); r.wait()
    # geliştirici değil
    r = baslat(False)
    bak("geliştirici değilse sayfa 404, veri ucu kapalı, geri al kapalı", ist("/kesisim", anahtar=False).get("_kod") == 404 and ist("/kesisim.json").get("acik") is False and ist("/kesisim", {"islem": "geri_al", "id": I["a"]}).get("ok") is False)
    r.terminate(); r.wait(); r = baslat(); canli_gizli = ist("/komut", {"tur": "gizli"})
    bak("gizli kipte sayfa 404, veri ucu kapalı, geri al kapalı", ist("/kesisim", anahtar=False).get("_kod") == 404 and ist("/kesisim.json").get("acik") is False and ist("/kesisim", {"islem": "geri_al", "id": I["a"]}).get("ok") is False, canli_gizli)
finally:
    r.terminate()
    try: r.wait(5)
    except Exception: r.kill()
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{'KALDI: ' + ', '.join(hata) if hata else 'hepsi geçti'}"); sys.exit(1 if hata else 0)
