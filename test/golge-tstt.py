#!/usr/bin/env python3
# Gölge kipte turkish-stt (aktarici/golge-tstt.py + tstt-golge-isci.py): kapalıyken süreç açılmaz, sahte tanıyıcıyla kayıt yolu, kuyruk dolunca dusen, gizli toplantıda atlama,
# çökünce yeniden açma, ayar kapanınca işçinin kapanması; kuruluysa gerçek model ve Türkçe wav ile en az bir "soz" satırı. Canlı aktarıcıya dokunmaz (yalıtılmış ad alanı).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/golge-tstt.py      (kaldı → çıkış 1)
import base64, json, os, queue, shutil, subprocess, sys, tempfile, threading, time, wave
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: import bosport  # gerçek modelli testler canlı toplantıyı bekler (AGIR_TESTLER)
except Exception: pass
T = tempfile.mkdtemp(prefix="suflor-golge-"); KL = os.path.join(T, "ses"); JS = os.path.join(KL, "tstt-golge.jsonl")
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
def write(pairs):
    for p, t in pairs:
        with open(p, "a", encoding="utf-8") as f: f.write(t)
STATE = {}; AYAR = {}; GIZLI = [False]
ns = dict(os=os, json=json, time=time, threading=threading, sys=sys, STATE=STATE, AYAR=AYAR, _ORT=T, _UYG=KOD, _APP=KOD, _ilk=lambda *y: next((x for x in y if os.path.exists(x)), y[-1]),
          gizli_acik=lambda: GIZLI[0], ses_arsivi_klasor=lambda: KL, LOCK=threading.Lock(), write=write)
exec(compile(open(os.path.join(KOD, "aktarici", "golge-tstt.py"), encoding="utf-8").read(), "golge-tstt", "exec"), ns)
ns["GOLGE_ISCI"] = os.path.join(KOD, "tstt-golge-isci.py")
os.environ["SUFLOR_GOLGE_SAHTE"] = "1"
def satirlar():
    try: return [json.loads(l) for l in open(JS, encoding="utf-8")]
    except OSError: return []
def bekle(kosul, sn=15):
    t = time.time()
    while time.time() - t < sn:
        if kosul(): return True
        time.sleep(0.1)
    return False
def pcm100(): return b"\x10\x00" * 1600
G = STATE["golge_tstt"]
# a) ayar kapalı: süreç açılmaz, kuyruk boş
ns["golge_besle"]("ben", time.time(), pcm100()); time.sleep(0.3)
kontrol("kapalıyken: işçi yok, kuyruk boş, durum kapali", ns["_GL"]["p"] is None and ns["GOLGE_Q"].qsize() == 0 and G["durum"] == "kapali")
# b) sahte tanıyıcı
AYAR.update(golge_tstt=True, tstt_python=sys.executable, tstt_model=T)
kontrol("golge_acik: python + model + işçi var", ns["golge_acik"]() is True)
t0 = time.time()
for i in range(30): ns["golge_besle"]("ben", t0 + i * 0.1, pcm100())  # 3 sn ses → 2 söz biter
kontrol("hazir satırı geldi, durum calisiyor", bekle(lambda: any(s["tur"] == "hazir" for s in satirlar())) and G["durum"] == "calisiyor")
kontrol("soz satırları yazıldı (3 sn → 3 söz)", bekle(lambda: len([s for s in satirlar() if s["tur"] == "soz"]) >= 3) and G["satir"] >= 3)
sz = [s for s in satirlar() if s["tur"] == "soz"][0]
kontrol("soz alanları ve sıra", all(k in sz for k in ("k", "t0", "ilk_ses", "ilk_duvar", "t1", "son_duvar", "metin", "degisim")) and sz["k"] == "ben" and sz["ilk_duvar"] <= sz["son_duvar"] and sz["t0"] <= sz["t1"] and sz["degisim"] >= 1)
kontrol("ses zamanı: ilk_ses = t0 + parça süresi (0,1 sn)", abs(sz["ilk_ses"] - sz["t0"] - 0.1) < 0.01)
kontrol("ara metin zamanları: değişim sayısı kadar, sıralı, sonuncusu kesin metin", len(sz["ara"]) == sz["degisim"] and sz["ara"][-1][2] == sz["metin"]
        and all(a[0] <= b[0] and a[1] <= b[1] for a, b in zip(sz["ara"], sz["ara"][1:])) and sz["ara"][0][1] == round(sz["ilk_duvar"], 2))
