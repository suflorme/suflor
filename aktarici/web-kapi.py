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
