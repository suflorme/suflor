# Suflor.me aktarıcı bölümü: İş kopyası — aynı iş farklı toplantılarda yeniden konuşulunca tek kayıt (10 Kasım). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır
# (bolum("is-kopya"), degerlendir'den sonra): AYAR, BASE, STATE, gizli_acik, _yapi_mod, degerlendir/DG_SEMA/dg_acik/dg_sonuc (degerlendir.py) … relay.py'nin ve öbür bölümlerin. import etme. Python 3.9 uyumlu.
# Sorun: "1Password araştırmasını paylaşacak" 29 Ekim'de de 5 Kasım'da da yeni iş olarak kaydoldu; panoda iki açık iş. Belge önerilerinde kayıtla karşılaştırma ve toplantı içinde yeniden yazımda eşleme
# vardı (yapi._benzer, graf_yaz); toplantılar arası yoktu. Kural (kullanıcı, 10 Kasım): asistan karar versin, emin değilse sorsun.
# Akış: açık iş/söz kayıtlarından (yapi.kayit_listesi: gizli ve deneme toplantısı zaten yok) daha önce taranmamış olanlar → aynı sahibin FARKLI toplantı/kaynaktaki açık işleriyle aday (5 harflik kök
#   örtüşmesi ≥ 0,4 ya da yapi._benzer; kayıt başına en çok 3 aday, tur başına en çok 8 çift) → tek değerlendirici (degerlendir("is_kopya"), Sonnet) "aynı iş mi":
#   ayni + güven ≥ IK_GUVEN → YENİ kayıt kalır, ESKİ kapanır (iptal + not, yeniye yorum; model daha iyi metin önerdiyse metin, yenide vade yoksa eskinin vadesi) — hepsi yapi.py'nin olay işlevleri (geri alınabilir);
#   emin_değil (model yoksa/başarısızsa da) → panoda "Bu iki iş aynı mı?" sorusu; farklı → çift "ayrı" kaydı, bir daha sorulmaz. Model yoksa hiçbir şey kendiliğinden kapanmaz.
# Durum: canli/is-kopya.json (0600): taranan kayit_id'ler, ayrı çiftler, bekleyen sorular, son birleştirmeler. Döngü: animsatici gibi — kayıt veritabanı değişince ~10 sn durulunca, değişmese de en çok 2 dk'da bir
#   (taranmamış kayıt kalmadıkça model çağrılmaz). Ayar is_kopya (varsayılan açık; false kapatır); gizli kipte tur yok. Uçlar: GET /is-kopya (anahtarlı, VERI_GET) → {"sorular","birlesen","say"};
#   POST /is-kopya {"islem": "birlestir"|"ayri"|"geri_al", "cift": "s118|s26"} (anahtarlı); /status "is_kopya".
IK_DOSYA = "is-kopya.json"
IK = {"kilit": threading.RLock(), "tur_t": 0.0, "imza": None, "gozlenen": None, "degisti_t": 0.0, "son": 0.0, "kalan": False}
IK_TUR_SN, IK_BAKIS_SN, IK_DURUL_SN, IK_ILK_SN = 120, 15, 10, 45
if os.environ.get("SUFLOR_TEST_BASLAT") and os.environ.get("SUFLOR_IK_HIZLI"): IK_TUR_SN, IK_BAKIS_SN, IK_DURUL_SN, IK_ILK_SN = 4, 1, 1, 1  # yalnız deneme
IK_KOK, IK_ESIK, IK_ADAY_KAYIT, IK_TUR_CIFT, IK_GUVEN = 5, 0.4, 3, 8, 2
IK_SORU_EN_COK, IK_AYRI_EN_COK, IK_TARANAN_EN_COK, IK_BIRLESEN_EN_COK, IK_GERI_SN = 50, 3000, 5000, 100, 24 * 3600
IK_GECICI = ("son çağrı başarısız", "tur sınırı", "günlük tavan", "çok aday", "kapalı", "model yok")  # model bu turda çalışmadı: çift taranmamış kalır, sonra yeniden denenir (soruya dökülmez)
IK_YASAK = re.compile(r"[\[\]<>{}]|KAYIT", re.I)
IK_SORU = ("Bu iki açık iş (aynı sahip, farklı toplantı ya da kaynak) aynı iş mi? Aynı iş = aynı çıktı/teslim ve aynı kişi; yalnızca konu benzerliği yetmez. "
           "Aynıysa YENİ kayıt kalır, ESKİ kapanır.")
