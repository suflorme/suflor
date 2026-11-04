# Suflor.me aktarıcı bölümü: Sesle oturuma talimat ve yapılacak (v0.75.0). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır
# (bolum("talimat")): AYAR, BASE, LOCK, write, _t, eylem_ekle, eylem_karar, soru_baslat, add_card, CARDS, toplanti_var, eposta_tur, eposta_ben … diğer
# bölümlerin. import etme. Python 3.9 uyumlu.
# Kullanıcının KENDİ sözü (bas-konuş, sohbet, toplantıda kendi kanalındaki hitap; karşı taraf ve otonom değil) Claude'a gitmeden yakalanır:
#   "<hedef kalıbı> (şunu) ilet/söyle/yaz/gönder/bildir: <ileti>"  → eylem kuyruğunda "oturum" işi
#   "yapılacaklarıma ekle: <iş>"                                    → eylem kuyruğunda "yapilacak" işi
# Onay: toplantı dışında sesli geri okuma + "İleteyim mi?" (evet/hayır, 10 sn Geri al); toplantıda onay kartı (Onayla / Reddet) — sesle okunmaz.
# Onaylanınca aktarıcı uygular (Claude değil): oturum → canli/gelen/<hedef>.jsonl (0600); hedef oturumun kancası (toplanti-claude.py gelen --hedef <ad>)
# okunmamışları bağlama ekler (oturumu uyandırmaz, kullanıcı o oturuma yazınca görünür). Yapılacak → v0.131.0'dan Mac'in Anımsatıcılar'ı (Suflor Takvim.app
# --animsatici; saat verildiyse o saatte çalar); eklenemezse (izin yok) eskisi gibi kullanıcının kendi adresine e-posta taslağı (ayar eposta; toplantıdaysa
# toplantı bitince açılır; gönderiyi kullanıcı yapar). Her iş canli/talimat-kayit.jsonl'e yazılır.
# Hedefler ayar "talimat_hedefler": [{"ad": "proje", "etiket": "proje oturumu", "kalip": ["proje oturumuna", …]}, …]; yoksa yalnız "proje". Geliştirme
# oturumu gibi kullanıcıya özel hedefler yalnız kullanıcının ayarında durur. Ayar "talimat": false kapatır.
# v0.101.1 (kullanıcı, 21 Ekim: "önce gönderemem diyor, ısrar edince gönderiyor"): kalıp Whisper yazımını kaçırınca ("ana oturma") soru Claude'a gidiyordu ve Claude
# bu yolu bilmiyordu; kalıp tutunca da ileti yalnız o cümleydi (asıl istek önceki cümlede kaldı). Artık Konuş istemi hedefleri söyler, Claude iletiyi konuşmanın
# bağlamından yazıp cevabın sonuna [İLET <hedef>: <ileti>] koyar; aktarıcı etiketi okumaz, siler ve aynı onay yoluna sokar (talimat_claude). Onaysız gitmez.
# Kalıpta "oturuma/oturumuna" Whisper'ın "oturma" yazımını da kabul eder.
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
def _kalip_rx(x): return re.escape(x).replace("oturumuna", "otur(?:umun|um|m)?a").replace("oturuma", "otur(?:um|m)?a")
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
        k = "|".join(_kalip_rx(x) for x in sorted(h["kalip"], key=len, reverse=True))
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
    return talimat_kuyruk(*c, metin, kaynak)
# v0.115.2 (kullanıcı, 22 Ekim test toplantısı: "asistan ve oturum aynı onayı iki kez sordu"): adsız "bunu geliştirme oturumuna bildirebilir misin?" isteğini
# toplantı oturumu kendi "ileteyim mi?" kartıyla sordu (onayı hiçbir şey göndermedi), az sonra asistan aynı isteği defterden görüp bu yoldan ikinci onay kartını
# açtı. Artık toplantı oturumu da bu yolu kullanır (toplanti-claude.py ilet → /ilet → talimat_ilet) ve aynı oturuma 5 dk içinde benzer ileti (sözcüklerin
# yarısı ortak) bekliyor/onaylandı/iletildi ise yenisi açılmaz.
TALIMAT_YINELEME_SN = 300
# v0.162.4 (31 Ekim 02:47–02:51 beta): ilk ileti 24, ikincisi 51 sözcük, ortak 13 → ortak/küçük = 0,54 ≥ 0,5 sayılıp içeriği farklı ek ileti "yinelenen" diye reddedildi
# (asistan sonra "gidecek" dedi, kart hiç açılmamıştı). Artık ortak/birleşim (Jaccard, o çiftte 0,21) ≥ 0,6; ya da küçük ileti büyüğün neredeyse içindeyse (ortak/küçük ≥ 0,85) VE
# boyutları yakınsa (küçük/büyük ≥ 0,6) — kısaltılmış tekrar. Küçük ileti uzun ilete "gömülü" olsa bile boyut çok farklıysa yeni ileti sayılır.
def _talimat_benzer(s, o):
    k = len(s & o)
    if not k: return False
    return k / len(s | o) >= 0.6 or (k / min(len(s), len(o)) >= 0.85 and min(len(s), len(o)) / max(len(s), len(o)) >= 0.6)
def _talimat_yinelenen(h, ileti, duyulan=None, gorev=False):  # gorev: asistanın önerisi — toplantı oturumunun aynı istek satırından (duyulan) yazdığı ileti de aynı iş sayılır
    s = _sozcukler(ileti); d = _sozcukler(duyulan) if duyulan else set(); sinir = (datetime.datetime.now() - datetime.timedelta(seconds=TALIMAT_YINELEME_SN)).isoformat(timespec="seconds")
    if not s: return None
    with LOCK:
        for x in reversed(EYLEMLER):
            if x.get("tur") != "oturum" or x.get("durum") not in ("bekliyor", "onaylandi", "yapildi") or str(x.get("at") or "") < sinir: continue
            try: a = json.loads(x.get("ayrinti") or "{}")
            except ValueError: continue
            o = _sozcukler(a.get("metin"))
            if a.get("hedef") != h["ad"]: continue
            if o and _talimat_benzer(s, o): return x
            if d and (gorev or a.get("oneri")) and _sozcukler(a.get("duyulan")) and _talimat_benzer(d, _sozcukler(a.get("duyulan"))): return x  # 3 Kasım: öneri ↔ toplantı oturumunun iletisi
    return None
