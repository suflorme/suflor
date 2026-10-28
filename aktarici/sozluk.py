# Suflor.me aktarıcı bölümü: Özel sözlük. Ayrı modül değildir — relay.py bunu kendi ad alanında, eski yerinde çalıştırır (bolum("sozluk")):
# STATE, LOCK, AYAR, write, _t … relay.py'nin; buradaki tanımlar da relay.py'ye aittir. import etme. Python 3.9 uyumlu.
# --- Özel sözlük ------------------------------------------------------------------------------------------------
# sozluk.json: {"terimler": [{"dogru": "GitHub", "yanlis": ["git hub"], "kip": "duzelt"|"baglam"|"isaret", "baglam": [...]}]}
# isaret: kör analizde "baglama_bakarak" işaretli kalemler — hiç düzeltilmez, yalnız "? x=Y" işareti.
# Döküm sistem/uygulama adlarını yanlış yazıyor (benzer sesli iki ad sürekli karışabilir). duzelt: her geçiş düzeltilir.
# baglam: yanlış biçim gerçek bir kelime/ad da olabilir ("eşli", "Kaan ve", "render") — yalnız AYNI satırda bağlam
# kelimelerinden biri varsa düzeltilir, yoksa satıra "? yanlış=Doğru" işareti konur (önceki satırlara bakınca konu
# değişmişken de düzeltiyordu: gündelik bir cümle ürün adına dönüyordu; yanlış düzeltme kaçırılandan kötü). Ham metin
# .jsonl'de "raw" alanında kalır. Türkçe karşılaştırma harf harf (İ/ı/ş/ğ… sadeleştirilir), ek konuşmacının
# söylediği gibi korunur ("git hub'da" → "GitHub'da"; ek olduğu gibi kalır — ünlü uyumu kurulmaz). Dosya değişince kendiliğinden yeniden yüklenir.
SOZ = {"mtime": None, "kurallar": []}
def _nc(c):
    if c in "İIı": return "i"
    import unicodedata; d = unicodedata.normalize("NFKD", c)
    return (d[0] if d else c).lower()[:1] or " "
def sade(t): return "".join(_nc(c) for c in t)
def sozluk_yukle():
    fp = os.path.join(BASE, "sozluk.json")
    try: m = os.path.getmtime(fp)
    except OSError: SOZ.update(mtime=None, kurallar=[]); return
    if m == SOZ["mtime"]: return
    try: terimler = json.load(open(fp, encoding="utf-8")).get("terimler", [])
    except Exception as e: print(f"SÖZLÜK: okunamadı ({e}) — önceki hâl kullanılıyor"); SOZ["mtime"] = m; return
    kur = []
    for t in terimler:
        dogru = str(t.get("dogru") or "").strip()
        if not dogru: continue
        bag = [sade(b) for b in t.get("baglam") or [] if str(b).strip()]
        for y in t.get("yanlis") or []:
            ys = sade(str(y)).strip()
            if len(ys) < 3 or ys == sade(dogru): continue
            govde = r"[\s\-]+".join(re.escape(w) for w in ys.split())
            # kısa biçimde ek kabul edilmez (yanlış eşleşme). v0.7.3: son kelimesi < 3 harf olan çok kelimeli biçimde de
            # (iki kısa sözcüklü biçim bir sonraki sözcüğün başını ek sanıp yanlış düzeltiyordu: 20 dökümde 14 kez)
            ek = r"(?P<ek>'?[a-z]{1,6})?" if len(ys) >= 5 and len(ys.split()[-1]) >= 3 else ""
            kur.append((re.compile(r"(?<![0-9a-z])" + govde + ek + r"(?![0-9a-z])"), dogru, ys, t.get("kip", "duzelt"), bag))
    kur.sort(key=lambda k: -len(k[2]))  # uzun biçim önce ("shoppy fay" "fay"dan önce)
    SOZ.update(mtime=m, kurallar=kur); print(f"SÖZLÜK: {len(terimler)} terim, {len(kur)} biçim yüklendi")
