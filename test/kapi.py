#!/usr/bin/env python3
# Claude kapısı (aktarici/kapi.py, K1 v0.243.0): izin tablosu × iş türü × gizli kip / toplantı / sessiz mod / mesai / gece / ortak tavan, S141 (e-posta yalnız Claude), engelin ÇAĞRIDAN ÖNCE olması,
# tekrar önleme (okunamayan cevapta 30 dk → 2 sa → 8 sa; başarılıda tekrar_sn), arka planın ön plan turunu beklemesi, çağrı başına benzersiz istek/çıktı dosyası (eşzamanlı iki çağrı),
# tek kayıt biçimi (claude-cagri.jsonl; engel satır yazmaz, kapi.jsonl'e seyrek özet), değerlendirici entegrasyonu (öneksiz kimlik eşleme, kapı engelinde kural yedeği),
# gün içi önerinin ön denetimi (toplanti-sonrasi.py _pro_engel), beta belirteç sayımı (beta-veri.py _beta_belirtec). Birim: bölümler yalıtılmış ad alanında, sahte Brifing.app
# (subprocess sahte), sahte saat; gerçek claude çağrılmaz, ağ yok. Kurgu veri.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kapi.py      (kaldı → çıkış 1)
import datetime, json, os, re, secrets, shutil, subprocess as _sp, sys, tempfile, threading, time, types
sys.dont_write_bytecode = True; os.environ["SUFLOR_TEST_SOZ_DONGU_YOK"] = "1"
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="kapi-")
CAR = datetime.datetime(2026, 11, 11, 11, 0).timestamp()   # Çarşamba 11:00 (mesai)
CMT = datetime.datetime(2026, 11, 14, 11, 0).timestamp()   # Cumartesi 11:00
GECE = datetime.datetime(2026, 11, 11, 23, 30).timestamp()  # Çarşamba 23:30
def src(ad): return open(os.path.join(KOD, "aktarici", ad), encoding="utf-8").read()
def dilim(metin, bas, son): return metin[metin.index(bas):metin.index(son)]
EYLEM_SRC = dilim(src("eylem-menu.py"), "def eylem_model", "def _kem_id")
BS = src("brifing-ses.py"); CJ_SRC = dilim(BS, "def claude_json", "# --- Sesli brifing")

class Beyin:  # sahte beyin.py: seçim değiştirilebilir; kullanim gerçek biçim
    tur = "claude-code"
    @classmethod
    def secim(c, ayar, is_): return {"tur": c.tur, "model": "sonnet" if c.tur == "claude-code" else "gemini-x", "saglayici": None if c.tur == "claude-code" else "gemini"}
    @staticmethod
    def claude_secim(ayar, is_): return {"tur": "claude-code", "model": "sonnet"}
    @staticmethod
    def prova_args(ayar, istem, model=None): return ["-p", istem, "--model", model or "sonnet"]
    @staticmethod
    def yedek_var(ayar, sec): return False
    @staticmethod
    def yedek_satiri(*a): return "yedek"
    @staticmethod
    def kullanim(j):
        u = j.get("usage") or {}
        return {"giris": sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")), "okunan": u.get("cache_read_input_tokens") or 0,
                "cikti": u.get("output_tokens"), "maliyet": j.get("total_cost_usd") or 0}

