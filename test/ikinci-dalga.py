#!/usr/bin/env python3
# İkinci dalga (9 Kasım): asistanın KAYIT komutları — sahibine taslak (kayit_taslak: e-posta/Teams), sesle gündeme ekleme (gundem_ekle), sesle toplantı başlat/bitir
# (toplanti_baslat, toplanti_bitir). Hepsi onaylı; hiçbiri bir şey göndermez. İşlev düzeyinde: aktarici/notlar.py (+ izin.py, brifing-ses.py'nin ilgili dilimleri) sahte ad alanında
# çalışır; kayıtlar gerçek yapi.py + geçici karar grafı; Mail/Teams açılmaz (TASLAK_ACICI, SUFLOR_TEST_BASLAT).
# aktarici/notlar.py (kayit_taslak, gundem_ekle, toplanti_*), izin.py (izin_iste), brifing-ses.py (soru_baslat, KAYIT_FIIL_OZEL) değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ikinci-dalga.py      (kaldı → çıkış 1)
import datetime, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.parse
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = os.path.realpath(tempfile.mkdtemp(prefix="dalga-")); d = os.path.join(T, "canli"); os.makedirs(d); HATA = []; AT = chr(64)
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
os.environ["SUFLOR_TEST_BASLAT"] = "1"
ayar_yol = os.path.join(T, "ayar.json"); json.dump({"ad": "Deniz T", "alan": "Deneme", "eposta_adres": "deniz.t" + AT + "firma.test"}, open(ayar_yol, "w")); os.environ["SUFLOR_AYAR"] = ayar_yol
import yapi
EK = "2026-11-05-0900-Ek-Toplanti"
yapi.graf_yaz(d, {"baslik": "Ek toplantı", "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": [
    {"tur": "karar", "metin": "Sunucu taşınacak", "kim": "Can Örnek", "saat": "10:00:00", "netlik": "ortuk"},
    {"tur": "is", "metin": "Raporu hazırla", "sahip": "Ayla Kurgu", "tarih": "2026-11-20"}, {"tur": "is", "metin": "Kendi işim", "sahip": "Deniz T"},
    {"tur": "is", "metin": "Sahipsiz iş"}, {"tur": "is", "metin": "Adresi olmayan kişinin işi", "sahip": "Burak Adressiz"}]}]}, EK + ".md")
import sqlite3
def db(sql): c = sqlite3.connect(os.path.join(d, "karar-grafi.sqlite")); r = c.execute(sql).fetchall(); c.close(); return r
def kid(m): r = db(f"SELECT id, tur FROM kayit WHERE metin LIKE '{m}%'")[0]; return ("k" if r[1] == "karar" else "q" if r[1] == "soru" else "s") + str(r[0])
KR, IS_A, IS_K, IS_S, IS_B = (kid(m) for m in ("Sunucu", "Raporu", "Kendi işim", "Sahipsiz", "Adresi olmayan"))
simdi = datetime.datetime.now().astimezone()
def ev(i, baslik, sa, kisi=3, **ek): return dict({"id": i, "baslik": baslik, "baslangic": (simdi + datetime.timedelta(hours=sa)).isoformat(), "bitis": (simdi + datetime.timedelta(hours=sa + 1)).isoformat(), "kisi_sayisi": kisi,
                                                  "katilimcilar": ["Ayla Kurgu", "Deniz T"], "katilimci_eposta": []}, **ek)
