#!/usr/bin/env python3
# basecamp-baglan.py: sahte Launchpad sunucusuyla kod değişimi, hesap seçimi, Anahtar Zinciri yazımı (deneme servis adı; test sonunda silinir — gerçek suflor-basecamp'e dokunulmaz),
# ayar.json'a yalnız hesap, --deneme akışı, hata iletileri. Gerçek ağ yok.   PYTHONDONTWRITEBYTECODE=1 python3 test/basecamp-baglan.py   (kaldı → çıkış 1)
import os, sys, json, time, threading, tempfile, importlib.util, urllib.request, urllib.parse, io, contextlib
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
GORULEN = []; MOD = {"hesaplar": 1, "token_hata": False}
class LP(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, g, kod=200): b = json.dumps(g).encode(); self.send_response(kod); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); GORULEN.append(("POST", u.path, {k: v[0] for k, v in q.items()}, self.headers.get("User-Agent")))
        if u.path == "/authorization/token":
            if MOD["token_hata"] or q.get("code") != ["KOD1"] or q.get("client_secret") != ["SIR"]: return self._j({"error": "x"}, 400)
            return self._j({"access_token": "AT1", "refresh_token": "RT1", "expires_in": 1209600})
        self._j({}, 404)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); GORULEN.append(("GET", u.path, {}, self.headers.get("User-Agent")))
        if self.headers.get("Authorization") != "Bearer AT1": return self._j({}, 401)
        P = self.server.server_port
        if u.path == "/authorization.json":
            h = [{"product": "bc3", "id": 111, "name": "Birinci Firma", "href": f"http://127.0.0.1:{P}/111"}, {"product": "bcx", "id": 5, "name": "Eski", "href": "x"}]
            if MOD["hesaplar"] > 1: h.append({"product": "bc3", "id": 222, "name": "Ikinci Firma", "href": f"http://127.0.0.1:{P}/222"})
            return self._j({"accounts": h})
        if u.path.endswith("/projects.json"): return self._j([{"id": 1}, {"id": 2}, {"id": 3}])
        self._j({}, 404)
sv = HTTPServer(("127.0.0.1", 0), LP); threading.Thread(target=sv.serve_forever, daemon=True).start()
EV = tempfile.mkdtemp(); SERVIS = f"suflor-basecamp-deneme-{os.getpid()}"
os.environ.update(SUFLOR_EV=EV, SUFLOR_BC_LAUNCHPAD=f"http://127.0.0.1:{sv.server_port}", SUFLOR_BC_SERVIS=SERVIS)
sp = importlib.util.spec_from_file_location("bcb", os.path.join(KOD, "basecamp-baglan.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)
AYAR = os.path.join(EV, "Library", "Application Support", "Suflor", "ayar.json")
os.makedirs(os.path.dirname(AYAR)); json.dump({"x": 1, "basecamp": {"proje_esleme": {"a": "B"}}}, open(AYAR, "w"))
PORT = 18770; YETKI = []
def tarayici(kod="KOD1"):
    def f(url):
        YETKI.append(url); q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        def git(): time.sleep(0.3); urllib.request.urlopen(f"{q['redirect_uri'][0]}?code={kod}&state={q['state'][0]}", timeout=5).read()
        threading.Thread(target=git, daemon=True).start()
    return f
try:
    h, n = B.baglan("CID", "SIR", PORT, ac=tarayici(), zaman=10)
    ok("yetki adresi: type=web_server + client_id + redirect_uri(8770 yolu biçimi)", "type=web_server" in YETKI[0] and "client_id=CID" in YETKI[0] and urllib.parse.quote(f"http://127.0.0.1:{PORT}/basecamp/geri", safe="") in YETKI[0])
    ok("kod değişimi doğru parametrelerle (secret adreste, çıktıda değil)", any(g[1] == "/authorization/token" and g[2].get("client_id") == "CID" and g[2].get("code") == "KOD1" for g in GORULEN))
    ok("tek bc3 hesabı seçildi, proje sayısı 3", h["id"] == 111 and n == 3)
    ok("tüm isteklerde User-Agent, kişisel bilgi yok", all(g[3] == "Suflor.me (https://github.com/suflorme/suflor)" for g in GORULEN))
    ok("Anahtar Zinciri: erişim belirteci", B.kc_oku(SERVIS) == "AT1")
    o = json.loads(__import__("base64").b64decode(B.kc_oku(SERVIS + "-oauth")).decode()); ok("Anahtar Zinciri: refresh_token, client_id, client_secret, bitiş", o.get("refresh_token") == "RT1" and o.get("client_id") == "CID" and o.get("client_secret") == "SIR" and o.get("bitis", 0) > time.time() + 1000000)
    a = json.load(open(AYAR)); ok("ayar.json: yalnız hesap eklendi, eski ayar korundu, anahtar/belirteç yok", a["basecamp"] == {"proje_esleme": {"a": "B"}, "hesap": "111"} and a["x"] == 1 and "AT1" not in json.dumps(a) and "SIR" not in json.dumps(a))
    # birden çok hesap: numara sorulur
    MOD["hesaplar"] = 2; girdi = []
    with contextlib.redirect_stdout(io.StringIO()) as c: h, n = B.baglan("CID", "SIR", PORT, ac=tarayici(), sor=lambda m: (girdi.append(m), "2")[1], zaman=10)
    ok("birden çok hesap: adlarıyla listelendi, numara soruldu", h["id"] == 222 and "Birinci Firma" in c.getvalue() and "Ikinci Firma" in c.getvalue() and girdi and json.load(open(AYAR))["basecamp"]["hesap"] == "222")
    # --deneme
    h, n = B.deneme(); ok("--deneme: mevcut anahtarla hesap + proje sayısı", h["id"] == 111 and n == 3)
    # hatalar
    MOD["token_hata"] = True
    try: B.baglan("CID", "SIR", PORT, ac=tarayici(), zaman=10); ok("yanlış secret → Türkçe hata", False)
    except B.Hata as e: ok("yanlış secret → Türkçe hata", "reddedildi" in str(e))
    MOD["token_hata"] = False
    try: B.baglan("CID", "SIR", PORT, ac=lambda u: None, zaman=2); ok("izin gelmezse zaman aşımı hatası", False)
    except B.Hata as e: ok("izin gelmezse zaman aşımı hatası", "izni alınamadı" in str(e))
    try: B.kc_yaz(SERVIS, "a", 'bozuk"deger'); ok("tırnaklı değer reddedilir", False)
    except B.Hata: ok("tırnaklı değer reddedilir", True)
finally:
    B.kc_sil(SERVIS); B.kc_sil(SERVIS + "-oauth"); sv.shutdown()
ok("test servisi silindi", B.kc_oku(SERVIS) == "" and B.kc_oku(SERVIS + "-oauth") == "")
print(f"\n{'TAMAM' if not HATA else 'KALDI: ' + ', '.join(HATA)}"); sys.exit(1 if HATA else 0)