# gizli toplantı: beslenmez
GIZLI[0] = True; n = ns["GOLGE_Q"].qsize(); ns["golge_besle"]("ben", time.time(), pcm100()); GIZLI[0] = False
kontrol("gizli toplantıda besleme atlandı", ns["GOLGE_Q"].qsize() == n)
# çökme: işçi öldürülür, sonraki besleme yeniden açar
p1 = ns["_GL"]["p"]; p1.kill(); p1.wait()
for i in range(12): ns["golge_besle"]("karsi", t0 + 10 + i * 0.1, pcm100()); time.sleep(0.05)
kontrol("çökünce yeniden açıldı (yeni süreç, karşı kanalda söz)", bekle(lambda: ns["_GL"]["p"] is not None and ns["_GL"]["p"] is not p1) and bekle(lambda: any(s.get("k") == "karsi" for s in satirlar() if s["tur"] == "soz")))
# ayar kapanınca işçi kapanır
p2 = ns["_GL"]["p"]; AYAR["golge_tstt"] = False
kontrol("ayar kapanınca işçi kapandı, durum kapali", bekle(lambda: p2.poll() is not None, 12) and G["durum"] == "kapali")
# kuyruk dolunca dusen (kuyruğu tüketen iş parçacığı yok: uyuyan sahte iş parçacığı)
AYAR["golge_tstt"] = True; ns["GOLGE_Q"] = queue.Queue(maxsize=3); dm = threading.Thread(target=time.sleep, args=(5,), daemon=True); dm.start(); ns["_GL"]["th"] = dm
d0 = G["dusen"]
for i in range(8): ns["golge_besle"]("ben", time.time(), pcm100())
kontrol("kuyruk dolunca dusen arttı (8 − 3 = 5)", G["dusen"] - d0 == 5 and ns["GOLGE_Q"].qsize() == 3)
AYAR["golge_tstt"] = False
# saatte 3'ten fazla çökme: durdu
ns["_GL"]["cokme"] = [time.time()] * 3; ns["_golge_coktu"]()
kontrol("saatte 3'ten fazla çökünce durdu ve bir saat beslenmez", G["durum"] == "durdu" and ns["_GL"]["dur"] > time.time() + 3000)
ns["_GL"]["dur"] = 0
# d) anlık ilk yazı (S191): ara satırları taslak deposuna, jsonl'a değil; Whisper tüketir; altyazı önceliği; ayar kapalı; gizli
import datetime
kaynak = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
parca = kaynak[kaynak.index("T_LOCK = threading.Lock(); TASLAK"):kaynak.index("# --- Yankı ayıklama")]
DUR = []; OKUMA = [True]
ns2 = dict(threading=threading, time=time, datetime=datetime, STATE={"meeting": "Deneme"}, AYAR={}, ben_adi=lambda: "Test Kullanıcı", gizli_acik=lambda: GIZLI[0], kume_oyla=lambda *a, **k: None,
           okuma_suruyor=lambda: OKUMA[0], okuma_dur_soz=lambda m, t=None: m.strip().lower() in ("bir dakika", "dur"), asistan_dur=lambda: DUR.append(1), _t=lambda tr, en: tr)
