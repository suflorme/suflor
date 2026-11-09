# Suflor.me aktarıcı bölümü: Eylem menüsü (ortak karar katmanı, yerel). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("eylem-menu")): AYAR, BASE, TAKVIM_TAM,
# _yapi_mod, kimlik_coz (kimlik.py), BEYIN, claude_yolu, BRIFING_APP, beyin_tek, claude_json, claude_yalin (brifing-ses.py) relay.py'nindir. Mantık yapi.py'de (eylem_menu, kayit_eylem; testte sahte
# bağımlılıkla), burada yalnız aktarıcıya bağlayan ince katman:
#   GET  /kayit-menu?id=<k12|s7|q3>   (anahtarlı, VERI_GET)  → menü bilgisi: eylemler, tarihçe, Geri al, gündem adayları, sahibin e-postası
#   POST /kayit-eylem {"id", "eylem", …} (anahtarlı; geçiş listesinde yok) → eylem tam bir olay yazar; taslak eylemleri bağlantı döner, GÖNDERMEZ
# Claude'a çalıştır: yalnız kaydın metni ve tarihçesi gider (yapi.claude_istemi); sağlayıcı ayar beyin.prova'yı paylaşır (tek çağrı; Claude Code Brifing.app'ten, telaffuz/prova gibi); sonuç kayda yorum olarak bağlanır.
# Gizli toplantı kaydında çalışmaz (yapi.kayit_eylem denetler). Dışarı hiçbir şey gönderilmez.
EYLEM_ZAMAN_SN = 120
def _kem_takvim(): return [e for e in TAKVIM_TAM.values() if isinstance(e, dict)]
def _kem_kimlik(ad, tam=True):  # kimlik.py: takvim, kayıt veritabanı, Kişiler (tam) → {"eposta", "kaynak", "guven", "adaylar"}; menü açılışında Kişiler'e gidilmez
    if "kimlik_coz" not in globals(): return {}
    return kimlik_coz(ad) if tam else kimlik_coz(ad, kisiler=False, yaz=False)
