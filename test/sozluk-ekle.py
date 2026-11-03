#!/usr/bin/env python3
# Sözlük komutunun regresyon testi (toplanti-claude.py sozluk --ekle / --birlestir): proje kartından gelen terimler
# (kaynak proje-karti, yanlış yazımı boş; yalnız Whisper istemine girer) ekleme ve yeniden kurmada silinmemeli —
# 22 Ekim'de bir --ekle canlı sözlükten 46 terimi götürdü. Geçici klasörde çalışır; gerçek ayar ve _canli'ye dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sozluk-ekle.py      (kaldı → çıkış 1)
import json, os, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-sozluk-")
proje, canli = os.path.join(T, "proje"), os.path.join(T, "canli")
os.makedirs(os.path.join(proje, "sozluk")); os.makedirs(canli)
open(os.path.join(proje, "sozluk", "duzeltme_sozlugu_oneri.tsv"), "w", encoding="utf-8").write(
    "uygulama\tdogru_bicim\thatali_bicimler\ndogrudan\tPazaryeri Pro\tpazar yeri pro|pazaryer pro\n")
open(os.path.join(proje, "sozluk", "kaynak.xlsx"), "wb").write(b"")  # okunamaz: vendor listesi boş kalır
AYAR = {"alan": "Test", "ad": "Deneme Kullanici", "port": 8790, "uygulama": os.path.join(T, "uyg"), "proje": proje,
        "ortak": os.path.join(T, "ortak"), "yerel_ses": False, "teshis": False, "dil": "tr",
        "sozluk_kaynagi": "sozluk", "sozluk_xlsx": "kaynak.xlsx"}
json.dump(AYAR, open(os.path.join(T, "ayar.json"), "w"), ensure_ascii=False)
ENV = dict(os.environ, SUFLOR_AYAR=os.path.join(T, "ayar.json"), PYTHONDONTWRITEBYTECODE="1")
FP = os.path.join(canli, "sozluk.json")
json.dump({"surum": 2, "terimler": [
    {"dogru": "Pazaryeri Pro", "yanlis": ["pazar yeri pro"], "kip": "duzelt", "baglam": [], "kaynak": "otomatik"},
    {"dogru": "Yankıhat", "yanlis": ["yangı hat"], "kip": "duzelt", "baglam": [], "kaynak": "otomatik"},
    {"dogru": "Kasaburç", "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti", "not": "kasa"},
    {"dogru": "StokKöprü", "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti", "not": ""},
    {"dogru": "Sonnet", "yanlis": ["Soneme"], "kip": "duzelt", "baglam": [], "kaynak": "kullanici"},
    {"dogru": "Pazaryeri Pro", "yanlis": ["pazaryer pro"], "kip": "duzelt", "baglam": [], "kaynak": "ogrenme-20261103", "aday": "a1b2c3d4"},  # 3 Kasım: öğrenen sözlük
    {"dogru": "Dravento", "yanlis": ["Drawento"], "kip": "baglam", "baglam": ["siparis"], "kaynak": "ogrenme-20261102", "aday": "a5e6f7a8"},
    {"dogru": "Zelmora", "yanlis": ["zelmora x"], "kip": "duzelt", "baglam": [], "kaynak": "sozluk-genisletme-20261103"},  # 3 Kasım: birleştirmenin üretmediği kaynak da korunur
    {"dogru": "Sonnet", "yanlis": ["Soneme", "Sonet"], "kip": "duzelt", "baglam": [], "kaynak": "sozluk-genisletme-20261103"}]}, open(FP, "w"), ensure_ascii=False)

kalan = 0
def sozluk(*arg):
    r = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "sozluk", *arg], env=ENV, capture_output=True, text=True, timeout=60)
    if r.returncode: print(r.stdout[-400:], r.stderr[-800:])
    return json.load(open(FP, encoding="utf-8"))["terimler"]
def bak(ad, kosul):
    global kalan
    print(("✓ " if kosul else "✗ ") + ad); kalan += not kosul
def dogrular(ts, kaynak=None): return sorted(t["dogru"] for t in ts if kaynak is None or t.get("kaynak") == kaynak)

ts = sozluk("--ekle", "yangı hat", "Yankıhat")  # kullanıcının biçimi otomatik terimden düşer → otomatik Yankıhat boşalır, kalkar
bak("--ekle proje kartı terimlerini korur", dogrular(ts, "proje-karti") == ["Kasaburç", "StokKöprü"])
bak("--ekle kullanıcının eklediği terim yerinde", any(t["dogru"] == "Yankıhat" and t.get("kaynak") == "kullanici" for t in ts))
bak("--ekle biçimi kullanıcıya geçen otomatik terim kalkar", not any(t["dogru"] == "Yankıhat" and t.get("kaynak") == "otomatik" for t in ts))
bak("--ekle başka otomatik terim yerinde", "Pazaryeri Pro" in dogrular(ts, "otomatik"))
ts = sozluk("--birlestir")
bak("--birlestir proje kartı terimlerini korur", dogrular(ts, "proje-karti") == ["Kasaburç", "StokKöprü"])
bak("--birlestir kullanıcı terimleri yerinde", {"Yankıhat", "Sonnet"} <= set(dogrular(ts, "kullanici")))
bak("--birlestir dış sözlükten otomatik terim kurar", "Pazaryeri Pro" in dogrular(ts, "otomatik"))
bak("--birlestir kaynaktan kalkan otomatik terim kalkar", "Yankıhat" not in dogrular(ts, "otomatik"))
bak("proje kartı terimi tek kez", len([t for t in ts if t["dogru"] == "Kasaburç"]) == 1)
og = [t for t in ts if str(t.get("kaynak", "")).startswith("ogrenme-")]
bak("--birlestir öğrenilen kuralları korur (kaynak, aday, kip, bağlam)", sorted((t["dogru"], t["aday"], t["kip"]) for t in og) == [("Dravento", "a5e6f7a8", "baglam"), ("Pazaryeri Pro", "a1b2c3d4", "duzelt")]
    and next(t for t in og if t["dogru"] == "Dravento")["baglam"] == ["siparis"])
bak("--birlestir: öğrenilen biçim otomatik terimde yinelenmez", not any("pazaryer pro" in t["yanlis"] for t in ts if t.get("kaynak") == "otomatik"))
gen = [t for t in ts if str(t.get("kaynak", "")).startswith("sozluk-genisletme-")]
bak("--birlestir birleştirmenin üretmediği kaynağı (sozluk-genisletme-*) korur", any(t["dogru"] == "Zelmora" and t["yanlis"] == ["zelmora x"] for t in gen) and len(gen) == 2)
bak("--birlestir: elle eklenenle çakışan biçim elle'de kalır, öteki biçim korunur, elle terimin kipi bozulmaz",
    next(t for t in gen if t["dogru"] == "Sonnet")["yanlis"] == ["Sonet"] and next(t for t in ts if t.get("kaynak") == "kullanici" and t["dogru"] == "Sonnet")["yanlis"] == ["Soneme"])
bak("--birlestir ikinci kez: terim sayısı değişmez (yinelenmez)", len(sozluk("--birlestir")) == len(ts))
print("GEÇTİ" if not kalan else f"KALDI: {kalan}")
sys.exit(1 if kalan else 0)
