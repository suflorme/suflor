# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("azure-ses")); import edilmez. gemini-ses.py'den sonra yüklenir.
# --- Azure MAI sesi: Gemini'nin yedeği (v0.128.0, S151 — kullanıcı 24 Ekim: "Aydın sesi Gemini'ye yakın; duygu, telaffuz, İngilizce sözcük, sayı/tarih başarılı") ------
# Gemini okuyamayınca (iki modelin de günlük sınırı dolu, hata ya da hata sonrası bekleme) gemini_oku aynı çağrıyı buraya verir; Azure da olmazsa False/None
# döner, çağıran eskisi gibi yerel sese (Pocket → Mac) düşer. Ses Gemini sesinin cinsiyetine göre: kadın (Kore …) → Elif, erkek (Charon …) → Aydın;
# ayar azure_ses_kadin / azure_ses_erkek ile değişir. Model MAI-Voice-2.1-Flash (önizleme; ayar azure_model). Üslup ve ton yönergesi gitmez (Azure yalnız SSML biçimi alır).
# Ayar: azure_yedek: true (varsayılan kapalı — beta kullanıcısının metni kendiliğinden Microsoft'a gitmez), azure_anahtar = Anahtar Zinciri öğe adı
# (varsayılan suflor-azure-speech; anahtar dosyaya, günlüğe, komut satırına yazılmaz), azure_bolge (varsayılan westeurope).
# Gizlilik (S151): okunacak cevap metni Microsoft'a gider, ses kaydı gitmez; Azure anlık seslendirmede metni ve sesi saklamaz. Gizli toplantıda
# gemini_izinli kapalı olduğu için buraya hiç gelinmez. Ücretsiz katman (F0) sınırda durur, fatura çıkmaz; dakikada 20 istek.
# Akış: REST cognitiveservices/v1, raw-24khz-16bit-mono-pcm → Gemini ile aynı çalıcı. Kullanım canli/azure-ses.jsonl (karakter, ses süresi, ilk ses).
from xml.sax.saxutils import escape as _xml_escape
AZURE = {"anahtar": None, "anahtar_t": 0.0, "hata_t": 0.0, "hata": None, "kilit": threading.Lock()}
AZURE_KADIN = {"Kore", "Aoede", "Leda", "Zephyr", "Sulafat"}  # GEMINI_SESLER'in kadın sesleri
AZURE_ILK_SN = 4.0
AZURE_BEKLE_SN = 30.0  # hata sonrası bu kadar denenmez
AZURE_ETIKET_RX = re.compile(r"\s*<[a-z_ ]{1,20}(?::\s*[a-z_]+)?>\s*", re.I)  # Gemini'nin sözsüz ses ve ton etiketleri (<chuckle>, <ton:uyari>)
def azure_anahtar():
    if os.environ.get("SUFLOR_TEST_AZURE_ANAHTAR") is not None: return os.environ["SUFLOR_TEST_AZURE_ANAHTAR"]
    if AZURE["anahtar"] is not None and time.time() - AZURE["anahtar_t"] < 300: return AZURE["anahtar"]
    try: k = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", str(AYAR.get("azure_anahtar") or "suflor-azure-speech"), "-w"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): k = ""
    AZURE.update(anahtar=k, anahtar_t=time.time()); return k
def azure_hazir(): return AYAR.get("azure_yedek") is True and time.time() - AZURE["hata_t"] >= AZURE_BEKLE_SN and bool(azure_anahtar())
def azure_ses_adi(gses=None):  # Gemini sesi → Azure ses adı (tr-TR-Elif:MAI-Voice-2.1-Flash)
    kadin = gemini_ses(gses) in AZURE_KADIN
    ad = str(AYAR.get("azure_ses_kadin" if kadin else "azure_ses_erkek") or ("Elif" if kadin else "Aydin"))
    model = str(AYAR.get("azure_model", "MAI-Voice-2.1-Flash") or "")  # "" → standart nöral sesler
    return f"tr-TR-{ad}:{model}" if model else f"tr-TR-{ad}"
def _azure_host(): return os.environ.get("SUFLOR_TEST_AZURE_HOST") or f"{AYAR.get('azure_bolge') or 'westeurope'}.tts.speech.microsoft.com"
def _azure_kayit(ses, metin, ses_sn, ilk):
    try: write([(os.path.join(BASE, "azure-ses.jsonl"), json.dumps({"t": datetime.datetime.now().isoformat(timespec="seconds"), "ses": ses, "karakter": len(metin),
                                                                    "ses_sn": round(ses_sn, 2), "ilk_ses": round(ilk, 2) if ilk else None}) + "\n")])
    except Exception as e: print(f"AZURE: kayıt yazılamadı ({e.__class__.__name__})")
