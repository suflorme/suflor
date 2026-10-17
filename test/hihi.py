#!/usr/bin/env python3
# Konuşurken "hı hı" (v0.47.0, aktarici/bas-konus.py _hihi_bak): ayar konus_hihi açık, kulaklık var, toplantı yok → uzun anlatımdaki yeni başlamış
# duraksamada (0,35–0,9 sn) kısık "alındı" klibi; ilk 6 sn'de ve son onaydan 12 sn içinde yok; ayar kapalıyken, kulaklık yokken ve toplantıda hiç yok.
# Ses: say (Yelda) cümleleri + aralarına sessizlik; 0,5 sn'lik parçalar gerçek zamanlı gönderilir. Olasılık testte 1 (HIHI_OLASILIK yerine ayar yok:
# SUFLOR_TEST_HIHI_KESIN=1). Gerçek Whisper gerekmez (akış parçaları kuyruğa düşer; işçi yoksa sonuç beklenmez).
# v0.48.0 tur sonu kapısı (tur-isci.py, smart-turn v3): işçi yokken eski kural; sahte işçi hep "cümle ortası" derse hiç çalmaz; gerçek model
# (ortak klasörde smart-turn-venv + model varsa) "…geçtik ve" duraksamasında susar, cümle sonunda çalar; işçinin numpy log-mel'i transformers'la aynı.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hihi.py     (~2 dk)
import os, sys, json, time, wave, base64, shutil, tempfile, subprocess, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-hihi-"); PORT = bos_port(8795); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
for f in ("relay.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(K, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(K, d), os.path.join(T, d))
lib = os.path.join(T, "tepki", "alindi"); os.makedirs(lib)
for i in range(3): open(os.path.join(lib, f"hi-hi-{i}.wav"), "w").close()
json.dump({"tepkiler": [{"id": f"alindi-{i}", "tur": "alindi", "metin": "Hı hı.", "tetik": [], "dosya": f"alindi/hi-hi-{i}.wav"} for i in range(3)]}, open(os.path.join(T, "tepki", "tepki.json"), "w"))
def ses(parcalar):  # [(metin, sonra_sessizlik_sn)] → 16 kHz int16
    out = b""
    for m, s in parcalar:
        a, w = os.path.join(T, "q.aiff"), os.path.join(T, "q.wav")
        subprocess.run(["say", "-v", "Yelda", "-o", a, m], check=True); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w], check=True)
        with wave.open(w) as f: out += f.readframes(f.getnframes())
        out += b"\x00\x00" * int(16000 * s)
    return out
def calistir(ayar, env):
    d = os.path.join(T, "canli"); shutil.rmtree(d, ignore_errors=True)
    json.dump(dict({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "tepki_sesleri": os.path.join(T, "tepki")}, **ayar), open(os.path.join(T, "ayar.json"), "w"))
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_TEPKI="1", SUFLOR_TEST_HIHI_KESIN="1", **env))
    for _ in range(50):
        time.sleep(0.2)
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
    time.sleep(0.8); return p, open(os.path.join(d, "kart-anahtari.txt")).read().strip()
def gonder(k, b, toplanti=False):
    h = {"X-Suflor-Anahtar": k, "Origin": f"http://127.0.0.1:{PORT}"}
    post = lambda yol, v: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=h), timeout=10).read()
    if toplanti: post("/ping", {"meeting": {"title": "Deneme"}, "call": True, "panel": True})
    post("/bas-konus", {"komut": "basla"})
    for i in range(0, len(b), 16000): post("/bas-konus", {"komut": "parca", "pcm": base64.b64encode(b[i:i + 16000]).decode()}); time.sleep(0.5)
