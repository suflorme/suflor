# Suflor.me aktarıcı bölümü: Toplantı oturumu arka planda (v0.111.0; kullanıcı 22 Ekim: "kullanıcının Claude Code terminalini görmesine gerek yok").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("toplanti-oturum")): AYAR, BASE, STATE, LOCK, _t, claude_yolu, BRIFING_APP,
# izin_iste, izin_bekle, gizli_acik … import etme. Python 3.9 uyumlu.
# Panodan Başlat'la açılan toplantı oturumu (/toplanti) Terminal yerine Suflor Brifing.app'in toplantı kipinde çalışır: `claude -p` stream-json giriş/çıkış,
# iki FIFO (bas-konuş açık süreç kipiyle aynı yol; Masaüstü izni o uygulamada). Oturumun kullanıcıya yazdıkları panoda "Claude" bölümünde görünür;
# tur bitince (sonuç iletisi) oturum kullanıcıyı bekler ve kutuya yazılan metin ona gider. Tur sürerken kutu eski yolla (izle GİRDİ) gider.
# Proje izinlerinde olmayan araç: Claude Code soruyu stdio'dan sorar (can_use_tool) → izin_iste (v0.115.0: kart değil, Claude bölümünde ve mini panoda
# Onayla / Reddet; toplantı dışında sesli) → karar.
# Panoda Durdur (interrupt) ve "Terminal'de göster" (süreç kapanır, aynı oturum `claude --resume` ile Terminal'de açılır). Süreç beklenmedik çıkarsa
# aynı oturum en çok TOPO_YENIDEN kez kaldığı yerden açılır. Ayar toplanti_terminal: true eski davranış (Terminal penceresi).
TOPO = {"app": None, "w": None, "durum": "kapali", "sid": None, "mesaj": [], "n": 0, "konu": None, "t0": 0.0, "t_durum": 0.0, "maliyet": 0.0, "nesil": 0,
        "kapali_nesil": None, "yeniden": 0, "izin": 0, "izin_toplam": 0, "hata": None, "acilis": None, "secenek_i": None, "etkinlik": None, "kilit": threading.RLock(), "kilit_sozluk": {}}
TOPO_YENIDEN, TOPO_MESAJ_EN_COK, TOPO_METIN_EN_COK, TOPO_SURE_SN = 2, 400, 6000, 8 * 3600
TOPO_TERMINAL_ILETI = "(Suflor) Oturum arka plandan Terminal'e alındı; arka plandaki Monitor durdu. Toplantı sürüyorsa izle'yi yeniden başlat, sürmüyorsa kaldığın yerden devam et."
TOPO_BOSTA_SN = 2 * 3600  # tur bitmiş ve izle yokken bu kadar boşta kalırsa süreç kapanır (~250 MB); "Terminal'de göster" yine aynı oturumu açar
TOPO_ISTEM = ("Bu toplantı oturumu Suflor.me panosundan arka planda açıldı; Terminal penceresi yok. Kullanıcıya yazdığın her metin panoda asistanın bölümünde "
              "görünür; kullanıcı yalnız asistanı tanır: kendinden asistanın adıyla söz et, 'Claude' deme; kullanıcı panodaki kutudan yazar. Kullanıcıya soru sorman gerekiyorsa soruyu kısa ve açık yaz, sonra turu bitir (cevap yeni ileti "
              "olarak gelir); AskUserQuestion aracını kullanma. Toplantı sürerken izle döngüsünü bırakma. Kancanın 'Terminal'den onay iste' demesi bu "
              "oturumda panodan onay demektir. Araç çağrılarında açıklama (description) alanını Türkçe, kullanıcıya düz bir cümleyle yaz — ne yapacağını ve "
              "gerekiyorsa neden (ör. \"Kulis'in veri dosyasını okuyup test listesini çıkarmak\"); komut, kod ya da dosya yolu yazma: onay kartında bu cümle görünür. Kullanıcıdan seçim isterken (onay, evet/hayır, birkaç seçenek) mesajının son satırına seçenekleri "
              "şu biçimde yaz: [[seç: Seçenek 1 | Seçenek 2 | Seçenek 3]] — en çok 5 seçenek, her biri kısa; panoda düğme olur, basılan seçenek cevap "
              "olarak gelir. Kullanıcı düğme yerine serbest metin de yazabilir.")
# Dış bilgi kaynağı (30 Ekim; kullanıcı onayı: toplantıda konuşulan konuyla ilgili güncel veri kaynaktan çekilip bilgi kartına yazılabilir — sorgu metni
# o kaynağa gider, asistan sesli konuşmaz). Ayar toplanti_bilgi_kaynaklari = [{"sunucu": "<MCP sunucu adı>", "araclar": ["get_*", …], "konu": "…", "ad": "…"}];
# yoksa kapalı. Sunucu adı claude -p'deki biçimiyle ya da araç adındaki biçimiyle yazılabilir ("claude.ai X Y" → araç mcp__claude_ai_X_Y__<araç>).
# Ayardaki sunucunun yalnız okuma adlı (BILGI_OKUMA_RX) ve listedeki desene uyan araçları sorulmadan geçer (oturumda en çok TOPO_BILGI_EN_COK; sonrası sorulur);
# aynı sunucunun öbür araçları reddedilir; başka MCP araçları eskisi gibi sorulur. Aynı kural toplanti-claude.py izin-kanca'da (bilgi_kaynagi_arac): ikisini birlikte değiştir.
BILGI_OKUMA_RX = re.compile(r"^(?:get|list|query|compare|search|fetch|read|describe|lookup|find)_[A-Za-z0-9_]+$")
BILGI_YAZMA = {"send", "forward", "reply", "create", "update", "delete", "remove", "trash", "upload", "share", "move", "rename", "copy", "respond", "set", "write",
               "post", "put", "patch", "edit", "modify", "add", "insert", "pause", "resume", "enable", "disable", "publish", "archive", "cancel", "approve", "execute",
               "run", "javascript", "navigate", "computer", "label", "draft", "mark", "schedule", "import", "sync", "trigger", "start", "stop", "apply", "assign",
               "invite", "grant", "revoke", "reset", "change", "save", "submit", "merge", "duplicate", "launch", "activate", "deactivate"}
