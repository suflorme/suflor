# Suflor.me aktarıcı bölümü: Anlık uyarılar (Faz 6 #7, #8). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("anlik")):
# STATE, LOCK, AYAR, sade, ben_adi, _t … relay.py'nin. import etme. Python 3.9 uyumlu.
# --- Anlık uyarı: Claude'u beklemeden, yalnız kullanıcıya (pano durum satırı, mini pano, şeritte kısa bildirim) ----------------
# 1) Adın geçti: karşı tarafın satırında kullanıcının ilk adı geçerse (ekli biçimler de: "Kerem'in", "Kereme") tek satır — kim, ne dedi.
#    Ek yalnız Türkçe hâl ekleri (kısa adda "Ali" → "alın" gibi sözcük yakalanmasın). Aynı satırın düzeltmeleri yeniden uyarmaz; aynı kişiden
#    30 sn içinde ikincisi görünen uyarının metnini günceller (yeni bildirim yok). Ayar adin_gecti: false kapatır.
# 2) Uzun konuşma: karşı taraf araya girmeden (≥ 4 sözcüklük karşı satır yok) kullanıcı uzun_konusma_sn'den (90) uzun konuşursa bir kez
#    "1,5 dk'dır sen konuşuyorsun". Kısa onaylar ("evet", "hı hı") sözü kesmiş sayılmaz; kullanıcı 20 sn susarsa sayaç sıfırlanır. 0 kapatır.
# Uyarı ANLIK_SN (20) görünür; /cards ve /status "anlik" alanında. Toplantıdan bağımsız sayaç dosya başına (yeni toplantı = yeni sayaç).
ANLIK = {"son": None, "n": 0, "ad_id": set(), "ad_son": {}, "uzun": {}}
ANLIK_SN = 20
_AD_EK = r"(?:'?(?:nin|nun|in|un|ye|ya|yi|yu|e|a|i|u|den|dan|ten|tan|de|da|te|ta|le|la|cigim|cim|ciyim))?"
def anlik_ver(tur, metin, ayrinti=""):
    ANLIK["n"] += 1
    ANLIK["son"] = {"id": f"a{ANLIK['n']}", "tur": tur, "metin": metin, "ayrinti": ayrinti, "t": time.time()}
    print(f"ANLIK: {tur} · {metin}")
    try: kart_bildir()  # şerit/pano uzun yoklaması hemen dönsün
    except NameError: pass
def anlik_view():
    a = ANLIK["son"]
    return {k: a[k] for k in ("id", "tur", "metin", "ayrinti")} if a and time.time() - a["t"] < ANLIK_SN else None
def _ilk_ad():
    a = sade(str(ben_adi() or "")).split(" ")[0]
    return a if len(a) >= 3 else None
def anlik_satir(key, e, text, onceki):
    # ingest'in her yazılan satırı için (LOCK içinde); hata satır yazımını durdurmaz
    try: _anlik_satir(key, e, text, onceki)
    except Exception as x: print(f"ANLIK: hata {x.__class__.__name__}")
def _anlik_satir(key, e, text, onceki):
    kim = e.get("speaker") or "?"; ben = kim == ben_adi() or e.get("kanal") == "ben"
    now = time.time(); t = e.get("t0") if isinstance(e.get("t0"), (int, float)) and abs(now - e["t0"]) < 120 else now
    sz = len(str(text).split())
    # 2) uzun konuşma
    esik = AYAR.get("uzun_konusma_sn", 90)
    if esik:
        u = ANLIK["uzun"].setdefault(key, {"bas": None, "son": 0, "uyardi": False})
        if ben:
            if u["bas"] is None or t - u["son"] > 20: u.update(bas=t, uyardi=False)
            u["son"] = max(u["son"], e.get("t1") if isinstance(e.get("t1"), (int, float)) and abs(now - e["t1"]) < 120 else t)
            sure = u["son"] - u["bas"]
            if sure >= esik and not u["uyardi"]:
                u["uyardi"] = True
                dk = sure / 60; ds = (f"{dk:.1f}".replace(".", ",") if ARAYUZ_DILI != "en" else f"{dk:.1f}").replace(",0", "").replace(".0", "")
                anlik_ver("uzun", _t(f"{ds} dk'dır sen konuşuyorsun", f"You've been talking for {ds} min"),
                          _t("karşı taraf araya girmedi — söz vermek ister misin?", "no one else has spoken — hand over?"))
        elif sz >= 4: u.update(bas=None, uyardi=False)
    # 1) adın geçti
    if ben or AYAR.get("adin_gecti") is False or not e.get("id") or e["id"] in ANLIK["ad_id"]: return
    ad = _ilk_ad()
    if not ad or not re.search(r"(?<![a-z])" + re.escape(ad) + _AD_EK + r"(?![a-z])", sade(str(text)).replace("’", "'")): return
    ANLIK["ad_id"].add(e["id"])
    if len(ANLIK["ad_id"]) > 500: ANLIK["ad_id"] = set(list(ANLIK["ad_id"])[-200:])
    ozet = f"“{' '.join(str(text).split())[:140]}”"; a = ANLIK["son"]
    if a and a["tur"] == "ad" and now - ANLIK["ad_son"].get(kim, 0) < 30 and now - a["t"] < ANLIK_SN: a.update(ayrinti=ozet, t=now)
    else: anlik_ver("ad", _t(f"Adın geçti — {kim}", f"You were mentioned — {kim}"), ozet)
    ANLIK["ad_son"][kim] = now
