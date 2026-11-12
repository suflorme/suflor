#!/usr/bin/env python3
# Karşı kanal devri ve sahte masaüstü toplantı (v0.238.1; 12 Kasım 22.00 toplantısı: ses yardımcısı Chrome'daki toplantıda masaüstü Teams'e geçti,
# yalnız sıfır ses verdi; sıfır ses parçaları eklentinin karşı parçalarını da atıyordu; 00.02'de toplantı dışında mikrofonu tutan masaüstü Teams sahte
# "Teams toplantısı" kaydı açtı).
#   A) yardımcı sıfır ses verirken eklentinin sekme sesi (duyulur) ≥ 2 sn sürünce karşı kanal eklentiye geçer; yardımcının sessiz parçaları Whisper'a
#      karışmaz; yardımcı yeniden duyulur ses verince geri döner. İkisi de çalışırken (yardımcı duyulur) eklentinin parçaları atılmayı sürdürür.
#   B) menü uygulaması masaüstü Teams'i "toplantı yok" diye bildirirken Teams'in mikrofonu tutması (sıfır ses) kayıt açmaz; menü uygulaması yokken ya da
#      Teams duyulur ses çıkarıyorsa eski davranış (ses sinyaliyle kayıt) sürer.
# Aktarıcıda yerel_ses_al / yerel_devir / ses_al (whisper-hat.py) / sinyaller (toplanti.py) değişince koştur (~40 sn; gerçek yardımcı ve model gerekmez):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/karsi-devir.py
import base64, glob, json, math, os, shutil, struct, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); KOKEN = "http://karsi.deneme"
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""), flush=True)
    if not k: HATA.append(ad)