def talimat_kuyruk(tur, h, ileti, metin, kaynak, claude=False, zaman=None, ek=None, oneri=None):  # oneri: asistanın kendi çıkardığı iş (kartta "Öneri:" ve bu gerekçe)  # claude: ileti Claude'un cevabından — pano cevabı Claude'unki kalır; zaman: hatırlatmanın saati (ISO, yerel)
    top = toplanti_var()
    if tur == "oturum":
        n = [t for t in _TAL["t"].get(h["ad"], []) if time.time() - t < 3600]
        if len(n) >= TALIMAT_SAAT_SINIR:
            cevap = _t("Bu saatte o oturuma çok ileti gitti; biraz sonra.", "Too many messages to that session this hour; later.")
            if not claude: _konus_kur(durum="hazir", soru=metin, cevap=cevap)
            if not top: seslendir(cevap, kuyruk=True)
            return True
        y = _talimat_yinelenen(h, ileti, metin, gorev=bool(oneri))
        if y:
            cevap = (_t("Bu ileti zaten onay bekliyor.", "That message is already waiting for approval.") if y["durum"] == "bekliyor"
                     else _t("Bu ileti zaten iletildi.", "That message was already sent."))
            if not claude: _konus_kur(durum="hazir", soru=metin, cevap=cevap)
            print(f"TALİMAT: yinelenmedi — {h['ad']} oturumuna 5 dk içinde benzer ileti var ({y['id']}, {y['durum']})")
            return True
        etiket = str(h.get("etiket") or h["ad"])
    x = eylem_ekle({"tur": tur, "baslik": ileti[:160], "ayrinti": json.dumps({"hedef": h["ad"] if h else None, "etiket": etiket if h else None, "metin": ileti,
                                                                            "duyulan": metin[:TALIMAT_EN_COK], "kaynak": kaynak, "toplantida": top, **({"zaman": zaman} if zaman else {}), **({"oneri": True} if oneri else {}), **(ek or {})}, ensure_ascii=False)})
    if not x: return False
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True)  # toplantı oturumu (Claude) bu işi uygulamaz, sunmaz
    _talimat_kayit({"id": x["id"], "tur": tur, "hedef": h["ad"] if h else None, "metin": ileti, "durum": "bekliyor", "kaynak": kaynak, "toplantida": top})
    ne = (_t(f"{etiket}na ileti", f"message to the {etiket}") if tur == "oturum" else _t("takvimden silme", "calendar removal") if tur == "sil"
          else _t("toplantı", "meeting") if tur == "toplanti" else _t("hatırlatma", "reminder"))
    if top:  # toplantıda: onay kartı, sesle okunmaz (kullanıcı)
        c_ = add_card({"kind": "not", "text": (_t(f"Öneri: {ne} — «{ileti[:300]}»", f"Suggestion: {ne} — «{ileti[:300]}»") if oneri else _t(f"Onay: {ne} — «{ileti[:300]}»", f"Approve: {ne} — «{ileti[:300]}»")),
                       "why": oneri or _t("Sesle verdiğin talimat; Onayla ya da Reddet.", "Your spoken instruction; approve or reject."), "onay": True})
        if c_:
            with LOCK: c_["eylem"] = x["id"]
        cevap = _t("Onay kartı panoda.", "Approval card on the panel.")
    else:
        soru_baslat([x["id"]]); cevap = _t(f"{ne}: «{ileti[:200]}» — onay bekliyor.", f"{ne}: «{ileti[:200]}» — waiting for approval.")
    if not claude: _konus_kur(durum="hazir", soru=metin, cevap=cevap, hata=None, olcum=None)
    print(f"TALİMAT: {'öneri · ' if oneri else 'Claude hazırladı · ' if claude else ''}{tur}{(' → ' + h['ad']) if h else ''} onay bekliyor ({'kart' if top else 'sesli'}) — \"{ileti[:60]}\"")
    return True
def talimat_ilet(p):  # v0.115.2: toplantı oturumu (toplanti-claude.py ilet, anahtarlı /ilet) — kullanıcının istediği ileti aynı onay yolundan; kendi kartını açmaz
    hedefler = [x["ad"] for x in talimat_hedefler()]
    h = next((x for x in talimat_hedefler() if x["ad"] == str(p.get("hedef") or "").strip().lower()), None); ileti = _talimat_temiz(p.get("metin"))[:TALIMAT_EN_COK]
    if AYAR.get("talimat") is False: return {"ok": False, "err": "kapalı", "hedefler": hedefler}
    if not h: return {"ok": False, "err": "hedef yok", "hedefler": hedefler}
    if len(ileti.split()) < 2: return {"ok": False, "err": "ileti kısa", "hedefler": hedefler}
    with LOCK: n = len(EYLEMLER)
    talimat_kuyruk("oturum", h, ileti, str(p.get("duyulan") or ileti)[:TALIMAT_EN_COK], "toplanti", claude=True)
    with LOCK: x = EYLEMLER[-1] if len(EYLEMLER) > n else None
    if x: return {"ok": True, "durum": "onay", "id": x["id"], "toplantida": toplanti_var()}
    y = _talimat_yinelenen(h, ileti, str(p.get("duyulan") or ileti)[:TALIMAT_EN_COK])  # talimat_kuyruk'taki denetimin aynısı (öneriyle istek satırı ortaksa yinelenen)
    return {"ok": True, "durum": "yinelenen", "id": y["id"], "eski": y["durum"]} if y else {"ok": False, "err": "sınır (saatte en çok %d)" % TALIMAT_SAAT_SINIR}
# Kullanıcı (24 Ekim, ilk sahne denemesi): "yarın 10'da Ali'yi aramamı hatırlatan bir not yaz" proje oturumuna ileti olarak hazırlandı, asistan "notu ben yazamıyorum"
# dedi; gece 01.12'de "yarın" sormadan Pazar sayıldı. Hatırlatma ve not isteği kullanıcının kendi yapılacağına gider ([İLET yapilacak: …] → eylem "yapilacak", onaylanınca
# kendine e-posta taslağı; Mac Hatırlatıcılar desteği yok). 00.00–05.00 arasında "yarın" belirsiz: asistan önce tek kısa soru sorar. Yanlış duyulan sözcükte geri
# sorulmaz (sohbet kuralı), ama eylemin günü, saati, kişisi ya da sayısı belirsizse tek kısa doğrulama sorusu kalır.
TALIMAT_ETIKET_RX = re.compile(r"\[\s*[İI]LET\s+(?P<h>[\w-]{1,24})\s*:\s*(?P<m>[^\]]*)\]?", re.I)
TALIMAT_ETIKET_BAS = re.compile(r"\[\s*[İI]LET\b", re.I)  # okuma bu noktada durur (etiket sesli okunmaz)
TALIMAT_YAPILACAK_AD = {"yapilacak", "yapılacak", "hatirlatma", "hatırlatma", "not", "todo"}
if "EYLEM_TUR" in globals(): EYLEM_TUR["sil"] = "Takvimden silme"  # v0.132.0
# v0.143.0 (kullanıcı 27 Ekim: "X ile toplantı" istendi, katılımcısız hatırlatma eklendi): toplantı isteği [İLET toplanti: <başlık> | <YYYY-MM-DDTHH:MM> | <dk> |
# <davetliler>] → onay → takvimin dolu "yeni etkinlik" sayfası açılır (Google; ayar eposta Outlook ise Outlook), kullanıcı Kaydet'e basar. macOS Takvim arayüzü (EventKit)
# katılımcı ekleyemez, toplantı bağlantısı oluşturamaz. Davetlinin adresi: söylenen e-posta ya da son 30 günün takvim olaylarındaki ad–adres eşi (takvim.swift kisiler).
# Sonraki adım: Google Takvim API ile karttaki tek tıkla oluşturma.
TALIMAT_TOPLANTI_AD = {"toplanti", "toplantı", "davet"}
if "EYLEM_TUR" in globals(): EYLEM_TUR["toplanti"] = "Toplantı"
TOPLANTI_DK = 30
_EPOSTA_RX = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
def _ad_anahtari(a): return " ".join(re.sub(r"[^\w\s]", " ", str(a or "").replace("İ", "i").replace("I", "ı").lower()).split())
def toplanti_davetli(adlar):  # ["Deniz", "<e-posta>"] → [{"ad", "eposta"|None}]; ad son 30 günün takvim olaylarındaki eşle (tam ad ya da ilk ad tek eşleşirse)
    es = {}
    for e in (globals().get("TAKVIM_TAM") or {}).values():
        for k in e.get("kisiler") or []:
            if k.get("ad") and k.get("eposta"): es.setdefault(_ad_anahtari(k["ad"]), set()).add(k["eposta"].lower())
    out = []
    for ad in adlar:
        ad = str(ad).strip(" .;")
        if not ad: continue
        m = _EPOSTA_RX.search(ad)
        if m: out.append({"ad": ad.replace(m.group(0), "").strip(" <>()") or m.group(0), "eposta": m.group(0).lower()}); continue
        a = _ad_anahtari(ad); bul = es.get(a, set())
        if not bul:  # ilk ad (ya da adın başı) tek kişiye gidiyorsa
            adaylar = {ep for k, v in es.items() if (k.split() or [""])[0] == a or k.startswith(a + " ") for ep in v}
            bul = adaylar if len(adaylar) == 1 else set()
        out.append({"ad": ad, "eposta": next(iter(bul)) if len(bul) == 1 else None})
    return out[:20]
