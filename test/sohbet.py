#!/usr/bin/env python3
# Sohbet kipi (v0.49.0, aktarici/sohbet.py) uçtan uca, kota harcamadan: say → 16 kHz PCM → /bas-konus sohbet_parca (0,5 sn'lik parçalar) → tur sonu
# (smart-turn bekleme seçicisi) → yerel Whisper → Brifing.app açık süreç → sahte "claude". Denenen: kulaklıksız açılmaz; cümle sonunda tur kapanır;
# "…geçtik ve" duraksamasında tur sürer (tek soru); cevap okunurken uzun konuşma araya girer, okuma durur, yeni soru gider; "tamam teşekkürler"
# kapatır (Claude'a gitmez); Claude düşünürken söylenen sonraki soru olur (v0.49.2); sessizlikte uyarı + kapanış (test süreleri 12/20 sn); toplantı başlayınca kapanır; sohbette "hı hı" yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sohbet.py     (~3 dk; Brifing.app, swiftc, whisper-venv; smart-turn varsa bekleme seçicisi de)
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request, wave
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT, PORT2 = 8793, 8794
T = tempfile.mkdtemp(prefix="sohbet-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
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
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.split("Soru: ", 1)[-1]
    for parca in ["Sorduğun: ", soru.rstrip(".?!") + ".", " Bu cevabın ikinci cümlesi biraz uzun tutuldu ki okunurken araya girilebilsin.", " Üçüncü cümle de var."]:
        time.sleep(0.1); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    pr({"type": "result", "duration_api_ms": 300, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje,
    "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_hihi": True, "sohbet_ses_izi": True}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
def ses(metin, v="Yelda"):
    a, w = os.path.join(T, "q.aiff"), os.path.join(T, "q.wav")
    subprocess.run(["say", "-v", v, "-o", a, metin], check=True); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w], check=True)
    with wave.open(w) as f: return f.readframes(f.getnframes())