def kur(ad, ayar=None, bolumler=("kapi.py",), eylem=True, degerlendir=False):
    d = os.path.join(T, ad); os.makedirs(d, exist_ok=True); app = os.path.join(d, "Brifing.app"); os.makedirs(app, exist_ok=True)
    durum = {"gizli": False, "toplanti": False, "sessiz": False, "saat": CAR, "cevap": lambda istem: "tamam", "bekle": 0.0, "istekler": [], "run": 0, "beyin_tek": 0, "claude": "/x/claude",
             "maliyet": 0.01, "is_error": False}
    lock = threading.Lock()
    def write(pairs):
        for yol, metin in pairs:
            with open(yol, "a", encoding="utf-8") as f: f.write(metin)
    def run(argv, **k):  # sahte "open -a Brifing.app --args --istek <dosya>"
        durum["run"] += 1; ist = argv[-1]; j = json.load(open(ist, encoding="utf-8")); durum["istekler"].append(os.path.basename(ist))
        if durum["bekle"]: time.sleep(durum["bekle"])
        istem = j["args"][1]; c = durum["cevap"](istem)
        if c is not None:
            r = {"result": c, "is_error": durum["is_error"], "total_cost_usd": durum["maliyet"], "duration_ms": 1200, "num_turns": 1,
                 "usage": {"input_tokens": 100, "cache_read_input_tokens": 800, "cache_creation_input_tokens": 300, "cache_creation": {"ephemeral_1h_input_tokens": 50}, "output_tokens": 40}}
            open(j["cikti"], "w", encoding="utf-8").write(json.dumps(r, ensure_ascii=False))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    sp = types.SimpleNamespace(run=run, TimeoutExpired=_sp.TimeoutExpired)
    def beyin_tek(is_, sec, istem, json_kip=False, sistem=None, zaman=180):
        durum["beyin_tek"] += 1; return "başka sağlayıcı cevabı", {"hata": False}
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "secrets": secrets, "subprocess": sp, "AYAR": dict(ayar or {}), "BASE": d, "LOCK": lock, "write": write,
          "SOHBET": {"acik": False}, "_KS": {"tur": None, "son": 0}, "print": lambda *a, **k: None, "_t": lambda tr, en: tr,
          "gizli_acik": lambda: durum["gizli"], "toplanti_var": lambda: durum["toplanti"], "aktif_dosya": lambda: None, "sessiz_acik": lambda: durum["sessiz"],
          "calisma_saatleri": lambda: ({0, 1, 2, 3, 4}, 540, 1080), "BEYIN": Beyin, "BRIFING_APP": app, "claude_yolu": lambda: durum["claude"], "claude_yalin": lambda: False,
          "beyin_tek": beyin_tek, "EYLEM_ZAMAN_SN": 5, "KAPI_SAAT": lambda: durum["saat"], "DG_SAAT": lambda: durum["saat"], "SOZ_SAAT": lambda: durum["saat"], "D": d, "DURUM": durum}
    for f in bolumler: exec(compile(src(f), f, "exec"), ns)
    exec(compile(CJ_SRC, "brifing-ses.py", "exec"), ns); ns["beyin_tek"] = beyin_tek  # dilimdeki gerçek beyin_tek yerine sahte
    if eylem: exec(compile(EYLEM_SRC, "eylem-menu.py", "exec"), ns)
    if degerlendir: exec(compile(src("degerlendir.py"), "degerlendir.py", "exec"), ns)
    ns["KAPI_BEKLE_SN"] = 0.6
    return ns
def satirlar(N, ad="claude-cagri.jsonl"):
    try: return [json.loads(l) for l in open(os.path.join(N["D"], ad), encoding="utf-8") if l.strip()]
    except OSError: return []

# --- 1) izin tablosu × iş türü × durum ---------------------------------------------------------------------------------------------------------
N = kur("tablo")
ARKA = [k for k, r in N["KAPI_TABLO"].items() if r["plan"] == "arka"]; ON = [k for k, r in N["KAPI_TABLO"].items() if r["plan"] == "on"]
SAATSIZ = {"dusunme", "degerlendir:mutabakat"}
ok("tablo: K1 işleri var (6 değerlendirici, düşünme, eylem, talimat, e-posta taslağı)", set(N["KAPI_TABLO"]) >= {"degerlendir:gun_ici", "degerlendir:toplanti_sonrasi", "degerlendir:belge_oneri", "degerlendir:is_kopya",
   "degerlendir:eposta", "degerlendir:mutabakat", "dusunme", "eylem", "talimat", "eposta_taslak"}, sorted(N["KAPI_TABLO"]))
ok("mesai içinde, olağan durumda hiçbir iş engellenmez", all(N["kapi_engel"](k, CAR) is None for k in N["KAPI_TABLO"]), {k: N["kapi_engel"](k, CAR) for k in N["KAPI_TABLO"]})
N["DURUM"]["gizli"] = True
ok("gizli kip: tüm arka plan işleri engel, ön plan serbest", all(N["kapi_engel"](k, CAR) == "gizli kip" for k in ARKA) and all(N["kapi_engel"](k, CAR) is None for k in ON))
N["DURUM"]["gizli"] = False; N["DURUM"]["toplanti"] = True
ok("toplantı sürerken: arka plan engel (toplantı sürüyor), ön plan serbest", all(N["kapi_engel"](k, CAR) == "toplantı sürüyor" for k in ARKA) and all(N["kapi_engel"](k, CAR) is None for k in ON))
N["DURUM"]["toplanti"] = False; N["DURUM"]["sessiz"] = True
ok("sessiz mod: yalnız kullanıcıya söyleyen değerlendiriciler (gün içi, toplantı sonrası) engel", N["kapi_engel"]("degerlendir:gun_ici", CAR) == "sessiz mod" and N["kapi_engel"]("degerlendir:toplanti_sonrasi", CAR) == "sessiz mod"
   and N["kapi_engel"]("degerlendir:belge_oneri", CAR) is None and N["kapi_engel"]("eylem", CAR) is None)
N["DURUM"]["sessiz"] = False
ok("hafta sonu (mesai dışı): arka plan engel, düşünme/mutabakat (gece düşünmesi istisnası) ve ön plan serbest",
   all(N["kapi_engel"](k, CMT) == "mesai dışı" for k in ARKA if k not in SAATSIZ) and all(N["kapi_engel"](k, CMT) is None for k in list(SAATSIZ) + ON))
