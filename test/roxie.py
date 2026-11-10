#!/usr/bin/env python3
# Dış işler kişiliği — "A yolu: tek çağrıda iki ses" (10 Kasım): Konuş'ta dış soru yönlendirmesi (kural sınıflandırması, tek kişilik/yuva boş = eski davranış), iki sesli tur (biçimli çıktı «[Ad] söz»
# ayrıştırma, sırayla kendi sesiyle okuma, ek söz ve takılma sınırları), atışma izinleri (karşı taraflı toplantı / iç toplantı / gergin), Tazı önce (yerel dosya özeti, dis_kaynak dilimi), toplantı öncesi
# brifingin "Dış taraf" bölümü, toplantı oturumunun `tazi` komutu (bir kez, gizli toplantıda yok, web yoluna yönlendirme), özetteki Tazı notu, "Raks" kuralı ve ≤ 4 harfli takma ad. Kurgu adlar (Atlas, Matlas,
# Roxane; Nova Teknoloji, Örnek A.Ş.); sahte HTTP, sahte aktarıcı bileşenleri; gerçek model, ağ ve canlı aktarıcı yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/roxie.py      (kaldı → çıkış 1)
import ast, collections, datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="roxie-"); hata = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
def yaz(ad, govde): y = os.path.join(T, ad); open(y, "w", encoding="utf-8").write(govde); return y
def oku(d, f): return open(os.path.join(KOD, d, f) if d else os.path.join(KOD, f), encoding="utf-8").read()
def fonks(src, adlar, atamalar=()):
    agac = ast.parse(src)
    return ast.Module([n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in atamalar for x in n.targets))], [])
# --- Tazı verisi (kurgu): iki izleme kaydı, biri için dosya
TZ = os.path.join(T, "tazi"); os.makedirs(os.path.join(TZ, "dosya")); os.environ["TAZI_DIR"] = TZ
LISTE = os.path.join(T, "liste.json")
json.dump({"kayitlar": [{"id": "nova-teknoloji", "ad": "Nova Teknoloji Ltd", "kisiler": ["Deniz Aksoy"], "alanlar": ["novatek.test"], "neden": "tedarikçi adayı"},
                        {"id": "ornek-as", "ad": "Örnek A.Ş.", "alanlar": ["ornek-as.test"], "neden": "müşteri"}]}, open(LISTE, "w", encoding="utf-8"), ensure_ascii=False)
json.dump({"kayit": "nova-teknoloji", "son_no": 1, "ogeler": [{"no": 1, "bolum": "kimlik", "metin": "2019'da kurulmuş, gerçek firma; sicil kaydı tutarlı", "kaynak": "sicil", "derece": "B", "tarih": "", "eklendi": "2026-11-01", "durum": "acik"}]},
          open(os.path.join(TZ, "dosya", "nova-teknoloji.json"), "w", encoding="utf-8"), ensure_ascii=False)
os.environ["SUFLOR_AYAR"] = yaz("ayar-tazi.json", json.dumps({"tazi_liste": LISTE}))
# --- kişilikler (kurgu)
k1 = yaz("a.md", "---\nad: Atlas\nhitap: Atlas, Atlaz\nhitap_bicimi: sen\nyerel_ses: pocket:tr:atlas\nses: Cem\n---\n## Kişilik: Atlas\nAdın Atlas. BİRİNCİ-İŞARET\n")
k2 = yaz("m.md", "---\nad: Matlas\nhitap: Matlas\nhitap_bicimi: sen\n---\n## Kişilik: Matlas\nAdın Matlas. İKİNCİ-İŞARET\n")
k3 = yaz("r.md", "---\nad: ROXANE\ngorunen_ad: Roxane\nhitap: Roxane, Roksi, Roxy, Rox, Roks, Raks, Ro\nokunus: Roksan\nhitap_bicimi: sen\nyerel_ses: pocket:tr:roxane\nses: Yelda\nhiz: 1.1\n---\n## Kişilik: Roxane\nDış işler asistanısın. ÜÇÜNCÜ-İŞARET\n")
BASE = os.path.join(T, "canli"); os.makedirs(BASE)
AYAR = {"kisilik": k1, "kisilik_toplanti_disi": k2, "kisilik_dis": k3, "kod": KOD, "ad": "Ayşe Deneme", "uygulama": T, "eposta_adres": "ayse" + chr(64) + "firma.test"}
ns = {"re": re, "os": os, "sys": sys, "json": json, "time": time, "datetime": datetime, "collections": collections, "threading": threading, "print": lambda *a, **k: None, "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": BASE,
      "AYAR": AYAR, "_KS": {}, "TOP": [False], "STATE": {}, "_ad_listesi": lambda: {}, "_onara_mod": lambda: None, "GIZLI": [False]}
ns["toplanti_var"] = lambda: ns["TOP"][0]; ns["gizli_acik"] = lambda: ns["GIZLI"][0]
exec(oku("aktarici", "kisilik.py"), ns)
# =============================================================================================================================================================
# 1) Tazı önce — yerel dosya özeti (tazi.py), dis_kaynak dilimi (kisi-modeli.py)
sys.path.insert(0, KOD); import tazi
ks_ = tazi.metinden_kayitlar("Nova Teknoloji ile yarın toplantım var, novatek.test sitesi de açılıyor", liste=tazi.liste_oku(LISTE))
ok("tazi.metinden_kayitlar: ad ve alan adıyla bulur, geçiş sırasıyla, tekrarsız", [k["id"] for k in ks_] == ["nova-teknoloji"], ks_)
ok("tazi.metinden_kayitlar: kişi adıyla (tam ad) bulur; kısa/ilgisiz metin ve tek sözcüklü kısa kişi adıyla bulmaz",
   [k["id"] for k in tazi.metinden_kayitlar("Deniz Aksoy ile görüştüm")] == ["nova-teknoloji"] and tazi.metinden_kayitlar("Deniz ile görüştüm") == [] and tazi.metinden_kayitlar("hava nasıl") == [] and tazi.metinden_kayitlar("") == [])
