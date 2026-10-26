#!/usr/bin/env python3
# Beta geliştirme verisi (S141): hiçbir metin değeri Mac'ten çıkmamalı. Üç katman:
#  1) teshis.temizle: içerik dolu yapay paket (ad, proje, dosya adı, e-posta, şifre benzeri, kart/soru metni anahtarda ve değerde) → hiçbiri kalmaz;
#     izinli seçenekler (adım, platform, sonuç, hafta) kalır.
#  2) Uçtan uca aktarıcı: yalıtılmış relay.py (SUFLOR_TEST_BETA: kısa süreler) yapay içerikli toplantıyla; yerel alıcıya gelen toplantı sonu ve
#     haftalık paket — sızıntı yok, beklenen sayılar var; gönderilen kopyası teshis/gonderilen/'de.
#  3) Kurulum sihirbazı (SUFLOR_EV deneme): adımlar → "bitti" paketi; yeni açılış yarıda kalınca "yarida" paketi ve bırakılan adım.
# Deneme aktarıcısı/sihirbazı gerçek Worker'a göndermez (teshis.DENEME) — bunu da denetler.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/beta-veri.py      (~40 sn; kaldı → çıkış 1)
EPOSTA = "zeynep" + chr(64) + "ornek.com"  # yapay adres (yayın taraması düz e-posta biçimini durdurur)
import http.server, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__)); KOD = os.path.dirname(BURA); sys.path.insert(0, BURA); sys.path.insert(0, KOD)
from bosport import bos_port
ok = []
def kontrol(ad, kosul, ek=""): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad + ("" if kosul else f"  [{ek}]"))
GIZLI = ["Zeynep", "Kartaloğlu", "Bozkurt", "sozlesme", EPOSTA, "Akdeniz", "Hayalet", "parola123", "Kumbara", "Poyrazcan", "Lodos"]
def sizinti(veri):
    m = json.dumps(veri, ensure_ascii=False).lower()
    return [g for g in GIZLI if g.lower() in m]

# ---------- 1) süzgeç ----------
import teshis
teshis.DENEME = True
p = {"tur": "haftalik", "hafta": "2026-H43", "ortam": {"kurulum": "0123456789ab", "kod": "0.120.0", "model": "Mac16,1", "gelistirici": True},
     "kullanim": {"toplanti_disi": {"sesli": 3, "Zeynep": 2, "toplam": 5}, "gun": 4},
     "kart_turu": {"soyle": {"kart": 2}, "Proje Bozkurt": {"kart": 1}}, "toplantilar": {"platformlar": {"meet": 2, "Akdeniz Toplantısı": 1}},
     "profil": {"ses_motoru": "pocket", "tema": "Hayalet", "hitap_bicimi": "sen", "tarz": "rahat", "asistan_adi": "Poyrazcan"},
     "kalite": {"not": "Zeynep Kartaloğlu sozlesme.docx dosyasını " + EPOSTA + " adresine gönderdi, parola123", "sayi": 5321234567},
     "adimlar": [{"adim": "claude", "sn": 12}, {"adim": "Kumbara", "sn": 3}], "sonuc": "Lodos", "birakilan": "claude",
     "gozlem": "Zeynep çok gergindi; Bozkurt projesi", "Lodos kart metni": "Hayalet"}
t = teshis.temizle(p)
kontrol("süzgeç: içerik dolu pakette hiçbir gizli sözcük kalmadı", not sizinti(t), sizinti(t))
kontrol("süzgeç: izinli seçenekler kaldı (hafta, platform, adım, ses motoru, hitap, tarz)",
        t["hafta"] == "2026-H43" and t["toplantilar"]["platformlar"].get("meet") == 2 and t["adimlar"][0]["adim"] == "claude" and t["profil"]["ses_motoru"] == "pocket"
        and t["profil"]["hitap_bicimi"] == "sen" and t["profil"]["tarz"] == "rahat" and t["birakilan"] == "claude", json.dumps(t, ensure_ascii=False)[:300])
kontrol("süzgeç: bilinmeyen seçenek '?' (sonuç, tema, adım)", t["sonuc"] == "?" and t["profil"]["tema"] == "?" and t["adimlar"][1]["adim"] == "?")
kontrol("süzgeç: Claude gözlemi (serbest metin) gitmez", t.get("gozlem") is None)
kontrol("süzgeç: 10 haneli sayı değer olarak kalır (sayı içerik değil), metin içinde maskeli", t["kalite"]["sayi"] == 5321234567 and "5321234567" not in t["kalite"]["not"])
# klasör türü (S141): sahte ev klasöründe sağlayıcı yolları; hesap/e-posta kısmı pakete girmez
_ev = tempfile.mkdtemp(prefix="suflor-ev-")
for d in ("Library/CloudStorage/GoogleDrive-" + EPOSTA + "/My Drive/P", "Library/CloudStorage/OneDrive-Kisisel/P", "Library/CloudStorage/Box-Box/P",
          "Library/Mobile Documents/com~apple~CloudDocs/P", "Library/Mobile Documents/com~apple~CloudDocs/Documents", "Documents/P", "Desktop/P", "Dropbox/P"):
    os.makedirs(os.path.join(_ev, d))