ok("gece 23:30: arka plan engel (gece), düşünme serbest", all(N["kapi_engel"](k, GECE) == "gece" for k in ARKA if k not in SAATSIZ) and N["kapi_engel"]("dusunme", GECE) is None)
N2 = kur("gece-genis"); N2["calisma_saatleri"] = lambda: (set(range(7)), 0, 1440)
ok("çalışma saati 7/24 olsa da gece kuralı (soz_gece_bas/bit) arka planı durdurur", N2["kapi_engel"]("degerlendir:is_kopya", GECE) == "gece" and N2["kapi_engel"]("degerlendir:is_kopya", CAR) is None)
ok("bilinmeyen değerlendirici türü arka plan sayılır, bilinmeyen iş ön plan", N["kapi_kural"]("degerlendir:yeni")["plan"] == "arka" and N["kapi_kural"]("baska")["plan"] == "on")
# ortak tavan: bugünkü arka plan harcaması dosyadan
g = datetime.date.fromtimestamp(CAR).isoformat()
NT = kur("tavan")
with open(os.path.join(NT["D"], "claude-cagri.jsonl"), "w") as f:
    for is_, m in (("dusunme", 1.5), ("degerlendir:gun_ici", 1.0), ("giris", 0.6), ("bas-konus", 5.0), ("eylem", 2.0)): f.write(json.dumps({"at": g + "T03:10:00+03:00", "is": is_, "maliyet": m}) + "\n")
    f.write(json.dumps({"at": "2026-11-10T10:00:00+03:00", "is": "dusunme", "maliyet": 9}) + "\n")
ok("ortak tavan: bugünün arka plan işleri (düşünme + değerlendirici + giriş = 3,1 $) sayılır; ön plan ve dünkü satır sayılmaz", abs(NT["_kapi_usd_yukle"](CAR)["usd"] - 3.1) < 1e-6, NT["KAPI"]["usd"])
ok("tavan dolunca (varsayılan 3 $, degerlendir_gunluk_usd'den): arka plan engel (düşünme dahil), ön plan serbest",
   all(NT["kapi_engel"](k, CAR) == "günlük tavan" for k in ARKA) and all(NT["kapi_engel"](k, CAR) is None for k in ON) and NT["kapi_tavan_usd"]() == 3)
NT["AYAR"]["arka_gunluk_usd"] = 5
ok("ayar arka_gunluk_usd tavanı değiştirir; tavan=False ön denetimi tavana bakmaz", NT["kapi_engel"]("degerlendir:gun_ici", CAR) is None and NT["kapi_tavan_usd"]() == 5)
NT["AYAR"]["arka_gunluk_usd"] = 1; ok("tavan=False ile ön denetim tavanı atlar", NT["kapi_engel"]("degerlendir:gun_ici", CAR, tavan=False) is None and NT["kapi_engel"]("degerlendir:gun_ici", CAR) == "günlük tavan")
NT3 = kur("tavan-dg", ayar={"degerlendir_gunluk_usd": 0}); ok("degerlendir_gunluk_usd 0 (değerlendirici kapalı) öbür arka plan işlerini durdurmaz (tavan 3 $)", NT3["kapi_tavan_usd"]() == 3.0)

# --- 2) engel çağrıdan ÖNCE, satır yazmaz; seyrek özet ---------------------------------------------------------------------------------------------
N = kur("once"); N["DURUM"]["saat"] = CMT
r = N["eylem_model"]("x", is_adi="degerlendir:gun_ici")
ok("hafta sonu gün içi değerlendirmesi: Claude çağrılmadı (sahte Brifing.app hiç açılmadı), hata 'kapı: mesai dışı'", N["DURUM"]["run"] == 0 and r == (None, "kapı: mesai dışı"), (N["DURUM"]["run"], r))
for _ in range(5): N["eylem_model"]("x", is_adi="degerlendir:gun_ici")
oz = satirlar(N, "kapi.jsonl")
ok("engel claude-cagri.jsonl'e satır yazmaz; kapi.jsonl'de saatte en çok bir özet (6 engel → 1 satır, yalnız sayı)", not satirlar(N) and len(oz) == 1 and oz[0]["olay"] == "engel_ozet" and oz[0]["sayi"] == {"degerlendir:gun_ici|mesai dışı": 1}, oz)
v = N["kapi_view"](); ok("/status kapi: bugünkü engel sayısı (iş|neden)", v["engel"].get("degerlendir:gun_ici|mesai dışı") == 6 and v["bugun"]["engel"] == 6, v)
N["DURUM"]["saat"] = CMT + 3700; N["eylem_model"]("x", is_adi="degerlendir:gun_ici"); oz = satirlar(N, "kapi.jsonl")
ok("bir saat sonra ikinci özet yalnız aradaki farkla", len(oz) == 2 and oz[1]["sayi"] == {"degerlendir:gun_ici|mesai dışı": 6}, oz)
r = N["eylem_model"]("x", amac="talimat"); ok("hafta sonu ön plan (talimat) çağrılır", r == ("tamam", None) and N["DURUM"]["run"] == 1, r)

