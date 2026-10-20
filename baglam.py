#!/usr/bin/env python3
# Suflor.me — proje bağlamı araması. Yalnız yerel dosya; ağ yok, stdlib dışı bağımlılık yok.
# Proje klasörünün tamamını (görüşme dökümleri, canlı toplantılar, .md/.txt/.html/.json/.jsonl/.tsv/.csv, .xlsx, .docx)
# SQLite FTS5 dizinine koyar; Claude toplantı sırasında "Ayşe geçen ay yedekler için ne demişti?" gibi sorulara
# ve kartlara buradan dayanır. Dizin <uygulama klasörü>/dizin.sqlite (proje klasörüne yazmaz);
# her aramada değişen dosyalar kendiliğinden yeniden dizinlenir.
#   python3 baglam.py dizin [--yeniden]          dizini kur/güncelle, özet yaz
#   python3 baglam.py tara [--json]               proje taraması (SHA-256, kopya, sürüm grubu, kaynak türü, adla hariç) → <uygulama>/tarama.json
#   python3 baglam.py ara "yedek ayşe" [--kim Ayşe] [--tur gorusme,toplanti] [--son 30] [--n 8] [--kapsam ortak]
# v0.64.0: ayardaki bellek kaynakları (karar listeleri, kural dosyaları) ve Konuş geçmişi de dizinde (aşağıda "Bellek kaynakları").
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
DB = os.environ.get("SUFLOR_DIZIN") or os.path.join(AYAR["uygulama"], "dizin.sqlite")  # SUFLOR_DIZIN: deneme (kör kıyasta kol başına ayrı dizin)
SOZLUK = os.path.join(AYAR.get("sozluk_kaynagi") or "-", "duzeltme_sozlugu_oneri.tsv")
SUFLOR_SOZLUK = os.path.join(AYAR["uygulama"], "canli", "sozluk.json")  # esas sözlük
SOZLUK_KOPYA = os.path.join(AYAR["uygulama"], "dis-sozluk.tsv")  # dış sözlüğün uygulama klasöründeki kopyası: launchd'deki aktarıcı Masaüstü'nü okuyamaz
# Dizine girmeyenler (proje köküne göre): yedekler, arşiv, kod klasörü; alan kendi listesini ayarın "haric"ine yazar
# (ör. bir dökümün anonim kopyası çift sonuç verir, ara çıktılar ilk sonuçları kapar).
# (1 Ekim: .xlsx'in eski .md dışa aktarımları silindi, zip'i _arsiv/'de; _arsiv dizine girmez.)
# her alanda: _yedek, _arsiv, .claude, .git, Suflor kod klasörü; ayar.json "haric" ile alan kendi listesini ekler
HARIC_GENEL = ["_yedek", "_arsiv", ".claude", ".git", "suflor", os.path.basename(str(AYAR.get("kod") or "").rstrip("/")) or "suflor"]
HARIC = list(dict.fromkeys(HARIC_GENEL + list(AYAR.get("haric") or [])))  # ayar "haric": alanın kendi listesi (proje köküne göre)
CANLI_HARIC = {"takvim-secilen.json", "heartbeat.json", "kart-anahtari.txt", "olcum.jsonl", "agenda.json", "hazir.json", "karneler.jsonl", "karsilastirmalar.jsonl"}  # karne · v0.7.2: karşılaştırma
UZANTI = {".md", ".txt", ".html", ".htm", ".json", ".jsonl", ".tsv", ".csv", ".xlsx", ".docx", ".eml"}
CEVIR_UZ = {".pdf", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff", ".bmp"}  # T2: metne çevirme işçisiyle (önbellekten dizine)
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
    # paragraflar satır satır; tablolar Markdown tablosu (metin_parcala her satırı başlığıyla tek parça yapar — v0.66.0, T2 ölçümünde tablo %0'dı)
    x = zipfile.ZipFile(yol).read("word/document.xml").decode("utf-8", "replace")
    p_metin = lambda p: html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)))
    out = []
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>", x, re.S):
        if not m.group(0).startswith("<w:tbl>"): out.append(p_metin(m.group(0))); continue
        satirlar = [[" ".join(p_metin(p) for p in re.findall(r"<w:p[ >].*?</w:p>", tc, re.S)).replace("|", "/").strip() for tc in re.findall(r"<w:tc[ >].*?</w:tc>", tr, re.S)]
                    for tr in re.findall(r"<w:tr[ >].*?</w:tr>", m.group(0), re.S)]
        satirlar = [s for s in satirlar if any(s)]
        for i, s in enumerate(satirlar):
            out.append("| " + " | ".join(s) + " |")
            if i == 0: out.append("|" + "---|" * len(s))
        out.append("")
    return "\n".join(out)

# --- Dosya türü, tarih, başlık ----------------------------------------------------------------------------------
GORUSME = tuple(AYAR.get("gorusme_klasorleri") or ["gorusmeler/"])  # görüşme dökümü klasörleri (proje köküne göre)
ANALIZ = tuple(AYAR.get("analiz_klasorleri") or [])
BEN = ((str(AYAR.get("ad") or "").split() or ["-"])[0])  # kullanıcının adı: konuşmacı sayımında kendisi hariç
def tur_bul(kisa):
    if kisa in BELLEK_TUR: return BELLEK_TUR[kisa][0]
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

def parcala(yol, kisa, sha=None):
    ext = os.path.splitext(yol)[1].lower(); bt = BELLEK_TUR.get(kisa, ("",))[0]
    if bt == "konusma": return "Konuş geçmişi", "", gecmis_parcala(yol)
    if bt == "karar":
        t = open(yol, encoding="utf-8", errors="replace").read(); ps = karar_parcala(t)
        if ps: return baslik_bul(kisa, t), t[:1500], ps
    if ext == ".xlsx": return os.path.basename(kisa), "", xlsx_parcala(yol)
    if ext in CEVIR_UZ:  # T2: çevrilmiş metin önbellekten (çevrilmemişse dizine henüz girmez)
        ps = cevrilmis(yol, sha)
        if ps is None: raise Bekliyor()
        t = "\n".join(m for _, m in ps)
        return baslik_bul(kisa, t) if ext in (".pdf", ".pptx") else os.path.basename(kisa), t[:1500], [(k, "", m) for k0, m0 in ps for k, _, m in metin_parcala(m0, k0 + " · " if k0 else "")]
    if ext == ".eml": t = eml_metin(yol)
    elif ext == ".docx": t = docx_metin(yol)
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

# --- Bellek kaynakları (v0.64.0, S76) -------------------------------------------------------------------------
# Kişisel asistanın kullanıcıyı tanıması için proje klasörü dışındaki kaynaklar da dizine girer. Ayar "bellek_kaynaklari":
#   [{"yol": "<dosya ya da glob, ~ açılır>", "tur": "karar" | "kural", "kapsam": "ortak" | "ozel"}, …]
# karar: karar listesi (Markdown tablosu; her satır bir parça, satırın tarihiyle) · kural: bellek/kural dosyaları (dosya başına parçalar).
# Proje içindeki bir dosya da yazılabilir (ör. alanın kendi karar listesi): yalnız türü ve kapsamı değişir. Konuş geçmişi
# (<uygulama>/canli/konus-gecmis.jsonl) kendiliğinden "konusma" türü, "ozel" kapsam. Özel kapsam yalnız toplantı dışı kişiliğin cevabında aranır
# (Konuş ön araması kapsam="ortak" ile süzer); kodda yol ya da kişi adı yok, hepsi ayardan.
GECMIS = os.path.join(AYAR["uygulama"], "canli", "konus-gecmis.jsonl")
BELLEK_TUR = {}  # kısa yol → (tür, kapsam); dosyalar() doldurur
def _bellek_liste():
    out = []
    for k in AYAR.get("bellek_kaynaklari") or []:
        if not isinstance(k, dict) or not k.get("yol") or k.get("tur") not in ("karar", "kural"): continue
        out.append((os.path.expanduser(str(k["yol"])), k["tur"], "ortak" if str(k.get("kapsam") or "ortak") == "ortak" else "ozel"))
    return out
def bellek_dosyalari(erisilemeyen=None):
    pj = os.path.realpath(PROJE)
    for desen, tur, kapsam in _bellek_liste():
        kok = desen.split("*")[0].split("?")[0].split("[")[0]; kok = kok if kok.endswith("/") and "*" in desen else os.path.dirname(kok)
        try: os.listdir(kok)
        except PermissionError:  # launchd'nin Masaüstü engeli: glob sessizce boş döner, eski kayıtlar korunsun
            if erisilemeyen is not None: erisilemeyen.append(os.path.realpath(kok))  # anahtarlar gerçek yolla (macOS /var → /private/var)
            continue
        except OSError: continue
        for y in sorted(glob.glob(desen)):
            if not os.path.isfile(y) or os.path.basename(y) == "MEMORY.md": continue  # MEMORY.md: Claude Code bellek dizininin içindekiler listesi
            r = os.path.realpath(y)
            if r.startswith(pj + "/"): BELLEK_TUR[os.path.relpath(r, pj)] = (tur, kapsam); continue  # proje taraması zaten veriyor
            BELLEK_TUR[r] = (tur, kapsam); yield r, r
    if os.path.exists(GECMIS) and AYAR.get("konus_gecmis", bool(AYAR.get("kisilik_bellek"))) is not False:
        BELLEK_TUR[GECMIS] = ("konusma", "ozel"); yield GECMIS, GECMIS
_TARIH_RX = re.compile(r"(\d{1,2})\.(\d{1,2})\.(20\d\d)|(20\d\d)-(\d\d)-(\d\d)")
def _tarih_hucre(h):
    m = _TARIH_RX.search(h or "")
    if not m: return None
    try: return (datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m.group(1) else datetime.date(int(m.group(4)), int(m.group(5)), int(m.group(6)))).isoformat()
    except ValueError: return None
def karar_parcala(t):
    # Markdown tablosu: her satır bir karar (konum = numara; numarasız "Güncelleme" satırı önceki numaraya +); tarih satırın tarih hücresinden
    out, son = [], ""
    for ln in t.splitlines():
        if not ln.lstrip().startswith("|"): continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        tarih = next((_tarih_hucre(x) for x in c[:3] if _tarih_hucre(x)), None)
        if not tarih: continue  # başlık ve ayırıcı satırları
        no = c[0] if c[0] and not _tarih_hucre(c[0]) else ""
        if no: son = no
        metin = " · ".join(x.replace("**", "") for x in c if x)
        out.append((no or (son + "+" if son else ""), "", metin, tarih))
    return out
