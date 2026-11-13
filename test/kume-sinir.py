#!/usr/bin/env python3
# Canlı karşı kanal kümeleme sınırı (whisper-isci.py kumele, v0.242.2): yeni küme yalnız ≥ 2,5 sn parçayla açılır; 6 küme doluyken
# yeni ses gelirse en eski tek parçalı küme emekliye ayrılır, yeni küme sona eklenir (kN adı yeniden kullanılmaz); tek parçalı küme
# yoksa kümesiz kalır. 13 Kasım toplantısı: dört kısa gürültü kümesi sınırı doldurdu, üçüncü kişi kümesiz kaldı.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kume-sinir.py      (kaldı → çıkış 1; numpy yoksa whisper-venv Python'uyla kendini yeniden açar)
import os, re, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try: import numpy as np
except ImportError:
    py = "/Users/Shared/Suflor/whisper-venv/bin/python"
    if os.path.exists(py) and not os.environ.get("KS_ICERDE"): os.environ["KS_ICERDE"] = "1"; os.execv(py, [py, "-B", __file__])
    print("kume-sinir: numpy yok, atlandı"); sys.exit(0)
kod = open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read(); ns = {"SR": 16000}
for ad in ("KUME_ESIK", "KUME_YENI_SN"): exec(re.search(r"^" + ad + r"\b.*$", kod, re.M).group(0), ns)
exec(re.search(r"^def kumele\(.*?(?=^\S)", kod, re.M | re.S).group(0), ns)
rng = np.random.default_rng(5); taban = [v / np.linalg.norm(v) for v in rng.normal(size=(12, 192))]
def ses(i, g=0.05): v = taban[i] + rng.normal(scale=g, size=192); return v / np.linalg.norm(v)
def km(ks, i, sn): e = ses(i); return ns["kumele"](lambda _: e, ks, np.zeros(int(sn * 16000)), np, e)["kume"]
hata = []
def bak(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(ad) if not k else None
ks = []
bak("2 sn'lik ilk ses küme açmaz", km(ks, 0, 2.0) is None and not ks)
bak("3 sn'lik ses k1 açar", km(ks, 0, 3.0) == "k1")
bak("aynı kişi kısa parçada da k1", km(ks, 0, 1.0) == "k1")
for i in range(1, 6): km(ks, i, 3.0)
km(ks, 0, 3.0); km(ks, 1, 3.0); km(ks, 2, 3.0); km(ks, 3, 3.0); km(ks, 4, 3.0); km(ks, 5, 3.0)  # k1–k6 iki parçalı
bak("6 küme dolu", len(ks) == 6)
bak("hepsi çok parçalıyken yeni kişi kümesiz", km(ks, 6, 4.0) is None)
ks2 = []
km(ks2, 0, 3.0); km(ks2, 0, 3.0)
for i in range(1, 6): km(ks2, i, 3.0)  # k2–k6 tek parçalı gürültü
bak("doluyken yeni kişi k7 alır (k2 emekli)", km(ks2, 6, 4.0) == "k7" and ks2[1][1] == 0)
bak("yeni kişi sonra da k7", km(ks2, 6, 3.0) == "k7")
bak("emekli kümenin sesi artık k2 değil", km(ks2, 1, 3.0) != "k2")
bak("k1 (çok parçalı) korunur", km(ks2, 0, 3.0) == "k1")
print("küme sınırı: ✓ hepsi geçti" if not hata else f"küme sınırı: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
