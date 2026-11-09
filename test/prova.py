#!/usr/bin/env python3
# Prova odası (aktarici/prova.py): bölüm dosyası relay ad alanına benzer bir ad alanında yüklenir, model çağrısı (prova_model) sahtedir —
# gerçek Claude'a gidilmez. Akış, kişilik sınırları, tur sınırı, kayıt dosyaları, puan hesabı, rapor, belge okuma sınırı, aynı anda iki işlem.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/prova.py      (kaldı → çıkış 1)
import os, sys, re, json, time, datetime, subprocess, tempfile, threading
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = tempfile.mkdtemp(prefix="suflor-prova-"); LOCK = threading.Lock(); AYAR = {"prova_tur": 2}; ARAYUZ_DILI = "tr"
_t = lambda tr, en: en if ARAYUZ_DILI == "en" else tr
def write(pairs):
    for p, t in pairs:
        with open(p, "a", encoding="utf-8") as f: f.write(t)
src = open(os.path.join(KOD, "aktarici", "prova.py"), encoding="utf-8").read()
ns = dict(globals()); exec(compile(src, "prova.py", "exec"), ns)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
CAGRI = []; YANIT = {"davranis": None}
def sahte(istem):  # (ham, hata): istem türüne göre JSON
    CAGRI.append(istem)
    if YANIT["davranis"] == "hata": return None, "yanıt gelmedi"
    if "farklı rol öner" in istem: return '```json\n{"kisiler":[{"ad":"CFO","odak":"maliyet"},{"ad":"Hukuk","odak":"risk"},{"ad":"Müşteri","odak":"değer"}]}\n```', None
    if "Prova bitti" in istem:
        n = len(re.findall(r"^\d+\. \[", istem, re.M))
        return json.dumps({"degerlendirme": [{"no": i, "sonuc": ["ikna", "kismen", "etmedi"][i % 3], "neden": f"neden {i}"} for i in range(1, n + 1)],
                           "zayif": [{"nokta": "Maliyet belirsiz", "neden": "rakam yok"}, {"nokta": "Takvim", "neden": "kaynak yok"}], "hazirlik": [{"tur": "veri", "oneri": "Maliyet tablosu"}, {"tur": "cumle", "oneri": "Tek cümlelik değer"}], "genel": "Orta."}), None
    m = re.search(r"Rolün: ([^\s—.]+)", istem)
    return json.dumps({"soru": f"{m.group(1)} sorusu {len(CAGRI)}"}), None
ns["prova_model"] = sahte
P = ns["PROVA"]
# 1) başlamadan
bak("başlangıç durumu yok", ns["prova_view"]()["durum"] == "yok")
bak("boş konu reddedilir", "hata" in ns["prova_baslat"]("", "", None))
# 2) kişilik önerisi modelden, akış
v = ns["prova_baslat"]("Yeni fiyat modeline geçiş", "Kısa bağlam")
bak("öneriden 3 kişilik, ilk soru bekliyor", v["durum"] == "bekliyor" and [k["ad"] for k in v["kisiler"]] == ["CFO", "Hukuk", "Müşteri"] and v["siradaki"]["kisi"] == "CFO")
bak("toplam soru = tur x kişilik", v["soru_toplam"] == 6 and v["tur"] == 1)
bak("ikinci başlat reddedilir", "hata" in ns["prova_baslat"]("başka", "", None))
bak("boş cevap reddedilir", "hata" in ns["prova_cevap"]("  "))
sirali = [v["siradaki"]["kisi"]]
for i in range(6):
    v = ns["prova_cevap"](f"cevap {i + 1}")
    if v["siradaki"]: sirali.append(v["siradaki"]["kisi"])