def gecmis_parcala(yol):
    out = []
    for ln in open(yol, encoding="utf-8", errors="replace"):
        try: o = json.loads(ln)
        except ValueError: continue
        at = str(o.get("at") or ""); soru = str(o.get("soru") or "").strip()
        if not at or not soru: continue
        metin = (f"[{o['kisilik']}] " if o.get("kisilik") else "") + (f"(toplantıda: {o['toplanti']}) " if o.get("toplanti") else "") + \
            f"Kullanıcının sorusu: {soru}\nCevabın: {str(o.get('sesli') or '').strip()}" + (f"\nYazılı ayrıntı: {str(o['ayrinti']).strip()[:1500]}" if o.get("ayrinti") else "")
        out.append((at[:16].replace("T", " "), "", metin, at[:10]))
    return out
# Zaman süzgeci: "dün / geçen hafta / geçen ay / geçen salı / 3 gün önce / 12 Ekim" → (baş, bitiş). Hatırlama kalıbında ("ne demiştim",
# "neden karar verdik") konuşma ve karar türleri önce aranır (LongMemEval: zaman aralığıyla süzmek zaman sorularında +%7–11).
_GUNLER = ["pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi", "pazar"]
_AYLAR_N = ["ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik"]
def zaman_araligi(q, bugun=None):
    b = bugun or datetime.date.today(); n = " " + " ".join(kelimeler(q)) + " "; G = datetime.timedelta
    def ay_bas(d): return d.replace(day=1)
    if " gecen hafta" in n: s = b - G(days=b.weekday() + 7); return s.isoformat(), (s + G(days=6)).isoformat()
    if " bu hafta" in n: return (b - G(days=b.weekday())).isoformat(), b.isoformat()
    if " gecen ay" in n: s = ay_bas(ay_bas(b) - G(days=1)); return s.isoformat(), (ay_bas(b) - G(days=1)).isoformat()
    if " bu ay" in n: return ay_bas(b).isoformat(), b.isoformat()
    m = re.search(r" gecen (" + "|".join(_GUNLER) + r")\w*", n)
    if m: s = b - G(days=b.weekday() + 7) + G(days=_GUNLER.index(m.group(1))); return s.isoformat(), s.isoformat()
    m = re.search(r" son (\d{1,3}) gun", n)
    if m: return (b - G(days=int(m.group(1)))).isoformat(), b.isoformat()
    m = re.search(r" (\d{1,3}) (gun|hafta) once", n)
    if m: d = b - G(days=int(m.group(1)) * (7 if m.group(2) == "hafta" else 1)); return (d - G(days=1)).isoformat(), (d + G(days=1)).isoformat()
    m = re.search(r" (\d{1,2}) (" + "|".join(_AYLAR_N) + r")\w*", n)
    if m:
        try:
            d = datetime.date(b.year, _AYLAR_N.index(m.group(2)) + 1, int(m.group(1)))
            if d > b: d = d.replace(year=b.year - 1)
            return d.isoformat(), d.isoformat()
        except ValueError: pass
    if re.search(r" (evvelsi|onceki) gun", n): d = b - G(days=2); return d.isoformat(), d.isoformat()
    if re.search(r" dun(ku)? ", n): d = b - G(days=1); return d.isoformat(), d.isoformat()
    if re.search(r" (gecen gun|gecenlerde|gecende)", n): return (b - G(days=10)).isoformat(), (b - G(days=1)).isoformat()
    if " bugun" in n: return b.isoformat(), b.isoformat()
    return None
HATIRLA_RX = re.compile(r"\b(demistim|demistin|dedim|dedin|demisti[mn]?|soylemistim|soylemistin|soyledim|konusmustuk|konustuk|sormustum|sordum|"
                        r"karar (vermistik|verdik|vermistim|verdim|almistik|aldik)|kararlastirmistik|anlasmistik|hatirliyor mu|hatirlat|ne konustuk|"
                        r"vazgec(tik|mistik|tim|mistim)|(biraktik|birakmistik|kaldirdik|kaldirmistik|degistirdik|degistirmistik))\b")
_KARAR_RX = re.compile(r"\b(karar|kararlas|anlasmis|vazgec|birak|kaldird|kaldirmis|degistird|degistirmis)")
_SOZ_RX = re.compile(r"\b(demis|dedi[mn]?\b|soyle|sordu|sormus|konus|hatirl)")
_ZAMAN_SOZ = ("bugun", "dun", "evvelsi", "onceki", "gecen", "hafta", "son", "once", "demis", "dedi", "dedin", "dedim", "soyle", "konus", "sordu", "sormus",
              "karar", "verdi", "vermis", "almis", "aldik", "hatirl", "neden", "niye", "sana", "bana", "ben", "sen", "biz", "musun", "misin", "kararlas", "anlas",
              "vazgec", "birakt", "kaldird", "degistird") + tuple(_GUNLER) + tuple(_AYLAR_N)
def bellek_ara(q, kapsam=None, n=3, bugun=None):
    # hatırlama ya da zaman ifadesi varsa → (satırlar, aralık); yoksa ([], None). Önce konuşma ve karar türleri (aralıkla), sözcük kalmazsa aralıktaki en yeniler
    zr = zaman_araligi(q, bugun); hat = bool(HATIRLA_RX.search(" ".join(kelimeler(q))))
    if not zr and not hat: return [], None
    nq = " ".join(kelimeler(q)); ka, so = bool(_KARAR_RX.search(nq)), bool(_SOZ_RX.search(nq))
    turler = ["karar"] if ka and not so else ["konusma"] if so and not ka else ["konusma", "karar"]  # "ne demiştim" → konuşma; "neden karar verdik" → karar
    if kapsam == "ortak": turler = [t for t in turler if t != "konusma"]
    if not turler: return [], zr
    c = baglan()
    kalan = " ".join(w for w in kelimeler(q) if not w.isdigit() and not any(w.startswith(z) for z in _ZAMAN_SOZ) and w not in DUR and len(w) > 1)
    rows = ara_ic(c, kalan, None, turler, None, n, 2, kapsam, zr)[0] if kalan.strip() else []
    if not rows and zr:
        kos = "d.tur IN (%s) AND COALESCE(p.tarih, d.tarih) BETWEEN ? AND ?" % ",".join("?" * len(turler)) + (" AND COALESCE(d.kapsam, 'ortak') = 'ortak'" if kapsam == "ortak" else "")
        rows = c.execute("SELECT p.id, p.yol, p.konum, p.kim, p.metin, d.tur, COALESCE(p.tarih, d.tarih), d.baslik, 0 FROM parca p JOIN dosya d ON d.yol = p.yol WHERE "
                         + kos + " ORDER BY COALESCE(p.tarih, d.tarih) DESC, p.konum DESC LIMIT ?", turler + list(zr) + [n]).fetchall()
    return rows, zr

# --- Dizin ------------------------------------------------------------------------------------------------------
def baglan():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript("""
      CREATE TABLE IF NOT EXISTS dosya(yol TEXT PRIMARY KEY, mtime REAL, boy INTEGER, tur TEXT, tarih TEXT, baslik TEXT, parca INTEGER);
      CREATE TABLE IF NOT EXISTS parca(id INTEGER PRIMARY KEY, yol TEXT, konum TEXT, kim TEXT, metin TEXT);
      CREATE INDEX IF NOT EXISTS parca_yol ON parca(yol);
      CREATE INDEX IF NOT EXISTS parca_kim ON parca(kim);
      CREATE VIRTUAL TABLE IF NOT EXISTS ara USING fts5(n, kimn, content='', prefix='3 4 5', tokenize='unicode61');""")
    for t, k in (("dosya", "kapsam"), ("parca", "tarih")):  # v0.64.0: bellek kaynakları (eski dizine sütun eklenir; boşsa kapsam ortak, tarih dosyanınki)
        if k not in [r[1] for r in c.execute(f"PRAGMA table_info({t})")]: c.execute(f"ALTER TABLE {t} ADD COLUMN {k} TEXT")
    tara_baglan(c)  # proje hazırlığı T1: tarama tablosu + dosya alanları
    return c
def dokum_kopyasi(yol):
    # `toplanti-claude.py dokum` dosyası (<alan>-<kişi>-transkript-<YYYYMMDD>.md) aynı toplantının _canli/ dökümünün
    # temiz kopyası — kaynağı _canli'de duruyorsa dizine ikinci kez girmez (ilk 3 sonuç aynı satırla dolmasın)
    if not re.search(r"-transkript-\d{8}\.md$", yol): return False
    try: m = re.search(r"Kaynak: `_canli/([^`]+)\.md`", open(yol, encoding="utf-8", errors="replace").read(800))
    except OSError: return False
    return bool(m) and os.path.exists(os.path.join(PROJE, "_canli", m.group(1) + ".jsonl"))
ERISILEMEYEN = []  # son guncelle'de okunamayan klasörler (proje köküne göre; "" = kök): launchd'nin Masaüstü engeli (TCC) os.walk'ta sessizce boş döner
def dosyalar(erisilemeyen=None):
    hata = (lambda e: erisilemeyen.append(os.path.relpath(e.filename, PROJE) if e.filename else "")) if erisilemeyen is not None else None
    yield from bellek_dosyalari(erisilemeyen)  # önce: proje içindeki bellek kaynağının türü (BELLEK_TUR) proje taramasından önce bilinsin
    for kok, dirs, fs in os.walk(PROJE, onerror=hata, followlinks=False):
        rel = os.path.relpath(kok, PROJE); rel = "" if rel == "." else rel
        dirs[:] = [d for d in dirs if not any(os.path.join(rel, d) == h or os.path.join(rel, d).startswith(h + "/") for h in HARIC)]
        for f in fs:
            k = os.path.join(rel, f)
            if os.path.splitext(f)[1].lower() in UZANTI | CEVIR_UZ and k not in HARIC and not f.startswith("~$") and not dokum_kopyasi(os.path.join(kok, f)): yield os.path.join(kok, f), k
    canli = os.path.join(PROJE, "_canli")  # kısayol: os.walk takip etmez, ayrıca gez
    if os.path.isdir(canli):
        for f in sorted(os.listdir(canli)):
            if f in CANLI_HARIC or not f.endswith((".jsonl",)) or not f.startswith("20"): continue
            yield os.path.join(canli, f), "_canli/" + f
