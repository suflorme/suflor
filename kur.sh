#!/bin/bash
# Suflor.me — tek satır kurulum. Terminal'e yapıştır:
#   curl -fsSL https://raw.githubusercontent.com/suflorme/suflor/main/kur.sh | bash
# Mac'i denetler, kodu ~/Suflor.me klasörüne indirir (git gerekmez) ve kurulum sihirbazını tarayıcıda açar.
# Gerisi sihirbazda. Yeniden çalıştırmak güvenlidir: kodu günceller, ayarlarına ve belgelerine dokunmaz.
set -e
DEPO="suflorme/suflor"; KOD="$HOME/Suflor.me"; PORT=8770
y() { printf "\033[1m%s\033[0m\n" "$1"; }

y "Suflor.me kurulumu"
[ "$(uname -s)" = "Darwin" ] || { echo "Suflor.me yalnız Mac'te çalışır."; exit 1; }
[ "$(uname -m)" = "arm64" ] || { echo "Bu Mac'te Apple Silicon (M serisi) işlemci yok; Suflor.me'nin yerel konuşma tanıması yalnız M serisinde çalışır."; exit 1; }
if ! /usr/bin/python3 -c "import sys; assert sys.version_info >= (3, 9)" >/dev/null 2>&1; then
  echo "Önce Apple'ın komut satırı araçları gerekiyor. Açılan pencerede \"Yükle\"ye bas."
  echo "Kurulum bitince bu satırı Terminal'e yeniden yapıştır."
  xcode-select --install >/dev/null 2>&1 || true; exit 0
fi

echo "→ Suflor.me indiriliyor: $KOD"
GECICI="$(mktemp -d)"
curl -fsSL "https://codeload.github.com/$DEPO/tar.gz/refs/heads/main" | tar -xz -C "$GECICI" --strip-components 1
mkdir -p "$KOD"
# kod dosyaları güncellenir; kullanıcının bu klasöre koyduğu başka bir şey silinmez
(cd "$GECICI" && tar -cf - .) | (cd "$KOD" && tar -xf -)
rm -rf "$GECICI"
chmod +x "$KOD"/*.command "$KOD"/*.sh 2>/dev/null || true
xattr -dr com.apple.quarantine "$KOD" 2>/dev/null || true

echo "→ Kurulum sihirbazı açılıyor"
pkill -f "kurulum.py --port $PORT" >/dev/null 2>&1 || true
mkdir -p "$HOME/Library/Logs"
cd "$KOD" && PYTHONDONTWRITEBYTECODE=1 nohup /usr/bin/python3 kurulum.py --port "$PORT" >"$HOME/Library/Logs/suflor-kurulum.log" 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done
open "http://127.0.0.1:$PORT/"
y "Sihirbaz tarayıcıda açıldı. Bu pencereyi kapatabilirsin."
echo "Açılmadıysa tarayıcıda şu adrese git: http://127.0.0.1:$PORT/"
