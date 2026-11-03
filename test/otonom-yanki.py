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
for dosya, adlar in (("otonom.py", {"yanki_disi", "otonom_kesilsin", "OTONOM_YANKI_GECIKME_SN", "OTONOM_ARA_KARE", "OTONOM_ARA_YAYILIM_SN", "OTONOM_ARA_KUME", "OTONOM_KESME_SN"}), ("toplantiya-ses.py", {"ses_zarfi"})):
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
ts = sorted(set(yanki(0.45)) | {T0 + 4.0 + 0.02 * i for i in range(25)})
ok("31 Ekim: yankı + 0,5 sn kelimesiz ses (nefes, hareket): kesmez", not ks([t for t in ts if t <= T0 + 5.5], zarf) and not ks(ts, zarf))
bos = [k for k in range(1, 490) if not zarf[k] and zarf[k - 1] and not any(zarf[k:k + 8])]  # ≥ 0,16 sn'lik aralıklar  # okunan sesteki aralıkların başı (kare)
g1 = next(k for k in bos if k >= 200); g2 = next(k for k in bos if k >= g1 + 48)  # "hı hı": iki hece, iki aralığa ~1 sn arayla düşer (gerçek 1 Kasım: 0,3 sn açıklanamayan, 0,9 sn yayılım)
hh = {T0 + 0.45 + (k + m) * 0.02 for k in (g1, g2) for m in range(-6, 14) if 0 <= k + m < 500}
ts = sorted(set(yanki(0.45)) | hh)
ok("1 Kasım: yankı + okurken \"hı hı\": kesmez", not any(ks([t for t in ts if t <= T0 + u], zarf) for u in (4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0)) and not ks(ts, zarf))
ts = sorted(set(yanki(0.45)) | {T0 + 4 + i * 0.02 for i in range(75)}); ok("yankı + 1,5 sn gerçek ses: yine keser", ks([t for t in ts if t <= T0 + 5.55], zarf))
ok("yalnız yankı: kesmez (otonom_kesilsin)", not ks(yanki(0.45), zarf) and not ks(yanki(0.0, kayip=0.3), zarf))
ok("3 Kasım: 0,18 sn gecikmeli yankı (yerleşik hoparlör → mikrofon): kesmez", not any(ks([t for t in yanki(0.18) if t <= T0 + u], zarf) for u in (3, 5, 7, 9)) and abs((yd(yanki(0.18), zarf, T0)[1] or 9) - 0.18) <= 0.06)
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
# 3 Kasım (gerçek Teams denemesi, yerleşik mikrofon): kullanıcı asistanın üstüne konuştu, enerji ölçümü yankı sandı. okuma_ustune_soz: okuma sürerken başlamış ben satırı,
# ≥ 3 içerik sözcüğü ve sesi kullanıcıya benziyorsa (ses izi ≥ 0,45) keser; yankı (bozuk yazılmış da olsa) ve "hı hı/hmm/evet" kesmez. Metinler ve benzerlikler o günün günlüğünden.
_ayikla("whisper-hat.py", {"_yk"}); _ayikla("otonom.py", {"OTONOM_USTUNE_SOZ", "ONAY_SOZ", "_kok_benzer", "okuma_ustune_soz"})
_a2 = ast.parse(open(os.path.join(KOD, "aktarici", "otonom.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in _a2.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple) and any(getattr(e, "id", "") == "OTONOM_USTUNE_BENZERLIK" for e in n.targets[0].elts)], []), "otonom.py", "exec"), ns)
ns.update(OT_K=threading.Lock(), _ot_ayar=lambda a, v: v, kisilikler=lambda: [{"hitap": ["ATLAS", "Atlas"]}], KENDI_SES=[], _kok_ayni=lambda x, y: (lambda n: n >= 3 and n >= min(len(x), len(y)) - 2)(next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))))
uk = ns["okuma_ustune_soz"]; tb = time.time() - 5; ns["OT"] = {"id": "x", "durum": "okunuyor", "t_durum": tb}
ok("üstüne konuşma (12:10:32 'Deneme 13'ün tüm maddelerini yap.', ses izi 0,72): keser", bool(uk(tb + 1.0, "Deneme 13'ün tüm maddelerini yap.", 0.72)))
ok("üstüne konuşma (12:10:47, 0,62, yankıyla karışık): keser", bool(uk(tb + 2.0, "Yani deneme 13'ün tüm test... Transpikt işi şu an bekleyişte. Asıl transpikt başlat.", 0.62)))
ok("bozuk yazılmış yankı (11:44:44 'Evet. Evet. Sizi duyuyoruz.', 0,08): kesmez", not uk(tb + 1.0, "Evet. Evet. Sizi duyuyoruz. Sizi duyuyoruz.", 0.08))
ok("bozuk yankı, ses izi yüksek ama içerik onay (11:43:49 'Dinliyorum. Tamam. Peki.'): kesmez", not uk(tb + 1.0, "Dinliyorum. Tamam. Peki.", 0.6))
for m in ("Hı hı.", "Hmm.", "Evet evet.", "Tamam, evet.", "Atlas."):
    ok(f"okurken '{m}' (ses izi 0,7): kesmez", not uk(tb + 1.0, m, 0.7))
ok("kısa söz ('Toplantı bitince.', 2 sözcük, 0,68): kesmez (kısa durdurma okuma_dur_soz'da)", not uk(tb + 1.0, "Toplantı bitince.", 0.68))
ok("okuma başlamadan başlamış satır (11:53:17): kesmez", not uk(tb - 0.5, "Atlas. Bargo şimdi burada ne yazıyor bak", 0.59))
ns["OT"]["durum"] = "okundu"; ok("okuma bitmişse kesmez", not uk(tb + 1.0, "Deneme 13'ün tüm maddelerini yap.", 0.72)); ns["OT"]["durum"] = "okunuyor"
ns["KENDI_SES"].append((tb, tb + 20, ns["_yk"]("Transkript işi şu an bekleyişte: asıl transkripti başlattınız, bekçi kurdu; toplantı bitince haber verip örneği hazırlayacak.")))
ok("ses izi yok (kısa parça), yankının bozuk yazımı ('Asıl transpikt işi şuan bekleyin.'): kesmez", not uk(tb + 2.0, "Asıl transpikt işi şuan bekleyin.", None))
ok("ses izi yok, okunan metinde olmayan 4 sözcük: keser (yedek kural)", bool(uk(tb + 2.0, "Bütçe tablosunu yarın gönderelim mi", None)))
kod_w = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
ok("whisper_yaz'daki kısa durdurma sözü ses kilidinde de çalışır (yalnız oda kipinde atlanır)", 'not (is_.get("oda") and oda_acik()) and "okuma_dur_soz" in globals()' in kod_w)
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
