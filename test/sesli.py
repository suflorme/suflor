# Faz 4 — sesli özet ve "yazayım mı?" dizisi (yalıtılmış aktarıcı; SUFLOR_TEST_BASLAT: ses çalınmaz, okunacak metin günlüğe yazılır).
# Aktarıcıda seslendir / ozet_sesli / soru_* / eylem_sun / eylem_karar ya da panodaki Sonra/Sus değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli.py
import shutil, json, os, sys, subprocess, tempfile, time, urllib.request, urllib.error
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8795)
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
    post("/son-toplanti", {"ozet": os.path.join(T, "ozet.md"), "baslik": "Deneme", "cikti": {"karar": 2, "is": 3, "acik": 1}, "degerlendirme": "Bütçe onaylandı; **süre** uzatıldı", "oneri": "Gündemi kısalt"})
    time.sleep(0.5); L = log()
    ok("özet sesli okundu (karar/iş/açık sayısı, kararlar, öneri, bekleyen sayısı)", "Toplantı özeti hazır. 2 karar, 3 iş, 1 açık. Bütçe onaylandı; süre uzatıldı. Öneri: Gündemi kısalt." in L and "3 iş var" in L)
    post("/eylem-sun", {}); time.sleep(0.5)
    ok("sun → ilk iş soruldu", "Karar: erişim listesi cuma güncellenir. Bunu kayda geçireyim mi?" in log() and st()["eylem"]["sesli"] == ids[0])
    post("/eylem-karar", {"id": ids[0], "durum": "onaylandi"}, pano=True); time.sleep(0.5)
    ok("Onayla → ikinci iş soruldu", "Deniz — takip e-postası. Taslağını hazırlayayım mı?" in log() and st()["eylem"]["sesli"] == ids[1])
    post("/eylem-sesli", {"komut": "sonra"}, pano=True); time.sleep(0.5)
    ok("Sonra → üçüncü iş, ikinci bekliyor", st()["eylem"]["sesli"] == ids[2] and "Metnini hazırlayayım mı?" in log()
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
    post("/son-toplanti", {"ozet": os.path.join(T, "ozet.md"), "baslik": "Deneme", "cikti": {"karar": 1}, "degerlendirme": "x"}); time.sleep(0.5)
    ok("toplantı sürerken hiçbir şey okunmadı", log().count("SES (deneme)") == n0)
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait()
# S24 Aşama 1: sesli cevap ayırıcısı (aktarıcının kendi tanımları; Whisper'ın verdiği biçimler — noktalama, büyük harf, İ/I)
import ast
_k = "".join(open(f, encoding="utf-8").read() for f in [os.path.join(KOD, "relay.py")] + sorted(__import__("glob").glob(os.path.join(KOD, "aktarici", "*.py")))); _ad = {"SES_CEVAP", "SES_AMA", "SES_DOLGU", "SES_PEKISTIRME", "sesli_ayir"}
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
         ("Aç.", "onay"), ("Aç lütfen.", "onay"), ("Olsun.", "onay"), ("Boş ver.", "red"), ("Vazgeç.", "red"), ("Açma.", "red"),  # v0.131.0: sorunun fiili onay
         ("Altyazı M.K.", "yok"), ("Teşekkürler.", "yok"), ("", "yok"), ("Hı.", "yok")]
yanlis = [(m, b, _ns["sesli_ayir"](m)) for m, b in TABLO if _ns["sesli_ayir"](m) != b]
ok(f"sesli cevap ayırıcısı {len(TABLO) - len(yanlis)}/{len(TABLO)}" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
# v0.131.0: doğal soru ve yeniden sorma (aktarıcının kendi tanımları)
_ad2 = {"EYLEM_FIIL", "SORU_YENIDEN", "SORU_UZUN", "SORU_BIRAK", "kullanici_ilk_ad", "_eylem_fiil", "_yeniden_sor", "_soru_metni", "_cumle"}
_ns2 = {"re": __import__("re"), "datetime": __import__("datetime"), "AYAR": {"ad": "Deniz K"}, "ARAYUZ_DILI": "tr", "_t": lambda a, b: a, "SORU": {}}
exec(compile(ast.Module([n for n in ast.parse(_k).body if (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in _ad2 for x in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name in _ad2)], []), "relay", "exec"), _ns2)
yil = __import__("datetime").date.today().year
s = _ns2["_soru_metni"]({"tur": "yapilacak", "baslik": f"Yarın Pazar 25 Ekim {yil} sabah 10.00'da Ali'yi ara"})
ok(f"ilk soru doğal, adla, yılsız: {s!r}", s == "Deniz, Yarın Pazar 25 Ekim sabah 10.00'da Ali'yi ara. Hatırlatma olarak ekleyeyim mi?")
x = {"tur": "takvim", "baslik": "Toplantı"}; y1 = _ns2["_yeniden_sor"](x); y2 = _ns2["_yeniden_sor"](x)
ok(f"anlaşılmazsa seçenek saymadan bir kez daha sorar, ikincisinde bırakır: {y1!r}", y1 and "takvimine ekleyeyim mi" in y1.lower() and "sonra" not in y1 and y2 is None)
_ns2["SORU"]["deneme"] = 0; u = _ns2["_yeniden_sor"](x, uzun=True); ok(f"uzun cevapta: {u!r}", u == "Anladım, yalnız emin olayım: takvimine ekleyeyim mi?")
cumleler = set()
for _ in range(20): _ns2["SORU"]["deneme"] = 0; cumleler.add(_ns2["_yeniden_sor"](x))
ok(f"yeniden sorma cümleleri değişir ({len(cumleler)} farklı)", len(cumleler) >= 2 and all("  " not in c and " ," not in c for c in cumleler))
print("yazayım:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
