#!/usr/bin/env python3
# Tazı koşturucu (11 Kasım; aktarici/tazi-kos.py + kisi-modeli.py tazi_acik/tazi_mod): ayar tazi (geliştiricide açık, beta'da kapalı), gizli kip, aday + hızlı/tam tarama alt süreci,
# tek tarama aynı anda, kuyruk ≤ 5, tekrar önleme (6 saat), günlük tavan, toplantıda tam tarama bekler, "Tazı, <ad> araştır" kalıbı, yalıtılmış aktarıcıda POST /tazi (anahtarsız 401),
# /status tazi, toplanti-claude.py tazi komutu (kapalı/gizli/tarama başlatma) ve hazırlık bloğunda gizli denetimi. Sahte tazi.py (argümanları günlüğe yazar); gerçek ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tazi-kos.py      (kaldı → çıkış 1)
import datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="tazi-kos-"); HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
SAHTE = '''import os, sys, time
def liste_oku(arg=None, dizin=None): return [{"id": "nova-teknoloji", "ad": "Nova Teknoloji", "kisiler": [], "alanlar": ["novatek.test"]}]
def kayit_bul(liste, q):
    q = str(q).lower(); return next((k for k in liste if q in k["ad"].lower() or q in k["alanlar"] or q == k["id"]), None)
def veri_dizin(dizin=None): return os.environ["TAZI_DIR"]
def metinden_kayitlar(metin, liste=None, dizin=None, en_cok=3): return []
def ozet_metni(x, *a, **k): return "Tazı · Nova Teknoloji — son tarama 1 Kas\\nKimlik: deneme" if "nova teknoloji" in str(x).lower() else None
if __name__ == "__main__":
    open(os.environ["FAKE_TAZI_LOG"], "a").write(" ".join(sys.argv[1:]) + "\\n")
    time.sleep(float(os.environ.get("FAKE_TAZI_UYKU", "0")))
'''
KODK = os.path.join(T, "kod"); os.makedirs(KODK); open(os.path.join(KODK, "tazi.py"), "w").write(SAHTE)
LOG = os.path.join(T, "tazi-argv.log"); os.environ["FAKE_TAZI_LOG"] = LOG
def satirlar(): return open(LOG, encoding="utf-8").read().splitlines() if os.path.exists(LOG) else []

# ---------- 1) birim ----------
def ns_kur(ayar, **ek):
    ns = {"os": os, "stat": __import__("stat"), "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "sys": sys, "AYAR": dict({"kod": KODK}, **ayar), "BASE": os.path.join(T, "b" + str(len(os.listdir(T)))),
          "print": lambda *a, **k: LOGP.append(" ".join(str(x) for x in a)), "_t": lambda tr, en: tr, "gizli_acik": lambda: False, "toplanti_suruyor": lambda: False,
          "STATE": {}}
    os.makedirs(ns["BASE"], exist_ok=True); ns.update(ek)
    for f in ("kisi-modeli.py", "tazi-kos.py"): exec(compile(open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read(), f, "exec"), ns)
    return ns
LOGP = []
os.environ["SUFLOR_TZK_DONGU_YOK"] = "1"
N = ns_kur({"tazi": False})
ok("ayar tazi kapalı: tazi_acik False, tazi_mod None, tazi_var False, istek 'kapali' ve alt süreç yok", N["tazi_acik"]() is False and N["tazi_mod"]() is None and N["tazi_var"]() is False
   and N["tazi_kos"]("Nova Teknoloji")["durum"] == "kapali" and not satirlar())
ok("ayar yok + gelistirici_mi False (beta) → kapalı; True → açık; gelistirici_mi tanımsız → açık",
   ns_kur({}, gelistirici_mi=lambda: False)["tazi_acik"]() is False and ns_kur({}, gelistirici_mi=lambda: True)["tazi_acik"]() is True and ns_kur({})["tazi_acik"]() is True)
