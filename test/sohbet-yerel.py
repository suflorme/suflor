#!/usr/bin/env python3
# Sohbet yerel ses yolunda (Aşama 2 Adım 4, 12 Kasım 2026; aktarici/sohbet.py + yerel-konus.py): gerçek aktarıcı süreci + sahte yardımcı (Unix soket).
# Denenen: yerel_konus false iken bugünkü yol (kulaklıksız açılmaz, soket bağlantısı yok, /status'ta "ky" yok); kulaklıkta mik_ac{vpio:false}; hoparlörde ayar
# yerel_konus_hoparlor false iken açılmaz ("kulaklık" hatası, mik_ac yok), true iken mik_ac{vpio:true}; sohbet yanıtı yerel:true; mik öbekleri sohbet gövdesine
# gider (hata yok); sohbet_kapat → mik_kapat; bas-tut (komut basla) öncesi mik_kapat ve yerel sohbetin kapanması; yardımcı yokken kulaklıkta bugünkü yol (yerel:false).
# Gerçek ses/model yok. Aygıt değişimi (kulaklık takıldı/çıktı) canlıda denenir: SUFLOR_TEST_KULAKLIK süreç başına sabittir.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sohbet-yerel.py
import base64, json, os, shutil, socket, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="sy", dir="/tmp"); ANAHTAR = "b" * 48; proje = os.path.join(T, "proje"); os.makedirs(proje)
open(os.path.join(T, "ses-anahtari.txt"), "w").write(ANAHTAR + "\n")
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write("#!/usr/bin/env python3\nimport sys\nfor l in sys.stdin: pass\n"); os.chmod(sahte, 0o755)
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
class Sunucu:
    def __init__(self, yol):
        self.msj = []; self.c = None; self.baglanti = 0
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); self.s.bind(yol); self.s.listen(2); threading.Thread(target=self.kabul, daemon=True).start()
    def kabul(self):
        while True:
            try: c, _ = self.s.accept()
            except OSError: return
            self.c = c; self.baglanti += 1; threading.Thread(target=self.oku, args=(c,), daemon=True).start()
    def oku(self, c):
        tamp = b""; ilk = True
        while True:
            try: b = c.recv(65536)
            except OSError: return
            if not b: return
            tamp += b
            while b"\n" in tamp:
                sat, tamp = tamp.split(b"\n", 1); o = json.loads(sat)
                if ilk: ilk = False; c.sendall(b'{"t":"nabiz","vpio":false,"mik":false,"cal":false,"surum":"t0"}\n'); continue
                self.msj.append(o)
    def gonder(self, o): self.c.sendall((json.dumps(o) + "\n").encode())
    def tip(self, t): return [o for o in self.msj if o.get("t") == t]
def bekle(kosul, sn=8.0):
    t = time.time()
    while time.time() - t < sn:
        if kosul(): return True
        time.sleep(0.05)
    return bool(kosul())
