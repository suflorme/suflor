#!/usr/bin/env python3
# Ses kuyruğu işçisi (aktarici/brifing-ses.py _ses_isci): her öğe doğru çalıcıya gider — ("dosya", yol) → afplay, ("g", metin, ses, üslup) → Gemini,
# düz metin → Mac sesi. v0.80.1: Gemini parçası da demet olduğu için dosya sanılıp afplay'e gidiyordu; sesli cevap hiç duyulmuyordu (deneme kipinde
# seslendir kuyruğa girmeden döndüğü için öteki testler görmedi). Sahte çalıcılarla, ses çalınmaz (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-kuyruk.py
import ast, os, sys, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read())
fn = [f for f in agac.body if isinstance(f, ast.FunctionDef) and f.name in ("_ses_metin", "_ses_isci", "_cal_anahtar", "ses_basladi", "_g_birlestir", "ses_sonraki_hazirla")]
CALAN = []
class P:  # sahte afplay/say süreci
    def __init__(self, k, **a): self.k = k; self.stdin = self; self.yazi = b""
    def write(self, b): self.yazi += b
    def close(self): CALAN.append(("mac", self.yazi.decode()))
    def wait(self):
        if self.k[0] == "/usr/bin/afplay": CALAN.append(("afplay", self.k[1]))
def deneme(gemini_acik, motor="mac", q=None, bekle=3, pocket=None, piper=None, bek=None, onceden=(), ek=None):  # pocket/piper: None = yok, True/False = okuyabildi mi (S93)
    del CALAN[:]
    n = {"SES": {"q": q or [("dosya", "/tepki.caf"), ("g", "Gemini cümlesi.", "Charon", "dostça"), "Mac cümlesi."], "isci": True, "kes": 0, "bek": bek or []}, "GEMINI_BIRLESIK_EN_COK": 600, "SES_K": threading.Condition(),
         "subprocess": type("S", (), {"Popen": P, "DEVNULL": None, "PIPE": None}), "kisilik_sesi": lambda m=None, toplantiya=False: (m or motor, None, 1.0), "gemini_var": lambda: gemini_acik, "gemini_izinli": lambda toplantiya=False: gemini_acik,
         "gemini_oku": lambda metin, **a: (n["ses_basladi"](a.get("kayit")), CALAN.append(("gemini", metin, a.get("ses"), a.get("uslup"))), True)[2], "etiket_sil": lambda m: m, "kisilik": lambda: {},
         "pocket_oku": lambda metin, **a: (CALAN.append(("pocket", metin) if not str(a.get("ses") or "").startswith("en:") else ("pocket", metin, a["ses"])), True)[1] if pocket else False, "ARAYUZ_DILI": "tr",
         "AYAR": {"piper_python": "/x", "piper_model": "/y"} if piper is not None else {},
         "piper_oku": lambda metin, *a, **k: (CALAN.append(("piper", metin)), True)[1] if piper else False, "piper_hiz": lambda: 1.0, "SES_TABAN_HIZ": 180, "print": lambda *a, **k: None, "time": time, "os": os,
         "gemini_onceden_var": lambda m, s_: m in onceden, "pocket_var": lambda: pocket is not None, "pocket_ses_adi": lambda v: v, "pocket_varsayilan": lambda: "tr:yerel"}
    n.update(ek or {})
    exec(compile(ast.Module(fn, []), "brifing-ses.py", "exec"), n)
    threading.Thread(target=n["_ses_isci"], daemon=True).start()
    for _ in range(100):
        if len(CALAN) >= bekle: break
        time.sleep(0.01)
    return list(CALAN)
c = deneme(True)
ok(f"Gemini açık: tepki → afplay, Gemini parçası → Gemini (sesi ve üslubuyla), düz metin → Mac: {c}",
   c == [("afplay", "/tepki.caf"), ("gemini", "Gemini cümlesi.", "Charon", "dostça"), ("mac", "Mac cümlesi.")])
c = deneme(False)
ok(f"Gemini yok: Gemini parçası Mac sesiyle okunur, hiçbir parça afplay'e dosya diye gitmez: {c}",
   c == [("afplay", "/tepki.caf"), ("mac", "Gemini cümlesi."), ("mac", "Mac cümlesi.")])
