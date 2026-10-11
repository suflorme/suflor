#!/usr/bin/env python3
# İngilizce arayüz metinlerinin testi. Tek kaynak pano/dil.js (globalThis.SUFLOR_EN; anahtar Türkçe metnin kendisi); eklenti ve
# aktarıcı onu yükler. Kurulum sihirbazı kendi anahtarlı sözlüğünü kullanır (ortak metin 2). Bu test şunları yakalar:
#   1. dil.js'te aynı Türkçe metin iki kez (sonuncusu kazanır, ilki sessizce kaybolur)
#   2. yasak terim ("dashboard", "board") — Suflor.me'de pano = "panel", mini pano = "mini panel" (sihirbaz dahil)
#   3. bir yüzey kendi sözlüğünü yeniden tanımlamış ya da dil.js'i yüklemiyor
#   4. kodda L("…") ile çevrilen sabit metnin dil.js'te İngilizcesi yok
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dil.py      (kaldı → çıkış 1)
import json, os, re, sys

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KULLANAN = ["popup.js", "background.js", "content.js", "pano/pano.html", "pano/hazirlik.html"]
YASAK = re.compile(r"\b(dashboard|board)\b", re.I)
oku = lambda y: open(os.path.join(KOD, y), encoding="utf-8").read()
hatalar = []

# 1–2. tek kaynak: her satırda bir "tr": "en" girdisi
en, satir_dis = {}, 0
STR = r'"(?:[^"\\]|\\.)*"'
for no, satir in enumerate(oku("pano/dil.js").splitlines(), 1):
    m = re.match(rf"\s*({STR})\s*:\s*({STR}),?\s*$", satir)
    if not m:
        if re.match(r'\s*"', satir): satir_dis += 1; hatalar.append(f"dil.js:{no}: girdi okunamadı (her satırda tek \"tr\": \"en\")")
        continue
    tr, ing = json.loads(m.group(1)), json.loads(m.group(2))
    if tr in en: hatalar.append(f"dil.js:{no}: aynı metin iki kez — {tr!r}")
    en[tr] = ing
    if YASAK.search(ing): hatalar.append(f"dil.js:{no}: yasak terim — {tr!r} → {ing!r}")
if "globalThis.SUFLOR_EN" not in oku("pano/dil.js"): hatalar.append("dil.js: globalThis.SUFLOR_EN tanımı yok")

# 3. her yüzey tek kaynağı kullanıyor ve yüklüyor
for y in KULLANAN:
    s = oku(y)
    if re.search(r"\bEN\s*=\s*\{", s): hatalar.append(f"{y}: kendi EN sözlüğü var — metni pano/dil.js'e taşı")
    if "SUFLOR_EN" not in s: hatalar.append(f"{y}: SUFLOR_EN kullanılmıyor")
man = json.loads(oku("manifest.json"))
for cs in man.get("content_scripts", []):
    js = cs.get("js", [])
    if "content.js" in js and ("pano/dil.js" not in js or js.index("pano/dil.js") > js.index("content.js")):
        hatalar.append("manifest.json: içerik betiklerinde pano/dil.js content.js'ten önce yüklenmiyor")
if 'importScripts("pano/dil.js")' not in oku("background.js"): hatalar.append("background.js: importScripts(\"pano/dil.js\") yok")
p = oku("popup.html")
if 'src="pano/dil.js"' not in p or p.index('src="pano/dil.js"') > p.index('src="popup.js"'): hatalar.append("popup.html: pano/dil.js popup.js'ten önce yüklenmiyor")
for y in ("pano/pano.html", "pano/hazirlik.html"):
    if "/*__DIL_SOZLUK__*/" not in oku(y): hatalar.append(f"{y}: aktarıcının gömdüğü /*__DIL_SOZLUK__*/ yer tutucusu yok")
if '"/*__DIL_SOZLUK__*/", pano_dosyasi("dil.js")' not in oku("relay.py"): hatalar.append("relay.py: sayfa() dil.js'i gömmüyor")

# 4. L("sabit metin") / L('sabit metin'); içinde kaçış ya da birleştirme olanlar atlanır
kullanilan = set()
for y in KULLANAN:
    s = oku(y)
    for m in re.finditer(r"""\bL\(\s*(["'])((?:(?!\1)[^\\])*)\1\s*[,)]""", s):
        kullanilan.add(m.group(2))
        if m.group(2) and m.group(2) not in en: hatalar.append(f"{y}: İngilizcesi yok — L({m.group(2)!r})")

# sihirbaz: anahtar adlı ayrı düzen (M.tr / M.en); yalnız İngilizce bloğunda yasak terime bakılır
s = oku("sihirbaz/sihirbaz.js"); m = re.search(r"\n\s*en:\s*\{", s)
if not m: hatalar.append("sihirbaz/sihirbaz.js: en bloğu bulunamadı")
else:
    for satir in s[m.start():s.index("\n  };", m.start())].splitlines():
        if YASAK.search(satir): hatalar.append(f"sihirbaz/sihirbaz.js: yasak terim — {satir.strip()[:120]}")

# bilgi: hiçbir kaynakta metin olarak geçmeyen girdi (değişkenle L(x) çağrılan metinler de burada görünebilir; hata değil)
tum = "".join(oku(y) for y in KULLANAN + ["relay.py", "platform-teams.js", "popup.html"] + sorted(os.path.relpath(f, KOD) for f in __import__("glob").glob(os.path.join(KOD, "aktarici", "*.py"))))  # aktarıcının metni panoda L(x) ile çevrilir
kimsesiz = [k for k in en if k not in kullanilan and json.dumps(k, ensure_ascii=False)[1:-1] not in tum and k not in tum]
print(f"dil: pano/dil.js {len(en)} metin · {len(KULLANAN)} yüzey + sihirbaz · {len(hatalar)} sorun" + (f" · kaynakta görünmeyen {len(kimsesiz)}" if kimsesiz else ""))
for h in hatalar: print("  KALDI:", h)
sys.exit(1 if hatalar else 0)
