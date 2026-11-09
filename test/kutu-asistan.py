#!/usr/bin/env python3
# Panodaki kutuya yazılan HER ŞEY asistana gider (5 Kasım): toplantı oturumu izlemiyorken /girdi → Konuş asistanına yazılı soru (başta "?" ya da "not:" şart değil);
# not mu soru mu talimat mı ayrımını asistan yapar: cevabın sonundaki [NOT: …] ve [SÖZLÜK: yanlış => doğru] etiketlerini aktarıcı ayıklar ve işi yapar (Notlar defteri, sözlük);
# asistan hiç çalışamazsa yazı Notlar'da kalır ve panoda söylenir. Sahte "claude" (kota yok), Brifing.app açık süreç kipi (swiftc ile derlenir); Whisper gerekmez.
# aktarici/bas-konus.py (konus_yazili, KUTU_KURAL, _konus_kur), aktarici/notlar.py (kutu_*) ya da relay.py /girdi değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kutu-asistan.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8792)
T = tempfile.mkdtemp(prefix="kutu-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
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
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, re, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; kural = "tek kutudan geldi" in q; soru = q.strip().splitlines()[-1]
    if "yavaş" in soru: time.sleep(3)
    if "değil" in soru: c = ["Tamam, sözlüğe ekledim: Mira Kalem → Mira Kalın.", "\\n[SÖZLÜK: Mira Kalem => Mira Kalın]"]
    elif "hatırlat" in soru: c = ["Not aldım.", " [NOT: yarın Ali'yi ara]"]
    elif "kötü" in soru: c = ["Tamam.", "\\n[SÖZLÜK: bu çok uzun bir yanlış yazılış yani dört sözcükten fazla => Doğru]"]
    else: c = ["Sorduğun: " + soru.rstrip("?.") + "."]
    c.append(" Kural geldi." if kural else " Kural yok.")
    if "cevabın ilk kısmı sesli okunur" in q: c.append(" Sesli tur.")
    if "hoparlör düğmesini" in q: c.append(" Düğme ipucu var.")
    if "ayrıntılı" in soru: c.append("\\n---\\nYazılı ayrıntı burada.")
    for p in c: time.sleep(0.1); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": p}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
os.makedirs(os.path.join(T, "bin2")); bozuk = os.path.join(T, "bin2", "claude"); open(bozuk, "w").write("#!/bin/sh\nexit 1\n"); os.chmod(bozuk, 0o755)  # açılır açılmaz çıkan claude: asistan çalışamıyor
def ayar(ad, **ek):
    yol = os.path.join(T, ad + ".json"); json.dump(dict({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor",
        "claude": sahte, "konus_zaman_asimi_sn": 0, "konus_bekle_sn": 0, "konus_ara_sn": 0, "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, **ek), open(yol, "w")); return yol
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
def baslat(ad, port, ayar_yolu):
    d = os.path.join(T, ad); os.makedirs(d)
    p = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(port)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar_yolu, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
                         stdout=open(os.path.join(T, ad + ".log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); return p, d, open(os.path.join(d, "kart-anahtari.txt")).read().strip()
class Uc:
    def __init__(s, port, anahtar): s.port, s.h = port, {"X-Suflor-Anahtar": anahtar, "Origin": f"http://127.0.0.1:{port}"}
    def post(s, yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=20).read())
    def status(s): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}/status", headers=s.h), timeout=10).read())
    def bekle(s, soru_parca, sn=40):
        t0 = time.time()
        while time.time() - t0 < sn:
            k = s.status()["konus"]
            if soru_parca in (k.get("soru") or "") and k["durum"] in ("hazir", "hata"): return k
            time.sleep(0.25)
        return s.status()["konus"]
def jsonl(d, ad):
    try: return [json.loads(l) for l in open(os.path.join(d, ad), encoding="utf-8")]
    except OSError: return []
r1 = r2 = None
try:
    # 1) sahte claude var: toplantı yok, oturum yok
    P1 = PORT; r1, d1, k1 = baslat("canli1", P1, ayar("ayar1")); u = Uc(P1, k1); log1 = lambda: open(os.path.join(T, "canli1.log"), encoding="utf-8").read()
    g = u.post("/girdi", {"text": "Son toplantıda sahipsiz kalan işler neler"}); k = u.bekle("sahipsiz")
    ok("soru işareti olmadan yazılan soru asistana gider, cevap panoda yazılı", g.get("tur") == "asistan" and k["durum"] == "hazir" and "Son toplantıda sahipsiz kalan işler neler" in (k.get("cevap") or ""))
    ok("kutu kuralı (not/soru/talimat ayrımı) isteme eklendi", "Kural geldi" in (k.get("cevap") or ""))
    ok("yazıyla gelen soru okunmaz, Notlar'a düşmedi, döküm açılmadı", "SES (deneme)" not in log1() and not jsonl(d1, "notlar.jsonl") and not [f for f in os.listdir(d1) if f.endswith(".md")])
    time.sleep(0.5); g = u.post("/girdi", {"text": "Mira Kalem değil Mira Kalın olarak düzelt"}); k = u.bekle("Mira Kalem")
    soz = json.load(open(os.path.join(d1, "sozluk.json"), encoding="utf-8")).get("terimler", []) if os.path.exists(os.path.join(d1, "sozluk.json")) else []
    ok("düzeltme talimatı: [SÖZLÜK] etiketi sözlüğe kullanıcı terimi olarak eklendi", any(t.get("dogru") == "Mira Kalın" and "Mira Kalem" in t.get("yanlis", []) and t.get("kaynak") == "kullanici" for t in soz))
    ok("etiket panoda görünmez, asistanın cevabı durur; Notlar'a not olarak düşmedi", k["durum"] == "hazir" and "[SÖZLÜK" not in (k.get("cevap") or "") and "sözlüğe ekledim" in (k.get("cevap") or "") and not jsonl(d1, "notlar.jsonl"))
    time.sleep(0.5); g = u.post("/girdi", {"text": "yarın Ali'yi ara hatırlat"}); k = u.bekle("hatırlat")
    n_ = jsonl(d1, "notlar.jsonl")
    ok("not niteliğindeki yazı: asistan [NOT] ile kaydeder → Notlar defteri; etiket görünmez", len(n_) == 1 and n_[0]["metin"] == "yarın Ali'yi ara" and "[NOT" not in (k.get("cevap") or "") and "Not aldım" in (k.get("cevap") or ""))
    ok("/status notlar listesinde", [x["metin"] for x in u.status().get("notlar") or []] == ["yarın Ali'yi ara"])
    time.sleep(0.5); u.post("/girdi", {"text": "kötü bir düzeltme"}); k = u.bekle("kötü")
    ok("uygun olmayan sözlük etiketi eklenmez, cevapta açıkça söylenir", "Sözlüğe eklenemedi" in (k.get("cevap") or "") and len(json.load(open(os.path.join(d1, "sozluk.json"), encoding="utf-8"))["terimler"]) == len(soz))
    # meşgulken ikinci yazı kaybolmaz
    time.sleep(0.5); u.post("/girdi", {"text": "yavaş bir soru"}); g2 = u.post("/girdi", {"text": "ikinci yazı hemen"}); u.bekle("yavaş")
    ok("asistan meşgulken ikinci yazı Notlar'a yedeklenir (yedek: true, tur defter)", g2.get("yedek") is True and g2.get("tur") == "defter" and any(x["metin"] == "ikinci yazı hemen" for x in jsonl(d1, "notlar.jsonl")))
    time.sleep(0.5); g3 = u.post("/girdi", {"text": "https://ornek.example/rapor"})
    ok("yalnız bağlantı: bağlam kaynağı, asistana gitmez", g3.get("tur") == "bağlam")
    time.sleep(0.5); g4 = u.post("/girdi", {"text": "? kaç kişiydik"}); k = u.bekle("kaç kişiydik")
    ok("başta ? hâlâ doğrudan soru (kural eklenmez: not sayılmaz)", g4.get("tur") == "asistan" and "Kural yok" in (k.get("cevap") or ""))
    # v0.214: kutudaki sesli cevap düğmesi (/girdi sesli:true)
    ses_n = lambda: log1().count("SES (deneme)")
    time.sleep(0.5); n0 = ses_n(); u.post("/girdi", {"text": "sesli konuş dostum"}); k = u.bekle("sesli konuş"); time.sleep(0.5)
    ok("sesli kapalıyken yazılı tur okunmaz; istem düğmeyi işaret eder (kendiliğinden açmaz)", "Düğme ipucu var" in (k.get("cevap") or "") and "Sesli tur" not in (k.get("cevap") or "") and ses_n() == n0)
    time.sleep(0.5); n0 = ses_n(); u.post("/girdi", {"text": "hangi işler açık ayrıntılı", "sesli": True}); k = u.bekle("ayrıntılı"); time.sleep(1.0)
    l1 = log1(); gecen = l1[l1.rfind("KONUŞ: kutu sorusu sesli cevapla"):] if "kutu sorusu sesli cevapla" in l1 else ""
    ok("sesli:true: cevap okuma kuyruğuna gider, istem sesli turu söyler (yazılı kural değil)", ses_n() > n0 and "Sesli tur" in (k.get("cevap") or "") and "Düğme ipucu" not in (k.get("cevap") or ""))
    ok("sesli turda --- sonrası yazılı ayrıntı okunmaz ama panoda görünür", "Yazılı ayrıntı burada" not in gecen and "Yazılı ayrıntı burada" in (k.get("cevap") or ""))
    time.sleep(0.5); n0 = ses_n(); u.post("/girdi", {"text": "yarın Ali'yi ara hatırlat", "sesli": True}); k = u.bekle("hatırlat"); time.sleep(1.0)
    l1 = log1(); gecen = l1[l1.rfind("KONUŞ: kutu sorusu sesli cevapla"):]
    ok("sesli turda [NOT: …] etiketi okunmaz, iş yine yapılır", "[NOT" not in gecen.split("SES (deneme)", 1)[-1] and ses_n() > n0 and any(x["metin"] == "yarın Ali'yi ara" for x in jsonl(d1, "notlar.jsonl")))
    time.sleep(0.5); n0 = ses_n(); u.post("/girdi", {"text": "sesli:false deneme sorusu", "sesli": False}); k = u.bekle("sesli:false"); time.sleep(0.5)
    ok("sesli:false açıkça: okunmaz", ses_n() == n0 and "Sesli tur" not in (k.get("cevap") or ""))
    ok("aktarıcıda hata yok (asistan açık)", "Traceback" not in log1())
    # 2) asistan hiç çalışamıyor (claude yok): yazı not olarak kalır ve panoda söylenir
    P2 = bos_port(PORT + 5); r2, d2, k2 = baslat("canli2", P2, ayar("ayar2", claude=bozuk, port=P2)); u2 = Uc(P2, k2)
    g = u2.post("/girdi", {"text": "Ümit Mut şeklinde formal yaz"}); k = u2.bekle("Ümit Mut")
    ok("asistan çalışamazsa: durum hata, panoda yazının not olarak kaydedildiği söylenir", k["durum"] == "hata" and "not olarak kaydedildi" in (k.get("hata") or ""))
    ok("yazı Notlar defterinde kaldı", [x["metin"] for x in jsonl(d2, "notlar.jsonl")] == ["Ümit Mut şeklinde formal yaz"])
    ok("aktarıcıda hata yok (asistan yok)", "Traceback" not in open(os.path.join(T, "canli2.log"), encoding="utf-8").read())
finally:
    for p in (r1, r2):
        if p: p.terminate(); p.wait()
    subprocess.run(["pkill", "-f", T]); shutil.rmtree(T, ignore_errors=True)
print("kutu-asistan: ✓ hepsi geçti" if not HATA else f"kutu-asistan: ✗ {len(HATA)} kaldı")
sys.exit(1 if HATA else 0)
