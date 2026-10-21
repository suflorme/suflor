#!/usr/bin/env python3
# İngilizce cümle İngilizce sesle (v0.101.3, aktarici/brifing-ses.py okuma_dili / kisilik_en_sesi / seslendir): okunacak parçanın dili, İngilizce parçada
# Türkçe okunuş adımlarının (telaffuz: yabancı sözcük sözlüğü, kişilik okunuşu) atlanması, kuyruğa ("en", metin, ses) girmesi; kişilikte yerel_ses_en yoksa,
# Pocket kurulu değilse ya da ses Mac/Gemini ise bugünkü yol. Taklit ortam, ses çalınmaz (~1 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ingilizce-ses.py
import ast, os, re, sys, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
src = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
cv = open(os.path.join(KOD, "aktarici", "ceviri.py"), encoding="utf-8").read()
ag = ast.parse(src); ad_ = {"okuma_dili", "kisilik_en_sesi", "seslendir"}
govde = [n for n in ag.body if (isinstance(n, ast.FunctionDef) and n.name in ad_) or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_DIL_EN", "_DIL_TR", "_DIL") for t in n.targets))]
TEL = []; K = {"k": {"yerel_ses": "pocket:wite:male_1", "yerel_ses_en": "pocket:en:michael"}, "motor": "pocket", "pocket": True}
ns = {"re": re, "time": time, "os": os, "AYAR": {"konusma": True}, "ARAYUZ_DILI": "tr", "SES": {"q": [], "isci": True}, "SES_K": threading.Condition(),
      "ton_ayikla": lambda m: (m, None), "ton_kur": lambda t: None, "gemini_izinli": lambda *a: False, "kisilik": lambda: K["k"],
      "kisilik_sesi": lambda *a, **k: (K["motor"], "wite:male_1", 1.0), "tepki_ayir": lambda m: (None, m), "etiket_sil": lambda m: m,
      "telaffuz": lambda m, mac=False: (TEL.append(m), m.replace("Sir", "sör"))[1], "kisilik_telaffuz": lambda m: (TEL.append(m), m.replace("Sir", "sör"))[1],
      "ses_duzen": lambda m, mac=True: m, "ses_durdur": lambda: None, "pocket_var": lambda: K["pocket"], "_cal_anahtar": lambda m: m,
      "pocket_ses_adi": lambda s: (s[7:] if s.startswith("pocket:") else s) if s.split(":")[-2:-1] in (["en"], ["wite"], ["alperiox"]) else None}
exec(cv[cv.index("_EN_SOZ ="):cv.index("def ceviri_ekle")], ns)
exec(compile(ast.Module(govde, []), "brifing-ses.py", "exec"), ns)
od = ns["okuma_dili"]
TABLO = [("Happy to help, Sir.", "en"), ("Fair enough, but an accent just means you speak more than one language.", "en"), ("OK, Sir.", "en"),
         ("I'll prepare it for your approval.", "en"), ("You have three meetings on Friday.", "en"),
         ("Tamam, hallettim.", "tr"), ("Toplantı saat onda.", "tr"), ("Executive Planning toplantısı yarın.", "tr"), ("Peki, Basecamp'e bakayım.", "tr"),
         ("Evet, gönderdim.", "tr")]
yanlis = [(m, b, od(m)) for m, b in TABLO if od(m) != b]
ok(f"okuma dili {len(TABLO) - len(yanlis)}/{len(TABLO)}" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
od("Happy to help, Sir."); ok("belirsiz kısa parça son 20 sn'deki dille (cevap cümle cümle gelir)", od("Right.") == "en")
ns["_DIL"].update(son=None, t=0); ok("belirsiz ve öncesi yoksa Türkçe", od("Right.") == "tr")
def sor(metin):
    ns["SES"]["q"].clear(); del TEL[:]; ns["_DIL"].update(son=None, t=0); ns["seslendir"](metin, kuyruk=True); return list(ns["SES"]["q"])
q = sor("Happy to help, Sir.")
ok(f"İngilizce cümle → ('en', metin, 'en:michael'), Türkçe okunuş yok (Sir okunuşu uygulanmadı): {q}", q == [("en", "Happy to help, Sir.", "en:michael")] and not TEL)
q = sor("Tamam Sir, hallettim.")
ok(f"Türkçe cümle → bugünkü yol (telaffuz uygulandı, düz metin): {q}", q == ["Tamam sör, hallettim."] and TEL)
K["k"] = dict(K["k"], yerel_ses_en=None); q = sor("Happy to help, Sir.")
ok(f"kişilikte yerel_ses_en yok → bugünkü yol: {q}", q == ["Happy to help, sör."]); K["k"]["yerel_ses_en"] = "pocket:en:michael"
K["pocket"] = False; q = sor("Happy to help, Sir."); K["pocket"] = True
ok(f"Pocket kurulu değil → bugünkü yol: {q}", q == ["Happy to help, sör."])
K["motor"] = "mac"; q = sor("Happy to help, Sir."); K["motor"] = "pocket"
ok(f"⚙ Ayarlar'da Mac sesi → dokunulmaz: {q}", q == ["Happy to help, sör."])
ns["ARAYUZ_DILI"] = "en"; q = sor("Happy to help, Sir."); ns["ARAYUZ_DILI"] = "tr"
ok(f"İngilizce arayüzde (beta) değişiklik yok: {q}", q == ["Happy to help, sör."])
print("ingilizce-ses: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata")); sys.exit(1 if HATA else 0)
