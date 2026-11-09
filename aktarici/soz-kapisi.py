# Suflor.me aktarıcı bölümü: Tek söz kapısı (9 Kasım; asistan mimarisi adım 2). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır
# (bolum("soz-kapisi")): AYAR, BASE, LOCK, write, SOHBET, _KS, bildirim, gizli_acik, toplanti_var, aktif_dosya, sessiz_acik, calisma_saatleri, _t … relay.py'nin ve öbür bölümlerin. import etme.
# Amaç: asistanın KENDİLİĞİNDEN kullanıcıya söylediği ya da bildirdiği her şey (gün içi öneri, toplantı sonrası açık uç, toplantı hatırlatması, e-posta, kişisel tarih,
# sistem uyarısı) tek kapıdan geçer. Zamanlayıcılar yalnız ADAY üretir (soz_aday); kapı karar verir: şimdi / sonra / bastırıldı. Kullanıcının sorusuna verilen cevap, toplantı içi kart ve
# onay kartı kendiliğinden söz değildir: kapsam dışı.
# Engeller TEK yerde (_soz_engel): gizli kip (hiçbir şey sunulmaz, soz.jsonl'e de yazılmaz) · süren toplantı (toplantıyla ilgili olmayan aday bekler) · sessiz mod · gece · mesai (calisma_saatleri) ·
# acil olmayanlar arasında en az aralık (ayar soz_aralik_dk, 20) · günlük bütçe (soz_gunluk_butce, 6). Öncelik 0 bilgi · 1 normal · 2 önemli · 3 acil:
#   3: yalnız gizli kip durdurur (bütçeyi, aralığı, sessiz modu, mesaiyi aşar) · 2: gece/mesai atlanır ama toplantı, sessiz mod, aralık, bütçe geçerli · 0–1: hepsi geçerli.
# Aynı anahtar soz_tekrar_dk (360) içinde ikinci kez sunulmaz. Kaynağa özgü sınırlar (gün içi önerinin günde 3'ü, 90 dk aralığı, e-postanın sessiz saatleri) kaynakta kalır.
# "sonra": bellekte + canli/soz-kuyruk.json'da bekler, dakikalık döngü yeniden değerlendirir, gecerli_sn dolunca düşer (soz.jsonl'de "gecti"). Yeniden başlayınca kuyruktaki öğeler varsayılan bildirimle teslim edilir.
# Kayıt canli/soz.jsonl (yalnız eklenir; METİN YOK, anahtar yalnız kaynak+anahtar özeti): sunuldu · teslim · gecti · iptal · bastirildi · sonuc (kabul|ret|ertele|yoksay).
# Sunulup kaynağın kendi süresi içinde işlem görmeyen söz otomatik "yoksay" olur. Kullanıcı işlemleri kaynak uçlarından soz_sonuc(ref, sonuc) ile bağlanır; ref = söz kimliği | anahtar | "kaynak:<ad>" (o kaynağın son sunulan, sonuçsuz sözü).
# Ayarlar (yalnız ayar.json; ⚙ Ayarlar'da yok): soz_aralik_dk, soz_gunluk_butce, soz_tekrar_dk, soz_gece (false kapatır), soz_gece_bas (22), soz_gece_bit (7). Ölçüm: olcum.py isabet. /status "soz".
import hashlib

