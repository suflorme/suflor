# --- Deneme toplantısı (duman testi) kipi (Faz D2, S162, v0.148.0; mimari plan §5 Faz D, §3 ilke 3) ---------------------------------------------------------
# 27 Ekim: hataların çoğu ilk kez toplantının ortasında görüldü. Kullanıcı toplantıya girdikten sonra panoda "Deneme toplantısı (3 dk)"e basar; aktarıcı en çok 3 dk süren
# bir denetim listesi koşar, panoda madde madde canlı ✓ / ✗ / ? / bekliyor gösterilir. Kip YALNIZ OKUR: toplantıya hiçbir şey yazmaz, dökümde not düşmez, asistanı
# kendisi konuşturmaz (kullanıcı kısa bir soru sorar; cevabın gelip gelmediğine ve ilk metnin süresine bakılır). Aynı anda tek kip. Toplantı yoksa başlamaz.
# Maddeler: a toplantı tanındı (platform + adın KAYNAĞI: takvim|Başlat|sinyal) · b döküm dosyası açıldı · c her kanaldan (altyazı, ben, karşı) 30 sn içinde satır
# (kanal kurulu/açık değilse ?) — ölçüm aktarici/saglik.py'nin veri_satiri zamanları, ikinci ölçüm yok · d Claude toplantı oturumu açık mı + açılışta kaç izin kartı ·
# e asistan cevabı 60 sn içinde, ilk metin kaç sn'de (bas-konus.py'nin tur kaydından duman_konus) · f toplantiya_ses açıksa BlackHole okunuyor mu · g kaynak (takas, yük).
# f ve g `kurulum.py dogrula --json --hizli --yazma`'nın blackhole ve kaynak maddeleridir (D1 eşikleri; ikinci kod yok; dogrula.json/posta kutusuna yazmaz).
# Sonuç: <uygulama>/duman/<YYYYMMDD-HHMM>.json; beta kullanıcısında (ayar gelistirici yok) ayrıca <ortak>/geri-bildirim/<tarih>-duman-<platform>-<hesap>.md.
# İçerik kuralı kurulum.py _dogrula_temiz ile aynı: yalnız sayı, durum, süre, platform; toplantı/kişi adı, döküm metni, yol yok; ad için yalnız kaynağı.
# /status duman, POST /duman {"islem": "baslat"|"bitir"} (yalnız pano, anahtarlı). Deneme: SUFLOR_TEST_HIZLI süreleri kısaltır.
import getpass as _gp
DUMAN_HIZLI = bool(os.environ.get("SUFLOR_TEST_HIZLI"))
DUMAN_SN, DUMAN_KANAL_SN, DUMAN_SORU_SN, DUMAN_DOGRULA_SN = (24, 5, 8, 3) if DUMAN_HIZLI else (180, 30, 60, 20)
DUMAN = {"aktif": False, "t0": 0.0, "t_bit": None, "platform": None, "kaynak": None, "m": [], "sonuc": None, "dogrula": None, "dogrula_n": 0, "konus": None, "izin_ilk": 0, "dosya": None, "nesil": 0, "yok_t": None}
DUMAN_KISA = {"teams": "Teams", "meet": "Meet", "zoom": "Zoom"}
DUMAN_KANAL_AD = {"altyazi": ("altyazı", "captions"), "ben": ("ben", "me"), "karsi": ("karşı taraf", "other side")}
def _dm_temiz(x):  # kurulum.py _dogrula_temiz ile aynı kural: yol ve kullanıcı adı çıkar
    u = _gp.getuser(); x = re.sub(r"/Users/[^/\s]+", "/Users/[kullanıcı]", str(x))
    return re.sub(rf"\b{re.escape(u)}\b", "[kullanıcı]", x) if u and len(u) > 2 else x
def _dm_platform():
    x = STATE.get("extension") or {}; a = OTO.get("aktif") if "OTO" in globals() else None
    if a and a.get("platform"): return a["platform"]
    if toplanti_var() and x.get("platform"): return x["platform"]
    m = STATE.get("masaustu") or {}
    if m.get("toplantida"): return (MASAUSTU_PLATFORM if "MASAUSTU_PLATFORM" in globals() else {}).get(m.get("uygulama") or "", "bilinmeyen")
    return x.get("platform") or "bilinmeyen"
