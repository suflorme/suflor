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
# v0.194.1: şerit Bugün belirteçlerini (--b-*) taşır; eski adlar pano.html'deki eşlemeyle aynı karşılığa bakar. Toast (Teams sayfasında, değişken yok) TON tablosundaki değerler de --b-*'den.
C = oku("content.js"); i = C.index(".w{font:"); wa, wk = jetonlar(C[i:C.index("@media", i)]), jetonlar(C[C.index("@media (prefers-color-scheme:dark){.w{", i):C.index(".pill{", i)])
ESLE = {"s1": "b-yuzey", "s2": "b-yuzey2", "tx": "b-murekkep", "t2": "b-m2", "t3": "b-m3", "bd": "b-cizgi", "bd2": "b-cizgi2", "hov": "b-uzerinde", "ac": "b-vurgu", "ac-yazi": "b-ana-yazi", "dikkat": "b-gec"}
def serit_ayni(j, w): return set(w) == set(ESLE) and all(j[ESLE[k]].strip().lower() == v.strip().lower() for k, v in w.items())
kontrol("Teams şeridi açık renkleri renk.css'in Bugün belirteçleriyle aynı", serit_ayni(acik, wa))
kontrol("Teams şeridi koyu renkleri renk.css'in Bugün belirteçleriyle aynı", serit_ayni(koyu, wk))
ton = dict(re.findall(r'(dikkat|vurgu|notr): \["(#[0-9A-Fa-f]{6})", "(#[0-9A-Fa-f]{6})"\]', C[C.index("const TON = "):C.index("const TON_ESKI")]) and re.findall(r'(dikkat|vurgu|notr): \["(#[0-9A-Fa-f]{6})", "(#[0-9A-Fa-f]{6})"\]', C)) if False else {m[0]: (m[1], m[2]) for m in re.findall(r'(dikkat|vurgu|notr): \["(#[0-9A-Fa-f]{6})", "(#[0-9A-Fa-f]{6})"\]', C)}
kontrol("Teams toast tonları renk.css'le aynı (dikkat=geç, vurgu=vurgu, nötr=m3; açık/koyu)", ton == {"dikkat": (acik["b-gec"], koyu["b-gec"]), "vurgu": (acik["b-vurgu"], koyu["b-vurgu"]), "notr": (acik["b-m3"], koyu["b-m3"])})
kontrol("eklenti penceresi eski adları Bugün belirteçlerine bağlar (pano.html ile aynı eşleme)", "--bg:var(--b-zemin);--s1:var(--b-yuzey)" in oku("popup.html") and "--dikkat:var(--b-gec)" in oku("popup.html"))
kontrol("Teams şeridi ve eklenti penceresinde eski palet ya da sarı/pirinç dolgu kalmadı", not re.search(r"#(18201c|646c66|b0832e|8a6420|c0503b|1f7a4f|171d1a|e8ebe6)\b", "\n".join(l for l in C.split("\n") if "TON_ESKI = " not in l), re.I) and not re.search(r"#(c9973a|fff)\b", oku("popup.html")[oku("popup.html").index("<style>"):oku("popup.html").index("</style>")], re.I))  # logo SVG'deki pirinç sayılmaz
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
sx = [y for p in ("pano/pano.html", "pano/bugun.css", "popup.html") for y in sabit(p)]
kontrol(f"pano, hazırlık ve eklenti penceresinde sabit yazı boyu/köşe yok ({sx[:3] or '—'})", not sx)
# 21 Ekim: Teams şeridi (content.js gölge DOM + kart penceresi) ve kurulum sihirbazı da aynı ölçekte; şerit renk.css'i yükleyemez, değerleri kendisi taşır
sx = [y for p in ("content.js", "sihirbaz/sihirbaz.css") for y in sabit(p)]
kontrol(f"Teams şeridi ve sihirbazda sabit yazı boyu/köşe yok ({sx[:3] or '—'})", not sx)
ct = jetonlar(C[C.index(":host,:root{"):C.index("}", C.index(":host,:root{"))])
kontrol("Teams şeridinin yazı boyu ve köşe ölçeği renk.css'le aynı", ct and all(olcu.get(k) == v for k, v in ct.items()) and set(ct) == {k for k in olcu if k.startswith(("yz-", "kose"))})
kontrol("hareket azaltma: renk.css tüm animasyon ve geçişleri kısaltır, Teams kart penceresi de", re.search(r"prefers-reduced-motion:reduce\)\{\*,\*::before,\*::after\{animation-duration", R) is not None
        and "@media (prefers-reduced-motion:reduce){*{animation:none!important" in C)
# 6 Kasım (pano tasarım sistemi, adım 1): tek yazı ölçeği 12·13·15·18·24·40, boşluk 4·8·12·16·24·32·48, köşe 6·8·14·tam — pano/yazi.css'te; pano.html ve bugun.css yalnız bunları kullanır
# (renk.css'teki eski --yz-1..5/--kose-* adları eklenti penceresi, Teams şeridi ve hazırlık için durur). Düğme/etiket/bağlantı bileşenleri bugun.css'te.
Y = oku("pano/yazi.css"); yt = jetonlar(Y[:Y.index("/* Bugün sayfası ölçüleri")])
kontrol("yazi.css: altı yazı boyu, yedi boşluk, dört köşe belirteci (tek ölçek)", {k: yt.get(k) for k in ("yz-12", "yz-13", "yz-15", "yz-18", "yz-24", "yz-40")} == {"yz-12": "12px", "yz-13": "13px", "yz-15": "15px", "yz-18": "18px", "yz-24": "24px", "yz-40": "40px"}
        and [yt.get(f"bo-{n}") for n in (4, 8, 12, 16, 24, 32, 48)] == [f"{n}px" for n in (4, 8, 12, 16, 24, 32, 48)] and [yt.get(k) for k in ("r-6", "r-8", "r-14", "r-tam")] == ["6px", "8px", "14px", "999px"])
