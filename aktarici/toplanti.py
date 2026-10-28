# --- Tek toplantı kaydı (Faz B, v0.149.0; mimari plan §3 ilke 1–2, S162–S165; tasarım planlar/faz-b-tasarim.md) ------------------------------------
# Toplantının adı, dosyası, platformu, başlangıç ve bitişi yalnız burada: TOPLANTI["aktif"] (süren) ve TOPLANTI["onceki"] (son biten). Durum akışı:
#   boş → algılandı (dosya bir kez açılır) → sürüyor (ilk satır ya da güvenli sinyal) → bitiyor (sinyal SINYAL_SN yok ya da açık çıkış) → bitti → boş
# bitiyor'dayken sinyal dönerse aynı dosyada sürer (kısa kopma, sekme yenileme, web↔masaüstü); BITIYOR_SN dolup Whisper kuyruğunda o toplantının parçası
# kalmayınca (en çok KUYRUK_BEKLE_SN) bitti. Biten toplantıya satır yazılmaz (S163): geç gelen satır günlüğe ve gec_atilan sayacına.
# Sinyaller: menü uygulaması (masaüstü toplantıda) ve eklenti (bir sekme çağrıda) güvenli; ses yardımcısı (toplantı uygulaması/tarayıcı mikrofonu tutuyor)
# tek başına yalnız takvimde ±TAKVIM_PAY_DK toplantı ya da elle Başlat varsa açar ve Claude oturumu yerine öneri kartı çıkarır (S162). Eklenti kapı değil (S165):
# ad ve dosya kararı vermez, durumu sekme başına tutulur (EKLENTI), yokken hiçbir şey durmaz. Ad: elle Başlat konusu (toplantı açılmadan önce, ≤ 30 dk) →
# takvim konusu → "<Platform> toplantısı HH:MM"; pencere/sekme başlığı ve Meet kodu ad olmaz. STATE["meeting"/"file"], toplanti_var(), aktif_dosya()
# bu kayıttan türer. Durum canli/toplanti.json'a (geçişte ve 5 sn'de bir) yazılır; aktarıcı yeniden başlayınca oradan kurulur.
_TH = bool(os.environ.get("SUFLOR_TEST_HIZLI"))
SINYAL_SN = 6 if _TH else 30          # bir sinyal bu kadar tazeyse var; sürüyor'da hepsi bu kadar yoksa (ve satır yoksa) bitiyor
BITIYOR_SN = float(os.environ.get("SUFLOR_TEST_BITIYOR_SN") or (8 if _TH else 90))
SINYALSIZ_SN = 1200                   # hiç sinyal görmemiş (yalnız satırla açılan) kayıt son satırdan bu kadar sonra biter — eski 20 dk kuralı
SES_SESSIZ_SN, SATIRSIZ_SN = (6, 8) if _TH else (60, 300)  # ses sinyali: mikrofon tutuluyor + bu kadar içinde ses ya da satır
ALGILANDI_BEKLE_SN = 10 if _TH else 120  # zayıf sinyalle algılanıp hiç satır gelmeden sinyal kaybolursa kayıt silinir
BASLAT_BEKLE_DK = 30                  # Başlat'la açılan kayıt bu kadar satırsız bekler; elle Başlat konusu bu kadar ad olur
ON_PAY_SN = 10                        # toplantı algılanmadan hemen önce söylenen söz de o toplantıya
KUYRUK_BEKLE_SN = 20 if _TH else 300  # bitti için Whisper kuyruğunun boşalması en çok bu kadar beklenir
TAKVIM_PAY_DK = OTO_ESLE_DK = 15
BITIR_KILIT_SN = 600                  # elle bitirince aynı sinyal sürse de bu kadar (ya da sinyal 10 sn kesilene dek) yeniden açılmaz
EKLENTI_GOR_SN = 25; EKLENTI_DUS_SN = 120
TOPLANTI = {"aktif": None, "onceki": None, "kilit": None}
OTO = TOPLANTI  # eski ad (duman, saglik): OTO["aktif"] süren kayıt
EKLENTI = {}  # sekme → eklentinin son durumu (sekme kimliği content.js'te sayfa başına; eski eklenti "eski-<platform>")
TOPLANTI_FP = os.path.join(BASE, "toplanti.json")
MASAUSTU_PLATFORM = {"Teams": "teams", "Zoom": "zoom", "zoom.us": "zoom", "Microsoft Teams": "teams"}
if "EYLEM_TUR" in globals(): EYLEM_TUR["baslat"] = "Başlat"  # öneri kartının yerel işi

def url_platform(u):
    u = str(u or "").lower()
    if re.search(r"https://([a-z0-9-]+\.)*(teams\.microsoft\.com|teams\.live\.com|teams\.cloud\.microsoft)", u): return "teams"
    if "://meet.google.com" in u: return "meet"
    if re.search(r"https://([a-z0-9-]+\.)?zoom\.us", u): return "zoom"
    return None