TAKVIM = [ev("e1", "Haftalık Operasyon", 3), ev("e2", "Executive Planning Toplantısı", 26), ev("e3", "Executive Planning Toplantısı", 120), ev("e4", "Executive Review", 50), ev("e5", "Yarın Sabah Sync", 30)]
AYLA = "ayla.kurgu" + AT + "firma.test"
KIM = {"Ayla Kurgu": {"eposta": AYLA}, "Can Örnek": {"eposta": "can.ornek" + AT + "firma.test"}}
izin_iste_log, TOP = [], {"aktif": None}; karar_sira = ["onaylandi"]; kayit_log = {"bitir": [], "baslat": []}
import threading as _th
ns = {"AYAR": {"ad": "Deniz T"}, "_t": lambda a, b: a, "re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": _th, "subprocess": subprocess, "urllib": urllib, "BASE": d, "LOCK": _th.Lock(), "KONUS": {},
      "_yapi_mod": lambda: yapi, "_kem_takvim": lambda: TAKVIM, "_kem_kimlik": lambda ad, tam: KIM.get(ad, {"eposta": None}), "_izin_kayit": lambda o: None, "print": lambda *a, **k: None}
import baglayici as _bag; ns["_baglayici_mod"] = lambda: _bag
def izin_iste(tur, ne, ayrinti=None, sesli=True, oturum=False, sure_sn=None, toplantida_sesli=False):
    izin_iste_log.append({"tur": tur, "ne": ne, "ayrinti": ayrinti, "sesli": sesli, "toplantida_sesli": toplantida_sesli}); return f"i{len(izin_iste_log)}"
