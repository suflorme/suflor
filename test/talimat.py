#!/usr/bin/env python3
# Sesle oturuma talimat ve yapılacak (v0.75.0, aktarici/talimat.py) — kota harcamadan, Whisper ve Claude olmadan:
#  1) ayrıştırma tablosu (hedef kalıbı, ileti önde/arkada, yapılacak, kişilik adı, hitap olmayan cümle)
#  2) yalıtılmış aktarıcı: toplantıda kendi "Claude: …" satırı → onay kartı (sesle okunmaz), eylem kuyruğunda yerel iş (toplantı oturumu görmez),
#     Onayla → gelen kutusu (0600) → toplanti-claude.py gelen bir kez basar; Reddet → yazılmaz; karşı tarafın aynı sözü talimat sayılmaz;
#     yapılacak → onay → toplantı bitince e-posta taslağı (deneme kipinde açılmaz, günlükte).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/talimat.py
import json, os, re, shutil, stat, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8785)
T = tempfile.mkdtemp(prefix="talimat-"); canli = os.path.join(T, "canli"); os.makedirs(canli); HATA = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad, flush=True); HATA.append(ad) if not k else None
HEDEF = [{"ad": "proje", "etiket": "proje oturumu", "kalip": ["proje oturumuna", "ana oturuma"]}, {"ad": "gelistirme", "etiket": "geliştirme oturumu", "kalip": ["geliştirme oturumuna"]}]
# 1) ayrıştırma
src = open(os.path.join(KOD, "aktarici", "talimat.py"), encoding="utf-8").read()
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": __import__("datetime"), "AYAR": {"talimat_hedefler": HEDEF}, "_t": lambda a, b: a, "kisilik_hitap_bul": lambda m: (None, re.sub(r"^Atlas,\s*", "", m))}
exec(src[src.index("TALIMAT_FIIL ="):src.index("def _talimat_kayit")], ns)
for g, b in [("proje oturumuna ilet: sözleşme taslağını cuma 17.00'ye kadar hazırla", ("oturum", "proje", "sözleşme taslağını cuma 17.00'ye kadar hazırla")),
             ("Geliştirme oturumuna şunu söyle, panodaki düğme rengini koyulaştır.", ("oturum", "gelistirme", "panodaki düğme rengini koyulaştır")),
             ("Haftalık raporu pazartesiye çek, bunu ana oturuma ilet.", ("oturum", "proje", "Haftalık raporu pazartesiye çek")),
             ("Yapılacaklarıma ekle: vergi beyannamesini kontrol et", ("yapilacak", None, "vergi beyannamesini kontrol et")),
             ("Claude: yapılacak listeme yaz, dişçiden randevu al.", ("yapilacak", None, "dişçiden randevu al")),
             ("Atlas, Geliştirme Oturumuna bildirim gönderir misin? Test bildirimi.", ("oturum", "gelistirme", "Test bildirimi")),  # ilk gerçek deneme (18 Ekim)
             ("Proje oturumuna bir mesaj ilet: toplantı perşembeye kaydı.", ("oturum", "proje", "toplantı perşembeye kaydı")),
             ("Ana oturuma not düş, yarın izinliyim.", ("oturum", "proje", "yarın izinliyim")),
             ("Anladım. Ana oturma bildirim gönderir misin? R12 işi listeden çıksın.", ("oturum", "proje", "R12 işi listeden çıksın")),  # v0.101.1: Whisper "oturma"
             ("Oturma odasına bildirim gönder: ışıklar açık.", None),
             ("Proje oturumu bugün ne yaptı?", None), ("Yarın ne var?", None), ("proje oturumuna ilet", None)]:
    c = ns["talimat_coz"](g); c = (c[0], c[1]["ad"] if c[1] else None, c[2]) if c else None
    ok(f"ayrıştırma: {g!r} → {c}", c == b)