# v0.80.8: kuyrukta bekleyen aynı ses ve üsluptaki Gemini parçaları tek istekte; ses ya da üslup değişince ayrı; 600 karakter sınırı
c = deneme(True, q=[("g", "Bir.", "Charon", "u"), ("g", "İki.", "Charon", "u"), ("g", "Üç.", "Charon", "u2"), ("g", "Dört.", "Kore", "u2")], bekle=3)
ok(f"birleştirme: aynı ses+üslup tek istek, değişince ayrı: {c}", c == [("gemini", "Bir. İki.", "Charon", "u"), ("gemini", "Üç.", "Charon", "u2"), ("gemini", "Dört.", "Kore", "u2")])
uzun = "x" * 350 + "."
c = deneme(True, q=[("g", uzun, "Charon", "u"), ("g", uzun, "Charon", "u"), ("g", "Son.", "Charon", "u")], bekle=2)
ok(f"birleştirme sınırı (600 karakter): {[len(x[1]) for x in c]}", [len(x[1]) for x in c] == [351, 356])
# S93: yerel ses Pocket — okuyabilirse Pocket, okuyamazsa Mac sesi (Piper denenmez; sıra Pocket → Mac → Piper); Gemini parçası Gemini yoksa düz metin olur
q3 = lambda: [("dosya", "/tepki.caf"), ("g", "Gemini cümlesi.", "Charon", "dostça"), "Yerel cümle."]
c = deneme(False, motor="pocket", q=q3(), pocket=True)
ok(f"Pocket: tepki → afplay, metinler → Pocket: {c}", c == [("afplay", "/tepki.caf"), ("pocket", "Gemini cümlesi."), ("pocket", "Yerel cümle.")])
c = deneme(False, motor="pocket", q=q3(), pocket=False, piper=True)
ok(f"Pocket okuyamadı → Mac sesi, Piper kurulu olsa da (sıra Pocket → Mac → Piper): {c}", c == [("afplay", "/tepki.caf"), ("mac", "Gemini cümlesi."), ("mac", "Yerel cümle.")])
c = deneme(False, motor="pocket", q=q3(), pocket=False)
ok(f"Pocket okuyamadı, Piper yok → Mac sesi: {c}", c == [("afplay", "/tepki.caf"), ("mac", "Gemini cümlesi."), ("mac", "Yerel cümle.")])
# v0.101.3: ("en", metin, ses) İngilizce cümle → kişiliğin İngilizce Pocket sesi; okuyamazsa düz metin olarak yerel sese (Mac) düşer
c = deneme(False, motor="pocket", q=[("en", "Happy to help.", "en:michael"), "Türkçe cümle."], bekle=2, pocket=True)
ok(f"İngilizce parça → Pocket İngilizce sesi, Türkçe parça → Pocket: {c}", c == [("pocket", "Happy to help.", "en:michael"), ("pocket", "Türkçe cümle.")])
c = deneme(False, motor="mac", q=[("en", "Happy to help.", "en:michael"), ("dosya", "/tepki.caf")], bekle=2, pocket=False)
ok(f"İngilizce ses okuyamadı → Mac sesi (düz metin), sonraki öğe yerinde: {c}", c == [("mac", "Happy to help."), ("afplay", "/tepki.caf")])
# v0.95.0: duyulan ilk ses — bekleyen metin çalmaya başlayınca (Gemini birleşik okumada ikinci cümle de) çağrı bir kez; çalmayan metnin çağrısı gelmez
CAL = {}
bk = lambda ad: (ad[:40], lambda t: CAL.setdefault(ad, t), time.time())
c = deneme(True, q=[("g", "Bir.", "Charon", "u"), ("g", "İki.", "Charon", "u"), "Mac cümlesi."], bekle=2, bek=[bk("Bir."), bk("İki."), bk("Mac cümlesi."), bk("Hiç çalmayan.")])
time.sleep(0.05)
ok(f"çalma anı: Gemini (birleşik) ve Mac sesinde bekleyen metinler çağrıldı, çalmayan çağrılmadı: {sorted(CAL)}", sorted(CAL) == ["Bir.", "Mac cümlesi.", "İki."])
# v0.127: sesi önceden istenmiş parçaya arkadaki parçalar eklenmez (önceden alınan boşa gitmesin)
c = deneme(True, q=[("g", "Bir.", "Charon", "u"), ("g", "İki.", "Charon", "u")], bekle=2, onceden=("Bir.",))
ok(f"önceden istenmiş parça tek başına: {c}", c == [("gemini", "Bir.", "Charon", "u"), ("gemini", "İki.", "Charon", "u")])
# v0.127: ("yerel", metin) sistem uyarısı → kişiliğin yerel sesi (Pocket), Gemini açık olsa da; Pocket yoksa Mac sesi
c = deneme(True, q=[("yerel", "Uyarı.")], bekle=1, pocket=True)
ok(f"uyarı yerel sesle (Pocket): {c}", c == [("pocket", "Uyarı.")])
c = deneme(True, motor="gemini", q=[("yerel", "Uyarı."), ("g", "Sonra.", "Charon", "u")], bekle=2)
ok(f"Pocket yoksa uyarı Mac sesiyle, sonraki Gemini parçası Gemini'yle: {c}", c == [("mac", "Uyarı."), ("gemini", "Sonra.", "Charon", "u")])
# v0.127: Gemini okuyamadı ve günlük sınır doldu (gemini_izinli artık False) → kişiliğin yerel sesi (Pocket), Mac değil
IZ = {"v": True}
c = deneme(True, motor="gemini", q=[("g", "Sınırda.", "Charon", "u")], bekle=1, pocket=True,
           ek={"gemini_izinli": lambda toplantiya=False: IZ["v"], "gemini_oku": lambda metin, **a: IZ.__setitem__("v", False),
               "kisilik_sesi": lambda m=None, toplantiya=False: (m or ("gemini" if IZ["v"] else "pocket"), None, 1.0)})
