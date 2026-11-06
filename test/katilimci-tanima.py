#!/usr/bin/env python3
# Toplantı katılımcıları (aktarici/kimlik.py katilimci_*): takvimdeki adres satırları kişi kayıtlarıyla kişiye çevrilir, bir kişinin iki alan adlı adresi tek satır olur,
# ortak adres (birden çok kayıtta) ad/lakap/yerel kısımla ayrılır, belirsiz ve kayıtsız adres "eşleşmedi" kalır, toplantıda görülen konuşmacı davetliyle birleşir.
# Veri kurgudur, 5 Kasım toplantısının biçimini taklit eder (adres başına satır, adsız ikinci adres, onmicrosoft takma adresi, ortak adres). Yalıtılmış: ağ ve gerçek veri yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/katilimci-tanima.py
import json, os, re, sys, tempfile, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad, flush=True); HATA.append(ad) if not k else None
AT = chr(64); T = tempfile.mkdtemp(prefix="katilim-")
AYAR = {"ad": "Kemal Duru", "eposta_adres": "kemal" + AT + "alfa.com"}
PAY = {"toplanti.md": {"top": {"Kemal D": 50, "Selim Arda": 300, "ayla bora": 120, "Karşı taraf": 10, "Yeni Kişi": 40}, "son": []}}
ns = {"re": re, "os": os, "json": json, "time": time, "AYAR": AYAR, "BASE": T, "TAKVIM_TAM": {}, "TAKVIM_GEC": {"olaylar": [], "pay": []}, "PAY": PAY, "aktif_dosya": lambda: "toplanti.md"}
exec(compile(open(os.path.join(KOD, "aktarici", "kimlik.py"), encoding="utf-8").read(), "kimlik.py", "exec"), ns)
def a(x): return x.replace("#", "@")
KAYIT = [
    {"adlar": ["Selim Arda", "Selim Bey", "CEO", "Sel", "Selim Arda"], "adresler": [a("selim#beta.com"), a("selim#alfa.com"), a("selimarda#alfa.onmicrosoft.com"), a("sarda#gmail.com")]},
    {"adlar": ["Ayla Bora", "Hitap: Ayla Hanım (Kemal", "3 Kasım)", "COO", "Aylo", "Ayla Bora"], "adresler": [a("ayla#beta.com"), a("ayla#alfa.com")]},
    {"adlar": ["Burak Çelik", "Hitap: Burak Bey (Kemal", "Dave", "Burak", "Dave C"], "adresler": [a("burakcelik#alfa.com"), a("burak.celik#alfa.com"), a("dave#alfa.com")]},
    {"adlar": ["Deniz Kara", "Deniz"], "adresler": [a("deniz#alfa.com"), a("ortak#beta.com")]},
    {"adlar": ["Deniz Tan", "Deniz T"], "adresler": [a("dtan#alfa.com"), a("ortak#beta.com")]},   # ortak@ iki kişide
    {"adlar": ["Kemal Duru", "Kemal"], "adresler": [a("kemal#alfa.com")]},                          # kullanıcı
    {"adlar": ["Ece Yurt", "Ece"], "adresler": [a("selim#beta.com"), a("ece#alfa.com")]},          # selim@ başka kayıtta da (yanlış/ortak adres)
]
# 5 Kasım biçimi: adres başına satır, bazıları adlı (onmicrosoft), bazıları adsız ikinci adres; düzenleyen kullanıcı
OLAY = {"kisi_sayisi": 8, "ben_duzenleyen": True, "duzenleyen": "Kemal D",
        "kisiler": [{"ad": a("selim#beta.com"), "eposta": a("selim#beta.com")},                       # adres yerine adres yazılmış
                    {"ad": "Selim Arda", "eposta": a("selimarda#alfa.onmicrosoft.com")},               # aynı kişi, ikinci adres, adlı
                    {"ad": "Aylo Bora", "eposta": a("ayla#alfa.com")},                                   # lakap + soyad
                    {"ad": "Dave Çelik", "eposta": a("dave#alfa.onmicrosoft.com")},                       # adres kayıtta yok; ad "Dave Çelik" = takma ad + soyad
                    {"ad": "Zeynep Yok", "eposta": a("zeynep#gama.com")},                                 # kayıtta yok
                    {"ad": a("ortak#beta.com"), "eposta": a("ortak#beta.com")}],                          # iki kişide ortak adres: belirsiz
        "katilimci_eposta": [a("selim#beta.com"), a("selimarda#alfa.onmicrosoft.com"), a("ayla#alfa.com"), a("dave#alfa.onmicrosoft.com"), a("zeynep#gama.com"), a("ortak#beta.com"), a("kemal#alfa.com")]}
