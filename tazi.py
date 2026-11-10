#!/usr/bin/env python3
"""Tazı — dış firma ve iş bağlantısı izleme aracı (Suflor.me). Yalnız standart kütüphane, Python 3.9.

Kural toplar, yapay zekâ değerlendirir: `tara` makine kaynaklarını (RDAP, DNS, crt.sh, site, ABR, haber RSS) okur, önceki
taramayla karşılaştırır (v2 dedektif kipi: Wayback arşivi, site taraması, altyapı, GitHub, kayıtlar arası bağlantı haritası);
Claude oturumu (.claude/skills/tazi) haber, LinkedIn ve X'i tamamlar, `ekle` ve `dosya` ile yazar, `rapor` üretir.
Yalnız iş bilgisi: özel hayat, konum, aile, sağlık toplanmaz; kişi puanlanmaz. Bulgu türleri kapalı listedir.
Veri: ~/Library/Application Support/Suflor/tazi/ (ya da TAZI_DIR). Şifre/anahtar dosyaya yazılmaz.
"""
import argparse, datetime, difflib, email.utils, hashlib, ipaddress, json, os, re, shlex, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser

UA = "Suflor-Tazi/1 (+local)"
TURLER = ("alan_adi", "dns", "sertifika", "sicil", "site", "haber", "gonderi", "ortaklik",
          "arsiv", "teknoloji", "baglanti", "kod", "sosyal_hesap", "varlik")
# durum türleri: değişir, kaybolabilir (baglanti her taramada yeniden hesaplanır)
DURUM_TURLER = ("alan_adi", "dns", "sicil", "site", "arsiv", "teknoloji", "sosyal_hesap", "varlik", "baglanti")
OLAY_TURLER = ("sertifika", "haber", "gonderi", "ortaklik", "kod")  # olay türleri: yalnız yeni
HIZLI_KAYNAK = ("rdap", "dns", "tarama", "haber")   # hızlı tarama: Wayback, crt.sh, site içi gezinme, GitHub yok
KAYNAKLAR = ("rdap", "dns", "crt", "tarama", "sicil", "haber", "arsiv", "altyapi", "kod")
KAYNAK_TAKMA = {"site": "tarama"}
BOLUMLER = ("kimlik", "zaman", "iddia", "celiski", "bayrak", "soru", "iz")
PLATFORMLAR = ("linkedin", "x")
AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOGRULAMA_ON = ("google-site-verification", "ms=", "atlassian-domain-verification", "facebook-domain-verification")
ABR_ATLA = "abr.business.gov.au"


# ---------- yardımcılar ----------
def bugun():
    s = os.environ.get("TAZI_BUGUN")
    if s:
        return datetime.datetime.strptime(s, "%Y%m%d").date()
    return datetime.date.today()


def tarih_kisa(iso):
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
        return f"{d.day} {AY[d.month - 1]}"
    except Exception:
        return str(iso)[:10]


def tr_kucuk(s):
    return str(s or "").replace("İ", "i").casefold().replace("ı", "i")


def slug(s):
    t = str(s).translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")).lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "kayit"


