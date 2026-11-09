# Suflor.me aktarıcı bölümü: Toplantı sonrası proaktif hatırlatma (5 Kasım, "sürekli assist eden proaktif kişisel asistan").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("toplanti-sonrasi")): AYAR, STATE, SON, BASE, bildirim, konus_yazili … relay.py'nin. import etme.
# Özet hazır olduktan ayar toplanti_sonrasi_hatirlat_dk (varsayılan 10; 0 kapalı) dakika sonra, toplantının yapı dosyasından (.yapi.json) açık uçlar sayılır:
# tarihsiz iş, sahipsiz iş, teyit bekleyen karar, cevapsız açık soru. Biri > 0 ise: menü bildirimi + panoda Bugün'ün başında tek cümle ve "Bakalım" düğmesi
# (asistana yazılı soru gider); sesli söyleme yalnız ayar toplanti_sonrasi_sesli: true ve toplantıda/Konuş'ta değilken. Bir toplantı için bir kez.
# Atlanır: gizli toplantı, deneme (Deneme toplantısı kipi, "deneme" adı, yapıda "deneme": true), yeni toplantı başlamış, kullanıcı o arada panoda Kararlar ve işler'i açmış
# (POST /proaktif gordu) ya da asistana sormuş. Gizli toplantının özeti zaten gelmez; yine de tetik anında gizli kip denetlenir.
# --- Gün içi proaktif öneri (9 Kasım): toplantı dışında, kullanıcı boşken, mesai saatinde, günde en çok N kez asistan KISA BİR ÖNERİ cümlesi kurar ---
# Kaynak: yapi.bugun_veri (geciken işler, teyit bekleyen kararlar, bugün vadeli işler) ve belge_oneri_view (belgeden önerilen işler). Sıra: gecikmiş > teyit > bugün vadeli > belge. Bir seferde bir öneri.
# Yazma hiç yapılmaz: öneri cümlesi + (varsa) hazır [KAYIT] komutu PRO_BAG'a konur; kullanıcının sonraki Konuş sorusunda asistana bağlam olarak gider (pro_baglam, notlar.py kayit_sonuc_notu):
# kullanıcı "evet" derse asistan etiketi koyar, onay kartı panoda açılır (izin_iste "kayit") — yazma yine tek tık onaylı. Kanallar: menü bildirimi + panoda Bugün şeridi ("Bakalım" = evet, onaya sun) + isteğe bağlı sesli (toplanti_sonrasi_sesli).
# Ayarlar: proaktif_oneri (açık; false kapatır), proaktif_gunluk_en_cok (3; 0 kapalı), proaktif_aralik_dk (90; iki öneri arası), proaktif_bosta_dk (5; kullanıcı son bu kadar dk asistana/Kararlar'a dokunmamış olmalı).
# Atlanır: gizli kip, toplantı ya da deneme (duman) toplantısı, sessiz mod, asistan konuşurken/sohbetteyken, mesai (calisma_saatleri) dışı, günlük sınır, aralık dolmamış, panoda bekleyen şerit var.
# Tekrar: aynı öneri (tür + kayıt kimlikleri) 24 saat sonrasına kadar yeniden sunulmaz; öneri çıkmadıysa 20 dk sonra yeniden bakılır. Durum proaktif.json'da (gun, oneri).
PRO_SORU = "Son toplantının açık uçlarını sırayla sor: tarihsiz işler, sahipsiz işler, teyit bekleyen kararlar"
PRO_DOSYA = "proaktif.json"
PROAKTIF = {"bekleyen": None, "yapildi": set(), "gordu_t": 0.0, "zamanlayici": {}}
PRO_GUN = {"tarih": "", "n": 0, "son_t": 0.0, "oneri": {}, "bakis_t": 0.0, "dongu": False}  # günlük sayaç, son sunum, anahtar → sunum zamanı, son boş bakış
PRO_BAG = {"a": None, "n": 0}  # asistana bildirilecek son gün önerisi: {"cumle", "komut", "arg", "t"}; en çok PRO_BAG_TUR turda söylenir, PRO_BAG_SN sonra düşer
PRO_TARAMA_SN, PRO_BOS_SN, PRO_TEKRAR_SN, PRO_BAG_SN, PRO_BAG_TUR, PRO_BEKLEYEN_SN = 120, 1200, 86400, 3 * 3600, 2, 1800

