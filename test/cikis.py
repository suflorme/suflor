#!/usr/bin/env python3
# Dış çıkış kapısı (19 Kasım 2026; aktarici/cikis.py cikis_izin, aktarici/web-kapi.py web metin kapısı; mimari denetim 4 B2–B4, R1/R5).
#   1) Durağan (AST): relay.py, aktarici/*.py ve kök *.py içindeki her ağ çağrısı (urlopen, HTTP(S)Connection, create_connection, requests, curl/gh alt süreci) aynı işlevde
#      (ya da onu saran işlevde) cikis_izin'i — doğrudan ya da aynı dosyadaki bir kapı işlevi üzerinden — soruyor; değilse İSTİSNA listesinde gerekçesiyle duruyor.
#      Ağa modül/alt süreç üzerinden çıkan bölüm işlevleri (Firestore, Tazı, Anımsatıcılar, toplantıya ses, toplantı oturumunun web izni) GEREKLI_KAPI listesinde.
#      Yönlendirilen dosyalarda "gizli_acik yoksa engelleme" (fail-open) kalıbı kalmamış.
#   2) Birim: web metin kapısı (kurgu adlar ve döküm): uzunluk, e-posta, uzun sayı, iç kişi adı, dış katılımcı serbest (S208), 6 sözcüklük alıntı; adres yolu.
#   3) Gizli kip: cikis_izin her hedefte ret, yalnız beta teknik sayaçları geçer; kapı yoksa / gizli_acik yoksa / hata verirse gizli (fail-closed); bilinmeyen hedef ret.
#      teshis.cikis_izin ve tazi_cikis tek başına (gizli.json) fail-closed; Konuş kancası (ayrı süreç) gizli/klasör yok/bozuk süzgeçte reddeder, süzgeçteki adı yakalar.
#      Bölüm düzeyi: gemini-ses (gizli kipte istek atılmaz), sozluk-hakem _hk_istek, basecamp _bc_http.
# Ağ yok, port açılmaz, gerçek servis çağrılmaz. Kurgu veri.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/cikis.py      (kaldı → çıkış 1)
import ast, glob, json, os, re, subprocess, sys, tempfile, threading, time
AT = "@"  # yayın taraması e-posta biçimini yakalamasın (diğer testler gibi)
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
def oku(y): return open(os.path.join(KOD, y), encoding="utf-8").read()

# --- 1) Durağan ------------------------------------------------------------------------------------------------------------------------------------------------
AG = {"urlopen", "HTTPSConnection", "HTTPConnection", "create_connection"}
ISTISNA = {  # (dosya, işlev) → neden: kapı gerekmeyen ya da başka kapıdan geçen ağ çağrısı
    ("aktarici/beyin.py", "_ac"): "model sağlayıcısı (S146): model çağrısı kapi.py kapi_model'den geçer (test/gizli-kapi.py)",
    ("basecamp-baglan.py", "http"): "tek seferlik OAuth kurulum komutu (kullanıcı Terminal'de çalıştırır; aktarıcı dışı)",
    ("basecamp-baglan.py", "proje_say"): "tek seferlik OAuth kurulum komutu (yalnız okuma)",
    ("ortak_bulut.py", "_http"): "Firestore modülü: aktarıcıda tek çağıran ortak-klasor.py _ort_firestore (GEREKLI_KAPI); tek başına giris/kur komutu kullanıcıdan",
    ("relay.py", "_guncelleme_dongu"): "yalnız GET yayin.json / manifest.json (veri gitmez); relay.py bu dalgada başka oturumda",
    ("whisper-isci.py", "__init__"): "yerel whisper-server (127.0.0.1)", ("whisper-isci.py", "istek"): "yerel whisper-server (127.0.0.1)",
    ("toplanti-claude.py", "geri_bildirim_cmd"): "gh issue list / auth token: yalnız okuma, içerik gitmez",
    ("toplanti-claude.py", "rapor_cmd"): "gh issue create: gb_gizli (fail-closed) + teshis.sade süzgeci (aşağıda ayrıca denetlenir)",
}
ISTISNA_DOSYA = {
    "kurulum.py": "kurulum/güncelleme: imzalı ya da SHA-256 sabit indirme ve yerel aktarıcı yoklaması; kullanıcı içeriği gitmez",
    "toplanti-claude.py": "A.relay (127.0.0.1) yerel aktarıcı uçları; dış çıkış yalnız gh (yukarıda)",
}
GEREKLI_KAPI = {  # ağa modül/alt süreç/yardımcı uygulama üzerinden çıkan bölüm işlevleri: gövdede cikis_izin (ya da aynı dosyadaki kapı işlevi)
    ("aktarici/ortak-klasor.py", "_ort_firestore"), ("aktarici/tazi-istemci.py", "tazi_cagir"), ("aktarici/animsatici.py", "_anim_yardimci"),
    ("aktarici/toplantiya-ses.py", "toplantiya_soyle"), ("aktarici/toplanti-oturum.py", "_topo_web_red"), ("teshis.py", "gonder"), ("teshis.py", "_bekleyenleri_gonder"),
    ("aktarici/gemini-ses.py", "_gemini_oku"), ("aktarici/gemini-ses.py", "gemini_onceden"), ("aktarici/saglayici.py", "sg_anahtar_dene"),
}
EK_KAPI = {("toplanti-claude.py", "gb_gizli")}  # cikis_izin adını taşımayan ama aynı işi yapan kapı (ayrı süreç)
def _ag(c):
    for n in ast.walk(c.func):
        if isinstance(n, ast.Attribute) and (n.attr in AG or (isinstance(n.value, ast.Name) and n.value.id == "requests")): return n.attr
        if isinstance(n, ast.Name) and n.id in AG: return n.id
    a0 = c.args[0] if c.args else None
    if isinstance(a0, (ast.List, ast.Tuple)) and a0.elts and isinstance(a0.elts[0], ast.Constant) and str(a0.elts[0].value).rsplit("/", 1)[-1] in ("curl", "gh"):
        return str(a0.elts[0].value)
    return None
