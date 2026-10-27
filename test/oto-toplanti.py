#!/usr/bin/env python3
# S161 (v0.144.0) — toplantıyı kendisi tanıma, kota harcamadan (sahte claude, Brifing.app bu sınamada derlenir):
#  1) Başlat'sız Meet (eklenti nabzı, Meet kodu adıyla): takvimdeki toplantının adıyla dosya hemen açılır, başlık "Google Meet" der (Teams değil), toplantı
#     oturumu sormadan açılır; Meet kodlu ve "Toplantı" adlı satır/not aynı dosyaya gider; süren toplantıda elle Başlat yeni oturum ve kayıt açmaz;
#     sinyal kesilince toplantı biter.
#  2) Gizli kipte tanınmaz. 3) Masaüstü Teams: aynı anda süren iki takvim toplantısından platformu tutan seçilir; ayar oto_haric'teki adda oturum açılmaz.
# aktarici/oto-toplanti.py, baslat, paths/ensure_header (ad eşleme) değişince koştur:  PYTHONDONTWRITEBYTECODE=1 python3 test/oto-toplanti.py
import datetime, glob, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8781)
T = os.path.realpath(tempfile.mkdtemp(prefix="oto-")); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): sys.exit("atlandı: Brifing.app ya da swiftc yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
open(sahte, "w").write('''#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:2] == ["auth"]: print(json.dumps({"loggedIn": True})); sys.exit(0)
D = os.path.dirname(os.path.abspath(sys.argv[0]))
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
pr({"type": "system", "subtype": "init", "session_id": "0f1e2d3c-4b5a-4968-8776-655443322110"})
while True:
    l = sys.stdin.readline()
    if not l: break
    o = json.loads(l)
    if o.get("type") != "user": continue
    with open(os.path.join(D, "iletiler.jsonl"), "a") as f: f.write(json.dumps(o["message"]["content"], ensure_ascii=False) + "\\n")
    pr({"type": "assistant", "message": {"content": [{"type": "text", "text": "İzliyorum."}]}}); pr({"type": "result", "subtype": "success", "total_cost_usd": 0.0})
''')
os.chmod(sahte, 0o755)
simdi = datetime.datetime.now().astimezone(); iso = lambda d: d.isoformat(timespec="seconds")
olay = lambda i, ad, pl, b, s, bag: {"id": i, "baslik": ad, "baslangic": iso(simdi + datetime.timedelta(minutes=b)), "bitis": iso(simdi + datetime.timedelta(minutes=s)),
                                     "tum_gun": False, "takvim": "İş", "platform": pl, "baglanti": bag, "katilimcilar": ["Deniz Yıldız"], "kisi_sayisi": 2}
json.dump({"durum": "ok", "olaylar": [olay("e1", "Deniz ile proje", "meet", -3, 27, "https://meet.google.com/abc-defg-hij"),
                                      olay("e2", "Haftalık plan", "teams", -1, 29, "https://teams.microsoft.com/l/meetup-join/x"),
                                      olay("e3", "Akşam görüşmesi", "meet", 240, 270, "https://meet.google.com/zzz-yyyy-xxx")]}, open(os.path.join(T, "takvim.json"), "w"), ensure_ascii=False)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje,
                                               "ortak": "/Users/Shared/Suflor", "claude": sahte, "konusma": False, "yerel_ses": False, "oto_haric": ["haftalık"]}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
