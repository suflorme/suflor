#!/usr/bin/env python3
# Konuş Aşama 2 Adım 5 (12 Kasım 2026; aktarici/sohbet.py ag_*): yerel yolda araya girme ve kısa söz tanıma — gerçek Silero, gerçek Whisper işçisi
# (whisper.cpp), gerçek turkish-stt (kuruluysa). Aktarıcı yalıtılmış kopyadan modül olarak yüklenir; yardımcı yok, öbekler gerçek zamanlı verilir.
#   1) Sınıf ve yankı kuralları (modelsiz): dur/onay/başka/boş, "Bekte"/"Tur" bir harf yanlışı, okunan metindeki söz yankı sayılır.
#   2) Yerel yol kapalıyken (SOHBET["yerel"] false ya da kip kapali) ag_obek hiçbir şey yapmaz, gövde bugünkü kuralı izler.
#   3) Gerçek VPIO kaydı (../_yedek/test-araclari/hoparlor-yanki/kayit3/kisa_var_vpio.wav, asistan hoparlörde okurken kullanıcının dur/bekle/evet/hı hı/soru
#      sözleri; MacBook Air, ses %81): kip tam, hoparlör (eşik 0,6 sn). Sayılır: doğru kesme, kaçan, yanlış kesme (onay ya da yankıdan), "dur" tepkisi.
#   4) Yapay ses (say -o, Yelda) kulaklık kipi (eşik 0,3 sn): dur/bekle keser, evet/hı hı/tamam kesmez, uzun soru keser (tam).
# Gerçek model yükler (AGIR_TESTLER; toplantı/sohbet sürerken bekler):  PYTHONDONTWRITEBYTECODE=1 python3 test/araya-girme.py   (~2,5 dk)
import importlib.util as u, json, os, shutil, statistics, subprocess, sys, tempfile, threading, time, wave
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bosport  # noqa: F401  (AGIR_TESTLER)
from bosport import bos_port
import numpy as np
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []; SR = 16000
HY = os.path.join(os.path.dirname(KOD), "_yedek", "test-araclari", "hoparlor-yanki")
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
def oku(yol):  # wav (int16 ya da float32, çok kanallıysa ilk kanal) → float32 16 kHz
    ham = open(yol, "rb").read(); i = 12; fmt = None; veri = b""
    while i + 8 <= len(ham):
        ad_, n = ham[i:i + 4], int.from_bytes(ham[i + 4:i + 8], "little")
        if ad_ == b"fmt ": fmt = (int.from_bytes(ham[i + 8:i + 10], "little"), int.from_bytes(ham[i + 10:i + 12], "little"), int.from_bytes(ham[i + 12:i + 16], "little"))
        elif ad_ == b"data": veri = ham[i + 8:i + 8 + n]; break
        i += 8 + n + (n & 1)
    tur, kn, sr = fmt; a = np.frombuffer(veri, np.float32 if tur == 3 else np.int16)
    if kn > 1: a = a[:len(a) // kn * kn].reshape(-1, kn)[:, 0]
    a = a.astype(np.float32) * (1.0 if tur == 3 else 1 / 32768)
    if sr != SR: a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)
    return a
# --- aktarıcı (yalıtılmış kopya, gerçek ortak klasör: Silero, whisper.cpp, turkish-stt) ---
PORT = bos_port(8781); T = tempfile.mkdtemp(prefix="suflor-ag-")
for f in ("relay.py", "manifest.json", "whisper-isci.py", "vad-isci.py", "tstt-golge-isci.py", "tur-isci.py", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "gelistirici": True, "yerel_araya_girme": "tam"},
          open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json")
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)]; os.chdir(T)
sp = u.spec_from_file_location("relay_ag", os.path.join(T, "relay.py")); m = u.module_from_spec(sp); sp.loader.exec_module(m)
# --- 1) sınıf ve yankı ---
S = m._ag_sinif
beklenen = [("Dur.", "dur"), ("Bekle.", "dur"), ("Sus!", "dur"), ("Bir dakika.", "dur"), ("Yeter.", "dur"), ("Bekte.", "dur"), ("Tur.", "dur"), ("Pekle", "dur"),
            ("Evet.", "onay"), ("Mhm.", "onay"), ("Hı hı.", "onay"), ("Tamam.", "onay"), ("Aynen", "onay"), ("Peki.", "onay"), ("Doğru.", "onay"), ("Anladım.", "onay"),
            ("Yarın hava nasıl?", "baska"), ("Peace.", "baska"), ("Altyazı M.K.", "bos"), ("İzlediğiniz için teşekkür ederim.", "bos"), ("", "bos")]
