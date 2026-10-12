#!/usr/bin/env python3
# Piper ile yerel Türkçe seslendirme (aktarici/piper-ses.py + piper-isci.py): işçi gerçek ses modeliyle cümle cümle wav üretir, hız ayarı
# süreyi kısaltır, okuma kesilince kalan cümleler çalınmaz ve dosyaları silinir, ayar/dosya yoksa False (çağıran Mac sesine düşer), yalıtılmış
# aktarıcı /status'ta "seslendirme" verir. Ses çalınmaz (SUFLOR_TEST_PIPER_SESSIZ). Yollar kodda değil: ayardaki piper_python / piper_model
# ya da SUFLOR_PIPER_PYTHON / SUFLOR_PIPER_MODEL; ikisi de yoksa test atlanır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/piper.py      (kaldı → çıkış 1)
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time, types, urllib.request
os.environ["SUFLOR_TEST_PIPER_SESSIZ"] = "1"
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try: AY = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
except (OSError, ValueError): AY = {}
PY = os.environ.get("SUFLOR_PIPER_PYTHON") or AY.get("piper_python"); MODEL = os.environ.get("SUFLOR_PIPER_MODEL") or AY.get("piper_model")
if not (PY and MODEL and os.path.exists(PY) and os.path.exists(MODEL)): print("piper: atlandı (Piper ortamı ya da ses modeli yok)"); sys.exit(0)
HATA = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-piper-")
# bölümü relay.py'nin ad alanı yerine küçük bir taklitle çalıştır
AYAR = {"ses_motoru": "piper", "piper_python": PY, "piper_model": MODEL}
ns = {"AYAR": AYAR, "ARAYUZ_DILI": "tr", "A": types.SimpleNamespace(port=8790), "_UYG": KOD, "_APP": T, "deneme_aktarici": lambda: True,
      "_ilk": lambda *y: next((x for x in y if os.path.exists(x)), y[-1]), "os": os, "json": json, "time": time, "threading": threading, "subprocess": subprocess}
exec(compile(open(os.path.join(KOD, "aktarici", "piper-ses.py"), encoding="utf-8").read(), "piper-ses.py", "exec"), ns)
r = None
try:
    t = time.time(); ok = ns["piper_oku"]("Merhaba, toplantı başladı.")
    bak(f"ilk okuma işçiyi açar ve biter ({time.time() - t:.1f} sn)", ok is True and ns["PIPER"]["durum"] == "hazir")
    # işçiyle doğrudan: cümle başına parça, hız süreyi kısaltır
    p = ns["PIPER"]["p"]
    def iste(kim, metin, hiz):
        q = ns["queue"].Queue(); ns["PIPER"]["bekleyen"][kim] = q
        p.stdin.write(json.dumps({"id": kim, "metin": metin, "hiz": hiz}) + "\n"); p.stdin.flush(); parca = []
        while True:
            o = q.get(timeout=20)
            if o.get("bitti") or o.get("hata"): ns["PIPER"]["bekleyen"].pop(kim); return parca, o
            parca.append(o)
    M = "Satışlar yüzde on iki arttı. Toplantı on beş Kasım'da. Sonra konuşalım."
    p1, b1 = iste("t1", M, 1.0); p2, _ = iste("t2", M, 1.3)
    for i in range(2): p1 += iste(f"t1{i}", M, 1.0)[0]; p2 += iste(f"t2{i}", M, 1.3)[0]  # süre her üretimde biraz oynuyor: üç üretimin toplamı
    bak(f"üç cümle → üç parça (×3), ilk parça hızlı (ilk {p1[0].get('ilk') if p1 else '-'} sn)", len(p1) == 9 and (p1[0].get("ilk") or 9) < 1.0)
    s1, s2 = sum(x["sure"] for x in p1), sum(x["sure"] for x in p2)
    bak(f"hız 1,3 süreyi kısaltır ({s1:.2f} → {s2:.2f} sn; beklenen ~%23)", s2 < s1 * 0.9)
    for x in p1 + p2:
        try: os.remove(x["wav"])
        except OSError: pass
    # kesme: ilk parçadan sonra iptal → True döner, kalan wav'lar kalmaz
    say = {"n": 0}
    def iptal(): say["n"] += 1; return say["n"] > 1
    ok = ns["piper_oku"]("Birinci cümle. İkinci cümle. Üçüncü cümle. Dördüncü cümle.", 1.0, iptal=iptal)
    time.sleep(1.5)
    bak("okuma kesilince kalan cümleler çalınmaz, dosyaları silinir", ok is True and not glob.glob(os.path.join(ns["PIPER_GECICI"], "*.wav")))
    AYAR["ses_motoru"] = None; bak("ayar kapalı → False (Mac sesi)", ns["piper_oku"]("Deneme.") is False); AYAR["ses_motoru"] = "piper"
    ns["ARAYUZ_DILI"] = "en"; bak("arayüz İngilizce → False", ns["piper_oku"]("Test.") is False); ns["ARAYUZ_DILI"] = "tr"
    ns["PIPER"]["p"].kill(); time.sleep(0.5); AYAR["piper_model"] = os.path.join(T, "yok.onnx"); ns["PIPER"]["hata"] = None
    bak("ses dosyası yok → False", ns["piper_oku"]("Deneme.") is False and ns["PIPER"]["durum"] == "yok")
    # yalıtılmış aktarıcı: bölüm yükleniyor, /status seslendirme
    for f in ("relay.py", "manifest.json", "piper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
    shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
    canli = os.path.join(T, "canli"); os.makedirs(canli); ay = os.path.join(T, "ayar.json")
    json.dump({"port": 8790, "uygulama": T, "ortak": T, "ses_motoru": "piper", "piper_python": PY, "piper_model": MODEL}, open(ay, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", "8790"], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
    st = {}
    for _ in range(60):
        try:
            k = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
            st = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8790/status", headers={"X-Suflor-Anahtar": k}), timeout=3)); break
        except Exception: time.sleep(0.3)
    bak(f"aktarıcı /status seslendirme ({st.get('seslendirme')})", (st.get("seslendirme") or {}).get("motor") == "piper")
    bak("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log")).read())
finally:
    if r: r.terminate(); r.wait()
    p = ns["PIPER"].get("p")
    if p and p.poll() is None: p.kill()
    shutil.rmtree(T, ignore_errors=True)
print("piper:", "✓ GEÇTİ" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
