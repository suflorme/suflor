#!/bin/bash
# Suflor.me — aktarıcıyı kurar / günceller (Mac açılışında kendiliğinden başlar). Çift tıkla. Kaldırmak için: --kaldir
# Asıl iş kurulum.py'de (tek kurulum komutu): python3 kurulum.py kur | kaldir
# Toplantı, sohbet ya da süren Konuş cevabı varken kurmaz (aktarıcı yeniden başlar, konuşma bölünür); yine de kurmak için: --zorla
if [ "$1" = "--kaldir" ]; then exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" kaldir; fi
# Geliştirme klasöründe (oturum.py kur) kaydedilmemiş kod ya da başka oturumun yayın kilidi varken kurmaz — --zorla bunu da atlamaz (S104)
if [ -f "$(dirname "$0")/oturum.py" ]; then
  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B "$(dirname "$0")/oturum.py" --kurulum || exit 1
fi
if [ "$1" != "--zorla" ]; then
  m=$(PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$(dirname "$0")/kurulum.py" mesgul) || { echo "Kurulmadı: $m. Bitince yeniden çalıştır (beklemeden kurmak için: --zorla)."; exit 1; }
fi
exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" kur