def azure_view():
    if AYAR.get("azure_yedek") is not True: return None
    return {"hazir": azure_hazir(), "hata": AZURE["hata"]}
def azure_oku(metin, iptal=None, kayit=None, ses=None, topla=False, aygit=None, duzey=None):
    # gemini_oku ile aynı sözleşme: bitince True (topla: ham ses), hiç ses çalınamadıysa False (topla: None)
    metin = re.sub(r"\s{2,}", " ", AZURE_ETIKET_RX.sub(" ", metin or "")).strip()
    if not metin or not azure_hazir(): return None if topla else False
    if aygit and not os.access(PIPER_OYNAT, os.X_OK): return False
    ad = azure_ses_adi(ses)
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="tr-TR"><voice name="{_xml_escape(ad)}">'
            f'{_xml_escape(metin)}</voice></speak>').encode()
    host = _azure_host(); t0 = time.time(); ilk = None; nbayt = 0; oyn = None; tampon = bytearray()
    sessiz = bool(os.environ.get("SUFLOR_TEST_GEMINI_SESSIZ")) or topla
    with AZURE["kilit"]:
        try:
            c = (http.client.HTTPConnection if host.startswith("127.0.0.1") else http.client.HTTPSConnection)(host, timeout=AZURE_ILK_SN)
            c.request("POST", "/cognitiveservices/v1", body=ssml, headers={"Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": "raw-24khz-16bit-mono-pcm",
                                                                           "Ocp-Apim-Subscription-Key": azure_anahtar(), "User-Agent": "suflor"})
            r = c.getresponse()
            if r.status != 200: raise RuntimeError(f"HTTP {r.status}: {' '.join(r.read()[:300].decode('utf-8', 'replace').split())[:160]}")
            while True:
                b = r.read1(9600) if hasattr(r, "read1") else r.read(9600)
                if not b: break
                if iptal and iptal():
                    if oyn and oyn.poll() is None: oyn.terminate()
                    c.close(); return None if topla else True
                if ilk is None:
                    ilk = time.time() - t0
                    if sessiz and not topla: ses_basladi(kayit)
                    if not sessiz and os.access(PIPER_OYNAT, os.X_OK):
                        try:
                            oyn = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)] + ([str(aygit)] if aygit else []), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            if kayit is not None: kayit["p"] = oyn
                        except OSError: oyn = None
                nbayt += len(b)
                if duzey is not None: b = _duzey(b, duzey)
                if oyn:
                    try: oyn.stdin.write(b); oyn.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError): c.close(); return True  # çalıcı kesildi (ses_durdur)
                    if nbayt == len(b): ses_basladi(kayit)
                else: tampon.extend(b)
            c.close()
        except Exception as e:
            if not nbayt:
                AZURE.update(hata=str(e)[:200] or e.__class__.__name__, hata_t=time.time())
                print(f"AZURE: okunamadı ({e.__class__.__name__}: {str(e)[:120]}) — yerel ses, {AZURE_BEKLE_SN:.0f} sn Azure denenmez"); return None if topla else False
            print(f"AZURE: akış yarıda kesildi ({e.__class__.__name__})")
    AZURE["hata"] = None
    if oyn:
        try: oyn.stdin.close()
        except (OSError, ValueError): pass
        try: _oynat_bekle(oyn, nbayt / 2 / GEMINI_SR - (time.time() - (t0 + (ilk or 0))) + 5)
        except subprocess.TimeoutExpired: pass
        if oyn.poll() is None: oyn.terminate()
    elif tampon and not sessiz: _pcm_cal(bytes(tampon), iptal=iptal, kayit=kayit, aygit=aygit)
    _azure_kayit(ad, metin, nbayt / 2 / GEMINI_SR, ilk)
    print(f"AZURE: {ad} · {len(metin)} karakter · ilk ses {ilk or 0:.2f} sn · {nbayt / 2 / GEMINI_SR:.1f} sn ses{' (toplandı)' if topla else ''}")
    if topla: return bytes(tampon) if tampon else None
    return nbayt > 0