def sozluk_uygula(text, dosya):
    # dönen: (düzeltilmiş metin, [{"bicim", "dogru", "durum": "duzeltildi"|"supheli"}])
    sozluk_yukle()
    if not SOZ["kurallar"]: return text, []
    pencere = sade(text); out, olay = text, []
    for rx, dogru, ys, kip, bag in SOZ["kurallar"]:
        n = sade(out); parcalar, son = [], 0
        for m in rx.finditer(n):
            if n[m.start():m.end()].replace("'", "").startswith(sade(dogru).replace(" ", "")): continue  # "discont"+"inued" zaten doğru
            if kip == "isaret" or (kip == "baglam" and not any(b in pencere for b in bag)):  # isaret: hiç düzeltme, yalnız "?"
                olay.append({"bicim": out[m.start():m.end()], "dogru": dogru, "durum": "supheli"}); continue
            harf = len((m.groupdict().get("ek") or "").lstrip("'"))  # ek harfleri özgün metinden, kesme işaretiyle
            parcalar.append(out[son:m.start()] + dogru + ("'" + out[m.end() - harf:m.end()] if harf else ""))
            olay.append({"bicim": out[m.start():m.end()], "dogru": dogru, "durum": "duzeltildi"}); son = m.end()
        if parcalar: out = "".join(parcalar) + out[son:]
    return out, olay

