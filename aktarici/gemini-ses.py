# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("gemini-ses")); import edilmez.
# --- Gemini ile seslendirme (v0.78.0, S83 — kullanıcı 18 Ekim: kör dinlemede Gemini açık ara en iyi, Elif en kötü) -----------------------------
# Ayar "ses_motoru": "gemini" ve Anahtar Zinciri'nde anahtar varsa (ayar "gemini_anahtar" = öğe adı, varsayılan suflor-gemini; anahtar dosyaya,
# günlüğe, komut satırına yazılmaz) okumalar (Konuş/sohbet cevabı, sesli özet, brifing, "yazayım mı?") Gemini TTS ile okunur. Ses "gemini_ses"
# (hazır ses adı), model "gemini_model" (varsayılan 3.8 Flash-Lite: ilk ses ~0,7 sn, 3.8 Flash ~1,1 sn — ölçüm testler/arastirma-konusma-sesi-20261018).
# Kişilik dosyasında "ses: gemini" ya da "ses: gemini:Kore" o kişiliğe Gemini sesi verir.
# Gizlilik: okunacak cevap metni Google'a gider (ses kaydı gitmez). Kullanıcı kararı S83: proje yedeği zaten Google'da; ücretli katman (ücretsizde metin
# eğitimde kullanılır). v0.80.0 (S87): sesli çeviri, fısıltı, sesli özet (iki sesli), toplantıda duyuru da Gemini'yle; ton cümleye göre (aşağıda).
# Akış: streamGenerateContent (SSE) → 24 kHz ham ses parçaları → Suflor Oynat (kesintisiz çalıcı) stdin'i; ilk parça gelince çalmaya başlar.
# Ağ yoksa, anahtar geçersizse ya da 3 sn'de ses gelmezse (yeni bağlantıyla bir kez daha denendikten sonra) False döner, çağıran Mac sesine düşer;
# hata sonrası GEMINI_BEKLE_SN Gemini denenmez (her cümle beklemesin). Kullanım canli/gemini-ses.jsonl'e (karakter, ses süresi, ilk ses) yazılır — maliyet: Flash-Lite ses 6 $/M token = 25 token/sn
# (2026 sonuna kadar ~0,009 $/dk; 1 Ocak 2027'den iki katı).
import http.client, re
GEMINI = {"durum": None, "hata": None, "anahtar": None, "anahtar_t": 0.0, "c": None, "kilit": threading.RLock(), "hata_t": 0.0}  # RLock: zaman aşımında aynı iş parçacığı yeniden dener
GEMINI_SESLER = ("Kore", "Aoede", "Leda", "Zephyr", "Sulafat", "Charon", "Puck", "Fenrir", "Orus", "Achird", "Algieba")
GEMINI_MODELLER = ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts")
GEMINI_SR = 24000
GEMINI_HOST = os.environ.get("SUFLOR_TEST_GEMINI_HOST") or "generativelanguage.googleapis.com"  # deneme: 127.0.0.1:<port> (TLS'siz)
GEMINI_ILK_SN = 3.0  # v0.80.2: 5 → 3 sn (ilk ses p90 0,7 sn); ses gelmezse yeni bağlantıyla bir kez daha denenir
GEMINI_BEKLE_SN = 15.0  # v0.80.2: iki deneme de olmazsa Gemini bu kadar denenmez (60 sn'de kullanıcı bir dakika Mac sesi duydu, 18 Ekim)
GEMINI_ONAY = ("Hı hı.", "Hıhı.", "Hı hı, evet.", "Hım hım.")  # v0.79.0: aktif dinleme / alındı (tepki_cal), o anda üretilir; aynı klip tekrarlanmaz
GEMINI_ONAY_USLUP = "Dinlerken araya giren kısa, kısık ve doğal bir onay sesi; tek nefeste, vurgusuz."
def gemini_anahtar():
    if os.environ.get("SUFLOR_TEST_GEMINI_ANAHTAR") is not None: return os.environ["SUFLOR_TEST_GEMINI_ANAHTAR"]
    if GEMINI["anahtar"] is not None and time.time() - GEMINI["anahtar_t"] < 300: return GEMINI["anahtar"]
    try: k = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", str(AYAR.get("gemini_anahtar") or "suflor-gemini"), "-w"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): k = ""
    GEMINI.update(anahtar=k, anahtar_t=time.time()); return k
