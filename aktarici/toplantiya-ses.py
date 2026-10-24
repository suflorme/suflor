# --- Toplantıya sesli söyle (v0.38.0, 15 Ekim — kullanıcı isteği: masaüstü Teams'te BlackHole denemesi; ayar toplantiya_ses, varsayılan kapalı) ----------
# Yol: kullanıcı BlackHole'u kendisi kurar (GPL sürücü, Suflor'a gömülmez) ve Teams'te mikrofon olarak "BlackHole 2ch"i seçer. Menü uygulaması
# (OrtakMik) gerçek mikrofonu BlackHole'a geçirir; Option + Shift + S (menü → /komut soyle) son Konuş/hitap cevabının sesli kısmını (--- öncesi)
# Mac sesiyle BlackHole'a okur — Core Audio iki akışı aygıtta karıştırır, karşı taraf kullanıcının kanalından duyar. Aynı anda kulaklığa da
# okunur (kullanıcı ne söylendiğini duysun); kulaklık yoksa yerelde okunmaz (hoparlör → mikrofon → toplantıya ikinci kez giderdi).
# Toplantıdaki ilk okumada Suflor kendini tanıtır. Teams'te sessizdeyse karşı taraf duymaz (Teams BlackHole girişini de keser). Okurken yeniden
# basmak susturur. Okunan metin dökümde ayrı etiketle kalır (| saat | **SUFLOR (sesli)** | metin | sesli |; .jsonl'de note + kaynak: suflor) — defter
# ve toplantı oturumu bunu kullanıcının notu saymaz.
# Web sürümü (v0.50.0): toplantı tarayıcıdaysa (Teams/Meet/Zoom web; eklenti nabzı call=true, masaüstü toplantı yok) BlackHole gerekmez. Metin Mac
# sesiyle WAV'a yazılır (say -o), eklenti /soyle-ses'ten alır, sayfa bağlamındaki soyle-main.js toplantı bağlantısının (RTCPeerConnection) ses
# göndericisini yalnız okuma süresince "mikrofon + Suflor" karışımıyla değiştirir (replaceTrack), bitince mikrofona döner — özellik kullanılmadıkça
# toplantı sesine dokunulmaz. Mikrofon sayfada kapalıysa (sessiz) okumaz; sonucu eklenti /olay "soyle-web" ile bildirir.
# v0.77.2 (18 Ekim, sohbet açıkken toplantı dışında okunan tanıtım mikrofondan girip "yazayım mı?" cevabı sayıldı): toplantı yokken okunmaz; okuma
# sürerken ts_caliyor() doğrudur — sohbet bunu da "Suflor okuyor" sayar (ses_caliyor), okunan metin kendi sesi süzgecine (kendi_ses_kaydet) yazılır.
TS = {"p": [], "tanitti": None, "son": None, "web": None, "test_bit": 0.0}; TS_KILIT = threading.Lock()
def ts_caliyor():
    if os.environ.get("SUFLOR_TEST_BASLAT") and time.time() < TS["test_bit"]: return True
    w = TS.get("web")
    if w and not w["dur"] and not w.get("bitti") and time.time() - w["t"] < w["sure"] + 1: return True
    with TS_KILIT: return any(p.poll() is None for p in TS["p"])
