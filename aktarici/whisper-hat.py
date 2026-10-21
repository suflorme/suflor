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
import base64, subprocess, queue, struct, math
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
# ayar "whisper_motor": "cpp" → canlı döngüde whisper.cpp + Core ML (aynı turbo q8, kodlayıcı Neural Engine'de; ~2,3 kat hızlı, doğruluk ve
# uydurma süzgeci aynı — 20 Ekim kıyası). Dosyalar <ortak>/whisper-cpp/ (whisper-server, ggml-large-v3-turbo-q8_0.bin + Core ML kodlayıcı);
# yoksa MLX'e düşülür. Dosyadan ve toplu döküm her durumda MLX.
WH_CPP = os.path.join(_ORT, "whisper-cpp")
def wh_cpp(): return AYAR.get("whisper_motor") == "cpp" and os.path.exists(os.path.join(WH_CPP, "whisper-server")) and os.path.exists(os.path.join(WH_CPP, "ggml-large-v3-turbo-q8_0.bin"))
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
def wh_bas_sira(is_):  # bas-konuş akış parçası (v0.47.1): kuyruğun başındaki bas-konuş işlerinin ARKASINA — parçalar sırayla (önce gelen önce) dökülür
    with WH_Q.not_empty:
        q = WH_Q.queue; i = 0
        while i < len(q) and q[i].get("bas"): i += 1
        q.insert(i, is_); WH_Q.unfinished_tasks += 1; WH_Q.not_empty.notify()
def _rms(b):
    if audioop: return audioop.rms(b, 2)
    import array; a = array.array("h"); a.frombytes(b); return int((sum(x * x for x in a) / max(1, len(a))) ** 0.5)
