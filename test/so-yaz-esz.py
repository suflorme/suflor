# 13 Kasım (#45): _so_yaz eşzamanlı kayıtta FileNotFoundError vermemeli (aynı dosyaya iki iş parçacığı)
import ast, os, sys, tempfile, threading
KOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aktarici", "sozluk-ogren.py")
def fonk(yol):
    agac = ast.parse(open(yol, encoding="utf-8").read())
    f = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "_so_yaz")
    g = {"os": os, "threading": threading}; exec(compile(ast.Module([f], []), yol, "exec"), g); return g["_so_yaz"]
def dene(_so_yaz, n=8, tur=300):
    d = tempfile.mkdtemp(); hedef = os.path.join(d, "durum.json"); hata = []
    def is_():
        for i in range(tur):
            try: _so_yaz(hedef, '{"i": %d}' % i, 0o600)
            except Exception as e: hata.append(e)
    T = [threading.Thread(target=is_) for _ in range(n)]; [t.start() for t in T]; [t.join() for t in T]
    artik = [x for x in os.listdir(d) if x.endswith(".tmp")]
    return hata, artik, oct(os.stat(hedef).st_mode & 0o777)
eski = sys.argv[1] if len(sys.argv) > 1 else None
if eski: h, a, _ = dene(fonk(eski)); print(f"eski kod: {len(h)} hata ({type(h[0]).__name__ if h else '-'})")
h, a, izin = dene(fonk(KOD))
ok = not h and not a and izin == "0o600"
print(f"yeni kod: {len(h)} hata, {len(a)} artık geçici dosya, izin {izin}"); print("TAMAM" if ok else "HATA"); sys.exit(0 if ok else 1)
