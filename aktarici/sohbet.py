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
# Yakın ses kapısı — ÖLÇÜM KİPİ (v0.80.7, kullanıcı 18 Ekim: kalabalıkta arka plan konuşması soru oluyor; ses izi fısıltıda/yüksek seste tanımıyor). Düzeye
# bakan kapı: arka plan düzeyi = son SOHBET_ARKA_SN'nin pencere düzeylerinin SOHBET_ARKA_YUZDE dilimi; pencere "yakın ses" = arka planın KAT katından yüksek.
# Benzetim (scratchpad, 19 Ekim): kat 4'te kullanıcı arka plandan ≥ 6 dB yüksekse turunun %58–72'si, yalnız arka plan turunun %28'i geçer; eşit düzeyde
# ayırmaz (MacBook mikrofonu masadayken olası). Gerçek ortamdaki farkı bilmediğimiz için şimdilik hiçbir şey engellenmez: her turda günlüğe + canli/sohbet-kapi.jsonl
# (yalnız sayılar) — eşik bu veriyle seçilecek.
SOHBET_ARKA_SN, SOHBET_ARKA_YUZDE, SOHBET_KAPI_KATLAR, SOHBET_KAPI_ORAN = 30.0, 0.3, (3.0, 4.0), 0.45
def _kapi_olc(pen, esik0):  # sohbet_parca: ham pencere düzeyleri → arka plan geçmişi + tur sayaçları
    arka = SOHBET.setdefault("arka", collections.deque(maxlen=int(SOHBET_ARKA_SN * WH_SR * 2 / AKIS_PENCERE)))
    if len(arka) >= 40:
        a = sorted(arka)[int(len(arka) * SOHBET_ARKA_YUZDE)]; o = SOHBET.setdefault("kapi", {"ham": 0, "yakin": [0] * len(SOHBET_KAPI_KATLAR), "arka": [], "kon": []})
        o["arka"].append(a)
        for x in pen:
            if x < esik0: continue
            o["ham"] += 1; o["kon"].append(x)
            for i, k in enumerate(SOHBET_KAPI_KATLAR):
                if x >= max(esik0, a * k): o["yakin"][i] += 1
    arka.extend(pen)
def _giris_turu():  # varsayılan girişin bağlantı türü: yerleşik (MacBook) / bluetooth (kulaklık) / usb / sanal / ? — kapı verisinde mikrofonları ayırmak için
    if os.environ.get("SUFLOR_TEST_BASLAT"): return "deneme"
    try:
        g = _ca_ozellik(1, "dIn ")
        t = struct.pack(">I", _ca_ozellik(g, "tran") or 0).decode("latin-1") if g else ""
        return {"bltn": "yerleşik", "blue": "bluetooth", "blea": "bluetooth", "usb ": "usb", "virt": "sanal"}.get(t, t.strip() or "?")
    except Exception: return "?"
def _kapi_yaz(sonuc):  # tur bitti (sonuc: gonderildi | ...) → ölçüm satırı; sayaçlar sıfırlanır
    o = SOHBET.pop("kapi", None)
    if not o or o["ham"] < 8: return
    arka = sorted(o["arka"])[len(o["arka"]) // 2] if o["arka"] else 0; kon = sorted(o["kon"])[len(o["kon"]) // 2]
    fark = 20 * math.log10(kon / arka) if arka > 0 and kon > 0 else None
    oran = [round(y / o["ham"], 2) for y in o["yakin"]]; i4 = SOHBET_KAPI_KATLAR.index(4.0) if 4.0 in SOHBET_KAPI_KATLAR else -1
    karar = "geçerdi" if oran[i4] >= SOHBET_KAPI_ORAN else "keserdi"
    print(f"SOHBET ÖLÇÜM: konuşma {o['ham'] * AKIS_PENCERE / 2 / WH_SR:.1f} sn · arka plan {arka:.0f} · konuşma {kon:.0f}" + (f" ({fark:+.1f} dB)" if fark is not None else "") +
          " · yakın oran " + ", ".join(f"kat {k:g} %{v * 100:.0f}" for k, v in zip(SOHBET_KAPI_KATLAR, oran)) + f" → kapı (kat 4, %{SOHBET_KAPI_ORAN * 100:.0f}) {karar} · {sonuc}")
    satir = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "sn": round(o["ham"] * AKIS_PENCERE / 2 / WH_SR, 1), "arka": round(arka), "kon": round(kon),
             "fark_db": round(fark, 1) if fark is not None else None, "oran": dict(zip([f"{k:g}" for k in SOHBET_KAPI_KATLAR], oran)), "karar": karar, "sonuc": sonuc,
             "mikrofon": _giris_turu()}
    try:
        with LOCK: write([(os.path.join(BASE, "sohbet-kapi.jsonl"), json.dumps(satir, ensure_ascii=False) + "\n")])
    except Exception as e: print(f"SOHBET ÖLÇÜM: yazılamadı ({e.__class__.__name__})")
SOHBET_DUSUNME_RX = re.compile(r"(\b(nasıl (desem|diyeyim|söylesem|anlatsam)|yani|şey|hani|işte|şöyle( ki)?|mesela|aslında|bir saniye|dur bir|bekle|ve|ama|fakat|çünkü|ki|veya|ya da|ile|"
                               r"how (do i|should i) (say|put)|i mean|like|so|and|but|because|um+|uh+)|\b(e+|ı+|hm+|em+))\W*$", re.I)
SOHBET_KAPAT_RX = re.compile(r"^\W*(tamam,?\s*)?(teşekkür(ler| ederim)|sağ ?ol(un)?|kapat|sohbeti kapat|bu kadar|görüşürüz|thanks?( you)?|that'?s all|goodbye|bye)\W*$", re.I)
SOHBET_BEKLE_RX = re.compile(r"\b(bekle|dur bir|bir saniye|bir dakika|şey|hold on|wait|one sec(ond)?)\W*$", re.I)
def ses_caliyor():  # v0.77.2: toplantıya söyle okuması da sayılır (ayrı süreçle çalar; sohbet onu mikrofondan cevap sanıyordu)
    if os.environ.get("SUFLOR_TEST_BASLAT"): return time.time() < SES.get("test_bit", 0) or ts_caliyor()
    with SES_K: q = bool(SES["q"]); p = SES.get("p"); m = SES.get("mesgul_t") or 0  # v0.127: işçi parçayı aldı, ilk ses bekleniyor (Gemini ~0,6 sn) — o arada da çalıyor sayılır
    return q or bool(p and p.poll() is None) or 0 < time.time() - m < SES_MESGUL_SN or ts_caliyor()
