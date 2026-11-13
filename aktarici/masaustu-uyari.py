# --- Masaüstü toplantı kartları (13 Kasım, kullanıcı: masaüstü Teams'te "eklenti neden çalışmıyor" sorusu ve BlackHole seçilmeden konuşamayan asistan) ----
# 1) Bilgi kartı: masaüstü toplantı (Teams/Zoom uygulaması) sürerken toplantı başına bir kez — tarayıcı eklentisi gerekmez, döküm masaüstü yardımcılarından.
# 2) BlackHole uyarısı: ayar toplantiya_ses açıkken menü uygulaması (OrtakMik, --ortak-mik) ~10 sn'de bir ve değişince POST /ortak-mik
#    {bh_var, bh_okunuyor, gecis} bildirir: bh_okunuyor = bu uygulamadan başka bir süreç BlackHole'dan ses okuyor (Teams'te mikrofon "BlackHole 2ch").
#    Masaüstü toplantı OM_TOPLANTI_SN'dir sürüyor, kullanıcının mikrofonu toplantıda açık, rapor taze (< OM_TAZE_SN) ve BlackHole OM_OKUNMUYOR_SN'dir
#    okunmuyorsa toplantı başına bir kez kart: asistan konuşursa karşı taraf duymaz. Rapor hiç gelmiyorsa (menü uygulaması --ortak-mik'siz ya da eski) kart
#    yok, günlüğe toplantı başına tek satır. Gizli toplantıda kart yok. Karar _toplanti_dongu'dan (toplanti.py) her turda masaustu_uyari_bak() ile.
_OM_TH = bool(os.environ.get("SUFLOR_TEST_HIZLI"))
OM_TOPLANTI_SN, OM_OKUNMUYOR_SN, OM_TAZE_SN = (4, 3, 10) if _OM_TH else (60, 45, 30)
OM = {"t": 0.0, "bh_var": None, "bh_okunuyor": None, "gecis": None, "t_okunmuyor": None}
MU = {"uyari": None, "bilgi": None, "rapor_yok": None, "bh_yok": None}  # toplantı kimliği: o toplantıda kart/günlük satırı verildi
def ortak_mik_al(p):  # POST /ortak-mik (menü uygulaması, anahtarla)
    om = OM; now = time.time()
    bh_var = p.get("bh_var") is not False; okunuyor = bool(p.get("bh_okunuyor")) and bh_var; gecis = bool(p.get("gecis"))
    if (okunuyor, gecis, bh_var) != (om["bh_okunuyor"], om["gecis"], om["bh_var"]):
        print(f"ORTAK MİK: BlackHole {'yok' if not bh_var else 'okunuyor' if okunuyor else 'okunmuyor'} · geçiş {'açık' if gecis else 'kapalı'}")
    if okunuyor: om["t_okunmuyor"] = None
    elif om["t_okunmuyor"] is None or now - om["t"] > OM_TAZE_SN: om["t_okunmuyor"] = now  # rapor kesilip döndüyse süre baştan
    om.update(t=now, bh_var=bh_var, bh_okunuyor=okunuyor, gecis=gecis)
    return {"ok": True}
def masaustu_uygulamada():  # süren toplantı masaüstü uygulamasında: menü uygulaması toplantıda görüyor ya da mikrofonu tutan uygulama Teams/Zoom (tarayıcı değil)
    if eklenti_cagri(): return False
    if masaustu_toplantida(): return True
    y = STATE.get("yerel_ses") or {}
    return y.get("uygulama") in MASAUSTU_PLATFORM and yerel_ses_durum() == "dinliyor"
def _mu_platform():
    u = (STATE.get("masaustu") or {}).get("uygulama") or (STATE.get("yerel_ses") or {}).get("uygulama") or ""
    return MASAUSTU_PLATFORM.get(u, "bilinmeyen")
def _mu_mik_acik(now):  # kullanıcının mikrofonu toplantıda açık: Teams "sessiz değil" diyor, ya da bilinmiyor ve menü uygulamasının mikrofonu ses veriyor
    s = (STATE.get("masaustu") or {}).get("sessiz")
    return s is False or (s is None and now - (STATE.get("masaustu_mic") or {}).get("son", 0) < 10)
def masaustu_uyari_bak():
    try: _masaustu_uyari_bak()
    except Exception as e: print(f"MASAÜSTÜ UYARI: hata ({e.__class__.__name__}: {str(e)[:120]})")
def _masaustu_uyari_bak():
    a = TOPLANTI.get("aktif"); now = time.time()
    if not a or a.get("durum") != "suruyor" or gizli_acik() or not masaustu_uygulamada(): return
    k = a["id"]; pl = _mu_platform(); ad = PLATFORM_AD.get(pl, "") if pl != "bilinmeyen" else ""
    if MU["bilgi"] != k:
        MU["bilgi"] = k
        add_card({"kind": "not", "text": _t(f"Masaüstü {ad or 'uygulama'} toplantısı: tarayıcı eklentisi gerekmez", f"Desktop {ad or 'app'} meeting: no browser extension needed"),
                  "why": _t("Döküm Suflor.me'nin masaüstü yardımcılarından gelir (karşı tarafın sesi, senin mikrofonun, açıksa altyazı); eklentinin çalışmaması sorun değil.",
                            "The transcript comes from Suflor.me's desktop helpers (the other side's audio, your microphone, captions if on); the extension not running is fine.")})
        print(f"MASAÜSTÜ UYARI: bilgi kartı — masaüstü toplantı, eklenti gerekmez ({a['dosya']})")
    if AYAR.get("toplantiya_ses") is not True or MU["uyari"] == k or now - a["t0"] < OM_TOPLANTI_SN or not _mu_mik_acik(now): return
    om = OM
    if now - om["t"] >= OM_TAZE_SN:
        if MU["rapor_yok"] != k: MU["rapor_yok"] = k; print("MASAÜSTÜ UYARI: menü uygulamasından BlackHole raporu yok (--ortak-mik kapalı ya da eski sürüm) — Teams mikrofonu denetlenemiyor, kart yok")
        return
    if not om["bh_var"]:
        if MU["bh_yok"] != k: MU["bh_yok"] = k; print("MASAÜSTÜ UYARI: BlackHole aygıtı yok — toplantıya sesli söyle çalışmaz, kart yok")
        return
    if om["bh_okunuyor"] or om["t_okunmuyor"] is None or now - om["t_okunmuyor"] < OM_OKUNMUYOR_SN: return
    MU["uyari"] = k; asi = asistan_ad()
    yol = _t('Teams → Ayarlar → Cihazlar → Mikrofon: "BlackHole 2ch" seç.', 'Teams → Settings → Devices → Microphone: choose "BlackHole 2ch".') if pl == "teams" else \
          _t('Toplantı uygulamasının ses ayarlarında mikrofon olarak "BlackHole 2ch" seç.', 'In the meeting app\'s audio settings, choose "BlackHole 2ch" as the microphone.')
    add_card({"kind": "not", "text": _t(f"{ad or 'Toplantı uygulaması'} mikrofonu BlackHole değil — {asi} konuşursa karşı taraf duymaz",
                                        f"{ad or 'Meeting app'} microphone isn't BlackHole — if {asi} speaks, the others won't hear"), "why": yol})
    print(f"MASAÜSTÜ UYARI: BlackHole {round(now - om['t_okunmuyor'])} sn'dir okunmuyor — uyarı kartı ({a['dosya']})")