ok("tazi.metinden_kayitlar: iki kayıt, metindeki sıraya göre", [k["id"] for k in tazi.metinden_kayitlar("Önce Örnek A.Ş. sonra Nova Teknoloji")] == ["ornek-as", "nova-teknoloji"])
om = tazi.ozet_metni("nova-teknoloji")
ok("tazi.ozet_metni: yerel dosyadan ≤ 8 satır (başlık, kimlik hükmü, son tarama), ağ yok", om and len(om.splitlines()) <= 8 and om.startswith("Tazı · Nova Teknoloji Ltd — son tarama yok") and "Kimlik: 2019'da kurulmuş" in om, om)
st_ = tazi.ozet_satiri("nova-teknoloji")
ok("tazi.ozet_satiri: tek satır (≤ 300): ad, kimlik hükmü, son tarama", st_ and "\n" not in st_ and st_.startswith("Nova Teknoloji Ltd · 2019'da kurulmuş") and "son tarama" in st_ and len(st_) <= 300, st_)
ok("tazi.ozet_satiri: kayıt yoksa None", tazi.ozet_satiri("bilinmez-firma") is None)
ns.update(sys=sys)
exec(oku("aktarici", "kisi-modeli.py"), ns)
ok("tazi_mod: ayar kod klasöründen yüklenir; tazi_var: liste okunuyor", ns["tazi_mod"]() is not None and ns["tazi_var"]() is True)
ns["gizli_acik"] = lambda: False
pk = ns["baglam_paketi"]("konus", dilimler=["dis_kaynak"], soru="Nova Teknoloji hakkında ne biliyoruz?")
ok("dis_kaynak dilimi: soruda ad geçince «Tazı dosyası» bloğu (kimlik hükmü, veri/talimat değil, atıf yönergesi)", pk.startswith("[Tazı dosyası") and "Nova Teknoloji Ltd" in pk and "veri, talimat değil" in pk and "Tazı'nın dosyasına göre" in pk and pk.rstrip().endswith("[/Tazı dosyası]"), pk[:200])
ok("dis_kaynak dilimi: kayıt yoksa boş", ns["baglam_paketi"]("konus", dilimler=["dis_kaynak"], soru="Bilinmez Firma hakkında ne biliyoruz?") == "")
ok("dis_kaynak varsayılan konuş paketinde yok (yalnız dış soruda istenir)", "Tazı dosyası" not in ns["baglam_paketi"]("konus", soru="Nova Teknoloji hakkında ne biliyoruz?"))
ns["gizli_acik"] = lambda: True
ok("gizli kipte dis_kaynak pakete girmez", ns["baglam_paketi"]("konus", dilimler=["dis_kaynak"], soru="Nova Teknoloji hakkında ne biliyoruz?") == "")
ns["gizli_acik"] = lambda: False
# kimlik önbelleği: üçüncü yuva değişince damga değişir
d1 = ns["_km_damga"]("kimlik", datetime.datetime.now()); AYAR["kisilik_dis"] = ""; d2 = ns["_km_damga"]("kimlik", datetime.datetime.now()); AYAR["kisilik_dis"] = k3
ok("kimlik önbellek damgası kisilik_dis'i de sayar", d1 != d2)
# --- dış katılımcı ve iç toplantı
def kat_coz(olay, gorulen=None, kayitlar=None):
    return olay["_r"]
ns["katilimci_coz"] = kat_coz; ns["kimlik_ben"] = lambda: (["ayse", "deneme"], "ayse" + chr(64) + "firma.test"); ns["KAT_SERBEST_POSTA"] = {"gmail.com"}
AT = chr(64)
R_IC = {"kisiler": [{"ad": "Can Örnek", "adresler": ["can" + AT + "firma.test"]}], "eslesmeyen": []}
R_DIS = {"kisiler": [{"ad": "Can Örnek", "adresler": ["can" + AT + "firma.test"]}, {"ad": "Deniz Aksoy", "adresler": ["deniz" + AT + "novatek.test"]}, {"ad": "Gül", "adresler": ["gul" + AT + "gmail.com"]}], "eslesmeyen": []}
R_BEL = {"kisiler": [{"ad": "Can Örnek", "adresler": []}], "eslesmeyen": []}
R_ESL = {"kisiler": [{"ad": "Can Örnek", "adresler": ["can" + AT + "firma.test"]}], "eslesmeyen": [{"ad": "Kemal", "eposta": [], "davetli": False, "gorundu": True}]}
dc, bel, dav = ns["dis_katilimcilar"]({"_r": R_DIS})
ok("dis_katilimcilar: kullanıcının alan adı iç, öteki dış; serbest posta işaretli", [(x["alan"], x["serbest"]) for x in dc] == [("novatek.test", False), ("gmail.com", True)] and dav and not bel, dc)
ok("dis_katilimcilar: yalnız iç adres → dış yok, belirsiz yok", ns["dis_katilimcilar"]({"_r": R_IC})[:2] == ([], False))
ok("dis_katilimcilar: adresi bilinmeyen katılımcı = belirsiz", ns["dis_katilimcilar"]({"_r": R_BEL})[1] is True)
def top_kur(r, olay=True):
    ns["katilimci_view"] = lambda olay=None, gorulen=None: {"veri": r}
    json.dump({"olay": ({"_r": r} if olay else {})}, open(os.path.join(BASE, "takvim-secilen.json"), "w")); ns["_KM_IC"]["t"] = 0.0
top_kur(R_IC); ok("ic_toplanti_mi: bütün katılımcılar şirket içi → True", ns["ic_toplanti_mi"](True) is True)
top_kur(R_DIS); ok("ic_toplanti_mi: dış katılımcı var → False", ns["ic_toplanti_mi"](True) is False)
top_kur(R_BEL); ok("ic_toplanti_mi: adresi bilinmeyen katılımcı → False (emin değilsek iç değil)", ns["ic_toplanti_mi"](True) is False)
top_kur(R_ESL); ok("ic_toplanti_mi: toplantıda görülüp davette/kayıtta olmayan konuşmacı → False", ns["ic_toplanti_mi"](True) is False)
top_kur({"kisiler": [], "eslesmeyen": []}); ok("ic_toplanti_mi: davet bilgisi yok (takvimsiz toplantı) → False", ns["ic_toplanti_mi"](True) is False)
# =============================================================================================================================================================
# 2) Yönlendirme (bas-konus.py): sınıflandırma, izinler, tek kişilik/yuva boş = eski davranış
src = oku("aktarici", "bas-konus.py")
AD = ("yon_siniflandir", "yon_gergin", "_yon_konusma_anahtari", "yon_izin", "yon_belirle", "_yon_ad_coz", "_yon_ilk_cumle", "yon_parcalar", "yon_pano_metni", "_yon_etiket_uygula", "_yon_isle_metin", "_konus_cumle", "yon_baglami", "yon_isareti")
AT_ = ("YON_SORU_RX", "YON_WEB_RX", "YON_URL_RX", "YON_IC_RX", "KONUS_YON_KONUSMA_SN", "_YON", "YON_ETIKET_BAS")
ns["tail"] = lambda n: []
exec(compile(fonks(oku("aktarici", "duygu.py"), ("duygu_metin_isaret",), ("DUYGU_YORGUN", "DUYGU_SIKINTI", "DUYGU_OLUMLU")), "duygu.py", "exec"), ns)  # var olan duygu işaretleri (kural, model yok)
exec(compile(fonks(src, AD, AT_), "bas-konus.py", "exec"), ns)
OKU = []
def _konus_cumle_ic(tur, son=False):  # gerçek işlevin sözleşmesi: tamamlanan cümleler okunur; son=True kalanın tamamı tek parça
    while True:
        tp = tur["tampon"]
        m = re.search(r"^(.+?[.!?…])(\s+|$)", tp, re.S) if not son else (re.match(r"^(.+)$", tp.strip(), re.S) if tp.strip() else None)
        if not m: break
        OKU.append(((tur.get("ses_k") or {}).get("ad"), m.group(1).strip())); tur["tampon"] = tp[m.end():] if not son else ""
