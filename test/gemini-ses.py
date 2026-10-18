#!/usr/bin/env python3
# Gemini ile seslendirme (v0.78.0, aktarici/gemini-ses.py): sahte Gemini sunucusuna (SSE, 24 kHz ham ses) karşı — akış okunur ve kayda girer, HTTP hatası
# ve ses gelmemesi False döner (çağıran Mac sesine düşer; zaman aşımında önce yeni bağlantıyla bir kez daha, v0.80.2) ve 15 sn Gemini denenmez, okuma yarıda kesilebilir, ses adı ve model ayardan;
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
        if DAVRANIS["tur"] == "429hep" or (DAVRANIS["tur"] == "429bir" and not DAVRANIS.get("verildi")):  # v0.80.6: hız sınırı
            DAVRANIS["verildi"] = True; b = b'{"error":{"code":429,"message":"You exceeded your current quota","details":[{"@type":"type.googleapis.com/google.rpc.RetryInfo","retryDelay":"1s"}]}}'
            self.send_response(429); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if DAVRANIS["tur"] == "gunluk" and "flash-lite" in self.path or DAVRANIS["tur"] == "gunluk2":  # v0.80.10: model başına günlük sınır
            b = b'{"error":{"code":429,"message":"Quota exceeded for metric: generativelanguage.googleapis.com/generate_requests_per_model_per_day, limit: 100","details":[{"@type":"type.googleapis.com/google.rpc.RetryInfo","retryDelay":"6303s"}]}}'
            self.send_response(429); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
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
ad["gemini_oku"]("Üsluplu.", uslup="nüktedan,\n dostça"); bak("üslup Style başlığıyla, Transcript'ten önce (v0.79.0)", GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"] == "## Style:\nnüktedan, dostça\n## Transcript:\nÜsluplu.")
ad["AYAR"]["gemini_model"] = "gemini-3.8-flash-tts"; ad["gemini_oku"]("Flash."); bak("model ayardan (3.8 Flash)", "/gemini-3.8-flash-tts:" in GELEN[-1]["yol"])
ad["AYAR"]["gemini_model"] = "uydurma"; bak("bilinmeyen model → Flash-Lite", ad["gemini_model"]() == "gemini-3.8-flash-lite-tts")
DAVRANIS["tur"] = "400"; n = len(GELEN); r4 = ad["gemini_oku"]("Hata.")
bak(f"HTTP 400 → False (Mac sesine düşer), durum hata: {ad['GEMINI']['hata'][:60]!r}", r4 is False and ad["GEMINI"]["durum"] == "hata")
r5 = ad["gemini_oku"]("Hemen yine."); bak("HTTP hatası yeniden denenmez; sonra 15 sn istek atılmaz (her cümle beklemesin)", r5 is False and len(GELEN) == n + 1)
ad["GEMINI"]["hata_t"] = 0; DAVRANIS["tur"] = "yavas"; n = len(GELEN); t0 = time.time(); r6 = ad["gemini_oku"]("Yavaş.")
bak(f"3 sn'de ses gelmezse yeni bağlantıyla bir kez daha, sonra False ({time.time() - t0:.1f} sn, {len(GELEN) - n} istek)", r6 is False and time.time() - t0 < 7.5 and len(GELEN) - n == 2)
DAVRANIS["tur"] = "ok"; ad["GEMINI"]["hata_t"] = 0
class _Bir:  # ilk istekte yavaş, ikincide hızlı: yeniden deneme sesi kurtarır
    n = 0
eski = Sahte.do_POST
def _ilk_yavas(self):
    _Bir.n += 1
    if _Bir.n == 1: DAVRANIS["tur"] = "yavas"
    else: DAVRANIS["tur"] = "ok"
    eski(self)
Sahte.do_POST = _ilk_yavas; ad["_gemini_kapat"](); t0 = time.time(); r6b = ad["gemini_oku"]("Bir yavaş bir hızlı."); Sahte.do_POST = eski; DAVRANIS["tur"] = "ok"
bak(f"ilk deneme zaman aşımı, ikinci başarılı → True, Mac sesine düşmez ({time.time() - t0:.1f} sn)", r6b is True and ad["GEMINI"]["durum"] == "hazir")
ad["GEMINI"]["hata_t"] = 0; DAVRANIS["tur"] = "ok"; bak("sonra yeniden çalışır", ad["gemini_oku"]("Tekrar.") is True)
# v0.80.6: 429 (hız sınırı) — önerilen süre beklenip bir kez daha; ikinci de 429 ise Mac sesine düşer
DAVRANIS.update(tur="429bir", verildi=False); n = len(GELEN); t0 = time.time(); r429 = ad["gemini_oku"]("Hız sınırı bir kez.")
bak(f"429 bir kez: retryDelay (1 sn) beklenip yeniden, ses alınır ({time.time() - t0:.1f} sn, {len(GELEN) - n} istek)", r429 is True and len(GELEN) - n == 2 and 0.9 < time.time() - t0 < 3.5)
DAVRANIS.update(tur="429hep"); n = len(GELEN); r429b = ad["gemini_oku"]("Hız sınırı sürüyor.")
bak(f"429 sürüyor: yalnız bir kez yeniden, sonra False (Mac sesi) ({len(GELEN) - n} istek)", r429b is False and len(GELEN) - n == 2)
DAVRANIS.update(tur="429hep"); ad["GEMINI"]["hata_t"] = 0; n = len(GELEN); t0 = time.time(); r429c = ad["gemini_oku"]("Kesilecek.", iptal=lambda: time.time() - t0 > 0.3)
bak(f"beklerken okuma kesilirse beklemez, Mac sesine düşmez ({time.time() - t0:.1f} sn)", r429c is True and time.time() - t0 < 1.0 and len(GELEN) - n == 1)
ad["GEMINI"]["hata_t"] = 0; DAVRANIS["tur"] = "ok"
bak("bekleme süresi: Retry-After başlığı, gövdedeki retryDelay, sınırlar", ad["_gemini_bekleme"]("", "2") == 2.0 and ad["_gemini_bekleme"]('"retryDelay": "9s"') == 4.0 and ad["_gemini_bekleme"]("yok") == 1.5 and ad["_gemini_bekleme"]('"retryDelay": "0.1s"') == 0.5)
# v0.80.10: günlük sınır — beklemeden öteki model; ikisi de doluysa istek atılmadan False; kayıt dosyası yeniden yüklenince de geçerli
DAVRANIS.update(tur="gunluk"); ad["GEMINI"]["hata_t"] = 0; n = len(GELEN); t0 = time.time(); rg = ad["gemini_oku"]("Günlük sınır.")
yollar = [g["yol"] for g in GELEN[n:]]
bak(f"günlük sınır: beklemeden 3.8 Flash'a geçer ({time.time() - t0:.1f} sn, {yollar})", rg is True and len(yollar) == 2 and "flash-lite" in yollar[0] and "flash-lite" not in yollar[1] and time.time() - t0 < 1.5)
n = len(GELEN); ad["gemini_oku"]("Sonraki cümle.")
bak("sonraki cümle dolu modeli hiç denemez", len(GELEN) - n == 1 and "flash-lite" not in GELEN[-1]["yol"])
DAVRANIS.update(tur="gunluk2"); n = len(GELEN); rg2 = ad["gemini_oku"]("İkisi de dolu."); n2 = len(GELEN); rg3 = ad["gemini_oku"]("Yine.")
bak(f"iki model dolu: False, sonra istek atılmaz ({n2 - n} + {len(GELEN) - n2} istek)", rg2 is False and rg3 is False and n2 - n == 1 and len(GELEN) == n2)
ad["GEMINI_KOTA"]["dolu"] = None; bak("kayıt dosyasından yüklenir (aktarıcı yeniden başlasa da)", ad["gemini_model"]() is None and "kota_dolu" in ad["gemini_view"]())
os.remove(os.path.join(T, "gemini-kota.json")); ad["GEMINI_KOTA"]["dolu"] = None; ad["GEMINI"]["hata_t"] = 0; DAVRANIS.update(tur="normal")
bak("kayıt yoksa ayardaki model", ad["gemini_model"]() == "gemini-3.8-flash-lite-tts")
os.environ["SUFLOR_TEST_GEMINI_ANAHTAR"] = ""; bak("anahtar yoksa okumaz (False)", ad["gemini_oku"]("Anahtarsız.") is False and not ad["gemini_acik"]())
os.environ["SUFLOR_TEST_GEMINI_ANAHTAR"] = "deneme-anahtar"

# 1b) v0.79.0: çalmadan ses (toplantıya söyle), aygıt argümanı ve kısık düzey sahte çalıcıyla
pcm = ad["gemini_pcm"]("Toplantıya."); bak(f"gemini_pcm: ham ses döner ({len(pcm or b'')} bayt)", pcm is not None and len(pcm) == 4 * 12000)
SAHTE = os.path.join(T, "sahte-oynat.sh"); open(SAHTE, "w").write('#!/bin/sh\necho "$@" >> "$0.arg"\ncat >> "$0.pcm"\n'); os.chmod(SAHTE, 0o755)
ad["PIPER_OYNAT"] = SAHTE; os.environ.pop("SUFLOR_TEST_GEMINI_SESSIZ")
ad["gemini_oku"]("BlackHole'a.", aygit="59", duzey=0.5); time.sleep(0.3)
arg = open(SAHTE + ".arg").read().split("\n")[-2]; ham = open(SAHTE + ".pcm", "rb").read()
bak(f"aygıt çalıcıya argüman olarak gider ({arg!r})", arg == "24000 59")
bak("duzey 0,5 sesi kısar (örnek değerleri yarıya)", len(ham) == 4 * 12000 and ham[2:4] == bytes([1, 0]) * 0 + ham[2:4] and int.from_bytes(ham[12000 * 1 + 0:12000 * 1 + 2], "little", signed=True) == 0 and int.from_bytes(ham[24000:24002], "little", signed=True) == 1)
os.environ["SUFLOR_TEST_GEMINI_SESSIZ"] = "1"; ad["PIPER_OYNAT"] = "/yok"
bak("aygıt istenip çalıcı yoksa False (afplay varsayılan çıkışa giderdi)", ad["gemini_oku"]("Yok.", aygit="59") is False)
# 1c) toplantıya söyle: toplantı kişiliğinin sesi Gemini ise BlackHole + kulaklık aynı Gemini sesi (sahte çalıcı)
tsn = dict(ad); open(SAHTE + ".arg", "w").close()
tsn.update(PIPER_OYNAT=SAHTE, kisilik_sesi=lambda zorla=None: ("gemini", "Kore", 1.0), kisilik=lambda: {"ses_uslup": "ölçülü"}, kisilik_telaffuz=lambda m: m, ses_duzen=lambda m, mac=True: m,
           AYAR={"toplantiya_ses": True}, STATE={"masaustu": {"toplantida": True}}, toplanti_var=lambda: True, ts_web=lambda: False, ts_aygit=lambda: "59", otonom_kisayol=lambda: None,
           ses_secimi=lambda: None, telaffuz=lambda m, mac=False: m, ses_durdur=lambda: None, kulaklik=lambda: True, kendi_ses_kaydet=lambda *a: None, note=lambda *a: None, kart_bildir=lambda: None,
           sesli_terim_suz=lambda m: m, etiket_sil=lambda m: m, _t=lambda a, b: a, ARAYUZ_DILI="tr", kisilik_ad=lambda: "Atlas", re=__import__("re"), secrets=__import__("secrets"))
exec(compile(open(os.path.join(K, "aktarici", "toplantiya-ses.py"), encoding="utf-8").read(), "toplantiya-ses.py", "exec"), tsn)
tsn["TS"]["tanitti"] = "?"  # tanıtım bu denemede okunmasın
r = tsn["toplantiya_soyle"]("Bütçe onaylandı."); time.sleep(0.5)
argl = [x for x in open(SAHTE + ".arg").read().split("\n") if x]
bak(f"toplantıya söyle Gemini: BlackHole (59) + kulaklık, Kore ({argl}, {r})", r.get("ok") and argl == ["24000 59", "24000"] and '"voice_name": "Kore"' in json.dumps(GELEN[-1]["govde"]) and "## Style:\nölçülü" in GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"])
# 1d) hı hı: Gemini sesiyle konuşan kişilikte klip değil o anda Gemini (tepki_cal)
bs = open(os.path.join(K, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); i = bs.index("def tepki_cal("); tc = dict(ad)
tc.update(AYAR={}, piper_acik=lambda: False, kisilik_sesi=lambda zorla=None: ("gemini", "Charon", 1.0), threading=threading); n0 = len(GELEN)
exec(bs[i:bs.index("\n_TEPKI_BAS", i)], tc)
r1 = tc["tepki_cal"]("alindi", hemen=True, ses=0.4); time.sleep(0.8)
bak("hı hı: Gemini'den o anda (klip yok), kısık, Charon", r1 is True and len(GELEN) == n0 + 1 and '"voice_name": "Charon"' in json.dumps(GELEN[-1]["govde"]) and "Hı" in GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"] + "Hım")
bak("bekleme (düşünme) klibi Gemini'de çalmaz → çağıran cümleyi okur", tc["tepki_cal"]("dusunme") is False)

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