def _isaret(fn):  # işlev cikis_izin'i soruyor mu (ad ya da globals().get("cikis_izin"))
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id == "cikis_izin": return True
        if isinstance(n, ast.Attribute) and n.attr == "cikis_izin": return True
        if isinstance(n, ast.Constant) and n.value == "cikis_izin": return True
    return False
def _cagrilar(fn): return {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
dosyalar = sorted({os.path.relpath(f, KOD) for f in glob.glob(os.path.join(KOD, "*.py")) + glob.glob(os.path.join(KOD, "aktarici", "*.py"))})
bulunan, eksik, islevler = [], [], {}
for d in dosyalar:
    t = ast.parse(oku(d)); fns = {}
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): fns.setdefault(n.name, n)
    kapi = {a for a, f in fns.items() if _isaret(f)} | {a for (dd, a) in EK_KAPI if dd == d}
    islevler[d] = (fns, kapi)
    def gez(n, yigin):
        for ch in ast.iter_child_nodes(n):
            y = yigin + [ch] if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else yigin
            if isinstance(ch, ast.Call) and _ag(ch):
                ad = y[0].name if y else "<modül>"; tam = ".".join(f.name for f in y) or "<modül>"
                gecti = any(_isaret(f) or (_cagrilar(f) & kapi) for f in y)
                bulunan.append((d, tam, ch.lineno))
                if not gecti and (d, ad) not in ISTISNA and d not in ISTISNA_DOSYA: eksik.append(f"{d}:{ch.lineno} {tam} ({_ag(ch)})")
            gez(ch, y)
    gez(t, [])
ok(f"ağ çağrıları sınıflı ({len(bulunan)} çağrı)", not eksik, eksik)
for (d, a), neden in ISTISNA.items():
    ok(f"istisna hâlâ geçerli: {d} {a}", d in islevler and a in islevler[d][0], "işlev yok — listeyi güncelle")
for d, a in sorted(GEREKLI_KAPI):
    fns, kapi = islevler.get(d, ({}, set()))
    f = fns.get(a)
    ok(f"kapıdan geçiyor: {d} {a}", bool(f) and (_isaret(f) or bool(_cagrilar(f) & kapi)))
FAIL_OPEN = re.compile(r'"gizli_acik" in globals\(\) and (bool\()?gizli_acik\(\)')
YONLENEN = ["aktarici/gemini-ses.py", "aktarici/basecamp-oku.py", "aktarici/animsatici.py", "aktarici/toplantiya-ses.py", "aktarici/sozluk-hakem.py", "aktarici/bas-konus.py",
            "aktarici/kisi-modeli.py", "aktarici/talimat.py", "aktarici/notlar.py", "aktarici/toplanti-oturum.py", "aktarici/tazi-istemci.py", "aktarici/cikis.py"]
