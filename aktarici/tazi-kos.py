# --- Tazı koşturucu (11 Kasım): Suflor'un iz sürme köpeği. Aday listesine ekler (tazi.py aday), taramayı arka planda alt süreç olarak koşturur (tazi.py tara --kim … [--hizli]).
# Kural: tek tarama aynı anda, kuyruk ≤ 5, aynı ad 6 saatte bir, günlük tavan ayar tazi_gunluk (20); toplantı sürerken tam tarama bekler (ağ etkisi), hızlı hemen gider.
# Gizli kipte ve ayar tazi kapalıyken (geliştiricide varsayılan açık, beta'da kapalı) hiçbir şey çalışmaz. Tarama yalnız ad ve alan adını ağa götürür; döküm/iç sayı gitmez.
# Günlükte "TAZI KOŞ:" satırları kayıt kimliğiyle (ad yazılmaz). Durum /status "tazi", uç POST /tazi {islem: tara|durum} (anahtarlı). ana izleme listesine yazılmaz.
import subprocess, stat
TZK = {"calisiyor": None, "kuyruk": [], "sonuc": None, "dongu": False}
TZK_KUYRUK_EN_COK = 5
TZK_TEKRAR_SN = 6 * 3600
TZK_LOCK = threading.Lock()
def _tzk_yol(): return os.path.join(BASE, "tazi-kos.json") if "BASE" in globals() else None
def _tzk_oku():
    try: d = json.load(open(_tzk_yol(), encoding="utf-8"))
    except (OSError, ValueError, TypeError): d = {}
    bug = datetime.date.today().isoformat()
    if d.get("gun") != bug: d = {"gun": bug, "n": 0, "son": d.get("son") or {}}
    d.setdefault("son", {}); d.setdefault("n", 0); return d
def _tzk_yaz(d):
    try: tmp = _tzk_yol() + ".tmp"; json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False); os.replace(tmp, _tzk_yol())
    except (OSError, TypeError): pass
def _tzk_anahtar(ad): return " ".join(str(ad or "").lower().replace("İ", "i").replace("ı", "i").split())
def tzk_tavan():
    try: return max(1, int(AYAR.get("tazi_gunluk") or 20))
    except (TypeError, ValueError): return 20
def tazi_kos(ad, alan=None, kip="hizli", neden="elle"):  # → {"ok", "durum": basladi|kuyruk|bekliyor|zaten|tavan|gizli|kapali|yok|bos|dolu, "mesaj"}; ağ yok, hemen döner
    ad = " ".join(str(ad or "").split())[:80]; alan = (str(alan or "").strip().lower()[:80]) or None; kip = "tam" if kip == "tam" else "hizli"
    if not tazi_acik(): return {"ok": False, "durum": "kapali"}
    if gizli_acik(): return {"ok": False, "durum": "gizli"}
    if len(ad) < 3: return {"ok": False, "durum": "bos"}
    if not tazi_yol(): return {"ok": False, "durum": "yok"}
    k = _tzk_anahtar(ad)
    with TZK_LOCK:
        d = _tzk_oku(); s = d["son"].get(k) or {}; now = time.time()
        if any(o["k"] == k and (o["kip"] == kip or kip == "hizli") for o in TZK["kuyruk"]) or (TZK["calisiyor"] or {}).get("k") == k: return {"ok": True, "durum": "zaten"}
        if (s.get("tam") and now - s["tam"] < TZK_TEKRAR_SN) or (s.get(kip) and now - s[kip] < TZK_TEKRAR_SN): return {"ok": True, "durum": "zaten"}
        if d["n"] >= tzk_tavan(): print(f"TAZI KOŞ: günlük sınır ({d['n']}/{tzk_tavan()}) — istek alınmadı"); return {"ok": False, "durum": "tavan"}
        if len(TZK["kuyruk"]) >= TZK_KUYRUK_EN_COK: return {"ok": False, "durum": "dolu"}
        d["n"] += 1; _tzk_yaz(d)
        TZK["kuyruk"].append({"ad": ad, "alan": alan, "kip": kip, "neden": neden if neden in ("toplanti", "konus", "brifing", "elle") else "elle", "k": k, "t": now})
        bekliyor = kip == "tam" and toplanti_suruyor()
    print(f"TAZI KOŞ: kuyruğa alındı ({kip}, neden {neden}, kuyruk {len(TZK['kuyruk'])})")
    if "STATE" in globals() and not os.environ.get("SUFLOR_TZK_DONGU_YOK"): _tzk_dongu_baslat()
    return {"ok": True, "durum": "bekliyor" if bekliyor else "basladi"}
def _tzk_sec():  # çalıştırılacak sıradaki öğe: hızlı önce; tam toplantı sürerken beklemede
    tm = toplanti_suruyor()
    for o in sorted(TZK["kuyruk"], key=lambda o: (o["kip"] == "tam", o["t"])):
        if o["kip"] == "tam" and tm: continue
        return o
    return None
