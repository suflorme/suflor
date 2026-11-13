#!/usr/bin/env python3
# Araştırmalar satırı eylemleri (13 Kasım): aktarici/web-arastirma.py arastirma_islem / arastirma_view(gizli) / ar_hedefler — Gizle (dosya silinmez, gizlenen.jsonl, geri alınır),
# İlet → talimat hedefinin gelen kutusu (talimat.py _gelen_yaz; toplanti-claude.py gelen bağlama basar), İlet → asistan (konus_yazili ek=veri bloğu; gizli kipte yok), İş olarak ekle (_is_kaydet → Kararlar ve işler; is-bag.jsonl).
# Sonra yalıtılmış aktarıcıda POST /arastirma (yalnız pano: Origin + anahtar) ve GET /arastirma?gizli=1. Gerçek ağa, gerçek gelen kutusuna, Claude'a gidilmez.
# aktarici/web-arastirma.py (kart eylemleri), relay.py /arastirma ya da pano Araştırmalar satırı değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/arastirma-eylem.py      (kaldı → çıkış 1)
import json, os, re, shutil, subprocess, sys, tempfile, threading, time, datetime, urllib.request, urllib.error, importlib.util
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD); T = tempfile.mkdtemp(prefix="areylem-"); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
KAYIT = {"surum": 1, "at": "2026-11-12T10:00:00+03:00", "kanal": "kutu", "durum": "ok", "sure_sn": 40, "maliyet": 0.04, "sorgu_sayisi": 4, "sayfa_sayisi": 3, "kaynak_sayisi": 2,
         "bagimsiz_kaynak": 2, "sorgular": [], "sesli": "Orbitek 2014'te kuruldu; iki kaynak aynı şeyi söylüyor.", "metin": "Orbitek 2014'te kuruldu ([Site](https://orbitek.example/a), 01.10.2026).\n\n## Çelişkiler\nyok",
         "kaynaklar": [{"url": "https://orbitek.example/a", "baslik": "Şirket sitesi", "tarih": "01.10.2026", "tur": "birincil"}, {"url": "https://ajans.example/h", "baslik": "Ajans", "tarih": "", "tur": "ikincil"}],
         "yerel": [], "uyari": [], "hata": None}
def kayit_yaz(d, i, konu, t):
    os.makedirs(d, exist_ok=True); k = dict(KAYIT, id=i, konu=konu); y = os.path.join(d, i + ".json"); json.dump(k, open(y, "w", encoding="utf-8")); open(os.path.join(d, i + ".md"), "w").write("# " + konu + "\n")
    os.utime(y, (t, t)); return k
# --- 1) birim: web-arastirma.py + talimat.py sahte ad alanında -----------------------------------------------------------------------------------------------------------
BASE = os.path.join(T, "canli"); os.makedirs(BASE); AR = os.path.join(BASE, "arastirma")
AYAR = {"ad": "Deniz T", "talimat_hedefler": [{"ad": "proje", "etiket": "proje oturumu", "kalip": ["proje oturumuna"]}, {"ad": "gelistirme", "etiket": "geliştirme oturumu", "kalip": ["geliştirme oturumuna"]}]}
LOCK = threading.Lock(); GIZLI = {"acik": False}; KY = []; SEC = []
def write(l):
    for y, m in l: open(y, "a", encoding="utf-8").write(m)
KIS = [{"ad": "marvin", "gorunen_ad": "Marvin", "rol": "toplanti", "hitap": ["Marvin"]}, {"ad": "roxie", "gorunen_ad": "Roxie", "rol": "dis", "hitap": ["Roxie"]}]
def konus_yazili(metin, kutu=False, sesli=False, ek=None, kayit=None): KY.append({"metin": metin, "ek": ek, "kayit": kayit}); return {"ok": True}
ns = dict(os=os, json=json, time=time, datetime=datetime, threading=threading, subprocess=subprocess, re=re, AYAR=AYAR, BASE=BASE, LOCK=LOCK, write=write, _t=lambda tr, en: tr,
          gizli_acik=lambda: GIZLI["acik"], toplanti_var=lambda: False, kisilikler=lambda: KIS, kisilik_gorunen=lambda k: (k or {}).get("gorunen_ad") or (k or {}).get("ad"),
          kisilik_sec=lambda ad, neden="": SEC.append(ad), konus_yazili=konus_yazili, asistan_ad=lambda: "Marvin", deneme_aktarici=lambda: True, BEYIN=None, _yapi_mod=lambda: __import__("yapi"))