ok("ayar tazi: true beta'da da açar (elle)", ns_kur({"tazi": True}, gelistirici_mi=lambda: False)["tazi_acik"]() is True)
G = ns_kur({"tazi": True}, gizli_acik=lambda: True)
ok("gizli kipte istek 'gizli', komut cevabı None (Claude'a gider), alt süreç yok", G["tazi_kos"]("Nova Teknoloji")["durum"] == "gizli" and G["tazi_komut_cevap"]("Tazı, Nova Teknoloji araştır") is None and not satirlar())

K = ns_kur({"tazi": True})
r = K["tazi_kos"]("Örnek Danışmanlık", "ornek-danisma.test", "hizli", "brifing")
ok("hızlı istek kuyruğa alınır, hemen döner", r["ok"] and r["durum"] == "basladi" and len(K["TZK"]["kuyruk"]) == 1 and not satirlar())
o = K["tzk_isle"]()
ok("koşum: önce aday (ad, alan, neden), sonra tara --hizli", o and satirlar() == ["aday --ad Örnek Danışmanlık --neden brifing --alan ornek-danisma.test", "tara --kim Örnek Danışmanlık --hizli"], satirlar())
ok("günlükte TAZI KOŞ satırları var, ad yazılmaz (kayıt kimliği)", any(l.startswith("TAZI KOŞ: başladı (hizli, kayıt") for l in LOGP) and not any("Örnek" in l for l in LOGP), LOGP)
ok("sonuç durumu: ok, kayıt, kip", K["TZK"]["sonuc"]["durum"] == "ok" and K["TZK"]["sonuc"]["kip"] == "hizli" and K["tazi_view"]()["bugun"] == 1)
ok("aynı ad 6 saat içinde tekrar istenmez (zaten)", K["tazi_kos"]("örnek danışmanlık", None, "hizli")["durum"] == "zaten")
ok("tam tarama da hızlıdan sonra istenebilir (kip farklı)", K["tazi_kos"]("Örnek Danışmanlık", None, "tam")["durum"] in ("basladi", "bekliyor"))
K["tzk_isle"]()
ok("tam koşum --hizli'siz", satirlar()[-1] == "tara --kim Örnek Danışmanlık")
ok("tam yapılmışsa hızlı da 'zaten'", K["tazi_kos"]("Örnek Danışmanlık", None, "hizli")["durum"] == "zaten")
# tek tarama aynı anda
K["TZK"]["calisiyor"] = {"k": "x"}; K["tazi_kos"]("Yalı Teknoloji"); ok("çalışan varken ikinci başlamaz", K["tzk_isle"]() is None and len(K["TZK"]["kuyruk"]) == 1); K["TZK"]["calisiyor"] = None; K["TZK"]["kuyruk"].clear()
# günlük tavan + kuyruk sınırı
Q = ns_kur({"tazi": True, "tazi_gunluk": 3})
d = [Q["tazi_kos"](f"Firma {x}")["durum"] for x in ("Alfa", "Beta", "Gama", "Delta")]
ok("günlük tavan (3): dördüncü istek 'tavan'", d == ["basladi", "basladi", "basladi", "tavan"], d)
Q2 = ns_kur({"tazi": True}); d = [Q2["tazi_kos"](f"Firma {x}")["durum"] for x in ("A1a", "B1b", "C1c", "D1d", "E1e", "F1f")]
ok("kuyruk en çok 5: altıncı 'dolu'", d[:5] == ["basladi"] * 5 and d[5] == "dolu", d)
ok("kısa ad (< 3) reddedilir", Q2["tazi_kos"]("ab")["durum"] == "bos")
# toplantıda tam bekler, hızlı gider
tm = {"v": True}; W = ns_kur({"tazi": True}, toplanti_suruyor=lambda: tm["v"])
a1 = W["tazi_kos"]("Uzak Tam Firma", None, "tam"); a2 = W["tazi_kos"]("Uzak Hızlı Firma", None, "hizli")
ok("toplantıda tam 'bekliyor', hızlı 'basladi'", a1["durum"] == "bekliyor" and a2["durum"] == "basladi")
n0 = len(satirlar()); x1 = W["tzk_isle"](); n1 = len(satirlar())
ok("toplantı sürerken yalnız hızlı koşar (tam kuyrukta kalır)", x1 and x1["kip"] == "hizli" and n1 == n0 + 2 and W["tzk_isle"]() is None and len(W["TZK"]["kuyruk"]) == 1)
tm["v"] = False; x2 = W["tzk_isle"]()
ok("toplantı bitince tam koşar", x2 and x2["kip"] == "tam" and satirlar()[-1] == "tara --kim Uzak Tam Firma")
# gizli açılınca kuyruk boşalır
gz = {"v": False}; Z = ns_kur({"tazi": True}, gizli_acik=lambda: gz["v"]); Z["tazi_kos"]("Gizli Deneme Firma"); gz["v"] = True; n0 = len(satirlar())
ok("kuyruktayken gizli kip açılırsa hiçbir şey koşmaz, kuyruk boşalır", Z["tzk_isle"]() is None and not Z["TZK"]["kuyruk"] and len(satirlar()) == n0)
# komut kalıbı
tk = K["tazi_komut"]
ok("kalıp: 'Tazı, X araştır / iz sür / izle / izlemeye al / incele'", [tk(m) for m in ("Tazı, Nova Teknoloji araştır", "Tazı Nova Teknoloji iz sür", "tazi: Nova Teknoloji izle", "Tazı, Nova Teknoloji'yi araştır", "Tazı, novatek.test sitesini incele", "Tazı, Nova Teknoloji izlemeye al")]
   == ["Nova Teknoloji", "Nova Teknoloji", "Nova Teknoloji", "Nova Teknoloji", "novatek.test sitesini", "Nova Teknoloji"], [tk(m) for m in ("Tazı, Nova Teknoloji araştır", "Tazı, novatek.test sitesini incele")])