ns["AYAR"]["talimat"] = False; ok("ayar talimat: false kapatır", ns["talimat_coz"]("proje oturumuna ilet: deneme yapalım") is None)
ns["AYAR"] = {}; ok("ayar yoksa yalnız proje hedefi (geliştirme yok)", ns["talimat_coz"]("geliştirme oturumuna ilet: renk değişsin") is None and ns["talimat_coz"]("proje oturumuna ilet: renk değişsin"))
# 1a) v0.101.1: Claude'un hazırladığı ileti — [İLET <hedef>: <ileti>] etiketi silinir, yalnız kullanıcının kendi sorusunda onaya gider
nc = dict(ns, AYAR={"talimat_hedefler": HEDEF}, TALIMAT_EN_COK=1000); giden = []
ZAMAN = []
nc["talimat_kuyruk"] = lambda tur, h, ileti, metin, kaynak, claude=False, zaman=None: ZAMAN.append(zaman) or giden.append((tur, h["ad"] if h else None, ileti, kaynak, claude)) or True
exec(src[src.index("TALIMAT_FIIL ="):src.index("def _talimat_kayit")] + src[src.index("TALIMAT_ETIKET_RX ="):src.index("def talimat_karar")], nc); exec("def print(*a, **k): pass", nc)
c_ = "Tamam, hazırladım.\n---\nAyrıntı.\n[İLET proje: R12 Ali raporu işini listeden çıkar.]"
t_, g_ = nc["talimat_claude"](c_, "o işi listeden çıkaralım", {"kaynak": "bas"})
ok("Claude etiketi: silindi, proje hedefine onaya gitti (claude=True)", g_ and "[İLET" not in t_ and t_.endswith("Ayrıntı.") and giden[-1] == ("oturum", "proje", "R12 Ali raporu işini listeden çıkar", "bas", True))
n_ = len(giden)
for tur_, ad_ in (({"kaynak": "karsi", "karsi": True}, "karşı taraf"), ({"kaynak": "hitap"}, None)):
    t_, g_ = nc["talimat_claude"](c_, "soru", tur_)
    ok(f"Claude etiketi ({tur_['kaynak']}): {'gitmedi' if ad_ else 'gitti (kullanıcının hitabı)'}, etiket silindi", "[İLET" not in t_ and (not g_ if ad_ else g_))
ok("karşı tarafın sorusunda kuyruğa bir şey girmedi", len(giden) == n_ + 1)
t_, g_ = nc["talimat_claude"]("Olur. [ILET bilinmeyen: bir şey yap lütfen]", "s", {"kaynak": "bas"}); ok("bilinmeyen hedef: gitmez, etiket silinir", not g_ and t_ == "Olur.")
t_, g_ = nc["talimat_claude"]("Cevap.", "s", {"kaynak": "bas"}); ok("etiketsiz cevap değişmez", t_ == "Cevap." and not g_)
nc["AYAR"] = {"talimat": False}; ok("ayar talimat: false → istemde yol yok", nc["talimat_istem"]() == "")
nc["AYAR"] = {"talimat_hedefler": HEDEF}; i_ = nc["talimat_istem"]()
ok("istemde hedef listesi ve etiket biçimi", "proje = proje oturumu" in i_ and "gelistirme = geliştirme oturumu" in i_ and "[İLET <hedef>: <ileti>]" in i_)
t_, g_ = nc["talimat_claude"]("Hazırladım.\n[İLET yapilacak: Cumartesi 10.00'da Ali'yi ara.]", "yarın onda Ali'yi aramamı hatırlatan bir not yaz", {"kaynak": "sohbet"})
ok("24 Ekim: hatırlatma/not → kullanıcının yapılacağı (oturuma değil), etiket silindi", g_ and t_ == "Hazırladım." and giden[-1] == ("yapilacak", None, "Cumartesi 10.00'da Ali'yi ara", "sohbet", True))
t_, g_ = nc["talimat_claude"]("Hazırladım. [İLET yapilacak: Pazar sabah 10.00'da Ali'yi ara | 2026-10-25T10:00]", "s", {"kaynak": "sohbet"})
ok(f"v0.131.0: etiketteki saat ayrılır (Anımsatıcılar): {giden[-1][2]!r} · {ZAMAN[-1]!r}", g_ and giden[-1][2] == "Pazar sabah 10.00'da Ali'yi ara" and ZAMAN[-1] == "2026-10-25T10:00")
ok("saat biçimleri: '2026-10-25 9.30' → 09:30, saatsiz → None, bozuk tarih → None", nc["animsatici_zaman_ayir"]("a b | 2026-10-25 9.30") == ("a b", "2026-10-25T09:30")
   and nc["animsatici_zaman_ayir"]("süt al") == ("süt al", None) and nc["animsatici_zaman_ayir"]("x y | 2026-13-40T10:00")[1] is None)
