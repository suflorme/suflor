#!/usr/bin/env python3
# Dil kilidi (aktarici/whisper-hat.py DIL-KILIT bloğu + whisper-isci.py dil_kilit): kısa parça baskın dille, uzun parça serbest, kanal başına ayrı bellek,
# ayar önceliği, dil_son kirlenmez; işçi kaynağında dil_kilit oto dil algılamayı kapatır. Gerçek model yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dil-kilit.py      (kaldı → çıkış 1)
import os, sys, re
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
G = {"re": re}; exec(src.split("# DIL-KILIT-BASLA")[1].split("# DIL-KILIT-BITIS")[0], G)
bask, not_, kisa = G["dk_baskin"], G["dk_not"], G["dk_kisa"]
ok("≤2,5 sn kısa; 4 kelime kısa; uzun değil", kisa(2.5) and kisa(6, 4) and not kisa(3.0, 5))
ben, karsi = [], []
ok("geçmiş yokken ayarlı dil", bask(ben, "tr", 100) == "tr" and bask(ben, None, 100) is None)
for i in range(4): not_(karsi, "en", 5.0, 12, 100 + i)
not_(ben, "tr", 5.0, 12, 100)
ok("kanal başına ayrı: karşı en (≥3 karar), ben ayarlı tr", bask(karsi, "tr", 110) == "en" and bask(ben, "tr", 110) == "tr")
g = []; not_(g, "en", 1.0, 1, 100); not_(g, "en", 5.0, 3, 100); not_(g, "en", 2.0, 8, 100)
ok("kısa parçadaki karar belleğe girmez", g == [])
ok("120 sn sonra bellek düşer → ayar", bask(karsi, "tr", 300) == "tr")
m = []
for d in ("tr", "tr", "en", "tr"): not_(m, d, 5.0, 10, 50)
ok("çoğunluk tr → karışık ayarda da tr", bask(m, None, 60) == "tr")
for _ in range(20): not_(m, "en", 6.0, 12, 70)
ok("pencere 8 ile sınırlı, yeni çoğunluk en", len(m) == 8 and bask(m, None, 80) == "en")
# 5 Kasım biçimi: karşı kanal uzun Türkçe + kısa "en" sapmaları
c = []
for _ in range(4): not_(c, "tr", 6.0, 15, 10)
ok("kısa parça (1,3 sn) tr'ye kilitlenir", bask(c, "tr", 12) == "tr" and kisa(1.3))
# "Evet." çökmesi koruması (5 Kasım ölçümü: gerçek Evet lp 0,00 / kelime olasılığı 1,00; gülme ve anlaşılmayan ses lp ≤ -0,47 ve/veya kelime olasılığı ≤ 0,23)
ck = G["dk_cokme"]
ok("çökme: gülme (lp -0,59, kp 0,14) boşalır; gerçek Evet (lp 0, kp 1) kalır", ck("Evet.", -0.59, 0.14) and ck("Evet.", -0.47, 0.23) and ck("Evet.", -0.42, 0.24) and not ck("Evet.", -0.0, 1.0) and not ck("Evet.", -0.09, 0.97))
ok("çökme: sınırdaki gerçek Evet'ler kalır (lp -0,22…-0,28, kp 0,40…0,87)", not ck("Evet.", -0.22, 0.48) and not ck("Evet.", -0.28, 0.40) and not ck("Evet.", -0.25, 0.87))
ok("çökme: tek sözcüklük tipik değilse ya da çok sözcüklüyse dokunulmaz", not ck("Görünmüyor.", -0.9, 0.05) and not ck("Tamam. Evet.", -0.42, 0.19) and not ck("Evet, tamam.", -0.9, 0.1) and not ck("", -0.9, 0.1))
ok("çökme: tamam/hı/hmm de, noktalama ve büyük harfle", ck("Tamam!", -0.5, 0.5) and ck("Hı.", -0.1, 0.1) and ck("HMM...", -0.5, 0.9))
ok("çökme: kanıt (lp/kp) yoksa dokunulmaz", not ck("Evet.", None, None))
ok("hat: kilitli parçada çökme metni boşaltır, parçaya kilit_supheli yazar", 'is_.get("dil_kilit") and dk_cokme(' in src and 'is_["kilit_supheli"] = True' in src and '"kilit_supheli": True' in src)
isci = open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read()
ok("işçi: kilitli parçada lp ve kp döner", '"lp": round(min(' in isci and 'if p.get("dil_kilit") and tut' in isci and '"kp": min(' in isci)
ok("hat: kilit istekte dil_kilit, algılamayı kapatır", 'istek["dil_kilit"] = True' in src and 'for x_ in ("diller", "dil_yedek", "dil_algila")' in src)
ok("hat: parcalar.jsonl'a dil_kilit yazılır", '"dil_kilit": True} if istek.get("dil_kilit")' in src)
ok("hat: ayar dil_kilit:false kapatır", 'AYAR.get("dil_kilit", True) is not False' in src)
isci = open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read()
ok("işçi: dil_kilit oto dil algılamayı kapatır", re.search(r'oto = .*not p\.get\("dil_kilit"\)', isci) is not None)
sys.exit(1 if HATA else 0)
