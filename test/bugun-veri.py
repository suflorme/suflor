#!/usr/bin/env python3
# Bugün sayfasının veri katmanı (yapi.py bugun_veri / karar_teyit_kaldir / kayit_bul): kendi ve başkalarının açık işleri, gecikme, teyit bekleyen kararlar,
# son toplantının kararları; gizli toplantıdan gelen kayıt hiçbirinde dönmez; teyit eki yalnız kararda kalkar.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bugun-veri.py
import datetime, os, shutil, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
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
finally: shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