# Sesli "Claude:" talimatı (TOPLANTI-MODU §4) Whisper'da "Cloud," / "Klod:" diye yazılıyor (9 Ekim denemesi: "Cloud, card, English,
# yes."). Yalnız kullanıcının kendi satırında ve cümle başında düzeltilir: "cloud'a bağımlıyız" gibi gerçek bulut anlamı ve karşı
# tarafın sözü değişmez. Ham metin .jsonl'de "raw"da kalır. 11 Ekim: "...Cloud kaydı kapat." (üç noktadan sonra boşluksuz, virgülsüz) kaçtı →
# üç nokta da cümle başı; virgül yoksa ardından bulut anlamlı sözcük gelmemeli ("Cloud hizmeti pahalı" değişmez).
BULUT = r"hizmet|tabanl|sunucu|depola|bili[sş]im|ortam|altyap|platform|teknoloj|uygulama|sağlay|sistem|taraf|üzerin|maliyet|computing|service|storage|server|based|native|code\b"
# 12 Ekim (deneme 7): "Klot. Kaç kart açık?" — Whisper hitaptan sonra nokta koyup cümleyi bölüyor → noktadan sonra büyük harfle süren cümle de
# hitap. "Suflor" da uyandırma sözü (kullanıcı isteği): aynı kural, "Claude:" olur (toplantı oturumu tek biçim arar). Cümle ortasında yalnız doğru yazılmış
# "Claude"/"Suflor" ve satır soruyla bitiyorsa: "… yapayım Claude kaç kart açık?" ("Claude mu yazdı?" gibi ek/edat sonrası değişmez).
# S133 (22 Ekim): tek muhatap asistan — kişiliksiz kurulumda seslenme yalnız "Suflor"; "Claude" (ve Whisper'ın "Cloud/Klod" yazımları) artık komut değil.
HITAP_AD = r"(?:suflor|suflör|süflör)"
HITAP_RX = re.compile(r"(^|[.!?…]\s+|(?:\.{3}|…)\s*)" + HITAP_AD + r"(?:\s*[,:]\s*|\.\s+(?=[A-ZÇĞİÖŞÜ])(?!(?:" + BULUT + r"))|\s+(?!(?:" + BULUT + r"))(?=\w))", re.I)
HITAP_ORTA_RX = re.compile(r"(?<=\w)([,]?\s+)(?:Suflor)(?:\s*[,:]\s*|\s+(?!(?:mi|mı|mu|mü|ile|ve|için|gibi|de|da|ya|ki)\b)(?=\w))(?=[^.!?…]*\?\s*$)")
# Kişilik hitabı (v0.53.0, ölçüm 16 Ekim: kişilik adıyla başlayan 14 cümlenin 13'ü istemle doğru yazıldı): adlar kişilik dosyasından/ayardan (kodda sabit ad yok).
# Cümle başında ad + virgül/iki nokta/nokta ya da cümle soru ise hitap: "<Ad> markasının yeni ürünü…" tetiklemez. İçeride yine "Claude:" olur.
# S94 (19 Ekim test toplantısı: "<Ad> gelsin" virgülsüz ve sorusuz kaçtı): noktalamasız/sorusuz cümlede istek varsa da hitap (KISILIK_ISTEK, kisilik.py).
# Kişilik varken "Claude"/"Suflor" artık seslenme değil (toplantıda tek kural: asistanın adı); kişiliksiz (nötr) kurulumda eskisi gibi.
_KHR = {"k": {}, "rx": {}, "son": None, "satir": None}  # v0.61.0: iki kişilik — kalıp tüm adlarla; "son" = (az önce tanınan kişiliğin adı, zaman), konus_hitap okur; "satir" = son hitap_duzelt satırındaki ad
def _kisilik_hitap_rx(rol=None):  # rol "toplanti": yalnız toplantı kişiliğinin adları (karşı taraf için)
    ks = [k for k in kisilikler() if not rol or k["rol"] == rol]; adlar = tuple(a for k in ks for a in k["hitap"])
    if _KHR["k"].get(rol) != adlar:
        _KHR["k"][rol] = adlar
        _KHR["rx"][rol] = re.compile(r"((?:^|[.!?…]\s+|(?:\.{3}|…)\s*)(?:" + KISILIK_GIRIS + r"[,.!]?\s+)?)(" + "|".join(re.escape(a) for a in sorted(adlar, key=len, reverse=True)) + r")(?:\s*[,:]\s*|\.\s+(?=[A-ZÇĞİÖŞÜ])|\s+(?!" + KISILIK_SOZ_ETME + r")(?=[^.!?…]*(?:\?|" + KISILIK_ISTEK + r"))"
                                     # v0.113.1 (22 Ekim test toplantısı: "Tamam... Orney... eee... Bugün projede... açık kalan iş kaldı mı?" ~1 dk cevapsız): addan sonra
                                     # duraksama (üç nokta) ve satırın kalanında soru ya da istek varsa da seslenme
                                     r"|(?:\.{2,}(?!\.)|…)(?!\s*" + KISILIK_SOZ_ETME + r")\s*(?=[^\n]*(?:\?|" + KISILIK_ISTEK + r")))", re.I) if adlar else None
    return _KHR["rx"][rol]
def _kisilik_hitap_ad(soz):  # tanınan hitap sözü → kişiliğin adı
    for k in kisilikler():
        if any(a.lower() == soz.lower() for a in k["hitap"]): return k["ad"]
    return None