def _okuma_izle(simdi):  # okumanın başladığı an (araya girme koruması SOHBET_KORU_SN buna göre); bekçi ve parça ikisi de çağırır
    tur = _KS["tur"]; okuma = ses_caliyor() and (tur is None or bool(tur.get("t_ses")))  # tur bittiyse kuyruktaki son cümleler okunuyor
    if okuma and not SOHBET["t_okuma"]: SOHBET["t_okuma"] = simdi
    if not okuma: SOHBET["t_okuma"] = 0.0
    return okuma
# v0.54.3 (kullanıcı, 16 Ekim: "sohbette miyim, kapalı mı anlamıyorum"): son kapanış nedeni 60 sn panoda görünür (aktarıcı kendisi kapatınca iz kalsın)
# v0.74.0 (kullanıcı, 18 Ekim: "ara yolu uygula"): toplantı dışında kulaklık takılıysa panonun mikrofon düğmesi Sohbet'i açar (bir dokunuş); kulaklık yoksa ya da
# toplantıda basılı tut. Pano bunun için "kulaklik"ı okur (Core Audio, 3 sn önbellek; toplantıda sorulmaz).
_SOH_KUL = {"t": 0.0, "v": False}
def _sohbet_kulaklik():
    if toplanti_var(): return False
    if time.time() - _SOH_KUL["t"] > 3: _SOH_KUL.update(t=time.time(), v=bool(kulaklik()))
    return _SOH_KUL["v"]
def _sohbet_ky_view():  # yerel ses yolu tanısı (bağlı, vpio, mik, düşme sayısı); yalnız ayar yerel_konus açıkken görünür — kapalıyken /status aynı. Beta veri paketine girmez
    f = globals().get("ky_etkin"); g = globals().get("ky_view")
    try: return {"ky": g()} if f and g and f() else {}
    except Exception: return {}
def sohbet_view():
    if SOHBET["acik"]:
        dv = SOHBET.get("devam")  # devam penceresi (bas-konus.py konus_devam_pencere): kalan sn — panoda/menüde "dinliyor (kısa)" göstergesi için
        return {"acik": True, "bekle": SOHBET["bekle"], "okuyor": ses_caliyor(), "kulaklik": True, "yerel": bool(SOHBET.get("yerel")), **_sohbet_ky_view(), **({"ag": ag_view()} if SOHBET.get("yerel") else {}), **({"devam": max(0, round(dv["sn"] - (time.time() - max(SOHBET["t_ses"], SOHBET["t_mesgul"])), 1))} if dv else {})}
    k = SOHBET.get("kapanis")
    return {"acik": False, "kulaklik": _sohbet_kulaklik(), **_sohbet_ky_view(), **({"kapandi": k["neden"], "kapandi_sn": round(time.time() - k["t"])} if k and time.time() - k["t"] < 60 else {})}
def _ky_islev(ad): return globals().get(ad)  # yerel-konus.py yoksa (yalıtılmış yükleme) None
def _sohbet_yerel_karar(kul):  # (yerel yol kullanılsın mı, vpio) — Adım 4 (12 Kasım): yerel yol hazır, toplantı yok, gizli değil: kulaklıkta VPIO kapalı, hoparlörde VPIO açık
    # (hoparlörde yalnız ayar yerel_konus_hoparlor true iken; varsayılan false). Yerel yol hazır değilse (ayar kapalı, yardımcı yok, düşmüş) bugünkü yol aynen.
    hazir = _ky_islev("ky_hazir"); gizli = _ky_islev("gizli_acik")
    try:
        if not (hazir and hazir()) or toplanti_var() or (gizli and gizli()): return False, False
    except Exception: return False, False
    if kul: return True, False
    return (True, True) if AYAR.get("yerel_konus_hoparlor") is True else (False, False)
def sohbet_basla():
    if not AYAR.get("konusma", True): return {"ok": False, "err": _t("Konuşma kapalı (ayar konusma)", "Voice is off (setting konusma)")}
    if toplanti_var(): return {"ok": False, "err": _t(f"Toplantı sürerken sohbet kapalı — “{asistan_ad()}, …” de ya da basılı tut", "Conversation is off during a meeting — say “Claude, …” or hold to talk")}
    kul = kulaklik(); yerel, vpio = _sohbet_yerel_karar(kul)
    err_kul = {"ok": False, "err": _t("Sohbet yalnız kulaklıkla (hoparlörde Suflor kendi sesini duyar) — basılı tutarak sor", "Conversation needs headphones (on speakers Suflor hears itself) — hold to talk instead")}
    if not kul and not yerel: return err_kul
    if SOHBET["acik"]: return {"ok": True, "yerel": bool(SOHBET.get("yerel"))}
    mik = False
    if yerel:  # mikrofon çalmadan ÖNCE açılır (çalarken mik_ac motoru yeniden kurar, çalan akış kesilir); motor sohbet boyunca açık kalır
        mik = bool(_ky_islev("ky_mik_ac")(vpio))
        if not mik:
            if not kul: return err_kul  # hoparlörde yerel yol açılamadı: bugünkü davranış
            yerel = False  # kulaklıkta yerel yol açılamadı: bugünkü yol (pano mikrofonu)
    r = konus_basla()
    if not r.get("ok"):
        if mik: _ky_islev("ky_mik_kapat")("sohbet açılmadı")
        return r
    simdi = time.time()
    SOHBET.pop("biriken", None); SOHBET.pop("onceki", None); SOHBET.pop("vpio_bekle", None); SOHBET.pop("yerel_yok", None); SOHBET.pop("kesik", None); SOHBET.pop("son_gonder", None)
    with SOHBET["kilit"]: SOHBET.update(acik=True, t_ac=simdi, t_ses=simdi, t_mesgul=simdi, uyari=False, durak=None, bekle=None, kesme_sn=0.0, sira=SOHBET["sira"] + 1, yerel=mik, vpio=bool(mik and vpio), hoparlor=bool(mik and vpio), aygit_say=(_ky_islev("KY") or {}).get("aygit_say", 0))
    _konus_kur(durum="dinliyor", soru=None, cevap="", hata=None, olcum=None, kaynak="sohbet")
    if float(AYAR.get("hihi_tur_esik", TUR_ESIK)) > 0: threading.Thread(target=tur_baslat, daemon=True).start()
    threading.Thread(target=_sohbet_bekci, args=(SOHBET["sira"],), daemon=True).start()
    if mik: threading.Thread(target=ag_hazirla, daemon=True).start()  # Adım 5: Silero + kısa söz tanıyıcı (yerel_araya_girme kapalıysa hiçbiri)
    print("SOHBET: açıldı" + (f" (yerel ses yolu, {'hoparlör — VPIO açık' if vpio else 'kulaklık — VPIO kapalı'})" if mik else "")); return {"ok": True, "yerel": mik}
