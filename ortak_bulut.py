#!/usr/bin/env python3
# Suflor.me ortak karar katmanı A7 — Firestore taşıma katmanı (6 Kasım). Ortak karar/iş olaylarını Cloud Firestore'dan paylaşır:
# her kullanıcı yalnız kendi olaylarını yazar (Security Rules: yazan = oturum e-postası, silme yok), bir olayı yalnız `okuyan` listesindekiler okur. Yalnız standart kütüphane.
# İçe aktarılabilir mantık (aktarici/ortak-klasor.py çağırır: `esitle`, `hazir`, `gecikme_ozet`) + komut satırı: kur, giris, davet, katil, durum, esitle.
#   python3 -B ortak_bulut.py kur --proje <p> --istemci <id> --alan <a> [--alan <b>]     yönetici kurulumu (bir kez; yönetici belirteci saklanmaz)
#   python3 -B ortak_bulut.py davet | katil <kod> | giris | durum | esitle
# Kimlik: Google OAuth masaüstü akışı (PKCE, 127.0.0.1) → Google id_token → Firebase signInWithIdp → Firebase belirteci; yenileme belirteci YALNIZ Anahtar Zinciri'nde
# (suflor-firestore-yenileme), Web API anahtarı suflor-firestore-api, istemci sırrı suflor-firestore-istemci-sirri. Ayar: ortak_tasima ("firestore"; yoksa kapalı),
# firestore_proje, firestore_istemci_id, firestore_alanlar (izinli e-posta alan adları), firestore_bolge. Kod/yorumda gerçek proje, alan adı, e-posta yok: yalnız ayarda.
# Gizlilik: olay seçimi ve süzgeci A3 ile BİREBİR aynı yardımcıdan (yapi.ortak_secilen: gizli/deneme toplantı, Claude yorumu, ayar öncesi kayıt gitmez). Kişisel posta alan adı ya da
# firestore_alanlar dışı kimlik → hiçbir istek gitmez. Ses, döküm satırı, alıntı gitmez. Beta paketine alan eklenmez.
# Deneme (gerçek Google/Anahtar Zinciri'ne hiç gidilmez): SUFLOR_FS_KOK (127.0.0.1 sahte sunucu kökü; her servis <kök>/<servis-adı>/… altında), SUFLOR_FS_ZINCIR_DIZIN (Anahtar Zinciri
# yerine düz dosyalar), SUFLOR_FS_TEST=1 (ikisi de zorunlu; yoksa hiçbir şey yapılmaz), SUFLOR_FS_GIRIS_IPUCU (sahte oturum açma e-postası), SUFLOR_FS_BEKLE (uzun işlem yoklama sn).
import argparse, base64, calendar, hashlib, http.server, json, os, re, secrets, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request, webbrowser

