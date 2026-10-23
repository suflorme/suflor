#!/usr/bin/env python3
# Yapay zekâ sağlayıcısı seçimi (Faz 11 Aşama 4, aktarici/saglayici.py): seçenek ↔ "beyin" ayarı (sg_profil, sg_ad, sg_yaz; elle yazılmış model korunur),
# beyin.py secim()'in yazılan ayarı doğru okuması, teshis.py beta seçeneğinin (yalnız tür) aynı ayrımı yapması, Anahtar Zinciri yazımının biçim denetimi
# (deneme kipinde Anahtar Zinciri'ne dokunulmaz), anahtar denemesi sahte sunucuya, Ollama kurulumu sahte sürümle (SHA-256 uyuşmazlığı, arşiv denetimi,
# model indirme ilerlemesi), deneme aktarıcısında panodaki ⚙ Ayarlar (beyin_* satırları, anahtarsız seçenek reddi, Varsayılanlara dön dışında) ve Ollama'nın
# yalnız ayar onu gösterirken açılıp kapanması (OLLAMA_CONTEXT_LENGTH, 127.0.0.1), /status beyin sağlığı; kurulum sihirbazının /api/beyin/anahtar ve
# kur/tamamla'nın beyin.varsayilan yazması (deneme ev klasörü).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/saglayici.py      (~20 sn; kaldı → çıkış 1)
import hashlib, http.server, importlib.util, io, json, os, re, shutil, socket, subprocess, sys, tarfile, tempfile, threading, time, urllib.error, urllib.request

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = ""  # Anahtar Zinciri'ne dokunulmaz (boş = anahtar yok)
SG = yukle("sg_t", os.path.join(KOD, "aktarici", "saglayici.py")); BY = yukle("beyin_t", os.path.join(KOD, "aktarici", "beyin.py"))
sys.path.insert(0, KOD); import teshis
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
def bos_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def bekle(kosul, sn=10):
    son = time.time() + sn
    while time.time() < son:
        if kosul(): return True
        time.sleep(0.2)
    return False

