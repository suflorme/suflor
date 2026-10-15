#!/usr/bin/env python3
# Tepki sesleri (v0.43.0, aktarici/brifing-ses.py tepki_*): tepki.json kütüphanesinden cevap başındaki tetiğe ("Vay!", "Haha,") klip seçilir, kalan
# metin ayrılır; aynı türün söyleyişleri arasında son 8 klip yeniden seçilmez; kütüphane yoksa / ayar kapalıysa / sistem sesi uymuyorsa klip yok.
# Gerçek ses dosyası gerekmez (boş dosyalar); SUFLOR_TEST_TEPKI sistem sesi denetimini atlar.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tepki.py
import os, re, sys, json, time, shutil, tempfile, subprocess, collections, threading
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-tepki-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
lib = os.path.join(T, "v2"); os.makedirs(os.path.join(lib, "saskinlik")); os.makedirs(os.path.join(lib, "gulme")); os.makedirs(os.path.join(lib, "dusunme"))
L = [("saskinlik-vay-1", "saskinlik", "Vay!", ["vay"]), ("saskinlik-vay-be-1", "saskinlik", "Vay be!", ["vay be"]), ("saskinlik-hadi-ya-1", "saskinlik", "Hadi ya!", ["hadi ya"]),
     ("gulme-haha-1", "gulme", "Haha.", ["haha"]), ("gulme-kikir-1", "gulme", "(kıkırdama)", []), ("dusunme-himm-1", "dusunme", "Hımm.", []), ("dusunme-himm-2", "dusunme", "Hmm.", [])]
for i, tur, m, tt in L: open(os.path.join(lib, tur, i + ".wav"), "w").close()
json.dump({"surum": 2, "tepkiler": [{"id": i, "tur": tur, "metin": m, "tetik": tt, "dosya": f"{tur}/{i}.wav"} for i, tur, m, tt in L]}, open(os.path.join(lib, "tepki.json"), "w"), ensure_ascii=False)
os.environ["SUFLOR_TEST_TEPKI"] = "1"
src = open(os.path.join(K, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
g = {"os": os, "re": re, "json": json, "time": time, "subprocess": subprocess, "collections": collections, "threading": threading, "AYAR": {"tepki_sesleri": lib},
     "SES": {"q": [], "isci": True}, "SES_K": threading.Condition(), "piper_acik": lambda: False, "_ses_isci": lambda: None}
exec(src[src.index("# Tepki sesleri (v0.43.0"):src.index("# Okunan metinde görülen bilinmeyen yabancı sözcükler")], g)
ad = lambda k: os.path.basename(k) if k else None
k, m = g["tepki_ayir"]("Vay! Bütçe iki katına çıkmış.")
bak(f"'Vay!' → saşkınlık klibi + kalan metin ({ad(k)} · {m!r})", k and "/saskinlik/" in k and m == "Bütçe iki katına çıkmış.")
k, m = g["tepki_ayir"]("Vay be, bunu beklemiyordum.")
bak(f"iki sözcüklü tetik ({ad(k)} · {m!r})", k and "/saskinlik/" in k and m == "Bunu beklemiyordum.")
k, m = g["tepki_ayir"]("Haha, bu gerçekten komikti.")
bak(f"'Haha,' → gülme türü (kıkırdama da olabilir) ({ad(k)})", k and "/gulme/" in k and m == "Bu gerçekten komikti.")
k, m = g["tepki_ayir"]("Vay!")
bak("yalnız tetik → yalnız klip, metin boş", k and m == "")
k, m = g["tepki_ayir"]("Toplantı yarın saat onda.")
bak("tetiksiz cümle dokunulmaz", k is None and m == "Toplantı yarın saat onda.")
k, m = g["tepki_ayir"]("Vaybe sonra konuşuruz.")
bak("tetiğe benzeyen ama noktalamasız başlangıç dokunulmaz", k is None)
s = [ad(g["tepki_sec"]("saskinlik")) for _ in range(9)]
bak(f"aynı klip art arda yok (3 söyleyiş, 9 seçim: {s[:4]}…)", all(a != b for a, b in zip(s, s[1:])))
bak("düşünme türü (bekleme) seçilir", "/dusunme/" in (g["tepki_sec"]("dusunme") or ""))
g["AYAR"]["tepki_sesi"] = False
bak("ayar tepki_sesi: false → klip yok", g["tepki_ayir"]("Vay! Tamam.")[0] is None)
g["AYAR"]["tepki_sesi"] = True; g["AYAR"]["tepki_sesleri"] = os.path.join(T, "yok"); g["TEPKI"]["t"] = 0
bak("kütüphane yok → klip yok, metin aynen", g["tepki_ayir"]("Vay! Tamam.") == (None, "Vay! Tamam."))
del os.environ["SUFLOR_TEST_TEPKI"]; g["AYAR"]["tepki_sesleri"] = lib; g["TEPKI"].update(t=0, ses_t=0); g["AYAR"]["tepki_ses_adi"] = "OlmayanSes"
bak("sistem sesi kütüphanenin sesi değil → klip yok", g["tepki_sec"]("saskinlik") is None)
shutil.rmtree(T, ignore_errors=True)
print("tepki: ✓ hepsi geçti" if not hata else f"tepki: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
