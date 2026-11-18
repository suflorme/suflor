#!/usr/bin/env python3
# Regresyon (18 Kasım 2026): ag_obek, tanınmayan bir aday (sinif None) bitince TypeError verdi — _ag_say({...}.get(sinif, sinif + "_bitti")) varsayılanı her zaman hesaplıyordu.
# Modelsiz, sabit port yok (bos_port; relay yalnız modül olarak yüklenir, sunucu başlamaz). Silero/Whisper/tstt sahte.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/araya-girme-ilk.py
import importlib.util as u, json, os, shutil, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
PORT = bos_port(8782); T = tempfile.mkdtemp(prefix="suflor-agilk-")
for f in ("relay.py", "manifest.json", "whisper-isci.py", "vad-isci.py", "tstt-golge-isci.py", "tur-isci.py", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "gelistirici": True, "yerel_araya_girme": "dur", "yerel_araya_tstt": False},
          open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json")
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)]; os.chdir(T)
sp = u.spec_from_file_location("relay_agilk", os.path.join(T, "relay.py")); m = u.module_from_spec(sp); sp.loader.exec_module(m)
# 1) sayaç adı: her sınıf için metin döner (None dahil)
for k in (None, "on", "bos", "baska", "onay", "dur", "yanki"):
    try: ad = m._ag_bitis_adi(k); ok(f"_ag_bitis_adi({k!r}) → {ad!r}", isinstance(ad, str) and ad)
    except Exception as e: ok(f"_ag_bitis_adi({k!r}) hata verdi: {e!r}", False)
# 2) ilk okuma durumu: SES["simdi"] boş, ARAYA taze; sahte VAD ile bir söz başlar ve biter, aday tanınmadan kapanır → ag_obek istisnasız False
m.AYAR["yerel_araya_girme"] = "dur"; m.SOHBET.update(acik=True, yerel=True, hoparlor=False, t_okuma=time.time())
with m.SES_K: m.SES["simdi"] = None
m.ag_etkin = lambda: True; m._okuma_izle = lambda simdi: True; m.vad_sifirla = lambda: True; m._agt_besle = lambda *a, **k: None
m._ag_whisper = lambda aday, pcm: None   # Whisper iş parçacığı model yüklemesin
olaylar = [[{"o": "basla", "t": 0}], [], [{"o": "bitti", "t": 1500}]] + [[]] * 3
sira = iter(olaylar); m.vad_olasilik = lambda pcm, **k: {"olay": next(sira, []), "konusma": False}
m.AG_ADAY_SN = 0.1; m.AG_TANI_SN = 99.0
pcm = b"\x01\x00" * 1600; hata = None; sonuc = []
try:
    for i in range(6): sonuc.append(m.ag_obek(pcm, time.time() + i * 0.1))
except Exception as e: hata = e
ok(f"ilk okumada tanınmayan aday ag_obek'i düşürmez ({hata!r})" if hata else "ilk okumada tanınmayan aday ag_obek'i düşürmez", hata is None)
ok("tanınmayan aday öbeği araya girme saymaz (hepsi False)", hata is None and not any(sonuc))
ok("taninmadi sayacı arttı", m.ARAYA["say"].get("taninmadi", 0) >= 1)
print("HATA:", HATA) if HATA else print("tamam")
sys.exit(1 if HATA else 0)
