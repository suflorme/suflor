#!/usr/bin/env python3
# Proje kartı (proje hazırlığı T5; planlar/proje-hazirligi.md §2 Adım 4, §2b, §8). Dizindeki asıl ve geçerli belgelerden (en çok 300, en yeniden;
# dışa aktarım, eski sürüm, kopya, adla hariç, toplantı dökümü ve özel bellek kaynakları girmez) belge başına bir Claude çağrısı → JSON:
# kişiler, kurumlar, kararlar, tarihler, açık işler, sözlük (her satırda kaynak: dosya + konum). Metin dizinden gelir (gizli bilgi parçaları
# zaten dışarıda); yalnız Claude'a gider. Sonuç belge metninin özetiyle önbelleklenir (<uygulama>/kart-onbellek/): değişmeyen belge yeniden sorulmaz.
# Yerelde birleştirme: aynı kişinin yazımları ve takma adları tek kişi; aynı karar/iş/olayın farklı tarihleri silinmez, "celiski" diye işaretlenir.
# Düzenli klasör kipi (kökte CLAUDE.md, DURUM ya da karar kaydı belgesi varsa): kart önce bunlardan beslenir; yalnız diğer belgelerden gelen satırlar
# "fark" işaretli; belgelere dokunulmaz. Veritabanı kipi (ayar veritabani): kişiler veritabanından (ayar veritabani.kisiler; varsa .kararlar,
# .gorevler), belgelerden yalnız özet ve sözlük. Taslak <uygulama>/proje-karti-taslak.json; onay (T6'da sihirbaz E ekranı) → proje-karti.json,
# sözlük maddeleri sozluk.json'a (Whisper istemine de girer), düzenli olmayan klasörde CLAUDE.md'ye kısa taslak not (yalnız CLAUDE.md varsa).
# v0.121.0: onaylı kart <uygulama>/proje.db'ye de yazılır (baglam.py proje_vt_guncelle) — yapay zekâdan bağımsız: Konuş ve toplantı oturumu SQL ile okur.
#   python3 proje-karti.py cikar [--sinir 300] [--model sonnet] [--paralel 4] [--tahmin]
#   python3 proje-karti.py goster | onayla
import argparse, collections, concurrent.futures, datetime, hashlib, importlib.util, json, os, re, sqlite3, subprocess, sys, threading, time

_B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baglam.py"); sys.dont_write_bytecode = True
_sp = importlib.util.spec_from_file_location("suflor_baglam_kart", _B); B = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(B)
_sp = importlib.util.spec_from_file_location("suflor_beyin_kart", os.path.join(os.path.dirname(os.path.abspath(__file__)), "aktarici", "beyin.py"))
BY = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(BY)  # v0.121.1: beyin katmanı (yapay zekâ çağrısı tek yerde)
AYAR = B.AYAR; UYG = AYAR["uygulama"]; PROJE = B.PROJE
ONB = os.path.join(UYG, "kart-onbellek"); TASLAK = os.path.join(UYG, "proje-karti-taslak.json"); KART = os.path.join(UYG, "proje-karti.json")
GECMIS = os.path.join(UYG, "proje-karti-gecmis.jsonl"); SOZLUK = os.path.join(UYG, "canli", "sozluk.json")
ISTEM_SURUM, BELGE_KAR, SINIR = 1, 24000, 300
DUZENLI_RX = re.compile(r"^(CLAUDE\.md|[^/]*DURUM[^/]*\.md|[^/]*karar[-_ ]?defteri[^/]*\.md)$", re.I)  # kökte ya da bir alt klasörde
VT = AYAR.get("veritabani") if isinstance(AYAR.get("veritabani"), dict) and AYAR["veritabani"].get("yol") else None
UNVAN = {"bey", "hanim", "hn", "bay", "bayan", "mr", "mrs", "ms", "dr", "prof"}

