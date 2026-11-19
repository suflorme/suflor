#!/usr/bin/env python3
# Rota tablosu (19 Kasım 2026; mimari denetim 3, bulgu 3). relay.py'de tam yollu uçlar ROTA_GET / ROTA_POST tablosunda (@rota), kalanlar eski if zincirinde.
#   1) Durağan (AST): tabloda aynı yol iki kez yok; tablodaki yol eski zincirde de yok (ulaşılamayan dal kalmasın); eski zincirde aynı tam yol iki kez yok;
#      tablo, ortak denetimlerden (köken, VERI_GET 401, anahtar, gizli YUT/RED) SONRA soruluyor; kayıt işlevi çift kaydı açılışta ValueError ile durduruyor.
#   2) Envanter: taşınan / eski zincirde kalan uç sayıları ve önek/kalıp yolları (yalnız bilgi).
#   3) Davranış eşliği: önceki sürüm (../_yedek/relay-v0.252.0.py; SUFLOR_ROTA_ESKI ile başka dosya) ve bu sürüm yalıtılmış klasörlerde BOŞ portta açılır
#      (gizli-kapi.py düzeni: sahte open/claude, kurgu ayar); aynı istekler ikisine de gider, durum kodları (ve JSON'da ok/err, üst düzey anahtarlar) karşılaştırılır.
# Gerçek claude çağrılmaz, ağ yok, sabit port açmaz. Kurgu veri.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/rota.py      (kaldı → çıkış 1)
import ast, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESKI = os.environ.get("SUFLOR_ROTA_ESKI") or os.path.join(os.path.dirname(KOD), "_yedek", "relay-v0.252.0.py")
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)

# --- 1) Durağan ------------------------------------------------------------------------------------------------------------------------------------------------------
def yol_ifadesi(n):  # yol | self.path | self.path.split("?")[0]
    if isinstance(n, ast.Name) and n.id == "yol": return True
    if isinstance(n, ast.Attribute) and n.attr == "path" and isinstance(n.value, ast.Name) and n.value.id == "self": return True
    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "split": return yol_ifadesi(n.value.func.value)
    return False
def kosul_yollari(test):
    tam, onek = set(), set()
    for n in ast.walk(test):
        if isinstance(n, ast.Compare) and yol_ifadesi(n.left) and len(n.ops) == 1:
            c = n.comparators[0]
            if isinstance(n.ops[0], ast.Eq) and isinstance(c, ast.Constant) and isinstance(c.value, str): tam.add(c.value)
            elif isinstance(n.ops[0], ast.In) and isinstance(c, (ast.Tuple, ast.Set, ast.List)): tam |= {e.value for e in c.elts if isinstance(e, ast.Constant)}
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "startswith" and yol_ifadesi(n.func.value):
            onek |= {a.value for a in n.args if isinstance(a, ast.Constant)}
    return tam, onek
def zincir(fn, isaret):
    """İşlevin üst düzey if'leri: isaret (tablo sorgusu) öncesi = ön denetimler, sonrası = eski zincir. [(satır, tam yollar, önekler)]"""
    on, son, gecti = [], [], isaret is None
    for st in fn.body:
        if isaret and isaret in ast.dump(st): gecti = True; continue
        if isinstance(st, ast.If):
            t, o = kosul_yollari(st.test); (son if gecti else on).append((st.lineno, t, o))
    return on, son
def analiz(src):
    A = ast.parse(src); H = next(c for c in A.body if isinstance(c, ast.ClassDef) and c.name == "H")
    m = {f.name: f for f in H.body if isinstance(f, ast.FunctionDef)}
    tablo = {"GET": [], "POST": []}
    for f in A.body:
        if not isinstance(f, ast.FunctionDef): continue
        for d in f.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "rota":
                yon = d.args[0].value; kw = {k.arg: k.value.value for k in d.keywords}
                for a in d.args[1:]: tablo[yon].append((a.value, f.name, kw))
    var = bool(tablo["GET"] or tablo["POST"])
    gon, gson = zincir(m["do_GET"], "ROTA_GET" if var else None)
    pon, pson = zincir(m["_post"], "ROTA_POST" if var else None)
    return {"tablo": tablo, "get_on": gon, "get": gson, "post_on": pon, "post": pson, "m": m, "src": src}