def _dm_ad_kaynagi():  # adın NEREDEN geldiği (adın kendisi hiçbir yere yazılmaz): takvim | Başlat | sinyal
    now = time.time(); a = OTO.get("aktif") if "OTO" in globals() else None; b = STATE.get("baslatma") or {}
    yakin = bool(b.get("konu") and now - (b.get("at") or 0) < 30 * 60)
    if (a and a.get("olay")) or (yakin and b.get("olay")): return "takvim"
    if yakin and not b.get("oto"): return "Başlat"
    return "sinyal"
def _dm_kanal(k, t0, gecen, x, mas):  # → (durum, not)
    if k == "altyazi":
        if mas and not toplanti_var(): return "?", _t("masaüstü toplantıda altyazı kanalı yok", "no captions channel in a desktop meeting")
        if not (x.get("captions") or x.get("panel")): return "?", _t("altyazı/transkript açık değil", "captions/transcript not on")
    elif k == "ben":
        bk = ben_kod(); neden = {"yok": _t("eklentiden mikrofon bilgisi yok", "no microphone info from the extension"), "kapali": _t("mikrofon kanalı kapalı", "microphone channel off"),
                                 "hata": _t("mikrofon açılamadı", "microphone failed to open"), "sessiz": _t("mikrofon sessizde", "microphone muted")}.get(bk)
        if neden and not (mas and bk == "yok"): return "?", neden
    else:
        yd = yerel_ses_durum(); neden = {"yok": _t("ses yardımcısı kurulu değil", "audio helper not installed"), "kapali": _t("ses yardımcısı kapalı", "audio helper off"),
                                         "izin": _t("ses kaydı izni yok", "no audio recording permission")}.get(yd)
        if neden: return "?", neden
    son = kanal_son(k)
    if son > t0: return "ok", _t(f"satır {round(son - t0)} sn'de geldi", f"line arrived after {round(son - t0)} s")
    if gecen < DUMAN_KANAL_SN: return "bekliyor", _t("satır bekleniyor", "waiting for a line")
    return "hata", _t(f"{DUMAN_KANAL_SN} sn'de satır gelmedi", f"no line within {DUMAN_KANAL_SN} s")
def _dm_oturum(now):  # d: Claude toplantı oturumu açık mı, açılışta kaç izin kartı
    v = toplanti_oturum_view() if "toplanti_oturum_view" in globals() else None; a = OTO.get("aktif") if "OTO" in globals() else None; nd = (a or {}).get("neden") or ""
    iz = max(DUMAN["izin_ilk"], TOPO.get("izin_toplam", 0) if "TOPO" in globals() else 0)
    if v and v.get("durum") in ("calisiyor", "bekliyor", "izliyor", "terminalde"):
        return "ok", _t(f"oturum açık ({v['durum']}), açılışta {iz} izin kartı", f"session open ({v['durum']}), {iz} permission cards at start")
    if v and v.get("durum") == "hata": return "hata", _t("oturum hata verdi", "session errored")
    if nd.startswith("hariç"): return "?", _t("toplantı ayarda hariç tutulmuş", "meeting excluded in settings")
    if "deneme" in nd: return "?", _t("deneme aktarıcısı: oturum açılmaz", "test relay: no session")
    if "güvenilir sinyal" in nd: return "?", _t("yalnız mikrofon + takvim sinyali: oturum önerisi bekliyor", "mic + calendar signal only: session offer pending")
    return "hata", _t("Claude toplantı oturumu açık değil", "Claude meeting session is not open")
