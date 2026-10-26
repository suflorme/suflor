#!/usr/bin/env python3
# v0.137.0 — Suflor'un çalışma klasörü (ayar calisma): içi dolu bir belge klasörü proje seçilince Suflor'un dosyaları (CLAUDE.md, .claude/, _canli,
# gorusmeler/, belgeler/, _kanit/, _arsiv/) <proje>/Suflor'da; kullanıcının dosyalarına ve proje köküne dokunulmaz. Boş/yeni klasörde ve eski düzende
# (kökte _canli ya da /toplanti komutu) eskisi gibi kökte. Arama proje klasörünü dizinler, Suflor/_arsiv ve .claude dizine girmez; görüşme türü
# Suflor/gorusmeler'den; _canli kısayolu çalışma klasöründen gezilir. Kaldırma Suflor klasörünü kaldırır, belgelere dokunmaz. Sihirbazın
# /api/klasor-bilgi ucu. Deneme ev klasöründe (SUFLOR_EV), aktarıcı kurulmaz (~5 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/calisma.py
import importlib.util, json, os, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV = tempfile.mkdtemp(prefix="calisma-"); os.environ["SUFLOR_EV"] = EV; HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""))
    if not k: HATA.append(ad)
sp = importlib.util.spec_from_file_location("kurulum", os.path.join(KOD, "kurulum.py")); K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
def dosya(y, m="x"):
    os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w", encoding="utf-8").write(m)
