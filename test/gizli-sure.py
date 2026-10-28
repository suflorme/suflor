#!/usr/bin/env python3
# S91 küçük işleri (v0.89.0): gizli toplantı (/komut gizli — Gemini'ye metin gitmez, asistanlar toplantıda konuşmaz, toplantı bitince
# kendiliğinden kapanır), sesli süre uyarısı (ayar sure_duyuru — yürütücüde 15 dk, 5 dk, doldu, gündem kayması toplantıya söylenir; geç
# katılınca geçilmiş eşik söylenmez) ve fısıltıda strateji ipucu (soruya bağlı olmayan SÖYLE kartının fısıltısı en az 2 dk arayla).
# Aktarıcı yalıtılmış kopyadan modül olarak yüklenir; ses çalınmaz, Google'a gidilmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/gizli-sure.py      (kaldı → çıkış 1; ~10 sn)
import contextlib, datetime, importlib.util as u, io, json, os, shutil, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT = bos_port(8771)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-gs-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
kd = os.path.join(T, "kisilik"); os.makedirs(kd)
open(os.path.join(kd, "alfa.md"), "w").write("---\nad: ALFA\nses: gemini:Kore\n---\nToplantı kişiliği.\n")
json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "kisilik": os.path.join(kd, "alfa.md"),
           "toplantiya_ses": True, "toplanti_duyuru": True, "fisilti": True}, open(os.path.join(T, "ayar.json"), "w"))
os.environ.update(SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_TS_AYGIT="1", SUFLOR_TEST_HIZLI="1",
                  SUFLOR_TEST_GEMINI_ANAHTAR="deneme", SUFLOR_TEST_GEMINI_HOST="127.0.0.1:9", SUFLOR_TEST_GEMINI_SESSIZ="1")
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)]; os.chdir(T)
sp = u.spec_from_file_location("relay_t", os.path.join(T, "relay.py")); m = u.module_from_spec(sp)
with contextlib.redirect_stdout(io.StringIO()): sp.loader.exec_module(m)
def cikti(fn, *a, bekle=0.0, **k):
    o = io.StringIO()
    with contextlib.redirect_stdout(o):
        r = fn(*a, **k)
        if bekle: time.sleep(bekle)
    return r, o.getvalue()
def toplanti(): m.eklenti_nabiz({"platform": "teams", "sekme": "t1", "call": True, "panel": True, "rows": 1}, "Chrome/1"); m.toplanti_bak()  # Faz B: eklenti nabzı çağrıda = toplantı var (eski _cagri_son yok)

