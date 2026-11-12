#!/usr/bin/env python3
# Suflor.me — Kesişim (F1, 12 Kasım 2026): günlük çapraz kontrol. Proje veritabanı + Tazı dizini + takvim katmanı + rutin izleri tek bulgu şemasıyla karşılaştırılır.
# Tasarım: ../planlar/kesisim-mimari-20261111.md (§1–3, §7, §8). F1 kapsamı: kural tabanlı, belirlenimci, model/çözücü/pano YOK; ağa hiçbir şey göndermez.
#   python3 -B kesisim.py kos [--canli DIR] [--json] [--kuru] [--vt YOL] [--tazi DIR]   (canlı klasör varsayılanı: ayardaki uygulama klasörü/canli)
#   python3 -B kesisim.py belirsiz [--canli DIR]    (belirsiz adaylar; F2 çözücüsüne teslim biçimi)
# Okuma: proje veritabanı baglayici üzerinden YALNIZ SALT OKUNUR (mode=ro); tazi.db salt okunur (indeksle ÇAĞRILMAZ), son.json/iletisim.jsonl salt okunur. veritabanına ve Tazı'ya yazılmaz.
#   Yazılan tek şey: <canli>/kesisim.json (bugün) ve kesisim.jsonl (geçmiş; metin yok: zaman, id, tur, durum).
# Bulgu: id (tur+varlık+kaynaklar+alandan sabit özet), tur (celiski|eksik|bayat|yeni|bekleyen|rutin), varlik (kisi:<veritabanı id> | firma:<alan adı> | sistem:<ad>; veritabanında karşılığı olmayan Tazı kişisi
#   kisi:~<tazi id>), ozet (tek cümle), kaynaklar [{sistem, kayit, baglanti}], kanit {ham, duzey} (Tazı A–D ve K0–K3 ortak ölçek: A/K3=3 B/K2=2 C/K1=1 D/K0=0; birden çok kaynakta en zayıf halka),
#   ilk_gorulme, durum (yeni|suruyor|kapandi|ertelendi; önceki koşudan taşınır), onerilen_eylem, belirsiz (True: kural karar veremedi, model bakacak; "karsilastirma" {a, b} taşır).
# Gizlilik: gelistirici değilse çıkar (beta'da kapalı); gizli toplantı açıksa çıkar (gizli=True); kişisel/sağlık kaydı (#53: OZEL_RX) bulguya hiç girmez, yalnız sayısı yazılır.
import argparse, datetime, hashlib, json, os, re, sqlite3, sys, time
sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.abspath(__file__))
if KOK not in sys.path: sys.path.insert(0, KOK)
import baglayici

SURUM = 1
TAZI_VARSAYILAN = "~/Library/Application Support/Suflor/tazi"
AYAR_VARSAYILAN = "~/Library/Application Support/Suflor/ayar.json"
TUR_SIRA = ("celiski", "eksik", "bayat", "bekleyen", "yeni", "rutin")
YAKIN_GUN, YAKIN_DAR_GUN = 14, 3          # yaklaşan toplantı penceresi; bayatlık için dar pencere
TAZI_BAYAT_GUN, FIRMA_BAYAT_GUN = 30, 30   # yaklaşan toplantıdaki firma dosyası / dis_firma kaydı bu kadar günden eskiyse bayat
YENI_SAAT, BEKLEYEN_GUN = 24, 3
OVERLAP_ESIK = 0.12                        # web_ozet ↔ Tazı kimlik: ortak belirgin sözcük oranı bunun altındaysa belirsiz aday
DUZEY = {"A": 3, "B": 2, "C": 1, "D": 0, "K3": 3, "K2": 2, "K1": 1, "K0": 0}
# #53: sağlık ve özel nitelikli kişisel kayıtlar hiçbir belgeye girmez. Veritabanında kategori sütunu yok; metin süzgeci (kişiyle ilgili alanlara: öneri, çelişki, takvim başlığı) — eşleşen satır atlanır.
OZEL_RX = re.compile(r"(?i)(sağlık|saglik|hastane|hastalık|hastalik|\bhasta\b|doktor|ameliyat|tedavi|muayene|\bilaç|\bilac|rahatsızlık|rahatsizlik|gebelik|hamile|doğum izni|dogum izni|"
                     r"kanser|terapi|psikolog|psikiyatr|tahlil|medical|doctor|hospital|surgery|therapy|pregnan|diagnos|cenaze|funeral|boşanma|bosanma|divorce|sick leave|hastalık izni)")
