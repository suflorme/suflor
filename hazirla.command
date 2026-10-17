#!/bin/bash
# Suflor.me — proje hazırlığını yeniden aç (panoda ⚙ Ayarlar → Proje → "Projeyi yeniden hazırla" bunu açar).
# Kurulum sihirbazı yalnız hazırlık ekranlarıyla açılır: tarama, süre, ilerleme, proje kartı. Asıl iş: python3 kurulum.py --adim hazirlik
cd "$(dirname "$0")" || exit 1
pkill -u "$(id -u)" -f "kurulum.py --port" >/dev/null 2>&1 || true  # yalnız bu kullanıcının eski sihirbazı
( PYTHONDONTWRITEBYTECODE=1 nohup /usr/bin/python3 kurulum.py --port 8770 --ac --adim hazirlik >"$HOME/Library/Logs/suflor-kurulum.log" 2>&1 & )
echo "Suflor.me: proje hazırlığı tarayıcıda açılıyor. Bu pencereyi kapatabilirsin."
