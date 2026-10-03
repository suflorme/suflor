#!/bin/bash
# Suflor.me — güncelleme (v0.9.2). Çift tıkla: GitHub'dan son sürümü alır, aktarıcıyı yeniden kurar, /toplanti komutunu
# şablondan yeniler (eskisi .eski olarak kalır). Sonra Chrome'da eklentiyi yenilemen yeterli.
set -e
KOD="$(cd "$(dirname "$0")" && pwd)"; AYAR="$HOME/Library/Application Support/Suflor/ayar.json"
cd "$KOD"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "Kod klasöründe kaydedilmemiş değişiklik var — güncelleme yapılmadı:"; git status --short; exit 1; fi
once=$(git rev-parse --short HEAD); git pull --ff-only -q; sonra=$(git rev-parse --short HEAD)
[ "$once" = "$sonra" ] && echo "✓ zaten güncel ($sonra)" || { echo "✓ güncellendi: $once → $sonra"; git log --oneline "$once..$sonra" | head -10; }
"$KOD/aktarici-kur.command"
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
