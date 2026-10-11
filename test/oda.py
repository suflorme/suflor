#!/usr/bin/env python3
# Aynı mikrofonda ikinci kişi (v0.27.0, ayar oda: true). Birinci bölüm (AST, model gerekmez): profil yokken ≥ 30 sn tutarlı konuşmadan kurulur,
# baştan iki kişi karışıksa kurulmaz; < 1,5 sn parça hep kullanıcı; profile uzak parça "Odadaki kişi"; dosya 0600. İkinci bölüm (whisper-venv ve
# depo dışı gerçek kayıt varsa): yalıtılmış aktarıcıya gerçek işçiyle kullanıcı kanalından kullanıcının kaydı + başka bir ses + yine kullanıcı;
# ortadaki satırlar "Odadaki kişi", kalanı kullanıcı. oda kapalıyken hepsi kullanıcı; ses kilidi: başka sesin (say) "Claude:" komutu
# komut_ses "uymuyor" alır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/oda.py      (kaldı → çıkış 1; gerçek kısım ~2 dk)
import ast, base64, datetime, json, math, os, random, shutil, struct, subprocess, sys, tempfile, time, urllib.error, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(KOD, "..", "_yedek", "test-araclari", "gercek-ses")
hata = []
def bak(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hata.append(ad)
# --- 1. kural (AST) ---
T = tempfile.mkdtemp(prefix="suflor-oda-")
import re
ns = {"re": re, "base64": base64, "struct": struct, "math": math, "os": os, "json": json, "time": time, "datetime": datetime, "BASE": T, "print": lambda *a: None, "ben_adi": lambda: "Ali K"}
agac = ast.parse(open(os.path.join(KOD, "aktarici/whisper-hat.py"), encoding="utf-8").read())
sec = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in {"_iz_coz", "oda_kim", "_oda_yol", "_oda_kaydet"}) or
       (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in {"ODA", "ODA_AD"} or (isinstance(x, ast.Tuple) and any(getattr(e, "id", "").startswith("ODA_") for e in x.elts)) for x in n.targets))]
