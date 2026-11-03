#!/usr/bin/env python3
# S188 adım 1: whisper.cpp varsayılan motor + geçici MLX yedeği + kurulumda whisper.cpp indirme. Gerçek indirme YOK (yerel sahte sunucu, sahte dosyalar;
# MLX modeli diskteki 8 bit kopyadan). Üç katman:
#  1) İşçi (whisper-isci.py): bozuk/eksik whisper-server ile açılamama sınıfları (coreml, macos_surum, dosya_yok, zaman_asimi), MLX modeli yoksa "mlx_yok",
#     varsa aynı süreçte MLX'e geçiş (hazır satırında motor mlx, yedek, cpp.hata) ve gerçek çözüm.
#  2) Kurulum (kurulum.py whispercpp_kur): sahte Hugging Face + sürüm sayfası — indirme, SHA-256, zip'ten yalnız kodlayıcı (yol kaçışı yok), imzalı sunucu
#     paketi (yayinla.py --whisper-cpp-paket deneme anahtarıyla), olan yeniden inmez, bozuk özet ve başka anahtarla imza reddedilir.
#  3) Aktarıcı (relay.py + aktarici/whisper-hat.py): ayar yokken Apple Silicon'da cpp denenir, açılamayınca günlükte "cpp açılamadı (…) — MLX yedeği",
#     o günün işareti, MLX modeli yokken /status'ta "indiriliyor", inince MLX'le hazır; yeniden açılışta aynı gün cpp denenmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/whisper-yedek.py   (~1 dk; gerçek MLX modeli iki kez yüklenir)
import base64, http.server, io, json, math, os, re, shutil, struct, subprocess, sys, tempfile, threading, time, urllib.request, zipfile
sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__)); KOD = os.path.dirname(BURA); sys.path.insert(0, BURA)
import bosport  # noqa: canlı kullanım koruması (gerçek model)
from bosport import bos_port
ORT = "/Users/Shared/Suflor"; PY = os.path.join(ORT, "whisper-venv", "bin", "python")
Q8 = os.path.join(ORT, "whisper-modeller", "hub", "models--suflor--whisper-large-v3-turbo-q8", "snapshots", "yerel")
GERCEK_SUNUCU = os.path.join(ORT, "whisper-cpp", "whisper-server")
if not os.path.exists(PY): print("whisper-venv kurulu değil — atlandı"); sys.exit(0)
ok = []
def kontrol(ad, kosul, ek=""): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad + ("" if kosul else f"  [{str(ek)[:400]}]"))
T = tempfile.mkdtemp(prefix="suflor-test-wyedek-")
procs = []

def sahte_cpp(ad, betik, kodlayici=True):  # sahte <ortak>/whisper-cpp: betik whisper-server yerine
    d = os.path.join(T, ad); os.makedirs(d)
    open(os.path.join(d, "whisper-server"), "w").write("#!/bin/sh\n" + betik + "\n"); os.chmod(os.path.join(d, "whisper-server"), 0o755)
    open(os.path.join(d, "ggml-large-v3-turbo-q8_0.bin"), "wb").write(b"x" * 100)
    if kodlayici: os.makedirs(os.path.join(d, "ggml-large-v3-turbo-encoder.mlmodelc"))
    return d
