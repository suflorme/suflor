# Suflor.me aktarıcı bölümü: Mac Anımsatıcılar eşitlemesi (S258, 9 Kasım — "kurulumda Mac Anımsatıcılar ile entegrasyon"). Ayrı modül değildir: relay.py bunu kendi ad alanında
# çalıştırır (bolum("animsatici")): AYAR, AYAR_PANO, BASE, STATE, _t, gizli_acik, _yapi_mod … relay.py'nin ve öbür bölümlerin. import etme. Python 3.9 uyumlu.
# Ne yapar: Kararlar ve işler'deki KULLANICININ KENDİ işleri (kayit_listesi: tur "is", kendi) seçilen Anımsatıcılar listesine (ayar animsatici_liste, varsayılan "Suflor.me";
#   yoksa yeni liste açılır) anımsatıcı olarak eklenir: başlık = iş metni, son tarih varsa bitiş tarihi, notta toplantı adı + Suflor kayıt kimliği işareti ("Suflor.me · kayıt <kayit_id>").
#   · Suflor'da iş bitince/iptal olunca anımsatıcı tamamlanır; iş yeniden açılırsa anımsatıcı da açılır; iş metni/tarihi Suflor'da değişirse anımsatıcıya yansır.
#   · Anımsatıcılar'da tamamlanan iş Suflor'da "yapildi" olur (olay günlüğüne kaynak "animsatici"; geri alınabilir). Tamamlanmış anımsatıcı yeniden açılırsa iş de açılır.
#   · Durum iki değerli olduğu için iki taraf da aynı turda değiştiyse aynı yöne gitmiştir (çakışma olmaz); metin/tarih ikisinde de değiştiyse Suflor'unki kazanır (anımsatıcı ezilir).
#   · Anımsatıcı silinirse Suflor işi SİLİNMEZ: eşleme düşer ve iş bir daha eklenmez ("yoksay"). Başka listedeki ya da bizim eklemediğimiz anımsatıcıya dokunulmaz.
# Eşleme kalıcı: canli/animsatici-es.json {"liste", "es": {kayit_id: {"id": calendarItemIdentifier, "tamam", "baslik", "vade"}}, "yoksay": [kayit_id]} (0600). İş metni orada tutulur (yerel dosya; dışarı gitmez).
# Yardımcı: Suflor Takvim.app --anim-esitle <istek.json> (EventKit; takvim.swift). Tur başına en çok iki çağrı: önce boş istek (listenin son durumu), fark varsa uygulayan ikinci çağrı.
# Zamanlama: 5 dk'da bir tam tur; kayıt veritabanı (karar-grafi.sqlite) değişince ~10 sn durulduktan sonra tur (iş değişince). Yalnız ayar animsatici: true iken; ayar kapalıyken yardımcı
# hiç çalışmaz. Gizli kip açıkken tur yok; gizli ve deneme toplantılarının işleri kayit_listesi'nde zaten yok (gitmez). Günlük: "ANIMSATICI: +n ~n ✓n" (eklenen, güncellenen, tamamlanan/bitirilen).
# Ayarlar: animsatici (bool; beta varsayılan kapalı, geliştirici kurulumunda sihirbaz sorar), animsatici_liste (liste adı, en çok 60 harf).
# Uçlar (relay.py; bu bölümdeki anim_view/anim_islem'i çağırır): GET /animsatici → durum; POST /animsatici {"islem": "simdi"|"listeler"}.
import subprocess
AYAR_PANO.setdefault("animsatici", ("bool", False, None)); AYAR_PANO.setdefault("animsatici_liste", ("metin", "Suflor.me", 60))
ANIM_DOSYA = "animsatici-es.json"
ANIM_TUR_SN, ANIM_DURUL_SN, ANIM_BAKIS_SN, ANIM_ILK_SN = 300, 10, 15, 45
if os.environ.get("SUFLOR_TEST_BASLAT") and os.environ.get("SUFLOR_ANIM_HIZLI"): ANIM_TUR_SN, ANIM_DURUL_SN, ANIM_BAKIS_SN, ANIM_ILK_SN = 4, 1, 1, 1  # yalnız deneme (test/animsatici.py)
ANIM_ISARET = "Suflor.me · kayıt "
ANIM = {"kilit": threading.Lock(), "son": None, "sonuc": None, "imza": None, "degisti_t": 0.0, "tur_t": 0.0, "hata": ""}
def anim_acik(): return AYAR.get("animsatici") is True
def anim_liste_adi(): return " ".join(str(AYAR.get("animsatici_liste") or "Suflor.me").split())[:60] or "Suflor.me"
def _anim_yol(): return os.path.join(BASE, ANIM_DOSYA)
def anim_oku():
    d = {"liste": "", "es": {}, "yoksay": []}
    try:
        with open(_anim_yol(), encoding="utf-8") as f: j = json.load(f)
        if isinstance(j, dict):
            d["liste"] = str(j.get("liste") or ""); d["es"] = {str(k): v for k, v in (j.get("es") or {}).items() if isinstance(v, dict) and v.get("id")}
            d["yoksay"] = [str(x) for x in (j.get("yoksay") or [])][-2000:]
    except (OSError, ValueError, AttributeError): pass
    return d