# 1) gizli toplantı — v0.89.1: tamamen steril, tekrar basana kadar
import threading, urllib.request
srv = m.ThreadingHTTPServer(("127.0.0.1", PORT), m.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
def post(yol, govde):
    r = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(govde).encode(), method="POST",
                               headers={"X-Suflor-Anahtar": m.CARD_KEY, "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(r, timeout=10).read())
    except urllib.error.HTTPError as e: return json.loads(e.read() or b"{}")
m.STATE["meeting"] = "Deneme Toplantı"; toplanti(); m.kanal_sessizlik = lambda: 2.0; m.SES["test_bit"] = 0
post("/ingest", {"meeting": {"title": "Deneme Toplantı"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Veli", "time": "00:01", "text": "gizli öncesi satır"}]})
md = os.path.join(m.BASE, m.STATE["file"]); once = open(md, encoding="utf-8").read()
bak("başta: Gemini izinli, asistanlar konuşur, satır yazılır", m.gemini_izinli(True) and m.asistan_toplanti() and "gizli öncesi satır" in once)
r = post("/komut", {"tur": "gizli"})
bak("/komut gizli açar (HTTP), günlük/dökümde yalnız işaret", r.get("ok") and m.gizli_acik() and r.get("gizli", {}).get("acik") and "**GİZLİ** | açıldı" in open(md, encoding="utf-8").read())
r = post("/ingest", {"meeting": {"title": "Deneme Toplantı"}, "source": "transcript", "entries": [{"id": "a/2", "speaker": "Veli", "time": "00:02", "text": "GİZLİ İÇERİK"}]})
r2 = post("/taslak", {"meeting": {"title": "Deneme Toplantı"}, "entries": [{"speaker": "Veli", "text": "GİZLİ TASLAK"}]})
r3 = post("/ses", {"pcm": "AAAA", "kanal": "karsi"}); r4 = post("/kanit", {"png": "iVBOR"})
bak("eklentinin satırı, taslağı, sesi, kanıtı 'ok' ile alınıp atılır (yeniden gönderilmesin)", all(x.get("ok") and x.get("gizli") for x in (r, r2, r3, r4)))
bak("döküme ve jsonl'e gizli içerik girmez", "GİZLİ İÇERİK" not in open(md, encoding="utf-8").read() and "GİZLİ TASLAK" not in json.dumps(m.taslak_view(), ensure_ascii=False))
red = [y for y in ("/bas-konus", "/ask", "/note", "/baslat", "/brifing", "/card", "/moderator", "/kanit-iste", "/eylem", "/girdi") if not (post(y, {"tur": "x", "text": "x", "kind": "not"}).get("err", "").startswith("Gizli"))]
bak(f"Konuş, soru, not, Başlat, brifing, kart, moderatör… reddedilir {red or ''}", not red)
r = post("/komut", {"tur": "ozet"}); bak("Ne diyeyim? (komut) reddedilir", r.get("gizli") and not r.get("ok"))
bak("Gemini yok, asistanlar konuşmaz, duyuru yok", not m.gemini_izinli(True) and not m.asistan_toplanti() and not m.duyuru_acik() and m.toplanti_duyuru("not", "X") is False)
r, _ = cikti(m.toplantiya_soyle, "Merhaba"); bak("toplantıya söyle reddedilir", r.get("ok") is False and "Gizli" in r.get("err", ""))
_, o = cikti(m._whisper_yaz, {"kanal": "karsi"}, "GİZLİ WHISPER"); bak("Whisper satırı yazılmaz (kuyrukta kalmış parça)", "GİZLİ WHISPER" not in open(md, encoding="utf-8").read())
m.FISILTI.update(son=0, ipucu=0); _, o = cikti(m.paylasim_bildir, True, "deneme"); bak("kendiliğinden kanıt (ekran paylaşımı) açılmaz", "KANIT" not in o and not m.STATE.get("paylasim", {}).get("acik") if isinstance(m.STATE.get("paylasim"), dict) else "KANIT" not in o)
m.EKLENTI.clear(); m.STATE.pop("masaustu", None); time.sleep(4)
bak("toplantı bitse de kendiliğinden kapanmaz", m.gizli_acik())
bak("durum diskte: aktarıcı yeniden başlasa da sürer", os.path.exists(m.GIZLI_FP))
v = m.cards_view(); bak("pano verisinde gizli görünür", (v.get("gizli") or {}).get("acik") is True)
toplanti(); r = post("/komut", {"tur": "gizli"})
bak("ikinci basış kapatır, satırlar yeniden yazılır", r.get("ok") and not m.gizli_acik() and m.gemini_izinli(True) and not os.path.exists(m.GIZLI_FP))
post("/ingest", {"meeting": {"title": "Deneme Toplantı"}, "source": "transcript", "entries": [{"id": "a/3", "speaker": "Veli", "time": "00:03", "text": "gizli sonrası satır"}]})
bak("kapandıktan sonra satır yazılır, aradaki içerik yok", "gizli sonrası satır" in open(os.path.join(m.BASE, m.STATE["file"]), encoding="utf-8").read())
pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read()
bak("panoda ve mini panoda 🔒 düğmesi ve uyarı şeridi", "id=gz " in pano and "id=mgz " in pano and pano.count("gizliCiz(") == 3 and "tur:\"gizli\"" in pano and "gzb" in pano)
izle = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read()
bak("izle: gizlide tek GİZLİ TOPLANTI satırı, sonra olay yok", 'emit("GİZLİ TOPLANTI: kullanıcı açtı' in izle and "time.sleep(2); continue" in izle)

# 2) sesli süre uyarısı
def gundem(kalan_dk, rol="yurutucu", n=4, bitti=0, bas_dk=60):
    now = datetime.datetime.now()
    json.dump({"title": "Deneme", "rol": rol, "baslangic": (now - datetime.timedelta(minutes=bas_dk)).isoformat(timespec="seconds"),
               "bitis": (now + datetime.timedelta(minutes=kalan_dk)).isoformat(timespec="seconds"), "items": [f"M{i}" for i in range(n)]}, open(os.path.join(m.BASE, "agenda.json"), "w"))
    m.STATE["agenda_ticks"] = {str(i): True for i in range(bitti)}; m.AG["mtime"] = None
sdb = m.sure_duyuru_bak; m.sure_duyuru_bak = lambda: None  # arka plandaki nöbet eşikleri tüketmesin; deneme doğrudan çağırır
toplanti(); m.AYAR["sure_duyuru"] = True; m.SURE_DUY.update(toplanti=None, esik=set())
gundem(10)
bak("geç katılınca geçilmiş 15 dk eşiği söylenmez", sdb() is None and "15" in m.SURE_DUY["esik"])
m.SURE_DUY.update(toplanti=None, esik=set()); gundem(20, bitti=3); sdb()
gundem(14, bitti=3); r = sdb()
bak(f"15 dk eşiği: {r}", r and r[0] == "15" and "Kalan süre 14 dakika" in r[1] and "1 madde açık" in r[1])
bak("aynı eşik ikinci kez söylenmez", sdb() is None)
gundem(4, bitti=4); r = sdb(); bak(f"5 dk eşiği: {r}", r and r[0] == "5" and r[1] == "Son beş dakika.")
gundem(-1, bitti=4); r = sdb(); bak(f"süre doldu: {r}", r and r[0] == "bitti")
m.SURE_DUY.update(toplanti=None, esik=set()); gundem(40, n=6, bitti=0, bas_dk=50); sdb()
toplanti(); m.SURE_DUY["kayma_son"] = time.time() - 10; r = sdb()
bak(f"gündem kayması (≥ 2 madde geride): {r}", r and r[0] == "kayma" and "gerisindeyiz" in r[1])
bak("kayma aralık dolmadan tekrar yok", sdb() is None)
m.SURE_DUY.update(toplanti=None, esik=set()); gundem(20, rol="katilimci"); sdb(); gundem(14, rol="katilimci")
bak("katılımcı rolünde süre söylenmez", sdb() is None)
m.SURE_DUY.update(toplanti=None, esik=set()); m.AYAR["sure_duyuru"] = False; gundem(20); sdb(); gundem(14)
bak("ayar kapalıyken söylenmez (eşik yine işaretlenir)", sdb() is None and "15" in m.SURE_DUY["esik"])
toplanti(); m.SES["test_bit"] = 0; m.AYAR["sure_duyuru"] = True; m.AYAR["toplanti_duyuru"] = False; m.DUYURU["son"] = time.time()
r, o = cikti(m.toplanti_duyuru, "sure", metin="Son beş dakika.", bekle=1.5)
bak("süre duyurusu toplanti_duyuru kapalıyken de ve 60 sn aralığına takılmadan okunur", r is True and "DUYURU: sure · Son beş dakika." in o)
m.GIZLI["acik"] = True; bak("gizlide süre duyurusu yok", m.sure_duyuru_acik() is False); m.GIZLI["acik"] = False
# v0.92.0: gece yarısını geçen toplantı — yalın "HH:MM" saat şimdiye en yakın güne düşer
class _Saat(datetime.datetime):
    SIMDI = None
    @classmethod
    def now(cls, tz=None): return cls.SIMDI
def saat_dene(simdi, bas, bit):
    _Saat.SIMDI = simdi; eski = m.datetime.datetime; m.datetime.datetime = _Saat
    try:
        json.dump({"title": "Gece", "rol": "yurutucu", "baslangic": bas, "bitis": bit, "items": ["A", "B"]}, open(os.path.join(m.BASE, "agenda.json"), "w"))
        m.STATE["agenda_ticks"] = {}; m.AG["mtime"] = None; return m.sure_view()
    finally: m.datetime.datetime = eski
g = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 40))
v = saat_dene(g, "23:30", "00:30"); bak(f"23.40'ta 23:30–00:30 toplantı: kalan 50 dk ({v and v.get('kalan_dk')})", v and v["kalan_dk"] == 50 and v.get("toplam_dk") == 60)
v = saat_dene(g + datetime.timedelta(minutes=30), "23:30", "00:30"); bak(f"00.10'da aynı toplantı: kalan 20 dk, geçen 40 ({v and (v.get('kalan_dk'), v.get('gecen_dk'))})", v and v["kalan_dk"] == 20 and v.get("gecen_dk") == 40)
v = saat_dene(g.replace(hour=14, minute=10), "14:00", "15:00"); bak(f"gündüz toplantısı değişmedi ({v and v.get('kalan_dk')})", v and v["kalan_dk"] == 50 and v.get("gecen_dk") == 10)
ayar_k = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
bak("ayar sure_duyuru aktarıcıda ve ⚙ Ayarlar'da", '"sure_duyuru": ("bool", False, None)' in ayar_k and "['sure_duyuru','bool'" in pano)

# 3) fısıltıda strateji ipucu
m.kulaklik = lambda: True; m._kullanici_konusuyor = lambda: False; toplanti(); m.FISILTI.update(son=0, ipucu=0)
_, o = cikti(m.fisilti_kart, {"kind": "soyle", "text": "Bütçeyi şimdi sorun", "fisilti": "Bütçeyi şimdi sor"}, bekle=0.3)
bak("soruya bağlı olmayan SÖYLE fısıltısı okunur", "FISILTI (deneme): Bütçeyi şimdi sor" in o)
m.FISILTI["son"] = 0
_, o = cikti(m.fisilti_kart, {"kind": "soyle", "text": "Tarihe itiraz edin", "fisilti": "Tarihe itiraz et"}, bekle=0.3)
bak("ikinci ipucu 2 dk dolmadan okunmaz", "ipucu" in o and "dolmadı" in o and "Tarihe" not in o.split("FISILTI (deneme)")[-1] if "FISILTI (deneme)" in o else "dolmadı" in o)
_, o = cikti(m.fisilti_kart, {"kind": "dur", "text": "Ekranda şifre var"}, bekle=0.3)
bak("DUR fısıltısı ipucu sınırına girmez", "FISILTI (deneme): Ekranda şifre var" in o)
m.FISILTI["son"] = 0
_, o = cikti(m.fisilti_kart, {"kind": "soyle", "text": "Cevap", "fisilti": "Yüz yirmi bin", "reply_to": "q1"}, bekle=0.3)
bak("soru cevabının fısıltısı ipucu sınırına girmez", "FISILTI (deneme): Yüz yirmi bin" in o)
for f in ("TOPLANTI-KURALLARI.md",):
    bak(f"{f}: strateji ipucu ve sure_duyuru kuralı", "**Strateji ipucu:**" in open(os.path.join(KOD, f), encoding="utf-8").read() and "sure_duyuru" in open(os.path.join(KOD, f), encoding="utf-8").read())

shutil.rmtree(T, ignore_errors=True)
print("GEÇTİ" if not hata else f"KALDI ({len(hata)}): " + "; ".join(hata)); sys.exit(1 if hata else 0)
