#!/usr/bin/env python3
# Sihirbazın proje taraması (kurulum.py hz_tara/hz_ozet): tarama sürerken gelen istek (klasör yongası, "Dizine al") yok sayılmaz — bekleyen
# işaretlenir, süren tarama bitince sonraki özet yoklaması yeni ayarla bir kez daha tarar (21 Ekim: test49'da ekran eski sayıda kalıyordu).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/hazirlik-tara.py      (kaldı → çıkış 1; < 1 sn)
import importlib.util, os, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("kurulum_deneme", os.path.join(KOD, "kurulum.py")); K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
class Surec:  # sahte arka plan taraması: bitti mi elle
    def __init__(s): s.bitti = False
    def poll(s): return 0 if s.bitti else None
baslayan = []
def arka(*a): p = Surec(); baslayan.append(p); return p
K._hz_arka = arka; K._hz = lambda komut, *a, **k: {"tarama": {"dosya": 5}}
K.HZ.clear(); K.HZ["tara"] = None
K.hz_tara(); bak("ilk istek taramayı başlatır", len(baslayan) == 1)
K.hz_tara(); bak("tarama sürerken ikinci istek yeni süreç açmaz", len(baslayan) == 1 and K.HZ.get("tara_bekleyen"))
o = K.hz_ozet(); bak("süren taramada özet 'sürüyor' der", o["tara_suruyor"] is True and len(baslayan) == 1)
baslayan[0].bitti = True
o = K.hz_ozet(); bak("bitince bekleyen istek yeni taramayı başlatır, özet hâlâ 'sürüyor'", len(baslayan) == 2 and o["tara_suruyor"] is True and not K.HZ.get("tara_bekleyen"))
baslayan[1].bitti = True
o = K.hz_ozet(); bak("bekleyen yokken yeni tarama açılmaz, özet 'bitti'", len(baslayan) == 2 and o["tara_suruyor"] is False)
print(("KALDI: " + ", ".join(hata)) if hata else "GEÇTİ")
sys.exit(1 if hata else 0)
