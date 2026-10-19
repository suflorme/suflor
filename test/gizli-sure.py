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
def toplanti(): m.STATE["_cagri_son"] = time.time()

# 1) gizli toplantı
m.STATE["meeting"] = "Deneme Toplantı"; toplanti(); m.kanal_sessizlik = lambda: 2.0; m.SES["test_bit"] = 0
bak("başta: Gemini toplantıya izinli, asistanlar konuşur, duyuru açık", m.gemini_izinli(True) and m.asistan_toplanti() and m.duyuru_acik() and m.otonom_acik())
_, o = cikti(m.komut_uygula, "gizli", "", None)
bak("/komut gizli açar, günlükte GİZLİ", m.gizli_acik() and "GİZLİ: açıldı" in o and "🔒" in m.STATE["komut"]["metin"])
bak("gizlide Gemini hiç yok (toplantıya da)", not m.gemini_izinli(True) and not m.gemini_izinli() and m.kisilik_sesi(toplantiya=True)[0] != "gemini")
bak("gizlide asistanlar toplantıda konuşmaz, otonom kapalı", not m.asistan_toplanti() and not m.otonom_acik())
bak("gizlide duyuru yok", not m.duyuru_acik() and m.toplanti_duyuru("not", "X") is False)
r, _ = cikti(m.toplantiya_soyle, "Merhaba")
bak("gizlide toplantıya söyle reddedilir", r.get("ok") is False and "Gizli" in r.get("err", ""))
r, _ = cikti(m.moderator_basla, "toplantıyı sen yönet")
bak("gizlide moderatör başlamaz", r.get("ok") is False and "Gizli" in r.get("err", ""))
v = m.cards_view() if hasattr(m, "cards_view") else None
bak("pano verisinde gizli görünür", (v or {}).get("gizli", {}).get("acik") is True if v else "gizli" in open(os.path.join(KOD, "aktarici", "eylem.py")).read())
_, o = cikti(m.komut_uygula, "gizli", "", None)
bak("ikinci basış kapatır", not m.gizli_acik() and "kapandı (kullanıcı)" in o and m.gemini_izinli(True))
_, o = cikti(m.komut_uygula, "gizli", "", None); m.STATE["_cagri_son"] = 0; m.STATE.pop("masaustu", None)
o = io.StringIO()
with contextlib.redirect_stdout(o):
    son = time.time() + 6
    while m.gizli_acik() and time.time() < son: time.sleep(0.2)
bak(f"toplantı yokken {m.GIZLI_BOS_SN} sn sonra kendiliğinden kapanır", not m.gizli_acik() and "toplantı bitti" in o.getvalue())
pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read()
bak("panoda ve mini panoda 🔒 düğmesi", "id=gz " in pano and "id=mgz " in pano and pano.count("gizliCiz(") == 3 and "tur:\"gizli\"" in pano)

# 2) sesli süre uyarısı
def gundem(kalan_dk, rol="yurutucu", n=4, bitti=0, bas_dk=60):
    now = datetime.datetime.now()
    json.dump({"title": "Deneme", "rol": rol, "baslangic": (now - datetime.timedelta(minutes=bas_dk)).strftime("%H:%M"),
               "bitis": (now + datetime.timedelta(minutes=kalan_dk)).strftime("%H:%M"), "items": [f"M{i}" for i in range(n)]}, open(os.path.join(m.BASE, "agenda.json"), "w"))
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
m.SURE_DUY["kayma_son"] = time.time() - 10; r = sdb()
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
