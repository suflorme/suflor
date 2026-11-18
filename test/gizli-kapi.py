#!/usr/bin/env python3
# Gizli kip tek model kapısı (19 Kasım 2026; aktarici/kapi.py kapi_gizli + kapi_model). Kullanıcı kararı: gizli kipte HİÇBİR Claude / yapay zekâ çağrısı yok
# (prova, eylem menüsü, e-posta taslağı, Konuş, çeviri, toplantı oturumu, giriş yoklaması dahil). Varsayılan KAPALI: gizli durumu belirlenemezse çağrı yok.
#   1) Durağan (AST): aktarıcı sürecinde (relay.py + aktarici/*.py) alt süreç başlatan her çağrı yeri sınıflı; model çağıran yer yalnız MODEL_KAPI listesinde ve
#      alt süreçten ÖNCE kapi_model'i soruyor (ya da kapi_iste içinde koşuyor); "kapı yoksa engelleme" (else None) kalıbı yok; kapi_engel/kapi_iste/kapi_ac kapıdan geçiyor;
#      GIZLI_RED gereken uçları içeriyor. Yeni bir çağrı yeri eklenince bu test sınıflandırılana kadar düşer.
#   2) Birim: kapi_gizli fail-closed; kapi_brifing, beyin_tek, _brifing_akis, ar_calistir gizli kipte ve kapı yokken alt süreç açmıyor.
#   3) Davranış: yalıtılmış aktarıcı BOŞ portta, gizli.json ile açık başlar; PATH'te sahte `open` ve sahte claude (çağrıyı dosyaya yazar). GIZLI_RED'deki her uç ve
#      prova / eylem / e-posta / toplantı oturumu istekleri reddedilir; /status kapi.model.gecti 0 kalır; sahte open/claude hiçbir model çağrısı görmez.
# Sabit port açmaz (bos_port(0)), gerçek claude çağrılmaz, ağ yok. Kurgu veri.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gizli-kapi.py      (kaldı → çıkış 1)
import ast, glob, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
def oku(y): return open(os.path.join(KOD, y), encoding="utf-8").read()

# --- 1) Durağan ------------------------------------------------------------------------------------------------------------------------------------------------------
SP = {"run", "Popen", "check_output", "call", "check_call", "system", "execv", "execvp", "spawnv"}
ISARET = re.compile(r"claude|BRIFING_APP|BEYIN\.|\bby\.|\bBY\.|_args\(")  # işlevde model izi: claude yolu, Brifing yardımcısı, beyin katmanı, *_args(
# Model çağıran yerler (aktarıcı süreci): alt süreçten önce kapi_model
MODEL_KAPI = {("aktarici/kapi.py", "kapi_brifing"), ("aktarici/brifing-ses.py", "_brifing_akis"), ("aktarici/brifing-ses.py", "beyin_tek"), ("aktarici/bas-konus.py", "konus_ac"),
              ("aktarici/ceviri.py", "_cv_baslat"), ("aktarici/toplanti-oturum.py", "toplanti_oturum_ac"), ("aktarici/toplanti-oturum.py", "toplanti_oturum_terminal"),
              ("aktarici/web-arastirma.py", "ar_calistir")}
KAPI_ISTE_ICINDE = {("relay.py", "kesisim_model.cagri"): "kesisim_model"}  # kapi_iste'ye verilen cagri: kapi_iste → kapi_engel → kapi_model
MODEL_DEGIL = {  # izli işlevde alt süreç ama model çağrısı değil (neden)
    ("aktarici/bas-konus.py", "_onara_yardimci"): "Brifing --dizin: proje belgesi dizinleme",
    ("aktarici/bas-konus.py", "vt_izle_bak"): "Brifing --vt-izle: kayıt veritabanı izleme",
    ("aktarici/bas-konus.py", "_vt_sema_uret"): "toplanti-claude.py vt-sema (yerel)",
    ("aktarici/dokum-kontrol.py", "dk_temiz_yenile"): "toplanti-claude.py dokum (yerel)",
    ("aktarici/notlar.py", "kutu_sozluk_ekle"): "toplanti-claude.py sozluk (yerel)",
    ("aktarici/whisper-hat.py", "bellek_view"): "süreç listesi",
    ("relay.py", "_baslat"): "aktarıcı açılışı (yerel yardımcılar)",
    ("relay.py", "claude_girisli"): "claude auth status: içerik yok, model çağrısı yok",
    ("relay.py", "claude_surum_bak"): "claude --version: model çağrısı yok",
    ("relay.py", "toplanti_maliyet_yaz"): "toplanti-claude.py maliyet (yerel)",
}
AYRI_SUREC = {"kurulum.py", "kesisim-coz.py", "proje-karti.py", "toplanti-claude.py"}  # aktarıcı dışı (kullanıcı ya da başka oturum başlatır); kalan iş: tek çıkış modülü

