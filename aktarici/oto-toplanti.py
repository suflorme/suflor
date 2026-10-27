# --- Toplantıyı kendisi tanıma (S161, v0.144.0; kullanıcı 27 Ekim: "nereden başlatırsam başlatayım … otomatik olarak tanıyıp dahil olması gerekir") ---------
# 27 Ekim Meet denemesi: toplantı Meet sayfasından açıldı, Başlat'a basılmadı → dosya ilk notta "Toplantı" adıyla açıldı, başlık "Teams" dedi, toplantı oturumu
# yoktu. Artık tek tetik "tanınan toplantı": eklenti (çağrı açık) · menü uygulaması (masaüstü Teams/Zoom) · ses yardımcısı (toplantı uygulaması mikrofonu
# tutuyor — tek başına yalnız takvimde şu an süren bağlantılı bir toplantı varsa; mrt'de pano sohbeti sırasında Safari de "dinliyor" göründü).
# Tanınınca: takvimde ±OTO_ESLE_DK eşleşen toplantıdan ad (yoksa Başlat'ın konusu, o da yoksa sinyalin adı); platform sinyalden; döküm dosyası hemen açılır;
# Claude'un toplantı oturumu yalnız güvenilir sinyalde (eklenti çağrıda · masaüstü uygulama toplantıda · elle Başlat) sormadan açılır (baslat oto) — gizli kipte, ayar oto_haric'teki
# adlarda ve ayar oto_toplanti: false iken açılmaz. Sinyal yalnız "mikrofon + takvim" ise (S162, 27 Ekim: Safari/başka uygulama mikrofonu tutunca oturum boşuna açılıyordu) oturum açılmaz:
# panoda "Toplantı algılandı — Claude'u başlat" onay kartı çıkar (oto_oner; Onayla → baslat). Sonradan güvenilir sinyal gelirse oturum kendiliğinden açılır. Deneme
# aktarıcısında oturum yalnız SUFLOR_TEST_OTO=1 ile (sahte claude; kota harcanmaz). Sinyalin ham adları (sayfa başlığı, Meet kodu, pencere başlığı,
# "Toplantı") toplantı sürdükçe tek dosyaya eşlenir (oto_ad: paths/ensure_header/show). Başlat elle kalır; süren toplantıda yeni kayıt açmaz (baslat katıldı).
OTO = {"aktif": None, "son": None}
if "EYLEM_TUR" in globals(): EYLEM_TUR["baslat"] = "Başlat"  # öneri kartının yerel işi (oto_oner)
OTO_ESLE_DK = 15
OTO_BITIS_SN = float(os.environ.get("SUFLOR_TEST_YENI_SN") or (20 if os.environ.get("SUFLOR_TEST_HIZLI") else MASAUSTU_YENI_SN))  # sinyal bu kadar yoksa bitti — masaüstü yeni toplantı kuralıyla aynı süre (kısa kopma aynı toplantıda)
OTO_BASLAT_DK = 30  # bu süre içinde elle Başlat'a basıldıysa onun konusu ve oturumu kullanılır
MASAUSTU_PLATFORM = {"Teams": "teams", "Zoom": "zoom"}
def _oto_genel(ad):  # sinyalin anlamsız adı (eşlemede ham ad sayılır, dosyaya ad olmaz)
    return not ad or ad == YER_TUTUCU or bool(re.fullmatch(r"(Microsoft Teams|Teams|Zoom( Meeting| Toplantısı)?|Google Meet|Meet|Toplantı|Meeting|(Teams|Zoom|Masaüstü) toplantısı)", str(ad).strip(), re.I))
def oto_sinyal():  # → {"kaynak", "platform", "ham"} ya da None
    now = time.time(); x = STATE.get("extension") or {}
    if x.get("call") and _yas_sn(x) < min(30, TOPLANTI_VAR_SN):
        return {"kaynak": "eklenti", "platform": x.get("platform") or "bilinmeyen", "ham": x.get("meeting"), "guvenli": True}
    m = STATE.get("masaustu") or {}
    if m.get("toplantida") and now - m.get("t", 0) < 30:
        return {"kaynak": "masaüstü", "platform": MASAUSTU_PLATFORM.get(m.get("uygulama") or "", "bilinmeyen"), "ham": masaustu_baslik(), "guvenli": True}
    if yerel_ses_durum() == "dinliyor" and not (globals().get("SOHBET") or {}).get("acik"):  # pano sohbeti de mikrofonu tutar
        b = STATE.get("baslatma") or {}
        if b.get("konu") and not b.get("oto") and now - (b.get("at") or 0) < OTO_BASLAT_DK * 60:  # elle Başlat: güvenilir
            return {"kaynak": "mikrofon", "platform": b.get("platform") or "bilinmeyen", "ham": None, "guvenli": True}
        o = oto_takvim(None)  # takvimde ±OTO_ESLE_DK içinde toplantı (S162: kesin değil — bağlantı da aranmaz); güvenilir sayılmaz, yalnız öneri
        if o: return {"kaynak": "mikrofon", "platform": o.get("platform") or "bilinmeyen", "ham": None, "olay": o, "guvenli": False}
    return None
