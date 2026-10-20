# Suflor.me aktarıcı bölümü: Toplantıda otonom katılım. Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("otonom")):
# KONUS, _KS, KANALLAR, toplantiya_soyle, ts_durdur, ts_sesli_kisim, TS, kulaklik, toplanti_var … diğer bölümlerin. import etme. Python 3.9 uyumlu.
# --- Otonom katılım (v0.56.0; S68 tasarımı, dış araştırma side-session-notes/…/adim4-otonom-arastirma.md) ----------------------------------------
# Biri (kullanıcı ya da karşı taraf) asistana adıyla seslenince konuşan süreç cevaplar; cevap kullanıcıya önce panoda gelir (kulaklıkta kısa uyarı sesi),
# OTONOM_ITIRAZ_SN içinde itiraz yoksa (panoda ✕, Option + Shift + S) söz sırası beklenir: akan kanalların hepsinde OTONOM_SESSIZ_SN sessizlik → cevabın
# sesli kısmı toplantıya okunur (toplantiya_soyle: web'de doğrudan, masaüstünde BlackHole). OTONOM_BEKLE_SN'de fırsat çıkmazsa yalnız panoda kalır
# ("söylenmedi"). Okurken biri OTONOM_KESME_SN konuşursa susar ve yeniden başlamaz. Cevap kulağa ayrıca okunmaz (iki kez okunur, soran bekler);
# toplantıya okunan ses kulaklıkta da duyulur. Ayar otonom (varsayılan kapalı); okumak için toplantiya_ses de açık olmalı (değilse panoda kalır).
# Araştırma önerisi (ölçüm değil): sessizlik 0,7–1,0 sn, fırsat yoksa 6–8 sn — başlangıç S68'in değerleri, ayarla kısaltılır (otonom_sessiz_sn, otonom_bekle_sn).
# S94 (kullanıcı, 19 Ekim): tek kural — adıyla seslenilen asistan herkese cevap verir; itiraz penceresi yok (0), ayar otonom kalktı: tek anahtar
# toplantiya_ses ("Asistanlar toplantıda konuşsun", asistan_toplanti). Durdurmak: "<Ad>, dur" / "sus" ya da Option + Shift + S (asistan_dur).
OTONOM_ITIRAZ_SN, OTONOM_SESSIZ_SN, OTONOM_BEKLE_SN, OTONOM_KESME_SN, OTONOM_GORUNUR_SN = 0.0, 1.5, 20.0, 1.0, 60.0
# 19 Ekim test toplantısı: okumaların hepsi 2–3 sn'de "biri konuştu" diye kesildi — kesen, karşı taraftan (aynı odadaki ikinci cihaz) geri gelen kendi sesimizdi.
# Kesme eşiği 0,3 → 1,0 sn ve kanaldaki ses, okunan sesin (TS["zarf"], 20 ms kareler) 0–OTONOM_YANKI_GECIKME_SN gecikmeli kopyasıyla açıklanıyorsa
# yankı sayılır; yalnız açıklanamayan ses (biz susarken konuşan) eşiği doldurursa okuma kesilir. Zarf yoksa (Mac sesi) eski sayım.
OTONOM_YANKI_GECIKME_SN, OTONOM_ARA_KARE = 1.5, 12  # ara kare: okunan sesin sessiz aralarına düşen ses (yankı oraya düşmez; üstümüze konuşan düşürür) ≥ 0,24 sn
def otonom_kesilsin(ts, zarf, t_bas, esik):  # → (kesilsin mi, son 3 sn'de açıklanamayan kare, gecikme ya da None)
    n, d = yanki_disi(ts, zarf, t_bas)
    if n >= esik: return True, n, d  # biz susarken ≥ esik ses, ya da yankı değil
    son = sum(1 for t in ts if t >= ts[-1] - 3.0) if ts else 0
    return (d is not None and n >= OTONOM_ARA_KARE and son >= esik), n, d  # üstümüze konuşma: son 3 sn'de ≥ esik ses ve bir kısmı aralarımızda
OT = {"id": None}; OT_K = threading.Lock()
OT_SON = ("iptal", "okundu", "kesildi", "soylenmedi", "okunamadi")
def otonom_acik(): return asistan_toplanti() and toplanti_var()  # S94: tek anahtar (moderatör de toplantiya_ses ister)
def _ot_ayar(ad, v):
    try: return max(0.0, float(AYAR.get(ad, v)))
    except (TypeError, ValueError): return v