def _sohbet_yerel_kapat(sira, hemen):  # sohbet bitti: yerel mikrofon kapanır. Okuma sürüyorsa bitmesi beklenir (mik_kapat motoru yeniden kurar, çalan akışı keser); bu arada yeni sohbet açıldıysa dokunulmaz
    kapat = _ky_islev("ky_mik_kapat")
    if not kapat: return
    if not hemen:
        t0 = time.time(); time.sleep(0.6)
        while ses_caliyor() and time.time() - t0 < 30: time.sleep(0.3)
    if not SOHBET["acik"] and SOHBET["sira"] == sira: kapat("sohbet kapandı")
def sohbet_bas_tut_oncesi():  # bas-tut (komut basla) öncesi: yerel mikrofon kapanır (üçüncü kapatıcı; Chrome mikrofonu açınca yardımcı Chrome'u toplantı sanıp VPIO'yu kapatır). Yerel sohbet/devam penceresi sessizce biter
    if SOHBET["acik"] and SOHBET.get("yerel"): sohbet_kapat("devam: bas-tut", hemen=True)
    else:
        ky = _ky_islev("KY"); kapat = _ky_islev("ky_mik_kapat")
        if ky and kapat and ky["mik"]: kapat("bas-tut")
def sohbet_kapat(neden, soz=None, hemen=False):
    with SOHBET["kilit"]:
        if not SOHBET["acik"]: return
        yerel = bool(SOHBET.get("yerel")); hop = bool(SOHBET.get("hoparlor")); sira = SOHBET["sira"]; SOHBET.update(yerel=False, vpio=False, hoparlor=False)
        SOHBET.update(acik=False, bekle=None, kapanis=None if neden.startswith("devam") else {"neden": "kullanici" if neden.startswith("kullanıcı") else {"toplantı başladı": "toplanti", "kulaklık çıktı": "kulaklik"}.get(neden, neden), "t": time.time()})  # devam penceresi sessiz kapanır: panoda "Sohbet kapandı" notu çıkmaz
        SOHBET.pop("biriken", None); SOHBET.pop("onceki", None); SOHBET.pop("devam", None)
    if not _KS["tur"]: _akis_sifirla(); _konus_kur(durum="hazir" if konus_canli() else "kapali")
    if yerel: threading.Thread(target=_sohbet_yerel_kapat, args=(sira, hemen or neden in ("toplantı başladı", "gizli toplantı")), daemon=True).start()
    if "_agt_kapat" in globals(): _ag_sifirla(); threading.Thread(target=_agt_kapat, daemon=True).start()  # Adım 5: kısa söz tanıyıcı sohbetle kapanır
    if soz: seslendir(soz, kuyruk=True)
    _ag_olay("sohbet_sure", sure_ms=round((time.time() - SOHBET["t_ac"]) * 1000), yerel=yerel, hoparlor=hop)
    print(f"SOHBET: kapandı ({neden}, {time.time() - SOHBET['t_ac']:.0f} sn)")
def _sohbet_yerel_denetle(simdi, kul):  # Adım 4: yerel yolda kulaklık/hoparlör kararı (aygit_degisti olayında ya da 5 sn'de bir) ve bağlantı denetimi. True: sohbet kapandı
    ky = _ky_islev("KY")
    if not ky: return False
    if kul is not None:
        vpio = not kul
        if vpio and AYAR.get("yerel_konus_hoparlor") is not True: sohbet_kapat("kulaklık çıktı", _t("Kulaklık çıktı, sohbeti kapattım.", "Headphones out, conversation closed.")); return True
        if vpio != SOHBET.get("vpio"): SOHBET["vpio_bekle"] = vpio  # okuma bitince uygulanır (mik_ac çalan akışı keser)
    vb = SOHBET.get("vpio_bekle")
    if vb is not None and not ses_caliyor() and not _KS["tur"]:
        SOHBET.pop("vpio_bekle", None)
        if _ky_islev("ky_mik_ac")(vb): SOHBET.update(vpio=vb, hoparlor=vb); print(f"SOHBET: aygıt değişti — VPIO {'açıldı (hoparlör)' if vb else 'kapandı (kulaklık)'}")
    if not ky["mik"] and ky["devam_vpio"] is None:  # bağlantı koptu / mikrofon düştü: yardımcı dönünce mik_ac yeniden; 8 sn dönmezse sohbet biter (pano mikrofonu açılmamış, ses gelmez)
        t = SOHBET.setdefault("yerel_yok", simdi)
        if _ky_islev("ky_mik_ac")(bool(SOHBET.get("vpio"))): SOHBET.pop("yerel_yok", None); print("SOHBET: yerel mikrofon yeniden açıldı")
        elif simdi - t > 8: sohbet_kapat("yerel ses koptu", _t("Ses bağlantısı koptu, sohbeti kapattım.", "Audio link dropped, conversation closed.")); return True
    else: SOHBET.pop("yerel_yok", None)
    return False
def _sohbet_bekci(sira):
    k_t = 0.0
    while SOHBET["acik"] and SOHBET["sira"] == sira:
        time.sleep(0.5); simdi = time.time(); _okuma_izle(simdi)
        if toplanti_var(): sohbet_kapat("toplantı başladı"); return
        yerel = bool(SOHBET.get("yerel")); ky = _ky_islev("KY"); ag = ky.get("aygit_say", 0) if ky and yerel else 0
        if simdi - k_t > 5 or (yerel and ag != SOHBET.get("aygit_say")):  # aygit_degisti olayı beklemeden denetler
            k_t = simdi; SOHBET["aygit_say"] = ag; kul = kulaklik()
            if yerel:
                if _sohbet_yerel_denetle(simdi, kul): return
            elif not kul: sohbet_kapat("kulaklık çıktı", _t("Kulaklık çıktı, sohbeti kapattım.", "Headphones out, conversation closed.")); return
        elif yerel and _sohbet_yerel_denetle(simdi, None): return
        d = SOHBET.get("dusunme")
        if d and not _KS["tur"] and SOHBET["t_ses"] - d["t"] < 0.3 and simdi - d["t"] >= SOHBET_DUSUNME_SN: SOHBET.pop("dusunme", None); _sohbet_dusunme_gonder(d["metin"])
        if _KS["tur"] or (ses_caliyor() and not SOHBET["uyari"]): SOHBET["t_mesgul"] = simdi; continue
        bos = simdi - max(SOHBET["t_ses"], SOHBET["t_mesgul"])
        dv = SOHBET.get("devam")
        if dv and bos >= dv["sn"]: sohbet_kapat("devam penceresi bitti"); return  # sessiz kapanır (ses yok, "Buradayım" yok)
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
    return _sohbet_parca_govde(pcm, p)
