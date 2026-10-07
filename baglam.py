#!/usr/bin/env python3
# Suflor.me — proje bağlamı araması. Yalnız yerel dosya; ağ yok, stdlib dışı bağımlılık yok.
# Proje klasörünün tamamını (görüşme dökümleri, canlı toplantılar, .md/.txt/.html/.json/.jsonl/.tsv/.csv, .xlsx, .docx)
# SQLite FTS5 dizinine koyar; Claude toplantı sırasında "Ayşe geçen ay yedekler için ne demişti?" gibi sorulara
# ve kartlara buradan dayanır. Dizin <uygulama klasörü>/dizin.sqlite (proje klasörüne yazmaz);
# her aramada değişen dosyalar kendiliğinden yeniden dizinlenir.
#   python3 baglam.py dizin [--yeniden]          dizini kur/güncelle, özet yaz
#   python3 baglam.py ara "yedek ayşe" [--kim Ayşe] [--tur gorusme,toplanti] [--son 30] [--n 8]
# Sözlük (sozluk.json + ayardaki sozluk_kaynagi tsv'si): doğru adı arayınca dökümlerdeki yanlış yazımları da bulunur.
import argparse, collections, datetime, glob, html, json, os, re, sqlite3, sys, time, unicodedata, zipfile

# hesap başına ayar (relay.py ile aynı kural): ~/Library/Application Support/Suflor/ayar.json; yoksa varsayılanlar
AYAR_YOL = os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")  # SUFLOR_AYAR: deneme için
def ayar_oku():
    v = {"alan": "Suflor", "ad": "", "port": 8765, "uygulama": "~/Library/Application Support/Suflor", "proje": "~/Suflor", "ortak": "/Users/Shared/Suflor",
         "sozluk_kaynagi": None}
    try: v.update(json.load(open(AYAR_YOL, encoding="utf-8")))
    except (OSError, ValueError): pass
    for k in ("uygulama", "proje", "ortak"): v[k] = os.path.expanduser(str(v[k]))
    return v
AYAR = ayar_oku()
PROJE = AYAR["proje"]  # hesabın proje (bağlam) klasörü
DB = os.path.join(AYAR["uygulama"], "dizin.sqlite")
SOZLUK = os.path.join(AYAR.get("sozluk_kaynagi") or "-", "duzeltme_sozlugu_oneri.tsv")
SUFLOR_SOZLUK = os.path.join(AYAR["uygulama"], "canli", "sozluk.json")  # esas sözlük
# Dizine girmeyenler (proje köküne göre): yedekler, arşiv, kod klasörü; alan kendi listesini ayarın "haric"ine yazar
# (ör. bir dökümün anonim kopyası çift sonuç verir, ara çıktılar ilk sonuçları kapar).
# (1 Ekim: .xlsx'in eski .md dışa aktarımları silindi, zip'i _arsiv/'de; _arsiv dizine girmez.)
# her alanda: _yedek, _arsiv, .claude, .git, Suflor kod klasörü; ayar.json "haric" ile alan kendi listesini ekler
HARIC_GENEL = ["_yedek", "_arsiv", ".claude", ".git", "suflor", os.path.basename(str(AYAR.get("kod") or "").rstrip("/")) or "suflor"]
HARIC = list(dict.fromkeys(HARIC_GENEL + list(AYAR.get("haric") or [])))  # ayar "haric": alanın kendi listesi (proje köküne göre)
CANLI_HARIC = {"takvim-secilen.json", "heartbeat.json", "kart-anahtari.txt", "olcum.jsonl", "agenda.json", "hazir.json", "karneler.jsonl", "karsilastirmalar.jsonl"}  # karne · v0.7.2: karşılaştırma
UZANTI = {".md", ".txt", ".html", ".htm", ".json", ".jsonl", ".tsv", ".csv", ".xlsx", ".docx"}
PARCA = 700  # bir parçanın hedef uzunluğu (karakter)

# --- Türkçe sadeleştirme: harf harf 1:1 (özgün metinde konum bulunabilsin) ---------------------------------------
def _nc(c):
    if c in "İIı": return "i"
    d = unicodedata.normalize("NFKD", c)
    return (d[0] if d else c).lower()[:1] or " "
def norm(t): return "".join(_nc(c) for c in t)
def kelimeler(t): return re.findall(r"[0-9a-z]+", norm(t))