def gemini_var(): return bool(gemini_anahtar())
def gemini_acik(): return AYAR.get("ses_motoru") == "gemini" and gemini_var()
def gemini_ses(ad=None):
    v = str(ad or AYAR.get("gemini_ses") or "Charon")
    return v if v in GEMINI_SESLER else "Charon"
# v0.80.10 (19 Ekim): Google'ın günlük sınırı model başına (Tier 1'de 100 istek/gün, "generate_requests_per_model_per_day"). Dolunca o model
# sıfırlanana kadar (gövdedeki retryDelay) hiç denenmez, öteki modele geçilir; ikisi de doluysa istek atılmadan Mac sesi. Kayıt canli/gemini-kota.json.
GEMINI_KOTA = {"dolu": None}
def _kota_yol(): return os.path.join(BASE, "gemini-kota.json")
def _kota():
    if GEMINI_KOTA["dolu"] is None:
        try: GEMINI_KOTA["dolu"] = {k: float(v) for k, v in json.load(open(_kota_yol(), encoding="utf-8")).items()}
        except (OSError, ValueError, AttributeError): GEMINI_KOTA["dolu"] = {}
    simdi = time.time()
    return {k: v for k, v in GEMINI_KOTA["dolu"].items() if v > simdi}
def _kota_doldu(model, govde):
    m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', govde or "")
    sn = float(m.group(1)) if m else 3600.0
    GEMINI_KOTA["dolu"] = dict(_kota(), **{model: time.time() + sn})
    try:
        with open(_kota_yol(), "w", encoding="utf-8") as f: f.write(json.dumps(GEMINI_KOTA["dolu"]))
    except OSError: pass
    return sn
def _gunluk_mu(govde): return "per_day" in (govde or "") or "PerDay" in (govde or "")
def gemini_model():  # ayardaki model; günlük sınırı dolduysa öteki; ikisi de doluysa None
    m = str(AYAR.get("gemini_model") or GEMINI_MODELLER[0])
    m = m if m in GEMINI_MODELLER else GEMINI_MODELLER[0]
    dolu = _kota()
    for x in (m,) + tuple(y for y in GEMINI_MODELLER if y != m):
        if x not in dolu: return x
    return None
def gemini_view():
    return {"motor": "gemini", "durum": GEMINI["durum"] or "hazir", "hata": GEMINI["hata"], "ses": gemini_ses(), "model": gemini_model(), "kota_dolu": sorted(_kota())}
def _gemini_baglanti():
    if GEMINI["c"] is None:
        GEMINI["c"] = (http.client.HTTPConnection if GEMINI_HOST.startswith("127.0.0.1") else http.client.HTTPSConnection)(GEMINI_HOST, timeout=GEMINI_ILK_SN)
    return GEMINI["c"]
def _gemini_kapat():
    c, GEMINI["c"] = GEMINI["c"], None
    try: c and c.close()
    except OSError: pass
def _gemini_parcalar(o):  # SSE olayındaki base64 ses parçaları (inlineData.data)
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "data" and isinstance(v, str) and len(v) > 16:
                try: yield base64.b64decode(v)
                except ValueError: pass
            else: yield from _gemini_parcalar(v)
    elif isinstance(o, list):
        for x in o: yield from _gemini_parcalar(x)
def _gemini_kayit(metin, ses_sn, ilk):
    try: write([(os.path.join(BASE, "gemini-ses.jsonl"), json.dumps({"t": datetime.datetime.now().isoformat(timespec="seconds"), "model": gemini_model() or "",
                                                                     "karakter": len(metin), "ses_sn": round(ses_sn, 2), "ilk_ses": round(ilk, 2) if ilk else None}) + "\n")])
    except Exception as e: print(f"GEMINI: kayıt yazılamadı ({e.__class__.__name__})")
def gemini_pcm(metin, ses=None, uslup=None):  # v0.79.0: çalmadan 24 kHz 16 bit ham ses (toplantıya söyle); olmazsa None
    return gemini_oku(metin, ses=ses, uslup=uslup, topla=True)
