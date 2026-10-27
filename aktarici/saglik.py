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
    return bool(toplanti_var() or OTO.get("aktif") or (STATE.get("masaustu") or {}).get("toplantida"))
def kanal_akiyor(k, sn=None): return time.time() - _VY["kanal"].get(k, 0) < (sn or VERI_YOK_SN)  # pano sağlığı: süreç değil, veri akıyor mu
def veri_yok_view():
    now = time.time()
    if not toplanti_suruyor():
        if _VY["yazildi"]: print("VERİ YOK: kalktı (toplantı bitti)")
        _VY.update(bas=None, yazildi=False); return None
    if _VY["bas"] is None: _VY["bas"] = now
    sn = now - max(_VY["bas"], _VY["son"])
    if sn < VERI_YOK_SN:
        if _VY["yazildi"]: print("VERİ YOK: kalktı (satır geldi)"); _VY["yazildi"] = False
        return None
    x = STATE.get("extension") or {}; w = STATE.get("whisper") or {}
    kanallar = {"altyazi": "acik" if (x.get("captions") or x.get("panel")) else "yok", "ben": ben_kod(), "karsi": yerel_ses_durum() if yerel_ses_durum() != "kapali" else ("web" if x.get("call") else "kapali"),
                "whisper": w.get("durum") or "yok"}
    if not _VY["yazildi"]:
        _VY["yazildi"] = True; print(f"VERİ YOK: toplantı sürüyor ama {round(sn)} sn'dir satır gelmiyor (altyazı {kanallar['altyazi']}, ben {kanallar['ben']}, karşı {kanallar['karsi']}, whisper {kanallar['whisper']})")
    return {"sn": round(sn), "kanallar": kanallar}
def _veri_yok_dongu():  # /status yoklanmasa da günlüğe yazılsın
    while True:
        time.sleep(2 if os.environ.get("SUFLOR_TEST_HIZLI") else 5)
        try: veri_yok_view()
        except Exception as e: print(f"VERİ YOK: bakılamadı ({e.__class__.__name__})")

DOGRULA = {"p": None, "t": 0.0}
def dogrula_oku():
    try: return json.load(open(os.path.join(AYAR["uygulama"], "dogrula.json"), encoding="utf-8"))
    except Exception: return None
def dogrula_istek(yenile=False):
    now = time.time(); p = DOGRULA["p"]; calisiyor = bool(p and p.poll() is None); k = _kod_dir()
    if yenile and not calisiyor:
        if not k or not os.path.isfile(os.path.join(k, "kurulum.py")): return {"ok": False, "err": _t("Kurulum klasörü bulunamadı (ayar kod)", "Install folder not found (setting kod)")}
        if now - DOGRULA["t"] < 60: return dict(dogrula_oku() or {}, ok=True, calisiyor=False, bekle=round(60 - (now - DOGRULA["t"])))
        DOGRULA["t"] = now
        DOGRULA["p"] = subprocess.Popen([sys.executable, "-B", os.path.join(k, "kurulum.py"), "dogrula", "--json"], cwd=k, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
        calisiyor = True
    d = dogrula_oku() or {}
    return dict(d, ok=True, var=bool(d), calisiyor=calisiyor)
