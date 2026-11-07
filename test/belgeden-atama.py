#!/usr/bin/env python3
# Belgeden atama (7 Kasım, S211, A yolu): yapi.belge_isleri (kural tabanlı iş maddesi: başlık altı madde, onay kutusu, önek, tablo; sahip/vade ayıklama; bitmiş madde yok),
# yapi.belge_parcalari (düz metin doğrudan, ötekiler çevirme önbelleğinden), yapi.belge_onerileri (proje kartı + toplantı belgesi; kayıttakini, reddedileni, gizli toplantı belgesini önermez,
# deneme belgesi yalnız deneme=True ile; kaynak adı ve satırı), yapi.belge_oneri_kabul (kayit_olustu + is_atandi, sahipsizse yalnız kayit_olustu; ikinci kez yok),
# yapi.belge_oneri_reddet, ortak klasöre yalnız gizli/deneme olmayanın olayı gider; aktarıcıda GET/POST /belge-oneri (anahtarlı, sahibin e-postası kimlik modülünden).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/belgeden-atama.py      (kaldı → çıkış 1)
AT = "@"
import datetime, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="suflor-belge-"); AY = os.path.join(T, "ayar.json"); json.dump({"ad": "Ece Deneme"}, open(AY, "w")); os.environ["SUFLOR_AYAR"] = AY
import yapi; from bosport import bos_port
hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
C = os.path.join(T, "canli"); os.makedirs(C); rl = None
try:
    BELGE = """# Proje notu
Giriş paragrafı, iş değil.
- Bu madde başlık altında değil

## Aksiyonlar
- Sözleşme taslağını gözden geçir — Doruk Ersoy
- Bütçe tablosunu güncelle (Ece) vade: 2026-11-20
1. Tedarikçiye dönüş yap @Selin
- [x] Bitmiş iş yazılmaz
- Sunum hazırlandı ✓

## Notlar
- Bu madde de iş değil
- [ ] Toplantı odasını ayarla
TODO: Lisans yenilemesini kontrol et, sorumlu: Doruk Ersoy, 15.12.2026

| Görev | Sorumlu | Vade |
|---|---|---|
| Ölçüm raporunu yaz | Selin Arı | 2026-11-30 |
| Tamamlandı işi | Selin Arı | 2026-11-01 |
"""
    m = yapi.belge_isleri(BELGE); d = {x["metin"]: x for x in m}
    bak("iş maddeleri: başlık altı, onay kutusu, TODO öneki, tablo; başlık dışı madde ve bitmiş iş yok",
        list(d) == ["Sözleşme taslağını gözden geçir", "Bütçe tablosunu güncelle", "Tedarikçiye dönüş yap", "Toplantı odasını ayarla", "Lisans yenilemesini kontrol et", "Ölçüm raporunu yaz"], list(d))
    bak("sahip ayıklama: — Ad, (Ad), @Ad, sorumlu:, tablo sütunu", [d[k]["sahip"] for k in d] == ["Doruk Ersoy", "Ece", "Selin", "", "Doruk Ersoy", "Selin Arı"], [d[k]["sahip"] for k in d])
    bak("vade: ISO, gg.aa.yyyy → ISO, tablo; satır numarası", d["Bütçe tablosunu güncelle"]["vade"] == "2026-11-20" and d["Lisans yenilemesini kontrol et"]["vade"] == "2026-12-15"
        and d["Ölçüm raporunu yaz"]["vade"] == "2026-11-30" and d["Sözleşme taslağını gözden geçir"]["satir"] == 6, m)
    bak("boş metin → []", yapi.belge_isleri("") == [] and yapi.belge_isleri(None) == [])
    # belgeler: düz metin + önbellekten docx; toplantılar: normal, gizli, deneme
    BL = os.path.join(T, "belgeler"); os.makedirs(BL); ONB = os.path.join(T, "onbellek")
    open(os.path.join(BL, "notlar.md"), "w", encoding="utf-8").write(BELGE)
    open(os.path.join(BL, "plan.docx"), "wb").write(b"PK sahte docx")
    sha = hashlib.sha256(open(os.path.join(BL, "plan.docx"), "rb").read()).hexdigest(); os.makedirs(os.path.join(ONB, sha[:2]))
    json.dump({"parcalar": [["s. 2", "Yapılacaklar:\n- Kurulum rehberini çevir — Doruk Ersoy"]]}, open(os.path.join(ONB, sha[:2], sha + ".json"), "w", encoding="utf-8"))
    open(os.path.join(BL, "gizli.md"), "w", encoding="utf-8").write("## Aksiyonlar\n- Gizli toplantı maddesi — Doruk Ersoy\n")
    open(os.path.join(BL, "deneme.md"), "w", encoding="utf-8").write("## Aksiyonlar\n- Deneme toplantısı maddesi — Doruk Ersoy\n")
    open(os.path.join(BL, "okunmaz.pdf"), "wb").write(b"%PDF sahte")
    bak("parçalar: düz metin doğrudan, docx önbellekten, önbelleksiz pdf None", yapi.belge_parcalari(os.path.join(BL, "notlar.md"))[0][1].startswith("# Proje")
        and yapi.belge_parcalari(os.path.join(BL, "plan.docx"), ONB)[0][0] == "s. 2" and yapi.belge_parcalari(os.path.join(BL, "okunmaz.pdf"), ONB) is None)
    BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"; N, G, DN = "2026-11-06-1000-Proje", "2026-11-06-1200-Ozel", "2026-11-06-1400-Test-4"
    for t, ek in ((N, ""), (G, "| 12:00:05 | **GİZLİ** | açıldı | |\n"), (DN, "")):
        open(os.path.join(C, t + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {t}\n\n" + BAS + "| 10:00:00 | Ece Deneme | merhaba | |\n" + ek)
    yapi.graf_yaz(C, {"baslik": "Proje", "tarih": "2026-11-06", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "Toplantı odasını ayarla.", "sahip": "Ece Deneme"}]}]}, N + ".md")
    KART = {"acik_isler": [{"is": "Pilot sonuçlarını derle", "sahip": ["Selin Arı"], "tarih": "2026-11-25", "kaynaklar": [["/x/Proje/rapor.pdf", "s. 4"]]},
                           {"is": "Sözleşme taslağını gözden geçir", "sahip": [], "kaynaklar": [["/x/b.docx", ""]]}]}  # belgede de var: tek öneri
    BELGELER = [{"ad": "notlar.md", "yol": os.path.join(BL, "notlar.md"), "toplanti": N + ".md"}, {"ad": "plan.docx", "yol": os.path.join(BL, "plan.docx"), "toplanti": N + ".md"},
                {"ad": "gizli.md", "yol": os.path.join(BL, "gizli.md"), "toplanti": G + ".md"}, {"ad": "deneme.md", "yol": os.path.join(BL, "deneme.md"), "toplanti": DN + ".md"},
                {"ad": "okunmaz.pdf", "yol": os.path.join(BL, "okunmaz.pdf"), "toplanti": N + ".md"}]
    v = yapi.belge_onerileri(C, KART, BELGELER, ONB); o = {x["metin"]: x for x in v["oneriler"]}
    bak("öneriler: kart + belge + önbellek; kayıttaki (noktalısı da) yok; gizli ve deneme belgesi yok; aynı madde tek",
        set(o) == {"Pilot sonuçlarını derle", "Sözleşme taslağını gözden geçir", "Bütçe tablosunu güncelle", "Tedarikçiye dönüş yap", "Lisans yenilemesini kontrol et", "Ölçüm raporunu yaz",
                   "Kurulum rehberini çevir"} and v["say"]["kayitta"] == 1, sorted(o))
    bak("kaynak adı ve satırı öneride; gerekçe yazılı", o["Pilot sonuçlarını derle"]["kaynak"] == {"tur": "proje_karti", "ad": "rapor.pdf", "konum": "s. 4"}
        and o["Bütçe tablosunu güncelle"]["kaynak"] == {"tur": "belge", "ad": "notlar.md", "konum": "satır 7"} and o["Kurulum rehberini çevir"]["kaynak"]["konum"] == "s. 2, satır 2"
        and "belgede" in o["Tedarikçiye dönüş yap"]["neden"] and o["Sözleşme taslağını gözden geçir"]["kaynak"]["tur"] == "proje_karti")
    vd = yapi.belge_onerileri(C, None, BELGELER, ONB, deneme=True)
    bak("deneme=True: deneme belgesinin maddesi gelir, gizli yine yok", "Deneme toplantısı maddesi" in {x["metin"] for x in vd["oneriler"]} and "Gizli toplantı maddesi" not in {x["metin"] for x in vd["oneriler"]})
    # kabul: kayit_olustu + is_atandi; sahipsiz yalnız kayit_olustu
    KD = {}; yapi.ortak_secilen(C, KD, "ece" + AT + "firma.test", "Ece Deneme")  # paylaşım başlangıcı: bundan sonraki olaylar gider
    n0 = len(yapi.olaylar(C))
    r = yapi.belge_oneri_kabul(C, o["Pilot sonuçlarını derle"], eposta="selin.ari" + AT + "firma.test")
    x = yapi.ortak_kayit(C, r["kayit_id"]); th = [e["tur"] for e in yapi.olaylar(C, r["kayit_id"])]
    bak("kabul: kayit_olustu + is_atandi, sahip adı ve e-postası rolde, isteyen kullanıcı, vade ve kaynak alıntıda", r["ok"] and th == ["kayit_olustu", "is_atandi"] and x["roller"]["sahip"] == {"ad": "Selin Arı", "eposta": "selin.ari" + AT + "firma.test"}
        and x["roller"]["isteyen"].get("ben") and x["vade"] == "2026-11-25" and x["tur"] == "is", (r, x))
    r2 = yapi.belge_oneri_kabul(C, o["Sözleşme taslağını gözden geçir"])
    bak("sahipsiz öneri: yalnız kayit_olustu, sahipsiz işareti", r2["ok"] and r2["sahipsiz"] and [e["tur"] for e in yapi.olaylar(C, r2["kayit_id"])] == ["kayit_olustu"])
    bak("aynı öneri ikinci kez kayda girmez", not yapi.belge_oneri_kabul(C, o["Pilot sonuçlarını derle"])["ok"] and len(yapi.olaylar(C)) == n0 + 3)
    bak("reddet: geçersiz kimlik reddedilir", not yapi.belge_oneri_reddet(C, "x1"))
    yapi.belge_oneri_reddet(C, o["Tedarikçiye dönüş yap"]["id"])
    v2 = yapi.belge_onerileri(C, KART, BELGELER, ONB); m2 = {x["metin"] for x in v2["oneriler"]}
    bak("sonra: kabul edilen ve reddedilen bir daha önerilmez", not {"Pilot sonuçlarını derle", "Sözleşme taslağını gözden geçir", "Tedarikçiye dönüş yap"} & m2 and v2["say"]["red"] == 1 and "Bütçe tablosunu güncelle" in m2)
    bak("kabul edilen iş Kararlar ve işler listesinde", "Pilot sonuçlarını derle" in {k["metin"] for k in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"]})
    # gizli toplantı belgesinden elle kabul de yok; deneme toplantısının belgesinden kabul ortak klasöre gitmez
    bak("gizli toplantıya bağlı öneri kabul edilmez", yapi.belge_oneri_kabul(C, {"metin": "Gizli toplantı maddesi", "toplanti": G + ".md"}).get("err") == "gizli")
    rd = yapi.belge_oneri_kabul(C, next(x for x in vd["oneriler"] if x["metin"] == "Deneme toplantısı maddesi"), eposta="doruk" + AT + "firma.test")
    od = yapi.ortak_secilen(C, KD, "ece" + AT + "firma.test", "Ece Deneme")
    giden = [x["kayit_id"] for x in od["satirlar"]]
    bak("ortak paylaşım: proje kartı işinin olayları gider, deneme toplantısı belgesinden kabul edilen gitmez", rd["ok"] and r["kayit_id"] in giden and rd["kayit_id"] not in giden and od["atlanan"].get("deneme", 0) >= 2, od)
    # kayıt veritabanının açık işleri (ayar veritabani.gorevler satırları: iş, sahip, vade, konum)
    VR = [["Envanter tablosunu kurumsala taşı · 29 Ekim: ek not · 30 Ekim: başka not", "Doruk Ersoy (ana sahip), Selin Arı", "", "iş kaydı #7"],
          ["A1 · Erişim listesini doğrula", "Selin Hanım", "2026-11-20", "iş kaydı #8"], ["Kısa", "Doruk", "", "#9"],
          ["Pilot sonuçlarını derle", "Selin Arı", "", "#10"], ["Uzun cümle sahipli iş kaydı", "bu iş kurucu kararından sonra netleşecek", "", "#11"]]
    vv = {x["metin"]: x for x in yapi.belge_onerileri(C, None, [], None, vt_isler=VR)["oneriler"]}
    bak("veritabanı: ' · ' sonrası tarihli notlar düşer (ilk parça kısaysa iki parça), çok kısa yok, kayıttaki (ve reddedilen) yok",
        set(vv) == {"Envanter tablosunu kurumsala taşı", "A1 · Erişim listesini doğrula", "Uzun cümle sahipli iş kaydı"}, sorted(vv))
    bak("veritabanı sahibi: parantez ve ikinci kişi atılır, unvan düşer, cümle sahip sayılmaz; vade ISO; kaynak satırı",
        vv["Envanter tablosunu kurumsala taşı"]["sahip"] == "Doruk Ersoy" and vv["A1 · Erişim listesini doğrula"]["sahip"] == "Selin" and vv["A1 · Erişim listesini doğrula"]["vade"] == "2026-11-20"
        and vv["Uzun cümle sahipli iş kaydı"]["sahip"] == "" and vv["Envanter tablosunu kurumsala taşı"]["kaynak"] == {"tur": "veritabani", "ad": "kayıt veritabanı", "konum": "iş kaydı #7"}, vv)
    bak("veritabanı satırı verilmezse kartın veritabani.acik_isler satırları", [x["metin"] for x in yapi.belge_onerileri(C, {"veritabani": {"acik_isler": [VR[0]]}}, [], None)["oneriler"]] == ["Envanter tablosunu kurumsala taşı"])
    # aktarıcı: GET/POST /belge-oneri — baglam.json'daki belge, proje kartı uygulama klasöründe; e-posta kimlik modülünden (takvim katılımcısı)
    PORT = bos_port(8799); U = f"http://127.0.0.1:{PORT}"; UY = os.path.join(T, "uyg"); os.makedirs(UY)
    shutil.copytree(ONB, os.path.join(UY, "cevirme-onbellek"))
    json.dump({"acik_isler": [{"is": "Eğitim takvimini çıkar", "sahip": ["Doruk Ersoy"], "kaynaklar": [["/x/egitim.docx", "s. 1"]]}]}, open(os.path.join(UY, "proje-karti.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"son": 2, "kaynaklar": [{"id": "b1", "at": datetime.datetime.now().isoformat(timespec="seconds"), "tur": "dosya", "deger": os.path.join(BL, "plan.docx"), "ad": "plan.docx", "kaynak": "birak", "file": N + ".md"},
                                       {"id": "b2", "at": datetime.datetime.now().isoformat(timespec="seconds"), "tur": "baglanti", "deger": "https://ornek.test/x", "ad": "x", "kaynak": "kutu", "file": N + ".md"}]},
              open(os.path.join(C, "baglam.json"), "w", encoding="utf-8"))
    g0 = datetime.date.today().isoformat()
    json.dump({"durum": "ok", "olaylar": [{"id": "ev1", "baslik": "Proje", "baslangic": f"{g0}T23:40:00+03:00", "bitis": f"{g0}T23:55:00+03:00", "katilimcilar": ["Doruk Ersoy"],
                                           "kisiler": [{"ad": "Doruk Ersoy", "eposta": "doruk.ersoy" + AT + "firma.test"}], "katilimci_eposta": ["doruk.ersoy" + AT + "firma.test"], "tum_gun": False}]},
              open(os.path.join(T, "takvim.json"), "w", encoding="utf-8"), ensure_ascii=False)  # aktarıcı takvimi canlı klasörünün yanında
    import sqlite3; VDB = os.path.join(T, "kayit.db"); vc = sqlite3.connect(VDB)
    vc.execute("CREATE TABLE is_kaydi (id INTEGER PRIMARY KEY, tur TEXT, baslik TEXT, sahip TEXT, ne_zaman TEXT, acik INTEGER, oncelik TEXT, sira INTEGER)")
    vc.executemany("INSERT INTO is_kaydi (tur, baslik, sahip, ne_zaman, acik) VALUES (?,?,?,?,?)", [("is", "Yedekleme planını yaz", "Doruk Ersoy", "", 1), ("is", "Kapanmış veritabanı işi", "Doruk Ersoy", "", 0), ("adim", "Sıradaki adım iş değil", "", "", 1)]); vc.commit(); vc.close()
    GQ = "SELECT baslik, sahip, ne_zaman, 'iş kaydı #' || id FROM is_kaydi WHERE acik = 1 AND tur = 'is' ORDER BY oncelik IS NULL, coalesce(sira, 999999), id"
    json.dump({"alan": "Deneme", "ad": "Ece Deneme", "uygulama": UY, "veritabani": {"yol": VDB, "gorevler": GQ}, "proje": T, "ortak": "/Users/Shared/Suflor", "port": PORT, "gelistirici": True, "konusma": False, "yerel_ses": False}, open(AY, "w"))
    rl = subprocess.Popen([sys.executable, "relay.py", "--dir", C, "--port", str(PORT)], cwd=KOD, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_AYAR=AY),
                          stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(40):
        if os.path.exists(os.path.join(C, "kart-anahtari.txt")): break
        time.sleep(0.25)
    time.sleep(1.5); key = open(os.path.join(C, "kart-anahtari.txt")).read().strip()
    def al(yol, anahtar=True, govde=None):
        q = urllib.request.Request(U + yol, data=json.dumps(govde).encode() if govde is not None else None, headers={"X-Suflor-Anahtar": key} if anahtar else {})
        try: return json.load(urllib.request.urlopen(q, timeout=20))
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    bak("/belge-oneri anahtarsız 401", al("/belge-oneri", False).get("_kod") == 401)
    a = al("/belge-oneri"); ao = {x["metin"]: x for x in a.get("oneriler") or []}
    bak("/belge-oneri: kayıt veritabanının açık işi (kapanmış ve adım yok) + proje kartı + bağlamdaki belge (önbellekten), bağlantı okunmaz", a.get("ok") and set(ao) == {"Eğitim takvimini çıkar", "Kurulum rehberini çevir", "Yedekleme planını yaz"}, a)
    k = al("/belge-oneri", govde={"id": ao["Eğitim takvimini çıkar"]["id"], "islem": "kabul"})
    x = yapi.ortak_kayit(C, k.get("kayit_id") or "-") or {}
    bak("POST kabul: kayit_olustu + is_atandi, sahibin e-postası takvimden", k.get("ok") and k["olaylar"] == ["kayit_olustu", "is_atandi"] and (x.get("roller") or {}).get("sahip", {}).get("eposta") == "doruk.ersoy" + AT + "firma.test", (k, x.get("roller")))
    rr = al("/belge-oneri", govde={"id": ao["Kurulum rehberini çevir"]["id"], "islem": "reddet"}); a2 = al("/belge-oneri")
    bak("veritabanı dosyası değişmedi (yalnız okuma)", sqlite3.connect(VDB).execute("SELECT count(*) FROM is_kaydi").fetchone()[0] == 3)
    bak("POST reddet → listeden düşer; bilinmeyen öneri kabul edilmez", rr.get("ok") and [x["metin"] for x in a2.get("oneriler") or []] == ["Yedekleme planını yaz"] and not al("/belge-oneri", govde={"id": "o" + "0" * 15, "islem": "kabul"}).get("ok"))
finally:
    if rl: rl.terminate()
    shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
