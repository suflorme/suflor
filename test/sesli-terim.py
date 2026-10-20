#!/usr/bin/env python3
# Sesli kısımda iç terim süzgeci ve "son toplantı" bağlamı (v0.57.1; aktarici/bas-konus.py sesli_terim_suz, GECMIS_TOP_RX, son_toplanti_metni).
# Aktarıcının kendi tanımları AST ile alınır (kopya kural yok). Gerçek deneme örnekleri: "karar kaydı bulamadım" (16 Ekim) süzülür; "rol dökümleri" (dışa aktarılan
# liste) değişmez. Süzgeç ya da son toplantı kalıbı değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-terim.py      (kaldı → çıkış 1)
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ns = {"re": re, "print": lambda *a, **k: None, "_t": lambda tr, en: tr,
      "SON": [{"at": "2026-10-09T18:30:00", "baslik": "Depo erişim envanteri", "dosya": "2026-10-09-1801-Depo.md", "cikti": {"karar": 1}, "kopya": "/x/ozetler/depo.md"},
              {"at": "2026-10-13T20:57:51", "baslik": "Suflor.me deneme 9", "dosya": "2026-10-13-2009-Suflorme-deneme-9.md", "cikti": {"karar": 0}, "kopya": "/x/ozetler/d9.md"}]}
agac = ast.parse(open(os.path.join(KOD, "aktarici/bas-konus.py"), encoding="utf-8").read())
AD = {"sesli_terim_suz", "son_toplanti_metni"}; DEG = {"SESLI_KAYNAK_RX", "SESLI_TERIM", "GECMIS_TOP_RX", "_DENEME_AD"}
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in AD) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in DEG for x in n.targets))]
exec(compile(ast.Module(sec, []), "bas-konus.py", "exec"), ns)
TABLO = [
    ("Son toplantıya bağlı bir karar kaydı bulamadım.", "Son toplantıya bağlı bir karar bulamadım.", "16 Ekim gerçek cevap"),
    ("Kayıtlara göre 22 kişinin hesabında kapalı.", "22 kişinin hesabında kapalı.", "kaynak atfı düşer, büyük harf"),
    ("Karar defterine göre iki karar var.", "İki karar var.", "İ büyük harfi"),
    ("Karar kayıtlarında bu yok.", "Kararlarda bu yok.", "çoğul + bulunma"),
    ("Ali kullanıcı ve rol dökümlerini gönderdi.", "Ali kullanıcı ve rol dökümlerini gönderdi.", "dışa aktarılan liste: değişmez"),
    ("Teslim tarihi cuma.", "Teslim tarihi cuma.", "terimsiz cümle değişmez"),
    ("Rakamlar dökümde kısmen bozuk çıkmış, bu yüzden yaklaşık.", "Rakamlar net duyulmamış, bu yüzden yaklaşık.", "v0.95.1: belirsizlik iç terimsiz"),
    ("Dökümde bozuk yazılmış yerler var.", "Net duyulmamış yerler var.", "v0.95.1: cümle başı büyük harf"),
    ("Dökümde Filipinli çalışanlar için net bir liste yok.", "Görüşmede Filipinli çalışanlar için net bir liste yok.", "v0.95.1: dökümde → görüşmede"),
    ("Sözlerini dökümden kontrol ettim.", "Sözlerini görüşmeden kontrol ettim.", "v0.95.1: dökümden → görüşmeden"),
    ("Ali rol dökümünü gönderdi.", "Ali rol dökümünü gönderdi.", "v0.95.1: dışa aktarılan liste değişmez"),
]
hata = 0
for g, b, ad in TABLO:
    o = ns["sesli_terim_suz"](g)
    if o != b: hata += 1; print(f"✗ {ad}: {g!r} → {o!r} (beklenen {b!r})")
SORU = [("Son toplantıda hangi kararlar alındı?", True), ("Son toplantıda alınan kararlar neydi?", True), ("Geçen toplantıda ne konuştuk?", True),
        ("Önceki görüşmenin özeti ne?", True), ("Kaç kişinin iki adımlı doğrulaması kapalı?", False), ("Bugün takvimimde ne var?", False), ("Toplantıda neler konuşuldu?", True)]
for s, b in SORU:
    if bool(ns["GECMIS_TOP_RX"].search(s)) != b:
        hata += 1; print(f"✗ son toplantı kalıbı: {s!r} → {not b}")
m = ns["son_toplanti_metni"]()
if not (m.index("deneme 9") < m.index("Depo") and "· deneme ·" in m and "· gerçek ·" in m and "özet: /x/ozetler/depo.md" in m): hata += 1; print("✗ son toplantılar bloğu:", m)
print("sesli terim:", "✓ hepsi geçti" if not hata else f"✗ {hata} sorun"); sys.exit(1 if hata else 0)