def eylem_model(istem, amac=None, soru=None, maske=None):
    # amac verilirse (talimat | kayit | degerlendir) istemin başına kişi modelinin paketi (profil + öğrenilenler …; aktarici/kisi-modeli.py baglam_paketi) eklenir; gizlilik süzgeci pakette.
    # → (ham metin, hata metni ya da None). Tek model çağrısı (prova_model gibi): başka sağlayıcıysa beyin_tek, Claude Code ise Brifing.app --istek (Masaüstü izni uygulamada).
    try:
        if amac and "baglam_paketi" in globals():
            paket = baglam_paketi(amac, soru=soru)
            if paket and maske: paket = maske(paket)  # çağıranın kendi gizlilik maskesi (ör. e-posta değerlendirmesinde adres maskesi)
            if paket: istem = paket + "\n" + istem
        sec = BEYIN.secim(AYAR, "prova"); claude_var = bool(claude_yolu()) and os.path.isdir(BRIFING_APP); ham = None
        if sec["tur"] != "claude-code":
            ham, olc = beyin_tek("prova", sec, istem, json_kip=False, sistem=None, zaman=EYLEM_ZAMAN_SN)
            if olc and not olc.get("hata"): return ham, None
            if not (claude_var and BEYIN.yedek_var(AYAR, sec)): return None, "yanıt gelmedi"
            print(BEYIN.yedek_satiri("prova", sec, ham if olc else "çıktı okunamadı"))
        if not claude_var: return None, "Claude Code yok"
        d = os.path.join(BASE, "eylem"); os.makedirs(d, exist_ok=True)
        cikti = os.path.join(d, "cikti.json"); istek = os.path.join(d, "istek.json"); t0 = time.time()
        if os.path.exists(cikti): os.remove(cikti)
        model = BEYIN.claude_secim(AYAR, "prova")["model"]
        fd = os.open(istek, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump({"claude": claude_yolu(), "args": BEYIN.prova_args(AYAR, istem, model), "cwd": d, "cikti": cikti, "sure": EYLEM_ZAMAN_SN}, f, ensure_ascii=False)
        try: subprocess.run(["open", "-g", "-W", "-n", "-a", BRIFING_APP, "--args", "--istek", istek], capture_output=True, timeout=EYLEM_ZAMAN_SN + 30)
        except (OSError, subprocess.TimeoutExpired): pass
        try: os.remove(istek)
        except OSError: pass
        try: ham = open(cikti, encoding="utf-8").read(); os.remove(cikti)
        except OSError: return None, "Claude yanıt vermedi"
        metin, _ = claude_json(ham, "eylem", t0, bool(claude_yalin()), "claude-code", model)
        return metin, None
    except Exception as e: return None, e.__class__.__name__
def _kem_id(yol):
    import urllib.parse; m = re.search(r"[?&]id=([^&]{1,40})(?:&|$)", str(yol)); return urllib.parse.unquote_plus(m.group(1)) if m else ""
def kayit_menu_view(tam_yol):  # GET /kayit-menu?id=
    y = _yapi_mod(); kid = _kem_id(tam_yol)
    if not y or not kid: return {"ok": False, "err": "kayıt yok"}
    try: return _at_menuye_ekle(y, kid, y.eylem_menu(BASE, kid, _kem_takvim(), lambda ad: _kem_kimlik(ad, False)))
    except Exception as e: print(f"EYLEM MENÜSÜ: okunamadı ({e.__class__.__name__})"); return {"ok": False, "err": e.__class__.__name__}
def kayit_eylem_islem(p):  # POST /kayit-eylem
    y = _yapi_mod(); p = p if isinstance(p, dict) else {}; kid = str(p.get("id") or "")[:40]; e = str(p.get("eylem") or "")[:20]
    if not y or not kid or not e: return {"ok": False, "err": "id ve eylem gerekli"}
    if e == "toplanti": return _at_islem(y, kid, p)
    try: r = y.kayit_eylem(BASE, kid, e, p, None, lambda ad: _kem_kimlik(ad, True), _kem_takvim(), lambda i: eylem_model(i, amac="kayit"))
    except Exception as ex: print(f"EYLEM MENÜSÜ: {e} yapılamadı ({ex.__class__.__name__})"); return {"ok": False, "err": ex.__class__.__name__}
    print(f"EYLEM MENÜSÜ: {e} {kid} → " + ("tamam" if r.get("ok") else str(r.get("err"))))  # günlüğe metin yazılmaz
    return r
# --- Acil toplantı (6 Kasım): kaydın ilgili kişileriyle hemen bir toplantı kurma ekranını açar (Teams planlama, Google Takvim şablonu ya da Zoom). Davet GİTMEZ: açılan ekranda gönderen kullanıcıdır.
#   Menü cevabına "toplanti" eylemi + {"platformlar", "davetli": [{ad, eposta}], "eposta_yok": [ad]} eklenir (yapi.py'ye dokunmadan); POST /kayit-eylem {"id", "eylem": "toplanti", "platform"} → {"toplanti": {"url", "kopyala"?, …}}.
#   Platformlar ayar `toplanti_platformlari` (varsayılan teams, meet, zoom; ilki varsayılan). Zoom için isteğe bağlı `zoom_baglanti` (https kişisel toplantı bağlantısı).
#   Bağlantı biçimleri (ağa istek atılmaz; belgelenmiş derin bağlantılar):
#     teams: https://teams.microsoft.com/l/meeting/new?subject&attendees&startTime&endTime&content — Teams'in toplantı PLANLAMA ekranı; davetli, saat aralığı ve gündem birlikte gelir. (msteams:/l/call yalnız anlık arama açar, gündem taşımaz.)
#     meet:  https://calendar.google.com/calendar/render?action=TEMPLATE&text&dates&add&details — Google Takvim şablonu; Meet bağlantısını takvim kendisi ekler (meet.google.com/new davetli taşımaz).
#     zoom:  zoom_baglanti varsa aynı Takvim şablonu (bağlantı yer ve gündem notunda); yoksa https://zoom.us/start açılır ve davet metni (konu, davetliler, gündem) panoya kopyalanır.
#   Olay: toplanti_onerildi (yapi.OLAY_TURLERI'nde varsa; yoksa taslak_hazirlandi, tur "toplanti"); yalnız platform ve sayılar yazılır, adres yazılmaz. Geri alınmaz. Gizli toplantı kaydında yok.
TOPLANTI_PLATFORM = ("teams", "meet", "zoom"); TOPLANTI_SURE_DK = 30
def _at_platformlar():
    l = AYAR.get("toplanti_platformlari"); l = l if isinstance(l, list) else []
    out = [p for p in dict.fromkeys(str(a).strip().lower() for a in l) if p in TOPLANTI_PLATFORM]
    return out or list(TOPLANTI_PLATFORM)
def _at_zoom():
    u = str(AYAR.get("zoom_baglanti") or "").strip()
    return u if re.match(r"^https://[^\s]{4,300}$", u) else ""
def _at_davetliler(y, x, kimlik_f):
    # kaydın ilgili kişileri (iş: sahip; karar: isteyen, onaylayan; soru: sahip, isteyen) — kullanıcının kendisi hariç. → ([{ad, eposta}], [e-postası bilinmeyen adlar])
    roller = x.get("roller") or {}; anahtar = ("isteyen", "onaylayan") if x.get("tur") == "karar" else ("sahip", "isteyen") if x.get("tur") == "soru" else ("sahip",)
    try: bl = y.bilinen_adlar(BASE)
    except Exception: bl = []
    var, eposta_yok, goren = [], [], set()
    for k in anahtar:
        r = roller.get(k)
        if not r or not (r.get("ad") or r.get("eposta")): continue
        ad = " ".join(str(r.get("ad") or "").split()); ep = str(r.get("eposta") or "").strip().lower()
        if not ep and ad and kimlik_f:
            try: ep = str((kimlik_f(ad) or {}).get("eposta") or "").strip().lower()
            except Exception: ep = ""
        if "@" not in ep: ep = ""
        if r.get("ben") or y.kendi_mi(ad, ep, bl): continue
        an = ep or ad.lower()
        if an in goren: continue
        goren.add(an)
        if ep: var.append({"ad": ad, "eposta": ep})
        else: eposta_yok.append(ad or "?")
    return var, eposta_yok
def _at_kullanilir(x): return bool(x) and (x.get("durum") == "acik" or x.get("tur") == "karar")
def _at_menuye_ekle(y, kid, m):
    if not isinstance(m, dict) or not m.get("ok"): return m
    x = y.ortak_kayit(BASE, kid)
    if not _at_kullanilir(x): return m
    var, yok = _at_davetliler(y, x, lambda ad: _kem_kimlik(ad, False))
    el = list(m.get("eylemler") or []); i = el.index("claude") if "claude" in el else len(el); el.insert(i, "toplanti")
    return dict(m, eylemler=el, toplanti={"platformlar": _at_platformlar(), "davetli": var, "eposta_yok": yok, "zoom_baglanti": bool(_at_zoom())})
def toplanti_hazirla(x, platform, davetli, simdi=None, en=False, zoom_baglanti=""):
    # saf işlev: kayıt + platform + davetliler → {"url", "kopyala"?, "konu", "gundem", "baslangic", "bitis"}; ağa dokunmaz
    import urllib.parse; Q = lambda t: urllib.parse.quote(str(t), safe="")
    simdi = (simdi or datetime.datetime.now().astimezone()).replace(second=0, microsecond=0); bit = simdi + datetime.timedelta(minutes=TOPLANTI_SURE_DK)
    metin = str(x.get("metin") or "")
    metin = re.sub(r"\s*\(teyit bekliyor(?:\s*[—-]\s*.*)?\)\s*$", "", metin).strip()
    es = [str(d.get("eposta") or "").strip().lower() for d in davetli if "@" in str(d.get("eposta") or "")][:10]
    konu = (("Urgent: " if en else "Acil: ") + metin[:70]).strip()[:120]
    top = str(x.get("baslik") or "").strip(); gun = x.get("tarih") or ""
    try: gun = _at_tarih(gun, en)
    except Exception: pass
    yer = f"{top} ({gun})" if top and gun else top or gun
    gundem = (("Agenda: " if en else "Gündem: ") + metin[:500]) + (("\n" + (f"Source: {yer}" if en else f"Kaynak: {yer} toplantısı")) if yer else "")
    out = {"konu": konu, "gundem": gundem, "baslangic": simdi.isoformat(timespec="seconds"), "bitis": bit.isoformat(timespec="seconds")}
    if platform == "teams":
        out["url"] = ("https://teams.microsoft.com/l/meeting/new?subject=" + Q(konu) + "&attendees=" + ",".join(Q(e) for e in es) + "&startTime=" + Q(out["baslangic"]) + "&endTime=" + Q(out["bitis"]) + "&content=" + Q(gundem))
        return out
    utc = lambda t: t.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if platform == "zoom" and not zoom_baglanti:
        out["url"] = "https://zoom.us/start"
        out["kopyala"] = "\n".join([konu, ("Attendees: " if en else "Davetliler: ") + ", ".join(es), gundem])
        return out
    det = gundem + (("\nZoom: " + zoom_baglanti) if platform == "zoom" else "")
    out["url"] = ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + Q(konu) + "&dates=" + utc(simdi) + "/" + utc(bit) + "&add=" + ",".join(Q(e) for e in es) + "&details=" + Q(det)
                  + (("&location=" + Q(zoom_baglanti)) if platform == "zoom" else ""))
    return out
