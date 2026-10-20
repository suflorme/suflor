#!/usr/bin/env python3
# Gömme klasörünün sıkıştırılması (v0.97.6, gomme-isci.py sikistir): eski/geçersiz satır ≥ 2.000 ve ≥ %30 ise geçerli satırlar yeni paketlere yazılır,
# eskiler silinir; her parçanın en yeni gömmesi kalır, vektör parçaya doğru bağlı kalır. Model yüklenmez (eksik parça yok), sahte paketler.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gomme-sikistir.py      (<ortak>/cevir-venv gerekir; ~3 sn)
import glob, json, os, shutil, sqlite3, subprocess, sys, tempfile, zlib
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VPY = "/Users/Shared/Suflor/cevir-venv/bin/python"
if not os.path.exists(VPY): sys.exit("atlandı: cevir-venv yok")
T = tempfile.mkdtemp(prefix="gomme-sik-"); K = os.path.join(T, "gomme"); DB = os.path.join(T, "dizin.sqlite"); os.makedirs(K)
ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)
crc = lambda t: zlib.crc32(t.encode("utf-8", "replace"))
URET = r'''
import sys, numpy as np, zlib, json, os
K = sys.argv[1]; crc = lambda t: zlib.crc32(t.encode())
def paket(no, ids, metinler):
    E = np.array([[i // 64, i % 64] + [0] * 766 for i, m in zip(ids, metinler)], dtype=np.float16)  # ilk iki öğe parça no (float16 tam tutsun): eşleşme denetimi
    np.save(f"{K}/p{no:05d}.npy", E); np.save(f"{K}/p{no:05d}.crc.npy", np.array([crc(m) for m in metinler], dtype=np.int64)); np.save(f"{K}/p{no:05d}.id.npy", np.array(ids, dtype=np.int64))
paket(0, list(range(0, 2048)), [f"eski {i}" for i in range(2048)])            # hepsi sonra değişti → eski
paket(1, list(range(2048, 4096)), [f"metin {i}" for i in range(2048, 4096)])  # geçerli
paket(2, list(range(0, 1500)), [f"metin {i}" for i in range(0, 1500)])        # 0–1499'un yeni hâli
json.dump({"surum": 2}, open(f"{K}/durum.json", "w"))
'''
subprocess.run([VPY, "-c", URET, K], check=True)
c = sqlite3.connect(DB); c.execute("CREATE TABLE parca (id INTEGER PRIMARY KEY, yol TEXT, metin TEXT)"); c.execute("CREATE TABLE dosya (yol TEXT, baslik TEXT)")
c.executemany("INSERT INTO parca VALUES (?, 'a.md', ?)", [(i, f"metin {i}") for i in range(4096) if not (1500 <= i < 1800)]); c.commit(); c.close()  # 1500–1799 silindi
r = subprocess.run([VPY, "-B", os.path.join(KOD, "gomme-isci.py"), "--dizinle", "--db", DB, "--klasor", K, "--kosul", "0"], capture_output=True, text=True, timeout=60)
kontrol("dizinleme çalıştı, model açılmadı", r.returncode == 0 and '"eksik": 0' in r.stdout and "sıkıştırıldı" in r.stderr)
DENET = r'''
import sys, glob, numpy as np
K = sys.argv[1]; fs = sorted(glob.glob(f"{K}/p*.id.npy"))
I = np.concatenate([np.load(f) for f in fs]); E = np.vstack([np.load(f[:-7] + ".npy") for f in fs])
print(len(fs), len(I), len(set(I.tolist())), int(((E[:, 0].astype(np.int64) * 64 + E[:, 1].astype(np.int64)) == I).all()), int(1500 in set(I.tolist())), int(0 in set(I.tolist())))
'''
o = subprocess.run([VPY, "-c", DENET, K], capture_output=True, text=True).stdout.split()
kontrol(f"geçerli satırlar kaldı: 1500 + 2048 = 3548, tekrarsız ({o})", o[1:3] == ["3548", "3548"])
kontrol("vektör parçasına bağlı kaldı (ilk iki öğe = parça no)", o[3] == "1")
kontrol("silinen parça yok, değişen parçanın yeni gömmesi var", o[4] == "0" and o[5] == "1")
kontrol("eski paketler silindi (2 yeni paket)", o[0] == "2" and not os.path.exists(os.path.join(K, "p00000.npy")))
r = subprocess.run([VPY, "-B", os.path.join(KOD, "gomme-isci.py"), "--dizinle", "--db", DB, "--klasor", K, "--kosul", "0"], capture_output=True, text=True, timeout=60)
kontrol("ikinci turda sıkıştırma yok (eski satır kalmadı)", r.returncode == 0 and "sıkıştırıldı" not in r.stderr)
shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