def _soz_sonuc_g(ref, sonuc):  # kullanıcı işlemini tek söz kapısına bildirir (soz-kapisi.py soz_sonuc); kapı yüklü değilse (yalıtılmış test) sessiz
    f = globals().get("soz_sonuc")
    if f:
        try: f(ref, sonuc)
        except Exception: pass
def _pro_oku():
    try:
        with open(os.path.join(BASE, PRO_DOSYA), encoding="utf-8") as f: v = json.load(f)
        PROAKTIF["yapildi"] = set(str(x) for x in (v.get("yapildi") or []))
        g = v.get("gun") or {}; PRO_GUN["tarih"], PRO_GUN["n"], PRO_GUN["son_t"] = str(g.get("tarih") or ""), int(g.get("n") or 0), float(g.get("son_t") or 0)
        PRO_GUN["oneri"] = {str(k): float(t) for k, t in (v.get("oneri") or {}).items() if time.time() - float(t) < 3 * 86400}
    except (OSError, ValueError, AttributeError, TypeError): pass
def _pro_yaz():
    try:
        with open(os.path.join(BASE, PRO_DOSYA) + ".tmp", "w", encoding="utf-8") as f: json.dump({"yapildi": sorted(PROAKTIF["yapildi"])[-200:], "gun": {"tarih": PRO_GUN["tarih"], "n": PRO_GUN["n"], "son_t": PRO_GUN["son_t"]}, "oneri": PRO_GUN["oneri"]}, f)
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
    return f"{baslik}: " + ", ".join(p) + ". " + _t((globals().get("cesit") or (lambda k_, l_: l_[0]))("pro_son", ["Bir bakalım mı?", "Birlikte toparlayalım mı?", "Şimdi bakalım mı, beş dakika sürmez?"]), "Shall we look?")  # 9 Kasım (dost): dönüşümlü kapanış

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
        if gizli_acik(): return  # gizli kip: hiçbir şey sunulmaz, işaretlenmez (soz-kapisi.py de aynısını yapar)
        c = pro_say(r["yapi"])
        if not c: return atla("yapı dosyası okunamadı")
        if _pro_deneme(r, c): return atla("deneme toplantısı")
        if aktif_dosya() or toplanti_var(): return atla("yeni toplantı başlamış")
        if PROAKTIF["gordu_t"] > float(r.get("t") or 0): return atla("kullanıcı Kararlar ve işler'e baktı")
        if "_KS" in globals() and _KS.get("sayac", 0) != sayac0: return atla("kullanıcı asistana sordu")
        if not (c["tarihsiz"] or c["sahipsiz"] or c["teyit"] or c["acik"]): return atla("açık uç yok")
        cumle = pro_cumle(r.get("baslik") or r.get("dosya") or _t("Son toplantı", "Last meeting"), c)
        def teslim():  # tek söz kapısı (soz-kapisi.py) şimdi dediğinde ya da kapı yoksa hemen
            PROAKTIF["yapildi"].add(_pro_k(r)); PRO_GUN["son_t"] = time.time(); _pro_yaz()  # gün içi öneriyle üst üste binmesin (günlük sayaca girmez)
            PROAKTIF["bekleyen"] = {"id": r["id"], "cumle": cumle, "t": time.time()}
            print(f"PROAKTİF: {cumle}")
            bildirim("Suflor.me", _t("Açık uçlar", "Open items"), cumle, son=r["id"])
            if AYAR.get("toplanti_sonrasi_sesli") is True and not SOHBET["acik"] and not (_KS.get("tur") if "_KS" in globals() else None) and not gizli_acik(): seslendir(cumle, kuyruk=True)
        if "soz_aday" in globals():  # aynı toplantı için yeniden planlansa da (yeniden başlatma) kapı anahtardan tanır; sonra/bastırılan söz işaretlenir ki yeniden aranmasın
            k = soz_aday("toplanti_sonrasi", cumle, anahtar="ts:" + _pro_k(r), oncelik=1, kip="sor", teslim=teslim, gecerli_sn=4 * 3600)
            if k["karar"] != "simdi" and k["neden"] != "gizli kip": PROAKTIF["yapildi"].add(_pro_k(r)); _pro_yaz()
        else: teslim()
    except Exception as e: print(f"PROAKTİF: hata ({e.__class__.__name__}: {e})")