ns["_konus_cumle_ic"] = _konus_cumle_ic
ok("gerçek _konus_cumle_ic her cümleyi tur['ses_k'] kişiliğinin sesiyle okutur (seslendir k=)", 'k=tur.get("ses_k")' in src[src.index("def _konus_cumle_ic"):src.index("def _konus_kesik_kapanis")])
ok("bekleme/ara/araç cümleleri de aynı kişiliğin sesiyle (k=tur.get('ses_k'))", src.count('k=tur.get("ses_k")') >= 4)
ns["KISILIK_SURE_SN"] = 180
def belirle(m, **tur): return ns["yon_belirle"](m, dict({"kaynak": "bas"}, **tur))
ns["_KSEC"]["ad"] = None
Y = belirle("Nova Teknoloji hakkında ne biliyoruz?")
ok("Tazı kaydı geçen soru → dış işler kişiliği (neden tazi), iç kişilik varsayılan muhatap", Y and Y["dis"] == "ROXANE" and Y["ic"] == "Matlas" and Y["neden"] == "tazi" and Y["tazi"] == ["Nova Teknoloji Ltd"], Y)
ok("alan adıyla da Tazı kaydı (novatek.test sitesi kaç yaşında?)", (belirle("novatek.test sitesi kaç yaşında?") or {}).get("neden") == "tazi")
for s_ in ("Bugün İstanbul'da hava nasıl?", "Dolar kuru kaç?", "Rakipler son haberlerde ne yapmış?", "Bu sayfayı özetle https://ornek.test/duyuru", "What is the latest news about the market?", "Bu firmanın kurucusu kimdir?"):
    y_ = belirle(s_); ok(f"web/güncel bilgi kalıbı → dış: {s_!r}", bool(y_) and y_["neden"] == "web", y_)
y_ = belirle("Nova Teknoloji ile yarınki toplantım için ne bilmeliyim?")
ok("dış + iç sinyal (toplantı) → dış işler ana ses, iç sinyal işaretli (öbür asistanın ek cümlesi beklenir)", y_ and y_["dis"] == "ROXANE" and y_["ic_sinyal"] is True)
for s_ in ("Bugün takvimimde ne var?", "Açık işlerim neler?", "Şu konuda ne düşünüyorsun?", "Teşekkürler.", "Nova Teknoloji.", "Yarın saat kaçta kalkayım?", "Son toplantıdaki kararlar neydi?", "Can Örnek kimdir?"):
    ok(f"iç ya da belirsiz soru → yönlendirme yok (varsayılan muhatap): {s_!r}", belirle(s_) is None)
ok("karşı taraf / adla hitap / moderatör / özet turu yönlendirilmez", all(belirle("Nova Teknoloji hakkında ne biliyoruz?", **t) is None for t in ({"karsi": "Ali"}, {"kaynak": "hitap"}, {"kaynak": "karsi"}, {"kaynak": "moderator"}, {"kaynak": "ozet"}, {"otonom": True})))
ns["_KSEC"].update(ad="Atlas", t=time.time())
ok("kullanıcı yakın zamanda birine adıyla seslenmişse (3 dk) o muhatap kalır, yönlendirme yok", belirle("Nova Teknoloji hakkında ne biliyoruz?") is None)
ns["_KSEC"].update(ad=None, t=0.0)
AYAR["dis_yonlendirme"] = False; ok("ayar dis_yonlendirme: false → yönlendirme yok", belirle("Nova Teknoloji hakkında ne biliyoruz?") is None); del AYAR["dis_yonlendirme"]
# yuva durumları: dış yuva boş (beta, tek/iki kişilik) ve yalnız dış yuva
AYAR["kisilik_dis"] = ""; ok("dış yuva boş → eski davranış (yönlendirme yok), soru işareti eskisi gibi", belirle("Nova Teknoloji hakkında ne biliyoruz?") is None and ns["yon_isareti"]({"kisi": "Atlas"}) == "[Bu soruyu Atlas cevaplıyor]\n" and ns["yon_isareti"]({}) == "")
AYAR["kisilik"] = ""; AYAR["kisilik_toplanti_disi"] = ""; AYAR["kisilik_dis"] = k3
ok("yalnız dış yuva tanımlıysa o tek muhatap: yönlendirme yok", belirle("Nova Teknoloji hakkında ne biliyoruz?") is None)
AYAR.update(kisilik=k1, kisilik_toplanti_disi=k2, kisilik_dis=k3)
# --- atışma izinleri
ns["_YON"]["taki"].clear(); ns["_YON"]["son_t"] = 0.0; ns["TOP"][0] = False
iki, taki, anah = ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")
ok("toplantı dışı: iki sesli söz serbest, takılma serbest (konuşmada henüz yok)", iki and taki and anah.startswith("kon:"))
ns["_YON"]["taki"][anah] = time.time()
ok("toplantı dışı: konuşma başına en çok bir takılma — hakkı kullanılmışsa takılma yok, iki sesli söz sürer", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, False))
ns["_YON"]["son_t"] = time.time() - 2000
ok("20 dk sessizlikten sonra yeni konuşma: takılma hakkı yenilenir", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, True))
ns["_YON"]["taki"].clear()
ok("kullanıcı sıkıntılı/yorgun/gergin → takılma yok (iki sesli söz sürer)", ns["yon_izin"]("Çok bunaldım, Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, False) and ns["yon_izin"]("Çok yoruldum, Nova Teknoloji kim?")[:2] == (True, False))
ns["duygu_acik"] = lambda: True; ns["duygu_durum"] = lambda: {"duygu": {"ses"}}
ok("duygu durumunda ses/söz/toplantı gerginliği → takılma yok", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, False)); del ns["duygu_acik"], ns["duygu_durum"]
ns["_YON"]["taki"].clear(); AYAR["yon_taki"] = False
ok("ayar yon_taki: false → takılma yok", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, False)); del AYAR["yon_taki"]
ns["TOP"][0] = True; ns["STATE"]["meeting"] = "Haftalık"
top_kur(R_DIS); ns["_YON"]["taki"].clear()
ok("toplantıda karşı taraf (dış katılımcı) varken iki asistanlı söz ve takılma YOK", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (False, False))
top_kur(R_BEL); ok("toplantıda emin değilsek (belirsiz katılımcı) da YOK", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (False, False))
top_kur(R_IC); ns["_KM_IC"]["t"] = 0.0
iki, taki, anah = ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")
ok("iç toplantı: iki sesli söz serbest, toplantı başına en çok bir takılma", iki and taki and anah == "top:Haftalık")
ns["_YON"]["taki"][anah] = time.time(); ok("iç toplantı: takılma hakkı kullanılınca yok", ns["yon_izin"]("Nova Teknoloji hakkında ne biliyoruz?")[:2] == (True, False))
ns["_YON"]["taki"].clear()
Y = belirle("Nova Teknoloji hakkında ne biliyoruz?", otonom=False); ok("yon_belirle toplantıda iç toplantı izniyle iki sesli", Y and Y["iki"] and Y["taki"])
top_kur(R_DIS); Y = belirle("Nova Teknoloji hakkında ne biliyoruz?")
ok("karşı taraflı toplantıda dış soru yine dış işler kişiliğine gider ama tek ses (iki=False, takılma yok)", Y and Y["dis"] == "ROXANE" and Y["iki"] is False and Y["taki"] is False)
ok("tek sesli turda işaret: «[Bu soruyu Roxane cevaplıyor — …» etiket yazma yok, kaynak ve tarih", (lambda s: s.startswith("[Bu soruyu Roxane cevaplıyor") and "etiket yazma" in s and "kaynağıyla ve tarihiyle" in s and "Tazı'nın dosyasına göre" in s)(ns["yon_isareti"]({"yon": Y, "kisi": "ROXANE"})))
ns["TOP"][0] = False; ns["_YON"]["taki"].clear()
# --- iki sesli işaret (istem): adlar, biçim kuralı, sınırlar
Y = belirle("Nova Teknoloji ile yarınki toplantım için ne bilmeliyim?"); isr = ns["yon_isareti"]({"yon": Y, "kisi": "ROXANE"})
ok("iki sesli işaret: iki ad etiketi, TEK cümle ek, ana ses, Tazı atfı, takılma serbest (~), iç sinyal, yazılı ayrıntı etiketsiz",
   all(x in isr for x in ("İKİ SESLİ TUR", "«[Roxane] …»", "«[Matlas] …»", "TEK cümle", "en çok 3 cümle", "Tazı'nın dosyasına göre", "«[Ad~]»", "ek cümlesi beklenir", "etiketsiz")) and "Takılma yok" not in isr, isr)
