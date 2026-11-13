#!/usr/bin/env python3
# Whisper tekrar döngüsü uydurması (whisper-isci.py tekrar_dongu; 19 Ekim test toplantısı "OBSERV, PARA, OLI, AKMU" + 9 kez "AKMU"): aynı sözcük/öbek art arda ≥ 4
# kez ve satırın en az yarısıysa satır atılır; gerçek tekrar ("evet evet evet") ve uzun cümlede geçen tekrar kalır. Nokta öbeği (nokta_ayikla, 30 Ekim). İşçi yüklenmez (~0 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tekrar-dongu.py
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ns = {"re": re}
a = ast.parse(open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in ("_tekrar_bul", "tekrar_dongu", "tekrar_kirp", "tekrar_sadelestir", "hiz_asiri", "nokta_ayikla", "_tepki_obegi", "sayi_suphe", "kurtar_hiz_uygun")) or
                         (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("HARF_DONGU_RX", "NOKTA_OBEK", "NOKTA_YOGUNLUK", "TEPKI_SOZ", "TEPKI_TEK", "UYDURMA", "SAYI_YUZDE_RX", "SAYI_CIPLAK_RX") for t in n.targets))], []), "whisper-isci.py", "exec"), ns)
TABLO = [("OBSERV, PARA, OLI, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU,", True, "19 Ekim gerçek satır"),
         ("Teşekkürler teşekkürler teşekkürler teşekkürler.", True, "tek sözcük döngüsü"), ("Bir iki, bir iki, bir iki, bir iki.", True, "iki sözcüklük öbek"),
         ("Evet evet evet, tamam.", False, "gerçek üçlü tekrar"), ("Evet evet evet evet, anladım ama bütçe konusunda henüz bir karar vermedik, haftaya bakalım.", False, "uzun cümlede tekrar"),
         ("Toplantı yarın saat onda.", False, "düz cümle"), ("", False, "boş")]
hata = 0
for m, b, ad in TABLO:
    v = ns["tekrar_dongu"](m); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {'atılır' if v else 'kalır'}")
# v0.88.2: öbek döngüsünün önünde gerçek söz varsa söz + öbeğin bir kopyası kalır (19 Ekim 18.23 deneme); tek sözcük döngüsü atılır
for m, b, ad in [("Eklentiyi yeniledim. Web toplantısına girdim. Web toplantısına girdim. Web toplantısına girdim. Web toplantısına girdim. Web toplantısına girdim.",
                  "Eklentiyi yeniledim. Web toplantısına girdim.", "gerçek söz + öbek döngüsü → söz kalır"),
                 ("OBSERV, PARA, OLI, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU,", None, "tek sözcük döngüsü kırpılmaz, atılır"),
                 ("Bir iki, bir iki, bir iki, bir iki.", None, "önünde söz yoksa atılır")]:
    v = ns["tekrar_kirp"](m); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v!r}")
# v0.113.1 (22 Ekim test toplantısı): harf döngüsü ve art arda aynı cümle
for m, b, ad in [("ve ölçümleri hepsini geliştirme oturumuna bildir" + "ir" * 150, "ve ölçümleri hepsini geliştirme oturumuna bildir", "harf döngüsü tek sözcükte → bir kez"),
                 ("Marvin burada mısın? Marvin burada mısın? Marvin burada mısın?", "Marvin burada mısın?", "art arda aynı cümle (3 sözcük) → bir kez"),
                 ("Claude: burada mısın? Claude: burada mısın?", "Claude: burada mısın?", "hitaplı tekrar → bir kez"),
                 ("Evet. Evet. Tamam.", "Evet. Evet. Tamam.", "kısa cümle tekrarı kalır (gerçek söz)"),
                 ("Bütçe 10000000 lira, onaylandı.", "Bütçe 10000000 lira, onaylandı.", "rakam döngü sayılmaz"),
                 ("Hahaha çok iyi.", "Hahaha çok iyi.", "gerçek kahkaha (3 kez) kalır"),
                 ("Toplantı yarın saat onda. Toplantı yarın saat onda mı?", "Toplantı yarın saat onda. Toplantı yarın saat onda mı?", "farklı cümle (soru) kalır")]:
    v = ns["tekrar_sadelestir"](m); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v[:70]!r}")