t_, g_ = nc["talimat_claude"]("Tamam. [İLET hatırlatma: süt al]", "s", {"kaynak": "karsi", "karsi": True}); ok("karşı tarafın isteğinde yapılacak da gitmez", not g_ and t_ == "Tamam.")
ok("istemde saat alanı, takvim, gerçek durum listesi ve silme etiketi", "| <YYYY-MM-DDTHH:MM>]" in i_ and "takvimine o saatte etkinlik" in i_ and "[İLET sil: <no>]" in i_ and "Hazırladığın işler" in i_)
ok("istemde hatırlatma yolu, 'yazamıyorum' yok, gece 'yarın' sorusu, eylemde kısa doğrulama", "[İLET yapilacak:" in i_ and "'yazamıyorum' deme" in i_ and "00.00 ile 05.00" in i_ and "tek kısa doğrulama sorusu" in i_)
ok("okuma sınırı: etiketin başı yakalanır (kapanış gelmeden)", nc["TALIMAT_ETIKET_BAS"].search("Hazırladım. [İLET pro") is not None)
# 1b) onay sözcükleri (v0.77.1, kullanıcı: evet dışında gönder, bildir, onaylıyorum, yes, tamam da onay)
bs = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); nb = {"re": re}; exec(bs[bs.index("SES_CEVAP = {"):bs.index("def sesli_cevap(")], nb)
for g, b in [("Bildir.", "onay"), ("Gönder", "onay"), ("Evet, gönder.", "onay"), ("Onaylıyorum", "onay"), ("Yes", "onay"), ("Tamam", "onay"), ("İlet.", "onay"),
             ("Gönderme", "red"), ("Hayır, iletme.", "red"),
             ("İleti.", "onay"), ("Evet, evet, gönder. Kabul ediyorum, ilet.", "onay"), ("Kabul ediyorum.", "onay"),  # v0.101.1 (21 Ekim gerçek deneme)
             ("Hayır hayır, gönderme bunu.", "red"), ("Evet, Ali'nin raporunu da ekle lütfen.", "uzun"), ("Evet evet gönder ama önce bana oku", "uzun")]:
    ok(f"onay sözcüğü: {g!r} → {nb['sesli_ayir'](g)}", nb["sesli_ayir"](g) == b)
