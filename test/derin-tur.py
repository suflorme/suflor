#!/usr/bin/env python3
# Konuş derin tur (9 Kasım; aktarici/bas-konus.py konus_derin_mi/konus_derin_karar/konus_ac/gonder, aktarici/beyin.py derin_secim/konus_args effort):
# analiz/karşılaştırma/strateji sorularında o tur Opus'lu ayrı süreç; kısa/hızlı Sonnet'te; kapsam (toplantı, karşı taraf, gizli kip, sohbet) değişmez.
# Süreç/ağ/Claude yok (~1 sn):  PYTHONDONTWRITEBYTECODE=1 python3 test/derin-tur.py
import ast, importlib.util, os, re, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
sp = importlib.util.spec_from_file_location("beyin", os.path.join(KOD, "aktarici", "beyin.py")); BY = importlib.util.module_from_spec(sp); sp.loader.exec_module(BY)
agac = ast.parse(kod)
AD = {"konus_derin_mi", "konus_derin_karar", "_derin_belge_ekli"}
sec = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in AD) or (isinstance(d, ast.Assign) and any(getattr(t, "id", "").startswith("DERIN_") for t in d.targets))]
AYAR = {}; GIZLI = [False]; KAYNAK = []; SAGLAYICI = ["claude-code"]
ns = {"re": re, "AYAR": AYAR, "BEYIN": BY, "gizli_acik": lambda: GIZLI[0], "baglam_oku": lambda: list(KAYNAK), "konus_secim": lambda: {"tur": SAGLAYICI[0], "model": "sonnet"},
      "TAKVIM_UZAK_RX": re.compile(r"(?i)\b(aralık|kasım)\b"), "TAKVIM_BOS_RX": re.compile(r"(?i)müsait"), "BEKLE_TAKVIM_RX": re.compile(r"(?i)takvim|ajanda")}
exec(compile(ast.Module(sec, []), "bas-konus.py", "exec"), ns)
mi = lambda s: ns["konus_derin_mi"](s)[0]
# --- sınıflandırıcı: derin olması gerekenler
for s in ["Bu iki teklifi karşılaştır ve hangisinin bize daha uygun olduğunu söyle",
          "Yeni fiyatlandırma kararını analiz et",
          "Ekteki raporun artıları ve eksileri neler",
          "Bu pazara girme stratejimizi değerlendir, riskler neler olabilir",
          "Satışların neden düştüğünü neden-sonuç ilişkisiyle anlat",
          "Compare the two vendor proposals and tell me which one fits better",
          "Please analyze the churn numbers from last quarter",
          "What are the pros and cons of moving the launch to March?",
          "Derin düşün: ekibi ikiye bölmek mantıklı mı?",
          "Opus'la cevapla, bu sözleşmeyi nasıl okumalıyım",
          "Think hard about whether we should accept this offer"]:
    ok(f"derin: {s[:60]}", mi(s))
# --- hızlı/kısa kalması gerekenler (yanlış pozitif)
for s in ["Bugün toplantım var mı", "Ali'nin telefonu ne", "Strateji toplantısı ne zaman", "Karşılaştır", "Analiz", "Saat kaç",
          "Yarınki sunumu değerlendir", "Bu e-postaya kısaca cevap yaz, iki ürünü karşılaştır", "Hızlıca söyle, bu iki teklifi karşılaştır ve seç",
          "Briefly compare the two offers", "What time is the strategy meeting", "Kasım ayındaki strateji toplantısını değerlendirdik mi",
          "Bana bir hatırlatma ekle", "Notları özetle", "What's the weather"]:
    ok(f"hızlı kalır: {s[:60]}", not mi(s))