SOZ_DOSYA, SOZ_KUYRUK_DOSYA = "soz.jsonl", "soz-kuyruk.json"
SOZK = {"kuyrukta_teslim": False, "kuyruk": [], "son": {}, "tekrar": {}, "bekle": {}, "gun": {"tarih": "", "teslim": 0, "bastirilan": 0}, "son_t": 0.0, "n": 0, "dongu": False, "bekleyen_yaz": []}
SOZ_KILIT = threading.RLock()
_BILDIRIM_YEREL = globals().get("_BILDIRIM_YEREL") or threading.local()  # relay.py tanımlar; yalıtılmış testte burada
SOZ_SAAT = globals().get("SOZ_SAAT") or time.time  # testlerde sahte saat (önceden tanımlıysa korunur)
SOZ_SONUCLAR = ("kabul", "ret", "ertele", "yoksay")
SOZ_DONGU_SN, SOZ_GECERLI_SN, SOZ_YOKSAY_VARSAYILAN = 60, 4 * 3600, 4 * 3600
SOZ_YOKSAY_SN = {"gun_ici": 1800, "toplanti_sonrasi": 3600, "toplanti_hatirlat": 900, "toplanti_cikis": 3600, "gun_plani": 6 * 3600, "eposta": 8 * 3600, "kisisel_tarih": 12 * 3600, "sistem": 3600}  # kaynağın kendi süresi: sonuç gelmezse otomatik yoksay
SOZ_BASLIK = {"gun_ici": ("Öneri", "Suggestion"), "toplanti_sonrasi": ("Açık uçlar", "Open items"), "toplanti_hatirlat": ("Toplantı yaklaşıyor", "Meeting coming up"), "toplanti_cikis": ("Toplantı özeti", "Meeting summary"), "gun_plani": ("Günün planı hazır", "Today's plan is ready"),
              "eposta": ("E-posta", "Email"), "kisisel_tarih": ("Kişisel tarih", "Personal date")}

def _soz_say(ad, v, lo, hi):
    try: x = float(AYAR.get(ad, v))
    except (TypeError, ValueError): x = float(v)
    return min(float(hi), max(float(lo), x))
def soz_butce(): return int(_soz_say("soz_gunluk_butce", 6, 0, 100))
def _soz_h(kaynak, anahtar): return hashlib.sha1((str(kaynak) + "|" + str(anahtar)).encode("utf-8")).hexdigest()[:10]
def _soz_zaman(t): return datetime.datetime.fromtimestamp(t).isoformat(timespec="seconds")
def _soz_yol(ad): return os.path.join(BASE, ad)

def _soz_yaz(r):  # yalnız eklenir; LOCK alınamazsa (başka iş tutuyor) bellekte bekler, sonraki yazışta gider
    SOZK["bekleyen_yaz"].append(json.dumps(r, ensure_ascii=False) + "\n")
    try:
        if not LOCK.acquire(timeout=2): return
    except Exception: return
    try:
        write([(_soz_yol(SOZ_DOSYA), "".join(SOZK["bekleyen_yaz"]))]); SOZK["bekleyen_yaz"] = []
    except Exception as e: print(f"SÖZ: kayıt yazılamadı ({e.__class__.__name__})")
    finally: LOCK.release()
def _soz_kuyruk_yaz():
    if not SOZK["kuyruk"] and not os.path.exists(_soz_yol(SOZ_KUYRUK_DOSYA)): return  # hiç kuyruk olmadıysa dosya da açılmaz
    try:
        v = [{k: q[k] for k in ("id", "kaynak", "h", "oncelik", "kip", "bitis", "t0", "metin", "ek")} for q in SOZK["kuyruk"]]
        with open(_soz_yol(SOZ_KUYRUK_DOSYA) + ".tmp", "w", encoding="utf-8") as f: json.dump(v, f, ensure_ascii=False)
        os.replace(_soz_yol(SOZ_KUYRUK_DOSYA) + ".tmp", _soz_yol(SOZ_KUYRUK_DOSYA))
    except OSError: pass

def _soz_gun(simdi):
    tarih = datetime.date.fromtimestamp(simdi).isoformat(); g = SOZK["gun"]
    if g["tarih"] != tarih: g.update(tarih=tarih, teslim=0, bastirilan=0)

def _soz_mesai(simdi):  # ayar calisma_saatleri (varsayılan Pzt–Cum 09:00–18:00)
    try: g, b, e = calisma_saatleri()
    except Exception: g, b, e = {0, 1, 2, 3, 4}, 540, 1080
    d = datetime.datetime.fromtimestamp(simdi)
    return d.weekday() in g and b <= d.hour * 60 + d.minute < e
def _soz_gece(simdi):
    if AYAR.get("soz_gece") is False: return False
    b, e = int(_soz_say("soz_gece_bas", 22, 0, 23)), int(_soz_say("soz_gece_bit", 7, 0, 23)); h = datetime.datetime.fromtimestamp(simdi).hour
    return (h >= b or h < e) if b > e else (b <= h < e)