def _dm_konus(gecen):  # e: asistan cevabı
    if AYAR.get("konusma") is False or ("konus_beyin_var" in globals() and not konus_beyin_var()): return "?", _t("Konuş kapalı ya da Claude yok", "Talk off or no Claude")
    k = DUMAN["konus"]
    if k and k.get("hata"): return "hata", _t("asistan cevabı hata verdi", "assistant answer failed")
    if k:
        ilk = f"{k['ilk_ms'] / 1000:.1f}" if k.get("ilk_ms") is not None else "?"; top = f"{k['sure_ms'] / 1000:.1f}" if k.get("sure_ms") is not None else "?"
        return "ok", _t(f"cevap geldi: ilk metin {ilk} sn, toplam {top} sn ({k['kaynak']})", f"answer arrived: first text {ilk} s, total {top} s ({k['kaynak']})")
    if gecen < DUMAN_KANAL_SN + DUMAN_SORU_SN: return "bekliyor", _t("asistana kısa bir soru sor", "ask the assistant a short question")
    return "hata", _t(f"{DUMAN_SORU_SN} sn'de cevap gelmedi", f"no answer within {DUMAN_SORU_SN} s")
def _dm_dogrula_madde(i):  # f / g: kurulum.py dogrula'nın maddesi
    d = DUMAN["dogrula"]
    if d is None: return "bekliyor", _t("denetim koşuyor", "check running")
    x = next((y for y in d if y.get("id") == i), None)
    if not x: return "?", _t("denetim okunamadı", "check could not be read")
    return x["durum"], x["not"]
def _dm_maddeler(now):
    t0 = DUMAN["t0"]; gecen = now - t0; x = STATE.get("extension") or {}; mas = bool((STATE.get("masaustu") or {}).get("toplantida")); M = []
    def m(i, ad, d, n, **ek): M.append(dict({"id": i, "ad": ad, "durum": d, "not": _dm_temiz(n)}, **ek))
    plat = DUMAN["platform"] or "bilinmeyen"
    m("a", _t("Toplantı tanındı", "Meeting recognised"), "?" if plat == "bilinmeyen" else "ok", _t(f"platform: {DUMAN_KISA.get(plat, plat)} · ad kaynağı: {DUMAN['kaynak']}", f"platform: {DUMAN_KISA.get(plat, plat)} · name from: {DUMAN['kaynak']}"))
    f = aktif_dosya(); m("b", _t("Döküm dosyası açıldı", "Transcript file opened"), "ok" if f else "hata", _t("dosya açık", "file open") if f else _t("toplantı sürüyor ama döküm dosyası yok", "meeting running but no transcript file"))
    kd = {k: _dm_kanal(k, t0, gecen, x, mas) for k in ("altyazi", "ben", "karsi")}; ds = [v[0] for v in kd.values()]
    cd = "hata" if "hata" in ds else "bekliyor" if "bekliyor" in ds else "?" if "?" in ds else "ok"
    m("c", _t("Her kanaldan satır geldi (30 sn)", "A line from every channel (30 s)"), cd, " · ".join(f"{DUMAN_KANAL_AD[k][0 if ARAYUZ_DILI != 'en' else 1]}: {({'ok': '✓', 'hata': '✗', '?': '?', 'bekliyor': '…'})[v[0]]}" + (f" ({v[1]})" if v[0] in ("?", "hata") else "") for k, v in kd.items()),
      kanal={k: {"durum": v[0], "not": _dm_temiz(v[1])} for k, v in kd.items()})
    m("d", _t("Claude toplantı oturumu", "Claude meeting session"), *_dm_oturum(now))
    m("e", _t("Asistan cevabı", "Assistant answer"), *_dm_konus(gecen))
    if AYAR.get("toplantiya_ses") is True: m("f", _t("BlackHole okunuyor", "BlackHole is read"), *_dm_dogrula_madde("blackhole"))
    else: m("f", _t("BlackHole okunuyor", "BlackHole is read"), "atla", _t("ayar kapalı (toplantiya_ses)", "setting off (toplantiya_ses)"))
    m("g", _t("Mac kaynakları", "Mac resources"), *_dm_dogrula_madde("kaynak"))
    return M
