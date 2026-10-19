#!/usr/bin/env python3
# Sesli "Claude:" hitabı (aktarici/sozluk.py HITAP_RX, hitap_duzelt): Whisper'ın "Cloud"/"Klod" yazımı kullanıcı satırında cümle başında
# "Claude:" olur; bulut anlamı değişmez. Aktarıcının kendi tanımları AST ile alınır (kopya kural yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hitap.py      (kaldı → çıkış 1)
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIS = {"v": None, "v2": None}; ns = {"re": re, "time": __import__("time"), "kisilikler": lambda: [x for x in (KIS["v"], KIS["v2"]) if x]}  # v0.53.0: kişilik hitabı (nötr örnek ad "Atlas")
agac = ast.parse(open(os.path.join(KOD, "aktarici/sozluk.py"), encoding="utf-8").read())
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in ("hitap_duzelt", "_kisilik_hitap_rx", "_kisilik_hitap_ad", "hitap_aski")) or
       (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in {"HITAP_RX", "HITAP_ORTA_RX", "HITAP_AD", "BULUT", "_KHR", "HITAP_ASKI", "HITAP_ASKI_SN"} for x in n.targets))]
ka = ast.parse(open(os.path.join(KOD, "aktarici/kisilik.py"), encoding="utf-8").read())  # 19 Ekim: söz etme kalıbı kisilik.py'de (iki yer aynı tanımı kullanır)
sec = [n for n in ka.body if isinstance(n, ast.Assign) and any(getattr(x, "id", None) == "KISILIK_SOZ_ETME" for x in n.targets)] + sec
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
KIS["v"] = {"ad": "Atlas", "rol": "toplanti", "hitap": ["Atlas", "Atlaz", "Hatlas"]}
for girdi, bek, ac in [
    ("Atlas, bugün kaç toplantım var?", "Claude: bugün kaç toplantım var?", "kişilik: virgüllü"),
    ("ATLAS: fiyat kaç olarak geçti?", "Claude: fiyat kaç olarak geçti?", "kişilik: iki noktalı, büyük harf"),
    ("Atlaz bu karar çelişiyor mu?", "Claude: bu karar çelişiyor mu?", "kişilik: Whisper yazımı, virgülsüz soru"),
    ("Hatlas. Açık iş var mı?", "Claude: Açık iş var mı?", "kişilik: noktadan sonra büyük harf"),
    ("Atlas markasının yeni ürünü güzel olmuş.", "Atlas markasının yeni ürünü güzel olmuş.", "kişilik: hitap değil (soru değil, noktalama yok)"),
    ("Dün Atlas çok iyiydi.", "Dün Atlas çok iyiydi.", "kişilik: cümle ortası"),
    ("Atlas ile ilgili problem neydi?", "Atlas ile ilgili problem neydi?", "19 Ekim: kişilikten söz (ile ilgili), seslenme değil"),
    ("Tamam. Atlas hakkında ne düşünüyorsun?", "Tamam. Atlas hakkında ne düşünüyorsun?", "kişilikten söz (hakkında)"),
    ("Atlas mı cevap verdi?", "Atlas mı cevap verdi?", "kişilikten söz (soru eki)"),
    ("Atlas'ın sesi neden kesildi?", "Atlas'ın sesi neden kesildi?", "kişilikten söz (kesmeli ek)"),
    ("Atlas neden kesik konuşuyordu?", "Claude: neden kesik konuşuyordu?", "soru cümlesi, ad + soru: seslenme (kural aynı)"),
    ("Claude, özet çıkar.", "Claude: özet çıkar.", "kişilik açıkken eski hitap da sürer"),
    ("Suflor, kaç kart açık?", "Claude: kaç kart açık?", "kişilik açıkken Suflor da sürer (geçiş)")]:
    cik, _ = ns["hitap_duzelt"](girdi); ok = cik == bek; hata += not ok
    print(f"{'✓' if ok else '✗'} {ac}: {girdi!r} → {cik!r}" + ("" if ok else f" (beklenen {bek!r})"))