ok("kalıp: başka cümleler komut değil", all(tk(m) is None for m in ("Nova Teknoloji'yi araştır", "Tazı nedir", "Roxane, Nova Teknoloji araştır", "Tazı, bana bir şey anlat", "Tazı, https://x.test araştır", "Tazı, ab araştır")))
c = ns_kur({"tazi": True})["tazi_komut_cevap"]("Tazı, Nova Teknoloji'yi araştır")
ok("komut cevabı: toplantı dışında tam tarama kuyruğa, teyit cümlesi", c and "iz sürüyor" in c)
C2 = ns_kur({"tazi": True}, toplanti_suruyor=lambda: True); C2["tazi_komut_cevap"]("Tazı, Yeni Firma Adı izle")
ok("komut toplantıdayken hızlı kuyruğa", C2["TZK"]["kuyruk"][0]["kip"] == "hizli" and C2["TZK"]["kuyruk"][0]["neden"] == "konus")
ok("kapalıyken komut cevabı None", ns_kur({"tazi": False})["tazi_komut_cevap"]("Tazı, Nova Teknoloji araştır") is None)
ok("POST /tazi birimi: durum ve tara", K["tazi_islem"]({"islem": "durum"})["ok"] and K["tazi_islem"]({"islem": "tara", "kim": "Birim Deneme Firma"})["ok"] and K["tazi_islem"]({"islem": "x"})["ok"] is False)
# rapor listesi + okuma (12 Kasım)
RD = os.path.join(T, "tazi-veri"); os.makedirs(os.path.join(RD, "rapor")); os.environ["TAZI_DIR"] = RD
def _rap(ad, metin="# Rapor\n\nİçerik [bağ](https://ornek.test)", t=None):
    y = os.path.join(RD, "rapor", ad); open(y, "w", encoding="utf-8").write(metin)
    if t: os.utime(y, (t, t))
