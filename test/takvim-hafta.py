#!/usr/bin/env python3
# v0.55.0 (v0.59.0: her soruda 7 gün, ileri tarihte 30, boşluklar yalnız boş zaman sorusunda) — takvim haftası ve uygun zaman: bos_zamanlar (çalışma saatleri, dolu etkinlikler, hafta sonu), Konuş bağlamında 7 gün yalnız haftaya/boş zamana
# değinen soruda, sözlü iş talimatı kalıbı (HITAP_IS_RX: e-posta taslağı, toplantı koy), /takvim?gun=7 ve toplanti-claude.py takvim --gun 7.
# Hafta görünümü (panodaki hafta ızgarası, /takvim?hafta=<n>, takvim_hafta) da burada.
# Kota yok, Whisper yok (~5 sn). Takvim/uygun zaman/iş talimatı kalıbı değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/takvim-hafta.py
import datetime as dt, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8789)
HATA = []
def ok(ad, k, ayr=None):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad); ayr is not None and print("   ", ayr)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
# --- işlevler doğrudan (exec, sahte takvim) -----------------------------------------------------------------------------------------
simdi = dt.datetime(2026, 10, 16, 10, 7).astimezone()  # Cuma 10:07
def olay(i, gun, b, s, **k):
    g = simdi.replace(hour=0, minute=0) + dt.timedelta(days=gun)
    return dict({"id": f"e{i}", "baslik": f"Toplantı {i}", "baslangic": (g + dt.timedelta(hours=b)).isoformat(), "bitis": (g + dt.timedelta(hours=s)).isoformat(),
                 "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayla K"], "kisi_sayisi": 2}, **k)
TAK = {e["id"]: e for e in [olay(1, 0, 11, 12), olay(2, 3, 9, 10.5), olay(3, 3, 13, 18), olay(4, 4, 0, 24, tum_gun=True), olay(5, 5, 9, 18, reddettin=True),
                            olay(6, 6, 10, 11, takvim="Paylaşılan", hesap="Başkası")]}
ad = {"re": re, "datetime": dt, "os": os, "json": json, "time": time, "subprocess": subprocess, "BASE": "/yok/canli", "TAKVIM_APP": "/yok", "AYAR": {"takvim_haric": ["Paylaşılan · Başkası"]}, "TAKVIM_TAM": TAK, "ARAYUZ_DILI": "tr", "STATE": {"takvim": {"durum": "ok"}},
      "_t": lambda a, b: a, "_zaman": lambda t: dt.datetime.fromisoformat(t).astimezone()}
exec(kod[kod.index("_GUN_TR = "):kod.index("# Kişilik (v0.53.0")], ad)
exec(kod[kod.index("# --- Takvim haftası ve uygun zaman"):kod.index("def _konus_kur(")], ad)
bz = {str(d): [f"{b:%H:%M}–{e:%H:%M}" for b, e in ar] for d, ar in ad["bos_zamanlar"](simdi)}
ok(f"bugün: şimdiden (çeyreğe yuvarlı) sonra, 11–12 dolu → 10:15–11:00, 12:00–18:00 ({bz.get('2026-10-16')})", bz.get("2026-10-16") == ["10:15–11:00", "12:00–18:00"])
ok("hafta sonu (Cumartesi, Pazar) yok", "2026-10-17" not in bz and "2026-10-18" not in bz)
ok(f"Pazartesi 9–10:30 ve 13–18 dolu → 10:30–13:00 ({bz.get('2026-10-19')})", bz.get("2026-10-19") == ["10:30–13:00"])
ok("tüm gün etkinlik ve reddedilen davet dolu sayılmaz; izlenmeyen takvim hariç", all(bz.get(f"2026-10-2{i}") == ["09:00–18:00"] for i in (0, 1, 2)))
ad["AYAR"]["calisma_saatleri"] = {"gunler": [0, 1, 2, 3, 4, 5], "bas": "10:00", "bit": "16:00"}
bz2 = {str(d): [f"{b:%H:%M}–{e:%H:%M}" for b, e in ar] for d, ar in ad["bos_zamanlar"](simdi)}
ok("ayar calisma_saatleri (Cumartesi dahil, 10–16)", bz2.get("2026-10-17") == ["10:00–16:00"] and bz2.get("2026-10-20") == ["10:00–16:00"] and "2026-10-18" not in bz2)
ad["AYAR"].pop("calisma_saatleri")
b_dar = ad["konus_baglam"](simdi, "", "Bugün kaçta toplantım var?"); b_gen = ad["konus_baglam"](simdi, "", "Gelecek hafta perşembe boş saatim var mı?")
ok("her soruda 7 gün (v0.59.0), boş zaman yalnız boş/uygun zaman sorusunda", "(önümüzdeki 7 gün)" in b_dar and "Boş zamanlar" not in b_dar and "Toplantı 2" in b_dar)
ok("boş zamana değinen soruda 7 gün + boş zamanlar (gün adıyla)", "(önümüzdeki 7 gün)" in b_gen and "Boş zamanlar" in b_gen and "Pazartesi 19 Ekim 13:00–18:00 · Toplantı 3" in b_gen
   and "- Salı 20 Ekim: 09:00–18:00" in b_gen and "Toplantı 6" not in b_gen)
