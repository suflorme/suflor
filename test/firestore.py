#!/usr/bin/env python3
# Firestore taşıması — ortak karar katmanı A7 (ortak_bulut.py + aktarici/ortak-klasor.py + yapi.ortak_secilen/ortak_al). AĞA ÇIKMAZ: sahte sunucu (http.server, iş parçacığında, boş port) Google OAuth, signInWithIdp,
# securetoken, Firestore (commit/runQuery/batchGet/get), firebaserules, webApps, serviceusage, databases ve indexes uçlarını taklit eder ve tasarımdaki Security Rules'u Python'da uygular
# (belirteç → e-posta; okuyan denetimi; yazan = oturum; silme yok; okuyan küçülmez; alan adı listesi). Anahtar Zinciri yerine düz dosya klasörü. Gerçek Google'a ve gerçek Anahtar Zinciri'ne
# hiçbir istek gitmez (SUFLOR_FS_KOK ve SUFLOR_FS_ZINCIR_DIZIN yoksa modül kendisi durur; test ilk iş bunu denetler). Kurgu veri; gerçek claude yok.
# Senaryolar: iki yalıtılmış aktarıcıyla uçtan uca (A→B atama ve durum geri dönüşü, "Sana atandı"), rol dışı erişim 403, başkası adına yazma reddi, gizli/deneme/ayar öncesi/Claude yorumu 0,
# okuyan genişleme, çevrimdışı kuyruk ve çift 0, Drive'dan taşıma, kişisel/alan dışı kimlikte sıfır istek, kur (idempotent), davet/katıl, gecikme ölçümü, kural metni kaçışı, belirteç yenileme.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/firestore.py      (kaldı → çıkış 1; ~60 sn)
AT = "@"  # e-posta biçimi kaynakta geçmesin (açık depo taraması)
import base64, http.server, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, urllib.error, urllib.parse, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)  # kod önce: test/yapi.py adı çakışır
import yapi; import ortak_bulut as ob; from bosport import bos_port
hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
ALAN = "ornek.test"; PROJE = "test-proje"; ISTEMCI = "test-istemci-kimligi"; SIR = "test-istemci-sirri"; APIK = "test-api-anahtari"
EA, EB, EC, EF, EG = ["ayse", "bora", "can", "fatma", "gul"][0] + AT + ALAN, "bora" + AT + ALAN, "can" + AT + ALAN, "fatma" + AT + ALAN, "gul" + AT + ALAN
EY = "yonetici" + AT + ALAN; ED = "dis" + AT + "baska.example"; EGM = "kisisel" + AT + "gmail.com"
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
M_NORMAL, M_GIZLI, M_DENEME, M_ESKI = "2026-11-05-1400-Haftalik-Plan", "2026-11-05-1500-Butce-Ozel-Gorusme", "2026-11-05-1600-Deneme-Toplantisi", "2026-11-04-1000-Eski-Toplanti"
T = tempfile.mkdtemp(prefix="suflor-fs-")

# ============================== sahte sunucu ==============================================================================================================
def _b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
def _yuk(t):
    try: p = t.split(".")[1]; return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    except Exception: return {}
def _tv(v):
    if isinstance(v, int) and not isinstance(v, bool): return {"integerValue": str(v)}
    if isinstance(v, list): return {"arrayValue": {"values": [_tv(x) for x in v]}}
    if isinstance(v, float): return {"timestampValue": ob.ts_yaz(v)}
    return {"stringValue": str(v)}
def _ac(f):
    if "stringValue" in f: return f["stringValue"]
    if "integerValue" in f: return int(f["integerValue"])
    if "timestampValue" in f: return ob.ts_oku(f["timestampValue"])
    if "arrayValue" in f: return [_ac(x) for x in f["arrayValue"].get("values") or []]
    return None
def kural_izin(metin, yontem, ben, dogrulandi, mevcut, yeni, belge_id, zaman_esit):
    # tasarımdaki Security Rules'un Python karşılığı (alan adı deseni yayındaki metinden okunur)
    m = re.search(r"matches\('\^\[\^@\]\+@\((.*?)\)\$'\)", metin or "")
    if not m or not dogrulandi or not ben or not re.fullmatch(r"[^@]+@(" + m.group(1) + ")", ben): return False
    if yontem in ("get", "list"): return mevcut is not None and ben in (mevcut.get("okuyan") or [])
    if yontem == "create":
        return (set(yeni) <= set(ob.ALANLAR) and yeni.get("yazan") == ben and yeni.get("olay_id") == belge_id and isinstance(yeni.get("okuyan"), list) and len(yeni["okuyan"]) <= 50
                and ben in yeni["okuyan"] and isinstance(yeni.get("veri"), str) and len(yeni["veri"]) <= 20000 and zaman_esit)
    if yontem == "update":
        if mevcut is None or mevcut.get("yazan") != ben: return False
        fark = {k for k in set(mevcut) | set(yeni) if mevcut.get(k) != yeni.get(k)}
        return (fark <= {"okuyan", "guncel"} and isinstance(yeni.get("okuyan"), list) and len(yeni["okuyan"]) <= 50 and set(mevcut.get("okuyan") or []) <= set(yeni["okuyan"]) and zaman_esit)
    return False  # delete ve diğerleri