Y2 = dict(Y, taki=False, ic_sinyal=False, tazi=[]); isr2 = ns["yon_isareti"]({"yon": Y2, "kisi": "ROXANE"})
ok("takılma yoksa işaret «Takılma yok» der; Tazı kaydı yoksa «Tazı'da bu soru için kayıt yok» ve web yolu", "Takılma yok" in isr2 and "~" not in isr2 and "Tazı'da bu soru için kayıt yok" in isr2 and "ek cümlesi beklenir" not in isr2)
# =============================================================================================================================================================
# 3) İki sesli tur: biçimli çıktının ayrıştırılması, sıra, sınırlar
def akit(metin, y, parca=7):
    del OKU[:]; tur = {"yon": dict(y, ek_n=0, taki_n=0), "tampon": "", "metin": ""}
    m = re.search(r"(?:^|\n)[ \t]*-{3,}", metin); sesli = metin[:m.start()] if m else metin
    for i in range(0, len(sesli), parca):
        tur["tampon"] += sesli[i:i + parca]; tur["metin"] += sesli[i:i + parca]; ns["_konus_cumle"](tur)
    ns["_konus_cumle"](tur, son=True); tur["metin"] = metin
    return list(OKU), ns["yon_pano_metni"](metin, tur), tur
YT = dict(Y, taki=False, ic_sinyal=True); YK = dict(Y, taki=True)
M1 = "[Roxane] Tazı'nın dosyasına göre Nova 2019'da kuruldu. Son tarama 3 Kas.\n[Matlas] Yarın 10'da onlarla toplantın var. İkinci cümle atılır.\n---\nKaynak: Tazı dosyası, 3 Kas."
for parca in (1, 5, 7, 400):
    o, pano, tur = akit(M1, YT, parca)
    ok(f"sıra ve ses: önce dış işler (iki cümle), sonra iç asistanın TEK cümlesi, ek söz fazlası atılır (parça {parca})",
       o == [("ROXANE", "Tazı'nın dosyasına göre Nova 2019'da kuruldu."), ("ROXANE", "Son tarama 3 Kas."), ("Matlas", "Yarın 10'da onlarla toplantın var.")], o)
ok("panoda satır başı «[Ad] söz» etiketli bloklar, atılan cümle yok, yazılı ayrıntı aynen", pano == "[Roxane] Tazı'nın dosyasına göre Nova 2019'da kuruldu. Son tarama 3 Kas.\n[Matlas] Yarın 10'da onlarla toplantın var.\n---\nKaynak: Tazı dosyası, 3 Kas.", pano)
o, pano, tur = akit("[Roxane] Bilgi burada.\n[Matlas] Ek bir.\n[Matlas] Ek iki.", YT)
ok("iç asistanın ikinci satırı sınır dışı: söylenmez, panoda yok", o == [("ROXANE", "Bilgi burada."), ("Matlas", "Ek bir.")] and "Ek iki" not in pano, (o, pano))
o, pano, tur = akit("Düz cevap, etiket yok. İkinci cümle.", YT)
ok("etiket yazılmamışsa tüm cevap dış işler kişiliğinin sesiyle (ana ses), panoda etiketsiz", o == [("ROXANE", "Düz cevap, etiket yok."), ("ROXANE", "İkinci cümle.")] and pano == "Düz cevap, etiket yok. İkinci cümle.", (o, pano))
o, pano, tur = akit("[Roxane] Yalnız dış bilgi. İkinci cümle.", YT)
ok("yalnız dış işler konuştuysa panoda etiket yok (başlık zaten onun adı)", pano == "[Roxane] Yalnız dış bilgi. İkinci cümle.".replace("[Roxane] ", ""), pano)
o, pano, tur = akit("[Roxane] Kaynak [1] var. Bakın.\n[1] kaynak adı bir etiket değil.", YT)
ok("tanınmayan köşeli parantez ([1]) etiket sayılmaz, metindir", o and o[0][0] == "ROXANE" and all(x[0] == "ROXANE" for x in o) and any("[1] kaynak adı" in x[1] for x in o), o)
o, pano, tur = akit("[Roxane] Bilgi.\n[Matlas~] Takılma burada.", YT)
ok("takılma izni yokken «[Ad~]» satırı söylenmez ve panoda görünmez", o == [("ROXANE", "Bilgi.")] and "Takılma" not in pano, (o, pano))
ns["_YON"]["taki"].clear(); o, pano, tur = akit("[Roxane] Bilgi.\n[Matlas~] Takılma burada. Fazlası atılır.\n[Roxane~] İkinci takılma.", YK)
ok("takılma izni varken ilki söylenir (tek cümle), ikincisi sınır dışı; hak işlenir (konuşma başına bir)", o == [("ROXANE", "Bilgi."), ("Matlas", "Takılma burada.")] and "İkinci takılma" not in pano and list(ns["_YON"]["taki"]) == [YK["anahtar"]], (o, pano, ns["_YON"]["taki"]))
o, pano, tur = akit("[Roxane] Bilgi.\n[Matlas] İçeriden bilgi.\n[Matlas~] Takılma burada.", YK)
ok("ek söz + takılma birlikte: ek (1) ve takılma (1) ayrı sayılır", o == [("ROXANE", "Bilgi."), ("Matlas", "İçeriden bilgi."), ("Matlas", "Takılma burada.")], o)
ns["_YON"]["taki"].clear()
ns["TALIMAT_ETIKET_BAS"] = re.compile(r"\[\s*[İI]LET\b", re.I)
o, pano, tur = akit("[Roxane] Bilgi.\n[Matlas] İçeriden bilgi. Fazla cümle.\n[İLET: hedef | ileti]", YT); pano_ = ns["yon_pano_metni"]("[Roxane] Bilgi.\n[Matlas] İçeriden bilgi. Fazla cümle.\n[İLET: hedef | ileti]", tur)
ok("ek sözün ardından gelen [İLET …] etiketi kırpılmaz (talimat kaybolmaz), ek söz tek cümleye iner", pano_.endswith("\n[İLET: hedef | ileti]") and "Fazla cümle" not in pano_ and "[Matlas] İçeriden bilgi." in pano_, pano_)
# akarken yarım etiket beklenir (okunmaz, panoda görünmez)
tur = {"yon": dict(YT, ek_n=0, taki_n=0), "tampon": "", "metin": ""}; del OKU[:]
for p_ in ("[Roxane] İlk cümle bitti. [Rox", "ane] bu etiket ortada.", "\n[Mat"):
    tur["tampon"] += p_; tur["metin"] += p_; ns["_konus_cumle"](tur)
