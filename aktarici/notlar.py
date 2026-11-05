# Suflor.me aktarıcı bölümü: Notlar defteri — toplantı yokken pano kutusu (v0.117.0, S136).
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("notlar")): BASE, write, aktif_dosya … relay.py'nin. import etme.
# Kullanıcı (22 Ekim): toplantı yokken kutuya yazılan not sahte bir "Toplantı" dökümü açıyor, pano 20 dk toplantı görünümüne geçiyordu
# (Başlat ve takvim gizli); soru izleyen olmadığı için cevapsız kalıyordu. Artık ne süren, ne de hazırlanan
# (son 30 dk'da Başlat/gündem, arka planda toplantı oturumu) toplantı varsa: soru toplantı dışı asistana yazılı gider (konus_yazili: cevap
# panoda, okunmaz), not canli/notlar.jsonl'e. Defter kişisel: panoya yalnız anahtarlı /status ile gider. Silme ayrı satırla ({"sil": id}).
NOTLAR_DOSYA, NOT_HAZIRLIK_SN, NOT_GOSTER_SA, NOT_GOSTER_EN_COK = "notlar.jsonl", 1800, 24, 20

def toplantisiz():  # kutu: süren, yeni biten ya da hazırlanan toplantı yok
    if aktif_dosya() or topo_canli(): return False  # Faz B: süren (algılandı/sürüyor/bitiyor) toplantı
    for y in ("takvim-secilen.json", "agenda.json"):  # Başlat ya da gündem: yeni toplantı hazırlanıyor, not ona (PRE) gider
        try:
            if time.time() - os.path.getmtime(os.path.join(BASE, y)) < NOT_HAZIRLIK_SN: return False
        except OSError: pass
    return True

def not_defter_yaz(metin, at=None):
    o = {"id": "n" + secrets.token_hex(4), "at": str(at or datetime.datetime.now().isoformat(timespec="seconds"))[:40], "metin": str(metin)[:4000]}
    write([(os.path.join(BASE, NOTLAR_DOSYA), json.dumps(o, ensure_ascii=False) + "\n")])
    print(f"NOT: toplantı yok — Notlar defterine ({len(o['metin'])} karakter)"); return {"ok": True, "id": o["id"]}

def _notlar_oku():
    ls, sil = [], set()
    try:
        with open(os.path.join(BASE, NOTLAR_DOSYA), encoding="utf-8") as f:
            for ln in f:
                try: o = json.loads(ln)
                except ValueError: continue
                if not isinstance(o, dict): continue
                if o.get("sil"): sil.add(str(o["sil"]))
                elif o.get("id") and o.get("metin"): ls.append(o)
    except OSError: pass
    return [o for o in ls if o["id"] not in sil]

def notlar_view():  # /status "notlar": son NOT_GOSTER_SA saatin notları, yeniden eskiye
    sinir = (datetime.datetime.now() - datetime.timedelta(hours=NOT_GOSTER_SA)).isoformat(timespec="seconds")
    return [{"id": o["id"], "at": o.get("at"), "metin": o["metin"]} for o in reversed(_notlar_oku()) if str(o.get("at") or "")[:19] >= sinir[:19]][:NOT_GOSTER_EN_COK]