class Kanal:
    def __init__(self, ad): self.ad = ad; self.reset(); self.gurultu = 300.0; self.son_bitis = 0.0; self.onceki = ""; self.baslangic = time.time(); self.t_ses = 0.0; self.n_ses = 0; self.ses_t = collections.deque(maxlen=600)  # t_ses/n_ses: otonom söz sırası (v0.56.0); ses_t: sesli karelerin zamanı (son ~12 sn; otonomun yankı ayrımı, 19 Ekim)
    def reset(self): self.parca = bytearray(); self.on = bytearray(); self.konusuyor = False; self.sessiz = 0; self.sesli = 0; self.ust = 0; self.t0 = 0.0; self.rmsler = []
    def besle(self, pcm, t_bas, baslik):
        if t_bas - self.son_bitis > 0.5 and self.konusuyor: self.kes(baslik)  # boşluk (mikrofon kapalıydı / parça kayıp)
        if time.time() - STATE["whisper"]["kanallar"].get(self.ad, 0) > WH_AKIS_SN: self.baslangic = time.time()
        STATE["whisper"]["kanallar"][self.ad] = time.time()
        for i in range(0, len(pcm) - WH_KARE * 2 + 1, WH_KARE * 2):
            kare = bytes(pcm[i:i + WH_KARE * 2]); t = t_bas + i / 2 / WH_SR; r = _rms(kare)
            esik = max(220.0, self.gurultu * 2.8)
            if r > esik: self.t_ses = t + WH_KARE / WH_SR; self.n_ses += 1; self.ses_t.append(t)
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
    if kanal == "ben":  # masaüstü mikrofonu (v0.30.0): eklenti son 3 sn'de "ben" verdiyse menü uygulamasının parçası atılır — çift satır olmasın
        if p.get("kaynak") != "masaustu": STATE["_ben_eklenti"] = time.time()
        elif time.time() - (STATE.get("_ben_eklenti") or 0) < 3: return {"ok": True, "eklenti": True}
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
    gerek = 0 if yuklu else (1.5 if wh_cpp() else 2.0 if WH_MODEL == _WH_Q8 else 2.5)  # q8 ~1,8 GB, tam turbo ~2,4 GB, whisper.cpp ~1,3 GB
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
    adlar = [k["ad"] for k in kisilikler()]  # v0.61.0: iki kişiliğin adı da; v0.53.0: hitap adı istemin başında (ölçüm: istemsiz 9/14, istemle 13/14)
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
               **({"SUFLOR_ECAPA": ECAPA} if os.path.exists(ECAPA) else {}), **({"SUFLOR_WHISPER_CPP": WH_CPP} if wh_cpp() else {}))
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
    _ISCI.update(p=pr, satirlar=q, baslik=None); w.update(durum="hazir", model=j.get("model"), motor=j.get("motor") or "mlx"); kume_sifirla()
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
        if "gizli_acik" in globals() and gizli_acik(): continue  # v0.89.1: gizli toplantı — parça işlenmeden atılır, işçi açılmaz
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
            if _ISCI["baslik"] is not None: kume_sifirla()
            _ISCI["baslik"] = is_["baslik"]
        # "yazayım mı?" sorusuna bas-konuş cevabı istemsiz: whisper.cpp ad/terim listeli istemle kısa "Evet."i "Evit." yazıyordu, ayırıcı tanımıyordu
        # (20 Ekim, test34; istemsiz doğru). Cevap sözcüklerini isteme koymak olmaz: işçi istemde geçen tek sözü "istemi geri okuma" diye atar.
        istem = "" if is_.get("bas") and SORU.get("aktif") else istem_metni()
        istek = {"id": is_["id"], "pcm": base64.b64encode(is_["pcm"]).decode(), "dil": dil, "istem": istem, "onceki": (k.onceki if k else "")[-150:],
                 "kanal": is_["kanal"], "baslik": is_["baslik"]}
        if not dil: istek.update(diller=["tr", "en"], dil_yedek=getattr(k, "dil_son", None))  # karışık: yalnız tr/en
        elif dil in ("tr", "en"):
            # dil geçişi (v0.29.2, S36): dayatılan dil boş çıkarsa işçi öbür dile bakar (olasılık ≥ %80); kanal son 60 sn'de öbür dilde satır
            # verdiyse önce o dil denenir (karşı taraf İngilizce konuşurken her parça önce Türkçe çözülmesin), boş çıkarsa toplantı diline döner
            istek["dil_algila"] = True; istek["ana_dil"] = dil
            if k and getattr(k, "dil_son", None) in ("tr", "en") and k.dil_son != dil and time.time() - getattr(k, "dil_son_t", 0) < 60: istek["dil"] = k.dil_son
        # kullanıcı kanalında ses izi: oda açıksa ad için, değilse yalnız ses kilidi için ("Claude:" komutu kullanıcının sesi mi; ayar ses_kilidi)
        if is_["kanal"] == "ben" and not is_.get("bas") and (oda_acik() or AYAR.get("ses_kilidi", True) is not False): istek["oda"] = is_["oda"] = True
        if is_.get("bas") and is_.get("oto_dil"): istek["oto_dil"] = True  # v0.101.4: Konuş sorusunun ilk parçası — dil Whisper'dan (yalnız tr/en)
        if is_.get("iz_iste"): istek["iz_iste"] = True  # sohbet sorusu: ses izi süzgeci (aktarici/sohbet.py sohbet_ses_izi_red)
        try:
            _ISCI["p"].stdin.write(json.dumps(istek) + "\n"); _ISCI["p"].stdin.flush()
            l = _ISCI["satirlar"].get(timeout=60); j = json.loads(l) if l else {"hata": "işçi kapandı"}
        except Exception as e: j = {"hata": f"{e.__class__.__name__}"}
        if is_.get("bas"):  # bas-konuş: metin dökümüne değil, soruya (konus_metin)
            if is_.get("iz_iste"): is_["iz"] = j.get("iz")
            if is_.get("oto_dil") and j.get("dil") in ("tr", "en") and "konus_dil_kaydet" in globals(): konus_dil_kaydet(j["dil"], is_.get("akis_nesil"))
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
        if j.get("atilan"):  # süzgecin attığı metin (v0.32.12): uydurma listesini kendi kayıtlarımızdan büyütmek için; yalnız bu Mac'te, döndürülür
            try: _log("uydurma-adaylari.jsonl", {"t": round(time.time(), 1), "kanal": is_.get("kanal"), "atilan": j["atilan"], "satir": bool(metin)})
            except Exception: pass
        if metin and j.get("dil") in ("tr", "en") and KANALLAR.get(is_["kanal"]): KANALLAR[is_["kanal"]].dil_son = j["dil"]; KANALLAR[is_["kanal"]].dil_son_t = time.time()
        if metin and j.get("dil_gecis"): print(f"WHISPER: {is_['kanal']} kanalı {j.get('dil')} ({j['dil_gecis']}) — toplantı dili dışında konuşma")
        if metin:
            if j.get("kume_hata"): STATE["ses_model"]["hata"] = j["kume_hata"]
            if j.get("kume"): STATE["ses_model"]["parca"] += 1
            is_["t_ses"] = time.time(); sonuc = whisper_yaz(is_, metin, j.get("ses"), {k: j[k] for k in ("kume", "iz", "bol") if j.get(k)} or None) or "satir"
        is_kaydet(is_, sonuc, time.time(), q_n, isci_sn=j.get("sn"), acildi=acildi)
        if AYAR.get("parca_kaydet"): parca_kaydet(is_, istek, j, sonuc)