TAK["e7"] = olay(7, 20, 14, 15); TAK["e7"]["baslik"] = "Uzak gözden geçirme"
b_7, b_30 = ad["konus_baglam"](simdi, "", "Ne var önümüzde?"), ad["konus_baglam"](simdi, "", "Kasım başında ne var?")
ok("20 gün sonraki etkinlik 7 günlük bağlamda yok, ileri tarih sorusunda 30 günde var", "Uzak gözden geçirme" not in b_7 and "(önümüzdeki 30 gün)" in b_30 and "Uzak gözden geçirme" in b_30)
ok("uzak tarih kalıbı: ay adı, gelecek ay, iki hafta sonra tutar; genel ve bu hafta sorusu tutmaz", all(ad["TAKVIM_UZAK_RX"].search(x) for x in ("21 Ekim'de ne var?", "Ay sonunda toplantı var mı?", "Gelecek ay ne var?", "İki hafta sonra ne var?", "Kasım'da müsait miyim?", "What's on next month?"))
   and not any(ad["TAKVIM_UZAK_RX"].search(x) for x in ("Bütçe ne kadar?", "Sen kimsin?", "Yarın ne var?", "Gelecek hafta ne var?", "Bu hafta neler var?", "Ayla ne dedi?")))
ok("boş zaman kalıbı: müsait, uygun zaman tutar; takvim sorusu tutmaz", all(ad["TAKVIM_BOS_RX"].search(x) for x in ("Salı müsait miyim?", "Uygun bir zaman öner", "When am I available?"))
   and not any(ad["TAKVIM_BOS_RX"].search(x) for x in ("Salı ne var?", "Gelecek hafta ne var?")))
# v0.84.0: geçmiş günler (yalnız geçmişi soran soruda) ve davet notu (yalnız gündem/davet sorusunda; katılım metni ve parola silinir)
ad["_baslik_soz"] = lambda b: {w for w in re.findall(r"\w{4,}", str(b or "").replace("İ", "i").replace("I", "ı").lower()) if not w.isdigit()}
ad["TAKVIM_GEC"]["olaylar"] = [olay(8, -1, 14, 15, baslik="Tedarikçi görüşmesi", katilimcilar=["Kerem A"]), olay(9, -10, 9, 10, baslik="Eski toplantı"),
                               olay(10, -2, 9, 10, baslik="Gizli", takvim="Paylaşılan", hesap="Başkası")]
bg = ad["konus_baglam"](simdi, "", "Dün kiminle görüştüm?"); bn = ad["konus_baglam"](simdi, "", "Bugün kaçta toplantım var?")
ok("geçmiş: 'dün kiminle görüştüm' → geçen 7 gün, dün 14:00 Tedarikçi görüşmesi + kişi", "Mac Takvim (geçen 7 gün)" in bg and "- dün 14:00–15:00 · Tedarikçi görüşmesi · Kerem A" in bg)
ok("geçmiş: 7 günden eski ve izlenmeyen takvim yok", "Eski toplantı" not in bg and "Gizli" not in bg)
ok("geçmişi sormayan soruda geçmiş blok yok", "geçen 7 gün" not in bn and "Tedarikçi" not in bn)
GR = ad["GECMIS_GUN_RX"]
ok("geçmiş kalıbı: dün, geçen hafta, Salıki toplantı, kiminle görüştüm tutar; yarın/gelecek tutmaz",
   all(GR.search(x) for x in ("Dünkü toplantı nasıldı?", "Geçen hafta kimlerle toplandım?", "Salıki toplantıda kim vardı?", "Bu hafta kimlerle görüştüm?", "Who did I meet yesterday?"))
   and not any(GR.search(x) for x in ("Yarın ne var?", "Gelecek hafta ne var?", "Bütçe ne kadar?", "Salı müsait miyim?")))