def _soz_asistan_mesgul():
    try: return bool(SOHBET["acik"] or ("_KS" in globals() and _KS.get("tur")))
    except Exception: return False

def _soz_engel(kaynak, oncelik, kip, ek, simdi):  # → None (şimdi sunulabilir) ya da (karar, neden); gizli kip soz_aday'da önce bakılır
    if gizli_acik(): return ("bastirildi", "gizli kip")
    if oncelik < 3:
        if toplanti_var() or aktif_dosya():
            if not ek.get("toplantiyla_ilgili"): return ("sonra", "toplantı sürüyor")
        if sessiz_acik(): return ("sonra", "sessiz mod")
        if oncelik < 2 and not _soz_mesai(simdi): return ("sonra", "mesai dışı")
        if _soz_gece(simdi) and not ek.get("kullanici_aktif"): return ("sonra", "gece")  # kullanici_aktif: kullanıcı az önce etkindi (toplantıdan yeni çıktı) — gece kuralı kendiliğinden söz için
        if kip != "bildir" and _soz_asistan_mesgul(): return ("sonra", "asistan meşgul")
        if simdi - SOZK["son_t"] < _soz_say("soz_aralik_dk", 20, 0, 720) * 60: return ("sonra", "aralık dolmadı")
        if SOZK["gun"]["teslim"] >= soz_butce(): return ("bastirildi", "günlük bütçe")
    return None

def _soz_varsayilan(r):  # teslim işlevi verilmeyen (ya da yeniden başlatmadan sonra kuyruktan gelen) söz: menü bildirimi
    bildirim("Suflor.me", _t(*SOZ_BASLIK.get(r["kaynak"], ("Suflor.me", "Suflor.me"))), r.get("metin") or "")

def _soz_teslim_et(r):  # kilit DIŞINDA; teslim işlevi False dönerse söz iptal sayılır
    f = r.get("teslim_f")
    _BILDIRIM_YEREL.asistan = r["kaynak"] != "sistem"  # 10 Kasım: söz kapısından geçen her şey asistanın adıyla (sistem uyarısı Suflor.me)
    try: s = _soz_varsayilan(r) if f is None else f()
    except Exception as e: print(f"SÖZ: teslim hatası ({r['kaynak']}: {e.__class__.__name__})"); return True
    finally: _BILDIRIM_YEREL.asistan = False
    return s is not False
def _soz_sayac(r, simdi):  # teslim sayıldı (kilit içinde)
    SOZK["gun"]["teslim"] += 1; r["teslim_edildi"] = True; r["teslim_t"] = simdi
    if r["oncelik"] < 3: SOZK["son_t"] = simdi
    SOZK["bekle"][r["id"]] = simdi + float((r.get("ek") or {}).get("yoksay_sn") or SOZ_YOKSAY_SN.get(r["kaynak"], SOZ_YOKSAY_VARSAYILAN))
def _soz_kayit(olay, r, simdi, **ek):
    _soz_yaz(dict({"olay": olay, "id": r["id"], "kaynak": r["kaynak"], "a": r["h"], "t": round(simdi, 1), "z": _soz_zaman(simdi)}, **ek))
def soz_simdi(t):  # teslim işlevleri için: söz kuyruktan geliyorsa şimdiki saat, değilse çağıranın verdiği an
    return float(SOZ_SAAT()) if SOZK["kuyrukta_teslim"] else t
def _soz_son_tut(r):
    SOZK["son"][r["id"]] = r
    if len(SOZK["son"]) > 300:
        for k in sorted(SOZK["son"], key=lambda i: SOZK["son"][i]["t"])[:50]: SOZK["son"].pop(k, None)