def toplanti_ayir(ileti):  # "<başlık> | 2026-10-28T12:00 | 30 | Deniz, Ali" → {"baslik", "zaman", "dk", "davetli": [...]}; saat yoksa zaman None
    p = [x.strip() for x in str(ileti or "").split("|")]; baslik = p[0]; zaman = None; dk = TOPLANTI_DK; adlar = []
    for x in p[1:]:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[T ](\d{1,2})[:.](\d{2})(?::\d{2})?", x)
        if m and not zaman:
            try: zaman = datetime.datetime.strptime(f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}", "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M")
            except ValueError: pass
            continue
        m = re.fullmatch(r"(\d{1,3})\s*(?:dk|dakika|min)?", x, re.I)
        if m and 5 <= int(m.group(1)) <= 480: dk = int(m.group(1)); continue
        if x: adlar += [y for y in re.split(r"\s*[,;]\s*|\s+(?:ve|and)\s+", x) if y.strip()]
    return {"baslik": baslik, "zaman": zaman, "dk": dk, "davetli": toplanti_davetli(adlar)}
def toplanti_ozet(a):  # kartta ve sesli soruda okunacak kısa metin
    z = a.get("zaman"); zs = datetime.datetime.strptime(z, "%Y-%m-%dT%H:%M").strftime("%d.%m %H.%M") if z else _t("saatsiz", "no time")
    d = ", ".join(k["ad"] + ("" if k.get("eposta") else _t(" (adresi yok)", " (no address)")) for k in a.get("davetli") or [])
    return f"{a.get('baslik')} · {zs} · {a.get('dk') or TOPLANTI_DK} {_t('dk', 'min')}" + (f" · {d}" if d else "")
def toplanti_sayfa_url(a):  # takvimin dolu "yeni etkinlik" sayfası
    e = urllib.parse.quote; ben = eposta_ben() if "eposta_ben" in globals() else None; tur = eposta_tur() if "eposta_tur" in globals() else "gmail"
    bas = datetime.datetime.strptime(a["zaman"], "%Y-%m-%dT%H:%M"); bit = bas + datetime.timedelta(minutes=int(a.get("dk") or TOPLANTI_DK))
    adres = [k["eposta"] for k in a.get("davetli") or [] if k.get("eposta")]; yok = [k["ad"] for k in a.get("davetli") or [] if not k.get("eposta")]
    not_ = (_t("Suflor.me — panodaki takvimden oluşturuldu.", "Suflor.me — created from the panel calendar.") if a.get("kaynak") == "pano" else _t("Suflor.me — sesle istendi.", "Suflor.me — requested by voice.")) + (("\n" + _t("Adresi bulunamayan davetli: ", "Invitee without address: ") + ", ".join(yok)) if yok else "")
    if tur == "outlook":
        return (f"https://outlook.office.com/calendar/deeplink/compose?subject={e(a['baslik'])}&startdt={e(bas.astimezone().isoformat())}&enddt={e(bit.astimezone().isoformat())}"
                f"&to={e(';'.join(adres))}&body={e(not_)}&online=true")
    tz = ""
    try: tz = os.path.realpath("/etc/localtime").split("zoneinfo/", 1)[1]
    except (IndexError, OSError): pass
    return (f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={e(a['baslik'])}&dates={bas:%Y%m%dT%H%M%S}/{bit:%Y%m%dT%H%M%S}"
            + (f"&ctz={e(tz)}" if tz else "") + (f"&add={e(','.join(adres))}" if adres else "") + f"&details={e(not_)}&vcon=meet" + (f"&authuser={e(ben)}" if ben else ""))
