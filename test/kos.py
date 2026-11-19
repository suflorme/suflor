#!/usr/bin/env python3
# Katmanlı test koşucusu. Hepsi art arda koşar (sabit portlar çakışır). Kullanım (PYTHONDONTWRITEBYTECODE gerekmez, -B yeter):
#   python3 -B test/kos.py                    # katman A (varsayılan; hızlı, gerçek model/headless yok)
#   python3 -B test/kos.py --katman AB        # A + B (gerçek aktarıcı/port)
#   python3 -B test/kos.py --hepsi            # A + B + C (C: ağır modelli + headless; canlı kullanımda atlanır)
#   python3 -B test/kos.py --degisen          # git diff'te değişen dosyaların testleri (testler/TEST-REHBERI.md) + katman A
#   python3 -B test/kos.py --tarih-kaydir 400 # katman A'yı +400 gün kaydırılmış saatle de koş, sonucu değişen (tarihe bağlı) testleri bildir
#   python3 -B test/kos.py test/renk.py ...   # yalnız bu testler (katmandan bağımsız)
#   --yedek-dahil: ../_yedek/test-araclari/test<N>.py (headless Chrome; katman C) da keşfedilir
# Katman: ilk 5 satırda "# katman: A|B|C" varsa o; yoksa test/katman.json "elle" kaydı; yoksa çıkarım (AGIR_TESTLER/headless → C,
# aktarıcı/port → B, kalan A). Ölçülen süre katman.json'a yazılır. Sonuç: testler/kos-son.json. Bilinen kırıklar: test/bilinen-kirik.json
# ({test: {neden, son_tarih}}): son_tarihe kadar raporlanır ama koşuyu düşürmez; geçince düşürür.
import argparse, datetime, glob, json, os, re, subprocess, sys, tempfile, time

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST = os.path.join(KOD, "test"); YEDEK = os.path.join(os.path.dirname(KOD), "_yedek", "test-araclari")
KATMAN_J = os.path.join(TEST, "katman.json"); KIRIK_J = os.path.join(TEST, "bilinen-kirik.json"); SON_J = os.path.join(KOD, "testler", "kos-son.json")
REHBER = os.path.join(KOD, "testler", "TEST-REHBERI.md")
SINIR = {"A": 90, "B": 240, "C": 600}
DISLA = {"bosport.py", "katman.json", "kos.py"}  # yardımcılar, test değil