# --- eklenti: sekme başına durum ----------------------------------------------------------------------------------------------------------------------------
def eklenti_nabiz(p, ua):  # /ping (LOCK içinde) → STATE["extension"] çağrıdaki sekmeden türer; Teams ana sayfası Meet'i ezmez (2016-meet B1)
    simdi = time.time(); pl = p.get("platform") if p.get("platform") in PLATFORM_AD else None
    sk = str(p.get("sekme") or "")[:16] or f"eski-{pl or '?'}"
    x = EKLENTI.setdefault(sk, {"sekme": sk, "t_panel": 0.0, "t_captions": 0.0, "t_ust": 0.0, "t_call": 0.0, "rows": 0, "call": False, "platform": "bilinmeyen"})
    ust = not ("mic" in p and p["mic"] is None)  # iç çerçeve mic: null gönderir (content.js); alansız istemci (test, curl) üst sayılır
    for k in ("panel", "captions"):
        if p.get(k): x["t_" + k] = simdi
    if p.get("panel"): x["rows"] = p.get("rows", 0)
    cikti = False
    if ust:
        cikti = bool(x["call"]) and not p.get("call") and isinstance(p.get("mic"), dict)
        # toplantı sayfası mı (Meet kodu / toplantı yolu): eski eklenti göndermez — Meet nabzı yalnız toplantı sayfasından gelir
        x["sayfa"] = p["sayfa"] if isinstance(p.get("sayfa"), bool) else bool(pl == "meet" or p.get("call") or p.get("captions") or p.get("panel"))
        x.update(t_ust=simdi, call=bool(p.get("call")), meeting=(p.get("meeting") or {}).get("title"), lang=p.get("lang") or p.get("capLang"),
                 langSrc=p.get("langSrc") or ("captions" if p.get("capLang") else None))
        if x["call"]: x["t_call"] = simdi
        if cikti:  # açık çıkış: bu sekmenin eski panel/altyazı görüntüsü çağrıda sayılmasın (yoksa toplanti_cikis çıkışı kabul etmez)
            for k in ('panel', 'captions'):
                if not p.get(k): x['t_' + k] = 0.0
    x.update(seen=simdi, ver=p.get("ver") or x.get("ver"), platform=pl or x.get("platform") or "bilinmeyen", sent=p.get("sent", 0),
             capAuto=p.get("capAuto") or x.get("capAuto", ""), yonerge=p.get("yonerge") or x.get("yonerge"),
             tarayici="Edge" if "Edg/" in ua else "Safari" if ("Safari/" in ua and "Chrome/" not in ua) else "Chrome")
    for k in [k for k, v in EKLENTI.items() if simdi - v["seen"] > EKLENTI_DUS_SN]: EKLENTI.pop(k, None)
    STATE["extension"] = eklenti_ozet()
    return cikti  # çağrıdan çıkıldı (üst çerçeve call true → false)
def _eklenti_cagrida(x, simdi=None):  # çağrı düğmesi görüldü ya da döküm paneli/altyazı açık (eski toplanti_var kuralı: call | panel | captions; 28 Ekim mrt: call=false, altyazı açık)
    simdi = simdi or time.time()
    return simdi - x.get("seen", 0) < min(SINYAL_SN, 60) and (bool(x.get("call")) and simdi - x.get("t_ust", 0) < min(SINYAL_SN, 60)
                                                              or simdi - x.get("t_panel", 0) < EKLENTI_GOR_SN or simdi - x.get("t_captions", 0) < EKLENTI_GOR_SN)
def eklenti_cagri():  # çağrıdaki sekme (birden çoksa süren toplantının platformu önde, sonra en taze) ya da None
    simdi = time.time(); a = TOPLANTI.get("aktif") or {}
    ls = [x for x in EKLENTI.values() if _eklenti_cagrida(x, simdi)]
    return max(ls, key=lambda x: (x.get("platform") == a.get("platform"), x["t_ust"])) if ls else None
def eklenti_sayfa():  # toplantı sayfası açık sekme (çağrı görülmese de; 28 Ekim mrt: Türkçe Meet'te "Ayrıl" bulunamadı, call hep false)
    simdi = time.time(); ls = [x for x in EKLENTI.values() if x.get("sayfa") and simdi - x.get("t_ust", 0) < SINYAL_SN]
    return max(ls, key=lambda x: x["t_ust"]) if ls else None
def eklenti_ozet():  # geriye uyum: /status extension, izle DURUM satırı, beta, duman — çağrıdaki sekme, yoksa en taze
    if not EKLENTI: return None
    simdi = time.time(); x = eklenti_cagri() or max(EKLENTI.values(), key=lambda v: v["seen"])
    return {"ver": x.get("ver"), "seen": datetime.datetime.fromtimestamp(x["seen"]).isoformat(timespec="seconds"), "sekme": x["sekme"],
            "panel": simdi - x["t_panel"] < EKLENTI_GOR_SN, "rows": x["rows"] if simdi - x["t_panel"] < EKLENTI_GOR_SN else 0,
            "captions": simdi - x["t_captions"] < EKLENTI_GOR_SN, "call": bool(x.get("call")) and simdi - x.get("t_ust", 0) < 60,  # ham çağrı (toplantıya sesli söyle web yolu buna bakar) "lang": x.get("lang"), "langSrc": x.get("langSrc"),
            "meeting": x.get("meeting"), "sent": x.get("sent", 0), "capAuto": x.get("capAuto", ""), "platform": x.get("platform") or "bilinmeyen",
            "yonerge": x.get("yonerge"), "sekme_sayisi": len(EKLENTI)}

# --- sinyaller -----------------------------------------------------------------------------------------------------------------------------------------------
def masaustu_toplantida():  # menü uygulaması masaüstü Teams/Zoom'da toplantı görüyor (pencere başlığı okunmaz)
    m = STATE.get("masaustu") or {}
    return bool(m.get("toplantida")) and time.time() - m.get("t", 0) < SINYAL_SN