def ik_acik(): return AYAR.get("is_kopya") is not False
def _ik_yol(): return os.path.join(BASE, IK_DOSYA)
def ik_oku():
    try:
        with open(_ik_yol(), encoding="utf-8") as f: d = json.load(f)
    except (OSError, ValueError): d = {}
    d = d if isinstance(d, dict) else {}
    for k, v in (("taranan", []), ("ayri", []), ("sorular", []), ("birlesen", [])): d[k] = d[k] if isinstance(d.get(k), list) else v
    d["sayac"] = d["sayac"] if isinstance(d.get("sayac"), dict) else {}
    return d
def ik_yaz(d):
    d = dict(d, taranan=d["taranan"][-IK_TARANAN_EN_COK:], ayri=d["ayri"][-IK_AYRI_EN_COK:], sorular=d["sorular"][-IK_SORU_EN_COK:], birlesen=d["birlesen"][-IK_BIRLESEN_EN_COK:])
    try:
        fd = os.open(_ik_yol() + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
        os.replace(_ik_yol() + ".tmp", _ik_yol())
    except OSError as e: print(f"İŞ KOPYA: durum yazılamadı ({e.__class__.__name__})")
def _ik_kisa(x, n): x = " ".join(str(x or "").split()); return x if len(x) <= n else x[:n - 1].rstrip() + "…"
def _ik_sira(x):  # YENİ/ESKİ ayrımı: toplantı tarihi, eşitse yerel kimlik numarası
    try: n = int(str(x.get("id") or "")[1:])
    except ValueError: n = 0
    return (str(x.get("tarih") or ""), n)
def _ik_cift_kim(a, b):  # "yeni|eski" yerel kimlikleri
    y_, e_ = (a, b) if _ik_sira(a) >= _ik_sira(b) else (b, a); return y_, e_
def _ik_anahtar(a, b): return "|".join(sorted((a["kayit_id"], b["kayit_id"])))
def _ik_kokler(y, m): return {w[:IK_KOK] for w in re.findall(r"[0-9a-z]+", y.kisi_anahtar(m)) if len(w) > 3}
def _ik_ayni_sahip(y, a, b):
    if not a.get("kim") or not b.get("kim"): return False
    ea, eb = str(a.get("sahip_eposta") or "").lower(), str(b.get("sahip_eposta") or "").lower()
    if ea and eb: return ea == eb
    return bool(y.kisi_eslesir(a["kim"], b["kim"]))
def _ik_skor(y, a, b):  # → örtüşme (0-1); benzer metin 1 sayılır
    ka, kb = _ik_kokler(y, a["metin"]), _ik_kokler(y, b["metin"])
    if y._benzer(y.kisi_anahtar(a["metin"]), y.kisi_anahtar(b["metin"])): return 1.0
    return len(ka & kb) / min(len(ka), len(kb)) if ka and kb else 0.0
def ik_acik_isler(y):  # → açık iş satırları (kayit_listesi: gizli ve deneme toplantısı yok)
    v = y.kayit_listesi(BASE, str(AYAR.get("ad") or ""))
    return [x for x in (v.get("kayitlar") or []) if x.get("tur") == "is" and x.get("durum") == "acik" and x.get("kayit_id") and str(x.get("metin") or "").strip()]
def ik_adaylar(y, isler, d, cift_en_cok=IK_TUR_CIFT):
    # Saf karar işlevi (test/is-kopya.py). → (ciftler: [(yeni, eski, skor)], islenen: [kayit_id]) — islenen = bu turda tüm çiftleri değerlendirmeye giren (ya da çifti olmayan) taranmamış kayıtlar.
    taranan, ayri = set(d.get("taranan") or []), set(d.get("ayri") or []); ciftler = []; gor = set(); islenen = []
    for x in sorted((i for i in isler if i["kayit_id"] not in taranan), key=_ik_sira):
        adaylar = []
        for o in isler:
            if o["kayit_id"] == x["kayit_id"]: continue
            if (x.get("toplanti") or "") == (o.get("toplanti") or "") and (x.get("toplanti") or ""): continue  # aynı toplantı içi (toplantı içi eşleme graf_yaz'da)
            k = _ik_anahtar(x, o)
            if k in ayri or not _ik_ayni_sahip(y, x, o): continue
            s = _ik_skor(y, x, o)
            if s >= IK_ESIK: adaylar.append((s, k, o))
        adaylar.sort(key=lambda t: -t[0]); yeni_c = [(s, k, o) for s, k, o in adaylar[:IK_ADAY_KAYIT] if k not in gor]
        if len(ciftler) + len(yeni_c) > cift_en_cok and ciftler: break  # sığmıyor: bu kayıt sonraki turda
        for s, k, o in yeni_c:
            gor.add(k); yn, es = _ik_cift_kim(x, o); ciftler.append((yn, es, round(s, 2)))
        islenen.append(x["kayit_id"])
    return ciftler[:cift_en_cok] if len(ciftler) > cift_en_cok else ciftler, islenen
def _ik_aday(yn, es, skor):
    return {"id": f"{yn['id']}|{es['id']}",
            "metin": f"YENİ ({yn.get('tarih') or '?'}, {_ik_kisa(yn.get('baslik') or 'toplantı', 40)}): {_ik_kisa(yn['metin'], 100)} ‖ ESKİ ({es.get('tarih') or '?'}, {_ik_kisa(es.get('baslik') or 'toplantı', 40)}): {_ik_kisa(es['metin'], 100)}",
            "veri": {"sahip": yn.get("kim"), "yeni vade": yn.get("vade"), "eski vade": es.get("vade"), "sözcük örtüşmesi": skor}, "yedek": {"karar": "emin_degil", "oncelik": 0}}
def _ik_ozet(x): return {"id": x["id"], "kayit_id": x["kayit_id"], "metin": _ik_kisa(x["metin"], 200), "vade": x.get("vade") or "", "tarih": x.get("tarih") or "", "baslik": _ik_kisa(x.get("baslik") or "", 80), "kim": x.get("kim") or ""}

def ik_birlestir(y, d, yn, es, metin="", otomatik=True, kaynak="model"):
    # YENİ kalır, ESKİ kapanır: durum (iptal + not) → yeniye yorum → (önerilen metin) → (yenide vade yoksa eskinin vadesi). Hepsi yapi olayı (geri_al ile geri alınır). → birlesen girdisi ya da None (eski artık açık değil)
    ol = []; tarih_y, tarih_e = yn.get("tarih") or "", es.get("tarih") or ""
    o, _ = y.kayit_durum(BASE, es["id"], "iptal", kaynak="is-kopya", not_=f"aynı iş — {tarih_y} kaydı ({yn['id']}) sürüyor".replace("  ", " "))
    if not o: return None
    ol.append(o["olay_id"])
    top = " ".join(p for p in (tarih_e, es.get("baslik") or "") if p) or "Önceki"
    o, _ = y.yorum_ekle(BASE, yn["id"], f"{top} toplantısındaki aynı iş ({es['id']}) buna birleştirildi.", kaynak="is-kopya")
    if o: ol.append(o["olay_id"])
    m = " ".join(str(metin or "").split())
    if m and len(m) <= 200 and not IK_YASAK.search(m) and m != " ".join(str(yn["metin"]).split()):
        try:
            o, _ = y.metin_duzelt(BASE, yn["id"], m, kaynak="is-kopya")
            if o: ol.append(o["olay_id"])
        except ValueError: pass
    if es.get("vade") and not yn.get("vade"):
        o, _ = y.ertele(BASE, yn["id"], es["vade"], neden="eski kayıttan alındı", kaynak="is-kopya")
        if o: ol.append(o["olay_id"])
    b = {"zaman": time.time(), "cift": f"{yn['id']}|{es['id']}", "yeni": yn["kayit_id"], "eski": es["kayit_id"], "yeni_id": yn["id"], "eski_id": es["id"], "yeni_metin": _ik_kisa(yn["metin"], 120),
         "eski_metin": _ik_kisa(es["metin"], 120), "olaylar": ol, "otomatik": bool(otomatik), "geri": False}
    d["birlesen"].append(b); d["taranan"] = d["taranan"] + [k for k in (yn["kayit_id"], es["kayit_id"]) if k not in d["taranan"]]
    if otomatik: d["sayac"]["otomatik"] = int(d["sayac"].get("otomatik") or 0) + 1
    print(f"İŞ KOPYA: {es['id']} → {yn['id']} birleşti ({kaynak if otomatik else 'kullanıcı'})")  # günlüğe iş metni yazılmaz
    return b

def _ik_soru(d, yn, es, neden, kaynak, metin=""):
    c = f"{yn['id']}|{es['id']}"
    if any(s.get("cift") == c for s in d["sorular"]): return
    d["sorular"].append({"cift": c, "yeni": yn["kayit_id"], "eski": es["kayit_id"], "yeni_id": yn["id"], "eski_id": es["id"], "zaman": time.time(), "neden": _ik_kisa(neden, 120), "kaynak": kaynak,
                         "metin": _ik_kisa(metin, 200), "yeni_ozet": _ik_ozet(yn), "eski_ozet": _ik_ozet(es)})
    d["sayac"]["soru"] = int(d["sayac"].get("soru") or 0) + 1
def ik_tur(zorla=False):
    # Bir tarama turu → {"ok", "cift", "birlesti", "soru", "ayri", "kalan"} ya da {"ok": False, "neden"}. Tek seferde bir tur (kilit).
    if not ik_acik() and not zorla: return {"ok": False, "neden": "kapali"}
    if gizli_acik(): return {"ok": False, "neden": "gizli"}
    if "degerlendir" not in globals() or not dg_acik(): return {"ok": False, "neden": "degerlendirici"}
    if not IK["kilit"].acquire(blocking=False): return {"ok": False, "neden": "mesgul"}
    try:
        IK["tur_t"] = time.time(); y = _yapi_mod()
        if not y: return {"ok": False, "neden": "yapi_yok"}
        isler = ik_acik_isler(y); d = ik_oku(); ciftler, islenen = ik_adaylar(y, isler, d); IK["kalan"] = False
        bos_say = {"birlesti": 0, "soru": 0, "ayri": 0, "ertelendi": 0}
        if not ciftler:
            d["taranan"] += islenen; ik_yaz(d); IK["son"] = time.time(); IK["kalan"] = len([i for i in isler if i["kayit_id"] not in set(d["taranan"])]) > 0
            return dict(bos_say, ok=True, cift=0, kalan=IK["kalan"])
        sonuc = degerlendir("is_kopya", [_ik_aday(*c) for c in ciftler], soru=IK_SORU, sema=DG_SEMA["is_kopya"])
        say = dict(bos_say); ertelenen = set()
        for (yn, es, _s), s in zip(ciftler, sonuc):
            k = _ik_anahtar(yn, es); kar = s.get("karar"); kay = s.get("kaynak")
            if kay == "yedek" and s.get("yedek_neden") in IK_GECICI: ertelenen.update((yn["kayit_id"], es["kayit_id"])); say["ertelendi"] += 1; continue
            if kar == "ayni" and kay != "yedek" and int(s.get("oncelik") or 0) >= IK_GUVEN:
                try: b = ik_birlestir(y, d, yn, es, s.get("metin") or "", True, "model")
                except Exception as e: print(f"İŞ KOPYA: birleştirme hatası ({e.__class__.__name__})"); b = None
                if b: say["birlesti"] += 1; continue
                ertelenen.update((yn["kayit_id"], es["kayit_id"])); continue
            if kar == "farkli" and kay != "yedek": d["ayri"].append(k); say["ayri"] += 1; continue
            _ik_soru(d, yn, es, s.get("neden") or ("model cevap vermedi" if kay == "yedek" else "emin değil"), kay or "model", s.get("metin") or ""); say["soru"] += 1
        d["taranan"] += [k for k in islenen if k not in ertelenen and k not in d["taranan"]]
        IK["kalan"] = bool(ertelenen) or len([i for i in isler if i["kayit_id"] not in set(d["taranan"])]) > 0
        ik_yaz(d); IK["son"] = time.time()
        if any(say.values()): print(f"İŞ KOPYA: tur {len(ciftler)} çift → {say['birlesti']} birleşti, {say['soru']} soru, {say['ayri']} ayrı" + (f", {say['ertelendi']} ertelendi" if say["ertelendi"] else ""))
        return dict(say, ok=True, cift=len(ciftler), kalan=IK["kalan"])
    except Exception as e:
        print(f"İŞ KOPYA: hata ({e.__class__.__name__})"); return {"ok": False, "neden": "hata"}
    finally: IK["imza"] = _ik_imza(); IK["kilit"].release()

def _ik_imza():  # kayıt veritabanının (ve WAL'ının) boyut + değişme zamanı: iş değişti mi
    s = []
    for ek in ("", "-wal"):
        try: st = os.stat(os.path.join(BASE, "karar-grafi.sqlite" + ek)); s.append((st.st_mtime_ns, st.st_size))
        except OSError: s.append(None)
    return tuple(s)
def _ik_canli(y, d):  # bekleyen sorular güncel kayıtla: ikisi de hâlâ açık olanlar (başka yerden kapananlar düşer)
    try: acik = {x["kayit_id"]: x for x in ik_acik_isler(y)}
    except Exception: return []
    out = []
    for s in d["sorular"]:
        yn, es = acik.get(s.get("yeni")), acik.get(s.get("eski"))
        if yn and es: out.append((s, yn, es))
    return out
def ik_view():  # GET /is-kopya (anahtarlı): panoda "Aynı iş olabilir"
    y = _yapi_mod(); d = ik_oku()
    if not y: return {"ok": False, "sorular": [], "birlesen": [], "say": {}}
    sorular = [{"cift": f"{yn['id']}|{es['id']}", "neden": s.get("neden") or "", "yeni": _ik_ozet(yn), "eski": _ik_ozet(es)} for s, yn, es in _ik_canli(y, d)]
    simdi = time.time()
    birlesen = [{"cift": b["cift"], "zaman": b["zaman"], "yeni_metin": b.get("yeni_metin") or "", "eski_metin": b.get("eski_metin") or "", "otomatik": bool(b.get("otomatik"))}
                for b in d["birlesen"] if not b.get("geri") and b.get("otomatik") and simdi - float(b.get("zaman") or 0) <= IK_GERI_SN][::-1]
    return {"ok": True, "acik": ik_acik(), "sorular": sorular, "birlesen": birlesen, "say": {"taranan": len(d["taranan"]), "bekleyen": len(sorular), "otomatik": int(d["sayac"].get("otomatik") or 0)}}
def ik_status():  # /status "is_kopya": yalnız sayı
    d = ik_oku(); y = _yapi_mod()
    return {"acik": ik_acik(), "taranan": len(d["taranan"]), "bekleyen": len(_ik_canli(y, d)) if y else len(d["sorular"]), "son_s": round(time.time() - IK["son"]) if IK["son"] else None,
            "otomatik": int(d["sayac"].get("otomatik") or 0)}
def _ik_cift_bul(liste, cift):
    c = str(cift or "")[:40]; ters = "|".join(reversed(c.split("|")))
    return next((s for s in liste if s.get("cift") in (c, ters)), None)
def ik_islem(p):
    p = p if isinstance(p, dict) else {}; isl = str(p.get("islem") or ""); cift = str(p.get("cift") or "")[:40]
    if isl not in ("birlestir", "ayri", "geri_al") or not cift: return {"ok": False, "err": "islem ve cift gerekli"}
    y = _yapi_mod()
    if not y: return {"ok": False, "err": "yapi"}
    with IK["kilit"]:
        d = ik_oku()
        if isl == "geri_al":
            b = next((x for x in d["birlesen"] if x.get("cift") == cift and not x.get("geri")), None) or _ik_cift_bul([x for x in d["birlesen"] if not x.get("geri")], cift)
            if not b: return {"ok": False, "err": "birleştirme yok"}
            n = 0
            for oid in reversed(b.get("olaylar") or []):
                try: n += len(y.geri_al(BASE, oid, kaynak="is-kopya"))
                except Exception as e: print(f"İŞ KOPYA: geri alma hatası ({e.__class__.__name__})")
            b["geri"] = True; k = "|".join(sorted((b["yeni"], b["eski"])))
            if k not in d["ayri"]: d["ayri"].append(k)
            ik_yaz(d); dg_sonuc("is_kopya", b["cift"], "ret"); print(f"İŞ KOPYA: {b['eski_id']} → {b['yeni_id']} birleştirmesi geri alındı")
            return {"ok": True, "geri_alinan": n}
        s = _ik_cift_bul(d["sorular"], cift)
        if not s: return {"ok": False, "err": "soru yok (cevaplanmış ya da kayıt değişmiş olabilir)"}
        d["sorular"] = [x for x in d["sorular"] if x is not s]; k = "|".join(sorted((s["yeni"], s["eski"])))
        if isl == "ayri":
            if k not in d["ayri"]: d["ayri"].append(k)
            ik_yaz(d); dg_sonuc("is_kopya", s["cift"], "ret"); return {"ok": True}
        acik = {x["kayit_id"]: x for x in ik_acik_isler(y)}; yn, es = acik.get(s["yeni"]), acik.get(s["eski"])
        if not yn or not es: ik_yaz(d); return {"ok": False, "err": "kayıtlardan biri artık açık değil"}
        try: b = ik_birlestir(y, d, yn, es, s.get("metin") or "", False)
        except Exception as e: print(f"İŞ KOPYA: birleştirme hatası ({e.__class__.__name__})"); ik_yaz(d); return {"ok": False, "err": e.__class__.__name__}
        ik_yaz(d)
        if not b: return {"ok": False, "err": "eski kayıt kapatılamadı"}
        dg_sonuc("is_kopya", s["cift"], "kabul"); return {"ok": True, "cift": b["cift"]}

def _ik_dongu():
    time.sleep(IK_ILK_SN)
    while True:
        try:
            if ik_acik() and not gizli_acik():
                imza = _ik_imza(); simdi = time.time()
                if imza != IK["imza"]:  # iş değişti: ~10 sn durulunca tur (art arda değişiklikler tek tura iner), en erken IK_TUR_SN sonra
                    if imza != IK["gozlenen"]: IK["gozlenen"] = imza; IK["degisti_t"] = simdi
                    elif simdi - IK["degisti_t"] >= IK_DURUL_SN and simdi - IK["tur_t"] >= IK_TUR_SN: ik_tur()
                elif IK["kalan"] and simdi - IK["tur_t"] >= IK_TUR_SN: ik_tur()  # taranmamış kayıt kaldı (tur sınırı / model dönmedi): yeniden dene
        except Exception as e: print(f"İŞ KOPYA: döngü hatası ({e.__class__.__name__})")
        time.sleep(IK_BAKIS_SN)
if not os.environ.get("SUFLOR_IK_DONGU_YOK") and not (os.environ.get("SUFLOR_TEST_BASLAT") and not os.environ.get("SUFLOR_IK_HIZLI")): threading.Thread(target=_ik_dongu, daemon=True).start()