def _duzey(b, duzey):  # ham sesi kısar (hı hı); duzey 0–1
    import array
    a = array.array("h", b[:len(b) // 2 * 2]); f = max(0.0, min(1.0, float(duzey)))
    for i in range(len(a)): a[i] = int(a[i] * f)
    return a.tobytes()
GEMINI_429_EN_COK_SN = 4.0  # v0.80.6 (19 Ekim: art arda istekte "kota aşıldı" 429): cümle cümle okumada hız sınırına takılınca Mac sesine düşmeden önce
def _gemini_bekleme(govde, retry_after=None):  # sunucunun önerdiği bekleme (Retry-After başlığı ya da gövdedeki "retryDelay": "2s"); 0,5–GEMINI_429_EN_COK_SN, yoksa 1,5
    sn = None
    try: sn = float(retry_after) if retry_after else None
    except ValueError: sn = None
    if sn is None:
        m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', govde or "")
        sn = float(m.group(1)) if m else 1.5
    return max(0.5, min(GEMINI_429_EN_COK_SN, sn))
def gemini_oku(metin, iptal=None, kayit=None, ses=None, uslup=None, topla=False, aygit=None, duzey=None, _yeniden=False):
    # metni Gemini'yle okur; bitince True. Hiç ses çalınamadıysa False (çağıran Mac sesine düşer). iptal(): True dönerse kalan ses çalınmaz;
    # kayit["p"]: çalan süreç (ses_durdur keser). topla: çalmaz, ham sesi döndürür (None: alınamadı). aygit: Core Audio aygıt kimliği (BlackHole);
    # duzey: 0–1 ses düzeyi (kısık "hı hı").
    if not metin or not gemini_var(): return None if topla else False
    if aygit and not os.access(PIPER_OYNAT, os.X_OK): return False  # aygıta yalnız kesintisiz çalıcı çalabilir (afplay varsayılan çıkışa gider)
    if time.time() - GEMINI["hata_t"] < GEMINI_BEKLE_SN: return None if topla else False
    model = gemini_model()
    if not model: return None if topla else False  # iki modelin de günlük sınırı dolu: istek atılmaz
    govde = json.dumps({"contents": [{"role": "user", "parts": [{"text": (f"## Style:\n{' '.join(str(uslup).split())}\n" if uslup else "") + "## Transcript:\n" + metin}]}],
                        "generationConfig": {"responseModalities": ["audio"], "temperature": 1,
                                             "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": gemini_ses(ses)}}}}}, ensure_ascii=False).encode()
    t0 = time.time(); ilk = None; nbayt = 0; oyn = None; sessiz = bool(os.environ.get("SUFLOR_TEST_GEMINI_SESSIZ")) or topla; tampon = bytearray()
    def bitir(bekle):
        if oyn:
            try: oyn.stdin.close()
            except (OSError, ValueError): pass
            if bekle:
                try: oyn.wait(timeout=nbayt / 2 / GEMINI_SR - (time.time() - (t0 + (ilk or 0))) + 5)
                except subprocess.TimeoutExpired: pass
            if oyn.poll() is None: oyn.terminate()
        elif bekle and tampon and not sessiz:  # çalıcı yok: tek WAV, afplay
            import tempfile, wave
            fd, yol = tempfile.mkstemp(suffix=".wav", prefix="suflor-gemini-"); os.close(fd)
            try:
                with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(GEMINI_SR); w.writeframes(bytes(tampon))
                pr = subprocess.Popen(["/usr/bin/afplay", yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if kayit is not None: kayit["p"] = pr
                pr.wait()
            finally:
                try: os.remove(yol)
                except OSError: pass
    with GEMINI["kilit"]:  # tek bağlantı, sırayla (okuma kuyruğu zaten tek işçi)
        try:
            for deneme in (0, 1):  # kalıcı bağlantı sunucu tarafında kapanmışsa bir kez yeniden kur
                c = _gemini_baglanti()
                try:
                    c.request("POST", f"/v1beta/models/{model}:streamGenerateContent?alt=sse", body=govde,
                              headers={"Content-Type": "application/json", "x-goog-api-key": gemini_anahtar(), "Accept": "text/event-stream"})
                    r = c.getresponse(); break
                except (http.client.HTTPException, BrokenPipeError, ConnectionResetError):  # sunucu kapatmış ya da bağlantı yarım kalmış
                    _gemini_kapat()
                    if deneme: raise
            if r.status != 200:
                hata = r.read()[:3000].decode("utf-8", "replace"); _gemini_kapat()
                if r.status == 429 and _gunluk_mu(hata):  # günlük sınır: beklemek işe yaramaz — model sıfırlanana kadar bırakılır, öteki hemen denenir
                    sn = _kota_doldu(model, hata); oteki = gemini_model()
                    print(f"GEMINI: {model} günlük sınırı doldu ({sn / 3600:.1f} saat sonra açılır)" + (f" — {oteki} ile devam" if oteki else " — iki model de dolu, Mac sesi"))
                    if oteki: return gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=_yeniden)
                    return None if topla else False
                if r.status in (429, 503) and not _yeniden:  # v0.80.6: hız sınırı / geçici yoğunluk — önerilen süre (en çok GEMINI_429_EN_COK_SN) beklenip bir kez daha
                    bekle = _gemini_bekleme(hata, r.getheader("Retry-After")); t_b = time.time()
                    print(f"GEMINI: hız sınırı (HTTP {r.status}) — {bekle:.1f} sn bekleyip yeniden")
                    while time.time() - t_b < bekle:
                        if iptal and iptal(): return None if topla else True  # okuma kesildi: Mac sesine düşülmez
                        time.sleep(0.1)
                    return gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=True)
                raise RuntimeError(f"HTTP {r.status}: {' '.join(hata.split())[:160]}")
            while True:
                satir = r.readline()
                if not satir: r.read(); break  # yanıt bitti; bağlantı sonraki istek için boşalır
                s = satir.decode("utf-8", "replace").strip()
                if not s.startswith("data:"): continue
                try: o = json.loads(s[5:])
                except ValueError: continue
                for b in _gemini_parcalar(o):
                    if iptal and iptal(): _gemini_kapat(); bitir(False); return True
                    if ilk is None:
                        ilk = time.time() - t0
                        if not sessiz and os.access(PIPER_OYNAT, os.X_OK):
                            try:
                                oyn = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)] + ([str(aygit)] if aygit else []), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                if kayit is not None: kayit["p"] = oyn
                            except OSError: oyn = None
                    nbayt += len(b)
                    if duzey is not None: b = _duzey(b, duzey)
                    if oyn:
                        try: oyn.stdin.write(b); oyn.stdin.flush()
                        except (BrokenPipeError, OSError, ValueError): _gemini_kapat(); return True  # çalıcı kesildi (ses_durdur)
                    else: tampon.extend(b)
        except Exception as e:
            _gemini_kapat()
            if not nbayt and not _yeniden and not isinstance(e, RuntimeError):  # zaman aşımı / bağlantı: yeni bağlantıyla bir kez daha (HTTP hatası kalıcı, denenmez)
                print(f"GEMINI: ses gelmedi ({e.__class__.__name__}) — yeni bağlantıyla yeniden")
                return gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=True)
            if not nbayt:
                GEMINI.update(durum="hata", hata=str(e)[:200] or e.__class__.__name__, hata_t=time.time())
                print(f"GEMINI: okunamadı ({e.__class__.__name__}: {str(e)[:120]}) — Mac sesi, {GEMINI_BEKLE_SN:.0f} sn Gemini denenmez"); return None if topla else False
            print(f"GEMINI: akış yarıda kesildi ({e.__class__.__name__})")
    GEMINI.update(durum="hazir", hata=None)
    bitir(True)
    _gemini_kayit(metin, nbayt / 2 / GEMINI_SR, ilk)
    print(f"GEMINI: {len(metin)} karakter · ilk ses {ilk or 0:.2f} sn · {nbayt / 2 / GEMINI_SR:.1f} sn ses{' (toplandı)' if topla else ''}")
    if topla: return bytes(tampon) if tampon else None
    return nbayt > 0
