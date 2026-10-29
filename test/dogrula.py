#!/usr/bin/env python3
# Faz D (S162, v0.147.0) — kurulum.py dogrula (Kurulumu denetle), sahte ortamda: eksik model, eski eklenti sürümü, dolu takas, kurulu olmayan BlackHole → ✗; okunamayan izin → ?;
# sağlam madde → ✓; posta kutusu dosyası (beta kullanıcısı) yalnız sayı/durum/ayar adı içerir (yol, kullanıcı adı, ayar DEĞERİ yok); geliştiricide posta kutusu yazılmaz;
# kurulum.py guncelleme-sonrasi'nın dogrula'yı çağırdığı; aktarıcıda /dogrula (anahtarlı okuma, ?yenile=1 arka planda ve dakikada bir).
# kurulum.py dogrula ya da aktarici/saglik.py değişince koştur:  PYTHONDONTWRITEBYTECODE=1 python3 test/dogrula.py
import getpass, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8783)
T = os.path.realpath(tempfile.mkdtemp(prefix="dogrula-")); EV = os.path.join(T, "ev"); DESTEK = os.path.join(EV, "Library", "Application Support", "Suflor"); ORTAK = os.path.join(T, "ortak")
APP = os.path.join(T, "uyg"); canli = os.path.join(APP, "canli"); os.makedirs(DESTEK); os.makedirs(ORTAK); os.makedirs(canli)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
ay = os.path.join(DESTEK, "ayar.json"); GIZLI_DEGER = "gizli-deger-93817"
AYAR = {"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": APP, "proje": os.path.join(T, "proje"), "ortak": ORTAK, "kod": KOD, "toplantiya_ses": True, "konusma": False, "yerel_ses": False,
        "oto_toplanti": False, "tepki_sesleri": os.path.join(T, "yok"), "eposta_adres": f"{GIZLI_DEGER}@ornek.com", "kisilik_bellek": GIZLI_DEGER, "sozluk_ek": ["Deniz Yıldız"], "tema": "koyu"}
json.dump(AYAR, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py", "kurulum.py"): shutil.copy(os.path.join(KOD, f), APP)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(APP, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(APP, "pano"))
ORT = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_EV=EV, SUFLOR_AYAR=ay, SUFLOR_TEST_PAYLASILAN=ORTAK, SUFLOR_TEST_TAKAS="9.5,10.0", SUFLOR_TEST_BLACKHOLE="yok", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_KOD=os.path.join(T, "yok-kod"))  # kod klasörü yok: git klonu değil (beta); aktarıcı da uygulama klasöründeki kopyaya düşer
LOG = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=APP, stdout=open(LOG, "w"), stderr=subprocess.STDOUT, env=ORT)
U = f"http://127.0.0.1:{PORT}"
def istek(yol, g=None, anahtar=True):
    h = {"Content-Type": "application/json"}
    if anahtar: h["X-Suflor-Anahtar"] = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    return json.load(urllib.request.urlopen(urllib.request.Request(U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h), timeout=10))
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        try:
            if kosul(): return True
        except Exception: pass
        time.sleep(0.3)
    return False
def dogrula(*a, env=None):
    p = subprocess.run([sys.executable, "-B", os.path.join(KOD, "kurulum.py"), "dogrula", *a], capture_output=True, text=True, env=env or ORT, timeout=120); return p
