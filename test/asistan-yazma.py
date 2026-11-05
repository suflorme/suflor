#!/usr/bin/env python3
# Asistan kayıt yazar, her yazmada kullanıcının tek tık onayıyla (5 Kasım): asistan (kutu ya da Konuş) cevabın sonuna [KAYIT: {"komut", "arg", "neden"}] koyar;
# aktarıcı izin listesinden doğrular, panoda onay kartı açar; Onayla → aktarıcı yazar ve sonuç cevabın altına düşer; Reddet → yazılmaz.
# İzin listesi dışı komut/argüman/kimlik/özet adı → kart açılmaz; gizli kipte yazılmaz; turda en çok 5 öneri; aynı öneri yeniden sorulmaz; sesli cevapta etiket okunmaz.
# Sahte "claude" (kota yok), Brifing.app açık süreç kipi (swiftc ile derlenir). aktarici/notlar.py (kayit_*), bas-konus.py (KAYIT_*) değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/asistan-yazma.py      (kaldı → çıkış 1)
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8793)
T = tempfile.mkdtemp(prefix="yazma-"); proje = os.path.join(T, "proje"); os.makedirs(proje); d = os.path.join(T, "canli"); os.makedirs(os.path.join(d, "ozetler"))
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
# Sahte claude: sorudaki "ETIKET:<json>" parçalarını [KAYIT: <json>] olarak cevabın sonuna koyar; istemde blok ve kural geldiyse söyler.
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, re, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.strip().splitlines()[-1]
    c = ["Onayına sundum."]
    c += [" Kural geldi." if "[Kayıt yazma]" in q else " Kural yok.", " Blok geldi." if "k1 · karar · teyit bekliyor" in q else " Blok yok."]
    c += [" Gizli sızdı." if "Gizli karar" in q else "", " Sonuç geldi." if "[Önerdiğin kayıtların sonucu" in q else ""]
    for e in re.findall(r"ETIKET:(\\{.*?\\})(?=\\s*ETIKET:|\\s*$)", soru): c.append("\\n[KAYIT: " + e + "]")
    for p in c: time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": p}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglam.py", "whisper-isci.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
# kayıtlar: açık toplantı A (k1 teyit bekliyor, k2 onaylı, s3 açık iş, q4 açık soru) ve gizli toplantı G (k5)
sys.path.insert(0, T); import yapi
A_, G_ = "2026-11-04-1000-Deneme-Toplantisi", "2026-11-04-1500-Gizli-Toplanti"
c = yapi._db(d)
with c:
    for i, (top, tur, metin, sahip, durum) in enumerate([(A_, "karar", "Bütçe onaylandı (teyit bekliyor — örtük kabul)", None, "acik"), (A_, "karar", "Lansman ertelendi", None, "acik"),
                                                         (A_, "is", "Raporu hazırla", "Deniz T", "acik"), (A_, "soru", "Fiyat ne olacak?", None, "acik"), (G_ + ".md", "karar", "Gizli karar metni", None, "acik")], 1):
        c.execute("INSERT INTO kayit (id, toplanti, baslik, tarih, tur, sahip, metin, durum) VALUES (?,?,?,?,?,?,?,?)", (i, top if top.endswith(".md") else top + ".md", "Deneme toplantısı", "2026-11-04", tur, sahip, metin, durum))
c.close()
kopya = os.path.join(d, "ozetler", "deneme-ozeti.md"); open(kopya, "w", encoding="utf-8").write("# Deneme\n\nKararlar: Bütçe 120 bin TL olarak onaylandı.\n")
asil = os.path.join(T, "baska", "deneme-ozeti.md"); os.makedirs(os.path.dirname(asil)); open(asil, "w", encoding="utf-8").write("asıl dosya: Bütçe 120 bin TL\n")
open(os.path.join(d, "son-toplantilar.jsonl"), "w", encoding="utf-8").write(
    json.dumps({"id": "s1", "at": "2026-11-04T11:00:00", "dosya": A_ + ".md", "baslik": "Deneme toplantısı", "ozet": asil, "kopya": kopya}) + "\n" +
    json.dumps({"id": "s2", "at": "2026-11-04T16:00:00", "dosya": G_ + ".md", "baslik": "Gizli", "ozet": kopya, "kopya": kopya, "gizli": True}) + "\n")
yol = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor",
    "claude": sahte, "konus_zaman_asimi_sn": 0, "konus_bekle_sn": 0, "konus_ara_sn": 0, "konus_on_ac": False, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, open(yol, "w"))