exec(compile(ast.Module(sec, []), "whisper-hat.py", "exec"), ns)
random.seed(5)
def birim(v): n = math.sqrt(sum(x * x for x in v)); return [x / n for x in v]
TB = {k: birim([random.gauss(0, 1) for _ in range(192)]) for k in "UO"}
def iz(k): return base64.b64encode(struct.pack("<192e", *birim([t + random.gauss(0, 0.03) for t in TB[k]]))).decode()
ok_, ODA = ns["oda_kim"], ns["ODA"]
bak("profil yokken (öğrenirken) hep kullanıcı", all(ok_(iz("O" if i % 2 else "U"), 4.0, "iki sözcük") == "Ali K" for i in range(8)))
bak("baştan iki kişi karışık (yarı yarıya): profil kurulmaz", ODA["profil"] is None)
ODA.update(profil=None, sn=0.0, ogren=[], yuklendi=True)
for _ in range(8): ok_(iz("U"), 4.0, "iki sözcük")
yol = os.path.join(T, "ses-izi-ben.json")
bak("≥ 30 sn tutarlı konuşma: profil kuruldu, dosya 0600", ODA["profil"] is not None and os.path.exists(yol) and not os.stat(yol).st_mode & 0o077)
bak("profile uzak ≥ 1,5 sn parça → Odadaki kişi", ok_(iz("O"), 3.0, "iki sözcük") == "Odadaki kişi")
bak("< 1,5 sn parça hep kullanıcı", ok_(iz("O"), 1.0, "iki sözcük") == "Ali K")
bak("tek sözcük / işaret karar vermez", ok_(iz("O"), 3.0, "!") == "Ali K" and ok_(iz("O"), 3.0, "Evet.") == "Ali K")
bak("kullanıcının parçası kullanıcı", ok_(iz("U"), 3.0, "iki sözcük") == "Ali K")
ODA.update(profil=None, sn=0.0, ogren=[], yuklendi=False)
bak("kayıtlı profil dosyadan yüklenir", ok_(iz("O"), 3.0, "iki sözcük") == "Odadaki kişi")
shutil.rmtree(T, ignore_errors=True)
# --- 2. gerçek işçiyle ---
AY0 = json.load(open(os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
py = next((y for y in (os.path.join(d, "whisper-venv", "bin", "python") for d in (AY0["ortak"], AY0["uygulama"])) if os.path.exists(y)), None)
ec = next((y for y in (os.path.join(d, "ses-modeller", "spkrec-ecapa-voxceleb", "ecapa-mlx.npz") for d in (AY0["ortak"], AY0["uygulama"])) if os.path.exists(y)), None)
KUL, DIG = os.path.join(GS, "kullanici", "tek.wav"), os.path.join(GS, "calisma", "easyturkish208.wav")
def pcm(y, bas, son):
    b = open(y, "rb").read(); i = b.index(b"data") + 8; return b[i + int(bas * 16000) * 2:i + int(son * 16000) * 2]
if not (py and ec and os.path.exists(KUL) and os.path.exists(DIG)):
    print("(whisper-venv, ses izi modeli ya da gerçek kayıt yok — gerçek işçi bölümü atlandı)")
else:
    T = tempfile.mkdtemp(prefix="suflor-oda2-"); canli = os.path.join(T, "canli"); os.makedirs(canli); PORT = 8783
    for f in ("relay.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    # profil: kullanıcının kaydının ilk 60 sn'si (gerçek kullanımda toplantının ilk 30 sn'sinden kendiliğinden kurulur)
    kod = ("import sys, json, base64, numpy as np, mlx.core as mx, importlib.util; s = importlib.util.spec_from_file_location('w', sys.argv[1]); w = importlib.util.module_from_spec(s); s.loader.exec_module(w)\n"
           "b = open(sys.argv[3], 'rb').read(); a = np.frombuffer(b[b.index(b'data') + 8:], np.int16).astype(np.float32)[:16000 * 60] / 32768; z = w.Ecapa(sys.argv[2], np, mx)\n"
           "e = sum(np.array(z(a[i:i + 16000 * 5]), np.float32) for i in range(0, len(a) - 16000 * 5, 16000 * 5)); e /= np.linalg.norm(e)\n"
           "print(json.dumps({'iz': base64.b64encode(e.astype(np.float16).tobytes()).decode(), 'sn': 60}))")
    open(os.path.join(canli, "ses-izi-ben.json"), "w").write(subprocess.run([py, "-c", kod, os.path.join(KOD, "whisper-isci.py"), ec, KUL], capture_output=True, text=True).stdout)
    def calistir(oda):
        ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": AY0["ortak"], "oda": oda}, open(ay, "w"))
        r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, f"relay-{oda}.log"), "w"), stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
        try:
            for _ in range(50):
                if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
                time.sleep(0.2)
            time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); baslik = f"Oda Deneme {oda}"
            def post(yol, v):
                q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K, "Origin": "chrome-extension://" + "a" * 32})
                return json.loads(urllib.request.urlopen(q, timeout=30).read())
            post("/ping", {"call": True, "panel": True, "meeting": {"title": baslik}})
            sira = [("U", pcm(KUL, 62, 80)), ("-", b"\0\0" * 16000 * 2), ("O", pcm(DIG, 40, 58)), ("-", b"\0\0" * 16000 * 2), ("U", pcm(KUL, 95, 113)), ("-", b"\0\0" * 16000 * 3)]
            if not oda: sira += [("K", KOMUT), ("-", b"\0\0" * 16000 * 3)]  # ses kilidi: başka sesin "Claude:" komutu
            t = time.time(); aralik = []
            for kim, p in sira:
                t0 = t
                for i in range(0, len(p), 16000):  # 0,5 sn'lik parçalar, gerçek zamandan ~2 kat hızlı (kuyruk birleştirmesine yol açmadan)
                    post("/ses", {"kanal": "ben", "t": int(t * 1000), "pcm": base64.b64encode(p[i:i + 16000]).decode(), "meeting": {"title": baslik}})
                    t += len(p[i:i + 16000]) / 32000; time.sleep(0.25)
                if kim != "-": aralik.append((kim, t0, t))
            for _ in range(120):
                time.sleep(1)
                st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
                if not (st.get("whisper") or {}).get("kuyruk") and time.time() - t > 15: break
            jl = next((os.path.join(canli, f) for f in os.listdir(canli) if f.endswith(".jsonl") and str(oda) in f), None)
            rs = [json.loads(l) for l in open(jl, encoding="utf-8")] if jl else []
            out = []
            for x in rs:
                if x.get("src") != "whisper" or "t0" not in x: continue
                orta = (x["t0"] + x["t1"]) / 2; gk = next((k for k, a, b in aralik if a - 0.5 <= orta <= b + 0.5), "?")
                out.append((gk, x.get("speaker"), round(x["t1"] - x["t0"], 1), x.get("text", "")[:40], x.get("komut_ses")))
            return out
        finally: r.terminate(); r.wait(5)
    a = os.path.join(T, "komut"); subprocess.run(["say", "-v", "Yelda", "-o", a + ".aiff", "Tamam. Claude, bir kart gönder lütfen, toplantı notlarını da ekle."], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a + ".aiff", a + ".wav"], check=True)
    _b = open(a + ".wav", "rb").read(); KOMUT = _b[_b.index(b"data") + 8:]
    s1 = calistir(True)
    for x in s1: print("   ", x)
    beklenen = lambda gk: "Odadaki kişi" if gk == "O" else "Ali K"
    yanlis = [x for x in s1 if x[2] >= 1.5 and x[1] != beklenen(x[0])]
    bak(f"oda açık: {len(s1)} satır, ≥ 1,5 sn satırlarda doğru kişi (yanlış {len(yanlis)})", s1 and not yanlis and any(x[1] == "Odadaki kişi" for x in s1))
    bak("kullanıcının kendi satırı başkasına yazılmadı", not [x for x in s1 if x[0] == "U" and x[1] != "Ali K"])
    s2 = calistir(False)
    for x in s2: print("   ", x)
    bak(f"oda kapalı: {len(s2)} satırın hepsi kullanıcı", s2 and all(x[1] == "Ali K" for x in s2))
    bak("ses kilidi: başka sesin 'Claude:' komutu işaretlendi (uymuyor)", any(x[0] == "K" and x[4] == "uymuyor" for x in s2))
    bak("ses kilidi: kullanıcının satırlarında işaret yok", not any(x[0] == "U" and x[4] == "uymuyor" for x in s2))
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("oda: ✓ hepsi geçti" if not hata else f"oda: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