yanlis = [(x, S(x), b) for x, b in beklenen if S(x) != b]
ok(f"sınıf: {len(beklenen) - len(yanlis)}/{len(beklenen)} doğru" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
ara = [("E", "on"), ("Ev", "on"), ("Bek", "on"), ("D", "on"), ("Hı", "onay"), ("Ta", "on"), ("Dur", "dur"), ("Yar", "baska"), ("Yarın hav", "baska"), ("Evet", "onay"), ("Bir", "on")]
yanlis = [(x, S(x, ara=True), b) for x, b in ara if S(x, ara=True) != b]
ok("ara metin (tstt): onay/dur sözünün başı karar bekler" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
with m.SES_K: m.SES["simdi"] = "Akşamları ekran kullanımını azaltmak da uykuya dalmayı hızlandırır, durum böyle."
m.ARAYA["okunan"].clear()
ok("yankı: okunan metindeki söz sayılmaz (\"ekran kullanımı\"), okunmayan söz sayılır (\"yarın hava\")", m._ag_yanki("ekran kullanımını") and not m._ag_yanki("Yarın hava nasıl?"))
with m.SES_K: m.SES["simdi"] = "Arabayı iki saatte bir durdurup kısa bir mola ver. Sonra dur ve dinlen."
ok("yankı (durdurma sözü): yalnız aynı sözcük — \"dur\" okunan metinde varsa yankı, yalnız \"durdurup\" varsa değil", m._ag_yanki("Dur.", tam=True))
with m.SES_K: m.SES["simdi"] = "Arabayı iki saatte bir durdurup kısa bir mola ver."
ok("yankı (durdurma sözü): \"durdurup\" okunurken gerçek \"Dur\" yankı sayılmaz", not m._ag_yanki("Dur.", tam=True))
with m.SES_K: m.SES["simdi"] = ""
# --- 2) yerel yol kapalıyken hiçbir şey ---
m.SOHBET.update(acik=True, yerel=False, hoparlor=False)
ok("yerel yol kapalı: ag_etkin false, ag_obek öbeği almaz", not m.ag_etkin() and m.ag_obek(b"\0\0" * 1600, time.time()) is False)
m.AYAR["yerel_araya_girme"] = "kapali"; m.SOHBET["yerel"] = True
ok("kip kapali: ag_etkin false (Adım 4 davranışı: hoparlörde araya girme yok)", not m.ag_etkin())
m.AYAR["yerel_araya_girme"] = "tam"
# --- modeller ---
m.vad_baslat(); m._agt_baslat(); m.wh_one_al({"isinma": True, "kuyruga": time.time()}); m._isci_baslat()
t = time.time()
while time.time() - t < 240 and not (m.VAD.get("durum") == "hazir" and (m.AGT["durum"] == "hazir" or not m._agt_var()) and m._ISCI.get("p") and m.STATE["whisper"].get("durum") in ("hazir", "calisiyor", "acik")):
    time.sleep(0.5)
print(f"  modeller: Silero {m.VAD.get('durum')}, turkish-stt {m.AGT['durum']}, Whisper {m.STATE['whisper'].get('durum')} ({time.time() - t:.0f} sn)")
def wh_isit():  # ilk istekte sunucu ısınır: ölçüme girmesin
    ev = threading.Event(); m.wh_one_al({"id": "isit", "bas": True, "kanal": "bas", "baslik": None, "pcm": b"\0\0" * 8000, "t0": time.time(), "t1": time.time(), "kuyruga": time.time(),
                                        "dil": "tr", "istemsiz": True, "geri": lambda a, b: ev.set()}); ev.wait(120)
wh_isit(); wh_isit()
ok("Silero hazır", m.VAD.get("durum") == "hazir")
# --- ortak sürücü: öbekleri gerçek zamanlı ver, okuma aralıklarını ve kesmeleri izle ---
KESME = []; OKU = {"v": False}
m.ses_caliyor = lambda: OKU["v"]
m.ses_durdur = lambda: OKU.update(v=False) or True
m.ARAYA["kanca"] = lambda sinif, aday, tepki: KESME.append({"sinif": sinif, "t": aday["t"], "tepki": tepki, "kaynak": aday.get("kaynak"), "metin": aday.get("metin"), "wall": time.time()})
SINIF = []; GECIKME = []
_eski = m.ag_metin
def ag_metin_izle(aday, metin, kaynak, ara=False):
    s = _eski(aday, metin, kaynak, ara)
    if s and s != "on": SINIF.append({"t": aday["t"], "sinif": s, "kaynak": kaynak, "metin": metin, "wall": time.time(), "gec": round(time.time() - aday["t"], 3)})
    return s
m.ag_metin = ag_metin_izle
def sur(x, okumalar, metinler):  # x: float32 akış; okumalar: [(bas, son)] akış sn; metinler: okuma başına okunan metin → T0 (akış 0 anı)
    m._KS["tur"] = None; n = len(x) // 1600; T0 = time.time() + 0.2; i_ok = -1
    for i in range(n):
        ts = i * 0.1; k = next((j for j, (a, b) in enumerate(okumalar) if a <= ts < b), -1)
        if k != i_ok:
            i_ok = k; OKU["v"] = k >= 0
            with m.SES_K: m.SES["simdi"] = metinler[k] if k >= 0 else ""
        elif k >= 0 and not OKU["v"]: pass  # kesildi: bu okuma bitti sayılır
        bek = T0 + (i + 1) * 0.1 - time.time()
        if bek > 0: time.sleep(bek)
        m.ag_obek((np.clip(x[i * 1600:(i + 1) * 1600], -1, 1) * 32767).astype("<i2").tobytes(), T0 + i * 0.1)
    time.sleep(2.0); OKU["v"] = False; m.ag_obek(b"\0\0" * 1600, time.time()); return T0
# --- 3) gerçek VPIO kaydı (hoparlör, kip tam) ---
kayit = os.path.join(HY, "kayit3", "kisa_var_vpio.wav")
if not os.path.exists(kayit): print("– kayit3 yok: gerçek kayıt sınaması atlandı")
else:
    sys.path.insert(0, HY); from metin import CEVAP  # okunan metinler (asistan tarafı)
    meta = json.load(open(kayit + ".json")); Lv = meta["play_epoch"] - meta["tap_ilk_epoch"] + 0.1
    S_ = json.load(open(os.path.join(HY, "ses", "S_kisa_var.json"))); ogeler = [o for o in S_["ogeler"] if not o["isinma"]]
    b_ = json.load(open(os.path.join(HY, "adim0", "b_sonuc.json")))["olay"]
    olay = [{"tur": o["tur"], "s": o["s"]} for o in b_ if o.get("akis") == "vpio" and o.get("durum") == "ok"]  # Silero başı (Adım 0b), akış saniyesi
    x = oku(kayit); x = x[int(Lv * SR):int((Lv + S_["sure"] + 1) * SR)]
    m.SOHBET.update(acik=True, yerel=True, hoparlor=True, t_okuma=0.0); m.AYAR["yerel_araya_girme"] = "tam"
    print(f"  kayıt: {len(x) / SR:.0f} sn, {len(ogeler)} okuma, {len(olay)} söz — gerçek zamanlı veriliyor…")
    KESME.clear(); SINIF.clear(); T0 = sur(x, [(o["bas"], o["son"]) for o in ogeler], [CEVAP[o["metin_no"]] for o in ogeler])
    gercek = {"dur": "dur", "bekle": "dur", "evet": "onay", "hihi": "onay", "soru": "baska"}
    sonuc = []; kullanilan = set()
    for e in olay:
        k = next((j for j, c in enumerate(KESME) if j not in kullanilan and -0.6 <= c["t"] - T0 - e["s"] <= 1.5), None)
        if k is not None: kullanilan.add(k)
        c = KESME[k] if k is not None else None
        sn = [s for s in SINIF if -0.6 <= s["t"] - T0 - e["s"] <= 1.5]
        sonuc.append(dict(e, gercek=gercek[e["tur"]], kesti=c["sinif"] if c else None, tepki=round(c["tepki"], 2) if c else None, kaynak=c["kaynak"] if c else None,
                          tanima=[(s["kaynak"], s["metin"], s["sinif"]) for s in sn][:3]))
    for r in sonuc: print(f"    {r['tur']:5} {r['s']:6.1f} sn → kesme {r['kesti'] or '—':5} tepki {r['tepki'] if r['tepki'] is not None else '—'} ({r['kaynak'] or '—'}) · {r['tanima']}")
    dur_ = [r for r in sonuc if r["gercek"] == "dur"]; onay_ = [r for r in sonuc if r["gercek"] == "onay"]; baska_ = [r for r in sonuc if r["gercek"] == "baska"]
    yankidan = [c for j, c in enumerate(KESME) if j not in kullanilan]
    tep = [r["tepki"] for r in dur_ if r["kesti"] == "dur"]
    print(f"  ÖZET (VPIO, hoparlör, tam): dur/bekle {sum(r['kesti'] == 'dur' for r in dur_)}/{len(dur_)} kesti (kaçan {sum(not r['kesti'] for r in dur_)}), "
          f"onay {sum(bool(r['kesti']) for r in onay_)}/{len(onay_)} yanlış kesme, başka söz {sum(bool(r['kesti']) for r in baska_)}/{len(baska_)} kesti, "
          f"söz dışı (yankı) yanlış kesme {len(yankidan)}" + (f" {[(round(c['t'] - T0, 1), c['metin']) for c in yankidan]}" if yankidan else "") +
          (f" · dur tepkisi ortanca {statistics.median(tep):.2f} sn, en kötü {max(tep):.2f} sn" if tep else ""))
    wh = [s for s in SINIF if s["kaynak"] == "whisper"]
    ok("gerçek kayıt: onay (evet/hı hı) okumayı kesmedi", not any(r["kesti"] for r in onay_))
    ok("gerçek kayıt: söz dışında (yalnız asistan yankısı) yanlış kesme yok", not yankidan)
    ok(f"gerçek kayıt: dur/bekle en az 3/4 kesti (Adım 0b'de Whisper 0,4 sn parçada 3/4 doğru yazdı)", sum(r["kesti"] == "dur" for r in dur_) >= 3)
    ok("gerçek kayıt: Whisper kısa parça yolu çalıştı", bool(wh) or not m._ISCI.get("p"))
    json.dump({"olay": sonuc, "kesme": [dict(c, t=round(c["t"] - T0, 2)) for c in KESME], "sinif": [dict(s, t=round(s["t"] - T0, 2)) for s in SINIF]},
              open(os.path.join(tempfile.gettempdir(), "araya-girme-sonuc.json"), "w"), ensure_ascii=False, indent=1, default=float)
# --- 4) yapay ses, kulaklık (eşik 0,3 sn): sessizlik + gürültü üstünde say -o ---
def say(metin):
    yol = os.path.join(T, "s.wav"); subprocess.run(["/usr/bin/say", "-v", "Yelda", "-o", yol, "--file-format=WAVE", "--data-format=LEI16@16000", metin], check=True, timeout=30)
    with wave.open(yol) as w: return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768 * 0.5
sozler = [("Dur.", "dur"), ("Evet.", "onay"), ("Bekle.", "dur"), ("Hı hı.", "onay"), ("Tamam.", "onay"), ("Yarın sabah toplantı kaçta başlıyor, hatırlatır mısın?", "baska"), ("Sus.", "dur")]
rng = np.random.default_rng(7); parca = []; yer = []; t_ = 1.5
for metin, g in sozler:
    a = say(metin); parca += [np.zeros(int(1.5 * SR) if not parca else int(4.0 * SR), np.float32), a]; yer.append((t_, g, metin)); t_ += len(a) / SR + 4.0
x = np.concatenate(parca + [np.zeros(3 * SR, np.float32)]); x = x + rng.normal(0, 0.002, len(x)).astype(np.float32)
oku_ = [(max(0.0, s - 3.0), s + 3.0) for s, _, _ in yer]  # her sözden 3 sn önce okuma başlar (kulaklıkta koruma SOHBET_KORU_SN 2 sn)
m.SOHBET.update(acik=True, yerel=True, hoparlor=False, t_okuma=0.0); GECIKME += SINIF; KESME.clear(); SINIF.clear()
print(f"  yapay ses (kulaklık, eşik {m.ag_esik():.1f} sn): {len(sozler)} söz…")
T0 = sur(x, oku_, ["Bugün hava güneşli, akşam serinleyecek."] * len(oku_))
iyi = 0
for s, g, metin in yer:
    c = next((c for c in KESME if -0.3 <= c["t"] - T0 - s <= 1.5), None)
    dogru = (c is not None) == (g in ("dur", "baska")); iyi += dogru
    print(f"    {'✓' if dogru else '✗'} {metin[:30]:30} ({g}) → {c['sinif'] + ' ' + format(c['tepki'], '.2f') + ' sn ' + str(c['kaynak']) if c else 'kesmedi'}")
ok(f"yapay ses kulaklık: {iyi}/{len(yer)} doğru karar", iyi == len(yer))
tep = [c["tepki"] for c in KESME if c["sinif"] == "dur"]
if tep: print(f"  yapay ses 'dur' tepkisi (söz başından kes'e): ortanca {statistics.median(tep):.2f} sn, en kötü {max(tep):.2f} sn")
GECIKME += SINIF; print(f"  sayaçlar: {m.ag_view()['say']}")
for kay in ("tstt", "whisper"):  # tanıyıcının ilk sınıf kararı, söz başından (Silero) — iki bölümün toplamı
    g = [x["gec"] for x in GECIKME if x["kaynak"] == kay]
    if g: print(f"  {kay}: sınıf kararı söz başından ortanca {statistics.median(g):.2f} sn, en kötü {max(g):.2f} sn (n={len(g)})")
try: m._agt_kapat(); m.vad_kapat(); m._isci_kapat("test bitti")
except Exception: pass
os.chdir("/"); shutil.rmtree(T, ignore_errors=True)
print("araya girme: ✓ hepsi geçti" if not HATA else f"araya girme: ✗ {len(HATA)} sınama kaldı")
sys.exit(1 if HATA else 0)
