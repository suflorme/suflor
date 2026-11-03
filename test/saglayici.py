#!/usr/bin/env python3
# Yapay zekâ sağlayıcısı seçimi (Faz 11 Aşama 4, aktarici/saglayici.py): seçenek ↔ "beyin" ayarı (sg_profil, sg_ad, sg_yaz; elle yazılmış model korunur),
# beyin.py secim()'in yazılan ayarı doğru okuması, teshis.py beta seçeneğinin (yalnız tür) aynı ayrımı yapması, Anahtar Zinciri yazımının biçim denetimi
# (deneme kipinde Anahtar Zinciri'ne dokunulmaz), anahtar denemesi sahte sunucuya, deneme aktarıcısında panodaki ⚙ Ayarlar (beyin_* satırları,
# anahtarsız seçenek reddi, kaldırılan "ollama" seçeneğinin reddi ve eski ayarın Claude Code'a düşmesi, Varsayılanlara dön dışında), /status beyin sağlığı;
# kurulum sihirbazının /api/beyin/anahtar ve kur/tamamla'nın beyin.varsayilan yazması (deneme ev klasörü).
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
a["beyin_ozel"] = {"adres": "https://api.ornek.com/v1", "model": "m-1"}; SG.sg_yaz(a, {"ceviri": "claude-code", "konus": "ozel"})
kontrol("iş başına: çeviri Claude Code, Konuş OpenAI uyumlu", SG.sg_secim(a) == {"varsayilan": "gemini", "konus": "ozel", "ceviri": "claude-code", "proje_karti": ""}, SG.sg_secim(a))
s = BY.secim(a, "konus")
kontrol("beyin.py: Konuş ozel hizmete (adres, öğe suflor-ozel, effort/öğe sızmaz)", s["adres"] == "https://api.ornek.com/v1" and s["effort"] is None and s["anahtar"] == "suflor-ozel", s)
kontrol("beyin.py: çeviri claude-code (haiku)", BY.secim(a, "ceviri") == {"tur": "claude-code", "model": "haiku"})
kontrol("sg_etkin: proje kartı varsayılanı izler", SG.sg_etkin(a)["proje_karti"] == "gemini")
a["beyin"]["konus"]["model"] = "m-elle"; SG.sg_yaz(a, {"konus": "ozel"})
kontrol("aynı seçenek yeniden: elle yazılmış model korunur", a["beyin"]["konus"]["model"] == "m-elle")
b = {"beyin": {"konus": {"tur": "openai-uyumlu", "saglayici": "ollama", "model": "qwen3.5:4b-q4_K_M"}, "ceviri": {"tur": "openai-uyumlu", "adres": "http://127.0.0.1:11434/v1", "model": "x"}}}
kontrol("eski ayar (ollama): seçenek Claude Code'a düşer, loopback adres elle verilen ozel sayılır", SG.sg_ad(b["beyin"]["konus"]) == "claude-code" and SG.sg_ad(b["beyin"]["ceviri"]) == "ozel")
kontrol("beyin.py: eski ollama ayarı Claude Code'a düşer (çökmez)", BY.secim(b, "konus") == {"tur": "claude-code", "model": "sonnet"}, BY.secim(b, "konus"))
kontrol("ollama artık seçenek değil", "ollama" not in SG.SG_SECENEK and SG.sg_yaz({}, {"konus": "ollama"}) is not None)
kontrol("ozel tanımsızken hata", SG.sg_yaz({}, {"konus": "ozel"}) is not None)
o = dict(a); o.pop("beyin", None); SG.sg_yaz(o, {"varsayilan": "gemini"}); SG.sg_yaz(o, {"konus": "ozel"})
kontrol("ozel: adres + model + öğe suflor-ozel", {k: v for k, v in o["beyin"]["konus"].items() if v is not None} == {"tur": "openai-uyumlu", "adres": "https://api.ornek.com/v1", "model": "m-1", "anahtar": "suflor-ozel"})
s = BY.secim(o, "konus")
kontrol("beyin.py: ozel (varsayılan Gemini'yken) → saglayici diger, effort/öğe sızmaz", s["saglayici"] == "diger" and s["effort"] is None and s["anahtar"] == "suflor-ozel" and s["fiyat"] is None, s)
kontrol("LM Studio (127.0.0.1:1234) ozel sayılır", SG.sg_ad({"tur": "openai-uyumlu", "adres": "http://127.0.0.1:1234/v1"}) == "ozel")
SG.sg_yaz(a, {"konus": "", "ceviri": "", "varsayilan": "claude-code"})
kontrol("hepsi geri: beyin anahtarı kalkar", "beyin" not in a, a)
kontrol("bilinmeyen iş/seçenek reddedilir", SG.sg_yaz({}, {"toplanti": "gemini"}) and SG.sg_yaz({}, {"konus": "x"}))

