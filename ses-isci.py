#!/usr/bin/env python3
# Suflor.me — ses işçisi (v0.8.4). Aktarıcı (relay.py) bunu ses-venv Python'uyla alt süreç olarak başlatır; iki model bir
# kez yüklenir, sonra stdin'den gelen konuşma parçalarını (Whisper'a giden parçanın aynısı) işler. Tamamen yerel: ağ yok.
#   duygu  : emotion2vec+ base (FunASR) — 9 sınıf, parça başına ~0,15 sn. Tahmindir; kişi etiketinde metin + ses
#            sinyalleriyle birlikte kullanılır (CLAUDE.md "duygu").
#   kişi   : ECAPA-TDNN (SpeechBrain, VoxCeleb) ses izi, 192 boyut, ~0,03 sn. Karşı kanalda (Teams sekmesinin sesi, birden çok
#            kişi karışık) konuşmacı kümelenir: k1, k2… Adı aktarıcı altyazıdan öğrenir. ben kanalı kümelenmez.
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "pcm": "<base64 int16, 16 kHz>", "kanal": "ben"|"karsi"}
#   çıkış : {"hazir": true, "sn": yükleme} · {"id", "duygu": {"etiket", "p", "dagilim"}, "kume": "k1"|null, "benzerlik"} · {"id", "hata"}
# FunASR, SpeechBrain'den önce içe aktarılmalı (tersinde FunASR'ın modül taraması SpeechBrain'in tembel modülüne takılıyor).
import sys, os, json, time, base64
os.environ.setdefault("HF_HUB_OFFLINE", "1")
MOD = os.environ.get("SUFLOR_SES_MODELLER") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "ses-modeller")
ETIKET = {"angry": "kizgin", "disgusted": "igrenmis", "fearful": "korkmus", "happy": "mutlu", "neutral": "notr",
          "other": "diger", "sad": "uzgun", "surprised": "saskin", "<unk>": "bilinmiyor", "unknown": "bilinmiyor"}
KUME_ESIK = 0.45; KUME_GUNCELLE = 0.5; KUME_KISA_ESIK = 0.55; KUME_EN_COK = 6; KUME_MIN_SN = 1.5
_OUT = sys.stdout; sys.stdout = sys.stderr  # FunASR/SpeechBrain stdout'a yazıyor ("funasr version…"): protokol satırları ayrı kalsın
def out(o): _OUT.write(json.dumps(o, ensure_ascii=False) + "\n"); _OUT.flush()
def main():
    t = time.time()
    try:
        import numpy as np, logging
        logging.disable(logging.WARNING)
        from funasr import AutoModel
        duygu = AutoModel(model=os.path.join(MOD, "emotion2vec_plus_base"), disable_update=True, device="cpu", log_level="ERROR")
        import torch
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        d = os.path.join(MOD, "spkrec-ecapa-voxceleb")
        # v0.9.2: modeller ortak klasörde (/Users/Shared/Suflor) — diğer hesap oraya yazamaz; SpeechBrain savedir'e yazdığı için
        # yazılamıyorsa hesabın kendi önbelleği (~90 MB, bir kez kopyalanır)
        sv = d if os.access(d, os.W_OK) else os.path.expanduser("~/Library/Caches/Suflor/spkrec-ecapa-voxceleb")
        os.makedirs(sv, exist_ok=True)
        iz = EncoderClassifier.from_hparams(source=d, savedir=sv, overrides={"pretrained_path": d}, run_opts={"device": "cpu"}, local_strategy=LocalStrategy.NO_LINK)
        duygu.generate(np.zeros(16000, np.float32), granularity="utterance", extract_embedding=False, disable_pbar=True)  # ısınma
    except Exception as e:
        out({"hata": f"model yüklenemedi: {e.__class__.__name__}: {str(e)[:200]}"}); return 1
    out({"hazir": True, "sn": round(time.time() - t, 1)})
    kumeler = {}  # kanal → [[ağırlık merkezi (birim vektör), sayı]]
    for satir in sys.stdin:
        if not satir.strip(): continue
        try: p = json.loads(satir)
        except ValueError: continue
        if p.get("sifirla"): kumeler.clear(); out({"id": p.get("id"), "sifirlandi": True}); continue  # yeni toplantı
        try:
            a = np.frombuffer(base64.b64decode(p["pcm"]), np.int16).astype(np.float32) / 32768; t = time.time(); o = {"id": p.get("id")}
            r = duygu.generate(a, granularity="utterance", extract_embedding=False, disable_pbar=True)[0]
            sk = sorted(zip(r["scores"], r["labels"]), reverse=True)
            ad = lambda l: ETIKET.get(str(l).split("/")[-1], str(l).split("/")[-1])
            o["duygu"] = {"etiket": ad(sk[0][1]), "p": round(float(sk[0][0]), 2), "dagilim": {ad(l): round(float(x), 2) for x, l in sk if x >= 0.05}}
            if p.get("kanal") == "karsi" and len(a) >= 16000 * 0.8:
                e = iz.encode_batch(torch.tensor(a)[None]).squeeze().numpy(); e = e / (np.linalg.norm(e) + 1e-9)
                ks = kumeler.setdefault("karsi", []); uzun = len(a) >= 16000 * KUME_MIN_SN
                sim = [float(np.dot(e, k[0])) for k in ks]; j = int(np.argmax(sim)) if sim else -1
                if j >= 0 and sim[j] >= (KUME_ESIK if uzun else KUME_KISA_ESIK):
                    if uzun and sim[j] >= KUME_GUNCELLE:
                        c = ks[j][0] * ks[j][1] + e; ks[j][0] = c / (np.linalg.norm(c) + 1e-9); ks[j][1] += 1
                    o["kume"] = f"k{j + 1}"; o["benzerlik"] = round(sim[j], 2)
                elif uzun and len(ks) < KUME_EN_COK:
                    ks.append([e, 1]); o["kume"] = f"k{len(ks)}"; o["benzerlik"] = round(max(sim), 2) if sim else None
                else: o["kume"] = None
            o["sn"] = round(time.time() - t, 3); out(o)
        except Exception as e:
            out({"id": p.get("id"), "hata": f"{e.__class__.__name__}: {str(e)[:200]}"})
    return 0
if __name__ == "__main__":
    sys.exit(main())