def _sohbet_parca_govde(pcm, p):  # iç gövde (12 Kasım, Aşama 2 Adım 2): pano/menü sohbet_parca'dan ve yerel yardımcının mikrofon öbeklerinden (yerel-konus.py) aynı yol; p: {"pcm": base64} (konus_parca'ya gider)
    if not SOHBET["acik"]: return {"ok": False, "kapali": True}
    simdi = time.time(); pen = _pencereler(pcm); esik = AKIS.get("esik") or 400
    try: _kapi_olc(pen, esik)  # v0.80.7: ölçüm kipi, davranışı değiştirmez
    except Exception as e: print(f"SOHBET ÖLÇÜM: hata {e.__class__.__name__}")
    konusma = sum(x >= esik for x in pen) * AKIS_PENCERE / 2 / WH_SR
    if konusma >= 0.15: SOHBET.update(t_ses=simdi, uyari=False)
    _olcum_izle(simdi, konusma)
    tur = _KS["tur"]
    # v0.54.3 (S70, kullanıcı 16 Ekim: "arka plan seslerinden sürekli kesiliyor ve susuyor"): araya girme varsayılan kapalı (ayar sohbet_araya_girme) — cevap
    # sonuna kadar okunur, okuma sırasında gelen ses atılır (arka plan sesi okumayı kesmez, sonraki soru da olmaz); Claude düşünürken söylenen yine biriktirilir.
    # Adım 5: yerel yolda araya girme (ag_etkin) açıksa okurken karar ag_obek'in (100 ms öbek, Silero + kısa söz tanıma); eski düzey kuralı bu sürede çalışmaz
    if (not AYAR.get("sohbet_araya_girme") or SOHBET.get("hoparlor") or ag_etkin()) and _okuma_izle(simdi):  # hoparlörde (Adım 4) araya girme ayardan bağımsız kapalı: yankı kalıntısı okumayı kesmesin
        if time.time() - SOHBET.get("ag_t", 0) < 2.0 and SOHBET.get("biriken") is not None: SOHBET["biriken"] += pcm; return {"ok": True, "mesgul": True}  # araya girme az önce kesti, okuma bitişi henüz görünmedi
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
        with AKIS["kilit"]: AKIS.update(pcm=bytearray(bir), kesik=0, sira=0, metin={}, bekleyen=0, nesil=AKIS.get("nesil", 0) + 1)  # v0.98.1: yoldaki parça karışmasın
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
    if konusma < 0.4: SOHBET.update(durak=None, bekle=None); SOHBET.pop("kapi", None); return
    if n >= KONUS_EN_UZUN_SN - 3: return _sohbet_gonder(b, n, sessiz)  # bir dakikalık kayıt tavanına yaklaşınca duraksamasız da tur kapanır
    if sessiz < SOHBET_SESSIZ_SN: SOHBET.update(durak=None, bekle=None); return
    durak = (len(pen) - k) * AKIS_PENCERE  # son konuşma penceresinin sonu: pencereler kaydın başına hizalı, parça boyu ne olursa olsun duraksama boyunca sabit
    if SOHBET["durak"] != durak:  # yeni duraksama: bekleme süresini seç (v0.49.5: duraksama başına bir kez — önce len(b)'ye göreydi, her parçada kayıyordu)
        onara_isit()  # v0.79.1: tur kapanmadan ön aramanın dizini bellekte olsun
        e = float(AYAR.get("hihi_tur_esik", TUR_ESIK)); p = tur_olasilik(b[:durak + int(0.3 * WH_SR * 2)]) if e > 0 else None
        bek = SOHBET_MODELSIZ_SN if p is None else SOHBET_KISA_SN if p >= e else SOHBET_UZUN_SN
        with AKIS["kilit"]: son = str(AKIS["metin"].get(AKIS["sira"] - 1) or "") if AKIS["sira"] else ""
        if son and SOHBET_BEKLE_RX.search(son): bek = max(bek, SOHBET_BEKLE_SN)
        SOHBET.update(durak=durak, bekle=bek)
        print(f"SOHBET: duraksama — tur sonu {'yok' if p is None else f'{p:.2f}'}, {bek:.1f} sn beklenecek")
    if sessiz >= SOHBET["bekle"]: return _sohbet_gonder(b, n, sessiz)
    with AKIS["kilit"]:  # v0.80.4: duraksamaya kadarki ses dökülmüşse ön arama tur sonunu beklemeden başlar (soru aynı kalırsa sonuç hazır olur)
        hazir = AKIS["sira"] and AKIS["bekleyen"] == 0 and AKIS["kesik"] >= durak
        metin = " ".join(" ".join(str(AKIS["metin"].get(i) or "").split()) for i in range(AKIS["sira"])).strip() if hazir else ""
    if metin and len(metin.split()) >= 3 and not SOHBET_KAPAT_RX.search(metin) and not SOHBET_DUSUNME_RX.search(metin):
        try: onara_onceden(metin)
        except Exception as e: print(f"SOHBET: önceden ön arama başlatılamadı ({e.__class__.__name__})")
def _sohbet_gonder(b, n, sessiz):
    SOHBET.update(durak=None, bekle=None, son_gonder=time.time()); SOHBET.pop("dusunme", None)
    print(f"SOHBET: tur bitti ({n:.1f} sn kayıt, {sessiz:.1f} sn sessizlik)"); _kapi_yaz("tur bitti")
    r = konus_ses({"pcm": base64.b64encode(b).decode(), "t_soz_bitis": SOHBET.get("t_ses")})  # t_ses = son konuşma parçasının geldiği an (ölçüm)
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
    with AKIS["kilit"]: AKIS.update(pcm=bytearray(pcm) + (bir or b""), kesik=0, sira=0, metin={}, iz={}, bekleyen=0, nesil=AKIS.get("nesil", 0) + 1)
    # v0.92.1: söz dökülürken devamı söylendiyse (biriken seste konuşma) yeni konuşma var sayılır — yoksa tur sonu bekçisi yalnız ilk yarıyı 4 sn sonra
    # gönderiyordu, devamı kayboluyordu (test/sohbet.py "nasıl desem"; yeni konuşma ölçütü yalnız sonradan gelen parçaydı)
    devam = bool(bir) and sum(x >= (AKIS.get("esik") or 400) for x in _pencereler(bytes(bir))) * AKIS_PENCERE / 2 / WH_SR >= 0.15
    SOHBET.update(dusunme={"t": simdi - (1.0 if devam else 0.0), "metin": metin}, durak=None, bekle=None, t_ses=simdi, uyari=False)
    print(f"SOHBET: söz düşünme sözüyle bitti (\"…{' '.join(metin.split())[-30:]}\") — gönderilmedi, dinleme sürüyor")
    return True
