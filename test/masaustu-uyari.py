#!/usr/bin/env python3
# Masaüstü toplantı kartları (aktarici/masaustu-uyari.py, 13 Kasım): POST /ortak-mik (menü uygulaması OrtakMik raporu) ve panodaki iki kart.
#  A) toplantiya_ses açık, masaüstü Teams, mikrofon açık, BlackHole okunmuyor → süre dolmadan kart yok; sonra "mikrofonu BlackHole değil" kartı bir kez;
#     bilgi kartı ("eklenti gerekmez") bir kez; toplantı bitip yenisi başlayınca ikisi de yeniden (toplantı başına bir kez).
#  B) BlackHole okunuyor → uyarı yok.  C) rapor hiç yok → uyarı yok, günlüğe tek satır.  D) ayar kapalı → uyarı yok (bilgi kartı var).
#  E) web toplantısı (eklenti çağrıda) → ikisi de yok.  F) Teams'te sessizde → uyarı yok.  Anahtarsız /ortak-mik reddedilir.
#  G) "Eklenti çalışmıyor" (/status toplanti.mic_bilinmiyor): mikrofonu tutan uygulama masaüstü Teams'se yok, Chrome'sa var.
# Yalıtılmış aktarıcılar (SUFLOR_TEST_HIZLI: toplantı ≥ 4 sn, BlackHole ≥ 3 sn okunmuyor, rapor tazeliği 10 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/masaustu-uyari.py      (kaldı → çıkış 1)
import base64, datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""), flush=True)
    if not k: HATA.append(ad)
simdi = datetime.datetime.now().astimezone(); iso = lambda d: d.isoformat(timespec="seconds")
TEAMS = {"id": "e2", "baslik": "Haftalık plan", "baslangic": iso(simdi - datetime.timedelta(minutes=1)), "bitis": iso(simdi + datetime.timedelta(minutes=29)), "tum_gun": False,
         "takvim": "İş", "platform": "teams", "baglanti": "https://teams.microsoft.com/l/meetup-join/x", "katilimcilar": ["Ayşe Örnek"], "kisi_sayisi": 2}

