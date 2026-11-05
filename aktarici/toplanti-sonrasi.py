# Suflor.me aktarıcı bölümü: Toplantı sonrası proaktif hatırlatma (5 Kasım, "sürekli assist eden proaktif kişisel asistan").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("toplanti-sonrasi")): AYAR, STATE, SON, BASE, bildirim, konus_yazili … relay.py'nin. import etme.
# Özet hazır olduktan ayar toplanti_sonrasi_hatirlat_dk (varsayılan 10; 0 kapalı) dakika sonra, toplantının yapı dosyasından (.yapi.json) açık uçlar sayılır:
# tarihsiz iş, sahipsiz iş, teyit bekleyen karar, cevapsız açık soru. Biri > 0 ise: menü bildirimi + panoda Bugün'ün başında tek cümle ve "Bakalım" düğmesi
# (asistana yazılı soru gider); sesli söyleme yalnız ayar toplanti_sonrasi_sesli: true ve toplantıda/Konuş'ta değilken. Bir toplantı için bir kez.
# Atlanır: gizli toplantı, deneme (Deneme toplantısı kipi, "deneme" adı, yapıda "deneme": true), yeni toplantı başlamış, kullanıcı o arada panoda Kararlar ve işler'i açmış
# (POST /proaktif gordu) ya da asistana sormuş. Gizli toplantının özeti zaten gelmez; yine de tetik anında gizli kip denetlenir.
PRO_SORU = "Son toplantının açık uçlarını sırayla sor: tarihsiz işler, sahipsiz işler, teyit bekleyen kararlar"
PRO_DOSYA = "proaktif.json"
PROAKTIF = {"bekleyen": None, "yapildi": set(), "gordu_t": 0.0, "zamanlayici": {}}

def _pro_oku():
    try:
        with open(os.path.join(BASE, PRO_DOSYA), encoding="utf-8") as f: PROAKTIF["yapildi"] = set(str(x) for x in (json.load(f).get("yapildi") or []))
    except (OSError, ValueError, AttributeError): pass
def _pro_yaz():
    try:
        with open(os.path.join(BASE, PRO_DOSYA) + ".tmp", "w", encoding="utf-8") as f: json.dump({"yapildi": sorted(PROAKTIF["yapildi"])[-200:]}, f)
        os.replace(os.path.join(BASE, PRO_DOSYA) + ".tmp", os.path.join(BASE, PRO_DOSYA))
    except OSError: pass

def _pro_k(r): return str(r.get("dosya") or r.get("ozet") or r["id"])  # bir toplantı için bir kez: aynı özet yeniden kaydedilse de

def pro_dk():
    try: return float(AYAR.get("toplanti_sonrasi_hatirlat_dk", 10))
    except (TypeError, ValueError): return 10.0

def pro_say(yol):  # yapı dosyası → {"tarihsiz", "sahipsiz", "teyit", "acik"} (yalnız > 0 olanlar anlamlı) ya da None
    try:
        with open(yol, encoding="utf-8") as f: v = json.load(f)
    except (OSError, ValueError): return None
    if not isinstance(v, dict) or not isinstance(v.get("maddeler"), list): return None
    c = {"tarihsiz": 0, "sahipsiz": 0, "teyit": 0, "acik": 0}
    k = lambda x: str(x or "").replace("İ", "i").replace("I", "ı").lower().replace("ö", "o").replace("ü", "u")
    for m in v["maddeler"]:
        for o in (m.get("ogeler") or []) if isinstance(m, dict) else []:
            if not isinstance(o, dict) or not str(o.get("metin") or "").strip(): continue
            t = o.get("tur")
            if t == "is":
                if not str(o.get("tarih") or "").strip(): c["tarihsiz"] += 1
                if not str(o.get("sahip") or "").strip(): c["sahipsiz"] += 1
            elif t == "karar" and (k(o.get("netlik")) in ("ortuk", "tek") or str(o.get("varsayim") or "").strip()): c["teyit"] += 1
            elif t == "soru" and not str(o.get("cevap") or "").strip(): c["acik"] += 1
    c["deneme"] = bool(v.get("deneme"))
    return c

def pro_cumle(baslik, c):
    p = []
    if c["tarihsiz"]: p.append(_t(f"{c['tarihsiz']} işin tarihi yok", f"{c['tarihsiz']} action items have no due date"))
    if c["sahipsiz"]: p.append(_t(f"{c['sahipsiz']} işin sahibi yok", f"{c['sahipsiz']} action items have no owner"))
    if c["teyit"]: p.append(_t(f"{c['teyit']} karar teyit bekliyor", f"{c['teyit']} decisions await confirmation"))
    if c["acik"]: p.append(_t(f"{c['acik']} açık soru var", f"{c['acik']} open questions"))
    return f"{baslik}: " + ", ".join(p) + _t(". Bakalım mı?", ". Shall we look?")

