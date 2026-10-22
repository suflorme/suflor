# Suflor.me aktarıcı bölümü: Toplantı arşivi — dökümler listesi, toplantılarda arama, dökümü panoda okuma (v0.116.0).
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("arsiv")): BASE, _t … relay.py'nin. import etme. Python 3.9 uyumlu.
# Arama dizine (baglam.py) bağlı değil: dökümler küçük (22 Ekim: 56 dosya, 590 KB, tam tarama ~20 ms) ve süren toplantı da hemen
# aranabilsin diye .md dosyaları doğrudan okunur. Türkçe ek için kök eşleşmesi: 7+ harfte son iki, 5–6 harfte son harf düşer ("sözlük" → "sözlüğe";
# daha kısa kök "sözler"i de buluyordu). Özetin kopyası varsa (canli/ozetler/) onun satırları da aranır.
# Dökümler kişi adı içerir: yalnız anahtarlı okuma uçlarından (VERI_GET) panoya gider.
import unicodedata, urllib.parse
ARSIV_DOSYA_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})-(.+)\.md$")
ARSIV_SATIR_RX = re.compile(r"^\|\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$")
ARSIV_ARA_EN_COK, ARSIV_DOKUM_EN_COK, ARSIV_METIN_EN_COK = 60, 6000, 400  # sonuç · panoda gösterilen satır · sonuçtaki metin (karakter)
_ARSIV = {}  # dosya adı → (mtime, boyut, ayrıştırılmış döküm)

def _ar_norm(s):  # küçük harf, Türkçe i/ı ve aksan sade (ğ → g, ş → s): arama ve vurgu aynı biçimle
    return "".join("i" if c in "İIı" else (unicodedata.normalize("NFKD", c)[:1] or c).lower() for c in str(s or ""))
def _ar_kok(w): return w[:-2] if len(w) >= 7 else w[:-1] if len(w) >= 5 else w
def _ar_kokler(q): return list(dict.fromkeys(_ar_kok(w) for w in re.findall(r"\w+", _ar_norm(q)) if len(w) >= 2))[:8]
def _ar_eslesir(kok, kelimeler): return any(k.startswith(kok) for k in kelimeler)

def _ar_oku(f):  # → {"baslik", "satirlar": [(saat, kim, metin, isaret, sistem)]} · mtime/boyut değişmedikçe önbellekten
    yol = os.path.join(BASE, f)
    try: st = os.stat(yol)
    except OSError: return None
    on = _ARSIV.get(f)
    if on and on[0] == st.st_mtime and on[1] == st.st_size: return on[2]
    baslik, satirlar = None, []
    try:
        with open(yol, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if baslik is None and ln.startswith("# "): baslik = ln[2:].strip().split(" — ", 1)[-1]; continue
                m = ARSIV_SATIR_RX.match(ln.rstrip("\n"))
                if not m or m.group(1) == "Saat": continue
                kim = m.group(2).strip(); sistem = kim.startswith("**")
                satirlar.append((m.group(1), kim.strip("* ").strip(), m.group(3).strip(), m.group(4).strip(), sistem))
    except OSError: return None
    d = {"baslik": baslik, "satirlar": satirlar}
    if len(_ARSIV) > 400: _ARSIV.clear()
    _ARSIV[f] = (st.st_mtime, st.st_size, d); return d

def _ar_ozetler():  # döküm dosya adı → son özet kaydı (son-toplantilar.jsonl tümü; SON bellekte yalnız son 20)
    o = {}
    try:
        with open(os.path.join(BASE, "son-toplantilar.jsonl"), encoding="utf-8") as fh:
            for ln in fh:
                try: r = json.loads(ln)
                except ValueError: continue
                if isinstance(r, dict) and r.get("dosya"): o[str(r["dosya"])] = r
    except OSError: pass
    return o

def _ar_dosyalar():  # yeniden eskiye; yalnız döküm adları (yan dosyalar .md değil)
    try: ls = [f for f in os.listdir(BASE) if ARSIV_DOSYA_RX.match(f)]
    except OSError: return []
    return sorted(ls, reverse=True)

def _ar_ozet(f, d, oz):  # listede ve aramada bir toplantının özeti
    m = ARSIV_DOSYA_RX.match(f); r = oz.get(f) or {}
    konusan = [s for s in d["satirlar"] if not s[4]]
    sure = None
    if len(d["satirlar"]) >= 2:
        def dk(s): h, mi = s.split(":")[:2]; return int(h) * 60 + int(mi)
        sure = (dk(d["satirlar"][-1][0]) - dk(d["satirlar"][0][0])) % (24 * 60)
    kisiler = [k for k, _ in collections.Counter(s[1] for s in konusan).most_common(4)]
    return {"id": f[:-3], "baslik": r.get("baslik") or d["baslik"] or m.group(6).replace("-", " "),
            "at": f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}", "sure_dk": sure, "satir": len(konusan),
            "kisiler": kisiler, "ozet": r.get("id") if r.get("kopya") and os.path.isfile(str(r["kopya"])) else None}

