#!/usr/bin/env python3
# Faz D2 (S162, v0.148.0) — Deneme toplantısı (duman testi) kipi: toplantı yokken reddedilir; toplantıda başlar, tek kip; altyazı satırı gelince c/altyazı ✓, mikrofon açıkken susan "ben" kanalı
# 30 sn (testte 5 sn) sonra ✗, kurulu olmayan karşı kanal "?" ve nedeniyle; ad kaynağı takvim|Başlat|sinyal (ad yazılmaz); asistan cevabı (duman_konus) ✓ ve ilk metin süresi; BlackHole/kaynak
# kurulum.py dogrula'dan (✗ takas, ✗ BlackHole yok); Bitir ve süre dolunca özet; <uygulama>/duman/<tarih>.json ve (beta) ortak posta kutusu dosyası yalnız sayı/durum/süre/platform içerir
# (toplantı adı, kişi adı, döküm metni, yol yok); geliştiricide posta kutusu yazılmaz; kip toplantı dosyasına hiçbir şey yazmaz.
# aktarici/duman.py, saglik.py, bas-konus.py'deki kanca ya da kurulum.py dogrula değişince koştur:  PYTHONDONTWRITEBYTECODE=1 python3 test/duman.py
import getpass, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8784)
T = os.path.realpath(tempfile.mkdtemp(prefix="duman-")); EV = os.path.join(T, "ev"); DESTEK = os.path.join(EV, "Library", "Application Support", "Suflor"); ORTAK = os.path.join(T, "ortak")
APP = os.path.join(T, "uyg"); canli = os.path.join(APP, "canli"); os.makedirs(DESTEK); os.makedirs(ORTAK); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
ay = os.path.join(DESTEK, "ayar.json"); TOPLANTI_AD = "Gizli Proje Toplantısı Orion"; KISI = "Zeynep Kaya"; METIN = "bütçe onaylandı yedi yüz bin"
AYAR = {"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": APP, "proje": proje, "ortak": ORTAK, "kod": KOD, "toplantiya_ses": True, "konusma": False, "yerel_ses": False, "oto_toplanti": False,
        "tepki_sesleri": os.path.join(T, "yok")}
json.dump(AYAR, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py", "kurulum.py"): shutil.copy(os.path.join(KOD, f), APP)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(APP, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(APP, "pano"))
ORT = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_EV=EV, SUFLOR_AYAR=ay, SUFLOR_TEST_PAYLASILAN=ORTAK, SUFLOR_TEST_TAKAS="9.5,10.0", SUFLOR_TEST_BLACKHOLE="yok", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_KOD=os.path.join(T, "yok-kod"))  # kod klasörü yok: git klonu değil (beta); denetim uygulama klasöründeki kurulum.py kopyasına düşer
LOG = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=APP, stdout=open(LOG, "w"), stderr=subprocess.STDOUT, env=ORT)
U = f"http://127.0.0.1:{PORT}"; Lg = lambda: open(LOG, encoding="utf-8").read()
def istek(yol, g=None):
    k = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k, "Origin": U}
    return json.load(urllib.request.urlopen(urllib.request.Request(U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h), timeout=15))
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        try:
            if kosul(): return True
        except Exception: pass
        time.sleep(0.25)
    return False
NABIZ = {"a": False}
def nabiz():
    while True:
        try:
            if NABIZ["a"]: istek("/ping", {"ver": "0.148.0", "meeting": {"title": TOPLANTI_AD}, "panel": False, "rows": 0, "platform": "meet", "call": True, "captions": True, "mic": {"on": True, "sessiz": False}})
        except Exception: pass
        time.sleep(1)
