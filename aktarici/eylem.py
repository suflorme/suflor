# Suflor.me aktarıcı bölümü: Eylem kuyruğu (Faz 4). Ayrı modül değildir — relay.py bunu kendi ad alanında, eski yerinde çalıştırır (bolum("eylem")):
# STATE, LOCK, AYAR, write, _t … relay.py'nin; buradaki tanımlar da relay.py'ye aittir. import etme. Python 3.9 uyumlu.
# --- Eylem kuyruğu (Faz 4) --------------------------------------------------------------------------------------
# Toplantıda konuşulan iş (kayıt, takvim/e-posta taslağı, belge değişikliği, takip e-postası) kart göstermeden kuyruğa girer
# (toplanti-claude.py eylem ekle). Toplantı sonunda Claude listeyi sunar (eylem sun): panoda Onayla/Reddet + "Hepsini onayla", ya da
# kullanıcı sohbette onaylar (eylem onay). Karar yalnız anahtarlı istemciden; Claude yalnız onaylananı, ayrıntıda yazıldığı gibi
# uygular ve sonucu yazar (eylem sonuc). E-posta yalnız taslak, takvim bildirim gönderilmeden — kural metni TOPLANTI-KURALLARI §8.
EYLEM_TUR = {"kayit": "Kayıt", "takvim": "Takvim", "eposta": "E-posta", "belge": "Belge", "takip": "Takip e-postası", "mesaj": "Ekip mesajı", "diger": "Diğer"}
EYLEMLER = []; EYLEM_SAAT = 12  # bu kadar saatten eski eylem panoda görünmez
def _eylem_temiz(x, n): return " ".join(str(x or "").split())[:n]
def eylem_yukle():
    sinir = (datetime.datetime.now() - datetime.timedelta(hours=EYLEM_SAAT)).isoformat(); by = {}
    try:
        for raw in open(os.path.join(BASE, "eylemler.jsonl"), encoding="utf-8"):
            try: x = json.loads(raw)
            except ValueError: continue
            if "tur" in x:
                if str(x.get("at", "")) >= sinir: EYLEMLER.append(x); by[x["id"]] = x
            elif x.get("id") in by: by[x["id"]].update({k: v for k, v in x.items() if k not in ("id", "at")})
    except FileNotFoundError: pass
def eylem_ekle(p):
    tur = p.get("tur") if p.get("tur") in EYLEM_TUR else None; baslik = _eylem_temiz(p.get("baslik"), 160)
    if not tur or not baslik: return None
    ayr = str(p.get("ayrinti") or "").strip()[:4000]; now = datetime.datetime.now()
    x = {"id": "e" + str(int(time.time() * 1000)) + secrets.token_hex(2), "at": now.isoformat(timespec="seconds"), "file": aktif_dosya(),
         "tur": tur, "baslik": baslik, "ayrinti": ayr, "kim": _eylem_temiz(p.get("kim"), 60) or None, "durum": "bekliyor", "sunuldu": False}
    with LOCK:
        EYLEMLER.append(x); _log("eylemler.jsonl", x)
        if x["file"]: _md(f"| {now.strftime('%H:%M:%S')} | **EYLEM** | kuyruğa ({EYLEM_TUR[tur]}): {baslik.replace('|', '¦')} | |")  # toplantı bittiyse dökümde yer yok
    return x
def _eylem_yama(x, **k):  # LOCK içinde
    x.update(k); _log("eylemler.jsonl", dict({"id": x["id"], "at": datetime.datetime.now().isoformat(timespec="seconds")}, **k))
def eylem_sun():
    with LOCK:
        xs = [x for x in eylem_gorunen() if x["durum"] == "bekliyor" and not x.get("sunuldu")]
        for x in xs: _eylem_yama(x, sunuldu=True)
    soru_baslat([x["id"] for x in xs])  # sesli "yazayım mı?"
    return len(xs)
