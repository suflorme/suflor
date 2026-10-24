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
if "ses_basladi" not in globals():  # v0.95.0: çalma anı ölçümü brifing-ses.py'de; bu bölüm tek başına yüklenince (testler) etkisiz
    def ses_basladi(kayit=None): pass
GEMINI = {"durum": None, "hata": None, "anahtar": None, "anahtar_t": 0.0, "c": None, "kilit": threading.RLock(), "hata_t": 0.0}  # RLock: zaman aşımında aynı iş parçacığı yeniden dener
GEMINI_SESLER = ("Kore", "Aoede", "Leda", "Zephyr", "Sulafat", "Charon", "Puck", "Fenrir", "Orus", "Achird", "Algieba")
GEMINI_MODELLER = ("gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts")  # v0.80.11: günlük sınır yedek sırası
# (her modelin günlük sınırı ayrı; 19 Ekim ölçümü, Charon, ilk ses: 3.1 Flash 1,2 sn akışlı; 2.5 Flash 3,9 sn akışsız ve duygusuz — hızı için son yedek; 2.5 Pro 6,8 sn, alınmadı)
GEMINI_SECILIR = GEMINI_MODELLER[:2]  # ayarda seçilebilen (ana) modeller
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
# v0.81.0 (S92, kullanıcı 19 Ekim: "öncelik toplantı esnasında katılımcıları etkilemesi"): günlük sınır yüzünden Gemini yalnız katılımcıların duyduğu seste —
# toplantıya söyle, otonom cevap, toplantıda tanıtım/duyuru (toplantiya_soyle). Kulağa cevap, fısıltı, sesli çeviri ve toplantı dışı her okuma yerel ses (Piper;
# yoksa Mac). Ayar gemini_kapsam: toplanti (varsayılan) | hepsi (eski davranış).
# v0.98.0 (S104, kullanıcı 20 Ekim): sesli "Gemini sesiyle konuş" → toplantı dışında da Gemini, GEMINI_GECIS_SN (15 dk; ayar gemini_gecis_dk) sonra ya da
# "yerel sese dön" deyince hemen yerel ses (Pocket). Geçiş kalıcı değil: günlük sınır (model başına 100 istek) çabuk dolmasın; iki model de dolunca kendiliğinden biter.
GEMINI_GECIS = {"bitis": 0.0}
GEMINI_GECIS_SN = float(AYAR.get("gemini_gecis_dk") or 15) * 60
def gemini_gecis_acik():
    b = GEMINI_GECIS["bitis"]
    if not b: return False
    if time.time() >= b: GEMINI_GECIS["bitis"] = 0.0; print("GEMINI: geçiş süresi doldu — yerel ses"); return False
    if gemini_model() is None: GEMINI_GECIS["bitis"] = 0.0; print("GEMINI: günlük sınır doldu — geçiş bitti, yerel ses"); return False
    return True
GECIS_AC_RX = re.compile(r"(?i)^\W*gemini\W*\w*\s+(?:sesi\w*\s+)?(?:konuş|geç|dön|başla)\w*(?:\s+m[ıiuü]s[ıiuü]n)?\W*$|^\W*(?:use|switch to) (?:the )?gemini(?: voice)?\W*$")
GECIS_KAPAT_RX = re.compile(r"(?i)^\W*(?:yerel|kendi|normal|eski|pocket)\s+ses\w*\s+(?:dön|geç)\w*(?:\s+m[ıiuü]s[ıiuü]n)?\W*$|^\W*gemini'?\w*\s+(?:kapat|bırak)\w*\W*$"
                            r"|^\W*(?:back to|switch to|use) (?:the )?local voice\W*$")
def gemini_gecis_komut(metin):  # → okunacak kısa onay ya da None (komut değil). Yalnız tüm cümle komutsa (cümle içindeki "Gemini" sayılmaz)
    m = " ".join(str(metin or "").split())
    if GECIS_KAPAT_RX.search(m):
        acikti = gemini_gecis_acik(); GEMINI_GECIS["bitis"] = 0.0; print("GEMINI: geçiş kapatıldı (kullanıcı)" if acikti else "GEMINI: geçiş zaten kapalı")
        return _t("Tamam, yerel sese döndüm." if acikti else "Zaten yerel sesle konuşuyorum.", "OK, back to the local voice." if acikti else "I'm already using the local voice.")
    if not GECIS_AC_RX.search(m): return None
    if not gemini_var() or ("gizli_acik" in globals() and gizli_acik()): return _t("Gemini sesi şu an kullanılamıyor.", "The Gemini voice isn't available right now.")
    if gemini_model() is None: return _t("Gemini'nin bugünkü sınırı doldu, yerel sesle devam ediyorum.", "Gemini's daily limit is used up; staying with the local voice.")
    GEMINI_GECIS["bitis"] = time.time() + GEMINI_GECIS_SN; dk = round(GEMINI_GECIS_SN / 60)
    print(f"GEMINI: geçiş açıldı ({dk} dk, kullanıcı)")
    return _t(f"Tamam, {dk} dakika Gemini sesiyle konuşuyorum.", f"OK, I'll use the Gemini voice for {dk} minutes.")
