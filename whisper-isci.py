#!/usr/bin/env python3
# Suflor.me — Whisper işçisi (v0.8.3; v0.13.12 ses izi). Aktarıcı (relay.py) bunu whisper-venv Python'uyla alt süreç olarak başlatır;
# model bir kez yüklenir, sonra stdin'den gelen konuşma parçalarını metne çevirir. Tamamen yerel: ağ yok (model diskten).
# Protokol (satır başına bir JSON):
#   giriş : {"id": "...", "pcm": "<base64 int16, 16 kHz, tek kanal>", "dil": "tr"|"en"|null, "istem": "terimler…", "onceki": "son metin",
#            "kanal": "ben"|"karsi", "baslik": "toplantı", "kisaltma": ["SKU", …] (sözlüğün büyük harfli terimleri), "oda": true (yalnız ben: ses izi de döner),
#            "diller": ["tr", "en"] + "dil_yedek" (dil yokken: başka dil bulunursa yedek dilde yeniden)}
#   çıkış : {"hazir": true, "model": "...", "sn": yükleme, "ecapa": bool} · {"id": "...", "text": "...", "sn": süre, "dil": "tr", "atlanan": n,
#            "kume": "k1"|null, "benzerlik", "iz": karşı kanal ses izi (float16 base64), "bol": [{"s", "e", "n", "iz"}] bölüm başına} · {"id": "...", "hata": "..."}
# konuşmacı ses izi (ECAPA-TDNN, SpeechBrain VoxCeleb ağırlıkları) bu süreçte MLX ile çalışır — ayrı ses işçisi,
# PyTorch ve duygu modeli (emotion2vec+) kalktı. Ağırlıklar modeller-kur'un bir kez dönüştürdüğü ecapa-mlx.npz (SUFLOR_ECAPA); yoksa
# kümeleme olmaz, Whisper aynen çalışır. SpeechBrain'le aynı sonuç (6 Ekim, 18 parça: kosinüs ≥ 0,99999), parça başına ~25 ms.
# Uydurma süzgeci: sessiz/gürültülü parçada Whisper altyazı kalıpları üretir ("Altyazı M.K.", "İzlediğiniz için
# teşekkürler") — 1 Ekim yapay ses denemesinde görüldü. Kalıp + düşük güven + tekrar oranıyla atılır.
import sys, os, json, time, base64, re, zlib
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model diskte; ağa çıkma
MODEL = os.environ.get("SUFLOR_WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
if "/" in MODEL and not os.path.isdir(MODEL):  # depo adı: çevrimdışı açılış refs/main ister; yoksa diskteki anlık görüntüden aç
    import glob as _g
    _s = sorted(_g.glob(os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub", "models--" + MODEL.replace("/", "--"), "snapshots", "*", "weights.safetensors")))
    if _s and not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_s[0]))), "refs", "main")): MODEL = os.path.dirname(_s[0])
UYDURMA = re.compile(r"altyaz[ıi]\s*m\.?\s*k|izlediğiniz için teşekkür|субтитр|yoyo television|优优独播|abone ol(mayı|un)|beğenmeyi unutma|bir sonraki videoda|"
                     r"^\W*(abone ol|[İi]zlediğiniz için)\W*$|"  # 3 Kasım: tek başına duran kalıp (cümle içindeki "abone olmak istiyorum" gerçek söz, kalır)
                     r"thanks? (you )?for watching|subtitles? by|please subscribe|amara\.org|transcribed by|"
                     r"^\W*(müzik|music|alkış|applause|\[.*\]|\(.*\))\W*$", re.I)
# 23 Ekim üçlü sohbet denemesi: Fransızca altyazı imzası kullanıcının gerçek sözünün başına yapıştı ("- Sous-titrage: N-S-T-R, O Arkadaşlar sakin olun…");
# bölümü atmak sözü de atardı — imza ve ardından gelen büyük harf kısaltmaları kırpılır, kalan söz tutulur (kalan yoksa bölüm uydurma sayılır).
UYDURMA_ON = re.compile(r"^\W*(?i:sous[- ]?titr\w*|untertitel\w*|ondertitel\w*|sottotitol\w*|subt[ií]tul\w*|napisy|legendas?)\b\W*"
                        r"(?:(?:[A-ZÇĞİÖŞÜ](?:[-.]?[A-ZÇĞİÖŞÜ0-9])*|\d+|[A-Z][a-zé]+-[A-Z][a-zé]+)['’]?[^\w\s]*(?:\s+|$))*")
UYDURMA_ON_YABANCI = re.compile(r"(?i)amara\.org|radio-canada|\b(im auftrag|réalis|par |por la|des ZDF)")  # imzanın kendisi (Fransızca/Almanca/İspanyolca) — kalan da uydurma
UYDURMA_ETIKET = re.compile(r"\*[^*\n]{1,30}\*")  # v0.125.2: "*sad*", "*sigh*" — Whisper'ın yıldızlı ses etiketi (köşeli/parantezli tek başına UYDURMA'da)
def uydurma_on_kirp(x):  # → (kalan metin, kırpılan imza ya da "")
    et = UYDURMA_ETIKET.findall(x or "")
    if et: x = " ".join(UYDURMA_ETIKET.sub(" ", x).split()); x = re.sub(r"^[-–—\s]+", "", x)
    k, imza = _uydurma_imza(x)
    return k, " ".join(et + ([imza] if imza else []))
