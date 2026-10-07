#!/usr/bin/env python3
# İngilizce arayüz metinlerinin tutarlılık testi. Sözlükler dosyalarda ayrı durur (popup, background, content, pano, hazırlık,
# sihirbaz); bu test onların birbirinden kopmasını yakalar:
#   1. aynı Türkçe metin her dosyada aynı İngilizceye çevrilmiş mi
#   2. yasak terim ("dashboard", "board") geçiyor mu — Suflor.me'de pano = "panel", mini pano = "mini panel"
#   3. kodda L("…") ile çevrilen sabit metnin o dosyanın sözlüğünde İngilizcesi var mı
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dil.py      (kaldı → çıkış 1)
import json, os, re, sys

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOZLUKLU = ["popup.js", "background.js", "content.js", "pano/pano.html", "pano/hazirlik.html"]
YASAK = re.compile(r"\b(dashboard|board)\b", re.I)


def blok(s, bas):  # bas'tan sonraki ilk { … } bloğu (dengeli parantez)
    j = s.index("{", bas); d = 0
    for k in range(j, len(s)):
        d += {"{": 1, "}": -1}.get(s[k], 0)
        if d == 0: return s[j:k + 1]
    raise ValueError("kapanmayan blok")


def sozluk(yol):
    s = open(os.path.join(KOD, yol), encoding="utf-8").read()
    m = re.search(r"\bEN\s*=\s*\{", s)
    if not m: raise ValueError(f"{yol}: EN sözlüğü bulunamadı")
    return s, json.loads(blok(s, m.start()))


hatalar, ceviri = [], {}  # ceviri: Türkçe → {dosya: İngilizce}
for yol in SOZLUKLU:
    try: s, en = sozluk(yol)
    except Exception as e: hatalar.append(f"{yol}: sözlük okunamadı ({e})"); continue
    for tr, ing in en.items():
        ceviri.setdefault(tr, {})[yol] = ing
        if YASAK.search(ing): hatalar.append(f"{yol}: yasak terim — {tr!r} → {ing!r}")
    # L("sabit metin") / L('sabit metin'); içinde kaçış ya da birleştirme olanlar atlanır
    for m in re.finditer(r"""\bL\(\s*(["'])((?:(?!\1)[^\\])*)\1\s*[,)]""", s):
        if m.group(2) and m.group(2) not in en: hatalar.append(f"{yol}: İngilizcesi yok — L({m.group(2)!r})")

for tr, d in ceviri.items():
    if len(set(d.values())) > 1: hatalar.append(f"farklı çeviri — {tr!r}: " + "; ".join(f"{y} → {v!r}" for y, v in d.items()))

# sihirbaz: anahtar adlı ayrı düzen (M.tr / M.en); yalnız İngilizce bloğunda yasak terime bakılır
s = open(os.path.join(KOD, "sihirbaz/sihirbaz.js"), encoding="utf-8").read()
m = re.search(r"\n\s*en:\s*\{", s)
if not m: hatalar.append("sihirbaz/sihirbaz.js: en bloğu bulunamadı")
else:
    for satir in blok(s, m.start()).splitlines():
        if YASAK.search(satir): hatalar.append(f"sihirbaz/sihirbaz.js: yasak terim — {satir.strip()[:120]}")

ortak = sum(1 for d in ceviri.values() if len(d) > 1)
print(f"dil: {len(SOZLUKLU)} sözlük + sihirbaz · {len(ceviri)} metin, {ortak} ortak · {len(hatalar)} sorun")
for h in hatalar: print("  KALDI:", h)
sys.exit(1 if hatalar else 0)
