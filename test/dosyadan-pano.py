#!/usr/bin/env python3
# Panoya bırakılan ses/video → dosyadan döküm (aktarıcı /dosyadan-karar + /dosyadan): yalıtılmış aktarıcı (kopya klasörde relay.py +
# toplanti-claude.py + whisper-isci.py, kurulumdaki gibi), gerçek Whisper. Denetim: sor (biçim, toplantı, meşgul), anahtar ve köken,
# ham gövdeyle yükleme, blok ilerlemesi, döküm proje/gorusmeler'e, saat dosya tarihinden, geçici kopya silinir, aynı ad → Üzerine yaz /
# Vazgeç, bozuk dosya, korunan proje klasöründe (Masaüstü) canli/dokum. Whisper kurulu değilse atlar (~1 dk).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dosyadan-pano.py      (kaldı → çıkış 1)
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, wave

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GERCEK = json.load(open(os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
ORTAK = os.path.expanduser(GERCEK.get("ortak") or "/Users/Shared/Suflor")
if not os.path.isdir(os.path.join(ORTAK, "whisper-venv")): print("Whisper kurulu değil — atlandı"); sys.exit(0)
T = tempfile.mkdtemp(prefix="suflor-dp-")
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)

# kayıt: iki Türkçe cümle (say), 16 kHz → m4a
def wav(metin, ad):
    subprocess.run(["say", "-v", "Yelda", "-o", ad + ".aiff", metin], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", ad + ".aiff", ad + ".wav"], check=True)
    b = open(ad + ".wav", "rb").read(); return b[b.index(b"data") + 8:]
o = wave.open(os.path.join(T, "k.wav"), "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000)
for k, m in enumerate(["Depo sayımı Cuma günü bitecek, toplam yüz kırk iki palet var.", "Barkod okuyucular için teklif Perşembe gelir."]):
    o.writeframes(wav(m, os.path.join(T, f"p{k}")) + b"\0\0" * 8000)
o.close(); SES = os.path.join(T, "Pano deneme.m4a")
subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", os.path.join(T, "k.wav"), SES], check=True)
sure = os.path.getsize(os.path.join(T, "k.wav")) / 32000
BITIS = datetime.datetime(2026, 10, 10, 14, 0, 0).timestamp() + sure  # dosya tarihi = kaydın sonu → döküm 14:00'te başlar
open(os.path.join(T, "bozuk.m4a"), "w").write("metin")

class Aktarici:
    def __init__(self, port, proje):
        self.url = f"http://127.0.0.1:{port}"; self.canli = os.path.join(T, f"canli{port}"); os.makedirs(self.canli)
        ay = os.path.join(T, f"ayar{port}.json")
        json.dump({"alan": "Deneme", "ad": "Deniz T", "port": port, "uygulama": T, "proje": proje, "ortak": ORTAK, "bildirim": False}, open(ay, "w"))
        self.p = subprocess.Popen([sys.executable, "relay.py", "--dir", self.canli, "--port", str(port)], cwd=T, stdout=open(os.path.join(T, f"relay{port}.log"), "w"),
                                  stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
        for _ in range(80):
            if os.path.exists(os.path.join(self.canli, "kart-anahtari.txt")):
                try: self.durum(); break
                except Exception: pass
            time.sleep(0.1)
    def anahtar(self): return open(os.path.join(self.canli, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    def istek(self, yol, govde=None, koken="pano", anh=True, ham=None, ad=None, tarih=None):
        h = {"Origin": self.url} if koken == "pano" else ({"Origin": koken} if koken else {})
        if anh: h["X-Suflor-Anahtar"] = self.anahtar()
        if ad: h.update({"X-Suflor-Ad": urllib.parse.quote(ad), "X-Suflor-Tarih": str(int((tarih or time.time()) * 1000))})
        veri = ham if ham is not None else (json.dumps(govde).encode() if govde is not None else None)
        q = urllib.request.Request(self.url + yol, data=veri, method="POST" if veri is not None else "GET", headers=h)
        try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    def karar(self, islem, **k): return self.istek("/dosyadan-karar", dict(k, islem=islem))
    def yukle(self, yol, ad=None, **k): return self.istek("/dosyadan", ham=open(yol, "rb").read(), ad=ad or os.path.basename(yol), tarih=k.pop("tarih", BITIS), **k)
    def durum(self): return self.istek("/status", koken=None).get("dosyadan")
    def bekle(self, *son, sn=240):
        gorulen = set(); t = time.time()
        while time.time() - t < sn:
            d = self.durum() or {}
            if d.get("toplam"): gorulen.add(d["blok"])
            if d.get("durum") in son: return d, gorulen
            time.sleep(0.3)
        return self.durum() or {}, gorulen
    def kapat(self): self.p.terminate(); self.p.wait(5)

A = Aktarici(8791, os.path.join(T, "proje")); os.makedirs(os.path.join(T, "proje", "gorusmeler"))
try:
    kontrol("sor: ses/video olmayan dosya reddedilir", "ses/video değil" in (A.karar("sor", ad="rapor.pdf", boyut=10).get("err") or ""))
    kontrol("sor: m4a kabul", A.karar("sor", ad="Pano deneme.m4a", boyut=os.path.getsize(SES)).get("ok") is True)
    kontrol("anahtarsız yükleme 401", A.yukle(SES, anh=False).get("kod") == 401)
    kontrol("pano dışı kökenden yükleme 403", A.yukle(SES, koken="https://kotu.example").get("kod") == 403)
    t0 = time.time(); r = A.yukle(SES)
    kontrol("ham gövdeyle yüklendi, döküm başladı", r.get("ok") is True and (A.durum() or {}).get("durum") in ("calisiyor", "bitti"))
    kontrol("iş sürerken ikinci dosya reddedilir", "sürüyor" in (A.karar("sor", ad="x.m4a", boyut=10).get("err") or ""))
    d, bl = A.bekle("bitti", "hata"); sn = time.time() - t0
    md = d.get("md") or ""
    kontrol(f"döküm hazır ({sn:.0f} sn), blok ilerlemesi görüldü {sorted(bl)}", d.get("durum") == "bitti" and bl and os.path.isfile(md))
    kontrol("döküm proje/gorusmeler'de (.md + .vtt), yer gösterildi", os.path.realpath(os.path.dirname(md or "-")) == os.path.realpath(os.path.join(T, "proje", "gorusmeler")) and os.path.isfile(md[:-3] + ".vtt") and "gorusmeler" in (d.get("yer") or ""))
    L = [l for l in open(md, encoding="utf-8") if l.startswith("**[")] if os.path.isfile(md) else []
    kontrol("saat dosya tarihinden (ilk satır ~14:00; AAC dolgusu ±2 sn), metin doğru", L[:1] and L[0][3:11] in ("13:59:58", "13:59:59", "14:00:00", "14:00:01") and any("perşembe" in l.lower() for l in L))
    kontrol("geçici kopya silindi", not os.listdir(os.path.join(A.canli, "dosyadan")))
    kontrol("Dökümü aç", A.karar("ac").get("ok") is True)
    kontrol("Kapat → bölüm gizlenir", A.karar("kapat").get("ok") and A.durum() is None)
    A.yukle(SES); d, _ = A.bekle("var", "bitti", "hata", sn=60)
    kontrol("aynı ad → 'var' (Whisper'dan önce), dosya bekliyor", d.get("durum") == "var" and d.get("var", "").endswith(".md") and os.listdir(os.path.join(A.canli, "dosyadan")))
    ilk = os.path.getmtime(md); A.karar("uzerine"); d, _ = A.bekle("bitti", "hata")
    kontrol("Üzerine yaz → yeniden yazıldı", d.get("durum") == "bitti" and os.path.getmtime(md) > ilk)
    A.karar("kapat"); A.yukle(SES); A.bekle("var", sn=60)
    kontrol("Vazgeç → iş ve geçici kopya silinir", A.karar("vazgec").get("ok") and A.durum() is None and not os.listdir(os.path.join(A.canli, "dosyadan")))
    A.yukle(os.path.join(T, "bozuk.m4a")); d, _ = A.bekle("hata", "bitti", sn=60)
    kontrol("bozuk dosya: hata panoda", d.get("durum") == "hata" and "ses çıkarılamadı" in (d.get("hata") or ""))
    A.karar("kapat"); A.istek("/ping", {"call": True, "meeting": {"title": "Deneme"}}, koken=None)
    kontrol("toplantı sürerken başlamaz (sor ve yükleme)", "toplantı sürüyor" in (A.karar("sor", ad="a.m4a", boyut=10).get("err") or "") and A.yukle(SES).get("ok") is False)
finally: A.kapat()

# proje Masaüstü'nde: launchd oraya yazamaz → canli/dokum (klasöre dokunulmaz; olmayan yol)
B = Aktarici(8792, os.path.expanduser("~/Desktop/suflor-deneme-yok"))
try:
    B.yukle(SES); d, _ = B.bekle("bitti", "hata")
    kontrol("Masaüstündeki proje → canli/dokum, panoda 'canli/dokum'", d.get("durum") == "bitti" and os.path.realpath(os.path.dirname(d.get("md") or "-")) == os.path.realpath(os.path.join(B.canli, "dokum")) and d.get("yer") == "canli/dokum")
    kontrol("Masaüstü'nde klasör açılmadı", not os.path.exists(os.path.expanduser("~/Desktop/suflor-deneme-yok")))
finally: B.kapat()
shutil.rmtree(T, ignore_errors=True)
print(f"dosyadan-pano: {'✓ hepsi geçti' if not hatalar else '✗ ' + str(len(hatalar)) + ' kaldı'}"); sys.exit(1 if hatalar else 0)
