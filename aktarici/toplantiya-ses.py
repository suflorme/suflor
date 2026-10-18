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
def toplantiya_soyle(metin=None):
    if AYAR.get("toplantiya_ses") is not True: return {"ok": False, "err": _t("Toplantıya sesli söyleme kapalı (⚙ Ayarlar)", "Speaking into the meeting is off (⚙ Settings)")}
    if ts_durdur(): print("TOPLANTIYA SÖYLE: susturuldu"); return {"ok": True, "metin": _t("🔇 Suflor sustu", "🔇 Suflor stopped")}
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")):
        print("TOPLANTIYA SÖYLE: toplantı yok — okunmadı"); return {"ok": False, "err": _t("Toplantı yok — toplantıya söylenecek bir yer yok", "No meeting — nowhere to say it")}
    web = ts_web(); aygit = None if web else ts_aygit()
    if not web and not aygit: return {"ok": False, "err": _t("BlackHole kurulu değil — masaüstü toplantıya ses gidemez (web toplantısında gerekmez)", "BlackHole isn't installed — no audio can reach a desktop meeting (not needed for web meetings)")}
    m = ts_sesli_kisim(metin if metin is not None else KONUS.get("cevap"))
    if not m: return {"ok": False, "err": _t("Söylenecek cevap yok — önce Konuş'la sor", "Nothing to say — ask with Talk first")}
    toplanti = STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
    if TS["tanitti"] != toplanti:
        k = kisilik(); tn = (k or {}).get("tanitim") or str(AYAR.get("tanitim") or "").strip()  # v0.53.0: kişilik/ayar tanıtımı; yoksa nötr varsayılan
        TS["tanitti"] = toplanti; m = (tn or TS_TANITIM.get(ARAYUZ_DILI, TS_TANITIM["en"]).format(ad=(AYAR.get("ad") or "").split(" ")[0] or "kullanıcı")) + " " + m
    v = ses_secimi(); okunan = ses_duzen(telaffuz(m, mac=True)); sesli = ["/usr/bin/say"] + (["-v", str(v)] if v else [])
    # v0.79.0 (kullanıcı 18 Ekim: "toplantı kişiliğinin sesi"): kişiliğin sesi Gemini ise ses Gemini'den (ör. toplantı kişiliği Kore); alınamazsa Mac sesi
    km, kses, _ = kisilik_sesi(); gpcm = None
    if km == "gemini" and os.access(PIPER_OYNAT, os.X_OK) and not os.environ.get("SUFLOR_TEST_BASLAT"):
        gpcm = gemini_pcm(ses_duzen(kisilik_telaffuz(m), False), ses=kses, uslup=(kisilik() or {}).get("ses_uslup"))
        if not gpcm: print("TOPLANTIYA SÖYLE: Gemini sesi alınamadı — Mac sesi")
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
    TS["son"] = m; TS["son_t"] = time.time() + (len(gpcm) / 2 / GEMINI_SR if gpcm else len(m) / 14)  # okuma sonu (Mac sesinde tahmin ~14 karakter/sn): karşı taraf hitabı ardından 10 sn sayılmaz
    kendi_ses_kaydet(m, time.time(), TS["son_t"])
    if STATE.get("meeting"):  # toplantı dosyası yoksa (deneme, toplantı dışı) not yazılmaz — yeni dosya açmasın
        try: note({"meeting": {"title": STATE["meeting"]}, "text": m, "kaynak": "suflor", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        except Exception as e: print(f"TOPLANTIYA SÖYLE: not yazılamadı ({e.__class__.__name__})")
    print(f"TOPLANTIYA SÖYLE: {len(m)} karakter · aygıt {aygit}{' · Gemini ' + (kses or gemini_ses()) if gpcm else ''}{' · kulaklıkta da' if len(ps) > 1 else ' · kulaklık yok, yerelde okunmadı'}")
    return {"ok": True, "metin": "🔊 " + m[:120]}
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
def duyuru_acik(): return AYAR.get("toplanti_duyuru") is True and AYAR.get("toplantiya_ses") is True
def _duyuru_toplanti():
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")): return None
    return STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
def toplanti_duyuru(neden, baslik=None):  # arka planda söz sırasını bekler; başlarsa True
    if not duyuru_acik() or not _duyuru_toplanti(): return False
    if neden != "baslangic" and time.time() - DUYURU["son"] < DUYURU_ARA_SN: print(f"DUYURU: {DUYURU_ARA_SN:.0f} sn dolmadı, okunmadı ({neden})"); return False
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