def dizinle(c, yol, kisa, st, hata=None):  # bir dosyayı (yeniden) dizinle → parça sayısı (None: dizine girmez — çevrilmedi, adla hariç ya da birebir kopya)
    sil(c, kisa)
    t = c.execute("SELECT gizli, kopya_of, sha256 FROM tarama WHERE yol=? AND mtime=? AND boy=?", (kisa, st.st_mtime, st.st_size)).fetchone()
    if t and (t[0] or t[1]): c.execute("DELETE FROM dosya WHERE yol=?", (kisa,)); return None  # §2/§4: hariç tutulan ve kopya dizine girmez
    try: baslik, bas, ps = parcala(yol, kisa, t[2] if t else None)
    except Bekliyor: c.execute("DELETE FROM dosya WHERE yol=?", (kisa,)); return None
    except Exception as e:
        if hata is not None: hata.append(f"{kisa}: {e.__class__.__name__}")
        ps, baslik, bas = [], os.path.basename(kisa), ""
    n0 = len(ps); ps = [p for p in ps if not gizli_bilgi(p[2])]  # G3: şifre/anahtar/kart/IBAN geçen parça dizine girmez
    tur = tur_bul(kisa); tarih = tarih_bul(kisa, bas, st.st_mtime); kapsam = BELLEK_TUR.get(kisa, (None, "ortak"))[1]
    for p in ps:
        konum, kim, metin = p[:3]
        cur = c.execute("INSERT INTO parca(yol, konum, kim, metin, tarih) VALUES(?,?,?,?,?)", (kisa, konum, kim, metin, p[3] if len(p) > 3 else None))
        c.execute("INSERT INTO ara(rowid, n, kimn) VALUES(?,?,?)", (cur.lastrowid, norm(metin), norm(kim)))
    c.execute("INSERT OR REPLACE INTO dosya(yol, mtime, boy, tur, tarih, baslik, parca, kapsam, gizli_parca) VALUES(?,?,?,?,?,?,?,?,?)", (kisa, st.st_mtime, st.st_size, tur, tarih, baslik, len(ps), kapsam, n0 - len(ps)))
    tara_dosyaya(c, kisa)  # tarama alanları (dosya değiştiyse boş kalır, sonraki tara doldurur)
    return len(ps)
def gecmis_guncelle(c=None):  # Konuş geçmişine satır eklenince yalnız o dosya (10 dk'lık tam turu beklemeden; ~ms)
    c = c or baglan()
    try: st = os.stat(GECMIS)
    except OSError: return 0
    BELLEK_TUR[GECMIS] = ("konusma", "ozel"); n = dizinle(c, GECMIS, GECMIS, st); c.commit(); return n or 0
def guncelle(c, yeniden=False, sessiz=True):
    t0 = time.time(); eski = {r[0]: (r[1], r[2], r[3], r[4] or "ortak") for r in c.execute("SELECT yol, mtime, boy, tur, kapsam FROM dosya")}
    if yeniden: eski = {}; c.executescript("DELETE FROM dosya; DELETE FROM parca; INSERT INTO ara(ara) VALUES('delete-all');")
    gorulen, n_yeni, n_parca, hata, eris = set(), 0, 0, [], []
    try:
        if not os.listdir(PROJE): eris.append(".")  # TCC bazen hata yerine boş liste verir; proje kökü gerçekte boş olmaz
    except OSError: eris.append(".")
    for yol, kisa in dosyalar(eris):
        gorulen.add(kisa)
        try: st = os.stat(yol)
        except OSError: continue
        if eski.get(kisa) == (st.st_mtime, st.st_size, tur_bul(kisa), BELLEK_TUR.get(kisa, (None, "ortak"))[1]): continue  # tür/kapsam ayarı değişince de yeniden
        n = dizinle(c, yol, kisa, st, hata)
        if n is not None: n_parca += n; n_yeni += 1
    # okunamayan klasörün dosyaları "silinmiş" sayılmaz (17 Ekim: aktarıcının 10 dk'lık turu dizini 101 bin parçadan 301'e indirdi)
    eris = sorted({"" if e in (".", "") else e for e in eris}); ERISILEMEYEN[:] = eris
    korunur = lambda k: any(e == "" or k == e or k.startswith(e + "/") for e in eris)  # kök okunamazsa hepsi (görülen _canli zaten güncel)
    for k in set(eski) - gorulen:
        if not korunur(k): sil(c, k); c.execute("DELETE FROM dosya WHERE yol=?", (k,))
    c.commit()
    try: sozluk_kopyala()  # dış sözlük → uygulama klasörü (aktarıcının Konuş ön araması oradan okur)
    except OSError as e: print(f"dizin: dış sözlük kopyalanamadı ({e.__class__.__name__})", file=sys.stderr)
    try:  # son turun izi: aktarıcı, Brifing yardımcısının (--dizin) tam erişimle bitirip bitirmediğini buradan anlar
        with open(DB + ".tur.json.tmp", "w", encoding="utf-8") as f: json.dump({"t": time.time(), "erisilemeyen": eris, "pid": os.getpid()}, f)
        os.replace(DB + ".tur.json.tmp", DB + ".tur.json")
    except OSError: pass
    if eris and not sessiz: print(f"dizin: okunamayan klasör ({', '.join(e or 'proje kökü' for e in eris)}) — eski kayıtları korundu", file=sys.stderr)
    if not sessiz or n_yeni:
        print(f"dizin: {n_yeni} dosya güncellendi · {n_parca} parça · {time.time() - t0:.1f} sn" + (f" · okunamayan: {', '.join(hata)}" if hata else ""), file=sys.stderr)
    return n_yeni
def sil(c, kisa):
    ids = [r[0] for r in c.execute("SELECT id FROM parca WHERE yol=?", (kisa,))]
    for i in ids:
        r = c.execute("SELECT metin, kim FROM parca WHERE id=?", (i,)).fetchone()
        c.execute("INSERT INTO ara(ara, rowid, n, kimn) VALUES('delete', ?, ?, ?)", (i, norm(r[0]), norm(r[1])))
    c.execute("DELETE FROM parca WHERE yol=?", (kisa,))

# --- Tarama (proje hazırlığı T1, planlar/proje-hazirligi.md §2 Adım 1) ----------------------------------------------
# Klasördeki her dosya (desteklenmeyen biçimler dahil): yol, tür, boyut, değişme zamanı, SHA-256 → `tarama` tablosu (SHA önbelleği:
# değişme zamanı + boyut aynıysa yeniden okunmaz; boş dosya "bos" işaretli, kopya sayılmaz) + dizindeki `dosya` satırına sha256/surum_grubu/gecerli/kopya_of/kaynak_turu/gizli/hata.
# Birebir kopya: aynı SHA → biri asıl, diğerleri kopya. Sürüm grubu: ad kökü (v3, son, final, (1), tarih ekleri silinir) + aynı klasör +
# aynı uzantı; içerik okunabiliyorsa MinHash benzerliği ≥ 0,8 şart, okunamıyorsa (PDF, görüntü — T2'ye kadar) adında tarih olan gruplanmaz
# (yalnız tarihle ayrışan adlar çoğu kez ayrı toplantı/gün kaydıdır). Kaynak türü kural tabanlı (asil / turetilmis / disa_aktarim; ayar
# `veritabani.disa_aktarim` yolları dışa aktarım). Adla hariç tutma (.env, *.key, *.pem, parola/şifre/maaş…, kimlik taramaları) → gizli=1.
# Sonuçtan çıkarma T3'te; burada yalnız tarama ve kayıt. Rapor <uygulama>/tarama.json.
TARA_RAPOR = os.path.join(AYAR["uygulama"], "tarama.json")
TARA_ATLA = {".ds_store", "thumbs.db", "desktop.ini", ".localized", "icon\r"}
TARA_TUR = {"belge": "md txt rtf docx doc odt pages pdf", "sunum": "pptx ppt key odp", "tablo": "xlsx xls csv tsv numbers ods",
            "veri": "json jsonl xml yaml yml db sqlite sqlite3 npy parquet", "web": "html htm", "goruntu": "png jpg jpeg webp heic gif tif tiff bmp",
            "eposta": "eml msg mbox", "ses": "mp3 m4a wav aac flac ogg opus", "video": "mp4 mov m4v webm mkv avi",
            "arsiv": "zip rar 7z tar gz tgz", "kod": "py js ts gs sql sh swift rb go java c h css ipynb drawio vtt srt"}
TARA_TUR = {u: t for t, us in TARA_TUR.items() for u in us.split()}
TARA_METIN = {".md", ".txt", ".html", ".htm", ".json", ".jsonl", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".vtt", ".srt", ".docx", ".xlsx"}  # MinHash için okunabilenler (+ çevrilmiş PDF/görüntü önbellekten)
TARA_GIZLI_UZ = {".env", ".key", ".pem", ".p12", ".pfx", ".kdbx", ".keychain", ".gpg", ".asc", ".ovpn", ".ppk"}
TARA_GIZLI_AD = re.compile(r"parola|sifre(?!lem|li)|password|passwd|credential|maas|salary|bordro|payroll|(^|[^a-z])(id_rsa|id_ed25519|\.?env)($|[^a-z])")
TARA_KIMLIK_AD = re.compile(r"kimlik|pasaport|passport|ehliyet|nufus|surucu belgesi|id[ _-]?card|kimlik karti")  # yalnız görüntü/PDF: kimlik taraması
TARA_DISA_KLASOR = re.compile(r"^(disa|disa[ _-]?aktarim|export|exports|dump|dokum[ _-]?ham|snapshot|snapshots|form[ _-]?cevaplar[a-z]*)$")
TARA_DISA_UZ = {".csv", ".tsv", ".json", ".jsonl", ".xlsx", ".xls", ".xml", ".db", ".sqlite"}
TARA_TURETILMIS_KLASOR = re.compile(r"^_?(son[ _-]?yayin|yayin|yayinlanan|publish|published|dist|build|_site|site[ _-]?cikti)$")  # yayımlanmış/derlenmiş kopyalar
TARA_TURETILMIS_AD = re.compile(r"(^|[^a-z])(ozet|ozeti|summary|gorunum|view|pivot|anonim|anonymized|cikti|output)($|[^a-z])")
TARA_ASIL_UZ = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".key", ".numbers", ".pages", ".odt", ".ods", ".odp"}  # yanındaki aynı adlı md/csv/pdf bunun dışa çıktısı
TARA_TARIH = re.compile(r"(?<!\d)(20\d\d[-_.]?[01]\d[-_.]?[0-3]\d(?:[-_ t]?[0-2]\d[-_.:h]?[0-5]\d(?:[-_.:]?[0-5]\d)?)?|[0-3]?\d[-_.][01]?\d[-_.](?:20)?\d\d)(?!\d)")
TARA_SAAT = re.compile(r"(?<!\d)20\d\d[-_.]?[01]\d[-_.]?[0-3]\d[-_ t]?[0-2]\d[-_.:h]?[0-5]\d(?!\d)")  # tarih + saat damgası (otomatik çıktı)
TARA_SURUM = re.compile(r"\(\d{1,3}\)|(^|[^a-z0-9])(v\d+(?:[._]\d+)*|rev\d*|r\d|surum\s?\d+|versiyon\s?\d+|version\s?\d+|son|final|nihai|guncel|latest|yeni|eski|"
                        r"taslak|draft|kopya|kopyasi|copy|duzeltilmis|revize|revised|edited)(?=$|[^a-z0-9])")
