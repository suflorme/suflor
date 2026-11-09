#!/usr/bin/env python3
"""Tazı — dış firma ve iş bağlantısı izleme aracı (Suflor.me). Yalnız standart kütüphane, Python 3.9.

Kural toplar, yapay zekâ değerlendirir: `tara` makine kaynaklarını (RDAP, DNS, crt.sh, site, ABR, haber RSS) okur, önceki
taramayla karşılaştırır; Claude oturumu (.claude/skills/tazi) haber ve LinkedIn'i tamamlar, `ekle` ile yazar, `rapor` üretir.
Yalnız iş bilgisi: özel hayat, konum, aile, sağlık toplanmaz; kişi puanlanmaz. Bulgu türleri kapalı listedir.
Veri: ~/Library/Application Support/Suflor/tazi/ (ya da TAZI_DIR). Şifre/anahtar dosyaya yazılmaz.
"""
import argparse, datetime, difflib, email.utils, hashlib, json, os, re, shlex, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser

UA = "Suflor-Tazi/1 (+local)"
TURLER = ("alan_adi", "dns", "sertifika", "sicil", "site", "haber", "gonderi", "ortaklik")
DURUM_TURLER = ("alan_adi", "dns", "sicil", "site")      # durum türleri: değişir, kaybolabilir
OLAY_TURLER = ("sertifika", "haber", "gonderi", "ortaklik")  # olay türleri: yalnız yeni
KAYNAKLAR = ("rdap", "dns", "crt", "site", "sicil", "haber")
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


def http_al(url, zaman=20, ek=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(ek or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=zaman) as r:
        veri = r.read(3_000_000)
        cs = r.headers.get_content_charset() or "utf-8"
    return veri.decode(cs, "replace")


# ---------- izleme listesi ----------
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
                       "neden": next((i for i, c in enumerate(low) if c.startswith("neden")), None)}
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
        sira = []
        for a in alanlar:
            if a not in sira:
                sira.append(a)
        kayitlar.append({"id": slug(ad), "ad": ad, "kisiler": kisiler, "alanlar": sira, "abn": abn,
                         "linkedin": lin, "sayfalar": [], "haber_sorgu": [], "neden": neden})
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


def liste_oku(arg=None, dizin=None):
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
    def __init__(self, k, bugun_, dizin, onceki_site):
        self.k, self.bugun, self.dizin, self.onceki_site = k, bugun_, dizin, onceki_site
        self.facts, self.durum, self.site = [], {}, {}


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
                    ctx.facts.append(Fact("alan_adi", f"{d}:{alt}", dg, f"alan adı {d} {et}", kid, "A", url + "domain/" + d))
            ctx.durum[kid] = "ok"
        except Exception as e:
            ctx.durum[kid] = "okunamadı: " + temiz_hata(e)


def dig_calistir(t, d):
    kom = shlex.split(os.environ.get("TAZI_DIG") or "dig") + ["+short", t, d]
    p = subprocess.run(kom, capture_output=True, text=True, timeout=20)
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
                        ctx.facts.append(Fact("dns", f"{d}:{t.lower()}:{s}", s, f"DNS {t} {d}", kid, "A", f"dns:{d}"))
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
    return "\n".join(s for s in satirlar if s)[:20000], re.sub(r"\s+", " ", p.baslik).strip()


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


def site(ctx):
    urller = [f"https://{d}/" for d in ctx.k["alanlar"]] + list(ctx.k["sayfalar"])
    for u in dict.fromkeys(urller):
        kid = f"site:{u}"
        try:
            metin, baslik = sayfa_metni(http_al(site_adres(u)))
            h = hashlib.sha256(metin.encode()).hexdigest()
            ctx.site[u] = {"metin": metin, "baslik": baslik}
            ctx.facts.append(Fact("site", u, h, f"site {kaynak_alan(u)}", kid, "C", u, baslik=baslik,
                                  ozet=f"site: {baslik or kaynak_alan(u)}", site_url=u))
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