# 2) yalıtılmış aktarıcı
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "talimat_hedefler": HEDEF, "eposta": "gmail", "eposta_adres": "deniz" + chr(64) + "ornek.test"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log"); env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_METIN="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
L = lambda: open(log, encoding="utf-8", errors="replace").read()
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None, pano=False):
        h = {"X-Suflor-Anahtar": K, **({"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers=h), timeout=10).read())
    n = [0]
    def satir(kanal, metin, kim="Deniz T"):
        n[0] += 1; uc("/ingest", {"meeting": {"title": "Talimat deneme"}, "source": "whisper", "entries": [{"id": f"t/{n[0]}", "speaker": kim, "time": time.strftime("%H:%M:%S"), "text": metin, "kanal": kanal}]})
    NABIZ = threading.Event()
    def nabiz():
        while not NABIZ.is_set(): uc("/ping", {"meeting": {"title": "Talimat deneme"}, "call": True, "panel": True}); time.sleep(2)
    threading.Thread(target=nabiz, daemon=True).start(); time.sleep(0.5)
    tc = lambda *a: subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", *a], capture_output=True, text=True, env=env, timeout=30).stdout
    satir("ben", "Claude: geliştirme oturumuna ilet: panodaki düğme rengini koyulaştır."); time.sleep(0.8)
    kartlar = uc("/cards"); kart = next((c for c in kartlar.get("cards") or [] if c.get("onay") and "geliştirme oturumu" in c.get("text", "")), None)
    ok("toplantıda kendi talimatı → onay kartı", bool(kart) and "panodaki düğme rengini koyulaştır" in kart["text"])
    ok("toplantıda sesle okunmadı", "SES (deneme)" not in L())
    ey = (kartlar.get("eylem") or {}).get("liste") or []
    ok("eylem kuyruğunda yerel iş (oturum, bekliyor)", any(x["tur"] == "oturum" and x.get("yerel") and x["durum"] == "bekliyor" for x in ey))
    ok("toplantı oturumu yerel işi görmez (eylem liste)", "düğme rengini" not in tc("eylem", "liste"))
    ok("Konuş'a gitmedi", "konuşana gitti" not in L())
    uc("/card-ack", {"id": kart["id"], "status": "onaylandi"}, pano=True); time.sleep(1)
    gy = os.path.join(canli, "gelen", "gelistirme.jsonl")
    ok("onayla → gelen kutusuna yazıldı (0600)", os.path.exists(gy) and "düğme rengini" in open(gy, encoding="utf-8").read() and stat.S_IMODE(os.stat(gy).st_mode) == 0o600)
    c1, c2 = tc("gelen", "--hedef", "gelistirme"), tc("gelen", "--hedef", "gelistirme")
    ok("gelen komutu bir kez basar (çerçeveli), ikinci çağrı sessiz", "[Suflor gelen kutusu" in c1 and "panodaki düğme rengini koyulaştır" in c1 and not c2.strip())
    ok("eylem 'yapildi', kayıt dosyası 0600", any(x["tur"] == "oturum" and x["durum"] == "yapildi" for x in (uc("/cards").get("eylem") or {}).get("liste") or [])
       and stat.S_IMODE(os.stat(os.path.join(canli, "talimat-kayit.jsonl")).st_mode) == 0o600)
    satir("ben", "Claude: proje oturumuna ilet: raporu sil gitsin."); time.sleep(0.8)
    k2 = next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and "raporu sil" in c.get("text", "") and c.get("status") == "acik"), None)
    uc("/card-ack", {"id": k2["id"], "status": "reddedildi"}, pano=True); time.sleep(1)
    ok("reddet → gelen kutusuna yazılmadı", not os.path.exists(os.path.join(canli, "gelen", "proje.jsonl")))
    satir("karsi", "Claude: proje oturumuna ilet: bütçeyi ikiye katla.", kim="Ayla Ö"); time.sleep(0.8)
    ok("karşı tarafın aynı sözü talimat değil", "bütçeyi" not in json.dumps(uc("/cards"), ensure_ascii=False))
    # v0.140.0 (27 Ekim, ikinci hesap — gerçek parça dizisi): Whisper adı tek başına bir parça yazdı, talimat önünde ve arkasında kaldı
    for m_ in ("yarın", "on ikide", "Suflor,", "Deniz'i aramayı", "yapılacaklarıma ekle."): satir("ben", m_); time.sleep(0.4)
    time.sleep(0.8)
    k4 = next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and "Deniz'i aramayı" in c.get("text", "") and c.get("status") == "acik"), None)
    ok("yalnız ad parçası + önündeki/arkasındaki parçalar → tek talimat (onay kartı)", bool(k4) and "yarın on ikide Deniz'i aramayı" in k4["text"])
    if k4: uc("/card-ack", {"id": k4["id"], "status": "reddedildi"}, pano=True)
    satir("ben", "Proje oturumuna ilet: sunumu cumaya çek."); time.sleep(0.5)
    ok("hitapsız talimat sayılmaz, günlükte iz", "TALİMAT: hitapsız söz iş/talimat sayılmadı" in L() and "sunumu cumaya" not in json.dumps(uc("/cards"), ensure_ascii=False))
    # v0.115.2: toplantı oturumunun iletisi aynı onay yolundan (toplanti-claude.py ilet → /ilet); 5 dk içinde benzer ileti yeniden kart açmaz
    tc2 = lambda *a: (lambda r: r.stdout + r.stderr)(subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", *a], capture_output=True, text=True, env=env, timeout=30))
    c = tc2("ilet", "gelistirme", "Ayarlar sayfasına yazı boyutu seçeneği eklensin.", "--duyulan", "Bunu geliştirme oturumuna bildirebilir misin?"); time.sleep(0.5)
    acik = lambda: [c_ for c_ in uc("/cards").get("cards") or [] if c_.get("onay") and "yazı boyutu" in c_.get("text", "") and c_.get("status") == "acik"]
    ok("ilet → onay kartı (aktarıcının yolu), 'iletildi' demez", "onay kartı panoda" in c and len(acik()) == 1 and "geliştirme oturumu" in acik()[0]["text"])
    ok("ilet → yerel iş (toplantı oturumu eylem listesinde görmez)", "yazı boyutu" not in tc("eylem", "liste"))
    satir("ben", "Claude: geliştirme oturumuna ilet: ayarlar sayfasına yazı boyutu seçeneği ekle."); time.sleep(0.8)
    ok("aynı istek asistandan da gelince ikinci kart açılmadı", len(acik()) == 1 and "TALİMAT: yinelenmedi — gelistirme" in L())
    ok("ilet ikinci kez → yinelenmedi", "yinelenmedi" in tc2("ilet", "gelistirme", "Ayarlar sayfasına yazı boyutu seçeneği ekle") and len(acik()) == 1)
    ok("başka iletiler yinelenen sayılmaz", "onay kartı panoda" in tc2("ilet", "gelistirme", "Mini panoda saat de görünsün.") and len(acik()) == 1)
    ok("yanlış hedef → geçerli adlar", "geçerli hedefler: proje, gelistirme" in tc2("ilet", "yok", "bir iki üç"))
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/ilet", data=b'{"hedef":"proje","metin":"bir iki"}'), timeout=5); izinsiz = False
    except urllib.error.HTTPError as e: izinsiz = e.code == 401
    ok("anahtarsız /ilet → 401", izinsiz)
    satir("ben", "Claude: yapılacaklarıma ekle: vergi beyannamesini kontrol et."); time.sleep(0.8)
    k3 = next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and "vergi" in c.get("text", "") and c.get("status") == "acik"), None)
    ok("yapılacak → onay kartı", bool(k3))
    uc("/card-ack", {"id": k3["id"], "status": "onaylandi"}, pano=True); time.sleep(2)
    ok("toplantı sürerken taslak açılmadı", "taslak gmail" not in L())
    NABIZ.set(); t0 = time.time()
    while time.time() - t0 < 40 and "taslak gmail" not in L(): time.sleep(0.5)  # SUFLOR_TEST_HIZLI: toplantı 6 sn nabızsız biter
    ok(f"saatsiz yapılacak: toplantı bitince e-posta taslağı (kendi adresine) — {time.time() - t0:.0f} sn", "TALİMAT (deneme): taslak gmail · Yapılacak: vergi beyannamesini kontrol et" in L()
       and "takvime eklenemedi (saat yok)" in L())
    # toplantı dışında: Konuş'a söylenen talimat → sesli geri okuma + "İleteyim mi?", panodan Onayla → gelen kutusu
    uc("/bas-konus", {"metin": "Proje oturumuna şunu söyle: haftalık raporu pazartesiye çek."}, pano=True); time.sleep(1)
    ok("toplantı dışında: sesli geri okuma ve 'İleteyim mi?'", "haftalık raporu pazartesiye çek. İleteyim mi?" in L())
    x = next((x for x in (uc("/cards").get("eylem") or {}).get("liste") or [] if "haftalık raporu" in x["baslik"]), None)
    ok("panoda onay bekliyor, Claude'a gitmedi", bool(x) and x["durum"] == "bekliyor" and "açık süreç açıldı" not in L())
    uc("/eylem-karar", {"id": x["id"], "durum": "onaylandi"}, pano=True); time.sleep(1)
    ok("panodan onay → proje gelen kutusu", "haftalık raporu pazartesiye çek" in tc("gelen", "--hedef", "proje"))
    ok("aktarıcıda hata yok", "Traceback" not in L())