def _uydurma_imza(x):
    m = UYDURMA_ON.match(x or "")
    if not m: return x, ""
    kal = x[m.end():].strip()
    if UYDURMA_ON_YABANCI.search(kal): return "", x
    return kal[:1].upper() + kal[1:], x[:m.end()].strip()
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
# Tekrar döngüsü (19 Ekim test toplantısı): karşı kanaldan geri gelen kendi sesimiz "OBSERV, PARA, OLI, AKMU" + 9 kez "AKMU" yazıldı; kısa satırda sıkıştırma
# oranı süzgeci (2,4) yakalamıyor. Aynı sözcük ya da 2–3 sözcüklük öbek art arda ≥ 4 kez ve satırın en az yarısıysa uydurma (gerçek "evet evet evet" 3 kez kalır).
# 3 Kasım: 2 sözcüklük öbeğin tam 3 kez tekrarı da döngü; gerçek tepkiler ("tamam tamam", "evet anladım" ×3) muaf (öbek yalnız bu sözcüklerden oluşuyorsa)
TEPKI_SOZ = frozenset("evet hayır hı hıhı hıı hm hmm mhm mm mmm ım ıı ee eh ah oh ha he tamam anladım anladık peki olur aynen tabii tabi yok ya işte yani ok okay yes no right yeah sure".split())
def _tepki_obegi(b): return all(x in TEPKI_SOZ for x in b)
def _tekrar_bul(w):
    # Art arda tekrar eden birimi bulur → (başlangıç, birim uzunluğu, tekrar sayısı) ya da None. 1–3 sözcüklük birim ≥ 4 kez ve satırın en az yarısıysa;
    # 4–12 sözcüklük birim (cümle ya da cümle çifti, noktalama farklı olsa da) ≥ 3 kez gelirse (28 Ekim Teams testi: iki cümlelik öbek 3 kez + yarım kopya;
    # gerçek konuşmada 4 sözcüklük sözün üç kez aynen tekrarı yok).
    for n in range(1, 13):
        i = 0
        while i + n <= len(w):
            k = 1
            while w[i + k * n:i + (k + 1) * n] == w[i:i + n]: k += 1
            if (n <= 3 and k >= 4 and k * n >= len(w) / 2) or (n >= 4 and k >= 3 and len(set(w[i:i + n])) > 1) \
                    or (n == 2 and k == 3 and k * n >= len(w) / 2 and len(set(w[i:i + n])) > 1 and not _tepki_obegi(w[i:i + n])): return i, n, k
            i += 1
    return None
def tekrar_dongu(metin):
    return _tekrar_bul([x.lower() for x in re.findall(r"\w+", metin or "")]) is not None
# v0.88.2 (19 Ekim 18.23 deneme): gerçek cümlenin ardına öbek döngüsü eklenince ("Eklentiyi yeniledim. Web toplantısına girdim." + öbek ×N) tüm satır
# atılıyordu. Döngü 2–3 sözcüklük öbekse ve önünde en az 2 sözcük varsa öndeki söz + öbeğin bir kopyası kalır; tek sözcük döngüsü ("AKMU" ×9) yine atılır.
# Uzun birimde (≥ 4 sözcük) önceki söz + birimin bir kopyası + döngüden sonra gelen farklı söz kalır; döngünün yarım son kopyası düşer.
def tekrar_kirp(metin):
    for _ in range(3):
        m = list(re.finditer(r"\w+", metin or "")); w = [x.group().lower() for x in m]
        r = _tekrar_bul(w)
        if not r: return (metin or "").strip() or None
        i, n, k = r
        if n == 1 or (n <= 3 and (i < 2 or len(set(w[i:i + n])) == 1)): return None  # öbek tek sözcüğün tekrarıysa ("AKMU AKMU") tek sözcük döngüsü
        son = k * n + i  # döngünün tam kopyalarının bittiği sözcük; yalnız birimin başından oluşan kuyruk (yarım kopya) düşer
        kuyruk = w[son:]
        if kuyruk and kuyruk == w[i:i + len(kuyruk)]: son = len(w)
        bas = metin[:m[i + n - 1].end()]; j = m[i + n - 1].end()
        bas += metin[j] if j < len(metin) and metin[j] in ".!?" else ""
        metin = (bas + (" " + metin[m[son].start():] if son < len(w) else "")).strip()
    return metin
# Nokta öbeği (30 Ekim test toplantısı): kullanıcı kanalında sözsüz sürekli seste Whisper yüzlerce "..." üretti; yalnız noktadan oluşan bölümler atılıyordu ama
# arada 1–3 sözcük çıkan bölüm noktalarıyla birlikte döküme yazılıyor, askıdaki hitaba ekleniyordu. Ayrı duran noktalama öbekleri (≥ 3 tane) silinir; kalan
# sözcük ≤ 1 ya da 3 sn'den uzun parçada saniyede < NOKTA_YOGUNLUK sözcükse satır uydurmadır (asistan adı geçiyorsa kalır). Sözcüksüz metin her zaman atılır.
NOKTA_OBEK = re.compile(r"^[.…·]+[,;:!?]*$"); NOKTA_YOGUNLUK = 0.35
def nokta_ayikla(metin, sn=0.0, hitap=()):  # → (kalan metin, atılan ya da None)
    if not metin or not metin.strip(): return metin, None
    if not re.search(r"\w", metin): return "", metin
    t = metin.split()
    if sum(1 for x in t if NOKTA_OBEK.match(x)) < 3: return metin, None
    kalan = " ".join(x for x in t if not NOKTA_OBEK.match(x)).strip(); n = len(re.findall(r"\w+", kalan))
    adli = any(re.search(r"(?<!\w)" + re.escape(str(h)) + r"(?!\w)", kalan, re.I) for h in hitap or () if str(h).strip())
    if not adli and (n <= 1 or (sn >= 3 and n / sn < NOKTA_YOGUNLUK)): return "", metin
    return kalan, metin
