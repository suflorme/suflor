#!/usr/bin/env python3
# Suflor.me düzenli temizlik: yedek sürümleri, __pycache__, büyük günlükler, ses arşivi, ortak klasör, geri bildirim kutusu.
# Varsayılan kip yalnız rapordur (kuru koşu). --uygula verilince YALNIZ iki iş yapılır: sürüm yedeklerinin fazlası ve __pycache__
# Çöp Sepeti'ne taşınır (kalıcı silme yok), okunmuş eski geri bildirim raporları kutudaki arsiv/ alt klasörüne taşınır.
# Günlük, ses arşivi ve ortak klasör için hiçbir zaman değişiklik yapılmaz (aktarıcı yazıyor olabilir; saklama aktarıcının işi).
#   python3 -B temizlik.py                         kuru koşu raporu
#   python3 -B temizlik.py --uygula                taşı (toplantı/sohbet sürüyorsa durur)
#   python3 -B temizlik.py --json                  makine okunur özet
# Yollar değiştirilebilir (deneme için): --yedek-dizin --kod --ortak --cop --uygulama-dizin --ses-kok --okunan, ya da SUFLOR_TEMIZLIK_<AD> ortam değişkenleri.
import argparse, datetime, json, os, re, shutil, subprocess, sys, time
sys.dont_write_bytecode = True

KOD0 = os.path.dirname(os.path.abspath(__file__))
EV = os.path.expanduser("~")
DESTEK = os.path.join(EV, "Library", "Application Support")

# Ortak klasörde kod tarafından kullanılan üst düzey klasörler (kurulum.py, baglam.py, bas-konus.py, whisper-hat.py, golge-tstt.py vb.).
# Burada olmayan klasör "tanınmayan" diye yalnız raporlanır, hiçbir zaman taşınmaz.
ORTAK_BILINEN = {
    "whisper-modeller", "whisper-venv", "whisper-cpp", "cevir-modeller", "cevir-venv", "anlam-modeller", "ses-modeller",
    "smart-turn-venv", "tstt-model", "tstt-venv", "python312", "tts-deneme", "geri-bildirim", "pocket-venv", "pocket-modeller",
}
YEDEK_RX = re.compile(r"^(?P<taban>.+)-v(?P<sur>\d+(?:\.\d+)+)\.(?P<uz>[A-Za-z0-9]+)$")
GUN = 86400


def boyut_yaz(b):
    for ad, k in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if b >= k: return f"{b / k:.1f} {ad}"
    return f"{b} B"


def agac_boyu(yol):
    t = 0
    try:
        if os.path.isfile(yol) or os.path.islink(yol): return os.lstat(yol).st_size
        for k, _, fs in os.walk(yol):
            for f in fs:
                try: t += os.lstat(os.path.join(k, f)).st_size
                except OSError: pass
    except OSError: pass
    return t


def ayar_oku(yol):
    try: return json.load(open(yol, encoding="utf-8"))
    except Exception: return {}


def cop_ad(cop, ad):
    hedef = os.path.join(cop, ad)
    if not os.path.lexists(hedef): return hedef
    kok, uz = os.path.splitext(ad); ts = time.strftime("%Y%m%d-%H%M%S"); n = 0
    while True:
        hedef = os.path.join(cop, f"{kok}-{ts}" + (f"-{n}" if n else "") + uz)
        if not os.path.lexists(hedef): return hedef
        n += 1


def cope_tasi(yol, cop):
    os.makedirs(cop, exist_ok=True)
    shutil.move(yol, cop_ad(cop, os.path.basename(yol)))


def surum_anahtari(s):
    return tuple(int(x) for x in s.split("."))


# ---- kalemler: her biri {"kalem", "dosya", "bayt", "ayrinti", "yapilacak": [...yollar], "yapildi": 0} -------------------------------------------------

