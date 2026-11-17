#!/usr/bin/env python3
# Tazı koşturucu ve istemcisi (11 Kasım; S321: aktarici/tazi-istemci.py + tazi-kos.py + kisi-modeli.py tazi_acik/tazi_var): ayar tazi (geliştiricide açık, beta'da kapalı), gizli kip, aday + hızlı/tam tarama,
# tek tarama aynı anda, kuyruk ≤ 5, tekrar önleme (6 saat), günlük tavan, toplantıda tam tarama bekler, "Tazı, <ad> araştır" kalıbı, yalıtılmış aktarıcıda POST /tazi (anahtarsız 401),
# /status tazi, toplanti-claude.py tazi komutu (kapalı/gizli/tarama başlatma) ve hazırlık bloğunda gizli denetimi; istemci davranışı (Tazı yok / hata / bozuk çıktı / zaman aşımı / önbellek).
# Sahte Tazı hizmeti test/sahte-tazi.py (çağrıları günlüğe yazar); Tazı'nın gerçek kodu ve gerçek ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tazi-kos.py      (kaldı → çıkış 1)
import datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="tazi-kos-"); HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
SAHTE = os.path.join(KOD, "test", "sahte-tazi.py")
FIX = os.path.join(T, "sahte-tazi.json")
json.dump({"kayitlar": [{"id": "nova-teknoloji", "ad": "Nova Teknoloji", "alanlar": ["novatek.test"], "kisiler": []}],
           "ozet": {"nova-teknoloji": "Tazı · Nova Teknoloji — son tarama 1 Kas\nKimlik: deneme"}, "satir": {"nova-teknoloji": "Nova Teknoloji · deneme (son tarama 1 Kas)"}}, open(FIX, "w"))
LOG = os.path.join(T, "tazi-cagri.log"); os.environ.update(SAHTE_TAZI=FIX, SAHTE_TAZI_GUNLUK=LOG); os.environ.pop("TAZI_HIZMET", None)
def tum(): return [json.loads(l) for l in open(LOG, encoding="utf-8")] if os.path.exists(LOG) else []
def satirlar(): return [c for c in tum() if c["islem"] in ("aday_ekle", "tara")]  # tarama ile ilgili çağrılar (eski "alt süreç" sayımı)

# ---------- 1) birim ----------
def ns_kur(ayar, **ek):
    ns = {"os": os, "stat": __import__("stat"), "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "sys": sys, "AYAR": dict({"tazi_yol": SAHTE}, **ayar), "BASE": os.path.join(T, "b" + str(len(os.listdir(T)))),
          "print": lambda *a, **k: LOGP.append(" ".join(str(x) for x in a)), "_t": lambda tr, en: tr, "gizli_acik": lambda: False, "toplanti_suruyor": lambda: False,
          "STATE": {}}
    os.makedirs(ns["BASE"], exist_ok=True); ns.update(ek)
    for f in ("tazi-istemci.py", "kisi-modeli.py", "tazi-kos.py"): exec(compile(open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read(), f, "exec"), ns)
    return ns
LOGP = []
os.environ["SUFLOR_TZK_DONGU_YOK"] = "1"
N = ns_kur({"tazi": False})
ok("ayar tazi kapalı: tazi_acik False, tazi_var False, kayıt/özet boş, istek 'kapali' ve hizmet hiç çağrılmaz", N["tazi_acik"]() is False and N["tazi_var"]() is False and N["tazi_kayitlar"]("Nova Teknoloji") == []
   and N["tazi_ozet"]("Nova Teknoloji") is None and N["tazi_kos"]("Nova Teknoloji")["durum"] == "kapali" and not tum())
ok("ayar yok + gelistirici_mi False (beta) → kapalı; True → açık; gelistirici_mi tanımsız → açık",
   ns_kur({}, gelistirici_mi=lambda: False)["tazi_acik"]() is False and ns_kur({}, gelistirici_mi=lambda: True)["tazi_acik"]() is True and ns_kur({})["tazi_acik"]() is True)
