# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("piper-ses")); import edilmez.
# --- Piper ile yerel Türkçe seslendirme (S36, S37) -----------------------------------------------------------------------------------
# Ayar "ses_motoru": "piper" + "piper_python" (Piper'ın Python ortamı) + "piper_model" (.onnx) varsa Türkçe okumalar (sesli çeviri,
# fısıltı, sesli özet, brifing, bas-konuş cevabı, "yazayım mı?") Piper'la okunur; ayar yoksa, dosya yoksa, arayüz dili Türkçe değilse ya da
# işçi hata verirse Mac sesine (say) düşülür. Ses dosyası depoda değildir (lisansı belirsiz; yalnız kullanıcının kendi kurulumu — S37).
# İşçi (piper-isci.py) aktarıcı açılırken bir kez yüklenir (~0,6 sn, ~0,35 GB) ve açık kalır; metin cümle cümle üretilir, ilk cümle hazır
# olunca çalınmaya başlar (afplay). Hız: "piper_hiz" (özet, cevap; varsayılan 1,0), "piper_hiz_kisa" (çeviri özü, fısıltı; varsayılan 1,15).
# Ses ayarı (v0.32.2): "piper_ton" / "piper_ritim" (noise_scale / noise_w; yoksa modelin 0,4 / 0,3'ü); "piper_hiz" 1,0 ≈ 6,6 hece/sn
# (13 Ekim ölçümü; radyo sunucusu ~5,1), 0,85 ≈ 5,8.
# Cümle arası (v0.32.2): Piper cümle sonunu kırpıyor, parçalar arka arkaya çalınınca cümleler birbirine biniyordu → ikinci cümleden başlayarak
# başa "piper_cumle_ara" sn sessizlik (varsayılan 0,4; hıza göre ölçekli; 0 kapatır; ; : sonrası 0,7, virgül sonrası 0,35 katı).
# Çalıcı: "Suflor Oynat.app" (oynat.swift) okumanın bütün cümlelerini tek akışta çalar — her cümleye ayrı afplay cümle başına ~0,75 sn ek
# boşluk veriyordu (13 Ekim ölçümü), duraklama kodun elinde değildi. Çalıcı yoksa afplay (parçalar cümle sonuna kadar birleşik).
# Ses ve metin Mac'ten çıkmaz.
import queue, tempfile, wave
PIPER = {"p": None, "durum": "kapali", "hata": None, "bekleyen": {}, "iptal": set(), "n": 0, "kilit": threading.Lock(), "baslat_t": 0.0}
PIPER_ISCI = _ilk(os.path.join(_UYG, "piper-isci.py"), os.path.join(_APP, "piper-isci.py"))
PIPER_OYNAT = os.path.join(AYAR["uygulama"], "Suflor Oynat.app", "Contents", "MacOS", "SuflorOynat")
PIPER_GECICI = os.path.join(tempfile.gettempdir(), f"suflor-piper-{A.port}")
def piper_acik():
    return AYAR.get("ses_motoru") == "piper" and ARAYUZ_DILI == "tr" and bool(AYAR.get("piper_python")) and bool(AYAR.get("piper_model"))
def piper_hiz(kisa=False):
    try: return float(AYAR.get("piper_hiz_kisa" if kisa else "piper_hiz") or (1.15 if kisa else 1.0))
    except (TypeError, ValueError): return 1.15 if kisa else 1.0
def piper_ara():
    try: return max(0.0, min(1.5, float(AYAR.get("piper_cumle_ara", 0.4))))
    except (TypeError, ValueError): return 0.4
# Uzun ünlü (v0.32.3): Piper "cuma"yı dʒˈuma okur (kısa a, vurgu başta); Türkçede dʒumˈaː. aktarici/uzun-unlu.json (+ kullanıcı eki
# canli/uzun-unlu.json) kök → IPA; metinde geçenler işçiye gider, işçi eki Piper'ın çözümlemesinden ekleyip [[ ham ses yazımı ]] yapar.
_UZUN_V = {"t": 0, "v": {}}
def piper_uzun(metin):
    if time.time() - _UZUN_V["t"] > 30:
        v = {}
        for yol in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "aktarici", "uzun-unlu.json"), os.path.join(BASE, "uzun-unlu.json")):
            try: v.update({str(k).lower(): str(x) for k, x in json.load(open(yol, encoding="utf-8")).items() if not str(k).startswith("_") and str(x).strip()})
            except FileNotFoundError: pass
            except (OSError, ValueError, AttributeError): print(f"PIPER: {os.path.basename(yol)} okunamadı")
        _UZUN_V.update(t=time.time(), v=v)
    k = metin.lower().replace("â", "a").replace("î", "i").replace("û", "u")
    return {a: x for a, x in _UZUN_V["v"].items() if a.replace("â", "a").replace("î", "i").replace("û", "u") in k}
