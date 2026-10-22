#!/usr/bin/env python3
# Kullanıcı izni (v0.97.0, aktarici/izin.py; güvenlik denetimi Y1/K1) — kota harcamadan, Whisper ve Claude olmadan, yalıtılmış aktarıcıyla:
#  1) anahtarsız yazma (Y1): ilk istek 403 "izin bekliyor" + onay kartı + eylem kuyruğunda yerel izin işi; Onayla → aynı kaynak yazabilir (12 sa);
#     başka köken ayrıca sorulur; Reddet → 30 dk sorulmaz; anahtarsız Onayla geçmez; anahtarlı istek hiç sormaz.
#  2) /izin-iste (K1): anahtarsız 401; anahtarlı istek kullanıcı kararını bekler (Onayla → onaylandi, Reddet → reddedildi, cevap yok → zaman_asimi).
#  3) toplanti-claude.py izin-kanca: riskli Bash/MCP aracında onay → allow, red → deny, aktarıcı yok → ask; riskli olmayan araçta çıktı yok.
#  4) panodan Başlat: toplanti-baslat.command --settings ile kanca dosyasını verir (PreToolUse, Bash|mcp__.*).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/izin.py
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8786)
T = tempfile.mkdtemp(prefix="izin-"); canli = os.path.join(T, "canli"); os.makedirs(canli); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad, flush=True); HATA.append(ad) if not k else None
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log"); env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
L = lambda: open(log, encoding="utf-8", errors="replace").read()
EK = "chrome-extension://" + "a" * 32; EK2 = "chrome-extension://" + "b" * 32
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None, anahtar=True, koken=None, zaman=10):
        h = {"Content-Type": "application/json", **({"X-Suflor-Anahtar": K} if anahtar else {}), **({"Origin": koken} if koken else {})}
        try: y = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers=h), timeout=zaman)
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")
        return y.status, json.loads(y.read())
    PANO = f"http://127.0.0.1:{PORT}"
    def izin_kartlari(): return [c for c in uc("/cards")[1].get("cards") or [] if c.get("onay") and c.get("text", "").startswith("İzin:") and c.get("status") == "acik"]
    # 1) anahtarsız yazma
    kod, y = uc("/note", {"text": "anahtarsız not"}, anahtar=False, koken=EK)
    ok(f"anahtarsız ilk istek → 403 izin bekliyor ({kod})", kod == 403 and y.get("err") == "izin bekliyor")
    k1 = izin_kartlari()
    ok("onay kartı açıldı (kaynak ve uç yazıyor)", len(k1) == 1 and EK[:30] in k1[0]["text"] and "/note" in k1[0]["text"])
    ey = (uc("/cards")[1].get("eylem") or {}).get("liste") or []
    ok("eylem kuyruğunda yerel izin işi (bekliyor)", any(x["tur"] == "izin" and x.get("yerel") and x["durum"] == "bekliyor" for x in ey))
    kod, _ = uc("/note", {"text": "ikinci"}, anahtar=False, koken=EK)
    ok("onay beklerken yine 403, ikinci kart açılmaz", kod == 403 and len(izin_kartlari()) == 1)
    kod, _ = uc("/card-ack", {"id": k1[0]["id"], "status": "onaylandi"}, anahtar=False, koken=EK)
    ok(f"anahtarsız Onayla geçmez ({kod})", kod in (401, 403) and len(izin_kartlari()) == 1)
    kod, _ = uc("/card-ack", {"id": k1[0]["id"], "status": "onaylandi"}, koken=PANO); time.sleep(0.3)
    kod2, _ = uc("/note", {"text": "onaydan sonra"}, anahtar=False, koken=EK)
    ok(f"Onayla → aynı kaynak yazabilir ({kod2})", kod == 200 and kod2 == 200 and not izin_kartlari())
    kod, _ = uc("/note", {"text": "başka eklenti"}, anahtar=False, koken=EK2)
    k2 = izin_kartlari(); ok("başka köken ayrıca sorulur", kod == 403 and len(k2) == 1 and EK2[:30] in k2[0]["text"])
    uc("/card-ack", {"id": k2[0]["id"], "status": "reddedildi"}, koken=PANO); time.sleep(0.3)
    kod, _ = uc("/note", {"text": "reddedilen"}, anahtar=False, koken=EK2)
    ok("Reddet → 403 ve yeni kart açılmaz", kod == 403 and not izin_kartlari())
    kod, _ = uc("/note", {"text": "anahtarlı"}, koken=EK2)
    ok("anahtarlı istek izin sormaz", kod == 200 and not izin_kartlari())
    ok("izin kaydı 0600", oct(os.stat(os.path.join(canli, "izin-kayit.jsonl")).st_mode & 0o777) == "0o600")
    # 2) /izin-iste
    kod, _ = uc("/izin-iste", {"arac": "send_message", "ozet": "x"}, anahtar=False)
    ok(f"/izin-iste anahtarsız 401 ({kod})", kod == 401)
    def karar_ver(durum, gecikme=0.8):
        def f():
            time.sleep(gecikme); c = izin_kartlari()
            if c: uc("/card-ack", {"id": c[-1]["id"], "status": durum}, koken=PANO)
        threading.Thread(target=f, daemon=True).start()
    karar_ver("onaylandi"); kod, y = uc("/izin-iste", {"arac": "send_message", "ozet": "alıcı: x, konu: deneme"}, zaman=30)
    ok(f"/izin-iste kararı bekler → onaylandi ({y.get('karar')})", kod == 200 and y.get("karar") == "onaylandi")
    karar_ver("reddedildi"); kod, y = uc("/izin-iste", {"arac": "javascript_tool", "ozet": "document.title"}, zaman=30)
    ok(f"Reddet → reddedildi ({y.get('karar')})", y.get("karar") == "reddedildi")
    t = time.time(); kod, y = uc("/izin-iste", {"arac": "navigate", "ozet": "https://ornek.test", "bekle": 1.5}, zaman=30)
    ok(f"cevap yok → zaman_asimi ({y.get('karar')}, {time.time() - t:.1f} sn)", y.get("karar") == "zaman_asimi" and time.time() - t < 5)
    ok("süresi dolan kart panoda kapanır (v0.112.2: onaylanırsa bekleyen yoktu, ikinci kart açılıyordu)", not izin_kartlari())
    for c in izin_kartlari(): uc("/card-ack", {"id": c["id"], "status": "reddedildi"}, koken=PANO)
    # v0.112.2: kartta komut/JSON yok, düz cümle (kullanıcı: "kodu göstermenin anlamı yok")
    def kart_metni(govde):
        karar_ver("reddedildi", 0.8); t_ = {}
        def yakala():
            for _ in range(20):
                c = izin_kartlari()
                if c: t_["m"] = c[-1]["text"]; return
                time.sleep(0.1)
        th = threading.Thread(target=yakala); th.start(); uc("/izin-iste", govde, zaman=30); th.join(); return t_.get("m", "")
    m = kart_metni({"arac": "Bash (satır içi python)", "ad": "Bash", "ozet": "python3 -c 'import json;print(1)'", "aciklama": "Kulis'in veri dosyasını okuyup test listesini çıkarmak"})
    ok(f"Bash: kartta açıklama cümlesi, komut yok ({m[:90]})", "Kulis'in veri dosyasını okuyup test listesini çıkarmak" in m and "Onaylıyor musun" in m and "python3" not in m and "import" not in m)
    m = kart_metni({"arac": "Bash (satır içi python)", "ad": "Bash", "ozet": "python3 -c 'print(2)'"})
    ok(f"Bash açıklamasız: genel cümle, komut yok ({m[:80]})", "komut çalıştırmak" in m and "print" not in m)
    m = kart_metni({"arac": "create_draft", "ad": "mcp__gmail__create_draft", "ozet": '{"to":"Deniz T","subject":"Toplantı notu","body":"{x}"}', "girdi": {"to": "Deniz T", "subject": "Toplantı notu"}})
    ok(f"MCP: düz cümle + alıcı/konu, JSON yok ({m[:90]})", "e-posta taslağı hazırlamak" in m and "Deniz T" in m and "Toplantı notu" in m and "{" not in m)
    # 3) izin-kanca
    def kanca(girdi, relay=f"http://127.0.0.1:{PORT}"):
        return subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", relay, "izin-kanca"],
                              input=json.dumps(girdi), capture_output=True, text=True, env=env, timeout=60).stdout.strip()
    ok("riskli olmayan Bash → çıktı yok", kanca({"tool_name": "Bash", "tool_input": {"command": "python3 toplanti-claude.py kart not deneme"}}) == "")
    ok("Read → çıktı yok", kanca({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}) == "")
    ok("riskli olmayan MCP (okuma) → çıktı yok", kanca({"tool_name": "mcp__x__search_threads", "tool_input": {"q": "a"}}) == "")
    karar_ver("onaylandi", 1.5); o = kanca({"tool_name": "Bash", "tool_input": {"command": "PYTHONDONTWRITEBYTECODE=1 python3 -c 'print(1)'"}})
    ok(f"satır içi python + Onayla → allow ({o[:90]})", '"permissionDecision": "allow"' in o and '"hookEventName": "PreToolUse"' in o)
    karar_ver("reddedildi", 1.5); o = kanca({"tool_name": "mcp__gmail__send_message", "tool_input": {"to": "x", "subject": "deneme"}})
    ok(f"e-posta gönderme + Reddet → deny ({o[:80]})", '"permissionDecision": "deny"' in o)
    o = kanca({"tool_name": "mcp__claude-in-chrome__navigate", "tool_input": {"url": "https://ornek.test"}}, relay="http://127.0.0.1:9")
    ok(f"aktarıcı yok → ask ({o[:80]})", '"permissionDecision": "ask"' in o)
    for c in izin_kartlari(): uc("/card-ack", {"id": c["id"], "status": "reddedildi"}, koken=PANO)
    # 4) panodan Başlat → --settings kanca dosyası
    kod, y = uc("/baslat", {"konu": "İzin deneme"}, koken=PANO); time.sleep(0.5)
    cmd = open(os.path.join(T, "toplanti-baslat.command"), encoding="utf-8").read() if os.path.exists(os.path.join(T, "toplanti-baslat.command")) else ""
    kj = os.path.join(T, "toplanti-kanca.json"); kk = json.load(open(kj)) if os.path.exists(kj) else {}
    h = ((kk.get("hooks") or {}).get("PreToolUse") or [{}])[0]
    ok("Başlat: toplanti-baslat.command --settings ile kanca dosyasını verir", f"--settings {kj}" in cmd or f"--settings '{kj}'" in cmd)
    ok("kanca dosyası: PreToolUse, Bash|mcp__.*, izin-kanca, zaman aşımı ≥ 180", h.get("matcher") == "Bash|mcp__.*" and "izin-kanca" in h["hooks"][0]["command"] and h["hooks"][0]["timeout"] >= 180)
finally:
    r.terminate()
    try: r.wait(5)
    except Exception: r.kill()
print(f"\nizin: {'✓ hepsi geçti' if not HATA else '✗ ' + str(len(HATA)) + ' hata'}"); sys.exit(1 if HATA else 0)