def kalem_yedek(yedek_dizin, sakla):
    gruplar = {}
    try: adlar = sorted(os.listdir(yedek_dizin))
    except OSError: adlar = []
    for ad in adlar:
        yol = os.path.join(yedek_dizin, ad)
        if os.path.islink(yol) or not os.path.isfile(yol): continue  # alt klasörlere ve bağlara dokunulmaz
        m = YEDEK_RX.match(ad)
        if not m: continue
        gruplar.setdefault((m["taban"], m["uz"]), []).append((surum_anahtari(m["sur"]), os.path.getmtime(yol), ad, yol))
    tasinacak, ozet = [], []
    for (taban, uz), l in sorted(gruplar.items()):
        l.sort(key=lambda x: (x[0], x[1]), reverse=True)  # en yeni sürüm başta (eşitse değişiklik zamanı)
        fazla = l[sakla:]
        if fazla:
            tasinacak += [x[3] for x in fazla]; ozet.append(f"{taban}.{uz}: {len(l)} → {min(len(l), sakla)}")
    return {"kalem": "yedek", "baslik": f"Sürüm yedekleri ({yedek_dizin}, her gruptan en yeni {sakla} kalır)", "toplam_grup": len(gruplar),
            "dosya": len(tasinacak), "bayt": sum(agac_boyu(y) for y in tasinacak), "yapilacak": tasinacak, "eylem": "cop",
            "ayrinti": ozet[:12] + ([f"… +{len(ozet) - 12} grup"] if len(ozet) > 12 else [])}


def kalem_pycache(kod):
    bul = []
    for k, ds, _ in os.walk(kod):
        ds[:] = [d for d in ds if d != ".git" and not os.path.islink(os.path.join(k, d))]
        for d in list(ds):
            if d == "__pycache__": bul.append(os.path.join(k, d)); ds.remove(d)
    return {"kalem": "pycache", "baslik": "__pycache__ (kod klasöründe olmamalı)", "dosya": len(bul), "bayt": sum(agac_boyu(y) for y in bul),
            "yapilacak": bul, "eylem": "cop", "ayrinti": [os.path.relpath(y, kod) for y in bul[:10]]}


def kalem_gunluk(dizinler, esik_mb, ekstra=()):
    esik = esik_mb * 1024 * 1024; bul = []
    for kok in dizinler:
        for k, ds, fs in os.walk(kok):
            ds[:] = [d for d in ds if not os.path.islink(os.path.join(k, d))]
            for f in fs:
                if f.endswith(".log"):
                    y = os.path.join(k, f)
                    try:
                        b = os.lstat(y).st_size
                        if b > esik: bul.append((y, b))
                    except OSError: pass
    for y in ekstra:
        try:
            b = os.lstat(y).st_size
            if b > esik and all(y != x[0] for x in bul): bul.append((y, b))
        except OSError: pass
    bul.sort(key=lambda x: -x[1])
    return {"kalem": "gunluk", "baslik": f"Büyük günlükler (> {esik_mb} MB; yalnız rapor, aktarıcı yazıyor olabilir)", "dosya": len(bul), "bayt": sum(b for _, b in bul),
            "yapilacak": [], "eylem": "yok", "ayrinti": [f"{boyut_yaz(b)}  {y}" for y, b in bul[:10]]}


def kalem_ses(kokler):
    toplam, n, en_eski, bulunan = 0, 0, None, []
    for ad, kok in kokler:
        if not os.path.isdir(kok): continue
        bulunan.append(ad)
        for k, _, fs in os.walk(kok):
            for f in fs:
                y = os.path.join(k, f)
                try: st = os.lstat(y)
                except OSError: continue
                toplam += st.st_size; n += 1; en_eski = st.st_mtime if en_eski is None else min(en_eski, st.st_mtime)
    ayr = [f"klasörler: {', '.join(bulunan) or 'yok'}", "saklama aktarıcının işi: ayar ses_arsivi_gun (14 gün) ve toplam sınır (aktarici/whisper-hat.py ses_arsivi_temizle); burada silinmez"]
    if en_eski: ayr.insert(1, "en eski dosya: " + datetime.datetime.fromtimestamp(en_eski).strftime("%Y-%m-%d"))
    return {"kalem": "ses_arsivi", "baslik": "Ses arşivi (yalnız rapor)", "dosya": n, "bayt": toplam, "yapilacak": [], "eylem": "yok", "ayrinti": ayr,
            "en_eski": datetime.datetime.fromtimestamp(en_eski).strftime("%Y-%m-%d") if en_eski else None}


