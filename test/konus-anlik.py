#!/usr/bin/env python3
# v0.250.2 (17 Kasım): Konuş güncel değer denetimi (bas-konus.py konus_anlik_*), öz eleştiri sohbet sayılır (konus_derin_mi / DERIN_SOHBET_RX),
# Pocket cümle sonu artığı (pocket-isci.py kuyruk_temizle). Model çağrısı yok; bas-konus.py'nin ilgili bölümü saplarla yüklenir.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/konus-anlik.py
import io, json, os, re, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)

src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
bas = src.index("# v0.250.2 (17 Kasım, kullanıcı: \"web erişimi zaten var"); son = src.index("def _web_bekci(tur):")
okunan, seslenen = [], []
class Yazici(io.StringIO):
    def flush(self): pass
g = {"re": re, "json": json, "AYAR": {}, "KONUS": {}, "_KS": {"web": True, "w": Yazici()},
     "_t": lambda tr, en: tr, "_konus_kur": lambda **k: None, "seslendir": lambda m, **k: seslenen.append(m),
     "TALIMAT_ETIKET_BAS": re.compile(r"\[İLET"), "KAYIT_ETIKET_BAS": re.compile(r"\[KAYIT:"), "KUTU_ETIKET_BAS": re.compile(r"\[NOT:")}
g["_konus_cumle"] = lambda tur, son=False: okunan.append(tur["tampon"])
exec(src[bas:son], g)

# 1) sınıflandırma
for q, b in [("Sydney'in bir haftalık hava durumunu söyler misin?", True), ("Dolar kaç lira?", True), ("Gram altın kaç lira?", True), ("Maç kaç kaç bitti?", True),
             ("What's the weather in Paris?", True), ("Bugün beni neler bekliyor?", False), ("Masanın altında ne var?", False), ("Bunu hissediyorum.", False),
             ("Kurul toplantısı ne zaman?", False), ("Kurulum nasıl gidiyor?", False)]:
    ok(f"güncel değer sorusu mu: {q} → {b}", g["konus_anlik_mi"](q) == b)
tur = {"sesli": True, "kaynak": "bas"}
ok("web açıkken tutulur", g["konus_anlik_tut"](tur, "İstanbul'da hava nasıl?"))
g["_KS"]["web"] = False; ok("web kapalıyken tutulmaz", not g["konus_anlik_tut"](tur, "İstanbul'da hava nasıl?")); g["_KS"]["web"] = True
ok("toplantıda (otonom) tutulmaz", not g["konus_anlik_tut"]({"sesli": True, "otonom": True}, "hava nasıl"))
g["AYAR"]["konus_anlik_denetim"] = False; ok("ayarla kapanır", not g["konus_anlik_tut"](tur, "hava nasıl")); g["AYAR"].pop("konus_anlik_denetim")

# 2) "bulamadım" → bir kez yeniden gönderim, okunmaz
tur = {"sesli": True, "soru": "Sydney hava durumu?", "araclar": ["WebSearch"], "arac_kesim": 5,
       "metin": "Hmm. Sydney için güncel bir haftalık tahmin bulamadım. En sağlıklısı Meteoroloji Bürosu'na bakmak.", "anlik_tut": True}
w = g["_KS"]["w"]
ok("bulamadım → yeniden gönderildi", g["konus_anlik_yeniden"](tur, {}) is True)
giden = [json.loads(l) for l in w.getvalue().splitlines()]
ok("sürece tek not gitti, soru ve WebFetch talimatı içinde", len(giden) == 1 and "WebFetch" in giden[0]["message"]["content"] and giden[0]["message"]["content"].endswith("Soru: Sydney hava durumu?"))
ok("eski cevap temizlendi, okunmadı", tur["metin"] == "" and not okunan and tur["anlik_tekrar"])
ok("kullanıcıya kısa ara cümle", seslenen == ["Bir de sayfalara bakıyorum."])
tur["metin"] = "İkinci cevap: yine bulamadım."
ok("ikinci 'bulamadım' yeniden göndermez (en çok bir kez)", g["konus_anlik_yeniden"](tur, {}) is False and len(w.getvalue().splitlines()) == 1)

# 3) değer bulunduysa doğrudan okunur; yalnız son araçtan sonraki metin, ayrıntı okunmaz
tur = {"sesli": True, "soru": "hava?", "araclar": ["WebSearch", "WebFetch"], "metin": "Bakıyorum, araçtan önce.Yarın 23 derece, bulutlu.\n---\nKaynak: timeanddate", "anlik_tut": True}
tur["arac_kesim"] = len("Bakıyorum, araçtan önce.")
ok("değer var → yeniden gönderim yok", g["konus_anlik_yeniden"](tur, {}) is False)
g["konus_anlik_oku"](tur)
ok("okunan yalnız son araçtan sonraki sesli kısım", okunan[-1].strip() == "Yarın 23 derece, bulutlu." and tur["ayrinti"] and not tur["anlik_tut"])
ok("hata sonucunda yeniden gönderim yok", g["konus_anlik_yeniden"]({"metin": "bulamadım", "soru": "x"}, {"is_error": True}) is False)

