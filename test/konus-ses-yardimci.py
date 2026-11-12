#!/usr/bin/env python3
# Konuş ses yardımcısı (konus-ses.swift, Aşama 2 Adım 1) — soket sözleşmesi ../planlar/konus-ses-protokol.md. Gerçek ses aygıtı AÇILMAZ: yardımcı --kuru kipte,
# geçici klasörde koşar (aktarıcıya, canlı yardımcıya ve mikrofona dokunmaz). Denetlenen: soket/anahtar izinleri, yanlış anahtar, anahtarsız bağlantının
# çalışan istemciyi düşürememesi, kabul nabzı ve periyodik nabız, mik_ac/mik_kapat öbekleri, cal_ac/ses/cal_bitir olay sırası (cal_basladi.ts monotonic),
# kes ve yeni cal_ac ile kesilme, kulaklık (SIGUSR1) ve toplantı mikrofonu (SIGUSR2) VPIO kararı, bağlantı kopunca her şeyin kapanması, ikinci kopya, boşta kapanma.
# Gerçek swiftc ile derler (~5 sn). konus-ses.swift değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konus-ses-yardimci.py
import base64, json, os, re, shutil, signal, socket, stat, subprocess, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f"  [{ek}]" if (ek and not k) else ""))
    if not k: HATA.append(ad)

# kaynak denetimi: Silero modeli adresi/özeti kurulum.py ile aktarici/vad.py'de aynı (Adım 3)
src = lambda f: open(os.path.join(KOD, f), encoding="utf-8").read()
kur = src("kurulum.py")
ok("kurulum.py KOPYA listesinde vad-isci.py", '"vad-isci.py"' in kur.split("KOPYA = [", 1)[1].split("]", 1)[0])
if os.path.exists(os.path.join(KOD, "aktarici", "vad.py")):
    vad = src("aktarici/vad.py"); al = lambda s, ad: (re.search(ad + r'\s*=\s*"([^"]+)"', s) or [None, None])[1]
    ok("VAD_URL / VAD_SHA kurulum.py ile aktarici/vad.py'de aynı", al(kur, "VAD_URL") and al(kur, "VAD_URL") == al(vad, "VAD_URL") and al(kur, "VAD_SHA") == al(vad, "VAD_SHA"))
ok("Konuş yardımcısı yalnız geliştiricide kurulur (konus_kur(app, _gelistirici()))", "konus_kur(app, _gelistirici())" in kur)

if not shutil.which("swiftc"): print("swiftc yok — yardımcı denemesi atlandı"); sys.exit(1 if HATA else 0)
T = tempfile.mkdtemp(prefix="ksy-"); IKILI = os.path.join(T, "SuflorKonus"); UYG = os.path.join(T, "u"); os.makedirs(UYG)
SOKET = os.path.join(UYG, "konus-ses.sock"); ANAHTAR = os.path.join(UYG, "ses-anahtari.txt"); GUNLUK = os.path.join(T, "gunluk.txt")
r = subprocess.run(["swiftc", "-O", "-o", IKILI, os.path.join(KOD, "konus-ses.swift")], capture_output=True, text=True)
ok("konus-ses.swift derlendi", r.returncode == 0, r.stderr[-400:])
if r.returncode: shutil.rmtree(T, ignore_errors=True); sys.exit(1)

def baslat(*ek):
    return subprocess.Popen([IKILI, "--uygulama", UYG, "--kuru", "--nabiz-sn", "0.5", "--bosta-sn", "3", *ek], stdout=subprocess.DEVNULL, stderr=open(GUNLUK, "a"))
class Ist:
    def __init__(self):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); self.s.settimeout(0.1); self.s.connect(SOKET); self.t = b""; self.olay = []; self.kapandi = False
    def yaz(self, o): self.s.sendall((json.dumps(o) + "\n").encode())
    def oku(self, sn=0.3):
        son = time.time() + sn
        while time.time() < son and not self.kapandi:
            try: b = self.s.recv(1 << 16)
            except socket.timeout: continue
            except OSError: self.kapandi = True; break
            if not b: self.kapandi = True; break
            self.t += b
            while b"\n" in self.t:
                sat, self.t = self.t.split(b"\n", 1); self.olay.append(json.loads(sat))
    def bekle(self, kosul, sn=3.0):
        son = time.time() + sn
        while time.time() < son:
            x = [o for o in self.olay if kosul(o)]
            if x: return x[0]
            if self.kapandi: return None
            self.oku(0.1)
        return None
    def tur(self, t): return [o for o in self.olay if o.get("t") == t]
    def temizle(self): self.olay = []
    def kapat(self): self.s.close()