KOLEKTOR = {"rdap": rdap, "dns": dns, "crt": crt, "site": site, "sicil": sicil, "haber": haber}


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
    for f in ctx.facts:
        a = anahtar(k["id"], f.tur, f.alt)
        simdiki.add(a)
        r = rows.get(a)
        durum_tur = f.tur in DURUM_TURLER
        ek = dict(f.ek)
        ek.pop("yas", None)
        ek.pop("site_url", None)
        if r is None:
            if ilk and (durum_tur or f.tur == "sertifika" or (f.tur == "haber" and f.ek.get("yas", 99) > 14)):
                d = "taban"
            else:
                d = "yeni"
            r = {"anahtar": a, "kayit": k["id"], "tur": f.tur, "alt": f.alt, "deger": f.deger, "onceki": None, "ozet": f.ozet,
                 "kaynak": f.kaynak, "tarih": f.tarih or iso, "derece": f.derece, "ilk_gorulme": iso, "son_gorulme": iso,
                 "durum": d, "tarama": bug, "kid": f.kid, "etiket": f.etiket}
            r.update(ek)
            if f.tur == "site" and d == "yeni" and not ilk:
                r["ozet"] = f"yeni sayfa izleniyor: {f.alt}"
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


def tara_cmd(a):
    dizin = veri_dizin()
    liste = liste_oku(a.liste)
    if a.kim:
        k = kayit_bul(liste, a.kim)
        if not k:
            print("eşleşme yok: " + a.kim)
            return 1
        liste = [k]
    sec = [s.strip() for s in a.kaynak.split(",")] if a.kaynak else list(KAYNAKLAR)
    bad = [s for s in sec if s not in KAYNAKLAR]
    if bad:
        print("bilinmeyen kaynak: " + ",".join(bad))
        return 1
    b = bugun()
    bug = b.strftime("%Y%m%d")
    rows = bulgu_oku(dizin)
    son = json_oku(yollar(dizin)["son"], {"kayitlar": {}})
    son.setdefault("kayitlar", {})
    for k in liste:
        onc_t, onc = onceki_tarama(dizin, k["id"], bug)
        ilk = onc_t is None
        ctx = Ctx(k, b, dizin, onc.get("site", {}))
        for s in sec:
            try:
                KOLEKTOR[s](ctx)
            except Exception as e:
                ctx.durum[s] = "okunamadı: " + temiz_hata(e)
        birlestir(k, ctx, rows, ilk, bug)
        yaz_atomik(os.path.join(dizin, "tarama", bug, k["id"] + ".json"), json.dumps(
            {"kayit": k["id"], "tarih": b.isoformat(), "kaynaklar": sec, "durum": ctx.durum, "site": ctx.site,
             "olgular": [{"tur": f.tur, "alt": f.alt, "deger": f.deger, "kid": f.kid} for f in ctx.facts]}, ensure_ascii=False))
        bu = [r for r in rows.values() if r["kayit"] == k["id"] and r["tarama"] == bug]
        okunmayan = [f"{kk}: {v}" for kk, v in ctx.durum.items() if v != "ok"]
        say = lambda d: sum(1 for r in bu if r["durum"] == d)
        son["kayitlar"][k["id"]] = {"ad": k["ad"], "tarih": b.isoformat(), "yeni": say("yeni"), "degisti": say("degisti"),
                                    "kayip": say("kayip"), "taban": say("taban"), "okunamayan": okunmayan}
        print(f"{k['ad']}: {say('yeni')} yeni, {say('degisti')} değişti, {say('kayip')} artık görünmüyor, "
              f"{say('taban')} taban, {len(okunmayan)} okunamadı")
    son["tarama"] = bug
    bulgu_yaz(dizin, rows)
    yaz_atomik(yollar(dizin)["son"], json.dumps(son, ensure_ascii=False, indent=1))
    print(f"tarama {bug} bitti: {len(liste)} kayıt")
    return 0


# ---------- LinkedIn, ekle, değerlendir ----------
def li_norm(u):
    p = urllib.parse.urlparse(u.strip())
    return (p.netloc.lower().replace("www.", "") + p.path.rstrip("/")).lower()


