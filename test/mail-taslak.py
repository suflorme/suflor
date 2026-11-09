#!/usr/bin/env python3
# Asistan Mac Mail'e (ya da Gmail/Outlook web) e-posta TASLAĞI koyar, her seferinde tek tık onayıyla ve ASLA göndermeden (9 Kasım): cevaptaki
# [KAYIT: {"komut": "eposta_taslak", "arg": {kime, konu, govde}}] etiketi → aktarıcı doğrular → panoda onay kartı → Onayla → taslak penceresi.
# Sahte claude (kota yok); aktarıcı deneme kipinde (SUFLOR_TEST_BASLAT) taslağı açmaz, günlüğe "TASLAK (deneme): {json}" yazar. Kullanıcının gerçek Mail'ine yazılmaz.
# aktarici/notlar.py (eposta_taslak, taslak_*) değişince koştur:   PYTHONDONTWRITEBYTECODE=1 python3 test/mail-taslak.py      (kaldı → çıkış 1)
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.realpath(tempfile.mkdtemp(prefix="taslak-")); HATA = []; AT = chr(64); BEN = "kullanici.deneme" + AT + "firma.test"
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, re, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.strip().splitlines()[-1]
    c = ["Taslak hazır."] + [" Taslak kuralı geldi." if "[E-posta taslağı]" in q else " Taslak kuralı yok."]
    for e in re.findall(r"ETIKET:(\\{.*?\\})(?=\\s*ETIKET:|\\s*$)", soru):  # kutu girdisi kısa sınırlı: uzun gövde yer tutucudan burada üretilir
        e = e.replace("@@UZUN@@", "\\\\n".join("Bölüm %d: " % i + "Cilalı bir kitap özeti cümlesi. " * 6 for i in range(60))).replace("@@COKUZUN@@", "y" * 31000)
        c.append("\\n[KAYIT: " + e + "]")
    for p in c: time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": p}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
def E(**arg): return "ETIKET:" + json.dumps({"komut": "eposta_taslak", "arg": arg, "neden": "Kullanıcı istedi"}, ensure_ascii=False)
class Uc:
    def __init__(s, port, anahtar): s.port, s.h = port, {"X-Suflor-Anahtar": anahtar, "Origin": f"http://127.0.0.1:{port}"}
    def post(s, yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=20).read())
    def status(s): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}/status", headers=s.h), timeout=10).read())
    def kartlar(s): return [k for k in s.status().get("cards") or [] if k.get("izin") == "kayit" and k.get("status") == "acik"]
    def bekle(s, parca, sn=40):
        t0 = time.time()
        while time.time() - t0 < sn:
            k = s.status()["konus"]
            if parca in (k.get("soru") or "") and k["durum"] in ("hazir", "hata"): return k
            time.sleep(0.25)
        return s.status()["konus"]
    def cevap_bekle(s, parca, sn=10):
        t0 = time.time()
        while time.time() - t0 < sn:
            k = s.status()["konus"]
            if parca in (k.get("cevap") or ""): return k
            time.sleep(0.2)
        return s.status()["konus"]
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): sys.exit("atlandı: Brifing.app ya da swiftc yok")
APP = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, APP, symlinks=True)  # Konuş/kutu açık süreç kipi bu yardımcıyla çalışır (asistan-yazma.py ile aynı düzenek)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(APP, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", APP], capture_output=True)
def kos(ad, ek, govdeler):  # bir aktarıcı örneği: ad = alt klasör, ek = ayar eklemeleri
    t = os.path.join(T, ad); d = os.path.join(t, "canli"); os.makedirs(os.path.join(d, "ozetler")); os.makedirs(os.path.join(t, "proje")); port = bos_port(8793)
    for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), t)
    shutil.copytree(APP, os.path.join(t, "Suflor Brifing.app"), symlinks=True); shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(t, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(t, "pano"))
    yol = os.path.join(t, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": port, "uygulama": t, "proje": os.path.join(t, "proje"), "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_zaman_asimi_sn": 0,
        "konus_bekle_sn": 0, "konus_ara_sn": 0, "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok", **ek}, open(yol, "w"))
    P = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(port)], cwd=t, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_METIN="1"),
                         stdout=open(os.path.join(t, "relay.log"), "w"), stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); u = Uc(port, open(os.path.join(d, "kart-anahtari.txt")).read().strip())
        log = lambda: [json.loads(l) for l in [x.split("TASLAK (deneme): ", 1)[1] for x in open(os.path.join(t, "relay.log"), encoding="utf-8") if "TASLAK (deneme): " in x]]
        govdeler(u, log, d)
    finally: P.terminate(); P.wait(10)