# parça Whisper aşamasına ulaştı mı (deneme aktarıcısında Whisper yok: "kapali"; atılan parça "yerel"/"eklenti" döner)
kanala = lambda r: ("durum" in r or r.get("kapali") is True) and not r.get("yerel") and not r.get("eklenti")
SIFIR = base64.b64encode(b"\0\0" * 8000).decode()  # 0,5 sn sessizlik
SESLI = base64.b64encode(b"".join(struct.pack("<h", int(4000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(8000))).decode()  # 0,5 sn ton

class Aktarici:
    def __init__(self):
        self.T = os.path.realpath(tempfile.mkdtemp(prefix="karsi-devir-")); self.canli = os.path.join(self.T, "canli"); os.makedirs(self.canli)
        self.port = bos_port(8781); self.U = f"http://127.0.0.1:{self.port}"; self.log = os.path.join(self.T, "relay.log")
        os.makedirs(os.path.join(self.T, "Suflor Ses.app"))  # yerel ses "kurulu"
        # ortak = deneme klasörü: gerçek whisper-venv bulunmasın (model yüklenmez; Whisper "yok" olsa da devir kararı ondan önce)
        json.dump({"alan": "Deneme", "ad": "Ali T", "port": self.port, "uygulama": self.T, "ortak": self.T, "konusma": False}, open(os.path.join(self.T, "ayar.json"), "w"))
        json.dump({"durum": "ok", "olaylar": []}, open(os.path.join(self.T, "takvim.json"), "w"))
        for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py"): shutil.copy(os.path.join(KOD, f), self.T)
        for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(self.T, d))
        self.p = subprocess.Popen([sys.executable, "relay.py", "--dir", self.canli, "--port", str(self.port)], cwd=self.T, stdout=open(self.log, "a"), stderr=subprocess.STDOUT,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(self.T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTO="1",
                                           SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_TEST_KOKEN=KOKEN))
        for _ in range(100):
            try: self.istek("/status"); return
            except Exception: time.sleep(0.1)
    def kapat(self): self.p.terminate(); self.p.wait(5); shutil.rmtree(self.T, ignore_errors=True)
    def istek(self, yol, g=None, anahtar="kart-anahtari.txt"):
        k = open(os.path.join(self.canli if anahtar == "kart-anahtari.txt" else self.T, anahtar)).read().strip()
        h = {"Content-Type": "application/json", "X-Suflor-Anahtar": k}
        if yol == "/ses": h["Origin"] = KOKEN  # eklentinin sekme sesi (deneme kökeni)
        q = urllib.request.Request(self.U + yol, data=json.dumps(g).encode() if g is not None else None, headers=h)
        return json.load(urllib.request.urlopen(q, timeout=10))
    def nabiz(self, uyg="Teams", tepe=0): return self.istek("/ses-yerel", {"nabiz": True, "durum": "dinliyor", "uygulama": uyg, "tepe": tepe, "surum": "0.24.0", "kurma": 0}, "ses-anahtari.txt")
    def yerel(self, pcm=SIFIR): return self.istek("/ses-yerel", {"t": int(time.time() * 1000), "pcm": pcm}, "ses-anahtari.txt")
    def eklenti(self, pcm=SESLI): return self.istek("/ses", {"kanal": "karsi", "t": int(time.time() * 1000), "pcm": pcm})
    def ping(self, call=True): return self.istek("/ping", {"ver": "0.238.1", "meeting": {"title": "Haftalık plan"}, "panel": False, "rows": 0, "platform": "teams",
                                                           "call": call, "captions": call, "sekme": "t1", "mic": {"on": call}})
    def masaustu(self, top): return self.istek("/masaustu", {"uygulama": "Teams", "toplantida": top})
    def durum(self): return self.istek("/status")["toplanti"]["durum"]
    def md(self): return sorted(os.path.basename(f) for f in glob.glob(os.path.join(self.canli, "*.md")))
    def gunluk(self): return open(self.log, encoding="utf-8").read()

# --- A) karşı kanal devri ---------------------------------------------------------------------------------------------------------------------------------
R = Aktarici()
try:
    R.ping(); R.nabiz(); time.sleep(0.5)
    ok("A0 Chrome'daki Teams toplantısı kaydı açık", R.durum() in ("algilandi", "suruyor"), R.durum())
    y0 = R.yerel(); ok("A1 eklenti yokken yardımcının (sıfır) parçası kanala gider", kanala(y0), str(y0))
    e0 = R.eklenti(); ok("A-2 eklentinin ilk duyulur parçası hemen geçmez (yardımcı son 3 sn'de parça verdi; kanıt < 2 sn)", e0.get("yerel") is True, str(e0))
    ey, yy = [], []
    t0 = time.time()
    while time.time() - t0 < 3.5:
        yy.append(R.yerel()); ey.append(R.eklenti()); time.sleep(0.4)
    ok("A3 yardımcı sıfır, eklenti ≥ 2 sn duyulur: eklentinin parçaları geçer", kanala(ey[-1]) and kanala(ey[-2]), str(ey[-2:]))
    ok("A4 devirde yardımcının sessiz parçası kanala karışmaz", yy[-1].get("eklenti") is True, str(yy[-1]))
    ok("A5 devir günlükte bir kez", R.gunluk().count("YEREL SES: yardımcı sessiz — karşı kanal eklentinin sekme sesinden") == 1)
    for _ in range(4): R.eklenti(SIFIR); time.sleep(0.3)
    ok("A6 karşı taraf sustu (eklenti sessiz): devir sürer, aç-kapa yok", R.yerel().get("eklenti") is True and kanala(R.eklenti(SIFIR)))
    y2 = R.yerel(SESLI); ok("A7 yardımcı yeniden duyulur ses verdi: parçası kanala gider", kanala(y2), str(y2))
    e2 = R.eklenti(); ok("A8 ...ve eklentinin parçası yine atılır (çift satır yok)", e2.get("yerel") is True, str(e2))
    ok("A9 geri dönüş günlükte", "YEREL SES: karşı kanal yeniden yardımcıdan" in R.gunluk())
    # ikisi de çalışıyor: söz başında eklentinin parçası yardımcıdan önce gelse de devir olmaz
    ey = []; t0 = time.time()
    while time.time() - t0 < 3.5:
        ey.append(R.eklenti()); R.yerel(SESLI); time.sleep(0.4)
    ok("A10 ikisi de duyulur: eklentinin parçaları hep atılır, devir yok", all(x.get("yerel") is True for x in ey) and R.gunluk().count("karşı kanal eklentinin sekme sesinden") == 1, str(ey))
    ok("A11 aktarıcıda hata yok", "Traceback" not in R.gunluk())
finally:
    R.kapat()

# --- B) masaüstü Teams açık ama toplantıda değil: kayıt açılmaz -----------------------------------------------------------------------------------------
def senaryo(menu, tepe):
    R = Aktarici()
    try:
        if menu is not None: R.masaustu(menu)
        t0 = time.time(); kayit = False
        while time.time() - t0 < 9:  # SUFLOR_TEST_HIZLI: SES_SESSIZ_SN 6
            if menu is not None: R.masaustu(menu)
            R.nabiz("Teams", tepe); R.yerel(SESLI if tepe else SIFIR); time.sleep(0.5)
            kayit = kayit or R.durum() != "bos"
        return kayit, R.md(), "Traceback" in R.gunluk()
    finally:
        R.kapat()
k, md, tb = senaryo(False, 0)
ok("B1 menü 'Teams toplantı yok' + Teams mikrofonu tutuyor, sıfır ses: kayıt açılmaz", not k and not md, str(md))
ok("B2 hata yok", not tb)
k, md, tb = senaryo(None, 0)
ok("B3 menü uygulaması yokken eski davranış: ses sinyaliyle kayıt açılır", k)
k, md, tb = senaryo(False, 2000)
ok("B4 menü 'toplantı yok' ama Teams duyulur ses çıkarıyor ('Ayrıl' okunamadı): kayıt açılır", k)
ok("B5 hata yok", not tb)
print("karşı devir:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