def _at_tarih(t, en):
    y = _yapi_mod(); return y.tarih_okunur(t, en) if y else t
def _at_islem(y, kid, p):
    x = y.ortak_kayit(BASE, kid)
    if not x: return {"ok": False, "err": "kayıt yok"}
    if x.get("gizli") or (x.get("toplanti") and y.gizli_mi(BASE, x["toplanti"])): return {"ok": False, "err": "gizli", "eylem": "toplanti"}
    if not _at_kullanilir(x): return {"ok": False, "err": "bu kayıt için toplanti yok", "eylem": "toplanti"}
    pl = _at_platformlar(); platform = str(p.get("platform") or pl[0]).lower()
    if platform not in pl: return {"ok": False, "err": "platform yok", "eylem": "toplanti"}
    var, yok = _at_davetliler(y, x, lambda ad: _kem_kimlik(ad, True)); en = str(AYAR.get("dil") or "") == "en"
    t = toplanti_hazirla(x, platform, var, en=en, zoom_baglanti=_at_zoom())
    veri = {"platform": platform, "davetli": len(var), "eposta_yok": len(yok)}
    tur = "toplanti_onerildi" if "toplanti_onerildi" in getattr(y, "OLAY_TURLERI", ()) else "taslak_hazirlandi"
    o, _ = y._degistir(BASE, kid, tur, lambda _x: dict(veri, tur="toplanti") if tur == "taslak_hazirlandi" else veri, None, "eylem")
    print(f"EYLEM MENÜSÜ: toplanti {kid} → {platform}, davetli {len(var)}, e-postasız {len(yok)}")  # günlüğe ad/adres yazılmaz
    return {"ok": True, "eylem": "toplanti", "olay": o["olay_id"] if o else None, "kayit": y._kayit_kisa(y.ortak_kayit(BASE, kid)),
            "toplanti": dict(t, platform=platform, davetli=len(var), eposta_yok=yok)}