def yukle(p, vars_=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {} if vars_ is None else vars_

def agir_kume():
    try:
        m = re.search(r"AGIR_TESTLER\s*=\s*\{(.*?)\}", open(os.path.join(TEST, "bosport.py"), encoding="utf-8").read(), re.S)
        return set(re.findall(r'"([^"]+\.py)"', m.group(1)))
    except Exception: return set()

def cikar(yol, agir):
    ad = os.path.basename(yol)
    if yol.startswith(YEDEK) or "headless" in ad: return "C"
    try: kaynak = open(yol, encoding="utf-8", errors="replace").read()
    except Exception: return "A"
    ilk = "\n".join(kaynak.splitlines()[:5])
    m = re.search(r"#\s*katman:\s*([ABC])", ilk)
    if m: return m.group(1)
    if ad in agir: return "C"
    if re.search(r"headless|--headless|chromium", kaynak, re.I) and re.search(r"subprocess|Popen", kaynak): return "C"
    if re.search(r"bos_port|relay\.py|127\.0\.0\.1|localhost|http\.server|\b87\d\d\b", kaynak): return "B"
    return "A"

def kesfet(yedek_dahil):
    kat = yukle(KATMAN_J); agir = agir_kume(); sonuc = {}
    adaylar = [p for p in sorted(glob.glob(os.path.join(TEST, "*.py"))) if os.path.basename(p) not in DISLA]
    if yedek_dahil: adaylar += [p for p in sorted(glob.glob(os.path.join(YEDEK, "test[0-9]*.py"))) if re.fullmatch(r"test\d+\.py", os.path.basename(p))]
    for p in adaylar:
        ad = os.path.relpath(p, KOD) if p.startswith(TEST) else "yedek/" + os.path.basename(p)
        k = kat.get(ad) or {}
        sonuc[ad] = {"yol": p, "katman": k["katman"] if k.get("elle") else cikar(p, agir)}
    return sonuc

def mesgul():
    try:
        r = subprocess.run([sys.executable, "-B", "-c", "import kurulum; print(kurulum.mesgul())"], cwd=KOD, capture_output=True, text=True, timeout=20,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    except Exception: return ""

def bekle_bos(sn=900):
    t0 = time.time()
    while True:
        m = mesgul()
        if not m: return ""
        if time.time() - t0 > sn: return m
        print(f"  … canlı kullanım var ({m}); 60 sn beklenir", flush=True); time.sleep(60)

def headless_oldur(): subprocess.run(["pkill", "-f", "Google Chrome.*--headless"], capture_output=True)

def sahte_saat_dizini(gun):
    d = tempfile.mkdtemp(prefix="kos-saat-")
    open(os.path.join(d, "sitecustomize.py"), "w").write(f'''import time as _t, datetime as _d
_K = {int(gun)} * 86400
_g, _lt, _gm, _sf = _t.time, _t.localtime, _t.gmtime, _t.strftime
_t.time = lambda: _g() + _K
_t.localtime = lambda s=None: _lt(_g() + _K if s is None else s)
_t.gmtime = lambda s=None: _gm(_g() + _K if s is None else s)
_t.strftime = lambda f, tt=None: _sf(f, _lt(_g() + _K) if tt is None else tt)
_dt, _dd = _d.datetime, _d.date
class _DT(_dt):
    @classmethod
    def now(cls, tz=None): return _dt.now(tz) + _d.timedelta(seconds={int(gun)} * 86400)
    @classmethod
    def utcnow(cls): return _dt.utcnow() + _d.timedelta(seconds={int(gun)} * 86400)
    @classmethod
    def today(cls): return cls.now()
class _D(_dd):
    @classmethod
    def today(cls): return _dd.today() + _d.timedelta(days={int(gun)})
_d.datetime = _DT; _d.date = _D
''')
    return d

def kos_tek(ad, yol, katman, saat_dizini=None):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SUFLOR_TEST_ZORLA": os.environ.get("SUFLOR_TEST_ZORLA", "")}
    if saat_dizini: env["PYTHONPATH"] = saat_dizini + os.pathsep + env.get("PYTHONPATH", "")
    if katman == "C": headless_oldur()
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-B", yol], cwd=KOD, capture_output=True, text=True, timeout=SINIR[katman], env=env, errors="replace")
        cikti = (r.stdout or "") + (r.stderr or ""); kod = r.returncode; zaman_asimi = False
    except subprocess.TimeoutExpired as e:
        cikti = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")); kod = -9; zaman_asimi = True
    if katman == "C": headless_oldur()
    x = [l.strip() for l in cikti.splitlines() if l.lstrip().startswith("✗")]
    durum = "zaman_asimi" if zaman_asimi else ("gecti" if kod == 0 and not x else "kaldi")
    son = [l for l in cikti.splitlines() if l.strip()][-3:]
    return {"durum": durum, "cikis": kod, "sure": round(time.time() - t0, 1), "x_satirlari": x[:8], "son": [s[:200] for s in son]}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("testler", nargs="*"); ap.add_argument("--katman", default="A"); ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--degisen", action="store_true"); ap.add_argument("--tarih-kaydir", type=int, default=0, metavar="GUN")
    ap.add_argument("--yedek-dahil", action="store_true"); ap.add_argument("--canli-bekle", type=int, default=900, metavar="SN")
    a = ap.parse_args()
    katmanlar = "ABC" if a.hepsi else a.katman.upper()
    tum = kesfet(a.yedek_dahil or "C" in katmanlar and a.hepsi)
    if a.testler:
        sec = {}
        for t in a.testler:
            ad = os.path.relpath(os.path.abspath(t), KOD) if os.path.exists(t) else t
            if ad in tum: sec[ad] = tum[ad]
            else: print("bilinmeyen test:", t); return 2
    else:
        sec = {k: v for k, v in tum.items() if v["katman"] in katmanlar}
        if a.degisen:
            for k in degisen_testler(tum): sec.setdefault(k, tum[k])
            if not a.katman or a.katman.upper() == "A": sec = {k: v for k, v in tum.items() if k in sec or v["katman"] == "A"}
    kirik = yukle(KIRIK_J); bugun = datetime.date.today().isoformat()
    print(f"kos: {len(sec)} test, katman {''.join(sorted({v['katman'] for v in sec.values()}))}", flush=True)
    saat = sahte_saat_dizini(a.tarih_kaydir) if a.tarih_kaydir else None
    sonuclar = {}; kat_j = yukle(KATMAN_J)
    for ad, v in sorted(sec.items(), key=lambda kv: (kv[1]["katman"], kv[0])):
        if v["katman"] in "BC":
            m = bekle_bos(a.canli_bekle)
            if m: sonuclar[ad] = {"katman": v["katman"], "durum": "atlandi", "neden": m, "sure": 0}; print(f"  - {ad}: atlandı ({m})", flush=True); continue
        r = kos_tek(ad, v["yol"], v["katman"]); r["katman"] = v["katman"]; sonuclar[ad] = r
        print(f"  {'✓' if r['durum'] == 'gecti' else '✗'} {ad} [{v['katman']}] {r['sure']} sn", flush=True)
        e = kat_j.setdefault(ad, {}); e["sure"] = r["sure"]; e["katman"] = e.get("katman") if e.get("elle") else v["katman"]
    json.dump(dict(sorted(kat_j.items())), open(KATMAN_J, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # tarih kaydırma: aynı testleri kaydırılmış saatle de koş, sonucu değişenleri bildir
    tarihe_bagli = []
    if saat:
        print(f"\ntarih kaydırma +{a.tarih_kaydir} gün:", flush=True)
        for ad, v in sorted(sec.items()):
            if v["katman"] != "A" or sonuclar[ad]["durum"] == "atlandi": continue
            r2 = kos_tek(ad, v["yol"], "A", saat)
            if r2["durum"] != sonuclar[ad]["durum"]:
                tarihe_bagli.append({"test": ad, "normal": sonuclar[ad]["durum"], "kaydirilmis": r2["durum"], "x": r2["x_satirlari"][:3]}); print(f"  ! {ad}: {sonuclar[ad]['durum']} → {r2['durum']}", flush=True)
    # sınıflandırma
    yeni, bilinen, gecen, atlanan = [], [], [], []
    for ad, r in sonuclar.items():
        if r["durum"] == "atlandi": atlanan.append(ad)
        elif r["durum"] == "gecti":
            gecen.append(ad)
            if ad in kirik: r["not"] = "bilinen kırık listesinde ama geçti; listeden çıkar"
        else:
            k = kirik.get(ad)
            if k and bugun <= k.get("son_tarih", ""): bilinen.append(ad); r["bilinen"] = k.get("neden")
            else: yeni.append(ad); r["bilinen"] = (k or {}).get("neden") and f"son tarih geçti: {k['son_tarih']}"
    ozet = {"zaman": datetime.datetime.now().isoformat(timespec="seconds"), "katmanlar": katmanlar, "gecti": len(gecen), "yeni_kirik": yeni, "bilinen_kirik": bilinen,
            "atlandi": atlanan, "tarihe_bagli": tarihe_bagli, "tarih_kaydir": a.tarih_kaydir, "sure_toplam": round(sum(r["sure"] for r in sonuclar.values()), 1), "testler": sonuclar}
    os.makedirs(os.path.dirname(SON_J), exist_ok=True); json.dump(ozet, open(SON_J, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{'test':44} {'kat':3} {'durum':12} {'sn':>6}")
    for ad, r in sorted(sonuclar.items(), key=lambda kv: (kv[1]["durum"] == "gecti", kv[0])):
        if r["durum"] != "gecti": print(f"{ad:44} {r['katman']:3} {r['durum'] + (' (bilinen)' if ad in bilinen else ''):12} {r['sure']:>6}")
    for ad in yeni:
        for l in sonuclar[ad]["x_satirlari"][:2] or sonuclar[ad]["son"][-1:]: print(f"   {ad}: {l[:150]}")
    print(f"\ngeçen {len(gecen)} · YENİ kırık {len(yeni)} · bilinen kırık {len(bilinen)} · atlanan {len(atlanan)} · {ozet['sure_toplam']} sn · {SON_J}")
    return 1 if yeni else 0

def degisen_testler(tum):
    r = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=KOD, capture_output=True, text=True)
    dosyalar = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    try: satirlar = open(REHBER, encoding="utf-8").read().splitlines()
    except Exception: satirlar = []
    bulunan = set()
    for d in dosyalar:
        if d.startswith("test/") and d.endswith(".py") and d in tum: bulunan.add(d)
        ad = os.path.basename(d)
        for s in satirlar:
            if re.search(r"(?<![\w/.-])" + re.escape(ad) + r"(?![\w-])", s):
                for t in re.findall(r"test/([\w.-]+\.py)", s):
                    if "test/" + t in tum: bulunan.add("test/" + t)
    print(f"değişen dosya {len(dosyalar)}, rehberden eşleşen test {len(bulunan)}")
    return bulunan

if __name__ == "__main__": sys.exit(main())
