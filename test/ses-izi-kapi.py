#!/usr/bin/env python3
# Ses izi kapısı, gölge kip ("ben" kanalı; 2 Kasım): işçi parçayı 1,5 sn / 0,5 sn pencerelerle tarar ve benzerlikleri döndürür, aktarıcı eşik başına karar
# (gecir/kirp/at) hesaplayıp YALNIZ canli/ses-izi-kapi.jsonl'e yazar. Denetim: pencere sayısı · profil yoksa hesap yok · karşı kanalda hesap yok ·
# Whisper metni profil verilse de verilmese de AYNI (davranış değişmez) · ek süre ölçümü · karar mantığı · ayar kapalıyken dosya yok · kayıtta metin yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-izi-kapi.py      (kaldı → çıkış 1; whisper-venv + ECAPA gerekir, ~30 sn)
import base64, json, os, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: canlı kullanım koruması (gerçek model)

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = "/Users/Shared/Suflor/whisper-venv/bin/python"
MODEL = "/Users/Shared/Suflor/whisper-modeller/hub/models--suflor--whisper-large-v3-turbo-q8/snapshots/yerel"
ECAPA = "/Users/Shared/Suflor/ses-modeller/spkrec-ecapa-voxceleb/ecapa-mlx.npz"
if not (os.path.exists(VENV) and os.path.isdir(MODEL) and os.path.exists(ECAPA)): print("Whisper/ECAPA kurulu değil — atlandı"); sys.exit(0)
if sys.executable != VENV: os.execv(VENV, [VENV, "-I", os.path.abspath(__file__)])
import importlib.util, struct
import numpy as np
SR = 16000; T = tempfile.mkdtemp(prefix="suflor-kapi-")
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
def pcm(a): return base64.b64encode((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes()).decode()
def soyle(ses, metin):
    aiff, wav = os.path.join(T, "s.aiff"), os.path.join(T, "s.wav")
    subprocess.run(["say", "-v", ses, "-o", aiff, metin], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", aiff, wav], check=True, capture_output=True)
    b = open(wav, "rb").read(); i = b.find(b"data") + 8
    return np.concatenate([np.zeros(SR // 4), np.frombuffer(b[i:], np.int16).astype(np.float32) / 32768, np.zeros(SR // 4)])
_sp = importlib.util.spec_from_file_location("whisper_isci", os.path.join(KOD, "whisper-isci.py")); WI = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(WI)

# 1) pencere düzeni (modelsiz)
P = WI.kapi_pencereler
kontrol("0,5 sn parça tek pencere", len(P(SR // 2)) == 1)
kontrol("1,5 sn parça tek pencere", P(int(1.5 * SR)) == [(0, int(1.5 * SR))])
kontrol("2 sn parça 2 pencere, sona kadar kapsar", len(P(2 * SR)) == 2 and P(2 * SR)[-1][1] == 2 * SR)
kontrol("6 sn parça 10 pencere (0,5 sn adım)", len(P(6 * SR)) == 10 and all(e - b == int(1.5 * SR) for b, e in P(6 * SR)))
kontrol("1,8 sn: açıkta kalan kuyruk için sona hizalı pencere", len(P(int(1.8 * SR))) == 2 and P(int(1.8 * SR))[-1][1] == int(1.8 * SR))
kontrol("üst sınır", len(P(120 * SR)) == WI.KAPI_EN_COK)
sahte = lambda x: np.array([1.0, 0.0], np.float32)
kontrol("kapi_benzerlik: pencere başına tek sayı, 2 ondalık", WI.kapi_benzerlik(sahte, np.zeros(3 * SR, np.float32), np.array([1.0, 0.0], np.float32), np) == [1.0] * len(P(3 * SR)))

# 2) aktarıcı tarafı: whisper-hat.py'deki kapı bloğu yalıtılmış ad alanında (relay.py ad alanı taklidi)
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
blok = src[src.index("# --- Ses izi kapısı, gölge kip"):src.index("def kume_sifirla()")]
kanal_dir = os.path.join(T, "canli"); os.makedirs(kanal_dir)
def _log(ad, r):
    with open(os.path.join(kanal_dir, ad), "a", encoding="utf-8") as f: f.write(json.dumps(r, ensure_ascii=False) + "\n")
import base64 as b64m, math
def _iz_coz(b):
    r = b64m.b64decode(b); v = struct.unpack(f"<{len(r) // 2}e", r); n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
AYAR = {}; ODA = {"profil": None, "sn": 0.0, "yuklendi": True}
ns = dict(AYAR=AYAR, ODA=ODA, _log=_log, _iz_coz=_iz_coz, _oda_yol=lambda: os.path.join(T, "yok.json"), json=json, base64=b64m, struct=struct, math=math, time=time, os=os)
exec(compile(blok, "whisper-hat-kapi", "exec"), ns)
kar = ns["kapi_karar"]
k, pay = kar([0.30, 0.22, 0.10, 0.18], [0.15, 0.20, 0.25, 0.30])
kontrol("karar: 0.15 kirp (0.10 altta)", k["0.15"] == "kirp" and pay["0.15"] == 0.25)
kontrol("karar: 0.20 kirp, 0.25 kirp, 0.30 kirp", k["0.20"] == "kirp" and k["0.25"] == "kirp" and k["0.30"] == "kirp")
kontrol("karar: kırpılan pay 0.20'de 0.5, 0.30'da 0.75", pay["0.20"] == 0.5 and pay["0.30"] == 0.75)
k, pay = kar([0.5, 0.4], [0.15, 0.30]); kontrol("karar: hepsi üstte → gecir, pay 0", k == {"0.15": "gecir", "0.30": "gecir"} and pay["0.30"] == 0.0)
k, pay = kar([0.05, 0.1], [0.15, 0.30]); kontrol("karar: hiçbiri üstte → at, pay 1", k == {"0.15": "at", "0.30": "at"} and pay["0.30"] == 1.0)
kontrol("varsayılan eşikler", ns["kapi_esikler"]() == [0.15, 0.2, 0.25, 0.3])
AYAR["ses_izi_kapi_esikler"] = [0.4, 0.1]; kontrol("ayardan eşik listesi (sıralı)", ns["kapi_esikler"]() == [0.1, 0.4])
AYAR["ses_izi_kapi_esikler"] = "bozuk"; kontrol("bozuk eşik ayarı varsayılana döner", ns["kapi_esikler"]() == [0.15, 0.2, 0.25, 0.3]); AYAR.pop("ses_izi_kapi_esikler")
kontrol("profil yokken kapi_profil_b64 yok", ns["kapi_profil_b64"]() is None)
ODA["profil"] = [3.0, 4.0]; ODA["sn"] = 31.0
pb = ns["kapi_profil_b64"](); v = struct.unpack("<2e", b64m.b64decode(pb)); kontrol("profil birim vektör olarak kodlanır", abs(v[0] - 0.6) < 1e-2 and abs(v[1] - 0.8) < 1e-2)
ODA["profil"] = None

METIN = "Bugün toplantıda bütçe konusunu konuşacağız"  # kayıtta bulunmamalı
is_ = {"t0": 100.0, "t1": 106.0, "kapi_istendi": True, "kapi_profil_var": True}
j = {"kapi": [0.31, 0.22, 0.18, 0.05], "kapi_ms": 41, "atilan_harf": 7}
dosya = os.path.join(kanal_dir, "ses-izi-kapi.jsonl")
ns["kapi_kaydet"](is_, "satir", METIN, j)
satirlar = [json.loads(l) for l in open(dosya, encoding="utf-8")] if os.path.exists(dosya) else []
kontrol("kayıt yazıldı", len(satirlar) == 1)
r = satirlar[0] if satirlar else {}
kontrol("kayıt alanları", all(a in r for a in ("t", "kanal", "parca_sn", "profil", "pencere", "karar", "kirp_pay", "sonuc", "harf", "atilan_harf", "ek_ms", "mikrofon")) and r.get("kanal") == "ben" and r.get("profil") is True)
kontrol("harf = yazılan metnin harf sayısı, atılan harf işçiden", r.get("harf") == sum(c.isalpha() for c in METIN) and r.get("atilan_harf") == 7 and r.get("ek_ms") == 41)
kontrol("kayıtta metin yok (yalnız sayı/etiket)", METIN.split()[0] not in open(dosya, encoding="utf-8").read() and all(not isinstance(x, str) or len(x) < 12 for x in r.values() if not isinstance(x, (dict, list))))
ns["kapi_kaydet"](dict(is_, kapi_profil_var=False), "bos", "", {}); s2 = [json.loads(l) for l in open(dosya, encoding="utf-8")][-1]
kontrol("profil yoksa satır yalnız profil:false, pencere/karar yok", s2["profil"] is False and "pencere" not in s2 and "karar" not in s2)
n0 = len(open(dosya, encoding="utf-8").readlines()); AYAR["ses_izi_kapi"] = False
kontrol("ayar kapalıyken kapi_acik False", ns["kapi_acik"]() is False)
ns["kapi_kaydet"](is_, "satir", METIN, j); kontrol("ayar kapalıyken dosya yazılmaz", len(open(dosya, encoding="utf-8").readlines()) == n0); AYAR.pop("ses_izi_kapi")
ns["kapi_kaydet"](dict(is_, kapi_istendi=False), "satir", METIN, j); kontrol("istenmemiş parça (karşı kanal / bas-konuş) yazılmaz", len(open(dosya, encoding="utf-8").readlines()) == n0)

# 3) gerçek işçi: davranış değişmez + ek süre
p = subprocess.Popen([VENV, os.path.join(KOD, "whisper-isci.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_WHISPER_MODEL=MODEL, SUFLOR_ECAPA=ECAPA))
def sor(i, a, **ek):
    p.stdin.write(json.dumps(dict({"id": i, "pcm": pcm(a), "dil": "tr", "ana_dil": "tr", "kanal": "ben", "baslik": "d"}, **ek)) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
try:
    ilk = json.loads(p.stdout.readline()); kontrol("işçi hazır, ECAPA yüklü", ilk.get("hazir") and ilk.get("ecapa"))
    ecapa = WI.Ecapa(ECAPA, np, __import__("mlx.core", fromlist=["x"]))
    benim = soyle("Yelda", "Bugün toplantıda bütçe konusunu konuşacağız. Önce geçen çeyreğin rakamlarına bakalım, sonra yeni plana geçelim.")
    baska = soyle("Samantha", "Yesterday we talked about the new shipping rules and the warehouse schedule for next month.")
    prof = ecapa(benim); pb = base64.b64encode(prof.astype(np.float16).tobytes()).decode()
    sor("ısınma", benim)
    for ad, a in (("kendi sesim", benim), ("başka ses", baska)):
        r0 = sor("a", a); r1 = sor("b", a, kapi_profil=pb)
        kontrol(f"{ad}: profil verilince metin aynı ({(r0.get('text') or '')[:30]!r})", r0.get("text") == r1.get("text") and r0.get("atlanan") == r1.get("atlanan") and r0.get("dil") == r1.get("dil"))
        kontrol(f"{ad}: profilsiz istekte kapı alanı yok", "kapi" not in r0 and "kapi_ms" not in r0)
        n = len(WI.kapi_pencereler(len(a)))
        kontrol(f"{ad}: {len(a) / SR:.1f} sn → {n} pencere", isinstance(r1.get("kapi"), list) and len(r1["kapi"]) == n)
        print(f"   pencereler {r1.get('kapi')} · ek {r1.get('kapi_ms')} ms · işçi {r1.get('sn')} sn")
        if ad == "kendi sesim": ben_ort = float(np.mean(r1["kapi"])); ek_ms = r1.get("kapi_ms")
        else: oda_ort = float(np.mean(r1["kapi"]))
    kontrol("kendi sesim başka sesten yüksek benzerlik", ben_ort > oda_ort + 0.2)
    kontrol(f"ek süre ≤ 400 ms (hedef ~100; ölçülen {ek_ms} ms)", ek_ms is not None and ek_ms <= 400)
    r = sor("k", benim, kapi_profil=pb, kanal="karsi"); kontrol("karşı kanalda kapı hesaplanmaz", "kapi" not in r)
    r = sor("c", benim[:int(1.2 * SR)], kapi_profil=pb); kontrol("1,2 sn parça tek pencere", len(r.get("kapi") or []) == 1)
    r = sor("g", np.zeros(SR * 2, np.float32), kapi_profil=pb); kontrol("sessiz parçada işçi çökmez, yanıt gelir", "id" in r and "hata" not in r)
    r = sor("z", benim, kapi_profil="bozuk!!"); kontrol("bozuk profil Whisper sonucunu bozmaz", bool((r.get("text") or "").strip()) and "kapi_hata" in r)
finally:
    p.stdin.close(); p.wait(10)
print("GEÇTİ" if not hatalar else f"KALDI: {len(hatalar)} — " + "; ".join(hatalar))
sys.exit(1 if hatalar else 0)