def kanal_sessizlik():  # → sn: akan kanalların hepsinde son konuşma sesinden bu yana geçen (yakalanan sese göre); akan kanal yoksa None
    now = time.time(); s = []
    for ad, k in list(KANALLAR.items()):
        if now - STATE["whisper"]["kanallar"].get(ad, 0) > 3: continue  # bu kanal akmıyor
        if now - k.son_bitis > 1.5: s.append(0.0); continue  # parça gecikti: bilinmiyor → sessiz sayılmaz
        s.append(max(0.0, k.son_bitis - k.t_ses))
    return min(s) if s else None
def kanal_ses_sayaci(): return {ad: k.n_ses for ad, k in list(KANALLAR.items())}
def yanki_disi(ts, zarf, t_bas, kare=0.02, en_cok_gecikme=None, son_sn=3.0):
    # ts: kanalın sesli kare zamanları (okuma başından); zarf: okunan sesin kareleri (t_bas'tan). Gecikme bütün ts'ten bulunur (20 ms adım), açıklanamayan
    # (okunan ses o an sessizken gelen) kareler yalnız son son_sn içinde sayılır — uzun okumada küçük uyumsuzluk birikmesin. → (açıklanamayan kare, gecikme ya da None)
    if not ts: return 0, None
    son = [t for t in ts if t >= ts[-1] - son_sn]
    if not zarf: return len(son), None
    g_son = OTONOM_YANKI_GECIKME_SN if en_cok_gecikme is None else en_cok_gecikme
    def dolu(t):  # okunan ses t anında (±1 kare) sesli mi
        i = int((t - t_bas) / kare)
        return any(0 <= j < len(zarf) and zarf[j] for j in (i - 1, i, i + 1))
    eniyi, eniyi_d = -1, None
    for k in range(int(g_son / 0.02) + 1):  # 20 ms adımlarla gecikme ara
        d = k * 0.02; n = sum(1 for t in ts if dolu(t - d))
        if n > eniyi: eniyi, eniyi_d = n, d
    if eniyi < 0.6 * len(ts): return len(son), None  # okunan sesle örtüşmüyor: yankı değil, hepsi gerçek ses
    return sum(1 for t in son if not dolu(t - eniyi_d)), eniyi_d
def otonom_view():
    with OT_K: o = dict(OT)
    if not o.get("id") or (o.get("durum") in OT_SON and time.time() - o.get("t_durum", 0) > OTONOM_GORUNUR_SN): return None
    return {"id": o["id"], "durum": o["durum"], "metin": o.get("metin", "")[:400], "kim": o.get("kim"), "neden": o.get("neden"), "ad": o.get("ad"),
            "kalan": round(max(0.0, o.get("son", 0) - time.time()), 1) if o["durum"] == "itiraz" else None}
def _ot_gec(i, durum, **ek):  # id hâlâ bu ve bitmemişse durumu ilerletir
    with OT_K:
        if OT.get("id") != i or OT.get("durum") in OT_SON: return False
        OT.update(durum=durum, t_durum=time.time(), **ek); return True