finally:
    r.terminate(); r.wait(5)
    if HATA or sys.exc_info()[0]: print("günlük:", log)
    else: shutil.rmtree(T, ignore_errors=True)
# v0.132.0: saatli hatırlatma takvime (etkinlik kimliği işe yazılır), Konuş bağlamında gerçek durum, sesle silme ([İLET sil: no]) → onay → takvimden silinir
import threading as _th
os.environ["SUFLOR_TEST_BASLAT"] = "1"
EY = []; YAMA = []
def _yama(x, **k): x.update(k); YAMA.append(k)
n3 = {"re": re, "os": os, "json": json, "time": time, "datetime": __import__("datetime"), "subprocess": __import__("subprocess"), "threading": _th, "urllib": __import__("urllib"),
      "AYAR": {}, "BASE": tempfile.mkdtemp(), "LOCK": _th.RLock(), "EYLEMLER": EY, "_eylem_yama": _yama, "_t": lambda a, b: a, "write": lambda x: None, "toplanti_var": lambda: False,
      "GERI_AL_SN": 0, "CARDS": [], "EYLEM_TUR": {}, "eylem_sonuc": lambda p: next(x for x in EY if x["id"] == p["id"]).update(durum=p["durum"], sonuc=p["sonuc"]),
      "soru_baslat": lambda ids: None, "_konus_kur": lambda **k: None, "seslendir": lambda *a, **k: None, "add_card": lambda c: None,
      "eylem_ekle": lambda p: EY.append(dict(p, id="e17920000000" + str(len(EY)).zfill(4) + "ab", at=__import__("datetime").datetime.now().isoformat(timespec="seconds"), durum="bekliyor")) or EY[-1]}