for d in YONLENEN: ok(f"fail-open kalıp yok: {d}", not FAIL_OPEN.search(oku(d)))
kk = oku("aktarici/konus-web-kanca.py")
ok("Konuş kancası WebSearch'ü artık denetliyor", 'if ad == "WebSearch": return' not in kk and "web_metin_suphe" in kk and "web_getir_suphe" in kk and "web_suzgec_oku" in kk)
tc = oku("toplanti-claude.py"); i = tc.index("def rapor_cmd")
rc = tc[i:tc.index("\ndef ", i + 10)]
ok("rapor --github: GitHub'a süzülmüş gövde (teshis.sade), ham dosya değil", "_ts.sade(" in rc and '"--body-file", gfp' in rc and '"--body-file", fp' not in rc and "gb_gizli()" in rc)

# --- 2) Web metin kapısı ---------------------------------------------------------------------------------------------------------------------------------------
W = {"__name__": "web_kapi"}; exec(compile(oku("aktarici/web-kapi.py"), "web-kapi.py", "exec"), W)
DOKUM = "**Deniz Arkın** (10:02): üçüncü çeyrekte bayi indirimini yüzde on iki artırmaya karar verdik ama duyurmayalım"
S = W["web_suzgec_kur"](["Deniz Arkın", "Tolga Yılmazer", "Pınar"], [DOKUM], izinli=["Selin Örnekdış"])
ok("süzgeç metin taşımıyor", "deniz" not in json.dumps(S).lower() and "indirim" not in json.dumps(S).lower())
for q, bek in [("İstanbul hava durumu yarın", None), ("dolar kuru bugün", None), ("2026 enflasyon beklentisi", None), ("Örnek Holding yatırım haberi", None),
               ("Selin Örnekdış LinkedIn", None),  # S208: dış katılımcı serbest
               ("deniz arkin linkedin", "ad"), ("DENİZ ARKIN kimdir", "ad"), ("Pınar ne iş yapıyor", "ad"), ("tolga yilmazer", "ad"),
               ("bayi indirimini yüzde on iki artırmaya karar", "alinti"), ("bilgi" + AT + "ornek.com.tr", "eposta"), ("müşteri 1.250.000 TL ciro", "sayi"),
               ("x " * 40, "uzun")]:
    r = W["web_metin_suphe"](q, S)
    ok(f"arama kapısı: {q[:30]!r} → {bek or 'serbest'}", (r is None) == (bek is None), r)
for u, bek in [("https://tr.wikipedia.org/wiki/Ankara", None), ("https://www.example.com/haber/2026/11/ekonomi-gundemi", None),
               ("https://www.linkedin.com/in/deniz-arkin", "ad"), ("https://ornek.com/a/" + "-".join(["kelime"] * 30), "uzun"),
               ("https://ornek.com/s?q=bayi+indirimini+y%C3%BCzde+on+iki+art%C4%B1rmaya", "alinti"), ("http://127.0.0.1:8765/status", "yerel")]:
    r = W["web_getir_suphe"](u, S)
    ok(f"adres kapısı: {u[:44]} → {bek or 'serbest'}", (r is None) == (bek is None), r)

# --- 3) cikis.py: gizli kip ve hedefler -----------------------------------------------------------------------------------------------------------------------
os.environ["SUFLOR_CIKIS_DONGU_YOK"] = "1"
def ns(gizli=False, **ek):
    n = dict(W); n.update(__name__="cikis_test", os=os, json=json, time=time, threading=threading, re=re, AYAR={}, BASE=tempfile.mkdtemp(), STATE={}, _t=lambda tr, en: tr)
    if gizli is not None: n["gizli_acik"] = (lambda: gizli) if not callable(gizli) else gizli
    n.update(ek); exec(compile(oku("aktarici/cikis.py"), "cikis.py", "exec"), n); return n