YENI = analiz(open(os.path.join(KOD, "relay.py"), encoding="utf-8").read())
T = YENI["tablo"]
for yon in ("GET", "POST"):
    yollar = [y for y, _, _ in T[yon]]
    cift = sorted({y for y in yollar if yollar.count(y) > 1})
    ok(f"{yon} tablosunda çift kayıt yok", not cift, cift)
    zy = [y for _, t, _ in YENI[yon.lower()] for y in t]
    ortak = sorted(set(yollar) & set(zy))
    ok(f"{yon}: tablodaki yol eski zincirde yok (ulaşılamayan dal yok)", not ortak, ortak)
    zc = sorted({y for y in zy if zy.count(y) > 1})
    ok(f"{yon}: eski zincirde aynı tam yol iki kez yok", not zc, zc)
    ok(f"{yon}: tablo işleyicileri modül düzeyinde ve imzası doğru", all(n.startswith("_g_" if yon == "GET" else "_p_") for _, n, _ in T[yon]))
# Sıra: tablo ortak denetimlerden sonra
dg = ast.get_source_segment(YENI["src"], YENI["m"]["do_GET"]); dp = ast.get_source_segment(YENI["src"], YENI["m"]["_post"])
ok("GET: köken → VERI_GET 401 → tablo sırası", 0 <= dg.find("self._koken() is None") < dg.find("yol in VERI_GET") < dg.find("ROTA_GET.get(yol)"))
ok("GET: anahtarsız /takvim ve /kimlik?n= tablodan önce (ön denetim)", dg.find('yol == "/takvim" and not self._yetkili()') < dg.find("ROTA_GET.get(yol)") and dg.find("kimlik_imza(") < dg.find("ROTA_GET.get(yol)"))
ok("POST: köken → boyut/JSON → anahtar → gizli YUT/RED → tablo sırası",
   0 <= dp.find("self._koken() is None") < dp.find('"err": "boyut"') < dp.find("not yetkili and self.path") < dp.find("GIZLI_YUT") < dp.find("GIZLI_RED") < dp.find("ROTA_POST.get(self.path)"))
ok("POST: tablo pano=True için köken 403 veriyor ve bağlamı (yetkili, pano, serit, o) geçiriyor",
   'if r[1] and not pano: return self._json({"ok": False, "err": "köken"}, 403)' in dp and '{"yetkili": yetkili, "pano": pano, "serit": serit, "o": o}' in dp)
ok("do_POST finally kart_bildir() aynen", "finally: kart_bildir()" in ast.get_source_segment(YENI["src"], YENI["m"]["do_POST"]))
S = YENI["src"]; RK = S[S.index("ROTA_GET, ROTA_POST = {}, {}"):S.index("class H(BaseHTTPRequestHandler):")]
ns = {}; exec(RK, ns)
@ns["rota"]("POST", "/x")
def _a(self, p, k): return 1
try:
    ns["rota"]("POST", "/x")(lambda self, p, k: 2); cift_hata = False
except ValueError: cift_hata = True
ok("rota(): aynı yol ikinci kez kaydedilince ValueError (açılışta durur)", cift_hata)

# --- 2) Envanter ------------------------------------------------------------------------------------------------------------------------------------------------------
ES = analiz(open(ESKI, encoding="utf-8").read()) if os.path.exists(ESKI) else None
def say(a, yon):
    tab = {y for y, _, _ in a["tablo"][yon]}; z = {y for _, t, _ in a[yon.lower()] for y in t}; on = {y for _, t, _ in a[yon.lower() + "_on"] for y in t}
    onek = sorted({o for _, _, o in a[yon.lower()] + a[yon.lower() + "_on"] for o in o})
    return tab, z, on, onek