PANO = {p: "\n".join(l for l in oku(p).split("\n") if "w.document.write(" not in l) for p in ("pano/pano.html", "pano/bugun.css")}  # yazdırılan PDF sayfası ayrı belge
ESKI = re.compile(r"var\(--(?:yz-[1-5]|b-yz-[a-z-]+|b-k-[a-z]+)\)")
kontrol("pano.html ve bugun.css eski yazı/köşe adlarını (--yz-1..5, --b-yz-*, --b-k-*) kullanmaz", not [p for p, t in PANO.items() if ESKI.search(t)])
def olcek_disi(t):
    x = []
    for m in re.finditer(r"font-size:\s*([^;}\"'`]+)", t): x.append(m.group(1).strip())
    for m in re.finditer(r"(?<![\w-])font:\s*([^;}\"'`]*)", t):
        z = re.search(r"(?:^|\s)([0-9.]+px|var\(--yz-[0-9]+\))(?:/|\s|$)", m.group(1).strip() + " ")
        if z: x.append(z.group(1))
    return [v for v in x if v not in ("inherit",) and not re.fullmatch(r"var\(--yz-(12|13|15|18|24|40)\)", v)]
sx = {p: olcek_disi(t) for p, t in PANO.items()}
kontrol(f"pano.html ve bugun.css yazı boyu yalnız ölçekte (12·13·15·18·24·40) ({[v for l in sx.values() for v in l][:3] or '—'})", not any(sx.values()))
kr = [m for t in PANO.values() for m in re.findall(r"border-radius:\s*(?:[1-9][0-9.]*px)", t)] + [m for t in PANO.values() for m in re.findall(r"var\(--r-(?!6\)|8\)|14\)|tam\))[a-z0-9-]*\)", t)]
kontrol(f"pano.html ve bugun.css köşe yalnız belirteçte (6·8·14·tam) ({kr[:3] or '—'})", not kr)
sp = [m for t in PANO.values() for m in re.findall(r"(?:padding|margin|gap)(?:-[a-z]+)?:\s*[^;}\"'`]*", t) if re.search(r"(?<![-\w(,.])(?:[1-9][0-9]?)px", re.sub(r"(?:calc|max|min|clamp)\([^;}]*\)", "", m)) and not re.search(r"-[0-9]+px", m)]
kontrol(f"pano.html ve bugun.css boşluklarda belirteç dışı pozitif px yok; yalnız büyük yerleşim değerleri ve eksi kenar boşlukları kalır ({sp[:3] or '—'})", len(sp) <= 6)
kontrol("tek düğme bileşeni: .b-ana/.b-iki/.b-sade/.b-k, 36 (küçük 32), 13/500, köşe 8; eski .b/.ana/.sade/.iri, button.pri/.gh/.lnk eşlenir", all(x in PANO["pano/bugun.css"] for x in (".b-ana,.b-iki,.b-sade,#bgn .b,", "height:var(--d-yuk)", "font:500 var(--yz-13)", "border-radius:var(--r-8)", ".b-k{height:var(--d-yuk-k)", "#bgn .b.ana", "#emd .b.sade", "#prd .b.ana"))
        and yt.get("d-yuk") == "36px" and yt.get("d-yuk-k") == "32px" and "button.pri{" in PANO["pano/pano.html"] and "button.gh{" in PANO["pano/pano.html"] and "button.lnk," in PANO["pano/pano.html"])
kontrol("tek durum etiketi: .etiket (12/500, köşe 6, 4×8) ve gec/bekliyor/uyari/notr/olumlu türleri; Onaylanmadı, gecikti, dış kayıt, Monitör nedeni bağlı",
        all(x in PANO["pano/bugun.css"] for x in (".etiket,.chip{", "padding:var(--bo-4) var(--bo-8)", "border-radius:var(--r-6)", ".etiket.gec{", ".etiket.bekliyor,.etiket.uyari{", ".etiket.olumlu{", ".etiket.notr")) and 'class="etiket gec onayis son"' in PANO["pano/pano.html"] and 'class="etiket notr"' in PANO["pano/pano.html"])
kontrol("tek bağlantı biçimi: a ve a:visited vurgu yeşili, alt çizgisiz, hover'da alt çizgi; pano.html'de başka bağlantı rengi/alt çizgisi yok",
        "a,a:link,a:visited{color:var(--b-vurgu);text-decoration:none}a:hover" in PANO["pano/bugun.css"] and not re.search(r"(?<![\w-])a(?:\.[a-z]+)?\s*\{[^}]*(?:#[0-9a-f]{3,6}|blue)", PANO["pano/pano.html"], re.I) and not re.search(r"(?:^|[ ,}])[.#a-z0-9 ]*\ba\{[^}]*text-decoration:underline", PANO["pano/pano.html"]))
kontrol("göreli tarih: tek yardımcı goreliTarih/goreliTam/goreliSpan; bnVadeEt, kisaGun, gunTxt, arTarih ona bağlı", all(x in PANO["pano/pano.html"] for x in ("function goreliTarih(t,vadeli)", "function goreliTam(t)", "const goreliSpan=", "function kisaGun(at){return goreliTarih(at)}", "return goreliTarih(d)+' '+sa", "return goreliSpan(x.vade,x.gecikti?'etiket gec':'vade',true)")))
kontrol("işaretlenemeyen satırda (Monitör, dış kayıt, açık soru) boş yuvarlak gizli", ".kaynakn,#bgn .onay.soru{display:none}" in PANO["pano/bugun.css"])
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