log = lambda: open(os.path.join(T, "relay.log")).read()
try:
    b = ses([("Geçen hafta ekip toplantısında bütçe konusunu uzun uzun konuştuk.", 0.6), ("Sonra yedekleme konusuna geçtik ve herkes görüş bildirdi.", 0.6),
             ("Özellikle gece yedeklerinin zamanlaması tartışıldı.", 0.6), ("En sonunda cuma gününe kadar bir plan hazırlamaya karar verdik.", 0.6),
             ("Ayrıca yeni bir test ortamı kurulması da gündeme geldi.", 0.6), ("Bu konuda ne yapmamızı önerirsin?", 0.4)])
    print(f"   ses {len(b) / 32000:.1f} sn")
    p, k = calistir({"konus_hihi": True}, {"SUFLOR_TEST_KULAKLIK": "1"}); gonder(k, b); time.sleep(0.5); p.terminate(); p.wait(5)
    bak("tur sonu işçisi yok → yalnız kural", "tur sonu modeli yok" in log())
    ls = [l for l in log().splitlines() if "aktif dinleme" in l]
    for l in ls: print("   " + l[20:])
    sn = [float(l.split("— \"hı hı\" (")[1].split(".")[0]) for l in ls]
    bak(f"uzun anlatımda 'hı hı' çaldı ({len(ls)} kez)", 1 <= len(ls) <= 4)
    bak("ilk 6 sn'de yok, aralar ≥ 12 sn", all(s >= 6 for s in sn) and all(b_ - a_ >= 11 for a_, b_ in zip(sn, sn[1:])))
    bak("kısık ve sırasız (hemen) çalındı", all("(hemen)" in l for l in log().splitlines() if "SES (deneme): tepki" in l) and "SES (deneme): tepki" in log())
    for ad, ayar, env, top in (("ayar kapalı", {}, {"SUFLOR_TEST_KULAKLIK": "1"}, False), ("kulaklık yok", {"konus_hihi": True}, {"SUFLOR_TEST_KULAKLIK": "0"}, False),
                               ("toplantıda", {"konus_hihi": True}, {"SUFLOR_TEST_KULAKLIK": "1"}, True)):
        p, k = calistir(ayar, env); gonder(k, b, top); time.sleep(0.3); p.terminate(); p.wait(5)
        bak(f"{ad} → 'hı hı' yok", "aktif dinleme" not in log())
    bak("günlükte hata yok", "Traceback" not in log())
    # sahte tur sonu işçisi: her duraksamaya 0,10 → hiç çalmaz, her karar günlükte
    open(os.path.join(T, "tur-isci.py"), "w").write('import sys, json\nprint(json.dumps({"hazir": True}), flush=True)\n'
        'for s in sys.stdin: print(json.dumps({"id": json.loads(s)["id"], "p": 0.1, "ms": 1}), flush=True)\n')
    p, k = calistir({"konus_hihi": True}, {"SUFLOR_TEST_KULAKLIK": "1", "SUFLOR_TUR_PY": sys.executable, "SUFLOR_TUR_MODEL": os.path.join(T, "relay.py")})
    gonder(k, b); time.sleep(0.5); p.terminate(); p.wait(5)
    bak("sahte işçi 'cümle ortası' → 'hı hı' yok, kararlar günlükte", "tur sonu modeli hazır" in log() and "\"hı hı\"" not in log() and log().count("tur sonu modeli 0.10 <") >= 2)
    os.remove(os.path.join(T, "tur-isci.py"))
    tpy = "/Users/Shared/Suflor/smart-turn-venv/bin/python"; tmod = sorted(__import__("glob").glob("/Users/Shared/Suflor/ses-modeller/smart-turn/smart-turn-v3*.onnx"))
    if os.path.exists(tpy) and tmod:
        shutil.copy(os.path.join(K, "tur-isci.py"), T)
        b2 = ses([("Geçen hafta ekip toplantısında bütçe konusunu uzun uzun konuştuk.", 0.0), ("Sonra yedekleme konusuna geçtik ve", 0.6),
                  ("herkes görüş bildirdi, özellikle gece yedeklerinin zamanlaması tartışıldı.", 0.6), ("En sonunda cuma gününe kadar plan hazırlamaya karar verdik.", 0.6)])
        p, k = calistir({"konus_hihi": True}, {"SUFLOR_TEST_KULAKLIK": "1"}); gonder(k, b2); time.sleep(0.5); p.terminate(); p.wait(5)
        ls = [l for l in log().splitlines() if "aktif dinleme" in l]
        for l in ls: print("   " + l[20:])
        bak("gerçek model hazır", "tur sonu modeli hazır" in log())
        bak("'…geçtik ve' duraksamasında sustu", bool(ls) and "sustu, tur sonu modeli" in ls[0])
        bak("cümle sonunda çaldı (tur sonu olasılığıyla)", any("\"hı hı\"" in l and "tur sonu 0." in l for l in ls))
        kod = ("import sys, importlib.util, numpy as np\nsp = importlib.util.spec_from_file_location('t', sys.argv[1]); t = importlib.util.module_from_spec(sp); sp.loader.exec_module(t)\n"
               "from transformers import WhisperFeatureExtractor\nfe = WhisperFeatureExtractor(chunk_length=8); r = np.random.RandomState(1)\n"
               "for n in (16000 * 3, 16000 * 11):\n a = (r.randn(n) * 0.1).astype(np.float32); b = np.pad(a[-128000:], (max(0, 128000 - n), 0))\n"
               " f = fe(b, sampling_rate=16000, return_tensors='np', padding='max_length', max_length=128000, truncation=True, do_normalize=True).input_features\n"
               " print(float(np.abs(f - t.ozellik(a)).max()))\n")
        r = subprocess.run([tpy, "-I", "-B", "-c", kod, os.path.join(K, "tur-isci.py")], capture_output=True, text=True)
        if "No module named 'transformers'" in r.stderr: print("   (transformers yok — log-mel karşılaştırması atlandı)")
        else: bak(f"log-mel transformers'la aynı ({r.stdout.split()})", r.returncode == 0 and all(float(x) < 1e-4 for x in r.stdout.split()))
    else: print("   (smart-turn-venv ya da model yok — gerçek model denemesi atlandı)")
finally:
    subprocess.run(["pkill", "-f", f"relay.py --dir {T}"])
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("hı hı: ✓ hepsi geçti" if not hata else f"hı hı: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