# Bölünen hitap (19 Ekim test toplantısı): Whisper "<kişilik adı> şu an" ve "toplantıda kaç tane şey var? … kontrol eder misin?" diye iki satıra böldü; ilk satırda soru
# işareti olmadığı için hitap sayılmadı, Konuş cevap vermedi. Kullanıcı satırı ad (ya da Claude/Suflor) ile başlayıp noktalamasız biterse (en çok 6 sözcük) askıda
# tutulur; HITAP_ASKI_SN içinde başlayan sonraki kullanıcı satırıyla birleşik metinde hitap aranır (döküm satırları ayrı kalır).
HITAP_ASKI = {"metin": None, "t1": 0.0, "satir": None, "pen": 2.0, "bas": 0.0, "cevap": False}; HITAP_ASKI_SN = 2.0
# v0.140.0 (27 Ekim, ikinci hesap: "yarın / on ikide / Sera, / [kişi] ile / bir toplantı planına / takvime ekle." — ad tek başına bir parça, talimat
# hitapsız kalıp kayboldu): yalnız addan oluşan satır askıya alınır; hemen önündeki noktalamasız kullanıcı satırları (en çok HITAP_ONCE_N, aralar
# ≤ HITAP_DEVAM_SN) adın arkasına eklenir; sonraki satırlar HITAP_DEVAM_SN içinde geldikçe cümle (. ? ! …) bitene dek birikir. Asistanın sorusuna
# hitapsız cevap (hitap_cevap_baslat) yalnız süreyle biter (cevap birkaç cümle olabilir). En çok HITAP_EN_COK_SN / HITAP_EN_COK_SOZ.
HITAP_DEVAM_SN = 3.0; HITAP_ONCE_N = 3; HITAP_EN_COK_SN = 20.0; HITAP_EN_COK_SOZ = 45
HITAP_ONCE = []  # son kullanıcı satırları [(metin, t0, t1)]
def _hitap_adlari(): return [x for k in kisilikler() for x in k["hitap"]]
def _hitap_alt():
    adlar = _hitap_adlari()
    return "(?:" + "|".join([re.escape(x) for x in sorted(adlar, key=len, reverse=True)] + ([] if adlar else [HITAP_AD])) + ")"
def _hitap_rx(): return r"\W*" + _hitap_alt() + r"\b"
def hitap_yalniz_ad(metin):  # satır yalnız asistanın adı mı ("Sera," / "Sera") → adın yazıldığı biçim, değilse None
    m = re.fullmatch(r"\W*(" + _hitap_alt() + r")[\s.,:;!?…]*", metin or "", re.I)
    return m.group(1) if m else None
def hitap_aski(metin, t0=None, t1=None):  # → askıdaki hitap + bu satır (birleşik, tamamlandı) ya da None; bu satır askıya alınır ya da askıdakine eklenirse None
    a = HITAP_ASKI; t0 = time.time() if t0 is None else t0; t1 = time.time() if t1 is None else t1
    once = [x for x in HITAP_ONCE]; HITAP_ONCE.append((metin, t0, t1)); del HITAP_ONCE[:-HITAP_ONCE_N - 1]
    a.update(satir=None)
    if a["metin"] and 0 <= t0 - a["t1"] <= a["pen"]:
        m = a["metin"] + " " + metin
        if not a["cevap"] and (re.search(r"[.!?…]\s*$", metin) or len(m.split()) >= HITAP_EN_COK_SOZ or t1 - a["bas"] >= HITAP_EN_COK_SN or a["pen"] == HITAP_ASKI_SN):
            a.update(metin=None); return m
        if a["cevap"] and (len(m.split()) >= HITAP_EN_COK_SOZ or t1 - a["bas"] >= HITAP_EN_COK_SN): a.update(metin=None); return m
        a.update(metin=m, t1=t1, satir=metin, pen=HITAP_DEVAM_SN); return None
    a.update(metin=None)
    ad = hitap_yalniz_ad(metin)
    if ad:  # yalnız ad: önündeki noktalamasız satırlar (aynı cümlenin başı) arkasına
        on, son_t0 = [], t0
        for x, x0, x1 in reversed(once):
            if not (0 <= son_t0 - x1 <= HITAP_DEVAM_SN) or re.search(r"[.!?…]\s*$", x) or len(on) >= HITAP_ONCE_N: break
            on.insert(0, x); son_t0 = x0
        a.update(metin=" ".join([ad + ","] + on), t1=t1, satir=metin, pen=HITAP_DEVAM_SN, bas=son_t0, cevap=False); return None
    if re.match(_hitap_rx(), metin or "", re.I) and not re.search(r"[.!?…:,]\s*$", metin) and len(metin.split()) <= 6:
        a.update(metin=metin, t1=t1, satir=metin, pen=HITAP_ASKI_SN, bas=t0, cevap=False)
    return None
