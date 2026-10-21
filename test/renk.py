#!/usr/bin/env python3
# Renkler, yazı boyları ve köşeler tek kaynakta (v0.99.2; boy/köşe v0.99.3, pano/renk.css): pano ve hazırlık gömer, eklenti penceresi ve sihirbaz bağlar; Teams şeridi (content.js, gölge DOM) aynı
# değerleri taşır. Okunurluk (WCAG AA ≥ 4,5:1): soluk yazı (--t3) tüm zeminlerde, uyarı (--wa) yüzeyde ve kendi zemininde, ana düğme yazısı dolgusunda.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/renk.py      — renk değiştirince ya da yeni yüzey eklenince
import os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)
oku = lambda p: open(os.path.join(KOD, p), encoding="utf-8").read()
R = oku("pano/renk.css")
def jetonlar(blok): return dict(re.findall(r"--([a-z0-9-]+):([^;}]+)", blok))
acik = jetonlar(R[R.index(":root{"):R.index("@media")]); koyu = jetonlar(R[R.index(":root:not([data-theme=light])"):R.index(":root[data-theme=dark]")])
koyu2 = jetonlar(R[R.index(":root[data-theme=dark]"):])
kontrol("koyu tema iki yolda aynı (sistem tercihi ve data-theme=dark)", koyu == koyu2)
def L(h):
    h = h.strip().lstrip("#"); h = "".join(c * 2 for c in h) if len(h) == 3 else h; c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]; return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def oran(a, b): x, y = sorted([L(a), L(b)], reverse=True); return (x + 0.05) / (y + 0.05)
for ad, j in (("açık", acik), ("koyu", koyu)):
    en = min(oran(j["t3"], j[z]) for z in ("bg", "s1", "s2", "gr-bg"))
    kontrol(f"{ad}: soluk yazı tüm zeminlerde ≥ 4,5 ({en:.2f})", en >= 4.5)
    kontrol(f"{ad}: ana düğme yazısı dolguda ≥ 4,5 ({oran('#ffffff', j['ac-dolgu']):.2f})", oran("#ffffff", j["ac-dolgu"]) >= 4.5)
kontrol(f"açık: uyarı yüzeyde ve kendi zemininde ≥ 4,5 ({min(oran(acik['wa'], acik['s1']), oran(acik['wa'], acik['wa-bg'])):.2f})", min(oran(acik["wa"], acik["s1"]), oran(acik["wa"], acik["wa-bg"])) >= 4.5)
C = oku("content.js"); i = C.index(".w{font:"); wa, wk = jetonlar(C[i:C.index("@media", i)]), jetonlar(C[C.index("@media (prefers-color-scheme:dark){.w{", i):C.index(".pill{", i)])
kontrol("Teams şeridi açık renkleri renk.css'le aynı", all(acik[k] == v for k, v in wa.items() if k in acik) and len(wa) >= 7)
kontrol("Teams şeridi koyu renkleri renk.css'le aynı", all(koyu[k] == v for k, v in wk.items() if k in koyu) and len(wk) >= 7)
kontrol("pano renk.css'i gömer", "/*__RENK__*/" in oku("pano/pano.html") and 'replace("/*__RENK__*/", pano_dosyasi("renk.css"))' in oku("relay.py"))
kontrol("eklenti penceresi ve sihirbaz bağlar", 'href="pano/renk.css"' in oku("popup.html") and 'href="/pano/renk.css"' in oku("sihirbaz/index.html") and '"/pano/renk.css"' in oku("kurulum.py"))
kopya = [p for p in ("pano/pano.html", "popup.html", "sihirbaz/sihirbaz.css") if re.search(r"--(t3|soluk|tx|murekkep)\s*:\s*#", oku(p))]
kontrol(f"başka dosyada renk tanımı kopyası yok ({kopya or '—'})", not kopya)
# v0.99.3: yazı boyu ve köşe yarıçapı da renk.css'te (az basamak); pano, hazırlık ve eklenti penceresinde sabit px kalmasın. Başlık yazısı (font:300 …,
# marka yazı tipi) ve yazdırılan PDF sayfası (pano.html'de window.open'la yazılan ayrı belge) sayılmaz. Hareket azaltma tüm yüzeylerde.
olcu = jetonlar(R[:R.index("@media")])
kontrol("renk.css'te beş yazı boyu ve üç köşe + tam yuvarlak", all(f"yz-{i}" in olcu for i in range(1, 6)) and all(k in olcu for k in ("kose-s", "kose", "kose-l", "kose-tam")))
def sabit(p):
    x = []
    for i, l in enumerate(oku(p).split("\n")):
        if p == "pano/pano.html" and "w.document.write(" in l: continue  # yazdırılan PDF sayfası
        x += [f"{p}:{i + 1} {m}" for m in re.findall(r"font-size:\s*[0-9.]+px|font:\s*[0-9.]+px|border-radius:\s*(?:[1-9][0-9.]*px|var\(--r\))", l)]
    return x
sx = [y for p in ("pano/pano.html", "popup.html") for y in sabit(p)]
kontrol(f"pano, hazırlık ve eklenti penceresinde sabit yazı boyu/köşe yok ({sx[:3] or '—'})", not sx)
# 21 Ekim: Teams şeridi (content.js gölge DOM + kart penceresi) ve kurulum sihirbazı da aynı ölçekte; şerit renk.css'i yükleyemez, değerleri kendisi taşır
sx = [y for p in ("content.js", "sihirbaz/sihirbaz.css") for y in sabit(p)]
kontrol(f"Teams şeridi ve sihirbazda sabit yazı boyu/köşe yok ({sx[:3] or '—'})", not sx)
ct = jetonlar(C[C.index(":host,:root{"):C.index("}", C.index(":host,:root{"))])
kontrol("Teams şeridinin yazı boyu ve köşe ölçeği renk.css'le aynı", ct and all(olcu.get(k) == v for k, v in ct.items()) and set(ct) == {k for k in olcu if k.startswith(("yz-", "kose"))})
kontrol("hareket azaltma: renk.css tüm animasyon ve geçişleri kısaltır, Teams kart penceresi de", re.search(r"prefers-reduced-motion:reduce\)\{\*,\*::before,\*::after\{animation-duration", R) is not None
        and "@media (prefers-reduced-motion:reduce){*{animation:none!important" in C)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
