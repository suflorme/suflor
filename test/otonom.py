#!/usr/bin/env python3
# Toplantıda asistanlar (S94 tek kural; aktarici/otonom.py, konus_hitap*) uçtan uca, kota harcamadan: yalıtılmış aktarıcı + Brifing.app açık süreç + sahte "claude".
# İki kanala (ben, karşı) 0,25 sn'de bir yapay ses beslenir (konuşma = ton, sessizlik = hafif gürültü). Senaryolar: kullanıcı çağırmadan karşı taraf seslenemez;
# kullanıcı "<Ad>, …" → asistan katılır, itirazsız söz sırası → toplantıya okuma; katıldıktan sonra karşı taraf sorar; Dur (pano) ve Option + Shift + S;
# konuşma sürerken bekleme; okurken biri konuşursa susma; fırsat çıkmazsa söylenmez; kullanıcı kanalının sözsüz sesi (30 Ekim) söz sırasını tutmaz; ikinci kişilik de herkese; Konuş düğmesi yalnız kullanıcıya;
# kişilik varken "Claude:" asistan değil; ayar (toplantiya_ses) kapalıyken toplantıya okunmaz; v0.157.0: ilk cümlede okuma başlar, devamı ikinci parça. otonom.py, konus_hitap*, toplantiya_soyle ya da Kanal değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/otonom.py
import base64, json, math, os, shutil, struct, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8792); KOKEN = "http://otonom.deneme"
T = tempfile.mkdtemp(prefix="otonom-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
# 30 Ekim test toplantısı: kullanıcının mikrofonunda sözsüz sürekli ses söz sırasını hiç bırakmadı. Saf karar (soz_firsati) aktarıcısız sınanır.
import ast as _ast
_ns = {}; _a = _ast.parse(open(os.path.join(KOD, "aktarici", "otonom.py"), encoding="utf-8").read())
exec(compile(_ast.Module([n for n in _a.body if (isinstance(n, _ast.FunctionDef) and n.name == "soz_firsati") or (isinstance(n, _ast.Assign) and any(
    getattr(t, "id", "") == "OTONOM_YEDEK_SN" for t in getattr(n.targets[0], "elts", n.targets)))], []), "otonom.py", "exec"), _ns)
_sf = _ns["soz_firsati"]
for arg, bek, ad in [((2.0, 2.0, 1, 1.5, False, 99), "sessiz", "herkes sessiz → söz sırası"),
                     ((0.1, 3.0, 2, 1.5, True, 20), "sozsuz", "kullanıcı kanalı sözsüz ses, karşı sessiz → söylenir"),
                     ((0.1, None, 2, 1.5, True, 20), "sozsuz", "yalnız kullanıcı kanalı akıyor, sözsüz → söylenir"),
                     ((0.1, 0.2, 2, 1.5, True, 20), None, "karşı taraf konuşuyor → kullanıcı kanalı sözsüz olsa da beklenir"),
                     ((0.1, 3.0, 10, 1.5, False, 20), None, "kural yok, 10 sn → beklenir"),
                     ((0.1, 3.0, 16, 1.5, False, 20), "yedek", "16 sn, kullanıcının sözlü satırı yok, karşı sessiz → yedek kural"),
                     ((0.1, 3.0, 16, 1.5, False, 3), None, "16 sn ama kullanıcı 3 sn önce sözlü satır verdi → beklenir"),
                     ((0.1, 0.5, 16, 1.5, False, 20), None, "16 sn ama karşı taraf konuşuyor → beklenir"),
                     ((0.1, 3.0, 16, 1.5, False, 20, 0), None, "yedek kapalı (otonom_yedek_sn 0) → beklenir")]:
    v = _sf(*arg); ok(f"soz_firsati: {ad} ({v})", v == bek)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc") or not os.path.exists("/Users/Shared/Suflor/whisper-venv/bin/python"): sys.exit("atlandı: Brifing.app, swiftc ya da whisper-venv yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1
    ot = "toplantıya okunur, herkes duyar" in q; kim = next((a for a in ("MATLAS", "ATLAS") if f"[Bu soruyu {a} cevaplıyor]" in q), "?")
    yk = "yalnız kullanıcı duyar" in q
    if "zebra" in q[-200:]:  # v0.157.0 (yalnız sorunun kendisinde; defter önceki soruları da taşır): ilk cümle hemen, ikincisi 4 sn sonra (okuma ilk cümlede başlamalı)
        for parca, bek in (("İlk cümle hemen geldi.", 0.05), (" İkinci cümle sonra geldi.", 4.0), ("\\n---\\n", 0.05), ("Ayrıntı yavaş.", 0.05)):
            time.sleep(bek); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
        pr({"type": "result", "duration_api_ms": 300, "total_cost_usd": 0.01 * n, "num_turns": 1, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}}); continue
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
      "claude": sahte, "toplantiya_ses": True, "kisilik": kis, "kisilik_toplanti_disi": kis2, "otonom_bekle_sn": 6, "karsi_onay_sn": 10}