class Aktarici:
    def __init__(self, ad, toplantiya_ses=True, takvim=False):
        self.ad = ad; self.T = os.path.realpath(tempfile.mkdtemp(prefix=f"mu-{ad}-")); self.canli = os.path.join(self.T, "canli"); os.makedirs(self.canli)
        self.port = bos_port(8771); self.U = f"http://127.0.0.1:{self.port}"; self.log = os.path.join(self.T, "relay.log")
        json.dump({"durum": "ok", "olaylar": [TEAMS] if takvim else []}, open(os.path.join(self.T, "takvim.json"), "w"), ensure_ascii=False)
        os.makedirs(os.path.join(self.T, "Suflor Ses.app"))  # yerel ses "kurulu" sayılsın
        json.dump({"alan": "Deneme", "ad": "Ali T", "port": self.port, "uygulama": self.T, "ortak": "/Users/Shared/Suflor", "konusma": False, "toplantiya_ses": toplantiya_ses},
                  open(os.path.join(self.T, "ayar.json"), "w"))
        for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py"): shutil.copy(os.path.join(KOD, f), self.T)
        for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(self.T, d))
        self.p = subprocess.Popen([sys.executable, "relay.py", "--dir", self.canli, "--port", str(self.port)], cwd=self.T, stdout=open(self.log, "a"), stderr=subprocess.STDOUT,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(self.T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1",
                                           SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_BITIYOR_SN="1"))
    def hazir(self):
        for _ in range(150):
            try: self.istek("/status"); return True
            except Exception: time.sleep(0.1)
        return False
    def istek(self, yol, g=None, anahtar="kart-anahtari.txt", anahtarli=True):
        h = {"Content-Type": "application/json"}
        if anahtarli: h["X-Suflor-Anahtar"] = open(os.path.join(self.canli if anahtar == "kart-anahtari.txt" else self.T, anahtar)).read().strip()
        q = urllib.request.Request(self.U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
        try: return json.load(urllib.request.urlopen(q, timeout=10))
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    def masaustu(self, top, sessiz=False): return self.istek("/masaustu", {"uygulama": "Teams", "toplantida": top, "sessiz": sessiz})
    def om(self, okunuyor, gecis=True): return self.istek("/ortak-mik", {"bh_var": True, "bh_okunuyor": okunuyor, "gecis": gecis})
    def ping(self, call=True): return self.istek("/ping", {"ver": "0.241.0", "meeting": {"title": "abc"}, "panel": False, "rows": 0, "platform": "teams", "call": call, "captions": call, "sekme": "t1", "mic": {"on": call}})
    def ses_nabiz(self, uyg): return self.istek("/ses-yerel", {"nabiz": True, "durum": "dinliyor", "uygulama": uyg, "tepe": 2000}, "ses-anahtari.txt")
    def kartlar(self, parca):
        try: return sum(1 for s in open(os.path.join(self.canli, "kartlar.jsonl"), encoding="utf-8") if s.strip() and parca in (json.loads(s).get("text") or ""))
        except OSError: return 0
    def uyari(self): return self.kartlar("BlackHole")
    def bilgi(self): return self.kartlar("eklentisi gerekmez")
    def gunluk(self): return open(self.log, encoding="utf-8").read()
    def kapat(self):
        self.p.terminate()
        try: self.p.wait(5)
        except subprocess.TimeoutExpired: self.p.kill()
    def sil(self): shutil.rmtree(self.T, ignore_errors=True)

R = {}
try:
    R = {"A": Aktarici("A"), "B": Aktarici("B"), "C": Aktarici("C"), "D": Aktarici("D", toplantiya_ses=False), "E": Aktarici("E"), "F": Aktarici("F"),
         "G1": Aktarici("G1", takvim=True), "G2": Aktarici("G2", takvim=True)}
    ok("aktarıcılar açıldı", all(r.hazir() for r in R.values()))
    ok("anahtarsız /ortak-mik reddedilir", R["A"].istek("/ortak-mik", {"bh_okunuyor": False}, anahtarli=False).get("_kod") == 401)
    def tur():  # her senaryonun bir saniyelik girdisi
        R["A"].masaustu(True); R["A"].om(False)
        R["B"].masaustu(True); R["B"].om(True)
        R["C"].masaustu(True)
        R["D"].masaustu(True); R["D"].om(False)
        R["E"].ping(True); R["E"].om(False)
        R["F"].masaustu(True, sessiz=True); R["F"].om(False)
        for g, u in (("G1", "Teams"), ("G2", "Chrome")):
            R[g].ses_nabiz(u); R[g].istek("/ses-masaustu", {"olay": "acildi", "aygit": "MacBook Pro Mikrofonu"})
            t0 = time.time()
            R[g].istek("/ingest", {"meeting": {"title": "x"}, "source": "whisper", "entries": [{"id": f"w/{t0}", "speaker": "Karşı taraf", "time": "10:00", "text": "merhaba", "kanal": "karsi", "t0": t0, "t1": t0 + 1}]})
    bas = time.time(); erken = None
    while time.time() - bas < 10:
        tur(); time.sleep(1)
        if erken is None and time.time() - bas >= 2: erken = R["A"].uyari()
    ok("A: toplantı süresi dolmadan uyarı kartı yok", erken == 0, f"{erken}")
    ok("A: BlackHole okunmuyor → uyarı kartı bir kez", R["A"].uyari() == 1, f"{R['A'].uyari()}")
    ok("A: bilgi kartı (eklenti gerekmez) bir kez", R["A"].bilgi() == 1, f"{R['A'].bilgi()}")
    ok("A: günlükte uyarı satırı", "MASAÜSTÜ UYARI: BlackHole" in R["A"].gunluk())
    ok("B: BlackHole okunuyor → uyarı yok", R["B"].uyari() == 0 and R["B"].bilgi() == 1, f"{R['B'].uyari()}/{R['B'].bilgi()}")
    ok("C: rapor yok → uyarı yok, günlükte tek satır", R["C"].uyari() == 0 and R["C"].gunluk().count("BlackHole raporu yok") == 1, f"{R['C'].uyari()}/{R['C'].gunluk().count('BlackHole raporu yok')}")
    ok("D: ayar kapalı → uyarı yok (bilgi kartı var)", R["D"].uyari() == 0 and R["D"].bilgi() == 1, f"{R['D'].uyari()}/{R['D'].bilgi()}")
    ok("E: web toplantısı → uyarı ve bilgi kartı yok", R["E"].uyari() == 0 and R["E"].bilgi() == 0 and R["E"].istek("/status")["toplanti"]["durum"] == "suruyor", f"{R['E'].uyari()}/{R['E'].bilgi()}")
    ok("F: Teams'te sessizde → uyarı yok", R["F"].uyari() == 0, f"{R['F'].uyari()}")
    g1, g2 = R["G1"].istek("/status")["toplanti"], R["G2"].istek("/status")["toplanti"]
    ok("G: masaüstü Teams mikrofonu tutuyor → 'Eklenti çalışmıyor' yok", g1.get("durum") == "suruyor" and g1.get("mic_bilinmiyor") is False, json.dumps({k: g1.get(k) for k in ("durum", "mic_bilinmiyor")}))
    ok("G: tarayıcı (Chrome) mikrofonu tutuyor → 'Eklenti çalışmıyor' var", g2.get("durum") == "suruyor" and g2.get("mic_bilinmiyor") is True, json.dumps({k: g2.get(k) for k in ("durum", "mic_bilinmiyor")}))
    ok("G: masaüstü Teams (yalnız ses) → bilgi kartı, Chrome → yok", R["G1"].bilgi() == 1 and R["G2"].bilgi() == 0, f"{R['G1'].bilgi()}/{R['G2'].bilgi()}")
    for k in [k for k in R if k != "A"]: R[k].kapat()
    # A: toplantı biter, yenisi başlar → iki kart yeniden (toplantı başına bir kez)
    a = R["A"]; a.masaustu(False)
    for _ in range(40):
        if a.istek("/status")["toplanti"]["durum"] == "bos": break
        a.om(False); time.sleep(0.5)
    ok("A: ilk toplantı bitti", a.istek("/status")["toplanti"]["durum"] == "bos")
    bas = time.time()
    while time.time() - bas < 9: a.masaustu(True); a.om(False); time.sleep(1)
    ok("A: yeni toplantıda uyarı ve bilgi kartı yeniden (toplam 2'şer)", a.uyari() == 2 and a.bilgi() == 2, f"{a.uyari()}/{a.bilgi()}")
finally:
    for r in R.values():
        try: r.kapat()
        except Exception: pass
    if HATA:
        for r in R.values(): print(f"--- {r.ad} günlük: {r.log}")
    else:
        for r in R.values(): r.sil()
print("SONUÇ:", "geçti" if not HATA else f"{len(HATA)} kaldı: {HATA}")
sys.exit(1 if HATA else 0)
