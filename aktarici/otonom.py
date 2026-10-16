# Suflor.me aktarıcı bölümü: Toplantıda otonom katılım. Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("otonom")):
# KONUS, _KS, KANALLAR, toplantiya_soyle, ts_durdur, ts_sesli_kisim, TS, kulaklik, toplanti_var … diğer bölümlerin. import etme. Python 3.9 uyumlu.
# --- Otonom katılım (v0.56.0; S68 tasarımı, dış araştırma side-session-notes/…/adim4-otonom-arastirma.md) ----------------------------------------
# Biri (kullanıcı ya da karşı taraf) asistana adıyla seslenince konuşan süreç cevaplar; cevap kullanıcıya önce panoda gelir (kulaklıkta kısa uyarı sesi),
# OTONOM_ITIRAZ_SN içinde itiraz yoksa (panoda ✕, Option + Shift + S) söz sırası beklenir: akan kanalların hepsinde OTONOM_SESSIZ_SN sessizlik → cevabın
# sesli kısmı toplantıya okunur (toplantiya_soyle: web'de doğrudan, masaüstünde BlackHole). OTONOM_BEKLE_SN'de fırsat çıkmazsa yalnız panoda kalır
# ("söylenmedi"). Okurken biri OTONOM_KESME_SN konuşursa susar ve yeniden başlamaz. Cevap kulağa ayrıca okunmaz (iki kez okunur, soran bekler);
# toplantıya okunan ses kulaklıkta da duyulur. Ayar otonom (varsayılan kapalı); okumak için toplantiya_ses de açık olmalı (değilse panoda kalır).
# Araştırma önerisi (ölçüm değil): sessizlik 0,7–1,0 sn, fırsat yoksa 6–8 sn — başlangıç S68'in değerleri, ayarla kısaltılır (otonom_sessiz_sn, otonom_bekle_sn).
OTONOM_ITIRAZ_SN, OTONOM_SESSIZ_SN, OTONOM_BEKLE_SN, OTONOM_KESME_SN, OTONOM_GORUNUR_SN = 3.0, 1.5, 20.0, 0.3, 60.0
OT = {"id": None}; OT_K = threading.Lock()
OT_SON = ("iptal", "okundu", "kesildi", "soylenmedi", "okunamadi")
def otonom_acik(): return AYAR.get("otonom") is True and toplanti_var() and AYAR.get("konusma", True) is not False
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
def otonom_view():
    with OT_K: o = dict(OT)
    if not o.get("id") or (o.get("durum") in OT_SON and time.time() - o.get("t_durum", 0) > OTONOM_GORUNUR_SN): return None
    return {"id": o["id"], "durum": o["durum"], "metin": o.get("metin", "")[:400], "kim": o.get("kim"), "neden": o.get("neden"),
            "kalan": round(max(0.0, o.get("son", 0) - time.time()), 1) if o["durum"] == "itiraz" else None}
def _ot_gec(i, durum, **ek):  # id hâlâ bu ve bitmemişse durumu ilerletir
    with OT_K:
        if OT.get("id") != i or OT.get("durum") in OT_SON: return False
        OT.update(durum=durum, t_durum=time.time(), **ek); return True
def _ot_uyari():  # kullanıcıya: cevap hazır, 3 sn sonra toplantıya okunacak (yalnız kulaklıkta; hoparlörde mikrofona girerdi)
    if os.environ.get("SUFLOR_TEST_BASLAT") or not kulaklik(): return
    try: subprocess.Popen(["/usr/bin/afplay", "-v", "0.35", "/System/Library/Sounds/Tink.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError: pass
def otonom_sun(cevap, kaynak, kim=None):  # konuşanın cevabı hazır → itiraz penceresi başlar
    m = ts_sesli_kisim(cevap)
    if not m: return False
    i = secrets.token_hex(4)
    with OT_K: OT.clear(); OT.update(id=i, metin=m, kaynak=kaynak, kim=kim, durum="itiraz", t=time.time(), t_durum=time.time(), son=time.time() + _ot_ayar("otonom_itiraz_sn", OTONOM_ITIRAZ_SN))
    _ot_uyari(); print(f"OTONOM: cevap hazır ({kaynak}{' · ' + kim if kim else ''}) — {_ot_ayar('otonom_itiraz_sn', OTONOM_ITIRAZ_SN):.0f} sn itiraz penceresi")
    threading.Thread(target=_ot_dongu, args=(i,), daemon=True).start(); return True
def otonom_karar(i, karar):  # panodan: iptal | simdi
    with OT_K:
        if not OT.get("id") or (i and OT["id"] != i) or OT.get("durum") in OT_SON: return {"ok": False, "err": _t("Bekleyen cevap yok", "No pending answer")}
        i = OT["id"]; d = OT["durum"]
    if karar == "simdi" and d in ("itiraz", "sira"): OT["simdi"] = True; print("OTONOM: 'şimdi söyle'"); return {"ok": True}
    if d == "okunuyor": ts_durdur()
    _ot_gec(i, "iptal", neden=_t("sen durdurdun", "you stopped it")); print(f"OTONOM: iptal ({d} sırasında)"); return {"ok": True}
def otonom_kisayol():  # Option + Shift + S: otonom cevap bekliyor ya da okunuyorsa durdurur (→ sonuç), yoksa None (eski davranış)
    with OT_K: d = OT.get("durum") if OT.get("id") else None
    if d not in ("itiraz", "sira", "okunuyor"): return None
    otonom_karar(None, "iptal"); return {"ok": True, "metin": _t("🔇 Toplantıya söylenmeyecek", "🔇 Won't be said in the meeting")}
def _ot_dongu(i):
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
    t0 = time.time(); n0 = None; esik = int(_ot_ayar("otonom_kesme_sn", OTONOM_KESME_SN) / 0.02)  # 20 ms'lik kareler
    while time.time() < (TS.get("son_t") or 0) + 0.5:
        if OT.get("id") != i or OT.get("durum") != "okunuyor": return
        if time.time() - t0 >= 0.3:  # okumanın başında önceki sözün kuyruğu sayılmasın
            n = kanal_ses_sayaci()
            if n0 is None: n0 = n
            elif any(v - n0.get(ad, 0) >= esik for ad, v in n.items()):
                ts_durdur(); _ot_gec(i, "kesildi", neden=_t("biri konuşmaya başladı", "someone started talking")); print("OTONOM: biri konuştu — okuma durdu, yeniden başlamayacak"); return
        time.sleep(0.05)
    _ot_gec(i, "okundu"); print("OTONOM: toplantıya okundu")
