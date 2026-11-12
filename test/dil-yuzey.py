#!/usr/bin/env python3
# İngilizce kipte Türkçe kalan yüzeylerin taraması (13 Kasım: beta kullanıcısı arayüzü İngilizce kurdu, menü ve ifadeler Türkçe göründü).
# test/dil.py L("…") çağrılarını denetler; bu test onun görmediği yerlere bakar:
#   1. menü çubuğu uygulaması (menu-cubugu.swift): T("…") metinlerinin, menü/araç çubuğu/Ayarlar sekmesi listelerindeki adların EN_METIN'de
#      karşılığı var; uyar(), toolTip, accessibilityDescription, bildirim gövdesi gibi kullanıcıya giden yerlerde çıplak Türkçe metin yok
#      (T(…) ya da TE(tr, en) ile sarılı); dil /cards yoklamasından da gelir (açılışta /status tek denemeydi)
#   2. aktarıcı: /cards yanıtları (düz ve uzun yoklama) arayuz_dili taşır
#   3. pano.html durağan işaretleme: metin düğümleri ve title/placeholder/aria-label pano/dil.js'te anahtar olarak var (cevir() tam eşleşme arar);
#      yardım penceresi (iki dilli div'ler) ve marka adları hariç
#   4. kurulum sihirbazı: tr ve en blokları aynı anahtarlara sahip
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dil-yuzey.py      (kaldı → çıkış 1)
import json, os, re, sys

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oku = lambda y: open(os.path.join(KOD, y), encoding="utf-8").read()
hatalar = []
TRK = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
STR = r'"(?:[^"\\]|\\.)*"'

# dil.js
en = {}
for satir in oku("pano/dil.js").splitlines():
    m = re.match(rf"\s*({STR})\s*:\s*({STR}),?\s*$", satir)
    if m: en[json.loads(m.group(1))] = json.loads(m.group(2))

# 1. menu-cubugu.swift
sw = oku("menu-cubugu.swift")
i, j = sw.index("let EN_METIN"), sw.index("func T(_ s")
blok = sw[i:j]
anahtar = set(re.findall(r'"((?:[^"\\]|\\.)*)"\s*:', blok))
kod_satirlari = [(n, l) for n, l in enumerate(sw.splitlines(), 1) if not l.lstrip().startswith("//")]
ilk, son = sw[:i].count("\n") + 1, sw[:j].count("\n") + 1  # sözlüğün kendisi taranmaz

for n, l in kod_satirlari:
    if ilk <= n <= son: continue
    # T("sabit") metinleri sözlükte olmalı
    for m in re.finditer(r'\bT\("((?:[^"\\]|\\.)*)"\)', l):
        if m.group(1) not in anahtar: hatalar.append(f"menu-cubugu.swift:{n}: EN_METIN'de yok — T(\"{m.group(1)}\")")
    # kullanıcıya giden yerde çıplak Türkçe metin
    for m in re.finditer(r'(?:\buyar\(|\.toolTip = |accessibilityDescription: |govde: |\.messageText = |\.subtitle = |\.body = )"((?:[^"\\]|\\.)*)"', l):
        if TRK.search(m.group(1)): hatalar.append(f"menu-cubugu.swift:{n}: çıplak Türkçe (T/TE ile sar) — {m.group(1)[:70]}")
    m = re.search(r'\?\? "((?:[^"\\]|\\.)*)"\)', l)  # uyar(v["err"] as? String ?? "…")
    if m and "uyar(" in l and TRK.search(m.group(1)): hatalar.append(f"menu-cubugu.swift:{n}: uyar yedek metni Türkçe — {m.group(1)[:70]}")

SF = re.compile(r"^[a-z0-9.:\-]+$")
def bolge(bas, bit):
    a = sw.index(bas); b = sw.index(bit, a); return sw[:a].count("\n") + 1, sw[a:b]