sus = lambda sn: b"\x00\x00" * int(16000 * sn)
def baslat(port, kulak, ayar_yol):
    d = os.path.join(T, f"canli{port}"); os.makedirs(d, exist_ok=True)
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(port)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar_yol, SUFLOR_TEST_BASLAT="1",
                         SUFLOR_TEST_KULAKLIK=kulak, SUFLOR_TEST_SOHBET_KISA="1"), stdout=open(os.path.join(T, f"relay{port}.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); return p, open(os.path.join(d, "kart-anahtari.txt")).read().strip()
def istemci(port, K):
    def post(v, yol="/bas-konus"):
        h = {"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{port}"}
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{yol}", data=json.dumps(v).encode(), headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["konus"]
    return post, st
pler = []
try:
    ay2 = os.path.join(T, "ayar2.json"); json.dump(dict(json.load(open(ay)), port=PORT2), open(ay2, "w"))
    p2, K2 = baslat(PORT2, "0", ay2); pler.append(p2); post2, _ = istemci(PORT2, K2)
    r = post2({"komut": "sohbet_basla"}); ok(f"kulaklık yokken açılmaz ({r.get('err', '')[:40]}…)", not r.get("ok") and "kulaklık" in (r.get("err") or "").lower())
    p2.terminate()
    r_, K = baslat(PORT, "1", ay); pler.append(r_); post, st = istemci(PORT, K)
    log = lambda: open(os.path.join(T, f"relay{PORT}.log")).read()
    # ses izi süzgeci (v0.51.0): kullanıcı profili Yelda'nın sesinden (gerçekte toplantılarda öğrenilir); başka ses (Daniel) soru olmamalı
    ECAPA = "/Users/Shared/Suflor/ses-modeller/spkrec-ecapa-voxceleb/ecapa-mlx.npz"; profil = os.path.exists(ECAPA)
    if profil:
        pw = os.path.join(T, "profil.wav")
        with wave.open(pw, "wb") as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(ses("Merhaba, bugün toplantıda bütçeyi, takvimi ve yedekleme planını konuştuk. Sonra herkes görüşünü söyledi, kararları yarın netleştireceğiz."))
        kod = ("import sys,json,base64,importlib.util,wave,numpy as np,mlx.core as mx\nsp=importlib.util.spec_from_file_location('w',sys.argv[1]);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)\n"
               "e=m.Ecapa(sys.argv[2],np,mx);f=wave.open(sys.argv[3]);a=np.frombuffer(f.readframes(f.getnframes()),np.int16).astype(np.float32)/32768\n"
               "v=np.asarray(e(a),np.float32).reshape(-1);v=v/np.linalg.norm(v);json.dump({'iz':base64.b64encode(v.astype(np.float16).tobytes()).decode(),'sn':30},open(sys.argv[4],'w'))")
        subprocess.run(["/Users/Shared/Suflor/whisper-venv/bin/python", "-I", "-B", "-c", kod, os.path.join(T, "whisper-isci.py"), ECAPA, pw, os.path.join(T, f"canli{PORT}", "ses-izi-ben.json")], check=True)
    def akit(b, hiz=2.0):  # ~0,5 sn'lik parçalar (pano gibi 2 × 4096 örnek: 50 ms pencerelere hizalı değil), gerçek zamanın hiz katı
        son = {}
        for i in range(0, len(b), 16384):
            son = post({"komut": "sohbet_parca", "pcm": base64.b64encode(b[i:i + 16384]).decode()}); time.sleep(0.512 / hiz)
            if son.get("kapali"): break
        return son
    def okuma_bitsin(sn=30):
        t = time.time()
        while time.time() - t < sn and st()["sohbet"].get("okuyor"): akit(sus(0.5))
        akit(sus(1))
    def bekle_hazir(once, sn=40):  # yeni soru cevaplanana kadar sessizlik akıtılır (gerçek mikrofon gibi)
        t = time.time()
        while time.time() - t < sn:
            k = st()
            if k["durum"] in ("hazir", "hata") and k.get("soru") and k.get("soru") != once: return k
            akit(sus(0.5))
        return st()
    ok("açıldı", post({"komut": "sohbet_basla"}).get("ok") and st()["sohbet"]["acik"])
    akit(sus(1.5)); akit(ses("Toplantı en çok kaç dakika sürmeli?") + sus(1.2))
    k = bekle_hazir(None)
    ok(f"cümle sonunda tur kapandı, soru gitti ({k.get('soru')!r})", "dakika" in (k.get("soru") or "") and "Sorduğun" in (k.get("cevap") or ""))
    okuma_bitsin()
    n0 = log().count("SOHBET: tur bitti"); d0 = log().count("SOHBET: duraksama")
    akit(ses("Sonra yedekleme konusuna geçtik ve") + sus(1.0) + ses("herkes görüş bildirdi, sence ne yapmalıyız?") + sus(1.2))
    k = bekle_hazir(k.get("soru"))
    tur_sonu = "tur sonu yok" not in log()
    ok(f"'…ve' duraksamasında tur sürdü, tek soru ({k.get('soru')!r})", log().count("SOHBET: tur bitti") - n0 == 1 and "yedekleme" in (k.get("soru") or "").lower() and "görüş" in (k.get("soru") or "").lower())
    d = log().count("SOHBET: duraksama") - d0
    ok(f"tur sonu modeli duraksama başına bir kez soruldu ({d} satır, iki duraksama)", 1 <= d <= 2)
    okuma_bitsin()
    # araya girme: cevap okunurken (test: metin uzunluğu × 60 ms) 2 sn sonra uzun konuşma
    akit(ses("Bütçe kaç lira?") + sus(1.2)); t = time.time()
    while time.time() - t < 30 and "Sorduğun: Bütçe" not in log(): akit(sus(0.5))
    k0 = st().get("soru"); time.sleep(2.3); akit(ses("Dur, onu boş ver, yarın hava nasıl olacak?") + sus(1.2))
    ok("cevap okunurken uzun konuşma araya girdi", "SOHBET: araya girildi" in log())
    k = bekle_hazir(k0)
    ok(f"araya girilen söz yeni soru oldu ({k.get('soru')!r})", "hava" in (k.get("soru") or "").lower())
    okuma_bitsin()
    # v0.49.2: soru biter bitmez (Claude düşünürken) söylenen atılmaz, sonraki soru olur
    k1 = st().get("soru"); akit(ses("Kaç kişi katılacak?") + sus(1.0) + ses("Bir de yarın saat kaçta başlıyoruz?") + sus(1.2))
    ok("Claude düşünürken konuşma biriktirildi", "Claude düşünürken konuşma — biriktiriliyor" in log())
    k = bekle_hazir(k1); k = bekle_hazir(k.get("soru")) if "kişi" in (k.get("soru") or "") else k
    ok(f"düşünürken söylenen sonraki soru oldu ({k.get('soru')!r})", "yarın" in (k.get("soru") or "").lower() and "kişi" not in (k.get("soru") or "").lower())
    okuma_bitsin()
    # v0.51.3 düşünme sözü: "…nasıl desem" + 2,6 sn duraksama + devamı → tek soru; "şey" + sessizlik → 4 sn sonra olduğu gibi gider
    n1 = log().count("SOHBET: tur bitti")
    akit(ses("Yarın toplantıda bütçeyi, nasıl desem") + sus(2.6) + ses("biraz daha ayrıntılı konuşalım mı?") + sus(1.5))
    k = bekle_hazir(k.get("soru"))
    ok(f"düşünme sözü: dinleme sürdü, iki parça tek soru ({k.get('soru')!r})", "düşünme sözüyle bitti" in log() and "bütçe" in (k.get("soru") or "").lower() and "ayrıntılı" in (k.get("soru") or "").lower())
    okuma_bitsin()
    akit(ses("Peki ama") + sus(1.5)); k2 = bekle_hazir(k.get("soru"))  # "Peki şey" bir koşuda "şeye" yazıldı
    ok(f"düşünme sözünden sonra sessizlik: söz 4 sn sonra olduğu gibi gitti ({k2.get('soru')!r})", "söz olduğu gibi gidiyor" in log() and "peki" in (k2.get("soru") or "").lower())
    okuma_bitsin(); k = k2
    if profil:
        ok("ses izi: kullanıcının (Yelda) sorusu geçti", "SOHBET: ses izi" in log() and "— kullanıcı" in log())
        n1 = log().count("SOHBET: tur bitti"); soru_once = st().get("soru")
        akit(ses("Hey, what's the weather going to be like in London tomorrow?", "Daniel") + sus(2.0)); time.sleep(4); akit(sus(1))
        ok(f"ses izi: başka sesin sorusu Claude'a gitmedi ({st().get('soru')!r})", log().count("SOHBET: tur bitti") > n1 and "kullanıcıya benzemiyor" in log() and st().get("soru") == soru_once)
        ok("ses izi: sohbet dinlemeye devam ediyor", st()["sohbet"]["acik"] and st()["durum"] == "dinliyor")
        ok("ses izi: reddedince sesli söyledi ('Sesini tanıyamadım')", "Sesini tanıyamadım" in log())
    else: ok("(ses izi modeli yok — süzgeç denenmedi)", True)
    nc = log().count("Sorduğun")
    akit(ses("Tamam, teşekkürler.") + sus(1.2)); t = time.time()
    while time.time() - t < 20 and st()["sohbet"]["acik"]: akit(sus(0.5))
    ok("'tamam teşekkürler' kapattı, Claude'a gitmedi", not st()["sohbet"]["acik"] and "kapandı (kullanıcı" in log() and log().count("Sorduğun") == nc)
    ok("kapalıyken parça reddedilir (pano mikrofonu kapatır)", post({"komut": "sohbet_parca", "pcm": base64.b64encode(sus(0.5)).decode()}).get("kapali"))
    post({"komut": "sohbet_basla"}); t = time.time(); r = {}
    while time.time() - t < 30 and not r.get("kapali"): r = akit(sus(0.5), hiz=1.0)
    ok("sessizlikte uyarı ve kapanış", "sn sessizlik — uyarı" in log() and "kapandı (sessizlik" in log() and r.get("kapali"))
    post({"komut": "sohbet_basla"}); akit(sus(1))
    post({"meeting": {"title": "Deneme"}, "call": True, "panel": True}, yol="/ping"); time.sleep(1.5)
    ok("toplantı başlayınca kapandı", "kapandı (toplantı başladı" in log() and not st()["sohbet"]["acik"])
    ok("sohbette 'hı hı' yok (konuşurken de tur sonunda da)", "aktif dinleme" not in log() and "bırakınca \"hı hı\"" not in log())
    ok("smart-turn bekleme seçicisi çalıştı" if tur_sonu else "(smart-turn yok — modelsiz bekleme)", True)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    for p in pler: p.terminate()
    subprocess.run(["pkill", "-f", f"relay.py --dir {T}"])
    if not HATA: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})"); print("\n".join(l for l in open(os.path.join(T, f"relay{PORT}.log")).read().splitlines() if "SOHBET" in l or "KONUŞ" in l)[-3000:])
print("sohbet: ✓ hepsi geçti" if not HATA else f"sohbet: ✗ {len(HATA)} kaldı"); sys.exit(1 if HATA else 0)