# --- Ayrıştırıcılar: her biri (konum, konuşmacı, metin) parçaları üretir -------------------------------------------
KONUSMA_RE = re.compile(r"^\*\*(.{1,60}?)\*\*\s+`(\d{1,2}:\d{2}(?::\d{2})?)`\s*$")
def pencere(birimler, basliksiz=False):
    # birimler: [(konum, konuşmacı, metin)] → ~PARCA'lık pencereler; konuşmacılar birleşir
    out, cur, n = [], [], 0
    for b in birimler:
        cur.append(b); n += len(b[2])
        if n >= PARCA:
            out.append(cur); cur, n = [], 0
    if cur: out.append(cur)
    res = []
    for w in out:
        kim = ", ".join(dict.fromkeys(k for _, k, _ in w if k))
        metin = "\n".join((f"[{k}{' ' + l if l else ''}] " if k else "") + m for l, k, m in w) if not basliksiz else "\n".join(m for _, _, m in w)
        res.append((w[0][0], kim, metin))
    return res
def metin_parcala(t, konum0=""):
    # başlıklara ve boş satırlara göre; tablo satırları başlık satırıyla birlikte tek tek
    out, bas, buf, tablo_bas, satir = [], "", [], None, 0
    def bosalt():
        if buf:
            s = "\n".join(buf).strip()
            for i in range(0, len(s), PARCA * 2):
                if s[i:i + PARCA * 2].strip(): out.append((f"{konum0}s{satir}", "", (bas + "\n" if bas else "") + s[i:i + PARCA * 2]))
            buf.clear()
    for i, ln in enumerate(t.splitlines(), 1):
        if re.match(r"^#{1,6}\s", ln): bosalt(); bas = ln.lstrip("#").strip(); satir = i; tablo_bas = None; continue
        if ln.startswith("|"):
            hucre = [h.strip() for h in ln.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", h) or not h for h in hucre): continue
            if tablo_bas is None: bosalt(); tablo_bas = hucre; continue
            s = " · ".join(f"{a}: {b}" if a else b for a, b in zip(tablo_bas + [""] * len(hucre), hucre) if b)
            if s: out.append((f"{konum0}s{i}", "", (bas + " — " if bas else "") + s))
            continue
        tablo_bas = None
        if not ln.strip():
            if sum(len(x) for x in buf) >= PARCA: bosalt()
            continue
        if not buf: satir = i
        buf.append(ln)
    bosalt()
    return out
def dokum_mu(t): return sum(1 for ln in t.splitlines()[:400] if KONUSMA_RE.match(ln.strip())) >= 5
def dokum_parcala(t):
    birim, kim, zaman, buf = [], "", "", []
    def bitir():
        if kim and buf: birim.append((zaman, kim, " ".join(x.strip() for x in buf if x.strip())))
    for ln in t.splitlines():
        m = KONUSMA_RE.match(ln.strip())
        if m: bitir(); kim, zaman, buf = m.group(1).strip(), m.group(2), []
        elif kim: buf.append(ln)
    bitir()
    return pencere(birim)
def html_metin(t):
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section)>", "\n", t)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))
def json_dizeler(o, yol=""):
    if isinstance(o, str):
        if len(o.strip()) > 2: yield yol, o
    elif isinstance(o, dict):
        for k, v in o.items(): yield from json_dizeler(v, f"{yol}.{k}" if yol else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from json_dizeler(v, f"{yol}[{i}]")
KAYIT_ALAN = ["ozet", "alinti", "metin", "text", "note", "konu", "tur", "bilgi_turu", "surec"]
def jsonl_parcala(yol, kisa):
    rows = []
    for ln in open(yol, encoding="utf-8", errors="replace"):
        try: rows.append(json.loads(ln))
        except Exception: pass
    if kisa.startswith("_canli/"):  # canlı toplantı satırları
        birim = [(r.get("time") or "", "NOT" if "note" in r else (r.get("speaker") or "?"), r.get("note") or r.get("text") or "") for r in rows if isinstance(r, dict)]
        return pencere([b for b in birim if b[2]])
    out = []
    for r in rows:
        if not isinstance(r, dict): continue
        kid = r.get("kayit_id") or r.get("tur_id") or r.get("id") or ""
        parca = [f"{k}: {r[k]}" for k in KAYIT_ALAN if isinstance(r.get(k), str) and r[k].strip()]
        if not parca: parca = [v for _, v in json_dizeler(r)][:8]
        if parca: out.append((str(kid), str(r.get("konusmaci") or r.get("speaker") or ""), " · ".join(parca)[:PARCA * 2]))
    return out
def xlsx_parcala(yol):
    z = zipfile.ZipFile(yol); out = []
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        x = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
        ss = [html.unescape(re.sub(r"<[^>]+>", "", si)) for si in re.findall(r"<si>(.*?)</si>", x, re.S)]
    wb = z.read("xl/workbook.xml").decode("utf-8", "replace")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    rid = dict(re.findall(r'<Relationship [^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
    rid.update({a: b for b, a in re.findall(r'<Relationship [^>]*Target="([^"]+)"[^>]*Id="([^"]+)"', rels)})
    for ad, r in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb):
        hedef = rid.get(r, ""); hedef = hedef.lstrip("/"); hedef = hedef if hedef.startswith("xl/") else "xl/" + hedef
        if hedef not in z.namelist(): continue
        ad = html.unescape(ad); x = z.read(hedef).decode("utf-8", "replace"); bas = None
        for rn, rx in re.findall(r'<row [^>]*r="(\d+)"[^>]*>(.*?)</row>', x, re.S):
            hucre = []
            for attrs, ic in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", rx, re.S):
                v = re.search(r"<v>(.*?)</v>", ic or "", re.S); t = re.search(r'\bt="(\w+)"', attrs)
                if t and t.group(1) == "s" and v: s = ss[int(v.group(1))] if int(v.group(1)) < len(ss) else ""
                elif t and t.group(1) == "inlineStr": s = re.sub(r"<[^>]+>", "", ic or "")
                elif v: s = v.group(1)
                else: s = ""
                hucre.append(html.unescape(s).strip())
            dolu = [h for h in hucre if h]
            if not dolu: continue
            if bas is None and len(dolu) >= 2: bas = hucre; continue
            s = " · ".join(f"{a}: {b}" if a and len(a) < 40 else b for a, b in zip((bas or []) + [""] * len(hucre), hucre) if b)
            if s: out.append((f"{ad}!{rn}", "", f"{ad} — {s}"[:PARCA * 2]))
    return out
def docx_metin(yol):
    x = zipfile.ZipFile(yol).read("word/document.xml").decode("utf-8", "replace")
    return "\n".join(html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))) for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S))