BILGI_RISK_RX = re.compile(r"send|forward|reply|create_event|update_event|delete|trash|javascript|navigate|computer|form_input|file_upload|share_file|upload|"
                           r"move_item|rename_item|update_file|create_file|copy_file|respond_to_event|set_vacation|create_filter|label_", re.I)  # = toplanti-claude.py IZIN_MCP
TOPO_BILGI_EN_COK = 200  # 5 Kasım: eski tavan 8'di, gerçek toplantıda dolup her sorguda onay çıktı; şimdi yalnız kaçak döngü sigortası
def mcp_sunucu_adi(s):  # Claude Code'un araç adındaki sunucu biçimi (claude.ai bağlayıcısında alt çizgiler birleşir, baş/son atılır)
    s = str(s or "").strip(); r = re.sub(r"[^A-Za-z0-9_-]", "_", s)
    return re.sub(r"_+", "_", r).strip("_") if s.startswith("claude.ai ") else r
# Kişi/firma kaynağı varsayılanı (5 Kasım): ayarda kisi_kaynaklari yoksa Apollo, yalnız KREDİ HARCAMAYAN okuma araçlarıyla (araç açıklamalarından doğrulandı: people_api_search ve
# organizations_lookup ücretsiz; mixed_companies_search ve organizations_job_postings 1 kredi, enrich/match/bulk kredi harcar → kapalı; diğer her Apollo aracı reddedilir). Kapatmak: kisi_kaynaklari: [].
KISI_VARSAYILAN = [{"sunucu": "plugin:sales:apollo", "araclar": [], "okuma": ["apollo_mixed_people_api_search", "apollo_organizations_lookup"], "konu": "kişi ve firma bilgisi (ad, unvan, şirket, alan adı); e-posta/telefon açma yok", "ad": "Apollo"}]
def kisi_kaynaklari_liste():
    v = AYAR.get("kisi_kaynaklari"); return KISI_VARSAYILAN if v is None else (v if isinstance(v, list) else [])
def bilgi_kaynaklari():
    out = []
    for k in list(AYAR.get("toplanti_bilgi_kaynaklari") or []) + list(kisi_kaynaklari_liste()):  # kisi_kaynaklari (5 Kasım): kişi/firma bilgi bağlayıcıları, aynı şema; "okuma" = adı okuma önekli olmayan okuma araçlarının tam adları
        if not isinstance(k, dict) or not str(k.get("sunucu") or "").strip(): continue
        ok_ = [str(x).strip() for x in (k.get("okuma") or []) if re.fullmatch(r"[A-Za-z0-9_]{1,64}", str(x).strip())]
        ar = [str(x).strip() for x in (k.get("araclar") or []) if re.fullmatch(r"[A-Za-z0-9_*?]{1,64}", str(x).strip())]
        ad = " ".join(str(k.get("ad") or re.sub(r"^claude\.ai\s+", "", str(k["sunucu"]).strip())).split())[:60]
        u = str(k.get("url") or "").strip()  # yalnız Konuş kullanır (https; claude.ai bağlayıcısının sunucu adresi, allowedMcpServers için); toplantı oturumu bakmaz
        out.append({"sunucu": mcp_sunucu_adi(k["sunucu"]), "araclar": ar, "okuma": ok_, "kisi": k in kisi_kaynaklari_liste(), "konu": " ".join(str(k.get("konu") or "").split())[:200], "ad": ad, "url": u if len(u) <= 200 and re.fullmatch(r"https://[^\s\"'\\]+", u) else ""})
    return out
def bilgi_kaynagi_arac(ad):  # ayardaki bir kaynağın aracıysa {"kaynak", "arac", "izinli"}, değilse None
    import fnmatch
    ad = str(ad or "")
    for k in bilgi_kaynaklari():
        on = "mcp__" + k["sunucu"] + "__"
        if not ad.startswith(on): continue
        a = ad[len(on):]
        izinli = (bool(BILGI_OKUMA_RX.match(a)) and not (set(a.lower().split("_")) & BILGI_YAZMA) and not BILGI_RISK_RX.search(a)
                  and any(fnmatch.fnmatchcase(a, d) for d in k["araclar"])) or (a in k.get("okuma", []) and not (set(a.lower().split("_")) & BILGI_YAZMA) and not BILGI_RISK_RX.search(a))
        return {"kaynak": k, "arac": a, "izinli": izinli}
    return None
