#!/usr/bin/env python3
# Suflor.me tur sonu işçisi (v0.48.0): smart-turn v3 (Daily, BSD-2, 8 MB ONNX) — "konuşmacının cümlesi bitti mi" olasılığı.
# Konuşurken "hı hı"nın kapısı (aktarici/bas-konus.py _hihi_bak): kural bir duraksama bulunca son ≤ 8 sn ses buraya gelir; olasılık eşiğin
# altındaysa (cümle ortası, düşünme duraksaması) "hı hı" çalmaz. Ölçüm testler/smart-turn-20261016.md (Türkçe iki kayıt: doğru anda çalma
# %47–58 → eşik 0,95'te %71–74).
# Girdi (stdin, satır başına JSON): {"id": n, "pcm": base64 int16 16 kHz tek kanal}; çıktı: {"id": n, "p": 0–1, "ms": çıkarım}
# Açılışta {"hazir": true} ya da {"hata": "..."}. Özellik çıkarımı transformers'sız: Whisper log-mel (WhisperFeatureExtractor, chunk_length=8,
# do_normalize) numpy ile — test/hihi.py transformers'la karşılaştırır (ortamda varsa).
#   <smart-turn-venv>/bin/python -I -B tur-isci.py <model.onnx>
import sys, json, time, base64
import numpy as np
SR, N_FFT, HOP, N_MEL, SN = 16000, 400, 160, 80, 8
def _mel_suzgec():  # librosa/HF "slaney" mel ölçeği ve normu (Whisper'ın mel_filters'ı)
    f_min, f_sp, min_log_hz = 0.0, 200.0 / 3, 1000.0
    min_log_mel, logstep = (min_log_hz - f_min) / f_sp, np.log(6.4) / 27.0
    def hz2mel(f): f = np.asarray(f, float); return np.where(f >= min_log_hz, min_log_mel + np.log(np.maximum(f, 1e-10) / min_log_hz) / logstep, (f - f_min) / f_sp)
    def mel2hz(m): m = np.asarray(m, float); return np.where(m >= min_log_mel, min_log_hz * np.exp(logstep * (m - min_log_mel)), f_min + f_sp * m)
    fftf = np.linspace(0, SR / 2, N_FFT // 2 + 1); melf = mel2hz(np.linspace(hz2mel(0.0), hz2mel(SR / 2), N_MEL + 2))
    fd = np.diff(melf); r = melf[:, None] - fftf[None, :]
    w = np.maximum(0, np.minimum(-r[:-2] / fd[:-1, None], r[2:] / fd[1:, None]))
    return w * (2.0 / (melf[2:N_MEL + 2] - melf[:N_MEL]))[:, None]
MEL = _mel_suzgec(); PENCERE = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)  # periyodik Hann
def ozellik(a):  # float32 ses → (1, 80, 800)
    a = a[-SN * SR:]
    if len(a) < SN * SR: a = np.pad(a, (SN * SR - len(a), 0))  # sola sıfır (smart-turn audio_utils)
    a = (a - a.mean()) / np.sqrt(a.var() + 1e-7)  # do_normalize
    p = np.pad(a, (N_FFT // 2, N_FFT // 2), mode="reflect")
    n = 1 + (len(p) - N_FFT) // HOP
    kare = np.lib.stride_tricks.as_strided(p, (n, N_FFT), (p.strides[0] * HOP, p.strides[0])) * PENCERE
    guc = np.abs(np.fft.rfft(kare, axis=1)) ** 2
    with np.errstate(all="ignore"): m = MEL @ guc.T  # numpy 2.0 + Accelerate (sistem Python 3.9 ortamı) sonuç doğruyken yanlış uyarı verir
    m = np.log10(np.maximum(m, 1e-10))[:, :-1]
    m = (np.maximum(m, m.max() - 8.0) + 4.0) / 4.0
    return m[None].astype(np.float32)
def main():
    try:
        import onnxruntime as ort
        so = ort.SessionOptions(); so.inter_op_num_threads = 1; so.intra_op_num_threads = 2
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        S = ort.InferenceSession(sys.argv[1], sess_options=so, providers=["CPUExecutionProvider"])
        S.run(None, {"input_features": ozellik(np.zeros(SR, np.float32))})  # ısınma
    except Exception as e:
        print(json.dumps({"hata": f"{e.__class__.__name__}: {str(e)[:200]}"}), flush=True); return
    print(json.dumps({"hazir": True}), flush=True)
    for sat in sys.stdin:
        g = {}
        try:
            g = json.loads(sat); t = time.perf_counter()
            a = np.frombuffer(base64.b64decode(g["pcm"]), np.int16).astype(np.float32) / 32768
            p = float(S.run(None, {"input_features": ozellik(a)})[0].reshape(-1)[0])
            print(json.dumps({"id": g.get("id"), "p": round(p, 4), "ms": round((time.perf_counter() - t) * 1000, 1)}), flush=True)
        except Exception as e:
            print(json.dumps({"id": g.get("id") if isinstance(g, dict) else None, "hata": e.__class__.__name__}), flush=True)
if __name__ == "__main__": main()