def _sohbet_dusunme_gonder(metin):  # düşünme sözünden sonra SOHBET_DUSUNME_SN sessizlik: söz olduğu gibi Claude'a
    _akis_sifirla(); tur = {"t_birak": time.time(), "t_metin": time.time(), "metin": "", "tampon": "", "kaynak": "sohbet", "tur_turu": "devam" if SOHBET.get("devam") else "sohbet", "t_soz_bitis": SOHBET.get("t_ses")}; _KS["tur"] = tur
    print(f"SOHBET: düşünme sözünden sonra {SOHBET_DUSUNME_SN:.0f} sn sessizlik — söz olduğu gibi gidiyor")
    threading.Thread(target=_konus_sor, args=(metin, tur), daemon=True).start()
def sohbet_metin(metin):  # konus_ses'in yazıya dökülmüş metni: sohbeti kapatan söz mü (True: Claude'a gitmez)
    if not SOHBET["acik"]: return False
    if SOHBET.get("devam") and DEVAM_KAPAT_RX2.match(metin or ""): sohbet_kapat("devam: kapanış sözü (" + " ".join(metin.split())[:30] + ")"); return True  # "tamam / teşekkürler": pencere sessizce kapanır, Claude'a gitmez
    if not SOHBET_KAPAT_RX.match(metin or ""): return False
    sohbet_kapat("kullanıcı: " + " ".join(metin.split())[:40], _t("Görüşürüz.", "Talk soon.")); return True
# --- Yerel yolda araya girme ve kısa söz tanıma (Konuş Aşama 2, Adım 5; 12 Kasım 2026) --------------------------------------------------------
# Yalnız sohbet yerel ses yolundayken (SOHBET["yerel"], yardımcının 100 ms mikrofon öbekleri) ve asistan okurken. Ayar yerel_araya_girme: kapali | dur
# (varsayılan: yalnız durdurma sözü keser) | tam (başka söz de keser). Kapalıyken ya da yerel yol yokken bugünkü davranış aynen (kulaklıkta sohbet_araya_girme
# ile eski düzey kuralı, hoparlörde araya girme yok). Akış: öbek → Silero (vad.py) konuşma başı → başından 0,25 sn önceden tampon → iki tanıyıcı:
#   (1) turkish-stt akış tanıyıcısı (tstt-golge-isci.py'nin ayrı örneği, işlemci; ara metin ~0,3 sn adımla) — hızlı yol;
#   (2) AG_TANI_SN (0,35 sn) dolunca kısa parça Whisper işçisine, kuyruğun başına (wh_one_al; toplantı yokken kuyruk boş, Konuş akış parçaları da okurken gitmez).
# Ölçüm (12 Kasım, kayit3 VPIO, Silero başına göre): whisper.cpp + Core ML tanıma p50 0,49 sn (parça uzunluğundan bağımsız: kodlayıcı hep 30 sn işler;
# -ac Core ML'yi bozuyor, Core ML'siz -ac 512 0,32 sn ama "dur" yanlış yazılıyor) → "dur" tepkisi ~0,9 sn; tstt ara metni "Dur" başından ~0,6 sn sonra (2/2),
# "Bekle" ~0,9 sn, öbek işi ~11 ms. Kural: ilk karar veren kazanır (tstt çoğunlukla önce). Sınıf (_ag_sinif):
#   dur  — ASISTAN_DUR_RX (sus dahil; tek sözcükte bir harf yanlışına dayanıklı: "Bekte", "Tur") → hemen kes (koruma süresi yok), ses AG_DUR_DEVAM_SN'yi
#          geçerse ("Dur, şunu sor…") söz yeni turun başı olur, geçmezse atılır ("dur" Claude'a soru olarak gitmez);
#   onay — hı hı, evet, tamam, aynen, peki, doğru, anladım (ONAY_SOZ ile) → kesmez; onay/dur sözünün başı ("Ev", "Bek") karar bekler;
#   başka — kip tam'da ≥ araya_girme_sn_hoparlor (0,6) / _kulaklik (0,3) kesintisiz konuşma (Silero) ve okuma başından ≥ koruma (hoparlörde 3 sn: VPIO uyum
#          geçişi, Adım 0a; kulaklıkta SOHBET_KORU_SN) → kes, söz `biriken` ile yeni tur;
#   yankı — tanınan sözcükler okunan metinde (SES["simdi"] + son okunanlar + KENDI_SES, kök benzerliği) → sayılmaz.
AG_TANI_SN, AG_ON_SN, AG_DUR_DEVAM_SN, AG_KORU_HOP_SN, AG_OKUNAN_SN = 0.35, 0.25, 1.2, 3.0, 6.0
AG_ADAY_SN, AG_ADAY_EN_COK_SN = 1.6, 10.0  # konuşma bitse de söz adayı başından AG_ADAY_SN'ye dek yaşar (kısa "dur"un tanıması Silero'nun "bitti"sinden sonra gelir; tstt son parçayı ardından gelen sesle verir)
AG_ONAY = {"hı", "hıhı", "hıhıı", "hıı", "hm", "hmm", "mhm", "mm", "ımm", "evet", "tamam", "aynen", "peki", "doğru", "anladım", "he", "hee", "haa", "ha", "olur", "tabii", "tabi",
           "yes", "yeah", "okay", "ok", "right", "sure", "uh", "huh"}
