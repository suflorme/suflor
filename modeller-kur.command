#!/bin/bash
# Suflor.me — yerel modeller ve Python ortamı (~3,3 GB; olanı yeniden kurmaz). Çift tıkla. Asıl iş: python3 kurulum.py modeller
exec /usr/bin/python3 "$(dirname "$0")/kurulum.py" modeller
