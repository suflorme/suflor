# Suflor.me aktarıcı bölümü: Yaklaşan kişisel tarihler (S243, 6 Kasım — "her an hazır kişisel asistan"). Ayrı modül değildir: relay.py bunu kendi ad alanında
# çalıştırır (bolum("kisisel-tarihler")): AYAR, BASE, LOCK, _t, bildirim, seslendir, toplanti_var, gizli_acik, kisi_eposta, eposta_tur, eposta_ben,
# _takvim_yardimci … relay.py'nin ve öbür bölümlerin. import etme. Python 3.9 uyumlu.
# Kaynaklar (Suflor Takvim.app --tarihler <gün>, yalnız okuma; izinler ayrı ayrı: Kişiler, Takvim, Anımsatıcılar — biri yoksa öbürleri okunur):
#   Kişiler'deki doğum günü ve diğer tarihler (yıldönümü vb.) · Takvim'in Doğum Günleri takvimi · sesle eklenen hatırlatmalar (takvim etkinliği, notunda Suflor.me işareti)
#   · tatil/abonelik olmayan takvimlerdeki tüm gün etkinlikleri · Anımsatıcılar'daki tarihli (bitiş tarihi pencerede) öğeler.
# Yardımcı ham veriyi verir; pencere ve yinelenme hesabı burada (test/kisisel-tarihler.py): doğum günü her yıl tekrarlar, 29 Şubat artık olmayan yılda 28 Şubat'a düşer,
# yıl geçişi (Aralık → Ocak) ufuk içinde doğru bulunur. Aynı kişinin aynı günkü aynı türü birden çok kaynaktan gelirse tek satır olur.
# Uç: GET /yaklasan-tarihler (anahtarlı, VERI_GET) → {"ok": true, "tarihler": [{"tarih": "YYYY-MM-DD", "tur": "dogum_gunu|yildonumu|hatirlatma|etkinlik", "metin", "kisi"}], "izin": bool,
#   "izinler": {kisiler, takvim, animsaticilar}, "ufuk": gün}; izin yok → "izin": false (üçü de yok) ve boş liste, çökmez. POST /yaklasan-tarihler {"islem": "taslak"|"yoksay", "tarih", "kisi"}:
#   yoksay → o kayıt bir daha listelenmez/hatırlatılmaz; taslak → doğum günü kutlama taslağı (e-posta ya da Teams sohbeti, ayar kutlama_kanali), GÖNDERİM YOK — kullanıcı gönderir.
# Hatırlatma: bir gün önce ve günün sabahı (ayar kisisel_tarih_saat, varsayılan 09:00) menü bildirimi; ayar kisisel_tarih_sesli: true ise ek olarak kısa sesli (yalnız toplantıda ve Konuş'ta değilken;
# gizli toplantıda hiçbiri). Bir tarih için aynı hatırlatma bir kez (kisisel-tarihler.json "bildirilen"). Ayarlar: kisisel_tarihler (açık), kisisel_tarih_ufuk (gün, 14), kisisel_tarih_hatirlat,
# kisisel_tarih_sesli, kisisel_tarih_saat, kutlama_kanali (eposta|teams).
import calendar as _cal
KT_DOSYA = "kisisel-tarihler.json"
KT_ONBELLEK_SN = 600
_KT = {"t": 0.0, "ham": None, "ufuk": 0, "yoksay": None, "bildirilen": None}
def _kt_fold(s):  # ad karşılaştırması: büyük-küçük harf, aksan ve Türkçe i/ı farkı yok
    import unicodedata
    s = str(s or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).split())
def kt_ufuk():
    try: return max(1, min(int(AYAR.get("kisisel_tarih_ufuk", 14)), 90))
    except (TypeError, ValueError): return 14
def kt_acik(): return AYAR.get("kisisel_tarihler") is not False
def _kt_gun(yil, ay, gun):  # 29 Şubat artık olmayan yılda 28 Şubat; geçersiz tarih None
    try:
        if ay == 2 and gun == 29 and not _cal.isleap(yil): gun = 28
        return datetime.date(yil, int(ay), int(gun))
    except (ValueError, TypeError): return None
