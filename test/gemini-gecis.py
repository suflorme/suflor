#!/usr/bin/env python3
# "Gemini sesiyle konuş" geçişi (v0.98.0, S104; aktarici/gemini-ses.py gemini_gecis_komut, gemini_gecis_acik, gemini_kapsam; Konuş yolunda bas-konus.py _konus_sor):
# kalıplar yalnız tüm cümle komutken tutar; açılınca toplantı dışında da Gemini izinli; süre dolunca, "yerel sese dön" deyince ya da iki model de dolunca
# yerel ses; anahtar yoksa ya da gizli toplantıda açılmaz. Google'a gidilmez (~0 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gemini-gecis.py
import ast, os, re, sys, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "gemini-ses.py"), encoding="utf-8").read())
AD = {"gemini_gecis_acik", "gemini_gecis_komut", "gemini_kapsam", "gemini_izinli"}
sec = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in AD) or (isinstance(d, ast.Assign) and any(getattr(t, "id", "") in ("GEMINI_GECIS", "GEMINI_GECIS_SN", "GECIS_AC_RX", "GECIS_KAPAT_RX") for t in d.targets))]
D = {"var": True, "model": "m", "gizli": False}
ns = {"re": re, "time": time, "print": lambda *a, **k: None, "AYAR": {}, "_t": lambda a, b: a, "gemini_var": lambda: D["var"], "gemini_model": lambda: D["model"], "gizli_acik": lambda: D["gizli"]}
exec(compile(ast.Module(sec, []), "gemini-ses.py", "exec"), ns)
k, acik, izin = ns["gemini_gecis_komut"], ns["gemini_gecis_acik"], ns["gemini_izinli"]
for m in ["Gemini sesiyle konuş.", "Gemini sesine geç", "Gemini'ye geç.", "Gemini sesiyle konuşur musun?"]:
    ok(f"açma kalıbı tutar: {m!r}", ns["GECIS_AC_RX"].search(m) is not None)
for m in ["Yerel sese dön.", "Kendi sesine dön", "Gemini'yi kapat.", "Normal sese geç."]:
    ok(f"kapatma kalıbı tutar: {m!r}", ns["GECIS_KAPAT_RX"].search(m) is not None)
for m in ["Gemini sesiyle konuşmanın maliyeti ne kadar?", "Dün Gemini'ye geçmeyi konuştuk, karar ne oldu?", "Toplantıda yerel sese döndük mü?", "Gemini nedir?"]:
    ok(f"soru komut sayılmaz: {m!r}", k(m) is None)
ok("başta kapalı: toplantı dışında Gemini izinli değil", not izin() and izin(toplantiya=True))
c = k("Gemini sesiyle konuş."); ok(f"açılınca onay ve toplantı dışında izin ({c!r})", "15 dakika" in c and acik() and izin())
ns["GEMINI_GECIS"]["bitis"] = time.time() - 1; ok("süre dolunca kendiliğinden yerel ses", not izin() and not acik())
k("Gemini'ye geç"); c = k("Yerel sese dön."); ok(f"süre dolmadan 'yerel sese dön' hemen kapatır ({c!r})", "döndüm" in c and not izin())
ok("kapalıyken 'yerel sese dön': zaten yerel", "Zaten" in k("Yerel sese dön"))
k("Gemini sesine geç"); D["model"] = None; ok("iki model de dolunca geçiş biter", not izin() and not acik())
ok("sınır doluyken açılmaz, söyler", "sınırı doldu" in k("Gemini sesine geç") and not acik()); D["model"] = "m"
D["var"] = False; ok("anahtar yoksa açılmaz", "kullanılamıyor" in k("Gemini sesine geç") and not acik()); D["var"] = True
D["gizli"] = True; ok("gizli toplantıda açılmaz", "kullanılamıyor" in k("Gemini sesine geç") and not acik()); D["gizli"] = False
ns["AYAR"]["gemini_kapsam"] = "hepsi"; ok("ayarda 'hepsi' seçiliyse geçişten bağımsız izinli", izin()); ns["AYAR"].pop("gemini_kapsam")
b = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ok("Konuş yolunda komut Claude'a gitmeden yakalanıyor, karşı taraf geçiremez", "gemini_gecis_komut(" in b and 'tur.get("kaynak") not in ("karsi", "moderator") and not tur.get("karsi")' in b)
print("gemini geçiş: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