exec(compile(open(os.path.join(KOD, "aktarici", "talimat.py"), encoding="utf-8").read(), "talimat.py", "exec"), n3)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    t_, g_ = n3["talimat_claude"]("Hazırladım. [İLET yapilacak: Kardeşini ara; bugün 14.00 | 2026-10-25T14:00]", "s", {"kaynak": "sohbet"})
x = EY[-1]; x["durum"] = "onaylandi"
with contextlib.redirect_stdout(io.StringIO()): n3["_talimat_uygula"](x["id"])
ok(f"saatli hatırlatma takvime: etkinlik kimliği işte, sonuç {x.get('sonuc')!r}", x.get("etkinlik") == "deneme-2026-10-25T14:00" and x["durum"] == "yapildi" and "takvime eklendi" in x["sonuc"])
b_ = n3["talimat_durum_blok"]()
ok(f"Konuş bağlamında gerçek durum: {b_.splitlines()[-1]!r}", "Hazırladığın işler" in b_ and x["id"][-6:] in b_ and "takvime eklendi" in b_)
with contextlib.redirect_stdout(io.StringIO()):
    t_, g_ = n3["talimat_claude"](f"Tamam. [İLET sil: {x['id'][-6:]}]", "s", {"kaynak": "sohbet"})
s_ = EY[-1]
ok("sesle silme isteği: 'sil' işi, etkinlik kimliğiyle, onay bekliyor", g_ and t_ == "Tamam." and s_["tur"] == "sil" and json.loads(s_["ayrinti"])["etkinlik"] == x["etkinlik"])
s_["durum"] = "onaylandi"
with contextlib.redirect_stdout(io.StringIO()): n3["_talimat_uygula"](s_["id"])
ok("onaylanınca takvimden silindi, hatırlatma 'silindi' görünür", s_["durum"] == "yapildi" and x.get("silindi") is True and "takvimden silindi" in n3["talimat_durum_blok"]())
with contextlib.redirect_stdout(io.StringIO()):
    t_, g_ = n3["talimat_claude"]("Tamam. [İLET sil: 999999]", "s", {"kaynak": "sohbet"})
ok("bilinmeyen numara: silme işi açılmaz, etiket silinir", not g_ and t_ == "Tamam.")
# v0.143.0: davetli toplantı — [İLET toplanti: başlık | zaman | dk | davetliler] → onay → takvimin dolu "yeni etkinlik" sayfası (hatırlatma değil)
import urllib.parse as _up
EP = lambda k: k + chr(64) + "ornek.test"  # adres kaynakta yazılmaz (açık depo taraması)
n3["TAKVIM_TAM"] = {"a": {"kisiler": [{"ad": "Deniz Yıldız", "eposta": EP("Deniz.Y")}, {"ad": "Ali Kaya", "eposta": EP("ali")}]},
                    "b": {"kisiler": [{"ad": "Ali Demir", "eposta": EP("ali.d")}]}}
n3["eposta_ben"] = lambda: EP("ben"); n3["eposta_tur"] = lambda: "gmail"
d_ = n3["toplanti_davetli"](["Deniz", "Ali", "Ali Kaya", EP("zeynep"), "Misafir"])
ok(f"davetli: tek eşleşen ilk ad bulunur, iki 'Ali' belirsiz kalır, tam ad bulunur, e-posta olduğu gibi, bilinmeyen adressiz: {d_}",
   [k["eposta"] for k in d_] == [EP("deniz.y"), None, EP("ali"), EP("zeynep"), None])
