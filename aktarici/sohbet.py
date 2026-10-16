# Suflor.me aktarıcı bölümü: Sohbet kipi (eller serbest). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("sohbet")):
# KONUS, _KS, AKIS, konus_basla, konus_ses, konus_parca, tur_olasilik, seslendir … bas-konus.py / brifing-ses.py'nin. import etme. Python 3.9 uyumlu.
# --- Sohbet kipi (v0.49.0; S47 2. madde, araştırma testler/arastirma-sohbet-kipi-20261016/) ---------------------------------------------------
# Panoda "Sohbet"e bir dokunuş: mikrofon açık kalır, ses yarım saniyede bir gelir (komut sohbet_parca). Tur sonu: sessizlik SOHBET_SESSIZ_SN'yi
# geçince smart-turn sorulur — model kapı değil bekleme süresi seçicisi (LiveKit/HF düzeni): "bitti" (≥ hihi_tur_esik) → toplam SOHBET_KISA_SN,
# değilse SOHBET_UZUN_SN beklenir; konuşma sürerse tur sürer; son parçanın metni "bekle / bir saniye" ile bitiyorsa SOHBET_BEKLE_SN. Süre dolunca
# kayıt bas-tut'un bırakış yoluna (konus_ses) gider. Suflor düşünürken/konuşurken gelen ses atılır; ancak cevap SOHBET_KORU_SN'den uzun süredir
# okunuyorken ≥ SOHBET_KESME_SN kesintisiz konuşma araya girme sayılır: okuma durur, kalan cümleler okunmaz, ses yeni turun başı olur ("hı hı" kısa
# kalır, kesme sayılmaz). v0.49.2: Claude düşünürken söylenen de atılmaz — ayrı tamponda birikir (önceki sorunun akışı o sırada sıfırlanır), Suflor boşa
# çıkınca sonraki sorunun başı olur; söz sürerken okuma başlarsa koruma süresi beklenmeden okuma durur. Kapanış: SOHBET_UYARI_SN sessizlikte "Buradayım." , SOHBET_KAPAN_SN'de kapanır; "tamam teşekkürler / kapat" kapatır;
# toplantı başlarsa ya da kulaklık çıkarsa kapanır. Yalnız kulaklıkla ve toplantı dışında (hoparlörde Suflor kendi sesini duyar; Apple ses işleme yok).
# v0.49.5 bekleme 0,8/2,5 → 1,0/2,0 ve biriktirme eşiği 0,15 → 0,3 sn: gerçek kayıtlarla benzetim (testler/sohbet-esik-20261016.md) — erken kesme
# %4,3 → %1,7, tur sonunda ortanca bekleme +0,2 sn; kısa çıtırtı/"evet" Claude düşünürken biriktirmeyi başlatmaz.
SOHBET_SESSIZ_SN, SOHBET_KISA_SN, SOHBET_UZUN_SN, SOHBET_MODELSIZ_SN, SOHBET_BEKLE_SN, SOHBET_BIRIK_SN = 0.6, 1.0, 2.0, 1.2, 6.0, 0.3
SOHBET_KESME_SN, SOHBET_KORU_SN, SOHBET_UYARI_SN, SOHBET_KAPAN_SN, SOHBET_ONCE_SN = 0.7, 2.0, 30.0, 60.0, 1.5
if os.environ.get("SUFLOR_TEST_SOHBET_KISA"): SOHBET_UYARI_SN, SOHBET_KAPAN_SN = 12.0, 20.0  # test/sohbet.py
SOHBET = {"acik": False, "t_ac": 0.0, "t_ses": 0.0, "t_mesgul": 0.0, "uyari": False, "durak": None, "bekle": None, "kesme_sn": 0.0, "t_okuma": 0.0, "sira": 0, "kilit": threading.Lock()}
# Düşünme sözü (v0.51.3, ikinci gerçek deneme 16 Ekim: "Günaydın… nasıl desem" duraksamasında tur sonu modeli 0,98 dedi, soru erken gitti; devam eden söz okumayı
# durdurdu ve kullanıcı hiçbir şey duymadı). Tur bittiğinde dökülen söz düşünme ya da bağlaç sözüyle bitiyorsa Claude'a gitmez: kayıt akışa geri konur, dinleme sürer,
# konuşma sürerse iki parça tek soru olur. SOHBET_DUSUNME_SN boyunca hiç konuşulmazsa söz olduğu gibi gider (takılıp kalmasın). Duraksama anında son parça henüz
# dökülmemiş olduğundan SOHBET_BEKLE_RX bu durumu yakalayamıyordu.
SOHBET_DUSUNME_SN = 4.0
SOHBET_DUSUNME_RX = re.compile(r"(\b(nasıl (desem|diyeyim|söylesem|anlatsam)|yani|şey|hani|işte|şöyle( ki)?|mesela|aslında|bir saniye|dur bir|bekle|ve|ama|fakat|çünkü|ki|veya|ya da|ile|"
                               r"how (do i|should i) (say|put)|i mean|like|so|and|but|because|um+|uh+)|\b(e+|ı+|hm+|em+))\W*$", re.I)
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
# v0.54.3 (kullanıcı, 16 Ekim: "sohbette miyim, kapalı mı anlamıyorum"): son kapanış nedeni 60 sn panoda görünür (aktarıcı kendisi kapatınca iz kalsın)
def sohbet_view():
    if SOHBET["acik"]: return {"acik": True, "bekle": SOHBET["bekle"], "okuyor": ses_caliyor()}
    k = SOHBET.get("kapanis")
    return {"acik": False, **({"kapandi": k["neden"], "kapandi_sn": round(time.time() - k["t"])} if k and time.time() - k["t"] < 60 else {})}