def pro_view():  # /status "proaktif": panoda Bugün'ün başındaki cümle; yeni toplantı başlayınca ya da elle kapatılınca kalkar
    b = PROAKTIF["bekleyen"]
    if not b: return None
    if aktif_dosya() or gizli_acik(): return None
    return dict({"id": b["id"], "cumle": b["cumle"]}, **({"tur": "gun", "yazma": bool((b["gun"] or {}).get("komut"))} if b.get("gun") else {}))  # tur gun: gün içi öneri ("Bakalım" = evet, onaya sun)

def pro_islem(p):  # POST /proaktif (yalnız pano): sor (Bakalım) | kapat | gordu (Kararlar ve işler açıldı)
    i = p.get("islem")
    b = PROAKTIF["bekleyen"]
    if i == "gordu":
        PROAKTIF["gordu_t"] = time.time()
        if b and not b.get("gun"): _soz_sonuc_g("kaynak:toplanti_sonrasi", "kabul")  # kendiliğinden Kararlar ve işler'e gitti: açık uçlara baktı
        return {"ok": True}
    if i == "tara": return {"ok": True, "sonuc": pro_gun_tara(zorla=bool(p.get("zorla")))}  # elle bir tarama (testler, ileride pano); kurallar aynen geçerli, yalnız "boş bakış" bekleme süresi atlanır
    if i == "kapat":
        if b and b["id"] == p.get("id"):
            PROAKTIF["bekleyen"] = None
            if b.get("gun"): PRO_BAG["a"] = None  # kapatılan öneri asistana söylenmez
            _soz_sonuc_g("kaynak:" + ("gun_ici" if b.get("gun") else "toplanti_sonrasi"), "ret")
        return {"ok": True}
    if i == "sor":
        if not b or b["id"] != p.get("id"): return {"ok": False, "err": _t("hatırlatma yok", "no reminder")}
        if gizli_acik(): return gizli_red()
        if b.get("gun"):  # gün içi öneri: soru cümlenin kendisi + hazır komut (kayıt sözcüğü geçtiği için asistan kayıt kuralını ve kayıt listesini de alır); onay kartı yine panoda
            a = b["gun"]
            r = konus_yazili(_t("Evet, ", "Yes, ") + (_t(f"kaydı onayıma sun: {a['cumle']} (kayıt komutu: {a['komut']} {json.dumps(a['arg'], ensure_ascii=False)})", f"put the record up for my approval: {a['cumle']} (record command: {a['komut']} {json.dumps(a['arg'], ensure_ascii=False)})")
                                                      if a.get("komut") else _t(f"olur, iyi fikir: {a['cumle']}", f"sure, good idea: {a['cumle']}") if a.get("tur") == "dostca"
                                                      else _t(f"birlikte bakalım: {a['cumle']}", f"let's look together: {a['cumle']}")))
            if r.get("ok"): PROAKTIF["bekleyen"] = None; PRO_BAG["a"] = None; _soz_sonuc_g("kaynak:gun_ici", "kabul"); print("PROAKTİF: gün içi öneri — evet, asistana soruldu")
            return r
        r = konus_yazili(_t(PRO_SORU, "Ask me, one by one, about the open items of the last meeting: items without a due date, items without an owner, decisions awaiting confirmation"))
        if r.get("ok"): PROAKTIF["bekleyen"] = None; _soz_sonuc_g("kaynak:toplanti_sonrasi", "kabul"); print("PROAKTİF: Bakalım — asistana soruldu")
        return r
    return {"ok": False, "err": "islem"}