def _tzk_cagir(args, zaman):  # kabuksuz alt süreç; (çıkış kodu, çıktı)
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        p = subprocess.run([sys.executable, "-B", tazi_yol()] + args, capture_output=True, text=True, timeout=zaman, env=env)
        if p.returncode:  # hata türü günlüğe (yalnız son satırın tür adı; ad/metin yazılmaz)
            son = next((x for x in reversed((p.stderr or "").strip().splitlines()) if x.strip()), "")
            print(f"TAZI KOŞ: tazi.py {args[0] if args else '?'} çıkış {p.returncode} ({re.split(r'[:(]', son, 1)[0].strip()[:60] or 'stderr boş'})")
        return p.returncode, (p.stdout or "")[-600:]
    except subprocess.TimeoutExpired: return 124, "zaman aşımı"
    except Exception as e: return 125, e.__class__.__name__
def _tzk_kayit_id(ad):
    try: m = tazi_mod(); k = m.kayit_bul(m.liste_oku(), ad) if m else None; return (k or {}).get("id") or "?"
    except Exception: return "?"
def tzk_isle():  # sıradaki öğeyi koştur (dongu çağırır; testler doğrudan çağırır) → koşan öğe ya da None
    with TZK_LOCK:
        if TZK["calisiyor"]: return None
        if gizli_acik() or not tazi_acik(): TZK["kuyruk"].clear(); return None
        o = _tzk_sec()
        if not o: return None
        TZK["kuyruk"].remove(o); TZK["calisiyor"] = o
    t0 = time.time()
    try:
        a = ["aday", "--ad", o["ad"], "--neden", o["neden"]] + (["--alan", o["alan"]] if o["alan"] else [])
        _tzk_cagir(a, 20)
        kid = _tzk_kayit_id(o["ad"]); print(f"TAZI KOŞ: başladı ({o['kip']}, kayıt {kid}, neden {o['neden']})")
        rc, cikti = _tzk_cagir(["tara", "--kim", o["ad"]] + (["--hizli"] if o["kip"] == "hizli" else []), 60 if o["kip"] == "hizli" else 900)
        with TZK_LOCK:
            d = _tzk_oku(); d["son"].setdefault(o["k"], {})[o["kip"]] = time.time(); d["son"] = dict(list(d["son"].items())[-300:]); _tzk_yaz(d)
        TZK["sonuc"] = {"kayit": kid, "kip": o["kip"], "durum": "ok" if rc == 0 else "hata", "t": round(time.time()), "sn": round(time.time() - t0)}
        print(f"TAZI KOŞ: bitti ({o['kip']}, kayıt {kid}, {'ok' if rc == 0 else 'çıkış ' + str(rc)}, {round(time.time() - t0)} sn)")
        if "tazi_yenile" in globals(): tazi_yenile()
    except Exception as e: print(f"TAZI KOŞ: hata ({e.__class__.__name__})")
    finally:
        with TZK_LOCK: TZK["calisiyor"] = None
    return o
def _tzk_dongu():
    while True:
        time.sleep(5)
        try:
            if TZK["kuyruk"] and not TZK["calisiyor"]: tzk_isle()
        except Exception as e: print(f"TAZI KOŞ: döngü hatası ({e.__class__.__name__})")
def _tzk_dongu_baslat():
    if not TZK["dongu"]: TZK["dongu"] = True; threading.Thread(target=_tzk_dongu, daemon=True).start()
# --- Rapor listesi ve okuma (12 Kasım, panoda Bugün'de "Tazı raporu"): <tazi veri>/rapor/*.md. Liste /status tazi.raporlar (≤ 5, -son.md kopyaları ve DIZIN.md yok); metin POST /tazi {islem: rapor, dosya} (yalnız pano, ≤ 200 KB).
# Tazı kapalıyken ve gizli kipte boş döner. Rapor adı/metni günlüğe yazılmaz.
TZR_EN_COK = 5
TZR_BOYUT = 200 * 1024
TZR_AD_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.md$")
def _tzr_dizin():  # rapor klasörü (tazi.py veri_dizin yolu; tazi.py yoksa None)
    m = tazi_mod()
    try: return os.path.join(m.veri_dizin(), "rapor") if m else None
    except Exception: return None
def _tzr_tur(f): return "tazi" if f.startswith("tazi-") else "toplanti" if f.startswith("toplanti-") else "kisi"
def tazi_raporlar(en=None):  # [{tur: tazi|toplanti|kisi, dosya, t (değişme, epoch sn)}] yeniden eskiye
    if not tazi_acik() or gizli_acik(): return []
    d = _tzr_dizin(); o = []
    try: ad = os.listdir(d) if d and os.path.isdir(d) else []
    except OSError: return []
    for f in ad:
        if not f.endswith(".md") or f.endswith("-son.md") or f == "DIZIN.md" or not TZR_AD_RX.match(f): continue
        try: st = os.stat(os.path.join(d, f))
        except OSError: continue
        if not stat.S_ISREG(st.st_mode): continue
        o.append({"tur": _tzr_tur(f), "dosya": f, "t": int(st.st_mtime)})
    o.sort(key=lambda x: (x["t"], x["dosya"]), reverse=True); return o[:en or TZR_EN_COK]
