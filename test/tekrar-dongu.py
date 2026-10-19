#!/usr/bin/env python3
# Whisper tekrar döngüsü uydurması (whisper-isci.py tekrar_dongu; 19 Ekim test toplantısı "OBSERV, PARA, OLI, AKMU" + 9 kez "AKMU"): aynı sözcük/öbek art arda ≥ 4
# kez ve satırın en az yarısıysa satır atılır; gerçek tekrar ("evet evet evet") ve uzun cümlede geçen tekrar kalır. İşçi yüklenmez (~0 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tekrar-dongu.py
import ast, os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ns = {"re": re}
a = ast.parse(open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in a.body if isinstance(n, ast.FunctionDef) and n.name in ("tekrar_dongu", "tekrar_kirp")], []), "whisper-isci.py", "exec"), ns)
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
print("tekrar döngüsü: " + ("✓ hepsi geçti" if not hata else f"✗ {hata} hata")); sys.exit(1 if hata else 0)