TS_TANITIM = {"tr": "Merhaba, ben {ad} adına konuşan yapay zekâ asistanı Suflor.", "en": "Hello, I'm Suflor, an AI assistant speaking for {ad}."}
def ts_aygit():  # say -a ? listesinde BlackHole çıkış aygıtının kimliği (yoksa None)
    if os.environ.get("SUFLOR_TEST_TS_AYGIT"): return os.environ["SUFLOR_TEST_TS_AYGIT"]  # test/toplantiya-ses.py: BlackHole'suz deneme
    try: out = subprocess.run(["/usr/bin/say", "-a", "?"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired): return None
    m = re.search(r"^\s*(\d+)\s+BlackHole\b", out, re.M)
    return m.group(1) if m else None
def ts_sesli_kisim(metin):  # Konuş cevabının okunan kısmı: "---" öncesi, en çok 400 karakter
    return etiket_sil(sesli_terim_suz(re.split(r"(?:^|\n)\s*-{3,}", metin or "", maxsplit=1)[0].strip()[:400]))  # v0.79.0: ses etiketleri yok · v0.57.1: iç terim süzgeci (bas-konus.py)
def ts_web():  # toplantı tarayıcıda mı: eklenti son 30 sn'de call=true dedi ve masaüstü uygulamada toplantı yok
    x = STATE.get("extension") or {}
    if not x.get("call") or (STATE.get("masaustu") or {}).get("toplantida"): return False
    try: return (datetime.datetime.now() - datetime.datetime.fromisoformat(x["seen"])).total_seconds() < 30
    except (KeyError, TypeError, ValueError): return False
def ts_web_view():  # şeride: okunacak ses (eklenti /soyle-ses?id= ile alır) ve "dur"; okuma süresi + 15 sn sonra düşer
    w = TS.get("web")
    return {"id": w["id"], "dur": w["dur"]} if w and time.time() - w["t"] < w["sure"] + 15 else None
def ts_web_ses(i):
    w = TS.get("web"); return w["ses"] if w and w["id"] == i else None
def ts_web_durum(d):  # eklentinin sonucu: caliyor | bitti | durdu | sessiz | baglanti-yok | hata:<ad>
    d = str(d or "")[:60]; print(f"TOPLANTIYA SÖYLE (web): {d}")
    w = TS.get("web")
    if w and d != "caliyor": w["bitti"] = True  # sonraki basış susturma değil, yeni okuma
    uy = {"sessiz": _t("🔇 Toplantıda mikrofonun kapalı — Suflor okumadı", "🔇 Your mic is muted in the meeting — Suflor didn't speak"),
          "baglanti-yok": _t("⚠ Toplantı bağlantısı bulunamadı — Suflor okumadı (sayfayı yenileyip yeniden dene)", "⚠ No meeting connection found — Suflor didn't speak (reload the page and retry)")}.get(d)
    if d.startswith("hata"): uy = _t("⚠ Toplantıya okunamadı", "⚠ Couldn't speak into the meeting") + f" ({d[5:] or '?'})"
    if uy: STATE["komut"] = {"id": secrets.token_hex(4), "at": datetime.datetime.now().isoformat(timespec="seconds"), "tur": "soyle", "metin": uy}
def ts_durdur():
    w = TS.get("web"); web = bool(w and not w["dur"] and not w.get("bitti") and time.time() - w["t"] < w["sure"] + 3)
    if web: w["dur"] = True
    with TS_KILIT: ps, TS["p"] = TS["p"], []
    n = int(web)
    for p in ps:
        if p.poll() is None: p.terminate(); n += 1
    return n > 0
# v0.113.0 (kullanıcı, 22 Ekim test toplantısı: "Gemini kotamı doldurmamak için toplantıda Pocket sesine dön diyebilmem lazım"): katılımcıların duyduğu
# ses ayarla (⚙ Ayarlar → Konuş → Toplantıda asistanın sesi, toplanti_ses) ya da toplantıda sesle (ses_komut). kisilik = eskisi gibi kişiliğin sesi (S92: Gemini).
# Gemini seçilip kullanılamıyorsa Pocket, o da yoksa Mac sesi. → (motor "gemini"|"pocket"|"piper"|"mac", ses adı)
def toplanti_ses_motoru():
    ts = AYAR.get("toplanti_ses") or "kisilik"; k = kisilik() or {}
    pocket = lambda: ("pocket", (pocket_ses_adi(k.get("yerel_ses")) if str(k.get("yerel_ses") or "").startswith("pocket") else None) or pocket_varsayilan()) if pocket_var() else ("mac", None)
    if ts == "mac": return "mac", None
    if ts == "pocket": return pocket()
    if ts == "gemini":
        kses = str(k.get("ses") or "")
        return ("gemini", kses.split(":", 1)[1].strip() if kses.startswith("gemini:") else None) if gemini_izinli(True) else pocket()
    km, kses, _ = kisilik_sesi(toplantiya=True)
    return km, kses
# Sesle ses değiştirme (v0.113.0): yalnız tüm cümle komutsa ("tamam, Pocket sesine dön", "Pocket'a geç", "Gemini sesine geç", "Mac sesine geç"; Whisper
# "Pocket"ı paket/pakıt yazabiliyor). Toplantıda toplanti_ses ayarını kalıcı değiştirir (⚙ Ayarlar'da da görünür); toplantı dışında v0.98.0 Gemini geçişi.
SES_KOMUT_RX = re.compile(r"(?i)^\W*(?:(?:tamam|peki|lütfen|hadi|şimdi|o\s+zaman)\W+)*(?P<m>pocket|poket|pakıt|paket|yerel|kendi|normal|gemini|cemini|mac)"
                          r"(?:'?(?:n?[ıiuü]n|n|y?[ae]))?\s*(?:ses\w*\s+)?(?:dön|geç|konuş|kullan|başla)\w*(?:\s+m[ıiuü]s[ıiuü]n)?(?:\W+lütfen)?\W*$")
def ses_komut(metin):  # → okunacak kısa onay ya da None (komut değil)
    m = SES_KOMUT_RX.search(" ".join(str(metin or "").split()))
    if not m: return gemini_gecis_komut(metin)
    h = m.group("m").lower(); hedef = "gemini" if h in ("gemini", "cemini") else "mac" if h == "mac" else "pocket"
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")):
        if hedef == "mac": return _t("Toplantı dışındaki sesi ⚙ Ayarlar → Ses'ten değiştirebilirsin.", "Change the voice outside meetings in ⚙ Settings → Voice.")
        return gemini_gecis_komut("gemini sesiyle konuş" if hedef == "gemini" else "yerel sese dön")
    ad = {"pocket": "Pocket", "gemini": "Gemini", "mac": _t("Mac", "Mac")}[hedef]
    if hedef == "pocket" and not pocket_var(): return _t("Pocket bu Mac'te kurulu değil; ses değişmedi.", "Pocket isn't installed on this Mac; the voice didn't change.")
    if hedef == "gemini" and not gemini_izinli(True): return _t("Gemini sesi şu an kullanılamıyor; ses değişmedi.", "The Gemini voice isn't available right now; the voice didn't change.")
    if hedef == "gemini" and gemini_model() is None: return _t("Gemini'nin bugünkü sınırı doldu; ses değişmedi.", "Gemini's daily limit is used up; the voice didn't change.")
    eski = toplanti_ses_motoru()[0]
    r = ayar_yaz({"toplanti_ses": hedef})
    if not r.get("ok"): return _t("Ayar yazılamadı; ses değişmedi.", "Couldn't save the setting; the voice didn't change.")
    if hedef != "gemini": GEMINI_GECIS["bitis"] = 0.0
    print(f"TOPLANTIYA SÖYLE: ses sesle değişti — {eski} → {hedef}")
    return _t(f"Tamam, toplantıda {ad} sesiyle konuşuyorum." if eski != hedef else f"Zaten {ad} sesiyle konuşuyorum.",
              f"OK, I'll use the {ad} voice in the meeting." if eski != hedef else f"I'm already using the {ad} voice.")
def toplantiya_soyle(metin=None):
    if AYAR.get("toplantiya_ses") is not True: return {"ok": False, "err": _t("Toplantıya sesli söyleme kapalı (⚙ Ayarlar)", "Speaking into the meeting is off (⚙ Settings)")}
    if ts_durdur(): print("TOPLANTIYA SÖYLE: susturuldu"); return {"ok": True, "metin": _t("🔇 Suflor sustu", "🔇 Suflor stopped")}
    if "gizli_acik" in globals() and gizli_acik(): print("TOPLANTIYA SÖYLE: gizli toplantı — okunmadı"); return {"ok": False, "err": _t("Gizli toplantı açık — toplantıya ses gitmez", "Private meeting is on — nothing is said into the meeting")}
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")):
        print("TOPLANTIYA SÖYLE: toplantı yok — okunmadı"); return {"ok": False, "err": _t("Toplantı yok — toplantıya söylenecek bir yer yok", "No meeting — nowhere to say it")}
    web = ts_web(); aygit = None if web else ts_aygit()
    if not web and not aygit: return {"ok": False, "err": _t("BlackHole kurulu değil — masaüstü toplantıya ses gidemez (web toplantısında gerekmez)", "BlackHole isn't installed — no audio can reach a desktop meeting (not needed for web meetings)")}
    m = ts_sesli_kisim(metin if metin is not None else KONUS.get("cevap"))
    if not m: return {"ok": False, "err": _t("Söylenecek cevap yok — önce Konuş'la sor", "Nothing to say — ask with Talk first")}
    toplanti = STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
    tanitim = None
    if TS["tanitti"] != toplanti:
        k = kisilik(); tn = (k or {}).get("tanitim") or str(AYAR.get("tanitim") or "").strip()  # v0.53.0: kişilik/ayar tanıtımı; yoksa nötr varsayılan
        tanitim = tn or TS_TANITIM.get(ARAYUZ_DILI, TS_TANITIM["en"]).format(ad=(AYAR.get("ad") or "").split(" ")[0] or "kullanıcı")
        TS["tanitti"] = toplanti; m = tanitim + " " + m
    v = ses_secimi(); okunan = ses_duzen(telaffuz(m, mac=True)); sesli = ["/usr/bin/say"] + (["-v", str(v)] if v else [])
    # v0.79.0 (kullanıcı 18 Ekim: "toplantı kişiliğinin sesi"): kişiliğin sesi Gemini ise ses Gemini'den (ör. toplantı kişiliği Kore); alınamazsa Mac sesi
    km, kses = toplanti_ses_motoru(); gpcm = None  # v0.81.0 (S92): katılımcıların duyduğu ses — Gemini burada; v0.113.0: ayar toplanti_ses / sesle Pocket
    if km == "gemini" and os.access(PIPER_OYNAT, os.X_OK) and not os.environ.get("SUFLOR_TEST_BASLAT"):
        usl = kisilik_uslup(kisilik()) or None; govde = m[len(tanitim) + 1:] if tanitim else m
        # tanıtım ve toplantı başı duyurusu sabit: bir kez okunup önbellekte (günlük sınırdan yemez); tanıtım ayrı okunup cevabın önüne eklenir
        gpcm = gemini_pcm(ses_duzen(kisilik_telaffuz(govde), False), ses=kses, uslup=usl, sabit=True if govde.strip() in DUYURU_SABIT() else None)
        if gpcm and tanitim:
            tp = gemini_pcm(ses_duzen(kisilik_telaffuz(tanitim), False), ses=kses, uslup=usl, sabit=True)
            gpcm = (tp + b"\0\0" * int(GEMINI_SR * 0.35) + gpcm) if tp else None
        if not gpcm: print("TOPLANTIYA SÖYLE: Gemini sesi alınamadı — Mac sesi")
    elif km == "pocket" and os.access(PIPER_OYNAT, os.X_OK) and (not os.environ.get("SUFLOR_TEST_BASLAT") or os.environ.get("SUFLOR_TEST_TS_POCKET")):
        # v0.113.0: Pocket da 24 kHz 16 bit — Gemini'nin yolu (BlackHole / web toplantısında eklenti) aynen; okunacak metin toplanır, sonra çalınır
        gpcm = pocket_pcm(kisilik_telaffuz(etiket_sil(m)), ses=kses)
        if gpcm: print(f"TOPLANTIYA SÖYLE: Pocket sesi ({kses}, {len(gpcm) / 2 / GEMINI_SR:.1f} sn)")
        else: print("TOPLANTIYA SÖYLE: Pocket sesi alınamadı — Mac sesi")
    if web: return _ts_web_hazirla(m, sesli, okunan, gpcm)
    if os.environ.get("SUFLOR_TEST_BASLAT"):
        print(f"TOPLANTIYA SÖYLE (deneme): aygıt {aygit} · {okunan}"); TS["son"] = m; TS["son_t"] = TS["test_bit"] = time.time() + len(m) / 14
        kendi_ses_kaydet(m, time.time(), TS["son_t"]); return {"ok": True, "metin": "🔊 " + m}
    ses_durdur()  # kulaklıkta okunan bir şey varsa karışmasın
    ps = []
    try:
        if gpcm:  # Gemini sesi kesintisiz çalıcıyla BlackHole'a (karşı taraf) ve kulaklığa
            for a in [aygit] + ([None] if kulaklik() else []):
                p = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)] + ([str(a)] if a else []), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); ps.append(p)
                threading.Thread(target=_ts_besle, args=(p, gpcm), daemon=True).start()
        else:
            ps.append(subprocess.Popen(sesli + ["-a", aygit, okunan], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            if kulaklik(): ps.append(subprocess.Popen(sesli + [okunan], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    except OSError as e: print(f"TOPLANTIYA SÖYLE: hata {e.__class__.__name__}"); return {"ok": False, "err": "say"}
    with TS_KILIT: TS["p"] = ps
    TS["zarf"] = (time.time(), ses_zarfi(gpcm, GEMINI_SR)) if gpcm else None  # 19 Ekim: otonom okurken kanaldaki ses kendi yankımız mı (otonom.py)
    TS["son"] = m; TS["son_t"] = time.time() + (len(gpcm) / 2 / GEMINI_SR if gpcm else len(m) / 14)  # okuma sonu (Mac sesinde tahmin ~14 karakter/sn): karşı taraf hitabı ardından 10 sn sayılmaz
    kendi_ses_kaydet(m, time.time(), TS["son_t"])
    if STATE.get("meeting"):  # toplantı dosyası yoksa (deneme, toplantı dışı) not yazılmaz — yeni dosya açmasın
        try: note({"meeting": {"title": STATE["meeting"]}, "text": m, "kaynak": "suflor", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        except Exception as e: print(f"TOPLANTIYA SÖYLE: not yazılamadı ({e.__class__.__name__})")
    print(f"TOPLANTIYA SÖYLE: {len(m)} karakter · aygıt {aygit}{' · Gemini ' + (kses or gemini_ses()) if gpcm else ''}{' · kulaklıkta da' if len(ps) > 1 else ' · kulaklık yok, yerelde okunmadı'}")
    return {"ok": True, "metin": "🔊 " + m[:120]}
def ses_zarfi(pcm, sr, kare_sn=0.02):  # 16 bit ham ses → 20 ms karelerin sesli/sessiz listesi (eşik: en yüksek karelerin %12'si)
    import array
    a = array.array("h"); a.frombytes(pcm[: len(pcm) // 2 * 2]); n = max(1, int(sr * kare_sn))
    r = [math.sqrt(sum(x * x for x in a[i:i + n][::4]) / max(1, len(a[i:i + n][::4]))) for i in range(0, len(a) - n + 1, n)]
    if not r: return []
    tepe = sorted(r)[int(len(r) * 0.95)]
    return [x > max(150.0, tepe * 0.12) for x in r]
def _ts_besle(p, pcm):  # kesintisiz çalıcıya ham sesi verir (ts_durdur süreci keserse yazma hatası yok sayılır)
    try: p.stdin.write(pcm); p.stdin.close()
    except (OSError, ValueError): pass
def _ts_web_hazirla(m, sesli, okunan, gpcm=None):
    import tempfile
    fd, yol = tempfile.mkstemp(suffix=".wav", prefix="suflor-soyle-"); os.close(fd)
    try:
        if gpcm:  # v0.79.0: Gemini sesi aynı biçimde (24 kHz 16 bit WAV)
            import wave
            with wave.open(yol, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(GEMINI_SR); w.writeframes(gpcm)
            r = subprocess.CompletedProcess([], 0)
        else: r = subprocess.run(sesli + ["-o", yol, "--file-format=WAVE", "--data-format=LEI16@24000", okunan], capture_output=True, timeout=60)
        b = open(yol, "rb").read()
    except (OSError, subprocess.TimeoutExpired) as e: r, b = None, b""; print(f"TOPLANTIYA SÖYLE (web): ses üretilemedi ({e.__class__.__name__})")
    finally:
        try: os.remove(yol)
        except OSError: pass
    if not r or r.returncode or len(b) < 1000: return {"ok": False, "err": _t("Ses üretilemedi", "Couldn't make the audio")}
    sure = (len(b) - 44) / 48000  # 24 kHz × 2 bayt
    ses_durdur()
    TS["web"] = {"id": secrets.token_hex(6), "ses": b, "t": time.time(), "sure": sure, "dur": False}
    ps = []
    if kulaklik() and not os.environ.get("SUFLOR_TEST_BASLAT"):  # kullanıcı da duysun (kulaklık yoksa hoparlör → mikrofon → toplantıya ikinci kez giderdi)
        try:
            if gpcm:
                p = subprocess.Popen([PIPER_OYNAT, str(GEMINI_SR)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); ps.append(p)
                threading.Thread(target=_ts_besle, args=(p, gpcm), daemon=True).start()
            else: ps.append(subprocess.Popen(sesli + [okunan], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        except OSError: pass
    with TS_KILIT: TS["p"] = ps
    TS["zarf"] = (time.time(), ses_zarfi(b[44:], 24000))  # 19 Ekim: otonomun yankı ayrımı (eklenti birazdan çalar; gecikme aramada)
    TS["son"] = m; TS["son_t"] = time.time() + sure
    kendi_ses_kaydet(m, time.time(), TS["son_t"])
    if STATE.get("meeting"):
        try: note({"meeting": {"title": STATE["meeting"]}, "text": m, "kaynak": "suflor", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        except Exception as e: print(f"TOPLANTIYA SÖYLE: not yazılamadı ({e.__class__.__name__})")
    kart_bildir()
    print(f"TOPLANTIYA SÖYLE (web): {len(m)} karakter · {sure:.1f} sn ses{' · kulaklıkta da' if ps else ''}")
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
# --- Toplantıda duyuru (v0.80.0, S87 — kullanıcı 18 Ekim: "karşı tarafa bildirim sesi" = toplantıda duyuru; ayar toplanti_duyuru, varsayılan kapalı) -------
# Toplantıya söyle açıksa (toplantiya_ses) Suflor toplantıdakilere kısa duyuru yapar: toplantı başında bir kez tanıtım + "dinleyip not alıyorum" (tanıtımı
# toplantiya_soyle kendisi ekler) ve toplantıda onaylanan iş için "Not aldım: …" (en çok DUYURU_ARA_SN'de bir). Söz sırası boşalınca okunur
# (kanal_sessizlik ≥ 1,5 sn, en çok DUYURU_SIRA_SN beklenir; kanal akmıyorsa ölçülemez, okunmaz). Ses toplantı kişiliğinin Gemini sesi (toplantiya_soyle).
DUYURU = {"toplanti": None, "t_ilk": 0.0, "son": 0.0, "say": 0}
DUYURU_ARA_SN, DUYURU_SIRA_SN, DUYURU_BASLA_SN = 60.0, 20.0, (3.0 if os.environ.get("SUFLOR_TEST_HIZLI") else 30.0)
DUYURU_METIN = {"baslangic": ("Toplantıyı dinleyip not alıyorum.", "I'm listening and taking notes."), "not": ("Not aldım: {b}", "Noted: {b}")}
def DUYURU_SABIT(): return {_t(*DUYURU_METIN["baslangic"])}  # v0.81.0: değişmeyen duyurular (önbellekten)
def duyuru_acik(): return AYAR.get("toplanti_duyuru") is True and AYAR.get("toplantiya_ses") is True and not ("gizli_acik" in globals() and gizli_acik())
def _duyuru_toplanti():
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")): return None
    return STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
def toplanti_duyuru(neden, baslik=None, metin=None):  # arka planda söz sırasını bekler; başlarsa True. neden "sure": metin hazır (sesli süre uyarısı)
    if not (sure_duyuru_acik() if neden == "sure" else duyuru_acik()) or not _duyuru_toplanti(): return False
    if neden not in ("baslangic", "sure") and time.time() - DUYURU["son"] < DUYURU_ARA_SN: print(f"DUYURU: {DUYURU_ARA_SN:.0f} sn dolmadı, okunmadı ({neden})"); return False
    if metin is None:
        tr, en = DUYURU_METIN[neden]; b = _cumle(" ".join(str(baslik or "").split())[:120]).rstrip(".") if baslik else ""
        metin = _t(tr, en).format(b=b).strip()
    if metin.endswith(":"): return False
    if not metin.endswith((".", "!", "?")): metin += "."
    def calis():
        son = time.time() + DUYURU_SIRA_SN
        while time.time() < son:
            if not _duyuru_toplanti(): return
            s = kanal_sessizlik()
            if s is not None and s >= 1.5 and not ses_caliyor(): break
            time.sleep(0.3)
        else: print(f"DUYURU: söz sırası boşalmadı, okunmadı ({neden})"); return
        r = toplantiya_soyle(metin)
        if r.get("ok"): DUYURU.update(son=time.time(), say=DUYURU["say"] + 1); print(f"DUYURU: {neden} · {metin}")
        else: print(f"DUYURU: okunamadı ({neden}) — {r.get('err')}")
    threading.Thread(target=calis, daemon=True).start(); return True
def duyuru_eylem(xs):  # eylem_karar'dan: toplantıda onaylanan işler (birden çoksa ilki + sayı)
    if not xs or not duyuru_acik() or not _duyuru_toplanti(): return
    b = xs[0].get("baslik") or ""
    if len(xs) > 1: b = _t(f"{b} ve {len(xs) - 1} iş daha", f"{b} and {len(xs) - 1} more")
    toplanti_duyuru("not", b)
def _duyuru_nobet():  # toplantı başında bir kez: toplantı DUYURU_BASLA_SN sürdükten sonra
    while True:
        time.sleep(1.0 if os.environ.get("SUFLOR_TEST_HIZLI") else 5.0)
        try:
            t = _duyuru_toplanti()
            if not t: DUYURU.update(toplanti=None, t_ilk=0.0); continue
            if DUYURU["toplanti"] == t: continue
            if not DUYURU["t_ilk"]: DUYURU["t_ilk"] = time.time()
            if time.time() - DUYURU["t_ilk"] < DUYURU_BASLA_SN or not duyuru_acik(): continue
            DUYURU["toplanti"] = t; toplanti_duyuru("baslangic")
        except Exception as e: print(f"DUYURU: nöbet hatası {e.__class__.__name__}")
threading.Thread(target=_duyuru_nobet, daemon=True).start()
# --- Sesli süre uyarısı (S91, v0.89.0; ayar sure_duyuru, varsayılan kapalı; toplantiya_ses de açık olmalı) ------------------------------------
# Yürütücü rolünde (agenda.json rol) kalan 15 dk, son 5 dk, süre doldu ve gündem kayması (≥ 2 madde geride, en çok SURE_KAYMA_SN'de bir)
# toplantıya söylenir; önceden yalnız toplantı oturumuna SÜRE olayı ve kart. Toplantıya geç katılınca geçilmiş eşikler söylenmez. Söz sırası duyuruyla aynı.
SURE_DUY = {"toplanti": None, "esik": set(), "kayma_son": 0.0}
SURE_KAYMA_SN = 5.0 if os.environ.get("SUFLOR_TEST_HIZLI") else 600.0
def sure_duyuru_acik(): return AYAR.get("sure_duyuru") is True and AYAR.get("toplantiya_ses") is True and not ("gizli_acik" in globals() and gizli_acik())
def _sure_esikler(sv): k = sv["kalan_dk"]; return {e for e, ok in (("15", k <= 15), ("5", k <= 5), ("bitti", k <= 0)) if ok}
def sure_duyuru_metin(e, sv):
    kal, acik = sv["kalan_dk"], len(sv.get("acik") or [])
    if e == "15": return _t(f"Kalan süre {kal} dakika" + (f", gündemde {acik} madde açık." if acik else "."), f"{kal} minutes left" + (f", {acik} agenda items open." if acik else "."))
    if e == "5": return _t("Son beş dakika" + (f"; {acik} madde açık." if acik else "."), "Last five minutes" + (f"; {acik} items still open." if acik else "."))
    if e == "bitti": return _t("Toplantı süresi doldu.", "We're at time.")
    return _t(f"Gündemin {sv['kayma']} madde gerisindeyiz; kalan süre {kal} dakika.", f"We're {sv['kayma']} agenda items behind; {kal} minutes left.")
def sure_duyuru_bak():  # nöbetten; söylenecekse (neden, metin), yoksa None
    t = _duyuru_toplanti()
    if not t: SURE_DUY.update(toplanti=None, esik=set()); return None
    sv = sure_view() if (agenda().get("rol") or "") == "yurutucu" else None
    if not sv: return None
    es = _sure_esikler(sv)
    if SURE_DUY["toplanti"] != t: SURE_DUY.update(toplanti=t, esik=set(es), kayma_son=time.time()); return None  # geçilmiş eşikler söylenmez
    yeni = es - SURE_DUY["esik"]; SURE_DUY["esik"] |= es
    if not sure_duyuru_acik(): return None
    if yeni: e = next(x for x in ("bitti", "5", "15") if x in yeni); SURE_DUY["kayma_son"] = time.time(); return e, sure_duyuru_metin(e, sv)
    if sv.get("kayma", 0) >= 2 and sv["kalan_dk"] > 5 and time.time() - SURE_DUY["kayma_son"] >= SURE_KAYMA_SN:
        SURE_DUY["kayma_son"] = time.time(); return "kayma", sure_duyuru_metin("kayma", sv)
    return None
def _sure_nobet():
    while True:
        time.sleep(1.0 if os.environ.get("SUFLOR_TEST_HIZLI") else 5.0)
        try:
            r = sure_duyuru_bak()
            if r: print(f"SÜRE DUYURU: {r[0]} · {r[1]}"); toplanti_duyuru("sure", metin=r[1])
        except Exception as e: print(f"SÜRE DUYURU: nöbet hatası {e.__class__.__name__}")
threading.Thread(target=_sure_nobet, daemon=True).start()