# Web araştırması (5 Kasım; kullanıcı kararı, gizlilik istisnası): ayar web_arastirma (varsayılan açık) — WebSearch/WebFetch açıkken müşteri, rakip ya da kişi hakkında
# açık kaynak (web, LinkedIn'in herkese açık sayfası) araştırılabilir. Sınır istemde ve kodda: aramaya yalnız firma/kişi adı ve konu gider (döküm alıntısı, iç sayı, toplantı
# içeriği, dosya adı gitmez); gizli toplantıda web yok (_topo_web_red); WebFetch yalnız genel internet adresleri. Onaysız geçiş ayar bilgi_onaysiz'a bağlı.
TOPO_WEB = ("WebSearch", "WebFetch"); TOPO_WEB_EN_COK = 60
TOPO_WEB_ISTEM = (" Web araştırması (WebSearch, WebFetch) açık: toplantıda geçen müşteri, rakip ya da kişi hakkında açık kaynaktan (web, herkese açık sayfalar) bilgi toplayabilirsin. "
                  "SINIR: aramaya yalnız firma ya da kişi adı ve konu gider; döküm alıntısı, iç sayı, toplantı içeriği ve dosya adı arama metnine asla girmez. Gizli toplantıda web araması yok. "
                  "Sonucu not kartı olarak yaz; --neden'de 'Kaynak: <site>, <bağlantı>' ve bulgunun tarihini ver; tek kaynaktan gelen bilgiyi 'doğrulanmadı' diye işaretle.")
# Claude in Chrome (5 Kasım; kullanıcı: kendi LinkedIn oturumu açıkken sormadan okunabilir): oturum `--chrome` ile açılır (toplanti_oturum_ac). Yalnız linkedin.com'da
# OKUMA: sekme açma/kapama, navigate (yalnız linkedin.com adresi), get_page_text, find, read_page. Tıklama, form, betik, yükleme vb. her şey reddedilir. Chrome kapalı,
# eklenti bağlı değil ya da oturum kapalıysa araç hata verir/yoktur → istem zinciri: kişi bağlayıcısı → web araması; hiçbir adım toplantıyı ya da izin kuyruğunu bekletmez
# (her izin sorusu kendi iş parçacığında, aktarıcı Chrome'u açmaz). Aynı kural kanca yolunda izin.py izin_arac → topo_chrome_karar.
TOPO_CHROME_ON = "mcp__claude-in-chrome__"
TOPO_CHROME_OKU = {"tabs_context_mcp", "tabs_create_mcp", "tabs_close_mcp", "navigate", "get_page_text", "find", "read_page", "list_connected_browsers"}
def topo_chrome_acik(): return topo_web_acik() and AYAR.get("linkedin_chrome") is not False
def topo_chrome_karar(ad, gi):  # Chrome aracı değilse None; "allow" | "deny"
    ad = str(ad or "")
    if not ad.startswith(TOPO_CHROME_ON): return None
    k = ad[len(TOPO_CHROME_ON):]; gi = gi if isinstance(gi, dict) else {}
    if k not in TOPO_CHROME_OKU or not topo_chrome_acik() or gizli_acik(): return "deny"
    if k == "navigate":
        m = re.match(r"^https://([A-Za-z0-9.-]+)(?::443)?(?:[/?#]|$)", str(gi.get("url") or ""))
        if not m or not re.fullmatch(r"(?:[a-z0-9-]+\.)*linkedin\.com", m.group(1).lower()): return "deny"
    return "allow"
TOPO_KISI_ISTEM = (" Kişi/firma araştırması için kaynak sırası (her adım hata verirse sessizce sonrakine geç, toplantıyı bekletme; bir adım 5 sn'de cevap vermezse bırak): "
                   "1) Claude in Chrome (mcp__claude-in-chrome__ araçları ağır olduğu için önce ToolSearch ile yükle): YALNIZ linkedin.com'da ve YALNIZ OKUMA — sekme aç (tabs_create_mcp), navigate, get_page_text, find, read_page; "
                   "arama kutusuna yazmak, tıklamak, bağlantı isteği, mesaj, beğeni, takip, profil düzenleme gibi hiçbir yazma eylemi yok, şifre girme yok; Chrome açık değilse, araçlar yoksa ya da LinkedIn "
                   "oturumu kapalıysa (giriş sayfası gelirse) 'LinkedIn'de oturum açık değil' diye not al, Chrome'u açmaya çalışma, kendi açtığın sekmeyi kapat ve sonrakine geç. "
                   "2) Kişi/firma bilgi bağlayıcısı (yukarıdaki listede varsa; yalnız izinli okuma araçları — kredi harcayan zenginleştirme ve e-posta/telefon açma yok, onlar reddedilir; araç çağrısı yalnız kişi/firma adı ve alan adı alır). 3) WebSearch (gerekirse 'site:linkedin.com' ya da firmanın kendi sitesi) — her zaman son yedek. "
                   "Kartın --neden satırına hangi kaynaktan geldiğini yaz (ör. 'Kaynak: LinkedIn (Chrome), <bağlantı>' ya da 'Kaynak: web, <bağlantı>').")