bak("kişilikler sırayla, ikinci turda başa döner", sirali == ["CFO", "Hukuk", "Müşteri", "CFO", "Hukuk", "Müşteri"])
bak("tur sınırında tamam, yeni soru yok", v["durum"] == "tamam" and v["siradaki"] is None and len(v["gecmis"]) == 6 and v["tur"] == 2)
bak("tamamda cevap reddedilir", "hata" in ns["prova_cevap"]("fazla"))
n_once = len(CAGRI)
# 3) kişilik ekle/çıkar sınırları
bak("çıkarma 3 altına inmez", "hata" in ns["prova_kisi"]("cikar", "CFO"))
v = ns["prova_kisi"]("ekle", "Ekip lideri", "uygulanabilirlik")
bak("kişilik eklenince bitmiş tur yeniden açılır", v["durum"] == "bekliyor" and v["siradaki"]["kisi"] == "Ekip lideri" and v["soru_toplam"] == 8)
bak("aynı ad eklenmez, 5'i geçmez", "hata" in ns["prova_kisi"]("ekle", "cfo") and ns["prova_kisi"]("ekle", "Bir", "")["durum"] in ("bekliyor", "dusunuyor") and "hata" in ns["prova_kisi"]("ekle", "İki"))
v = ns["prova_cevap"]("", atla=True)
bak("atlanan cevap kaydı", v["gecmis"][-1]["cevap"] == "" or v["gecmis"][-2].get("atlandi") is True)
# 4) rapor
v = ns["prova_bitir"]()
r = v["rapor"]
bak("bitti, rapor var", v["durum"] == "bitti" and r is not None and v["rapor_md"].startswith("# Prova raporu"))
bak("puan koddan: ikna 1, kısmen 0,5, etmedi 0 (atlanan etmedi)", isinstance(r["puan"], int) and 0 <= r["puan"] <= 100 and "ikna etti" in r["puan_gerekce"])
bak("zayıf nokta tam 3 (model 2 verdi, kodla tamamlandı)", len(r["zayif"]) == 3)
bak("ikna etmeyen itirazlar ve hazırlık", len(r["ikna_etmeyen"]) >= 1 and len(r["hazirlik"]) == 2 and all(x["tur"] in ("veri", "belge", "cumle") for x in r["hazirlik"]))
bak("tekrar bitir aynı rapor, ek model çağrısı yok", (lambda c: (ns["prova_bitir"](), len(CAGRI) == c)[1])(len(CAGRI)))
# 5) puan hesabı
bak("puan: 2 ikna + 1 kısmen + 1 etmedi = 63", ns["prova_puan"]([{"sonuc": "ikna"}, {"sonuc": "ikna"}, {"sonuc": "kismen"}, {"sonuc": "etmedi"}], 4)[0] == 63)
bak("puan: cevap yoksa 0", ns["prova_puan"]([], 0)[0] == 0)
# 6) kayıt dosyaları
d = os.path.join(BASE, "prova"); dosyalar = sorted(os.listdir(d))
jl = [f for f in dosyalar if f.endswith(".jsonl")]; md = [f for f in dosyalar if f.endswith(".md")]
bak("canli/prova altında bir .jsonl ve bir .md", len(jl) == 1 and len(md) == 1 and jl[0][:-6] == md[0][:-3] and re.fullmatch(r"\d{8}-\d{6}", jl[0][:-6]))
olaylar = [json.loads(s) for s in open(os.path.join(d, jl[0]), encoding="utf-8")]
bak("jsonl: baslat, soru, cevap, kisi, rapor olayları", {o["olay"] for o in olaylar} >= {"baslat", "soru", "cevap", "kisi", "rapor"} and olaylar[0]["olay"] == "baslat" and olaylar[-1]["olay"] == "rapor")
bak("rapor .md içeriği panodakiyle aynı", open(os.path.join(d, md[0]), encoding="utf-8").read().strip() == v["rapor_md"].strip())
# 7) sıfırla, yeni prova: verilen kişilikler, tur parametresi, İngilizce, hata ve yeniden deneme
ns["prova_sifirla"]()
bak("sıfırlandı", ns["prova_view"]()["durum"] == "yok")
time.sleep(1.1)  # kayıt adı saniyeye kadar
v = ns["prova_baslat"]("Karar", "", ["CFO — maliyet", {"ad": "Hukuk", "odak": "risk"}, "Müşteri"], tur=1)
bak("verilen kişilikler ve tur=1", v["durum"] == "bekliyor" and v["soru_toplam"] == 3 and v["kisiler"][0] == {"ad": "CFO", "odak": "maliyet"})
bak("2 kişilik reddedilir", (ns["prova_sifirla"](), "hata" in ns["prova_baslat"]("k", "", ["A", "B"]))[1] and "hata" in ns["prova_baslat"]("k", "", list("ABCDEF")))
YANIT["davranis"] = "hata"
v = ns["prova_baslat"]("Karar", "", ["A", "B", "C"])
bak("model hatası: durum hata, çökmez, hata metni", v["durum"] == "hata" and v["hata"])
YANIT["davranis"] = None
v = ns["prova_yeniden"]()
bak("yeniden dene: ilk soru gelir", v["durum"] == "bekliyor" and v["siradaki"]["kisi"] == "A")
bak("cevapsız bitirilemez", "hata" in ns["prova_bitir"]())
# 8) kayıtlı olay: baglam içeriği değil uzunluk yazılır
bak("kayıtta bağlam metni yok, yalnız uzunluk", all("baglam" not in o or isinstance(o["baglam"], int) for o in olaylar) and '"baglam_uzunluk"' in open(os.path.join(d, jl[0]), encoding="utf-8").read())
ns["prova_sifirla"]()
# 9) belge okuma sınırları
ev = os.path.expanduser("~"); tmp = tempfile.mkdtemp(prefix="prova-belge-", dir=ev)
try:
    ok = os.path.join(tmp, "sunum.md"); open(ok, "w", encoding="utf-8").write("# Sunum\nFiyat artışı %0")
    sifre = os.path.join(tmp, "sifre-listesi.txt"); open(sifre, "w").write("x")
    pdf = os.path.join(tmp, "a.pdf"); open(pdf, "wb").write(b"%PDF")
    bak("belge okunur", ns["prova_belge_oku"](ok)[0].startswith("# Sunum"))
    bak("ev dışı, şifre adlı, desteklenmeyen tür reddedilir", all(ns["prova_belge_oku"](x)[1] for x in ("/etc/hosts", sifre, pdf, os.path.join(tmp, "yok.md"))))
    v = ns["prova_baslat"]("", "", None, belge=ok, proje=False)
    bak("belgeyle başlar, istemde belge metni <veri> içinde", v["durum"] == "bekliyor" and any("Fiyat artışı" in c and "<veri>" in c for c in CAGRI[-2:]))