# --- 2. beta: yalnız seçenek, aynı ayrım -------------------------------------------------------------------------------------------
for d in ({}, {"beyin": {"konus": SG.sg_profil("ozel", o), "varsayilan": SG.sg_profil("gemini", {})}}, o, b):
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

# --- 4. sağlık ---------------------------------------------------------------------------------------------------------------------------
kontrol("sağlık: Gemini anahtarsız → ⚠", not [x for x in SG.sg_saglik({"beyin": {"varsayilan": SG.sg_profil("gemini", {})}}, True) if x["ad"] == "gemini"][0]["ok"])
GEC = tempfile.mkdtemp(prefix="suflor-sg-"); o3 = os.path.join(GEC, "ortak3"); os.makedirs(o3)

# --- 5. deneme aktarıcısı: panodaki Ayarlar -------------------------------------------------------------------------------
subprocess.run(["pkill", "-f", "relay.py --dir " + GEC], capture_output=True)
RL = os.path.join(GEC, "relay"); shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(RL, "aktarici")); shutil.copy(os.path.join(KOD, "relay.py"), RL)
shutil.copy(os.path.join(KOD, "manifest.json"), RL); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(RL, "pano"))
rport = bos_port(); ayar_yol = os.path.join(GEC, "ayar.json"); os.makedirs(os.path.join(GEC, "uyg"))
json.dump({"port": rport, "uygulama": os.path.join(GEC, "uyg"), "ortak": o3, "proje": os.path.join(GEC, "proje"), "beyin": {"konus": {"tur": "openai-uyumlu", "saglayici": "ollama", "model": "qwen3.5:4b-q4_K_M"}}}, open(ayar_yol, "w"))  # eski ayar: kaldırılan seçenek
ort = dict(os.environ, SUFLOR_AYAR=ayar_yol, SUFLOR_TEST_BEYIN_ANAHTAR="", PYTHONDONTWRITEBYTECODE="1")
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
    kontrol("/status beyin: eski ollama ayarı Claude Code'a düşer", st["beyin"]["etkin"] == {"konus": "claude-code", "ceviri": "claude-code", "proje_karti": "claude-code"}, st.get("beyin"))
    kontrol("Ayarlar: beyin_* değerleri + kullanılabilirlik", ay["deger"]["beyin_varsayilan"] == "claude-code" and ay["deger"]["beyin_konus"] == "claude-code" and "ollama" not in ay["beyin"] and ay["beyin"]["gemini"] is False, ay.get("beyin"))
    kontrol("Ayarlar: kullanılabilirlikte ollama yok", "ollama" not in json.dumps(ay["beyin"]))
    kontrol("Varsayılanlara dön yapay zekâ seçimine dokunmaz", not any(k.startswith("beyin_") for k in ay["varsayilan"]))
    r = istek("/ayar", {"degisen": {"beyin_konus": "gemini"}})
    kontrol("anahtarsız Gemini reddedilir", r.get("ok") is False and "beyin_konus" in r.get("hata", {}), r)
    r = istek("/ayar", {"degisen": {"beyin_konus": "ollama"}})
    kontrol("kaldırılan 'ollama' seçeneği reddedilir", r.get("ok") is False and "beyin_konus" in r.get("hata", {}), r)
    r = istek("/ayar", {"degisen": {"beyin_proje_karti": "bilinmeyen"}})
    kontrol("bilinmeyen seçenek reddedilir", r.get("ok") is False)
finally:
    rp.terminate(); rp.wait(5); gunluk.close()

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
    kontrol("sihirbaz /api/durum beyin", d["secim"] == "claude-code" and "ollama" not in d and "ollama_gb" not in d, d)
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