def kalem_ortak(ortak, ayar_degerleri):
    bilinen = set(ORTAK_BILINEN)
    rx = re.compile(re.escape(os.path.normpath(ortak)) + r"/([^/\s\"']+)")  # ayarda adı geçen yollar (piper_model, pocket_hf vb.) da tanınır
    for v in ayar_degerleri:
        if isinstance(v, str): bilinen.update(rx.findall(v))
    tanin, topl = [], 0
    try: adlar = sorted(os.listdir(ortak))
    except OSError: adlar = []
    for ad in adlar:
        y = os.path.join(ortak, ad)
        if not os.path.isdir(y) or os.path.islink(y) or ad in bilinen or ad.startswith("."): continue
        b = agac_boyu(y); topl += b; tanin.append((ad, b))
    return {"kalem": "ortak", "baslik": f"Ortak klasörde tanınmayan üst düzey klasörler ({ortak}; asla taşınmaz)", "dosya": len(tanin), "bayt": topl,
            "yapilacak": [], "eylem": "yok", "ayrinti": [f"{ad}  {boyut_yaz(b)}" for ad, b in tanin], "klasorler": [{"ad": ad, "bayt": b} for ad, b in tanin]}


def rapor_tarihi(ad, yol):
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", ad)
    if m:
        try: return datetime.datetime(int(m[1]), int(m[2]), int(m[3])).timestamp()
        except ValueError: pass
    try: return os.path.getmtime(yol)
    except OSError: return time.time()


def kalem_kutu(kutu, okunan_yol, gun):
    try: okunan = set(json.load(open(okunan_yol, encoding="utf-8")))
    except Exception: okunan = set()
    esik = time.time() - gun * GUN; eski = []; tum = 0
    try: adlar = sorted(os.listdir(kutu))
    except OSError: adlar = []
    for ad in adlar:
        y = os.path.join(kutu, ad)
        if not ad.endswith(".md") or os.path.islink(y) or not os.path.isfile(y): continue
        tum += 1
        if ad in okunan and rapor_tarihi(ad, y) < esik: eski.append(y)
    return {"kalem": "geri_bildirim", "baslik": f"Geri bildirim kutusu ({kutu}): {gun} günden eski ve okunmuş raporlar → arsiv/", "dosya": len(eski),
            "bayt": sum(agac_boyu(y) for y in eski), "yapilacak": eski, "eylem": "arsiv", "arsiv": os.path.join(kutu, "arsiv"),
            "ayrinti": [f"kutuda {tum} rapor, okunmuş işaretli {len([a for a in adlar if a in okunan])}"] + [os.path.basename(y) for y in eski[:8]]}


# ---- çalıştırma ------------------------------------------------------------------------------------------------------------------------------

