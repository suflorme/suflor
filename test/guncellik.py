#!/usr/bin/env python3
# Güncellik ve ilgi katmanı (yapi.guncellik, davet_gundemi, guncellik_blogu, guncellik_karne; gundem_taslagi davet kipi): yapay toplantı — gündemli davet, kapanmış iş, cevaplanmış e-posta,
# başka toplantının ilgisiz maddesi, vadesi çok geçmiş dokunulmamış iş (bayat), sonra yeniden kaydedilmiş iş (yerini aldı), gündemde olmayan kritik konu (ek öneri), yakın geçmiş karar.
# Beklenen: davet gündemi omurga; bitmiş/bayat/ilgisiz açık diye çıkmaz; her aday için karne satırı (metin yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/guncellik.py      (kaldı → çıkış 1)
import datetime, json, os, shutil, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
AT = "@"
hata = []
def bak(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""))
    if not k: hata.append(ad)
# 1. davet gündemi ayrıştırma
NOT = ("12 Kasım 2026 · 07.00–08.00 PST / 18.00–19.00 TSİ\r\n\r\nGündem\r\n\r\n18.00 · 5 dk\r\nAçılış\r\n18.05 · 10 dk\r\nMevcut organizasyon yapısı\r\n18.15 · 15 dk\r\n"
       "Hedeflenen organizasyon yapısı\r\n18.30 · 20 dk\r\nOrganizasyon yapısına ilişkin tartışma ve kararlar\r\n18.50 · 10 dk\r\nTeknik konular\r\n\r\n  *   Workspace acil durum hesabının açılması\r\n"
       "  *   Kullanılmayan hesapların askıya alınması / kapatılması\r\n\r\nÖn okuma (isteğe bağlı)\r\n• PDF<https://ornek.test/x>\r\n\r\n________________\r\nMicrosoft Teams toplantısı\r\nKatıl: https://ornek.test")
g = yapi.davet_gundemi(NOT)
bak("davet gündemi: saat satırı + başlık satırı, süre, alt maddeler; tarih satırı, ön okuma ve katılım bloğu girmez",
    [(x["no"], x["saat"], x["dk"], x["baslik"]) for x in g] == [(1, "18.00", 5, "Açılış"), (2, "18.05", 10, "Mevcut organizasyon yapısı"), (3, "18.15", 15, "Hedeflenen organizasyon yapısı"),
                                                                (4, "18.30", 20, "Organizasyon yapısına ilişkin tartışma ve kararlar"), (5, "18.50", 10, "Teknik konular")]
    and g[4]["alt"] == ["Workspace acil durum hesabının açılması", "Kullanılmayan hesapların askıya alınması / kapatılması"], g)
bak("davet gündemi: numaralı/işaretli liste ve '(10 dk)' süre eki", [(x["baslik"], x["dk"]) for x in yapi.davet_gundemi("Gündem:\n1. Bütçe durumu (10 dk)\n2. Tedarikçi seçimi\n- alt madde")] ==
    [("Bütçe durumu", 10), ("Tedarikçi seçimi", None), ("alt madde", None)] or [(x["baslik"], x["dk"]) for x in yapi.davet_gundemi("Gündem:\n1. Bütçe durumu (10 dk)\n2. Tedarikçi seçimi")] == [("Bütçe durumu", 10), ("Tedarikçi seçimi", None)])
bak("davet gündemi: başlıksız iki işaretli madde gündemdir; tek madde ya da düz metin değildir", len(yapi.davet_gundemi("- Bütçe\n- Plan")) == 2 and yapi.davet_gundemi("- Bütçe için karar") == []
    and yapi.davet_gundemi("Merhaba, haftalık görüşmemiz.\nGörüşmek üzere") == [] and yapi.davet_gundemi("") == [] and yapi.davet_gundemi(None) == [])
bak("kök: ünsüz yumuşaması (hesabı/hesap), kısaltma (org), genel sözcük atılır", yapi._gn_kokler("hesabı") == yapi._gn_kokler("hesap") and "organ" in yapi._gn_kokler("org şeması")
    and not yapi._gn_kokler("toplantı gündemi açılış"))
