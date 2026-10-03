#!/usr/bin/env python3
# Suflor.me — toplantı sırasında Claude Code oturumunun kullandığı yardımcı (v0.7.3). Yalnız 127.0.0.1 ve yerel dosya.
#   izle  : transkript/not/soru/kart olaylarını satır satır yazar (Claude Code "Monitor" aracıyla izlenir)
#   kart  : panoya / mini panoya / Teams şeridine kart gönderir (kart-anahtari.txt ile)
#   olcum : gecikme raporu (v0.4.6) — eklenti sabitlemesi, SORU→CEVAP, HAZIR tetik→kart
#   ara   : proje + geçmiş toplantı araması (v0.5.0, baglam.py) — SORU gelince izle ilk 3 sonucu kendisi ekler
#   hazir : hazir.json'daki önceden yazılmış kartı gönderir (v0.4.5); izle, tetik kelimesi geçince "HAZIR hN" yazar
#   acik  : cevapsız kalan soruyu kaydeder/kapatır (v0.6.0); izle, tetik yeniden geçince "AÇIK SORU aN" yazar
#   gundem: gündem maddesini işaretler (v0.6.0) — kalan süre/kayma hesabı ve pano bunu kullanır
#   kanit : toplantının kanıt ekran görüntülerini listeler / açıklama yazar (v0.7.0); izle her yenisinde "KANIT n" yazar
#   karne : toplantı sonu kısa başarı değerlendirmesi, 1–5 not (v0.7.0); --kaydet ile karneler.jsonl'e
#   hazirlik: toplantı öncesi bağlam paketi — kişi + gündem maddesi aramaları, önceki cevapsız sorular (v0.7.0)
#   karsilastir: Teams'in indirilen dökümü (.vtt/.docx/.txt) ile Suflor dökümü — kaçan satır, konuşmacı uyumu (v0.7.2)
# Örnek:
#   PYTHONDONTWRITEBYTECODE=1 python3 toplanti-claude.py izle
#   python3 toplanti-claude.py kart sor "Ayşe'ye yedeklerin nerede tutulduğunu sor" --neden "Gündem 1'de geçmedi" --gundem 0
#   python3 toplanti-claude.py kart cevap "…" --cevap q1790705538130
#   python3 toplanti-claude.py hazir h3            (SORU'ya cevapsa: hazir h3 --cevap q…)
# hazir.json biçimi: {"toplanti": "…", "kartlar": [{"id": "h1", "gundem": 0, "tetik": ["root", "mfa"],
#   "tur": "sor", "metin": "…", "neden": "…"}]}  — tetik: küçük harf, kelime/ifade; biri satırda geçerse eşleşir
import argparse, subprocess, datetime, json, math, os, re, statistics, sys, time, urllib.request
sys.dont_write_bytecode = True  # baglam.py içe aktarılınca eklenti klasöründe __pycache__ oluşmasın (Chrome yüklemez)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# v0.9.2: hesap başına ayar (relay.py ile aynı kural): ~/Library/Application Support/Suflor/ayar.json; yoksa varsayılanlar
AYAR_YOL = os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")  # SUFLOR_AYAR: deneme için
def ayar_oku():
    v = {"alan": "Suflor", "ad": "", "port": 8765, "uygulama": "~/Library/Application Support/Suflor", "proje": "~/Suflor", "ortak": "/Users/Shared/Suflor",
         "sozluk_kaynagi": None}
    try: v.update(json.load(open(AYAR_YOL, encoding="utf-8")))
    except (OSError, ValueError): pass
    for k in ("uygulama", "proje", "ortak"): v[k] = os.path.expanduser(str(v[k]))
    return v
AYAR = ayar_oku()
# v0.10.0: kullanıcının adı ayardan (olay etiketleri "NOT (<ad>)"); kanal kimliği "ben" — eski kayıtlardaki kanal adı (adın küçük
# harfli ilk sözcüğü) ve sözlükteki eski "kaynak" değeri de aynı kişi sayılır
BEN = (str(AYAR.get("ad") or "").split() or ["Kullanıcı"])[0]
BEN_ESKI = {"ben", "kullanici", BEN.lower()}
def kanal_n(k): return "ben" if k in BEN_ESKI else k
def elle_mi(t): return t.get("kaynak") in BEN_ESKI
DEF_DIR = os.path.join(AYAR["uygulama"], "canli")
ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=DEF_DIR); ap.add_argument("--relay", default=f"http://127.0.0.1:{AYAR['port']}")
sub = ap.add_subparsers(dest="cmd", required=True)
# v0.4.7: 5 sn / 4 satır → 20 sn / 30 satır. 30 Eylül testinde 461 olay üretildi, Claude her birine yazdı ve
# SORU'lar kuyrukta kaldı (ortanca 34 sn, en kötü 218 sn). SORU artık beklemez: biriken satırlarla birlikte hemen gider.
iz = sub.add_parser("izle"); iz.add_argument("--aralik", type=int, default=20, help="satırları en geç kaç sn'de bir toplu yaz")
iz.add_argument("--paket", type=int, default=30, help="bu kadar satır birikince beklemeden yaz")
ka = sub.add_parser("kart"); ka.add_argument("tur", choices=["sor", "belirt", "deginme", "dikkat", "cevap", "bilgi", "duygu"])
ka.add_argument("metin"); ka.add_argument("--neden", default=""); ka.add_argument("--cevap", default=None, help="cevaplanan soru kimliği (q…)")
ka.add_argument("--gundem", type=int, default=None, help="ilgili gündem maddesinin sırası (0'dan)")
ka.add_argument("--ton", choices=["olumlu", "notr", "gergin", "olumsuz", "ilgili", "heyecanli", "tedirgin", "savunmada", "ilgisiz", "kararsiz"], default=None,
                help="duygu kartı: konuşmanın ya da (--kim ile) kişinin tonu (tahmin; v0.8.2: kişi etiketleri)")
ka.add_argument("--kim", default=None, help="v0.8.2: duygu kartı bu kişi için (pano başlığında kişi başına etiket)")
ol = sub.add_parser("olcum"); ol.add_argument("dosya", nargs="?", help="toplantı .md/.jsonl adı (yoksa en yenisi)")
ar = sub.add_parser("ara", help="v0.5.0: proje + geçmiş toplantı araması (baglam.py)"); ar.add_argument("sorgu")
ar.add_argument("--kim"); ar.add_argument("--tur", help="virgüllü: toplanti,gorusme,analiz,sunum,tablo,belge")
ar.add_argument("--son", type=int, help="son N gün"); ar.add_argument("--n", type=int, default=8)
sz = sub.add_parser("sozluk", help="v0.5.1: özel sözlük — listele ya da ekle (aktarıcı dosya değişince kendiliğinden yükler)")
sz.add_argument("--ekle", nargs=2, metavar=("YANLIS", "DOGRU"), help="yanlış biçim ve doğru ad; kullanıcı onaylamadan ekleme")
sz.add_argument("--baglam", default="", help="virgüllü: yalnız aynı satırda bu kelimelerden biri varsa düzelt (gerçek kelime olabilen biçimler için)")
sz.add_argument("--not", dest="aciklama", default="")
sz.add_argument("--birlestir", action="store_true", help="v0.5.2: ayardaki sözlük kaynağından (tsv + xlsx Vendor sekmesi) yeniden kur; --ekle ile eklenenler korunur")
ac = sub.add_parser("acik", help="v0.6.0: cevapsız sorular — liste | ekle \"soru\" --tetik a,b | kapat aN")
ac.add_argument("islem", nargs="?", default="liste", choices=["liste", "ekle", "kapat", "sifirla"]); ac.add_argument("deger", nargs="?")
ac.add_argument("--tetik", default="", help="virgüllü, küçük harf: konu yeniden açılınca geçecek ayırt edici kelimeler")
ac.add_argument("--kim", default=""); ac.add_argument("--gundem", type=int, default=None)
ac.add_argument("--durum", default="cevaplandi", choices=["cevaplandi", "gecildi"], help="kapat: cevaplandı mı, konu mu kapandı")
gu = sub.add_parser("gundem", help="v0.6.0: gündem maddesini işaretle (0'dan); --geri işareti kaldırır"); gu.add_argument("i", type=int)
gu.add_argument("--geri", action="store_true")
kn = sub.add_parser("kanit", help="v0.7.0: kanıt listesi | kanit N --aciklama \"…\""); kn.add_argument("n", nargs="?", type=int)
kn.add_argument("--aciklama", default=None); kn.add_argument("--dosya", default=None)
kr = sub.add_parser("karne", help="v0.7.0: toplantı karnesi (1–5 not)"); kr.add_argument("dosya", nargs="?")
kr.add_argument("--takip", default=None, help="takip işleri: toplam/sahipli (ör. 6/5) — Claude özetten sayar")
kr.add_argument("--karar", type=int, default=None, help="çıkan karar sayısı"); kr.add_argument("--kaydet", action="store_true", help="karneler.jsonl'e ekle")
kr.add_argument("--gecmis", action="store_true", help="son karneler")
hl = sub.add_parser("hazirlik", help="v0.7.0: toplantı öncesi bağlam paketi"); hl.add_argument("--kim", default=None); hl.add_argument("--n", type=int, default=3)
ks = sub.add_parser("karsilastir", help="v0.7.2: Teams dökümü (.vtt/.docx/.txt) ile Suflor.me dökümünü karşılaştır")
ks.add_argument("teams", help="Teams'ten indirilen döküm dosyası"); ks.add_argument("dosya", nargs="?", help="Suflor.me .md/.jsonl (yoksa en yenisi)")
ks.add_argument("--n", type=int, default=12, help="en çok kaç kaçan bölüm listelensin"); ks.add_argument("--kaydet", action="store_true")
kz = sub.add_parser("kesinlik", help="v0.8.3: toplantıda kesin söylenmeyen iddialar (özet için)"); kz.add_argument("dosya", nargs="?", help="toplantı .md (yoksa en yenisi)")
kc = sub.add_parser("koc", help="v0.8.3: kullanıcının konuşma koçluğu (toplantı sonu)"); kc.add_argument("dosya", nargs="?")
an = sub.add_parser("anlar", help="v0.8.3: öne çıkan anlar (toplantı sonu)"); an.add_argument("dosya", nargs="?"); an.add_argument("--n", type=int, default=5)
sg = sub.add_parser("saglik", help="v0.8.5: toplantı öncesi sağlık kontrolü (aktarıcı, eklenti sürümü, Whisper, ses modeli, bellek, disk)")
tk = sub.add_parser("takvim", help="v0.9.3: Mac Takvim'den sıradaki toplantılar (davet notu, katılımcılar); --id ile tek toplantı")
tk.add_argument("--id", default=None); tk.add_argument("--n", type=int, default=6)
rp = sub.add_parser("rapor", help="v0.9.9: geliştiriciye geri bildirim — içeriksiz paket (sürüm, ölçüm, kart dönüşleri, günlük, gözlemler) → <ortak>/geri-bildirim")
rp.add_argument("dosya", nargs="?", help="toplantı .md (yoksa en yenisi)"); rp.add_argument("--not", dest="notlar", default="", help="sorunlar, öneriler (Claude'un ve kullanıcının gözlemleri; toplantı içeriği yazma)")
rp.add_argument("--github", action="store_true", help="ayrıca GitHub'da konu (issue) aç (gh oturumu gerekir)"); rp.add_argument("--goster", action="store_true", help="kaydetmeden yazdır")
gb = sub.add_parser("geri-bildirim", help="v0.9.9: geliştirici tarafı — ortak klasördeki raporlar; --yeni yalnız okunmamışlar, --okundu işaretler")
gb.add_argument("--yeni", action="store_true"); gb.add_argument("--okundu", action="store_true")
hz = sub.add_parser("hazir"); hz.add_argument("hid", help="hazir.json'daki kart kimliği (h1, h2…)")
hz.add_argument("--cevap", default=None, help="SORU'ya cevap olarak gönder (q…); tür cevap olur")
A = ap.parse_args()

def get(path):
    # v0.9.1: izle kendini bildirir → panoda "Claude izliyor" noktası (yalnız /status'ta kullanılır)
    # v0.9.3: yalnız izle bildirir (takvim/saglik gibi tek seferlik komutlar "Claude izliyor" saymasın — panodan başlatmayı kilitler)
    return json.load(urllib.request.urlopen(urllib.request.Request(A.relay + path, headers={"X-Suflor-Istemci": "izle"} if A.cmd == "izle" else {}), timeout=3))

def hazir_yukle():
    try: return json.load(open(os.path.join(A.dir, "hazir.json"), encoding="utf-8")).get("kartlar", [])
    except FileNotFoundError: return []

def hazir():
    h = next((h for h in hazir_yukle() if h.get("id") == A.hid), None)
    if not h: sys.exit(f"hazir.json'da {A.hid} yok")
    A.tur = "cevap" if A.cevap else h.get("tur", "bilgi"); A.metin = h["metin"]; A.neden = h.get("neden", "")
    A.gundem = h.get("gundem"); A.ton = None
    cid = kart()
    olcum_yaz({"t": "hazir-gonder", "hid": A.hid, "card_id": cid, "card_at": simdi()})

PROJE = AYAR["proje"]  # v0.9.2: hesabın proje (bağlam) klasörü
# Dış sözlük kaynağı (ayar sozluk_kaynagi: tsv + xlsx) isteğe bağlı; yoksa birleştirme "kaynak yok" der
SOZ_TSV = os.path.join(PROJE, AYAR.get("sozluk_kaynagi") or "-", "duzeltme_sozlugu_oneri.tsv")
SOZ_XLSX = os.path.join(PROJE, AYAR.get("sozluk_kaynagi") or "-", AYAR.get("sozluk_xlsx") or "-")
# Dış sözlük görüşme dökümleri için kurulmuş olabilir; canlı toplantıda bazı "toplu" biçimler gerçek kelime ya da ad da
# olabiliyor → Suflor bunları yalnız aynı satırda bağlam kelimesi varsa düzeltir (daha sıkı, hiçbir zaman daha gevşek).
SIKI = AYAR.get("sozluk_siki") or {}
ATLA = set(AYAR.get("sozluk_atla") or [])
DOGRU_SADE = AYAR.get("sozluk_dogru_sade") or {}
# Alanın kendi ekleri ve kişi notları ayardan (sozluk_ek, kisiler); yalnız canlı asistan kullanır
SUFLOR_EK = [tuple(x) for x in AYAR.get("sozluk_ek") or []]  # (doğru, [yanlışlar], kip, [bağlam], not)
KISILER = AYAR.get("kisiler") or []  # yalnız okuma: takma adlar, karıştırılmaması gerekenler
def _sb(x): return " ".join(baglam_norm(x).split())
def baglam_norm(x):
    import unicodedata
    return "".join("i" if c in "İIı" else (unicodedata.normalize("NFKD", c)[:1] or c).lower() for c in str(x))
def elle_oncelik(oto, elle):
    # v0.7.3: kullanıcının eklediği biçim otomatik terimlerden çıkarılır (dış sözlük başka ada bağlasa da kullanıcının kararı geçer)
    mb = {_sb(y) for t in elle for y in t.get("yanlis", [])}
    out = []
    for t in oto:
        t = dict(t, yanlis=[y for y in t["yanlis"] if _sb(y) not in mb])
        if t["yanlis"]: out.append(t)
    return out