dm = lambda: istek("/status").get("duman")
M = lambda d, i: next((x for x in (d or {}).get("maddeler", []) if x["id"] == i), {})
try:
    ok("aktarıcı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")), 20)); time.sleep(1.5)
    threading.Thread(target=nabiz, daemon=True).start()
    ok("duman yokken /status duman boş", dm() is None)
    x = istek("/duman", {"islem": "baslat"}); ok(f"toplantı yokken reddedildi: {x.get('err')}", x.get("ok") is False and "toplantıya gir" in (x.get("err") or ""))
    x = istek("/duman", {"islem": "bitir"}); ok("çalışan deneme yokken Bitir reddedildi", x.get("ok") is False)
    NABIZ["a"] = True; ok("toplantı tanındı (eklenti çağrıda)", bekle(lambda: (istek("/status").get("extension") or {}).get("call"), 8)); time.sleep(1)
    dosya_once = {f: os.path.getsize(os.path.join(canli, f)) for f in os.listdir(canli) if f.endswith((".md", ".jsonl"))}
    x = istek("/duman", {"islem": "baslat"}); ok("toplantıda başladı", x.get("ok") is True and (x.get("duman") or {}).get("aktif") is True)
    x2 = istek("/duman", {"islem": "baslat"}); ok(f"ikinci Başlat reddedildi (tek kip): {x2.get('err')}", x2.get("ok") is False)
    d = dm(); ok("a: toplantı tanındı, platform Meet, ad kaynağı sinyal", M(d, "a").get("durum") == "ok" and "Meet" in M(d, "a")["not"] and "sinyal" in M(d, "a")["not"])
    ok("c: henüz bekliyor", M(d, "c").get("durum") == "bekliyor")
    ok("e: Konuş kapalı → ? ve yönerge var", M(d, "e").get("durum") == "?" and len(d.get("yonerge") or []) == 2)
    # altyazı satırı (toplantı dosyası açılır)
    istek("/ingest", {"meeting": {"title": TOPLANTI_AD}, "source": "transcript", "entries": [{"id": "a/1", "speaker": KISI, "time": "10:00", "text": METIN}]})
    ok("c/altyazı ✓ satır gelince", bekle(lambda: ((M(dm(), "c").get("kanal") or {}).get("altyazi") or {}).get("durum") == "ok", 5))
    ok("b: döküm dosyası ✓", M(dm(), "b").get("durum") == "ok")
    # asistan cevabı (bas-konus.py'nin ölçüm kaydından gelen kanca)
    ok("duman_konus kancası bas-konus.py'de", "duman_konus(o)" in open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read())
    # asistan cevabı maddesi (e): Konuş açıkken bekliyor → cevap gelince ✓ ve ilk metin süresi → hata/zaman aşımı ✗ (duman.py yalıtılmış çalıştırılır; bas-konus.py kancası ayrıca denetlendi)
    ns = {"os": os, "time": time, "re": re, "json": json, "subprocess": subprocess, "threading": threading, "sys": sys, "datetime": __import__("datetime"), "STATE": {}, "TOPO": {}, "AYAR": {"konusma": True},
          "ARAYUZ_DILI": "tr", "_t": lambda tr, en: tr}; exec(compile(open(os.path.join(KOD, "aktarici", "duman.py"), encoding="utf-8").read(), "duman.py", "exec"), ns); D = ns["DUMAN"]
    D["aktif"] = True; ok("e: Konuş açık, cevap yok, süre içinde → bekliyor", ns["_dm_konus"](1)[0] == "bekliyor")
    ns["duman_konus"]({"ilk_ms": 1800, "sure_ms": 4200, "kaynak": "hitap", "hata": False}); e = ns["_dm_konus"](1); ok(f"e: cevap geldi → ✓ ve ilk metin süresi: {e[1]}", e[0] == "ok" and "1.8 sn" in e[1] and "hitap" in e[1])
    ns["duman_konus"]({"ilk_ms": 1, "sure_ms": 1, "kaynak": "bas", "hata": True}); ok("e: ikinci cevap ilkini değiştirmez", "1.8 sn" in ns["_dm_konus"](1)[1])
    D["konus"] = None; ok("e: süre dolunca cevap yok → ✗", ns["_dm_konus"](999)[0] == "hata")
    D["aktif"] = False; ns["duman_konus"]({"ilk_ms": 5, "sure_ms": 5, "kaynak": "bas"}); ok("e: kip kapalıyken gelen cevap sayılmaz", D["konus"] is None)
    D["aktif"] = True; ns["duman_konus"]({"ilk_ms": 5, "sure_ms": 5, "kaynak": "bas", "hata": True}); ok("e: cevap hata verdiyse ✗", ns["_dm_konus"](1)[0] == "hata")
    # yalıtılmış: konuşma görüldü ama satır gelmedi → ✗; konuşma yok → ?
    ns["kanal_son"] = lambda k: 0.0; ns["ben_kod"] = lambda: "akiyor"; ns["yerel_ses_durum"] = lambda: "dinliyor"; ns["DUMAN_KANAL_SN"] = 30
    D.update(ilk={}, ses={}); ok("c: konuşma yok, satır yok → ?", ns["_dm_kanal"]("ben", 1000.0, 40, {}, False)[0] == "?")
    D["ses"] = {"ben": 1005.0}; ok("c: konuşma var, satır yok → ✗", ns["_dm_kanal"]("ben", 1000.0, 40, {}, False)[0] == "hata")
    D["ses"] = {"karsi": 1005.0}; ok("c: altyazı: karşı konuştu, satır yok → ✗", ns["_dm_kanal"]("altyazi", 1000.0, 40, {"captions": True}, False)[0] == "hata")
    D.update(ilk={"ben": 1178.0}, ses={}); ok("c: satır 178 sn'de → pencerede ✓ değil", ns["_dm_kanal"]("ben", 1000.0, 200, {}, False)[0] == "?")
    D.update(ilk={"ben": 1010.0}); ok("c: satır 10 sn'de → ✓", ns["_dm_kanal"]("ben", 1000.0, 200, {}, False)[0] == "ok")
    # ben kanalı susar → ✗; karşı kanal kurulu değil → ?
    # 28 Ekim: ses seviyesinde konuşma yoksa satır gelmemesi arıza değil → ? ve "kimse konuşmadı"; konuşma olup satır gelmediyse ✗ (aşağıda yalıtılmış)
    ok("c: ben susunca ? ve kimse konuşmadı (mikrofon açık)", bekle(lambda: ((M(dm(), "c").get("kanal") or {}).get("ben") or {}).get("durum") == "?", 12) and "kimse konuşmadı" in M(dm(), "c")["kanal"]["ben"]["not"])
    k = M(dm(), "c").get("kanal") or {}
    ok(f"c: karşı kanal kurulu değil → ? ve neden: {k.get('karsi')}", k.get("karsi", {}).get("durum") == "?" and k["karsi"]["not"])
    ok("c: genel ? (kimse konuşmadı, ✗ değil)", M(dm(), "c").get("durum") == "?")
    ok("d: Claude oturumu açık değil → ✗ ya da ? (deneme)", M(dm(), "d").get("durum") in ("hata", "?"))
    ok("f: BlackHole ✗ (kurulu değil) kurulum.py dogrula'dan", bekle(lambda: M(dm(), "f").get("durum") == "hata", 25) and "kurulu değil" in M(dm(), "f")["not"])
    ok("g: Mac kaynakları ✗ (takas dolu)", M(dm(), "g").get("durum") == "hata" and "takas" in M(dm(), "g")["not"])
    ok("dogrula.json ve posta kutusuna yazılmadı (--yazma)", not os.path.exists(os.path.join(APP, "dogrula.json")) and not os.path.isdir(os.path.join(ORTAK, "geri-bildirim")))
    # Whisper ben satırı sonradan gelirse ✓'ya döner (canlı ölçüm)
    istek("/ingest", {"meeting": {"title": TOPLANTI_AD}, "source": "whisper", "entries": [{"id": "w/1", "speaker": "Deniz T", "time": "10:01", "text": "evet tamam", "kanal": "ben"}]})
    ok("c/ben pencereden sonra gelen satır ✓ saymaz (tutarlı: ? ve pencere dışı)", bekle(lambda: "pencere dışı" in (((M(dm(), "c").get("kanal") or {}).get("ben") or {}).get("not") or ""), 5) and ((M(dm(), "c").get("kanal") or {}).get("ben") or {}).get("durum") != "ok")
    # Bitir
    x = istek("/duman", {"islem": "bitir"}); d = x.get("duman") or {}
    ok(f"Bitir: özet: {d.get('ozet')}", x.get("ok") is True and d.get("aktif") is False and re.match(r"Meet: \d/\d geçti", d.get("ozet") or "") is not None)
    ok("özet sorunları söyler (BlackHole, Mac kaynakları)", "BlackHole" in d["ozet"] and "Mac kaynakları" in d["ozet"])
    ok("bitince bekliyor madde kalmadı", all(m["durum"] != "bekliyor" for m in d["maddeler"]))
    ok("Bitir sonrası yeniden başlatılabilir", istek("/duman", {"islem": "baslat"}).get("ok") is True)
    ok("süre dolunca kendiliğinden bitti", bekle(lambda: (dm() or {}).get("aktif") is False, 40) and "geçti" in (dm() or {}).get("ozet", ""))
    # yazılan dosyalar
    dd = os.path.join(APP, "duman"); js = sorted(os.listdir(dd)) if os.path.isdir(dd) else []
    ok(f"<uygulama>/duman/<tarih>.json yazıldı: {js}", len(js) >= 1 and all(re.fullmatch(r"\d{8}-\d{4}\.json", f) for f in js))
    kd = os.path.join(ORTAK, "geri-bildirim"); md = sorted(os.listdir(kd)) if os.path.isdir(kd) else []
    ok(f"beta: posta kutusu dosyası {md}", len(md) >= 1 and all(re.fullmatch(r"\d{8}-\d{4}-duman-meet-[a-z0-9_-]+\.md", f) for f in md))
    tum = "".join(open(os.path.join(dd, f), encoding="utf-8").read() for f in js) + "".join(open(os.path.join(kd, f), encoding="utf-8").read() for f in md); kul = getpass.getuser()
    yasak = (TOPLANTI_AD, "Orion", KISI, "Zeynep", METIN, "yedi yüz", T, EV, "/Users/") + ((kul,) if len(kul) > 2 else ())
    ok("dosyalarda toplantı adı, kişi adı, döküm metni ve yol yok", all(y not in tum for y in yasak))
    ok("dosyada platform, kaynak ve madde durumları var", '"platform": "meet"' in tum and "sinyal" in tum and "✗" in "".join(open(os.path.join(kd, f), encoding="utf-8").read() for f in md))
    ok("/status duman çıktısında ad ve metin yok", all(y not in json.dumps(dm(), ensure_ascii=False) for y in (TOPLANTI_AD, KISI, METIN)))
    sonra = {f: os.path.getsize(os.path.join(canli, f)) for f in os.listdir(canli) if f.endswith((".md", ".jsonl"))}
    yeni = {f for f in sonra if f not in dosya_once}
    ok("kip toplantı dosyalarına yazmadı (yalnız ingest satırları)", all(not any(w in open(os.path.join(canli, f), encoding="utf-8").read() for w in ("DUMAN", "Deneme toplantısı", "duman")) for f in sonra))
    ok("günlükte başladı ve bitti", "DUMAN: başladı" in Lg() and "DUMAN: bitti" in Lg())
    # geliştirici: posta kutusu yazılmaz
    r.terminate(); time.sleep(1); shutil.rmtree(kd, ignore_errors=True); shutil.rmtree(dd, ignore_errors=True)
    AYAR["gelistirici"] = True; json.dump(AYAR, open(ay, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=APP, stdout=open(LOG, "w"), stderr=subprocess.STDOUT, env=ORT)
    ok("geliştirici aktarıcı açıldı", bekle(lambda: istek("/status").get("surum"), 20)); NABIZ["a"] = True; time.sleep(2)
    ok("geliştirici: başladı", istek("/duman", {"islem": "baslat"}).get("ok") is True); time.sleep(1); istek("/duman", {"islem": "bitir"})
    ok("geliştirici: duman/<tarih>.json var, posta kutusu yok", os.path.isdir(dd) and len(os.listdir(dd)) == 1 and not os.path.isdir(kd))
    # toplantı biterse kip kapanır
    istek("/duman", {"islem": "baslat"}); NABIZ["a"] = False
    ok("toplantı bitince kip kendiliğinden kapandı", bekle(lambda: (dm() or {}).get("aktif") is False, 20))
    ok("pano: Deneme toplantısı düğmesi ve penceresi kaynakta", all(w in open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read() for w in ("id=ayd2", "id=dmd", "dumanCiz", "'/duman'")))
finally:
    r.terminate(); time.sleep(0.5); shutil.rmtree(T, ignore_errors=True)
print("\nSONUÇ: " + ("hepsi geçti" if not HATA else f"{len(HATA)} başarısız: {HATA}")); sys.exit(1 if HATA else 0)
