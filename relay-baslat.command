#!/bin/bash
# v0.3.4: aktarıcı artık Mac açılışında kendiliğinden başlıyor (aktarici-kur.command). Bu dosya yalnız panoyu açar;
# aktarıcı yanıt vermiyorsa otomatik başlatmayı yeniden tetikler.
if ! curl -s -m 2 http://127.0.0.1:8765/status >/dev/null; then
  launchctl kickstart -k "gui/$(id -u)/local.suflor.aktarici" 2>/dev/null || "$(dirname "$0")/aktarici-kur.command"
  sleep 2
fi
open http://127.0.0.1:8765/