def _ot_uyari():  # kullanıcıya: cevap hazır, 3 sn sonra toplantıya okunacak (yalnız kulaklıkta; hoparlörde mikrofona girerdi)
    if os.environ.get("SUFLOR_TEST_BASLAT") or not kulaklik(): return
    try: subprocess.Popen(["/usr/bin/afplay", "-v", "0.35", "/System/Library/Sounds/Tink.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError: pass
# v0.97.0 (güvenlik denetimi Y2; kullanıcı: "yetenekler kalsın, sesli ya da tık onayımı istesin"): karşı tarafın sorusuna cevap toplantıya okunmadan önce
# kullanıcının onayı — onay kartı (izin.py; pano, mini pano, Teams şeridi), panodaki asistan satırında "şimdi", ya da kendi kanalından "<Ad>, oku" (bas-konus.py
# ASISTAN_OKU_RX). KARSI_ONAY_SN içinde onay yoksa ya da reddedilirse okunmaz (panoda kalır). Ayar karsi_onay: false kapatır.
KARSI_ONAY_SN = 45.0
def otonom_onay_ver(karar="onaylandi", kaynak="ses"):  # bekleyen karşı taraf cevabı izni → karar; True: vardı
    with OT_K: iz = OT.get("izin") if OT.get("id") and OT.get("durum") not in OT_SON else None
    if not iz or IZIN.get(iz, {}).get("karar"): return False
    threading.Thread(target=eylem_karar, args=({"id": iz, "durum": karar}, kaynak), daemon=True).start(); return True  # ingest LOCK altında çağrılabilir (sesli onay)
def otonom_sun(cevap, kaynak, kim=None, ad=None):  # konuşanın cevabı hazır → (itiraz penceresi, S94'ten 0) → söz sırası → toplantıya; ad: konuşan asistan
    m = ts_sesli_kisim(cevap)
    if not m: return False
    i = secrets.token_hex(4); itz = _ot_ayar("otonom_itiraz_sn", OTONOM_ITIRAZ_SN)
    iz = None
    if kaynak == "karsi" and AYAR.get("karsi_onay", True) is not False and "izin_iste" in globals():
        iz = izin_iste("karsi_cevap", _t(f"{kim or 'Karşı taraf'} sordu; {ad or 'asistan'} toplantıya şunu okuyacak: «{m[:220]}» — okuyayım mı? (sesle: «{ad or 'Suflor'}, oku»)",
                                         f"{kim or 'The other side'} asked; {ad or 'the assistant'} will say in the meeting: «{m[:220]}» — read it? (by voice: «{ad or 'Suflor'}, read it»)"),
                       {"kim": kim, "ad": ad, "metin": m[:600]}, sesli=False)
        itz = max(itz, _ot_ayar("karsi_onay_sn", KARSI_ONAY_SN))
    with OT_K: OT.clear(); OT.update(id=i, metin=m, kaynak=kaynak, kim=kim, ad=ad, durum="itiraz", t=time.time(), t_durum=time.time(), son=time.time() + itz, **({"izin": iz} if iz else {}))
    if itz > 0: _ot_uyari()
    print(f"OTONOM: cevap hazır ({kaynak}{' · ' + kim if kim else ''}{' · ' + ad if ad else ''})" + (f" — {itz:.0f} sn itiraz penceresi" if itz > 0 else " — söz sırası bekleniyor"))
    threading.Thread(target=_ot_dongu, args=(i,), daemon=True).start(); return True
def otonom_karar(i, karar):  # panodan: iptal | simdi
    with OT_K:
        if not OT.get("id") or (i and OT["id"] != i) or OT.get("durum") in OT_SON: return {"ok": False, "err": _t("Bekleyen cevap yok", "No pending answer")}
        i = OT["id"]; d = OT["durum"]
    if OT.get("izin") and d == "itiraz":  # v0.97.0 (Y2): panodaki "şimdi" onay, ✕ red
        otonom_onay_ver("onaylandi" if karar == "simdi" else "reddedildi", "pano"); return {"ok": True}
    if karar == "simdi" and d in ("itiraz", "sira"): OT["simdi"] = True; print("OTONOM: 'şimdi söyle'"); return {"ok": True}
    if d == "okunuyor": ts_durdur()
    _ot_gec(i, "iptal", neden=_t("sen durdurdun", "you stopped it")); print(f"OTONOM: iptal ({d} sırasında)"); return {"ok": True}
def otonom_kisayol():  # Option + Shift + S: otonom cevap bekliyor ya da okunuyorsa durdurur (→ sonuç), yoksa None (eski davranış)
    with OT_K: d = OT.get("durum") if OT.get("id") else None
    if d not in ("itiraz", "sira", "okunuyor"): return None
    otonom_karar(None, "iptal"); return {"ok": True, "metin": _t("🔇 Toplantıya söylenmeyecek", "🔇 Won't be said in the meeting")}
def asistan_dur():  # S94: "<Ad>, dur" / "sus" ve Option + Shift + S — bekleyen ya da okunan cevap ve toplantıya okuma susar (moderatör sürer)
    r = otonom_kisayol()
    if ts_durdur(): print("ASİSTAN: sustu (okuma durdu)"); return {"ok": True, "metin": _t("🔇 Asistan sustu", "🔇 Assistant stopped")}
    return r or {"ok": True, "metin": _t("🔇 Okunan bir şey yok", "🔇 Nothing is being read")}
def _ot_dongu(i):
    iz = OT.get("izin")
    if iz:  # v0.97.0 (Y2): karşı tarafa cevap — kullanıcı onayı
        k = izin_bekle(iz, max(0.0, OT.get("son", 0) - time.time()))
        if k == "zaman_asimi": eylem_karar({"id": iz, "durum": "reddedildi"}, "zaman")  # kartı kapat
        if k != "onaylandi":
            _ot_gec(i, "soylenmedi" if k == "zaman_asimi" else "iptal", neden=_t("onay gelmedi", "no approval") if k == "zaman_asimi" else _t("onaylamadın", "you rejected it"))
            print(f"OTONOM: karşı tarafa cevap okunmadı ({'onay gelmedi' if k == 'zaman_asimi' else 'reddedildi'})"); return
        print("OTONOM: karşı tarafa cevap onaylandı — söz sırası bekleniyor"); OT["son"] = time.time()  # onay pencereyi kapatır; söz sırası kuralı sürer
    while time.time() < OT.get("son", 0) and not OT.get("simdi"):  # itiraz penceresi
        if OT.get("id") != i or OT.get("durum") != "itiraz": return
        time.sleep(0.1)
    if not _ot_gec(i, "sira"): return
    bas = time.time(); bek, ses = _ot_ayar("otonom_bekle_sn", OTONOM_BEKLE_SN), _ot_ayar("otonom_sessiz_sn", OTONOM_SESSIZ_SN)
    while True:  # söz sırası: akan kanalların hepsi sessiz
        if OT.get("id") != i or OT.get("durum") != "sira": return
        if not toplanti_var(): _ot_gec(i, "soylenmedi", neden=_t("toplantı bitti", "the meeting ended")); return
        s = kanal_sessizlik()
        if s is None: _ot_gec(i, "soylenmedi", neden=_t("toplantı sesi gelmiyor — söz sırası ölçülemedi", "no meeting audio — turn-taking unavailable")); print("OTONOM: kanal akmıyor — söylenmedi"); return
        if s >= ses or OT.get("simdi"): break
        if time.time() - bas >= bek: _ot_gec(i, "soylenmedi", neden=_t(f"{bek:.0f} sn içinde söz fırsatı çıkmadı", f"no opening within {bek:.0f} s")); print("OTONOM: fırsat çıkmadı — söylenmedi"); return
        time.sleep(0.1)
    if not _ot_gec(i, "okunuyor"): return
    print(f"OTONOM: söz sırası ({time.time() - bas:.1f} sn bekledi) — toplantıya okunuyor")
    r = toplantiya_soyle(OT["metin"])
    if not r.get("ok"): _ot_gec(i, "okunamadi", neden=str(r.get("err") or "?")); print(f"OTONOM: okunamadı ({r.get('err')})"); return
    t0 = time.time(); esik = int(_ot_ayar("otonom_kesme_sn", OTONOM_KESME_SN) / 0.02); zarf = TS.get("zarf"); son_bak = 0.0; yanki_yazildi = False  # 20 ms'lik kareler
    while time.time() < (TS.get("son_t") or 0) + 0.5:
        if OT.get("id") != i or OT.get("durum") != "okunuyor": return
        if time.time() - t0 >= 0.3 and time.time() - son_bak >= 0.25:  # okumanın başında önceki sözün kuyruğu sayılmasın; çeyrek saniyede bir bak
            son_bak = time.time()
            for ad, k in list(KANALLAR.items()):
                ts = [t for t in list(getattr(k, "ses_t", ())) if t >= t0 + 0.3]
                kes, n, d = otonom_kesilsin(ts, zarf[1] if zarf else None, zarf[0] if zarf else t0, esik)
                if kes:
                    ts_durdur(); _ot_gec(i, "kesildi", neden=_t("biri konuşmaya başladı", "someone started talking"))
                    print(f"OTONOM: biri konuştu ({ad}, {n * 0.02:.1f} sn yankıyla açıklanmayan ses) — okuma durdu, yeniden başlamayacak"); return
                if d is not None and len(ts) >= esik and not yanki_yazildi:
                    yanki_yazildi = True; print(f"OTONOM: {ad} kanalında kendi sesimizin yankısı (~{d:.2f} sn gecikme) — okuma sürüyor")
        time.sleep(0.05)
    _ot_gec(i, "okundu"); print("OTONOM: toplantıya okundu")
