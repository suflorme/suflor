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
def izin_id(ad, gi, rid):  # gerçek claude gibi tool_use kimliğiyle (süre günlüğü tool_result'la eşleşir)
    pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": rid, "name": ad, "input": gi}]}})
    pr({"type": "control_request", "request_id": rid, "request": {"subtype": "can_use_tool", "tool_name": ad, "input": gi}})
    return bekle_cevap(rid)
pr({"type": "system", "subtype": "init", "session_id": SID})
open(os.path.join(D, "pid"), "w").write(str(os.getpid())); asili = False
while True:
    l = sys.stdin.readline()
    if not l:
        if asili: time.sleep(120)  # Monitor çalışan gerçek claude gibi: giriş kapansa da çıkmaz
        break
    o = json.loads(l)
    if o.get("type") == "control_request": continue  # boşta gelen durdurma
    q = o["message"]["content"]
    if q.startswith("/toplanti"): yaz("Gündem hazır. **Rolün** yürütücü mü?"); bitti()
    elif q.startswith("metrik-"):  # dış bilgi kaynağı (kurgu bağlayıcı "claude.ai Deneme Metrik"); başka bağlayıcı "Baska"
        def mcp(ad, rid):
            c = izin_id(ad, {"donem": "son_7_gun"}, rid)
            if c["behavior"] == "allow": pr({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": rid, "content": "{}"}]}})
            return c["behavior"]
        M = "mcp__claude_ai_Deneme_Metrik__"
        if q == "metrik-oku": yaz("Metrik oku: " + mcp(M + "get_store_sales", "b-1") + "/" + mcp(M + "list_available_metrics", "b-2")); bitti()
        elif q == "metrik-yaz": yaz("Metrik yaz: " + mcp(M + "update_campaign_settings", "b-3") + "/" + mcp(M + "export_report", "b-4") + "/" + mcp(M + "get_budget_set", "b-5")); bitti()
        elif q == "metrik-baska": yaz("Başka bağlayıcı: " + mcp("mcp__claude_ai_Baska__get_messages", "b-6")); bitti()
        elif q == "metrik-tavan": yaz("Tavan: " + "/".join(mcp(M + "query_metrics", "t-" + str(i)) for i in range(7))); bitti()
        elif q.startswith("metrik-kart"):  # toplantıda konu geçti: sorgu → bilgi kartı (kaynak satırı --neden'de)
            c = mcp(M + "get_paid_performance", "b-7")
            O = json.load(open(os.path.join(D, "ortam.json")))
            import subprocess
            r = subprocess.run([sys.executable, "-B", O["tc"], "--dir", O["canli"], "--relay", O["relay"], "kart", "not", "Ücretli kanal son 7 gün dönüşüm %8 — toplantıda %12 dendi",
                                "--neden", "Kaynak: Deneme Metrik, 14:05"], capture_output=True, text=True, env=dict(os.environ, SUFLOR_AYAR=O["ayar"], PYTHONDONTWRITEBYTECODE="1"))
            yaz("Metrik kart: " + c + " · " + ("kart" if "kart gönderildi" in r.stdout else "kart yok " + r.stderr[-200:])); bitti()
    elif "rutin-ok" in q:  # 31 Ekim: rutin adımlar kartsız
        C, P, TC = D + "/../canli", D + "/../proje/gorusmeler", D + "/../toplanti-claude.py"
        vaka = [("Write", {"file_path": C + "/agenda.json"}), ("Write", {"file_path": C + "/hazir.json"}), ("Edit", {"file_path": P + "/ozet-20261031.md"}),
                ("Write", {"file_path": P + "/ozet-20261031.md.yapi.json"}), ("Bash", {"command": "sleep 5"}), ("Bash", {"command": "sleep 120"}),
                ("Bash", {"command": 'python3 -c "import time; time.sleep(3)"'}), ("Bash", {"command": "python3 -B " + TC + " maliyet"}),
                ("Bash", {"command": "mv " + P + "/a.md.yapi.json " + P + "/b.yapi.json"})]
        r = []
        for i, (ad, gi) in enumerate(vaka): r.append(izin(ad, gi, "oto-%d" % i)["behavior"])
        yaz("Oto: " + "/".join(r)); bitti()
    elif "rutin-disi" in q:
        C, P, TC = D + "/../canli", D + "/../proje/gorusmeler", D + "/../toplanti-claude.py"
        vaka = [("Write", {"file_path": C + "/baska.json"}), ("Write", {"file_path": P + "/../x.md"}), ("Write", {"file_path": P + "/kacak.md"}),
                ("Write", {"file_path": P + "/betik.sh"}), ("Bash", {"command": "sleep 121"}), ("Bash", {"command": "sleep 5; rm -rf x"}),
                ("Bash", {"command": 'python3 -c "import time; time.sleep(3); import os"'}), ("Bash", {"command": "python3 -B " + TC + " eylem onay hepsi"}),
                ("Bash", {"command": "python3 -B " + TC + " maliyet; rm x"}), ("Bash", {"command": "mv " + P + "/a.md " + D + "/b.md"}),
                ("Bash", {"command": "python3 -B " + TC + " maliyet\\nrm x"}), ("Bash", {"command": "sleep 3 > " + P + "/a.md"})]
        r = []
        for i, (ad, gi) in enumerate(vaka): r.append(izin(ad, gi, "disi-%d" % i)["behavior"])
        yaz("Disi: " + "/".join(r)); bitti()
    elif "izin" in q: c = izin("Bash", {"command": "python3 -c 'print(1)' # " + str(time.time()), "description": "Deneme komutu"}, "r-" + str(time.time())); yaz("İzin: " + c["behavior"]); bitti()
    elif "asili" in q: asili = True; yaz("Arka plan işi sürüyor"); bitti()
    elif "secim" in q: yaz("Bu kararda anlaştınız mı?\\n\\n[[seç: Anlaştık | Anlaşmadık | Emin değilim]]"); bitti()
    elif "monitor-izle" in q: c = izin("Monitor", {"command": "PYTHONDONTWRITEBYTECODE=1 python3 -u " + D + "/../toplanti-claude.py izle", "description": "izle"}, "m-1"); yaz("Monitor izle: " + c["behavior"]); bitti()
    elif "monitor-baska" in q: c = izin("Monitor", {"command": "python3 -u /tmp/toplanti-claude.py izle", "description": "x"}, "m-2"); yaz("Monitor başka: " + c["behavior"]); bitti()
    elif "oku-izni" in q:
        c1 = izin("Read", {"file_path": "/x/y/z.md"}, "o-1"); c2 = izin("Grep", {"pattern": "x"}, "o-2"); c3 = izin("Bash", {"command": "python3 -B " + D + "/../toplanti-claude.py saglik", "description": "sağlık"}, "o-3")
        c4 = izin("Bash", {"command": "python3 -B " + D + "/../toplanti-claude.py dokum", "description": "döküm kaydı"}, "o-4"); yaz("Okuma: " + "/".join(c["behavior"] for c in (c1, c2, c3, c4))); bitti()
    elif "yazma-izni" in q: c = izin("Bash", {"command": "python3 -B " + D + "/../toplanti-claude.py eylem ekle kayit x", "description": "yaz"}, "y-1"); yaz("Yazma: " + c["behavior"]); bitti()
    elif "hatirla" in q:
        c1 = izin("WebFetch", {"url": "https://example.com/a"}, "h-1"); c2 = izin("WebFetch", {"url": "https://example.com/a"}, "h-2"); yaz("Hatırla: " + c1["behavior"] + "/" + c2["behavior"]); bitti()
    elif "soru-araci" in q: c = izin("AskUserQuestion", {"questions": []}, "s-1"); yaz("AskUserQuestion: " + c["behavior"] + " · " + c.get("message", "")[:40]); bitti()
    elif "uzun" in q:
        pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "sleep 99", "description": "Proje belgelerini taramak"}}]}})
        yaz("Uzun iş başladı")
        pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x/y/rapor-veri.json"}}]}})
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
                                               "ortak": "/Users/Shared/Suflor", "claude": sahte, "konusma": False, "yerel_ses": False,
                                               "toplanti_bilgi_kaynaklari": [{"sunucu": "claude.ai Deneme Metrik", "araclar": ["get_*", "list_*", "query_*", "compare_*"],
                                                                              "konu": "deneme satış ve kanal metrikleri", "ad": "Deneme Metrik"}]}, open(ay, "w"))
