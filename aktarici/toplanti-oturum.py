# Suflor.me aktarıcı bölümü: Toplantı oturumu arka planda (v0.111.0; kullanıcı 22 Ekim: "kullanıcının Claude Code terminalini görmesine gerek yok").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("toplanti-oturum")): AYAR, BASE, STATE, LOCK, _t, claude_yolu, BRIFING_APP,
# izin_iste, izin_bekle, gizli_acik … import etme. Python 3.9 uyumlu.
# Panodan Başlat'la açılan toplantı oturumu (/toplanti) Terminal yerine Suflor Brifing.app'in toplantı kipinde çalışır: `claude -p` stream-json giriş/çıkış,
# iki FIFO (bas-konuş açık süreç kipiyle aynı yol; Masaüstü izni o uygulamada). Oturumun kullanıcıya yazdıkları panoda "Claude" bölümünde görünür;
# tur bitince (sonuç iletisi) oturum kullanıcıyı bekler ve kutuya yazılan metin ona gider. Tur sürerken kutu eski yolla (izle GİRDİ) gider.
# Proje izinlerinde olmayan araç: Claude Code soruyu stdio'dan sorar (can_use_tool) → izin_iste (panoda onay kartı; toplantı dışında sesli) → karar.
# Panoda Durdur (interrupt) ve "Terminal'de göster" (süreç kapanır, aynı oturum `claude --resume` ile Terminal'de açılır). Süreç beklenmedik çıkarsa
# aynı oturum en çok TOPO_YENIDEN kez kaldığı yerden açılır. Ayar toplanti_terminal: true eski davranış (Terminal penceresi).
TOPO = {"app": None, "w": None, "durum": "kapali", "sid": None, "mesaj": [], "n": 0, "konu": None, "t0": 0.0, "t_durum": 0.0, "maliyet": 0.0, "nesil": 0,
        "kapali_nesil": None, "yeniden": 0, "izin": 0, "hata": None, "acilis": None, "secenek_i": None, "kilit": threading.RLock()}
TOPO_YENIDEN, TOPO_MESAJ_EN_COK, TOPO_METIN_EN_COK, TOPO_SURE_SN = 2, 400, 6000, 8 * 3600
TOPO_TERMINAL_ILETI = "(Suflor) Oturum arka plandan Terminal'e alındı; arka plandaki Monitor durdu. Toplantı sürüyorsa izle'yi yeniden başlat, sürmüyorsa kaldığın yerden devam et."
TOPO_BOSTA_SN = 2 * 3600  # tur bitmiş ve izle yokken bu kadar boşta kalırsa süreç kapanır (~250 MB); "Terminal'de göster" yine aynı oturumu açar
TOPO_ISTEM = ("Bu toplantı oturumu Suflor.me panosundan arka planda açıldı; Terminal penceresi yok. Kullanıcıya yazdığın her metin panoda 'Claude' bölümünde "
              "görünür; kullanıcı panodaki kutudan yazar. Kullanıcıya soru sorman gerekiyorsa soruyu kısa ve açık yaz, sonra turu bitir (cevap yeni ileti "
              "olarak gelir); AskUserQuestion aracını kullanma. Toplantı sürerken izle döngüsünü bırakma. Kancanın 'Terminal'den onay iste' demesi bu "
              "oturumda panodan onay demektir. Araç çağrılarında açıklama (description) alanını Türkçe, kullanıcıya düz bir cümleyle yaz — ne yapacağını ve "
              "gerekiyorsa neden (ör. \"Kulis'in veri dosyasını okuyup test listesini çıkarmak\"); komut, kod ya da dosya yolu yazma: onay kartında bu cümle görünür. Kullanıcıdan seçim isterken (onay, evet/hayır, birkaç seçenek) mesajının son satırına seçenekleri "
              "şu biçimde yaz: [[seç: Seçenek 1 | Seçenek 2 | Seçenek 3]] — en çok 5 seçenek, her biri kısa; panoda düğme olur, basılan seçenek cevap "
              "olarak gelir. Kullanıcı düğme yerine serbest metin de yazabilir.")