class Sahte:
    def __init__(s, bozuk_sina=False):
        s.kilit = threading.RLock(); s.port = bos_port(8790); s.istekler = []; s.belgeler = {}; s.kural = None; s.son_t = 0.0; s.sayac = 0
        s.kodlar = {}; s.yenileme = {}; s.iptal = set(); s.hizmetler = set(); s.db = False; s.indexler = []; s.apps = []; s.rulesetler = {}; s.release = None; s.islemler = {}
        s.bozuk_sina = bozuk_sina; s.sunucu = None; s.ac()
    def ac(s):
        sa = s
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self): sa.isle(self, "GET")
            def do_POST(self): sa.isle(self, "POST")
            def do_PATCH(self): sa.isle(self, "PATCH")
        class S(http.server.ThreadingHTTPServer): allow_reuse_address = True; daemon_threads = True
        s.sunucu = S(("127.0.0.1", s.port), H); threading.Thread(target=s.sunucu.serve_forever, daemon=True).start()
    def kapat(s): s.sunucu.shutdown(); s.sunucu.server_close()
    def kok(s): return f"http://127.0.0.1:{s.port}"
    def yenileme_ver(s, ep): t = f"fr.{_b64({'e': ep})}.{len(s.yenileme)}"; s.yenileme[t] = ep; return t
    def fb_belirtec(s, ep): s.sayac += 1; return f"h.{_b64({'email': ep, 'email_verified': True, 'exp': int(time.time()) + 3600, 'n': s.sayac})}.s"
    def hepsini_iptal(s): s.iptal = {"*"}
    def kural_yukle(s, metin): s.kural = metin; s.release = "rs0"; s.rulesetler["rs0"] = metin
    def tum_metin(s): return json.dumps(s.belgeler, ensure_ascii=False)
    def op(s, yanit, bekle=1): s.sayac += 1; ad = f"operations/op{s.sayac}"; s.islemler[ad] = {"bekle": bekle, "yanit": yanit}; return {"name": ad, "done": False}
    def yaz(s, h, kod, o):
        v = json.dumps(o).encode(); h.send_response(kod); h.send_header("Content-Type", "application/json"); h.send_header("Content-Length", str(len(v))); h.end_headers(); h.wfile.write(v)
    def hata(s, h, kod, durum): s.yaz(h, kod, {"error": {"code": kod, "status": durum, "message": durum}})
    def kimlik(s, h):  # Authorization: Bearer → (e-posta, kapsam, tür) ya da None; iptal edilmiş belirteç 401
        a = h.headers.get("Authorization") or ""
        if not a.startswith("Bearer "): return None
        t = a[7:]
        if "*" in s.iptal and t.startswith("h."): return None
        p = _yuk(t); return (p.get("email"), p.get("scope") or "", t[:2]) if p.get("email") else None
    def isle(s, h, yontem):
        with s.kilit: s.istekler.append((yontem, h.path.split("?")[0]))
        u = urllib.parse.urlparse(h.path); q = urllib.parse.parse_qs(u.query); n = int(h.headers.get("Content-Length") or 0); ham = h.rfile.read(n) if n else b""
        ct = h.headers.get("Content-Type") or ""
        try: govde = (dict(urllib.parse.parse_qsl(ham.decode())) if "x-www-form" in ct else json.loads(ham.decode() or "{}")) if ham else {}
        except ValueError: govde = {}
        parca = u.path.strip("/").split("/", 1); servis = parca[0]; yol = "/" + (parca[1] if len(parca) > 1 else "")
        with s.kilit:
            try: getattr(s, "s_" + servis)(h, yontem, yol, q, govde)
            except AttributeError as e: s.hata(h, 404, "NOT_FOUND " + str(e))
    # --- OAuth ve kimlik
    def s_yetki(s, h, yontem, yol, q, g):
        ip = (q.get("login_hint") or [""])[0]; kod = f"kod{len(s.kodlar)}"
        s.kodlar[kod] = {"e": ip, "ch": q["code_challenge"][0], "kapsam": q["scope"][0], "istemci": q["client_id"][0]}
        h.send_response(302); h.send_header("Location", f"{q['redirect_uri'][0]}?code={kod}&state={q['state'][0]}"); h.send_header("Content-Length", "0"); h.end_headers()
    def s_oauth(s, h, yontem, yol, q, g):
        k = s.kodlar.get(g.get("code"))
        if not k or g.get("client_id") != ISTEMCI or g.get("client_secret") != SIR: return s.hata(h, 401, "UNAUTHENTICATED")
        import hashlib
        if base64.urlsafe_b64encode(hashlib.sha256(g.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode() != k["ch"]: return s.hata(h, 400, "INVALID_GRANT")
        s.yaz(h, 200, {"access_token": "ga." + _b64({"email": k["e"], "scope": k["kapsam"]}) + ".s", "id_token": "g." + _b64({"email": k["e"]}) + ".s", "expires_in": 3599})
    def s_identitytoolkit(s, h, yontem, yol, q, g):
        if (q.get("key") or [""])[0] != APIK: return s.hata(h, 403, "PERMISSION_DENIED")
        m = re.search(r"id_token=([^&]+)", g.get("postBody", "")); ep = _yuk(m.group(1)).get("email") if m else None
        if not ep: return s.hata(h, 400, "INVALID_IDP_RESPONSE")
        s.yaz(h, 200, {"idToken": s.fb_belirtec(ep), "refreshToken": s.yenileme_ver(ep), "expiresIn": "3600", "email": ep})
    def s_securetoken(s, h, yontem, yol, q, g):
        ep = s.yenileme.get(g.get("refresh_token"))
        if (q.get("key") or [""])[0] != APIK or not ep or g.get("grant_type") != "refresh_token": return s.hata(h, 400, "INVALID_REFRESH_TOKEN")
        s.iptal.discard("*"); s.yaz(h, 200, {"id_token": s.fb_belirtec(ep), "refresh_token": g["refresh_token"], "expires_in": "3600", "user_id": "u"})
    # --- Firestore verisi
    def belge_json(s, i, d):
        f = {k: _tv(x) for k, x in d.items()}; return {"name": f"projects/{PROJE}/databases/(default)/documents/olaylar/{i}", "fields": f, "createTime": ob.ts_yaz(d["guncel"]), "updateTime": ob.ts_yaz(d["guncel"])}
    def s_firestore(s, h, yontem, yol, q, g):
        m = re.fullmatch(r"/v1/projects/([^/]+)/databases/\(default\)(.*)", yol)
        if not m:
            if yol.startswith("/v1/operations/"): return s.islem_yanit(h, yol[4:])
            m2 = re.fullmatch(r"/v1/projects/([^/]+)/databases", yol)
            if m2 and yontem == "POST": return s.admin(h, lambda: (setattr(s, "db", True), s.yaz(h, 200, s.op({}, 1)))) if s.admin_ok(h) else None
            return s.hata(h, 404, "NOT_FOUND")
        ek = m.group(2)
        if ek == "" and yontem == "GET": return (s.yaz(h, 200, {"name": "(default)"}) if s.db else s.hata(h, 404, "NOT_FOUND")) if s.admin_ok(h) else None
        if ek.startswith("/collectionGroups/olaylar/indexes"):
            if not s.admin_ok(h): return
            if yontem == "POST":
                s.indexler.append({"name": f"i{len(s.indexler)}", "queryScope": g["queryScope"], "fields": g["fields"] + [{"fieldPath": "__name__", "order": "ASCENDING"}], "state": "CREATING", "okuma": 0}); return s.yaz(h, 200, s.op({}, 0))
            for x in s.indexler:
                x["okuma"] += 1; x["state"] = "READY" if x["okuma"] > 1 else "CREATING"
            return s.yaz(h, 200, {"indexes": [{k: v for k, v in x.items() if k != "okuma"} for x in s.indexler]})
        k = s.kimlik(h)
        if not k or k[2] != "h.": return s.hata(h, 401, "UNAUTHENTICATED")
        ben = k[0]; dogru = True
        if ek == "/documents:commit": return s.commit(h, ben, dogru, g)
        if ek == "/documents:runQuery": return s.sorgu(h, ben, dogru, g)
        if ek == "/documents:batchGet":
            out = []
            for ad in g.get("documents") or []:
                i = ad.rsplit("/", 1)[1]; d = s.belgeler.get(i)
                if not kural_izin(s.kural, "get", ben, dogru, d, None, i, False): return s.hata(h, 403, "PERMISSION_DENIED")
                out.append({"found": s.belge_json(i, d)} if d else {"missing": ad})
            return s.yaz(h, 200, out)
        mm = re.fullmatch(r"/documents/olaylar/([^/]+)", ek)
        if mm and yontem == "GET":
            d = s.belgeler.get(mm.group(1))
            if not kural_izin(s.kural, "get", ben, dogru, d, None, mm.group(1), False): return s.hata(h, 403, "PERMISSION_DENIED")
            return s.yaz(h, 200, s.belge_json(mm.group(1), d))
        s.hata(h, 404, "NOT_FOUND")
    def commit(s, h, ben, dogru, g):
        yeni_t = max(time.time(), s.son_t + 1e-6); sec = {};
        for w in g.get("writes") or []:
            if "delete" in w:
                if not kural_izin(s.kural, "delete", ben, dogru, None, None, "", False): return s.hata(h, 403, "PERMISSION_DENIED")
                continue
            i = w["update"]["name"].rsplit("/", 1)[1]; f = {k: _ac(v) for k, v in (w["update"].get("fields") or {}).items()}; mevcut = sec.get(i) or s.belgeler.get(i); var = mevcut is not None
            on = (w.get("currentDocument") or {}).get("exists"); zaman = bool(w.get("updateTransforms"))
            if on is False and var: return s.hata(h, 409, "ALREADY_EXISTS")
            if on is True and not var: return s.hata(h, 404, "NOT_FOUND")
            if "updateMask" in w:
                yeni = dict(mevcut); yeni.update({k: f[k] for k in w["updateMask"]["fieldPaths"] if k in f}); yontem = "update"
            else: yeni = dict(f); yontem = "create"
            if zaman: yeni["guncel"] = yeni_t
            if not kural_izin(s.kural, yontem, ben, dogru, mevcut, yeni, i, zaman): return s.hata(h, 403, "PERMISSION_DENIED")
            sec[i] = yeni
        s.belgeler.update(sec); s.son_t = yeni_t; s.yaz(h, 200, {"writeResults": [{} for _ in g.get("writes") or []], "commitTime": ob.ts_yaz(yeni_t)})
    def sorgu(s, h, ben, dogru, g):
        sq = g["structuredQuery"]; w = sq.get("where") or {}; fl = w["compositeFilter"]["filters"] if "compositeFilter" in w else ([w] if w else []); ac = None; alt = None; esit = False
        for f in fl:
            ff = f["fieldFilter"]; ad = ff["field"]["fieldPath"]
            if ad == "okuyan" and ff["op"] == "ARRAY_CONTAINS": ac = ff["value"]["stringValue"]
            if ad == "guncel": alt = ob.ts_oku(ff["value"]["timestampValue"]); esit = ff["op"] == "GREATER_THAN_OR_EQUAL"
        # liste kuralı: sorgu "ben okuyanda" kısıtını kanıtlayamazsa tümü reddedilir (gerçek Firestore davranışı)
        if ac != ben or not kural_izin(s.kural, "list", ben, dogru, {"okuyan": [ben]}, None, "", False): return s.hata(h, 403, "PERMISSION_DENIED")
        rs = [(i, d) for i, d in s.belgeler.items() if ben in d["okuyan"] and (alt is None or (d["guncel"] >= alt if esit else d["guncel"] > alt))]
        rs.sort(key=lambda x: (x[1]["guncel"], x[0])); rs = rs[:int(sq.get("limit") or 1000)]
        s.yaz(h, 200, [{"document": s.belge_json(i, d), "readTime": ob.ts_yaz(time.time())} for i, d in rs] or [{"readTime": ob.ts_yaz(time.time())}])
    # --- yönetim uçları
    def admin_ok(s, h):
        k = s.kimlik(h)
        if not k or k[2] != "ga" or "cloud-platform" not in k[1] or not h.headers.get("X-Goog-User-Project"): s.hata(h, 403, "PERMISSION_DENIED"); return False
        return True
    def admin(s, h, f): return f()
    def islem_yanit(s, h, ad):
        o = s.islemler.get(ad)
        if not o: return s.hata(h, 404, "NOT_FOUND")
        if o["bekle"] > 0: o["bekle"] -= 1; return s.yaz(h, 200, {"name": ad, "done": False})
        s.yaz(h, 200, {"name": ad, "done": True, "response": o["yanit"]})
    def s_serviceusage(s, h, yontem, yol, q, g):
        if yol.startswith("/v1/operations/"): return s.islem_yanit(h, yol[4:])
        if not s.admin_ok(h): return
        m = re.fullmatch(r"/v1/projects/[^/]+/services/([^:]+)(:enable)?", yol)
        if m and yontem == "GET": return s.yaz(h, 200, {"state": "ENABLED" if m.group(1) in s.hizmetler else "DISABLED"})
        if m and m.group(2): s.hizmetler.add(m.group(1)); return s.yaz(h, 200, s.op({}, 1))
        s.hata(h, 404, "NOT_FOUND")
    def sina(s, g):
        metin = g["source"]["files"][0]["content"]; out = []
        for v in g["testSuite"]["testCases"]:
            r = v["request"]; t = r.get("auth", {}).get("token", {}); mevcut = (v.get("resource") or {}).get("data"); yeni = (r.get("resource") or {}).get("data")
            zaman_esit = yeni is not None and yeni.get("guncel") == r.get("time")
            iz = kural_izin(metin, r["method"], t.get("email"), t.get("email_verified"), mevcut, yeni, r["path"].rsplit("/", 1)[1], zaman_esit)
            ok = (iz == (v["expectation"] == "ALLOW")) != s.bozuk_sina
            out.append({"state": "SUCCESS" if ok else "FAILURE"})
        return {"testResults": out}
    def s_firebaserules(s, h, yontem, yol, q, g):
        if not s.admin_ok(h): return
        if yol.endswith(":test"): return s.yaz(h, 200, s.sina(g))
        if yol.endswith("/rulesets") and yontem == "POST":
            i = f"rs{len(s.rulesetler) + 1}"; s.rulesetler[i] = g["source"]["files"][0]["content"]; return s.yaz(h, 200, {"name": f"projects/{PROJE}/rulesets/{i}"})
        m = re.search(r"/rulesets/([^/]+)$", yol)
        if m and yontem == "GET": return s.yaz(h, 200, {"source": {"files": [{"name": "firestore.rules", "content": s.rulesetler[m.group(1)]}]}}) if m.group(1) in s.rulesetler else s.hata(h, 404, "NOT_FOUND")
        if yol.endswith("/releases/cloud.firestore"):
            if yontem == "GET": return s.yaz(h, 200, {"name": "rel", "rulesetName": f"projects/{PROJE}/rulesets/{s.release}"}) if s.release else s.hata(h, 404, "NOT_FOUND")
            if yontem == "PATCH": s.release = g["release"]["rulesetName"].rsplit("/", 1)[1]; s.kural = s.rulesetler[s.release]; return s.yaz(h, 200, {})
        if yol.endswith("/releases") and yontem == "POST": s.release = g["rulesetName"].rsplit("/", 1)[1]; s.kural = s.rulesetler[s.release]; return s.yaz(h, 200, {})
        s.hata(h, 404, "NOT_FOUND")
    def s_firebase(s, h, yontem, yol, q, g):
        if yol.startswith("/v1beta1/operations/"): return s.islem_yanit(h, yol[9:])
        if not s.admin_ok(h): return
        if yol.endswith("/webApps"):
            if yontem == "GET": return s.yaz(h, 200, {"apps": s.apps} if s.apps else {})
            s.apps.append({"appId": f"1:1:web:{len(s.apps)}", "displayName": g["displayName"]}); return s.yaz(h, 200, s.op(s.apps[-1], 1))
        m = re.search(r"/webApps/([^/]+)/config$", yol)
        if m: return s.yaz(h, 200, {"apiKey": APIK})
        s.hata(h, 404, "NOT_FOUND")

# ============================== sınama düzeneği ==========================================================================================================
srv = Sahte(); Z0 = os.path.join(T, "z-test"); os.makedirs(Z0)
# 0) koruma: SUFLOR_FS_KOK ve zincir klasörü olmadan modül hiçbir şey yapmaz (gerçek Google/Anahtar Zinciri'ne gidilemez)
ayar0 = os.path.join(T, "ayar0.json"); json.dump({"ortak_tasima": "firestore", "firestore_proje": PROJE, "firestore_istemci_id": ISTEMCI, "firestore_alanlar": [ALAN]}, open(ayar0, "w"))
envk = {k: v for k, v in os.environ.items() if not k.startswith("SUFLOR_FS_")}; envk.update(SUFLOR_FS_TEST="1", SUFLOR_AYAR=ayar0, PYTHONDONTWRITEBYTECODE="1")
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "ortak_bulut.py"), "giris"], env=envk, capture_output=True, text=True, timeout=30)
bak("koruma: SUFLOR_FS_KOK/zincir klasörü yoksa (deneme kipinde) modül durur, hiçbir istek gitmez", r.returncode == 1 and "test_koruma" in r.stderr and not srv.istekler, (r.returncode, r.stderr[-200:]))
envk["SUFLOR_FS_KOK"] = "http://example.com"; envk["SUFLOR_FS_ZINCIR_DIZIN"] = Z0
r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "ortak_bulut.py"), "giris"], env=envk, capture_output=True, text=True, timeout=30)
bak("koruma: kök yerel döngü adresi değilse durur", r.returncode == 1 and "test_koruma" in r.stderr, (r.returncode, r.stderr[-200:]))
os.environ.update(SUFLOR_FS_TEST="1", SUFLOR_FS_KOK=srv.kok(), SUFLOR_FS_ZINCIR_DIZIN=Z0, SUFLOR_FS_BEKLE="0.02")
srv.kural_yukle(ob.kurallar([ALAN]))