LOG = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(LOG, "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTURUM="1", SUFLOR_TEST_OTO="1",
                              SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0"))
U = f"http://127.0.0.1:{PORT}"; L = lambda: open(LOG, encoding="utf-8").read()
def istek(yol, g=None):
    k = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k}
    if yol in ("/baslat", "/ayar"): h["Origin"] = U  # yalnız pano (ya da eklenti) başlatır / ayar yazar
    q = urllib.request.Request(U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
    return json.load(urllib.request.urlopen(q, timeout=10))
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        if kosul(): return True
        time.sleep(0.3)
    return False
NABIZ = {"g": None}
def nabiz_dongu():
    while True:
        g = NABIZ["g"]
        try:
            if g == "meet": istek("/ping", {"ver": "0.144.0", "meeting": {"title": "abc-defg-hij"}, "panel": False, "rows": 0, "platform": "meet", "call": True, "captions": True})
            elif g == "masaustu": istek("/masaustu", {"uygulama": "Teams", "toplantida": True, "baslik": "Haftalık plan | Microsoft Teams"})
        except Exception: pass
        time.sleep(1)
dosyalar = lambda: sorted(os.path.basename(f) for f in glob.glob(os.path.join(canli, "2*-*.md")))
ILET = os.path.join(T, "bin", "iletiler.jsonl"); iletiler = lambda: open(ILET, encoding="utf-8").read().splitlines() if os.path.exists(ILET) else []
try:
    ok("aktarıcı açıldı", bekle(lambda: os.path.exists(os.path.join(canli, "kart-anahtari.txt")), 20))
    time.sleep(1.5)
    threading.Thread(target=nabiz_dongu, daemon=True).start()
    # 1) Meet, Başlat'sız
    NABIZ["g"] = "meet"
    ok("Meet toplantısı Başlat'sız tanındı (takvimden ad, platform Meet)", bekle(lambda: "OTO: toplantı tanındı — Deniz ile proje · Google Meet · eklenti · takvimden" in L()))
    d1 = [f for f in dosyalar() if f.endswith("-Deniz-ile-proje.md")]
    ok(f"döküm dosyası satır beklemeden açıldı: {dosyalar()}", len(d1) == 1 and len(dosyalar()) == 1)
    bas = open(os.path.join(canli, d1[0]), encoding="utf-8").read() if d1 else ""
    ok("dosya başlığı takvimdeki ad ve Google Meet (Teams değil)", "# Canlı transkript — Deniz ile proje" in bas and "Google Meet canlı altyazı" in bas and "Teams" not in bas)
    ok("toplantı oturumu sormadan açıldı (sahte claude: /toplanti, 'kendiliğinden tanındı')", bekle(lambda: any("/toplanti" in x and "kendiliğinden tanındı" in x for x in iletiler()), 20))
    ok("günlükte 'oturumu açıldı'", "OTO: toplantı oturumu açıldı" in L())
    st = istek("/status"); ok(f"/status oto_toplanti: {st.get('oto_toplanti')}", (st.get("oto_toplanti") or {}).get("ad") == "Deniz ile proje" and st["oto_toplanti"]["platform"] == "meet")
    sec = json.load(open(os.path.join(canli, "takvim-secilen.json"), encoding="utf-8"))
    ok("takvim-secilen.json takvim olayıyla (gündem/katılımcı toplantı oturumuna)", (sec.get("olay") or {}).get("id") == "e1" and sec.get("konu") == "Deniz ile proje")
    istek("/ingest", {"meeting": {"title": "abc-defg-hij", "platform": "meet"}, "source": "captions", "entries": [{"id": "a/1", "speaker": "Deniz Yıldız", "time": "10:00", "text": "Merhaba, başlayalım mı?"}]})
    istek("/ingest", {"meeting": {"title": "Toplantı"}, "source": "whisper", "entries": [{"id": "w/1", "speaker": "Deniz T", "time": "10:01", "text": "Evet, gündemle başlayalım."}]})
    icerik = open(os.path.join(canli, d1[0]), encoding="utf-8").read() if d1 else ""
    ok(f"Meet kodlu ve 'Toplantı' adlı satırlar aynı dosyada: {dosyalar()}", "başlayalım mı" in icerik and "gündemle başlayalım" in icerik and len(dosyalar()) == 1)
    n_il = len([x for x in iletiler() if "/toplanti" in x])
    istek("/status", None)  # pano görünümü
    rb = istek("/baslat", {"konu": "Başka bir konu", "rol": "katilimci", "dil": "tr"})
    time.sleep(2)
    ok(f"süren toplantıda elle Başlat: katıldı, yeni oturum ve kayıt yok ({rb})", rb.get("ok") and rb.get("katildi") and len([x for x in iletiler() if "/toplanti" in x]) == n_il and len(dosyalar()) == 1)
    NABIZ["g"] = None
    ok("sinyal kesilince toplantı bitti", bekle(lambda: "OTO: toplantı bitti — Deniz ile proje" in L(), 40))
    # 2) gizli kipte tanınmaz
    istek("/komut", {"tur": "gizli"}); NABIZ["g"] = "meet"; time.sleep(5)
    ok("gizli kipte tanınmadı", L().count("OTO: toplantı tanındı") == 1)
    NABIZ["g"] = None; time.sleep(8); istek("/komut", {"tur": "gizli"}); time.sleep(2)  # önce eklenti çağrısı düşsün (hızlı kipte 6 sn), sonra gizli kapanır
    # 3) masaüstü Teams: platformu tutan takvim toplantısı, hariç tutulan adda oturum yok
    NABIZ["g"] = "masaustu"
    ok("masaüstü Teams tanındı, iki süren toplantıdan Teams olanı seçildi", bekle(lambda: "OTO: toplantı tanındı — Haftalık plan · Teams · masaüstü · takvimden" in L(), 20))
    ok("hariç tutulan adda toplantı oturumu açılmadı", bekle(lambda: "OTO: toplantı oturumu açılmadı (hariç (haftalık))" in L(), 10))
    ok(f"masaüstü toplantısının dosyası takvim adıyla: {dosyalar()}", bekle(lambda: any(f.endswith("-Haftalık-plan.md") for f in dosyalar()), 10))
    hb = next((open(os.path.join(canli, f), encoding="utf-8").read() for f in dosyalar() if f.endswith("-Haftalık-plan.md")), "")
    ok("masaüstü dosyasının başlığı Teams", "Teams toplantısı" in hb)
    NABIZ["g"] = None
    # 4) v0.145.0: panodaki ⚙ Ayarlar — hariç listesi virgüllü metinden; "Toplantıyı kendisi tanısın" kapalıyken tanınmaz
    ra = istek("/ayar", {"degisen": {"oto_haric": " özel, Bire  Bir ,özel,", "oto_toplanti": False}})
    ayj = json.load(open(ay, encoding="utf-8")); dg = istek("/status")["ayarlar"]["deger"]
    ok(f"ayar kaydı: liste tekilleşti, panoda virgüllü ({ra}, {ayj.get('oto_haric')}, {dg.get('oto_haric')!r})",
       ra.get("ok") and ayj.get("oto_haric") == ["özel", "Bire Bir"] and ayj.get("oto_toplanti") is False and dg.get("oto_haric") == "özel, Bire Bir" and dg.get("oto_toplanti") is False)
    time.sleep(25); n_ = L().count("OTO: toplantı tanındı"); NABIZ["g"] = "meet"; time.sleep(5); NABIZ["g"] = None
    ok("'Toplantıyı kendisi tanısın' kapalıyken tanınmadı", L().count("OTO: toplantı tanındı") == n_)
    ra = istek("/ayar", {"degisen": {"oto_haric": "", "oto_toplanti": True}}); ayj = json.load(open(ay, encoding="utf-8"))
    ok("boş liste ve açık (varsayılan) ayar dosyasından çıkar", ra.get("ok") and "oto_haric" not in ayj and "oto_toplanti" not in ayj)
    ok("aktarıcıda hata yok", "Traceback" not in L() and "OTO: denetim hatası" not in L())
finally:
    r.terminate()
    try: r.wait(5)
    except subprocess.TimeoutExpired: r.kill()
    subprocess.run(["pkill", "-f", T], capture_output=True)
    if HATA: print("günlük:", LOG)
    else: shutil.rmtree(T, ignore_errors=True)
print("oto-toplanti:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
