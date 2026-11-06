#!/usr/bin/env python3
# Tam ses kaydı (aktarici/whisper-hat.py "Tam ses kaydı" bloğu): tam-ben.wav / tam-karsi.wav kesintisiz ve hizalı, boşluk sıfırla dolar, tam.json, başlık doğru uzunluk
# (dosya açıkken de), m4a çevirisi, kapalı/geliştirici değil/gizli/toplantı dışı/ses_arsivi kapalı iken kayıt yok, kuyruk dolunca sessiz bırakma, çağrı yeri ses_al'da,
# ses yolunun yavaşlamaması. Model yüklemez (blok yalıtılmış ad alanında).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-arsivi-tam.py      (kaldı → çıkış 1)
import datetime, json, os, queue, shutil, struct, subprocess, sys, tempfile, threading, time, wave
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-tam-"); BASE = os.path.join(T, "canli"); os.makedirs(BASE)
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
a = src.index("# Tam ses kaydı"); b = src.index("# --- Konuşmacı ses izi")
blok = src[a:b].replace("try: _sa_t = threading.Timer(30", "try: None and threading.Timer(30")
def write(pairs):
    for p, t in pairs:
        with open(p, "a", encoding="utf-8") as f: f.write(t)
AYAR = {"ses_arsivi": True}; AKTIF = [None]; GEL = [True]; GIZLI = [False]; TM = []
ns = dict(os=os, json=json, time=time, datetime=datetime, shutil=shutil, subprocess=subprocess, threading=threading, queue=queue, struct=struct, BASE=BASE, AYAR=AYAR, write=write,
          aktif_dosya=lambda: AKTIF[0], _kapi_mikrofon=lambda: "yerlesik", gelistirici_mi=lambda: GEL[0], gizli_acik=lambda: GIZLI[0], print=lambda *x: None)
exec(compile(blok, "tam-blok", "exec"), ns)
ns["_sa_tmutil"] = lambda y: TM.append(y)
ns["TAM_BOSTA_SN"] = 2  # test: 2 sn sessizlikte kapanır
KOK = os.path.join(BASE, "ses-arsivi")
def pcm(sn, deger=1000): return struct.pack("<h", deger) * int(16000 * sn)
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        try:
            if kosul(): return True
        except (OSError, ValueError): pass  # dosya henüz yok / yazılıyor
        time.sleep(0.05)
    return False
def oku(yol):
    with wave.open(yol) as w: return w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes(), w.readframes(w.getnframes())

# 1) ses_al çağrı yeri ve yeri
kontrol("çağrı yeri ses_al'da, golge_besle'den önce", "    tam_besle(kanal, t_sn, pcm)" in src and src.index("    tam_besle(kanal, t_sn, pcm)") < src.index('    if "golge_besle" in globals(): golge_besle(kanal, t_sn, pcm)')
        and src.index("def ses_al(p):") < src.index("    tam_besle(kanal, t_sn, pcm)") < src.index("def whisper_akiyor"))
kontrol("ayar anahtarları: ses_arsivi, ses_arsivi_tam, gelistirici_mi", all(k in blok for k in ('AYAR.get("ses_arsivi")', '"ses_arsivi_tam"', "gelistirici_mi()")))

# 2) kapalı durumlar: kuyruğa bile girmez, klasör oluşmaz
AKTIF[0] = "2026-11-06-1000-deneme.md"; t0 = time.time() - 30
def hic_yok(ad):
    n = ns["_TAM"]["q"].qsize(); ns["tam_besle"]("ben", t0, pcm(1)); time.sleep(0.3)
    kontrol(ad, ns["_TAM"]["q"].qsize() == n and not os.path.exists(os.path.join(KOK, "2026-11-06-1000-deneme", "tam-ben.wav")))
GEL[0] = False; ns["_TAM"]["gel"] = (0.0, False); hic_yok("geliştirici değil: kayıt yok")
GEL[0] = True; ns["_TAM"]["gel"] = (0.0, False); AYAR["ses_arsivi"] = False; hic_yok("ses_arsivi kapalı: kayıt yok"); AYAR["ses_arsivi"] = True
AYAR["ses_arsivi_tam"] = False; hic_yok("ses_arsivi_tam false: kayıt yok"); del AYAR["ses_arsivi_tam"]
GIZLI[0] = True; hic_yok("gizli toplantı: kayıt yok"); GIZLI[0] = False
AKTIF[0] = None; ns["tam_besle"]("ben", t0, pcm(1)); time.sleep(0.3)
kontrol("toplantı dışı (toplanti-disi-*): kayıt yok", not os.path.isdir(KOK) or not any(d.startswith("toplanti-disi-") and os.listdir(os.path.join(KOK, d)) for d in os.listdir(KOK)))
ns["tam_besle"]("diger", t0, pcm(1)); ns["tam_besle"]("ben", t0, b""); time.sleep(0.2)
AKTIF[0] = "2026-11-06-1000-deneme.md"
kontrol("geçersiz kanal / boş ses: kayıt yok", ns["_TAM"]["q"].qsize() == 0 and not os.path.isdir(os.path.join(KOK, "2026-11-06-1000-deneme")))