def _pro_deneme(r, c):
    ad = (str(r.get("baslik") or "") + " " + str(r.get("dosya") or "")).lower()
    if c.get("deneme") or "deneme" in ad or "duman" in ad: return True
    d = globals().get("DUMAN") or {}
    t = float(r.get("t") or 0)
    return bool(d.get("t0") and d["t0"] - 60 <= t <= (d.get("t_bit") or time.time()) + 900)

def pro_planla(r, bekle_sn=None):  # son_ekle'den: özet kaydı r (SON kaydı); yeniden başlayınca kalan süreyle
    try:
        dk = pro_dk()
        if dk <= 0 or not r.get("yapi") or _pro_k(r) in PROAKTIF["yapildi"] or _pro_k(r) in PROAKTIF["zamanlayici"]: return
        sayac0 = _KS.get("sayac", 0) if "_KS" in globals() else 0
        z = threading.Timer(dk * 60 if bekle_sn is None else max(1.0, bekle_sn), pro_tetik, args=(r, sayac0)); z.daemon = True; PROAKTIF["zamanlayici"][_pro_k(r)] = z; z.start()
        print(f"PROAKTİF: {dk:g} dk sonra açık uçlara bakılacak ({r.get('baslik') or r.get('dosya')})")
    except Exception as e: print(f"PROAKTİF: planlanamadı ({e.__class__.__name__})")

def pro_tetik(r, sayac0=0):
    PROAKTIF["zamanlayici"].pop(_pro_k(r), None)
    try:
        if _pro_k(r) in PROAKTIF["yapildi"] or pro_dk() <= 0: return
        def atla(neden): print(f"PROAKTİF: atlandı — {neden}"); PROAKTIF["yapildi"].add(_pro_k(r)); _pro_yaz()
        if gizli_acik(): return atla("gizli toplantı")
        c = pro_say(r["yapi"])
        if not c: return atla("yapı dosyası okunamadı")
        if _pro_deneme(r, c): return atla("deneme toplantısı")
        if aktif_dosya() or toplanti_var(): return atla("yeni toplantı başlamış")
        if PROAKTIF["gordu_t"] > float(r.get("t") or 0): return atla("kullanıcı Kararlar ve işler'e baktı")
        if "_KS" in globals() and _KS.get("sayac", 0) != sayac0: return atla("kullanıcı asistana sordu")
        if not (c["tarihsiz"] or c["sahipsiz"] or c["teyit"] or c["acik"]): return atla("açık uç yok")
        cumle = pro_cumle(r.get("baslik") or r.get("dosya") or _t("Son toplantı", "Last meeting"), c)
        PROAKTIF["yapildi"].add(_pro_k(r)); _pro_yaz()
        PROAKTIF["bekleyen"] = {"id": r["id"], "cumle": cumle, "t": time.time()}
        print(f"PROAKTİF: {cumle}")
        bildirim("Suflor.me", _t("Açık uçlar", "Open items"), cumle, son=r["id"])
        if AYAR.get("toplanti_sonrasi_sesli") is True and not SOHBET["acik"] and not (_KS.get("tur") if "_KS" in globals() else None) and not gizli_acik(): seslendir(cumle, kuyruk=True)
    except Exception as e: print(f"PROAKTİF: hata ({e.__class__.__name__}: {e})")

def pro_view():  # /status "proaktif": panoda Bugün'ün başındaki cümle; yeni toplantı başlayınca ya da elle kapatılınca kalkar
    b = PROAKTIF["bekleyen"]
    if not b: return None
    if aktif_dosya() or gizli_acik(): return None
    return {"id": b["id"], "cumle": b["cumle"]}

def pro_islem(p):  # POST /proaktif (yalnız pano): sor (Bakalım) | kapat | gordu (Kararlar ve işler açıldı)
    i = p.get("islem")
    if i == "gordu": PROAKTIF["gordu_t"] = time.time(); return {"ok": True}
    b = PROAKTIF["bekleyen"]
    if i == "kapat":
        if b and b["id"] == p.get("id"): PROAKTIF["bekleyen"] = None
        return {"ok": True}
    if i == "sor":
        if not b or b["id"] != p.get("id"): return {"ok": False, "err": _t("hatırlatma yok", "no reminder")}
        if gizli_acik(): return gizli_red()
        r = konus_yazili(_t(PRO_SORU, "Ask me, one by one, about the open items of the last meeting: items without a due date, items without an owner, decisions awaiting confirmation"))
        if r.get("ok"): PROAKTIF["bekleyen"] = None; print("PROAKTİF: Bakalım — asistana soruldu")
        return r
    return {"ok": False, "err": "islem"}

def pro_yukle():  # aktarıcı açılışında (son_yukle'den sonra): son 3 saatin henüz işlenmemiş özetleri için kalan süreyle yeniden planla
    _pro_oku()
    for r in list(SON):
        try:
            if r.get("yapi") and _pro_k(r) not in PROAKTIF["yapildi"] and time.time() - float(r.get("t") or 0) < 3 * 3600: pro_planla(r, pro_dk() * 60 - (time.time() - float(r.get("t") or 0)))
        except Exception: pass
