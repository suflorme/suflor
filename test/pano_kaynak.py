# Testlerin okuduğu pano kaynağı (mimari denetim 2, adım 4; 19 Kasım): pano.html'in betiği pano/js/NN-ad.js dosyalarında; aktarıcı (relay.py pano_js)
# onları ad sırasıyla art arda ekleyip /*__PANO_JS__*/ yerine koyar. pano_kaynak() aynısını yapar: dönen metin bölmeden önceki pano.html'in birebir aynısı
# (yazı tipi, renk, dil.js, anahtar yer tutucuları yerinde kalır). Kaynağı grep'leyen testler pano.html'i doğrudan değil bunu okur.
#   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from pano_kaynak import pano_kaynak, pano_js
import os, re
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANO_JS_AD = re.compile(r"\d\d-[a-z0-9-]+\.js")  # relay.py PANO_JS_AD ile aynı
def _oku(p): return open(p, encoding="utf-8").read()
def pano_js_dosyalari(kok=KOD):
    d = os.path.join(kok, "pano", "js")
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if PANO_JS_AD.fullmatch(f)] if os.path.isdir(d) else []
def pano_js(kok=KOD):  # sunulan betik (dosyalar sırayla; son satır sonu atılır — relay.py pano_js ile aynı)
    s = "".join(_oku(f) for f in pano_js_dosyalari(kok))
    return s[:-1] if s.endswith("\n") else s
def pano_kaynak(kok=KOD):  # pano.html + betiği yerinde
    return _oku(os.path.join(kok, "pano", "pano.html")).replace("/*__PANO_JS__*/", pano_js(kok))