# 2. yapay graf
T = tempfile.mkdtemp(prefix="suflor-gunc-"); C = os.path.join(T, "canli"); os.makedirs(C); bugun = datetime.date(2026, 11, 12)
try:
    BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    D_ORG, D_TEK, D_ESK = "2026-11-05-1800-Organizasyonel-Donusum-Rol-Inceleme", "2026-11-04-2155-Teknik-Board", "2026-09-20-1000-Organizasyonel-Donusum-Baslangic"
    for d in (D_ORG, D_TEK, D_ESK): open(os.path.join(C, d + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {d}\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n")
    def y(top, baslik, tarih, ogeler): yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    y(D_ESK, "Organizasyonel Dönüşüm — Başlangıç", "2026-09-20", [
        {"tur": "is", "metin": "Eski organizasyon şeması envanterini çıkarmak", "sahip": "Ayşe Deneme", "tarih": "2026-09-25"},          # vadesi 48 gün geçmiş, dokunulmamış → bayat
        {"tur": "is", "metin": "Workspace acil durum hesabı için kasa seçmek", "sahip": "Ali Örnek"}])                                  # sonra yeniden kaydedildi → yerini aldı
    y(D_TEK, "Teknik Board", "2026-11-04", [
        {"tur": "is", "metin": "Tedarikçi fiyat eşleme listesini hazırlatmak", "sahip": "Ali Örnek"},                                   # katılımcının ama konu dışı
        {"tur": "is", "metin": "Kamera analizi için maliyet hesabı", "sahip": "Ece Üçüncü"},                                             # üçüncü kişi, konu dışı ("hesap" tek kök)
        {"tur": "karar", "metin": "Dealer alan adları arama listesinden çıkarılacak", "kim": "Ali Örnek", "netlik": "ortuk"}])           # onay süresi doldu → bayat, konu dışı
    y(D_ORG, "Organizasyonel Dönüşüm — Rol İnceleme", "2026-11-05", [
        {"tur": "karar", "metin": "Rol bazlı org şeması yönünde ilerlenecek; taslaklar sonraki toplantıda karara bağlanacak", "kim": "Ayşe Deneme", "netlik": "acik"},  # kapanmış karar → geçmiş
        {"tur": "is", "metin": "Hedef organizasyon yapısı taslağını kuruculara göndermek", "sahip": "Ayşe Deneme", "tarih": "2026-11-08"},   # yapıldı → bitti (geçmiş, G3)
        {"tur": "is", "metin": "Workspace acil durum hesabı için kasa seçmek ve zarfı Ali'ye vermek", "sahip": "Ali Örnek", "tarih": "2026-11-14"},  # açık → G5
        {"tur": "is", "metin": "Hedeflenen organizasyon yapısında rol listesini tamamlamak", "sahip": "Ozan Katılımcı", "tarih": "2026-11-10"},  # açık, gecikmiş → G3
        {"tur": "karar", "metin": "Kullanılmayan hesaplar askıya alınacak, kapatma kararı organizasyon yapısı netleşince", "kim": "Ali Örnek", "netlik": "ortuk"},  # onay bekliyor → G5
        {"tur": "is", "metin": "Organizasyon yapısı geçişinde bordro ve yetki devri takvimini çıkarmak", "sahip": "Ayşe Deneme", "tarih": "2026-11-11"}])  # gecikmiş, kritik; gündem maddesi var (G3/G4)
    v0 = yapi.kayit_listesi(C, "Ayşe Deneme", bugun); dd = {x["metin"]: x for x in v0["kayitlar"]}
    yapi.soz_kapat(C, dd["Hedef organizasyon yapısı taslağını kuruculara göndermek"]["id"], "yapildi")
    v0 = yapi.kayit_listesi(C, "Ayşe Deneme", bugun); dd = {x["metin"]: x for x in v0["kayitlar"]}; iid = lambda m: dd[m]["id"]
    OLAY = {"id": "ev-org", "baslik": "Organizasyonel Dönüşüm — Organizasyon Yapısı", "notlar": NOT, "katilimcilar": ["Ali Örnek", "Ozan Katılımcı"],
            "katilimci_eposta": ["ali" + AT + "sirket.onmicrosoft.test", "ozan" + AT + "sirket.onmicrosoft.test"]}
    EP = [{"id": "m1", "konu": "Workspace acil durum hesabı kurulumu", "durum": "cozuldu", "t": "2026-11-10"},               # cevaplanmış/çözülmüş → bitti
          {"id": "m2", "konu": "Kullanılmayan hesapların askıya alınması onayı", "durum": "senden_bekleniyor", "t": "2026-11-11"},  # açık → G5
          {"id": "m3", "konu": "Haftalık bülten", "durum": "bilgi", "t": "2026-11-11"}]
    v = yapi.guncellik_olay(C, OLAY, "Ayşe Deneme", bugun=bugun, epostalar=EP)
    kr = {k["id"]: k for k in v["kararlar"]}
    bagli = {g_["no"]: [x["id"] for x in g_["adaylar"]] for g_ in v["gundem"]}
    tum_acik = [x["id"] for g_ in v["gundem"] for x in g_["adaylar"]] + [x["id"] for x in v["ek_oneri"]]
    bak("omurga: davet kipi, beş madde sırasıyla; Suflor yeni gündem maddesi eklemez", v["davet"] and [g_["baslik"] for g_ in v["gundem"]] == [x["baslik"] for x in g])
    bak("G5 (teknik): açık acil durum hesabı işi + onay bekleyen askıya alma kararı + açık e-posta bağlanır", iid("Workspace acil durum hesabı için kasa seçmek ve zarfı Ali'ye vermek") in bagli[5]
        and iid("Kullanılmayan hesaplar askıya alınacak, kapatma kararı organizasyon yapısı netleşince") in bagli[5] + bagli[3] + bagli[4] and "em2" in bagli[5], bagli)
    bak("G3 (hedef yapı): gecikmiş rol listesi işi bağlanır", iid("Hedeflenen organizasyon yapısında rol listesini tamamlamak") in bagli[3], bagli)
    bak("kapanmış iş açık diye çıkmaz (bitti), yakın geçmiş olarak gider", kr[iid("Hedef organizasyon yapısı taslağını kuruculara göndermek")]["durum"] == "bitti"
        and iid("Hedef organizasyon yapısı taslağını kuruculara göndermek") not in tum_acik and iid("Hedef organizasyon yapısı taslağını kuruculara göndermek") in [x["id"] for x in v["gecmis"]])
    bak("onaylı karar (kapandı) yalnız geçmiş", kr[iid("Rol bazlı org şeması yönünde ilerlenecek; taslaklar sonraki toplantıda karara bağlanacak")]["karar"] == "gecmis")
    bak("cevaplanmış e-posta (çözüldü) bitti; açık listelerde yok; bilgi e-postası da yok", kr.get("em1", {}).get("durum") == "bitti" and "em1" not in tum_acik and "em3" not in tum_acik, kr.get("em1"))
    bak("başka toplantının ilgisiz maddeleri (katılımcının da üçüncü kişinin de) ele", all(kr.get(iid(m), {"karar": "ele"})["karar"] == "ele" for m in
        ("Tedarikçi fiyat eşleme listesini hazırlatmak", "Kamera analizi için maliyet hesabı")) and not any(iid(m) in tum_acik + [x["id"] for x in v["belirsiz"]] for m in ("Tedarikçi fiyat eşleme listesini hazırlatmak", "Kamera analizi için maliyet hesabı")))
    bak("vadesi çok geçmiş dokunulmamış iş bayat; açık diye bağlanmaz", kr[iid("Eski organizasyon şeması envanterini çıkarmak")]["durum"] == "bayat" and iid("Eski organizasyon şeması envanterini çıkarmak") not in tum_acik,
        kr[iid("Eski organizasyon şeması envanterini çıkarmak")])
    bak("onay süresi dolmuş karar bayat", kr[iid("Dealer alan adları arama listesinden çıkarılacak")]["durum"] == "bayat")
    bak("sonra yeniden kaydedilen iş: eskisinin yerini yenisi aldı", kr[iid("Workspace acil durum hesabı için kasa seçmek")]["durum"] == "yerini_aldi" and iid("Workspace acil durum hesabı için kasa seçmek") not in tum_acik)
    bak("ayıklanan sayıları dolu (bitti, bayat, yerini aldı, konu dışı)", all(v["ayiklanan"][k] >= 1 for k in ("bitti", "bayat", "yerini_aldi", "konu_disi")), v["ayiklanan"])
    blk = yapi.guncellik_blogu(v)
    bak("istem bloğu: omurga, durum etiketi, son değişiklik ve kaynak; bitmiş/ilgisiz metin açık listede yok", "G5. Teknik konular (18.50, 10 dk)" in blk and "[açık;" in blk and "son değişiklik" in blk
        and "kayıt: Organizasyonel Dönüşüm — Rol İnceleme" in blk and "Tedarikçi fiyat" not in blk and "Kamera analizi" not in blk and "Haftalık bülten" not in blk and "bunları açık diye önerme" in blk, blk)
    bak("istem bloğu İngilizce", "Invitation agenda" in yapi.guncellik_blogu(v, "en") and "do not bring these up as open" in yapi.guncellik_blogu(v, "en"))
    ks = [json.loads(l) for l in yapi.guncellik_karne(v, "hazirlik", "ev-org", at="2026-11-12T10:00:00+03:00")]
    bak("karne: her bağlı aday için satır + özet satırı; metin yok, olay kimliği özetli", len(ks) == len(v["kararlar"]) + 1 and all("metin" not in k and k["olay"] != "ev-org" and len(k["olay"]) == 12 for k in ks)
        and ks[-1]["ozet"] == v["ayiklanan"] and {k.get("karar") for k in ks[:-1]} >= {"gundeme_bagla", "ele", "gecmis"})
    gt = yapi.gundem_taslagi(C, OLAY["katilimcilar"], "Ayşe Deneme", OLAY["baslik"], bugun, notlar=NOT, epostalar=EP)
    bak("gündem taslağı (davet kipi): maddeler = davetin maddeleri, satır 'N · başlık (saat, dk)', bağlı kayıt sayısı alt satırda", gt["davet"] and [m["satir"] for m in gt["maddeler"]][1] == "2 · Mevcut organizasyon yapısı (18.05, 10 dk)"
        and gt["maddeler"][4]["baslik"].startswith(f"{len(bagli[5])} açık kayıt bağlı") and "Tedarikçi" not in gt["metin"], gt["maddeler"][4])
    gs = yapi.gundem_taslagi(C, OLAY["katilimcilar"], "Ayşe Deneme", "Haftalık", bugun)
    bak("gündem taslağı (gündemsiz): katılımcının açık işi gelir, üçüncü kişinin işi ve bayat/bitmiş gelmez", not gs["davet"] and iid("Workspace acil durum hesabı için kasa seçmek ve zarfı Ali'ye vermek") in [m["id"] for m in gs["maddeler"]]
        and iid("Kamera analizi için maliyet hesabı") not in [m["id"] for m in gs["maddeler"]] and iid("Eski organizasyon şeması envanterini çıkarmak") not in [m["id"] for m in gs["maddeler"]], [m["metin"] for m in gs["maddeler"]])
    # elle gündeme eklenen kayıt her zaman girer (maddeye uymuyorsa ek öneri)
    k_ = iid("Tedarikçi fiyat eşleme listesini hazırlatmak"); yapi.gundeme_ekle(C, dd["Tedarikçi fiyat eşleme listesini hazırlatmak"]["kayit_id"], "ev-org")
    v2 = yapi.guncellik_olay(C, OLAY, "Ayşe Deneme", bugun=bugun)
    bak("elle 'Gündeme ekle' denen konu dışı kayıt ek öneri olarak gelir", k_ in [x["id"] for x in v2["ek_oneri"]], [x["id"] for x in v2["ek_oneri"]])
finally: shutil.rmtree(T, ignore_errors=True)
print(f"\nKALDI: {hata}" if hata else "\nhepsi geçti"); sys.exit(1 if hata else 0)