def arsiv_liste():  # GET /toplantilar — konuşma satırı ya da özeti olmayan dosya (ör. toplantısızken yazılan not) listeye girmez
    oz = _ar_ozetler(); out = []
    for f in _ar_dosyalar():
        d = _ar_oku(f)
        if not d or not d["satirlar"]: continue
        x = _ar_ozet(f, d, oz)
        if x["satir"] or x["ozet"]: out.append(x)
    return {"toplantilar": out, "toplam": len(out)}

def _ar_parcala(metin, kokler):  # metni [parça, eşleşti mi] listesine böler (panoda vurgu; HTML aktarıcıda üretilmez)
    out = []
    for p in re.split(r"(\w+)", metin):
        if not p: continue
        e = bool(re.match(r"\w", p)) and any(_ar_norm(p).startswith(k) for k in kokler)
        if out and out[-1][1] == e: out[-1][0] += p
        else: out.append([p, e])
    return out

def _ar_ozet_satirlari(r):  # özetin kopyasından aranacak satırlar: (saat yok, "Özet", metin, "", sistem=False)
    try:
        with open(str(r.get("kopya") or ""), encoding="utf-8", errors="replace") as fh: ls = fh.read(300000).splitlines()
    except OSError: return []
    out = []
    for ln in ls:
        if ln.lstrip().startswith("#"): continue  # başlık ("Kararlar", "Sözlük") sonuç olmasın
        t = re.sub(r"^\s*(?:[-*+]|\d+[.)]|>)\s*", "", ln).replace("**", "").strip()
        if len(t) >= 3 and not t.startswith("|---"): out.append(("", _t("Özet", "Summary"), t, "", False))
    return out

def arsiv_ara(q):  # GET /toplantilar?q=… — her satır bütün sözcükleri içermeli; yoksa en çok sözcüğü içerenler
    kokler = _ar_kokler(q)
    if not kokler: return {"q": q, "sonuclar": [], "toplam": 0}
    oz = _ar_ozetler(); adaylar = []
    for f in _ar_dosyalar():
        d = _ar_oku(f)
        if not d: continue
        r = oz.get(f) or {}
        for i, s in [(-1, x) for x in (_ar_ozet_satirlari(r) if r.get("kopya") else [])] + list(enumerate(d["satirlar"])):
            kel = re.findall(r"\w+", _ar_norm(s[1] + " " + s[2]))
            n = sum(1 for k in kokler if _ar_eslesir(k, kel))
            if n: adaylar.append((n, f, i, s, d))
    tam = [a for a in adaylar if a[0] == len(kokler)]
    secilen = tam or sorted(adaylar, key=lambda a: -a[0])
    out, toplantilar = [], {}
    for n, f, i, s, d in secilen:
        if f not in toplantilar: toplantilar[f] = _ar_ozet(f, d, oz)
        if len(out) < ARSIV_ARA_EN_COK:
            out.append({"id": f[:-3], "baslik": toplantilar[f]["baslik"], "at": toplantilar[f]["at"], "satir": i, "saat": s[0], "kim": s[1],
                        "sistem": s[4], "ozet": i < 0, "ozet_id": toplantilar[f]["ozet"], "parcalar": _ar_parcala(s[2][:ARSIV_METIN_EN_COK], kokler)})
    return {"q": q, "kokler": kokler, "tam": bool(tam), "sonuclar": out, "toplam": len(secilen), "toplanti_sayisi": len(toplantilar)}

def arsiv_dokum(i):  # GET /toplantilar/dokum?id=<dosya adı .md'siz>
    f = str(i or "") + ".md"
    if not ARSIV_DOSYA_RX.match(f) or "/" in f or f.startswith("."): return {"ok": False, "err": _t("geçersiz toplantı", "invalid meeting")}
    d = _ar_oku(f)
    if not d: return {"ok": False, "err": _t("döküm yok", "no transcript")}
    s = d["satirlar"]
    return {"ok": True, **_ar_ozet(f, d, _ar_ozetler()), "kesildi": len(s) > ARSIV_DOKUM_EN_COK,
            "satirlar": [{"saat": x[0], "kim": x[1], "metin": asistan_goster(x[2]), "isaret": asistan_goster(x[3]), "sistem": x[4]} for x in s[:ARSIV_DOKUM_EN_COK]]}  # S133: eski dökümlerde "Claude:" hitabı

def arsiv_ozet_kaydi(i):  # son_ac'ın yedeği: SON bellekte yalnız son 20 kaydı tutar; arşivdeki eski toplantının "Özeti aç"ı için
    return next((r for r in _ar_ozetler().values() if r.get("id") == str(i or "")), None)

def arsiv_istek(yol, tam_yol):  # relay do_GET: /toplantilar[?q=…] · /toplantilar/dokum?id=…
    qs = urllib.parse.parse_qs(str(tam_yol).partition("?")[2])
    if yol == "/toplantilar/dokum": return arsiv_dokum((qs.get("id") or [""])[0])
    q = (qs.get("q") or [""])[0].strip()[:200]
    return arsiv_ara(q) if q else arsiv_liste()