ok("ayar tazi: true beta'da da açar (elle)", ns_kur({"tazi": True}, gelistirici_mi=lambda: False)["tazi_acik"]() is True)
G = ns_kur({"tazi": True}, gizli_acik=lambda: True)
ok("gizli kipte istek 'gizli', komut cevabı None (Claude'a gider), alt süreç yok", G["tazi_kos"]("Nova Teknoloji")["durum"] == "gizli" and G["tazi_komut_cevap"]("Tazı, Nova Teknoloji araştır") is None and not satirlar())

K = ns_kur({"tazi": True})
r = K["tazi_kos"]("Örnek Danışmanlık", "ornek-danisma.test", "hizli", "brifing")
ok("hızlı istek kuyruğa alınır, hemen döner", r["ok"] and r["durum"] == "basladi" and len(K["TZK"]["kuyruk"]) == 1 and not satirlar())
o = K["tzk_isle"]()
ok("koşum: önce aday_ekle (ad, alan, neden), sonra tara (kayıt kimliğiyle, hızlı)", o and satirlar() == [{"islem": "aday_ekle", "ad": "Örnek Danışmanlık", "neden": "brifing", "alan": "ornek-danisma.test"},
   {"islem": "tara", "kim": "ornek-danismanlik", "hizli": True}], satirlar())
ok("günlükte TAZI KOŞ satırları var, ad yazılmaz (kayıt kimliği)", any(l.startswith("TAZI KOŞ: başladı (hizli, kayıt") for l in LOGP) and not any("Örnek" in l for l in LOGP), LOGP)
ok("sonuç durumu: ok, kayıt, kip", K["TZK"]["sonuc"]["durum"] == "ok" and K["TZK"]["sonuc"]["kip"] == "hizli" and K["tazi_view"]()["bugun"] == 1)
ok("aynı ad 6 saat içinde tekrar istenmez (zaten)", K["tazi_kos"]("örnek danışmanlık", None, "hizli")["durum"] == "zaten")
ok("tam tarama da hızlıdan sonra istenebilir (kip farklı)", K["tazi_kos"]("Örnek Danışmanlık", None, "tam")["durum"] in ("basladi", "bekliyor"))
K["tzk_isle"]()
ok("tam koşum hizli=false", satirlar()[-1] == {"islem": "tara", "kim": "ornek-danismanlik", "hizli": False}, satirlar()[-1:])
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
ok("toplantı bitince tam koşar", x2 and x2["kip"] == "tam" and satirlar()[-1] == {"islem": "tara", "kim": "uzak-tam-firma", "hizli": False})
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
# rapor listesi + okuma (12 Kasım; S321: liste/okuma Tazı hizmetinde — süzme ve 200 KB sınırı orada sınanır; burada istemci tarafı)
RAP = [{"tur": "kisi", "dosya": "ad-soyad-20261111.md", "t": 1_800_000_500}, {"tur": "toplanti", "dosya": "toplanti-2026-11-11.md", "t": 1_800_000_400},
       {"tur": "tazi", "dosya": "tazi-20261111.md", "t": 1_800_000_300}, {"tur": "tazi", "dosya": "../gizli.md", "t": 1_800_000_200}]