NOT = ("________________\r\nMicrosoft Teams Need help?<https://aka.ms/JoinTeamsMeeting>\r\nJoin the meeting now<https://teams.microsoft.com/l/meetup-join/x>\r\n"
       "Meeting ID: 385 107 963 300 68\r\nPasscode: ky7hL3DZ\r\n________________\r\nGündem: bütçe ve takvim.\r\nLütfen rakamları getirin.\r\nFor organizers: Meeting options<https://teams.microsoft.com/meetingOptions/?a=1>")
temiz = ad["davet_notu_temiz"](NOT)
ok(f"davet notu süzgeci: parola, toplantı kimliği, bağlantı ve Teams metni silinir ({temiz!r})", temiz == "Gündem: bütçe ve takvim. Lütfen rakamları getirin.")
ok("yalnız katılım metni olan not boş kalır", ad["davet_notu_temiz"](NOT.split("Gündem")[0]) == "")
ok("Teams'in 'Please do not edit' ayırıcısı ve tek 'Join:' satırı da silinir", ad["davet_notu_temiz"]("Join:\r\n::~:~::~:~:~:~:~:~:: Join Microsoft Teams Meeting Please do not edit this section. ::~:~::~:~::\r\nKonu: teklif") == "Konu: teklif")
TAK["e2"]["baslik"] = "Bütçe gözden geçirme"; TAK["e2"]["notlar"] = NOT
bd = ad["konus_baglam"](simdi, "", "Bütçe gözden geçirme toplantısının gündemi ne?")
ok("davet sorusu: o toplantının temiz notu bağlamda, parola yok", "Davet notu — Bütçe gözden geçirme (Pazartesi 19 Ekim 09:00): Gündem: bütçe ve takvim. Lütfen rakamları getirin." in bd and "ky7h" not in bd and "Passcode" not in bd)
ok("davet sormayan soruda not yok (parola hiçbir soruda yok)", "Davet notu" not in ad["konus_baglam"](simdi, "", "Bütçe gözden geçirme kaçta?") and "ky7h" not in ad["konus_baglam"](simdi, "", "Bütçe gözden geçirme kaçta?"))
bs_ = ad["konus_baglam"](simdi, "", "Sıradaki toplantının gündemi ne?")
ok("başlık eşleşmezse sıradaki toplantı; notu yoksa 'katılım bilgisinden başka not yok'", "Davet notu — Toplantı 1" in bs_ and "başka not yok" in bs_)
ad3 = {"re": re}; exec(kod[kod.index("HITAP_IS_RX = "):kod.index("def konus_hitap(")].split("# v0.55.0 (S70): toplantıda Konuş")[0], ad3)
ISR = ad3["HITAP_IS_RX"]
evet = ["Ayla'ya bütçe için bir e-posta taslağı hazırla.", "Ali'ye kısa bir mail yaz.", "Bir taslak hazırla, teklifi özetlesin.", "Perşembe saat on dörde Ayla ile toplantı koy.",
        "Salı için bir görüşme ayarla.", "Bunu takvime ekle.", "Davet gönder ekibe.", "kuyruğa al teklif e-postasını", "Draft an email to Ayla."]
hayir = ["Gelecek hafta ne var?", "Perşembe boş saatim var mı?", "Ayla'nın e-posta adresi ne?", "Son toplantıda ne konuşuldu?", "Bütçe ne kadar?"]
ok("iş talimatı kalıbı: e-posta taslağı, toplantı koy, takvime ekle tutar", all(ISR.search(x) for x in evet))
ok("takvim sorusu ve bilgi sorusu iş talimatı sayılmaz (konuşan cevaplar)", not any(ISR.search(x) for x in hayir))
# --- hafta görünümü (panoda hafta ızgarası): takvim_hafta(ofset) — Pazartesi–Pazar, ileri + geçmiş kaynak birleşir, hazırlık = brifing durumu -----------------
exec(kod[kod.index("# Hafta görünümü (panoda hafta ızgarası)"):kod.index("def takvim_yenile():")], ad)
ad["os"] = os
def hol(i, gun, b, s, **k): return dict(olay(i, gun, b, s), baslik=f"Hafta {i}", **k)
ad["TAKVIM_TAM"] = {e["id"]: e for e in [hol(1, 0, 11, 12), hol(2, 0, 11.5, 12.5), hol(3, 1, 9, 10, reddettin=True), hol(4, 3, 10, 11), hol(5, 2, 0, 24, tum_gun=True),
                                         hol(6, 0, 15, 16, takvim="Paylaşılan", hesap="Başkası")]}