def topo_web_acik(): return AYAR.get("web_arastirma") is not False
def _topo_kisi_kaynak(ad):  # günlük etiketi: chrome | bağlayıcı (kisi_kaynaklari) | web
    ad = str(ad or "")
    if ad.startswith(TOPO_CHROME_ON): return "chrome"
    if ad in TOPO_WEB: return "web"
    bk = bilgi_kaynagi_arac(ad)
    return "bağlayıcı" if bk and bk["kaynak"].get("kisi") else None
def topo_istem():
    ks = bilgi_kaynaklari(); web = (TOPO_WEB_ISTEM + TOPO_KISI_ISTEM.replace("1) Claude in Chrome", "1) Claude in Chrome" if topo_chrome_acik() else "1) (Chrome kapalı: atla) Claude in Chrome")) if topo_web_acik() else ""
    if not ks: return TOPO_ISTEM + web
    return TOPO_ISTEM + web + " Toplantıda kullanabileceğin dış bilgi kaynakları (yalnız okuma; toplantı kurallarındaki 'Dış bilgi kaynağı' maddesine göre): " + "; ".join(
        f"«{k['ad']}» — konu: {k['konu'] or 'belirtilmedi'}; araçlar: mcp__{k['sunucu']}__ altında {', '.join(k['araclar']) or '(yok)'}" for k in ks) + \
        ". Sonucu not kartı olarak yaz; --neden'de 'Kaynak: <kaynak adı>, <sorgu saati>'. Sorguya kişi adı ya da dökümden alıntı koyma."
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
# v0.115.0 (kullanıcı, 22 Ekim test toplantısı: "neden bekliyorsun" — Claude'un ne yaptığı görünmüyordu, Terminal'e geçti): panoda ve mini panoda tek satır
# canlı durum "Claude şu an: <araç cümlesi>…". Cümle aracın açıklamasından (TOPO_ISTEM Türkçe düz cümle yazdırır) ya da araç türünden (arac_cumlesi);
# araç sonucu, metin ya da tur sonu gelince silinir (satır "düşünüyor" der). Komut ve dosya yolu yalnız Ayrıntı'da.
def _topo_etkinlik(ad, gi):
    gi = gi if isinstance(gi, dict) else {}
    metin = _t("toplantıyı izlemek", "watching the meeting") if _topo_izle_mi(ad, gi) else arac_cumlesi(ad, gi)
    TOPO["etkinlik"] = {"metin": metin[:200], "t": time.time()}
def _topo_gonder(o):
    w = TOPO["w"]
    if not w: return False
    try: w.write(json.dumps(o, ensure_ascii=False) + "\n"); w.flush(); return True
    except (OSError, ValueError): return False
def toplanti_oturum_ac(cl, model, ky, ilk, konu=None, sid=None):
    # cl: claude yolu · model: ayar claude_model · ky: toplanti-kanca.json (ya da None) · ilk: ilk kullanıcı iletisi · sid: kaldığı yerden (--resume)
    with TOPO["kilit"]:
        TOPO["izin_toplam"] = 0  # deneme toplantısı kipi: açılışta kaç izin kartı çıktı (aktarici/duman.py)
        if topo_canli(): toplanti_oturum_kapat("yeni başlatma")
        gir, cik, istek = (os.path.join(BASE, f) for f in ("toplanti-giris.fifo", "toplanti-cikis.fifo", "toplanti-istek.json"))
        for f in (gir, cik):
            try: os.remove(f)
            except OSError: pass
            os.mkfifo(f, 0o600)
        args = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--permission-prompt-tool", "stdio",
                "--append-system-prompt", topo_istem()] + (["--chrome"] if topo_chrome_acik() else []) + (["--model", str(model)] if model else []) + (["--settings", ky] if ky else []) + (["--resume", sid] if sid else [])
        fd = os.open(istek, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"kip": "toplanti", "claude": cl, "args": args, "cwd": AYAR["calisma"], "cikti": os.path.join(BASE, "toplanti-bos"),
                       "giris": gir, "cikis": cik, "sure": TOPO_SURE_SN}, f, ensure_ascii=False)
        if not sid: TOPO.update(izin_hatirla=set(), mesaj=[], n=TOPO["n"], sid=None, secenek_i=None, konu=konu, t0=time.time(), maliyet=0.0, yeniden=0, izin=0, hata=None, etkinlik=None,
                                bilgi_sorgu=0, web_sorgu=0, bilgi_t={})
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
    _topo_durum("terminalde"); _topo_mesaj("sistem", _t("Oturum Terminal'e alındı; oradan sürer. Arka plandaki toplantı izlemesi durdu ve kutuya yazdıkların artık oturuma gitmez — Terminal'de yaz.",
                                                    "The session moved to Terminal and continues there. Background meeting watching stopped and what you type in the box no longer reaches the session — type in Terminal."))
    print(f"TOPLANTI OTURUMU: Terminal'e alındı ({sid[:8]})"); return {"ok": True}