def isci(cpp, model, hf=None, ek=None, girdi=None, sn=60):
    env = dict(os.environ, SUFLOR_WHISPER_CPP=cpp, SUFLOR_WHISPER_MODEL=model, HF_HOME=hf or os.path.join(T, "hf-bos"), HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1", **(ek or {}))
    p = subprocess.Popen([PY, "-u", os.path.join(KOD, "whisper-isci.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env); procs.append(p)
    t = time.time(); ilk = json.loads(p.stdout.readline() or "{}"); ilk["_sn"] = round(time.time() - t, 1)
    cevap = None
    if girdi is not None and ilk.get("hazir"):
        p.stdin.write(json.dumps(girdi) + "\n"); p.stdin.flush(); cevap = json.loads(p.stdout.readline() or "{}")
    try: p.stdin.close(); p.wait(10)
    except Exception: p.kill()
    return ilk, cevap
def pcm_say(metin, ses="Yelda"):
    a, w = os.path.join(T, "s.aiff"), os.path.join(T, "s.wav")
    subprocess.run(["say", "-v", ses, "-o", a, metin], check=True); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w], check=True)
    b = open(w, "rb").read(); return b[b.index(b"data") + 8:]

try:
    # ---------- 1) işçi ----------
    os.makedirs(os.path.join(T, "hf-bos"))
    COREML = sahte_cpp("cpp-coreml", "echo \"whisper_init_state: failed to load Core ML model from 'x-encoder.mlmodelc'\" >&2; exit 1")
    j, _ = isci(COREML, "mlx-community/whisper-large-v3-turbo")
    kontrol(f"Core ML hatası + MLX modeli yok → hata, mlx_yok, sınıf coreml ({j['_sn']} sn)", not j.get("hazir") and j.get("mlx_yok") and (j.get("cpp") or {}).get("hata") == "coreml"
            and (j.get("cpp") or {}).get("sonuc") == "yedek", j)
    DYLD = sahte_cpp("cpp-dyld", "echo 'dyld[42]: Symbol not found: _foo (built for macOS 27.0 which is newer than running OS)' >&2; exit 134")
    j, _ = isci(DYLD, "mlx-community/whisper-large-v3-turbo")
    kontrol("ikili bu macOS'ta açılmıyor → sınıf macos_surum", (j.get("cpp") or {}).get("hata") == "macos_surum", j)
    EKSIK = sahte_cpp("cpp-eksik", "exit 0", kodlayici=False)
    j, _ = isci(EKSIK, "mlx-community/whisper-large-v3-turbo")
    kontrol("Core ML kodlayıcısı yok → sınıf dosya_yok", (j.get("cpp") or {}).get("hata") == "dosya_yok", j)
    YAVAS = sahte_cpp("cpp-yavas", "exec sleep 40")
    j, _ = isci(YAVAS, "mlx-community/whisper-large-v3-turbo", ek={"SUFLOR_CPP_ACILIS_SN": "2"})
    time.sleep(0.5); kalan = subprocess.run(["pgrep", "-f", "sleep 40"], capture_output=True, text=True).stdout.split()
    kontrol(f"sunucu açılmıyor → sınıf zaman_asimi ({j['_sn']} sn), sunucu süreci kapatıldı", (j.get("cpp") or {}).get("hata") == "zaman_asimi" and j["_sn"] < 10 and not kalan, [j, kalan])
    if os.path.exists(os.path.join(Q8, "weights.safetensors")):
        TR = pcm_say("Bugünkü toplantıda stok yönetimini konuşacağız.")
        j, c = isci(COREML, Q8, girdi={"id": "a", "pcm": base64.b64encode(TR).decode(), "dil": "tr", "kanal": "karsi", "baslik": "Deneme"})
        kontrol(f"cpp açılamadı → aynı süreçte MLX: hazır, motor mlx, yedek, cpp.hata coreml ({j['_sn']} sn)",
                j.get("hazir") and j.get("motor") == "mlx" and j.get("yedek") is True and (j.get("cpp") or {}).get("hata") == "coreml", j)
        kontrol(f"MLX yedeğiyle Türkçe çözüm: {(c or {}).get('text')!r}", re.search(r"stok", (c or {}).get("text") or "", re.I), c)
    else: print("· 8 bit MLX modeli yok — gerçek yedek çözümü atlandı")
    if os.path.exists(GERCEK_SUNUCU):  # gerçek sunucu, gerçek modeller: yedek yoksa motor cpp, cpp alanı başarılı
        j, _ = isci(os.path.join(ORT, "whisper-cpp"), Q8 if os.path.isdir(Q8) else "mlx-community/whisper-large-v3-turbo", hf=os.path.join(ORT, "whisper-modeller"))
        kontrol(f"sağlam whisper.cpp: motor cpp, cpp.sonuc basarili, açılış {(j.get('cpp') or {}).get('acilis_sn')} sn", j.get("motor") == "cpp" and (j.get("cpp") or {}).get("sonuc") == "basarili"
                and isinstance((j.get("cpp") or {}).get("acilis_sn"), (int, float)) and not j.get("yedek"), j)

    # ---------- 2) kurulum: whisper.cpp indirme ----------
    os.environ["SUFLOR_EV"] = os.path.join(T, "ev"); os.makedirs(os.environ["SUFLOR_EV"])
    sys.path.insert(0, KOD); import kurulum
    ank = os.path.join(T, "anahtar"); ank2 = os.path.join(T, "anahtar2")
    for a in (ank, ank2): subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "suflor-yayin", "-f", a], check=True)
    os.environ["SUFLOR_TEST_IMZA_ACIK"] = open(ank + ".pub").read().split(" suflor")[0].strip()
    rnd = lambda n: (os.urandom(n))
    Q8_B, VAD_B = rnd(300_000), rnd(5_000)
    KOD_DOSYA = {"weights/weight.bin": rnd(200_000), "model.mil": b"mil", "coremldata.bin": b"cd", "metadata.json": b"{}", "analytics/coremldata.bin": b"an"}
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w") as z:
        z.writestr("ggml-large-v3-turbo-encoder.mlmodelc/", b"")
        for k, v in KOD_DOSYA.items(): z.writestr("ggml-large-v3-turbo-encoder.mlmodelc/" + k, v)
        z.writestr("__MACOSX/ggml-large-v3-turbo-encoder.mlmodelc/._model.mil", b"x"); z.writestr("ggml-large-v3-turbo-encoder.mlmodelc/../../kacak.txt", b"x")
    ZIP_B = zb.getvalue()
    import hashlib
    h = lambda b: hashlib.sha256(b).hexdigest()
    kurulum.WCPP_PARCA = [("ggml-large-v3-turbo-q8_0.bin", "ggerganov/whisper.cpp", "r1", "ggml-large-v3-turbo-q8_0.bin", len(Q8_B), h(Q8_B), "dosya"),
                          ("ggml-large-v3-turbo-encoder.mlmodelc", "ggerganov/whisper.cpp", "r1", "ggml-large-v3-turbo-encoder.mlmodelc.zip", len(ZIP_B), h(ZIP_B), "zip"),
                          ("ggml-silero-v6.2.0.bin", "ggml-org/whisper-vad", "r2", "ggml-silero-v6.2.0.bin", len(VAD_B), h(VAD_B), "dosya")]
    kurulum.WCPP_KODLAYICI = {k: len(v) for k, v in KOD_DOSYA.items()}
    # sunucu paketi: yayinla.py'nin paketleyicisiyle (deneme anahtarı; gerçek sunucu yoksa küçük betik + elle aynı biçim)
    pk = os.path.join(T, "paket"); os.makedirs(pk); kay = os.path.join(T, "kaynak"); os.makedirs(kay)
    if os.path.exists(GERCEK_SUNUCU):
        shutil.copy(GERCEK_SUNUCU, kay); open(os.path.join(kay, "SURUM.txt"), "w").write("deneme derlemesi\n")
        r = subprocess.run([sys.executable, os.path.join(KOD, "yayinla.py"), "--whisper-cpp-paket", pk, "--kaynak", kay, "--anahtar", ank, "--minos-gec"], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        kontrol("yayinla.py --whisper-cpp-paket: paket + imzalı liste hazır, gönderilmedi", r.returncode == 0 and "Gönderilmedi" in r.stdout and len(os.listdir(pk)) == 3, r.stdout + r.stderr)
        r2 = subprocess.run([sys.executable, os.path.join(KOD, "yayinla.py"), "--whisper-cpp-paket", os.path.join(T, "paket-x"), "--kaynak", kay, "--anahtar", ank], capture_output=True, text=True,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        mo = re.search(r"minos ([\d.]+)", subprocess.run(["otool", "-l", GERCEK_SUNUCU], capture_output=True, text=True).stdout)
        if mo and tuple(int(x) for x in mo.group(1).split(".")) > (14, 0): kontrol(f"yayinla.py: macOS {mo.group(1)} için derlenmiş ikiliyi paketlemez", r2.returncode != 0 and "yeniden derle" in r2.stdout + r2.stderr, r2.stdout + r2.stderr)
    else:
        import tarfile
        open(os.path.join(kay, "whisper-server"), "w").write("#!/bin/sh\nexit 0\n"); os.chmod(os.path.join(kay, "whisper-server"), 0o755)
        with tarfile.open(os.path.join(pk, kurulum.WCPP_PAKET), "w:gz") as t: t.add(os.path.join(kay, "whisper-server"), "whisper-server")
        open(os.path.join(pk, kurulum.WCPP_PAKET + ".sha256"), "w").write(f"# suflor-whisper-cpp {kurulum.WCPP_SURUM}\n{h(open(os.path.join(pk, kurulum.WCPP_PAKET), 'rb').read())}  {kurulum.WCPP_PAKET}\n")
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", ank, "-n", "suflor-whisper-cpp", os.path.join(pk, kurulum.WCPP_PAKET + ".sha256")], check=True)
    SUNUCU = {}; ISTEK = []
    for ad, depo, rev, uzak, *_ in kurulum.WCPP_PARCA: SUNUCU[f"/{depo}/resolve/{rev}/{uzak}"] = {"ggml-large-v3-turbo-q8_0.bin": Q8_B, "ggml-large-v3-turbo-encoder.mlmodelc": ZIP_B}.get(ad, VAD_B)
    for f in os.listdir(pk): SUNUCU["/rel/" + f] = open(os.path.join(pk, f), "rb").read()
    class Sun(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            ISTEK.append(self.path); b = SUNUCU.get(self.path)
            if b is None: self.send_response(404); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    SP = bos_port(8784); srv = http.server.ThreadingHTTPServer(("127.0.0.1", SP), Sun); threading.Thread(target=srv.serve_forever, daemon=True).start()
    kurulum.WCPP_HF = f"http://127.0.0.1:{SP}"; kurulum.WCPP_REL = f"http://127.0.0.1:{SP}/rel"
    o1 = os.path.join(T, "ortak1"); os.makedirs(o1)
    r = kurulum.whispercpp_kur(o1); d = os.path.join(o1, "whisper-cpp")
    kontrol("kurulum: hepsi indi ve doğrulandı (model, kodlayıcı, VAD, imzalı sunucu)", r is True and kurulum.whispercpp_hazir(o1), [r, kurulum.wcpp_eksik(o1), sorted(os.listdir(d)) if os.path.isdir(d) else None])
    kontrol("kurulum: kodlayıcı zip'ten yalnız kendi klasörü (__MACOSX yok, yol kaçışı yok, geçici dosya yok)",
            not os.path.exists(os.path.join(T, "kacak.txt")) and not os.path.exists(os.path.join(o1, "kacak.txt")) and not any(".indir" in f or ".zip" in f or ".acilis" in f or f.startswith(".sunucu") for f in os.listdir(d))
            and open(os.path.join(d, "ggml-large-v3-turbo-encoder.mlmodelc", "weights", "weight.bin"), "rb").read() == KOD_DOSYA["weights/weight.bin"], os.listdir(d))
    kontrol("kurulum: sihirbaz durumu hazır", kurulum.oku_json(kurulum._wcpp_kayit()).get("durum") == "hazir", kurulum.oku_json(kurulum._wcpp_kayit()))
    n = len(ISTEK); r = kurulum.whispercpp_kur(o1)
    kontrol("kurulum: olan ve doğru olan yeniden inmez (istek yok)", r is True and len(ISTEK) == n, ISTEK[n:])
    os.remove(os.path.join(d, "ggml-large-v3-turbo-q8_0.bin")); iyi = SUNUCU[f"/ggerganov/whisper.cpp/resolve/r1/ggml-large-v3-turbo-q8_0.bin"]
    SUNUCU["/ggerganov/whisper.cpp/resolve/r1/ggml-large-v3-turbo-q8_0.bin"] = iyi[:-1] + bytes([iyi[-1] ^ 1])  # aynı boy, farklı özet
    r = kurulum.whispercpp_kur(o1)
    kontrol("kurulum: SHA-256 tutmayan model yerine konmaz (yarım dosya kalmaz), durum hata, sunucu ve kodlayıcı yerinde",
            r is False and not os.path.exists(os.path.join(d, "ggml-large-v3-turbo-q8_0.bin")) and not any(".indir" in f for f in os.listdir(d)) and kurulum.oku_json(kurulum._wcpp_kayit()).get("durum") == "hata"
            and os.path.exists(os.path.join(d, "whisper-server")), os.listdir(d))
    SUNUCU["/ggerganov/whisper.cpp/resolve/r1/ggml-large-v3-turbo-q8_0.bin"] = iyi
    sig = [k for k in SUNUCU if k.endswith(".sig")][0]; liste = sig[:-4]
    os.remove(os.path.join(pk, os.path.basename(sig)))
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", ank2, "-n", "suflor-whisper-cpp", os.path.join(pk, os.path.basename(liste))], check=True)
    SUNUCU[sig] = open(os.path.join(pk, os.path.basename(sig)), "rb").read()
    o2 = os.path.join(T, "ortak2"); os.makedirs(o2); n = len(ISTEK); r = kurulum.whispercpp_kur(o2)
    kontrol("kurulum: başka anahtarla imzalı sunucu paketi kurulmaz ve modeller hiç istenmez (MLX ile devam)", r is False and not os.path.exists(os.path.join(o2, "whisper-cpp", "whisper-server"))
            and not any("/resolve/" in x for x in ISTEK[n:]) and not os.path.exists(os.path.join(o2, "whisper-cpp", "ggml-large-v3-turbo-q8_0.bin")), [ISTEK[n:], os.listdir(os.path.join(o2, "whisper-cpp"))])
    # sürüm sayfasında paket henüz yok (kod paket yüklenmeden yayınlandı): 404 → 2 GB model indirme isteği hiç yapılmaz, durum "sunucu yok — MLX ile devam"
    yedek_rel = {k: SUNUCU.pop(k) for k in [k for k in SUNUCU if k.startswith("/rel/")]}
    o4 = os.path.join(T, "ortak4"); os.makedirs(o4); n = len(ISTEK); r = kurulum.whispercpp_kur(o4); kd = kurulum.oku_json(kurulum._wcpp_kayit())
    kontrol("kurulum: sürüm sayfası 404 → model/kodlayıcı/VAD isteği yok, durum hata 'sunucu yok — MLX ile devam'",
            r is False and ISTEK[n:] and all(x.startswith("/rel/") for x in ISTEK[n:]) and kd.get("durum") == "hata" and "sunucu yok" in (kd.get("mesaj") or "")
            and os.listdir(os.path.join(o4, "whisper-cpp")) == [], [ISTEK[n:], kd])
    SUNUCU.update(yedek_rel)
    srv.shutdown()

    # ---------- 3) aktarıcı: varsayılan cpp → açılamaz → MLX modeli iner → MLX'le hazır ----------
    if not os.path.exists(os.path.join(Q8, "weights.safetensors")): print("· 8 bit MLX modeli yok — aktarıcı katmanı atlandı")
    else:
        kod = os.path.join(T, "kod"); os.makedirs(kod)
        for f in ("relay.py", "toplanti-claude.py", "baglam.py", "yapi.py", "taahhut.py", "teshis.py", "kullanim.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), kod)
        for dd in ("marka", "pano", "aktarici"): shutil.copytree(os.path.join(KOD, dd), os.path.join(kod, dd))
        o3 = os.path.join(T, "ortak3"); os.makedirs(os.path.join(o3, "whisper-modeller")); os.symlink(os.path.join(ORT, "whisper-venv"), os.path.join(o3, "whisper-venv"))
        shutil.copytree(COREML, os.path.join(o3, "whisper-cpp"))
        uyg = os.path.join(T, "uyg"); canli = os.path.join(uyg, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "proje"))
        PORT = bos_port(8796)
        json.dump({"alan": "Test", "ad": "Deneme Kişi", "port": PORT, "uygulama": uyg, "proje": os.path.join(T, "proje"), "ortak": o3, "yerel_ses": False, "dil": "tr",
                   "teshis_adres": "http://127.0.0.1:9/"}, open(os.path.join(T, "ayar.json"), "w"))  # whisper_motor yok: varsayılan
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_MLX_KAYNAK=Q8, SUFLOR_TEST_MLX_BEKLE="4", SUFLOR_TEST_KOKEN="chrome-extension://deneme")
        env.pop("SUFLOR_EV", None)
        log = os.path.join(T, "relay.log")
        def relay_ac():
            p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=kod, env=env, stdout=open(log, "a"), stderr=subprocess.STDOUT); procs.append(p); return p
        rl = relay_ac()
        def istek(yol, g=None):
            hd = {"Content-Type": "application/json", "Origin": "chrome-extension://deneme"}
            try: hd["X-Suflor-Anahtar"] = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
            except OSError: pass
            r = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=None if g is None else json.dumps(g).encode(), method="GET" if g is None else "POST", headers=hd)
            return json.loads(urllib.request.urlopen(r, timeout=5).read() or b"{}")
        def bekle(kosul, sn):
            son = time.time() + sn
            while time.time() < son:
                try:
                    if kosul(): return True
                except Exception: pass
                time.sleep(0.3)
            return False
        kontrol("deneme aktarıcısı açıldı", bekle(lambda: bool(istek("/status")), 25))
        kontrol("ayar yokken istenen motor cpp (Apple Silicon)", (istek("/status").get("whisper") or {}).get("istenen_motor") == "cpp", istek("/status").get("whisper"))
        ses = {"t": time.time() * 1000}
        def konus():  # 1,2 sn ton + 1 sn sessizlik, 100 ms parçalarla (Whisper işi kuyruğa girer)
            for i in range(22):
                pcm = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 220 * k / 16000)) if i < 12 else 0) for k in range(1600))
                istek("/ses", {"kanal": "ben", "t": ses["t"], "pcm": base64.b64encode(pcm).decode()}); ses["t"] += 100
        gunluk = lambda: open(log, encoding="utf-8", errors="replace").read()
        indiriliyor = []
        def durum_izle():
            w = istek("/status").get("whisper") or {}
            if w.get("durum") == "indiriliyor": indiriliyor.append(w.get("hata"))
            return w
        son = time.time() + 120
        while time.time() < son and (durum_izle().get("durum") != "hazir"):
            konus(); time.sleep(0.5)
        w = durum_izle(); g = gunluk()
        kontrol("günlük: 'WHISPER: cpp açılamadı (coreml: …) — MLX yedeği'", re.search(r"WHISPER: cpp açılamadı \(coreml: .*\) — MLX yedeği", g), g[-1500:])
        kontrol("MLX modeli yokken indirildi; /status'ta 'indiriliyor' göründü", "MLX modeli diskte yok" in g and "WHISPER: MLX modeli indi" in g and indiriliyor, [indiriliyor[:1], [l for l in g.splitlines() if "WHISPER" in l]])
        kontrol("sonra işçi MLX'le hazır; /status'ta cpp sonucu (yedek, coreml)", w.get("durum") == "hazir" and w.get("motor") == "mlx" and (w.get("cpp") or {}).get("hata") == "coreml", w)
        yed = json.load(open(os.path.join(uyg, "whisper-cpp-yedek.json"))) if os.path.exists(os.path.join(uyg, "whisper-cpp-yedek.json")) else {}
        kontrol("o günün işareti yazıldı", yed.get("gun") == time.strftime("%Y-%m-%d") and yed.get("hata") == "coreml", yed)
        ac = [json.loads(l) for l in open(os.path.join(canli, "whisper-cpp-acilis.jsonl"))] if os.path.exists(os.path.join(canli, "whisper-cpp-acilis.jsonl")) else []
        kontrol("açılış kaydı (beta verisi kaynağı): bir kez, yedek/coreml", len(ac) == 1 and ac[0].get("sonuc") == "yedek" and ac[0].get("hata") == "coreml", ac)
        rl.terminate(); rl.wait(10); n0 = gunluk().count("cpp açılamadı")
        rl = relay_ac(); bekle(lambda: bool(istek("/status")), 25)
        son = time.time() + 60
        while time.time() < son and (durum_izle().get("durum") != "hazir"):
            konus(); time.sleep(0.5)
        g = gunluk()
        kontrol("yeniden açılış, aynı gün: cpp denenmez, doğrudan MLX", durum_izle().get("durum") == "hazir" and g.count("cpp açılamadı") == n0 and durum_izle().get("motor") == "mlx", g[-800:])
        rl.terminate(); rl.wait(10)
finally:
    for p in procs:
        try: p.kill()
        except Exception: pass
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} geçti"); sys.exit(0 if ok and all(ok) else 1)
