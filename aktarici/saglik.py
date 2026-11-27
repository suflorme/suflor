# --- Sessiz kırılma yok (Faz D, S162, v0.147.0; mimari plan §3 ilke 3) -----------------------------------------------------------------------------------
# 27 Ekim denemeleri: toplantı sürüyor, hiçbir kanaldan döküm gelmiyor, sağlık satırı yine de yeşil ("süreç çalışıyor" = ✓). Sağlık artık "veri akıyor mu" diye
# ölçülür: toplantı sürerken (eklenti çağrıda · masaüstü toplantı · tanınan toplantı; gizli kipte değil) VERI_YOK_SN boyunca ingest'e hiçbir satır gelmediyse
# /status veri_yok {sn, kanallar} döner, günlüğe bir kez yazılır, pano sarı uyarı gösterir; satır gelince kalkar. Kanal durumu "neden"i söyler (altyazı, ben, karşı).
# /dogrula: kurulum.py dogrula'nın (Kurulumu denetle) son sonucu; ?yenile=1 arka planda yeniden koşturur (kilitli, en çok dakikada bir).
_VY = {"bas": None, "son": 0.0, "kanal": {}, "yazildi": False}
VERI_YOK_SN = 6 if os.environ.get("SUFLOR_TEST_HIZLI") else 60
def veri_satiri(kaynak, kanal):  # ingest her satırda çağırır: altyazı ("transcript") ya da Whisper kanalı ("ben" | "karsi")
    now = time.time(); _VY["son"] = now; _VY["kanal"]["altyazi" if kaynak != "whisper" else (kanal if kanal in ("ben", "karsi") else "karsi")] = now
def toplanti_suruyor():
    if gizli_acik(): return False
    a = TOPLANTI.get("aktif") or {}  # Faz B: süren kayıt; Başlat'la açılıp henüz sinyali olmayan (toplantı başlamadı) sayılmaz
    return toplanti_var() or (a.get("durum") == "algilandi" and bool(sinyaller()))
def kanal_akiyor(k, sn=None): return time.time() - _VY["kanal"].get(k, 0) < (sn or VERI_YOK_SN)  # pano sağlığı: süreç değil, veri akıyor mu
def kanal_son(k): return _VY["kanal"].get(k, 0)  # kanalın son satır zamanı (deneme toplantısı kipi: başladıktan sonra satır geldi mi)
def veri_yok_view():
    now = time.time()
    if not toplanti_suruyor():
        if _VY["yazildi"]: print("VERİ YOK: kalktı (toplantı bitti)")
        _VY.update(bas=None, yazildi=False); return None
    if _VY["bas"] is None: _VY["bas"] = now
    sn = now - max(_VY["bas"], _VY["son"])
    if sn < VERI_YOK_SN * (2 if yerel_ses_durum() == "dinliyor" else 1):  # mrt 28 Ekim B4: ses dinleniyorsa kimse konuşmuyor olabilir — eşik 2 katı
        if _VY["yazildi"]: print("VERİ YOK: kalktı (satır geldi)"); _VY["yazildi"] = False
        return None
    x = STATE.get("extension") or {}; w = STATE.get("whisper") or {}
    kanallar = {"altyazi": "acik" if (x.get("captions") or x.get("panel")) else "yok", "ben": ben_kod(), "karsi": yerel_ses_durum() if yerel_ses_durum() != "kapali" else ("web" if x.get("call") else "kapali"),
                "whisper": w.get("durum") or "yok"}
    if not _VY["yazildi"]:
        _VY["yazildi"] = True; print(f"VERİ YOK: toplantı sürüyor ama {round(sn)} sn'dir satır gelmiyor (altyazı {kanallar['altyazi']}, ben {kanallar['ben']}, karşı {kanallar['karsi']}, whisper {kanallar['whisper']})")
    return {"sn": round(sn), "kanallar": kanallar}
