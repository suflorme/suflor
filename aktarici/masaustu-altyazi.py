# Masaüstü Teams canlı altyazısı (13 Kasım, oturum "altyazi"): menü uygulaması (menu-cubugu.swift, MasaustuAltyazi) masaüstü toplantı sürerken
# Teams'in altyazı panelini Erişilebilirlik (AX) ağacından ~1 sn'de bir okur ve ham anlık görüntüyü POST /masaustu-altyazi ile buraya verir:
#   {"girdiler": [{"ax": <öğe numarası>, "m": [<girdinin doğrudan StaticText metinleri>]}, …]}  (ekrandaki sırayla)  ya da  {"durum": "yok"}
# Satır kimliği, büyüyen girdinin sabitlenmesi ve yineleme ayıklama burada (eklentideki content.js tick() + capId kuralının Python karşılığı; saf işlev
# ma_birlestir test/masaustu-altyazi.py ile sınanır). Sabitlenen satır ingest()'e "captions" kaynağıyla gider: ben/karşı ayrımı (ben_satiri: konuşmacı adı
# kullanıcının adıysa ben) ve Whisper akarken o tarafın altyazısının gölgeye gitmesi tarayıcı altyazısıyla aynı. Metin yalnız 127.0.0.1'de kalır.
# 13 Kasım gerçek izleri (iki kişi): girdi = Group .fui-ChatMessageCompact__body; ilk StaticText konuşmacı adı, son StaticText söz. Dış katılımcıda arada
# "Dış bilinmeyen" etiketi (Group; ad değil). Teams sistem satırları ("… dökümü başlattı", "Döküm başlatıldı. Alt yazılar …") tek StaticText → atılır.
# Aynı öğe her taramada yeniden okunur (izde aynı söz 3–4 kez): kimlik öğeye (ax) + metin başına bağlı; büyüyen girdi aynı kimlikle sabitlenene dek bekler.
# Ayar masaustu_altyazi (varsayılan açık): false iken uç "kapali" döner, menü uygulaması okumayı bırakır.
import re as _re_ma, time as _time_ma, secrets as _sec_ma
MA_SABIT_SN = 3.0  # eklentinin stableMs varsayılanı; son (hâlâ konuşulan) girdi 2 katı
MA_SISTEM_RX = _re_ma.compile(r"dökümü (başlattı|durdurdu)$|^döküm (başlatıldı|durduruldu|başlatılıyor)\b|(started|stopped) transcription$|^transcription (has )?(started|stopped)\b|"
                              r"kaydı (başlattı|durdurdu)$|(started|stopped) recording$", _re_ma.I)  # yedek: sistem satırı iki metinle gelirse
MA_ETIKET_RX = _re_ma.compile(r"^(dış|harici|external|misafir|konuk|guest)\b.*|.*\b(bilinmeyen|unknown|unverified|doğrulanmamış)$", _re_ma.I)  # ad değil, rozet
def ma_yeni(): return {"ses": _sec_ma.token_hex(3), "n": 0, "tok": {}, "son": [], "pending": {}, "sent": {}}
def ma_norm(t): return " ".join(_re_ma.sub(r"[^\w ]", "", str(t or "").lower(), flags=_re_ma.U).replace("_", " ").split())
def ma_ayikla(g):  # ham girdi → (konuşmacı, söz) ya da None (sistem satırı, boş)
    m = [" ".join(str(x).split()) for x in (g.get("m") or []) if isinstance(x, str)] if isinstance(g, dict) else []
    m = [x for x in m if x]
    if len(m) < 2: return None  # tek metin: Teams sistem satırı (döküm başladı vb.)
    kim, soz = m[0][:80], m[-1][:4000]
    if MA_SISTEM_RX.search(soz) or MA_ETIKET_RX.match(soz) and len(m) > 2: return None
    if MA_ETIKET_RX.match(kim): kim = "?"
    return kim, soz
def _ma_bas_tutar(a, b):  # capId kuralı: ilk 8 harf (noktalama yok sayılır) tutuyorsa aynı cümle
    k = min(8, len(a), len(b)); return k > 0 and a[:k] == b[:k]
def _ma_kimlik(d, ax, kim, n):
    t = d["tok"].get(ax) if ax is not None else None
    if t and _ma_bas_tutar(t["head"], n):
        if len(n) > len(t["head"]): t["head"] = n
        return t["id"]
    # öğe yeni (ya da Teams öğeyi yeniden kurdu): son girdilerden aynı konuşmacının, başı tutan cümlesi — aynı söz iki kimlik almasın
    for i in reversed(d["son"][-12:]):
        s = d["pending"].get(i) or {}
        if s.get("kim") == kim and _ma_bas_tutar(s.get("head", ""), n) and not any(v["id"] == i for k, v in d["tok"].items() if k != ax and k in d.get("_bu_tur", ())):
            if ax is not None: d["tok"][ax] = {"id": i, "head": max(n, s.get("head", ""), key=len)}
            return i
    d["n"] += 1; i = f"axcap-{d['ses']}/{d['n']}"
    if ax is not None: d["tok"][ax] = {"id": i, "head": n}
    d["son"].append(i); del d["son"][:-40]
    return i
def _ma_saat(t): return _time_ma.strftime("%H:%M:%S", _time_ma.localtime(t))
def _ma_iso(t): return _time_ma.strftime("%Y-%m-%dT%H:%M:%S", _time_ma.gmtime(t)) + ".%03dZ" % int((t % 1) * 1000)
def _ma_satir(d, i, v, simdi, need):
    e = {"id": i, "speaker": v["kim"], "text": v["text"], "time": _ma_saat(v["seen"]), "seen": _ma_iso(v["seen"]), "chg": _ma_iso(v["since"]), "stableMs": int(need * 1000)}
    if i in d["sent"]: e["revised"] = True
    d["sent"][i] = v["text"]; return e