def _kt_sonraki(ay, gun, bugun):  # bugünden (dahil) sonraki ilk yinelenme günü
    for y in (bugun.year, bugun.year + 1):
        d = _kt_gun(y, ay, gun)
        if d and d >= bugun: return d
    return None
def _kt_kisi_adi(baslik, adlar):  # doğum günü takvimi başlığı ("Ayşe'nin doğum günü", "Ayşe's Birthday") → bilinen kişi adı ya da başlıktan temizlenmiş ad
    f = _kt_fold(baslik)
    for a in sorted(adlar, key=len, reverse=True):
        if _kt_fold(a) and _kt_fold(a) in f: return a
    ad = re.sub(r"(?i)\s*[’'`´]?\s*(?:n[iıuü]n|[iıuü]n|n?[ae]n|s)?\s*(?:do[gğ]um\s+g[uü]n[uü]|birthday)\b.*$", "", str(baslik or "")).strip(" -—:")
    return ad or str(baslik or "").strip()
def _kt_kisi_etiketi(ad, yas, en):
    return (f"{ad} — birthday" + (f" (turns {yas})" if yas else "")) if en else (f"{ad} — doğum günü" + (f" ({yas}. yaş)" if yas else ""))
def kt_hesapla(ham, bugun, ufuk, yoksay=None):  # ham: yardımcı çıktısı → tekilleştirilmiş, tarihe göre sıralı liste
    en = str(AYAR.get("dil") or "") == "en"; son = bugun + datetime.timedelta(days=ufuk); out = {}; yoksay = set(yoksay or ())
    def ekle(d, tur, metin, kisi=""):
        if not d or d < bugun or d > son: return
        k = (d.isoformat(), tur, _kt_fold(kisi) or _kt_fold(metin))
        if k in out or "|".join(k) in yoksay: return
        out[k] = {"tarih": d.isoformat(), "tur": tur, "metin": str(metin)[:200], "kisi": str(kisi)[:80]}
    adlar = []
    for c in (ham or {}).get("kisiler") or []:
        if not isinstance(c, dict) or not str(c.get("ad") or "").strip(): continue
        ad = str(c["ad"]).strip(); adlar.append(ad); dg = c.get("dogum")
        if isinstance(dg, dict) and dg.get("ay") and dg.get("gun"):
            d = _kt_sonraki(int(dg["ay"]), int(dg["gun"]), bugun); yas = (d.year - int(dg["yil"])) if d and dg.get("yil") and int(dg["yil"]) > 1900 else 0
            ekle(d, "dogum_gunu", _kt_kisi_etiketi(ad, yas if 0 < yas < 130 else 0, en), ad)
        for t in c.get("tarihler") or []:
            if not isinstance(t, dict) or not t.get("ay") or not t.get("gun"): continue
            d = _kt_sonraki(int(t["ay"]), int(t["gun"]), bugun); et = str(t.get("etiket") or "").strip() or (_t("özel gün", "special date"))
            ekle(d, "yildonumu", f"{ad} — {et}", ad)
    for e in (ham or {}).get("dogum_takvimi") or []:  # Kişiler'deki aynı kişi zaten eklendiyse anahtar çakışır, ikinci satır düşer
        try: d = datetime.date.fromisoformat(str(e.get("tarih") or ""))
        except ValueError: continue
        ad = _kt_kisi_adi(e.get("baslik"), adlar); ekle(d, "dogum_gunu", _kt_kisi_etiketi(ad, 0, en), ad)
    for kay, tur in (("suflor", "hatirlatma"), ("animsaticilar", "hatirlatma"), ("etkinlikler", "etkinlik")):
        for e in (ham or {}).get(kay) or []:
            try: d = datetime.date.fromisoformat(str(e.get("tarih") or ""))
            except ValueError: continue
            b = str(e.get("baslik") or "").strip()
            if b: ekle(d, tur, b + (f" ({e['saat']})" if e.get("saat") else ""), "")
    # Suflor hatırlatması Anımsatıcılar'da da aynı başlıkla varsa saatli olan kalır: aynı gün + aynı başlık kökü tek satır
    sirali = sorted(out.values(), key=lambda x: (x["tarih"], {"dogum_gunu": 0, "yildonumu": 1, "hatirlatma": 2, "etkinlik": 3}[x["tur"]], x["metin"]))
    gor = {}
    for x in sirali:
        k = (x["tarih"], x["tur"], _kt_fold(re.sub(r"\s*\(\d\d:\d\d\)$", "", x["metin"])))
        if k not in gor or len(x["metin"]) > len(gor[k]["metin"]): gor[k] = x  # saatli olan kalır
    return sorted(gor.values(), key=lambda x: sirali.index(x))