try:
    ok("aktarıcı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")), 20)); time.sleep(1.5)
    istek("/takvim?v=0.1.0")  # eklentinin eski sürümle yoklaması
    p = dogrula("--json"); d = json.loads(p.stdout); M = {x["id"]: x for x in d["maddeler"]}
    ok(f"çıkış kodu ✗ varken 1: {p.returncode}", p.returncode == 1)
    ok("aktarıcı sürümü ✓ (kodla aynı)", M["surum-aktarici"]["durum"] == "ok")
    ok(f"eski eklenti sürümü ✗: {M['surum-eklenti']['not']}", M["surum-eklenti"]["durum"] == "hata" and "0.1.0" in M["surum-eklenti"]["not"] and M["surum-eklenti"]["yap"])
    ok(f"eksik Whisper modeli ✗: {M['model-whisper']['not']}", M["model-whisper"]["durum"] == "hata" and M["model-whisper"]["yap"])
    ok("anlam modeli yok → ? (isteğe bağlı)", M["model-anlam"]["durum"] == "?")
    ok(f"yüksek takas ✗: {M['kaynak']['not']}", M["kaynak"]["durum"] == "hata" and "takas 9.5/10.0" in M["kaynak"]["not"])
    ok(f"BlackHole yok ✗ (toplantiya_ses açık): {M['blackhole']['not']}", M["blackhole"]["durum"] == "hata" and "kurulu değil" in M["blackhole"]["not"])
    ok("okunamayan izinler ? (deneme ortamında)", all(M[k]["durum"] == "?" for k in ("izin-mikrofon", "izin-erisilebilirlik", "izin-ekran", "izin-bildirim", "izin-masaustu")))
    ok("ajan deneme ortamında ?", M["ajan"]["durum"] == "?")
    ok("her ✗ ve ? maddede 'ne yapmalı'", all(x["yap"] for x in d["maddeler"] if x["durum"] != "ok") and all(not x["yap"] for x in d["maddeler"] if x["durum"] == "ok"))
    ok("ayar farkı: yalnız adlar (eposta_adres/kisilik_bellek kurulum anahtarı dışı, tema varsayılan değil)", "kisilik_bellek" in M["ayar-fark"]["not"] and "tema" in M["ayar-fark"]["not"] and GIZLI_DEGER not in json.dumps(d) and "Deniz" not in M["ayar-fark"]["not"])
    kd = os.path.join(ORTAK, "geri-bildirim"); dos = [f for f in os.listdir(kd)] if os.path.isdir(kd) else []
    ok(f"beta kullanıcısı: posta kutusu dosyası {dos}", len(dos) == 1 and re.fullmatch(r"\d{8}-\d{4}-dogrula-[a-z0-9_-]+\.md", dos[0]) is not None)
    md = open(os.path.join(kd, dos[0]), encoding="utf-8").read() if dos else ""
    ok("posta kutusu: ✗ maddeleri ve ne yapmalı var", "✗" in md and "ne yapmalı" in md and "Eklenti sürümü" in md)
    kul = getpass.getuser()
    ok("posta kutusu/dogrula.json: yol, kullanıcı adı, ayar değeri, ad yok", all(x not in (md + json.dumps(d, ensure_ascii=False)) for x in ("/Users/", T, EV, GIZLI_DEGER, "Deniz", "ornek.com") + ((kul,) if len(kul) > 2 else ())))
    src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read(); ok("izin ✗ önerisi: listede açık görünse de − ile kaldırıp + ile yeniden ekle (~/Applications/Suflor.me.app)", "IZIN_YENIDEN.format(ad=ad)" in src and "− ile kaldırın, + ile yeniden ekleyin" in src and "Command + Shift + G → ~/Applications/Suflor.me.app" in src)
    ok("dogrula --yazma: dosya yazmaz", subprocess.run([sys.executable, "-B", os.path.join(KOD, "kurulum.py"), "dogrula", "--json", "--hizli", "--yazma"], capture_output=True, text=True, env=dict(ORT, SUFLOR_TEST_DURUMSUZ="1"), timeout=120).returncode in (0, 1) and len(os.listdir(os.path.join(ORTAK, "geri-bildirim"))) == len(dos))
    ok("dogrula.json uygulama klasörüne yazıldı", os.path.isfile(os.path.join(APP, "dogrula.json")))
    ok("metin çıktısında ✓/✗/? simgeleri", all(s in dogrula().stdout for s in ("✓", "✗", "?")))
    # geliştirici: posta kutusu yazılmaz
    shutil.rmtree(kd); AYAR["gelistirici"] = True; json.dump(AYAR, open(ay, "w")); dogrula("--json")
    ok("geliştiricide posta kutusu dosyası yazılmadı", not os.path.isdir(kd) or not os.listdir(kd))
    del AYAR["gelistirici"]; json.dump(AYAR, open(ay, "w"))
    # geliştirici ölçütü: ayar gelistirici yok ama kod klasörü git klonu → beta değil, posta kutusu yazılmaz
    gk = os.path.join(T, "gk"); os.makedirs(os.path.join(gk, ".git")); d7 = json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_KOD=gk)).stdout)
    ok("git klonu (ayarda gelistirici yok) → beta False, posta kutusu yazılmadı", d7["beta"] is False and not os.path.isdir(kd))
    ok("ayar gelistirici yok, .git yok → beta True", json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_DURUMSUZ="1")).stdout)["beta"] is True); shutil.rmtree(kd, ignore_errors=True)
    # kod okunamıyor (launchd altında Masaüstü): uygulama klasöründeki kopya koşar; Swift kaynakları yok → ✓ DEĞİL ?; sürüm notunda kopya ibaresi
    uy = os.path.join(T, "uyg-kopya"); os.makedirs(os.path.join(uy, "Contents")); shutil.copy(os.path.join(KOD, "kurulum.py"), uy); shutil.copy(os.path.join(KOD, "manifest.json"), uy)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(uy, "aktarici"))  # kurulum.py modül düzeyinde aktarici/saglayici.py yükler (uygulama klasöründe KOPYA ile var)
    pk = subprocess.run([sys.executable, "-B", os.path.join(uy, "kurulum.py"), "dogrula", "--json", "--hizli", "--yazma"], capture_output=True, text=True, env=dict(ORT, SUFLOR_TEST_DURUMSUZ="1"), cwd=uy, timeout=120)
    dk = {x["id"]: x for x in json.loads(pk.stdout)["maddeler"]}
    ok(f"kopyadan koşunca Swift maddesi ? (yanlış ✓ yok): {dk['swift']['durum']} {dk['swift']['not']}", dk["swift"]["durum"] == "?" and "okunamıyor" in dk["swift"]["not"] and "python3 kurulum.py dogrula" in dk["swift"]["yap"])
    dk2 = {x["id"]: x for x in json.loads(subprocess.run([sys.executable, "-B", os.path.join(KOD, "kurulum.py"), "dogrula", "--json", "--hizli", "--yazma"], capture_output=True, text=True, env=dict(ORT, SUFLOR_KOD_OKUNAMAZ="1"), timeout=120).stdout)["maddeler"]}
    ok("SUFLOR_KOD_OKUNAMAZ=1: Swift ? ve sürüm notunda 'kurulu kopyaya göre'", dk2["swift"]["durum"] == "?" and "kurulu kopyaya göre" in dk2["surum-aktarici"]["not"])
    ok("kod okunabilirken Swift maddesi '?' değil (kaynaklarla karşılaştırır)", {x["id"]: x for x in json.loads(dogrula("--json", "--hizli", "--yazma", env=dict(ORT, SUFLOR_TEST_DURUMSUZ="1")).stdout)["maddeler"]}["swift"]["durum"] in ("ok", "hata"))
    ok("kurulum.py KOPYA listesinde", '"kurulum.py"' in open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read().split("KOPYA = [")[1].split("]")[0])
    # BlackHole var + bir süreç okuyor → ✓; kurulu ama toplantıda kimse okumuyor → ? (toplantı dışı)
    d2 = json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_BLACKHOLE="calisiyor")).stdout)
    ok("BlackHole çalışıyor ✓", {x["id"]: x for x in d2["maddeler"]}["blackhole"]["durum"] == "ok")
    d3 = json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_BLACKHOLE="var")).stdout)
    ok("BlackHole kurulu, kimse okumuyor, toplantı yok → ?", {x["id"]: x for x in d3["maddeler"]}["blackhole"]["durum"] == "?")
    # sağlam kaynak ✓
    d4 = json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_TAKAS="0.2,4.0")).stdout); ok("takas düşükken kaynak notunda takas sorunu yok", "takas" not in {x["id"]: x for x in d4["maddeler"]}["kaynak"]["not"].split(",")[0] or {x["id"]: x for x in d4["maddeler"]}["kaynak"]["durum"] == "ok")
    del AYAR["toplantiya_ses"]; json.dump(AYAR, open(ay, "w")); d6 = json.loads(dogrula("--json").stdout); ok("toplantiya_ses kapalıyken BlackHole maddesi ✓ (denetlenmez)", {x["id"]: x for x in d6["maddeler"]}["blackhole"]["durum"] == "ok")
    # aktarıcı yokken
    d5 = json.loads(dogrula("--json", env=dict(ORT, SUFLOR_TEST_DURUMSUZ="1")).stdout); ok("aktarıcıya ulaşılamazsa ✗", {x["id"]: x for x in d5["maddeler"]}["surum-aktarici"]["durum"] == "hata")
    # /dogrula ucu
    try: urllib.request.urlopen(U + "/dogrula", timeout=5); anahtarsiz = 200
    except urllib.error.HTTPError as e: anahtarsiz = e.code
    ok(f"/dogrula anahtarsız 401: {anahtarsiz}", anahtarsiz == 401)
    g = istek("/dogrula"); ok(f"/dogrula son dogrula.json'u döner (maddeler {len(g.get('maddeler') or [])})", g.get("var") and g.get("maddeler") and not g.get("calisiyor"))
    os.remove(os.path.join(APP, "dogrula.json")); g = istek("/dogrula"); ok("dogrula.json yokken var: false", g.get("var") is False)
    g = istek("/dogrula?yenile=1"); ok("?yenile=1 arka planda başlattı", g.get("ok") and g.get("calisiyor"))
    ok("denetim bitince sonuç geldi", bekle(lambda: istek("/dogrula").get("var") and not istek("/dogrula").get("calisiyor"), 60))
    sw = {x["id"]: x for x in istek("/dogrula").get("maddeler", [])}.get("swift", {})
    ok(f"kod klasörü yok → aktarıcı uygulama klasöründeki kurulum.py kopyasını koşturdu (swift {sw.get('durum')}: {sw.get('not')})", sw.get("durum") == "?" and "okunamıyor" in sw.get("not", ""))
    g = istek("/dogrula?yenile=1"); ok(f"dakikada bir sınırı (bekle={g.get('bekle')})", g.get("ok") and not g.get("calisiyor") and g.get("bekle", 0) > 0)
    # güncelleme sonrası denetim kendiliğinden
    src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read(); gs = src[src.index("def guncelleme_sonrasi"):]
    ok("guncelleme_sonrasi sonunda dogrula çağrılır, özet yazılır", "dogrula(sessiz_=True)" in gs and "Kurulum denetimi:" in gs)
finally:
    r.terminate(); time.sleep(0.5); shutil.rmtree(T, ignore_errors=True)
print("\nSONUÇ: " + ("hepsi geçti" if not HATA else f"{len(HATA)} başarısız: {HATA}")); sys.exit(1 if HATA else 0)