AG_DUR_SOZ = ("dur", "sus", "yeter", "kes", "bekle", "stop", "wait")
AG_BOS_RX = re.compile(r"altyaz|izlediğiniz için|abone ol|^\W*(m\.?\s*k\.?)+\W*$", re.I)
ARAYA = {"acik": False, "aday": None, "tut": None, "n": 0, "on": collections.deque(maxlen=6), "t0": 0.0, "okunan": collections.deque(maxlen=8), "sira": 0, "kilit": threading.RLock(), "say": {}}
# Ölçüm olayları (Aşama 2 Adım 6): canli/sohbet-olay.jsonl, METİNSİZ — yalnız tür, zaman, süre, sınıf, kaynak. Beta veri paketine girmez; okuyan: olcum.py sohbet.
#   araya_girme  — okuma kesildi (sinif dur|baska, kaynak tstt|whisper, tepki_ms söz başından karara; onaydi: karardan önce onay sanılmıştı)
#   onay_gecti   — okurken kısa onay sözü ("hı hı") duyuldu ve okumayı kesmedi
#   kacan_aday   — okurken Silero konuşma gördü ama tanıma karar çıkaramadı (tanınmadı/boş/yarım)
#   olasi_yanlis — "başka söz" kesmesinden sonra OLCUM_YANLIS_SN içinde kullanıcıdan söz gelmedi (öksürük, arka plan sesi)
#   bolunen_soru — tur söz bitmeden kapandı: soru gönderildikten sonra OLCUM_BOLUNEN_SN içinde konuşma sürdü (gecikme_ms)
#   yerel_dusme  — yerel ses yolu bugünkü yola düştü (yerel-konus.py)
#   sohbet_sure  — sohbet kapandı (sure_ms, yerel, hoparlor): dakika başına oranların paydası
OLCUM_YANLIS_SN, OLCUM_BOLUNEN_SN = 3.0, 2.0
def _ag_olay(olay, **alan):  # ölçüm olayı; yazılamazsa sessizce geçer (ses hattını etkilemez)
    try: _ky_gunluk(olay, **{"hoparlor": bool(SOHBET.get("hoparlor")), **alan})
    except Exception: pass
def _olcum_izle(simdi, konusma):  # her mikrofon parçasında: olasi_yanlis (kesmeden sonra söz gelmedi) ve bolunen_soru (gönderimden hemen sonra konuşma sürdü)
    k = SOHBET.get("kesik")
    if k:
        if konusma >= 0.15: SOHBET["kesik"] = None
        elif simdi - k["t"] >= OLCUM_YANLIS_SN: SOHBET["kesik"] = None; _ag_olay("olasi_yanlis", sinif=k["sinif"], kaynak=k["kaynak"], tepki_ms=k["tepki_ms"])
    g = SOHBET.get("son_gonder")
    if g:
        if simdi - g > OLCUM_BOLUNEN_SN: SOHBET["son_gonder"] = None
        elif konusma >= 0.3 and not ses_caliyor(): SOHBET["son_gonder"] = None; _ag_olay("bolunen_soru", gecikme_ms=round((simdi - g) * 1000))
def ag_kip():
    v = str(AYAR.get("yerel_araya_girme") or "dur").strip().lower()
    return v if v in ("kapali", "dur", "tam") else "dur"
def ag_esik(): return float(AYAR.get("araya_girme_sn_hoparlor", 0.6) if SOHBET.get("hoparlor") else AYAR.get("araya_girme_sn_kulaklik", 0.3))
def ag_etkin():  # yerel sohbet açık, kip kapalı değil, Silero hazır (değilse bugünkü kural sürer)
    return bool(SOHBET["acik"] and SOHBET.get("yerel")) and ag_kip() != "kapali" and VAD.get("durum") == "hazir"
def _ag_norm(t): return " ".join(re.sub(r"[^\w\s]", " ", str(t or "").replace("İ", "i").replace("I", "ı").lower()).split())
def _ag_bir_harf(a, b):  # tek düzeltme uzaklığı (değiştirme/ekleme/silme) ≤ 1
    if a == b: return True
    if abs(len(a) - len(b)) > 1: return False
    if len(a) == len(b): return sum(x != y for x, y in zip(a, b)) == 1
    k, u = (a, b) if len(a) < len(b) else (b, a)
    return any(u[:i] + u[i + 1:] == k for i in range(len(u)))
def _ag_adsiz(metin):  # baştaki kişilik adı atılır ("Marvin, dur"), son cümle alınır (okuma_dur_soz gibi)
    c = [x for x in re.split(r"(?<=[.!?…])\s+", " ".join(str(metin or "").split())) if x.strip()]
    if not c: return ""
    try: adlar = {sade(x) for k in kisilikler() for x in k.get("hitap") or []}
    except Exception: adlar = set()
    sw = c[-1].split()
    while sw and sade(sw[0].strip(",.;:!?…")) in adlar: sw = sw[1:]
    return " ".join(sw)
def _ag_sinif(metin, ara=False):  # → dur | onay | on (onay/dur sözünün başı, karar bekler) | baska | bos. ara: tstt ara metni (büyüyerek gelir)
    son = _ag_adsiz(metin); n = _ag_norm(son)
    if not n or AG_BOS_RX.search(str(metin or "")): return "bos"
    if ASISTAN_DUR_RX.match(son) or ASISTAN_DUR_RX.match(n): return "dur"
    w = n.split()
    if len(w) == 1 and (w[0] == "tur" or any(len(d) >= 4 and _ag_bir_harf(w[0], d) for d in AG_DUR_SOZ)): return "dur"  # Whisper/tstt kısa parçada "Bekte", "Pekle", "Tur"
    onay2 = globals().get("ONAY_SOZ") or set()  # otonom.py (sade biçim)
    if all(x in AG_ONAY or sade(x) in onay2 for x in w) or n.replace(" ", "") in AG_ONAY: return "onay"
    if ara and len(w) <= 2 and len(w[-1]) <= 4 and any(o.startswith(w[-1]) for o in tuple(AG_ONAY) + AG_DUR_SOZ + ("bir",)) and all(x in AG_ONAY for x in w[:-1]): return "on"
    if ara and len(w) <= 3 and w[0] in ("dur", "bir") and ASISTAN_DUR_RX.match(n + " dakika") or (ara and n in ("bir", "bir da", "bir sa", "dur bi", "dur bir")): return "on"  # "bir dakika" yarım
    return "baska"
def _ag_yanki(metin, tam=False):  # tanınan sözcükler az önce okunan metinde mi (kök benzerliği; kişilik adları sayılmaz). tam: durdurma sözü — yalnız aynı sözcük
    # (12 Kasım ölçümü: kök benzerliğinde "dur" önceki cümledeki "durdurup"a benzedi, gerçek "dur" kaçtı; VPIO kalıntısı −74 dBFS, yankı tam sözcük olarak gelir)
    w = [x for x in re.findall(r"\w+", sade(_ag_adsiz(metin))) if len(x) >= 2]
    if not tam: w = [x for x in w if len(x) > 2] or w
    if not w: return False
    simdi = time.time()
    with SES_K: okunan = [str(SES.get("simdi") or "")]
    okunan += [m for t, m in list(ARAYA["okunan"]) if simdi - t < AG_OKUNAN_SN]
    kaynak = [re.findall(r"\w+", sade(etiket_sil(m))) for m in okunan if m]
    try:
        with YANKI_LOCK: kaynak += [list(k[2]) for k in KENDI_SES if k[1] >= simdi - AG_OKUNAN_SN]
    except NameError: pass
    for o in kaynak:
        if not o: continue
        ortak = sum(1 for x in w if any(x == y or (not tam and _kok_ayni(x, y)) for y in o))
        if ortak >= max(1, math.ceil(YANKI_KAPSAM * len(w))): return True
    return False