_kt = {d: teshis.klasor_turu(os.path.join(_ev, d), ev=_ev) for d in ("Library/CloudStorage/GoogleDrive-" + EPOSTA + "/My Drive/P", "Library/CloudStorage/OneDrive-Kisisel/P",
       "Library/CloudStorage/Box-Box/P", "Library/Mobile Documents/com~apple~CloudDocs/P", "Documents/P", "Desktop/P", "Dropbox/P", "yok/P")}
kontrol("klasör türü: googledrive, onedrive, diger_bulut, icloud (Belgeler eşitlemesi dahil), yerel, dropbox, yok",
        list(_kt.values()) == ["googledrive", "onedrive", "diger_bulut", "icloud", "icloud", "yerel", "dropbox", "yok"], _kt)
json.dump({"proje": os.path.join(_ev, "Desktop/P"), "t": time.time(), "sayilar": {"dosya": 40, "bulutta": 7, "bulut_kisayol": 2, "okunamayan": 1, "erisilemeyen": ["Zeynep"]}},
          open(os.path.join(_ev, "tarama.json"), "w"))
_po = teshis.temizle({"proje": teshis.proje_olcu(os.path.join(_ev, "Desktop/P"), _ev)})["proje"]
kontrol("proje ölçüsü son taramadan: 40 dosya, 7 yalnız bulutta, 2 kısayol, 2 okunamayan; ad yok",
        _po.get("dosya") == 40 and _po.get("bulutta") == 7 and _po.get("bulut_kisayol") == 2 and _po.get("okunamayan") == 2 and not sizinti(_po), _po)
shutil.rmtree(_ev, ignore_errors=True)
kontrol("deneme: gerçek Worker adresine gönderim kapalı", teshis.acik({}) is False and teshis.acik({"teshis_adres": "http://127.0.0.1:9/"}) is True)