d_ = json.load(open(FIX)); d_.update(raporlar=RAP, rapor_metin={"tazi-20261111.md": "# Rapor\n\nİçerik [bağ](https://ornek.test)"}); json.dump(d_, open(FIX, "w"))
R = ns_kur({"tazi": True}); ls = R["tazi_raporlar"]()
ok("rapor listesi: hizmetten, sırası korunur, geçersiz ad süzülür", [x["dosya"] for x in ls] == ["ad-soyad-20261111.md", "toplanti-2026-11-11.md", "tazi-20261111.md"] and [x["tur"] for x in ls] == ["kisi", "toplanti", "tazi"], ls)
ok("tazi_view raporlar alanı", R["tazi_view"]()["raporlar"] == ls)
n_ = len(tum()); R["tazi_raporlar"](); R["tazi_view"]()
ok("rapor listesi önbellekte (pano /status yoklaması her seferinde hizmeti çağırmaz)", len(tum()) == n_)
g = R["tazi_rapor_oku"]("tazi-20261111.md")
ok("rapor oku: doğru dosya, metin, tür", g["ok"] and g["dosya"] == "tazi-20261111.md" and g["tur"] == "tazi" and "İçerik" in g["metin"] and g["t"] > 0, g)
n_ = len(tum())
ok("rapor oku: .. / yol / boş / uzantı istemcide reddedilir (hizmete gitmez)", all(not R["tazi_islem"]({"islem": "rapor", "dosya": d})["ok"] for d in ("../gizli.md", "..", "a/../../gizli.md", "/etc/passwd", "tazi-20261111.txt", "", None, ".gizli.md", "x..md")) and len(tum()) == n_)
ok("rapor oku: hizmette yoksa 'yok'", R["tazi_rapor_oku"]("yok-20260101.md")["durum"] == "yok")
os.environ["SAHTE_TAZI_HATA"] = "rapor_oku:buyuk"; ok("rapor oku: hizmet 'buyuk' derse 'buyuk'", R["tazi_rapor_oku"]("tazi-20261111.md")["durum"] == "buyuk"); del os.environ["SAHTE_TAZI_HATA"]
ok("rapor: ayar tazi kapalıyken liste boş, okuma 'kapali'", ns_kur({"tazi": False})["tazi_raporlar"]() == [] and ns_kur({"tazi": False})["tazi_rapor_oku"]("tazi-20261111.md")["durum"] == "kapali")
ok("rapor: gizli kipte liste boş, okuma 'gizli'", ns_kur({"tazi": True}, gizli_acik=lambda: True)["tazi_raporlar"]() == [] and ns_kur({"tazi": True}, gizli_acik=lambda: True)["tazi_rapor_oku"]("tazi-20261111.md")["durum"] == "gizli")

# istemci davranışı (S321): Tazı var / yok / hata / bozuk çıktı / zaman aşımı / önbellek
V = ns_kur({"tazi": True})
ok("Tazı var: tazi_var True, kayıt ve özet hizmetten", V["tazi_var"]() is True and [k["id"] for k in V["tazi_kayitlar"]("yarın Nova Teknoloji ile görüşme")] == ["nova-teknoloji"]
   and V["tazi_ozet"]("nova-teknoloji").startswith("Tazı · Nova Teknoloji") and V["tazi_satir"]("nova-teknoloji").startswith("Nova Teknoloji ·"))
n_ = len(tum()); V["tazi_kayitlar"]("yarın Nova Teknoloji ile görüşme"); V["tazi_var"]()
ok("okuyan çağrılar önbellekte: aynı soru hizmeti yeniden çağırmaz", len(tum()) == n_)
V["tazi_yenile"](); V["tazi_var"](); ok("tazi_yenile önbelleği boşaltır", len(tum()) == n_ + 1)
ok("girdi stdin'den gider: hizmet metni JSON'dan aldı", any(c["islem"] == "eslesen_kayitlar" and c.get("metin") == "yarın Nova Teknoloji ile görüşme" for c in tum()))
Y = ns_kur({"tazi": True, "tazi_yol": os.path.join(T, "yok", "tazi_hizmet.py")}); LOGP.clear(); n_ = len(tum())
ok("Tazı yok (beta, Tazı'sız kurulum): tazi_yol None, tazi_var False, kayıt [], özet None, tarama 'yok', rapor boş, günlükte hata yok",
   Y["tazi_yol"]() is None and Y["tazi_var"]() is False and Y["tazi_kayitlar"]("Nova Teknoloji") == [] and Y["tazi_ozet"]("Nova Teknoloji") is None
   and Y["tazi_kos"]("Nova Teknoloji")["durum"] == "yok" and Y["tazi_raporlar"]() == [] and Y["tazi_cagir"]("durum", {}, ayar=Y["AYAR"]) == {"ok": False, "hata": "tazi_yok"}
   and not any("TAZI" in l for l in LOGP) and len(tum()) == n_, LOGP)