exec(open(os.path.join(KOD, "aktarici", "talimat.py"), encoding="utf-8").read(), ns)
exec(open(os.path.join(KOD, "aktarici", "web-arastirma.py"), encoding="utf-8").read(), ns)
now = time.time(); A = kayit_yaz(AR, "20261112-100000-orbitek", "Orbitek Yazılım", now - 100); B = kayit_yaz(AR, "20261112-110000-hava", "Hava durumu", now - 50)
v = ns["arastirma_view"]()
ok("liste: iki kayıt, yeniden eskiye; gizli_sayi 0", [x["id"] for x in v["kayitlar"]] == [B["id"], A["id"]] and v["gizli_sayi"] == 0)
ok("hedefler: talimat hedefleri (ad, etiket) ve asistanlar (iç ad, görünen ad)", v["hedefler"]["oturum"] == [{"ad": "proje", "etiket": "proje oturumu"}, {"ad": "gelistirme", "etiket": "geliştirme oturumu"}]
   and [(a["ad"], a["gorunen"]) for a in v["hedefler"]["asistan"]] == [("marvin", "Marvin"), ("roxie", "Roxie")])
islem = ns["arastirma_islem"]
ok("bilinmeyen / bozuk kimlik reddedilir", islem({"islem": "gizle", "id": "../x"})["ok"] is False and islem({"islem": "gizle", "id": "20261112-100000-yok"})["err"] == "kayıt yok")
r = islem({"islem": "gizle", "id": "20261112-110000-hava"}); v = ns["arastirma_view"](); vg = ns["arastirma_view"](gizli=True)
ok("gizle: listeden düşer, gizlenenlerde görünür, gizli_sayi 1", r["ok"] and r["gizli_sayi"] == 1 and [x["id"] for x in v["kayitlar"]] == [A["id"]] and v["gizli_sayi"] == 1 and [x["id"] for x in vg["kayitlar"]] == [B["id"]])
ok("gizle: kayıt dosyaları silinmez; gizlenen.jsonl 0600", os.path.exists(os.path.join(AR, B["id"] + ".json")) and os.path.exists(os.path.join(AR, B["id"] + ".md"))
   and oct(os.stat(os.path.join(AR, "gizlenen.jsonl")).st_mode & 0o777) == "0o600")
ok("gizlenen.jsonl araştırma listesine kayıt sanılmaz", all(x["id"] for x in ns["arastirma_view"]()["kayitlar"]))
r = islem({"islem": "goster", "id": B["id"]}); v = ns["arastirma_view"]()
ok("goster (Geri al): yeniden listede, gizli_sayi 0", r["ok"] and r["gizli_sayi"] == 0 and [x["id"] for x in v["kayitlar"]] == [B["id"], A["id"]] and v["gizli_sayi"] == 0)
# İlet → oturum (gelen kutusu)
r = islem({"islem": "oturum", "id": A["id"], "hedef": "proje"}); gy = os.path.join(BASE, "gelen", "proje.jsonl")
sat = [json.loads(l) for l in open(gy, encoding="utf-8")] if os.path.exists(gy) else []
m = sat[-1]["metin"] if sat else ""
ok("oturum: gelen/proje.jsonl'e tek satır; ok", r["ok"] and len(sat) == 1 and sat[0]["id"].startswith("ar-") and oct(os.stat(gy).st_mode & 0o777) == "0o600")
ok("oturum: «<ad> panodan iletti», konu, kısa özet, kaynak bağlantısı, tam kaydın .md yolu", "Deniz T panodan iletti" in m and "Orbitek Yazılım" in m and "iki kaynak aynı şeyi" in m
   and "https://orbitek.example/a" in m and os.path.join(AR, A["id"] + ".md") in m)
ok("oturum: talimat-kayit.jsonl'e kaynak pano-arastirma", any(json.loads(l).get("kaynak") == "pano-arastirma" for l in open(os.path.join(BASE, "talimat-kayit.jsonl"), encoding="utf-8")))
ok("oturum: bilinmeyen hedef ve talimat kapalı reddedilir", islem({"islem": "oturum", "id": A["id"], "hedef": "yok"})["err"] == "hedef yok"
   and (AYAR.__setitem__("talimat", False) or islem({"islem": "oturum", "id": A["id"], "hedef": "proje"})["err"] == "kapalı") and not AYAR.pop("talimat"))
