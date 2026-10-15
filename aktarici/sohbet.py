# Suflor.me aktarıcı bölümü: Sohbet kipi (eller serbest). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("sohbet")):
# KONUS, _KS, AKIS, konus_basla, konus_ses, konus_parca, tur_olasilik, seslendir … bas-konus.py / brifing-ses.py'nin. import etme. Python 3.9 uyumlu.
# --- Sohbet kipi (v0.49.0; S47 2. madde, araştırma testler/arastirma-sohbet-kipi-20261016/) ---------------------------------------------------
# Panoda "Sohbet"e bir dokunuş: mikrofon açık kalır, ses yarım saniyede bir gelir (komut sohbet_parca). Tur sonu: sessizlik SOHBET_SESSIZ_SN'yi
# geçince smart-turn sorulur — model kapı değil bekleme süresi seçicisi (LiveKit/HF düzeni): "bitti" (≥ hihi_tur_esik) → toplam SOHBET_KISA_SN,
# değilse SOHBET_UZUN_SN beklenir; konuşma sürerse tur sürer; son parçanın metni "bekle / bir saniye" ile bitiyorsa SOHBET_BEKLE_SN. Süre dolunca
# kayıt bas-tut'un bırakış yoluna (konus_ses) gider. Suflor düşünürken/konuşurken gelen ses atılır; ancak cevap SOHBET_KORU_SN'den uzun süredir
# okunuyorken ≥ SOHBET_KESME_SN kesintisiz konuşma araya girme sayılır: okuma durur, kalan cümleler okunmaz, ses yeni turun başı olur ("hı hı" kısa
# kalır, kesme sayılmaz). Kapanış: SOHBET_UYARI_SN sessizlikte "Buradayım." , SOHBET_KAPAN_SN'de kapanır; "tamam teşekkürler / kapat" kapatır;
# toplantı başlarsa ya da kulaklık çıkarsa kapanır. Yalnız kulaklıkla ve toplantı dışında (hoparlörde Suflor kendi sesini duyar; Apple ses işleme yok).
SOHBET_SESSIZ_SN, SOHBET_KISA_SN, SOHBET_UZUN_SN, SOHBET_MODELSIZ_SN, SOHBET_BEKLE_SN = 0.6, 0.8, 2.5, 1.2, 6.0
SOHBET_KESME_SN, SOHBET_KORU_SN, SOHBET_UYARI_SN, SOHBET_KAPAN_SN, SOHBET_ONCE_SN = 0.7, 2.0, 30.0, 60.0, 1.5
if os.environ.get("SUFLOR_TEST_SOHBET_KISA"): SOHBET_UYARI_SN, SOHBET_KAPAN_SN = 12.0, 20.0  # test/sohbet.py
SOHBET = {"acik": False, "t_ac": 0.0, "t_ses": 0.0, "t_mesgul": 0.0, "uyari": False, "durak": None, "bekle": None, "kesme_sn": 0.0, "t_okuma": 0.0, "sira": 0, "kilit": threading.Lock()}
SOHBET_KAPAT_RX = re.compile(r"^\W*(tamam,?\s*)?(teşekkür(ler| ederim)|sağ ?ol(un)?|kapat|sohbeti kapat|bu kadar|görüşürüz|thanks?( you)?|that'?s all|goodbye|bye)\W*$", re.I)
SOHBET_BEKLE_RX = re.compile(r"\b(bekle|dur bir|bir saniye|bir dakika|şey|hold on|wait|one sec(ond)?)\W*$", re.I)
def ses_caliyor():
    if os.environ.get("SUFLOR_TEST_BASLAT"): return time.time() < SES.get("test_bit", 0)
    with SES_K: q = bool(SES["q"]); p = SES.get("p")
    return q or bool(p and p.poll() is None)
def _okuma_izle(simdi):  # okumanın başladığı an (araya girme koruması SOHBET_KORU_SN buna göre); bekçi ve parça ikisi de çağırır
    tur = _KS["tur"]; okuma = ses_caliyor() and (tur is None or bool(tur.get("t_ses")))  # tur bittiyse kuyruktaki son cümleler okunuyor
    if okuma and not SOHBET["t_okuma"]: SOHBET["t_okuma"] = simdi
    if not okuma: SOHBET["t_okuma"] = 0.0
    return okuma