def oto_ses_sayilir():  # yerel ses (/ses-yerel): eklenti tanımasa da ses yardımcısı toplantı uygulamasını dinliyor ve takvim/Başlat doğruluyorsa toplantı sayılır — tek kaynak oto_sinyal
    try: return bool(oto_sinyal())
    except Exception: return False
def oto_takvim(platform, kesin=False):  # şu an süren ya da ±OTO_ESLE_DK içinde başlayan takvim toplantısı; aynı platform önde, sonra başlangıcı en yakın
    now = datetime.datetime.now().astimezone(); ad = []
    for e in (globals().get("TAKVIM_TAM") or {}).values():
        if e.get("tum_gun") or e.get("reddettin"): continue
        try: b, s = _zaman(e["baslangic"]), _zaman(e["bitis"])
        except (KeyError, TypeError, ValueError): continue
        pay = datetime.timedelta(minutes=0 if kesin else OTO_ESLE_DK)
        if not (b - pay <= now <= s + (datetime.timedelta(0) if kesin else datetime.timedelta(minutes=5))): continue
        if kesin and not e.get("baglanti"): continue
        ad.append((0 if platform and e.get("platform") == platform else 1, abs((now - b).total_seconds()), e))
    return min(ad, key=lambda t: t[:2])[2] if ad else None
def oto_ad(title):  # sinyalin ham adını süren toplantının adına eşle (paths/ensure_header/show çağırır); toplantı yoksa olduğu gibi
    a = OTO.get("aktif")
    if not a or title == a["ad"]: return title
    if title in a["ham"] or _oto_genel(title): return a["ad"]
    x = STATE.get("extension") or {}
    if x.get("call") and _yas_sn(x) < min(30, TOPLANTI_VAR_SN) and title == x.get("meeting"): a["ham"].add(title); return a["ad"]
    return title
def oto_platform(): return (OTO.get("aktif") or {}).get("platform")
def oto_view():
    a = OTO.get("aktif")
    return {k: a[k] for k in ("ad", "platform", "kaynak", "olay", "oturum", "neden")} if a else None
def oto_bak():
    if AYAR.get("oto_toplanti") is False: return
    now = time.time(); s = oto_sinyal(); a = OTO.get("aktif")
    if a:
        if s:
            a["t_son"] = now
            if s.get("guvenli") and not a["karar"]: _oto_oturum(a, s, False, now)  # sonradan güvenilir sinyal (eklenti/masaüstü/Başlat) geldi
            if s.get("ham") and s["ham"] != a["ad"]: a["ham"].add(s["ham"])
        elif now - a["t_son"] > OTO_BITIS_SN:
            print(f"OTO: toplantı bitti — {a['ad']} (sinyal {round(now - a['t_son'])} sn yok)"); OTO["son"] = a; OTO["aktif"] = None
        return
    if not s or gizli_acik(): return
    o = s.get("olay") or oto_takvim(s["platform"])
    b = STATE.get("baslatma") or {}; elle = bool(b.get("konu") and not b.get("oto") and now - (b.get("at") or 0) < OTO_BASLAT_DK * 60)  # kendi açtığı sayılmaz
    ad = (b["konu"] if elle else None) or (o or {}).get("baslik") or (None if _oto_genel(s.get("ham")) else s.get("ham")) \
         or (f"{PLATFORM_AD[s['platform']]} toplantısı" if s["platform"] in PLATFORM_AD and s["platform"] != "bilinmeyen" else "Toplantı")
    ad = " ".join(str(ad).split())[:200]
    haric = next((h for h in (AYAR.get("oto_haric") or []) if isinstance(h, str) and h.strip() and h.strip().lower() in ad.lower()), None)
    a = OTO["aktif"] = {"ad": ad, "platform": s["platform"], "kaynak": s["kaynak"], "olay": (o or {}).get("id"), "ham": {x for x in (s.get("ham"),) if x and x != ad},
                        "t0": now, "t_son": now, "oturum": False, "neden": None, "karar": False, "haric": haric, "guvenli": bool(s.get("guvenli"))}
    print(f"OTO: toplantı tanındı — {ad} · {PLATFORM_AD.get(s['platform'], s['platform'])} · {s['kaynak']}" + (" · takvimden" if o else " · elle Başlat" if elle else ""))
    with LOCK:  # döküm dosyası hemen (satır beklemeden): 27 Ekim'de ilk nota kadar açılmadı
        x = STATE.get("extension") or {}  # başlık asıl kaynağı söylesin: eklentinin transkript paneli / canlı altyazı, yoksa genel
        src = (None if x.get("panel") else "captions" if x.get("captions") else "oto") if s["kaynak"] == "eklenti" else "oto"
        md, jl = paths(ad); hdr = ensure_header(md, ad, {"platform": s["platform"]}, src); show(md, ad)
    if hdr: write([(md, hdr)])
    heartbeat()
    _oto_oturum(a, s, elle, now)
