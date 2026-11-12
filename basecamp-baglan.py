#!/usr/bin/env python3
# Suflor.me — Basecamp OKUMA bağlayıcısını bağlar (OAuth, 37signals Launchpad). Çift tıkla: basecamp-baglan.command.
#   python3 basecamp-baglan.py            Client ID ve Secret sorar, tarayıcıda izin verirsin, belirteçler Anahtar Zinciri'ne yazılır
#   python3 basecamp-baglan.py --deneme   yalnız mevcut anahtarla hesabı ve proje sayısını gösterir (yazmaz)
# Gizlilik: Client ID/Secret ve belirteçler yalnız Anahtar Zinciri'ne gider; ayar.json'a ve günlüğe yazılmaz. ayar.json'a yalnız hesap numarası girer.
# Anahtar Zinciri yazımı: `security add-generic-password -w <değer>` değeri komut satırına koyar ve `ps`te görünür. Bunun yerine `security -i`
# (etkileşimli kip) komutu stdin'den okur; değer hiçbir süreç argümanında geçmez. Tırnak ya da ters bölü içeren değer reddedilir (Basecamp belirteçleri içermez).
# Öğeler: <servis> (hesap "access_token") = Bearer belirteci (aktarici/basecamp-oku.py okur); <servis>-oauth (hesap "oauth") = JSON (base64) {refresh_token, client_id,
# client_secret, redirect_uri, bitis}. Servis adı varsayılan suflor-basecamp; deneme için SUFLOR_BC_SERVIS.
# Deneme/test ortam değişkenleri: SUFLOR_BC_LAUNCHPAD (Launchpad adresi), SUFLOR_EV (ayar klasörü; kurulum.py ile aynı).
import base64, getpass, importlib.util, json, os, secrets, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.abspath(__file__))
LP = os.environ.get("SUFLOR_BC_LAUNCHPAD") or "https://launchpad.37signals.com"
UA = "Suflor.me (https://github.com/suflorme/suflor)"
PORT = 8770; YOL = "/basecamp/geri"
def servis(): return os.environ.get("SUFLOR_BC_SERVIS") or "suflor-basecamp"
def redirect(port=PORT): return f"http://127.0.0.1:{port}{YOL}"
class Hata(Exception): pass

