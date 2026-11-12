# Suflor.me aktarıcı bölümü: Konuş yerel ses istemcisi (akıcı sohbet Aşama 2, Adım 2; 12 Kasım 2026). Ayrı modül değildir — relay.py bunu kendi ad alanında
# çalıştırır (bolum("yerel-konus"), bolum("sohbet")'ten önce). Python 3.9 uyumlu. Sözleşme: ../planlar/konus-ses-protokol.md (Swift yardımcısı `Suflor Konus.app`,
# Unix soket <uygulama>/konus-ses.sock, ilk satır anahtar, satır başına bir JSON).
# Ne yapar: yardımcıya bağlanır (okuma iş parçacığı + yeniden bağlanma), mikrofon öbeklerini (16 kHz Int16) sohbet gövdesine (_sohbet_parca_govde) verir, hoparlörde
# çalmayı yardımcının VPIO motoruna yönlendirir. İki yol:
#   M yolu — Mac sesi (say): metin `say -o` ile PCM'e çevrilir, yardımcıya cal_ac/ses/cal_bitir ile gider; ses_basladi ← cal_basladi (ses saati).
#   D yolu — Pocket, Gemini: dış çalıcı (SuflorOynat) yerinde kalır; çalarken ky_sessiz_sar motorda sessiz çalıcı düğümü açık tutar (VPIO başvurusu, Adım 0a).
# Aygıtlı ve BlackHole yolu (toplantıya ses) hiç değişmez. Ayar yerel_konus (varsayılan false; yalnız gelistirici_mi()): false iken bu bölüm HİÇ bağlanmaz,
# çağıranlar bugünkü yolu izler. Yardımcı 2 sn içinde cal_basladi demezse bugünkü yola düşülür ve günlüğe yerel_dusme yazılır.
# Adlar ky_ önekiyle (relay'de yerel_* adları Suflor Ses.app ve Pocket'in).
import socket, subprocess, base64, wave, tempfile
KY_BAGLAN_ARA_SN, KY_BAGLAN_AZAMI_SN, KY_CAL_BASLA_SN, KY_DUSME_BEKLE_SN, KY_SESSIZ_SN, KY_MIK_BIRLES_SN = 2.0, 30.0, 2.0, 30.0, 20.0, 0.4
KY_SAY_SR = 22050  # say -o çıkışı (Mac sesi); yardımcı 48 kHz'e kendisi çevirir
KY = {"s": None, "bagli": False, "dongu": None, "dur": False, "kilit": threading.RLock(), "yaz_kilit": threading.Lock(), "mik": False, "vpio": False, "calan": {}, "sira": 0,
      "durum": {}, "dusme_bit": 0.0, "dusme": 0, "kanca": None, "mik_isle": None, "mik_q": None, "mik_kusak": 0, "mik_tamp": bytearray(), "mik_p": None, "son_t": 0.0, "anahtar_hata": False, "vpio_istek": False, "vpio_bekle": 0.0, "devam_vpio": None,
      "sessiz": 0, "sessiz_gen": 0, "sessiz_acik": False, "mik_atilan": 0, "mik_n": 0, "saat_uyari": False, "aygit_say": 0}
def ky_etkin():  # ayar yerel_konus true VE geliştirici: değilse bu bölüm hiçbir şey yapmaz
    try: return AYAR.get("yerel_konus") is True and bool(gelistirici_mi())
    except Exception: return False
def ky_hazir():  # bağlı, anahtar kabul edilmiş ve yakın zamanda düşmemiş: çağıranlar yerel yolu yalnız buna bakarak seçer
    return bool(KY["bagli"]) and time.time() >= KY["dusme_bit"] and ky_etkin()