json.dump(AY, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="1", SUFLOR_TEST_KOKEN=KOKEN, SUFLOR_TEST_TS_AYGIT="7", SUFLOR_TEST_METIN="1"),
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
    son = lambda: log().count("OTONOM: söz sırası (")  # okuma başladı (v0.157.0: bir cevap birden çok parçada okunabilir — parça değil cevap sayılır)
    hazir = lambda: log().count("OTONOM: cevap hazır")
    def izin_kart(): return next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and c.get("status") == "acik" and "okuyayım mı" in c.get("text", "")), None)
    def izin_ver(durum="onaylandi", sn=20):  # v0.97.0 (Y2): karşı tarafa cevap onay kartı
        t = time.time()
        while time.time() - t < sn:
            c = izin_kart()
            if c: uc("/card-ack", {"id": c["id"], "status": durum}, pano=True); return c
            time.sleep(0.2)
    SUSKU = lambda: time.sleep(13)  # KARSI_HITAP_SUSKU_SN: asistan okuduktan sonra 10 sn karşı hitabı sayılmaz (kendi sesinin yankısı)
    # 0) kullanıcı çağırmadan karşı taraf seslenemez
    n0 = hazir(); satir("karsi", "Atlas, teslim tarihi ne zaman?"); time.sleep(4)
    ok("asistan katılmadan karşı tarafın seslenmesi sayılmadı", hazir() == n0 and "adıyla soruldu" not in log())
    # 1) kullanıcı "Atlas, …" → katılır → itirazsız söz sırası → okundu
    s0 = son(); satir("ben", "Atlas, teslim tarihi ne zaman?")
    v, t1 = bekle(lambda v: v.get("durum") in ("itiraz", "sira", "okunuyor", "okundu"), 20)
    ok("kullanıcı adıyla çağırdı: asistan katıldı", t1 is not None and "ASİSTAN: ATLAS toplantıya katıldı" in log())
    ok("itiraz penceresi yok (söz sırası bekleniyor)", "itiraz penceresi" not in log() and "söz sırası bekleniyor" in log())
    v, t2 = bekle(lambda v: v.get("durum") == "okundu", 15); ok("toplantıya bir kez okundu", t2 is not None and son() == s0 + 1)
    ok("istemde 'herkes duyar' bağlamı", "Otonom bağlam geldi" in ((st().get("konus") or {}).get("cevap") or ""))  # v0.157.0: okuma ilk cümlede başlar — cevap okunurken tamamlanır
    ok("cevap kulağa ayrıca okunmadı", "SES (deneme): " + "Teslim tarihi cuma" not in log())
    time.sleep(0.5); md = "".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))  # Faz B: tek toplantı, ad sayfa başlığından değil
    sat = [l for l in md.splitlines() if "SUFLOR" in l]
    ok(f"dökümde SUFLOR (sesli) satırı: tanıtım + sesli kısım, ayrıntı yok ({len(sat)} satır)", sat and "Merhaba, ben Atlas." in " ".join(sat) and "Teslim tarihi cuma" in " ".join(sat) and "Otonom bağlam geldi" in " ".join(sat) and "Ayrıntı" not in " ".join(sat))
    ok("/status: ATLAS toplantıda", ((st().get("konus") or {}).get("asistan") or {}).get("katilan") == ["ATLAS"])
    # 1b) v0.157.0: ilk cümlede konuşma — Claude ikinci cümleyi 4 sn sonra yazar; okuma ilk cümleyle başlar, ikincisi aynı okumanın devamı
    SUSKU(); s0 = son(); i0 = ot().get("id"); g0 = log().count("OTONOM: gecikme"); satir("ben", "Atlas, zebra planını anlatır mısın?")
    v, tb = bekle(lambda v: v.get("id") != i0 and v.get("durum") in ("okunuyor", "okundu"), 20); c_ilk = (st().get("konus") or {}).get("cevap") or ""; i1 = v.get("id")
    time.sleep(0.3); uc("/olay", {"tur": "soyle-web", "metin": "caliyor"}, koken=KOKEN)  # eklentinin bildirimi (deneme: eklenti yok)
    ok(f"ilk cümle hazırken okuma başladı, ikinci cümle henüz yoktu ({c_ilk[:40]!r})", tb is not None and "İlk cümle hemen geldi." in c_ilk and "İkinci" not in c_ilk and "Claude yazıyor, ilk" in log())
    v, tb2 = bekle(lambda v: v.get("id") == i1 and v.get("durum") == "okundu", 25)
    ok("ikinci cümle aynı okumanın 2. parçası olarak okundu", tb2 is not None and son() == s0 + 1 and "OTONOM: 2. parça okunuyor" in log() and "OTONOM: toplantıya okundu (2 parça)" in log())
    ok(f"panoda tam cevap (sesli kısmın tamamı, ayrıntı yok): {v.get('metin')!r}", "İlk cümle hemen geldi." in (v.get("metin") or "") and "İkinci cümle sonra geldi." in (v.get("metin") or "") and "Ayrıntı" not in (v.get("metin") or ""))
    time.sleep(0.5); md = "".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md")); sat = [l for l in md.splitlines() if "SUFLOR" in l]
    ok("dökümde iki parça da, ayrıntı yok", any("İlk cümle hemen geldi." in l for l in sat) and any("İkinci cümle sonra geldi." in l for l in sat) and not any("Ayrıntı yavaş" in l for l in sat))
    t_g = time.time()
    while time.time() - t_g < 15 and log().count("OTONOM: gecikme") == g0: time.sleep(0.3)
    gs = [l for l in log().splitlines() if "OTONOM: gecikme" in l][g0:]
    ok(f"gecikme satırı: ilk cümle hazır + Claude cevabı çalma başladıktan sonra bitti ({gs[-1][gs[-1].find('ilk cümle'):] if gs else '-'})", gs and "ilk cümle hazır" in gs[-1] and "çalma başladıktan" in gs[-1])
    # 2) katıldıktan sonra karşı taraf sorar; konuşma sürerken bekler, susunca okur
    SUSKU(); s0 = son(); MOD["karsi"] = "konus"; satir("karsi", "Atlas, kaç kişi katılacak?")
    v, _ = bekle(lambda v: v.get("durum") == "itiraz" and v.get("kim") == "Ayla Ö", 20); time.sleep(1.5)
    kc = izin_kart()
    ok("karşı tarafa cevap: onay kartı, onaysız okunmadı (v0.97.0)", kc is not None and "Ayla Ö" in kc["text"] and ot().get("durum") == "itiraz" and son() == s0)
    satir("ben", "Atlas, oku."); time.sleep(1)
    ok("'Atlas, oku' sesle onayladı, kart kapandı", "ASİSTAN: 'ATLAS, oku'" in log() and izin_kart() is None)
    v, _ = bekle(lambda v: v.get("durum") == "sira", 10); time.sleep(2.5)
    ok("katılan asistana karşı taraf sordu; konuşma sürerken söz sırası bekleniyor", ot().get("durum") == "sira" and son() == s0)
    MOD["karsi"] = "sessiz"; tk = time.time(); v, t3 = bekle(lambda v: v.get("durum") in ("okunuyor", "okundu"), 8)
    ok(f"susunca ≥ 1,5 sn sonra okumaya başladı ({time.time() - tk:.1f} sn)", t3 is not None and 1.4 <= time.time() - tk <= 4)
    bekle(lambda v: v.get("durum") == "okundu", 15); ok("bekledikten sonra bir kez okundu", son() == s0 + 1)
    # 3) Dur (pano) söz sırası beklerken
    SUSKU(); s0 = son(); MOD["karsi"] = "konus"; time.sleep(1.0); satir("ben", "Atlas, bütçe ne kadar?")  # v0.157.0: ilk cümle ~60 ms'de hazır — karşı konuşma önce işlensin
    v, _ = bekle(lambda v: v.get("durum") == "sira", 20)
    uc("/otonom", {"id": v.get("id"), "karar": "iptal"}, pano=True); MOD["karsi"] = "sessiz"; time.sleep(4)
    ok("Dur ile iptal: toplantıya okunmadı", ot().get("durum") == "iptal" and son() == s0)
    ok("/otonom yalnız pano kökeninden", uc("/otonom", {"karar": "iptal"}, koken="http://kotu.ornek").get("kod") == 403)
    # 4) Option + Shift + S (metinsiz /komut soyle) söz sırası beklerken durdurur
    s0 = son(); MOD["karsi"] = "konus"; time.sleep(1.0); satir("ben", "Atlas, sonraki adım ne?")
    v, _ = bekle(lambda v: v.get("durum") == "sira", 20)
    r6 = uc("/komut", {"tur": "soyle"}, pano=True); MOD["karsi"] = "sessiz"; time.sleep(4)
    ok("Option + Shift + S durdurdu", ot().get("durum") == "iptal" and son() == s0 and "söylenmeyecek" in (r6.get("metin") or ""))
    # 5) okurken biri konuşursa susar
    satir("ben", "Atlas, toplantı kaç dakika sürecek, uzunca anlatır mısın?")
    v, _ = bekle(lambda v: v.get("durum") == "okunuyor", 20); time.sleep(0.6); MOD["karsi"] = "konus"
    v, t4 = bekle(lambda v: v.get("durum") == "kesildi", 5); MOD["karsi"] = "sessiz"
    ok("okurken karşı taraf konuştu → okuma durdu (kesildi)", t4 is not None and "OTONOM: biri konuştu" in log())
    # 6) fırsat çıkmazsa söylenmez (otonom_bekle_sn 6)
    SUSKU(); s0 = son(); MOD["ben"] = "konus"; satir("karsi", "Atlas, sunumu kim yapacak?"); izin_ver()
    v, t5 = bekle(lambda v: v.get("durum") == "soylenmedi", 20); MOD["ben"] = "sessiz"
    ok(f"sürekli konuşmada fırsat çıkmadı → söylenmedi ({v.get('neden')})", t5 is not None and son() == s0)
    # 7) "Atlas, dur" — okunan bir şey yokken de sorun çıkarmaz, kesme komutu Claude'a gitmez
    n7 = hazir(); satir("ben", "Atlas, dur."); time.sleep(2)
    ok("'Atlas, dur' asistana soru olarak gitmedi", hazir() == n7 and "ASİSTAN: 'ATLAS, dur'" in log())
    # 8) ikinci kişilik (toplantı dışı) de adıyla çağrılınca herkese; katıldıktan sonra karşı taraf ona da sorar
    SUSKU(); s0 = son(); satir("ben", "Matlas, bugün ne konuştuk?")
    v, t9 = bekle(lambda v: v.get("durum") == "okundu" and son() == s0 + 1, 25)
    c = (st().get("konus") or {}).get("cevap") or ""
    ok("ikinci kişilik de herkese: toplantıya okundu", t9 is not None and "Kişi MATLAS." in c and "Otonom bağlam geldi" in c and "ASİSTAN: MATLAS toplantıya katıldı" in log())
    ok("panoda etiket ikinci kişiliğin adı", (st().get("konus") or {}).get("kisilik") == "MATLAS")
    time.sleep(0.5); md = "".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))  # Faz B: tek toplantı, ad sayfa başlığından değil
    ok("toplantıya okunan metinde konuşma dili yok (Bakıyorum)", "Bakıyorum." in " ".join([l for l in md.splitlines() if "SUFLOR" in l][-3:]))
    SUSKU(); s0 = son(); satir("karsi", "Matlas, bize de özet verir misin?"); izin_ver()
    v, t10 = bekle(lambda v: v.get("durum") == "okundu" and son() == s0 + 1, 25)
    ok("katılan ikinci kişiliğe karşı taraf sordu → MATLAS herkese", t10 is not None and "Kişi MATLAS." in ((st().get("konus") or {}).get("cevap") or ""))
    # 8b) v0.97.0 (Y2): karşı tarafa cevap — Reddet → okunmaz; onay gelmezse (karsi_onay_sn 10) okunmaz, kart kapanır
    SUSKU(); s0 = son(); satir("karsi", "Atlas, maliyet ne kadar?"); izin_ver("reddedildi")
    v, tr_ = bekle(lambda v: v.get("durum") == "iptal", 10)
    ok(f"karşı tarafa cevap reddedildi → okunmadı ({v.get('neden')})", tr_ is not None and son() == s0 and "reddedildi" in log())
    SUSKU(); s0 = son(); satir("karsi", "Atlas, toplantı nerede?")
    v, tz = bekle(lambda v: v.get("durum") == "soylenmedi", 25)
    ok(f"onay gelmedi → okunmadı, kart kapandı ({v.get('neden')})", tz is not None and son() == s0 and "onay gelmedi" in (v.get("neden") or "") and izin_kart() is None)
    # 8c) 30 Ekim: kullanıcı kanalında sözsüz sürekli ses (ton → Whisper sözsüz döner) söz sırasını tutmaz; okuma da o sesle kesilmez; karşı kanal sessiz
    SUSKU(); s0 = son(); MOD["ben"] = "konus"; time.sleep(16)  # ≥ 2 parça sözsüz dönsün (parça en çok 6 sn)
    satir("karsi", "Atlas, salon hazır mı?"); izin_ver()
    v, t12 = bekle(lambda v: v.get("durum") in ("okundu", "kesildi", "soylenmedi"), 25); MOD["ben"] = "sessiz"
    ok(f"kullanıcı kanalında sözsüz ses varken okundu ({v.get('durum')}, {v.get('neden')})", t12 is not None and v.get("durum") == "okundu" and son() == s0 + 1
       and "kullanıcı kanalındaki ses söz sırasını tutmadı (son parçalar sözsüz" in log())
    # 9) Konuş düğmesi (bas) toplantıda yalnız kullanıcıya
    SUSKU(); n9 = hazir(); s0 = son(); uc("/bas-konus", {"metin": "Atlas, bütçe kalemleri neler?"}, pano=True); time.sleep(4)
    c = (st().get("konus") or {}).get("cevap") or ""
    ok("Konuş düğmesi: yalnız kullanıcıya (toplantıya okunmadı)", "Yalnız kullanıcı." in c and "Otonom bağlam yok" in c and hazir() == n9 and son() == s0)
    # 10) kişilik varken "Claude:" asistan değil
    n10 = hazir(); satir("ben", "Claude, kaç kart açık acaba?"); time.sleep(4)
    ok("kişilik varken 'Claude,' asistana gitmedi", hazir() == n10)
    # 11) ayar kapalı (Asistanlar toplantıda konuşsun): cevap var ama toplantıya okunmaz
    ok("ayar kapatıldı", uc("/ayar", {"degisen": {"toplantiya_ses": False}}, pano=True).get("ok"))
    n11 = hazir(); satir("ben", "Atlas, kaç kart açık acaba?"); time.sleep(6)
    ok("ayar kapalıyken toplantıya okunmadı (yalnız kullanıcıya)", hazir() == n11 and "Yalnız kullanıcı." in ((st().get("konus") or {}).get("cevap") or ""))
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    DUR.set(); r.terminate(); r.wait(5)
    if HATA or sys.exc_info()[0]: print("günlük:", os.path.join(T, "relay.log"))
    else: shutil.rmtree(T, ignore_errors=True)
print("otonom:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")
