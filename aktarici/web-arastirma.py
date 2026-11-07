# Toplantı dışı derin web araştırması (S243, 6 Kasım; v0.204.0). "X'i araştır", "şu firma hakkında ne biliniyor", "dünkü olay ne" gibi istek Konuş'ta (bas-konuş) ya da
# pano kutusunda araştırma kipine girer: ayrı bir `claude -p` çağrısı yalnız WebSearch/WebFetch ile çok sorgulu, en az 3 bağımsız kaynaklı, kaynak bağlantılı ve tarihli
# bir rapor üretir; sesli kısa özet Konuş cevabına, kaynaklı tam metin `canli/arastirma/<id>.json|.md`'ye (panoda "---" sonrası ayrıntı) gider. Toplantı sürerken davranış
# değişmez (toplantıdaki araştırma toplanti-oturum.py, S208). Gizli kipte araştırma yok.
# GİZLİLİK (S208 sınırı): arama motoruna yalnız ad ve konu gider. İstemde: kullanıcının kendi cümlesinden çıkan konu + (kişiyse) Mac Kişiler'deki KURUM adı ayırt edici olarak.
# Yerel bilgi (Kişiler kaydı, geçmiş toplantı başlıkları) Claude'a GİTMEZ; aktarıcıda araştırma kaydına "Yerel bilgi" olarak sonradan eklenir. Döküm alıntısı, iç sayı,
# toplantı içeriği, dosya adı, e-posta/telefon/adres istemde yok. Ayar: web_arastirma (ana şalter, toplantıyı da kapatır) VE web_arastirma_disari (toplantı dışı, varsayılan açık).
# Yalnız sağlayıcı Claude Code iken (beyin ayarı başka sağlayıcıysa metin onun dışına çıkmaz: araştırma kapalı, sebebi söylenir).
import re as _re_ar
AR_DIR = os.path.join(BASE, "arastirma"); AR_EN_COK = 200; AR_BEKLE_SN = 15; AR_ZAMAN = 420
ARASTIRMA = {"aktif": None, "son": None}
_AR_ISARET = "[ARAŞTIRMA]"
def _ar_k(s): return str(s or "").replace("İ", "i").replace("I", "ı").lower()  # 1:1 uzunluk (Türkçe i/ı), konu orijinal harfle kesilir
_AR_EK = r"(?:derinlemesine |detaylı |ayrıntılı |kapsamlı |derin |web'?de |internette |bir güzel |ayrıca )*"
_AR_RX = [
    _re_ar.compile(r"^(?:lütfen |bana |şunu |bir )*(?:araştır\w*|araştırma yap\w*)[:,]?\s+(?P<k>.{3,160})$"),
    _re_ar.compile(r"^(?:lütfen |bana |bir )*(?P<k>.{3,160}?)\s+(?:hakkında|ile ilgili|konusunda|üzerine|için)\s+" + _AR_EK + r"(?:bir |biraz )?(?:araştırma yap\w*|araştır\w*|bilgi (?:bul|topla|ver)\w*)"),
    _re_ar.compile(r"^(?:lütfen |bana |bir )*(?P<k>.{3,160}?)\s+" + _AR_EK + r"araştır\w*"),
    _re_ar.compile(r"^(?P<k>.{3,160}?)\s+(?:hakkında|ile ilgili)\s+ne\s+(?:biliniyor|biliyoruz|biliyorsun|var|duydun|çıkıyor|bulabilirsin)"),
    _re_ar.compile(r"^(?P<k>(?:dünkü|bugünkü|az önceki|geçen haftaki|son|dün)\s+.{0,80}?(?:olay|gelişme|haber|saldırı|deprem|kaza|açıklama|karar)\w*)\s+(?:ne|neydi|nedir|neymiş|ne oldu|hakkında ne)\b"),
    _re_ar.compile(r"^(?:please )?(?:research|look up|look into|investigate)\s+(?P<k>.{3,160})$"),
    _re_ar.compile(r"^(?:what(?:'s| is) known about|what do we know about|tell me what(?:'s| is) out there on)\s+(?P<k>.{3,160})$"),
]
# yerel arama ya da erteleme/iş devri: araştırma kipi değil
_AR_IC = _re_ar.compile(r"\b(projede|projemizde|dosya\w*|döküm\w*|kayıtlar\w*|toplantılarda|toplantıda|defter\w*|veritaban\w*|mail\w*|e-?posta\w*|notlar\w*|takvim\w*|belgeler\w*|klasör\w*|arşiv\w*)\b")
_AR_ERTELE = _re_ar.compile(r"\b(yarın|haftaya|hatırlat\w*|not al\w*|not et\w*|yapılacak\w*|listeme|iş ata\w*|ata|ekle|kuyruğa|ayarla|planla)\b")
_AR_BELIRSIZ = _re_ar.compile(r"^(?:şu|bu|o|şu anki|bahsettiğim|az önce bahsettiğim)\s+\w+$")
def ar_tetik(metin):  # → None (araştırma isteği değil) | "" (konu belirsiz: sorulacak) | konu (kullanıcının kendi sözünden, orijinal harfle)
    m = " ".join(str(metin or "").split()); k = _ar_k(m).rstrip(" .!?…"); k0 = m[:len(k)]
    if len(k) < 8 or _AR_IC.search(k) or _AR_ERTELE.search(k): return None
    for rx in _AR_RX:
        r = rx.search(k)
        if not r: continue
        konu = k0[r.start("k"):r.end("k")].strip(" ,.:;!?…'\"’")
        konu = _re_ar.sub(r"['’]\w{1,4}$", "", konu).strip()
        if _re_ar.sub(r"(?i)^(?:lütfen|bana|şunu|bir)\s+", "", konu) != konu: konu = _re_ar.sub(r"(?i)^(?:lütfen|bana|şunu|bir)\s+", "", konu)
        if len(konu) < 3: return ""
        return "" if _AR_BELIRSIZ.match(_ar_k(konu)) else konu[:160]
    return None
