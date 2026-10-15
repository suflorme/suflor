# --- Toplantıya sesli söyle (v0.38.0, 15 Ekim — kullanıcı isteği: masaüstü Teams'te BlackHole denemesi; ayar toplantiya_ses, varsayılan kapalı) ----------
# Yol: kullanıcı BlackHole'u kendisi kurar (GPL sürücü, Suflor'a gömülmez) ve Teams'te mikrofon olarak "BlackHole 2ch"i seçer. Menü uygulaması
# (OrtakMik) gerçek mikrofonu BlackHole'a geçirir; Option + Shift + S (menü → /komut soyle) son Konuş/hitap cevabının sesli kısmını (--- öncesi)
# Mac sesiyle BlackHole'a okur — Core Audio iki akışı aygıtta karıştırır, karşı taraf kullanıcının kanalından duyar. Aynı anda kulaklığa da
# okunur (kullanıcı ne söylendiğini duysun); kulaklık yoksa yerelde okunmaz (hoparlör → mikrofon → toplantıya ikinci kez giderdi).
# Toplantıdaki ilk okumada Suflor kendini tanıtır. Teams'te sessizdeyse karşı taraf duymaz (Teams BlackHole girişini de keser). Okurken yeniden
# basmak susturur. Okunan metin dökümde not olarak kalır ("🔊 Suflor toplantıya söyledi: …").
TS = {"p": [], "tanitti": None, "son": None}; TS_KILIT = threading.Lock()
TS_TANITIM = {"tr": "Merhaba, ben {ad} adına konuşan yapay zekâ asistanı Suflor.", "en": "Hello, I'm Suflor, an AI assistant speaking for {ad}."}
def ts_aygit():  # say -a ? listesinde BlackHole çıkış aygıtının kimliği (yoksa None)
    if os.environ.get("SUFLOR_TEST_TS_AYGIT"): return os.environ["SUFLOR_TEST_TS_AYGIT"]  # test/toplantiya-ses.py: BlackHole'suz deneme
    try: out = subprocess.run(["/usr/bin/say", "-a", "?"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired): return None
    m = re.search(r"^\s*(\d+)\s+BlackHole\b", out, re.M)
    return m.group(1) if m else None
def ts_sesli_kisim(metin):  # Konuş cevabının okunan kısmı: "---" öncesi, en çok 400 karakter
    return re.split(r"(?:^|\n)\s*-{3,}", metin or "", maxsplit=1)[0].strip()[:400]
def ts_durdur():
    with TS_KILIT: ps, TS["p"] = TS["p"], []
    n = 0
    for p in ps:
        if p.poll() is None: p.terminate(); n += 1
    return n > 0
def toplantiya_soyle(metin=None):
    if AYAR.get("toplantiya_ses") is not True: return {"ok": False, "err": _t("Toplantıya sesli söyleme kapalı (⚙ Ayarlar)", "Speaking into the meeting is off (⚙ Settings)")}
    if ts_durdur(): print("TOPLANTIYA SÖYLE: susturuldu"); return {"ok": True, "metin": _t("🔇 Suflor sustu", "🔇 Suflor stopped")}
    aygit = ts_aygit()
    if not aygit: return {"ok": False, "err": _t("BlackHole kurulu değil — toplantıya ses gidemez", "BlackHole isn't installed — no audio can reach the meeting")}
    m = ts_sesli_kisim(metin if metin is not None else KONUS.get("cevap"))
    if not m: return {"ok": False, "err": _t("Söylenecek cevap yok — önce Konuş'la sor", "Nothing to say — ask with Talk first")}
    toplanti = STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
    if TS["tanitti"] != toplanti:
        TS["tanitti"] = toplanti; m = TS_TANITIM.get(ARAYUZ_DILI, TS_TANITIM["en"]).format(ad=(AYAR.get("ad") or "").split(" ")[0] or "kullanıcı") + " " + m
    v = ses_secimi(); okunan = telaffuz(m); sesli = ["/usr/bin/say"] + (["-v", str(v)] if v else [])
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"TOPLANTIYA SÖYLE (deneme): aygıt {aygit} · {okunan}"); TS["son"] = m; return {"ok": True, "metin": "🔊 " + m}
    ses_durdur()  # kulaklıkta okunan bir şey varsa karışmasın
    ps = []
    try:
        ps.append(subprocess.Popen(sesli + ["-a", aygit, okunan], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        if kulaklik(): ps.append(subprocess.Popen(sesli + [okunan], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    except OSError as e: print(f"TOPLANTIYA SÖYLE: hata {e.__class__.__name__}"); return {"ok": False, "err": "say"}
    with TS_KILIT: TS["p"] = ps
    TS["son"] = m
    if STATE.get("meeting"):  # toplantı dosyası yoksa (deneme, toplantı dışı) not yazılmaz — yeni dosya açmasın
        try: note({"meeting": {"title": STATE["meeting"]}, "text": "🔊 Suflor toplantıya söyledi: " + m, "at": datetime.datetime.now().isoformat(timespec="seconds")})
        except Exception as e: print(f"TOPLANTIYA SÖYLE: not yazılamadı ({e.__class__.__name__})")
    print(f"TOPLANTIYA SÖYLE: {len(m)} karakter · aygıt {aygit}{' · kulaklıkta da' if len(ps) > 1 else ' · kulaklık yok, yerelde okunmadı'}")
    return {"ok": True, "metin": "🔊 " + m[:120]}

# Menü uygulaması nöbeti (v0.39.0): Teams'in mikrofonu BlackHole'sa ve menü uygulaması kapanırsa karşı taraf kullanıcıyı da duymaz. Ayar açıkken
# 5 sn'de bir bakılır; kapalıysa yeniden açılır ve bildirim gelir (en çok 5 dk'da bir). menu_yeniden'in kısa kapanışı da yeniden açmayla biter (zararsız).
TS_NOBET = {"son_uyari": 0.0}
def _ts_nobet():
    while True:
        time.sleep(5)
        try:
            if AYAR.get("toplantiya_ses") is not True or AYAR.get("menu_cubugu") is not True or deneme_aktarici() or not os.path.isdir(MENU_APP): continue
            if subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "SuflorMenu"], capture_output=True, timeout=5).returncode == 0: continue
            time.sleep(3)  # menu_yeniden kapatıp açıyor olabilir
            if subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "SuflorMenu"], capture_output=True, timeout=5).returncode == 0: continue
            print("TOPLANTIYA SÖYLE: menü uygulaması kapalı — yeniden açılıyor (Teams'in mikrofonu BlackHole'sa ses gitmiyordu)")
            STATE["_menu_son"] = 0  # bildirim menüye değil macOS'a
            if time.time() - TS_NOBET["son_uyari"] > 300:
                TS_NOBET["son_uyari"] = time.time()
                bildirim("Suflor.me", _t("Menü uygulaması kapandı — yeniden açılıyor", "Menu app quit — reopening"),
                         _t("Teams'te mikrofon BlackHole ise birkaç saniye sesin gitmemiş olabilir.", "If Teams uses BlackHole as the microphone, your voice may have been cut for a few seconds."))
            menu_baslat()
        except Exception as e: print(f"TOPLANTIYA SÖYLE: nöbet hatası {e.__class__.__name__}")
if not os.environ.get("SUFLOR_TEST_BASLAT"): threading.Thread(target=_ts_nobet, daemon=True).start()