def anim_yaz(d):
    try:
        fd = os.open(_anim_yol() + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
        os.replace(_anim_yol() + ".tmp", _anim_yol())
    except OSError as e: print(f"ANIMSATICI: eşleme yazılamadı ({e.__class__.__name__})")
def anim_say():  # beta: yalnız sayı (eşlenen iş sayısı)
    try: return len(anim_oku()["es"])
    except Exception: return 0
def _anim_yardimci(args, istek=None):  # Suflor Takvim.app → çıktı sözlüğü ya da {"durum": "hata", …}. Deneme: SUFLOR_TEST_BASLAT + SUFLOR_ANIM_YARDIMCI=<betik> (sahte yardımcı)
    sahte = os.environ.get("SUFLOR_ANIM_YARDIMCI") if os.environ.get("SUFLOR_TEST_BASLAT") else None
    app = os.path.join(AYAR["uygulama"], "Suflor Takvim.app")
    if not sahte and not os.path.isdir(app): return {"durum": "hata", "hata": "Suflor Takvim.app yok"}
    yol = os.path.join(BASE, "animsatici-istek.json"); cikti = os.path.join(BASE, "animsatici-cikti.json")
    try:
        if os.path.exists(cikti): os.remove(cikti)
        if istek is not None:
            fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(istek, f, ensure_ascii=False)
            args = args + [yol]
        if sahte: subprocess.run([sys.executable, sahte] + args + ["--cikti", cikti], capture_output=True, timeout=60)
        else: subprocess.run(["open", "-g", "-W", "-n", "-a", app, "--args"] + args + ["--cikti", cikti], capture_output=True, timeout=200)
        with open(cikti, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e: return {"durum": "hata", "hata": e.__class__.__name__}
    finally:
        for f in (yol, cikti):
            try: os.remove(f)
            except OSError: pass
def anim_listeler():  # → {"durum": "ok", "listeler": [{ad, hesap, yazilabilir}]} | {"durum": "izin_yok"|"hata", …}
    return _anim_yardimci(["--anim-listeler"])

def _anim_not(x):
    top = " ".join(str(x.get("baslik") or "").split())[:80]; gun = str(x.get("tarih") or "")[:10]
    kim = " · ".join(p for p in (top, gun) if p)
    return (kim + "\n" if kim else "") + ANIM_ISARET + str(x.get("kayit_id") or "")
def _anim_vade(x):
    v = str(x.get("vade") or "").strip()
    return v[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v[:10]) else ""  # serbest metin ("cuma") anımsatıcıya tarih olarak gitmez
def _anim_baslik(x): return " ".join(str(x.get("metin") or "").split())[:300]
def anim_planla(isler, durum, ogeler):
    # Saf karar işlevi (test/animsatici.py). isler: kayit_listesi'nin kullanıcıya ait iş satırları; durum: anim_oku(); ogeler: yardımcının listedeki öğeleri (id → öğe).
    # → {"ekle": [...], "guncelle": [...], "tamamla": [{id, tamam}], "sil": [], "suflor": [(kayit_id, "yapildi"|"acik")], "dus": [kayit_id], "es": yeni eşleme}
    p = {"ekle": [], "guncelle": [], "tamamla": [], "sil": [], "suflor": [], "dus": []}; es = {k: dict(v) for k, v in durum["es"].items()}; yoksay = set(durum["yoksay"])
    for x in isler:
        kid = x.get("kayit_id") or ""
        if not kid or kid in yoksay: continue
        kapali = x.get("durum") == "kapandi"; e = es.get(kid)
        if not e:
            if not kapali: p["ekle"].append({"kayit_id": kid, "baslik": _anim_baslik(x), "vade": _anim_vade(x), "not": _anim_not(x)})  # biten işi yeni eklemeyiz
            continue
        o = ogeler.get(e["id"])
        if o is None: p["dus"].append(kid); es.pop(kid, None); continue  # anımsatıcı silinmiş: iş silinmez, bir daha eklenmez
        onceki = bool(e.get("tamam")); r_tamam = bool(o.get("tamam"))
        s_degisti = kapali != onceki; r_degisti = r_tamam != onceki
        if s_degisti and not r_degisti:
            p["tamamla"].append({"id": e["id"], "tamam": kapali}); e["tamam"] = kapali
        elif r_degisti and not s_degisti:
            p["suflor"].append((kid, "yapildi" if r_tamam else "acik")); e["tamam"] = r_tamam
        else: e["tamam"] = kapali  # ya değişen yok ya ikisi de aynı yöne gitti
        b, v = _anim_baslik(x), _anim_vade(x)
        if (b != e.get("baslik") or v != e.get("vade")) and not kapali:  # Suflor'da metin/tarih değişti: anımsatıcıya yansır (anımsatıcıda elle değişen alan eşleme anında Suflor değeriyle ezilir)
            g = {"id": e["id"], "baslik": b, "vade": v}; p["guncelle"].append(g); e["baslik"], e["vade"] = b, v
    p["es"] = es
    return p

def anim_tur(zorla=False):
    # Bir eşitleme turu → {"ok", "ekle", "guncelle", "tamamla", "suflor"} ya da {"ok": False, "neden"}. Tek seferde bir tur (kilit).
    if not anim_acik() and not zorla: return {"ok": False, "neden": "kapali"}
    if gizli_acik(): return {"ok": False, "neden": "gizli"}
    if not ANIM["kilit"].acquire(blocking=False): return {"ok": False, "neden": "mesgul"}
    try:
        ANIM["tur_t"] = time.time(); y = _yapi_mod()
        if not y: return {"ok": False, "neden": "yapi_yok"}
        liste = anim_liste_adi(); d = anim_oku()
        if d["liste"] and d["liste"] != liste: d = {"liste": liste, "es": {}, "yoksay": d["yoksay"]}  # liste değişti: eski listeye dokunulmaz, yeni listeye baştan
        d["liste"] = liste
        v = y.kayit_listesi(BASE, str(AYAR.get("ad") or ""))
        isler = [x for x in (v.get("kayitlar") or []) if x.get("tur") == "is" and x.get("kendi") and x.get("kayit_id") and not x.get("deneme")]
        o = _anim_yardimci(["--anim-esitle"], {"liste": liste, "olustur": True})
        if o.get("durum") != "ok":
            ANIM["hata"] = str(o.get("durum") or "hata") + (": " + str(o.get("hata"))[:80] if o.get("hata") else ""); ANIM["sonuc"] = {"ok": False, "neden": o.get("durum") or "hata"}
            if o.get("durum") != "izin_yok" or time.time() - ANIM.get("izin_log_t", 0) > 3600: print(f"ANIMSATICI: yardımcı yanıt vermedi ({ANIM['hata']})"); ANIM["izin_log_t"] = time.time()
            return ANIM["sonuc"]
        ANIM["hata"] = ""; ogeler = {str(g.get("id")): g for g in (o.get("ogeler") or []) if isinstance(g, dict) and g.get("id")}
        p = anim_planla(isler, d, ogeler); es = p["es"]; eklenen = 0; guncel = len(p["guncelle"]); bitti = 0; hata = 0
        if p["ekle"] or p["guncelle"] or p["tamamla"] or p["sil"]:
            o2 = _anim_yardimci(["--anim-esitle"], {"liste": liste, "olustur": True, "ekle": p["ekle"], "guncelle": p["guncelle"], "tamamla": p["tamamla"], "sil": p["sil"]})
            if o2.get("durum") != "ok": print(f"ANIMSATICI: yazma yapılamadı ({str(o2.get('durum'))})"); return {"ok": False, "neden": o2.get("durum") or "hata"}
            hata = int(o2.get("hata_say") or 0); ek = {str(g.get("kayit_id")): str(g.get("id")) for g in (o2.get("eklenen") or []) if g.get("id")}
            for a in p["ekle"]:
                i = ek.get(a["kayit_id"])
                if i: es[a["kayit_id"]] = {"id": i, "tamam": False, "baslik": a["baslik"], "vade": a["vade"]}; eklenen += 1
            bitti += len(p["tamamla"])
        for kid, dur in p["suflor"]:  # anımsatıcıdan gelen: Suflor'da iş durumu (olay günlüğü kaynak "animsatici")
            try:
                r = y.kayit_durum(BASE, kid, dur, kaynak="animsatici")
                if r and r[0]: bitti += 1
            except Exception as e: print(f"ANIMSATICI: iş durumu yazılamadı ({e.__class__.__name__})"); hata += 1
        d["es"] = es; d["yoksay"] = (d["yoksay"] + p["dus"])[-2000:]; anim_yaz(d)
        ANIM["son"] = time.time()
        if eklenen or guncel or bitti or p["dus"] or hata: print(f"ANIMSATICI: +{eklenen} ~{guncel} ✓{bitti}" + (f" · eşleme düştü {len(p['dus'])}" if p["dus"] else "") + (f" · hata {hata}" if hata else ""))
        ANIM["sonuc"] = {"ok": True, "ekle": eklenen, "guncelle": guncel, "tamamla": bitti, "suflor": len(p["suflor"]), "dus": len(p["dus"])}
        return ANIM["sonuc"]
    except Exception as e:
        print(f"ANIMSATICI: hata ({e.__class__.__name__})"); return {"ok": False, "neden": "hata"}
    finally:
        ANIM["imza"] = _anim_imza(); ANIM["kilit"].release()  # başarısız tur da imzayı ilerletir: yardımcı her 15 sn'de yeniden açılmasın (yeni deneme 5 dk sonra)

def _anim_imza():  # kayıt veritabanının (ve WAL'ının) boyut + değişme zamanı: iş değişti mi
    s = []
    for ek in ("", "-wal"):
        try: st = os.stat(os.path.join(BASE, "karar-grafi.sqlite" + ek)); s.append((st.st_mtime_ns, st.st_size))
        except OSError: s.append(None)
    return tuple(s)
def anim_view():  # /status animsatici ve GET /animsatici: yalnız durum ve sayı (iş metni yok)
    return {"acik": anim_acik(), "liste": anim_liste_adi(), "es": anim_say(), "son_s": round(time.time() - ANIM["son"]) if ANIM["son"] else None, "hata": ANIM["hata"] or None}
def anim_islem(p):  # POST /animsatici {"islem": "simdi"|"listeler"} (anahtarlı)
    i = str((p or {}).get("islem") or "")
    if i == "simdi": return dict(anim_tur(zorla=False), islem="simdi")
    if i == "listeler": return anim_listeler()
    return {"ok": False, "err": "islem"}
def _anim_dongu():
    time.sleep(ANIM_ILK_SN)
    while True:
        try:
            if anim_acik() and not gizli_acik():
                imza = _anim_imza(); simdi = time.time()
                if imza != ANIM["imza"]:  # iş değişti: ~10 sn durulunca tur (art arda değişiklikler tek tura iner)
                    if imza != ANIM.get("gozlenen"): ANIM["gozlenen"] = imza; ANIM["degisti_t"] = simdi
                    elif simdi - ANIM["degisti_t"] >= ANIM_DURUL_SN: anim_tur()
                elif simdi - ANIM["tur_t"] >= ANIM_TUR_SN: anim_tur()
        except Exception as e: print(f"ANIMSATICI: döngü hatası ({e.__class__.__name__})")
        time.sleep(ANIM_BAKIS_SN)
if not os.environ.get("SUFLOR_ANIM_DONGU_YOK"): threading.Thread(target=_anim_dongu, daemon=True).start()
