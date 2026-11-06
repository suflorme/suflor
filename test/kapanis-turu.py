#!/usr/bin/env python3
# Kapanış turu (6 Kasım, S211/S227): toplantı başında bu toplantının dizisinden ve katılımcılarından açık işler (vadesi geçen önce) ve teyit bekleyen kararlar.
# yapi.kapanis_turu (seçim: dizi/başlık ya da katılımcı; kendi toplantısı, gizli, kapanmış, deneme ayrımı; sıra; sayılar), yapi.kapanis_blogu (asistana blok, TR/EN),
# aktarıcıda GET /kapanis-turu (anahtarlı; takvim-secilen.json'dan başlık + katılımcı), panodaki düğmelerin kullandığı /is-durum, /karar-onay, /kayit-eylem ertele sonrası
# kaydın listeden düşmesi ve olay yazılması, tc kapanis.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kapanis-turu.py      (kaldı → çıkış 1)
AT = "@"  # e-posta biçimi kaynakta geçmesin (açık depo taraması)
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)
import yapi; from bosport import bos_port
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-kapanis-"); C = os.path.join(T, "canli"); os.makedirs(C); bugun = datetime.date(2026, 11, 6); rl = None
BEN = "Ayşe Deneme"
try:
    bak("graf yokken boş", yapi.kapanis_turu(C, ["Can Örnek"], BEN, "Haftalık Plan", bugun)["isler"] == [])
    BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    H1, H2, B, G, DN, BU = ("2026-10-27-1000-Haftalik-Plan", "2026-11-03-1000-Haftalik-Plan", "2026-11-02-1400-Butce", "2026-11-04-0900-Ozel", "2026-11-04-1100-Test-2",
                            "2026-11-06-1000-Haftalik-Plan")
    for d, s in ((H1, ""), (H2, ""), (B, ""), (G, "| 09:00:10 | **GİZLİ** | açıldı | |\n"), (DN, ""), (BU, "")):
        open(os.path.join(C, d + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {d}\n\n" + BAS + (s or f"| 10:00:00 | {BEN} | merhaba | |\n"))
    def y(top, baslik, tarih, ogeler): yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    y(H1, "Haftalık Plan", "2026-10-27", [{"tur": "karar", "metin": "Eski dizi kararı", "netlik": "ortuk"},  # dizinin sonraki toplantısı (H2) geçti → onaylanmadı
                                          {"tur": "is", "metin": "Sunumu hazırla", "sahip": "Deniz Yeni", "tarih": "2026-10-31"},  # dizi, katılımcı değil, 6 gün gecikti
                                          {"tur": "is", "metin": "Kapanmış iş", "sahip": "Deniz Yeni", "tarih": "2026-10-30"}])
    y(H2, "Haftalık Plan", "2026-11-03", [{"tur": "karar", "metin": "Takvim kararı", "netlik": "ortuk"},  # 3 gün → eski (hatırlatma)
                                          {"tur": "karar", "metin": "Onaylı karar", "netlik": "acik"},
                                          {"tur": "is", "metin": "Benim dizi işim", "sahip": BEN, "tarih": "2026-11-05"},  # kendi işi dizide: 1 gün gecikti
                                          {"tur": "is", "metin": "Tarihsiz dizi işi", "sahip": "Zeynep Kaya"},
                                          {"tur": "is", "metin": "Vadesi gelecek", "sahip": "Zeynep Kaya", "tarih": "2026-11-12"}])
    y(B, "Bütçe", "2026-11-02", [{"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-04"},  # katılımcının işi başka toplantıdan: 2 gün gecikti
                                 {"tur": "is", "metin": "Başkasının bütçe işi", "sahip": "Zeynep Kaya", "tarih": "2026-11-01"},  # katılımcı değil, dizi değil → yok
                                 {"tur": "is", "metin": "Benim bütçe işim", "sahip": BEN, "tarih": "2026-11-01"},  # kendi işi ama dizi değil → yok
                                 {"tur": "karar", "metin": "Can'ın kararı", "kim": "Can Örnek", "netlik": "ortuk"}])  # söyleyen katılımcı → var
    y(G, "Özel", "2026-11-04", [{"tur": "is", "metin": "Gizli iş", "sahip": "Can Örnek", "tarih": "2026-11-01"}])
    y(DN, "Test-2", "2026-11-04", [{"tur": "is", "metin": "Deneme işi", "sahip": "Can Örnek", "tarih": "2026-11-01"}])
    y(BU, "Haftalık Plan", "2026-11-06", [{"tur": "is", "metin": "Bugünkü toplantının işi", "sahip": "Can Örnek", "tarih": "2026-11-01"}])
    kap = next(x for x in yapi.kayit_listesi(C, BEN, bugun)["kayitlar"] if x["metin"] == "Kapanmış iş"); yapi.soz_kapat(C, kap["id"], "yapildi")
    KAT = ["can.ornek" + AT + "firma.test", "Doruk Uzak"]
    v = yapi.kapanis_turu(C, KAT, BEN, "Haftalık Plan", bugun, toplanti=BU + ".md")
    isler = [k["metin"] for k in v["isler"]]; kar = [k["metin"] for k in v["kararlar"]]
    bak("işler: vadesi geçen önce (en çok geciken başta), sonra vadesi gelecek, sonra tarihsiz", isler == ["Sunumu hazırla", "Tabloyu güncelle", "Benim dizi işim", "Vadesi gelecek", "Tarihsiz dizi işi"])
    bak("dizide olmayan ve sahibi katılımcı olmayan iş yok; kullanıcının dizi dışı işi yok", "Başkasının bütçe işi" not in isler and "Benim bütçe işim" not in isler)
    bak("bu toplantının kendi kaydı, gizli toplantı, deneme toplantısı ve kapanmış iş yok", not {"Bugünkü toplantının işi", "Gizli iş", "Deneme işi", "Kapanmış iş"} & set(isler))
    bak("kararlar: onaylanmadı önce, sonra 3+ gün (eski), sonra yeni; onaylı karar yok", kar == ["Eski dizi kararı", "Takvim kararı", "Can'ın kararı"])
    kd = {k["metin"]: k for k in v["kararlar"]}
    bak("karar alanları: onaylanmadı (dizinin sonraki toplantısı), Takvim kararı 3 gün eski, Can'ın kararı 4 gün eski",
        kd["Eski dizi kararı"]["onay"]["durum"] == "onaylanmadi" and kd["Takvim kararı"]["eski"] and kd["Takvim kararı"]["onay"]["gun"] == 3 and kd["Can'ın kararı"]["eski"])
    bak("sayılar: 5 iş (3 gecikmiş), 3 karar (3 eski); eşleşen kişi Can Örnek", v["say"] == {"is": 5, "gecikti": 3, "karar": 3, "eski": 3} and v["kisiler"] == ["Can Örnek"])
    v2 = yapi.kapanis_turu(C, KAT, BEN, "Haftalık Plan", bugun, toplanti=BU, en_cok=2)
    bak("en_cok kırpar, sayılar toplamı korur; toplanti uzantısız da tanınır", [k["metin"] for k in v2["isler"]] == ["Sunumu hazırla", "Tabloyu güncelle"] and v2["say"]["is"] == 5)
    vk = yapi.kapanis_turu(C, ["Can Örnek"], BEN, "", bugun)
    bak("başlıksız: yalnız katılımcının kayıtları (dizi yok)", [k["metin"] for k in vk["isler"]] == ["Bugünkü toplantının işi", "Tabloyu güncelle"] and [k["metin"] for k in vk["kararlar"]] == ["Can'ın kararı"])
    bak("katılımcı ve başlık yoksa boş", yapi.kapanis_turu(C, [], BEN, "", bugun)["isler"] == [] and yapi.kapanis_turu(C, ["  "], BEN, None, bugun)["kararlar"] == [])
    vd = yapi.kapanis_turu(C, ["Can Örnek"], BEN, "Test-3", bugun, deneme=True)
    bak("deneme toplantısında yalnız deneme kayıtları", [k["metin"] for k in vd["isler"]] == ["Deneme işi"] and vd["kararlar"] == [])
    b = yapi.kapanis_blogu(v)
    bak("blok: sayılar, kimlikli satırlar, kural (kendiliğinden kapatma yok), kapanış etiketi", b.startswith("[Kapanış turu") and "5 açık iş (3'ü vadesi geçmiş)" in b and "3 teyit bekleyen karar (3 tanesi 3+ gündür)" in b
        and "kendiliğinden kapatma" in b and b.endswith("[/Kapanış turu]") and f"- {v['isler'][0]['id']} · Deniz Yeni: Sunumu hazırla — 6 gün gecikti (Haftalık Plan, 2026-10-27)" in b
        and "Zeynep Kaya: Tarihsiz dizi işi — tarihsiz" in b and "Can Örnek: Can'ın kararı — 4 gündür onay bekliyor" in b and "Eski dizi kararı — onaylanmadı (dizinin sonraki toplantısı geçti)" in b)
    be = yapi.kapanis_blogu(v, "en")
    bak("blok İngilizce", be.startswith("[Closing round") and "6 days overdue" in be and "awaiting approval for 4 days" in be and "1 day overdue" in be and be.endswith("[/Closing round]"))
    bak("boş seçimde blok yok", yapi.kapanis_blogu(yapi.kapanis_turu(C, [], BEN, "", bugun)) == "" and yapi.kapanis_blogu(None) == "")
    # aktarıcı: GET /kapanis-turu (takvim-secilen.json'dan başlık + katılımcı), düğmelerin uçları
    PORT = bos_port(8799); U = f"http://127.0.0.1:{PORT}"
    json.dump({"at": "2026-11-06T10:00:00", "konu": "Haftalık Plan", "olay": {"id": "ev1", "baslik": "Haftalık Plan", "katilimcilar": ["Doruk Uzak"],
               "kisiler": [{"ad": "Can Örnek", "eposta": "can.ornek" + AT + "firma.test"}]}}, open(os.path.join(C, "takvim-secilen.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"alan": "Deneme", "ad": BEN, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "port": PORT, "gelistirici": True, "konusma": False, "yerel_ses": False}, open(os.path.join(T, "ayar.json"), "w"))
    rl = subprocess.Popen([sys.executable, "relay.py", "--dir", C, "--port", str(PORT)], cwd=KOD, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")),
                          stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(40):
        if os.path.exists(os.path.join(C, "kart-anahtari.txt")): break
        time.sleep(0.25)
    time.sleep(1); key = open(os.path.join(C, "kart-anahtari.txt")).read().strip()
    def al(yol, anahtar=True, govde=None):
        r = urllib.request.Request(U + yol, data=json.dumps(govde).encode() if govde is not None else None, headers={"X-Suflor-Anahtar": key} if anahtar else {})
        try: return json.load(urllib.request.urlopen(r, timeout=10))
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    bak("/kapanis-turu anahtarsız 401", al("/kapanis-turu", False).get("_kod") == 401)
    k = al("/kapanis-turu"); ki = {x["metin"]: x for x in k.get("isler") or []}; kk = {x["metin"]: x for x in k.get("kararlar") or []}
    # gerçek tarih bugünden: Bugünkü toplantının işi aktif toplantı yokken (deneme aktarıcısı) başka toplantı sayılır → listede; gizli/deneme/kapanmış yine yok
    bak("/kapanis-turu: ok, başlık takvimden, dizi + katılımcı kayıtları, blok dolu", k.get("ok") and k.get("baslik") == "Haftalık Plan" and {"Sunumu hazırla", "Tabloyu güncelle", "Benim dizi işim"} <= set(ki)
        and not {"Gizli iş", "Deneme işi", "Kapanmış iş", "Başkasının bütçe işi"} & set(ki) and "Can'ın kararı" in kk and k.get("blok", "").startswith("[Kapanış turu"))
    r = al("/is-durum", govde={"id": ki["Sunumu hazırla"]["id"], "durum": "yapildi"})
    r2 = al("/karar-onay", govde={"idler": [kk["Can'ın kararı"]["id"]]})
    r3 = al("/kayit-eylem", govde={"id": ki["Tabloyu güncelle"]["id"], "eylem": "ertele", "vade": "2026-12-01", "neden": "kapanış turu"})
    r4 = al("/is-durum", govde={"id": ki["Benim dizi işim"]["id"], "durum": "yapilmadi"})
    k2 = al("/kapanis-turu"); ki2 = {x["metin"]: x for x in k2.get("isler") or []}
    bak("Bitti / Onayla / İptal sonrası kayıt düşer; Ertele vadeyi değiştirir (listede kalır)", r.get("ok") and r2.get("ok") and r3.get("ok") and r4.get("ok") and "Sunumu hazırla" not in ki2 and "Benim dizi işim" not in ki2
        and "Can'ın kararı" not in {x["metin"] for x in k2.get("kararlar") or []} and ki2.get("Tabloyu güncelle", {}).get("vade") == "2026-12-01")
    ol = yapi.olaylar(C); turler = [o["tur"] for o in ol if o.get("kaynak") in ("suflor", "eylem")]
    bak("her düğme bir olay yazdı (durum_degisti ×2, karar_onaylandi, ertelendi)", turler.count("durum_degisti") >= 3 and "karar_onaylandi" in turler and "ertelendi" in turler)
    t = subprocess.run([sys.executable, "-B", "toplanti-claude.py", "--dir", C, "--relay", U, "kapanis"], cwd=KOD, capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")))
    bak("tc kapanis: bloğu basar", t.stdout.startswith("[Kapanış turu") and "Tabloyu güncelle" in t.stdout)
finally:
    if rl: rl.terminate()
    shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