def cagri_yerleri(yol):
    S = open(yol, encoding="utf-8").read(); A = ast.parse(S); out = []
    def gez(n, ad, fn):
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)): ad2, fn2 = ad + [c.name], c
            elif isinstance(c, ast.ClassDef): ad2, fn2 = ad + [c.name], fn
            else: ad2, fn2 = ad, fn
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name):
                a, k = c.func.attr, c.func.value.id
                if (a in SP and k in ("subprocess", "os", "sp_", "_sp")) or (a == "tek" and k in ("BEYIN", "by", "BY")):
                    seg = ast.get_source_segment(S, fn2) if fn2 is not None else ast.get_source_segment(S, c)
                    out.append({"ad": ".".join(ad2) or "<modül>", "satir": c.lineno, "izli": bool(ISARET.search(seg or "")), "fn": fn2, "S": S, "tek": a == "tek"})
            gez(c, ad2, fn2)
    gez(A, [], None); return out

RELAY_DOSYA = ["relay.py"] + sorted(os.path.relpath(f, KOD) for f in glob.glob(os.path.join(KOD, "aktarici", "*.py")))
bulunan, sorun = set(), []
for d in RELAY_DOSYA:
    for y in cagri_yerleri(os.path.join(KOD, d)):
        a = (d, y["ad"])
        if not y["izli"] and not y["tek"]: continue
        if d == "aktarici/beyin.py": continue  # kütüphane (BEYIN.tek / Mcp): aktarıcıdaki çağıranları bu taramada (BEYIN.tek izli)
        bulunan.add(a)
        if a in MODEL_KAPI:
            kaynak = ast.get_source_segment(y["S"], y["fn"]); bas = y["fn"].lineno
            i = kaynak.find("kapi_model(")
            if i < 0 or bas + kaynak[:i].count("\n") >= y["satir"]: sorun.append(f"{d}:{y['ad']} satır {y['satir']}: alt süreçten önce kapi_model yok")
            if re.search(r'kapi_(ac|model)\([^)]*\)\)? if "kapi_\w+" in globals\(\) else None', kaynak): sorun.append(f"{d}:{y['ad']}: kapı yoksa engellemiyor (else None)")
        elif a in KAPI_ISTE_ICINDE:
            dis = KAPI_ISTE_ICINDE[a]; S = y["S"]; m = re.search(r"\ndef " + dis + r"\(.*?(?=\ndef )", S, re.S)
            if not m or "kapi_iste(" not in m.group(0): sorun.append(f"{d}:{y['ad']}: {dis} kapi_iste'den geçmiyor")
        elif a not in MODEL_DEGIL: sorun.append(f"{d}:{y['ad']} satır {y['satir']}: SINIFLANMAMIŞ alt süreç (model çağrısıysa kapi_model'den geçir ve MODEL_KAPI'ye ekle; değilse MODEL_DEGIL'e neden yaz)")
ok("aktarıcı sürecinde her model çağrı yeri tek kapıdan (kapi_model) geçiyor; sınıflanmamış yer yok", not sorun, sorun)
ok("beklenen çağrı yerlerinin hepsi bulundu (tarama körleşmedi)", (MODEL_KAPI | set(KAPI_ISTE_ICINDE)) <= bulunan, sorted((MODEL_KAPI | set(KAPI_ISTE_ICINDE)) - bulunan))
dis = sorted({os.path.basename(f) for f in glob.glob(os.path.join(KOD, "*.py")) if os.path.basename(f) != "relay.py" for y in cagri_yerleri(f) if y["izli"] or y["tek"]})
ok("aktarıcı dışında model izli alt süreç yalnız bilinen ayrı süreçlerde (" + ", ".join(sorted(AYRI_SUREC)) + ")", set(dis) <= AYRI_SUREC, sorted(set(dis) - AYRI_SUREC))
acik = []
for d in RELAY_DOSYA:
    for i, l in enumerate(oku(d).splitlines(), 1):
        if re.search(r'kapi_(ac|model)\([^)]*\)\)? if "kapi_(ac|model)" in globals\(\) else None', l): acik.append(f"{d}:{i}")
