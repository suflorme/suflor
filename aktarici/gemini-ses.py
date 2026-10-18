# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("gemini-ses")); import edilmez.
# --- Gemini ile seslendirme (v0.78.0, S83 — kullanıcı 18 Ekim: kör dinlemede Gemini açık ara en iyi, Elif en kötü) -----------------------------
# Ayar "ses_motoru": "gemini" ve Anahtar Zinciri'nde anahtar varsa (ayar "gemini_anahtar" = öğe adı, varsayılan suflor-gemini; anahtar dosyaya,
# günlüğe, komut satırına yazılmaz) okumalar (Konuş/sohbet cevabı, sesli özet, brifing, "yazayım mı?") Gemini TTS ile okunur. Ses "gemini_ses"
# (hazır ses adı), model "gemini_model" (varsayılan 3.8 Flash-Lite: ilk ses ~0,7 sn, 3.8 Flash ~1,1 sn — ölçüm testler/arastirma-konusma-sesi-20261018).
# Kişilik dosyasında "ses: gemini" ya da "ses: gemini:Kore" o kişiliğe Gemini sesi verir.
# Gizlilik: okunacak cevap metni Google'a gider (ses kaydı gitmez). Kullanıcı kararı S83: proje yedeği zaten Google'da; ücretli katman (ücretsizde metin
# eğitimde kullanılır). Toplantıya söyle ve fısıltı Mac sesinde kalır.
# Akış: streamGenerateContent (SSE) → 24 kHz ham ses parçaları → Suflor Oynat (kesintisiz çalıcı) stdin'i; ilk parça gelince çalmaya başlar.
# Ağ yoksa, anahtar geçersizse ya da 5 sn'de ses gelmezse False döner, çağıran Mac sesine düşer; hata sonrası 60 sn Gemini denenmez (her cümle
# beklemesin). Kullanım canli/gemini-ses.jsonl'e (karakter, ses süresi, ilk ses) yazılır — maliyet: Flash-Lite ses 6 $/M token = 25 token/sn
# (2026 sonuna kadar ~0,009 $/dk; 1 Ocak 2027'den iki katı).
import http.client
GEMINI = {"durum": None, "hata": None, "anahtar": None, "anahtar_t": 0.0, "c": None, "kilit": threading.Lock(), "hata_t": 0.0}
GEMINI_SESLER = ("Kore", "Aoede", "Leda", "Zephyr", "Sulafat", "Charon", "Puck", "Fenrir", "Orus", "Achird", "Algieba")
GEMINI_MODELLER = ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts")
GEMINI_SR = 24000
GEMINI_HOST = os.environ.get("SUFLOR_TEST_GEMINI_HOST") or "generativelanguage.googleapis.com"  # deneme: 127.0.0.1:<port> (TLS'siz)
GEMINI_ILK_SN = 5.0
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
def gemini_model():
    m = str(AYAR.get("gemini_model") or GEMINI_MODELLER[0])
    return m if m in GEMINI_MODELLER else GEMINI_MODELLER[0]
def gemini_view():
    return {"motor": "gemini", "durum": GEMINI["durum"] or "hazir", "hata": GEMINI["hata"], "ses": gemini_ses(), "model": gemini_model()}
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
    try: write([(os.path.join(BASE, "gemini-ses.jsonl"), json.dumps({"t": datetime.datetime.now().isoformat(timespec="seconds"), "model": gemini_model(),
                                                                     "karakter": len(metin), "ses_sn": round(ses_sn, 2), "ilk_ses": round(ilk, 2) if ilk else None}) + "\n")])
    except Exception as e: print(f"GEMINI: kayıt yazılamadı ({e.__class__.__name__})")
def gemini_pcm(metin, ses=None, uslup=None):  # v0.79.0: çalmadan 24 kHz 16 bit ham ses (toplantıya söyle); olmazsa None
    return gemini_oku(metin, ses=ses, uslup=uslup, topla=True)
def _duzey(b, duzey):  # ham sesi kısar (hı hı); duzey 0–1
    import array
    a = array.array("h", b[:len(b) // 2 * 2]); f = max(0.0, min(1.0, float(duzey)))
    for i in range(len(a)): a[i] = int(a[i] * f)
    return a.tobytes()
def gemini_oku(metin, iptal=None, kayit=None, ses=None, uslup=None, topla=False, aygit=None, duzey=None):
    # metni Gemini'yle okur; bitince True. Hiç ses çalınamadıysa False (çağıran Mac sesine düşer). iptal(): True dönerse kalan ses çalınmaz;
    # kayit["p"]: çalan süreç (ses_durdur keser). topla: çalmaz, ham sesi döndürür (None: alınamadı). aygit: Core Audio aygıt kimliği (BlackHole);
    # duzey: 0–1 ses düzeyi (kısık "hı hı").
    if not metin or not gemini_var(): return None if topla else False
    if aygit and not os.access(PIPER_OYNAT, os.X_OK): return False  # aygıta yalnız kesintisiz çalıcı çalabilir (afplay varsayılan çıkışa gider)
    if time.time() - GEMINI["hata_t"] < 60: return None if topla else False
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
                    c.request("POST", f"/v1beta/models/{gemini_model()}:streamGenerateContent?alt=sse", body=govde,
                              headers={"Content-Type": "application/json", "x-goog-api-key": gemini_anahtar(), "Accept": "text/event-stream"})
                    r = c.getresponse(); break
                except (http.client.HTTPException, BrokenPipeError, ConnectionResetError):  # sunucu kapatmış ya da bağlantı yarım kalmış
                    _gemini_kapat()
                    if deneme: raise
            if r.status != 200:
                hata = r.read()[:300].decode("utf-8", "replace"); _gemini_kapat()
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
            if not nbayt:
                GEMINI.update(durum="hata", hata=str(e)[:200] or e.__class__.__name__, hata_t=time.time())
                print(f"GEMINI: okunamadı ({e.__class__.__name__}: {str(e)[:120]}) — Mac sesi, 60 sn Gemini denenmez"); return None if topla else False
            print(f"GEMINI: akış yarıda kesildi ({e.__class__.__name__})")
    GEMINI.update(durum="hazir", hata=None)
    bitir(True)
    _gemini_kayit(metin, nbayt / 2 / GEMINI_SR, ilk)
    print(f"GEMINI: {len(metin)} karakter · ilk ses {ilk or 0:.2f} sn · {nbayt / 2 / GEMINI_SR:.1f} sn ses{' (toplandı)' if topla else ''}")
    if topla: return bytes(tampon) if tampon else None
    return nbayt > 0