def linkedin_cmd(a):
    dizin = veri_dizin()
    k = kayit_bul(liste_oku(a.liste), a.kayit_id)
    if not k:
        print("hayır: kayıt yok")
        return 1
    if li_norm(a.url) not in [li_norm(x) for x in k["linkedin"]]:
        print("hayır: adres bu kaydın listesinde yok")
        return 1
    yol = yollar(dizin)["sayac"]
    y = bugun().isocalendar()
    hafta = f"{y[0]}-W{y[1]:02d}"
    s = json_oku(yol, {})
    if s.get("hafta") != hafta:
        s = {"hafta": hafta, "n": 0, "log": []}
    lim = int(os.environ.get("TAZI_LI_LIMIT", "8"))
    if s["n"] >= lim:
        print(f"hayır: haftalık sınır doldu ({s['n']}/{lim})")
        return 1
    s["n"] += 1
    s["log"].append({"t": int(time.time()), "kayit": k["id"], "url": a.url.split("?")[0]})
    yaz_atomik(yol, json.dumps(s, ensure_ascii=False))
    print(f"evet ({s['n']}/{lim})")
    return 0


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
    derece = a.derece or {"gonderi": "C", "haber": "B", "ortaklik": "C"}.get(a.tur, "C")
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
    rows[an] = r
    bulgu_yaz(dizin, rows)
    print("eklendi")
    return 0


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


# ---------- rapor ----------
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
        ks.update((json_oku(os.path.join(kok, bug, i + ".json"), {}).get("kaynaklar") or []))
    L = [f"# Tazı raporu — {tarih_kisa(tarih)} {tarih[:4]}", "",
         f"{len(kayit_ids)} kayıt tarandı. Kaynaklar: {', '.join(s for s in KAYNAKLAR if s in ks) or '-'}.", ""]
    for i in kayit_ids:
        k = adlar.get(i, {"ad": i, "kisiler": []})
        snap = json_oku(os.path.join(kok, bug, i + ".json"), {})
        mine = [r for r in rows.values() if r["kayit"] == i]
        bu = [r for r in mine if r["tarama"] == bug]
        yeni = sorted([r for r in bu if r["durum"] == "yeni"], key=lambda r: r["tarih"], reverse=True)
        deg = [r for r in bu if r["durum"] == "degisti"]
        kayip = [r for r in bu if r["durum"] == "kayip"]
        taban = [r for r in bu if r["durum"] == "taban"]
        onc = [g for g in gunler if g < bug and os.path.exists(os.path.join(kok, g, i + ".json"))]
        ontxt = "önceki " + tarih_kisa(f"{onc[-1][:4]}-{onc[-1][4:6]}-{onc[-1][6:]}") if onc else "ilk tarama"
        L.append("## " + k["ad"] + ("".join(" · " + p for p in k["kisiler"])))
        L.append(f"Durum: {len(yeni)} yeni, {len(deg)} değişti, {len(kayip)} artık görünmüyor · tarama {tarih_kisa(tarih)} · {ontxt}")
        if taban:
            tb = []
            for r in taban:
                if r["alt"].endswith(":kayit_tarihi"):
                    tb.append(f"{r['alt'].split(':')[0]} alan adı kaydı {tarih_kisa(r['deger'])} {str(r['deger'])[:4]}")
                elif r["alt"].endswith(":kayit_kurulusu"):
                    tb.append(f"kayıt kuruluşu {r['deger']}")
                elif r["alt"] in ("abn:entity_name", "abn:abn_durumu"):
                    tb.append(r["etiket"].replace("sicil ", "") + " " + r["deger"])
                elif r["tur"] == "site" and r.get("baslik"):
                    tb.append(f"site başlığı «{r['baslik'][:60]}»")
            tb = list(dict.fromkeys(tb))
            adlar_s = sorted({r["alt"] for r in taban if r["tur"] == "sertifika" and not r["alt"].startswith("www.")
                              and r["alt"] not in k.get("alanlar", [])})
            if adlar_s:
                tb.append("sertifika kayıtlarındaki alt alan adları: " + ", ".join(adlar_s[:6]) + (f" (+{len(adlar_s) - 6})" if len(adlar_s) > 6 else ""))
            L.append(f"- İlk tarama: {len(taban)} kayıt taban alındı" + (" — " + "; ".join(tb[:8]) if tb else ""))
        kay = lambda r: f" Kaynak: {r['kaynak']}" if r.get("kaynak") else ""
        for r in yeni:
            s = f"- [Yeni · {r['derece']}] {tarih_kisa(r['tarih'])} — {r['ozet']}.{kay(r)}"
            if r.get("alinti"):
                s += f" Alıntı: “{r['alinti']}”"
            L.append(s)
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
        L.append(f"Değişmeyen: {len([r for r in mine if r['tarama'] != bug and r['durum'] != 'kayip'])} kayıt")
        L.append("")
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
    L = [f"Tazı · {k['ad']} — son tarama {tarih_kisa(st) if st else 'yok'}"]
    uygun = []
    for r in bulgu_oku(dizin).values():
        if r["kayit"] != k["id"] or r["durum"] not in ("yeni", "degisti"):
            continue
        try:
            d = datetime.date.fromisoformat(str(r["tarih"])[:10])
        except ValueError:
            continue
        if 0 <= (b - d).days <= 45 or d > b and (d - b).days <= 1:
            uygun.append((d, r))
    for d, r in sorted(uygun, key=lambda x: x[0], reverse=True)[:5]:
        o = r["ozet"] if r["tur"] != "alan_adi" and r["durum"] != "degisti" else f"{r.get('etiket', r['ozet'])}: {r.get('onceki') or ''} → {r['deger']}".replace(": →", ":")
        L.append(f"- [{r['derece']}] {tarih_kisa(d.isoformat())} {o[:180]}" + (f" ({kaynak_alan(r['kaynak'])})" if r.get("kaynak") else ""))
    if not uygun:
        L.append("son 45 günde yeni bir şey yok")
    t = json_oku(yollar(dizin)["son"], {}).get("tarama")
    n = json_oku(os.path.join(dizin, "notlar", t + ".json"), {}).get(k["id"]) if t else None
    if n:
        L.append("Değerlendirme: " + n[:300])
    return "\n".join(L)


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
              f"abn: {k['abn'] or '-'} | linkedin: {len(k['linkedin'])}")
    return 0


