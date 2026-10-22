#!/usr/bin/env python3
# v0.111.0 — panodan Başlat'la açılan toplantı oturumu arka planda (Terminal yok), kota harcamadan: /baslat → Brifing.app toplantı kipi (brifing.swift bu
# sınamada derlenir) → sahte "claude" (stream-json; soru sorar, izin ister, durdurulur, çöker) → panodaki iletiler, kutudan cevap, izin kartı,
# Durdur, kaldığı yerden yeniden açma, Terminal'e alma; Brifing.app'in toplantı kipinde reddettiği argümanlar.
# aktarici/toplanti-oturum.py, relay.py'deki baslat/girdi/toplanti-oturum uçları ya da brifing.swift'in toplantı kipi değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti-oturum.py
# Gerekenler: swiftc, kurulu Brifing.app (ayar.json'daki uygulama klasöründe; paket iskeleti için).
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8793)
T = os.path.realpath(tempfile.mkdtemp(prefix="topo-")); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): sys.exit("atlandı: Brifing.app ya da swiftc yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True); ikili = os.path.join(app, "Contents/MacOS/SuflorBrifing")
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", ikili, os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
open(sahte, "w").write('''#!/usr/bin/env python3
import json, os, sys, time
if sys.argv[1:2] == ["auth"]: print(json.dumps({"loggedIn": True})); sys.exit(0)
D = os.path.dirname(os.path.abspath(sys.argv[0])); arg = sys.argv[1:]
with open(os.path.join(D, "argumanlar.jsonl"), "a") as f: f.write(json.dumps(arg) + "\\n")
SID = "0f1e2d3c-4b5a-4968-8776-655443322110"
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
yaz = lambda t: pr({"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}})
bitti = lambda st="success": pr({"type": "result", "subtype": st, "total_cost_usd": 0.01, "session_id": SID})
def bekle_cevap(rid):
    while True:
        l = sys.stdin.readline()
        if not l: sys.exit(0)
        o = json.loads(l)
        if o.get("type") == "control_response" and o["response"].get("request_id") == rid: return o["response"]["response"]
def izin(ad, gi, rid):
    pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": ad, "input": gi}]}})
    pr({"type": "control_request", "request_id": rid, "request": {"subtype": "can_use_tool", "tool_name": ad, "input": gi}})
    return bekle_cevap(rid)
pr({"type": "system", "subtype": "init", "session_id": SID})
while True:
    l = sys.stdin.readline()
    if not l: break
    o = json.loads(l)
    if o.get("type") == "control_request": continue  # boşta gelen durdurma
    q = o["message"]["content"]
    if q.startswith("/toplanti"): yaz("Gündem hazır. **Rolün** yürütücü mü?"); bitti()
    elif "izin" in q: c = izin("Bash", {"command": "python3 -c 'print(1)'", "description": "Deneme komutu"}, "r-" + str(time.time())); yaz("İzin: " + c["behavior"]); bitti()
    elif "soru-araci" in q: c = izin("AskUserQuestion", {"questions": []}, "s-1"); yaz("AskUserQuestion: " + c["behavior"] + " · " + c.get("message", "")[:40]); bitti()
    elif "uzun" in q:
        yaz("Uzun iş başladı")
        while True:
            l = sys.stdin.readline()
            if not l: sys.exit(0)
            if json.loads(l).get("request", {}).get("subtype") == "interrupt": bitti("error_during_execution"); break
    elif "cok" in q and not os.path.exists(os.path.join(D, "coktu")): open(os.path.join(D, "coktu"), "w").close(); sys.exit(1)
    elif "beklenmedik" in q: yaz("Kaldığım yerden sürüyorum"); bitti()
    else: yaz("Aldım: " + q); bitti()
''')
os.chmod(sahte, 0o755)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje,
                                               "ortak": "/Users/Shared/Suflor", "claude": sahte, "konusma": False, "yerel_ses": False}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTURUM="1", SUFLOR_TEST_KULAKLIK="0"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