# /toplanti izle'yi Monitor'la kurar (30 dk'da bir yeniden); proje izinlerinde Monitor yok — Terminal'de her seferinde elle onaylanıyordu. Yalnız Suflor'un
# kendi toplanti-claude.py'si (aktarıcının yanındaki, ayar kod ya da uygulama klasöründeki) ve yalnız `izle` alt komutu kartsız geçer; başka komut kart açar.
TOPO_IZLE_RX = re.compile(r"^(?:PYTHONDONTWRITEBYTECODE=1\s+)?(?:/usr/bin/)?python3\s+(?:-[uBI]+\s+)*(\S+/toplanti-claude\.py)(?:\s+--dir\s+\S+)?(?:\s+--relay\s+http://127\.0\.0\.1:\d+)?\s+izle\s*$")
def _topo_izle_mi(ad, gi):
    m = TOPO_IZLE_RX.match(str(gi.get("command") or "").strip()) if ad == "Monitor" else None
    if not m: return False
    yer = {os.path.realpath(os.path.join(d, "toplanti-claude.py")) for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), AYAR["uygulama"]) if d}
    return os.path.realpath(os.path.expanduser(m.group(1))) in yer
# Faz A (S162, 27 Ekim: toplantıda her okuma için onay soruluyordu, Monitor 30 dk'da bir yenilenince yeniden soruldu): salt okuma araçları (Read, Grep, Glob), Suflor'un kendi
# okuma komutları ve toplantı sonu döküm kaydı sorulmaz; verilen izin oturum boyunca hatırlanır. Yazma, dışarıya gönderim ve satır içi python yine sorulur
# (izin-kanca ayrıca PreToolUse'ta riskliyi sorar; o kanca bu karardan bağımsızdır).
TOPO_OKU_ARAC = {"Read", "Grep", "Glob"}
TOPO_TC_OKUMA = {"saglik", "takvim", "gundem", "durum", "ara", "hazirlik", "hazir", "graf", "vt-sema", "vt-sor", "proje", "proje-notu", "olcum", "izle",
                 "dokum"}  # dokum: toplantı sonu temiz döküm kaydı (proje klasörüne yazar) — izne bağlı kalmaz
TOPO_TC_RX = re.compile(r"^(?:PYTHONDONTWRITEBYTECODE=1\s+)?(?:/usr/bin/)?python3\s+(?:-[uBI]+\s+)*(\S+/toplanti-claude\.py)(?:\s+--dir\s+\S+)?(?:\s+--relay\s+http://127\.0\.0\.1:\d+)?\s+([a-z-]+)((?:\s+[^\s;&|`$()<>\\\"']+|\s+\"[^\"`$\\]*\"|\s+'[^']*')*)\s*$")
def _topo_tc_okuma(ad, gi):
    c = str(gi.get("command") or "").strip(); m = TOPO_TC_RX.match(c) if ad == "Bash" and "\n" not in c and "\r" not in c else None
    if not m or m.group(2) not in TOPO_TC_OKUMA: return False
    yer = {os.path.realpath(os.path.join(d, "toplanti-claude.py")) for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), AYAR["uygulama"]) if d}
    return os.path.realpath(os.path.expanduser(m.group(1))) in yer
# 31 Ekim (test toplantısı: oturum kendi rutin adımları için izin kartı açtı): dar, kesin kalıplı otomatik izin. Yalnız (1) canlı klasördeki agenda.json / hazir.json ile
# özet klasöründeki (<çalışma>/gorusmeler) .md ve .json dosyalarına Write/Edit, (2) `sleep 1–120` ve `python3 -c "import time; time.sleep(N)"`, (3) bu oturumun
# toplanti-claude.py'sinin kayıt amaçlı alt komutları, (4) özet klasörü içinde iki yol arasında `mv`. Hedef yollar realpath ile çözülür (.. ve sembolik bağ dışarı kaçamaz).
# Başka her şey eskisi gibi sorulur. Kanca (toplanti-claude.py izin-kanca) aynı bekleme kalıbını riskli saymaz: IZIN_BEKLE_RX'i birlikte değiştir.
TOPO_TC_OTO = {"maliyet", "sonuc", "yapi", "bitir", "ozet-hazir"}  # dışarıya göndermeyen, silmeyen, ayar değiştirmeyen kayıt komutları; eylem/ilet/rapor/geri-bildirim/sozluk/hafiza/konusmaci dahil DEĞİL
TOPO_SLEEP_RX = re.compile(r"^sleep (\d{1,3})$")
TOPO_PYSLEEP_RX = re.compile(r"^(?:/usr/bin/)?python3 (?:-[BIu]+ )?-c (['\"])import time; ?time\.sleep\((\d{1,3})\)\1$")
TOPO_OLCUM_RX = re.compile(r"^(?:PYTHONDONTWRITEBYTECODE=1 )?(?:/usr/bin/)?python3 (?:-B )?(\S+/\.claude/skills/suflor-olcum/olcum\.py) toplanti --kaydet$")
TOPO_META_RX = re.compile(r"[;&|`$()<>\\\n\r]")
def _topo_oz_klasorler():  # özet klasörü <çalışma>/gorusmeler; deneme toplantısında (toplanti.md: --cikti <kod>/testler) <kod>/testler — 31 Ekim testinde özet ve .yapi.json oraya yazıldığı için kartlandı
    k = []
    if AYAR.get("calisma"): k.append(os.path.realpath(os.path.join(os.path.expanduser(str(AYAR["calisma"])), "gorusmeler")))
    if AYAR.get("kod"): k.append(os.path.realpath(os.path.join(os.path.expanduser(str(AYAR["kod"])), "testler")))
    return k
