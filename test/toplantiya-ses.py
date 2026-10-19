#!/usr/bin/env python3
# Toplantıya sesli söyle (v0.38.0, aktarici/toplantiya-ses.py): /komut soyle — ayar kapalıyken ve BlackHole yokken hata; açıkken ilk okumada tanıtım,
# ikincisinde yok; toplantı yokken okunmaz (v0.77.2); cevap yoksa hata; Konuş cevabının yalnız --- öncesi okunur; okurken ikinci basış susturur (gerçek say -a, kulaklık yoksa yerelde okunmaz).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplantiya-ses.py     (~15 sn; BlackHole gerekmez: SUFLOR_TEST_TS_AYGIT)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-ts-"); PORT = bos_port(8796); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(K, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(K, d), os.path.join(T, d))
def calistir(ayar, env):
    json.dump(dict({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T}, **ayar), open(os.path.join(T, "ayar.json"), "w"))
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "a"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"), **env))
    for _ in range(50):
        time.sleep(0.2)
        if os.path.exists(os.path.join(T, "canli", "kart-anahtari.txt")):
            try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1); break
            except Exception: pass
    return p
def soyle(metin=None):
    k = open(os.path.join(T, "canli", "kart-anahtari.txt")).read().strip()
    b = {"tur": "soyle", **({"not": metin} if metin else {})}
    return json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/komut", data=json.dumps(b).encode(), headers={"X-Suflor-Anahtar": k}), timeout=10))["metin"]
def toplantida():  # masaüstü toplantı sinyali (menü uygulamasının yaptığı gibi)
    k = open(os.path.join(T, "canli", "kart-anahtari.txt")).read().strip()
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/masaustu", data=json.dumps({"uygulama": "Deneme", "toplantida": True, "baslik": "Deneme TS"}).encode(), headers={"X-Suflor-Anahtar": k}), timeout=5)
try:
    p = calistir({}, {"SUFLOR_TEST_BASLAT": "1", "SUFLOR_TEST_TS_AYGIT": "1"})
    bak("ayar kapalı → kapalı uyarısı", "kapalı" in soyle("Deneme."))
    p.terminate(); p.wait(5)
    p = calistir({"toplantiya_ses": True}, {"SUFLOR_TEST_BASLAT": "1"} if subprocess.run(["/usr/bin/say", "-a", "?"], capture_output=True, text=True).stdout.find("BlackHole") < 0 else {"SUFLOR_TEST_BASLAT": "1", "SUFLOR_TEST_TS_AYGIT": ""})
    if "BlackHole" not in subprocess.run(["/usr/bin/say", "-a", "?"], capture_output=True, text=True).stdout: bak("BlackHole yok → kurulu değil uyarısı", "kurulu değil" in soyle("Deneme."))
    p.terminate(); p.wait(5)
    p = calistir({"toplantiya_ses": True}, {"SUFLOR_TEST_BASLAT": "1", "SUFLOR_TEST_TS_AYGIT": "1"})
    bak("toplantı yok → okunmaz (v0.77.2)", "Toplantı yok" in soyle("Deneme."))
    toplantida()
    bak("S94: metinsiz basış (Option + Shift + S) = dur; okunan yoksa söyler", "Okunan bir şey yok" in soyle())
    a = soyle("İlk cevap.\n---\nAyrıntı okunmaz."); b = soyle("İkinci cevap.")
    bak(f"ilk okumada tanıtım, --- sonrası yok: {a[:90]!r}", "yapay zekâ asistanı Suflor" in a and "Ali" in a and "Ayrıntı" not in a)
    bak(f"ikinci okumada tanıtım yok: {b!r}", "Suflor" not in b and "İkinci cevap" in b)
    p.terminate(); p.wait(5)
    # gerçek say: hoparlör dışındaki bir çıkış aygıtı varsa (ör. Microsoft Teams Audio) ona okunur, ikinci basış susturur
    ayg = [l.split()[0] for l in subprocess.run(["/usr/bin/say", "-a", "?"], capture_output=True, text=True).stdout.splitlines() if l.strip() and not any(s in l for s in ("Hoparlör", "Speaker", "Kulaklık", "Headphone", "AirPods"))]
    if ayg:
        p = calistir({"toplantiya_ses": True}, {"SUFLOR_TEST_TS_AYGIT": ayg[0]})
        k = open(os.path.join(T, "canli", "kart-anahtari.txt")).read().strip()
        toplantida()
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/ingest", data=json.dumps({"meeting": {"title": "Deneme TS"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Ayla Ö", "time": "10:00", "text": "Bütçe ne durumda?"}]}).encode(), headers={"X-Suflor-Anahtar": k}), timeout=5)
        a = soyle("Bu uzun bir deneme cümlesidir, birkaç saniye sürsün diye biraz daha uzatıyorum ve devam ediyorum."); time.sleep(1); b = soyle("x")
        md = [f for f in os.listdir(os.path.join(T, "canli")) if f.endswith(".md") and "Deneme-TS" in f]
        mt = open(os.path.join(T, "canli", md[0])).read() if md else ""; jt = open(os.path.join(T, "canli", md[0][:-3] + ".jsonl")).read() if md else ""
        bak("dökümde ayrı etiket (SUFLOR (sesli), kullanıcı notu değil), .jsonl'de kaynak: suflor", any("**SUFLOR (sesli)** |" in l and "Bu uzun bir deneme" in l for l in mt.splitlines()) and "NOTU" not in mt and '"kaynak": "suflor"' in jt)
        bak(f"gerçek say (aygıt {ayg[0]}) başladı, ikinci basış susturdu: {b!r}", a.startswith("⌨ 🔊") and "sustu" in b)
        p.terminate(); p.wait(5)
    else: print("(gerçek say denemesi atlandı: hoparlör dışı çıkış aygıtı yok)")
    log = open(os.path.join(T, "relay.log")).read(); bak("günlükte hata yok", "Traceback" not in log)
finally:
    subprocess.run(["pkill", "-f", f"relay.py --dir {T}"])
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("toplantıya söyle: ✓ hepsi geçti" if not hata else f"toplantıya söyle: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