def ar_acik():  # → (açık mı, kapalıysa sebep)
    if AYAR.get("web_arastirma") is False or AYAR.get("web_arastirma_disari") is False: return False, _t("Web araştırması kapalı (ayar web_arastirma_disari)", "Web research is off (setting web_arastirma_disari)")
    if gizli_acik(): return False, _t("Gizli kipte web araştırması yok", "No web research in private mode")
    if BEYIN.secim(AYAR, "konus")["tur"] != "claude-code": return False, _t("Web araştırması yalnız Claude Code sağlayıcısıyla çalışır (metin seçtiğin sağlayıcının dışına çıkmaz)", "Web research only works with the Claude Code provider (text never leaves your chosen provider)")
    if not claude_yolu(): return False, _t("Claude Code komut satırı (claude) bulunamadı", "Claude Code command line (claude) not found")
    return True, ""
def _ar_kisi_mi(konu):  # 2–3 sözcük, hepsi büyük harfle başlıyor: kişi adı gibi (ayırt edici kurum Kişiler'den aranır)
    w = konu.split(); return 2 <= len(w) <= 3 and all(x[:1].isupper() and not any(c.isdigit() for c in x) for x in w)
def ar_yerel(konu):  # → (ayırt edici kurum ya da "", yerel satırlar). Satırlar Claude'a gitmez; araştırma kaydına eklenir.
    kurum, sat = "", []
    if _ar_kisi_mi(konu) and "kisi_bul" in globals():
        try: o = kisi_bul(konu)
        except Exception: o = {}
        ks = o.get("kisiler") or [] if o.get("durum") == "ok" else []
        if ks:
            sat += [_t("Kişiler: ", "Contacts: ") + c["ad"] + (f" ({c['kurum']})" if c.get("kurum") else "") for c in ks[:3]]
            if len(ks) == 1 and ks[0].get("kurum"): kurum = ks[0]["kurum"][:80]  # tek eşleşme: kurum ayırt edici olarak aramaya girer (ad + kurum)
    if "arsiv_ara" in globals():
        try:
            a = arsiv_ara(konu)
            if a.get("tam"):
                g = {}
                for s in a.get("sonuclar") or []: g.setdefault(s["id"], (s.get("baslik") or s["id"], str(s.get("at") or "")[:10]))
                sat += [_t("Geçmiş toplantı: ", "Past meeting: ") + f"{b} ({t})" if t else _t("Geçmiş toplantı: ", "Past meeting: ") + b for b, t in list(g.values())[:5]]
        except Exception: pass
    return kurum, sat
