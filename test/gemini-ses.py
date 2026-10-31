#!/usr/bin/env python3
# Gemini ile seslendirme (v0.78.0, aktarici/gemini-ses.py; v0.157.0 süre bekçisi: şişen ses atılır, bir kez yeniden): sahte Gemini sunucusuna (SSE, 24 kHz ham ses) karşı — akış okunur ve kayda girer, HTTP hatası
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
        olaylar = []; npar = 4
        if DAVRANIS["tur"] == "sisme" or (DAVRANIS["tur"] == "sisme_bir" and not DAVRANIS.get("sisti")): npar = 40; DAVRANIS["sisti"] = True  # v0.157.0: 10 sn ses (iki kez okuma gibi)
        for i in range(npar):  # 4 parça × 0,25 sn ses
            pcm = (bytes([i, 0]) * 6000)
            olaylar.append("data: " + json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/l16;rate=24000", "data": base64.b64encode(pcm).decode()}}]}}]}) + "\r\n\r\n")
        b = "".join(olaylar).encode()
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        for o in olaylar: self.wfile.write(o.encode()); self.wfile.flush(); time.sleep(0.05)
PORT = bos_port(); sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Sahte); sunucu.handle_error = lambda *a: None; threading.Thread(target=sunucu.serve_forever, daemon=True).start()

