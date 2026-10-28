#!/usr/bin/env python3
# Sesli "Claude:" hitabı (aktarici/sozluk.py HITAP_RX, hitap_duzelt): Whisper'ın "Cloud"/"Klod" yazımı kullanıcı satırında cümle başında
# "Claude:" olur; bulut anlamı değişmez. Aktarıcının kendi tanımları AST ile alınır (kopya kural yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hitap.py      (kaldı → çıkış 1)
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIS = {"v": None, "v2": None}; ns = {"re": re, "time": __import__("time"), "kisilikler": lambda: [x for x in (KIS["v"], KIS["v2"]) if x]}  # v0.53.0: kişilik hitabı (nötr örnek ad "Atlas")
agac = ast.parse(open(os.path.join(KOD, "aktarici/sozluk.py"), encoding="utf-8").read())
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in ("hitap_duzelt", "_kisilik_hitap_rx", "_kisilik_hitap_ad", "hitap_aski", "hitap_askida", "hitap_aski_bitti",
                                                                    "_hitap_adlari", "_hitap_alt", "_hitap_rx", "hitap_yalniz_ad", "hitap_cevap_baslat", "hitap_aski_metin")) or
       (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in {"HITAP_RX", "HITAP_ORTA_RX", "HITAP_AD", "BULUT", "_KHR", "HITAP_ASKI", "HITAP_ASKI_SN", "HITAP_DEVAM_SN", "HITAP_AD_DEVAM_SN",
                                                                      "HITAP_ONCE_N", "HITAP_EN_COK_SN", "HITAP_EN_COK_SOZ", "HITAP_ONCE"} for x in n.targets))]