# --- 1. seçenek ↔ ayar -----------------------------------------------------------------------------------------------------------
a = {}
kontrol("ayarsız: varsayılan Claude Code, işler boş", SG.sg_secim(a) == {"varsayilan": "claude-code", "konus": "", "ceviri": "", "proje_karti": ""})
kontrol("Claude Code seçimi ayara bir şey yazmaz", SG.sg_yaz(a, {"varsayilan": "claude-code"}) is None and "beyin" not in a)
kontrol("gemini varsayılan", SG.sg_yaz(a, {"varsayilan": "gemini"}) is None and a["beyin"]["varsayilan"]["saglayici"] == "gemini" and a["beyin"]["varsayilan"]["anahtar"] is None)
s = BY.secim(a, "konus")
kontrol("beyin.py: Konuş Gemini'ye (adres hazır, öğe suflor-gemini, effort low)", s["tur"] == "openai-uyumlu" and s["adres"] == BY.HAZIR["gemini"] and s["anahtar"] == "suflor-gemini" and s["effort"] == "low", s)
kontrol("beyin.py: ayardaki gemini_anahtar öğesi geçerli", BY.secim(dict(a, gemini_anahtar="benim-oge"), "konus")["anahtar"] == "benim-oge")
SG.sg_yaz(a, {"ceviri": "claude-code", "konus": "ollama"})
kontrol("iş başına: çeviri Claude Code, Konuş yerel", SG.sg_secim(a) == {"varsayilan": "gemini", "konus": "ollama", "ceviri": "claude-code", "proje_karti": ""}, SG.sg_secim(a))
s = BY.secim(a, "konus")
kontrol("beyin.py: Konuş Ollama'ya (127.0.0.1:11434, effort none)", s["adres"] == "http://127.0.0.1:11434/v1" and s["effort"] == "none" and s["fiyat"] is None, s)
kontrol("beyin.py: çeviri claude-code (haiku)", BY.secim(a, "ceviri") == {"tur": "claude-code", "model": "haiku"})
kontrol("sg_etkin: proje kartı varsayılanı izler", SG.sg_etkin(a)["proje_karti"] == "gemini")
a["beyin"]["konus"]["model"] = "qwen3:4b"; SG.sg_yaz(a, {"konus": "ollama"})
kontrol("aynı seçenek yeniden: elle yazılmış model korunur", a["beyin"]["konus"]["model"] == "qwen3:4b")
b = dict(a, ollama_port=11499); SG.sg_yaz(b, {"proje_karti": "ollama"})
kontrol("ollama_port: adres yazılır, ad yine ollama", b["beyin"]["proje_karti"]["adres"] == "http://127.0.0.1:11499/v1" and SG.sg_ad(b["beyin"]["proje_karti"]) == "ollama")
kontrol("ozel tanımsızken hata", SG.sg_yaz(dict(a), {"konus": "ozel"}) is not None)
o = dict(a, beyin_ozel={"adres": "https://api.ornek.com/v1", "model": "m-1"}); SG.sg_yaz(o, {"konus": "ozel"})
kontrol("ozel: adres + model + öğe suflor-ozel", {k: v for k, v in o["beyin"]["konus"].items() if v is not None} == {"tur": "openai-uyumlu", "adres": "https://api.ornek.com/v1", "model": "m-1", "anahtar": "suflor-ozel"})
s = BY.secim(o, "konus")
kontrol("beyin.py: ozel (varsayılan Gemini'yken) → saglayici diger, effort/öğe sızmaz", s["saglayici"] == "diger" and s["effort"] is None and s["anahtar"] == "suflor-ozel" and s["fiyat"] is None, s)
kontrol("LM Studio (127.0.0.1:1234) ollama sayılmaz", SG.sg_ad({"tur": "openai-uyumlu", "adres": "http://127.0.0.1:1234/v1"}) == "ozel")
SG.sg_yaz(a, {"konus": "", "ceviri": "", "varsayilan": "claude-code"})
kontrol("hepsi geri: beyin anahtarı kalkar", "beyin" not in a, a)
kontrol("bilinmeyen iş/seçenek reddedilir", SG.sg_yaz({}, {"toplanti": "gemini"}) and SG.sg_yaz({}, {"konus": "x"}))

# --- 2. beta: yalnız seçenek, aynı ayrım -------------------------------------------------------------------------------------------
for d in ({}, {"beyin": {"konus": SG.sg_profil("ollama", {}), "varsayilan": SG.sg_profil("gemini", {})}}, o, b):
    tb = teshis.beyin_secenek(d); sg = SG.sg_secim(d)
    kontrol(f"teshis.beyin_secenek = sg_secim ({sorted(set(sg.values()))})", all(tb["beyin_" + k] == v for k, v in sg.items()), (tb, sg))
p = teshis.temizle(teshis.beyin_secenek(o))
kontrol("beta süzgeci: seçenek geçer, adres/model gitmez", p["beyin_konus"] == "ozel" and "api.ornek.com" not in json.dumps(p) and teshis.temizle({"beyin_konus": "api.ornek.com"})["beyin_konus"] == "?")