# --- Belgeden atama (7 Kasım): proje kartı + toplantıya eklenen belgelerden iş önerisi (yapi.belge_onerileri; seçim ve yazma orada, test/belgeden-atama.py) -------------------------
#   GET  /belge-oneri (anahtarlı, VERI_GET) → {"oneriler", "say"} — Kararlar ve işler sayfasında İşler sekmesinin üstünde
#   POST /belge-oneri {"id", "islem": "kabul"|"reddet", "sahip"?} (anahtarlı) → kabul: kayit_olustu + (sahip varsa) is_atandi; sahibin e-postası kimlik modülünden. Reddedilen bir daha önerilmez.
# Kayıt veritabanı (ayar veritabani.gorevler; yalnız okuma) önerilerin ilk kaynağı. Belgeler: canli/baglam.json + son BELGE_ARSIV_GUN gündeki baglam-arsiv.jsonl dosya kaynakları (bağlantılar değil); gizli toplantının belgesi yapi'de düşer.
BELGE_ARSIV_GUN = 14
def _bo_belgeler():
    out, gor = [], set(); sinir = datetime.datetime.now() - datetime.timedelta(days=BELGE_ARSIV_GUN)
    try: ks = list((json.load(open(os.path.join(BASE, "baglam.json"), encoding="utf-8")) or {}).get("kaynaklar") or [])
    except (OSError, ValueError): ks = []
    try:
        for l in open(os.path.join(BASE, "baglam-arsiv.jsonl"), encoding="utf-8"):
            try: k = json.loads(l)
            except ValueError: continue
            try:
                if isinstance(k, dict) and datetime.datetime.fromisoformat(str(k.get("at") or "")[:19]) >= sinir: ks.append(k)
            except ValueError: pass
    except OSError: pass
    for k in ks:
        if not isinstance(k, dict) or k.get("tur") != "dosya" or k.get("deger") in gor: continue
        gor.add(k.get("deger")); out.append({"ad": k.get("ad") or os.path.basename(str(k.get("deger"))), "yol": k.get("deger"), "toplanti": k.get("file") or ""})
    return out[-20:]