def tazi_rapor_oku(dosya):  # → {"ok", "dosya", "tur", "t", "metin"} ya da {"ok": False, "durum": …}
    if not tazi_acik(): return {"ok": False, "durum": "kapali"}
    if gizli_acik(): return {"ok": False, "durum": "gizli"}
    f = str(dosya or "")
    if not TZR_AD_RX.match(f) or ".." in f: return {"ok": False, "durum": "ad"}
    d = _tzr_dizin()
    if not d: return {"ok": False, "durum": "yok"}
    yol = os.path.join(d, f)
    try:
        if os.path.dirname(os.path.realpath(yol)) != os.path.realpath(d) or not os.path.isfile(yol): return {"ok": False, "durum": "yok"}
        st = os.stat(yol)
        if st.st_size > TZR_BOYUT: return {"ok": False, "durum": "buyuk"}
        with open(yol, encoding="utf-8", errors="replace") as fh: metin = fh.read(TZR_BOYUT)
    except OSError: return {"ok": False, "durum": "yok"}
    return {"ok": True, "dosya": f, "tur": _tzr_tur(f), "t": int(st.st_mtime), "metin": metin}
def tazi_view():  # /status "tazi"
    d = _tzk_oku() if _tzk_yol() else {"n": 0}
    return {"acik": bool(tazi_acik()), "calisiyor": bool(TZK["calisiyor"]), "kuyruk": len(TZK["kuyruk"]), "bugun": d.get("n", 0), "tavan": tzk_tavan(), "son": TZK["sonuc"], "raporlar": tazi_raporlar()}
def tazi_islem(p):  # POST /tazi (anahtarlı): tara {kim, alan?, kip?, neden?} | durum | rapor {dosya} (köken denetimi relay.py'de: yalnız pano)
    i = p.get("islem")
    if i == "rapor": return tazi_rapor_oku(p.get("dosya"))
    if i == "durum": return dict(tazi_view(), ok=True)
    if i == "tara":
        r = tazi_kos(p.get("kim") or p.get("ad"), p.get("alan"), p.get("kip") or "hizli", p.get("neden") or "elle"); return dict(r, durum_ozet=tazi_view())
    return {"ok": False, "err": "islem"}
# --- Sesle/yazıyla komut: "Tazı, <ad> araştır / iz sür / izle" (kural; model yok). Toplantı dışında tam tarama, toplantıda hızlı (Konuş'un yerel komutu toplantıda kapalı; kutu için de aynı).
TAZI_KOMUT_RX = re.compile(r"^\W*(?:tazı|tazi)(?:['’]\w+)?\b[\s,:;.!-]*(.{3,70}?)\s+(?:(?:iz\s?sür|araştır|arastir|incele|tara|izlemeye\s?al|izle)(?:\s?(?:lütfen|bakalım))?)\W*$", re.I)
def tazi_komut(metin):  # → izlenecek ad ya da None (komut değil)
    m = TAZI_KOMUT_RX.match(" ".join(str(metin or "").split()))
    if not m: return None
    ad = re.sub(r"['’](?:y?[ıiuü]|n[ıiuü]n?)$", "", m.group(1).strip(" ,.;:!?\"'")); ad = re.sub(r"^(?:şu|bu)\s+", "", ad, flags=re.I).strip(" ,.;:!?\"'")
    return ad if 3 <= len(ad) <= 60 and not re.search(r"https?:|@", ad) else None
def tazi_komut_cevap(metin):  # → okunacak/yazılacak kısa teyit ya da None (komut değil). Gizli kipte ve ayar kapalıyken None (Claude'a gider)
    ad = tazi_komut(metin)
    if not ad or gizli_acik() or not tazi_acik(): return None
    dom = re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", ad.lower())
    r = tazi_kos(ad, dom.group(1) if dom else None, "hizli" if toplanti_suruyor() else "tam", "konus")
    d = r.get("durum")
    if d in ("basladi", "bekliyor"): return _t(f"Tazı iz sürüyor: {ad}. Bitince sorarsan dosyadan anlatırım.", f"Tazı is on the trail: {ad}. Ask me when it's done and I'll tell you from the file.")
    if d == "zaten": return _t(f"{ad} için Tazı zaten çalışıyor ya da yakın zamanda tarandı; dosyasına bakabilirim.", f"Tazı already scanned {ad} recently or is on it; I can read its file.")
    if d == "tavan": return _t("Tazı'nın bugünkü tarama sınırı doldu; yarın tekrar dene.", "Tazı's daily scan limit is reached; try again tomorrow.")
    if d == "dolu": return _t("Tazı'nın kuyruğu dolu; birkaç dakika sonra tekrar söyle.", "Tazı's queue is full; ask again in a few minutes.")
    return None
