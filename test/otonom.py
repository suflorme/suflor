#!/usr/bin/env python3
# Otonom katılım (v0.56.0, S68; aktarici/otonom.py) uçtan uca, kota harcamadan: yalıtılmış aktarıcı + Brifing.app açık süreç + sahte "claude".
# İki kanala (ben, karşı) 0,25 sn'de bir yapay ses beslenir (konuşma = ton, sessizlik = hafif gürültü). Senaryolar: karşı tarafın hitabı → 3 sn itiraz →
# söz sırası → toplantıya okuma; ✕ iptal; konuşma sürerken bekleme; okurken biri konuşursa susma; fırsat çıkmazsa söylenmez; Option + Shift + S iptal;
# kullanıcının kendi hitabı; kişilik adıyla karşı hitap; ayar kapalıyken eski davranış. otonom.py, konus_hitap*, toplantiya_soyle ya da Kanal değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/otonom.py
import base64, json, math, os, shutil, struct, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8792; KOKEN = "http://otonom.deneme"
T = tempfile.mkdtemp(prefix="otonom-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
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
    ot = "toplantıya okunur, herkes duyar" in q
    for parca in ["Teslim tarihi cuma.", " Otonom bağlam geldi." if ot else " Otonom bağlam yok.", "\\n---\\n", "Ayrıntı."]:
        time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    pr({"type": "result", "duration_api_ms": 300, "total_cost_usd": 0.01 * n, "num_turns": 1, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
kis = os.path.join(T, "kisilik.md")
open(kis, "w", encoding="utf-8").write("---\nad: ATLAS\nhitap: Atlas\nokunus: atlas\ntanitim: Merhaba, ben Atlas.\nselam: Merhaba.\n---\n## Kişilik: ATLAS\nAdın ATLAS.\n")
os.chmod(kis, 0o600)
ay = os.path.join(T, "ayar.json")
AY = {"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor",
      "claude": sahte, "otonom": True, "toplantiya_ses": True, "kisilik": kis, "otonom_bekle_sn": 6}
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
                uc("/ses", {"kanal": kanal, "t": t, "pcm": base64.b64encode(TON if MOD[kanal] == "konus" else SUS).decode(), "meeting": {"title": "Otonom deneme"}}, koken=KOKEN)
            time.sleep(0.25)
    def nabiz():
        while not DUR.is_set(): uc("/ping", {"meeting": {"title": "Otonom deneme"}, "call": True, "panel": True, "mic": {"on": True}}); time.sleep(5)
    threading.Thread(target=besle, daemon=True).start(); threading.Thread(target=nabiz, daemon=True).start(); time.sleep(2)
    n_satir = [0]
    def satir(kanal, metin):
        n_satir[0] += 1; kim = "Deniz T" if kanal == "ben" else "Ayla Ö"
        uc("/ingest", {"meeting": {"title": "Otonom deneme"}, "source": "whisper", "entries": [{"id": f"o/{n_satir[0]}", "speaker": kim, "time": time.strftime("%H:%M:%S"), "text": metin, "kanal": kanal}]})
    def bekle(kosul, sn):
        t = time.time()
        while time.time() - t < sn:
            v = ot()
            if kosul(v): return v, time.time() - t
            time.sleep(0.1)
        return ot(), None
    son = lambda: log().count("TOPLANTIYA SÖYLE (")  # web yolu (ping call=true) ya da BlackHole (deneme)
    # 1) karşı tarafın hitabı → itiraz → söz sırası → okundu
    s0 = son(); satir("karsi", "Suflor, teslim tarihi ne zaman?")
    v, t1 = bekle(lambda v: v.get("durum") == "itiraz", 20)
    ok(f"karşı hitabı: cevap hazır, itiraz penceresi ({v.get('kalan')} sn kaldı)", t1 is not None and 0 < (v.get("kalan") or 0) <= 3)
    ok("istemde otonom bağlamı (toplantıya okunur, herkes duyar)", "Otonom bağlam geldi" in ((st().get("konus") or {}).get("cevap") or ""))
    ok("cevap kulağa ayrıca okunmadı", "SES (deneme): " + "Teslim tarihi cuma" not in log())
    ta = time.time(); v, t2 = bekle(lambda v: v.get("durum") in ("okunuyor", "okundu"), 10)
    ok(f"3 sn sonra, herkes sessizken toplantıya okumaya başladı ({time.time() - ta:.1f} sn)", t2 is not None and 2.5 <= time.time() - ta <= 7)
    bekle(lambda v: v.get("durum") == "okundu", 15); ok("toplantıya bir kez okundu", son() == s0 + 1)
    time.sleep(0.5); md = "".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md") and "Otonom" in f)
    sat = [l for l in md.splitlines() if "SUFLOR" in l]
    ok(f"dökümde SUFLOR (sesli) satırı: tanıtım + sesli kısım, ayrıntı yok ({len(sat)} satır)", sat and "Merhaba, ben Atlas." in sat[-1] and "Teslim tarihi cuma" in sat[-1] and "Ayrıntı" not in sat[-1])
    v, _ = bekle(lambda v: v.get("durum") == "okundu", 15); ok("durum: okundu", v.get("durum") == "okundu")
    SUSKU = lambda: time.sleep(13)  # KARSI_HITAP_SUSKU_SN: Suflor okuduktan sonra 10 sn karşı hitabı sayılmaz (kendi sesinin yankısı)
    # 2) ✕ iptal
    SUSKU(); s0 = son(); satir("karsi", "Suflor, bütçe ne kadar?")
    v, _ = bekle(lambda v: v.get("durum") == "itiraz", 20)
    uc("/otonom", {"id": v.get("id"), "karar": "iptal"}, pano=True); time.sleep(5)
    ok("✕ ile iptal: toplantıya okunmadı", ot().get("durum") == "iptal" and son() == s0)
    ok("/otonom yalnız pano kökeninden", uc("/otonom", {"karar": "iptal"}, koken="http://kotu.ornek").get("kod") == 403)
    # 3) konuşma sürerken bekler, susunca okur
    s0 = son(); satir("karsi", "Suflor, kaç kişi katılacak?")
    v, _ = bekle(lambda v: v.get("durum") == "itiraz", 20); MOD["karsi"] = "konus"
    v, _ = bekle(lambda v: v.get("durum") == "sira", 6); time.sleep(2.5)
    ok("konuşma sürerken söz sırası bekleniyor", ot().get("durum") == "sira" and son() == s0)
    MOD["karsi"] = "sessiz"; tk = time.time(); v, t3 = bekle(lambda v: v.get("durum") in ("okunuyor", "okundu"), 8)
    ok(f"susunca ≥ 1,5 sn sonra okumaya başladı ({time.time() - tk:.1f} sn)", t3 is not None and 1.4 <= time.time() - tk <= 4)
    bekle(lambda v: v.get("durum") == "okundu", 15); ok("bekledikten sonra bir kez okundu", son() == s0 + 1)
    # 4) okurken biri konuşursa susar
    SUSKU(); satir("karsi", "Suflor, toplantı kaç dakika sürecek, uzunca anlatır mısın?")
    v, _ = bekle(lambda v: v.get("durum") == "okunuyor", 20); time.sleep(0.6); MOD["karsi"] = "konus"
    v, t4 = bekle(lambda v: v.get("durum") == "kesildi", 5); MOD["karsi"] = "sessiz"
    ok("okurken karşı taraf konuştu → okuma durdu (kesildi)", t4 is not None and "OTONOM: biri konuştu" in log())
    # 5) fırsat çıkmazsa söylenmez (otonom_bekle_sn 6)
    SUSKU(); s0 = son(); satir("karsi", "Suflor, sunumu kim yapacak?")
    v, _ = bekle(lambda v: v.get("durum") == "itiraz", 20); MOD["ben"] = "konus"
    v, t5 = bekle(lambda v: v.get("durum") == "soylenmedi", 14); MOD["ben"] = "sessiz"
    ok(f"sürekli konuşmada fırsat çıkmadı → söylenmedi ({v.get('neden')})", t5 is not None and son() == s0)
    # 6) Option + Shift + S (komut soyle) itiraz penceresinde durdurur
    s0 = son(); satir("karsi", "Suflor, sonraki adım ne?")
    v, _ = bekle(lambda v: v.get("durum") == "itiraz", 20)
    r6 = uc("/komut", {"tur": "soyle"}, pano=True); time.sleep(5)
    ok("Option + Shift + S itiraz penceresinde durdurdu", ot().get("durum") == "iptal" and son() == s0 and "söylenmeyecek" in (r6.get("metin") or ""))
    # 7) kullanıcının kendi hitabı (Claude:) ve kişilik adıyla karşı hitap
    satir("ben", "Claude: yarınki toplantı saat kaçta?")
    v, t7 = bekle(lambda v: v.get("durum") == "itiraz", 20); ok("kullanıcının kendi hitabı da otonom", t7 is not None)
    bekle(lambda v: v.get("durum") == "okundu", 15); SUSKU()
    satir("karsi", "Atlas, bu hafta neler yapıldı?")
    v, t8 = bekle(lambda v: v.get("durum") == "itiraz" and v.get("kim") == "Ayla Ö", 20); ok("karşı taraf kişilik adıyla seslendi (Atlas,) → otonom", t8 is not None)
    bekle(lambda v: v.get("durum") == "okundu", 15)
    # 8) ayar kapalı: eski davranış (otonom yok)
    ok("ayar kapatıldı", uc("/ayar", {"degisen": {"otonom": False}}, pano=True).get("ok"))
    satir("ben", "Claude: kaç kart açık acaba?"); time.sleep(6)
    ok("ayar kapalıyken otonom penceresi açılmadı", ot().get("durum") in (None, "okundu") and log().count("OTONOM: cevap hazır") == 8)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    DUR.set(); r.terminate(); r.wait(5)
    if HATA: print("günlük:", os.path.join(T, "relay.log"))
    else: shutil.rmtree(T, ignore_errors=True)
print("otonom:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")
