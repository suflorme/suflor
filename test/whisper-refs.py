#!/usr/bin/env python3
# Whisper modeli refs/main'siz düzende (yeni xet indirmesi; 27 Ekim ikinci hesapta anlam modelinde görüldü): kurulumun çevrimdışı
# açılış denemesi ve işçinin varsayılanı anlık görüntüden açar; whisper_refs_yaz refs/main'i yazar. Gerçek model (ortak klasör), ~10 sn.
import importlib.util, os, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: canlı kullanım koruması (gerçek model)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("kurulum", os.path.join(KOD, "kurulum.py")); k = importlib.util.module_from_spec(sp); sp.loader.exec_module(k)
ORT = k.yollar()["ortak"]; VPY = os.path.join(ORT, "whisper-venv", "bin", "python")
DEPO = "models--mlx-community--whisper-large-v3-turbo"; KAYNAK = os.path.join(ORT, "whisper-modeller", "hub", DEPO)
if not os.access(VPY, os.X_OK) or not os.path.isdir(os.path.join(KAYNAK, "snapshots", k.WHISPER_REV)): print("whisper-refs: atlandı (model yok)"); sys.exit(0)
hata = 0
def ok(c, m):
    global hata; print(("✓ " if c else "✗ ") + m); hata += not c
t = tempfile.mkdtemp(prefix="suflor-wrefs-"); ort = os.path.join(t, "ort"); d = os.path.join(ort, "whisper-modeller", "hub", DEPO)
try:
    os.makedirs(d); os.symlink(os.path.join(KAYNAK, "blobs"), os.path.join(d, "blobs"))  # bloblar paylaşılır, refs yok
    shutil.copytree(os.path.join(KAYNAK, "snapshots"), os.path.join(d, "snapshots"), symlinks=True)
    env = dict(os.environ, HF_HOME=os.path.join(ort, "whisper-modeller"), HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    yuk = lambda m: subprocess.run([VPY, "-c", "import sys, numpy as np, mlx_whisper; mlx_whisper.transcribe(np.zeros(16000, np.float32), "
                                    "path_or_hf_repo=sys.argv[1], language='tr')", m], env=env, capture_output=True, text=True).returncode == 0
    refs = os.path.join(d, "refs", "main")
    ok(not yuk("mlx-community/whisper-large-v3-turbo"), "depo adıyla açılış refs/main yokken düşüyor (eski kurulum denemesi)")
    s = k.whisper_snap(ort); ok(bool(s) and s.endswith(k.WHISPER_REV), "whisper_snap sabit sürümün anlık görüntüsünü buldu")
    ok(yuk(s), "kurulum denemesi (anlık görüntü yolu) açılıyor")
    r = subprocess.run([VPY, "-c", "import runpy, sys; print(runpy.run_path(sys.argv[1], run_name='deneme')['MODEL'])", os.path.join(KOD, "whisper-isci.py")],
                       env=env, capture_output=True, text=True)
    ok(r.stdout.strip() == s, "işçinin varsayılan modeli anlık görüntüye döndü")
    k.whisper_refs_yaz(ort); ok(os.path.isfile(refs) and open(refs).read() == k.WHISPER_REV, "whisper_refs_yaz refs/main'i yazdı")
    ok(yuk("mlx-community/whisper-large-v3-turbo"), "refs/main yazılınca depo adıyla da açılıyor")
    ok(k.whisper_snap(os.path.join(t, "yok")) is None, "model yokken whisper_snap boş")
finally: shutil.rmtree(t, ignore_errors=True)
print("whisper-refs: " + ("✓ hepsi geçti" if not hata else f"✗ {hata} hata")); sys.exit(1 if hata else 0)
