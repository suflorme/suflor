#!/usr/bin/env python3
# Gemini ile seslendirme (v0.78.0, aktarici/gemini-ses.py): sahte Gemini sunucusuna (SSE, 24 kHz ham ses) karşı — akış okunur ve kayda girer, HTTP hatası
# ve ses gelmemesi False döner (çağıran Mac sesine düşer) ve 60 sn Gemini denenmez, okuma yarıda kesilebilir, ses adı ve model ayardan;
# kişilik sesi seçimi (gemini / gemini:Kore / anahtar yoksa Mac); ⚙ Ayarlar'da ses_motoru: gemini + gemini_ses kaydedilir. Ses çalınmaz, Google'a gidilmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gemini-ses.py     (~15 sn)
import base64, http.server, json, os, shutil, socket, subprocess, sys, tempfile, threading, time, types, urllib.request
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-gemini-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
def bos_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

GELEN = []; DAVRANIS = {"tur": "ok"}
class Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        govde = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        GELEN.append({"yol": self.path, "anahtar": self.headers.get("x-goog-api-key"), "govde": govde})
        if DAVRANIS["tur"] == "400":
            b = b'{"error":{"code":400,"message":"API key not valid"}}'
            self.send_response(400); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if DAVRANIS["tur"] == "yavas": time.sleep(7)
        olaylar = []
        for i in range(4):  # 4 parça × 0,25 sn ses
            pcm = (bytes([i, 0]) * 6000)
            olaylar.append("data: " + json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/l16;rate=24000", "data": base64.b64encode(pcm).decode()}}]}}]}) + "\r\n\r\n")
        b = "".join(olaylar).encode()
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        for o in olaylar: self.wfile.write(o.encode()); self.wfile.flush(); time.sleep(0.05)
PORT = bos_port(); sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Sahte); sunucu.handle_error = lambda *a: None; threading.Thread(target=sunucu.serve_forever, daemon=True).start()

# 1) Bölüm dosyası yalıtılmış ad alanında (relay.py'nin verdiği adlar taklit)
os.environ.update(SUFLOR_TEST_GEMINI_HOST=f"127.0.0.1:{PORT}", SUFLOR_TEST_GEMINI_ANAHTAR="deneme-anahtar", SUFLOR_TEST_GEMINI_SESSIZ="1")
YAZILAN = []
ad = {"__name__": "gemini_ses", "os": os, "time": time, "json": json, "base64": base64, "subprocess": subprocess, "threading": threading,
      "datetime": __import__("datetime"), "AYAR": {"gemini_ses": "Kore"}, "BASE": T, "PIPER_OYNAT": "/yok", "write": lambda ps: YAZILAN.extend(ps)}
exec(compile(open(os.path.join(K, "aktarici", "gemini-ses.py"), encoding="utf-8").read(), "gemini-ses.py", "exec"), ad)
t0 = time.time(); r = ad["gemini_oku"]("Gerçekten mi? Geçen hafta tam tersini söylemişlerdi.")
g = GELEN[-1] if GELEN else {}
bak(f"akış okundu: True, {time.time() - t0:.2f} sn", r is True)
bak("istek: streamGenerateContent + model Flash-Lite + anahtar başlıkta (adreste değil)", "flash-lite-tts:streamGenerateContent" in g.get("yol", "") and g.get("anahtar") == "deneme-anahtar" and "key=" not in g.get("yol", ""))
bak("ses adı ayardan (Kore), metin Transcript başlığıyla", json.dumps(g.get("govde", {}), ensure_ascii=False).count('"voice_name": "Kore"') == 1 and "## Transcript:\nGerçekten mi?" in g["govde"]["contents"][0]["parts"][0]["text"])
k = json.loads(YAZILAN[-1][1]) if YAZILAN else {}
bak(f"kullanım kaydı (gemini-ses.jsonl): {k}", YAZILAN and YAZILAN[-1][0].endswith("gemini-ses.jsonl") and k.get("ses_sn") == 1.0 and k.get("karakter") > 10 and k.get("ilk_ses") is not None)
r2 = ad["gemini_oku"]("İkinci.", ses="Puck"); bak("kalıcı bağlantıyla ikinci istek, ses parametresi (Puck)", r2 is True and '"voice_name": "Puck"' in json.dumps(GELEN[-1]["govde"]))
r3 = ad["gemini_oku"]("Kesilecek.", iptal=lambda: True); bak("iptal: ilk parçada durur, True (Mac sesine düşmez)", r3 is True)
ad["AYAR"]["gemini_model"] = "gemini-3.8-flash-tts"; ad["gemini_oku"]("Flash."); bak("model ayardan (3.8 Flash)", "/gemini-3.8-flash-tts:" in GELEN[-1]["yol"])
ad["AYAR"]["gemini_model"] = "uydurma"; bak("bilinmeyen model → Flash-Lite", ad["gemini_model"]() == "gemini-3.8-flash-lite-tts")
DAVRANIS["tur"] = "400"; n = len(GELEN); r4 = ad["gemini_oku"]("Hata.")
bak(f"HTTP 400 → False (Mac sesine düşer), durum hata: {ad['GEMINI']['hata'][:60]!r}", r4 is False and ad["GEMINI"]["durum"] == "hata")
r5 = ad["gemini_oku"]("Hemen yine."); bak("hatadan sonra 60 sn istek atılmaz (her cümle beklemesin)", r5 is False and len(GELEN) == n + 1)
ad["GEMINI"]["hata_t"] = 0; DAVRANIS["tur"] = "yavas"; t0 = time.time(); r6 = ad["gemini_oku"]("Yavaş.")
bak(f"5 sn'de ses gelmezse False ({time.time() - t0:.1f} sn)", r6 is False and time.time() - t0 < 6.5)
ad["GEMINI"]["hata_t"] = 0; DAVRANIS["tur"] = "ok"; bak("sonra yeniden çalışır", ad["gemini_oku"]("Tekrar.") is True)
os.environ["SUFLOR_TEST_GEMINI_ANAHTAR"] = ""; bak("anahtar yoksa okumaz (False)", ad["gemini_oku"]("Anahtarsız.") is False and not ad["gemini_acik"]())
os.environ["SUFLOR_TEST_GEMINI_ANAHTAR"] = "deneme-anahtar"