def _ag_say(ad): ARAYA["say"][ad] = ARAYA["say"].get(ad, 0) + 1
def _ag_sifirla(neden=None):
    with ARAYA["kilit"]: ARAYA.update(acik=False, aday=None, tut=None); ARAYA["on"].clear()
def _ag_okunan_izle():  # okunan cümleler (yankı kıyası için; SES["simdi"] her cümlede değişir)
    with SES_K: m = str(SES.get("simdi") or "")
    if m and (not ARAYA["okunan"] or ARAYA["okunan"][-1][1] != m): ARAYA["okunan"].append((time.time(), m))
def ag_obek(pcm, duvar=None):  # yerel-konus.py _ky_mik_isci her ~100 ms öbekte çağırır → True: öbek araya girmenin (gövdeye gitmez)
    if not ag_etkin():
        if ARAYA["acik"] or ARAYA["tut"]: _ag_sifirla()
        return False
    pcm = bytes(pcm); simdi = time.time(); n_ob = len(pcm) // 2
    duvar = float(duvar) if isinstance(duvar, (int, float)) else simdi - n_ob / WH_SR
    with ARAYA["kilit"]:
        tut = ARAYA["tut"]
        if tut is not None: return _ag_tut(tut, pcm, duvar)
        if not _okuma_izle(simdi):
            if ARAYA["acik"]: _ag_sifirla()
            return False
        if not ARAYA["acik"]:  # okuma başladı: Silero akışı sıfırdan (olay zamanları bu ana göre)
            if not vad_sifirla(): return False
            ARAYA.update(acik=True, aday=None, n=0, t0=duvar, sira=ARAYA["sira"] + 1); ARAYA["on"].clear()
        _ag_okunan_izle()
        bas = ARAYA["n"]; ARAYA["on"].append((bas, pcm)); ARAYA["n"] += n_ob
        r = vad_olasilik(pcm)
        if r is None: return False
        aday = ARAYA["aday"]
        for o in r.get("olay") or []:
            if o.get("o") == "basla":
                ornek = int(float(o.get("t") or 0) * WH_SR / 1000); bas0 = max(0, ornek - int(AG_ON_SN * WH_SR))
                on = b"".join(p_[max(0, bas0 - b_) * 2:] for b_, p_ in ARAYA["on"] if b_ + len(p_) // 2 > bas0)
                aday = ARAYA["aday"] = {"ornek": ornek, "t": ARAYA["t0"] + ornek / WH_SR, "pcm": bytearray(on), "son": ARAYA["n"], "sinif": None, "kaynak": None, "metin": "",
                                     "wh": False, "konusma": True, "no": ARAYA["sira"] * 1000 + len(ARAYA["say"]) + int(simdi * 1000) % 1000, "t_karar": None}
                _agt_besle(aday, on, duvar - (len(on) // 2 - n_ob) / WH_SR, sifirla=True)
            elif o.get("o") == "bitti" and aday is not None:
                aday["konusma"] = False
        if aday is None: return False
        sure = (ARAYA["n"] - aday["ornek"]) / WH_SR
        if aday["son"] < ARAYA["n"] and sure <= AG_ADAY_EN_COK_SN: aday["pcm"] += pcm; aday["son"] = ARAYA["n"]; _agt_besle(aday, pcm, duvar)
        if not aday["wh"] and sure >= AG_TANI_SN:
            aday["wh"] = True; threading.Thread(target=_ag_whisper, args=(aday, bytes(aday["pcm"])), daemon=True).start()
        if not aday["konusma"]:
            if sure >= AG_ADAY_SN:
                _ag_say({None: "taninmadi", "on": "taninmadi", "bos": "taninmadi", "baska": "baska_gecti" if ag_kip() == "dur" else "baska_kisa"}.get(aday["sinif"], aday["sinif"] + "_bitti"))
                if aday["sinif"] in (None, "on", "bos"): _ag_olay("kacan_aday", sure_ms=round(sure * 1000), kip=ag_kip())
                elif aday["sinif"] == "onay": _ag_olay("onay_gecti", sure_ms=round(sure * 1000), kaynak=aday.get("kaynak"), kip=ag_kip())
                ARAYA["aday"] = None
            return False
        if ag_kip() == "tam" and aday["sinif"] == "baska" and sure >= ag_esik() and simdi - SOHBET["t_okuma"] >= (AG_KORU_HOP_SN if SOHBET.get("hoparlor") else SOHBET_KORU_SN):
            ARAYA["aday"] = None; _ag_kes(aday, "baska", sure); return True
    return False
def _ag_tut(tut, pcm, duvar):  # "dur"dan sonra: söz sürerse yeni turun başı, kısa kalırsa atılır (kilit altında)
    tut["pcm"] += pcm; ARAYA["n"] += len(pcm) // 2
    r = vad_olasilik(pcm); bitti = bool(r and any(o.get("o") == "bitti" for o in r.get("olay") or []))
    if bitti or (r is not None and not r.get("konusma")):
        ARAYA["tut"] = None; ARAYA["acik"] = False; print(f"SOHBET: araya girme — durdurma sözü bitti, ses atıldı ({(ARAYA['n'] - tut['ornek']) / WH_SR:.1f} sn)"); return True
    if (ARAYA["n"] - tut["ornek"]) / WH_SR >= AG_DUR_DEVAM_SN:
        ARAYA["tut"] = None; ARAYA["acik"] = False; SOHBET["biriken"] = bytearray(tut["pcm"]); SOHBET["ag_t"] = time.time()
        print(f"SOHBET: araya girme — durdurma sözünden sonra konuşma sürüyor, yeni tur ({len(tut['pcm']) / 2 / WH_SR:.1f} sn ses)"); return True
    return True
def _ag_kes(aday, sinif, sure=None):  # okuma durur; başka söz yeni turun başı (biriken), "dur" tutulur (_ag_tut)
    t = time.time(); tepki = t - aday["t"]
    if sinif == "baska": SOHBET["biriken"] = bytearray(aday["pcm"]); SOHBET["ag_t"] = t
    else: ARAYA["tut"] = aday; ARAYA["aday"] = None
    _sohbet_kes(_KS["tur"], f"araya girme ({'durdurma sözü' if sinif == 'dur' else 'konuşma'}, {aday.get('kaynak') or '?'}, söz başından {tepki:.2f} sn)")
    aday["t_karar"] = t; _ag_say(sinif)
    _ag_olay("araya_girme", sinif=sinif, kaynak=aday.get("kaynak"), tepki_ms=round(tepki * 1000), kip=ag_kip(), **({"sure_ms": round(sure * 1000)} if sure else {}), **({"onaydi": True} if aday.get("onaydi") else {}))
    if sinif == "baska": SOHBET["kesik"] = {"t": t, "sinif": sinif, "kaynak": aday.get("kaynak"), "tepki_ms": round(tepki * 1000)}  # olasi_yanlis: kesmeden sonra söz gelmezse (_olcum_izle)
    k = ARAYA.get("kanca")
    if k:
        try: k(sinif, aday, tepki)
        except Exception: pass
def ag_metin(aday, metin, kaynak, ara=False):  # tanıyıcı sonucu (tstt ara metni ya da Whisper) → sınıf; "dur" hemen keser
    with ARAYA["kilit"]:
        if aday is not ARAYA["aday"] or aday["t_karar"]: return None
        s = _ag_sinif(metin, ara)
        if s in ("dur", "baska") and _ag_yanki(metin, tam=s == "dur"): s = "yanki"
        if s == "bos" and aday["sinif"]: return aday["sinif"]  # Whisper boş/uydurma: tstt'nin kararını silmez
        if s == "on" and aday["sinif"] in ("onay", "baska"): return aday["sinif"]
        aday.update(sinif=s, kaynak=kaynak, metin=str(metin or "")[:80])
        if s == "dur": _ag_kes(aday, "dur")
        elif s == "onay" and not aday.get("onay_say"): aday["onay_say"] = True; aday["onaydi"] = True; _ag_say("onay")
        elif s == "yanki" and not aday.get("yanki_say"): aday["yanki_say"] = True; _ag_say("yanki")
        return s
def _ag_whisper(aday, pcm):  # kısa parça Whisper işçisine, kuyruğun başına (bas-konuş işi gibi; dökülen metin yalnız sınıf için)
    t = time.time(); ev = threading.Event(); out = {}
    def g(m, h): out.update(m=m, h=h); ev.set()
    try:
        wh_one_al({"id": f"ag-{int(t * 1000)}", "bas": True, "kanal": "bas", "baslik": None, "pcm": pcm, "t0": t - len(pcm) / 2 / WH_SR, "t1": t, "kuyruga": t,
                   "dil": _t("tr", "en"), "oto_dil": False, "istemsiz": True, "geri": g}); _isci_baslat()
    except Exception as e: print(f"SOHBET: araya girme — Whisper'a gönderilemedi ({e.__class__.__name__})"); return
    if not ev.wait(5.0) or out.get("h"): return
    aday["wh_sn"] = round(time.time() - t, 3)
    ag_metin(aday, out.get("m") or "", "whisper")
# turkish-stt akış tanıyıcısı (isteğe bağlı; ayar yerel_araya_tstt false kapatır, kurulu değilse yalnız Whisper). Gölge kip işçisinin ayrı örneği, tek kanal "ag".
AGT = {"p": None, "durum": None, "kilit": threading.Lock(), "aday": None, "t_aday": 0.0}
def _agt_var():
    if AYAR.get("yerel_araya_tstt") is False or "_golge_yollar" not in globals(): return False
    py, md = _golge_yollar(); return os.path.exists(py) and os.path.isdir(md) and os.path.exists(GOLGE_ISCI)
def _agt_oku(p):
    for l in p.stdout:
        try: o = json.loads(l)
        except ValueError: continue
        if o.get("tur") == "hazir": AGT["durum"] = "hazir"; print(f"SOHBET: araya girme tanıyıcısı (turkish-stt) hazır ({o.get('yukleme_sn')} sn)"); continue
        if o.get("tur") != "ara" or o.get("k") != "ag": continue
        a = AGT["aday"]
        try: t = float(o.get("t") or 0)
        except (TypeError, ValueError): t = 0.0
        if a is None or t < AGT["t_aday"]: continue  # önceki sözün geç gelen ara metni
        ag_metin(a, o.get("metin") or "", "tstt", ara=True)
    if AGT["p"] is p: AGT.update(p=None, durum=None)
def _agt_baslat():
    with AGT["kilit"]:
        if AGT["p"] and AGT["p"].poll() is None: return True
        if not _agt_var(): return False
        py, md = _golge_yollar(); AGT["durum"] = "yukleniyor"
        try: p = subprocess.Popen([py, "-I", "-B", GOLGE_ISCI, md], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1, text=True, encoding="utf-8",
                                  env=dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1"))
        except OSError as e: AGT["durum"] = None; print(f"SOHBET: araya girme tanıyıcısı açılamadı ({e.__class__.__name__})"); return False
        AGT["p"] = p; threading.Thread(target=_agt_oku, args=(p,), daemon=True).start(); return True
def _agt_besle(aday, pcm, t, sifirla=False):
    p = AGT["p"]
    if not p or AGT["durum"] != "hazir" or not pcm: return
    if sifirla: AGT.update(aday=aday, t_aday=t)
    try: p.stdin.write(json.dumps({"k": "ag", "t": round(t, 3), "pcm": base64.b64encode(bytes(pcm)).decode(), **({"sifirla": True} if sifirla else {})}) + "\n"); p.stdin.flush()
    except (OSError, ValueError): AGT.update(p=None, durum=None)
def _agt_kapat():
    with AGT["kilit"]: p, AGT["p"] = AGT["p"], None; AGT.update(durum=None, aday=None)
    if p:
        try: p.stdin.close(); p.wait(3)
        except Exception:
            try: p.kill()
            except Exception: pass
def ag_hazirla():  # sohbet yerel yolda açılınca: Silero ve tstt (arka planda); kip kapalıysa hiçbir şey
    if ag_kip() == "kapali": return
    try: vad_baslat()
    except Exception as e: print(f"SOHBET: konuşma algılayıcı başlatılamadı ({e.__class__.__name__})")
    _agt_baslat()
def ag_view(): return {"kip": ag_kip(), "etkin": ag_etkin(), "tstt": AGT["durum"], "say": dict(ARAYA["say"])}
if "KY" in globals(): KY["obek_kanca"] = ag_obek