def gemini_kapsam(): return "hepsi" if AYAR.get("gemini_kapsam") == "hepsi" or gemini_gecis_acik() else "toplanti"
def gemini_izinli(toplantiya=False):  # v0.89.0: gizli toplantıda hiç; sınır dolunca yerel ses — v0.128.0: Azure yedeği hazırsa o (azure-ses.py)
    return gemini_var() and not ("gizli_acik" in globals() and gizli_acik()) and (toplantiya or gemini_kapsam() == "hepsi") and (gemini_model() is not None or ("azure_hazir" in globals() and azure_hazir()))
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
# v0.127 (kullanıcı 24 Ekim): sınır dolunca 3.1/2.5'e değil yerel sese (Pocket) — onlar daha yavaş ve duygusuz. v0.127.0: ayardaki model dolunca öbür ana model
# (Lite ↔ 3.8 Flash; ayrı günlük sınır, günde 100 → 200 istek), o da dolunca yerel ses. Kendi sayacımız (gemini_bugun) sınıra varınca istek atılmaz (429 beklenmez).
# Ayar gemini_yedek_model: false → yalnız ayardaki model; true → eski uzun zincir (3.1, 2.5 dahil).
def gemini_zincir():
    m = str(AYAR.get("gemini_model") or GEMINI_MODELLER[0])
    m = m if m in GEMINI_SECILIR else GEMINI_MODELLER[0]
    y = AYAR.get("gemini_yedek_model")
    return (m,) + tuple(x for x in (GEMINI_MODELLER if y is True else () if y is False else GEMINI_SECILIR) if x != m)
def gemini_model():  # zincirde sınırı dolmamış ilk model; hepsi doluysa None (yerel ses)
    dolu = _kota(); b = gemini_bugun()
    for x in gemini_zincir():
        if x not in dolu and b.get(x, 0) < GEMINI_GUN_SINIR: return x
    return None
def gemini_gun_basi(simdi=None):  # Google'ın günlük sayacının başı: Pasifik gece yarısı (America/Los_Angeles, yaz/kış saati dahil; TR'de 10.00, kış saatinde 11.00).
    # Google'ın belgesi böyle der; 24 Ekim'de AI Studio kullanım grafikleri de UTC-8/PDT ile çiziliyordu (kesin kanıt değil). v0.127'ye kadar UTC gece yarısı
    # sayılıyordu (19 Ekim 429'unun bekleme süresinden). Sayaç kayarsa gerçek 429 _kota_doldu'ya Google'ın verdiği sıfırlanma anını yazar (o kayıt önce gelir).
    try:
        from zoneinfo import ZoneInfo
        bolge = ZoneInfo("America/Los_Angeles")
    except Exception: bolge = datetime.timezone(datetime.timedelta(hours=-8))  # tz verisi yoksa PST
    t = datetime.datetime.fromtimestamp(time.time() if simdi is None else simdi, bolge)
    return t.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
_BUGUN = {"t": 0.0, "v": {}}
GEMINI_GUN_SINIR = 100  # Tier 1, model başına günlük istek (19 Ekim 429 yanıtı); dakikada 10 istek de model başına (24 Ekim: Lite ve 3.8 Flash)
def gemini_bugun():  # model başına bugün (Google günü) yapılan başarılı istek sayısı (canli/gemini-ses.jsonl; önbellekten çalınanlar sayılmaz); 10 sn önbellek (pano sık yoklar)
    if time.time() - _BUGUN["t"] < 10: return dict(_BUGUN["v"])
    bas = gemini_gun_basi(); say = {}
    try:
        for l in open(os.path.join(BASE, "gemini-ses.jsonl"), encoding="utf-8"):
            try: d = json.loads(l); t = datetime.datetime.fromisoformat(d["t"]).timestamp()
            except (ValueError, KeyError): continue
            if t >= bas: say[d.get("model") or "?"] = say.get(d.get("model") or "?", 0) + 1
    except OSError: pass
    _BUGUN.update(t=time.time(), v=say)
    return dict(say)
