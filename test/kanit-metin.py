#!/usr/bin/env python3
# v0.36.0 (S48): kanıt görüntüsündeki yazı — metin-tani.swift (Apple Vision, yerel) bu sınamada derlenir; aktarıcı kanıtı kaydedince yazıyı okur ve
# .md'ye "📷 KANIT n metni" satırı yazar (.jsonl'e girmez); aynı ekranın tekrarında "önceki kanıtla aynı yazı"; yazısız görüntüde satır yok.
# kanit / kanit_metin / metin-tani.swift değişince koştur:   PYTHONDONTWRITEBYTECODE=1 python3 test/kanit-metin.py   (~30 sn; ilk tanıma model yükler)
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8793)
T = tempfile.mkdtemp(prefix="kmetin-"); canli = os.path.join(T, "canli"); os.makedirs(canli); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
if not shutil.which("swiftc"): sys.exit("atlandı: swiftc yok")
ikili = os.path.join(T, "Suflor Metin.app", "Contents", "MacOS", "SuflorMetin"); os.makedirs(os.path.dirname(ikili))
subprocess.run(["swiftc", "-O", "-o", ikili, os.path.join(KOD, "metin-tani.swift")], check=True, capture_output=True)
g1, g2 = os.path.join(T, "g1.png"), os.path.join(T, "g2.png")
subprocess.run([ikili, "--deneme-resim", g1, "Çeyrek bütçesi: 1.250.000 TL\nTeslim tarihi 24 Kasım"], check=True)
subprocess.run([ikili, "--deneme-resim", g2, " "], check=True)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "kanit_metin": True}, open(ay, "w"))  # varsayılan kapalı
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K}), timeout=20).read())
    uc("/ingest", {"meeting": {"title": "Ekran toplantısı"}, "source": "transcript", "entries": [{"id": "e/1", "speaker": "Ayla K", "time": "10:00", "text": "Slayta bakalım."}]})
    kanit = lambda g: uc("/kanit-masaustu", {"png": base64.b64encode(open(g, "rb").read()).decode(), "kaynak": "pano"})
    log = lambda: open(os.path.join(T, "relay.log")).read()
    md = lambda: open(os.path.join(canli, next(f for f in os.listdir(canli) if f.endswith(".md")))).read()
    def bekle(f, sn=60):
        t = time.time()
        while time.time() - t < sn:
            if f(): return True
            time.sleep(0.3)
        return False
    ok("kanıt kaydedildi", kanit(g1).get("ok"))
    ok("görüntüdeki yazı .md'de 'KANIT 1 metni' satırı (Türkçe karakter, rakam)", bekle(lambda: "**📷 KANIT 1 metni** | Çeyrek bütçesi: 1.250.000 TL · Teslim tarihi 24 Kasım |" in md()))
    kanit(g1)
    ok("aynı ekranın tekrarı: 'önceki kanıtla aynı yazı'", bekle(lambda: "**📷 KANIT 2 metni** | önceki kanıtla aynı yazı |" in md(), 20))
    kanit(g2)
    ok("yazısız görüntü: metin satırı yok", bekle(lambda: "KANIT 3 METNİ: yazı yok" in log(), 20) and "KANIT 3 metni" not in md())
    jl = open(os.path.join(canli, next(f for f in os.listdir(canli) if f.endswith(".jsonl") and not f.startswith("claude")))).read()
    ok(".jsonl'e metin girmedi (döküm satırı sayılmaz)", "Çeyrek" not in jl and jl.count('"kanit"') == 3)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait()
if not HATA: shutil.rmtree(T, ignore_errors=True)
print("kanıt metni:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun ({T})"); sys.exit(1 if HATA else 0)