def pro_yukle():  # aktarıcı açılışında (son_yukle'den sonra): son 3 saatin henüz işlenmemiş özetleri için kalan süreyle yeniden planla
    _pro_oku()
    pro_gun_baslat()
    for r in list(SON):
        try:
            if r.get("yapi") and _pro_k(r) not in PROAKTIF["yapildi"] and time.time() - float(r.get("t") or 0) < 3 * 3600: pro_planla(r, pro_dk() * 60 - (time.time() - float(r.get("t") or 0)))
        except Exception: pass

# --- Gün içi öneri: aday kurma, kurallar, tarama, asistana bağlam ---------------------------------------------------------------------------------
def _pro_say(ad, v, lo, hi):
    try: x = float(AYAR.get(ad, v))
    except (TypeError, ValueError): x = float(v)
    return min(float(hi), max(float(lo), x))
def pro_gun_en_cok(): return int(_pro_say("proaktif_gunluk_en_cok", 3, 0, 10))
def pro_gun_acik(): return AYAR.get("proaktif_oneri") is not False and pro_gun_en_cok() > 0

_PRO_AY = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_PRO_AY_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
def _pro_cuma(bugun):  # bugünden sonraki ilk cuma (bugün cumaysa gelecek hafta)
    return bugun + datetime.timedelta(days=(4 - bugun.weekday()) % 7 or 7)
def _pro_kisa(m, n=50):
    m = " ".join(str(m or "").split())
    return m if len(m) <= n else m[:n - 1].rstrip() + "…"