# --- 3) kayıt biçimi --------------------------------------------------------------------------------------------------------------------------------
N = kur("kayit")
r = N["eylem_model"]("x", amac="talimat"); c = satirlar(N)
GEREK = ("is", "model", "saglayici", "giris", "onbellek_oku", "onbellek_yaz", "onbellek_yaz_1s", "cikti", "maliyet", "sure_ms", "sonuc", "neden", "at", "onbellek_orani", "hata", "plan", "bekleme_ms")
ok("tek satır, tek biçim: yeni alanlar + eski alanlar (at, onbellek_orani, hata)", len(c) == 1 and all(k in c[0] for k in GEREK), c)
ok("sayılar: giriş toplam 1200, okuma 800, yazım 300 (1 sa payı 50), çıktı 40; iş adı talimat; sonuç tamam; ön plan", c and c[0]["giris"] == 1200 and c[0]["onbellek_oku"] == 800 and c[0]["onbellek_yaz"] == 300
   and c[0]["onbellek_yaz_1s"] == 50 and c[0]["cikti"] == 40 and c[0]["is"] == "talimat" and c[0]["sonuc"] == "tamam" and c[0]["plan"] == "on" and c[0]["onbellek_orani"] == 0.67, c)
ok("satırda metin yok (istem/cevap)", c and "tamam" not in json.dumps({k: v for k, v in c[0].items() if k != "sonuc"}))
N["eylem_model"]("x", amac="eposta"); ok("amac eposta → iş adı eposta_taslak", satirlar(N)[-1]["is"] == "eposta_taslak")
N["DURUM"]["cevap"] = lambda istem: None  # Brifing.app cevap yazmadı
r = N["eylem_model"]("x"); c = satirlar(N)[-1]
ok("cevapsız gerçek çağrı da kayda geçer: sonuc hata, maliyet 0, neden kısa", r == (None, "Claude yanıt vermedi") and c["sonuc"] == "hata" and c["maliyet"] == 0 and c["neden"] == "Claude yanıt vermedi", c)
N["DURUM"]["cevap"] = lambda istem: "tamam"; N["DURUM"]["is_error"] = True
N["eylem_model"]("x"); c = satirlar(N)[-1]; ok("Claude is_error → sonuc hata", c["sonuc"] == "hata" and c["hata"] is True, c)
N["DURUM"]["is_error"] = False
N["claude_json"](json.dumps({"result": "r", "total_cost_usd": 0.02, "usage": {"input_tokens": 10, "output_tokens": 5}}), "brifing", time.time(), False)
c = satirlar(N)[-1]; ok("kapı dışı claude_json (brifing vb.) da aynı yeni alanlarla yazar", c["is"] == "brifing" and c["sonuc"] == "tamam" and c["onbellek_oku"] == 0 and c["cikti"] == 5 and "plan" not in c, c)
N["DURUM"]["gizli"] = True; n0 = len(satirlar(N)); N["eylem_model"]("x", amac="talimat")
ok("gizli kipte ön plan çağrısı yapılır; satır (yalnız sayı) bugünkü gibi yazılır", N["DURUM"]["run"] >= 4 and len(satirlar(N)) == n0 + 1 and "x" not in json.dumps(satirlar(N)[-1]).replace("max", ""))
N["DURUM"]["gizli"] = False

# --- 4) S141: e-posta yalnız Claude --------------------------------------------------------------------------------------------------------------
N = kur("s141"); Beyin.tur = "openai-uyumlu"
r1 = N["eylem_model"]("x", amac="eposta"); r2 = N["eylem_model"]("x", is_adi="degerlendir:eposta"); r3 = N["eylem_model"]("x", amac="talimat")
ok("başka sağlayıcı seçiliyken e-posta taslağı ve e-posta değerlendirmesi claude-code'a gider; talimat seçili sağlayıcıya", r1 == ("tamam", None) and r2 == ("tamam", None) and N["DURUM"]["run"] == 2
   and N["DURUM"]["beyin_tek"] == 1 and r3[0] == "başka sağlayıcı cevabı", (r1, r2, r3, N["DURUM"]))
N["DURUM"]["claude"] = ""
r = N["eylem_model"]("x", amac="eposta"); ok("claude-code yoksa e-posta işi engel (başka sağlayıcıya düşmez)", r == (None, "kapı: sağlayıcı (yalnız Claude)") and N["DURUM"]["beyin_tek"] == 1, r)
Beyin.tur = "claude-code"

