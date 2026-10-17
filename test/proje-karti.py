#!/usr/bin/env python3
# Proje hazırlığı T5 — proje kartı (proje-karti.py): sahte claude ile (kota yok). Aday seçimi (eski sürüm, dışa aktarım, kopya, adla hariç,
# toplantı dökümü girmez; sınır; düzenli klasör belgeleri önde), belge başına çıkarım ve önbellek (ikinci tur 0 çağrı, değişen belge yeniden),
# birleştirme (tek sözcüklü ad + tam ad + takma ad tek kişi), çelişen tarih işareti, düzenli klasörde "fark", veritabanı kipi (kişiler
# veritabanından, istemde yalnız özet + sözlük), toplantıda durma, bozuk JSON'da bir yeniden deneme, onay (kart dosyası, sözlüğe aktarma, CLAUDE.md notu).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/proje-karti.py      (kaldı → çıkış 1)
import importlib.util, json, os, shutil, sqlite3, sys, tempfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-kart-"); P = os.path.join(T, "proje"); U = os.path.join(T, "uyg"); os.makedirs(os.path.join(U, "canli"))
SAHTE = os.path.join(T, "claude"); SAYAC = os.path.join(T, "sayac.jsonl")
# sahte claude: istemdeki "KISI: ad | rol" vb. satırlardan JSON üretir; "BOZUK" geçen belgede ilk cevap bozuk; istemin türünü sayaca yazar
open(SAHTE, "w").write(r'''#!/usr/bin/env python3
import sys, json, re, os
istem = sys.stdin.read(); S = os.environ.get("SAYAC") or "''' + SAYAC + r'''"
yol = (re.search(r"BELGE: (\S+)", istem) or [None, "ozet"])[1]
onceki = sum(1 for l in open(S) if json.loads(l)["yol"] == yol) if os.path.exists(S) else 0
open(S, "a").write(json.dumps({"yol": yol, "tam": '"kisiler"' in istem}) + "\n")
if "BOZUK" in istem and onceki == 0: print(json.dumps({"result": "bozuk cevap", "total_cost_usd": 0.001})); sys.exit()
if yol == "ozet": print(json.dumps({"result": "Deneme projesi: depo taşıma ve tedarikçi seçimi.", "total_cost_usd": 0.002})); sys.exit()
o = {"ozet": f"{yol} özeti", "kisiler": [], "kurumlar": [], "kararlar": [], "tarihler": [], "acik_isler": [], "sozluk": []}
k = "-"
for ln in istem.splitlines():
    km = re.match(r"\[([^\]]+)\] ", ln)
    if km: k = km.group(1)
    m = re.search(r"(KISI|KARAR|TARIH|IS|TERIM|KURUM): (.*)", ln)
    if not m: continue
    tur, v = m.group(1), [x.strip() for x in m.group(2).split("|")]
    if tur == "KISI": o["kisiler"].append({"ad": v[0], "rol": v[1] if len(v) > 1 else "", "takma_adlar": v[2].split(",") if len(v) > 2 and v[2] else [], "konum": k})
    if tur == "KARAR": o["kararlar"].append({"ne": v[0], "ne_zaman": v[1], "kim": v[2] if len(v) > 2 else "", "konum": k})
    if tur == "TARIH": o["tarihler"].append({"ne": v[0], "tarih": v[1], "konum": k})
    if tur == "IS": o["acik_isler"].append({"is": v[0], "sahip": v[1], "tarih": v[2], "konum": k})
    if tur == "TERIM": o["sozluk"].append({"terim": v[0], "aciklama": v[1], "konum": k})
    if tur == "KURUM": o["kurumlar"].append({"ad": v[0], "konum": k})
print(json.dumps({"result": "```json\n" + json.dumps(o, ensure_ascii=False) + "\n```", "total_cost_usd": 0.003}))
''')
os.chmod(SAHTE, 0o755)
BELGE = {
    "CLAUDE.md": "# Proje\n\nKISI: Ayşe Yılmaz | proje yöneticisi | AY\n\nKARAR: Depo Gebze'ye taşınacak | 2026-11-01 | Ayşe\n",
    "belgeler/toplanti-notu.md": "# Not\n\nKISI: Ayşe | yönetici\n\nKISI: AY | koordinatör\n\nKARAR: Depo Gebze'ye taşınacak | 2026-11-15 | Ayşe\n\nTERIM: Gebze Lojistik Merkezi | yeni depo\n\nKURUM: Atlas Taşımacılık\n",
    "belgeler/plan.md": "# Plan\n\nIS: Tedarikçi listesini çıkar | Deniz | 2026-10-25\n\nTARIH: Açılış töreni | 2026-12-01\n\nKISI: Kemal Demir | satın alma\n\nTERIM: Gebze Lojistik Merkezi | depo\n\nTERIM: Tek Belgede Geçen | x\n\nTERIM: kayit.py | betik\n",
    "belgeler/eski-plan-v1.md": "# Plan\n\nIS: Eski iş | Biri | 2026-01-01\n" * 30,
    "belgeler/eski-plan-v2.md": "# Plan\n\nIS: Eski iş | Biri | 2026-01-01\n" * 30 + "ek\n",
    "veri/disa/kisiler.csv": "ad,rol\nKISI: Gizli Kisi | yok\n",
    "belgeler/sifreler.md": "# Hesaplar\n\nKISI: Hariç Kişi | yok\n",
    "belgeler/bozuk.md": "# Bozuk\n\nBOZUK ilk cevap\n\nKISI: Selin Ak | muhasebe\n",
}
for k, m in BELGE.items():
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w", encoding="utf-8").write(m)
os.utime(os.path.join(P, "belgeler/eski-plan-v1.md"), (1e9, 1e9))
os.makedirs(os.path.join(U, "canli"), exist_ok=True); os.symlink(os.path.join(U, "canli"), os.path.join(P, "_canli"))
open(os.path.join(U, "canli", "2026-10-17-1000-deneme.jsonl"), "w").write(json.dumps({"speaker": "Deniz", "time": "10:00", "text": "KISI: Toplantı Kişisi | yok"}) + "\n")
ay = os.path.join(T, "ayar.json")
def ayar_yaz(**ek): json.dump(dict({"alan": "Deneme", "uygulama": U, "proje": P, "ortak": os.path.join(T, "yok"), "claude": SAHTE}, **ek), open(ay, "w"))
ayar_yaz(); os.environ["SUFLOR_AYAR"] = ay; os.environ["SAYAC"] = SAYAC; sys.dont_write_bytecode = True
def yukle():
    sp = importlib.util.spec_from_file_location("kart", os.path.join(KOD, "proje-karti.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
cagri = lambda: [json.loads(l) for l in open(SAYAC)] if os.path.exists(SAYAC) else []
try:
    K = yukle(); c = K.B.baglan(); K.B.tara(c); K.B.guncelle(c)
    ad = [a[0] for a in K.aday_belgeler(c)]
    kontrol("adaylar: düzenli klasör belgesi önde; eski sürüm, dışa aktarım, adla hariç, toplantı dökümü yok",
            ad[0] == "CLAUDE.md" and set(ad) == {"CLAUDE.md", "belgeler/toplanti-notu.md", "belgeler/plan.md", "belgeler/eski-plan-v2.md", "belgeler/bozuk.md"}, str(ad))
    kontrol("sınır: en çok N belge", len(K.aday_belgeler(c, 2)) == 2)
    t = K.cikar(tahmin=True)
    kontrol("tahmin Claude'a sormaz", t["belge"] == 5 and not cagri(), json.dumps(t))
    k = K.cikar(paralel=2)
    ay_ = [p for p in k["kisiler"] if p["ad"] == "Ayşe Yılmaz"]
    kontrol("birleştirme: 'Ayşe Yılmaz', 'Ayşe' ve takma ad 'AY' tek kişi", len(ay_) == 1 and {"Ayşe", "AY"} <= set(ay_[0]["takma_adlar"]) and not any(p["ad"] in ("Ayşe", "AY") for p in k["kisiler"]),
            json.dumps(k["kisiler"], ensure_ascii=False)[:300])
    kr = [x for x in k["kararlar"] if "Gebze" in x["ne"]]
    kontrol("çelişen tarih silinmedi, işaretlendi", len(kr) == 1 and kr[0].get("celiski") == {"ne_zaman": ["2026-11-01", "2026-11-15"]}, json.dumps(kr, ensure_ascii=False))
    kontrol("düzenli klasör: CLAUDE.md'den gelen satır fark değil, yalnız diğer belgeden gelen fark", kr[0]["fark"] is False and
            [x for x in k["kisiler"] if x["ad"] == "Kemal Demir"][0]["fark"] is True and k["kip"] == "duzenli")
    kontrol("sözlük tekilleşti, kaynakları birikti", [m["terim"] for m in k["sozluk"]][:1] == ["Gebze Lojistik Merkezi"] and len(k["sozluk"][0]["kaynaklar"]) == 2)
    kontrol("bozuk JSON'da bir kez daha soruldu, belge girdi", any(p["ad"] == "Selin Ak" for p in k["kisiler"]) and sum(1 for x in cagri() if x["yol"] == "belgeler/bozuk.md") == 2)
    kontrol("proje özeti tek çağrıyla, kaynak satırlarında konum var", k["ozet"].startswith("Deneme projesi") and all(len(s) == 2 and s[1] for p in k["kisiler"] for s in p["kaynaklar"]))
    n1 = len(cagri()); k2 = K.cikar()
    kontrol("ikinci tur: önbellekten, 0 Claude çağrısı", len(cagri()) == n1 and k2["onbellek"] == 5, f"{len(cagri()) - n1} çağrı")
    open(os.path.join(P, "belgeler/plan.md"), "a", encoding="utf-8").write("\nKISI: Yeni Kişi | analist\n"); K.B.guncelle(c); n2 = len(cagri()); k3 = K.cikar()
    kontrol("değişen belge: yalnız o belge + proje özeti yeniden soruldu", len(cagri()) - n2 == 2 and any(p["ad"] == "Yeni Kişi" for p in k3["kisiler"]), f"{len(cagri()) - n2} çağrı")
    json.dump({"meeting": {"title": "x"}}, open(os.path.join(U, "canli", "heartbeat.json"), "w"))
    open(os.path.join(P, "belgeler/plan.md"), "a", encoding="utf-8").write("\nKISI: Bir Kişi Daha | x\n"); K.B.guncelle(c); n3 = len(cagri()); k4 = K.cikar(paralel=1)
    os.remove(os.path.join(U, "canli", "heartbeat.json"))
    kontrol("toplantıda: Claude'a sorulmadı, nedeni yazıldı", len(cagri()) == n3 and "toplantı" in (k4["durdu"] or ""), json.dumps(k4.get("durdu")))
    r = K.onayla(k3)
    s = json.load(open(K.SOZLUK, encoding="utf-8"))
    kontrol("onay: kart dosyası 0600, sözlüğe 1 terim (tek belgede geçen ve dosya adı aktarılmaz), düzenli klasörde CLAUDE.md'ye dokunulmadı", os.stat(K.KART).st_mode & 0o777 == 0o600 and r["sozluk_eklenen"] == 1
            and [t["dogru"] for t in s["terimler"]] == ["Gebze Lojistik Merkezi"] and r["claude_notu"] is False and "Proje kartı" not in open(os.path.join(P, "CLAUDE.md")).read())
    kontrol("ikinci onay sözlüğe tekrar eklemez", K.onayla(k3)["sozluk_eklenen"] == 0)
    # genel kip (kökte düzenli belge yok) → CLAUDE.md'ye taslak not
    os.rename(os.path.join(P, "CLAUDE.md"), os.path.join(P, "belgeler", "giris.md")); open(os.path.join(P, "CLAUDE.md"), "w").write("# Notlar\n")
    K.B.guncelle(c); kg = K.cikar(); kg["kip"] = "genel"
    r2 = K.onayla(kg)
    kontrol("genel kipte CLAUDE.md'ye kısa taslak not (bir kez)", r2["claude_notu"] is True and open(os.path.join(P, "CLAUDE.md")).read().count("## Proje kartı (taslak)") == 1
            and K.onayla(kg)["claude_notu"] is False)
    # veritabanı kipi
    vt = os.path.join(P, "kayit.db"); v = sqlite3.connect(vt); v.execute("CREATE TABLE kisi(ad, gorev)"); v.execute("INSERT INTO kisi VALUES('Zeynep Kaya', 'finans')"); v.commit(); v.close()
    ayar_yaz(veritabani={"yol": "kayit.db", "kisiler": "SELECT ad, gorev FROM kisi"}); K2 = yukle(); n4 = len(cagri())
    kv = K2.cikar()
    yeni = cagri()[n4:]
    kontrol("veritabanı kipi: kişiler veritabanından, belgelerden yalnız özet + sözlük istendi", kv["veritabani"]["kisiler"] == [["Zeynep Kaya", "finans"]] and kv["kisiler"] == []
            and yeni and not any(x["tam"] for x in yeni) and kv["sozluk"] and kv["veritabani"]["kararlar"] is None, json.dumps(kv.get("veritabani"), ensure_ascii=False))
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"proje kartı: {len(hatalar)} sorun" if hatalar else "proje kartı: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
