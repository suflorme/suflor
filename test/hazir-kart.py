#!/usr/bin/env python3
# Hazır kart gönderimi (13 Kasım): `toplanti-claude.py hazir h1` kart() fonksiyonunun okuduğu bütün seçenekleri
# bulmalı. 9 Ekim (A.gizli) ve 13 Kasım (A.fisilti: "Namespace fisilti özelliği yok") aynı hata; artık kart alt
# komutunun varsayılanları kendiliğinden doluyor. Sahte aktarıcıya POST /card gider, gövde denetlenir.
import json, os, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GELEN = []

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        GELEN.append((self.path, self.headers.get("X-Suflor-Anahtar"), json.loads(self.rfile.read(n) or b"{}")))
        b = json.dumps({"ok": True, "card": {"id": "c1", "kind": GELEN[-1][2].get("kind"), "text": GELEN[-1][2].get("text")}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

sv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=sv.serve_forever, daemon=True).start()
hata = []
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "kart-anahtari.txt"), "w").write("deneme-anahtar")
    json.dump({"kartlar": [{"id": "h1", "tur": "soyle", "metin": "Takvimi sor", "neden": "gündem 2", "gundem": 1},
                           {"id": "h2", "tur": "not", "metin": "Bütçe notu"}]}, open(os.path.join(d, "hazir.json"), "w"))
    def kos(*arg):
        return subprocess.run([sys.executable, "-B", os.path.join(KOK, "toplanti-claude.py"), "--dir", d,
                               "--relay", f"http://127.0.0.1:{sv.server_port}", "hazir", *arg],
                              capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    r = kos("h1")
    if r.returncode != 0 or "kart gönderildi" not in r.stdout: hata.append(f"h1 gönderilemedi: {r.returncode} {r.stderr[-400:]}")
    elif GELEN[-1][0] != "/card" or GELEN[-1][1] != "deneme-anahtar": hata.append(f"yanlış uç/anahtar: {GELEN[-1][:2]}")
    else:
        b = GELEN[-1][2]
        if b.get("kind") != "soyle" or b.get("text") != "Takvimi sor" or b.get("agenda_i") != 1: hata.append(f"h1 gövdesi: {b}")
        if any(k in b for k in ("fisilti", "gizli", "onay", "durum", "sessiz_ozet")): hata.append(f"h1'de boş seçenek gövdeye girdi: {b}")
    r = kos("h2", "--cevap", "q7")
    if r.returncode != 0: hata.append(f"h2 --cevap: {r.returncode} {r.stderr[-400:]}")
    elif GELEN[-1][2].get("kind") != "cevap" or GELEN[-1][2].get("reply_to") != "q7": hata.append(f"h2 gövdesi: {GELEN[-1][2]}")
    r = kos("h9")
    if r.returncode == 0 or "h9 yok" not in r.stderr: hata.append(f"olmayan kart: {r.returncode} {r.stderr[-200:]}")
sv.shutdown()
print("hazır kart: " + ("✓ hepsi geçti" if not hata else "✗ " + " | ".join(hata)))
sys.exit(1 if hata else 0)