# 2) Gerçek aktarıcı: ⚙ Ayarlar'da Gemini seçenekleri ve kaydetme
for f in ("relay.py", "manifest.json", "teshis.py"): shutil.copy(os.path.join(K, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(K, d), os.path.join(T, d))
RP = bos_port(); json.dump({"alan": "Deneme", "ad": "Ali K", "port": RP, "uygulama": T, "proje": T}, open(os.path.join(T, "ayar.json"), "w"))
p = subprocess.Popen([sys.executable, "relay.py", "--dir", os.path.join(T, "canli"), "--port", str(RP)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BASLAT="1"))
try:
    for _ in range(60):
        time.sleep(0.2)
        try: anahtar = open(os.path.join(T, "canli", "kart-anahtari.txt")).read().strip(); urllib.request.urlopen(f"http://127.0.0.1:{RP}/", timeout=1); break
        except Exception: pass
    def istek(yol, govde=None):
        r = urllib.request.Request(f"http://127.0.0.1:{RP}{yol}", data=json.dumps(govde).encode() if govde is not None else None, headers={"X-Suflor-Anahtar": anahtar, "Origin": f"http://127.0.0.1:{RP}"})
        return json.load(urllib.request.urlopen(r, timeout=10))
    a = istek("/status")["ayarlar"]
    bak("ayarlar: gemini anahtarı görülür, varsayılan Mac sesi / Charon / Flash-Lite", a.get("gemini") is True and a["deger"]["ses_motoru"] == "mac" and a["deger"]["gemini_ses"] == "Charon" and a["deger"]["gemini_model"] == "gemini-3.8-flash-lite-tts")
    r = istek("/ayar", {"degisen": {"ses_motoru": "gemini", "gemini_ses": "Kore"}}); a = istek("/status")
    bak(f"kaydet: ses_motoru gemini + Kore ({r})", r.get("ok") and a["ayarlar"]["deger"]["ses_motoru"] == "gemini" and a["ayarlar"]["deger"]["gemini_ses"] == "Kore"
        and json.load(open(os.path.join(T, "ayar.json"))).get("ses_motoru") == "gemini")
    bak(f"/status seslendirme: Gemini, Kore ({a.get('seslendirme')})", (a.get("seslendirme") or {}).get("motor") == "gemini" and a["seslendirme"].get("ses") == "Kore")
    r = istek("/ayar", {"degisen": {"gemini_ses": "Uydurma"}}); bak("bilinmeyen ses reddedilir", r.get("ok") is False)
    log = open(os.path.join(T, "relay.log")).read(); bak("günlükte hata yok", "Traceback" not in log)
finally:
    p.terminate()
    try: p.wait(5)
    except subprocess.TimeoutExpired: p.kill()
    sunucu.shutdown()
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("gemini ses: ✓ hepsi geçti" if not hata else f"gemini ses: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