TARA_KOPYA_AD = re.compile(r"\(\d{1,3}\)|(^|[^a-z])(kopya|kopyasi|copy)($|[^a-z])")
TARA_MINHASH_N, TARA_BENZER = 64, 0.8

def tara_tur(ext): return TARA_TUR.get(ext.lstrip("."), "diger")
def ad_koku(ad):
    # uzantısız ad → (kök, tarih_var, işaret_var). Kök boşsa (yalnız tarih/sürüm) gruplanmaz.
    n = norm(os.path.splitext(ad)[0]); tarih = bool(TARA_TARIH.search(n)); n = TARA_TARIH.sub(" ", n)
    isaret = False
    while True:
        m = TARA_SURUM.sub(" ", n)
        if m == n: break
        n, isaret = m, True
    k = re.sub(r"[^0-9a-z]+", "-", n).strip("-")
    return k, tarih, isaret
def _sha256(yol):
    import hashlib
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def tara_okunamaz(yol, ext):
    # parolalı/bozuk denetimi (parola sorulmaz): şifreli Office dosyası OLE kabıdır (zip değil), şifreli PDF'te /Encrypt
    try:
        with open(yol, "rb") as f: bas = f.read(8)
        if ext in (".docx", ".xlsx", ".pptx"):
            if bas.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"): return "parolali"
            if not bas.startswith(b"PK"): return "bozuk"
            with zipfile.ZipFile(yol) as z:
                if any(i.flag_bits & 1 for i in z.infolist()): return "parolali"
        elif ext == ".zip":
            with zipfile.ZipFile(yol) as z:
                if any(i.flag_bits & 1 for i in z.infolist()): return "parolali"
        elif ext == ".pdf":
            if not bas.startswith(b"%PDF"): return "bozuk"
            boy = os.path.getsize(yol)
            with open(yol, "rb") as f:
                if boy <= (4 << 20): v = f.read()
                else: v = f.read(1 << 18); f.seek(-(1 << 18), 2); v += f.read()
            if b"/Encrypt" in v: return "parolali"
    except zipfile.BadZipFile: return "bozuk"
    except OSError: return "okunamadi"
    return None
# v0.76.0 (T6): sihirbazın tarama ekranında kullanıcı kararı — ayar "dahil" (adla hariç tutulan dosya yine de dizine girer) ve "asil" (türetilmiş/dışa
# aktarım sayılan dosya ya da klasör asıl belge sayılır). İkisi de proje köküne göre yol; klasör verilirse altındaki her şey.
def _ayar_yolda(kisa, anahtar): return any(kisa == y or kisa.startswith(str(y).rstrip("/") + "/") for y in (AYAR.get(anahtar) or []) if y)
def tara_gizli(kisa, ext, tur):
    if _ayar_yolda(kisa, "dahil"): return None
    ad = norm(os.path.basename(kisa))
    if ext in TARA_GIZLI_UZ or ad in (".env", "id_rsa", "id_ed25519") or ad.startswith(".env."): return "ad: anahtar/ortam dosyası"
    if TARA_GIZLI_AD.search(ad): return "ad: " + TARA_GIZLI_AD.search(ad).group(0).strip(" ._-")
    if tur in ("goruntu",) or ext == ".pdf":
        m = TARA_KIMLIK_AD.search(ad)
        if m: return "ad: kimlik taraması (" + m.group(0) + ")"
    return None
def tara_kaynak_turu(kisa, ext, ayni_klasor_kokler, disa):
    # → (tür, neden). Sıra: kullanıcının "asil" işareti > ayardaki dışa aktarım yolu > dışa aktarım klasörü > tarih-saat damgalı veri dosyası > türetilmiş adı/klasörü > asıl.
    if _ayar_yolda(kisa, "asil"): return "asil", "kullanıcı: asıl"
    if any(kisa == d or kisa.startswith(d.rstrip("/") + "/") for d in disa): return "disa_aktarim", "ayar: veritabani.disa_aktarim"
    parcalar = [norm(p) for p in kisa.split("/")[:-1]]
    for p in parcalar:
        if TARA_DISA_KLASOR.match(p): return "disa_aktarim", f"klasör: {p}"
    ad = norm(os.path.basename(kisa))
    if ext in TARA_DISA_UZ and TARA_SAAT.search(ad): return "disa_aktarim", "ad: tarih-saat damgalı veri"
    if ANALIZ and kisa.startswith(ANALIZ): return "turetilmis", "ayar: analiz_klasorleri"
    for p in parcalar:
        if TARA_TURETILMIS_KLASOR.match(p): return "turetilmis", f"klasör: {p}"
    m = TARA_TURETILMIS_AD.search(os.path.splitext(ad)[0])
    if m: return "turetilmis", "ad: " + m.group(2)
    kok = os.path.splitext(ad)[0]
    if ext not in TARA_ASIL_UZ and any(u in TARA_ASIL_UZ and u != ext for u in ayni_klasor_kokler.get(kok, ())):
        return "turetilmis", "aynı adlı özgün belgenin çıktısı"
    return "asil", ""
def tara_metin(yol, ext, sinir=200_000, sha=None):
    try:
        if ext == ".docx": return docx_metin(yol)[:sinir]
        if ext == ".xlsx": return " ".join(m for _, _, m in xlsx_parcala(yol))[:sinir]
        if ext in CEVIR_UZ: ps = cevrilmis(yol, sha); return " ".join(m for _, m in ps)[:sinir] if ps else None
        if ext in (".html", ".htm"): return html_metin(open(yol, encoding="utf-8", errors="replace").read(sinir * 2))[:sinir]
        return open(yol, encoding="utf-8", errors="replace").read(sinir)
    except Exception: return None
def minhash(metin):
    # sözcük üçlüleri (shingle) → 64 değerlik imza; iki imzanın eş değer oranı ≈ Jaccard benzerliği
    import hashlib
    k = kelimeler(metin)
    sh = {" ".join(k[i:i + 3]) for i in range(max(1, len(k) - 2))} if k else set()
    if not sh: return None
    P = (1 << 61) - 1; hs = [int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "big") for s in sh]
    if not _MH_AB:
        rnd = __import__("random").Random(20261017); _MH_AB.extend((rnd.randrange(1, P), rnd.randrange(0, P)) for _ in range(TARA_MINHASH_N))
    return [min((a * h + b) % P for h in hs) for a, b in _MH_AB]
_MH_AB = []  # sabit tohumlu katsayılar: imzalar turlar arasında karşılaştırılabilir
def minhash_benzer(x, y): return sum(1 for a, b in zip(x, y) if a == b) / TARA_MINHASH_N if x and y else 0.0
def tara_baglan(c):
    c.execute("""CREATE TABLE IF NOT EXISTS tarama(yol TEXT PRIMARY KEY, mtime REAL, boy INTEGER, tur TEXT, sha256 TEXT, minhash TEXT,
                 surum_grubu TEXT, gecerli INTEGER, kopya_of TEXT, kaynak_turu TEXT, kaynak_neden TEXT, gizli INTEGER, gizli_neden TEXT, hata TEXT, t REAL)""")
    var = [r[1] for r in c.execute("PRAGMA table_info(dosya)")]
    for k, tip in (("sha256", "TEXT"), ("surum_grubu", "TEXT"), ("gecerli", "INTEGER"), ("kopya_of", "TEXT"), ("kaynak_turu", "TEXT"), ("gizli", "INTEGER"), ("hata", "TEXT"),
                   ("gizli_parca", "INTEGER"), ("cevirme", "TEXT")):
        if k not in var: c.execute(f"ALTER TABLE dosya ADD COLUMN {k} {tip}")
TARA_DOSYA_ALAN = "sha256, surum_grubu, gecerli, kopya_of, kaynak_turu, gizli, hata"
def tara_dosyaya(c, kisa=None):
    # tarama sonucunu dizindeki dosya satırına yaz (yalnız değişme zamanı ve boyutu aynıysa: dosya taramadan sonra değiştiyse alanlar boş kalır)
    w = "" if kisa is None else " WHERE yol = ?"
    c.execute(f"""UPDATE dosya SET ({TARA_DOSYA_ALAN}) = (SELECT {TARA_DOSYA_ALAN} FROM tarama t WHERE t.yol = dosya.yol AND t.mtime = dosya.mtime AND t.boy = dosya.boy){w}""",
              () if kisa is None else (kisa,))
