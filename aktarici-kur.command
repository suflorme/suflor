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
  if swiftc -O -o "$TAK/Contents/MacOS/SuflorTakvim" "$SRC/takvim.swift" 2>/tmp/suflor-takvim-derleme.log; then
    codesign -s - --force "$TAK" >/dev/null 2>&1 || true; echo "Takvim yardımcısı derlendi: $TAK"
  else echo "UYARI: takvim yardımcısı derlenemedi (/tmp/suflor-takvim-derleme.log) — takvim özelliği kapalı kalır"; fi
fi

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