# 3) kayıt: ben 1 sn, boşluk 2 sn, ben 1 sn; karsi 0,5 sn, boşluk, karsi 0,5 sn (sonu daha erken biter → sıfırla uzatılır)
AYAR["ses_arsivi_tam_m4a"] = False
T0 = time.time() - 10
ns["tam_besle"]("ben", T0, pcm(1, 1000))
ns["tam_besle"]("karsi", T0 + 0.5, pcm(0.5, 2000))
ns["tam_besle"]("ben", T0 + 3.0, pcm(1, 3000))
ns["tam_besle"]("karsi", T0 + 2.0, pcm(0.5, 4000))
kl = os.path.join(KOK, "2026-11-06-1000-deneme"); wb = os.path.join(kl, "tam-ben.wav"); wk = os.path.join(kl, "tam-karsi.wav")
kontrol("klasör ve iki dosya açıldı", bekle(lambda: os.path.exists(wb) and os.path.exists(wk) and os.path.exists(os.path.join(kl, "tam.json"))))
tj = json.load(open(os.path.join(kl, "tam.json"), encoding="utf-8"))
kontrol("tam.json: t0 (ilk ses), ornek_hizi 16000, kanallar", abs(tj["t0"] - T0) < 0.01 and tj["ornek_hizi"] == 16000 and tj["kanallar"] == ["ben", "karsi"])
kontrol("tmutil kök klasöre bir kez", TM == [KOK])
# dosya açıkken başlık güncellemesi: elle tetikle (10 sn beklemeden) — Empty yolunda da çalışır; burada süreci beklemeden iç durumu yok, o yüzden TAM_BOSTA kapanışını bekle
kontrol("kapanış: 2 sn sessizlikte tam.json'a sn/bitis yazıldı", bekle(lambda: "bitis" in json.load(open(os.path.join(kl, "tam.json"), encoding="utf-8")), 15))
tj = json.load(open(os.path.join(kl, "tam.json"), encoding="utf-8"))
sr, ch, sw, nb, vb = oku(wb); _, _, _, nk, vk = oku(wk)
kontrol(f"WAV 16 kHz mono int16 (okunabilir başlık)", (sr, ch, sw) == (16000, 1, 2))
kontrol(f"iki dosya aynı uzunlukta ({nb} = {nk} örnek) ve 4 sn", nb == nk and abs(nb - 64000) <= 1600)
kontrol("tam.json sn = dosya süresi", abs(tj["sn"] - nb / 16000) < 0.01 and abs(tj["bitis"] - (tj["t0"] + tj["sn"])) < 0.02)
def ort(v, bas_sn, bit_sn):
    s = struct.unpack("<%dh" % ((int(bit_sn * 16000) - int(bas_sn * 16000))), v[int(bas_sn * 16000) * 2:int(bit_sn * 16000) * 2]); return sum(abs(x) for x in s) / max(1, len(s))
kontrol("ben: 0–1 sn ses, 1–3 sn sıfır, 3–4 sn ses (duvar saatine hizalı)", ort(vb, 0.05, 0.95) > 900 and ort(vb, 1.05, 2.95) == 0 and ort(vb, 3.05, 3.95) > 2900)
kontrol("karsi: 0,5–1 sn ses, 0–0,5 sıfır, 1–2 sıfır, 2–2,5 ses, sonu sıfırla uzatıldı", ort(vk, 0.0, 0.45) == 0 and ort(vk, 0.55, 0.95) > 1900 and ort(vk, 1.05, 1.95) == 0 and ort(vk, 2.05, 2.45) > 3900 and ort(vk, 2.55, 3.95) == 0)
kontrol("m4a kapalıyken wav kalır, m4a yok", os.path.exists(wb) and not os.path.exists(os.path.join(kl, "tam-ben.m4a")))

