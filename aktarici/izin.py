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
def izin_iste(tur, ne, ayrinti=None, sesli=True, oturum=False):
    # oturum=True (v0.115.0; kullanıcı 22 Ekim: arka plandaki toplantı oturumunun araç izni ayrı kart olmasın): kart açılmaz — panonun Claude bölümünde
    # ve mini panoda Onayla / Reddet (toplanti_oturum_view "izinler"); karar yine eylem_karar → izin_karar. Toplantı dışında sesli soru aynı.
    ne = " ".join(str(ne or "").split())[:400]
    x = eylem_ekle({"tur": "izin", "baslik": ne[:160], "ayrinti": json.dumps(dict(ayrinti or {}, izin=tur, ne=ne), ensure_ascii=False)})
    if not x: return None
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True, **({"oturum": True} if oturum else {}))
    IZIN[x["id"]] = {"olay": threading.Event(), "karar": None, "tur": tur}
    if not oturum:
        c = add_card({"kind": "not", "text": _t(f"İzin: {ne}", f"Permission: {ne}"), "why": _t("Onayla ya da Reddet (yalnız sen).", "Approve or reject (you only)."), "onay": True})
        if c:
            with LOCK: c["eylem"] = x["id"]
    else: kart_bildir()
    top = toplanti_var()
    if sesli and not top: soru_baslat([x["id"]])
    _izin_kayit({"id": x["id"], "tur": tur, "ne": ne, "durum": "bekliyor", "toplantida": top})
    print(f"İZİN: {tur} onay bekliyor ({'Claude bölümü' if oturum else 'kart'}{' + sesli' if sesli and not top else ''}) — \"{ne[:80]}\"")
    return x["id"]
def izin_bekleyen_oturum():  # panonun Claude bölümü ve mini pano: arka plandaki toplantı oturumunun onay bekleyen araç izinleri
    return [{"id": x["id"], "metin": x["baslik"]} for x in eylem_gorunen() if x["tur"] == "izin" and x.get("oturum") and x["durum"] == "bekliyor"]
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
    if not i["karar"]: izin_sure_doldu(iid)
    return i["karar"] or "zaman_asimi"