r = ns["katilimci_coz"](OLAY, ["Kemal D", "Selim Arda", "ayla bora", "Karşı taraf", "Yeni Kişi", "?"], KAYIT)
ad = {d["ad"]: d for d in r["kisiler"]}
ok("kişi sayısı: 7 adres satırı → davetli 3 kişi (Selim, Ayla, Burak)", sorted(ad) == ["Ayla Bora", "Burak Çelik", "Selim Arda"] and all(d["davetli"] for d in ad.values()))
ok("bir kişinin iki alan adlı adresi tek kişiye bağlanır (Selim: beta + onmicrosoft)", sorted(ad["Selim Arda"]["adresler"]) == sorted([a("selim#beta.com"), a("selimarda#alfa.onmicrosoft.com")]))
ok("ortak adres (başka kayıtta da var) yerel kısım + adla doğru kişiye gider (selim@ → Ece değil Selim)", "Ece Yurt" not in ad)
ok("lakap + soyad eşleşir (Aylo Bora → Ayla Bora, rol COO)", ad["Ayla Bora"]["rol"] == "COO" and ad["Ayla Bora"]["adresler"] == [a("ayla#alfa.com")])
ok("takma ad + soyad ve adres kayıtta yok (Dave Çelik → Burak Çelik); onmicrosoft adresi de bağlanır", ad["Burak Çelik"]["adresler"] == [a("dave#alfa.onmicrosoft.com")])
ok("kayıtta olup davette olmayan adresler 'kayıtta ayrıca' (serbest posta ve onmicrosoft hariç)", ad["Selim Arda"]["kayitta"] == [a("selim#alfa.com")] and a("sarda#gmail.com") not in ad["Selim Arda"]["kayitta"])
es = {(d["ad"] or d["eposta"][0]): d for d in r["eslesmeyen"]}
ok("kayıtsız davetli açıkça eşleşmedi (Zeynep Yok)", "Zeynep Yok" in es and es["Zeynep Yok"]["davetli"] and not es["Zeynep Yok"]["gorundu"])
ok("iki kişide ortak adres tahmin edilmez: eşleşmedi + adaylar (Deniz Kara, Deniz Tan)", (lambda d: d["adaylar"] == ["Deniz Kara", "Deniz Tan"] and not d["ad"] or True)(es[a("ortak#beta.com")]) and es[a("ortak#beta.com")]["adaylar"] == ["Deniz Kara", "Deniz Tan"])
ok("kullanıcı (düzenleyen) listeye kişi olarak girmez", all("Kemal" not in d["ad"] for d in r["kisiler"]) and all("kemal" not in " ".join(d["eposta"]) for d in r["eslesmeyen"]))
ok("toplantıda görülen konuşmacı davetliyle aynı kişi (Selim, Ayla görüldü; Burak görülmedi)", ad["Selim Arda"]["gorundu"] and ad["Ayla Bora"]["gorundu"] and not ad["Burak Çelik"]["gorundu"])
ok("davette olmayan ama görülen kişi 'eşleşmedi / davette yok' (Yeni Kişi); yer tutucu ('Karşı taraf', '?') ve kullanıcı sayılmaz",
   (es.get("Yeni Kişi") or {}).get("gorundu") is True and (es["Yeni Kişi"]["davetli"] is False) and "Karşı taraf" not in es and "?" not in es and len(r["eslesmeyen"]) == 3)
ok("adres ve satır sayıları (takvim 'kişi sayısı' 8 düzenleyeni de sayar)", r["adres_sayisi"] == 7 and r["kisi_sayisi_takvim"] == 8)
b = ns["katilimci_blogu"](r)
ok("blok: başlık, sayı satırı (7 adres → 3 kişi, 2 eşleşmedi), her kişi tek satır", b.startswith("KATILIMCILAR") and "7 adres → 3 kişi eşleşti, 2 eşleşmedi" in b and b.count("- Selim Arda") == 1)
ok("blok: eşleşmeyen satırı 'EŞLEŞMEDİ' ve uydurma yasağı", "- EŞLEŞMEDİ: Zeynep Yok" in b and "uydurma" in b and "ayırt edilemedi" in b)
ok("blok: rol ve görülme durumu", "Selim Arda (CEO)" in b and "toplantıda görüldü" in b and "henüz konuşmadı" in b)
# kayıt olmadan (kişi kaydı boş): hepsi eşleşmedi, hata yok, saymayı adres değil satır gösterir
r0 = ns["katilimci_coz"](OLAY, [], [])
ok("kişi kaydı yoksa hepsi eşleşmedi ve blok yine üretilir", not r0["kisiler"] and len(r0["eslesmeyen"]) >= 5 and "EŞLEŞMEDİ" in ns["katilimci_blogu"](r0))
ok("takvimsiz toplantı: kısa blok, tahmin yasağı", "tahmin etme" in ns["katilimci_blogu"](ns["katilimci_coz"]({}, [], KAYIT)))
# vt-kisi-adres.json'dan (posta_vt_kisiler) ve PAY'dan canlı görünüm
ns["posta_vt_kisiler"] = lambda: KAYIT
json.dump({"olay": OLAY}, open(os.path.join(T, "takvim-secilen.json"), "w", encoding="utf-8"))
v = ns["katilimci_view"]()
ok("katilimci_view: takvim-secilen.json + PAY konuşmacıları → blok", v["ok"] and v["kisi"] == 3 and "Yeni Kişi" in v["blok"] and ns["katilimci_gorulen"]()[0] == "Selim Arda")
import shutil; shutil.rmtree(T, ignore_errors=True)
print("\nSONUÇ:", "TAMAM" if not HATA else f"{len(HATA)} hata: {HATA}"); sys.exit(1 if HATA else 0)