# 3 Kasım (13:09 toplantısı): istemdeki "290.000" biçimini taklit eden uydurma sayı ("%83.000'ü" = yüzde 83; "2.000…" = "iki,"). Satır ATILMAZ, yalnız işaretlenir
# (dökümün .jsonl kaydında sayi_suphe). Yüzde + binlik ayraç (başı 0 olmayan) ya da bağlamsız yalnız "N.000" satırı; "290.000 TL", "%83", "2.000 kişi" işaretlenmez.
SAYI_YUZDE_RX = re.compile(r"%\s?[1-9]\d{0,2}\.\d{3}(?!\d)"); SAYI_CIPLAK_RX = re.compile(r"^\W*\d{1,3}\.000\W*$")
def sayi_suphe(metin):
    x = (metin or "").strip()
    return bool(SAYI_YUZDE_RX.search(x) or SAYI_CIPLAK_RX.match(x))
# Hız denetimi (28 Ekim: 1 sn'lik parçada 58 sözcük): sürekli konuşma saniyede ~6 sözcüğü geçmez; uzun ve imkânsız hızlı satır uydurmadır.
def hiz_asiri(metin, sn):
    n = len(re.findall(r"\w+", metin or ""))
    return n >= 15 and sn > 0 and n / max(sn, 1.0) > 8
# v0.113.1 (22 Ekim test toplantısı): iki uydurma biçimi süzgeçten geçti — (1) harf döngüsü tek sözcükte ("bildiririririr…" yüzlerce harf; sözcük düzeyindeki
# tekrar_dongu görmez), (2) cümlenin art arda aynen tekrarı ("Marvin burada mısın? Marvin burada mısın? Marvin burada mısın?": asistan iki kez cevap verdi).
# Harf döngüsü: 1–4 harflik birim art arda ≥ 7 kez → bir kez (rakam sayılmaz: "10000000" kalır). Cümle: ≥ 3 sözcüklük cümle art arda aynen gelirse bir kez.
HARF_DONGU_RX = re.compile(r"((?:[^\W\d_]){1,4}?)\1{6,}")
def tekrar_sadelestir(metin):
    m = HARF_DONGU_RX.sub(r"\1", metin or "")
    parca = re.split(r"(?<=[.!?…])\s+", m.strip()); out = []
    anah = lambda c: " ".join(re.findall(r"\w+", c.lower()))
    for c in parca:
        if out and len(anah(c).split()) >= 3 and anah(c) == anah(out[-1]): continue
        out.append(c)
    return " ".join(out) if m.strip() else m
def cozme_ayari(sn):
    # canlı parça: yeniden deneme 2 sıcaklıkla, belirteç sesin süresiyle sınırlı (sn başına 20, en az 48). Varsayılan 6 sıcaklık × 224 belirteç
    # kısa parçada tekrar döngüsünü 6 kez baştan çözüyordu: 11 Ekim toplantılarında uydurma işleri ortalama 11,6 sn, işçi süresinin %59'u.
    return {"temperature": (0.0, 0.2), "sample_len": min(224, max(48, int(sn * 20)))}
# whisper.cpp + Core ML motoru (S188: Apple Silicon'da varsayılan, ayar whisper_motor: mlx kapatır; aktarıcı SUFLOR_WHISPER_CPP=<ortak>/whisper-cpp verir). Aynı turbo q8 modeli,
# kodlayıcı Neural Engine'de. 20 Ekim kıyası (testler/asr-kiyas-20261020.md, 1.093 öğe): 4–6 sn parça 1,40 → 0,60 sn, kısa parça p90
# 2,57 → 0,55 sn, canlı parça Türkçe hata %12,5 → %12,7, uydurma bu dosyanın süzgeciyle aynı (%23). Canlı döngü; ses izi
# (ECAPA) MLX'te kalır. Sunucu yalnız 127.0.0.1'de; işçi öldürülse de bekçi kabuk sunucuyu kapatır.
# Açılamazsa (CppHata.sinif): dosya_yok · calismiyor (ikili başlamadı) · macos_surum (ikili bu macOS için derlenmemiş) · coreml (kodlayıcı yüklenemedi) ·
# sunucu_kapandi (başka nedenle çıktı) · zaman_asimi · isinma (sunucu açık, ilk çözüm başarısız) · diger. main() bunu MLX yedeğine çevirir; sınıf beta verisine gider.
CPP_HATA = ("dosya_yok", "calismiyor", "macos_surum", "coreml", "sunucu_kapandi", "zaman_asimi", "isinma", "diger")
class CppHata(RuntimeError):
    def __init__(s, sinif, mesaj): RuntimeError.__init__(s, mesaj); s.sinif = sinif
def cpp_hata_sinif(e):
    if isinstance(e, CppHata): return e.sinif
    if isinstance(e, FileNotFoundError): return "dosya_yok"
    if isinstance(e, (PermissionError, OSError)): return "calismiyor"
    return "diger"
def cpp_cikti_sinif(son):
    if re.search(r"(?i)dyld|newer than running OS|incompatible|Symbol not found|bad CPU type", son): return "macos_surum"
    if re.search(r"(?i)core ?ml|mlmodelc", son): return "coreml"
    return "sunucu_kapandi"
