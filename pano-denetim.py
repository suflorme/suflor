#!/usr/bin/env python3
# Pano/eklenti JavaScript sözdizimi denetimi: tek bir kaçışsız kesme işareti tüm panoyu boş bırakabiliyor (v0.2). Satır içi <script> blokları
# (pano/*.html, sihirbaz/*.html), pano/*.js, sihirbaz/*.js ve eklentinin kök *.js dosyaları geçici klasöre yazılıp `node --check` ile denenir.
#   PYTHONDONTWRITEBYTECODE=1 python3 pano-denetim.py [kök]     çıkış 0 temiz (ya da node yok: uyarı), 1 hata
# Kurulum (kurulum.py) ve commit kancası (yayinla.py --kanca-kur) bunu çağırır.
import glob, os, re, shutil, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.abspath(__file__))
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.S | re.I)
def node_bul():
    for a in (shutil.which("node"), os.path.expanduser("~/.local/bin/node"), "/opt/homebrew/bin/node", "/usr/local/bin/node"):
        if a and os.path.isfile(a) and os.access(a, os.X_OK): return a
    return None
def birimler(kok):  # (gösterim adı, kaynak, uzantı, ilk satır kayması)
    for f in sorted(glob.glob(os.path.join(kok, "pano", "*.html")) + glob.glob(os.path.join(kok, "sihirbaz", "*.html"))):
        s = open(f, encoding="utf-8").read()
        for m in SCRIPT.finditer(s):
            a = m.group(1)
            if re.search(r"\bsrc\s*=", a, re.I): continue
            t = re.search(r"""\btype\s*=\s*["']?([^"'\s>]+)""", a, re.I)
            if t and t.group(1).lower() not in ("text/javascript", "module", "application/javascript"): continue
            yield os.path.relpath(f, kok), m.group(2), ".mjs" if t and t.group(1).lower() == "module" else ".js", s.count("\n", 0, m.start(2))
    for f in sorted(glob.glob(os.path.join(kok, "*.js")) + glob.glob(os.path.join(kok, "pano", "*.js")) + glob.glob(os.path.join(kok, "sihirbaz", "*.js"))):
        yield os.path.relpath(f, kok), open(f, encoding="utf-8").read(), ".js", 0
def denetle(kok=KOD):
    """Hata listesi döner: ["dosya:satır mesaj", ...]; node yoksa None."""
    node = node_bul()
    if not node: return None
    T = tempfile.mkdtemp(prefix="pano-denetim-"); hata = []
    try:
        for i, (ad, kaynak, uz, kayma) in enumerate(birimler(kok)):
            y = os.path.join(T, f"{i}{uz}"); open(y, "w", encoding="utf-8").write(kaynak)
            r = subprocess.run([node, "--check", y], capture_output=True, text=True)
            if r.returncode:
                m = re.search(re.escape(y) + r":(\d+)", r.stderr); satir = int(m.group(1)) + kayma if m else "?"
                ileti = next((l for l in r.stderr.splitlines() if "Error" in l), "sözdizimi hatası").strip()
                hata.append(f"{ad}:{satir} {ileti}")
    finally: shutil.rmtree(T, ignore_errors=True)
    return hata
if __name__ == "__main__":
    kok = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else KOD
    h = denetle(kok)
    if h is None: print("UYARI: node bulunamadı — pano/eklenti JavaScript sözdizimi denetlenmedi."); sys.exit(0)
    for x in h: print("  " + x)
    print(f"{'✗' if h else '✓'} JavaScript sözdizimi: {len(h)} hata"); sys.exit(1 if h else 0)