def sohbet_basla():
    if not AYAR.get("konusma", True): return {"ok": False, "err": _t("Konuşma kapalı (ayar konusma)", "Voice is off (setting konusma)")}
    if toplanti_var(): return {"ok": False, "err": _t("Toplantı sürerken sohbet kapalı — “Claude, …” de ya da basılı tut", "Conversation is off during a meeting — say “Claude, …” or hold to talk")}
    if not kulaklik(): return {"ok": False, "err": _t("Sohbet yalnız kulaklıkla (hoparlörde Suflor kendi sesini duyar) — basılı tutarak sor", "Conversation needs headphones (on speakers Suflor hears itself) — hold to talk instead")}
    if SOHBET["acik"]: return {"ok": True}
    r = konus_basla()
    if not r.get("ok"): return r
    simdi = time.time()
    SOHBET.pop("biriken", None); SOHBET.pop("onceki", None)
    with SOHBET["kilit"]: SOHBET.update(acik=True, t_ac=simdi, t_ses=simdi, t_mesgul=simdi, uyari=False, durak=None, bekle=None, kesme_sn=0.0, sira=SOHBET["sira"] + 1)
    _konus_kur(durum="dinliyor", soru=None, cevap="", hata=None, olcum=None, kaynak="sohbet")
    if float(AYAR.get("hihi_tur_esik", HIHI_TUR_ESIK)) > 0: threading.Thread(target=tur_baslat, daemon=True).start()
    threading.Thread(target=_sohbet_bekci, args=(SOHBET["sira"],), daemon=True).start()
    print("SOHBET: açıldı"); return {"ok": True}