# --- 5) tekrar önleme ---------------------------------------------------------------------------------------------------------------------------
N = kur("tekrar"); D = N["DURUM"]; cagir = lambda: N["kapi_iste"]("degerlendir:is_kopya", lambda: N["eylem_model"]("x", is_adi="degerlendir:is_kopya"), karma="k1", coz=lambda h: None)
r = cagir(); ok("okunamayan cevap: sonuc okunamadi, kayıtta okunamadi", r["sonuc"] == "okunamadi" and satirlar(N)[-1]["sonuc"] == "okunamadi" and satirlar(N)[-1]["neden"] == "çıktı okunamadı", (r, satirlar(N)[-1:]))
r = cagir(); ok("aynı karma hemen: engel 'tekrar' (çağrı yok)", r["sonuc"] == "engel" and r["neden"] == "tekrar" and D["run"] == 1)
D["saat"] += 31 * 60; r = cagir(); ok("30 dk sonra yeniden sorulur, yine okunamadı", r["sonuc"] == "okunamadi" and D["run"] == 2)
D["saat"] += 90 * 60; r = cagir(); ok("ikinci okunamayandan sonra 2 sa: 1,5 sa sonra hâlâ engel", r["neden"] == "tekrar" and D["run"] == 2)
D["saat"] += 31 * 60; r = cagir(); ok("2 sa dolunca sorulur (3. okunamadı → 8 sa)", r["sonuc"] == "okunamadi" and D["run"] == 3 and abs(N["KAPI"]["tekrar"]["degerlendir:is_kopya|k1"]["bitis"] - D["saat"] - 8 * 3600) < 1)
r = N["kapi_iste"]("degerlendir:is_kopya", lambda: N["eylem_model"]("x", is_adi="degerlendir:is_kopya"), karma="k2", coz=lambda h: {"a": 1})
r2 = N["kapi_iste"]("degerlendir:is_kopya", lambda: ("y", None), karma="k2")
ok("başarılı cevaptan sonra aynı karma tekrar_sn (30 dk) Claude'a gitmez, son başarılı cevap döner (onbellek, maliyet 0)", r["sonuc"] == "tamam" and r["cozum"] == {"a": 1} and r2["sonuc"] == "onbellek"
   and r2["ham"] == r["ham"] and r2["cozum"] == {"a": 1} and r2["maliyet"] == 0.0, r2)
D["saat"] += 1801; r2 = N["kapi_iste"]("degerlendir:is_kopya", lambda: ("y", None), karma="k2"); ok("30 dk sonra yeniden sorulabilir", r2["sonuc"] == "tamam")
# HTTP istek iş parçacığında arka plan işi beklemez (v0.243.1)
N["_KS"]["tur"] = {"soru": "x"}; N["KAPI_YEREL"].beklemesiz = True; t0 = time.time(); r = N["kapi_iste"]("degerlendir:belge_oneri", lambda: ("y", None)); N["KAPI_YEREL"].beklemesiz = False; N["_KS"]["tur"] = None
ok("istek iş parçacığında Konuş turu sürerken arka plan beklemeden engel", r["neden"] == "asistan meşgul" and time.time() - t0 < 0.3, (r, time.time() - t0))
import socketserver
class _H(socketserver.BaseRequestHandler):
    def handle(s): _H.sonuc = N["kapi_istek_parcacigi"]()
class _S(socketserver.ThreadingMixIn, socketserver.TCPServer): daemon_threads = True
_sv = _S(("127.0.0.1", 0), _H); threading.Thread(target=_sv.serve_forever, daemon=True).start()
import socket as _so; _c = _so.create_connection(_sv.server_address); _c.close(); time.sleep(0.3); _sv.shutdown(); _sv.server_close()
ok("kapi_istek_parcacigi: ThreadingMixIn istek iş parçacığını tanır, normal iş parçacığını tanımaz", getattr(_H, "sonuc", None) is True and N["kapi_istek_parcacigi"]() is False)