finally:
    subprocess.run(["rm", "-rf", tmp]); ns["prova_sifirla"]()
# 10) proje özeti isteme girer (varsa), sınırlıdır
ns["proje_ozeti_istem"] = lambda: "Ö" * 5000
n0 = len(CAGRI); ns["prova_baslat"]("Konu", "", ["A", "B", "C"])
bak("proje özeti en çok 1500 karakter", any("Proje özeti" in c for c in CAGRI[n0:]) and max(len(c) for c in CAGRI[n0:]) < 5000)
ns["prova_sifirla"]()
# 11) İngilizce arayüz
ARAYUZ_DILI = "en"; v = ns["prova_baslat"]("Decision", "", None)
bak("İngilizce: varsayılan değil model önerisi; rapor başlığı İngilizce", (ns["prova_cevap"]("a"), ns["prova_bitir"]()["rapor_md"].startswith("# Rehearsal report"))[1])
ARAYUZ_DILI = "tr"; ns["prova_sifirla"]()
# 12) aynı anda iki işlem: ikincisi reddedilir
bekle = threading.Event(); orijinal = ns["prova_model"]
def yavas(i): bekle.wait(3); return orijinal(i)
ns["prova_model"] = yavas; sonuc = []
t = threading.Thread(target=lambda: sonuc.append(ns["prova_baslat"]("Konu", "", ["A", "B", "C"]))); t.start(); time.sleep(0.3)
bak("düşünürken ikinci başlat ve cevap reddedilir", "hata" in ns["prova_baslat"]("x", "", None) and "hata" in ns["prova_cevap"]("x") and ns["prova_view"]()["durum"] == "dusunuyor")
bekle.set(); t.join(); bak("ilk işlem tamamlandı", sonuc and sonuc[0]["durum"] == "bekliyor")
ns["prova_model"] = orijinal
# 13) HTTP işleyici (prova_islem) ve bilinmeyen işlem
ns["prova_sifirla"]()
bak("prova_islem: oner / baslat / cevap / bitir", len(ns["prova_islem"]({"islem": "oner", "konu": "k"})["kisiler"]) == 3 and ns["prova_islem"]({"islem": "baslat", "konu": "k", "kisiler": ["A", "B", "C"], "proje": False, "tur": 1})["durum"] == "bekliyor"
    and ns["prova_islem"]({"islem": "cevap", "metin": "c"})["durum"] == "bekliyor" and ns["prova_islem"]({"islem": "bitir"})["durum"] == "bitti")