ISTEM = """Aşağıda bir proje klasöründeki tek bir belgenin metni var; köşeli parantez içindeki değerler konumdur.
Bu belgeden proje kartı için bilgi çıkar. Yalnız metinde açıkça yazanı al: tahmin etme, yorum ve öneri ekleme, belgede olmayanı uydurma.
Her maddeye "konum" yaz (bilginin geçtiği köşeli parantez değeri). Şifre, anahtar, kart ya da hesap numarası yazma. Değerleri belgenin dilinde yaz.
Yalnız şu JSON'u döndür, başka hiçbir şey yazma:
{SEMA}
Boş kalanları [] bırak. "sozluk": bu projeye özgü özel adlar, sistem/ürün/kurum adları ve kısaltmalar (genel sözcükler değil), en çok 15."""
SEMA_TAM = ('{"ozet": "belgenin 1-2 cümlelik özeti", "kisiler": [{"ad": "", "rol": "", "kurum": "", "takma_adlar": [], "konum": ""}], '
            '"kurumlar": [{"ad": "", "konum": ""}], "kararlar": [{"ne": "", "kim": "", "ne_zaman": "", "konum": ""}], '
            '"tarihler": [{"tarih": "", "ne": "", "konum": ""}], "acik_isler": [{"is": "", "sahip": "", "tarih": "", "konum": ""}], '
            '"sozluk": [{"terim": "", "aciklama": "", "konum": ""}]}')
SEMA_VT = '{"ozet": "belgenin 1-2 cümlelik özeti", "sozluk": [{"terim": "", "aciklama": "", "konum": ""}]}'
OZET_ISTEM = """Aşağıda bir projenin belgelerinin tek tek özetleri var (en yeniden eskiye). Bunlardan projenin 5-8 cümlelik genel özetini yaz:
ne yapılıyor, kimlerle, hangi aşamada, öne çıkan konular. Yalnız özetlerde yazana dayan, yorum ve öneri ekleme. Yalnız özet metnini yaz."""

def n(t): return " ".join(B.kelimeler(str(t or "")))
def kisi_anahtar(ad): return " ".join(w for w in B.kelimeler(str(ad or "")) if w not in UNVAN)

def aday_belgeler(c, sinir=SINIR):
    # → [(yol, tur, tarih, duzenli)] en yeniden; düzenli klasör belgeleri önde
    sat = c.execute("""SELECT d.yol, d.tur, COALESCE(d.tarih, ''), d.mtime FROM dosya d
                       WHERE COALESCE(d.gecerli, 1) = 1 AND COALESCE(d.kaynak_turu, 'asil') = 'asil' AND COALESCE(d.gizli, 0) = 0
                         AND COALESCE(d.kapsam, 'ortak') = 'ortak' AND d.parca > 0 AND d.tur IN ('belge', 'sunum', 'gorusme', 'tablo', 'karar', 'kural')
                         AND d.yol NOT LIKE '/%' AND d.yol NOT LIKE '\\_canli/%' ESCAPE '\\'""").fetchall()
    duz = lambda y: y.count("/") <= 1 and bool(DUZENLI_RX.match(os.path.basename(y)))
    sat = [r for r in sat if r[1] not in ("karar", "kural") or duz(r[0])]  # bellek kaynağı olarak eklenmiş karar/kural dosyası yalnız düzenli belgeyse
    sat = [r for r in sat if duz(r[0])] + sorted([r for r in sat if not duz(r[0])], key=lambda r: (r[2], r[3]), reverse=True)
    return [(y, t, tr, duz(y)) for y, t, tr, _ in sat[:sinir]]

def belge_metni(c, yol):
    out, boy = [], 0
    for konum, metin in c.execute("SELECT konum, metin FROM parca WHERE yol = ? ORDER BY id", (yol,)):
        s = f"[{konum or '-'}] {metin}"
        if boy + len(s) > BELGE_KAR: out.append("[…] (belgenin devamı kısaltıldı)"); break
        out.append(s); boy += len(s)
    return "\n".join(out)