def sohbet_view(): return {"acik": SOHBET["acik"], "bekle": SOHBET["bekle"], "okuyor": ses_caliyor()} if SOHBET["acik"] else {"acik": False}
def sohbet_basla():
    if not AYAR.get("konusma", True): return {"ok": False, "err": _t("Konuşma kapalı (ayar konusma)", "Voice is off (setting konusma)")}
    if toplanti_var(): return {"ok": False, "err": _t("Toplantı sürerken sohbet kapalı — “Claude, …” de ya da basılı tut", "Conversation is off during a meeting — say “Claude, …” or hold to talk")}
    if not kulaklik(): return {"ok": False, "err": _t("Sohbet yalnız kulaklıkla (hoparlörde Suflor kendi sesini duyar) — basılı tutarak sor", "Conversation needs headphones (on speakers Suflor hears itself) — hold to talk instead")}
    if SOHBET["acik"]: return {"ok": True}
    r = konus_basla()
    if not r.get("ok"): return r
    simdi = time.time()
    with SOHBET["kilit"]: SOHBET.update(acik=True, t_ac=simdi, t_ses=simdi, t_mesgul=simdi, uyari=False, durak=None, bekle=None, kesme_sn=0.0, sira=SOHBET["sira"] + 1)
    _konus_kur(durum="dinliyor", soru=None, cevap="", hata=None, olcum=None, kaynak="sohbet")
    if float(AYAR.get("hihi_tur_esik", HIHI_TUR_ESIK)) > 0: threading.Thread(target=tur_baslat, daemon=True).start()
    threading.Thread(target=_sohbet_bekci, args=(SOHBET["sira"],), daemon=True).start()
    print("SOHBET: açıldı"); return {"ok": True}
def sohbet_kapat(neden, soz=None):
    with SOHBET["kilit"]:
        if not SOHBET["acik"]: return
        SOHBET.update(acik=False, bekle=None)
    if not _KS["tur"]: _akis_sifirla(); _konus_kur(durum="hazir" if konus_canli() else "kapali")
    if soz: seslendir(soz, kuyruk=True)
    print(f"SOHBET: kapandı ({neden}, {time.time() - SOHBET['t_ac']:.0f} sn)")
def _sohbet_bekci(sira):
    k_t = 0.0
    while SOHBET["acik"] and SOHBET["sira"] == sira:
        time.sleep(0.5); simdi = time.time(); _okuma_izle(simdi)
        if toplanti_var(): sohbet_kapat("toplantı başladı"); return
        if simdi - k_t > 5:
            k_t = simdi
            if not kulaklik(): sohbet_kapat("kulaklık çıktı", _t("Kulaklık çıktı, sohbeti kapattım.", "Headphones out, conversation closed.")); return
        if _KS["tur"] or (ses_caliyor() and not SOHBET["uyari"]): SOHBET["t_mesgul"] = simdi; continue
        bos = simdi - max(SOHBET["t_ses"], SOHBET["t_mesgul"])
        if bos >= SOHBET_KAPAN_SN: sohbet_kapat("sessizlik", _t("Sohbeti kapattım.", "Conversation closed.")); return
        if bos >= SOHBET_UYARI_SN and not SOHBET["uyari"]:
            SOHBET["uyari"] = True; seslendir(_t("Buradayım.", "I'm here."), kuyruk=True); print(f"SOHBET: {SOHBET_UYARI_SN:.0f} sn sessizlik — uyarı")
def _pencereler(b, bas=0):
    return [_rms(bytes(b[i:i + AKIS_PENCERE])) for i in range(bas, len(b) - AKIS_PENCERE + 1, AKIS_PENCERE)]