for yon in ("GET", "POST"):
    tab, z, on, onek = say(YENI, yon)
    if ES: _, ez, eon, _ = say(ES, yon); print(f"  {yon} önce: {len(ez | eon)} tam yol, hepsi if zincirinde")
    print(f"  {yon} şimdi: tabloda {len(tab)} · eski zincirde {len(z)} · ön denetimde {len(on)} ({', '.join(sorted(on)) or '-'}) · önek/kalıp: {', '.join(onek) or '-'}")
    print(f"     eski zincirde kalan: {', '.join(sorted(z))}")
    if ES:
        _, ez, eon, _ = say(ES, yon)
        ok(f"{yon}: önceki sürümün her tam yolu hâlâ karşılanıyor (tablo ya da zincir)", (ez | eon) <= (tab | z | on), sorted((ez | eon) - (tab | z | on)))

# --- 3) Davranış eşliği -----------------------------------------------------------------------------------------------------------------------------------------------
if not os.path.exists(ESKI):
    print(f"(eşlik denetimi atlandı: {ESKI} yok)"); sys.exit(1 if HATA else 0)
TMP = tempfile.mkdtemp(prefix="rota-")
bin_ = os.path.join(TMP, "bin"); os.makedirs(bin_); iz = os.path.join(TMP, "iz.log")
for ad in ("open", "claude", "osascript"):  # sahte: çağrıyı iz dosyasına yazar, hiçbir şey açmaz
    y = os.path.join(bin_, ad); open(y, "w").write(f'#!/bin/sh\necho "{ad} $*" >> "{iz}"\n' + ('[ "$1" = "--version" ] && echo "2.1.0 (Claude Code)"\n[ "$1" = "auth" ] && echo \'{{"loggedIn": true}}\'\n' if ad == "claude" else "") + "exit 0\n"); os.chmod(y, 0o755)
