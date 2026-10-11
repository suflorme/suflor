#!/usr/bin/env python3
# Ölçüm kayıtlarının döndürülmesi (v0.24.2): yalıtılmış aktarıcı şişkin whisper-isler.jsonl ile açılır (sınır deneme için 200 KB). Denetim:
# açılıştan sonra döndürülür · arşiv (canli/arsiv/<ad>.gz) + aktif dosya = özgün satırlar, sırası aynı · aktif ~sınırın yarısı ve tam satırla
# başlar · sınırın altındaki dosya (izle-paketler) ve durum dosyası (kartlar) dokunulmaz · ikinci döndürme arşive ekler · olcum.py
# kayit_satirlari ikisini birlikte okur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kayit-dondur.py      (kaldı → çıkış 1)
import gzip, importlib.util, json, os, shutil, subprocess, sys, tempfile, time

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-kd-"); PORT = 8792
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
canli = os.path.join(T, "canli"); os.makedirs(canli)
def satirlar(n, bas=0): return [json.dumps({"t": 1790000000 + i, "id": f"w-karsi-{i}", "sonuc": "satir", "kuyruk": 0.1, "dolgu": "x" * 200}) + "\n" for i in range(bas, bas + n)]
ozgun = satirlar(2500)  # ~600 KB
open(os.path.join(canli, "whisper-isler.jsonl"), "w").writelines(ozgun)
open(os.path.join(canli, "izle-paketler.jsonl"), "w").writelines(satirlar(10))
open(os.path.join(canli, "kartlar.jsonl"), "w").write("x" * 300 * 1024 + "\n")
hatalar = []
def ac():
    return subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "a"),
                            stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_KAYIT_SINIR_KB="200"))
def oku_tum():
    a = os.path.join(canli, "arsiv", "whisper-isler.jsonl.gz")
    ars = gzip.open(a, "rt").readlines() if os.path.exists(a) else []
    return ars, open(os.path.join(canli, "whisper-isler.jsonl")).readlines()
r = ac()
try:
    for _ in range(100):
        time.sleep(0.2)
        if "KAYIT:" in open(os.path.join(T, "relay.log")).read(): break
    time.sleep(0.5)
    ars, akt = oku_tum()
    if not ars: hatalar.append("döndürülmedi (arşiv yok)")
    if ars + akt != ozgun: hatalar.append(f"satır kaybı/sıra: arşiv {len(ars)} + aktif {len(akt)} ≠ {len(ozgun)}")
    boy = os.path.getsize(os.path.join(canli, "whisper-isler.jsonl"))
    if not 90 * 1024 <= boy <= 110 * 1024: hatalar.append(f"aktif boyu {boy // 1024} KB (beklenen ~100)")
    try: json.loads(akt[0])
    except Exception: hatalar.append("aktif dosya yarım satırla başlıyor")
    if len(open(os.path.join(canli, "izle-paketler.jsonl")).readlines()) != 10: hatalar.append("sınır altındaki dosya değişti")
    if os.path.getsize(os.path.join(canli, "kartlar.jsonl")) != 300 * 1024 + 1: hatalar.append("durum dosyası (kartlar) değişti")
    if "döndürülemedi" in open(os.path.join(T, "relay.log")).read(): hatalar.append("günlükte döndürme hatası")
    # ikinci tur: yeni satırlar eklenir, aktarıcı yeniden açılır → arşive eklenir (gzip ardışık üye)
    r.terminate(); r.wait(5)
    ek = satirlar(1500, 2500); open(os.path.join(canli, "whisper-isler.jsonl"), "a").writelines(ek)
    open(os.path.join(T, "relay.log"), "w").close(); r = ac()
    for _ in range(100):
        time.sleep(0.2)
        if "KAYIT:" in open(os.path.join(T, "relay.log")).read(): break
    time.sleep(0.5)
    ars2, akt2 = oku_tum()
    if ars2 + akt2 != ozgun + ek: hatalar.append(f"ikinci tur satır kaybı: {len(ars2)} + {len(akt2)} ≠ {len(ozgun) + len(ek)}")
    if len(ars2) <= len(ars): hatalar.append("ikinci tur arşive eklemedi")
    # olcum.py arşiv + aktif
    sp = importlib.util.spec_from_file_location("olcum", os.path.join(KOD, ".claude", "skills", "suflor-olcum", "olcum.py")); om = importlib.util.module_from_spec(sp)
    sys.argv = ["olcum.py"]; sp.loader.exec_module(om); om.CANLI = canli
    if om.kayit_satirlari("whisper-isler.jsonl") != ozgun + ek: hatalar.append("olcum.py kayit_satirlari arşivi + aktifi birlikte okumadı")
finally:
    r.terminate(); r.wait(5)
    if not hatalar: shutil.rmtree(T, ignore_errors=True)
print("kayıt döndürme: ✓ hepsi geçti" if not hatalar else "✗ " + "\n✗ ".join(hatalar) + f"\n(deneme klasörü: {T})")
sys.exit(1 if hatalar else 0)