def _sohbet_esik():
    with AKIS["kilit"]: b = bytes(AKIS["pcm"])
    taban = sorted(_pencereler(b)[::4]) or [0]
    return b, max(250, taban[len(taban) // 5] * 2.5)
def sohbet_parca(p):
    if not SOHBET["acik"]: return {"ok": False, "kapali": True}
    try: pcm = base64.b64decode(str(p.get("pcm") or ""), validate=True)
    except ValueError: return {"ok": False, "err": "pcm"}
    simdi = time.time(); pen = _pencereler(pcm); esik = AKIS.get("esik") or 400
    konusma = sum(x >= esik for x in pen) * AKIS_PENCERE / 2 / WH_SR
    if konusma >= 0.15: SOHBET.update(t_ses=simdi, uyari=False)
    tur = _KS["tur"]
    if tur or ses_caliyor():  # Suflor düşünüyor ya da okuyor
        onceki = SOHBET.setdefault("onceki", collections.deque(maxlen=4)); onceki.append(pcm)  # araya girmede sözün başı kaybolmasın (son ~2 sn)
        okuma = _okuma_izle(simdi)
        # araya girme: cevap ≥ SOHBET_KORU_SN'dir okunuyor ve parçanın çoğu konuşma; ardışık parçalarda birikir
        SOHBET["kesme_sn"] = SOHBET["kesme_sn"] + konusma if konusma >= len(pen) * AKIS_PENCERE / 2 / WH_SR * 0.6 else 0.0
        if okuma and simdi - SOHBET["t_okuma"] >= SOHBET_KORU_SN and SOHBET["kesme_sn"] >= SOHBET_KESME_SN:
            if tur: tur["sesli"] = False
            ses_durdur(); SOHBET.update(kesme_sn=0.0, t_okuma=0.0)
            with AKIS["kilit"]: AKIS["pcm"] = bytearray(b"".join(onceki)); AKIS.update(kesik=0, sira=0, metin={}, bekleyen=0)
            print("SOHBET: araya girildi — okuma durdu, kalan cümleler okunmayacak")
            SOHBET["kesildi"] = True
        elif SOHBET.get("kesildi"):  # araya girildi, Claude'un turu bitene kadar ses biriktirilir
            with AKIS["kilit"]: AKIS["pcm"] += pcm
        return {"ok": True, "mesgul": True}
    SOHBET["t_okuma"] = 0.0; SOHBET["kesme_sn"] = 0.0; SOHBET.pop("onceki", None)
    if SOHBET.pop("kesildi", None): _sohbet_akis_kur()  # biriken araya girme sesi akışa
    r = konus_parca(p)
    if not r.get("ok"): return r
    _sohbet_kirp(); _sohbet_tur_sonu()
    return {"ok": True}
def _sohbet_akis_kur():  # araya girmede biriken ses akış parçalarına bölünmeden durdu; konus_parca'nın kesimi sonraki parçada sürer
    with AKIS["kilit"]: AKIS.update(kesik=0, sira=0, metin={}, bekleyen=0)
def _sohbet_kirp():  # konuşma başlamadan biriken sessizlik büyümesin (60 sn tavanı): son SOHBET_ONCE_SN tutulur
    b, esik = _sohbet_esik()
    with AKIS["kilit"]:
        if AKIS["kesik"] or AKIS["sira"] or len(AKIS["pcm"]) < int(4 * WH_SR * 2): return
        if any(x >= esik for x in _pencereler(AKIS["pcm"])[:-int(SOHBET_ONCE_SN * WH_SR * 2 / AKIS_PENCERE)]): return
        del AKIS["pcm"][:len(AKIS["pcm"]) - int(SOHBET_ONCE_SN * WH_SR * 2) // 2 * 2]
def _sohbet_tur_sonu():
    b, esik = _sohbet_esik(); pen = _pencereler(b)
    if not pen: return
    k = 0
    while k < len(pen) and pen[-1 - k] < esik: k += 1
    sessiz = k * AKIS_PENCERE / 2 / WH_SR; konusma = sum(x >= esik for x in pen[:len(pen) - k]) * AKIS_PENCERE / 2 / WH_SR; n = len(b) / 2 / WH_SR
    if konusma < 0.4: SOHBET.update(durak=None, bekle=None); return
    if n >= KONUS_EN_UZUN_SN - 3: return _sohbet_gonder(b, n, sessiz)  # bir dakikalık kayıt tavanına yaklaşınca duraksamasız da tur kapanır
    if sessiz < SOHBET_SESSIZ_SN: SOHBET.update(durak=None, bekle=None); return
    durak = len(b) - k * AKIS_PENCERE
    if SOHBET["durak"] != durak:  # yeni duraksama: bekleme süresini seç
        e = float(AYAR.get("hihi_tur_esik", HIHI_TUR_ESIK)); p = tur_olasilik(b[:durak + int(0.3 * WH_SR * 2)]) if e > 0 else None
        bek = SOHBET_MODELSIZ_SN if p is None else SOHBET_KISA_SN if p >= e else SOHBET_UZUN_SN
        with AKIS["kilit"]: son = str(AKIS["metin"].get(AKIS["sira"] - 1) or "") if AKIS["sira"] else ""
        if son and SOHBET_BEKLE_RX.search(son): bek = max(bek, SOHBET_BEKLE_SN)
        SOHBET.update(durak=durak, bekle=bek)
        print(f"SOHBET: duraksama — tur sonu {'yok' if p is None else f'{p:.2f}'}, {bek:.1f} sn beklenecek")
    if sessiz >= SOHBET["bekle"]: _sohbet_gonder(b, n, sessiz)
def _sohbet_gonder(b, n, sessiz):
    SOHBET.update(durak=None, bekle=None)
    print(f"SOHBET: tur bitti ({n:.1f} sn kayıt, {sessiz:.1f} sn sessizlik)")
    r = konus_ses({"pcm": base64.b64encode(b).decode()})
    if not r.get("ok"): print(f"SOHBET: soru gönderilemedi ({r.get('err')})"); _akis_sifirla(); _konus_kur(durum="dinliyor", hata=None)
def sohbet_metin(metin):  # konus_ses'in yazıya dökülmüş metni: sohbeti kapatan söz mü (True: Claude'a gitmez)
    if not SOHBET["acik"] or not SOHBET_KAPAT_RX.match(metin or ""): return False
    sohbet_kapat("kullanıcı: " + " ".join(metin.split())[:40], _t("Görüşürüz.", "Talk soon.")); return True