# v0.156.0 (28 Ekim Teams testi, kişi adsız yapay cümlelerle aynı biçim): (1) iki cümlelik öbek (ilkinde virgül, soru işareti, ikincisi nokta) 3 kez + yarım kopya;
# (2) 14 sözcük + tek sözcük ×49 (1 sn'lik parça); doğal tekrar (evet evet, bir dakika. bir dakika., çok çok güzel) bozulmaz
IKI = "Merhaba, bu deneme nasıl? Hemen bak şuna."
for m, b, ad in [(" ".join([IKI] * 3) + " Merhaba, bu deneme", IKI, "iki cümlelik öbek ×3 + yarım kopya → bir kez"),
                 ("Önce şunu söyleyeyim. " + " ".join([IKI] * 3) + " Sonra devam ederiz.", "Önce şunu söyleyeyim. " + IKI + " Sonra devam ederiz.", "öncesi ve sonrası kalır"),
                 ("Bu bir deneme yarın saat onda bu bir deneme yarın saat onda, " + ", ".join(["barbi"] * 49) + ",", None, "14 sözcük + tek sözcük ×49 → atılır"),
                 ("Evet evet, tamam. Bir dakika. Bir dakika. Çok çok güzel.", "Evet evet, tamam. Bir dakika. Bir dakika. Çok çok güzel.", "doğal kısa tekrarlar kalır"),
                 ("Bir iki üç, bir iki üç, bir iki üç.", "Bir iki üç, bir iki üç, bir iki üç.", "3 sözcüklük birim ×3 (sayma) kalır"),
                 ("Tamam anladım tamam anladım tamam anladım.", "Tamam anladım tamam anladım tamam anladım.", "2 sözcüklük birim ×3 kalır"),
                 ("Yarın görüşelim mi? Yarın görüşelim mi? Olur.", "Yarın görüşelim mi? Yarın görüşelim mi? Olur.", "4 sözcüklük birim ×2 kalır"),
                 ("Bütçeyi onaylayalım, takvimi konuşalım, ekibi belirleyelim, sonra da başlayalım.", "Bütçeyi onaylayalım, takvimi konuşalım, ekibi belirleyelim, sonra da başlayalım.", "tekrarsız uzun cümle")]:
    d = ns["tekrar_dongu"](m); v = ns["tekrar_kirp"](m) if d else m; hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {str(v)[:70]!r}")
for m, sn, b, ad in [(" ".join(["kelime"] * 58), 1.02, True, "1 sn'de 58 sözcük → imkânsız hız"), (" ".join(["kelime"] * 20), 4.0, False, "saniyede 5 sözcük kalır"),
                     ("Evet tamam anladım.", 0.3, False, "kısa satır hız denetimine girmez")]:
    v = ns["hiz_asiri"](m, sn); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v}")
# 30 Ekim test toplantısı (kurgu metinle aynı biçim): sözsüz sürekli seste "... ... ..." öbekleri; arada 1–3 sözcük çıkan satır döküme ve askıdaki hitaba giriyordu
N = " ".join(["..."] * 40)
for m, sn, hit, b, ad in [(N, 5.5, (), "", "yalnız üç nokta → atılır"),
                          ("...Bunu yazalım, tamam mı? " + N + " ..", 5.5, (), "...Bunu yazalım, tamam mı?", "sözlü kısım + 40 öbek → öbekler silinir"),
                          ("... Atlas, cevap ver. " + " ".join(["..."] * 8), 5.6, ("Atlas",), "Atlas, cevap ver.", "hitaplı satır: ad ve söz kalır, öbekler gider"),
                          ("... ... ... dedim. " + N, 5.8, (), "", "tek sözcük + öbekler → atılır"),
                          ("... ... ... Atlas. ... ...", 2.0, ("Atlas",), "Atlas.", "yalnız asistan adı + öbekler → ad kalır"),
                          ("... ... ... bir iki ... ... ...", 8.0, (), "", "8 sn'de 2 sözcük (seyrek) → atılır"),
                          ("Şey... bilmiyorum... bakarız.", 3.0, (), "Şey... bilmiyorum... bakarız.", "sözcüğe yapışık üç nokta (gerçek duraksama) kalır"),
                          ("Evet ... tamam ... olur.", 3.0, (), "Evet ... tamam ... olur.", "iki ayrı öbek kalır (eşik 3)"),
                          (". . .", 1.0, (), "", "sözcüksüz noktalama → atılır"), ("Toplantı yarın saat onda.", 2.0, (), "Toplantı yarın saat onda.", "düz cümle")]:
    v = ns["nokta_ayikla"](m, sn, hit)[0]; hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v[:50]!r}")
# 3 Kasım (rapor testler/whisper-uydurma-20261103.md): (1) 2 sözcüklük öbek tam ×3 döngü, gerçek tepkiler (17 gerçek örnek türü) muaf; (2) çıplak kalıp; (3) sayı şüphesi
for m, b, ad in [("Bir iki, bir iki, bir iki.", True, "2 sözcük ×3 (sayma benzeri)"), ("Gel bak gel bak gel bak", True, "2 sözcük ×3 öbek"),
                 ("Görüşürüz iyi günler görüşürüz iyi günler görüşürüz iyi günler", False, "3 sözcük ×3 kalır (kural 4+ sözcük)"),
                 ("Tamam tamam tamam.", False, "tepki: tamam ×3"), ("Evet evet evet.", False, "tepki: evet ×3"), ("Hı hı hı.", False, "tepki: hı hı hı"),
                 ("Mhm mhm mhm.", False, "tepki: mhm ×3"), ("Hmm hmm hmm.", False, "tepki: hmm ×3"), ("Anladım anladım anladım.", False, "tepki: anladım ×3"),
                 ("Tamam anladım tamam anladım tamam anladım.", False, "tepki öbeği ×3"), ("Evet tamam evet tamam evet tamam.", False, "tepki öbeği ×3 (evet tamam)"),
                 ("Tık tık tık.", False, "tık tık tık kalır"), ("Gibi gibi gibi.", False, "gibi gibi gibi kalır"),
                 ("Dün akşam toplantıya girdik, bütçe bu bu bu şekilde gitti ama yine de bir bakalım şimdi.", False, "cümle içinde tek sözcük ×3 kalır"),
                 ("Konu şu: bir ara bir ara bir ara bakalım diye konuşuruz ve haftaya karar veririz kesin.", False, "2 sözcük ×3 ama satırın yarısından az → kalır")]:
    v = ns["tekrar_dongu"](m); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {'atılır' if v else 'kalır'}")