ARG = os.path.join(T, "bin", "argumanlar.jsonl")
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip(); PANO = f"http://127.0.0.1:{PORT}"
    def uc(yol, v=None, anahtar=True, zaman=15):
        h = {"Content-Type": "application/json", "Origin": PANO, **({"X-Suflor-Anahtar": K} if anahtar else {})}
        try: y = urllib.request.urlopen(urllib.request.Request(PANO + yol, data=json.dumps(v).encode() if v is not None else None, headers=h), timeout=zaman)
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")
        return y.status, json.loads(y.read())
    def to(): return uc("/status")[1].get("toplanti_oturum") or {}
    def bekle(kosul, sn=15):
        t0 = time.time()
        while time.time() - t0 < sn:
            v = to()
            if kosul(v): return v
            time.sleep(0.2)
        return to()
    def mesaj(): return uc("/toplanti-oturum?n=0")[1].get("mesaj") or []
    def claude_der(metin, sn=15):
        t0 = time.time()
        while time.time() - t0 < sn:
            if any(m["kim"] == "claude" and metin in m["metin"] for m in mesaj()): return True
            time.sleep(0.2)
        return False
    def izin_kartlari(): return [c for c in uc("/cards")[1].get("cards") or [] if c.get("onay") and "Toplantı oturumu" in c.get("text", "") and c.get("status") == "acik"]

    ok("Başlat'tan önce panoda oturum bölümü yok", to() == {})
    kod, y = uc("/baslat", {"konu": "Deneme oturum", "rol": "yurutucu", "dil": "tr"})
    ok(f"Başlat arka planda açtı ({kod}, arka={y.get('arka')})", kod == 200 and y.get("ok") and y.get("arka") is True)
    v = bekle(lambda v: v.get("durum") == "bekliyor")
    ok(f"oturum soru sordu → durum bekliyor ({v.get('durum')})", v.get("durum") == "bekliyor" and v.get("konu") == "Deneme oturum")
    m = mesaj(); ok("Claude'un sorusu panoda (/toplanti-oturum)", any(x["kim"] == "claude" and "yürütücü mü" in x["metin"] for x in m))
    a = [json.loads(l) for l in open(ARG)][0]
    ok("claude stream-json + izin soruları aktarıcıya (--permission-prompt-tool stdio)", "stream-json" in a and a[a.index("--permission-prompt-tool") + 1] == "stdio")
    st = a[a.index("--settings") + 1]
    ok("kanca dosyası Brifing.app'te denetlenip içerik olarak verildi (izin-kanca, -I -B)", st.startswith("{") and "izin-kanca" in st and "python3 -I -B" in st)
    ok("ilk ileti /toplanti, istem metni argümanda yok", not any(x.startswith("/toplanti") for x in a) and "--permission-mode" not in a and "--resume" not in a)
    ok("eski .command Terminal'e açılmadı (yine yazılır, açılmaz)", "arka planda Claude" in open(os.path.join(T, "relay.log")).read())

    kod, y = uc("/girdi", {"text": "Evet yürütücüyüm"})
    ok(f"oturum beklerken kutudaki yazı ona gider ({y.get('tur')})", y.get("tur") == "oturum")
    ok("cevap Claude'a ulaştı", claude_der("Aldım: Evet yürütücüyüm"))
    ok("kullanıcının cevabı panoda 'ben' olarak", any(x["kim"] == "ben" and x["metin"] == "Evet yürütücüyüm" for x in mesaj()))

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "izin iste"})
    t0 = time.time()
    while time.time() - t0 < 10 and not izin_kartlari(): time.sleep(0.2)
    k = izin_kartlari(); v = to()
    ok(f"araç izni panoda onay kartı ({len(k)}) ve oturum özeti izin={v.get('izin')}", len(k) == 1 and "Bash" in k[0]["text"] and v.get("izin") == 1)
    uc("/card-ack", {"id": k[0]["id"], "status": "onaylandi"})
    ok("Onayla → Claude Code'a allow", claude_der("İzin: allow"))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "izin iste yine"})
    t0 = time.time()
    while time.time() - t0 < 10 and not izin_kartlari(): time.sleep(0.2)
    k = izin_kartlari(); uc("/card-ack", {"id": k[0]["id"], "status": "reddedildi"}) if k else None
    ok("Reddet → deny", claude_der("İzin: deny"))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "soru-araci"})
    ok("AskUserQuestion kartsız reddedilir (soru düz metin olsun)", claude_der("AskUserQuestion: deny") and not izin_kartlari())

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "uzun iş"}); ok("uzun iş sürüyor", claude_der("Uzun iş başladı") and to().get("durum") == "calisiyor")
    kod, y = uc("/girdi", {"text": "hazırlık sırasında not"}); ok(f"oturum çalışırken (izle yok) kutudaki yazı ona gider ({y.get('tur')})", y.get("tur") == "oturum")
    kod, y = uc("/toplanti-oturum", {"islem": "durdur"})
    v = bekle(lambda v: v.get("durum") == "bekliyor")
    ok(f"Durdur → tur kesildi, oturum bekliyor ({v.get('durum')})", y.get("ok") and v.get("durum") == "bekliyor" and any(x["kim"] == "sistem" and "Durduruldu" in x["metin"] for x in mesaj()))

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "cok"})
    ok("süreç çökünce aynı oturum kaldığı yerden açılır (--resume)", claude_der("Kaldığım yerden sürüyorum", 25))
    a = [json.loads(l) for l in open(ARG)]
    ok("yeniden açılışta --resume <oturum kimliği>", len(a) == 2 and a[1][a[1].index("--resume") + 1] == "0f1e2d3c-4b5a-4968-8776-655443322110")

    kod, y = uc("/toplanti-oturum", {"islem": "durdur"}); ok("oturum beklerken Durdur bir şey yapmaz", not y.get("ok"))
    kod, _ = uc("/toplanti-oturum?n=0", anahtar=False); ok(f"iletiler anahtarsız okunmaz ({kod})", kod == 401)
    kod, _ = uc("/toplanti-oturum", {"islem": "durdur"}, anahtar=False); ok(f"işlem anahtarsız yapılmaz ({kod})", kod in (401, 403))

    kod, y = uc("/toplanti-oturum", {"islem": "terminal"})
    cm = open(os.path.join(T, "toplanti-terminal.command")).read() if os.path.exists(os.path.join(T, "toplanti-terminal.command")) else ""
    v = to()
    ok("Terminal'de göster → aynı oturum --resume ile .command'a, arka plandaki kapandı",
       y.get("ok") and "--resume 0f1e2d3c-4b5a-4968-8776-655443322110" in cm and v.get("durum") == "terminalde")
    kod, y = uc("/girdi", {"text": "sonraki not"}); ok(f"Terminal'e alındıktan sonra kutu eski yolda ({y.get('tur')})", y.get("tur") == "not")

    # Brifing.app toplantı kipi: izin listesi dışındaki argümanı ve değiştirilmiş kancayı reddeder (çıkış 3)
    def calistir(args, kanca=None):
        gir, cik = os.path.join(canli, "d-gir.fifo"), os.path.join(canli, "d-cik.fifo")
        ist = os.path.join(canli, "d-istek.json")
        if kanca is not None: json.dump(kanca, open(os.path.join(T, "toplanti-kanca.json"), "w"))
        json.dump({"kip": "toplanti", "claude": sahte, "args": args, "cwd": proje, "cikti": os.path.join(canli, "d-bos"), "giris": gir, "cikis": cik}, open(ist, "w"))
        return subprocess.run([ikili, "--istek", ist], capture_output=True, timeout=10).returncode
    taban = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--permission-prompt-tool", "stdio"]
    ok("--permission-mode bypassPermissions reddedilir", calistir(taban + ["--permission-mode", "bypassPermissions"]) == 3)
    ok("--dangerously-skip-permissions reddedilir", calistir(taban + ["--dangerously-skip-permissions"]) == 3)
    ok("istem metni (konumsal argüman) reddedilir", calistir(taban + ["/toplanti"]) == 3)
    ok("izin sorusu aktarıcıya gitmeyen istek reddedilir", calistir(taban[:5]) == 3)
    iyi = json.load(open(os.path.join(T, "toplanti-kanca.json")))
    kotu = json.loads(json.dumps(iyi)); kotu["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "/bin/sh -c 'curl x' izin-kanca"
    ok("değiştirilmiş kanca komutu reddedilir", calistir(taban + ["--settings", os.path.join(T, "toplanti-kanca.json")], kotu) == 3)
    kotu = json.loads(json.dumps(iyi)); kotu["permissions"] = {"allow": ["Bash"]}
    ok("kanca dosyasına izin eklenirse reddedilir", calistir(taban + ["--settings", os.path.join(T, "toplanti-kanca.json")], kotu) == 3)
    json.dump(iyi, open(os.path.join(T, "toplanti-kanca.json"), "w"))
finally:
    r.terminate()
    try: r.wait(5)
    except subprocess.TimeoutExpired: r.kill()
    subprocess.run(["pkill", "-f", T + "/bin/claude"], capture_output=True)
if HATA: print(f"\n{len(HATA)} kaldı — günlük: {T}/relay.log"); sys.exit(1)
shutil.rmtree(T, ignore_errors=True); print("\ntoplantı oturumu: hepsi geçti")
