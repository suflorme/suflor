#!/usr/bin/env python3
# Tepki ucu (POST /tepki, 12 Kasım) ve /status "kesisim" özeti: yalnız pano kökeni + anahtar; geçersiz kaynak/değer/kimlik reddedilir;
# tepki.jsonl yalnız zaman, kaynak, id, deger (metin yok); kesisim.json "cozum" özetlenir, yoksa None. Yalıtılmış aktarıcı; gerçek _canli'ye dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tepki.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8772)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-tepki-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
def anh(): return open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
def gonder(govde, pano=True, anahtar=True):
    h = {"Content-Type": "application/json"}
    if anahtar: h["X-Suflor-Anahtar"] = anh()
    if pano: h["Origin"] = f"http://127.0.0.1:{PORT}"
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}/tepki", data=json.dumps(govde).encode(), method="POST", headers=h)
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except urllib.error.HTTPError as e: return {"_kod": e.code}
def durum():
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": anh()})
    return json.loads(urllib.request.urlopen(q, timeout=10).read())
try:
    for _ in range(60):
        if "çalışıyor" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): break
        time.sleep(0.2)
    yol = os.path.join(canli, "tepki.jsonl")
    bak("tepki: geçerli (tazi/iyi) kabul", gonder({"kaynak": "tazi", "id": "firma-20261112.md", "deger": "iyi"}).get("ok") is True)
    bak("tepki: kesisim/yanlis ve eposta/iyi kabul", gonder({"kaynak": "kesisim", "id": "b12", "deger": "yanlis"}).get("ok") and gonder({"kaynak": "eposta", "id": "e1", "deger": "iyi"}).get("ok"))
    bak("tepki: pano kökeni yoksa 403", gonder({"kaynak": "tazi", "id": "x", "deger": "iyi"}, pano=False).get("_kod") == 403)
    bak("tepki: anahtarsız reddedilir", gonder({"kaynak": "tazi", "id": "x", "deger": "iyi"}, anahtar=False).get("_kod") in (401, 403))
    bak("tepki: geçersiz kaynak / değer / boş kimlik / satır sonu", not any(gonder(g).get("ok") for g in (
        {"kaynak": "baska", "id": "x", "deger": "iyi"}, {"kaynak": "tazi", "id": "x", "deger": "belki"}, {"kaynak": "tazi", "id": "", "deger": "iyi"}, {"kaynak": "tazi", "id": "a\nb", "deger": "iyi"})))
    ls = [json.loads(x) for x in open(yol, encoding="utf-8").read().splitlines()] if os.path.isfile(yol) else []
    bak("tepki.jsonl: üç satır, yalnız zaman/kaynak/id/deger", len(ls) == 3 and all(sorted(x) == ["deger", "id", "kaynak", "zaman"] for x in ls) and ls[0]["id"] == "firma-20261112.md")
    bak("/status kesisim: dosya yokken None", durum().get("kesisim") is None)
    json.dump({"bulgular": [], "cozum": {"tarih": "2026-11-12", "duzeltilen": 2, "arastirilan": 3, "birakilan": 1, "oh_kapali": True, "model": "x",
              "cozulemeyen_onemli": [{"id": "b7", "ozet": "Örnek bulgu", "neden": "kanıt yok", "gizli_alan": "gitmez"}]}}, open(os.path.join(canli, "kesisim.json"), "w"))
    k = durum().get("kesisim") or {}
    bak("/status kesisim: sayılar ve önemli çözülemeyenler; fazladan alan taşınmaz", (k.get("duzeltilen"), k.get("arastirilan"), k.get("birakilan")) == (2, 3, 1)
        and k.get("cozulemeyen_onemli") == [{"id": "b7", "ozet": "Örnek bulgu", "neden": "kanıt yok"}] and "model" not in k)
    json.dump({"bulgular": []}, open(os.path.join(canli, "kesisim.json"), "w"))
    bak("/status kesisim: cozum yoksa None", durum().get("kesisim") is None)
    bak("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("tepki: ✓ hepsi geçti" if not hata else f"tepki: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