def hitap_cevap_baslat(ad, metin, t0=None, t1=None):  # asistanın sorusuna hitapsız cevap → "<ad>, <cevap>" askıya (süre dolunca gider); askıdaki metni döndürür
    t0 = time.time() if t0 is None else t0; t1 = time.time() if t1 is None else t1
    HITAP_ASKI.update(metin=f"{ad}, {metin}", t1=t1, satir=metin, pen=HITAP_DEVAM_SN, bas=t0, cevap=True); return HITAP_ASKI["metin"]
def hitap_askida(metin): return bool(metin) and HITAP_ASKI["satir"] == metin and bool(HITAP_ASKI["metin"])  # bu satır askıya alındı ya da askıdakine eklendi
def hitap_aski_metin(): return HITAP_ASKI["metin"]
def hitap_aski_bitti(metin):  # S94: askıdaki metne HITAP_DEVAM_SN içinde devam gelmedi → tek başına hitap ("<Ad> gelsin" kaybolmasın) — metni döndürür, yoksa None
    if not metin or HITAP_ASKI["metin"] != metin: return None
    HITAP_ASKI.update(metin=None, satir=None); return metin
# S133 (kullanıcı, 22 Ekim): dışarı aktarılan dökümde kullanıcının satırı "<kullanıcı>: Claude: …" görünüyordu. İçeride (jsonl, izle, Konuş) hitap biçimi
# "Claude:" kalır; kullanıcıya görünen dökümde (.md, panodaki canlı döküm, Dökümler penceresi) seslenilen asistanın adı yazılır ("<ad>, …").
_ASG_RX = re.compile(r"(^|[.!?…]\s+|(?:\.{3}|…)\s*)Claude:\s*")
def asistan_goster(metin, ad=None):  # ad: satırda seslenilen asistan (jsonl "hitap"); yoksa toplantı asistanı
    if not metin or "Claude:" not in metin: return metin
    ad = ad or (asistan_ad() if "asistan_ad" in globals() else None) or "Suflor"
    return _ASG_RX.sub(lambda m: m.group(1) + ad + ", ", metin).replace("Cloud=Claude:", "→ " + ad)
def hitap_duzelt(text):
    krx = _kisilik_hitap_rx(); _KHR["satir"] = None
    def kd(m):
        ad = _kisilik_hitap_ad(m.group(2))
        if ad: _KHR["son"] = (ad, time.time()); _KHR["satir"] = ad
        return m.group(1) + "Claude: "
    out = krx.sub(kd, text) if krx else text
    if not kisilikler():  # S94: kişilik varken Claude/Suflor seslenme değil
        out = HITAP_RX.sub(lambda m: m.group(1) + "Claude: ", out)
        if out == text: out = HITAP_ORTA_RX.sub(lambda m: ". Claude: ", text, count=1)
    return out, ([{"bicim": "Cloud", "dogru": "Claude:", "durum": "duzeltildi"}] if out != text else [])