# --- 6) eşzamanlılık: benzersiz dosya, arka plan ön planı bekler ------------------------------------------------------------------------------------
N = kur("es"); D = N["DURUM"]; D["bekle"] = 0.4; D["cevap"] = lambda istem: "cevap:" + istem[-3:]
out = {}
def is_(ad, istem, **k): out[ad] = N["eylem_model"](istem, **k)
th = [threading.Thread(target=is_, args=("a", "istem-AAA"), kwargs={"amac": "talimat"}), threading.Thread(target=is_, args=("b", "istem-BBB"), kwargs={"is_adi": "dusunme"})]
for t in th: t.start()
for t in th: t.join()
ok("eşzamanlı iki çağrı birbirinin cevabını almaz", out.get("a") == ("cevap:AAA", None) and out.get("b") == ("cevap:BBB", None), out)
ok("istek dosyaları çağrı başına benzersiz, ortak istek.json/cikti.json yok", len(set(D["istekler"])) == 2 and "istek.json" not in D["istekler"] and not [f for f in os.listdir(os.path.join(N["D"], "eylem")) if f in ("istek.json", "cikti.json")], D["istekler"])
ok("istek/çıktı dosyaları çağrıdan sonra silinir", not [f for f in os.listdir(os.path.join(N["D"], "eylem")) if f.startswith(("istek-", "cikti-"))], os.listdir(os.path.join(N["D"], "eylem")))
D["bekle"] = 0; N["_KS"]["tur"] = {"soru": "x"}; t0 = time.time()
r = N["kapi_iste"]("degerlendir:belge_oneri", lambda: ("y", None))
ok("Konuş turu sürerken arka plan bekler, bitmezse engel 'asistan meşgul' (çağrı yok)", r["sonuc"] == "engel" and r["neden"] == "asistan meşgul" and time.time() - t0 >= 0.5)
r = N["kapi_iste"]("eylem", lambda: ("y", None)); ok("Konuş turu sürerken ön plan beklemez", r["sonuc"] == "tamam")
def bitir(): time.sleep(0.25); N["_KS"]["tur"] = None
threading.Thread(target=bitir).start(); r = N["kapi_iste"]("degerlendir:belge_oneri", lambda: ("y", None))
ok("tur biterse bekleyen arka plan işi çağrılır", r["sonuc"] == "tamam")
# v0.243.2: kilit tutan işlerde (e-posta, iş kopyası) tablo bekle_sn genel beklemeyi kısaltır
ok("e-posta ve iş kopyası tablosunda bekle_sn 10", N["KAPI_TABLO"]["degerlendir:eposta"].get("bekle_sn") == 10 and N["KAPI_TABLO"]["degerlendir:is_kopya"].get("bekle_sn") == 10)
_eski_b, _eski_t = N["KAPI_BEKLE_SN"], N["KAPI_TABLO"]["degerlendir:eposta"]["bekle_sn"]; N["KAPI_BEKLE_SN"] = 5; N["KAPI_TABLO"]["degerlendir:eposta"]["bekle_sn"] = 0.3
N["_KS"]["tur"] = {"soru": "x"}; t0 = time.time(); r = N["kapi_iste"]("degerlendir:eposta", lambda: ("y", None)); gecen = time.time() - t0; N["_KS"]["tur"] = None
N["KAPI_BEKLE_SN"], N["KAPI_TABLO"]["degerlendir:eposta"]["bekle_sn"] = _eski_b, _eski_t
ok("bekle_sn'li iş Konuş turunda genel süre yerine kendi süresi kadar bekler", r["neden"] == "asistan meşgul" and 0.25 <= gecen < 2, (r, gecen))
# ortak sıra: ES=2 → üçüncü arka plan işi bekler
N["KAPI_SIRA_SN"] = 0.3; ev = threading.Event(); sonuc3 = {}
def uzun(): ev.wait(2); return ("y", None)
t1 = threading.Thread(target=lambda: N["kapi_iste"]("degerlendir:is_kopya", uzun)); t2 = threading.Thread(target=lambda: N["kapi_iste"]("degerlendir:belge_oneri", uzun))
t1.start(); t2.start(); time.sleep(0.1)
r = N["kapi_iste"]("degerlendir:eposta", lambda: ("y", None)); r_on = N["kapi_iste"]("talimat", lambda: ("y", None)); ev.set(); t1.join(); t2.join()
ok("ortak sıra (2) doluyken üçüncü arka plan işi bekler (zaman aşımında 'sıra dolu'), ön plan atlar", r["neden"] == "sıra dolu" and r_on["sonuc"] == "tamam", (r, r_on))
# tavan muhasebesi: arka plan çağrısının maliyeti belleğe eklenir
N = kur("usd"); N["eylem_model"]("x", is_adi="degerlendir:is_kopya"); N["eylem_model"]("x", amac="talimat")
ok("arka plan çağrısının ölçülen maliyeti ortak tavana eklenir; ön plan eklenmez", abs(N["kapi_view"]()["arka_usd"] - 0.01) < 1e-9, N["kapi_view"]())