# ---------- yerel alıcı ----------
GELEN = []; UA = []
class Al(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        UA.append(self.headers.get("User-Agent") or "")
        b = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try: GELEN.append(json.loads(b))
        except ValueError: GELEN.append({"ham": b.decode("utf-8", "replace")})
        o = b'{"ok":true}'; self.send_response(200); self.send_header("Content-Length", str(len(o))); self.end_headers(); self.wfile.write(o)
AP = bos_port(8781); srv = http.server.ThreadingHTTPServer(("127.0.0.1", AP), Al); threading.Thread(target=srv.serve_forever, daemon=True).start()
ADRES = f"http://127.0.0.1:{AP}/"
def bekle(kosul, sn):
    son = time.time() + sn
    while time.time() < son:
        if kosul(): return True
        time.sleep(0.3)
    return False

T = tempfile.mkdtemp(prefix="suflor-beta-")
procs = []
try:
    # ---------- 2) uçtan uca aktarıcı ----------
    kod = os.path.join(T, "kod"); os.makedirs(kod)
    for f in ("relay.py", "toplanti-claude.py", "baglam.py", "yapi.py", "taahhut.py", "teshis.py", "kullanim.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), kod)
    for d in ("marka", "pano", "aktarici"): shutil.copytree(os.path.join(KOD, d), os.path.join(kod, d))
    uyg = os.path.join(T, "uyg"); canli = os.path.join(uyg, "canli"); os.makedirs(canli); os.makedirs(os.path.join(T, "proje"))
    PORT = bos_port(8798)
    json.dump({"alan": "Test", "ad": "Zeynep Kartaloğlu", "port": PORT, "uygulama": uyg, "proje": os.path.join(T, "proje"), "ortak": os.path.join(T, "ortak"),
               "yerel_ses": False, "dil": "tr", "teshis_adres": ADRES, "ses_motoru": "mac", "tema": "koyu"}, open(os.path.join(T, "ayar.json"), "w"), ensure_ascii=False)
    # Konuş kaydı (toplantıda iki soru, biri 12 sn), toplantı dışı bir soru — metin alanı yok, aktarıcı da yazmaz
    simdi = time.strftime("%Y-%m-%dT%H:%M:%S+03:00")
    with open(os.path.join(canli, "claude-cagri.jsonl"), "w") as f:
        for r in ({"is": "bas-konus", "kaynak": "hitap", "toplantida": True, "ses_ms": 2100, "ilk_ms": 1500, "giris": 1000, "maliyet": 0.01},
                  {"is": "bas-konus", "kaynak": "bas", "toplantida": True, "ses_ms": 12500, "ilk_ms": 9000, "giris": 900, "maliyet": 0.02},
                  {"is": "bas-konus", "kaynak": "yazili", "toplantida": False, "ses_ms": None, "ilk_ms": 1800, "giris": 800, "maliyet": 0.01}):
            f.write(json.dumps(dict(r, at=simdi)) + "\n")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BETA="1")
    rl = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=kod, env=env, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    procs.append(rl)
    anahtar = lambda: open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def istek(yol, g=None):
        r = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=None if g is None else json.dumps(g).encode(), method="GET" if g is None else "POST",
                                   headers={"Content-Type": "application/json", "X-Suflor-Anahtar": anahtar()})
        return json.loads(urllib.request.urlopen(r, timeout=5).read() or b"{}")
    kontrol("deneme aktarıcısı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")) and bool(istek("/status")), 20))
    M = {"title": "Akdeniz Bozkurt Projesi — Zeynep Kartaloğlu"}
    istek("/ping", {"meeting": M, "panel": True, "rows": 12, "call": True, "ver": "test", "platform": "meet"})
    for i in range(12):
        istek("/ingest", {"meeting": M, "source": "transcript", "entries": [{"id": f"b/{i}", "speaker": "Zeynep Kartaloğlu", "time": f"00:{i:02d}",
                                                                             "text": f"Hayalet sözleşmesini Kumbara'ya gönder, parola123, Lodos {i}"}]})
    istek("/card", {"kind": "soyle", "text": "Zeynep'e Bozkurt sözleşmesini sor", "why": "Akdeniz"})
    istek("/ask", {"tur": "ozet"}); istek("/komut", {"tur": "sessiz"}); istek("/komut", {"tur": "sessiz"})
    gel = lambda tur: [g for g in GELEN if g.get("tur") == tur]
    open(os.path.join(canli, "beta-haftalik-simdi"), "w").close()  # haftalık paket şimdi (deneme kipi: bu haftanın sayıları)
    kontrol("haftalık paket yerel alıcıya geldi", bekle(lambda: gel("haftalik"), 15), [g.get("tur") for g in GELEN])
    kontrol("toplantı sonu paketi geldi (toplantı 4 sn sessiz kalınca)", bekle(lambda: gel("toplanti_sonu"), 25), open(os.path.join(T, "relay.log")).read()[-600:])
    kontrol("gelen paketlerin hiçbirinde ad, konu, dosya, şifre ya da metin yok", not sizinti(GELEN), sizinti(GELEN))
    if gel("toplanti_sonu"):
        k = gel("toplanti_sonu")[-1].get("kalite") or {}
        kontrol("toplantı sonu: kalite — satır gecikmesi, Konuş ilk ses ve 10 sn üstü oran, hitap",
                "satir_gecikme_sn" in k and (k.get("konus") or {}).get("cevap") == 2 and (k["konus"].get("on_sn_ustu_yuzde") == 50) and k.get("hitap") == 1, json.dumps(k)[:400])
        kontrol("toplantı sonu: Claude gözlemi ve son günlük satırları yok", not gel("toplanti_sonu")[-1].get("son_olaylar"))
        kontrol("toplantı sonu: platform toplantının kendisinden (meet)", (gel("toplanti_sonu")[-1].get("toplanti") or {}).get("platform") == "meet")
    # haftalık paket toplantı sürerken ilk turda kurulur (deneme kipinde hemen): toplantı sonrası sayılar ikinci pakette yok, bu yüzden kalanı sayıdan bak
    if gel("haftalik"):
        h = gel("haftalik")[-1]
        kontrol("haftalık: kullanım (kullanim.py) — toplantı dışı yazılı 1, toplantıda herkese 1 + kulağa 1",
                (h["kullanim"].get("toplanti_disi") or {}).get("yazili") == 1 and (h["kullanim"].get("toplanti_ici") or {}).get("herkese") == 1
                and (h["kullanim"].get("toplanti_ici") or {}).get("kulaga") == 1, json.dumps(h.get("kullanim"))[:300])
        kontrol("haftalık: özellik (Ne diyeyim 1, Sessiz 1 — kapatma sayılmaz) ve profil (ses mac, tema koyu)",
                h["ozellik"].get("ne_diyeyim") == 1 and h["ozellik"].get("sessiz") == 1 and h["profil"].get("ses_motoru") == "mac" and h["profil"].get("tema") == "koyu",
                json.dumps([h.get("ozellik"), h.get("profil")])[:300])
        kontrol("haftalık: maliyet (bas_konus 3 çağrı) ve kimlik yalnız kurulum numarası", ((h.get("maliyet") or {}).get("claude") or {}).get("bas_konus", {}).get("cagri") == 3
                and re.fullmatch(r"[0-9a-f]{12}", h["ortam"]["kurulum"]), json.dumps(h.get("maliyet"))[:300])
    kontrol("istek kendi kimliğiyle (Cloudflare Python-urllib'i 1010 ile engelliyor)", UA and all(u.startswith("Suflor.me/") for u in UA), UA[:2])
    gk = os.listdir(os.path.join(uyg, "teshis", "gonderilen")) if os.path.isdir(os.path.join(uyg, "teshis", "gonderilen")) else []
    kontrol("gönderilen paketlerin kopyası teshis/gonderilen/'de", any("haftalik" in f for f in gk) and any("toplanti_sonu" in f for f in gk), gk)
    olay = json.load(open(os.path.join(canli, "beta-olay.json"))) if os.path.exists(os.path.join(canli, "beta-olay.json")) else {}
    kontrol("olay kaydında yalnız ad ve zaman (satır metni yok)", olay and not sizinti(olay) and all(len(x) == 2 for x in olay.get("olay", [])), str(olay)[:200])
    rl.terminate(); rl.wait(5)

    # ---------- 3) kurulum sihirbazı ----------
    GELEN.clear()
    ev = os.path.join(T, "ev"); destek = os.path.join(ev, "Library", "Application Support", "Suflor"); os.makedirs(destek)
    json.dump({"teshis_adres": ADRES, "uygulama": os.path.join(ev, "uyg")}, open(os.path.join(destek, "ayar.json"), "w"))
    def sihirbaz():
        sp = bos_port(8771)
        p_ = subprocess.Popen([sys.executable, os.path.join(KOD, "kurulum.py"), "--port", str(sp)], env=dict(env, SUFLOR_EV=ev), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        procs.append(p_); k = None
        for _ in range(40):
            l = p_.stdout.readline()
            m = re.search(r"\?k=(\S+)", l or "")
            if m: k = m.group(1); break
        url = f"http://127.0.0.1:{sp}"
        o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor()); o.open(f"{url}/?k={k}", timeout=5)
        def kaydet(adim): o.open(urllib.request.Request(f"{url}/api/kaydet", data=json.dumps({"dil": "tr", "adim_id": adim, "cevap": {"ad": "Zeynep Kartaloğlu", "sirket": "Bozkurt"}}).encode(),
                                                        headers={"Content-Type": "application/json", "Origin": url}), timeout=5)
        return p_, kaydet
    p1, kaydet = sihirbaz()
    for a in ("karsilama", "hosgeldin", "mac", "claude", "sen", "asistan", "proje", "kur", "takvim", "eklenti", "bitti"): kaydet(a); time.sleep(0.05)
    kontrol("kurulum: 'bitti' paketi geldi", bekle(lambda: [g for g in GELEN if g.get("tur") == "kurulum" and g.get("sonuc") == "bitti"], 20), GELEN[-1:] if GELEN else "yok")
    b = next((g for g in GELEN if g.get("tur") == "kurulum"), {})
    kontrol("kurulum: adım süreleri, Claude, model, Mac (sayı ve seçenek)", [x["adim"] for x in b.get("adimlar", [])][:3] == ["karsilama", "hosgeldin", "mac"]
            and "claude" in b and "model" in b and b.get("ortam", {}).get("bellek_gb"), json.dumps(b)[:300])
    p1.terminate(); p1.wait(5)
    kontrol("kurulum: bitmiş kurulumda kapanınca yarıda paketi gitmez", not [g for g in GELEN if g.get("sonuc") == "yarida"])
    p2, kaydet = sihirbaz()
    for a in ("karsilama", "hosgeldin", "mac", "claude"): kaydet(a)
    kontrol("kurulum: 'claude' adımında bırakıldı → yarıda paketi, bırakılan adım claude", bekle(lambda: [g for g in GELEN if g.get("sonuc") == "yarida" and g.get("birakilan") == "claude"], 20),
            [(g.get("sonuc"), g.get("birakilan")) for g in GELEN])
    kontrol("kurulum paketlerinde ad ve şirket yok", not sizinti(GELEN), sizinti(GELEN))
    p2.terminate(); p2.wait(5)
finally:
    for p_ in procs:
        try: p_.kill()
        except Exception: pass
    srv.shutdown()
    if "--sakla" in sys.argv: print("geçici klasör:", T)
    else: shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