def toplanti_dis_sinyal():  # ses yardımcısının nabız yanıtı: yalnız sesten bağımsız sinyal (ses kendi sinyalini doğrulamasın — döngü)
    return bool(eklenti_cagri() or masaustu_toplantida())
def sinyaller():  # {kaynak: {"platform", "guvenli"}}
    s = {}; e = eklenti_cagri()
    if e: s["eklenti"] = {"platform": e.get("platform") or "bilinmeyen", "guvenli": True}
    if masaustu_toplantida(): s["masaustu"] = {"platform": MASAUSTU_PLATFORM.get((STATE.get("masaustu") or {}).get("uygulama") or "", "bilinmeyen"), "guvenli": True}
    a = TOPLANTI.get("aktif"); y = STATE["yerel_ses"]; now = time.time()
    # mikrofonu tutmak tek başına sürdürmez: toplantı uygulaması son SES_SESSIZ_SN'de ses çıkardı ya da son SATIRSIZ_SN'de satır geldi (eski bitiş kuralı;
    # 13 Ekim deneme 8: eklenti sustu, Chrome'daki toplantı sürüyordu)
    canli_ = not a or now - (y.get("sesli_t") or 0) < SES_SESSIZ_SN or now - a["t_satir"] < SATIRSIZ_SN
    if yerel_ses_durum() in ("dinliyor", "izin") and canli_ and not (globals().get("SOHBET") or {}).get("acik"):  # pano sohbeti de mikrofonu tutar
        s["ses"] = {"platform": MASAUSTU_PLATFORM.get(STATE["yerel_ses"].get("uygulama") or "", "bilinmeyen"), "guvenli": False}
        t = None if e else eklenti_sayfa()
        if t: s["eklenti"] = {"platform": t.get("platform") or "bilinmeyen", "guvenli": True, "sayfa": True}  # toplantı sekmesi + tarayıcı mikrofonu tutuyor
    if a and now - (a["kaynaklar"].get("altyazi") or 0) < SINYAL_SN and (a["kaynaklar"].get("altyazi") or 0) > (a.get("t_bitis") or 0) + 2: s["altyazi"] = {"platform": a["platform"], "guvenli": True}  # eklentinin altyazı/döküm satırı
    return s
def _elle_baslat(now):  # toplantı açılmadan önce elle basılmış, henüz bir kayda ad olmamış Başlat
    b = STATE.get("baslatma") or {}
    return b if b.get("konu") and not b.get("oto") and not b.get("kayit") and now - (b.get("at") or 0) < BASLAT_BEKLE_DK * 60 else None
def oto_takvim(platform, kesin=False):  # şu an süren ya da ±TAKVIM_PAY_DK içinde başlayan takvim toplantısı; aynı platform önde, sonra başlangıcı en yakın
    now = datetime.datetime.now().astimezone(); ad = []
    for e in (globals().get("TAKVIM_TAM") or {}).values():
        if e.get("tum_gun") or e.get("reddettin"): continue
        try: b, s = _zaman(e["baslangic"]), _zaman(e["bitis"])
        except (KeyError, TypeError, ValueError): continue
        pay = datetime.timedelta(minutes=0 if kesin else TAKVIM_PAY_DK)
        if not (b - pay <= now <= s + (datetime.timedelta(0) if kesin else datetime.timedelta(minutes=5))): continue
        if kesin and not e.get("baglanti"): continue
        ad.append((0 if platform and e.get("platform") == platform else 1, abs((now - b).total_seconds()), e))
    return min(ad, key=lambda t: t[:2])[2] if ad else None

# --- kayıt ---------------------------------------------------------------------------------------------------------------------------------------------------
def toplanti_durum(): return (TOPLANTI.get("aktif") or {}).get("durum") or "bos"
def toplanti_acik(): return toplanti_durum() in ("algilandi", "suruyor", "bitiyor")
def toplanti_var():  # 73 okuyucunun "toplantıdayız" anlamı (eskiden eklenti/masaüstü son 60 sn): kayıt sürüyor ve bir toplantı sinyali görüldü
    a = TOPLANTI.get("aktif") or {}  # yalnız satırla açılan kayıt (eski istemci, curl) dökümü tutar ama Konuş/ses kuralları için toplantı sayılmaz
    return a.get("durum") == "suruyor" and any(k in a["kaynaklar"] for k in ("eklenti", "masaustu", "ses", "altyazi"))
def aktif_dosya(): return (TOPLANTI["aktif"] or {}).get("dosya") if toplanti_acik() else None
GOSTER_SN = 1200  # biten toplantının kartları ve dökümü panoda özet gelene ya da bu süre dolana dek görünür (yalnız gösterim; dosyasına yazılmaz)
def gorunen_dosya():  # pano ve kartlar: süren toplantı, yoksa yeni biten (özeti henüz gelmemiş) toplantı
    f = aktif_dosya()
    if f: return f
    o = TOPLANTI.get("onceki")
    return o["dosya"] if o and not o.get("ozet") and time.time() - (o.get("t_kapanis") or 0) < GOSTER_SN else None