def _dm_dogrula_kos(nesil):  # kurulum.py dogrula'yı (yazmadan) ayrı iş parçacığında koştur; yalnız blackhole ve kaynak maddeleri tutulur
    k = _kod_dir(); d = None
    try:
        if k and os.path.isfile(os.path.join(k, "kurulum.py")):
            p = subprocess.run([sys.executable, "-B", os.path.join(k, "kurulum.py"), "dogrula", "--json", "--hizli", "--yazma"], cwd=k, capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL)
            d = [x for x in json.loads(p.stdout).get("maddeler", []) if x.get("id") in ("blackhole", "kaynak")]
    except Exception as e: print(f"DUMAN: denetim koşmadı ({e.__class__.__name__})")
    if DUMAN["nesil"] == nesil: DUMAN["dogrula"] = d if d else []
def duman_konus(o):  # bas-konus.py: bir Konuş/hitap turu bitti (o = ölçüm kaydı) — kip sürerken ilk cevap sayılır; yalnız süre ve tür saklanır
    if DUMAN["aktif"] and not DUMAN["konus"]:
        DUMAN["konus"] = {"ilk_ms": o.get("ilk_ms"), "sure_ms": o.get("sure_ms"), "hata": bool(o.get("hata")), "kaynak": str(o.get("kaynak") or "bas")[:12]}
def _dm_ozet(M):
    toplam = [x for x in M if x["durum"] != "atla"]; gecti = sum(1 for x in toplam if x["durum"] == "ok"); sorun = []
    ad = DUMAN_KISA.get(DUMAN["platform"] or "", _t("Toplantı", "Meeting"))
    for x in M:
        if x["durum"] != "hata": continue
        if x["id"] == "c": sorun += [(_t(f"{DUMAN_KANAL_AD[k][0]} satırı gelmedi", f"no {DUMAN_KANAL_AD[k][1]} line")) for k, v in x["kanal"].items() if v["durum"] == "hata"]
        else: sorun.append(x["ad"] + ": " + x["not"])
    bel = sum(1 for x in toplam if x["durum"] in ("?", "bekliyor"))
    return f"{ad}: {gecti}/{len(toplam)} " + _t("geçti", "passed") + (" — " + "; ".join(sorun) if sorun else "") + (_t(f" ({bel} belirsiz)", f" ({bel} unclear)") if bel else "")
