# Güvenlik denetimi G2/G3 (13 Kasım 2026, security-audit skill denemesi): dışarı çıkan web isteği ve okunan dosya için ortak kapı.
# Amaç yetenek kısmak değil, sızdırma yolunu kapatmak: genel bir sayfayı açmak (WebFetch) ve dosya okumak sorulmadan sürer; yalnız
# veri taşıyabilecek biçimdeki adres (uzun sorgu, kodlanmış uzun parça, kullanıcı adı/şifre bölümü) ya da gizli bilgi taşıyan
# dosya (anahtar, şifre, tarayıcı çerezi) kullanıcıya sorulur. Bölüm dosyası olarak relay.py'nin ad alanında çalışır (bolum("web-kapi")),
# Konuş kancası da aynı dosyayı tek başına çalıştırır: yalnız standart kütüphane, relay globallerine dokunmaz.
import os, re, ipaddress, urllib.parse

WEB_SORGU_EN_COK = 80      # sorgu dizgesi (? sonrası) karakter sınırı: arama sayfası, sayfa numarası, dil seçimi sığar
WEB_ADRES_EN_COK = 400     # adresin tamamı
WEB_KODLU_PARCA = 48       # bu uzunlukta, büyük+küçük harf+rakam karışık kesintisiz parça (base64 gibi) ya da 64+ hex veri taşıyor sayılır;
                           # sayfa adı (tire/alt çizgili sözcükler), GitHub commit numarası (40 hex) sorulmaz
_WEB_PARCA_RX = re.compile(r"[A-Za-z0-9+=_.%~-]+")
def _web_kodlu(metin):
    for s in _WEB_PARCA_RX.findall(metin):
        if len(s) >= 64 and re.fullmatch(r"[0-9a-fA-F]+", s): return True
        if len(s) >= WEB_KODLU_PARCA and re.search(r"[A-Z]", s) and re.search(r"[a-z]", s) and re.search(r"\d", s) and not re.search(r"[a-z]{3,}[-_][a-z]{3,}[-_][a-z]{3,}", s, re.I): return True
    return False
_WEB_YEREL_SON = (".local", ".internal", ".localhost", ".lan", ".home", ".arpa", ".test", ".invalid")

def web_url_suphe(url):  # sorulmadan açılamayacak adres için (tr, en) neden, yoksa None
    u = str(url or "").strip()
    try: p = urllib.parse.urlsplit(u)
    except ValueError: return ("Adres çözülemedi.", "The address could not be parsed.")
    if p.scheme.lower() not in ("http", "https") or not p.hostname:
        return ("Yalnız http/https adresleri açılır.", "Only http/https addresses can be opened.")
    if p.username or p.password or "@" in (p.netloc or ""):
        return ("Adreste kullanıcı adı/şifre bölümü var.", "The address contains a user name/password part.")
    h = p.hostname.lower().rstrip(".")
    try: ipaddress.ip_address(h); return ("IP adresi doğrudan açılmaz.", "Raw IP addresses are not opened.")
    except ValueError: pass
    if h in ("localhost", "0.0.0.0") or "." not in h or h.endswith(_WEB_YEREL_SON) or re.fullmatch(r"[0-9x.]+", h):
        return ("Yalnız genel internet adresleri açılır.", "Only public internet addresses can be opened.")
    if len(u) > WEB_ADRES_EN_COK: return ("Adres çok uzun.", "The address is too long.")
    if len(p.query or "") > WEB_SORGU_EN_COK: return ("Adresin sorgu bölümü uzun (veri taşıyabilir).", "The query part is long (it may carry data).")
    if _web_kodlu(urllib.parse.unquote((p.path or "") + "/" + (p.query or "").replace("&", "/").replace("=", "/") + "/" + (p.fragment or ""))):
        return ("Adreste uzun kodlanmış bir parça var (veri taşıyabilir).", "The address has a long encoded segment (it may carry data).")
    return None