def _topo_oz_icinde(yol, dosya=True):
    yol = str(yol or "")
    if not yol or "\0" in yol: return False
    g = os.path.realpath(os.path.expanduser(yol)); ad = os.path.basename(g)
    for k in _topo_oz_klasorler():
        if os.path.dirname(g) == k or g.startswith(k + os.sep):  # eski toplantının belgesi üzerine yazılmaz: yalnız yeni dosya ya da adında bugünün tarihi olan
            return not dosya or (not ad.startswith(".") and ad.endswith((".md", ".json")) and (not os.path.exists(g) or time.strftime("%Y%m%d") in ad or time.strftime("%Y-%m-%d") in ad))
    return False
def _topo_oto(ad, gi):  # kural uyuyorsa kısa açıklama (günlük için), değilse None
    if ad in ("Write", "Edit"):
        yol = str(gi.get("file_path") or "")
        if not yol or "\0" in yol: return None
        g = os.path.realpath(os.path.expanduser(yol))
        if g in {os.path.realpath(os.path.join(BASE, f)) for f in ("agenda.json", "hazir.json")} or _topo_oz_icinde(yol): return f"{ad} {os.path.basename(g)}"
        return None
    if ad != "Bash": return None
    c = str(gi.get("command") or "").strip()
    m = TOPO_SLEEP_RX.match(c) or TOPO_PYSLEEP_RX.match(c)
    if m: n = int(m.group(m.lastindex)); return f"Bash bekleme {n} sn" if 1 <= n <= 120 else None
    if TOPO_META_RX.search(c): return None
    m = TOPO_OLCUM_RX.match(c)  # toplantı sonu teknik ölçüm raporu (toplanti.md adım 6): kodun kendi olcum.py'si, yalnız `toplanti --kaydet` (testler/olcum-toplanti-<tarih>.md'ye yazar)
    if m and AYAR.get("kod") and os.path.realpath(os.path.expanduser(m.group(1))) == os.path.realpath(os.path.join(os.path.expanduser(str(AYAR["kod"])), ".claude/skills/suflor-olcum/olcum.py")): return "Bash olcum toplanti --kaydet"
    m = TOPO_TC_RX.match(c)
    if m and m.group(2) in TOPO_TC_OTO and os.path.realpath(os.path.expanduser(m.group(1))) in _topo_tc_yerler(): return f"Bash toplanti-claude {m.group(2)}"
    try: av = shlex.split(c)
    except ValueError: return None
    if av and av[0] == "mv":
        yollar = [x for x in av[1:] if not x.startswith("-")]; secenek = [x for x in av[1:] if x.startswith("-")]
        if len(yollar) == 2 and all(x in ("-n",) for x in secenek) and all(_topo_oz_icinde(y) for y in yollar): return "Bash mv (özet klasörü)"
    return None
def _topo_tc_yerler(): return {os.path.realpath(os.path.join(d, "toplanti-claude.py")) for d in (os.path.dirname(os.path.abspath(__file__)), os.path.expanduser(str(AYAR.get("kod") or "")), AYAR["uygulama"]) if d}
def _topo_okuma_arac(ad):  # girdiden bağımsız hatırlanabilen araç: web araçları ve yazma izi taşımayan MCP okuma araçları (5 Kasım: aynı araç farklı girdiyle yeniden soruluyordu)
    if ad in TOPO_WEB or (ad.startswith(TOPO_CHROME_ON) and ad[len(TOPO_CHROME_ON):] in TOPO_CHROME_OKU): return True
    k = ad.split("__")[-1]
    return ad.startswith("mcp__") and bool(BILGI_OKUMA_RX.match(k)) and not (set(k.lower().split("_")) & BILGI_YAZMA) and not BILGI_RISK_RX.search(k)
def _topo_izin_anahtar(ad, gi):
    if _topo_okuma_arac(ad): return ad
    return ad + "\0" + (str(gi.get("command") or "") if ad in ("Bash", "Monitor") else json.dumps(gi, sort_keys=True, ensure_ascii=False))
def _topo_web_red(ad, gi):  # web aracı reddedilecekse Türkçe/İngilizce neden, yoksa None
    if not topo_web_acik(): return _t("Web araştırması kapalı (ayar).", "Web research is turned off (setting).")
    if gizli_acik(): return _t("Gizli toplantıda web araması yok.", "No web search in a private meeting.")
    if ad == "WebFetch":
        u = str(gi.get("url") or ""); m = re.match(r"^https?://([^/:?#@\s]+)(?::\d+)?(?:[/?#]|$)", u, re.I); h = (m.group(1) if m else "").lower()
        if not m or h in ("localhost", "0.0.0.0") or h.endswith((".local", ".internal", ".localhost", ".lan")) or re.match(r"^(\d{1,3}\.){3}\d{1,3}$", h) or ":" in h or "." not in h:
            return _t("Yalnız genel internet adresleri açılır.", "Only public internet addresses can be opened.")
    return None
