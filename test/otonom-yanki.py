#!/usr/bin/env python3
# Otonom okurken yankı ayrımı (aktarici/otonom.py yanki_disi, toplantiya-ses.py ses_zarfi; 19 Ekim test toplantısı): kanaldaki ses okunan sesin gecikmeli
# kopyasıysa (karşı taraftan geri gelen kendi sesimiz) okuma kesilmez; biz susarken gelen ses ≥ 1 sn ise kesilir; okunan sesle örtüşmeyen ses yankı sayılmaz.
# Yapay kare dizileriyle, ses yok (~1 sn).   PYTHONDONTWRITEBYTECODE=1 python3 test/otonom-yanki.py
import ast, math, os, random, struct, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
ns = {"math": math}
for dosya, adlar in (("otonom.py", {"yanki_disi", "otonom_kesilsin", "OTONOM_YANKI_GECIKME_SN", "OTONOM_ARA_KARE", "OTONOM_KESME_SN"}), ("toplantiya-ses.py", {"ses_zarfi"})):
    a = ast.parse(open(os.path.join(KOD, "aktarici", dosya), encoding="utf-8").read())
    sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(
        (getattr(x, "id", None) in adlar) or (isinstance(x, ast.Tuple) and any(getattr(e, "id", None) in adlar for e in x.elts)) for x in n.targets))]
    exec(compile(ast.Module(sec, []), dosya, "exec"), ns)
yd = ns["yanki_disi"]; ks = lambda ts, z: ns["otonom_kesilsin"](ts, z, T0, ESIK)[0]; ESIK = int(ns["OTONOM_KESME_SN"] / 0.02)
ok(f"kesme eşiği 1 sn ({ESIK} kare)", ESIK == 50)
random.seed(1)
# okunan ses: 10 sn, sözcük (0,2–0,5 sn sesli) + boşluk (0,05–0,25 sn)
zarf = []
while len(zarf) < 500: zarf += [True] * random.randint(10, 25) + [False] * random.randint(3, 12)
zarf = zarf[:500]; T0 = 1000.0
def yanki(gecikme, kayip=0.1, son=10.0):  # okunan sesin gecikmeli kopyası (karelerin %10'u kayıp: gürültü bastırma)
    return [T0 + i * 0.02 + gecikme for i, v in enumerate(zarf) if v and random.random() > kayip and i * 0.02 + gecikme <= son]
ts = yanki(0.45); n, d = yd(ts, zarf, T0)
ok(f"karşı taraftan geri gelen kendi sesimiz (0,45 sn gecikme): yankı, kesmez (açıklanamayan {n} kare, gecikme {d})", n < ESIK and d is not None and abs(d - 0.45) <= 0.08)
ts = yanki(0.0, kayip=0.3); n, d = yd(ts, zarf, T0)
ok(f"mikrofona sızan kısık kendi ses (gecikmesiz, %30 kayıp): kesmez ({n} kare)", n < ESIK)
# biz susarken (son 1,4 sn okunan ses sessiz) biri 1,2 sn konuşuyor
z2 = zarf[:430] + [False] * 70
ts = [t for t in yanki(0.3, son=8.6)] + [T0 + 8.7 + i * 0.02 for i in range(60)]
n, d = yd(ts, z2, T0)
ok(f"yankının üstüne biz susarken 1,2 sn konuşma: keser ({n} kare ≥ {ESIK})", n >= ESIK)
ts = [T0 + 2 + i * 0.02 for i in range(80)]; n, d = yd(ts, [False] * 500, T0)
ok(f"okunan ses sessizken gelen 1,6 sn ses: gerçek ses ({n} kare), yankı değil", n >= ESIK and d is None)
ts = sorted(t for t in set(yanki(0.45)) | {T0 + 4 + i * 0.02 for i in range(75)} if t <= T0 + 5.55); n, d = yd(ts, zarf, T0)  # döngü 0,25 sn'de bir bakar: o anki görünüm
ok(f"biz konuşurken yankının üstüne 1,5 sn konuşma: keser (aralarımızda {n} kare)", ks(ts, zarf))
ok("yalnız yankı: kesmez (otonom_kesilsin)", not ks(yanki(0.45), zarf) and not ks(yanki(0.0, kayip=0.3), zarf))
n, d = yd([T0 + 1 + i * 0.02 for i in range(30)], None, T0)
ok("zarf yoksa (Mac sesi) eski sayım: 0,6 sn ses kesmez", n == 30 and n < ESIK)
# uzun okumada küçük uyumsuzluk birikmez: yalnız son 3 sn sayılır
uzun = []
while len(uzun) < 1500: uzun += [True] * random.randint(10, 25) + [False] * random.randint(3, 12)
ts = [T0 + i * 0.02 + 0.5 for i, v in enumerate(uzun[:1500]) if v] + [T0 + i * 0.02 + 0.5 for i, v in enumerate(uzun[:1500]) if not v and random.random() < 0.12]
ts.sort(); n, d = yd(ts, uzun[:1500], T0)
ok(f"30 sn okumada %12 dağınık gürültü: kesmez (son 3 sn'de {n} kare)", not ns["otonom_kesilsin"](ts, uzun[:1500], T0, ESIK)[0])
# ses_zarfi: 24 kHz 16 bit — 0,3 sn ton + 0,2 sn sessizlik
pcm = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / 24000)) if (i // 2400) % 5 < 3 else 0) for i in range(24000))
z = ns["ses_zarfi"](pcm, 24000)
ok(f"ses_zarfi: 50 kare, sesli/sessiz örüntü ({sum(z)} sesli ≈ 30)", len(z) == 50 and 28 <= sum(z) <= 32 and z[0] and not z[16])
# okuma sürerken kullanıcının kısa durdurma sözü (28 Ekim "bir dakika"): yankı ölçümü beklenmeden keser; söylediğimiz metinde geçiyorsa kesmez
import re, time, threading
def _ayikla(dosya, adlar):
    a = ast.parse(open(os.path.join(KOD, "aktarici", dosya), encoding="utf-8").read())
    sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in adlar for x in n.targets))]
    exec(compile(ast.Module(sec, []), dosya, "exec"), ns)