# Gizli bilgi taşıyan dosya ve klasörler: okunması sorulur (yasak değil). Yol ~ ile ya da göreli gelebilir; gerçek yola çevrilir.
_HASSAS_KLASOR = (".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker", ".config/gh", ".config/gcloud", "Library/Keychains", "Library/Cookies",
                  "Library/Application Support/Google/Chrome", "Library/Application Support/BraveSoftware", "Library/Application Support/Firefox",
                  "Library/Safari", "Library/Mail", "Library/Messages", "Library/Application Support/1Password", "Library/Application Support/Bitwarden")
_HASSAS_AD_RX = re.compile(r"(^\.env(\..*)?$|^\.netrc$|^\.npmrc$|^\.pypirc$|^id_(rsa|dsa|ecdsa|ed25519)|\.(pem|key|p12|pfx|keychain-db|kdbx)$|"
                           r"anahtar[^/]*\.txt$|credential|secret|token[^/]*\.(json|txt)$|cookies?(\.sqlite|\.binarycookies)?$|^login data$)", re.I)

def hassas_yol(yol):  # okunması kullanıcıya sorulacak yol mu
    y = str(yol or "")
    if not y or "\0" in y: return False
    try: g = os.path.realpath(os.path.expanduser(y))
    except (OSError, ValueError): return True
    ev = os.path.realpath(os.path.expanduser("~"))
    if g == ev or g.startswith(ev + os.sep):
        ic = g[len(ev):].lstrip(os.sep)
        if any(ic == k or ic.startswith(k + os.sep) for k in _HASSAS_KLASOR): return True
    return bool(_HASSAS_AD_RX.search(os.path.basename(g)))

# --- Web'e giden METİN kapısı (19 Kasım 2026, denetim 4 B3; S208 toplantıda, S257 toplantı dışı Konuş): arama sorgusu (WebSearch) ve adresin yol/sorgu
# kısmı (WebFetch). Kural: yalnız ad ve konu gider; döküm alıntısı, iç sayı, toplantı/kayıt içeriği gitmez. Tutucu kod sınırı (istemdeki kuralın yanında):
#   uzunluk (karakter + sözcük), e-posta adresi, 5+ haneli sayı (telefon, tutar, kimlik), bilinen İÇ kişi adı (kayıt veritabanı, kimlik eşlemesi,
#   toplantıda konuşanlar; S208 gereği dış katılımcının adı serbest) ve güncel dökümden 6+ sözcüklük birebir dizi. Süzgeç metin taşımaz: ad ve 6'lı
#   dizilerin yalnız özeti (sha256'nın ilk 16 hanesi) tutulur; aktarıcı canli/cikis-suzgec.json'a (0600) yazar, Konuş kancası (ayrı süreç) oradan okur.
import hashlib, unicodedata
WEB_ARAMA_EN_COK = 160     # arama sorgusu karakter sınırı
WEB_ARAMA_SOZCUK = 16      # arama sorgusu sözcük sınırı
WEB_YOL_SOZCUK = 24        # adresin yol + sorgu kısmında sözcük sınırı (haber/viki başlığı sığar, cümle taşınamaz)
WEB_ALINTI_N = 6           # dökümden bu kadar ardışık sözcük birebir geçerse alıntı sayılır
WEB_SAYI_HANE = 5          # bu kadar ve daha çok haneli sayı (ayraçlar sayılmaz) iç sayı sayılır; yıl (4 hane) serbest
_WEB_EPOSTA_RX = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")
_WEB_SAYI_RX = re.compile(r"\d[\d.,']*\d|\d")
def web_katla(s):  # Türkçe harf katlama + küçük harf: İıÇçĞğÖöŞşÜü → i/c/g/o/s/u (kimlik.py _kim_katla ile aynı)
    s = str(s or "").replace("İ", "i").replace("I", "i").replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