def sozluk_birlestir(d):
    import csv, re as _re
    sys.dont_write_bytecode = True; import baglam
    kor = []
    for x in csv.DictReader(open(SOZ_TSV, encoding="utf-8"), delimiter="\t"):
        uy = (x.get("uygulama") or "").strip(); dg = _re.split(r"\s*\(", (x.get("dogru_bicim") or x.get("onerilen_dogru_bicim") or "").strip())[0].strip()
        if uy == "uygulanmaz" or not dg: continue
        dg = DOGRU_SADE.get(dg, dg); bic = [b.strip() for b in x["hatali_bicimler"].split("|") if b.strip() and "[" not in b]
        for b in bic:
            if b.lower() in ATLA: continue
            sk = SIKI.get(b.lower()); kip = "isaret" if uy == "baglama_bakarak" else ("baglam" if sk else "duzelt")
            kor.append((dg, b, kip, sk or [], f"dış sözlük: {uy}"))
    grup = {}
    for dg, b, kip, bag, nt in kor + [(dg, y, kip, bag, nt) for dg, ys, kip, bag, nt in SUFLOR_EK for y in ys]:
        k = (dg, kip, tuple(bag)); t = grup.setdefault(k, {"dogru": dg, "yanlis": [], "kip": kip, "baglam": list(bag), "not": nt, "kaynak": "otomatik"})
        if b not in t["yanlis"]: t["yanlis"].append(b)
    elle = [t for t in d.get("terimler", []) if elle_mi(t)]
    grup = elle_oncelik(list(grup.values()), elle)
    vendor = []
    try:
        for k, _, m in baglam.xlsx_parcala(SOZ_XLSX):
            if k.startswith("Vendor!"):
                ad = m.split(" — ", 1)[-1].split(" · ")[0]; vendor += [a.strip() for a in ad.split(":") if a.strip()]
    except Exception as e: print(f"Vendor listesi okunamadı: {e.__class__.__name__}")
    return {"surum": 2, "guncelleme": datetime.date.today().isoformat(),
            "aciklama": "Suflor.me özel sözlüğü. duzelt: her geçiş düzeltilir · baglam: yalnız aynı satırda bağlam kelimesi varsa · isaret: düzeltilmez, '?' işareti. Kaynak: ayardaki sozluk_kaynagi (sozluk --birlestir ile yeniden kurulur) + elle eklenenler (kaynak=kullanici).",
            "kaynak_mtime": max(os.path.getmtime(SOZ_TSV), os.path.getmtime(SOZ_XLSX)),
            "terimler": grup + elle, "vendor": sorted(dict.fromkeys(vendor)), "kisiler": KISILER}
def sozluk_cmd():
    fp = os.path.join(A.dir, "sozluk.json")
    try: d = json.load(open(fp, encoding="utf-8"))
    except FileNotFoundError: d = {"surum": 1, "terimler": []}
    if A.birlestir:
        d = sozluk_birlestir(d); tmp = fp + ".tmp"
        json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, fp)
        say = {}
        for t in d["terimler"]: say[t["kip"]] = say.get(t["kip"], 0) + len(t["yanlis"])
        print(f"sözlük kuruldu: {len(d['terimler'])} terim · biçim {say} · vendor {len(d['vendor'])} · kişi notu {len(d['kisiler'])}")
        return
    if A.ekle:
        y, dg = A.ekle; bag = [b.strip() for b in A.baglam.split(",") if b.strip()]; kip = "baglam" if bag else "duzelt"
        # v0.7.3: yalnız kullanıcının terimine ekle — otomatik terime eklenen biçim --birlestir'de siliniyordu
        t = next((t for t in d["terimler"] if elle_mi(t) and t.get("dogru") == dg and t.get("kip", "duzelt") == kip and t.get("baglam", []) == bag), None)
        if t is None: t = {"dogru": dg, "yanlis": [], "kip": kip, "baglam": bag, "not": A.aciklama, "kaynak": "kullanici"}; d["terimler"].append(t)
        if y not in t["yanlis"]: t["yanlis"].append(y)
        d["terimler"] = elle_oncelik([x for x in d["terimler"] if not elle_mi(x)], [x for x in d["terimler"] if elle_mi(x)]) \
            + [x for x in d["terimler"] if elle_mi(x)]
        d["guncelleme"] = datetime.date.today().isoformat(); tmp = fp + ".tmp"
        json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, fp)
        print(f"eklendi: {y} → {dg} ({kip}{': ' + ', '.join(bag) if bag else ''})")
        return
    for t in d["terimler"]:
        print(f"{t['dogru']:<18} {'·'.join(t.get('yanlis', []))}" + (f"   [bağlam: {', '.join(t['baglam'])}]" if t.get("kip") == "baglam" else "") + ("   [yalnız işaret]" if t.get("kip") == "isaret" else ""))
    if d.get("vendor"): print(f"vendor ({len(d['vendor'])}): " + ", ".join(d["vendor"]))
    for k in d.get("kisiler", []): print("kişi: " + k)
    try:
        if os.path.getmtime(SOZ_TSV) > d.get("kaynak_mtime", 0): print("UYARI: sözlük kaynağı daha yeni — sozluk --birlestir çalıştır")
    except OSError: pass
def ara_cmd():
    import baglam
    r = baglam.ara(A.sorgu, A.kim, A.tur.split(",") if A.tur else None, A.son, A.n); baglam.yaz(r, A.sorgu, r[1])
def soru_baglam(text, n=3):
    # v0.5.0: SORU gelince ilk sonuçlar olayla birlikte gider — Claude ayrı arama yapmadan cevaplayabilsin
    try:
        import baglam, io, contextlib
        r = baglam.ara(text, n=n); buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()): baglam.yaz(r, text, r[1])
        return ["  BAĞLAM (proje araması, ilk %d; yetmezse: ara \"…\"):" % n] + ["    " + l for l in buf.getvalue().splitlines()]
    except Exception as e: return [f"  BAĞLAM: arama yapılamadı ({e.__class__.__name__})"]
def simdi(): return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
def olcum_yaz(r):
    with open(os.path.join(A.dir, "olcum.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(r, ensure_ascii=False) + "\n")
def zaman(t):  # "…Z" (eklenti, UTC) ya da saat dilimsiz yerel (aktarıcı) → karşılaştırılabilir an
    if not t: return None
    d = datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
    return d if d.tzinfo else d.astimezone()

def olcum():
    jls = sorted((f for f in os.listdir(A.dir) if f.endswith(".jsonl") and f[:2] == "20"), key=lambda f: os.path.getmtime(os.path.join(A.dir, f)))
    f = (A.dosya.replace(".md", ".jsonl") if A.dosya else (jls[-1] if jls else None))
    if not f: sys.exit("toplantı dosyası yok")
    rows = [json.loads(l) for l in open(os.path.join(A.dir, f), encoding="utf-8") if l.strip()]
    md = f.replace(".jsonl", ".md")
    def rapor(ad, xs):
        xs = sorted(x for x in xs if x is not None)
        if not xs: print(f"{ad}: veri yok"); return
        p90 = xs[min(len(xs) - 1, int(len(xs) * 0.9))]
        print(f"{ad}: n={len(xs)} · ortanca {statistics.median(xs):.1f} sn · %90 {p90:.1f} sn · en kötü {xs[-1]:.1f} sn")
    print(f"Dosya: {f}")
    for ms in sorted({r.get("stableMs") for r in rows if r.get("chg")}, key=lambda x: x or 0):
        grp = [r for r in rows if r.get("chg") and r.get("stableMs") == ms]
        rapor(f"Eklenti, son değişme → aktarım (sabitleme {ms/1000:g} sn)", [(zaman(r["at"]) - zaman(r["chg"])).total_seconds() for r in grp])
        rapor(f"Eklenti, ilk görülme → aktarım (sabitleme {ms/1000:g} sn)", [(zaman(r["at"]) - zaman(r["seen"])).total_seconds() for r in grp])
    if not any(r.get("chg") for r in rows): print("Eklenti: bu dosyada ölçüm alanı yok (v0.4.6 öncesi)")
    wh = [r for r in rows if r.get("src") == "whisper"]
    if wh:  # v0.8.1: taslak ilk görülme → Whisper satırının yazılması (panoda taslağın kesin metinden ne kadar önce göründüğü)
        rapor("Taslak → kesin metin (Whisper)", [(zaman(r["at"]) - zaman(r["taslak"])).total_seconds() for r in wh if r.get("taslak") and r.get("at")])
        print(f"Whisper satırı: {len(wh)} · taslağı olan: {sum(1 for r in wh if r.get('taslak'))}")
    def jl(name):
        try: rs = [json.loads(l) for l in open(os.path.join(A.dir, name), encoding="utf-8") if l.strip()]
        except FileNotFoundError: return []
        byid = {r["id"]: r for r in rs if "text" in r}  # v0.6.0: bekleyen kaydın dosyası sonradan yama satırıyla gelir
        for r in rs:
            if "text" not in r and "file" in r and r.get("id") in byid: byid[r["id"]]["file"] = r["file"]
        return rs
    qs = {q["id"]: q for q in jl("sorular.jsonl") if q.get("file") == md}
    cards = [c for c in jl("kartlar.jsonl") if "text" in c and c.get("file") == md]
    rapor("SORU → CEVAP kartı", [(zaman(c["at"]) - zaman(qs[c["reply_to"]]["at"])).total_seconds() for c in cards if c.get("reply_to") in qs])
    om = jl("olcum.jsonl"); ids = {c["id"] for c in cards}
    tet = {o["hid"]: o for o in om if o.get("t") == "hazir-tetik" and o.get("file") == md}
    rapor("HAZIR tetik satırı → kart", [(zaman(o["card_at"]) - zaman(tet[o["hid"]]["row_at"])).total_seconds() for o in om if o.get("t") == "hazir-gonder" and o.get("card_id") in ids and o.get("hid") in tet])
    print(f"Kart: {len(cards)} · tür: " + ", ".join(f"{k} {sum(c['kind'] == k for c in cards)}" for k in sorted({c['kind'] for c in cards})))

ACIK_FP = lambda: os.path.join(A.dir, "acik.json")
def acik_yukle():
    try: return json.load(open(ACIK_FP(), encoding="utf-8"))
    except FileNotFoundError: return {"sorular": []}
def acik_cmd():
    d = acik_yukle(); qs = d.setdefault("sorular", [])
    if A.islem == "ekle":
        if not A.deger: sys.exit("soru metni gerekli")
        n = 1 + max([int(q["id"][1:]) for q in qs if str(q.get("id", "")).startswith("a") and q["id"][1:].isdigit()] or [0])
        q = {"id": f"a{n}", "at": simdi(), "metin": " ".join(A.deger.split())[:200], "tetik": [kucuk(t.strip()) for t in A.tetik.split(",") if t.strip()],
             "kim": A.kim, "gundem": A.gundem, "durum": "acik"}
        try: q["file"] = get("/status").get("file")  # v0.7.0: karne ve sonraki hazırlık hangi toplantıda sorulduğunu bilsin
        except Exception: pass
        qs.append(q)
    elif A.islem == "sifirla":
        # v0.7.0: yeni toplantıdan önce — eskiden acik.json silinirdi; artık acik-arsiv.jsonl'e taşınır, hazirlik
        # aynı kişiyle bir sonraki toplantıda cevapsız kalanları gösterir
        try: baslik = json.load(open(os.path.join(A.dir, "agenda.json"), encoding="utf-8")).get("title", "")
        except Exception: baslik = ""
        if qs:
            with open(os.path.join(A.dir, "acik-arsiv.jsonl"), "a", encoding="utf-8") as f:
                for q in qs: f.write(json.dumps(dict(q, arsiv_at=simdi(), toplanti=q.get("toplanti") or baslik), ensure_ascii=False) + "\n")
        print(f"{len(qs)} soru arşive taşındı ({sum(q.get('durum') == 'acik' for q in qs)} cevapsız)"); d["sorular"] = []; qs = d["sorular"]
    elif A.islem == "kapat":
        q = next((q for q in qs if q.get("id") == A.deger), None)
        if not q: sys.exit(f"acik.json'da {A.deger} yok")
        q["durum"] = A.durum; q["kapandi"] = simdi()
    if A.islem != "liste":
        tmp = ACIK_FP() + ".tmp"; json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, ACIK_FP())
    for q in qs:
        if A.islem == "liste" or q is qs[-1] or q.get("id") == A.deger:
            print(f"{q['id']} [{q.get('durum')}] {q.get('metin')}" + (f" — {q['kim']}" if q.get("kim") else "") + (f"   tetik: {', '.join(q['tetik'])}" if q.get("tetik") else ""))
def gundem_cmd():
    try: items = json.load(open(os.path.join(A.dir, "agenda.json"), encoding="utf-8")).get("items", [])
    except FileNotFoundError: items = []
    if not 0 <= A.i < len(items): sys.exit(f"gündemde {A.i} yok (0–{len(items) - 1})")
    req = urllib.request.Request(A.relay + "/agenda-tick", data=json.dumps({"i": A.i, "v": not A.geri, "label": items[A.i] + " (Claude)"}).encode(), method="POST")
    urllib.request.urlopen(req, timeout=3); print(f"gündem {A.i} {'işaret kaldırıldı' if A.geri else 'bitti işaretlendi'}: {items[A.i]}")

# v0.6.0: soru gibi görünen satır (cevapsız soru takibi için izle "❓" koyar; anlamı Claude çıkarır)
SORU_RX = re.compile(r"\?\s*$|\bm[iıuü](s[iıuü]n(?:[iıuü]z)?|y[iıuü]z|y[iıuü]m|yd[iıuü])?\b|\b(kim|neden|niye|nasıl|nerede|nereden|nereye|hangi|hangisi|kaç|ne zaman)\b|^(ne|what|who|when|where|why|how|which|do you|did you|can you|could you|is there|are there)\b", re.I)
def soru_mu(t): return bool(SORU_RX.search(kucuk(t.strip())))
def satir(r): return f"  [{r.get('time') or ''} {r.get('speaker') or '?'}] {'❓ ' if soru_mu(r.get('text','')) else ''}{'↻ ' if r.get('revised') else ''}{r.get('text','')}"
def son_satirlar(jl, sn=75, en_az=4, en_cok=40):
    # "Son 1 dk" özeti için: son sn saniyede aktarılan satırlar (aynı kimliğin son hâli); azsa son en_az satır
    try: rs = [json.loads(l) for l in open(jl, encoding="utf-8") if l.strip()]
    except FileNotFoundError: return []
    rs = [r for r in rs if "note" not in r and "kanit" not in r]; son = {}
    for r in rs: son[r.get("id") or id(r)] = r
    rs = list(son.values()); sinir = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=sn)
    yeni = [r for r in rs if r.get("at") and zaman(r["at"]) >= sinir]
    return (yeni if len(yeni) >= en_az else rs[-en_az:])[-en_cok:]

def tetik_var(t, low):  # v0.7.3: tetik kelime başında aranır (".env" "bakıyorum.Envantere"nin içinde eşleşiyordu); ek serbest ("repo" → "reposunda")
    return bool(t) and re.search(r"(?<!\w)" + re.escape(t), low) is not None
def kucuk(t):  # Türkçe küçük harf: "İ"→"i", "I"→"ı" (Python lower() "İ"yi iki karaktere böler)
    return t.replace("İ", "i").replace("I", "ı").lower()