AR_ISTEM = """Sen bir araştırma yardımcısısın. Aşağıdaki konuyu internette (WebSearch ve WebFetch) derinlemesine ve doğrulanabilir biçimde araştır. Bugünün tarihi: {tarih}.
KONU: {konu}{ayirt}

YÖNTEM
- Tek arama yetmez: en az 4 farklı sorgu yaz (konunun adı, resmî adı, Türkçe ve gerekirse İngilizce, son gelişme, çelişkiyi sınayan sorgu). Bulduğun önemli sayfaları WebFetch ile aç, arama özetine güvenme.
- En az 3 BAĞIMSIZ kaynak ara (aynı haberi yeniden yazan siteler tek kaynak sayılır). Birincil kaynağı tercih et: resmî site, ticaret sicili/kamu kaydı, kurumun kendi açıklaması, haber ajansı; blog, forum ve sosyal medya ikincildir.
- Her iddianın yanında kaynak bağlantısı ve yayın/güncelleme tarihi olsun. Tarihi bulamazsan "tarih yok" yaz. Bilgi eskiyse (bir yıldan eski) bunu söyle.
- Kaynaklar çelişirse çelişkiyi açıkça yaz (hangi kaynak ne diyor). Doğrulayamadığın, tek kaynaktan gelen ya da kulaktan dolma bilgiyi "doğrulanamadı" diye ayrı işaretle; uydurma, tahminle tamamlama.
- Aramaya YALNIZ konunun adı ve konuyu belirten sözcükler gider. Başka hiçbir bilgi (iç sayı, toplantı, belge, kişisel ayrıntı) arama metnine girmez. Kişi hakkında yalnız herkese açık, mesleki bilgi ara; adres, telefon, aile, sağlık gibi özel bilgi arama ve yazma.
- Konu belirsizse (ör. "dünkü olay") en çok haber olan ilk birkaç olayı kısaca sırala, hangisini kastettiğini sonda sor.

ÇIKTI BİÇİMİ (başlıklar aynen, Türkçe yaz, başka metin ekleme)
[SESLİ]
Konuşarak okunacak EN ÇOK 3 kısa cümle ve 45 kelime: en önemli bulgu, sonra güven düzeyi (kaç bağımsız kaynak, çelişki var mı, neyi doğrulayamadın). Bağlantı, parantez, madde işareti, ayrıntılı rakam listesi yok; ayrıntı [METİN]'de.
[METİN]
Markdown: kısa özet; sonra başlıklar altında bulgular. Her iddianın sonunda ([site adı](bağlantı), tarih). "## Çelişkiler" ve "## Doğrulanamadı" bölümleri (yoksa "yok" yaz).
[KAYNAKLAR]
Her satır: <tam bağlantı> | <site ya da sayfa adı> | <yayın tarihi ya da tarih yok> | birincil ya da ikincil
"""
def ar_istem(konu, kurum=""):
    ay = f"\nAyırt edici ipucu (aramada ad ile birlikte kullanabilirsin): {kurum}" if kurum else ""
    return AR_ISTEM.format(tarih=datetime.date.today().strftime("%d.%m.%Y"), konu=konu, ayirt=ay)
def _ar_alan_adi(url):
    m = _re_ar.match(r"^https?://([^/:?#\s]+)", str(url or "").strip().lower())
    if not m: return None
    p = m.group(1).split("."); return ".".join(p[-3:] if len(p) >= 3 and p[-2] in ("com", "org", "net", "gov", "edu", "co") else p[-2:])
def ar_ayristir(cikti):  # model çıktısı → {sesli, metin, kaynaklar [{url, baslik, tarih, tur}]}; başlık eksikse tüm çıktı metin olur
    c = str(cikti or ""); bol = {}
    for ad in ("SESLİ", "METİN", "KAYNAKLAR"):
        r = _re_ar.search(r"\[" + ad + r"\]\s*\n(.*?)(?=\n\[(?:SESLİ|METİN|KAYNAKLAR)\]|\Z)", c, _re_ar.S)
        if r: bol[ad] = r.group(1).strip()
    kay = []
    for s in (bol.get("KAYNAKLAR") or "").splitlines():
        p = [x.strip(" -*•") for x in s.split("|")]
        if p and _re_ar.match(r"^https?://\S+$", p[0]) and p[0] not in [k["url"] for k in kay]:
            kay.append({"url": p[0][:300], "baslik": (p[1] if len(p) > 1 else "")[:120], "tarih": (p[2] if len(p) > 2 else "")[:40], "tur": "birincil" if len(p) > 3 and "birincil" in p[3].lower() else "ikincil"})
    metin = bol.get("METİN") or ("" if bol.get("SESLİ") else c.strip())
    return {"sesli": bol.get("SESLİ") or "", "metin": metin, "kaynaklar": kay[:40]}
