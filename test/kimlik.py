#!/usr/bin/env python3
# Kimlik (A1, aktarici/kimlik.py): ad → e-posta eşlemesi — Türkçe harf katlama, ilk ad/tam ad/baş harf, belirsizlikte eşlenmedi + adaylar, kaynak sırası,
# elle düzeltme, kimlik_birlesti, önbellek, eşlenemeyen listesi. Yalıtılmış: geçici klasör, sahte takvim ve sahte kisi_bul; ağ, Kişiler ve gerçek veri yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kimlik.py
import json, os, re, shutil, sqlite3, stat, sys, tempfile, time, datetime
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad, flush=True); HATA.append(ad) if not k else None
T = tempfile.mkdtemp(prefix="kimlik-")
AT = chr(64)  # tarama düz e-posta görmesin
AYAR = {"ad": "Kemal Duru", "eposta_adres": "Kemal.Duru" + AT + "firma.com"}
KISI = {}; CAGRI = []
def kisi_bul(ad): CAGRI.append(ad); return next((v for k, v in KISI.items() if k.lower() == ad.lower()), {"durum": "ok", "kisiler": []})
ns = {"re": re, "os": os, "json": json, "time": time, "AYAR": AYAR, "BASE": T, "kisi_bul": kisi_bul,
      "TAKVIM_TAM": {}, "TAKVIM_GEC": {"olaylar": [], "pay": []}}
src = open(os.path.join(KOD, "aktarici", "kimlik.py"), encoding="utf-8").read(); exec(compile(src, "kimlik.py", "exec"), ns)
def taz(): ns["kimlik_takvim_sifirla"]()
ns["TAKVIM_TAM"]["1"] = {"kisiler": [{"ad": "Ayşe Yılmaz", "eposta": "ayse.yilmaz" + AT + "firma.com"}, {"ad": "Bora Kaya", "eposta": "Bora.Kaya" + AT + "Firma.com"},
                                    {"ad": "Deniz Aksoy", "eposta": "deniz.aksoy" + AT + "firma.com"}, {"ad": "Deniz Tekin", "eposta": "deniz.tekin" + AT + "firma.com"},
                                    {"ad": "Kaya, Selim", "eposta": "selim.kaya" + AT + "firma.com"}, {"ad": "Ayla Nur Kaya", "eposta": "ayla.kaya" + AT + "firma.com"}],
                         "katilimci_eposta": ["ayse.yilmaz" + AT + "firma.com", "cem.arslan" + AT + "firma.com", "x" + AT + "firma.com", "ece.tas" + AT + "firma.com"]}
