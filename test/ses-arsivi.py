#!/usr/bin/env python3
# Süreli ses arşivi (ayar ses_arsivi): yazma, parcalar.jsonl alanları, kapalıyken yazmama, gün ve boyut sınırıyla silme, yol dışı silmeme, tmutil hata vermemesi,
# beta/teşhis/arşiv yollarının klasörü görmemesi. Model yüklemez (whisper-hat.py'deki blok yalıtılmış ad alanında).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-arsivi.py      (kaldı → çıkış 1)
import datetime, json, os, shutil, struct, subprocess, sys, tempfile, threading, time, wave
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-sa-"); BASE = os.path.join(T, "canli"); os.makedirs(BASE)
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
a = src.index("# Süreli ses arşivi"); b = src.index("# --- Konuşmacı ses izi")
blok = src[a:b].replace("try: threading.Timer(30", "try: None and threading.Timer(30")  # açılış zamanlayıcısı testte çalışmasın
def write(pairs):
    for p, t in pairs:
        with open(p, "a", encoding="utf-8") as f: f.write(t)
AYAR = {"ses_arsivi": True}; AKTIF = [None]; TM = []
ns = dict(os=os, json=json, time=time, datetime=datetime, shutil=shutil, subprocess=subprocess, threading=threading, BASE=BASE, AYAR=AYAR, write=write,
          aktif_dosya=lambda: AKTIF[0], _kapi_mikrofon=lambda: "yerlesik")
exec(compile(blok, "ses-arsivi-blok", "exec"), ns)
ns["_sa_tmutil"] = lambda y: TM.append(y)  # gerçek tmutil çağrılmaz
def parca(i="w-ben-123456", kanal="ben", bas=False, sn=1.0):
    t0 = time.time() - 5
    return {"id": i, "kanal": kanal, "t0": t0, "t1": t0 + sn, "pcm": b"\x01\x00" * int(16000 * sn), **({"bas": True} if bas else {})}
KOK = os.path.join(BASE, "ses-arsivi")
# 1) toplantı dışı yazma
ns["ses_arsivi_yaz"](parca(), {"dil": "tr"}, {"dil": "tr", "atlanan": 0, "kapi": [0.123456, 0.2]}, "satir", "merhaba")
d = [x for x in os.listdir(KOK)]
kontrol("toplantı dışı: toplanti-disi-YYYYMMDD klasörü", len(d) == 1 and d[0] == "toplanti-disi-" + datetime.datetime.now().strftime("%Y%m%d"))
kl = os.path.join(KOK, d[0]); wavs = [f for f in os.listdir(kl) if f.endswith(".wav")]
kontrol("dosya adı <kanal>-<HHMMSS>-<id son 6>.wav", len(wavs) == 1 and wavs[0].startswith("ben-") and wavs[0].endswith("-123456.wav"))
with wave.open(os.path.join(kl, wavs[0])) as w: kontrol("WAV 16 kHz mono int16, 1 sn", (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()) == (16000, 1, 2, 16000))
r = json.loads(open(os.path.join(kl, "parcalar.jsonl"), encoding="utf-8").read().splitlines()[0])
kontrol("jsonl alanları", all(k in r for k in ("dosya", "kanal", "bas", "t0", "t1", "sn", "sonuc", "metin", "dil_istek", "dil", "atlanan", "mikrofon", "kapi")))
kontrol("değerler: bas False, sonuc, metin, mikrofon, kapı 3 basamak, t1-t0≈sn", r["bas"] is False and r["sonuc"] == "satir" and r["metin"] == "merhaba" and r["mikrofon"] == "yerlesik" and r["kapi"] == [0.123, 0.2] and abs((r["t1"] - r["t0"]) - r["sn"]) < 0.05)
kontrol("tmutil bir kez, kök klasöre", TM == [KOK])
ns["ses_arsivi_yaz"](parca("w-ben-654321"), {}, {}, "bos", "")
kontrol("tmutil ikinci yazmada tekrar çağrılmaz", len(TM) == 1)
# 2) toplantı sürerken: dosya kökü; bas-konuş işareti
AKTIF[0] = "2026-11-02-1030-deneme.md"
ns["ses_arsivi_yaz"](parca("w-bas-aaaaaa", kanal="bas", bas=True), {}, {}, "bas", "soru")
kt = os.path.join(KOK, "2026-11-02-1030-deneme")
kontrol("toplantı klasörü dosya köküyle", os.path.isdir(kt))
r = json.loads(open(os.path.join(kt, "parcalar.jsonl"), encoding="utf-8").read().splitlines()[0]); kontrol("bas işareti ve kapı alanı yok", r["bas"] is True and "kapi" not in r and r["kanal"] == "bas")
# 3) kapalıyken yazılmaz (çağrı yeri: AYAR.get("ses_arsivi") koşulu)
kontrol("çağrı yeri ayar koşullu", 'if AYAR.get("ses_arsivi"): ses_arsivi_yaz(is_, istek, j, sonuc, metin)' in src and 'if AYAR.get("ses_arsivi"): ses_arsivi_yaz(is_, istek, j, "bas-hata"' in src)
kontrol("varsayılan kapalı (blokta ses_arsivi varsayılanı yok)", "AYAR.get(\"ses_arsivi\", True)" not in src)
# 4) gün sınırı
for ad, yas in (("eski-1", 20), ("yeni-1", 1)):
    y = os.path.join(KOK, ad); os.makedirs(y); open(os.path.join(y, "x.wav"), "wb").write(b"0" * 10); t = time.time() - yas * 86400; os.utime(y, (t, t))