def _dm_yaz(r):  # <uygulama>/duman/<tarih>.json; beta kullanıcısında ayrıca ortak posta kutusu. İçerik kuralı: yalnız sayı, durum, süre, platform
    ts = time.strftime("%Y%m%d-%H%M", time.localtime(DUMAN["t0"])); d = os.path.join(AYAR["uygulama"], "duman")
    try:
        os.makedirs(d, exist_ok=True); json.dump(r, open(os.path.join(d, ts + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1); DUMAN["dosya"] = ts + ".json"
    except OSError as e: print(f"DUMAN: yazılamadı ({e.__class__.__name__})")
    if not AYAR.get("gelistirici"):
        gb = os.path.join(AYAR.get("ortak") or "/Users/Shared/Suflor", "geri-bildirim"); hesap = re.sub(r"[^a-z0-9_-]", "", _gp.getuser().lower()) or "hesap"
        sim = {"ok": "✓", "hata": "✗", "?": "?", "bekliyor": "…", "atla": "—"}
        try:
            os.makedirs(gb, exist_ok=True)
            open(os.path.join(gb, f"{ts}-duman-{r['platform']}-{hesap}.md"), "w", encoding="utf-8").write(
                f"# Deneme toplantısı — v{r['surum']} ({r['t']}, {r['sure_sn']} sn)\n\nPlatform: {r['platform']} · ad kaynağı: {r['kaynak']}\n\n" + "\n".join(f"- {sim[x['durum']]} **{x['ad']}** — {x['not']}" for x in r["maddeler"]) + f"\n\n{r['ozet']}\n")
        except OSError as e: print(f"DUMAN: posta kutusuna yazılamadı ({e.__class__.__name__})")
def _dm_bitir(neden):
    if not DUMAN["aktif"]: return
    now = time.time(); M = _dm_maddeler(now)
    for x in M:
        if x["durum"] == "bekliyor": x["durum"] = "?"; x["not"] = _t("süre dolmadan bitirildi", "ended before time was up") + (": " + x["not"] if x["not"] else "")
    DUMAN.update(aktif=False, t_bit=now, m=M); ozet = _dm_ozet(M)
    r = {"t": datetime.datetime.fromtimestamp(DUMAN["t0"]).isoformat(timespec="seconds"), "surum": SURUM, "sure_sn": round(now - DUMAN["t0"]), "bitis": neden, "platform": DUMAN["platform"] or "bilinmeyen",
         "kaynak": DUMAN["kaynak"], "maddeler": [{k: x[k] for k in ("id", "ad", "durum", "not") if k in x} | ({"kanal": x["kanal"]} if "kanal" in x else {}) for x in M], "ozet": ozet}
    DUMAN["sonuc"] = ozet; _dm_yaz(r); print("DUMAN: bitti — " + ozet)
def _dm_dongu(nesil):
    while DUMAN["aktif"] and DUMAN["nesil"] == nesil:
        try:
            now = time.time(); gecen = now - DUMAN["t0"]
            if not toplanti_suruyor():
                DUMAN["yok_t"] = DUMAN["yok_t"] or now
                if now - DUMAN["yok_t"] > (4 if DUMAN_HIZLI else 15): _dm_bitir("toplanti-bitti"); return
            else: DUMAN["yok_t"] = None
            if TOPO.get("izin_toplam") is not None: DUMAN["izin_ilk"] = max(DUMAN["izin_ilk"], TOPO["izin_toplam"])
            if DUMAN["dogrula_n"] == 0 and gecen >= DUMAN_DOGRULA_SN: DUMAN["dogrula_n"] = 1; threading.Thread(target=_dm_dogrula_kos, args=(nesil,), daemon=True).start()
            DUMAN["m"] = _dm_maddeler(now)
            if gecen >= DUMAN_SN: _dm_bitir("sure-doldu"); return
        except Exception as e: print(f"DUMAN: tur hatası ({e.__class__.__name__}: {e})")
        time.sleep(0.5 if DUMAN_HIZLI else 1)
def duman_islem(p):
    islem = p.get("islem")
    if islem == "bitir":
        if not DUMAN["aktif"]: return {"ok": False, "err": _t("çalışan deneme yok", "no test running")}
        _dm_bitir("elle"); return {"ok": True, "duman": duman_view()}
    if islem != "baslat": return {"ok": False, "err": "islem"}
    if DUMAN["aktif"]: return {"ok": False, "err": _t("deneme zaten sürüyor", "a test is already running"), "duman": duman_view()}
    if not toplanti_suruyor(): return {"ok": False, "err": _t("önce toplantıya gir", "join a meeting first")}
    DUMAN["nesil"] += 1; DUMAN.update(aktif=True, t0=time.time(), t_bit=None, platform=_dm_platform(), kaynak=_dm_ad_kaynagi(), m=[], sonuc=None, dogrula=None, dogrula_n=0, konus=None, dosya=None, yok_t=None,
                                       izin_ilk=TOPO.get("izin_toplam", 0) if "TOPO" in globals() else 0)
    print(f"DUMAN: başladı — {DUMAN['platform']} · ad kaynağı {DUMAN['kaynak']}"); DUMAN["m"] = _dm_maddeler(time.time())
    threading.Thread(target=_dm_dongu, args=(DUMAN["nesil"],), daemon=True).start(); return {"ok": True, "duman": duman_view()}
def duman_view():  # /status duman: hiç koşmadıysa None
    if not DUMAN["t0"]: return None
    now = time.time(); gecen = round((DUMAN["t_bit"] or now) - DUMAN["t0"])
    return {"aktif": DUMAN["aktif"], "t0": round(DUMAN["t0"]), "gecen": gecen, "sure": DUMAN_SN, "platform": DUMAN["platform"], "kaynak": DUMAN["kaynak"], "maddeler": DUMAN["m"], "ozet": DUMAN["sonuc"], "dosya": DUMAN["dosya"],
            "yonerge": [_t("Mikrofona bir-iki cümle konuş; karşı tarafın da konuşmasını bekle.", "Say a sentence or two; wait for the other side to speak too."), _t("Şimdi asistana kısa bir soru sor.", "Now ask the assistant a short question.")] if DUMAN["aktif"] else []}
