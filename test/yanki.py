#!/usr/bin/env python3
# Yankı ayırıcı (aktarici/whisper-hat.py _yanki_mi; v0.25.2): hoparlörden mikrofona giren karşı ses (gerçek yankı) atılır, kullanıcının aynı konudaki
# kendi sözü atılmaz. Gerçek örneklerin (6, 7, 9 Ekim günlüğü) sözcük yapısı, adlar değiştirilerek + uç durumlar. Aktarıcının kendi tanımları
# AST ile alınır (kopya kural yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yanki.py      (kaldı → çıkış 1)
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ns = {"re": re}
for dosya, adlar in (("aktarici/sozluk.py", {"_nc", "sade"}), ("aktarici/whisper-hat.py", {"_yk", "_yanki_mi", "YANKI_KAPSAM"})):
    agac = ast.parse(open(os.path.join(KOD, dosya), encoding="utf-8").read())
    sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in adlar for x in n.targets))]
    exec(compile(ast.Module(sec, []), dosya, "exec"), ns)
yk, yanki = ns["_yk"], ns["_yanki_mi"]
def dene(ben, karsi, cakisma=2.0): return yanki((0.0, 3.0, yk(ben)), (3.0 - cakisma, 6.0, yk(karsi)))
TABLO = [
    # (ben kanalı, karşı kanal, yankı mı, açıklama)
    ("Merhabalar herkese.", "Teşekkür ederim. Merhabalar herkese.", True, "7 Ekim gerçek yankı"),
    ("Müdür Bey yetki verebiliyor mu?", "Müdür Bey'i artık hatta Müdür Bey'i veriyor artık yani yetkileri öyle söyleyeyim ben", False, "9 Ekim kulaklık: kendi sorusu"),
    ("Takvim Ads, Posta Ads, Mağaza, Depo bir de yedincisi ney", "Posta Ads, Mağaza, Arşiv.", False, "6 Ekim: kendi sayımı + soru"),
    ("Bütçeyi gelecek hafta netleştireceğiz, teklif cuma günü gelir.", "Bütçeyi gelecek hafta netleştireceğiz, teklif cuma günü gelir.", True, "birebir yankı"),
    ("bütçeyi gelecek hafta netleştirecez teklif cuma gelir", "Bütçeyi gelecek hafta netleştireceğiz, teklif cuma günü gelir.", True, "Whisper farklı yazmış yankı (5/7 sırayla)"),
    ("Evet.", "Evet.", True, "tek sözcük yankı"),
    ("Tamam, sözleşmeyi ben gönderirim.", "Sözleşmeyi siz mi göndereceksiniz yoksa biz mi?", False, "aynı konu, cevap"),
    ("Mağaza ve Arşiv erişimi lazım", "Mağaza erişimi var, Arşiv yok.", False, "ortak adlar, farklı cümle"),
    ("Merhabalar herkese.", "Teşekkür ederim. Merhabalar herkese.", False, "zamanda çakışmıyor (0,3 sn)"),
]
hata = 0
for ben, karsi, bek, ac in TABLO:
    sonuc = dene(ben, karsi, 0.3 if "çakışmıyor" in ac else 2.0)
    ok = sonuc == bek; hata += not ok
    print(("✓ " if ok else "✗ ") + f"{ac}: {'yankı' if sonuc else 'kendi sözü'}")
print(f"yankı: {len(TABLO) - hata}/{len(TABLO)}" + (" ✓ hepsi geçti" if not hata else ""))
sys.exit(1 if hata else 0)
