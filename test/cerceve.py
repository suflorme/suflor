#!/usr/bin/env python3
# Eklentinin iç çerçeve nabızları (v0.88.2; 19 Ekim 18.13 deneme: altyazı paneli açıkken /status "panel/captions false"): eklenti her çerçevede çalışır,
# paneli/altyazıyı görmeyen iç çerçevenin nabzı (mic: null) üst çerçevenin bilgisini silmemeli. Panel/altyazı herhangi bir çerçevede son 25 sn'de
# görüldüyse açık; çağrı ve toplantı adı yalnız üst çerçeveden. Yalıtılmış aktarıcı (~3 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/cerceve.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-cerceve-"); PORT = bos_port(8794); URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
canli = os.path.join(T, "canli"); os.makedirs(canli)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"),
                     stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KOKEN="http://sahte.test"))
hata = []
def bak(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hata.append(ad)
def istek(yol, govde=None):
    h = {"X-Suflor-Anahtar": open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip(), "Origin": "http://sahte.test"}
    q = urllib.request.Request(URL + yol, data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET", headers=h)
    return json.load(urllib.request.urlopen(q, timeout=5))
def ext(): return istek("/status").get("extension") or {}
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")):
            try: istek("/status"); break
            except (urllib.error.URLError, OSError): pass
        time.sleep(0.1)
    ust = {"meeting": {"title": "Deneme"}, "panel": True, "rows": 4, "captions": True, "call": True, "lang": "tr", "mic": {"on": True, "sessiz": False}}
    ic = {"meeting": {"title": ""}, "panel": False, "rows": 0, "captions": False, "call": False, "mic": None}
    istek("/ping", ust); istek("/ping", ic)
    x = ext(); bak(f"iç çerçeve nabzı paneli, altyazıyı, çağrıyı ve adı silmez ({x.get('panel')}, {x.get('captions')}, {x.get('call')}, {x.get('meeting')!r}, {x.get('rows')})",
                   x.get("panel") is True and x.get("captions") is True and x.get("call") is True and x.get("meeting") == "Deneme" and x.get("rows") == 4)
    istek("/ping", dict(ic, captions=True)); istek("/ping", dict(ust, captions=False))
    bak("altyazıyı yalnız iç çerçeve görse de açık", ext().get("captions") is True)
    istek("/ping", dict(ust, call=False, panel=False, mic={"on": False}))
    x = ext(); bak(f"üst çerçeve toplantıdan çıkınca çağrı biter ({x.get('call')})", x.get("call") is False)
    istek("/ping", {"meeting": {"title": "Deneme"}, "panel": False, "captions": False, "call": False})
    bak("mic alanı olmayan istemci (test, curl) üst çerçeve sayılır", ext().get("call") is False)
    bak("/status'ta iç alanlar yok", not any(k.startswith("_ext_") for k in istek("/status")))
    bak("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"çerçeve: {len(hata)} sorun" if hata else "çerçeve: ✓ GEÇTİ")
sys.exit(1 if hata else 0)