ad["TAKVIM_GEC"] = {"olaylar": [hol(11, -2, 14, 15), hol(1, 0, 11, 12), hol(12, -11, 9, 10)], "t": 0}
ad["BRIFING"] = {"e1": {"durum": "hazir"}, "e2": {"durum": "calisiyor"}}
h0, h1, hm, hk = (ad["takvim_hafta"](o, simdi) for o in (0, 1, -1, 9))
b0 = {o["baslik"]: o for o in h0["olaylar"]}
ok(f"bu hafta Pazartesi 12 Ekim'den; ileri + geçmiş birleşik, ertesi hafta yok ({sorted(b0)})", h0["hafta_bas"] == "2026-10-12" and set(b0) == {"Hafta 1", "Hafta 2", "Hafta 3", "Hafta 5", "Hafta 11"})
ok("iki kaynakta olan toplantı bir kez; izlenmeyen takvim yok", [o["baslik"] for o in h0["olaylar"]].count("Hafta 1") == 1 and "Hafta 6" not in b0)
ok("hazırlık: brifing hazır → hazir, sürüyor → eksik, yok → yok", b0["Hafta 1"]["hazirlik"] == "hazir" and b0["Hafta 2"]["hazirlik"] == "eksik" and b0["Hafta 3"]["hazirlik"] == "yok")
ok("geçmiş: geçmiş kaynaktan, başlatılamaz; gelecek başlatılır; reddedilen işaretli; tüm gün işaretli",
   b0["Hafta 11"]["gecmis"] and not b0["Hafta 11"]["baslatilir"] and b0["Hafta 11"]["id"].startswith("g:") and b0["Hafta 1"]["baslatilir"] and not b0["Hafta 1"]["gecmis"]
   and b0["Hafta 3"]["reddettin"] and b0["Hafta 5"]["tum_gun"] and b0["Hafta 1"]["saat"] == "11:00" and b0["Hafta 1"]["bitis_saat"] == "12:00")
ok("sonraki hafta: Pazartesi 19 Ekim, yalnız o haftanın toplantısı", h1["hafta_bas"] == "2026-10-19" and [o["baslik"] for o in h1["olaylar"]] == ["Hafta 4"])
ok("geçen hafta (geçmiş kaynaktan) ve gezinme sınırı -1…+4", hm["hafta_bas"] == "2026-10-05" and [o["baslik"] for o in hm["olaylar"]] == ["Hafta 12"] and hk["ofset"] == 4 and ad["takvim_hafta"](-7, simdi)["ofset"] == -1)
ok(f"kapsam: geçmiş 14 gün, ileri {ad['TAKVIM_SONRA_SA']} sa ({h0['kapsam']})", h0["kapsam"] == {"bas": "2026-10-02", "son": "2026-11-15"} and h0["en_az"] == -1 and h0["en_cok"] == 4)
ad["TAKVIM_GEC"]["olaylar"] = []
ok("geçmiş okunmadıysa kapsam bugünden başlar", ad["takvim_hafta"](0, simdi)["kapsam"]["bas"] == "2026-10-16")
# --- hazırlık toplantı başına (S hazirlik2): kayıtlı brifing → hazir; gündem, belge bağlantısı ya da aynı kişiyle son 30 günde Suflor kaydı → eksik; hiçbiri → yok ----------
HZ = tempfile.mkdtemp(prefix="hazirlik-"); ad["BASE"] = HZ; ad["AYAR"]["ad"] = "Deniz T"
def hk(i, gun, **k): return dict(olay(i, gun, 10, 11), **dict({"baslik": f"Hazırlık {i}", "katilimcilar": ["Ece Y"]}, **k))
TEAMS = "________________\nMicrosoft Teams Need help?\nJoin the meeting now\nMeeting ID: 123 456\nPasscode: abc\nhttps://teams.microsoft.com/l/meetup-join/x"
hz_ol = [hk(21, 3), hk(22, 4, notlar="Gündem: bütçe taslağı ve teslim tarihi"), hk(23, 5, notlar="Belge: https://ornek.sharepoint.com/sites/x/Teklif.docx"),
         hk(24, 6, katilimcilar=["Ayla Kaya", "Ece Y"]), hk(25, 3, notlar=TEAMS), hk(26, 4, katilimcilar=["Deniz Tan"]), hk(27, 5, katilimcilar=["Bora E"])]
