# Suflor.me aktarıcı bölümü: Whisper hattı: işçi, ses izi, taslak, yankı. Ayrı modül değildir — relay.py bunu kendi ad alanında, eski yerinde çalıştırır (bolum("whisper-hat")):
# STATE, LOCK, AYAR, write, _t … relay.py'nin; buradaki tanımlar da relay.py'ye aittir. import etme. Python 3.9 uyumlu.
# --- Whisper: yerel konuşma tanıma -------------------------------------------------------------------------------
# 1 Ekim gerçek ses testi (iç test raporu): aynı kayıtta Teams altyazısı Türkçede %25 kelime
# hatası, proje terimlerinde 3/12; Whisper (large-v3-turbo, yerel) %8, 9/12. kullanıcı: Whisper'a geç.
# Akış: eklenti ses parçalarını POST /ses ile gönderir — kanal "ben" (Teams sayfasındaki mikrofon, içerik betiği) ve
# "karsi" (Teams sekmesinin sesi = diğer katılımcılar; popup ile, offscreen belgesi — ya da yerel ses yardımcısı). Aktarıcı her kanalı
# sessizliğe göre konuşma parçalarına böler (enerji tabanlı VAD: ses etkinliği algılama), parçaları Whisper işçisine
# (whisper-isci.py, whisper-venv Python'uyla alt süreç; model bir kez yüklenir) verir, metni ingest() ile normal satır
# olarak yazar (src "whisper"). Konuşmacı: ben kanalı → kullanıcının adı; karsi kanalı → aynı anlarda Teams altyazısında
# görünen ad (altyazı açıksa), tek karşı konuşmacı varsa onun adı, yoksa "Karşı taraf".
# Çift satır olmasın: bir kanal Whisper'a akarken o tarafın altyazı/döküm satırları .md/.jsonl'e değil
# <toplantı>.altyazi.log'a gider (konuşmacı eşleme ve karşılaştırma için). Whisper o kanaldan 90 sn satır üretmezse
# altyazı yeniden yazılır (sessiz kalma/bozulma güvencesi). Ses diske yazılmaz; yalnız metin.
import base64, subprocess, queue
try: import audioop  # Python ≤ 3.12 (sistem 3.9)
except ImportError: audioop = None
_UYG = os.path.dirname(os.path.abspath(__file__)); _APP = AYAR["uygulama"]; _ORT = AYAR["ortak"]
def _ilk(*yollar): return next((y for y in yollar if os.path.exists(y)), yollar[-1])
# önce ortak klasör (/Users/Shared/Suflor, iki hesap), sonra eski yerler (aktarıcının yanı, hesabın App Support'u)
WH_PY = _ilk(os.path.join(_ORT, "whisper-venv", "bin", "python"), os.path.join(_UYG, "whisper-venv", "bin", "python"), os.path.join(_APP, "whisper-venv", "bin", "python"))
WH_ISCI = _ilk(os.path.join(_UYG, "whisper-isci.py"), os.path.join(_APP, "whisper-isci.py"))
WH_MODELLER = _ilk(os.path.join(_ORT, "whisper-modeller"), os.path.join(_UYG, "whisper-modeller"), os.path.join(_APP, "whisper-modeller"))
# Model diskteki anlık görüntüsünden (snapshot) doğrudan açılır: ortak klasör diğer hesap için salt okunur, HF önbelleği
# kilit dosyası yazamaz. Bulunamazsa eskisi gibi depo adı + HF_HOME.
WH_MODEL = next(iter(sorted(glob.glob(os.path.join(WH_MODELLER, "hub", "models--mlx-community--whisper-large-v3-turbo", "snapshots", "*", "weights.safetensors")))), None)
WH_MODEL = os.path.dirname(WH_MODEL) if WH_MODEL else None
# kurulumun yerelde ürettiği 8 bit turbo (aktarici-kur / modeller-kur) varsa o kullanılır — 0,6 GB daha az bellek,
# aynı doğruluk, parça +0,06 sn. Ayar "whisper_model": "turbo" tam modele döndürür.
_WH_Q8 = os.path.join(WH_MODELLER, "hub", "models--suflor--whisper-large-v3-turbo-q8", "snapshots", "yerel")
if AYAR.get("whisper_model") != "turbo" and os.path.exists(os.path.join(_WH_Q8, "weights.safetensors")): WH_MODEL = _WH_Q8
WH_SR = 16000; WH_KARE = 320  # 20 ms
# parça üst sınırı 12 → 6 sn. Ölçüm (6 Ekim, 115 sn kesintisiz Türkçe, gerçek zamanlı): kelime → satır ortanca 7,7 → 4,6 sn,
# %90 12,2 → 6,7 sn; WER 12 sn %16,0 · 8 sn %11,9 · 6 sn %15,6–18,1 (aynı ayarda tur farkı kadar — kesim noktasına bağlı gürültü)
WH_SESSIZ_MS = 700; WH_ON_MS = 300; WH_MAX_SN = 6; WH_MIN_KONUSMA_MS = 400; WH_BOSTA_KAPAT_SN = 600
WH_AKIS_SN = 20; WH_GUVENCE_SN = 90; WH_ATLA_SN = 120
# kuyruk birikince aynı kanalın sıradaki parçaları tek çağrıda: işçi süresi parça boyundan bağımsız ~1,2 sn (7 Ekim 18:03 ölçümü:
# <2 sn 1,15 · 4–6 sn 1,24), kuyruk iki dönemde 25–27 parçaya çıkıp gecikme 135 sn'yi buldu. ben kanalı yalnız karşı akmıyorken
# birleşir: yankı süzgeci parçanın tamamını atar, birleşik parçada kullanıcının gerçek sözleri de giderdi.
WH_BIRLES_ESIK = 3; WH_BIRLES_MAX_SN = 18; WH_BIRLES_ARA = b"\x00\x00" * int(WH_SR * 0.25)
STATE["whisper"] = {"durum": "kapali", "model": None, "kuyruk": 0, "satir": 0, "atlanan": 0, "son_sn": None, "gecikme_sn": None,
                    "hata": None, "kanallar": {}, "kanal_son_satir": {}, "kanal_son_parca": {}, "gecikme_max": 0.0, "durgun_max": 0.0,
                    "parca": {}, "eski_atlanan": {}, "birlesen": {}}  # kanal başına: kuyruğa giren · 120 sn'yi geçip atılan · birleştirilen