os.environ["TAZI_HIZMET"] = SAHTE; ok("ortam TAZI_HIZMET ayardan önce gelir", Y["tazi_yol"]() == SAHTE); del os.environ["TAZI_HIZMET"]
os.environ["SAHTE_TAZI_HATA"] = "eslesen_kayitlar:ic_hata"; H = ns_kur({"tazi": True}); LOGP.clear()
ok("hizmet hata dönerse: kayıt [] ve günlüğe tür bir kez", H["tazi_kayitlar"]("Nova Teknoloji") == [] and H["tazi_kayitlar"]("başka Nova Teknoloji") == []
   and [l for l in LOGP if l.startswith("TAZI:")] == ["TAZI: eslesen_kayitlar hatası (ic_hata)"], LOGP)
del os.environ["SAHTE_TAZI_HATA"]
os.environ["SAHTE_TAZI_BOZUK"] = "1"; Bz = ns_kur({"tazi": True})
ok("JSON olmayan çıktı → hata 'cikti', çağıran çökmez", Bz["tazi_cagir"]("durum", {}, ayar=Bz["AYAR"])["hata"] == "cikti" and Bz["tazi_var"]() is False)
del os.environ["SAHTE_TAZI_BOZUK"]
os.environ["SAHTE_TAZI_UYKU"] = "3"; Zm = ns_kur({"tazi": True}); t0 = time.time()
ok("zaman aşımı → 'zaman_asimi', bekleme sınırlı", Zm["tazi_cagir"]("durum", {}, zaman=1, ayar=Zm["AYAR"]) == {"ok": False, "hata": "zaman_asimi"} and time.time() - t0 < 2.5)
del os.environ["SAHTE_TAZI_UYKU"]
os.environ["SAHTE_TAZI_HATA"] = "tara:tarama"; Hk = ns_kur({"tazi": True}); Hk["tazi_kos"]("Hatalı Tarama Firma"); Hk["tzk_isle"]()
ok("tarama hatası: sonuç 'hata', günlükte işlem ve kod (ad yok)", Hk["TZK"]["sonuc"]["durum"] == "hata" and any(l.startswith("TAZI KOŞ: tara hata (tarama)") for l in LOGP) and not any("Hatalı" in l for l in LOGP), LOGP[-3:])
del os.environ["SAHTE_TAZI_HATA"]

# ---------- 2) yalıtılmış aktarıcı ----------
del os.environ["SUFLOR_TZK_DONGU_YOK"]
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
os.makedirs(os.path.join(T, "proje"), exist_ok=True)
class Uc:
    def __init__(s, ad, **ayar):
        s.port = bos_port(8795); s.d = os.path.join(T, ad); os.makedirs(s.d); s.log = os.path.join(T, ad + ".log"); yol = os.path.join(T, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Ayşe Deneme", "port": s.port, "uygulama": T, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "yok"), "claude": "/yok/claude", "konus_on_ac": False,
                        "pocket_python": "/yok/python", "pocket_hf": "/yok", "kod": T, "tazi_yol": SAHTE}, **ayar), open(yol, "w"))
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=T, stdout=open(s.log, "w"), stderr=subprocess.STDOUT,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"))
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
    ok("aktarıcı kendi döngüsüyle koşturdu: sonuç ok, bugün 1", st["son"] and st["son"]["durum"] == "ok" and st["bugun"] == 1 and {"islem": "tara", "kim": "nova-yeni-firma", "hizli": True} in satirlar(), st)
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
    ok("/status tazi.raporlar: hizmetin listesi", [x["dosya"] for x in A.istek("/status")["tazi"]["raporlar"]][:2] == ["ad-soyad-20261111.md", "toplanti-2026-11-11.md"])
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
    ok("tc tazi taraması koştu", {"islem": "tara", "kim": "bambaska-yeni-firma", "hizli": True} in satirlar(), satirlar()[-3:])
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
