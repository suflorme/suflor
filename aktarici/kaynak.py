# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("kaynak")). Kaynak bekçisi (mimari plan C / K4, 29 Ekim) + PID ile süreç kapatma.
# 27 Ekim 21:45: takas doldu, yük 246, Whisper 121 sn'de açıldı; kullanıcıya hiçbir uyarı yoktu. Bekçi 10 sn'de bir boş bellek (%), takas (GB) ve 1 dk yükü okur
# (sistem_anlik, bas-konus.py) ve üç düzey tutar: normal / dar / kritik. DAR'da yalnız isteğe bağlı ya da önceden yapılan işler ertelenir (kaynak_dar()):
# Konuş'u önceden açma (konus_on_ac), ikinci Konuş süreci (konus_iki_surec), ön arama dizini turu + Brifing yardımcısı dizin turu (_onara_guncelle), veritabanı
# önbelleği yardımcısı (vt_izle_bak), Pocket'in boşta kapanması 1 dk'ya iner (pocket_izle_bir; toplantı motoru Pocket'se açık kalır). Whisper, Konuş'un tek
# süreci ve toplantı oturumu HİÇBİR düzeyde durdurulmaz. KRİTİK'te ek olarak /status kaynak.duzey "kritik" → panoda kalıcı sarı kart.
# Eşikler (ayar kaynak_*; AYAR_PANO'da yok). Veri: 28 Ekim sistem-izi.jsonl (toplantı içi, 291 ölçüm): boş bellek en az %29, p5 %37, medyan %63;
# takas p50 0, p90 3,2, p99 3,9, en çok 3,9 GB (16 GB'lık Mac). 27 Ekim olayı: takas dolu, yük 246 (10 çekirdek). Dar eşiği gözlenen en düşüğün altında
# (boş ≤ %22, takas ≥ 4 GB, yük ≥ 1,5 × çekirdek), kritik çok daha aşağıda (boş ≤ %12, takas ≥ 6 GB, yük ≥ 3 × çekirdek). Titreşim: düzey ancak
# 3 ardışık ölçümde (30 sn) yükselir; düşmek için ölçümler çıkış payını da geçmeli (boş +5 puan, takas −0,5 GB, yük × 0,8) ve 6 ardışık (60 sn) sürmeli.
import subprocess, signal
KAYNAK_DUZEYLER = ("normal", "dar", "kritik")
KAYNAK_SN = 0.3 if os.environ.get("SUFLOR_TEST_HIZLI") else 10
KAYNAK = {"duzey": "normal", "bos_yuzde": None, "takas_gb": None, "yuk": None, "t": None, "_yukari": 0, "_asagi": 0}
def _kaynak_esikler():
    def f(k, v):
        try: return float(AYAR.get(k, v))
        except (TypeError, ValueError): return float(v)
    cek = os.cpu_count() or 4
    return {"dar": {"bos": f("kaynak_dar_bos", 22), "takas": f("kaynak_dar_takas", 4.0), "yuk": f("kaynak_dar_yuk", 1.5) * cek},
            "kritik": {"bos": f("kaynak_kritik_bos", 12), "takas": f("kaynak_kritik_takas", 6.0), "yuk": f("kaynak_kritik_yuk", 3.0) * cek},
            "pay": {"bos": f("kaynak_cikis_bos", 5), "takas": f("kaynak_cikis_takas", 0.5), "yuk": f("kaynak_cikis_yuk", 0.8)},
            "yukari_n": int(f("kaynak_yukari_n", 3)), "asagi_n": int(f("kaynak_asagi_n", 6))}
def kaynak_ham(o, es, cikis=False):  # → düzey adı; cikis=True: mevcut düzeyde kalma ölçütü (eşiklere çıkış payı eklenir)
    b, t, y = o.get("bos_yuzde"), o.get("takas_gb"), o.get("yuk"); p = es["pay"]; d = "normal"
    for ad in ("dar", "kritik"):
        e = es[ad]; bos_e = e["bos"] + (p["bos"] if cikis else 0); tak_e = e["takas"] - (p["takas"] if cikis else 0); yuk_e = e["yuk"] * (p["yuk"] if cikis else 1)
        if (b is not None and b <= bos_e) or (t is not None and t >= tak_e) or (y is not None and y >= yuk_e): d = ad
    return d