ok("yarım etiket akışta: öncesi okunur, etiket tamamlanana dek beklenir (okunmaz)", OKU == [("ROXANE", "İlk cümle bitti. [Rox")] or OKU == [("ROXANE", "İlk cümle bitti.")] or all("[Mat" not in x[1] for x in OKU), OKU)
ok("panoda akarken yarım etiket görünmez", "[Mat" not in ns["yon_pano_metni"](tur["metin"], tur), ns["yon_pano_metni"](tur["metin"], tur))
ok("tek sesli turda (iki=False) metne dokunulmaz: sarmalayıcı doğrudan okur, pano metni aynen", (lambda t: (ns["_konus_cumle"](t, son=True), OKU[-1])[1] == (None, "[Matlas] diye yazsa da okur."))({"yon": dict(Y, iki=False), "tampon": "[Matlas] diye yazsa da okur."})
   and ns["yon_pano_metni"]("ham [Matlas] metin", {"yon": dict(Y, iki=False)}) == "ham [Matlas] metin")
ok("model geçmişine giden metinde etiketler «Ad: » olur (sonraki turlara etiket örneği taşınmasın)", re.sub(r"(?m)^\[([^\]\n:]{1,40})\][ \t]*", r"\1: ", "[Roxane] Bir.\n[Matlas] İki.") == "Roxane: Bir.\nMatlas: İki." and 'r"\\1: "' in src)
# =============================================================================================================================================================
# 4) Ses: her söz kendi kişiliğinin sesiyle (brifing-ses.py _kisilik_sesi/seslendir → kuyruk öğesi "ks")
bsrc = oku("aktarici", "brifing-ses.py")
SES = {"q": [], "isci": True, "kes": 0}; sn = {"AYAR": {"ses_motoru": "pocket", "konusma": True}, "SES": SES, "SES_K": threading.Condition(), "os": os, "re": re, "print": lambda *a, **k: None, "ARAYUZ_DILI": "tr", "SES_TABAN_HIZ": 180,
      "kisilik": lambda ad=None: ns["kisilik"](ad), "gemini_izinli": lambda t=False: False, "gemini_acik": lambda: False, "pocket_var": lambda: True, "pocket_ses_adi": lambda v: str(v).split("pocket:", 1)[-1], "pocket_varsayilan": lambda: "tr:varsayilan",
      "ses_secimi": lambda: "Yelda", "ton_ayikla": lambda m: (m, None), "ton_kur": lambda t: None, "etiket_sil": lambda m: m, "ses_duzen": lambda m, mac=False: m, "telaffuz": lambda m, mac=False: m, "kisilik_telaffuz": lambda m: m,
      "okuma_dili": lambda m: "tr", "kisilik_en_sesi": lambda k=None: None, "ses_durdur": lambda: None, "gemini_kisilik_sesi": lambda k: "Kore", "ses_uslup_bul": lambda m, k: None, "ozet_ses_motoru": lambda k=None: (None, "yok"), "_cal_anahtar": lambda o: "",
      "SES_BASLA": None}
exec(compile(fonks(bsrc, ("_kisilik_sesi", "kisilik_sesi", "seslendir", "_ses_metin")), "brifing-ses.py", "exec"), sn)
kA, kR = ns["kisilik"]("Matlas"), ns["kisilik"]("ROXANE")  # toplantı dışında varsayılan Matlas
ns["_KSEC"].update(ad=None, t=0.0); ns["TOP"][0] = False
ok("kisilik_sesi(kk=): o an cevaplayan değil verilen kişiliğin yerel sesi (Pocket: atlas ≠ roxane)", sn["kisilik_sesi"](None, False, kR)[:2] == ("pocket", "tr:roxane") and sn["kisilik_sesi"](None, False, ns["kisilik"]("Atlas"))[:2] == ("pocket", "tr:atlas"))
ok("kisilik_sesi(\"mac\", kk=): kişiliğin Mac sesi ve hızı (Yelda 1.1 ↔ Cem)", sn["kisilik_sesi"]("mac", False, kR)[1:] == ("Yelda", 1.1) and sn["kisilik_sesi"]("mac", False, ns["kisilik"]("Atlas"))[1] == "Cem")
SES["q"].clear(); sn["seslendir"]("Dış işler cümlesi.", kuyruk=True, k=kR); sn["seslendir"]("Varsayılan cümle.", kuyruk=True, k=kA); sn["seslendir"]("Kişiliksiz cümle.", kuyruk=True)
ok("seslendir(k=dış işler) → «ks» öğesi (kendi Pocket sesi, Mac sesi, hızı); varsayılan kişilik ve kişiliksiz çağrı düz metin (eski davranış)",
   SES["q"] == [("ks", "Dış işler cümlesi.", "pocket", "tr:roxane", "Yelda", 1.1), "Varsayılan cümle.", "Kişiliksiz cümle."], SES["q"])
