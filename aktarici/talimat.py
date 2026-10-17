# Suflor.me aktarıcı bölümü: Sesle oturuma talimat ve yapılacak (v0.75.0). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır
# (bolum("talimat")): AYAR, BASE, LOCK, write, _t, eylem_ekle, eylem_karar, soru_baslat, add_card, CARDS, toplanti_var, eposta_tur, eposta_ben … diğer
# bölümlerin. import etme. Python 3.9 uyumlu.
# Kullanıcının KENDİ sözü (bas-konuş, sohbet, toplantıda kendi kanalındaki hitap; karşı taraf ve otonom değil) Claude'a gitmeden yakalanır:
#   "<hedef kalıbı> (şunu) ilet/söyle/yaz/gönder/bildir: <ileti>"  → eylem kuyruğunda "oturum" işi
#   "yapılacaklarıma ekle: <iş>"                                    → eylem kuyruğunda "yapilacak" işi
# Onay: toplantı dışında sesli geri okuma + "İleteyim mi?" (evet/hayır, 10 sn Geri al); toplantıda onay kartı (Onayla / Reddet) — sesle okunmaz.
# Onaylanınca aktarıcı uygular (Claude değil): oturum → canli/gelen/<hedef>.jsonl (0600); hedef oturumun kancası (toplanti-claude.py gelen --hedef <ad>)
# okunmamışları bağlama ekler (oturumu uyandırmaz, kullanıcı o oturuma yazınca görünür). Yapılacak → kullanıcının kendi adresine e-posta taslağı (ayar eposta;
# toplantıdaysa toplantı bitince açılır; gönderiyi kullanıcı yapar). Her iş canli/talimat-kayit.jsonl'e yazılır.
# Hedefler ayar "talimat_hedefler": [{"ad": "proje", "etiket": "proje oturumu", "kalip": ["proje oturumuna", …]}, …]; yoksa yalnız "proje". Geliştirme
# oturumu gibi kullanıcıya özel hedefler yalnız kullanıcının ayarında durur. Ayar "talimat": false kapatır.
import urllib.parse
TALIMAT_FIIL = r"(?:ilet|söyle|soyle|yaz|gönder|gonder|bildir|aktar|not\s+düş|not\s+dus|talimat\s+ver|haber\s+ver)\w*"
TALIMAT_NESNE = r"(?:bildirim|mesaj|ileti|not|talimat|haber|hatırlatma)\w*\s+"  # v0.77.1
YAPILACAK_RX = re.compile(r"(?:yapılacaklar(?:ıma|ımı|ım|a)?|yapılacak\s+listeme|yapılacak\s+listesine|yapılacaklar\s+listeme|yapılacaklar\s+listesine|to-?do(?:\s+listeme|\s+listesine)?)"
                          r"\s+(?:olarak\s+)?(?:ekle|yaz|koy|kaydet|at)\w*\s*[:,.;\-]?\s*(?P<m>.*)$", re.I | re.S)
TALIMAT_EN_COK, TALIMAT_SAAT_SINIR = 1000, 20  # ileti uzunluğu; hedef başına saatte en çok
_TAL = {"t": {}}
def talimat_hedefler():
    h = AYAR.get("talimat_hedefler")
    if isinstance(h, list) and h:
        out = [x for x in h if isinstance(x, dict) and re.fullmatch(r"[a-z0-9-]{1,24}", str(x.get("ad") or "")) and x.get("kalip")]
        if out: return out
    return [{"ad": "proje", "etiket": _t("proje oturumu", "project session"), "kalip": ["proje oturumuna", "proje oturumuna da", "ana oturuma", "project session"]}]
