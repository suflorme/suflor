#!/usr/bin/env python3
# Komşu ses (v0.240.0, S307; whisper-isci.py komsu_sozcukler/komsu_bas/komsu_coz, aktarici/whisper-hat.py komsu_pcm/k.komsu): karşı kanalın dil kilitli
# kısa parçası önceki parçanın son 6 sn sesiyle birlikte çözülür, önceki metin hizalanıp çıkarılır; boş/şüpheli sonuçta tek başına çözüme dönülür.
# Sahte whisper.cpp yanıtıyla, gerçek model yok (~0 sn). Gerçek ölçüm: _yedek/test-araclari/gercek-toplanti/komsu-ses/ (canli-olc.py).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/komsu-ses.py      (kaldı → çıkış 1)
import os, sys, re, base64, importlib.util
sys.dont_write_bytecode = True
import numpy as np
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
sp = importlib.util.spec_from_file_location("wi", os.path.join(KOD, "whisper-isci.py")); wi = importlib.util.module_from_spec(sp); sp.loader.exec_module(wi)
def yanit(sozler, dil_seg=None):  # sozler: [(sözcük, başlangıç, bitiş)] → tek bölümlü verbose_json
    return {"segments": [{"text": " " + " ".join(w for w, _, _ in sozler), "avg_logprob": -0.3, "no_speech_prob": 0.01,
                          "words": [{"word": " " + w, "start": a, "end": b, "probability": 0.9} for w, a, b in sozler]}]}
class Sahte:
    def __init__(s, r): s.r = r; s.n = 0; s.uzunluk = None
    def istek(s, a, language=None, initial_prompt=None): s.n += 1; s.uzunluk = len(a); s.dil = language; s.istem = initial_prompt; return s.r
SR = 16000; onc = np.zeros(6 * SR, np.int16).tobytes(); parca = np.zeros(int(1.5 * SR), np.float32)
p = {"komsu_pcm": base64.b64encode(onc).decode(), "komsu_metin": "bunu yarın sabah ekiple konuşalım", "dil": "tr", "dil_kilit": True}
# önceki parça 0–6 sn, boşluk 6–6,3, kısa parça 6,3–7,8
ONCEKI = [("bunu", 3.0, 3.4), ("yarın", 3.5, 3.9), ("sabah", 4.0, 4.4), ("ekiple", 4.5, 5.0), ("konuşalım.", 5.1, 5.9)]
m = Sahte(yanit(ONCEKI + [("İnşallah.", 6.4, 7.2)]))
r = wi.komsu_coz(m, parca, p, np)
ok("önceki metin çıkarılır, kısa parçanın sözü kalır", r and r["text"] == "İnşallah.")
ok("istek: önceki 6 sn + 0,3 sn boşluk + parça, dil sabit, istemsiz", m.uzunluk == 6 * SR + int(0.3 * SR) + len(parca) and m.dil == "tr" and m.istem == "")
ok("sonuç işaretli (komsu) ve tek bölüm", r and r.get("komsu") is True and len(r["segments"]) == 1 and r["segments"][0]["kp"] == 0.9)
# hizalama: önceki parçanın son sözcüğü sınırın ötesine taşmışsa da çıkarılır (zamanla kesmek "konuşalım"ı taşırıyordu)
m = Sahte(yanit(ONCEKI[:-1] + [("konuşalım.", 5.6, 6.5), ("Evet.", 6.6, 7.0)]))
r = wi.komsu_coz(m, parca, p, np); ok("sınırı aşan önceki sözcük hizalamayla atılır", r and r["text"] == "Evet.")
# eşleşme yoksa zaman sınırı
m = Sahte(yanit([("bambaşka", 2.0, 3.0), ("bir", 3.1, 3.5), ("söz", 3.6, 4.0), ("Yarın", 6.5, 7.0), ("bakarız.", 7.0, 7.6)]))
r = wi.komsu_coz(m, parca, dict(p, komsu_metin="hiç eşleşmeyen metin burada"), np); ok("eşleşme yoksa zaman sınırından sonrası", r and r["text"] == "Yarın bakarız.")
# boş / uydurma / hızlı → None (tek başına çözüme dönülür)
m = Sahte(yanit(ONCEKI)); ok("kısa parçada söz yoksa None", wi.komsu_coz(m, parca, p, np) is None)
m = Sahte(yanit(ONCEKI + [(w, 6.4 + i * 0.1, 6.5 + i * 0.1) for i, w in enumerate("bir iki üç dört beş altı yedi sekiz dokuz on".split())]))
ok("saniyede 6 sözcükten hızlı sonuç None", wi.komsu_coz(m, parca, p, np) is None)
m = Sahte(yanit(ONCEKI + [("İzlediğiniz", 6.4, 6.8), ("için", 6.8, 7.0), ("teşekkür", 7.0, 7.3), ("ederim.", 7.3, 7.7)]))
ok("uydurma kalıbı None", wi.komsu_coz(m, parca, p, np) is None)
ok("boş komşu ses None", wi.komsu_coz(Sahte(yanit(ONCEKI)), parca, dict(p, komsu_pcm=""), np) is None)
# kaynak denetimi: işçi yalnız cpp + kilitli + komsu_pcm iken dener, hata/None'da tek başına çözer; hat yalnız karşı kanalda, aynı toplantıda, 30 sn içinde gönderir
isci = open(os.path.join(KOD, "whisper-isci.py"), encoding="utf-8").read(); hat = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
ok("işçi: koşul cpp + komsu_pcm + dil_kilit", 'if CPP and p.get("komsu_pcm") and p.get("dil_kilit") and p.get("dil") in ("tr", "en"):' in isci)
ok("işçi: None ya da hata → tek başına çözüm", "if r is None: r = coz(a, language=None if oto" in isci and 'except Exception as e: r = None; sys.stderr.write(f"komşu ses' in isci)
ok("işçi: çıktıda komsu işareti", '**({"komsu": True} if r.get("komsu") else {})' in isci)
ok("hat: yalnız karşı kanal, aynı başlık, 30 sn, ayar komsu_ses", re.search(r'is_\["kanal"\] == "karsi" and ko and AYAR\.get\("komsu_ses", True\) is not False and ko\[3\] == is_\["baslik"\] and -1 <= is_\["t0"\] - ko\[0\] <= KOMSU_ARA_SN', hat) is not None)
ok("hat: komşu yalnız kilit bloğunda (kısa parça) eklenir", hat.index('istek["komsu_pcm"]') > hat.index('istek["dil"] = bd; istek["dil_kilit"] = True'))
ok("hat: her karşı sonucu sonraki parçanın komşusu olur (son 6 sn)", 'k.komsu = (is_["t1"], bytes(is_["pcm"][-int(KOMSU_ONC_SN * 32000):]), metin, is_["baslik"])' in hat)
ok("hat: parcalar.jsonl'a komsu yazılır", '**({"komsu": True} if is_.get("komsu") else {})' in hat)
print(f"\n{'TAMAM' if not HATA else 'KALDI: ' + ', '.join(HATA)}"); sys.exit(1 if HATA else 0)