json.dump({"tc": os.path.join(T, "toplanti-claude.py"), "canli": canli, "relay": f"http://127.0.0.1:{PORT}", "ayar": ay}, open(os.path.join(T, "bin", "ortam.json"), "w"))
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
    def izin_kartlari(): return [c for c in uc("/cards")[1].get("cards") or [] if c.get("onay") and "Claude şunu yapmak istiyor" in c.get("text", "") and c.get("status") == "acik"]
    def izinler(): return to().get("izinler") or []  # v0.115.0: arka plandaki oturumun izni kart değil, Claude bölümünde (Onayla / Reddet → /eylem-karar)
    def izin_bekle_(sn=10):
        t0 = time.time()
        while time.time() - t0 < sn and not izinler(): time.sleep(0.2)
        return izinler()

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
    k = izin_bekle_(); v = to()
    ok(f"araç izni Claude bölümünde ({len(k)}), ayrı kart yok ({len(izin_kartlari())}), oturum özeti izin={v.get('izin')}", len(k) == 1 and not izin_kartlari() and v.get("izin") == 1)
    _ey = ((uc("/status")[1].get("eylem") or {}).get("liste")) or []; _iz = [x for x in _ey if x.get("tur") == "izin" and x.get("durum") == "bekliyor"]
    ok("izin işinin ayrıntısı görünümde boş (ham JSON yok), başlık cümlesi var", bool(_iz) and all(x.get("ayrinti") == "" and "arac" not in json.dumps(x, ensure_ascii=False) and x.get("baslik") for x in _iz))
    ok("toplantı oturumunun izni sesli sorulmaz (günlükte '+ sesli' yok)", "onay bekliyor (Claude bölümü)" in open(os.path.join(T, "relay.log"), encoding="utf-8", errors="replace").read()
       and "(Claude bölümü + sesli)" not in open(os.path.join(T, "relay.log"), encoding="utf-8", errors="replace").read())
    ok(f"izinde açıklama cümlesi, komut yok ({k[0]['metin'][:80] if k else ''})", bool(k) and "Şunu yapmak istiyorum: Deneme komutu" in k[0]["metin"] and "Claude" not in k[0]["metin"] and "print(1)" not in k[0]["metin"])
    ok("panodaki izin iletisi düz cümle (komut yok)", any(x["kim"] == "izin" and x["metin"] == "Deneme komutu" for x in mesaj()))
    kod, y = uc("/eylem-karar", {"id": k[0]["id"], "durum": "onaylandi"}) if k else (0, {})
    ok("Onayla → Claude Code'a allow, izin listeden düştü", y.get("ok") and claude_der("İzin: allow") and not izinler())
    ok("kararın izi panoda ('İzin verdin.')", any(x["kim"] == "sistem" and x["metin"] == "İzin verdin." for x in mesaj()))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "izin iste yine"})
    k = izin_bekle_(); uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"}) if k else None
    ok("Reddet → deny", claude_der("İzin: deny") and any(x["kim"] == "sistem" and x["metin"] == "İzni reddettin." for x in mesaj()))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "izin iste anahtarsiz"}); k = izin_bekle_()
    kod, y = uc("/eylem-karar", {"id": k[0]["id"], "durum": "onaylandi"}, anahtar=False) if k else (0, {})
    ok(f"izin anahtarsız onaylanamaz ({kod})", kod in (401, 403) and len(izinler()) == 1)
    if k: uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"}); claude_der("İzin: deny")
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "monitor-izle"})
    ok("Suflor'un izle'si (Monitor) kartsız onaylanır", claude_der("Monitor izle: allow") and not izin_kartlari() and not izinler())
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "monitor-baska"})
    t0 = time.time()
    while time.time() - t0 < 10 and not izin_kartlari(): time.sleep(0.2)
    k = izin_bekle_(); ok("başka yerdeki toplanti-claude.py ile Monitor izin ister", len(k) == 1)
    if k: uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"})
    claude_der("Monitor başka: deny")
    # Faz A (S162): salt okuma araçları, Suflor'un okuma komutları ve toplantı sonu döküm kaydı sorulmaz; yazma sorulur; onaylanan izin oturumda hatırlanır; ikinci Başlat oturumu öldürmez
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "oku-izni"})
    ok("Read, Grep, toplanti-claude.py saglik ve dokum kartsız izinli", claude_der("Okuma: allow/allow/allow/allow") and not izin_kartlari() and not izinler())
    # 31 Ekim: rutin adımlar (agenda/hazir/özet yazımı, bekleme, kayıt komutu, özet klasöründe mv) kartsız; dışındakiler sorulur
    os.makedirs(os.path.join(proje, "gorusmeler"), exist_ok=True)
    try: os.symlink("/etc/hosts", os.path.join(proje, "gorusmeler", "kacak.md"))
    except OSError: pass
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "rutin-ok"})
    ok("rutin adımlar (agenda.json, hazir.json, özet .md/.yapi.json, sleep, python bekleme, maliyet, mv) kartsız izinli",
       claude_der("Oto: " + "/".join(["allow"] * 9)) and not izin_kartlari() and not izinler())
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "rutin-disi"}); kesin = 0
    for _ in range(12):
        k = izin_bekle_(8)
        if not k: break
        kesin += 1; uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"}); time.sleep(0.4)
    ok(f"kuralın dışı (başka yol, .., sembolik bağ, .sh, sleep 121, metakarakter, eylem onay, mv dışarı, yeni satır) hepsi sorulur ({kesin}/12)",
       kesin == 12 and claude_der("Disi: " + "/".join(["deny"] * 12)))
    _lg = open(os.path.join(T, "relay.log"), encoding="utf-8", errors="replace").read()
    ok("otomatik izinler günlüğe İZİN: otomatik satırı olarak yazıldı", "İZİN: otomatik — Write agenda.json" in _lg and "İZİN: otomatik — Bash bekleme 5 sn" in _lg)
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "yazma-izni"}); k = izin_bekle_(); ok("toplanti-claude.py eylem ekle (yazma) yine sorulur", len(k) == 1)
    if k: uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"})
    claude_der("Yazma: deny")
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "hatirla"}); k = izin_bekle_(); ok("dışarı erişim (WebFetch) ilk kez sorulur", len(k) == 1)
    if k: uc("/eylem-karar", {"id": k[0]["id"], "durum": "onaylandi"})
    ok("verilen izin oturumda hatırlanır: ikincisi yeniden sorulmaz", claude_der("Hatırla: allow/allow") and not izinler())
    sid0 = to().get("n"); kod, y = uc("/baslat", {"konu": "Deneme oturum", "rol": "yurutucu", "dil": "tr"})
    ok(f"ikinci Başlat canlı oturumu kapatmaz: katıldı ({y})", y.get("ok") and y.get("katildi") is True and to().get("durum") in ("bekliyor", "izliyor") and to().get("n") == sid0)
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "soru-araci"})
    ok("AskUserQuestion kartsız reddedilir (soru düz metin olsun)", claude_der("AskUserQuestion: deny") and not izin_kartlari() and not izinler())
    # dış bilgi kaynağı (ayar toplanti_bilgi_kaynaklari; kurgu bağlayıcı)
    ist = __import__("unicodedata").normalize("NFC", a[a.index("--append-system-prompt") + 1])  # Brifing.app argümanı NFD'ye çevirebiliyor
    ok("oturum istemi kaynağın adını ve konusunu ayardan alır", "«Deneme Metrik»" in ist and "deneme satış ve kanal metrikleri" in ist)
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "metrik-oku"})
    ok("kaynağın okuma araçları sorulmadan geçer", claude_der("Metrik oku: allow/allow") and not izinler() and not izin_kartlari())
    lg = open(os.path.join(T, "relay.log")).read()
    ok("günlükte BİLGİ KAYNAĞI: sunucu · araç · süre (içerik yok)", "BİLGİ KAYNAĞI: claude_ai_Deneme_Metrik · get_store_sales · " in lg and "son_7_gun" not in lg)
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "metrik-yaz"})
    ok("aynı kaynağın yazma/desen dışı araçları sorulmadan reddedilir", claude_der("Metrik yaz: deny/deny/deny") and not izinler())
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "metrik-baska"}); k = izin_bekle_()
    ok("başka bağlayıcının aracı eskisi gibi onaya gider", len(k) == 1)
    if k: uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"})
    claude_der("Başka bağlayıcı: deny")
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "metrik-kart"})
    ok("konu geçince sorgu → bilgi kartı (not, kaynak satırı --neden'de)", claude_der("Metrik kart: allow · kart", 20))
    kk = [c for c in uc("/cards")[1].get("cards") or [] if "dönüşüm %8" in c.get("text", "")]
    ok(f"kart türü not, kaynak görünür ({[(c.get('kind'), c.get('why')) for c in kk]})", len(kk) == 1 and kk[0].get("kind") == "not" and "Kaynak: Deneme Metrik" in (kk[0].get("why") or ""))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "metrik-tavan"}); sorulan = 0  # önceki 3 sorgu + 5 = 8; sonrakiler sorulur
    for _ in range(3):
        k = izin_bekle_(5)
        if not k: break
        sorulan += 1; uc("/eylem-karar", {"id": k[0]["id"], "durum": "reddedildi"}); time.sleep(0.3)
    ok(f"oturum tavanı (8) dolunca sorgu kullanıcıya sorulur ({sorulan} soru)", sorulan == 2 and claude_der("Tavan: allow/allow/allow/allow/allow/deny/deny", 10))
    # izin-kanca (PreToolUse; Terminal kipinde de çalışır): okuma dışı reddedilir, okuma karar almaz; ayar yokken eski davranış
    def kanca(ad, ayar):
        r = subprocess.run(["/usr/bin/python3", "-I", "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", "http://127.0.0.1:1", "izin-kanca"],
                           input=json.dumps({"tool_name": ad, "tool_input": {}}), capture_output=True, text=True, env=dict(os.environ, SUFLOR_AYAR=ayar), timeout=30)
        return (json.loads(r.stdout).get("hookSpecificOutput") or {}).get("permissionDecision") if r.stdout.strip() else None
    bos = os.path.join(T, "ayar-bos.json"); json.dump({k_: v_ for k_, v_ in json.load(open(ay)).items() if k_ != "toplanti_bilgi_kaynaklari"}, open(bos, "w"))
    M = "mcp__claude_ai_Deneme_Metrik__"
    def kanca_bash(c):
        r = subprocess.run(["/usr/bin/python3", "-I", "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", "http://127.0.0.1:1", "izin-kanca"],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}), capture_output=True, text=True, env=dict(os.environ, SUFLOR_AYAR=ay), timeout=30)
        return (json.loads(r.stdout).get("hookSpecificOutput") or {}).get("permissionDecision") if r.stdout.strip() else None
    ok("kanca: python ile bekleme (1–120 sn) riskli sayılmaz; başka satır içi python ve 121 sn yine sorulur (ask: aktarıcı yok)",
       kanca_bash('python3 -c "import time; time.sleep(3)"') is None and kanca_bash('python3 -c "import time; time.sleep(121)"') == "ask" and kanca_bash("python3 -c 'print(1)'") == "ask")
    ok("kanca: okuma aracında karar yok", kanca(M + "get_store_sales", ay) is None and kanca(M + "compare_channels", ay) is None)
    ok("kanca: okuma dışı araç deny", kanca(M + "update_campaign_settings", ay) == "deny" and kanca(M + "export_report", ay) == "deny" and kanca(M + "get_budget_set", ay) == "deny")
    ok("kanca: başka bağlayıcıda değişiklik yok", kanca("mcp__claude_ai_Baska__get_messages", ay) is None)
    ok("kanca: ayar yokken eski davranış (karar yok)", kanca(M + "update_campaign_settings", bos) is None)
    ns = {"re": __import__("re"), "threading": __import__("threading"), "AYAR": {}, "_t": lambda a_, b_: a_}
    exec(compile(open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read(), "toplanti-oturum.py", "exec"), ns)
    ok("aktarıcı: ayar yokken kaynak yok, istem değişmez", ns["bilgi_kaynagi_arac"](M + "get_store_sales") is None and ns["topo_istem"]() == ns["TOPO_ISTEM"])
    ok("sunucu adı biçimi: 'claude.ai X Y' → claude_ai_X_Y", ns["mcp_sunucu_adi"]("claude.ai Deneme Metrik") == "claude_ai_Deneme_Metrik" and ns["mcp_sunucu_adi"]("claude_ai_Deneme_Metrik") == "claude_ai_Deneme_Metrik")

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "uzun iş"}); ok("uzun iş sürüyor", claude_der("Uzun iş başladı") and to().get("durum") == "calisiyor")
    v = bekle(lambda v: (v.get("etkinlik") or {}).get("metin", "").startswith("“rapor"), 5)
    ok(f"canlı durum: son aracın düz cümlesi ({(v.get('etkinlik') or {}).get('metin')})", (v.get("etkinlik") or {}).get("metin") == "“rapor-veri.json” dosyasını okumak" and (v.get("etkinlik") or {}).get("sn", 99) < 5)
    ok("Bash açıklaması da canlı duruma düştü (Ayrıntı'da komut)", any(x["kim"] == "arac" and "Proje belgelerini taramak" in x["metin"] for x in mesaj()))
    kod, y = uc("/girdi", {"text": "hazırlık sırasında not"}); ok(f"oturum çalışırken (izle yok) kutudaki yazı ona gider ({y.get('tur')})", y.get("tur") == "oturum")
    kod, y = uc("/toplanti-oturum", {"islem": "durdur"})
    v = bekle(lambda v: v.get("durum") == "bekliyor")
    ok(f"Durdur → tur kesildi, oturum bekliyor ({v.get('durum')})", y.get("ok") and v.get("durum") == "bekliyor" and any(x["kim"] == "sistem" and "Durduruldu" in x["metin"] for x in mesaj()))
    ok("tur bitince canlı durum silinir", v.get("etkinlik") is None)

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "cok"})
    ok("süreç çökünce aynı oturum kaldığı yerden açılır (--resume)", claude_der("Kaldığım yerden sürüyorum", 25))
    a = [json.loads(l) for l in open(ARG)]
    ok("yeniden açılışta --resume <oturum kimliği>", len(a) == 2 and a[1][a[1].index("--resume") + 1] == "0f1e2d3c-4b5a-4968-8776-655443322110")

    kod, y = uc("/toplanti-oturum", {"islem": "durdur"}); ok("oturum beklerken Durdur bir şey yapmaz", not y.get("ok"))
    urllib.request.urlopen(urllib.request.Request(PANO + "/status", headers={"X-Suflor-Anahtar": K, "X-Suflor-Istemci": "izle"}), timeout=5).read()
    v = to(); ok(f"izle (Monitor) çalışırken tur bitmiş oturum 'izliyor' ({v.get('durum')})", v.get("durum") == "izliyor")
    kod, y = uc("/girdi", {"text": "toplantıda not"}); ok(f"izle çalışırken kutu eski yolda: not + GİRDİ ({y.get('tur')})", y.get("tur") == "iletildi")
    # v0.112.0: seçenekli soru ([[seç: …]])
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "secim"}); claude_der("anlaştınız mı")
    v = bekle(lambda v: (v.get("soru") or {}).get("secenek"))
    sm = [x for x in mesaj() if x["kim"] == "claude" and "anlaştınız mı" in x["metin"]][-1]
    ok("seçenek satırı iletiden ayıklandı, seçenekler ayrı", "[[" not in sm["metin"] and sm.get("secenek") == ["Anlaştık", "Anlaşmadık", "Emin değilim"])
    ok(f"izle sürerken de soru açık ({v.get('durum')}): /status soru.secenek", v.get("durum") == "izliyor" and v["soru"]["i"] == sm["i"] and v["soru"]["secenek"][0] == "Anlaştık")
    kod, y = uc("/girdi", {"text": "Anlaşmadık, bütçe eksik"}); ok(f"seçenekli soru açıkken (izle sürse de) kutu cevabı oturuma ({y.get('tur')})", y.get("tur") == "oturum")
    ok("serbest cevap Claude'a ulaştı, soru kapandı", claude_der("Aldım: Anlaşmadık, bütçe eksik") and not (to().get("soru") or {}).get("secenek"))
    uc("/toplanti-oturum", {"islem": "yaz", "metin": "secim 2"}); time.sleep(0.3); v = bekle(lambda v: (v.get("soru") or {}).get("secenek")); i2 = v["soru"]["i"]
    kod, y = uc("/toplanti-oturum", {"islem": "sec", "i": sm["i"], "secim": "Anlaştık"}); ok("eski sorunun düğmesi reddedilir", not y.get("ok"))
    kod, y = uc("/toplanti-oturum", {"islem": "sec", "i": i2, "secim": "Belki"}); ok("listede olmayan seçim reddedilir", not y.get("ok"))
    kod, y = uc("/toplanti-oturum", {"islem": "sec", "i": i2, "secim": "Anlaştık"})
    ok("düğme → seçim oturuma gider, panoda 'ben' olarak", y.get("ok") and claude_der("Aldım: Anlaştık") and any(x["kim"] == "ben" and x["metin"] == "Anlaştık" and x.get("kaynak") == "düğme" for x in mesaj()))
    ok("cevaptan sonra soru kapandı", not (to().get("soru") or {}).get("secenek"))
    kod, _ = uc("/toplanti-oturum?n=0", anahtar=False); ok(f"iletiler anahtarsız okunmaz ({kod})", kod == 401)
    kod, _ = uc("/toplanti-oturum", {"islem": "durdur"}, anahtar=False); ok(f"işlem anahtarsız yapılmaz ({kod})", kod in (401, 403))

    uc("/toplanti-oturum", {"islem": "yaz", "metin": "asili"}); claude_der("Arka plan işi sürüyor")
    pid = int(open(os.path.join(T, "bin", "pid")).read()); t0 = time.time()
    kod, y = uc("/toplanti-oturum", {"islem": "kapat"}, zaman=30)
    def yasiyor(p):
        try: os.kill(p, 0); return True
        except OSError: return False
    while time.time() - t0 < 15 and yasiyor(pid): time.sleep(0.3)
    ok(f"Kapat: giriş kapanınca çıkmayan claude Brifing.app'te kapatılır ({time.time() - t0:.1f} sn)", y.get("ok") and not yasiyor(pid) and to().get("durum") == "kapali")
    ok("kapandıktan sonra kendiliğinden yeniden açılmaz", (time.sleep(2), to().get("durum"))[1] == "kapali" and any(x["kim"] == "sistem" and "kapatıldı" in x["metin"] for x in mesaj()))
    kod, y = uc("/toplanti-oturum", {"islem": "terminal"})
    cm = open(os.path.join(T, "toplanti-terminal.command")).read() if os.path.exists(os.path.join(T, "toplanti-terminal.command")) else ""
    v = to()
    ok("Terminal'de göster → aynı oturum --resume ile .command'a (izle'yi yeniden başlat iletisiyle), arka plandaki kapandı",
       y.get("ok") and "--resume 0f1e2d3c-4b5a-4968-8776-655443322110" in cm and "yeniden başlat" in cm and v.get("durum") == "terminalde")
    kod, y = uc("/girdi", {"text": "sonraki not"}); ok(f"Terminal'e alındıktan sonra kutu eski yolda ({y.get('tur')})", y.get("tur") in ("not", "iletildi"))
    ok("Terminal'e alınınca panoda: izleme durdu, kutudaki yazı oturuma gitmez", any(x["kim"] == "sistem" and "izlemesi durdu" in x["metin"] and "oturuma gitmez" in x["metin"] for x in mesaj()))

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