exec(compile(parca, "taslak", "exec"), ns2)
A = ns2["AYAR"]
def gor(tstt=True): return ns2["taslak_view"]("Deneme", tstt=tstt)
# ara satırları gerçek akıştan: işçi sahte tanıyıcıyla ara satırı yollar, _golge_oku bunu taslak_tstt'ye verir
ns.update(taslak_tstt=ns2["taslak_tstt"], taslak_tstt_bitti=ns2["taslak_tstt_bitti"])
if os.path.exists(JS): os.remove(JS)
AYAR.update(golge_tstt=True, tstt_python=sys.executable, tstt_model=T); G.update(durum="kapali"); ns["_GL"].update(th=None, p=None, t=0, cokme=[], dur=0); ns["GOLGE_Q"] = queue.Queue(maxsize=300)
t0 = time.time()
for i in range(5): ns["golge_besle"]("karsi", t0 + i * 0.1, pcm100())
kontrol("ara metin panoda: kanal karsi, taslak metni, tarafsız ad", bekle(lambda: any(d["kanal"] == "karsi" and d["text"].startswith("sahte") for d in gor())) and gor()[0]["speaker"] == "Karşı taraf")
kontrol("izle'ye giden /taslak (tstt=False) tstt taslağını içermez", gor(False) == [])
kontrol("ara satırı tstt-golge.jsonl'a yazılmadı", not any(s.get("tur") == "ara" for s in satirlar()))
d0 = list(ns2["TASLAK"].values())[0]; kontrol("taslak src tstt, kimlik tstt-karsi-1", d0["src"] == "tstt" and d0["id"] == "tstt-karsi-1")
for i in range(5, 10): ns["golge_besle"]("karsi", t0 + i * 0.1, pcm100())  # 1 sn dolar → söz biter
kontrol("söz bitince taslak kısa ömre geçer (8 sn)", bekle(lambda: d0.get("omur") == 8))
n1 = ns2["taslak_tuket"]("karsi", time.time())
kontrol("Whisper satırı tstt taslağını tüketir (panoda görünmez), ilk görülme anı döner", n1 is not None and gor() == [])
ns2["taslak_tstt"]("karsi", "yeni söz", None)
kontrol("yeni söz yeni kimlik alır, tüketilen sayı devralınmaz", [d["id"] for d in gor()] == ["tstt-karsi-2"] and gor()[0]["text"] == "yeni söz")
ns2["taslak_tuket"]("karsi", time.time() - 5)  # söz Whisper parçasından sonra başladı: tüketilmez
kontrol("parçadan sonra başlayan taslak tüketilmez", len(gor()) == 1)
# süre dolumu
d2 = ns2["TASLAK"]["tstt-karsi-2"]; ns2["taslak_tstt_bitti"]("karsi"); d2["son"] -= 9; ns2["taslak_view"]("Deneme", tstt=True)
kontrol("Whisper satırı gelmezse (yankı süzgeci) taslak 8 sn sonra düşer", "tstt-karsi-2" not in ns2["TASLAK"])
# altyazı önceliği
ns2["taslak_tstt"]("karsi", "tstt yazısı", None)
ns2["taslak_al"]({"meeting": {"title": "Deneme"}, "source": "captions", "entries": [{"id": "c1", "speaker": "Ali V", "text": "altyazı yazısı"}]})
g = gor(); kontrol("aynı kanalda taze altyazı taslağı varsa tstt gizli", [x["text"] for x in g] == ["altyazı yazısı"])
ns2["taslak_tstt"]("ben", "benim sözüm", None)
kontrol("öbür kanal etkilenmez (ben tstt görünür, ad ben_adi)", any(x["kanal"] == "ben" and x["speaker"] == "Test Kullanıcı" for x in gor()))
ns2["TASLAK"]["c1"]["son"] -= 4
kontrol("altyazı 3 sn'den eskiyse tstt yine görünür", any(x["text"] == "tstt yazısı" for x in gor()))
# durdurma sözü (yalnız okuma sürerken, ben kanalı, 0,6 sn kararlı)
ns2["taslak_tstt"]("ben", "bir dakika", None); time.sleep(0.2); n = len(DUR)
kontrol("durdurma sözü 0,6 sn dolmadan kesmez", len(DUR) == 0)
kontrol("durdurma sözü kararlı kalınca okuma durur", bekle(lambda: len(DUR) == 1, 3))
OKUMA[0] = False; ns2["taslak_tstt"]("ben", "dur", None); time.sleep(1)
kontrol("okuma sürmüyorsa durdurma bakılmaz", len(DUR) == 1)
ns2["taslak_tstt"]("karsi", "bir dakika", None); time.sleep(1)
kontrol("karşı kanal taslağı okumayı durdurmaz", len(DUR) == 1)
# ayar kapalı / gizli
ns2["TASLAK"].clear(); ns2["_TSTT"].clear(); A["tstt_taslak"] = False; ns2["taslak_tstt"]("karsi", "kapalı", None)
kontrol("ayar tstt_taslak kapalı: taslak oluşmaz", ns2["TASLAK"] == {})
A.pop("tstt_taslak"); GIZLI[0] = True; ns2["taslak_tstt"]("karsi", "gizli", None); GIZLI[0] = False
kontrol("gizli toplantıda taslak oluşmaz", ns2["TASLAK"] == {})
ns2["taslak_tstt"]("karsi", "bir iki üç", None); A["tstt_taslak"] = False
kontrol("ayar kapanınca mevcut tstt taslağı panodan kalkar", gor() == [])
A.pop("tstt_taslak"); ns2["taslak_tuket"]("karsi", time.time()); ns2["taslak_tstt"]("karsi", "bir", None)
kontrol("metin tüketilenden kısaysa yeni söz sayılır", [x["text"] for x in gor()] == ["bir"])
AYAR["golge_tstt"] = False; time.sleep(6)
# c) gerçek işçi ve model (yoksa atla)
PY, MD = "/Users/Shared/Suflor/tstt-venv/bin/python", "/Users/Shared/Suflor/tstt-model"
WAV = os.path.join(os.path.dirname(KOD), "_yedek", "test-araclari", "gercek-ses", "calisma", "easyturkish208.wav")
if os.path.exists(PY) and os.path.isdir(MD) and os.path.exists(WAV):
    os.environ.pop("SUFLOR_GOLGE_SAHTE", None); os.remove(JS)
    ns["GOLGE_Q"] = queue.Queue(maxsize=300); ns["_GL"].update(th=None, p=None, t=0, cokme=[]); G.update(durum="kapali", dusen=0, satir=0)
    AYAR.update(golge_tstt=True, tstt_python=PY, tstt_model=MD)
    with wave.open(WAV) as w:
        ok = (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2); veri = w.readframes(16000 * 12)
    kontrol("test sesi 16 kHz mono int16", ok)
    t0 = time.time()
    for i in range(0, len(veri) // 3200):
        ns["golge_besle"]("karsi", t0 + i * 0.1, veri[i * 3200:(i + 1) * 3200])
        if i % 100 == 99: time.sleep(0.5)  # kuyruk (300) taşmasın
    kontrol("gerçek: hazir satırı", bekle(lambda: any(s["tur"] == "hazir" for s in satirlar()), 40))
    kontrol("gerçek: kuyruk boşaldı", bekle(lambda: ns["GOLGE_Q"].empty(), 60)); time.sleep(2)
    AYAR["golge_tstt"] = False; p = ns["_GL"]["p"]
    if p: bekle(lambda: p.poll() is not None, 15)
    sl = satirlar(); hz = [s for s in sl if s["tur"] == "hazir"]; sz = [s for s in sl if s["tur"] == "soz"]
    kontrol(f"gerçek: en az bir soz satırı ({len(sz)})", len(sz) >= 1 and all(s["ilk_duvar"] <= s["son_duvar"] for s in sz))
    kontrol("gerçek: ara metin zamanları dolu, sonuncusu kesin metin", all(s["ara"] and s["ara"][-1][2] == s["metin"] for s in sz if not s.get("yarim")))
    if hz: print(f"  yükleme {hz[0]['yukleme_sn']} sn")
    if sz: print("  örnek:", json.dumps({**sz[0], "metin": sz[0]["metin"][:50]}, ensure_ascii=False))
else: print("- gerçek model/ses yok: atlandı")
print(T) if hatalar else shutil.rmtree(T, ignore_errors=True)
print("\nKALDI: " + ", ".join(hatalar) if hatalar else "\nhepsi geçti"); sys.exit(1 if hatalar else 0)