def _kt_yol(): return os.path.join(BASE, KT_DOSYA)
def _kt_oku():
    if _KT["yoksay"] is not None: return
    try: v = json.load(open(_kt_yol(), encoding="utf-8")); assert isinstance(v, dict)
    except (OSError, ValueError, AssertionError): v = {}
    _KT["yoksay"] = set(str(x) for x in v.get("yoksay") or []); _KT["bildirilen"] = {str(k): str(x) for k, x in (v.get("bildirilen") or {}).items()}
def _kt_yaz():
    try:
        yol = _kt_yol(); fd = os.open(yol + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump({"yoksay": sorted(_KT["yoksay"])[-500:], "bildirilen": dict(sorted(_KT["bildirilen"].items())[-300:])}, f, ensure_ascii=False)
        os.replace(yol + ".tmp", yol)
    except OSError: pass
def _kt_anahtar(x): return "|".join((x["tarih"], x["tur"], _kt_fold(x.get("kisi")) or _kt_fold(x["metin"])))
def kt_ham(yenile=False):  # → yardımcı çıktısı (10 dk önbellek) ya da {"durum": …}
    ufuk = kt_ufuk()
    if not yenile and _KT["ham"] is not None and _KT["ufuk"] == ufuk and time.time() - _KT["t"] < KT_ONBELLEK_SN: return _KT["ham"]
    if os.environ.get("SUFLOR_TEST_BASLAT") and not os.environ.get("SUFLOR_TEST_TARIH"): return {"durum": "hata", "hata": "deneme kipi"}
    o = _takvim_yardimci(["--tarihler", str(ufuk)])
    if o.get("durum") == "ok": _KT.update(t=time.time(), ham=o, ufuk=ufuk)
    return o
def kt_liste(yenile=False, bugun=None):  # → (tarihler, durum sözlüğü)
    if not kt_acik(): return [], {"kapali": True}
    _kt_oku(); ham = kt_ham(yenile)
    if ham.get("durum") != "ok": return [], {"hata": str(ham.get("hata") or ham.get("durum"))[:160], "izin": False}
    iz = ham.get("izinler") or {}; izinler = {k: bool(iz.get(k)) for k in ("kisiler", "takvim", "animsaticilar")}
    return kt_hesapla(ham, bugun or datetime.date.today(), kt_ufuk(), _KT["yoksay"]), {"izinler": izinler, "izin": any(izinler.values())}
def kt_view(yenile=False, bugun=None):  # GET /yaklasan-tarihler
    try: liste, d = kt_liste(yenile, bugun)
    except Exception as e: return {"ok": False, "tarihler": [], "hata": e.__class__.__name__}
    if d.get("kapali"): return {"ok": True, "tarihler": [], "kapali": True, "ufuk": kt_ufuk()}
    if d.get("hata"): return {"ok": True, "tarihler": [], "izin": d.get("izin") if d.get("izin") is not None else False, "hata": d["hata"], "ufuk": kt_ufuk()}
    return {"ok": True, "tarihler": liste, "izin": d["izin"], "izinler": d["izinler"], "ufuk": kt_ufuk()}
# --- kutlama taslağı (gönderim yok) ----------------------------------------------------------------------------------------------------------------------
def kt_kutlama_metni(kisi, en=False):
    ilk = str(kisi or "").split()[0] if str(kisi or "").strip() else ""
    return (f"Happy birthday{', ' + ilk if ilk else ''}! Wishing you a wonderful year ahead." if en else f"Doğum günün kutlu olsun{' ' + ilk if ilk else ''}! Yeni yaşında sağlık, mutluluk ve başarı dolu bir yıl dilerim.")
def kt_taslak_url(kisi, kanal=None):  # → (url, adres ya da None, kanal)
    en = str(AYAR.get("dil") or "") == "en"; e = urllib.parse.quote; adres = kisi_eposta(kisi) if kisi else None
    govde = kt_kutlama_metni(kisi, en); konu = "Happy birthday" if en else "Doğum günün kutlu olsun"
    kanal = kanal or str(AYAR.get("kutlama_kanali") or "eposta")
    if kanal == "teams": return (f"https://teams.microsoft.com/l/chat/0/0?users={e(adres or '')}&message={e(govde)}", adres, "teams")
    tur = eposta_tur(); to = adres or ""
    ben = eposta_ben() or ""
    u = (f"https://outlook.office.com/mail/deeplink/compose?to={e(to)}&subject={e(konu)}&body={e(govde)}" if tur == "outlook" else
         f"https://mail.google.com/mail/u/{e(ben)}/?view=cm&fs=1&to={e(to)}&su={e(konu)}&body={e(govde)}" if tur == "gmail" else
         f"mailto:{e(to)}?subject={e(konu)}&body={e(govde)}")
    return (u, adres, "eposta")
def kt_islem(p):  # POST /yaklasan-tarihler
    _kt_oku(); i = p.get("islem"); tarih = str(p.get("tarih") or ""); kisi = str(p.get("kisi") or "")
    if i not in ("taslak", "yoksay") or not re.fullmatch(r"\d{4}-\d\d-\d\d", tarih): return {"ok": False, "err": "islem"}
    liste, d = kt_liste()
    x = next((y for y in liste if y["tarih"] == tarih and _kt_fold(y.get("kisi")) == _kt_fold(kisi) and (i == "yoksay" or y["tur"] == "dogum_gunu")), None)
    if i == "yoksay":
        if not x: return {"ok": False, "err": _t("kayıt yok", "no such item")}
        _KT["yoksay"].add(_kt_anahtar(x)); _kt_yaz(); return {"ok": True}
    if not x: return {"ok": False, "err": _t("doğum günü kaydı yok", "no birthday entry")}
    if gizli_acik(): return gizli_red() if "gizli_red" in globals() else {"ok": False, "err": "gizli"}
    if toplanti_var(): return {"ok": False, "err": "toplantida"}  # taslak tarayıcıda açılır; toplantıda açılmaz, bitince yine istenir
    u, adres, kanal = kt_taslak_url(kisi, p.get("kanal") if p.get("kanal") in ("eposta", "teams") else None)
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"KİŞİSEL TARİH (deneme): kutlama taslağı {kanal} · alıcı {'var' if adres else 'yok'}"); return {"ok": True, "kanal": kanal, "alici": bool(adres), "deneme": True}
    try: subprocess.Popen(["/usr/bin/open", u], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as ex: return {"ok": False, "err": ex.__class__.__name__}
    print(f"KİŞİSEL TARİH: kutlama taslağı açıldı ({kanal}, alıcı {'var' if adres else 'yok'})")  # günlüğe ad/adres yazılmaz
    return {"ok": True, "kanal": kanal, "alici": bool(adres), "sonuc": _t("Taslak açıldı (Gönder sende)", "Draft opened (you send it)")}
# --- hatırlatma: bir gün önce ve günün sabahı ------------------------------------------------------------------------------------------------------------
def _kt_saat():
    m = re.fullmatch(r"(\d{1,2}):(\d\d)", str(AYAR.get("kisisel_tarih_saat") or "09:00"))
    return (min(int(m.group(1)), 23), min(int(m.group(2)), 59)) if m else (9, 0)
def kt_hatirlat_bul(liste, simdi):  # → [(anahtar, cümle)]: yarın olanlar (bir gün önce) ve bugün olanlar (sabah); bildirilmiş olanlar atlanır. Yalnız doğum günü, yıldönümü, hatırlatma (etkinlik gürültü)
    en = str(AYAR.get("dil") or "") == "en"; bugun = simdi.date(); out = []
    if (simdi.hour, simdi.minute) < _kt_saat(): return out
    for x in liste:
        if x["tur"] == "etkinlik": continue
        fark = (datetime.date.fromisoformat(x["tarih"]) - bugun).days
        if fark not in (0, 1): continue
        k = _kt_anahtar(x) + "#" + ("yarin" if fark else "bugun")
        if k in (_KT["bildirilen"] or {}): continue
        on = (_t("Yarın: ", "Tomorrow: ") if fark else _t("Bugün: ", "Today: ")); out.append((k, on + x["metin"]))
    return out
def kt_hatirlat_tur(simdi=None):  # periyodik (30 dk); toplantıda/gizli kipte/kapalıyken yapmaz — o gün sonra yine denenir (bildirilmediği için kaybolmaz)
    if not kt_acik() or AYAR.get("kisisel_tarih_hatirlat") is False or gizli_acik() or toplanti_var(): return 0
    simdi = simdi or datetime.datetime.now(); _kt_oku()
    liste, d = kt_liste(bugun=simdi.date())
    n = 0
    for k, cumle in kt_hatirlat_bul(liste, simdi):
        _KT["bildirilen"][k] = simdi.date().isoformat(); _kt_yaz(); n += 1
        bildirim("Suflor.me", _t("Kişisel tarih", "Personal date"), cumle)
        if AYAR.get("kisisel_tarih_sesli") is True and not SOHBET["acik"] and not (_KS.get("tur") if "_KS" in globals() else None): seslendir(cumle, kuyruk=True)
    for k in [k for k, g in _KT["bildirilen"].items() if g < (simdi.date() - datetime.timedelta(days=3)).isoformat()]: _KT["bildirilen"].pop(k, None)
    return n
def _kt_dongu():
    time.sleep(90)
    while True:
        try: kt_hatirlat_tur()
        except Exception as e: print(f"KİŞİSEL TARİH: hata ({e.__class__.__name__})")
        time.sleep(1800)
# --- Konuş / asistan: tarih sorusuna veri ("bu hafta kimin doğum günü var", "yarın neyi unutmamalıyım") -------------------------------------------------
KT_SORU_RX = re.compile(r"do[gğ]um\s*g[uü]n|birthday|y[iı]l\s*d[oö]n[uü]m|unutmamal|unutma\b|hat[iı]rlat|anımsat|anims?at|yakla[sş]an\s+tarih|kutla|what.*(?:forget|remember)", re.I)
def kisisel_tarih_baglam(soru):  # Konuş [Bağlam]'ına: soru tarih/hatırlatma anıyorsa yaklaşan tarihler (en çok 20 satır); yoksa, kapalıysa, gizli toplantıda ""
    try:
        if not soru or not kt_acik() or gizli_acik() or not KT_SORU_RX.search(str(soru)): return ""
        liste, d = kt_liste()
        if d.get("hata") or d.get("izin") is False:
            return _t("Kişisel tarihler okunamadı (Kişiler/Takvim/Anımsatıcılar izni yok olabilir); kullanıcıya izin gerektiğini söyle.\n", "Personal dates could not be read (Contacts/Calendar/Reminders permission may be missing); tell the user.\n")
        gunler = _t(("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"), ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))
        satir = [f"- {x['tarih']} {gunler[datetime.date.fromisoformat(x['tarih']).weekday()]}: {x['metin']}" for x in liste[:20]]
        bas = _t(f"Yaklaşan kişisel tarihler (Mac Kişiler/Takvim/Anımsatıcılar; sonraki {kt_ufuk()} gün; bugün {datetime.date.today().isoformat()}):\n", f"Upcoming personal dates (Mac Contacts/Calendar/Reminders; next {kt_ufuk()} days; today {datetime.date.today().isoformat()}):\n")
        return bas + ("\n".join(satir) if satir else _t("- bu aralıkta kayıt yok", "- nothing in this range")) + "\n"
    except Exception as e:
        print(f"KİŞİSEL TARİH: bağlam eklenemedi ({e.__class__.__name__})"); return ""