def sohbet_kapat(neden, soz=None):
    with SOHBET["kilit"]:
        if not SOHBET["acik"]: return
        SOHBET.update(acik=False, bekle=None, kapanis={"neden": "kullanici" if neden.startswith("kullanıcı") else {"toplantı başladı": "toplanti", "kulaklık çıktı": "kulaklik"}.get(neden, neden), "t": time.time()})
        SOHBET.pop("biriken", None); SOHBET.pop("onceki", None)
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
        d = SOHBET.get("dusunme")
        if d and not _KS["tur"] and SOHBET["t_ses"] - d["t"] < 0.3 and simdi - d["t"] >= SOHBET_DUSUNME_SN: SOHBET.pop("dusunme", None); _sohbet_dusunme_gonder(d["metin"])
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
    # v0.54.3 (S70, kullanıcı 16 Ekim: "arka plan seslerinden sürekli kesiliyor ve susuyor"): araya girme varsayılan kapalı (ayar sohbet_araya_girme) — cevap
    # sonuna kadar okunur, okuma sırasında gelen ses atılır (arka plan sesi okumayı kesmez, sonraki soru da olmaz); Claude düşünürken söylenen yine biriktirilir.
    if not AYAR.get("sohbet_araya_girme") and _okuma_izle(simdi):
        SOHBET.pop("biriken", None); SOHBET.pop("onceki", None); SOHBET["kesme_sn"] = 0.0
        if konusma >= SOHBET_BIRIK_SN and SOHBET.get("yok_t") != SOHBET["t_okuma"]:
            SOHBET["yok_t"] = SOHBET["t_okuma"]; print("SOHBET: okuma sürerken ses — yok sayıldı (araya girme kapalı), okuma sürüyor")
        return {"ok": True, "mesgul": True}
    if tur or ses_caliyor():  # Suflor düşünüyor ya da okuyor
        onceki = SOHBET.setdefault("onceki", collections.deque(maxlen=4)); onceki.append(pcm)  # sözün başı kaybolmasın (son ~2 sn)
        okuma = _okuma_izle(simdi)
        SOHBET["kesme_sn"] = SOHBET["kesme_sn"] + konusma if konusma >= len(pen) * AKIS_PENCERE / 2 / WH_SR * 0.6 else 0.0  # ardışık parçalarda birikir
        bir = SOHBET.get("biriken")
        if bir is not None:  # biriktiriliyor (araya girme ya da düşünürken konuşma); Suflor boşa çıkınca akışa geçer
            bir += pcm
            if okuma and SOHBET["kesme_sn"] >= SOHBET_KESME_SN: _sohbet_kes(tur, "konuşma sürerken okuma başladı")  # söz sürüyor: koruma süresi yok
            return {"ok": True, "mesgul": True}
        if okuma:  # araya girme: cevap ≥ SOHBET_KORU_SN'dir okunuyor ve ≥ SOHBET_KESME_SN kesintisiz konuşma ("hı hı" kısa kalır)
            if simdi - SOHBET["t_okuma"] >= SOHBET_KORU_SN and SOHBET["kesme_sn"] >= SOHBET_KESME_SN:
                SOHBET["biriken"] = bytearray(b"".join(onceki)); _sohbet_kes(tur, "araya girildi")
        elif konusma >= SOHBET_BIRIK_SN:  # v0.49.2: Claude düşünürken (yazıya dökme, cevap bekleme) konuşma atılmaz, sonraki soru olur
            SOHBET["biriken"] = bytearray(b"".join(onceki)); print("SOHBET: Claude düşünürken konuşma — biriktiriliyor, sonraki soru olacak")
        return {"ok": True, "mesgul": True}
    SOHBET["t_okuma"] = 0.0; SOHBET["kesme_sn"] = 0.0; SOHBET.pop("onceki", None)
    bir = SOHBET.pop("biriken", None)
    if bir is not None:
        with AKIS["kilit"]: AKIS.update(pcm=bytearray(bir), kesik=0, sira=0, metin={}, bekleyen=0)
        print(f"SOHBET: biriken {len(bir) / 2 / WH_SR:.1f} sn ses sonraki soruya")
    r = konus_parca(p)
    if not r.get("ok"): return r
    _sohbet_kirp(); _sohbet_tur_sonu()
    return {"ok": True}
