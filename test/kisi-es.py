#!/usr/bin/env python3
# Kişi eş adları (yapi.py kisi_es_*): hatalı ya da İngilizce yazılmış kişi adı → doğru ad. Okurken (kayit_listesi, bugun_veri, graf_kisi, sozler, disa_aktar),
# yazarken (graf_yaz, soz_ekle), mevcut veriyi düzeltme (kuru/uygula/yedek), sözlük bağlantısı, komut satırı. Kurgu adlarla.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisi-es.py      (kaldı → çıkış 1)
import datetime, glob, json, os, shutil, sqlite3, subprocess, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
hata = []
def bak(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else "\n" + ek))
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-kisies-"); C = os.path.join(T, "canli"); os.makedirs(C); bugun = datetime.date(2026, 11, 5)
try:
    def y(top, ogeler): yapi.graf_yaz(C, {"baslik": "T " + top, "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    # eşleme yokken: aynı kişi üç adla
    y("2026-11-03-1000-A", [{"tur": "is", "metin": "Birinci", "sahip": "Zed K", "tarih": "2026-11-09"}, {"tur": "is", "metin": "İkinci", "sahip": "Zeynep Kaya", "tarih": "2026-11-09"},
                            {"tur": "karar", "metin": "Karar bir", "kim": "Johnny Orman", "netlik": "acik"}, {"tur": "is", "metin": "Üçüncü", "sahip": "Cahit Orman"},
                            {"tur": "soru", "metin": "Soru bir", "kim": "ZED  k"}, {"tur": "is", "metin": "Benim", "sahip": "Ayşe D"}])
    v0 = yapi.kayit_listesi(C, "Ayşe Deneme", bugun)
    bak("eşleme yokken süzgeçte aynı kişi birden çok adla", {"Zed K", "Zeynep Kaya", "Johnny Orman", "Cahit Orman"} <= set(v0["kisiler"]))
    bak("eş ad ekle; boş ve aynı ad eklenmez", yapi.kisi_es_ekle(C, "Zed K", "Zeynep Kaya") == ("Zed K", "Zeynep Kaya") and yapi.kisi_es_ekle(C, "Johnny Orman", "Cahit Orman")
        and yapi.kisi_es_ekle(C, "", "X") is None and yapi.kisi_es_ekle(C, "zeynep kaya", "ZEYNEP KAYA") is None and yapi.kisi_es_ekle(C, "Ayşe D", "Ayşe") is not None)
    v = yapi.kayit_listesi(C, "Ayşe Deneme", bugun)
    bak("okurken: süzgeç listesinde tek ad", sorted(v["kisiler"]) == ["Ayşe", "Cahit Orman", "Zeynep Kaya"] and not {"Zed K", "Johnny Orman"} & set(v["kisiler"]))
    d = {x["metin"]: x for x in v["kayitlar"]}
    bak("okurken: sahip/kim alanları doğru ad (harf ve boşluk duyarsız)", d["Birinci"]["kim"] == "Zeynep Kaya" and d["Karar bir"]["kim"] == "Cahit Orman" and d["Soru bir"]["kim"] == "Zeynep Kaya")
    bak("okurken: Senden beklenenler eşlemeyle (kullanıcı eş adı da kendi sayılır)", d["Benim"]["kendi"] is True)
    b = yapi.bugun_veri(C, "Ayşe Deneme", bugun)
    bak("bugun_veri: kendi işi eş adla bulunur, başkaları doğru adla", [x["metin"] for x in b["kendi"]] == ["Benim"] or "Benim" in [x["metin"] for x in b["kendi"]])
    bak("bugun_veri: başkalarının işi doğru ad", all(x["kim"] != "Zed K" for x in b["kendi"] + b["baskalari"]))
    gk = yapi.graf_kisi(C, "Zed K", 10)
    bak("graf_kisi: eş adla sorulunca doğru adın tüm kayıtları, satırlarda doğru ad", {r[4] for r in gk} >= {"Birinci", "İkinci"} and all(r[2] in (None, "Zeynep Kaya") or r[3] in (None, "Zeynep Kaya") for r in gk))
    bak("sozler(kim): eş adla da doğru adla da aynı sonuç", [x["metin"] for x in yapi.sozler(C, "Zed K")] == [x["metin"] for x in yapi.sozler(C, "Zeynep Kaya")] and len(yapi.sozler(C, "Zed K")) == 2)
    csv_, _, n = yapi.disa_aktar(C, "csv")
    bak("dışa aktarma: doğru ad", "Zed K" not in csv_ and "Johnny" not in csv_ and "Zeynep Kaya" in csv_ and n == 6)
    # yazarken
    y("2026-11-04-0900-B", [{"tur": "is", "metin": "Yeni iş", "sahip": "ZED K", "tarih": "2026-11-12"}, {"tur": "iddia", "metin": "İddia", "kim": "johnny orman"}])
    c = sqlite3.connect(os.path.join(C, "karar-grafi.sqlite")); ham = dict(c.execute("SELECT metin, COALESCE(sahip, kim) FROM kayit WHERE metin IN ('Yeni iş', 'İddia')").fetchall())
    bak("yazarken: graf_yaz kişi alanlarını eşlemeyle yazar", ham == {"Yeni iş": "Zeynep Kaya", "İddia": "Cahit Orman"})
    s = yapi.soz_ekle(C, "Zed K", "Söz ver"); bak("yazarken: soz_ekle", s["kim"] == "Zeynep Kaya")
    ey = yapi.eylem_esle(C, [{"id": "e1", "tur": "takvim", "baslik": "Toplantı kur"}], "Zed K", "x.md")
    bak("yazarken: eylem_esle sahibi", ey == 1 and c.execute("SELECT sahip FROM kayit WHERE bag = 'eylem:e1'").fetchone()[0] == "Zeynep Kaya")
    c.close()
    # mevcut veriyi düzelt
    c = sqlite3.connect(os.path.join(C, "karar-grafi.sqlite")); c.execute("UPDATE kayit SET sahip = 'Zed K' WHERE metin = 'Yeni iş'"); c.commit(); c.close()
    ham_say = lambda: sqlite3.connect(os.path.join(C, "karar-grafi.sqlite")).execute("SELECT COUNT(*) FROM kayit WHERE kim IN ('Zed K', 'ZED  k', 'Johnny Orman') OR sahip IN ('Zed K', 'Ayşe D')").fetchone()[0]
    before = ham_say(); k = yapi.kisi_es_uygula(C, kuru=True)
    bak("kuru: sayar, yazmaz, yedek yok", k["degisen"] == before and before >= 5 and ham_say() == before and not glob.glob(os.path.join(C, "*.yedek-*")) and k["adlar"].get("Zed K", 0) >= 1)
    u = yapi.kisi_es_uygula(C)
    yd = glob.glob(os.path.join(C, "karar-grafi.sqlite.yedek-*"))
    bak("uygula: kayıtlar düzelir, sayı kurudakiyle aynı, tarihli yedek alınır", u["degisen"] == k["degisen"] and ham_say() == 0 and len(yd) == 1 and u["yedek"] == yd[0]
        and sqlite3.connect(yd[0]).execute("SELECT COUNT(*) FROM kayit WHERE sahip = 'Zed K'").fetchone()[0] >= 1)
    bak("uygula ikinci kez: değişecek kayıt yok, yeni yedek yok", yapi.kisi_es_uygula(C)["degisen"] == 0 and len(glob.glob(os.path.join(C, "karar-grafi.sqlite.yedek-*"))) == 1)
    # sözlük bağlantısı
    bak("sözlük: yanlış biçim grafta kişi adı değilse eş ad eklenmez", yapi.kisi_es_sozluk_ekle(C, "Kubernetes", "Kuberneteş") is None)
    y("2026-11-05-1000-C", [{"tur": "is", "metin": "Son", "sahip": "Sam Ket"}])
    bak("sözlük: grafta kişi adı olan yanlış biçim eş ada girer", yapi.kisi_es_sozluk_ekle(C, "sam ket", "Samet Kaya") == ("sam ket", "Samet Kaya")
        and yapi.kayit_listesi(C, "", bugun)["kayitlar"][0]["kim"] in ("Samet Kaya", "Cahit Orman", "Zeynep Kaya", "Ayşe"))
    bak("zincir: doğru ad da eş adsa asıl adına", yapi.kisi_es_ekle(C, "Samet K", "sam ket") == ("Samet K", "Samet Kaya"))
    bak("sil/liste", yapi.kisi_es_sil(C, "SAMET K") == 1 and ("Samet K", "Samet Kaya") not in yapi.kisi_es_liste(C))
    # komut satırı (yalıtılmış canlı klasörü; gerçek ayar/aktarıcıya dokunmaz)
    T2 = os.path.join(T, "k2"); os.makedirs(os.path.join(T2, "uyg")); shutil.copy(os.path.join(C, "karar-grafi.sqlite.yedek-" + yd[0].rsplit("yedek-", 1)[1]), os.path.join(T2, "karar-grafi.sqlite"))
    ay = os.path.join(T2, "ayar.json"); json.dump({"uygulama": os.path.join(T2, "uyg"), "proje": T2, "port": 8791}, open(ay, "w"))
    def tc(*a): return subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", T2, *a], capture_output=True, text=True, timeout=60, env=dict(os.environ, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1"))
    r = tc("kisi-es", "--ekle", "Zed K", "Zeynep Kaya"); bak("komut: --ekle", "eş ad eklendi" in r.stdout, r.stdout + r.stderr)
    r = tc("kisi-es", "--kuru"); bak("komut: --kuru sayar", "kuru: " in r.stdout and "kayıtta kişi adı değişecek" in r.stdout and "Zed K" in r.stdout, r.stdout + r.stderr)
    r = tc("kisi-es", "--uygula"); bak("komut: --uygula yedek yolu + sayı", "düzeltildi" in r.stdout and "yedek:" in r.stdout, r.stdout + r.stderr)
    r = tc("kisi-es"); bak("komut: liste", "Zed K → Zeynep Kaya" in r.stdout, r.stdout + r.stderr)
    r = tc("sozluk", "--ekle", "Zed K", "Zeynep Kaya"); bak("komut: sozluk --ekle çökmez", r.returncode == 0 and "eklendi" in r.stdout, r.stdout + r.stderr)
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not hata else 'KALDI: ' + str(len(hata))}")
sys.exit(1 if hata else 0)
