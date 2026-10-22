#!/usr/bin/env python3
# Toplantıda asistanın sesi (v0.113.0; aktarici/toplantiya-ses.py toplanti_ses_motoru, ses_komut, SES_KOMUT_RX): ayar toplanti_ses (kisilik | gemini | pocket | mac)
# katılımcıların duyduğu sesi seçer; Gemini kullanılamıyorsa Pocket, o da yoksa Mac. Toplantıda tüm cümle komutsa ("tamam, Pocket sesine dön",
# "Gemini sesine geç", Whisper'ın "paket"i) ayar kalıcı değişir; toplantı dışında v0.98.0 Gemini geçişine gider. Model yüklenmez, Google'a gidilmez (~0 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti-ses.py
import ast, os, re, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
agac = ast.parse(open(os.path.join(KOD, "aktarici", "toplantiya-ses.py"), encoding="utf-8").read())
sec = [d for d in agac.body if (isinstance(d, ast.FunctionDef) and d.name in ("toplanti_ses_motoru", "ses_komut")) or
       (isinstance(d, ast.Assign) and any(getattr(t, "id", "") == "SES_KOMUT_RX" for t in d.targets))]
D = {"pocket": True, "gemini": True, "model": "m", "top": True, "kisi": {"ad": "Deniz", "ses": "gemini:Charon", "yerel_ses": "pocket:wite:male_1"}, "gecis": []}
AYAR = {}
def ayar_yaz(deg): AYAR.update(deg); return {"ok": True}
ns = {"re": re, "print": lambda *a, **k: None, "AYAR": AYAR, "STATE": {}, "_t": lambda a, b: a, "kisilik": lambda: D["kisi"], "pocket_var": lambda: D["pocket"],
      "pocket_ses_adi": lambda s: s.split(":", 1)[1] if s and s.startswith("pocket:") else None, "pocket_varsayilan": lambda: "wite:female_2",
      "gemini_izinli": lambda toplantiya=False: D["gemini"] and toplantiya, "gemini_model": lambda: D["model"], "toplanti_var": lambda: D["top"],
      "kisilik_sesi": lambda toplantiya=False: ("gemini", "Charon", 1.0), "ayar_yaz": ayar_yaz, "GEMINI_GECIS": {"bitis": 5.0},
      "gemini_gecis_komut": lambda m: D["gecis"].append(m) or ("geçiş:" + m)}
exec(compile(ast.Module(sec, []), "toplantiya-ses.py", "exec"), ns)
mot, kom, rx = ns["toplanti_ses_motoru"], ns["ses_komut"], ns["SES_KOMUT_RX"]
# ses seçimi
ok("varsayılan (kisilik): kişiliğin sesi — eskisi gibi Gemini", mot() == ("gemini", "Charon"))
AYAR["toplanti_ses"] = "pocket"; ok("pocket: kişiliğin yerel Pocket sesi", mot() == ("pocket", "wite:male_1"))
D["kisi"] = {"ad": "X", "ses": "gemini:Kore"}; ok("pocket, kişilikte yerel ses yok: Pocket varsayılanı", mot() == ("pocket", "wite:female_2"))
D["pocket"] = False; ok("pocket kurulu değil: Mac sesi", mot() == ("mac", None)); D["pocket"] = True
AYAR["toplanti_ses"] = "gemini"; ok("gemini: kişiliğin Gemini sesi", mot() == ("gemini", "Kore"))
D["gemini"] = False; ok("gemini kullanılamıyor (anahtar/gizli): Pocket", mot()[0] == "pocket"); D["gemini"] = True
AYAR["toplanti_ses"] = "mac"; ok("mac: Mac sesi", mot() == ("mac", None))
# komut kalıbı
for m in ["Tamam, Pocket sesine dön.", "tamam paket sesine dön.", "Pocket'a geç", "Pakıt sesine geç lütfen", "Gemini sesine geç.", "Gemini sesiyle konuş", "Mac sesine geçer misin?", "Yerel sese dön"]:
    ok(f"komut: {m!r}", rx.search(m) is not None)
for m in ["Paketi geri gönder.", "Pocket sesi güzel değil mi?", "Gemini kotası doldu, Pocket sesine dön demem lazım", "toplantıda tamam paket sesine dön diyebilmem lazım.", "Gemini nedir?"]:
    ok(f"komut değil: {m!r}", rx.search(m) is None)
# toplantıda: ayar kalıcı değişir
D["kisi"] = {"ad": "Deniz", "ses": "gemini:Charon", "yerel_ses": "pocket:wite:male_1"}; AYAR["toplanti_ses"] = "kisilik"
c = kom("Tamam, Pocket sesine dön."); ok(f"toplantıda Pocket'a geçer, ayar yazılır, Gemini geçişi kapanır ({c!r})", AYAR["toplanti_ses"] == "pocket" and "Pocket sesiyle" in c and ns["GEMINI_GECIS"]["bitis"] == 0.0)
ok("aynı komut ikinci kez: zaten", "Zaten Pocket" in kom("Pocket'a geç"))
c = kom("Gemini sesine geç."); ok(f"Gemini'ye döner ({c!r})", AYAR["toplanti_ses"] == "gemini" and "Gemini sesiyle" in c)
D["model"] = None; c = kom("Mac sesine geç"); ok("Mac'e geçer", AYAR["toplanti_ses"] == "mac")
c = kom("Gemini sesine geç"); ok(f"Gemini sınırı doluysa değişmez, söyler ({c!r})", AYAR["toplanti_ses"] == "mac" and "sınırı doldu" in c); D["model"] = "m"
D["pocket"] = False; c = kom("Pocket sesine dön"); ok(f"Pocket kurulu değilse değişmez ({c!r})", AYAR["toplanti_ses"] == "mac" and "kurulu değil" in c); D["pocket"] = True
# toplantı dışında: Gemini geçişine gider
D["top"] = False; D["gecis"].clear(); kom("Pocket sesine dön"); kom("Gemini sesiyle konuş")
ok("toplantı dışında Gemini geçişi (yerel sese dön / Gemini sesiyle konuş)", D["gecis"] == ["yerel sese dön", "gemini sesiyle konuş"] and AYAR["toplanti_ses"] == "mac")
ok("komut değilse geçiş kalıbına bırakılır", kom("Gemini'yi kapat.") == "geçiş:Gemini'yi kapat.")
# bağlantılar
b = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read(); r = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
ok("Konuş yolunda kullanıcının toplantıdaki kendi hitabı da komut olur (otonom tur), karşı taraf olmaz",
   'ses_komut(' in b and '(not tur.get("otonom") or tur.get("kaynak") == "hitap")' in b and 'not in ("karsi", "moderator") and not tur.get("karsi")' in b)
ok("ayar panoda: toplanti_ses (kisilik|gemini|pocket|mac)", '"toplanti_ses": ("sec", "kisilik", ("kisilik", "gemini", "pocket", "mac"))' in r)
ok("durumda Pocket görünür (seslendirme.motor) ve toplantı sesi ayrı", 'motor="pocket") if pocket_acik()' in r and "toplanti=toplanti_ses_motoru()[0]" in r)
print("toplantı sesi: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