def soz_aday(kaynak, metin, *, anahtar, oncelik=1, kip="bildir", teslim=None, gecerli_sn=None, ek=None, simdi=None):
    # kaynak: "gun_ici" | "toplanti_sonrasi" | "toplanti_hatirlat" | "eposta" | "kisisel_tarih" | "sistem" … · teslim: bugünkü teslim işlevi (bildirim/ses/pano durumu; argümansız) · simdi: yalnız testler
    # → {"id", "karar": "simdi" | "sonra" | "bastirildi", "neden"}; "simdi"de teslim bu çağrıda çalıştı
    simdi = float(simdi) if simdi else float(SOZ_SAAT())
    try: oncelik = max(0, min(3, int(oncelik)))
    except (TypeError, ValueError): oncelik = 1
    kip = kip if kip in ("bildir", "sor", "onayla") else "bildir"
    if gizli_acik():  # hiçbir şey sunulmaz, kayıt da yok; yalnız sistem uyarısı (içerik taşımaz: "Claude oturumu düştü" vb.) kayıtsız hemen gösterilir — gizli toplantıda sessizce bozulmasın
        if kaynak == "sistem" and oncelik >= 2:
            _soz_teslim_et({"kaynak": kaynak, "metin": metin, "teslim_f": teslim}); return {"id": "", "karar": "simdi", "neden": "sistem (gizli kip, kayıtsız)"}
        return {"id": "", "karar": "bastirildi", "neden": "gizli kip"}
    ek = {k: v for k, v in (ek or {}).items() if isinstance(v, (bool, int, float, str))} if isinstance(ek, dict) else {}
    h = _soz_h(kaynak, anahtar); gecerli = float(gecerli_sn) if gecerli_sn else float(SOZ_GECERLI_SN)
    with SOZ_KILIT:
        _soz_gun(simdi)
        for q in SOZK["kuyruk"]:
            if q["h"] == h: return {"id": q["id"], "karar": "sonra", "neden": "kuyrukta"}
        t0 = SOZK["tekrar"].get(h)
        if t0 is not None and simdi - t0[0] < _soz_say("soz_tekrar_dk", 360, 0, 10080) * 60: return {"id": t0[1], "karar": "bastirildi", "neden": "tekrar"}
        SOZK["n"] += 1
        r = {"id": "z" + str(int(simdi * 1000)) + "%02d" % (SOZK["n"] % 100), "kaynak": str(kaynak), "anahtar": str(anahtar), "h": h, "oncelik": oncelik, "kip": kip, "metin": str(metin or ""), "ek": ek,
             "teslim_f": teslim, "t": simdi, "t0": simdi, "bitis": simdi + gecerli, "sonuc": None, "teslim_edildi": False}
        e = _soz_engel(kaynak, oncelik, kip, ek, simdi)
        _soz_son_tut(r)
        if e is None:
            SOZK["tekrar"][h] = (simdi, r["id"]); _soz_sayac(r, simdi); _soz_kayit("sunuldu", r, simdi, oncelik=oncelik, kip=kip, karar="simdi", neden="")
        elif e[0] == "sonra":
            SOZK["kuyruk"].append(r); SOZK["tekrar"][h] = (simdi, r["id"]); _soz_kuyruk_yaz()
            _soz_kayit("sunuldu", r, simdi, oncelik=oncelik, kip=kip, karar="sonra", neden=e[1])
            return {"id": r["id"], "karar": "sonra", "neden": e[1]}
        else:
            SOZK["tekrar"][h] = (simdi, r["id"]); SOZK["gun"]["bastirilan"] += 1
            _soz_kayit("sunuldu", r, simdi, oncelik=oncelik, kip=kip, karar="bastirildi", neden=e[1])
            return {"id": r["id"], "karar": "bastirildi", "neden": e[1]}
    if not _soz_teslim_et(r):
        with SOZ_KILIT:
            SOZK["gun"]["teslim"] = max(0, SOZK["gun"]["teslim"] - 1); SOZK["bekle"].pop(r["id"], None); SOZK["tekrar"].pop(h, None); r["teslim_edildi"] = False
            _soz_kayit("iptal", r, simdi, neden="teslim iptal")
        return {"id": r["id"], "karar": "bastirildi", "neden": "teslim iptal"}
    return {"id": r["id"], "karar": "simdi", "neden": ""}