HEDEF = sorted(ns()["CIKIS_TABLO"])
ok("tablo beklenen hedefleri içeriyor", {"gemini_tts", "gemini_api", "web_arama", "web_getir", "basecamp", "animsatici", "firestore", "drive", "kaggle", "beta", "tazi", "github_rapor", "toplanti_ses", "saglayici", "bilgi_kaynagi"} <= set(HEDEF))
def _hata(): raise RuntimeError("x")
for ad, g in [("gizli açık", True), ("gizli_acik yok", None), ("gizli_acik hata", _hata)]:
    n = ns(gizli=g)
    gecen = [h for h in HEDEF if n["cikis_izin"](h, "metin", "hava durumu")[0]]
    ok(f"{ad}: hiçbir hedef geçmiyor (beta dışı)", gecen == [], gecen)
    ok(f"{ad}: beta teknik sayaçları geçiyor", all(n["cikis_izin"]("beta", t)[0] for t in ("hata", "kurulum", "haftalik", "toplanti_sonu")))
    ok(f"{ad}: beta kullanıcı metni (sorun/geri_bildirim) geçmiyor", not any(n["cikis_izin"]("beta", t)[0] for t in ("sorun", "geri_bildirim", "")))
n = ns(gizli=False, VT_BELLEK={"adlar": ["Deniz Arkın"]}, KIMLIK_VT={"tolga yilmazer": {}})
ok("gizli kapalı: bütün hedefler (web dışı) geçiyor", all(n["cikis_izin"](h, "x")[0] for h in HEDEF if not h.startswith("web_")))
ok("bilinmeyen hedef ret", n["cikis_izin"]("ftp", "x") == (False, "bilinmeyen hedef"))
ok("web_arama serbest konu geçiyor", n["cikis_izin"]("web_arama", "konus", "Ankara hava durumu")[0])
ok("web_arama iç kişi adı (VT) ret", not n["cikis_izin"]("web_arama", "konus", "Deniz Arkın maaş")[0])
ok("web_arama iç kişi adı (kimlik) ret", not n["cikis_izin"]("web_arama", "konus", "Tolga Yılmazer")[0])
ok("web_getir yol adı ret", not n["cikis_izin"]("web_getir", "konus", "https://www.linkedin.com/in/deniz-arkin")[0])
B = n["BASE"]; open(os.path.join(B, "t.md"), "w", encoding="utf-8").write(DOKUM + "\n")
n2 = ns(gizli=False, BASE=B, aktif_dosya=lambda: "t.md", katilimci_gorulen=lambda: ["Kerem Toplantıda"])
ok("toplantıda konuşanın adı ret", not n2["cikis_izin"]("web_arama", "toplanti", "Kerem Toplantıda kimdir")[0])
ok("güncel dökümden alıntı ret", not n2["cikis_izin"]("web_arama", "toplanti", "bayi indirimini yüzde on iki artırmaya karar")[0])
ok("neden metni arayüz dilinde", "alıntı" in n2["cikis_neden"](n2["cikis_izin"]("web_arama", "toplanti", "bayi indirimini yüzde on iki artırmaya karar")[1]))
B4 = tempfile.mkdtemp(); json.dump({"olay": {"kisiler": [{"ad": "Selin Örnekdış"}, {"ad": "Murat İçeriden"}]}}, open(os.path.join(B4, "takvim-secilen.json"), "w"))
n4 = ns(gizli=False, BASE=B4, katilimci_coz=lambda olay, g: {"kisiler": olay["kisiler"]}, dis_katilimcilar=lambda olay: ([{"ad": "Selin Örnekdış", "eposta": "s" + AT + "dis.example"}], False, True))
ok("S208: dış katılımcı serbest, iç davetli ret", n4["cikis_izin"]("web_arama", "toplanti", "Selin Örnekdış LinkedIn")[0] and not n4["cikis_izin"]("web_arama", "toplanti", "Murat İçeriden LinkedIn")[0])
n2["cikis_suzgec_yaz"](); fp = os.path.join(B, "cikis-suzgec.json"); d = json.load(open(fp))
ok("kanca süzgeci 0600, metin yok", (os.stat(fp).st_mode & 0o777) == 0o600 and "kerem" not in json.dumps(d).lower() and d.get("adlar") and d.get("n6"))
n3 = ns(gizli=True, BASE=B); n3["cikis_suzgec_yaz"](); ok("gizli kipte süzgeç yalnız {gizli: true}", json.load(open(fp)).get("gizli") is True and "adlar" not in json.load(open(fp)))
ok("sayaçlar yalnız sayı", all(isinstance(v, int) for v in list(n2["cikis_view"]()["gecti"].values()) + list(n2["cikis_view"]()["engel"].values())))

