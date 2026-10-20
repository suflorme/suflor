# Suflor.me aktarıcı bölümü: Kullanıcı izni (v0.97.0; 20 Ekim güvenlik denetimi Y1/K1/Y2 — kullanıcı: "yetenekler kalsın, sesli ya da tık onayımı istesin").
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("izin")): AYAR, LOCK, CARDS, _t, add_card, eylem_ekle, _eylem_yama,
# soru_baslat, toplanti_var … import etme. Python 3.9 uyumlu.
# izin_iste(tur, ne, ayrinti) → eylem kuyruğunda "izin" işi (yerel: aktarıcı karar verir, toplantı oturumu sunmaz) + panoda onay kartı (Onayla / Reddet,
# yalnız anahtarlı pano) + toplantı dışında sesli soru ("İzin vereyim mi?" → Konuş'la evet/hayır). Karar eylem_karar → izin_karar ile gelir;
# izin_bekle(id, sn) bekler → "onaylandi" | "reddedildi" | "zaman_asimi". Kayıt canli/izin-kayit.jsonl (0600).
# Kullananlar: anahtarsız yazma isteği (Y1, kaynak başına bir kez; onay 12 sa geçerli), toplantı oturumunun riskli aracı (K1, toplanti-claude.py
# izin-kanca → /izin-iste), karşı tarafın sorusuna sesli cevap (Y2, bas-konus/otonom).
EYLEM_TUR["izin"] = "İzin"
EYLEM_SORU["izin"] = ("İzin vereyim mi?", "Shall I allow it?")
IZIN = {}            # id → {"olay": Event, "karar": None|str, "tur": str}
IZIN_KAYNAK = {}     # Y1: anahtarsız kaynak → {"durum": bekliyor|onaylandi|reddedildi, "t": zaman, "id": eylem id}
IZIN_KAYNAK_SN = 12 * 3600; IZIN_RED_SN = 30 * 60; IZIN_BEKLE_SN = 180
def _izin_kayit(o):
    yol = os.path.join(BASE, "izin-kayit.jsonl")
    if not os.path.exists(yol):
        try: os.close(os.open(yol, os.O_WRONLY | os.O_CREAT, 0o600))
        except OSError: pass
    with LOCK: write([(yol, json.dumps(dict(o, at=datetime.datetime.now().isoformat(timespec="seconds")), ensure_ascii=False) + "\n")])
def izin_iste(tur, ne, ayrinti=None, sesli=True):
    ne = " ".join(str(ne or "").split())[:300]
    x = eylem_ekle({"tur": "izin", "baslik": ne[:160], "ayrinti": json.dumps(dict(ayrinti or {}, izin=tur, ne=ne), ensure_ascii=False)})
    if not x: return None
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True)
    IZIN[x["id"]] = {"olay": threading.Event(), "karar": None, "tur": tur}
    c = add_card({"kind": "not", "text": _t(f"İzin: {ne}", f"Permission: {ne}"), "why": _t("Onayla ya da Reddet (yalnız sen).", "Approve or reject (you only)."), "onay": True})
    if c:
        with LOCK: c["eylem"] = x["id"]
    top = toplanti_var()
    if sesli and not top: soru_baslat([x["id"]])
    _izin_kayit({"id": x["id"], "tur": tur, "ne": ne, "durum": "bekliyor", "toplantida": top})
    print(f"İZİN: {tur} onay bekliyor ({'kart' if top or not sesli else 'kart + sesli'}) — \"{ne[:80]}\"")
    return x["id"]
def izin_karar(x, durum):  # eylem_karar'dan (yerel iş, tur izin): bağlı kartı kapat, bekleyeni uyandır
    with LOCK:
        for c in CARDS:
            if c.get("eylem") == x["id"] and c.get("status") == "acik": c["status"] = durum; c["acted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    i = IZIN.get(x["id"])
    if i: i["karar"] = durum; i["olay"].set()
    for k, v in IZIN_KAYNAK.items():
        if v.get("id") == x["id"]: v.update(durum=durum, t=time.time())
    _izin_kayit({"id": x["id"], "tur": (i or {}).get("tur"), "durum": durum, "kaynak": x.get("kaynak")})
def izin_bekle(iid, sn=IZIN_BEKLE_SN):
    i = IZIN.get(iid)
    if not i: return "zaman_asimi"
    i["olay"].wait(sn)
    return i["karar"] or "zaman_asimi"
# --- Y1: anahtarsız yazma isteği (geçiş listesi GECIS_YAZMA). Eski eklenti ya da başka bir yerel süreç (öbür macOS hesabı, başka eklenti, Teams
# sayfasındaki betik) anahtarsız yazabiliyordu: sahte satır, asistanı konuşturma, sahte onay kartı. Yetenek kalır; kaynak (köken) başına ilk istekte
# kullanıcıya sorulur, onaylanırsa 12 saat geçer, reddedilirse 30 dk sorulmaz. Onay gelene kadar istek işlenmez (403 "izin bekliyor").
def izin_anahtarsiz(yol, koken):
    k = koken or "yerel süreç (köken yok)"; v = IZIN_KAYNAK.get(k); now = time.time()
    if v and v["durum"] == "onaylandi" and now - v["t"] < IZIN_KAYNAK_SN: return True
    if v and v["durum"] == "bekliyor" and now - v["t"] < IZIN_BEKLE_SN * 10: return False
    if v and v["durum"] == "reddedildi" and now - v["t"] < IZIN_RED_SN: return False
    iid = izin_iste("anahtarsiz", _t(f"Anahtarsız istek: {k[:80]} → {yol}. Bu kaynak 12 saat yazabilsin mi?",
                                     f"Request without key: {k[:80]} → {yol}. Allow this source for 12 hours?"), {"koken": k, "yol": yol})
    IZIN_KAYNAK[k] = {"durum": "bekliyor", "t": now, "id": iid}
    return False
def izin_kaynak_view():
    now = time.time()
    return [{"koken": k, "durum": v["durum"], "age_s": round(now - v["t"])} for k, v in IZIN_KAYNAK.items() if now - v["t"] < IZIN_KAYNAK_SN] or None
# --- K1: toplantı oturumunun riskli aracı (Claude Code PreToolUse kancası: toplanti-claude.py izin-kanca → POST /izin-iste, anahtarlı). Kanca
# yalnız riskli araçlar için sorar; karar gelene kadar bekler (en çok IZIN_BEKLE_SN), cevap yoksa Claude Code kendi onay sorusuna düşer.
def izin_arac(p):
    arac = " ".join(str(p.get("arac") or "").split())[:80]; ozet = " ".join(str(p.get("ozet") or "").split())[:240]
    if not arac: return {"ok": False, "err": "arac"}
    iid = izin_iste("arac", _t(f"Toplantı oturumu: {arac} — {ozet}", f"Meeting session: {arac} — {ozet}"), {"arac": arac, "ozet": ozet})
    if not iid: return {"ok": False, "err": "eylem"}
    return {"ok": True, "id": iid, "karar": izin_bekle(iid, min(IZIN_BEKLE_SN, float(p.get("bekle") or IZIN_BEKLE_SN)))}