def ar_calistir(konu, kurum="", zaman=AR_ZAMAN):  # → {"ok", "cikti", "sorgular", "sayfalar", "maliyet", "tur", "api_ms", "hata"}; claude doğrudan (cwd BASE: Masaüstü gerekmez)
    cl = claude_yolu(); args = [cl] + BEYIN.arastirma_args(AYAR); t0 = time.time()
    o = {"ok": False, "cikti": "", "sorgular": [], "sayfalar": [], "maliyet": 0.0, "tur": None, "api_ms": None, "hata": None}
    try: p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=BASE, text=True, encoding="utf-8", bufsize=1)
    except OSError as e: o["hata"] = e.__class__.__name__; return o
    kes = threading.Timer(zaman, lambda: p.kill()); kes.daemon = True; kes.start()
    try:
        p.stdin.write(ar_istem(konu, kurum)); p.stdin.close()
        for s in p.stdout:
            try: j = json.loads(s)
            except ValueError: continue
            if j.get("type") == "assistant":
                for b in (j.get("message") or {}).get("content") or []:
                    if b.get("type") != "tool_use": continue
                    gi = b.get("input") or {}
                    if b.get("name") == "WebSearch" and gi.get("query"): o["sorgular"].append(str(gi["query"])[:200])
                    elif b.get("name") == "WebFetch" and gi.get("url"): o["sayfalar"].append(str(gi["url"])[:300])
            elif j.get("type") == "result":
                o.update(cikti=str(j.get("result") or ""), maliyet=round(j.get("total_cost_usd") or 0, 4), tur=j.get("num_turns"), api_ms=j.get("duration_api_ms"), ok=not j.get("is_error"))
                if j.get("is_error"): o["hata"] = str(j.get("result") or "")[:160]
        p.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired, ValueError) as e: o["hata"] = e.__class__.__name__
    finally:
        kes.cancel()
        if p.poll() is None: p.kill()
    if not o["ok"] and not o["hata"]: o["hata"] = "zaman aşımı" if time.time() - t0 >= zaman - 1 else "çıktı yok"
    o["sure_ms"] = round((time.time() - t0) * 1000); return o