def durum_cmd(a):
    dizin = veri_dizin()
    y = bugun().isocalendar()
    s = json_oku(yollar(dizin)["sayac"], {})
    n = s.get("n", 0) if s.get("hafta") == f"{y[0]}-W{y[1]:02d}" else 0
    print(f"veri klasörü: {dizin}\nliste: {liste_yolu(a.liste, dizin)}\nson tarama: {son_tarama_tarihi(dizin) or 'yok'}\n"
          f"LinkedIn bu hafta: {n}/{os.environ.get('TAZI_LI_LIMIT', '8')}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="tazi.py", description="Tazı: dış firma ve iş bağlantısı izleme (yalnız iş bilgisi).")
    p.add_argument("--liste", help="izleme listesi yolu (JSON ya da Markdown tablo)")
    sp = p.add_subparsers(dest="komut", required=True)
    sp.add_parser("liste", help="izleme listesini göster").set_defaults(f=liste_cmd)
    t = sp.add_parser("tara", help="kaynakları oku, önceki taramayla karşılaştır")
    t.add_argument("--kim"); t.add_argument("--kaynak", help="rdap,dns,crt,site,sicil,haber"); t.set_defaults(f=tara_cmd)
    li = sp.add_parser("linkedin-izin", help="LinkedIn sayfası açmadan önce sayaçtan izin al")
    li.add_argument("kayit_id"); li.add_argument("url"); li.set_defaults(f=linkedin_cmd)
    e = sp.add_parser("ekle", help="Claude'un topladığı bulguyu ekle")
    e.add_argument("--kim", required=True); e.add_argument("--tur", required=True); e.add_argument("--ozet", required=True)
    e.add_argument("--kaynak"); e.add_argument("--tarih"); e.add_argument("--derece", choices=list("ABCD")); e.add_argument("--alinti")
    e.set_defaults(f=ekle_cmd)
    d = sp.add_parser("degerlendir", help="kayıt için tek paragraflık değerlendirme")
    d.add_argument("--kim", required=True); d.add_argument("--metin", required=True); d.set_defaults(f=degerlendir_cmd)
    r = sp.add_parser("rapor", help="Markdown rapor üret")
    r.add_argument("--tarama", help="AAAAGGAA"); r.set_defaults(f=rapor_cmd)
    o = sp.add_parser("ozet", help="bir kaydın son gelişmeleri (en çok 6 satır)")
    o.add_argument("--kim", required=True); o.set_defaults(f=ozet_cmd)
    sp.add_parser("durum", help="veri klasörü, liste, son tarama, LinkedIn sayacı").set_defaults(f=durum_cmd)
    a = p.parse_args(argv)
    try:
        return a.f(a) or 0
    except FileNotFoundError as ex:
        print(f"dosya bulunamadı: {ex.filename}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