def pro_aday_kur(veri, belgeler, bugun):
    # saf: bugun_veri sözlüğü + belge önerileri listesi → öncelik sırasıyla adaylar [{"anahtar", "tur", "cumle", "komut", "arg"}]; komutsuz aday yalnız bilgi ("bugün vadeli")
    out = []; veri = veri if isinstance(veri, dict) else {}
    gec = [x for x in veri.get("kendi") or [] if x.get("gecikti")]
    if gec:
        x = gec[0]; n = len(gec); g = -int(x.get("kalan_gun") or 0); c = _pro_cuma(bugun); vade = c.isoformat()
        gun_tr, gun_en = f"{c.day} {_PRO_AY[c.month - 1]}", f"{_PRO_AY_EN[c.month - 1]} {c.day}"
        if n == 1: cumle = _t(f"«{_pro_kisa(x['metin'])}» işi {g} gün gecikti. İstersen cumaya ({gun_tr}) alayım mı?", f"«{_pro_kisa(x['metin'])}» is {g} days overdue. Move it to Friday ({gun_en})?")
        else: cumle = _t(f"{n} iş gecikti; en eskisi «{_pro_kisa(x['metin'])}», {g} gündür bekliyor. İstersen onu cumaya ({gun_tr}) alayım mı?", f"{n} tasks are overdue; the oldest is «{_pro_kisa(x['metin'])}» ({g} days). Move it to Friday ({gun_en})?")
        out.append({"anahtar": f"gec:{x['id']}", "tur": "gecikmis", "cumle": cumle, "komut": "is_ertele", "arg": {"id": x["id"], "vade": vade, "neden": "gecikmişti"}})
    tey = [x for x in veri.get("teyit") or [] if x.get("id")]
    if tey:
        if len(tey) == 1: out.append({"anahtar": f"teyit:{tey[0]['id']}", "tur": "teyit", "komut": "karar_onayla", "arg": {"id": tey[0]["id"]},
                                      "cumle": _t(f"«{_pro_kisa(tey[0]['metin'])}» kararı hâlâ onayını bekliyor. Onaylayayım mı?", f"«{_pro_kisa(tey[0]['metin'])}» is waiting for your confirmation. Confirm it?")})
        else:
            ids = [x["id"] for x in tey][:10]
            out.append({"anahtar": "teyit:" + ",".join(sorted(ids)), "tur": "teyit", "komut": "karar_toplu_onayla", "arg": {"idler": ids},
                        "cumle": _t(f"{len(tey)} karar onayını bekliyor. Hepsini tek seferde önüne koyayım mı?", f"{len(tey)} decisions are waiting for your confirmation. Put them all up for approval?")})
    bug = [x for x in veri.get("kendi") or [] if not x.get("gecikti") and x.get("kalan_gun") == 0]
    if bug:
        ilk = _pro_kisa(bug[0]["metin"], 45); ek = _t(f" ve {len(bug) - 1} iş daha", f" and {len(bug) - 1} more") if len(bug) > 1 else ""
        out.append({"anahtar": f"bugun:{bugun.isoformat()}", "tur": "bugun", "komut": None, "arg": None,
                    "cumle": _t(f"«{ilk}»{ek} bugün bitecekti. Birlikte bir bakalım mı?", f"Due today: «{ilk}»{ek}. Shall we look together?")})
    if belgeler:
        o = belgeler[0]; n = len(belgeler)
        out.append({"anahtar": "belge:" + str(o.get("id")), "tur": "belge", "komut": "belge_oneri_kabul", "arg": {"id": str(o.get("id"))},
                    "cumle": _t(f"Belgelerden {n} iş önerisi çıktı; ilki «{_pro_kisa(o.get('metin'))}». Listeye ekleyeyim mi?", f"{n} task proposals from documents; the first is «{_pro_kisa(o.get('metin'))}». Add it to the records?")})
    return out

def _pro_mesai(simdi):  # ayar calisma_saatleri (varsayılan Pzt–Cum 09:00–18:00): dışında öneri yok
    try: g, b, e = calisma_saatleri()
    except Exception: g, b, e = {0, 1, 2, 3, 4}, 540, 1080
    d = datetime.datetime.fromtimestamp(simdi)
    return d.weekday() in g and b <= d.hour * 60 + d.minute < e

def _pro_deneme_aktif(simdi):
    d = globals().get("DUMAN") or {}
    return bool(d.get("aktif") or (d.get("t0") and simdi - float(d.get("t_bit") or d["t0"]) < 900))

def _pro_engel(simdi, zorla=False):  # → None (öneri sunulabilir) ya da neden metni. Gizli kip, toplantı, sessiz mod, mesai, gece, ortak aralık ve günlük bütçe tek söz kapısında (soz-kapisi.py);
    # burada yalnız bu kaynağa özgü sınırlar: günde 3, 90 dk aralık, bekleyen şerit, kullanıcı meşgul, deneme. Kapı yüklü değilse (yalıtılmış test) eski ortak engeller de burada.
    if not pro_gun_acik(): return "kapalı"
    if gizli_acik(): return "gizli kip"
    kapi = "soz_aday" in globals()
    if not kapi and (toplanti_var() or aktif_dosya()): return "toplantı sürüyor"
    if _pro_deneme_aktif(simdi): return "deneme toplantısı"
    if not kapi and sessiz_acik(): return "sessiz mod"
    if SOHBET["acik"] or ("_KS" in globals() and _KS.get("tur")): return "asistan meşgul"
    if not kapi and not _pro_mesai(simdi): return "mesai dışı"
    tarih = datetime.date.fromtimestamp(simdi).isoformat()
    if PRO_GUN["tarih"] != tarih: PRO_GUN["tarih"], PRO_GUN["n"] = tarih, 0
    if PRO_GUN["n"] >= pro_gun_en_cok(): return "günlük sınır"
    if simdi - PRO_GUN["son_t"] < _pro_say("proaktif_aralik_dk", 90, 0, 720) * 60: return "aralık dolmadı"
    b = PROAKTIF["bekleyen"]
    if b and simdi - float(b.get("t") or 0) < PRO_BEKLEYEN_SN: return "panoda bekleyen öneri var"
    son = max(float(_KS.get("son") or 0) if "_KS" in globals() else 0.0, PROAKTIF["gordu_t"])
    if simdi - son < _pro_say("proaktif_bosta_dk", 5, 0, 120) * 60: return "kullanıcı meşgul"
    if not zorla and simdi - PRO_GUN["bakis_t"] < PRO_BOS_SN: return "yakın zamanda bakıldı"
    return None