def kaynak_isle(o, es=None):  # bir ölçüm: sayaçları ve düzeyi günceller, geçişte günlük satırı yazar → düzey
    es = es or _kaynak_esikler(); K = KAYNAK; once = K["duzey"]; sira = KAYNAK_DUZEYLER.index
    K.update(bos_yuzde=o.get("bos_yuzde"), takas_gb=o.get("takas_gb"), yuk=o.get("yuk"), t=round(time.time(), 1))
    ham = kaynak_ham(o, es); tut = kaynak_ham(o, es, cikis=True)
    if sira(ham) > sira(once): K["_yukari"] += 1; K["_asagi"] = 0; yeni = ham if K["_yukari"] >= es["yukari_n"] else once
    elif sira(tut) < sira(once): K["_asagi"] += 1; K["_yukari"] = 0; yeni = tut if K["_asagi"] >= es["asagi_n"] else once
    else: K["_yukari"] = K["_asagi"] = 0; yeni = once
    if yeni != once:
        K.update(duzey=yeni, _yukari=0, _asagi=0)
        print(f"KAYNAK: {once} → {yeni} (boş %{K['bos_yuzde']}, takas {K['takas_gb']} GB, yük {K['yuk']})")
    return K["duzey"]
def kaynak_olc():  # sistem_anlik (bas-konus.py) okuyucusunu kullanır; SUFLOR_KAYNAK_OLCUM = JSON dosyası (deneme: sahte ölçüm)
    sahte = os.environ.get("SUFLOR_KAYNAK_OLCUM")
    if sahte:
        try: o = json.load(open(sahte, encoding="utf-8"))
        except (OSError, ValueError): return {}
    else: o = sistem_anlik()
    t = o.get("takas_gb") if o.get("takas_gb") is not None else (round(o["takas_mb"] / 1024, 2) if o.get("takas_mb") is not None else None)
    return {"bos_yuzde": o.get("bos_yuzde"), "takas_gb": t, "yuk": o.get("yuk")}
def kaynak_dar(): return KAYNAK["duzey"] != "normal" and AYAR.get("kaynak_bekci") is not False  # dar ya da kritik: isteğe bağlı işler ertelenir
def kaynak_view():
    return {"duzey": KAYNAK["duzey"], "bos_yuzde": KAYNAK["bos_yuzde"], "takas_gb": KAYNAK["takas_gb"], "yuk": KAYNAK["yuk"], "t": KAYNAK["t"]}
def _kaynak_dongu():
    while True:
        time.sleep(KAYNAK_SN)
        if AYAR.get("kaynak_bekci") is False: KAYNAK["duzey"] = "normal"; continue
        try: kaynak_isle(kaynak_olc())
        except Exception as e: print(f"KAYNAK: ölçülemedi ({e.__class__.__name__})")
# --- PID ile süreç kapatma (pkill yerine) -----------------------------------------------------------------------------------------------------------
# Aktarıcının `open -a` ile açtığı yardımcıların (Suflor Ses, menü uygulaması) Popen nesnesi yoktur (LaunchServices açar). PID, YALNIZ bu hesabın
# süreçleri içinden (pgrep -u <uid>) bulunur, her biri tek tek SIGTERM'lenir, bekleme sonunda yaşayan SIGKILL alır. Öteki hesabın süreçleri hiç görünmez.
def surec_pidler(desen, tam=False):
    try: r = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x" if tam else "-f", desen], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError): return []
    return [int(x) for x in r.split() if x.isdigit() and int(x) != os.getpid()]
def surec_kapat(desen, tam=False, bekle=3.0):  # → bulunan süreç sayısı
    pids = surec_pidler(desen, tam); n = len(pids)
    for p in pids:
        try: os.kill(p, signal.SIGTERM)
        except OSError: pass
    son = time.time() + bekle
    while pids and time.time() < son:
        pids = [p for p in pids if _surec_yasiyor(p)]
        if pids: time.sleep(0.1)
    for p in pids:
        try: os.kill(p, signal.SIGKILL)
        except OSError: pass
    return n
def _surec_yasiyor(p):
    try: os.kill(p, 0); return True
    except OSError: return False