import unicodedata
ns.update(re=re, time=time, threading=threading, TS={"web": None, "p": []}, TS_KILIT=threading.Lock(), YANKI_LOCK=threading.Lock(), KENDI_SES=[],
          kisilikler=lambda: [{"hitap": ["Deniz"]}], sade=lambda t: unicodedata.normalize("NFKD", t.lower().replace("ı", "i")).encode("ascii", "ignore").decode(), _kok_ayni=lambda x, y: x[:3] == y[:3])
_ayikla("bas-konus.py", {"ASISTAN_DUR_RX"}); _ayikla("otonom.py", {"okuma_suruyor", "okuma_dur_soz"})
ds = ns["okuma_dur_soz"]
ok("okuma yokken 'Bir dakika' kesmez", not ds("Bir dakika."))
ns["TS"]["web"] = {"t": time.time(), "sure": 15.0, "dur": False}
for m in ("Bir dakika.", "Dur.", "Sus artık", "Deniz, bekle", "Beni dinler misin? Bir dakika.", "Wait", "Dur bir dakika"):
    ok(f"okurken '{m}' → keser", ds(m))
for m in ("Bir dakika içinde toplantıya katılacağım ve sizi arayacağım", "Evet tamam", "Bunu bir dakika sonra konuşalım"):
    ok(f"okurken '{m}' → kesmez", not ds(m))
ns["KENDI_SES"].append((time.time() - 5, time.time() + 5, ["bir", "dakika", "sonra"]))
ok("söylediğimiz metinde 'bir dakika' geçiyorsa (yankı olabilir) kesmez", not ds("Bir dakika.", time.time() - 3))
ns["TS"]["web"]["dur"] = True
ok("okuma bittiyse kesmez", not ds("Dur."))
# v0.152.0: başkasına seslenilen ad hitapsız cevap sayılmaz; karşı hitap yalnız okunan metne benzerse atılır; ikinci cevap öncekinin okumasını kesmez; "siz" kuralı
_VK = {"_VOKATIF": set()}; ns.update(_VK, kisilikler=lambda: [{"hitap": ["Deniz"]}])
_ayikla("bas-konus.py", {"_VOKATIF", "_vk_ad", "vokatif_ogren", "vokatif_mi"})
vo, vm = ns["vokatif_ogren"], ns["vokatif_mi"]
ok("başkasına seslenilmemişken ad cevap dışı sayılmaz", not vm("Esra öyle deme."))
vo("Esra, duyuyor musun beni?"); vo("Deniz, beni duyuyor musun?")
ok("virgülle seslenilen ad öğrenilir: 'Esra öyle deme' cevap sayılmaz", vm("Esra öyle deme.") and vm("Esra duydun mu konuşmayı?"))
ok("asistanın kendi adı öğrenilmez", not vm("Deniz tamam."))
ok("başka bir söz cevap sayılabilir ('Bugün değil, salı')", not vm("Bugün değil, salı."))
kod_ = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read(); kod_o = open(os.path.join(KOD, "aktarici", "otonom.py"), encoding="utf-8").read()
ok("karşı hitap: satır zamanı varsa yalnız _kendi_mi yankısı atılır", "def konus_hitap_karsi(text, kim, t0=None, t1=None)" in kod_ and "_kendi_mi((t0, t1, _yk(text)), k) for k in KENDI_SES" in kod_)
ok("toplantıya okunan cevap istemine 'siz' kuralı (TR+EN)", "kullanıcıya her zaman «siz» diye hitap et" in kod_ and "always address the user formally" in kod_)
ok("otonom_sun öncekinin okuması sürerken bekler; gecikme satırı yazılır", "önceki cevap sürüyordu" in kod_o and "OTONOM: gecikme" in kod_o)
print("otonom yankı: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