def baslat(kulak, ayar, sunucu_var):
    port = bos_port(8795); d = os.path.join(T, f"canli{port}"); os.makedirs(d, exist_ok=True); yol = os.path.join(T, f"ayar{port}.json")
    json.dump(dict({"alan": "Deneme", "ad": "Deniz T", "port": port, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "gelistirici": True}, **ayar), open(yol, "w"))
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(port)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1",
                         SUFLOR_TEST_KULAKLIK=kulak, SUFLOR_UYGULAMA=T), stdout=open(os.path.join(T, f"relay{port}.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(80):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(d, "kart-anahtari.txt")).read().strip()
    def post(v):
        h = {"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{port}"}
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/bas-konus", data=json.dumps(v).encode(), headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["konus"]["sohbet"]
    return p, post, st, lambda: open(os.path.join(T, f"relay{port}.log")).read()
pler = []
try:
    # 1. yerel_konus false (varsayılan): bugünkü davranış
    sun = Sunucu(os.path.join(T, "konus-ses.sock"))
    p, post, st, log = baslat("0", {}, True); pler.append(p)
    r = post({"komut": "sohbet_basla"}); ok(f"yerel_konus false + kulaklıksız: açılmaz, bugünkü kulaklık mesajı", not r.get("ok") and "kulaklık" in (r.get("err") or "").lower())
    time.sleep(1.5); ok("yerel_konus false: yardımcıya bağlanılmadı, /status'ta ky yok", sun.baglanti == 0 and "ky" not in st())
    p.terminate(); p.wait(5)
    p, post, st, log = baslat("1", {}, True); pler.append(p)
    r = post({"komut": "sohbet_basla"}); ok(f"yerel_konus false + kulaklıkta: açılır, yerel yok ({r})", r.get("ok") is True and r.get("yerel") is False)
    ok("yerel_konus false: yardımcıya hiç mesaj gitmedi", sun.baglanti == 0 and not sun.msj and st().get("yerel") is False); post({"komut": "sohbet_kapat"}); p.terminate(); p.wait(5)
    # 2. yerel_konus true, kulaklıkta
    p, post, st, log = baslat("1", {"yerel_konus": True}, True); pler.append(p)
    ok("yerel yol bağlandı", bekle(lambda: sun.baglanti >= 1 and "bağlantıyı kabul etti" in log()))
    n0 = len(sun.tip("mik_ac")); r = post({"komut": "sohbet_basla"})
    ok(f"kulaklıkta sohbet yerel açıldı (yerel:true)", r.get("ok") is True and r.get("yerel") is True)
    ok("kulaklıkta mik_ac{vpio:false}", bekle(lambda: len(sun.tip("mik_ac")) > n0) and sun.tip("mik_ac")[-1]["vpio"] is False)
    s = st(); ok("/status sohbet.yerel true ve ky görünür (mik açık, vpio kapalı)", s.get("yerel") is True and s.get("ky", {}).get("mik") is True and s["ky"]["vpio"] is False)
    sil = base64.b64encode(b"\x00\x01" * 1600).decode()
    for i in range(10): sun.gonder({"t": "mik", "b64": sil, "duzey": -50.0, "vpio": False, "ts": 1.0 + i / 10})
    time.sleep(1.2); ok("mik öbekleri işlendi, aktarıcı hatası yok", "Traceback" not in log() and "işlenemedi" not in log())
    sun.gonder({"t": "aygit_degisti", "cikis": "x", "giris": "y", "kulaklik": True}); time.sleep(1.5)
    ok("aygit_degisti: sohbet açık kalır, VPIO kararı aynı (kulaklık) → ek mik_ac yok", st().get("acik") is True and len(sun.tip("mik_ac")) == n0 + 1)
    nk = len(sun.tip("mik_kapat")); post({"komut": "sohbet_kapat"})
    ok("sohbet_kapat → mik_kapat", bekle(lambda: len(sun.tip("mik_kapat")) > nk))
    # bas-tut: açık yerel sohbet + basla → sessiz kapanır, mik kapanır
    post({"komut": "sohbet_basla"}); ok("sohbet yeniden açıldı", bekle(lambda: st().get("acik") is True))
    nk = len(sun.tip("mik_kapat")); r = post({"komut": "basla"})
    ok("bas-tut (basla) öncesi mik_kapat gitti ve yerel sohbet kapandı", bekle(lambda: len(sun.tip("mik_kapat")) > nk) and st().get("acik") is not True)
    post({"komut": "sus"}); p.terminate(); p.wait(5)
    # 3. yerel_konus true, hoparlör: ayar yerel_konus_hoparlor false → açılmaz
    p, post, st, log = baslat("0", {"yerel_konus": True}, True); pler.append(p)
    ok("hoparlör, yerel bağlı", bekle(lambda: "bağlantıyı kabul etti" in log()))
    n0 = len(sun.tip("mik_ac")); r = post({"komut": "sohbet_basla"})
    ok("yerel_konus_hoparlor false: hoparlörde açılmaz, bugünkü kulaklık mesajı, mik_ac gitmedi", not r.get("ok") and "kulaklık" in (r.get("err") or "").lower() and len(sun.tip("mik_ac")) == n0)
    p.terminate(); p.wait(5)
    # 4. yerel_konus_hoparlor true: hoparlörde VPIO açık
    p, post, st, log = baslat("0", {"yerel_konus": True, "yerel_konus_hoparlor": True}, True); pler.append(p)
    ok("hoparlör+ayar, yerel bağlı", bekle(lambda: "bağlantıyı kabul etti" in log()))
    n0 = len(sun.tip("mik_ac")); r = post({"komut": "sohbet_basla"})
    ok("hoparlörde sohbet yerel açıldı", r.get("ok") is True and r.get("yerel") is True)
    ok("hoparlörde mik_ac{vpio:true}", bekle(lambda: len(sun.tip("mik_ac")) > n0) and sun.tip("mik_ac")[-1]["vpio"] is True)
    ok("/status hoparlörde ky.vpio true", st().get("ky", {}).get("vpio") is True)
    post({"komut": "sohbet_kapat"}); p.terminate(); p.wait(5)
    # 5. yardımcı yok (soket kapalı), kulaklıkta: bugünkü yol
    sun.s.close()
    if os.path.exists(os.path.join(T, "konus-ses.sock")): os.remove(os.path.join(T, "konus-ses.sock"))
    p, post, st, log = baslat("1", {"yerel_konus": True}, False); pler.append(p)
    r = post({"komut": "sohbet_basla"}); ok(f"yardımcı yokken kulaklıkta bugünkü yol (yerel:false)", r.get("ok") is True and r.get("yerel") is False)
    p.terminate(); p.wait(5)
finally:
    for p in pler:
        try: p.kill()
        except Exception: pass
    shutil.rmtree(T, ignore_errors=True)
print("\n" + ("TÜMÜ GEÇTİ" if not HATA else f"{len(HATA)} HATA: {HATA}")); sys.exit(1 if HATA else 0)
