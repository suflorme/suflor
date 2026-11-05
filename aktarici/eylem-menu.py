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