# 4) başlık dosya AÇIKKEN doğru (çökme: kapatmadan oku) + ardışık kayıt + hizalama toleransı (titreşim sıfır eklemez, çakışma kırpılır)
AKTIF[0] = "2026-11-06-1100-ikinci.md"; kl2 = os.path.join(KOK, "2026-11-06-1100-ikinci"); T1 = time.time() - 5
ns["TAM_BOSTA_SN"] = 60
ns["tam_besle"]("ben", T1, pcm(1)); ns["tam_besle"]("ben", T1 + 1.03, pcm(1))  # 30 ms boşluk: tolerans içinde → bitişik
ns["tam_besle"]("ben", T1 + 1.8, pcm(1))  # 200 ms çakışma: tolerans (100 ms) üstünde → 200 ms kırpılır, toplam 2,8 sn
bekle(lambda: os.path.exists(os.path.join(kl2, "tam-ben.wav")) and os.path.getsize(os.path.join(kl2, "tam-ben.wav")) >= 44 + 89600, 5)
time.sleep(0.5)
yol = os.path.join(kl2, "tam-ben.wav"); boy = os.path.getsize(yol)
kontrol(f"çakışma kırpıldı, titreşim eklenmedi ({(boy - 44) / 32000:.2f} sn = 2,8 sn)", abs((boy - 44) / 2 - 44800) <= 2)
# başlığı yenilemek için: yeni klasöre geçiş eski oturumu kapatır
AKTIF[0] = "2026-11-06-1200-ucuncu.md"; kl3 = os.path.join(KOK, "2026-11-06-1200-ucuncu"); ns["tam_besle"]("karsi", time.time() - 2, pcm(0.2))
kontrol("klasör değişince eski oturum kapandı (tam.json bitis, başlık kesin uzunluk)", bekle(lambda: "bitis" in json.load(open(os.path.join(kl2, "tam.json"), encoding="utf-8")), 10))
srb, _, _, n2, _ = oku(os.path.join(kl2, "tam-ben.wav")); _, _, _, n2k, _ = oku(os.path.join(kl2, "tam-karsi.wav"))
kontrol(f"ikinci toplantı iki kanal eşit uzunluk ({n2} = {n2k}); yeni klasörde ayrı tam.json", n2 == n2k and n2 > 40000 and os.path.exists(os.path.join(kl3, "tam.json")))
kontrol("bayt başlığı dosya boyuyla tutarlı", struct.unpack("<I", open(os.path.join(kl2, "tam-ben.wav"), "rb").read(44)[40:44])[0] == os.path.getsize(os.path.join(kl2, "tam-ben.wav")) - 44)

# 5) m4a çevirisi (afconvert) ve wav silme
AYAR["ses_arsivi_tam_m4a"] = True; ns["TAM_BOSTA_SN"] = 2
AKTIF[0] = "2026-11-06-1300-dorduncu.md"; kl4 = os.path.join(KOK, "2026-11-06-1300-dorduncu"); T4 = time.time() - 3
ns["tam_besle"]("ben", T4, pcm(1)); ns["tam_besle"]("karsi", T4, pcm(1))
if shutil.which("afconvert"):
    kontrol("m4a üretildi, wav silindi (iki kanal)", bekle(lambda: all(os.path.exists(os.path.join(kl4, f"tam-{k}.m4a")) and not os.path.exists(os.path.join(kl4, f"tam-{k}.wav")) for k in ("ben", "karsi")), 40))
    kontrol("m4a boş değil", os.path.getsize(os.path.join(kl4, "tam-ben.m4a")) > 500)
else: print("- afconvert yok, m4a atlandı")