def slug(s): s = re.sub(r"[^\w\s-]", "", s, flags=re.U).strip(); s = re.sub(r"\s+", "-", s); return s[:60] or "toplanti"
# Faz B (v0.149.0): dosyanın adı ve açılışı aktarici/toplanti.py'de (_kayit_ac, bir kez); eski paths/yer tutucu birleştirme (dosyayı yeniden adlandırıyordu) kalktı.
def restore_state():
    # Aktarıcı yeniden başlatıldığında sayaçlar (satır, işaret, kanıt, gündem, görülen satırlar) dosyadan kurulur. Faz B: süren toplantı canli/toplanti.json'dan
    # (toplanti_kur: ≤ 5 dk önce yazılmışsa bitiyor olarak sürer, sinyal gelirse aynı dosya); yoksa bugünün son dökümü yalnız gösterim için (yeni yazım ayrı dosyaya).
    try:
        suren = toplanti_kur()
        if suren: STATE["file"] = suren; STATE["meeting"] = TOPLANTI["aktif"]["ad"]  # .jsonl henüz yoksa da (yalnız başlık yazıldı) süren toplantı bilinsin
        today = datetime.date.today().strftime("%Y-%m-%d")
        # yalnız toplantı dökümü (tek noktalı ad): yan dosyalar (.ceviri.jsonl …) seçilmesin (12 Ekim deneme 6: üç dosya)
        cands = [os.path.join(BASE, suren[:-3] + ".jsonl")] if suren else \
                sorted((f for f in glob.glob(os.path.join(BASE, f"{today}-*.jsonl")) if os.path.basename(f).count(".") == 1), key=os.path.getmtime)
        if not cands or not os.path.exists(cands[-1]): return
        jl = cands[-1]; base = jl[:-6]; md = base + ".md"
        age_min = (datetime.datetime.now().timestamp() - os.path.getmtime(jl)) / 60
        lines = 0; flags = []; notes = 0; key = os.path.basename(md); first_at = None
        for raw in open(jl, encoding="utf-8"):
            raw = raw.strip()
            if not raw: continue
            try: rec = json.loads(raw)
            except Exception: continue
            if "note" in rec: notes += 1; continue
            if "kanit" in rec: STATE["kanitlar"].setdefault(key, []).append(rec); continue
            lines += 1; first_at = first_at or rec.get("at")
            pay_kayit(key, rec, _epoch(rec.get("at")))
            if rec.get("flags"): flags.append(rec)
            if rec.get("id"): SEEN.setdefault(os.path.basename(md), {})[rec["id"]] = rec.get("text")
        title = None
        try:
            head = open(md, encoding="utf-8").readline()
            m = re.match(r"# Canlı transkript — (.+)$", head.strip())
            if m: title = m.group(1)
        except Exception: pass
        STATE["file_last"][key] = os.path.getmtime(jl)
        if first_at: STATE["file_start"][key] = datetime.datetime.fromtimestamp(_epoch(first_at)).isoformat(timespec="seconds")
        if suren:
            STATE["meeting"] = title = (TOPLANTI["aktif"] or {}).get("ad") or title
            # gündem işaretleri .md'deki GÜNDEM satırlarından geri kurulur (kalan süre/kayma hesabı bunlara dayanır)
            items = agenda().get("items", [])
            try:
                for l in open(md, encoding="utf-8"):
                    g = re.match(r"\| [\d:]+ \| \*\*GÜNDEM\*\* \| ([✓✗]) (.*?)(?: \(Claude\))? \| \|$", l.rstrip("\n"))
                    if g and g.group(2) in items: STATE["agenda_ticks"][str(items.index(g.group(2)))] = g.group(1) == "✓"
            except OSError: pass
        STATE["file"] = os.path.basename(md); STATE["file_lines"][os.path.basename(md)] = lines
        STATE["lines"] = lines; STATE["flags"] = flags[-50:]; STATE["notes"] = notes  # pano "not 0" demesin
        STATE["last"] = datetime.datetime.fromtimestamp(os.path.getmtime(jl)).isoformat(timespec="seconds")
        resumed = "süren toplantı (sinyal bekleniyor)" if suren else f"salt-okunur gösterim (dosya {age_min:.0f} dk önceki, yeni yazım ayrı dosyaya gidecek)"
        print(f"Durum kuruldu: {STATE['file']} · {lines} satır · {resumed}")
    except Exception as e:
        print(f"Durum kurulamadı (yeni oturum gibi devam): {e}")