for m, b, ad in [("abone ol", True, "çıplak abone ol"), ("Abone ol.", True, "büyük harfli, noktalı"), ("İzlediğiniz için.", True, "çıplak İzlediğiniz için"), ("izlediğiniz için", True, "küçük harf"),
                 ("izlediğiniz için teşekkür ederim", True, "eski kalıp (teşekkür) hâlâ yakalanır"), ("Abone olmak istiyorum, fiyat nedir?", False, "cümle içi abone olmak kalır"),
                 ("Yeni sisteme abone ol dediler.", False, "cümlede abone ol kalır"), ("Bunu izlediğiniz için teşekkür ederiz Ayşe Hanım.", True, "eski kalıp davranışı değişmedi"),
                 ("Bu videoyu izlediğiniz için", False, "cümle sonunda 'izlediğiniz için' kalır")]:
    v = bool(ns["UYDURMA"].search(m)); hata += v != b; print(("✓ " if v == b else "✗ ") + f"kalıp {ad}: {'atılır' if v else 'kalır'}")
for m, b, ad in [("%83.000'ü", True, "yüzde + binlik ayraç"), ("Bütçenin %83.000'ü harcandı.", True, "cümlede yüzde + binlik"), ("2.000…", True, "bağlamsız 2.000"), ("3.000...", True, "bağlamsız 3.000"),
                 ("290.000 TL", False, "normal tutar"), ("Toplam 290.000 TL harcadık.", False, "cümlede tutar"), ("%83", False, "normal yüzde"), ("yüzde 83", False, "sözlü yüzde"),
                 ("2.000 kişi geldi.", False, "2.000 kişi"), ("%0.500", False, "ondalık yüzde"), ("%30.8", False, "ondalık yüzde 30.8"), ("Rakam 8.000 civarı.", False, "cümlede N.000"), ("", False, "boş")]:
    v = ns["sayi_suphe"](m); hata += v != b; print(("✓ " if v == b else "✗ ") + f"sayı şüphesi {ad}: {'işaretli' if v else 'temiz'}")
# v0.239.1 (12 Kasım gerçek toplantı, elle döküm kontrolü; kişi adsız): ses konuşmaysa (tek_on/tepki) tek sözcük döngüsünün önündeki gerçek söz ve tepki sözcüğünün tek kopyası kalır
G = "Tamam bu konuyu yarın sabah ekiple birlikte konuşalım. Sonra şeyde " + " ".join(["chat"] * 14) + " c"
for m, k, b, ad in [(G, {"tek_on": 5, "tepki": True}, "Tamam bu konuyu yarın sabah ekiple birlikte konuşalım. Sonra şeyde", "gerçek söz + tek sözcük döngüsü → söz kalır"),
                    (G, {}, None, "kurtarma kapalıyken eski davranış (atılır)"),
                    (" ".join(["Evet."] * 13) + " Ev", {"tek_on": 5, "tepki": True}, "Evet.", "tepki döngüsü → tek kopya"),
                    (" ".join(["Abi?"] * 16), {"tek_on": 5, "tepki": True}, "Abi?", "hitap döngüsü → tek kopya"),
                    ("3 3 3 3 3 3 3", {"tek_on": 5, "tepki": True}, None, "sayı döngüsü yine atılır"),
                    ("Uh-huh. Uh-huh. Uh-huh. Uh-huh.", {"tek_on": 5, "tepki": True}, None, "İngilizce tepki yine atılır"),
                    ("Okay okay okay okay okay", {"tek_on": 5, "tepki": True}, None, "İngilizce okay yine atılır"),
                    ("OBSERV, PARA, OLI, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU, AKMU,", {"tek_on": 5, "tepki": True}, None, "3 sözcük + döngü (19 Ekim yankı) yine atılır")]:
    v = ns["tekrar_kirp"](m, **k); hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v!r}")
for m, sn, b, ad in [("Bu bir deneme yarın saat onda bu bir deneme yarın saat onda", 1.0, False, "1 sn'de 12 sözcük kurtarılmaz (28 Ekim)"),
                     ("Tamam bu konuyu yarın sabah ekiple birlikte konuşalım. Sonra şeyde", 5.2, True, "5,2 sn'de 11 sözcük kurtarılır")]:
    v = ns["kurtar_hiz_uygun"](m, sn); hata += v != b; print(("✓ " if v == b else "✗ ") + f"kurtarma hızı {ad}: {v}")
print("tekrar döngüsü: " + ("✓ hepsi geçti" if not hata else f"✗ {hata} hata")); sys.exit(1 if hata else 0)