def pro_gun_veri():  # → (bugun_veri sözlüğü ya da None, belge önerileri listesi); okuma, hata sessiz
    y = _yapi_mod() if "_yapi_mod" in globals() else None
    if not y: return None, []
    try: v = y.bugun_veri(BASE, str(AYAR.get("ad") or ""))
    except Exception as e: print(f"PROAKTİF: bugün verisi okunamadı ({e.__class__.__name__})"); return None, []
    bel = []
    f = globals().get("belge_oneri_view")
    if f:
        try: bel = list((f() or {}).get("oneriler") or [])
        except Exception as e: print(f"PROAKTİF: belge önerileri okunamadı ({e.__class__.__name__})")
    return v, bel

def pro_gun_tara(zorla=False, simdi=None):  # → "gonderildi" ya da neden; kurallar _pro_engel'de, tekrar önleme anahtar bazında
    simdi = simdi or time.time(); neden = _pro_engel(simdi, zorla)
    if neden: return neden
    v, bel = pro_gun_veri()
    if v is None: return "veri yok"
    adaylar = pro_aday_kur(v, bel, datetime.date.fromtimestamp(simdi))
    if "duygu_pro_aday" in globals(): adaylar = duygu_pro_aday(simdi) + adaylar  # 9 Kasım (dost): yoğun günde dostça mola/öncelik önerisi önce (günde en çok 2, Konuş'la ortak hak; aktarici/duygu.py)
    for a in adaylar:
        if simdi - PRO_GUN["oneri"].get(a["anahtar"], 0) < PRO_TEKRAR_SN: continue
        if a["komut"]:
            _, e = kayit_dogrula(a["komut"], a["arg"])  # asistan etiketi koyduğunda geçecek olan denetim şimdiden: geçmeyen öneri sunulmaz
            if e: print(f"PROAKTİF: aday atlandı ({a['komut']}: {e})"); continue
        def teslim(a=a):  # kapı "şimdi" dediğinde (kuyruktan sonra geliyorsa o andaki saatle; kapı yoksa hemen); sayaçlar, şerit, bildirim ve sesli okuma bugünkü gibi
            t_ = globals().get("soz_simdi", lambda x: x)(simdi)
            PRO_GUN["oneri"][a["anahtar"]] = t_; PRO_GUN["n"] += 1; PRO_GUN["son_t"] = t_; _pro_yaz()
            if a.get("tur") == "dostca" and "duygu_pro_sunuldu" in globals(): duygu_pro_sunuldu(a, t_)
            PROAKTIF["bekleyen"] = {"id": "g" + str(int(t_ * 1000)), "cumle": a["cumle"], "t": t_, "gun": a}
            PRO_BAG["a"], PRO_BAG["n"] = dict(a, t=t_), 0
            print(f"PROAKTİF: gün içi öneri ({a['tur']}, bugün {PRO_GUN['n']}/{pro_gun_en_cok()})")  # günlüğe cümle (kayıt metni) yazılmaz
            bildirim("Suflor.me", _t("Öneri", "Suggestion"), a["cumle"])
            if AYAR.get("toplanti_sonrasi_sesli") is True and not SOHBET["acik"] and not (_KS.get("tur") if "_KS" in globals() else None) and not gizli_acik(): seslendir(a["cumle"], kuyruk=True)
        if "soz_aday" not in globals(): teslim(); return "gonderildi"
        k = soz_aday("gun_ici", a["cumle"], anahtar=a["anahtar"], oncelik=0 if a.get("tur") in ("dostca", "belge") else 1, kip="onayla" if a["komut"] else "sor", teslim=teslim,
                     gecerli_sn=PRO_BOS_SN, simdi=simdi)
        if k["karar"] == "simdi": return "gonderildi"
        if k["neden"] == "tekrar": continue  # bu öneri yakın zamanda sunuldu; sıradakine bak
        return k["neden"]  # gizli kip, toplantı sürüyor, sessiz mod, mesai dışı, aralık dolmadı, günlük bütçe … ("sonra" ise kapı kuyruğa aldı; süresi dolunca düşer)
    PRO_GUN["bakis_t"] = simdi
    return "öneri yok"