def toplanti_sayfa_ac(a):
    if not a.get("zaman"): return False, _t("saat yok", "no time")
    u = toplanti_sayfa_url(a)
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"TALİMAT (deneme): toplantı sayfası {u}"); return True, _t("takvim sayfası açıldı (deneme)", "calendar page opened (test)")
    try: subprocess.Popen(["/usr/bin/open"] + (["-g"] if toplanti_var() else []) + [u], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # toplantıda öne gelmez
    except OSError as ex: return False, ex.__class__.__name__
    return True, _t("takvimde toplantı sayfası açıldı — Kaydet sende", "meeting page opened in your calendar — you press Save")
def takvim_toplanti(p, simdi=None):  # v0.166.0: panodaki takvimden toplantı oluşturma — {baslik, zaman "YYYY-MM-DDTHH:MM", dk, davetli [ad|e-posta], onizle, ac}; sayfa dolu açılır, Kaydet kullanıcıda (takvime doğrudan yazılmaz)
    if not isinstance(p, dict): return {"ok": False, "err": _t("geçersiz istek", "invalid request")}
    baslik = " ".join(str(p.get("baslik") or "").split()); dv = p.get("davetli"); zaman = str(p.get("zaman") or ""); dk = p.get("dk", TOPLANTI_DK)
    if len(baslik) > 300 or not isinstance(dv, (list, type(None))) or len(dv or []) > 20 or any(not isinstance(x, str) or len(x) > 200 for x in dv or []): return {"ok": False, "err": _t("geçersiz istek", "invalid request")}
    if isinstance(dk, bool) or not isinstance(dk, int) or not 5 <= dk <= 480: return {"ok": False, "err": _t("süre 5–480 dakika olmalı", "duration must be 5–480 minutes")}
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", zaman): return {"ok": False, "err": _t("saat geçersiz", "invalid time")}
    try: bas = datetime.datetime.strptime(zaman, "%Y-%m-%dT%H:%M")
    except ValueError: return {"ok": False, "err": _t("saat geçersiz", "invalid time")}
    a = {"baslik": baslik or _t("Toplantı", "Meeting"), "zaman": zaman, "dk": dk, "davetli": toplanti_davetli([x for x in dv or [] if x.strip()]), "kaynak": "pano"}
    gecmis = bas < (simdi or datetime.datetime.now()) - datetime.timedelta(minutes=1)
    if p.get("onizle"): return {"ok": True, "davetli": a["davetli"], "url": toplanti_sayfa_url(a), "gecmis": gecmis}
    if not baslik: return {"ok": False, "err": _t("başlık yok", "no title")}
    if gecmis: return {"ok": False, "err": _t("geçmiş bir saate toplantı oluşturulamaz", "can't create a meeting in the past")}
    url = toplanti_sayfa_url(a)
    if p.get("ac"):
        ok, msg = toplanti_sayfa_ac(a)
        if not ok: return {"ok": False, "err": msg}
        return {"ok": True, "url": url, "acildi": True, "davetli": a["davetli"], "ileti": msg}
    return {"ok": True, "url": url, "acildi": False, "davetli": a["davetli"]}  # Chrome panosu sayfayı kendisi açar
ANIMSATICI_ZAMAN_RX = re.compile(r"\s*\|\s*(\d{4}-\d{2}-\d{2})[T ](\d{1,2})[:.](\d{2})(?::\d{2})?\s*$")
def animsatici_zaman_ayir(ileti):  # "<iş> | 2026-10-25T10:00" → ("<iş>", "2026-10-25T10:00"); saat yoksa (ileti, None)
    m = ANIMSATICI_ZAMAN_RX.search(ileti or "")
    if not m: return re.sub(r"\s*\|\s*$", "", ileti or ""), None
    try: z = datetime.datetime.strptime(f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}", "%Y-%m-%d %H:%M")
    except ValueError: return ileti[:m.start()].rstrip(), None
    return ileti[:m.start()].rstrip(), z.strftime("%Y-%m-%dT%H:%M")
# v0.132.0 (25 Ekim denemesi: hatırlatma takvime eklenmişken asistan "onay bekliyor", "göremiyorum, silemem" dedi): Konuş bağlamına son 2 saatte hazırlanan işlerin durumu
TALIMAT_DURUM_SA = 2
def talimat_durum_blok():
    sinir = (datetime.datetime.now() - datetime.timedelta(hours=TALIMAT_DURUM_SA)).isoformat(timespec="seconds")
    with LOCK: xs = [x for x in EYLEMLER if x.get("tur") in ("yapilacak", "oturum", "sil", "toplanti") and str(x.get("at") or "") >= sinir][-6:]
    if not xs: return ""
    ad = {"bekliyor": ("onay bekliyor", "waiting for approval"), "onaylandi": ("onaylandı, uygulanıyor", "approved, being applied"), "reddedildi": ("reddedildi", "rejected"),
          "hata": ("yapılamadı", "failed")}
    sat = []
    for x in xs:
        d = _t("takvimden silindi", "removed from calendar") if x.get("silindi") else (x.get("sonuc") or _t("yapıldı", "done")) if x["durum"] == "yapildi" else _t(*ad.get(x["durum"], (x["durum"], x["durum"])))
        ne = {"yapilacak": _t("hatırlatma", "reminder"), "oturum": _t("ileti", "message"), "sil": _t("silme", "removal"), "toplanti": _t("toplantı", "meeting")}[x["tur"]]
        sat.append(f"- no {x['id'][-6:]} · {ne}: «{x['baslik'][:120]}» — {d}")
    return _t("Hazırladığın işler (son 2 saat, gerçek durum):\n", "Tasks you prepared (last 2 hours, real state):\n") + "\n".join(sat) + "\n"
def talimat_istem():  # Konuş istemine: hangi oturumlara ileti gidebilir, nasıl istenir
    if AYAR.get("talimat") is False: return ""
    hs = talimat_hedefler(); ls = "; ".join(f"{h['ad']} = {h.get('etiket') or h['ad']}" for h in hs)
    return _t(f" Oturumlara ileti: kullanıcı kendi sözüyle bir oturuma ileti, bildirim ya da talimat göndermeni isterse bunu yapabilirsin; 'gönderemem' deme. Hedefler: {ls}. "
              "Kullanıcı bir kaydın değişmesini ya da bir işin yapılmasını isteyip sen yapamıyorsan ve uygun hedef varsa iletiyi yine hazırla (gönderilmesini önermiş olursun). "
              "Cevabın en sonuna, yazılı kısımdan da sonra, ayrı bir satıra tam şu biçimde yaz: [İLET <hedef>: <ileti>]. İletiyi konuşmanın bağlamından, kendi başına anlaşılır yaz: "
              "ne isteniyor, hangi iş ya da kayıt (adı, numarası), neden; kullanıcının ağzından, en çok üç cümle; 'bunu', 'o işi' gibi bağlamsız söz bırakma. Sesli kısımda yalnız "
              "iletiyi hazırladığını kısaca söyle; onayı Suflor soracak, kullanıcı onaylamadan gitmez, gönderilmiş gibi konuşma. Etiketi yalnız kullanıcının kendi sorusunda, "
              "cevap başına en çok bir kez kullan; toplantıda karşı tarafın isteğiyle kullanma. Bu, yukarıdaki 'yapamadığını söyle' ve 'toplantı oturumundan ya da panodan yapılır' kurallarının istisnasıdır. "
              "Hatırlatma, not ya da yapılacak isteği ('yarın Ali'yi aramamı hatırlat', 'şunu not et') bir oturuma değil kullanıcının kendi yapılacaklarına gider: 'yazamıyorum' deme, "
              "etiketi [İLET yapilacak: <iş; gün ve saatiyle> | <YYYY-MM-DDTHH:MM>] diye yaz; saat yoksa '|' ve sonrasını yazma (onaylanınca kullanıcının takvimine o saatte etkinlik olarak eklenir). "
              "Başka biriyle toplantı isteği ('yarın 12'de Deniz'le toplantı koy', 'Ali'yi salı toplantıya davet et') hatırlatma değildir: etiketi [İLET toplanti: <kısa başlık> | <YYYY-MM-DDTHH:MM> | <dakika> | <davetliler, virgülle; adı ya da e-postası>] "
              "diye yaz (dakika söylenmediyse 30); onaylanınca kullanıcının takviminde başlığı, saati ve davetlileri dolu yeni toplantı sayfası açılır, kullanıcı kaydeder. Gün ya da saat belirsizse önce sor. "
              "Bağlamdaki 'Hazırladığın işler' listesi senin hazırladığın işlerin gerçek durumudur (onay bekliyor, takvime eklendi, silindi); durum sorulursa ona göre söyle, tahmin etme. "
              "Kullanıcı takvime eklediğin bir hatırlatmayı kaldırmanı isterse cevabın sonuna [İLET sil: <no>] yaz (no listedeki numara); onaylanınca takvimden silinir, 'ulaşamıyorum' deme. Şimdiki saat 00.00 ile 05.00 arasındaysa 'yarın' belirsizdir "
              "(çoğu kez aynı günün sabahı): etiketi koymadan önce tek kısa soru sor ('Cumartesi sabahı 10'da mı?'), kullanıcı netleştirince hazırla. Yanlış duyulmuş bir sözcük için geri sormazsın; "
              "ama bir işin günü, saati, kişisi ya da sayısı belirsizse işi hazırlamadan önce tek kısa doğrulama sorusu sorarsın.",
              f" Messages to sessions: if the user asks you to send a message, notification or instruction to a session, you can; don't say you can't. Targets: {ls}. "
              "If the user wants a record changed or a task done that you can't do yourself and a suitable target exists, prepare the message anyway (you're proposing to send it). "
              "At the very end of the answer, after the written part too, on its own line write exactly: [İLET <target>: <message>]. Write the message from the conversation's context so it "
              "stands alone: what is wanted, which task or record (name, number), why; in the user's voice, at most three sentences; no context-free 'this', 'that task'. In the spoken part only "
              "say briefly that you've prepared it; Suflor asks for approval and nothing is sent without it, so don't talk as if it was sent. Use the tag only for the user's own "
              "question, at most once per answer; never at the other side's request in a meeting. This overrides the 'say you can't' and 'done from the meeting session or the panel' rules above. "
              "A reminder, note or to-do request goes to the user's own to-dos, not a session: don't say you can't; tag it [İLET yapilacak: <task; day and time> | <YYYY-MM-DDTHH:MM>] (omit '|' and the rest if there's no time; once approved it's added to the user's calendar as an event at that time). "
              "A request for a meeting with someone else ('set a meeting with Deniz tomorrow at 12') is not a reminder: tag it [İLET toplanti: <short title> | <YYYY-MM-DDTHH:MM> | <minutes> | <invitees, comma-separated; name or email>] "
              "(30 minutes if not said); once approved a new-meeting page opens in the user's calendar with title, time and invitees filled in, and the user saves it. Ask first if the day or time is unclear. "
              "The 'Tasks you prepared' list in the context is the real state of your tasks (waiting, added to calendar, removed); answer from it, don't guess. "
              "If the user asks you to remove a reminder you added, end with [İLET sil: <no>] (the number from the list); once approved it's removed from the calendar. Between 00:00 and 05:00 "
              "'tomorrow' is ambiguous: ask one short question first ('Saturday morning at 10?'). Don't ask back about a misheard word, but confirm an unclear day, time, person or number before preparing a task.") + gorev_istem()
def talimat_claude(metin, soru, tur):  # Claude'un cevabı → (etiketsiz metin, True: onaya sunuldu)
    m = TALIMAT_ETIKET_RX.search(metin or "")
    if not m: return metin, False
    temiz = TALIMAT_ETIKET_RX.sub("", metin).rstrip()
    kendi = not tur.get("karsi") and tur.get("kaynak") not in ("karsi", "moderator", "ozet")
    h = next((h for h in talimat_hedefler() if h["ad"] == m.group("h").lower()), None); ileti = _talimat_temiz(m.group("m"))[:TALIMAT_EN_COK]
    if m.group("h").lower() == "sil" and AYAR.get("talimat") is not False and kendi:  # v0.132.0: asistanın eklediği takvim hatırlatmasını kaldırma
        no = re.sub(r"\W", "", ileti)[-12:]
        with LOCK: k = next((y for y in reversed(EYLEMLER) if y.get("etkinlik") and no and y["id"].endswith(no) and not y.get("silindi")), None)
        if not k: print(f"TALİMAT: silinecek iş bulunamadı ({no or 'numara yok'})"); return temiz, False
        return temiz, talimat_kuyruk("sil", None, k["baslik"], str(soru or "")[:TALIMAT_EN_COK], tur.get("kaynak") or "bas", claude=True, ek={"etkinlik": k["etkinlik"], "kaynak_eylem": k["id"]})
    if m.group("h").lower() in TALIMAT_TOPLANTI_AD and AYAR.get("talimat") is not False and kendi:  # v0.143.0: davetli toplantı → takvimin dolu sayfası
        a = toplanti_ayir(ileti)
        if not a["baslik"] or not a["zaman"]: print(f"TALİMAT: toplantı hazırlanmadı ({'başlık' if not a['baslik'] else 'saat'} yok)"); return temiz, False
        return temiz, talimat_kuyruk("toplanti", None, toplanti_ozet(a), str(soru or "")[:TALIMAT_EN_COK], tur.get("kaynak") or "bas", claude=True, zaman=a["zaman"],
                                     ek={"baslik": a["baslik"], "dk": a["dk"], "davetli": a["davetli"]})
    if m.group("h").lower() in TALIMAT_YAPILACAK_AD and AYAR.get("talimat") is not False and kendi and len(ileti.split()) >= 2:  # hatırlatma/not → kullanıcının yapılacağı
        ileti, zaman = animsatici_zaman_ayir(ileti)
        return temiz, talimat_kuyruk("yapilacak", None, ileti, str(soru or "")[:TALIMAT_EN_COK], tur.get("kaynak") or "bas", claude=True, zaman=zaman)
    if AYAR.get("talimat") is False or not kendi or not h or len(ileti.split()) < 2:
        print(f"TALİMAT: Claude'un iletisi alınmadı ({'kapalı' if AYAR.get('talimat') is False else 'kullanıcının sorusu değil' if not kendi else 'hedef yok' if not h else 'ileti kısa'})")
        return temiz, False
    return temiz, talimat_kuyruk("oturum", h, ileti, str(soru or "")[:TALIMAT_EN_COK], tur.get("kaynak") or "bas", claude=True)
# --- Kişisel asistanın görev çıkarması (kullanıcı, 3 Kasım) --------------------------------------------------------------------------------------
# Kişilik dosyasında "gorev_cikar: evet" (kisilik.py gorev_cikar_acik: toplantı kişiliğinin bayrağı; kurumsal asistanda yok, orada iş yalnız adıyla seslenilince):
#  1) Toplantıda kullanıcının hitapsız iş sözü atılmaz, öneri kartı olur (3 Kasım 17.11: "bu bulguyu geliştirme oturumuna iletli hemen lütfen." "asistanın adıyla
#     başlamalı" diye atılmıştı). Kalıp: talimat_coz (hedefli ileti, yapılacak) ya da GOREV_IS_RX (takvim, hatırlatma, e-posta, toplantı koyma) ve istek kipi
#     (GOREV_ISTEK_RX: -sin, -elim, -eyim, lütfen, "ekler misin"). Geçmiş zaman ("ilettim") ve iş fiili olmayan söz öneri olmaz (17.15: kullanıcı ekrandaki metni
#     sesli okurken "… sessiz kalırsa panoda uyaracaksın" — HITAP_IS_RX "sessiz"i iş sayıyordu). İleti bağlamsızsa ("bunu", "bu bulguyu") ya da kısaysa
#     kullanıcının son GOREV_BAGLAM_SN'deki satırlarıyla tamamlanır: kartta kendi sözleri durur, Claude yeniden yazmaz.
#  2) Ortada sahipsiz kalan iş: herhangi bir konuşmacının "raporun gönderilmesi lazım", "kim bakacak?", "birinin … lazım" sözü GOREV_SAHIP_SN içinde kimse
#     üstlenmezse ("ben bakarım", "Ali halletsin", "bende") kullanıcıya hatırlatma önerisi olur. Sözde sahip varsa ("Ali'nin bakması lazım") öneri yok;
#     "konuşmamız/düşünmemiz lazım" iş sayılmaz. Seyrek: toplantıda en çok GOREV_SAHIPSIZ_EN_COK, iki öneri arası en az GOREV_SAHIPSIZ_ARA_SN, aynı anda tek aday.
#  Her öneri onay kartıyla (toplantıda sesle okunmaz). Aynı iş (reddedilen dahil, toplantı boyunca) yeniden önerilmez. Toplantı oturumu izliyorsa (topo_izliyor)
#  hitapsız söz önerisi GOREV_OTURUM_BEKLE_SN bekler: oturum o arada iş açtıysa öneri açılmaz; oturumun sonraki aynı iletisi istek satırından (duyulan) yinelenen
#  sayılır. Claude'a sorulmaz: ek gecikme ve maliyet yok. Toplantı dışında Konuş istemine kural girer (talimat_istem): konuşmadan çıkan iş [İLET yapilacak: …]
#  ile hazırlanır, aktarıcı "Hatırlatma olarak ekleyeyim mi?" diye sorar.
_GOREV_HIZLI = bool(os.environ.get("SUFLOR_TEST_HIZLI"))
GOREV_BAGLAM_SN, GOREV_BOSLUK_SN, GOREV_OTURUM_BEKLE_SN, GOREV_SAHIP_SN = 60, (3 if _GOREV_HIZLI else 15), (2 if _GOREV_HIZLI else 30), (3 if _GOREV_HIZLI else 40)
GOREV_SAHIPSIZ_ARA_SN, GOREV_SAHIPSIZ_EN_COK, GOREV_HITAPSIZ_EN_COK = (4 if _GOREV_HIZLI else 600), 3, 10
GOREV_IS_RX = re.compile(r"\btakvim\w*\s+(?:ekle|koy|işle|yaz)\w*|\btakvime\b|\bhatırlat\w*|\b(?:e-?posta|mail|ileti|mesaj)\w*\b.{0,40}?\b(?:yaz|gönder|hazırla|at)\w*|"
                         r"\btaslağ?\w*\s+(?:yaz|hazırla|oluştur|çıkar)\w*|\b(?:toplantı|görüşme|etkinlik|randevu)\w*\b.{0,30}?\b(?:koy|ayarla|planla|oluştur|ekle)\w*|"
                         r"\bdavet\w*\s+(?:gönder|at|hazırla)\w*|\bkuyruğa\b|\bremind|\badd to (?:my )?calendar|\bsend (?:an )?email|\bschedule (?:a |the )?(?:meeting|call)", re.I)
GOREV_ISTEK_RX = re.compile(r"\b\w+(?:s[ıiuü]n|s[ıiuü]nl[ae]r|[ae]l[ıi]m|[ae]y[ıi]m|m[ae]l[ıi]y[ıi][mz])\b|\b(?:lütfen|lazım|gerek\w*)\b|\b\w+(?:[ae]r|[ıiuü]r)\s+m[ıiuü]s[ıiuü]n\w*|"
                            r"\b(?:ekle|koy|yaz|gönder|ilet|hatırlat|hazırla|ayarla|planla|bildir|söyle)\b|\b(?:please|can you|could you)\b", re.I)
GOREV_GECMIS_RX = re.compile(r"\b(?:ilet|gönder|yaz|söyle|bildir|ekle|koy|hatırlat|hazırla|kaydet|aktar)\w*?(?:d[ıiuü][mk]|t[ıiuü][mk]|m[ıiuü]şt[ıiuü][mk])\b", re.I)
GOREV_BAGLAMSIZ_RX = re.compile(r"\b(?:bunu|şunu|sunu|onu|bunları|şunları|söylediğimi|dediğimi|bu\s+\w+[yn]?[ıiuü])\b", re.I)
_GOREV_FIIL = r"(?:mam[ıi]z|mem[ie]z|[ıiuü]lmas[ıi]|[ıiuü]lmes[ıi]|nmas[ıi]|nmes[ıi]|lmas[ıi]|lmes[ıi]|mas[ıi]|mes[ıi])"
# Somut iş fiili şart: 3 Kasım ölçümü (60 gerçek toplantı, 5.892 satır) — her "-mamız lazım" aday olunca 48 satır çıktı, çoğu "hedefi belirlememiz lazım" gibi söz
_GOREV_IS_KOK = (r"(?:gönder|hazırla|yaz|güncelle|ara|kontrol\s+et|düzelt|paylaş|ilet|bildir|bilgilendir|sor|planla|ayarla|takip\s+et|ekle|yolla|tamamla|imzala|onayla|öde|"
                 r"teslim\s+et|test\s+et|incele|toparla|çıkar|kur|hatırlat|davet\s+et|randevu\s+al|rezervasyon\s+yap|sipariş\s+ver|teklif\s+(?:ver|iste)|fatura\w*\s+kes)")
GOREV_SAHIPSIZ_RX = re.compile(r"\b" + _GOREV_IS_KOK + _GOREV_FIIL + r"\s+(?:lazım|gerek(?:iyor|li|ir)?|şart)\b|"
                               r"\bbirinin\b.{0,40}?\b(?:lazım|gerek\w*)\b|\bkim\s+(?:yapacak|bakacak|hazırlayacak|gönderecek|halledecek|üstlenecek|takip\s+edecek|ilgilenecek|arayacak|yazacak|soracak)\b|"
                               r"\b(?:someone|somebody)\s+(?:needs to|should|has to)\b|\bwho(?:'s| is| will)\s+(?:going to\s+)?(?:do|handle|take|send|own|follow up)\b|"
                               r"\bwe need to\s+(?:send|prepare|update|fix|check|follow up|schedule|call|email)\b", re.I)
GOREV_SAHIPLI_RX = re.compile(r"\b(?:benim|senin|onun|sizin)\b|\b\w+['’]n?[ıiuü]n\b", re.I)  # sözün kendisinde işin sahibi ("Ali'nin bakması lazım")
# 5 Kasım (gerçek toplantıda yanlış kart, kullanıcı reddetti: bir telefon aramasında sıra bekleyen kişiyi anlatan cümlenin sonundaki "geri araması gerekiyor"): durum anlatımı iş değil.
# Anlatım = "-ken" zarf-fiili ya da "-dığı" ortacı + "gerek"/"lazım" dışında bir "-yor" yüklemi ("bekliyor", "kaçıyor"); iş isteği yalnız "gerek/lazım" taşır, yanında anlatım yüklemi yoktur.
GOREV_ANLATIM_RX = re.compile(r"\b\w+ken\b|\b\w+d[ıiuü][ğg][ıiuü]\w*\b", re.I); GOREV_ANLATIM_YOR_RX = re.compile(r"\b(?!gerek|lazım)\w+[ıiuü]yor\b", re.I)
def gorev_anlatim_mi(m): return bool(GOREV_ANLATIM_RX.search(m) and GOREV_ANLATIM_YOR_RX.search(m))
GOREV_USTLEN_RX = re.compile(r"\b(?:ben|biz)\b.{0,30}?\b\w+(?:[ae]r[ıi]m|[ıiuü]r[ıiuü]m|[ae]r[ıi]z|[ıiuü]r[ıiuü]z|[ae]y[ıi]m|[ae]l[ıi]m)\b|\bbende\b|\büstlen\w*|"
                             r"\b\w+\s+(?:yapsın|baksın|hazırlasın|göndersin|halletsin|ilgilensin|arasın|yazsın|sorsun|takip\s+etsin|üstlensin)\b|"
                             r"\bsen\s+(?:\w+\s+){0,2}?(?:yap|bak|hazırla|gönder|hallet|ilgilen|ara|yaz|sor)\w*\b|\bI(?:'ll| will| can)\s+(?:do|take|handle|send|check|follow)\b|"
                             r"\b(?:I'?m on it|leave it to me)\b", re.I)
# Sözlü saat/tarih → ISO yerel saat (görev önerisi: Claude'a sorulmadığı için hatırlatmanın zamanını burası çıkarır). Yalnız saat işaretiyle: "saat N", "N'de/'da/'te/'ta",
# dakikalı "9.45"/"9:45", gün/dönem sözcüğünün yanındaki sayı ("öğleden sonra 3"); "3 kişi", "%30", "2.000" saat sayılmaz. Bulamazsa None.
_SC_AY = ("ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık")
_SC_GUN = ("pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar")
_SC_EK = r"(?:['’]?(?:y?[ae]|[ıi]n|[dt][ae]|[dt][ae]n|[yn]?[ıi]))?"
SC_TARIH_RX = re.compile(r"(?<![\d.,:/])(\d{1,2})\s+(" + "|".join(_SC_AY) + r")\w*(?:\s+(20\d\d)\b)?", re.I)
SC_GUN_RX = re.compile(r"\b(pazartesi|salı|çarşamba|perşembe|cumartesi|cuma|pazar)" + _SC_EK + r"\b", re.I)
SC_GOGUN_RX = re.compile(r"\b(yarın|öbür\s+gün|obur\s+gün|ertesi\s+gün|bugün)\b", re.I)
SC_DONEM_RX = re.compile(r"\b(öğleden\s+sonra|akşam|gece|öğle|sabah)\w*", re.I)
SC_DAKIKALI_RX = re.compile(r"(?<![\d.,:/])(\d{1,2})[.:](\d{2})(?![\d]|[.,:/]\d)")
SC_SAAT_RX = re.compile(r"\bsaat\s+(\d{1,2})(?![\d.,:/%])")
SC_EKLI_RX = re.compile(r"(?<![\d.,:/%])(\d{1,2})\s*['’]\s*[dt][ae]\b|(?<![\d.,:/%])(\d{1,2})[dt][ae]\b")
SC_DONEMLI_RX = re.compile(r"\b(?:öğleden\s+sonra|akşam|gece|öğle|sabah)\w*\s+(?:saat\s+)?(\d{1,2})(?![\d.,:/%])", re.I)
def saat_coz(metin, simdi=None):  # → "YYYY-MM-DDTHH:MM" (yerel) ya da None
    m_ = " ".join(str(metin or "").replace("İ", "i").replace("I", "ı").lower().split()); simdi = simdi or datetime.datetime.now()
    sa = dk = None
    for rx in (SC_DAKIKALI_RX, SC_SAAT_RX, SC_EKLI_RX, SC_DONEMLI_RX):
        x = rx.search(m_)
        if x:
            g = [v for v in x.groups() if v is not None]; sa = int(g[0]); dk = int(g[1]) if len(g) > 1 else 0; break
    if sa is not None:
        if sa > 23 or dk > 59: sa = None
    d = None; tarih = SC_TARIH_RX.search(m_)
    if tarih:
        ay = next((i + 1 for i, a in enumerate(_SC_AY) if tarih.group(2).startswith(a)), None)
        try:
            yil = int(tarih.group(3) or simdi.year); d = datetime.date(yil, ay, int(tarih.group(1)))
            if not tarih.group(3) and d < simdi.date(): d = datetime.date(yil + 1, ay, int(tarih.group(1)))
        except (ValueError, TypeError): return None
    if sa is not None:
        dn = SC_DONEM_RX.search(m_); dd = dn.group(1).split()[0] if dn else ""
        if not dn and 1 <= sa <= 6: sa += 12  # dönem sözcüğü yoksa 1–6 öğleden sonra sayılır ("pazartesi 3'te" → 15:00); açık dönem ("sabah 3") kazanır
        elif (dd in ("öğleden", "akşam") and sa < 12) or (dd == "gece" and 6 <= sa < 12) or (dd == "öğle" and 1 <= sa <= 5): sa += 12
        if sa > 23: return None
    if d is None:
        g_ = SC_GOGUN_RX.search(m_); gn = SC_GUN_RX.search(m_)
        if g_:
            d = simdi.date() + datetime.timedelta(days=0 if g_.group(1) == "bugün" else 1 if g_.group(1).startswith(("yarın", "ertesi")) else 2)
        elif gn:
            hedef = _SC_GUN.index(gn.group(1)); fark = (hedef - simdi.weekday()) % 7
            if fark == 0 and not (sa is not None and datetime.datetime.combine(simdi.date(), datetime.time(sa, dk)) > simdi): fark = 7
            d = simdi.date() + datetime.timedelta(days=fark)
    if d is None:
        if sa is None: return None
        d = simdi.date()
        if datetime.datetime.combine(d, datetime.time(sa, dk)) <= simdi: d += datetime.timedelta(days=1)
    if sa is None: sa, dk = 9, 0
    return datetime.datetime.combine(d, datetime.time(sa, dk)).strftime("%Y-%m-%dT%H:%M")
_GOREV = {"dosya": None, "oneri": [], "sahipsiz_t": 0.0, "sahipsiz_n": 0, "hitapsiz_n": 0, "bekleyen": False}
def _gorev_toplanti():  # öneri sayaçları ve "önerildi" listesi toplantı başına
    d = (aktif_dosya() if "aktif_dosya" in globals() else None) or STATE.get("meeting")
    if _GOREV["dosya"] != d: _GOREV.update(dosya=d, oneri=[], sahipsiz_t=0.0, sahipsiz_n=0, hitapsiz_n=0, bekleyen=False)
    return d
def _gorev_benzer(s, o):  # öneri yinelemesi: talimat benzerliğinden gevşek (aynı iş başka sözcüklerle yeniden söylenir)
    k = len(s & o)
    return bool(k) and (k / len(s | o) >= 0.5 or k / min(len(s), len(o)) >= 0.6)
def _gorev_ayrinti(x):
    try: a = json.loads(x.get("ayrinti") or "{}")
    except (ValueError, TypeError): a = {}
    return a if isinstance(a, dict) else {}
def _gorev_onerildi(metin):  # bu toplantıda benzer iş önerildi mi (reddedilen dahil) ya da eylem kuyruğunda var mı
    s = _sozcukler(metin)
    if not s: return True
    if any(_gorev_benzer(s, o) for o in _GOREV["oneri"]): return True
    with LOCK: xs = [x for x in EYLEMLER if _GOREV["dosya"] and x.get("file") == _GOREV["dosya"]]
    return any(_gorev_benzer(s, _sozcukler(f"{x.get('baslik') or ''} {_gorev_ayrinti(x).get('metin') or ''}")) for x in xs)
def _gorev_oturum_acti(t):  # toplantı oturumu (ya da asistanın kendi yolu) t'den sonra bir iş açtı mı — öneri dışında
    sinir = datetime.datetime.fromtimestamp(t - 2).isoformat(timespec="seconds")
    with LOCK: return next((x for x in reversed(EYLEMLER) if str(x.get("at") or "") >= sinir and not _gorev_ayrinti(x).get("oneri")), None)
def _gorev_baglam(t, metin, en_cok):  # kullanıcının bu sözden hemen önceki satırları: geriye doğru, aralarında GOREV_BOSLUK_SN'den uzun sessizlik olmayan
    out = []; sm = _sozcukler(metin); son = t  # (en çok GOREV_BAGLAM_SN geriye; Whisper ve altyazı yinelemesi bir kez). Boşluk konu değişimi sayılır: 3 Kasım denemesi
    for t_, _k, m, ben in reversed(list(SON_SATIRLAR)):  # (sesli okunan ekran metni sonraki "takvime eklesin"in iletisine karışıyordu)
        if not ben or t_ > t: continue
        if son - t_ > GOREV_BOSLUK_SN or t - t_ > GOREV_BAGLAM_SN or len(out) >= en_cok: break
        m = " ".join(str(m).replace("Claude:", " ").split()); s = _sozcukler(m); son = t_
        if len(s) < 2 or _talimat_benzer(s, sm) or any(_talimat_benzer(s, _sozcukler(o)) for o in out): continue
        out.insert(0, m)
    return out
def gorev_hitapsiz(metin):  # ingest (LOCK altında: burada LOCK alınmaz, yineleme denetimi iş parçacığında): kullanıcının hitapsız Whisper satırı iş sözüne benziyor → None: görev çıkarma kapalı (eski kural: atılır), True: ele alındı
    if AYAR.get("talimat") is False or not toplanti_var() or not ("gorev_cikar_acik" in globals() and gorev_cikar_acik()): return None
    c = talimat_coz(metin); ist = GOREV_ISTEK_RX.search(metin)
    if not c and not GOREV_IS_RX.search(metin): print(f"GÖREV: hitapsız söz iş sayılmadı (iş fiili yok) — \"{metin[:60]}\""); return True
    if not ist: print(f"GÖREV: hitapsız söz iş sayılmadı ({'geçmiş zaman' if GOREV_GECMIS_RX.search(metin) else 'istek kipi yok'}) — \"{metin[:60]}\""); return True
    _gorev_toplanti(); t = time.time()
    if _GOREV["hitapsiz_n"] >= GOREV_HITAPSIZ_EN_COK: print(f"GÖREV: bu toplantıda {GOREV_HITAPSIZ_EN_COK} öneri oldu — öneri yok — \"{metin[:60]}\""); return True
    baglamsiz = bool(GOREV_BAGLAMSIZ_RX.search(metin))
    if c and c[0] == "oturum":
        tur, h, ileti = c
        if baglamsiz or len(ileti.split()) < 4: ileti = " ".join(_gorev_baglam(t, metin, 4) + [metin])
    elif c: tur, h, ileti = c
    else:
        tur, h, ileti = "yapilacak", None, metin
        if baglamsiz or len(metin.split()) < 6: ileti = " ".join(_gorev_baglam(t, metin, 2) + [metin])
    ileti = _talimat_temiz(ileti)
    if len(ileti) > TALIMAT_EN_COK: ileti = ileti[-TALIMAT_EN_COK:].split(" ", 1)[-1]  # baştan kısalt: istek satırı kalsın
    neden = _t("Adımı söylemeden söyledin; yapmamı istersen Onayla.", "You said it without my name; approve if you want it done.")
    print(f"GÖREV: hitapsız iş sözü öneri adayı ({tur}{' → ' + h['ad'] if h else ''}) — \"{metin[:60]}\"")
    zaman = (saat_coz(metin) or saat_coz(ileti)) if tur == "yapilacak" else None
    threading.Thread(target=_gorev_sun, args=(tur, h, ileti, metin, t, neden, zaman), daemon=True).start(); return True
def _gorev_sun(tur, h, ileti, metin, t, neden, zaman=None):  # ayrı iş parçacığında (ingest LOCK'u bırakınca): yineleme, toplantı oturumu, onay kartı
    if _gorev_onerildi(ileti): print(f"GÖREV: benzer iş bu toplantıda önerildi — yinelenmedi — \"{metin[:60]}\""); return
    _GOREV["hitapsiz_n"] += 1; _GOREV["oneri"].append(_sozcukler(ileti))
    if "topo_izliyor" in globals() and topo_izliyor():  # toplantı oturumu da izliyor (işaretsiz iş talimatını o da yapar): önce o, çift kart olmasın
        time.sleep(GOREV_OTURUM_BEKLE_SN); x = _gorev_oturum_acti(t)
        if x: print(f"GÖREV: toplantı oturumu iş açtı ({x['id']}) — öneri açılmadı"); return
    if toplanti_var(): talimat_kuyruk(tur, h, ileti, metin, "gorev", claude=True, oneri=neden, zaman=zaman)
def gorev_satir(metin, kim, ben):  # ingest (LOCK altında: burada LOCK alınmaz), her yeni satır (iki kanal): sahipsiz iş adayı → GOREV_SAHIP_SN sonra bakılır
    if AYAR.get("talimat") is False or not metin or "Claude:" in metin or not GOREV_SAHIPSIZ_RX.search(metin): return
    if not toplanti_var() or not ("gorev_cikar_acik" in globals() and gorev_cikar_acik()): return
    if gorev_anlatim_mi(metin): print(f"GÖREV: durum anlatımı iş sayılmadı — \"{metin[:60]}\""); return
    if GOREV_SAHIPLI_RX.search(metin) or GOREV_USTLEN_RX.search(metin): print(f"GÖREV: işin sahibi sözde var — öneri yok — \"{metin[:60]}\""); return
    _gorev_toplanti()
    if _GOREV["bekleyen"] or _GOREV["sahipsiz_n"] >= GOREV_SAHIPSIZ_EN_COK or time.time() - _GOREV["sahipsiz_t"] < GOREV_SAHIPSIZ_ARA_SN:
        print(f"GÖREV: sahipsiz iş adayı — seyreklik sınırı, öneri yok — \"{metin[:60]}\""); return
    _GOREV["bekleyen"] = True; print(f"GÖREV: sahipsiz iş adayı — {GOREV_SAHIP_SN} sn üstlenen bekleniyor — \"{metin[:60]}\"")
    threading.Thread(target=_gorev_sahipsiz, args=(metin, kim, ben, time.time()), daemon=True).start()
def _gorev_sahipsiz(metin, kim, ben, t):
    try:
        time.sleep(GOREV_SAHIP_SN)
        with LOCK: sonra = [m for t_, _k, m, _b in list(SON_SATIRLAR) if t_ > t]
        u = next((m for m in sonra if GOREV_USTLEN_RX.search(m)), None)
        if u: print(f"GÖREV: sahipsiz iş adayı üstlenildi (\"{u[:40]}\") — öneri yok"); return
        x = _gorev_oturum_acti(t)
        if x: print(f"GÖREV: sahipsiz iş için toplantı oturumu iş açtı ({x['id']}) — öneri açılmadı"); return
        if not toplanti_var(): return
        if _gorev_onerildi(metin): print(f"GÖREV: sahipsiz iş adayı zaten önerildi ya da kuyrukta — \"{metin[:60]}\""); return
        _GOREV.update(sahipsiz_n=_GOREV["sahipsiz_n"] + 1, sahipsiz_t=time.time()); _GOREV["oneri"].append(_sozcukler(metin))
        kim_ = _t("sen", "you") if ben else (kim or _t("karşı taraf", "the other side"))
        ileti = _t(f"Toplantıda sahipsiz kalan iş ({kim_}): ", f"Unowned task from the meeting ({kim_}): ") + _talimat_temiz(metin)[:TALIMAT_EN_COK - 60]
        talimat_kuyruk("yapilacak", None, ileti, metin, "gorev", claude=True, zaman=saat_coz(metin),
                       oneri=_t("Kimse üstlenmedi; senin işin olsun istersen Onayla (hatırlatma olur).", "Nobody took it; approve to make it your to-do (a reminder)."))
    finally: _GOREV["bekleyen"] = False
def gorev_istem():  # Konuş istemine (talimat_istem): görev çıkaran kişilik konuşmadan çıkan işi öneri olarak hazırlar
    gk = gorev_kisilikleri() if "gorev_kisilikleri" in globals() else []
    if not gk: return ""
    adlar = ", ".join(k["ad"] for k in gk); yalniz = len(kisilikler()) > len(gk)
    return _t(f" Görev çıkarma{f' (yalnız {adlar} olarak cevap verirken)' if yalniz else ''}: kullanıcı açıkça istemese de konuşmada onun üstlendiği ya da kimsenin üstlenmediği somut bir iş "
              "geçerse (ne yapılacağı belli; 'bakarız', 'belki', 'düşünelim' iş değildir) ve 'Hazırladığın işler' listesinde yoksa, cevabın sonuna [İLET yapilacak: <iş; varsa gün ve saatiyle> | <YYYY-MM-DDTHH:MM>] "
              "ile öneri olarak hazırla. Sesli kısımda bunu en çok bir kısa cümleyle an ('Bunu hatırlatma olarak not edebilirim.'); onayı Suflor 'ekleyeyim mi?' diye sorar, eklenmiş gibi konuşma. "
              "Konuşma başına en çok bir öneri; reddedilen ya da zaten hazırlanmış işi yeniden önerme; karşı tarafın sorusuna cevapta kullanma.",
              f" Task extraction{f' (only when answering as {adlar})' if yalniz else ''}: even if the user doesn't ask, when a concrete task comes up that they took on or nobody took "
              "(what to do is clear; 'we'll see', 'maybe', 'let's think' are not tasks) and it isn't in the 'Tasks you prepared' list, end the answer with [İLET yapilacak: <task; day and time if any> | <YYYY-MM-DDTHH:MM>] "
              "as a suggestion. In the spoken part mention it in at most one short sentence ('I can note that as a reminder.'); Suflor asks 'shall I add it?', don't talk as if it was added. "
              "At most one suggestion per conversation; don't re-suggest a rejected or already prepared task; never when answering the other side.")
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
    elif x["tur"] == "toplanti": ok, sonuc = toplanti_sayfa_ac(a)  # v0.143.0
    elif x["tur"] == "sil":  # v0.132.0: asistanın eklediği takvim hatırlatmasını kaldır
        ok, sonuc = takvim_etkinlik_sil(a.get("etkinlik"))
        with LOCK:
            k = next((y for y in EYLEMLER if y["id"] == a.get("kaynak_eylem")), None)
            if ok and k: _eylem_yama(k, silindi=True)
    else:
        ok, sonuc, kimlik = takvim_hatirlatma(a) if a.get("zaman") else (False, "saat yok", None)
        if ok and kimlik:
            with LOCK: _eylem_yama(x, etkinlik=kimlik)
        if not ok:  # saat yok ya da takvime yazılamadı: eski yol — kendine e-posta taslağı
            print(f"TALİMAT: takvime eklenemedi ({sonuc}) — e-posta taslağına düşüldü")
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
def _takvim_yardimci(args, istek=None):  # Suflor Takvim.app (--etkinlik / --etkinlik-sil) → çıktı sözlüğü ya da {"durum": "hata", …}
    app = globals().get("TAKVIM_APP") or ""
    if not os.path.isdir(app): return {"durum": "hata", "hata": "Suflor Takvim.app yok"}
    yol = os.path.join(BASE, "takvim-is-istek.json"); cikti = os.path.join(BASE, "takvim-is-cikti.json")
    try:
        if os.path.exists(cikti): os.remove(cikti)
        if istek is not None:
            fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(istek, f, ensure_ascii=False)
            args = args + [yol]
        subprocess.run(["open", "-g", "-W", "-n", "-a", app, "--args"] + args + ["--cikti", cikti], capture_output=True, timeout=150)
        return json.load(open(cikti, encoding="utf-8"))
    except (OSError, ValueError, subprocess.TimeoutExpired) as e: return {"durum": "hata", "hata": e.__class__.__name__}
    finally:
        for f in (yol, cikti):
            try: os.remove(f)
            except OSError: pass
def takvim_hatirlatma(a):  # v0.132.0 (kullanıcı 25 Ekim: Anımsatıcılar değil takvim): saatli hatırlatma → takvime 15 dk'lık, başında uyaran etkinlik → (ok, sonuç, kimlik)
    is_ = str(a.get("metin") or "").strip(); z = a.get("zaman")
    if not is_ or not z: return False, "saat yok", None
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"TALİMAT (deneme): takvim · {is_[:60]} · {z}"); return True, _t("takvime eklendi (deneme)", "added to calendar (test)"), "deneme-" + z
    o = _takvim_yardimci(["--etkinlik"], {"baslik": is_, "zaman": z, "dk": 15, "not": _t("Suflor.me — sesle eklendi", "Suflor.me — added by voice"),
                                          "takvim": str(AYAR.get("hatirlatma_takvim") or "")})
    if o.get("durum") != "ok": return False, str(o.get("hata") or o.get("durum"))[:120], None
    return True, _t(f"takvime eklendi ({o.get('takvim')}, {z.replace('T', ' ')})", f"added to calendar ({o.get('takvim')}, {z.replace('T', ' ')})"), o.get("id")
def takvim_etkinlik_sil(kimlik):
    if os.environ.get("SUFLOR_TEST_BASLAT"): print(f"TALİMAT (deneme): takvimden silindi · {kimlik}"); return True, _t("takvimden silindi (deneme)", "removed from calendar (test)")
    o = _takvim_yardimci(["--etkinlik-sil", str(kimlik)])
    if o.get("durum") == "ok": return True, _t("takvimden silindi", "removed from calendar")
    if o.get("durum") == "yok": return True, _t("takvimde zaten yoktu", "was no longer in the calendar")
    return False, str(o.get("hata") or o.get("durum"))[:120]
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