def ma_birlestir(d, girdiler, simdi, sabit_sn=MA_SABIT_SN):
    """Saf işlev: ham anlık görüntü → (sabitlenen satırlar, taslaklar). d = ma_yeni() durumu (çağıran saklar)."""
    ok = []
    d["_bu_tur"] = {g.get("ax") for g in girdiler if isinstance(g, dict)}
    for g in girdiler:
        r = ma_ayikla(g)
        if not r: continue
        kim, soz = r; i = _ma_kimlik(d, g.get("ax"), kim, ma_norm(soz))
        if any(x[0] == i for x in ok): ok = [x for x in ok if x[0] != i]  # aynı kimlik iki kez (yeniden kurulan öğe): sondaki geçerli
        ok.append((i, kim, soz))
    fresh, taslak, gorulen = [], [], set()
    for idx, (i, kim, soz) in enumerate(ok):
        gorulen.add(i); son = idx == len(ok) - 1
        need = sabit_sn * (2 if son else 1)
        v = d["pending"].get(i)
        if not v or v["text"] != soz:
            d["pending"][i] = {"text": soz, "kim": kim, "since": simdi, "seen": v["seen"] if v else simdi, "head": ma_norm(soz)}
            if d["sent"].get(i) != soz and idx >= len(ok) - 3: taslak.append({"id": i, "speaker": kim, "text": soz})
            continue
        v["kim"] = kim
        if simdi - v["since"] < need:
            if d["sent"].get(i) != soz and idx >= len(ok) - 3: taslak.append({"id": i, "speaker": kim, "text": soz})
            continue
        if d["sent"].get(i) == soz: continue
        fresh.append(_ma_satir(d, i, v, simdi, need))
    # ekrandan düşen (panel kapandı, liste kaydı, altyazı kapandı) ve henüz sabitlenmemiş girdi kaybolmasın: son hâliyle gönderilir
    for i, v in list(d["pending"].items()):
        if i in gorulen: continue
        if d["sent"].get(i) != v["text"] and simdi - v["since"] < 120:
            e = _ma_satir(d, i, v, simdi, 0); e["flush"] = True; fresh.append(e)
        if simdi - v["since"] > 600: d["pending"].pop(i, None); d["sent"].pop(i, None)
    if len(d["tok"]) > 200:
        canli = set(d["pending"]); d["tok"] = {k: t for k, t in d["tok"].items() if t["id"] in canli}
    return fresh, taslak

# --- aktarıcı ucu ------------------------------------------------------------------------------------------------------------------------------------------
MA = ma_yeni(); MA.update(t=0.0, yazildi=False, uyari=None)
MA_KILIT = threading.Lock()
def masaustu_altyazi_acik(): return AYAR.get("masaustu_altyazi") is not False
def masaustu_altyazi_taze(sn=None):  # son SINYAL_SN'de masaüstü altyazı satırı/görüntüsü geldi (toplanti.py _alt_satir)
    return time.time() - MA.get("t", 0) < (sn or globals().get("SINYAL_SN", 30))
def masaustu_altyazi_al(p):
    if not masaustu_altyazi_acik(): return {"ok": True, "kapali": True}
    if gizli_acik(): return {"ok": True, "gizli": True}  # gizli toplantıda satır yazılmaz (ingest de atar; okuma burada durur)
    now = time.time()
    if p.get("durum") == "yok": masaustu_altyazi_yok(); return {"ok": True}
    g = p.get("girdiler")
    if not isinstance(g, list): return {"ok": False, "err": "girdiler"}
    with MA_KILIT:
        fresh, taslak = ma_birlestir(MA, [x for x in g[:60] if isinstance(x, dict)], now)
        bekleyen = sum(1 for i, v in MA["pending"].items() if MA["sent"].get(i) != v["text"])
    if g:
        MA["t"] = now
        if not MA["yazildi"]: MA["yazildi"] = True; print(f"MASAÜSTÜ ALTYAZI: Teams altyazısı okunuyor ({len(g)} girdi görünüyor)")
    m = {"title": STATE.get("meeting") or "Toplantı"}
    if fresh: ingest({"meeting": m, "source": "captions", "capturedAt": _ma_iso(now), "entries": fresh, "masaustu": True})
    if taslak: taslak_al({"meeting": m, "source": "captions", "entries": taslak})
    return {"ok": True, "bekleyen": bekleyen, "yeni": len(fresh)}
def masaustu_altyazi_yok():  # menü uygulaması toplantıda ~45 sn altyazı paneli bulamadı: günlüğe ve kullanıcıya toplantı başına bir kez
    a = TOPLANTI.get("aktif") or {}; k = a.get("id") or "-"
    if MA.get("uyari") == k or eklenti_cagri(): return
    MA["uyari"] = k
    print("MASAÜSTÜ ALTYAZI: altyazı bulunamadı — Teams'te altyazıyı aç (Diğer (…) → Dil ve konuşma → Canlı altyazıyı aç)")
    wh = "whisper_akiyor" in globals() and whisper_akiyor("karsi")
    bildirim("Suflor.me", _t("Altyazı kapalı", "Captions off"),
             _t("Konuşmacı adları için" if wh else "Döküm için", "For speaker names," if wh else "For the transcript,") + " "
             + _t("Teams'te altyazıyı aç: Diğer (…) → Dil ve konuşma → Canlı altyazıyı aç", "turn on captions in Teams: More (…) → Language and speech → Turn on live captions"))
