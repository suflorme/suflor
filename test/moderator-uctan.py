#!/usr/bin/env python3
# Moderatör uçtan uca (v0.83.0, S93; aktarici/moderator.py), kota harcamadan: test/otonom.py düzeni (yalıtılmış aktarıcı + Brifing.app açık süreç + sahte "claude",
# iki kanala yapay ses). Senaryo: kullanıcı toplantıda toplantı dışı kişiliğe "toplantıyı sen yönet, gündem: …" der → moderatör başlar (Claude'a soru gitmez) →
# başla görevi o kişilikle Konuş sürecine gider → otonom yoldan toplantıya okunur → karşı taraf o kişiliğe seslenince (otonom ayarı kapalıyken de) cevap toplantıya →
# "sonraki madde" → ikinci madde açılır → "yönetimi geri alıyorum" → kapanır. moderator.py, konus_hitap*, otonom_acik ya da _konus_sor değişince koştur (~1,5 dk):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/moderator-uctan.py
import base64, json, math, os, shutil, struct, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8793); KOKEN = "http://otonom.deneme"
T = tempfile.mkdtemp(prefix="moderator-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc") or not os.path.exists("/Users/Shared/Suflor/whisper-venv/bin/python"): sys.exit("atlandı: Brifing.app, swiftc ya da whisper-venv yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1
    ot = "toplantıya okunur, herkes duyar" in q; kim = next((a for a in ("MATLAS", "ATLAS") if f"[Bu soruyu {a} cevaplıyor]" in q), "?")
    if "[Moderatör görevi" in q: ot = "doğrudan toplantıya okunur" in q; kim = kim + (" moderatör-" + ("basla" if "devraldığını" in q else "ac" if "Sıradaki maddeyi aç" in q else "diger"))
    yk = "yalnız kullanıcı duyar" in q
    for parca in ["Teslim tarihi cuma.", " Bakıyorum." if kim == "MATLAS" else "", " Otonom bağlam geldi." if ot else " Otonom bağlam yok.", "\\n---\\n", "Ayrıntı.", f" Kişi {kim}.", " Yalnız kullanıcı." if yk else ""]:
        time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    pr({"type": "result", "duration_api_ms": 300, "total_cost_usd": 0.01 * n, "num_turns": 1, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
kis = os.path.join(T, "kisilik.md")
open(kis, "w", encoding="utf-8").write("---\nad: ATLAS\nhitap: Atlas\nokunus: atlas\ntanitim: Merhaba, ben Atlas.\nselam: Merhaba.\n---\n## Kişilik: ATLAS\nAdın ATLAS.\n")
os.chmod(kis, 0o600)
kis2 = os.path.join(T, "kisilik2.md")  # v0.61.0: toplantı dışı kişilik — toplantıda adıyla çağrılınca yalnız kullanıcıya, isterse toplantıya
open(kis2, "w", encoding="utf-8").write("---\nad: MATLAS\nhitap: Matlas\nhitap_bicimi: sen\nkonusma_dili: evet\n---\n## Kişilik: MATLAS\nAdın MATLAS.\n")
ay = os.path.join(T, "ayar.json")
AY = {"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor",
      "claude": sahte, "otonom": False, "toplantiya_ses": True, "kisilik": kis, "kisilik_toplanti_disi": kis2, "otonom_bekle_sn": 6}
json.dump(AY, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="1", SUFLOR_TEST_KOKEN=KOKEN, SUFLOR_TEST_TS_AYGIT="7"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
log = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8", errors="replace").read()
MOD = {"ben": "sessiz", "karsi": "sessiz"}; DUR = threading.Event()
def ses_parca(konus, n=4000):  # 0,25 sn 16 kHz
    if konus: return b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * i / 16000))) for i in range(n))
    return b"".join(struct.pack("<h", (i * 7919 % 61) - 30) for i in range(n))