def tara(c=None, sessiz=True):
    c = c or baglan(); t0 = time.time()
    vt = AYAR.get("veritabani") if isinstance(AYAR.get("veritabani"), dict) else {}
    disa = [str(d).strip("/") for d in (vt.get("disa_aktarim") or []) if str(d).strip("/")]
    eski = {r[0]: r[1:] for r in c.execute("SELECT yol, mtime, boy, sha256, minhash, hata FROM tarama")}
    eris, atlanan, kayit = [], collections.Counter(), []
    hata_kayit = (lambda e: eris.append(os.path.relpath(e.filename, PROJE) if e.filename else ""))
    try:
        if not os.listdir(PROJE): eris.append("")
    except OSError: eris.append("")
    for kok, dirs, fs in os.walk(PROJE, onerror=hata_kayit, followlinks=False):
        rel = os.path.relpath(kok, PROJE); rel = "" if rel == "." else rel
        dirs[:] = sorted(d for d in dirs if not any(os.path.join(rel, d) == h or os.path.join(rel, d).startswith(h + "/") for h in HARIC))
        for f in sorted(fs):
            k = os.path.join(rel, f); y = os.path.join(kok, f)
            if k in HARIC: atlanan["ayar: haric"] += 1; continue
            if f.startswith("~$") or f.startswith(".~lock."): atlanan["kilit dosyası"] += 1; continue
            if f.lower() in TARA_ATLA or f.startswith("._"): atlanan["sistem dosyası"] += 1; continue
            if os.path.islink(y): atlanan["kısayol"] += 1; continue
            try: st = os.stat(y)
            except OSError: eris.append(k); continue
            kayit.append((k, y, st))
    # özgün belge + çıktısı eşleşmesi için: klasör → ad kökü (uzantısız, sadeleşmiş) → uzantılar
    kokler = collections.defaultdict(lambda: collections.defaultdict(set))
    for k, y, st in kayit: kokler[os.path.dirname(k)][norm(os.path.splitext(os.path.basename(k))[0])].add(os.path.splitext(k)[1].lower())
    satir = {}
    for k, y, st in kayit:
        ext = os.path.splitext(k)[1].lower(); tur = tara_tur(ext); e = eski.get(k)
        if e and e[0] == st.st_mtime and e[1] == st.st_size and e[2]: sha, mh, hata = e[2], e[3], e[4]
        else:
            try: sha = _sha256(y)
            except OSError: eris.append(k); continue
            hata = tara_okunamaz(y, ext) if st.st_size else "bos"; mh = None
        if mh is None and (ext in TARA_METIN or ext in CEVIR_UZ) and not hata and st.st_size <= (50 << 20):  # çevrilmiş metin sonradan gelir
            t = tara_metin(y, ext, sha=sha); s = minhash(t) if t else None; mh = json.dumps(s) if s else None
        kt, kn = tara_kaynak_turu(k, ext, kokler[os.path.dirname(k)], disa)
        gn = tara_gizli(k, ext, tur)
        satir[k] = dict(yol=k, mtime=st.st_mtime, boy=st.st_size, tur=tur, sha256=sha, minhash=mh, surum_grubu=None, gecerli=1, kopya_of=None,
                        kaynak_turu=kt, kaynak_neden=kn, gizli=1 if gn else 0, gizli_neden=gn, hata=hata)
    # birebir kopya: adında kopya işareti olmayan, yolu kısa, en eski olan asıl
    sha_grup = collections.defaultdict(list)
    for s in satir.values():
        if not s["gizli"] and s["boy"]: sha_grup[s["sha256"]].append(s)  # hariç tutulan dosya kopya/sürüm hesabına girmez
    kopyalar = []
    for g in sha_grup.values():
        if len(g) < 2: continue
        g.sort(key=lambda s: (bool(TARA_KOPYA_AD.search(norm(os.path.basename(s["yol"])))), s["yol"].count("/"), s["mtime"], s["yol"]))
        for s in g[1:]: s["kopya_of"], s["gecerli"] = g[0]["yol"], 0
        kopyalar.append({"asil": g[0]["yol"], "kopyalar": [s["yol"] for s in g[1:]], "boy": g[0]["boy"]})
    # sürüm grubu: aynı klasör + aynı uzantı + aynı ad kökü; içerik benzerliğiyle doğrulanır
    aday = collections.defaultdict(list)
    for s in satir.values():
        if s["kopya_of"] or s["gizli"]: continue
        kk, tarih, isaret = ad_koku(os.path.basename(s["yol"]))
        if len(kk) < 2: continue  # yalnız tarih/sürümden oluşan ad: kök yok, gruplanmaz
        s["_tarih"] = tarih; aday[(os.path.dirname(s["yol"]), os.path.splitext(s["yol"])[1].lower(), kk)].append(s)
    gruplar = []
    for (kl, ext, kk), g in sorted(aday.items()):
        if len(g) < 2: continue
        ata = {id(s): id(s) for s in g}
        def bul(x):
            while ata[x] != x: ata[x] = ata[ata[x]]; x = ata[x]
            return x
        for i, a in enumerate(g):
            for b in g[i + 1:]:
                ma, mb = (json.loads(a["minhash"]) if a["minhash"] else None), (json.loads(b["minhash"]) if b["minhash"] else None)
                if ma and mb: ayni = minhash_benzer(ma, mb) >= TARA_BENZER
                elif ext in TARA_METIN or (a["minhash"] or b["minhash"]): ayni = False  # metin okunabildi ama boş/okunamadı ya da yalnız biri çevrildi: içerik kanıtı yok
                else: ayni = not (a["_tarih"] or b["_tarih"])  # içerik henüz yok (T2): adında tarih varsa gruplama
                if ayni: ata[bul(id(a))] = bul(id(b))
        alt = collections.defaultdict(list)
        for s in g: alt[bul(id(s))].append(s)
        for uyeler in alt.values():
            if len(uyeler) < 2: continue
            uyeler.sort(key=lambda s: (s["mtime"], s["yol"]), reverse=True)
            ad = os.path.join(kl, kk + ext) + (f"#{len(gruplar) + 1}" if any(x["ad"] == os.path.join(kl, kk + ext) for x in gruplar) else "")
            for j, s in enumerate(uyeler): s["surum_grubu"], s["gecerli"] = ad, 1 if j == 0 else 0
            gruplar.append({"ad": ad, "gecerli": uyeler[0]["yol"], "eski": [s["yol"] for s in uyeler[1:]]})
    # kayıt: okunamayan klasördeki eski satırlar korunur (launchd'nin Masaüstü engeli)
    eris = sorted({e for e in eris})
    korunur = lambda k: any(e == "" or k == e or k.startswith(e + "/") for e in eris)
    for k in set(eski) - set(satir):
        if not korunur(k): c.execute("DELETE FROM tarama WHERE yol=?", (k,))
    simdi = time.time()
    c.executemany("INSERT OR REPLACE INTO tarama VALUES(:yol,:mtime,:boy,:tur,:sha256,:minhash,:surum_grubu,:gecerli,:kopya_of,:kaynak_turu,:kaynak_neden,:gizli,:gizli_neden,:hata,:t)",
                  [dict(s, t=simdi) for s in satir.values()])
    tara_dosyaya(c)
    for s in satir.values():  # kopya ve adla hariç dizinden çıkar (dizinle de almaz; kopya olmaktan çıkınca sonraki dizin turu geri alır)
        if (s["kopya_of"] or s["gizli"]) and c.execute("SELECT 1 FROM dosya WHERE yol=?", (s["yol"],)).fetchone(): sil(c, s["yol"]); c.execute("DELETE FROM dosya WHERE yol=?", (s["yol"],))
    c.commit()
    ss = list(satir.values())
    rapor = {"t": int(simdi), "proje": PROJE, "sure_sn": round(time.time() - t0, 1),
             "sayilar": {"dosya": len(ss), "boyut": sum(s["boy"] for s in ss), "tur": dict(collections.Counter(s["tur"] for s in ss).most_common()),
                         "kopya": sum(len(k["kopyalar"]) for k in kopyalar), "kopya_kumesi": len(kopyalar),
                         "surum_grubu": len(gruplar), "eski_surum": sum(len(g["eski"]) for g in gruplar),
                         "kaynak_turu": dict(collections.Counter(s["kaynak_turu"] for s in ss)), "haric": sum(s["gizli"] for s in ss),
                         "okunamayan": sum(1 for s in ss if s["hata"]), "atlanan": dict(atlanan), "erisilemeyen": eris},
             "surum_gruplari": gruplar, "kopyalar": kopyalar,
             "haric": [{"yol": s["yol"], "neden": s["gizli_neden"]} for s in ss if s["gizli"]],
             "okunamayan": [{"yol": s["yol"], "hata": s["hata"]} for s in ss if s["hata"]],
             "kaynak_turu": [{"yol": s["yol"], "tur": s["kaynak_turu"], "neden": s["kaynak_neden"]} for s in ss if s["kaynak_turu"] != "asil"],
             "dosyalar": [{k: s[k] for k in ("yol", "tur", "boy", "mtime", "sha256", "kaynak_turu", "surum_grubu", "gecerli", "kopya_of", "gizli", "hata")} for s in ss]}
    try:
        with open(TARA_RAPOR + ".tmp", "w", encoding="utf-8") as f: json.dump(rapor, f, ensure_ascii=False, indent=1)
        os.chmod(TARA_RAPOR + ".tmp", 0o600); os.replace(TARA_RAPOR + ".tmp", TARA_RAPOR)
    except OSError: pass
    return rapor
def tara_ozet(r):
    s = r["sayilar"]; kt = s["kaynak_turu"]
    out = [f"tarama: {s['dosya']} dosya · {s['boyut'] / 1e6:.1f} MB · {r['sure_sn']} sn",
           "  türler: " + ", ".join(f"{t} {n}" for t, n in s["tur"].items()),
           f"  birebir kopya: {s['kopya']} ({s['kopya_kumesi']} küme) · sürüm grubu: {s['surum_grubu']} ({s['eski_surum']} eski sürüm)",
           f"  kaynak türü: asıl {kt.get('asil', 0)} · türetilmiş {kt.get('turetilmis', 0)} · dışa aktarım {kt.get('disa_aktarim', 0)}",
           f"  hariç (adla): {s['haric']} · okunamayan (parolalı/bozuk/boş): {s['okunamayan']}" + (" · atlanan: " + ", ".join(f"{k} {n}" for k, n in s["atlanan"].items()) if s["atlanan"] else "")]
    if s["erisilemeyen"]: out.append("  okunamayan klasör: " + ", ".join(e or "proje kökü" for e in s["erisilemeyen"][:5]) + " (eski kayıtlar korundu)")
    out.append(f"  rapor: {TARA_RAPOR}")
    return "\n".join(out)

# --- Çevirme (proje hazırlığı T2, planlar/proje-hazirligi.md §2 Adım 2) ---------------------------------------------
# PDF, sunum ve görüntüler (CEVIR_UZ) Mac'te metne çevrilir: <ortak>/cevir-venv'deki cevir-isci.py (Docling + Apple Vision; ağ kapalı).
# Sonuç <uygulama>/cevirme-onbellek/<sha256>.json (proje klasörüne yazılmaz; aynı içerik bir kez çevrilir). `cevir` önce `tara`yı çalıştırır;
# adla hariç tutulan, birebir kopya, parolalı/bozuk/boş dosya çevrilmez. Her dosyaya zaman sınırı: aşılırsa işçi öldürülür, dosya
# "zaman_asimi" diye önbelleğe yazılır, sonraki dosya yeni işçiyle; işçi CEVIR_YENILE dosyada bir yenilenir (bellek). Toplantı başlarsa
# dosyalar arasında durur; yeniden çalıştırınca önbellekte olanlar atlanır (kaldığı yerden). Dizin (guncelle) çevrilmiş metni önbellekten okur.
# G3 — içerikle gizli bilgi: dizine giren her parça gizli_bilgi()'den geçer (şifre/parola + değer, API anahtarı biçimleri, özel anahtar,
# Luhn'u tutan kart numarası, IBAN); eşleşen parça dizine girmez, dosyanın gizli_parca sayısı artar (rapor ve sihirbaz için).
class Bekliyor(Exception): pass  # çevrilmesi gereken dosyanın önbelleği yok: dizine henüz girmez
ONBELLEK = os.path.join(AYAR["uygulama"], "cevirme-onbellek")
CEVIR_PY = os.environ.get("SUFLOR_CEVIR_PY") or os.path.join(AYAR["ortak"], "cevir-venv", "bin", "python")
CEVIR_ISCI = os.environ.get("SUFLOR_CEVIR_ISCI") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "cevir-isci.py")
CEVIR_YENILE, CEVIR_HAZIR_SN = 25, 300
def cevir_sure(ext): return int(AYAR.get("cevir_sure_sn") or 0) or (60 if ext not in (".pdf", ".pptx") else 180)