now = int(time.time())
_rap("tazi-20261110.md", t=now - 300); _rap("tazi-20261111.md", t=now - 200); _rap("tazi-son.md", t=now - 10); _rap("toplanti-2026-11-11.md", t=now - 100); _rap("toplanti-son.md", t=now - 5)
_rap("ad-soyad-20261111.md", t=now - 50); _rap("DIZIN.md", t=now); _rap("a1-20261101.md", t=now - 900); _rap("a2-20261101.md", t=now - 800); _rap("a3-20261101.md", t=now - 700)
os.makedirs(os.path.join(RD, "rapor", "alt.md")); open(os.path.join(RD, "gizli.md"), "w").write("dışarıda")
R = ns_kur({"tazi": True}); ls = R["tazi_raporlar"]()
ok("rapor listesi: ≤ 5, yeniden eskiye, -son.md ve DIZIN.md yok, tür doğru", [x["dosya"] for x in ls] == ["ad-soyad-20261111.md", "toplanti-2026-11-11.md", "tazi-20261111.md", "tazi-20261110.md", "a3-20261101.md"]
   and [x["tur"] for x in ls] == ["kisi", "toplanti", "tazi", "tazi", "kisi"], ls)
ok("tazi_view raporlar alanı", R["tazi_view"]()["raporlar"] == ls)
g = R["tazi_rapor_oku"]("tazi-20261111.md")
ok("rapor oku: doğru dosya, metin, tür", g["ok"] and g["dosya"] == "tazi-20261111.md" and g["tur"] == "tazi" and "İçerik" in g["metin"] and g["t"] > 0, g)
ok("rapor oku: .. / yol / dizin / dosya yok reddedilir", all(not R["tazi_islem"]({"islem": "rapor", "dosya": d})["ok"] for d in ("../gizli.md", "..", "a/../../gizli.md", "/etc/passwd", "alt.md", "yok-20260101.md", "tazi-20261111.txt", "", None, ".gizli.md", "x..md")))
_rap("buyuk-20261111.md", "x" * (200 * 1024 + 1), t=now - 5000); ok("rapor oku: 200 KB üstü reddedilir", R["tazi_rapor_oku"]("buyuk-20261111.md")["durum"] == "buyuk")
ok("rapor: ayar tazi kapalıyken liste boş, okuma 'kapali'", ns_kur({"tazi": False})["tazi_raporlar"]() == [] and ns_kur({"tazi": False})["tazi_rapor_oku"]("tazi-20261111.md")["durum"] == "kapali")
ok("rapor: gizli kipte liste boş, okuma 'gizli'", ns_kur({"tazi": True}, gizli_acik=lambda: True)["tazi_raporlar"]() == [] and ns_kur({"tazi": True}, gizli_acik=lambda: True)["tazi_rapor_oku"]("tazi-20261111.md")["durum"] == "gizli")

# ---------- 2) yalıtılmış aktarıcı ----------
del os.environ["SUFLOR_TZK_DONGU_YOK"]
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano")); shutil.copy(os.path.join(KODK, "tazi.py"), T)
os.makedirs(os.path.join(T, "proje"), exist_ok=True)
class Uc:
    def __init__(s, ad, **ayar):
        s.port = bos_port(8795); s.d = os.path.join(T, ad); os.makedirs(s.d); s.log = os.path.join(T, ad + ".log"); yol = os.path.join(T, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Ayşe Deneme", "port": s.port, "uygulama": T, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "yok"), "claude": "/yok/claude", "konus_on_ac": False,
                        "pocket_python": "/yok/python", "pocket_hf": "/yok", "kod": T}, **ayar), open(yol, "w"))
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=T, stdout=open(s.log, "w"), stderr=subprocess.STDOUT,
                               env=dict(os.environ, TAZI_DIR=RD, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", FAKE_TAZI_UYKU="0"))
        for _ in range(80):
            if os.path.exists(os.path.join(s.d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); s.h = {"X-Suflor-Anahtar": open(os.path.join(s.d, "kart-anahtari.txt")).read().strip()}
    def istek(s, yol, v=None, h=True):
        r = urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=(json.dumps(v).encode() if v is not None else None), headers=(s.h if h else {}))
        return json.loads(urllib.request.urlopen(r, timeout=30).read())
    def metin(s): return open(s.log, encoding="utf-8").read()
    def kapat(s): s.p.terminate(); s.p.wait(timeout=10)
def tc(u, *args, ayar=None):
    return subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", u.d, "--relay", f"http://127.0.0.1:{u.port}"] + list(args), capture_output=True, text=True, timeout=60, cwd=T,
                          env=dict(os.environ, SUFLOR_AYAR=os.path.join(T, os.path.basename(u.d) + ".json"))).stdout