ka = ast.parse(open(os.path.join(KOD, "aktarici/kisilik.py"), encoding="utf-8").read())  # 19 Ekim: söz etme kalıbı kisilik.py'de (iki yer aynı tanımı kullanır)
sec = [n for n in ka.body if isinstance(n, ast.Assign) and any(getattr(x, "id", None) in ("KISILIK_SOZ_ETME", "KISILIK_ISTEK", "KISILIK_GIRIS") for x in n.targets)] + sec
exec(compile(ast.Module(sec, []), "sozluk.py", "exec"), ns)
TABLO = [
    ("Cloud, card, English, yes.", "Cloud, card, English, yes.", "S133: Claude adı seslenme değil — 9 Ekim: virgüllü"),
    ("...Cloud kaydı kapat.", "...Cloud kaydı kapat.", "S133: Claude adı seslenme değil — 11 Ekim: üç noktadan sonra, virgülsüz"),
    ("Hikayesi duyulmadan... ...Cloud kaydı kapat.", "Hikayesi duyulmadan... ...Cloud kaydı kapat.", "S133: Claude adı seslenme değil — 11 Ekim gerçek satır yapısı"),
    ("Tamam. Klod not al bunu.", "Tamam. Klod not al bunu.", "S133: Claude adı seslenme değil — nokta + virgülsüz"),
    ("Klo, özet çıkar.", "Klo, özet çıkar.", "S133: Claude adı seslenme değil — Klo hitabı"),
    ("Cloud hizmeti pahalı geldi.", "Cloud hizmeti pahalı geldi.", "bulut anlamı, cümle başı"),
    ("Cloud tabanlı bir sistem kuracağız.", "Cloud tabanlı bir sistem kuracağız.", "bulut anlamı"),
    ("Biz cloud'a bağımlıyız.", "Biz cloud'a bağımlıyız.", "cümle ortası, kesmeli"),
    ("Bunu cloud kaydı olarak tutalım.", "Bunu cloud kaydı olarak tutalım.", "cümle ortası, virgülsüz"),
    ("Cloud'a taşıdık.", "Cloud'a taşıdık.", "cümle başı, kesmeli"),
    ("Cloud.", "Cloud.", "tek sözcük"),
    ("Klot. Kaç kart açık?", "Klot. Kaç kart açık?", "S133: Claude adı seslenme değil — 12 Ekim: hitaptan sonra nokta"),
    ("Tamam. Klot. Not al.", "Tamam. Klot. Not al.", "S133: Claude adı seslenme değil — nokta + hitap + nokta"),
    ("Cloud. Hizmeti pahalı.", "Cloud. Hizmeti pahalı.", "nokta sonrası bulut anlamı"),
    ("Bunu yapayım. Claude kaç kart açık?", "Bunu yapayım. Claude kaç kart açık?", "S133: Claude adı seslenme değil — 12 Ekim: doğru yazım, cümle başı"),
    ("Bunu yapayım Claude kaç kart açık?", "Bunu yapayım Claude kaç kart açık?", "S133: Claude adı seslenme değil — cümle ortası, soru"),
    ("Bunu Claude mu yazdı?", "Bunu Claude mu yazdı?", "cümle ortası, soru eki"),
    ("Bunu Claude ile yazdık.", "Bunu Claude ile yazdık.", "cümle ortası, soru değil"),
    ("Suflor, kaç kart açık?", "Claude: kaç kart açık?", "Suflor uyandırma sözü"),
    ("Tamam. Suflor. Not al.", "Tamam. Claude: Not al.", "S133: nokta + Suflor + nokta"),
    ("Bunu yapayım Suflor kaç kart açık?", "Bunu yapayım. Claude: kaç kart açık?", "S133: Suflor cümle ortası, soru"),
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
    ("Atlas gelsin", "Claude: gelsin", "S94: virgülsüz istek (-sın/-sin) seslenme"),
    ("Atlas özetle son on dakikayı", "Claude: özetle son on dakikayı", "S94: virgülsüz istek fiili seslenme"),
    ("Atlas bunu kontrol eder misin", "Claude: bunu kontrol eder misin", "S94: '…er misin' sorusuz da seslenme"),
    ("Atlas dün güzel cevap verdi.", "Atlas dün güzel cevap verdi.", "S94: istek yok, addan söz — seslenme değil"),
    ("Claude, özet çıkar.", "Claude, özet çıkar.", "S94: kişilik açıkken Claude seslenme değil (tek kural: asistanın adı)"),
    ("Suflor, kaç kart açık?", "Suflor, kaç kart açık?", "S94: kişilik açıkken Suflor seslenme değil"),
    ("Tamam, Atlas, bunu not al.", "Tamam, Claude: bunu not al.", "v0.101.1: giriş sözü + virgül + ad (ölçümde 12/14 kaçıyordu)"),
    ("Tamam Atlas bunu not al.", "Tamam Claude: bunu not al.", "v0.101.1: giriş sözü, virgülsüz istek"),
    ("Selam Atlas, yarına bakar mısın?", "Selam Claude: yarına bakar mısın?", "v0.101.1: selam + ad + rica"),
    ("Tamam. Merhaba Atlaz, kaç kart açık?", "Tamam. Merhaba Claude: kaç kart açık?", "v0.101.1: noktadan sonra selam + ad"),
    ("Tamam, Atlas dün iyi cevap verdi.", "Tamam, Atlas dün iyi cevap verdi.", "v0.101.1: giriş sözünden sonra da addan söz seslenme değil"),
    ("Merhaba Atlas'a selam söyle.", "Merhaba Atlas'a selam söyle.", "v0.101.1: selam + ekli ad seslenme değil"),
    ("Bak Atlas ne güzel olmuş.", "Bak Atlas ne güzel olmuş.", "v0.101.1: listede olmayan söz (bak) giriş sayılmaz"),
    # v0.113.1 (22 Ekim test toplantısı: "Tamam... Orney... eee... Bugün projede... açık kalan iş kaldı mı?" ~1 dk cevapsız): addan sonra üç noktalı duraksama
    ("Tamam... Atlaz... eee... Bugün projede... açık kalan iş kaldı mı? Bir kontrol eder misin?", "Tamam... Claude: eee... Bugün projede... açık kalan iş kaldı mı? Bir kontrol eder misin?", "v0.113.1: ad + üç nokta + soru"),
    ("Atlas… şunu özetle.", "Claude: şunu özetle.", "v0.113.1: ad + üç nokta + istek"),
    ("Atlas... ile ilgili bir şey sorayım mı?", "Atlas... ile ilgili bir şey sorayım mı?", "v0.113.1: üç noktadan sonra da addan söz seslenme değil"),
    ("Atlas... evet güzeldi.", "Atlas... evet güzeldi.", "v0.113.1: üç nokta, soru/istek yok — seslenme değil")]:
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
ok = r6 is None; hata += not ok; print(("✓ " if ok else "✗ ") + "S94: kişilik açıkken Claude yazımı (Klod) askıya alınmaz")
ha("Atlas gelsin", T + 100, T + 101); ok = ns["hitap_askida"]("Atlas gelsin") and ns["hitap_aski_bitti"]("Atlas gelsin") == "Atlas gelsin" and not ns["hitap_askida"]("Atlas gelsin")
hata += not ok; print(("✓ " if ok else "✗ ") + "S94: devamı gelmeyen askıdaki hitap tek başına bırakılır (hitap_aski_bitti)")
KIS["v"] = None
ha("Süflör şu an", T + 120, T + 121); r7 = ha("kaç kart açık?", T + 121.3, T + 123)
ok = r7 == "Süflör şu an kaç kart açık?" and ns["hitap_duzelt"](r7)[0].startswith("Claude:"); hata += not ok; print(("✓ " if ok else "✗ ") + "kişiliksiz kurulumda Suflor yazımlarıyla da (Süflör)")
ha("Klod şu an", T + 140, T + 141); r8 = ha("kaç kart açık?", T + 141.3, T + 143)
ok = r8 is None; hata += not ok; print(("✓ " if ok else "✗ ") + "S133: kişiliksiz kurulumda Claude yazımı (Klod) askıya alınmaz")
# v0.140.0 (27 Ekim, ikinci hesap — gerçek parça dizisi, adlar örnek): ad tek başına bir parça; önündeki ve arkasındaki parçalar tek hitapta birleşir
KIS["v"] = {"ad": "Atlas", "rol": "toplanti", "hitap": ["Atlas", "Atlaz"]}; KIS["v2"] = None
ask, ak, ab = ns["hitap_askida"], ns["hitap_aski_metin"], ns["hitap_aski_bitti"]
dizi = [("yarın", 200.0, 200.8), ("on ikide", 201.4, 202.2), ("Atlas,", 202.6, 203.0), ("Deniz ile", 203.3, 204.1), ("bir toplantı planına", 204.6, 206.0), ("takvime ekle.", 207.9, 209.0)]
sonuc = [ha(m, a, b) for m, a, b in dizi]
ok = sonuc[:5] == [None] * 5 and sonuc[5] == "Atlas, yarın on ikide Deniz ile bir toplantı planına takvime ekle." \
     and ns["hitap_duzelt"](sonuc[5])[0] == "Claude: yarın on ikide Deniz ile bir toplantı planına takvime ekle."; hata += not ok