def soz_tur(simdi=None):  # dakikalık: kuyruğu yeniden değerlendir, süresi dolanı düşür, sonuç gelmeyeni otomatik yoksay say → {"teslim", "gecti", "yoksay"}
    simdi = float(simdi) if simdi else float(SOZ_SAAT()); out = {"teslim": 0, "gecti": 0, "yoksay": 0, "bastirildi": 0}; teslimler = []
    if gizli_acik(): return out  # gizli kipte kuyruk bekler, hiçbir şey yazılmaz
    with SOZ_KILIT:
        _soz_gun(simdi)
        for q in [q for q in SOZK["kuyruk"] if simdi > q["bitis"]]:
            SOZK["kuyruk"].remove(q); _soz_kayit("gecti", q, simdi); out["gecti"] += 1
        for q in sorted(list(SOZK["kuyruk"]), key=lambda q: (-q["oncelik"], q["t0"])):
            e = _soz_engel(q["kaynak"], q["oncelik"], q["kip"], q.get("ek") or {}, simdi)
            if e is None:
                SOZK["kuyruk"].remove(q); _soz_sayac(q, simdi); _soz_kayit("teslim", q, simdi, bekleme_sn=round(simdi - q["t0"])); teslimler.append(q); out["teslim"] += 1
            elif e[0] == "bastirildi":
                SOZK["kuyruk"].remove(q); SOZK["gun"]["bastirilan"] += 1; _soz_kayit("bastirildi", q, simdi, neden=e[1]); out["bastirildi"] += 1
        for i, bit in [(i, b) for i, b in SOZK["bekle"].items() if simdi >= b]:
            SOZK["bekle"].pop(i, None); r = SOZK["son"].get(i)
            if r and not r.get("sonuc"): r["sonuc"] = "yoksay"; _soz_kayit("sonuc", r, simdi, sonuc="yoksay", otomatik=True); out["yoksay"] += 1
        _soz_kuyruk_yaz()
    for q in teslimler:
        SOZK["kuyrukta_teslim"] = True
        try: sonuc = _soz_teslim_et(q)
        finally: SOZK["kuyrukta_teslim"] = False
        if not sonuc:
            with SOZ_KILIT: SOZK["gun"]["teslim"] = max(0, SOZK["gun"]["teslim"] - 1); SOZK["bekle"].pop(q["id"], None); _soz_kayit("iptal", q, simdi, neden="teslim iptal")
    return out

def _soz_coz(ref):
    ref = str(ref or ""); sn = SOZK["son"]
    if ref in sn: return sn[ref]
    if ref.startswith("kaynak:"):
        a = [r for r in sn.values() if r["kaynak"] == ref[7:] and r.get("teslim_edildi") and not r.get("sonuc")]
        return max(a, key=lambda r: r["t"]) if a else None
    a = [r for r in sn.values() if r.get("anahtar") == ref or r["h"] == _soz_h(r["kaynak"], ref)]
    return max(a, key=lambda r: r["t"]) if a else None
def soz_sonuc(ref, sonuc, simdi=None):  # kullanıcı işlemi: kabul | ret | ertele | yoksay → {"ok", "id"}; söz bilinmiyorsa ya da sonucu zaten varsa ok False (hata fırlatmaz)
    if sonuc not in SOZ_SONUCLAR: return {"ok": False, "neden": "sonuç"}
    simdi = float(simdi) if simdi else float(SOZ_SAAT())
    try:
        with SOZ_KILIT:
            r = _soz_coz(ref)
            if not r: return {"ok": False, "neden": "söz yok"}
            if r.get("sonuc") and r["sonuc"] != "yoksay": return {"ok": False, "neden": "sonuç var", "id": r["id"]}
            r["sonuc"] = sonuc; SOZK["bekle"].pop(r["id"], None); _soz_kayit("sonuc", r, simdi, sonuc=sonuc, otomatik=False)
            for q in [q for q in SOZK["kuyruk"] if q["id"] == r["id"]]: SOZK["kuyruk"].remove(q)  # kuyrukta beklerken sonuçlanan söz sunulmaz
            return {"ok": True, "id": r["id"]}
    except Exception as e: print(f"SÖZ: sonuç yazılamadı ({e.__class__.__name__})"); return {"ok": False, "neden": "hata"}