# 4) öz eleştiri sohbet sayılır (Opus derin turu değil)
m = re.search(r"^DERIN_SOHBET_RX = re\.compile\(.*?\)\n", src, re.M | re.S)
ok("DERIN_SOHBET_RX var", bool(m))
h = {"re": re}; exec(m.group(0), h)
ok("'öz eleştiri olarak neler söyleyebilirsin' sohbet", bool(h["DERIN_SOHBET_RX"].search("Öz eleştiri olarak neler söyleyebilirsin?")))
ok("'stratejiyi eleştir' sohbet değil", not h["DERIN_SOHBET_RX"].search("Bu stratejiyi eleştirir misin?"))
ok("konus_derin_mi öz eleştiriyi derin saymıyor (kural kaynakta)", 'return False, "sohbet (öz eleştiri)"' in src)
ki = open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read()
ok("KIVRAK: öz eleştiri asistanın kendisi için", "SENİN (asistanın) davranışın" in ki and "YOUR (the assistant's) behaviour" in ki)

# 5) Pocket cümle sonu artığı
try:
    import numpy as np
except ImportError:
    np = None
if np is None: print("· numpy yok: kuyruk_temizle atlandı")
else:
    ps = open(os.path.join(KOD, "pocket-isci.py"), encoding="utf-8").read()
    p = {}; exec(ps[ps.index("PARCA_SN, ARA_SN"):ps.index("def main():")], p)
    SR = 24000; rng = np.random.default_rng(1)
    konusma = (0.3 * np.sin(np.arange(int(0.5 * SR)) * 0.05)).astype(np.float32)
    sessiz = (1e-5 * rng.standard_normal(int(0.3 * SR))).astype(np.float32)
    artik = (0.2 * np.sin(np.arange(int(0.12 * SR)) * 0.09)).astype(np.float32)
    a = np.concatenate([konusma, sessiz, artik]); b = p["kuyruk_temizle"](a, SR, np)
    ok("sessizlikten sonraki kısa artık atıldı", len(b) <= len(konusma) + int(0.08 * SR) and len(b) >= len(konusma))
    ok("son örnek sıfıra sönümlü", abs(float(b[-1])) < 1e-6)
    c = np.concatenate([konusma, sessiz]); d = p["kuyruk_temizle"](c, SR, np)
    ok("artık yoksa konuşma ve sessizlik korunur", len(d) == len(c))
    kapanma = (1e-3 * rng.standard_normal(int(0.08 * SR))).astype(np.float32)  # "t" kapanması: sessiz eşiğin üstünde
    e = np.concatenate([konusma, kapanma, artik]); f = p["kuyruk_temizle"](e, SR, np)
    ok("patlamalı ünsüz (kısa kapanma + ses) atılmaz", len(f) == len(e))
    yalniz = np.concatenate([sessiz, artik]); y = p["kuyruk_temizle"](yalniz, SR, np)
    ok("önünde konuşma yoksa (kısa cümlenin kendisi) atılmaz", len(y) == len(yalniz))
    ok("önceki kısım çalındıysa sessizlik+artık atılır", len(p["kuyruk_temizle"](yalniz, SR, np, once=True)) < len(yalniz))

# 6) v0.250.3: tur sonu beklemesi ve ön söz; Pocket Whisper'dan sonra ısınır
so = open(os.path.join(KOD, "aktarici", "sohbet.py"), encoding="utf-8").read()
ok("SOHBET_KISA_SN 1,3", re.search(r"^SOHBET_SESSIZ_SN, SOHBET_KISA_SN.*= 0\.6, 1\.3,", so, re.M) is not None)
h = {"re": re}; exec(re.search(r"^SOHBET_ONSOZ_RX = re\.compile\(.*?\)\n", so, re.M).group(0), h)
for q, b in [("Tamam. Peki Marvin, aynı soruyu tekrar sorayım sana.", True), ("Şöyle bir şey var ama", True), ("Peki,", True),
             ("Açıkçası şu anda kuş gözlemini yapmak istemezdim Marvin.", False), ("Bunu yapar mısın?", False), ("I think so.", False)]:
    ok(f"ön söz: {q} → {b}", bool(h["SOHBET_ONSOZ_RX"].search(q)) == b)
import threading, time
bk = src[src.index("POCKET_WH_BEKLE_SN, POCKET_WH_BASLA_SN"):src.index("def konus_basla():")]
sira = []
P = {"STATE": {"whisper": {"durum": "yukleniyor"}}, "POCKET": {"durum": "kapali"}, "AYAR": {}, "os": os, "time": time, "threading": threading,
     "pocket_var": lambda: True, "kisilik_sesi": lambda: ("pocket", None, 1), "print": lambda *a, **k: None}
def _pb(*a, **k): sira.append("pocket"); P["POCKET"]["durum"] = "yukleniyor"; return False
P["pocket_baslat"] = _pb
exec(bk, P); P["POCKET_WH_BASLA_SN"] = 0.3
os.environ.pop("SUFLOR_TEST_BASLAT", None)
P["konus_pocket_isit"](); time.sleep(0.5)
ok("Whisper yüklenirken Pocket beklemede", sira == [])
P["STATE"]["whisper"]["durum"] = "hazir"; sira.append("whisper"); time.sleep(0.5)
ok("Whisper hazır olunca Pocket ısındı (sıra: önce Whisper)", sira == ["whisper", "pocket"])
P["POCKET"]["durum"] = "kapali"; P["STATE"]["whisper"]["durum"] = "kapali"; sira.clear()
P["konus_pocket_isit"](); time.sleep(0.8)
ok("Whisper yüklenmeye başlamadıysa kısa beklemeden sonra Pocket ısınır", sira == ["pocket"])

print("konus-anlik:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