# --- Dosya türü, tarih, başlık ----------------------------------------------------------------------------------
GORUSME = tuple(AYAR.get("gorusme_klasorleri") or ["gorusmeler/"])  # görüşme dökümü klasörleri (proje köküne göre)
ANALIZ = tuple(AYAR.get("analiz_klasorleri") or [])
BEN = ((str(AYAR.get("ad") or "").split() or ["-"])[0])  # kullanıcının adı: konuşmacı sayımında kendisi hariç
def tur_bul(kisa):
    if kisa.startswith("_canli/"): return "toplanti"
    if kisa.startswith(GORUSME) or re.search(r"dokum|transkript", kisa, re.I): return "gorusme"
    if ANALIZ and kisa.startswith(ANALIZ): return "analiz"
    if kisa.startswith(("Sunum/", "sunum/")) or re.search(r"sunum|sunu|deck", kisa, re.I): return "sunum"
    if kisa.endswith(".xlsx"): return "tablo"
    return "belge"
AYLAR = {a: i + 1 for i, a in enumerate("ocak şubat mart nisan mayıs haziran temmuz ağustos eylül ekim kasım aralık".split())}
def tarih_bul(kisa, bas, mtime):
    m = re.search(r"(20\d\d)-?(\d\d)-?(\d\d)", os.path.basename(kisa))
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(20\d\d)", bas)
    if m: return f"{m.group(3)}-{AYLAR[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return datetime.date.fromtimestamp(mtime).isoformat()
def baslik_bul(kisa, t):
    for ln in t.splitlines()[:5]:
        if ln.startswith("# "): return ln[2:].strip()[:120]
    return os.path.basename(kisa)