def claude_cagir(istem, model, is_="proje-karti"):
    cl = BY.claude_yolu(B.AYAR)
    if not cl: raise RuntimeError("claude bulunamadı")
    t0 = time.time()
    r = BY.tek(cl, BY.kart_args(model), istem, UYG)
    try: j = json.loads(r.stdout)
    except ValueError: raise RuntimeError(f"claude çıktısı okunamadı ({(r.stderr or r.stdout)[-120:]})")
    k = BY.kullanim(j)
    o = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "is": is_, "sure_ms": j.get("duration_ms"), "duvar_ms": round((time.time() - t0) * 1000),
         "maliyet": round(k["maliyet"], 4), "giris": k["giris"], "cikti": k["cikti"], "hata": bool(j.get("is_error"))}
    try:
        with open(os.path.join(UYG, "canli", "claude-cagri.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(o, ensure_ascii=False) + "\n")
    except OSError: pass
    if j.get("is_error"): raise RuntimeError(str(j.get("result") or "claude hatası")[:160])
    return str(j.get("result") or ""), o["maliyet"]

def json_al(metin):
    m = re.search(r"\{.*\}", metin, re.S)
    return json.loads(m.group(0)) if m else None

def belge_cikar(yol, metin, model, vt_kipi):
    anahtar = hashlib.sha256(f"{ISTEM_SURUM}|{int(vt_kipi)}|{model}|{metin}".encode()).hexdigest()
    y = os.path.join(ONB, anahtar[:2], anahtar + ".json")
    try: return json.load(open(y, encoding="utf-8")), 0.0, True
    except (OSError, ValueError): pass
    istem = ISTEM.replace("{SEMA}", SEMA_VT if vt_kipi else SEMA_TAM) + f"\n\nBELGE: {yol}\n\n{metin}"
    toplam = 0.0; hata = None
    for _ in range(2):  # JSON bozuksa bir kez daha
        try:
            cevap, usd = claude_cagir(istem, model); toplam += usd; o = json_al(cevap)
            if isinstance(o, dict): break
            hata = "JSON yok"
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as e: hata = f"{e.__class__.__name__}: {str(e)[:120]}"
    else:
        return {"hata": hata}, toplam, False
    o = {k: v for k, v in o.items() if k in ("ozet", "kisiler", "kurumlar", "kararlar", "tarihler", "acik_isler", "sozluk")}
    os.makedirs(os.path.dirname(y), exist_ok=True)
    with open(y + ".tmp", "w", encoding="utf-8") as f: json.dump(o, f, ensure_ascii=False)
    os.chmod(y + ".tmp", 0o600); os.replace(y + ".tmp", y)
    return o, toplam, False

# --- Birleştirme ------------------------------------------------------------------------------------------------------
def _liste(o, k): return [x for x in (o.get(k) or []) if isinstance(x, dict)]
def birlestir(sonuclar, duzenli_var):
    # sonuclar: [(yol, duzenli, json)] → kart bölümleri
    kisiler, k_idx = [], {}
    def kisi_bul(ad, takma):
        ka = kisi_anahtar(ad)
        if not ka: return None
        for a in [ka] + [kisi_anahtar(t) for t in takma]:
            if a and a in k_idx: return k_idx[a]
        if " " not in ka:  # tek sözcük ("Ayşe"): tek bir tam adın ilk sözcüğüyse o kişi
            ad_lar = [p for p in kisiler if p["_anahtar"].split()[0] == ka and " " in p["_anahtar"]]
            if len(ad_lar) == 1: return ad_lar[0]
        else:  # tam ad geldi, önce tek sözcükle kaydedilmiş biri varsa ona bağla (yalnız o tek sözcükle başlayan tam ad yoksa)
            tek = k_idx.get(ka.split()[0])
            if tek and " " not in tek["_anahtar"] and not any(p is not tek and p["_anahtar"].split()[0] == ka.split()[0] for p in kisiler): return tek
        return None
    def kisi_ekle(x, kaynak):
        ad = str(x.get("ad") or "").strip(); takma = [str(t).strip() for t in (x.get("takma_adlar") or []) if str(t).strip()]
        if not kisi_anahtar(ad): return
        p = kisi_bul(ad, takma)
        if p is None:
            p = {"ad": ad, "takma_adlar": [], "roller": [], "kurumlar": [], "kaynaklar": [], "_anahtar": kisi_anahtar(ad)}; kisiler.append(p)
        elif len(kisi_anahtar(ad)) > len(p["_anahtar"]) and " " in kisi_anahtar(ad):  # daha tam yazım ad olur, eskisi takma ad
            if p["ad"] not in p["takma_adlar"]: p["takma_adlar"].append(p["ad"])
            p["ad"], p["_anahtar"] = ad, kisi_anahtar(ad)
        elif ad != p["ad"] and ad not in p["takma_adlar"]: p["takma_adlar"].append(ad)
        for t in takma:
            if t != p["ad"] and t not in p["takma_adlar"]: p["takma_adlar"].append(t)
        for alan, hedef in (("rol", "roller"), ("kurum", "kurumlar")):
            v = str(x.get(alan) or "").strip()
            if v and n(v) not in {n(z) for z in p[hedef]}: p[hedef].append(v)
        p["kaynaklar"].append(kaynak)
        for a in [p["_anahtar"]] + [kisi_anahtar(t) for t in p["takma_adlar"]]:
            if a: k_idx[a] = p
    def grup(alan_metin, alan_tarih, ekler=()):
        d, sira = {}, []
        def ekle(x, kaynak):
            m = str(x.get(alan_metin) or "").strip()
            if not m: return
            k = n(m)[:90]
            if k not in d:
                d[k] = {alan_metin: m, **{e: [] for e in ekler}, "tarihler": [], "kaynaklar": []}; sira.append(k)
            g = d[k]; t = str(x.get(alan_tarih) or "").strip()
            if t and t not in g["tarihler"]: g["tarihler"].append(t)
            for e in ekler:
                v = str(x.get(e) or "").strip()
                if v and v not in g[e]: g[e].append(v)
            g["kaynaklar"].append(kaynak)
        def bitir():
            out = []
            for k in sira:
                g = d[k]; tl = g.pop("tarihler")
                g[alan_tarih] = tl[0] if tl else ""
                if len({n(t) for t in tl}) > 1: g["celiski"] = {alan_tarih: tl}  # §2 Adım 4: çelişen tarih silinmez
                out.append(g)
            return out
        return ekle, bitir
    karar_ekle, k_bitir = grup("ne", "ne_zaman", ("kim",))
    t_ekle, t_bitir = grup("ne", "tarih")
    i_ekle, i_bitir = grup("is", "tarih", ("sahip",))
    kurumlar, sozluk = {}, {}
    ozetler = []
    for yol, duz, o in sonuclar:
        if not isinstance(o, dict) or o.get("hata"): continue
        kay = lambda x: [yol, str(x.get("konum") or "")]
        if o.get("ozet"): ozetler.append((yol, str(o["ozet"])[:400]))
        for x in _liste(o, "kisiler"): kisi_ekle(x, kay(x))
        for x in _liste(o, "kurumlar"):
            a = str(x.get("ad") or "").strip()
            if a: kurumlar.setdefault(n(a), {"ad": a, "kaynaklar": []})["kaynaklar"].append(kay(x))
        for x in _liste(o, "kararlar"): karar_ekle(x, kay(x))
        for x in _liste(o, "tarihler"): t_ekle(x, kay(x))
        for x in _liste(o, "acik_isler"): i_ekle(x, kay(x))
        for x in _liste(o, "sozluk"):
            t = str(x.get("terim") or "").strip()
            if t and len(t) <= 60: sozluk.setdefault(n(t), {"terim": t, "aciklama": str(x.get("aciklama") or "").strip(), "kaynaklar": []})["kaynaklar"].append(kay(x))
    for p in kisiler: p.pop("_anahtar", None)
    kart = {"kisiler": kisiler, "kurumlar": list(kurumlar.values()), "kararlar": k_bitir(), "tarihler": t_bitir(), "acik_isler": i_bitir(), "sozluk": list(sozluk.values())}
    if duzenli_var:  # düzenli klasör: yalnız diğer belgelerden gelen satır "fark"
        duz_yol = {y for y, d, _ in sonuclar if d}
        for bol in kart.values():
            for x in bol: x["fark"] = not any(k[0] in duz_yol for k in x.get("kaynaklar") or [])
    return kart, ozetler

# --- Veritabanı kipi --------------------------------------------------------------------------------------------------
def vt_oku():
    if not VT: return None
    yol = os.path.join(PROJE, VT["yol"]) if not os.path.isabs(VT["yol"]) else VT["yol"]
    out = {"kaynak": "veritabani", "yol": VT["yol"]}
    try: c = sqlite3.connect(f"file:{yol}?mode=ro", uri=True); c.execute("SELECT 1").fetchone()
    except sqlite3.Error as e: out["hata"] = f"veritabanı açılamadı ({e.__class__.__name__})"; return out
    for bol, k in (("kisiler", "kisiler"), ("kararlar", "kararlar"), ("acik_isler", "gorevler")):
        if not VT.get(k): out[bol] = None; continue
        try: out[bol] = [[str(v) for v in r] for r in c.execute(VT[k]).fetchmany(500)]
        except sqlite3.Error as e: out[bol] = None; out.setdefault("sorgu_hatasi", []).append(f"{k}: {str(e)[:80]}")
    c.close(); return out

# --- Komutlar ---------------------------------------------------------------------------------------------------------
def cikar(sinir=SINIR, model=None, paralel=4, tahmin=False, sessiz=True, ilerleme=None):  # ilerleme(n, toplam): sihirbaz (hazirlik.py)
    model = model or BY.secim(AYAR, "proje_karti")["model"]; c = B.baglan(); t0 = time.time()
    adaylar = aday_belgeler(c, sinir); duzenli_var = any(d for *_, d in adaylar)
    metinler = [(y, d, belge_metni(c, y)) for y, _, _, d in adaylar]
    if tahmin:
        # 17 Ekim gerçek proje denemesi (10 belge): giriş ≈ karakter / 3 + 1.200, çıktı ≈ 1.500 belirteç/belge (veritabanı kipinde de sözlük uzun) → 0,43 $
        kar = sum(len(m) for _, _, m in metinler); tk = kar / 3 + len(metinler) * 1200; cik = (len(metinler) + 1) * 1500
        return {"belge": len(metinler), "karakter": kar, "tahmini_giris_belirtec": int(tk), "tahmini_usd_sonnet": round(tk / 1e6 * 3 + cik / 1e6 * 15, 2)}
    sonuc, usd, onb, hatalar, durdu = [None] * len(metinler), 0.0, 0, [], None
    kilit = threading.Lock()
    def is_(i):
        nonlocal usd, onb, durdu
        if durdu: return
        if B.toplantida(): durdu = "toplantı başladı — sonra kaldığı yerden"; return
        y, d, m = metinler[i]; o, u, ob = belge_cikar(y, m, model, bool(VT))
        with kilit:
            usd += u; onb += ob; sonuc[i] = (y, d, o)
            if o.get("hata"): hatalar.append((y, o["hata"]))
            if ilerleme: ilerleme(sum(1 for s in sonuc if s), len(metinler))
            if not sessiz: print(f"  [{sum(1 for s in sonuc if s)}/{len(metinler)}] {y}" + (" (önbellek)" if ob else "") + (f" — hata: {o['hata']}" if o.get("hata") else ""), file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max(1, paralel)) as ex: list(ex.map(is_, range(len(metinler))))
    sonuclar = [s for s in sonuc if s]
    kart, ozetler = birlestir(sonuclar, duzenli_var)
    ozet = ""
    if ozetler and not durdu:
        anahtar = hashlib.sha256(json.dumps([ISTEM_SURUM, model, ozetler], ensure_ascii=False).encode()).hexdigest(); oy = os.path.join(ONB, "ozet-" + anahtar + ".txt")
        try: ozet = open(oy, encoding="utf-8").read()
        except OSError:
            try:
                ozet, u = claude_cagir(OZET_ISTEM + "\n\n" + "\n".join(f"- {y}: {o}" for y, o in ozetler[:SINIR]), model); usd += u; ozet = ozet.strip()
                os.makedirs(ONB, exist_ok=True); open(oy, "w", encoding="utf-8").write(ozet)
            except (RuntimeError, subprocess.TimeoutExpired) as e: hatalar.append(("(proje özeti)", str(e)[:120]))
    taslak = {"t": int(time.time()), "surum": 1, "kip": "duzenli" if duzenli_var else "genel", "veritabani_kipi": bool(VT), "model": model,
              "belge": len(sonuclar), "aday": len(adaylar), "onbellek": onb, "ozet": ozet, **kart, "belge_ozetleri": [{"yol": y, "ozet": o} for y, o in ozetler],
              "maliyet_usd": round(usd, 4), "hatalar": hatalar[:50], "durdu": durdu, "sure_sn": round(time.time() - t0, 1)}
    if VT:  # §2b.1: kişi, karar, açık iş tek doğru kaynaktan
        taslak["veritabani"] = vt_oku()
        for bol in ("kisiler", "kararlar", "tarihler", "acik_isler", "kurumlar"): taslak[bol] = []
    os.makedirs(UYG, exist_ok=True)
    with open(TASLAK + ".tmp", "w", encoding="utf-8") as f: json.dump(taslak, f, ensure_ascii=False, indent=1)
    os.chmod(TASLAK + ".tmp", 0o600); os.replace(TASLAK + ".tmp", TASLAK)
    return taslak

def ozet_satiri(k):
    s = (f"proje kartı ({k['kip']}{', veritabanı kipi' if k['veritabani_kipi'] else ''}): {k['belge']}/{k['aday']} belge · önbellek {k['onbellek']} · "
         f"kişi {len(k['kisiler'])} · kurum {len(k['kurumlar'])} · karar {len(k['kararlar'])} · tarih {len(k['tarihler'])} · açık iş {len(k['acik_isler'])} · "
         f"sözlük {len(k['sozluk'])} · çelişki {sum(1 for b in ('kararlar', 'tarihler', 'acik_isler') for x in k[b] if x.get('celiski'))} · "
         f"{k['maliyet_usd']} $ · {k['sure_sn']} sn")
    if k.get("veritabani"): v = k["veritabani"]; s += f"\n  veritabanı: " + (v.get("hata") or " · ".join(f"{b} {len(v[b]) if v.get(b) is not None else 'sorgu yok'}" for b in ("kisiler", "kararlar", "acik_isler")))
    if k.get("hatalar"): s += f"\n  hata: {len(k['hatalar'])} ({k['hatalar'][0][0]}: {k['hatalar'][0][1][:80]})"
    if k.get("durdu"): s += f"\n  durdu: {k['durdu']}"
    return s

def onayla(taslak=None, kim="kullanici", terimler=None):  # terimler: sihirbazın E ekranında kullanıcının seçtiği sözlük terimleri (None: kurala göre)
    k = taslak or json.load(open(TASLAK, encoding="utf-8"))
    k = dict(k, onay={"t": int(time.time()), "kim": kim})
    with open(KART + ".tmp", "w", encoding="utf-8") as f: json.dump(k, f, ensure_ascii=False, indent=1)
    os.chmod(KART + ".tmp", 0o600); os.replace(KART + ".tmp", KART)
    with open(GECMIS, "a", encoding="utf-8") as f: f.write(json.dumps({"t": k["onay"]["t"], "kim": kim, "belge": k["belge"], "kisi": len(k["kisiler"]), "sozluk": len(k["sozluk"])}) + "\n")
    duz_yol = {y for y in {s[0] for m in k.get("sozluk") or [] for s in m.get("kaynaklar") or []} if y.count("/") <= 1 and DUZENLI_RX.match(os.path.basename(y))}
    eklenen = sozluge_aktar(k.get("sozluk") or [], duz_yol, terimler)
    notu = claude_notu(k) if k.get("kip") != "duzenli" else False  # düzenli klasörde belgeler değişmez
    # v0.121.0: onaylı kart proje veritabanına (kisi, karar, acik_is… — Konuş ve toplantı oturumu vt_sor ile okur; kayıt veritabanı kipinde kurulmaz)
    try: pv = B.proje_vt_guncelle()
    except Exception as e: pv = {"hata": e.__class__.__name__}
    return {"sozluk_eklenen": eklenen, "claude_notu": notu, "proje_vt": pv}

SOZ_KONUSULMAZ = re.compile(r"[/@\\#\[\]()]|\.\w|^[a-z0-9_-]+$")  # dosya/alan adı, komut, adres, işaretli ya da tümü küçük harf: söylenmez
SOZ_AKTAR_EN_COK = 60  # Whisper istemi ~200 belirteç (whisper-hat istem_metni): 17 Ekim gerçek proje kartında (201 belge) 1.228 terim, süzgeçten sonra 303 kalıyordu
def sozluk_aktarilir(m, duz_yol):
    # Whisper istemi kısıtlı (belirteç bütçesi): yalnız en az iki belgede geçen ya da düzenli belgeden gelen, konuşmada söylenen terim
    if SOZ_KONUSULMAZ.search(m["terim"]): return False
    kay = {k[0] for k in m.get("kaynaklar") or []}
    return len(kay) >= 2 or bool(kay & duz_yol)
def sozluge_aktar(maddeler, duz_yol=frozenset(), terimler=None):
    # kartın sözlüğü → sozluk.json (kaynak proje-karti; yanlış yazımı yok: düzeltme yapmaz, Whisper istemine özel ad olarak girer)
    try: s = json.load(open(SOZLUK, encoding="utf-8"))
    except (OSError, ValueError): s = {"surum": 1, "terimler": []}
    var = {n(t.get("dogru")) for t in s.get("terimler", [])} | {n(y) for t in s.get("terimler", []) for y in (t.get("yanlis") or [])}
    eklenen = 0
    secim = {n(t) for t in terimler} if terimler is not None else None  # kullanıcı seçtiyse kural yerine seçim (en çok yine SOZ_AKTAR_EN_COK)
    secilen = sorted((m for m in maddeler if (n(m["terim"]) in secim if secim is not None else sozluk_aktarilir(m, duz_yol))), key=lambda m: (not ({k[0] for k in m.get("kaynaklar") or []} & duz_yol), -len({k[0] for k in m.get("kaynaklar") or []})))
    for m in secilen[:SOZ_AKTAR_EN_COK]:
        if n(m["terim"]) and n(m["terim"]) not in var:
            s.setdefault("terimler", []).append({"dogru": m["terim"], "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti", "not": m.get("aciklama", "")[:120]})
            var.add(n(m["terim"])); eklenen += 1
    if eklenen:
        os.makedirs(os.path.dirname(SOZLUK), exist_ok=True)
        with open(SOZLUK + ".tmp", "w", encoding="utf-8") as f: json.dump(s, f, ensure_ascii=False, indent=1)
        os.replace(SOZLUK + ".tmp", SOZLUK)
    return eklenen

NOT_BASLIK = "## Proje kartı (taslak)"
def claude_notu(k):
    cm = os.path.join(PROJE, "CLAUDE.md")
    if not os.path.isfile(cm): return False
    s = open(cm, encoding="utf-8").read()
    if NOT_BASLIK in s: return False
    satir = [f"\n\n{NOT_BASLIK}", f"_Suflor.me proje kartından ({datetime.date.today().isoformat()}); onaylı kart uygulama klasöründe. İstediğin zaman düzenleyebilirsin._", ""]
    if k.get("ozet"): satir += [k["ozet"], ""]
    if k.get("kisiler"): satir += ["Kişiler: " + "; ".join(p["ad"] + (f" ({', '.join(p['roller'][:2])})" if p.get("roller") else "") for p in k["kisiler"][:15]), ""]
    if k.get("acik_isler"): satir += ["Açık işler:"] + [f"- {x['is']}" + (f" — {', '.join(x['sahip'])}" if x.get("sahip") else "") + (f" ({x['tarih']})" if x.get("tarih") else "") for x in k["acik_isler"][:10]] + [""]
    if k.get("sozluk"): satir += ["Terimler: " + ", ".join(m["terim"] for m in k["sozluk"][:30])]
    open(cm, "w", encoding="utf-8").write(s.rstrip() + "\n".join(satir) + "\n")
    return True

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cikar"); c.add_argument("--sinir", type=int, default=SINIR); c.add_argument("--model"); c.add_argument("--paralel", type=int, default=4)
    c.add_argument("--tahmin", action="store_true", help="Claude'a sormadan belge sayısı ve maliyet tahmini")
    sub.add_parser("goster"); sub.add_parser("onayla")
    A = ap.parse_args()
    if A.cmd == "cikar":
        r = cikar(A.sinir, A.model, A.paralel, A.tahmin, sessiz=False); print(json.dumps(r, ensure_ascii=False) if A.tahmin else ozet_satiri(r))
    elif A.cmd == "goster": print(ozet_satiri(json.load(open(TASLAK, encoding="utf-8"))))
    else: print(json.dumps(onayla(), ensure_ascii=False))