ns["izin_iste"] = izin_iste; ns["izin_bekle"] = lambda iid: karar_sira[0]
ns["toplanti_durum"] = lambda: (TOP["aktif"] or {}).get("durum") or "bos"; ns["TOPLANTI"] = TOP
ns["toplanti_bitir"] = lambda neden, dosya=None: (kayit_log["bitir"].append(neden), True)[1]
def baslat(p): kayit_log["baslat"].append(p); return {"ok": True}
ns["baslat"] = baslat
exec(open(os.path.join(KOD, "aktarici", "notlar.py"), encoding="utf-8").read(), ns)
dog, uyg, etk = ns["kayit_dogrula"], ns["kayit_uygula"], ns["kayit_etiketleri"]
def acici(): a = list(ns["TASLAK_ACICI"]); ns["TASLAK_ACICI"].clear(); return a
def olaylar(k): return db(f"SELECT tur, kaynak FROM olay WHERE kayit_id = (SELECT kayit_id FROM kayit WHERE id = {k[1:]})")
try:
    # --- 1) kayit_taslak ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    ok("komutlar izin listesinde ve asistanın kuralında (iki dil)", all(k in ns["KAYIT_KOMUTLAR"] and k in ns["IKINCI_KURAL"]["tr"] and k in ns["IKINCI_KURAL"]["en"] for k in ("kayit_taslak", "gundem_ekle", "toplanti_baslat", "toplanti_bitir")) and "kayit_taslak" in ns["kayit_kural"]())
    ok("istek kalıbı: «Ayla'ya hatırlatma yaz», «gündemine ekle», «toplantıyı bitir/başlat» kuralı yükler", all(ns["KAYIT_ISTEK_RX"].search(s) for s in ("Ayla'ya bu iş için hatırlatma yaz", "Executive Planning gündemine ekle", "toplantıyı bitir", "toplantıyı başlat", "Teams'ten mesaj hazırla", "add it to the agenda", "end the meeting")))
    h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "eposta", "govde": "Merhaba Ayla,\nRapor ne durumda?"})
    ok("e-posta: alıcı kaydın sahibi (kimlik katmanından), konu kayıttan türer, onay özeti; henüz açılmadı", e is None and h["kime"] == [AYLA] and h["konu"].startswith("Hatırlatma: Raporu hazırla") and "Ayla Kurgu" in h["ozet"] and AYLA in h["ozet"] and not acici())
    okk, ne = uyg({"komut": "kayit_taslak", "arg": {"id": IS_A, "kanal": "eposta", "govde": "Merhaba Ayla,\nRapor ne durumda?"}}); a = acici()
    ok("onaydan sonra tek taslak açılır (tür mailto, alıcı sahip), gönderme yok, kayda «taslak hazırlandı» olayı (asistan)", okk and len(a) == 1 and a[0]["kime"] == [AYLA] and a[0]["tur"] == "mailto" and ("taslak_hazirlandi", "asistan") in olaylar(IS_A))
    okk, ne = uyg({"komut": "kayit_taslak", "arg": {"id": IS_A, "kanal": "teams", "govde": "Ayla, rapor için bir güncelleme var mı? **Not:** yarın toplantı"}}); a = acici()
    u = a[0]["url"] if a else ""
    ok("Teams: https derin bağlantısı, users=sahibin adresi, mesaj önceden yazılı (markdown süsü yok), tür teams", okk and u.startswith("https://teams.microsoft.com/l/chat/0/0?users=" + urllib.parse.quote(AYLA, safe="@.+-_") + "&message=") and urllib.parse.unquote(u.split("message=")[1]) == "Ayla, rapor için bir güncelleme var mı? Not: yarın toplantı" and a[0]["tur"] == "teams")
    h, e = dog("kayit_taslak", {"id": IS_B, "kanal": "teams", "govde": "Merhaba"})
    okk, ne = uyg({"komut": "kayit_taslak", "arg": {"id": IS_B, "kanal": "teams", "govde": "Merhaba"}}); a = acici()
    ok("sahibin adresi bulunamazsa alıcısız (özette «alıcısız»; Teams bağlantısında users yok)", e is None and "alıcısız" in h["ozet"] and okk and a and a[0]["kime"] == [] and "users=" not in a[0]["url"] and a[0]["url"].startswith("https://teams.microsoft.com/l/chat/0/0?message="))
    h, e = dog("kayit_taslak", {"id": IS_S, "kanal": "eposta", "konu": "Konu", "govde": "Metin"}); ok("sahipsiz kayıt: alıcısız e-posta taslağı kurulur", e is None and h["kime"] == [] and h["konu"] == "Konu")
    h, e = dog("kayit_taslak", {"id": IS_K, "kanal": "eposta", "govde": "Metin"}); ok("kayıt kullanıcının kendisininse reddedilir (kendine taslak yazılmaz)", h is None and "senin" in e)
    h, e = dog("kayit_taslak", {"id": KR, "kanal": "teams", "govde": "Merhaba"}); ok("karar: onaylayan atanmamışsa alıcısız taslak kurulur", e is None and h["kime"] == [])
    yapi.ata(d, yapi.ortak_kayit(d, KR)["kayit_id"], {"onaylayan": {"ad": "Can Örnek", "eposta": ""}}, None, "eylem"); h, e = dog("kayit_taslak", {"id": KR, "kanal": "teams", "govde": "Merhaba"})
    ok("karar: alıcı onaylayan (adresi kimlik katmanından)", e is None and h["kime"] == ["can.ornek" + AT + "firma.test"])
    h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "sms", "govde": "x"}); ok("kanal eposta/teams dışı reddedilir", h is None and "kanal" in e)
    h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "teams", "govde": "x" * 1501}); ok("Teams mesajı 1500 karakteri aşarsa reddedilir (sessizce kesilmez)", h is None and "uzun" in e)
    h, e = dog("kayit_taslak", {"id": "s99999", "kanal": "teams", "govde": "x yy"}); ok("olmayan kayıt reddedilir", h is None and "yok" in e)
    h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "teams"}); ok("metin boşsa reddedilir (metni asistan yazmalı)", h is None and "boş" in e)
    h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "teams", "govde": "Selam", "fazla": "x"}); ok("fazla argüman reddedilir", h is None and "uymuyor" in e)
    yapi.kayit_durum(d, IS_A, "yapildi", None, "eylem"); h, e = dog("kayit_taslak", {"id": IS_A, "kanal": "teams", "govde": "Selam"}); ok("kapalı iş için taslak yazılmaz", h is None and "kapalı" in e); yapi.kayit_durum(d, IS_A, "acik", None, "eylem")
    # onaysız açılmaz: etiket → kart (izin_iste) sunulur, Reddet → açılmaz
    karar_sira[0] = "reddedildi"; izin_iste_log.clear()
    tur = {"kaynak": "yazili", "yazili": True}; cev = etk('Tamam. [KAYIT: {"komut": "kayit_taslak", "arg": {"id": "' + IS_A + '", "kanal": "teams", "govde": "Selam Ayla"}, "neden": "istedi"}]', tur); time.sleep(0.4)
    ok("etiket onay kartı açar, etiket cevapta yok; reddedilince hiçbir pencere açılmaz", len(izin_iste_log) == 1 and izin_iste_log[0]["ayrinti"]["komut"] == "kayit_taslak" and "[KAYIT" not in cev and "Onayını bekliyor" in cev and not acici())
    karar_sira[0] = "onaylandi"
    # --- 2) gundem_ekle ----------------------------------------------------------------------------------------------------------------------------------------------------------------
    h, e = dog("gundem_ekle", {"id": IS_A}); ok("toplanti verilmezse takvimdeki bir sonraki toplantı (en yakın)", e is None and h["baslik"] == "Haftalık Operasyon" and h["etkinlik"] == "e1" and "gündemine eklenir" in h["ozet"])
    h, e = dog("gundem_ekle", {"id": IS_A, "toplanti": "Executive Planning"}); ok("adla eşleşme: aynı başlıklı tekrar eden toplantıda en yakın olan", e is None and h["etkinlik"] == "e2")
    h, e = dog("gundem_ekle", {"id": IS_A, "toplanti": "Executive"}); ok("farklı başlıklı birden çok toplantı eşleşirse reddedilir ve adaylar söylenir (belirsizde sorar)", h is None and "hangisi" in e and "Executive Planning" in e and "Executive Review" in e)
    h, e = dog("gundem_ekle", {"id": IS_A, "toplanti": "Yok Böyle Toplantı"}); ok("takvimde olmayan ad reddedilir", h is None and "yok" in e)
    h, e = dog("gundem_ekle", {"id": IS_A, "metin": "x yyy"}); ok("id ve metin birlikte verilirse reddedilir", h is None and "ikisi birden" in e)
    h, e = dog("gundem_ekle", {}); ok("ikisi de yoksa reddedilir", h is None)
    TAKVIM_ESKI = list(TAKVIM); TAKVIM[:] = []; h, e = dog("gundem_ekle", {"id": IS_A}); ok("takvimde uygun toplantı yoksa reddedilir", h is None and "yaklaşan" in e); TAKVIM[:] = TAKVIM_ESKI
    n0 = db("SELECT COUNT(*) FROM olay")[0][0]
    okk, ne = uyg({"komut": "gundem_ekle", "arg": {"id": IS_A, "toplanti": "Executive Planning"}})
    g = yapi.ortak_kayit(d, IS_A).get("gundem") or {}
    ok("onaydan sonra kayıt o toplantının gündemine eklenir (panodaki yolla, olay kaynağı asistan)", okk and g.get("etkinlik") == "e2" and ("gundeme_eklendi", "asistan") in olaylar(IS_A) and db("SELECT COUNT(*) FROM olay")[0][0] == n0 + 1)
    h, e = dog("gundem_ekle", {"id": IS_A, "toplanti": "Executive Planning"}); ok("zaten o gündemdeyse reddedilir", h is None and "zaten" in e)
    n0 = db("SELECT COUNT(*) FROM kayit")[0][0]; okk, ne = uyg({"komut": "gundem_ekle", "arg": {"metin": "Bütçe revizyonu konuşulsun", "toplanti": "Haftalık"}})
    yeni = db("SELECT id FROM kayit WHERE metin = 'Bütçe revizyonu konuşulsun'")
    ok("metin verilirse önce iş kaydı açılır, sonra gündeme eklenir (özette iş kaydı olduğu yazılır)", okk and db("SELECT COUNT(*) FROM kayit")[0][0] == n0 + 1 and yeni and (yapi.ortak_kayit(d, "s" + str(yeni[0][0])).get("gundem") or {}).get("etkinlik") == "e1" and "iş kaydı" in dog("gundem_ekle", {"metin": "Başka madde", "toplanti": "Haftalık"})[0]["ozet"])
    ns["gizli_acik"] = lambda: True; h, e = dog("gundem_ekle", {"id": IS_B}); ok("gizli kipte gündeme ekleme reddedilir", h is None and "gizli" in e); ns.pop("gizli_acik")
    # --- 3) toplantı bitir / başlat ----------------------------------------------------------------------------------------------------------------------------------------------------
    TOP["aktif"] = None; h, e = dog("toplanti_bitir", {}); ok("toplantı yokken bitir kibarca reddedilir", h is None and "süren" in e)
    okk, ne = uyg({"komut": "toplanti_bitir", "arg": {}}); ok("toplantı yokken onay gelse de bitirilmez (uygulamada yeniden denetlenir)", okk is False and not kayit_log["bitir"])
    TOP["aktif"] = {"durum": "bitiyor", "ad": "X"}; h, e = dog("toplanti_bitir", {}); ok("toplantı zaten bitiyorsa reddedilir", h is None and "bitiyor" in e)
    TOP["aktif"] = {"durum": "suruyor", "ad": "Haftalık Operasyon"}; h, e = dog("toplanti_bitir", {}); ok("toplantı sürerken bitir kurulur, özette toplantı adı", e is None and "Haftalık Operasyon" in h["ozet"])
    h, e = dog("toplanti_bitir", {"x": "y"}); ok("bitir argüman almaz", h is None)
    karar_sira[0] = "reddedildi"; izin_iste_log.clear(); kayit_log["bitir"].clear()
    cev = etk('Soruyorum. [KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "Kullanıcı bitir dedi"}]', {"kaynak": "bas", "sesli": True, "toplantida": True}); time.sleep(0.4)
    ok("toplantı sürerken sesli tur: kart sesli (toplantida_sesli) açılır; «hayır» → toplantı bitirilmez", len(izin_iste_log) == 1 and izin_iste_log[0]["sesli"] is True and izin_iste_log[0]["toplantida_sesli"] is True and not kayit_log["bitir"] and "Onayını bekliyor" in cev)
    karar_sira[0] = "onaylandi"; izin_iste_log.clear(); ns["KAYIT_SORULAN"].clear()
    etk('[KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "x"}]', {"kaynak": "bas", "sesli": True, "toplantida": True}); time.sleep(0.5)
    ok("açık «evet» (onay) gelince toplantı bir kez bitirilir", kayit_log["bitir"] == ["elle bitirildi (sesle)"])
    izin_iste_log.clear(); karar_sira[0] = "reddedildi"; ns["KAYIT_SORULAN"].clear()
    etk('[KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "x"}]', {"kaynak": "yazili", "yazili": True}); ns["KAYIT_SORULAN"].clear()
    ok("yazılı turda kart sesli değildir (yalnız panoda tık)", len(izin_iste_log) == 1 and izin_iste_log[0]["sesli"] is False and not izin_iste_log[0]["toplantida_sesli"])
    izin_iste_log.clear(); ns["KAYIT_SORULAN"].clear()
    etk('[KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "x"}]', {"kaynak": "bas", "sesli": False, "toplantida": True})
    ok("toplantıda kulaklık yoksa (tur.sesli yok) sesli sorulmaz, yalnız kart", len(izin_iste_log) == 1 and izin_iste_log[0]["sesli"] is False)
    izin_iste_log.clear(); ns["KAYIT_SORULAN"].clear()
    etk('[KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "x"}]', {"kaynak": "bas", "sesli": True, "karsi": "Ali"})
    ok("karşı tarafın sorusunda bitirme önerisi yok sayılır", not izin_iste_log)
    ns["gizli_acik"] = lambda: True; h, e = dog("toplanti_bitir", {}); ok("gizli kipte de bitirme çalışır ama toplantı adı yazılmaz", e is None and "Haftalık" not in h["ozet"])
    ns["KAYIT_SORULAN"].clear(); izin_iste_log.clear(); karar_sira[0] = "reddedildi"
    cev = etk('[KAYIT: {"komut": "kayit_taslak", "arg": {"id": "' + IS_A + '", "kanal": "teams", "govde": "Selam"}, "neden": "x"}] [KAYIT: {"komut": "toplanti_bitir", "arg": {}, "neden": "x"}]', {"kaynak": "bas", "sesli": True, "toplantida": True}); time.sleep(0.3)
    ok("gizli kipte yalnız toplanti_bitir/baslat geçer, içerik yazan komutlar yok sayılır", len(izin_iste_log) == 1 and izin_iste_log[0]["ayrinti"]["komut"] == "toplanti_bitir" and "Gizli kip açık" in cev); ns.pop("gizli_acik")
    # başlat
    TOP["aktif"] = {"durum": "suruyor", "ad": "Haftalık Operasyon"}; h, e = dog("toplanti_baslat", {}); ok("toplantı sürerken başlat reddedilir (zaten sürüyor)", h is None and "sürüyor" in e)
    TOP["aktif"] = None; TAKVIM[:] = [ev("eS", "Şimdiki Sync", -0.1), ev("eG", "Geç Toplantı", 5)]
    h, e = dog("toplanti_baslat", {}); ok("başlat: takvimde şimdi başlayan toplantı varsa onunla (özette ad, olay kimliği)", e is None and h["olay"] == "eS" and "Şimdiki Sync" in h["ozet"])
    okk, ne = uyg({"komut": "toplanti_baslat", "arg": {}}); ok("onaydan sonra elle Başlat yolu (baslat) bir kez çağrılır, olay kimliğiyle", okk and kayit_log["baslat"] == [{"olay": "eS"}])
    kayit_log["baslat"].clear(); TAKVIM[:] = []; h, e = dog("toplanti_baslat", {}); okk, ne = uyg({"komut": "toplanti_baslat", "arg": {}})
    ok("takvimde yakın toplantı yoksa konusuz Başlat (adı Başlat kendisi verir)", e is None and okk and kayit_log["baslat"] == [{}])
    kayit_log["baslat"].clear(); okk, ne = uyg({"komut": "toplanti_baslat", "arg": {"konu": "Deneme Sohbet"}}); ok("konu verilirse Başlat o konuyla", okk and kayit_log["baslat"] == [{"konu": "Deneme Sohbet"}])
    # --- 4) sesli onay katmanı (izin.py + brifing-ses.py dilimleri) ------------------------------------------------------------------------------------------------------------------------
    iz = open(os.path.join(KOD, "aktarici", "izin.py"), encoding="utf-8").read(); soru_log = []; top_v = [True]
    ns3 = {"os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": {}, "BASE": d, "LOCK": threading.Lock(), "_t": lambda a, b: a, "EYLEM_TUR": {}, "EYLEM_SORU": {}, "EYLEM_FIIL": {},
           "eylem_ekle": lambda o: dict(o, id="e1", durum="bekliyor"), "_eylem_yama": lambda *a, **k: None, "add_card": lambda c: None, "kart_bildir": lambda: None, "write": lambda *a, **k: None,
           "toplanti_var": lambda: top_v[0], "soru_baslat": lambda ids, zorla=False: soru_log.append((ids, zorla)), "print": lambda *a, **k: None}
    exec(iz, ns3); ns3["izin_iste"]("kayit", "x", {"komut": "toplanti_bitir"}, sesli=True); n_ = len(soru_log)
    ns3["izin_iste"]("kayit", "x", {"komut": "toplanti_bitir"}, sesli=True, toplantida_sesli=True)
    ok("izin_iste: toplantıda normalde sesli soru yok; toplantida_sesli ile zorla sorulur; toplantı dışında eskisi gibi", n_ == 0 and soru_log == [(["e1"], True)] and (top_v.__setitem__(0, False) or ns3["izin_iste"]("kayit", "x", {}, sesli=True) or soru_log[-1] == (["e1"], False)))
    bs = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
    dilim = bs[bs.index("def _izin_turu(x):"):bs.index("def _yeniden_sor(")]; dil2 = bs[bs.index("def soru_baslat("):bs.index("def soru_sonraki(")]
    ns4 = {"json": json, "re": re, "datetime": datetime, "AYAR": {"ad": "Deniz T", "konusma": True}, "ARAYUZ_DILI": "tr", "_t": lambda a, b: a, "LOCK": threading.Lock(), "SORU": {"liste": [], "aktif": None},
           "EYLEM_FIIL": {"kayit_izin": (("Kayda yazayım mı?", "Yazıyorum.", "Peki, yazmıyorum."), ("Shall I write it to the records?", "Writing it.", "Okay, not writing it.")), "diger": (("Yapayım mı?", "Yapıyorum.", "Peki, yapmıyorum."), ("", "", ""))},
           "_cumle": lambda x: " ".join(str(x or "").split()), "_ses_serbest": lambda: False, "soru_sonraki": lambda: ns4.setdefault("sonraki", 0) or ns4.__setitem__("sonraki", ns4["sonraki"] + 1)}
    exec(dilim, ns4); exec(dil2, ns4); ns4["kullanici_ilk_ad"] = lambda: "Deniz"
    x_ = {"id": "e9", "tur": "izin", "baslik": "Kayda yazayım mı? toplantı bitirilir", "ayrinti": json.dumps({"izin": "kayit", "komut": "toplanti_bitir", "ozet": "«X» toplantısı bitirilir", "neden": "bitir dedi"})}
    ok("sesli soru metni: «Deniz, toplantıyı bitireyim mi?» (kayda yazayım mı değil); onay/red sözleri kendi cümlesi", ns4["_soru_metni"](x_) == "Deniz, toplantıyı bitireyim mi?" and ns4["_fiil_x"](x_)[1] == "Bitiriyorum." and ns4["_fiil_x"](x_)[2] == "Peki, bitirmiyorum.")
    x2 = dict(x_, ayrinti=json.dumps({"izin": "kayit", "komut": "karar_onayla", "ozet": "«Y» onaylanır", "neden": "n"}))
    ok("diğer kayıt kartlarının sorusu değişmedi (Kayda yazayım mı?)", ns4["_fiil_x"](x2)[0] == "Kayda yazayım mı?" and "Kayda yazayım mı?" in ns4["_soru_metni"](x2))
    ns4["soru_baslat"](["e9"]); a0 = ns4["SORU"]["liste"][:]; ns4["soru_baslat"](["e9"], zorla=True)
    ok("soru_baslat: toplantıda (ses serbest değil) soru sorulmaz; zorla verilirse sorulur", a0 == [] and ns4["SORU"]["liste"] == ["e9"] and ns4.get("sonraki") == 1)
    ok("hiçbir yerde gönderme komutu yok (e-posta/Teams yeni kodda yalnız açar)", not re.search(r"\bsend_message|outlook_send|\bsend_draft|osascript|NSAppleScript|\bsmtplib|\.sendmail", open(os.path.join(KOD, "aktarici", "notlar.py"), encoding="utf-8").read()))
finally: shutil.rmtree(T, ignore_errors=True)
print("ikinci-dalga: ✓ hepsi geçti" if not HATA else f"ikinci-dalga: ✗ {len(HATA)} kaldı")
sys.exit(1 if HATA else 0)