SES["q"].clear(); sn["seslendir"]("Toplantı kişiliği cümlesi.", kuyruk=True, k=ns["kisilik"]("Atlas"))
ok("varsayılan olmayan başka kişilik de kendi sesiyle («ks», Atlas: Pocket atlas, Mac Cem)", SES["q"] == [("ks", "Toplantı kişiliği cümlesi.", "pocket", "tr:atlas", "Cem", 1.0)], SES["q"])
ns["_KSEC"].update(ad="ROXANE", t=time.time())
SES["q"].clear(); sn["seslendir"]("Dış işler cümlesi.", kuyruk=True, k=kR); sn["seslendir"]("Varsayılan cümle.", kuyruk=True, k=kA)
ok("o an cevaplayan kişilik dış işlerse onun cümlesi düz metin, öbürü «ks»", SES["q"][0] == "Dış işler cümlesi." and SES["q"][1][0] == "ks", SES["q"])
ns["_KSEC"].update(ad=None, t=0.0)
sn["gemini_izinli"] = lambda t=False: True; kR2 = dict(kR, ses="gemini:Kore"); SES["q"].clear(); sn["seslendir"]("Gemini cümlesi.", kuyruk=True, k=kR2)
ok("Gemini sesli kişilik: öğe «g» (kendi Gemini sesi) — eski yol", SES["q"] and SES["q"][0][0] == "g", SES["q"])
ok("_ses_isci «ks» öğesini bilir (test/ses-kuyruk.py) ve _ses_metin düz metni verir", '"ks"' in bsrc and sn["_ses_metin"](("ks", "x", "mac", None, "Y", 1.0)) == "x")
# =============================================================================================================================================================
# 5) Toplantı öncesi brifing: "Dış taraf" bölümü (Tazı'nın yerel dosyasından; model çağrısı yok)
bn = dict(ns); bn.update(katilimci_coz=kat_coz)
exec(compile(fonks(bsrc, ("dis_kisilik", "dis_etiket", "brifing_dis_taraf", "brifing_dis_konusma")), "brifing-ses.py", "exec"), bn)
bn["BRIFING_DIS_EN_COK"] = 6
R_B = {"kisiler": [{"ad": "Can Örnek", "adresler": ["can" + AT + "firma.test"]}, {"ad": "Deniz Aksoy", "adresler": ["deniz" + AT + "novatek.test"]}, {"ad": "Ece Toprak", "adresler": ["ece" + AT + "yenifirma.test"]},
                                                                  {"ad": "Gül Yıldız", "adresler": ["gul" + AT + "gmail.com"]}, {"ad": "Berk", "adresler": ["berk" + AT + "yenifirma.test"]}], "eslesmeyen": []}
dt = bn["brifing_dis_taraf"]({"_r": R_B})
ok("dış taraf: Tazı'da olan firma özetiyle (tek satır), olmayanlar «dosya yok — Tazı'ya aday» (alan adıyla gruplu, serbest postada kişi adıyla); şirket içi katılımcı yok",
   len(dt) == 3 and dt[0].startswith("Nova Teknoloji Ltd · 2019'da kurulmuş") and any(x.startswith("yenifirma.test (Berk, Ece Toprak): Tazı'da dosya yok") and x.endswith("Tazı'ya aday") for x in dt)
   and any(x.startswith("Gül Yıldız: Tazı'da dosya yok") for x in dt) and not any("Can" in x or "firma.test:" in x for x in dt), dt)
ok("etiket: «<dış işler adı> · Dış taraf»; yuva boşsa «Tazı · Dış taraf»", bn["dis_etiket"]() == "Roxane · Dış taraf" and (AYAR.update(kisilik_dis=""), bn["dis_etiket"]())[1] == "Tazı · Dış taraf"); AYAR["kisilik_dis"] = k3
bn["gizli_acik"] = lambda: True; ok("gizli kipte bölüm yok", bn["brifing_dis_taraf"]({"_r": R_B}) == []); bn["gizli_acik"] = lambda: False
ok("dış katılımcı yoksa bölüm yok", bn["brifing_dis_taraf"]({"_r": R_IC}) == [])
# 11 Kasım: Tazı'da dosyası olmayan KURUMSAL alan adı → hızlı tarama istenir (serbest postadaki kişi değil; en çok 3; gizli kipte ve Tazı kapalıyken yok)
KOS = []; bn["tazi_kos"] = lambda ad, alan=None, kip="hizli", neden="elle": KOS.append((ad, alan, kip, neden)) or {"ok": True, "durum": "basladi"}
bn["brifing_dis_taraf"]({"_r": R_B})
ok("brifing: dosyası olmayan kurumsal alan için hızlı tarama istendi (alan adı, kip hızlı, neden brifing); gmail kişisi ve dosyası olan firma için istenmedi", KOS == [("yenifirma.test", "yenifirma.test", "hizli", "brifing")], KOS)
R_B3 = {"kisiler": [{"ad": "P" + str(i), "adresler": ["p" + str(i) + AT + "firma" + str(i) + ".test"]} for i in range(5)], "eslesmeyen": []}; KOS.clear(); bn["brifing_dis_taraf"]({"_r": R_B3})
ok("brifing: en çok 3 tarama istenir", len(KOS) == 3, KOS)
KOS.clear(); bn["gizli_acik"] = lambda: True; bn["brifing_dis_taraf"]({"_r": R_B}); bn["gizli_acik"] = lambda: False
ok("gizli kipte brifing taraması istenmez", not KOS, KOS)

AYAR["kod"] = os.path.join(T, "yok"); ns["_KM_TAZI"].update(m=None, hata=None); bn["tazi_var"] = lambda: False
ok("Tazı kurulu değilse bölüm yok (hepsi «dosya yok» yanıltmasın)", bn["brifing_dis_taraf"]({"_r": R_B}) == []); AYAR["kod"] = KOD; ns["_KM_TAZI"].update(m=None, hata=None); bn["tazi_var"] = ns["tazi_var"]
okuma = bn["brifing_dis_konusma"]({"dis_taraf": dt})
ok("sesli «Dış taraf.» bölümü: ilk üç satır, kaynak/«(son tarama …)» parantezi okunmaz", okuma.startswith("Dış taraf. Nova Teknoloji Ltd") and "son tarama" not in okuma and okuma.count(".") >= 3, okuma)
ok("brifing sonucuna dis_taraf + dis_etiket yazılır; _brifing_oku ana okumadan sonra dış bölümü dış işler kişiliğinin sesiyle sıraya alır; yuva boşsa varsayılan asistanın okumasına eklenir",
   'sonuc["dis_taraf"] = dt; sonuc["dis_etiket"] = dis_etiket()' in bsrc and 'seslendir(dis[0], kuyruk=True, k=dis[1])' in bsrc and 'if dm and dk is None: metin = (metin + " " + dm).strip()' in bsrc)