def web_sozcukler(s): return re.findall(r"[a-z0-9]+", web_katla(s))
def web_ozet(sozcukler): return hashlib.sha256(" ".join(sozcukler).encode("utf-8")).hexdigest()[:16]
def web_suzgec_kur(adlar=(), metinler=(), izinli=()):  # → {"adlar": [özet], "ad_n": en uzun ad (sözcük), "n6": [özet]} (metin taşımaz)
    serbest = {tuple(web_sozcukler(a)) for a in izinli or () if web_sozcukler(a)}
    ad_oz, en = set(), 1
    for a in adlar or ():
        s = tuple(web_sozcukler(a))
        if not s or s in serbest or (len(s) == 1 and len(s[0]) < 3): continue  # tek harfli/iki harfli tek sözcük (ör. "ek") ad sayılmaz
        ad_oz.add(web_ozet(s)); en = max(en, min(len(s), 6))
    n6 = set()
    for m in metinler or ():
        s = web_sozcukler(m)
        for i in range(0, max(0, len(s) - WEB_ALINTI_N + 1)): n6.add(web_ozet(s[i:i + WEB_ALINTI_N]))
    return {"adlar": sorted(ad_oz), "ad_n": en, "n6": sorted(n6)}
def web_metin_suphe(metin, suzgec=None, sinir=True):  # → (tr, en) neden ya da None. sinir: arama sorgusu uzunluk sınırları (adres yolu için False)
    m = " ".join(str(metin or "").split())
    if sinir and len(m) > WEB_ARAMA_EN_COK: return ("Arama metni çok uzun (yalnız ad ve konu gider).", "The search text is too long (only names and topics may go out).")
    s = web_sozcukler(m)
    if sinir and len(s) > WEB_ARAMA_SOZCUK: return ("Arama metninde çok sözcük var (yalnız ad ve konu gider).", "The search text has too many words (only names and topics may go out).")
    if _WEB_EPOSTA_RX.search(m): return ("Arama metninde e-posta adresi var.", "The search text contains an e-mail address.")
    for x in _WEB_SAYI_RX.findall(m):
        if sum(c.isdigit() for c in x) >= WEB_SAYI_HANE: return ("Arama metninde uzun bir sayı var (iç sayı gitmez).", "The search text contains a long number (internal figures stay here).")
    if not isinstance(suzgec, dict): return None
    adlar = set(suzgec.get("adlar") or ())
    try: en = max(1, min(6, int(suzgec.get("ad_n") or 3)))
    except (TypeError, ValueError): en = 3
    if adlar:
        for n in range(1, en + 1):
            for i in range(0, len(s) - n + 1):
                if web_ozet(s[i:i + n]) in adlar: return ("Arama metninde iç kayıttaki ya da toplantıdaki bir kişinin adı var.", "The search text contains the name of a person from internal records or the meeting.")
    n6 = set(suzgec.get("n6") or ())
    if n6:
        for i in range(0, len(s) - WEB_ALINTI_N + 1):
            if web_ozet(s[i:i + WEB_ALINTI_N]) in n6: return ("Arama metni dökümden birebir alıntı içeriyor.", "The search text quotes the transcript word for word.")
    return None
def web_getir_suphe(url, suzgec=None):  # WebFetch: adres kapısı + yol/sorgu kısmında metin kapısı (sözcük sınırı, ad, alıntı, e-posta, uzun sayı)
    r = web_url_suphe(url)
    if r: return r
    try: p = urllib.parse.urlsplit(str(url or "").strip())
    except ValueError: return ("Adres çözülemedi.", "The address could not be parsed.")
    yol = urllib.parse.unquote_plus((p.path or "") + " " + (p.query or "") + " " + (p.fragment or ""))
    yol = re.sub(r"[/_\-+=&?#.,;:]+", " ", yol)
    if len(web_sozcukler(yol)) > WEB_YOL_SOZCUK: return ("Adres yolunda çok sözcük var (veri taşıyabilir).", "The address path has too many words (it may carry data).")
    return web_metin_suphe(yol, suzgec, sinir=False)
def web_suzgec_oku(canli):  # Konuş kancası (ayrı süreç): → (süzgeç ya da None, neden ya da None). Dosya yok → None (genel sınırlar yine geçerli); okunamıyor/bozuk → neden (reddet)
    fp = os.path.join(str(canli or ""), "cikis-suzgec.json")
    try:
        import json as _j
        with open(fp, encoding="utf-8") as f: d = _j.load(f)
    except FileNotFoundError: return None, None
    except Exception: return None, "süzgeç okunamadı"
    if not isinstance(d, dict): return None, "süzgeç bozuk"
    if d.get("gizli"): return None, "gizli"
    return d, None
