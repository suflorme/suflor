#!/bin/sh
# Suflor.me — yerel modeller ve Python ortamları (v0.8.5). Yeni Mac'te ya da bozulunca bir kez çalıştır; olanı yeniden kurmaz.
#   whisper-venv  : mlx-whisper (konuşma tanıma, Apple GPU)                    ~760 MB
#   whisper-modeller: mlx-community/whisper-large-v3-turbo (Hugging Face)      ~1,6 GB (+ yerelde 8 bit kopyası ~0,8 GB, v0.13.14)
#   ses-modeller  : speechbrain/spkrec-ecapa-voxceleb (~85 MB) → ecapa-mlx.npz (konuşmacı ayırma, Whisper işçisinde MLX ile)
# İnternet yalnız bu kurulumda gerekir; aktarıcı modelleri çevrimdışı açar (HF_HUB_OFFLINE=1). Toplam ~3,3 GB disk.
# v0.13.12: ses-venv (PyTorch + FunASR + SpeechBrain) ve duygu modeli (emotion2vec+) kalktı; eski kurulumda duruyorlarsa kullanılmaz.
# Sürümler 2 Ekim 2026'da çalışan kurulumdan sabitlendi. Sonra: ./aktarici-kur.command
set -e
# v0.9.2: modeller ve ortamlar iki macOS hesabında ortak: /Users/Shared/Suflor (ayar.json "ortak"). Başka hesap kurduysa
# bu hesap yalnız okur — eksik yoksa hiçbir şey indirmez; eksik varsa kuran hesapta çalıştırılmalı.
APP="$(/usr/bin/python3 -c "import json,os
v={'ortak':'/Users/Shared/Suflor'}
try: v.update(json.load(open(os.path.expanduser('~/Library/Application Support/Suflor/ayar.json'))))
except Exception: pass
print(os.path.expanduser(v['ortak']))")"; PY=/usr/bin/python3
KOD="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$APP" 2>/dev/null || true; cd "$APP"
if [ ! -w "$APP" ]; then echo "Not: $APP başka bir hesabın — yalnız denetlenecek, kurulum yapılmayacak."; fi
bos=$(df -g "$HOME" | awk 'NR==2{print $4}')
if [ "${bos:-0}" -lt 6 ]; then echo "Diskte ${bos} GB boş — en az 6 GB gerekli. Yer açıp yeniden çalıştır."; exit 1; fi
ok() { "$1" -c "$2" >/dev/null 2>&1; }
# v0.9.3: modeller önce GitHub Release'ten (ayar model_deposu, yoksa açık depo; etiket modeller-v1; gh oturumu), SHA-256
# doğrulanarak; olmazsa Hugging Face'ten. Python ortamları her zaman sabit sürümlerle kurulur (taşınamazlar).
REL=modeller-v1; DEPO="$(/usr/bin/python3 -c 'import json,os;p=os.path.expanduser("~/Library/Application Support/Suflor/ayar.json");print((json.load(open(p)) if os.path.exists(p) else {}).get("model_deposu") or "suflorme/suflor")' 2>/dev/null || echo suflorme/suflor)"
rel_indir() {  # $1: arşiv adı → ortak klasöre açar; başarısızsa 1 döner
  command -v gh >/dev/null && gh auth status >/dev/null 2>&1 || return 1
  local t; t="$(mktemp -d)"
  echo "→ $1 GitHub'dan indiriliyor…"
  gh release download "$REL" -R "$DEPO" -p "$1" -p SHA256SUMS -D "$t" || { rm -rf "$t"; return 1; }
  (cd "$t" && grep " $1\$" SHA256SUMS | shasum -a 256 -c -) || { echo "  doğrulama tutmadı"; rm -rf "$t"; return 1; }
  tar -xf "$t/$1" -C "$APP" && rm -rf "$t"
}

if ok "$APP/whisper-venv/bin/python" "import mlx_whisper"; then echo "✓ whisper-venv var"
else
  echo "→ whisper-venv kuruluyor…"; $PY -m venv "$APP/whisper-venv"
  "$APP/whisper-venv/bin/python" -m pip install -q --upgrade pip
  "$APP/whisper-venv/bin/python" -m pip install -q "mlx-whisper==0.4.3" "mlx==0.29.3" "numpy==2.0.2"
fi
if [ -d "$APP/whisper-modeller/hub/models--mlx-community--whisper-large-v3-turbo" ]; then echo "✓ Whisper modeli var"
else
  rel_indir suflor-whisper-large-v3-turbo.tar || { echo "→ Whisper modeli Hugging Face'ten indiriliyor (~1,6 GB)…"
  HF_HOME="$APP/whisper-modeller" "$APP/whisper-venv/bin/python" -c "from huggingface_hub import snapshot_download as s; s('mlx-community/whisper-large-v3-turbo')"; }
fi

mkdir -p "$APP/ses-modeller"; EK="$APP/ses-modeller/spkrec-ecapa-voxceleb"
if [ -f "$EK/embedding_model.ckpt" ]; then echo "✓ ses izi modeli var"
else
  echo "→ ses izi modeli Hugging Face'ten indiriliyor (~85 MB)…"
  "$APP/whisper-venv/bin/python" -c "from huggingface_hub import snapshot_download as s; s('speechbrain/spkrec-ecapa-voxceleb', local_dir='$EK', allow_patterns=['embedding_model.ckpt', 'hyperparams.yaml'])"
fi
if [ -f "$EK/ecapa-mlx.npz" ]; then echo "✓ ses izi ağırlıkları (MLX) var"
else PYTHONDONTWRITEBYTECODE=1 "$APP/whisper-venv/bin/python" "$KOD/whisper-isci.py" --ecapa-donustur "$EK/embedding_model.ckpt" "$EK/ecapa-mlx.npz" \
       || echo "Not: ses izi ağırlıkları dönüştürülemedi — konuşmacı ayırma kapalı kalır, Whisper çalışır"
fi

ORT="$APP"
# v0.13.14: Whisper turbo'nun 8 bit kopyası yerelde bir kez üretilir (indirme yok, ~1 dk, 824 MB); aktarıcı varsa onu kullanır
T="$(ls -d "$ORT"/whisper-modeller/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/* 2>/dev/null | head -1)"
Q8="$ORT/whisper-modeller/hub/models--suflor--whisper-large-v3-turbo-q8/snapshots/yerel"
if [ -n "$T" ] && [ ! -f "$Q8/weights.safetensors" ] && [ -w "$ORT/whisper-modeller/hub" ]; then
  echo "→ Whisper 8 bit modeli hazırlanıyor (bir kez, ~1 dk)…"
  HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 "$ORT/whisper-venv/bin/python" "$KOD/whisper-isci.py" --whisper-nicemle "$T" "$Q8" 2>/dev/null \
    && chmod -R go+rX "$ORT/whisper-modeller/hub/models--suflor--whisper-large-v3-turbo-q8" 2>/dev/null \
    || echo "Not: 8 bit model hazırlanamadı — tam model kullanılır"
fi

echo "→ Deneme: modeller çevrimdışı açılıyor mu…"
HF_HOME="$APP/whisper-modeller" HF_HUB_OFFLINE=1 "$APP/whisper-venv/bin/python" -c "
import numpy as np, mlx_whisper; mlx_whisper.transcribe(np.zeros(16000, np.float32), path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='tr'); print('✓ Whisper açılıyor')"
chmod -R go+rX "$APP" 2>/dev/null || true  # diğer hesap okuyabilsin
echo "Tamam. Şimdi: ./aktarici-kur.command"