def parcala(yol, kisa):
    ext = os.path.splitext(yol)[1].lower()
    if ext == ".xlsx": return os.path.basename(kisa), "", xlsx_parcala(yol)
    if ext == ".docx": t = docx_metin(yol)
    elif ext == ".jsonl":
        bas = open(yol.replace(".jsonl", ".md"), encoding="utf-8", errors="replace").read(600) if kisa.startswith("_canli/") and os.path.exists(yol.replace(".jsonl", ".md")) else ""
        return baslik_bul(kisa, bas), bas, jsonl_parcala(yol, kisa)
    else: t = open(yol, encoding="utf-8", errors="replace").read()
    if ext in (".html", ".htm"): t = html_metin(t)
    if ext == ".json":
        try: o = json.loads(t)
        except Exception: o = None
        if o is not None: return os.path.basename(kisa), "", [(y, "", s) for y, s in json_dizeler(o) if len(s) > 15][:5000] or []
    if ext in (".tsv", ".csv"):
        ay = "\t" if ext == ".tsv" else ","; ls = t.splitlines(); bas = ls[0].split(ay) if ls else []
        return os.path.basename(kisa), "", [(f"s{i}", "", " · ".join(f"{a}: {b}" for a, b in zip(bas, ln.split(ay)) if b)) for i, ln in enumerate(ls[1:], 2) if ln.strip()]
    return baslik_bul(kisa, t), t[:1500], (dokum_parcala(t) if dokum_mu(t) else metin_parcala(t))

# --- Dizin ------------------------------------------------------------------------------------------------------
def baglan():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript("""
      CREATE TABLE IF NOT EXISTS dosya(yol TEXT PRIMARY KEY, mtime REAL, boy INTEGER, tur TEXT, tarih TEXT, baslik TEXT, parca INTEGER);
      CREATE TABLE IF NOT EXISTS parca(id INTEGER PRIMARY KEY, yol TEXT, konum TEXT, kim TEXT, metin TEXT);
      CREATE INDEX IF NOT EXISTS parca_yol ON parca(yol);
      CREATE VIRTUAL TABLE IF NOT EXISTS ara USING fts5(n, kimn, content='', prefix='3 4 5', tokenize='unicode61');""")
    return c
def dokum_kopyasi(yol):
    # `toplanti-claude.py dokum` dosyası (<alan>-<kişi>-transkript-<YYYYMMDD>.md) aynı toplantının _canli/ dökümünün
    # temiz kopyası — kaynağı _canli'de duruyorsa dizine ikinci kez girmez (ilk 3 sonuç aynı satırla dolmasın)
    if not re.search(r"-transkript-\d{8}\.md$", yol): return False
    try: m = re.search(r"Kaynak: `_canli/([^`]+)\.md`", open(yol, encoding="utf-8", errors="replace").read(800))
    except OSError: return False
    return bool(m) and os.path.exists(os.path.join(PROJE, "_canli", m.group(1) + ".jsonl"))
def dosyalar():
    for kok, dirs, fs in os.walk(PROJE, followlinks=False):
        rel = os.path.relpath(kok, PROJE); rel = "" if rel == "." else rel
        dirs[:] = [d for d in dirs if not any(os.path.join(rel, d) == h or os.path.join(rel, d).startswith(h + "/") for h in HARIC)]
        for f in fs:
            k = os.path.join(rel, f)
            if os.path.splitext(f)[1].lower() in UZANTI and k not in HARIC and not f.startswith("~$") and not dokum_kopyasi(os.path.join(kok, f)): yield os.path.join(kok, f), k
    canli = os.path.join(PROJE, "_canli")  # kısayol: os.walk takip etmez, ayrıca gez
    if os.path.isdir(canli):
        for f in sorted(os.listdir(canli)):
            if f in CANLI_HARIC or not f.endswith((".jsonl",)) or not f.startswith("20"): continue
            yield os.path.join(canli, f), "_canli/" + f
