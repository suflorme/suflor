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
# yes."). Yalnız kullanıcının kendi satırında, cümle başında ve ardından virgül/iki nokta gelirse düzeltilir: "cloud'a bağımlıyız"
# gibi gerçek bulut anlamı ve karşı tarafın sözü değişmez. Ham metin .jsonl'de "raw"da kalır.
HITAP_RX = re.compile(r"(^|[.!?…]\s+)(?:cloud|klod|klot|clod|claud|klaud|clode)\s*[,:]\s*", re.I)
def hitap_duzelt(text):
    out = HITAP_RX.sub(lambda m: m.group(1) + "Claude: ", text)
    return out, ([{"bicim": "Cloud", "dogru": "Claude:", "durum": "duzeltildi"}] if out != text else [])

def slug(s): s = re.sub(r"[^\w\s-]", "", s, flags=re.U).strip(); s = re.sub(r"\s+", "-", s); return s[:60] or "toplanti"
def paths(title):
    # Aynı toplantı için ilk çağrıda saat damgalı dosya adı üretilir, sonraki çağrılar aynı dosyaya yazar
    # (böylece aynı başlıklı iki toplantı aynı gün farklı dosyaya düşer; adlandırma yalnız ingest/note içinde,
    # yani LOCK altında çağrılır).
    # eşlenen dosyaya RESUME_MAX_AGE_MIN'den uzun süredir yazılmadıysa bu yeni bir toplantıdır → yeni dosya
    # (29 Eylül: aynı başlıklı iki toplantı aynı dosyaya düştü; aktarıcı açık kaldıkça eşleme sürüyordu)
    base = STATE["meeting_files"].get(title)
    if base and time.time() - STATE["file_last"].get(os.path.basename(base) + ".md", 0) > RESUME_MAX_AGE_MIN * 60: base = None
    if not base and title != YER_TUTUCU: base = yer_tutucu_birlestir(title)
    if not base:
        d = datetime.date.today().strftime("%Y-%m-%d"); t = datetime.datetime.now().strftime("%H%M")
        base = os.path.join(BASE, f"{d}-{t}-{slug(title)}"); STATE["meeting_files"][title] = base
        STATE["file_start"][os.path.basename(base) + ".md"] = datetime.datetime.now().isoformat(timespec="seconds")
    STATE["file_last"][os.path.basename(base) + ".md"] = time.time()  # yalnız yazarken çağrılır (ingest/note/gündem)
    return base + ".md", base + ".jsonl"
RESUME_MAX_AGE_MIN = 20  # bu süreden eski bir dosya "hâlâ süren toplantı" sayılmaz, yeniden bağlanmaz
YER_TUTUCU = "Toplantı"; BIRLESTIR_DK = 10; YT_AD = {}  # taşınan dosya (.md yolu) → gerçek toplantı adı (adsız satır süren adı bozmasın)
def yer_tutucu_birlestir(title):
    # toplantının ilk satırları (çoğu kez Whisper) eklenti toplantı adını göndermeden gelir ve "Toplantı" dosyasına düşer; ad gelince
    # yeni dosya açılıyordu (7 Ekim: 1 satırlık "…-1803-Toplantı.md" + asıl dosya). Yer tutucu dosya süren dosyaysa ve son
    # BIRLESTIR_DK içinde başladıysa gerçek ada taşınır (saat damgası korunur); sonraki adsız satırlar da oraya gider. LOCK altında.
    eski = STATE["meeting_files"].get(YER_TUTUCU)
    if not eski or not os.path.basename(eski).endswith("-" + slug(YER_TUTUCU)): return None  # zaten taşındıysa (takma ad) yeniden taşınmaz
    emd = os.path.basename(eski) + ".md"
    try: bas = datetime.datetime.fromisoformat(STATE["file_start"].get(emd) or "").timestamp()
    except ValueError: return None
    if STATE["file"] != emd or time.time() - bas > BIRLESTIR_DK * 60 or time.time() - STATE["file_last"].get(emd, 0) > RESUME_MAX_AGE_MIN * 60: return None
    yeni = os.path.join(BASE, os.path.basename(eski)[:16] + slug(title)); ymd = os.path.basename(yeni) + ".md"
    if any(os.path.exists(yeni + u) for u in (".md", ".jsonl", ".altyazi.log", ".sesizi.log")): return None
    try:
        for u in (".md", ".jsonl", ".altyazi.log", ".sesizi.log"):
            if os.path.exists(eski + u): os.rename(eski + u, yeni + u)
        if os.path.exists(yeni + ".md"):
            m = open(yeni + ".md", encoding="utf-8").read()
            m = m.replace(f"# Canlı transkript — {YER_TUTUCU}\n", f"# Canlı transkript — {title}\n", 1)
            open(yeni + ".md.tmp", "w", encoding="utf-8").write(m); os.replace(yeni + ".md.tmp", yeni + ".md")
    except OSError as e: print(f"UYARI: yer tutucu dosya taşınamadı ({e}) — ad gelince yeni dosya açılır"); return None
    for k in ("file_lines", "file_last", "file_start", "kanitlar"):
        if emd in STATE[k]: STATE[k][ymd] = STATE[k].pop(emd)
    if emd in SEEN: SEEN[ymd] = SEEN.pop(emd)
    if emd in PAY: PAY[ymd] = PAY.pop(emd)
    for k in [k for k in _PAY_ONCEKI if k[0] == emd]: _PAY_ONCEKI[(ymd, k[1])] = _PAY_ONCEKI.pop(k)
    HEADERED.add(yeni + ".md"); STATE["file"] = ymd
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for liste, log in ((CARDS, "kartlar.jsonl"), (QUESTIONS, "sorular.jsonl")):
        for r in liste:
            if r.get("file") == emd: r["file"] = ymd; _log(log, {"id": r["id"], "at": now, "file": ymd})
    STATE["meeting_files"][title] = STATE["meeting_files"][YER_TUTUCU] = yeni; YT_AD[yeni + ".md"] = title
    print(f"DOSYA: toplantı adı geldi — {emd} → {ymd} (ilk satırlar aynı dosyada)")
    return yeni