# 1) Bölüm dosyası yalıtılmış ad alanında (relay.py'nin verdiği adlar taklit)
os.environ.update(SUFLOR_TEST_GEMINI_HOST=f"127.0.0.1:{PORT}", SUFLOR_TEST_GEMINI_ANAHTAR="deneme-anahtar", SUFLOR_TEST_GEMINI_SESSIZ="1")
YAZILAN = []
ad = {"__name__": "gemini_ses", "math": __import__("math"), "os": os, "time": time, "json": json, "base64": base64, "subprocess": subprocess, "threading": threading,
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
# v0.157.0 süre bekçisi: sınır 2,0 + 0,10 × karakter; 29 Ekim'deki gibi 47 karakterde 10 sn ses şişmiş sayılır
import contextlib as _cl, io as _io
M47 = "Evet, teslim tarihi cuma; ekip hazır görünüyor."; bak(f"sınır: 47 karakter → {ad['gemini_sinir_sn'](M47):.1f} sn", abs(ad["gemini_sinir_sn"](M47) - 6.7) < 0.05)
DAVRANIS.update(tur="sisme_bir", sisti=False); n = len(GELEN); out = _io.StringIO()
with _cl.redirect_stdout(out): pcm = ad["gemini_pcm"](M47)
bak(f"şişen ses (10 sn / 47 karakter) atıldı, bir kez yeniden istendi, ikincisi alındı ({len(GELEN) - n} istek, {len(pcm or b'') / 48000:.1f} sn)",
    pcm is not None and len(pcm) == 48000 and len(GELEN) - n == 2 and "GEMINI: süre şişti (" in out.getvalue() and "atıldı, yeniden isteniyor" in out.getvalue())
kk = [json.loads(x[1]) for x in YAZILAN[-2:]]; bak(f"iki istek de kayıtta, şişen 'sisme' işaretli ({kk})", kk[0].get("sisme") is True and "sisme" not in kk[1])
DAVRANIS.update(tur="sisme"); n = len(GELEN); out = _io.StringIO()
with _cl.redirect_stdout(out): pcm2 = ad["gemini_pcm"](M47); r_s = ad["gemini_oku"]("Kısa söz.")
bak(f"yine şişerse None/False (yedek sese düşer), en çok iki istek ({len(GELEN) - n} istek)", pcm2 is None and r_s is False and len(GELEN) - n == 4 and out.getvalue().count("yine şişti, yedek ses") == 2)
bak("şişme hata sayılmaz (Gemini 15 sn kapanmaz)", ad["GEMINI"]["hata_t"] == 0)
ad["AYAR"]["gemini_sure_bekci"] = False; n = len(GELEN); pcm3 = ad["gemini_pcm"](M47); ad["AYAR"].pop("gemini_sure_bekci")
bak("ayar gemini_sure_bekci: false → bekçi kapalı", pcm3 is not None and len(pcm3) == 480000 and len(GELEN) - n == 1)
# akarak çalarken: sınıra kadar çalıcıya verilir, fazlası atılır, yeniden istenmez
cal_say = os.path.join(T, "calinan"); calici = os.path.join(T, "calici")
open(calici, "w").write(f"#!/bin/sh\nwc -c > {cal_say}\n"); os.chmod(calici, 0o755)
ad["PIPER_OYNAT"] = calici; os.environ.pop("SUFLOR_TEST_GEMINI_SESSIZ"); n = len(GELEN); out = _io.StringIO()
with _cl.redirect_stdout(out): r_c = ad["gemini_oku"](M47)
os.environ["SUFLOR_TEST_GEMINI_SESSIZ"] = "1"; ad["PIPER_OYNAT"] = "/yok"; time.sleep(0.3)
cb = int(open(cal_say).read().strip() or 0) if os.path.exists(cal_say) else -1
bak(f"akarak çalarken şişme: sınıra kadar ({cb / 48000:.2f} sn ≤ 6,7) çalındı, yeniden istenmedi", r_c is True and 0 < cb <= 6.7 * 48000 and len(GELEN) - n == 1 and "çalınırken sınırda kesildi" in out.getvalue())
DAVRANIS.update(tur="ok"); ad["GEMINI"]["hata_t"] = 0
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
# v0.127.0: varsayılan zincir Lite → 3.8 Flash; ikisi de dolunca False (çağıran yerel sese, Pocket'e döner), 3.1/2.5 denenmez; gemini_izinli de kapanır
bak("varsayılan zincir: Lite → 3.8 Flash", ad["gemini_zincir"]() == ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"))
ad["AYAR"]["gemini_model"] = "gemini-3.8-flash-tts"; bak("ayarda Flash seçiliyse: Flash → Lite", ad["gemini_zincir"]() == ("gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts")); ad["AYAR"].pop("gemini_model")
DAVRANIS.update(tur="gunluk"); ad["GEMINI"]["hata_t"] = 0; n = len(GELEN); t0 = time.time(); rv = ad["gemini_oku"]("Günlük sınır varsayılan.")
yollar = [g["yol"] for g in GELEN[n:]]
bak(f"günlük sınır (varsayılan): beklemeden 3.8 Flash'a geçer ({time.time() - t0:.1f} sn, {len(yollar)} istek)", rv is True and len(yollar) == 2 and "flash-lite" not in yollar[1] and time.time() - t0 < 1.5)
DAVRANIS.update(tur="gunluk2"); n = len(GELEN); rv2 = ad["gemini_oku"]("İkisi de dolu varsayılan."); yl = [g["yol"].split("/")[3].split(":")[0] for g in GELEN[n:]]
bak(f"ikisi de dolu (varsayılan): 3.1/2.5 denenmez, False; model yok ({yl})", rv2 is False and yl == ["gemini-3.8-flash-tts"] and ad["gemini_model"]() is None)
os.remove(os.path.join(T, "gemini-kota.json")); ad["GEMINI_KOTA"]["dolu"] = None; ad["GEMINI"]["hata_t"] = 0
ad["AYAR"]["gemini_yedek_model"] = False
DAVRANIS.update(tur="gunluk"); n = len(GELEN); rv3 = ad["gemini_oku"]("Yedeksiz.")
bak(f"gemini_yedek_model: false — yalnız ayardaki model, dolunca False ({len(GELEN) - n} istek)", rv3 is False and len(GELEN) - n == 1 and ad["gemini_model"]() is None)
os.remove(os.path.join(T, "gemini-kota.json")); ad["GEMINI_KOTA"]["dolu"] = None; ad["GEMINI"]["hata_t"] = 0
ad["AYAR"]["gemini_yedek_model"] = True  # eski yedek zinciri ayarla açılır
DAVRANIS.update(tur="gunluk"); ad["GEMINI"]["hata_t"] = 0; n = len(GELEN); t0 = time.time(); rg = ad["gemini_oku"]("Günlük sınır.")
yollar = [g["yol"] for g in GELEN[n:]]
bak(f"günlük sınır: beklemeden 3.8 Flash'a geçer ({time.time() - t0:.1f} sn, {yollar})", rg is True and len(yollar) == 2 and "flash-lite" in yollar[0] and "flash-lite" not in yollar[1] and time.time() - t0 < 1.5)
n = len(GELEN); ad["gemini_oku"]("Sonraki cümle.")
bak("sonraki cümle dolu modeli hiç denemez", len(GELEN) - n == 1 and "flash-lite" not in GELEN[-1]["yol"])
DAVRANIS.update(tur="gunluk2"); n = len(GELEN); rg2 = ad["gemini_oku"]("İkisi de dolu."); n2 = len(GELEN); rg3 = ad["gemini_oku"]("Yine.")
yl = [g["yol"].split("/")[3].split(":")[0] for g in GELEN[n:n2]]
bak(f"yedek sırası 3.8 Flash → 3.1 Flash → 2.5 Flash, hepsi dolu: False, sonra istek atılmaz ({yl} + {len(GELEN) - n2})",
    rg2 is False and rg3 is False and yl == ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"] and len(GELEN) == n2)
ad["GEMINI_KOTA"]["dolu"] = None; bak("kayıt dosyasından yüklenir (aktarıcı yeniden başlasa da)", ad["gemini_model"]() is None and "kota_dolu" in ad["gemini_view"]())
os.remove(os.path.join(T, "gemini-kota.json")); ad["GEMINI_KOTA"]["dolu"] = None; ad["GEMINI"]["hata_t"] = 0; DAVRANIS.update(tur="normal")
ad["AYAR"].pop("gemini_yedek_model")
bak("kayıt yoksa ayardaki model", ad["gemini_model"]() == "gemini-3.8-flash-lite-tts")
# v0.127: günlük sayaç Pasifik gece yarısı sıfırlanır (America/Los_Angeles; yaz saatinde UTC 07.00 = TR 10.00, kışın UTC 08.00 = TR 11.00)
import datetime as _dtz
_u = lambda *a: _dtz.datetime(*a, tzinfo=_dtz.timezone.utc).timestamp()
gb = ad["gemini_gun_basi"]
bak("sayaç günü: yaz saati (PDT) — UTC 06.59'da önceki gün, 07.00'de yeni gün",
    gb(_u(2026, 10, 24, 6, 59)) == _u(2026, 10, 23, 7, 0) and gb(_u(2026, 10, 24, 7, 0)) == _u(2026, 10, 24, 7, 0))
bak("sayaç günü: kış saati (PST) — UTC 07.59'da önceki gün, 08.00'de yeni gün",
    gb(_u(2026, 12, 1, 7, 59)) == _u(2026, 11, 30, 8, 0) and gb(_u(2026, 12, 1, 8, 0)) == _u(2026, 12, 1, 8, 0))
bak("sayaç günü: saat değişimi günü (1 Kasım 2026) gece yarısı PDT", gb(_u(2026, 11, 1, 12, 0)) == _u(2026, 11, 1, 7, 0))
# v0.127: kendi sayacımız (gemini-ses.jsonl, Google günü) — %80'de bir kez uyarı, 100'de istek atılmaz (429 beklenmez), günlükte birer satır
import contextlib, io, datetime as _dt
UYARI = []; ad["yerel_uyari"] = UYARI.append; ad["_t"] = lambda a, b: a
yol_k = os.path.join(T, "gemini-ses.jsonl"); simdi_ = _dt.datetime.now().isoformat(timespec="seconds")
def _say(n_): open(yol_k, "w").write("".join(json.dumps({"t": simdi_, "model": "gemini-3.8-flash-lite-tts"}) + "\n" for _ in range(n_))); ad["_BUGUN"]["t"] = 0.0
ad["AYAR"]["gemini_yedek_model"] = False; cikti = io.StringIO()
with contextlib.redirect_stdout(cikti):
    _say(79); ad["_kota_bak"]("gemini-3.8-flash-lite-tts"); u0 = len(UYARI)
    _say(80); ad["_kota_bak"]("gemini-3.8-flash-lite-tts"); _say(85); ad["_kota_bak"]("gemini-3.8-flash-lite-tts")
bak(f"%80 uyarısı (yalnız ayardaki model): 79'da yok, 80'de bir kez (85'te yinelenmez) — {UYARI}", u0 == 0 and len(UYARI) == 1 and "yüzde seksen" in UYARI[0] and cikti.getvalue().count("%80'i doldu") == 1)
bak("panoya: gemini_gunluk uyari işareti", ad["gemini_gunluk_view"]()["uyari"] is True)
ad["GEMINI_KOTA"].pop("uyari_gun", None); UYARI.clear(); ad["AYAR"].pop("gemini_yedek_model")
def _say2(nl, nf):
    open(yol_k, "w").write("".join(json.dumps({"t": simdi_, "model": m_}) + "\n" for m_, k_ in (("gemini-3.8-flash-lite-tts", nl), ("gemini-3.8-flash-tts", nf)) for _ in range(k_))); ad["_BUGUN"]["t"] = 0.0
cikti = io.StringIO()
with contextlib.redirect_stdout(cikti):
    _say2(100, 0); ad["_kota_bak"]("gemini-3.8-flash-lite-tts"); u1 = len(UYARI)
    _say2(100, 59); ad["_kota_bak"]("gemini-3.8-flash-tts"); u2 = len(UYARI)
    _say2(100, 60); ad["_kota_bak"]("gemini-3.8-flash-tts")
bak(f"zincirde %80 iki modelin toplamına göre: Lite 100'de uyarı yok, 159'da yok, 160'ta bir kez; Lite dolunca 'sıradaki model' satırı",
    u1 == 0 and u2 == 0 and len(UYARI) == 1 and "sıradaki model gemini-3.8-flash-tts" in cikti.getvalue() and ad["gemini_model"]() == "gemini-3.8-flash-tts")
ad["GEMINI_KOTA"].pop("uyari_gun", None); ad["GEMINI_KOTA"].pop("dolu_gun", None); UYARI.clear(); ad["AYAR"]["gemini_yedek_model"] = False
_say(100); n = len(GELEN); cikti = io.StringIO()
with contextlib.redirect_stdout(cikti): ad["_kota_bak"]("gemini-3.8-flash-lite-tts"); r100 = ad["gemini_oku"]("Sınırda."); ad["_kota_bak"]("gemini-3.8-flash-lite-tts")
bak(f"sayaç 100: istek atılmaz, False; model yok; günlükte tek satır ({cikti.getvalue().count('günlük sınır doldu')})", r100 is False and len(GELEN) == n and ad["gemini_model"]() is None and cikti.getvalue().count("günlük sınır doldu") == 1)
bak("panoda model dolu görünür", ad["gemini_gunluk_view"]()["modeller"][0]["dolu"] is True)
os.remove(yol_k); ad["_BUGUN"]["t"] = 0.0; ad["GEMINI_KOTA"].pop("uyari_gun", None); ad["GEMINI_KOTA"].pop("dolu_gun", None); ad["AYAR"].pop("gemini_yedek_model")
bak("sayaç sıfırlanınca yine Gemini", ad["gemini_model"]() == "gemini-3.8-flash-lite-tts")
# v0.127: önceden isteme — çalan okuma sürerken sıradaki parçanın sesi istenir; okuma sırası gelince yeni istek atılmadan çalar; anahtar metin + ses
n = len(GELEN); ok_ = ad["gemini_onceden"]("Sıradaki söz burada.", "Kore", "neşeli"); time.sleep(0.6)
bak(f"önceden isteme: bir istek, metin + ses + üslup ({len(GELEN) - n})", ok_ and len(GELEN) - n == 1 and '"voice_name": "Kore"' in json.dumps(GELEN[-1]["govde"]) and "neşeli" in GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"])
bak("aynı söz ikinci kez istenmez", ad["gemini_onceden"]("Sıradaki  söz burada.", "Kore") and len(GELEN) - n == 1)
CAL_ = []; kayit_ = {}; ad["ses_basladi"] = lambda k=None: CAL_.append(time.time())
t0 = time.time(); ro = ad["gemini_oku"]("Sıradaki söz burada.", ses="Kore", kayit=kayit_)
bak(f"okuma sırası gelince istek atılmadan çalar ({len(GELEN) - n} istek, {time.time() - t0:.2f} sn, çalma anı {len(CAL_)})", ro is True and len(GELEN) - n == 1 and len(CAL_) == 1)
n = len(GELEN); ad["gemini_oku"]("Sıradaki söz burada.", ses="Kore"); bak("kullanılan önceden alınmış ses bir daha kullanılmaz (yeni istek)", len(GELEN) - n == 1)
n = len(GELEN); ad["gemini_onceden"]("Başka sesle.", "Kore"); time.sleep(0.4); ad["gemini_oku"]("Başka sesle.", ses="Charon")
bak("ses farklıysa önceden alınan kullanılmaz", len(GELEN) - n == 2)
ad["gemini_onceden"]("Kesilecek söz.", "Kore"); time.sleep(0.4); ad["gemini_onceden_temizle"]("deneme"); n = len(GELEN); ad["gemini_oku"]("Kesilecek söz.", ses="Kore")
bak("okuma kesilince önceden alınanlar atılır", len(GELEN) - n == 1)
DAVRANIS["tur"] = "yavas"; n = len(GELEN); ad["gemini_onceden"]("Yavaş gelen.", "Kore"); time.sleep(0.2); DAVRANIS["tur"] = "ok"; time.sleep(3)
t0 = time.time(); ry = ad["gemini_oku"]("Yavaş gelen.", ses="Kore")
bak(f"önceden isteme yavaşsa (ses gelmedi) normal istekle okunur ({len(GELEN) - n} istek, {time.time() - t0:.1f} sn)", ry is True and len(GELEN) - n == 2)
ad["GEMINI"]["hata_t"] = 0; _say2(100, 100)
bak("sayaç doluyken (iki model) önceden istenmez", ad["gemini_onceden"]("Dolu.", "Kore") is False); os.remove(yol_k); ad["_BUGUN"]["t"] = 0.0
bak("ayarda yedek model seçilemez (3.1 → Flash-Lite)", (ad["AYAR"].__setitem__("gemini_model", "gemini-3.1-flash-tts-preview"), ad["gemini_model"]())[1] == "gemini-3.8-flash-lite-tts"); ad["AYAR"].pop("gemini_model")
# v0.80.11: sabit cümle önbelleği — ilk GEMINI_SABIT_N okuyuş Gemini'den (kaydedilir), sonra istek yok; art arda aynı okuyuş değil; sabit olmayan cümle önbelleğe girmez
ad["BEKLE_GENEL"] = {"tr": ["Bir saniye.", "Bakayım."]}; ad["GEMINI"]["hata_t"] = 0
n = len(GELEN); [ad["gemini_oku"]("Bir saniye.", ses="Charon") for _ in range(3)]; n3 = len(GELEN)
kl = ad["_sabit_klasor"]("Bir saniye.", "Charon", None); dosyalar = sorted(f for f in os.listdir(kl) if f.endswith(".pcm"))
bak(f"ilk 3 okuyuş Gemini'den, önbelleğe yazılır ({n3 - n} istek, {dosyalar})", n3 - n == 3 and dosyalar == ["0.pcm", "1.pcm", "2.pcm"])
secilen = []; ad["_SABIT_SON"].clear()
for _ in range(6): r_ = ad["gemini_oku"]("Bir saniye.", ses="Charon"); secilen.append(ad["_SABIT_SON"][kl])
bak(f"sonra istek atılmaz, art arda aynı okuyuş yok ({len(GELEN) - n3} istek, {secilen})", len(GELEN) == n3 and r_ is True and all(a != b for a, b in zip(secilen, secilen[1:])))
pc = ad["gemini_oku"]("Bir saniye.", ses="Charon", topla=True)
bak("toplantıya söyle (topla) önbellekten ham ses alır", isinstance(pc, bytes) and len(pc) == 48000 and len(GELEN) == n3)
n = len(GELEN); ad["gemini_oku"]("Bir saniye.", ses="Kore"); bak("başka ses ayrı önbellek (Kore için yine istek)", len(GELEN) - n == 1)
n = len(GELEN); ad["gemini_oku"]("Bu sabit değil."); ad["gemini_oku"]("Bu sabit değil.")
bak("sabit olmayan cümle her seferinde Gemini'ye gider", len(GELEN) - n == 2)
n = len(GELEN); [ad["gemini_oku"]("Hı hı.", ses="Charon", duzey=0.5) for _ in range(4)]; bak(f"hı hı da önbellekte (4 okumada {len(GELEN) - n} istek)", len(GELEN) - n == 3)
bak("sohbetin 30 sn uyarısı ('Buradayım.') sabit cümle", ad["_sabit_mi"]("Buradayım.") and ad["_sabit_mi"]("I'm here.") and not ad["_sabit_mi"]("Buradayım, söyle bakalım ne istiyorsun."))
bak("v0.127: kısa söz (≤ 3 sözcük, ≤ 24 karakter) ve sahne tepki havuzu sabit; uzun söz değil", ad["_sabit_mi"]("Hadi ya!") and ad["_sabit_mi"]("Haklısın, kabul.")
    and (ad.__setitem__("SAHNE_ONAY", ["Bunu bu açıdan görmemiştim."]), ad["_sabit_mi"]("Bunu bu açıdan görmemiştim."))[1] and not ad["_sabit_mi"]("Bunu hiç bu açıdan görmemiştim."))
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
tsn.update(PIPER_OYNAT=SAHTE, kisilik_sesi=lambda zorla=None, toplantiya=False: ("gemini", "Kore", 1.0), kisilik=lambda: {"ses_uslup": "ölçülü"}, kisilik_telaffuz=lambda m: m, ses_duzen=lambda m, mac=True: m,
           AYAR={"toplantiya_ses": True}, STATE={"masaustu": {"toplantida": True}}, toplanti_var=lambda: True, ts_web=lambda: False, ts_aygit=lambda: "59", otonom_kisayol=lambda: None,
           ses_secimi=lambda: None, telaffuz=lambda m, mac=False: m, ses_durdur=lambda: None, kulaklik=lambda: True, kendi_ses_kaydet=lambda *a: None, note=lambda *a: None, kart_bildir=lambda: None,
           sesli_terim_suz=lambda m: m, etiket_sil=lambda m: m, _t=lambda a, b: a, ARAYUZ_DILI="tr", kisilik_ad=lambda: "Atlas", re=__import__("re"), secrets=__import__("secrets"))
exec(compile(open(os.path.join(K, "aktarici", "toplantiya-ses.py"), encoding="utf-8").read(), "toplantiya-ses.py", "exec"), tsn)
tsn["ts_aygit"] = lambda: "59"  # bölüm dosyası kendi ts_aygit'ini tanımlar (gerçek BlackHole kimliği yeniden başlatınca değişir: 59 → 85, 19 Ekim)
tsn["TS"]["tanitti"] = "?"  # tanıtım bu denemede okunmasın
r = tsn["toplantiya_soyle"]("Bütçe onaylandı."); time.sleep(0.5)
argl = [x for x in open(SAHTE + ".arg").read().split("\n") if x]
bak(f"toplantıya söyle Gemini: BlackHole (59) + kulaklık, Kore ({argl}, {r})", r.get("ok") and argl == ["24000 59", "24000"] and '"voice_name": "Kore"' in json.dumps(GELEN[-1]["govde"]) and "## Style:\nölçülü" in GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"])
# v0.81.0 (S92): tanıtım ayrı okunup cevabın önüne eklenir ve önbelleğe girer; ikinci toplantıda tanıtım için istek yok
def _tan(toplanti):
    ts_ = tsn; eski_ = (ts_["kisilik"], ts_["STATE"]); ts_["kisilik"] = lambda: {"ses_uslup": "ölçülü", "tanitim": "Merhaba, ben Atlas."}; ts_["TS"]["tanitti"] = None; ts_["STATE"] = {"masaustu": {"toplantida": True, "baslik": toplanti}}
    ts_["TS"]["p"] = []; n = len(GELEN); r_ = ts_["toplantiya_soyle"]("Bütçe bu hafta onaylandı, sevkiyat da başlıyor."); time.sleep(0.3); ts_["kisilik"], ts_["STATE"] = eski_
    return r_, [g["govde"]["contents"][0]["parts"][0]["text"].split("## Transcript:\n")[-1] for g in GELEN[n:]]
for i_ in range(3): r1_, m1_ = _tan(f"T{i_}")
r2_, m2_ = _tan("T9")
bak(f"tanıtım ayrı istek, ilk 3 toplantıda önbelleğe yazılır ({m1_})", r1_.get("ok") and m1_ == ["Bütçe bu hafta onaylandı, sevkiyat da başlıyor.", "Merhaba, ben Atlas."] and "Merhaba, ben Atlas." in r1_.get("metin", ""))
bak(f"sonra tanıtım önbellekten, yalnız cevap Gemini'ye ({m2_})", r2_.get("ok") and m2_ == ["Bütçe bu hafta onaylandı, sevkiyat da başlıyor."])
# 1d) hı hı: Gemini sesiyle konuşan kişilikte klip değil o anda Gemini (tepki_cal)
bs = open(os.path.join(K, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); i = bs.index("def tepki_cal("); tc = dict(ad)
tc.update(AYAR={}, piper_acik=lambda: False, kisilik_sesi=lambda zorla=None, toplantiya=False: ("gemini", "Charon", 1.0), threading=threading); n0 = len(GELEN)
exec(bs[i:bs.index("\n_TEPKI_BAS", i)], tc)
r1 = tc["tepki_cal"]("alindi", hemen=True, ses=0.4); time.sleep(0.8)
bak("hı hı: Gemini'den o anda (klip yok), kısık, Charon", r1 is True and len(GELEN) == n0 + 1 and '"voice_name": "Charon"' in json.dumps(GELEN[-1]["govde"]) and "Hı" in GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"] + "Hım")
bak("bekleme (düşünme) klibi Gemini'de çalmaz → çağıran cümleyi okur", tc["tepki_cal"]("dusunme") is False)

# 1e) v0.127 karışık okuma (bas-konus.py _konus_cumle): Gemini sesinde ilk cümle hemen ve tek başına, kalanlar cevap bitince tek okumada; Claude geç
# bitirirse ilk okuma bitince biriken okunur; okuma kesildiyse biriken okunmaz; uzun cevap iki parça; Pocket'te cümle cümle; okuma sınırı (5 cümle) aynen
import ast as _ast
bk_ = _ast.parse(open(os.path.join(K, "aktarici", "bas-konus.py"), encoding="utf-8").read())
fk_ = [f for f in bk_.body if (isinstance(f, _ast.FunctionDef) and f.name in ("_konus_cumle", "_konus_g_biriktir", "_konus_g_bosalt", "_konus_g_bekci"))
       or (isinstance(f, _ast.Assign) and any(getattr(t, "id", "") in ("KONUS_OKU_EN_COK", "_KG_K") for t in f.targets))]
def karisik(motor, cumleler, son_bekle=0.0, kes_ara=False, calan=lambda: False):
    OKU = []; SES_ = {"kes": 0}
    kn = {"re": __import__("re"), "time": time, "threading": threading, "print": lambda *a, **k: None, "SES": SES_, "GEMINI_BIRLESIK_EN_COK": 600,
          "kisilik_sesi": lambda m=None, toplantiya=False: (motor, None, 1.0), "konusma_dili": lambda c: c, "sesli_terim_suz": lambda c: c,
          "seslendir": lambda c, kuyruk=False, cal=None, ozet=False: (OKU.append(c), True)[1], "ses_caliyor": calan}
    exec(compile(_ast.Module(fk_, []), "bas-konus.py", "exec"), kn)
    tur = {"tampon": "", "sesli": True}
    for i_, c_ in enumerate(cumleler):
        tur["tampon"] += c_ + " "; kn["_konus_cumle"](tur)
        if kes_ara and i_ == 1: SES_["kes"] += 1
    time.sleep(son_bekle); kn["_konus_cumle"](tur, son=True); tur["t_son"] = time.time(); time.sleep(0.15)
    return OKU
CV = ["Merhaba, bugün iki konu var.", "Birincisi bütçe onayı.", "İkincisi tedarik takvimi.", "Ayrıntılar panoda."]
o_ = karisik("gemini", CV, calan=lambda: True)
bak(f"Gemini: ilk cümle tek başına, kalan 3 cümle tek okumada ({o_})", o_ == [CV[0], " ".join(CV[1:])])
o_ = karisik("pocket", CV)
bak(f"Pocket: cümle cümle (bugünkü gibi) ({len(o_)} okuma)", o_ == CV)
o_ = karisik("gemini", CV, son_bekle=0.3, calan=lambda: False)
bak(f"Claude geç bitirirse ilk okuma bitince biriken okunur, sonra kalan ({o_})", o_[0] == CV[0] and " ".join(o_[1:]) == " ".join(CV[1:]) and len(o_) <= 3)
o_ = karisik("gemini", CV, kes_ara=True, calan=lambda: True)
bak(f"okuma kesildiyse (dur / Option + Shift + S) biriken okunmaz ({o_})", o_ == [CV[0]])
UZ = ["Bu birinci cümle ve oldukça uzun bir açıklama içeriyor, " * 2 + "tamam."] + ["Bu cümle de uzun ve ayrıntılı bir açıklama, " * 5 + "bitti."] * 4
o_ = karisik("gemini", UZ, calan=lambda: True)
bak(f"uzun cevap: okuma sınırı 5 cümle, kalan 600 karakteri aşınca iki parça ({[len(x) for x in o_]})", len(o_) == 3 and o_[0] == UZ[0] and all(len(x) <= 600 for x in o_))
o_ = karisik("gemini", CV + ["Beşinci cümle burada.", "Altıncı okunmaz."], calan=lambda: True)
bak(f"okuma sınırı (KONUS_OKU_EN_COK = 5) aynen: altıncı cümle okunmaz ({o_})", "Altıncı" not in " ".join(o_) and "Beşinci" in o_[-1])

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
