#!/usr/bin/env python3
# Sesli kanıt isteği (v0.31.6): relay.py'deki SESLI_KANIT_RX / SESLI_KANIT_YOK kalıpları — istek biçimi tetikler, konu içinde geçen sözcük ve
# olumsuz istek tetiklemez (Faz 2'de üç yanlış alarm yüzünden kaldırılmıştı). Kural değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-kanit.py      (kaldı → çıkış 1)
import os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
exec(src[src.index("SESLI_KANIT_RX ="):src.index("SESLI_KANIT = {")])
ORNEK = [("Kanıt al.", 1), ("Ekran görüntüsünü alır mısın?", 1), ("şunun ekran görüntüsü alalım", 1), ("Claude: ekran kaydı başlat", 1),
         ("Can you take a screenshot?", 1), ("ekran resmini çek", 1), ("Bir kanıt alsana şuna", 1),
         ("Ekran görüntüsü almayalım şimdi", 0), ("kanıt almaya gerek yok", 0), ("bu konuda kanıt var mı", 0), ("ekran görüntüsü paylaştım", 0),
         ("ekran kaydı var elimizde", 0), ("kanıtı aldık zaten geçen hafta", 0), ("don't take a screenshot", 0)]
hata = 0
for t, b in ORNEK:
    v = bool(SESLI_KANIT_RX.search(t)) and not SESLI_KANIT_YOK.search(t)
    if v != bool(b): hata += 1; print(f"✗ {t!r}: {v}, beklenen {bool(b)}")
# Gerçek aktarıcı: kullanıcının satırında "Kanıt al." → kanıt isteği açılır ve aktarıcı cevap vermeyi sürdürür (13 Ekim deneme 8: ingest LOCK'u tutarken
# kanıt isteği LOCK'u yeniden aldı, aktarıcı kilitlendi — eklenti sustu, satırlar durdu). SUFLOR_TEST_RELAY ile başka relay.py denenebilir.
import json, shutil, subprocess, tempfile, time, urllib.request
T = tempfile.mkdtemp(prefix="suflor-sk-"); canli = os.path.join(T, "canli"); os.makedirs(canli); PORT = 8768
shutil.copy(os.environ.get("SUFLOR_TEST_RELAY") or os.path.join(KOD, "relay.py"), os.path.join(T, "relay.py")); shutil.copy(os.path.join(KOD, "manifest.json"), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K}), timeout=4).read())
    M = {"title": "Kanıt Deneme"}; post("/ping", {"call": True, "panel": True, "meeting": M})
    try:
        post("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": "w/1", "speaker": "Ali K", "time": "10:00", "text": "Kanıt al."}]})
        st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=4).read())
        ok = bool(st.get("kanit_iste")) and (st["kanit_iste"].get("kaynak") == "sesli")
    except Exception as e: ok = False; print(f"✗ aktarıcı cevap vermedi ({e.__class__.__name__})")
    if not ok: hata += 1
    print(("✓" if ok else "✗") + " gerçek aktarıcı: \"Kanıt al.\" → sesli kanıt isteği, aktarıcı kilitlenmedi")
finally: r.kill(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print(f"sesli kanıt: {len(ORNEK) + 1 - hata}/{len(ORNEK) + 1}" + (" ✓ hepsi geçti" if not hata else ""))
sys.exit(1 if hata else 0)
