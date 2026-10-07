#!/bin/bash
# Suflor.me — güncelleme. Çift tıkla: son sürümü alır, aktarıcıyı yeniden kurar, /toplanti komutunu şablondan yeniler.
# Asıl iş: python3 kurulum.py guncelle (panodaki "Güncelle" düğmesi de bu dosyayı çalıştırır)
exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" guncelle