def eylem_karar(p, kaynak):
    d = p.get("durum") if p.get("durum") in ("onaylandi", "reddedildi") else None
    if not d: return 0
    ek = {"karar_t": round(time.time(), 3), "ses_metin": _eylem_temiz(p.get("ses_metin"), 200)} if kaynak == "ses" else {}  # Geri al süresi + ne duyuldu
    with LOCK:
        xs = [x for x in eylem_gorunen() if x["durum"] == "bekliyor" and (p.get("id") == "hepsi" and x.get("sunuldu") or x["id"] == p.get("id"))]
        for x in xs: _eylem_yama(x, durum=d, karar_at=datetime.datetime.now().isoformat(timespec="seconds"), yetkili=True, kaynak=kaynak, **ek)
    if xs: print(f"EYLEM: {len(xs)} iş {'onaylandı' if d == 'onaylandi' else 'reddedildi'} ({kaynak})" + (f" · duyulan \"{ek['ses_metin']}\"" if ek else ""))
    if kaynak != "ses" and xs: ses_durdur()  # sesli kararda geri okuma ("Takvim onaylandı.") kuyrukta, kesilmez
    if xs and p.get("id") == "hepsi": soru_bitir("hepsi")
    elif xs and SORU["aktif"] in {x["id"] for x in xs}: soru_sonraki()
    return len(xs)
def eylem_geri_al(p):  # sesli kararın 10 sn'lik Geri al'ı: iş bekliyor'a döner, soru yeniden okunur
    with LOCK:
        x = next((x for x in eylem_gorunen() if x["id"] == p.get("id")), None)
        if not x or x.get("kaynak") != "ses" or x["durum"] not in ("onaylandi", "reddedildi") or time.time() - (x.get("karar_t") or 0) > GERI_AL_SN + 2: return False
        _eylem_yama(x, durum="bekliyor", geri_alindi=True, kaynak=None, karar_at=None, karar_t=None)
        if SORU["aktif"] and SORU["aktif"] != x["id"]: SORU["liste"].insert(0, SORU["aktif"])
        SORU["liste"] = [x["id"]] + [i for i in SORU["liste"] if i != x["id"]]; SORU["aktif"] = None
    print(f"EYLEM: {x['id']} sesli karar geri alındı"); ses_durdur(); seslendir(_t("Geri aldım.", "Undone."), kuyruk=True); soru_sonraki()
    return True
def eylem_sonuc(p):
    d = p.get("durum") if p.get("durum") in ("yapildi", "hata") else None
    with LOCK:
        x = next((x for x in EYLEMLER if x["id"] == p.get("id")), None)
        if not x or not d or x["durum"] not in ("onaylandi", "yapildi", "hata"): return False
        _eylem_yama(x, durum=d, sonuc=_eylem_temiz(p.get("sonuc"), 300))
    return True
def eylem_gorunen():
    sinir = (datetime.datetime.now() - datetime.timedelta(hours=EYLEM_SAAT)).isoformat()
    return [x for x in EYLEMLER if x["at"] >= sinir]
GERI_AL_SN = 10  # sesli karar bu kadar sn geri alınabilir; toplantı oturumu (eylem bekle) kararı ancak sonra alır
def _geri_al_sn(x):
    if x.get("kaynak") != "ses" or x["durum"] not in ("onaylandi", "reddedildi"): return 0
    return max(0, round(GERI_AL_SN - (time.time() - (x.get("karar_t") or 0)), 1))
def eylem_view():
    xs = eylem_gorunen(); soru_zaman()
    return {"liste": [dict({k: x.get(k) for k in ("id", "at", "tur", "baslik", "ayrinti", "kim", "durum", "sunuldu", "sonuc", "kaynak", "ses_metin")}, geri_al_sn=_geri_al_sn(x)) for x in xs],
            "bekleyen": sum(1 for x in xs if x["durum"] == "bekliyor"), "sesli": SORU["aktif"]} if xs else None