def piper_ton():  # "piper_ton" (noise_scale, tonlama çeşitliliği) / "piper_ritim" (noise_w, hece süresi çeşitliliği); yoksa modelin kendi değeri
    o = {}
    for k, a in (("ton", "piper_ton"), ("ritim", "piper_ritim")):
        try:
            if AYAR.get(a) is not None: o[k] = max(0.0, min(1.5, float(AYAR[a])))
        except (TypeError, ValueError): pass
    return o
def piper_view():
    return {"motor": "piper" if piper_acik() else "mac", "durum": PIPER["durum"] if piper_acik() else None, "hata": PIPER["hata"] if piper_acik() else None,
            "calici": ("oynat" if os.access(PIPER_OYNAT, os.X_OK) else "afplay") if piper_acik() else None}
def _piper_okuyucu(p):
    for satir in p.stdout:
        try: o = json.loads(satir)
        except ValueError: continue
        if "hazir" in o:
            if o.get("hazir"): PIPER.update(durum="hazir", hata=None, sr=int(o.get("sr") or 22050)); print(f"PIPER: hazır ({o.get('sn')} sn)")
            else: PIPER.update(durum="hata", hata=str(o.get("hata") or "?")[:200]); print(f"PIPER: yüklenemedi — {PIPER['hata']}")
            continue
        kim = o.get("id")
        if kim in PIPER["iptal"]:  # okuma kesildi: kalan cümlelerin dosyaları çalınmadan silinir
            if o.get("wav"):
                try: os.remove(o["wav"])
                except OSError: pass
            if o.get("bitti") or o.get("hata"): PIPER["iptal"].discard(kim)
            continue
        q = PIPER["bekleyen"].get(kim)
        if q: q.put(o)
    if PIPER["p"] is p: PIPER.update(p=None, durum="hata" if PIPER["durum"] != "kapali" else "kapali")
    for q in list(PIPER["bekleyen"].values()): q.put({"hata": "işçi kapandı"})