def _ar_slug(konu): return (_re_ar.sub(r"[^a-z0-9]+", "-", _ar_k(konu).translate(str.maketrans("çğıöşü", "cgiosu"))).strip("-") or "konu")[:40]
def ar_kaydet(konu, kanal, sonuc, yerel):  # canli/arastirma/<id>.json (+ .md, 0600) ve claude-cagri.jsonl is: arastirma → {id, kayit}
    simdi = datetime.datetime.now().astimezone(); i = simdi.strftime("%Y%m%d-%H%M%S") + "-" + _ar_slug(konu); ay = ar_ayristir(sonuc.get("cikti"))
    bag = sorted({_ar_alan_adi(k["url"]) for k in ay["kaynaklar"] if _ar_alan_adi(k["url"])})
    uyari = []
    if sonuc.get("ok") and len(bag) < 3: uyari.append(_t(f"Yalnız {len(bag)} bağımsız kaynak bulundu; bilgi doğrulanmadı sayılmalı.", f"Only {len(bag)} independent source(s) found; treat as unverified."))
    kayit = {"surum": 1, "id": i, "at": simdi.isoformat(timespec="seconds"), "konu": konu, "kanal": kanal, "durum": "ok" if sonuc.get("ok") and ay["metin"] else "hata",
             "sure_sn": round((sonuc.get("sure_ms") or 0) / 1000, 1), "maliyet": sonuc.get("maliyet"), "sorgu_sayisi": len(sonuc.get("sorgular") or []), "sayfa_sayisi": len(sonuc.get("sayfalar") or []),
             "kaynak_sayisi": len(ay["kaynaklar"]), "bagimsiz_kaynak": len(bag), "sorgular": sonuc.get("sorgular") or [], "sesli": ay["sesli"], "metin": ay["metin"], "kaynaklar": ay["kaynaklar"],
             "yerel": yerel, "uyari": uyari, "hata": sonuc.get("hata")}
    try:
        os.makedirs(AR_DIR, mode=0o700, exist_ok=True)
        md = f"# {konu}\n\n_{kayit['at'][:16]} · {kayit['bagimsiz_kaynak']} bağımsız kaynak · {kayit['sorgu_sayisi']} sorgu_\n\n" + "".join(f"> {u}\n" for u in uyari) + ("\n" if uyari else "") + ay["metin"] \
             + ("\n\n## Kaynaklar\n" + "\n".join(f"- [{k['baslik'] or k['url']}]({k['url']}) · {k['tarih']} · {k['tur']}" for k in ay["kaynaklar"]) if ay["kaynaklar"] else "") \
             + ("\n\n## Yerel bilgi (aramaya gitmedi)\n" + "\n".join("- " + s for s in yerel) if yerel else "") + "\n"
        for ek, ic in ((".json", json.dumps(kayit, ensure_ascii=False, indent=1)), (".md", md)):
            fd = os.open(os.path.join(AR_DIR, i + ek), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(ic)
        for eski in sorted((f for f in os.listdir(AR_DIR) if f.endswith(".json")), key=lambda f: os.stat(os.path.join(AR_DIR, f)).st_mtime_ns)[:-AR_EN_COK]:
            for ek in (".json", ".md"):
                try: os.remove(os.path.join(AR_DIR, eski[:-5] + ek))
                except OSError: pass
    except OSError as e: print(f"ARAŞTIRMA: kayıt yazılamadı ({e.__class__.__name__})")
    o = {"at": kayit["at"], "is": "arastirma", "saglayici": "claude-code", "model": BEYIN.arastirma_model(AYAR), "sure_ms": sonuc.get("sure_ms"), "api_ms": sonuc.get("api_ms"), "duvar_ms": sonuc.get("sure_ms"),
         "tur": sonuc.get("tur"), "maliyet": kayit["maliyet"] or 0, "sorgu": kayit["sorgu_sayisi"], "sayfa": kayit["sayfa_sayisi"], "kaynak": kayit["kaynak_sayisi"], "bagimsiz": kayit["bagimsiz_kaynak"],
         "kanal": kanal, "hata": kayit["durum"] != "ok"}
    with LOCK: write([(os.path.join(BASE, "claude-cagri.jsonl"), json.dumps(o, ensure_ascii=False) + "\n")])
    return kayit
def ar_cevap(kayit):  # Konuş cevabı: sesli kısa özet, "---", kaynaklı tam metin (pano "---" sonrasını ayrıntı gösterir)
    if kayit["durum"] != "ok": return _t("Araştırma tamamlanamadı: ", "Research didn't finish: ") + (kayit.get("hata") or "?"), ""
    sesli = kayit["sesli"] or " ".join(_re_ar.split(r"(?<=[.!?])\s+", _re_ar.sub(r"[#*\[\]()>`_]", "", kayit["metin"]))[:2])[:400]
    if kayit["uyari"]: sesli = (sesli + " " + kayit["uyari"][0]).strip()
    yaz = kayit["metin"] + ("\n\n" + "\n".join(f"- [{k['baslik'] or k['url']}]({k['url']}) · {k['tarih']}" for k in kayit["kaynaklar"]) if kayit["kaynaklar"] else "") \
          + "\n\n" + _t(f"Kayıt: {kayit['id']} ({kayit['bagimsiz_kaynak']} bağımsız kaynak, {kayit['sure_sn']} sn)", f"Record: {kayit['id']} ({kayit['bagimsiz_kaynak']} independent sources, {kayit['sure_sn']} s)")
    if kayit["yerel"]: yaz += "\n\n" + _t("Yerel bilgi (aramaya gitmedi):\n", "Local info (not sent to search):\n") + "\n".join("- " + s for s in kayit["yerel"])
    return sesli, yaz
def _ar_is(konu, kanal, metin, sesli_ac):
    t0 = time.time(); bekledi = []
    def bekle():
        if ARASTIRMA["aktif"] and sesli_ac and not bekledi:
            bekledi.append(1); seslendir(_t("Araştırıyorum, biraz sürebilir.", "Researching, this may take a moment."), kuyruk=True)
    tm = threading.Timer(AR_BEKLE_SN, bekle); tm.daemon = True; tm.start()
    try:
        kurum, yerel = ar_yerel(konu); sonuc = ar_calistir(konu, kurum); kayit = ar_kaydet(konu, kanal, sonuc, yerel)
        sesli, yaz = ar_cevap(kayit); ARASTIRMA["son"] = {"id": kayit["id"], "konu": konu, "durum": kayit["durum"], "sure_sn": kayit["sure_sn"], "kaynak": kayit["bagimsiz_kaynak"]}
        print(f"ARAŞTIRMA: bitti ({kayit['durum']}, {kayit['sure_sn']} sn, {kayit['sorgu_sayisi']} sorgu, {kayit['sayfa_sayisi']} sayfa, {kayit['bagimsiz_kaynak']} bağımsız kaynak, ${kayit['maliyet']}) kanal={kanal} id={kayit['id']}")
        if not _KS.get("tur") or _KS["tur"].get("arastirma"):  # araya başka soru girmediyse Konuş cevabı
            _KS["tur"] = None; _konus_kur(durum="hazir", soru=metin, cevap=sesli + ("\n\n---\n" + yaz if yaz else ""), hata=None)
        if sesli_ac and sesli: seslendir(sesli, kuyruk=True)
    except Exception as e:
        print(f"ARAŞTIRMA: hata {e.__class__.__name__}: {e}")
        if not _KS.get("tur") or _KS["tur"].get("arastirma"): _KS["tur"] = None; _konus_kur(durum="hata", hata=_t("Araştırma yapılamadı", "Research failed"))
    finally: tm.cancel(); ARASTIRMA["aktif"] = None
def arastirma_dene(metin, tur):  # _konus_sor'un başında: True → istek araştırma kipine alındı (Konuş soruyu normal yola götürmez)
    if toplanti_var() or tur.get("kaynak") in ("hitap", "karsi", "moderator"): return False  # toplantı sırasındaki davranış değişmez
    konu = ar_tetik(metin)
    if konu is None: return False
    kanal = "kutu" if tur.get("kutu") else "yazili" if tur.get("yazili") else "bas"; sesli_ac = not tur.get("yazili")
    if AYAR.get("web_arastirma") is False or AYAR.get("web_arastirma_disari") is False: return False  # kapalıysa soru bugünkü gibi asistana gider
    ok, neden = ar_acik()
    if not ok: _KS["tur"] = None; _konus_kur(durum="hazir", soru=metin, cevap=neden); (sesli_ac and seslendir(neden, kuyruk=True)); return True
    if not konu:
        m = _t("Hangi kişi, firma ya da olayı araştırayım? Adını söyle ya da yaz.", "Which person, company or event should I research? Give me the name.")
        _KS["tur"] = None; _konus_kur(durum="hazir", soru=metin, cevap=m); (sesli_ac and seslendir(m, kuyruk=True)); return True
    if ARASTIRMA["aktif"]:
        m = _t(f"Bir araştırma sürüyor ({ARASTIRMA['aktif']}); bitince sorarım.", f"A research is already running ({ARASTIRMA['aktif']}).")
        _KS["tur"] = None; _konus_kur(durum="hazir", soru=metin, cevap=m); return True
    ARASTIRMA["aktif"] = konu; _KS["tur"] = None; _konus_kur(durum="dusunuyor", soru=metin, cevap="", hata=None)
    print(f"ARAŞTIRMA: başladı kanal={kanal} konu={konu!r}")
    threading.Thread(target=_ar_is, args=(konu, kanal, metin, sesli_ac), daemon=True).start(); return True
def arastirma_view(id_=None):  # GET /arastirma (son 20 özet) · ?id=<kayıt> (tam kayıt); pano için kayıt biçimi canli/arastirma/<id>.json
    if id_:
        if not _re_ar.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-z0-9-]{1,40}", str(id_)): return {"hata": "id"}
        try: return json.load(open(os.path.join(AR_DIR, id_ + ".json"), encoding="utf-8"))
        except (OSError, ValueError): return {"hata": "yok"}
    liste = []
    try: dos = sorted((f for f in os.listdir(AR_DIR) if f.endswith(".json")), key=lambda f: os.stat(os.path.join(AR_DIR, f)).st_mtime_ns)[-20:][::-1]
    except OSError: dos = []
    for f in dos:
        try: k = json.load(open(os.path.join(AR_DIR, f), encoding="utf-8"))
        except (OSError, ValueError): continue
        liste.append({x: k.get(x) for x in ("id", "at", "konu", "kanal", "durum", "sure_sn", "bagimsiz_kaynak", "kaynak_sayisi", "sesli", "uyari")})
    return {"aktif": ARASTIRMA["aktif"], "son": ARASTIRMA["son"], "kayitlar": liste}
