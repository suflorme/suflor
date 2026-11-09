# Suflor.me aktarıcı bölümü: Planlı toplantı hatırlatması (9 Kasım) — asistan toplantıdan önce sesle haber verir, istenirse kısa hazırlık brifingi verir.
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("toplanti-hatirlat")): AYAR, STATE, TAKVIM_TAM, TAKVIM_GEC, BRIFING, BASE, bildirim, seslendir … relay.py'nin. import etme.
# Ne zaman: toplantıdan ayar toplanti_hatirlat_dk (10; 1..60) dk önce. Ardışık toplantıda (öncekinin bitişi ile bu toplantı arası < süre) önceki biter bitmez.
#   Bir toplantı için tek hatırlatma (toplanti-hatirlat.json, günlük; aktarıcı yeniden açılsa da tekrar etmez).
# Hangi toplantı: takvimde reddedilmemiş, tüm gün olmayan, başka katılımcılı ya da Teams/Meet/Zoom bağlantılı olanlar. Tek kişilik blok, gizli işaretli (başlıkta gizli/confidential/private/🔒) yok.
#   Rutin (aynı başlık + aynı katılımcılar son 4 haftada ≥ 3 kez geçmiş) → sesli değil, yalnız menü bildirimi.
# Susma: gizli kip → hiçbir şey; başka toplantı sürüyorsa, sessiz mod, asistan konuşuyor/sohbette, deneme toplantısı, ayar toplanti_hatirlat_sesli kapalı → yalnız menü bildirimi.
#   (Mac'in Rahatsız Etme/Odak durumu aktarıcıdan okunamıyor — launchd altında sistem dosyasına erişim yok; bu yüzden bakılmaz.)
# Cümle yerelde kurulur (Claude yok, maliyet 0): saat farkı + toplantı adı + katılımcıların kısa adı + o kişilerle açık iş sayısı + "Kısa bir hazırlık ister misin?".
# Brifing yalnız "evet"te: that_hazirlik() mevcut brifing_iste/brifing_sesli yolunu kullanır; hazır olana dek bekler, olmazsa yerel kısa özet okunur.
# Sesle yanıt: sesli turun içinden that_sesli_yakala(metin) çağrılır ("evet" → hazırlık, "toplantıyı aç" → bağlantı, "hayır/sonra" → kapat); pencere THAT_PENCERE_SN.
# Pano/menü: /status "toplanti_hatirlat" + POST /toplanti-hatirlat {islem: hazirlik | ac | kapat} (yalnız pano). Ayarlar: toplanti_hatirlat, toplanti_hatirlat_dk, toplanti_hatirlat_sesli.
THAT_DOSYA = "toplanti-hatirlat.json"
THAT = {"yapildi": {}, "bekleyen": None, "dongu": False, "kilit": threading.Lock()}
THAT_TARAMA_SN, THAT_PENCERE_SN, THAT_RUTIN_GUN, THAT_RUTIN_EN_AZ, THAT_BRIFING_BEKLE_SN = 30, 120, 28, 3, 120
THAT_GIZLI_RX = re.compile(r"(?i)\b(gizli|confidential|private)\b|🔒")
THAT_EVET_RX = re.compile(r"^\W*(?:evet|olur|tamam|anlat|isterim|ister(?:im)?|hadi|lütfen|buyur|dinliyorum|başla|söyle|e\s*evet|yes|sure|okay|ok)\b", re.I)
THAT_HAYIR_RX = re.compile(r"\b(?:hayır|yok|gerek\s+yok|istemiyorum|istemem|sonra|şimdi\s+değil|kalsın|boş\s+ver|no|not\s+now|later)\b", re.I)
THAT_AC_RX = re.compile(r"(?:toplantı(?:yı|ya)?\s+(?:aç|gir|katıl)|(?:bağlantı|link)(?:ı|i)?\s+aç|katıl(?:ayım|alım)?\b|open\s+the\s+meeting|join\s+the\s+meeting|\bjoin\b)", re.I)