TON, SUS = ses_parca(True), ses_parca(False)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None, koken=None, pano=False):
        h = {"X-Suflor-Anahtar": K, "Content-Type": "application/json", **({"Origin": koken} if koken else {"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    st = lambda: uc("/status")
    ot = lambda: (st().get("konus") or {}).get("otonom") or {}
    def besle():
        while not DUR.is_set():
            t = int(time.time() * 1000)
            for kanal in ("ben", "karsi"):
                uc("/ses", {"kanal": kanal, "t": t, "pcm": base64.b64encode(TON if MOD[kanal] == "konus" else SUS).decode(), "meeting": {"title": "Moderatör deneme"}}, koken=KOKEN)
            time.sleep(0.25)
    def nabiz():
        while not DUR.is_set(): uc("/ping", {"meeting": {"title": "Moderatör deneme"}, "call": True, "panel": True, "mic": {"on": True}}); time.sleep(5)
    threading.Thread(target=besle, daemon=True).start(); threading.Thread(target=nabiz, daemon=True).start(); time.sleep(2)
    n_satir = [0]
    def satir(kanal, metin):
        n_satir[0] += 1; kim = "Deniz T" if kanal == "ben" else "Ayla Ö"
        uc("/ingest", {"meeting": {"title": "Moderatör deneme"}, "source": "whisper", "entries": [{"id": f"o/{n_satir[0]}", "speaker": kim, "time": time.strftime("%H:%M:%S"), "text": metin, "kanal": kanal}]})
    def bekle(kosul, sn):
        t = time.time()
        while time.time() - t < sn:
            v = ot()
            if kosul(v): return v, time.time() - t
            time.sleep(0.1)
        return ot(), None
    son = lambda: log().count("TOPLANTIYA SÖYLE (")
    cevap = lambda: ((st().get("konus") or {}).get("cevap") or "")
    mod = lambda: (st().get("konus") or {}).get("moderator") or {}
    def bekle_log(parca, sn, n0=0):
        t = time.time()
        while time.time() - t < sn:
            if log().count(parca) > n0: return True
            time.sleep(0.2)
        return False
    satir("karsi", "Merhaba, ben Ayla."); time.sleep(1)
    # 1) kullanıcı toplantı dışı kişiliğe yönetimi devreder
    s0 = son(); satir("ben", "Matlas, toplantıyı sen yönet, gündem: bütçe ve takvim, her madde 5 dakika.")
    ok("moderatör başladı: MATLAS, 2 madde, 5 dk", bekle_log("MODERATÖR: başladı · MATLAS · 2 madde · madde başına 5.0 dk", 10))
    ok("komut Claude'a soru olarak gitmedi (başla görevi gitti)", bekle_log("MODERATÖR: basla · Bütçe", 10))
    v, t1 = bekle(lambda v: v.get("durum") == "itiraz", 25)
    ok("başla görevi otonom yoldan: itiraz penceresi", t1 is not None and "OTONOM: cevap hazır (moderator)" in log())
    ok("görevi MATLAS cevapladı, istemde 'doğrudan toplantıya okunur'", "Kişi MATLAS moderatör-basla" in cevap() and "Otonom bağlam geldi" in cevap())
    bekle(lambda v: v.get("durum") == "okundu", 20); ok("açılış toplantıya okundu", son() == s0 + 1)
    m = mod(); ok(f"durum: madde 1/2 Bütçe, kalan süre var ({m.get('kalan_sn')} sn)", m.get("acik") and m.get("sira") == 1 and m.get("madde") == "Bütçe" and (m.get("kalan_sn") or 0) > 200)
    # 2) karşı taraf moderatör kişiliğine seslenir (otonom ayarı kapalı)
    time.sleep(13); s0 = son(); satir("karsi", "Matlas, bütçe ne kadar?")
    v, t2 = bekle(lambda v: v.get("durum") == "itiraz" and v.get("kim") == "Ayla Ö", 25)
    ok("karşı taraf moderatöre seslendi → otonom (ayar kapalıyken de)", t2 is not None)
    bekle(lambda v: v.get("durum") == "okundu", 20); ok("cevabı MATLAS verdi ve toplantıya okundu", "Kişi MATLAS" in cevap() and son() == s0 + 1)
    # 3) sonraki madde
    time.sleep(2); n0 = log().count("MODERATÖR: ac"); satir("ben", "Matlas, sonraki maddeye geçelim.")
    ok("'sonraki madde' komutu: ikinci madde açılıyor", bekle_log("MODERATÖR: ac · Takvim", 25, n0))
    bekle(lambda v: v.get("durum") == "okundu" and "moderatör-ac" in cevap(), 25); ok("ikinci madde açılışı okundu", "moderatör-ac" in cevap())
    # 4) yönetimi geri al
    time.sleep(2); satir("ben", "Matlas, tamam yönetimi geri alıyorum.")
    ok("yönetimi geri alınca kapandı", bekle_log("MODERATÖR: kapandı", 10) and not mod().get("acik"))
    ok("aktarıcıda hata yok", "Traceback" not in log() and "MODERATÖR: hata" not in log())
finally:
    DUR.set(); r.terminate(); r.wait(5)
    if HATA or sys.exc_info()[0]: print("günlük:", os.path.join(T, "relay.log"))
    else: shutil.rmtree(T, ignore_errors=True)
print("moderatör uçtan uca:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")