def gemini_gunluk_view():  # panoya (⚙ Ayarlar → Gemini nerede): model sırasıyla bugünkü istek, sınır, dolu mu
    if not gemini_var(): return None
    b = gemini_bugun(); dolu = _kota()
    return {"modeller": [{"ad": m, "n": b.get(m, 0), "dolu": m in dolu or b.get(m, 0) >= GEMINI_GUN_SINIR} for m in GEMINI_MODELLER], "sinir": GEMINI_GUN_SINIR,
            "toplam": sum(b.values()), "uyari": GEMINI_KOTA.get("uyari_gun") == gemini_gun_basi()}
# v0.127: zincirin toplam günlük sınırının %80'i (GEMINI_UYARI_ORAN) dolunca Google günü başına bir kez kısa sesli uyarı (yerel sesle, okuma ve sohbet sırası
# boşalınca; Gemini isteği harcanmaz) ve günlükte bir satır; bir model dolunca bir satır (sıradaki model ya da yerel ses).
GEMINI_UYARI_ORAN = 0.8
GEMINI_UYARI = ("Gemini sesinin bugünkü sınırının yüzde sekseni doldu; dolunca yerel sese döneceğim.", "Gemini voice is at 80 percent of today's limit; I'll switch to the local voice when it runs out.")
GEMINI_UYARI_AZURE = ("Gemini sesinin bugünkü sınırının yüzde sekseni doldu; dolunca yedek sese geçeceğim.", "Gemini voice is at 80 percent of today's limit; I'll switch to the backup voice when it runs out.")
def _kota_bak(model):  # başarılı her istekten sonra
    b = gemini_bugun(); n = b.get(model, 0); gun = gemini_gun_basi(); z = gemini_zincir(); dolu = _kota()
    kalan = sum(0 if x in dolu else max(0, GEMINI_GUN_SINIR - b.get(x, 0)) for x in z); top = GEMINI_GUN_SINIR * len(z)
    if n >= GEMINI_GUN_SINIR and (GEMINI_KOTA.get("dolu_gun") or {}).get(model) != gun:
        GEMINI_KOTA["dolu_gun"] = {**(GEMINI_KOTA.get("dolu_gun") or {}), model: gun}; s = gemini_model()
        print(f"GEMINI: günlük sınır doldu ({n}/{GEMINI_GUN_SINIR}, {model}) — " + (f"sıradaki model {s}" if s else "okumalar Azure yedeğinde" if "azure_hazir" in globals() and azure_hazir() else "okumalar yerel seste"))
    if top - kalan >= top * GEMINI_UYARI_ORAN and kalan > 0 and GEMINI_KOTA.get("uyari_gun") != gun:
        GEMINI_KOTA["uyari_gun"] = gun
        print(f"GEMINI: günlük sınırın %{round(GEMINI_UYARI_ORAN * 100)}'i doldu ({top - kalan}/{top}, {len(z)} model) — sesli uyarı sırada")
        if "yerel_uyari" in globals(): yerel_uyari(_t(*(GEMINI_UYARI_AZURE if "azure_hazir" in globals() and azure_hazir() else GEMINI_UYARI)))
def gemini_view():
    return {"motor": "gemini", "durum": GEMINI["durum"] or "hazir", "hata": GEMINI["hata"], "ses": gemini_ses(), "model": gemini_model(), "kota_dolu": sorted(_kota()),
            "kapsam": gemini_kapsam(), "bugun": gemini_bugun(), "azure": azure_view() if "azure_view" in globals() else None}
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
def _gemini_kayit(metin, ses_sn, ilk, model=None):
    try: write([(os.path.join(BASE, "gemini-ses.jsonl"), json.dumps({"t": datetime.datetime.now().isoformat(timespec="seconds"), "model": model or gemini_model() or "",
                                                                     "karakter": len(metin), "ses_sn": round(ses_sn, 2), "ilk_ses": round(ilk, 2) if ilk else None}) + "\n")])
    except Exception as e: print(f"GEMINI: kayıt yazılamadı ({e.__class__.__name__})")
    _BUGUN["t"] = 0.0  # sayaç yeniden okunsun
def _oynat_bekle(oyn, sn):  # çalıcının bitmesini bekler; bu arada sıradaki parça belli olursa sesi önceden istenir (brifing-ses.py ses_sonraki_hazirla)
    son = time.time() + max(0.5, sn); bakildi = 0.0
    while oyn.poll() is None and time.time() < son:
        if "ses_sonraki_hazirla" in globals() and time.time() - bakildi > 0.1:
            bakildi = time.time()
            try: ses_sonraki_hazirla()
            except Exception as e: print(f"GEMINI: sıradaki hazırlanamadı ({e.__class__.__name__})")
        time.sleep(0.03)
    if oyn.poll() is None: raise subprocess.TimeoutExpired("oynat", sn)
