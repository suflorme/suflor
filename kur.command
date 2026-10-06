#!/bin/bash
# Suflor.me — yeni bir macOS hesabında ilk kurulum (v0.9.2). Çift tıkla; birkaç soru sorar, sonra her şeyi kurar:
#   1) bilgisayar denetimi (Apple Silicon / M serisi, Python, disk)
#   2) hesabın ayar dosyası: ~/Library/Application Support/Suflor/ayar.json (alan adı, adın, port, proje klasörü)
#   3) proje (bağlam) klasörü: CLAUDE.md, .claude/commands/toplanti.md, belgeler/, gorusmeler/, _kanit/, _arsiv/
#   4) modeller ve Python ortamları: ortak klasörde (/Users/Shared/Suflor) varsa kullanılır, yoksa indirilir (~3,3 GB)
#   5) aktarıcı: Mac açılışında kendiliğinden başlar (aktarici-kur.command)
# Yeniden çalıştırmak güvenlidir: var olan ayar ve dosyaların üzerine yazmadan önce sorar.
set -e
KOD="$(cd "$(dirname "$0")" && pwd)"
AYAR_DIR="$HOME/Library/Application Support/Suflor"; AYAR="$AYAR_DIR/ayar.json"
echo "Suflor.me kurulumu — kod: $KOD"; echo

# 1) Denetim
[ "$(uname -m)" = "arm64" ] || { echo "Bu Mac Apple Silicon (M serisi) değil — Suflor.me'nin yerel konuşma tanıması yalnız M serisinde çalışır."; exit 1; }
if ! /usr/bin/python3 -c "import sys; assert sys.version_info >= (3, 9)" 2>/dev/null; then
  echo "Python 3 yok. Açılan pencerede 'Yükle' de (Xcode komut satırı araçları), bitince bu dosyayı yeniden çalıştır."; xcode-select --install || true; exit 1
fi
bos=$(df -g "$HOME" | awk 'NR==2{print $4}'); echo "✓ Apple Silicon · Python $(/usr/bin/python3 -c 'import platform;print(platform.python_version())') · disk boş ${bos} GB"

# 2) Ayar
sor() { local s; read -r -p "$1 [$2]: " s; echo "${s:-$2}"; }
bos_port() { for p in 8765 8766 8767 8768; do curl -s -m 1 "http://127.0.0.1:$p/status" >/dev/null || { echo $p; return; }; done; echo 8769; }
if [ -f "$AYAR" ]; then
  echo "Ayar dosyası zaten var:"; cat "$AYAR"; echo
  [ "$(sor "Yeniden sorayım mı? (e/h)" h)" = "e" ] || YENI=0
fi
if [ "${YENI:-1}" = "1" ]; then
  ALAN="$(sor "Çalışma alanının adı (panoda ve eklentide görünür)" "Kişisel")"
  AD="$(sor "Toplantılardaki adın (Teams'te göründüğü gibi)" "$(id -F 2>/dev/null || whoami)")"
  PORT="$(sor "Aktarıcı portu (bu Mac'teki diğer hesap 8765 kullanıyorsa farklı olmalı)" "$(bos_port)")"
  PROJE="$(sor "Proje (bağlam) klasörü — belgelerin ve toplantı özetlerin burada durur" "$HOME/Suflor-$(/usr/bin/python3 -c "import sys,unicodedata as u;t=sys.argv[1].replace('ı','i').replace('İ','I');print(''.join(c for c in u.normalize('NFKD',t) if c.isascii() and (c.isalnum() or c=='-')))" "$ALAN")")"
  mkdir -p "$AYAR_DIR"
  /usr/bin/python3 - "$AYAR" "$ALAN" "$AD" "$PORT" "$PROJE" "$KOD" <<'P'
import json, sys
yol, alan, ad, port, proje, kod = sys.argv[1:]
json.dump({"alan": alan, "ad": ad, "port": int(port), "uygulama": "~/Library/Application Support/Suflor", "proje": proje,
           "ortak": "/Users/Shared/Suflor", "kod": kod, "sozluk_kaynagi": None, "haric": [], "komut_sablondan": True, "durum_belgesi": "belgeler/DURUM.md", "claude_model": "sonnet"}, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
P
  echo "✓ ayar yazıldı: $AYAR"
fi
oku() { /usr/bin/python3 -c "import json,os,sys;print(os.path.expanduser(str(json.load(open(sys.argv[1]))[sys.argv[2]])))" "$AYAR" "$1"; }
ALAN="$(oku alan)"; AD="$(oku ad)"; PORT="$(oku port)"; PROJE="$(oku proje)"

# 3) Proje klasörü
mkdir -p "$PROJE"/{belgeler,gorusmeler,_kanit,_arsiv} "$PROJE/.claude/commands"
doldur() { /usr/bin/python3 - "$1" "$2" "$ALAN" "$AD" "$PORT" "$PROJE" "$KOD" <<'P'
import sys
kaynak, hedef, alan, ad, port, proje, kod = sys.argv[1:]
s = open(kaynak, encoding="utf-8").read()
for k, v in {"{{ALAN}}": alan, "{{AD}}": ad, "{{PORT}}": port, "{{PROJE}}": proje, "{{KOD}}": kod}.items(): s = s.replace(k, v)
open(hedef, "w", encoding="utf-8").write(s)
P
}
if [ -f "$PROJE/CLAUDE.md" ]; then echo "· $PROJE/CLAUDE.md var — dokunulmadı"; else doldur "$KOD/sablon/CLAUDE.md" "$PROJE/CLAUDE.md"; echo "✓ CLAUDE.md (alan kuralları şablonu) yazıldı — 'Ben kimim', 'Kişiler', 'Terimler'i doldur"; fi
doldur "$KOD/sablon/toplanti.md" "$PROJE/.claude/commands/toplanti.md"; echo "✓ /toplanti komutu: $PROJE/.claude/commands/toplanti.md"

# 4) Modeller (ortak klasör)
ORT=/Users/Shared/Suflor
if [ -x "$ORT/whisper-venv/bin/python" ] && [ -d "$ORT/whisper-modeller/hub" ] && [ -f "$ORT/ses-modeller/spkrec-ecapa-voxceleb/ecapa-mlx.npz" ]; then
  echo "✓ modeller ortak klasörde ($ORT) — indirme yok"
else
  echo "→ modeller kuruluyor (ortak klasöre, ~3,3 GB; internet gerekir)"; "$KOD/modeller-kur.command"
fi

# Claude Code komut satırı (panodan başlatma ve /toplanti için)
if command -v claude >/dev/null || [ -x "$HOME/.local/bin/claude" ]; then echo "✓ Claude Code komut satırı var"
else echo "⚠ Claude Code komut satırı yok — kurulum: Terminal'de  curl -fsSL https://claude.ai/install.sh | bash  sonra  claude  ile giriş yap (rehber §1)"; fi

# 5) Aktarıcı
"$KOD/aktarici-kur.command"
echo
echo "Kurulum bitti — çalışma alanı: $ALAN · port $PORT · proje: $PROJE"
echo "Sıradaki adımlar (ayrıntı: $KOD/KURULUM-kisisel-hesap.md):"
echo "  1. Chrome → chrome://extensions → Geliştirici modu → 'Paketlenmemiş öğe yükle' → $KOD"
echo "  2. Suflor.me simgesine tıkla → çalışma alanı olarak '$ALAN' seç"
echo "  3. $PROJE/CLAUDE.md'yi doldur, belgelerini belgeler/ altına koy"
echo "  4. Claude Code'u bu klasörde aç ($PROJE), toplantıdan önce: /toplanti <kişi — konu>"