def guncelle(c, yeniden=False, sessiz=True):
    t0 = time.time(); eski = {r[0]: (r[1], r[2]) for r in c.execute("SELECT yol, mtime, boy FROM dosya")}
    if yeniden: eski = {}; c.executescript("DELETE FROM dosya; DELETE FROM parca; INSERT INTO ara(ara) VALUES('delete-all');")
    gorulen, n_yeni, n_parca, hata = set(), 0, 0, []
    for yol, kisa in dosyalar():
        gorulen.add(kisa)
        try: st = os.stat(yol)
        except OSError: continue
        if eski.get(kisa) == (st.st_mtime, st.st_size): continue
        sil(c, kisa)
        try: baslik, bas, ps = parcala(yol, kisa)
        except Exception as e: hata.append(f"{kisa}: {e.__class__.__name__}"); ps, baslik, bas = [], os.path.basename(kisa), ""
        tur = tur_bul(kisa); tarih = tarih_bul(kisa, bas, st.st_mtime)
        for konum, kim, metin in ps:
            cur = c.execute("INSERT INTO parca(yol, konum, kim, metin) VALUES(?,?,?,?)", (kisa, konum, kim, metin))
            c.execute("INSERT INTO ara(rowid, n, kimn) VALUES(?,?,?)", (cur.lastrowid, norm(metin), norm(kim)))
        c.execute("INSERT OR REPLACE INTO dosya VALUES(?,?,?,?,?,?,?)", (kisa, st.st_mtime, st.st_size, tur, tarih, baslik, len(ps)))
        n_yeni += 1; n_parca += len(ps)
    for k in set(eski) - gorulen: sil(c, k); c.execute("DELETE FROM dosya WHERE yol=?", (k,))
    c.commit()
    if not sessiz or n_yeni:
        print(f"dizin: {n_yeni} dosya güncellendi · {n_parca} parça · {time.time() - t0:.1f} sn" + (f" · okunamayan: {', '.join(hata)}" if hata else ""), file=sys.stderr)
    return n_yeni
def sil(c, kisa):
    ids = [r[0] for r in c.execute("SELECT id FROM parca WHERE yol=?", (kisa,))]
    for i in ids:
        r = c.execute("SELECT metin, kim FROM parca WHERE id=?", (i,)).fetchone()
        c.execute("INSERT INTO ara(ara, rowid, n, kimn) VALUES('delete', ?, ?, ?)", (i, norm(r[0]), norm(r[1])))
    c.execute("DELETE FROM parca WHERE yol=?", (kisa,))

# --- Sözlük ve sorgu --------------------------------------------------------------------------------------------
_SOZ = []
def sozluk():
    if not _SOZ: _SOZ.append(_sozluk_oku())
    return _SOZ[0]
def _sozluk_oku():
    # [(doğru biçim, [biçimler…])] — biçimler sadeleştirilmiş; doğru biçim de biçimlerden biri.
    # önce Suflor sözlüğü (sozluk.json, kullanıcının kararları); dış sözlük önerilerinden yalnız onunla çakışmayanlar
    # (dış sözlük bir adı ters yönde düzeltebilir; doğru ad kullanıcının kararıdır).
    out, gor = [], set(); grup = {}
    try:
        for t in json.load(open(SUFLOR_SOZLUK, encoding="utf-8")).get("terimler", []):
            d = str(t.get("dogru") or "").strip()
            if d: grup.setdefault(d, set()).update(norm(x).strip() for x in [d] + list(t.get("yanlis") or []) if norm(x).strip())
    except (FileNotFoundError, ValueError): pass
    for d, b in grup.items(): out.append((d, sorted(b, key=len, reverse=True))); gor |= b
    try:
        for i, ln in enumerate(open(os.path.join(PROJE, SOZLUK), encoding="utf-8")):
            p = ln.rstrip("\n").split("\t")
            if i == 0 or len(p) < 2: continue
            dogru = re.split(r"\s*\(", p[1])[0].strip()
            bicim = {norm(b).strip() for b in p[0].split("|") if norm(b).strip()} | ({norm(dogru)} if norm(dogru).strip() else set())
            if bicim & gor: continue
            out.append((dogru, sorted(bicim, key=len, reverse=True)))
    except FileNotFoundError: pass
    return out
# Türkçe soru, İngilizce döküm — kelime kökü eşleşirse İngilizce kökler de VEYA'lanır
CEVIRI = {"kontr": "check", "erisi": "acces", "musteri": "custo", "fatur": "invoi", "odeme": "payme",
          "sifre": "passw", "hesap": "accou", "teslim": "deliv", "iptal": "cance", "durum": "statu", "bilgi": "infor",
          "takip": "track follo", "sorun": "issue probl", "egiti": "train", "not": "notes", "gecik": "delay",
          "fiyat": "price", "toplan": "meeti", "yonet": "manag", "onay": "appro", "ekran": "scree", "talep": "reque"}