# --- sesle "Ayşe'nin doğum gününü hatırlat" (aktarici/talimat.py talimat_yakala bunu önce dener): Kişiler'de TEK eşleşen kişinin sonraki doğum günü → var olan hatırlatma yolu
# (onay kartı/sesli onay → takvime saatinde uyaran etkinlik). Birden çok ya da hiç eşleşme/doğum günü yoksa None: soru Claude'a gider, o sorar. Pencere sınırı yok (6 ay sonrası da olur).
KT_HATIRLAT_RX = re.compile(r"^\W*(?:(?:claude|suflor|süflör)\W+)?(?P<k>[^\s,.:;?!]{2,30}(?:\s+[^\s,.:;?!]{2,30}){0,2}?)\s+do[gğ]um\s+g[uü]n[uü]\w*\s+(?:bana\s+)?(?:hat[iı]rlat|an[iı]msat)\w*", re.I)
KT_DURAK = {"bana", "şu", "su", "lütfen", "lutfen", "evet", "tamam", "peki", "hadi", "bir", "de", "da", "claude", "suflor", "süflör"}
def kt_dogum_coz(metin):  # → ad parçası ya da None
    r = KT_HATIRLAT_RX.match(str(metin or ""))
    if not r: return None
    j = [re.sub(r"(?i)[’'`´](?:n[iıuü]n|[iıuü]n|n?[ae])$|(?<=[a-zçğıöşü])(?:n[iıuü]n)$", "", t) for t in r.group("k").split() if _kt_fold(t) not in KT_DURAK]
    return " ".join(j).strip() or None