def mesgul_mu(kod):
    # kurulum.py mesgul(): toplantı, sohbet ya da Konuş cevabı sürüyorsa metin döner (CLI bölümü 0 ise boş). Aynı işlev, süreç olarak çağrılır.
    if "SUFLOR_TEMIZLIK_MESGUL" in os.environ: return os.environ["SUFLOR_TEMIZLIK_MESGUL"]  # deneme: değer verilir (boş = meşgul değil)
    try:
        r = subprocess.run([sys.executable, "-B", os.path.join(kod, "kurulum.py"), "mesgul"], capture_output=True, text=True, timeout=30, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if r.returncode != 0: return (r.stdout + r.stderr).strip() or f"kurulum.py mesgul çıkış {r.returncode}"
        return ""
    except Exception as e: return f"meşguliyet denetlenemedi ({e.__class__.__name__})"


def uygula(k, cop):
    n = 0
    for y in k["yapilacak"]:
        try:
            if k["eylem"] == "cop": cope_tasi(y, cop)
            elif k["eylem"] == "arsiv":
                os.makedirs(k["arsiv"], exist_ok=True); hedef = os.path.join(k["arsiv"], os.path.basename(y))
                if os.path.lexists(hedef): continue  # var olan arşiv dosyası ezilmez
                shutil.move(y, hedef)
            n += 1
        except OSError as e: k.setdefault("hatalar", []).append(f"{os.path.basename(y)}: {e.__class__.__name__}")
    k["yapildi"] = n


def main(argv=None):
    E = lambda ad, varsayilan: os.environ.get("SUFLOR_TEMIZLIK_" + ad) or varsayilan
    ap = argparse.ArgumentParser(description="Suflor.me temizlik (varsayılan: kuru koşu)")
    ap.add_argument("--uygula", action="store_true", help="taşı (yedek fazlası + __pycache__ → Çöp Sepeti; okunmuş eski raporlar → kutu/arsiv)")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--yedek-sakla", type=int, default=5)
    ap.add_argument("--gunluk-mb", type=int, default=50); ap.add_argument("--rapor-gun", type=int, default=90)
    ap.add_argument("--kod", default=E("KOD", KOD0)); ap.add_argument("--yedek-dizin", default=E("YEDEK", None))
    ap.add_argument("--ortak", default=E("ORTAK", None)); ap.add_argument("--cop", default=E("COP", os.path.join(EV, ".Trash")))
    ap.add_argument("--uygulama-dizin", action="append", help="günlük aranacak klasör (birden çok verilebilir)")
    ap.add_argument("--ses-kok", action="append", help="ses arşivi klasörü (ad=yol ya da yol)")
    ap.add_argument("--okunan", default=E("OKUNAN", os.path.join(DESTEK, "Suflor", "okunan-raporlar.json")))
    ap.add_argument("--ayar", default=E("AYAR", os.path.join(DESTEK, "Suflor", "ayar.json")))
    a = ap.parse_args(argv)
    ayar = ayar_oku(a.ayar)
    kod = os.path.abspath(os.path.expanduser(a.kod)); yedek = os.path.abspath(os.path.expanduser(a.yedek_dizin or os.path.join(kod, "..", "_yedek")))
    ortak = os.path.abspath(os.path.expanduser(a.ortak or ayar.get("ortak") or "/Users/Shared/Suflor"))
    uyg_ayar = os.path.expanduser(str(ayar.get("uygulama") or os.path.join(DESTEK, "Suflor")))
    gdizin = [os.path.expanduser(x) for x in a.uygulama_dizin] if a.uygulama_dizin else sorted({os.path.join(DESTEK, "Suflor"), uyg_ayar})  # uygulama klasörü ayardan (hesaba göre farklı olabilir)
    ekstra = [] if a.uygulama_dizin else [os.path.join(EV, "Library", "Logs", f) for f in ("suflor-aktarici.log", "suflor-konus.log", "suflor-kurulum.log", "suflor-menu.log", "suflor-menu-hata.log", "suflor-ses.log")]
    if a.ses_kok: kokler = [(x.split("=", 1)[0], x.split("=", 1)[1]) if "=" in x else (os.path.basename(x), x) for x in a.ses_kok]
    else:
        canli = os.path.join(uyg_ayar, "canli"); kokler = [("ses-arsivi", os.path.join(canli, "ses-arsivi")), ("egitim-havuzu", os.path.join(canli, "egitim-havuzu"))]
    kalemler = [kalem_yedek(yedek, a.yedek_sakla), kalem_pycache(kod), kalem_gunluk(gdizin, a.gunluk_mb, ekstra), kalem_ses(kokler),
                kalem_ortak(ortak, list(ayar.values())), kalem_kutu(os.path.join(ortak, "geri-bildirim"), a.okunan, a.rapor_gun)]
    sonuc = {"kip": "uygula" if a.uygula else "kuru-kosu", "zaman": datetime.datetime.now().isoformat(timespec="seconds"), "durdu": None, "kalemler": kalemler}
    if a.uygula:
        m = mesgul_mu(kod)
        if m: sonuc["durdu"] = "meşgul: " + m
        else:
            for k in kalemler:
                if k["eylem"] != "yok": uygula(k, a.cop)
    if a.json:
        print(json.dumps(sonuc, ensure_ascii=False, indent=1)); return 2 if sonuc["durdu"] else 0
    print(f"Suflor.me temizlik — {'UYGULA' if a.uygula else 'kuru koşu (hiçbir şey taşınmadı)'} · {sonuc['zaman']}")
    if sonuc["durdu"]: print(f"DURDU: {sonuc['durdu']}; hiçbir şey taşınmadı.")
    for k in kalemler:
        if k["eylem"] == "yok": son = "yalnız rapor"
        elif sonuc["durdu"]: son = "dokunulmadı (durdu)"
        elif a.uygula: son = f"{k['yapildi']} öğe " + ("Çöp Sepeti'ne taşındı" if k["eylem"] == "cop" else "arsiv/'e taşındı")
        else: son = f"{k['dosya']} öğe " + ("çöpe taşınacaktı" if k["eylem"] == "cop" else "arsiv/'e taşınacaktı")
        print(f"\n- {k['baslik']}\n  {k['dosya']} öğe, {boyut_yaz(k['bayt'])} · {son}")
        for s in k["ayrinti"]: print(f"    {s}")
        for h in k.get("hatalar", []): print(f"    HATA: {h}")
    return 2 if sonuc["durdu"] else 0


if __name__ == "__main__":
    sys.exit(main())