def http(url, yontem="GET", bearer=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if bearer: h["Authorization"] = "Bearer " + bearer
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=b"" if yontem == "POST" else None, method=yontem, headers=h), timeout=20) as f:
            return json.loads(f.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e: raise Hata(f"Basecamp isteği reddedildi (HTTP {e.code}). Client ID/Secret ve yönlendirme adresi doğru mu?")
    except Exception: raise Hata("Basecamp'e ulaşılamadı. İnternet bağlantını denetle.")

def kc_yaz(sv, hesap, deger):
    if any(c in deger + sv + hesap for c in '"\\\n\r'): raise Hata("Anahtar Zinciri'ne yazılamayan karakter var.")
    r = subprocess.run(["/usr/bin/security", "-i"], input=f'add-generic-password -U -s "{sv}" -a "{hesap}" -w "{deger}"\n', capture_output=True, text=True, timeout=20)
    if r.returncode != 0: raise Hata("Anahtar Zinciri'ne yazılamadı.")
def b64(d): return base64.b64encode(json.dumps(d).encode()).decode()  # JSON tırnak içerir; security -i komutunu bozmasın diye base64
def kc_oku(sv):
    r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", sv, "-w"], capture_output=True, text=True, timeout=15)
    return r.stdout.strip() if r.returncode == 0 else ""
def kc_sil(sv):  # yalnız testler kullanır
    subprocess.run(["/usr/bin/security", "delete-generic-password", "-s", sv], capture_output=True, timeout=15)

def kod_bekle(port, state, ac, zaman=300):  # tek seferlik yerel sunucu: tarayıcı yönlendirmesinden kodu alır
    sonuc = {}
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path != YOL: self.send_response(404); self.end_headers(); return
            q = urllib.parse.parse_qs(u.query)
            if q.get("code") and (not q.get("state") or q["state"][0] == state): sonuc["kod"] = q["code"][0]; m = "Bağlandı. Bu sekmeyi kapatıp Terminal'e dönebilirsin."
            else: sonuc["hata"] = (q.get("error") or ["izin verilmedi"])[0]; m = "İzin alınamadı. Terminal'e dön."
            b = f"<!doctype html><meta charset=utf-8><body style='font:16px -apple-system;padding:3em'>{m}".encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
    try: sv = HTTPServer(("127.0.0.1", port), H)
    except OSError: raise Hata(f"{port} numaralı kapı kullanımda (kurulum sihirbazı açık olabilir). Kapatıp yeniden dene.")
    sv.timeout = 1
    try:
        ac(); son = time.time() + zaman
        while not sonuc and time.time() < son: sv.handle_request()
    finally: sv.server_close()
    if "kod" not in sonuc: raise Hata("Basecamp izni alınamadı (" + sonuc.get("hata", "süre doldu") + ").")
    return sonuc["kod"]

def hesap_sec(hesaplar, sor):
    if not hesaplar: raise Hata("Bu Basecamp girişinde Basecamp 3/4 hesabı bulunamadı.")
    if len(hesaplar) == 1: return hesaplar[0]
    for i, h in enumerate(hesaplar, 1): print(f"  {i}) {h.get('name')}")
    try: return hesaplar[int(sor("Hangi hesap? Numara: ")) - 1]
    except Exception: raise Hata("Geçersiz numara.")

def ayar_yaz(hesap):  # ayar.json'a yalnız hesap; aktarıcının kullandığı kilitli yazma (kurulum.ayar_degistir)
    sp = importlib.util.spec_from_file_location("suflor_kurulum", os.path.join(KOD, "kurulum.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    def fn(a):
        b = a.get("basecamp") if isinstance(a.get("basecamp"), dict) else {}; b["hesap"] = str(hesap); a["basecamp"] = b
    m.ayar_degistir(fn)

def proje_say(href, belirtec):
    n, url = 0, href.rstrip("/") + "/projects.json"
    try:
        for _ in range(10):
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Authorization": "Bearer " + belirtec, "Accept": "application/json"}), timeout=20) as f:
                n += len(json.loads(f.read().decode("utf-8", "replace"))); ln = f.headers.get("Link") or ""
            import re; m = re.search(r'<([^>]+)>;\s*rel="next"', ln)
            if not m: break
            url = m.group(1)
    except Exception: raise Hata("Projeler okunamadı (belirteç geçersiz olabilir).")
    return n

def baglan(cid, csecret, port=PORT, ac=None, sor=input, yaz_ayar=True, zaman=300):
    ru = redirect(port); state = secrets.token_urlsafe(16)
    yetki = f"{LP}/authorization/new?" + urllib.parse.urlencode({"type": "web_server", "client_id": cid, "redirect_uri": ru, "state": state})
    kod = kod_bekle(port, state, lambda: (ac or webbrowser.open)(yetki), zaman)
    g = http(f"{LP}/authorization/token?" + urllib.parse.urlencode({"type": "web_server", "client_id": cid, "redirect_uri": ru, "client_secret": csecret, "code": kod}), "POST")
    if not g.get("access_token") or not g.get("refresh_token"): raise Hata("Basecamp belirteç vermedi.")
    yet = http(f"{LP}/authorization.json", bearer=g["access_token"])
    h = hesap_sec([a for a in yet.get("accounts", []) if a.get("product") == "bc3"], sor)
    sv = servis()
    kc_yaz(sv, "access_token", g["access_token"])
    kc_yaz(sv + "-oauth", "oauth", b64({"refresh_token": g["refresh_token"], "client_id": cid, "client_secret": csecret, "redirect_uri": ru, "bitis": int(time.time()) + int(g.get("expires_in") or 1209600)}))
    if yaz_ayar: ayar_yaz(h["id"])
    return h, proje_say(h["href"], g["access_token"])

def deneme():
    k = kc_oku(servis())
    if not k: raise Hata("Anahtar Zinciri'nde Basecamp belirteci yok. Önce bağla: basecamp-baglan.command")
    yet = http(f"{LP}/authorization.json", bearer=k)
    h = [a for a in yet.get("accounts", []) if a.get("product") == "bc3"]
    if not h: raise Hata("Basecamp 3/4 hesabı bulunamadı.")
    return h[0], proje_say(h[0]["href"], k)

def main():
    try:
        if "--deneme" in sys.argv: h, n = deneme()
        else:
            print("Basecamp'i bağlıyorum. Launchpad'de kayıtlı uygulamanın bilgileri gerekir (yönlendirme adresi: " + redirect() + ").")
            cid = getpass.getpass("Client ID: ").strip(); cs = getpass.getpass("Client Secret: ").strip()
            if not cid or not cs: raise Hata("Client ID ve Client Secret boş olamaz.")
            print("Tarayıcıda Basecamp izin sayfası açılıyor; 'Yes, I'll allow access' de."); h, n = baglan(cid, cs)
        print(f"Tamam: Basecamp hesabı '{h.get('name')}', {n} proje okunuyor.")
    except Hata as e: print("Olmadı: " + str(e)); sys.exit(1)
    except KeyboardInterrupt: print("\nİptal edildi."); sys.exit(1)
if __name__ == "__main__": main()