pano = oku("pano", "pano.html"); dil = oku("pano", "dil.js")
ok("pano: brifing bölümü (kart, brifing paneli, dışa aktarma, Bugün ayrıntısı) etiketiyle; İngilizce dil.js'te", pano.count("dis_taraf") >= 4 and '"Dış taraf": "Outside parties"' in dil)
# =============================================================================================================================================================
# 6) Toplantı oturumunun `tazi` komutu ve istemi (toplanti-oturum.py, toplanti-claude.py)
DURUM = {"gizli": False}
class FR(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        j = json.dumps({"gizli": DURUM["gizli"], "file": "2026-11-10-1000-Haftalik.md", "konus": {"dis_ad": DURUM.get("dis_ad", "Roxane")}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(j)
PORT = bos_port(8798); srv = ThreadingHTTPServer(("127.0.0.1", PORT), FR); threading.Thread(target=srv.serve_forever, daemon=True).start()
CL = os.path.join(T, "canli2"); os.makedirs(CL)
def tc(ad, ayar=None, env=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TAZI_DIR=TZ)
    if ayar is not None: e["SUFLOR_AYAR"] = yaz("ayar-" + str(abs(hash(json.dumps(ayar))) % 10**6) + ".json", json.dumps(dict({"tazi_liste": LISTE}, **ayar)))
    r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", CL, "--relay", f"http://127.0.0.1:{PORT}", "tazi", ad], capture_output=True, text=True, timeout=30, env=e)
    return (r.stdout + r.stderr).strip()
c1 = tc("Nova Teknoloji")
ok("tc tazi: Tazı'da olan ad → «KART ETİKETİ: Roxane · Tazı dosyası» + yerel özet (≤ 8 satır) + kaynağı/tarihi an", c1.startswith("KART ETİKETİ: Roxane · Tazı dosyası\nTazı · Nova Teknoloji Ltd") and "Kimlik: 2019'da kurulmuş" in c1 and "son tarama tarihini an" in c1, c1)
c2 = tc("Nova Teknoloji"); ok("aynı ad toplantıda bir kez: ikinci çağrı «zaten soruldu», kart yazma", "zaten soruldu" in c2 and "KART" not in c2, c2)
c2b = tc("  NOVA   teknoloji "); ok("aynı ad büyük/küçük harf ve boşluk farkıyla da bir kez sayılır", "zaten soruldu" in c2b, c2b)
c3 = tc("Bilinmez Firma", ayar={"web_arastirma": True})
ok("Tazı'da dosya yoksa ve web araştırması açıksa: yalnız ad ve konuyla kısa açık kaynak araması (S208), etiket «Roxane · web», kaynak + tarih, tek kaynak = doğrulanmadı", "Tazı'da dosya yok: Bilinmez Firma" in c3 and "Web araştırması açık" in c3 and "yalnız ad ve konuyla" in c3 and "Roxane · web" in c3 and "doğrulanmadı" in c3, c3)
c4 = tc("Başka Firma", ayar={"web_arastirma": False})
ok("dosya yok + web araştırması kapalı: karta «dosya yok», arama yok", "Web araştırması kapalı" in c4 and "dosya yok" in c4 and "arama" not in c4.split("Web araştırması kapalı")[0], c4)
DURUM["dis_ad"] = None; os.remove(os.path.join(CL, "tazi-toplanti.json")); c5 = tc("Nova Teknoloji")
ok("dış işler kişiliği yoksa etiket yalnız «Tazı»", c5.startswith("KART ETİKETİ: Tazı\n"), c5); DURUM["dis_ad"] = "Roxane"
os.remove(os.path.join(CL, "tazi-toplanti.json")); DURUM["gizli"] = True; c6 = tc("Nova Teknoloji")
ok("gizli toplantıda hiçbir şey çalışmaz (Tazı okunmaz, ad sayılmaz)", c6.startswith("gizli toplantı: Tazı kartı yok") and not os.path.exists(os.path.join(CL, "tazi-toplanti.json")), c6); DURUM["gizli"] = False
os.remove(os.path.join(CL, "tazi-toplanti.json")) if os.path.exists(os.path.join(CL, "tazi-toplanti.json")) else None
ok("yeni toplantıda ad yeniden sorulabilir (kayıt toplantıya bağlı)", (lambda: (json.dump({"toplanti": "baska-toplanti.md", "adlar": ["nova teknoloji"]}, open(os.path.join(CL, "tazi-toplanti.json"), "w")), "KART ETİKETİ" in tc("Nova Teknoloji"))[1])())
def hz(gizli=False, ayar=None):  # toplanti-claude.py hazirlik: Tazı bölümü (gizli toplantıda ve ayar tazi kapalıyken yok)
    DURUM["gizli"] = gizli; e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TAZI_DIR=TZ)
    e["SUFLOR_AYAR"] = yaz("ayar-hz-" + str(abs(hash(json.dumps(ayar or {}))) % 10**6) + ".json", json.dumps(dict({"tazi_liste": LISTE}, **(ayar or {}))))
    r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", CL, "--relay", f"http://127.0.0.1:{PORT}", "hazirlik", "--kim", "Nova Teknoloji"], capture_output=True, text=True, timeout=30, env=e)
    DURUM["gizli"] = False; return r.stdout + r.stderr
h1 = hz()
ok("hazırlık: Tazı bölümü var (izlenen firma, yerel özet)", "## Tazı: son gelişmeler" in h1 and "Nova Teknoloji Ltd" in h1, h1[:300])
h2 = hz(gizli=True); ok("hazırlık: gizli toplantıda Tazı bölümü yok", "## Tazı:" not in h2 and "Nova Teknoloji Ltd" not in h2 and "Hazırlık" in h2, h2[:300])
h3 = hz(ayar={"tazi": False}); ok("hazırlık: ayar tazi kapalıyken bölüm yok", "## Tazı:" not in h3 and "Hazırlık" in h3, h3[:300])
osrc = oku("aktarici", "toplanti-oturum.py")
ok("salt okuyan komut listesinde (izinsiz): TOPO_TC_OKUMA'da tazi", '"dokum", "tazi"}' in osrc)
on = dict(ns); on.update(AYAR=dict(AYAR), tazi_var=ns["tazi_var"], tazi_mod=ns["tazi_mod"])
exec(compile(fonks(osrc, ("topo_tazi_istem",)), "toplanti-oturum.py", "exec"), on)
ti = on["topo_tazi_istem"]()
ok("toplantı oturumu istemi: yeni kurum dışı ad → `toplanti-claude.py tazi \"<ad>\"`, etiket «Roxane · Tazı dosyası», bir kez, gizlide yok, yorum/puan yok", all(x in ti for x in ("KURUM DIŞI", "toplanti-claude.py tazi", "«Roxane · Tazı dosyası»", "Aynı ad toplantıda bir kez", "Gizli toplantıda hiç çalıştırma", "yorum ya da puan yazma")), ti)
on["kisilikler"] = lambda: [k for k in ns["kisilikler"]() if k["rol"] != "dis"]; ok("dış işler yuvası boşsa etiket «Tazı»", "«Tazı»" in on["topo_tazi_istem"]() and "Roxane" not in on["topo_tazi_istem"]())
on["tazi_var"] = lambda: False; on["AYAR"] = {}; ok("Tazı kurulu/ayarlı değilse kural isteme girmez", on["topo_tazi_istem"]() == "")
ok("topo_istem Tazı kuralını web/ön yükleme kuralından sonra ekler", "web += topo_arac_onyukle(ks) + topo_tazi_istem()" in osrc)
# =============================================================================================================================================================
# 7) Özet: Tazı notu (relay.py son_ekle) + /status konus.dis_ad — yalıtılmış aktarıcı
PR = bos_port(8795); CA = os.path.join(T, "canli3"); os.makedirs(os.path.join(CA, "ozetler"))
for f in ("relay.py", "manifest.json", "tazi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PR, "uygulama": T, "proje": T, "ortak": T, "kisilik": k1, "kisilik_toplanti_disi": k2, "kisilik_dis": k3, "tazi_liste": LISTE, "tazi": True}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", TAZI_DIR=TZ)
r = subprocess.Popen([sys.executable, "relay.py", "--dir", CA, "--port", str(PR)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
def rq(yol, govde=None):
    q = urllib.request.Request(f"http://127.0.0.1:{PR}{yol}", data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
        headers={"X-Suflor-Anahtar": open(os.path.join(CA, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{PR}", "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except Exception as e: return {"_hata": str(e)}
try:
    for _ in range(80):
        if os.path.exists(os.path.join(CA, "kart-anahtari.txt")) and "çalışıyor" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): break
        time.sleep(0.25)
    st = rq("/status"); ok("/status konus.dis_ad: dış işler kişiliğinin görünen adı (tc tazi etiketi için)", (st.get("konus") or {}).get("dis_ad") == "Roxane", (st.get("konus") or {}).get("dis_ad"))
    def ozet(ad, metin):
        yol = os.path.join(T, ad + ".md"); open(yol, "w", encoding="utf-8").write(metin)
        return rq("/son-toplanti", {"ozet": yol, "baslik": ad, "dosya": ad + ".md", "cikti": {"karar": 1}, "metin": metin})
    r1 = ozet("ozet-bir", "# Özet\n\n## Kararlar\n- Nova Teknoloji ile teklif cuma gidecek.\n- Örnek A.Ş. sözleşmesi bekliyor; Kemal ile konuşuldu.\n")
    sv = (rq("/status").get("son_toplantilar") or [{}])[0]
    ok("özette geçen dış firmalar Tazı kayıtlarıyla eşlenir: ad başına tek satır özet (Tazı'nın dosyası olan ve olmayan), etiket «Roxane»", r1.get("ok") and sv.get("tazi_etiket") == "Roxane"
       and [x["ad"] for x in sv.get("tazi") or []] == ["Nova Teknoloji Ltd", "Örnek A.Ş."] and all("\n" not in x["satir"] for x in sv["tazi"]) and sv["tazi"][0]["satir"].startswith("Nova Teknoloji Ltd"), sv.get("tazi"))
    ok("özet dosyasına Tazı notu yazılmaz (yalnız panoda)", "Tazı" not in open(os.path.join(T, "ozet-bir.md"), encoding="utf-8").read())
    r2 = ozet("ozet-iki", "# Özet\n\n- Nova Teknoloji konuşuldu.\n- gizli bölüm (10:20–10:30)\n"); sv2 = next((x for x in rq("/status").get("son_toplantilar") or [] if x.get("baslik") == "ozet-iki"), {})
    ok("gizli bölümlü özette Tazı notu yok", r2.get("ok") and not sv2.get("tazi"), sv2)
    r3 = ozet("ozet-uc", "# Özet\n\n- Kimseyle ilgili bir şey yok.\n"); sv3 = next((x for x in rq("/status").get("son_toplantilar") or [] if x.get("baslik") == "ozet-uc"), {})
    ok("dış ad geçmiyorsa not yok", r3.get("ok") and not sv3.get("tazi"), sv3)
finally:
    r.terminate(); r.wait(timeout=10); srv.shutdown()
ok("pano: Son toplantılar ve Bugün ayrıntısında «<ad> · Tazı notu» (en çok 5 satır), dil.js'te İngilizce", pano.count("r.tazi") >= 3 and '"Tazı notu": "Tazı note"' in dil)
ok("pano: iki sesli cevap ad etiketli ayrı bloklar (kcKonus, kcOge, shTur); bilinen asistan adıyla başlayan satırlar", "function kcKonus(ky)" in pano and "kcKonusHtml(e,i,ky,mini_)" in pano and "const sg=kcKonus(ky)" in pano and "kisilik_harita" in pano)
# =============================================================================================================================================================
# 8) Küçükler: "Raks" kuralı; kişilik adı kümeleri; kısa hitap
b = ns["kisilik_hitap_bul"]
ok("Türkçede sözcük olan kısa ad ('Raks') yalnız virgül/iki nokta ile hitap: 'Raks, bu firma kim?' / 'Raks: bak' evet; 'Raks etmek zor muydu?' / 'Raks bu firma kim?' hayır",
   b("Raks, bu firma kim?")[0]["ad"] == "ROXANE" and b("Raks: bak şuna")[0]["ad"] == "ROXANE" and b("Raks etmek zor muydu?")[0] is None and b("Raks bu firma kim?")[0] is None and b("Raks?")[0] is None)
ok("öteki kısa adlar (Rox, Ro) eskisi gibi soru biçimiyle de hitap", b("Rox bu firma kim?")[0]["ad"] == "ROXANE" and b("Ro, bu firma kim?")[0]["ad"] == "ROXANE" and b("Roxane bak şuna")[0]["ad"] == "ROXANE")
ok("hitap_kisa_siki yalnız Türkçe sözcük olan kısa adları işaretler", ns["hitap_kisa_siki"]("Raks") and ns["hitap_kisa_siki"]("raks") and not ns["hitap_kisa_siki"]("Rox") and not ns["hitap_kisa_siki"]("Ro"))
sz_ = oku("aktarici", "sozluk-ogren.py"); so = {"os": os, "re": re, "AYAR": AYAR, "_so_k": lambda x: re.sub(r"\s+", " ", str(x).lower()).strip()}
exec(compile(fonks(sz_, ("so_kisilik_adlari",)), "sozluk-ogren.py", "exec"), so)
adlar = so["so_kisilik_adlari"]()
ok("öğrenen sözlük kişilik adları üçüncü yuvayı da sayar (roxane, roksi…)", "roxane" in adlar and "roksi" in adlar and "atlas" in adlar and "matlas" in adlar, sorted(adlar))
print("roxie: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı")); sys.exit(1 if hata else 0)