# Konuş kancası (ayrı süreç)
KK = os.path.join(KOD, "aktarici", "konus-web-kanca.py")
def kanca(ad, deger, canli):
    gi = {"tool_name": ad, "tool_input": {"url": deger} if ad == "WebFetch" else {"query": deger}}
    r = subprocess.run([sys.executable, "-I", "-B", KK, canli], input=json.dumps(gi), capture_output=True, text=True, timeout=10)
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "allow"
C = tempfile.mkdtemp(); json.dump(W["web_suzgec_kur"](["Deniz Arkın"], [DOKUM]), open(os.path.join(C, "cikis-suzgec.json"), "w"))
ok("kanca: serbest arama", kanca("WebSearch", "Ankara hava durumu", C) == "allow")
ok("kanca: süzgeçteki ad (WebSearch) ret", kanca("WebSearch", "deniz arkın linkedin", C) == "deny")
ok("kanca: dökümden alıntı ret", kanca("WebSearch", "bayi indirimini yüzde on iki artırmaya karar", C) == "deny")
ok("kanca: süzgeçteki ad (WebFetch yolu) ret", kanca("WebFetch", "https://www.linkedin.com/in/deniz-arkin", C) == "deny")
ok("kanca: süzgeç yokken e-posta ret", kanca("WebSearch", "bilgi" + AT + "ornek.com", tempfile.mkdtemp()) == "deny")
ok("kanca: canlı klasör yok → ret (fail-closed)", kanca("WebSearch", "hava", os.path.join(C, "yok")) == "deny")
C2 = tempfile.mkdtemp(); open(os.path.join(C2, "cikis-suzgec.json"), "w").write("{bozuk")
ok("kanca: bozuk süzgeç → ret", kanca("WebSearch", "hava", C2) == "deny")
C3 = tempfile.mkdtemp(); json.dump({"gizli": True}, open(os.path.join(C3, "cikis-suzgec.json"), "w"))
ok("kanca: süzgeç gizli → ret", kanca("WebSearch", "hava", C3) == "deny")
C4 = tempfile.mkdtemp(); open(os.path.join(C4, "gizli.json"), "w").write("{}")
ok("kanca: gizli.json → ret (WebSearch ve WebFetch)", kanca("WebSearch", "hava", C4) == "deny" and kanca("WebFetch", "https://example.com", C4) == "deny")

# teshis (beta kanalı) ve Tazı istemcisi: tek başına fail-closed
sys.path.insert(0, KOD); import teshis
U = tempfile.mkdtemp(); os.makedirs(os.path.join(U, "canli"))
ok("teshis: gizli yokken geri bildirim geçer", teshis.cikis_izin("geri_bildirim", U)[0])
open(os.path.join(U, "canli", "gizli.json"), "w").write("{}")
ok("teshis: gizli.json → teknik sayaç geçer, kullanıcı metni geçmez", teshis.cikis_izin("hata", U)[0] and not teshis.cikis_izin("geri_bildirim", U)[0] and not teshis.cikis_izin(None, U)[0])
teshis.CIKIS_IZIN = lambda h, t: (h == "beta" and t == "x", "")
ok("teshis: aktarıcı kapısına devrediyor", teshis.cikis_izin("x", "/yok")[0] and not teshis.cikis_izin("hata", "/yok")[0]); teshis.CIKIS_IZIN = None
r = teshis.gonder({"tur": "geri_bildirim", "kullanici_metni": "deneme"}, {"teshis": True}, U, arka=False)
ok("teshis.gonder gizli kipte kullanıcı metnini kuyruğa bile yazmıyor", r.get("durum") in ("gizli", "kapali") and not os.path.isdir(os.path.join(U, "teshis", "bekleyen")) or not os.listdir(os.path.join(U, "teshis", "bekleyen")), r)
T = {"__name__": "tazi_test"}; exec(compile(oku("aktarici/tazi-istemci.py"), "tazi-istemci.py", "exec"), T)
ok("Tazı: tek başına gizli.json → çağrı yok", T["tazi_cagir"]("durum", {}, ayar={"uygulama": U, "tazi_yol": __file__}) == {"ok": False, "hata": "gizli"})
T["cikis_izin"] = lambda h, t: (False, "gizli kip")
ok("Tazı: aktarıcıda kapı reddederse çağrı yok", T["tazi_cagir"]("durum", {}, ayar={"tazi_yol": __file__}).get("hata") == "gizli")