W_LOCK = threading.Lock(); WH_Q = queue.Queue(); ALTYAZI_SON = []  # (epoch, konuşmacı) son 10 dk
def wh_one_al(is_):  # bas-konuş işi kuyruğun başına (S24): toplantı sonundan kalan parçalar "evet"i bekletmesin
    with WH_Q.not_empty: WH_Q.queue.appendleft(is_); WH_Q.unfinished_tasks += 1; WH_Q.not_empty.notify()
def _rms(b):
    if audioop: return audioop.rms(b, 2)
    import array; a = array.array("h"); a.frombytes(b); return int((sum(x * x for x in a) / max(1, len(a))) ** 0.5)
class Kanal:
    def __init__(self, ad): self.ad = ad; self.reset(); self.gurultu = 300.0; self.son_bitis = 0.0; self.onceki = ""; self.baslangic = time.time()
    def reset(self): self.parca = bytearray(); self.on = bytearray(); self.konusuyor = False; self.sessiz = 0; self.sesli = 0; self.ust = 0; self.t0 = 0.0; self.rmsler = []
    def besle(self, pcm, t_bas, baslik):
        if t_bas - self.son_bitis > 0.5 and self.konusuyor: self.kes(baslik)  # boşluk (mikrofon kapalıydı / parça kayıp)
        if time.time() - STATE["whisper"]["kanallar"].get(self.ad, 0) > WH_AKIS_SN: self.baslangic = time.time()
        STATE["whisper"]["kanallar"][self.ad] = time.time()
        for i in range(0, len(pcm) - WH_KARE * 2 + 1, WH_KARE * 2):
            kare = bytes(pcm[i:i + WH_KARE * 2]); t = t_bas + i / 2 / WH_SR; r = _rms(kare)
            esik = max(220.0, self.gurultu * 2.8)
            if not self.konusuyor:
                self.gurultu = self.gurultu * 0.98 + r * 0.02 if r < self.gurultu * 2.5 else self.gurultu * 0.999 + r * 0.001
                self.on += kare; self.on = self.on[-int(WH_SR * WH_ON_MS / 1000) * 2:]
                self.ust = self.ust + 1 if r > esik else 0
                if self.ust >= 3:
                    self.konusuyor = True; self.t0 = t - len(self.on) / 2 / WH_SR; self.parca = bytearray(self.on); self.sesli = 3; self.sessiz = 0
                    self.rmsler = [0] * (len(self.on) // (WH_KARE * 2))
            else:
                self.parca += kare; self.rmsler.append(r)
                if r > esik: self.sesli += 1; self.sessiz = 0
                else: self.sessiz += 1
                if self.sessiz * 20 >= WH_SESSIZ_MS: self.kes(baslik)
                elif len(self.parca) >= WH_MAX_SN * WH_SR * 2: self.bol(baslik)
        self.son_bitis = t_bas + len(pcm) / 2 / WH_SR
    def bol(self, baslik):
        # uzun kesintisiz konuşma: son 1,5 sn'nin en sessiz karesinden böl (kelime ortasından kesmemek için), kalan sürer
        son = self.rmsler[-75:]; j = len(self.rmsler) - len(son) + min(range(len(son)), key=son.__getitem__)
        kalan, kalan_r, t_kalan = self.parca[j * WH_KARE * 2:], self.rmsler[j:], self.t0 + j * WH_KARE / WH_SR
        self.parca = self.parca[:j * WH_KARE * 2]; self.sessiz = 0; self.kes(baslik)
        self.konusuyor = True; self.parca = bytearray(kalan); self.rmsler = kalan_r; self.t0 = t_kalan; self.sesli = sum(1 for x in kalan_r if x > 0)
    def kes(self, baslik):
        if self.konusuyor and self.sesli * 20 >= WH_MIN_KONUSMA_MS:
            fazla = max(0, self.sessiz - 10) * WH_KARE * 2  # sondaki sessizliğin 200 ms'i kalsın
            pcm = bytes(self.parca[:len(self.parca) - fazla] if fazla else self.parca)
            WH_Q.put({"id": f"w-{self.ad}-{int(self.t0 * 1000)}", "kanal": self.ad, "t0": self.t0, "t1": self.t0 + len(pcm) / 2 / WH_SR,
                      "pcm": pcm, "baslik": baslik, "kuyruga": time.time()})
            STATE["whisper"]["kuyruk"] = WH_Q.qsize(); STATE["whisper"]["kanal_son_parca"][self.ad] = time.time()
            STATE["whisper"]["parca"][self.ad] = STATE["whisper"]["parca"].get(self.ad, 0) + 1
        self.reset()
KANALLAR = {}
def ses_al(p):
    # POST /ses: {"kanal": "ben"|"karsi", "t": ilk örneğin epoch ms'si, "pcm": base64 int16 16 kHz, "meeting": {"title"}}
    w = STATE["whisper"]
    if w["durum"] == "yok": return {"ok": False, "kapali": True, "err": w.get("hata")}
    kanal = "ben" if p.get("kanal") in BEN_ESKI else ("karsi" if p.get("kanal") == "karsi" else None)
    if not kanal: return {"ok": False, "err": "kanal"}
    # yerel ses yardımcısı karşı sesi veriyorsa eklentinin (popup, sekme sesi) karşı parçaları atılır — çift satır olmasın
    try: pcm = base64.b64decode(str(p.get("pcm") or ""), validate=True)
    except Exception: return {"ok": False, "err": "pcm"}
    if kanal == "karsi" and p.get("kaynak") != "yerel":
        if pcm and max(abs(min(memoryview(pcm[:len(pcm) // 2 * 2]).cast("h"), default=0)), max(memoryview(pcm[:len(pcm) // 2 * 2]).cast("h"), default=0)) > 500:
            STATE["yerel_ses"]["eklenti_karsi_ses"] = time.time()  # "izin" kuralının kanıtı
        if time.time() - (STATE["yerel_ses"].get("son") or 0) < 3: return {"ok": True, "yerel": True}
    if len(pcm) > WH_SR * 2 * 10: return {"ok": False, "err": "parça çok büyük"}
    baslik = (p.get("meeting") or {}).get("title") or STATE.get("meeting") or "Toplantı"
    with W_LOCK:
        k = KANALLAR.setdefault(kanal, Kanal(kanal)); k.besle(pcm, (p.get("t") or time.time() * 1000) / 1000.0, baslik)
    _isci_baslat()
    return {"ok": True, "durum": w["durum"]}
def whisper_akiyor(kanal):
    # bu kanal şu an Whisper'a akıyor ve işe yarıyor mu (altyazı satırları gölgeye alınsın mı)
    w = STATE["whisper"]; now = time.time()
    if w["durum"] not in ("hazir", "yukleniyor") or now - w["kanallar"].get(kanal, 0) > WH_AKIS_SN: return False
    k = KANALLAR.get(kanal); bas = k.baslangic if k else now
    # Whisper 47 sn tıkanınca "ben"in son satırı 100 sn önceydi, koruma düştü, altyazı satırları döküme sızdı (çift,
    # saatsiz). Son satır yerine son KUYRUĞA GİREN parçaya da bakılır: parça kuyruktaysa Whisper onu yazacak demektir.
    son = max(w["kanal_son_satir"].get(kanal, 0), w["kanal_son_parca"].get(kanal, 0))
    return now - bas < 60 or now - son < WH_GUVENCE_SN
_BELLEK = {"t": 0, "v": None, "en_cok": []}
BELLEK_AD = {"Google Chrome": "Chrome", "Microsoft Teams": "Teams", "Microsoft Edge": "Edge", "claude": "Claude Code", "Claude": ("Claude uygulaması", "Claude app"),
             "com.apple.WebKit.WebContent": ("Safari sekmeleri", "Safari tabs"), "Code Helper": "VS Code"}
def bellek_ad(k):  # ham ad → arayüz dilinde ad (önbellekte ham ad durur; dil sonradan değişebilir)
    if k.startswith("@"): return _t(f"diğer macOS hesabı ({k[1:]})", f"other macOS account ({k[1:]})")
    a = BELLEK_AD.get(k, k); return _t(*a) if isinstance(a, tuple) else a
def bellek_kullananlar(en_cok=3, esik_gb=0.3):
    # bellek az uyarısında neyi kapatacağını söyle — süreçler uygulama paketine (.app) göre
    # toplanır (Chrome'un yardımcı süreçleri tek "Chrome"); diğer macOS hesabının süreçleri tek kalem; sistem (root, _hesaplar) ve
    # Suflor'un kendi süreçleri (aktarıcı, Whisper işçisi, Suflor Ses) dışarıda. RSS paylaşılan belleği iki kez sayabilir: gösterge, ölçüm değil.
    import pwd
    try: ben = pwd.getpwuid(os.getuid()).pw_name
    except Exception: ben = os.environ.get("USER", "")
    kendi = {os.getpid()} | ({_ISCI["p"].pid} if _ISCI.get("p") else set())
    g = {}
    for l in subprocess.run(["ps", "-axo", "pid=,user=,rss=,comm="], capture_output=True, text=True, timeout=5).stdout.splitlines():
        try: pid, u, r, c = l.strip().split(None, 3); pid = int(pid); gb = int(r) / 2 ** 20
        except ValueError: continue
        if u == "root" or u.startswith("_") or pid in kendi: continue
        if u != ben: ad = "@" + u
        else:
            m = re.search(r"/([^/]+)\.app/", c); ad = m.group(1) if m else os.path.basename(c)
            if ad.startswith("Suflor") or "whisper-venv" in c: continue
        g[ad] = g.get(ad, 0) + gb
    return [(a, round(v, 1)) for a, v in sorted(g.items(), key=lambda kv: -kv[1]) if v >= esik_gb][:en_cok]
def bellek_view():
    # boş bellek panoda da uyarı (3 Ekim: saglik ~3,1 GB dedi, uyarı yalnız Claude sohbetinde kaldı). Ölçüm toplanti-claude.py
    # saglik ile aynı (vm_stat: free + inactive + speculative + purgeable), 60 sn'de bir. Modeller yüklenmeden ~2,5 GB gerekir
    # (Whisper ~2,4; v0.13.12: ses izi içinde); yüklendikten sonra yalnız 1,5 GB altı uyarılır (bellek takası, gecikme).
    if time.time() - _BELLEK["t"] > 60:
        _BELLEK["t"] = time.time()
        try:
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout; sayfa = int(re.search(r"page size of (\d+)", vm).group(1))
            _BELLEK["v"] = round(sum(int(re.search(rf"{k}:\s+(\d+)", vm).group(1)) for k in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable")) * sayfa / 2 ** 30, 1)
        except Exception: _BELLEK["v"] = None
        try: _BELLEK["en_cok"] = bellek_kullananlar()
        except Exception: _BELLEK["en_cok"] = []
    bos = _BELLEK["v"]
    if bos is None: return {"bos_gb": None, "uyari": ""}
    w = STATE["whisper"]; yuklu = w["durum"] in ("hazir", "yok")
    # gerek sayıları suflor-olcum ölçümünden (4 Ekim): Whisper ~2,4 GB; v0.13.12: ses izi Whisper işçisinde (~0,1 GB)
    gerek = 0 if yuklu else (2.0 if WH_MODEL == _WH_Q8 else 2.5)  # q8 ~1,8 GB, tam turbo ~2,4 GB
    az = bos < 1.5 or (gerek and bos < gerek + 0.5)
    sy = (lambda x: str(x)) if ARAYUZ_DILI == "en" else (lambda x: str(x).replace(".", ","))  # ondalık: en 3.1, tr 3,1
    ec = [(bellek_ad(a), v) for a, v in _BELLEK.get("en_cok") or []]
    adlar = ", ".join(f"{a} ~{sy(v)} GB" for a, v in ec)
    son = (_t(f" — en çok: {adlar}; kullanmadığını kapat", f" — biggest: {adlar}; close what you don't need") if adlar else
           _t(" — kullanmadığın uygulama ve sekmeleri kapat", " — close apps and tabs you aren't using"))
    return {"bos_gb": bos, "en_cok": [{"ad": a, "gb": v} for a, v in ec],
            "uyari": _t(f"Bellek az: ~{sy(bos)} GB boş", f"Low memory: ~{sy(bos)} GB free") + (_t(f" (Whisper ~{sy(round(gerek, 1))} GB ister)", f" (Whisper needs ~{sy(round(gerek, 1))} GB)") if gerek else "") + son if az else ""}
def ben_kod():
    # ben_neden'in dilden bağımsız kodu — pano yalnız hata/sorun'da uyarır (sessizde olmak sorun değil)
    m = STATE.get("mic") or {}
    if not m or time.time() - m.get("t", 0) > 60: return "yok"
    return "hata" if m.get("hata") else "kapali" if not m.get("on") else "sessiz" if m.get("sessiz") else "sorun"
def ben_neden():
    # ben kanalı ✗ iken neden — eklentinin son nabzındaki mikrofon durumu (sessizlikte de ses akar; ✗ = ses gelmiyor)
    m = STATE.get("mic") or {}
    if not m or time.time() - m.get("t", 0) > 60: return _t("eklentiden mikrofon bilgisi yok", "no microphone info from the extension")
    if m.get("hata"): return _t("mikrofon açılamadı: ", "microphone could not be opened: ") + m["hata"]
    if not m.get("on"): return _t("mikrofon kanalı açılmadı (toplantıda değil ya da Whisper kapalı)", "microphone channel not open (not in a meeting, or Whisper is off)")
    if m.get("sessiz"): return _t("Teams'te mikrofonun kapalı (sessizde)", "your microphone is muted in the meeting")
    return _t("mikrofon açık ama ses gelmiyor", "microphone is on but no audio is coming in")
def whisper_view():
    w = STATE["whisper"]; now = time.time()
    return {"durum": w["durum"], "ben": now - w["kanallar"].get("ben", 0) < WH_AKIS_SN, "ben_neden": ben_neden(), "ben_kod": ben_kod(), "karsi": now - w["kanallar"].get("karsi", 0) < WH_AKIS_SN,
            "kuyruk": WH_Q.qsize(), "satir": w["satir"], "gecikme_sn": w["gecikme_sn"], "hata": w["hata"],
            "atlanan": w.get("atlanan", 0), "son_sn": w.get("son_sn"), "gecikme_max": w.get("gecikme_max"), "durgun_max": w.get("durgun_max"),
            "parca": w.get("parca"), "eski_atlanan": w.get("eski_atlanan"), "birlesen": w.get("birlesen"),
            "ses_model": STATE["ses_model"]["durum"], "yanki": w.get("yanki", 0), "yerel": yerel_ses_durum(), "yerel_akiyor": now - (STATE["yerel_ses"].get("son") or 0) < 5, "kumeler": {k: kume_adi(k) for k in sorted({k for _, _, k in KUME_BEKLEYEN} | set(KUME_AD))}}
def ben_adi():
    a = agenda().get("ben")
    if a: return a
    for _, k in reversed(ALTYAZI_SON):
        if sade(k).split(" ")[0] == sade(AYAR["ad"]).split(" ")[0]: return k
    return AYAR["ad"]  # hesabın kullanıcı adı (ayar.json "ad")
def istem_metni():
    # Whisper'a önceden verilen terimler (initial_prompt), önem sırasıyla: bu toplantının gündeminde/hazır kartlarında geçenler,
    # kullanıcının eklediği sözlük adları, diğer sözlük adları, sabitler. Sınır belirteçle işçide (whisper-isci.py istem_kur):
    # Whisper 223 belirteci aşan istemin BAŞINI atıyordu — en önemli terimler düşüyordu (7 Ekim ölçümü: 176 + önceki ~45).
    try: ter = json.load(open(os.path.join(BASE, "sozluk.json"), encoding="utf-8")).get("terimler", [])
    except Exception: ter = []
    try: hz = json.load(open(os.path.join(BASE, "hazir.json"), encoding="utf-8")).get("kartlar", [])
    except Exception: hz = []
    ag = agenda(); bu = " ".join([str(ag.get("title") or "")] + [str(x) for x in ag.get("items") or []] + [str(k.get("metin") or "") for k in hz if isinstance(k, dict)]).lower()
    # Tümü küçük harfli sözlük terimi ("product", "customer service") istemde yer yemesin: Whisper genel sözcüğü zaten yazar,
    # istem özel adlar için (9 Ekim: 57 terim 182 belirteç, bütçe 155 → sondaki özel adlar düşüyordu). Sözlük düzeltmesi bundan bağımsız.
    adlar = []
    for t in sorted(ter, key=lambda t: (str(t.get("dogru") or "").strip().lower() not in bu, t.get("kaynak") not in BEN_ESKI)):
        d = str(t.get("dogru") or "").strip().replace(",", " ")
        if d and d != d.lower() and d not in adlar: adlar.append(d)
    for d in ["AWS", "IAM", "MFA", "Google Workspace"] + list(AYAR.get("whisper_terimler") or []):  # ayar: alanın sık sistem adları
        if d not in adlar: adlar.append(d)
    return (", ".join(adlar))[:3000] + "."
_ISCI = {"p": None, "satirlar": None, "kilit": threading.Lock(), "thread": None, "baslik": None}
def _isci_baslat():
    with _ISCI["kilit"]:
        if _ISCI["thread"] and _ISCI["thread"].is_alive(): return
        _ISCI["thread"] = threading.Thread(target=_isci_dongu, daemon=True); _ISCI["thread"].start()
def _isci_ac():
    w = STATE["whisper"]
    if not (os.path.exists(WH_PY) and os.path.exists(WH_ISCI)):
        w.update(durum="yok", hata=f"whisper-venv ya da whisper-isci.py yok ({WH_PY})"); print(f"WHISPER: kullanılamıyor — {w['hata']}"); return False
    w.update(durum="yukleniyor", hata=None); t = time.time()
    env = dict(os.environ, HF_HOME=WH_MODELLER, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", **({"SUFLOR_WHISPER_MODEL": WH_MODEL} if WH_MODEL else {}),
               **({"SUFLOR_ECAPA": ECAPA} if os.path.exists(ECAPA) else {}))
    pr = subprocess.Popen([WH_PY, "-u", WH_ISCI], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=env)
    q = queue.Queue()
    def oku():
        for l in pr.stdout: q.put(l)
        q.put(None)
    threading.Thread(target=oku, daemon=True).start()
    try: ilk = q.get(timeout=180)
    except queue.Empty: ilk = None
    try: j = json.loads(ilk) if ilk else {}
    except ValueError: j = {}
    if not j.get("hazir"):
        pr.kill(); w.update(durum="hata", hata=j.get("hata") or "işçi başlamadı"); print(f"WHISPER: {w['hata']}"); return False
    _ISCI.update(p=pr, satirlar=q, baslik=None); w.update(durum="hazir", model=j.get("model")); KUME_AD.clear(); del KUME_BEKLEYEN[:]; del CAP_OY[:]
    STATE["ses_model"].update(durum="hazir" if j.get("ecapa") else "yok", hata=None if j.get("ecapa") else f"ses izi ağırlıkları yok ({ECAPA})", sn=j.get("sn"))
    print(f"WHISPER: hazır ({j.get('model')}, {time.time() - t:.1f} sn{', ses izi (ECAPA, MLX)' if j.get('ecapa') else ', ses izi yok'})")
    return True
def _isci_kapat(neden):
    pr = _ISCI["p"]; _ISCI.update(p=None, satirlar=None)
    if pr:
        try: pr.stdin.close(); pr.wait(timeout=5)
        except Exception: pr.kill()
    if STATE["whisper"]["durum"] == "hazir": STATE["whisper"]["durum"] = "kapali"
    if STATE["ses_model"]["durum"] == "hazir": STATE["ses_model"]["durum"] = "kapali"
    print(f"WHISPER: işçi kapatıldı ({neden})")
def _birlestir(is_):
    # is_ kuyruktan alındı; kuyrukta bekleyen aynı kanal/başlık parçaları (sırayla, toplam ≤ WH_BIRLES_MAX_SN) ona eklenir, diğerleri yerinde kalır
    if is_.get("isinma") or is_.get("bas") or WH_Q.qsize() < WH_BIRLES_ESIK: return is_
    if is_["kanal"] == "ben" and time.time() - STATE["whisper"]["kanallar"].get("karsi", 0) < WH_AKIS_SN: return is_
    ek = []; sure = is_["t1"] - is_["t0"]
    with WH_Q.mutex:
        for x in list(WH_Q.queue):
            if x.get("isinma") or x["kanal"] != is_["kanal"] or x["baslik"] != is_["baslik"]: continue
            if sure + 0.25 + (x["t1"] - x["t0"]) > WH_BIRLES_MAX_SN: break
            WH_Q.queue.remove(x); ek.append(x); sure += 0.25 + (x["t1"] - x["t0"])
    if not ek: return is_
    b = STATE["whisper"]["birlesen"]; b[is_["kanal"]] = b.get(is_["kanal"], 0) + len(ek)
    pcm = bytearray(is_["pcm"])
    for x in ek: pcm += WH_BIRLES_ARA + x["pcm"]
    return dict(is_, pcm=bytes(pcm), t1=ek[-1]["t1"], birlesik=1 + len(ek))
# İşçinin her işi (satır bırakmayanlar dahil: boş, uydurma, yankı, eski, hata) canli/whisper-isler.jsonl'e: kuyruk gecikmesinin
# nereden geldiği satır kaydından görünmüyordu (9 Ekim). olcum.py toplanti özetler. Uzun beklemede günlüğe ayrıca bir satır.
WH_UZUN_BEKLEME_SN = 8
def is_kaydet(is_, sonuc, bit, q_n, isci_sn=None, acildi=False):
    al = is_.get("t_al") or bit
    r = {"t": round(bit, 2), "kanal": is_.get("kanal"), "sonuc": sonuc, "parca_sn": round(is_["t1"] - is_["t0"], 2), "q": q_n,
         "bekleme": round(al - is_["kuyruga"], 2), "is_sn": round(bit - al, 2), **({"isci_sn": isci_sn} if isci_sn is not None else {}),
         **({"birlesik": is_["birlesik"]} if is_.get("birlesik") else {}), **({"acildi": True} if acildi else {})}
    _ISCI["son_is"] = {"kanal": r["kanal"], "sonuc": sonuc, "sure": r["is_sn"], "bit": bit}
    try: _log("whisper-isler.jsonl", r)
    except Exception: pass
def _isci_dongu():
    w = STATE["whisper"]; hata_say = 0
    while True:
        try: is_ = WH_Q.get(timeout=WH_BOSTA_KAPAT_SN)
        except queue.Empty:
            if toplanti_var(): continue  # toplantı içinde uzun sessizlikte (ekran paylaşımı) kapanıp 5 sn yeniden yüklenmesin
            if _ISCI["p"]: _isci_kapat(f"{WH_BOSTA_KAPAT_SN // 60} dk ses yok, bellek boşaltıldı")
            return
        w["kuyruk"] = WH_Q.qsize()
        if is_.get("isinma"):  # toplantıdan önce modeli belleğe al (ilk cümle beklemesin)
            if not _ISCI["p"] or _ISCI["p"].poll() is not None: _isci_ac()
            continue
        # eşik 45 → 120 sn — altyazı gölgedeyken atlanan parça dökümden tamamen kayboluyordu (6 Ekim: en kötü 45,6 sn)
        if time.time() - is_["kuyruga"] > WH_ATLA_SN:
            w["atlanan"] += 1; w["eski_atlanan"][is_["kanal"]] = w["eski_atlanan"].get(is_["kanal"], 0) + 1
            if not is_.get("bas"): is_kaydet(is_, "eski", time.time(), WH_Q.qsize())
            continue
        q_n = WH_Q.qsize(); is_ = _birlestir(is_)
        is_["t_al"] = time.time(); is_["q_n"] = q_n  # gecikme bileşenleri
        bek = is_["t_al"] - is_["kuyruga"]; o = _ISCI.get("son_is")
        if bek > WH_UZUN_BEKLEME_SN and not is_.get("bas"):  # 9 Ekim: önünde 0–1 iş varken 14–20 sn bekleme — işçi nerede kaldı
            print(f"WHISPER: parça {bek:.1f} sn bekledi ({is_['kanal']}, sırada {q_n})" + (f" · önceki iş {o['kanal']} {o['sonuc']} {o['sure']:.1f} sn, "
                  f"{is_['t_al'] - o['bit']:.1f} sn önce bitti" if o else " · önceki iş yok"))
        acildi = False
        if not _ISCI["p"] or _ISCI["p"].poll() is not None:
            acildi = True
            if not _isci_ac():
                if w["durum"] == "yok": return
                hata_say += 1; time.sleep(min(60, 5 * hata_say)); continue
        dil = {"tr": "tr", "en": "en"}.get(agenda().get("dil") or "tr")  # karisik → None: Whisper dili kendisi seçer
        if is_.get("bas"): dil = is_.get("dil") or dil  # bas-konuş: arayüz dili (toplantı dışı, gündem eski olabilir)
        k = KANALLAR.get(is_["kanal"])
        if is_.get("bas"): is_["baslik"] = _ISCI["baslik"]  # bas-konuş parçası küme/ad sıfırlamasın
        if _ISCI["baslik"] != is_["baslik"]:  # yeni toplantı: karşı kanal kümeleri ve adları sıfırlanır (işçi de başlık değişince sıfırlar)
            if _ISCI["baslik"] is not None: KUME_AD.clear(); del KUME_BEKLEYEN[:]; del CAP_OY[:]
            _ISCI["baslik"] = is_["baslik"]
        istek = {"id": is_["id"], "pcm": base64.b64encode(is_["pcm"]).decode(), "dil": dil, "istem": istem_metni(), "onceki": (k.onceki if k else "")[-150:],
                 "kanal": is_["kanal"], "baslik": is_["baslik"]}
        try:
            _ISCI["p"].stdin.write(json.dumps(istek) + "\n"); _ISCI["p"].stdin.flush()
            l = _ISCI["satirlar"].get(timeout=60); j = json.loads(l) if l else {"hata": "işçi kapandı"}
        except Exception as e: j = {"hata": f"{e.__class__.__name__}"}
        if is_.get("bas"):  # bas-konuş: metin dökümüne değil, soruya (konus_metin)
            threading.Thread(target=is_["geri"], args=(" ".join(str(j.get("text") or "").split()), j.get("hata")), daemon=True).start()
            if j.get("hata"): _isci_kapat("hata")
            continue
        if j.get("hata"):
            print(f"WHISPER: parça çevrilemedi ({j['hata']}) — işçi yeniden başlatılacak"); w["hata"] = j["hata"]; _isci_kapat("hata")
            is_kaydet(is_, "hata", time.time(), q_n, acildi=acildi); continue
        hata_say = 0; metin = " ".join(str(j.get("text") or "").split()); is_["t_wh"] = time.time(); is_["isci_sn"] = j.get("sn")
        gec = round(time.time() - is_["t1"], 1)
        w.update(son_sn=j.get("sn"), gecikme_sn=gec, gecikme_max=max(w.get("gecikme_max") or 0, gec)); w["atlanan"] += j.get("atlanan", 0)
        if j.get("istem_dusen") and j["istem_dusen"] != w.get("istem_dusen"): print(f"WHISPER: istem sınırı — {j['istem_dusen']} terim sığmadı (önem sırasında sondakiler)")
        w["istem_dusen"] = j.get("istem_dusen", 0)
        w["durgun_max"] = max(w.get("durgun_max") or 0, round(is_["t_wh"] - is_["t_al"], 1))  # tek parçanın en uzun işçi süresi (6 Ekim: 47 sn tıkanma)
        sonuc = "uydurma" if j.get("atlanan") else "bos"
        if metin:
            if j.get("kume_hata"): STATE["ses_model"]["hata"] = j["kume_hata"]
            if j.get("kume"): STATE["ses_model"]["parca"] += 1
            is_["t_ses"] = time.time(); sonuc = whisper_yaz(is_, metin, j.get("ses"), {k: j[k] for k in ("kume", "iz", "bol") if j.get(k)} or None) or "satir"
        is_kaydet(is_, sonuc, time.time(), q_n, isci_sn=j.get("sn"), acildi=acildi)
# --- Konuşmacı ses izi (v0.8.4 ses işçisi → v0.13.12 Whisper işçisinin içinde) ------------------------------------------------
# ECAPA (SpeechBrain VoxCeleb ağırlıkları, MLX) karşı kanal parçalarını kümeler: k1, k2… Kümenin adı altyazıdan oylanır: altyazı satırı
# konuşmadan 3–6 sn sonra geldiği için o anda bekleyen parçalar geriye dönük oy alır. Ad yoksa tek kümede "Karşı taraf", çok kümede
# "Karşı taraf 2". v0.13.12 (Faz 1, G4): ayrı ses işçisi (ses-venv: PyTorch, ~370 MB, 2,7 sn yükleme) ve duygu modeli (emotion2vec+)
# kalktı; ağırlık dosyası (ecapa-mlx.npz, modeller-kur dönüştürür) yoksa durum "yok", Whisper aynen çalışır. STATE["ses_model"] adı
# pano/teşhis/olcum uyumu için kaldı: ses izinin durumu.
ECAPA = _ilk(*(os.path.join(d, "ses-modeller", "spkrec-ecapa-voxceleb", "ecapa-mlx.npz") for d in (_ORT, _UYG, _APP)),
             os.path.expanduser("~/Library/Caches/Suflor/ecapa-mlx.npz"))  # ortak klasör yazılamıyorsa hesabın önbelleği (aktarici-kur)
STATE["ses_model"] = {"durum": "kapali", "hata": None, "sn": None, "parca": 0}
KUME_AD = {}; KUME_BEKLEYEN = []  # küme → {ad: oy}; (t0, t1, küme) son parçalar (altyazı oyu için)
CAP_OY = []  # (an, ad, taslak mı) son altyazı/taslak işaretleri
def _oy_uyar(c, taslak, t0, t1):
    # taslak konuşurken gelir (≤ ~1 sn gecikme): parçanın içinde; sabit altyazı satırı konuşma bittikten 3–6 sn sonra
    return (t0 + 0.3 <= c <= t1 + 1.5) if taslak else (t1 + 1.0 <= c <= t1 + 9.0)
def kume_oyla(kim, taslak=False):
    # altyazı/taslak geldi (kim konuşuyor): zamanı uyan karşı parçaların kümesine oy (taslak 2, sabit satır 1)
    if not kim or kim in ("?", ben_adi()): return
    now = time.time(); CAP_OY.append((now, kim, taslak)); del CAP_OY[:-200]
    for t0, t1, k in KUME_BEKLEYEN:
        if _oy_uyar(now, taslak, t0, t1): KUME_AD.setdefault(k, {}); KUME_AD[k][kim] = KUME_AD[k].get(kim, 0) + (2 if taslak else 1)
def kume_parca(t0, t1, k):
    # yeni parça yazılırken: konuşma sırasında gelmiş taslaklar geriye dönük oy verir
    KUME_BEKLEYEN.append((t0, t1, k)); del KUME_BEKLEYEN[:-30]
    for c, kim, taslak in CAP_OY:
        if _oy_uyar(c, taslak, t0, t1): KUME_AD.setdefault(k, {}); KUME_AD[k][kim] = KUME_AD[k].get(kim, 0) + (2 if taslak else 1)
def kume_adi(kume):
    oy = KUME_AD.get(kume)
    if oy and max(oy.values()) >= 2: return max(oy, key=oy.get)
    return None
def konusmaci_karsi(t0, t1, kume=None):
    ben = ben_adi(); now = time.time()
    son = [(t, k) for t, k in ALTYAZI_SON if k and k != ben and k != "?" and now - t < 600]
    tas = [k for c, k, ts in CAP_OY if ts and _oy_uyar(c, True, t0, t1)]  # konuşma sırasında gelen taslağın adı en güvenilir
    if tas: return max(set(tas), key=tas.count)
    ayni = [k for t, k in son if t0 - 2 <= t <= t1 + 10]
    if ayni: return max(set(ayni), key=ayni.count)
    farkli = {k for _, k in son}; n_kume = len({k for _, _, k in KUME_BEKLEYEN} | set(KUME_AD))
    if kume and n_kume > 1: return f"Karşı taraf {kume[1:]}"  # ses izinden ayrılmış, adı henüz öğrenilmedi
    if len(farkli) == 1: return next(iter(farkli))
    return f"Karşı taraf {kume[1:]}" if kume else "Karşı taraf"  # küme varsa hep numaralı: kişi başına ses tabanı tutarlı kalsın
# --- Taslak + kesin metin ----------------------------------------------------------------------------------------
# Whisper satırı ancak konuşma parçası bitince gelir (sessizlikten ~1,5 sn sonra; uzun cümlede başlangıçtan ≤ ~14 sn).
# Bu arada Teams altyazısının/dökümünün henüz sabitlenmemiş hâli eklentiden POST /taslak ile her saniye gelir; pano onu
# soluk "taslak" satırı olarak gösterir, SORU/ÖZET İSTEĞİ bağlamı da görür (izle GET /taslak). Taslak dosyaya yazılmaz.
# Silinme: aynı kimlik normal satır olarak yazılınca (Whisper o kanalda akmıyorsa), ya da o kanaldan Whisper satırı
# gelince — parçanın bitişinden önce görünmüş taslakların o anki kelimeleri "tüketilir"; aynı altyazı düğümü büyümeye
# devam ederse yalnız yeni kelimeleri taslak kalır. Hiçbiri olmazsa son güncellemeden TASLAK_OMUR_SN sonra düşer.
T_LOCK = threading.Lock(); TASLAK = {}; TASLAK_BITEN = {}; TASLAK_OMUR_SN = 20
def _taslak_kanal(kim): return "ben" if kim and kim == ben_adi() else "karsi"
def _taslak_temizle(now):
    for i in [i for i, d in TASLAK.items() if now - d["son"] > TASLAK_OMUR_SN]: del TASLAK[i]
    if len(TASLAK_BITEN) > 600:
        for i in list(TASLAK_BITEN)[:-400]: del TASLAK_BITEN[i]
def taslak_al(p):
    # POST /taslak: {"meeting": {"title"}, "source": "captions"|"transcript", "entries": [{"id", "speaker", "text"}]}
    now = time.time(); baslik = (p.get("meeting") or {}).get("title") or STATE.get("meeting") or "Toplantı"; n = 0
    gelen = [(str(e.get("id") or "")[:160], " ".join(str(e.get("text") or "").replace("|", "¦").split())[:2000], str(e.get("speaker") or "?")[:80])
             for e in (p.get("entries") or [])[:20] if isinstance(e, dict)]
    gelen = [(i, t, k, _taslak_kanal(k)) for i, t, k in gelen if i and t]
    for k in {k for _, _, k, kanal in gelen if kanal == "karsi"}: kume_oyla(k, taslak=True)  # konuşmacı ayırma için ad oyu
    with T_LOCK:
        for i, t, kim, kanal in gelen:
            if TASLAK_BITEN.get(i) == t: continue  # bu hâli zaten satır olarak yazıldı (geç kalan taslak)
            d = TASLAK.get(i)
            if d is None: d = TASLAK[i] = {"id": i, "ilk": now, "tuketilen": 0, "sabit": False}
            if d.get("text") != t: d["sabit"] = False
            d.update(speaker=kim, text=t, son=now, kanal=kanal, src=p.get("source"), baslik=baslik); n += 1
        _taslak_temizle(now)
    return {"ok": True, "n": n}
def taslak_sabit(e, src, golgede):
    # ingest'ten: eklentinin sabitlenmiş satırı. Gölgeye gittiyse (Whisper akıyor) Whisper'ı bekleyen taslak olarak kalır.
    i = str(e.get("id") or ""); t = " ".join(str(e.get("text") or "").split())
    if not i: return
    with T_LOCK:
        if not golgede: TASLAK.pop(i, None); TASLAK_BITEN[i] = t; return
        d = TASLAK.get(i); now = time.time()
        if d is None: d = TASLAK[i] = {"id": i, "ilk": now, "tuketilen": 0}
        d.update(speaker=e.get("speaker") or "?", text=t, son=now, kanal=_taslak_kanal(e.get("speaker")), src=src, sabit=True)
def taslak_tuket(kanal, t1):
    # Whisper satırı yazılmadan önce: bu kanalda parçanın bitişinden (t1) önce görünmüş taslakların kelimeleri tüketilir.
    # Döner: tüketilen en eski taslağın ilk görülme anı (epoch) — "taslak öne alma" ölçümü için; yoksa None.
    ilk = None
    with T_LOCK:
        for d in TASLAK.values():
            n = len(d["text"].split())
            if d["kanal"] != kanal or d["ilk"] > t1 + 1.0 or d["tuketilen"] >= n: continue
            ilk = d["ilk"] if ilk is None else min(ilk, d["ilk"]); d["tuketilen"] = n
    return ilk
def taslak_view(baslik=None):
    now = time.time(); out = []
    with T_LOCK:
        _taslak_temizle(now)
        for d in sorted(TASLAK.values(), key=lambda d: d["ilk"]):
            if baslik and d.get("baslik") != baslik: continue
            w = d["text"].split()[d["tuketilen"]:]
            if w: out.append({"id": d["id"], "speaker": d["speaker"], "text": " ".join(w), "kanal": d["kanal"], "sabit": bool(d.get("sabit")),
                              "yas_sn": round(now - d["son"], 1), "ilk": datetime.datetime.fromtimestamp(d["ilk"]).isoformat(timespec="milliseconds")})
    return out[-6:]
# --- Yankı ayıklama ------------------------------------------------------------------------------------------------
# Hoparlörden çıkan karşı taraf sesi kullanıcının mikrofonuna da girerse aynı sözler iki kanalda (ben + karsi) yazılır, kullanıcının
# adıyla ikinci kez. ben kanalının parçası, zamanı karşı kanalın bir parçasıyla ≥ 0,5 sn çakışıp kelimelerinin ≥ %50'si aynıysa
# yazılmaz (sayılır: whisper.yanki). Karşı parça henüz çevrilmediyse (kuyrukta / sürüyor) kullanıcı satırı en çok 4 sn bekletilir.
YANKI_LOCK = threading.Lock(); YANKI_KARSI = []; YANKI_BEKLEYEN = []; STATE["whisper"]["yanki"] = 0
def _yk(t): return set(w for w in re.findall(r"\w+", sade(t or "")) if len(w) > 2)
def _yanki_mi(a, b):  # a, b: (t0, t1, kelimeler)
    if min(a[1], b[1]) - max(a[0], b[0]) < 0.5 or not a[2] or not b[2]: return False
    return len(a[2] & b[2]) / min(len(a[2]), len(b[2])) >= 0.5
def _karsi_bekleniyor(t0, t1):
    k = KANALLAR.get("karsi")
    if k and k.konusuyor and k.t0 < t1: return True
    with WH_Q.mutex: q = list(WH_Q.queue)
    return any(x["kanal"] == "karsi" and min(x["t1"], t1) - max(x["t0"], t0) >= 0.5 for x in q)
def _yanki_say(metin):
    STATE["whisper"]["yanki"] += 1; n = STATE["whisper"]["yanki"]
    if n == 1 or n % 10 == 0: print(f"YANKI: ben kanalında karşı tarafın sözleri ({n}. kez, yazılmadı) — \"{metin[:60]}\"")
def _yanki_bosalt(zorla=False):
    now = time.time(); yaz = []
    with YANKI_LOCK:
        for b in list(YANKI_BEKLEYEN):
            m = (b[0]["t0"], b[0]["t1"], _yk(b[1]))
            if any(_yanki_mi(m, k) for k in YANKI_KARSI): YANKI_BEKLEYEN.remove(b); _yanki_say(b[1])
            elif zorla or now >= b[4] or not _karsi_bekleniyor(b[0]["t0"], b[0]["t1"]): YANKI_BEKLEYEN.remove(b); yaz.append(b)
    for b in yaz: _whisper_yaz(*b[:4])
def whisper_yaz(is_, metin, ses=None, model=None):
    kanal = is_["kanal"]; now = time.time()
    karsi_akiyor = now - STATE["whisper"]["kanallar"].get("karsi", 0) < WH_AKIS_SN
    if kanal == "karsi":
        with YANKI_LOCK: YANKI_KARSI.append((is_["t0"], is_["t1"], _yk(metin))); del YANKI_KARSI[:-20]
        _whisper_yaz(is_, metin, ses, model); _yanki_bosalt(); return "satir"
    if kanal == "ben" and karsi_akiyor:
        m = (is_["t0"], is_["t1"], _yk(metin))
        with YANKI_LOCK:
            if any(_yanki_mi(m, k) for k in YANKI_KARSI): _yanki_say(metin); return "yanki"
            if _karsi_bekleniyor(is_["t0"], is_["t1"]):
                YANKI_BEKLEYEN.append((is_, metin, ses, model, now + 4.0)); threading.Timer(4.1, _yanki_bosalt).start(); return "bekletildi"
    _whisper_yaz(is_, metin, ses, model); return "satir"
def _whisper_yaz(is_, metin, ses=None, model=None):
    kanal = is_["kanal"]; k = KANALLAR.get(kanal)
    if k: k.onceki = (k.onceki + " " + metin)[-300:]
    STATE["whisper"]["satir"] += 1; STATE["whisper"]["kanal_son_satir"][kanal] = time.time()
    kume = (model or {}).get("kume") if kanal == "karsi" else None
    if kume: kume_parca(is_["t0"], is_["t1"], kume)
    kim = ben_adi() if kanal == "ben" else (kume_adi(kume) if kume else None) or konusmaci_karsi(is_["t0"], is_["t1"], kume)
    ta = taslak_tuket(kanal, is_["t1"])
    # satır başına gecikme bileşenleri (sn) — kuyruk bekleme, işçiye gidiş-dönüş, işçinin kendi süresi, ses işçisi
    # bekleme, yankı bekletmesi, toplam (parça sonu → yazım). olcum.py toplanti bunları ayrı ayrı özetler.
    t_now = time.time(); g = lambda a, b: round(is_[b] - is_[a], 2) if is_.get(a) and is_.get(b) else None
    gec = {"kuyruk": g("kuyruga", "t_al"), "whisper": g("t_al", "t_wh"), "isci": is_.get("isci_sn"), "ses": g("t_wh", "t_ses"),
           "yanki": round(t_now - is_["t_ses"], 2) if is_.get("t_ses") else None, "toplam": round(t_now - is_["t1"], 2), "q": is_.get("q_n"), **({"birlesik": is_["birlesik"]} if is_.get("birlesik") else {})}
    ingest({"meeting": {"title": is_["baslik"]}, "source": "whisper", "capturedAt": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "entries": [{"id": is_["id"], "speaker": kim, "time": datetime.datetime.fromtimestamp(is_["t0"]).strftime("%H:%M:%S"), "text": metin,
                         "seen": datetime.datetime.utcfromtimestamp(is_["t1"]).isoformat(timespec="milliseconds") + "Z", "kanal": kanal,
                         "t0": round(is_["t0"], 2), "t1": round(is_["t1"], 2),
                         **({"kume": kume} if kume else {}), **({k: model[k] for k in ("iz", "bol") if model.get(k)} if kanal == "karsi" and model else {}),  # # v0.8.3: parça sınırları (epoch) — cevap gecikmesi, söz kesme
                         **({"taslak": datetime.datetime.utcfromtimestamp(ta).isoformat(timespec="milliseconds") + "Z"} if ta else {}), "gec": gec,
                         **({"ses": dict(ses, hiz=round(len(metin.split()) / max(0.5, ses.get("sure") or 0) * 60))} if ses else {})}]})  # ses sinyalleri + hız (kelime/dk)