def kur(ad, relay_kaynak):
    E = os.path.join(TMP, ad); canli = os.path.join(E, "canli"); proje = os.path.join(E, "proje"); ortak = os.path.join(E, "ortak")
    for d in (canli, proje, ortak): os.makedirs(d)
    for f in ("yapi.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), E)
    shutil.copy(relay_kaynak, os.path.join(E, "relay.py"))
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(E, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(E, "pano"))
    port = bos_port(0); ayar = os.path.join(E, "ayar.json")
    json.dump({"alan": "Deneme", "ad": "Deniz T", "port": port, "uygulama": E, "proje": proje, "calisma": proje, "ortak": ortak, "claude": os.path.join(bin_, "claude"),
               "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok", "konusma": False, "talimat_hedefler": {}}, open(ayar, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_ORTAK_POSTA="", SUFLOR_TEST_SOZ_DONGU_YOK="1",
               PATH=bin_ + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(port)], cwd=E, env=env, stdout=open(os.path.join(E, "r.log"), "w"), stderr=subprocess.STDOUT)
    return {"ad": ad, "E": E, "canli": canli, "port": port, "p": p}
R = [kur("eski", ESKI), kur("yeni", os.path.join(KOD, "relay.py"))]
try:
    for r in R:
        for _ in range(150):
            if os.path.exists(os.path.join(r["canli"], "kart-anahtari.txt")) or r["p"].poll() is not None: break
            time.sleep(0.2)
        time.sleep(1.5)
        ok(f"{r['ad']} aktarıcı açıldı", r["p"].poll() is None and os.path.exists(os.path.join(r["canli"], "kart-anahtari.txt")), open(os.path.join(r["E"], "r.log"), encoding="utf-8", errors="replace").read()[-800:])
        r["an"] = open(os.path.join(r["canli"], "kart-anahtari.txt")).read().strip()
    if HATA: raise SystemExit
    def iste(r, yontem, yol, govde=None, anahtar=False, koken=None, ham=None):
        h = {"Content-Type": "application/json"}
        if anahtar: h["X-Suflor-Anahtar"] = r["an"]
        if koken == "pano": h["Origin"] = f"http://127.0.0.1:{r['port']}"
        elif koken: h["Origin"] = koken
        veri = ham if ham is not None else (json.dumps(govde).encode() if yontem == "POST" else None)
        try: x = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{r['port']}{yol}", data=veri, headers=h, method=yontem), timeout=20); kod, b, ct = x.status, x.read(), x.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e: kod, b, ct = e.code, e.read(), e.headers.get("Content-Type", "")
        except OSError as e: return ("hata", repr(e)[:80])
        if "json" in ct:
            try: j = json.loads(b)
            except ValueError: return (kod, "bozuk-json")
            return (kod, (j.get("ok"), j.get("err"), tuple(sorted(j))) if isinstance(j, dict) else type(j).__name__)
        return (kod, ct.split(";")[0])
    def kiyas(ad, istekler, anahtar_kume=True):
        fark = []
        for yontem, yol, kw in istekler:
            a, b = iste(R[0], yontem, yol, **kw), iste(R[1], yontem, yol, **kw)
            if not anahtar_kume and isinstance(a[1], tuple): a, b = (a[0], a[1][:2]), (b[0], b[1][:2])
            if a != b: fark.append((yontem, yol, kw.get("koken"), a, b))
        ok(f"{ad}: {len(istekler)} istekte eski ve yeni aynı", not fark, fark[:5])
        return fark
    ALL_GET = sorted({y for y, _, _ in T["GET"]} | {y for _, t, _ in YENI["get"] + YENI["get_on"] for y in t} | {y for _, t, _ in ES["get"] + ES["get_on"] for y in t})
    ALL_POST = sorted({y for y, _, _ in T["POST"]} | {y for _, t, _ in YENI["post"] for y in t} | {y for _, t, _ in ES["post"] for y in t})
    EK_GET = ["/", "/mini", "/yok-boyle-bir-yol", "/agenda?x=1", "/konus-gecmis?x=1", "/geri-bildirim/onizle?x=1", "/status?x=1", "/takvim?v=0.1.0", "/kimlik?n=" + "0" * 32,
              "/toplanti-oturum?n=3", "/marka/yok.svg", "/kanit/yok.png", "/cards?bekle=0"]
    # a) anahtarsız GET: VERI_GET 401, kabuklar 200, diğerleri aynı
    kiyas("anahtarsız GET (tüm yollar + sorgulu)", [("GET", y, {}) for y in ALL_GET + EK_GET])
    # b) anahtarlı GET: yan etkisiz okuma uçları (Mac uygulamalarına — Kişiler, Takvim, Anımsatıcılar, Mail — dokunanlar hariç)
    GUVENLI_GET = ["/toplanti-oturum", "/toplanti-oturum?n=2", "/geri-bildirim/onizle", "/taslak", "/taslak?pano=1", "/agenda", "/agenda?x=1", "/toplantilar", "/prova",
                   "/bugun-veri", "/is-kopya", "/belge-oneri", "/kayit-menu", "/izleme", "/arastirma", "/arastirma?id=yok", "/kesisim.json", "/dokum-kontrol/liste",
                   "/dokum-kontrol/plan", "/dokum-kontrol/sozluk", "/ortak", "/kayitlar", "/kapanis-turu", "/gundem-taslagi", "/vt-bellek", "/konus-gecmis",
                   "/konus-gecmis?x=1", "/katilimcilar", "/kimlik", "/kesisim", "/dokum-kontrol", "/yok-boyle-bir-yol", "/cards"]
    kiyas("anahtarlı GET (okuma uçları; durum + ok/err + üst düzey anahtarlar)", [("GET", y, {"anahtar": True}) for y in GUVENLI_GET])
    # c) anahtarsız POST: 401 / geçiş listesi 403 (kaynak onayı istemi açan yoklama uçları hariç: izin kartı ve sesli soru üretir)
    YOKLAMA = {"/ping", "/agenda-tick", "/agenda-aktif", "/takvim-yenile"}
    kiyas("anahtarsız POST (tüm yollar, boş gövde)", [("POST", y, {"govde": {}}) for y in ALL_POST if y not in YOKLAMA] + [("POST", "/yok", {"govde": {}})])
    # d) anahtarlı ama pano dışı köken: yalnız-pano uçları 403 köken (işleyici çalışmaz → hepsi güvenli)
    PANO = sorted({y for y, _, kw in T["POST"] if kw.get("pano")} | {"/dusunme", "/notlar", "/geri-bildirim", "/bas-konus", "/baglam-dosya", "/kesisim", "/otonom"})
    kiyas("anahtarlı, köken yok: yalnız-pano uçları", [("POST", y, {"govde": {}, "anahtar": True}) for y in PANO])
    kiyas("anahtarlı, eklenti kökeni: yalnız-pano uçları", [("POST", y, {"govde": {}, "anahtar": True, "koken": "chrome-extension://" + "a" * 32}) for y in PANO])
    kiyas("anahtarlı, yabancı köken: hepsi 403", [("POST", y, {"govde": {}, "anahtar": True, "koken": "https://kotu.example"}) for y in ALL_POST])
    # e) anahtarlı, geçersiz gövde: JSON değil / dizi / sorgulu yol / bilinmeyen işlem
    kiyas("anahtarlı, bozuk JSON ve dizi gövde (400)", [("POST", y, {"anahtar": True, "ham": b"{bozuk"}) for y in ("/card", "/ingest", "/ayar", "/yok")]
          + [("POST", y, {"anahtar": True, "ham": b"[]"}) for y in ("/card", "/toplanti", "/prova")])
    kiyas("anahtarlı, sorgulu POST yolu tabloya da zincire de düşmez (404)", [("POST", y, {"govde": {}, "anahtar": True}) for y in ("/card?x=1", "/toplanti?islem=bitir", "/ayar?x")])
    GECERSIZ = {"islem": "__yok__", "komut": "__yok__"}
    YAN_ETKISIZ = ["/card", "/etiket", "/eylem", "/toplanti", "/card-ack", "/eylem-sonuc", "/kanit-iste", "/agenda-aktif", "/tek-kullanim", "/son-toplanti", "/ilet",
                   "/prova", "/kayit-eylem", "/kayit-not", "/belge-oneri", "/is-kopya", "/karar-onay", "/is-durum", "/dokum-kontrol", "/vt-bellek", "/toplanti-oturum",
                   "/yaklasan-tarihler", "/disa-aktar", "/eylem-karar", "/masaustu-altyazi", "/ortak-mik", "/komut", "/olay", "/kanit"]
    kiyas("anahtarlı, köken yok, geçersiz işlem (yan etkisiz uçlar)", [("POST", y, {"govde": dict(GECERSIZ), "anahtar": True}) for y in YAN_ETKISIZ], anahtar_kume=False)
    PANO_GUVENLI = ["/otonom", "/moderator", "/eylem-geri-al", "/eylem-sesli", "/arastirma", "/eposta-onemli", "/kesisim", "/tepki", "/proaktif", "/toplanti-hatirlat",
                    "/hatirlat", "/notlar", "/son-ac", "/konus-gecmis-sil", "/dusunme", "/tazi"]
    kiyas("anahtarlı pano, geçersiz işlem (yalnız-pano uçları)", [("POST", y, {"govde": dict(GECERSIZ), "anahtar": True, "koken": "pano"}) for y in PANO_GUVENLI], anahtar_kume=False)
    izl = open(iz, encoding="utf-8").read().splitlines() if os.path.exists(iz) else []
    ok("sahte claude/open/osascript model çağrısı görmedi (-p, --resume)", not [l for l in izl if " -p" in l or "--resume" in l], izl[:5])
    for r in R:
        lg = open(os.path.join(r["E"], "r.log"), encoding="utf-8", errors="replace").read()
        ok(f"{r['ad']}: aktarıcı günlüğünde yakalanmayan istek hatası yok", "Traceback" not in lg, lg[lg.find("Traceback"):][:600])
except SystemExit: pass
finally:
    for r in R:
        r["p"].terminate()
        try: r["p"].wait(5)
        except subprocess.TimeoutExpired: r["p"].kill()
    shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'KALDI: ' + str(len(HATA)) if HATA else 'GEÇTİ'}"); sys.exit(1 if HATA else 0)