def gemini_pcm(metin, ses=None, uslup=None, sabit=None):  # v0.79.0: çalmadan 24 kHz 16 bit ham ses (toplantıya söyle); olmazsa None
    return gemini_oku(metin, ses=ses, uslup=uslup, topla=True, sabit=sabit)
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
# v0.80.11 (kullanıcı, 19 Ekim): sabit kısa cümleler (bekleme cümleleri, "hı hı") önbellekten — her ses + üslup + cümle için GEMINI_SABIT_N farklı okuyuş
# bir kez Gemini'den alınıp canli/gemini-onbellek/'e yazılır, sonra Google'a gitmeden rastgele biri çalar (art arda aynısı değil). İsteklerin ~%20'si bekleme
# cümlesiydi (18–19 Ekim, 14/71); günlük sınır geç dolar, bekleme cümlesi beklemesiz başlar.
GEMINI_SABIT_N = 3
GEMINI_SABIT_EK = ("Buradayım.", "I'm here.")  # sohbette 30 sn sessizlik uyarısı (aktarici/sohbet.py); bekleme cümleleri BEKLE_* havuzlarından
_SABIT_SON = {}
GEMINI_SABIT_KISA = (3, 24)  # v0.127: en çok 3 sözcük ve 24 karakterlik söz de sabit sayılır (üçlü sahnedeki "Hadi ya!", "Haklısın, kabul." yinelenir; önbelleğe
# yazmak fazladan istek gerektirmez, yinelenince istek atılmaz). Üçlü sahnenin tepki ve onay havuzları (uclu-sahne.py) da öyle.
def _sabit_mi(metin):
    m = (metin or "").strip()
    if m in GEMINI_ONAY or m in GEMINI_SABIT_EK: return True
    if m and len(m) <= GEMINI_SABIT_KISA[1] and len(m.split()) <= GEMINI_SABIT_KISA[0]: return True
    g = globals()
    for ad in ("SAHNE_ARAYA", "SAHNE_TEPKI", "SAHNE_ONAY"):
        if m in (g.get(ad) or ()): return True
    for ad in ("BEKLE_GENEL", "BEKLE_TUR", "BEKLE_TUR_EN"):
        v = g.get(ad)
        vs = [x for l in v.values() for x in (l if isinstance(l, list) else [l])] if isinstance(v, dict) else (v or [])
        if m in vs: return True
    return False
def _sabit_klasor(metin, ses, uslup):
    import hashlib
    h = hashlib.sha1(f"{gemini_ses(ses)}\n{' '.join(str(uslup or '').split())}\n{metin.strip()}".encode()).hexdigest()[:16]
    return os.path.join(BASE, "gemini-onbellek", h)
def _sabit_dolu(metin, ses, uslup):
    try: return len([f for f in os.listdir(_sabit_klasor(metin, ses, uslup)) if f.endswith(".pcm")]) >= GEMINI_SABIT_N
    except OSError: return False
def _sabit_al(metin, ses, uslup):  # dolu önbellekten rastgele bir okuyuş (ham ses) ya da None (henüz GEMINI_SABIT_N okuyuş yok)
    import random
    k = _sabit_klasor(metin, ses, uslup)
    try: ds = sorted(f for f in os.listdir(k) if f.endswith(".pcm"))
    except OSError: return None
    if len(ds) < GEMINI_SABIT_N: return None
    secenek = [d for d in ds if d != _SABIT_SON.get(k)] or ds
    d = random.choice(secenek); _SABIT_SON[k] = d
    try: return open(os.path.join(k, d), "rb").read() or None
    except OSError: return None
def _sabit_yaz(metin, ses, uslup, pcm):
    k = _sabit_klasor(metin, ses, uslup)
    try:
        os.makedirs(k, exist_ok=True)
        n = len([f for f in os.listdir(k) if f.endswith(".pcm")])
        if n >= GEMINI_SABIT_N: return
        with open(os.path.join(k, f"{n}.pcm"), "wb") as f: f.write(pcm)
        with open(os.path.join(k, "metin.txt"), "w", encoding="utf-8") as f: f.write(f"{gemini_ses(ses)} · {metin.strip()}\n")
    except OSError: pass