def kt_dogum_bul(ad, bugun=None, ham=None):  # → (tam ad, tarih ya da None) ; "yok" / "belirsiz" için (None, neden)
    bugun = bugun or datetime.date.today(); ham = ham if ham is not None else kt_ham()
    if ham.get("durum") != "ok": return (None, "okunamadi")
    tok = _kt_fold(ad).split()
    if not tok: return (None, "yok")
    es = []
    for c in ham.get("kisiler") or []:
        dg = c.get("dogum") if isinstance(c, dict) else None
        if not (isinstance(dg, dict) and dg.get("ay") and dg.get("gun")): continue
        ct = _kt_fold(c.get("ad")).split()
        if all(any(x == t or (len(t) >= 4 and x.startswith(t)) for x in ct) for t in tok): es.append((str(c["ad"]), dg))
    if len(es) != 1: return (None, "belirsiz" if es else "yok")
    d = _kt_sonraki(int(es[0][1]["ay"]), int(es[0][1]["gun"]), bugun)
    return (es[0][0], d) if d else (None, "yok")
def kt_sesli_hatirlat(metin, bugun=None, ham=None):  # → (ileti, zaman "YYYY-MM-DDTHH:MM") ya da None
    if not kt_acik(): return None
    ad = kt_dogum_coz(metin)
    if not ad: return None
    tam, d = kt_dogum_bul(ad, bugun, ham)
    if not tam or not d: return None
    s = _kt_saat(); en = str(AYAR.get("dil") or "") == "en"
    return ((f"{tam} — birthday" if en else f"{tam} — doğum günü"), f"{d.isoformat()}T{s[0]:02d}:{s[1]:02d}")