def heartbeat():
    # geçici dosya + os.replace: disk doluyken yarım/boş heartbeat.json bırakmasın; yazılamazsa geçilir (türetilmiş veri)
    disk_check()
    if BACKLOG: flush_backlog()
    fp = os.path.join(BASE, "heartbeat.json"); tmp = fp + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f: json.dump(STATE, f, ensure_ascii=False, indent=1)
        os.replace(tmp, fp)
    except OSError:
        try: os.remove(tmp)
        except OSError: pass
def _heartbeat_dongu():  # S162: heartbeat.json yalnız eklenti nabzında yazılıyordu → eklenti yokken (masaüstü, tanınmayan sayfa) donup kalıyordu; zamanlayıcı da yazar
    while True:
        time.sleep(2 if os.environ.get("SUFLOR_TEST_HIZLI") else 8)
        try:
            with LOCK: heartbeat()
        except Exception as e: print(f"HEARTBEAT: yazılamadı ({e.__class__.__name__})")
# platform katmanı: /ses'i kabul eden toplantı siteleri (içerik betiği kökeni) ve görünen adları. Meet/Zoom eklentide
# henüz yüklenmiyor (v0.9.1/v0.9.2); kökenleri burada şimdiden durur ki eklenti tarafı eklenince aktarıcı kurulumu gerekmesin.
PLATFORM_KOKEN = [r"https://teams\.(microsoft\.com|cloud\.microsoft|live\.com)$", r"https://meet\.google\.com$", r"https://([a-z0-9-]+\.)?zoom\.us$"]
PLATFORM_AD = {"teams": "Teams", "meet": "Google Meet", "zoom": "Zoom", "bilinmeyen": "Toplantı"}  # S162: platform bilinmiyorsa varsayılan Teams değil
def ensure_header(md, title, m, source=None):
    # başlık metnini döndürür (dosya yoksa ve daha önce sıraya konmadıysa); yazım write() ile, satırlarla aynı grupta
    if md in HEADERED or os.path.exists(md): HEADERED.add(md); return ""
    HEADERED.add(md)
    # altyazı modunda başlık bunu söyler (konuşmacı adı olmayabilir, dil yanlış seçilmiş olabilir)
    # platform adı eklentiden (meeting.platform; Whisper satırlarında son ping'in platformu)
    # S161: tanınan toplantının platformu (masaüstü/Whisper satırında meeting.platform yok; 27 Ekim Meet toplantısının başlığı "Teams" dedi)
    pl = PLATFORM_AD.get((m or {}).get("platform") or "bilinmeyen", "Toplantı")  # Faz B: platform toplantı kaydından (toplanti.py), eklentinin son nabzından değil
    src = f"Whisper (yerel konuşma tanıma, large-v3-turbo; konuşmacı: kullanıcı mikrofonu / karşı taraf {pl} sesi)" if source == "whisper" else \
          f"{pl} canlı altyazı (döküm yetkisi yok; konuşmacı adı eksik, dil yanlış seçilmişse metin anlamsız olabilir)" if source == "captions" else \
          f"{pl if pl == 'Toplantı' else pl + ' toplantısı'} (Suflor.me kendiliğinden tanıdı; satırlar Whisper ya da canlı altyazıdan)" if source == "oto" else f"{pl} transkript paneli (otomatik döküm; isim ve sistem adları hatalı olabilir)"
    # 19 Ekim test toplantısı: masaüstü Teams'te eklenti yok → "Başlangıç: ?"; başlangıç bilinmiyorsa dosyanın ilk kaydının saati (canlı dosya geliş sırasıyla yazılır:
    # Whisper satırı ~5 sn geç gelir, Suflor'un sesli satırı okunduğu an — toplantı sonundaki döküm (toplanti-claude.py dokum) zamana göre sıralar)
    bas = (m or {}).get("startedAt") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + " (ilk kayıt; satırlar geliş sırasıyla)"
    return (f"# Canlı transkript — {title}\n\n**Başlangıç: {bas} · Kaynak: {src} · Aktarıcı: Suflor.me**\n**Gizlilik: iç belge, kişi adı içerir.**\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n")