class CppMotor:
    def __init__(s, dizin):
        import socket, subprocess, urllib.request, threading, collections
        so = socket.socket(); so.bind(("127.0.0.1", 0)); s.port = so.getsockname()[1]; so.close()
        s.ad = "whisper.cpp:ggml-large-v3-turbo-q8_0+coreml"; s.url = f"http://127.0.0.1:{s.port}/inference"
        for f in ("whisper-server", "ggml-large-v3-turbo-q8_0.bin", "ggml-large-v3-turbo-encoder.mlmodelc"):
            if not os.path.exists(os.path.join(dizin, f)): raise CppHata("dosya_yok", f"{f} yok")
        # -nlp: yoksa her istekte dil olasılığı için kodlayıcı ikinci kez çalışıyor; -ml 100000: yoksa bölüm 60 karakterde sözcük ortasından kesiliyor
        # sunucunun çıktısı yalnız son satırları bellekte tutulur (açılmazsa nedeni sınıflamak için: Core ML, macOS sürümü); diske yazılmaz
        try:
            s.p = subprocess.Popen([os.path.join(dizin, "whisper-server"), "-m", os.path.join(dizin, "ggml-large-v3-turbo-q8_0.bin"), "--host", "127.0.0.1",
                                    "--port", str(s.port), "-t", "4", "-l", "tr", "-bs", "-1", "-et", "2.4", "-lpt", "-1.0", "-nth", "0.6", "-nlp",
                                    "-ml", "100000", "--public", "/nonexistent"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   env=dict(os.environ, WHISPER_TEMP_MAX="0.2"))  # yeniden deneme 0 → 0,2'de durur (MLX'teki cozme_ayari gibi; yamalı sunucu)
        except OSError as e: raise CppHata(cpp_hata_sinif(e), f"whisper-server başlatılamadı ({e.__class__.__name__})")
        s.cikti = collections.deque(maxlen=40)
        def _oku():
            for l in iter(s.p.stderr.readline, b""): s.cikti.append(l.decode("utf-8", "replace").rstrip())
        threading.Thread(target=_oku, daemon=True).start()
        # bekçi: işçi çıkınca (öldürülüp zombi kalsa da) sunucuyu kapatır; normal çıkışta atexit hemen kapatır
        subprocess.Popen(["/bin/sh", "-c", f"while d=$(ps -o stat= -p {os.getpid()} 2>/dev/null) && [ \"${{d#Z}}\" = \"$d\" ] && kill -0 {s.p.pid} 2>/dev/null; "
                          f"do sleep 1; done; kill {s.p.pid} 2>/dev/null"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import atexit; atexit.register(lambda: s.p.poll() is None and s.p.terminate())
        t0 = time.time()  # ilk açılışta Neural Engine derlemesi 30–60 sn (macOS sonra önbellekten verir; M1/M2'de ölçülmedi)
        sinir = float(os.environ.get("SUFLOR_CPP_ACILIS_SN") or 170)
        while True:
            if s.p.poll() is not None:
                time.sleep(0.2); raise CppHata(cpp_cikti_sinif("\n".join(s.cikti)), f"whisper-server kapandı ({s.p.returncode})")
            try: urllib.request.urlopen(f"http://127.0.0.1:{s.port}/", timeout=2); break
            except urllib.error.HTTPError: break
            except Exception: pass
            if time.time() - t0 > sinir: s.p.kill(); raise CppHata("zaman_asimi", f"whisper-server {sinir:.0f} sn'de açılmadı")
            time.sleep(0.2)
        s.acilis_sn = round(time.time() - t0, 1)
        try: from mlx_whisper.tokenizer import LANGUAGES; s.kod = {v: k for k, v in LANGUAGES.items()}
        except Exception: s.kod = {"turkish": "tr", "english": "en"}
    def kapat(s):
        try:
            if s.p.poll() is None: s.p.terminate(); s.p.wait(5)
        except Exception:
            try: s.p.kill()
            except Exception: pass
    def istek(s, a, language=None, initial_prompt=None):
        import io, wave, uuid, urllib.request, numpy as np
        b = io.BytesIO()
        with wave.open(b, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())
        alan = {"language": language or "auto", "prompt": initial_prompt or "", "temperature": "0.0", "temperature_inc": "0.2",
                "response_format": "verbose_json", "no_timestamps": "false", "no_language_probabilities": "true", "max_len": "100000"}
        sn = uuid.uuid4().hex; g = []
        for k, v in alan.items(): g += [f"--{sn}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode(), str(v).encode("utf-8"), b"\r\n"]
        g += [f"--{sn}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"p.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode(), b.getvalue(), b"\r\n", f"--{sn}--\r\n".encode()]
        q = urllib.request.Request(s.url, data=b"".join(g), headers={"Content-Type": f"multipart/form-data; boundary={sn}"})
        with urllib.request.urlopen(q, timeout=120) as y: return json.loads(y.read().decode("utf-8"))
    def __call__(s, a, language=None, initial_prompt=None, **_):  # mlx_whisper.transcribe biçiminde sonuç
        r = s.istek(a, language, initial_prompt)
        seg = [{"text": x.get("text") or "", "start": float(x.get("start") or 0), "end": float(x.get("end") or 0),
                "no_speech_prob": x.get("no_speech_prob", 0), "avg_logprob": x.get("avg_logprob", 0), "kp": min([w.get("probability", 1) for w in x.get("words") or [] if (w.get("word") or "").strip(" .,!?…")] or [1]),
                "compression_ratio": sikisma_orani(x.get("text") or "")} for x in r.get("segments") or []]  # 3 Kasım: sunucu vermiyor; MLX'teki 2,4 süzgeci cpp'de de çalışsın
        d = str(r.get("language") or "").lower()
        return {"text": "".join(x["text"] for x in seg), "segments": seg, "language": s.kod.get(d, d) or language}
CPP = None
def sikisma_orani(t):  # Whisper'ın compression_ratio'su (metin bayt / zlib bayt); tekrar döngüsünde büyür
    b = t.strip().encode("utf-8"); return round(len(b) / len(zlib.compress(b)), 3) if b else 0
def mlx_model_var():  # MLX Whisper modeli diskte mi (çevrimdışı açılabilir mi) — yoksa yedek MLX'e geçmeden aktarıcıya "mlx_yok" denir
    if os.path.isdir(MODEL): return os.path.exists(os.path.join(MODEL, "weights.safetensors")) or os.path.exists(os.path.join(MODEL, "weights.npz"))
    import glob as _g
    kok = os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub", "models--" + MODEL.replace("/", "--"))
    return bool(_g.glob(os.path.join(kok, "snapshots", "*", "weights.*"))) and os.path.exists(os.path.join(kok, "refs", "main"))
def dil_olasilik(a):  # Whisper'ın dil tahmini (ilk 30 sn): {dil: olasılık}; yalnız kodlayıcı + tek belirteç, çözmeden ucuz
    if CPP:  # whisper.cpp: olasılık istenmiyor (-nlp); algılanan dil tek aday olarak döner, metin boşsa geçiş zaten yapılmaz
        r = CPP(a); return {r["language"]: 1.0} if r.get("language") else {}
    import mlx.core as mx
    from mlx_whisper.transcribe import ModelHolder
    from mlx_whisper.audio import log_mel_spectrogram, pad_or_trim, N_FRAMES, N_SAMPLES
    m = ModelHolder.get_model(MODEL, mx.float16)
    _, pr = m.detect_language(pad_or_trim(log_mel_spectrogram(a, n_mels=m.dims.n_mels, padding=N_SAMPLES), N_FRAMES, axis=-2).astype(mx.float16))
    return pr[0] if isinstance(pr, list) else pr
# başka dile geçişte kısa parçada Whisper'ın en sık uydurması (12 Ekim ölçümü: Türkçe kayıttaki gürültü İngilizce çözülünce "Thank you.")
UYDURMA_EN = re.compile(r"^(thank you|thanks|amen|cheers|bye|okay|you|so)[.!]?$", re.I)
DIL_GECIS = 0.9  # dayatılan dil boş çıkınca öbür dile geçiş için en düşük olasılık
# Kısa kalıp konuşmasız parçadan (13 Ekim, gercek-ses/uydurma-topla.py): İngilizce kipte oda gürültüsü, nefes, klavye, uğultu ve sıfır ses
# 36 parçanın 34'ünde "Thank you." / "You" yazıldı ve süzgeçten geçti (yukarıdaki kural yalnız toplantı dili Türkçeyken atıyordu). Gerçek kısa
# konuşmada (Yüksek Mahkeme kaydı, ≤ 4 sözcüklü 32 parça) 20 ms karelerin ses düzeyi %90'lık/%10'luk oranı ≥ 6,5 ve %90'lık ≥ 0,067; düz gürültüde
# oran ~1, nefes ve klavyede oran yüksek ama düzey < 0,02. Yalnız UYDURMA_EN kalıbına uyan tüm metinde, toplantı dili ne olursa olsun.
def konusma_var(a, np, sr=16000):
    k = sr // 50; m = len(a) // k
    if m < 5: return False
    r = np.sqrt((a[:m * k].reshape(m, k) ** 2).mean(1)) + 1e-6
    p90 = float(np.percentile(r, 90))
    return p90 >= 0.02 and p90 / float(np.percentile(r, 10)) >= 3
def tr_harf(x, dil):  # Türkçe çözümde Azerice "ə" (11 Ekim: arka plandaki haber "muhabirənin … adreslər" yazıldı) → "e"
    return x.replace("ə", "e").replace("Ə", "E") if dil == "tr" else x
# Tamamı büyük harfli çıktı (3 Kasım, testler/kisa-soru-cpp-mlx-20261103.md): istem yalnız büyük harfli kısaltmalardan oluşunca (sözlüğü boş yeni kurulum)
# whisper.cpp kısa Türkçe soruyu "BÜPÇE KAÇ LİRA?" diye büyük harfle yazıyor. Dil tr iken ≥ 3 harf ve ≥ 2 sözcük, harflerin tamamı büyükse Türkçe kuralla küçültülür;
# istemde geçen ve istekle gelen "kisaltma" (sözlüğün büyük harfli terimleri; istem 215 belirteçle sınırlı) kısaltmalar büyük kalır, cümle başları büyütülür. Tek sözcük ("AWS.") dokunulmaz.
def _tr_alt(w): return w.replace("İ", "i").replace("I", "ı").lower()
def _tr_ust(c): return {"i": "İ", "ı": "I"}.get(c, c.upper())
def buyuk_harf_duzelt(x, dil, istem="", kisaltma=()):
    if dil != "tr" or not x: return x
    harf = [c for c in x if c.isalpha()]
    if len(harf) < 3 or not all(c.isupper() for c in harf) or len(x.split()) < 2: return x
    kisa = {w.strip(".,:;!?…()\"'") for w in (istem or "").split()}; kisa = {w for w in kisa if len(w) >= 2 and w.isalpha() and w.isupper()} | set(kisaltma or ())  # R17: kisaltma = aktarıcının gönderdiği sözlük kısaltmaları (istemde olmasa da korunur)
    cikti, bas = [], True
    for w in x.split():
        cek = w.strip(".,:;!?…()\"'")
        if cek in kisa: y = w
        else:
            y = _tr_alt(w)
            if bas:
                i = next((k for k, c in enumerate(y) if c.isalpha()), None)
                if i is not None: y = y[:i] + _tr_ust(y[i]) + y[i + 1:]
        bas = w[-1:] in ".?!…"
        cikti.append(y)
    y = " ".join(cikti)
    if y == x: return x
    global _BUYUK_LOG
    if not _BUYUK_LOG: _BUYUK_LOG = True; sys.stderr.write("WHISPER: tamamı büyük harf çıktı küçültüldü\n")
    return y
_BUYUK_LOG = False
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
# Ses izi kapısı, gölge kip (2 Kasım): "ben" kanalı parçası 1,5 sn pencere / 0,5 sn adımla taranır, her pencerenin kullanıcı profiline kosinüs benzerliği döner.
# Karar aktarıcıda (yalnız kayda yazılır; Whisper'a giden ses değişmez). Kısa parça (≤ 1,5 sn) tek pencere; sonda 0,25 sn'den fazla açıkta kalırsa sona hizalı son pencere.
KAPI_PEN_SN, KAPI_ADIM_SN, KAPI_EN_COK = 1.5, 0.5, 40
def kapi_pencereler(n, sr=SR):
    w, h = int(KAPI_PEN_SN * sr), int(KAPI_ADIM_SN * sr)
    if n <= w: return [(0, n)]
    o = [(i, i + w) for i in range(0, n - w + 1, h)]
    if o[-1][1] < n - sr // 4: o.append((n - w, n))
    return o[:KAPI_EN_COK]
def kapi_benzerlik(iz, a, profil, np):  # profil: birim vektör; dönen: pencere başına kosinüs (2 ondalık)
    return [round(float(np.dot(iz(a[b:e]), profil)), 2) for b, e in kapi_pencereler(len(a))]
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
    global CPP
    t = time.time(); model_ad = MODEL; cpp = None
    try: import numpy as np
    except Exception as e: out({"hata": f"model yüklenemedi: {e.__class__.__name__}: {str(e)[:200]}"}); return 1
    # S188 (3 Kasım): whisper.cpp varsayılan motor; açılamazsa (sunucu başlamadı, Core ML, ısınma) aynı süreçte MLX'e geçilir — geçici yedek. Sonuç "cpp"
    # alanıyla döner (aktarıcı günlüğe yazar, o gün cpp'yi yeniden denemez, beta verisine sayar). MLX modeli diskte yoksa "mlx_yok": aktarıcı indirir.
    if os.environ.get("SUFLOR_WHISPER_CPP"):
        tc = time.time(); m = None
        try:
            m = CppMotor(os.environ["SUFLOR_WHISPER_CPP"])
            try: m(np.zeros(16000, np.float32), language="tr")  # ısınma: model belleğe, Core ML çalışıyor mu
            except Exception as e: raise CppHata("isinma", f"ilk çözüm başarısız ({e.__class__.__name__}: {str(e)[:120]})")
            CPP = m; model_ad = m.ad; coz = CPP
            cpp = {"sonuc": "basarili", "sn": round(time.time() - tc, 1), "acilis_sn": m.acilis_sn}
        except Exception as e:
            if m: m.kapat()
            cpp = {"sonuc": "yedek", "hata": cpp_hata_sinif(e), "mesaj": str(e)[:200], "sn": round(time.time() - tc, 1)}
            sys.stderr.write(f"whisper.cpp açılamadı ({cpp['hata']}): {e}\n")
    if not CPP:
        if cpp and not mlx_model_var():
            out({"hata": "whisper.cpp açılamadı, MLX modeli diskte yok", "cpp": cpp, "mlx_yok": True}); return 1
        try:
            import mlx_whisper
            def coz(a, **k): return mlx_whisper.transcribe(a, path_or_hf_repo=MODEL, **k)
            coz(np.zeros(16000, np.float32), language="tr")  # ısınma: model belleğe
        except Exception as e:
            out({"hata": f"model yüklenemedi: {e.__class__.__name__}: {str(e)[:200]}", **({"cpp": cpp} if cpp else {})}); return 1
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
    out({"hazir": True, "model": model_ad, "motor": "cpp" if CPP else "mlx", "sn": round(time.time() - t, 1), "ecapa": bool(iz), **({"cpp": cpp, "yedek": not CPP} if cpp else {})})
    kumeler = []; baslik = None  # karşı kanal kümeleri; yeni toplantıda sıfırlanır
    for satir in sys.stdin:
        if not satir.strip(): continue
        try: p = json.loads(satir)
        except ValueError: continue
        try:
            a = np.frombuffer(base64.b64decode(p["pcm"]), np.int16).astype(np.float32) / 32768
            t = time.time(); dusen = 0
            cozme = cozme_ayari(len(a) / SR)
            if tok: istem, dusen = istem_kur(tok, p.get("istem") or "", p.get("onceki") or "")
            else: istem = " ".join(x for x in (p.get("istem") or "", p.get("onceki") or "") if x).strip() or None
            # karma dil (whisper.cpp): dil sabitken whisper.cpp İngilizce konuşmayı Türkçeye "çevirip" anlamsız metin yazıyor (20 Ekim terimli kayıt:
            # "Let me switch to English…" → "İngilizce bir zaman, çünkü…"; MLX yazmıyordu). Karşı kanalda dil kendiliğinden bulunur (yalnız tr/en;
            # başkası çıkarsa sabit dilde yeniden): parça ~0,6 → ~1,1 sn. Kullanıcının kanalı ve Konuş sabit dilde kalır (hız orada önemli).
            # v0.101.4: Konuş da (oto_dil) — yalnız sorunun ilk parçasında; aktarıcı sonraki parçaları bulunan dille gönderir (+0,5 sn parça başına yalnız bir kez)
            oto = bool(CPP) and (p.get("kanal") == "karsi" or p.get("oto_dil") is True) and p.get("dil") in ("tr", "en") and not p.get("dil_kilit")  # dil kilidi: kısa parçada dil algılama yok
            r = coz(a, language=None if oto else (p.get("dil") or None), initial_prompt=istem,
                                       condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4, **cozme)
            if oto and r.get("language") not in ("tr", "en"):
                r = coz(a, language=p["dil"], initial_prompt=istem, condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4, **cozme)
            # karışık dil (gündem dil=karisik): yalnız izin verilen diller (tr/en); Whisper başkasını bulursa (11 Ekim: iki Türkçe satır İzlandaca)
            # kanalın son dilinde (yoksa ilk izinli dilde) yeniden
            if not p.get("dil") and p.get("diller") and r.get("language") not in p["diller"]:
                r = coz(a, language=p.get("dil_yedek") if p.get("dil_yedek") in p["diller"] else p["diller"][0],
                                           initial_prompt=istem, condition_on_previous_text=False, no_speech_threshold=0.6, compression_ratio_threshold=2.4, **cozme)
            # dil geçişi (v0.29.2, S36): toplantı dili dayatılmış (tr/en) ve sonuç boşsa Whisper'ın dil tahminine bakılır; öbür dil (en/tr)
            # ≥ %80 ise o dilde yeniden çözülür (12 Ekim: Türkçe toplantıda İngilizce konuşan karşı tarafın 62 parçası boş kalmıştı).
            # Dayatma kalkmaz: karışık kipte Türkçe kayıttaki gürültü "Thank you." diye yazılıyor ve süre iki katına çıkıyordu.
            gec_dil = None
            def _bos(rr): return not any(gecerli(s, (s.get("text") or "").strip()) for s in rr.get("segments") or [])
            if oto and r.get("language") != p["dil"] and not _bos(r): gec_dil = (r.get("language"), None)
            if p.get("dil") in ("tr", "en") and p.get("dil_algila") and not oto and _bos(r):
                obur = "en" if p["dil"] == "tr" else "tr"
                try: pr = dil_olasilik(a)
                except Exception: pr = {}
                if pr.get(obur, 0) >= DIL_GECIS:
                    r2 = coz(a, language=obur, initial_prompt=istem, condition_on_previous_text=False,
                                                no_speech_threshold=0.6, compression_ratio_threshold=2.4, **cozme)
                    if not _bos(r2): r = r2; gec_dil = (obur, round(float(pr[obur]), 2))
            tut, atla, atilan = [], 0, []  # atilan: aktarıcı canli/uydurma-adaylari.jsonl'e yazar (uydurma listesini kendi kayıtlarımızdan büyütmek için)
            for s in r.get("segments") or []:
                x, imza = uydurma_on_kirp((s.get("text") or "").strip())
                if imza: atilan.append(imza)
                if not x or UYDURMA.search(x) or (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -0.8) \
                        or s.get("compression_ratio", 0) > 2.4 or s.get("avg_logprob", 0) < -1.2: atla += 1; atilan += [x] if x else []; continue
                tut.append((s, x))
            metin = buyuk_harf_duzelt(tr_harf(" ".join(x for _, x in tut).strip(), r.get("language")), r.get("language"), istem, p.get("kisaltma"))
            # toplantı dili dışındaki İngilizce (geçişle ya da kanal belleğiyle) kısa kalıp → uydurma
            if p.get("ana_dil") and r.get("language") == "en" != p["ana_dil"] and UYDURMA_EN.match(metin): atilan.append(metin); metin = ""; atla += 1
            if metin and UYDURMA_EN.match(metin) and not konusma_var(a, np): atilan.append(metin); metin = ""; atla += 1
            # kısa satırda web adresi: Whisper'ın video sonu uydurması ("www.feyyaz.tv" — 1 Ekim headless bip sesi denemesi)
            if metin and len(metin.split()) <= 6 and re.search(r"\bwww\.|https?://|\.(com|tv|net|org)(\.tr)?\b", metin, re.I): atilan.append(metin); metin = ""; atla += 1
            # istemi geri okuma. v0.88.2 (19 Ekim 18.20 deneme): istemde toplantının önceki satırları da var; kullanıcı aynı sözü yeniden söyleyince
            # ("Test toplantısı başladı") gerçek satır atılıyordu. Yalnız önceki satırlarla eşleşen metin, parçada konuşma sesi varsa kalır.
            # v0.140.0 (27 Ekim, ikinci hesap): kullanıcının tek başına söylediği asistan adı ("Sera,") istemin başında geçtiği için atılıyordu, arkasından gelen
            # talimat hitapsız kalıp kayboldu. Parçada konuşma sesi varsa yalnız addan oluşan satır kalır (aktarıcı onu sonraki satırlara hitap olarak taşır).
            # 1 Kasım: bu toplantının kişi adları da istemde (aktarıcı "kisiler" verir); tek başına söylenen ad ("Ayşe.") konuşma sesiyle gelirse kalır.
            adlar = {str(x).lower() for x in (p.get("hitap") or [])} | {w for x in (p.get("kisiler") or []) for w in (str(x).lower(), str(x).lower().split()[0] if str(x).split() else "")} - {""}
            adli = bool(metin and adlar and metin.strip(" .,:;!?…").lower() in adlar and konusma_var(a, np))
            if istem and metin and not adli and metin.lower().strip(" .") in istem.lower():
                terim = metin.lower().strip(" .") in (p.get("istem") or "").lower()
                if terim or not konusma_var(a, np): atilan.append(metin); metin = ""; atla += 1
            # yarım yarım geri okuma (20 Ekim, whisper.cpp + sessiz parça: "Grafan, Jira, Promethu."): her sözcüğün en az %60'ı (≥ 3 harf) bir
            # terim sözcüğüyle aynı başlıyorsa ve parçada konuşma sesi yoksa uydurma. Gerçek kısa söz ("Jira'ya baktım") en az bir terim dışı sözcük taşır.
            if metin and p.get("istem") and not konusma_var(a, np):
                tw = re.findall(r"\w{3,}", (p.get("istem") or "").lower()); mw = re.findall(r"\w+", metin.lower())
                ortak = lambda w, t: len(os.path.commonprefix([w, t])) >= max(3, int(0.6 * len(w) + 0.5))  # bozuk yazılan terim de ("promethu")
                if mw and all(len(w) >= 3 and any(ortak(w, t) for t in tw) for w in mw): atilan.append(metin); metin = ""; atla += 1
            if metin and hiz_asiri(metin, len(a) / SR): atilan.append(metin); atla += 1; metin = ""  # imkânsız söz hızı (kısa parçada yüzlerce sözcük)
            if metin and tekrar_dongu(metin):  # tekrar döngüsü uydurması (öndeki gerçek söz kalır)
                kirp = tekrar_kirp(metin); atilan.append(metin); atla += 1; metin = kirp or ""
            if metin and (s_ := tekrar_sadelestir(metin)) != metin: atilan.append(metin); metin = s_  # v0.113.1: harf döngüsü, art arda aynı cümle
            if metin:  # 30 Ekim: "... ... ..." öbekleri (sözsüz seste) — öbekler silinir, sözcüğü kalmayan satır atılır
                m_, at_ = nokta_ayikla(metin, len(a) / SR, p.get("hitap"))
                if at_ is not None: atilan.append(at_); atla += 0 if m_ else 1; metin = m_
            try: ses = ses_olc(a, np) if metin else None
            except Exception: ses = None
            km = {}
            if p.get("baslik") != baslik: kumeler = []; baslik = p.get("baslik")
            oda = (p.get("kanal") == "ben" and p.get("oda")) or (p.get("kanal") == "bas" and p.get("iz_iste"))  # kullanıcı kanalında (ikinci kişi/ses kilidi) ya da sohbet sorusunda iz: kümesiz, aktarıcı profille karşılaştırır
            if iz and metin and (p.get("kanal") == "karsi" or oda) and len(a) >= SR * 0.5:
                # ses izi satırla geri döner (float16, base64): aktarıcı <toplantı>.sesizi.log'a yazar, toplantı sonunda toplu kümelenir (--toplu)
                try:
                    b64 = lambda v: base64.b64encode(v.astype(np.float16).tobytes()).decode()
                    e = iz(a); km = {"iz": b64(e)}
                    if not oda and len(a) >= SR * 0.8: km.update(kumele(iz, kumeler, a, np, e))
                    # birden çok bölümlü parçada bölüm (cümle) başına iz: hızlı söz devrinde canlı parça iki kişiyi içerir (11 Ekim, Easy Turkish:
                    # canlı parçaların 6/15'i) ve parça izi ikisini tek kişide birleştirir (%62 → bölüm izleriyle %100). n = bölümün sözcük sayısı
                    # (aktarıcının satır metnini bölmesi için); < 0,5 sn bölümün izi yok.
                    if len(tut) > 1 and not oda:
                        km["bol"] = [dict({"s": round(sg["start"], 2), "e": round(sg["end"], 2), "n": len(x.split())},
                                          **({"iz": b64(iz(a[int(sg["start"] * SR):int(sg["end"] * SR)]))} if (sg["end"] - sg["start"]) >= 0.5 else {})) for sg, x in tut]
                except Exception as e: km = {"kume_hata": f"{e.__class__.__name__}: {str(e)[:120]}"}
            kapi = {}
            if iz and p.get("kanal") == "ben" and p.get("kapi_profil") and len(a) >= SR * 0.3:  # gölge kip: yalnız ölçer, metni/sesi değiştirmez
                try:
                    t_k = time.time(); pf = np.frombuffer(base64.b64decode(p["kapi_profil"]), np.float16).astype(np.float32); pf = pf / (np.linalg.norm(pf) + 1e-9)
                    kapi = {"kapi": kapi_benzerlik(iz, a, pf, np), "kapi_ms": round((time.time() - t_k) * 1000), "atilan_harf": sum(len(re.findall(r"\w", x)) for x in atilan)}
                except Exception as e: kapi = {"kapi_hata": f"{e.__class__.__name__}: {str(e)[:80]}"}
            out({"id": p.get("id"), "text": metin, "sn": round(time.time() - t, 2), "dil": r.get("language"), "atlanan": atla, **({"atilan": [x[:80] for x in atilan[:3]]} if atilan else {}), **({"dil_gecis": gec_dil[1]} if gec_dil and metin else {}), **({"istem_dusen": dusen} if dusen else {}), **({"sayi_suphe": True} if sayi_suphe(metin) else {}), **({"istem_tok": len(tok.encode(" " + istem))} if tok and istem else {}), **({"ses": ses} if ses else {}), **({"lp": round(min([s.get("avg_logprob", 0) for s, _ in tut] or [0]), 3), "kp": round(min([s.get("kp", 1) for s, _ in tut] or [1]), 3)} if p.get("dil_kilit") and tut else {}), **km, **kapi})
        except Exception as e:
            out({"id": p.get("id"), "hata": f"{e.__class__.__name__}: {str(e)[:200]}"})
    return 0
def gecerli(s, x):  # canlı işçideki uydurma süzgeci (bölüm başına)
    return bool(x) and not UYDURMA.search(x) and not (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -0.8) \
        and s.get("compression_ratio", 0) <= 2.4 and s.get("avg_logprob", 0) >= -1.2 \
        and not (len(x.split()) <= 6 and re.search(r"\bwww\.|https?://|\.(com|tv|net|org)(\.tr)?\b", x, re.I))
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
    # bölümleri farklı kümede olan satır), "n": satır, "k": küme sayısı, "merkez": {no: süre ağırlıklı ortalama iz (float16 base64, birim)},
    # "sn": {no: izli konuşma sn}} — merkez ses izi hafızası içindir (toplanti-claude.py hafiza_*)
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
    top_iz, top_sn = {}, {}
    for n, k in enumerate(et):
        if k is None or k not in ad or birim[n][1] is None: continue
        no = ad[k]; top_iz[no] = top_iz.get(no, 0) + birim[n][0] * birim[n][1]; top_sn[no] = top_sn.get(no, 0) + birim[n][0]
    merkez = {no: base64.b64encode((v / (np.linalg.norm(v) + 1e-9)).astype(np.float16).tobytes()).decode() for no, v in top_iz.items() if top_sn[no] > 0}
    out({"kume": km, "bol": bl, "n": len(satir), "k": len(ad), "merkez": merkez, "sn": {no: round(v, 1) for no, v in top_sn.items()}}); return 0
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
    sys.exit(main())