def toplanti_anahtar(): return (TOPLANTI.get("aktif") or {}).get("id") or "-"  # Whisper parçasının toplantısı (küme/ad sıfırlama)
def _ad_temiz(s): return " ".join(str(s or "").split())[:200]
def _kayit_ac(kaynak, platform, guvenli, olay=None, konu=None, platform_kaynak=None):  # LOCK içinde; dosya burada bir kez açılır
    now = time.time(); b = _elle_baslat(now) if konu is None else None
    if konu is None and b: konu = b["konu"]
    if b and not olay and b.get("olay"): olay = TAKVIM_TAM.get(str(b["olay"]))
    o = olay if olay is not None else oto_takvim(platform)
    if not olay and konu and o and _ad_temiz(o.get("baslik")) != _ad_temiz(konu) and not (b or {}).get("olay"): o_ad = None
    else: o_ad = (o or {}).get("baslik")
    if o and o.get("baglanti") and url_platform(o["baglanti"]): platform, platform_kaynak = url_platform(o["baglanti"]), "takvim"
    elif o and o.get("platform") in PLATFORM_AD and o["platform"] != "bilinmeyen" and platform == "bilinmeyen": platform, platform_kaynak = o["platform"], "takvim"
    if b and platform == "bilinmeyen":
        bp = b.get("platform") or url_platform(b.get("baglanti"))
        if bp: platform, platform_kaynak = bp, "başlat"
    saat = datetime.datetime.now().strftime("%H:%M")
    ad, ad_k = (_ad_temiz(konu), "başlat") if konu else (_ad_temiz(o_ad), "takvim") if o_ad else \
               ((f"{PLATFORM_AD[platform]} toplantısı {saat}" if platform in PLATFORM_AD and platform != "bilinmeyen" else f"Toplantı {saat}"), "nötr")
    d = datetime.date.today().strftime("%Y-%m-%d"); t = datetime.datetime.now().strftime("%H%M")
    base = os.path.join(BASE, f"{d}-{t}-{slug(ad)}")
    if os.path.exists(base + ".md") or os.path.exists(base + ".jsonl"):  # aynı dakikada aynı ad
        n = 2
        while os.path.exists(f"{base}-{n}.md"): n += 1
        base = f"{base}-{n}"
    dosya = os.path.basename(base) + ".md"
    haric = next((h for h in (AYAR.get("oto_haric") or []) if isinstance(h, str) and h.strip() and h.strip().lower() in ad.lower()), None)
    a = {"id": secrets.token_hex(4), "durum": "algilandi", "ad": ad, "ad_kaynak": ad_k, "dosya": dosya, "platform": platform or "bilinmeyen",
         "platform_kaynak": platform_kaynak or (kaynak if platform and platform != "bilinmeyen" else None), "kaynak": kaynak, "olay": (o or {}).get("id"),
         "t0": now, "t_sinyal": now, "t_satir": 0.0, "t_bitis": None, "t_kapanis": None, "satir": 0, "gec_atilan": 0, "kaynaklar": {kaynak: now},
         "guvenli": bool(guvenli), "oturum": False, "karar": False, "neden": None, "haric": haric, "oner": None, "bitis_neden": None, "elle": False, "cikis": False}
    if b: b["kayit"] = a["id"]
    TOPLANTI["aktif"] = a
    x = STATE.get("extension") or {}
    src = (None if x.get("panel") else "captions" if x.get("captions") else "oto") if kaynak == "eklenti" else "oto"
    md = os.path.join(BASE, dosya); hdr = ensure_header(md, ad, {"platform": a["platform"]}, src)
    STATE["file_start"][dosya] = datetime.datetime.now().isoformat(timespec="seconds"); STATE["file_last"][dosya] = now; STATE["file_lines"].setdefault(dosya, 0)
    STATE["file"] = dosya; STATE["meeting"] = ad; STATE["notes"] = 0; STATE["flags"] = []; STATE["lines"] = 0; STATE["toplanti_bitti"] = None
    notlar_ = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in globals().get("PRE_NOT") or []); (globals().get("PRE_NOT") or []).clear()
    write([(md, hdr), (md, pre_al(md)), (md[:-3] + ".jsonl", notlar_)])
    print(f"TOPLANTI: algılandı — {dosya} · {PLATFORM_AD.get(a['platform'], a['platform'])} · {kaynak} · ad {ad_k}")
    _durum_yaz(); return a
def _gecis(a, d, neden=None):
    eski = a["durum"]; a["durum"] = d
    if d == "bitiyor": a["t_bitis"] = time.time(); a["bitis_neden"] = neden
    print(f"TOPLANTI: {eski} → {d}" + (f" ({neden})" if neden else "") + f" · {a['dosya']}"); _durum_yaz()
def _kapat(a, neden):  # LOCK içinde: bitti → boş
    a["durum"] = "bitti"; a["t_kapanis"] = time.time(); a["bitis_neden"] = a.get("bitis_neden") or neden
    TOPLANTI["onceki"] = a; TOPLANTI["aktif"] = None
    STATE["toplanti_bitti"] = {"file": a["dosya"], "t": datetime.datetime.now().isoformat(timespec="seconds"), "neden": a["bitis_neden"]}
    print(f"TOPLANTI: bitti ({a['bitis_neden']}) · {a['dosya']} · {a['satir']} satır" + (f" · {a['gec_atilan']} geç satır yazılmadı" if a["gec_atilan"] else ""))
    if globals().get("SESLI", {}).get("acik"):  # sesli çeviri toplantıyla kapanır
        print(f"SESLİ ÇEVİRİ: toplantı bitti — kapandı · okunan {SESLI['okunan']}, atlanan {SESLI['atlanan']}"); SESLI.update(acik=False, q=[])
    _durum_yaz()
