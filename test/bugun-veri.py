#!/usr/bin/env python3
# Bugün sayfasının veri katmanı (yapi.py bugun_veri / karar_teyit_kaldir / kayit_bul): kendi ve başkalarının açık işleri, gecikme, teyit bekleyen kararlar,
# son toplantının kararları; gizli toplantıdan gelen kayıt hiçbirinde dönmez; teyit eki yalnız kararda kalkar.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bugun-veri.py
import datetime, json, os, shutil, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-bugun-"); bugun = datetime.date(2026, 11, 5)
try:
    bak("graf yokken boş", yapi.bugun_veri(T, "Ayşe Deneme", bugun) == {"ad": "Ayşe Deneme", "kendi": [], "baskalari": [], "teyit": [], "son_karar": None})
    D1, G = "2026-11-05-0930-Butce", "2026-11-04-1500-Ozel"
    BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    open(os.path.join(T, D1 + ".md"), "w", encoding="utf-8").write("# Canlı transkript — Bütçe\n\n" + BAS + "| 09:30:00 | Ayşe Deneme | merhaba | |\n")
    open(os.path.join(T, G + ".md"), "w", encoding="utf-8").write("# Canlı transkript — Özel\n\n" + BAS + "| 15:00:10 | **GİZLİ** | açıldı | |\n")
    def y(top, ogeler): yapi.graf_yaz(T, {"baslik": top, "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    y(G, [{"tur": "karar", "metin": "Gizli karar", "netlik": "ortuk"}, {"tur": "is", "metin": "Gizli iş", "sahip": "Ayşe Deneme", "tarih": "2026-11-01"}])
    y(D1, [{"tur": "karar", "metin": "Bütçe onaylandı", "netlik": "acik"}, {"tur": "karar", "metin": "Tedarikçi Mart'ta", "netlik": "ortuk"},
           {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Ayşe Deneme", "tarih": "2026-11-02"}, {"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe", "tarih": "2026-11-06"},
           {"tur": "is", "metin": "Analiz", "sahip": "Can Örnek", "tarih": "2026-11-03"}, {"tur": "soz", "metin": "Görüş getirecek", "sahip": "Zeynep Kaya", "tarih": "cuma"}])
    v = yapi.bugun_veri(T, "Ayşe Deneme", bugun)
    bak("kendi işler: sahip ilk adıyla eşleşir, gecikme ve kalan gün", [(x["metin"], x["gecikti"], x["kalan_gun"]) for x in v["kendi"]] == [("Tabloyu güncelle", True, -3), ("Sözleşmeyi oku", False, 1)])
    bak("başkalarının işleri: kişi, gecikme; serbest metin vade sona", [(x["kim"], x["gecikti"]) for x in v["baskalari"]] == [("Can Örnek", True), ("Zeynep Kaya", False)] and v["baskalari"][1]["kalan_gun"] is None)
    bak("gizli toplantıdan hiçbir kayıt dönmez", not any("Gizli" in x["metin"] for k in ("kendi", "baskalari", "teyit") for x in v[k]) and "Gizli" not in str(v["son_karar"]))
    bak("teyit bekleyen karar: ek metinden ayrılır, neden verilir", [(x["metin"], bool(x["neden"])) for x in v["teyit"]] == [("Tedarikçi Mart'ta", True)])
    bak("son toplantının kararları (en yeni toplantı, gizli değil)", v["son_karar"] and v["son_karar"]["toplanti"] == D1 + ".md" and [x["metin"] for x in v["son_karar"]["kararlar"]] == ["Bütçe onaylandı", "Tedarikçi Mart'ta"])
    bak("ad boşsa kendi/başkası ayrılamaz", yapi.bugun_veri(T, "", bugun)["kendi"] == [] and yapi.bugun_veri(T, "", bugun)["baskalari"] == [])
    kid = v["teyit"][0]["id"]
    bak("kayit_bul: gizli toplantıdaki kayıt bulunamaz", yapi.kayit_bul(T, "k1", ("karar",)) is None and yapi.kayit_bul(T, kid, ("karar",)))
    bak("karar_teyit_kaldir: eki kaldırır, metin korunur", yapi.karar_teyit_kaldir(T, kid) == "Tedarikçi Mart'ta" and not yapi.bugun_veri(T, "Ayşe", bugun)["teyit"])
    bak("ikinci çağrı (ek yok) ya da gizli karar: None", yapi.karar_teyit_kaldir(T, kid) is None and yapi.karar_teyit_kaldir(T, "k1") is None)
    bak("iş kimliğiyle karar onayı olmaz", yapi.karar_teyit_kaldir(T, "s3") is None)
    s = yapi.soz_kapat(T, v["kendi"][0]["id"], "yapildi")
    bak("soz_kapat sonrası iş açık listeden düşer", s and [x["metin"] for x in yapi.bugun_veri(T, "Ayşe", bugun)["kendi"]] == ["Sözleşmeyi oku"])
    # --- S226: "Senden beklenenler" kuralları (14 gün / yürüten / katıldığı toplantı / 30 gün) ---
    T2 = tempfile.mkdtemp(prefix="suflor-bugun2-")
    try:
        def y2(top, tarih, ogeler): yapi.graf_yaz(T2, {"baslik": top, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
        def dok(top): open(os.path.join(T2, top + ".md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n" + BAS + "| 09:30:00 | Ayşe Deneme | merhaba | |\n")
        def rol(top, r):
            os.makedirs(os.path.join(T2, "gundemler"), exist_ok=True); json.dump({"title": top, "rol": r}, open(os.path.join(T2, "gundemler", top + ".json"), "w", encoding="utf-8"))
        YENI, ESKI, YAB, KAT = "2026-11-03-0900-Yeni", "2026-09-20-0900-Eski", "2026-11-04-1000-Yabanci", "2026-09-30-1000-Katilimci"
        for t in (YENI, ESKI, YAB, KAT): dok(t)
        rol(YENI, "yurutucu"); rol(KAT, "katilimci"); rol(YAB, "dinleyici")
        y2(YENI, "2026-11-03", [{"tur": "karar", "metin": "Yürütülen yeni karar", "netlik": "ortuk"}, {"tur": "is", "metin": "Yeni iş", "sahip": "Ayşe", "tarih": "2026-11-04"},
                                {"tur": "is", "metin": "Yeni başkası", "sahip": "Can Örnek", "tarih": "2026-11-20"}])
        y2(ESKI, "2026-09-20", [{"tur": "karar", "metin": "Eski karar", "netlik": "ortuk"}, {"tur": "is", "metin": "Eski gecikmiş iş", "sahip": "Ayşe", "tarih": "2026-09-25"},
                                {"tur": "is", "metin": "Eski ama vadesi gelecekte", "sahip": "Ayşe", "tarih": "2026-12-01"}, {"tur": "is", "metin": "Eski başkası gecikmiş", "sahip": "Can Örnek", "tarih": "2026-09-30"},
                                {"tur": "is", "metin": "Eski başkası ileri vade", "sahip": "Zeynep Kaya", "tarih": "2026-12-15"}])
        y2(YAB, "2026-11-04", [{"tur": "karar", "metin": "Dinleyici olduğum toplantının kararı", "netlik": "ortuk"}, {"tur": "is", "metin": "Dinleyici toplantısından başkası", "sahip": "Can Örnek", "tarih": "2026-11-06"}])
        y2(KAT, "2026-09-30", [{"tur": "karar", "metin": "Katılımcı olduğum toplantının kararı", "netlik": "ortuk"}, {"tur": "is", "metin": "Katılımcıdan eski başkası", "sahip": "Can Örnek", "tarih": "2026-10-20"}])
        y2("2026-11-02-1200-Dosyasiz", "2026-11-02", [{"tur": "is", "metin": "Katılmadığım toplantı", "sahip": "Can Örnek", "tarih": "2026-11-09"}])  # dökümü/gündemi yok → kullanıcı katılmamış
        w = yapi.bugun_veri(T2, "Ayşe Deneme", bugun)
        bak("S226 teyit: yalnız yürütülen toplantının kararı (katılımcı/dinleyici toplantısı girmez)", sorted(x["metin"] for x in w["teyit"]) == ["Eski karar", "Yürütülen yeni karar"])
        bak("S226 teyit: 14 günden eski karar geride, yeni değil", {x["metin"]: x["geride"] for x in w["teyit"]} == {"Yürütülen yeni karar": False, "Eski karar": True})
        kg = {x["metin"]: x["geride"] for x in w["kendi"]}
        bak("S226 kendi: son 14 gün taze; eski gecikmiş geride; eski ama vadesi gelecekte geride değil", kg == {"Yeni iş": False, "Eski gecikmiş iş": True, "Eski ama vadesi gelecekte": False})
        bak("S226 kendi: geride olanlar listenin sonunda", [x["geride"] for x in w["kendi"]] == sorted(x["geride"] for x in w["kendi"]))
        dg = {x["metin"]: (x.get("durum_g"), x.get("teyit_et"), x["geride"]) for k_ in ("kendi", "baskalari") for x in w[k_]}
        bak("G2 tek durum kapısı: vadesi 14+ gün geçmiş dokunulmamış iş bayat → teyit_et ve geride; taze ve vadesi gelecekteki açık",
            dg["Eski gecikmiş iş"] == ("bayat", True, True) and dg["Yeni iş"] == ("acik", False, False)
            and dg["Eski ama vadesi gelecekte"] == ("acik", False, False), dg)
        _x = next(x for x in w["kendi"] if x["metin"] == "Eski gecikmiş iş")
        bak("G2 satırda durum_neden ve son_degisiklik (kayıt tarihi), dokunma günü", _x["durum_neden"] == ["vade_cok_gecti"] and _x["son_degisiklik"] == "2026-09-20" and _x["dokunma"] == 46, _x)
        _d = yapi.kayit_durumlari(T2, "Ayşe Deneme", bugun)
        bak("G2 kayit_durumlari bugun_veri ile aynı sonucu verir (tek kaynak)", all(_d[x["id"]]["durum"] == x["durum_g"] for k_ in ("kendi", "baskalari", "teyit") for x in w[k_]))
        bm = sorted(x["metin"] for x in w["baskalari"])
        bak("S226 başkaları: son 30 gün ya da vadesi gelecekte (katılımcı/dinleyici toplantıları dahil, katılınmayan değil)",
            bm == sorted(["Yeni başkası", "Eski başkası ileri vade", "Dinleyici toplantısından başkası"]), bm)
        bak("S226 başkaları: 30 günden eski gecikmiş girmez", "Eski başkası gecikmiş" not in bm and "Katılımcıdan eski başkası" not in bm and "Katılmadığım toplantı" not in bm)
        bak("S226 toplanti_rolu: rol kaydı yoksa yürüten, döküm yoksa katılmamış", yapi.toplanti_rolu(T2, YENI + ".md") == (True, True) and yapi.toplanti_rolu(T2, KAT + ".md") == (True, False)
            and yapi.toplanti_rolu(T2, "2026-11-02-1200-Dosyasiz.md") == (False, False))
    finally: shutil.rmtree(T2, ignore_errors=True)
    # --- 9 Kasım: adaş (aynı ilk ad, farklı soyad) başkasının işi "senin işin" görünmez (kendi_mi) ---
    T3 = tempfile.mkdtemp(prefix="suflor-bugun3-")
    try:
        AD = "2026-11-04-1000-Adas"; open(os.path.join(T3, AD + ".md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n")
        yapi.graf_yaz(T3, {"baslik": AD, "tarih": "2026-11-04", "maddeler": [{"baslik": "G", "ogeler": [
            {"tur": "is", "metin": "Benim işim", "sahip": "Ayşe Deneme", "tarih": "2026-11-06"}, {"tur": "is", "metin": "Adaşın işi", "sahip": "Ayşe Kaya", "tarih": "2026-11-06"},
            {"tur": "is", "metin": "Tek adlı iş", "sahip": "Ayşe", "tarih": "2026-11-06"}]}]}, AD + ".md")
        a = yapi.bugun_veri(T3, "Ayşe Deneme", bugun)
        bak("adaş: bugun_veri kendi = yalnız tam ad (adaşın işi başkaları'nda)", sorted(x["metin"] for x in a["kendi"]) == ["Benim işim"] and "Adaşın işi" in [x["metin"] for x in a["baskalari"]], [x["metin"] for x in a["kendi"]])
        kl = yapi.kayit_listesi(T3, "Ayşe Deneme", bugun)
        bak("adaş: kayit_listesi kendi bayrağı adaşa verilmez", {x["metin"]: x["kendi"] for x in kl["kayitlar"] if x["tur"] == "is"} == {"Benim işim": True, "Adaşın işi": False, "Tek adlı iş": False}, {x["metin"]: x["kendi"] for x in kl["kayitlar"] if x["tur"] == "is"})
    finally: shutil.rmtree(T3, ignore_errors=True)
finally: shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
