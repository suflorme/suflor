#!/usr/bin/env python3
# Sözlük terim kullanım kaydı (aktarici/sozluk-ogren.py so_kullanim_guncelle, sözlük 4. aşama, 4 Kasım) → canli/sozluk-kullanim.json: terim → {son, toplanti_sayisi, ilk}.
# İlk doldurma (izlem en eski dökümden), aynı toplantı iki kez sayılmaz, konuşmacı sütunu sayılmaz, sözlüğün düzelttiği (text) sayılır, süren toplantı işlenmez,
# kayıt veritabanı terimi (VT_BELLEK) kayda girmez, sözlükten çıkan terim kayıttan çıkar, sonradan giren terimin izlemi bugün / öğrenme günü, --kuru yazmaz,
# toplanti-claude.py sozluk --kullanim. Bütün terimler kurgu. Geçici klasörde (~2 sn):  PYTHONDONTWRITEBYTECODE=1 python3 test/sozluk-kullanim.py
import collections, datetime, hashlib, json, os, re, subprocess, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); AK = os.path.join(KOD, "aktarici")
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else f"  — {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-sozluk-kullanim-"); uyg = os.path.join(T, "uyg"); canli = os.path.join(uyg, "canli"); os.makedirs(canli)
AYAR_YOL = os.path.join(T, "ayar.json"); AYAR = {"alan": "Deneme", "ad": "Deneme Kullanici", "port": 8790, "uygulama": uyg, "dil": "tr"}; json.dump(AYAR, open(AYAR_YOL, "w"))
BUGUN = datetime.date.today(); gun = lambda n: (BUGUN - datetime.timedelta(days=n)).isoformat()
def sozluk(ter): json.dump({"surum": 2, "terimler": ter}, open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)
sozluk([{"dogru": "Kalendix", "yanlis": ["kalendiks"], "kip": "duzelt", "kaynak": "kullanici"}, {"dogru": "Pelvora Hub", "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti"},
        {"dogru": "Tessaline", "yanlis": [], "kip": "duzelt", "kaynak": "otomatik"}, {"dogru": "Zornik", "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti"}])
def toplanti(ad, n_gun, satirlar, saat="1000", eski=True):
    md = f"{gun(n_gun)}-{saat}-{ad}.md"
    with open(os.path.join(canli, md[:-3] + ".jsonl"), "w", encoding="utf-8") as f:
        for i, (kim, t) in enumerate(satirlar): f.write(json.dumps({"id": f"{ad}/{i}", "speaker": kim, "text": t}, ensure_ascii=False) + "\n")
    open(os.path.join(canli, md), "w", encoding="utf-8").write("# Canlı transkript\n")
    if eski:
        for f in (md, md[:-3] + ".jsonl"): os.utime(os.path.join(canli, f), (time.time() - 3600, time.time() - 3600))
    return md
m1 = toplanti("Plan", 40, [("Kişi A", "Kalendix takvimini açalım."), ("Kişi B", "Pelvora Hub'a da bakalım.")])
m2 = toplanti("Rapor", 10, [("Kişi A", "Kalendix'te iki hata var."), ("Zornik", "konuşmacı adı sayılmaz"), ("Kişi B", "Morvaxis entegrasyonu")])
m3 = toplanti("Ozet", 2, [("Kişi A", "Tessaline düzeltildi")])  # text sözlüğün düzelttiği hâl (raw ayrı): sayılır
json.dump({"id": "Ozet/1", "speaker": "Kişi A", "text": "Kalendix bugün", "raw": "kalendiks bugün"}, open(os.path.join(canli, m3[:-3] + ".jsonl"), "a"), ensure_ascii=False)
os.utime(os.path.join(canli, m3[:-3] + ".jsonl"), (time.time() - 3600, time.time() - 3600))
AKTIF = {"md": toplanti("Suren", 0, [("Kişi A", "Tessaline şu an konuşuluyor.")], saat="2359", eski=False)}
def ad_alani():
    ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "collections": collections, "hashlib": hashlib, "threading": threading, "BASE": canli,
          "AYAR": AYAR, "AYAR_YOL": AYAR_YOL, "LOCK": threading.Lock(), "print": lambda *a, **k: None}
    s = open(os.path.join(AK, "sozluk.py"), encoding="utf-8").read(); exec(s[:s.index('# Sesli "Claude:"')], ns)
    exec(compile(open(os.path.join(AK, "sozluk-ogren.py"), encoding="utf-8").read(), "sozluk-ogren.py", "exec"), ns)
    ns["aktif_dosya"] = lambda: AKTIF["md"]; return ns