def _talimat_temiz(m): return " ".join(str(m or "").split()).strip(" ,.;:-")
def talimat_coz(metin):  # → ("oturum", hedef, ileti) | ("yapilacak", None, iş) | None
    if AYAR.get("talimat") is False or not metin: return None
    _kb, m = kisilik_hitap_bul(metin) if "kisilik_hitap_bul" in globals() else (None, metin)
    m = re.sub(r"^\W*(claude|suflor|süflör)\W+", "", m.strip(), flags=re.I)
    y = YAPILACAK_RX.search(m)
    if y:
        is_ = _talimat_temiz(y.group("m")) or _talimat_temiz(re.sub(r"\b(bunu|şunu|sunu)\b", "", m[:y.start()], flags=re.I))
        return ("yapilacak", None, is_[:TALIMAT_EN_COK]) if len(is_.split()) >= 2 else None
    for h in talimat_hedefler():
        k = "|".join(re.escape(x) for x in sorted(h["kalip"], key=len, reverse=True))
        # v0.77.1 (ilk gerçek deneme): "bildirim gönderir misin? <ileti>" — nesne sözcüğü (bildirim, mesaj …) ve soru eki fiil sayılmaz, ileti sonrasıdır
        r = re.search(r"(?:" + k + r")\s+(?:de\s+|da\s+)?(?:şunu\s+|sunu\s+|bunu\s+)?(?:bir\s+)?(?:" + TALIMAT_NESNE + r")?" + TALIMAT_FIIL +
                      r"(?:\s+m[iıuü](?:s[iıuü]n|y[iıuü]z|s[iıuü]n[iıuü]z)?)?\s*[:,.;?!\-]*\s*(?P<m>.*)$", m, re.I | re.S)
        if not r: continue
        ileti = _talimat_temiz(r.group("m")) or _talimat_temiz(re.sub(r"\b(bunu|şunu|sunu)\b", "", m[:r.start()], flags=re.I))
        if len(ileti.split()) < 2: return None
        return ("oturum", h, ileti[:TALIMAT_EN_COK])
    return None
def _talimat_kayit(o):
    yol = os.path.join(BASE, "talimat-kayit.jsonl")
    if not os.path.exists(yol):
        try: os.close(os.open(yol, os.O_WRONLY | os.O_CREAT, 0o600))
        except OSError: pass
    with LOCK: write([(yol, json.dumps(dict(o, at=datetime.datetime.now().isoformat(timespec="seconds")), ensure_ascii=False) + "\n")])
def talimat_yakala(metin, kaynak):  # kullanıcının kendi sözü → True: talimat/yapılacak olarak alındı (Claude'a gitmez)
    c = talimat_coz(metin)
    if not c: return False
    tur, h, ileti = c; top = toplanti_var()
    if tur == "oturum":
        n = [t for t in _TAL["t"].get(h["ad"], []) if time.time() - t < 3600]
        if len(n) >= TALIMAT_SAAT_SINIR:
            cevap = _t("Bu saatte o oturuma çok ileti gitti; biraz sonra.", "Too many messages to that session this hour; later."); _konus_kur(durum="hazir", soru=metin, cevap=cevap)
            if not top: seslendir(cevap, kuyruk=True)
            return True
        etiket = str(h.get("etiket") or h["ad"])
    x = eylem_ekle({"tur": tur, "baslik": ileti[:160], "ayrinti": json.dumps({"hedef": h["ad"] if h else None, "etiket": etiket if h else None, "metin": ileti,
                                                                            "duyulan": metin[:TALIMAT_EN_COK], "kaynak": kaynak, "toplantida": top}, ensure_ascii=False)})
    if not x: return False
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True)  # toplantı oturumu (Claude) bu işi uygulamaz, sunmaz
    _talimat_kayit({"id": x["id"], "tur": tur, "hedef": h["ad"] if h else None, "metin": ileti, "durum": "bekliyor", "kaynak": kaynak, "toplantida": top})
    ne = (_t(f"{etiket}na ileti", f"message to the {etiket}") if tur == "oturum" else _t("yapılacak (e-posta)", "to-do (email)"))
    if top:  # toplantıda: onay kartı, sesle okunmaz (kullanıcı)
        c_ = add_card({"kind": "not", "text": _t(f"Onay: {ne} — «{ileti[:300]}»", f"Approve: {ne} — «{ileti[:300]}»"), "why": _t("Sesle verdiğin talimat; Onayla ya da Reddet.", "Your spoken instruction; approve or reject."), "onay": True})
        if c_:
            with LOCK: c_["eylem"] = x["id"]
        cevap = _t("Onay kartı panoda.", "Approval card on the panel.")
    else:
        soru_baslat([x["id"]]); cevap = _t(f"{ne}: «{ileti[:200]}» — onay bekliyor.", f"{ne}: «{ileti[:200]}» — waiting for approval.")
    _konus_kur(durum="hazir", soru=metin, cevap=cevap, hata=None, olcum=None)
    print(f"TALİMAT: {tur}{(' → ' + h['ad']) if h else ''} onay bekliyor ({'kart' if top else 'sesli'}) — \"{ileti[:60]}\"")
    return True