_BURASI = os.path.dirname(os.path.abspath(__file__))
ORTAK_OGE = {"yenileme": "suflor-firestore-yenileme", "api": "suflor-firestore-api", "sir": "suflor-firestore-istemci-sirri"}
KISISEL = ("gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "msn.com", "yahoo.com", "icloud.com", "me.com", "mac.com", "yandex.com", "proton.me", "protonmail.com", "aol.com")
KOLEKSIYON = "olaylar"
ALANLAR = ("v", "olay_id", "kayit_id", "tur", "zaman", "saat", "yazan", "yazan_ad", "cihaz", "kaynak", "veri", "okuyan", "guncel")
TOPLU, SORGU_SINIR, OKUYAN_EN_COK, TUR_EN_COK = 200, 300, 50, 20
SERVISLER = {"yetki": "https://accounts.google.com", "oauth": "https://oauth2.googleapis.com", "identitytoolkit": "https://identitytoolkit.googleapis.com",
             "securetoken": "https://securetoken.googleapis.com", "firestore": "https://firestore.googleapis.com", "firebaserules": "https://firebaserules.googleapis.com",
             "firebase": "https://firebase.googleapis.com", "serviceusage": "https://serviceusage.googleapis.com"}
KAPSAM_GIRIS = "openid email"
KAPSAM_YONETICI = "openid email https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/firebase"
API_SERVISLERI = ("firestore.googleapis.com", "firebaserules.googleapis.com", "identitytoolkit.googleapis.com", "firebase.googleapis.com")
_EPOSTA = re.compile(r"^[a-z0-9._%+'-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
_ALAN = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
_PROJE = re.compile(r"^[a-z][a-z0-9-]{4,29}$")
_ISTEMCI = re.compile(r"^[A-Za-z0-9._-]{8,200}$")
_GIZLI = re.compile(r"^[A-Za-z0-9._~/+=:%-]{1,4000}$")  # Anahtar Zinciri'ne yazılacak değer (security -i satırında tırnak güvenli)
class FsHata(Exception):
    # sinif: ag | yetki | giris_yok | kural | yok | sunucu | istek | ayar | alan | eposta | kapali | test_koruma
    def __init__(self, sinif, ek=""): super().__init__(f"{sinif}{(': ' + ek) if ek else ''}"); self.sinif = sinif; self.ek = ek

# --- uç adresleri, ayar, Anahtar Zinciri -------------------------------------------------------------------------------------------------------------------
def _test_mi(): return bool(os.environ.get("SUFLOR_FS_TEST"))
def _koruma():  # deneme kipinde sahte kök ve düz dosya zinciri ZORUNLU (gerçek Google/Anahtar Zinciri'ne yanlışlıkla gitmesin); kök yalnız yerel döngü adresi olabilir
    kok = os.environ.get("SUFLOR_FS_KOK")
    if _test_mi() and not (kok and os.environ.get("SUFLOR_FS_ZINCIR_DIZIN")): raise FsHata("test_koruma", "SUFLOR_FS_KOK ve SUFLOR_FS_ZINCIR_DIZIN gerekli")
    if kok and urllib.parse.urlparse(kok).hostname not in ("127.0.0.1", "localhost", "::1"): raise FsHata("test_koruma", "kök yerel olmalı")
def uc(servis, yol):
    _koruma(); kok = os.environ.get("SUFLOR_FS_KOK")
    return (kok.rstrip("/") + "/" + servis if kok else SERVISLER[servis]) + yol
def ayar_yol(): return os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")
def ayar_oku():
    try: v = json.load(open(ayar_yol(), encoding="utf-8"))
    except (OSError, ValueError): v = {}
    return v if isinstance(v, dict) else {}
def ayar_yaz(**kv):  # oku-değiştir-yaz; diğer anahtarlara dokunulmaz
    yol = ayar_yol(); v = ayar_oku(); v.update(kv)
    os.makedirs(os.path.dirname(yol), exist_ok=True); fd = os.open(yol + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(v, f, ensure_ascii=False, indent=1)
    os.replace(yol + ".tmp", yol)
def zincir_oku(oge):
    _koruma(); d = os.environ.get("SUFLOR_FS_ZINCIR_DIZIN")
    if d:
        try: return open(os.path.join(d, oge), encoding="utf-8").read().strip()
        except OSError: return ""
    try: return subprocess.run(["/usr/bin/security", "find-generic-password", "-a", "suflor", "-s", str(oge), "-w"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError): return ""
def zincir_yaz(oge, deger):  # security -i: değer ps'te görünmez; dosyaya/ayara yazılmaz
    _koruma()
    if not _GIZLI.match(str(deger)): raise FsHata("ayar", "değer biçimi")
    d = os.environ.get("SUFLOR_FS_ZINCIR_DIZIN")
    if d:
        os.makedirs(d, exist_ok=True); fd = os.open(os.path.join(d, oge), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(deger)
        return
    r = subprocess.run(["/usr/bin/security", "-i"], input=f'add-generic-password -U -a suflor -s {oge} -l "Suflor.me {oge}" -w "{deger}"\n', capture_output=True, text=True, timeout=20)
    if r.returncode: raise FsHata("ayar", "Anahtar Zinciri'ne yazılamadı")

def alan_gecerli(a): return bool(_ALAN.match(str(a))) and str(a) not in KISISEL
def alan_izinli(ep, alanlar):  # e-posta alan adı izinli listede ve kişisel posta değil
    ep = str(ep or "").lower()
    return bool(_EPOSTA.match(ep)) and ep.split("@")[1] in [str(a).lower() for a in alanlar or []] and ep.split("@")[1] not in KISISEL
def baglam(ayar=None, sir_gerek=False):
    a = ayar if isinstance(ayar, dict) else ayar_oku()
    p = str(a.get("firestore_proje") or ""); ist = str(a.get("firestore_istemci_id") or ""); al = [str(x).lower() for x in (a.get("firestore_alanlar") or []) if alan_gecerli(str(x).lower())]
    if not _PROJE.match(p) or not al: raise FsHata("ayar", "proje ya da alan adı yok")
    b = {"proje": p, "istemci": ist, "alanlar": al, "api": zincir_oku(ORTAK_OGE["api"]), "bolge": str(a.get("firestore_bolge") or "eur3")}
    if sir_gerek or ist: b["sir"] = zincir_oku(ORTAK_OGE["sir"])
    return b
def hazir(ayar=None):  # ağa gitmeden: kapali | ayar_eksik | giris_yok | hazir (Anahtar Zinciri'nde yenileme belirteci ve API anahtarı var)
    a = ayar if isinstance(ayar, dict) else ayar_oku()
    if str(a.get("ortak_tasima") or "drive") != "firestore": return "kapali"
    try: b = baglam(a)
    except FsHata: return "ayar_eksik"
    return "hazir" if zincir_oku(ORTAK_OGE["yenileme"]) and b["api"] else "giris_yok"

# --- HTTP ----------------------------------------------------------------------------------------------------------------------------------------------------
def _http(yontem, url, govde=None, belirtec=None, form=None, ust=None, zaman=30):  # → (kod, sözlük); ağ yoksa FsHata("ag")
    h = dict(ust or {}); veri = None
    if form is not None: veri = urllib.parse.urlencode(form).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
    elif govde is not None: veri = json.dumps(govde, ensure_ascii=False).encode(); h["Content-Type"] = "application/json"
    if belirtec: h["Authorization"] = "Bearer " + belirtec
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=veri, method=yontem, headers=h), timeout=zaman) as r: kod, ham = r.status, r.read()
    except urllib.error.HTTPError as e: kod, ham = e.code, e.read()
    except (OSError, ValueError) as e: raise FsHata("ag", e.__class__.__name__)
    try: o = json.loads(ham.decode("utf-8") or "{}")
    except ValueError: o = {}
    return kod, (o if isinstance(o, (dict, list)) else {})
def _sinif(kod, o=None):
    d = ((o or {}).get("error") or {}) if isinstance(o, dict) else {}; st = str(d.get("status") or "")
    if kod == 401: return "yetki"
    if kod == 403: return "kural"
    if kod == 404: return "yok"
    if kod in (409, 412) or st in ("ALREADY_EXISTS", "FAILED_PRECONDITION"): return "cakisma"
    return "sunucu" if kod >= 500 or kod == 429 else "istek"
def _jwt_yuk(t):
    try: p = str(t).split(".")[1]; return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    except Exception: return {}
def ts_oku(s):  # RFC 3339 (nanosaniyeli olabilir) → saniye (float)
    m = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z", str(s or ""))
    if not m: return 0.0
    return calendar.timegm(time.strptime(m[1], "%Y-%m-%dT%H:%M:%S")) + (float("0." + m[2]) if m[2] else 0.0)
def ts_yaz(t): t = max(0.0, float(t)); return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(t))) + ".%06dZ" % int((t % 1) * 1e6)

# --- kimlik: Google OAuth (PKCE) → Firebase ------------------------------------------------------------------------------------------------------------------
def _oauth(b, kapsam):  # tarayıcıda Google izin penceresi; yerel dönüş adresi 127.0.0.1:<boş port> → {access_token, id_token, …}
    ver = secrets.token_urlsafe(48); chal = base64.urlsafe_b64encode(hashlib.sha256(ver.encode()).digest()).rstrip(b"=").decode(); durum = secrets.token_urlsafe(16); alinan = {}
    class Ic(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == durum and q.get("code"): alinan["kod"] = q["code"][0]
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("<meta charset=utf-8><p>Suflor.me Google girişi tamam; bu sekmeyi kapatabilirsin.</p>".encode())
    sv = http.server.HTTPServer(("127.0.0.1", 0), Ic); port = sv.server_address[1]; sv.timeout = 300; dr = f"http://127.0.0.1:{port}"
    q = {"client_id": b["istemci"], "redirect_uri": dr, "response_type": "code", "scope": kapsam, "code_challenge": chal, "code_challenge_method": "S256", "state": durum, "prompt": "select_account"}
    if os.environ.get("SUFLOR_FS_GIRIS_IPUCU"): q["login_hint"] = os.environ["SUFLOR_FS_GIRIS_IPUCU"]
    url = uc("yetki", "/o/oauth2/v2/auth") + "?" + urllib.parse.urlencode(q)
    t = threading.Thread(target=sv.handle_request); t.start()
    if os.environ.get("SUFLOR_FS_KOK"): threading.Thread(target=lambda: _http("GET", url), daemon=True).start()  # deneme: sahte yetki ucu yönlendirmeyi kendisi yapar
    else: print("tarayıcıda Google izin penceresi açılıyor…", file=sys.stderr); webbrowser.open(url)
    t.join(310); sv.server_close()
    if not alinan.get("kod"): raise FsHata("yetki", "izin alınamadı")
    f = {"client_id": b["istemci"], "code": alinan["kod"], "code_verifier": ver, "redirect_uri": dr, "grant_type": "authorization_code"}
    if b.get("sir"): f["client_secret"] = b["sir"]
    kod, o = _http("POST", uc("oauth", "/token"), form=f)
    if kod != 200 or not o.get("id_token"): raise FsHata("yetki", f"belirteç alınamadı ({kod})")
    return o
def _firebase_giris(b, google_id_token):  # → {idToken, refreshToken, expiresIn, email}
    kod, o = _http("POST", uc("identitytoolkit", "/v1/accounts:signInWithIdp") + "?key=" + urllib.parse.quote(b["api"]),
                   {"postBody": f"id_token={google_id_token}&providerId=google.com", "requestUri": "http://localhost", "returnSecureToken": True, "returnIdpCredential": True})
    if kod != 200 or not o.get("idToken"): raise FsHata(_sinif(kod, o) if kod != 400 else "yetki", f"firebase girişi ({kod})")
    return o
_B = {}  # proje → {"id", "bitis", "eposta"}: Firebase belirteci yalnız bellekte (1 sa; 5 dk kala yenilenir)
def firebase_belirtec(b, zorla=False):  # → (id_token, e-posta)
    t = _B.get(b["proje"])
    if t and not zorla and t["bitis"] > time.time() + 300: return t["id"], t["eposta"]
    ref = zincir_oku(ORTAK_OGE["yenileme"])
    if not ref or not b.get("api"): raise FsHata("giris_yok")
    kod, o = _http("POST", uc("securetoken", "/v1/token") + "?key=" + urllib.parse.quote(b["api"]), form={"grant_type": "refresh_token", "refresh_token": ref})
    if kod in (400, 401) or not o.get("id_token"): _B.pop(b["proje"], None); raise FsHata("yetki" if kod in (400, 401) else _sinif(kod, o), f"yenileme ({kod})")
    if o.get("refresh_token") and o["refresh_token"] != ref and _GIZLI.match(o["refresh_token"]): zincir_yaz(ORTAK_OGE["yenileme"], o["refresh_token"])
    ep = str(_jwt_yuk(o["id_token"]).get("email") or "").lower()
    _B[b["proje"]] = {"id": o["id_token"], "bitis": time.time() + int(o.get("expires_in") or 3600), "eposta": ep}
    return o["id_token"], ep
def giris(ayar=None, ilerle=print):  # tek seferlik oturum açma (kapsam openid email) → e-posta
    b = baglam(ayar, True)
    if not b["istemci"] or not b["api"]: raise FsHata("ayar", "istemci kimliği ya da API anahtarı yok")
    o = _oauth(b, KAPSAM_GIRIS); fb = _firebase_giris(b, o["id_token"]); ep = str(fb.get("email") or _jwt_yuk(fb["idToken"]).get("email") or "").lower()
    if not alan_izinli(ep, b["alanlar"]): raise FsHata("alan", "bu e-posta alan adı izinli değil")  # izinli değilse hiçbir şey saklanmaz
    zincir_yaz(ORTAK_OGE["yenileme"], fb["refreshToken"]); _B[b["proje"]] = {"id": fb["idToken"], "bitis": time.time() + int(fb.get("expiresIn") or 3600), "eposta": ep}
    ilerle(f"Giriş tamam: {ep}"); return ep

# --- Firestore REST ---------------------------------------------------------------------------------------------------------------------------------------------
def _fs(b, yontem, yol, govde=None):  # yol: /documents:commit gibi; 401'de belirteç bir kez yenilenir → (kod, gövde)
    url = uc("firestore", f"/v1/projects/{b['proje']}/databases/(default){yol}")
    for deneme in (0, 1):
        tok, _ = firebase_belirtec(b, zorla=bool(deneme))
        kod, o = _http(yontem, url, govde, tok)
        if kod != 401 or deneme: return kod, o
def _isim(b, olay_id): return f"projects/{b['proje']}/databases/(default)/documents/{KOLEKSIYON}/{olay_id}"
def _tv(v):
    if isinstance(v, bool): return {"booleanValue": v}
    if isinstance(v, int): return {"integerValue": str(v)}
    if isinstance(v, list): return {"arrayValue": {"values": [_tv(x) for x in v]}}
    return {"stringValue": str(v)}
def _alan_oku(f):
    if not isinstance(f, dict): return None
    if "stringValue" in f: return f["stringValue"]
    if "integerValue" in f:
        try: return int(f["integerValue"])
        except ValueError: return None
    if "timestampValue" in f: return f["timestampValue"]
    if "booleanValue" in f: return f["booleanValue"]
    if "arrayValue" in f: return [_alan_oku(x) for x in (f["arrayValue"].get("values") or [])]
    return None
_GUNCEL_DONUSUM = [{"fieldPath": "guncel", "setToServerValue": "REQUEST_TIME"}]
def _belge(b, s, okuyan):  # olay satırı + okuyan → commit yazması (yalnız oluştur; var ise ALREADY_EXISTS)
    f = {k: _tv(s[k]) for k in ("v", "olay_id", "kayit_id", "tur", "zaman", "saat", "yazan", "yazan_ad", "cihaz", "kaynak")}
    f["veri"] = _tv(json.dumps(s["veri"], ensure_ascii=False)); f["okuyan"] = _tv(list(okuyan))
    return {"update": {"name": _isim(b, s["olay_id"]), "fields": f}, "currentDocument": {"exists": False}, "updateTransforms": _GUNCEL_DONUSUM}
def _yama(b, olay_id, okuyan):  # yalnız okuyan + guncel güncellenir (kural: yalnız yazan, yalnız genişleme)
    return {"update": {"name": _isim(b, olay_id), "fields": {"okuyan": _tv(list(okuyan))}}, "updateMask": {"fieldPaths": ["okuyan"]}, "currentDocument": {"exists": True},
            "updateTransforms": _GUNCEL_DONUSUM}
def _yaz_toplu(b, yazmalar):
    # → {"yazildi", "var": zaten vardı/yok sayıldı} ; ağ/5xx/401/kural hatası FsHata (imleç ilerlemesin). Toplu başarısızsa tek tek: ALREADY_EXISTS/FAILED_PRECONDITION = zaten gönderilmiş.
    say = {"yazildi": 0, "var": 0}
    for i in range(0, len(yazmalar), TOPLU):
        grup = yazmalar[i:i + TOPLU]; kod, o = _fs(b, "POST", "/documents:commit", {"writes": grup})
        if kod == 200: say["yazildi"] += len(grup); continue
        if _sinif(kod, o) != "cakisma": raise FsHata(_sinif(kod, o), f"commit {kod}")
        for w in grup:
            kod, o = _fs(b, "POST", "/documents:commit", {"writes": [w]})
            if kod == 200: say["yazildi"] += 1
            elif _sinif(kod, o) in ("cakisma", "yok"): say["var"] += 1
            else: raise FsHata(_sinif(kod, o), f"commit {kod}")
    return say
def _kume(*listeler, ep):  # okuyan kümeleri birleşir (küçülmez), ≤ 50, her zaman yazan dahil
    s = set()
    for l in listeler: s |= {str(x).lower() for x in (l or [])}
    s.discard(ep); return sorted(s)[:OKUYAN_EN_COK - 1] + [ep] if s else [ep]
def _kume_sirali(*listeler, ep): return sorted(_kume(*listeler, ep=ep))

# --- eşitleme (aktarıcının döngüsü bunu çağırır) -------------------------------------------------------------------------------------------------------------
def gecikme_ozet(kd):  # durum dosyasındaki son 200 gecikme (sn) → (ortanca, p90) ya da (None, None)
    g = sorted(float(x) for x in (kd or {}).get("gecikme") or [])
    return (round(g[len(g) // 2], 1), round(g[min(len(g) - 1, int(len(g) * 0.9))], 1)) if g else (None, None)
def _yapi(y):
    if y is not None: return y
    if _BURASI not in sys.path: sys.path.insert(0, _BURASI)
    import yapi; return yapi
def _disari(y, b, dizin, kd, ep, ad, gecmis, kimlik_f, iceri_kidler):
    out = {"yazilan": 0, "atlanan": {}, "genisleyen": 0}; ok = kd.setdefault("okuyan", {})
    sec = y.ortak_secilen(dizin, kd, ep, ad, gecmis, kimlik_f); out["atlanan"] = dict(sec["atlanan"])
    # rol genişlemesi: bu kullanıcının daha önce gönderdiği olayların okuyan'ı yeni rollere göre büyür (başkasının olayına dokunulmaz; okuyan küçülmez)
    kidler = [k for k in sorted(set(sec["okuyan"]) | set(iceri_kidler)) if k in ok]
    yeni = y.ortak_okuyan(dizin, kidler, ep, ad, kimlik_f) if kidler else {}; yamalar = []; guncel = {}
    for kid in kidler:
        birlesik = _kume_sirali(ok[kid]["k"], yeni.get(kid), ep=ep)
        if birlesik != sorted(ok[kid]["k"]): yamalar += [_yama(b, i, birlesik) for i in ok[kid]["i"]]; guncel[kid] = birlesik
    if yamalar: _yaz_toplu(b, yamalar); out["genisleyen"] = len(guncel)
    for kid, k in guncel.items(): ok[kid]["k"] = k
    yazmalar = []; ids = {}
    for s in sec["satirlar"]:
        if len(json.dumps(s["veri"], ensure_ascii=False)) > y.ORTAK_SATIR_EN_COK: out["atlanan"]["buyuk"] = out["atlanan"].get("buyuk", 0) + 1; continue
        s = dict(s, yazan=ep); kid = s["kayit_id"]; k = _kume_sirali((ok.get(kid) or {}).get("k"), sec["okuyan"].get(kid), ep=ep)
        yazmalar.append(_belge(b, s, k)); ids.setdefault(kid, (k, []))[1].append(s["olay_id"])
    if yazmalar: _yaz_toplu(b, yazmalar)
    for kid, (k, l) in ids.items():
        e = ok.setdefault(kid, {"k": [], "i": []}); e["k"] = k; e["i"] = e["i"] + [i for i in l if i not in e["i"]]
    if sec["son"] is not None: kd["gonderilen"] = sec["son"]
    kd["yazilan"] = int(kd.get("yazilan") or 0) + len(yazmalar); out["yazilan"] = len(yazmalar); return out
def _sorgu(b, ep, alt, esit):
    return {"structuredQuery": {"from": [{"collectionId": KOLEKSIYON}], "where": {"compositeFilter": {"op": "AND", "filters": [
        {"fieldFilter": {"field": {"fieldPath": "okuyan"}, "op": "ARRAY_CONTAINS", "value": {"stringValue": ep}}},
        {"fieldFilter": {"field": {"fieldPath": "guncel"}, "op": "GREATER_THAN_OR_EQUAL" if esit else "GREATER_THAN", "value": {"timestampValue": ts_yaz(alt)}}}]}},
        "orderBy": [{"field": {"fieldPath": "guncel"}, "direction": "ASCENDING"}], "limit": SORGU_SINIR}}
def _belge_satir(y, d):  # Firestore belgesi → doğrulanmış olay satırı ya da None
    f = d.get("fields") or {}; o = {k: _alan_oku(f.get(k)) for k in ALANLAR}
    try: o["veri"] = json.loads(o["veri"]) if isinstance(o.get("veri"), str) and len(o["veri"]) <= y.ORTAK_SATIR_EN_COK else None
    except ValueError: o["veri"] = None
    yz = str(o.get("yazan") or "").lower()
    if not _EPOSTA.match(yz) or not y._CIHAZ_RX.match(str(o.get("cihaz") or "")): return None
    return o if y._satir_gecerli(o, yz, o["cihaz"]) else None
def _iceri(y, b, dizin, kd, ep, yerel_cihaz):
    out = {"alinan": 0, "cift": 0, "bozuk": 0, "yarim": 0, "dosya": 0, "kisiler": [], "kidler": []}
    imlec = float(kd.get("imlec") or 0); alt = max(0.0, imlec - 2); esit = False; en_son = imlec; gelen = []; kisiler = set()
    for _ in range(TUR_EN_COK):
        kod, o = _fs(b, "POST", "/documents:runQuery", _sorgu(b, ep, alt, esit))
        if kod != 200 or not isinstance(o, list): raise FsHata(_sinif(kod, o if isinstance(o, dict) else {}), f"runQuery {kod}")
        belgeler = [x["document"] for x in o if isinstance(x, dict) and x.get("document")]
        for d in belgeler:
            g = ts_oku(_alan_oku((d.get("fields") or {}).get("guncel"))); en_son = max(en_son, g)
            s = _belge_satir(y, d)
            if not s: out["bozuk"] += 1; continue
            if s["cihaz"] == yerel_cihaz: continue
            kisiler.add(s["yazan"].lower()); s["_g"] = g; gelen.append(s)
        if len(belgeler) < SORGU_SINIR: break
        alt, esit = en_son, True  # dolu sayfa: aynı turda devam (eşit sınır; çift olay_id ile düşer)
    if gelen:
        r = y.ortak_al(dizin, gelen); out["alinan"], out["cift"], out["kidler"] = r["alinan"], r["cift"], r["kidler"]; yeni = set(r["yeni"]); simdi = time.time()
        g = kd.setdefault("gecikme", []); g.extend(round(max(0.0, simdi - x["_g"]), 2) for x in gelen if x["olay_id"] in yeni); del g[:-200]
    kd["imlec"] = en_son; out["kisiler"] = sorted(kisiler | set(kd.get("kisiler") or [])); kd["kisiler"] = out["kisiler"]
    kd["alinan"] = int(kd.get("alinan") or 0) + out["alinan"]; return out
def esitle(dizin, ayar, ep, ad="", gecmis=False, kimlik_f=None, y=None):
    # bir tur: önce başkalarının olayları alınır, sonra bu Mac'inkiler yazılır → {"disari", "iceri", "zaman", "gecikme": (ortanca, p90)}.
    # İzinsiz kimlik (kişisel posta / alan dışı / oturum e-postası ile giriş farklı) → hiçbir istek gitmez. Hata: FsHata(sınıf); imleç ilerlemez (çevrimdışı kuyruk = yerel günlük).
    y = _yapi(y); ep = str(ep or "").lower(); b = baglam(ayar)
    if not alan_izinli(ep, b["alanlar"]): raise FsHata("alan")
    _, giris_ep = firebase_belirtec(b)
    if giris_ep != ep: raise FsHata("eposta")
    d = y._ortak_durum(dizin); kd = d.setdefault("firestore", {}).setdefault(b["proje"], {})
    c = y._db(dizin)
    try: cihaz = y._yerel_cihaz(c)
    finally: c.close()
    try:
        i = _iceri(y, b, dizin, kd, ep, cihaz); dd = _disari(y, b, dizin, kd, ep, ad, gecmis, kimlik_f, i["kidler"])
        kd["eposta"] = ep; kd["son_esitleme"] = time.strftime("%Y-%m-%dT%H:%M:%S"); kd["son_hata"] = None
    except FsHata as e: kd["son_hata"] = e.sinif; y._ortak_durum_yaz(dizin, d); raise
    y._ortak_durum_yaz(dizin, d)
    return {"disari": dd, "iceri": i, "zaman": kd["son_esitleme"], "gecikme": gecikme_ozet(kd)}

# --- kurallar ve yönetici kurulumu ------------------------------------------------------------------------------------------------------------------------------
def kurallar(alanlar):  # Security Rules metni; alan adı noktaları [.] ile kaçışlı (kural düzenli ifadesinde nokta her karakter olmasın)
    al = [str(a).lower() for a in alanlar]
    if not al or not all(alan_gecerli(a) for a in al): raise FsHata("ayar", "alan adı geçersiz")
    desen = "|".join(a.replace(".", "[.]") for a in al)
    return f"""rules_version = '2';
service cloud.firestore {{
  match /databases/{{database}}/documents {{
    function giris() {{ return request.auth != null && request.auth.token.email_verified == true
                              && request.auth.token.email.matches('^[^@]+@({desen})$'); }}
    function ben() {{ return request.auth.token.email; }}
    match /olaylar/{{olay}} {{
      allow get, list: if giris() && ben() in resource.data.okuyan;
      allow create: if giris()
        && request.resource.data.keys().hasOnly(['v','olay_id','kayit_id','tur','zaman','saat','yazan','yazan_ad','cihaz','kaynak','veri','okuyan','guncel'])
        && request.resource.data.yazan == ben() && request.resource.data.olay_id == olay
        && request.resource.data.okuyan is list && request.resource.data.okuyan.size() <= 50 && ben() in request.resource.data.okuyan
        && request.resource.data.veri is string && request.resource.data.veri.size() <= 20000
        && request.resource.data.guncel == request.time;
      allow update: if giris() && resource.data.yazan == ben()
        && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['okuyan','guncel'])
        && request.resource.data.okuyan is list && request.resource.data.okuyan.size() <= 50
        && request.resource.data.okuyan.hasAll(resource.data.okuyan)
        && request.resource.data.guncel == request.time;
      allow delete: if false;
    }}
    match /{{document=**}} {{ allow read, write: if false; }}
  }}
}}
"""
def _sina_durumlari(alan):  # (ad, beklenen, yöntem, e-posta, doğrulandı, mevcut okuyan, istek verisi, sert mi) — sert olmayanlar sunucu zaman damgası eşitliğine bağlı ALLOW'lardır
    at = "@"; a, o, c, d = "sina-a" + at + alan, "sina-b" + at + alan, "sina-c" + at + alan, "sina-d" + at + "baska.example"
    return [("rolü olan okur (get)", "ALLOW", "get", o, True, [a, o], None, True), ("rolü olan listeler", "ALLOW", "list", o, True, [a, o], None, True),
            ("rolü olmayan aynı alan adlı get", "DENY", "get", c, True, [a, o], None, True), ("rolü olmayan aynı alan adlı list", "DENY", "list", c, True, [a, o], None, True),
            ("başka alan adı (okuyanda adı geçse bile)", "DENY", "get", d, True, [a, d], None, True), ("e-postası doğrulanmamış", "DENY", "get", o, False, [a, o], None, True),
            ("başkası adına yazma", "DENY", "create", o, True, None, {"yazan": a, "okuyan": [a, o]}, True), ("okuyanında kendisi olmayan oluşturma", "DENY", "create", a, True, None, {"yazan": a, "okuyan": [o]}, True),
            ("silme", "DENY", "delete", a, True, [a], None, True), ("okuyan'dan kişi çıkarma", "DENY", "update", a, True, [a, o], {"okuyan": [a]}, True),
            ("yazan olmayan güncelleme", "DENY", "update", o, True, [a, o], {"okuyan": [a, o, c]}, True),
            ("kendi olayını oluşturma", "ALLOW", "create", a, True, None, {"yazan": a, "okuyan": [a, o]}, False), ("okuyan genişletme (sahibi)", "ALLOW", "update", a, True, [a, o], {"okuyan": [a, o, c]}, False)]
def _sina_govde(b, metin, alan):
    sab = "2026-11-06T10:00:00Z"; belge = lambda ok, **k: dict({"v": 1, "olay_id": "sina1", "kayit_id": "K", "tur": "kayit_olustu", "zaman": sab, "saat": 1, "yazan": "sina-a" + "@" + alan, "yazan_ad": "",
                                                                  "cihaz": "c-000000", "kaynak": "s", "veri": "{}", "okuyan": ok, "guncel": sab}, **k)
    vakalar = []
    for ad, bek, yontem, ep, dogru, mevcut, istek, _ in _sina_durumlari(alan):
        rq = {"auth": {"uid": "u-" + ep.split("@")[0], "token": {"email": ep, "email_verified": dogru}}, "path": f"/databases/(default)/documents/{KOLEKSIYON}/sina1", "method": yontem, "time": sab}
        v = {"expectation": bek, "request": rq}
        if mevcut is not None: v["resource"] = {"data": belge(mevcut)}
        if istek is not None: rq["resource"] = {"data": belge(istek["okuyan"], **{k: x for k, x in istek.items() if k != "okuyan"})}
        vakalar.append(v)
    return {"source": {"files": [{"name": "firestore.rules", "content": metin}]}, "testSuite": {"testCases": vakalar}}
def kural_sina(b, tok, metin, ilerle=print):  # firebaserules projects:test → (sert hata sayısı, uyarı sayısı); sunucu yanıtı beklenenle uyuşmazsa sert durum çıkış 1 yapar
    alan = b["alanlar"][0]; kod, o = _http("POST", uc("firebaserules", f"/v1/projects/{b['proje']}:test"), _sina_govde(b, metin, alan), tok, ust={"X-Goog-User-Project": b["proje"]})
    if kod != 200: raise FsHata(_sinif(kod, o), f"kural sınaması {kod}")
    sonuc = o.get("testResults") or []; durumlar = _sina_durumlari(alan); sert = uyari = 0
    if len(sonuc) != len(durumlar): raise FsHata("istek", "kural sınaması eksik yanıt")
    for (ad, bek, *_, sertmi), r in zip(durumlar, sonuc):
        ok = r.get("state") == "SUCCESS"
        if ok: ilerle(f"  ✓ {bek} · {ad}")
        elif sertmi: sert += 1; ilerle(f"  ✗ {bek} bekleniyordu · {ad}")
        else: uyari += 1; ilerle(f"  ! {bek} sınaması geçmedi (zaman damgası biçimi olabilir) · {ad}")
    return sert, uyari
def _bekle_sn(): return float(os.environ.get("SUFLOR_FS_BEKLE") or 3)
def _islem_bekle(servis, surum, ad, tok, proje, ust_sn=300):  # uzun süren işlem bitene kadar yokla → yanıt
    son = time.time() + ust_sn; ust = {"X-Goog-User-Project": proje}
    while True:
        kod, o = _http("GET", uc(servis, f"/{surum}/{ad}"), belirtec=tok, ust=ust)
        if kod != 200: raise FsHata(_sinif(kod, o), f"işlem {kod}")
        if o.get("done"):
            if o.get("error"): raise FsHata("istek", str((o["error"] or {}).get("message") or "işlem hatası")[:120])
            return o.get("response") or {}
        if time.time() > son: raise FsHata("sunucu", "işlem zaman aşımı")
        time.sleep(_bekle_sn())
def kur(proje, istemci, alanlar, bolge=None, ilerle=print):
    # Yönetici kurulumu: her adım idempotent, Türkçe ilerleme satırı. Yönetici belirteci yalnız bellekte. Hata → FsHata; kural sınaması beklenmedikse FsHata("istek")
    if not _PROJE.match(str(proje)) or not _ISTEMCI.match(str(istemci)): raise FsHata("ayar", "proje ya da istemci kimliği geçersiz")
    alanlar = [str(a).lower() for a in alanlar]
    if not alanlar or not all(alan_gecerli(a) for a in alanlar): raise FsHata("ayar", "alan adı geçersiz ya da kişisel posta")
    bolge = bolge or ayar_oku().get("firestore_bolge") or "eur3"; sir = zincir_oku(ORTAK_OGE["sir"])
    if not sir: raise FsHata("ayar", "istemci sırrı Anahtar Zinciri'nde yok (" + ORTAK_OGE["sir"] + ")")
    b = {"proje": proje, "istemci": istemci, "sir": sir, "alanlar": alanlar}; ust = {"X-Goog-User-Project": proje}
    ilerle("1/8 Yönetici girişi (Google)…"); o = _oauth(b, KAPSAM_YONETICI); tok = o.get("access_token")
    if not tok: raise FsHata("yetki", "yönetici belirteci yok")
    def adm(yontem, servis, yol, govde=None): return _http(yontem, uc(servis, yol), govde, tok, ust=ust)
    ilerle("2/8 Servisler etkinleştiriliyor…")
    for s in API_SERVISLERI:
        kod, o = adm("GET", "serviceusage", f"/v1/projects/{proje}/services/{s}")
        if kod == 200 and o.get("state") == "ENABLED": ilerle(f"  · {s}: zaten açık"); continue
        kod, o = adm("POST", "serviceusage", f"/v1/projects/{proje}/services/{s}:enable", {})
        if kod != 200: raise FsHata(_sinif(kod, o), f"{s} etkinleştirilemedi ({kod})")
        if o.get("name") and not o.get("done"): _islem_bekle("serviceusage", "v1", o["name"], tok, proje)
        ilerle(f"  · {s}: açıldı")
    ilerle("3/8 Firestore veritabanı…"); kod, o = adm("GET", "firestore", f"/v1/projects/{proje}/databases/(default)")
    if kod == 200: ilerle("  · (default) zaten var")
    elif kod == 404:
        kod, o = adm("POST", "firestore", f"/v1/projects/{proje}/databases?databaseId=(default)", {"type": "FIRESTORE_NATIVE", "locationId": bolge})
        if kod != 200: raise FsHata(_sinif(kod, o), f"veritabanı oluşturulamadı ({kod})")
        if o.get("name") and not o.get("done"): _islem_bekle("firestore", "v1", o["name"], tok, proje)
        ilerle(f"  · (default) oluşturuldu ({bolge})")
    else: raise FsHata(_sinif(kod, o), f"veritabanı sorgusu ({kod})")
    ilerle("4/8 Bileşik dizin (okuyan + guncel)…"); yol = f"/v1/projects/{proje}/databases/(default)/collectionGroups/{KOLEKSIYON}/indexes"
    def dizin_var():
        kod, o = adm("GET", "firestore", yol)
        for x in (o.get("indexes") or []) if kod == 200 else []:
            f = [(z.get("fieldPath"), z.get("arrayConfig") or z.get("order")) for z in x.get("fields") or []][:2]
            if x.get("queryScope") == "COLLECTION" and f == [("okuyan", "CONTAINS"), ("guncel", "ASCENDING")]: return x
        return None
    x = dizin_var()
    if not x:
        kod, o = adm("POST", "firestore", yol, {"queryScope": "COLLECTION", "fields": [{"fieldPath": "okuyan", "arrayConfig": "CONTAINS"}, {"fieldPath": "guncel", "order": "ASCENDING"}]})
        if kod != 200: raise FsHata(_sinif(kod, o), f"dizin oluşturulamadı ({kod})")
        ilerle("  · dizin istendi, hazır olması bekleniyor…")
    son = time.time() + 300; ilk = True
    while not x or x.get("state") != "READY":
        if time.time() > son: raise FsHata("sunucu", "dizin 5 dk içinde hazır olmadı")
        if not ilk: time.sleep(_bekle_sn())
        ilk = False; x = dizin_var()
    ilerle("  · dizin hazır")
    ilerle("5/8 Güvenlik kuralları sınanıyor ve yayınlanıyor…"); metin = kurallar(alanlar)
    sert, uyari = kural_sina(b | {"proje": proje}, tok, metin, ilerle)
    if sert: raise FsHata("istek", f"kural sınaması: {sert} beklenmeyen sonuç; kurallar yayınlanmadı")
    rel = f"projects/{proje}/releases/cloud.firestore"; kod, o = adm("GET", "firebaserules", f"/v1/{rel}"); guncel = False
    if kod == 200 and o.get("rulesetName"):
        k2, r2 = adm("GET", "firebaserules", f"/v1/{o['rulesetName']}")
        guncel = k2 == 200 and any(f.get("content") == metin for f in (r2.get("source") or {}).get("files") or [])
    if guncel: ilerle("  · yayındaki kurallar zaten güncel")
    else:
        kod2, r = adm("POST", "firebaserules", f"/v1/projects/{proje}/rulesets", {"source": {"files": [{"name": "firestore.rules", "content": metin}]}})
        if kod2 != 200 or not r.get("name"): raise FsHata(_sinif(kod2, r), f"kural seti oluşturulamadı ({kod2})")
        if kod == 200: k3, r3 = adm("PATCH", "firebaserules", f"/v1/{rel}", {"release": {"name": rel, "rulesetName": r["name"]}})
        else: k3, r3 = adm("POST", "firebaserules", f"/v1/projects/{proje}/releases", {"name": rel, "rulesetName": r["name"]})
        if k3 != 200: raise FsHata(_sinif(k3, r3), f"kurallar yayınlanamadı ({k3})")
        ilerle("  · kurallar yayınlandı")
    ilerle("6/8 Web uygulaması ve API anahtarı…"); kod, o = adm("GET", "firebase", f"/v1beta1/projects/{proje}/webApps")
    if kod != 200: raise FsHata(_sinif(kod, o), f"web uygulamaları ({kod})")
    uyg = o.get("apps") or []; app = next((a for a in uyg if a.get("displayName") == "Suflor.me"), uyg[0] if uyg else None)
    if app is None:
        kod, o = adm("POST", "firebase", f"/v1beta1/projects/{proje}/webApps", {"displayName": "Suflor.me"})
        if kod != 200: raise FsHata(_sinif(kod, o), f"web uygulaması oluşturulamadı ({kod})")
        app = _islem_bekle("firebase", "v1beta1", o["name"], tok, proje) if o.get("name") and not o.get("done") else (o.get("response") or {}); ilerle("  · web uygulaması oluşturuldu")
    else: ilerle("  · web uygulaması zaten var")
    kod, o = adm("GET", "firebase", f"/v1beta1/projects/{proje}/webApps/{app.get('appId')}/config"); api = str(o.get("apiKey") or "") if kod == 200 else ""
    if not api: raise FsHata("istek", "web API anahtarı alınamadı")
    zincir_yaz(ORTAK_OGE["api"], api); ilerle("  · API anahtarı Anahtar Zinciri'ne yazıldı")
    ilerle("7/8 Ayar yazılıyor…"); ayar_yaz(ortak_tasima="firestore", firestore_proje=proje, firestore_istemci_id=istemci, firestore_alanlar=alanlar, firestore_bolge=bolge)
    ilerle("8/8 Kendi girişin (Google)…"); giris(ayar_oku(), ilerle); ilerle("Kurulum tamam."); return 0

# --- davet / katıl / durum ------------------------------------------------------------------------------------------------------------------------------------
def davet(ayar=None):  # tek satır kod (base64url JSON); yalnız ekrana basılır
    b = baglam(ayar, True)
    if not (b["istemci"] and b["sir"] and b["api"]): raise FsHata("ayar", "istemci kimliği, sır ya da API anahtarı eksik")
    return base64.urlsafe_b64encode(json.dumps({"proje": b["proje"], "istemci_id": b["istemci"], "istemci_sirri": b["sir"], "api": b["api"], "alanlar": b["alanlar"], "bolge": b["bolge"]},
                                               ensure_ascii=False, separators=(",", ":")).encode()).decode().rstrip("=")
def katil(kod, ilerle=print, giris_yap=True):
    try: p = json.loads(base64.urlsafe_b64decode(kod + "=" * (-len(kod) % 4)))
    except Exception: raise FsHata("ayar", "davet kodu çözülemedi")
    al = [str(a).lower() for a in p.get("alanlar") or []] if isinstance(p, dict) else []
    if not (isinstance(p, dict) and _PROJE.match(str(p.get("proje"))) and _ISTEMCI.match(str(p.get("istemci_id"))) and al and all(alan_gecerli(a) for a in al)
            and _GIZLI.match(str(p.get("istemci_sirri"))) and _GIZLI.match(str(p.get("api")))): raise FsHata("ayar", "davet kodu geçersiz")
    zincir_yaz(ORTAK_OGE["sir"], p["istemci_sirri"]); zincir_yaz(ORTAK_OGE["api"], p["api"])
    ayar_yaz(ortak_tasima="firestore", firestore_proje=p["proje"], firestore_istemci_id=p["istemci_id"], firestore_alanlar=al, firestore_bolge=str(p.get("bolge") or "eur3"))
    ilerle("Davet işlendi; ayar ve anahtarlar yazıldı."); return giris(ayar_oku(), ilerle) if giris_yap else None
def durum(dizin=None, ayar=None):  # metin içermez
    a = ayar if isinstance(ayar, dict) else ayar_oku(); h = hazir(a); kd = {}
    if dizin and h not in ("kapali", "ayar_eksik"):
        try: y = _yapi(None); kd = y._ortak_durum(dizin).get("firestore", {}).get(str(a.get("firestore_proje")), {})
        except Exception: kd = {}
    o, p90 = gecikme_ozet(kd)
    return {"tasima": str(a.get("ortak_tasima") or "drive"), "durum": h, "proje": str(a.get("firestore_proje") or ""), "giris": h == "hazir", "eposta": kd.get("eposta") or "",
            "son_esitleme": kd.get("son_esitleme"), "son_hata": kd.get("son_hata"), "gecikme_ortanca": o, "gecikme_p90": p90}

# --- komut satırı -------------------------------------------------------------------------------------------------------------------------------------------------
def _dizin_varsayilan(a): return os.path.join(os.path.expanduser(str(a.get("uygulama") or "~/Library/Application Support/Suflor")), "canli")  # aktarıcının canli klasörü (toplanti-claude.py DEF_DIR gibi)
def main(argv=None):
    ap = argparse.ArgumentParser(prog="ortak_bulut.py", description="Suflor.me ortak karar katmanı: Firestore taşıması"); alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kur"); k.add_argument("--proje", required=True); k.add_argument("--istemci", required=True); k.add_argument("--alan", action="append", required=True); k.add_argument("--bolge")
    alt.add_parser("giris"); alt.add_parser("davet"); kt = alt.add_parser("katil"); kt.add_argument("kod")
    for ad in ("durum", "esitle"):
        s = alt.add_parser(ad); s.add_argument("--dizin")
    n = ap.parse_args(argv); a = ayar_oku()
    try:
        if n.komut == "kur": return kur(n.proje, n.istemci, n.alan, n.bolge)
        if n.komut == "giris": giris(a); return 0
        if n.komut == "davet": print(davet(a)); return 0
        if n.komut == "katil": katil(n.kod); return 0
        dizin = os.path.expanduser(n.dizin) if getattr(n, "dizin", None) else _dizin_varsayilan(a)
        if n.komut == "durum":
            for ad, v in durum(dizin, a).items(): print(f"{ad}: {v}")
            return 0
        if n.komut == "esitle":
            y = _yapi(None); r = esitle(dizin, a, str(a.get("eposta_kimlik") or y.ben_eposta() or ""), str(a.get("ad") or ""), a.get("ortak_gecmis") is True)
            print(f"yazılan {r['disari']['yazilan']} · alınan {r['iceri']['alinan']} · çift {r['iceri']['cift']} · gecikme {r['gecikme']}"); return 0
    except FsHata as e: print(f"HATA ({e.sinif}): {e.ek or 'ayrıntı yok'}", file=sys.stderr); return 1
    return 2
if __name__ == "__main__":
    sys.dont_write_bytecode = True; sys.stdout.reconfigure(line_buffering=True)  # ilerleme satırları boruya da hemen düşsün
    sys.exit(main())
