#!/usr/bin/env python3
# Suflor'un kendi sesi (v0.30.2; deneme 6): hoparlörden okunan sesli çeviri özü / fısıltı mikrofondan geri gelirse kullanıcının satırı olmaz;
# kullanıcının aynı anda başka sözü ve okuma aralığı dışında aynı söz yazılır. Aktarıcı yalıtılmış kopyadan modül olarak yüklenir.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kendi-ses.py      (kaldı → çıkış 1; ~3 sn)
import importlib.util as u, json, os, shutil, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT = bos_port(8777)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-ks-")
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json"); sys.dont_write_bytecode = True
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)]; os.chdir(T)
sp = u.spec_from_file_location("relay_t", os.path.join(T, "relay.py")); m = u.module_from_spec(sp); sp.loader.exec_module(m)
yazilan = []; m._whisper_yaz = lambda is_, metin, ses=None, model=None: yazilan.append(metin)
t = time.time(); m.kendi_ses_kaydet("Eğlenceli değilse sadece bir serseri", t, t + 2.5)
sonuc = [m.whisper_yaz({"kanal": "ben", "t0": t + 0.3, "t1": t + 3.0}, "Eğlenceli değilse sadece bir serseri."),
         m.whisper_yaz({"kanal": "ben", "t0": t + 1.0, "t1": t + 3.5}, "Bence bu sunum çok iyi gidiyor."),
         m.whisper_yaz({"kanal": "ben", "t0": t + 20, "t1": t + 23}, "Eğlenceli değilse sadece bir serseri.")]
shutil.rmtree(T, ignore_errors=True)
ok = sonuc == ["yanki", "satir", "satir"]
print(("✓" if ok else "✗") + f" okunan öz atıldı, kullanıcının sözü ve zaman dışı aynı söz yazıldı · {sonuc}")
print("kendi ses: ✓ hepsi geçti" if ok else "kendi ses: ✗ kaldı")
sys.exit(0 if ok else 1)