def _iptal(a):  # algılandı ama hiç satır gelmedi: yalnız başlıklı dosya silinir
    TOPLANTI["aktif"] = None
    if not a["satir"] and not STATE["file_lines"].get(a["dosya"], 0):
        for u in (".md", ".jsonl"):
            try: os.remove(os.path.join(BASE, a["dosya"][:-3] + u))
            except OSError: pass
        HEADERED.discard(os.path.join(BASE, a["dosya"]))
        for k in ("file_last", "file_start", "file_lines"): STATE[k].pop(a["dosya"], None)
        if STATE.get("file") == a["dosya"]: STATE["file"] = (TOPLANTI.get("onceki") or {}).get("dosya"); STATE["meeting"] = (TOPLANTI.get("onceki") or {}).get("ad")
    print(f"TOPLANTI: algılanan toplantı başlamadı — kayıt kaldırıldı ({a['dosya']})"); _durum_yaz()
def _kuyruk_bos(t):  # Whisper kuyruğunda t'den önce başlamış (bas-konuş dışı) parça yok
    try: return not any(not x.get("bas") and not x.get("isinma") and x.get("t0", 0) <= t for x in list(WH_Q.queue))
    except Exception: return True

def toplanti_bak():  # LOCK içinde; geçişleri yapar, LOCK dışında koşacak işleri (oturum, öneri, hızlı özet) döndürür
    now = time.time(); s = sinyaller(); a = TOPLANTI["aktif"]; sonra = []
    STATE["extension"] = eklenti_ozet()
    if a:
        guvenli = any(v["guvenli"] for v in s.values())
        for k in s:
            if k != "altyazi": a["kaynaklar"][k] = now  # altyazı kaynağının zamanını yalnız satır tazeler (yoksa sinyal kendini besler)
        if s: a["t_sinyal"] = now
        if a["platform"] == "bilinmeyen":  # açılışta bilinmeyen platform sonradan bir kez dolar (ad ve başlık değişmez)
            p = next((v["platform"] for v in s.values() if v["platform"] != "bilinmeyen"), None)
            if p: a["platform"], a["platform_kaynak"] = p, next(k for k, v in s.items() if v["platform"] == p); print(f"TOPLANTI: platform {PLATFORM_AD.get(p, p)} ({a['platform_kaynak']})")
        d = a["durum"]
        if d == "algilandi":
            if guvenli or a["satir"]: _gecis(a, "suruyor", "güvenli sinyal" if guvenli else "ilk satır")
            elif not s and now - a["t_sinyal"] > (BASLAT_BEKLE_DK * 60 if a["kaynak"] == "başlat" else ALGILANDI_BEKLE_SN): _iptal(a); a = None
        elif d == "suruyor":
            esik = SINYAL_SN if any(k in a["kaynaklar"] for k in ("eklenti", "masaustu", "ses", "altyazi")) else SINYALSIZ_SN  # hiç sinyal görmemiş kayıt (yalnız satır: eski istemci, curl)
            if not s and now - max(a["t_sinyal"], a["t_satir"]) > esik:
                _gecis(a, "bitiyor", f"{round(esik)} sn sinyal ve satır yok"); sonra.append(lambda: hizli_ozet_tetik("sinyal"))
        elif d == "bitiyor":
            if not a["elle"] and (guvenli or (s and not a["cikis"])): _gecis(a, "suruyor", "sinyal geri geldi"); a["cikis"] = False
            elif now - a["t_bitis"] >= (0 if a["elle"] else BITIYOR_SN) and (_kuyruk_bos(a["t_bitis"]) or now - a["t_bitis"] > (30 if a["elle"] else KUYRUK_BEKLE_SN)):
                _kapat(a, a.get("bitis_neden")); a = None
        if a and a["durum"] in ("algilandi", "suruyor") and guvenli and not a["karar"] and not a.get("_bak"):  # sonradan güvenilir sinyal geldi
            a["_bak"] = True; sonra.append(lambda a=a: _oto_oturum(a, {"guvenli": True}, _baslatla(a)))
        return sonra
    k = TOPLANTI.get("kilit")
    if k:  # elle bitirildi: aynı sinyal kesilene (10 sn) ya da BITIR_KILIT_SN dolana dek yeniden açılmaz
        if s: k["t_sinyal"] = now
        if now - k["t_sinyal"] < 10 and now - k["t"] < BITIR_KILIT_SN: return sonra
        TOPLANTI["kilit"] = None
    if not s or gizli_acik():
        _teshis(None); return sonra
    guv = next((k_ for k_ in ("eklenti", "masaustu") if k_ in s), None)
    if guv: kaynak, platform, guvenli = guv, s[guv]["platform"], True
    else:
        # yalnız mikrofon (eklenti çağrı/toplantı sekmesi yok): 28 Ekim — takvim/Başlat yoksa da dosya ve döküm açılır (S162: sormadan), Claude oturumu
        # yerine öneri kartı; takvim de yoksa öneri ilk satırla (Konuş/Safari mikrofonu boşuna kart çıkarmasın; satırsız kayıt 120 sn'de silinir)
        if (globals().get("KONUS") or {}).get("durum") in ("dinliyor", "yaziya"): return sonra  # panodaki Konuş mikrofonu toplantı değil
        b = _elle_baslat(now); o = oto_takvim(None)
        kaynak, platform, guvenli = "ses", s["ses"]["platform"], bool(b)
    a = _kayit_ac(kaynak, platform, guvenli); sonra.append(modelleri_isit)  # mrt 28 Ekim B1: Whisper toplantı başında açılsın (bitince açılıyordu)
    _teshis(a, s)
    if guvenli: _gecis(a, "suruyor", "güvenli sinyal")
    if guvenli or b or o: a["_bak"] = True; sonra.append(lambda a=a: _oto_oturum(a, {"guvenli": a["guvenli"]}, _baslatla(a)))
    else: a["oner_satirla"] = True
    return sonra