def _that_oku():
    try:
        with open(os.path.join(BASE, THAT_DOSYA), encoding="utf-8") as f: v = json.load(f)
        THAT["yapildi"] = {str(k): dict(x) for k, x in (v.get("yapildi") or {}).items() if isinstance(x, dict) and time.time() - float(x.get("t") or 0) < 36 * 3600}
    except (OSError, ValueError, AttributeError, TypeError): pass
def _that_yaz():
    try:
        yol = os.path.join(BASE, THAT_DOSYA)
        with open(yol + ".tmp", "w", encoding="utf-8") as f: json.dump({"yapildi": THAT["yapildi"]}, f, ensure_ascii=False)
        os.replace(yol + ".tmp", yol)
    except OSError: pass

def _soz_sonuc_g(ref, sonuc):  # kullanıcı işlemini tek söz kapısına bildirir (soz-kapisi.py soz_sonuc); kapı yüklü değilse (yalıtılmış test) sessiz
    f = globals().get("soz_sonuc")
    if f:
        try: f(ref, sonuc)
        except Exception: pass
def that_acik(): return AYAR.get("toplanti_hatirlat") is not False
def that_sesli_acik(): return AYAR.get("toplanti_hatirlat_sesli") is not False and AYAR.get("konusma", True) is not False
def that_dk():
    try: x = float(AYAR.get("toplanti_hatirlat_dk", 10))
    except (TypeError, ValueError): x = 10.0
    return min(60.0, max(1.0, x))
def _that_anahtar(e): return str(e.get("id") or e.get("baslik") or "").split("@")[0] + "|" + str(e.get("baslangic") or "")