def kod_ac_u(u, yol, v, ork=None):  # pano kökeniyle (Origin) ya da kökensiz POST; (kod, json)
    r = urllib.request.Request(f"http://127.0.0.1:{u.port}{yol}", data=json.dumps(v).encode(), headers=dict(u.h, Origin=f"http://127.0.0.1:{u.port}") if ork is None else dict(u.h, **({"Origin": ork} if ork else {})))
    try: x = urllib.request.urlopen(r, timeout=30); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
try:
    A = Uc("a", tazi=True, tazi_gunluk=5)
    ok("açılışta hata yok", "Traceback" not in A.metin())
    try: A.istek("/tazi", {"islem": "durum"}, h=False); kod = 200
    except urllib.error.HTTPError as e: kod = e.code
    ok("/tazi anahtarsız 401", kod == 401, kod)
    ok("/status tazi alanı: açık, kuyruk 0", A.istek("/status").get("tazi", {}).get("acik") is True and A.istek("/status")["tazi"]["kuyruk"] == 0)
    r = A.istek("/tazi", {"islem": "tara", "kim": "Nova Yeni Firma", "alan": "novayeni.test", "kip": "hizli", "neden": "toplanti"})
    ok("/tazi tara: kabul (basladi)", r.get("ok") and r.get("durum") == "basladi", r)
    n0 = len(satirlar())
    for _ in range(30):
        if A.istek("/status")["tazi"]["son"]: break
        time.sleep(1)
    st = A.istek("/status")["tazi"]
    ok("aktarıcı kendi döngüsüyle koşturdu: sonuç ok, bugün 1", st["son"] and st["son"]["durum"] == "ok" and st["bugun"] == 1 and any(l.startswith("tara --kim Nova Yeni Firma --hizli") for l in satirlar()), st)
    ok("günlükte TAZI KOŞ, ad yok", "TAZI KOŞ: bitti" in A.metin() and "Nova Yeni" not in A.metin())
    def kod_ac(yol, v, ork=None):
        r = urllib.request.Request(f"http://127.0.0.1:{A.port}{yol}", data=json.dumps(v).encode(), headers=dict(A.h, **({"Origin": ork} if ork else {})))
        try: u = urllib.request.urlopen(r, timeout=30); return u.status, json.loads(u.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    pk = f"http://127.0.0.1:{A.port}"
    k1, r1 = kod_ac("/tazi", {"islem": "rapor", "dosya": "tazi-20261111.md"}, pk)
    ok("/tazi rapor (pano kökeni): metin gelir", k1 == 200 and r1.get("ok") and "İçerik" in r1.get("metin", ""), (k1, str(r1)[:100]))
    k2, r2 = kod_ac("/tazi", {"islem": "rapor", "dosya": "tazi-20261111.md"})
    ok("/tazi rapor köken yok (pano değil): 403", k2 == 403 and not r2.get("ok"), (k2, r2))
    k3, r3 = kod_ac("/tazi", {"islem": "rapor", "dosya": "../gizli.md"}, pk)
    ok("/tazi rapor '..' reddi", k3 == 200 and not r3.get("ok") and "dışarıda" not in json.dumps(r3), (k3, r3))
    ok("/status tazi.raporlar: liste var, -son.md yok", [x["dosya"] for x in A.istek("/status")["tazi"]["raporlar"]][:2] == ["ad-soyad-20261111.md", "toplanti-2026-11-11.md"] and not any(x["dosya"].endswith("-son.md") for x in A.istek("/status")["tazi"]["raporlar"]))
    ok("günlükte rapor adı/metni yok", "ad-soyad" not in A.metin() and "İçerik" not in A.metin())
    A.istek("/komut", {"tur": "gizli"}); n0 = len(satirlar())
    ok("gizli kipte /status raporlar boş, /tazi rapor 'gizli'", A.istek("/status")["tazi"]["raporlar"] == [] and kod_ac("/tazi", {"islem": "rapor", "dosya": "tazi-20261111.md"}, pk)[1].get("durum") == "gizli")
    A.istek("/komut", {"tur": "gizli"}); A.istek("/komut", {"tur": "gizli"}); n0 = len(satirlar())
    gz = A.istek("/tazi", {"islem": "tara", "kim": "Gizli Bir Firma"}); o4 = tc(A, "tazi", "Nova Teknoloji"); hg = tc(A, "hazirlik", "--kim", "Nova Teknoloji")
    ok("gizli kipte: /tazi 'gizli', tc tazi sessiz, hazırlıkta Tazı bölümü yok, alt süreç yok", gz.get("durum") == "gizli" and "gizli toplantı" in o4 and "## Tazı:" not in hg and len(satirlar()) == n0, (gz, o4[:80]))
    A.istek("/komut", {"tur": "gizli"}); h0 = tc(A, "hazirlik", "--kim", "Nova Teknoloji")
    ok("gizli kapanınca hazırlıkta Tazı bölümü gelir (sahte özet)", "## Tazı: son gelişmeler" in h0 and "Kimlik: deneme" in h0, h0[:300])
    # toplanti-claude.py: dosyası olmayan ad → tarama başlatır
    n0 = len(satirlar()); out = tc(A, "tazi", "Bambaşka Yeni Firma")
    ok("tc tazi: dosya yok → hızlı tarama başlatıldı, 'iz sürüyor' yönergesi, ad sayılmadı (30 sn sonra yeniden sorulabilir)", "Tazı iz sürüyor" in out and "dosya yok" in out, out)
    time.sleep(8)
    ok("tc tazi taraması koştu", any(l.startswith("tara --kim Bambaşka Yeni Firma --hizli") for l in satirlar()), satirlar()[-3:])
    out2 = tc(A, "tazi", "Bambaşka Yeni Firma")
    ok("tc tazi ikinci çağrı: ad hâlâ sorulabilir, ikinci tarama başlamaz (zaten)", "zaten soruldu" not in out2 and "Tazı iz sürüyor" not in out2 and "dosya yok" in out2, out2)
    A.kapat()
    B = Uc("b", tazi=False)
    ok("ayar tazi kapalı: /status tazi.acik False; /tazi tara 'kapali'", B.istek("/status")["tazi"]["acik"] is False and B.istek("/tazi", {"islem": "tara", "kim": "Nova Yeni Firma"}).get("durum") == "kapali")
    ok("ayar tazi kapalı: /status raporlar boş, /tazi rapor 'kapali'", B.istek("/status")["tazi"]["raporlar"] == [] and kod_ac_u(B, "/tazi", {"islem": "rapor", "dosya": "tazi-20261111.md"})[1].get("durum") == "kapali")
    n0 = len(satirlar()); o3 = tc(B, "tazi", "Nova Teknoloji")
    ok("tc tazi: kapalıyken sessiz ('Tazı kapalı'), tarama yok", "Tazı kapalı" in o3 and len(satirlar()) == n0, o3)
    h = tc(B, "hazirlik", "--kim", "Nova Teknoloji", "--katilimci", "Nova Teknoloji")
    ok("hazırlık: ayar kapalıyken Tazı bölümü yok", "## Tazı:" not in h and "Hazırlık" in h, h[:200])
    B.kapat()
    C = Uc("c", tazi=True)
    h2 = tc(C, "hazirlik", "--kim", "Nova Teknoloji")
    ok("hazırlık: açıkken Tazı bölümü var", "## Tazı: son gelişmeler" in h2 and "Traceback" not in h2)
    C.kapat()
finally:
    for u in ("A", "B", "C"):
        try: globals()[u].p.kill()
        except Exception: pass
print(f"\n{'TAMAM' if not HATA else 'KALDI'} — {len(HATA)} başarısız"); sys.exit(1 if HATA else 0)
