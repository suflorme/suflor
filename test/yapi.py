#!/usr/bin/env python3
# Toplantı yapısı (yapi.py, v0.27.0): `yapi` → karar grafı (canli/karar-grafi.sqlite, 0600) + zihin haritası (tek HTML) · aynı toplantı ikinci kez
# yazılınca çoğalmaz · `graf --kim` ilk adla bulur, başka kişiyi getirmez · hazırlıkta "karar grafı" bölümü · haritada "Resim olarak indir" PNG
# üretir (headless Chrome) · ozet-hazir haritayı aktarıcıya verir, panodaki "Zihin haritası" açar (deneme kipi).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yapi.py      (kaldı → çıkış 1; ~20 sn)
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8777
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-yp-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
def tc(*a): return subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", *a],
                                  capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)
Y = {"baslik": "Ayşe — bütçe", "tarih": "2026-10-11", "maddeler": [
    {"baslik": "Bütçe", "durum": "konuşuldu", "ogeler": [{"tur": "karar", "metin": "Bütçe 120 bin", "kim": "Ayşe Yılmaz", "saat": "10:12:30", "alinti": "120'de kalalım"},
                                                         {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Yılmaz"}, {"tur": "yanlis", "metin": "atılmalı"}]},
    {"baslik": "Teklif", "ogeler": [{"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "tarih": "2026-10-17"}, {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Ali K"}]}]}
yj = os.path.join(T, "ozet.yapi.json"); json.dump(Y, open(yj, "w"), ensure_ascii=False)
ozet = os.path.join(T, "ayse-toplanti-ozeti-20261011.md"); open(ozet, "w").write("# Özet\n\n## Değerlendirme — not 4/5\nKarar çıktı.\n")
o = tc("yapi", yj, "--ozet", ozet)
db = os.path.join(canli, "karar-grafi.sqlite"); hy = ozet[:-3] + "-zihin-haritasi.html"
n = lambda: sqlite3.connect(db).execute("SELECT COUNT(*) FROM kayit").fetchone()[0]
bak(f"yapi: 4 kayıt, geçersiz tür atıldı ({o.stdout.strip().splitlines()[0] if o.stdout else o.stderr[-200:]})", os.path.exists(db) and n() == 4)
bak("veritabanı 0600", os.path.exists(db) and not os.stat(db).st_mode & 0o077)
tc("yapi", yj, "--ozet", ozet); bak("aynı toplantı ikinci kez: çoğalmadı", n() == 4)
g = tc("graf", "--kim", "ayşe").stdout
bak("graf --kim ilk adla: Ayşe'nin karar ve iddiası, Bora'nınki yok", "Bütçe 120 bin" in g and "95 bin" in g and "revize" not in g)
bak("graf --kim sahip: Bora'nın açık işi", "Teklifi revize et" in tc("graf", "--kim", "Bora").stdout)
h = tc("hazirlik", "--kim", "Ayşe Yılmaz").stdout
bak("hazırlıkta karar grafı bölümü", "karar grafı" in h and "95 bin" in h)
H = open(hy, encoding="utf-8").read() if os.path.exists(hy) else ""
bak("zihin haritası: tek dosya, dış kaynak yok, veri gömülü", H.startswith("<!doctype html>") and not re.search(r"(src|href)=[\"']https?://", H) and "Bütçe 120 bin" in H)
# PNG: indirme bağlantısının href'i yakalanır
dene = os.path.join(T, "dene.html"); open(dene, "w", encoding="utf-8").write(H.replace("ciz();\n</script>", "ciz();HTMLAnchorElement.prototype.click=function(){document.body.insertAdjacentHTML('beforeend','<pre id=png>'+this.download+'|'+this.href.slice(0,30)+'|'+this.href.length+'</pre>')};setTimeout(()=>document.getElementById('png').click(),300)\n</script>"))
cik = os.path.join(T, "o.html")
pr = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={T}/p", "--no-first-run", "--virtual-time-budget=4000", "--dump-dom", "file://" + dene], stdout=open(cik, "w"), stderr=subprocess.DEVNULL)
m = None
for _ in range(80):
    time.sleep(0.25); m = re.search(r'<pre id="png">(.*?)</pre>', open(cik, encoding="utf-8", errors="replace").read())
    if m: break
pr.kill(); pr.wait(5)
p = (m.group(1).split("|") if m else ["", "", "0"])
bak(f"Resim olarak indir: PNG ({p[0]}, {p[2]} karakter)", p[0].endswith(".png") and p[1].startswith("data:image/png;base64,") and int(p[2]) > 5000)
# aktarıcı: ozet-hazir haritayı kopyalar, pano düğmesi açar
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    o = tc("ozet-hazir", ozet, "--baslik", "Ayşe — bütçe")
    bak("ozet-hazir: zihin haritası gitti", "zihin haritası" in o.stdout)
    st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    son = (st.get("son_toplantilar") or [{}])[0]
    bak("panoda kayıtta harita, kopya aktarıcının klasöründe", son.get("harita", "").startswith(os.path.join(canli, "ozetler")) and os.path.exists(son.get("harita", "")))
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}/son-ac", data=json.dumps({"id": son.get("id"), "tur": "harita"}).encode(),
                               headers={"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{PORT}"})
    a = json.loads(urllib.request.urlopen(q, timeout=10).read()); time.sleep(0.3)
    bak("Zihin haritası düğmesi açar (deneme)", a.get("ok") and "AÇ (deneme): harita" in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally: r.terminate(); r.wait(5)
if not hata: shutil.rmtree(T, ignore_errors=True)
else: print(f"(deneme klasörü: {T})")
print("yapı: ✓ hepsi geçti" if not hata else f"yapı: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
