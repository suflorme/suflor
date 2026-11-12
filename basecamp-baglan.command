#!/bin/bash
# Suflor.me — Basecamp okuma bağlayıcısını bağlar (Launchpad OAuth; belirteçler Anahtar Zinciri'ne). Çift tıkla. Yalnız bağlantı doğrulaması için: --deneme
# Asıl iş basecamp-baglan.py'de. Önce KILAVUZ.md'deki "Basecamp'i bağla" adımlarıyla Launchpad'de uygulamayı kaydet.
/usr/bin/python3 "$(dirname "$0")/basecamp-baglan.py" "$@"
s=$?; echo; read -n 1 -s -r -p "Kapatmak için bir tuşa bas."; exit $s