# v0.61.0: iki kişilik — ikinci adın içinde birincinin yazımı geçse de (Matlas ⊃ atlas) doğru kişilik tanınır
KIS["v2"] = {"ad": "Matlas", "rol": "disi", "hitap": ["Matlas", "Oh Matlas", "Oh, Matlas"]}
for girdi, bek, kim, ac in [
    ("Matlas, yarın ne var?", "Claude: yarın ne var?", "Matlas", "ikinci kişilik: virgüllü"),
    ("Oh, Matlas, bugün nasıl geçti?", "Claude: bugün nasıl geçti?", "Matlas", "ikinci kişilik: 'Oh,' önekiyle"),
    ("Atlas, kaç kart açık?", "Claude: kaç kart açık?", "Atlas", "iki kişilik açıkken birinci de tanınır"),
    ("Dün Matlas'ı aradım.", "Dün Matlas'ı aradım.", None, "ikinci kişilik: cümle ortası hitap değil")]:
    ns["_KHR"]["son"] = None; cik, _ = ns["hitap_duzelt"](girdi); sn = (ns["_KHR"]["son"] or (None,))[0]; ok = cik == bek and sn == kim; hata += not ok
    print(f"{'✓' if ok else '✗'} {ac}: {girdi!r} → {cik!r} · {sn}" + ("" if ok else f" (beklenen {bek!r} · {kim})"))
rx = ns["_kisilik_hitap_rx"]("toplanti"); ok = bool(rx.search("Atlas, özet?")) and not rx.search("Matlas, özet?"); hata += not ok
print(f"{'✓' if ok else '✗'} karşı taraf kalıbı yalnız toplantı kişiliğinin adı")
KIS["v"] = KIS["v2"] = None
cik, _ = ns["hitap_duzelt"]("Atlas, bugün kaç toplantım var?"); ok = cik == "Atlas, bugün kaç toplantım var?"; hata += not ok
print(f"{'✓' if ok else '✗'} kişilik dosyası yokken ad hitap değil: {cik!r}")
# 19 Ekim test toplantısı: hitap iki satıra bölündü ("<ad> şu an" + "toplantıda kaç tane şey var? … kontrol eder misin?") → birleşik metinde hitap
KIS["v"] = {"ad": "Atlas", "rol": "toplanti", "hitap": ["Atlas", "Atlaz"]}; KIS["v2"] = None
ha = ns["hitap_aski"]; T = 1000.0
r1 = ha("Atlas şu an", T, T + 1.5); r2 = ha("toplantıda kaç tane şey var? Kontrol eder misin?", T + 2.0, T + 7.5)
b = ns["hitap_duzelt"](r2 or "")[0]
ok = r1 is None and r2 == "Atlas şu an toplantıda kaç tane şey var? Kontrol eder misin?" and b.startswith("Claude: şu an toplantıda"); hata += not ok
print(("✓ " if ok else "✗ ") + f"bölünen hitap birleşir: {b!r}")
ha("Atlas şu an", T + 20, T + 21); r3 = ha("toplantıda kaç kişi var?", T + 24, T + 26)
ok = r3 is None; hata += not ok; print(("✓ " if ok else "✗ ") + "2 sn'den geç gelen satır birleşmez")
ha("Atlas, kaç kart açık?", T + 40, T + 41); r4 = ha("Bir de özet çıkar.", T + 41.5, T + 43)
ok = r4 is None; hata += not ok; print(("✓ " if ok else "✗ ") + "noktalamayla biten tam hitap askıya alınmaz")
ha("Bugün şu an", T + 60, T + 61); r5 = ha("toplantıda kaç kişi var?", T + 61.2, T + 63)
ok = r5 is None; hata += not ok; print(("✓ " if ok else "✗ ") + "adla başlamayan satır askıya alınmaz")
ha("Klod şu an", T + 80, T + 81); r6 = ha("kaç kart açık?", T + 81.3, T + 83)
ok = r6 == "Klod şu an kaç kart açık?" and ns["hitap_duzelt"](r6)[0].startswith("Claude:"); hata += not ok; print(("✓ " if ok else "✗ ") + "Claude yazımlarıyla da (Klod)")

print("GEÇTİ" if not hata else f"KALDI: {hata}")
sys.exit(1 if hata else 0)
