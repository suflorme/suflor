#!/usr/bin/env python3
# Whisper tekrar döngüsü uydurması (whisper-isci.py tekrar_dongu; 19 Ekim test toplantısı "OBSERV, PARA, OLI, AKMU" + 9 kez "AKMU"): aynı sözcük/öbek art arda ≥ 4
# kez ve satırın en az yarısıysa satır atılır; gerçek tekrar ("evet evet evet") ve uzun cümlede geçen tekrar kalır. İşçi yüklenmez (~0 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tekrar-dongu.py
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ns = {"re": re}
a = ast.parse(open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in ("_tekrar_bul", "tekrar_dongu", "tekrar_kirp", "tekrar_sadelestir", "hiz_asiri")) or
                         (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "HARF_DONGU_RX" for t in n.targets))], []), "whisper-isci.py", "exec"), ns)
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
print("tekrar döngüsü: " + ("✓ hepsi geçti" if not hata else f"✗ {hata} hata")); sys.exit(1 if hata else 0)
