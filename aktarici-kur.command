#!/bin/bash
# Suflor.me — aktarıcıyı kurar / günceller (Mac açılışında kendiliğinden başlar). Çift tıkla. Kaldırmak için: --kaldir
# Asıl iş kurulum.py'de (tek kurulum komutu): python3 kurulum.py kur | kaldir
if [ "$1" = "--kaldir" ]; then exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" kaldir; fi
exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" kur