# v0.112.0 (S122 2. adım): Claude'un seçim sorusu — mesajdaki [[seç: A | B]] satırı ayıklanır, panoda ve mini panoda düğme olur; basınca seçim oturuma gider.
TOPO_SECENEK_RX = re.compile(r"^[ \t]*\[\[\s*(?:seç|sec|seçenek|secenek|options?|choices?)\s*:\s*(.+?)\s*\]\][ \t]*$", re.M | re.I)
def _topo_secenek_ayir(metin):
    bul = TOPO_SECENEK_RX.findall(str(metin or ""))
    if not bul: return metin, None
    liste = []
    for x in bul[-1].split("|"):
        x = " ".join(x.split())[:60]
        if x and x not in liste: liste.append(x)
    return TOPO_SECENEK_RX.sub("", metin).strip(), (liste[:5] if len(liste) >= 1 else None)
def topo_canli(): return bool(TOPO["w"]) and TOPO["app"] is not None and TOPO["app"].poll() is None
def _topo_durum(d, hata=None):
    TOPO["durum"] = d; TOPO["t_durum"] = time.time()
    if hata is not None: TOPO["hata"] = hata
def _topo_mesaj(kim, metin, **ek):
    metin = str(metin or "").strip()
    if kim == "claude":
        metin, sec = _topo_secenek_ayir(metin)
        if sec: ek["secenek"] = sec
    if not metin and not ek.get("secenek"): return
    with LOCK:
        TOPO["n"] += 1
        if ek.get("secenek"): TOPO["secenek_i"] = TOPO["n"]
        TOPO["mesaj"].append(dict(i=TOPO["n"], t=datetime.datetime.now().strftime("%H:%M"), kim=kim, metin=metin[:TOPO_METIN_EN_COK], **ek))
        del TOPO["mesaj"][:-TOPO_MESAJ_EN_COK]
def _topo_arac_ozet(ad, gi):
    gi = gi if isinstance(gi, dict) else {}
    if ad == "Bash": s = gi.get("description") or gi.get("command")
    elif ad in ("Read", "Edit", "Write"): s = gi.get("file_path")
    elif ad in ("Grep", "Glob"): s = gi.get("pattern")
    else: s = json.dumps(gi, ensure_ascii=False)
    return " ".join(str(s or "").split())[:200]
def _topo_gonder(o):
    w = TOPO["w"]
    if not w: return False
    try: w.write(json.dumps(o, ensure_ascii=False) + "\n"); w.flush(); return True
    except (OSError, ValueError): return False