ad["TAKVIM_TAM"] = {e["id"]: e for e in hz_ol}; ad["TAKVIM_GEC"] = {"olaylar": [], "t": 0}; ad["BRIFING"] = {}
SONUC = {"ozet": "Kısa özet", "gecmis": [], "acik": ["Teslim tarihi"], "dikkat": ["Bütçe"]}
a21 = ad["hazirlik_yaz"](hz_ol[0], {"durum": "hazir", "at": "2026-10-16T09:00:00", "sonuc": SONUC, "hata": None})
ok("hazırlık dosyası <canli>/hazirlik/<anahtar>.json, içerik brifing biçiminde + anahtar", os.path.isfile(os.path.join(HZ, "hazirlik", a21 + ".json"))
   and ad["hazirlik_oku"](a21)["sonuc"] == SONUC and ad["hazirlik_oku"](a21)["anahtar"] == a21)
ok("anahtar: tekrar eki (kimlik@başlangıç) atılır, geçmiş okumasıyla aynı; başlangıç ya da kimlik değişince farklı; kimliksizde başlık + başlangıç",
   ad["hazirlik_anahtar"](dict(hz_ol[0], id="e21@" + hz_ol[0]["baslangic"])) == a21 and ad["hazirlik_anahtar"](dict(hz_ol[0], baslangic=hz_ol[1]["baslangic"])) != a21
   and ad["hazirlik_anahtar"](dict(hz_ol[0], id="e99")) != a21 and ad["hazirlik_anahtar"](dict(hz_ol[0], id="")) != a21 and len(a21) == 20 and re.fullmatch(r"[0-9a-f]+", a21))
# arşiv: Suflor dökümleri (aktarici/arsiv.py) — son 30 günde Ayla Kaya konuşmuş; 40 gün önce Bora E; kullanıcı (Deniz T) sayılmaz
ARS = {"2026-10-10-1400-Deneme.md": [("14:00", "Ayla Kaya", "x", "", False), ("14:01", "Deniz T", "y", "", False), ("14:02", "Suflor", "z", "", True)],
       "2026-09-06-1000-Eski.md": [("10:00", "Bora E", "x", "", False)]}
ad["ARSIV_DOSYA_RX"] = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})-(.+)\.md$"); ad["_ar_dosyalar"] = lambda: sorted(ARS, reverse=True)
ad["_ar_oku"] = lambda f: {"baslik": f, "satirlar": ARS[f]}
hw = {o["baslik"]: o for o in ad["takvim_hafta"](0, simdi)["olaylar"] + ad["takvim_hafta"](1, simdi)["olaylar"]}
hz = {k: (v["hazirlik"], v["hazirlik_neden"]) for k, v in hw.items()}
ok("kayıtlı hazırlık → hazir (ileri gün), sonuç blokta", hz["Hazırlık 21"][0] == "hazir" and hw["Hazırlık 21"]["hazirlik_sonuc"] == SONUC, hz)
ok("gündemli davet → eksik (gundem)", hz["Hazırlık 22"] == ("eksik", ["gundem"]), hz)
ok("belge bağlantısı → eksik (gundem + belge)", hz["Hazırlık 23"][0] == "eksik" and "belge" in hz["Hazırlık 23"][1], hz)
ok("son 30 günde ortak katılımcı (Ayla Kaya) → eksik (gecmis)", hz["Hazırlık 24"] == ("eksik", ["gecmis"]), hz)
ok("yalnız Teams katılım metni gündem sayılmaz; boş → yok", hz["Hazırlık 25"] == ("yok", []), hz)
ok("kullanıcının kendisi ortak katılımcı sayılmaz; 30 günden eski kayıt sayılmaz", hz["Hazırlık 26"] == ("yok", []) and hz["Hazırlık 27"] == ("yok", []), hz)
ok("hazırlanmamışta sonuç yok", hw["Hazırlık 22"]["hazirlik_sonuc"] is None and hw["Hazırlık 25"]["brifing"] is None)
ad["BRIFING"] = {"e25": {"durum": "calisiyor"}, "e26": {"durum": "hata", "hata": "Brifing okunamadı"}, "e27": {"durum": "hazir", "sonuc": SONUC, "anahtar": "baska"}}
hw = {o["baslik"]: o for o in ad["takvim_hafta"](0, simdi)["olaylar"] + ad["takvim_hafta"](1, simdi)["olaylar"]}
ok("brifing sürüyor → eksik + brifing=calisiyor; hata → eksik + hata metni", hw["Hazırlık 25"]["hazirlik"] == "eksik" and hw["Hazırlık 25"]["brifing"] == "calisiyor"
   and hw["Hazırlık 26"]["hazirlik"] == "eksik" and hw["Hazırlık 26"]["brifing_hata"] == "Brifing okunamadı")