CEVIRI.update(AYAR.get("ceviri_ek") or {})  # ayar: alanın kendi terimleri (Türkçe kök → İngilizce kökler)
def terim(k): return (k[:5] if len(k) > 5 else k) + "*"
def sorgu_kur(q):
    # her kelime kökle (ilk 5 harf) eşleşir; sözlükte geçen biçim varsa tüm biçimleri VEYA'lanır
    qn = " " + " ".join(kelimeler(q)) + " "; gruplar, eklenen = [], []
    for dogru, bic in sozluk():
        for b in bic:
            if b and f" {b} " in qn:
                gruplar.append("(" + " OR ".join(('"' + x + '"' if " " in x else terim(x)) for x in bic) + ")")
                eklenen.append(dogru); qn = qn.replace(f" {b} ", " "); break
    for k in qn.split():
        if k not in DUR and len(k) > 1:
            en = next((v for kk, v in CEVIRI.items() if k.startswith(kk)), None)
            gruplar.append("(" + " OR ".join([terim(k)] + [x + "*" for x in en.split()]) + ")" if en else terim(k))
    return gruplar, eklenen
DUR = {"ve", "ile", "bir", "bu", "ne", "mi", "mu", "da", "de", "icin", "gibi", "ki", "o", "neler", "nedir", "hakkinda",
       "dedi", "demisti", "soyledi", "soylemisti", "neydi", "nasil", "kim", "kimde", "nerede", "hangi", "var", "yok"}
_ADLAR = set()
def konusmacilar(c):
    # dizindeki konuşmacı adlarının kelimeleri (≥3 harf, K01/G gibi kodlar hariç) → sorguda kişi adı tanınsın
    ad = set()
    for (k,) in c.execute("SELECT DISTINCT kim FROM parca WHERE kim != ''"):
        for w in kelimeler(k):
            if len(w) >= 3 and not re.fullmatch(r"[kg]\d+|not", w) and w != norm(BEN): ad.add(w)
    # dökümün dosya adı → o dökümde en çok konuşan (kullanıcı dışı) kişi: dosya adı "Can" diye sorulur, konuşmacı "John Smith"
    for (yol,) in c.execute("SELECT yol FROM dosya WHERE tur = 'gorusme'"):
        if not yol.startswith(GORUSME): continue
        kok = kelimeler(os.path.basename(yol).rsplit(".", 1)[0])
        if not kok or len(kok[0]) < 3 or kok[0] in ad: continue
        say = collections.Counter(k.strip() for (kim,) in c.execute("SELECT kim FROM parca WHERE yol = ?", (yol,))
                                  for k in kim.split(",") if k.strip() and not k.strip().startswith(BEN))
        en = say.most_common(1)[0][0] if say else ""
        if kelimeler(en) and kelimeler(en)[0] != kok[0]: TAKMA[kok[0]] = kelimeler(en)[0]; ad.add(kok[0])
    _ADLAR.update(ad); return ad