_TESHIS = {"son": None}
def _teshis(a, s=None):  # toplantı sayfası/altyazı var ama güvenli sinyal yok → gerekçe günlüğe bir kez (28 Ekim mrt: hiç iz yoktu)
    x = eklenti_sayfa() or next((v for v in EKLENTI.values() if time.time() - v["t_captions"] < EKLENTI_GOR_SN), None)
    if a and a["guvenli"] or (not a and not x): return
    k = (a or {}).get("id") or (x or {}).get("sekme")
    if _TESHIS["son"] == k: return
    _TESHIS["son"] = k; ys = yerel_ses_durum(); ya = STATE["yerel_ses"].get("uygulama") or "-"
    print(f"TOPLANTI: sinyal zayıf (eklenti {'call=' + str(bool((x or {}).get('call'))).lower() if x else 'yok'}, altyazı {'var' if x and time.time() - x['t_captions'] < EKLENTI_GOR_SN else 'yok'}, "
          f"ses {ys}{' ' + ya if ys in ('dinliyor', 'izin') else ''}, takvim {'var' if oto_takvim(None) else 'yok'}) → " + ("kayıt açıldı, Claude oturumu öneriyle" if a else "kayıt açılmadı (ses yok)"))
def _baslatla(a): return (STATE.get("baslatma") or {}).get("kayit") == a["id"]  # kayıt elle Başlat'la açıldı: oturumu Başlat açtı
def _alt_satir(kaynak):  # altyazı/döküm satırı ve eklentinin bir sekmesi son SINYAL_SN'de nabız attı (nabızsız istemci — curl, test — sinyal değil)
    return kaynak in ("captions", "transcript") and any(time.time() - x["seen"] < SINYAL_SN for x in EKLENTI.values())
def toplanti_satir(t, icerik=True, kaynak=None):  # LOCK içinde; satırın yakalandığı ana göre hedef kayıt → (dosya, kayit) ya da (None, None) (yazılmaz)
    now = time.time(); t = t or now; a = TOPLANTI["aktif"]; o = TOPLANTI.get("onceki")
    if not a and icerik and not gizli_acik():  # satırın kendisi sinyaldir (eklenti satırı, sesten satır)
        for f in toplanti_bak(): threading.Thread(target=f, daemon=True).start()
        a = TOPLANTI["aktif"]
        if not a and not TOPLANTI.get("kilit"):
            alt = _alt_satir(kaynak)  # eklentinin altyazı/döküm satırı: toplantı kesin (28 Ekim: call=false iken de)
            a = _kayit_ac("altyazı" if alt else "satır", (eklenti_cagri() or eklenti_ozet() or {}).get("platform") or "bilinmeyen", alt)
            threading.Thread(target=modelleri_isit, daemon=True).start()
    if a and t >= a["t0"] - ON_PAY_SN:
        if icerik:
            a["t_satir"] = now; a["satir"] += 1
            if _alt_satir(kaynak): a["kaynaklar"]["altyazi"] = now; a["guvenli"] = True
            ilk = a["durum"] == "algilandi"
            if not a["karar"] and not a.get("_bak") and (a["guvenli"] or (ilk and a.get("oner_satirla"))):  # altyazı geldi → oturum; yalnız ses → ilk satırda öneri
                a["_bak"] = True; g = a["guvenli"]; threading.Thread(target=lambda: _oto_oturum(a, {"guvenli": g}, _baslatla(a)), daemon=True).start()
            if a["durum"] == "algilandi": _gecis(a, "suruyor", "ilk satır")
            elif a["durum"] == "bitiyor" and not a["elle"] and t > a["t_bitis"] + 2: _gecis(a, "suruyor", "yeni satır"); a["cikis"] = False
        return a["dosya"], a
    if a and a["durum"] == "bitiyor" and t >= a["t0"] - ON_PAY_SN: return a["dosya"], a
    if o and o["t0"] - ON_PAY_SN <= t <= (o.get("t_bitis") or o["t_kapanis"] or now):  # bitmiş toplantının satırı: yazılmaz (S163)
        o["gec_atilan"] += 1
        print(f"GEÇ SATIR: bitmiş toplantının ({o['dosya']}) satırı {round(now - t)} sn gecikmeli geldi — yazılmadı (toplam {o['gec_atilan']})"); return None, None
    if a: return a["dosya"], a  # zamanı aralık dışında (saat kayması): süren toplantıya
    return None, None
def toplanti_cikis(neden):  # açık çıkış (eklenti çağrı → yok, masaüstü toplantıda → yok): LOCK içinde
    a = TOPLANTI["aktif"]
    if not a or a["durum"] != "suruyor" or eklenti_cagri() or ("masaüstü" not in neden and masaustu_toplantida()): return False
    a["cikis"] = True; _gecis(a, "bitiyor", neden); return True