def kart():
    key = open(os.path.join(A.dir, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    body = {"kind": A.tur, "text": A.metin, "why": A.neden}
    if A.cevap: body["reply_to"] = A.cevap
    if A.gundem is not None: body["agenda_i"] = A.gundem
    if A.ton: body["ton"] = A.ton
    if getattr(A, "kim", None) and A.tur == "duygu": body["kim"] = A.kim
    req = urllib.request.Request(A.relay + "/card", data=json.dumps(body).encode(), method="POST",
                                 headers={"X-Suflor-Anahtar": key, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=3)); c = r.get("card") or {}
    print(f"kart gönderildi: {c.get('id')} [{c.get('kind')}] {c.get('text')}")
    return c.get("id")

class Tail:
    # bir jsonl dosyasını kaldığı yerden okur; dosya kısalırsa/değişirse baştan
    def __init__(self, path, from_end=True):
        self.path = path; self.pos = os.path.getsize(path) if (from_end and os.path.exists(path)) else 0
    def new(self):
        try:
            size = os.path.getsize(self.path)
            if size < self.pos: self.pos = size  # v0.4.9: aktarıcı disk dolunca yarım eki geri keser; baştan okuyup her şeyi yeniden yazma
            with open(self.path, encoding="utf-8") as f:
                f.seek(self.pos); data = f.read(); self.pos = f.tell()
        except FileNotFoundError: return []
        out = []
        for raw in data.splitlines():
            try: out.append(json.loads(raw))
            except Exception: pass
        return out

def emit(*lines):
    for l in lines: print(l, flush=True)

# --- v0.7.0: kendiliğinden bağlam ------------------------------------------------------------------------------
# Konuşmada bir sistem adı geçince (SistemKatalogu + sözlük) izle, o satırların ayırt edici kelimeleriyle projede arar
# ve ilk 2 sonucu pakete ekler — Claude çelişkiyi SORU beklemeden görür (Suflor'un asıl farkı: proje bağlamı).
# Aynı sistem 10 dk'da bir; pakette en çok 2 sistem; süren toplantının kendi dosyası sonuçlardan çıkarılır.
KATALOG = os.path.join(PROJE, AYAR.get("sistem_katalogu") or "-")  # v0.9.2: alanın sistem tablosu (SistemKatalogu sekmesi)
PLATFORM_AD = {"teams": "Teams", "meet": "Google Meet", "zoom": "Zoom"}  # v0.9.0: eklenti ping'indeki platform → görünen ad
GENEL = {"not", "kagit", "banka", "lokal", "kendi", "tarayici", "sifre", "vendor", "komisyon", "finansman", "yapay", "teams",
         "microsoft 365", "google", "meta", "uygulamalar", "password", "token", "api", "api anahtarlari", "ceo", "chrome profili"} \
        | set(AYAR.get("sistem_genel") or [])  # ayar: alanın katalogundaki genel adlar
GENEL_ILK = {"not", "kagit", "banka", "lokal", "kendi", "tarayici", "sifre", "vendor", "komisyon", "finansman", "yapay"}
EK_SISTEM = ["Gmail", "SharePoint", "Supabase", "Vaultwarden", "1Password", "Claude", "ChatGPT", "Gemini", "Copilot", "Notion", "Slack", "Asana"] + list(AYAR.get("ek_sistem") or [])
def sistemler():
    import baglam
    adlar = set(EK_SISTEM)
    try:
        for k, _, m in baglam.xlsx_parcala(KATALOG):
            g = re.search(r"Sistem: ([^·]+)", m) if k.startswith("SistemKatalogu!") else None
            if g: adlar.update(x.strip() for x in re.split(r"[/(),—]| - ", g.group(1)))
    except Exception: pass
    try:
        for t in json.load(open(os.path.join(A.dir, "sozluk.json"), encoding="utf-8")).get("terimler", []):
            if not str(t.get("not", "")).startswith("kişi"): adlar.add(str(t.get("dogru", "")).strip())
    except Exception: pass
    out = {}
    for a in adlar:
        n = " ".join(baglam.kelimeler(a))
        if len(n) < 3 or not a[:1].isupper() and not a[:1].isdigit() or n in GENEL or n.split()[0] in GENEL_ILK: continue
        out[n] = re.compile(r"(?<![0-9a-z])" + re.escape(n) + (r"" if len(n) >= 5 else r"(?![0-9a-z])"))
    return out
DOLGU = {"evet", "hayir", "tamam", "yani", "simdi", "sonra", "boyle", "soyle", "oldu", "olur", "olarak", "kadar", "zaten",
         "biraz", "bunu", "bunlar", "onlar", "orada", "burada", "bizim", "sizin", "benim", "senin", "aslinda", "galiba", "mesela",
         "diyor", "diyorum", "yapiyor", "yapiyoruz", "lazim", "gerek", "gerekiyor", "hani", "iste", "ama", "fakat", "cunku", "daha",
         "cok", "sey", "seyi", "seyler", "tarafinda", "tarafi", "tane", "hepsi", "hepsinde", "sanirim", "galiba", "peki", "konusunu",
         "konusu", "alalim", "bakalim", "olmasi", "olan", "olarak", "diye", "dedim", "dedi", "listesinde", "kullanicilari", "kullanici",
         "simdilik", "baska", "birisi", "kimler", "tutuyor", "yonetiyor", "duruyor", "elimde", "bende", "sende", "kim", "hangi", "nerede", "neden", "nasil", "icin", "gibi", "var", "yok", "degil"}
def icerik_kelime(metinler, haric=(), n=3):
    import baglam
    say = {}
    for t in metinler:
        for k in re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", t):  # kısaltmalar (IAM, MFA, 2FA) kısa da olsa ayırt edicidir
            k = k.lower()
            if not any(k.startswith(h[:5]) for h in haric): say[k] = say.get(k, 0) + 2
        for w in baglam.kelimeler(t):
            if len(w) >= 4 and w not in DOLGU and w not in baglam.DUR and not any(w.startswith(h[:5]) for h in haric): say[w] = say.get(w, 0) + 1
    return [w for w, _ in sorted(say.items(), key=lambda x: -x[1])[:n]]
def oto_baglam(recs, sis, son_ara, cur, gundem_n="", kisi=""):
    import baglam, io, contextlib
    bul = {}
    for r in recs:
        t = " ".join(baglam.kelimeler(r.get("text", "")))
        for n, rx in sis.items():
            if rx.search(t): bul.setdefault(n, []).append(r.get("text", ""))
    # v0.7.3 (döküm oynatması): geçerken bir kez anılan araç (WhatsApp, Gmail) aranmaz — 16 bağlamın 11'i
    # gürültüydü. Gündemde geçen sistem tek anışta, gündem dışı olan pakette en az 2 satırda geçince aranır.
    secim = [n for n in sorted(bul, key=lambda n: -len(bul[n])) if time.time() - son_ara.get(n, 0) >= 600
             and (n in gundem_n or len(bul[n]) >= 2)][:2]
    out = []
    for n in secim:
        son_ara[n] = time.time(); q = " ".join([n] + icerik_kelime(bul[n], haric=n.split()))
        try:
            # analiz ara çıktıları ve sunumlar canlıda gürültü: önce tablo/belge/görüşme/toplantı, boşsa hepsi
            rows, ek = baglam.ara(q, turler=["tablo", "belge", "gorusme", "toplanti"], n=5)
            if not rows: rows, ek = baglam.ara(q, n=5)
            if kisi:  # v0.7.3: önce karşıdaki kişinin satırları ("Kişi: Ayşe"), sonra genel — kişinin kendi söylediği önce gelsin
                kr, _ = baglam.ara(q + " " + kisi, turler=["tablo", "belge", "gorusme", "toplanti"], n=5)
                kr = [x for x in kr if kisi in baglam.norm(x[4] + " " + (x[3] or ""))]
                rows = kr + [x for x in rows if x[0] not in {y[0] for y in kr}]
            mevcut = os.path.basename(cur)[:-3] if cur else None  # süren toplantının kendi dosyası sonuç değildir
            rows = [x for x in rows if (not mevcut or mevcut not in x[1]) and not str(x[2]).startswith("DüzeltmeKaydı")
                    and "çift kayıt" not in x[4]][:2]  # düzeltme günlüğü ve katalog çift kaydı bağlam değil
            if not rows: continue
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): baglam.yaz((rows, ek), q, ek)
            out += [f"  BAĞLAM · {n} (kendiliğinden, \"{q}\"; konuşmayla çelişiyorsa belirt/sor + kaynak, değilse geç):"] + ["    " + l[:330] for l in buf.getvalue().splitlines()]
        except Exception as e: out.append(f"  BAĞLAM · {n}: arama yapılamadı ({e.__class__.__name__})")
    return out
# --- v0.7.0: gündem tahmini ----------------------------------------------------------------------------------------
# Her maddenin ayırt edici kelime kökleri (5 harf; birden çok maddede geçen kök sayılmaz) + hazir.json tetikleri.
# Son 3 dk'da bir maddenin ≥ 2 farklı kökü geçerse "şu an bu madde" sayılır; değişince izle "GÜNDEM ▶" yazar, pano ▶ gösterir.
# Kesin değil: yalnız öneri — Claude önceki madde bittiyse `gundem i` ile işaretler.
GUNDEM_DUR = DOLGU | {"liste", "listesi", "kullanici", "kullanicilari", "hesap", "hesabi", "hesaplari", "erisim", "erisimleri", "kimde",
                      "kimin", "nerede", "duruyor", "yalniz", "politikasi", "teyidi", "ikinci", "kendi", "acik", "kalanlar", "kapanis", "zaman",
                      # v0.7.1: toplantının kendisi hakkında konuşurken her yerde geçer (1 Ekim testinde yanlış ▶)
                      "gundem", "madde", "isaret", "toplanti", "konus", "konusma", "soru", "cevap", "kart", "not", "ozet"}
# v0.7.3 (87 dk'lık döküm oynatması): eski kural (≥ 2 kök) gündem dışı ilk 55 dk'da 21 yanlış ▶ verdi ("sistem, uygulama",
# "sistem, teknik"). Şimdi: genel kökler sayılmaz; en az bir GÜÇLÜ kök (sistem adı, kısaltma, noktalı/rakamlı ad) gerekir.
# Benzetimde 25 ▶ (1 doğru, 15'i konu yokken) → 7 ▶ (4 doğru, 0'ı konu yokken).
GUNDEM_KOK_DUR = {"takip", "siste", "tekni", "uygul", "erisi", "gelis", "dokum", "deger", "hesab", "servi", "serve", "org"} | set(AYAR.get("gundem_kok_dur") or [])
GUCLU_DEGIL = {"cloud", "devel", "dev", "dashb", "hub", "com", "googl", "ornat", "gmail", "mut", "david"}  # çok kelimeli adların genel parçası
def gundem_kokleri(items, hz, sis_kok=frozenset()):
    # dönen: (kökler, güçlü kökler) — madde başına küme
    import baglam
    kok = [{w[:5] for w in baglam.kelimeler(it) if len(w) >= 3 and w not in GUNDEM_DUR and w not in baglam.DUR} - GUNDEM_KOK_DUR for it in items]
    say = {}
    for k in kok:
        for w in k: say[w] = say.get(w, 0) + 1
    tum = kok; kok = [{w for w in k if say[w] == 1} for k in kok]
    for h in hz:
        i = h.get("gundem")
        if isinstance(i, int) and 0 <= i < len(kok): kok[i] |= {w[:5] for t in h.get("tetik", []) for w in baglam.kelimeler(t) if len(w) >= 3}
    guclu = []
    for i, it in enumerate(items):
        g = set()
        for w in re.findall(r"[\w.@-]+", it):
            if re.fullmatch(r"[A-Z0-9]{2,6}", w) or re.search(r"\d|\.", w): g |= {x[:5] for x in baglam.kelimeler(w) if len(x) >= 3}
        g = ((g | {x for x in kok[i] if x in sis_kok}) & kok[i]) - GUCLU_DEGIL
        if not g:  # ayırt edici sistem adı yoksa maddede geçen ortak sistem adı (aynı sistem üç maddede) geri gelir
            g = {x for x in tum[i] if x in sis_kok} - GUCLU_DEGIL; kok[i] |= g
        guclu.append(g)
    return kok, guclu

def gundem_kopya(md, agj):
    # v0.7.0: karne geçmiş toplantıyı kendi gündemiyle değerlendirsin (agenda.json bir sonraki toplantıda değişir)
    if not agj: return
    try:
        os.makedirs(os.path.join(A.dir, "gundemler"), exist_ok=True); fp = os.path.join(A.dir, "gundemler", md[:-3] + ".json")
        json.dump(agj, open(fp + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(fp + ".tmp", fp)
    except OSError: pass

# --- v0.8.2: kişi başına ses sinyali gözlemi (kullanıcı, 2 Ekim: kişiye özel duygu) -----------------------------------
# Whisper satırının "ses" alanı (whisper-isci.py: db, f0, f0_oyn, sure; relay: hiz) kişinin KENDİ tabanıyla karşılaştırılır:
# taban = kişinin ilk SES_TABAN_SN konuşması (en az SES_TABAN_N parça), şimdi = son SES_PENCERE_SN (en az 3 parça).
# Belirgin sapma ya da tabana dönüş → "SES · <kişi>" olayı (kişi başına en çok SES_ARALIK_SN'de bir). Claude bunu metinle
# birlikte okuyup kişi başına duygu kartı verir (kart duygu --kim). Mikrofon (kullanıcı) ve sekme sesi (karşı) farklı kanallar;
# her kişi kendi kanalında kıyaslandığı için mutlak değerler önemsiz. Tahmindir: kötü mikrofon, ses seviyesi değişikliği yanıltır.
SES_TABAN_SN = 300; SES_TABAN_N = 6; SES_PENCERE_SN = 120; SES_ARALIK_SN = 180
SES_ESIK = {"hiz": 25, "db": 4.0, "f0": 1.5, "oyn": 40, "uzun": -50}  # %, dB, yarım ton, %, % (parça başına kelime)
class SesIz:
    def __init__(s): s.k = {}
    def besle(s, r):
        v = r.get("ses"); kim = r.get("speaker") or "?"
        if not v or kim in ("?", "Karşı taraf") or not r.get("at"): return []
        t = zaman(r["at"]).timestamp(); d = s.k.setdefault(kim, {"p": [], "t0": t, "son": 0.0, "durum": "normal"})
        d["p"].append(dict(v, t=t, kel=len((r.get("text") or "").split()))); d["p"] = d["p"][-400:]
        taban = [x for x in d["p"] if x["t"] - d["t0"] <= SES_TABAN_SN]
        if len(taban) < SES_TABAN_N or t - d["t0"] < 60: return []
        simdi = [x for x in d["p"] if t - x["t"] <= SES_PENCERE_SN and x["t"] - d["t0"] > SES_TABAN_SN]
        if len(simdi) < 3: return []
        med = lambda xs, k: statistics.median([x[k] for x in xs if x.get(k) is not None]) if any(x.get(k) is not None for x in xs) else None
        fark = {}
        for k, ad in (("hiz", "hiz"), ("kel", "uzun")):
            a, b = med(taban, k), med(simdi, k)
            if a and b is not None: fark[ad] = round((b - a) / a * 100)
        a, b = med(taban, "db"), med(simdi, "db")
        if a is not None and b is not None: fark["db"] = round(b - a, 1)
        a, b = med(taban, "f0"), med(simdi, "f0")
        if a and b: fark["f0"] = round(12 * math.log2(b / a), 1)
        a, b = med(taban, "f0_oyn"), med(simdi, "f0_oyn")
        if a and b is not None: fark["oyn"] = round((b - a) / a * 100)
        sapan = [k for k, e in SES_ESIK.items() if k in fark and (fark[k] <= e if e < 0 else abs(fark[k]) >= e)]
        durum = "sapma" if sapan else "normal"
        if t - d["son"] < SES_ARALIK_SN or (durum == "normal" and d["durum"] == "normal"): return []
        if durum == "sapma" and d["durum"] == "sapma" and set(sapan) <= d.get("sapan", set()): return []  # yalnız yeni sinyal sapınca tekrar
        d.update(son=t, durum=durum, sapan=set(sapan) | (d.get("sapan", set()) if durum == "sapma" else set()))
        ad = {"hiz": "konuşma hızı", "db": "ses yüksekliği", "f0": "ses perdesi", "oyn": "perde dalgalanması", "uzun": "cümle uzunluğu"}
        bir = {"hiz": "%", "db": " dB", "f0": " yarım ton", "oyn": "%", "uzun": "%"}
        ozet = " · ".join(f"{ad[k]} {'+' if fark[k] > 0 else ''}{fark[k]}{bir[k]}{' ⚑' if k in sapan else ''}" for k in ad if k in fark)
        if durum == "sapma":
            return [f"SES · {kim}: kendi tabanına göre (ilk {SES_TABAN_SN // 60} dk) son {SES_PENCERE_SN // 60} dk'da {ozet} ({len(simdi)} parça) "
                    f"→ metinle birlikte değerlendir; gerekirse kart duygu --kim \"{kim}\" --ton …"]
        return [f"SES · {kim}: tabana döndü ({ozet}) → açık kişi etiketi artık geçerli değilse güncelle"]

# --- v0.8.3: kesinlik ölçümü (kullanıcı, 2 Ekim) ------------------------------------------------------------------------
# Karşı tarafın iddia içeren satırı (rakam, sıklık, kapsam, sahiplik, güvenlik terimi, sistem adı) ne kadar kesin söylendi:
# çekince sözü ("sanırım", "galiba", "I think"), kullanıcının sorusundan sonraki cevap gecikmesi (Whisper t0/t1), parçada
# duraksama (ses.sesli düşük) ve dolgu sesi puanı düşürür. Puan ≤ KES_ESIK → "KESİNLİK · <kişi>" olayı + kesinlik.jsonl
# (özet "kesinleşmesi gereken iddialar" bölümü için). Kişi başına KES_ARALIK_SN'de bir. Görüşmelerde veri kalitesi için.
KES_ESIK = 60; KES_ARALIK_SN = 90
CEKINCE_RX = re.compile(r"\b(sanırım|sanıyorum|galiba|herhalde|tahminen|tahmin(im|imce)|bilmiyorum|emin değilim|pek emin|olabilir|"
    r"gibi geliyor|aşağı yukarı|yaklaşık|kabaca|belki|hatırladığım kadarıyla|diye (biliyorum|hatırlıyorum)|bakmam (lazım|gerek)|kontrol etmem (lazım|gerek)|"
    r"tam bilemiyorum|net değil|i think|i guess|i believe|probably|maybe|perhaps|not sure|roughly|kind of|sort of|i assume|as far as i know)\b", re.I)
DOLGU_RX = re.compile(r"(?<!\w)(şey|ı{2,}|e{3,}|hı+m+|um+|uh+|erm)(?!\w)", re.I)
IDDIA_RX = re.compile(r"\d|\b(iki|üç|dört|beş|altı|yedi|sekiz|dokuz|yirmi|otuz|elli|yüz|bin|two|three|four|five|six|ten|twenty|hundred)\b|\b(her (gün|hafta|ay|sabah)|haftada|ayda|günde|yılda|hepsi|hiçbir\w*|kimse|herkes|sadece|yalnız(ca)?|"
    r"sorumlu\w*|sahib\w*|admin\w*|yetki\w*|şifre\w*|parola\w*|yedek\w*|backup\w*|mfa|2fa|iki aşamalı|daily|weekly|monthly|every|all of|none|only|nobody|everyone)\b", re.I)
class Kesinlik:
    def __init__(s, ben, sis=()):
        s.ben = ben; s.sis = [n.lower() for n in sis if len(n) >= 3]; s.soru_t1 = None; s.son = {}; s.say = {}  # kişi → [satır, çekinceli satır]
    def besle(s, r):
        kim = r.get("speaker") or "?"; t = r.get("text") or ""
        if kim.split(" ")[0] == s.ben.split(" ")[0]:
            if soru_mu(t): s.soru_t1 = r.get("t1") or (zaman(r["at"]).timestamp() if r.get("at") else None)
            return []
        low = kucuk(t)
        yer = [m.start() for m in IDDIA_RX.finditer(low)] + [low.find(n) for n in s.sis if n in low]  # iddianın konumları
        gec = None
        if s.soru_t1 and r.get("t0"):
            g = r["t0"] - s.soru_t1
            if 0 <= g < 20: gec = round(g, 1)
        if r.get("t0") or kim != "?": s.soru_t1 = None  # gecikme yalnız soruya verilen ilk cevapta
        hep = list(CEKINCE_RX.finditer(low)); sy = s.say.setdefault(kim, [0, 0]); sy[0] += 1; sy[1] += bool(hep)
        if not yer or len(t.split()) < 4: return []
        # çekince yalnız iddianın yakınındaysa (±60 karakter) sayılır; kucuk() uzunluğu korur: ham metinden gösterilir ("I think")
        cek = [t[m.start():m.end()].lower() for m in hep if any(abs(m.start() - y) <= 60 for y in yer)]; dol = DOLGU_RX.search(low); ses = r.get("ses") or {}
        neden, puan = [], 100
        aliskanlik = sy[0] >= 10 and sy[1] / sy[0] >= 0.25  # kişi çekinceyi sık kullanıyor ("I think" alışkanlığı): tek çekince az şey söyler
        if cek: puan -= (15 if aliskanlik else 25) * min(2, len(cek)); neden.append("çekince \"" + "\", \"".join(dict.fromkeys(cek)) + "\"" + (" (sık kullanıyor)" if aliskanlik else ""))
        if gec is not None and gec >= 3: puan -= 20 if gec >= 5 else 10; neden.append(f"soruya {gec:.1f} sn sonra cevap".replace(".", ","))
        if ses.get("sesli") is not None and ses["sesli"] < 0.55 and (ses.get("sure") or 0) >= 3: puan -= 10; neden.append("duraksamalı")
        if dol: puan -= 10; neden.append(f"dolgu \"{dol.group(0)}\"")
        now = time.time()
        if puan > KES_ESIK or now - s.son.get(kim, 0) < KES_ARALIK_SN: return []
        s.son[kim] = now
        try:
            with open(os.path.join(A.dir, "kesinlik.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": r.get("at"), "file": r.get("_file"), "id": r.get("id"), "kim": kim, "text": t, "puan": puan, "neden": neden}, ensure_ascii=False) + "\n")
        except OSError: pass
        return [f"KESİNLİK · {kim} ({puan}/100): \"{t[:140]}\" — {'; '.join(neden)} → iddia kesin değil: konu açıkken "
                f"sor/belirt kartıyla kesinleştir ya da kanıt iste (rol sınırı geçerli); gerekmiyorsa geç"]

# --- v0.8.3: söz kesme + yankı, yorgunluk (kullanıcı, 2 Ekim) ------------------------------------------------------------
# Whisper satırlarının parça sınırları (t0/t1, iki ayrı kanal: kullanıcının mikrofonu / Teams sekmesinin sesi) üst üste binerse:
# sonra başlayan, öbürü ≥ 0,5 sn konuşmuşken başladıysa ve öbürü ≥ 1 sn daha sürdüyse "söz kesti". İki metin büyük ölçüde
# aynıysa bu söz kesme değil YANKI (karşı tarafın sesi hoparlörden kullanıcının mikrofonuna giriyor → çift satır): bir kez bildirilir.
KESME_PENCERE_SN = 300; KESME_ESIK = 3; KESME_ARALIK_SN = 300
def _kel(t): return set(w for w in re.findall(r"\w+", kucuk(t or "")) if len(w) > 2)
class Kesme:
    def __init__(s, ben): s.ben = ben; s.son = {"ben": [], "karsi": []}; s.olay = []; s.bildirim = {}; s.yanki = 0; s.yanki_bildirildi = False
    def besle(s, r):
        k = kanal_n(r.get("kanal"))
        if r.get("src") != "whisper" or k not in s.son or r.get("t0") is None or r.get("t1") is None: return []
        out = []; obur = "karsi" if k == "ben" else "ben"
        for o in s.son[obur]:
            ust = min(r["t1"], o["t1"]) - max(r["t0"], o["t0"])
            if ust <= 0.5: continue
            a, b = _kel(r.get("text")), _kel(o.get("text"))
            if a and b and len(a & b) / max(1, min(len(a), len(b))) >= 0.5:
                s.yanki += 1
                if s.yanki >= 2 and not s.yanki_bildirildi:
                    s.yanki_bildirildi = True
                    out.append("YANKI: karşı tarafın sesi kullanıcının mikrofonuna da giriyor (aynı sözler iki kanalda, üst üste) — satırlar çift "
                               "görünebilir → kullanıcıya bir kez dikkat kartı: \"Hoparlör sesi mikrofona giriyor — kulaklık tak ya da sesi kıs\"")
                continue
            ilk, sonra = (o, r) if o["t0"] <= r["t0"] else (r, o)
            if sonra["t0"] - ilk["t0"] >= 0.5 and ilk["t1"] - sonra["t0"] >= 1.0:
                s.olay.append((sonra["t0"], sonra.get("speaker") or "?", ilk.get("speaker") or "?", kanal_n(sonra.get("kanal"))))
        s.son[k] = (s.son[k] + [r])[-12:]
        now = r["t1"]; s.olay = [x for x in s.olay if now - x[0] <= KESME_PENCERE_SN]
        for kanal in ("ben", "karsi"):
            xs = [x for x in s.olay if x[3] == kanal]
            if len(xs) >= KESME_ESIK and now - s.bildirim.get(kanal, 0) >= KESME_ARALIK_SN:
                s.bildirim[kanal] = now; kim, kimi = xs[-1][1], xs[-1][2]
                if kanal == "ben":
                    out.append(f"KESME: son {KESME_PENCERE_SN // 60} dk'da {kim}, {kimi}'in sözünü {len(xs)} kez kesti → yürütücüde değinme kartı "
                               f"(şeritte gizli): \"{kimi.split(' ')[0]} bitirsin — sözünü kesme\"; kullanıcı sunum/açıklama yapıyorsa gönderme")
                else:
                    out.append(f"KESME: son {KESME_PENCERE_SN // 60} dk'da {kim}, kullanıcının sözünü {len(xs)} kez kesti — itiraz, acele ya da söylemek istediği "
                               f"bir şey olabilir → gerekirse sor kartı: \"{kim.split(' ')[0]}'e söz ver, ne eklemek istediğini sor\"")
        return out
    def ozet(s): return {"ben_kesti": sum(1 for x in s.olay if x[3] == "ben"), "karsi_kesti": sum(1 for x in s.olay if x[3] == "karsi"), "yanki": s.yanki}
# Yorgunluk / dikkat düşüşü: toplantı ≥ YORGUN_MIN_DK sürdükten sonra son 10 dk'da konuşanların çoğunda (kendi ilk 15 dk'larına göre)
# hız ve perde dalgalanması birlikte düşmüşse → "YORGUNLUK" olayı (15 dk'da bir). Öneri: kısa özet, kalan maddeye odak, mola.
YORGUN_MIN_DK = 40; YORGUN_ARALIK_SN = 900
class Yorgunluk:
    def __init__(s): s.p = {}; s.t0 = None; s.son = 0.0
    def besle(s, r):
        v = r.get("ses"); kim = r.get("speaker") or "?"
        if not v or r.get("t1") is None or kim == "?": return []
        t = r["t1"]; s.t0 = s.t0 or t; s.p.setdefault(kim, []).append((t, v.get("hiz"), v.get("f0_oyn"), v.get("db")))
        if t - s.t0 < YORGUN_MIN_DK * 60 or t - s.son < YORGUN_ARALIK_SN: return []
        med = lambda xs: statistics.median(xs) if xs else None
        dusen, sayilan, ayr = 0, 0, []
        for kisi, xs in s.p.items():
            ilk = [x for x in xs if x[0] - s.t0 <= 900]; son = [x for x in xs if t - x[0] <= 600]
            if len(ilk) < 5 or len(son) < 3: continue
            sayilan += 1; h0, h1 = med([x[1] for x in ilk if x[1]]), med([x[1] for x in son if x[1]])
            o0, o1 = med([x[2] for x in ilk if x[2] is not None]), med([x[2] for x in son if x[2] is not None])
            if h0 and h1 and o0 and o1 is not None:
                dh, do = (h1 - h0) / h0 * 100, (o1 - o0) / o0 * 100
                if dh <= -15 and do <= -20: dusen += 1; ayr.append(f"{kisi.split(' ')[0]} hız {dh:+.0f}%, dalgalanma {do:+.0f}%")
        if sayilan >= 1 and dusen * 2 > sayilan:
            s.son = t
            return [f"YORGUNLUK: toplantı {int((t - s.t0) // 60)}. dk; son 10 dk'da {', '.join(ayr)} (ilk 15 dk'ya göre) → enerji düşüyor: "
                    f"yürütücüde belirt kartı — kısa özet geçip kalan en önemli maddeye odaklan ya da 5 dk mola öner"]
        return []

# --- v0.8.4: duygu modeli (emotion2vec+, ses işçisi) kişi başına -----------------------------------------------------
# Whisper satırının "duygu" alanı {etiket, p}. Son DM_PENCERE_SN'de kişinin parçalarında aynı nötr dışı duygu baskınsa
# (en az DM_MIN parça ve %40, ortalama güven ≥ DM_GUVEN) "DUYGU MODELİ · <kişi>" olayı; nötre dönünce bir kez. Kişi başına DM_ARALIK_SN'de bir.
# Model oyuncu kayıtlarıyla eğitildi; Türkçe ve toplantı konuşmasında tahmin: kişi etiketi metin + SES ile birlikte verilir.
DM_PENCERE_SN = 120; DM_MIN = 3; DM_GUVEN = 0.6; DM_ARALIK_SN = 180
DM_AD = {"kizgin": "kızgın", "igrenmis": "tiksinmiş", "korkmus": "kaygılı/korkmuş", "mutlu": "mutlu", "uzgun": "üzgün", "saskin": "şaşkın", "notr": "nötr"}
class DuyguModel:
    def __init__(s): s.k = {}
    def besle(s, r):
        v = r.get("duygu"); kim = r.get("speaker") or "?"
        if not v or kim in ("?", "Karşı taraf") or r.get("t1") is None: return []
        d = s.k.setdefault(kim, {"p": [], "son": 0.0, "durum": "notr"}); t = r["t1"]
        d["p"].append((t, v.get("etiket"), v.get("p") or 0)); d["p"] = [x for x in d["p"] if t - x[0] <= DM_PENCERE_SN]
        xs = [x for x in d["p"] if x[1] not in ("diger", "bilinmiyor")]
        if len(xs) < DM_MIN or t - d["son"] < DM_ARALIK_SN: return []
        say = {}
        for _, e, p in xs:
            if e != "notr": say.setdefault(e, []).append(p)
        bas = max(say, key=lambda e: len(say[e])) if say else None
        if bas and len(say[bas]) >= DM_MIN and len(say[bas]) >= 0.4 * len(xs) and statistics.mean(say[bas]) >= DM_GUVEN:  # model çoğunlukla "nötr" der: %40 anlamlı
            if d["durum"] == bas: return []
            d.update(son=t, durum=bas)
            return [f"DUYGU MODELİ · {kim}: son {DM_PENCERE_SN // 60} dk'da {len(say[bas])}/{len(xs)} parça \"{DM_AD.get(bas, bas)}\" "
                    f"(ort. güven {statistics.mean(say[bas]):.2f}) → metin ve SES ile uyuşuyorsa kart duygu --kim \"{kim}\" --ton …; tek başına yetmez"]
        if d["durum"] != "notr" and sum(1 for x in xs if x[1] == "notr") * 2 > len(xs):
            d.update(son=t, durum="notr"); return [f"DUYGU MODELİ · {kim}: nötre döndü → açık kişi etiketi artık geçmiyorsa güncelle"]
        return []

def izle():
    import baglam  # v0.7.3: hazır kart tetiği kök karşılaştırması
    q_tail = Tail(os.path.join(A.dir, "sorular.jsonl")); k_tail = Tail(os.path.join(A.dir, "kartlar.jsonl"))
    cur = None; t_tail = None; buf = []; acks = []; buf_since = None; last_state = None; texts = {}; aday = None; aday_t = 0.0
    hz_path = os.path.join(A.dir, "hazir.json"); hz_mtime = None; hz = []; hz_seen = set()
    ag_path = os.path.join(A.dir, "agenda.json"); ag_mtime = None; agj = {}
    ac_mtime = None; acik = []; ac_son = {}  # açık soru kimliği → son hatırlatma anı
    sure_ilk = True; sure_esik = set(); kayma_son = 0.0; pay_son = time.time() - 300  # PAY ilk 5 dk susar (yeniden kurulumda tekrar etmesin)
    # v0.7.0: kendiliğinden bağlam + gündem tahmini
    try: sis = sistemler()
    except Exception: sis = {}
    son_ara = {}; buf_recs = []; kokler = []; guclu = []; kok_pen = []; aktif_i = None; aktif_t = 0.0; kok_sig = None
    ses_iz = SesIz(); sesler = []  # v0.8.2
    kes = None  # v0.8.3: kesinlik ölçümü (ben adı ilk /status'tan sonra)
    kesme = Kesme(BEN); yorgun = Yorgunluk(); dmodel = DuyguModel()  # v0.8.3, v0.8.4
    import collections; konusan = collections.Counter()  # v0.7.3: karşıdaki kişi = kullanıcı dışında en çok konuşan
    sis_kok = frozenset(w[:5] for n in sis for w in n.split() if len(w) >= 3)
    def paket_baglam():
        nonlocal buf_recs
        import baglam
        kisi = next((baglam.kelimeler(k)[0] for k, _ in konusan.most_common() if baglam.kelimeler(k) and not k.startswith(AYAR["ad"].split(" ")[0]) and k != "?"), "")
        ek = oto_baglam(buf_recs, sis, son_ara, cur, " ".join(baglam.kelimeler(" ".join(agj.get("items", [])))), kisi) if buf_recs and sis else []
        buf_recs = []; return ek
    def guclu_son(i):  # son 3 dk'da i. maddenin güçlü kökü geçti mi
        return any(j == i and w in guclu[i] for _, j, w in kok_pen) if 0 <= i < len(guclu) else False
    def gundem_tahmin(r, ticks):
        nonlocal aktif_i, aktif_t
        import baglam
        if not kokler: return
        now = time.time(); ws = {w[:5] for w in baglam.kelimeler(r.get("text", "")) if len(w) >= 3}
        for i, k in enumerate(kokler):
            for w in ws & k: kok_pen.append((now, i, w))
        while kok_pen and kok_pen[0][0] < now - 180: kok_pen.pop(0)
        puan, vur = {}, {}
        for _, i, w in kok_pen:
            puan.setdefault(i, set()).add(w)
            if w in guclu[i]: vur[i] = vur.get(i, 0) + 1
        # v0.7.3: en az bir güçlü kök + başka bir kök, ya da güçlü kök 3 dk'da iki kez
        aday_ = [(len(v) + vur.get(i, 0), i) for i, v in puan.items() if not ticks.get(str(i))
                 and (vur.get(i, 0) >= 1 and len(v) >= 2 or vur.get(i, 0) >= 2)]
        if not aday_: return
        _, best = max(aday_)
        if best == aktif_i or now - aktif_t < 60: return
        onceki = aktif_i; aktif_i, aktif_t = best, now
        try: urllib.request.urlopen(urllib.request.Request(A.relay + "/agenda-aktif", data=json.dumps({"i": best}).encode(), method="POST"), timeout=2)
        except Exception: pass
        items = agj.get("items", [])
        acks.append(f"GÜNDEM ▶ {best}: {str(items[best])[:70]} — konuşuluyor görünüyor ({', '.join(sorted(puan[best]))})" +
                    (f" · önceki madde {onceki} işaretsiz: bittiyse gundem {onceki}" if onceki is not None and not ticks.get(str(onceki)) else ""))
    def ag_yukle():
        nonlocal ag_mtime, agj
        try:
            m = os.path.getmtime(ag_path)
            if m != ag_mtime: ag_mtime = m; agj = json.load(open(ag_path, encoding="utf-8")); return True
        except (OSError, ValueError): pass
        return False
    ag_yukle(); rol0 = agj.get("rol")
    # v0.4.10: rol her yeniden kurulumda görünsün (30 dk'da bir Monitor yenilenir; sohbet özetlenince rol unutulmasın)
    emit(f"İZLEME BAŞLADI · rol {rol0 or 'yurutucu (varsayılan)'} · gündem {len(agj.get('items', []))} madde" +
         (f" · bitiş {agj['bitis']}" if agj.get("bitis") else " · bitiş saati yok (kalan süre kapalı)") + f" · dil {agj.get('dil') or 'tr (varsayılan)'} · aktarıcı {A.relay}")
    while True:
        if ag_yukle():
            if cur: gundem_kopya(cur, agj)
            if agj.get("rol") != rol0: rol0 = agj.get("rol"); emit(f"ROL: {rol0}")
        if (ag_mtime, hz_mtime) != kok_sig:
            kok_sig = (ag_mtime, hz_mtime)
            try: kokler, guclu = gundem_kokleri(agj.get("items", []), hz, sis_kok); aktif_i = None
            except Exception: kokler, guclu = [], []
        rol = agj.get("rol") or "yurutucu"
        try:  # v0.6.0: açık sorular (Claude yazar: acik ekle/kapat)
            m = os.path.getmtime(ACIK_FP())
            if m != ac_mtime: ac_mtime = m; acik = [q for q in acik_yukle().get("sorular", []) if q.get("durum") == "acik"]
        except (OSError, ValueError): pass
        try:  # hazır kartlar dosyası toplantı sırasında da güncellenebilir
            m = os.path.getmtime(hz_path)
            if m != hz_mtime: hz_mtime = m; hz = hazir_yukle(); emit(f"HAZIR KARTLAR: {len(hz)} yüklendi")
        except (FileNotFoundError, ValueError): pass
        try:
            s = get("/status")
            for c in (s.get("cards") or []) + (s.get("closed") or []): texts[c["id"]] = f"[{c.get('kind')}] {c.get('text')}"
            x = s.get("extension") or {}; ticks = s.get("agenda_ticks") or {}
            wv = s.get("whisper") or {}; wak = wv.get("durum") in ("hazir", "yukleniyor") and (wv.get("ben") or wv.get("karsi"))  # v0.8.0
            state = ("eklenti bağlı" if (x.get("age_s") is not None and x["age_s"] < 30) else "EKLENTİ SİNYALİ YOK") + \
                    ((" · WHISPER (yerel konuşma tanıma): {BEN} " + ("✓" if wv.get("ben") else "✗" + (f" ({wv['ben_neden']})" if wv.get("ben_neden") else "")) + " · karşı taraf " + ("✓" if wv.get("karsi") else "✗ (karşı ses kapalı — Option + Shift + W; karşı tarafın satırları " + ("altyazıdan" if (x.get("panel") or x.get("captions")) else "GELMİYOR") + ")")) if wak else
                     (" · panel açık" if x.get("panel") else (" · YALNIZ ALTYAZI (konuşmacı adı olmayabilir; özette kişiye bağlama)" if x.get("captions") else
                     (f" · ⚠ TOPLANTIDA ama döküm/altyazı kapalı — satır gelmiyor ({PLATFORM_AD.get(x.get('platform'), 'Teams')}'te kullanıcıya uyarı çıktı; 2 dk sürerse dikkat kartı: \"{(x.get('yonerge') or {}).get('altyazi') or 'Diğer → Dil ve konuşma → Canlı altyazı'}\")" if x.get("call") else " · panel kapalı")))) + \
                    (f" · ⚠ WHISPER {wv['durum']}: {wv.get('hata')}" if wv.get("durum") == "hata" else "") + \
                    (" · ⚠ SES MODELİ hata (duygu modeli/konuşmacı ayırma yok; Whisper çalışıyor)" if wv.get("ses_model") == "hata" else "") + \
                    (f" · altyazıyı kendisi açamadı ({x['capAuto'][11:]})" if str(x.get("capAuto") or "").startswith("basarisiz") and not (x.get("panel") or x.get("captions") or wak) else "") + \
                    (f" · ⚠ DİL: {(s.get('dil') or {}).get('uyari')} → kullanıcıya dikkat kartı gönder; düzelene kadar metinden çıkarım yapma" if (s.get("dil") or {}).get("uyari") else "") + \
                    (f" · ⚠ {s['uyari']} (satırlar dosyaya gelmiyor; kullanıcıya dikkat kartı gönder)" if s.get("uyari") else "")
            # v0.6.2: altyazı ayar menüsü açılınca "panel kapalı ↔ YALNIZ ALTYAZI" titriyordu (1 Ekim: 6 olay) →
            # durum 10 sn sabit kalınca yazılır; ⚠ içeren (dil, disk) ve ilk durum hemen
            if state != last_state:
                if state != aday: aday, aday_t = state, time.time()
                if last_state in (None, "yok") or "⚠" in state or time.time() - aday_t >= 10: emit(f"DURUM: {state}"); last_state = state
            sv = s.get("sure")  # v0.6.0: kalan süre eşikleri ve gündem kayması — yalnız eşik geçilince bir kez
            if sv:
                kal, gun = sv["kalan_dk"], f"gündem {sv['bitti']}/{sv['toplam']} bitti" + (f", beklenen {sv['beklenen']}" if sv.get("beklenen") is not None else "")
                acik_m = " · açık: " + " | ".join(str(ag_i)[:45] for ag_i in [agj.get("items", [])[i] for i in sv.get("acik", [])[:4] if i < len(agj.get("items", []))]) if sv.get("acik") else ""
                esik = [e for e, ok in (("yari", sv.get("gecen_dk") is not None and sv.get("toplam_dk") and sv["gecen_dk"] * 2 >= sv["toplam_dk"]), ("15", kal <= 15), ("5", kal <= 5), ("bitti", kal <= 0)) if ok]
                yeni = [e for e in esik if e not in sure_esik]; sure_esik.update(esik)
                if sure_ilk: emit(f"SÜRE: kalan {kal} dk (bitiş {sv['bitis']}) · {gun}{acik_m}"); sure_ilk = False; kayma_son = time.time()
                elif yeni: emit(f"SÜRE: {({'yari': 'sürenin yarısı geçti', '15': '15 dk kaldı', '5': '5 dk kaldı', 'bitti': 'SÜRE DOLDU'})[yeni[-1]]} · kalan {kal} dk (bitiş {sv['bitis']}) · {gun}{acik_m}")
                elif sv.get("kayma", 0) >= 2 and time.time() - kayma_son >= 600:
                    emit(f"SÜRE: gündem kayması — {sv['kayma']} madde geride · kalan {kal} dk · {gun}{acik_m}"); kayma_son = time.time()
            if (wv.get("yanki") or 0) >= 2 and not kesme.yanki_bildirildi:  # v0.8.5: aktarıcı yankı satırlarını yazmıyor, sayıyor
                kesme.yanki_bildirildi = True
                sesler.append(f"YANKI: karşı tarafın sesi kullanıcının mikrofonuna giriyor ({wv['yanki']} parça; aktarıcı bu satırları yazmadı) → kullanıcıya bir kez "
                              "dikkat kartı: \"Hoparlör sesi mikrofona giriyor — kulaklık tak ya da sesi kıs\"")
            pv = s.get("pay")  # v0.6.0: konuşma payı — yalnız yürütücüde, kullanıcı son 10 dk'da çok konuşuyorsa, 10 dk'da bir
            if pv and rol == "yurutucu" and pv.get("ben_son") is not None and pv["ben_son"] >= 60 and pv.get("kelime_son", 0) >= 150 and time.time() - pay_son >= 600 and pv.get("adsiz", 0) < 50 \
                    and any(k not in (pv["ben"], "?") for k, _ in pv["son"]):  # v0.6.2: tek konuşmacıda pay anlamsız (1 Ekim testi)
                emit(f"PAY: son 10 dk konuşma payı {pv['ben']} %{pv['ben_son']} (" + ", ".join(f"{k} %{v}" for k, v in pv["son"] if k != pv["ben"]) + f") · toplantı boyu {pv['ben']} %{pv['ben_top']}"); pay_son = time.time()
            f = s.get("file")
            if f and f != cur:
                cur = f; jl = os.path.join(A.dir, f.replace(".md", ".jsonl"))
                t_tail = Tail(jl, from_end=False); old = [r for r in t_tail.new() if "note" not in r and "kanit" not in r]
                gundem_kopya(f, agj)
                emit(f"DOSYA: {f} · toplantı: {s.get('meeting')} · mevcut {len(old)} satır" +
                     ("" if not old else " · son satırlar:"))
                for r in old[-6:]: emit(satir(r))
            if t_tail:
                for r in t_tail.new():
                    if "note" in r: emit(f"NOT ({BEN}): {r['note']}")
                    elif "kanit" in r:  # v0.7.0: hemen — ekranda sır olabilir
                        emit(f"KANIT {r.get('n')}: {os.path.join(A.dir, r['kanit'])}" + (f" · not \"{r['not']}\"" if r.get("not") else "") +
                             f" · {r.get('kaynak') or '?'} → SORU yoksa Read ile bak: ekranda sır/şifre → dikkat kartı; gündemle ilgili görünen → kanit {r.get('n')} --aciklama \"…\"; sohbete yazma")
                    else:
                        buf.append(satir(r)); buf_recs.append(r); gundem_tahmin(r, ticks); konusan[r.get("speaker") or "?"] += 1
                        try: sesler += ses_iz.besle(r)  # v0.8.2
                        except Exception: pass
                        try:  # v0.8.3
                            if kes is None: kes = Kesinlik(agj.get("ben") or AYAR["ad"].split(" ")[0], sis)
                            sesler += kes.besle(dict(r, _file=cur))
                        except Exception: pass
                        try: sesler += kesme.besle(r) + yorgun.besle(r) + dmodel.besle(r)  # v0.8.3, v0.8.4
                        except Exception: pass
                        buf_since = buf_since or time.time()
                        low = kucuk(r.get("text", "") + " " + r.get("raw", ""))  # v0.5.1: sözlük düzeltmesi öncesi hâl de
                        for q in acik:  # v0.6.0: cevapsız soru konusu yeniden açıldı — soru başına 5 dk'da bir
                            t = next((t for t in q.get("tetik", []) if tetik_var(t, low)), None)
                            if t and time.time() - ac_son.get(q["id"], 0) >= 300:
                                ac_son[q["id"]] = time.time()
                                emit(f"AÇIK SORU {q['id']} konusu yeniden açıldı (tetik \"{t}\"): {q.get('metin')}" + (f" — {q['kim']}" if q.get("kim") else "") +
                                     f"   [{r.get('speaker','?')}] {r.get('text','')[:100]}  → cevaplandıysa: acik kapat {q['id']} · değilse sor kartı")
                        for h in hz:
                            t = next((t for t in h.get("tetik", []) if tetik_var(kucuk(t), low)), None)
                            # v0.7.3: genel kelime tetiği ("repo", "anahtar", kişi adı) yalnız madde konuşulurken — oynatmada üç
                            # hazır kart açılış konuşmasında ve geçerken anılan addan harcandı; sistem adı tetiği hemen geçer
                            gi = h.get("gundem") if isinstance(h.get("gundem"), int) else -1
                            if t and not (0 <= gi < len(guclu) and ({w[:5] for w in baglam.kelimeler(t)} & (guclu[gi] | sis_kok)
                                          or aktif_i == gi or guclu_son(gi))): t = None
                            if t and h.get("id") not in hz_seen:
                                hz_seen.add(h.get("id"))
                                olcum_yaz({"t": "hazir-tetik", "hid": h.get("id"), "file": cur, "row_id": r.get("id"), "row_at": r.get("at"), "emit_at": simdi()})
                                emit(f"HAZIR {h.get('id')} (gündem {h.get('gundem')}, tetik \"{t}\"): [{h.get('tur')}] {h.get('metin')}")
        except Exception as e:
            if last_state != "yok": emit(f"DURUM: AKTARICI YANIT VERMİYOR ({e.__class__.__name__})"); last_state = "yok"
        qs = [q for q in q_tail.new() if "text" in q]  # v0.6.0: {"id","file"} yama satırları soru değil
        if qs:  # soru önce, bağlam için biriken satırlar arkasından — tek olay
            jl_cur = os.path.join(A.dir, cur.replace(".md", ".jsonl")) if cur else None
            def taslak_satir():  # v0.8.1: henüz kesinleşmemiş (Whisper bekleyen / konuşulan) metin — son sözler kaçmasın
                try: ts = get("/taslak").get("taslak") or []
                except Exception: ts = []
                return [f"  TASLAK ({len(ts)}, kesin değil — Teams'in ham metni, Whisper satırı gelince yerine geçer):", *[f"  [~ {t.get('speaker') or '?'}] {t.get('text')}" for t in ts]] if ts else []
            def soru_olay(q):
                if q.get("tur") == "ozet":  # v0.6.0: "Son 1 dk" düğmesi — bağlam araması yok, son dakikanın satırları
                    ss = son_satirlar(jl_cur) if jl_cur else []
                    return [f"ÖZET İSTEĞİ {q.get('id')}: son 1 dk'yı 1–2 cümleyle özetle → kart cevap \"…\" --cevap {q.get('id')}   ← ÖNCE BUNU (30 sn)",
                            f"  SON 1 DK ({len(ss)} satır):" if ss else "  SON 1 DK: satır yok — 'son 1 dakikada döküm gelmedi' de", *[satir(r) for r in ss], *taslak_satir()]
                return [f"SORU {q.get('id')}: {q.get('text')}   ← ÖNCE BUNU CEVAPLA (30 sn)", *soru_baglam(q.get('text') or ''), *taslak_satir()]
            emit(*[l for q in qs for l in soru_olay(q)], *acks, *sesler,
                 *([f"SATIRLAR ({len(buf)}, soruya kadar):", *buf] if buf else []), *paket_baglam())
            buf = []; acks = []; sesler = []; buf_since = None
        for k in k_tail.new():
            if "text" in k: texts[k["id"]] = f"[{k.get('kind')}] {k.get('text')}"
            elif "status" in k: acks.append(f"KART {({'yapildi': '✓ yaptı', 'okundu': '👁 okudu (reddetmedi)', 'gecildi': '✕ gerek yok (bir daha önerme)', 'yenilendi': '↻ yenilendi'}).get(k['status'], k['status'])}: {texts.get(k.get('id'), k.get('id'))}")
        if acks and not buf_since: buf_since = time.time()  # kart dönüşü acil değil: sıradaki paketle gider
        if (buf or acks) and (len(buf) >= A.paket or time.time() - buf_since >= A.aralik):
            emit(*acks, *sesler, *([f"SATIRLAR ({len(buf)}):", *buf] if buf else []), *paket_baglam()); buf = []; acks = []; sesler = []; buf_since = None
        time.sleep(2)

# --- v0.7.0: kanıt listesi / açıklama ----------------------------------------------------------------------------
def toplanti_dosyasi(ad=None):
    if ad: return os.path.basename(ad).replace(".jsonl", ".md")
    try:
        f = get("/status").get("file")
        if f: return f
    except Exception: pass
    jls = sorted((f for f in os.listdir(A.dir) if f.endswith(".jsonl") and f[:2] == "20"), key=lambda f: os.path.getmtime(os.path.join(A.dir, f)))
    return jls[-1].replace(".jsonl", ".md") if jls else None
def kayitlar(md):
    try: return [json.loads(l) for l in open(os.path.join(A.dir, md.replace(".md", ".jsonl")), encoding="utf-8") if l.strip()]
    except FileNotFoundError: return []
def kanit_cmd():
    md = toplanti_dosyasi(A.dosya)
    if not md: sys.exit("toplantı dosyası yok")
    ac_fp = os.path.join(A.dir, "kanit", md[:-3], "aciklama.json")
    try: ac = json.load(open(ac_fp, encoding="utf-8"))
    except (FileNotFoundError, ValueError): ac = {}
    ks = [r for r in kayitlar(md) if "kanit" in r]
    if A.n is not None and A.aciklama is not None:
        if not any(r.get("n") == A.n for r in ks): sys.exit(f"{md} içinde kanıt {A.n} yok")
        ac[str(A.n)] = " ".join(A.aciklama.split())[:300]; os.makedirs(os.path.dirname(ac_fp), exist_ok=True)
        tmp = ac_fp + ".tmp"; json.dump(ac, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, ac_fp)
    print(f"{md}: {len(ks)} kanıt")
    for r in ks:
        if A.n is None or r.get("n") == A.n:
            print(f"  {r.get('n')} · {str(r.get('at', ''))[11:19]} · {os.path.join(A.dir, r['kanit'])}" + (f" · not: {r['not']}" if r.get("not") else "") + (f" · açıklama: {ac[str(r.get('n'))]}" if str(r.get("n")) in ac else ""))

# --- v0.7.0: karne — toplantı sonu kısa başarı değerlendirmesi ---------------------------------------------------
# Ölçülebilen kısım buradan, nitel kısım (takip işlerinin sahibi var mı) Claude'un özetinden --takip ile gelir.
# Boyutlar (0–5) ve ağırlık: gündem kapsamı 30 · zaman 15 · açık soruların kapanması 20 · konuşma payı 15 (yalnız yürütücü,
# Görüşmede kullanıcı dinlemeli: ≤ %40 tam puan) · takip işlerinin sahibi 20. Veri olmayan boyut hesaba katılmaz.
NOT_AD = [(4.5, "çok iyi"), (3.5, "iyi"), (2.5, "orta"), (1.5, "zayıf"), (0, "verimsiz")]
def karne_hesap(md):
    rs = kayitlar(md); son = {}
    for r in rs:
        if "note" in r or "kanit" in r: continue
        son[r.get("id") or id(r)] = r
    satirlar = list(son.values())
    # gündem: önce izle'nin bu toplantı için sakladığı kopya, yoksa bugünkü agenda.json (yalnız .md'deki işaretlerle
    # uyuşuyorsa), o da yoksa .md'de işaretlenmiş maddeler — geçmiş toplantıya bugünün gündemi uygulanmasın
    ticks = {}
    try:
        for l in open(os.path.join(A.dir, md), encoding="utf-8"):
            g = re.match(r"\| [\d:]+ \| \*\*GÜNDEM\*\* \| ([✓✗]) (.*?)(?: \(Claude\))? \| \|$", l.rstrip("\n"))
            if g: ticks[g.group(2)] = g.group(1) == "✓"
    except FileNotFoundError: pass
    agj, kaynak = {}, "yok"
    for fp, kyn in ((os.path.join(A.dir, "gundemler", md[:-3] + ".json"), "kopya"), (os.path.join(A.dir, "agenda.json"), "guncel")):
        try: d = json.load(open(fp, encoding="utf-8"))
        except Exception: continue
        if kyn == "kopya" or (ticks and any(it in ticks for it in d.get("items", []))): agj, kaynak = d, kyn; break
    if kaynak == "yok" and ticks: agj = {"items": list(ticks)}; kaynak = "md"
    rol = agj.get("rol") or "yurutucu"; items = agj.get("items") or []
    ats = sorted(zaman(r["at"]) for r in satirlar if r.get("at"))
    bas, bit = (ats[0], ats[-1]) if ats else (None, None)
    v = {"dosya": md, "rol": rol, "baslik": agj.get("title"), "satir": len(satirlar), "boyut": {}, "not_": [], "olcu": {}}
    if bas: v["olcu"]["sure_dk"] = round((bit - bas).total_seconds() / 60)
    if kaynak == "md": v["not_"].append("gündem kopyası yok — yalnız işaretlenen maddeler sayıldı")
    if items:
        bitti = sum(1 for it in items if ticks.get(it)); v["olcu"]["gundem"] = f"{bitti}/{len(items)}"
        v["acik_gundem"] = [it for it in items if not ticks.get(it)]
        v["boyut"]["gündem"] = (5 * bitti / len(items), 30, f"{len(items)} maddenin {bitti}'i konuşuldu")
    if agj.get("bitis") and bit:
        try:
            bl = bit.astimezone()  # satır saatleri UTC gelir; plan ve gösterim yerel saatle
            plan = datetime.datetime.combine(bl.date(), datetime.time(*map(int, re.split(r"[:.]", agj["bitis"])[:2]))).astimezone()
            asim = (bit - plan).total_seconds() / 60; v["olcu"]["asim_dk"] = round(asim)
            p = 5 if asim <= 2 else 4 if asim <= 5 else 3 if asim <= 10 else 2 if asim <= 20 else 1
            v["boyut"]["zaman"] = (p, 15, f"bitiş {agj['bitis']}, son satır {bl.strftime('%H:%M')} ({'+' if asim > 0 else ''}{round(asim)} dk)")
        except Exception: pass
    qs = [q for q in acik_yukle().get("sorular", []) if q.get("file") in (None, md)]
    if qs:
        kap = sum(q.get("durum") == "cevaplandi" for q in qs); v["cevapsiz"] = [q for q in qs if q.get("durum") == "acik"]
        v["boyut"]["açık sorular"] = (5 * kap / len(qs), 20, f"{kap}/{len(qs)} cevaplandı")
    # konuşma payı (son sürüm satırlar; ham metin)
    say = {}
    for r in satirlar: say[r.get("speaker") or "?"] = say.get(r.get("speaker") or "?", 0) + len(str(r.get("raw") or r.get("text") or "").split())
    top = sum(say.values()); ben = agj.get("ben") or next((k for k in say if kucuk(k).startswith(kucuk(BEN))), None)
    if top:
        v["olcu"]["pay"] = {k: round(100 * n / top) for k, n in sorted(say.items(), key=lambda x: -x[1])[:5]}
        adsiz = 100 * say.get("?", 0) / top; konusmaci = len([k for k in say if k != "?"])
        if rol == "yurutucu" and ben in say and adsiz < 50 and konusmaci >= 2:
            b = 100 * say[ben] / top; p = 5 if b <= 40 else 4 if b <= 50 else 3 if b <= 60 else 2 if b <= 70 else 1
            v["boyut"]["konuşma payı"] = (p, 15, f"{ben} %{round(b)} (hedef ≤ %40)")
    if A.takip:
        try:
            t, sh = map(int, A.takip.split("/"))
            if t: v["boyut"]["takip sahipli"] = (5 * sh / t, 20, f"{sh}/{t} işin sahibi ve tarihi var")
            else: v["not_"].append("takip işi çıkmadı")
        except ValueError: pass
    else: v["not_"].append("takip işleri sayılmadı (--takip toplam/sahipli)")
    if A.karar is not None: v["olcu"]["karar"] = A.karar
    agirlik = sum(w for _, w, _ in v["boyut"].values())
    v["puan"] = round(2 * sum(p * w for p, w, _ in v["boyut"].values()) / agirlik) / 2 if agirlik else None
    v["etiket"] = next(e for e_, e in NOT_AD if v["puan"] is not None and v["puan"] >= e_) if v["puan"] is not None else "ölçülemedi"
    # Suflor'un kendi karnesi: kart isabeti, sıklık, yanıt süresi
    cards = [c for c in olcum_jl("kartlar.jsonl") if "text" in c and c.get("file") == md]
    qsj = {q["id"]: q for q in olcum_jl("sorular.jsonl") if q.get("file") == md}
    yon = [c for c in cards if c["kind"] in ("sor", "belirt", "deginme", "dikkat")]
    yap, gec = sum(c.get("status") == "yapildi" for c in yon), sum(c.get("status") == "gecildi" for c in yon)
    cev = sorted((zaman(c["at"]) - zaman(qsj[c["reply_to"]]["at"])).total_seconds() for c in cards if c.get("reply_to") in qsj)
    saat = max(v["olcu"].get("sure_dk", 0), 1) / 60
    v["suflor"] = {"kart": len(cards), "saatte": round(len(cards) / saat, 1), "tur": {k: sum(c["kind"] == k for c in cards) for k in sorted({c["kind"] for c in cards})},
                   "isabet": f"{yap}/{yap + gec}" if yap + gec else None, "cevap_ortanca_sn": round(statistics.median(cev)) if cev else None,
                   "ton": [c.get("ton") for c in cards if c["kind"] == "duygu"], "kanit": sum("kanit" in r for r in rs)}
    return v
def olcum_jl(name):
    try: rs = [json.loads(l) for l in open(os.path.join(A.dir, name), encoding="utf-8") if l.strip()]
    except FileNotFoundError: return []
    byid = {r["id"]: r for r in rs if "text" in r}
    for r in rs:
        if "text" in r: continue
        if r.get("id") in byid:
            if "file" in r: byid[r["id"]]["file"] = r["file"]
            if "status" in r: byid[r["id"]]["status"] = r["status"]
    return list(byid.values())
def karne_cmd():
    fp = os.path.join(A.dir, "karneler.jsonl")
    if A.gecmis:
        try: ks = [json.loads(l) for l in open(fp, encoding="utf-8") if l.strip()][-10:]
        except FileNotFoundError: sys.exit("karne yok")
        for k in ks: print(f"{k['dosya'][:16]} · {k.get('baslik') or '-'} · not {k.get('puan')} ({k.get('etiket')}) · " + " · ".join(f"{a} {b[0]:.1f}" for a, b in k["boyut"].items()) + f" · Suflor.me isabet {k['suflor'].get('isabet') or '-'}")
        return
    md = toplanti_dosyasi(A.dosya)
    if not md: sys.exit("toplantı dosyası yok")
    v = karne_hesap(md); sf = v["suflor"]
    print(f"## Karne — not {('%g' % v['puan']) if v['puan'] is not None else '-'}/5 ({v['etiket']})")
    print(f"*{v['dosya']} · rol {v['rol']} · {v['olcu'].get('sure_dk', '?')} dk · {v['satir']} satır" + (f" · {v['olcu']['karar']} karar" if "karar" in v["olcu"] else "") + "*\n")
    # v0.7.1 (kullanıcı: "karışık"): boyut başına tek sade satır, puan tam sayı
    for a, (p, w, ac) in v["boyut"].items(): print(f"- {a.capitalize()}: {round(p)}/5 — {ac}")
    for n in v["not_"]: print(f"- ({n})")
    if v.get("acik_gundem"): print("- açık kalan gündem: " + " | ".join(str(x)[:50] for x in v["acik_gundem"][:5]))
    if v.get("cevapsiz"): print("- cevapsız sorular: " + " | ".join(q.get("metin", "")[:60] + (f" ({q['kim']})" if q.get("kim") else "") for q in v["cevapsiz"][:5]))
    if v["olcu"].get("pay"): print("- konuşma payı: " + ", ".join(f"{k} %{n}" for k, n in v["olcu"]["pay"].items()))
    print(f"- Suflor.me: {sf['kart']} kart ({sf['saatte']}/saat; " + ", ".join(f"{k} {n}" for k, n in sf["tur"].items()) + ")" + (f" · isabet ✓/(✓+✕) {sf['isabet']}" if sf["isabet"] else "") +
          (f" · SORU→CEVAP ortanca {sf['cevap_ortanca_sn']} sn" if sf["cevap_ortanca_sn"] is not None else "") + (f" · ton {'→'.join(sf['ton'])}" if sf["ton"] else "") + (f" · 📷 {sf['kanit']} kanıt" if sf["kanit"] else ""))
    print("\nClaude: 1–2 cümle nitel değerlendirme ekle (karar çıktı mı, en zayıf boyut ve bir dahaki toplantıya tek öneri).")
    if A.kaydet:
        with open(fp, "a", encoding="utf-8") as f: f.write(json.dumps(dict(v, at=simdi(), cevapsiz=[q.get("metin") for q in v.get("cevapsiz", [])]), ensure_ascii=False, default=str) + "\n")
        print("(karneler.jsonl'e eklendi)")

# --- v0.7.0: toplantı öncesi bağlam paketi -----------------------------------------------------------------------
def hazirlik_cmd():
    import baglam, io, contextlib
    try: agj = json.load(open(os.path.join(A.dir, "agenda.json"), encoding="utf-8"))
    except Exception: agj = {}
    def bas(q, **kw):
        r = baglam.ara(q, n=A.n, **kw); buf = io.StringIO()
        with contextlib.redirect_stdout(buf): baglam.yaz(r, q, r[1])
        return ["  " + l[:330] for l in buf.getvalue().splitlines()]
    print(f"# Hazırlık — {agj.get('title') or '(gündem yok)'}")
    if A.kim:
        print(f"\n## {A.kim}: geçmişte ne dedi"); print("\n".join(bas(A.kim, kim=A.kim)))
    for i, it in enumerate(agj.get("items") or []):
        q = " ".join([w for w in baglam.kelimeler(it) if len(w) >= 3 and w not in GUNDEM_DUR and w not in baglam.DUR][:6])
        print(f"\n## Gündem {i}: {it}\n  (arama: {q})"); print("\n".join(bas(q) if q else ["  (aranacak kelime yok)"]))
    try: ars = [json.loads(l) for l in open(os.path.join(A.dir, "acik-arsiv.jsonl"), encoding="utf-8") if l.strip()]
    except FileNotFoundError: ars = []
    k = kucuk(A.kim or "")
    ars = [q for q in ars if q.get("durum") == "acik" and (not k or k.split()[0] in kucuk(q.get("kim") or "") or k.split()[0] in kucuk(q.get("toplanti") or ""))]
    print("\n## Önceki toplantılarda cevapsız kalan sorular" + (f" ({A.kim})" if A.kim else ""))
    print("\n".join(f"  - {q.get('metin')} — {q.get('kim') or '?'} · {q.get('toplanti') or '?'} · {str(q.get('at', ''))[:10]}" for q in ars[-10:]) or "  yok")
    if A.kim:
        try:
            db = AYAR.get("durum_belgesi")  # v0.9.2: alanın durum belgesi
            if not db: raise FileNotFoundError
            dur = [l.strip() for l in open(os.path.join(PROJE, db), encoding="utf-8") if k.split()[0] in kucuk(l)][:8]
            print(f"\n## {db}'de {A.kim} geçen satırlar"); print("\n".join("  " + l[:250] for l in dur) or "  yok")
        except FileNotFoundError: pass
    print("\nClaude: bundan hazir.json kartlarını ve kullanıcıya 3–6 satırlık 'geçmişte ne dendi / açık ne' özetini çıkar (kaynak dosya @konum).")

# --- v0.7.2: Teams'in kendi dökümüyle karşılaştırma ------------------------------------------------------------
# Sanal listenin satır kaçırıp kaçırmadığını ölçmenin tek yolu (BRIEF §6.3). İki taraf kelimelere bölünür (baglam.norm:
# Türkçe harf sadeleşir), difflib ile hizalanır; Teams satırının kelimelerinin < %50'si Suflor'da yoksa "kaçan" sayılır.
# Suflor tarafında sözlük düzeltmesi öncesi ham metin (raw) kullanılır; aynı id'nin düzeltmesi (revised) son hâliyle sayılır.
ZAMAN_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?(?:[.,]\d+)?")
def _sn(t):
    m = ZAMAN_RE.fullmatch(t.strip()) if t else None
    if not m: return None
    a, b, c = m.groups(); return int(a) * 3600 + int(b) * 60 + int(c) if c is not None else int(a) * 60 + int(b)
def teams_oku(yol):
    # [(saniye, konuşmacı, metin)] — VTT (<v Ad>…</v>), Teams .docx/.txt ("Ad   0:03" başlığı + metin) ya da "Ad: metin"
    import baglam
    if yol.lower().endswith(".docx"):  # satır sonları (<w:br/>) korunur; gerçek Teams .docx'te başlık ve metin aynı paragrafta
        import zipfile, html as _h
        x = zipfile.ZipFile(yol).read("word/document.xml").decode("utf-8", "replace")
        t = "\n".join(_h.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<w:(br|cr)[^>]*/>", "\n", p))) for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S))
    else: t = open(yol, encoding="utf-8-sig", errors="replace").read()
    out, sn, kim, buf = [], None, "", []
    def bitir():
        # her satır ayrı: Teams .docx tek konuşmacının uzun bloğunu satır satır yazar; satır düzeyinde kaçan ölçülsün
        for x in buf: out.append((sn, kim, x.strip()))
        buf.clear()
    bas_re = re.compile(r"^(.{1,60}?)\s{1,}(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*$")
    bitisik_re = re.compile(r"^(\S.{0,58}?)\s{2,}(\d{1,2}:\d{2}(?::\d{2})?)(\S.*)$")
    for ln in t.splitlines():
        ln = ln.strip()
        if not ln or ln == "WEBVTT" or re.fullmatch(r"[0-9a-f-]{8,}/\d+(-\d+)?|\d+", ln): continue
        if "-->" in ln: bitir(); sn = _sn(ln.split("-->")[0]); kim = ""; continue
        if re.search(r"(dökümü|transkripti?) (başlattı|durdurdu)|started transcription|stopped transcription", ln, re.I): continue
        m = bas_re.match(ln)
        if m and _sn(m.group(2)) is not None and len(m.group(1).split()) <= 5: bitir(); kim, sn = m.group(1).strip(), _sn(m.group(2)); continue
        m = bitisik_re.match(ln)  # "Ad Soyad   0:03Görüşmeleri yaptık…" (Teams .docx, 2026)
        if m and len(m.group(1).split()) <= 5: bitir(); kim, sn = m.group(1).strip(), _sn(m.group(2)); ln = m.group(3).strip()
        elif _sn(ln) is not None: bitir(); sn = _sn(ln); continue
        v = re.match(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$", ln)
        if v: kim = v.group(1).strip(); ln = v.group(2)
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if ln: buf.append(ln)
    bitir()
    if any(x[0] is not None for x in out): out = [x for x in out if x[0] is not None]  # başlık/tarih satırları (ilk konuşmacıdan önce)
    return [x for x in out if x[2]]
def karsilastir_cmd():
    import baglam, difflib
    if not os.path.exists(A.teams): sys.exit(f"dosya yok: {A.teams}")
    md = toplanti_dosyasi(A.dosya)
    if not md: sys.exit("Suflor.me toplantı dosyası yok")
    tm = teams_oku(A.teams)
    if not tm: sys.exit("Teams dosyasında satır bulunamadı (biçim tanınmadı)")
    son, sira = {}, []
    for r in kayitlar(md):
        if "text" not in r: continue
        if r.get("id") not in son: sira.append(r.get("id"))
        son[r.get("id")] = r
    sf = [son[i] for i in sira]
    def kel(x): return baglam.kelimeler(x)
    a, a_i = [], []
    for i, (_, _, m) in enumerate(tm):
        for w in kel(m): a.append(w); a_i.append(i)
    b, b_i = [], []
    for j, r in enumerate(sf):
        for w in kel(r.get("raw") or r.get("text") or ""): b.append(w); b_i.append(j)
    if not b: sys.exit(f"{md}: Suflor.me dökümünde satır yok")
    eslesen_a, eslesen_b, es = [0] * len(tm), [0] * len(sf), {}
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=len(a) > 4000).get_matching_blocks():
        for k in range(blk.size):
            i, j = a_i[blk.a + k], b_i[blk.b + k]; eslesen_a[i] += 1; eslesen_b[j] += 1
            es.setdefault(i, {}); es[i][j] = es[i].get(j, 0) + 1
    ka = [len(kel(m)) for _, _, m in tm]; kb = [len(kel(r.get("raw") or r.get("text") or "")) for r in sf]
    kacan = [i for i in range(len(tm)) if ka[i] and eslesen_a[i] / ka[i] < 0.5]
    kisa = [i for i in kacan if ka[i] < 3]  # "Evet.", "Tamam." — Teams kısa satırları ayrı tutar, Suflor.me çoğu zaman birleştirir
    kapsam = sum(eslesen_a) / max(1, sum(ka)); fazla = 1 - sum(eslesen_b) / max(1, sum(kb))
    # konuşmacı: Teams satırını en çok kelimesini taşıyan Suflor satırıyla eşle
    def ad(x): return (kel(x or "") or [""])[0]
    uy, uymaz, soru, ornek = 0, 0, 0, []
    for i, js in es.items():
        j = max(js, key=js.get); s_k = (sf[j].get("speaker") or "").strip()
        if not tm[i][1]: continue
        if not s_k or s_k == "?": soru += 1
        elif ad(s_k) == ad(tm[i][1]): uy += 1
        else:
            uymaz += 1
            if len(ornek) < 3: ornek.append(f"{_hms(tm[i][0])} Teams {tm[i][1]} ↔ Suflor.me {s_k}: {tm[i][2][:60]}")
    # ardışık kaçan satırlar → bölüm
    bolum, cur = [], []  # kısa satırlar bölümü bölmez, ama yalnız kısalardan oluşan bölüm listelenmez
    for i in kacan:
        if cur and i != cur[-1] + 1: bolum.append(cur); cur = []
        cur.append(i)
    if cur: bolum.append(cur)
    kisa_k = set(kisa); bolum = [g for g in bolum if any(i not in kisa_k for i in g)]
    bolum.sort(key=lambda g: -sum(ka[i] for i in g))
    print(f"# Karşılaştırma — {md[:-3]}  ↔  {os.path.basename(A.teams)}")
    print(f"Teams: {len(tm)} satır, {sum(ka)} kelime · Suflor.me: {len(sf)} satır, {sum(kb)} kelime"
          + (f" ({sum(1 for r in sf if r.get('src') == 'captions')} altyazı)" if any(r.get("src") == "captions" for r in sf) else ""))
    print(f"- Kapsam: Teams kelimelerinin %{round(100 * kapsam)}'i Suflor.me'de var")
    if kapsam < 0.2: print("  ⚠ Kapsam çok düşük — dosyalar aynı toplantının olmayabilir (Suflor.me dosyasını adıyla ver) ya da Suflor.me o sırada kapalıydı")
    print(f"- Kaçan satır: {len(kacan) - len(kisa)} / {len(tm)} (≥ 3 kelime; ayrıca {len(kisa)} kısa satır: evet/tamam türü)")
    print(f"- Suflor.me'de olup Teams'te olmayan: kelimelerin %{round(100 * fazla)}'i (tekrar, altyazı farkı ya da Teams'in sonradan düzelttiği)")
    if uy + uymaz + soru:
        print(f"- Konuşmacı: {uy} uyuyor · {uymaz} farklı · {soru} '?' (Suflor.me'de ad yok) — uyum %{round(100 * uy / (uy + uymaz + soru))}")
        for o in ornek: print(f"    farklı: {o}")
    if bolum:
        print(f"\n## En büyük kaçan bölümler (Teams saati, kayıt başından)")
        for g in bolum[:A.n]:
            k = ", ".join(dict.fromkeys(tm[i][1] for i in g if tm[i][1])) or "?"
            print(f"- {_hms(tm[g[0]][0])}–{_hms(tm[g[-1]][0])} · {len(g)} satır, {sum(ka[i] for i in g)} kelime · {k}: {' '.join(tm[i][2] for i in g)[:110]}")
    if A.kaydet:
        with open(os.path.join(A.dir, "karsilastirmalar.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": simdi(), "dosya": md, "teams": os.path.basename(A.teams), "teams_satir": len(tm), "suflor_satir": len(sf),
                                "kapsam": round(kapsam, 3), "kacan": len(kacan) - len(kisa), "kacan_kisa": len(kisa), "fazla": round(fazla, 3),
                                "konusmaci": {"uyuyor": uy, "farkli": uymaz, "soru": soru}}, ensure_ascii=False) + "\n")
        print("(karsilastirmalar.jsonl'e eklendi)")
def kesinlik_cmd():  # v0.8.3: özetin "kesinleşmesi gereken iddialar" bölümü
    md = toplanti_dosyasi(A.dosya)
    try: rs = [json.loads(l) for l in open(os.path.join(A.dir, "kesinlik.jsonl"), encoding="utf-8") if l.strip()]
    except FileNotFoundError: rs = []
    rs = [r for r in rs if r.get("file") == md]
    print(f"{md}: kesin söylenmeyen iddia {len(rs)}")
    for r in rs: print(f"  {(r.get('at') or '')[11:19]} {r.get('kim')} ({r.get('puan')}/100): \"{r.get('text')}\" — {'; '.join(r.get('neden') or [])}")
# --- v0.8.3: konuşma koçluğu ve öne çıkan anlar (toplantı sonu; özete girer) ------------------------------------------
ACIK_UCLU_RX = re.compile(r"\b(nasıl|neden|niye|ne(yi|ler|den)?|hangi|anlat\w*|açıkla\w*|örnek\w*|how|why|what|which|tell me|walk me|describe|explain)\b", re.I)
KARAR_RX = re.compile(r"\b(karar\w*|anlaştık|tamam o zaman|öyle yapalım|yapalım|kesinleşti|son tarih|cumaya|pazartesiye|haftaya|deadline|agreed|let's|we will|decided|by (monday|friday|next week))\b", re.I)
def _jl_kayit(md):
    try: return [json.loads(l) for l in open(os.path.join(A.dir, md.replace(".md", ".jsonl")), encoding="utf-8") if l.strip()]
    except FileNotFoundError: sys.exit(f"{md}: .jsonl yok")
def koc_cmd():
    md = toplanti_dosyasi(A.dosya); rs = _jl_kayit(md); ag = {}
    try: ag = json.load(open(os.path.join(A.dir, "agenda.json"), encoding="utf-8"))
    except Exception: pass
    ben = (ag.get("ben") or AYAR["ad"]).split(" ")[0]
    son = {}
    for r in rs:
        if "text" in r: son[r.get("id") or id(r)] = r
    rs = list(son.values()); mr = [r for r in rs if (r.get("speaker") or "").split(" ")[0] == ben]
    if not mr: print(f"{md}: {ben} satırı yok"); return
    kel = sum(len(r["text"].split()) for r in mr); top = sum(len(r["text"].split()) for r in rs) or 1
    hiz = [r["ses"]["hiz"] for r in mr if (r.get("ses") or {}).get("hiz")]; oyn = [r["ses"]["f0_oyn"] for r in mr if (r.get("ses") or {}).get("f0_oyn") is not None]
    dol = sum(len(DOLGU_RX.findall(kucuk(r["text"]))) for r in mr)
    sorular = [r for r in mr if soru_mu(r["text"])]; acik = [r for r in sorular if ACIK_UCLU_RX.search(kucuk(r["text"]))]
    uzun = [r for r in sorular if len(r["text"].split()) > 30]
    kz = Kesme(ben); n_m = n_k = 0  # izle'nin söz kesme kuralı, toplantı boyu sayılır (pencere her parçada daralır: yeni olayları say)
    for r in sorted((r for r in rs if r.get("t0") is not None), key=lambda r: r["t1"]):
        once = list(kz.olay); kz.besle(r)
        for x in kz.olay:
            if x not in once: n_m += x[3] == "ben"; n_k += x[3] != "ben"
    print(f"Konuşma koçluğu — {md} ({ben})")
    print(f"  konuşma payı (kelime): %{round(kel / top * 100)}")
    if hiz: print(f"  konuşma hızı: ortanca {statistics.median(hiz):.0f} kelime/dk (Whisper parçaları, n={len(hiz)})")
    if oyn: m = statistics.median(oyn); print(f"  ses perdesi dalgalanması: ortanca {m:.2f} yarım ton" + (" — tek düze (< 1,0)" if m < 1.0 else ""))
    print(f"  dolgu sesi: {dol} ({dol / max(1, kel) * 100:.1f} / 100 kelime)")
    print(f"  soru: {len(sorular)} · açık uçlu {len(acik)} (%{round(len(acik) / max(1, len(sorular)) * 100)}) · 30 kelimeden uzun soru {len(uzun)}")
    if uzun: print(f"    en uzun soru: \"{max(uzun, key=lambda r: len(r['text']))['text'][:160]}\"")
    print(f"  söz kesme: {ben} karşı tarafı {n_m} kez kesti · karşı taraf {ben}'i {n_k} kez kesti · yankı {kz.yanki} parça")
    dg = [r["duygu"]["etiket"] for r in mr if r.get("duygu")]  # v0.8.4: duygu modeli (tahmin)
    if dg: print("  sesindeki duygu (model, tahmin): " + ", ".join(f"{DM_AD.get(e, e)} %{round(dg.count(e) / len(dg) * 100)}" for e in sorted(set(dg), key=dg.count, reverse=True)[:4]))
def anlar_cmd():
    md = toplanti_dosyasi(A.dosya); rs = _jl_kayit(md); kes = []
    try: kes = [json.loads(l) for l in open(os.path.join(A.dir, "kesinlik.jsonl"), encoding="utf-8") if l.strip() and md in l]
    except FileNotFoundError: pass
    dk = {}; taban = {}  # dakika → puan, nedenler, örnek satırlar
    for r in rs:
        v = r.get("ses"); k = r.get("speaker")
        if v and k: taban.setdefault(k, []).append(v)
    tb = {k: (statistics.median([x.get("hiz") or 0 for x in v]), statistics.median([x.get("db") or -40 for x in v])) for k, v in taban.items() if len(v) >= 5}
    def kova(r):
        if not r.get("at"): return None
        z = zaman(r["at"]); return z.strftime("%H:%M")
    def ekle(r, p, neden):
        b = kova(r)
        if not b: return
        d = dk.setdefault(b, {"puan": 0.0, "neden": {}, "satir": []}); d["puan"] += p; d["neden"][neden] = d["neden"].get(neden, 0) + 1
        if r.get("text") and len(d["satir"]) < 2 and r.get("speaker"): d["satir"].append(f"{r['speaker']}: {r['text'][:110]}")
    for r in rs:
        if "note" in r:
            if "⭐" in str(r["note"]): ekle(r, 5, "⭐ kullanıcı işaretledi")
            continue
        if "kanit" in r: ekle(r, 2, "kanıt"); continue
        if "text" not in r: continue
        if KARAR_RX.search(kucuk(r["text"])): ekle(r, 2, "karar/tarih sözü")
        v, k = r.get("ses"), r.get("speaker")
        if v and k in tb:
            h0, d0 = tb[k]
            if h0 and v.get("hiz") and abs(v["hiz"] - h0) / h0 >= 0.3: ekle(r, 1, "hız değişimi")
            if v.get("db") is not None and v["db"] - d0 >= 4: ekle(r, 1, "ses yükseldi")
        dm = r.get("duygu") or {}
        if dm.get("etiket") not in (None, "notr", "diger", "bilinmiyor") and (dm.get("p") or 0) >= 0.7: ekle(r, 1, f"duygu: {DM_AD.get(dm['etiket'], dm['etiket'])}")
    for x in kes: ekle(x, 2, "kesin olmayan iddia")
    sec = sorted(dk.items(), key=lambda kv: -kv[1]["puan"])[:A.n]
    print(f"Öne çıkan anlar — {md} (ilk {len(sec)})")
    for b, d in sorted(sec):
        print(f"  {b} · puan {d['puan']:.0f} · " + ", ".join(f"{n}{' ×' + str(c) if c > 1 else ''}" for n, c in d["neden"].items()))
        for l in d["satir"]: print(f"      {l}")
def saglik_cmd():  # v0.8.5: toplantıdan önce tek bakış; ⚠ satırları kullanıcıya iletilecek eksikler
    import shutil, subprocess as sp_
    APP = AYAR["uygulama"]; EK = os.path.dirname(os.path.abspath(__file__)); sorun = 0
    def sat(ok, metin, oneri=""):
        nonlocal sorun; sorun += not ok; print(("✓ " if ok else "⚠ ") + metin + (f" → {oneri}" if (oneri and not ok) else ""))
    try: man = json.load(open(os.path.join(EK, "manifest.json"))).get("version")
    except Exception: man = None
    try: s = get("/status")
    except Exception: s = None
    sat(bool(s), f"aktarıcı {('v' + str(s.get('surum'))) if s else 'yanıt vermiyor'}", os.path.join(AYAR.get("kod") or "<kod klasörü>", "aktarici-kur.command") + "'a çift tıkla")
    if s and man and s.get("surum") and s["surum"] != man: sat(False, f"aktarıcı v{s['surum']}, klasördeki sürüm v{man}", "./aktarici-kur.command")
    x = (s or {}).get("extension") or {}
    if x.get("age_s") is not None and x["age_s"] < 30:
        sat(x.get("ver") == man, f"eklenti bağlı · v{x.get('ver') or '?'}" + (f" (klasörde v{man})" if x.get("ver") != man else ""), "chrome://extensions → Suflor.me → yenile, Teams sekmesini yenile")
    else: print("· eklenti sinyali yok (Teams sekmesi açık değil ya da toplantı başlamadı — normal olabilir)")
    wv = (s or {}).get("whisper") or {}
    M = next((d for d in (AYAR["ortak"], APP) if os.path.exists(os.path.join(d, "whisper-venv", "bin", "python"))), AYAR["ortak"])  # v0.9.2: önce ortak klasör
    wok = os.path.exists(os.path.join(M, "whisper-venv", "bin", "python")) and os.path.isdir(os.path.join(M, "whisper-modeller", "hub", "models--mlx-community--whisper-large-v3-turbo"))
    sat(wok and wv.get("durum") not in ("yok", "hata"), f"Whisper {'kurulu' if wok else 'KURULU DEĞİL'} · durum {wv.get('durum') or '?'}" + (f" · {wv.get('hata')}" if wv.get("hata") else ""), os.path.join(AYAR.get("kod") or "<kod klasörü>", "modeller-kur.command"))
    sok = os.path.exists(os.path.join(M, "ses-venv", "bin", "python")) and os.path.exists(os.path.join(M, "ses-modeller", "emotion2vec_plus_base", "model.pt")) and os.path.exists(os.path.join(APP, "ses-isci.py"))
    sat(sok and wv.get("ses_model") not in ("yok", "hata"), f"ses modeli (duygu + konuşmacı ayırma) {'kurulu' if sok else 'KURULU DEĞİL'} · durum {wv.get('ses_model') or '?'}", "modeller-kur.command, sonra aktarici-kur.command")
    try:
        vm = sp_.run(["vm_stat"], capture_output=True, text=True).stdout; sayfa = int(re.search(r"page size of (\d+)", vm).group(1))
        bos = sum(int(re.search(rf"{k}:\s+(\d+)", vm).group(1)) for k in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable")) * sayfa / 2 ** 30
        # Whisper turbo ~1,6 GB + ses işçisi ~2,2 GB (1-2 Ekim ölçümü) + pay
        sat(bos >= 4.5, f"kullanılabilir bellek ~{bos:.1f} GB", "Whisper + ses modeli ~4 GB ister: kullanılmayan uygulamaları (Chrome sekmeleri) kapat")
    except Exception: print("· bellek ölçülemedi")
    d = shutil.disk_usage(os.path.expanduser("~")).free / 2 ** 30; sat(d >= 3, f"disk boş {d:.0f} GB", "en az 3 GB aç (döküm, kanıt görüntüleri)")
    sat(os.path.exists(os.path.join(APP, "dizin.sqlite")), "proje arama dizini", "ilk `ara` kendisi kurar")
    sat(os.path.exists(os.path.join(A.dir, "kart-anahtari.txt")), "kart anahtarı", "aktarıcıyı yeniden kur")
    print("SONUÇ: " + ("hazır" if not sorun else f"{sorun} eksik (⚠)"))
def takvim_cmd():  # v0.9.3: aktarıcının takvimi (Suflor Takvim yardımcısı, Takvim uygulamasındaki tüm hesaplar)
    try: t = get("/takvim?tam=1")
    except Exception as e: sys.exit(f"aktarıcıya ulaşılamadı: {e}")
    if t.get("durum") != "ok": print(f"takvim: {t.get('durum')} — {t.get('hata') or ''}".strip(" —"))
    ol = [o for o in t.get("olaylar") or [] if not A.id or o.get("id") == A.id][:A.n]
    if not ol: print("Bugün başka toplantı yok."); return
    for o in ol:
        ne = "şimdi" if o.get("suruyor") else (f"{o['dk']} dk sonra" if o.get("dk", 0) <= 120 else "")
        print(f"## {o['saat']}–{o['bitis_saat']} {o['baslik']}" + (f"  ({ne})" if ne else "") + f"  · id {o['id']}")
        print(f"  platform: {o.get('platform') or '?'} · düzenleyen: {o.get('duzenleyen') or '?'}{' (sen)' if o.get('ben_duzenleyen') else ''} · kişi: {o.get('kisi_sayisi') or '?'} · takvim: {o.get('takvim')}")
        if o.get("katilimcilar"): print("  katılımcılar: " + ", ".join(o["katilimcilar"]))
        if o.get("notlar"):
            n = re.sub(r"_{6,}.*", "", o["notlar"], flags=re.S)  # Teams davetinin "Microsoft Teams toplantısı …" alt bloğu
            print("  davet notu:\n    " + "\n    ".join(l for l in n.strip().splitlines()[:40] if l.strip()))
# --- v0.9.9: geliştiriciye geri bildirim -------------------------------------------------------------------------
# Kişisel hesapta (ya da başka bir Mac'te) yapılan toplantının teşhis verisi geliştirme oturumuna ulaşsın. İçerik YOK: döküm
# satırı, kart metni, kişi adı, toplantı adı yazılmaz — yalnız sürüm, süre, sayılar, gecikmeler, günlüğün teknik satırları
# (toplantı adı "<toplantı>" ile örtülür) ve --not gözlemleri. Hedef aynı Mac'te iki hesabın ortak klasörü
# (<ortak>/geri-bildirim, herkes yazabilir, yapışkan bit); --github ile ayrıca özel depoda konu.
GB_DIR = lambda: os.path.join(AYAR["ortak"], "geri-bildirim")
GB_DEPO = AYAR.get("geri_bildirim_depo")  # --github hedefi (yoksa yalnız ortak klasör)
GUNLUK = os.path.expanduser(AYAR.get("gunluk") or "~/Library/Logs/suflor-aktarici.log")
GUNLUK_RX = re.compile(r"EKLENTİ|WHISPER|SES MODELİ|nabız|hata|HATA|UYARI|Traceback|Error|BAŞLAT|DİSK|TAKVİM|KANIT|aktarıcı çalışıyor")
def _calistir(fn, **kw):
    import io, contextlib
    old = {k: getattr(A, k, None) for k in kw}
    for k, v in kw.items(): setattr(A, k, v)
    b = io.StringIO()
    try:
        with contextlib.redirect_stdout(b): fn()
    except SystemExit as e: b.write(f"({e})\n")
    except Exception as e: b.write(f"(hata: {e})\n")
    finally:
        for k, v in old.items(): setattr(A, k, v)
    return b.getvalue().strip()
def rapor_cmd():
    md = toplanti_dosyasi(A.dosya)
    if not md: sys.exit("toplantı dosyası yok")
    rs = kayitlar(md); baslik = ""
    try: baslik = re.sub(r"^# Canlı transkript — ", "", open(os.path.join(A.dir, md), encoding="utf-8").readline().strip())
    except OSError: pass
    ort = lambda t: (t.replace(baslik, "<toplantı>") if baslik else t).replace(md[:-3], "<dosya>").replace(os.path.expanduser("~"), "~")
    try: st = get("/status")
    except Exception: st = {}
    x = st.get("extension") or {}; wv = st.get("whisper") or {}
    try: man = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json"))).get("version")
    except Exception: man = "?"
    sh = lambda *c: (subprocess.run(list(c), capture_output=True, text=True).stdout or "").strip()
    for k in ("takip", "karar"): setattr(A, k, getattr(A, k, None))  # karne_hesap bunları okur (rapor ayrıştırıcısında yok)
    try: v = karne_hesap(md); sf = v["suflor"]
    except Exception as e: v, sf = {"olcu": {}, "rol": "?"}, {}
    satir = [r for r in rs if "text" in r]; kaynak = {}
    for r in satir: kaynak[r.get("src") or r.get("source") or "?"] = kaynak.get(r.get("src") or r.get("source") or "?", 0) + 1
    zam = [zaman(r["at"]) for r in rs if r.get("at")]
    t0, t1 = (min(zam).astimezone(), max(zam).astimezone()) if zam else (None, None)
    g = []
    try:
        for l in open(GUNLUK, encoding="utf-8", errors="replace"):
            m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) ", l)
            if not m or not GUNLUK_RX.search(l): continue
            if t0:
                an = datetime.datetime.fromisoformat(m.group(1)).astimezone()
                if not (t0 - datetime.timedelta(minutes=15) <= an <= t1 + datetime.timedelta(minutes=10)): continue
            g.append(ort(l.rstrip())[:300])
    except OSError: g.append("(günlük okunamadı)")
    ag = {}
    try: ag = json.load(open(os.path.join(A.dir, "agenda.json"), encoding="utf-8"))
    except Exception: pass
    import getpass
    tarih = (t0 or datetime.datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M")
    out = [f"# Suflor.me geri bildirim — {tarih} · alan {AYAR.get('alan')} · hesap {getpass.getuser()}", "",
           "İçerik yok: döküm, kart metni ve adlar yazılmadı (toplantı adı <toplantı>).", "", "## Ortam",
           f"- Sürüm: aktarıcı {st.get('surum', '?')} · eklenti (çalışan) {x.get('ver', '?')} · kod {man}",
           f"- Mac: {sh('sysctl', '-n', 'hw.model')} · macOS {sh('sw_vers', '-productVersion')} · bellek {round(int(sh('sysctl', '-n', 'hw.memsize') or 0) / 2**30)} GB · boş ~{(st.get('bellek') or {}).get('bos_gb', '?')} GB",
           f"- Claude modeli (ayar): {AYAR.get('claude_model') or 'varsayılan'} · platform {x.get('platform') or '?'} · rol {v.get('rol') or ag.get('rol') or '?'} · dil {ag.get('dil') or '?'}",
           f"- Whisper: {wv.get('durum', '?')} · ses modeli {wv.get('ses_model', '?')} · yankı {wv.get('yanki', 0)}", "",
           "## Toplantı (sayılar)",
           f"- Süre ~{round((t1 - t0).total_seconds() / 60) if t0 else '?'} dk · satır {len(satir)} (kaynak: " + ", ".join(f"{k} {n}" for k, n in kaynak.items()) + f") · not {sum(1 for r in rs if 'note' in r)} · kanıt {sum(1 for r in rs if 'kanit' in r)}",
           f"- Kartlar: {sf.get('kart', '?')} ({sf.get('saatte', '?')}/saat; " + ", ".join(f"{k} {n}" for k, n in (sf.get("tur") or {}).items()) + f") · isabet ✓/(✓+✕) {sf.get('isabet')} · SORU→CEVAP ortanca {sf.get('cevap_ortanca_sn')} sn",
           f"- Karne: {v.get('puan', '-')}/5 · gündem {v['olcu'].get('gundem', '?')} · " + " · ".join(f"{a} {round(b[0])}" for a, b in (v.get("boyut") or {}).items()), "", "## Ölçüm (`olcum`)", "```", ort(_calistir(olcum, dosya=md)), "```", "",
           "## Gözlemler (Claude ve kullanıcı)", A.notlar.strip() or "(yok)", "",
           f"## Aktarıcı günlüğü (teknik satırlar, toplantı ±15 dk; {len(g)} satır)", "```", *(g[-150:] or ["(yok)"]), "```"]
    metin = "\n".join(out) + "\n"
    if A.goster: print(metin); return
    d = GB_DIR()
    try:
        os.makedirs(d, exist_ok=True)
        fp = os.path.join(d, f"{(t0 or datetime.datetime.now()).strftime('%Y%m%d-%H%M')}-{re.sub(r'[^A-Za-z0-9]+', '', str(AYAR.get('alan')))}-{getpass.getuser()}.md")
        with open(fp, "w", encoding="utf-8") as f: f.write(metin)
        os.chmod(fp, 0o644); print(f"geri bildirim yazıldı: {fp}")
    except OSError as e:
        fp = os.path.join(A.dir, "geri-bildirim-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") + ".md"); open(fp, "w", encoding="utf-8").write(metin)
        print(f"ortak klasöre yazılamadı ({e}) — {fp} (geliştiriciye elle ilet; kurulum: aktarici-kur.command klasörü açar)")
    if A.github and not GB_DEPO: print("GitHub deposu ayarda yok (geri_bildirim_depo) — yalnız ortak klasöre yazıldı")
    elif A.github:
        r = subprocess.run(["gh", "issue", "create", "-R", GB_DEPO, "--title", f"Geri bildirim {tarih} · {AYAR.get('alan')}", "--body-file", fp], capture_output=True, text=True)
        print(("GitHub: " + r.stdout.strip()) if r.returncode == 0 else f"GitHub konusu açılamadı: {(r.stderr or '').strip()[:200]} (ortak klasördeki dosya yeterli)")
def geri_bildirim_cmd():
    d = GB_DIR(); kayit = os.path.expanduser("~/Library/Application Support/Suflor/okunan-raporlar.json")
    try: okunan = set(json.load(open(kayit)))
    except Exception: okunan = set()
    try: fs = sorted(f for f in os.listdir(d) if f.endswith(".md"))
    except OSError: fs = []
    yeni = [f for f in fs if f not in okunan]
    if A.okundu:
        os.makedirs(os.path.dirname(kayit), exist_ok=True); json.dump(sorted(okunan | set(fs)), open(kayit, "w")); print(f"{len(yeni)} rapor okundu işaretlendi"); return
    ls = yeni if A.yeni else fs
    if not ls: print("" if A.yeni else f"rapor yok ({d})"); return
    print(f"Suflor.me geri bildirim: {len(yeni)} okunmamış rapor ({d}) — oku, sorunları değerlendir, sonra `toplanti-claude.py geri-bildirim --okundu`")
    for f in ls: print(("• " if f in yeni else "  ") + os.path.join(d, f))
def _hms(sn):
    if sn is None: return "?"
    return f"{sn // 3600}:{sn % 3600 // 60:02d}:{sn % 60:02d}" if sn >= 3600 else f"{sn // 60}:{sn % 60:02d}"

try:
    {"kart": kart, "hazir": hazir, "izle": izle, "olcum": olcum, "ara": ara_cmd, "sozluk": sozluk_cmd, "acik": acik_cmd, "gundem": gundem_cmd,
     "kanit": kanit_cmd, "karne": karne_cmd, "hazirlik": hazirlik_cmd,
     "karsilastir": karsilastir_cmd, "kesinlik": kesinlik_cmd, "koc": koc_cmd, "anlar": anlar_cmd, "saglik": saglik_cmd, "takvim": takvim_cmd, "rapor": rapor_cmd, "geri-bildirim": geri_bildirim_cmd}[A.cmd]()
except KeyboardInterrupt: pass