def _bo_kart():
    try: return json.load(open(os.path.join(AYAR["uygulama"], "proje-karti.json"), encoding="utf-8"))
    except (OSError, ValueError): return None
def _bo_vt():  # kayıt veritabanının açık işleri (ayar baglayici.kayit.sorgular.gorevler ya da eski veritabani.gorevler), en çok 500 satır: [iş metni, sahip, vade, konum].
    # A1: aktarıcı Masaüstü'ndeki veritabanını hiç açmaz; veritabanı yardımcısının (vt-izle) yazdığı canli/vt-gorevler.json önbelleği (OnbellekOkuyucu) okunur.
    b = _baglayici_mod()
    if not b: return None
    c = b.ayar_coz(AYAR).get("kayit") or {}
    if not c.get("yol") or not str((c.get("sorgular") or {}).get("gorevler") or "").strip(): return None
    try: return [b.is_satiri(i) for i in b.onbellek_okuyucu(BASE, globals().get("VT_BELLEK")).acik_isler()[:500]]
    except b.YetenekYok:
        if _BO_VT_UYARI.get("e") != "YetenekYok": _BO_VT_UYARI["e"] = "YetenekYok"; print("BELGEDEN ATAMA: görev önbelleği (vt-gorevler.json) yok — veritabanı yardımcısı henüz yazmadı")
        return None
_BO_VT_UYARI = {}
def belge_oneri_view():
    y = _yapi_mod()
    if not y or not hasattr(y, "belge_onerileri"): return {"ok": False, "oneriler": [], "say": {}}
    try: return dict(y.belge_onerileri(BASE, _bo_kart(), _bo_belgeler(), os.path.join(AYAR["uygulama"], "cevirme-onbellek"), vt_isler=_bo_vt()), ok=True)
    except Exception as e: print(f"BELGEDEN ATAMA: öneriler okunamadı ({e.__class__.__name__})"); return {"ok": False, "oneriler": [], "say": {}}
def belge_oneri_islem(p):
    y = _yapi_mod(); p = p if isinstance(p, dict) else {}; oid = str(p.get("id") or "")[:20]; isl = str(p.get("islem") or "")
    if not y or not oid or isl not in ("kabul", "reddet"): return {"ok": False, "err": "id ve işlem gerekli"}
    if isl == "reddet": r = {"ok": y.belge_oneri_reddet(BASE, oid)}; print(f"BELGEDEN ATAMA: öneri reddedildi {oid}"); return r
    o = next((x for x in belge_oneri_view().get("oneriler") or [] if x.get("id") == oid), None)
    if not o: return {"ok": False, "err": "öneri yok (kayda girmiş ya da reddedilmiş olabilir)"}
    sh = " ".join(str(p.get("sahip") or o.get("sahip") or "").split())[:80]; ep = ""
    if sh:
        try: ep = (_kem_kimlik(sh, True) or {}).get("eposta") or ""
        except Exception: ep = ""
    try: r = y.belge_oneri_kabul(BASE, o, sh, ep)
    except Exception as e: print(f"BELGEDEN ATAMA: kabul yapılamadı ({e.__class__.__name__})"); return {"ok": False, "err": e.__class__.__name__}
    print(f"BELGEDEN ATAMA: öneri kayda girdi {oid} → {r.get('id')} · " + ", ".join(r.get("olaylar") or []) + (" · e-postalı" if ep else ""))  # günlüğe metin yazılmaz
    return r