print(("✓ " if ok else "✗ ") + f"yalnız ad + önceki/sonraki parçalar tek hitap: {sonuc[5]!r}")
ha("Tamam teşekkürler.", 300, 301); ha("yarın on ikide Deniz ile", 301.5, 303); ha("Atlas", 303.5, 304); ok = ask("Atlas") and ak() == "Atlas, yarın on ikide Deniz ile"
ha("bir toplantı planına", 304.5, 306); ok = ok and ask("bir toplantı planına") and ak() == "Atlas, yarın on ikide Deniz ile bir toplantı planına"
ok = ok and ab("Atlas, yarın on ikide Deniz ile") is None and ab(ak()) == "Atlas, yarın on ikide Deniz ile bir toplantı planına" and ak() is None; hata += not ok
print(("✓ " if ok else "✗ ") + "noktalı satırda önceki ek durur; cümle bitmezse süre dolunca birikmiş metin gider (eski zamanlayıcı boşa)")
ha("Atlas,", 400, 400.5); r9 = ha("bütçe ne durumda?", 408.5, 410)
ok = r9 is None and not ask("bütçe ne durumda?") and ak() is None; hata += not ok  # askıdaki ad zamanlayıcıyla zaten gitmişti (hitap_aski_zaman)
print(("✓ " if ok else "✗ ") + f"yalnız addan {ns['HITAP_AD_DEVAM_SN']:.0f} sn'den geç gelen satır eklenmez")
ok = ns["hitap_yalniz_ad"]("Atlaz.") == "Atlaz" and ns["hitap_yalniz_ad"]("Atlas gelsin") is None and ns["hitap_yalniz_ad"]("Atlası") is None; hata += not ok
print(("✓ " if ok else "✗ ") + "yalnız ad tanıma (Whisper yazımı, ekli ad ve devamlı satır değil)")
# asistanın sorusuna hitapsız cevap: noktalama bitirmez, süre bitirir (gerçek dizi: üç kısa cümle)
ns["hitap_cevap_baslat"]("Atlas", "bugün öğlen on ikide.", 500, 501.5)
r10 = [ha(m, a, b) for m, a, b in [("takvimimde oluştur.", 503.5, 505), ("maile de taslak olarak yaz.", 507.5, 509)]]
ok = r10 == [None, None] and ask("maile de taslak olarak yaz.") and ab(ak()) == "Atlas, bugün öğlen on ikide. takvimimde oluştur. maile de taslak olarak yaz."; hata += not ok
print(("✓ " if ok else "✗ ") + "asistanın sorusuna hitapsız cevap birikir, süre dolunca o asistana")
bk = ast.parse(open(os.path.join(KOD, "aktarici/bas-konus.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in bk.body if (isinstance(n, ast.FunctionDef) and n.name in ("asistan_soru_kaydet", "asistan_cevap_bekliyor")) or
                         (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in ("ASISTAN_SORU_SN", "_ASISTAN_SORU") for x in n.targets))], []), "bas-konus.py", "exec"), ns)