def _sohbet_kes(tur, neden):  # okumayı durdur, kalan cümleler okunmasın
    if tur: tur["sesli"] = False
    ses_durdur(); SOHBET.update(kesme_sn=0.0, t_okuma=0.0)
    print(f"SOHBET: {neden} — okuma durdu, kalan cümleler okunmayacak")
def _sohbet_kirp():  # konuşma başlamadan biriken sessizlik büyümesin (60 sn tavanı): son SOHBET_ONCE_SN tutulur
    b, esik = _sohbet_esik()
    with AKIS["kilit"]:
        if AKIS["kesik"] or AKIS["sira"] or len(AKIS["pcm"]) < int(4 * WH_SR * 2): return
        if any(x >= esik for x in _pencereler(AKIS["pcm"])[:-int(SOHBET_ONCE_SN * WH_SR * 2 / AKIS_PENCERE)]): return
        del AKIS["pcm"][:len(AKIS["pcm"]) - int(SOHBET_ONCE_SN * WH_SR * 2) // 2 * 2]
def _sohbet_tur_sonu():
    d = SOHBET.get("dusunme")
    if d and SOHBET["t_ses"] - d["t"] < 0.3: return  # düşünme sözünden sonra yeni konuşma yok: aynı söz yeniden gitmesin (bekçi SOHBET_DUSUNME_SN'de gönderir)
    b, esik = _sohbet_esik(); pen = _pencereler(b)
    if not pen: return
    k = 0
    while k < len(pen) and pen[-1 - k] < esik: k += 1
    sessiz = k * AKIS_PENCERE / 2 / WH_SR; konusma = sum(x >= esik for x in pen[:len(pen) - k]) * AKIS_PENCERE / 2 / WH_SR; n = len(b) / 2 / WH_SR
    if konusma < 0.4: SOHBET.update(durak=None, bekle=None); return
    if n >= KONUS_EN_UZUN_SN - 3: return _sohbet_gonder(b, n, sessiz)  # bir dakikalık kayıt tavanına yaklaşınca duraksamasız da tur kapanır
    if sessiz < SOHBET_SESSIZ_SN: SOHBET.update(durak=None, bekle=None); return
    durak = (len(pen) - k) * AKIS_PENCERE  # son konuşma penceresinin sonu: pencereler kaydın başına hizalı, parça boyu ne olursa olsun duraksama boyunca sabit
    if SOHBET["durak"] != durak:  # yeni duraksama: bekleme süresini seç (v0.49.5: duraksama başına bir kez — önce len(b)'ye göreydi, her parçada kayıyordu)
        e = float(AYAR.get("hihi_tur_esik", HIHI_TUR_ESIK)); p = tur_olasilik(b[:durak + int(0.3 * WH_SR * 2)]) if e > 0 else None
        bek = SOHBET_MODELSIZ_SN if p is None else SOHBET_KISA_SN if p >= e else SOHBET_UZUN_SN
        with AKIS["kilit"]: son = str(AKIS["metin"].get(AKIS["sira"] - 1) or "") if AKIS["sira"] else ""
        if son and SOHBET_BEKLE_RX.search(son): bek = max(bek, SOHBET_BEKLE_SN)
        SOHBET.update(durak=durak, bekle=bek)
        print(f"SOHBET: duraksama — tur sonu {'yok' if p is None else f'{p:.2f}'}, {bek:.1f} sn beklenecek")
    if sessiz >= SOHBET["bekle"]: _sohbet_gonder(b, n, sessiz)
def _sohbet_gonder(b, n, sessiz):
    SOHBET.update(durak=None, bekle=None); SOHBET.pop("dusunme", None)
    print(f"SOHBET: tur bitti ({n:.1f} sn kayıt, {sessiz:.1f} sn sessizlik)")
    r = konus_ses({"pcm": base64.b64encode(b).decode()})
    if not r.get("ok"): print(f"SOHBET: soru gönderilemedi ({r.get('err')})"); _akis_sifirla(); _konus_kur(durum="dinliyor", hata=None)
# Ses izi süzgeci (v0.51.0, S59 3. adım; ayar sohbet_ses_izi, varsayılan kapalı): mikrofon açık kaldığı için odadaki başkasının ya da televizyonun sözü
# soru olmasın. Turun akış parçalarının ses izi (ECAPA, Whisper işçisinde) toplantılarda öğrenilen kullanıcı profiliyle (ses-izi-ben.json) karşılaştırılır;
# ≥ 1,5 sn'lik parçaların süresinin %60'ı ODA_ESIK'in (0,35; 11 Ekim ölçümü: kullanıcı 0,36–0,78, başka sesler ≤ 0,33) altındaysa soru gitmez, dinleme
# sürer. Profil yoksa ya da parçalar kısaysa süzgeç karar vermez (soru gider). Araya girme yalnız ses düzeyine bakar (bu süzgeç onu kapsamaz).
def sohbet_ses_izi_red(izler):  # izler: [(iz, sn)] → True: kullanıcının sesi değil
    if not SOHBET["acik"] or AYAR.get("sohbet_ses_izi") is not True: return False
    olc = [(b, sn) for b, sn in ((kullanici_benzer(iz), sn) for iz, sn in izler if sn >= ODA_EN_KISA) if b is not None]
    if not olc: print("SOHBET: ses izi — karar yok (profil yok ya da parçalar kısa), soru gidiyor"); return False
    top = sum(sn for _, sn in olc); red = sum(sn for b, sn in olc if b < ODA_ESIK) >= 0.6 * top
    print(f"SOHBET: ses izi {' '.join(f'{b:.2f}' for b, _ in olc)} — {'kullanıcıya benzemiyor, soru gönderilmedi' if red else 'kullanıcı'}")
    return red
def sohbet_dusunme(metin, pcm):  # konus_ses'in dökülmüş metni düşünme sözüyle mi bitiyor → True: gönderilmez, kayıt akışa geri, dinleme sürer
    if not SOHBET["acik"] or not SOHBET_DUSUNME_RX.search(metin or ""): return False
    simdi = time.time(); bir = SOHBET.pop("biriken", None); SOHBET.pop("onceki", None)  # dökülürken söylenen (biriktirilen) kaydın sonuna
    with AKIS["kilit"]: AKIS.update(pcm=bytearray(pcm) + (bir or b""), kesik=0, sira=0, metin={}, iz={}, bekleyen=0)
    SOHBET.update(dusunme={"t": simdi, "metin": metin}, durak=None, bekle=None, t_ses=simdi, uyari=False)
    print(f"SOHBET: söz düşünme sözüyle bitti (\"…{' '.join(metin.split())[-30:]}\") — gönderilmedi, dinleme sürüyor")
    return True
def _sohbet_dusunme_gonder(metin):  # düşünme sözünden sonra SOHBET_DUSUNME_SN sessizlik: söz olduğu gibi Claude'a
    _akis_sifirla(); tur = {"t_birak": time.time(), "t_metin": time.time(), "metin": "", "tampon": "", "kaynak": "sohbet"}; _KS["tur"] = tur
    print(f"SOHBET: düşünme sözünden sonra {SOHBET_DUSUNME_SN:.0f} sn sessizlik — söz olduğu gibi gidiyor")
    threading.Thread(target=_konus_sor, args=(metin, tur), daemon=True).start()
def sohbet_metin(metin):  # konus_ses'in yazıya dökülmüş metni: sohbeti kapatan söz mü (True: Claude'a gitmez)
    if not SOHBET["acik"] or not SOHBET_KAPAT_RX.match(metin or ""): return False
    sohbet_kapat("kullanıcı: " + " ".join(metin.split())[:40], _t("Görüşürüz.", "Talk soon.")); return True