def talimat_karar(x, durum):  # eylem_karar'dan: yerel iş onaylandı/reddedildi → (Geri al süresinden sonra) uygula; bağlı onay kartını kapat
    with LOCK:
        for c in CARDS:
            if c.get("eylem") == x["id"] and c.get("status") == "acik": c["status"] = durum; c["acted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    if durum != "onaylandi": _talimat_kayit({"id": x["id"], "tur": x["tur"], "durum": "reddedildi"}); return
    threading.Thread(target=_talimat_uygula, args=(x["id"],), daemon=True).start()
def _talimat_uygula(eid):
    with LOCK: x = next((x for x in EYLEMLER if x["id"] == eid), None)
    if not x: return
    if x.get("kaynak") == "ses": time.sleep(GERI_AL_SN + 0.5)  # sesli kararın Geri al'ı
    with LOCK:
        if x["durum"] != "onaylandi": return
    try: a = json.loads(x.get("ayrinti") or "{}")
    except ValueError: a = {}
    if x["tur"] == "oturum": ok, sonuc = _gelen_yaz(eid, a)
    else:
        while toplanti_var(): time.sleep(20)  # toplantıda tarayıcıda taslak açılmasın
        ok, sonuc = _yapilacak_taslak(a)
    eylem_sonuc({"id": eid, "durum": "yapildi" if ok else "hata", "sonuc": sonuc})
    _talimat_kayit({"id": eid, "tur": x["tur"], "hedef": a.get("hedef"), "durum": "yapildi" if ok else "hata", "sonuc": sonuc})
    print(f"TALİMAT: {eid} {'uygulandı' if ok else 'uygulanamadı'} — {sonuc}")
def _gelen_yaz(eid, a):
    h = next((h for h in talimat_hedefler() if h["ad"] == a.get("hedef")), None)
    if not h: return False, _t("hedef ayarda yok", "target not in settings")
    d = os.path.join(BASE, "gelen"); yol = os.path.join(d, h["ad"] + ".jsonl")
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        if not os.path.exists(yol): os.close(os.open(yol, os.O_WRONLY | os.O_CREAT, 0o600))
    except OSError as e: return False, e.__class__.__name__
    _TAL["t"].setdefault(h["ad"], []).append(time.time())
    o = {"id": eid, "at": datetime.datetime.now().isoformat(timespec="seconds"), "metin": a.get("metin"), "duyulan": a.get("duyulan"), "toplantida": a.get("toplantida")}
    with LOCK: write([(yol, json.dumps(o, ensure_ascii=False) + "\n")])
    return True, _t(f"{h.get('etiket') or h['ad']} gelen kutusuna yazıldı", f"written to the {h.get('etiket') or h['ad']} inbox")
def _yapilacak_taslak(a):
    ben = eposta_ben() if "eposta_ben" in globals() else None
    if not ben: return False, _t("e-posta adresi yok (ayar eposta_adres)", "no email address (setting eposta_adres)")
    is_ = str(a.get("metin") or ""); konu = _t("Yapılacak: ", "To-do: ") + (is_[:70] + ("…" if len(is_) > 70 else ""))
    govde = is_ + "\n\n" + _t(f"(Sesle eklendi, {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}.)", f"(Added by voice, {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.)")
    e = urllib.parse.quote; tur = eposta_tur()
    u = (f"https://outlook.office.com/mail/deeplink/compose?to={e(ben)}&subject={e(konu)}&body={e(govde)}" if tur == "outlook" else
         f"https://mail.google.com/mail/u/{e(ben)}/?view=cm&fs=1&to={e(ben)}&su={e(konu)}&body={e(govde)}" if tur == "gmail" else
         f"mailto:{e(ben)}?subject={e(konu)}&body={e(govde)}")
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"TALİMAT (deneme): taslak {tur} · {konu}"); return True, _t("taslak açıldı (deneme)", "draft opened (test)")
    try: subprocess.Popen(["/usr/bin/open", u], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as ex: return False, ex.__class__.__name__
    return True, _t("e-posta taslağı açıldı (Gönder sende)", "email draft opened (you send it)")