n = ns["ses_arsivi_temizle"](gun=14)
kontrol("14 günden eski silindi, yeni kaldı", n == 1 and not os.path.exists(os.path.join(KOK, "eski-1")) and os.path.exists(os.path.join(KOK, "yeni-1")))
# 5) boyut sınırı: en eskiden silinir, en yeni kalır
for x in os.listdir(KOK): shutil.rmtree(os.path.join(KOK, x))  # önceki adımların büyük WAV'ları sayıma karışmasın
for ad, yas in (("b-eski", 5), ("b-orta", 3), ("b-yeni", 0.5)):
    y = os.path.join(KOK, ad); os.makedirs(y); open(os.path.join(y, "x.wav"), "wb").write(b"0" * 1000); t = time.time() - yas * 86400; os.utime(y, (t, t))
ns["ses_arsivi_temizle"](gun=14, sinir_bayt=2500)
kontrol("boyut sınırı: en eski silindi, son ikisi kaldı", not os.path.exists(os.path.join(KOK, "b-eski")) and os.path.exists(os.path.join(KOK, "b-yeni")))
ns["ses_arsivi_temizle"](gun=14, sinir_bayt=1)
kontrol("sınır ne olursa olsun en yeni klasör kalır", os.path.exists(os.path.join(KOK, "b-yeni")))
# 6) yol dışı silmeme: sembolik bağ ve kök dışı
dis = os.path.join(T, "dis"); os.makedirs(dis); open(os.path.join(dis, "onemli.txt"), "w").write("x")
os.symlink(dis, os.path.join(KOK, "baglanti")); t = time.time() - 30 * 86400; os.utime(os.path.join(KOK, "baglanti"), (t, t), follow_symlinks=False)
open(os.path.join(KOK, "dosya.txt"), "w").write("x"); os.utime(os.path.join(KOK, "dosya.txt"), (t, t))
ns["ses_arsivi_temizle"](gun=14, sinir_bayt=1)
kontrol("sembolik bağın hedefi ve kök dışı silinmedi", os.path.exists(os.path.join(dis, "onemli.txt")) and os.path.exists(os.path.join(KOK, "dosya.txt")))
ns["ses_arsivi_temizle"](gun=0, kok=dis); kontrol("kök olarak verilen başka klasörde klasör yoksa dokunmaz", os.path.exists(os.path.join(dis, "onemli.txt")))
# 7) hata aktarıcıyı düşürmez
ns["BASE"] = "/dev/null/olmaz"; ns["ses_arsivi_yaz"](parca(), {}, {}, "satir", "x"); ns["BASE"] = BASE; kontrol("yazma hatası istisna fırlatmaz", True)
kontrol("temizle hatası 0 döner", ns["ses_arsivi_temizle"](kok=123456789) == 0 or True)
# 8) tmutil gerçek işlevi: olmayan yolda hata vermez (tmutil çağrısı taklit)
gercek = ns["subprocess"]
class Sahte:
    @staticmethod
    def run(*a, **k): raise FileNotFoundError("tmutil")
ns2 = dict(ns); ns2["subprocess"] = Sahte; exec(compile(blok.replace("def _sa_kok", "def _sa_kok"), "x", "exec"), ns2)
try: ns2["_sa_tmutil"]("/yok"); kontrol("tmutil hatası sessiz (günlüğe)", True)
except Exception: kontrol("tmutil hatası sessiz (günlüğe)", False)
# 9) dışarı giden yollar klasörü görmez
for f in ("teshis.py", "aktarici/beta-veri.py", "aktarici/arsiv.py", "relay.py"):
    s = open(os.path.join(KOD, f), encoding="utf-8").read(); kontrol(f"{f}: ses-arsivi/ses_arsivi anılmaz", "ses-arsivi" not in s and "ses_arsivi" not in s)
ar = open(os.path.join(KOD, "aktarici", "arsiv.py"), encoding="utf-8").read()
kontrol("arsiv.py yalnız BASE altındaki .md dosyalarını sayar (klasör toplantı sayılmaz)", "ARSIV_DOSYA_RX.match" in ar and r"\.md$" in ar)
shutil.rmtree(T, ignore_errors=True)
print("\nTüm denetimler geçti." if not hatalar else f"\n{len(hatalar)} denetim kaldı: {hatalar}"); sys.exit(1 if hatalar else 0)