def soz_view():  # /status "soz"
    g = SOZK["gun"]
    return {"sunulan": g["teslim"], "bastirilan": g["bastirilan"], "kuyruk": len(SOZK["kuyruk"]), "butce": soz_butce(), "kalan": max(0, soz_butce() - g["teslim"])}

def _soz_yukle():  # açılışta: son kayıtlardan tekrar önleme, günlük sayaç, sonuçsuz sözler; kuyruk dosyasından bekleyenler (varsayılan bildirimle teslim edilir)
    simdi = float(SOZ_SAAT()); _soz_gun(simdi)
    try:
        with open(_soz_yol(SOZ_DOSYA), encoding="utf-8") as f: satirlar = f.readlines()[-600:]
    except OSError: satirlar = []
    bugun = SOZK["gun"]["tarih"]
    for l in satirlar:
        try: r = json.loads(l)
        except ValueError: continue
        if not isinstance(r, dict) or not r.get("id") or not r.get("a"): continue
        t = float(r.get("t") or 0)
        if simdi - t > 3 * 86400: continue
        o = r.get("olay"); s = SOZK["son"].get(r["id"])
        if o == "sunuldu":
            SOZK["tekrar"][r["a"]] = (t, r["id"])
            s = SOZK["son"][r["id"]] = {"id": r["id"], "kaynak": str(r.get("kaynak") or ""), "anahtar": "", "h": r["a"], "oncelik": int(r.get("oncelik") or 1), "kip": r.get("kip") or "bildir", "metin": "", "ek": {},
                                       "teslim_f": None, "t": t, "t0": t, "bitis": t, "sonuc": None, "teslim_edildi": r.get("karar") == "simdi"}
            if r.get("karar") == "simdi":
                if r.get("z", "")[:10] == bugun: SOZK["gun"]["teslim"] += 1
                if s["oncelik"] < 3: SOZK["son_t"] = max(SOZK["son_t"], t)
            elif r.get("karar") == "bastirildi" and r.get("z", "")[:10] == bugun: SOZK["gun"]["bastirilan"] += 1
        elif o == "teslim" and s:
            s["teslim_edildi"] = True
            if r.get("z", "")[:10] == bugun: SOZK["gun"]["teslim"] += 1
            if s["oncelik"] < 3: SOZK["son_t"] = max(SOZK["son_t"], t)
        elif o == "sonuc" and s: s["sonuc"] = r.get("sonuc")
    for s in SOZK["son"].values():
        if s["teslim_edildi"] and not s["sonuc"]:
            bit = s["t"] + SOZ_YOKSAY_SN.get(s["kaynak"], SOZ_YOKSAY_VARSAYILAN)
            if bit > simdi: SOZK["bekle"][s["id"]] = bit
    try:
        with open(_soz_yol(SOZ_KUYRUK_DOSYA), encoding="utf-8") as f: v = json.load(f)
        for q in v if isinstance(v, list) else []:
            if isinstance(q, dict) and q.get("id") and float(q.get("bitis") or 0) > simdi:
                q = dict(q, teslim_f=None, t=float(q.get("t0") or simdi), sonuc=None, teslim_edildi=False, anahtar=""); SOZK["kuyruk"].append(q); SOZK["son"].setdefault(q["id"], q)
    except (OSError, ValueError, TypeError): pass

def _soz_dongu():
    while True:
        time.sleep(SOZ_DONGU_SN)
        try: soz_tur()
        except Exception as e: print(f"SÖZ: döngü hatası ({e.__class__.__name__}: {e})")
def soz_baslat():
    if SOZK["dongu"]: return
    SOZK["dongu"] = True; threading.Thread(target=_soz_dongu, daemon=True).start()
try: _soz_yukle()
except Exception as e: print(f"SÖZ: kayıtlar yüklenemedi ({e.__class__.__name__})")
if not os.environ.get("SUFLOR_TEST_SOZ_DONGU_YOK"): soz_baslat()