ok("başka tekrarın (anahtarı farklı) brifingi bu toplantıyı hazır göstermez", hw["Hazırlık 27"]["hazirlik"] == "yok")
ad["BRIFING"] = {}; shutil.rmtree(HZ, ignore_errors=True)
# --- uçtan uca: /takvim?gun=7 ve toplanti-claude.py takvim --gun 7 ------------------------------------------------------------------
T = tempfile.mkdtemp(prefix="takvim-hafta-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
s0 = dt.datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "u1", "baslik": "Uzak toplantı", "baslangic": (s0 + dt.timedelta(days=4)).isoformat(), "bitis": (s0 + dt.timedelta(days=4, hours=1)).isoformat(),
           "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayla K"], "kisi_sayisi": 2}]
           + [{"id": "h1", "baslik": "Haftalık", "baslangic": (s0 + dt.timedelta(days=d, hours=1)).isoformat(), "bitis": (s0 + dt.timedelta(days=d, hours=2)).isoformat(),
               "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": [], "kisi_sayisi": 0} for d in (16, 2, 9)]}, open(os.path.join(T, "takvim.json"), "w"))
# sahte Brifing.app (istekteki çıktı dosyasına Claude'un json çıktısını yazar) + sahte claude (yalnız var olsun) — kota yok
app = os.path.join(T, "Suflor Brifing.app", "Contents"); os.makedirs(os.path.join(app, "MacOS"))
open(os.path.join(app, "Info.plist"), "w").write('<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>CFBundleExecutable</key><string>brifing</string>'
    f'<key>CFBundleIdentifier</key><string>deneme.suflor.brifing.{os.getpid()}</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>')
SAHTE = {"result": json.dumps({"ozet": "Sahte brifing özeti", "gecmis": [], "acik": ["Açık soru"], "dikkat": ["Dikkat edilecek"]}, ensure_ascii=False), "usage": {}, "total_cost_usd": 0}
open(os.path.join(app, "MacOS", "brifing"), "w").write("#!/bin/sh\nexec /usr/bin/python3 -I -B -c 'import json,sys; i=json.load(open(sys.argv[sys.argv.index(\"--istek\")+1])); "
    f"open(i[\"cikti\"],\"w\").write({json.dumps(json.dumps(SAHTE, ensure_ascii=False))})' \"$@\"\n")
