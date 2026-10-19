#!/usr/bin/env python3
# Konuşmasız parçada kısa kalıp (v0.32.12): İngilizce kipte gürültü "Thank you." / "You" yazılıyordu (13 Ekim, gercek-ses/uydurma-topla.py:
# 36 yapay parçanın 34'ü). Gerçek Whisper işçisine yapay gürültü (oda, klavye, sıfır) ve `say` ile okunmuş gerçek kısa sözler verilir:
# gürültü boş döner ve atılan metin "atilan"da gelir; gerçek "Thank you." ve Türkçe kısa cevap korunur. Whisper kurulu değilse atlar (~20 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/uydurma.py      (kaldı → çıkış 1)
import base64, json, os, subprocess, sys, tempfile

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = "/Users/Shared/Suflor/whisper-venv/bin/python"
MODEL = "/Users/Shared/Suflor/whisper-modeller/hub/models--suflor--whisper-large-v3-turbo-q8/snapshots/yerel"
if not (os.path.exists(VENV) and os.path.isdir(MODEL)): print("Whisper kurulu değil — atlandı"); sys.exit(0)
# numpy whisper-venv'de; -I: test/ klasörü yola girmesin (eski test/platform.py — artık platformlar.py —, numpy'ın yüklediği platform modülünün önüne geçiyordu)
if sys.executable != VENV: os.execv(VENV, [VENV, "-I", os.path.abspath(__file__)])
import numpy as np
SR = 16000; rng = np.random.default_rng(5); T = tempfile.mkdtemp(prefix="suflor-uyd-")
def pcm(a): return base64.b64encode((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes()).decode()
def soyle(ses, metin):
    aiff, wav = os.path.join(T, "s.aiff"), os.path.join(T, "s.wav")
    subprocess.run(["say", "-v", ses, "-o", aiff, metin], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", aiff, wav], check=True, capture_output=True)
    b = open(wav, "rb").read(); i = b.find(b"data") + 8
    return np.concatenate([np.zeros(SR // 4), np.frombuffer(b[i:], np.int16).astype(np.float32) / 32768, np.zeros(SR // 4)])
klavye = rng.normal(0, 0.0007, SR * 2)
for t in rng.uniform(0, 1.98, 12): j = int(t * SR); klavye[j:j + 80] += rng.normal(0, 0.15, 80) * np.exp(-np.arange(80) / 15)
parcalar = [("oda gürültüsü", "en", rng.normal(0, 0.003, int(SR * 2.4)), False), ("klavye", "en", klavye, False),
            ("sıfır ses", "en", np.zeros(SR * 2), False), ("oda gürültüsü (Türkçe kip)", "tr", rng.normal(0, 0.003, SR * 2), False),
            ("gerçek 'Thank you.'", "en", soyle("Samantha", "Thank you."), True), ("gerçek Türkçe kısa cevap", "tr", soyle("Yelda", "Tamam, teşekkürler."), True)]
p = subprocess.Popen([VENV, os.path.join(KOD, "whisper-isci.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_WHISPER_MODEL=MODEL))
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
try:
    ilk = json.loads(p.stdout.readline())
    kontrol("işçi hazır", ilk.get("hazir"))
    for i, (ad, dil, a, konusma) in enumerate(parcalar):
        p.stdin.write(json.dumps({"id": str(i), "pcm": pcm(a), "dil": dil, "ana_dil": dil, "kanal": "karsi", "baslik": "d"}) + "\n"); p.stdin.flush()
        r = json.loads(p.stdout.readline()); m = r.get("text") or ""
        if konusma: kontrol(f"{ad} korunur → {m!r}", bool(m.strip()))
        else: kontrol(f"{ad} boş döner" + (f" (atılan: {r['atilan']})" if r.get("atilan") else ""), not m.strip())
    # v0.88.2 (19 Ekim 18.20 deneme): kullanıcı toplantıda daha önce söylediği sözü yeniden söyleyince istemdeki önceki satırla eşleşip atılıyordu
    a = soyle("Yelda", "Test toplantısı başladı.")
    for ad, govde, bek in [("önceki satırla aynı gerçek söz korunur", {"onceki": "Test toplantısı başladım. Bir iki üç."}, True)]:
        p.stdin.write(json.dumps(dict({"id": "o", "pcm": pcm(a), "dil": "tr", "ana_dil": "tr", "kanal": "ben", "baslik": "d"}, **govde)) + "\n"); p.stdin.flush()
        r = json.loads(p.stdout.readline()); kontrol(f"{ad} → {r.get('text')!r}" + (f" (atılan: {r['atilan']})" if r.get("atilan") else ""), bool((r.get("text") or "").strip()) == bek)
finally:
    p.stdin.close(); p.wait(10)
print("GEÇTİ" if not hatalar else f"KALDI: {len(hatalar)} — " + "; ".join(hatalar))
sys.exit(1 if hatalar else 0)