def _topo_izin(o):  # Claude Code'un izin sorusu (can_use_tool) → panoda onay → control_response
    r = o.get("request") or {}; ad = str(r.get("tool_name") or "?"); gi = r.get("input") if isinstance(r.get("input"), dict) else {}
    hat = TOPO.setdefault("izin_hatirla", set()); anh = _topo_izin_anahtar(ad, gi); bk = bilgi_kaynagi_arac(ad)
    try: oto = _topo_oto(ad, gi)
    except Exception: oto = None
    onaysiz = AYAR.get("bilgi_onaysiz") is not False  # 5 Kasım: varsayılan açık — okuma araçları ve web araması sorulmaz
    web_red = _topo_web_red(ad, gi) if ad in TOPO_WEB else None
    if web_red:
        cevap = {"behavior": "deny", "message": web_red}; print(f"TOPLANTI OTURUMU: izin {ad} (web) → reddedildi ({web_red})")
    elif ad in TOPO_WEB and onaysiz and TOPO.get("web_sorgu", 0) < TOPO_WEB_EN_COK:
        TOPO["web_sorgu"] = TOPO.get("web_sorgu", 0) + 1; cevap = {"behavior": "allow", "updatedInput": gi}
        print(f"TOPLANTI OTURUMU: izin {ad} (web araştırması {TOPO['web_sorgu']}/{TOPO_WEB_EN_COK}) → kendiliğinden")
    elif ad.startswith(TOPO_CHROME_ON) and topo_chrome_karar(ad, gi) == "deny":
        cevap = {"behavior": "deny", "message": _t("Claude in Chrome'da yalnız linkedin.com'u okuma araçları açık (sekme, navigate, get_page_text, find, read_page).", "Only read tools on linkedin.com are open in Claude in Chrome.")}
        print(f"KİŞİ ARAŞTIRMA: chrome · {ad[len(TOPO_CHROME_ON):]} → reddedildi")
    elif ad.startswith(TOPO_CHROME_ON) and onaysiz:
        cevap = {"behavior": "allow", "updatedInput": gi}; print(f"KİŞİ ARAŞTIRMA: chrome · {ad[len(TOPO_CHROME_ON):]} → kendiliğinden")
    elif bk and not bk["izinli"]:  # ayardaki bilgi kaynağının okuma dışı aracı: sorulmaz, reddedilir
        cevap = {"behavior": "deny", "message": _t("Bu araç bilgi kaynağının okuma araçlarından değil; toplantıda yalnız okuma araçları kullanılır.",
                                                   "This tool isn't one of the information source's read tools; only read tools are used in the meeting.")}
        print(f"TOPLANTI OTURUMU: izin {bk['kaynak']['sunucu']} · {bk['arac']} (bilgi kaynağı, okuma dışı) → reddedildi")
    elif bk and onaysiz and TOPO.get("bilgi_sorgu", 0) < TOPO_BILGI_EN_COK:
        TOPO["bilgi_sorgu"] = TOPO.get("bilgi_sorgu", 0) + 1; cevap = {"behavior": "allow", "updatedInput": gi}
        print(f"TOPLANTI OTURUMU: izin {bk['kaynak']['sunucu']} · {bk['arac']} (bilgi kaynağı, okuma {TOPO['bilgi_sorgu']}/{TOPO_BILGI_EN_COK}) → kendiliğinden")
    elif _topo_izle_mi(ad, gi):
        cevap = {"behavior": "allow", "updatedInput": gi}; print("TOPLANTI OTURUMU: izin Monitor (izle) → kendiliğinden")
    elif ad in TOPO_OKU_ARAC or _topo_tc_okuma(ad, gi):
        cevap = {"behavior": "allow", "updatedInput": gi}; print(f"TOPLANTI OTURUMU: izin {ad} (salt okuma) → kendiliğinden")
    elif oto:
        cevap = {"behavior": "allow", "updatedInput": gi}; print(f"İZİN: otomatik — {oto}")  # beta sayacı: beta-veri.py BETA_RX "oto_izin" (satır metni tutulmaz)
    elif anh in hat:
        cevap = {"behavior": "allow", "updatedInput": gi}; print(f"TOPLANTI OTURUMU: izin {ad} → oturumda daha önce verilmişti")
    elif ad == "AskUserQuestion":  # soru düz metin olarak panoya gelsin
        cevap = {"behavior": "deny", "message": _t("Bu oturumda AskUserQuestion yok: soruyu düz metin olarak yaz ve turu bitir; kullanıcı panodan cevaplar.",
                                                   "AskUserQuestion isn't available in this session: write the question as plain text and end the turn; the user answers from the panel.")}
    else:
        # 5 Kasım: aynı araç paralel çağrılırsa (ayrı iş parçacıkları) ikisi de soruyordu — anahtar başına kilit; ikinci çağrı kilidi alınca verilmiş izni görür
        with TOPO["kilit_sozluk"].setdefault(anh, threading.Lock()):
            if anh in hat: cevap = {"behavior": "allow", "updatedInput": gi}; print(f"TOPLANTI OTURUMU: izin {ad} → aynı anda sorulan izin onaylandı, yeniden sorulmadı")
            else: cevap = _topo_izin_sor(ad, gi, anh, hat)
    _topo_gonder({"type": "control_response", "response": {"subtype": "success", "request_id": o.get("request_id"), "response": cevap}})
