#!/usr/bin/env python3
# Suflor.me — Pocket TTS seslendirme işçisi (yerel Türkçe ses, S93). Aktarıcı bunu Pocket'ın kendi Python ortamıyla (ayar pocket_python; torch +
# pocket_tts + pocket_tts_turkish) alt süreç olarak başlatır. Tamamen yerel: ağ yok (HF_HUB_OFFLINE), modeller kullanıcının Hugging Face önbelleğinde
# (ayar pocket_hf = HF_HOME). İşlemcide tek çekirdek çalışır; Whisper grafik işlemcide olduğu için yarışmazlar (19 Ekim ölçümü: Whisper'a etkisi %4).
# İki model (19 Ekim kör puanlama, testler/yerel-ses-arastirma-20261019):
#   wite     = wite-tech/pocket-tts-turkish — hazır sesler female_1..3 / male_1..3, duygu etiketi (mutlu, üzgün, kızgın, şaşkın, sakin), sayıları kendisi okur
#   alperiox = alperiox/pocket-tts-turkish (6 katman) — duygu etiketi yok, ses örneği ister (wite'ın hazır seslerinden ya da bir .wav), rakam okuyamaz
#              (aktarıcı rakamı yazıya çevirip gönderir), Türkçe küçük harfle eğitilmiş
#   en       = kyutai/pocket-tts İngilizce (v0.101.3, kullanıcı 21 Ekim: İngilizce cevap Türkçe aksanla okunuyordu) — ses kopyalamasız sürüm
#              (pocket-tts-without-voice-cloning, koşulsuz), hazır sesler (michael, mary …; kör dinlemede seçildi), duygu etiketi yok, ilk ses ~0,05 sn
# Ses adı "model:ses": "wite:male_1", "alperiox:female_2", "alperiox:/yol/ornek.wav", "en:michael".
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "metin": "...", "ses": "wite:male_1", "duygu": null|"mutlu"|…}
#   çıkış : {"hazir": true, "sn": yükleme, "sr": 24000, "modeller": [...]} · parça {"id", "parca": i, "wav": yol, "sure": sn, "ilk": sn (yalnız ilk)}
#           · {"id", "bitti": true, "n": parça sayısı, "sn": toplam üretim} · {"id", "hata": "..."}
#   Parça ~0,5 sn'de bir yazılır (kesintisiz çalıcı ilk sesi hemen çalar); cümleler arasına 0,25 sn sessizlik. Cümle yalnız . ! ? … sonunda bölünür.
import sys, os, re, json, glob, time, wave, tempfile

def yaz(o): sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n"); sys.stdout.flush()

PARCA_SN, ARA_SN = 0.5, 0.25
_KUCUK = str.maketrans({"I": "ı", "İ": "i"})

