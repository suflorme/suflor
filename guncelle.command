#!/bin/bash
# Suflor.me — güncelleme (v0.11.2). Çift tıkla: son sürümü alır, aktarıcıyı yeniden kurar, /toplanti komutunu
# şablondan yeniler (eskisi .eski olarak kalır). Sonra Chrome'da eklentiyi yenilemen yeterli.
# İki kurulum biçimi: git klonu (.git var → git pull) ya da tek satır kurulum (kur.sh; .git yok → açık depodan tar).
# Gövde main() içinde: tar yolu bu dosyanın kendisini de yeniler, bash dosyayı okumayı bitirmeden değişmesin.
set -e
DEPO="suflorme/suflor"
KOD="$(cd "$(dirname "$0")" && pwd)"; AYAR="$HOME/Library/Application Support/Suflor/ayar.json"

surum() { /usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$1/manifest.json" 2>/dev/null || echo "?"; }

git_ile() {
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "Kod klasöründe kaydedilmemiş değişiklik var — güncelleme yapılmadı:"; git status --short; exit 1; fi
  once=$(git rev-parse --short HEAD); git pull --ff-only -q; sonra=$(git rev-parse --short HEAD)
  [ "$once" = "$sonra" ] && echo "✓ zaten güncel ($sonra)" || { echo "✓ güncellendi: $once → $sonra"; git log --oneline "$once..$sonra" | head -10; }
}

tar_ile() {
  once=$(surum "$KOD"); GECICI="$(mktemp -d)"; trap 'rm -rf "$GECICI"' EXIT
  echo "→ son sürüm indiriliyor (github.com/$DEPO)"
  if ! curl -fsSL "https://codeload.github.com/$DEPO/tar.gz/refs/heads/main" | tar -xz -C "$GECICI" --strip-components 1; then
    echo "İndirilemedi — internet bağlantısını denetle, sonra yeniden çift tıkla. Hiçbir dosya değişmedi."; exit 1
  fi
  [ -f "$GECICI/manifest.json" ] && [ -f "$GECICI/relay.py" ] || { echo "İndirilen paket eksik — güncelleme yapılmadı."; exit 1; }
  sonra=$(surum "$GECICI")
  if [ "$once" = "$sonra" ]; then echo "✓ zaten güncel (v$sonra) — yine de aktarıcı ve komut yenileniyor"; fi
  # kur.sh ile aynı: kod dosyaları güncellenir, kullanıcının bu klasöre koyduğu başka bir şey silinmez
  (cd "$GECICI" && tar -cf - .) | (cd "$KOD" && tar -xf -)
  chmod +x "$KOD"/*.command "$KOD"/*.sh 2>/dev/null || true
  xattr -dr com.apple.quarantine "$KOD" 2>/dev/null || true
  [ "$once" != "$sonra" ] && echo "✓ güncellendi: v$once → v$sonra"
  return 0
}

main() {
  cd "$KOD"
  if [ -d "$KOD/.git" ]; then git_ile; else tar_ile; fi
  if ! "$KOD/aktarici-kur.command"; then
    echo; echo "UYARI: aktarıcı kurulamadı — kod güncellendi ama çalışan aktarıcı eski sürümde kalmış olabilir."
    echo "Bu pencerenin yukarısındaki hatayı geliştiriciye ilet ya da $KOD/aktarici-kur.command dosyasına çift tıkla."; exit 1
  fi
  # v0.13.7 (5 Ekim): kişisel hesapta kod v0.13.6 iken çalışan aktarıcı v0.13.2'de kalmıştı — sürümler karşılaştırılır
  PORT_="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("port", 8765))' "$AYAR" 2>/dev/null || echo 8765)"
  CALISAN="$(curl -s -m 3 "http://127.0.0.1:$PORT_/status" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin).get("surum", "?"))' 2>/dev/null || echo "?")"
  if [ "$CALISAN" != "$(surum "$KOD")" ]; then
    echo "UYARI: çalışan aktarıcı v$CALISAN, kod v$(surum "$KOD"). $KOD/aktarici-kur.command dosyasına çift tıkla; düzelmezse Mac'i yeniden başlat."
  else echo "✓ aktarıcı v$CALISAN çalışıyor"; fi
  if [ -f "$AYAR" ]; then
    /usr/bin/python3 - "$AYAR" "$KOD" <<'P'
import json, os, shutil, sys
a = json.load(open(sys.argv[1], encoding="utf-8")); kod = sys.argv[2]
proje = os.path.expanduser(a["proje"]); hedef = os.path.join(proje, ".claude", "commands", "toplanti.md")
s = open(os.path.join(kod, "sablon", "toplanti.md"), encoding="utf-8").read()
for k, v in {"{{ALAN}}": a["alan"], "{{AD}}": a["ad"], "{{PORT}}": str(a["port"]), "{{PROJE}}": proje, "{{KOD}}": kod}.items(): s = s.replace(k, v)
if a.get("komut_sablondan") and os.path.isdir(os.path.dirname(hedef)):  # kendi komutunu yazan alan (komut_sablondan yok): dokunma
    if os.path.exists(hedef) and open(hedef, encoding="utf-8").read() != s: shutil.copy(hedef, hedef + ".eski")
    open(hedef, "w", encoding="utf-8").write(s); print("✓ /toplanti komutu şablondan yenilendi")
P
  fi
  echo "Şimdi: Chrome → chrome://extensions → Suflor.me → yenile (⟳), sonra toplantı sekmesini yenile."
}

main "$@"; exit