def toplanti_bitir(neden, dosya=None):  # elle: özet hazır, toplantı oturumu kapat, duman, POST /toplanti — kuyruk boşalınca (≤ 30 sn) bitti
    with LOCK:
        a = TOPLANTI["aktif"]; o = TOPLANTI.get("onceki")
        if neden == "özet hazır" and o and (not dosya or o["dosya"] == dosya) and not (a and a["dosya"] == dosya): o["ozet"] = True; _durum_yaz()
        if not a or (dosya and a["dosya"] != dosya): return False
        a["elle"] = True; a["ozet"] = neden == "özet hazır"
        if a["durum"] != "bitiyor": _gecis(a, "bitiyor", neden)
        else: a["bitis_neden"] = neden
        TOPLANTI["kilit"] = {"t": time.time(), "t_sinyal": time.time()}
        for f in toplanti_bak(): threading.Thread(target=f, daemon=True).start()
    return True
def toplanti_baslatta(konu, olay, platform, baglanti):  # baslat()'tan (LOCK dışında): kayıt yoksa açar, sürüyorsa katılır, bitiyorsa konuya göre
    with LOCK:
        a = TOPLANTI["aktif"]
        if a and a["durum"] == "bitiyor":
            if not konu or _ad_temiz(konu) == a["ad"]: _gecis(a, "suruyor", "Başlat"); a["elle"] = a["cikis"] = False; return a
            _kapat(a, "yeni Başlat"); a = None
        if a: return a
        TOPLANTI["kilit"] = None
        p = platform or url_platform(baglanti) or "bilinmeyen"
        a = _kayit_ac("başlat", p, True, olay=olay, konu=None if olay and _ad_temiz(olay.get("baslik")) == _ad_temiz(konu) else konu,
                         platform_kaynak="başlat" if p != "bilinmeyen" else None)
        a["karar"] = True; a["neden"] = "oturum zaten var (Başlat)"; a["oturum"] = True
        b = STATE.get("baslatma") or {}
        if b.get("konu"): b["kayit"] = a["id"]
        return a

# --- Claude toplantı oturumu (S161–S162 kuralı aynen) -------------------------------------------------------------------------------------------------------
def _oto_oturum(a, s, elle):  # a["karar"]: oturum kararı verildi; güvenilmeyen sinyalde (öneri) yanlış kalır, güvenilir sinyal gelince yeniden denenir
    try: _oto_oturum_(a, s, elle)
    finally: a["_bak"] = False
def _oto_oturum_(a, s, elle):
    if a["karar"]: return
    now = time.time()
    if AYAR.get("oto_toplanti") is False: a["neden"] = "ayar kapalı (oto_toplanti)"; a["karar"] = True
    elif a["haric"]: a["neden"] = f"hariç ({a['haric']})"; a["karar"] = True
    elif elle or topo_canli() or (STATE.get("izle_seen") and now - STATE["izle_seen"] < 60) or (TOPO.get("durum") == "aciliyor"):
        a["neden"] = "oturum zaten var (Başlat)"; a["oturum"] = True; a["karar"] = True
    elif deneme_aktarici() and os.environ.get("SUFLOR_TEST_OTO") != "1": a["neden"] = "deneme aktarıcısı"; a["karar"] = True
    elif not s.get("guvenli"):
        a["neden"] = "güvenilir sinyal yok (yalnız mikrofon + takvim) — öneri kartı"; oto_oner(a)
        print("OTO: toplantı oturumu açılmadı (" + a["neden"] + ")"); return
    else:
        a["karar"] = True; r = baslat({"olay": a["olay"], "konu": a["ad"], "platform": a["platform"], "oto": True})
        a["oturum"] = bool(r.get("ok")); a["neden"] = None if r.get("ok") else str(r.get("err") or "?")[:160]
        if r.get("ok") and a.get("oner"):  # önce öneri kartı çıkmıştı (yalnız ses), sonra güvenli sinyal geldi: kart kendiliğinden kapanır
            with LOCK:
                for x in eylem_gorunen():
                    if x["id"] == a["oner"] and x["durum"] == "bekliyor": _eylem_yama(x, durum="onaylandi", kaynak="oto")
                for c in CARDS:
                    if c.get("eylem") == a["oner"] and c.get("status") == "acik": c["status"] = "onaylandi"
    print("OTO: toplantı oturumu " + (f"açılmadı ({a['neden']})" if a["neden"] else "açıldı"))
def oto_oner(a):  # panoda onay kartı (yerel eylem + onay kartı); tıklayınca baslat — toplantı başına bir kez
    if a.get("oner"): return
    ne = _t("Toplantı algılandı — Claude'u başlat", "Meeting detected — start Claude")
    x = eylem_ekle({"tur": "baslat", "baslik": f"{ne}: {a['ad']}"[:160], "ayrinti": json.dumps({"olay": a["olay"], "konu": a["ad"], "platform": a["platform"]}, ensure_ascii=False)})
    if not x: return
    with LOCK: x["yerel"] = True; _eylem_yama(x, yerel=True)
    c = add_card({"kind": "not", "text": ne, "why": a["ad"][:120], "onay": True})
    if c:
        with LOCK: c["eylem"] = x["id"]
    a["oner"] = x["id"]; print(f"OTO: öneri kartı — {a['ad']}")
