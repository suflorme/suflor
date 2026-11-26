#!/usr/bin/env python3
# Görünen ad → gerçek ad (v0.255.0, 26 Kasım): baglayici.takma_ad_haritasi / gorunen_ad_cozucu birim testi (geçici sqlite, uydurma adlar) +
# toplanti-claude.py ad_uygula → gercek_ad_coz üzerinden temiz döküm (md, vtt, başlık sayımı). Öncelik: elle kisi-es > kisi_takma > dokunma.
#   PYTHONDONTWRITEBYTECODE=1 python3 -B test/takma-ad.py      (kaldı → çıkış 1)
import json, os, shutil, sqlite3, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import baglayici as B
T = tempfile.mkdtemp(prefix="suflor-takma-")
hata = []
def bak(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(ad) if not k else None

# --- 1. birim: geçici kayıt veritabanı ---
DB = os.path.join(T, "kayit.db"); con = sqlite3.connect(DB)
con.executescript("""
CREATE TABLE kisi (id TEXT PRIMARY KEY, ad TEXT, lakap TEXT, durum TEXT);
CREATE TABLE kisi_takma (kisi_id TEXT, ad TEXT, baglam TEXT);
INSERT INTO kisi VALUES ('zey','Zeynep Kayaoğlu',NULL,'Aktif'), ('bur','Burak Tandoğan',NULL,'Aktif'), ('bur2','Burak Tandogan Eski',NULL,'Birleştirildi'),
                        ('ece','Ece Varol',NULL,NULL), ('ece2','Ece Varolcan',NULL,'Aktif'), ('kul','Deniz Ak',NULL,'Aktif');
INSERT INTO kisi_takma VALUES ('zey','Zed Kaya','sistem görünen adı'), ('zey','zeynep kayaoglu',''), ('zey','CMO','rol'), ('zey','Zizi','takma (muhtemel)'),
  ('zey','Zey K','teyitsiz yazım'), ('zey','zey' || '@' || 'ornek.test',''), ('bur','Bobby T','Meet görünen adı'), ('bur2','Bob Eski',''),
  ('ece','Evi','takma'), ('ece2','Evi','takma'), ('ece','Ece V',''), ('ece2','Ece V','yazım muhtemel'), ('kul','Deniz A','');
""")
con.commit()
satir = lambda q: con.execute(q).fetchall()
h, el = B.takma_ad_haritasi(satir)
bak("benzersiz takma ad çevrilir (büyük/küçük harf, Türkçe harf duyarsız)", h.get(B.ad_norm("ZED KAYA")) == "Zeynep Kayaoğlu" and h.get(B.ad_norm("bobby t")) == "Burak Tandoğan")
bak("iki kişiye çıkan takma ad atlanır", B.ad_norm("Evi") not in h and el.get("birden çok kişiye çıkıyor", 0) >= 1)
bak("kuşkulu takma ad da belirsizliğe sayılır (Ece V)", B.ad_norm("Ece V") not in h)
bak("rol kısaltması (CMO) atlanır", B.ad_norm("CMO") not in h and el.get("rol/unvan kısaltması") == 1)
bak("muhtemel/teyitsiz atlanır", B.ad_norm("Zizi") not in h and B.ad_norm("Zey K") not in h and el.get("muhtemel/teyitsiz/ad değil", 0) >= 2)
bak("e-posta atlanır", not any("@" in k for k in h) and el.get("e-posta ya da boş") == 1)
bak("birleştirilmiş kişinin takma adı atlanır", B.ad_norm("Bob Eski") not in h and el.get("birleştirilmiş ya da kişisi yok") == 1)
bak("kişinin kendi adı eşleme üretmez", B.ad_norm("Zeynep Kayaoğlu") not in h)
c = B.gorunen_ad_cozucu(satir, None, ben=("Deniz",))
bak("çözücü: görünen ad → gerçek ad", c("Zed  Kaya") == "Zeynep Kayaoğlu")
bak("çözücü: kendi adı ve bilinmeyen ad dokunulmaz", c("ZEYNEP KAYAOGLU") == "ZEYNEP KAYAOGLU" and c("Yabancı Biri") == "Yabancı Biri")
bak("çözücü: kullanıcının kendisi değişmez (Deniz A)", c("Deniz A") == "Deniz A")
bak("çözücü: yer tutucu etiketler değişmez", all(c(x) == x for x in ("Karşı taraf 2", "Bilinmeyen konuşmacı", "You", "Claude", "?", "", None)))
es = {B.ad_norm("Zed Kaya"): "Zeynep K. (elle)", B.ad_norm("Kemal Yok"): "Kemal Var"}
c2 = B.gorunen_ad_cozucu(satir, lambda a: es.get(B.ad_norm(a), a), ben=("Deniz",))
bak("kisi-es veritabanını ezer", c2("Zed Kaya") == "Zeynep K. (elle)" and c2("Kemal Yok") == "Kemal Var" and c2("Bobby T") == "Burak Tandoğan")
c3 = B.gorunen_ad_cozucu(None, lambda a: es.get(B.ad_norm(a), a))
bak("veritabanı yokken yalnız kisi-es", c3("Kemal Yok") == "Kemal Var" and c3("Bobby T") == "Bobby T")
def bozuk(q): raise sqlite3.OperationalError("no such table")
bak("veritabanı okunamazsa sessizce dokunmaz", B.gorunen_ad_cozucu(bozuk)("Bobby T") == "Bobby T")
bak("tablosu olmayan veritabanı (boş satır) dokunmaz", B.gorunen_ad_cozucu(lambda q: [])("Bobby T") == "Bobby T")
con.close()

# --- 2. uçtan uca: temiz döküm (md + vtt + başlık sayımı) ---
canli, OUT = os.path.join(T, "canli"), os.path.join(T, "cikti"); os.makedirs(canli); os.makedirs(OUT)
md = "2026-11-26-1500-Deneme-Toplantisi"; t = 1795700000.0
rows = [{"at": "x", "id": "w-ben-1", "time": "15:00:00", "speaker": "Deniz A", "text": "Merhaba.", "src": "whisper", "kanal": "ben", "t0": t, "t1": t + 1},
        {"at": "x", "id": "w-karsi-2", "time": "15:00:20", "speaker": "Zed Kaya", "text": "Selam, başlayalım.", "src": "whisper", "kanal": "karsi", "t0": t + 20, "t1": t + 22},
        {"at": "x", "id": "w-karsi-3", "time": "15:00:40", "speaker": "Bobby T", "text": "Ben de buradayım.", "src": "whisper", "kanal": "karsi", "t0": t + 40, "t1": t + 42},
        {"at": "x", "id": "w-karsi-4", "time": "15:01:00", "speaker": "Karşı taraf 2", "text": "Bir soru.", "src": "whisper", "kanal": "karsi", "t0": t + 60, "t1": t + 62}]
open(os.path.join(canli, md + ".jsonl"), "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
open(os.path.join(canli, md + ".md"), "w").write("# Canlı transkript — Deneme Toplantısı\n")
def ayar_yaz(vt):
    a = {"alan": "Test", "ad": "Deniz Ak", "uygulama": os.path.join(T, "uyg"), "proje": T, "ortak": os.path.join(T, "ortak"), "teshis": False, "dil": "tr", "proje_vt": False}
    if vt: a["veritabani"] = {"yol": DB}
    json.dump(a, open(os.path.join(T, "ayar.json"), "w"), ensure_ascii=False)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"))
def cli(*a): return subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, *a], capture_output=True, text=True, env=env)
ayar_yaz(True)
r = cli("dokum", md + ".md", "--cikti", OUT, "--kim", "Deneme")
m = next((open(os.path.join(OUT, f), encoding="utf-8").read() for f in os.listdir(OUT) if f.endswith(".md")), "")
v = next((open(os.path.join(OUT, f), encoding="utf-8").read() for f in os.listdir(OUT) if f.endswith(".vtt")), "")
bak("döküm yazıldı", r.returncode == 0 and m and v)
bak("md: görünen ad gerçek adla", "] Zeynep Kayaoğlu:**" in m and "] Burak Tandoğan:**" in m and "Zed Kaya" not in m and "Bobby T" not in m)
bak("md başlık sayımı gerçek adla", "Zeynep Kayaoğlu 1" in m and "Burak Tandoğan 1" in m)
bak("vtt: gerçek ad", "<v Zeynep Kayaoğlu>" in v and "<v Burak Tandoğan>" in v and "Zed Kaya" not in v)
bak("kullanıcı ve yer tutucu değişmedi", "] Deniz A:**" in m and "] Karşı taraf 2:**" in m)
bak(".jsonl değişmedi", "Zed Kaya" in open(os.path.join(canli, md + ".jsonl"), encoding="utf-8").read())
r = cli("kisi-es", "--ekle", "Zed Kaya", "Zeynep Elle")
r = cli("dokum", md + ".md", "--goster", "--kim", "Deneme")
bak("kisi-es veritabanını ezer (döküm)", "] Zeynep Elle:**" in r.stdout and "] Burak Tandoğan:**" in r.stdout)
ayar_yaz(False)
r = cli("dokum", md + ".md", "--goster", "--kim", "Deneme")
bak("veritabanı yokken yalnız kisi-es (döküm)", r.returncode == 0 and "] Zeynep Elle:**" in r.stdout and "] Bobby T:**" in r.stdout)
shutil.rmtree(T, ignore_errors=True)
print("takma ad: ✓ hepsi geçti" if not hata else f"takma ad: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
