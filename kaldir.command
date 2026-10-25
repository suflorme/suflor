#!/bin/bash
# Suflor.me — bu hesaptan tamamen kaldırır (aktarıcı, Mac uygulaması, ayarlar, dökümler; isterse modeller, proje ve kod klasörü). Çift tıkla.
# Silmez, Çöp Sepeti'ne taşır: Çöp boşaltılana dek geri alınabilir. Asıl iş: python3 kurulum.py sil
/usr/bin/python3 "$(dirname "$0")/kurulum.py" sil "$@"
echo; read -n 1 -s -r -p "Kapatmak için bir tuşa bas."; echo
