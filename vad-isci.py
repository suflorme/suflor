#!/usr/bin/env python3
# Suflor.me konuşma algılayıcı işçisi (Konuş Aşama 2, Adım 3): Silero VAD v6.2.3 (snakers4/silero-vad, MIT, 2,3 MB ONNX) — "şu an konuşma var mı" olasılığı.
# Yerel Konuş hattında (aktarici/vad.py istemcisi) asistan okurken kullanıcının sesi başladı mı sorusuna cevap verir (araya girme, Adım 5).
# Girdi (stdin, satır başına JSON): {"id": n, "pcm": base64 int16 16 kHz tek kanal, "esik": 0.5, "min_konusma_ms": 96, "min_sessizlik_ms": 160}
#   (esik/min_* isteğe bağlı, verilirse kalıcı olur) ya da {"id": n, "sifirla": true} (model durumu ve olay makinesi sıfırlanır).
# Çıktı: {"id": n, "p": [32 ms pencere başına olasılık], "son": son olasılık, "konusma": şu an konuşma durumunda mı,
#         "olay": [{"o": "basla"|"bitti", "t": ms}], "ms": çıkarım süresi}; t = sıfırlamadan beri akış zamanı (konuşmanın gerçek başı/sonu).
# Açılışta {"hazir": true}; model/ortam yoksa {"yok": true} (model dosyası yok) ya da {"hata": "..."} ve çıkar — çökmez.
# Silero 16 kHz'te 512 örnek (32 ms) ister; artan örnekler bir sonraki öbeğe taşınır. Önceki pencerenin son 64 örneği bağlam olarak başa eklenir,
# 2x128 durum (state) öbekler arasında taşınır (silero_vad.OnnxWrapper ile aynı). Çağrı:
#   <smart-turn-venv>/bin/python -I -B vad-isci.py <silero_vad.onnx>
import sys, os, json, time, base64
import numpy as np
SR, PEN, BAGLAM = 16000, 512, 64
PEN_MS = PEN * 1000.0 / SR  # 32 ms
def main():
    yol = sys.argv[1] if len(sys.argv) > 1 else ""
    if not yol or not os.path.isfile(yol):
        print(json.dumps({"yok": True}), flush=True); return
    try:
        import onnxruntime as ort
        so = ort.SessionOptions(); so.inter_op_num_threads = 1; so.intra_op_num_threads = 1
        S = ort.InferenceSession(yol, sess_options=so, providers=["CPUExecutionProvider"])
        sr_g = np.array(SR, dtype=np.int64)
        durum = np.zeros((2, 1, 128), np.float32)
        S.run(None, {"input": np.zeros((1, PEN + BAGLAM), np.float32), "state": durum, "sr": sr_g})  # ısınma
    except Exception as e:
        print(json.dumps({"hata": f"{e.__class__.__name__}: {str(e)[:200]}"}), flush=True); return
    print(json.dumps({"hazir": True}), flush=True)
    A = {"esik": 0.5, "min_konusma_ms": 96.0, "min_sessizlik_ms": 160.0}
    def sifirla():
        return {"durum": np.zeros((2, 1, 128), np.float32), "baglam": np.zeros(BAGLAM, np.float32), "artik": np.zeros(0, np.float32),
                "n": 0, "konusma": False, "kosu_bas": None, "sessiz_bas": None}
    K = sifirla()
    for sat in sys.stdin:
        g = {}
        try:
            g = json.loads(sat); t0 = time.perf_counter()
            for ad in A:
                if g.get(ad) is not None: A[ad] = float(g[ad])
            if g.get("sifirla"): K = sifirla()
            ps, olay = [], []
            if g.get("pcm"):
                a = np.concatenate([K["artik"], np.frombuffer(base64.b64decode(g["pcm"]), np.int16).astype(np.float32) / 32768])
                nw = len(a) // PEN; K["artik"] = a[nw * PEN:].copy()
                neg = max(A["esik"] - 0.15, 0.01)  # çıkış eşiği (histerezis; silero get_speech_timestamps ile aynı)
                for i in range(nw):
                    w = a[i * PEN:(i + 1) * PEN]
                    x = np.concatenate([K["baglam"], w])[None]
                    p_, K["durum"] = S.run(None, {"input": x, "state": K["durum"], "sr": sr_g})
                    K["baglam"] = x[0, -BAGLAM:]; p = float(p_.reshape(-1)[0]); ps.append(round(p, 4))
                    bas_ms = K["n"] * PEN_MS; K["n"] += 1; son_ms = K["n"] * PEN_MS  # pencerenin başı/sonu (akış ms)
                    if not K["konusma"]:
                        if p >= A["esik"]:
                            if K["kosu_bas"] is None: K["kosu_bas"] = bas_ms
                            if son_ms - K["kosu_bas"] >= A["min_konusma_ms"]:
                                K["konusma"] = True; K["sessiz_bas"] = None; olay.append({"o": "basla", "t": round(K["kosu_bas"], 1)}); K["kosu_bas"] = None
                        else: K["kosu_bas"] = None
                    else:
                        if p < neg:
                            if K["sessiz_bas"] is None: K["sessiz_bas"] = bas_ms
                            if son_ms - K["sessiz_bas"] >= A["min_sessizlik_ms"]:
                                K["konusma"] = False; olay.append({"o": "bitti", "t": round(K["sessiz_bas"], 1)}); K["sessiz_bas"] = None
                        elif p >= A["esik"]: K["sessiz_bas"] = None  # eşikler arası: durumu koru
            print(json.dumps({"id": g.get("id"), "p": ps, "son": ps[-1] if ps else None, "konusma": K["konusma"], "olay": olay,
                              "ms": round((time.perf_counter() - t0) * 1000, 1)}), flush=True)
        except Exception as e:
            print(json.dumps({"id": g.get("id") if isinstance(g, dict) else None, "hata": e.__class__.__name__}), flush=True)
if __name__ == "__main__": main()