# 5b) aynı klasör yeniden açılır: (b) 60 sn sessizlik sonrası kapanıp tekrar ses; (a) iş parçacığı/_TAM sıfırdan (aktarıcı yeniden başlar). Var olan dosya bozulmaz, bölüm numaralanır
AYAR["ses_arsivi_tam_m4a"] = False; ns["TAM_BOSTA_SN"] = 2
AKTIF[0] = "2026-11-06-1600-bolum.md"; kb = os.path.join(KOK, "2026-11-06-1600-bolum"); Tb = time.time() - 20
ns["tam_besle"]("ben", Tb, pcm(1, 1111)); ns["tam_besle"]("karsi", Tb, pcm(1, 2222))
bekle(lambda: "bitis" in json.load(open(os.path.join(kb, "tam.json"), encoding="utf-8")), 10)
ilk = {f: open(os.path.join(kb, f), "rb").read() for f in ("tam-ben.wav", "tam-karsi.wav", "tam.json")}
Tb2 = Tb + 10; ns["tam_besle"]("ben", Tb2, pcm(1, 3333))
bekle(lambda: os.path.exists(os.path.join(kb, "tam-2.json")) and "bitis" in json.load(open(os.path.join(kb, "tam-2.json"), encoding="utf-8")), 10)
kontrol("kapanıp yeniden açılma: ilk bölüm bayt bayt aynı", all(open(os.path.join(kb, f), "rb").read() == v for f, v in ilk.items()))
j2 = json.load(open(os.path.join(kb, "tam-2.json"), encoding="utf-8"))
kontrol("yeni bölüm ayrı: tam-2-ben/karsi.wav, kendi t0'ı", abs(j2["t0"] - Tb2) < 0.01 and os.path.exists(os.path.join(kb, "tam-2-ben.wav")) and os.path.exists(os.path.join(kb, "tam-2-karsi.wav")) and oku(os.path.join(kb, "tam-2-ben.wav"))[3] == oku(os.path.join(kb, "tam-2-karsi.wav"))[3] == 16000)
# (a) _TAM sıfırdan: yeni kuyruk + iş parçacığı (eski iş parçacığı kapatılmış sayılır)
ns["_TAM"]["q"] = queue.Queue(maxsize=4000); ns["_TAM"]["th"] = None
ns["tam_besle"]("ben", Tb + 20, pcm(1, 4444))
bekle(lambda: os.path.exists(os.path.join(kb, "tam-3.json")) and "bitis" in json.load(open(os.path.join(kb, "tam-3.json"), encoding="utf-8")), 10)
kontrol("iş parçacığı yeniden başlayınca tam-3 açıldı; tam ve tam-2 dosyaları bozulmadı", all(open(os.path.join(kb, f), "rb").read() == v for f, v in ilk.items()) and os.path.exists(os.path.join(kb, "tam-3-ben.wav")) and oku(os.path.join(kb, "tam-2-ben.wav"))[3] == 16000)
# m4a yarışı: bölüm 1 m4a'ya çevrilirken bölüm 2 açılsa da yalnız kendi wav'ını çevirir/siler
if shutil.which("afconvert"):
    AYAR["ses_arsivi_tam_m4a"] = True; AKTIF[0] = "2026-11-06-1700-yaris.md"; ky = os.path.join(KOK, "2026-11-06-1700-yaris"); Ty = time.time() - 20
    ns["tam_besle"]("ben", Ty, pcm(1)); bekle(lambda: "bitis" in json.load(open(os.path.join(ky, "tam.json"), encoding="utf-8")), 10); ns["tam_besle"]("ben", Ty + 10, pcm(1, 5555))
    kontrol("m4a: bölüm 1 ve 2 ayrı ayrı çevrildi, birbirinin wav'ını silmedi", bekle(lambda: all(os.path.exists(os.path.join(ky, f"{o}-ben.m4a")) and not os.path.exists(os.path.join(ky, f"{o}-ben.wav")) for o in ("tam", "tam-2")), 40))
AYAR["ses_arsivi_tam_m4a"] = False

# 6) disk/yazma hatası: sessizce bırakır, iş parçacığı ölmez; kuyruk dolunca bırakır
bekle(lambda: "bitis" in json.load(open(os.path.join(kl4, "tam.json"), encoding="utf-8")), 10)
AKTIF[0] = "2026-11-06-1400-disk.md"; ns["_ac_gercek"] = ns["_tam_ac"]
def bozuk(kl, t): raise OSError(28, "No space left on device")
ns["_tam_ac"] = bozuk; ns["tam_besle"]("ben", time.time(), pcm(1)); time.sleep(0.4)
kontrol("disk dolu: istisna sızmadı, iş parçacığı sürüyor", ns["_TAM"]["th"].is_alive())
ns["_tam_ac"] = ns["_ac_gercek"]
nq = ns["_TAM"]["q"]; ns["_TAM"]["q"] = queue.Queue(maxsize=3); ns["_TAM"]["th"] = threading.Thread(target=lambda: time.sleep(5), daemon=True); ns["_TAM"]["th"].start()
t = time.time()
for i in range(20): ns["tam_besle"]("ben", time.time(), pcm(0.1))
kontrol("kuyruk dolunca bloklamadan bırakır (20 çağrı < 0,2 sn)", time.time() - t < 0.2 and ns["_TAM"]["q"].qsize() == 3)
ns["_TAM"]["q"] = nq

# 7) ses yolu maliyeti: kuyruğa koyma çağrısı (gerçek yazma ayrı iş parçacığında)
AKTIF[0] = "2026-11-06-1500-olcum.md"; p10 = pcm(0.5); t = time.perf_counter(); N = 400
for i in range(N): ns["tam_besle"]("ben", time.time() + i * 0.5, p10)
ms = (time.perf_counter() - t) / N * 1000
kontrol(f"tam_besle çağrı başına {ms:.3f} ms (< 1 ms)", ms < 1.0)
bekle(lambda: ns["_TAM"]["q"].empty(), 20); time.sleep(0.5)
shutil.rmtree(T, ignore_errors=True)
print("\n" + ("TÜMÜ GEÇTİ" if not hatalar else f"KALDI: {len(hatalar)}"))
sys.exit(1 if hatalar else 0)
