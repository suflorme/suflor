#!/usr/bin/env python3
# Faz B (v0.149.0) — tek toplantı kaydı (aktarici/toplanti.py). Her senaryo kendi yalıtılmış aktarıcısında (SUFLOR_TEST_HIZLI: sinyal 6 sn, bitiyor 8 sn):
#  A) eklenti yok — Meet web: ses yardımcısı Chrome'u dinliyor + takvimde Meet → kayıt takvim adıyla, platform meet, oturum yerine öneri; ses ve menü mikrofonu
#     (tut) kabul; ses kesilince bitiş.  B) eklenti yok — Teams web + elle Başlat: ad Başlat konusu, ikinci Başlat aynı dosya.
#  C) masaüstü Teams, pencere başlığı kişi adı → dosya adında kişi adı yok.  D) 1826-teams B2: masaüstü toplantı biter, 70 sn sonra Başlat "Test" → iki dosya,
#     yenisinin olayları yenisinde; E) 296 sn gecikmiş satır: bitiyor'da eski dosyaya, bitti'den sonra yazılmaz (GEÇ SATIR, gec_atilan).
#  F) Meet kodlu sayfa başlığı → dosya adı takvimden.  G) 2016-meet B1: çağrısız Teams sekmesi çağrıdaki Meet'i ezmez.
#  H) kısa kopma aynı dosya; aktarıcı yeniden başlayınca aynı dosya; elle bitir → sekme hâlâ çağrıda iken yeniden açılmaz.
#  L) ardışık toplantı (3 Kasım): /status aktif yalnız canlı toplantı, gosterim + toplanti.son bitiyor/bitti'de; sürerken farklı konuyla Başlat → soru, onayla →
#     eski kapanır + yeni dosya; bitiyor'da konusuz Başlat → yeni dosya (ad "<Platform> toplantısı HH:MM").  M) bitiyor'da başka sekme + başka başlık → yeni
#     dosya; aynı sekme (başlık değişse de) ya da aynı başlık → aynı dosya; başlıksız başka sekme 10 sn'den önce aynı, sonra yeni.
#  N) konuşmacı etiketlemesi (toplu Whisper, sahte) yeni toplantı sürerken ertelenir, toplantı bitince arka planda yapılır.
#  O) ardışık toplantıda Claude oturumu (3 Kasım canlı hata): 1. biter → 2. Başlat'la açılır (oturum ertelenir) → 1.'nin oturumu özet yazar (toplanti-claude.py
#     ozet-hazir) → özet 1.'ye sayılır, 2. sürer, ertelenen oturum açılır; 3. kendiliğinden tanınır (oturum yine ertelenir), eski istemci özeti 3.'nün dosyasıyla
#     gönderse de 3. bitmez. Oturum sahte (aktarıcının deneme kopyasında toplanti_oturum_ac yerine `cat` süreci).
#  P) 3 Kasım canlı: 1. bitiyor'dayken 2. Başlat (1. kapanır, 2. aynı anda açılır) → izle 1.'nin TOPLANTI BİTTİ'sini verir, 2.'nin dosyasına geçmez; özet hiç gelmezse
#     2.'nin oturumu bekleme süresi dolunca açılır; özetten sonra eski oturumun süren turu kısa süre bitirilir; terminal kipinde 2. Başlat beklemez.
# aktarici/toplanti.py, ingest/not/kanıt yönlendirmesi, /ping, /masaustu, /ses-yerel değişince koştur:  PYTHONDONTWRITEBYTECODE=1 python3 test/toplanti.py
import base64, datetime, glob, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""), flush=True)
    if not k: HATA.append(ad)
simdi = datetime.datetime.now().astimezone(); iso = lambda d: d.isoformat(timespec="seconds")
def olay(i, ad, pl, b, s, bag):
    return {"id": i, "baslik": ad, "baslangic": iso(simdi + datetime.timedelta(minutes=b)), "bitis": iso(simdi + datetime.timedelta(minutes=s)), "tum_gun": False,
            "takvim": "İş", "platform": pl, "baglanti": bag, "katilimcilar": ["Ayşe Örnek"], "kisi_sayisi": 2}
MEET = olay("e1", "Örnek ile proje", "meet", -3, 27, "https://meet.google.com/abc-defg-hij")
TEAMS = olay("e2", "Haftalık plan", "teams", -1, 29, "https://teams.microsoft.com/l/meetup-join/x")

