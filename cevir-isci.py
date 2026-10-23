#!/usr/bin/env python3
# Belge → metin işçisi (proje hazırlığı T2; planlar/proje-hazirligi.md §2 Adım 2). Ortak klasördeki ayrı Python 3.12 ortamında çalışır
# (<ortak>/cevir-venv; kurulum.py modeller → cevir_kur): Docling (MIT) + Apple Vision OCR (ocrmac; tr-TR, en-US). Yerel: modeller
# <ortak>/cevir-modeller'dan, ağ kapalı (HF_HUB_OFFLINE). baglam.py `cevir` bu işçiyi açar, dosyaları tek tek verir; zaman sınırını,
# yeniden başlatmayı ve önbelleği baglam.py yönetir (bir dosya takılırsa süreç öldürülür, sonraki dosya yeni süreçte).
# Satır protokolü (stdin/stdout, JSON): başta {"hazir": true, "arac": "..."} · istek {"id", "yol"} → {"id", "parcalar": [[konum, metin], …]} ya da {"id", "hata"}.
# Konum: PDF'te "sayfa <n>", sunumda "slayt <n>", görüntüde "". HEIC önce macOS `sips` ile PNG'ye çevrilir. Parolalı dosyada parola sorulmaz.
# v0.121.0: Pages/Keynote (Docling iWork), Numbers ve .xls (xlrd) → tablo biçimlerinde ayrıca "tablolar": [{"sayfa", "satirlar"}] (proje veritabanına).
import json, os, subprocess, sys, tempfile, time

ORTAK = os.environ.get("SUFLOR_ORTAK") or "/Users/Shared/Suflor"
MODELLER = os.path.join(ORTAK, "cevir-modeller")
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HOME", MODELLER); os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
CIKIS = sys.stdout; sys.stdout = sys.stderr  # kütüphanelerin print'leri protokolü bozmasın
def yaz(o): CIKIS.write(json.dumps(o, ensure_ascii=False) + "\n"); CIKIS.flush()

def donusturucu():
    from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, OcrMacOptions
    po = PdfPipelineOptions(artifacts_path=MODELLER if os.path.isdir(MODELLER) else None)
    po.do_ocr = True; po.do_table_structure = True; po.ocr_options = OcrMacOptions(lang=["tr-TR", "en-US"])
    po.do_picture_classification = False; po.do_picture_description = False; po.do_code_enrichment = False; po.do_formula_enrichment = False
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po), InputFormat.IMAGE: ImageFormatOption(pipeline_options=po)})

def satir_parcalari(sayfa, satirlar):  # tablo satırları → [[konum, "Sayfa — başlık: değer · …"]] (baglam.py xlsx_parcala ile aynı biçim)
    out, bas = [], None
    for n, r in enumerate(satirlar, 1):
        h = [str(x).strip() for x in r]; dolu = [x for x in h if x]
        if not dolu: continue
        if bas is None and len(dolu) >= 2: bas = h; continue
        s = " · ".join(f"{a}: {b}" if a and len(a) < 40 else b for a, b in zip((bas or []) + [""] * len(h), h) if b)
        if s: out.append([f"{sayfa}!{n}", f"{sayfa} — {s}"[:1400]])
    return out
def xls_oku(yol):  # v0.121.0: eski Excel (BIFF) → xlrd (BSD; Docling .xls için LibreOffice ister)
    import datetime, xlrd
    wb = xlrd.open_workbook(yol); tablolar, out = [], []
    for sh in wb.sheets():
        satirlar = []
        for r in range(sh.nrows):
            sat = []
            for c in range(sh.ncols):
                h = sh.cell(r, c)
                if h.ctype == xlrd.XL_CELL_DATE:
                    try:
                        g = xlrd.xldate_as_datetime(h.value, wb.datemode); v = g.date().isoformat() if g.time() == datetime.time(0) else g.isoformat(timespec="minutes")
                    except (ValueError, OverflowError): v = h.value
                elif h.ctype == xlrd.XL_CELL_NUMBER: v = int(h.value) if float(h.value).is_integer() else h.value
                elif h.ctype == xlrd.XL_CELL_BOOLEAN: v = "doğru" if h.value else "yanlış"
                elif h.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR): v = ""
                else: v = str(h.value)
                sat.append(v)
            satirlar.append(sat)
        tablolar.append({"sayfa": sh.name, "satirlar": satirlar}); out += satir_parcalari(sh.name, satirlar)
    return out, tablolar
def parcalar(cv, yol):  # → (parçalar, tablolar): tablolar yalnız tablo biçimlerinde (.xls, .numbers) — baglam.py proje veritabanına yazar
    ext = os.path.splitext(yol)[1].lower(); gecici = None
    if ext == ".xls": return xls_oku(yol)
    try:
        if ext == ".heic":
            gecici = tempfile.mkdtemp(prefix="suflor-heic-"); png = os.path.join(gecici, "g.png")
            subprocess.run(["sips", "-s", "format", "png", yol, "--out", png], capture_output=True, timeout=60, check=True); yol = png
        doc = cv.convert(yol).document
        if ext == ".numbers":  # tablo başına sayfa: satırlar hem aramaya (parça) hem proje veritabanına (tablo)
            tablolar, out = [], []
            for i, tb in enumerate(doc.tables, 1):
                df = tb.export_to_dataframe(doc=doc); sayfa = f"Tablo {i}"
                satirlar = [[str(x) for x in df.columns]] + [["" if x is None else str(x) for x in r] for r in df.values.tolist()]
                tablolar.append({"sayfa": sayfa, "satirlar": satirlar}); out += satir_parcalari(sayfa, satirlar)
            return (out or [["", doc.export_to_markdown()]]), tablolar
        sayfalar = sorted(getattr(doc, "pages", {}) or {})
        if len(sayfalar) <= 1: return [["", doc.export_to_markdown()]], []
        on = "slayt " if ext in (".pptx", ".ppt", ".key") else "sayfa "
        out = [[f"{on}{n}", doc.export_to_markdown(page_no=n)] for n in sayfalar]
        return [p for p in out if p[1].strip()], []
    finally:
        if gecici: subprocess.run(["rm", "-rf", gecici])

def main():
    try:
        import docling; from importlib.metadata import version
        cv = donusturucu(); arac = f"docling {version('docling')} + vision"
    except Exception as e:
        yaz({"hazir": False, "hata": f"{e.__class__.__name__}: {str(e)[:200]}"}); return 1
    yaz({"hazir": True, "arac": arac})
    for satir in sys.stdin:
        try: istek = json.loads(satir)
        except ValueError: continue
        t = time.time()
        try:
            ps, tb = parcalar(cv, istek["yol"])
            yaz({"id": istek.get("id"), "parcalar": ps, **({"tablolar": tb} if tb else {}), "sure": round(time.time() - t, 2)})
        except Exception as e:
            m = f"{e.__class__.__name__}: {str(e)[:200]}"
            yaz({"id": istek.get("id"), "hata": "parolali" if any(k in m.lower() for k in ("password", "encrypt", "parola")) else m, "sure": round(time.time() - t, 2)})
    return 0

if __name__ == "__main__": sys.exit(main())