def giris(k=None):
    i = Ist(); i.yaz({"t": "anahtar", "k": k if k is not None else open(ANAHTAR).read().strip()}); return i
def es(i):  # sıra noktası: durum iste, cevabına kadarki olayları at (temizle sokette yoldaki eski öbekleri atamaz — yardımcı komutları sırayla işler)
    i.yaz({"t": "durum"}); d = i.bekle(lambda o: o.get("t") == "durum"); i.olay = i.olay[i.olay.index(d) + 1:] if d else []; return d
def pcm(sn, sr=24000): return base64.b64encode(b"\x10\x00" * int(sn * sr)).decode()

p = baslat()
try:
    son = time.time() + 5
    while time.time() < son and not os.path.exists(SOKET): time.sleep(0.05)
    ok("soket açıldı", os.path.exists(SOKET))
    ok("soket izni 0600", stat.S_IMODE(os.stat(SOKET).st_mode) == 0o600, oct(stat.S_IMODE(os.stat(SOKET).st_mode)))
    ok("anahtar dosyası üretildi, 0600, boş değil", os.path.exists(ANAHTAR) and stat.S_IMODE(os.stat(ANAHTAR).st_mode) == 0o600 and len(open(ANAHTAR).read().strip()) >= 32)

    # ikinci kopya aynı sokette çalışmaz
    p2 = baslat()
    try: p2.wait(5); ok("ikinci kopya 'zaten dinliyor' deyip çıkar (çıkış 0)", p2.returncode == 0 and os.path.exists(SOKET))
    except subprocess.TimeoutExpired: p2.kill(); ok("ikinci kopya 'zaten dinliyor' deyip çıkar (çıkış 0)", False)

    # yanlış anahtar / JSON olmayan ilk satır
    y = giris("yanlis"); h = y.bekle(lambda o: o.get("t") == "hata")
    ok("yanlış anahtar → hata{neden: anahtar}", h and h.get("neden") == "anahtar"); y.oku(0.5); ok("yanlış anahtarda bağlantı kapanır", y.kapandi); y.kapat()
    y = Ist(); y.s.sendall(b"merhaba\n"); h = y.bekle(lambda o: o.get("t") == "hata"); y.oku(0.5)
    ok("JSON olmayan ilk satır → hata anahtar + kapanış", h and h.get("neden") == "anahtar" and y.kapandi); y.kapat()

    # doğru anahtar: kabul nabzı
    a = giris(); n = a.bekle(lambda o: o.get("t") == "nabiz", 1.0)
    ok("doğru anahtar → hemen nabız (kabul işareti)", n and n.get("mik") is False and n.get("cal") is False and n.get("vpio") is False and n.get("surum"))
    a.temizle(); a.oku(1.6); ok("nabız periyodik (0,5 sn ayarıyla 1,6 sn'de ≥ 2)", len(a.tur("nabiz")) >= 2, len(a.tur("nabiz")))

    # anahtarsız bağlantı çalışan istemciyi düşüremez
    z = Ist(); time.sleep(0.3); a.temizle(); a.oku(0.8)
    ok("anahtarsız ikinci bağlantı ilk istemciyi düşürmez", not a.kapandi and a.tur("nabiz")); z.kapat()

    # mikrofon
    a.temizle(); a.yaz({"t": "mik_ac", "vpio": True}); m = a.bekle(lambda o: o.get("t") == "mik")
    ok("mik_ac → mik öbekleri", bool(m))
    if m:
        ok("öbek 100 ms @ 16 kHz Int16 (3200 bayt), düzey −120 (sessizlik), vpio true", len(base64.b64decode(m["b64"])) == 3200 and m["duzey"] == -120 and m["vpio"] is True)
        ok("mik.duvar Unix saatinde (time.time ile ±1 sn), ts sayı", abs(m["duvar"] - time.time()) < 1.0 and isinstance(m["ts"], float), m["duvar"] - time.time())
    a.oku(1.0); ok("≈ 10 öbek/sn", 7 <= len(a.tur("mik")) <= 14, len(a.tur("mik")))
    a.temizle(); a.yaz({"t": "durum"}); d = a.bekle(lambda o: o.get("t") == "durum")
    ok("durum → mik true, aygıt bilgisi, hata alanı", d and d["mik"] is True and isinstance(d.get("aygit"), dict) and "hata" in d and d.get("kuru") is True)

    # kulaklık (SIGUSR1): VPIO kapanır; çıkınca geri
    a.temizle(); p.send_signal(signal.SIGUSR1); ad = a.bekle(lambda o: o.get("t") == "aygit_degisti")
    ok("aygıt değişimi → aygit_degisti{kulaklik: true}", ad and ad.get("kulaklik") is True and "cikis" in ad and "giris" in ad)
    es(a); m = a.bekle(lambda o: o.get("t") == "mik"); ok("kulaklıkta mik_ac{vpio:true} olsa da vpio false", m and m["vpio"] is False)
    p.send_signal(signal.SIGUSR1); a.bekle(lambda o: o.get("t") == "aygit_degisti" and o.get("kulaklik") is False); es(a)
    m = a.bekle(lambda o: o.get("t") == "mik"); ok("kulaklık çıkınca VPIO geri (istenen true)", m and m["vpio"] is True)

    # toplantı mikrofonu (SIGUSR2): VPIO kapanır, toplantı sürerken açılmaz
    a.temizle(); p.send_signal(signal.SIGUSR2); tm = a.bekle(lambda o: o.get("t") == "toplanti_mik")
    ok("toplantı uygulaması mikrofonda → toplanti_mik{uygulama, vpio_kapatildi: true}", tm and tm.get("uygulama") == "Teams" and tm.get("vpio_kapatildi") is True)
    a.temizle(); a.yaz({"t": "mik_ac", "vpio": True}); es(a); m = a.bekle(lambda o: o.get("t") == "mik")
    ok("toplantı sürerken mik_ac{vpio:true} → vpio false", m and m["vpio"] is False)
    p.send_signal(signal.SIGUSR2); time.sleep(0.3); es(a); m = a.bekle(lambda o: o.get("t") == "mik")
    ok("toplantı bitince VPIO kendiliğinden açılmaz", m and m["vpio"] is False)
    a.yaz({"t": "mik_ac", "vpio": True}); es(a); m = a.bekle(lambda o: o.get("t") == "mik")
    ok("toplantı bitince yeni mik_ac{vpio:true} → vpio true", m and m["vpio"] is True)
    # sıra noktası: mik_kapat'tan hemen sonra durum — yardımcı komutları sırayla işler, durum cevabından sonra tek bir mik bile hatadır
    # (cevaptan önceki öbekler mik_kapat işlenmeden yazılmış, sokette yoldaydı)
    a.temizle(); a.yaz({"t": "mik_kapat"}); a.yaz({"t": "durum"}); d = a.bekle(lambda o: o.get("t") == "durum"); a.oku(0.8)
    sonra = a.olay[a.olay.index(d) + 1:] if d else []
    ok("mik_kapat işlendikten sonra hiç mik olayı yok", d is not None and not [o for o in sonra if o.get("t") == "mik"], len([o for o in sonra if o.get("t") == "mik"]))
    ok("mik_kapat sonrası durum: mik false, vpio false", d and d["mik"] is False and d["vpio"] is False)
    a.yaz({"t": "mik_ac", "vpio": False}); a.yaz({"t": "mik_ac", "vpio": False}); es(a)
    ok("art arda mik_ac (motor yeniden kurulmadan) öbekler sürer", a.bekle(lambda o: o.get("t") == "mik") is not None)
    a.temizle(); a.yaz({"t": "mik_kapat"}); a.yaz({"t": "durum"}); d = a.bekle(lambda o: o.get("t") == "durum"); a.oku(0.6)
    ok("ikinci mik_kapat'tan sonra da mik olayı yok", d is not None and not [o for o in a.olay[a.olay.index(d) + 1:] if o.get("t") == "mik"])

    # çalma: cal_ac → ses → cal_bitir → cal_basladi → cal_bitti
    a.temizle(); t0 = time.time()
    a.yaz({"t": "cal_ac", "id": "c1", "sr": 24000}); a.yaz({"t": "ses", "id": "c1", "b64": pcm(0.3)}); a.yaz({"t": "cal_bitir", "id": "c1"})
    b = a.bekle(lambda o: o.get("t") == "cal_basladi"); bt = a.bekle(lambda o: o.get("t") == "cal_bitti", 3)
    ok("cal_basladi{id, ts}", b and b.get("id") == "c1" and isinstance(b.get("ts"), float) and "t" in b and b["t"] == "cal_basladi")
    ok("cal_basladi.duvar Unix saatinde, isteğe yakın", b and 0 <= b["duvar"] - t0 < 1.0, b and b["duvar"] - t0)
    ok("cal_bitti{id} cal_basladi'dan sonra", bt and bt.get("id") == "c1" and a.olay.index(b) < a.olay.index(bt))
    ok("cal_bitti verinin süresi kadar sonra (0,3 sn)", bt is not None and time.time() - b["duvar"] >= 0.25)
    ok("kesildi yok", not a.tur("kesildi"))
    a.temizle(); a.yaz({"t": "cal_ac", "id": "bos", "sr": 16000}); a.yaz({"t": "cal_bitir", "id": "bos"})
    bt = a.bekle(lambda o: o.get("t") == "cal_bitti"); ok("verisiz akış: cal_bitti hemen, cal_basladi yok", bt and bt["id"] == "bos" and not a.tur("cal_basladi"))
    # kes
    a.temizle(); a.yaz({"t": "cal_ac", "id": "c2", "sr": 22050}); a.yaz({"t": "ses", "id": "c2", "b64": pcm(2, 22050)})
    a.bekle(lambda o: o.get("t") == "cal_basladi"); a.yaz({"t": "kes"}); k = a.bekle(lambda o: o.get("t") == "kesildi"); a.yaz({"t": "cal_bitir", "id": "c2"}); a.oku(0.5)
    ok("kes → kesildi{id}; sonra cal_bitti gelmez", k and k["id"] == "c2" and not a.tur("cal_bitti"))
    # yeni cal_ac eskisini keser; eski id'nin verisi atılır
    a.temizle(); a.yaz({"t": "cal_ac", "id": "c3", "sr": 24000}); a.yaz({"t": "ses", "id": "c3", "b64": pcm(1)})
    a.yaz({"t": "cal_ac", "id": "c4", "sr": 24000}); k = a.bekle(lambda o: o.get("t") == "kesildi")
    a.yaz({"t": "ses", "id": "c3", "b64": pcm(0.2)}); a.yaz({"t": "ses", "id": "c4", "b64": pcm(0.2)}); a.yaz({"t": "cal_bitir", "id": "c4"})
    bt = a.bekle(lambda o: o.get("t") == "cal_bitti")
    ok("yeni cal_ac → eski akış kesildi{c3}", k and k["id"] == "c3")
    ok("yeni akış biter (cal_bitti c4), eski id'nin verisi hata vermez", bt and bt["id"] == "c4" and not a.tur("hata"))
    # hatalı komutlar
    a.temizle(); a.yaz({"t": "cal_ac", "id": "x"}); h = a.bekle(lambda o: o.get("t") == "hata"); ok("sr'siz cal_ac → hata{neden: komut}", h and h["neden"] == "komut")
    a.temizle(); a.yaz({"t": "bilinmez"}); h = a.bekle(lambda o: o.get("t") == "hata"); ok("bilinmeyen komut → hata{neden: komut}", h and h["neden"] == "komut")
    a.temizle(); a.yaz({"t": "sessiz_dugum", "ac": True}); a.yaz({"t": "durum"}); d = a.bekle(lambda o: o.get("t") == "durum")
    ok("sessiz_dugum{ac:true} kabul edilir", d is not None and not a.tur("hata")); a.yaz({"t": "sessiz_dugum", "ac": False})

    # yeni yetkili bağlantı eskisini kapatır
    a.yaz({"t": "mik_ac", "vpio": False}); a.bekle(lambda o: o.get("t") == "mik")
    b2 = giris(); b2.bekle(lambda o: o.get("t") == "nabiz"); a.oku(0.5)
    ok("anahtarlı ikinci bağlantı eskisini kapatır", a.kapandi); a.kapat()
    b2.temizle(); b2.yaz({"t": "durum"}); d = b2.bekle(lambda o: o.get("t") == "durum")
    ok("eski istemci kapanınca mikrofon kapandı (yeni istemcide mik false)", d and d["mik"] is False)
    # bağlantı kopunca her şey kapanır
    b2.yaz({"t": "mik_ac", "vpio": True}); b2.bekle(lambda o: o.get("t") == "mik"); b2.kapat(); time.sleep(0.3)
    c = giris(); n = c.bekle(lambda o: o.get("t") == "nabiz"); ok("istemci koptu → mikrofon kapandı (kabul nabzında mik false)", n and n["mik"] is False); c.kapat()

    # boşta kapanma (--bosta-sn 3)
    try: p.wait(6); ok("bağlantısız 3 sn sonra kendini kapatır, soket dosyası silinir", p.returncode == 0 and not os.path.exists(SOKET), p.returncode)
    except subprocess.TimeoutExpired: ok("bağlantısız 3 sn sonra kendini kapatır, soket dosyası silinir", False)
    g = open(GUNLUK, encoding="utf-8").read()
    ok("günlükte başlangıç ve kapanış satırı", "başladı v" in g and "kapanıyor" in g)
finally:
    if p.poll() is None: p.kill()
    shutil.rmtree(T, ignore_errors=True)
print("konus-ses-yardimci:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