# --- 7) değerlendirici entegrasyonu ---------------------------------------------------------------------------------------------------------------
SEMA = {"kararlar": ("soyle", "gec"), "yedek": "soyle", "tanim": {}, "metin": False}
N = kur("dg", degerlendir=True); D = N["DURUM"]
D["cevap"] = lambda istem: json.dumps([{"id": "42", "karar": "gec", "oncelik": 1, "neden": "eski"}, {"id": "gec:7", "karar": "soyle", "oncelik": 2, "neden": "önemli"}])
r = N["degerlendir"]("gun_ici", [{"id": "belge:42", "metin": "Belge önerisi"}, {"id": "gec:7", "metin": "Gecikmiş iş"}], soru="?", sema=SEMA)
ok("öneksiz kimlik ('42') tek anlamlı eşleşmede 'belge:42'ye çevrilir; cevap atılmaz", [(x["id"], x["karar"], x["kaynak"]) for x in r] == [("belge:42", "gec", "model"), ("gec:7", "soyle", "model")], r)
c = [x for x in satirlar(N) if x["is"] == "degerlendir:gun_ici"]
ok("değerlendirici çağrısı kapıdan geçer: tek satır, sonuc tamam, arka plan, maliyet ölçülen", len(c) == 1 and c[0]["sonuc"] == "tamam" and c[0]["plan"] == "arka" and c[0]["maliyet"] == 0.01, c)
dgk = [json.loads(l) for l in open(os.path.join(N["D"], "degerlendir.jsonl"))]; ok("degerlendir.jsonl çağrı maliyeti kapının ölçümünden", [x for x in dgk if x["olay"] == "cagri"][0]["maliyet"] == 0.01, dgk)
ok("dg_kimlik_esle: belirsiz önek (iki adayda '7') eşlenmez; '[aday x]' biçimi temizlenir", N["dg_kimlik_esle"]("7", {"gec:7", "belge:7"}) == "7" and N["dg_kimlik_esle"]("aday belge:3", {"belge:3"}) == "belge:3"
   and N["dg_kimlik_esle"]("3", {"belge:3", "x"}) == "belge:3" and N["dg_kimlik_esle"]("y", {"x"}) == "y")
D["saat"] += 3600; D["cevap"] = lambda istem: json.dumps([{"id": "7", "karar": "gec", "oncelik": 1, "neden": "x"}])
r = N["degerlendir"]("gun_ici", [{"id": "gec:7", "metin": "Gecikmiş iş 2"}, {"id": "belge:7", "metin": "Belge 2"}], soru="?", sema=SEMA)
ok("belirsiz öneksiz kimlik: iki aday da kural yedeğine düşer", all(x["kaynak"] == "yedek" for x in r), r)
run0 = D["run"]; D["saat"] += 700
r = N["degerlendir"]("gun_ici", [{"id": "gec:7", "metin": "Gecikmiş iş 2"}, {"id": "belge:7", "metin": "Belge 2"}], soru="?", sema=SEMA)
ok("aynı aday kümesi okunamadıktan sonra (değerlendiricinin 10 dk'sı geçse de) kapı 30 dk sormaz: yedek 'kapı: tekrar'", D["run"] == run0 and r[0]["yedek_neden"] == "kapı: tekrar", r)
D["saat"] = CMT; run0 = D["run"]; n_dg = len(open(os.path.join(N["D"], "degerlendir.jsonl")).readlines())
r = N["degerlendir"]("is_kopya", [{"id": "c1", "metin": "Aynı iş mi"}], soru="?", sema=dict(SEMA, kararlar=("ayni", "farkli", "emin_degil"), yedek="emin_degil"))
ok("hafta sonu iş kopyası: Claude çağrılmaz, kural yedeği 'kapı: mesai dışı', degerlendir.jsonl'e çağrı/yedek satırı yazılmaz",
   D["run"] == run0 and r[0]["kaynak"] == "yedek" and r[0]["yedek_neden"] == "kapı: mesai dışı" and len(open(os.path.join(N["D"], "degerlendir.jsonl")).readlines()) == n_dg, r)
ok("kapı engelinden sonra değerlendiricinin 'son çağrı başarısız' süresi başlamaz", "is_kopya" not in N["DG"]["hata_t"])
ok("dg_tavan_asildi kapının ortak tavanını kullanır", N["dg_tavan_asildi"]() == N["kapi_tavan_asildi"]())
# v0.243.1 gerileme: başarılı "sonra" kararından sonra 30 dk içinde aynı aday kümesi yeniden gelince yedek "soyle"ye dönmemeli
N = kur("dg-sonra", degerlendir=True); D = N["DURUM"]; SEMA3 = {"kararlar": ("soyle", "sonra", "gec"), "yedek": "soyle", "kisa": ("sonra",), "tanim": {}, "metin": False}
D["cevap"] = lambda istem: json.dumps([{"id": "gec:9", "karar": "sonra", "oncelik": 1, "neden": "şimdi değil"}])
A9 = [{"id": "gec:9", "metin": "Gecikmiş iş 9"}]
def dg_tur(): N["DG"]["onb"] = {}; N["DG"]["tur_t"] = {}; return N["degerlendir"]("gun_ici", A9, soru="?", sema=SEMA3)  # önbellek boşaltılır: aynı küme yeniden kapıya gelir
r1 = dg_tur(); run1 = D["run"]
D["saat"] += 600; usd1 = N["DG"]["usd"]["usd"]; n_cagri = sum(1 for l in open(os.path.join(N["D"], "degerlendir.jsonl")) if '"olay": "cagri"' in l)
r2 = dg_tur()
ok("gün içi 'sonra' → 10 dk sonra aynı küme: Claude çağrılmadı, karar yine 'sonra' (yedek 'soyle' değil), maliyet ve çağrı satırı eklenmedi",
   r1[0]["karar"] == "sonra" and r2[0]["karar"] == "sonra" and r2[0]["kaynak"] == "onbellek" and D["run"] == run1 and N["DG"]["usd"]["usd"] == usd1
   and sum(1 for l in open(os.path.join(N["D"], "degerlendir.jsonl")) if '"olay": "cagri"' in l) == n_cagri, (r1, r2))
