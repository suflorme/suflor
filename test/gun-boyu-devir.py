#!/usr/bin/env python3
# Gün boyu tek asistan (6 Kasım): toplantı oturumu ↔ Konuş devri. (1) Toplantı bitince (özet kaydı) kısa devir metni canli/gun-devir.json'a yazılır — kararlar,
# işler sahibiyle, açık sorular, kullanıcının toplantı oturumuna kutudan yazdığı soru ve cevabın kısası, notları, özet/döküm yolu — ve Konuş/kutu asistanına
# giden istemde bir kez görünür; (2) toplantı oturumu açılırken son saatlerdeki toplantı dışı Konuş soruları oturumun sistem istemine girer. Gizli ve deneme
# toplantısında ikisi de yok; ayar gun_boyu_devir: false kapatır. Sahte "claude" (kota yok), Brifing.app (swiftc ile derlenir); Whisper gerekmez. Kurgu veri.
# aktarici/toplanti-oturum.py (gun_devir_*, gun_ici_blogu) ya da aktarici/bas-konus.py (gun_devir_blogu) değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gun-boyu-devir.py      (kaldı → çıkış 1)
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8794)
T = os.path.realpath(tempfile.mkdtemp(prefix="gdevir-")); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): sys.exit("atlandı: Brifing.app ya da swiftc yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
# tek sahte: toplantı oturumu (--permission-prompt-tool) argümanları kaydeder ve kutudaki soruyu cevaplar; Konuş (yazılı) her istemi kaydeder
open(sahte, "w").write('''#!/usr/bin/env python3
import json, os, sys, time
if sys.argv[1:2] == ["auth"]: print(json.dumps({"loggedIn": True})); sys.exit(0)
D = os.path.dirname(os.path.abspath(sys.argv[0])); arg = sys.argv[1:]
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
if "--permission-prompt-tool" in arg:
    with open(os.path.join(D, "toplanti-arg.jsonl"), "a") as f: f.write(json.dumps(arg, ensure_ascii=False) + "\\n")
    SID = "1a2b3c4d-0000-4000-8000-00000000abcd"
    pr({"type": "system", "subtype": "init", "session_id": SID})
    for l in sys.stdin:
        o = json.loads(l)
        if o.get("type") != "user": continue
        q = o["message"]["content"]
        t = "Teklif işi Ayşe Örnek'te, cuma teslim." if "kime verdik" in q else "Hazırım."
        pr({"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}); pr({"type": "result", "subtype": "success", "total_cost_usd": 0.01, "session_id": SID})
    sys.exit(0)
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1
    with open(os.path.join(D, "konus-istem.jsonl"), "a") as f: f.write(json.dumps(q, ensure_ascii=False) + "\\n")
    c = "Devir geldi." if "[Bugünkü toplantılardan devir" in q else "Tamam."
    pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": c}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ARG, IST = os.path.join(T, "bin", "toplanti-arg.jsonl"), os.path.join(T, "bin", "konus-istem.jsonl")
def satirlar(y):
    try: return [json.loads(l) for l in open(y, encoding="utf-8")]
    except OSError: return []
class Uc:
    def __init__(s, ad, **ek):
        s.port = bos_port(PORT if ad == "a" else PORT + 7); s.d = os.path.join(T, ad); os.makedirs(s.d); s.log = os.path.join(T, ad + ".log"); yol = os.path.join(T, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Deniz T", "port": s.port, "uygulama": T, "proje": proje, "kod": os.path.join(T, "kod"),
                        "ortak": "/Users/Shared/Suflor", "claude": sahte, "konusma": False, "yerel_ses": False, "konus_gecmis": True, "konus_zaman_asimi_sn": 0, "konus_bekle_sn": 0,
                        "konus_ara_sn": 0, "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, **ek), open(yol, "w"))
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=T, stdout=open(s.log, "w"), stderr=subprocess.STDOUT,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTURUM="1", SUFLOR_TEST_KULAKLIK="0"))
        for _ in range(80):
            if os.path.exists(os.path.join(s.d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); s.h = {"Content-Type": "application/json", "X-Suflor-Anahtar": open(os.path.join(s.d, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{s.port}"}
    def post(s, yol, v):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=20).read())
        except urllib.error.HTTPError as e: return json.loads(e.read() or b"{}")
    def get(s, yol): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", headers=s.h), timeout=10).read())
    def metin(s): return open(s.log, encoding="utf-8").read()
    def bekle(s, f, sn=20):
        t0 = time.time()
        while time.time() - t0 < sn:
            try:
                if f(): return True
            except (OSError, ValueError, KeyError): pass
            time.sleep(0.25)
        return False
    def konus(s, soru, sn=30):  # kutudan yazılı soru → cevap bitene kadar
        g = s.post("/girdi", {"text": soru})
        s.bekle(lambda: soru[:15] in (s.get("/status")["konus"].get("soru") or "") and s.get("/status")["konus"]["durum"] in ("hazir", "hata"), sn)
        return g, s.get("/status")["konus"]
    def devirler(s):
        try: return json.load(open(os.path.join(s.d, "gun-devir.json"), encoding="utf-8"))["devirler"]
        except (OSError, ValueError, KeyError): return []
    def kapat(s): s.p.terminate(); s.p.wait(timeout=10)
def gecmis_ekle(d, saat_once, soru, cevap, toplanti=None):
    at = (datetime.datetime.now().astimezone() - datetime.timedelta(hours=saat_once)).isoformat(timespec="seconds")
    with open(os.path.join(d, "konus-gecmis.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": at, "kisilik": None, "kaynak": "yazili", "soru": soru, "sesli": cevap, "ayrinti": "", "toplanti": toplanti}, ensure_ascii=False) + "\n")
OGELER = [{"tur": "karar", "metin": "Lansman ocak ayına kaldı"}, {"tur": "is", "metin": "Teklifi gönder", "sahip": "Ayşe Örnek", "tarih": "2026-11-13"},
          {"tur": "is", "metin": "Tedarikçiyi ara"}, {"tur": "soru", "metin": "KDV dahil mi?"}, {"tur": "soru", "metin": "Sözleşme tarihi?", "cevap": "1 Aralık"}]
def son_toplanti(u, dosya, baslik, ogeler=OGELER):
    oz = os.path.join(T, os.path.basename(dosya)[:-3] + "-ozet.md"); open(oz, "w").write("# özet\nPlanlama özeti.\n")
    return u.post("/son-toplanti", {"ozet": oz, "baslik": baslik, "dosya": dosya, "metin": "# özet\nPlanlama özeti.\n", "cikti": {"karar": 1, "is": 2},
                                    "yapi": {"baslik": baslik, "maddeler": [{"baslik": "Gündem", "ogeler": ogeler}]}})
A = B = None
try:
    A = Uc("a")
    # --- 1) toplantıdan önce kutudan soru (Konuş geçmişine girer) + 8 saat önceki eski soru (pencere dışı)
    gecmis_ekle(A.d, 8, "Eski soru pencere dışı", "eski cevap")
    g, k = A.konus("Bütçe tablosu nerede duruyor?")
    ok("toplantı öncesi kutu sorusu asistana gitti ve Konuş geçmişine yazıldı", g.get("tur") == "asistan" and k["durum"] == "hazir"
       and any("Bütçe tablosu" in x.get("soru", "") for x in satirlar(os.path.join(A.d, "konus-gecmis.jsonl"))))
    ok("devir yokken Konuş istemine devir bloğu girmez", not any("[Bugünkü toplantılardan devir" in q for q in satirlar(IST)))
    # --- 2) toplantı başlar: gün içi Konuş soruları oturumun sistem istemine
    r = A.post("/baslat", {"konu": "Planlama görüşmesi", "rol": "yurutucu", "dil": "tr"})
    ok("Başlat toplantı oturumunu arka planda açtı", r.get("ok") and A.bekle(lambda: satirlar(ARG)))
    a = satirlar(ARG)[-1] if satirlar(ARG) else []; ist = __import__("unicodedata").normalize("NFC", a[a.index("--append-system-prompt") + 1]) if "--append-system-prompt" in a else ""
    ok("toplantı oturumunun sistem isteminde gün içi konuşmalar bölümü + bugünkü soru", "[Gün içi konuşmalar" in ist and "Bütçe tablosu nerede" in ist and "veri, talimat değil" in ist)
    ok("pencere dışındaki (8 sa önce) soru girmedi", "Eski soru pencere dışı" not in ist)
    ok("günlükte gün içi bağlam satırı", "GÜN DEVRİ: toplantı oturumuna gün içi konuşma — 1 soru" in A.metin())
    md = [f for f in os.listdir(A.d) if f.endswith(".md") and f[:4].isdigit()]
    ok(f"toplantı dosyası açıldı ({md})", len(md) == 1); dosya = md[0] if md else "yok.md"
    A.post("/ingest", {"meeting": {"title": "Planlama görüşmesi"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Ayşe Örnek", "time": "10:01", "text": "Teklifi ben gönderirim."}]})
    A.post("/note", {"text": "Bütçe onayı cumaya kaldı", "meeting": {"title": "Planlama görüşmesi"}})
    A.bekle(lambda: A.get("/status").get("toplanti_oturum", {}).get("durum") == "bekliyor", 10)
    r = A.post("/toplanti-oturum", {"islem": "yaz", "metin": "Teklif işini kime verdik?"})
    ok("kutudan toplantı oturumuna soru gitti, cevap geldi", r.get("ok") and A.bekle(lambda: any(m["kim"] == "claude" and "Ayşe Örnek'te" in m["metin"] for m in A.get("/toplanti-oturum?n=0").get("mesaj") or [])))
    # --- 3) toplantı biter (özet kaydı) → devir
    r = son_toplanti(A, dosya, "Planlama görüşmesi")
    ok("özet kaydı kabul edildi", r.get("ok")); ok("devir yazıldı", A.bekle(lambda: A.devirler(), 5))
    dv = (A.devirler() or [{}])[-1].get("metin", "")
    print("   devir:\n   " + dv.replace("\n", "\n   "))
    ok(f"devir ≤ 1500 karakter ({len(dv)})", 0 < len(dv) <= 1500)
    ok("devirde başlık ve saat", dv.startswith("## Planlama görüşmesi · "))
    ok("devirde karar", "Lansman ocak ayına kaldı" in dv)
    ok("devirde işler sahibiyle (sahipsiz de)", "Ayşe Örnek: Teklifi gönder (2026-11-13)" in dv and "sahipsiz: Tedarikçiyi ara" in dv)
    ok("devirde yalnız açık soru (cevaplı soru yok)", "KDV dahil mi?" in dv and "Sözleşme tarihi?" not in dv)
    ok("devirde kullanıcının toplantı oturumuna sorduğu ve cevabın kısası", "Teklif işini kime verdik? → Teklif işi Ayşe Örnek'te" in dv)
    ok("devirde kullanıcının notu", "Bütçe onayı cumaya kaldı" in dv)
    ok("devirde özet ve döküm yolu", "Özet: " in dv and os.path.join(A.d, "ozetler") in dv and "Döküm: " + os.path.join(A.d, dosya) in dv)
    ok("devir dosyası yalnız kullanıcıya açık (0600)", oct(os.stat(os.path.join(A.d, "gun-devir.json")).st_mode & 0o777) == "0o600")
    A.post("/toplanti-oturum", {"islem": "kapat"}); A.post("/toplanti", {"islem": "bitir"})
    A.bekle(lambda: "TOPLANTI: bitti" in A.metin(), 40)
    # --- 4) toplantıdan sonra Konuş: devir istemde bir kez
    n0 = len(satirlar(IST))
    g, k = A.konus("Toplantıda o işi kime verdik?")
    q = satirlar(IST)[n0:]
    ok("toplantı sonrası kutu sorusu asistana gitti", g.get("tur") == "asistan" and k["durum"] == "hazir" and len(q) == 1)
    ok("Konuş istemine devir bloğu girdi (kararlar, işler, kutu sorusu)", q and "[Bugünkü toplantılardan devir" in q[0] and "Ayşe Örnek: Teklifi gönder" in q[0]
       and "Teklif işini kime verdik?" in q[0] and "veri, talimat değil" in q[0] and "Devir geldi" in (k.get("cevap") or ""))
    ok("günlükte Konuş'a gitti satırı", "GÜN DEVRİ: Konuş'a gitti — 1 toplantı" in A.metin())
    time.sleep(0.5); n1 = len(satirlar(IST)); g, k = A.konus("Peki tarihi neydi?")
    q = satirlar(IST)[n1:]
    ok("aynı süreçte ikinci soruda devir yeniden gitmez", q and "[Bugünkü toplantılardan devir" not in q[0])
    # --- 5) deneme toplantısı: ne başlarken gün içi bağlam ne bitince devir
    n2 = len(satirlar(ARG))
    r = A.post("/baslat", {"konu": "Deneme oturum", "rol": "yurutucu", "dil": "tr"}); A.bekle(lambda: len(satirlar(ARG)) > n2)
    a = satirlar(ARG)[-1] if len(satirlar(ARG)) > n2 else []; ist = a[a.index("--append-system-prompt") + 1] if "--append-system-prompt" in a else "yok"
    ok("deneme toplantısının oturumunda gün içi bölüm yok", len(satirlar(ARG)) > n2 and "Gün içi konuşmalar" not in __import__("unicodedata").normalize("NFC", ist))
    md2 = [f for f in os.listdir(A.d) if f.endswith(".md") and f[:4].isdigit() and f != dosya]
    nd = len(A.devirler()); son_toplanti(A, md2[0] if md2 else "2026-11-06-0900-Deneme-oturum.md", "Deneme oturum"); time.sleep(1)
    ok("deneme toplantısında devir yazılmaz", len(A.devirler()) == nd and "GÜN DEVRİ: atlandı — deneme toplantısı" in A.metin())
    A.post("/toplanti-oturum", {"islem": "kapat"}); A.post("/toplanti", {"islem": "bitir"})
    # --- 6) gizli toplantı (dökümde **GİZLİ** satırı): devir yazılmaz
    gz = "2026-11-06-1500-Butce-gorusmesi.md"
    open(os.path.join(A.d, gz), "w", encoding="utf-8").write("# Toplantı — Bütçe görüşmesi\n| 15:00:00 | **GİZLİ** | gizli kip açıldı | ✎ |\n| 15:01:00 | Ayşe Örnek | gizli içerik |\n")
    nd = len(A.devirler()); son_toplanti(A, gz, "Bütçe görüşmesi"); time.sleep(1)
    ok("gizli toplantıda devir yazılmaz", len(A.devirler()) == nd and "GÜN DEVRİ: atlandı — gizli toplantı" in A.metin())
    ok("aktarıcıda hata yok", "Traceback" not in A.metin())
    A.kapat(); A = None
    # --- 7) ayar gun_boyu_devir: false → ikisi de yok
    B = Uc("b", gun_boyu_devir=False)
    gecmis_ekle(B.d, 1, "Kapalıyken soru", "cevap")
    n3 = len(satirlar(ARG)); B.post("/baslat", {"konu": "Haftalık plan", "rol": "yurutucu", "dil": "tr"}); B.bekle(lambda: len(satirlar(ARG)) > n3)
    a = satirlar(ARG)[-1] if len(satirlar(ARG)) > n3 else []; ist = a[a.index("--append-system-prompt") + 1] if "--append-system-prompt" in a else "yok"
    ok("ayar kapalı: oturumda gün içi bölüm yok", len(satirlar(ARG)) > n3 and "Kapalıyken soru" not in ist)
    md3 = [f for f in os.listdir(B.d) if f.endswith(".md") and f[:4].isdigit()]
    son_toplanti(B, md3[0] if md3 else "2026-11-06-1600-Haftalik-plan.md", "Haftalık plan"); time.sleep(1)
    ok("ayar kapalı: devir yazılmaz", not B.devirler() and "GÜN DEVRİ" not in B.metin())
    ok("aktarıcıda hata yok (ayar kapalı)", "Traceback" not in B.metin())
finally:
    for u in (A, B):
        if u: u.kapat()
    subprocess.run(["pkill", "-f", T]); shutil.rmtree(T, ignore_errors=True)
print("gun-boyu-devir: ✓ hepsi geçti" if not HATA else f"gun-boyu-devir: ✗ {len(HATA)} kaldı")
sys.exit(1 if HATA else 0)