ok("'kısa' derse ama 'derin düşün' de derse derin (zorla kazanır)", mi("Kısaca değil, derin düşün ve karşılaştır"))
ok("uzun (≥ 300 karakter) zayıf tetikli soru derin", mi("Geçen çeyrekte ekibin yaptığı seçimleri strateji açısından düşünüyorum " + "ve bunun ardındaki gerekçeleri tek tek anlatmanı istiyorum " * 5))
ok("zayıf tetik takvim sorusunda derin değil", not mi("Aralık ayındaki toplantılarımı strateji açısından değerlendir bakalım şimdi ne var"))
# --- belge ekli
KAYNAK.append({"tur": "dosya", "ad": "kitap.pdf"})
ok("belge ekli + belgeye atıf + 'neden/sence' ≥ 6 sözcük: derin", mi("Belgedeki üçüncü bölümün yaklaşımı sence neden işe yaramıyor"))
ok("belge ekli ama sayfa/sayı sorusu (tetik yok): hızlı", not mi("Belgenin kaç sayfası var ve yazarı kim"))
GIZLI[0] = True
ok("gizli kipte belge yolu derin sayılmaz", not mi("Belgedeki üçüncü bölümün yaklaşımı sence neden işe yaramıyor"))
GIZLI[0] = False; KAYNAK.clear()
ok("belge yokken aynı cümle hızlı", not mi("Belgedeki üçüncü bölümün yaklaşımı sence neden işe yaramıyor"))
# --- kapsam kapıları (konus_derin_karar)
S = "Bu iki teklifi karşılaştır ve hangisinin bize daha uygun olduğunu söyle"
kr = lambda tur, top=False: ns["konus_derin_karar"](S, tur, top)
d = kr({"kaynak": "bas"}); ok("bas-konuş: derin, model opus, effort high varsayılan", d[0] and d[1] == "opus" and d[2] == "high" and d[3])
ok("pano kutusundan yazılı soru: derin", kr({"kaynak": "yazili", "kutu": True})[0])
ok("toplantı sürerken: değişmez (Sonnet)", not kr({"kaynak": "bas"}, True)[0])
ok("karşı taraf sorusu: değişmez", not kr({"kaynak": "karsi", "karsi": "Ali"})[0] and not kr({"kaynak": "bas", "karsi": "Ali"})[0])
ok("hitap / moderatör / özet / sohbet: değişmez", not any(kr({"kaynak": k})[0] for k in ("hitap", "moderator", "ozet", "sohbet")))
ok("otonom tur: değişmez", not kr({"kaynak": "bas", "otonom": True})[0])
GIZLI[0] = True; ok("gizli kip: değişmez", not kr({"kaynak": "bas"})[0]); GIZLI[0] = False
SAGLAYICI[0] = "openai-uyumlu"; ok("Claude Code dışı sağlayıcı: değişmez", not kr({"kaynak": "bas"})[0]); SAGLAYICI[0] = "claude-code"
AYAR["konus_derin"] = False; ok("ayar konus_derin: false kapatır", not kr({"kaynak": "bas"})[0]); AYAR.clear()
AYAR.update(konus_derin_model="fable", konus_derin_effort="xhigh"); d = kr({"kaynak": "bas"}); ok("ayar: derin model ve effort", d[1] == "fable" and d[2] == "xhigh"); AYAR.clear()
AYAR.update(konus_derin_model="op us;rm", konus_derin_effort="çok"); d = BY.derin_secim(AYAR); ok("geçersiz model/effort güvenli varsayılana düşer", d == {"model": "opus", "effort": "high"}); AYAR.clear()
# --- beyin.konus_args
a0 = BY.konus_args({}, "İSTEM", "", None, "/x/canli"); ok("derin dışı argümanlar eskisiyle aynı (model sonnet, effort yok)", a0[a0.index("--model") + 1] == "sonnet" and "--effort" not in a0)
a1 = BY.konus_args({"konus_effort": "medium"}, "İSTEM", "", None, "/x/canli", "opus", None, False, "high")
ok("derin: --model opus, --effort high (konus_effort medium'u geçer)", a1[a1.index("--model") + 1] == "opus" and a1[a1.index("--effort") + 1] == "high" and a1.count("--effort") == 1)
a2 = BY.konus_args({"konus_effort": "medium"}, "İSTEM", "", None, "/x/canli"); ok("derin dışı: ayardaki konus_effort aynen", a2[a2.index("--effort") + 1] == "medium")
# --- bağlantılar (kaynak)
ok("konus_ac derin süreci derin_secim ile açar, _KS['derin'] işaretler", 'BEYIN.derin_secim(AYAR) if _KS.get("derin_iste")' in kod and '_KS["derin"] = bool(ds)' in kod and 'ds["effort"] if ds else None' in kod)
ok("gonder: model değişince süreç yenilenir (önceki konuşma gseq=0 ile taşınır)", 'bool(_KS.get("derin")) != _KS["derin_iste"]' in kod and "konus_kapat(\"derin tur: Opus'a geçiş\"" in kod)
ok("günlük satırı KONUŞ: derin tur (<model>)", 'print(f"KONUŞ: derin tur ({dm_})' in kod)
ok("maliyet kaydında derin alanı; model alanı sürecin init modelinden (gerçek Opus adı)", '"derin": bool(tur.get("derin"))' in kod and '"model": _KS.get("model")' in kod)
ok("önceden açılan süreç Sonnet; yuva durumu derin'i taşır/sıfırlar", '_KS["derin_iste"] = False' in kod and '"gseq", "derin"' in kod and kod.count("gseq=0, derin=False") == 2)
ok("geçmiş bloğu ve belge bloğu derin turda da gider (turdan bağımsız kod yolu)", "onc = konus_gecmis_blogu(tur)" in kod and "gt += belge_baglam()" in kod)
print("derin tur: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
