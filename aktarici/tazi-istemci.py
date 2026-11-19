# --- Tazı istemcisi (S321, 17 Kasım): Suflor Tazı'nın MÜŞTERİSİDİR. Tazı ayrı depo ve ayrı hizmettir; Suflor'da Tazı kodu yok, Tazı'nın veri klasörü
# (tazi.db, dosya/, rapor/) doğrudan okunmaz. Tek kapı: Tazı deposundaki tazi_hizmet.py (sözleşme orada: docs/arayuz.md, arayuz_surum 1).
# Yer: ortam TAZI_HIZMET > ayar tazi_yol > kurulu kopya ~/Library/Application Support/Tazi/uygulama/tazi_hizmet.py (Tazı kur.py;
# launchd altındaki aktarıcı Masaüstü'nü okuyamayabilir) > geliştirme deposu ~/Desktop/Tazi/tazi_hizmet.py. Dosya yoksa (beta, Tazı'sız kurulum) her çağrı {"ok": False, "hata": "tazi_yok"}:
# çağıranlar bunu "Tazı kapalı" gibi sessizce karşılar. Girdi JSON'u standart girdiden gider (ad `ps` çıktısına düşmez); çıktı tek JSON nesnesi.
# Ayar tazi (aç/kapa) burada denetlenmez: çağıranın işidir. Gizli kip (19 Kasım, dış çıkış kapısı aktarici/cikis.py) BURADA da denetlenir, varsayılan kapalı:
#   aktarıcıda cikis_izin("tazi"); tek başına yüklenince (toplanti-claude.py, kesisim*.py) canli/gizli.json okunur — var ya da varlığı belirlenemiyorsa çağrı yok ({"hata": "gizli"}).
# İki kullanım: aktarıcıda bolum("tazi-istemci") ile ortak ad alanına girer; toplanti-claude.py, kesisim.py, kesisim-coz.py importlib ile yükler.
import hashlib, json, os, subprocess, sys, threading, time
TAZI_HIZMET_KURULU = "~/Library/Application Support/Tazi/uygulama/tazi_hizmet.py"
TAZI_HIZMET_VARSAYILAN = "~/Desktop/Tazi/tazi_hizmet.py"
TAZI_ZAMAN_VARSAYILAN = 20
_TZI_ONB = {}   # (işlem, girdi özeti) → (bitiş zamanı, sonuç); okuyan işlemler için kısa süreli önbellek (pano /status yoklaması, Konuş yönlendirmesi)
_TZI_ONB_EN_COK = 200
_TZI_KILIT = threading.Lock()
def _tzi_ayar(ayar):
    if isinstance(ayar, dict): return ayar
    a = globals().get("AYAR")
    if isinstance(a, dict): return a
    try:
        with open(os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8") as f: a = json.load(f)
        return a if isinstance(a, dict) else {}
    except (OSError, ValueError): return {}
def tazi_hizmet_yolu(ayar=None):  # → hizmet dosyasının yolu ya da None (Tazı kurulu değil)
    y = os.environ.get("TAZI_HIZMET") or _tzi_ayar(ayar).get("tazi_yol")
    if not y:
        k = os.path.expanduser(TAZI_HIZMET_KURULU)
        y = k if os.path.isfile(k) else TAZI_HIZMET_VARSAYILAN
    y = os.path.expanduser(str(y))
    return y if os.path.isfile(y) else None
def _tzi_canli(ayar):  # aktarıcının canli klasörü (tek başına kullanımda gizli.json için)
    a = _tzi_ayar(ayar)
    return os.path.join(os.path.expanduser(str(a.get("uygulama") or "~/Library/Application Support/Suflor")), "canli")
def tazi_cikis(islem, ayar=None):  # → (ok, neden). Aktarıcıda dış çıkış kapısı; değilse gizli.json (fail-closed)
    f = globals().get("cikis_izin")
    if callable(f): return f("tazi", str(islem))
    try: os.lstat(os.path.join(_tzi_canli(ayar), "gizli.json")); return False, "gizli kip"
    except FileNotFoundError: return True, ""
    except OSError: return False, "gizli kip"
def tazi_onbellek_sil():
    with _TZI_KILIT: _TZI_ONB.clear()
def tazi_cagir(islem, girdi=None, zaman=TAZI_ZAMAN_VARSAYILAN, ayar=None, onbellek=0):
    """→ hizmetin JSON nesnesi ({"ok": True, …} ya da {"ok": False, "hata": kod}). İstemci kodları: tazi_yok, erisim_yok (macOS izni), zaman_asimi, cikti, cagri.
    onbellek > 0: aynı işlem + girdi bu kadar saniye yeniden çağrılmaz (yalnız okuyan işlemlerde kullan)."""
    ok, neden = tazi_cikis(islem, ayar)
    if not ok: return {"ok": False, "hata": "gizli" if neden == "gizli kip" else "cikis"}
    y = tazi_hizmet_yolu(ayar)
    if not y:  # launchd altındaki aktarıcı Masaüstü'nü okuyamayabilir (macOS izni): "yok"tan ayrı kod, günlükte görünsün
        try: os.stat(os.path.expanduser(str(os.environ.get("TAZI_HIZMET") or _tzi_ayar(ayar).get("tazi_yol") or TAZI_HIZMET_VARSAYILAN)))
        except PermissionError: return {"ok": False, "hata": "erisim_yok"}
        except OSError: pass
        return {"ok": False, "hata": "tazi_yok"}
    ham = json.dumps(girdi or {}, ensure_ascii=False, sort_keys=True)
    k = (y, islem, hashlib.sha1(ham.encode("utf-8")).hexdigest()) if onbellek else None
    if k:
        with _TZI_KILIT:
            v = _TZI_ONB.get(k)
            if v and v[0] > time.time(): return v[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        p = subprocess.run([sys.executable, "-B", y, str(islem), "--json-girdi", "-"], input=ham, capture_output=True, text=True, timeout=zaman, env=env)
        try: r = json.loads((p.stdout or "").strip().splitlines()[-1])
        except (ValueError, IndexError): r = {"ok": False, "hata": "cikti", "ayrinti": f"çıkış {p.returncode}"}
        if not isinstance(r, dict): r = {"ok": False, "hata": "cikti"}
    except subprocess.TimeoutExpired: r = {"ok": False, "hata": "zaman_asimi"}
    except Exception as e: r = {"ok": False, "hata": "cagri", "ayrinti": e.__class__.__name__}
    if k:
        with _TZI_KILIT:
            if len(_TZI_ONB) >= _TZI_ONB_EN_COK: _TZI_ONB.clear()
            _TZI_ONB[k] = (time.time() + onbellek, r)
    return r