def cards_view():
    ertele_kontrol()
    # (kullanıcı) pano yeniden açılınca önceki toplantının kartları görünmez — yalnız süren toplantının (aktif dosya)
    # ve henüz dosyası belli olmayan (PRE'de bekleyen) kartlar
    # dosyası belli olmayan kayıt (toplantı dışında sorulan soru, PRE kartı) yalnız 30 dk görünür — yoksa eski bir
    # "test" sorusu panoda ve şeritte süresiz "1 soru bekliyor" diye kalıyordu
    af = aktif_dosya(); yeni = lambda r: (datetime.datetime.now() - datetime.datetime.fromisoformat(r.get("at") or "2000-01-01T00:00:00")).total_seconds() < 1800
    bu = lambda r: r.get("file") == af if r.get("file") is not None else yeni(r)
    cs = [c for c in CARDS if bu(c)]; qs_ = [q for q in QUESTIONS if bu(q)]
    answered = {c.get("reply_to") for c in CARDS if c.get("reply_to")}
    kartlar = [c if c.get("kind") in CARD_KINDS else dict(c, kind=kart_turu(c.get("kind")), **({"gizli": True} if c.get("kind") == "deginme" else {}))
               for c in cs if c.get("kind") != "duygu"]
    open_ = sorted((c for c in kartlar if c.get("status") == "acik" and not c.get("ertele") and not tutulan(c)), key=lambda c: c.get("geri") or c.get("at") or "")
    ertelenen = sum(1 for c in kartlar if c.get("status") == "acik" and c.get("ertele"))
    closed = sorted((c for c in kartlar if c.get("status") not in ("acik", "ozetlendi")), key=lambda c: c.get("acted_at") or "")[-5:]
    tone = next(({"ton": c["ton"], "at": c["at"]} for c in reversed(cs) if c.get("kind") == "duygu" and not c.get("kim")), None)
    tone_kisi = {}  # kişi başına son duygu etiketi (kullanıcı, 2 Ekim)
    for c in cs:
        if c.get("kind") == "duygu" and c.get("kim"): tone_kisi[c["kim"]] = {"ton": c["ton"], "at": c["at"]}
    ki = STATE["kanit_iste"]; ki = ki if ki and time.time() - ki["t"] < 20 else None
    return {"uyari": disk_warning(), "tone": tone, "tone_kisi": tone_kisi, "cards": open_, "closed": closed, "questions": [q for q in qs_ if q["id"] not in answered][-5:],
            "sure": sure_view(), "pay": pay_view(af) if af else None, "acik": acik_view() if gundem_gorunur() else [], "dil": dil_view(),
            "kanit_iste": {"id": ki["id"], "not": ki.get("not", ""), "kaynak": ki.get("kaynak", "pano")} if ki else None, "kanit_n": len(STATE["kanitlar"].get(af, [])) if af else 0,
            "whisper": whisper_view(), "komut": STATE.get("komut"), "sessiz": sessiz_view(), "ertelenen": ertelenen, "eylem": eylem_view(),
            "baglam": baglam_view(), "yaparken": yaparken_view(),
            "son": {k: v for k, v in (STATE.get("son_satir") or {}).items() if k != "file"} if (STATE.get("son_satir") or {}).get("file") == af and af else None}
# şerit uzun yoklaması — GET /cards?bekle=25&imza=<son> şeridin gösterdiği durum değişene kadar (en çok 25 sn)
# bekler, değişince hemen döner. Her POST (kart, ✓/✕, soru, kanıt isteği, komut, satır) bekleyenleri uyandırır; POST dışı değişiklik
# (süre, Whisper satırı) en geç 1 sn'de yakalanır. Ölçüm (headless, 12 kart): kart → şerit ortanca 2,1 sn → bkz. BRIEF.
KART_KOSUL = threading.Condition()
def kart_bildir():
    with KART_KOSUL: KART_KOSUL.notify_all()