def _topo_izin_sor(ad, gi, anh, hat):
    if True:
        ozet = _topo_arac_ozet(ad, gi); TOPO["izin"] += 1; TOPO["izin_toplam"] += 1
        _topo_mesaj("izin", arac_cumlesi(ad, gi))  # v0.112.2: düz cümle, komut yalnız eylem ayrıntısında ve izin-kayit.jsonl'de
        iid = izin_iste("arac", izin_metni(ad, gi), {"arac": ad, "ozet": ozet}, oturum=True)  # v0.115.0: kart değil, Claude bölümünde Onayla / Reddet
        k = izin_bekle(iid) if iid else "zaman_asimi"; TOPO["izin"] = max(0, TOPO["izin"] - 1)
        _topo_mesaj("sistem", {"onaylandi": _t("İzin verdin.", "You allowed it."), "reddedildi": _t("İzni reddettin.", "You declined.")}.get(k, _t("İzin süresi doldu; bu adım atlandı.", "The permission timed out; Claude skipped this step.")))
        cevap = ({"behavior": "allow", "updatedInput": gi} if k == "onaylandi" else
                 {"behavior": "deny", "message": _t(f"{AYAR.get('ad') or 'Kullanıcı'} reddetti (Suflor); bu adımı atla, gerekirse ona sor." if k == "reddedildi" else
                                                     "Kullanıcı onay vermedi (süre doldu); bu adımı atla, gerekirse ona sor.",
                                                     "The user declined (Suflor); skip this step and ask them if needed." if k == "reddedildi" else
                                                     "No approval from the user (timed out); skip this step and ask them if needed.")})
        if k == "onaylandi": hat.add(anh)  # oturum boyunca hatırla (yeniden soru yok)
        print(f"TOPLANTI OTURUMU: izin {ad} → {k}")
    return cevap
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
                if topo_chrome_acik():  # kişi araştırma zinciri: Chrome bağlantısı (tek satır; yoksa web'e düşülür, Chrome'u açmayız)
                    cd = next((m.get("status") for m in (j.get("mcp_servers") or []) if isinstance(m, dict) and m.get("name") == "claude-in-chrome"), None)
                    print("KİŞİ ARAŞTIRMA: chrome " + ("bağlı" if cd == "connected" else "yok → web (ya da kişi bağlayıcısı)"))
                if TOPO["durum"] == "bekliyor": _topo_durum("calisiyor")
            elif t == "assistant":
                if TOPO["durum"] == "bekliyor": _topo_durum("calisiyor")  # kullanıcı yazmadan yeni tur (arka plan işi bitti bildirimi vb.)
                for b in ((j.get("message") or {}).get("content") or []):
                    if not isinstance(b, dict): continue
                    if b.get("type") == "text": _topo_mesaj("claude", b.get("text")); TOPO["etkinlik"] = None
                    elif b.get("type") == "tool_use":
                        _topo_mesaj("arac", (str(b.get("name") or "?") + " — " + _topo_arac_ozet(b.get("name"), b.get("input"))).strip(" —")); _topo_etkinlik(b.get("name"), b.get("input"))
                        kk = _topo_kisi_kaynak(b.get("name"))
                        if kk and b.get("id"): TOPO.setdefault("kisi_t", {})[str(b["id"])] = (kk, time.time())
                        bk = bilgi_kaynagi_arac(b.get("name"))
                        if bk and b.get("id"): TOPO.setdefault("bilgi_t", {})[str(b["id"])] = (bk["kaynak"]["sunucu"], bk["arac"], time.time())
            elif t == "user":
                c = (j.get("message") or {}).get("content")
                for x in (c if isinstance(c, list) else []):  # bilgi kaynağı süresi: günlüğe yalnız sunucu, araç, süre (içerik yok)
                    s = TOPO.get("bilgi_t", {}).pop(str(x.get("tool_use_id")), None) if isinstance(x, dict) and x.get("type") == "tool_result" else None
                    ks_ = TOPO.get("kisi_t", {}).pop(str(x.get("tool_use_id")), None) if isinstance(x, dict) and x.get("type") == "tool_result" else None
                    if ks_: print(f"KİŞİ ARAŞTIRMA: {ks_[0]} → {'hata (sonraki kaynağa geçilir: ' + ('web' if ks_[0] != 'web' else 'yok') + ')' if x.get('is_error') else 'tamam'} · {time.time() - ks_[1]:.1f} sn")
                    if s: print(f"BİLGİ KAYNAĞI: {s[0]} · {s[1]} · {time.time() - s[2]:.1f} sn{' · hata' if x.get('is_error') else ''}")
                if isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c): TOPO["etkinlik"] = None  # araç bitti: sıradaki adıma kadar "düşünüyor"
            elif t == "result":
                try: TOPO["maliyet"] = round(TOPO["maliyet"] + float(j.get("total_cost_usd") or 0), 4)
                except (TypeError, ValueError): pass
                if TOPO["durum"] == "calisiyor": _topo_durum("bekliyor")
                TOPO["etkinlik"] = None
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
    e = TOPO["etkinlik"] if d == "calisiyor" else None
    return {"durum": d, "n": TOPO["n"], "t0": TOPO["t0"], "izin": TOPO["izin"], "konu": TOPO["konu"], "hata": TOPO["hata"] if TOPO["durum"] == "hata" else None,
            "terminal": bool(TOPO["sid"] and TOPO["acilis"]), "son": (son or {}).get("metin", "")[:300], "son_i": (son or {}).get("i"), "soru": soru,
            "etkinlik": {"metin": e["metin"], "sn": round(time.time() - e["t"])} if e else None, "sn": round(time.time() - TOPO["t_durum"]),
            "izinler": izin_bekleyen_oturum() if topo_canli() else []}
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