ok(f"sınır dolunca Pocket'e döner: {c}", c == [("pocket", "Sınırda.")])
# v0.127: ses_sonraki_hazirla — kuyruk başındaki Gemini parçaları birleşip sesi önceden istenir
ON = []
n = {"SES": {"q": [("g", "Bir.", None, "u"), ("g", "İki.", None, "u"), "düz"]}, "SES_K": threading.Condition(), "GEMINI_BIRLESIK_EN_COK": 600, "gemini_izinli": lambda toplantiya=False: True,
     "kisilik_sesi": lambda m=None, toplantiya=False: ("gemini", "Kore", 1.0), "gemini_onceden": lambda m, s_, u: ON.append((m, s_, u)), "gemini_onceden_var": lambda m, s_: False}
exec(compile(ast.Module(fn, []), "brifing-ses.py", "exec"), n); n["ses_sonraki_hazirla"]()
ok(f"sıradaki hazırlanır: birleşik metin + kişiliğin sesi ({ON}, kuyruk {n['SES']['q']})", ON == [("Bir. İki.", "Kore", "u")] and n["SES"]["q"] == [("g", "Bir. İki.", None, "u"), "düz"])
# v0.127: Gemini ilk sesi beklenirken (işçi parçayı aldı, kuyruk boş, çalıcı yok) ses_caliyor True kalmalı. Eskiden False dönüyordu: üçlü sohbet önceki söz
# bitti sanıp sıradakini erken sıraya koyuyor, "çaldı" bildirimi 3 sn içinde gelmeyince canli/uclu.jsonl bosluk_ms ~3000 yazılıyordu (gerçek boşluk 0,6–1 sn).
sh = ast.parse(open(os.path.join(KOD, "aktarici", "sohbet.py"), encoding="utf-8").read())
fs = [f for f in sh.body if isinstance(f, ast.FunctionDef) and f.name == "ses_caliyor"]
fb = [f for f in agac.body if isinstance(f, ast.Assign) and any(getattr(t, "id", "") == "SES_MESGUL_SN" for t in f.targets)]
class Calan:  # sahte çalıcı süreci: bitene kadar poll() None
    def __init__(self, sn): self.son = time.time() + sn
    def poll(self): return None if time.time() < self.son else 0
def g_oku(metin, kayit=None, **a):  # gecikmeli Gemini: 0,4 sn ilk ses, 0,5 sn çalma
    time.sleep(0.4); kayit["p"] = Calan(0.5); n2["ses_basladi"](kayit); time.sleep(0.5); return True
n2 = {"SES": {"q": [], "isci": True, "kes": 0, "bek": []}, "SES_K": threading.Condition(), "GEMINI_BIRLESIK_EN_COK": 600, "os": os, "time": time, "print": lambda *a, **k: None,
      "kisilik_sesi": lambda m=None, toplantiya=False: ("gemini", "Kore", 1.0), "gemini_izinli": lambda toplantiya=False: True, "gemini_oku": g_oku, "etiket_sil": lambda m: m,
      "kisilik": lambda: {}, "ts_caliyor": lambda: False, "gemini_onceden_var": lambda m, s_: False}
exec(compile(ast.Module(fn + fs + fb, []), "brifing-ses.py", "exec"), n2)
threading.Thread(target=n2["_ses_isci"], daemon=True).start()
def koy2(m, cal=None):
    with n2["SES_K"]:
        n2["SES"]["q"].append(("g", m, "Kore", None))
        if cal: n2["SES"]["bek"].append((n2["_cal_anahtar"](("g", m)), cal, time.time()))
        n2["SES_K"].notify()
koy2("Birinci söz burada."); time.sleep(0.2)
ok("ilk ses beklenirken (kuyruk boş, çalıcı yok) ses_caliyor True", n2["ses_caliyor"]() is True)
while n2["ses_caliyor"](): time.sleep(0.02)  # üçlü sohbet: önceki söz bitince sıradakini koyar (kisilik.py oku, uclu-sahne.py _sahne_oku_satir)
t_bos = time.time(); bas = {}; koy2("İkinci söz burada.", cal=lambda t: bas.setdefault("t", t))
t1 = time.time()
while time.time() - t1 < 3 and not bas: time.sleep(0.02)
bosluk = round(((bas.get("t") or time.time()) - t_bos) * 1000)
ok(f"üçlü boşluk ölçümü gerçek ilk ses gecikmesi (≈ 400 ms, 3000 değil): {bosluk} ms", 300 <= bosluk <= 800)
time.sleep(1.2); ok("okuma bitince ses_caliyor False", n2["ses_caliyor"]() is False)
print("ses-kuyruk: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
