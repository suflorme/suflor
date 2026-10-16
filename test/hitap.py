#!/usr/bin/env python3
# Sesli "Claude:" hitabı (aktarici/sozluk.py HITAP_RX, hitap_duzelt): Whisper'ın "Cloud"/"Klod" yazımı kullanıcı satırında cümle başında
# "Claude:" olur; bulut anlamı değişmez. Aktarıcının kendi tanımları AST ile alınır (kopya kural yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hitap.py      (kaldı → çıkış 1)
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIS = {"v": None}; ns = {"re": re, "kisilik": lambda: KIS["v"]}  # v0.53.0: kişilik hitabı (nötr örnek ad "Atlas")
agac = ast.parse(open(os.path.join(KOD, "aktarici/sozluk.py"), encoding="utf-8").read())
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in ("hitap_duzelt", "_kisilik_hitap_rx")) or
       (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in {"HITAP_RX", "HITAP_ORTA_RX", "HITAP_AD", "BULUT", "_KHR"} for x in n.targets))]
exec(compile(ast.Module(sec, []), "sozluk.py", "exec"), ns)
TABLO = [
    ("Cloud, card, English, yes.", "Claude: card, English, yes.", "9 Ekim: virgüllü"),
    ("...Cloud kaydı kapat.", "...Claude: kaydı kapat.", "11 Ekim: üç noktadan sonra, virgülsüz"),
    ("Hikayesi duyulmadan... ...Cloud kaydı kapat.", "Hikayesi duyulmadan... ...Claude: kaydı kapat.", "11 Ekim gerçek satır yapısı"),
    ("Tamam. Klod not al bunu.", "Tamam. Claude: not al bunu.", "nokta + virgülsüz"),
    ("Klo, özet çıkar.", "Claude: özet çıkar.", "Klo hitabı"),
    ("Cloud hizmeti pahalı geldi.", "Cloud hizmeti pahalı geldi.", "bulut anlamı, cümle başı"),
    ("Cloud tabanlı bir sistem kuracağız.", "Cloud tabanlı bir sistem kuracağız.", "bulut anlamı"),
    ("Biz cloud'a bağımlıyız.", "Biz cloud'a bağımlıyız.", "cümle ortası, kesmeli"),
    ("Bunu cloud kaydı olarak tutalım.", "Bunu cloud kaydı olarak tutalım.", "cümle ortası, virgülsüz"),
    ("Cloud'a taşıdık.", "Cloud'a taşıdık.", "cümle başı, kesmeli"),
    ("Cloud.", "Cloud.", "tek sözcük"),
    ("Klot. Kaç kart açık?", "Claude: Kaç kart açık?", "12 Ekim: hitaptan sonra nokta"),
    ("Tamam. Klot. Not al.", "Tamam. Claude: Not al.", "nokta + hitap + nokta"),
    ("Cloud. Hizmeti pahalı.", "Cloud. Hizmeti pahalı.", "nokta sonrası bulut anlamı"),
    ("Bunu yapayım. Claude kaç kart açık?", "Bunu yapayım. Claude: kaç kart açık?", "12 Ekim: doğru yazım, cümle başı"),
    ("Bunu yapayım Claude kaç kart açık?", "Bunu yapayım. Claude: kaç kart açık?", "cümle ortası, soru"),
    ("Bunu Claude mu yazdı?", "Bunu Claude mu yazdı?", "cümle ortası, soru eki"),
    ("Bunu Claude ile yazdık.", "Bunu Claude ile yazdık.", "cümle ortası, soru değil"),
    ("Suflor, kaç kart açık?", "Claude: kaç kart açık?", "Suflor uyandırma sözü"),
    ("Süflör not al.", "Claude: not al.", "Suflor, Whisper yazımı"),
    ("Suflor'u kapattım.", "Suflor'u kapattım.", "Suflor ekli, hitap değil"),
    ("Dün Suflor çok iyiydi.", "Dün Suflor çok iyiydi.", "Suflor cümle ortası, soru değil"),
]
hata = 0
for girdi, bek, ac in TABLO:
    cik, _ = ns["hitap_duzelt"](girdi); ok = cik == bek; hata += not ok
    print(f"{'✓' if ok else '✗'} {ac}: {girdi!r} → {cik!r}" + ("" if ok else f" (beklenen {bek!r})"))
# kişilik açıkken (16 Ekim ölçümünden çıkan kural: ad + noktalama ya da soru cümlesi); eski hitaplar geçiş döneminde sürer
KIS["v"] = {"hitap": ["Atlas", "Atlaz", "Hatlas"]}
for girdi, bek, ac in [
    ("Atlas, bugün kaç toplantım var?", "Claude: bugün kaç toplantım var?", "kişilik: virgüllü"),
    ("ATLAS: fiyat kaç olarak geçti?", "Claude: fiyat kaç olarak geçti?", "kişilik: iki noktalı, büyük harf"),
    ("Atlaz bu karar çelişiyor mu?", "Claude: bu karar çelişiyor mu?", "kişilik: Whisper yazımı, virgülsüz soru"),
    ("Hatlas. Açık iş var mı?", "Claude: Açık iş var mı?", "kişilik: noktadan sonra büyük harf"),
    ("Atlas markasının yeni ürünü güzel olmuş.", "Atlas markasının yeni ürünü güzel olmuş.", "kişilik: hitap değil (soru değil, noktalama yok)"),
    ("Dün Atlas çok iyiydi.", "Dün Atlas çok iyiydi.", "kişilik: cümle ortası"),
    ("Claude, özet çıkar.", "Claude: özet çıkar.", "kişilik açıkken eski hitap da sürer"),
    ("Suflor, kaç kart açık?", "Claude: kaç kart açık?", "kişilik açıkken Suflor da sürer (geçiş)")]:
    cik, _ = ns["hitap_duzelt"](girdi); ok = cik == bek; hata += not ok
    print(f"{'✓' if ok else '✗'} {ac}: {girdi!r} → {cik!r}" + ("" if ok else f" (beklenen {bek!r})"))
KIS["v"] = None
cik, _ = ns["hitap_duzelt"]("Atlas, bugün kaç toplantım var?"); ok = cik == "Atlas, bugün kaç toplantım var?"; hata += not ok
print(f"{'✓' if ok else '✗'} kişilik dosyası yokken ad hitap değil: {cik!r}")
print("GEÇTİ" if not hata else f"KALDI: {hata}")
sys.exit(1 if hata else 0)