def _pcm_cal(pcm, iptal=None, kayit=None, aygit=None, duzey=None):  # önbellekteki ham sesi kesintisiz çalıcıyla (yoksa WAV + afplay) çalar
    if duzey is not None: pcm = _duzey(pcm, duzey)
    if os.environ.get("SUFLOR_TEST_GEMINI_SESSIZ"): ses_basladi(kayit); return True
    if os.access(PIPER_OYNAT, os.X_OK):
        try: oyn = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)] + ([str(aygit)] if aygit else []), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError: return False
        if kayit is not None: kayit["p"] = oyn; ses_basladi(kayit)
        try:
            for i in range(0, len(pcm), 9600):
                if iptal and iptal(): break
                oyn.stdin.write(pcm[i:i + 9600]); oyn.stdin.flush()
            oyn.stdin.close()
            _oynat_bekle(oyn, len(pcm) / 2 / GEMINI_SR + 5)
        except (BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired): pass
        if oyn.poll() is None: oyn.terminate()
        return True
    if aygit: return False
    import tempfile, wave
    fd, yol = tempfile.mkstemp(suffix=".wav", prefix="suflor-gemini-"); os.close(fd)
    try:
        with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(GEMINI_SR); w.writeframes(pcm)
        pr = subprocess.Popen(["/usr/bin/afplay", yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if kayit is not None: kayit["p"] = pr; ses_basladi(kayit)
        pr.wait()
    finally:
        try: os.remove(yol)
        except OSError: pass
    return True
def _gemini_govde(metin, ses, uslup):
    return json.dumps({"contents": [{"role": "user", "parts": [{"text": (f"## Style:\n{' '.join(str(uslup).split())}\n" if uslup else "") + "## Transcript:\n" + metin}]}],
                       "generationConfig": {"responseModalities": ["audio"], "temperature": 1,
                                            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": gemini_ses(ses)}}}}}, ensure_ascii=False).encode()
# --- Önceden isteme (v0.127, kullanıcı 24 Ekim: "karışık yol" — istek azalsın, sesler arası boşluk kısalsın) ---------------------------------------
# Sıradaki parça belliyse (kuyrukta bekleyen Gemini parçası ya da üçlü sohbette öbür asistanın hazır sözü) sesi, çalan okuma sürerken ayrı bağlantıyla
# istenir ve bellekte biriktirilir; okuma sırası gelince istek atılmadan hemen çalar (boşluk ilk ses gecikmesi ~0,6 sn yerine çalıcının açılışı). İstek sayısı
# değişmez: aynı metin aynı sesle bir kez istenir. Kullanılmayan önceden alınmış ses GEMINI_ONCEDEN_SN sonra atılır (okuma kesildiyse hemen; istek boşa gider).
GEMINI_ONCEDEN = {}  # (metin, ses) → {"pcm": bytearray, "bitti": bool, "ok": bool, "t": zaman, "ilk": sn}
GEMINI_ONCEDEN_SN = 90
_ONCEDEN_K = threading.Lock()
def _onceden_anahtar(metin, ses): return (" ".join(str(metin or "").split()), gemini_ses(ses))
def gemini_onceden_var(metin, ses):
    with _ONCEDEN_K: return _onceden_anahtar(metin, ses) in GEMINI_ONCEDEN
def gemini_onceden_temizle(neden=None):
    with _ONCEDEN_K: n = len(GEMINI_ONCEDEN); GEMINI_ONCEDEN.clear()
    if n and neden: print(f"GEMINI: önceden alınan {n} ses atıldı ({neden})")
def gemini_onceden(metin, ses=None, uslup=None):  # sesi şimdiden iste (okumadan); → True: istendi ya da zaten isteniyor
    if not metin or not gemini_var() or (_sabit_mi(metin) and _sabit_dolu(metin, ses, uslup)) or time.time() - GEMINI["hata_t"] < GEMINI_BEKLE_SN: return False
    model = gemini_model()
    if not model: return False
    a = _onceden_anahtar(metin, ses); simdi = time.time()
    with _ONCEDEN_K:
        for k in [k for k, v in GEMINI_ONCEDEN.items() if simdi - v["t"] > GEMINI_ONCEDEN_SN]:
            GEMINI_ONCEDEN.pop(k); print(f"GEMINI: önceden alınan ses kullanılmadı · {k[0][:40]}")
        if a in GEMINI_ONCEDEN: return True
        o = GEMINI_ONCEDEN[a] = {"pcm": bytearray(), "bitti": False, "ok": False, "t": simdi, "ilk": None, "ev": threading.Event()}
    def al():
        c = None; t0 = time.time()
        try:
            c = (http.client.HTTPConnection if GEMINI_HOST.startswith("127.0.0.1") else http.client.HTTPSConnection)(GEMINI_HOST, timeout=GEMINI_ILK_SN)
            c.request("POST", f"/v1beta/models/{model}:streamGenerateContent?alt=sse", body=_gemini_govde(metin, ses, uslup),
                      headers={"Content-Type": "application/json", "x-goog-api-key": gemini_anahtar(), "Accept": "text/event-stream"})
            r = c.getresponse()
            if r.status != 200:
                hata = r.read()[:3000].decode("utf-8", "replace")
                if r.status == 429 and _gunluk_mu(hata): _kota_doldu(model, hata); print(f"GEMINI: {model} günlük sınırı doldu (önceden isterken)")
                else: print(f"GEMINI: önceden isteme HTTP {r.status} — okuma sırası gelince yeniden istenecek")
                return
            while True:
                satir = r.readline()
                if not satir: break
                s_ = satir.decode("utf-8", "replace").strip()
                if not s_.startswith("data:"): continue
                try: ol = json.loads(s_[5:])
                except ValueError: continue
                for b in _gemini_parcalar(ol):
                    if o["ilk"] is None: o["ilk"] = time.time() - t0
                    o["pcm"].extend(b); o["ev"].set()
            o["ok"] = bool(o["pcm"])
        except Exception as e: print(f"GEMINI: önceden isteme olmadı ({e.__class__.__name__})")
        finally:
            o["bitti"] = True; o["ev"].set()
            try: c and c.close()
            except OSError: pass
            if o["ok"]:
                _gemini_kayit(metin, len(o["pcm"]) / 2 / GEMINI_SR, o["ilk"], model); _kota_bak(model)
                print(f"GEMINI: {len(metin)} karakter önceden · ilk ses {o['ilk'] or 0:.2f} sn · {len(o['pcm']) / 2 / GEMINI_SR:.1f} sn ses · {time.time() - t0:.1f} sn'de geldi")
    threading.Thread(target=al, daemon=True).start()
    return True
def _onceden_al(metin, ses):
    with _ONCEDEN_K: return GEMINI_ONCEDEN.pop(_onceden_anahtar(metin, ses), None)
def _onceden_cal(o, metin, iptal, kayit):  # önceden istenen sesi çal (gelmeye devam ediyorsa akarak) → True/False; None: hiç ses gelmedi, normal istekle okunsun
    son = o["t"] + GEMINI_ILK_SN  # önceden isteme başladığından beri ilk ses süresi (okumadaki zaman aşımıyla aynı); geçtiyse normal istek
    while not o["pcm"] and not o["bitti"] and time.time() < son:
        if iptal and iptal(): return True
        o["ev"].wait(0.05)
    if not o["pcm"]: return None
    if o["bitti"]: return _pcm_cal(bytes(o["pcm"]), iptal=iptal, kayit=kayit) or None
    if os.environ.get("SUFLOR_TEST_GEMINI_SESSIZ") or not os.access(PIPER_OYNAT, os.X_OK):  # kesintisiz çalıcı yok: hepsi gelince
        while not o["bitti"]: o["ev"].wait(0.05)
        return _pcm_cal(bytes(o["pcm"]), iptal=iptal, kayit=kayit) or None
    try: oyn = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError: return None
    if kayit is not None: kayit["p"] = oyn
    yazilan = 0; ilk = True
    try:
        while True:
            if iptal and iptal(): break
            n = len(o["pcm"])
            if n > yazilan:
                oyn.stdin.write(bytes(o["pcm"][yazilan:n])); oyn.stdin.flush(); yazilan = n
                if ilk: ses_basladi(kayit); ilk = False
            elif o["bitti"]: break
            else: o["ev"].clear(); o["ev"].wait(0.05)
        oyn.stdin.close(); _oynat_bekle(oyn, yazilan / 2 / GEMINI_SR + 5)
    except (BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired): pass
    if oyn.poll() is None: oyn.terminate()
    print(f"GEMINI: önceden alınan ses çalındı · {len(metin)} karakter")
    return True
def gemini_oku(metin, iptal=None, kayit=None, ses=None, uslup=None, topla=False, aygit=None, duzey=None, sabit=None):
    # v0.128.0 (S151): Gemini okuyamazsa (sınır dolu, hata, bekleme) Azure MAI sesi (azure-ses.py, ayar azure_yedek); o da olmazsa çağıran yerel sese düşer
    r = _gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, sabit=sabit)
    if (r is None if topla else r is False) and metin and "azure_hazir" in globals() and azure_hazir():
        return azure_oku(metin, iptal=iptal, kayit=kayit, ses=ses, topla=topla, aygit=aygit, duzey=duzey)
    return r
def _gemini_oku(metin, iptal=None, kayit=None, ses=None, uslup=None, topla=False, aygit=None, duzey=None, _yeniden=False, sabit=None):
    # metni Gemini'yle okur; bitince True. Hiç ses çalınamadıysa False (çağıran Mac sesine düşer). iptal(): True dönerse kalan ses çalınmaz;
    # kayit["p"]: çalan süreç (ses_durdur keser). topla: çalmaz, ham sesi döndürür (None: alınamadı). aygit: Core Audio aygıt kimliği (BlackHole);
    # duzey: 0–1 ses düzeyi (kısık "hı hı").
    if not metin or not gemini_var(): return None if topla else False
    if aygit and not os.access(PIPER_OYNAT, os.X_OK): return False  # aygıta yalnız kesintisiz çalıcı çalabilir (afplay varsayılan çıkışa gider)
    sabit = _sabit_mi(metin) if sabit is None else sabit  # v0.81.0: çağıran söyleyebilir (kişilik tanıtımı, toplantı başı duyurusu)
    if sabit:
        pcm = _sabit_al(metin, ses, uslup)
        if pcm:
            print(f"GEMINI: önbellekten · {metin.strip()[:40]}")
            if topla: return _duzey(pcm, duzey) if duzey is not None else pcm
            return _pcm_cal(pcm, iptal=iptal, kayit=kayit, aygit=aygit, duzey=duzey)
    if time.time() - GEMINI["hata_t"] < GEMINI_BEKLE_SN: return None if topla else False
    model = gemini_model()
    if not model: return None if topla else False  # iki modelin de günlük sınırı dolu: istek atılmaz
    on = _onceden_al(metin, ses) if not topla and not aygit and duzey is None else None
    if on:
        r = _onceden_cal(on, metin, iptal, kayit)
        if r and sabit and on["ok"]: _sabit_yaz(metin, ses, uslup, bytes(on["pcm"]))
        if r is not None: return r
    govde = _gemini_govde(metin, ses, uslup)
    t0 = time.time(); ilk = None; nbayt = 0; oyn = None; sessiz = bool(os.environ.get("SUFLOR_TEST_GEMINI_SESSIZ")) or topla; tampon = bytearray(); ham = bytearray()
    def bitir(bekle):
        if oyn:
            try: oyn.stdin.close()
            except (OSError, ValueError): pass
            if bekle:
                try: _oynat_bekle(oyn, nbayt / 2 / GEMINI_SR - (time.time() - (t0 + (ilk or 0))) + 5)
                except subprocess.TimeoutExpired: pass
            if oyn.poll() is None: oyn.terminate()
        elif bekle and tampon and not sessiz:  # çalıcı yok: tek WAV, afplay
            import tempfile, wave
            fd, yol = tempfile.mkstemp(suffix=".wav", prefix="suflor-gemini-"); os.close(fd)
            try:
                with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(GEMINI_SR); w.writeframes(bytes(tampon))
                pr = subprocess.Popen(["/usr/bin/afplay", yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if kayit is not None: kayit["p"] = pr; ses_basladi(kayit)
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
                    print(f"GEMINI: {model} günlük sınırı doldu ({sn / 3600:.1f} saat sonra açılır)" + (f" — {oteki} ile devam" if oteki else " — iki model de dolu (yedek ya da yerel ses)"))
                    if oteki: return _gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=_yeniden, sabit=sabit)
                    return None if topla else False
                if r.status in (429, 503) and not _yeniden:  # v0.80.6: hız sınırı / geçici yoğunluk — önerilen süre (en çok GEMINI_429_EN_COK_SN) beklenip bir kez daha
                    bekle = _gemini_bekleme(hata, r.getheader("Retry-After")); t_b = time.time()
                    print(f"GEMINI: hız sınırı (HTTP {r.status}) — {bekle:.1f} sn bekleyip yeniden")
                    while time.time() - t_b < bekle:
                        if iptal and iptal(): return None if topla else True  # okuma kesildi: Mac sesine düşülmez
                        time.sleep(0.1)
                    return _gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=True, sabit=sabit)
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
                        if sessiz and not topla: ses_basladi(kayit)  # deneme kipi: ses çalınmaz, ilk parça geldi
                        if not sessiz and os.access(PIPER_OYNAT, os.X_OK):
                            try:
                                oyn = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)] + ([str(aygit)] if aygit else []), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                if kayit is not None: kayit["p"] = oyn
                            except OSError: oyn = None
                    nbayt += len(b)
                    if sabit: ham.extend(b)
                    if duzey is not None: b = _duzey(b, duzey)
                    if oyn:
                        try: oyn.stdin.write(b); oyn.stdin.flush()
                        except (BrokenPipeError, OSError, ValueError): _gemini_kapat(); return True  # çalıcı kesildi (ses_durdur)
                        if nbayt == len(b): ses_basladi(kayit)  # v0.95.0: ilk ses parçası çalıcıda
                    else: tampon.extend(b)
        except Exception as e:
            _gemini_kapat()
            if not nbayt and not _yeniden and not isinstance(e, RuntimeError):  # zaman aşımı / bağlantı: yeni bağlantıyla bir kez daha (HTTP hatası kalıcı, denenmez)
                print(f"GEMINI: ses gelmedi ({e.__class__.__name__}) — yeni bağlantıyla yeniden")
                return _gemini_oku(metin, iptal=iptal, kayit=kayit, ses=ses, uslup=uslup, topla=topla, aygit=aygit, duzey=duzey, _yeniden=True, sabit=sabit)
            if not nbayt:
                GEMINI.update(durum="hata", hata=str(e)[:200] or e.__class__.__name__, hata_t=time.time())
                print(f"GEMINI: okunamadı ({e.__class__.__name__}: {str(e)[:120]}) — Mac sesi, {GEMINI_BEKLE_SN:.0f} sn Gemini denenmez"); return None if topla else False
            print(f"GEMINI: akış yarıda kesildi ({e.__class__.__name__})"); ham.clear()  # yarım okuyuş önbelleğe girmez
    GEMINI.update(durum="hazir", hata=None)
    if sabit and ham and not (iptal and iptal()): _sabit_yaz(metin, ses, uslup, bytes(ham))
    bitir(True)
    _gemini_kayit(metin, nbayt / 2 / GEMINI_SR, ilk, model); _kota_bak(model)
    print(f"GEMINI: {len(metin)} karakter · ilk ses {ilk or 0:.2f} sn · {nbayt / 2 / GEMINI_SR:.1f} sn ses{' (toplandı)' if topla else ''}")
    if topla: return bytes(tampon) if tampon else None
    return nbayt > 0
# --- v0.80.0 (S87, kullanıcı 18 Ekim: "sesle ilgili her şey Gemini'ye") ------------------------------------------------------------------------
# gemini_kullan: anahtar var ve ses motoru Gemini ya da bir kişiliğin sesi Gemini → kısa okumalar (fısıltı, sesli çeviri, duyuru) da Gemini'yle.
# gemini_kisa: beklemeli kısa okuma (okuma kuyruğundan bağımsız; Gemini bağlantısı kilitle sırayla); olmazsa False, çağıran Piper/Mac sesine düşer.
def gemini_kullan():
    if not gemini_izinli(): return False  # v0.81.0: kısa okumalar (fısıltı, sesli çeviri) yalnız kullanıcıya — kapsam "toplanti"da yerel ses
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
# v0.127.0 (24 Ekim ölçümü, testler/arastirma-ses-20261024/sizinti): Türkçe yönerge Türkçe metinle aynı dilde olunca Gemini onu ara sıra sesli okuyor
# (uzun Türkçe üslupla Lite + 3.8 Flash 6/55; İngilizce yönergeyle okuma 0, yalnız cümleyi iki kez okuma 3/55). Bu yüzden Gemini'ye giden üslup İngilizce: kişilikte ses_uslup_en,
# yoksa Türkçe üslubun yalnız ilk cümlesi (kısa yönerge Flash 1/27); durum tonu, fısıltı ve çevirmen yönergesinin İngilizcesi.
def kisilik_uslup(k=None):
    k = kisilik() if k is None and "kisilik" in globals() else k
    en = str((k or {}).get("ses_uslup_en") or "").strip()
    if en: return en
    tr = str((k or {}).get("ses_uslup") or "").strip()
    return re.split(r"(?<=[.;!?])\s", tr, maxsplit=1)[0].rstrip(";").strip()
def ses_uslup_bul(metin, k=None, ek=None):  # kişiliğin üslubu + durum tonu + ek (fısıltı, çevirmen …); boşsa None
    k = kisilik() if k is None else k
    ton = ton_bul(metin); p = [kisilik_uslup(k)]
    if ton: p.append(TON_USLUP[ton][1])
    if ek: p.append(ek)
    u = " ".join(x for x in p if x)
    return u or None