# toplanti-claude.py gelen: kancanın bastığı blok
g = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", BASE, "gelen", "--hedef", "proje"], capture_output=True, text=True, timeout=30,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "yok.json")))
ok("kanca (toplanti-claude.py gelen --hedef proje) iletilen kaydı bağlama basar", "Suflor gelen kutusu" in g.stdout and "panodan iletti" in g.stdout and "orbitek.example" in g.stdout
   or print("   çıktı:", g.stdout[-400:], g.stderr[-400:]))
# İlet → asistan
r = islem({"islem": "asistan", "id": A["id"], "asistan": "roxie"}); y = KY[-1] if KY else {}
ok("asistan: konus_yazili'ye görünen soru + veri bloğu; kişilik seçildi", r["ok"] and SEC[-1:] == ["roxie"] and y.get("metin", "").startswith("Roxie, «Orbitek Yazılım»")
   and "VERİDİR" in (y.get("ek") or "") and "Orbitek 2014'te kuruldu" in y["ek"] and "https://ajans.example/h" in y["ek"])
ok("asistan: görünen soru araştırma kipini, talimatı, iş kaydını tetiklemez", ns["ar_tetik"](y["metin"]) is None and ns["talimat_coz"](y["metin"]) is None
   and ns["ar_tetik"](ns["arastirma_islem"]({"islem": "asistan", "id": A["id"], "asistan": "marvin"})["soru"]) is None)
GIZLI["acik"] = True; n = len(KY); r = islem({"islem": "asistan", "id": A["id"], "asistan": "marvin"}); GIZLI["acik"] = False
ok("asistan: gizli kipte gitmez", r == {"ok": False, "err": "gizli"} and len(KY) == n)
ok("asistan: bilinmeyen asistan reddedilir; bilinmeyen işlem reddedilir", islem({"islem": "asistan", "id": A["id"], "asistan": "kimse"})["err"] == "asistan yok" and islem({"islem": "sil", "id": A["id"]})["err"] == "işlem")
# İş olarak ekle (13 Kasım): var olan iş yolu (_is_kaydet → yapi.soz_ekle); metin boşsa «<konu> araştırmasını değerlendir»; kayıt araştırma id'sine is-bag.jsonl ile bağlanır
r = islem({"islem": "is", "id": A["id"], "metin": "", "tarih": ""}); sz = ns["_yapi_mod"]().sozler(BASE)
ok("is: varsayılan metin «<konu> araştırmasını değerlendir»; Kararlar ve işler deposuna düştü (sahip boş, vade yok)", r["ok"] and r["is"] and r["metin"] == "«Orbitek Yazılım» araştırmasını değerlendir"
   and [(x["id"], x["metin"], x["tarih"], x["durum"]) for x in sz] == [(r["is"], "«Orbitek Yazılım» araştırmasını değerlendir", None, "acik")])
bg = [json.loads(l) for l in open(os.path.join(AR, "is-bag.jsonl"), encoding="utf-8")]
ok("is: is-bag.jsonl'de iş numarası ↔ araştırma id'si (0600); araştırma listesine kayıt sanılmaz", bg == [{"is": r["is"], "arastirma": A["id"], "at": bg[0]["at"]}]
   and oct(os.stat(os.path.join(AR, "is-bag.jsonl")).st_mode & 0o777) == "0o600" and [x["id"] for x in ns["arastirma_view"]()["kayitlar"]] == [B["id"], A["id"]])