def veri_dizin(dizin=None):
    d = dizin or os.environ.get("TAZI_DIR") or os.path.expanduser("~/Library/Application Support/Suflor/tazi")
    os.makedirs(d, mode=0o700, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def yaz_atomik(yol, metin):
    os.makedirs(os.path.dirname(yol), mode=0o700, exist_ok=True)
    t = yol + ".tmp"
    with open(t, "w", encoding="utf-8") as f:
        f.write(metin)
    os.replace(t, yol)


def json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return varsayilan


def anahtar(kayit, tur, alt):
    return hashlib.sha1(f"{kayit}|{tur}|{alt}".encode()).hexdigest()[:16]


def kaynak_alan(k):
    try:
        n = urllib.parse.urlparse(k).netloc
        return n or str(k)
    except Exception:
        return str(k)


def temiz_hata(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}"
    if isinstance(e, urllib.error.URLError):
        return "bağlantı: " + str(e.reason)[:80]
    if isinstance(e, TimeoutError) or "timed out" in str(e):
        return "zaman aşımı"
    return (type(e).__name__ + ": " + str(e))[:100]


HIZLI = {"acik": False, "bitis": 0.0}   # hızlı tarama: kısa zaman aşımı, tek sayfa, toplam süre sınırı
HIZLI_ZAMAN = 8
HIZLI_TOPLAM = 30


def hizli_doldu():
    return HIZLI["acik"] and time.time() > HIZLI["bitis"]


def http_ayrinti(url, zaman=20, ek=None):
    """(metin, başlıklar[küçük harf], içerik türü)."""
    if HIZLI["acik"]:
        zaman = min(zaman, HIZLI_ZAMAN)
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(ek or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=zaman) as r:
        veri = r.read(3_000_000)
        cs = r.headers.get_content_charset() or "utf-8"
        bas = {k.lower(): v for k, v in r.headers.items()}
    return veri.decode(cs, "replace"), bas, bas.get("content-type", "")


def http_al(url, zaman=20, ek=None):
    return http_ayrinti(url, zaman, ek)[0]


_SON_ISTEK = [0.0]


def nazik(url, zaman=20, ek=None):
    """Nazik hız: istekler arası en az TAZI_BEKLE sn (varsayılan 1). (metin, başlıklar, tür)."""
    ara = 0.3 if HIZLI["acik"] else float(os.environ.get("TAZI_BEKLE", "1"))
    gec = time.time() - _SON_ISTEK[0]
    if ara > 0 and gec < ara:
        time.sleep(ara - gec)
    try:
        return http_ayrinti(url, zaman, ek)
    finally:
        _SON_ISTEK[0] = time.time()


# ---------- izleme listesi ----------
def x_norm(u):
    """twitter.com → x.com, www yok, sorgu yok; yalnız profil kökü ya da /status/<no> kalır."""
    p = urllib.parse.urlparse(str(u).strip())
    h = p.netloc.lower().split(":")[0]
    h = h[4:] if h.startswith("www.") else h
    if h not in ("x.com", "twitter.com"):
        return None
    seg = [x for x in p.path.split("/") if x]
    if not seg or not re.fullmatch(r"[A-Za-z0-9_]{1,15}", seg[0]):
        return None
    if len(seg) == 1:
        return f"https://x.com/{seg[0].lower()}"
    if len(seg) == 3 and seg[1] == "status" and seg[2].isdigit():
        return f"https://x.com/{seg[0].lower()}/status/{seg[2]}"
    return None


def _alan_bul(metin):
    out = []
    for m in re.finditer(r"(?<![\w@.-])([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+)(?![\w-])", metin.lower()):
        d = m.group(1)
        if re.search(r"\.[a-z]{2,}$", d) and d != ABR_ATLA and d not in out:
            out.append(d[4:] if d.startswith("www.") else d)
    return out


def _kim_temizle(p):
    p = re.sub(r"\([^)]*\)", " ", p)
    p = re.sub(r",[^,]*$", "", p.strip())
    return re.sub(r"\s+", " ", p).strip(" ,")


def md_liste(metin):
    kayitlar, ust = [], None
    for ln in metin.splitlines():
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        h = [c.strip() for c in ln.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in h if c):
            continue
        if ust is None:
            low = [tr_kucuk(c) for c in h]
            if "kim" in low:
                ust = {"kim": low.index("kim"),
                       "web": low.index("web") if "web" in low else None,
                       "li": next((i for i, c in enumerate(low) if c.startswith("linkedin")), None),
                       "neden": next((i for i, c in enumerate(low) if c.startswith("neden")), None),
                       "x": next((i for i, c in enumerate(low) if c in ("x", "twitter")), None)}
            continue
        g = lambda i: h[i] if i is not None and i < len(h) else ""
        kim, web, li, neden = g(ust["kim"]), g(ust["web"]), g(ust["li"]), g(ust["neden"])
        if not kim:
            continue
        parcalar = [p.strip() for p in kim.split(" · ")]
        ad = _kim_temizle(parcalar[0])
        kisiler = [x for x in (_kim_temizle(p) for p in parcalar[1:]) if x]
        alanlar = [m.lower() for m in re.findall(r"@([\w-]+(?:\.[\w-]+)+)", kim)]
        for par in re.findall(r"\(([^)@]*)\)", parcalar[0]):
            alanlar += _alan_bul(par)
        alanlar += _alan_bul(web)
        abn = ""
        m = re.search(r"ABN[\s:]*((?:\d\s*){11})", web, re.I)
        if m:
            abn = re.sub(r"\D", "", m.group(1))
        lin = re.findall(r"https?://[^\s|)]*linkedin\.com[^\s|)]*", li)
        xl = []
        for u in re.findall(r"https?://(?:www\.)?(?:x|twitter)\.com/[^\s|)]*", " ".join(h)):
            u = x_norm(u)
            if u and u not in xl:
                xl.append(u)
        sira = []
        for a in alanlar:
            if a not in sira:
                sira.append(a)
        kayitlar.append({"id": slug(ad), "ad": ad, "kisiler": kisiler, "alanlar": sira, "abn": abn,
                         "linkedin": lin, "x": xl, "sayfalar": [], "haber_sorgu": [], "neden": neden})
    benzersiz, goruldu = [], {}
    for k in kayitlar:
        n = goruldu.get(k["id"], 0) + 1
        goruldu[k["id"]] = n
        if n > 1:
            k["id"] = f"{k['id'][:36]}-{n}"
        benzersiz.append(k)
    return benzersiz


def ayar_yolu():
    return os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")


def liste_yolu(arg=None, dizin=None):
    if arg:
        return os.path.expanduser(arg)
    a = json_oku(ayar_yolu(), {})
    if isinstance(a, dict) and a.get("tazi_liste"):
        return os.path.expanduser(str(a["tazi_liste"]))
    return os.path.join(veri_dizin(dizin), "liste.json")


def aday_yolu(dizin=None):
    return os.path.join(veri_dizin(dizin), "aday.json")


def aday_oku(dizin=None):
    ham = json_oku(aday_yolu(dizin), [])
    return [a for a in ham if isinstance(a, dict) and a.get("ad")] if isinstance(ham, list) else []


def liste_oku(arg=None, dizin=None):
    """ana izleme listesi (salt okunur) + Suflor'un aday listesi (aday.json; kaynak: suflor-aday)."""
    try:
        ana = _liste_oku(arg, dizin)
    except FileNotFoundError:
        if not aday_oku(dizin):
            raise
        ana = []
    var_id = {k["id"] for k in ana}
    var_ad = {tr_kucuk(k["ad"]) for k in ana}
    for a in aday_oku(dizin):
        if slug(a["ad"]) in var_id or tr_kucuk(a["ad"]) in var_ad:
            continue
        ana.append({"id": slug(a["ad"]), "ad": a["ad"], "kisiler": [], "alanlar": [str(x).lower() for x in (a.get("alanlar") or [])],
                    "abn": "", "linkedin": [], "x": [], "sayfalar": [], "haber_sorgu": [], "neden": a.get("neden") or "",
                    "kaynak": "suflor-aday"})
    return ana


def _liste_oku(arg=None, dizin=None):
    yol = liste_yolu(arg, dizin)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    if metin.lstrip().startswith(("[", "{")):
        ham = json.loads(metin)
        ham = ham.get("kayitlar", []) if isinstance(ham, dict) else ham
        out = []
        for k in ham:
            ad = k.get("ad") or k.get("id") or "kayit"
            out.append({"id": k.get("id") or slug(ad), "ad": ad, "kisiler": list(k.get("kisiler") or []),
                        "alanlar": [str(a).lower() for a in (k.get("alanlar") or [])],
                        "abn": re.sub(r"\D", "", k.get("abn") or ""), "linkedin": list(k.get("linkedin") or []),
                        "x": [u for u in (x_norm(x) for x in (k.get("x") or [])) if u],
                        "sayfalar": list(k.get("sayfalar") or []), "haber_sorgu": list(k.get("haber_sorgu") or []),
                        "neden": k.get("neden") or ""})
        return out
    return md_liste(metin)


def kayit_bul(liste, sorgu):
    q = tr_kucuk(sorgu).strip()
    if not q:
        return None
    for k in liste:
        if tr_kucuk(k["id"]) == q:
            return k
    dom = q.split("@", 1)[1] if "@" in q else q
    for k in liste:
        if any(dom == a or dom.endswith("." + a) for a in k["alanlar"]):
            return k
    if "@" in q or len(q) < 3:
        return None
    for k in liste:
        if q in tr_kucuk(k["ad"]) or any(q in tr_kucuk(p) for p in k["kisiler"]):
            return k
    return None


# ---------- toplayıcılar ----------
class Fact:
    def __init__(self, tur, alt, deger, etiket, kid, derece, kaynak="", tarih=None, ozet=None, **ek):
        self.tur, self.alt, self.deger, self.etiket, self.kid = tur, alt, deger, etiket, kid
        self.derece, self.kaynak, self.tarih, self.ek = derece, kaynak, tarih, ek
        self.ozet = ozet or (f"{etiket}: {deger}" if deger not in (None, "") else etiket)


class Ctx:
    def __init__(self, k, bugun_, dizin, onceki_site, rows=None):
        self.k, self.bugun, self.dizin, self.onceki_site = k, bugun_, dizin, onceki_site
        self.facts, self.durum, self.site = [], {}, {}
        self.rows = rows if rows is not None else {}
        self.gorulen = set()      # (tur, alt): aynı olgu iki kez eklenmez
        self.sosyal = []          # bu taramada keşfedilen (platform, kimlik)
        self.baglar = {}          # alan adı → taramada görülen same-domain adresler

    def ekle(self, f):
        a = (f.tur, f.alt)
        if a not in self.gorulen:
            self.gorulen.add(a)
            self.facts.append(f)


def rdap_taban(ctx):
    yol = os.path.join(ctx.dizin, "iana-rdap.json")
    try:
        if time.time() - os.path.getmtime(yol) < 7 * 86400:
            return json_oku(yol, None) or None
    except OSError:
        pass
    url = os.environ.get("TAZI_IANA", "https://data.iana.org/rdap/dns.json")
    veri = json.loads(http_al(url))
    yaz_atomik(yol, json.dumps(veri))
    return veri


def rdap(ctx):
    taban = None
    for d in ctx.k["alanlar"]:
        kid = f"rdap:{d}"
        try:
            if taban is None:
                taban = rdap_taban(ctx)
            tld = d.rsplit(".", 1)[-1]
            url = None
            for hizmet in taban.get("services", []):
                if tld in [t.lower() for t in hizmet[0]]:
                    url = hizmet[1][0]
                    break
            if not url:
                raise RuntimeError(f"RDAP desteklenmiyor (.{tld})")
            if not url.endswith("/"):
                url += "/"
            v = json.loads(http_al(url + "domain/" + d, ek={"Accept": "application/rdap+json"}))
            ev = {e.get("eventAction"): str(e.get("eventDate", ""))[:10] for e in v.get("events", [])}
            kur = ""
            for e in v.get("entities", []):
                if "registrar" in e.get("roles", []):
                    for it in (e.get("vcardArray") or [None, []])[1]:
                        if it and it[0] == "fn":
                            kur = it[3]
                    kur = kur or e.get("handle", "")
            ns = sorted({n.get("ldhName", "").lower().rstrip(".") for n in v.get("nameservers", []) if n.get("ldhName")})
            alanlar = [("kayit_tarihi", "kayıt tarihi", ev.get("registration", "")),
                       ("bitis_tarihi", "bitiş tarihi", ev.get("expiration", "")),
                       ("son_degisiklik", "son değişiklik", ev.get("last changed", "")),
                       ("kayit_kurulusu", "kayıt kuruluşu", kur),
                       ("ad_sunuculari", "ad sunucuları", ", ".join(ns)),
                       ("durum", "durum", ", ".join(sorted(v.get("status", []))))]
            for alt, et, dg in alanlar:
                if dg:
                    ek = {"k": "ns_kumesi", "v": dg} if alt == "ad_sunuculari" else {}
                    ctx.facts.append(Fact("alan_adi", f"{d}:{alt}", dg, f"alan adı {d} {et}", kid, "A", url + "domain/" + d, **ek))
            ctx.durum[kid] = "ok"
        except Exception as e:
            ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


def dig_calistir(t, d):
    kom = shlex.split(os.environ.get("TAZI_DIG") or "dig") + ["+short", t, d]
    p = subprocess.run(kom, capture_output=True, text=True, timeout=HIZLI_ZAMAN if HIZLI["acik"] else 20)
    if p.returncode != 0:
        raise RuntimeError(f"dig çıkış {p.returncode}")
    return [l.strip() for l in p.stdout.splitlines() if l.strip()]


def dns(ctx):
    for d in ctx.k["alanlar"]:
        for t in ("NS", "MX", "A", "TXT"):
            kid = f"dns:{d}:{t.lower()}"
            try:
                sat = dig_calistir(t, d)
                if t != "TXT":
                    for s in sorted({x.lower().rstrip(".") for x in sat}):
                        ek = {"k": "ip", "v": s} if t == "A" else {}
                        ctx.facts.append(Fact("dns", f"{d}:{t.lower()}:{s}", s, f"DNS {t} {d}", kid, "A", f"dns:{d}", **ek))
                else:
                    diger = 0
                    for s in sat:
                        s = re.sub(r'"\s*"', "", s).strip('"')
                        if s.lower().startswith("v=spf1"):
                            ctx.facts.append(Fact("dns", f"{d}:txt:spf", s[:200], f"DNS TXT (SPF) {d}", kid, "A", f"dns:{d}"))
                        elif s.lower().startswith(DOGRULAMA_ON):
                            on = re.split(r"[=:]", s, 1)[0].lower()
                            ctx.facts.append(Fact("dns", f"{d}:txt:{on}", on, f"DNS TXT doğrulama kaydı {d}", kid, "A", f"dns:{d}",
                                                  ozet=f"DNS TXT doğrulama kaydı {d}: {on}"))
                        else:
                            diger += 1
                    if diger:
                        ctx.facts.append(Fact("dns", f"{d}:txt:diger", str(diger), f"DNS TXT diğer kayıt sayısı {d}", kid, "A", f"dns:{d}"))
                ctx.durum[kid] = "ok"
            except Exception as e:
                ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


def crt(ctx):
    taban = os.environ.get("TAZI_CRTSH", "https://crt.sh/")
    for d in ctx.k["alanlar"]:
        kid = f"crt:{d}"
        try:
            v = json.loads(http_al(f"{taban}?q=%25.{d}&output=json", 60) or "[]")
            ilk = {}
            for s in v:
                tb = str(s.get("not_before", ""))[:10]
                for n in str(s.get("name_value", "")).split("\n"):
                    n = n.strip().lower()
                    if n.startswith("*."):
                        n = n[2:]
                    if n and (n not in ilk or (tb and tb < ilk[n])):
                        ilk[n] = tb
            for n in sorted(ilk)[:300]:
                ctx.facts.append(Fact("sertifika", n, ilk[n], f"sertifika adı {n}", kid, "A", f"crt.sh:{d}", tarih=ilk[n] or None,
                                      ozet=f"yeni sertifika adı: {n} (ilk kayıt {ilk[n] or '?'})"))
            ctx.durum[kid] = "ok"
        except Exception as e:
            ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


class _Metin(HTMLParser):
    BLOK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header", "footer", "table"}

    def __init__(self):
        super().__init__()
        self.atla, self.parca, self.baslik, self.t = 0, [], "", False

    def handle_starttag(self, tag, a):
        if tag in ("script", "style", "noscript"):
            self.atla += 1
        elif tag == "title":
            self.t = True
        if tag in self.BLOK:
            self.parca.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.atla:
            self.atla -= 1
        elif tag == "title":
            self.t = False
        if tag in self.BLOK:
            self.parca.append("\n")

    def handle_data(self, d):
        if self.t:
            self.baslik += d
        if not self.atla:
            self.parca.append(d)


def sayfa_metni(html):
    p = _Metin()
    p.feed(html)
    satirlar = [re.sub(r"\s+", " ", s).strip() for s in "".join(p.parca).split("\n")]
    metin = "\n".join(s for s in satirlar if s)
    metin = re.sub(r"[\w.+-]+\x40([\w-]+(?:\.[\w-]+)+)", lambda m: "…" + chr(64) + m.group(1), metin)  # yerel kısım saklanmaz
    return metin[:20000], re.sub(r"\s+", " ", p.baslik).strip()


def site_adres(u):
    o = os.environ.get("TAZI_HTTPS_OVERRIDE")
    if not o:
        return u
    pu = urllib.parse.urlparse(u)
    return o.rstrip("/") + "/" + pu.netloc + (pu.path or "/") + (("?" + pu.query) if pu.query else "")


def fark(eski, yeni):
    a, b = eski.splitlines(), yeni.splitlines()
    ek, sil, ay = [], [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            sil += a[i1:i2]
        if op in ("replace", "insert"):
            ek += b[j1:j2]
    ay = ["+ " + s[:200] for s in ek[:5]] + ["− " + s[:200] for s in sil[:3]]
    return len(ek), len(sil), ay[:8]


EPOSTA_RX = re.compile(r"[\w.+-]+\x40([\w-]+(?:\.[\w-]+)+)")
SERBEST_POSTA = ("gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "me.com",
                 "proton.me", "protonmail.com", "aol.com", "msn.com")
ONCELIK = ("about", "team", "people", "leadership", "founder", "careers", "jobs", "privacy", "terms", "legal", "contact",
           "partner", "client", "customer", "case", "pricing", "product", "solution", "blog", "news", "press", "security",
           "trust", "investor")
ADRES_SAYFA = ("contact", "legal", "privacy", "terms", "imprint", "iletisim", "about")
GIZLILIK_ANAHTAR = ("privacy", "terms", "legal", "gizlilik", "kvkk", "sartlar")
SABIT_UZANTI = re.compile(r"\.(?:pdf|jpe?g|png|gif|svg|webp|ico|css|js|zip|mp4|mp3|woff2?|ttf|xml|json|docx?|xlsx?|pptx?|rss)$", re.I)
SIRKET_RX = re.compile(r"\b[A-ZÇĞİÖŞÜ][\w&'.\- ]{1,60}\s(?:Pty\.?\s?Ltd\.?|Limited|Ltd\.?|Inc\.?|LLC|GmbH|A\.?Ş\.?)")
KIMLIK_RX = re.compile(r"\b(ABN|ACN)\b[\s:.#-]*((?:\d\s?){9,11})")
ANALITIK_RX = ((r"UA-\d{4,}-\d+", None), (r"\bG-[A-Z0-9]{6,}\b", None), (r"GTM-[A-Z0-9]{4,}", None), (r"\bAW-\d{6,}", None),
               (r"fbq\(\s*['\"]init['\"]\s*,\s*['\"]?(\d+)", 1), (r"hjid\s*:\s*(\d+)", 1),
               (r"_linkedin_partner_id\s*=\s*[\"'](\d+)", 1), (r"clarity\.ms/tag/([a-z0-9]{6,})", 1),
               (r"[\"']clarity[\"']\s*,\s*[\"']script[\"']\s*,\s*[\"']([a-z0-9]{6,})", 1))
ADRES_RX = (re.compile(r"\b\d{1,5}\s+[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+){0,3}\s(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)\b[^\n]{0,50}"),
            re.compile(r"[^\n]{0,30}\b(?:Mah\.|Mahallesi|Sok\.|Sokak|Cad\.|Caddesi)[^\n]{0,60}"))
SOSYAL_X_ATLA = {"intent", "share", "home", "i", "search", "hashtag", "settings", "login", "signup", "explore", "tos", "privacy",
                 "about", "widgets.js", "messages", "notifications", "compose", "sharer"}
SOSYAL_GH_ATLA = {"features", "topics", "sponsors", "login", "join", "about", "pricing", "orgs", "marketplace", "enterprise",
                  "readme", "site", "contact", "security", "settings", "apps", "collections", "trending", "login.php"}


class _Ham(HTMLParser):
    def __init__(self):
        super().__init__()
        self.a, self.kaynak, self.uretici = [], [], ""

    def handle_starttag(self, tag, at):
        a = {k.lower(): (v or "") for k, v in at}
        if tag == "a" and a.get("href"):
            self.a.append(a["href"])
        elif tag in ("script", "iframe") and a.get("src"):
            self.kaynak.append(a["src"])
        elif tag == "link" and a.get("href"):
            self.kaynak.append(a["href"])
        elif tag == "meta" and a.get("name", "").lower() == "generator":
            self.uretici = a.get("content", "")[:80]


def alan_esles(host, d):
    host = host.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    return host == d or host.endswith("." + d)


def sosyal_coz(href):
    """(platform, kimlik, adres) ya da None. Paylaş/intent bağlantıları atlanır."""
    try:
        p = urllib.parse.urlparse(href)
    except ValueError:
        return None
    h = p.netloc.lower().split(":")[0]
    h = h[4:] if h.startswith("www.") else h
    seg = [x for x in p.path.split("/") if x]
    if h in ("x.com", "twitter.com") and seg and re.fullmatch(r"[A-Za-z0-9_]{1,15}", seg[0]) and seg[0].lower() not in SOSYAL_X_ATLA:
        return ("x", seg[0].lower(), f"https://x.com/{seg[0]}")
    if h.endswith("linkedin.com") and len(seg) >= 2 and seg[0] in ("company", "in", "school"):
        return ("linkedin", f"{seg[0]}/{seg[1].lower()}", f"https://www.linkedin.com/{seg[0]}/{seg[1]}")
    if h == "github.com" and seg and seg[0].lower() not in SOSYAL_GH_ATLA:
        return ("github", seg[0].lower(), f"https://github.com/{seg[0]}")
    if h in ("youtube.com", "m.youtube.com"):
        if seg and seg[0].startswith("@"):
            return ("youtube", seg[0].lower(), f"https://www.youtube.com/{seg[0]}")
        if len(seg) >= 2 and seg[0] in ("channel", "c", "user"):
            return ("youtube", seg[1].lower(), f"https://www.youtube.com/{seg[0]}/{seg[1]}")
    if h in ("facebook.com", "fb.com", "m.facebook.com") and seg and seg[0].lower() not in (
            "sharer", "sharer.php", "share.php", "tr", "dialog", "plugins", "login", "policies", "help", "groups"):
        return ("facebook", seg[0].lower(), f"https://www.facebook.com/{seg[0]}")
    if h == "instagram.com" and seg and seg[0] not in ("p", "reel", "reels", "explore", "accounts", "stories", "tv"):
        return ("instagram", seg[0].lower(), f"https://www.instagram.com/{seg[0]}")
    if h == "medium.com" and seg and seg[0].startswith("@"):
        return ("medium", seg[0].lower(), f"https://medium.com/{seg[0]}")
    if h.endswith(".medium.com") and h.split(".")[0] not in ("www", "help", "policy", "blog"):
        return ("medium", h.split(".")[0], f"https://{h}")
    if h.endswith(".substack.com") and h.split(".")[0] not in ("www", "support", "on"):
        return ("substack", h.split(".")[0], f"https://{h}")
    return None


def tuzel_adlari(metin):
    out = []
    for m in SIRKET_RX.finditer(metin):
        tok = m.group(0).split()
        tut = []
        for t in reversed(tok):
            if t[:1].isupper() or t[:1].isdigit() or t in ("&", "of", "and"):
                tut.append(t)
            else:
                break
        ad = " ".join(reversed(tut)).strip(" .,-")
        if len(tut) >= 2 and ad not in out:
            out.append(ad)
    return out


def ad_norm(ad):
    a = tr_kucuk(ad)
    for _ in range(3):
        a = re.sub(r"[\s.,]+(pty\s*ltd|ltd|inc|llc|limited|gmbh|a\s*ş|pty|co)$", "", a.strip())
    return re.sub(r"[^a-z0-9]+", "", a.translate(str.maketrans("çğöşü", "cgosu")))


def robots_yasak(metin):
    yol, grup_bizim = [], False
    for ln in metin.splitlines():
        ln = ln.split("#")[0].strip()
        if ":" not in ln:
            continue
        a, v = [x.strip() for x in ln.split(":", 1)]
        a = a.lower()
        if a == "user-agent":
            grup_bizim = v == "*" or "tazi" in v.lower()
        elif a == "disallow" and grup_bizim and v:
            yol.append(v)
    return yol


def yasak_mi(yol, yasaklar):
    for y in yasaklar:
        rx = "^" + re.escape(y).replace(r"\*", ".*").replace(r"\$", "$")
        if re.match(rx, yol):
            return True
    return False


def sayfa_norm(u, d):
    p = urllib.parse.urlparse(u)
    if p.scheme not in ("http", "https") or not alan_esles(p.netloc, d):
        return None
    yol = re.sub(r"/{2,}", "/", p.path or "/")
    if SABIT_UZANTI.search(yol):
        return None
    return f"https://{d}{yol}"


def sayfa_puani(u):
    y = urllib.parse.urlparse(u).path.lower()
    return 1 if any(a in y for a in ONCELIK) else 0


def _tarama_cikar(ctx, d, u, html, metin, ust_basliklar):
    kid = f"tarama:{d}"
    ham = _Ham()
    try:
        ham.feed(html)
    except Exception:
        pass
    # sosyal hesaplar
    for href in ham.a:
        c = sosyal_coz(urllib.parse.urljoin(u, href))
        if c:
            plat, kim, adres = c
            ctx.sosyal.append((plat, kim))
            ctx.ekle(Fact("sosyal_hesap", f"{plat}:{kim}", adres, f"sosyal hesap ({plat})", kid, "C", u,
                          ozet=f"sosyal hesap ({plat}): {kim}", k="sosyal", v=f"{plat}/{kim}", plat=plat, handle=kim))
    # analitik / etiket kimlikleri
    for rx, g in ANALITIK_RX:
        for m in re.finditer(rx, html):
            kim = m.group(g or 0)
            ctx.ekle(Fact("teknoloji", f"{d}:analitik:{kim}", kim, f"analitik kimliği {kim}", kid, "C", u,
                          ozet=f"analitik kimliği {kim} ({d})", k="analitik", v=kim))
    # üçüncü taraf kaynaklar
    for src in ham.kaynak:
        try:
            pu = urllib.parse.urlparse(urllib.parse.urljoin(u, src))
        except ValueError:
            continue
        host = pu.netloc.lower().split(":")[0]
        if pu.scheme in ("http", "https") and host and not alan_esles(host, d):
            ctx.ekle(Fact("teknoloji", f"{d}:host:{host}", host, f"üçüncü taraf kaynak {host}", kid, "C", u,
                          ozet=f"üçüncü taraf kaynak: {host} ({d})", k="ucuncu_host", v=host, grup="üçüncü taraf kaynak"))
    if ham.uretici:
        ctx.ekle(Fact("teknoloji", f"{d}:generator", ham.uretici, f"site oluşturucu {d}", kid, "C", u,
                      ozet=f"site oluşturucu ({d}): {ham.uretici}"))
    for bas, ad in (("server", "sunucu yazılımı"), ("x-powered-by", "çalışma ortamı")):
        if ust_basliklar.get(bas):
            ctx.ekle(Fact("teknoloji", f"{d}:{bas}", ust_basliklar[bas][:80], f"{ad} {d}", kid, "C", u,
                          ozet=f"{ad} ({d}): {ust_basliklar[bas][:80]}"))
    # varlıklar: tüzel ad, ABN/ACN, e-posta alan adı (yerel kısım asla), adres (yalnız iletişim/hukuk sayfası)
    for ad in tuzel_adlari(metin):
        n = ad_norm(ad)
        ctx.ekle(Fact("varlik", f"{d}:tuzel:{n}", ad, f"site tüzel adı {ad}", kid, "C", u,
                      ozet=f"sitede tüzel ad: {ad} ({d})", k="tuzel_ad", v=n, ad=ad))
    for m in KIMLIK_RX.finditer(metin):
        sn = re.sub(r"\D", "", m.group(2))
        if len(sn) == (11 if m.group(1) == "ABN" else 9):
            ctx.ekle(Fact("varlik", f"{d}:{m.group(1).lower()}:{sn}", sn, f"site {m.group(1)} numarası", kid, "C", u,
                          ozet=f"sitede {m.group(1)}: {sn} ({d})", k=m.group(1).lower(), v=sn))
    for m in EPOSTA_RX.finditer(html):
        dom = m.group(1).lower().rstrip(".")
        if not alan_esles(dom, d) and dom not in SERBEST_POSTA and not re.search(r"sentry|wixpress|wix\.com|example\.|domain\.com|sentry\.io", dom) and re.search(r"\.[a-z]{2,}$", dom):
            ctx.ekle(Fact("varlik", f"{d}:eposta:{dom}", dom, f"e-posta alan adı {dom}", kid, "C", u,
                          ozet=f"sitede e-posta alan adı: {dom} ({d})", k="eposta_alani", v=dom))
    if any(a in urllib.parse.urlparse(u).path.lower() for a in ADRES_SAYFA):
        for rx in ADRES_RX:
            m = rx.search(metin)
            if m:
                ad = re.sub(r"\s+", " ", m.group(0)).strip(" ,.")[:90]
                ctx.ekle(Fact("varlik", f"{d}:adres:{slug(ad)}", ad, "şirket adresi", kid, "C", u,
                              ozet=f"sitede şirket adresi ({d}): {ad}", k="adres", v=slug(ad)))
                break
    # bağlantılar (BFS için)
    out = []
    for href in ham.a:
        n = sayfa_norm(urllib.parse.urljoin(u, href.split("#")[0]), d)
        if n and n not in out:
            out.append(n)
    return out


def _alan_tara(ctx, d):
    kid = f"tarama:{d}"
    mx = 1 if HIZLI["acik"] else int(os.environ.get("TAZI_SAYFA_MAX", "25"))
    yasaklar = []
    try:
        yasaklar = robots_yasak(nazik(site_adres(f"https://{d}/robots.txt"))[0])
    except Exception:
        pass
    if yasaklar:
        ctx.ekle(Fact("teknoloji", f"{d}:robots", ", ".join(sorted(yasaklar)), f"robots.txt {d}", kid, "A", f"https://{d}/robots.txt",
                      ozet=f"robots.txt yasak yolları ({d}): " + ", ".join(sorted(yasaklar)[:8])))
    adaylar, sira = [], [0]

    def ekle_aday(u):
        if u and u not in ctx.baglar[d] and not yasak_mi(urllib.parse.urlparse(u).path, yasaklar):
            ctx.baglar[d].append(u)
            adaylar.append((-sayfa_puani(u), sira[0], u))
            sira[0] += 1
    ctx.baglar[d] = []
    ekle_aday(f"https://{d}/")
    if not HIZLI["acik"] and not yasak_mi("/sitemap.xml", yasaklar):
        try:
            xml = nazik(site_adres(f"https://{d}/sitemap.xml"))[0]
            yollar_ = []
            for m in re.finditer(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
                n = sayfa_norm(m.group(1), d)
                if n and urllib.parse.urlparse(n).path not in yollar_:
                    yollar_.append(urllib.parse.urlparse(n).path)
            if yollar_:
                h = hashlib.sha1("\n".join(sorted(yollar_)).encode()).hexdigest()[:8]
                ctx.ekle(Fact("teknoloji", f"{d}:sitemap", f"{len(yollar_)}:{h}", f"sitemap.xml {d}", kid, "C", f"https://{d}/sitemap.xml",
                              ozet=f"sitemap.xml ({d}): {len(yollar_)} adres (ilk 5: " + ", ".join(yollar_[:5]) + ")"))
                for y in yollar_:
                    ekle_aday(f"https://{d}{y}")
        except Exception:
            pass
    cekilen, ilk_sayfa = 0, True
    while adaylar and cekilen < mx:
        adaylar.sort()
        _, _, u = adaylar.pop(0)
        cekilen += 1
        sk = f"site:{u}"
        try:
            html, ust, tur = nazik(site_adres(u))
            if tur and "html" not in tur.lower():
                continue
            metin, baslik = sayfa_metni(html)
            h = hashlib.sha256(metin.encode()).hexdigest()
            ctx.site[u] = {"metin": metin, "baslik": baslik}
            ctx.ekle(Fact("site", u, h, f"site {kaynak_alan(u)}", sk, "C", u, baslik=baslik,
                          ozet=f"site: {baslik or kaynak_alan(u)}", site_url=u))
            ctx.durum[sk] = "ok"
            for n in _tarama_cikar(ctx, d, u, html, metin, ust if ilk_sayfa else {}):
                ekle_aday(n)
            if ilk_sayfa:
                ctx.durum[kid] = "ok"
            ilk_sayfa = False
        except Exception as e:
            ctx.durum[sk] = "okunamadı: " + temiz_hata(e)
            if ilk_sayfa:
                ctx.durum[kid] = ctx.durum[sk]
                ilk_sayfa = False


def _cozulur(h):
    import socket
    try:
        socket.getaddrinfo(h, 443)
        return True
    except Exception:
        return False


def tarama(ctx):
    for d in ctx.k["alanlar"]:
        # Ana alan adının IP kaydı yok ama www'nin varsa (yalnız www'de yayın yapan site) www taranır
        if not os.environ.get("TAZI_HTTPS_OVERRIDE") and not _cozulur(d) and _cozulur("www." + d):
            ctx.durum[f"tarama:{d}"] = "ok"
            _alan_tara(ctx, "www." + d)
            continue
        _alan_tara(ctx, d)
    for u in ctx.k["sayfalar"]:      # listede açıkça yazılı ek sayfalar: tek okuma
        if u in ctx.site:
            continue
        sk = f"site:{u}"
        try:
            metin, baslik = sayfa_metni(http_al(site_adres(u)))
            ctx.site[u] = {"metin": metin, "baslik": baslik}
            ctx.ekle(Fact("site", u, hashlib.sha256(metin.encode()).hexdigest(), f"site {kaynak_alan(u)}", sk, "C", u,
                          baslik=baslik, ozet=f"site: {baslik or kaynak_alan(u)}", site_url=u))
            ctx.durum[sk] = "ok"
        except Exception as e:
            ctx.durum[sk] = "okunamadı: " + temiz_hata(e)


def _wb(url):
    """Wayback CDX sıkı hız sınırı koyuyor: istek öncesi ~5 sn, 429'da 20 sn bekleyip bir kez daha (TAZI_BEKLE=0 testte beklemez)."""
    olcek = float(os.environ.get("TAZI_BEKLE", "1"))
    time.sleep(5 * olcek)
    try:
        return nazik(url, 60)[0]
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        time.sleep(20 * olcek)
        return nazik(url, 60)[0]


def arsiv(ctx):
    taban = os.environ.get("TAZI_WAYBACK", "https://web.archive.org/cdx/search/cdx")
    for i, d in enumerate(ctx.k["alanlar"]):
        kid = f"arsiv:{d}"
        try:
            kaynak = f"{taban}?url={d}"
            v = json.loads(_wb(f"{taban}?url={urllib.parse.quote(d)}&output=json&limit=1&fl=timestamp") or "[]")
            if len(v) > 1:
                ts = v[1][0]
                t = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                ctx.ekle(Fact("arsiv", f"{d}:ilk", t, f"ilk arşiv kaydı {d}", kid, "B", kaynak,
                              ozet=f"ilk arşiv kaydı ({d}): {t}"))
            v = json.loads(_wb(f"{taban}?url={urllib.parse.quote(d + '/*')}&output=json&fl=timestamp,original,statuscode"
                              f"&collapse=urlkey&limit=300") or "[]")
            ilkgor = {}
            for r in v[1:]:
                try:
                    ts, orj, kod_ = r[0], r[1], r[2] if len(r) > 2 else "200"
                except IndexError:
                    continue
                if kod_ not in ("200", "-"):
                    continue
                y = re.sub(r"/{2,}", "/", urllib.parse.urlparse(orj).path or "/").rstrip("/") or "/"
                if y == "/" or SABIT_UZANTI.search(y):
                    continue
                t = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                if y not in ilkgor or t < ilkgor[y]:
                    ilkgor[y] = t
            ctx.ekle(Fact("arsiv", f"{d}:url_sayisi", str(len(ilkgor)), f"arşivdeki sayfa sayısı {d}", kid, "B", kaynak,
                          ozet=f"arşivde {len(ilkgor)} sayfa görülmüş ({d})"))
            for y in sorted(ilkgor)[:150]:
                ctx.ekle(Fact("arsiv", f"{d}:yol:{y}", ilkgor[y], f"arşivde görülen sayfa {y}", kid, "B", kaynak,
                              ozet=f"arşivde görülen sayfa: {y} (ilk {ilkgor[y]})", k="arsiv_yol", v=y, grup="arşivde görülen sayfa"))
            ctx.durum[kid] = "ok"
        except Exception as e:
            ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


MX_SAGLAYICI = (("aspmx", "Google Workspace"), ("google.com", "Google Workspace"), ("googlemail.com", "Google Workspace"),
                ("protection.outlook.com", "Microsoft 365"), ("outlook.com", "Microsoft 365"), ("zoho", "Zoho Mail"),
                ("mimecast", "Mimecast"), ("pphosted", "Proofpoint"), ("proofpoint", "Proofpoint"),
                ("messagingengine", "Fastmail"), ("mailgun", "Mailgun"), ("secureserver.net", "GoDaddy"),
                ("icloud.com", "iCloud"), ("protonmail", "Proton Mail"), ("yandex", "Yandex"), ("barracuda", "Barracuda"),
                ("mx.cloudflare.net", "Cloudflare E-posta"), ("registrar-servers.com", "Namecheap"))
SPF_SATICI = (("_spf.google.com", "Google Workspace"), ("spf.protection.outlook.com", "Microsoft 365"), ("sendgrid.net", "SendGrid"),
              ("mailgun.org", "Mailgun"), ("amazonses.com", "Amazon SES"), ("mktomail", "Marketo"), ("hubspot", "HubSpot"),
              ("salesforce", "Salesforce"), ("zendesk", "Zendesk"), ("mandrillapp", "Mailchimp Transactional"),
              ("servers.mcsv.net", "Mailchimp"), ("sparkpostmail", "SparkPost"), ("postmarkapp", "Postmark"), ("zoho", "Zoho"))


def ip_taban(ctx):
    yol = os.path.join(ctx.dizin, "iana-ip.json")
    try:
        if time.time() - os.path.getmtime(yol) < 7 * 86400:
            return json_oku(yol, None) or None
    except OSError:
        pass
    veri = json.loads(http_al(os.environ.get("TAZI_IANA_IP", "https://data.iana.org/rdap/ipv4.json")))
    yaz_atomik(yol, json.dumps(veri))
    return veri


def ip_rdap(ctx, ip, taban):
    a = ipaddress.ip_address(ip)
    for h in taban.get("services", []):
        if any(a in ipaddress.ip_network(c, strict=False) for c in h[0] if ":" not in c):
            url = h[1][0].rstrip("/") + "/ip/" + ip
            v = json.loads(http_al(url, ek={"Accept": "application/rdap+json"}))
            org = ""
            for e in v.get("entities", []):
                for it in (e.get("vcardArray") or [None, []])[1]:
                    if it and it[0] == "fn":
                        org = org or it[3]
                org = org or e.get("handle", "")
            return v.get("name", ""), org, v.get("country", ""), url
    raise RuntimeError("IP aralığı bulunamadı")


def altyapi(ctx):
    taban_ip = None
    for d in ctx.k["alanlar"]:
        kid = f"altyapi:{d}"
        hatalar, kaynak = [], f"dns:{d}"
        try:
            for s in dig_calistir("TXT", "_dmarc." + d):
                s = re.sub(r'"\s*"', "", s).strip('"')
                if s.lower().startswith("v=dmarc1"):
                    m = re.search(r"\bp=(\w+)", s)
                    if m:
                        ctx.ekle(Fact("teknoloji", f"{d}:dmarc:p", m.group(1), f"DMARC politikası {d}", kid, "A", kaynak,
                                      ozet=f"DMARC politikası ({d}): p={m.group(1)}"))
                    for dom in sorted({x.lower().rstrip(".") for x in re.findall(r"mailto:[^;,\s]*?\x40([^;,\s!]+)", s)}):
                        ctx.ekle(Fact("teknoloji", f"{d}:dmarc:rapor:{dom}", dom, f"DMARC rapor alıcısı {dom}", kid, "A", kaynak,
                                      ozet=f"DMARC rapor alıcısı alan adı ({d}): {dom}", k="dmarc_rapor", v=dom))
                    break
            else:
                ctx.ekle(Fact("teknoloji", f"{d}:dmarc:yok", "yok", f"DMARC kaydı {d}", kid, "A", kaynak,
                              ozet=f"DMARC kaydı yok ({d})"))
        except Exception as e:
            hatalar.append(temiz_hata(e))
        try:
            saglayicilar = set()
            for s in dig_calistir("MX", d):
                host = s.split()[-1].lower().rstrip(".")
                for ek_, ad in MX_SAGLAYICI:
                    if ek_ in host:
                        saglayicilar.add(ad)
                        break
            for ad in sorted(saglayicilar):
                ctx.ekle(Fact("teknoloji", f"{d}:eposta:{ad}", ad, f"e-posta sağlayıcısı {d}", kid, "A", kaynak,
                              ozet=f"e-posta sağlayıcısı ({d}): {ad}"))
        except Exception as e:
            hatalar.append(temiz_hata(e))
        try:
            for s in dig_calistir("TXT", d):
                s = re.sub(r'"\s*"', "", s).strip('"')
                if s.lower().startswith("v=spf1"):
                    for h in sorted({x.lower().rstrip(".") for x in re.findall(r"(?:include|redirect)[:=]([^\s]+)", s, re.I)}):
                        ad = next((a for e_, a in SPF_SATICI if e_ in h), "")
                        ctx.ekle(Fact("teknoloji", f"{d}:spf:{h}", h, f"SPF yetkili gönderici {h}", kid, "A", kaynak,
                                      ozet=f"SPF ile yetkili gönderici ({d}): {h}" + (f" — {ad}" if ad else ""), k="spf", v=h))
        except Exception as e:
            hatalar.append(temiz_hata(e))
        try:
            ipler = [x for x in dig_calistir("A", d) if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", x)][:3]
            for ip in ipler:
                a = ipaddress.ip_address(ip)
                if a.is_loopback or a.is_link_local or a.is_multicast or any(
                        a in ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
                    continue
                try:
                    if taban_ip is None:
                        taban_ip = ip_taban(ctx)
                    ad, org, ulke, url = ip_rdap(ctx, ip, taban_ip)
                    ozet_ = "; ".join(x for x in (ad, org, ulke) if x)
                    if not any(f.alt == f"{d}:ag:{slug(ad or ozet_)}" for f in ctx.facts):
                        ctx.ekle(Fact("teknoloji", f"{d}:ag:{slug(ad or ozet_)}", ozet_, f"barındırma ağı {d}", kid, "A", url,
                                      ozet=f"barındırma ağı ({d}): {ozet_}"))
                except Exception as e:
                    hatalar.append("IP RDAP " + temiz_hata(e))
        except Exception as e:
            hatalar.append(temiz_hata(e))
        ctx.durum[kid] = "ok" if not hatalar else "okunamadı: " + hatalar[0]


def kod(ctx):
    orgler = {kim for plat, kim in ctx.sosyal if plat == "github"}
    for r in ctx.rows.values():
        if r["kayit"] == ctx.k["id"] and r["tur"] == "sosyal_hesap" and r.get("plat") == "github" and r["durum"] != "kayip":
            orgler.add(r.get("handle", ""))
    taban = os.environ.get("TAZI_GITHUB", "https://api.github.com").rstrip("/")
    hd = {"Accept": "application/vnd.github+json"}
    for org in sorted(o for o in orgler if o)[:3]:
        kid = f"kod:{org}"
        try:
            try:
                o, tip = json.loads(http_al(f"{taban}/orgs/{org}", ek=hd)), "orgs"
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                o, tip = json.loads(http_al(f"{taban}/users/{org}", ek=hd)), "users"
            repos = json.loads(http_al(f"{taban}/{tip}/{org}/repos?per_page=30&sort=updated", ek=hd))
            ku = str(o.get("created_at", ""))[:10]
            ctx.ekle(Fact("kod", f"{org}:org", ku, f"GitHub {org}", kid, "A", f"https://github.com/{org}", tarih=ku or None,
                          ozet=f"GitHub {org}: {o.get('public_repos', '?')} açık depo, kuruluş {ku or '?'}", org_tarih=ku))
            for rp in repos[:30]:
                ad, pu, cr = rp.get("name", ""), str(rp.get("pushed_at", ""))[:10], str(rp.get("created_at", ""))[:10]
                if ad:
                    ctx.ekle(Fact("kod", f"{org}/{ad}@{pu}", pu, f"GitHub deposu {org}/{ad}", kid, "A", f"https://github.com/{org}/{ad}",
                                  tarih=pu or None, ozet=f"yeni/güncellenen depo {org}/{ad} (oluşturuldu {cr or '?'}, son push {pu or '?'})"))
            ctx.durum[kid] = "ok"
        except Exception as e:
            ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


def abr_guid():
    kom = shlex.split(os.environ.get("TAZI_SECURITY_CMD") or "security") + ["find-generic-password", "-s", "suflor-abr-guid", "-w"]
    try:
        p = subprocess.run(kom, capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None
    except Exception:
        return None


class _Satir(HTMLParser):
    def __init__(self):
        super().__init__()
        self.s, self.atla = [], 0

    def handle_starttag(self, tag, a):
        if tag in ("script", "style"):
            self.atla += 1
        self.s.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.atla:
            self.atla -= 1
        self.s.append("\n")

    def handle_data(self, d):
        if not self.atla:
            self.s.append(d)


def abr_sayfa(html):
    p = _Satir()
    p.feed(html)
    sat = [re.sub(r"\s+", " ", x).strip() for x in "".join(p.s).split("\n")]
    sat = [x for x in sat if x]
    etk = {"Entity name:": "entity_name", "ABN status:": "abn_durumu", "Entity type:": "entity_turu",
           "Goods & Services Tax (GST):": "gst", "Main business location:": "konum", "Business name(s):": "is_adlari",
           "ASIC registration:": "acn", "ACN:": "acn"}
    out, i = {}, 0
    while i < len(sat):
        a = etk.get(sat[i])
        if a:
            j, vals = i + 1, []
            while j < len(sat) and sat[j] not in etk and not sat[j].endswith(":") and len(vals) < (10 if a == "is_adlari" else 1):
                vals.append(sat[j])
                j += 1
            if vals:
                out[a] = "; ".join(sorted(vals)) if a == "is_adlari" else vals[0]
            i = j
        else:
            i += 1
    if "konum" in out:  # yalnız eyalet ve posta kodu
        m = re.search(r"\b([A-Z]{2,3})\s+(\d{4})\b", out["konum"])
        out["konum"] = f"{m.group(1)} {m.group(2)}" if m else out["konum"][:20]
    return out


def sicil(ctx):
    abn = ctx.k["abn"]
    if not abn:
        return
    kid = "sicil"
    taban = os.environ.get("TAZI_ABR", "https://abr.business.gov.au/")
    guid = abr_guid()
    try:
        if guid:
            ham = http_al(f"{taban}json/AbnDetails.aspx?abn={abn}&guid={urllib.parse.quote(guid)}")
            m = re.search(r"\((\{.*\})\)\s*;?\s*$", ham, re.S)
            j = json.loads(m.group(1) if m else ham)
            bn = j.get("BusinessName") or []
            v = {"entity_name": j.get("EntityName", ""), "abn_durumu": (j.get("AbnStatus", "") + " " + j.get("AbnStatusEffectiveFrom", "")).strip(),
                 "entity_turu": j.get("EntityTypeName", ""), "gst": j.get("Gst") or "",
                 "konum": f"{j.get('AddressState', '')} {j.get('AddressPostcode', '')}".strip(),
                 "is_adlari": "; ".join(sorted(bn if isinstance(bn, list) else [bn])), "acn": j.get("Acn", "")}
            kaynak = taban + "json/AbnDetails.aspx"
        else:
            v = abr_sayfa(http_al(f"{taban}ABN/View?abn={abn}"))
            kaynak = f"{taban}ABN/View?abn={abn}"
        if not v.get("entity_name") and not v.get("abn_durumu"):
            raise RuntimeError("sayfa ayrıştırılamadı")
        et = {"entity_name": "tüzel ad", "abn_durumu": "ABN durumu", "entity_turu": "tüzel türü", "gst": "GST",
              "konum": "ana iş yeri (eyalet, posta kodu)", "is_adlari": "iş adları", "acn": "ACN"}
        for a, dg in v.items():
            if dg:
                ctx.facts.append(Fact("sicil", f"abn:{a}", dg, f"sicil {et[a]}", kid, "A", kaynak))
        ctx.durum[kid] = "ok"
    except Exception as e:
        ctx.durum[kid] = "okunamadı: " + (temiz_hata(e).replace(guid, "***") if guid else temiz_hata(e))


SIRKET_EK = re.compile(r"\s+(pty\.?\s*ltd\.?|ltd\.?|inc\.?|llc|limited|pty|co\.?)\s*$", re.I)


def kisa_ad(ad):
    while True:
        y = SIRKET_EK.sub("", ad).strip()
        if y == ad:
            return y
        ad = y


def haber(ctx):
    k = ctx.k
    taban = os.environ.get("TAZI_NEWS", "https://news.google.com/rss/search")
    kisa = kisa_ad(k["ad"])
    sorgular = [(s.strip('"'), "firma") for s in k["haber_sorgu"]] or \
               [(kisa, "firma")] + [(p, "kisi") for p in k["kisiler"]]
    tek_kelime = len(kisa.split()) == 1
    alan_izi = [a for a in k["alanlar"]] + [a.split(".")[0] for a in k["alanlar"]]
    bulunan = {}
    kid = "haber"
    hata = None
    for q, tur in sorgular:
        try:
            xml = http_al(f"{taban}?q={urllib.parse.quote_plus(chr(34) + q + chr(34))}&hl=en-AU&gl=AU&ceid=AU:en")
            for it in ET.fromstring(xml).iter("item"):
                bas = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                aciklama = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")
                try:
                    tr = email.utils.parsedate_to_datetime(it.findtext("pubDate")).date()
                except Exception:
                    continue
                yas = (ctx.bugun - tr).days
                if yas > 30 or yas < -1:
                    continue
                govde = tr_kucuk(bas + " " + aciklama)
                if tr_kucuk(q) not in govde:
                    continue
                kay = (it.findtext("source") or "").strip()
                e = bulunan.setdefault(link or bas, {"bas": bas, "link": link, "tr": tr, "yas": yas, "kay": kay, "kisi": False, "govde": govde})
                if tur == "kisi":
                    e["kisi"] = True
        except Exception as ex:
            hata = temiz_hata(ex)
    for e in sorted(bulunan.values(), key=lambda x: x["tr"], reverse=True)[:8]:
        derece, ek = "B", ""
        if tek_kelime and not e["kisi"] and not any(a and a in e["govde"] for a in alan_izi):
            derece, ek = "D", " (ad benzerliği, doğrulanmadı)"
        ctx.facts.append(Fact("haber", e["link"] or e["bas"], e["tr"].isoformat(), "haber", kid, derece, e["link"],
                              tarih=e["tr"].isoformat(), ozet=e["bas"][:240] + (f" — {e['kay']}" if e["kay"] else "") + ek, yas=e["yas"]))
    ctx.durum[kid] = ("okunamadı: " + hata) if hata and not bulunan else "ok"


KOLEKTOR = {"rdap": rdap, "dns": dns, "crt": crt, "tarama": tarama, "sicil": sicil, "haber": haber,
            "arsiv": arsiv, "altyapi": altyapi, "kod": kod}


# ---------- veri dosyaları ----------
def yollar(dizin):
    return {"bulgular": os.path.join(dizin, "bulgular.jsonl"), "son": os.path.join(dizin, "son.json"),
            "sayac": os.path.join(dizin, "linkedin-sayac.json")}


def bulgu_oku(dizin):
    rows = {}
    try:
        with open(yollar(dizin)["bulgular"], encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    rows[r["anahtar"]] = r
    except FileNotFoundError:
        pass
    return rows


def bulgu_yaz(dizin, rows):
    yaz_atomik(yollar(dizin)["bulgular"], "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()))


def onceki_tarama(dizin, kid, bug):
    """(tarih, anlık görüntü) — bugünden önceki en yeni; yoksa bugünkü (aynı gün yeniden tarama)."""
    kok = os.path.join(dizin, "tarama")
    gunler = sorted(d for d in os.listdir(kok) if re.fullmatch(r"\d{8}", d)) if os.path.isdir(kok) else []
    dun = [g for g in gunler if g < bug and os.path.exists(os.path.join(kok, g, kid + ".json"))]
    sec = dun[-1] if dun else (bug if bug in gunler and os.path.exists(os.path.join(kok, bug, kid + ".json")) else None)
    return (sec, json_oku(os.path.join(kok, sec, kid + ".json"), {})) if sec else (None, {})


def birlestir(k, ctx, rows, ilk, bug):
    iso = ctx.bugun.isoformat()
    simdiki = set()
    def kok(kid):  # sayfa başına kaynak kimliği (site:<url>) alan adı düzeyinde sayılır: sitede yeni sayfa = yeni bulgu
        kid = str(kid or "")
        return "site:" + urllib.parse.urlparse(kid[5:]).netloc if kid.startswith("site:") else kid
    onceki_kid = {kok(r.get("kid")) for r in rows.values() if r["kayit"] == k["id"]}  # bu kayıtta daha önce okunmuş kaynaklar
    for f in ctx.facts:
        a = anahtar(k["id"], f.tur, f.alt)
        simdiki.add(a)
        r = rows.get(a)
        durum_tur = f.tur in DURUM_TURLER
        ek = dict(f.ek)
        ek.pop("yas", None)
        ek.pop("site_url", None)
        if r is None:
            if (ilk or kok(f.kid) not in onceki_kid) and f.tur != "baglanti" and (durum_tur or f.tur in ("sertifika", "kod") or (f.tur == "haber" and f.ek.get("yas", 99) > 14)):
                d = "taban"
            else:
                d = "yeni"
            r = {"anahtar": a, "kayit": k["id"], "tur": f.tur, "alt": f.alt, "deger": f.deger, "onceki": None, "ozet": f.ozet,
                 "kaynak": f.kaynak, "tarih": f.tarih or iso, "derece": f.derece, "ilk_gorulme": iso, "son_gorulme": iso,
                 "durum": d, "tarama": bug, "kid": f.kid, "etiket": f.etiket}
            r.update(ek)
            if f.tur == "site" and d == "yeni" and not ilk:
                r["ozet"], r["grup"] = f"yeni sayfa izleniyor: {f.alt}", "yeni izlenen sayfa"
            rows[a] = r
            continue
        r["son_gorulme"] = iso
        if durum_tur and r["deger"] != f.deger:
            r["onceki"], r["deger"], r["durum"], r["tarama"], r["tarih"] = r["deger"], f.deger, "degisti", bug, iso
            r["ozet"], r["derece"] = f.ozet, f.derece
            r.update(ek)
            if f.tur == "site":
                eski = ctx.onceki_site.get(f.alt, {}).get("metin")
                if eski is not None:
                    e, s, ay = fark(eski, ctx.site[f.alt]["metin"])
                    r["ozet"], r["ayrinti"] = f"site metni değişti: +{e}/−{s} satır", ay
                else:
                    r["ozet"] = "site metni değişti"
        elif durum_tur and r["durum"] == "kayip":
            r["durum"], r["tarama"], r["tarih"] = "yeni", bug, iso
    for a, r in rows.items():  # artık görünmüyor: yalnız kaynağı bu taramada okunduysa
        if (r["kayit"] == k["id"] and r["tur"] in DURUM_TURLER and a not in simdiki and r["durum"] != "kayip"
                and ctx.durum.get(r.get("kid")) == "ok"):
            r["durum"], r["tarama"], r["tarih"] = "kayip", bug, iso


def kaynak_coz(metin):
    sec = []
    for x in (y.strip() for y in metin.split(",") if y.strip()):
        x = KAYNAK_TAKMA.get(x, x)
        if x not in sec:
            sec.append(x)
    return sec


def tara_cmd(a):
    dizin = veri_dizin()
    tum = liste_oku(a.liste)
    liste = tum
    if a.kim:
        k = kayit_bul(tum, a.kim)
        if not k:
            print("eşleşme yok: " + a.kim)
            return 1
        liste = [k]
    hizli = bool(getattr(a, "hizli", False))
    if hizli:
        HIZLI.update(acik=True, bitis=time.time() + HIZLI_TOPLAM)
    sec = kaynak_coz(a.kaynak) if a.kaynak else (list(HIZLI_KAYNAK) if hizli else list(KAYNAKLAR))
    bad = [s for s in sec if s not in KAYNAKLAR]
    if bad:
        print("bilinmeyen kaynak: " + ",".join(bad))
        return 1
    sec = [s for s in KAYNAKLAR if s in sec]      # kod, tarama'dan sonra çalışsın
    b = bugun()
    bug = b.strftime("%Y%m%d")
    rows = bulgu_oku(dizin)
    son = json_oku(yollar(dizin)["son"], {"kayitlar": {}})
    son.setdefault("kayitlar", {})
    ctxs = {}
    for k in liste:
        onc_t, onc = onceki_tarama(dizin, k["id"], bug)
        ilk = onc_t is None
        ctx = Ctx(k, b, dizin, onc.get("site", {}), rows)
        for s in sec:
            if hizli_doldu():
                ctx.durum[s] = "okunamadı: hızlı tarama süresi doldu"
                continue
            try:
                KOLEKTOR[s](ctx)
            except Exception as e:
                ctx.durum[s] = "okunamadı: " + temiz_hata(e)
        birlestir(k, ctx, rows, ilk, bug)
        ctxs[k["id"]] = ctx
        yaz_atomik(os.path.join(dizin, "tarama", bug, k["id"] + ".json"), json.dumps(
            {"kayit": k["id"], "tarih": b.isoformat(), "kaynaklar": sec, "durum": ctx.durum, "site": ({**onc.get("site", {}), **ctx.site} if hizli else ctx.site),
             "olgular": [{"tur": f.tur, "alt": f.alt, "deger": f.deger, "kid": f.kid} for f in ctx.facts]}, ensure_ascii=False))
    bag = baglanti_uret(tum, rows, b, ctxs)           # ağ yok; tüm listeden yeniden hesaplanır
    for k in tum:
        c2 = Ctx(k, b, dizin, {}, rows)
        c2.facts, c2.durum = bag.get(k["id"], []), {"baglanti": "ok"}
        birlestir(k, c2, rows, False, bug)
    for k in liste:
        ctx = ctxs[k["id"]]
        bu = [r for r in rows.values() if r["kayit"] == k["id"] and r["tarama"] == bug and r["tur"] != "baglanti"]
        nb = sum(1 for r in rows.values() if r["kayit"] == k["id"] and r["tur"] == "baglanti" and r["durum"] != "kayip")
        okunmayan = [f"{kk}: {v}" for kk, v in ctx.durum.items() if v != "ok"]
        say = lambda d: sum(1 for r in bu if r["durum"] == d)
        son["kayitlar"][k["id"]] = {"ad": k["ad"], "tarih": b.isoformat(), "yeni": say("yeni"), "degisti": say("degisti"),
                                    "kayip": say("kayip"), "taban": say("taban"), "baglanti": nb, "okunamayan": okunmayan}
        print(f"{k['ad']}: {say('yeni')} yeni, {say('degisti')} değişti, {say('kayip')} artık görünmüyor, "
              f"{say('taban')} taban, {nb} bağlantı/bayrak, {len(okunmayan)} okunamadı")
    son["tarama"] = bug
    bulgu_yaz(dizin, rows)
    yaz_atomik(yollar(dizin)["son"], json.dumps(son, ensure_ascii=False, indent=1))
    print(f"tarama {bug} bitti: {len(liste)} kayıt")
    return 0


# ---------- bağlantı haritası ve bayraklar (ağ yok; kayıtlardan yeniden hesaplanır) ----------
ORTAK_NS = ("cloudflare.com", "awsdns", "googledomains.com", "domaincontrol.com", "azure-dns", "nsone.net", "ultradns",
            "registrar-servers.com", "dnsmadeeasy", "wixdns.net", "squarespace", "godaddy", "dnsimple")
ORTAK_HOST = ("googleapis", "gstatic", "cloudflare", "jsdelivr", "unpkg", "google-analytics", "googletagmanager", "fonts",
              "cdnjs", "bootstrapcdn", "jquery", "gravatar", "wp.com", "w.org", "youtube", "ytimg", "vimeo", "facebook", "fbcdn",
              "twitter", "twimg", "linkedin", "licdn", "doubleclick", "google.com", "googleusercontent", "fontawesome", "typekit",
              "recaptcha", "hsforms", "stripe", "microsoft", "azureedge", "amazonaws", "akamai", "fastly", "cloudfront",
              "wixstatic", "squarespace", "gtag")
ORTAK_SPF = ("google", "outlook", "microsoft", "sendgrid", "mailgun", "amazonses", "mandrillapp", "mailchimp", "mcsv.net",
             "zoho", "protection.outlook")
BAG_ETIKET = {"ns_kumesi": "ad sunucusu kümesi", "ip": "IP adresi", "analitik": "analitik kimliği", "ucuncu_host": "üçüncü taraf kaynak",
              "eposta_alani": "e-posta alan adı", "tuzel_ad": "tüzel ad", "sosyal": "sosyal hesap", "spf": "SPF gönderici",
              "dmarc_rapor": "DMARC rapor alıcısı"}
BAG_DERECE = {"analitik": "B", "tuzel_ad": "B"}


def _ortak_mi(tur, deger):
    kucuk = str(deger).lower()
    if tur == "ns_kumesi":
        return all(any(o in h for o in ORTAK_NS) for h in re.split(r"[,\s]+", kucuk) if h)
    if tur == "ucuncu_host":
        return any(o in kucuk for o in ORTAK_HOST)
    if tur == "spf":
        return any(o in kucuk for o in ORTAK_SPF)
    return False


def tarih_coz(m):
    """'2026-10-09' ya da '09 Oct 2026' (ABR) → datetime.date; yoksa None."""
    m = str(m or "")
    x = re.search(r"(\d{4})-(\d{2})-(\d{2})", m)
    try:
        if x:
            return datetime.date(int(x.group(1)), int(x.group(2)), int(x.group(3)))
        x = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", m)
        if x:
            ay = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(x.group(2).lower()) + 1
            return datetime.date(int(x.group(3)), ay, int(x.group(1)))
    except ValueError:
        return None
    return None


def baglanti_uret(tum, rows, b, ctxs):
    """{kayıt_id: [Fact]} — kayıtlar arası ortak izler (D; aynı analitik kimliği ya da tüzel ad B) ve kayıt içi bayraklar."""
    kim = {k["id"]: k for k in tum}
    deg = {i: {} for i in kim}       # kayıt → tür → {değer}
    kayit_ks = {i: [] for i in kim}  # (alan, kuruluş, tarih)
    for r in rows.values():
        i = r["kayit"]
        if i not in kim or r["durum"] == "kayip" or r["tur"] == "baglanti":
            continue
        if r.get("k") in BAG_ETIKET and r.get("v"):
            deg[i].setdefault(r["k"], set()).add(str(r["v"]))
    for i in kim:
        al = {}
        for r in rows.values():
            if r["kayit"] == i and r["tur"] == "alan_adi" and r["durum"] != "kayip":
                d, _, alt = r["alt"].partition(":")
                al.setdefault(d, {})[alt] = r["deger"]
        for d, v in al.items():
            if v.get("kayit_kurulusu") and tarih_coz(v.get("kayit_tarihi")):
                kayit_ks[i].append((d, v["kayit_kurulusu"], tarih_coz(v["kayit_tarihi"])))
    cikti = {i: [] for i in kim}

    def yaz(i, j, tur_, deger, derece):
        etk = BAG_ETIKET.get(tur_, tur_)
        cikti[i].append(Fact("baglanti", f"{tur_}:{deger}:{j}", deger, f"ortak {etk}", "baglanti", derece, "",
                             ozet=f"{kim[j]['ad']} ile ortak {etk}: {deger}", diger=j, bk=etk, bv=str(deger)))
    ids = sorted(kim)
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            i, j = ids[x], ids[y]
            for tur_, vi in deg[i].items():
                for v in sorted(vi & deg[j].get(tur_, set())):
                    if _ortak_mi(tur_, v) or (tur_ == "eposta_alani" and v in SERBEST_POSTA):
                        continue
                    yaz(i, j, tur_, v, BAG_DERECE.get(tur_, "D"))
                    yaz(j, i, tur_, v, BAG_DERECE.get(tur_, "D"))
            for d1, k1, t1 in kayit_ks[i]:
                for d2, k2, t2 in kayit_ks[j]:
                    if k1 == k2 and abs((t1 - t2).days) <= 7:
                        v = f"{k1} ({d1} {t1.isoformat()} / {d2} {t2.isoformat()})"
                        cikti[i].append(Fact("baglanti", f"kayit:{d1}:{d2}:{j}", v, "yakın kayıt tarihi", "baglanti", "D", "",
                                             ozet=f"{kim[j]['ad']} ile ortak kayıt kuruluşu ve yakın kayıt tarihi: {v}", diger=j,
                                             bk="kayıt kuruluşu ve yakın tarih", bv=v))
                        cikti[j].append(Fact("baglanti", f"kayit:{d2}:{d1}:{i}", v, "yakın kayıt tarihi", "baglanti", "D", "",
                                             ozet=f"{kim[i]['ad']} ile ortak kayıt kuruluşu ve yakın kayıt tarihi: {v}", diger=i,
                                             bk="kayıt kuruluşu ve yakın tarih", bv=v))
    # kayıt içi bayraklar
    for i, k in kim.items():
        mine = [r for r in rows.values() if r["kayit"] == i and r["durum"] != "kayip"]

        def bayrak(kod_, metin, derece="D"):
            cikti[i].append(Fact("baglanti", f"bayrak:{kod_}", metin, "bayrak", "baglanti", derece, "", ozet="Bayrak: " + metin))
        kayitlar = [(r["alt"].split(":")[0], tarih_coz(r["deger"])) for r in mine if r["tur"] == "alan_adi" and r["alt"].endswith(":kayit_tarihi")]
        kayitlar = [x for x in kayitlar if x[1]]
        for d, t in kayitlar:
            if 0 <= (b - t).days < 90:
                bayrak(f"yeni-alan:{d}", f"alan adı {d} yalnız {(b - t).days} gün önce kaydedilmiş ({t.isoformat()})")
        abn = next((tarih_coz(r["deger"]) for r in mine if r["alt"] == "abn:abn_durumu"), None)
        if abn and kayitlar:
            ilk_d = min(kayitlar, key=lambda x: x[1])
            fark_ = (abn - ilk_d[1]).days
            if fark_ > 60:
                bayrak("abn-genc", f"ABN etkin tarihi ({abn.isoformat()}) alan adı kaydından ({ilk_d[0]} {ilk_d[1].isoformat()}) {fark_} gün sonra (not)")
            elif fark_ < -60:
                bayrak("abn-yasli", f"ABN etkin tarihi ({abn.isoformat()}) alan adı kaydından ({ilk_d[0]} {ilk_d[1].isoformat()}) {-fark_} gün önce (not)")
        abr_ad = next((r["deger"] for r in mine if r["alt"] == "abn:entity_name"), "")
        siteler = [r["v"] for r in mine if r["tur"] == "varlik" and r.get("k") == "tuzel_ad" and r.get("v")]
        if abr_ad and siteler:
            n = ad_norm(abr_ad)
            if n and not any(n == s_ or n in s_ or s_ in n for s_ in siteler if s_):
                ad_s = next((r.get("ad") for r in mine if r.get("k") == "tuzel_ad"), siteler[0])
                bayrak("tuzel-ad", f"sitedeki tüzel ad «{ad_s}» ABR'deki «{abr_ad}» ile uyuşmuyor", "C")
        ctx = ctxs.get(i)
        if ctx is not None:
            for d in k["alanlar"]:
                if f"site:https://{d}/" in ctx.durum and ctx.durum[f"site:https://{d}/"] != "ok":
                    if any(r["tur"] == "sertifika" and r["kaynak"] == f"crt.sh:{d}" for r in mine):
                        bayrak(f"site-yok:{d}", f"{d} sitesi okunamıyor ama sertifika kayıtları var")
                elif ctx.durum.get(f"tarama:{d}") == "ok" and d in ctx.baglar:
                    gor = [urllib.parse.urlparse(u).path.lower() for u in ctx.baglar[d]]
                    if not any(a in y for y in gor for a in GIZLILIK_ANAHTAR):
                        bayrak(f"gizlilik-yok:{d}", f"{d} sitesinde gizlilik/şartlar/hukuk sayfası bulunamadı")
    return cikti


# ---------- sosyal bütçe (LinkedIn, X), ekle, değerlendir ----------
def li_norm(u):
    p = urllib.parse.urlparse(u.strip())
    return (p.netloc.lower().replace("www.", "") + p.path.rstrip("/")).lower()


def hafta_adi():
    y = bugun().isocalendar()
    return f"{y[0]}-W{y[1]:02d}"


def sayac_oku(dizin):
    """Eski biçim {"hafta","n","log"} → {"hafta","linkedin":{n,log},"x":{n,log}}; hafta değişince sıfırlanır."""
    s = json_oku(yollar(dizin)["sayac"], {})
    if not isinstance(s, dict):
        s = {}
    if "n" in s and "linkedin" not in s:
        s = {"hafta": s.get("hafta"), "linkedin": {"n": s.get("n", 0), "log": s.get("log", [])}}
    if s.get("hafta") != hafta_adi():
        s = {"hafta": hafta_adi()}
    for p in PLATFORMLAR:
        s.setdefault(p, {"n": 0, "log": []})
    return s


def sosyal_limit(platform):
    env = os.environ.get("TAZI_LI_LIMIT" if platform == "linkedin" else "TAZI_X_LIMIT")
    if env:
        return int(env)
    a = json_oku(ayar_yolu(), {})
    v = a.get(f"tazi_{platform}_hafta") if isinstance(a, dict) else None
    try:
        return int(v) if v is not None else 15
    except (TypeError, ValueError):
        return 15


def _x_kok(u):
    n = x_norm(u)
    return n.split("/status/")[0] if n else None


def sosyal_izinli_mi(platform, k, dizin, url):
    rows = bulgu_oku(dizin).values()
    kesif = [r for r in rows if r["kayit"] == k["id"] and r["tur"] == "sosyal_hesap" and r.get("plat") == platform and r["durum"] != "kayip"]
    if platform == "linkedin":
        izinli = [li_norm(x) for x in k["linkedin"]] + [li_norm(r["deger"]) for r in kesif]
        n = li_norm(url)
        return any(n == a or n.startswith(a + "/") for a in izinli if a)
    n = x_norm(url)
    if not n:
        return False
    handle = n.split("/")[3].lower()
    izinli = {_x_kok(x).split("/")[3].lower() for x in k.get("x", []) if _x_kok(x)} | {str(r.get("handle", "")).lower() for r in kesif}
    return handle in izinli


def sosyal_cmd(a, platform=None):
    platform = platform or a.platform
    dizin = veri_dizin()
    k = kayit_bul(liste_oku(a.liste), a.kayit_id)
    if not k:
        print("hayır: kayıt yok")
        return 1
    if not sosyal_izinli_mi(platform, k, dizin, a.url):
        print("hayır: adres bu kaydın listesinde ya da keşfedilen hesaplarında yok" if platform == "linkedin" else
              "hayır: adres bu kaydın X hesapları arasında değil (yalnız profil kökü ve /status/<no>)")
        return 1
    s = sayac_oku(dizin)
    lim = sosyal_limit(platform)
    if s[platform]["n"] >= lim:
        print(f"hayır: haftalık {platform} sınırı doldu ({s[platform]['n']}/{lim})")
        return 1
    s[platform]["n"] += 1
    s[platform]["log"].append({"t": int(time.time()), "kayit": k["id"], "url": a.url.split("?")[0]})
    yaz_atomik(yollar(dizin)["sayac"], json.dumps(s, ensure_ascii=False))
    print(f"evet ({s[platform]['n']}/{lim})")
    return 0


def linkedin_cmd(a):
    return sosyal_cmd(a, "linkedin")


def son_tarama_tarihi(dizin, kid=None):
    son = json_oku(yollar(dizin)["son"], {})
    if kid:
        return (son.get("kayitlar", {}).get(kid) or {}).get("tarih")
    t = son.get("tarama")
    return f"{t[:4]}-{t[4:6]}-{t[6:]}" if t else None


def ekle_cmd(a):
    dizin = veri_dizin()
    k = kayit_bul(liste_oku(a.liste), a.kim)
    if not k:
        print("kayıt yok: " + a.kim)
        return 1
    if a.tur not in TURLER:
        print("tür geçersiz; izin verilenler: " + ", ".join(TURLER))
        return 1
    if len(a.ozet) > 300:
        print("özet 300 karakteri aşıyor")
        return 1
    if a.alinti and len(a.alinti.split()) > 15:
        print("alıntı 15 kelimeyi aşıyor")
        return 1
    derece = a.derece or {"gonderi": "C", "haber": "B", "ortaklik": "C", "kod": "A", "arsiv": "B"}.get(a.tur, "C")
    rows = bulgu_oku(dizin)
    b = bugun()
    son = json_oku(yollar(dizin)["son"], {})
    bug = son.get("tarama") or b.strftime("%Y%m%d")
    an = anahtar(k["id"], a.tur, a.kaynak or a.ozet)
    if an in rows:
        rows[an]["son_gorulme"] = b.isoformat()
        bulgu_yaz(dizin, rows)
        print("zaten var")
        return 0
    r = {"anahtar": an, "kayit": k["id"], "tur": a.tur, "alt": a.kaynak or a.ozet[:60], "deger": a.ozet, "onceki": None, "ozet": a.ozet,
         "kaynak": a.kaynak or "", "tarih": a.tarih or b.isoformat(), "derece": derece, "ilk_gorulme": b.isoformat(),
         "son_gorulme": b.isoformat(), "durum": "yeni", "tarama": bug, "kid": "claude"}
    if a.alinti:
        r["alinti"] = a.alinti
    if a.tur == "gonderi":
        r["platform"] = a.platform or "web"
    rows[an] = r
    bulgu_yaz(dizin, rows)
    print("eklendi")
    return 0


def aday_ekle(ad, alan=None, neden="elle", dizin=None):
    """Suflor'un aday listesine ekler (ana listene hiç yazılmaz). Döner: (durum, kayıt): "yeni" | "var"."""
    ad = re.sub(r"\s+", " ", str(ad or "")).strip()[:80]
    if len(ad) < 2:
        return "bos", None
    alan = (str(alan).strip().lower() if alan else "")
    alan = re.sub(r"^https?://", "", alan).split("/")[0].replace("www.", "") if alan else ""
    try:
        mevcut = kayit_bul(liste_oku(None, dizin), alan or ad) or kayit_bul(liste_oku(None, dizin), ad)
    except FileNotFoundError:
        mevcut = None
    if mevcut and (tr_kucuk(mevcut["ad"]) == tr_kucuk(ad) or mevcut["id"] == slug(ad) or (alan and alan in mevcut["alanlar"])):
        return "var", mevcut
    lst = aday_oku(dizin)
    kay = {"ad": ad, "alanlar": [alan] if alan else [], "neden": neden if neden in ("toplanti", "konus", "brifing", "elle") else "elle",
           "tarih": bugun().isoformat()}
    lst.append(kay)
    yaz_atomik(aday_yolu(dizin), json.dumps(lst[-200:], ensure_ascii=False, indent=1))
    return "yeni", kay


def aday_cmd(a):
    d, k = aday_ekle(a.ad, a.alan, a.neden)
    print({"yeni": f"aday eklendi: {a.ad}", "var": f"zaten listede: {k['ad'] if k else a.ad}", "bos": "ad gerekli"}[d])
    return 0 if d != "bos" else 1


def degerlendir_cmd(a):
    dizin = veri_dizin()
    k = kayit_bul(liste_oku(a.liste), a.kim)
    if not k:
        print("kayıt yok: " + a.kim)
        return 1
    if len(a.metin) > 400:
        print("değerlendirme 400 karakteri aşıyor")
        return 1
    bug = json_oku(yollar(dizin)["son"], {}).get("tarama") or bugun().strftime("%Y%m%d")
    yol = os.path.join(dizin, "notlar", bug + ".json")
    n = json_oku(yol, {})
    n[k["id"]] = a.metin
    yaz_atomik(yol, json.dumps(n, ensure_ascii=False))
    print("kaydedildi")
    return 0


# ---------- dosya (Claude'un soruşturma notları) ----------
def dosya_yolu(dizin, kid):
    return os.path.join(dizin, "dosya", kid + ".json")


def dosya_oku(dizin, kid):
    d = json_oku(dosya_yolu(dizin, kid), {})
    return d if isinstance(d, dict) and isinstance(d.get("ogeler"), list) else {"kayit": kid, "ogeler": []}


def dosya_ogeleri(d, bolum, sadece_acik=False):
    return [o for o in d["ogeler"] if o["bolum"] == bolum and (not sadece_acik or o.get("durum") == "acik")]


def dosya_metni(k, d):
    L = [f"Dosya — {k['ad']}"]
    for b in BOLUMLER:
        og = dosya_ogeleri(d, b)
        if not og:
            continue
        L.append(f"[{b}]")
        for o in og:
            ek = (f" ({o['kaynak']})" if o.get("kaynak") else "") + (f" [{o['derece']}]" if o.get("derece") else "")
            dur = "" if o.get("durum") == "acik" else f" — kapandı: {o.get('sonuc') or '-'}"
            L.append(f"  #{o['no']} {o.get('tarih') or o['eklendi']} {o['metin']}{ek}{dur}")
    if len(L) == 1:
        L.append("(boş)")
    return "\n".join(L)


def dosya_cmd(a):
    dizin = veri_dizin()
    k = kayit_bul(liste_oku(a.liste), a.kim)
    if not k:
        print("kayıt yok: " + a.kim)
        return 1
    d = dosya_oku(dizin, k["id"])
    yol = dosya_yolu(dizin, k["id"])
    if a.kapat is not None:
        o = next((x for x in d["ogeler"] if x["no"] == a.kapat), None)
        if not o:
            print(f"öğe yok: #{a.kapat}")
            return 1
        o["durum"], o["sonuc"] = "kapali", (a.sonuc or "")[:400]
        yaz_atomik(yol, json.dumps(d, ensure_ascii=False, indent=1))
        print(f"kapandı: #{a.kapat}")
        return 0
    if a.metin is None and a.bolum is None:
        print(dosya_metni(k, d))
        return 0
    if not a.bolum or not a.metin:
        print("--bolum ve --metin birlikte gerekir")
        return 1
    if len(a.metin) > 400:
        print("metin 400 karakteri aşıyor")
        return 1
    if a.tarih and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.tarih):
        print("tarih YYYY-AA-GG olmalı")
        return 1
    if a.bolum == "kimlik":
        d["ogeler"] = [o for o in d["ogeler"] if o["bolum"] != "kimlik"]     # yalnız en son hüküm kalır
    no = max([o["no"] for o in d["ogeler"]] + [d.get("son_no", 0)]) + 1
    d["son_no"] = no
    d["ogeler"].append({"no": no, "bolum": a.bolum, "metin": a.metin, "kaynak": a.kaynak or "", "derece": a.derece or "C",
                        "tarih": a.tarih or "", "eklendi": bugun().isoformat(), "durum": "acik"})
    yaz_atomik(yol, json.dumps(d, ensure_ascii=False, indent=1))
    print(f"eklendi: #{no} ({a.bolum})")
    return 0


# ---------- rapor ----------
def _bayraklar(mine):
    return [r for r in mine if r["tur"] == "baglanti" and str(r["ozet"]).startswith("Bayrak:") and r["durum"] != "kayip"]


def zaman_cizelgesi(mine, d):
    ol = []
    for r in mine:
        if r["durum"] == "kayip":
            continue
        t = None
        if r["tur"] == "alan_adi" and r["alt"].endswith(":kayit_tarihi"):
            ol.append((str(r["deger"])[:10], f"alan adı {r['alt'].split(':')[0]} kaydedildi"))
        elif r["alt"] == "abn:abn_durumu" and tarih_coz(r["deger"]):
            ol.append((tarih_coz(r["deger"]).isoformat(), "ABN durumu: " + str(r["deger"])[:40]))
        elif r["tur"] == "arsiv" and r["alt"].endswith(":ilk"):
            ol.append((str(r["deger"])[:10], f"{r['alt'].split(':')[0]} ilk arşiv kaydı"))
        elif r["tur"] == "kod" and r["alt"].endswith(":org") and r.get("org_tarih"):
            ol.append((r["org_tarih"], f"GitHub {r['alt'].split(':')[0]} kuruldu"))
        elif r["tur"] == "gonderi":
            ol.append((str(r["tarih"])[:10], "gönderi: " + str(r["ozet"])[:70]))
    ilk_sert = {}
    for r in mine:
        if r["tur"] == "sertifika" and r["durum"] != "kayip" and r.get("tarih"):
            kk = r.get("kaynak", "")
            if kk not in ilk_sert or r["tarih"] < ilk_sert[kk][0]:
                ilk_sert[kk] = (str(r["tarih"])[:10], r["alt"])
    for kk, (t, ad) in ilk_sert.items():
        ol.append((t, f"{kk.replace('crt.sh:', '')} ilk sertifika kaydı ({ad})"))
    for o in dosya_ogeleri(d, "zaman"):
        ol.append(((o.get("tarih") or o["eklendi"])[:10], o["metin"][:90]))
    ol = sorted(set(ol))
    if len(ol) > 12:
        ol = ol[:5] + [("…", f"{len(ol) - 11} olay daha")] + ol[-6:]
    return [f"- {t} — {m}" for t, m in ol]


def dosya_bolumu(mine, d):
    kim = dosya_ogeleri(d, "kimlik")
    L = ["### Dosya", "Kimlik doğrulama: " + (kim[-1]["metin"] if kim else "henüz yazılmadı (dosya --bolum kimlik)")]
    L.append("Zaman çizelgesi:")
    L += zaman_cizelgesi(mine, d) or ["- veri yok"]
    L.append("İddia ve kanıt:")
    ig = [f"- [{o['derece']}] {o['metin']}" + (f" ({o['kaynak']})" if o.get("kaynak") else "") + f" #{o['no']}" for o in dosya_ogeleri(d, "iddia")]
    L += ig[:8] + ([f"- (+{len(ig) - 8} daha)"] if len(ig) > 8 else []) or ["- yok"]
    L.append("Çelişkiler ve bayraklar:")
    cb = [f"- {o['metin']} #{o['no']}" for b in ("celiski", "bayrak") for o in dosya_ogeleri(d, b, True)]
    cb += [f"- {r['ozet']}" for r in _bayraklar(mine)]
    L += cb[:10] + ([f"- (+{len(cb) - 10} daha)"] if len(cb) > 10 else []) or ["- yok"]
    L.append("Açık sorular:")
    L += [f"- #{o['no']} {o['metin']}" for o in dosya_ogeleri(d, "soru", True)][:8] or ["- yok"]
    L.append("Sıradaki izler:")
    L += [f"- #{o['no']} {o['metin']}" for o in dosya_ogeleri(d, "iz", True)][:8] or ["- yok"]
    return L


def yeni_satirlari(yeni, kay):
    gr = {}
    for r in yeni:
        if r.get("grup"):
            gr.setdefault(r["grup"], []).append(r)
    out, gorulen = [], set()
    for r in yeni:
        g = r.get("grup")
        if g and len(gr[g]) > 5:
            if g in gorulen:
                continue
            gorulen.add(g)
            v = gr[g]
            out.append(f"- [Yeni · {v[0]['derece']}] {tarih_kisa(v[0]['tarih'])} — {len(v)} {g} (ilk 5: "
                       + ", ".join(str(x.get('v') or x['deger']) for x in v[:5]) + ")")
            continue
        s = f"- [Yeni · {r['derece']}] {tarih_kisa(r['tarih'])} — {r['ozet']}.{kay(r)}"
        if r.get("alinti"):
            s += f" Alıntı: “{r['alinti']}”"
        out.append(s)
    return out


def baglanti_haritasi(rows, kayit_ids, adlar):
    cift = {}
    for r in rows.values():
        if r["tur"] == "baglanti" and r.get("diger") and r["durum"] != "kayip" and r["kayit"] in kayit_ids:
            a_, b_ = sorted((r["kayit"], r["diger"]))
            cift.setdefault((a_, b_), set()).add((r["bk"], r["bv"], r["derece"]))
    L = ["## Bağlantı haritası", ""]
    if not cift:
        return L + ["Kayıtlar arasında ortak iz bulunmadı.", ""]
    ad = lambda i: adlar.get(i, {"ad": i})["ad"]
    n = 0
    for (a_, b_), v in sorted(cift.items()):
        for bk, bv, dr in sorted(v):
            if n < 30:
                L.append(f"- [{dr}] {ad(a_)} ↔ {ad(b_)}: {bk} — {str(bv)[:90]}")
            n += 1
    if n > 30:
        L.append(f"- (+{n - 30} bağlantı daha)")
    return L + ["Bağlantılar ipucudur (D; analitik kimliği ve tüzel ad B); doğrulanana kadar hüküm değildir.", ""]


def rapor_uret(dizin, liste, bug):
    rows = bulgu_oku(dizin)
    adlar = {k["id"]: k for k in liste}
    kok = os.path.join(dizin, "tarama")
    gunler = sorted(d for d in os.listdir(kok) if re.fullmatch(r"\d{8}", d)) if os.path.isdir(kok) else []
    kayit_ids = sorted(f[:-5] for f in os.listdir(os.path.join(kok, bug)) if f.endswith(".json")) if bug in gunler else []
    notlar = json_oku(os.path.join(dizin, "notlar", bug + ".json"), {})
    tarih = f"{bug[:4]}-{bug[4:6]}-{bug[6:]}"
    ks = set()
    for i in kayit_ids:
        ks.update(KAYNAK_TAKMA.get(x, x) for x in (json_oku(os.path.join(kok, bug, i + ".json"), {}).get("kaynaklar") or []))
    L = [f"# Tazı raporu — {tarih_kisa(tarih)} {tarih[:4]}", "",
         f"{len(kayit_ids)} kayıt tarandı. Kaynaklar: {', '.join(s for s in KAYNAKLAR if s in ks) or '-'}.", ""]
    for i in kayit_ids:
        k = adlar.get(i, {"ad": i, "kisiler": []})
        snap = json_oku(os.path.join(kok, bug, i + ".json"), {})
        mine = [r for r in rows.values() if r["kayit"] == i]
        bu = [r for r in mine if r["tarama"] == bug and r["tur"] != "baglanti"]
        yeni = sorted([r for r in bu if r["durum"] == "yeni"], key=lambda r: r["tarih"], reverse=True)
        deg = [r for r in bu if r["durum"] == "degisti"]
        kayip = [r for r in bu if r["durum"] == "kayip"]
        taban = [r for r in bu if r["durum"] == "taban"]
        onc = [g for g in gunler if g < bug and os.path.exists(os.path.join(kok, g, i + ".json"))]
        ontxt = "önceki " + tarih_kisa(f"{onc[-1][:4]}-{onc[-1][4:6]}-{onc[-1][6:]}") if onc else "ilk tarama"
        L.append("## " + k["ad"] + ("".join(" · " + p for p in k["kisiler"])))
        L.append(f"Durum: {len(yeni)} yeni, {len(deg)} değişti, {len(kayip)} artık görünmüyor · tarama {tarih_kisa(tarih)} · {ontxt}")
        if taban:
            tb, site_n = [], 0
            for r in taban:
                if r["alt"].endswith(":kayit_tarihi"):
                    tb.append(f"{r['alt'].split(':')[0]} alan adı kaydı {tarih_kisa(r['deger'])} {str(r['deger'])[:4]}")
                elif r["alt"].endswith(":kayit_kurulusu"):
                    tb.append(f"kayıt kuruluşu {r['deger']}")
                elif r["alt"] in ("abn:entity_name", "abn:abn_durumu"):
                    tb.append(r["etiket"].replace("sicil ", "") + " " + r["deger"])
                elif r["tur"] == "site" and r.get("baslik") and site_n < 2:
                    site_n += 1
                    tb.append(f"site başlığı «{r['baslik'][:60]}»")
                elif r["tur"] == "arsiv" and r["alt"].endswith(":ilk"):
                    tb.append(f"ilk arşiv kaydı {r['deger']}")
            sy = sum(1 for r in taban if r["tur"] == "site")
            if sy > 1:
                tb.append(f"{sy} sayfa")
            tb = list(dict.fromkeys(tb))
            adlar_s = sorted({r["alt"] for r in taban if r["tur"] == "sertifika" and not r["alt"].startswith("www.")
                              and r["alt"] not in k.get("alanlar", [])})
            if adlar_s:
                tb.append("sertifika kayıtlarındaki alt alan adları: " + ", ".join(adlar_s[:6]) + (f" (+{len(adlar_s) - 6})" if len(adlar_s) > 6 else ""))
            for tur_, ad_ in (("teknoloji", "teknoloji bulgusu"), ("sosyal_hesap", "sosyal hesap"), ("varlik", "varlık bulgusu"),
                              ("arsiv", "arşiv kaydı"), ("kod", "kod deposu kaydı")):
                n_ = sum(1 for r in taban if r["tur"] == tur_)
                if n_:
                    tb.append(f"{n_} {ad_}")
            bas_ = "İlk tarama" if not onc else "Yeni kaynak(lar) ilk kez okundu"
            L.append(f"- {bas_}: {len(taban)} kayıt taban alındı" + (" — " + "; ".join(tb[:10]) if tb else ""))
        kay = lambda r: f" Kaynak: {r['kaynak']}" if r.get("kaynak") else ""
        L += yeni_satirlari(yeni, kay)
        for r in deg:
            if r["tur"] == "site":
                L.append(f"- [Değişti · {r['derece']}] {tarih_kisa(r['tarih'])} — {r['ozet']}.{kay(r)}")
                L += ["    " + x for x in r.get("ayrinti", [])]
            else:
                L.append(f"- [Değişti · {r['derece']}] {tarih_kisa(r['tarih'])} — {r.get('etiket', r['ozet'])}: "
                         f"{str(r['onceki'])[:90]} → {str(r['deger'])[:90]}.{kay(r)}")
        for r in kayip:
            L.append(f"- [Artık görünmüyor · {r['derece']}] {tarih_kisa(r['tarih'])} — {r['ozet']}")
        if notlar.get(i):
            L.append("Değerlendirme: " + notlar[i])
        oku = [f"{kk} ({v[len('okunamadı: '):]})" for kk, v in (snap.get("durum") or {}).items() if v != "ok"]
        if oku:
            L.append("Okunamayan: " + "; ".join(oku))
        L.append(f"Değişmeyen: {len([r for r in mine if r['tarama'] != bug and r['durum'] != 'kayip' and r['tur'] != 'baglanti'])} kayıt")
        L += dosya_bolumu(mine, dosya_oku(dizin, i))
        L.append("")
    L += baglanti_haritasi(rows, set(kayit_ids), adlar)
    L += ["---", "Kanıt dereceleri: A resmî/makine kaydı · B bağımsız yayın · C kendi beyanı · D çıkarım/doğrulanmadı.",
          "Yalnız iş bilgisi; özel hayat, konum, aile, sağlık toplanmaz.", ""]
    return "\n".join(L)


def rapor_cmd(a):
    dizin = veri_dizin()
    liste = liste_oku(a.liste)
    bug = a.tarama or json_oku(yollar(dizin)["son"], {}).get("tarama")
    if not bug:
        print("tarama yok; önce `tara`")
        return 1
    m = rapor_uret(dizin, liste, bug)
    yol = os.path.join(dizin, "rapor", f"tazi-{bug}.md")
    yaz_atomik(yol, m)
    yaz_atomik(os.path.join(dizin, "rapor", "tazi-son.md"), m)
    print(yol)
    return 0


# ---------- özet, durum ----------
def ozet_metni(sorgu, dizin=None, liste=None):
    """Toplantı hazırlığı için en çok 8 satır: başlık, kimlik hükmü, ≤4 yeni/değişen, açık bayrak, değerlendirme."""
    dizin = veri_dizin(dizin)
    try:
        liste = liste or liste_oku(None, dizin)
    except Exception:
        return None
    k = kayit_bul(liste, sorgu)
    if not k:
        return None
    b = bugun()
    st = son_tarama_tarihi(dizin, k["id"])
    ay = " (aday)" if k.get("kaynak") == "suflor-aday" else ""
    gun = ""
    if st:
        try:
            n = (b - datetime.date.fromisoformat(str(st)[:10])).days
            gun = f", {n} gün önce" if n >= 7 else ""
        except ValueError:
            pass
    L = [f"Tazı · {k['ad']}{ay} — son tarama {tarih_kisa(st) if st else 'yok'}{gun}"]
    d = dosya_oku(dizin, k["id"])
    kim = dosya_ogeleri(d, "kimlik")
    if kim:
        L.append("Kimlik: " + kim[-1]["metin"][:200])
    uygun, rows = [], bulgu_oku(dizin).values()
    for r in rows:
        if r["kayit"] != k["id"] or r["durum"] not in ("yeni", "degisti") or r["tur"] == "baglanti":
            continue
        try:
            dt = datetime.date.fromisoformat(str(r["tarih"])[:10])
        except ValueError:
            continue
        if 0 <= (b - dt).days <= 45 or dt > b and (dt - b).days <= 1:
            uygun.append((dt, r.get("kid") == "claude", r))
    for dt, _, r in sorted(uygun, key=lambda x: (x[0], x[1]), reverse=True)[:4]:
        o = r["ozet"] if r["tur"] != "alan_adi" and r["durum"] != "degisti" else f"{r.get('etiket', r['ozet'])}: {r.get('onceki') or ''} → {r['deger']}".replace(": →", ":")
        L.append(f"- [{r['derece']}] {tarih_kisa(dt.isoformat())} {o[:160]}" + (f" ({kaynak_alan(r['kaynak'])})" if r.get("kaynak") else ""))
    if not uygun:
        L.append("son 45 günde yeni bir şey yok")
    bay = [o["metin"] for bl in ("bayrak", "celiski") for o in dosya_ogeleri(d, bl, True)]
    bay += [str(r["ozet"])[len("Bayrak: "):] for r in _bayraklar([r for r in rows if r["kayit"] == k["id"]])]
    if bay:
        L.append(f"Açık bayrak: {len(bay)} — {bay[0][:120]}")
    t = json_oku(yollar(dizin)["son"], {}).get("tarama")
    n = json_oku(os.path.join(dizin, "notlar", t + ".json"), {}).get(k["id"]) if t else None
    if n:
        L.append("Değerlendirme: " + n[:300])
    return "\n".join(L[:8])


def metinden_kayitlar(metin, liste=None, dizin=None, en_cok=3):
    """Serbest metinde (soru, özet) adı, kişisi ya da alan adı geçen izleme kayıtları, geçiş sırasıyla. Yalnız yerel liste; ağ yok.
    Kısa (< 4 karakter) ad ve tek sözcüklü kısa kişi adı eşleşme sayılmaz; alan adı ve firma adı tam sözcük olarak aranır."""
    q = tr_kucuk(metin)
    if not q.strip():
        return []
    try:
        liste = liste if liste is not None else liste_oku(None, dizin)
    except Exception:
        return []

    def yer(s):
        s = tr_kucuk(s).strip()
        if len(s) < 4:
            return None
        m = re.search(r"(?<![\w.-])" + re.escape(s) + r"(?![\w-])", q)
        return m.start() if m else None
    out = []
    for k in liste:
        adlar = [k["ad"], kisa_ad(k["ad"])] + [p for p in k["kisiler"] if " " in p.strip() or len(p.strip()) >= 6] + list(k["alanlar"])
        ys = [y for y in (yer(a_) for a_ in adlar) if y is not None]
        if ys:
            out.append((min(ys), k))
    return [k for _, k in sorted(out, key=lambda x: x[0])][:en_cok]


def ozet_satiri(sorgu, dizin=None, liste=None):
    """Brifing ve kısa kartlar için tek satır (en çok ~260 karakter): ad, kimlik hükmü, ilk yeni gelişme, açık bayrak, son tarama. Eşleşme yoksa None."""
    m = ozet_metni(sorgu, dizin=dizin, liste=liste)
    if not m:
        return None
    L = m.splitlines()
    bas = re.match(r"Tazı · (.*?) — son tarama (.*)$", L[0])
    ad, st = (bas.group(1), bas.group(2)) if bas else (L[0], "?")
    p = [ad]
    for l in L[1:]:
        if l.startswith("Kimlik: "):
            p.append(l[8:100])
        elif l.startswith("- ["):
            p.append("yeni: " + re.sub(r"^- \[[A-D]\]\s*", "", l)[:90])
            break
    bay = next((l for l in L if l.startswith("Açık bayrak: ")), None)
    if bay:
        p.append(bay[:110])
    return (" · ".join(p) + f" (son tarama {st})")[:300]


def ozet_cmd(a):
    m = ozet_metni(a.kim, liste=liste_oku(a.liste))
    if m is None:
        print("eşleşme yok")
        return 1
    print(m)
    return 0


def liste_cmd(a):
    for k in liste_oku(a.liste):
        print(f"{k['id']} | {k['ad']} | kişiler: {', '.join(k['kisiler']) or '-'} | alanlar: {', '.join(k['alanlar']) or '-'} | "
              f"abn: {k['abn'] or '-'} | linkedin: {len(k['linkedin'])} | x: {len(k.get('x', []))}")
    return 0


def durum_cmd(a):
    dizin = veri_dizin()
    s = sayac_oku(dizin)
    print(f"veri klasörü: {dizin}\nliste: {liste_yolu(a.liste, dizin)}\nSuflor aday listesi: {len(aday_oku(dizin))} kayıt\nson tarama: {son_tarama_tarihi(dizin) or 'yok'}\n"
          f"LinkedIn bu hafta: {s['linkedin']['n']}/{sosyal_limit('linkedin')}\nX bu hafta: {s['x']['n']}/{sosyal_limit('x')}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="tazi.py", description="Tazı: dış firma ve iş bağlantısı izleme (yalnız iş bilgisi).")
    p.add_argument("--liste", help="izleme listesi yolu (JSON ya da Markdown tablo)")
    sp = p.add_subparsers(dest="komut", required=True)
    sp.add_parser("liste", help="izleme listesini göster").set_defaults(f=liste_cmd)
    t = sp.add_parser("tara", help="kaynakları oku, önceki taramayla karşılaştır")
    t.add_argument("--hizli", action="store_true", help="yalnız hızlı kaynaklar (RDAP, DNS, ana sayfa, haber), kısa zaman aşımı")
    t.add_argument("--kim"); t.add_argument("--kaynak", help=",".join(KAYNAKLAR) + " (site = tarama)"); t.set_defaults(f=tara_cmd)
    ad_ = sp.add_parser("aday", help="Suflor'un aday listesine ekle (ana listene yazılmaz)")
    ad_.add_argument("--ad", required=True); ad_.add_argument("--alan"); ad_.add_argument("--neden", default="elle", choices=("toplanti", "konus", "brifing", "elle"))
    ad_.set_defaults(f=aday_cmd)
    si = sp.add_parser("sosyal-izin", help="LinkedIn ya da X sayfası açmadan önce sayaçtan izin al")
    si.add_argument("platform", choices=PLATFORMLAR); si.add_argument("kayit_id"); si.add_argument("url"); si.set_defaults(f=sosyal_cmd)
    li = sp.add_parser("linkedin-izin", help="sosyal-izin linkedin takma adı")
    li.add_argument("kayit_id"); li.add_argument("url"); li.set_defaults(f=linkedin_cmd)
    e = sp.add_parser("ekle", help="Claude'un topladığı bulguyu ekle")
    e.add_argument("--kim", required=True); e.add_argument("--tur", required=True); e.add_argument("--ozet", required=True)
    e.add_argument("--kaynak"); e.add_argument("--tarih"); e.add_argument("--derece", choices=list("ABCD")); e.add_argument("--alinti")
    e.add_argument("--platform", choices=("linkedin", "x", "web"), default="web", help="gönderinin yayımlandığı yer")
    e.set_defaults(f=ekle_cmd)
    ds = sp.add_parser("dosya", help="soruşturma dosyası: ekle, kapat, göster")
    ds.add_argument("--kim", required=True); ds.add_argument("--bolum", choices=BOLUMLER); ds.add_argument("--metin")
    ds.add_argument("--kaynak"); ds.add_argument("--derece", choices=list("ABCD")); ds.add_argument("--tarih")
    ds.add_argument("--kapat", type=int, help="kapatılacak öğe no"); ds.add_argument("--sonuc")
    ds.set_defaults(f=dosya_cmd)
    d = sp.add_parser("degerlendir", help="kayıt için tek paragraflık değerlendirme")
    d.add_argument("--kim", required=True); d.add_argument("--metin", required=True); d.set_defaults(f=degerlendir_cmd)
    r = sp.add_parser("rapor", help="Markdown rapor üret")
    r.add_argument("--tarama", help="AAAAGGAA"); r.set_defaults(f=rapor_cmd)
    o = sp.add_parser("ozet", help="bir kaydın son gelişmeleri (en çok 8 satır)")
    o.add_argument("--kim", required=True); o.set_defaults(f=ozet_cmd)
    sp.add_parser("durum", help="veri klasörü, liste, son tarama, LinkedIn ve X sayaçları").set_defaults(f=durum_cmd)
    a = p.parse_args(argv)
    try:
        return a.f(a) or 0
    except FileNotFoundError as ex:
        print(f"dosya bulunamadı: {ex.filename}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