os.chmod(os.path.join(app, "MacOS", "brifing"), 0o755)
os.makedirs(os.path.join(T, "bin")); open(os.path.join(T, "bin", "claude"), "w").write("#!/bin/sh\nexit 0\n"); os.chmod(os.path.join(T, "bin", "claude"), 0o755)
j_ = json.load(open(ay)); j_.update(claude=os.path.join(T, "bin", "claude"), calisma=T); json.dump(j_, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    get = lambda y: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{y}", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    t1, t7, t30 = get("/takvim?tam=1"), get("/takvim?tam=1&gun=7"), get("/takvim?tam=1&gun=30")
    ok("/takvim (eski): 4 gün sonraki toplantı yok, boş zaman alanı yok", not any(o["id"] == "u1" for o in t1["olaylar"]) and "bos" not in t1)
    ok("/takvim?gun=7: 4 gün sonraki toplantı tarihiyle, boş zaman listesi", any(o["id"] == "u1" and o.get("tarih") for o in t7["olaylar"]) and isinstance(t7.get("bos"), list) and t7.get("gun") == 7)
    ok("/takvim?gun=30: 30 güne kadar açılır (v0.59.0)", t30.get("gun") == 30)
    hw0, hw1 = get("/takvim?hafta=0"), get("/takvim?hafta=1")
    pzt = (s0 - dt.timedelta(days=s0.weekday())).strftime("%Y-%m-%d")
    ok(f"/takvim?hafta=0: bu haftanın Pazartesisi ({hw0.get('hafta_bas')}), 4 gün sonraki toplantı bu ya da sonraki haftada",
       hw0.get("hafta_bas") == pzt and any(o["id"] == "u1" for o in hw0["olaylar"] + hw1["olaylar"]) and isinstance(hw0.get("kapsam"), dict), (hw0.get("durum"), [o["id"] for o in hw0["olaylar"] + hw1["olaylar"]]))
    ok("/takvim?hafta=-1 geçen hafta", get("/takvim?hafta=-1").get("ofset") == -1)
    def post(y, v):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{y}", data=json.dumps(v).encode(), method="POST", headers={"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{PORT}", "Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(q, timeout=10).read())
    hu = lambda: next((o for o in hw0["olaylar"] + hw1["olaylar"] + get("/takvim?hafta=0")["olaylar"] + get("/takvim?hafta=1")["olaylar"] if o["id"] == "u1"), {})
    hw0, hw1 = {"olaylar": []}, {"olaylar": []}
    ok("Hazırla öncesi: gelecek toplantı hazır değil, başlatılabilir", hu().get("hazirlik") in ("eksik", "yok") and hu().get("baslatilir"), hu())
    try: kod_ = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/brifing", data=b'{"olay":"u1"}', method="POST", headers={"X-Suflor-Anahtar": K}), timeout=10).status
    except urllib.error.HTTPError as e: kod_ = e.code
    ok(f"/brifing panosuz (Origin yok) reddedilir ({kod_})", kod_ in (401, 403))
    r1 = post("/brifing", {"olay": "u1"})
    ok(f"Hazırla: /brifing gelecek toplantı için başlar ({r1})", r1.get("ok") and r1.get("durum") == "calisiyor")
    ok("sürerken blok eksik + brifing=calisiyor", hu().get("brifing") == "calisiyor" or hu().get("hazirlik") == "hazir", hu())
    for _ in range(60):
        if hu().get("hazirlik") == "hazir": break
        time.sleep(0.5)
    o = hu()
    ok("bitince yeşil (hazir) ve sonuç blokta", o.get("hazirlik") == "hazir" and (o.get("hazirlik_sonuc") or {}).get("ozet") == "Sahte brifing özeti", (o.get("hazirlik"), o.get("brifing_hata"), open(os.path.join(T, "relay.log")).read()[-600:]))
    hzd = os.path.join(canli, "hazirlik")
    ok("hazırlık dosyası toplantı başına yazıldı", os.path.isdir(hzd) and len([f for f in os.listdir(hzd) if f.endswith(".json")]) == 1)
    ok("ikinci Hazırla yeniden çağırmaz (hazır)", post("/brifing", {"olay": "u1"}).get("durum") == "hazir")
    tk = [o for o in t30["olaylar"] if o["baslik"] == "Haftalık"]
    ok(f"tekrarlanan toplantının her tekrarı ayrı (aynı kimlik; v0.59.1): {len(tk)}/3, en yakını asıl kimlikle", len(tk) == 3 and tk[0]["id"] == "h1" and len({o["id"] for o in tk}) == 3)
    out = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "takvim", "--gun", "7"],
                         capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay)).stdout
    ok("toplanti-claude.py takvim --gun 7: boş zamanlar + uzak toplantı tarihli", "# Boş zamanlar (7 gün" in out and "Uzak toplantı" in out and (s0 + dt.timedelta(days=4)).strftime("%Y-%m-%d") in out)
    ok("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log")).read() and "HAZIRLIK: eşlenemedi" not in open(os.path.join(T, "relay.log")).read())
finally:
    r.terminate(); r.wait(); shutil.rmtree(T, ignore_errors=True)
print("takvim haftası:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