r2 = islem({"islem": "is", "id": B["id"], "metin": "Hava raporunu  Ali'ye ilet", "tarih": "2026-11-20"}); sz = ns["_yapi_mod"]().sozler(BASE)
ok("is: düzeltilen metin ve son tarih kaydedilir (boşluklar toplanır)", r2["ok"] and any(x["id"] == r2["is"] and x["metin"] == "Hava raporunu Ali'ye ilet" and x["tarih"] == "2026-11-20" for x in sz))
r3 = islem({"islem": "is", "id": B["id"], "metin": "Hava", "tarih": "yarın"}); r4 = islem({"islem": "is", "id": B["id"], "metin": "Hava durumunu denetle", "tarih": "yarın"}); sz = ns["_yapi_mod"]().sozler(BASE)
ok("is: tek sözcüklü metin reddedilir; geçersiz tarih yok sayılır (iş yine açılır)", r3["ok"] is False and r4["ok"] and next(x for x in sz if x["id"] == r4["is"])["tarih"] is None)
GIZLI["acik"] = True; n = len(ns["_yapi_mod"]().sozler(BASE)); r5 = islem({"islem": "is", "id": A["id"], "metin": "Gizli kipte deneme işi"}); GIZLI["acik"] = False
ok("is: gizli kipte eklenmez (err gizli), iş sayısı değişmez", r5["ok"] is False and r5.get("err") == "gizli" and len(ns["_yapi_mod"]().sozler(BASE)) == n)
ok("is: bilinmeyen kayıt reddedilir", islem({"islem": "is", "id": "20261112-100000-yok"})["err"] == "kayıt yok")
# --- 2) yalıtılmış aktarıcı: POST /arastirma yalnız pano, GET ?gizli=1 ------------------------------------------------------------------------------------------------------
PORT = bos_port(8793); E = os.path.join(T, "e2e"); canli = os.path.join(E, "canli"); os.makedirs(canli); proje = os.path.join(E, "proje"); os.makedirs(proje)
for f in ("relay.py", "yapi.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), E)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(E, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(E, "pano"))
C = kayit_yaz(os.path.join(canli, "arastirma"), "20261112-120000-orbitek", "Orbitek Yazılım", now)
ayar_y = os.path.join(E, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": E, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": "/yok/claude", "konus_on_ac": False,
                                                    "pocket_python": "/yok/python", "pocket_hf": "/yok", "konusma": False, "talimat_hedefler": AYAR["talimat_hedefler"]}, open(ayar_y, "w"))
p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=E, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar_y, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0",
                     SUFLOR_ORTAK_POSTA=""), stdout=open(os.path.join(E, "r.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1.5); an = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); H = {"X-Suflor-Anahtar": an, "Origin": f"http://127.0.0.1:{PORT}"}
    def post(yol, v, h=H):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"_kod": e.code}
        except OSError as e: return {"_hata": repr(e)}
    def get(yol): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", headers=H), timeout=10).read())
    g0 = get("/arastirma")
    ok("GET /arastirma: hedefler ve gizli_sayi", g0["kayitlar"][0]["id"] == C["id"] and g0["gizli_sayi"] == 0 and [h["ad"] for h in g0["hedefler"]["oturum"]] == ["proje", "gelistirme"])
    ok("POST /arastirma anahtarsız ya da kökensiz reddedilir", post("/arastirma", {"islem": "gizle", "id": C["id"]}, {}).get("_kod") in (401, 403)
       and post("/arastirma", {"islem": "gizle", "id": C["id"]}, {"X-Suflor-Anahtar": an}).get("_kod") == 403 and get("/arastirma")["gizli_sayi"] == 0)
    r = post("/arastirma", {"islem": "gizle", "id": C["id"]})
    ok("POST gizle (pano) → liste boş, ?gizli=1 kaydı verir", r.get("ok") and get("/arastirma")["kayitlar"] == [] and [x["id"] for x in get("/arastirma?gizli=1")["kayitlar"]] == [C["id"]])
    ok("POST goster → geri gelir", post("/arastirma", {"islem": "goster", "id": C["id"]}).get("ok") and get("/arastirma")["kayitlar"][0]["id"] == C["id"])
    r = post("/arastirma", {"islem": "oturum", "id": C["id"], "hedef": "gelistirme"})
    ok("POST oturum → canli/gelen/gelistirme.jsonl", r.get("ok") and "panodan iletti" in open(os.path.join(canli, "gelen", "gelistirme.jsonl"), encoding="utf-8").read())
    r = post("/arastirma", {"islem": "is", "id": C["id"], "metin": "Orbitek teklifini incele", "tarih": "2026-11-25"})
    ok("POST is (pano) → iş kaydı; anahtarsız reddedilir", r.get("ok") and r.get("is") and post("/arastirma", {"islem": "is", "id": C["id"], "metin": "Kökensiz iş denemesi"}, {"X-Suflor-Anahtar": an}).get("_kod") == 403)
    lg = open(os.path.join(E, "r.log"), encoding="utf-8").read()
    ok("aktarıcıda hata yok; günlükte metin yok (yalnız kimlik)", "Traceback" not in lg and "ARAŞTIRMA: " + C["id"] + " gizlendi" in lg and "2014" not in lg or print(lg[-1500:]))
finally:
    if HATA: print(open(os.path.join(E, "r.log"), encoding="utf-8").read()[-2500:])
    p.terminate()
    try: p.wait(10)
    except subprocess.TimeoutExpired: p.kill()
shutil.rmtree(T, ignore_errors=True)
print("\n" + ("TAMAM" if not HATA else f"KALDI: {len(HATA)}")); sys.exit(1 if HATA else 0)