P = None
def db(sql): c = sqlite3.connect(os.path.join(d, "karar-grafi.sqlite")); r = c.execute(sql).fetchall(); c.close(); return r
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
def E(_k, **arg): return "ETIKET:" + json.dumps({"komut": _k, "arg": arg, "neden": "Kullanıcı istedi"}, ensure_ascii=False)
try:
    P = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_METIN="1"),
                         stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); u = Uc(PORT, open(os.path.join(d, "kart-anahtari.txt")).read().strip()); log = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    # 1) kutu: kararı onayla → kart → Onayla → yazılır
    u.post("/girdi", {"text": "k1 kararını onayla " + E("karar_onayla", id="k1")}); k = u.bekle("k1 kararını")
    kr = u.kartlar()
    if os.environ.get("HATA_AYIKLA"): print(k, "\n", log()[-3000:])
    ok("istemde kayıt kuralı ve kimlikli kayıt bloğu var; gizli toplantının kaydı blokta yok", "Kural geldi" in (k.get("cevap") or "") and "Blok geldi" in k.get("cevap", "") and "Gizli sızdı" not in k.get("cevap", ""))
    ok("öneri panoda tek onay kartı açtı (metinde neden ve ne yazılacağı); etiket cevapta görünmez", len(kr) == 1 and "Kayda yazayım mı?" in kr[0]["text"] and "Kullanıcı istedi" in kr[0]["text"] and "Bütçe onaylandı" in kr[0]["text"]
       and "[KAYIT" not in k.get("cevap", "") and "Onayını bekliyor: 1" in k.get("cevap", ""))
    ok("onaydan önce yazılmadı", "teyit bekliyor" in db("SELECT metin FROM kayit WHERE id = 1")[0][0])
    u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); k = u.cevap_bekle("Yazıldı")
    ok("Onayla → karar onaylandı (teyit eki kalktı), cevabın altına «Yazıldı» düştü", db("SELECT metin FROM kayit WHERE id = 1")[0][0] == "Bütçe onaylandı" and "✓ Yazıldı" in (k.get("cevap") or ""))
    # 2) Konuş (bas): iş yapıldı → Reddet → yazılmaz; sonraki turda asistana sonuç bildirilir; sesli okunan kısımda etiket yok
    time.sleep(0.5); u.post("/bas-konus", {"metin": "s3 işini yapıldı işaretle " + E("is_durum", id="s3", durum="yapildi")}); k = u.bekle("s3 işini")
    kr = u.kartlar()
    ok("Konuş turunda da kart açıldı; sesli okunan metinde etiket yok", len(kr) == 1 and "Raporu hazırla" in kr[0]["text"] and not any("KAYIT" in l and "SES" in l for l in log().splitlines()))
    u.post("/card-ack", {"id": kr[0]["id"], "status": "reddedildi"}); k = u.cevap_bekle("Yazılmadı")
    ok("Reddet → iş açık kaldı, cevapta «Yazılmadı (reddettin)»", db("SELECT durum FROM kayit WHERE id = 3")[0][0] == "acik" and "reddettin" in (k.get("cevap") or ""))
    time.sleep(0.5); u.post("/girdi", {"text": "teşekkürler"}); k = u.bekle("teşekkürler")
    ok("sonraki turda asistana önceki önerinin sonucu gider", "Sonuç geldi" in (k.get("cevap") or ""))
    time.sleep(0.5); u.post("/bas-konus", {"metin": "bugün hava nasıl"}); k = u.bekle("hava nasıl")
    ok("kayıt konusu geçmeyen Konuş turunda kural ve blok eklenmez", "Kural yok" in (k.get("cevap") or "") and "Blok yok" in k.get("cevap", ""))
    # 3) aynı öneri yeniden sorulmaz
    time.sleep(0.5); u.post("/girdi", {"text": "yine s3 işini yapıldı işaretle " + E("is_durum", id="s3", durum="yapildi")}); k = u.bekle("yine s3")
    ok("aynı öneri yarım saat içinde yeniden sorulmaz (kart yok, cevapta söylenir)", not u.kartlar() and "az önce soruldu" in (k.get("cevap") or ""))
    # 4) izin listesi dışı: komut, ek argüman, gizli toplantının kaydı, yol kaçışı, biçim bozuk → kart yok
    time.sleep(0.5)
    u.post("/girdi", {"text": "kötü öneriler kaydı " + " ".join([E("dosya_sil", yol="/etc/hosts"), E("karar_onayla", id="k1", komut="rm -rf"), E("karar_duzelt", id="k5", metin="sızdır"),
                                                        E("ozet_duzelt", ozet="../../../etc/passwd", eski="a", yeni="b"), E("is_durum", id="s3; rm", durum="yapildi"), E("is_ekle", metin=["liste"])]) + " ETIKET:{bozuk}"})
    k = u.bekle("kötü öneriler")
    ok("izin listesi dışı komut/argüman/kimlik/yol: kart açılmadı, her biri cevapta «sunulmadı»", not u.kartlar() and (k.get("cevap") or "").count("sunulmadı") == 6 and "anlaşılmadı" in k.get("cevap", ""))
    ok("gizli toplantının kararı değişmedi", db("SELECT metin FROM kayit WHERE id = 5")[0][0] == "Gizli karar metni")
    # 5) özet düzeltmesi: panodaki kopya; asıl dosya izinli özet klasörü dışında → dokunulmaz
    time.sleep(0.5); u.post("/girdi", {"text": "özette tutarı düzelt " + E("ozet_duzelt", ozet=A_, eski="120 bin TL", yeni="125 bin TL")}); k = u.bekle("tutarı düzelt")
    kr = u.kartlar(); ok("özet düzeltme kartı", len(kr) == 1 and "120 bin TL" in kr[0]["text"] and "125 bin TL" in kr[0]["text"])
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"}); k = u.cevap_bekle("Yazıldı")
    ok("Onayla → panodaki kopya düzeldi; izinli klasör dışındaki asıl dosyaya dokunulmadı ve söylendi", "125 bin TL" in open(kopya, encoding="utf-8").read() and "120 bin TL" in open(asil, encoding="utf-8").read() and "yalnız panodaki kopya" in (k.get("cevap") or ""))
    # 6) iş ekleme + karar düzeltme + soru kapatma birlikte; tur başı sınır (7 öneri → 5 kart)
    time.sleep(0.5)
    et = [E("is_ekle", metin="Teklifi gönder", kim="Ali", tarih="2026-11-10", toplanti=A_), E("karar_duzelt", id="k2", metin="Lansman bir ay ertelendi"), E("soru_kapat", id="q4")] + \
         [E("is_ekle", metin=f"Ek iş {i}") for i in range(4)]
    u.post("/girdi", {"text": "toplu kayıt " + " ".join(et)}); k = u.bekle("toplu kayıt"); kr = u.kartlar()
    ok("turda en çok 5 öneri sunulur, kalanı için cevapta not", len(kr) == 5 and "en çok 5" in (k.get("cevap") or ""))
    for x in kr[:3]: u.post("/card-ack", {"id": x["id"], "status": "onaylandi"})
    for x in kr[3:]: u.post("/card-ack", {"id": x["id"], "status": "reddedildi"})
    time.sleep(1.5)
    ok("onaylanan üçü yazıldı (yeni iş sahip/vade/toplantıyla, karar metni, soru kapandı), reddedilen ikisi yok",
       db("SELECT sahip, son_tarih, toplanti FROM kayit WHERE metin = 'Teklifi gönder'") == [("Ali", "2026-11-10", A_ + ".md")] and db("SELECT metin FROM kayit WHERE id = 2")[0][0] == "Lansman bir ay ertelendi"
       and db("SELECT durum FROM kayit WHERE id = 4")[0][0] == "cevaplandi" and not db("SELECT id FROM kayit WHERE metin LIKE 'Ek iş%'"))
    # 7) gizli kip: onay beklerken gizli açılırsa yazılmaz; gizli kipte kutu asistana gitmez
    time.sleep(0.5); u.post("/girdi", {"text": "lansmanı onayla kaydı " + E("karar_duzelt", id="k2", metin="Lansman iptal")}); u.bekle("lansmanı onayla"); kr = u.kartlar()
    u.post("/komut", {"tur": "gizli"}); time.sleep(0.3)
    if kr: u.post("/card-ack", {"id": kr[0]["id"], "status": "onaylandi"})
    time.sleep(1.5)
    ok("gizli kip açıldıktan sonra onay gelse de yazılmaz", len(kr) == 1 and db("SELECT metin FROM kayit WHERE id = 2")[0][0] == "Lansman bir ay ertelendi")
    g = u.post("/girdi", {"text": "gizlide kayıt " + E("karar_duzelt", id="k2", metin="x")})
    ok("gizli kipte kutu yazısı reddedilir (asistana gitmez)", g.get("gizli") is True)
    u.post("/komut", {"tur": "gizli"})
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    if P: P.terminate(); P.wait()
    subprocess.run(["pkill", "-f", T]); shutil.rmtree(T, ignore_errors=True)
print("asistan-yazma: ✓ hepsi geçti" if not HATA else f"asistan-yazma: ✗ {len(HATA)} kaldı")
sys.exit(1 if HATA else 0)