def mac_mail(u, log, d):
    u.post("/girdi", {"text": "kitap özetini taslak yap " + E(kime="kendime", konu="Cilalı kitap özeti", govde="# Kitap\n\n**Ana fikir:** *vurgu*\n* madde bir\n* madde iki")}); k = u.bekle("kitap özetini")
    kr = u.kartlar()
    ok("e-posta konusu geçen turda istemde taslak kuralı var (asistan «yapamam» demez)", "Taslak kuralı geldi" in (k.get("cevap") or ""))
    ok("onay kartı açıldı: konu, alıcı (kendi adresi), uzunluk, Mail ve «Gönder sende»; etiket cevapta yok", len(kr) == 1 and "Cilalı kitap özeti" in kr[0]["text"] and BEN in kr[0]["text"] and "Mac Mail" in kr[0]["text"] and "Gönder sende" in kr[0]["text"] and "[KAYIT" not in (k.get("cevap") or ""))
    ok("onaydan önce taslak açılmadı", not log())
    u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); k = u.cevap_bekle("Yazıldı"); l = log()
    ok("Onayla → tek taslak, alıcı kendi adresi, tür mailto (Mac Mail), cevabın altında «Yazıldı»", len(l) == 1 and l[0]["kime"] == [BEN] and l[0]["tur"] == "mailto" and "✓ Yazıldı" in (k.get("cevap") or ""))
    ok("gövde düz metin (markdown süsü yok, madde korunur)", l and l[0]["govde"] == "KITAP\n\nAna fikir: vurgu\n- madde bir\n- madde iki")
    ok("hiçbir yerde gönderme komutu yok (kaynakta send/gönder uygulaması yok)", not re.search(r"\bsend_message|outlook_send|\bsend_draft|osascript|NSAppleScript|\bsmtplib", open(os.path.join(KOD, "aktarici", "notlar.py"), encoding="utf-8").read()))
    time.sleep(0.5); u.post("/girdi", {"text": "alıcısız taslak " + E(konu="Not", govde="Kısa not")}); u.bekle("alıcısız"); kr = u.kartlar()
    ok("alıcısız taslak kartı: «alıcısız»", len(kr) == 1 and "alıcısız" in kr[0]["text"])
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); u.cevap_bekle("Yazıldı"); time.sleep(0.3)
    ok("alıcısız taslak açıldı (kime boş)", len(log()) == 2 and log()[1]["kime"] == [])
    time.sleep(0.5); u.post("/girdi", {"text": "reddedilecek " + E(kime="kendime", konu="Reddet", govde="metin metin")}); u.bekle("reddedilecek"); kr = u.kartlar()
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "reddedildi"}); k = u.cevap_bekle("Yazılmadı")
    ok("Reddet → taslak açılmadı", len(log()) == 2 and "Yazılmadı" in (k.get("cevap") or ""))
    time.sleep(0.5); u.post("/girdi", {"text": "kötü taslaklar " + " ".join([E(kime="Ali Veli", konu="x", govde="yy"), E(kime="a" + AT + "b.test\nBcc: z" + AT + "z.test", konu="x", govde="yy"), E(kime="", konu="", govde="yy"),
                                                                               E(konu="x", govde="@@COKUZUN@@"), E(kime="", konu="x", govde="yy", ek="1"), E(kime=",".join(f"u{i}" + AT + "f.test" for i in range(6)), konu="x", govde="yy")])})
    k = u.bekle("kötü taslaklar")
    ok("geçersiz alıcı (ad), başlık sokma, boş konu, aşırı uzun gövde, ek argüman, çok alıcı: kart yok, hepsi cevapta «sunulmadı»", not u.kartlar() and (k.get("cevap") or "").count("sunulmadı") == 6)
    time.sleep(0.5); u.post("/girdi", {"text": "gizli öncesi taslak " + E(kime="kendime", konu="Gizli", govde="metin metin")}); u.bekle("gizli öncesi"); kr = u.kartlar()
    u.post("/komut", {"tur": "gizli"}); time.sleep(0.3)
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"})
    time.sleep(1.5)
    ok("gizli kip açıldıktan sonra onay gelse de taslak açılmaz", len(kr) == 1 and len(log()) == 2)
    u.post("/komut", {"tur": "gizli"})
    # uzun gövde (kitap özeti ~ 12 bin karakter) Mac Mail'de sınırsız
    uzun = "\n".join(f"Bölüm {i}: " + "Cilalı bir kitap özeti cümlesi. " * 6 for i in range(60)); time.sleep(0.5)
    u.post("/girdi", {"text": "uzun özet " + E(kime="kendime", konu="Uzun", govde="@@UZUN@@")}); u.bekle("uzun özet"); kr = u.kartlar()
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); u.cevap_bekle("Yazıldı"); time.sleep(0.3)
    ok(f"uzun gövde ({len(uzun)} karakter) tam gider", len(log()) == 3 and len(log()[2]["govde"]) >= len(uzun) - 5)
def mac_mail_kendi_adres_yok(u, log, d):
    u.post("/girdi", {"text": "kendime taslak " + E(kime="kendime", konu="x", govde="yy")}); k = u.bekle("kendime taslak")
    ok("kendi adres kayıtlı değilse «kendime» reddedilir, kart yok", not u.kartlar() and "eposta_adres" in (k.get("cevap") or ""))
def gmail(u, log, d):
    u.post("/girdi", {"text": "gmail taslağı " + E(kime="kendime", konu="Gmail", govde="@@UZUN@@")}); u.bekle("gmail taslağı"); kr = u.kartlar()
    ok("Gmail türünde kart «Gmail» der", len(kr) == 1 and "Gmail" in kr[0]["text"])
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); k = u.cevap_bekle("Yazıldı")
    l = log(); ok("Gmail türü: taslak tür gmail, alıcı kendi adresi", len(l) == 1 and l[0]["tur"] == "gmail" and l[0]["kime"] == [BEN])
kos("mac", {"eposta": "mailto", "eposta_adres": BEN}, mac_mail)
kos("adressiz", {"eposta": "mailto"}, mac_mail_kendi_adres_yok)
kos("gmail", {"eposta": "gmail", "eposta_adres": BEN}, gmail)
if not os.environ.get("KORU"): shutil.rmtree(T, ignore_errors=True)
else: print(T)
print("TAMAM" if not HATA else f"KALDI: {len(HATA)}"); sys.exit(1 if HATA else 0)
