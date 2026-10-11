# Faz 4 — sesli özet ve "yazayım mı?" dizisi (yalıtılmış aktarıcı; SUFLOR_TEST_BASLAT: ses çalınmaz, okunacak metin günlüğe yazılır).
# Aktarıcıda seslendir / ozet_sesli / soru_* / eylem_sun / eylem_karar ya da panodaki Sonra/Sus değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli.py
import shutil, json, os, sys, subprocess, tempfile, time, urllib.request, urllib.error
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8795
T = tempfile.mkdtemp(prefix="yaz-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": os.path.join(T, "yok")}, open(ay, "w"))
for f in ("relay.py", "manifest.json"): subprocess.run(["cp", os.path.join(KOD, f), T])
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
subprocess.run(["cp", "-R", os.path.join(KOD, "pano"), T]); open(os.path.join(T, "ozet.md"), "w").write("# özet\n")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=ENV, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(yol, v, pano=False):
        h = {"X-Suflor-Anahtar": K, "Content-Type": "application/json"}
        if pano: h["Origin"] = f"http://127.0.0.1:{PORT}"
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=h), timeout=10).read())
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    log = lambda: open(os.path.join(T, "relay.log")).read()
    ids = [post("/eylem", {"tur": t, "baslik": b, "kim": k})["eylem"]["id"] for t, b, k in
           [("kayit", "Karar: erişim listesi cuma güncellenir", None), ("takip", "Deniz — takip e-postası", "Deniz"), ("mesaj", "Ekibe toplantı notu", None)]]
    post("/son-toplanti", {"ozet": os.path.join(T, "ozet.md"), "baslik": "Deneme", "puan": "4", "degerlendirme": "Karar çıktı; **süre** aşıldı", "oneri": "Gündemi kısalt"})
    time.sleep(0.5); L = log()
    ok("özet sesli okundu (not, değerlendirme, öneri, bekleyen sayısı)", "Toplantı özeti hazır. Not: beş üzerinden 4. Karar çıktı; süre aşıldı. Öneri: Gündemi kısalt." in L and "3 iş var" in L)
    post("/eylem-sun", {}); time.sleep(0.5)
    ok("sun → ilk iş soruldu", "Kayıt: Karar: erişim listesi cuma güncellenir. Yazayım mı?" in log() and st()["eylem"]["sesli"] == ids[0])
    post("/eylem-karar", {"id": ids[0], "durum": "onaylandi"}, pano=True); time.sleep(0.5)
    ok("Onayla → ikinci iş soruldu", "Takip e-postası: Deniz — takip e-postası. Kişi: Deniz. Taslak olarak yazayım mı?" in log() and st()["eylem"]["sesli"] == ids[1])
    post("/eylem-sesli", {"komut": "sonra"}, pano=True); time.sleep(0.5)
    ok("Sonra → üçüncü iş, ikinci bekliyor", st()["eylem"]["sesli"] == ids[2] and "Metni hazırlayayım mı?" in log()
       and next(x for x in st()["eylem"]["liste"] if x["id"] == ids[1])["durum"] == "bekliyor")
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/eylem-sesli", data=b'{"komut":"sus"}', headers={"X-Suflor-Anahtar": K})); kod = 200
    except urllib.error.HTTPError as e: kod = e.code
    ok("Sonra/Sus yalnız panodan (pano kökeni yoksa 403)", kod == 403)
    post("/eylem-sesli", {"komut": "sus"}, pano=True); time.sleep(0.3)
    ok("Sus → dizi bitti", st()["eylem"]["sesli"] is None and "dizisi bitti (sus)" in log())
    # hepsini onayla diziyi bitirir
    i4 = post("/eylem", {"tur": "belge", "baslik": "Not belgesi"})["eylem"]["id"]; post("/eylem-sun", {}); time.sleep(0.3)
    post("/eylem-karar", {"id": "hepsi", "durum": "onaylandi"}, pano=True); time.sleep(0.3)
    ok("Hepsini onayla → dizi bitti", st()["eylem"]["sesli"] is None and "dizisi bitti (hepsi)" in log())
    # toplantı sürerken okunmaz
    n0 = log().count("SES (deneme)")
    post("/ping", {"meeting": {"title": "Deneme"}, "call": True, "panel": True, "rows": 1})
    post("/eylem", {"tur": "kayit", "baslik": "Toplantıda eklenen"}); post("/eylem-sun", {})
    post("/son-toplanti", {"ozet": os.path.join(T, "ozet.md"), "baslik": "Deneme", "puan": "3", "degerlendirme": "x"}); time.sleep(0.5)
    ok("toplantı sürerken hiçbir şey okunmadı", log().count("SES (deneme)") == n0)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait()
# S24 Aşama 1: sesli cevap ayırıcısı (aktarıcının kendi tanımları; Whisper'ın verdiği biçimler — noktalama, büyük harf, İ/I)
import ast
_k = "".join(open(f, encoding="utf-8").read() for f in [os.path.join(KOD, "relay.py")] + sorted(__import__("glob").glob(os.path.join(KOD, "aktarici", "*.py")))); _ad = {"SES_CEVAP", "SES_AMA", "SES_DOLGU", "sesli_ayir"}
_ns = {"re": __import__("re")}
exec(compile(ast.Module([n for n in ast.parse(_k).body if (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in _ad for x in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name in _ad)], []), "relay", "exec"), _ns)
TABLO = [("Evet.", "onay"), ("Evet, yaz.", "onay"), ("Tamam.", "onay"), ("Olur olur.", "onay"), ("Ekle lütfen.", "onay"), ("EVET", "onay"), ("Yes.", "onay"), ("Okay, do it.", "onay"),
         ("Hayır.", "red"), ("Hayır, gerek yok.", "red"), ("Yazma.", "red"), ("No thanks.", "red"), ("İptal.", "red"),
         ("Sonra.", "sonra"), ("Atla.", "sonra"), ("Daha sonra.", "sonra"), ("Later.", "sonra"),
         ("Sus.", "sus"), ("Dur.", "sus"), ("Yeter.", "sus"), ("Stop.", "sus"),
         ("Hepsini onayla.", "hepsi"), ("Hepsi evet.", "hepsi"), ("Approve all.", "hepsi"),
         ("Ne dedin?", "tekrar"), ("Tekrar.", "tekrar"), ("Repeat.", "tekrar"),
         ("Evet yazma.", "karisik"), ("Hayır evet.", "karisik"), ("Hepsini reddet.", "karisik"), ("Tamam dur.", "karisik"),
         ("Evet ama saati on bir yap.", "uzun"), ("Evet ama.", "uzun"), ("Bunu yarın sabah ilk iş olarak yaz.", "uzun"),
         ("Altyazı M.K.", "yok"), ("Teşekkürler.", "yok"), ("", "yok"), ("Hı.", "yok")]
yanlis = [(m, b, _ns["sesli_ayir"](m)) for m, b in TABLO if _ns["sesli_ayir"](m) != b]
ok(f"sesli cevap ayırıcısı {len(TABLO) - len(yanlis)}/{len(TABLO)}" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
print("yazayım:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