# --- v0.80.0 (S87, kullanıcı 18 Ekim: "sesle ilgili her şey Gemini'ye") ------------------------------------------------------------------------
# gemini_kullan: anahtar var ve ses motoru Gemini ya da bir kişiliğin sesi Gemini → kısa okumalar (fısıltı, sesli çeviri, duyuru) da Gemini'yle.
# gemini_kisa: beklemeli kısa okuma (okuma kuyruğundan bağımsız; Gemini bağlantısı kilitle sırayla); olmazsa False, çağıran Piper/Mac sesine düşer.
def gemini_kullan():
    if not gemini_var(): return False
    if AYAR.get("ses_motoru") == "gemini": return True
    try: return any(str(k.get("ses") or "").startswith("gemini") for k in kisilikler())
    except Exception: return False
def gemini_kisilik_sesi(k=None):  # kişiliğin Gemini sesi (ses: gemini:Kore → Kore; ses: gemini → ayardaki); kişilik Gemini değilse ayardaki ses
    s = str((k or {}).get("ses") or "")
    return gemini_ses(s.split(":", 1)[1].strip() if s.startswith("gemini:") else None)
def gemini_kisa(metin, ses=None, uslup=None, duzey=None):
    if not metin or not gemini_kullan(): return False
    if os.environ.get("SUFLOR_TEST_BASLAT") and not os.environ.get("SUFLOR_TEST_GEMINI_HOST"): print(f"GEMINI (deneme, kısa): {gemini_ses(ses)} · {metin}"); return True
    return bool(gemini_oku(metin, ses=ses, uslup=uslup, duzey=duzey))