def _ky_uygulama(): return os.environ.get("SUFLOR_UYGULAMA") or AYAR["uygulama"]
def _ky_gunluk(olay, **alan):  # konsol + canli/sohbet-olay.jsonl (metinsiz; Aşama 2 Adım 6 aynı dosyayı kullanır). Yazılamazsa yalnız konsol
    print(f"YEREL KONUŞ: {olay}" + "".join(f" · {k}={v}" for k, v in alan.items()))
    try:
        satir = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "olay": olay, **alan}
        with LOCK: write([(os.path.join(BASE, "sohbet-olay.jsonl"), json.dumps(satir, ensure_ascii=False) + "\n")])
    except Exception: pass
def _ky_saat(duvar):  # cal_basladi.duvar (Unix saati) doğrudan ses saatidir (ts süreçler arası karşılaştırılamaz: sistem Python 3.9'unda monotonic süreç başına sıfırlanır); yoksa şimdi
    try:
        if duvar is not None: return float(duvar)
    except (TypeError, ValueError): pass
    if not KY["saat_uyari"]: KY["saat_uyari"] = True; print("YEREL KONUŞ: cal_basladi'da duvar saati yok — ses saati olarak olayın geldiği an kullanılıyor")
    return time.time()
def ky_gonder(o):  # tek satır JSON; bağlı değilse ya da yazılamazsa False
    s = KY["s"]
    if not s: return False  # bağlantı kabulü (ilk nabız) beklenirken de komut gidebilir (durum isteği)
    try:
        with KY["yaz_kilit"]: s.sendall((json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        return True
    except (OSError, ValueError): _ky_kopar(s); return False
def _ky_kopar(s=None):
    with KY["kilit"]:
        if s is not None and KY["s"] is not s: return
        s = KY["s"]; KY.update(s=None, bagli=False, mik=False, vpio=False, sessiz_acik=False)
        for p in list(KY["calan"].values()): p._bit(-15, kesildi=True)
        KY["calan"].clear()
    try: s and s.close()
    except OSError: pass
# --- Çalıcı: Popen benzeri (stdin.write/flush/close, poll, wait, terminate, kill, returncode) ---------------------------------------------
class _KyGiris:  # çalıcının stdin'i: write → ses, close → cal_bitir; kopuk/kesik akışa yazmak boru gibi OSError verir
    def __init__(self, c): self.c = c; self.kapali = False
    def write(self, b):
        if self.kapali or self.c.returncode is not None: raise BrokenPipeError("yerel çalıcı kapalı")
        b = bytes(b)
        for i in range(0, len(b), 19200):  # ≈ 0,4 sn @ 24 kHz; satır ~26 KB
            if not ky_gonder({"t": "ses", "id": self.c.id, "b64": base64.b64encode(b[i:i + 19200]).decode()}): self.c._bit(-1, dustu=True); raise BrokenPipeError("yerel yardımcıya yazılamadı")
            self.c._ilk_ses()
        return len(b)
    def flush(self): pass
    def close(self):
        if self.kapali: return
        self.kapali = True
        if self.c.returncode is None:
            self.c._ilk_ses(); ky_gonder({"t": "cal_bitir", "id": self.c.id})
class KyCalici:
    yerel = True
    def __init__(self, sr, kayit=None):
        with KY["kilit"]: KY["sira"] += 1; self.id = f"c{KY['sira']}"
        self.sr = int(sr); self.kayit = kayit; self.returncode = None; self.basladi = False; self.kesildi = False; self.dustu = False; self.t_basla = 0.0
        self.ev_bitti = threading.Event(); self.ev_basladi = threading.Event(); self.stdin = _KyGiris(self); self._izleyen = False
    def poll(self): return self.returncode
    def wait(self, timeout=None):
        if not self.ev_bitti.wait(timeout): raise subprocess.TimeoutExpired("yerel-cal", timeout)
        return self.returncode
    def terminate(self):  # ses_durdur / araya girme: yardımcıda hemen kes
        if self.returncode is None: ky_gonder({"t": "kes"}); self._bit(-15, kesildi=True)
    kill = terminate
    def _bit(self, kod, kesildi=False, dustu=False):
        with KY["kilit"]:
            if self.returncode is not None: return
            self.returncode = kod; self.kesildi = kesildi or self.kesildi; self.dustu = dustu or self.dustu; KY["calan"].pop(self.id, None)
        self.ev_basladi.set(); self.ev_bitti.set()
    def _ilk_ses(self):  # ilk veri gidince 2 sn'lik cal_basladi bekçisi başlar
        if self._izleyen: return
        self._izleyen = True; threading.Thread(target=self._bekci, daemon=True).start()
    def _bekci(self):
        if self.ev_basladi.wait(KY_CAL_BASLA_SN) or self.returncode is not None: return
        ky_dusur("cal_basladi_yok", id=self.id)  # yardımcı cevap vermedi: bugünkü yola düş; çağıran .dustu'ya bakar
        ky_gonder({"t": "kes"}); self._bit(-1, dustu=True)
def ky_dusur(neden, **alan):  # KY_DUSME_BEKLE_SN boyunca yerel yol kapalı (çağıranlar bugünkü yola gider); günlüğe yerel_dusme
    KY["dusme_bit"] = time.time() + KY_DUSME_BEKLE_SN; KY["dusme"] += 1; _ky_gunluk("yerel_dusme", neden=neden, **alan)
def ky_cal_ac(sr, aygit=None, kayit=None):  # → KyCalici ya da None (yerel yol yok / aygıt verildi: çağıran bugünkü yolu izler). Aygıtlı yol (toplantıya ses) hiç yerel olmaz
    if aygit or not ky_hazir(): return None
    c = KyCalici(sr, kayit)
    with KY["kilit"]:
        for o in list(KY["calan"].values()): o._bit(-15, kesildi=True)  # yeni cal_ac önceki akışı keser (kesildi olayı da gelir)
        KY["calan"][c.id] = c
    if not ky_gonder({"t": "cal_ac", "id": c.id, "sr": c.sr}): c._bit(-1, dustu=True); return None
    return c
# --- M yolu: say → PCM → yardımcı --------------------------------------------------------------------------------------------------------
class _KyMetin:  # say'in stdin'i: metin birikir, close() işi başlatır
    def __init__(self, s): self.s = s; self.tamp = b""; self.kapali = False
    def write(self, b): self.tamp += b if isinstance(b, (bytes, bytearray)) else str(b).encode("utf-8"); return len(b)
    def flush(self): pass
    def close(self):
        if self.kapali: return
        self.kapali = True; threading.Thread(target=self.s._calis, args=(self.tamp,), daemon=True).start()
class KySay:  # subprocess.Popen(["/usr/bin/say", …, "-f", "-"]) yerine geçer; ses_basladi cal_basladi'dan gelir (çağıran .yerel görünce kendisi çağırmaz)
    yerel = True
    def __init__(self, argv, **kw):
        self.argv = list(argv); self.stdin = _KyMetin(self); self.returncode = None; self.ev = threading.Event(); self.iptal = False; self.alt = None; self.cal = None; self.yedek = None
    def poll(self): return self.returncode
    def wait(self, timeout=None):
        if not self.ev.wait(timeout): raise subprocess.TimeoutExpired("say", timeout)
        return self.returncode
    def terminate(self):
        self.iptal = True
        for p in (self.alt, self.cal, self.yedek):
            try: p and p.poll() is None and p.terminate()
            except Exception: pass
        if self.returncode is None: self.returncode = -15; self.ev.set()
    kill = terminate
    def _bit(self, kod):
        if self.returncode is None: self.returncode = kod
        self.ev.set()
    def _calis(self, metin):
        fd, yol = tempfile.mkstemp(suffix=".wav", prefix="suflor-say-"); os.close(fd)
        try:
            a = self.argv[:-2] if self.argv[-2:] == ["-f", "-"] else self.argv  # "-f -" dışındaki ses/hız seçenekleri aynen
            self.alt = subprocess.Popen(a + ["-o", yol, "--file-format=WAVE", f"--data-format=LEI16@{KY_SAY_SR}", "-f", "-"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try: self.alt.communicate(metin, timeout=20)
            except subprocess.TimeoutExpired: self.alt.kill(); raise OSError("say -o zaman aşımı")
            if self.iptal: return
            with wave.open(yol) as w: sr = w.getframerate(); pcm = w.readframes(w.getnframes())
            c = ky_cal_ac(sr, kayit=SES) if pcm and ky_hazir() else None
            if c is None: raise OSError("yerel çalıcı yok")
            self.cal = c
            try:
                c.stdin.write(pcm); c.stdin.close()
                while c.returncode is None and not self.iptal: c.ev_bitti.wait(0.1)
            except (BrokenPipeError, OSError): pass
            if c.dustu and not self.iptal: raise OSError("yardımcı çalmadı")
            self._bit(0 if c.returncode in (None, 0) else c.returncode)
        except Exception as e:  # say -o, yardımcı ya da bağlantı bozuldu: bugünkü yol (doğrudan say) — söz kaybolmaz
            if self.iptal: return self._bit(-15)
            if not isinstance(e, OSError) or "yerel" not in str(e) and "yardımcı" not in str(e): _ky_gunluk("yerel_dusme", neden="say_" + e.__class__.__name__)
            try:
                self.yedek = p = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try: p.stdin.write(metin); p.stdin.close()
                except OSError: pass
                try: ses_basladi(SES)
                except Exception: pass
                while p.poll() is None and not self.iptal: time.sleep(0.05)
                self._bit(p.returncode or 0)
            except OSError: self._bit(1)
        finally:
            try: os.remove(yol)
            except OSError: pass
def ky_say_popen():  # brifing-ses.py _ses_isci: yerel yol hazırsa KySay, değilse None (çağıran subprocess.Popen kullanır)
    return KySay if ky_hazir() else None
# --- D yolu: dış çalıcı çalarken sessiz çalıcı düğüm ---------------------------------------------------------------------------------
def ky_sessiz_sar(oyn):  # Pocket/Gemini çalıcısı (SuflorOynat) başlayınca çağrılır: bitene dek motorda sessiz düğüm açık (VPIO başvurusu). Yerel yol yoksa hiçbir şey yapmaz
    if not ky_hazir() or oyn is None: return
    with KY["kilit"]: KY["sessiz"] += 1; KY["sessiz_gen"] += 1
    _ky_sessiz_gonder()
    def bekle():
        t0 = time.time()
        try:
            while oyn.poll() is None and time.time() - t0 < 600: time.sleep(0.2)
        except Exception: pass
        with KY["kilit"]: KY["sessiz"] = max(0, KY["sessiz"] - 1); gen = KY["sessiz_gen"] = KY["sessiz_gen"] + 1
        if KY["sessiz"] == 0: threading.Timer(1.0, _ky_sessiz_kapat, args=(gen,)).start()  # art arda cümlelerde düğüm kapanıp açılmasın (uyum geçişi ~3 sn)
    threading.Thread(target=bekle, daemon=True).start()
def _ky_sessiz_gonder():
    if not KY["sessiz_acik"] and KY["vpio"] and ky_gonder({"t": "sessiz_dugum", "ac": True}): KY["sessiz_acik"] = True
def _ky_sessiz_kapat(gen):
    with KY["kilit"]:
        if KY["sessiz"] or KY["sessiz_gen"] != gen or not KY["sessiz_acik"]: return
        KY["sessiz_acik"] = False
    ky_gonder({"t": "sessiz_dugum", "ac": False})
# --- Mikrofon ---------------------------------------------------------------------------------------------------------------------------
def _ky_toplanti():
    f = globals().get("toplanti_var")
    try: return bool(f and f())
    except Exception: return False
def _ky_gizli():
    f = globals().get("gizli_acik")
    try: return bool(f and f())
    except Exception: return False
def ky_mik_ac(vpio):  # → bool. Toplantı sürerken ya da gizli kipte açılmaz; kulaklıkta vpio=False (karar çağıranın: Adım 4)
    if not ky_hazir() or _ky_toplanti() or _ky_gizli(): return False
    if not ky_gonder({"t": "mik_ac", "vpio": bool(vpio)}): return False
    with KY["kilit"]: KY.update(mik=True, vpio=bool(vpio), vpio_istek=bool(vpio), devam_vpio=None, vpio_bekle=0.0); KY["mik_kusak"] += 1
    if KY["sessiz"]: _ky_sessiz_gonder()
    return True
def ky_mik_kapat(neden=None):
    with KY["kilit"]: var = KY["mik"]; KY.update(mik=False, vpio=False, sessiz_acik=False); KY["mik_tamp"] = bytearray(); KY["mik_kusak"] += 1  # kuşak: kapanıştan önce kuyruğa girmiş öbekler atılır
    ok = ky_gonder({"t": "mik_kapat"})
    if var and neden: print(f"YEREL KONUŞ: mikrofon kapatıldı ({neden})")
    return ok
def ky_kes(): return ky_gonder({"t": "kes"})
def ky_durum_iste(): return ky_gonder({"t": "durum"})
def _ky_mik_sohbete(pcm, p):  # varsayılan mikrofon alıcısı: sohbet açıksa gövdeye; Adım 4 başka alıcı koyabilir (KY["mik_isle"])
    f = globals().get("_sohbet_parca_govde")
    if f and SOHBET["acik"]: f(pcm, p)
def _ky_mik_isci():  # mikrofon öbekleri okuma iş parçacığını bekletmesin: ayrı iş parçacığı; 100 ms öbekler ≥ KY_MIK_BIRLES_SN'de birleşip gövdeye gider (pano ≈ 0,5 sn'de bir verir; gövde her çağrıda tüm tamponu tarar)
    # 12 Kasım (denetim): mik_kapat'tan önce kuyruğa girmiş öbek kapanıştan sonra gövdeye gitmesin — her öğe kuşağıyla gelir; kuşak değişince tampon atılır,
    # gövdeye vermeden hemen önce bayrak ve kuşak yeniden denetlenir (gizli kip / toplantı kapatıcısı)
    q = KY["mik_q"]; tamp = bytearray(); esik = int(KY_MIK_BIRLES_SN * 16000 * 2); kusak = None
    while True:
        o = q.get()
        if o is None: return
        k, o = o
        if k != kusak: tamp = bytearray(); kusak = k
        if not KY["mik"] or k != KY["mik_kusak"] or _ky_toplanti() or _ky_gizli(): tamp = bytearray(); continue
        try: tamp += base64.b64decode(str(o.get("b64") or ""), validate=True)
        except ValueError: continue
        if len(tamp) < esik: continue
        pcm = bytes(tamp); tamp = bytearray()
        if not KY["mik"] or k != KY["mik_kusak"]: continue
        try: (KY["mik_isle"] or _ky_mik_sohbete)(pcm, {"pcm": base64.b64encode(pcm).decode()})
        except Exception as e: print(f"YEREL KONUŞ: mikrofon öbeği işlenemedi ({e.__class__.__name__}: {str(e)[:80]})")
# --- Olaylar, okuma, bağlantı, bekçi -------------------------------------------------------------------------------------------------
def _ky_olay(o):
    t = o.get("t")
    if t == "mik":
        KY["mik_n"] += 1
        if _ky_gizli() or _ky_toplanti():  # gizli kip ya da toplantı: öbek atılır, yardımcıya kapatma yeniden söylenir
            if KY["mik"]: ky_mik_kapat("gizli kip" if _ky_gizli() else "toplantı")
            return
        if not KY["mik"]: return  # mik_kapat sonrası yoldaki öbekler
        try: KY["mik_q"].put_nowait((KY["mik_kusak"], o))
        except queue.Full: KY["mik_atilan"] += 1
    elif t == "cal_basladi":
        c = KY["calan"].get(o.get("id"))
        if c and not c.basladi:
            c.basladi = True; c.t_basla = _ky_saat(o.get("duvar")); c.ev_basladi.set()  # sözleşme tutarsızlığı: "t" tür alanıdır, ses saati aynı adla gelemez → "ts" (mik olayındaki gibi); asıl saat "duvar"
            if c.kayit is not None:
                try: ses_basladi(c.kayit, c.t_basla)
                except Exception as e: print(f"YEREL KONUŞ: ses_basladi hatası ({e.__class__.__name__})")
    elif t == "cal_bitti":
        c = KY["calan"].get(o.get("id"))
        if c: c._bit(0)
    elif t == "kesildi":
        c = KY["calan"].get(o.get("id"))
        if c: c._bit(-15, kesildi=True)
    elif t in ("nabiz", "durum"):
        if not KY["bagli"]: KY["bagli"] = True; print("YEREL KONUŞ: yardımcı bağlantıyı kabul etti")  # anahtar doğruysa yardımcı hemen nabız yazar (kabul işareti)
        KY["durum"] = {k: v for k, v in o.items() if k != "t"}
        if "vpio" in o and KY["mik"] and not o["vpio"] and KY["vpio"] and t == "nabiz": KY["vpio"] = False
    elif t == "toplanti_mik": KY["vpio_bekle"] = time.time(); print(f"YEREL KONUŞ: toplantı uygulaması mikrofonu aldı ({str(o.get('uygulama'))[:30]}) — VPIO {'kapandı' if o.get('vpio_kapatildi') else 'zaten kapalı'}"); KY["vpio"] = False
    elif t == "aygit_degisti": KY["aygit_say"] += 1; print(f"YEREL KONUŞ: aygıt değişti (kulaklık={o.get('kulaklik')})")
    elif t == "hata":
        print(f"YEREL KONUŞ: yardımcı hatası — {str(o.get('neden'))[:40]} {str(o.get('ayrinti') or '')[:80]}")
        if o.get("neden") == "anahtar": KY["anahtar_hata"] = True
    k = KY["kanca"]
    if k:
        try: k(o)
        except Exception as e: print(f"YEREL KONUŞ: olay kancası hatası ({e.__class__.__name__})")
def _ky_oku(s):  # bağlantı sürerken satır satır olay; çıkış: bağlantı koptu, durduruldu ya da ayar kapandı
    tamp = b""; s.settimeout(1.0); KY["son_t"] = time.time()
    while not KY["dur"] and KY["s"] is s:
        if not ky_etkin(): return
        try: b = s.recv(65536)
        except socket.timeout:
            if time.time() - KY["son_t"] > KY_SESSIZ_SN: print(f"YEREL KONUŞ: {KY_SESSIZ_SN:.0f} sn nabız yok — yeniden bağlanılıyor"); return
            continue
        except OSError: return
        if not b: return
        KY["son_t"] = time.time(); tamp += b
        while b"\n" in tamp:
            sat, tamp = tamp.split(b"\n", 1)
            try: o = json.loads(sat.decode("utf-8", "replace"))
            except ValueError: continue
            if isinstance(o, dict):
                try: _ky_olay(o)
                except Exception as e: print(f"YEREL KONUŞ: olay işlenemedi ({e.__class__.__name__}: {str(e)[:80]})")
def _ky_dongu():
    bekle = KY_BAGLAN_ARA_SN
    while not KY["dur"]:
        if not ky_etkin(): time.sleep(1.0); continue
        yol = os.path.join(_ky_uygulama(), "konus-ses.sock"); s = None
        try:
            if not os.path.exists(yol): raise OSError("soket yok")
            anahtar = open(os.path.join(_ky_uygulama(), "ses-anahtari.txt"), encoding="utf-8").read().strip()
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(2.0); s.connect(yol)
            s.sendall((json.dumps({"t": "anahtar", "k": anahtar}) + "\n").encode("utf-8"))
            with KY["kilit"]: KY.update(s=s, bagli=False, anahtar_hata=False)  # bagli: ilk nabızla (kabul)
            print("YEREL KONUŞ: yardımcıya bağlanıldı, kabul bekleniyor"); ky_durum_iste(); bekle = KY_BAGLAN_ARA_SN
            _ky_oku(s)
            print("YEREL KONUŞ: bağlantı kapandı")
            bekle = KY_BAGLAN_AZAMI_SN if KY["anahtar_hata"] else KY_BAGLAN_ARA_SN
        except OSError as e:
            if KY["bagli"] or bekle == KY_BAGLAN_ARA_SN: pass  # ilk denemede sessiz: yardımcı hiç çalışmıyor olabilir (konsolu doldurma)
            bekle = min(KY_BAGLAN_AZAMI_SN, bekle * 1.5)
        finally:
            if s is not None: _ky_kopar(s)
        t0 = time.time()
        while not KY["dur"] and time.time() - t0 < bekle: time.sleep(0.1)
def _ky_bekci():  # toplantı ya da gizli kip: mikrofon 0,5 sn içinde kapanır (VPIO diğer mikrofonları ~22 dB kısar; toplantı hattı korunur)
    while not KY["dur"]:
        time.sleep(0.5)
        sohbet = bool((globals().get("SOHBET") or {}).get("acik"))
        if KY["mik"] and KY["bagli"]:
            if _ky_toplanti(): KY["devam_vpio"] = KY["vpio_istek"]; ky_mik_kapat("toplantı başladı")
            elif _ky_gizli(): ky_mik_kapat("gizli kip")
            elif KY["vpio_bekle"] and not KY["vpio"] and KY["vpio_istek"] and time.time() - KY["vpio_bekle"] > 3:  # toplantı uygulaması mikrofonu bırakınca yardımcı VPIO'yu kendiliğinden açmaz: yeniden iste
                KY["vpio_bekle"] = 0.0
                if sohbet and ky_gonder({"t": "mik_ac", "vpio": True}): KY["vpio"] = True; print("YEREL KONUŞ: toplantı mikrofonu bırakıldı — mik_ac{vpio:true} yeniden")
        elif KY["devam_vpio"] is not None and KY["bagli"] and sohbet and not _ky_toplanti() and not _ky_gizli():  # toplantı bitti, sohbet açık: mikrofon geri
            v = KY["devam_vpio"]; KY["devam_vpio"] = None
            if ky_mik_ac(v): print("YEREL KONUŞ: toplantı bitti — mikrofon yeniden açıldı")
def ky_baslat():  # idempotent; ayar kapalıysa hiçbir şey başlamaz
    if not ky_etkin(): return False
    with KY["kilit"]:
        if KY["dongu"] and KY["dongu"].is_alive(): return True
        KY["dur"] = False; KY["mik_q"] = queue.Queue(maxsize=200)
        KY["dongu"] = threading.Thread(target=_ky_dongu, daemon=True); KY["dongu"].start()
        threading.Thread(target=_ky_bekci, daemon=True).start(); KY["mik_p"] = threading.Thread(target=_ky_mik_isci, daemon=True); KY["mik_p"].start()
    return True
def ky_durdur():  # testler ve ayar kapanışı
    KY["dur"] = True; _ky_kopar()
    if KY["mik_q"]: KY["mik_q"].put(None)
def ky_view(): return {"etkin": ky_etkin(), "bagli": ky_hazir(), "mik": KY["mik"], "vpio": KY["vpio"], "dusme": KY["dusme"], "yardimci": KY["durum"]}
if ky_etkin() and (not deneme_aktarici() or os.environ.get("SUFLOR_UYGULAMA")): ky_baslat()  # deneme aktarıcısı canlı yardımcının tek bağlantısını çalmasın (SUFLOR_UYGULAMA ayrı soket demektir)
