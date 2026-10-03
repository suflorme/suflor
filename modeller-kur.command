#!/bin/sh
# Suflor.me — yerel modeller ve Python ortamları (v0.8.5). Yeni Mac'te ya da bozulunca bir kez çalıştır; olanı yeniden kurmaz.
#   whisper-venv  : mlx-whisper (konuşma tanıma, Apple GPU)                    ~760 MB
#   whisper-modeller: mlx-community/whisper-large-v3-turbo (Hugging Face)      ~1,6 GB
#   ses-venv      : PyTorch + FunASR + SpeechBrain (duygu, konuşmacı ayırma)    ~860 MB
#   ses-modeller  : emotion2vec/emotion2vec_plus_base (~1,0 GB) + speechbrain/spkrec-ecapa-voxceleb (~85 MB)
# İnternet yalnız bu kurulumda gerekir; aktarıcı modelleri çevrimdışı açar (HF_HUB_OFFLINE=1). Toplam ~4,3 GB disk.
# Sürümler 2 Ekim 2026'da çalışan kurulumdan sabitlendi. Sonra: ./aktarici-kur.command
set -e
# v0.9.2: modeller ve ortamlar iki macOS hesabında ortak: /Users/Shared/Suflor (ayar.json "ortak"). Başka hesap kurduysa
# bu hesap yalnız okur — eksik yoksa hiçbir şey indirmez; eksik varsa kuran hesapta çalıştırılmalı.
APP="$(/usr/bin/python3 -c "import json,os
v={'ortak':'/Users/Shared/Suflor'}
try: v.update(json.load(open(os.path.expanduser('~/Library/Application Support/Suflor/ayar.json'))))
except Exception: pass
print(os.path.expanduser(v['ortak']))")"; PY=/usr/bin/python3
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

if ok "$APP/ses-venv/bin/python" "import funasr, speechbrain, torch"; then echo "✓ ses-venv var"
else
  echo "→ ses-venv kuruluyor (~860 MB)…"; $PY -m venv "$APP/ses-venv"
  "$APP/ses-venv/bin/python" -m pip install -q --upgrade pip
  "$APP/ses-venv/bin/python" -m pip install -q "torch==2.8.0" "torchaudio==2.8.0" "numpy==2.0.2" "speechbrain==1.1.1" "funasr==1.4.16"
fi
mkdir -p "$APP/ses-modeller"
if [ -f "$APP/ses-modeller/emotion2vec_plus_base/model.pt" ] && [ -f "$APP/ses-modeller/spkrec-ecapa-voxceleb/embedding_model.ckpt" ]; then echo "✓ ses modelleri var"
else
  if ! rel_indir suflor-ses-modeller.tar; then
  echo "→ ses modelleri Hugging Face'ten indiriliyor (~1,1 GB)…"
  "$APP/ses-venv/bin/python" - <<'P'
from huggingface_hub import snapshot_download
for repo, desen in (("speechbrain/spkrec-ecapa-voxceleb", ["*.ckpt", "*.yaml", "*.json", "label_encoder.txt"]),
                    ("emotion2vec/emotion2vec_plus_base", ["model.pt", "config.yaml", "configuration.json", "tokens.txt"])):
    snapshot_download(repo, local_dir="ses-modeller/" + repo.split("/")[1], allow_patterns=desen)
P
  fi
fi

echo "→ Deneme: modeller çevrimdışı açılıyor mu…"
HF_HOME="$APP/whisper-modeller" HF_HUB_OFFLINE=1 "$APP/whisper-venv/bin/python" -c "
import numpy as np, mlx_whisper; mlx_whisper.transcribe(np.zeros(16000, np.float32), path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='tr'); print('✓ Whisper açılıyor')"
HF_HUB_OFFLINE=1 SUFLOR_SES_MODELLER="$APP/ses-modeller" "$APP/ses-venv/bin/python" - <<'P' 2>/dev/null
import os, sys, numpy as np
sys.stdout = sys.stderr  # FunASR/SpeechBrain mesajları gizlensin (stderr kapalı), sonuç satırı __stdout__'a
M = os.environ["SUFLOR_SES_MODELLER"]
from funasr import AutoModel
AutoModel(model=M + "/emotion2vec_plus_base", disable_update=True, device="cpu", log_level="ERROR")
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy
d = M + "/spkrec-ecapa-voxceleb"
EncoderClassifier.from_hparams(source=d, savedir=d, overrides={"pretrained_path": d}, run_opts={"device": "cpu"}, local_strategy=LocalStrategy.NO_LINK)
sys.__stdout__.write("✓ duygu modeli ve konuşmacı ayırma açılıyor\n")
P
chmod -R go+rX "$APP" 2>/dev/null || true  # diğer hesap okuyabilsin
echo "Tamam. Şimdi: ./aktarici-kur.command"
