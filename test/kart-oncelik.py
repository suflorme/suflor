#!/usr/bin/env python3
# Kart önceliği (19 Kasım, tasarım denetimi K1/K2): pano/pano.html ve content.js'teki kartOncelik/kartSirala işlevleri kaynak
# dosyadan çıkarılıp node ile koşulur. Denetlenen: DUR en üstte, sonra karşı tarafın sorusu (süreli onay), sonra senden iş bekleyen
# (onay, Ne diyeyim, Söyle), sonra Cevap, en son Not; aynı öncelikte en yeni (geri gelen kart geri geldiği an) önce; iki yüzey aynı
# sırayı verir. Tarayıcı ve port gerekmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kart-oncelik.py      (kaldı → çıkış 1)
import json, os, re, subprocess, sys

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oku = lambda y: open(os.path.join(KOD, y), encoding="utf-8").read()
ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)

def islevler(metin):
    r = []
    for ad in ("kartOncelik", "kartSirala"):
        m = re.search(r"function " + ad + r"\(.*", metin)
        r.append(m.group(0).strip() if m else "")
    return r

# sentetik kartlar (içerik yok; yalnız tür ve alanlar)
KARTLAR = [
    {"id": "n1", "kind": "not", "at": "2026-11-19T10:00:00"},
    {"id": "c1", "kind": "cevap", "at": "2026-11-19T10:01:00"},
    {"id": "s1", "kind": "soyle", "at": "2026-11-19T10:02:00"},
    {"id": "c2", "kind": "cevap", "at": "2026-11-19T10:03:00"},
    {"id": "o1", "kind": "not", "onay": True, "izin": "kayit", "at": "2026-11-19T10:04:00"},
    {"id": "d1", "kind": "dur", "at": "2026-11-19T10:05:00"},
    {"id": "k1", "kind": "not", "onay": True, "eylem": "x", "izin": "karsi_cevap", "at": "2026-11-19T10:06:00"},
    {"id": "r1", "kind": "soyle", "replik": True, "at": "2026-11-19T10:07:00"},
    {"id": "d2", "kind": "dur", "gizli": True, "at": "2026-11-19T10:00:30"},
    {"id": "c3", "kind": "cevap", "at": "2026-11-19T09:00:00", "geri": "2026-11-19T10:08:00"},
]
BEKLENEN = ["d1", "d2", "k1", "r1", "o1", "s1", "c3", "c2", "c1", "n1"]

sonuc = {}
for yuzey in ("pano/pano.html", "content.js"):
    f = islevler(oku(yuzey))
    kontrol(f"{yuzey}: kartOncelik ve kartSirala tek satırlık işlev olarak var", all(f))
    if not all(f): continue
    js = "\n".join(f) + f"\nconst K={json.dumps(KARTLAR)};process.stdout.write(JSON.stringify({{s:kartSirala(K).map(c=>c.id),p:K.map(kartOncelik),bos:kartSirala(null).length,tek:kartOncelik(undefined)}}))"
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=20)
    if r.returncode: kontrol(f"{yuzey}: node koştu ({r.stderr.strip()[:200]})", False); continue
    sonuc[yuzey] = json.loads(r.stdout)
    s = sonuc[yuzey]["s"]
    kontrol(f"{yuzey}: sıra DUR → karşı tarafın sorusu → iş bekleyen → Cevap → Not ({s})", s == BEKLENEN)
    kontrol(f"{yuzey}: DUR her zaman ilk (gizli DUR da Söyle'den önce)", s[:2] == ["d1", "d2"])
    kontrol(f"{yuzey}: geri gelen Cevap geri geldiği anla sıralanır", s.index("c3") < s.index("c2"))
    kontrol(f"{yuzey}: boş liste ve eksik kart hata vermez", sonuc[yuzey]["bos"] == 0 and sonuc[yuzey]["tek"] == 4)

if len(sonuc) == 2:
    a, b = sonuc.values()
    kontrol("pano ve Teams şeridi aynı öncelik ve sırayı verir", a == b)

# yüzeyler işlevi gerçekten kullanıyor
P, C = oku("pano/pano.html"), oku("content.js")
kontrol("pano cardsHtml sırayı kartSirala'dan alır", "kcl=kartSirala(shKartlar(v,mini))" in P)
kontrol("menü paneli tek kart + sayaç (kdaha), panoda katlı kart (kkat)", "data-kdaha=1" in P and '" kkat"' in P and 'classList.contains("kkat")' in P)
kontrol("Teams şeridi kartSirala + tek kart ve '+N kart' çekmecesi", "kartSirala((v.cards || [])" in C and 'e("div", "dahasi")' in C and 'L("+{n} kart"' in C)
kontrol("Teams şeridi: üç etiketli kısayol + ⋯", 'const ANA_KS = ["konus", "ne", "kanit"]' in C and 'dh.dataset.rdaha = "1"' in C and ".row.ekler button.rb.ek" in C)
kontrol("DUR kartı belirgin (kiremit kenar ve zemin) panoda ve şeritte", ".k-dur{background:color-mix(in srgb,var(--dikkat)" in P and ".k-dur{background:color-mix(in srgb,var(--dikkat)" in C)

print(f"{sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