# v0.255.1 (beta #89/#90, 25 Kasım 93 dk Meet): karşı tarafın sesi akarken kullanıcının mikrofonu ("ben") 78 dk hiç yazılmadı, kimse fark etmedi
# (veri_yok yalnız hiçbir kanal akmıyorsa uyarır). Toplantı tarayıcıda sürerken (eklenti sekmesi ya da yerel ses yardımcısı bir tarayıcıyı dinliyor;
# masaüstü toplantı değil) BEN_KOPUK_SN boyunca mikrofon kanalı bağlı değilse — eklentiden mikrofon bilgisi yok (betik kopuk / toplantı eklentisiz
# tarayıcıda), mikrofon açılamadı ya da açık ama ses parçası gelmiyor — /status ben_kopuk {sn, neden, uygulama} döner (STATE üzerinden), günlüğe
# bir kez yazılır, pano ve mini pano kırmızı uyarı gösterir; kanal düzelince kalkar. Konuşmamak sorun değil: mikrofon açıkken sessizlikte de
# parça akar (ben_kod "akiyor"); sessize almak ("sessiz") ve Whisper'ı kapatmak ("kapali") uyarı değil. Altyazı akıyorsa ("ben" altyazıdan) yok.
BEN_KOPUK_SN = 8 if os.environ.get("SUFLOR_TEST_HIZLI") else 120
TARAYICILAR = ("Safari", "Google Chrome", "Chrome", "Firefox", "Microsoft Edge", "Arc", "Brave Browser", "Opera", "Vivaldi", "Chromium")
_BK = {"bas": None, "yazildi": False}
def _ben_kopuk_neden():  # → (kod, uygulama) ya da None (kanal bağlı / uyarılacak durum değil)
    if not toplanti_suruyor() or ("masaustu_toplantida" in globals() and masaustu_toplantida()): return None
    if (STATE.get("whisper") or {}).get("durum") in (None, "yok") or kanal_akiyor("altyazi", 180): return None
    kod = ben_kod() if "ben_kod" in globals() else "yok"
    if kod not in ("yok", "hata", "sorun"): return None
    ek = eklenti_sayfa() if "eklenti_sayfa" in globals() else None
    ya = str((STATE.get("yerel_ses") or {}).get("uygulama") or "")
    tarayici = ya if ya in TARAYICILAR and yerel_ses_durum() in ("dinliyor", "bekliyor", "izin") else ""
    if not ek and not tarayici: return None  # tarayıcıda toplantı izi yok (yüz yüze, telefon, masaüstü uygulama): eklentinin işi değil
    if kod == "yok" and not ek and tarayici and tarayici not in ("Google Chrome", "Chrome"): return ("tarayici", tarayici)
    return (kod if kod != "yok" else "sekme", tarayici or "Chrome")
def ben_kopuk_view():
    now = time.time(); n = _ben_kopuk_neden()
    if not n:
        if _BK["yazildi"]: print(f"MİKROFON KANALI: düzeldi ({round(now - _BK['bas'])} sn kopuk kaldı)")
        _BK.update(bas=None, yazildi=False); return None
    if _BK["bas"] is None: _BK["bas"] = now
    sn = now - _BK["bas"]
    if sn < BEN_KOPUK_SN: return None
    if not _BK["yazildi"]: _BK["yazildi"] = True; print(f"MİKROFON KANALI: kopuk — {round(sn)} sn'dir senin sesin yazılmıyor (neden {n[0]}, uygulama {n[1]})")
    return {"sn": round(sn), "neden": n[0], "uygulama": n[1]}
def _veri_yok_dongu():  # /status yoklanmasa da günlüğe yazılsın
    while True:
        time.sleep(2 if os.environ.get("SUFLOR_TEST_HIZLI") else 5)
        try: veri_yok_view()
        except Exception as e: print(f"VERİ YOK: bakılamadı ({e.__class__.__name__})")
        try: STATE["ben_kopuk"] = ben_kopuk_view()  # /status dict(STATE) ile pano ve mini panoya gider
        except Exception as e: STATE["ben_kopuk"] = None; print(f"MİKROFON KANALI: bakılamadı ({e.__class__.__name__})")

def _kurulum_py():  # → (yol, cwd, ek_ortam): launchd altında Masaüstü'ndeki kod klasörü AÇILAMAZ (stat çalışır, open çalışmaz); o zaman uygulama klasöründeki kopya (aktarici-kur KOPYA'da)
    k = _kod_dir()
    if k:
        y = os.path.join(k, "kurulum.py")
        try: open(y, "rb").close(); return y, k, {}
        except OSError: pass
    u = str(AYAR.get("uygulama") or ""); y = os.path.join(u, "kurulum.py") if u else ""
    if y and os.path.isfile(y): return y, u, {"SUFLOR_KOD_OKUNAMAZ": "1"}
    return None, None, {}
DOGRULA = {"p": None, "t": 0.0}
def dogrula_oku():
    try: return json.load(open(os.path.join(AYAR["uygulama"], "dogrula.json"), encoding="utf-8"))
    except Exception: return None
def dogrula_istek(yenile=False):
    now = time.time(); p = DOGRULA["p"]; calisiyor = bool(p and p.poll() is None); ky, kc, ke = _kurulum_py()
    if yenile and not calisiyor:
        if not ky: return {"ok": False, "err": _t("Kurulum klasörü bulunamadı (ayar kod)", "Install folder not found (setting kod)")}
        if now - DOGRULA["t"] < 60: return dict(dogrula_oku() or {}, ok=True, calisiyor=False, bekle=round(60 - (now - DOGRULA["t"])))
        DOGRULA["t"] = now
        DOGRULA["p"] = subprocess.Popen([sys.executable, "-B", ky, "dogrula", "--json"], cwd=kc, env=dict(os.environ, **ke), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
        calisiyor = True
    d = dogrula_oku() or {}
    return dict(d, ok=True, var=bool(d), calisiyor=calisiyor)