def eml_metin(yol):
    import email, email.policy
    m = email.message_from_binary_file(open(yol, "rb"), policy=email.policy.default)
    bas = "\n".join(f"{k}: {m[k]}" for k in ("Subject", "From", "To", "Cc", "Date") if m[k])
    govde = m.get_body(preferencelist=("plain", "html"))
    t = govde.get_content() if govde else ""
    if govde and govde.get_content_type() == "text/html": t = html_metin(t)
    return f"# {m['Subject'] or os.path.basename(yol)}\n\n{bas}\n\n{t}"

def _onbellek_yol(sha): return os.path.join(ONBELLEK, sha[:2], sha + ".json")
def cevrilmis(yol, sha=None):
    # dosyanın çevrilmiş parçaları [(konum, metin)] ya da None (henüz çevrilmedi); çevirme hatası → [] (dizine boş girer, yeniden denenmez)
    sha = sha or _sha256(yol)  # tarama satırı yoksa ya da eskiyse içerikten
    try: o = json.load(open(_onbellek_yol(sha), encoding="utf-8"))
    except (OSError, ValueError): return None
    return [] if o.get("hata") else [(k, m) for k, m in o.get("parcalar") or []]

_GIZLI_RX = [
    ("anahtar", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("anahtar", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("anahtar", re.compile(r"\b(?:sk|rk|pk)-(?:ant-|live_|test_|proj-)?[A-Za-z0-9_-]{20,}")),
    ("anahtar", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("anahtar", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("anahtar", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("anahtar", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
_SIFRE_RX = re.compile(r"(?i)(?:şifre|şifresi|sifre|parola|parolası|password|passwd|pwd|pass|pin)\b[^\n]{0,40}?[:=]?\s*[\"'`]?([^\s\"'`|,;]{8,64})")
_KART_RX = re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")
_IBAN_RX = re.compile(r"\b([A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?)\b")
def _luhn(s):
    t = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2: d = d * 2 - 9 if d > 4 else d * 2
        t += d
    return t % 10 == 0
def _iban_mi(s):
    s = s.replace(" ", "")
    if not 15 <= len(s) <= 34 or (s[:2] == "TR" and len(s) != 26): return False
    r = s[4:] + s[:4]
    return int("".join(str(int(ch, 36)) for ch in r)) % 97 == 1
def gizli_bilgi(metin):
    # → neden ya da None. Şifre: anahtar sözcükten sonra 40 karakter içinde harf + rakam (ya da işaret) içeren 8+ karakterlik değer.
    if not metin: return None
    for ad, rx in _GIZLI_RX:
        if rx.search(metin): return ad
    for m in _SIFRE_RX.finditer(metin):
        v = m.group(1)
        if re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", v) and (re.search(r"\d", v) and re.search(r"[^\w]", v) or re.search(r"\d", v) and re.search(r"[A-ZÇĞİÖŞÜ]", v) and re.search(r"[a-zçğıöşü]", v)): return "şifre"
    for m in _KART_RX.finditer(metin):
        d = re.sub(r"\D", "", m.group(0))
        if 13 <= len(d) <= 19 and d[0] in "3456" and _luhn(d) and len(set(d)) > 3: return "kart"
    for m in _IBAN_RX.finditer(metin):
        if _iban_mi(m.group(1)): return "iban"
    return None

def hazirlik_suruyor():  # v0.76.0: sihirbazın hazırlık işi (hazirlik.py calis) kilidi tutuyor mu — Brifing yardımcısının turu aynı dosyaları ikinci kez çevirmesin
    import fcntl
    try:
        with open(os.path.join(AYAR["uygulama"], "hazirlik.kilit"), "a") as k:
            try: fcntl.flock(k, fcntl.LOCK_EX | fcntl.LOCK_NB); return False
            except OSError: return True
    except OSError: return False
def toplantida():  # süren toplantı: aktarıcının nabız dosyasında toplantı + son 10 dk'da yazılmış
    try:
        y = os.path.join(AYAR["uygulama"], "canli", "heartbeat.json"); h = json.load(open(y, encoding="utf-8"))
        return bool((h.get("meeting") or (h.get("extension") or {}).get("call")) and time.time() - os.stat(y).st_mtime < 600)
    except (OSError, ValueError, AttributeError): return False

class _Isci:
    def __init__(self):
        import subprocess, threading, queue
        self.q = queue.Queue(); self.n = 0
        os.makedirs(AYAR["uygulama"], exist_ok=True)
        self.p = subprocess.Popen([CEVIR_PY, "-B", CEVIR_ISCI], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
                                  stderr=open(os.path.join(AYAR["uygulama"], "cevir-isci.log"), "a", encoding="utf-8"),
                                  env=dict(os.environ, SUFLOR_ORTAK=AYAR["ortak"], PYTHONDONTWRITEBYTECODE="1"))
        def oku():
            for ln in self.p.stdout:
                try: self.q.put(json.loads(ln))
                except ValueError: pass
            self.q.put({"bitti": True})  # süreç kendiliğinden kapandı (çöktü)
        threading.Thread(target=oku, daemon=True).start()
        self.hazir = self._al(CEVIR_HAZIR_SN) or {"hazir": False, "hata": "işçi açılmadı"}
    def _al(self, sn):
        import queue
        try: return self.q.get(timeout=sn)
        except queue.Empty: return None
    def iste(self, yol, sn):
        self.n += 1
        try: self.p.stdin.write(json.dumps({"id": self.n, "yol": yol}, ensure_ascii=False) + "\n"); self.p.stdin.flush()
        except OSError: return {"hata": "işçi kapandı"}
        while True:
            o = self._al(sn)
            if o is None: self.kapat(); return {"hata": "zaman_asimi"}
            if o.get("bitti"): self.kapat(); return {"hata": "işçi kapandı"}
            if o.get("id") == self.n: return o
    def kapat(self):
        try: self.p.kill()
        except OSError: pass
        self.p.wait()

def cevir(c=None, sinir=None, yeniden_dene=False, sessiz=True, isci_yenile=CEVIR_YENILE, butce_sn=None, ilerleme=None):  # ilerleme(n, toplam): sihirbaz (hazirlik.py)
    c = c or baglan(); t0 = time.time(); tara(c)
    adaylar = [r for r in c.execute("SELECT yol, sha256, mtime FROM tarama WHERE gizli=0 AND kopya_of IS NULL AND hata IS NULL ORDER BY mtime DESC")
               if os.path.splitext(r[0])[1].lower() in CEVIR_UZ]
    yap, onbellekte = [], 0
    for yol, sha, _ in adaylar:
        try: o = json.load(open(_onbellek_yol(sha), encoding="utf-8"))
        except (OSError, ValueError): o = None
        if o is None or (yeniden_dene and o.get("hata")): yap.append((yol, sha))
        else: onbellekte += 1
    if sinir: yap = yap[:sinir]
    say = collections.Counter(); hatalar = []; isci = None; durdu = None
    if yap and not os.path.exists(CEVIR_PY): durdu = f"çevirme ortamı yok ({CEVIR_PY}) — kurulum.py modeller"
    try:
        for i, (kisa, sha) in enumerate(yap):
            if durdu: break
            if toplantida(): durdu = "toplantı başladı — sonra kaldığı yerden"; break
            if butce_sn and time.time() - t0 > butce_sn: durdu = "tur süresi doldu — sonraki turda sürer"; break
            if isci is None or isci.n >= isci_yenile:
                if isci: isci.kapat()
                isci = _Isci()
                if not isci.hazir.get("hazir"): durdu = "işçi açılmadı: " + str(isci.hazir.get("hata"))[:160]; isci = None; break
            ext = os.path.splitext(kisa)[1].lower(); t1 = time.time()
            o = isci.iste(os.path.join(PROJE, kisa), cevir_sure(ext))
            if o.get("hata") in ("zaman_asimi", "işçi kapandı"): isci = None
            kayit = {"yol": kisa, "arac": isci.hazir.get("arac") if isci else None, "t": int(time.time()), "sure": round(time.time() - t1, 2)}
            if o.get("hata"): kayit["hata"] = o["hata"]; say["hata"] += 1; hatalar.append((kisa, o["hata"]))
            else: kayit["parcalar"] = o.get("parcalar") or []; say["cevrildi"] += 1; say["karakter"] += sum(len(m) for _, m in kayit["parcalar"])
            y = _onbellek_yol(sha); os.makedirs(os.path.dirname(y), exist_ok=True)
            with open(y + ".tmp", "w", encoding="utf-8") as f: json.dump(kayit, f, ensure_ascii=False)
            os.chmod(y + ".tmp", 0o600); os.replace(y + ".tmp", y)
            if o.get("hata") == "parolali": c.execute("UPDATE tarama SET hata='parolali' WHERE yol=?", (kisa,))
            if ilerleme: ilerleme(i + 1, len(yap))
            if not sessiz: print(f"  [{i + 1}/{len(yap)}] {kisa} — " + (f"hata: {o['hata']}" if o.get("hata") else f"{len(kayit['parcalar'])} parça, {kayit['sure']} sn"), file=sys.stderr)
    finally:
        if isci: isci.kapat()
    c.commit()
    n = guncelle(c)  # çevrilenler dizine
    gp = c.execute("SELECT count(*), coalesce(sum(gizli_parca), 0) FROM dosya WHERE gizli_parca > 0").fetchone()
    return {"aday": len(adaylar), "onbellekte": onbellekte, "cevrildi": say["cevrildi"], "hata": say["hata"], "hatalar": hatalar[:50], "karakter": say["karakter"],
            "kalan": len(adaylar) - onbellekte - say["cevrildi"] - say["hata"], "durdu": durdu, "dizine": n, "gizli_dosya": gp[0], "gizli_parca": gp[1],
            "sure_sn": round(time.time() - t0, 1)}
def cevir_ozet(r):
    s = [f"çevirme: {r['aday']} dosya adayı · önbellekte {r['onbellekte']} · bu tur çevrilen {r['cevrildi']} ({r['karakter']} karakter) · hata {r['hata']} · kalan {r['kalan']} · {r['sure_sn']} sn",
         f"  dizine giren/güncellenen dosya: {r['dizine']} · gizli bilgi olabilir (parça dizine girmedi): {r['gizli_dosya']} dosya, {r['gizli_parca']} parça"]
    if r["hatalar"]: s.append("  hatalar: " + ", ".join(f"{k} ({h})" for k, h in r["hatalar"][:8]))
    if r["durdu"]: s.append("  durdu: " + r["durdu"])
    return "\n".join(s)

# --- Anlama göre arama (proje hazırlığı T4, planlar/proje-hazirligi.md §2 Adım 3) ------------------------------------
# multilingual-e5-base gömmeleri <uygulama>/gomme/ altında (gomme-isci.py; <ortak>/cevir-venv). Yalnız sonuçta görünebilen parçalar gömülür
# (geçerli sürüm; veritabanı kipinde dışa aktarım hariç). Sorgu, arka planda açık tutulan sunucuya Unix soketiyle gider (~10 ms); sunucu yoksa
# bu arama yalnız sözcükle yapılır ve sunucu açılır (ilk kez ~12 sn) — Konuş ön araması hiç beklemez. Sözcük ve anlam sıraları RRF (k = 60)
# ile birleşir (k ve sözcük kesimi ölçümle: RRF_K, RRF_FTS). Toplu dizinleme Brifing yardımcısının dizin turunda (en çok `gomme_tur_sn`), toplantıda başlamaz, paketler arasında durur.
GOMME = os.path.join(AYAR["uygulama"], "gomme"); ANLAM_SOKET = os.path.join(AYAR["uygulama"], "anlam.sock")
GOMME_ISCI = os.environ.get("SUFLOR_GOMME_ISCI") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "gomme-isci.py")
ANLAM_KAPALI = AYAR.get("anlam_arama") is False
ANLAM_SN, ANLAM_K = 0.25, 100
RRF_K, RRF_FTS = 10, 20  # gerçek proje ölçümü (27 proje + 46 görüşme sorusu, ilk 5): k=10 ve sözcük sırasının ilk 20'si en iyi denge — 11/27 · 24/46 → 14/27 · 35/46
_ANLAM = {"acilis": 0}
def anlam_hazir(): return not ANLAM_KAPALI and os.path.exists(CEVIR_PY) and os.path.isdir(os.path.join(AYAR["ortak"], "anlam-modeller")) and os.path.exists(os.path.join(GOMME, "durum.json"))
def gomme_kosul():
    k = "COALESCE(d.gecerli, 1) = 1"
    return k + (" AND COALESCE(d.kaynak_turu, 'asil') != 'disa_aktarim'" if VT_KIPI else "")
def anlam_sunucu_ac():
    if time.time() - _ANLAM["acilis"] < 60: return  # açılıyor
    _ANLAM["acilis"] = time.time()
    import subprocess
    try:
        subprocess.Popen([CEVIR_PY, "-B", GOMME_ISCI, "--sunucu", "--db", DB, "--klasor", GOMME, "--soket", ANLAM_SOKET,
                          "--bos-dk", str(AYAR.get("anlam_bos_dk") or 30)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=open(os.path.join(AYAR["uygulama"], "anlam-sunucu.log"), "a"), start_new_session=True,
                         env=dict(os.environ, SUFLOR_ORTAK=AYAR["ortak"], PYTHONDONTWRITEBYTECODE="1"))
    except OSError: pass
def anlam_ara(q, k=ANLAM_K):
    # → [(parça no, benzerlik)] ya da None (kapalı, hazır değil, sunucu açılıyor ya da zaman aşımı); hiçbir durumda ANLAM_SN'den fazla beklemez
    if not anlam_hazir(): return None
    import socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(ANLAM_SN)
    try:
        s.connect(ANLAM_SOKET); s.sendall((json.dumps({"q": q, "k": k}, ensure_ascii=False) + "\n").encode()); veri = b""
        while not veri.endswith(b"\n"):
            x = s.recv(1 << 20)
            if not x: break
            veri += x
        o = json.loads(veri); _ANLAM["acilis"] = 0  # v0.92.1: sunucu ayaktaydı → sonra kapanırsa (boşta) bir sonraki arama 60 sn beklemeden yeniden açar
        return [(int(i), sk) for i, sk in o["sonuc"]] if "sonuc" in o else None
    except (FileNotFoundError, ConnectionRefusedError): anlam_sunucu_ac(); return None
    except (OSError, ValueError, KeyError): return None
    finally: s.close()
def gomme(c=None, butce_sn=None, sessiz=True, ilerleme=None):
    # eksik gömmeleri hesapla (işçi en çok 4 pakette bir yenilenir); toplantıda başlamaz → {"eksik", "yapilan", "durdu", "sure_sn"}
    import subprocess
    c = c or baglan(); t0 = time.time(); top = {"eksik": None, "yapilan": 0, "durdu": None}
    if ANLAM_KAPALI or not os.path.exists(CEVIR_PY) or not os.path.isdir(os.path.join(AYAR["ortak"], "anlam-modeller")): top["durdu"] = "anlam araması kurulu değil"; return top
    nabiz = os.path.join(AYAR["uygulama"], "canli", "heartbeat.json")
    while True:
        if toplantida(): top["durdu"] = "toplantı"; break
        kalan = None if not butce_sn else butce_sn - (time.time() - t0)
        if kalan is not None and kalan < 20: top["durdu"] = "tur süresi doldu — sonraki turda sürer"; break
        try:
            r = subprocess.run([CEVIR_PY, "-B", GOMME_ISCI, "--dizinle", "--db", DB, "--klasor", GOMME, "--kosul", gomme_kosul(), "--nabiz", nabiz,
                                "--paket-sinir", "4"] + (["--sure", str(int(kalan))] if kalan else []), capture_output=True, text=True,
                               timeout=(kalan + 120) if kalan else 7200, env=dict(os.environ, SUFLOR_ORTAK=AYAR["ortak"], PYTHONDONTWRITEBYTECODE="1"))
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except (subprocess.TimeoutExpired, ValueError, IndexError, OSError) as e: top["durdu"] = f"işçi hatası ({e.__class__.__name__})"; break
        if top["eksik"] is None: top["eksik"] = o["eksik"]
        top["yapilan"] += o["yapilan"]
        if ilerleme and top["eksik"]: ilerleme(top["yapilan"], top["eksik"])
        if not sessiz and o["yapilan"]: print(f"  gömme: {top['yapilan']}/{top['eksik']} parça", file=sys.stderr)
        if o.get("durdu") != "paket sınırı": top["durdu"] = o.get("durdu"); break
    top["sure_sn"] = round(time.time() - t0, 1); return top
def rrf_birlestir(sira_listeleri, k=RRF_K):
    p = {}
    for liste in sira_listeleri:
        for r, i in enumerate(liste): p[i] = p.get(i, 0.0) + 1.0 / (k + r + 1)
    return p

# --- Sözlük ve sorgu --------------------------------------------------------------------------------------------
_SOZ = {}
def _mt(y):
    try: return os.stat(y).st_mtime
    except OSError: return None
def sozluk():  # dosyalar değişince yeniden okunur (aktarıcı modülü bir kez yükler; kopya sonradan gelebilir)
    k = (_mt(SUFLOR_SOZLUK), _mt(os.path.join(PROJE, SOZLUK)), _mt(SOZLUK_KOPYA))
    if _SOZ.get("k") != k: _SOZ.update(k=k, v=_sozluk_oku())
    return _SOZ["v"]
def sozluk_kopyala():
    # dış sözlük .tsv'sini uygulama klasörüne kopyala (dizin turunda; Brifing yardımcısı Masaüstü izniyle çalışır). Kaynak okunamıyorsa
    # (launchd'deki aktarıcı) kopyaya dokunulmaz; proje okunabilir ve kaynak silinmişse kopya da silinir. → True: kopya değişti
    kaynak = os.path.join(PROJE, SOZLUK)
    try: st = os.stat(kaynak); veri = open(kaynak, "rb").read()
    except FileNotFoundError:
        try: os.listdir(os.path.dirname(kaynak) if os.path.isdir(os.path.dirname(kaynak)) else PROJE)
        except OSError: return False
        if os.path.exists(SOZLUK_KOPYA): os.remove(SOZLUK_KOPYA); return True
        return False
    except OSError: return False
    try:
        k = os.stat(SOZLUK_KOPYA)
        if k.st_mtime == st.st_mtime and k.st_size == st.st_size: return False
    except OSError: pass
    os.makedirs(os.path.dirname(SOZLUK_KOPYA), exist_ok=True)
    with open(SOZLUK_KOPYA + ".tmp", "wb") as f: f.write(veri)
    os.utime(SOZLUK_KOPYA + ".tmp", (st.st_atime, st.st_mtime)); os.replace(SOZLUK_KOPYA + ".tmp", SOZLUK_KOPYA)
    return True
def _sozluk_oku():
    # [(doğru biçim, [biçimler…])] — biçimler sadeleştirilmiş; doğru biçim de biçimlerden biri.
    # önce Suflor sözlüğü (sozluk.json, kullanıcının kararları); dış sözlük önerilerinden yalnız onunla çakışmayanlar
    # (dış sözlük bir adı ters yönde düzeltebilir; doğru ad kullanıcının kararıdır).
    out, gor = [], set(); grup = {}
    try:
        for t in json.load(open(SUFLOR_SOZLUK, encoding="utf-8")).get("terimler", []):
            d = str(t.get("dogru") or "").strip()
            if d: grup.setdefault(d, set()).update(norm(x).strip() for x in [d] + list(t.get("yanlis") or []) if norm(x).strip())
    except (OSError, ValueError): pass
    for d, b in grup.items(): out.append((d, sorted(b, key=len, reverse=True))); gor |= b
    try:
        try: f = open(os.path.join(PROJE, SOZLUK), encoding="utf-8")
        except PermissionError: f = open(SOZLUK_KOPYA, encoding="utf-8")  # aktarıcı (launchd): Brifing yardımcısının yazdığı kopya
        for i, ln in enumerate(f):
            p = ln.rstrip("\n").split("\t")
            if i == 0 or len(p) < 2: continue
            dogru = re.split(r"\s*\(", p[1])[0].strip()
            bicim = {norm(b).strip() for b in p[0].split("|") if norm(b).strip()} | ({norm(dogru)} if norm(dogru).strip() else set())
            if bicim & gor: continue
            out.append((dogru, sorted(bicim, key=len, reverse=True)))
    except OSError: pass  # yok (kopya da yoksa Konuş ön araması sözlüksüz sürer)
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
_KONUSMACI = {}
def konusmacilar(c):
    # dizindeki konuşmacı adlarının kelimeleri (≥3 harf, K01/G gibi kodlar hariç) → sorguda kişi adı tanınsın. Önbellekli (v0.70.2): her aramada
    # baştan sayılıyordu, disk önbelleği soğukken ~0,9 sn (Konuş ön araması 17 Ekim akşamı 1,2–1,3 sn); yalnız dizine yeni parça ya da görüşme girince yenilenir.
    anahtar = (c.execute("SELECT max(id) FROM parca").fetchone()[0], c.execute("SELECT count(*), max(mtime) FROM dosya WHERE tur = 'gorusme'").fetchone())
    if _KONUSMACI.get("k") == anahtar: return _KONUSMACI["ad"]
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
    _ADLAR.update(ad); _KONUSMACI.update(k=anahtar, ad=ad); return ad
TAKMA = {}
def ara(q, kim=None, turler=None, son=None, n=8, dosya_basina=2, guncel=True, kapsam=None, aralik=None, eski=False, disa=None):  # guncel=False: dizini güncellemeden (Konuş ön araması, ~0,1 sn)
    # kapsam="ortak": yalnız ortak kaynaklar (özel kapsamlı bellek kaynakları ve Konuş geçmişi girmez); aralik=(baş, bitiş) ISO tarih: parçanın tarihi
    # T3 (proje hazırlığı §2 Adım 3): sürüm grubunun eski sürümleri sonuçtan çıkar (eski=True: dahil); veritabanı kipinde (ayar veritabani)
    # dışa aktarımlar sonuçtan çıkar (§2b; disa=True: dahil); türetilmiş ve dışa aktarım aynı puandaki asıl kaynağın arkasına düşer.
    c = baglan()
    if guncel: guncelle(c)
    if not kim:
        # "Ayşe yedekler için ne demişti?" → önce Ayşe'nin konuştuğu parçalar, sonra genel sonuçlar
        adlar = konusmacilar(c); bulunan = [w for w in kelimeler(q) if w in adlar]
        if bulunan:
            kalan = " ".join(w for w in kelimeler(q) if w not in bulunan)
            once, ek = ara(kalan, bulunan[0], turler, son, max(2, n // 2), dosya_basina, guncel=False, kapsam=kapsam, aralik=aralik, eski=eski, disa=disa) if kalan.strip() else ([], [])
            genel, ek2 = ara_ic(c, q, None, turler, son, n, dosya_basina, kapsam, aralik, eski, disa)
            gor = {r[0] for r in once}
            return (once + [r for r in genel if r[0] not in gor])[:n], ek or ek2
    return ara_ic(c, q, kim, turler, son, n, dosya_basina, kapsam, aralik, eski, disa)
VT_KIPI = isinstance(AYAR.get("veritabani"), dict) and bool(AYAR["veritabani"].get("yol"))
IKINCIL = 0.9  # türetilmiş/dışa aktarım parçasının BM25 puanı çarpanı (puan eksi; küçük çarpan = geride)
def ara_ic(c, q, kim, turler, son, n, dosya_basina, kapsam=None, aralik=None, eski=False, disa=None):
    gruplar, eklenen = sorgu_kur(q)
    if not gruplar and not kim: return [], eklenen
    if kim and not TAKMA: konusmacilar(c)  # --kim <takma ad> doğrudan gelince takma adlar henüz kurulmamış olabilir
    kosul, arg = [], []
    if turler: kosul.append("d.tur IN (%s)" % ",".join("?" * len(turler))); arg += turler
    if son: kosul.append("d.tarih >= ?"); arg.append((datetime.date.today() - datetime.timedelta(days=son)).isoformat())
    if kapsam == "ortak": kosul.append("COALESCE(d.kapsam, 'ortak') = 'ortak'")
    if aralik: kosul.append("COALESCE(p.tarih, d.tarih) BETWEEN ? AND ?"); arg += list(aralik)
    if not eski: kosul.append("COALESCE(d.gecerli, 1) = 1")
    if not (disa if disa is not None else not VT_KIPI): kosul.append("COALESCE(d.kaynak_turu, 'asil') != 'disa_aktarim'")
    def calis(eslesme):
        kk = kelimeler(kim)[0] if kim and kelimeler(kim) else None  # parantez — "a OR b AND kimn:x" b'ye bağlanıyordu
        m = ((f"({eslesme}) AND " if eslesme else "") + f"kimn : {terim(TAKMA.get(kk, kk))}") if kk else eslesme
        m = m.strip() or "*"
        sql = ("SELECT p.id, p.yol, p.konum, p.kim, p.metin, d.tur, COALESCE(p.tarih, d.tarih), d.baslik, bm25(ara, 1.0, 0.3) * "
               f"(CASE WHEN d.kaynak_turu IN ('turetilmis', 'disa_aktarim') THEN {IKINCIL} ELSE 1.0 END) AS s FROM ara "
               "JOIN parca p ON p.id = ara.rowid JOIN dosya d ON d.yol = p.yol WHERE ara MATCH ? "
               + ("AND " + " AND ".join(kosul) if kosul else "") + " ORDER BY s LIMIT 200")
        try: return c.execute(sql, [m] + arg).fetchall()
        except sqlite3.OperationalError: return []
    rows = calis(" AND ".join(gruplar)) if gruplar else calis("")
    if len(rows) < 3 and len(gruplar) > 1: rows = rows + [r for r in calis(" OR ".join(gruplar)) if r[0] not in {x[0] for x in rows}]
    # yakın tarihe hafif öncelik; aynı dosyadan en çok dosya_basina sonuç
    bugun = datetime.date.today()
    def yakinlik(r):
        try: gun = (bugun - datetime.date.fromisoformat(r[6])).days
        except Exception: gun = 365
        return 1.0 + 0.3 / (1 + max(gun, 0) / 14)
    sirali = sorted(rows, key=lambda r: r[8] * yakinlik(r))
    vek = anlam_ara(q) if not kim and not ANLAM_KAPALI else None  # T4: anlam sırası (sunucu yoksa None → yalnız sözcük)
    if vek:
        satir = {r[0]: r for r in rows}; eksik = [i for i, _ in vek if i not in satir]
        if eksik:
            sql = ("SELECT p.id, p.yol, p.konum, p.kim, p.metin, d.tur, COALESCE(p.tarih, d.tarih), d.baslik, 0.0 FROM parca p JOIN dosya d ON d.yol = p.yol "
                   f"WHERE p.id IN ({','.join('?' * len(eksik))})" + (" AND " + " AND ".join(kosul) if kosul else ""))
            for r in c.execute(sql, eksik + arg): satir[r[0]] = r
        puan = rrf_birlestir([[r[0] for r in sirali[:RRF_FTS]], [i for i, _ in vek if i in satir]])
        ikincil = {i for i, kt in c.execute(f"SELECT p.id, d.kaynak_turu FROM parca p JOIN dosya d ON d.yol = p.yol WHERE p.id IN ({','.join('?' * len(puan))})", list(puan))
                   if kt in ("turetilmis", "disa_aktarim")}
        sirali = [satir[i] for i in sorted(puan, key=lambda i: -puan[i] * (IKINCIL if i in ikincil else 1.0) * yakinlik(satir[i]))]
    secilen, say = [], {}
    for r in sirali:
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
    tr = sub.add_parser("tara"); tr.add_argument("--json", action="store_true", help="raporun tamamı")
    gm = sub.add_parser("gomme"); gm.add_argument("--sure", type=int, help="en çok N sn")
    cv = sub.add_parser("cevir"); cv.add_argument("--n", type=int, help="en çok N dosya"); cv.add_argument("--yeniden-dene", action="store_true", help="hata/zaman aşımı kayıtlarını da")
    a = sub.add_parser("ara"); a.add_argument("sorgu"); a.add_argument("--kim"); a.add_argument("--tur", help="virgüllü: toplanti,gorusme,analiz,sunum,tablo,belge,karar,kural,konusma")
    a.add_argument("--son", type=int, help="son N gün"); a.add_argument("--n", type=int, default=8); a.add_argument("--kapsam", choices=["ortak"], help="yalnız ortak kaynaklar")
    a.add_argument("--eski", action="store_true", help="eski sürümler dahil"); a.add_argument("--disa", action="store_true", help="dışa aktarımlar dahil (veritabanı kipinde)")
    A = ap.parse_args()
    if A.cmd == "dizin":
        c = baglan(); guncelle(c, A.yeniden, sessiz=False)
        if hazirlik_suruyor(): print("dizin: sihirbazın proje hazırlığı sürüyor — çevirme ve gömme onda", file=sys.stderr); sys.exit(0)
        if AYAR.get("cevir", True) is not False and os.path.exists(CEVIR_PY) and not toplantida():  # Brifing yardımcısının turu: çevrilmemiş PDF/görüntü (en çok ~4 dk)
            r = cevir(c, butce_sn=int(AYAR.get("cevir_tur_sn") or 240))
            if r["cevrildi"] or r["hata"] or r["durdu"]: print(cevir_ozet(r), file=sys.stderr)
        if not toplantida():  # T4: eksik gömmeler (en çok ~4 dk)
            g = gomme(c, butce_sn=int(AYAR.get("gomme_tur_sn") or 240))
            if g["yapilan"] or (g["durdu"] and g["durdu"] != "anlam araması kurulu değil"): print(f"gömme: {g}", file=sys.stderr)
        for tur, nd, np_ in c.execute("SELECT tur, count(*), sum(parca) FROM dosya GROUP BY tur ORDER BY 3 DESC"): print(f"  {tur}: {nd} dosya, {np_} parça")
    elif A.cmd == "gomme":
        print(json.dumps(gomme(sessiz=False, butce_sn=A.sure), ensure_ascii=False))
    elif A.cmd == "cevir":
        r = cevir(sinir=A.n, yeniden_dene=A.yeniden_dene, sessiz=False); print(cevir_ozet(r))
    elif A.cmd == "tara":
        r = tara(); print(json.dumps(r, ensure_ascii=False, indent=1) if A.json else tara_ozet(r))
    else:
        r = ara(A.sorgu, A.kim, A.tur.split(",") if A.tur else None, A.son, A.n, kapsam=A.kapsam, eski=A.eski, disa=True if A.disa else None); yaz(r, A.sorgu, r[1])
