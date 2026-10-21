#!/usr/bin/env python3
# Kurulum ortak klasördeki yerel Türkçe sesleri (Pocket, Piper) bu hesabın ayarına yazar (kurulum.py yerel_ses_bul, 21 Ekim): ikisi birden varsa,
# yalnız eksik anahtar, elle verilen yol korunur, beta kullanıcısında (ortak klasörde yok) hiçbir şey yazılmaz. İşlev AST ile alınır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yerel-ses-ayar.py
import ast, os, shutil, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
agac = ast.parse(open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read())
ns = {"os": os}; exec(compile(ast.Module([n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "yerel_ses_bul"], []), "kurulum.py", "exec"), ns)
bul = ns["yerel_ses_bul"]; ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)
T = tempfile.mkdtemp(prefix="yerel-ses-ayar-")
def dosya(y, x=False):
    os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w").close()
    if x: os.chmod(y, 0o755)
try:
    a = {}; kontrol("boş ortak klasör: hiçbir şey yazılmaz", bul(a, T) == [] and a == {})
    pp, hf = os.path.join(T, "tts-deneme", "yeni-venv", "bin", "python"), os.path.join(T, "tts-deneme", "hf")
    dosya(pp, x=True); a = {}
    kontrol("Pocket'ın yalnız Python'u var (model yok): yazılmaz", bul(a, T) == [] and a == {})
    os.makedirs(hf); a = {"ses_motoru": "mac"}
    kontrol("Pocket tam: iki anahtar yazılır, ses_motoru değişmez", bul(a, T) == ["pocket_python", "pocket_hf"] and a["pocket_python"] == pp and a["pocket_hf"] == hf and a["ses_motoru"] == "mac")
    a = {"pocket_python": "/elle/python"}; bul(a, T)
    kontrol("elle verilen yol korunur, yalnız eksik yazılır", a == {"pocket_python": "/elle/python", "pocket_hf": hf})
    py, mo = os.path.join(T, "tts-deneme", "piper-venv", "bin", "python"), os.path.join(T, "piper-ses", "tr-turkce.onnx")
    dosya(py); dosya(mo); a = {}; bul(a, T)
    kontrol("Piper Python'u çalıştırılabilir değilse Piper yazılmaz", "piper_python" not in a)
    os.chmod(py, 0o755); a = {}
    kontrol("Piper tam: iki anahtar yazılır", set(bul(a, T)) == {"pocket_python", "pocket_hf", "piper_python", "piper_model"} and a["piper_model"] == mo)
    kontrol("hepsi zaten varsa yazılan yok (ayar yeniden yazılmaz)", bul(dict(a), T) == [])
    src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read()
    kontrol("kur() ayarı kilitli yazıyor (ayar_degistir)", "ayar_degistir(_ys)" in src)
finally: shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