def restore_state():
    # Aktarıcı yeniden başlatıldığında bugünün en son yazılan toplantı dosyasından sayaçları kurar
    # (STATE sıfırlanınca sayaçların toplantı ortasında tutarsızlaşması sorununa karşı). Dosya
    # RESUME_MAX_AGE_MIN'den eskiyse (leftover/önceki oturum) başlığı yeni yazıma bağlamaz — aksi halde
    # aynı adlı yeni bir toplantı, eski (belki dünkü) dosyaya karışır (29 Eylül gerçek testinde yaşandı).
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        cands = sorted(glob.glob(os.path.join(BASE, f"{today}-*.jsonl")), key=os.path.getmtime)
        if not cands: return
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
        if title and age_min <= RESUME_MAX_AGE_MIN:
            STATE["meeting_files"][title] = base; STATE["meeting"] = title
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
        resumed = "devam ediliyor" if (title and age_min <= RESUME_MAX_AGE_MIN) else f"salt-okunur gösterim (dosya {age_min:.0f} dk önceki, yeni yazım ayrı dosyaya gidecek)"
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
# platform katmanı: /ses'i kabul eden toplantı siteleri (içerik betiği kökeni) ve görünen adları. Meet/Zoom eklentide
# henüz yüklenmiyor (v0.9.1/v0.9.2); kökenleri burada şimdiden durur ki eklenti tarafı eklenince aktarıcı kurulumu gerekmesin.
PLATFORM_KOKEN = [r"https://teams\.(microsoft\.com|cloud\.microsoft|live\.com)$", r"https://meet\.google\.com$", r"https://([a-z0-9-]+\.)?zoom\.us$"]
PLATFORM_AD = {"teams": "Teams", "meet": "Google Meet", "zoom": "Zoom"}
def ensure_header(md, title, m, source=None):
    # başlık metnini döndürür (dosya yoksa ve daha önce sıraya konmadıysa); yazım write() ile, satırlarla aynı grupta
    if md in HEADERED or os.path.exists(md): HEADERED.add(md); return ""
    HEADERED.add(md)
    # altyazı modunda başlık bunu söyler (konuşmacı adı olmayabilir, dil yanlış seçilmiş olabilir)
    # platform adı eklentiden (meeting.platform; Whisper satırlarında son ping'in platformu)
    pl = PLATFORM_AD.get((m or {}).get("platform") or (STATE.get("extension") or {}).get("platform") or "teams", "Teams")
    src = f"Whisper (yerel konuşma tanıma, large-v3-turbo; konuşmacı: kullanıcı mikrofonu / karşı taraf {pl} sesi)" if source == "whisper" else \
          f"{pl} canlı altyazı (döküm yetkisi yok; konuşmacı adı eksik, dil yanlış seçilmişse metin anlamsız olabilir)" if source == "captions" else f"{pl} transkript paneli (otomatik döküm; isim ve sistem adları hatalı olabilir)"
    return (f"# Canlı transkript — {title}\n\n**Başlangıç: {m.get('startedAt','?')} · Kaynak: {src} · Aktarıcı: Suflor.me**\n**Gizlilik: iç belge, kişi adı içerir.**\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n")