bak("bilinmeyen işlem hata verir", "hata" in ns["prova_islem"]({"islem": "x"}) and "hata" in ns["prova_islem"](None))
# 12) bağlam denetimi (10 Kasım): rol önerisi ve rapor isteminin başında kişi modeli paketi + (konuyla örtüşen takvim toplantısının) katılımcı bloğu
PK = []; GZ = {"a": False}
ns["baglam_paketi"] = lambda amac, **k: (PK.append((amac, k)), "[PAKET-" + amac + "]\n")[1]; ns["gizli_acik"] = lambda: GZ["a"]
ns["_km_sar"] = lambda ad, govde, ac="", cap=None: f"[{ad}]\n{govde}\n[/{ad}]\n"; ns["_t"] = _t
ns["katilimci_view"] = lambda olay=None, gorulen=None: {"blok": "KATILIMCILAR: Aylin Örnek (davetli)", "kisi": 1, "eslesmeyen": 0}
json.dump({"olay": {"baslik": "Fiyat modeli toplantısı", "katilimcilar": ["Aylin Örnek"]}}, open(os.path.join(BASE, "takvim-secilen.json"), "w"))
ns["PROVA"].clear(); ns["PROVA"]["durum"] = "yok"; CAGRI.clear(); PK.clear(); ns["prova_oner"]("Yeni fiyat modeline geçiş kararı", "")
bak("rol önerisi: paket (brifing amacı, soru = konu) + konuyla örtüşen toplantının katılımcı bloğu isteme girdi", CAGRI[0].startswith("[PAKET-brifing]") and PK[0][0] == "brifing" and PK[0][1]["soru"] == "Yeni fiyat modeline geçiş kararı" and "Aylin Örnek" in CAGRI[0] and PK[0][1]["en_cok_kr"] == ns["PROVA_PAKET_KR"])
CAGRI.clear(); ns["prova_oner"]("Bambaşka konu: ofis taşınması", ""); bak("konu takvim toplantısıyla örtüşmüyorsa katılımcı bloğu girmez, paket yine gelir", CAGRI[0].startswith("[PAKET-brifing]") and "Aylin Örnek" not in CAGRI[0])
GZ["a"] = True; CAGRI.clear(); ns["prova_oner"]("Yeni fiyat modeline geçiş kararı", ""); bak("gizli kipte katılımcı bloğu hiç girmez (paket süzgeci baglam_paketi'nde)", "Aylin Örnek" not in CAGRI[0]); GZ["a"] = False
ns["prova_sifirla"](); v = ns["prova_baslat"]("Yeni fiyat modeline geçiş", "Kısa bağlam", ["CFO", "Hukuk", "Müşteri"]); ns["prova_cevap"]("c1"); ns["prova_cevap"]("c2"); ns["prova_cevap"]("c3")
CAGRI.clear(); PK.clear(); ns["prova_bitir"]()
bak("rapor: paket başa eklenir, soru = prova konusu", CAGRI and CAGRI[-1].startswith("[PAKET-brifing]") and "Prova bitti" in CAGRI[-1] and PK and PK[-1][1]["soru"] == "Yeni fiyat modeline geçiş")
ns["prova_sifirla"]()
print("\n" + (f"{len(hata)} test kaldı" if hata else "hepsi geçti")); sys.exit(1 if hata else 0)