def notlar_islem(p):  # POST /notlar {"sil": id} (pano, anahtarlı)
    i = str(p.get("sil") or "")
    if not i or not any(o["id"] == i for o in _notlar_oku()): return {"ok": False, "err": _t("not yok", "no such note")}
    write([(os.path.join(BASE, NOTLAR_DOSYA), json.dumps({"sil": i, "at": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")])
    return {"ok": True}

# --- Kutudaki her yazı asistana (5 Kasım) ----------------------------------------------------------------------------------------------------
# Toplantı oturumu izlemiyorken kutuya yazılan her şey Konuş asistanına yazılı gider (konus_yazili(kutu=True)); "not:" öneki ve başta "?" şart değil.
# Not mu, soru mu, düzeltme mi: asistan karar verir. Asistan dosya yazamaz (Read/Grep/Glob), bu yüzden cevabın sonunda iki etiketten birini koyar; aktarıcı
# cevap bitince etiketi ayıklar (panoda ve geçmişte görünmez) ve işi yapar:
#   [NOT: metin]            → toplantı yokken Notlar defteri, toplantı sürerken döküme not
#   [SÖZLÜK: yanlış => doğru] → sözlüğe kullanıcı terimi (toplanti-claude.py sozluk --ekle; yalnız ad/terim düzeltmesi; kayıt veritabanı ve özet düzeltmesi bu yolda yok)
# Asistan hiç çalışamazsa (Claude yok, süreç açılamadı, zaman aşımı, meşgul) yazı not olarak kalır ve panoda açıkça söylenir (kutu_yedek).
KUTU_ETIKET_RX = re.compile(r"\[\s*(NOT|NOTE|SÖZLÜK|SOZLUK|SÖZLUK|DICT)\s*:\s*(.+?)\s*\]", re.I | re.S)
KUTU_BEKLEYEN = {}  # asistana giden, henüz cevabı gelmemiş kutu yazısı: {"metin", "at"} (bas-konus.py konus_yazili; _konus_kur hata verince kutu_yedek)
KUTU_SOZLUK_SINIR = 60

def kutu_not_kaydet(metin, at=None):  # toplantı yokken Notlar defteri, toplantı sürerken (ya da hazırlanırken) döküme not
    if toplantisiz(): return not_defter_yaz(metin, at)
    note({"text": str(metin)[:4000], "at": at or datetime.datetime.now().isoformat(timespec="seconds"), "meeting": {}}); return {"ok": True}

def kutu_sozluk_ekle(yanlis, dogru):  # → None (eklendi) ya da hata metni. Sözlük kuralı: toplanti-claude.py sozluk --ekle (kullanıcı terimi, --birlestir'de korunur)
    y, d = " ".join(str(yanlis).split()), " ".join(str(dogru).split())
    if not y or not d or y.lower() == d.lower() or max(len(y), len(d)) > KUTU_SOZLUK_SINIR or len(y.split()) > 4 or len(d.split()) > 4: return _t("terim uygun değil", "term not suitable")
    tc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toplanti-claude.py")  # relay.py ile aynı klasör (kurulumda da)
    if not os.path.isfile(tc): return _t("sözlük aracı yok", "dictionary tool missing")
    try:
        r = subprocess.run([sys.executable, "-B", tc, "--dir", BASE, "sozluk", "--ekle", y, d], capture_output=True, text=True, timeout=30, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except (OSError, subprocess.SubprocessError) as e: return type(e).__name__
    if r.returncode: print(f"KUTU: sözlüğe eklenemedi — {(r.stderr or r.stdout)[-200:]}"); return _t("sözlüğe yazılamadı", "couldn't write to the dictionary")
    print(f"KUTU: sözlüğe eklendi — {y} → {d}"); return None

def kutu_etiketleri(metin, soru=""):  # asistanın cevabı → etiketsiz metin (not/sözlük işi yapılır; yapılamayan iş cevabın sonuna açıkça yazılır)
    uyari = []
    for m in KUTU_ETIKET_RX.finditer(metin or ""):
        tur_, ic = m.group(1).upper(), m.group(2).strip()
        if tur_.startswith("NOT"):
            if ic: kutu_not_kaydet(ic); print(f"KUTU: asistan notu kaydetti ({len(ic)} karakter)")
        else:
            p_ = re.split(r"\s*(?:=>|→|->|=)\s*", ic, 1)
            if len(p_) != 2: uyari.append(_t("Sözlüğe eklenemedi: biçim anlaşılmadı", "Not added to the dictionary: format unclear")); continue
            h = kutu_sozluk_ekle(p_[0].strip("\"'“”‘’ "), p_[1].strip("\"'“”‘’ "))
            if h: uyari.append(_t(f"Sözlüğe eklenemedi ({h})", f"Not added to the dictionary ({h})"))
    temiz = re.sub(r"[ \t]+\n", "\n", KUTU_ETIKET_RX.sub("", metin or "")).rstrip()
    return (temiz + ("\n" if temiz else "") + " · ".join(uyari)) if uyari else temiz

def kutu_yedek(hata=None):  # asistan çalışamadı (_konus_kur durum=hata): bekleyen kutu yazısı Not olarak kalır; → panoda gösterilecek hata metni
    k = dict(KUTU_BEKLEYEN); KUTU_BEKLEYEN.clear()
    try: eski = (datetime.datetime.now() - datetime.datetime.fromisoformat(k.get("at") or "2000-01-01")).total_seconds() > 300
    except ValueError: eski = True
    if not k.get("metin") or eski: return hata  # beş dakikadan eski bekleyen yazı başka işin hatasına bağlanmaz
    kutu_not_kaydet(k["metin"], k.get("at")); print(f"KUTU: asistan çalışamadı ({str(hata)[:80]}) — yazı not olarak kaydedildi")
    return _t("Asistan şu an çalışamadı; yazdığın not olarak kaydedildi", "The assistant couldn't run right now; what you typed was saved as a note") + (f" ({hata})" if hata else "")