class Aktarici:
    def __init__(self, olaylar=(), T=None, ek_env=None):
        self.ek_env = ek_env or {}; self.T = T or os.path.realpath(tempfile.mkdtemp(prefix="toplanti-")); self.canli = os.path.join(self.T, "canli"); os.makedirs(self.canli, exist_ok=True)
        self.port = bos_port(8783); self.U = f"http://127.0.0.1:{self.port}"; self.log = os.path.join(self.T, "relay.log")
        if not T:
            json.dump({"durum": "ok", "olaylar": list(olaylar)}, open(os.path.join(self.T, "takvim.json"), "w"), ensure_ascii=False)
            os.makedirs(os.path.join(self.T, "Suflor Ses.app"))  # yerel ses "kurulu" sayılsın (nabızla dinliyor)
            json.dump({"alan": "Deneme", "ad": "Ali T", "port": self.port, "uygulama": self.T, "ortak": "/Users/Shared/Suflor", "konusma": False,
                       "tepki_sesleri": os.path.join(self.T, "tepki-yok")}, open(os.path.join(self.T, "ayar.json"), "w"))
            for f in ("relay.py", "manifest.json", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), self.T)
            for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(self.T, d))
        self.ac()
    def ac(self):
        self.p = subprocess.Popen([sys.executable, "relay.py", "--dir", self.canli, "--port", str(self.port)], cwd=self.T, stdout=open(self.log, "a"), stderr=subprocess.STDOUT,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(self.T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTO="1", SUFLOR_TEST_HIZLI="1",
                                           SUFLOR_TEST_KULAKLIK="0", **self.ek_env))
        for _ in range(100):
            try: self.istek("/status"); return
            except Exception: time.sleep(0.1)
    def kapat(self): self.p.terminate(); self.p.wait(5)
    def sil(self): shutil.rmtree(self.T, ignore_errors=True)
    def istek(self, yol, g=None, anahtar="kart-anahtari.txt"):
        k = open(os.path.join(self.canli if anahtar == "kart-anahtari.txt" else self.T, anahtar)).read().strip()
        h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k}
        if yol == "/baslat": h["Origin"] = self.U
        q = urllib.request.Request(self.U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
        return json.load(urllib.request.urlopen(q, timeout=10))
    def ses_nabiz(self, durum="dinliyor", uyg="Chrome"): return self.istek("/ses-yerel", {"nabiz": True, "durum": durum, "uygulama": uyg, "tepe": 2000}, "ses-anahtari.txt")
    def ses_parca(self): return self.istek("/ses-yerel", {"t": int(time.time() * 1000), "pcm": base64.b64encode(b"\0\0" * 1600).decode()}, "ses-anahtari.txt")
    def ping(self, pl="meet", call=True, baslik="abc-defg-hij", sekme="t1"):
        return self.istek("/ping", {"ver": "0.149.0", "meeting": {"title": baslik}, "panel": False, "rows": 0, "platform": pl, "call": call, "captions": call, "sekme": sekme, "mic": {"on": call}})
    def cik(self, pl="meet", baslik="abc-defg-hij", sekme="t1"):  # çağrıdan çıkış: tek false nabzı yetmez (NABIZ_BITIS_SN) — iki false, aralarında ≥ 3 sn
        self.ping(pl, False, baslik, sekme); time.sleep(3.2); return self.ping(pl, False, baslik, sekme)
    def whisper(self, metin, t0=None, kanal="karsi"):
        t0 = t0 or time.time()
        return self.istek("/ingest", {"meeting": {"title": "yok sayılır"}, "source": "whisper", "entries": [{"id": f"w/{t0}", "speaker": "Karşı taraf", "time": "10:00", "text": metin, "kanal": kanal, "t0": t0, "t1": t0 + 1}]})
    def altyazi(self, metin, baslik="abc-defg-hij"):
        return self.istek("/ingest", {"meeting": {"title": baslik}, "source": "transcript", "capturedAt": datetime.datetime.utcnow().isoformat() + "Z",
                                      "entries": [{"id": f"a/{time.time()}", "speaker": "Ayla", "time": "10:00", "text": metin}]})
    def masaustu(self, top, baslik="Ayşe Yılmaz | Microsoft Teams"): return self.istek("/masaustu", {"uygulama": "Teams", "toplantida": top, "baslik": baslik})
    def durum(self): return self.istek("/status")["toplanti"]
    def md(self): return sorted(os.path.basename(f) for f in glob.glob(os.path.join(self.canli, "*.md")))
    def oku(self, f): return open(os.path.join(self.canli, f), encoding="utf-8").read()
    def gunluk(self): return open(self.log, encoding="utf-8").read()
def bekle(kosul, sn=25):
    t = time.time()
    while time.time() - t < sn:
        try:
            if kosul(): return True
        except Exception: pass
        time.sleep(0.3)
    return False
def surekli(f, sn):  # sn boyunca sinyali taze tut
    t = time.time()
    while time.time() - t < sn: f(); time.sleep(1)

def senaryo_A():
    print("— A) eklenti yok — Meet web (ses + takvim)")
    R = Aktarici([MEET])
    try:
        R.ses_nabiz(); ok("A1 ses parçası toplantı açılmadan beklenmez (kayıt sesle açılır)", "bekle" not in R.ses_parca())
        d = R.durum(); ok("A-2 kayıt takvim adıyla", d.get("ad") == "Örnek ile proje", str(d))
        ok("A3 platform meet (takvim bağlantısı)", d.get("platform") == "meet", str(d)); ok("A4 Claude oturumu yerine öneri", "öneri" in str(d.get("neden")), str(d))
        R.whisper("merhaba, başlayalım"); d = R.durum(); ok("A5 ilk satırla sürüyor", d.get("durum") == "suruyor", str(d))
        ok("A6 menü uygulamasına mikrofonu tut (eklenti yok)", R.masaustu(False).get("tut") is True)
        ok("A7 menü mikrofonu parçası kabul", "bekle" not in R.istek("/ses-masaustu", {"t": int(time.time() * 1000), "pcm": base64.b64encode(b"\0\0" * 1600).decode()}))
        R.istek("/ses-masaustu", {"olay": "acildi", "aygit": "MacBook Mikrofonu"})
        ok("A8 panoda 'sessiz durumu bilinmiyor' notu", R.durum().get("mic_bilinmiyor") is True, str(R.durum()))
        ok("A9 eklentisizken pano aktif", R.istek("/status")["aktif"] is True)
        R.ses_nabiz("bekliyor")
        ok("A10 ses kesilince bitti", bekle(lambda: R.durum()["durum"] == "bos", 40), str(R.durum()))
        md = R.md(); ok("A11 tek dosya, takvim adlı", len(md) == 1 and md[0].endswith("Örnek-ile-proje.md"), str(md))
        ok("A12 başlık Google Meet", "Google Meet" in R.oku(md[0]).splitlines()[2] if md else False)
        ok("A13 toplanti_bitti yayınlandı", (R.istek("/status").get("toplanti_bitti") or {}).get("file") == (md or [""])[0])
        ok("A14 hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_B():
    print("— B) eklenti yok — Teams web + elle Başlat")
    R = Aktarici([TEAMS])
    try:
        r = R.istek("/baslat", {"konu": "Yol haritası", "platform": "teams"}); ok("B1 Başlat", r.get("ok"), str(r))
        d = R.durum(); ok("B2 ad elle yazılan konu (takvimin önünde)", d.get("ad") == "Yol haritası", str(d)); ok("B3 algılandı", d.get("durum") == "algilandi", str(d))
        R.ses_nabiz("dinliyor", "Chrome"); R.whisper("toplantı başladı"); ok("B4 sürüyor", R.durum()["durum"] == "suruyor")
        R.istek("/baslat", {"konu": "Yol haritası"}); R.istek("/baslat", {"konu": ""}); R.whisper("ikinci satır")
        ok("B5 ikinci Başlat aynı dosya", len(R.md()) == 1, str(R.md()))
        R.istek("/note", {"text": "not denemesi", "at": datetime.datetime.utcnow().isoformat() + "Z"})
        ok("B6 not süren toplantıda", "not denemesi" in R.oku(R.md()[0]))
        ok("B7 hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_CDE():
    print("— C/D/E) masaüstü Teams, kişi adlı pencere; bölünme; 296 sn gecikmiş satır")
    R = Aktarici([])
    try:
        R.masaustu(True); d = R.durum(); saat = datetime.datetime.now().strftime("%H:%M")
        ok("C1 kayıt nötr adla (pencere başlığı değil)", d.get("ad", "").startswith("Teams toplantısı"), str(d))
        R.whisper("ilk toplantının satırı"); eski = R.md()[0]
        ok("C2 dosya adında kişi adı yok", "Ayşe" not in eski and "Yılmaz" not in eski, eski)
        ok("C3 durumda pencere başlığı yok", "Ayşe" not in json.dumps(R.istek("/status"), ensure_ascii=False))
        t_eski = time.time() - 2
        R.masaustu(False); ok("D1 masaüstü çıkışı → bitiyor", R.durum()["durum"] == "bitiyor", str(R.durum()))
        R.whisper("kuyrukta kalan söz", t_eski); ok("E1 bitiyor'da eski zamanlı satır eski dosyada", "kuyrukta kalan söz" in R.oku(eski))
        ok("D2 bitti", bekle(lambda: R.durum()["durum"] == "bos", 30), str(R.durum()))
        r = R.istek("/baslat", {"konu": "Test", "platform": "teams"}); ok("D3 yeni Başlat", r.get("ok") and not r.get("katildi"), str(r))
        R.istek("/note", {"text": "EKRAN olayı", "at": datetime.datetime.utcnow().isoformat() + "Z"})
        R.whisper("296 sn gecikmiş eski söz", t_eski - 1)
        md = R.md(); yeni = [m for m in md if m.endswith("-Test.md")]
        ok("D4 iki dosya", len(md) == 2 and len(yeni) == 1, str(md))
        ok("D5 yeni toplantının olayı yenisinde, eskide yok", yeni and "EKRAN olayı" in R.oku(yeni[0]) and "EKRAN olayı" not in R.oku(eski))
        ok("E2 bitmiş toplantının geç satırı hiçbir dosyada yok", not any("296 sn gecikmiş" in R.oku(m) for m in md))
        ok("E3 GEÇ SATIR günlükte", "GEÇ SATIR" in R.gunluk()); ok("E4 gec_atilan sayıldı", (R.durum().get("onceki") or {}).get("gec_atilan") == 1, str(R.durum()))
        ok("CDE hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_FG():
    print("— F/G) Meet kodlu sayfa başlığı; çağrısız Teams sekmesi Meet'i ezmez")
    R = Aktarici([MEET])
    try:
        R.ping("meet", True, "abc-defg-hij", "t1"); R.altyazi("altyazı satırı")
        md = R.md(); ok("F1 dosya adı takvimden, Meet kodu yok", len(md) == 1 and "Örnek-ile-proje" in md[0] and "abc" not in md[0], str(md))
        for _ in range(4): R.ping("teams", False, "Microsoft Teams", "t2"); R.ping("meet", True, "abc-defg-hij", "t1"); time.sleep(0.3)
        R.ping("teams", False, "Microsoft Teams", "t2")
        s = R.istek("/status"); ok("G1 eklenti özeti Meet sekmesi", (s.get("extension") or {}).get("platform") == "meet", str(s.get("extension")))
        ok("G2 kayıt platformu meet", s["toplanti"].get("platform") == "meet"); ok("G3 kayıt sürüyor (ezilmedi)", s["toplanti"]["durum"] == "suruyor")
        R.altyazi("ikinci altyazı", "Microsoft Teams"); ok("G4 hâlâ tek dosya", len(R.md()) == 1, str(R.md()))
        ok("F2 eklenti çağrıdayken Claude oturumu sormadan açıldı (mrt 28 Ekim 01:06)", bekle(lambda: "OTO: toplantı oturumu açıldı" in R.gunluk(), 8), R.gunluk()[-600:])
        # mrt 28 Ekim B2/B3: Meet aynı altyazı bloğunu tek kimlikle büyütür, saat alanı boş
        an = lambda: datetime.datetime.utcnow().isoformat() + "Z"
        blok = lambda m: R.istek("/ingest", {"meeting": {"title": "abc-defg-hij"}, "source": "captions", "capturedAt": an(),
                                             "entries": [{"id": "cap-x/2", "speaker": "Ayla", "time": "", "text": m, "seen": an(), "chg": an(), "revised": m != "Bir iki"}]})
        blok("Bir iki"); blok("Bir iki üç dört"); blok("Bir iki üç dört beş altı")
        md_ = R.oku(R.md()[0]); sat = [l for l in md_.splitlines() if "Bir iki" in l or l.startswith("| ") and "… " in l]
        ok("B2 düzeltme md'de yalnız eklenen kısım", sum("Bir iki" in l for l in md_.splitlines()) == 1 and "… üç dört |" in md_ and "… beş altı |" in md_, "\n".join(sat))
        ok("B3 boş saat seen/chg'den", all(not l.startswith("|  |") for l in sat) and bool(sat))
        R.istek("/ingest", {"meeting": {"title": "abc-defg-hij"}, "source": "captions", "capturedAt": an(), "entries": [{"id": "cap-y/1", "speaker": "Ali T", "time": "", "text": "Suflor, burada mısın?"}]})
        ok("B1 altyazıdaki hitap günlükte (Whisper kapalı)", "hitap altyazıda duyuldu, Whisper kapalı" in R.gunluk())
        ok("FG hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_H():
    print("— H) kısa kopma, yeniden başlatma, elle bitir")
    R = Aktarici([])
    try:
        R.ping("teams", True, "Microsoft Teams"); R.altyazi("ilk"); f = R.md()
        time.sleep(4); R.ping("teams", True, "Microsoft Teams"); R.altyazi("kopmadan sonra")
        ok("H1 kısa kopma aynı dosya", R.md() == f and R.durum()["durum"] == "suruyor", str(R.md()))
        R.kapat(); R.ac(); R.ping("teams", True, "Microsoft Teams"); R.altyazi("yeniden başlattıktan sonra")
        ok("H2 aktarıcı yeniden başlayınca aynı dosya", R.md() == f and "yeniden başlattıktan sonra" in R.oku(f[0]), str(R.md()))
        ok("H2b yeniden başlayınca Whisper ısınır (deneme ortamında model yok: 'kapali'dan çıkar)", bekle(lambda: R.istek("/status")["whisper"]["durum"] != "kapali", 8), str(R.istek("/status")["whisper"].get("durum")))
        q = R.istek("/ask", {"text": "Bütçe ne kadardı?"})
        ok("H2c toplantı oturumu izlemiyorken soru yazılı asistana gider (cevapsız kalmaz)", q.get("ok") and q.get("asistan") is not None and "SORU: toplantı oturumu izlemiyor" in R.gunluk(), str(q))
        ok("H3 elle bitir", R.istek("/toplanti", {"islem": "bitir"}).get("ok"))
        ok("H4 bitti", bekle(lambda: R.durum()["durum"] == "bos", 15), str(R.durum()))
        surekli(lambda: R.ping("teams", True, "Microsoft Teams"), 4)
        ok("H5 sekme çağrıdayken yeniden açılmadı", R.durum()["durum"] == "bos" and len(R.md()) == 1, str(R.durum()))
        ok("H hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_JK():
    print("— J/K) 28 Ekim mrt: Meet sekmesi call=false + ses Chrome; eklenti yok + ses, takvim yok")
    R = Aktarici([])
    try:
        R.ses_nabiz(); R.ping("meet", False, "abc-defg-hij", "t1")  # Türkçe Meet: "Ayrıl" bulunamadı, call=false ama toplantı sayfası
        R.istek("/ping", {"ver": "0.149.0", "meeting": {"title": "abc"}, "platform": "meet", "call": False, "captions": True, "sekme": "t1", "sayfa": True, "mic": {"on": False}})
        ok("J1 toplantı sekmesi + ses Chrome → kayıt sürüyor (güvenli)", bekle(lambda: R.durum()["durum"] == "suruyor", 8), str(R.durum()))
        ok("J2 Claude oturumu açıldı (öneri değil)", bekle(lambda: "OTO: toplantı oturumu açıldı" in R.gunluk(), 8), R.gunluk()[-500:])
        ok("J3 platform meet, ad nötr", R.durum().get("platform") == "meet" and R.durum().get("ad", "").startswith("Google Meet toplantısı"))
    finally: R.kapat(); R.sil()
    R = Aktarici([])
    try:
        R.ses_nabiz(); R.ses_parca(); d = R.durum()
        ok("K1 eklenti yok, takvim yok, yalnız ses → kayıt algılandı, dosya açık", d.get("durum") == "algilandi" and len(R.md()) == 1, str(d))
        ok("K2 gerekçe günlükte", "TOPLANTI: sinyal zayıf" in R.gunluk())
        ok("K3 satırdan önce öneri kartı yok", "öneri kartı" not in R.gunluk())
        R.whisper("merhaba"); ok("K4 ilk satırla öneri kartı", bekle(lambda: "OTO: öneri kartı" in R.gunluk(), 8), R.gunluk()[-500:])
        ok("K5 Claude oturumu sormadan açılmadı", "toplantı oturumu açıldı" not in R.gunluk())
        R.istek("/ping", {"ver": "0.149.0", "meeting": {"title": "abc"}, "platform": "meet", "call": False, "captions": False, "sekme": "t9", "mic": {"on": False}})  # altyazı satırı eklenti nabzı ister
        R.istek("/ingest", {"meeting": {"title": "abc"}, "source": "captions", "capturedAt": datetime.datetime.utcnow().isoformat() + "Z", "entries": [{"id": "c/1", "speaker": "Ayla", "time": "", "text": "altyazı geldi"}]})
        ok("K6 altyazı satırı gelince güvenli → oturum açıldı", bekle(lambda: "OTO: toplantı oturumu açıldı" in R.gunluk(), 8))
        ok("K7 öneri kartı kendiliğinden kapandı", not any("Toplantı algılandı" in c.get("text", "") for c in R.istek("/cards").get("cards", [])))
        ok("JK hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_L():
    print("— L) ardışık toplantı: /status alanları, sürerken farklı konu sorusu, bitiyor'da konusuz Başlat")
    R = Aktarici([])
    try:
        nab = lambda sk="t1", b="Proje A görüşmesi": R.ping("teams", True, b, sk)
        r = R.istek("/baslat", {"konu": "Proje A", "platform": "teams"}); nab(); R.altyazi("A'nın ilk satırı", "Proje A görüşmesi")
        s = R.istek("/status"); ok("L1 sürüyor: aktif ve gosterim", s["toplanti"]["durum"] == "suruyor" and s["aktif"] is True and s["gosterim"] is True and s["toplanti"].get("canli") is True, str(s["toplanti"]))
        r = R.istek("/baslat", {"konu": "Proje B", "platform": "teams"})
        ok("L2 sürerken farklı konu → soru (sessizce katılmaz)", r.get("soru") == "suruyor" and not r.get("ok") and r.get("ad") == "Proje A" and r.get("konu") == "Proje B" and "Proje A" in (r.get("err") or ""), str(r))
        ok("L3 soru sonrası tek dosya, kayıt sürüyor", len(R.md()) == 1 and R.durum()["ad"] == "Proje A", str(R.md()))
        r = R.istek("/baslat", {"konu": "Proje A"}); ok("L4 sürerken aynı konu → katılır (soru yok)", r.get("ok") and not r.get("soru") and len(R.md()) == 1, str(r))
        r = R.istek("/baslat", {}); ok("L4b sürerken konusuz → katılır", r.get("ok") and not r.get("soru") and len(R.md()) == 1, str(r))
        r = R.istek("/baslat", {"konu": "Proje B", "platform": "teams", "onay": "bitir"}); d = R.durum()
        ok("L5 onaylanınca eski kapandı, yeni dosya", r.get("ok") and len(R.md()) == 2 and d.get("ad") == "Proje B" and (d.get("onceki") or {}).get("ad") == "Proje A"
           and "onaylandı" in str((d.get("onceki") or {}).get("neden")), f"{r} {d}")
        R.altyazi("B'nin satırı", "Proje B görüşmesi")
        yb = [m for m in R.md() if m.endswith("Proje-B.md")]; ya = [m for m in R.md() if m.endswith("Proje-A.md")]
        ok("L6 yeni satır yeni dosyada", yb and ya and "B'nin satırı" in R.oku(yb[0]) and "B'nin satırı" not in R.oku(ya[0]), str(R.md()))
        ok("L7 bitiyor", bekle(lambda: R.durum()["durum"] == "bitiyor", 20), str(R.durum()))
        s = R.istek("/status"); t = s["toplanti"]
        ok("L8 bitiyor'da aktif yok (pano Bugün + Başlat), gosterim var, son = bitiyor", s["aktif"] is False and s["gosterim"] is True and t.get("bitiyor") is True and t.get("canli") is False
           and (t.get("son") or {}).get("durum") == "bitiyor" and (t.get("son") or {}).get("ad") == "Proje B", str(t))
        r = R.istek("/baslat", {"platform": "teams"}); d = R.durum(); md = R.md()
        ok("L9 bitiyor'da konusuz Başlat → yeni dosya, nötr ad", r.get("ok") and not r.get("katildi") and len(md) == 3 and str(d.get("ad")).startswith("Teams toplantısı")
           and (d.get("onceki") or {}).get("ad") == "Proje B", f"{r} {d} {md}")
        nab("t2", "Microsoft Teams"); R.altyazi("üçüncü toplantı")
        ok("L10 yeni kayıt sürüyor", bekle(lambda: R.durum()["durum"] == "suruyor", 8), str(R.durum()))
        ok("L11 bitti", bekle(lambda: R.durum()["durum"] == "bos", 40), str(R.durum()))
        s = R.istek("/status"); t = s["toplanti"]
        ok("L12 bitti sonrası: aktif yok, son toplantı gösterimi (özet bekleniyor)", s["aktif"] is False and s["gosterim"] is True and (t.get("son") or {}).get("durum") == "bitti"
           and (t.get("son") or {}).get("ozet") is False and t.get("bitiyor") is False, str(t))
        ok("L hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_M():
    print("— M) bitiyor'da eklentinin başka sekmesinde başka çağrı")
    R = Aktarici([], ek_env={"SUFLOR_TEST_BITIYOR_SN": "40"})
    try:
        bitiyor = lambda: bekle(lambda: R.durum()["durum"] == "bitiyor", 20)
        surekli(lambda: R.ping("teams", True, "Satış görüşmesi | Microsoft Teams", "t1"), 2); R.altyazi("satış satırı", "Satış görüşmesi | Microsoft Teams")
        ok("M1 ilk kayıt", len(R.md()) == 1 and R.durum()["durum"] == "suruyor", str(R.md()))
        ok("M2 bitiyor", bitiyor(), str(R.durum()))
        R.ping("teams", True, "Bütçe toplantısı | Microsoft Teams", "t2"); d = R.durum()
        ok("M3 başka sekme + başka başlık → yeni dosya, eski kapandı", len(R.md()) == 2 and d["durum"] == "suruyor" and "başka sekmede başka bir çağrı — yeni toplantı" in R.gunluk(), f"{d} {R.md()}")
        R.altyazi("bütçe satırı", "Bütçe toplantısı | Microsoft Teams"); yeni = R.durum()["dosya"]
        ok("M4 yeni çağrının satırı yeni dosyada", "bütçe satırı" in R.oku(yeni) and not any("bütçe satırı" in R.oku(m) for m in R.md() if m != yeni))
        ok("M5 bitiyor", bitiyor(), str(R.durum()))
        R.ping("teams", True, "Microsoft Teams", "t2")
        ok("M6 aynı sekme (başlık değişti) → aynı dosya", len(R.md()) == 2 and R.durum()["durum"] == "suruyor" and R.durum()["dosya"] == yeni, str(R.durum()))
        ok("M7 bitiyor", bitiyor(), str(R.durum()))
        R.ping("teams", True, "Bütçe toplantısı | Microsoft Teams", "t3")
        ok("M8 başka sekme, aynı başlık (yeniden katılma) → aynı dosya", len(R.md()) == 2 and R.durum()["dosya"] == yeni, str(R.durum()))
        ok("M9 bitiyor", bitiyor(), str(R.durum()))
        R.ping("teams", True, "Microsoft Teams", "t4")
        ok("M10 başlıksız başka sekme 10 sn'den önce → aynı dosya", len(R.md()) == 2 and R.durum()["dosya"] == yeni and R.durum()["durum"] == "suruyor", str(R.durum()))
        ok("M11 bitiyor", bitiyor(), str(R.durum())); time.sleep(11)
        R.ping("teams", True, "Microsoft Teams", "t5")
        ok("M12 başlıksız başka sekme 10 sn'den sonra → yeni dosya", len(R.md()) == 3 and R.durum()["dosya"] != yeni, f"{R.durum()} {R.md()}")
        ok("M13 kayıt dosyasında başlık metni yok (yalnız iz)", "Bütçe" not in open(os.path.join(R.canli, "toplanti.json"), encoding="utf-8").read())
        ok("M hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

def senaryo_N():
    print("— N) konuşmacı etiketlemesi yeni toplantı sürerken ertelenir")
    R = Aktarici([])
    try:
        surekli(lambda: R.ping("teams", True, "Eski görüşme", "t1"), 2); R.altyazi("eski satır", "Eski görüşme"); eski = R.durum()["dosya"]
        R.istek("/toplanti", {"islem": "bitir"}); ok("N1 eski bitti", bekle(lambda: R.durum()["durum"] == "bos", 20), str(R.durum()))
        # elle bitir kilidi aynı sekmeyi tutar; başka sekmedeki başka çağrı hemen yeni toplantıdır
        DUR = {"nabiz": True}
        def nabiz():
            while DUR["nabiz"]: R.ping("teams", True, "Yeni görüşme", "t2"); time.sleep(1)
        import threading; th = threading.Thread(target=nabiz, daemon=True); th.start()
        ok("N2 elle bitirdikten hemen sonra başka sekmedeki yeni çağrı kilide takılmadı, sürüyor", bekle(lambda: R.durum()["durum"] in ("algilandi", "suruyor") and R.durum().get("dosya") != eski, 15), str(R.durum()) + R.gunluk()[-800:])
        open(os.path.join(R.canli, eski[:-3] + ".sesizi.log"), "w").write('{"id": "x", "iz": ""}\n')
        sahte = os.path.join(R.T, "ortak-sahte", "whisper-venv", "bin"); os.makedirs(sahte); kayit = os.path.join(R.T, "toplu.log")
        open(os.path.join(sahte, "python"), "w").write(f"#!{sys.executable}\nimport sys, time\nopen({kayit!r}, 'a').write(str(time.time()) + ' ' + ' '.join(sys.argv[1:]) + '\\n')\nprint('{{\"kume\": {{}}, \"bol\": {{}}}}')\n")
        os.chmod(os.path.join(sahte, "python"), 0o755)
        ay = json.load(open(os.path.join(R.T, "ayar.json"))); ay["ortak"] = os.path.join(R.T, "ortak-sahte"); json.dump(ay, open(os.path.join(R.T, "ayar2.json"), "w"))
        t0 = time.time()
        c = subprocess.run([sys.executable, "-B", os.path.join(R.T, "toplanti-claude.py"), "--dir", R.canli, "--relay", R.U, "konusmaci", eski], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(R.T, "ayar2.json"), SUFLOR_TEST_HIZLI="1"))
        ok("N3 komut beklemeden döndü, 'ertelendi'", time.time() - t0 < 10 and "ertelendi" in c.stdout, c.stdout + c.stderr)
        ok("N4 toplu Whisper başlamadı", not os.path.exists(kayit))
        ok("N5 aktarıcı günlüğünde 'ertelendi'", bekle(lambda: "KONUŞMACI: etiketleme ertelendi" in R.gunluk(), 5))
        c2 = subprocess.run([sys.executable, "-B", os.path.join(R.T, "toplanti-claude.py"), "--dir", R.canli, "--relay", R.U, "konusmaci", eski], capture_output=True, text=True, timeout=60,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(R.T, "ayar2.json"), SUFLOR_TEST_HIZLI="1"))
        ok("N6 ikinci çağrı ikinci bekçi açmaz", R.gunluk().count("KONUŞMACI: etiketleme ertelendi") == 1, R.gunluk()[-400:])
        time.sleep(3); ok("N7 toplantı sürerken hâlâ başlamadı", not os.path.exists(kayit))
        DUR["nabiz"] = False
        ok("N8 yeni toplantı bitince toplu iş arka planda yapıldı", bekle(lambda: os.path.exists(kayit), 60) and bekle(lambda: "ertelenen etiketleme yapıldı" in R.gunluk(), 10), R.gunluk()[-600:])
        ok("N9 toplu iş tek kez, eşleme yazıldı", os.path.exists(kayit) and len(open(kayit).read().splitlines()) == 1 and os.path.exists(os.path.join(R.canli, eski[:-3] + ".konusmaci.json")))
        ok("N hata yok", "Traceback" not in R.gunluk())
    finally: R.kapat(); R.sil()

SAHTE_OTURUM = '''
# test/toplanti.py O: sahte toplantı oturumu (yalnız deneme kopyasında) — Brifing.app yerine stdin'i kapanınca çıkan `cat`
def toplanti_oturum_ac(cl, model, ky, ilk, konu=None, sid=None):
    with TOPO["kilit"]:
        if topo_canli(): toplanti_oturum_kapat("yeni başlatma")
        TOPO.update(mesaj=[], sid=None, konu=konu, t0=time.time(), hata=None, etkinlik=None)
        TOPO["app"] = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True); TOPO["w"] = TOPO["app"].stdin
        TOPO["nesil"] += 1; _topo_durum("calisiyor")
        print(f"TOPLANTI OTURUMU: arka planda açıldı (sahte) · {konu}"); return True
'''
def oturumlu(ek_ayar=None):  # O, P: sahte claude + sahte toplantı oturumu + nabız iş parçacığı (DUR["sekme"] = "dur" durdurur)
    T = os.path.realpath(tempfile.mkdtemp(prefix="toplanti-")); os.makedirs(os.path.join(T, "canli"))
    cl = os.path.join(T, "claude"); open(cl, "w").write("#!/bin/sh\necho '{\"loggedIn\": true}'\n"); os.chmod(cl, 0o755)
    port = bos_port(8783); json.dump({"durum": "ok", "olaylar": []}, open(os.path.join(T, "takvim.json"), "w"))
    os.makedirs(os.path.join(T, "Suflor Ses.app")); os.makedirs(os.path.join(T, "calisma"))
    json.dump({"alan": "Deneme", "ad": "Ali T", "port": port, "uygulama": T, "ortak": "/Users/Shared/Suflor", "konusma": False, "claude": cl, "calisma": os.path.join(T, "calisma"),
               "tepki_sesleri": os.path.join(T, "tepki-yok"), **(ek_ayar or {})}, open(os.path.join(T, "ayar.json"), "w"))
    for f in ["manifest.json"] + glob.glob(os.path.join(KOD, "*.py")): shutil.copy(os.path.join(KOD, f), T)  # P: izle (toplanti-claude.py) baglam vb. ister
    for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
    open(os.path.join(T, "aktarici", "toplanti-oturum.py"), "a", encoding="utf-8").write(SAHTE_OTURUM)
    R = Aktarici(T=T, ek_env={"SUFLOR_TEST_OTURUM": "1"})
    DUR = {"sekme": None, "baslik": None}
    def nabiz():
        while DUR["sekme"] != "dur":
            if DUR["sekme"]: R.ping("teams", True, DUR["baslik"], DUR["sekme"])
            time.sleep(1)
    import threading; threading.Thread(target=nabiz, daemon=True).start()
    acildi = lambda: R.gunluk().count("arka planda açıldı (sahte)")
    def ozet(ad):
        y = os.path.join(T, "calisma", ad); open(y, "w", encoding="utf-8").write("# Özet\n\n## Toplantı çıktısı\n- 1 karar\n"); return y
    def son_dosya():
        try: return json.loads(open(os.path.join(R.canli, "son-toplantilar.jsonl"), encoding="utf-8").read().splitlines()[-1]).get("dosya")
        except (OSError, IndexError, ValueError): return None
    return T, R, DUR, acildi, ozet, son_dosya
def senaryo_O():
    print("— O) ardışık toplantıda Claude oturumu: önceki toplantının özeti yenisini bitirmez, ertelenen oturum açılır")
    T, R, DUR, acildi, ozet, son_dosya = oturumlu()
    try:
        r = R.istek("/baslat", {"konu": "Toplantı bir", "platform": "teams"}); DUR.update(sekme="t1", baslik="Toplantı bir | Microsoft Teams"); time.sleep(1.5)
        R.altyazi("birinci toplantının satırı", DUR["baslik"]); d1 = R.durum()
        ok("O1 1. toplantı sürüyor, oturum açık (sahte)", r.get("ok") and d1.get("durum") == "suruyor" and d1.get("oturum") and acildi() == 1, f"{r} {d1}")
        f1 = d1.get("dosya"); DUR["sekme"] = None; R.cik("teams", "Toplantı bir | Microsoft Teams", "t1")
        ok("O2 1. toplantı bitti", bekle(lambda: R.durum()["durum"] == "bos", 40), str(R.durum()))
        ok("O3 oturum önceki toplantının sonunu yapıyor (/status oturum_dosya = 1.)", R.durum().get("oturum_dosya") == f1, str(R.durum()))
        r = R.istek("/baslat", {"konu": "Toplantı iki", "platform": "teams"})
        ok("O4 2. Başlat: kayıt açıldı, oturum ertelendi", r.get("ok") and r.get("ertelendi") and "önceki toplantının sonu bitince açılacak" in R.gunluk(), str(r))
        DUR.update(sekme="t2", baslik="Toplantı iki | Microsoft Teams"); time.sleep(1.5); R.altyazi("ikinci toplantının satırı", DUR["baslik"]); d2 = R.durum(); f2 = d2.get("dosya")
        ok("O5 2. sürüyor, oturum_dosya hâlâ 1.", d2.get("durum") == "suruyor" and f2 != f1 and d2.get("oturum_dosya") == f1, str(d2))
        c = subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", R.canli, "--relay", R.U, "ozet-hazir", ozet("Deneme-Toplanti-bir-ozeti.md")],
                           capture_output=True, text=True, timeout=30, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")))
        ok("O6 1.'nin özeti gönderildi, kaydı 1.'nin dosyasıyla", c.returncode == 0 and son_dosya() == f1, c.stdout + c.stderr + str(son_dosya()))
        time.sleep(2); d = R.durum()
        ok("O7 2. özetle bitmedi, sürüyor", d.get("durum") == "suruyor" and d.get("dosya") == f2 and "(özet hazır) · " + f2 not in R.gunluk(), str(d))
        ok("O8 ertelenen oturum açıldı (önceki toplantının özeti hazır)", bekle(lambda: acildi() == 2, 15) and "ertelenen toplantı oturumu açılıyor (önceki toplantının özeti hazır)" in R.gunluk()
           and "ertelenen oturum açılmadı" not in R.gunluk(), R.gunluk()[-900:])
        d = R.durum(); ok("O9 oturum artık 2.'nin: oturum_dosya yok, kayıtta oturum var", not d.get("oturum_dosya") and d.get("oturum") and not d.get("neden"), str(d))
        DUR["sekme"] = None; R.cik("teams", "Toplantı iki | Microsoft Teams", "t2")
        ok("O10 2. bitti", bekle(lambda: R.durum()["durum"] == "bos", 40), str(R.durum()))
        DUR.update(sekme="t3", baslik="Toplantı üç | Microsoft Teams"); time.sleep(1.5); R.altyazi("üçüncü toplantının satırı", DUR["baslik"])
        ok("O11 3. kendiliğinden tanındı, oturum ertelendi (eski oturuma bağlanmadı)", bekle(lambda: R.durum().get("durum") == "suruyor" and "OTO: " in R.gunluk()
           and "önceki toplantının sonu bitince açılacak" in R.gunluk().split("Toplantı iki")[-1], 10) and acildi() == 2, str(R.durum()) + R.gunluk()[-700:])
        f3 = R.durum().get("dosya")
        r = R.istek("/son-toplanti", {"ozet": ozet("Deneme-Toplanti-iki-ozeti.md"), "baslik": "Toplantı iki", "dosya": f3})  # eski istemci: süren toplantının dosyası
        time.sleep(2); d = R.durum()
        ok("O12 eski istemcinin özeti 3.'yü bitirmedi, önceki toplantıya sayıldı", r.get("ok") and d.get("durum") == "suruyor" and d.get("dosya") == f3 and "önceki toplantıya sayıldı" in R.gunluk(), str(d))
        ok("O13 3.'nün ertelenen oturumu açıldı", bekle(lambda: acildi() == 3, 15) and not R.durum().get("oturum_dosya"), R.gunluk()[-700:])
        ok("O hata yok", "Traceback" not in R.gunluk(), R.gunluk()[-1500:])
    finally: DUR["sekme"] = "dur"; R.kapat(); R.sil()

def senaryo_P():
    print("— P) 3 Kasım canlı: 1. bitiyor'dayken 2. Başlat'la açılır (1. kapanır, 2. aynı anda) → izle 1.'nin bitişini kaçırmaz, 2.'ye geçmez; özet gelmezse 2.'nin oturumu yine açılır; terminal kipi beklemez")
    T, R, DUR, acildi, ozet, son_dosya = oturumlu(); iz = None; izl = os.path.join(T, "izle.log")
    izle_oku = lambda: open(izl, encoding="utf-8").read()
    try:
        R.istek("/baslat", {"konu": "Toplantı bir", "platform": "teams"}); DUR.update(sekme="t1", baslik="Toplantı bir | Microsoft Teams"); time.sleep(1.5)
        R.altyazi("birinci toplantının satırı", DUR["baslik"]); f1 = R.durum().get("dosya")
        iz = subprocess.Popen([sys.executable, "-u", "-B", os.path.join(T, "toplanti-claude.py"), "--dir", R.canli, "--relay", R.U, "izle"], cwd=T, stdout=open(izl, "w"), stderr=subprocess.STDOUT,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")))
        ok("P1 izle 1. toplantının dosyasında", bekle(lambda: f"DOSYA: {f1}" in izle_oku(), 30), izle_oku()[-800:])
        DUR["sekme"] = None; R.cik("teams", DUR["baslik"], "t1")
        ok("P2 1. bitiyor (çağrıdan çıkıldı)", bekle(lambda: R.durum()["durum"] == "bitiyor", 10), str(R.durum()))
        r = R.istek("/baslat", {"konu": "Toplantı iki", "platform": "teams"}); d = R.durum(); f2 = d.get("dosya")
        ok("P3 2. Başlat: 1. kapandı, 2. açıldı, oturum ertelendi, oturum_dosya = 1.", r.get("ertelendi") and f2 != f1 and d.get("oturum_dosya") == f1, f"{r} {d}")
        DUR.update(sekme="t2", baslik="Toplantı iki | Microsoft Teams"); time.sleep(1.5); R.altyazi("ikinci toplantının satırı", DUR["baslik"])
        ok("P4 izle 1.'nin bitişini bildirdi (TOPLANTI BİTTİ)", bekle(lambda: "TOPLANTI BİTTİ (tarayıcıda çağrıdan çıkıldı)" in izle_oku(), 12), izle_oku()[-1200:])
        time.sleep(3); ok("P5 izle 2.'nin dosyasına geçmedi (2.'nin satırı eski oturuma gitmedi)", f"DOSYA: {f2}" not in izle_oku() and "ikinci toplantının satırı" not in izle_oku(), izle_oku()[-1200:])
        ok("P6 özet gelmedi: 2.'nin oturumu bekleme süresi dolunca yine açıldı", bekle(lambda: acildi() == 2, 40) and "ertelenen toplantı oturumu açılıyor (bekleme süresi doldu)" in R.gunluk(), R.gunluk()[-900:])
        d = R.durum(); ok("P7 oturum artık 2.'nin; izle 2.'ye geçti", not d.get("oturum_dosya") and d.get("oturum") and bekle(lambda: f"DOSYA: {f2}" in izle_oku(), 10), str(d) + izle_oku()[-500:])
        ok("P hata yok", "Traceback" not in R.gunluk() + izle_oku(), (R.gunluk() + izle_oku())[-1500:])
    finally:
        if iz: iz.terminate(); iz.wait(5)
        DUR["sekme"] = "dur"; R.kapat(); R.sil()
    # özetten sonra eski oturumun süren turu kısa süre bitirilir (canlı: yeni oturum eskisini ölçüm raporunun ortasında kapattı)
    T, R, DUR, acildi, ozet, son_dosya = oturumlu()
    try:
        R.istek("/baslat", {"konu": "Toplantı bir", "platform": "teams"}); DUR.update(sekme="t1", baslik="Toplantı bir | Microsoft Teams"); time.sleep(1.5)
        R.altyazi("birinci toplantının satırı", DUR["baslik"]); f1 = R.durum().get("dosya")
        DUR["sekme"] = None; R.cik("teams", DUR["baslik"], "t1"); bekle(lambda: R.durum()["durum"] == "bitiyor", 10)
        R.istek("/baslat", {"konu": "Toplantı iki", "platform": "teams"}); DUR.update(sekme="t2", baslik="Toplantı iki | Microsoft Teams"); time.sleep(1.5)
        R.istek("/son-toplanti", {"ozet": ozet("Deneme-bir.md"), "baslik": "Toplantı bir", "dosya": f1}); t = time.time()
        ok("P8 özetten sonra eski oturumun turu bitirilir, sonra 2.'nin oturumu açılır", bekle(lambda: acildi() == 2, 20) and time.time() - t >= 3 and son_dosya() == f1
           and "(önceki toplantının özeti hazır)" in R.gunluk(), f"{round(time.time() - t, 1)} sn · " + R.gunluk()[-700:])
    finally: DUR["sekme"] = "dur"; R.kapat(); R.sil()
    # terminal kipi (ayar toplanti_terminal): aktarıcı oturumu tutmaz — 2. toplantının Başlat'ı beklemeden yeni Terminal oturumu açar
    T, R, DUR, acildi, ozet, son_dosya = oturumlu({"toplanti_terminal": True})
    try:
        R.istek("/baslat", {"konu": "Toplantı bir", "platform": "teams"}); DUR.update(sekme="t1", baslik="Toplantı bir | Microsoft Teams"); time.sleep(1.5)
        R.altyazi("birinci toplantının satırı", DUR["baslik"]); DUR["sekme"] = None; R.cik("teams", DUR["baslik"], "t1"); bekle(lambda: R.durum()["durum"] == "bitiyor", 10)
        r = R.istek("/baslat", {"konu": "Toplantı iki", "platform": "teams"})
        ok("P9 terminal kipi: 2. Başlat ertelenmedi, Terminal oturumu yazıldı", r.get("ok") and not r.get("ertelendi") and "Toplantı iki · rol" in R.gunluk() and "Terminalde Claude" in R.gunluk().split("Toplantı iki")[-1]
           and not R.durum().get("oturum_dosya"), f"{r} " + R.gunluk()[-600:])
    finally: DUR["sekme"] = "dur"; R.kapat(); R.sil()

def senaryo_Q():
    print("— Q) tek call=false nabzı toplantıyı bitirmez; iki false ≥ 3 sn bitirir; açık bitiş beklemez (3 Kasım 17:12)")
    R = Aktarici([])
    try:
        R.ping("teams", True, "Toplantı | Microsoft Teams", "t1"); R.altyazi("ilk söz", "Toplantı | Microsoft Teams")
        ok("Q1 sürüyor", bekle(lambda: R.durum().get("durum") == "suruyor", 10), str(R.durum()))
        R.ping("teams", False, "Toplantı | Microsoft Teams", "t1"); R.ping("teams", True, "Toplantı | Microsoft Teams", "t1")  # tek false + hemen true
        time.sleep(0.5); R.ping("teams", False, "Toplantı | Microsoft Teams", "t1"); time.sleep(3.3); R.ping("teams", True, "Toplantı | Microsoft Teams", "t1")  # sayaç sıfırlandı: ilk false 3 sn önce ama araya true girdi
        R.ping("teams", False, "Toplantı | Microsoft Teams", "t1")
        time.sleep(1); g = R.gunluk()
        ok("Q2 tek false nabzı: durum sürüyor, özet başlamadı", R.durum().get("durum") == "suruyor" and "ÖZET (hızlı)" not in g and "tarayıcıda çağrıdan çıkıldı" not in g, str(R.durum()))
        R.ping("teams", False, "Toplantı | Microsoft Teams", "t1"); time.sleep(1)  # iki false ama aralık < 3 sn
        ok("Q3 iki false ama < 3 sn: hâlâ sürüyor", R.durum().get("durum") == "suruyor" and "ÖZET (hızlı)" not in R.gunluk(), str(R.durum()))
        time.sleep(2.4); R.ping("teams", False, "Toplantı | Microsoft Teams", "t1")  # ilk false'tan ≥ 3 sn, ardışık
        ok("Q4 ardışık iki false, ≥ 3 sn: bitiyor", bekle(lambda: R.durum().get("durum") == "bitiyor", 5), str(R.durum()))
        ok("Q5 çıkış nedeni günlükte", "suruyor → bitiyor (tarayıcıda çağrıdan çıkıldı)" in R.gunluk(), R.gunluk()[-500:])
    finally: R.kapat(); R.sil()
    R = Aktarici([])
    try:
        R.ping("teams", True, "Toplantı | Microsoft Teams", "t1"); R.altyazi("ilk söz", "Toplantı | Microsoft Teams")
        bekle(lambda: R.durum().get("durum") == "suruyor", 10)
        t = time.time(); R.istek("/toplanti", {"islem": "bitir"})
        ok("Q6 POST bitir: anında bitiyor (bekleme yok)", R.durum().get("durum") in ("bitiyor", "bos") and time.time() - t < 3, str(R.durum()))
    finally: R.kapat(); R.sil()
    R = Aktarici([])
    try:
        R.masaustu(True); R.whisper("ilk söz"); R.masaustu(False)
        ok("Q7 masaüstü toplantı bitişi: anında bitiyor", R.durum().get("durum") == "bitiyor", str(R.durum()))
    finally: R.kapat(); R.sil()

for s in [s for s in (senaryo_JK, senaryo_A, senaryo_B, senaryo_CDE, senaryo_FG, senaryo_H, senaryo_L, senaryo_M, senaryo_N, senaryo_O, senaryo_P, senaryo_Q) if not sys.argv[1:] or s.__name__[8:] in sys.argv[1:]]:  # ör. test/toplanti.py L M
    try: s()
    except Exception as e: ok(f"{s.__name__} istisna {e.__class__.__name__}: {e}", False)
print(f"toplantı kaydı: {len(HATA)} sorun" + "".join(f"\n  KALDI: {h}" for h in HATA) if HATA else "toplantı kaydı: ✓ tüm senaryolar")
sys.exit(1 if HATA else 0)