def _oto_oturum(a, s, elle, now):  # a["karar"]: oturum kararı verildi; güvenilmeyen sinyalde (öneri) yanlış kalır, güvenilir sinyal gelince yeniden denenir
    if a["haric"]: a["neden"] = f"hariç ({a['haric']})"; a["karar"] = True
    elif elle or topo_canli() or (STATE.get("izle_seen") and now - STATE["izle_seen"] < 60): a["neden"] = "oturum zaten var (elle Başlat)"; a["oturum"] = True; a["karar"] = True
    elif deneme_aktarici() and os.environ.get("SUFLOR_TEST_OTO") != "1": a["neden"] = "deneme aktarıcısı"; a["karar"] = True
    elif not s.get("guvenli"):
        a["neden"] = "güvenilir sinyal yok (yalnız mikrofon + takvim) — öneri kartı"; oto_oner(a)
        print("OTO: toplantı oturumu açılmadı (" + a["neden"] + ")"); return
    else:
        a["karar"] = True; r = baslat({"olay": a["olay"], "konu": a["ad"], "platform": s["platform"], "oto": True})
        a["oturum"] = bool(r.get("ok")); a["neden"] = None if r.get("ok") else str(r.get("err") or "?")[:160]
    print("OTO: toplantı oturumu " + (f"açılmadı ({a['neden']})" if a["neden"] else "açıldı"))
def oto_oner(a):  # panoda onay kartı (izin kartıyla aynı altyapı: yerel eylem + onay kartı); tıklayınca baslat — toplantı başına bir kez
    if a.get("oner"): return
    ne = _t("Toplantı algılandı — Claude'u başlat", "Meeting detected — start Claude")
    x = eylem_ekle({"tur": "baslat", "baslik": f"{ne}: {a['ad']}"[:160], "ayrinti": json.dumps({"olay": a["olay"], "konu": a["ad"], "platform": a["platform"]}, ensure_ascii=False)})
    if not x: return
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True)
    c = add_card({"kind": "not", "text": ne, "why": a["ad"][:120], "onay": True})
    if c:
        with LOCK: c["eylem"] = x["id"]
    a["oner"] = x["id"]; print(f"OTO: öneri kartı — {a['ad']}")
def oto_karar(x, durum):  # eylem_karar'dan: Onayla → baslat; Reddet → bu toplantıda yeniden sorma
    with LOCK:
        for c in CARDS:
            if c.get("eylem") == x["id"] and c.get("status") == "acik": c["status"] = durum; c["acted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    a = OTO.get("aktif") or {}
    if durum != "onaylandi":
        if a.get("oner") == x["id"]: a["karar"] = True; a["neden"] = "öneri reddedildi"
        return
    try: ay = json.loads(x.get("ayrinti") or "{}")
    except ValueError: ay = {}
    def is_():
        r = baslat({"olay": ay.get("olay"), "konu": ay.get("konu"), "platform": ay.get("platform"), "oto": True})
        if a.get("oner") == x["id"]: a["karar"] = True; a["oturum"] = bool(r.get("ok")); a["neden"] = None if r.get("ok") else str(r.get("err") or "?")[:160]
        print("OTO: öneri onaylandı — toplantı oturumu " + ("açıldı" if r.get("ok") else f"açılmadı ({str(r.get('err'))[:80]})"))
    threading.Thread(target=is_, daemon=True).start()
def _oto_dongu():
    while True:
        time.sleep(1 if os.environ.get("SUFLOR_TEST_HIZLI") else 3)
        try: oto_bak()
        except Exception as e: print(f"OTO: denetim hatası ({e.__class__.__name__}: {str(e)[:120]})")