TAKMA = {}
def ara(q, kim=None, turler=None, son=None, n=8, dosya_basina=2):
    c = baglan(); guncelle(c)
    if not kim:
        # "Ayşe yedekler için ne demişti?" → önce Ayşe'nin konuştuğu parçalar, sonra genel sonuçlar
        adlar = konusmacilar(c); bulunan = [w for w in kelimeler(q) if w in adlar]
        if bulunan:
            kalan = " ".join(w for w in kelimeler(q) if w not in bulunan)
            once, ek = ara(kalan, bulunan[0], turler, son, max(2, n // 2), dosya_basina) if kalan.strip() else ([], [])
            genel, ek2 = ara_ic(c, q, None, turler, son, n, dosya_basina)
            gor = {r[0] for r in once}
            return (once + [r for r in genel if r[0] not in gor])[:n], ek or ek2
    return ara_ic(c, q, kim, turler, son, n, dosya_basina)
def ara_ic(c, q, kim, turler, son, n, dosya_basina):
    gruplar, eklenen = sorgu_kur(q)
    if not gruplar and not kim: return [], eklenen
    if kim and not TAKMA: konusmacilar(c)  # --kim <takma ad> doğrudan gelince takma adlar henüz kurulmamış olabilir
    kosul, arg = [], []
    if turler: kosul.append("d.tur IN (%s)" % ",".join("?" * len(turler))); arg += turler
    if son: kosul.append("d.tarih >= ?"); arg.append((datetime.date.today() - datetime.timedelta(days=son)).isoformat())
    def calis(eslesme):
        kk = kelimeler(kim)[0] if kim and kelimeler(kim) else None  # parantez — "a OR b AND kimn:x" b'ye bağlanıyordu
        m = ((f"({eslesme}) AND " if eslesme else "") + f"kimn : {terim(TAKMA.get(kk, kk))}") if kk else eslesme
        m = m.strip() or "*"
        sql = ("SELECT p.id, p.yol, p.konum, p.kim, p.metin, d.tur, d.tarih, d.baslik, bm25(ara, 1.0, 0.3) AS s FROM ara "
               "JOIN parca p ON p.id = ara.rowid JOIN dosya d ON d.yol = p.yol WHERE ara MATCH ? "
               + ("AND " + " AND ".join(kosul) if kosul else "") + " ORDER BY s LIMIT 200")
        try: return c.execute(sql, [m] + arg).fetchall()
        except sqlite3.OperationalError: return []
    rows = calis(" AND ".join(gruplar)) if gruplar else calis("")
    if len(rows) < 3 and len(gruplar) > 1: rows = rows + [r for r in calis(" OR ".join(gruplar)) if r[0] not in {x[0] for x in rows}]
    # yakın tarihe hafif öncelik; aynı dosyadan en çok dosya_basina sonuç
    bugun = datetime.date.today()
    def puan(r):
        try: gun = (bugun - datetime.date.fromisoformat(r[6])).days
        except Exception: gun = 365
        return r[8] * (1.0 + 0.3 / (1 + max(gun, 0) / 14))
    secilen, say = [], {}
    for r in sorted(rows, key=puan):
        if say.get(r[1], 0) >= dosya_basina: continue
        say[r[1]] = say.get(r[1], 0) + 1; secilen.append(r)
        if len(secilen) >= n: break
    return secilen, eklenen
def kesit(metin, q, eklenen=(), boy=260):
    # içerik kelimesinin ilk geçtiği yerden; konuşmacı adı ve dolgu kelimeleri sayılmaz ("[ayşe yılmaz …]" her satırda var)
    nm = norm(metin); ks = [k[:5] for k in kelimeler(q) if len(k) > 2 and k not in DUR and k not in _ADLAR]
    for dogru, bic in sozluk():
        if dogru in eklenen: ks += [b.split()[0][:5] for b in bic if b.split()]
    pos = min((p for p in (nm.find(k) for k in ks) if p >= 0), default=0)
    a = max(0, pos - boy // 3); s = metin[a:a + boy].replace("\n", " / ")
    return ("…" if a else "") + s + ("…" if a + boy < len(metin) else "")
def yaz(sonuc, q, eklenen):
    rows, _ = sonuc
    if eklenen: print(f"(sözlük: {', '.join(eklenen)} — dökümdeki yanlış yazımları da arandı)")
    if not rows: print("sonuç yok"); return
    for i, (pid, yol, konum, kim, metin, tur, tarih, baslik, s) in enumerate(rows, 1):
        print(f"[{i}] {tur} · {tarih} · {baslik} · {yol}{(' @' + konum) if konum else ''}{(' · ' + kim) if kim else ''}")
        print(f"    {kesit(metin, q, eklenen)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dizin"); d.add_argument("--yeniden", action="store_true")
    a = sub.add_parser("ara"); a.add_argument("sorgu"); a.add_argument("--kim"); a.add_argument("--tur", help="virgüllü: toplanti,gorusme,analiz,sunum,tablo,belge")
    a.add_argument("--son", type=int, help="son N gün"); a.add_argument("--n", type=int, default=8)
    A = ap.parse_args()
    if A.cmd == "dizin":
        c = baglan(); guncelle(c, A.yeniden, sessiz=False)
        for tur, nd, np_ in c.execute("SELECT tur, count(*), sum(parca) FROM dosya GROUP BY tur ORDER BY 3 DESC"): print(f"  {tur}: {nd} dosya, {np_} parça")
    else:
        r = ara(A.sorgu, A.kim, A.tur.split(",") if A.tur else None, A.son, A.n); yaz(r, A.sorgu, r[1])