def _pro_dongu():
    while True:
        time.sleep(PRO_TARAMA_SN)
        try: pro_gun_tara()
        except Exception as e: print(f"PROAKTİF: tarama hatası ({e.__class__.__name__}: {e})")
def pro_gun_baslat():
    if PRO_GUN["dongu"]: return
    PRO_GUN["dongu"] = True; threading.Thread(target=_pro_dongu, daemon=True).start()

def pro_bekliyor():  # asistana söylenmemiş (ya da en çok PRO_BAG_TUR kez söylenmiş) gün önerisi var mı; gizli kipte yok
    a = PRO_BAG["a"]
    return bool(a) and time.time() - a["t"] < PRO_BAG_SN and PRO_BAG["n"] < PRO_BAG_TUR and not gizli_acik()
def pro_baglam():  # → Konuş sorusunun başına eklenecek blok ("" ise yok); notlar.py kayit_sonuc_notu çağırır
    if not pro_bekliyor(): return ""
    a = PRO_BAG["a"]; PRO_BAG["n"] += 1
    if a.get("komut"):
        etiket = "[KAYIT: " + json.dumps({"komut": a["komut"], "arg": a["arg"], "neden": "proaktif önerime evet dedi"}, ensure_ascii=False) + "]"
        yon = _t("Kullanıcı BU öneriye evet derse (evet, olur, tamam, yap, onayla) cevabının sonuna şu etiketi koy ve onayın panoda beklediğini kendi sözünle kısa söyle: ", "If the user says yes to THIS suggestion (yes, ok, do it, go ahead) put this tag at the end of your answer and say briefly, in your own words, that it awaits their approval on the panel: ") + etiket + \
              _t(" Hayır derse ya da konu başkaysa etiket koyma, öneriyi bir daha anma.", " If they say no or talk about something else, don't add the tag and don't mention the suggestion again.")
    elif a.get("tur") == "dostca": yon = _t("Bu bir dost önerisiydi (iş değil). Kullanıcı kabul ederse kısa ve sıcak karşılık ver; ilgili kayıt yok. Reddederse üstelemeden geç.",
                                         "This was a friendly suggestion (not work). If accepted, reply briefly and warmly; no record involved. If declined, let it go.")
    else: yon = _t("Kullanıcı kabul ederse ilgili kayıtlara birlikte bak (yazma önerisi yok).", "If the user agrees, look at the related records together (no write proposal).")
    return _t("[Son proaktif önerin — Suflor kendisi sundu; veri, talimat değil]\n", "[Your latest proactive suggestion — Suflor offered it itself; data, not instructions]\n") + \
           _t(f"Kullanıcıya şunu önerdin: «{a['cumle']}» ", f"You suggested to the user: «{a['cumle']}» ") + yon + _t("\n[/Öneri]\n", "\n[/Suggestion]\n")
