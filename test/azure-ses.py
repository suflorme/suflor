#!/usr/bin/env python3
# Azure MAI sesi, Gemini'nin yedeği (v0.128.0, S151, aktarici/azure-ses.py): sahte Gemini ve sahte Azure sunucusuna karşı — ayar kapalıyken hiç gidilmez;
# Gemini'nin iki modeli de doluyken ya da Gemini hata verince aynı okuma Azure'a gider (SSML, ses adı Gemini sesinin cinsiyetine göre Elif/Aydın, etiketler
# temizlenir, anahtar başlıkta), topla ham ses döndürür, Azure hatası False + 30 sn bekleme, gizli toplantıda gemini_izinli kapalı. Ses çalınmaz, buluta gidilmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/azure-ses.py     (~5 sn)
import base64, http.server, json, os, re, socket, subprocess, sys, tempfile, threading, time
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-azure-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
def bos_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

G = {"tur": "gunluk", "n": 0}
class Gemini(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"])); G["n"] += 1
        b = (b'{"error":{"code":429,"message":"Quota exceeded for metric: generate_requests_per_model_per_day, limit: 100"}}' if G["tur"] == "gunluk"
             else b'{"error":{"code":500,"message":"internal"}}')
        self.send_response(429 if G["tur"] == "gunluk" else 500); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
A = {"tur": "ok", "gelen": []}
class Azure(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        g = self.rfile.read(int(self.headers["Content-Length"])).decode()
        A["gelen"].append({"yol": self.path, "govde": g, "anahtar": self.headers.get("Ocp-Apim-Subscription-Key"), "bicim": self.headers.get("X-Microsoft-OutputFormat")})
        if A["tur"] == "401":
            b = b'{"error":"denied"}'; self.send_response(401); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        pcm = bytes(48000)  # 1 sn ses
        self.send_response(200); self.send_header("Content-Length", str(len(pcm))); self.end_headers()
        for i in range(0, len(pcm), 12000): self.wfile.write(pcm[i:i + 12000]); self.wfile.flush(); time.sleep(0.02)
def sun(h):
    p = bos_port(); s = http.server.ThreadingHTTPServer(("127.0.0.1", p), h); s.handle_error = lambda *a: None; threading.Thread(target=s.serve_forever, daemon=True).start(); return p
PG, PA = sun(Gemini), sun(Azure)
os.environ.update(SUFLOR_TEST_GEMINI_HOST=f"127.0.0.1:{PG}", SUFLOR_TEST_GEMINI_ANAHTAR="g-anahtar", SUFLOR_TEST_GEMINI_SESSIZ="1",
                  SUFLOR_TEST_AZURE_HOST=f"127.0.0.1:{PA}", SUFLOR_TEST_AZURE_ANAHTAR="a-anahtar")
YAZILAN = []
ad = {"__name__": "azure_ses", "math": __import__("math"), "os": os, "time": time, "json": json, "base64": base64, "subprocess": subprocess, "threading": threading, "re": re,
      "datetime": __import__("datetime"), "AYAR": {"gemini_ses": "Charon", "gemini_kapsam": "hepsi"}, "BASE": T, "PIPER_OYNAT": "/yok", "write": lambda ps: YAZILAN.extend(ps)}
for b in ("gemini-ses.py", "azure-ses.py"): exec(compile(open(os.path.join(K, "aktarici", b), encoding="utf-8").read(), b, "exec"), ad)

# 1) ayar kapalı: Gemini dolu → False, Azure'a gidilmez
r = ad["gemini_oku"]("Bütçe onaylandı."); bak("azure_yedek yokken Gemini olmayınca False, Azure'a istek yok", r is False and not A["gelen"])
bak("ayar kapalı: Gemini dolu → gemini_izinli kapalı (yerel ses)", ad["gemini_izinli"]() is False)
# 2) ayar açık: günlük sınır dolu → Azure
ad["AYAR"]["azure_yedek"] = True; ad["GEMINI"]["hata_t"] = 0
bak("ayar açık: Gemini dolu ama Azure hazır → gemini_izinli açık", ad["gemini_izinli"]() is True)
r = ad["gemini_oku"]("Toplam 4,2 milyon <chuckle> lira & vergi.", ses="Charon"); a = A["gelen"][-1] if A["gelen"] else {}
bak(f"Gemini dolu → Azure okudu (True)", r is True and len(A["gelen"]) == 1)
bak("istek: /cognitiveservices/v1, ham 24 kHz, anahtar başlıkta", a.get("yol") == "/cognitiveservices/v1" and a.get("bicim") == "raw-24khz-16bit-mono-pcm" and a.get("anahtar") == "a-anahtar")
bak(f"erkek Gemini sesi (Charon) → Aydın MAI; etiket temiz, XML kaçışlı: {a.get('govde', '')[-90:]!r}",
    'name="tr-TR-Aydin:MAI-Voice-2.1-Flash"' in a.get("govde", "") and "chuckle" not in a.get("govde", "") and "lira &amp; vergi" in a.get("govde", ""))
k = json.loads(YAZILAN[-1][1]) if YAZILAN else {}
bak(f"kullanım kaydı azure-ses.jsonl: {k}", YAZILAN and YAZILAN[-1][0].endswith("azure-ses.jsonl") and k.get("ses_sn") == 1.0 and k.get("ses") == "tr-TR-Aydin:MAI-Voice-2.1-Flash")
ad["gemini_oku"]("Merhaba.", ses="Kore"); bak("kadın Gemini sesi (Kore) → Elif", 'name="tr-TR-Elif:MAI-Voice-2.1-Flash"' in A["gelen"][-1]["govde"])
ad["AYAR"]["azure_ses_kadin"] = "Emel"; ad["AYAR"]["azure_model"] = ""; ad["gemini_oku"]("Merhaba.", ses="Kore")
bak("ayarla ses ve model değişir (Emel, modelsiz standart ses)", 'name="tr-TR-Emel"' in A["gelen"][-1]["govde"]); ad["AYAR"].pop("azure_ses_kadin"); ad["AYAR"].pop("azure_model")
pcm = ad["gemini_pcm"]("Toplantıya söyle."); bak("topla (toplantıya söyle): ham ses döner", isinstance(pcm, bytes) and len(pcm) == 48000)
r = ad["gemini_oku"]("Kesilecek.", iptal=lambda: True); bak("iptal: True (yerel sese düşmez)", r is True)
# 2b) duygu biçimi (v0.129.0)
st = ad["azure_stil"]
bak("biçim kuralı: soru → curious, maalesef → saddisappointed, tebrikler → excited, merak etme → encouraging, düz → neutral",
    st("Yarın gelir misin?") == "curious" and st("Maalesef teklif reddedildi.") == "saddisappointed" and st("Tebrikler, harika iş!") == "excited"
    and st("Merak etme, hallederiz.") == "encouraging" and st("Toplantı saat üçte.") == "neutral")
ad["TON"].update(ad="kotu_haber", t=time.time()); bak("Gemini'deki durum tonu önce gelir (kötü haber → saddisappointed, soru olsa da)", st("Gelir misin?") == "saddisappointed"); ad["ton_sifirla"]()
bak("fısıltı ve çevirmen üslubu → neutral", st("Harika!", uslup="Whispering in the ear: very short") == "neutral" and st("Harika!", uslup="Simultaneous interpreter: plain") == "neutral")
ad["kisilikler"] = lambda: [{"ad": "A", "ses": "gemini:Charon", "azure_stil": "friendlycheerful"}, {"ad": "B", "ses": "gemini:Kore", "azure_stil": "serious"}]
bak("kural yoksa kişiliğin azure_stil'i (Gemini sesine göre)", st("Toplantı saat üçte.", ses="Charon") == "friendlycheerful" and st("Toplantı saat üçte.", ses="Kore") == "serious")
ad.pop("kisilikler")
ad["gemini_oku"]("Maalesef olmadı.", ses="Charon"); g = A["gelen"][-1]["govde"]
bak("SSML: mstts ad alanı ve express-as biçimi", 'xmlns:mstts="http://www.w3.org/2001/mstts"' in g and '<mstts:express-as style="saddisappointed">Maalesef olmadı.</mstts:express-as>' in g)
bak("kullanım kaydında biçim", json.loads(YAZILAN[-1][1]).get("stil") == "saddisappointed")
ad["AYAR"]["azure_stil"] = False; ad["gemini_oku"]("Maalesef.", ses="Charon"); bak("ayar azure_stil: false → biçimsiz", "express-as" not in A["gelen"][-1]["govde"]); ad["AYAR"].pop("azure_stil")
ad["AYAR"]["azure_model"] = ""; ad["gemini_oku"]("Maalesef.", ses="Charon"); bak("standart nöral seste (modelsiz) biçim yok", "express-as" not in A["gelen"][-1]["govde"]); ad["AYAR"].pop("azure_model")
# 3) Gemini hata verince de (sınır değil) Azure
for x in ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"): ad["_kota"]().pop(x, None) if isinstance(ad["_kota"](), dict) else None
try: os.remove(os.path.join(T, "gemini-kota.json"))
except OSError: pass
ad["GEMINI_KOTA"]["dolu"] = None; G["tur"] = "500"; ad["GEMINI"]["hata_t"] = 0; n = len(A["gelen"]); gn = G["n"]
r = ad["gemini_oku"]("Gemini hatası."); bak(f"Gemini HTTP 500 → Azure okudu ({G['n'] - gn} Gemini isteği)", r is True and len(A["gelen"]) == n + 1 and G["n"] - gn >= 1)
n = len(A["gelen"]); gn = G["n"]; r = ad["gemini_oku"]("Bekleme süresinde."); bak("Gemini bekleme süresindeyken Gemini'ye gidilmez, Azure okur", r is True and G["n"] == gn and len(A["gelen"]) == n + 1)
# 4) Azure hatası → False, 30 sn denenmez
A["tur"] = "401"; n = len(A["gelen"]); r = ad["gemini_oku"]("Azure da yok.")
bak(f"Azure 401 → False (yerel ses), hata kaydı: {ad['AZURE']['hata']!r}", r is False and len(A["gelen"]) == n + 1 and ad["AZURE"]["hata"])
r = ad["gemini_oku"]("Hemen yine."); bak("hata sonrası Azure 30 sn denenmez", r is False and len(A["gelen"]) == n + 1 and ad["azure_hazir"]() is False)
A["tur"] = "ok"; ad["AZURE"]["hata_t"] = 0
# 5) gizli toplantı ve uyarı metni
ad["gizli_acik"] = lambda: True; bak("gizli toplantıda gemini_izinli kapalı (Azure da yok)", ad["gemini_izinli"]() is False); ad.pop("gizli_acik")
bak("durum: gemini_view içinde azure (son hata bir sonraki başarılı okumaya kadar görünür)", ad["gemini_view"]()["azure"]["hazir"] is True)
UY = []; ad["yerel_uyari"] = UY.append; ad["_t"] = lambda a, b: a
yol = os.path.join(T, "gemini-ses.jsonl"); simdi = __import__("datetime").datetime.now().isoformat(timespec="seconds")
open(yol, "w").write("".join(json.dumps({"t": simdi, "model": m}) + "\n" for m, n_ in (("gemini-3.8-flash-lite-tts", 100), ("gemini-3.8-flash-tts", 60)) for _ in range(n_))); ad["_BUGUN"]["t"] = 0.0
ad["_kota_bak"]("gemini-3.8-flash-tts"); bak(f"%80 uyarısı Azure açıkken 'yedek sese' der: {UY}", len(UY) == 1 and "yedek sese" in UY[0])
shutil = __import__("shutil"); shutil.rmtree(T, ignore_errors=True)
print("azure ses: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı")); sys.exit(1 if hata else 0)