def toplanti_oturum_ac(cl, model, ky, ilk, konu=None, sid=None):
    # cl: claude yolu · model: ayar claude_model · ky: toplanti-kanca.json (ya da None) · ilk: ilk kullanıcı iletisi · sid: kaldığı yerden (--resume)
    with TOPO["kilit"]:
        if topo_canli(): toplanti_oturum_kapat("yeni başlatma")
        gir, cik, istek = (os.path.join(BASE, f) for f in ("toplanti-giris.fifo", "toplanti-cikis.fifo", "toplanti-istek.json"))
        for f in (gir, cik):
            try: os.remove(f)
            except OSError: pass
            os.mkfifo(f, 0o600)
        args = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--permission-prompt-tool", "stdio",
                "--append-system-prompt", TOPO_ISTEM] + (["--model", str(model)] if model else []) + (["--settings", ky] if ky else []) + (["--resume", sid] if sid else [])
        fd = os.open(istek, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"kip": "toplanti", "claude": cl, "args": args, "cwd": os.path.expanduser(AYAR["proje"]), "cikti": os.path.join(BASE, "toplanti-bos"),
                       "giris": gir, "cikis": cik, "sure": TOPO_SURE_SN}, f, ensure_ascii=False)
        if not sid: TOPO.update(mesaj=[], n=TOPO["n"], sid=None, secenek_i=None, konu=konu, t0=time.time(), maliyet=0.0, yeniden=0, izin=0, hata=None)
        TOPO["acilis"] = {"cl": cl, "model": model, "ky": ky}
        _topo_durum("aciliyor", hata=None)
        TOPO["app"] = subprocess.Popen(["open", "-g", "-W", "-n", "-a", BRIFING_APP, "--args", "--istek", istek], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time(); w = None
        while time.time() - t0 < 20 and TOPO["app"].poll() is None:
            try: w = os.open(gir, os.O_WRONLY | os.O_NONBLOCK); break
            except OSError: time.sleep(0.05)
        if w is None:
            _topo_durum("hata", _t("Toplantı oturumu açılamadı (izin penceresi?) — yeniden Başlat", "Couldn't open the meeting session (permission prompt?) — press Start again"))
            print("TOPLANTI OTURUMU: açılamadı (Brifing yardımcısı girişi açmadı)"); return False
        os.set_blocking(w, True); TOPO["w"] = os.fdopen(w, "w", encoding="utf-8", buffering=1)
        TOPO["nesil"] += 1; threading.Thread(target=_topo_oku, args=(cik, TOPO["nesil"]), daemon=True).start()
        threading.Thread(target=_topo_bekci, args=(TOPO["nesil"],), daemon=True).start()
        _topo_gonder({"type": "user", "message": {"role": "user", "content": ilk}}); _topo_durum("calisiyor")
        print(f"TOPLANTI OTURUMU: arka planda açıldı ({time.time() - t0:.1f} sn){' · kaldığı yerden ' + sid[:8] if sid else ''}"); return True
def toplanti_oturum_kapat(neden):
    with TOPO["kilit"]:
        w, app = TOPO["w"], TOPO["app"]; TOPO.update(w=None, app=None); TOPO["kapali_nesil"] = TOPO["nesil"]
        if w:
            try: w.close()  # giriş kapanınca claude çıkar, uygulama da biter
            except OSError: pass
        if app and app.poll() is None:
            try: app.wait(timeout=10)
            except subprocess.TimeoutExpired: pass
        if w: print(f"TOPLANTI OTURUMU: kapandı ({neden})")
        if TOPO["durum"] not in ("hata", "terminalde"): _topo_durum("kapali")
def toplanti_oturum_yaz(metin, kaynak="kutu"):
    metin = str(metin or "").strip()[:4000]
    if not metin: return {"ok": False, "err": "boş"}
    if not topo_canli(): return {"ok": False, "err": _t("Toplantı oturumu açık değil", "The meeting session isn't running")}
    if not _topo_gonder({"type": "user", "message": {"role": "user", "content": metin}}): return {"ok": False, "err": _t("Oturuma yazılamadı", "Couldn't write to the session")}
    _topo_mesaj("ben", metin, kaynak=kaynak); _topo_durum("calisiyor"); TOPO["secenek_i"] = None
    print(f"TOPLANTI OTURUMU: kullanıcı yazdı ({kaynak}, {len(metin)} karakter)"); return {"ok": True}
def toplanti_oturum_durdur():
    if not topo_canli() or TOPO["durum"] != "calisiyor": return {"ok": False, "err": _t("Toplantı oturumu açık değil", "The meeting session isn't running")}
    _topo_gonder({"type": "control_request", "request_id": "durdur-" + secrets.token_hex(6), "request": {"subtype": "interrupt"}})
    _topo_mesaj("sistem", _t("Durduruldu. Yazarsan kaldığı yerden sürer.", "Stopped. Type to continue."))
    print("TOPLANTI OTURUMU: durduruldu (kullanıcı)"); return {"ok": True}
def toplanti_oturum_terminal():
    # aynı oturumu Terminal'de görünür açar: arka plandaki süreç kapanır (iki süreç aynı oturuma yazmasın), `claude --resume <kimlik>`
    sid, ac = TOPO["sid"], TOPO["acilis"] or {}
    if not sid: return {"ok": False, "err": _t("Oturum kimliği henüz yok — birkaç saniye sonra yeniden dene", "No session id yet — try again in a few seconds")}
    if topo_canli():
        _topo_gonder({"type": "control_request", "request_id": "terminal-" + secrets.token_hex(6), "request": {"subtype": "interrupt"}}); time.sleep(0.5)
    toplanti_oturum_kapat("Terminal'e alındı")
    cl = ac.get("cl") or claude_yolu()
    sh = (f"#!/bin/bash\n# Suflor.me — arka plandaki toplantı oturumu Terminal'de (her seferinde yeniden yazılır)\ncd {shlex.quote(os.path.expanduser(AYAR['proje']))} || exit 1\n"
          f"exec {shlex.quote(cl)} --resume {shlex.quote(sid)}" + (f" --model {shlex.quote(str(ac['model']))}" if ac.get("model") else "")
          + (f" --settings {shlex.quote(ac['ky'])}" if ac.get("ky") else "") + " " + shlex.quote(TOPO_TERMINAL_ILETI) + "\n")
    cp = os.path.join(AYAR["uygulama"], "toplanti-terminal.command")
    with open(cp, "w", encoding="utf-8") as f: f.write(sh)
    os.chmod(cp, 0o755)
    if not os.environ.get("SUFLOR_TEST_BASLAT"): subprocess.Popen(["open", "-a", "Terminal", cp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _topo_durum("terminalde"); _topo_mesaj("sistem", _t("Oturum Terminal'e alındı; oradan sürer.", "The session moved to Terminal and continues there."))
    print(f"TOPLANTI OTURUMU: Terminal'e alındı ({sid[:8]})"); return {"ok": True}
# /toplanti izle'yi Monitor'la kurar (30 dk'da bir yeniden); proje izinlerinde Monitor yok — Terminal'de her seferinde elle onaylanıyordu. Yalnız Suflor'un
# kendi toplanti-claude.py'si (aktarıcının yanındaki, ayar kod ya da uygulama klasöründeki) ve yalnız `izle` alt komutu kartsız geçer; başka komut kart açar.
TOPO_IZLE_RX = re.compile(r"^(?:PYTHONDONTWRITEBYTECODE=1\s+)?(?:/usr/bin/)?python3\s+(?:-[uBI]+\s+)*(\S+/toplanti-claude\.py)(?:\s+--dir\s+\S+)?(?:\s+--relay\s+http://127\.0\.0\.1:\d+)?\s+izle\s*$")
def _topo_izle_mi(ad, gi):
    m = TOPO_IZLE_RX.match(str(gi.get("command") or "").strip()) if ad == "Monitor" else None
    if not m: return False
    yer = {os.path.realpath(os.path.join(d, "toplanti-claude.py")) for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), AYAR["uygulama"]) if d}
    return os.path.realpath(os.path.expanduser(m.group(1))) in yer
def _topo_izin(o):  # Claude Code'un izin sorusu (can_use_tool) → panoda onay → control_response
    r = o.get("request") or {}; ad = str(r.get("tool_name") or "?"); gi = r.get("input") if isinstance(r.get("input"), dict) else {}
    if _topo_izle_mi(ad, gi):
        cevap = {"behavior": "allow", "updatedInput": gi}; print("TOPLANTI OTURUMU: izin Monitor (izle) → kendiliğinden")
    elif ad == "AskUserQuestion":  # soru düz metin olarak panoya gelsin
        cevap = {"behavior": "deny", "message": _t("Bu oturumda AskUserQuestion yok: soruyu düz metin olarak yaz ve turu bitir; kullanıcı panodan cevaplar.",
                                                   "AskUserQuestion isn't available in this session: write the question as plain text and end the turn; the user answers from the panel.")}
    else:
        ozet = _topo_arac_ozet(ad, gi); TOPO["izin"] += 1
        _topo_mesaj("izin", f"{ad} — {ozet}" if ozet else ad)
        iid = izin_iste("arac", izin_metni(ad, gi), {"arac": ad, "ozet": ozet})  # v0.112.2: kartta düz cümle, komut yalnız ayrıntıda
        k = izin_bekle(iid) if iid else "zaman_asimi"; TOPO["izin"] = max(0, TOPO["izin"] - 1)
        cevap = ({"behavior": "allow", "updatedInput": gi} if k == "onaylandi" else
                 {"behavior": "deny", "message": _t(f"{AYAR.get('ad') or 'Kullanıcı'} reddetti (Suflor); bu adımı atla, gerekirse ona sor." if k == "reddedildi" else
                                                     "Kullanıcı onay vermedi (süre doldu); bu adımı atla, gerekirse ona sor.",
                                                     "The user declined (Suflor); skip this step and ask them if needed." if k == "reddedildi" else
                                                     "No approval from the user (timed out); skip this step and ask them if needed.")})
        print(f"TOPLANTI OTURUMU: izin {ad} → {k}")
    _topo_gonder({"type": "control_response", "response": {"subtype": "success", "request_id": o.get("request_id"), "response": cevap}})
def _topo_oku(cik, nesil):
    try: r = open(cik, encoding="utf-8")
    except OSError: return
    with r:
        for l in r:
            if TOPO["nesil"] != nesil: break
            try: j = json.loads(l)
            except ValueError: continue
            t = j.get("type")
            if t == "system" and j.get("subtype") == "init":  # her turun başında gelir (Monitor olayı da yeni tur açar)
                if j.get("session_id"): TOPO["sid"] = str(j["session_id"])
                if TOPO["durum"] == "bekliyor": _topo_durum("calisiyor")
            elif t == "assistant":
                if TOPO["durum"] == "bekliyor": _topo_durum("calisiyor")  # kullanıcı yazmadan yeni tur (arka plan işi bitti bildirimi vb.)
                for b in ((j.get("message") or {}).get("content") or []):
                    if not isinstance(b, dict): continue
                    if b.get("type") == "text": _topo_mesaj("claude", b.get("text"))
                    elif b.get("type") == "tool_use": _topo_mesaj("arac", (str(b.get("name") or "?") + " — " + _topo_arac_ozet(b.get("name"), b.get("input"))).strip(" —"))
            elif t == "result":
                try: TOPO["maliyet"] = round(TOPO["maliyet"] + float(j.get("total_cost_usd") or 0), 4)
                except (TypeError, ValueError): pass
                if TOPO["durum"] == "calisiyor": _topo_durum("bekliyor")
                print(f"TOPLANTI OTURUMU: tur bitti ({j.get('subtype')}) — kullanıcıyı bekliyor")
            elif t == "control_request" and (j.get("request") or {}).get("subtype") == "can_use_tool":
                threading.Thread(target=_topo_izin, args=(j,), daemon=True).start()
    if TOPO["kapali_nesil"] == nesil or TOPO["nesil"] != nesil: return  # bilerek kapatıldı ya da yenisi açıldı
    TOPO.update(w=None)
    sid, ac = TOPO["sid"], TOPO["acilis"] or {}
    if sid and TOPO["yeniden"] < TOPO_YENIDEN and ac.get("cl"):
        TOPO["yeniden"] += 1; print(f"TOPLANTI OTURUMU: süreç beklenmedik kapandı — kaldığı yerden açılıyor ({TOPO['yeniden']}/{TOPO_YENIDEN})")
        _topo_mesaj("sistem", _t("Oturum beklenmedik kapandı; kaldığı yerden yeniden açıldı.", "The session closed unexpectedly; it was reopened where it left off."))
        if toplanti_oturum_ac(ac["cl"], ac.get("model"), ac.get("ky"), _t("(Suflor) Oturum beklenmedik kapandı ve yeniden açıldı. Kaldığın yerden sür; toplantı sürüyorsa izle döngüsüne dön.",
                                                                          "(Suflor) The session closed unexpectedly and was reopened. Continue where you left off; if the meeting is still on, go back to the izle loop."), sid=sid): return
    _topo_durum("hata", _t("Toplantı oturumu kapandı — Başlat'la yeniden aç ya da Terminal'de göster", "The meeting session closed — press Start again or show it in Terminal"))
    print("TOPLANTI OTURUMU: süreç kapandı (beklenmedik)")
def _topo_bekci(nesil):
    while TOPO["nesil"] == nesil and topo_canli():
        time.sleep(60)
        izliyor = STATE.get("izle_seen") and time.time() - STATE["izle_seen"] < 300
        if TOPO["nesil"] == nesil and TOPO["durum"] == "bekliyor" and not izliyor and time.time() - TOPO["t_durum"] > TOPO_BOSTA_SN:
            _topo_mesaj("sistem", _t("Uzun süredir boşta olduğu için kapandı. Sürdürmek için Terminal'de göster.", "Closed after a long idle period. Use Show in Terminal to continue."))
            toplanti_oturum_kapat("boşta"); return
def topo_izliyor(): return bool(STATE.get("izle_seen")) and time.time() - STATE["izle_seen"] < 60
def toplanti_oturum_view():
    if TOPO["durum"] == "kapali" and not TOPO["n"]: return None
    son = next((m for m in reversed(TOPO["mesaj"]) if m["kim"] == "claude"), None)
    d = TOPO["durum"]
    if d == "bekliyor" and topo_canli() and topo_izliyor(): d = "izliyor"  # tur bitti ama Monitor'daki izle sürüyor: kullanıcıyı beklemiyor, toplantıyı izliyor
    soru = None  # açık soru: seçenekli son ileti (cevaplanana kadar) ya da izlemeden kullanıcıyı bekleyen turun son iletisi
    sm = next((m for m in TOPO["mesaj"] if m["i"] == TOPO["secenek_i"]), None) if TOPO["secenek_i"] and topo_canli() else None
    if sm: soru = {"i": sm["i"], "metin": sm["metin"][-400:], "secenek": sm["secenek"]}
    elif d == "bekliyor" and son: soru = {"i": son["i"], "metin": son["metin"][-400:]}
    return {"durum": d, "n": TOPO["n"], "t0": TOPO["t0"], "izin": TOPO["izin"], "konu": TOPO["konu"], "hata": TOPO["hata"] if TOPO["durum"] == "hata" else None,
            "terminal": bool(TOPO["sid"] and TOPO["acilis"]), "son": (son or {}).get("metin", "")[:300], "son_i": (son or {}).get("i"), "soru": soru}
def toplanti_oturum_mesajlar(n=0):
    with LOCK: m = [x for x in TOPO["mesaj"] if x["i"] > n]
    return dict(toplanti_oturum_view() or {"durum": "kapali", "n": 0}, mesaj=m)
def toplanti_oturum_islem(p):
    i = p.get("islem")
    if i == "yaz":
        if gizli_acik(): return gizli_red()
        return toplanti_oturum_yaz(p.get("metin"), "pano")
    if i == "sec":  # seçenek düğmesi: yalnız açık sorunun kendi seçeneklerinden biri (eski düğmeye basılırsa reddedilir)
        if gizli_acik(): return gizli_red()
        sm = next((m for m in TOPO["mesaj"] if m["i"] == TOPO["secenek_i"]), None) if TOPO["secenek_i"] else None
        if not sm or p.get("i") != sm["i"] or p.get("secim") not in sm["secenek"]: return {"ok": False, "err": _t("Bu soru artık açık değil", "This question is no longer open")}
        return toplanti_oturum_yaz(p["secim"], "düğme")
    if i == "durdur": return toplanti_oturum_durdur()
    if i == "terminal": return toplanti_oturum_terminal()
    if i == "kapat":  # v0.112.0: panodaki Kapat (toplantı sonu işleri yapılmaz; sürdürmek için Terminal'de göster)
        if not topo_canli(): return {"ok": False, "err": _t("Toplantı oturumu açık değil", "The meeting session isn't running")}
        _topo_mesaj("sistem", _t("Oturum kapatıldı. Sürdürmek için Terminal'de göster.", "Session closed. Use Show in Terminal to continue."))
        toplanti_oturum_kapat("kullanıcı kapattı"); return {"ok": True}
    return {"ok": False, "err": "islem: yaz | sec | durdur | terminal | kapat"}
