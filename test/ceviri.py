#!/usr/bin/env python3
# Canlı çeviri (aktarici/ceviri.py, v0.27.0; ayar ceviri: true). Yalıtılmış aktarıcı, deneme çevirmeni (SUFLOR_TEST_CEVIRI: Claude çağrılmaz):
# karşı tarafın İngilizce Whisper satırı çevrilir, panonun /status tail'inde "ceviri" alanı, <toplantı>.ceviri.jsonl'e yazılır, .jsonl değişmez ·
# Türkçe satır ve kullanıcının kendi satırı çevrilmez · ayar kapalıyken çevrilmez · dil tahmini tablosu. İsteğe bağlı gerçek Claude denemesi:
# SUFLOR_CEVIRI_GERCEK=1 (az kota: tek öbek). Faz 11 Aşama 2: ayar beyin.ceviri openai-uyumlu → sahte OpenAI uyumlu sunucu (beyin.py calis, araçsız; kayıtta
# saglayici), sağlayıcı 503 verince öbek bir kez sahte Claude Code'la (günlükte BEYİN: yedek; yuva yedek süresince Claude'da).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ceviri.py      (kaldı → çıkış 1; ~15 sn)
import http.server, json, os, re, shutil, socket, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8779)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
def calistir(ceviri=True, gercek=False, kulaklik=None, ek=None, env_ek=None):
    T = tempfile.mkdtemp(prefix="suflor-cv-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    ay = os.path.join(T, "ayar.json"); json.dump(dict({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "ceviri": ceviri}, **(ek or {})), open(ay, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", **(env_ek or {}))
    if not gercek: env["SUFLOR_TEST_CEVIRI"] = "1"
    if kulaklik is not None: env["SUFLOR_TEST_KULAKLIK"] = "1" if kulaklik else "0"
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def istek(yol, v=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K})
        return json.loads(urllib.request.urlopen(q, timeout=40).read())
    return r, T, canli, istek
def satirlar(istek):
    t = time.time()
    istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [
        {"id": "wh/karsi/1", "speaker": "John", "time": "10:00:00", "text": "We can ship the new version on Monday if the tests pass.", "kanal": "karsi", "t0": t, "t1": t + 3},
        {"id": "wh/karsi/2", "speaker": "Ayşe", "time": "10:00:05", "text": "Bence bu hafta bitiremeyiz, çok iş var.", "kanal": "karsi", "t0": t + 5, "t1": t + 8},
        {"id": "wh/ben/1", "speaker": "Ali K", "time": "10:00:10", "text": "Okay, and what about the budget for this?", "kanal": "ben", "t0": t + 10, "t1": t + 12}]})
r, T, canli, istek = calistir()
try:
    satirlar(istek); time.sleep(3.5)
    tl = {x["id"]: x for x in istek("/status")["tail"] if x.get("id")}
    bak("İngilizce karşı satır çevrildi (tail'de ceviri)", tl.get("wh/karsi/1", {}).get("ceviri", "").startswith("[çeviri] We can ship"))
    bak("Türkçe karşı satır çevrilmedi", "ceviri" not in tl.get("wh/karsi/2", {}))
    bak("kullanıcının kendi satırı çevrilmedi", "ceviri" not in tl.get("wh/ben/1", {}))
    cv = [f for f in os.listdir(canli) if f.endswith(".ceviri.jsonl")]
    bak(".ceviri.jsonl yazıldı, .jsonl'de ceviri yok", cv and "ceviri" not in open(os.path.join(canli, cv[0].replace(".ceviri.jsonl", ".jsonl")), encoding="utf-8").read())
    bak("/status ceviri: açık, 1 satır", (istek("/status").get("ceviri") or {}).get("n") == 1)
finally: r.terminate(); r.wait(5)
shutil.rmtree(T, ignore_errors=True)
r, T, canli, istek = calistir(ceviri=False)
try:
    satirlar(istek); time.sleep(3.5)
    bak("ayar kapalıyken çevrilmez", not any("ceviri" in x for x in istek("/status")["tail"]))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
# sesli çeviri (v0.29.0): 🎧 kulaklıksız açılmaz; açılınca çeviri ayarı kapalı olsa da çevrilir, kısa öz okunur; tekrar basınca kapanır
r, T, canli, istek = calistir(ceviri=False, kulaklik=False)
try:
    k = istek("/komut", {"tur": "sesli_ceviri"})
    bak("kulaklık yokken sesli çeviri açılmaz (uyarı)", "Kulaklık" in k.get("metin", "") and not istek("/cards").get("sesli_ceviri"))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