try:
    # 1) içi dolu belge klasörü
    pr = os.path.join(EV, "Belgelerim", "Data Science")
    dosya(os.path.join(pr, "Kendi Notum.md"), "Regresyon atölyesi üçüncü haftada yapılacak. Lojistik model karşılaştırması."); dosya(os.path.join(pr, "ML", "model.csv"), "a,b\n1,2\n")
    dosya(os.path.join(pr, "CLAUDE.md"), "# Kullanıcının kendi Claude notu\n")  # kullanıcının kendi CLAUDE.md'si: Suflor'unki sanılmasın
    once = sorted(os.listdir(pr))
    ok("klasor_dolu: kullanıcı öğeleri sayılır (iskelet adları değil)", K.klasor_dolu(pr) == 2, str(K.klasor_dolu(pr)))
    K.tamamla({"ad": "Ayşe Yılmaz", "proje": pr}, "tr"); a = K.ayar(); cal = os.path.join(pr, "Suflor")
    ok("ayarda calisma = <proje>/Suflor, proje = belge klasörü", a.get("calisma") == cal and K.gen(a["proje"]) == pr, json.dumps({k: a.get(k) for k in ("proje", "calisma")}))
    ok("proje kökünde yalnız yeni 'Suflor' klasörü; kullanıcının dosyaları ve CLAUDE.md'si aynen", sorted(os.listdir(pr)) == sorted(once + ["Suflor"])
       and open(os.path.join(pr, "CLAUDE.md"), encoding="utf-8").read() == "# Kullanıcının kendi Claude notu\n", str(sorted(os.listdir(pr))))
    ok("Suflor/ içinde iskelet: CLAUDE.md, /toplanti komutu, gorusmeler, belgeler, _kanit, _arsiv",
       all(os.path.exists(os.path.join(cal, x)) for x in ("CLAUDE.md", ".claude/commands/toplanti.md", "gorusmeler", "belgeler", "_kanit", "_arsiv")))
    ok("Suflor/.claude/settings.json: proje klasörü ek okuma dizini", K.oku_json(os.path.join(cal, ".claude", "settings.json")) == {"permissions": {"additionalDirectories": [pr]}})
    t = open(os.path.join(cal, ".claude", "commands", "toplanti.md"), encoding="utf-8").read()
    ok("/toplanti komutu çalışma klasörünü ve proje belgelerini yazar", f"({cal})" in t and f"proje belgeleri: {pr}" in t and "{{" not in t)
    ok("CLAUDE.md'de proje belgeleri yolu", f"`{pr}`" in open(os.path.join(cal, "CLAUDE.md"), encoding="utf-8").read())
    ok("yollar(): calisma", K.yollar()["calisma"] == cal)
    ok("yeniden tamamla: aynı çalışma klasörü (iç içe Suflor/Suflor yok)", (K.tamamla({"ad": "Ayşe Yılmaz", "proje": pr}, "tr") or True) and K.ayar().get("calisma") == cal
       and not os.path.exists(os.path.join(cal, "Suflor")))
    # arama: proje dizinlenir; Suflor/_arsiv dizine girmez; Suflor/gorusmeler görüşme türü; _canli çalışma klasöründen
    dosya(os.path.join(cal, "gorusmeler", "ayse-toplanti-ozeti-20261026.md"), "# Özet\nKarar: regresyon atölyesi kayıtları açılsın.")
    dosya(os.path.join(cal, "_arsiv", "eski.md"), "eski arşiv regresyon notu")
    canli = os.path.join(EV, "canli-gercek"); dosya(os.path.join(canli, "20261026-Toplanti.jsonl"), json.dumps({"id": "a/1", "speaker": "Ayşe", "time": "01:00", "text": "regresyon atölyesi tarihini konuşalım"}) + "\n")
    os.symlink(canli, os.path.join(cal, "_canli"))
    ay = os.path.join(EV, "Library", "Application Support", "Suflor", "ayar.json"); a = K.ayar(); a["uygulama"] = os.path.join(EV, "uyg"); json.dump(a, open(ay, "w"))
    kod = ("import sys, json; sys.path.insert(0, %r); import baglam as B; c = B.baglan(); B.guncelle(c)\n"
           "print(json.dumps({'on': B.CAL_ON, 'yollar': sorted(r[0] for r in c.execute('SELECT yol FROM dosya')), 'tur': dict(c.execute('SELECT yol, tur FROM dosya').fetchall())}))") % KOD
    r = subprocess.run([sys.executable, "-B", "-c", kod], env=dict(os.environ, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True, timeout=120)
    try: d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: d = {"on": None, "yollar": [], "tur": {}}; print(r.stderr[-800:])
    y = d["yollar"]
    ok("arama: önek Suflor/, belgeler dizinde", d["on"] == "Suflor/" and "Kendi Notum.md" in y and "ML/model.csv" in y, str(y))
    ok("arama: Suflor/_arsiv ve .claude dizine girmez", not any(x.startswith(("Suflor/_arsiv", "Suflor/.claude")) for x in y), str(y))
    ok("arama: Suflor/gorusmeler görüşme türü", d["tur"].get("Suflor/gorusmeler/ayse-toplanti-ozeti-20261026.md") == "gorusme", str(d["tur"]))
    ok("arama: _canli çalışma klasöründen (dizinde _canli/…)", "_canli/20261026-Toplanti.jsonl" in y, str(y))
    # sihirbaz ucu
    ok("klasor-bilgi: dolu klasör → alt klasör", K.calisma_sec(pr, K.ayar()) == cal)
    # 2) boş/yeni klasör ve eski düzen: kökte
    bos = os.path.join(EV, "Suflor-bos"); K.tamamla({"ad": "Ayşe Yılmaz", "proje": bos}, "tr")
    ok("boş klasör: calisma yok, iskelet kökte", "calisma" not in K.ayar() and os.path.isfile(os.path.join(bos, ".claude", "commands", "toplanti.md")) and not os.path.exists(os.path.join(bos, "Suflor")))
    eski = os.path.join(EV, "Eski"); dosya(os.path.join(eski, "rapor.md")); os.symlink(canli, os.path.join(eski, "_canli"))
    ok("eski düzen (kökte _canli): calisma = proje", K.calisma_sec(eski, {}) == eski)
    # 3) kaldırma: Suflor klasörü gider (toplantı notu sorulur → --proje yoksa kalır), belgeler yerinde
    a = K.ayar(); a.update(proje=pr, calisma=cal, uygulama=os.path.join(EV, "uyg")); json.dump(a, open(ay, "w"))
    r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "kurulum.py"), "sil", "--evet", "--proje"], env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True, timeout=60)
    ok("kaldırma: Suflor klasörü tamamen gitti, proje kökü kurulumdan önceki hâlinde", not os.path.exists(cal) and sorted(os.listdir(pr)) == sorted(once), r.stdout[-700:] + str(sorted(os.listdir(pr))))
    ok("kaldırma: kullanıcının dosyaları ve kendi CLAUDE.md'si yerinde", os.path.isfile(os.path.join(pr, "ML", "model.csv"))
       and open(os.path.join(pr, "CLAUDE.md"), encoding="utf-8").read() == "# Kullanıcının kendi Claude notu\n")
finally: shutil.rmtree(EV, ignore_errors=True)
print("calisma: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