def main():
    gecici = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "suflor-pocket")
    onyukle = [x for x in (sys.argv[2] if len(sys.argv) > 2 else "").split(",") if x]
    os.makedirs(gecici, exist_ok=True)
    for f in glob.glob(os.path.join(gecici, "*.wav")):
        try: os.remove(f)
        except OSError: pass
    t = time.time()
    try:
        import numpy as np, torch
        torch.set_num_threads(1)
        hub = os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub")
        SABIT = {"wite-tech/pocket-tts-turkish": "fcbd37c74dc127be846face0ff36062e9a939f7b", "alperiox/pocket-tts-turkish": "13d9b4ad051ce9d5ef5bfb8af9724be01ad2fd31"}  # O5: denenmiş sürüm
        def anlik(repo):
            k = os.path.join(hub, "models--" + repo.replace("/", "--"), "snapshots")
            if SABIT.get(repo) and os.path.isdir(os.path.join(k, SABIT[repo])): return os.path.join(k, SABIT[repo])
            d = sorted(glob.glob(os.path.join(k, "*")))
            if not d: raise FileNotFoundError(f"{repo} indirilmemiş")
            print(f"pocket: {repo} denenmiş sürümü yok, {os.path.basename(d[-1])[:10]} kullanılıyor", file=sys.stderr); return d[-1]
        M = {}
        def wite():
            if "wite" not in M:
                from pocket_tts_turkish import TurkishTTS, frontend as F
                eski = F.TextFrontend.guard_first_word  # model ilk sözcüğü yutuyor ("Vay," "Aa,"); duygu etiketinden sonra başa virgül onu kurtarır (18 Ekim)
                if not getattr(eski, "_suflor", False):
                    yeni = lambda self, s, tagged: (", " if tagged else "") + eski(self, s, tagged); yeni._suflor = True
                    F.TextFrontend.guard_first_word = yeni
                M["wite"] = TurkishTTS.from_pretrained(anlik("wite-tech/pocket-tts-turkish"))
            return M["wite"]
        def alperiox():
            if "alperiox" not in M:
                from pocket_tts.models.tts_model import TTSModel
                d = anlik("alperiox/pocket-tts-turkish")
                cfg = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
                cfg.write(open(os.path.join(d, "turkish_6l.yaml"), encoding="utf-8").read().replace("hf://alperiox/pocket-tts-turkish/", d + "/")); cfg.close()
                M["alperiox"] = TTSModel.load_model(config=cfg.name); os.remove(cfg.name)
            return M["alperiox"]
        def ingilizce():
            if "en" not in M:
                from pocket_tts.models.tts_model import TTSModel
                M["en"] = TTSModel.load_model(language="english_2026-09")  # ağırlık ve ses sürümleri yapılandırmada sabit (@revizyon); çevrimdışı önbellekten
            return M["en"]
        DURUM_EN = {}
        DURUM = {}  # alperiox ses örneği durumları (ses başına bir kez)
        def alperiox_durum(ses):
            if ses not in DURUM:
                yol = ses if ses.endswith(".wav") else os.path.join(anlik("wite-tech/pocket-tts-turkish"), "voices", ses + ".wav")
                if not os.path.exists(yol): raise FileNotFoundError(f"ses örneği yok: {os.path.basename(yol)}")
                DURUM[ses] = alperiox().get_state_for_audio_prompt(yol)
            return DURUM[ses]
        def akis(ses, cumle, duygu):  # tek cümle → numpy parçaları (~80 ms)
            model, _, ad = ses.partition(":")
            if model == "wite":
                w = wite()
                for p in w.stream(cumle.replace("…", ","), voice=ad or "female_2", emotion=duygu or None): yield np.asarray(p, np.float32).reshape(-1)
            elif model == "alperiox":
                st = alperiox_durum(ad or "female_2")
                for p in alperiox().generate_audio_stream(st, cumle.replace("…", ",").translate(_KUCUK).lower()): yield p.detach().cpu().numpy().reshape(-1).astype(np.float32)
            elif model == "en":
                if (ad or "michael") not in DURUM_EN: DURUM_EN[ad or "michael"] = ingilizce().get_state_for_audio_prompt(ad or "michael")
                for p in ingilizce().generate_audio_stream(DURUM_EN[ad or "michael"], cumle.replace("…", ",")): yield p.detach().cpu().numpy().reshape(-1).astype(np.float32)
            else: raise ValueError(f"bilinmeyen model: {model}")
        for m in onyukle:  # aktarıcı açılırken kişiliklerin sesleri; ilk okuma beklemesin (ısınma dahil)
            for _ in akis(m, "Hello." if m.startswith("en:") else "Merhaba.", None): pass
    except Exception as e:
        yaz({"hazir": False, "hata": f"{e.__class__.__name__}: {e}"[:200]}); return
    SR = 24000
    yaz({"hazir": True, "sn": round(time.time() - t, 2), "sr": SR, "modeller": sorted(M)})
    for satir in sys.stdin:
        try: g = json.loads(satir)
        except ValueError: continue
        kim = str(g.get("id") or ""); metin = str(g.get("metin") or "").strip(); ses = str(g.get("ses") or "wite:female_2")
        if not metin: yaz({"id": kim, "bitti": True, "n": 0, "sn": 0}); continue
        try:
            t0 = time.time(); n = 0; biriken = []; uzun = 0
            def bosalt():
                nonlocal n, biriken, uzun
                if not biriken: return
                a = np.clip(np.concatenate(biriken), -1, 1); yol = os.path.join(gecici, f"{kim}-{n}.wav")
                with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a * 32767).astype(np.int16).tobytes())
                yaz(dict({"id": kim, "parca": n, "wav": yol, "sure": round(len(a) / SR, 2)}, **({"ilk": round(time.time() - t0, 3)} if n == 0 else {})))
                n += 1; biriken = []; uzun = 0
            cumleler = [x for x in re.split(r"(?<=[.!?…])\s+", metin) if x.strip()] or [metin]
            for k, c in enumerate(cumleler):
                if k: biriken.append(np.zeros(int(ARA_SN * SR), np.float32)); uzun += int(ARA_SN * SR)
                for p in akis(ses, c, g.get("duygu")):
                    biriken.append(p); uzun += len(p)
                    if uzun >= PARCA_SN * SR or n == 0: bosalt()  # ilk parça hemen (ilk ses ~0,03 sn), sonra ~0,5 sn'de bir
            bosalt()
            yaz({"id": kim, "bitti": True, "n": n, "sn": round(time.time() - t0, 3)})
        except Exception as e:
            yaz({"id": kim, "hata": f"{e.__class__.__name__}: {e}"[:200]})

if __name__ == "__main__": main()