def _that_k(x):  # Türkçe küçük harf, sadeleşmiş karşılaştırma anahtarı
    return re.sub(r"\s+", " ", str(x or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")).strip()
def _that_kim(e):  # katılımcı kümesi (rutin eşlemesi): e-posta varsa o, yoksa ad
    ep = [str(x).lower() for x in (e.get("katilimci_eposta") or []) if "@" in str(x)]
    return frozenset(ep or [_that_k(x) for x in (e.get("katilimcilar") or [])])

def that_toplanti_mi(e):  # takvim etkinliği hatırlatılacak bir toplantı mı
    if e.get("tum_gun") or e.get("reddettin") or e.get("paylasilan"): return False
    if f'{e.get("takvim")} · {e.get("hesap")}' in (AYAR.get("takvim_haric") or []): return False
    if THAT_GIZLI_RX.search(str(e.get("baslik") or "")): return False
    diger = bool(e.get("katilimcilar")) or bool(e.get("katilimci_eposta")) or (e.get("duzenleyen") and e.get("ben_duzenleyen") is False)
    return bool(diger or e.get("baglanti"))

def _that_aday_liste():  # [(başlangıç, bitiş, olay)] başlangıca göre; gizli işaretliler bile ardışıklık hesabında "meşgul" sayılır
    out = []
    for e in TAKVIM_TAM.values():
        if e.get("tum_gun") or e.get("reddettin") or e.get("paylasilan"): continue
        if f'{e.get("takvim")} · {e.get("hesap")}' in (AYAR.get("takvim_haric") or []): continue
        try: b, s_ = _zaman(e["baslangic"]), _zaman(e["bitis"])
        except (KeyError, TypeError, ValueError): continue
        out.append((b, s_, e))
    out.sort(key=lambda x: x[0]); return out

def that_tetik_zamani(b, liste, dk):  # toplantı başlangıcı b → hatırlatma anı: b - dk; öncesinde biten bir toplantı bu aralığa taşıyorsa onun bitişi
    t = b - datetime.timedelta(minutes=dk)
    for b2, s2, _ in liste:
        if b2 < b and t < s2 <= b: t = s2
    return t

def that_rutin(e, simdi):  # aynı başlık + aynı katılımcılar son 28 günde ≥ 3 kez (bu toplantıdan önce bitmiş)
    ad, kim = _that_k(e.get("baslik")), _that_kim(e)
    if not ad: return False
    try: b = _zaman(e["baslangic"])
    except (KeyError, TypeError, ValueError): return False
    gor = set()
    for x in list(TAKVIM_TAM.values()) + list((globals().get("TAKVIM_GEC") or {}).get("olaylar") or []):
        if not isinstance(x, dict) or x.get("reddettin") or x.get("tum_gun") or _that_k(x.get("baslik")) != ad or _that_kim(x) != kim: continue
        try: b2, s2 = _zaman(x["baslangic"]), _zaman(x["bitis"])
        except (KeyError, TypeError, ValueError): continue
        if b2 >= b or s2 > simdi or simdi - s2 > datetime.timedelta(days=THAT_RUTIN_GUN): continue
        gor.add(b2.isoformat())
    return len(gor) >= THAT_RUTIN_EN_AZ

# --- cümle ---------------------------------------------------------------------------------------------------------------------------------------------
def _that_ilk_ad(x):
    s = " ".join(str(x or "").split())
    if "@" in s and " " not in s: s = re.sub(r"[._\-]+", " ", s.split("@", 1)[0]).title()
    if "," in s: s = s.split(",", 1)[1].strip() or s  # "Yılmaz, Ayşe" → Ayşe
    return (s.split(" ")[0] if s else "").strip(".,;:()")
def _that_unlu(s, son=True):
    u = [c for c in s if c in "aeıioöuüAEIİOÖUÜ"]
    return (u[-1] if son else u[0]).lower() if u else "e"
def that_ile(ad):  # "Ayşe" → "Ayşe'yle", "Can" → "Can'la" (ünlü uyumu; kesme işaretiyle)
    if not ad: return ""
    son = ad[-1]; unlu_biter = son in "aeıioöuüAEIİOÖUÜ"; kalin = _that_unlu(ad) in "aıou"
    return ad + "'" + (("y" if unlu_biter else "") + ("la" if kalin else "le"))
def that_kisiler(kat, sen=True):  # katılımcı adları → ("Ayşe'yle" | "Ayşe ve Can'la" | "Ayşe, Can ve Deniz'le" | "6 kişiyle", ad listesi)
    ad = []; gor = set()
    for k in kat:
        a = _that_ilk_ad(k)
        if a and _that_k(a) not in gor: gor.add(_that_k(a)); ad.append(a)
    if not ad: return "", []
    if len(ad) > 3: return f"{len(ad)} kişiyle", ad
    if len(ad) == 1: return that_ile(ad[0]), ad
    return ad[0] + (", " + ad[1] if len(ad) == 3 else "") + " ve " + that_ile(ad[-1]), ad
def _that_kucuk_bas(t):  # "Bütçe" → "bütçe"; "OKR" gibi kısaltma olduğu gibi kalır
    if len(t) > 1 and t[1].isupper(): return t
    return ({"İ": "i", "I": "ı"}.get(t[0]) or t[0].lower()) + t[1:]
def that_baslik(b, en=40):  # toplantı adı → "bütçe toplantın" için gövde (sonuna toplantı eklenir); "… toplantısı" ise tekrarlanmaz
    t = " ".join(str(b or "").split())
    t = re.sub(r"(?i)^(?:fwd?|re|güncellendi|updated|invitation)\s*:\s*", "", t).strip()
    gov = re.sub(r"(?i)\s*\b(toplantısı|toplantı|toplantisi|toplanti|meeting)\s*$", "", t).strip()
    if len(gov) > en: gov = gov[:en].rsplit(" ", 1)[0].rstrip(" ,;:-–") or gov[:en]
    return _that_kucuk_bas(gov) if gov else ""
def that_isler(e, kat):  # (sende, onlarda, yapi.gundem_taslagi) — yalnız okuma; kayıt grafı yoksa (0, 0, None)
    y = _yapi_mod() if "_yapi_mod" in globals() else None
    if not y or not kat: return 0, 0, None
    ad = str(AYAR.get("ad") or "")
    try: g = y.gundem_taslagi(BASE, kat, ad, str(e.get("baslik") or ""))
    except Exception as ex: print(f"HATIRLAT: iş sayısı okunamadı ({ex.__class__.__name__})"); return 0, 0, None
    sende = onlarda = 0
    for m in g.get("maddeler") or []:
        if m.get("tur") != "is": continue
        if ad and m.get("kim") and y.kisi_eslesir(m["kim"], ad): sende += 1
        else: onlarda += 1
    return sende, onlarda, g

def that_cumle(e, simdi, sen=True, sorulu=True):  # → cümle (str). Yerel; Claude'a gitmez
    try: b = _zaman(e["baslangic"])
    except (KeyError, TypeError, ValueError): b = simdi
    dk = round((b - simdi).total_seconds() / 60)
    kat = [str(x) for x in (e.get("katilimcilar") or []) if str(x).strip()]
    if not kat and e.get("duzenleyen") and e.get("ben_duzenleyen") is False: kat = [str(e["duzenleyen"])]
    kim, adlar = that_kisiler(kat)
    zaman = (f"{dk} dakika sonra" if dk >= 2 else "Birazdan") if ARAYUZ_DILI != "en" else (f"In {dk} minutes" if dk >= 2 else "Shortly")
    gov = that_baslik(e.get("baslik"))
    if ARAYUZ_DILI == "en":
        t = " ".join(str(e.get("baslik") or "").split())[:50]
        c = f"{zaman} you have {t or 'a meeting'}" + (f" with {', '.join(adlar[:3])}" if adlar and len(adlar) <= 3 else f" with {len(adlar)} people" if adlar else "") + "."
    else:
        yap = "toplantın var" if sen else "toplantınız var"
        c = f"{zaman} " + (kim + " " if kim else "") + (gov + " " if gov else "") + yap + "."
    sende, onlarda, _ = that_isler(e, kat)
    if sende or onlarda:
        if ARAYUZ_DILI == "en":
            c += " " + (f"You have {sende} and they have {onlarda} open items." if sende and onlarda else f"You have {sende} open items." if sende else f"They have {onlarda} open items.")
        else:
            o = "onda" if len(adlar) == 1 else "onlarda"; s_ = "sende" if sen else "sizde"
            c += " " + (f"{s_.capitalize()} {sende}, {o} {onlarda} açık iş var." if sende and onlarda else f"{s_.capitalize()} {sende} açık iş var." if sende else f"{o.capitalize()} {onlarda} açık iş var.")
    if sorulu:  # 9 Kasım (dost): soru dönüşümlü — ilk hatırlatmada eski cümle, sonra konuşma dilinde başka biçim (evet/hayır sorusu kalır)
        c += " " + _t((globals().get("cesit") or (lambda k_, l_: l_[0]))("that_soru_" + ("sen" if sen else "siz"), ["Kısa bir hazırlık ister misin?", "Hızlıca bir bakalım mı?", "Birlikte kısaca toparlayalım mı?"] if sen else
                                                                          ["Kısa bir hazırlık ister misiniz?", "Hızlıca bir bakalım mı?", "Birlikte kısaca toparlayalım mı?"]), "Want a quick prep?")
    return c

def _that_sen():  # kişiliğin hitap biçimi (kisilik.py: dosyada hitap_bicimi; kişilik yoksa sen — ürün kararı, 9 Kasım)
    try:
        k = kisilik() if "kisilik" in globals() else None
        return (k.get("bicim") == "sen") if k else True
    except Exception: return False

# --- tarama --------------------------------------------------------------------------------------------------------------------------------------------
def _that_deneme_aktif(simdi):
    d = globals().get("DUMAN") or {}
    return bool(d.get("aktif") or (d.get("t0") and simdi - float(d.get("t_bit") or d["t0"]) < 900))

def that_sesli_engel(simdi):  # → None (sesli söylenebilir) ya da neden
    if not that_sesli_acik(): return "sesli kapalı"
    if toplanti_var(): return "toplantı sürüyor"
    if toplanti_acik(): return "toplantı kaydı açık"
    if sessiz_acik(): return "sessiz mod"
    if _that_deneme_aktif(simdi): return "deneme toplantısı"
    if SOHBET["acik"] or ("_KS" in globals() and _KS.get("tur")): return "asistan meşgul"
    return None

def that_tara(simdi=None):  # → None (yapılacak yok) ya da {"neden"|"sonuc": …}; saniyede bir değil THAT_TARAMA_SN'de bir çağrılır, hata sessiz
    simdi = simdi or datetime.datetime.now().astimezone(); ts = simdi.timestamp()
    if not that_acik(): return {"neden": "kapalı"}
    if gizli_acik(): return {"neden": "gizli kip"}  # işaretlenmez: gizli kip toplantıdan önce kapanırsa hatırlatılır
    dk = that_dk(); liste = [x for x in _that_aday_liste() if that_toplanti_mi(x[2])]  # ardışıklık yalnız gerçek toplantılar arasında (öğle/odak bloğu saymaz)
    if THAT["bekleyen"] and ts > THAT["bekleyen"]["bit"] + 300: THAT["bekleyen"] = None
    for b, s_, e in liste:
        if b <= simdi: continue
        if (b - simdi).total_seconds() > dk * 60: break  # sonrakiler daha da uzak (sıralı); hatırlatma anı en erken b - dk
        k = _that_anahtar(e)
        if k in THAT["yapildi"]: continue
        if simdi < that_tetik_zamani(b, liste, dk): continue
        # toplantı kaydı kapanış işlemindeyse (öncekinin sonu) kısa bekle; başlangıca 2 dk kalana dek
        if toplanti_durum() in ("algilandi", "bitiyor") and (b - simdi).total_seconds() > 120: return {"neden": "önceki toplantı kapanıyor"}
        sen = _that_sen()
        cumle = that_cumle(e, simdi, sen, sorulu=True); kisa = that_cumle(e, simdi, sen, sorulu=False); sonuc = {}
        def teslim(e=e, b=b, k=k, cumle=cumle, kisa=kisa, sonuc=sonuc):  # tek söz kapısı (soz-kapisi.py) şimdi dediğinde ya da kapı yoksa hemen; sesli/yalnız bildirim kararı teslim anında
            ts_ = globals().get("soz_simdi", lambda x: x)(ts)
            rutin = that_rutin(e, simdi); engel = that_sesli_engel(ts_)
            sesli = engel is None and not rutin
            THAT["yapildi"][k] = {"t": ts_, "tur": "sesli" if sesli else "bildirim"}; _that_yaz()
            oid = next((i for i, x in TAKVIM_TAM.items() if x is e), str(e.get("id") or ""))
            THAT["bekleyen"] = {"id": "h" + str(int(ts_ * 1000)), "oid": oid, "cumle": cumle, "kisa": kisa, "t": ts_, "bit": b.timestamp(), "sesli": sesli, "baglanti": bool(e.get("baglanti")), "hazirlik": False}
            print(f"HATIRLAT: toplantı hatırlatması ({'sesli' if sesli else 'yalnız bildirim: ' + (engel or 'rutin toplantı')}, {round((b - simdi).total_seconds() / 60)} dk kala)")  # başlık/katılımcı günlüğe yazılmaz
            bildirim("Suflor.me", _t("Toplantı yaklaşıyor", "Meeting coming up"), kisa, aksiyon=["hazirlik"] + (["katil"] if e.get("baglanti") else []), hatirlat=THAT["bekleyen"]["id"])
            if sesli: seslendir(cumle, kuyruk=True)
            sonuc.update({"sonuc": "sesli" if sesli else "bildirim", "cumle": cumle})
        if "soz_aday" not in globals(): teslim(); return sonuc
        # öncelik 3 (acil): zamanı belli, kapı yalnız gizli kipte durdurur; sessiz mod/toplantı yalnız SESLİ okumayı keser (that_sesli_engel, bildirim yine gider — eski davranış)
        THAT["yapildi"].setdefault(k, {"t": ts, "tur": "kapida"}); _that_yaz()  # kapı kuyruğa alsa da yeniden aday çıkmasın
        kr = soz_aday("toplanti_hatirlat", kisa, anahtar="th:" + k, oncelik=3, kip="sor", teslim=teslim, gecerli_sn=max(120, int((b - simdi).total_seconds()) + 60), simdi=ts)
        if kr["karar"] != "simdi":
            if kr["neden"] == "gizli kip": THAT["yapildi"].pop(k, None); _that_yaz(); return {"neden": "gizli kip"}  # işaretlenmez: gizli kip toplantıdan önce kapanırsa hatırlatılır
            return {"neden": kr["neden"]}
        return sonuc
    return None

def _that_dongu():
    while True:
        time.sleep(THAT_TARAMA_SN)
        try: that_tara()
        except Exception as e: print(f"HATIRLAT: tarama hatası ({e.__class__.__name__}: {e})")
def that_baslat():  # aktarıcı açılışında (relay.py ana)
    _that_oku()
    if THAT["dongu"]: return
    THAT["dongu"] = True; threading.Thread(target=_that_dongu, daemon=True).start()

def that_view():  # /status "toplanti_hatirlat": panoda ve menüde "Hazırlık" / "Katıl" düğmeleri; toplantı başlayınca ya da gizli kipte kalkar
    b = THAT["bekleyen"]
    if not b or gizli_acik() or time.time() > b["bit"] + 300: return None
    return {"id": b["id"], "cumle": b["kisa"], "baglanti": b["baglanti"], "sesli": b["sesli"], "hazirlik": b["hazirlik"]}
def that_bekliyor():  # sesli turun "evet" penceresi: sesli söylenmiş hatırlatmadan sonra THAT_PENCERE_SN sn (toplantı başlayana dek)
    b = THAT["bekleyen"]
    return bool(b and b["sesli"] and not gizli_acik() and time.time() - b["t"] < THAT_PENCERE_SN and time.time() < b["bit"])

# --- evet / aç / kapat ---------------------------------------------------------------------------------------------------------------------------------
def that_yerel_ozet(e):  # brifing kurulamazsa: davet amacı + gündem taslağı + son görüşme — yerelde, ≤ 3 cümle
    y = _yapi_mod() if "_yapi_mod" in globals() else None; p = []
    kat = [str(x) for x in (e.get("katilimcilar") or []) if str(x).strip()]
    try:
        if y:
            mad = y.davet_maddeleri(e.get("notlar"), 2)
            if mad: p.append(_t("Davette şu var: ", "The invite says: ") + "; ".join(m.rstrip(".") for m in mad) + ".")
            _, _, g = that_isler(e, kat)
            ms = [m["satir"] for m in (g or {}).get("maddeler") or []][:3]
            if ms: p.append(_t("Açıkta kalanlar: ", "Still open: ") + "; ".join(ms) + ".")
    except Exception as ex: print(f"HATIRLAT: yerel özet kurulamadı ({ex.__class__.__name__})")
    try:
        gt = gecmis_toplantilar(kat, e.get("baslik"), 1) if "gecmis_toplantilar" in globals() else []
        if gt:
            r = next((x for x in SON if x.get("dosya") == gt[0][0]), None) or {}
            d = " ".join(str(r.get("degerlendirme") or "").split())[:200]
            if d: p.append(_t("Geçen sefer: ", "Last time: ") + d.rstrip(".") + ".")
    except Exception as ex: print(f"HATIRLAT: son görüşme okunamadı ({ex.__class__.__name__})")
    return " ".join(p) or _t("Bu toplantı için elimde özel bir not yok; rahat gir.", "There is nothing special on record for this meeting.")

def _that_brifing_bekle(oid, e, sesli):  # arka plan: brifing hazır olunca (en çok THAT_BRIFING_BEKLE_SN) oku; olmazsa yerel özet
    t0 = time.time()
    while time.time() - t0 < THAT_BRIFING_BEKLE_SN:
        d = (BRIFING.get(oid) or {}).get("durum")
        if d == "hazir":
            if sesli and not toplanti_var() and not gizli_acik(): brifing_sesli(oid, "dinle")
            return
        if d == "hata" or d is None: break
        time.sleep(0.5)
    if sesli and not toplanti_var() and not gizli_acik(): seslendir(that_yerel_ozet(e), kuyruk=True)

def that_hazirlik(sesli=None):  # "evet" ya da panodaki/menüdeki Hazırlık: brifingi ister (Claude yalnız burada çağrılır); sesli=None → ayara göre
    b = THAT["bekleyen"]
    if not b or time.time() > b["bit"] + 300: return {"ok": False, "err": _t("hatırlatma yok", "no reminder")}
    if gizli_acik(): return gizli_red()
    if toplanti_var(): return {"ok": False, "err": _t("Toplantı sürerken okunmaz", "Not read aloud during a meeting")}
    e = takvim_olay(b["oid"])
    if not e: return {"ok": False, "err": _t("Toplantı takvimde bulunamadı", "Meeting not found in the calendar")}
    sesli = that_sesli_acik() if sesli is None else bool(sesli)
    b["hazirlik"] = True; _soz_sonuc_g("kaynak:toplanti_hatirlat", "kabul")
    d = (BRIFING.get(b["oid"]) or {}).get("durum")
    if d == "hazir":
        if sesli: brifing_sesli(b["oid"], "dinle")
        return {"ok": True, "durum": "hazir", "ses": sesli}
    if sesli: seslendir(_t((globals().get("cesit") or (lambda k_, l_: l_[0]))("that_evet", ["Tamam, hazırlıyorum.", "Hemen toparlıyorum.", "Olur, birkaç saniye."]), "Okay, preparing it."), kuyruk=True)  # 9 Kasım (dost): dönüşümlü
    r = brifing_iste({"olay": b["oid"]}) if d != "calisiyor" else {"ok": True}
    if not r.get("ok"):  # başka brifing sürüyor / Claude yok: yerel özet hemen
        if sesli: seslendir(that_yerel_ozet(e), kuyruk=True)
        return {"ok": True, "durum": "yerel", "ses": sesli, "not": r.get("err")}
    threading.Thread(target=_that_brifing_bekle, args=(b["oid"], e, sesli), daemon=True).start()
    print("HATIRLAT: hazırlık istendi"); return {"ok": True, "durum": "calisiyor", "ses": sesli}

def that_ac():  # "toplantıyı aç": takvimdeki bağlantı tarayıcıda (chrome_ac; yalnız takvim olayının doğrulanmış bağlantısı); onay istemez, veri göndermez
    b = THAT["bekleyen"]
    if not b or time.time() > b["bit"] + 300: return {"ok": False, "err": _t("hatırlatma yok", "no reminder")}
    if gizli_acik(): return gizli_red()
    if not b["baglanti"]: return {"ok": False, "err": _t("Toplantıda bağlantı yok", "This meeting has no link")}
    return chrome_ac({"olay": b["oid"]})

def that_islem(p):  # POST /toplanti-hatirlat (yalnız pano ve menü bildirimi)
    i = p.get("islem"); b = THAT["bekleyen"]
    if i in ("hazirlik", "ac", "kapat") and p.get("id") and (not b or b["id"] != p.get("id")): return {"ok": False, "err": _t("hatırlatma yok", "no reminder")}
    if i == "hazirlik": return that_hazirlik(sesli=bool(p.get("sesli")) if "sesli" in p else False)  # düğme: yazılı brifing panoda; sesli yalnız istenirse
    if i == "ac": _soz_sonuc_g("kaynak:toplanti_hatirlat", "kabul"); return that_ac()
    if i == "kapat": THAT["bekleyen"] = None; _soz_sonuc_g("kaynak:toplanti_hatirlat", "ret"); return {"ok": True}
    if i == "tara": return {"ok": True, "sonuc": that_tara()}  # elle bir tarama (testler); kurallar aynen geçerli
    return {"ok": False, "err": "islem"}

def that_sesli_yakala(metin):  # sesli turun içinden: pencere açıksa "evet" / "toplantıyı aç" / "hayır" → işlem yapılır, "hazirlik" | "ac" | "kapat" döner; yoksa None (soru normal akar)
    if not that_bekliyor(): return None
    m = " ".join(str(metin or "").split())
    if not m or len(m) > 80: return None
    if THAT_AC_RX.search(m) and not THAT_HAYIR_RX.search(m): _soz_sonuc_g("kaynak:toplanti_hatirlat", "kabul"); that_ac(); return "ac"
    if THAT_HAYIR_RX.search(m): THAT["bekleyen"] = None; _soz_sonuc_g("kaynak:toplanti_hatirlat", "ret"); return "kapat"
    if THAT_EVET_RX.match(m) and len(m.split()) <= 5: that_hazirlik(sesli=True); return "hazirlik"  # kısa onay; uzun cümle ("evet, bir de şunu sor") normal soru olarak akar
    return None