def serit_imza(v):
    import hashlib
    sv = v.get("sure") or {}
    ss = v.get("sessiz") or {}
    x = [[(c.get("id"), c.get("status"), c.get("geri")) for c in v["cards"]], [q.get("id") for q in v["questions"]], v.get("uyari"), v.get("dil"), (sv.get("kalan_dk"), sv.get("kayma")),
         (ss.get("acik"), (ss.get("kalan_sn") or 0) // 60, len(ss.get("tutulan") or [])), v.get("ertelenen"),
         [(x["id"], x["durum"], x.get("sunuldu")) for x in ((v.get("eylem") or {}).get("liste") or [])],
         (v.get("kanit_iste") or {}).get("id"), v.get("kanit_n"), bool(v.get("yaparken")), (v.get("komut") or {}).get("id"), str((v.get("son") or {}).get("at") or "")[:18]]  # son satır 10 sn adımla
    return hashlib.sha1(json.dumps(x, default=str, sort_keys=True).encode()).hexdigest()[:16]
def cards_bekle(imza, sn):
    son = time.time() + max(0, min(sn, 25))
    while True:
        v = cards_view(); v["imza"] = serit_imza(v)
        kalan = son - time.time()
        if v["imza"] != imza or kalan <= 0: return v
        with KART_KOSUL: KART_KOSUL.wait(min(1.0, kalan))
def add_card(p):
    ham = p.get("kind"); kind = kart_turu(ham)
    text = " ".join(str(p.get("text") or "").split())[:400]
    if not text: return None
    now = datetime.datetime.now()
    c = {"id": "k" + str(int(time.time() * 1000)) + secrets.token_hex(2), "at": now.isoformat(timespec="seconds"), "file": None,
         "kind": kind, "text": text, "why": " ".join(str(p.get("why") or "").split())[:300], "status": "acik"}
    if kind == "dur" and (p.get("gizli") or ham == "deginme"): c["gizli"] = True
    if p.get("onay"): c["onay"] = True  # onay kartı (#76): Onayla / Reddet — yalnız anahtarlı istemciden
    if p.get("reply_to"):
        c["reply_to"] = str(p["reply_to"])[:40]
        q = next((q for q in QUESTIONS if q["id"] == c["reply_to"]), None)
        if q: c["q"] = q["text"][:200]  # cevap kartında hangi soruya cevap olduğu görünsün
        if q and q.get("tur") == "ozet": c["replik"] = True; c.pop("q", None)  # "Ne diyeyim?" kartı: başlık "Ne diyeyim", soru satırı yok
    if isinstance(p.get("agenda_i"), int): c["agenda_i"] = p["agenda_i"]
    if p.get("durum"): c["durum"] = " ".join(str(p["durum"]).split())[:160]  # kartın altındaki tek satır (Ne diyeyim?: şu an ne konuşuluyor)
    if p.get("sessiz_ozet") and SESSIZ["id"]: c["sessiz_ozet"] = SESSIZ["id"]  # sessizin özeti: bekleyenleri kapatır, kendisi beklemez
    elif sessiz_acik() and kind != "dur" and not c.get("reply_to"): c["sessiz"] = SESSIZ["id"]
    with LOCK:
        c["file"] = aktif_dosya(); CARDS.append(c); _log("kartlar.jsonl", c)
        _md(f"| {now.strftime('%H:%M:%S')} | **CLAUDE · {'NE DİYEYİM' if c.get('replik') else CARD_KINDS[kind]}** | {c['text'].replace('|', '¦')}{(' — ' + c['durum'].replace('|', '¦')) if c.get('durum') else ''} |{' 🔇 bekliyor ' if c.get('sessiz') else ' '}|", c, "kartlar.jsonl")
        if c.get("sessiz_ozet"):
            for x in CARDS:
                if x.get("sessiz") == c["sessiz_ozet"] and x.get("status") == "acik":
                    x["status"] = "ozetlendi"; x["acted_at"] = c["at"]; _log("kartlar.jsonl", {"id": x["id"], "at": c["at"], "status": "ozetlendi"})
    return c
def etiket(p):  # duygu etiketi: genel (kim yok) ya da kişi başına; aynı kişinin önceki etiketinin yerine geçer
    ton = p.get("ton") if p.get("ton") in TONES else None
    if not ton: return None
    now = datetime.datetime.now()
    c = {"id": "e" + str(int(time.time() * 1000)) + secrets.token_hex(2), "at": now.isoformat(timespec="seconds"), "file": None,
         "kind": "duygu", "ton": ton, "text": "", "status": "etiket"}
    if p.get("kim"): c["kim"] = " ".join(str(p["kim"]).split())[:60]
    with LOCK:
        c["file"] = aktif_dosya(); CARDS.append(c); _log("kartlar.jsonl", c)
        _md(f"| {now.strftime('%H:%M:%S')} | **DUYGU** | {(c['kim'] + ': ') if c.get('kim') else ''}{TONES[ton]} (tahmin) | |", c, "kartlar.jsonl")
    return c
ACK_MD = {"yapildi": "✓ yaptım", "okundu": "👁 okudum", "gecildi": "✕ gerek yok", "onaylandi": "✓ ONAYLANDI", "reddedildi": "✕ REDDEDİLDİ"}
def ack_card(p, yetkili=False):
    # üç ayrı anlam — yapildi (✓ yaptım), okundu (👁 okudum: kapat, reddetme), gecildi (✕ gerek yok: bir daha önerme).
    # Onay kartı yalnız onaylandi / reddedildi ile kapanır (karta dokunmak onay değildir) ve yalnız anahtarlı istemciden (#76);
    # kayıtta "yetkili" işareti izle'nin ONAY olayına dayanaktır.
    if p.get("status") == "ertele": return ertele_card(p)
    st = p.get("status") if p.get("status") in ACK_MD else None
    with LOCK:
        c = next((c for c in CARDS if c["id"] == p.get("id")), None)
        if not c or not st or c.get("status") != "acik" and c.get("onay"): return False
        if bool(c.get("onay")) != (st in ("onaylandi", "reddedildi")) or (c.get("onay") and not yetkili): return False
        now = datetime.datetime.now(); c["status"] = st; c["acted_at"] = now.isoformat(timespec="seconds")
        _log("kartlar.jsonl", dict({"id": c["id"], "at": c["acted_at"], "status": st}, **({"yetkili": True} if yetkili else {})))
        _md(f"| {now.strftime('%H:%M:%S')} | **KART {ACK_MD[st]}** | {c['text'].replace('|', '¦')} | |")
    return True
# (kullanıcı, 3 Ekim) not ve "Claude'a sor" tek kutu. Metin "?", "soru", "Claude" ya da iki boşlukla başlıyorsa soru,
# değilse not. "?" ve ayrı sözcük "soru" (ardından boşluk, ":" "," "." "-" ya da metin sonu) baştan atılır; "sorun …" not kalır.
# "Claude" ile başlayan olduğu gibi soru olur ("Claude: dinleyiciyim" talimatı Claude'a tanınır gelsin). Ayrım ham metinle (istemci kırpmaz).
GIRDI_SORU = re.compile(r"^(?:\?+|soru(?=[\s:,.\-]|$)[:,.\-]?)\s*", re.I)
def girdi_ayir(ham):
    ham = str(ham or "").replace("\r", "")
    if ham.startswith("  "): return "soru", ham.strip()
    t = ham.strip(); m = GIRDI_SORU.match(t)
    if m: return "soru", t[m.end():].strip() or t
    if re.match(r"^claude", t, re.I): return "soru", t
    return "not", t
def ask(p):
    # tur "ozet" = "Ne diyeyim?" (Option + Shift + O, panodaki düğme; eski "Son 1 dk"): izle son 2 dk'nın satırlarını, gündemi ve açık
    # soruları ekler, Claude tek cümlelik replik + tek satır durum kartı döner (kayıt adı "ozet" eski kayıtlarla uyumlu kalsın diye)
    ozet = p.get("tur") == "ozet"
    text = str(p.get("text") or "").strip()[:1000] or ("Ne diyeyim?" if ozet else "")
    if not text: return None
    now = datetime.datetime.now()
    with LOCK:
        if ozet:  # çift tıklama: cevaplanmamış, 60 sn'den yeni özet isteği varsa yenisi açılmaz
            answered = {c.get("reply_to") for c in CARDS if c.get("reply_to")}
            q = next((q for q in reversed(QUESTIONS) if q.get("tur") == "ozet" and q["id"] not in answered and (now - datetime.datetime.fromisoformat(q["at"])).total_seconds() < 60), None)
            if q: return q
        q = {"id": "q" + str(int(time.time() * 1000)) + secrets.token_hex(2), "at": now.isoformat(timespec="seconds"), "file": aktif_dosya(), "text": text}
        if ozet: q["tur"] = "ozet"
        QUESTIONS.append(q); _log("sorular.jsonl", q)
        _md(f"| {now.strftime('%H:%M:%S')} | **{'NE DİYEYİM? İSTENDİ' if ozet else 'CLAUDE’A SORU'}** | {' / '.join(text.replace('|', '¦').splitlines())} | |", q, "sorular.jsonl")
    return q