class Mac:
    def __init__(s, ad, kisi, ep, port, tasima="firestore", drive=None, sunucu=None, alanlar=None):
        s.ad = ad; s.kisi = kisi; s.ep = ep; s.srv = sunucu or srv; s.kok = os.path.join(T, ad); s.canli = os.path.join(s.kok, "canli"); os.makedirs(s.canli); s.port = port; s.zincir = os.path.join(s.kok, "zincir"); os.makedirs(s.zincir)
        for f in ("relay.py", "manifest.json", "yapi.py", "ortak_bulut.py"): shutil.copy(os.path.join(KOD, f), s.kok)
        for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(s.kok, d))
        s.ayar = os.path.join(s.kok, "ayar.json"); a = {"alan": "Deneme", "ad": kisi, "port": port, "uygulama": s.kok, "proje": s.kok, "ortak": s.kok, "eposta_kimlik": ep, "ortak_firestore_aralik_sn": 3600}
        if tasima == "firestore": a.update(ortak_tasima="firestore", firestore_proje=PROJE, firestore_istemci_id=ISTEMCI, firestore_alanlar=alanlar or [ALAN])
        if drive: a["ortak_klasor"] = drive
        json.dump(a, open(s.ayar, "w"))
    def giris_ver(s, ep=None, api=True):  # Anahtar Zinciri yerine düz dosyalar: yenileme belirteci + API anahtarı + sır
        open(os.path.join(s.zincir, ob.ORTAK_OGE["yenileme"]), "w").write(s.srv.yenileme_ver(ep or s.ep))
        if api: open(os.path.join(s.zincir, ob.ORTAK_OGE["api"]), "w").write(APIK)
        open(os.path.join(s.zincir, ob.ORTAK_OGE["sir"]), "w").write(SIR)
    def env(s): return dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=s.ayar, SUFLOR_TEST_BASLAT="1", SUFLOR_FS_KOK=s.srv.kok(), SUFLOR_FS_ZINCIR_DIZIN=s.zincir, SUFLOR_FS_TEST="1", SUFLOR_FS_BEKLE="0.02")
    def baslat(s):
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.canli, "--port", str(s.port)], cwd=s.kok, stdout=open(os.path.join(s.kok, "relay.log"), "w"), stderr=subprocess.STDOUT, env=s.env())
        for _ in range(100):
            if "çalışıyor" in s.log(): return
            time.sleep(0.1)
    def log(s):
        try: return open(os.path.join(s.kok, "relay.log"), encoding="utf-8").read()
        except OSError: return ""
    def istek(s, yol, govde=None):
        k = open(os.path.join(s.canli, "kart-anahtari.txt")).read().strip()
        q = urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                                   headers={"X-Suflor-Anahtar": k, "Origin": f"http://127.0.0.1:{s.port}", "Content-Type": "application/json"})
        try: return json.loads(urllib.request.urlopen(q, timeout=30).read())
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    def esitle(s): return s.istek("/ortak", {"islem": "esitle"})
    def yaz(s, top, baslik, ogeler, gizli=False):
        open(os.path.join(s.canli, top + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {top}\n\n" + BAS + ("| 14:00:01 | **GİZLİ** | açıldı | |\n" if gizli else "| 14:00:01 | X | merhaba | |\n"))
        os.environ["SUFLOR_AYAR"] = s.ayar; yapi.graf_yaz(s.canli, {"baslik": baslik, "tarih": top[:10], "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    def kayit(s, metin): return next((x for x in s.istek("/kayitlar?deneme=1")["kayitlar"] if x["metin"] == metin), None)
    def olay_say(s):
        c = sqlite3.connect(os.path.join(s.canli, "karar-grafi.sqlite"))
        try: return c.execute("SELECT COUNT(*), COUNT(DISTINCT olay_id) FROM olay").fetchone()
        finally: c.close()
    def cli(s, *arg, env_ek=None):
        e = s.env(); e.update(env_ek or {})
        return subprocess.run([sys.executable, "-B", os.path.join(s.kok, "ortak_bulut.py"), *arg], cwd=s.kok, env=e, capture_output=True, text=True, timeout=120)
def say(ep=None): return {i for i, d in srv.belgeler.items() if ep is None or d["yazan"] == ep}

PA, PB, PC = bos_port(8801), bos_port(8802), bos_port(8803); PB = bos_port(PA + 1) if PB == PA else PB
macler = []
def yeni(*a, **k): m = Mac(*a, **k); macler.append(m); return m
A = yeni("a", "Ayşe Deneme", EA, PA); B = yeni("b", "Bora Kaya", EB, PB); C = yeni("c", "Can Örnek", EC, PC)
for m in (A, B, C): m.giris_ver()
try:
    A.yaz(M_ESKI, "Eski toplantı", [{"tur": "is", "metin": "Ayar öncesi eski iş", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-20"}])  # ilk Firestore turundan önceki kayıt: gitmemeli
    for m in (A, B, C): m.baslat()
    bak("üç aktarıcı açıldı", all("çalışıyor" in m.log() for m in (A, B, C)), [m.log()[-300:] for m in (A, B, C)])
    # --- (1) A'da toplantı: karar + A'dan B'ye ve C'ye iş; gizli ve deneme toplantıları
    v = A.esitle()
    bak("A: /ortak taşıma firestore, giriş var, kimlik şirket e-postası, durum ok", v.get("tasima") == "firestore" and v["firestore"]["giris"] is True and v.get("durum") == "ok" and v.get("kimlik") == EA and v["firestore"]["proje"] == PROJE, v)
    bak("ilk tur belge yazmaz (ayar öncesi kayıt gitmez)", not srv.belgeler and "Ayar öncesi" not in srv.tum_metin())
    A.yaz(M_NORMAL, "Haftalık Plan", [{"tur": "karar", "metin": "Bütçe 120 bin olarak kalıyor", "kim": "Ayşe Deneme", "saat": "14:02:00", "alinti": "yuz yirmide kalalim dedik", "netlik": "acik"},
                                     {"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-12", "saat": "14:05:00"},
                                     {"tur": "is", "metin": "Tedarikçiyi ara", "sahip": "Can Örnek", "sahip_eposta": EC, "tarih": "2026-11-13"},
                                     {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Deneme"}])
    A.yaz(M_GIZLI, "Bütçe özel görüşme", [{"tur": "karar", "metin": "GIZLIKARAR maaş artışı yüzde on", "kim": "Ayşe Deneme", "netlik": "acik"}, {"tur": "is", "metin": "GIZLIIS kadro planı", "sahip": "Bora Kaya", "sahip_eposta": EB}], gizli=True)
    A.yaz(M_DENEME, "Deneme toplantısı", [{"tur": "karar", "metin": "DENEMEKARAR deneme kararı", "kim": "Ayşe Deneme", "netlik": "acik"}])
    kt = A.kayit("Teklifi revize et"); yapi.yorum_ekle(A.canli, kt["kayit_id"], "CLAUDEYORUM hazırlık notu", yazan=EA, uretici="claude"); yapi.yorum_ekle(A.canli, kt["kayit_id"], "NORMALYORUM bir yorum", yazan=EA)
    v = A.esitle(); d = srv.tum_metin(); at = (v.get("son_tur") or {}).get("atlanan", {})
    bak("(4) gizli toplantıdan olay 0, deneme toplantısından 0, Claude yorumu 0; normal yorum gider", "GIZLIKARAR" not in d and "GIZLIIS" not in d and "DENEMEKARAR" not in d and "CLAUDEYORUM" not in d and "NORMALYORUM" in d, v.get("son_tur"))
    bak("(4) atlananlar sayıldı (gizli 2, deneme 1, claude 1) ve ayar öncesi kayıt gitmedi", at.get("gizli") == 2 and at.get("deneme") == 1 and at.get("claude") == 1 and "Ayar öncesi" not in d, at)
    bak("alıntı, iddia, döküm gitmez; belge alanları tasarımdaki gibi", "yuz yirmide" not in d and "Geçen yıl 95 bin" not in d and "merhaba" not in d and all(set(x) == set(ob.ALANLAR) for x in srv.belgeler.values()))
    kd = next(x for x in srv.belgeler.values() if "Bütçe 120 bin" in x["veri"]); ki = next(x for x in srv.belgeler.values() if "Teklifi revize et" in x["veri"] and x["tur"] == "kayit_olustu")
    bak("okuyan: iş kaydı yazan + sahip (+ kimse fazla), karar yalnız yazan; yazan = oturum e-postası; guncel sunucu zamanı",
        sorted(ki["okuyan"]) == sorted([EA, EB]) and kd["okuyan"] == [EA] and all(x["yazan"] == EA and abs(x["guncel"] - time.time()) < 60 for x in srv.belgeler.values()), (ki["okuyan"], kd["okuyan"]))
    # --- (1) B alır
    v = B.esitle()
    bak("(1) B bir turda A'nın B'ye atadığı işi alır (karar ve C'nin işi gelmez)", B.kayit("Teklifi revize et") is not None and B.kayit("Bütçe 120 bin olarak kalıyor") is None and B.kayit("Tedarikçiyi ara") is None and v["son_tur"]["cift"] == 0, v.get("son_tur"))
    bk = B.kayit("Teklifi revize et")
    bak("(1) 'Sana atandı' (atayan A) ve Bugün'de görünür", bk.get("atayan") == "Ayşe Deneme" and bk.get("kendi") is True and any(x["metin"] == "Teklifi revize et" and x.get("atayan") == "Ayşe Deneme" for x in B.istek("/bugun-veri")["kendi"]), bk)
    bak("(1) B'nin /ortak görünümü: gecikme ölçüldü (ortanca/p90 sayı), kişiler A", v["firestore"]["gecikme_ortanca"] is not None and v["firestore"]["gecikme_p90"] is not None and v.get("kisiler") == [EA], v.get("firestore"))
    # --- (1) B durum değişikliği → A
    r = B.istek("/is-durum", {"id": bk["id"], "durum": "yapildi"}); B.esitle(); v = A.esitle()
    bak("(1) A'da durum değişikliği B'ye, B'de yapıldı A'ya gider (iş A'da kapandı)", r.get("ok") is True and A.kayit("Teklifi revize et")["durum"] == "kapandi" and v.get("alinan") == 1, (r, v.get("alinan")))
    srv.hepsini_iptal(); v = B.esitle()
    bak("belirteç sunucuca geçersiz kılınınca (401) bir kez yenilenir ve tur başarılı", v.get("durum") == "ok" and not v.get("hata"), v)
    # --- (2) rolü olmayan F: doğrudan REST
    Zf = os.path.join(T, "z-f"); os.makedirs(Zf); os.environ["SUFLOR_FS_ZINCIR_DIZIN"] = Zf
    open(os.path.join(Zf, ob.ORTAK_OGE["yenileme"]), "w").write(srv.yenileme_ver(EF)); open(os.path.join(Zf, ob.ORTAK_OGE["api"]), "w").write(APIK)
    bF = ob.baglam({"firestore_proje": PROJE, "firestore_alanlar": [ALAN]}); sorgu = lambda ep, k=None: ob._fs(bF, "POST", "/documents:runQuery", ob._sorgu(bF, ep, 0, False))
    kod, o = sorgu(EF); belge_say = lambda o: sum(1 for x in o if x.get("document"))
    bak("(2) rolü olmayan F: kendi adına runQuery → 200, hiçbir belge yok", kod == 200 and belge_say(o) == 0 and len(srv.belgeler) > 0, (kod, o))
    kod, o = sorgu(EA); bak("(2) F başkasının (A) adına sorgu → 403", kod == 403, kod)
    ilk_id = next(iter(srv.belgeler)); kod, o = ob._fs(bF, "GET", f"/documents/olaylar/{ilk_id}")
    bak("(2) F belgeyi doğrudan get edince 403", kod == 403, kod)
    kod, o = ob._fs(bF, "POST", "/documents:runQuery", {"structuredQuery": {"from": [{"collectionId": "olaylar"}], "limit": 5}})
    bak("(2) filtresiz list → 403", kod == 403, kod)
    kod, o = ob._fs(bF, "POST", "/documents:batchGet", {"documents": [ob._isim(bF, ilk_id)]}); bak("(2) batchGet ile okuma → 403", kod == 403, kod)
    # --- (3) başkası adına yazma, silme, okuyan küçültme
    ham = {k: srv.belgeler[ilk_id][k] for k in ob.ALANLAR if k != "guncel"}
    def yaz_dene(**ek):
        s = dict(ham, **ek); s["olay_id"] = ek.get("olay_id", "YENIOLAY0000000000000000A1")
        return ob._fs(bF, "POST", "/documents:commit", {"writes": [ob._belge(bF, {k: s[k] for k in s if k != "okuyan"} | {"veri": json.loads(s["veri"])}, s["okuyan"])]})[0]
    bak("(3) F, yazan = A diyerek yazamaz (403)", yaz_dene(yazan=EA, okuyan=[EA, EF]) == 403)
    bak("(3) F, okuyanında kendisi olmadan yazamaz (403)", yaz_dene(yazan=EF, okuyan=[EA]) == 403)
    bak("(3) F, kendi adına doğru biçimde yazabilir (200); aynı belge ikinci kez 409", yaz_dene(yazan=EF, okuyan=[EF], cihaz="c-ffffffffffff") == 200 and yaz_dene(yazan=EF, okuyan=[EF], cihaz="c-ffffffffffff") == 409)
    kod, o = ob._fs(bF, "POST", "/documents:commit", {"writes": [{"delete": ob._isim(bF, "YENIOLAY0000000000000000A1")}]}); bak("(3) silme reddedilir (kendi belgesi bile)", kod == 403, kod)
    kod, o = ob._fs(bF, "POST", "/documents:commit", {"writes": [ob._yama(bF, ilk_id, [EA, EF])]}); bak("(3) başkasının belgesini güncelleyemez; okuyan'a kendini ekleyemez (403)", kod == 403, kod)
    kod, o = ob._fs(bF, "POST", "/documents:commit", {"writes": [ob._yama(bF, "YENIOLAY0000000000000000A1", [EF, EB])]}); bak("(3) kendi belgesinde okuyan genişletebilir (200)", kod == 200, kod)
    kod, o = ob._fs(bF, "POST", "/documents:commit", {"writes": [ob._yama(bF, "YENIOLAY0000000000000000A1", [EF])]}); bak("(3) okuyan küçülemez (403)", kod == 403, kod)
    del srv.belgeler["YENIOLAY0000000000000000A1"]
    # --- (5) okuyan genişleme: C sonradan role eklenir, eski olayları görür
    A.yaz(M_NORMAL.replace("1400", "1800"), "Ek toplantı", [{"tur": "is", "metin": "Ek iş kimseye açık değil", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-18"}])
    A.esitle(); C.esitle()
    ek = A.kayit("Ek iş kimseye açık değil"); yapi.metin_duzelt(A.canli, ek["kayit_id"], "Ek iş sonradan genişledi", yazan=EA)
    bak("(5) rol eklenmeden C kaydı görmez", C.kayit("Ek iş kimseye açık değil") is None and C.kayit("Ek iş sonradan genişledi") is None)
    yapi.ata(A.canli, ek["kayit_id"], {"onaylayan": {"ad": "Can Örnek", "eposta": EC}}, yazan=EA)
    v = A.esitle()
    eskiler = [x for x in srv.belgeler.values() if x["kayit_id"] == ek["kayit_id"]]
    bak("(5) A'nın eski olaylarının okuyan'ı C'yi içerecek şekilde genişledi (kayit_olustu dahil)", len(eskiler) >= 3 and all(EC in x["okuyan"] and EB in x["okuyan"] and EA in x["okuyan"] for x in eskiler), [x["okuyan"] for x in eskiler])
    v = C.esitle(); ck = C.kayit("Ek iş sonradan genişledi")
    bak("(5) C eski olayları da görür: kayıt metni (sonraki düzeltme) ve rolü tam", ck is not None and v["son_tur"]["bozuk"] == 0, (ck, v.get("son_tur")))
    sa, sc = A.olay_say(), C.olay_say(); A.esitle(); C.esitle()
    bak("(5) tekrar turlarında çift olay 0 (olay_id'ler tekil)", A.olay_say() == sa and C.olay_say() == sc and sc[0] == sc[1], (sa, sc))
    # --- (6) sunucu kapalıyken bekler, açılınca gider, çift 0
    srv.kapat(); belge_once = len(srv.belgeler)
    A.yaz(M_NORMAL.replace("1400", "1900"), "Kapalı sunucu", [{"tur": "is", "metin": "Kapalıyken yazılan iş", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-19"}])
    v = A.esitle()
    bak("(6) sunucu kapalı: durum ag_yok, hata sınıfı ag, hiçbir şey gitmedi, yerel kayıt var", v.get("durum") == "ag_yok" and v["firestore"]["son_hata"] == "ag" and len(srv.belgeler) == belge_once and A.kayit("Kapalıyken yazılan iş") is not None, v)
    srv.ac(); v = A.esitle()
    bak("(6) sunucu açılınca bekleyen olaylar gider (durum ok)", v.get("durum") == "ok" and any("Kapalıyken yazılan iş" in x["veri"] for x in srv.belgeler.values()), v)
    n1 = len(srv.belgeler); A.esitle(); A.esitle(); B.esitle()
    bak("(6) tekrar turlarında Firestore'a çift belge yok; B bekleyen işi aldı", len(srv.belgeler) == n1 and B.kayit("Kapalıyken yazılan iş") is not None and B.olay_say()[0] == B.olay_say()[1])
    # --- (8) kişisel posta ve alan dışı: hiçbir istek gitmez
    PD, PE = bos_port(8820), bos_port(8830)
    Dm = yeni("d", "Deniz Dış", ED, PD); Em = yeni("e", "Eda Kişisel", EGM, PE, alanlar=["gmail.com"])
    for m in (Dm, Em): m.giris_ver(); m.baslat()
    n_ist = len(srv.istekler); vd = Dm.esitle(); ve = Em.esitle()
    bak("(8) alan adı listesi dışı kimlik: durum alan_disi, sunucuya hiçbir istek yok", vd.get("durum") == "alan_disi" and len(srv.istekler) == n_ist, (vd.get("durum"), len(srv.istekler) - n_ist))
    bak("(8) kişisel posta adresi (alan listesinde gmail olsa bile): hiçbir istek yok", ve.get("durum") in ("kimlik_yok", "alan_disi", "ayar_eksik") and len(srv.istekler) == n_ist, (ve.get("durum"), len(srv.istekler) - n_ist))
    bak("(8) kişisel alan adı kurallara/ayara alınmaz", all(not ob.alan_gecerli(x) for x in ("gmail.com", "outlook.com")) and not ob.alan_izinli(EGM, ["gmail.com"]))
    # --- (8b) deneme aktarıcısı (canli klasörü ayardakinden farklı → teshis.DENEME): gerçek ayar Firestore'u gösterse de hiçbir istek gitmez
    Fm = yeni("f", "Fikret Deneme", EA, bos_port(8840)); Fm.giris_ver(); Fm.canli = os.path.join(Fm.kok, "deneme-canli"); os.makedirs(Fm.canli); Fm.baslat()
    n_ist = len(srv.istekler); vf = Fm.esitle(); time.sleep(0.5)
    bak("(8b) deneme aktarıcısı paylaşmaz: durum deneme, sunucuya hiçbir istek yok", vf.get("durum") == "deneme" and len(srv.istekler) == n_ist, (vf.get("durum"), len(srv.istekler) - n_ist))
    # --- (7) Drive klasöründen taşıma
    DG = os.path.join(T, "DriveG", "Ortak"); os.makedirs(DG); PG = bos_port(8840)
    G = yeni("g", "Gül Yazar", EG, PG, tasima="drive", drive=DG); G.giris_ver(); G.baslat()
    G.yaz(M_ESKI, "Gül eski", [{"tur": "is", "metin": "Gül eski iş", "sahip": "Gül Yazar", "tarih": "2026-11-21"}])
    G.esitle(); json.dump(dict(json.load(open(G.ayar)), ortak_klasor=DG), open(G.ayar, "w")); G.esitle()  # ilk tur başlangıcı ayarlar; ardından yeni kayıtlar Drive'a yazılır
    G.yaz(M_NORMAL, "Gül toplantı", [{"tur": "is", "metin": "Gül birinci iş", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-12"}, {"tur": "karar", "metin": "Gül kararı", "kim": "Gül Yazar", "netlik": "acik"},
                                     {"tur": "is", "metin": "Gül ikinci iş", "sahip": "Can Örnek", "sahip_eposta": EC}])
    G.yaz(M_GIZLI, "Gül özel", [{"tur": "karar", "metin": "GULGIZLI", "kim": "Gül Yazar", "netlik": "acik"}], gizli=True)
    G.esitle(); satir = [json.loads(l) for k, _, fs in os.walk(DG) for f in fs for l in open(os.path.join(k, f), encoding="utf-8") if l.strip()]
    ayg = json.load(open(G.ayar)); ayg.update(ortak_tasima="firestore", firestore_proje=PROJE, firestore_istemci_id=ISTEMCI, firestore_alanlar=[ALAN]); json.dump(ayg, open(G.ayar, "w"))
    r = G.cli("tasi", "--klasor", DG, "--dizin", G.canli); sd = say(EG); idler = {x["olay_id"] for x in satir}
    bak("(7) tasi: Drive'daki olay sayısı = Firestore'dakiler, eksik 0, çıkış 0", r.returncode == 0 and f"Drive: {len(idler)} olay · Firestore'da: {len(idler)} · eksik: 0" in r.stdout and sd == idler and len(idler) >= 3, (r.returncode, r.stdout[-300:], r.stderr[-200:]))
    r2 = G.cli("tasi", "--klasor", DG, "--dizin", G.canli)
    bak("(7) ikinci taşımada çift 0 (hepsi zaten vardı), sayı aynı", r2.returncode == 0 and "Yazıldı: 0" in r2.stdout and f"zaten vardı: {len(idler)}" in r2.stdout and say(EG) == idler, r2.stdout[-300:])
    n1 = len(srv.belgeler); vg = G.esitle()
    bak("(7) taşımadan sonra normal tur: aynı olaylar tekrar gitmez (belge sayısı aynı)", vg.get("durum") == "ok" and len(srv.belgeler) == n1 and "GULGIZLI" not in srv.tum_metin(), vg.get("durum"))
    vb = B.esitle(); gb = B.kayit("Gül birinci iş")
    bak("(7) B taşınan işi alır (okuyan B'yi içerir)", gb is not None and B.kayit("Gül kararı") is None, vb.get("son_tur"))
    # --- (11/12) görünüm ve kural metni
    v = A.istek("/ortak")
    bak("(11) /ortak firestore bloğu: proje, giriş, e-posta, gecikme alanları; metin/ad yok", set(v["firestore"]) == {"proje", "giris", "eposta", "gecikme_ortanca", "gecikme_p90", "son_hata"} and v["firestore"]["eposta"] == EA, v.get("firestore"))
    b1 = B.istek("/ortak")
    bak("(11) gecikme ortanca ≥ 0 ve p90 ≥ ortanca", b1["firestore"]["gecikme_ortanca"] >= 0 and b1["firestore"]["gecikme_p90"] >= b1["firestore"]["gecikme_ortanca"], b1["firestore"])
    kt = ob.kurallar(["ornek.test", "b-ornek.example"]); m = re.search(r"matches\('([^']*)'\)", kt)
    bak("(12) kurallar metni alan adını kaçışlı içerir ([.]), kaçışsız nokta yok", m is not None and "ornek[.]test|b-ornek[.]example" in m.group(1) and "ornek.test" not in kt and "allow delete: if false" in kt, m and m.group(1))
    try: ob.kurallar(["a.com') || true || ('"]); gecti = False
    except ob.FsHata: gecti = True
    try: ob.kurallar(["gmail.com"]); gecti2 = False
    except ob.FsHata: gecti2 = True
    bak("(12) kural enjeksiyonu ve kişisel alan adı reddedilir", gecti and gecti2)
    # --- (9) kur: baştan sona, idempotent; (10) davet → katıl
    srv2 = Sahte(bozuk_sina=True); PH = bos_port(8860)
    H = yeni("h", "Yönetici Han", EY, PH, tasima="yok", sunucu=srv2); open(os.path.join(H.zincir, ob.ORTAK_OGE["sir"]), "w").write(SIR)
    ekk = {"SUFLOR_FS_GIRIS_IPUCU": EY}
    r = H.cli("kur", "--proje", PROJE, "--istemci", ISTEMCI, "--alan", ALAN, env_ek=ekk)
    bak("(9) kur: kural sınaması beklenmeyen çıkarsa çıkış 1 ve kurallar yayınlanmaz", r.returncode == 1 and srv2.release is None and "beklenmeyen" in r.stderr, (r.returncode, r.stderr[-300:]))
    srv2.bozuk_sina = False; r = H.cli("kur", "--proje", PROJE, "--istemci", ISTEMCI, "--alan", ALAN, env_ek=ekk); ay = json.load(open(H.ayar))
    bak("(9) kur baştan sona: 4 servis, veritabanı, READY dizin, kurallar, web uygulaması, ayar, giriş", r.returncode == 0 and len(srv2.hizmetler) == 4 and srv2.db and [x["state"] for x in srv2.indexler] == ["READY"] and srv2.kural == ob.kurallar([ALAN])
        and len(srv2.apps) == 1 and open(os.path.join(H.zincir, ob.ORTAK_OGE["api"])).read() == APIK and os.path.exists(os.path.join(H.zincir, ob.ORTAK_OGE["yenileme"])), (r.returncode, r.stdout[-500:], r.stderr[-300:]))
    bak("(9) kur ayarı oku-değiştir-yaz: yeni anahtarlar yazıldı, ad/eposta_kimlik korundu", ay.get("ortak_tasima") == "firestore" and ay.get("firestore_proje") == PROJE and ay.get("firestore_istemci_id") == ISTEMCI and ay.get("firestore_alanlar") == [ALAN] and ay.get("ad") == "Yönetici Han" and ay.get("eposta_kimlik") == EY, ay)
    bak("(9) kur kuralları sınadı (sert maddeler ✓) ve Türkçe ilerleme satırları yazdı", "✓ DENY · rolü olmayan aynı alan adlı get" in r.stdout and "8/8" in r.stdout and "Kurulum tamam." in r.stdout, r.stdout[-400:])
    nr, na, ni, nh = len(srv2.rulesetler), len(srv2.apps), len(srv2.indexler), len(srv2.hizmetler); r = H.cli("kur", "--proje", PROJE, "--istemci", ISTEMCI, "--alan", ALAN, env_ek=ekk)
    bak("(9) ikinci kur idempotent: yeni kural seti/web uygulaması/dizin yok, çıkış 0", r.returncode == 0 and (len(srv2.rulesetler), len(srv2.apps), len(srv2.indexler), len(srv2.hizmetler)) == (nr, na, ni, nh) and "zaten güncel" in r.stdout, (r.stdout[-400:], r.stderr[-200:]))
    r = H.cli("davet"); kod = r.stdout.strip(); cozum = json.loads(base64.urlsafe_b64decode(kod + "=" * (-len(kod) % 4))) if r.returncode == 0 and kod else {}
    bak("(10) davet: tek satır kod, dosyaya yazılmadı", r.returncode == 0 and "\n" not in kod and cozum.get("proje") == PROJE and cozum.get("alanlar") == [ALAN] and not any(kod in open(os.path.join(k, f), errors="replace").read() for k, _, fs in os.walk(H.kok) for f in fs if f.endswith((".json", ".log"))), r.stderr[-200:])
    PI = bos_port(8870); I = yeni("i", "Ilgaz Yeni", "ilgaz" + AT + ALAN, PI, tasima="yok", sunucu=srv2)
    r = I.cli("katil", kod, env_ek={"SUFLOR_FS_GIRIS_IPUCU": "ilgaz" + AT + ALAN}); ai = json.load(open(I.ayar)); rd = I.cli("durum", "--dizin", I.canli)
    bak("(10) katıl: sır+api+yenileme Anahtar Zinciri'ne, ayar yazıldı, giriş tamam, durum 'giris: True'", r.returncode == 0 and open(os.path.join(I.zincir, ob.ORTAK_OGE["sir"])).read() == SIR and open(os.path.join(I.zincir, ob.ORTAK_OGE["api"])).read() == APIK
        and os.path.exists(os.path.join(I.zincir, ob.ORTAK_OGE["yenileme"])) and ai.get("firestore_proje") == PROJE and ai.get("ortak_tasima") == "firestore" and "giris: True" in rd.stdout and "durum: hazir" in rd.stdout, (r.returncode, r.stderr[-300:], rd.stdout))
    ai0 = dict(ai); r = I.cli("katil", "bozukkod", env_ek={"SUFLOR_FS_GIRIS_IPUCU": "ilgaz" + AT + ALAN})
    bak("(10) bozuk davet kodu reddedilir, ayar değişmez", r.returncode == 1 and json.load(open(I.ayar)) == ai0, r.stderr[-200:])
    r = I.cli("katil", kod, env_ek={"SUFLOR_FS_GIRIS_IPUCU": "disari" + AT + "baska.example"})
    bak("(10) alan adı dışı hesapla giriş reddedilir (belirteç saklanmaz)", r.returncode == 1 and "alan" in r.stderr, (r.returncode, r.stderr[-200:]))
    # --- uçtan uca: iki yalıtılmış aktarıcıda günlük/log sızıntısı ve hata
    gunluk = A.log() + B.log() + C.log() + G.log()
    bak("günlüğe yalnız sayı ve hata sınıfı (metin, ad, e-posta, belirteç yok)", "ORTAK (firestore)" in gunluk and "Teklifi" not in gunluk and "Bütçe" not in gunluk and AT + ALAN not in gunluk and "idToken" not in gunluk, gunluk[-600:])
    bak("gerçek Google'a ve gerçek Anahtar Zinciri'ne gidilmedi (tüm istekler sahte sunucuda)", all(not i[1].startswith("http") for i in srv.istekler) and len(srv.istekler) > 20)
    bak("teshis KOD_DOSYALARI ve kurulum KOPYA listesinde ortak_bulut.py", '"ortak_bulut.py"' in open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read() and '"ortak_bulut.py"' in open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read())
    bak("aktarıcılar hatasız", "Traceback" not in "".join(m.log() for m in macler), "".join(m.log() for m in macler)[-1500:])
finally:
    for m in macler:
        try: m.p.terminate(); m.p.wait(5)
        except Exception: pass
    for s_ in (srv, globals().get('srv2')):
        try: s_ and s_.kapat()
        except Exception: pass
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not hata else 'KALDI: ' + str(len(hata))}"); sys.exit(1 if hata else 0)
