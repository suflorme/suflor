#!/usr/bin/env python3
# Suflor.me — Whisper işçisi (v0.8.3). Aktarıcı (relay.py) bunu whisper-venv Python'uyla alt süreç olarak başlatır;
# model bir kez yüklenir, sonra stdin'den gelen konuşma parçalarını metne çevirir. Tamamen yerel: ağ yok (model diskten).
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "pcm": "<base64 int16, 16 kHz, tek kanal>", "dil": "tr"|"en"|null, "istem": "terimler…", "onceki": "son metin"}
#   çıkış : {"hazir": true, "model": "...", "sn": yükleme} · {"id": "...", "text": "...", "sn": süre, "dil": "tr", "atlanan": n} · {"id": "...", "hata": "..."}
# Uydurma süzgeci: sessiz/gürültülü parçada Whisper altyazı kalıpları üretir ("Altyazı M.K.", "İzlediğiniz için
# teşekkürler") — 1 Ekim yapay ses denemesinde görüldü. Kalıp + düşük güven + tekrar oranıyla atılır.
import sys, os, json, time, base64, re
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model diskte; ağa çıkma
MODEL = os.environ.get("SUFLOR_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
UYDURMA = re.compile(r"altyaz[ıi]\s*m\.?\s*k|izlediğiniz için teşekkür|abone ol(mayı|un)|beğenmeyi unutma|bir sonraki videoda|"
                     r"thanks? (you )?for watching|subtitles? by|please subscribe|amara\.org|transcribed by|"
                     r"^\W*(müzik|music|alkış|applause|\[.*\]|\(.*\))\W*$", re.I)
# v0.8.2 ses sinyalleri (kullanıcı, 2 Ekim: kişiye özel duygu): parçanın ses yüksekliği, perdesi (F0, otokorelasyon) ve perde
# dalgalanması. Kişinin kendi tabanıyla karşılaştırma toplanti-claude.py izle'de. Yalnız sayılar döner; ses saklanmaz.
def ses_olc(a, np, sr=16000):
    fl, hop = 640, 320  # 40 ms pencere, 20 ms adım
    if len(a) < fl * 3: return None
    n = 1 + (len(a) - fl) // hop
    kar = np.stack([a[i * hop:i * hop + fl] for i in range(n)]); rms = np.sqrt((kar ** 2).mean(1)) + 1e-9
    esik = max(0.006, np.percentile(rms, 90) * 0.25); sesli = rms > esik
    if sesli.sum() < 5: return None
    lo, hi = sr // 400, sr // 70  # 70–400 Hz
    f0 = []
    w = np.hanning(fl)
    for k in np.where(sesli)[0]:
        x = (kar[k] - kar[k].mean()) * w; X = np.fft.rfft(x, 2 * fl); ac = np.fft.irfft(X * np.conj(X))[:fl]
        if ac[0] <= 0: continue
        j = lo + int(np.argmax(ac[lo:hi])); 
        if ac[j] / ac[0] > 0.45: f0.append(sr / j)
    o = {"db": round(float(20 * np.log10(np.median(rms[sesli]))), 1), "sesli": round(float(sesli.mean()), 2), "sure": round(len(a) / sr, 2)}
    if len(f0) >= 5:
        f = np.array(f0); m = float(np.median(f)); st = 12 * np.log2(f / m)
        st = st[np.abs(st) < 12]  # oktav hatası
        o.update(f0=round(m, 1), f0_oyn=round(float(st.std()), 2))
    return o
def out(o): sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n"); sys.stdout.flush()
def main():
    t = time.time()
    try:
        import numpy as np, mlx_whisper
        mlx_whisper.transcribe(np.zeros(16000, np.float32), path_or_hf_repo=MODEL, language="tr")  # ısınma: model belleğe
    except Exception as e:
        out({"hata": f"model yüklenemedi: {e.__class__.__name__}: {str(e)[:200]}"}); return 1
    out({"hazir": True, "model": MODEL, "sn": round(time.time() - t, 1)})
    for satir in sys.stdin:
        if not satir.strip(): continue
        try: p = json.loads(satir)
        except ValueError: continue
        try:
            a = np.frombuffer(base64.b64decode(p["pcm"]), np.int16).astype(np.float32) / 32768
            t = time.time(); istem = " ".join(x for x in (p.get("istem") or "", p.get("onceki") or "") if x).strip() or None
            r = mlx_whisper.transcribe(a, path_or_hf_repo=MODEL, language=p.get("dil") or None, initial_prompt=istem,
                                       condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4)
            tut, atla = [], 0
            for s in r.get("segments") or []:
                x = (s.get("text") or "").strip()
                if not x or UYDURMA.search(x) or (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -0.8) \
                        or s.get("compression_ratio", 0) > 2.4 or s.get("avg_logprob", 0) < -1.2: atla += 1; continue
                tut.append(x)
            metin = " ".join(tut).strip()
            # kısa satırda web adresi: Whisper'ın video sonu uydurması ("www.feyyaz.tv" — 1 Ekim headless bip sesi denemesi)
            if metin and len(metin.split()) <= 6 and re.search(r"\bwww\.|https?://|\.(com|tv|net|org)(\.tr)?\b", metin, re.I): metin = ""; atla += 1
            if istem and metin and metin.lower().strip(" .") in istem.lower(): metin = ""; atla += 1  # istemi geri okuma
            try: ses = ses_olc(a, np) if metin else None
            except Exception: ses = None
            out({"id": p.get("id"), "text": metin, "sn": round(time.time() - t, 2), "dil": r.get("language"), "atlanan": atla, **({"ses": ses} if ses else {})})
        except Exception as e:
            out({"id": p.get("id"), "hata": f"{e.__class__.__name__}: {str(e)[:200]}"})
    return 0
if __name__ == "__main__":
    sys.exit(main())