ns = ad_alani(); ns["VT_BELLEK"]["terimler"] = [{"terim": "Morvaxis", "tur": "sistem"}]  # kayıt veritabanı terimi: dökümde geçse de kayda girmez
KY = os.path.join(canli, "sozluk-kullanim.json")
oz, K = ns["so_kullanim_guncelle"](kuru=True)
ok("--kuru yazmaz", not os.path.exists(KY) and oz["toplanti"] == 3 and oz["ilk_kez"])
oz, K = ns["so_kullanim_guncelle"](); k = json.load(open(KY, encoding="utf-8")); r = k["terimler"]
ok("ilk doldurma: 3 biten toplantı, süren toplantı işlenmez", oz["toplanti"] == 3 and sorted(k["islenen"]) == sorted([m1, m2, m3]) and AKTIF["md"] not in k["islenen"], k["islenen"])
ok("izlem en eski dökümün gününden", k["baslangic"] == gun(40) and all(x["ilk"] == gun(40) for x in r.values()), {d: x.get("ilk") for d, x in r.items()})
ok("Kalendix: 3 toplantı (ekli biçim ve sözlüğün düzelttiği de), son 2 gün önce", r["Kalendix"]["toplanti_sayisi"] == 3 and r["Kalendix"]["son"] == gun(2), r["Kalendix"])
ok("çok sözcüklü terim kesmeli ekle (Pelvora Hub'a) sayılır", r["Pelvora Hub"]["toplanti_sayisi"] == 1 and r["Pelvora Hub"]["son"] == gun(40))
ok("Tessaline: biten toplantıda 1 (süren toplantıdaki sayılmaz)", r["Tessaline"]["toplanti_sayisi"] == 1 and r["Tessaline"]["son"] == gun(2))
ok("konuşmacı sütunundaki ad sayılmaz (Zornik)", r["Zornik"]["toplanti_sayisi"] == 0 and "son" not in r["Zornik"])
ok("kayıt veritabanı terimi kayda girmez (Morvaxis)", "Morvaxis" not in r and "Morvaxis" not in open(KY, encoding="utf-8").read())
izin = oct(os.stat(KY).st_mode & 0o777); ok("dosya yalnız kullanıcıya (0600)", izin == "0o600", izin)
oz, K = ns["so_kullanim_guncelle"](); ok("aynı toplantılar ikinci kez sayılmaz", oz["toplanti"] == 0 and json.load(open(KY))["terimler"]["Kalendix"]["toplanti_sayisi"] == 3)
AKTIF["md"] = None; os.utime(os.path.join(canli, f"{gun(0)}-2359-Suren.jsonl"), (time.time() - 120, time.time() - 120))
ogr = f"ogrenme-{BUGUN - datetime.timedelta(days=3):%Y%m%d}"
sozluk([{"dogru": "Kalendix", "yanlis": ["kalendiks"], "kaynak": "kullanici"}, {"dogru": "Tessaline", "yanlis": [], "kaynak": "otomatik"},
        {"dogru": "Vardelo", "yanlis": ["vardello"], "kaynak": ogr}, {"dogru": "Quorvix", "yanlis": [], "kaynak": "proje-karti"}])
oz, K = ns["so_kullanim_guncelle"](); r = json.load(open(KY, encoding="utf-8"))["terimler"]
ok("biten toplantı sonraki çalışmada işlenir (Tessaline 2, son bugün)", oz["toplanti"] == 1 and r["Tessaline"]["toplanti_sayisi"] == 2 and r["Tessaline"]["son"] == gun(0), r.get("Tessaline"))
ok("sözlükten çıkan terim kayıttan çıkar", "Pelvora Hub" not in r and "Zornik" not in r, sorted(r))
ok("sonradan giren terim: izlem bugün; öğrenilen: öğrenme günü", r["Quorvix"]["ilk"] == gun(0) and r["Vardelo"]["ilk"] == gun(3), (r.get("Quorvix"), r.get("Vardelo")))
os.remove(KY); ns2 = ad_alani(); ns2["aktif_dosya"] = lambda: None
oz, K = ns2["so_kullanim_guncelle"](dosyalar=[m2]); ok("verilen toplantı listesiyle yalnız o işlenir", oz["toplanti"] == 1 and list(K["islenen"]) == [m2])
os.remove(KY)
env = dict(os.environ, SUFLOR_AYAR=AYAR_YOL, PYTHONDONTWRITEBYTECODE="1")
p = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "sozluk", "--kullanim", "--kuru"], capture_output=True, text=True, env=env, timeout=60)
ok("toplanti-claude.py sozluk --kullanim --kuru: sayılar terminale, dosya yazılmaz", p.returncode == 0 and "4 toplantı işlendi" in p.stdout and not os.path.exists(KY), (p.stdout + p.stderr)[-400:])
p = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "sozluk", "--kullanim"], capture_output=True, text=True, env=env, timeout=60)
ok("toplanti-claude.py sozluk --kullanim: kaydı doldurur", p.returncode == 0 and os.path.exists(KY) and json.load(open(KY))["terimler"]["Kalendix"]["toplanti_sayisi"] == 3, (p.stdout + p.stderr)[-400:])
print("kaldı: " + ", ".join(HATA) if HATA else "hepsi geçti"); sys.exit(1 if HATA else 0)