ns["TAKVIM_GEC"]["olaylar"].append({"kisiler": [{"ad": "Ayşe Yılmaz", "eposta": "ayse.yilmaz" + AT + "firma.com"}, {"ad": "Ece Taş", "eposta": "ece.tas" + AT + "firma.com"}], "katilimci_eposta": []})
taz()
coz = ns["kimlik_coz"]
def e(ad, **k): return coz(ad, **k)
# 1) katlama ve eşleme
ok("tam ad, Türkçe harf katlama ('AYŞE YILMAZ' = 'Ayse Yilmaz')", e("AYŞE YILMAZ")["eposta"] == "ayse.yilmaz" + AT + "firma.com" and e("Ayse Yilmaz")["eposta"] == "ayse.yilmaz" + AT + "firma.com")
ok("e-posta küçük harfe çevrilir", e("Bora Kaya")["eposta"] == "bora.kaya" + AT + "firma.com")
ok("ilk ad tek kişiye gidiyorsa eşlenir (kısmi güven)", e("Ayşe")["eposta"] == "ayse.yilmaz" + AT + "firma.com" and e("Ayşe")["guven"] < 0.95)
ok("ilk ad birden çok kişiye gidiyorsa EŞLENMEZ, adaylar döner", (lambda r: r["eposta"] is None and r["adaylar"] == ["deniz.aksoy" + AT + "firma.com", "deniz.tekin" + AT + "firma.com"])(e("Deniz")))
ok("'Soyad, Ad' yazımı", e("Selim Kaya")["eposta"] == "selim.kaya" + AT + "firma.com")
ok("baş harfli soyad (Ayşe Y.)", e("Ayşe Y.")["eposta"] == "ayse.yilmaz" + AT + "firma.com")
ok("ara ad takvimde fazla (Ayla Kaya ~ Ayla Nur Kaya)", e("Ayla Kaya")["eposta"] == "ayla.kaya" + AT + "firma.com")
ok("takvimdeki 'Kaya' soyadı için ilk ad yok → Bora ile Selim karışmaz: 'Kaya' eşlenmez", e("Kaya")["eposta"] is None)
ok("Whisper'ın yanlış yazdığı ad eşlenmez (tahmin yok)", e("Ayşa Yılmaz", kisiler=False)["eposta"] is None)
ok("adsız adresin yerel kısmı (ad.soyad" + AT + ") son kaynak, düşük güven", (lambda r: r["eposta"] == "cem.arslan" + AT + "firma.com" and r["kaynak"] == "eposta_yerel" and r["guven"] <= 0.6)(e("Cem Arslan", kisiler=False)))
ok("adresi adlı olarak da bilinen kişi yerel kısımla ikilenmez (Ece Taş tek)", e("Ece Taş", kisiler=False)["kaynak"] == "takvim")
ok("ad içinde e-posta varsa o kullanılır", e("Fatma <Fatma.Er" + AT + "Firma.com>")["eposta"] == "fatma.er" + AT + "firma.com")
ok("kişi olmayan sahip ('Ekip', 'Herkes') işlenmez", e("Ekip")["kaynak"] == "kisi_degil" and e("herkes")["eposta"] is None)
# 2) kullanıcı
ok("kullanıcının tam adı ayardan (kaynak ayar, güven 1)", (lambda r: r["eposta"] == "kemal.duru" + AT + "firma.com" and r["kaynak"] == "ayar" and r["guven"] == 1.0)(e("Kemal Duru")))
# 3) Kişiler ve sıra
CAGRI.clear(); e("Bora Kaya"); ok("takvimde tam eşleşme varsa Kişiler'e gidilmez", CAGRI == [])
KISI["Gamze Uslu"] = {"durum": "ok", "kisiler": [{"ad": "Gamze Uslu", "eposta": ["gamze" + AT + "gmail.com", "gamze.uslu" + AT + "firma.com"]}]}
r = e("Gamze Uslu"); ok("Kişiler: birden çok adreste kullanıcının alan adlısı seçilir", r["eposta"] == "gamze.uslu" + AT + "firma.com" and r["kaynak"] == "kisiler")
KISI["Hakan Ak"] = {"durum": "ok", "kisiler": [{"ad": "Hakan Ak", "eposta": ["hakan" + AT + "a.com", "hakan" + AT + "b.com"]}]}
r = e("Hakan Ak"); ok("Kişiler: alan adı ayıramıyorsa eşlenmez + adaylar", r["eposta"] is None and len(r["adaylar"]) == 2)
KISI["Ilgın Su"] = {"durum": "izin_yok", "hata": "x"}
ok("Kişiler izin vermezse sessizce eşlenmedi", e("Ilgın Su")["eposta"] is None)
n = len(CAGRI); e("Gamze Uslu"); ok("önbellek: ikinci çözümde kaynaklara gidilmez", len(CAGRI) == n and e("Gamze Uslu").get("onbellek"))
# 4) kayıt veritabanı
ns["kimlik_vt_yukle"]([("Tolga Er, Tolgay", "tolga.er" + AT + "firma.com"), ("Pelin Dağ", "pelin" + AT + "a.com,pelin" + AT + "b.com"), ("Adres Yok", "")])
ok("kayıt veritabanı adı + takma ad", e("Tolgay", kisiler=False)["eposta"] == "tolga.er" + AT + "firma.com" and e("Tolga Er", kisiler=False)["kaynak"] == "vt")
ok("veritabanında iki adresli kişi eşlenmez", e("Pelin Dağ", kisiler=False)["eposta"] is None)
# 5) elle düzeltme, birleştirme, kalıcılık
ok("elle düzeltme kalıcı ve öncelikli", ns["kimlik_duzelt"]("Deniz", "Deniz.Aksoy" + AT + "firma.com")["ok"] and e("Deniz")["eposta"] == "deniz.aksoy" + AT + "firma.com" and e("Deniz")["kaynak"] == "elle")
ok("geçersiz e-posta reddedilir", not ns["kimlik_duzelt"]("Nur", "nur" + AT + "")["ok"])
ok("kimlik.json 0600", stat.S_IMODE(os.stat(os.path.join(T, "kimlik.json")).st_mode) == 0o600)
ok("birleştir: Whisper yazımı asıl kişiye gider", ns["kimlik_birlestir"]("Ayşe Yılmaz", "Ayşa Yılmaz")["ok"] and e("Ayşa Yılmaz", kisiler=False)["eposta"] == "ayse.yilmaz" + AT + "firma.com")
d = json.load(open(os.path.join(T, "kimlik.json")))
ok("kimlik_birlesti olayı günlükte", any(o.get("olay") == "kimlik_birlesti" for o in d["olaylar"]))
ok("kendisiyle birleştirilmez", not ns["kimlik_birlestir"]("Bora Kaya", "bora kaya")["ok"])
ns["kimlik_duzelt"]("Deniz", ""); ok("elle kayıt silinince yine belirsiz", e("Deniz")["eposta"] is None)
# 6) ayar değişince/bozuk dosya
open(os.path.join(T, "kimlik.json"), "w").write("{bozuk"); ns["_KIM_DURUM"].update(d=None)
ok("bozuk kimlik.json çökertmez", e("Bora Kaya")["eposta"] == "bora.kaya" + AT + "firma.com")
# 7) kayıtlardaki sahipler
c = sqlite3.connect(os.path.join(T, "karar-grafi.sqlite")); c.execute("CREATE TABLE kayit (id INTEGER PRIMARY KEY, tarih TEXT, tur TEXT, kim TEXT, sahip TEXT)")
bugun = str(datetime.date.today()); eski = str(datetime.date.today() - datetime.timedelta(days=90))
for t, tur, kim, sahip in [(bugun, "is", "Bora Kaya", "Ayşe"), (bugun, "is", None, "Deniz"), (bugun, "karar", "Zeynep Yok", None), (bugun, "is", None, "Ekip"), (eski, "is", None, "Eski Kişi"), (bugun, "soz", None, "Bora Kaya")]:
    c.execute("INSERT INTO kayit (tarih, tur, kim, sahip) VALUES (?,?,?,?)", (t, tur, kim, sahip))
c.commit(); c.close()
o = ns["kimlik_olcum"](30, kisiler=False)
ok("ölçüm: son 30 gün, sahip yoksa kim; kişi olmayan ve eski kayıt hariç", o["toplam_ad"] == 5 and o["kisi_degil_kayit"] == 1 and o["eslenen_ad"] == 2)
es = {x["ad"]: x for x in o["eslenemeyen"]}
ok("eşlenemeyen: belirsiz (Deniz) ve bulunamadı (Zeynep Yok) ayrı nedenle", es["Deniz"]["neden"] == "belirsiz" and es["Zeynep Yok"]["neden"] == "bulunamadi" and "Eski Kişi" not in es)
ok("kimlik_eslenemeyen listeyi verir", len(ns["kimlik_eslenemeyen"](30, kisiler=False)) == 2)
ok("kayıtlar yalnız okunur (satır sayısı aynı)", sqlite3.connect(os.path.join(T, "karar-grafi.sqlite")).execute("SELECT count(*) FROM kayit").fetchone()[0] == 6)
shutil.rmtree(T, ignore_errors=True)
print("\nSONUÇ:", "TAMAM" if not HATA else f"{len(HATA)} hata: {HATA}"); sys.exit(1 if HATA else 0)