TUKETICI = {"gmail.com", "googlemail.com", "icloud.com", "me.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "proton.me", "protonmail.com"}
ALTYAPI = {"google.com", "microsoft.com", "zoom.us", "calendly.com", "teams.microsoft.com", "meet.google.com", "docs.google.com", "calendar.google.com", "basecamp.com"}
BENIM_TUR = ("sirket", "m365", "takma_ad", "hizmet", "kullanilmiyor")
TEKNIK_BULGU = {"dns", "alan_adi", "sertifika", "teknoloji", "site", "varlik", "baglanti"}   # "yeni" bulgu sayılmaz: gürültü

# ---------- yardımcılar ----------
def _zaman(s):
    s = str(s or "").strip()
    if not s: return None
    s = s[:19].replace(" ", "T")
    if len(s) == 10: s += "T00:00:00"
    try: return datetime.datetime.fromisoformat(s)
    except ValueError: return None
def _iso(d): return d.isoformat(timespec="seconds")
def _cumle(m, n=170):
    m = " ".join(str(m or "").split())
    m = re.split(r"(?<=[.!?])\s", m, maxsplit=1)[0]
    return m if len(m) <= n else m[:n - 1].rstrip() + "…"
def _json_liste(v):
    try: r = json.loads(v) if isinstance(v, str) else v
    except ValueError: return []
    return [str(x) for x in r] if isinstance(r, list) else []
def _ozel(*metin): return any(OZEL_RX.search(str(m or "")) for m in metin)
def _kanit(*ham):
    """ortak ölçek: en zayıf halka; tanınmayan derece 0 sayılır"""
    ks = [(DUZEY.get(str(h or "").strip().upper(), 0), str(h or "?").strip().upper() or "?") for h in ham] or [(0, "?")]
    d, h = min(ks)
    return {"ham": h, "duzey": d}
def _bid(tur, varlik, kaynaklar, alan):
    ks = "+".join(sorted(f"{k['sistem']}:{k['kayit']}" for k in kaynaklar))
    return hashlib.sha1(f"{tur}|{varlik}|{ks}|{alan}".encode()).hexdigest()[:16]
def _bulgu(tur, varlik, ozet, kaynaklar, kanit, alan, eylem, belirsiz=False, karsilastirma=None):
    b = {"id": _bid(tur, varlik, kaynaklar, alan), "tur": tur, "varlik": varlik, "ozet": ozet, "kaynaklar": kaynaklar, "kanit": kanit,
         "ilk_gorulme": None, "durum": "yeni", "onerilen_eylem": eylem, "belirsiz": bool(belirsiz)}
    if karsilastirma: b["karsilastirma"] = karsilastirma
    return b
def _k_vt(tablo, kayit, url=None): return {"sistem": "vt", "kayit": f"{tablo}/{kayit}", "baglanti": url or f"vt#{tablo}/{kayit}"}
def _k_tazi(kid, no=None, url=None): return {"sistem": "tazi", "kayit": f"{kid}" + (f"#{no}" if no is not None else ""), "baglanti": url or f"tazi/dosya/{kid}.json" + (f"#{no}" if no is not None else "")}
def _json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f: return json.load(f)
    except Exception: return varsayilan
def _yaz_atomik(yol, metin):
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    t = yol + ".tmp"
    with open(os.open(t, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f: f.write(metin)
    os.replace(t, yol)

def gelistirici_mi(ayar):  # relay.py gelistirici_mi() ile aynı ölçüt: ayar gelistirici true ya da kod klasörü git klonu (SUFLOR_TEST_KOD deneme için)
    if (ayar or {}).get("gelistirici") is True: return True
    k = os.path.expanduser(os.environ.get("SUFLOR_TEST_KOD") or str((ayar or {}).get("kod") or "")) or KOK
    if not os.path.isdir(k): k = KOK   # ayardaki kod klasörü yoksa modülün kendi klasörüne bak
    return os.path.isdir(os.path.join(k, ".git"))

# ---------- kaynak okuyucular (yalnız okuma) ----------
class _VT:
    """Proje veritabanı: baglayici._Sqlite (mode=ro). Sorgu hatası okunamayan listesine girer; bağlantı yoksa tüm sorgular []"""
    def __init__(self, b): self.b = b; self.hatalar = []
    def q(self, sql, param=()):
        r = self.b._calistir(sql, param)
        if self.b.son_hata: self.hatalar.append(f"{sql[:40]}…: {self.b.son_hata}")
        return r
    def acik(self): return self.b.dene() is None
def _vt_ac(vt, ayar):
    if vt: return _VT(baglayici._Sqlite(os.path.expanduser(vt), {}, ""))
    k = baglayici.yukle(ayar or {})
    if k and k[0].yol: return _VT(k[0])
    return None

def _tazi_oku(dizin):
    """tazi.db salt okunur (indeksle çağrılmaz) + son.json + iletisim.jsonl → sözlük; db yoksa {"yok": True}"""
    yol = os.path.join(dizin, "tazi.db")
    t = {"yok": True, "kayit": {}, "oge": [], "bulgu": [], "iletisim": [], "son_indeks": None, "tarama": {}}
    if not os.path.isfile(yol): return t
    import pathlib
    try:
        con = sqlite3.connect(pathlib.Path(yol).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        con.execute("PRAGMA query_only=1")
    except sqlite3.Error: return t
    try:
        for r in con.execute("SELECT id, ad, tur, alanlar, eposta_iz FROM kayit"):
            t["kayit"][r[0]] = {"id": r[0], "ad": r[1], "tur": r[2], "alanlar": _json_liste(r[3]), "eposta_iz": _json_liste(r[4])}
        t["oge"] = [dict(zip(("kayit", "no", "bolum", "metin", "kaynak", "derece", "tarih", "eklendi", "acik"), r))
                    for r in con.execute("SELECT kayit, no, bolum, metin, kaynak, derece, tarih, eklendi, acik FROM dosya_oge")]
        t["bulgu"] = [dict(zip(("kayit", "tur", "ozet", "derece", "ilk", "durum", "anahtar", "kaynak"), r))
                      for r in con.execute("SELECT kayit, tur, ozet, derece, ilk_gorulme, durum, anahtar, kaynak FROM bulgu")]
        m = con.execute("SELECT v FROM meta WHERE k='son_indeks'").fetchone()
        t["son_indeks"] = m[0] if m else None
        t["yok"] = False
    except sqlite3.Error: t["yok"] = True
    finally: con.close()
    son = _json_oku(os.path.join(dizin, "son.json"), {})
    t["tarama"] = {k: v.get("tarih") for k, v in (son.get("kayitlar") or {}).items() if isinstance(v, dict)}
    try:
        with open(os.path.join(dizin, "iletisim.jsonl"), encoding="utf-8") as f:
            for l in f:
                try: r = json.loads(l)
                except ValueError: continue
                if isinstance(r, dict) and r.get("kayit") and r.get("deger"): t["iletisim"].append(r)
    except OSError: pass
    return t

# ---------- ana koşu ----------
def kos(canli=None, vt=None, tazi_dizin=None, ayar=None, simdi=None, gizli=False, yaz=True, gelistirici=None):
    """→ sonuç sözlüğü (kesisim.json içeriği); atlanırsa {"atlandi": neden}. canli verilirse (ve yaz) kesisim.json/.jsonl yazılır."""
    t0 = time.perf_counter()
    ayar = ayar if isinstance(ayar, dict) else _json_oku(os.path.expanduser(os.environ.get("SUFLOR_AYAR") or AYAR_VARSAYILAN), {})
    RUTIN = [x for x in (ayar.get("kesisim_rutinler") or []) if isinstance(x, dict) and x.get("ad")]   # izlenecek zamanlanmış rutinler (ayar; koda gömülü değil)
    if gizli: return {"atlandi": "gizli"}
    if not (gelistirici if gelistirici is not None else gelistirici_mi(ayar)): return {"atlandi": "gelistirici_degil"}
    simdi = simdi or datetime.datetime.now()
    bugun = simdi.date()
    canli = os.path.expanduser(canli) if canli else None
    tdir = os.path.expanduser(tazi_dizin or os.environ.get("TAZI_DIR") or TAZI_VARSAYILAN)
    O = _vt_ac(vt, ayar)
    vt_acik = bool(O and O.acik())
    T = _tazi_oku(tdir)
    B, suzulen, kaynaklar = [], {"ozel": 0}, []
    own = {baglayici.alan_norm("onmicrosoft.com")}

    def kaynak(ad, son, beklenen_sn, bulgu=True, durum=None):
        s = _zaman(son) if not isinstance(son, datetime.datetime) else son
        yas = (simdi - s).total_seconds() if s else None
        d = durum or ("yok" if s is None else ("bayat" if yas > beklenen_sn else "taze"))
        kaynaklar.append({"ad": ad, "son_okuma": _iso(s) if s else None, "beklenen_sn": beklenen_sn, "yas_sn": int(yas) if yas is not None else None, "durum": d, "bulgu": bulgu})
        return d, yas

    # --- Veritabanı önbelleği (tek geçiş) ---
    h = {"ad": {}, "iz": {}, "firma": {}, "kisi": {}}
    firma, hesap_alan, takvim, oneri, celiski, ayarkv, okuma_son, rutin_iz = {}, set(), [], [], [], {}, {}, None
    if vt_acik:
        h = baglayici.kimlik_haritasi(O.q)
        for r in O.q("SELECT alan_adi, ad, guncelleme, web_ozet, kaynak_url FROM dis_firma"):
            firma[baglayici.alan_norm(r[0])] = dict(alan=r[0], ad=r[1], guncelleme=r[2], web=r[3], url=r[4])
        placeholders = ",".join("?" * len(BENIM_TUR))
        for (a_,) in O.q(f"SELECT DISTINCT alan_adi FROM hesap WHERE tur IN ({placeholders}) AND alan_adi IS NOT NULL", BENIM_TUR): own.add(baglayici.alan_norm(a_))
        bas, bit = bugun.isoformat(), (bugun + datetime.timedelta(days=YAKIN_GUN)).isoformat()
        for r in O.q("SELECT id, baslangic, baslik, dis_alanlar FROM takvim_etkinlik WHERE baslangic >= ? AND baslangic < ? AND dis_alanlar IS NOT NULL AND dis_alanlar <> '[]' ORDER BY baslangic", (bas, bit)):
            if _ozel(r[2]): suzulen["ozel"] += 1; continue
            takvim.append(dict(id=r[0], bas=r[1], baslik=r[2], alanlar=[baglayici.alan_norm(a) for a in _json_liste(r[3])]))
        for r in O.q("SELECT id, tarih, metin, kisi, sistem, alan, deger, kayit_zamani, yazan FROM guncelleme_onerisi WHERE durum = 'bekliyor' OR kayit_zamani >= ? OR tarih >= ?",
                     (_iso(simdi - datetime.timedelta(hours=YENI_SAAT)), (bugun - datetime.timedelta(days=2)).isoformat())):
            if _ozel(r[2], r[3], r[4], r[5], r[6]): suzulen["ozel"] += 1; continue
            oneri.append(dict(id=r[0], tarih=r[1], metin=r[2], kisi=r[3], sistem=r[4], kz=r[7], yazan=r[8], durum=None))
        durumlar = {r[0]: r[1] for r in O.q("SELECT id, durum FROM guncelleme_onerisi")}
        for o in oneri: o["durum"] = durumlar.get(o["id"])
        for r in O.q("SELECT id, kisi_id, sistem, kayittaki_ifade, neden, kaynak FROM celiski WHERE coalesce(durum,'Açık') NOT IN ('Kapandı','Çözüldü','Kapandi','Cozuldu')"):
            if _ozel(r[2], r[3], r[4]): suzulen["ozel"] += 1; continue
            celiski.append(dict(id=r[0], kisi=r[1], sistem=r[2], ifade=r[3], neden=r[4], kaynak=r[5]))
        belirtimler = [str(v) for x in RUTIN for v in ((x.get("iz") if isinstance(x.get("iz"), list) else [x.get("iz")]) + [x.get("kapali")]) if v]
        soru_ayar = tuple(sorted({v[5:] for v in belirtimler if v.startswith("ayar:")}))
        ph = ",".join("?" * len(soru_ayar))
        ayarkv = {r[0]: (r[1], r[2]) for r in O.q(f"SELECT anahtar, deger, guncelleme FROM ayar WHERE anahtar IN ({ph})", soru_ayar)} if soru_ayar else {}
        okuma_son = {r[0]: r[1] for r in O.q("SELECT kaynak, max(zaman) FROM okuma GROUP BY kaynak")}
        tk_okuma = (O.q("SELECT max(okuma) FROM takvim_etkinlik") or [[None]])[0][0]
        rutin_iz = (O.q("SELECT max(z) FROM (SELECT max(kayit_zamani) z FROM guncelleme_onerisi WHERE yazan = 'rutin' UNION ALL SELECT max(kayit_zamani) FROM olay WHERE yazan = 'rutin')") or [[None]])[0][0]
    else: tk_okuma = None

    # --- Tazı bağlantıları ---
    link, alan_kayit = {}, {}
    for kid, k in T["kayit"].items():
        kisi, alan = baglayici.kimlik_esle(h, k["ad"], k["alanlar"], k["eposta_iz"])
        k["kisi"], k["alan"] = kisi, alan
        k["varlik"] = ("kisi:" + kisi) if kisi else ("firma:" + alan) if alan else ("firma:" + baglayici.alan_norm(k["alanlar"][0])) if k["alanlar"] else "kisi:~" + kid
        for a in k["alanlar"]: alan_kayit.setdefault(baglayici.alan_norm(a), kid)
    ogeler = {}
    for o in T["oge"]: ogeler.setdefault(o["kayit"], []).append(o)
    def vt_kaynagi(k):
        if k.get("kisi"): return [_k_vt("kisi", k["kisi"])]
        if k.get("alan") and k["alan"] in firma: return [_k_vt("dis_firma", firma[k["alan"]]["alan"], firma[k["alan"]].get("url") if str(firma[k["alan"]].get("url") or "").startswith("http") else None)]
        return []

    # --- ÇELİŞKİ ---
    for o in T["oge"]:   # C1: Tazı dosyasında açık çelişki (Tazı kaynaklar arasında yakaladı; veritabanı bağlıysa onun kaydı ikinci kaynak)
        if o["bolum"] != "celiski" or not o["acik"] or o["kayit"] not in T["kayit"]: continue
        k = T["kayit"][o["kayit"]]
        ks = [_k_tazi(k["id"], o["no"], o["kaynak"] if str(o["kaynak"] or "").startswith("http") else None)] + vt_kaynagi(k)
        B.append(_bulgu("celiski", k["varlik"], f"{k['ad']}: kaynaklar ayrışıyor — {_cumle(o['metin'])}", ks, _kanit(o["derece"]), f"tazi-celiski-{o['no']}",
                        "Çelişkiyi ilgili kaynakla doğrula; doğruysa veritabanı kaydını (dis_firma.web_ozet / kisi) kaynaklı öneriyle düzelt"))
    for r in T["iletisim"]:   # C2: Tazı kaydının adı veritabanında bir kişiye bağlı, ama kaydın e-posta adresi veritabanında başka kişiye ait (e-posta izi eşleşmesi ad eşleşmesini ezdiği için ad ayrıca bakılır)
        if r.get("tur") != "eposta" or str(r.get("derece") or "").upper() not in ("A", "B"): continue
        k = T["kayit"].get(r["kayit"])
        n = baglayici.ad_norm(k["ad"]) if k else ""
        ad_kisi = h["ad"].get(n) if len(n) >= 4 else None
        sahip = h["iz"].get(baglayici.eposta_iz(r["deger"]))
        if not ad_kisi or not sahip or sahip == ad_kisi: continue
        ks = [_k_tazi(k["id"]), _k_vt("kisi", ad_kisi), _k_vt("hesap", baglayici.eposta_iz(r["deger"]))]
        B.append(_bulgu("celiski", "kisi:" + ad_kisi, f"{k['ad']} için Tazı'daki e-posta adresi veritabanında başka bir kişiye ({h['kisi'].get(sahip, sahip)}) kayıtlı.", ks, _kanit(r.get("derece"), "K2"),
                        "eposta-" + baglayici.eposta_iz(r["deger"]), "Adresin gerçek sahibini kaynakla doğrula; hangisi yanlışsa onu düzelt"))
    for kid, k in T["kayit"].items():   # C3/C4: dis_firma ↔ Tazı kayıt adı ve açıklaması
        f = firma.get(k.get("alan") or "")
        if not f or k.get("kisi"): continue
        n1, n2 = baglayici.ad_norm(f["ad"]), baglayici.ad_norm(k["ad"])
        ks = [_k_vt("dis_firma", f["alan"]), _k_tazi(kid)]
        if n1 and n2 and n1 != n2 and n1 not in n2 and n2 not in n1:
            B.append(_bulgu("celiski", k["varlik"], f"Firma adı iki kaynakta farklı: veritabanı «{f['ad']}», Tazı «{k['ad']}».", ks, _kanit("K1", "C"), "ad", "Aynı firma mı, farklı mı? Aynıysa adı eşitle",
                            belirsiz=True, karsilastirma={"a": {"sistem": "vt", "metin": f["ad"]}, "b": {"sistem": "tazi", "metin": k["ad"]}}))
        web = str(f.get("web") or "")
        kim = " ".join(o["metin"] for o in ogeler.get(kid, []) if o["bolum"] == "kimlik")
        if web.strip("- ") and not web.startswith("Web izi bulunamadı") and kim:
            sa, sb = (set(re.findall(r"[a-zçğıöşü0-9]{5,}", x.casefold())) for x in (web, kim))
            if sa and sb and len(sa & sb) / min(len(sa), len(sb)) < OVERLAP_ESIK:
                B.append(_bulgu("celiski", k["varlik"], f"{k['ad']}: veritabanındaki açıklama ile Tazı kimlik hükmü neredeyse hiç örtüşmüyor; aynı firmayı mı anlatıyorlar?", ks, _kanit("K1", "C"), "web-ozet",
                                "Model: iki açıklamayı karşılaştır; çelişen olgu varsa kaynaklı düzeltme öner", belirsiz=True,
                                karsilastirma={"a": {"sistem": "vt", "metin": web[:600]}, "b": {"sistem": "tazi", "metin": kim[:600]}}))
    for c in celiski:   # C5: veritabanının kendi açık çelişki kaydı (tek şemada görünsün; yeni çelişki yazılmaz)
        v = ("kisi:" + c["kisi"]) if c["kisi"] else "sistem:" + str(c["sistem"] or "vt")
        B.append(_bulgu("celiski", v, f"Veritabanında açık çelişki kaydı: {_cumle(c['neden'] or c['ifade'])}", [_k_vt("celiski", c["id"])], _kanit("K1"), f"vt-celiski-{c['id']}",
                        "Kaynağa bakıp çözüm kararını kayıt kapısı üzerinden ver"))

    # --- EKSİK / BAYAT (takvim ↔ dis_firma ↔ Tazı) ---
    yarin = bugun + datetime.timedelta(days=YAKIN_DAR_GUN)
    yaklasan = {}
    for e in takvim:
        for a in e["alanlar"]:
            if a in own or a in TUKETICI or a in ALTYAPI: continue
            yaklasan.setdefault(a, []).append(e)
    for a, evs in sorted(yaklasan.items()):
        e = evs[0]; ek = _k_vt("takvim_etkinlik", e["id"][:24])
        gun = _zaman(e["bas"]).date() if _zaman(e["bas"]) else bugun
        gecen = f"{e['bas'][:10]} «{_cumle(e['baslik'], 60)}»"
        if a not in firma:
            B.append(_bulgu("eksik", "firma:" + a, f"Takvimdeki dış alan {a} ({gecen}) dis_firma tablosunda yok.", [ek], _kanit("A"), "takvim-dis_firma",
                            "Tazı'dan kimlik hükmü al; dis_firma'ya kaynaklı öneriyle ekle"))
        kid = alan_kayit.get(a)
        if not kid:
            B.append(_bulgu("eksik", "firma:" + a, f"Takvimdeki dış alan {a} ({gecen}) için Tazı kaydı yok.", [ek], _kanit("A"), "takvim-tazi", "Tazı adayı olarak ekle ve tara"))
        elif not [o for o in ogeler.get(kid, []) if o["bolum"] != "soru"]:
            B.append(_bulgu("eksik", "firma:" + a, f"{a} için Tazı kaydı var ama dosyası boş ({gecen}).", [ek, _k_tazi(kid)], _kanit("A"), "tazi-dosya-bos", "Tazı taraması yap, dosyayı doldur"))
        if gun <= yarin:   # B1: yakın toplantı, eski dosya
            if kid:
                son = _zaman(T["tarama"].get(kid)) or _zaman(next((b["ilk"] for b in T["bulgu"] if b["kayit"] == kid), None))
                if son and (simdi - son).days > TAZI_BAYAT_GUN:
                    B.append(_bulgu("bayat", "firma:" + a, f"{a} toplantısı {e['bas'][:10]} günü; Tazı dosyasının son taraması {(simdi - son).days} gün önce.", [ek, _k_tazi(kid)], _kanit("A"), "tazi-tarama",
                                    "Toplantıdan önce hızlı Tazı taraması yap"))
            f = firma.get(a)
            if f and _zaman(f["guncelleme"]) and (simdi - _zaman(f["guncelleme"])).days > FIRMA_BAYAT_GUN:
                B.append(_bulgu("bayat", "firma:" + a, f"{a} toplantısı {e['bas'][:10]} günü; dis_firma kaydı {(simdi - _zaman(f['guncelleme'])).days} gündür güncellenmedi.", [ek, _k_vt("dis_firma", f["alan"])],
                                _kanit("A"), "dis_firma-guncelleme", "dis_firma'yı Tazı hükmüyle güncelle"))
    for kid, k in T["kayit"].items():   # E4: Tazı'da firma var, veritabanında hiçbir izi yok
        al = [baglayici.alan_norm(a) for a in k["alanlar"] if baglayici.alan_norm(a) not in own and baglayici.alan_norm(a) not in TUKETICI]
        if vt_acik and k["tur"] == "firma" and al and not k.get("kisi") and not k.get("alan"):
            B.append(_bulgu("eksik", "firma:" + al[0], f"Tazı'da izlenen {k['ad']} veritabanında (dis_firma ya da dış kişi olarak) kayıtlı değil.", [_k_tazi(kid)], _kanit("B"), "tazi-vt", "Toplantı ya da iş bağı varsa dis_firma'ya kaynaklı öneriyle ekle"))
    for r in T["iletisim"]:   # E3: Tazı'da iletişim (e-posta) var, veritabanında yok
        if r.get("tur") != "eposta" or str(r.get("derece") or "").upper() not in ("A", "B") or not vt_acik: continue
        k = T["kayit"].get(r["kayit"])
        if not k or not (k.get("kisi") or k.get("alan")) or baglayici.eposta_iz(r["deger"]) in h["iz"]: continue
        B.append(_bulgu("eksik", k["varlik"], f"{k['ad']} için Tazı'daki e-posta adresi hesap kayıtlarında yok.", [_k_tazi(k["id"])] + vt_kaynagi(k), _kanit(r.get("derece")),
                        "eposta-" + baglayici.eposta_iz(r["deger"]), "Adresi kaynakla veritabanına öneri olarak ekle"))

    # --- YENİ (son 24 sa) ---
    sinir = simdi - datetime.timedelta(hours=YENI_SAAT)
    gruplar = {}
    for b in T["bulgu"]:
        z = _zaman(b["ilk"])
        if b["durum"] == "yeni" and z and z >= sinir.replace(hour=0, minute=0, second=0) and b["tur"] not in TEKNIK_BULGU and b["kayit"] in T["kayit"]:
            gruplar.setdefault(b["kayit"], []).append(b)
    for kid, bs in sorted(gruplar.items()):
        k = T["kayit"][kid]; sayim = {}
        for b in bs: sayim[b["tur"]] = sayim.get(b["tur"], 0) + 1
        B.append(_bulgu("yeni", k["varlik"], f"{k['ad']}: son taramada {len(bs)} yeni bulgu ({', '.join(f'{t} {n}' for t, n in sorted(sayim.items()))}).", [_k_tazi(kid)], _kanit(*[b["derece"] for b in bs]),
                        "tazi-bulgu-" + min(str(b["ilk"])[:10] for b in bs), "Rapora bak; veritabanı kaydıyla çelişen ya da önemli olan var mı kontrol et"))
    for o in T["oge"]:
        z = _zaman(o["eklendi"])
        if o["bolum"] in ("bayrak", "iddia", "celiski") and o["acik"] and z and z >= sinir.replace(hour=0, minute=0, second=0) and o["kayit"] in T["kayit"] and o["bolum"] != "celiski":
            k = T["kayit"][o["kayit"]]
            B.append(_bulgu("yeni", k["varlik"], f"{k['ad']}: Tazı dosyasına yeni {o['bolum']} eklendi — {_cumle(o['metin'], 130)}", [_k_tazi(k["id"], o["no"])], _kanit(o["derece"]), f"tazi-oge-{o['no']}", "İddiayı kanıtla sına"))
    for r in T["iletisim"]:
        z = _zaman(r.get("eklendi"))
        if z and z >= sinir.replace(hour=0, minute=0, second=0) and r["kayit"] in T["kayit"]:
            k = T["kayit"][r["kayit"]]
            B.append(_bulgu("yeni", k["varlik"], f"{k['ad']} için yeni iletişim bilgisi eklendi ({r.get('tur')}).", [_k_tazi(k["id"])], _kanit(r.get("derece")), "iletisim-" + hashlib.sha1(str(r["deger"]).encode()).hexdigest()[:8],
                            "veritabanı kayıtlarıyla karşılaştır"))
    for o in oneri:
        z = _zaman(o["kz"])
        if o["durum"] == "bekliyor" and z and z >= sinir:
            B.append(_bulgu("yeni", ("kisi:" + str(h["ad"].get(baglayici.ad_norm(o["kisi"]), ""))) if o["kisi"] and h["ad"].get(baglayici.ad_norm(o["kisi"])) else "sistem:" + str(o["sistem"] or "vt"),
                            f"{o['yazan'] or 'rutin'} yeni öneri açtı: {_cumle(o['metin'], 120)}", [_k_vt("guncelleme_onerisi", o["id"])], _kanit("K1"), f"oneri-{o['id']}", "Öneriye bak; kanıtlıysa işle"))

    # --- BEKLEYEN ---
    for o in oneri:
        z = _zaman(o["kz"]) or _zaman(o["tarih"])
        if o["durum"] == "bekliyor" and z and (simdi - z).days > BEKLEYEN_GUN - 0 and (simdi - z) >= datetime.timedelta(days=BEKLEYEN_GUN):
            B.append(_bulgu("bekleyen", "sistem:" + str(o["sistem"] or "vt"), f"Öneri kuyruğunda {(simdi - z).days} gündür bekliyor: {_cumle(o['metin'], 120)}", [_k_vt("guncelleme_onerisi", o["id"])], _kanit("K1"), f"oneri-{o['id']}",
                            "Kanıta bakıp işle ya da reddet"))

    # --- KAYNAK TAZELİĞİ + RUTİN SAĞLIĞI ---
    def bayat_bulgu(ad, d, yas, esik, eylem, tur="bayat"):
        if d in ("bayat",):
            B.append(_bulgu(tur, "sistem:" + ad, f"{ad}: son iz {int(yas // 3600)} saat önce; beklenen en çok {int(esik // 3600)} saat.", [{"sistem": "kesisim", "kayit": ad, "baglanti": "kesisim.json#kaynaklar"}], _kanit("A" if tur == "bayat" else "C"), "tazelik", eylem))
    if O is None: kaynaklar.append({"ad": "Proje veritabanı", "son_okuma": None, "beklenen_sn": 0, "yas_sn": None, "durum": "yok", "bulgu": False})
    elif not vt_acik:
        kaynaklar.append({"ad": "Proje veritabanı", "son_okuma": None, "beklenen_sn": 86400, "yas_sn": None, "durum": "okunamadi", "bulgu": True})
        B.append(_bulgu("bayat", "sistem:Proje veritabanı", "Proje veritabanı okunamadı; veritabanıyla ilgili kurallar bu koşuda çalışmadı.", [{"sistem": "kesisim", "kayit": "Proje veritabanı", "baglanti": "kesisim.json#kaynaklar"}], _kanit("A"), "okunamadi",
                        "launchd altındaysa vt-izle anlık görüntüsü gerekir; yolu ve izni denetle"))
    else:
        mt = O.b.degisim_zamani()
        d, y = kaynak("Proje veritabanı (son değişiklik)", datetime.datetime.fromtimestamp(mt) if mt else None, 48 * 3600); bayat_bulgu("Proje veritabanı", d, y or 0, 48 * 3600, "Rutinlerin çalışıp çalışmadığına bak")
    if canli:
        vm = _json_oku(os.path.join(canli, "vt-mt.json"), {})
        if vm.get("kontrol"):
            d, y = kaynak("Proje veritabanı anlık görüntüsü (vt-izle)", datetime.datetime.fromtimestamp(float(vm["kontrol"])), 24 * 3600); bayat_bulgu("Proje veritabanı anlık görüntüsü", d, y or 0, 24 * 3600, "vt-izle'yi (Brifing.app) yeniden başlat")
    if T["yok"]: kaynaklar.append({"ad": "Tazı dizini", "son_okuma": None, "beklenen_sn": 4 * 86400, "yas_sn": None, "durum": "yok", "bulgu": False})
    else:
        d, y = kaynak("Tazı dizini (tazi.db)", T["son_indeks"], 4 * 86400); bayat_bulgu("Tazı dizini", d, y or 0, 4 * 86400, "tazi.py indeksle")
    tarihler = [z for z in (_zaman(v) for v in T["tarama"].values()) if z]
    if tarihler: kaynak("Tazı son tarama", max(tarihler), 8 * 86400, bulgu=False)
    rutinler = []   # (ad, son iz, beklenen sn, açıklama)
    if vt_acik:
        kaynak("Takvim okuması (takvim_etkinlik)", tk_okuma, 8 * 86400, bulgu=False)
        def iz(kaynak_adi):   # "ayar:<anahtar>" (ayar tablosunun güncelleme zamanı) | "takvim" | "rutin" (rutinin yazdığı öneri/olay) | "okuma:<parça>" (okuma kaydında kaynak adı parçası)
            if kaynak_adi.startswith("ayar:"): return ayarkv.get(kaynak_adi[5:], (None, None))[1]
            if kaynak_adi == "takvim": return tk_okuma
            if kaynak_adi == "rutin": return rutin_iz
            if kaynak_adi.startswith("okuma:"): return max((v for k_, v in (okuma_son or {}).items() if kaynak_adi[6:] in str(k_)), default=None)
            return None
        for x in RUTIN:
            if x.get("kapali") and str((ayarkv.get(str(x["kapali"])[5:]) or ("",))[0]).lower() == "kapali":
                kaynaklar.append({"ad": x["ad"], "son_okuma": None, "beklenen_sn": 0, "yas_sn": None, "durum": "kapali", "bulgu": False}); continue
            izler = [z for z in (iz(str(a)) for a in (x.get("iz") if isinstance(x.get("iz"), list) else [x.get("iz") or ""])) if z]
            rutinler.append((x["ad"], max(izler, default=None), float(x.get("esik_sa") or 36) * 3600, str(x.get("aciklama") or "")))
    if not T["yok"] and (tarihler or T["son_indeks"]):
        rutinler.append(("tazi-toplanti-dosyalari", max([z for z in tarihler + [_zaman(T["son_indeks"])] if z], default=None), 5 * 86400, "çalışma günleri 07:30; yeni dış kişi yoksa iz bırakmaz (eşik geniş)"))
    for ad, z, esik, acik in rutinler:
        d, y = kaynak(ad, z, esik, bulgu=False)
        if d == "bayat": B.append(_bulgu("rutin", "sistem:" + ad, f"Rutin {ad}: son iz {int(y // 3600)} saat önce (beklenen en çok {int(esik // 3600)} sa; {acik}). Çalışma kaydı okunamadığı için yalnız veri izinden çıkarıldı.",
                                          [{"sistem": "kesisim", "kayit": ad, "baglanti": "kesisim.json#kaynaklar"}], _kanit("C"), "rutin-sessiz", "Zamanlanmış görevin çalışma geçmişine bak; gerekirse elle çalıştır"))
        elif d == "yok": B.append(_bulgu("rutin", "sistem:" + ad, f"Rutin {ad}: hiç iz bulunamadı ({acik}).", [{"sistem": "kesisim", "kayit": ad, "baglanti": "kesisim.json#kaynaklar"}], _kanit("C"), "rutin-iz-yok", "Rutinin kurulu ve açık olduğunu denetle"))

    # --- tekilleştir, önceki koşudan durum taşı ---
    gor, tek = set(), []
    for b in B:
        if b["id"] in gor: continue
        gor.add(b["id"]); tek.append(b)
    onceki = {b["id"]: b for b in (_json_oku(os.path.join(canli, "kesisim.json"), {}).get("bulgular") or [])} if canli else {}
    gecis = []   # kesisim.jsonl: yalnız durum geçişleri
    simdi_s = _iso(simdi)
    for b in tek:
        p = onceki.get(b["id"])
        if p and p.get("durum") in ("yeni", "suruyor", "ertelendi"):
            b["ilk_gorulme"] = p.get("ilk_gorulme") or simdi_s
            b["durum"] = "ertelendi" if p["durum"] == "ertelendi" else "suruyor"
        else:
            b["ilk_gorulme"] = simdi_s; b["durum"] = "yeni"
            gecis.append({"t": simdi_s, "id": b["id"], "tur": b["tur"], "durum": "yeni"})
    for i, p in onceki.items():
        if i not in gor and p.get("durum") in ("yeni", "suruyor", "ertelendi"):
            tek.append(dict(p, durum="kapandi", kapanma=simdi_s)); gecis.append({"t": simdi_s, "id": i, "tur": p.get("tur"), "durum": "kapandi"})
    tek.sort(key=lambda b: (TUR_SIRA.index(b["tur"]) if b["tur"] in TUR_SIRA else 9, b["durum"] == "kapandi", b["varlik"], b["id"]))
    say = {}
    for b in tek:
        if b["durum"] != "kapandi": say[b["tur"]] = say.get(b["tur"], 0) + 1
    sonuc = {"surum": SURUM, "olusturma": simdi_s, "sure_sn": round(time.perf_counter() - t0, 3), "bugun": bugun.isoformat(),
             "ozet": {"toplam": sum(say.values()), "tur": say, "yeni": sum(1 for b in tek if b["durum"] == "yeni"), "kapandi": sum(1 for b in tek if b["durum"] == "kapandi"), "belirsiz": sum(1 for b in tek if b.get("belirsiz") and b["durum"] != "kapandi")},
             "kaynaklar": kaynaklar, "suzulen": suzulen, "okunamayan": (O.hatalar if O else []), "bulgular": tek}
    if canli and yaz:
        _yaz_atomik(os.path.join(canli, "kesisim.json"), json.dumps(sonuc, ensure_ascii=False, indent=1))
        if gecis:
            with open(os.open(os.path.join(canli, "kesisim.jsonl"), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "a", encoding="utf-8") as f:
                for g in gecis: f.write(json.dumps(g, ensure_ascii=False) + "\n")
    return sonuc

def belirsiz_adaylar(sonuc):
    """F2 çözücüsüne teslim: aktarıcıdaki değerlendir() adaylarıyla aynı biçim — [{"id", "metin" (kısa özet), "veri": {"tur","varlik","a","b","kaynaklar","kanit"}}].
    Çözücü kararı (düzelt|araştır|bırak) bulgunun id'siyle önbelleğe alınır; metin değişince id değişmez, içerik özeti değişir (değerlendir önbellek anahtarı)."""
    return [{"id": b["id"], "metin": b["ozet"], "veri": {"tur": b["tur"], "varlik": b["varlik"], "a": (b.get("karsilastirma") or {}).get("a"), "b": (b.get("karsilastirma") or {}).get("b"),
                                                      "kaynaklar": b["kaynaklar"], "kanit": b["kanit"]}}
            for b in (sonuc.get("bulgular") or []) if b.get("belirsiz") and b.get("durum") != "kapandi"]

def main(argv=None):
    ap = argparse.ArgumentParser(description="Kesişim: günlük çapraz kontrol (F1, kural tabanlı)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for ad in ("kos", "belirsiz"):
        p = sub.add_parser(ad)
        p.add_argument("--canli"); p.add_argument("--vt"); p.add_argument("--tazi")
        if ad == "kos": p.add_argument("--json", action="store_true"); p.add_argument("--kuru", action="store_true", help="dosya yazma")
        else: p.set_defaults(kuru=True, json=False)
    a = ap.parse_args(argv)
    canli = a.canli or os.path.join(baglayici._klasor(_json_oku(os.path.expanduser(os.environ.get("SUFLOR_AYAR") or AYAR_VARSAYILAN), {}), "uygulama", "~/Library/Application Support/Suflor"), "canli")
    s = kos(canli, a.vt, a.tazi, yaz=a.cmd == "kos" and not a.kuru)
    if s.get("atlandi"): print("atlandı: " + s["atlandi"]); return 0
    if a.cmd == "belirsiz": print(json.dumps(belirsiz_adaylar(s), ensure_ascii=False, indent=1)); return 0
    if a.json: print(json.dumps(s, ensure_ascii=False, indent=1)); return 0
    print(f"kesişim: {s['ozet']['toplam']} bulgu, {s['sure_sn']} sn · " + ", ".join(f"{t} {n}" for t, n in s["ozet"]["tur"].items()) + f" · belirsiz {s['ozet']['belirsiz']} · kapanan {s['ozet']['kapandi']} · süzülen özel {s['suzulen']['ozel']}")
    for k in s["kaynaklar"]: print(f"  kaynak {k['ad']}: {k['durum']}" + (f" ({k['yas_sn'] // 3600} sa önce)" if k["yas_sn"] is not None else ""))
    for b in s["bulgular"]: print(f"  [{b['tur']}/{b['durum']}] {b['varlik']} — {b['ozet']}" + (" (belirsiz)" if b["belirsiz"] else ""))
    for h in s["okunamayan"]: print("  okunamadı: " + h)
    return 0

if __name__ == "__main__":
    sys.exit(main())