ns["TS"] = {}; now = __import__("time").time()
ns["asistan_soru_kaydet"]("Atlas", "Evet, duydum. Toplantı bugün öğlen mi, salı mı?\n---\nAyrıntı."); ok = ns["asistan_cevap_bekliyor"](now + 8) == "Atlas" and ns["asistan_cevap_bekliyor"](now + 9) is None
ns["asistan_soru_kaydet"]("Atlas", "Tamam, ekledim."); ok = ok and ns["asistan_cevap_bekliyor"](now + 5) is None
ns["asistan_soru_kaydet"]("Atlas", "Hangi gün?"); ok = ok and ns["asistan_cevap_bekliyor"](now + 40) is None
ns["asistan_soru_kaydet"]("Atlas", "Hangi gün?"); ns["TS"]["son_t"] = now + 30; ok = ok and ns["asistan_cevap_bekliyor"](now + 45) == "Atlas"; hata += not ok
print(("✓ " if ok else "✗ ") + "asistanın sorusu: 20 sn içinde bir kez cevap bekler; soru değilse ya da geç kalırsa beklemez; toplantıya okunduysa okuma sonundan sayar")

# v0.125.1 (23 Ekim üçlü sohbet denemesi; gerçek cümleler örnek adlarla): Konuş/sohbette kişilik seçimi — takma ad, Whisper yazımları, ikinci cümledeki ad, sondaki seslenme
exec(compile(ast.Module([n for n in ka.body if isinstance(n, ast.FunctionDef) and n.name in ("kisilik_hitap_bul", "kisilik_hitap_icte")], []), "kisilik.py", "exec"), ns)
KIS["v"] = {"ad": "Atlas", "rol": "toplanti", "hitap": ["Atlas", "Atlaz", "Atti", "Atte", "Attisan", "Atti Hanım"]}
KIS["v2"] = {"ad": "Matlas", "rol": "disi", "hitap": ["Matlas", "Matti", "Mattin"]}
def kim(m):
    k, _ = ns["kisilik_hitap_bul"](m); k = k or ns["kisilik_hitap_icte"](m); return k["ad"] if k else None
for girdi, bek, ac in [
    ("Yani tabi ki cuma günlerini seviyoruz. Atte sen hangi günü en çok seversin?", "Atlas", "gerçek: ad ikinci cümlenin başında (Whisper yazımı)"),
    ("Atti, sen ne dersin?", "Atlas", "takma ad + virgül"),
    ("Sen ne dersin, Atti?", "Atlas", "sondaki seslenme + soru"),
    ("Peki sen hangisini seçerdin Atte?", "Atlas", "sondaki ad + soru, virgülsüz"),
    ("Evet, Matti, cevap ver bakalım. Attenin... Sorusu da", "Matlas", "gerçek: giriş + ad ilk cümlede (sonraki iyelik seslenme değil)"),
    ("Anladım. Matti Attisan'a felaket laf çaktı yalnız.", "Matlas", "gerçek: takılma adının Whisper yazımı ekli — söz etme"),
    ("Atti'nin filmi güzeldi, ben de izlerim.", None, "iyelik ekli ad seslenme değil"),
    ("Arkadaşlar ikiniz de çok komiksiniz.", None, "ikisine söz: kişilik adı yok")]:
    c = kim(girdi); ok = c == bek; hata += not ok
    print(f"{'✓' if ok else '✗'} üçlü hitap — {ac}: {girdi!r} → {c}" + ("" if ok else f" (beklenen {bek})"))
KIS["v"] = KIS["v2"] = None

print("GEÇTİ" if not hata else f"KALDI: {hata}")
sys.exit(1 if hata else 0)