# Bölüm düzeyi: gizli kipte ağa çıkılmıyor (GEMINI_HOST ulaşılamaz adres; bağlantı denenirse hata dönerdi — sayaçla ayırt edilir)
GN = {"__name__": "gemini_ses", "math": __import__("math"), "os": os, "time": time, "json": json, "base64": __import__("base64"), "subprocess": subprocess, "threading": threading,
      "datetime": __import__("datetime"), "AYAR": {"gemini_ses": "Kore"}, "BASE": tempfile.mkdtemp(), "OYNAT_YOL": "/yok", "write": lambda ps: None}
os.environ.update(SUFLOR_TEST_GEMINI_HOST="127.0.0.1:9", SUFLOR_TEST_GEMINI_ANAHTAR="deneme", SUFLOR_TEST_GEMINI_SESSIZ="1")
exec(compile(oku("aktarici/gemini-ses.py"), "gemini-ses.py", "exec"), GN)
SAY = []
GN["cikis_izin"] = lambda h, t, v=None: (SAY.append(h), (False, "gizli kip"))[1]; GN["cikis_gizli"] = lambda: True
ok("gemini: gizli kipte izinli değil", not GN["gemini_izinli"](True))
ok("gemini: gizli kipte okuma isteği atılmıyor", GN["gemini_oku"]("Merhaba dünya.") is False and SAY and set(SAY) == {"gemini_tts"})
ok("gemini: önceden alma da yok", GN["gemini_onceden"]("Merhaba dünya.") is False)
del GN["cikis_izin"], GN["cikis_gizli"]
ok("gemini: kapı yoksa (fail-closed) izinli değil ve istek yok", not GN["gemini_izinli"](True) and GN["gemini_oku"]("Merhaba.") is False)
HK = {"__name__": "hakem", "os": os, "time": time, "json": json, "re": re, "threading": threading, "datetime": __import__("datetime"), "AYAR": {}, "BASE": tempfile.mkdtemp()}
try:
    _t = ast.parse(oku("aktarici/sozluk-hakem.py"))  # yalnız kapıyla ilgili işlevler (bölümün geri kalanı öğrenen sözlüğe bağlı)
    exec(compile(ast.Module(body=[x for x in _t.body if isinstance(x, ast.FunctionDef) and x.name in ("_hk_gizli", "hakem_acik", "_hk_istek", "_hk_anahtar")], type_ignores=[]), "sozluk-hakem.py", "exec"), HK)
    HK.update(http=__import__("http.client"), HK_ZAMAN_ASIMI=1, gelistirici_mi=lambda: True, gemini_anahtar=lambda: "x")
    HK["GEMINI_HOST"] = "127.0.0.1:9"
    ok("hakem: kapı yoksa istek yok (0, '')", HK["_hk_istek"]("m", {})[:2] == (0, ""))
    ok("hakem: gizli belirlenemiyorsa kapalı", HK["hakem_acik"]() [0] is False)
except Exception as e: ok("hakem bölümü yüklenebildi", False, repr(e)[:200])
BC = {"__name__": "bc", "os": os, "time": time, "json": json, "re": re, "threading": threading, "AYAR": {}, "BASE": tempfile.mkdtemp(), "BC_URLOPEN": lambda *a, **k: (_ for _ in ()).throw(AssertionError("ağa çıktı"))}
try:
    exec(compile(oku("aktarici/basecamp-oku.py"), "basecamp-oku.py", "exec"), BC)
    BC["cikis_izin"] = lambda h, t, v=None: (False, "gizli kip")
    try: BC["_bc_http"]("https://3.basecampapi.com/x"); ok("basecamp: gizli kipte istek yok", False, "istisna yok")
    except OSError as e: ok("basecamp: gizli kipte istek yok", "dış çıkış" in str(e), str(e))
    except AssertionError as e: ok("basecamp: gizli kipte istek yok", False, str(e))
except Exception as e: ok("basecamp bölümü yüklenebildi", False, repr(e)[:200])

print(f"\n{len(HATA)} hata" if HATA else "\ncikis: tamam")
sys.exit(1 if HATA else 0)