r, T, canli, istek = calistir(ceviri=False, kulaklik=True)
try:
    istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [{"id": "wh/karsi/0", "speaker": "John", "time": "09:59:00", "text": "Hello everyone, thanks for joining today.", "kanal": "karsi", "t0": time.time(), "t1": time.time() + 2}]})
    k = istek("/komut", {"tur": "sesli_ceviri"})
    bak("kulaklıkla sesli çeviri açıldı", "açık" in k.get("metin", "") and (istek("/cards").get("sesli_ceviri") or {}).get("acik"))
    satirlar(istek); time.sleep(3.5)
    log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    bak("ayar kapalı ama sesli açık: satır çevrildi", any(x.get("id") == "wh/karsi/1" and "ceviri" in x for x in istek("/status")["tail"]))
    bak("kısa öz okundu (Türkçe satır ve kendi satırı okunmadı)", log.count("SESLİ ÇEVİRİ (deneme): [kısa] We can ship") == 1 and log.count("SESLİ ÇEVİRİ (deneme)") == 1)
    bak("panoda okunan sayısı 1", (istek("/cards").get("sesli_ceviri") or {}).get("okunan") == 1)
    istek("/komut", {"tur": "sesli_ceviri"})
    bak("tekrar basınca kapandı", not istek("/cards").get("sesli_ceviri"))
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
# --- Faz 11 Aşama 2: başka sağlayıcı ve Claude Code yedeği (sahte sunucu + sahte claude; ağ ve kota yok) ---
GELEN, DURUM = [], {"kod": 200}
def _cevir(icerik, on):  # "1. metin" satırları → {"1": "[on] metin", "k1": …}
    o = {}
    for m in re.finditer(r"^(\d+)\. (.*)$", icerik, re.M): o[m.group(1)] = f"[{on}] {m.group(2)}"; o["k" + m.group(1)] = f"[{on}-kısa] {' '.join(m.group(2).split()[:3])}"
    return json.dumps(o, ensure_ascii=False)
class Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        g = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); GELEN.append(g)
        if DURUM["kod"] != 200: b = b'{"error":{"message":"overloaded"}}'; self.send_response(DURUM["kod"]); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        p = [{"choices": [{"delta": {"content": _cevir(g["messages"][-1]["content"], "gemini")}, "finish_reason": "stop"}]}, {"choices": [], "usage": {"prompt_tokens": 500, "completion_tokens": 50}}]
        b = ("".join("data: " + json.dumps(x, ensure_ascii=False) + "\n\n" for x in p) + "data: [DONE]\n\n").encode()
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
so = socket.socket(); so.bind(("127.0.0.1", 0)); SPORT = so.getsockname()[1]; so.close()
SV = http.server.ThreadingHTTPServer(("127.0.0.1", SPORT), Sahte); threading.Thread(target=SV.serve_forever, daemon=True).start()
TD = tempfile.mkdtemp(prefix="suflor-cv-claude-"); SAHTE = os.path.join(TD, "claude")
open(SAHTE, "w").write("#!/usr/bin/env python3\nimport sys, json, re\n" + "def _cevir(icerik, on):\n    o = {}\n    for m in re.finditer(r'^(\\d+)\\. (.*)$', icerik, re.M): o[m.group(1)] = f'[{on}] {m.group(2)}'; o['k' + m.group(1)] = f'[{on}-kısa] ' + ' '.join(m.group(2).split()[:3])\n    return json.dumps(o, ensure_ascii=False)\n"
                     "for l in sys.stdin:\n    j = json.loads(l); c = j['message']['content']; t = _cevir(c, 'claude')\n"
                     "    print(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': t}]}}), flush=True)\n"
                     "    print(json.dumps({'type': 'result', 'result': t, 'usage': {'input_tokens': 10}, 'total_cost_usd': 0.001}), flush=True)\n")
os.chmod(SAHTE, 0o755)
BEYIN_AYAR = {"claude": SAHTE, "ceviri_surec": 1, "beyin": {"ceviri": {"tur": "openai-uyumlu", "saglayici": "gemini", "adres": f"http://127.0.0.1:{SPORT}/v1", "model": "gemini-3.8-flash", "anahtar": "x", "fiyat": [1, 0.1, 10]}}}
def _tail(istek, lid):
    t = time.time()
    while time.time() - t < 15:
        x = next((x.get("ceviri") for x in istek("/status")["tail"] if x.get("id") == lid and x.get("ceviri")), None)
        if x: return x
        time.sleep(0.3)
    return ""