for ad, (bas, bit) in {"anaMenu": ("func anaMenu()", "\n    @objc func"), "ARACLAR": ("static let ARACLAR", "static let TOPLANTI"), "menuGoster": ("func menuGoster()", "\n    }\n"),
                       "GRUPLAR": ("static let GRUPLAR", "static let EN:"), "MENU_DUGME": ("static let MENU_DUGME", "@objc func menuDugme")}.items():
    n0, metin = bolge(bas, bit)
    metin = re.sub(r"(?m)^\s*//.*$", "", metin)
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', metin):
        t = m.group(1)
        if SF.match(t) or t in ("Suflor.me", "mini", "yan", "kenar", "sohbet", "-", "") or "\\(" in t or len(t) <= 2: continue  # <= 2: kısayol tuşu
        if ad == "MENU_DUGME" and len(t) <= 3: continue  # sayfadaki düğme kimliği
        if t not in anahtar: hatalar.append(f"menu-cubugu.swift ({ad}): EN_METIN'de yok — {t[:70]}")

# T(t) ile dolaylı çağrılan sabit liste (menü ipuçları)
for m in re.finditer(r'for t in \[((?:"[^"]*",?\s*)+)\]', sw):
    for t in re.findall(r'"([^"]*)"', m.group(1)):
        if t not in anahtar: hatalar.append(f"menu-cubugu.swift: EN_METIN'de yok (menü ipucu) — {t}")

isle = sw[sw.index("func isle(_ v:"):][:400]
if 'dilAyarla(v["arayuz_dili"]' not in isle: hatalar.append("menu-cubugu.swift: isle() /cards yanıtından dili almıyor (dilAyarla(v[\"arayuz_dili\"]))")

# 2. relay.py
rl = oku("relay.py")
if rl.count("arayuz_dili=ARAYUZ_DILI") < 1 or 'v["arayuz_dili"] = ARAYUZ_DILI' not in rl: hatalar.append("relay.py: /cards (düz ya da uzun yoklama) arayuz_dili taşımıyor")

# 3. pano.html durağan işaretleme
h = oku("pano/pano.html")
h = re.sub(r"<script.*?</script>", "", h, flags=re.S); h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
h = re.sub(r"<dialog id=yrd>.*?</dialog>", "", h, flags=re.S)  # yardım: <div lang=tr> / <div lang=en> iki dilli
MARKA = {"Suflor.me pano", "Suflor", "me", "Teams", "Meet", "Zoom", "Suflor.me"}
HARF = re.compile(r"[A-Za-zçğıöşüÇĞİÖŞÜ]{2}")
for m in re.finditer(r">([^<>]+)<", h):
    t = m.group(1).strip()
    if t and HARF.search(t) and t not in en and t not in MARKA: hatalar.append(f"pano.html: durağan metin dil.js'te yok — {t[:70]!r}")
for m in re.finditer(r'(?:title|placeholder|aria-label)="([^"]+)"', h):
    t = m.group(1)
    if HARF.search(t) and t not in en and t not in MARKA: hatalar.append(f"pano.html: durağan öznitelik dil.js'te yok — {t[:70]!r}")

# 4. sihirbaz tr/en anahtar eşitliği
s = oku("sihirbaz/sihirbaz.js")
a = s.index("    tr: {"); b = s.index("    en: {"); c = s.index("\n  };", b)
def anahtarlar(x):  # dizge içeriğini atla; yalnız `ad: "` biçimli gerçek anahtarlar
    k, i, d = [], 0, False
    while i < len(x):
        if x[i] == "\\" and d: i += 2; continue
        if x[i] == '"': d = not d
        elif not d:
            m = re.match(r'([a-z_0-9]+):\s*"', x[i:])
            if m and (i == 0 or not x[i - 1].isalnum()): k.append(m.group(1)); i += len(m.group(1))
        i += 1
    return set(k)
ktr, ken = anahtarlar(s[a:b]), anahtarlar(s[b:c])
for k in sorted(ktr - ken): hatalar.append(f"sihirbaz.js: İngilizce bloğunda yok — {k}")
for k in sorted(ken - ktr): hatalar.append(f"sihirbaz.js: Türkçe bloğunda yok — {k}")

print(f"dil-yuzey: {len(anahtar)} menü metni · {len(en)} dil.js metni · {len(hatalar)} sorun")
for x in hatalar: print("  KALDI:", x)
sys.exit(1 if hatalar else 0)
