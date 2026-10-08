#!/usr/bin/env python3
# Faz 4 — bas-konuş uçtan uca, kota harcamadan: say → 16 kHz PCM → /bas-konus → yerel Whisper → Brifing.app açık süreç kipi (brifing.swift
# bu sınamada derlenir) → sahte "claude" (stream-json konuşur, soruyu yankılar) → cümle cümle okuma (SUFLOR_TEST_BASLAT: ses çalınmaz).
# Aktarıcıda konus_* / Whisper döngüsünün bas dalı / brifing.swift açık süreç kipi / panodaki Konuş değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bas-konus.py
# Gerekenler: swiftc, kurulu Brifing.app (ayar.json'daki uygulama klasöründe; paket iskeleti için), whisper-venv (/Users/Shared/Suflor).
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request, wave
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8791
T = tempfile.mkdtemp(prefix="bas-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc") or not os.path.exists("/Users/Shared/Suflor/whisper-venv/bin/python"): sys.exit("atlandı: Brifing.app, swiftc ya da whisper-venv yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
arg = sys.argv[1:]; assert "--input-format" in arg and "stream-json" in arg and not any("Bash" in a or "Write" in a for a in arg) and arg[arg.index("--model") + 1] == "sonnet"
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.split("Soru: ", 1)[-1]
    b = "[Bağlam" in q and "Şimdi:" in q and "Deneme planlama" in q and "GİZLİ NOT" not in q  # davet notu girmez
    if n == 2: pr({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "tool_use", "name": "Grep"}}}); time.sleep(0.3)
    for parca in ["Sorduğun: ", soru.rstrip(".?!") + ".", " Basecamp takvimi", " geldi." if b else " gelmedi."]:
        time.sleep(0.15); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    pr({"type": "result", "duration_api_ms": 500, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
import datetime as _dt
_y = (_dt.datetime.now().astimezone() + _dt.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "e1", "baslik": "Deneme planlama", "baslangic": _y.isoformat(), "bitis": (_y + _dt.timedelta(minutes=30)).isoformat(),
           "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Deniz T"], "kisi_sayisi": 2, "notlar": "GİZLİ NOT"}]}, open(os.path.join(T, "takvim.json"), "w"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
def pcm(metin):
    a, w = os.path.join(T, "q.aiff"), os.path.join(T, "q.wav")
    subprocess.run(["say", "-v", "Yelda", "-o", a, metin]); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w])
    with wave.open(w) as f: return base64.b64encode(f.readframes(f.getnframes())).decode()
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(v, pano=True):
        h = {"X-Suflor-Anahtar": K, **({"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/bas-konus", data=json.dumps(v).encode(), headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["konus"]
    log = lambda: open(os.path.join(T, "relay.log")).read()
    def sor(metin):
        p = pcm(metin); post({"komut": "basla"}); time.sleep(1.5); post({"pcm": p}); t0 = time.time()
        while time.time() - t0 < 60:
            k = st()
            if k["durum"] in ("hazir", "hata"): return k
            time.sleep(0.2)
        return st()
    ok("yalnız panodan (pano kökeni yoksa 403)", post({"komut": "basla"}, pano=False).get("kod") == 403)
    k = sor("Toplantı en çok kaç dakika sürmeli?")
    ok("soru yazıya döküldü ve Claude'a gitti", k["durum"] == "hazir" and "dakika" in (k.get("soru") or "").lower() and "Sorduğun" in (k.get("cevap") or ""))
    ok("cümle cümle okundu (ilk cümle sonuçtan önce)", log().count("SES (deneme)") == 2 and k["olcum"]["ses_ms"] < k["olcum"]["sure_ms"])
    ok("soruya tarih + yarının takvimi eklendi", "takvimi geldi" in (k.get("cevap") or ""))
    ok("okunurken yabancı ad Türkçe yazımla, pano metni aynen", "Beyskemp takvimi geldi" in log() and "Basecamp takvimi" in (k.get("cevap") or ""))
    ok("açık süreç bir kez açıldı", log().count("KONUŞ: açık süreç açıldı") == 1)
    k2 = sor("Toplantının sonunda ne yazılır?")
    ok("araç başlayınca 'Bakıyorum' söylendi (yalnız ikinci soruda)", log().count("Bakıyorum.") == 1 and log().count("SES (deneme)") == 5)
    ok("ikinci soru aynı süreçte, tur maliyeti farkla", k2["durum"] == "hazir" and log().count("KONUŞ: açık süreç açıldı") == 1 and abs(k2["olcum"]["maliyet"] - 0.01) < 1e-6)
    c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    ok("ölçüm claude-cagri.jsonl'de (bas-konus, wh/ilk/ses)", len(c) == 2 and all(x["is"] == "bas-konus" and x["wh_ms"] and x["ilk_ms"] and x["ses_ms"] for x in c)
       and c[0]["arac"] == 0 and c[1]["arac"] == 1 and c[1]["araclar"] == ["Grep"] and c[1]["arac_ilk_ms"])
    ok("döküme yazılmadı", not any(f.endswith(".md") for f in os.listdir(canli)))
    ok("çok kısa kayıt reddedildi", post({"komut": "basla"}).get("ok") and not post({"pcm": base64.b64encode(b"\0" * 3200).decode()}).get("ok"))
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/ping", data=json.dumps({"call": True, "panel": True}).encode(), headers={"X-Suflor-Anahtar": K}))
    ok("toplantı sürerken kapalı", not post({"komut": "basla"}).get("ok"))
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); subprocess.run(["pkill", "-f", T])
print("bas-konuş:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