def izin_sure_doldu(iid):  # v0.112.2 (22 Ekim: süresi dolan kart açık kaldı, kullanıcı onu onayladı — bekleyen yoktu, oturum ikinci kart açtı): kart ve iş kapanır
    with LOCK:
        for c in CARDS:
            if c.get("eylem") == iid and c.get("status") == "acik": c["status"] = "zaman_asimi"; c["acted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        for x in EYLEMLER:
            if x["id"] == iid and x["durum"] == "bekliyor": _eylem_yama(x, durum="zaman_asimi")
    if SORU.get("aktif") == iid: soru_sonraki()
    _izin_kayit({"id": iid, "durum": "zaman_asimi"}); print(f"İZİN: {iid} süre doldu — kart kapandı")
# v0.112.2 (kullanıcı, 22 Ekim: "Kodu göstermenin bir anlamı yok, kafam karışıyor. Bana düz metin şeklinde şunu yapmak istiyorum onaylıyor musun gibi sor"):
# araç izninde kartta komut/JSON yok — Claude'un yazdığı açıklama (Bash/Monitor description; toplantı oturumuna Türkçe düz cümle yazması söylenir) ya da
# araç türünden kurulan cümle. Komutun kendisi yalnız izin-kayit.jsonl ve eylem ayrıntısında.
IZIN_MCP_CUMLE = [  # (araç adı kalıbı, Türkçe, İngilizce) — ilk eşleşen
    (r"create_draft|draft", "e-posta taslağı hazırlamak", "prepare an email draft"), (r"reply", "e-postaya cevap göndermek", "send an email reply"),
    (r"forward", "bir e-postayı iletmek", "forward an email"), (r"send", "ileti ya da e-posta göndermek", "send a message or email"),
    (r"create_event", "takvime etkinlik eklemek", "add a calendar event"), (r"update_event", "takvimdeki bir etkinliği değiştirmek", "change a calendar event"),
    (r"delete_event", "takvimden bir etkinliği silmek", "delete a calendar event"), (r"respond_to_event", "bir davete cevap vermek", "respond to an invitation"),
    (r"set_vacation", "e-posta otomatik yanıtını ayarlamak", "set the email auto-reply"), (r"create_filter", "e-posta kuralı eklemek", "add an email rule"),
    (r"label_", "e-postaları etiketlemek", "label emails"), (r"trash|delete", "bir şeyi silmek", "delete something"), (r"share_file", "bir dosyayı paylaşmak", "share a file"),
    (r"upload|create_file|update_file|copy_file|move_item|rename_item", "bulut dosyalarında değişiklik yapmak", "change cloud files"),
    (r"navigate", "tarayıcıda bir sayfa açmak", "open a page in the browser"), (r"javascript|computer|form_input|file_upload", "tarayıcıda işlem yapmak", "act in the browser")]
def izin_metni(arac, gi=None, aciklama=None):
    return _t(f"Claude şunu yapmak istiyor: {arac_cumlesi(arac, gi, aciklama)}. Onaylıyor musun?", f"Claude wants to: {arac_cumlesi(arac, gi, aciklama)}. Do you approve?")
def arac_cumlesi(arac, gi=None, aciklama=None):  # aracın düz cümlesi ("… dosyasını okumak"): izin metni ve toplantı oturumunun canlı durum satırı
    gi = gi if isinstance(gi, dict) else {}; a = str(arac or ""); kisa = a.split("__")[-1]
    acik = " ".join(str(aciklama or gi.get("description") or "").split()).rstrip(" .")[:200]
    if a in ("Bash", "Monitor") or a.startswith("Bash"):
        ne = acik or _t("bilgisayarda bir komut çalıştırmak", "run a command on this Mac")
    elif a.startswith("mcp__"):
        m = next(((tr, en) for k, tr, en in IZIN_MCP_CUMLE if re.search(k, kisa, re.I)), None)
        ne = _t(m[0], m[1]) if m else _t(f"“{kisa}” aracını kullanmak", f"use the “{kisa}” tool")
        alici = gi.get("to") or gi.get("recipient") or gi.get("recipients"); konu = gi.get("subject") or gi.get("summary") or gi.get("title")
        if isinstance(alici, list): alici = ", ".join(str(x) for x in alici[:3])
        ek = ", ".join(x for x in [(_t("alıcı: ", "to: ") + " ".join(str(alici).split())[:80]) if alici else "", (_t("konu: ", "subject: ") + " ".join(str(konu).split())[:80]) if konu else ""] if x)
        if ek: ne += f" ({ek})"
    elif a in ("Write", "Edit", "NotebookEdit"): ne = _t(f"“{os.path.basename(str(gi.get('file_path') or gi.get('notebook_path') or ''))}” dosyasını değiştirmek", f"change the file “{os.path.basename(str(gi.get('file_path') or gi.get('notebook_path') or ''))}”")
    elif a == "Read": ne = _t(f"“{os.path.basename(str(gi.get('file_path') or ''))}” dosyasını okumak", f"read the file “{os.path.basename(str(gi.get('file_path') or ''))}”")
    elif a in ("WebFetch", "WebSearch"):
        alan = re.sub(r"^https?://([^/]+).*", r"\1", str(gi.get("url") or ""))
        ne = _t("internetten bilgi almak", "look something up on the internet") + (f" ({alan})" if alan else "")
    elif a in ("Grep", "Glob"): ne = acik or _t("dosyalarda aramak", "search the files")
    elif a == "TodoWrite": ne = _t("yapılacaklar listesini güncellemek", "update the to-do list")
    else: ne = acik or _t(f"“{kisa}” aracını kullanmak", f"use the “{kisa}” tool")
    return ne
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
    arka = "topo_canli" in globals() and topo_canli()  # arka plandaki oturumun kancası: izin Claude bölümünde (kart değil)
    iid = izin_iste("arac", izin_metni(p.get("ad") or arac, p.get("girdi"), p.get("aciklama")), {"arac": arac, "ozet": ozet}, oturum=arka)  # komut yalnız ayrıntıda/kayıtta
    if not iid: return {"ok": False, "err": "eylem"}
    k = izin_bekle(iid, min(IZIN_BEKLE_SN, float(p.get("bekle") or IZIN_BEKLE_SN)))
    return {"ok": True, "id": iid, "karar": k, "arka": arka}