D["saat"] += 1300; r3 = dg_tur(); ok("30 dk dolunca yeniden Claude'a sorulur", D["run"] == run1 + 1 and r3[0]["kaynak"] == "model", r3)
D["cevap"] = lambda istem: "bozuk"; A9[0]["metin"] = "Gecikmiş iş 9b"; D["saat"] += 3600
r4 = dg_tur(); D["saat"] += 700; run4 = D["run"]; r5 = dg_tur()
ok("okunamayan cevaptan sonra aynı küme: kapı 'tekrar' engeli → kural yedeği (çağrı yok)", r4[0]["kaynak"] == "yedek" and r5[0]["kaynak"] == "yedek" and r5[0]["yedek_neden"] == "kapı: tekrar" and D["run"] == run4, (r4, r5))

# --- 8) gün içi öneri ön denetimi (toplanti-sonrasi.py _pro_engel) -----------------------------------------------------------------------------
N = kur("pro", bolumler=("kapi.py", "toplanti-sonrasi.py"), eylem=False); N["soz_aday"] = lambda *a, **k: {"karar": "simdi"}
ok("söz kapısı yüklüyken bile hafta sonu gün içi taraması değerlendiriciden ÖNCE durur (mesai dışı)", N["_pro_engel"](CMT, True) == "mesai dışı")
N["DURUM"]["toplanti"] = True; ok("toplantı sürerken değerlendiriciden önce durur", N["_pro_engel"](CAR, True) == "toplantı sürüyor")
N["DURUM"]["toplanti"] = False; N["DURUM"]["sessiz"] = True; ok("sessiz modda değerlendiriciden önce durur", N["_pro_engel"](CAR, True) == "sessiz mod")
N["DURUM"]["sessiz"] = False; ok("gece (23:30) değerlendiriciden önce durur", N["_pro_engel"](GECE, True) == "gece")
ok("mesai içinde kapı engeli yok (sonraki kaynak kuralları işler)", N["_pro_engel"](CAR, True) not in ("mesai dışı", "gece", "toplantı sürüyor", "sessiz mod"), N["_pro_engel"](CAR, True))

# --- 9) beta belirteç sayımı (beta-veri.py) -----------------------------------------------------------------------------------------------------
bv = src("beta-veri.py"); B = {}; exec(compile(dilim(bv, "def _beta_sayi", "def _beta_maliyet"), "beta-veri.py", "exec"), B)
eski = B["_beta_belirtec"]({"is": "bas-konus", "giris": 1000, "onbellek_orani": 0.79, "yazim": 150, "cikis": "hoparlör"})
ok("eski Konuş satırı: okuma = giriş × oran (790), yazım 'yazim', ses aygıtı 'cikis' çıktı sayılmaz", eski == {"giris": 1000, "cikti": 0, "onbellek_yaz": 150, "onbellek_oku": 790}, eski)
yeni = B["_beta_belirtec"]({"is": "bas-konus", "giris": 1000, "onbellek_oku": 800, "onbellek_yaz": 150, "yazim": 150, "onbellek_yaz_1s": 20, "cikti": 60, "cikis_aygit": "kulaklık", "onbellek_orani": 0.8})
ok("yeni satır: yazım bir kez (yazim + onbellek_yaz çifte sayılmaz), 1 sa payı ayrıca eklenmez", yeni == {"giris": 1000, "cikti": 60, "onbellek_yaz": 150, "onbellek_oku": 800}, yeni)
top = B["_beta_belirtec"]({"is": "toplanti", "giris": 50, "onbellek_yaz": 100, "onbellek_yaz_1s": 30, "onbellek_oku": 2000, "cikis": 70})
ok("toplantı satırı: giriş toplama çevrilir (50+130+2000), yazım 5 dk + 1 sa, çıktı sayı olan 'cikis'", top == {"giris": 2180, "cikti": 70, "onbellek_yaz": 130, "onbellek_oku": 2000}, top)
cj = B["_beta_belirtec"]({"is": "degerlendir:gun_ici", "giris": 1200, "onbellek_oku": 800, "onbellek_yaz": 300, "onbellek_yaz_1s": 50, "cikti": 40})
ok("kapı satırı olduğu gibi", cj == {"giris": 1200, "cikti": 40, "onbellek_yaz": 300, "onbellek_oku": 800}, cj)

shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not HATA else 'KALDI'}: {len(HATA)} hata")
sys.exit(1 if HATA else 0)