def oto_karar(x, durum):  # eylem_karar'dan: Onayla → baslat; Reddet → bu toplantıda yeniden sorma
    with LOCK:
        for c in CARDS:
            if c.get("eylem") == x["id"] and c.get("status") == "acik": c["status"] = durum; c["acted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    a = TOPLANTI.get("aktif") or {}
    if durum != "onaylandi":
        if a.get("oner") == x["id"]: a["karar"] = True; a["neden"] = "öneri reddedildi"
        return
    try: ay = json.loads(x.get("ayrinti") or "{}")
    except ValueError: ay = {}
    def is_():
        r = baslat({"olay": ay.get("olay"), "konu": ay.get("konu"), "platform": ay.get("platform"), "oto": True})
        if a.get("oner") == x["id"]: a["karar"] = True; a["oturum"] = bool(r.get("ok")); a["neden"] = None if r.get("ok") else str(r.get("err") or "?")[:160]
        print("OTO: öneri onaylandı — toplantı oturumu " + ("açıldı" if r.get("ok") else f"açılmadı ({str(r.get('err'))[:80]})"))
    threading.Thread(target=is_, daemon=True).start()

# --- görünüm ve kalıcılık ------------------------------------------------------------------------------------------------------------------------------------
_KAYIT_ALAN = ("id", "durum", "ad", "ad_kaynak", "dosya", "platform", "platform_kaynak", "kaynak", "olay", "t0", "t_sinyal", "t_satir", "t_bitis", "t_kapanis",
               "satir", "gec_atilan", "guvenli", "oturum", "karar", "neden", "bitis_neden", "elle", "cikis", "ozet")
def _kayit_dis(a): return {k: a.get(k) for k in _KAYIT_ALAN} if a else None
def toplanti_view():  # /status toplanti — pano yalnız buna bakar
    a = TOPLANTI.get("aktif"); o = TOPLANTI.get("onceki"); now = time.time()
    v = {"durum": toplanti_durum(), "eklenti_yok": not eklenti_cagri()}
    if a:
        v.update(ad=a["ad"], dosya=a["dosya"], platform=a["platform"], bas=datetime.datetime.fromtimestamp(a["t0"]).strftime("%H:%M"),
                 son_satir_sn=round(now - a["t_satir"]) if a["t_satir"] else None, kaynaklar={k: round(now - t) for k, t in a["kaynaklar"].items()},
                 oturum=a["oturum"], neden=a["neden"], gec_atilan=a["gec_atilan"], bitis_neden=a.get("bitis_neden"))
        v["mic_bilinmiyor"] = a["durum"] == "suruyor" and not eklenti_cagri() and not masaustu_toplantida() and (STATE.get("masaustu_mic") or {}).get("acik", False)
    if o: v["onceki"] = {"dosya": o["dosya"], "ad": o["ad"], "bitti": datetime.datetime.fromtimestamp(o["t_kapanis"] or now).strftime("%H:%M"), "neden": o.get("bitis_neden"), "gec_atilan": o["gec_atilan"]}
    return v
def oto_view():  # eski /status oto_toplanti (pano: oturum açık mı)
    a = TOPLANTI.get("aktif")
    return {k: a[k] for k in ("ad", "platform", "kaynak", "olay", "oturum", "neden")} if a else None
def _durum_yaz():  # canli/toplanti.json (geçici dosya + os.replace)
    try:
        with open(TOPLANTI_FP + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"t": time.time(), "aktif": _kayit_dis(TOPLANTI.get("aktif")), "onceki": _kayit_dis(TOPLANTI.get("onceki"))}, f, ensure_ascii=False, indent=1)
        os.replace(TOPLANTI_FP + ".tmp", TOPLANTI_FP)
    except OSError: pass
def toplanti_kur():  # aktarıcı açılırken: süren kayıt ≤ 5 dk önce yazıldıysa bitiyor olarak sürer (sinyal gelirse aynı dosya), değilse önceki
    try: d = json.load(open(TOPLANTI_FP, encoding="utf-8"))
    except (OSError, ValueError): return None
    def kayit(r):
        if not r or not r.get("dosya"): return None
        a = {k: r.get(k) for k in _KAYIT_ALAN}; a.update(kaynaklar={}, oner=None, haric=None)
        for k in ("satir", "gec_atilan"): a[k] = a.get(k) or 0
        for k in ("t0", "t_sinyal", "t_satir"): a[k] = a.get(k) or 0.0
        return a
    TOPLANTI["onceki"] = kayit(d.get("onceki")); a = kayit(d.get("aktif")); now = time.time()
    if a and a["durum"] in ("algilandi", "suruyor", "bitiyor") and now - float(d.get("t") or 0) < 300 and os.path.exists(os.path.join(BASE, a["dosya"])):
        a.update(durum="bitiyor", t_bitis=now, t_sinyal=now, bitis_neden="aktarıcı yeniden başladı", elle=False, cikis=False, karar=True)
        TOPLANTI["aktif"] = a; HEADERED.add(os.path.join(BASE, a["dosya"])); print(f"TOPLANTI: yeniden başlangıçta süren kayıt kuruldu — {a['dosya']} (sinyal bekleniyor)")
        threading.Thread(target=lambda: (time.sleep(2), modelleri_isit()), daemon=True).start()  # mrt 28 Ekim: yeniden başlamadan sonra Whisper kapalı kalıyordu
        return a["dosya"]
    if a and a["durum"] != "bitti": a["durum"] = "bitti"; a["t_kapanis"] = a.get("t_kapanis") or float(d.get("t") or now); TOPLANTI["onceki"] = a
    return None
def _toplanti_dongu():
    son_yaz = 0.0
    while True:
        time.sleep(1 if _TH else 3)
        try:
            with LOCK: isler = toplanti_bak()
            for f in isler: threading.Thread(target=f, daemon=True).start()
            if time.time() - son_yaz >= 5: son_yaz = time.time(); _durum_yaz()
        except Exception as e: print(f"TOPLANTI: denetim hatası ({e.__class__.__name__}: {str(e)[:120]})")