a_ = n3["toplanti_ayir"]("Deniz ile proje toplantısı | 2026-10-28T12:00 | 45 dk | Deniz ve Misafir")
ok(f"toplantı ayrıştırma: başlık, saat, süre, davetliler: {a_}", a_["baslik"] == "Deniz ile proje toplantısı" and a_["zaman"] == "2026-10-28T12:00" and a_["dk"] == 45
   and [k["ad"] for k in a_["davetli"]] == ["Deniz", "Misafir"])
ok("süre söylenmezse 30 dk", n3["toplanti_ayir"]("Kısa görüşme | 2026-10-28 9.30 | Ali Kaya")["dk"] == 30)
u_ = _up.urlsplit(n3["toplanti_sayfa_url"](a_)); q_ = _up.parse_qs(u_.query)
ok(f"Google sayfası: başlık, 12.00–12.45, davetli adresi, adressiz ad notta, Meet, hesap: {q_}", u_.netloc == "calendar.google.com" and q_["action"] == ["TEMPLATE"]
   and q_["text"] == ["Deniz ile proje toplantısı"] and q_["dates"] == ["20261028T120000/20261028T124500"] and q_["add"] == [EP("deniz.y")]
   and "Misafir" in q_["details"][0] and q_["vcon"] == ["meet"] and q_["authuser"] == [EP("ben")])
n3["eposta_tur"] = lambda: "outlook"; uo_ = n3["toplanti_sayfa_url"](a_); n3["eposta_tur"] = lambda: "gmail"
ok("Outlook ayarında Outlook takvim sayfası", uo_.startswith("https://outlook.office.com/calendar/deeplink/compose?") and "deniz.y%40ornek.test" in uo_)
cikti_ = io.StringIO()
with contextlib.redirect_stdout(cikti_):
    t_, g_ = n3["talimat_claude"]("Hazırladım. [İLET toplanti: Deniz ile toplantı | 2026-10-28T12:00 | 30 | Deniz]", "yarın on ikide Deniz'le toplantı koy", {"kaynak": "sohbet"})
y_ = EY[-1]; ay_ = json.loads(y_["ayrinti"])
ok(f"Claude etiketi: 'toplanti' işi (hatırlatma değil), onay bekliyor, başlıkta davetli: {y_['baslik']!r}", g_ and t_ == "Hazırladım." and y_["tur"] == "toplanti"
   and ay_["zaman"] == "2026-10-28T12:00" and ay_["davetli"][0]["eposta"] == EP("deniz.y") and "Deniz" in y_["baslik"] and "12.00" in y_["baslik"])
y_["durum"] = "onaylandi"; cikti_ = io.StringIO()
with contextlib.redirect_stdout(cikti_): n3["_talimat_uygula"](y_["id"])
ok(f"onaylanınca takvim sayfası açıldı (takvime hatırlatma yazılmadı): {y_.get('sonuc')!r}", y_["durum"] == "yapildi" and "toplantı sayfası https://calendar.google.com" in cikti_.getvalue()
   and "TALİMAT (deneme): takvim ·" not in cikti_.getvalue() and not y_.get("etkinlik"))
ok("Konuş bağlamında toplantının durumu", "toplantı" in n3["talimat_durum_blok"]())
n_ = len(EY)
with contextlib.redirect_stdout(io.StringIO()):
    t_, g_ = n3["talimat_claude"]("Tamam. [İLET toplanti: Ali ile görüşme | Ali]", "s", {"kaynak": "sohbet"})
    t2_, g2_ = n3["talimat_claude"]("Tamam. [İLET toplanti: X | 2026-10-28T12:00 | Ali]", "s", {"kaynak": "karsi", "karsi": True})
ok("saatsiz toplantı ve karşı tarafın isteği iş açmaz, etiket silinir", not g_ and not g2_ and t_ == "Tamam." and t2_ == "Tamam." and len(EY) == n_)
i2_ = n3["talimat_istem"]()
ok("istemde toplantı etiketi ve 'hatırlatma değildir'", "[İLET toplanti:" in i2_ and "hatırlatma değildir" in i2_)
print("talimat:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
