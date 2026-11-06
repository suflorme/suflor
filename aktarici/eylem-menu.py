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
def eylem_model(istem):
    # → (ham metin, hata metni ya da None). Tek model çağrısı (prova_model gibi): başka sağlayıcıysa beyin_tek, Claude Code ise Brifing.app --istek (Masaüstü izni uygulamada).
    try:
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
    try: return y.eylem_menu(BASE, kid, _kem_takvim(), lambda ad: _kem_kimlik(ad, False))
    except Exception as e: print(f"EYLEM MENÜSÜ: okunamadı ({e.__class__.__name__})"); return {"ok": False, "err": e.__class__.__name__}
def kayit_eylem_islem(p):  # POST /kayit-eylem
    y = _yapi_mod(); p = p if isinstance(p, dict) else {}; kid = str(p.get("id") or "")[:40]; e = str(p.get("eylem") or "")[:20]
    if not y or not kid or not e: return {"ok": False, "err": "id ve eylem gerekli"}
    try: r = y.kayit_eylem(BASE, kid, e, p, None, lambda ad: _kem_kimlik(ad, True), _kem_takvim(), eylem_model)
    except Exception as ex: print(f"EYLEM MENÜSÜ: {e} yapılamadı ({ex.__class__.__name__})"); return {"ok": False, "err": ex.__class__.__name__}
    print(f"EYLEM MENÜSÜ: {e} {kid} → " + ("tamam" if r.get("ok") else str(r.get("err"))))  # günlüğe metin yazılmaz
    return r
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
def _bo_vt():  # ayar veritabani.gorevler: kayıt veritabanının açık işleri — YALNIZ OKUMA (mode=ro), en çok 500 satır, 3 sn; sütunlar: iş metni, sahip, vade, konum
    vt = AYAR.get("veritabani") if isinstance(AYAR.get("veritabani"), dict) else {}
    if not vt.get("yol") or not str(vt.get("gorevler") or "").strip(): return None
    yol = os.path.expanduser(str(vt["yol"])); yol = yol if os.path.isabs(yol) else os.path.join(os.path.expanduser(str(AYAR.get("proje") or "")), yol)
    import sqlite3, urllib.parse
    try:
        c = sqlite3.connect(f"file:{urllib.parse.quote(yol)}?mode=ro", uri=True, timeout=3); t0 = time.time()
        c.set_progress_handler(lambda: 1 if time.time() - t0 > 3 else 0, 10000)
        try: return [list(r) for r in c.execute(str(vt["gorevler"])).fetchmany(500)]
        finally: c.close()
    except sqlite3.Error as e:
        try:  # launchd altında Masaüstü'ndeki veritabanı açılmaz: veritabanı yardımcısının (vt-izle) yazdığı önbellek
            o = json.load(open(os.path.join(BASE, "vt-gorevler.json"), encoding="utf-8"))
            return [list(r) for r in (o.get("satirlar") or [])][:500]
        except (OSError, ValueError, AttributeError): pass
        if _BO_VT_UYARI.get("e") != e.__class__.__name__: _BO_VT_UYARI["e"] = e.__class__.__name__; print(f"BELGEDEN ATAMA: görev sorgusu okunamadı ({e.__class__.__name__}), önbellek de yok")
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