# Teşhis (v0.29.2, 12 Ekim: İngilizce YouTube denemesinde karşı kanalın 62 parçası "uydurma"; ses saklanmadığı için neden bilinemedi): ayar
# parca_kaydet: true iken her kanalın son PARCA_KAYIT_EN_COK parçası 16 kHz WAV + sonucu (dil, metin, atlanan) canli/teshis-parcalar/'a yazılır.
# Varsayılan kapalı; ses yalnız bu Mac'te kalır, eskiler silinir. Kapatınca klasörü elle sil.
PARCA_KAYIT_EN_COK = 20
def parca_kaydet(is_, istek, j, sonuc):
    try:
        import wave
        kl = os.path.join(BASE, "teshis-parcalar"); os.makedirs(kl, exist_ok=True)
        ad = f"{is_['kanal']}-{datetime.datetime.now().strftime('%H%M%S')}-{str(is_.get('id'))[-6:]}"
        with wave.open(os.path.join(kl, ad + ".wav"), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(is_["pcm"])
        write([(os.path.join(kl, "sonuclar.jsonl"), json.dumps({"dosya": ad + ".wav", "sonuc": sonuc, "dil_istek": istek.get("dil"), "dil": j.get("dil"),
                "atlanan": j.get("atlanan"), "metin": j.get("text"), "sn": round(len(is_["pcm"]) / 32000, 2)}, ensure_ascii=False) + "\n")])
        es = sorted(f for f in os.listdir(kl) if f.startswith(is_["kanal"] + "-") and f.endswith(".wav"))
        for f in es[:-PARCA_KAYIT_EN_COK]: os.remove(os.path.join(kl, f))
    except Exception as e: print(f"TEŞHİS: parça yazılamadı ({e.__class__.__name__})")
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
    return KUME_HAFIZA[kume][0] if kume in KUME_HAFIZA else None
# --- Ses izi hafızası canlıda (v0.27.0) ---------------------------------------------------------------------------------
# Toplantı sonu (toplanti-claude.py hafiza_*) altyazının ad verdiği kişilerin ortalama izini canli/ses-izi-hafiza.json'a yazar. Canlıda
# altyazı oyu olmayan küme, biriken izi (süre ağırlıklı ortalama) hafızadaki kişiye toplantı sonundaki eşikle benziyorsa onun adını alır;
# altyazı oyu gelince oy önce gelir, toplantı sonu etiketleme son sözü söyler. Hafızaya canlıdan yazılmaz. Eşikler toplanti-claude.py ile aynı.
HAFIZA_ESIK, HAFIZA_FARK, HAFIZA_EN_AZ_SN = 0.6, 0.1, 8.0
KUME_IZ = {}; KUME_HAFIZA = {}; _HAF = {"mt": None, "kisi": {}}  # küme → [toplam vektör, sn]; küme → (ad, benzerlik)
def _iz_coz(b):
    r = base64.b64decode(b); v = struct.unpack(f"<{len(r) // 2}e", r); n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
def _hafiza_kisi():
    if AYAR.get("ses_izi_hafiza", True) is False: return {}
    yol = os.path.join(BASE, "ses-izi-hafiza.json")
    try: mt = os.path.getmtime(yol)
    except OSError: return {}
    if mt != _HAF["mt"]:
        try: h = json.load(open(yol, encoding="utf-8")); _HAF.update(mt=mt, kisi={a: _iz_coz(x["iz"]) for a, x in h.items() if isinstance(x, dict) and x.get("iz")})
        except (OSError, ValueError, KeyError, TypeError, struct.error): _HAF.update(mt=mt, kisi={})
    return _HAF["kisi"]
def kume_iz_ekle(kume, iz, sn):
    if not kume or not iz or sn <= 0: return
    try: v = _iz_coz(iz)
    except Exception: return
    t = KUME_IZ.setdefault(kume, [[0.0] * len(v), 0.0])
    if len(t[0]) != len(v): return
    t[0] = [a + sn * b for a, b in zip(t[0], v)]; t[1] += sn
    oy = KUME_AD.get(kume)
    if (oy and max(oy.values()) >= 2) or t[1] < HAFIZA_EN_AZ_SN: KUME_HAFIZA.pop(kume, None); return
    kisi = _hafiza_kisi()
    if not kisi: return
    n = math.sqrt(sum(x * x for x in t[0])) or 1.0; m = [x / n for x in t[0]]
    kullanilan = {kume_adi(k) for k in set(KUME_AD) | set(KUME_HAFIZA) if k != kume}
    s = sorted(((sum(a * b for a, b in zip(m, x)), ad) for ad, x in kisi.items()), reverse=True)
    b, ad = s[0]; iki = s[1][0] if len(s) > 1 else 0.0
    if ad not in kullanilan and b >= HAFIZA_ESIK and b - iki >= HAFIZA_FARK:
        if KUME_HAFIZA.get(kume, (None,))[0] != ad: print(f"SES İZİ: {kume} → {ad} (hafızadan, benzerlik {b:.2f})")
        KUME_HAFIZA[kume] = (ad, round(b, 2))
    else: KUME_HAFIZA.pop(kume, None)
# --- Aynı mikrofonda ikinci kişi (v0.27.0; ayar oda: true ya da agenda.json "oda": true, varsayılan kapalı) -----------------------------
# Kullanıcı kanalındaki parçanın izi kullanıcının profiline (canli/ses-izi-ben.json, 0600, yalnız bu Mac) benzemiyorsa satır "Odadaki kişi".
# Profil yoksa ilk ≥ 30 sn'lik (≥ 1,5 sn'lik parçalar) konuşmadan kurulur: ortalamaya ≥ 0,5 benzeyen parçalar ≥ 24 sn tutarsa (biri baştan
# konuştuysa profil kurulmaz, sürer). Sonra ≥ 0,5 benzeyen parçalar profili yavaşça günceller (ağırlık en çok 600 sn). Ölçüm (11 Ekim,
# gercek-ses/oda-olc.py, kullanıcının 3 dk kaydı): kendi parçaları profile 0,36–0,78, başka sesler ≤ 0,33 → eşik 0,35; belirsizlik
# kullanıcıda kalır (kendi sözü başkasına yazılmasın). < 1,5 sn parça hep kullanıcı. Aynı mikrofondaki başka ses gerçekte daha yakın olabilir.
ODA_AD = "Odadaki kişi"; ODA_ESIK, ODA_GUNCELLE, ODA_EN_KISA, ODA_PROFIL_SN, ODA_AGIRLIK_SN = 0.35, 0.5, 1.5, 30.0, 600.0
ODA = {"profil": None, "sn": 0.0, "ogren": [], "yuklendi": False, "yazildi": 0.0, "say": 0}
def oda_acik(): return AYAR.get("oda") is True or agenda().get("oda") is True
def _oda_yol(): return os.path.join(BASE, "ses-izi-ben.json")
def _oda_kaydet():
    try:
        n = math.sqrt(sum(x * x for x in ODA["profil"])) or 1.0
        v = {"iz": base64.b64encode(struct.pack(f"<{len(ODA['profil'])}e", *(x / n for x in ODA["profil"]))).decode(), "sn": round(ODA["sn"], 1),
             "son": datetime.datetime.now().strftime("%Y-%m-%d")}
        fd = os.open(_oda_yol() + ".gecici", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(v, f)
        os.replace(_oda_yol() + ".gecici", _oda_yol()); ODA["yazildi"] = time.time()
    except OSError as e: print(f"ODA: profil yazılamadı ({e})")
def oda_kim(iz, sn, metin="", ad_ver=True):
    # kullanıcı kanalının satırı: ben_adi() ya da ODA_AD (ad_ver=False: oda kapalı — profil yine öğrenilir/güncellenir, ad hep kullanıcı;
    # benzerlik ODA["son_b"]'de, ses kilidi için). < 2 sözcüklü satır ("!", "Evet") karar vermez: sessizlik/gürültü parçasının izi
    # profilden uzak düşüyor (test/oda.py: Whisper'ın "!" satırı)
    ben = ben_adi(); ODA["son_b"] = None
    if not iz or len(re.findall(r"\w{2,}", metin or "")) < 2: return ben
    try: v = _iz_coz(iz)
    except Exception: return ben
    if not ODA["yuklendi"]:
        ODA["yuklendi"] = True
        try: x = json.load(open(_oda_yol(), encoding="utf-8")); ODA.update(profil=_iz_coz(x["iz"]), sn=float(x.get("sn") or 0))
        except (OSError, ValueError, KeyError, TypeError, struct.error): pass
    if ODA["profil"] is None:
        if sn >= ODA_EN_KISA: ODA["ogren"].append((sn, v)); del ODA["ogren"][:-40]
        top = sum(s_ for s_, _ in ODA["ogren"])
        if top >= ODA_PROFIL_SN:
            # baskın ses: diğerlerine benzerlik toplamı en yüksek parça (medoid) ve ona ≥ ODA_ESIK benzeyenler; konuşmanın ≥ %75'i olmalı
            # (ölçüm: kullanıcı tek başına %87; araya başka ses karışınca %35–55 → kurulmaz, öğrenme sürer)
            og = ODA["ogren"]; S = [[sum(a * b for a, b in zip(x, y)) for _, y in og] for _, x in og]
            md = max(range(len(og)), key=lambda i: sum(S[i])); tut = [og[j] for j in range(len(og)) if S[md][j] >= ODA_ESIK]
            if sum(s_ for s_, _ in tut) >= 0.75 * top:
                ODA.update(profil=[sum(s_ * x[i] for s_, x in tut) for i in range(len(v))], sn=sum(s_ for s_, _ in tut)); ODA["ogren"] = []
                print(f"ODA: kullanıcı ses profili kuruldu ({ODA['sn']:.0f} sn)"); _oda_kaydet()
        return ben
    n = math.sqrt(sum(x * x for x in ODA["profil"])) or 1.0; b = sum(a * x / n for a, x in zip(v, ODA["profil"]))
    if sn >= ODA_EN_KISA: ODA["son_b"] = round(b, 2)
    if sn >= ODA_EN_KISA and b < ODA_ESIK and ad_ver:
        ODA["say"] += 1
        if ODA["say"] == 1: print(f"ODA: {ODA_AD} (benzerlik {b:.2f})")
        return ODA_AD
    if sn >= ODA_EN_KISA and b >= ODA_GUNCELLE:
        w0 = min(ODA["sn"], ODA_AGIRLIK_SN); ODA["profil"] = [w0 * x / n + sn * a for x, a in zip(ODA["profil"], v)]; ODA["sn"] += sn
        if time.time() - ODA["yazildi"] > 60: _oda_kaydet()
    return ben
def kullanici_benzer(iz):  # parçanın ses izi ile kullanıcı profilinin (ses-izi-ben.json, toplantılarda öğrenilir) benzerliği; profil/iz yoksa None
    if not ODA["yuklendi"]:
        ODA["yuklendi"] = True
        try: x = json.load(open(_oda_yol(), encoding="utf-8")); ODA.update(profil=_iz_coz(x["iz"]), sn=float(x.get("sn") or 0))
        except (OSError, ValueError, KeyError, TypeError, struct.error): pass
    if not iz or ODA["profil"] is None: return None
    try: v = _iz_coz(iz)
    except Exception: return None
    n = math.sqrt(sum(x * x for x in ODA["profil"])) or 1.0
    return sum(a * x / n for a, x in zip(v, ODA["profil"]))
def kume_sifirla(): KUME_AD.clear(); del KUME_BEKLEYEN[:]; del CAP_OY[:]; KUME_IZ.clear(); KUME_HAFIZA.clear()
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
    if not farkli and not (kume and n_kume > 1):  # masaüstü (v0.31.0): altyazı yok, Kişiler panelinde kullanıcıdan başka tek kişi
        d = masaustu_diger_katilimci()
        if d: return d
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
# adıyla ikinci kez. ben kanalının parçası, zamanı karşı kanalın bir parçasıyla ≥ 0,5 sn çakışıp sözcüklerinin ≥ %60'ı karşı metinde AYNI
# SIRAYLA geçiyorsa (en az 2 sözcük; tek sözcüklük parçada 1) yazılmaz (sayılır: whisper.yanki). Karşı parça henüz çevrilmediyse (kuyrukta /
# sürüyor) kullanıcı satırı en çok 4 sn bekletilir. Eski kural (kümelerin küçüğünün %50'si, sırasız) aynı konudaki kendi sözü atıyordu: 9 Ekim
# kulaklıkla bir kişi adı ve "yetki" geçen kendi sorusu (karşı aynı anda aynı kişiden söz ediyordu; sırayla 2/4), 6 Ekim kendi sayımı + sorusu
# (karşının saydığı üç ad içinde; 3/9). Gerçek yankı 7 Ekim "Merhabalar herkese" (2/2) yine tutulur. test/yanki.py (adlar değiştirildi).
YANKI_LOCK = threading.Lock(); YANKI_KARSI = []; YANKI_BEKLEYEN = []; STATE["whisper"]["yanki"] = 0
YANKI_KAPSAM = 0.6
def _yk(t): return [w for w in re.findall(r"\w+", sade(t or "")) if len(w) > 2]
def _yanki_mi(a, b):  # a: ben, b: karşı — (t0, t1, sözcükler sırayla)
    if min(a[1], b[1]) - max(a[0], b[0]) < 0.5 or not a[2] or not b[2]: return False
    import difflib
    ortak = sum(m.size for m in difflib.SequenceMatcher(None, a[2], b[2], autojunk=False).get_matching_blocks())
    return ortak >= min(2, len(a[2])) and ortak / len(a[2]) >= YANKI_KAPSAM
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
# Suflor'un kendi sesi (v0.30.2, deneme 6): hoparlörden okunan sesli çeviri özü / fısıltı mikrofona girip kullanıcının adıyla satır oluyordu
# ("Eğlenceli değilse sadece bir serseri" ×3; konuşma payı, söz kesme ve DİNLE yanlış). Okuma aralığı ve sözcükleri kaydedilir; ben kanalında
# o aralıkla çakışan ve sözcükleri sırayla eşleşen satır (yankı kuralı) yazılmaz. Kulaklıkta zaten girmez.
KENDI_SES = []
# 19 Ekim test toplantısı: okunan "Ses kesikliğinin kaynağını şu an bilmiyorum" mikrofondan "<kişilik adı> sesin kesikliğinin kaynağını şu an bilin" yazıldı —
# Whisper yankıyı bozuk yazıyor (ek değişiyor, sözcük kısalıyor) ve istemdeki kişilik adını başa ekliyor; birebir eşleşme 2/5 kaldı. Yalnız kendi sesimiz için
# sözcükler kök benzerliğiyle karşılaştırılır (ortak önek ≥ 3 ve kısa olanın en çok 2 harf eksiği) ve kişilik adları sayılmaz; karşı tarafın yankı kuralı aynı.
def _kok_ayni(x, y):
    n = 0
    for a, b in zip(x, y):
        if a != b: break
        n += 1
    return n >= 3 and n >= min(len(x), len(y)) - 2
def _kendi_mi(a, b):  # a: ben satırı, b: Suflor'un okuduğu — (t0, t1, sözcükler)
    if min(a[1], b[1]) - max(a[0], b[0]) < 0.5: return False
    try: adlar = {sade(x) for k in kisilikler() for x in k.get("hitap") or []}
    except Exception: adlar = set()
    s = [w for w in a[2] if w not in adlar]; o = b[2]
    if not s or not o: return False
    d = [[0] * (len(o) + 1) for _ in range(len(s) + 1)]  # sıralı eşleşme (en uzun ortak alt dizi, kök benzerliğiyle)
    for i in range(len(s)):
        for j in range(len(o)): d[i + 1][j + 1] = d[i][j] + 1 if _kok_ayni(s[i], o[j]) else max(d[i][j + 1], d[i + 1][j])
    ortak = d[len(s)][len(o)]
    return ortak >= min(2, len(s)) and ortak / len(s) >= YANKI_KAPSAM
def kendi_ses_kaydet(metin, t0, t1):
    with YANKI_LOCK: KENDI_SES.append((t0, t1 + 1.5, _yk(metin))); del KENDI_SES[:-10]
def whisper_yaz(is_, metin, ses=None, model=None):
    kanal = is_["kanal"]; now = time.time()
    if kanal == "ben":
        m = (is_["t0"], is_["t1"], _yk(metin))
        with YANKI_LOCK: kendi = any(_kendi_mi(m, k) for k in KENDI_SES)
        if kendi:
            STATE["whisper"]["kendi_ses"] = STATE["whisper"].get("kendi_ses", 0) + 1
            if STATE["whisper"]["kendi_ses"] in (1, 10, 50): print(f"YANKI: Suflor'un okuduğu ses mikrofona girdi ({STATE['whisper']['kendi_ses']}. kez, yazılmadı) — \"{metin[:60]}\"")
            return "yanki"
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
    if "gizli_acik" in globals() and gizli_acik(): return  # v0.89.1: gizli toplantıda satır yazılmaz (kuyrukta kalmış parça dahil)
    kanal = is_["kanal"]; k = KANALLAR.get(kanal)
    if k: k.onceki = (k.onceki + " " + metin)[-300:]
    STATE["whisper"]["satir"] += 1; STATE["whisper"]["kanal_son_satir"][kanal] = time.time()
    kume = (model or {}).get("kume") if kanal == "karsi" else None
    if kume: kume_parca(is_["t0"], is_["t1"], kume); kume_iz_ekle(kume, (model or {}).get("iz"), max(0.0, is_["t1"] - is_["t0"]))
    kim = (oda_kim((model or {}).get("iz"), max(0.0, is_["t1"] - is_["t0"]), metin, oda_acik()) if is_.get("oda") else ben_adi()) if kanal == "ben" else \
        (kume_adi(kume) if kume else None) or konusmaci_karsi(is_["t0"], is_["t1"], kume)
    # ses kilidi (11 Ekim): kullanıcı kanalındaki "Claude:" komutu sesi kullanıcının profiline benzemiyorsa (yanındaki biri) işaretlenir;
    # izle satırı "⚠ses" ile verir, toplantı oturumu komut saymaz. "Odadaki kişi" satırı zaten kullanıcının değildir.
    komut_ses = None
    if kanal == "ben" and (HITAP_RX.search(metin) or re.search(r"(^|[.!?…]\s+)claude\b", metin, re.I)):
        b = ODA.get("son_b") if is_.get("oda") else None
        if kim == ODA_AD or (b is not None and b < ODA_ESIK):
            komut_ses = "uymuyor"; print(f"SES KİLİDİ: 'Claude:' komutu kullanıcının sesine benzemiyor (benzerlik {b if b is not None else '-'}) — komut sayılmaz")
        elif b is not None: komut_ses = "uyuyor"
    ta = taslak_tuket(kanal, is_["t1"])
    # satır başına gecikme bileşenleri (sn) — kuyruk bekleme, işçiye gidiş-dönüş, işçinin kendi süresi, ses işçisi
    # bekleme, yankı bekletmesi, toplam (parça sonu → yazım). olcum.py toplanti bunları ayrı ayrı özetler.
    t_now = time.time(); g = lambda a, b: round(is_[b] - is_[a], 2) if is_.get(a) and is_.get(b) else None
    gec = {"kuyruk": g("kuyruga", "t_al"), "whisper": g("t_al", "t_wh"), "isci": is_.get("isci_sn"), "ses": g("t_wh", "t_ses"),
           "yanki": round(t_now - is_["t_ses"], 2) if is_.get("t_ses") else None, "toplam": round(t_now - is_["t1"], 2), "q": is_.get("q_n"), **({"birlesik": is_["birlesik"]} if is_.get("birlesik") else {})}
    ingest({"meeting": {"title": is_["baslik"]}, "source": "whisper", "capturedAt": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "entries": [{"id": is_["id"], "speaker": kim, "time": datetime.datetime.fromtimestamp(is_["t0"]).strftime("%H:%M:%S"), "text": metin,
                         "seen": datetime.datetime.utcfromtimestamp(is_["t1"]).isoformat(timespec="milliseconds") + "Z", "kanal": kanal,
                         "t0": round(is_["t0"], 2), "t1": round(is_["t1"], 2), **({"komut_ses": komut_ses} if komut_ses else {}),
                         **({"kume": kume} if kume else {}), **({k: model[k] for k in ("iz", "bol") if model.get(k)} if kanal == "karsi" and model else {}),  # # v0.8.3: parça sınırları (epoch) — cevap gecikmesi, söz kesme
                         **({"taslak": datetime.datetime.utcfromtimestamp(ta).isoformat(timespec="milliseconds") + "Z"} if ta else {}), "gec": gec,
                         **({"ses": dict(ses, hiz=round(len(metin.split()) / max(0.5, ses.get("sure") or 0) * 60),
                                                  **({"benzer": ODA["son_b"]} if kanal == "ben" and is_.get("oda") and ODA.get("son_b") is not None else {}))} if ses else {})}]})
    # ses sinyalleri + hız (kelime/dk); benzer = kullanıcı kanalında parçanın kullanıcı profiline benzerliği (oda kapalıyken de; ODA_ESIK'i gerçek
    # toplantıda ölçmek için — Deneme 9'da odadaki ses −35…−42 dB, perde 220–290 Hz; kullanıcı −12…−20 dB, 125–150 Hz; profil benzerliği kayıtta yoktu)