ok("kapı yoksa model süreci açan (else None) kalıp kalmadı", not acik, acik)
KP = oku("aktarici/kapi.py")
def islev(S, ad): m = re.search(r"\ndef " + ad + r"\(.*?(?=\ndef |\Z)", S, re.S); return m.group(0) if m else ""
ke, ki, ka, kb = islev(KP, "kapi_engel"), islev(KP, "kapi_iste"), islev(KP, "kapi_ac"), islev(KP, "kapi_brifing")
ok("kapi_engel ilk kural olarak kapi_model'i soruyor (tablodaki gizli alanından bağımsız)", "kapi_model(" in ke and ke.index("kapi_model(") < min(ke.index('r.get("plan")'), ke.index("saglayici")) and 'r.get("gizli")' not in ke)
ok("kapi_iste çağrıdan önce kapi_engel; kapi_ac kapi_engel; kapi_brifing ilk iş kapi_model", "kapi_engel(" in ki and ki.index("kapi_engel(") < ki.index("cagri()") and "kapi_engel(" in ka and kb.index("kapi_model(") < kb.index("subprocess.run"))
ok("kapi_gizli fail-closed: işlev yoksa ve hata verirse True", re.search(r"if not callable\(f\): return True", islev(KP, "kapi_gizli")) is not None and "except Exception: return True" in islev(KP, "kapi_gizli"))
RS = oku("relay.py"); RA = ast.parse(RS)
GR = next(ast.literal_eval(n.value) for n in RA.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GIZLI_RED" for t in n.targets))
GEREKEN = {"/prova", "/kayit-eylem", "/kayit-not", "/eposta-onemli", "/girdi", "/bas-konus", "/brifing", "/eylem", "/dusunme", "/mutabakat", "/is-kopya", "/belge-oneri",
           "/yaklasan-tarihler", "/tazi", "/takvim-toplanti", "/arastirma", "/ask", "/note"}
ok("GIZLI_RED prova, eylem menüsü, e-posta taslağı ve Claude'a/dışarı gidebilen uçları içeriyor", GEREKEN <= GR, sorted(GEREKEN - GR))
ok("gizli_red iletisi aynen (pano tanıyor: ok False, gizli True)", '"gizli": True' in islev(RS, "gizli_red"))

# --- 2) Birim (bölümler yalıtılmış ad alanında, sahte alt süreç) ------------------------------------------------------------------------------------------------------
T = tempfile.mkdtemp(prefix="gizli-kapi-")
class SahteSP:
    TimeoutExpired = subprocess.TimeoutExpired; PIPE = subprocess.PIPE; DEVNULL = subprocess.DEVNULL; STDOUT = subprocess.STDOUT
    def __init__(s): s.n = 0
    def run(s, *a, **k): s.n += 1; return subprocess.CompletedProcess(a, 0, "", "")
    def Popen(s, *a, **k): s.n += 1; raise OSError("sahte")
def ad_alani(gizli, kapi=True):
    sp = SahteSP(); ns = {"__builtins__": __builtins__, "subprocess": sp, "threading": threading, "time": time, "os": os, "json": json, "re": re, "sys": sys, "datetime": __import__("datetime"),
                          "secrets": __import__("secrets"), "AYAR": {}, "BASE": T, "LOCK": threading.Lock(), "write": lambda p: None, "BRIFING_APP": os.path.join(T, "Brifing.app"), "print": lambda *a, **k: None}
    if gizli is not None: ns["gizli_acik"] = gizli
    if kapi: exec(compile(KP, "kapi.py", "exec"), ns)
    return ns, sp
ns, _ = ad_alani(None); ok("gizli_acik yok → kapi_gizli True, kapi_model engel", ns["kapi_gizli"]() is True and ns["kapi_model"]("x") == "gizli kip")
def patla(): raise RuntimeError("x")
ns, _ = ad_alani(patla); ok("gizli_acik hata verirse → kapi_gizli True (fail-closed)", ns["kapi_gizli"]() is True)
ns, _ = ad_alani(lambda: False); ok("gizli kapalı → kapi_model izin verir, sayaç gecti", ns["kapi_model"]("x") is None and ns["KAPI_MODEL"]["gecti"] == 1)
ns, sp = ad_alani(lambda: True)
ok("gizli kipte kapi_brifing Brifing.app'i açmaz (None), sayaç engel", ns["kapi_brifing"]({"claude": "/x", "args": ["-p", "x"], "cwd": T, "sure": 5}, "eylem", 5) is None and sp.n == 0 and ns["KAPI_MODEL"]["engel"] == 1)
ok("gizli kipte kapi_engel her iş türünde (ön plan prova/eylem/eposta_taslak/brifing, konus-ac, giris) engel", all(ns["kapi_engel"](k) == "gizli kip" for k in ("prova", "eylem", "eposta_taslak", "brifing", "talimat", "konus-ac", "ceviri-ac", "toplanti-ac", "giris", "arastirma", "dusunme", "degerlendir:eposta")))
BS = oku("aktarici/brifing-ses.py")
def dilim(S, bas, son): return S[S.index(bas):S.index(son, S.index(bas))]
BT = dilim(BS, "def beyin_tek", "# --- Sesli brifing"); BA = dilim(BS, "def _brifing_akis", "\ndef ")
class Beyin:
    __file__ = "/yok/beyin.py"
    @staticmethod
    def tek_istek(*a): return {}
for gz, kapi, ad in ((lambda: True, True, "gizli kipte"), (lambda: False, False, "kapı (kapi.py) yokken")):
    ns, sp = ad_alani(gz, kapi); ns.update(BEYIN=Beyin, claude_json=lambda *a: ("CEVAP", {"maliyet": 0}))
    exec(BT + "\n" + BA, ns)
    r1 = ns["beyin_tek"]("prova", {"tur": "openai"}, "istem"); r2 = ns["_brifing_akis"](os.path.join(T, "i.json"), {}, "istem")
    ok(f"{ad} beyin_tek ve _brifing_akis alt süreç açmaz (fail-closed)", r1 == ("", None) and r2 is None and sp.n == 0, (r1, r2, sp.n))
WA = oku("aktarici/web-arastirma.py"); AR = WA[WA.index("def ar_calistir"):WA.index("\ndef ar_kapidan")]
for gz, kapi, ad in ((lambda: True, True, "gizli kipte"), (lambda: False, False, "kapı yokken")):
    ns, sp = ad_alani(gz, kapi); ns.update(BEYIN=type("B", (), {"arastirma_args": staticmethod(lambda a: ["-p"])}), claude_yolu=lambda: "/x/claude", AR_ZAMAN=5, ar_istem=lambda k, u: k)
    exec(AR, ns); r = ns["ar_calistir"]("Orbitek")
    ok(f"{ad} web araştırması claude -p açmaz", not r["ok"] and str(r["hata"]).startswith("kapı: ") and sp.n == 0, r)

# --- 3) Davranış: yalıtılmış aktarıcı (boş port, gizli.json ile açık) --------------------------------------------------------------------------------------------------
PORT = bos_port(0); E = os.path.join(T, "e2e"); canli = os.path.join(E, "canli"); os.makedirs(canli); proje = os.path.join(E, "proje"); os.makedirs(proje)
for f in ("relay.py", "yapi.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), E)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(E, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(E, "pano"))
os.makedirs(os.path.join(E, "Suflor Brifing.app"))  # yardımcı "kurulu" görünsün: kapı olmasa model yolu alt sürece kadar inerdi
bin_ = os.path.join(T, "bin"); os.makedirs(bin_); iz = os.path.join(T, "iz.log")
for ad in ("open", "claude"):  # sahte: her çağrıyı iz dosyasına yazar, hiçbir şey açmaz
    y = os.path.join(bin_, ad); open(y, "w").write(f'#!/bin/sh\necho "{ad} $*" >> "{iz}"\n' + ('[ "$1" = "--version" ] && echo "2.1.0 (Claude Code)"\n[ "$1" = "auth" ] && echo \'{{"loggedIn": true}}\'\n' if ad == "claude" else "") + "exit 0\n"); os.chmod(y, 0o755)
json.dump({"bas": time.time()}, open(os.path.join(canli, "gizli.json"), "w"))
ayar_y = os.path.join(E, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": E, "proje": proje, "calisma": proje, "ortak": "/Users/Shared/Suflor", "claude": os.path.join(bin_, "claude"), "konus_on_ac": False,
           "pocket_python": "/yok/python", "pocket_hf": "/yok", "konusma": False, "talimat_hedefler": {}}, open(ayar_y, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar_y, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_ORTAK_POSTA="", SUFLOR_TEST_SOZ_DONGU_YOK="1",
           PATH=bin_ + os.pathsep + os.environ.get("PATH", ""))
p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=E, env=env, stdout=open(os.path.join(E, "r.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(100):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1.5); an = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); H = {"X-Suflor-Anahtar": an, "Origin": f"http://127.0.0.1:{PORT}", "Content-Type": "application/json"}
    def post(yol, v):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=H), timeout=20).read())
        except urllib.error.HTTPError as e: return {"_kod": e.code}
        except OSError as e: return {"_hata": repr(e)}
    def status(): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers=H), timeout=10).read())
    s0 = status(); ok("aktarıcı gizli kipte açıldı (gizli.json)", bool(s0.get("gizli")) or "GİZLİ: açık" in open(os.path.join(E, "r.log"), encoding="utf-8").read(), s0.get("gizli"))
    genel = {"islem": "x", "text": "deneme sorusu", "metin": "deneme", "id": "x", "tur": "x", "kayit": "x", "konu": "Deneme"}
    ozel = [("/prova", {"islem": "oner", "konu": "Bütçe sunumu"}), ("/prova", {"islem": "baslat", "konu": "Bütçe", "kisiler": ["Ali"]}), ("/prova", {"islem": "cevap", "metin": "x"}),
            ("/kayit-eylem", {"id": "x", "eylem": "taslak"}), ("/kayit-eylem", {"id": "x", "eylem": "ata", "kim": "Ali"}), ("/kayit-not", {"id": "x", "metin": "not"}),
            ("/eposta-onemli", {"islem": "taslak", "id": "x"}), ("/girdi", {"kayit": "x", "text": "Bu iş ne durumda?"}), ("/girdi", {"text": "Bana bugünü özetle"}),
            ("/bas-konus", {"text": "merhaba"}), ("/mutabakat", {"islem": "calistir"}), ("/dusunme", {"islem": "calistir"}), ("/tazi", {"islem": "iste", "ad": "Orbitek"}),
            ("/brifing", {"olay": "x"}), ("/eylem", {"islem": "sun"}), ("/komut", {"tur": "talimat", "metin": "x"})]
    red = [(y, post(y, dict(genel))) for y in sorted(GR)] + [(y, post(y, b)) for y, b in ozel]
    yanlis = [(y, r) for y, r in red if not (r.get("ok") is False and r.get("gizli") is True)]
    ok(f"gizli kipte {len(red)} istek (GIZLI_RED'in {len(GR)} ucu + prova/eylem/e-posta/Konuş/mutabakat/Tazı) gizli_red ile reddedildi", not yanlis, yanlis[:6])
    r = post("/toplanti-oturum", {"islem": "terminal"}); r2 = post("/toplanti-oturum", {"islem": "yaz", "metin": "x"})
    ok("toplantı oturumu: Terminal'e alma (claude --resume) ve yazma gizli kipte reddedilir", r.get("gizli") is True and r2.get("gizli") is True, (r, r2))
    time.sleep(1.0); s1 = status(); km = (s1.get("kapi") or {}).get("model") or {}
    ok("tek model kapısı hiç geçiş vermedi (/status kapi.model.gecti 0)", km.get("gecti") == 0, km)
    izl = open(iz, encoding="utf-8").read().splitlines() if os.path.exists(iz) else []
    model_iz = [l for l in izl if re.search(r"--istek|--beyin|(^claude| )-p( |$)|--print|stream-json|--resume", l)]
    ok("sahte open/claude hiçbir model çağrısı görmedi (Brifing --istek/--beyin, claude -p, --resume yok)", not model_iz, model_iz[:5])
    lg = open(os.path.join(E, "r.log"), encoding="utf-8").read()
    ok("aktarıcıda Traceback yok", "Traceback" not in lg or print(lg[-2500:]))
finally:
    if HATA:
        try: print(open(os.path.join(E, "r.log"), encoding="utf-8").read()[-2500:])
        except OSError: pass
    p.terminate()
    try: p.wait(10)
    except subprocess.TimeoutExpired: p.kill()
    shutil.rmtree(T, ignore_errors=True)
print(("TAMAM: " if not HATA else "KALDI: ") + f"{len(HATA)} hata")
sys.exit(1 if HATA else 0)