def piper_baslat():
    with PIPER["kilit"]:
        p = PIPER["p"]
        if p and p.poll() is None: return True
        if not piper_acik(): return False
        py, model = str(AYAR["piper_python"]), str(AYAR["piper_model"])
        eksik = next((y for y in (py, model, PIPER_ISCI) if not os.path.exists(y)), None)
        if eksik:
            if PIPER["hata"] != "yok": print(f"PIPER: dosya yok ({os.path.basename(eksik)}) — Mac sesi")
            PIPER.update(durum="yok", hata="yok"); return False
        if time.time() - PIPER["baslat_t"] < 30 and PIPER["durum"] == "hata": return False  # art arda çöken işçiyi zorlamaz
        PIPER["baslat_t"] = time.time(); PIPER["durum"] = "yukleniyor"
        try:
            p = subprocess.Popen([py, "-I", "-B", PIPER_ISCI, model, PIPER_GECICI], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, encoding="utf-8", env=dict(os.environ, HF_HUB_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
        except OSError as e:
            PIPER.update(durum="hata", hata=e.__class__.__name__); print(f"PIPER: başlatılamadı ({e.__class__.__name__}) — Mac sesi"); return False
        PIPER["p"] = p; threading.Thread(target=_piper_okuyucu, args=(p,), daemon=True).start()
    son = time.time() + 20
    while PIPER["durum"] == "yukleniyor" and time.time() < son: time.sleep(0.05)
    return PIPER["durum"] == "hazir"
# Okunur metin (v0.32.2): Piper (espeak tr) sayıların çoğunu doğru okur ("%12", "1.250", "3,5") ama sayıya bitişik eki ayrı sözcük okur
# ("12'si" → "on iki si", "3'üncü" → "üç ündcü"), "09.00"ı "sıfır dokuz nokta sıfır sıfır", "-5"i "beş", "3." sırasını "üç", "Dr."yi "dere"
# okur (13 Ekim fonem dökümü). Bu durumlar okumadan önce yazıya çevrilir; ek sözcüğe bitişir. Mac sesi sayıları kendisi okur, yalnız Piper'da.
_TR_BIR = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_TR_ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def tr_sayi(n):
    n = int(n)
    if n == 0: return "sıfır"
    out = []
    for deger, ad in ((10 ** 12, "trilyon"), (10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")):
        if n >= deger:
            k, n = divmod(n, deger); out += ([] if k == 1 and ad == "bin" else [tr_sayi(k)]) + [ad]
    if n >= 100: k, n = divmod(n, 100); out += ([] if k == 1 else [_TR_BIR[k]]) + ["yüz"]
    if n >= 10: out.append(_TR_ON[n // 10]); n %= 10
    if n: out.append(_TR_BIR[n])
    return " ".join(out)
def tr_sira(n):
    s = tr_sayi(n); son = s.split()[-1]
    if son == "dört": return s[:-4] + "dördüncü"
    ek = {"a": "ıncı", "ı": "ıncı", "e": "inci", "i": "inci", "o": "uncu", "u": "uncu", "ö": "üncü", "ü": "üncü"}[[c for c in son if c in "aıeioöuü"][-1]]
    return s + (ek[1:] if son[-1] in "aıeioöuü" else ek)
_TR_K = "a-zçğıöşü"; _TR_B = "A-ZÇĞİÖŞÜ"
def _sayi_yazi(tam, ondalik=None):
    return tr_sayi(tam.replace(".", "")) + (" virgül " + tr_sayi(ondalik) if ondalik else "")
_OKUNUR = [
    # saat: 09.00 / 15:30 (iki haneli dakika; binlik ayracı üç hanelidir) — "15:30'da" → "on beş otuzda"
    (re.compile(r"(?<![\d.,])([01]?\d|2[0-3])[:.]([0-5]\d)(?![\d])(?:'([" + _TR_K + r"]+))?"),
     lambda m: tr_sayi(m.group(1)) + ("" if m.group(2) == "00" else " " + tr_sayi(m.group(2))) + (m.group(3) or "")),
    # yüzde: %80'i → yüzde sekseni
    (re.compile(r"%\s?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?:'([" + _TR_K + r"]+))?"),
     lambda m: "yüzde " + _sayi_yazi(m.group(1), m.group(2)) + (m.group(3) or "")),
    # para işareti önde: $150 → 150 dolar
    (re.compile(r"([$€£])\s?(\d[\d.,]*\d|\d)"), lambda m: m.group(2) + " " + {"$": "dolar", "€": "avro", "£": "sterlin"}[m.group(1)]),
    (re.compile(r"(\d)\s?₺"), lambda m: m.group(1) + " lira"),
    # sıra sayısı: "3. çeyrek" → "üçüncü çeyrek" (ardından küçük harfle başlayan sözcük gelirse; cümle sonu değil)
    (re.compile(r"(?<![\d.,])(\d{1,4})\.(?=\s+[" + _TR_K + r"])"), lambda m: tr_sira(m.group(1))),
    # eksi: "-5 derece" → "eksi 5 derece" (aralık "10-15" dokunulmaz)
    (re.compile(r"(^|[\s(])-(?=\d)"), lambda m: m.group(1) + "eksi "),
    # sayıya bitişik ek: 2026'da → iki bin yirmi altıda, 3,5'i → üç virgül beşi
    (re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?'([" + _TR_K + r"]+)"),
     lambda m: _sayi_yazi(m.group(1), m.group(2)) + m.group(3)),
    # sayıdan sonra birim kısaltması
    (re.compile(r"(\d)\s?(dk|dak)\.?(?![\w])"), lambda m: m.group(1) + " dakika"),
    (re.compile(r"(\d)\s?sn\.?(?![\w])"), lambda m: m.group(1) + " saniye"),
    (re.compile(r"(\d)\s?km(?![\w])"), lambda m: m.group(1) + " kilometre"),
    (re.compile(r"(\d)\s?kg(?![\w])"), lambda m: m.group(1) + " kilogram"),
    (re.compile(r"(?<![\w])[Nn]o\s?[:.]?\s?(?=\d)"), lambda m: "numara "),
    # unvan (ardından büyük harfli ad)
    (re.compile(r"(?<![\w])(Dr|Prof|Doç|Av|Sn|Op|Uzm)\.(?=\s*[" + _TR_B + r"])"),
     lambda m: {"Dr": "Doktor", "Prof": "Profesör", "Doç": "Doçent", "Av": "Avukat", "Sn": "Sayın", "Op": "Operatör", "Uzm": "Uzman"}[m.group(1)]),
    # kısaltma; ardından cümle bitiyorsa nokta kalır
    (re.compile(r"(?<![\w])(vb|vs|örn|bkz)\.(\s+(?=[" + _TR_B + r"])|\s*$)?"),
     lambda m: {"vb": "ve benzeri", "vs": "vesaire", "örn": "örneğin", "bkz": "bakınız"}[m.group(1)] + ("." + m.group(2) if m.group(2) is not None else "")),
]
def piper_okunur(metin):
    for rx, f in _OKUNUR: metin = rx.sub(f, metin)
    return metin
def piper_oku(metin, hiz=1.0, iptal=None, kayit=None):
    # metni Piper'la okur; bitince True. Hiçbir parça çalınamadıysa False (çağıran Mac sesine düşer). iptal(): True dönerse kalan cümleler
    # çalınmaz; kayit["p"]: çalan süreç (kesintisiz çalıcı ya da afplay; ses_durdur keser).
    if not metin or not piper_acik() or not piper_baslat(): return False
    metin = piper_okunur(metin)
    PIPER["n"] += 1; kim = f"s{PIPER['n']}"; q = queue.Queue(); PIPER["bekleyen"][kim] = q; calinan = 0; oyn = None; sure = 0.0; t0 = time.time()
    def kapat(bekle):
        if not oyn: return
        try: oyn.stdin.close()
        except (OSError, ValueError): pass
        if bekle:
            try: oyn.wait(timeout=max(1.0, sure - (time.time() - t0)) + 5)
            except subprocess.TimeoutExpired: pass
        if oyn.poll() is None: oyn.terminate()
    try:
        if os.access(PIPER_OYNAT, os.X_OK) and not os.environ.get("SUFLOR_TEST_PIPER_SESSIZ"):
            try:
                oyn = subprocess.Popen([PIPER_OYNAT, str(PIPER.get("sr") or 22050)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if kayit is not None: kayit["p"] = oyn
            except OSError: oyn = None
        try: PIPER["p"].stdin.write(json.dumps(dict({"id": kim, "metin": metin, "hiz": hiz, "ara": piper_ara(), "yan": bool(oyn)}, **piper_ton(), **({"uzun": u} if (u := piper_uzun(metin)) else {})), ensure_ascii=False) + "\n"); PIPER["p"].stdin.flush()
        except (OSError, AttributeError, ValueError): kapat(False); return False
        while True:
            try: o = q.get(timeout=15)
            except queue.Empty: print("PIPER: cevap gelmedi (15 sn)"); kapat(calinan > 0); return calinan > 0
            if o.get("hata"): print(f"PIPER: hata — {str(o['hata'])[:120]}"); kapat(calinan > 0); return calinan > 0
            if o.get("bitti"): kapat(True); return calinan > 0 or o.get("n") == 0
            if iptal and iptal():
                PIPER["iptal"].add(kim); kapat(False)
                try: os.remove(o["wav"])
                except OSError: pass
                return True
            try:
                if os.environ.get("SUFLOR_TEST_PIPER_SESSIZ"): calinan += 1
                elif oyn:
                    with wave.open(o["wav"]) as w: b = w.readframes(w.getnframes())
                    try: oyn.stdin.write(b); oyn.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError): PIPER["iptal"].add(kim); return True  # çalıcı kesildi (ses_durdur)
                    calinan += 1; sure += len(b) / 2 / (PIPER.get("sr") or 22050)
                else:
                    pr = subprocess.Popen(["/usr/bin/afplay", o["wav"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if kayit is not None: kayit["p"] = pr
                    pr.wait(); calinan += 1
            except (OSError, wave.Error): kapat(False); return calinan > 0
            finally:
                try: os.remove(o["wav"])
                except OSError: pass
    finally: PIPER["bekleyen"].pop(kim, None)
if piper_acik() and not deneme_aktarici(): threading.Thread(target=piper_baslat, daemon=True).start()  # ilk okuma beklemesin