# --- 3. Anahtar Zinciri (deneme kipi) + anahtar denemesi ---------------------------------------------------------------------------
kontrol("kısa/boşluklu anahtar reddedilir", SG.sg_anahtar_yaz("suflor-ozel", "kisa") and SG.sg_anahtar_yaz("suflor-ozel", "abc def ghi jkl mno pqr"))
kontrol("tırnak/ters bölü içeren anahtar reddedilir (security -i alıntısı)", SG.sg_anahtar_yaz("suflor-ozel", 'abcdefghijklmnop"; delete') is not None)
kontrol("geçersiz öğe adı reddedilir", SG.sg_anahtar_yaz("a b", "A" * 20) is not None)
kontrol("geçerli anahtar deneme kipinde yazılmış sayılır", SG.sg_anahtar_yaz("suflor-ozel", "AIza" + "x" * 30) is None)
GELEN = []
class Api(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        GELEN.append((self.path, self.headers.get("Authorization")))
        kod = 200 if self.headers.get("Authorization") == "Bearer DOGRU-ANAHTAR-123456" else 401
        self.send_response(kod); self.end_headers(); self.wfile.write(b'{"data":[]}')
    def log_message(self, *a): pass
api_port = bos_port(); threading.Thread(target=http.server.HTTPServer(("127.0.0.1", api_port), Api).serve_forever, daemon=True).start()
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = "DOGRU-ANAHTAR-123456"
kontrol("anahtar denemesi: model listesi, Bearer başlığı", SG.sg_anahtar_dene(f"http://127.0.0.1:{api_port}/v1", "x") == ("iyi", "") and GELEN[-1] == ("/v1/models", "Bearer DOGRU-ANAHTAR-123456"), GELEN)
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = "YANLIS-ANAHTAR-123456"
kontrol("yanlış anahtar → 'anahtar'", SG.sg_anahtar_dene(f"http://127.0.0.1:{api_port}/v1", "x")[0] == "anahtar")
kontrol("http (yerel olmayan) adres reddedilir", SG.sg_anahtar_dene("http://ornek.com/v1", "x")[0] == "ag")
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = ""
kontrol("anahtar yoksa denenmez", SG.sg_anahtar_dene(f"http://127.0.0.1:{api_port}/v1", "x")[0] == "anahtar")

# --- 4. Ollama kurulumu (sahte sürüm) -------------------------------------------------------------------------------------------------
GEC = tempfile.mkdtemp(prefix="suflor-sg-")
SAHTE = r'''#!/usr/bin/python3
# sahte ollama: yalnız "serve" — /api/version, /api/tags, /api/pull (akışlı ilerleme, sonra bildirim dosyası); ortamı kayda yazar
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
if sys.argv[1:2] != ["serve"]: sys.exit(0)
h, p = os.environ["OLLAMA_HOST"].rsplit(":", 1); mod = os.environ["OLLAMA_MODELS"]
os.makedirs(mod, exist_ok=True)
json.dump({k: os.environ.get(k) for k in ("OLLAMA_HOST", "OLLAMA_CONTEXT_LENGTH", "OLLAMA_MODELS")}, open(os.path.join(mod, "..", "ortam.json"), "w"))
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"version":"0-sahte"}')
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}"); ad, _, et = b["model"].partition(":")
        self.send_response(200); self.end_headers()
        for c in (0, 1 << 27, 1 << 28):
            self.wfile.write((json.dumps({"status": "pulling", "total": 1 << 28, "completed": c}) + "\n").encode()); self.wfile.flush()
        y = os.path.join(mod, "manifests", "registry.ollama.ai", "library", ad); os.makedirs(y, exist_ok=True); open(os.path.join(y, et), "w").write("{}")
        self.wfile.write(b'{"status":"success"}\n')
    def log_message(self, *a): pass
HTTPServer((h, int(p)), H).serve_forever()
'''
paket = os.path.join(GEC, "sunucu"); os.makedirs(paket)
bilgi = tarfile.TarInfo("ollama"); veri = SAHTE.encode(); bilgi.size = len(veri); bilgi.mode = 0o755
with tarfile.open(os.path.join(paket, "ollama-darwin.tgz"), "w:gz") as t: t.addfile(bilgi, io.BytesIO(veri))
kotu = tarfile.TarInfo("../kacis"); kotu.size = 1
with tarfile.open(os.path.join(paket, "kotu.tgz"), "w:gz") as t: t.addfile(kotu, io.BytesIO(b"x"))
sha = hashlib.sha256(open(os.path.join(paket, "ollama-darwin.tgz"), "rb").read()).hexdigest()
class Dosya(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=paket, **k)
    def log_message(self, *a): pass
dosya_port = bos_port(); threading.Thread(target=http.server.HTTPServer(("127.0.0.1", dosya_port), Dosya).serve_forever, daemon=True).start()
ol_port = bos_port()
def kur(ortak, url, sha_):
    os.environ["SUFLOR_TEST_OLLAMA_URL"] = url; os.environ["SUFLOR_TEST_OLLAMA_SHA"] = sha_
    dy = os.path.join(ortak, "ollama-kur.json"); os.makedirs(ortak, exist_ok=True); SG.sg_ollama_kur(ortak, dy, port=ol_port); return json.load(open(dy))
o1 = os.path.join(GEC, "ortak1")
d = kur(o1, f"http://127.0.0.1:{dosya_port}/ollama-darwin.tgz", "0" * 64)
kontrol("SHA-256 uyuşmazlığı → hata, araç kurulmaz", d["durum"] == "hata" and "SHA" in d.get("mesaj", "") and not SG.sg_ollama_kurulu(o1), d)
o2 = os.path.join(GEC, "ortak2")
d = kur(o2, f"http://127.0.0.1:{dosya_port}/kotu.tgz", hashlib.sha256(open(os.path.join(paket, "kotu.tgz"), "rb").read()).hexdigest())
kontrol("klasör dışına çıkan arşiv öğesi → hata", d["durum"] == "hata" and not os.path.exists(os.path.join(o2, "kacis")), d)
o3 = os.path.join(GEC, "ortak3")
d = kur(o3, f"http://127.0.0.1:{dosya_port}/ollama-darwin.tgz", sha)
kontrol("kurulum: araç + model hazır", d["durum"] == "hazir" and SG.sg_ollama_kurulu(o3) and SG.sg_ollama_model_var(o3), d)
ort = json.load(open(os.path.join(o3, "ollama", "ortam.json")))
kontrol("kurulumda sunucu: 127.0.0.1, bağlam 32768, modeller ortak klasörde", ort == {"OLLAMA_HOST": f"127.0.0.1:{ol_port}", "OLLAMA_CONTEXT_LENGTH": "32768", "OLLAMA_MODELS": os.path.join(o3, "ollama", "modeller")}, ort)
kontrol("kurulum bitince geçici sunucu kapandı", bekle(lambda: not SG.sg_ollama_acik(ol_port), 5))
kontrol("indirme dosyası silindi", not os.path.exists(os.path.join(o3, "ollama", ".indirme.tgz")))
kontrol("sağlık: yerel model hazır", SG.sg_saglik({"ortak": o3, "beyin": {"konus": SG.sg_profil("ollama", {})}, "ollama_port": ol_port}, True)[-1]["ok"])
kontrol("sağlık: yerel seçili ama kurulu değil → ⚠", not SG.sg_saglik({"ortak": o1, "beyin": {"konus": SG.sg_profil("ollama", {})}})[-1]["ok"])
kontrol("sağlık: Gemini anahtarsız → ⚠", not [x for x in SG.sg_saglik({"beyin": {"varsayilan": SG.sg_profil("gemini", {})}}, True) if x["ad"] == "gemini"][0]["ok"])

# --- 5. deneme aktarıcısı: panodaki Ayarlar + Ollama'yı başlatma -------------------------------------------------------------------------------
subprocess.run(["pkill", "-f", "relay.py --dir " + GEC], capture_output=True)
RL = os.path.join(GEC, "relay"); shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(RL, "aktarici")); shutil.copy(os.path.join(KOD, "relay.py"), RL)
shutil.copy(os.path.join(KOD, "manifest.json"), RL); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(RL, "pano"))
rport = bos_port(); ayar_yol = os.path.join(GEC, "ayar.json"); os.makedirs(os.path.join(GEC, "uyg"))
json.dump({"port": rport, "uygulama": os.path.join(GEC, "uyg"), "ortak": o3, "proje": os.path.join(GEC, "proje"), "ollama_port": ol_port}, open(ayar_yol, "w"))
ort = dict(os.environ, SUFLOR_AYAR=ayar_yol, SUFLOR_TEST_OLLAMA="1", SUFLOR_TEST_BEYIN_ANAHTAR="", PYTHONDONTWRITEBYTECODE="1")
canli = os.path.join(GEC, "canli"); gunluk = open(os.path.join(GEC, "relay.log"), "w")
rp = subprocess.Popen([sys.executable, os.path.join(RL, "relay.py"), "--dir", canli, "--port", str(rport)], env=ort, stdout=gunluk, stderr=subprocess.STDOUT, cwd=RL)
try:
    def acik():
        try: urllib.request.urlopen(f"http://127.0.0.1:{rport}/ping", timeout=1); return True
        except urllib.error.HTTPError: return True
        except Exception: return False
    bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")) and acik(), 20)
    an = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def istek(yol, govde=None):
        r = urllib.request.Request(f"http://127.0.0.1:{rport}{yol}", data=json.dumps(govde).encode() if govde is not None else None,
                                   headers={"X-Suflor-Anahtar": an, "Origin": f"http://127.0.0.1:{rport}", "Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(r, timeout=10))
    st = istek("/status"); ay = st["ayarlar"]
    kontrol("/status beyin: ayarsızken Claude Code", st["beyin"]["etkin"] == {"konus": "claude-code", "ceviri": "claude-code", "proje_karti": "claude-code"}, st.get("beyin"))
    kontrol("Ayarlar: beyin_* değerleri + kullanılabilirlik", ay["deger"]["beyin_varsayilan"] == "claude-code" and ay["deger"]["beyin_konus"] == "" and ay["beyin"]["ollama"] is True and ay["beyin"]["gemini"] is False, ay.get("beyin"))
    kontrol("Varsayılanlara dön yapay zekâ seçimine dokunmaz", not any(k.startswith("beyin_") for k in ay["varsayilan"]))
    r = istek("/ayar", {"degisen": {"beyin_konus": "gemini"}})
    kontrol("anahtarsız Gemini reddedilir", r.get("ok") is False and "beyin_konus" in r.get("hata", {}), r)
    kontrol("Ollama seçilmeden açılmadı", not SG.sg_ollama_acik(ol_port))
    r = istek("/ayar", {"degisen": {"beyin_konus": "ollama"}})
    kontrol("Konuş → yerel model kaydedildi", r.get("ok") and json.load(open(ayar_yol))["beyin"]["konus"]["saglayici"] == "ollama", r)
    kontrol("ayar yerel modeli gösterince Ollama açıldı", bekle(lambda: SG.sg_ollama_acik(ol_port), 10))
    kontrol("günlük: OLLAMA: başlatıldı", "OLLAMA: başlatıldı" in open(os.path.join(GEC, "relay.log")).read())
    st = istek("/status")
    kontrol("/status beyin: Konuş ollama, sağlık ✓", st["beyin"]["etkin"]["konus"] == "ollama" and all(x["ok"] for x in st["beyin"]["saglik"] if x["ad"] == "ollama"), st["beyin"])
    r = istek("/ayar", {"degisen": {"beyin_konus": ""}})
    kontrol("Konuş varsayılana dönünce Ollama kapandı", r.get("ok") and bekle(lambda: not SG.sg_ollama_acik(ol_port), 10) and "beyin" not in json.load(open(ayar_yol)))
    r = istek("/ayar", {"degisen": {"beyin_proje_karti": "bilinmeyen"}})
    kontrol("bilinmeyen seçenek reddedilir", r.get("ok") is False)
finally:
    rp.terminate(); rp.wait(5); gunluk.close()
    subprocess.run(["pkill", "-f", os.path.join(o3, "ollama", "ollama")], capture_output=True)

# --- 6. kurulum sihirbazı (deneme ev klasörü) ------------------------------------------------------------------------------------------
EVK = os.path.join(GEC, "ev"); os.makedirs(EVK)
kp = bos_port()
ort = dict(os.environ, SUFLOR_EV=EVK, SUFLOR_TEST_BEYIN_ANAHTAR="", SUFLOR_TEST_BETA="", PYTHONDONTWRITEBYTECODE="1"); ort.pop("SUFLOR_TEST_BETA")
kpr = subprocess.Popen([sys.executable, os.path.join(KOD, "kurulum.py"), "--port", str(kp)], env=ort, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    k = None; son = time.time() + 15
    while time.time() < son and not k:
        satir = kpr.stdout.readline(); m = re.search(r"\?k=([\w-]+)", satir or ""); k = m and m.group(1)
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor()); op.open(f"http://127.0.0.1:{kp}/?k={k}", timeout=10)
    def kapi(yol, govde=None):
        r = urllib.request.Request(f"http://127.0.0.1:{kp}/api/{yol}", data=json.dumps(govde).encode() if govde is not None else None,
                                   headers={"Origin": f"http://127.0.0.1:{kp}", "Content-Type": "application/json"})
        return json.load(op.open(r, timeout=30))
    d = kapi("durum")["beyin"]
    kontrol("sihirbaz /api/durum beyin", d["secim"] == "claude-code" and "ollama" in d and d["ollama_gb"] == SG.SG_OLLAMA_MODEL_GB, d)
    r = kapi("beyin/anahtar", {"saglayici": "gemini", "anahtar": "kisa"})
    kontrol("sihirbaz: biçimsiz anahtar → hata bicim", r == {"ok": False, "hata": "bicim", "ayrinti": r.get("ayrinti")}, r)
    r = kapi("beyin/anahtar", {"saglayici": "ozel", "anahtar": "A" * 20, "adres": "http://ornek.com/v1", "model": "m"})
    kontrol("sihirbaz: https olmayan adres reddedilir", r.get("hata") == "adres", r)
    kapi("kaydet", {"dil": "tr", "adim": 3, "adim_id": "claude", "cevap": {"yz": "gemini", "ad": "Deneme"}})
    kayit = open(os.path.join(EVK, "Library", "Application Support", "Suflor", "kurulum.json")).read()
    kontrol("kurulum.json'da anahtar yok", "AAAAAAAAAAAAAAAAAAAA" not in kayit)
    r = kapi("kur/tamamla", {"cevap": {"yz": "gemini", "ad": "Deneme", "proje": os.path.join(EVK, "Suflor")}, "dil": "tr"})
    a = json.load(open(os.path.join(EVK, "Library", "Application Support", "Suflor", "ayar.json")))
    kontrol("kur/tamamla: beyin.varsayilan = Gemini", r.get("ayar") == "iyi" and SG.sg_ad((a.get("beyin") or {}).get("varsayilan")) == "gemini", (r, a.get("beyin")))
    r = kapi("kur/tamamla", {"cevap": {"yz": "claude-code", "ad": "Deneme", "proje": os.path.join(EVK, "Suflor")}, "dil": "tr"})
    a = json.load(open(os.path.join(EVK, "Library", "Application Support", "Suflor", "ayar.json")))
    kontrol("kur/tamamla: Claude Code seçilince beyin.varsayilan kalkar", "beyin" not in a, a.get("beyin"))
finally:
    kpr.terminate(); kpr.wait(5)
shutil.rmtree(GEC, ignore_errors=True)
print(f"\n{'TAMAM' if not hatalar else str(len(hatalar)) + ' KALDI'}")
sys.exit(1 if hatalar else 0)
