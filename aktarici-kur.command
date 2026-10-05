#!/bin/bash
# Suflor.me aktarıcısını Mac açılışında kendiliğinden başlayacak şekilde kurar / günceller (v0.3.4).
# macOS, arka planda (launchd) başlayan programların Masaüstü'ne erişimini engellediği için aktarıcı ve veri
# klasörü ~/Library/Application Support/Suflor altında durur (ayar: uygulama); proje klasöründeki _canli oraya bir kısayoldur.
# Her relay.py değişikliğinden sonra bu dosyayı yeniden çalıştır (çift tıkla). Kaldırmak için: --kaldir
set -e
# v0.9.2: yollar ve port hesabın ayar dosyasından (~/Library/Application Support/Suflor/ayar.json; yoksa varsayılanlar)
ayar() { /usr/bin/python3 -c "import json,os,sys
v={'port':8765,'uygulama':'~/Library/Application Support/Suflor','proje':'~/Suflor','ortak':'/Users/Shared/Suflor'}
try: v.update(json.load(open(os.path.expanduser('~/Library/Application Support/Suflor/ayar.json'))))
except Exception: pass
print(os.path.expanduser(str(v[sys.argv[1]])))" "$1"; }
APP="$(ayar uygulama)"; PORT="$(ayar port)"
DESK="$(ayar proje)/_canli"
PL="$HOME/Library/LaunchAgents/local.suflor.aktarici.plist"
LABEL="local.suflor.aktarici"
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "--kaldir" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true; rm -f "$PL"
  echo "Otomatik başlatma kaldırıldı. Veri $APP/canli içinde duruyor (Masaüstündeki _canli kısayolu çalışmaya devam eder)."
  exit 0
fi

# Bozuk relay.py kurulursa KeepAlive çöken aktarıcıyı döngüde kaldırmaya çalışır: önce sözdizimini denetle (v0.4.0)
if ! PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" "$SRC/relay.py"; then
  echo "HATA: relay.py sözdizimi hatalı — kurulum yapılmadı, çalışan aktarıcı olduğu gibi bırakıldı."; exit 1
fi
mkdir -p "$APP"
# v0.9.9: geri bildirim raporları için ortak klasör — iki macOS hesabı da yazar (herkes yazar, yapışkan bit: yalnız sahibi siler)
GB="$(ayar ortak 2>/dev/null || echo /Users/Shared/Suflor)/geri-bildirim"
[ -d "$GB" ] || mkdir -p "$GB" 2>/dev/null || true; chmod 1777 "$GB" 2>/dev/null || true
# Veri klasörü: Masaüstünde gerçek klasör varsa bir kez taşı, yerine kısayol bırak
if [ -d "$DESK" ] && [ ! -L "$DESK" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  pkill -u "$(id -u)" -f "relay.py --dir" 2>/dev/null || true; sleep 1
  [ -e "$APP/canli" ] && { echo "HATA: $APP/canli zaten var, taşıma yapılmadı."; exit 1; }
  mv "$DESK" "$APP/canli" && ln -s "$APP/canli" "$DESK"
  echo "Veri taşındı: $APP/canli  (Masaüstünde kısayol: $DESK)"
fi
mkdir -p "$APP/canli"
# v0.9.2: yeni hesapta proje klasöründe _canli kısayolu yoksa kur (Claude geçmiş toplantıları oradan arar)
if [ ! -e "$DESK" ] && [ -d "$(dirname "$DESK")" ]; then ln -s "$APP/canli" "$DESK" && echo "Kısayol: $DESK → $APP/canli"; fi
cp "$SRC/relay.py" "$APP/relay.py"
cp "$SRC/ses-isci.py" "$APP/ses-isci.py"  # v0.8.4: duygu modeli + konuşmacı ayırma (ses-venv, ses-modeller ayrıca kurulu olmalı)
cp "$SRC/whisper-isci.py" "$APP/whisper-isci.py"  # v0.8.0: yerel konuşma tanıma işçisi (whisper-venv ayrıca kurulu olmalı)
# v0.11.3: pano ve hazırlık sayfası marka yazı tiplerini ve işareti aktarıcının yanından verir (launchd Masaüstü'nü okuyamaz)
# v0.12.0: beta teşhis süzgeci + sözlüğü (kodun kendi günlük metinlerinden üretilir)
cp "$SRC/teshis.py" "$APP/teshis.py"; PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SRC/teshis.py" --sozluk "$SRC" > "$APP/teshis-sozluk.txt" 2>/dev/null || true
mkdir -p "$APP/marka/yazi"; cp "$SRC"/marka/*.svg "$APP/marka/" 2>/dev/null || true; cp "$SRC"/marka/yazi/*.woff2 "$APP/marka/yazi/" 2>/dev/null || true
# v0.9.3: takvim yardımcısı (Mac Takvim → takvim.json). Kaynak değiştiyse derlenir; takvim izni uygulamaya verilir (ilk açılışta sorulur).
TAK="$APP/Suflor Takvim.app"
if command -v swiftc >/dev/null && { [ ! -x "$TAK/Contents/MacOS/SuflorTakvim" ] || [ "$SRC/takvim.swift" -nt "$TAK/Contents/MacOS/SuflorTakvim" ]; }; then
  mkdir -p "$TAK/Contents/MacOS"
  cat > "$TAK/Contents/Info.plist" <<'PL'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>local.suflor.takvim</string><key>CFBundleName</key><string>Suflor Takvim</string>
  <key>CFBundleExecutable</key><string>SuflorTakvim</string><key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string><key>LSUIElement</key><true/>
  <key>NSCalendarsFullAccessUsageDescription</key><string>Suflor.me bugünkü toplantılarını bulmak, gündemini ve katılımcılarını toplantı asistanına vermek için takvimini okur. Hiçbir şey değiştirmez, bu Mac dışına göndermez.</string>
  <key>NSCalendarsUsageDescription</key><string>Suflor.me bugünkü toplantılarını bulmak için takvimini okur. Hiçbir şey değiştirmez.</string>
</dict></plist>
PL
  # v0.12.3 (güvenlik denetimi D3): derleme günlüğü sabit /tmp yolunda değil, kullanıcının geçici klasöründe benzersiz dosyada
  DLOG="$(mktemp "${TMPDIR:-/tmp}/suflor-takvim-derleme.XXXXXX")" || DLOG=/dev/null
  if swiftc -O -o "$TAK/Contents/MacOS/SuflorTakvim" "$SRC/takvim.swift" 2>"$DLOG"; then
    echo "Takvim yardımcısı derlendi: $TAK"; [ "$DLOG" = /dev/null ] || rm -f "$DLOG"
  else echo "UYARI: takvim yardımcısı derlenemedi ($DLOG) — takvim özelliği kapalı kalır"; fi
fi
# v0.13.0: yerel ses yardımcısı (ses-yardimcisi.swift → "Suflor Ses.app"): toplantı uygulamasının sesini (karşı taraf) Core Audio
# process tap ile alır, aktarıcıya verir — Option + Shift + W gerekmez. macOS 14.4+; izin "Sistem Sesi Kaydı" (yalnız sistem sesi) uygulamaya verilir.
SES="$APP/Suflor Ses.app"; SES_YENI=0
# v0.13.8: izin penceresi yalnız ilk kurulumda — güncellemede yeniden derlenen yardımcı aynı yerel imzayla imzalanır, izin korunur
[ -x "$SES/Contents/MacOS/SuflorSes" ] && SES_ILK=0 || SES_ILK=1
if command -v swiftc >/dev/null && sw_vers -productVersion | awk -F. '{exit !($1 > 14 || ($1 == 14 && $2 >= 4))}' && \
   { [ ! -x "$SES/Contents/MacOS/SuflorSes" ] || [ "$SRC/ses-yardimcisi.swift" -nt "$SES/Contents/MacOS/SuflorSes" ]; }; then
  mkdir -p "$SES/Contents/MacOS"
  cat > "$SES/Contents/Info.plist" <<'PL'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>local.suflor.ses</string><key>CFBundleName</key><string>Suflor Ses</string>
  <key>CFBundleExecutable</key><string>SuflorSes</string><key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.13.0</string><key>LSUIElement</key><true/><key>LSMinimumSystemVersion</key><string>14.4</string>
  <key>NSAudioCaptureUsageDescription</key><string>Suflor.me toplantıdaki karşı tarafın sesini yazıya dökmek için toplantı uygulamasının sesini alır. Ses kaydedilmez, bu Mac dışına gönderilmez.</string>
</dict></plist>
PL
  DLOG="$(mktemp "${TMPDIR:-/tmp}/suflor-ses-derleme.XXXXXX")" || DLOG=/dev/null
  if swiftc -O -o "$SES/Contents/MacOS/SuflorSes" "$SRC/ses-yardimcisi.swift" 2>"$DLOG"; then
    echo "Ses yardımcısı derlendi: $SES"; SES_YENI=1; [ "$DLOG" = /dev/null ] || rm -f "$DLOG"
    pkill -u "$(id -u)" -x SuflorSes 2>/dev/null || true  # eski kopya kapanır, aktarıcı yenisini açar
  else echo "UYARI: ses yardımcısı derlenemedi ($DLOG) — karşı ses için Option + Shift + W ile devam"; fi
fi
# v0.12.4: kalıcı yerel imza (yerel-imza.sh) — geçici imza her derlemede değişip izni (takvim, ses kaydı) düşürüyordu. Uygulama başka
# imzayla imzalıysa (eski kurulum ya da yeni derleme) yeniden imzalanır; kimlik bir kez değişir, sonra hep aynı kalır.
for U in "$TAK" "$SES"; do
  [ -d "$U/Contents/MacOS" ] || continue
  . "$SRC/yerel-imza.sh"; IMZA="$(yerel_imza)"
  if [ "$IMZA" = "-" ] || ! codesign -dv --verbose=2 "$U" 2>&1 | grep -q "^Authority=$IMZA\$"; then
    if codesign -s "$IMZA" --force "$U" >/dev/null 2>&1; then
      [ "$IMZA" = "-" ] && echo "UYARI: yerel imza kurulamadı — geçici imza; izin her derlemede yeniden istenebilir ($(basename "$U"))" \
        || echo "$(basename "$U") yerel imzayla imzalandı (izin aynı imzada korunur; ilk kez imzalandıysa macOS bir kez sorar)"
    fi
  fi
done
cat > "$PL" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>$APP/relay.py</string><string>--dir</string><string>$APP/canli</string><string>--port</string><string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$APP</string>
  <key>EnvironmentVariables</key><dict>
    <key>PYTHONDONTWRITEBYTECODE</key><string>1</string><key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/suflor-aktarici.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/suflor-aktarici.log</string>
</dict></plist>
EOF

# Elle başlatılmış bir aktarıcı portu tutuyorsa kapat, ajanı yeniden yükle
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
pkill -u "$(id -u)" -f "relay.py --dir" 2>/dev/null || true; sleep 1  # v0.9.2: yalnız bu hesabın aktarıcısı (diğer hesabınki çalışmaya devam eder)
launchctl bootstrap "gui/$(id -u)" "$PL"; sleep 2
if curl -s -m 3 "http://127.0.0.1:$PORT/status" >/dev/null; then
  echo "Aktarıcı çalışıyor → http://127.0.0.1:$PORT/  (Mac açılışında kendiliğinden başlar, çökerse yeniden kalkar)"
else
  echo "UYARI: aktarıcı yanıt vermiyor. Günlük: ~/Library/Logs/suflor-aktarici.log"; tail -5 "$HOME/Library/Logs/suflor-aktarici.log"; exit 1
fi
# v0.13.0: ilk kurulumda izin penceresi şimdi çıksın, toplantının ortasında değil. v0.13.8: aktarıcı yeniden başlatıldıktan SONRA —
# önceden izin beklenirken pencere kapatılırsa aktarıcı eski sürümde kalıyordu (5 Ekim kişisel hesap)
if [ "$SES_YENI" = 1 ] && [ "$SES_ILK" = 1 ] && [ -x "$SES/Contents/MacOS/SuflorSes" ]; then
  echo "Sistem sesi kaydı izni: macOS 'Suflor Ses' için izin sorarsa İzin Ver de (Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı). En çok 2 dk beklenir; aktarıcı zaten çalışıyor."
  # v0.13.5: en çok 2 dk bekle — izin penceresi yanıtlanmazsa kurulum (sihirbazın "Kuruyorum" adımı) takılıp kalmasın
  open -g -W -a "$SES" --args --izin 2>/dev/null & IZ=$!
  for _ in $(seq 1 120); do kill -0 "$IZ" 2>/dev/null || break; sleep 1; done
  kill "$IZ" 2>/dev/null || true; wait "$IZ" 2>/dev/null || true
fi

