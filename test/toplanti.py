#!/usr/bin/env python3
# Faz B (v0.149.0) — tek toplantı kaydı (aktarici/toplanti.py). Her senaryo kendi yalıtılmış aktarıcısında (SUFLOR_TEST_HIZLI: sinyal 6 sn, bitiyor 8 sn):
#  A) eklenti yok — Meet web: ses yardımcısı Chrome'u dinliyor + takvimde Meet → kayıt takvim adıyla, platform meet, oturum yerine öneri; ses ve menü mikrofonu
#     (tut) kabul; ses kesilince bitiş.  B) eklenti yok — Teams web + elle Başlat: ad Başlat konusu, ikinci Başlat aynı dosya.
#  C) masaüstü Teams, pencere başlığı kişi adı → dosya adında kişi adı yok.  D) 1826-teams B2: masaüstü toplantı biter, 70 sn sonra Başlat "Test" → iki dosya,
#     yenisinin olayları yenisinde; E) 296 sn gecikmiş satır: bitiyor'da eski dosyaya, bitti'den sonra yazılmaz (GEÇ SATIR, gec_atilan).
#  F) Meet kodlu sayfa başlığı → dosya adı takvimden.  G) 2016-meet B1: çağrısız Teams sekmesi çağrıdaki Meet'i ezmez.
#  H) kısa kopma aynı dosya; aktarıcı yeniden başlayınca aynı dosya; elle bitir → sekme hâlâ çağrıda iken yeniden açılmaz.
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
    def __init__(self, olaylar=(), T=None):
        self.T = T or os.path.realpath(tempfile.mkdtemp(prefix="toplanti-")); self.canli = os.path.join(self.T, "canli"); os.makedirs(self.canli, exist_ok=True)
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
                                           SUFLOR_TEST_KULAKLIK="0"))
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

for s in (senaryo_JK, senaryo_A, senaryo_B, senaryo_CDE, senaryo_FG, senaryo_H):
    try: s()
    except Exception as e: ok(f"{s.__name__} istisna {e.__class__.__name__}: {e}", False)
print(f"toplantı kaydı: {len(HATA)} sorun" + "".join(f"\n  KALDI: {h}" for h in HATA) if HATA else "toplantı kaydı: ✓ tüm senaryolar")
sys.exit(1 if HATA else 0)
