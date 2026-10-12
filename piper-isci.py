#!/usr/bin/env python3
# Suflor.me — Piper seslendirme işçisi (yerel Türkçe ses). Aktarıcı bunu Piper'ın kendi Python ortamıyla (ayar piper_python) alt süreç
# olarak başlatır; ses modeli (ayar piper_model, .onnx + yanında .onnx.json ya da config.json) bir kez yüklenir. Tamamen yerel: ağ yok.
# Ses dosyası depoda değildir: kullanıcı yerelde indirir, kod yalnız ayar varsa kullanır (lisansı belirsiz ses açık depoya girmez).
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "metin": "...", "hiz": 1.0, "ara": 0.4}   hiz > 1 daha hızlı (süre ≈ 1 / hiz; length_scale açılışta ölçülen eğriden);
#           "ton"/"ritim" (isteğe bağlı): noise_scale / noise_w_scale (yoksa modelin kendi değeri; dinlenerek seçilir)
#           ara: cümleler arasına eklenen sessizlik (sn, hıza göre ölçekli; Piper cümle sonunu kırpıyor); noktalı virgül / iki nokta
#           sonrası 0,7 katı, virgül sonrası 0,35 katı (Piper bunlarda ~0–0,06 sn duruyordu); "yan": true → her yan cümle ayrı parça
#           (kesintisiz çalıcıda ilk ses daha erken); yoksa parçalar cümle sonuna kadar birleşir (afplay her dosyada ~0,75 sn ekliyor)
#   çıkış : {"hazir": true, "sn": yükleme, "sr": örnekleme} · cümle başına {"id", "parca": i, "wav": yol, "sure": sn, "ilk": sn (yalnız ilk parça)}
#           · {"id", "bitti": true, "n": parça sayısı, "sn": toplam üretim} · {"id", "hata": "..."}
# wav'lar geçici klasöre yazılır; aktarıcı çalınca siler (işçi açılışta eskilerini temizler).
import sys, os, re, json, time, wave, glob, tempfile

def yaz(o): sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n"); sys.stdout.flush()

def main():
    model = sys.argv[1]; gecici = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tempfile.gettempdir(), "suflor-piper")
    os.makedirs(gecici, exist_ok=True)
    for f in glob.glob(os.path.join(gecici, "*.wav")):
        try: os.remove(f)
        except OSError: pass
    t = time.time()
    try:
        from piper import PiperVoice
        try: from piper import SynthesisConfig
        except ImportError: SynthesisConfig = None
        cfg = next((c for c in (model + ".json", os.path.join(os.path.dirname(model), "config.json")) if os.path.exists(c)), None)
        ses = PiperVoice.load(model, config_path=cfg) if cfg else PiperVoice.load(model)
        for _ in ses.synthesize("Merhaba."): pass  # ısınma: ilk cümle ~0,3 sn daha yavaş
    except Exception as e:
        yaz({"hazir": False, "hata": f"{e.__class__.__name__}: {e}"[:200]}); return
    sr = getattr(getattr(ses, "config", None), "sample_rate", 22050)
    taban = float(getattr(getattr(ses, "config", None), "length_scale", None) or 1.0)
    # hız eğrisi: süre length_scale'le doğrusal değişmiyor (12 Ekim, Türkçe ses: 0,9–1,2 arası süre ~%10, 0,9'un altı sert düşüş) →
    # açılışta birkaç değerle ölç, istenen süre oranına karşılık gelen değeri eğriden bul (~0,3 sn)
    egri = []
    if SynthesisConfig:
        ornek = "Toplantıda bütçe onayını ve teslim tarihini konuştuk, sonra yeniden bakacağız."
        for ls in sorted({0.5, 0.6, 0.7, 0.8, 0.9, 1.0, taban, taban * 1.25, taban * 1.6}):
            egri.append((ls, sum(len(c.audio_int16_bytes) for c in ses.synthesize(ornek, syn_config=SynthesisConfig(length_scale=ls)))))
    def ls_bul(hiz):
        if not egri: return taban / hiz
        hedef = dict(egri)[taban] / hiz
        for (a, da), (b, db) in zip(egri, egri[1:]):
            if da <= hedef <= db: return a + (b - a) * ((hedef - da) / (db - da) if db > da else 0)
        return egri[0][0] if hedef < egri[0][1] else egri[-1][0]
    yaz({"hazir": True, "sn": round(time.time() - t, 2), "sr": sr})
    for satir in sys.stdin:
        try: g = json.loads(satir)
        except ValueError: continue
        kim = str(g.get("id") or ""); metin = str(g.get("metin") or "").strip()
        if not metin: yaz({"id": kim, "bitti": True, "n": 0, "sn": 0}); continue
        try:
            hiz = min(2.0, max(0.5, float(g.get("hiz") or 1.0)))
            # hız modelin kendi konuşma hızına göre (taban = modelin length_scale'i; dinlenen örnekler bununla)
            ek = {k2: min(1.5, max(0.0, float(g[k1]))) for k1, k2 in (("ton", "noise_scale"), ("ritim", "noise_w_scale")) if g.get(k1) is not None}
            sc = SynthesisConfig(length_scale=ls_bul(hiz), **ek) if (SynthesisConfig and (abs(hiz - 1.0) > 0.01 or ek)) else None
            ara = min(1.5, max(0.0, float(g.get("ara") or 0))) / hiz
            t0 = time.time(); n = 0
            # cümleleri ve yan cümleleri kendimiz böleriz: Piper (espeak) küçük harfle başlayan cümleyi ayırmıyor, ; : , işaretlerinde durmuyordu
            parcalar, once = [], 0.0
            for x in re.split(r"(?<=[.!?…;:,])\s+", metin):
                if x.strip(): parcalar.append((x, once))
                once = ara * (1.0 if x.rstrip()[-1:] in ".!?…" else 0.7 if x.rstrip()[-1:] in ";:" else 0.35 if x.rstrip()[-1:] == "," else 0)
            parcalar = parcalar or [(metin, 0.0)]
            biriken, r = b"", sr
            for k, (x, sessiz) in enumerate(parcalar):
                for c in (ses.synthesize(x, syn_config=sc) if sc else ses.synthesize(x)):
                    r = getattr(c, "sample_rate", sr)
                    if sessiz and (biriken or n): biriken += bytes(int(sessiz * r) * 2)
                    biriken += c.audio_int16_bytes; sessiz = 0
                if biriken and (g.get("yan") or k == len(parcalar) - 1 or x.rstrip()[-1:] in ".!?…"):
                    yol = os.path.join(gecici, f"{kim}-{n}.wav")
                    with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(r); w.writeframes(biriken)
                    yaz(dict({"id": kim, "parca": n, "wav": yol, "sure": round(len(biriken) / 2 / r, 2)}, **({"ilk": round(time.time() - t0, 3)} if n == 0 else {})))
                    n += 1; biriken = b""
            yaz({"id": kim, "bitti": True, "n": n, "sn": round(time.time() - t0, 3)})
        except Exception as e:
            yaz({"id": kim, "hata": f"{e.__class__.__name__}: {e}"[:200]})

if __name__ == "__main__": main()
