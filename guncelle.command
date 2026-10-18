#!/bin/bash
# Suflor.me — güncelleme. Çift tıkla: son sürümü alır, aktarıcıyı yeniden kurar, /toplanti komutunu şablondan yeniler.
# Asıl iş: python3 kurulum.py guncelle (panodaki "Güncelle" düğmesi de bu dosyayı çalıştırır)
# Toplantı, sohbet ya da süren Konuş cevabı varken güncellemez; yine de güncellemek için: --zorla
exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" guncelle "$@"