r, T, canli, istek = calistir(gercek=True, ek=BEYIN_AYAR, env_ek={"SUFLOR_TEST_BEYIN_ANAHTAR": "deneme"})
try:
    satirlar(istek); cv1 = _tail(istek, "wh/karsi/1")
    bak("başka sağlayıcı: satır beyin.py ile çevrildi (araçsız, ısınma turu yok, anahtar Bearer)", cv1.startswith("[gemini] We can ship") and len(GELEN) == 1 and "tools" not in GELEN[0])
    bak("istek dosyası 0600, anahtar içermez", all(os.stat(os.path.join(canli, f)).st_mode & 0o777 == 0o600 and "deneme" not in open(os.path.join(canli, f)).read() for f in os.listdir(canli) if f.startswith("ceviri-istek")))
    DURUM["kod"] = 503; t = time.time()
    istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [{"id": "wh/karsi/7", "speaker": "John", "time": "10:02:00", "text": "The supplier will send the invoice next week.", "kanal": "karsi", "t0": t, "t1": t + 3}]})
    cv2 = _tail(istek, "wh/karsi/7"); log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    bak("sağlayıcı 503 → öbek bir kez Claude Code'la çevrildi, günlükte tek BEYİN: yedek satırı", cv2.startswith("[claude] The supplier") and log.count("BEYİN: yedek — ceviri: gemini") == 1)
    if not cv2.startswith("[claude]"): print("   ", cv2, "|", log[-600:])
    DURUM["kod"] = 200; n = len(GELEN); t = time.time()
    istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [{"id": "wh/karsi/8", "speaker": "John", "time": "10:03:00", "text": "Can we move the meeting to Friday then?", "kanal": "karsi", "t0": t, "t1": t + 3}]})
    bak("yedek süresinde yuva Claude Code'da kalır (sağlayıcıya her satırda yeniden gidilmez)", _tail(istek, "wh/karsi/8").startswith("[claude]") and len(GELEN) == n)
    cg = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(canli, "claude-cagri.jsonl")) else []
    bak("kayıtta saglayici (gemini: model + maliyet; yedek: claude-code)", any(x.get("is") == "ceviri" and x.get("saglayici") == "gemini" and x.get("model") == "gemini-3.8-flash" and abs(x["maliyet"] - 0.001) < 1e-6 for x in cg)
        and any(x.get("is") == "ceviri" and x.get("saglayici") == "claude-code" and x.get("model") == "haiku" for x in cg))
    if not cg: print("   kayıt yok")
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
SV.shutdown(); shutil.rmtree(TD, ignore_errors=True)
if os.environ.get("SUFLOR_CEVIRI_GERCEK"):
    r, T, canli, istek = calistir(gercek=True)
    try:
        satirlar(istek); t = time.time(); tr = ""
        while time.time() - t < 40 and not tr:
            time.sleep(1); tr = next((x.get("ceviri", "") for x in istek("/status")["tail"] if x.get("id") == "wh/karsi/1"), "")
        print(f"   gerçek Claude: {time.time() - t:.1f} sn · {tr}")
        bak("gerçek Claude çevirisi Türkçe", any(c in tr for c in "çğıöşü") or "Pazartesi" in tr)
        # v0.32.1: özdeki yabancı adların okunuşu ("o") aynı cevapla telaffuz-oto.json'a yazılır
        istek("/ingest", {"meeting": {"title": "Çeviri Deneme"}, "source": "whisper", "entries": [{"id": "wh/karsi/9", "speaker": "John", "time": "10:01:00",
              "text": "Let's discuss the Salesforce dashboard and the HubSpot pipeline on Teams.", "kanal": "karsi", "t0": time.time(), "t1": time.time() + 3}]})
        yol = os.path.join(canli, "telaffuz-oto.json"); t = time.time()
        def _oto():
            try: return json.load(open(yol, encoding="utf-8"))
            except (OSError, ValueError): return {}
        while time.time() - t < 40 and not any(k.lower() in ("salesforce", "hubspot") for k in _oto()): time.sleep(1)  # dosya ilk çeviriden de olabilir
        oto = _oto()
        print(f"   okunuş: {oto}")
        bak("çeviri cevabındaki okunuşlar telaffuz-oto.json'da", any(k.lower() in ("salesforce", "hubspot") for k in oto))
        try: cg = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"), encoding="utf-8")]
        except OSError: cg = []
        cv = [x for x in cg if x.get("is") == "ceviri"]
        print(f"   çağrı kaydı: {len(cv)} çeviri turu · {round(sum(x.get('maliyet') or 0 for x in cv), 4)} $")
        bak("çeviri turları claude-cagri.jsonl'de (sayılar, metin yok)", cv and all("giris" in x and "metin" not in x for x in cv))
    finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("çeviri: ✓ hepsi geçti" if not hata else f"çeviri: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
