#!/usr/bin/env python3
# Proje hazırlığı T6 — sihirbazın arka ucu (hazirlik.py): tarama özeti (klasörler, adla hariç, kaynak türü, süre tahmini), kullanıcı işaretleri
# (ayar haric / dahil / asil), iş kilidi (ikinci iş başlamaz; Brifing yardımcısının turu çevirme/gömme yapmaz), uçtan uca iş (çevirme ortamı yokken
# de biter; sahte claude ile kart), kart taslağı (önerilen terimler) ve onay (çıkarılan satırlar, yalnız seçilen terimler sözlüğe).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hazirlik.py      (kaldı → çıkış 1)
import fcntl, json, os, shutil, subprocess, sys, tempfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-hz-"); P = os.path.join(T, "proje"); U = os.path.join(T, "uyg"); os.makedirs(os.path.join(U, "canli"))
SAHTE = os.path.join(T, "claude")
open(SAHTE, "w").write(r'''#!/usr/bin/env python3
import sys, json, re
istem = sys.stdin.read()
yol = (re.search(r"BELGE: (\S+)", istem) or [None, "ozet"])[1]
if yol == "ozet": print(json.dumps({"result": "Deneme projesi.", "total_cost_usd": 0.001})); sys.exit()
o = {"ozet": yol + " özeti", "kisiler": [], "kurumlar": [], "kararlar": [], "tarihler": [], "acik_isler": [], "sozluk": []}
for ln in istem.splitlines():
    m = re.search(r"(KISI|TERIM): ([^|]*)\|?(.*)", ln)
    if m and m.group(1) == "KISI": o["kisiler"].append({"ad": m.group(2).strip(), "rol": m.group(3).strip(), "konum": "-"})
    if m and m.group(1) == "TERIM": o["sozluk"].append({"terim": m.group(2).strip(), "aciklama": m.group(3).strip(), "konum": "-"})
print(json.dumps({"result": json.dumps(o, ensure_ascii=False), "total_cost_usd": 0.002}))
''')
os.chmod(SAHTE, 0o755)
BELGE = {
    "belgeler/plan.md": "# Plan\n\nKISI: Ayşe Yılmaz | yönetici\n\nTERIM: Gebze Lojistik Merkezi | depo\n\nTERIM: Atlas Taşıma | firma\n",
    "belgeler/not.md": "# Not\n\nKISI: Kemal Demir | satın alma\n\nTERIM: Gebze Lojistik Merkezi | depo\n\nTERIM: Atlas Taşıma | firma\n",
    "belgeler/not-kopya.md": "# Not\n\nKISI: Kemal Demir | satın alma\n\nTERIM: Gebze Lojistik Merkezi | depo\n\nTERIM: Atlas Taşıma | firma\n",
    "belgeler/sifreler.md": "# Hesaplar\n\nKISI: Gizli Kişi | yok\n",
    "kisisel/gunluk.md": "# Günlük\n\nKISI: Özel Kişi | yok\n",
    "ozet/plan-ozeti.md": "# Plan özeti\n\nKISI: Özet Kişi | yok\n",
    "gorseller/ekran.png": "PNG değil ama uzantısı png",
}
for k, m in BELGE.items():
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w", encoding="utf-8").write(m)
ay = os.path.join(T, "ayar.json")
def ayar(): return json.load(open(ay))
def ayar_yaz(**ek): a = dict({"alan": "Deneme", "uygulama": U, "proje": P, "ortak": os.path.join(T, "yok"), "claude": SAHTE}, **ek); json.dump(a, open(ay, "w"))
ayar_yaz()
ENV = dict(os.environ, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1")
def hz(*a, girdi=None):
    r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "hazirlik.py"), *a], input=girdi, capture_output=True, text=True, env=ENV, timeout=120)
    try: return json.loads(r.stdout.strip().splitlines()[-1]), r
    except (ValueError, IndexError): return None, r
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
try:
    o, _ = hz("ozet")
    kontrol("taramadan önce özet boş (tarama yok)", o and o["tarama"] is None and o["is"]["calisiyor"] is False, json.dumps(o)[:200])
    t, r = hz("tara"); o, _ = hz("ozet")
    tr = (o or {}).get("tarama") or {}
    kontrol("tarama: dosya sayısı, birebir kopya, adla hariç (sifreler.md)", t and t["ok"] and tr["sayilar"]["dosya"] == 7 and tr["sayilar"]["kopya"] == 1
            and [x["yol"] for x in tr["haric"]] == ["belgeler/sifreler.md"], json.dumps(tr.get("sayilar"))[:300] + r.stderr[-300:])
    kontrol("klasörler listesi (dosya sayısıyla)", {k["ad"]: k["dosya"] for k in tr["klasorler"]} == {"belgeler": 4, "kisisel": 1, "ozet": 1, "gorseller": 1}, json.dumps(tr["klasorler"]))
    kontrol("kaynak türü: 'ozet' klasörü/adı türetilmiş", any(x["yol"] == "ozet/plan-ozeti.md" for x in tr["kaynak_turu"]), json.dumps(tr["kaynak_turu"]))
    th = o["tahmin"]
    kontrol("tahmin: çevrilecek 1 görüntü, kart belgesi sayısı, süre", th["cevir"] == {".png": 1} and th["kart_belge"] >= 3 and th["sn"] >= 1 and th["cevirme_kurulu"] is False, json.dumps(th))
    # kullanıcı işaretleri
    ayar_yaz(haric=["kisisel"], dahil=["belgeler/sifreler.md"], asil=["ozet"]); hz("tara"); o, _ = hz("ozet"); tr = o["tarama"]
    kontrol("ayar haric: klasör hariç görünür, dosyası taramada yok", next(k for k in tr["klasorler"] if k["ad"] == "kisisel")["haric"] and tr["sayilar"]["dosya"] == 6, json.dumps(tr["klasorler"]))
    kontrol("ayar dahil: adla hariç dosya artık hariç değil, 'dahil' listesinde", not tr["haric"] and tr["dahil"] == ["belgeler/sifreler.md"])
    kontrol("ayar asil: klasördeki dosya asıl sayılır", not any(x["yol"].startswith("ozet/") for x in tr["kaynak_turu"]) and tr["asil"] == ["ozet"], json.dumps(tr["kaynak_turu"]))
    ayar_yaz(haric=["kisisel"])
    # kilit: tutuluyken ikinci iş başlamaz, baglam hazirlik_suruyor doğru
    kf = open(os.path.join(U, "hazirlik.kilit"), "a"); fcntl.flock(kf, fcntl.LOCK_EX)
    _, r = hz("calis")
    o, _ = hz("ozet")
    bs = subprocess.run([sys.executable, "-B", "-c", f"import importlib.util as u;s=u.spec_from_file_location('b','{KOD}/baglam.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.hazirlik_suruyor())"],
                        capture_output=True, text=True, env=ENV).stdout.strip()
    kontrol("kilit tutuluyken: ikinci iş çıkar (2), özet 'çalışıyor', Brifing turu bekler", r.returncode == 2 and o["is"]["calisiyor"] and bs == "True", f"{r.returncode} {bs}")
    fcntl.flock(kf, fcntl.LOCK_UN); kf.close()
    # uçtan uca (çevirme ortamı ve anlam modeli yok; kart sahte claude ile)
    _, r = hz("calis", "--kart"); o, _ = hz("ozet"); e = o["is"]
    kontrol("iş bitti: evre 'bitti', kilit bırakıldı, sonuç sayıları", r.returncode == 0 and e["evre"] == "bitti" and not e["calisiyor"] and e["sonuc"]["belge"] >= 3 and e["sonuc"]["parca"] > 0,
            json.dumps(e)[:400] + r.stderr[-400:])
    kontrol("çevirme ortamı yokken 'durdu' sayılmaz, gömme 'kurulu değil'", e["cevir"]["durdu"] and "ortamı yok" in e["cevir"]["durdu"] and e["gomme"]["durdu"] == "anlam araması kurulu değil", json.dumps(e)[:300])
    kontrol("kart adımı ilerleme kaydı (n = toplam)", e["adim"].get("kart", {}).get("n") == e["adim"].get("kart", {}).get("toplam") > 0 and e["kart"]["hata"] == 0, json.dumps(e.get("adim")))
    kontrol("özette kart taslağı (onaysız)", o.get("kart") and o["kart"]["onay"] is None and o["kart"]["sayilar"]["kisiler"] >= 2, json.dumps(o.get("kart")))
    k, _ = hz("kart")
    kisi = [p["ad"] for p in k["kisiler"]]
    kontrol("kart: hariç klasör ve dahil edilmeyen gizli dosya kişisi yok", "Özel Kişi" not in kisi and "Gizli Kişi" not in kisi and {"Ayşe Yılmaz", "Kemal Demir"} <= set(kisi), str(kisi))
    oneri = {m["terim"]: m["oneri"] for m in k["sozluk"]}
    kontrol("kart: iki belgede geçen terimler önerili", oneri.get("Gebze Lojistik Merkezi") and oneri.get("Atlas Taşıma"), json.dumps(oneri, ensure_ascii=False))
    i_kemal = kisi.index("Kemal Demir")
    sonuc, r = hz("kart-onayla", girdi=json.dumps({"cikar": {"kisiler": [i_kemal]}, "terimler": ["Atlas Taşıma"]}))
    kart = json.load(open(os.path.join(U, "proje-karti.json")))
    soz = json.load(open(os.path.join(U, "canli", "sozluk.json")))
    kontrol("onay: çıkarılan kişi kartta yok, onay kaydı 'sihirbaz'", "Kemal Demir" not in [p["ad"] for p in kart["kisiler"]] and kart["onay"]["kim"] == "sihirbaz", (r.stderr or "")[-300:])
    kontrol("onay: yalnız seçilen terim sözlükte", [x["dogru"] for x in soz["terimler"]] == ["Atlas Taşıma"] and sonuc["sozluk_eklenen"] == 1, json.dumps(soz, ensure_ascii=False)[:200])
    o, _ = hz("ozet")
    kontrol("özette kart onaylı", o["kart"]["onay"] and o["kart"]["onay"]["kim"] == "sihirbaz")
    kontrol("hazirlik.json ve kart dosyaları yalnız uygulama klasöründe (proje klasörüne yazılmadı)",
            not any(f.startswith(("hazirlik", "proje-karti", "tarama")) for _, _, fs in os.walk(P) for f in fs))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("hazırlık:", "✓ hepsi geçti" if not hatalar else f"✗ {len(hatalar)} kaldı")
sys.exit(1 if hatalar else 0)
