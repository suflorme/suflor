#!/usr/bin/env python3
# Suflor.me — Whisper işçisi (v0.8.3; v0.13.12 ses izi). Aktarıcı (relay.py) bunu whisper-venv Python'uyla alt süreç olarak başlatır;
# model bir kez yüklenir, sonra stdin'den gelen konuşma parçalarını metne çevirir. Tamamen yerel: ağ yok (model diskten).
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "pcm": "<base64 int16, 16 kHz, tek kanal>", "dil": "tr"|"en"|null, "istem": "terimler…", "onceki": "son metin",
#            "kanal": "ben"|"karsi", "baslik": "toplantı"}
#   çıkış : {"hazir": true, "model": "...", "sn": yükleme, "ecapa": bool} · {"id": "...", "text": "...", "sn": süre, "dil": "tr", "atlanan": n,
#            "kume": "k1"|null, "benzerlik", "iz": karşı kanal ses izi (float16 base64), "bol": [{"s", "e", "n", "iz"}] bölüm başına} · {"id": "...", "hata": "..."}
# konuşmacı ses izi (ECAPA-TDNN, SpeechBrain VoxCeleb ağırlıkları) bu süreçte MLX ile çalışır — ayrı ses işçisi,
# PyTorch ve duygu modeli (emotion2vec+) kalktı. Ağırlıklar modeller-kur'un bir kez dönüştürdüğü ecapa-mlx.npz (SUFLOR_ECAPA); yoksa
# kümeleme olmaz, Whisper aynen çalışır. SpeechBrain'le aynı sonuç (6 Ekim, 18 parça: kosinüs ≥ 0,99999), parça başına ~25 ms.
# Uydurma süzgeci: sessiz/gürültülü parçada Whisper altyazı kalıpları üretir ("Altyazı M.K.", "İzlediğiniz için
# teşekkürler") — 1 Ekim yapay ses denemesinde görüldü. Kalıp + düşük güven + tekrar oranıyla atılır.
import sys, os, json, time, base64, re
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model diskte; ağa çıkma
MODEL = os.environ.get("SUFLOR_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
UYDURMA = re.compile(r"altyaz[ıi]\s*m\.?\s*k|izlediğiniz için teşekkür|субтитр|yoyo television|优优独播|abone ol(mayı|un)|beğenmeyi unutma|bir sonraki videoda|"
                     r"thanks? (you )?for watching|subtitles? by|please subscribe|amara\.org|transcribed by|"
                     r"^\W*(müzik|music|alkış|applause|\[.*\]|\(.*\))\W*$", re.I)
# ses sinyalleri (kullanıcı, 2 Ekim: kişiye özel duygu): parçanın ses yüksekliği, perdesi (F0, otokorelasyon) ve perde
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
# --- ECAPA (MLX). SpeechBrain'in Fbank'ı (25 ms Hamming, 10 ms adım, 80 mel, dB, üst 80 dB) + cümle ortalaması + ECAPA_TDNN
# (1024 kanal, Res2Net ölçek 8, SE 128, dikkatli istatistik havuzu); Conv1d "same" + yansıtmalı dolgu, BatchNorm çıkarım istatistiği.
SR, NFFT, HOP = 16000, 400, 160
KUME_ESIK = 0.45; KUME_GUNCELLE = 0.5; KUME_KISA_ESIK = 0.55; KUME_EN_COK = 6; KUME_MIN_SN = 1.5  # ses-isci.py'den aynen
class Ecapa:
    def __init__(s, yol, np, mx):
        s.np, s.mx = np, mx
        mel = lambda h: 2595 * np.log10(1 + h / 700); hz = 700 * (10 ** (np.linspace(mel(0), mel(SR // 2), 82, dtype=np.float32) / 2595) - 1)
        f = np.linspace(0, SR // 2, NFFT // 2 + 1, dtype=np.float32)[:, None]; e = (f - hz[1:-1]) / (hz[1:] - hz[:-1])[:-1]
        s.mel = np.maximum(0, np.minimum(e + 1, 1 - e)).astype(np.float32); s.pen = (0.54 - 0.46 * np.cos(2 * np.pi * np.arange(NFFT) / NFFT)).astype(np.float32)
        w = dict(np.load(yol)); s.w = {}
        for k, v in w.items():
            if k.endswith("conv.weight"): s.w[k] = mx.array(v.transpose(0, 2, 1))  # torch (çıkış, giriş, k) → MLX (çıkış, k, giriş)
            elif k.endswith("conv.bias"): s.w[k] = mx.array(v)
            elif k.endswith("norm.weight"):
                b = k[:-len("weight")]; sc = v / np.sqrt(w[b + "running_var"] + 1e-5)
                s.w[b + "sc"] = mx.array(sc); s.w[b + "sh"] = mx.array(w[b + "bias"] - w[b + "running_mean"] * sc)
    def fbank(s, a):
        np = s.np; x = np.pad(a.astype(np.float32), NFFT // 2); n = 1 + (len(x) - NFFT) // HOP
        kar = np.lib.stride_tricks.as_strided(x, (n, NFFT), (x.strides[0] * HOP, x.strides[0])) * s.pen
        with np.errstate(all="ignore"):  # macOS Accelerate matmul'ü yersiz taşma uyarısı veriyor; sonuç doğru
            db = 10 * np.log10(np.maximum((np.abs(np.fft.rfft(kar, NFFT)) ** 2) @ s.mel, 1e-10))
        db = np.maximum(db, db.max() - 80); return db - db.mean(0)
    def conv(s, x, p, dil=1):
        mx = s.mx; w = s.w[p + ".conv.weight"]; q = dil * (w.shape[1] - 1) // 2
        if q:
            L = x.shape[1]; i = s.np.concatenate([s.np.arange(q, 0, -1), s.np.arange(L), s.np.arange(L - 2, L - 2 - q, -1)])
            x = mx.take(x, mx.array(i), axis=1)
        return mx.conv1d(x, w, dilation=dil) + s.w[p + ".conv.bias"]
    def tdnn(s, x, p, dil=1): return s.mx.maximum(s.conv(x, p + ".conv", dil), 0) * s.w[p + ".norm.norm.sc"] + s.w[p + ".norm.norm.sh"]
    def blok(s, x, p, dil):
        mx = s.mx; r = x; xs = mx.split(s.tdnn(x, p + ".tdnn1"), 8, axis=2); y = [xs[0]]
        for i in range(1, 8): y.append(s.tdnn(xs[i] if i == 1 else xs[i] + y[-1], f"{p}.res2net_block.blocks.{i - 1}", dil))
        x = s.tdnn(mx.concatenate(y, axis=2), p + ".tdnn2")
        z = mx.maximum(s.conv(x.mean(axis=1, keepdims=True), p + ".se_block.conv1"), 0)
        return x * mx.sigmoid(s.conv(z, p + ".se_block.conv2")) + r
    def __call__(s, a):
        mx = s.mx; x = s.tdnn(mx.array(s.fbank(a))[None], "blocks.0"); xl = []
        for i in (1, 2, 3): x = s.blok(x, f"blocks.{i}", i + 1); xl.append(x)
        x = s.tdnn(mx.concatenate(xl, axis=2), "mfa")
        m = x.mean(axis=1, keepdims=True); sd = mx.sqrt(mx.maximum(((x - m) ** 2).mean(axis=1, keepdims=True), 1e-12))
        at = mx.concatenate([x, mx.broadcast_to(m, x.shape), mx.broadcast_to(sd, x.shape)], axis=2)
        at = mx.softmax(s.conv(mx.tanh(s.tdnn(at, "asp.tdnn")), "asp.conv"), axis=1)
        m = (at * x).sum(axis=1, keepdims=True); sd = mx.sqrt(mx.maximum((at * (x - m) ** 2).sum(axis=1, keepdims=True), 1e-12))
        e = s.np.array(s.conv(mx.concatenate([m, sd], axis=2) * s.w["asp_bn.norm.sc"] + s.w["asp_bn.norm.sh"], "fc")[0, 0])
        return e / (s.np.linalg.norm(e) + 1e-9)
def kumele(iz, ks, a, np, e=None):
    # karşı kanal (Teams sekmesinin/uygulamasının sesi, birden çok kişi karışık): parça en yakın kümeye; yoksa yeni küme (k1, k2…)
    e = iz(a) if e is None else e; uzun = len(a) >= SR * KUME_MIN_SN
    sim = [float(np.dot(e, k[0])) for k in ks]; j = int(np.argmax(sim)) if sim else -1
    if j >= 0 and sim[j] >= (KUME_ESIK if uzun else KUME_KISA_ESIK):
        if uzun and sim[j] >= KUME_GUNCELLE:
            c = ks[j][0] * ks[j][1] + e; ks[j][0] = c / (np.linalg.norm(c) + 1e-9); ks[j][1] += 1
        return {"kume": f"k{j + 1}", "benzerlik": round(sim[j], 2)}
    if uzun and len(ks) < KUME_EN_COK:
        ks.append([e, 1]); return {"kume": f"k{len(ks)}", "benzerlik": round(max(sim), 2) if sim else None}
    return {"kume": None}
# Whisper istemi en çok 223 belirteç (n_text_ctx // 2 - 1) ve aşınca BAŞINI atar — baştaki en önemli terimler düşüyordu. Önceki
# metne son ONCEKI_EN_COK belirteç, kalan bütçeye terimler sırayla ve bütün olarak (aktarıcı önem sırasıyla dizer); payı 8.
ISTEM_SINIR, ONCEKI_EN_COK = 223 - 8, 60
_ISTEM_ON = {}
def istem_kur(tok, terimler, onceki):
    on = tok.encode(" " + onceki.strip())[-ONCEKI_EN_COK:] if onceki and onceki.strip() else []
    butce = ISTEM_SINIR - len(on); k = (terimler, butce)
    if k not in _ISTEM_ON:
        ls = [t for t in (terimler or "").rstrip(".").split(", ") if t.strip()]; n = 0
        while n < len(ls) and len(tok.encode(" " + ", ".join(ls[:n + 1]) + ".")) <= butce: n += 1
        if len(_ISTEM_ON) > 50: _ISTEM_ON.clear()
        _ISTEM_ON[k] = (", ".join(ls[:n]) + "." if n else "", len(ls) - n)
    metin, dusen = _ISTEM_ON[k]
    return (" ".join(x for x in (metin, tok.decode(on).strip() if on else "") if x) or None), dusen
def out(o): sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n"); sys.stdout.flush()
def main():
    t = time.time()
    try:
        import numpy as np, mlx_whisper
        mlx_whisper.transcribe(np.zeros(16000, np.float32), path_or_hf_repo=MODEL, language="tr")  # ısınma: model belleğe
    except Exception as e:
        out({"hata": f"model yüklenemedi: {e.__class__.__name__}: {str(e)[:200]}"}); return 1
    # MLX ara bellek önbelleği kapalı. Sınırsızken parça boyları değiştikçe önbellek büyüyor: 47 parçalık oturumda
    # işçi 5 805 MB'a çıktı (kısa ölçüm 2 700 gösteriyordu — toplantıdaki swap'ın asıl nedeni); 0 ile 2 449 MB, parça 1,15 → 1,19 sn,
    # metin aynı (6 Ekim). SUFLOR_MLX_ONBELLEK_MB ile değiştirilebilir.
    try:
        import mlx.core as mx; mx.set_cache_limit(int(os.environ.get("SUFLOR_MLX_ONBELLEK_MB") or 0) * 2 ** 20)
    except Exception: pass
    iz = None; ey = os.environ.get("SUFLOR_ECAPA")
    if ey and os.path.exists(ey):
        try: import mlx.core as mx; iz = Ecapa(ey, np, mx); iz(np.zeros(16000, np.float32))  # ısınma
        except Exception as e: iz = None; sys.stderr.write(f"ECAPA yüklenemedi: {e}\n")
    try:
        from mlx_whisper.tokenizer import get_tokenizer
        tok = get_tokenizer(multilingual=True, num_languages=100)  # düz metin belirteçleri dilden bağımsız
    except Exception as e: tok = None; sys.stderr.write(f"belirteçleyici yok, istem kırpılmaz: {e}\n")
    out({"hazir": True, "model": MODEL, "sn": round(time.time() - t, 1), "ecapa": bool(iz)})
    kumeler = []; baslik = None  # karşı kanal kümeleri; yeni toplantıda sıfırlanır
    for satir in sys.stdin:
        if not satir.strip(): continue
        try: p = json.loads(satir)
        except ValueError: continue
        try:
            a = np.frombuffer(base64.b64decode(p["pcm"]), np.int16).astype(np.float32) / 32768
            t = time.time(); dusen = 0
            if tok: istem, dusen = istem_kur(tok, p.get("istem") or "", p.get("onceki") or "")
            else: istem = " ".join(x for x in (p.get("istem") or "", p.get("onceki") or "") if x).strip() or None
            r = mlx_whisper.transcribe(a, path_or_hf_repo=MODEL, language=p.get("dil") or None, initial_prompt=istem,
                                       condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4)
            tut, atla = [], 0
            for s in r.get("segments") or []:
                x = (s.get("text") or "").strip()
                if not x or UYDURMA.search(x) or (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -0.8) \
                        or s.get("compression_ratio", 0) > 2.4 or s.get("avg_logprob", 0) < -1.2: atla += 1; continue
                tut.append((s, x))
            metin = " ".join(x for _, x in tut).strip()
            # kısa satırda web adresi: Whisper'ın video sonu uydurması ("www.feyyaz.tv" — 1 Ekim headless bip sesi denemesi)
            if metin and len(metin.split()) <= 6 and re.search(r"\bwww\.|https?://|\.(com|tv|net|org)(\.tr)?\b", metin, re.I): metin = ""; atla += 1
            if istem and metin and metin.lower().strip(" .") in istem.lower(): metin = ""; atla += 1  # istemi geri okuma
            try: ses = ses_olc(a, np) if metin else None
            except Exception: ses = None
            km = {}
            if p.get("baslik") != baslik: kumeler = []; baslik = p.get("baslik")
            if iz and metin and p.get("kanal") == "karsi" and len(a) >= SR * 0.5:
                # ses izi satırla geri döner (float16, base64): aktarıcı <toplantı>.sesizi.log'a yazar, toplantı sonunda toplu kümelenir (--toplu)
                try:
                    b64 = lambda v: base64.b64encode(v.astype(np.float16).tobytes()).decode()
                    e = iz(a); km = {"iz": b64(e)}
                    if len(a) >= SR * 0.8: km.update(kumele(iz, kumeler, a, np, e))
                    # birden çok bölümlü parçada bölüm (cümle) başına iz: hızlı söz devrinde canlı parça iki kişiyi içerir (11 Ekim, Easy Turkish:
                    # canlı parçaların 6/15'i) ve parça izi ikisini tek kişide birleştirir (%62 → bölüm izleriyle %100). n = bölümün sözcük sayısı
                    # (aktarıcının satır metnini bölmesi için); < 0,5 sn bölümün izi yok.
                    if len(tut) > 1:
                        km["bol"] = [dict({"s": round(sg["start"], 2), "e": round(sg["end"], 2), "n": len(x.split())},
                                          **({"iz": b64(iz(a[int(sg["start"] * SR):int(sg["end"] * SR)]))} if (sg["end"] - sg["start"]) >= 0.5 else {})) for sg, x in tut]
                except Exception as e: km = {"kume_hata": f"{e.__class__.__name__}: {str(e)[:120]}"}
            out({"id": p.get("id"), "text": metin, "sn": round(time.time() - t, 2), "dil": r.get("language"), "atlanan": atla, **({"istem_dusen": dusen} if dusen else {}), **({"ses": ses} if ses else {}), **km})
        except Exception as e:
            out({"id": p.get("id"), "hata": f"{e.__class__.__name__}: {str(e)[:200]}"})
    return 0
def gecerli(s, x):  # canlı işçideki uydurma süzgeci (bölüm başına)
    return bool(x) and not UYDURMA.search(x) and not (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -0.8) \
        and s.get("compression_ratio", 0) <= 2.4 and s.get("avg_logprob", 0) >= -1.2 \
        and not (len(x.split()) <= 6 and re.search(r"\bwww\.|https?://|\.(com|tv|net|org)(\.tr)?\b", x, re.I))
def dosya_parcala(a, np, en_uzun=25, en_kisa=1.5):
    # konuşma parçaları: ≥ 0,5 sn sessizlikten bölünür (söz devri çoğunlukla orada), en çok 25 sn (uzunsa son 5 sn'nin en sessiz karesinden),
    # 1,5 sn'den kısa parça komşusuna eklenir. Sessizlik eşiği kaydın kendi gürültü tabanından (sessiz %10'luk dilim × 3).
    K = SR // 50; n = len(a) // K
    if n == 0: return [(0, len(a))]
    rms = np.sqrt((a[:n * K].reshape(n, K) ** 2).mean(1)); esik = max(0.002, min(0.02, float(np.percentile(rms, 10)) * 3)); ses = rms > esik
    bol, i = [], 0
    while i < n:
        while i < n and not ses[i]: i += 1
        if i >= n: break
        j, sus = i, 0
        while j < n and sus < 25:
            sus = sus + 1 if not ses[j] else 0; j += 1
        bol.append([i, j - sus]); i = j
    out_ = []
    for b0, b1 in bol:
        while b1 - b0 > en_uzun * 50:
            c = b0 + (en_uzun - 5) * 50 + int(np.argmin(rms[b0 + (en_uzun - 5) * 50:b0 + en_uzun * 50])); out_.append([b0, c]); b0 = c
        if out_ and (b1 - b0 < en_kisa * 50 or out_[-1][1] - out_[-1][0] < en_kisa * 50) and b1 - out_[-1][0] <= en_uzun * 50 and b0 - out_[-1][1] < 50: out_[-1][1] = b1
        else: out_.append([b0, b1])
    return [(max(0, b0 * K - SR // 5), min(len(a), b1 * K + SR // 5)) for b0, b1 in out_]  # 200 ms pay
DOSYA_DILLER = ("tr", "en"); DOSYA_YOGUNLUK = 0.35; DOSYA_YOGUN_SN = 6  # dosya kipi uydurma süzgeci (aşağıda dosya_tut)
def dosya_tut(sure, segler):
    # Dosya kipinde parça başına: canlıdaki süzgeç (gecerli) + yoğunluk. 10 Ekim gerçek kayıt ölçümü (gercek-ses/): müzikli 8–25 sn parçalar
    # yalnız "Thank you." gibi 1–2 sözcük üretti (≤ 0,2 sözcük/sn); gerçek konuşmada 6 sn'yi aşan parçada en düşük 1,9 sözcük/sn. Güven
    # (avg_logprob) ayırmıyor: gerçek "Thank you, counsel" −0,16…−0,73, uydurma −0,43…−1,0. 6 sn'den uzun parçada < 0,35 sözcük/sn → atılır.
    tut = [(s, (s.get("text") or "").strip()) for s in segler]; tut = [(s, x) for s, x in tut if gecerli(s, x)]
    if sure >= DOSYA_YOGUN_SN and sum(len(x.split()) for _, x in tut) / sure < DOSYA_YOGUNLUK: return [], len(segler)
    return tut, len(segler) - len(tut)
DOSYA_KUME_ESIK = 0.35  # toplu kümeleme birleşme eşiği (ortalama kosinüs); gercek-ses/kume-ayar.py ile seçildi
def toplu_kumele(izler, np, esik=DOSYA_KUME_ESIK, en_kisa=1.0, kucuk_sn=8.0):
    # Dosyada bütün ses baştan elde: parçaların ses izleri sonda birlikte kümelenir (ortalama bağlantılı, kosinüs ≥ esik birleşir; küme sınırı
    # yok). Canlı kural (sırayla, en çok 6 küme, sınır dolunca öncekini devralma) 10 Ekim'de 12 konuşmacılı gerçek kayıtta aynı kişiyi üç
    # kümeye böldü. izler: [(süre sn, iz ya da None)] → [küme no ya da None]; ≥ en_kisa sn parçalar kümelenir, kısa parça en yakın merkeze.
    idx = [i for i, (sn, e) in enumerate(izler) if e is not None and sn >= en_kisa]
    if not idx: return [None] * len(izler)
    X = np.array([izler[i][1] for i in idx], np.float32); X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    M = X @ X.T; np.fill_diagonal(M, -9); boy = np.ones(len(idx)); uye = [[i] for i in range(len(idx))]
    while len(idx) > 1:
        a, b = np.unravel_index(int(np.argmax(M)), M.shape)
        if M[a, b] < esik: break
        y = (M[a] * boy[a] + M[b] * boy[b]) / (boy[a] + boy[b]); M[a] = y; M[:, a] = y; M[a, a] = -9; M[b] = -9; M[:, b] = -9
        boy[a] += boy[b]; uye[a] += uye[b]; uye[b] = []
    et = [None] * len(izler); merk = {}; sure = {}
    for k, u in enumerate(uye):
        if u: merk[k] = X[u].mean(0); sure[k] = sum(izler[idx[j]][0] for j in u)
        for j in u: et[idx[j]] = k
    # toplam < kucuk_sn konuşmalık küme (gerçek kayıtta 12 kişiye 18 küme: fazlası 1–2 satırlık kırıntı) en yakın büyük kümeye katılır
    buyuk = {k: v for k, v in merk.items() if sure[k] >= kucuk_sn}
    if buyuk:
        tasi = {k: max(buyuk, key=lambda b: float(np.dot(merk[k], buyuk[b]))) for k in merk if k not in buyuk}
        et = [tasi.get(k, k) if k is not None else None for k in et]; merk = buyuk
    for i, (sn, e) in enumerate(izler):
        if et[i] is None and e is not None: et[i] = max(merk, key=lambda k: float(np.dot(e, merk[k])))
    return et
def toplu_dosya(yol):
    # toplantı sonu (toplanti-claude.py konusmaci): canlı karşı satırların ses izleri (<toplantı>.sesizi.log: {"id", "t0", "t1", "iz", "bol"?}) dosyadan
    # dökümdeki gibi toplu kümelenir. Bölümlü satırda birim bölümdür (iki kişili canlı parça ayrılır); < 0,5 sn izsiz bölüm satırdaki en uzun
    # izli bölümün kümesini alır. Model yüklenmez (yalnız numpy). Çıkış: {"kume": {id: no (süreye göre çoğunluk)}, "bol": {id: [no, …]} (yalnız
    # bölümleri farklı kümede olan satır), "n": satır, "k": küme sayısı}
    import numpy as np
    def iz_(b):
        e = np.frombuffer(base64.b64decode(b), np.float16).astype(np.float32); return e / (np.linalg.norm(e) + 1e-9)
    satir, birim = [], []  # satir: (id, [birim no]); birim: (süre, iz ya da None)
    for l in open(yol, encoding="utf-8"):
        try: r = json.loads(l); e = iz_(r["iz"])
        except (ValueError, KeyError, TypeError): continue
        bol = r.get("bol") or []
        if len(bol) > 1 and any(b.get("iz") for b in bol):
            ns = []
            for b in bol:
                try: ns.append(len(birim)); birim.append((max(0.0, float(b["e"]) - float(b["s"])), iz_(b["iz"]) if b.get("iz") else None))
                except (ValueError, KeyError, TypeError): ns.append(len(birim)); birim.append((0.0, None))
        else: ns = [len(birim)]; birim.append((max(0.0, float(r.get("t1") or 0) - float(r.get("t0") or 0)), e))
        satir.append((r["id"], ns))
    et = toplu_kumele(birim, np) if birim else []; ad = {}; km, bl = {}, {}
    for i, ns in satir:
        ks = [et[n] for n in ns]; sure = [birim[n][0] for n in ns]
        if all(k is None for k in ks): continue
        uz = max((m for m in range(len(ns)) if ks[m] is not None), key=lambda m: sure[m])
        ks = [k if k is not None else ks[uz] for k in ks]
        top = {}
        for k, sn in zip(ks, sure): top[k] = top.get(k, 0) + sn
        km[i] = ad.setdefault(max(top, key=top.get), len(ad) + 1)
        if len(set(ks)) > 1: bl[i] = [ad.setdefault(k, len(ad) + 1) for k in ks]
    out({"kume": km, "bol": bl, "n": len(satir), "k": len(ad)}); return 0
def dosya_dok(yol, dil, terimler):
    # Dosyadan döküm (toplanti-claude.py dosyadan): afconvert'in ürettiği 16 kHz tek kanal 16 bit WAV, canlıdaki gibi konuşma parçalarıyla
    # (dosya_parcala) Whisper'a. 10 Ekim yapay iki kişilik denemesinde 5 dk'lık bloklar dili blok başında bir kez buldu (İngilizce paragraf
    # Türkçe uydurmaya döndü) ve iki konuşmacıyı tek bölümde birleştirdi; parça başına dil ve ses izi ikisini de çözer. Ses izi (ECAPA)
    # varsa bölümler sonda toplu kümelenir (toplu_kumele), o yüzden iş bitince yazılır. Çıkış satır başına JSON:
    # {"hazir", "sure"} · {"blok", "toplam"} · {"bolum": {"t0", "t1", "metin", "kume"?}} · {"bitti", "sn", "atlanan"} · {"hata"}
    import struct
    t = time.time()
    try:
        import numpy as np, mlx_whisper
        b = open(yol, "rb").read(); i, fmt, a = 12, None, None  # RIFF parçaları; afconvert WAVE_FORMAT_EXTENSIBLE yazar, wave modülü okumaz
        while i + 8 <= len(b) and b[:4] == b"RIFF":
            ad, n = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
            if ad == b"fmt ": fmt = struct.unpack("<HHI", b[i + 8:i + 16]) + struct.unpack("<H", b[i + 22:i + 24])  # biçim, kanal, örnekleme, bit
            elif ad == b"data": a = np.frombuffer(b[i + 8:i + 8 + n], np.int16).astype(np.float32) / 32768; break
            i += 8 + n + (n & 1)
        if not fmt or a is None or fmt[1:] != (1, SR, 16): out({"hata": "WAV 16 kHz tek kanal 16 bit değil"}); return 1
    except Exception as e: out({"hata": f"{e.__class__.__name__}: {str(e)[:200]}"}); return 1
    try: import mlx.core as mx; mx.set_cache_limit(int(os.environ.get("SUFLOR_MLX_ONBELLEK_MB") or 0) * 2 ** 20)
    except Exception: pass
    iz = None; ey = os.environ.get("SUFLOR_ECAPA")
    if ey and os.path.exists(ey):
        try: import mlx.core as mx; iz = Ecapa(ey, np, mx)
        except Exception as e: sys.stderr.write(f"ECAPA yüklenemedi: {e}\n")
    istem = None
    if terimler:
        try:
            from mlx_whisper.tokenizer import get_tokenizer
            istem = istem_kur(get_tokenizer(multilingual=True, num_languages=100), terimler, "")[0]
        except Exception: istem = terimler
    out({"hazir": True, "model": MODEL, "sure": round(len(a) / SR, 1), "ecapa": bool(iz)})
    parcalar = dosya_parcala(a, np); atla, dil_son = 0, dil; adim = max(1, len(parcalar) // 20); izler, bolumler = [], []
    for k, (b0, b1) in enumerate(parcalar):
        if k % adim == 0: out({"blok": k + 1, "toplam": len(parcalar)})
        p = a[b0:b1]
        # dil: verilmediyse her parçada Whisper bulur (karışık dilli toplantı); 4 sn'den kısa parçada tahmin güvensiz → öncekinin dili
        r = mlx_whisper.transcribe(p, path_or_hf_repo=MODEL, language=dil or (dil_son if len(p) < 4 * SR else None), initial_prompt=istem,
                                   condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4)
        if not dil and r.get("language") not in DOSYA_DILLER:  # Rusça/Çince altyazı kalıbı ya da yanlış dil: beklenen dilde yeniden, sonra süzgeç
            r = mlx_whisper.transcribe(p, path_or_hf_repo=MODEL, language=dil_son or DOSYA_DILLER[0], initial_prompt=istem,
                                       condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4)
        if not dil and len(p) >= 4 * SR and r.get("language") in DOSYA_DILLER: dil_son = r["language"]
        tut, at = dosya_tut(len(p) / SR, r.get("segments") or []); atla += at
        for s, x in tut:
            if istem and x.lower().strip(" .") in istem.lower(): atla += 1; continue
            # ses izi parça değil bölüm (Whisper cümlesi) başına: hızlı sohbette söz sırası arasında 0,5 sn sessizlik olmuyor, parçada iki kişi
            # karışıyordu (10 Ekim, iki kişilik Türkçe podcast tek kümeye düştü; bölüm düzeyinde ilk 1,5 dk %97 doğru)
            s0, s1 = b0 + int(float(s["start"]) * SR), b0 + int(float(s["end"]) * SR); e = None
            if iz and s1 - s0 >= SR // 2:
                try: e = np.array(iz(a[s0:s1]), np.float32)
                except Exception: e = None
            izler.append(((s1 - s0) / SR, e))
            bolumler.append((len(izler) - 1, {"t0": round(b0 / SR + float(s["start"]), 2), "t1": round(b0 / SR + float(s["end"]), 2), "metin": x, "dil": r.get("language")}))
    et = toplu_kumele(izler, np) if iz else [None] * len(izler); ad = {}
    for k, bo in bolumler:  # küme adları ilk konuşma sırasıyla k1, k2…
        if et[k] is not None: bo["kume"] = ad.setdefault(et[k], f"k{len(ad) + 1}")
        out({"bolum": bo})
    out({"bitti": True, "sn": round(time.time() - t, 1), "atlanan": atla}); return 0
def ecapa_donustur(ckpt, hedef):
    # kurulumda bir kez (aktarici-kur / modeller-kur): SpeechBrain ağırlıkları (torch dosyası) → numpy .npz. torch yalnız burada gerekir
    # (whisper-venv'de mlx-whisper'ın bağımlılığı olarak var); işçi çalışırken torch içe aktarılmaz.
    import numpy as np, torch
    sd = torch.load(ckpt, map_location="cpu"); gec = hedef + ".tmp.npz"
    np.savez(gec, **{k: v.numpy().astype(np.float32) for k, v in sd.items() if not k.endswith("num_batches_tracked")})
    Ecapa(gec, np, __import__("mlx.core", fromlist=["core"]))(np.zeros(16000, np.float32)); os.replace(gec, hedef)  # açılmıyorsa yazılmaz
    print(f"✓ ses izi ağırlıkları dönüştürüldü: {hedef}")
def whisper_nicemle(kaynak, hedef, bit=8):
    # turbo modeli kurulumda bir kez yerelde 8 bite nicemlenir (indirme yok). Ölçüm (47 aynı parça, önbellek 0):
    # turbo 2 449 MB · parça 1,19 sn · WER %13,6/9,2 → q8 1 838 MB · 1,25 sn · %14,0/8,8. q4 doğruluk kaybettirdi (%16,9/10,7), kullanılmaz.
    import mlx.core as mx, mlx.nn as nn
    from mlx.utils import tree_flatten
    from mlx_whisper.load_models import load_model
    m = load_model(kaynak, dtype=mx.float16)
    nn.quantize(m, group_size=64, bits=bit, class_predicate=lambda p, x: isinstance(x, (nn.Linear, nn.Embedding)) and x.weight.shape[-1] % 64 == 0)
    gec = hedef + ".tmp"; os.makedirs(gec, exist_ok=True)
    mx.save_safetensors(os.path.join(gec, "weights.safetensors"), dict(tree_flatten(m.parameters())))
    c = json.load(open(os.path.join(kaynak, "config.json"))); c["quantization"] = {"group_size": 64, "bits": bit}
    json.dump(c, open(os.path.join(gec, "config.json"), "w"))
    import numpy as np, mlx_whisper; mlx_whisper.transcribe(np.zeros(16000, np.float32), path_or_hf_repo=gec, language="tr")  # açılmıyorsa yerine konmaz
    if os.path.isdir(hedef): import shutil; shutil.rmtree(hedef)
    os.replace(gec, hedef); print(f"✓ Whisper {bit} bit modeli hazır: {hedef}")
if __name__ == "__main__":
    if sys.argv[1:2] == ["--ecapa-donustur"]: ecapa_donustur(sys.argv[2], sys.argv[3]); sys.exit(0)
    if sys.argv[1:2] == ["--whisper-nicemle"]: whisper_nicemle(sys.argv[2], sys.argv[3]); sys.exit(0)
    if sys.argv[1:2] == ["--toplu"]: sys.exit(toplu_dosya(sys.argv[2]))
    if sys.argv[1:2] == ["--dosya"]: sys.exit(dosya_dok(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None, os.environ.get("SUFLOR_ISTEM", "")))
    sys.exit(main())