# Duruma göre ton: Gemini'ye giden üslup = kişiliğin ses_uslup'u + durum. Durum iki yerden: Claude cevabın başına <ton:ad> yazdıysa o (o cevabın
# kalanı için, TON_SURE_SN), yoksa cümlenin kendisinden kural (kötü haber, uyarı, acele). <ton:…> hiçbir seste okunmaz, panoda görünmez.
TON_USLUP = {
    "kotu_haber": ("Kötü bir haber veriyor: üzgün ama sakin, yumuşak ve anlayışlı; acele etmeden.", "Delivering bad news: sorry but calm, soft and understanding; unhurried."),
    "uyari": ("Uyarıyor: net, ciddi ve dikkat çekici; telaşsız.", "Warning: clear, serious and attention-getting; not alarmed."),
    "acele": ("Zaman dar: biraz hızlı, kısa ve net; telaşsız.", "Time is short: a bit faster, brief and clear; not frantic."),
    "sakin": ("Ortam gergin: çok sakin, alçak ve yavaş; yatıştırıcı, şakasız.", "The room is tense: very calm, low and slow; soothing, no jokes."),
    "yumusak": ("Ortam biraz gergin: yumuşak, sıcak ve uzlaştırıcı.", "The room is a little tense: soft, warm and conciliatory."),
    "ciddi": ("Ciddi ve ölçülü; şakasız.", "Serious and measured; no jokes."),
}
TON_RX = re.compile(r"\s*<ton:\s*([a-z_]+)\s*>\s*", re.I)
TON_KURAL = [  # (ton, kalıp) — ilk eşleşen; yalnız Gemini sesinde etkili
    ("kotu_haber", re.compile(r"\b(maalesef|ne yazık ki|üzgünüm|başarısız oldu|kaybettik|iptal edildi|reddedildi|unfortunately|i'm sorry|sadly)\b", re.I)),
    ("uyari", re.compile(r"\b(dikkat|uyarı|uyarıyorum|risk|tehlike|acil|ciddi bir sorun|önemli bir sorun|warning|careful|urgent|critical)\b", re.I)),
    ("acele", re.compile(r"\b(şimdi başlıyor|birazdan başlıyor|\d+ dakika kaldı|acele|right now|starting now|in \d+ minutes?)\b", re.I)),
]
TON_SURE_SN = 45
TON = {"ad": None, "t": 0.0}
def ton_ayikla(metin):  # metindeki <ton:ad> → (temiz metin, ad ya da None); ad bilinmiyorsa yok sayılır ("normal" tonu sıfırlar)
    m = TON_RX.search(metin or "")
    if not m: return metin, None
    ad = m.group(1).lower(); temiz = re.sub(r"\s{2,}", " ", TON_RX.sub(" ", metin)).strip()
    return temiz, (ad if ad in TON_USLUP or ad == "normal" else None)
def ton_kur(ad):
    TON.update(ad=ad, t=time.time())
    if ad: print(f"SES: ton {ad} (Claude)")
def ton_sifirla(): TON.update(ad=None, t=0.0)
def ton_bul(metin):  # → durum adı ya da None
    if TON["ad"] and time.time() - TON["t"] < TON_SURE_SN: return None if TON["ad"] == "normal" else TON["ad"]
    for ad, rx in TON_KURAL:
        if rx.search(metin or ""): return ad
    return None
def ses_uslup_bul(metin, k=None, ek=None):  # kişiliğin üslubu + durum tonu + ek (fısıltı, çevirmen …); boşsa None
    k = kisilik() if k is None else k
    ton = ton_bul(metin); p = [str((k or {}).get("ses_uslup") or "").strip()]
    if ton: p.append(_t(*TON_USLUP[ton]))
    if ek: p.append(ek)
    u = " ".join(x for x in p if x)
    return u or None
