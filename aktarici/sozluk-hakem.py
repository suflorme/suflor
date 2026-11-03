# Suflor.me aktarıcı bölümü: Gemini hakemi (öğrenen sözlük 3. aşama, 3 Kasım; plan ../planlar/sozluk-ogrenme-20261103.md). Ayrı modül değildir — relay.py bunu kendi ad
# alanında sozluk-ogren.py'den sonra çalıştırır (bolum("sozluk-hakem")); toplanti-claude.py (sozluk --ogren) da aynı ad alanına yükler (orada yalnız kanıt okuma; ağ yok). import etme. Python 3.9.
# Gizlilik (S186): YALNIZ geliştiricinin kurulumunda (gelistirici_mi) ve toplantı BİTTİKTEN sonra ses arşivinin parçaları (canli/ses-arsivi/<toplantı>/*.wav) Gemini API'ye (ücretli katman)
# gider. Beta kurulumunda iş parçacığı hiç başlamaz, hakem_toplanti ağa çıkmadan döner. Gizli kipi açıkken ve dökümünde **GİZLİ** satırı olan toplantıda ses gitmez. Canlı hat ve ses izi
# gitmez; Konuş parçaları (bas) gitmez. İsteğe yalnız ses + sabit yönerge girer: döküm, kişi adı, proje bilgisi yok. Ayar hakem_terim_istemi (varsayılan kapalı) açılırsa yalnız
# sözlüğün sistem/ürün biçimli terimleri (kişi adı değil) eklenir. Hakem dökümü doğru sayılmaz, kanıttır: aday kabul kapısının bütün şartlarından geçer (tek başına tek toplantıda kabul yok).
# Çıktı: <ses-arsivi>/<toplantı>/hakem.jsonl (0600; ses arşiviyle birlikte döner/silinir/eğitim havuzuna taşınır), ölçüm canli/hakem-olcum.jsonl (yalnız sayı), kullanım gemini-ses.jsonl (is: hakem).
import base64, collections, difflib, http.client, threading
HAKEM_MODEL = "gemini-3.5-flash"  # 4 Kasım: 3.8-flash 503 "yoğun talep" verdi (3.5-flash tek parça 7 sn, 36 parça 283 sn); 3 Kasım'daki varsayılan 3.8-flash'tı: ses girişi 0,75 $/M (32 belirteç/sn), çıkış 3,75 $/M (düşünme dahil) — 1 Ocak 2027'den iki katı
HAKEM_FIYAT = {"gemini-3.8-flash": (0.75, 3.75, "2027-01-01"), "gemini-3.6-flash": (0.75, 3.75, "2027-01-01"), "gemini-4-argon": (2.0, 10.0, "2026-12-01"),
               "gemini-3.5-flash-lite": (0.30, 2.50, None), "gemini-3.1-flash-lite": (0.50, 1.50, None), "gemini-3-flash-preview": (1.0, 3.0, None)}  # $/M belirteç: (giriş, çıkış, iki katına çıktığı gün)
HAKEM_YEDEK = ("gemini-3.8-flash", "gemini-3.6-flash")  # 4 Kasım: 3.8-flash "yoğun talep" 503 veriyordu (küçük yazı isteği de); 503/5xx/429 (günlük değil) gelince sıradaki model
HAKEM_FIYAT_BILINMEYEN = (2.0, 12.0, None)  # fiyatı bilinmeyen model: pahalı say (sınır erken dolsun)
HK_TOKEN_SN = 32; HK_CIKIS_SN = 8  # ses 32 belirteç/sn (belge); çıkış tahmini ~8 belirteç/sn konuşma (metin + JSON + düşük düşünme) — yalnız ön sınır denetimi için
HK_OBEK_SN = 300; HK_OBEK_PARCA = 60; HK_EN_KISA_SN = 0.5  # öbek ≤ 5 dk ses (WAV base64 ≈ 12,8 MB < 20 MB satır içi sınırı), ≤ 60 parça
HK_ZAMAN_ASIMI = 240; HK_DENEME = 3; HK_YENIDEN_DK = 30; HK_VAZGEC = 3; HK_BITIS_DK = 10; HK_ARALIK_SN = 600
HK_DURUM = "sozluk-hakem.json"; HK_OLCUM = "hakem-olcum.jsonl"
HK_YONERGE = ("Aşağıda bir toplantıdan kesilmiş ses parçaları var; her parçadan hemen önce köşeli parantez içinde kimliği yazılı. Her parçayı kelimesi kelimesine yazıya dök. "
              "Konuşma Türkçe, İngilizce ya da ikisi karışık olabilir: her sözcüğü söylendiği dilde yaz, çevirme. Düzeltme, özetleme, yorum yapma; tekrarları ve dolgu sözcüklerini de yaz. "
              "Duyulmayan ya da anlaşılmayan yeri uydurma, atla; parçada konuşma yoksa metni boş bırak. Özel adları duyduğun gibi, olağan yazımlarıyla yaz. "
              "Her parça için bir kayıt döndür: id = köşeli parantezdeki kimlik, metin = döküm.")
HK_SEMA = {"type": "OBJECT", "properties": {"parcalar": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "STRING"}, "metin": {"type": "STRING"}},
                                                                                       "required": ["id", "metin"]}}}, "required": ["parcalar"]}
def hakem_model(): return str(AYAR.get("hakem_model") or HAKEM_MODEL)
def hakem_gunluk_usd():
    try: return float(AYAR.get("hakem_gunluk_usd") if AYAR.get("hakem_gunluk_usd") is not None else 1.0)
    except (TypeError, ValueError): return 1.0
def hakem_en_cok_sn():
    try: return float(AYAR.get("hakem_en_cok_dk") or 120) * 60
    except (TypeError, ValueError): return 7200.0
def _hk_anahtar(): return gemini_anahtar() if "gemini_anahtar" in globals() else ""  # gemini-ses.py: Anahtar Zinciri (ayar gemini_anahtar), dosyaya/günlüğe yazılmaz
def hakem_acik():  # → (açık mı, neden); beta (geliştirici değil) her zaman kapalı
    if AYAR.get("hakem") is False: return False, "kapali"
    if not ("gelistirici_mi" in globals() and gelistirici_mi()): return False, "beta"
    if "gizli_acik" in globals() and gizli_acik(): return False, "gizli"
    if not _hk_anahtar(): return False, "anahtar_yok"
    return True, None
def _hk_gizli_mi(md):  # dökümünde gizli kip satırı olan toplantı (relay.py gizli_degistir: "| saat | **GİZLİ** | açıldı …")
    try: return "| **GİZLİ** |" in open(_so_yol(md), encoding="utf-8", errors="replace").read()
    except OSError: return False
def hakem_usd(model, giris, cikis, gun=None):
    f = HAKEM_FIYAT.get(model, HAKEM_FIYAT_BILINMEYEN); kat = 2 if f[2] and (gun or datetime.date.today().isoformat()) >= f[2] else 1
    return (giris * f[0] + cikis * f[1]) / 1e6 * kat
def hakem_tahmin_usd(sn, model=None): return hakem_usd(model or hakem_model(), sn * HK_TOKEN_SN + 400, sn * HK_CIKIS_SN)
def _hk_kayit_yol(kok=None): return os.path.join(kok or BASE, "gemini-ses.jsonl")
def hakem_bugun_usd(kok=None):  # bugün (yerel gün) hakeme harcanan
    bugun = datetime.date.today().isoformat(); t = 0.0
    try:
        for l in open(_hk_kayit_yol(kok), encoding="utf-8"):
            if '"hakem"' not in l: continue
            try: r = json.loads(l)
            except ValueError: continue
            if r.get("is") == "hakem" and str(r.get("t", ""))[:10] == bugun: t += float(r.get("usd") or 0)
    except OSError: pass
    return t
# --- parçalar ve hakem dökümü ---------------------------------------------------------------------------------------------------------------------------------------------------------
def _hk_kl(md): return _so_yol("ses-arsivi", md[:-3])
def _hk_parcalar_oku(kl):  # parcalar.jsonl → gönderilebilir parçalar (Konuş parçası yok, wav var), saate göre
    rs, gor = [], set()
    try:
        for l in open(os.path.join(kl, "parcalar.jsonl"), encoding="utf-8", errors="replace"):
            try: r = json.loads(l)
            except ValueError: continue
            if not isinstance(r, dict) or r.get("bas") or r.get("kanal") not in ("ben", "karsi"): continue
            d = os.path.basename(str(r.get("dosya") or ""))
            try: sn = float(r.get("sn") or 0)
            except (TypeError, ValueError): continue
            if not d.endswith(".wav") or d in gor or sn < HK_EN_KISA_SN or not os.path.isfile(os.path.join(kl, d)): continue
            gor.add(d); rs.append(dict(r, dosya=d, sn=sn))
    except OSError: pass
    return sorted(rs, key=lambda r: (float(r.get("t0") or 0), r["dosya"]))
def _hk_oku(yol):  # hakem.jsonl → ({dosya: kayıt}, son işareti)
    H, son = {}, None
    try:
        for l in open(yol, encoding="utf-8", errors="replace"):
            try: r = json.loads(l)
            except ValueError: continue
            if not isinstance(r, dict): continue
            if r.get("son"): son = r
            elif isinstance(r.get("dosya"), str): H[r["dosya"]] = r
    except OSError: pass
    return H, son
def _so_hakem_hazir(md):  # sozluk-ogren.py so_bekleyen: hakem bitti mi (bitince toplantı bir kez daha işlenir)
    return _hk_oku(os.path.join(_hk_kl(md), "hakem.jsonl"))[1] is not None
def _hk_sec(rs, en_cok_sn):  # → (seçilen, kırpıldı mı); sınırı aşan parçalar gönderilmez
    out, top = [], 0.0
    for r in rs:
        if top + r["sn"] > en_cok_sn: return out, True
        out.append(r); top += r["sn"]
    return out, False
def _hk_obekler(rs):
    ob, sn = [], 0.0
    for r in rs:
        if ob and (sn + r["sn"] > HK_OBEK_SN or len(ob) >= HK_OBEK_PARCA): yield ob; ob, sn = [], 0.0
        ob.append(r); sn += r["sn"]
    if ob: yield ob
def _hk_terimler():  # yalnız ayar hakem_terim_istemi: true — sözlüğün sistem/ürün biçimli terimleri (iç büyük harf ya da kısaltma; kişi adı biçimi değil), en çok 40
    out = []
    for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []):
        d = " ".join(str(t.get("dogru") or "").split())
        if d and len(d) <= 40 and (t.get("tur") in ("sistem", "urun", "marka") or (_so_tur_tahmini(d) == "sistem" and t.get("tur") not in ("kisi", "kurum"))) and d not in out: out.append(d)
    return out[:40]
def hakem_govde(obek, kl, dusunme="low"):  # istek gövdesi: sabit yönerge + [pN] + ses; döküm metni, ad, dosya adı girmez
    yon = HK_YONERGE
    if AYAR.get("hakem_terim_istemi") is True:
        tr = _hk_terimler()
        if tr: yon += " Toplantıda geçebilecek ürün ve sistem adları: " + ", ".join(tr) + "."
    parts = [{"text": yon}]
    for i, r in enumerate(obek):
        b = open(os.path.join(kl, r["dosya"]), "rb").read()
        parts += [{"text": f"[p{i + 1}]"}, {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(b).decode()}}]
    gc = {"temperature": 0, "responseMimeType": "application/json", "responseSchema": HK_SEMA}
    if dusunme: gc["thinkingConfig"] = {"thinkingLevel": dusunme}
    return {"contents": [{"role": "user", "parts": parts}], "generationConfig": gc}
def hakem_coz(govde, n):  # → ({"p1": metin, …} ya da None: bozuk, kullanım {giris, ses, cikis, dusunce})
    try: o = json.loads(govde)
    except ValueError: return None, {}
    u = o.get("usageMetadata") or {} if isinstance(o, dict) else {}
    kul = {"giris": int(u.get("promptTokenCount") or 0), "cikis": int(u.get("candidatesTokenCount") or 0), "dusunce": int(u.get("thoughtsTokenCount") or 0),
           "ses": sum(int(x.get("tokenCount") or 0) for x in u.get("promptTokensDetails") or [] if isinstance(x, dict) and x.get("modality") == "AUDIO")}
    try:
        t = "".join(p.get("text", "") for p in o["candidates"][0]["content"]["parts"] if isinstance(p, dict) and not p.get("thought"))
        t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", t); j = json.loads(t)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError): return None, kul
    if not isinstance(j, dict) or not isinstance(j.get("parcalar"), list): return None, kul
    idler = {f"p{i + 1}" for i in range(n)}; out = {}
    for x in j["parcalar"]:
        if isinstance(x, dict) and str(x.get("id") or "").strip("[] ") in idler and isinstance(x.get("metin"), str): out[str(x["id"]).strip("[] ")] = " ".join(x["metin"].split())[:4000]
    return out, kul
def _hk_istek(model, govde):  # → (HTTP durumu (0: ağ hatası), gövde, Retry-After, sn); anahtar başlıkta (adreste değil)
    host = globals().get("GEMINI_HOST") or "generativelanguage.googleapis.com"; t0 = time.time()
    c = (http.client.HTTPConnection if host.startswith("127.0.0.1") else http.client.HTTPSConnection)(host, timeout=HK_ZAMAN_ASIMI)
    try:
        c.request("POST", f"/v1beta/models/{model}:generateContent", body=json.dumps(govde), headers={"Content-Type": "application/json", "x-goog-api-key": _hk_anahtar()})
        r = c.getresponse(); b = r.read().decode("utf-8", "replace"); return r.status, b, r.getheader("Retry-After"), time.time() - t0
    except (OSError, http.client.HTTPException) as e: return 0, e.__class__.__name__, None, time.time() - t0
    finally:
        try: c.close()
        except OSError: pass
def _hk_kullanim(kok, model, kul, sn, gecikme, durum, n):  # gemini-ses.jsonl'e (olcum.py maliyet okur); kuru çalıştırmada geçici klasöre
    usd = hakem_usd(model, kul.get("giris", 0), kul.get("cikis", 0) + kul.get("dusunce", 0))
    r = {"t": datetime.datetime.now().isoformat(timespec="seconds"), "model": model, "is": "hakem", "parca": n, "giris_sn": round(sn, 1), "giris_token": kul.get("giris", 0),
         "ses_token": kul.get("ses", 0), "cikis_token": kul.get("cikis", 0), "dusunce_token": kul.get("dusunce", 0), "usd": round(usd, 5), "gecikme_sn": round(gecikme, 1), "durum": durum}
    _so_ekle(_hk_kayit_yol(kok), json.dumps(r) + "\n"); return usd
def _hk_obek_gonder(model, obek, kl, kok):  # → (metinler ya da None, özet); yeniden deneme: 429/5xx/ağ en çok HK_DENEME; günlük kota → "kota"
    dus = AYAR.get("hakem_dusunme", "low") or None; sn = sum(r["sn"] for r in obek); oz = {"usd": 0.0, "gecikme": 0.0, "giris": 0, "cikis": 0, "hata": None}
    mods = [model] + [m for m in HAKEM_YEDEK if m != model]
    for den in range(HK_DENEME):
        model = mods[min(den, len(mods) - 1)]; govde = hakem_govde(obek, kl, dus)
        st, b, ra, gec = _hk_istek(model, govde); oz["gecikme"] += gec
        if st == 200:
            m, kul = hakem_coz(b, len(obek)); oz["usd"] += _hk_kullanim(kok, model, kul, sn, gec, "ok" if m is not None else "bozuk", len(obek))
            oz["giris"] += kul.get("giris", 0); oz["cikis"] += kul.get("cikis", 0) + kul.get("dusunce", 0)
            if m is not None: oz["model"] = model; return m, oz  # 4 Kasım: cevap veren gerçek model (yedeğe geçilmiş olabilir)
            oz["hata"] = "bozuk_cevap"; continue  # bozuk JSON: bir kez daha
        if st == 400 and dus and "think" in b.lower(): dus = None; oz["hata"] = "dusunme_ayari"; continue  # model düşünme ayarını tanımıyor: ayarsız
        if st == 429 and ("per_day" in b or "PerDay" in b): oz["hata"] = "kota"; return None, oz
        oz["hata"] = f"http_{st}" if st else f"ag_{b}"
        try: oz["mesaj"] = " ".join(str(json.loads(b)["error"].get("message") or "").split())[:120]  # Google'ın hata iletisi (içerik değil; günlüğe)
        except (ValueError, KeyError, TypeError, AttributeError): pass
        if st and st not in (429, 500, 502, 503, 504): return None, oz  # 400/401/403/404: yeniden deneme yok
        if den + 1 < len(mods): continue  # yedek model hemen (aynı modeli beklemek yerine)
        time.sleep(min(60.0, _gemini_bekleme(b, ra) if st == 429 and "_gemini_bekleme" in globals() else 5.0 * (3 ** den)))
    return None, oz
# --- hizalama: yerel (sözlük uygulanmış) ↔ hakem → "yanlış → doğru" çiftleri ---------------------------------------------------------------------------------------------------------
HK_SOZ_RX = re.compile(r"[^\W_]+(?:['’][^\W\d_]+)?(?:-[^\W_]+)*")
def _hk_k(w): return re.sub(r"[^0-9a-z]", "", sade(w))
def _hk_toklar(t): return [(m.group(0), m.start()) for m in HK_SOZ_RX.finditer(t or "")]
def _hk_ek(w): p = re.split(r"['’]", w, 1); return p[0], (p[1] if len(p) > 1 else "")
HK_BUYUK = re.compile(r"[A-ZÇĞİÖŞÜ]")
def _hk_cift(ys, ds, cumle_basi, B, orta=()):  # orta: hakem metninde cümle ortasında büyük harfle de geçen sözcükler (cümle başındaki aynı sözcük ad sayılır)  # ys/ds: yerel/hakem sözcükleri → (yanlış, doğru) ya da None
    ys, ds = list(ys), list(ds)
    y0, ye = _hk_ek(ys[-1]); d0, de = _hk_ek(ds[-1])
    if ye or de:  # ek (kesmeli) kuralın parçası değil: "Belvoraya" / "Pelvora'ya" → Belvora → Pelvora
        ek = _hk_k(de or ye)
        if de: ds[-1] = d0
        if ye: ys[-1] = y0
        elif ek and _hk_k(ys[-1]).endswith(ek) and len(_hk_k(ys[-1])) - len(ek) >= 3 and sade(ys[-1])[-len(ek):] == ek: ys[-1] = ys[-1][:-len(ek)]
        if not de and ek and _hk_k(ds[-1]).endswith(ek) and len(_hk_k(ds[-1])) - len(ek) >= 3 and sade(ds[-1])[-len(ek):] == ek: ds[-1] = ds[-1][:-len(ek)]
    y, d = " ".join(ys), " ".join(ds); ky, kd = "".join(map(_hk_k, ys)), "".join(map(_hk_k, ds))
    if y == d or (ky == kd and len(ys) == len(ds)): return None  # yalnız büyük/küçük harf ya da ek ayrımı
    if not ky or not kd or len(y) > 60 or len(d) > 60 or re.search(r"\d", y + d): return None  # sayı yazımı farkı kanıt değil
    if any(_hk_k(w) in SO_SAYI for w in ys + ds): return None
    if ky != kd and (ky.startswith(kd) or kd.startswith(ky)) and abs(len(ky) - len(kd)) <= 4: return None  # ek farkı ("raporu" / "raporunu")
    if all(_hk_k(w) in SO_DUR for w in ds) or any(len(_hk_k(w)) < 2 for w in ds): return None
    # doğru biçim ad/terim gibi görünmeli: cümle ortasında büyük harf, iç büyük harf ya da kısaltma, ya da kapalı kümede geçen terim
    terim = any(HK_BUYUK.search(w) and (not (cumle_basi and i == 0) or _hk_k(w) in orta or HK_BUYUK.search(w[1:]) or (w.isupper() and len(w) >= 2)) for i, w in enumerate(ds))
    if not terim and not (B and _so_k(d) in B["kucuk"]): return None
    if B and _so_k(y) in B["kucuk"]: return None  # yanlış biçim kendisi bilinen bir terim
    if ky != kd and difflib.SequenceMatcher(None, ky, kd).ratio() < 0.4 and not ("_ad_anahtar" in globals() and _ad_anahtar(y) == _ad_anahtar(d)): return None  # hizalama kayması
    return y, d
def _hk_hizala(yp, hp, B=None):  # 4 Kasım: BÜTÜN hizalama — yp/hp yerel/hakem metin listeleri (zaman sırasıyla, aynı kanal); Gemini parça sınırına uymaz (birleştirir, kimlik kayar), parça başına hizalama anlamsız
    a = [(w, pi) for pi, t in enumerate(yp) for w, _ in _hk_toklar(t)]; hm = " ".join(h for h in hp if h); b = _hk_toklar(hm)
    ka, kb = [_hk_k(w) for w, _ in a], [_hk_k(w) for w, _ in b]; out = []; mes = fazla = 0; sb = lambda s: not s or s[-1] in ".!?:…\"“"
    orta = {kb[j] for j, (w, c) in enumerate(b) if HK_BUYUK.match(w) and not sb(hm[:c].rstrip())}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ka, kb, autojunk=False).get_opcodes():
        if op == "equal": continue
        mes += max(i2 - i1, j2 - j1) if op == "replace" else (i2 - i1 if op == "delete" else j2 - j1)
        if op == "delete": fazla += i2 - i1
        if op != "replace" or not (1 <= i2 - i1 <= 3 and 1 <= j2 - j1 <= 2): continue
        r = _hk_cift([w for w, _ in a[i1:i2]], [w for w, _ in b[j1:j2]], sb(hm[:b[j1][1]].rstrip()), B, orta)
        if r and r not in [(y, d) for y, d, _ in out]: out.append(r + (a[i1][1],))  # üçüncü öğe: yerel sözcüğün geldiği parçanın sırası (kanıt cümlesi için)
    return {"ciftler": out, "mesafe": mes, "kelime": len(b), "yerel_kelime": len(a), "yerel_fazla": fazla}
def hakem_ciftler(yerel, hakem, B=None): return [(y, d) for y, d, _ in _hk_hizala([yerel], [hakem], B)["ciftler"]]
def _hk_yerel(p):  # parçanın yerel metni sözlük uygulanmış hâliyle (dökümdeki gibi); parcalar.jsonl'de Whisper'ın sözlük öncesi metni durur
    m = " ".join(str(p.get("metin") or "").split())
    try: return sozluk_uygula(m, None)[0] if m else ""
    except Exception: return m
def _hk_kanallar(kl, H):  # → {kanal: [(parça, hakem kaydı)]} saat sırasıyla; yalnız hakemde kaydı olan parçalar (kırpılanlar dışarıda)
    K = collections.defaultdict(list)
    for p in _hk_parcalar_oku(kl):
        if p["dosya"] in H: K[p["kanal"]].append((p, H[p["dosya"]]))
    return K
def _kaynak_hakem(c):  # SO_KAYNAKLAR: hakem.jsonl tamamlanmış toplantı → {yanlis, aday_dogru, kaynak: hakem, toplanti, cumle}
    kl = _hk_kl(c["md"]); H, son = _hk_oku(os.path.join(kl, "hakem.jsonl"))
    if not son or not H: return []
    out = []
    for kanal, L in _hk_kanallar(kl, H).items():
        yer = [_hk_yerel(p) for p, _ in L]
        for y, d, pi in _hk_hizala(yer, [h.get("metin") or "" for _, h in L], c.get("B"))["ciftler"]:
            out.append({"yanlis": y, "aday_dogru": d, "kaynak": "hakem", "toplanti": c["md"], "cumle": _so_cumle(yer[pi], y)})
    return out
if not any(a == "hakem" for a, _ in SO_KAYNAKLAR): SO_KAYNAKLAR.append(("hakem", _kaynak_hakem))
# --- ölçüm (yalnız sayı) ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def hakem_olcum(md, kl, H, B=None):  # → yerel ↔ hakem sözcük hata oranı (hakem başvuru), kanal başına, kanalın bütün metni hizalanarak; terim isabeti; yerelde olup hakemde karşılığı olmayan sözcük oranı
    K = collections.defaultdict(lambda: {"parca": 0, "kelime": 0, "hata_ham": 0, "hata_sozluk": 0, "sn": 0.0, "fazla": 0, "yerel": 0})
    terimler = set(B["k"][0]) | set(B["k"][1]) if B else set(); th = tk = cift = 0
    for kanal, L in _hk_kanallar(kl, H).items():
        hp = [h.get("metin") or "" for _, h in L]; yer = [_hk_yerel(p) for p, _ in L]
        ham = _hk_hizala([" ".join(str(p.get("metin") or "").split()) for p, _ in L], hp); soz = _hk_hizala(yer, hp, B)
        k = K[kanal]; k["parca"] = len(L); k["sn"] = sum(p["sn"] for p, _ in L); k["kelime"] = soz["kelime"]; k["hata_ham"] = ham["mesafe"]; k["hata_sozluk"] = soz["mesafe"]
        k["fazla"] = soz["yerel_fazla"]; k["yerel"] = soz["yerel_kelime"]; cift += len(soz["ciftler"])
        if soz["kelime"] and terimler:
            hs, ys = " " + _so_k(" ".join(hp)) + " ", " " + _so_k(" ".join(yer)) + " "
            for t in terimler:
                if " " + t + " " in hs:
                    th += 1
                    if " " + t + " " not in ys: tk += 1
    oran = lambda h, n: round(h / n, 3) if n else None
    top = {a: sum(k[a] for k in K.values()) for a in ("parca", "kelime", "hata_ham", "hata_sozluk", "sn", "fazla", "yerel")}
    return {"t": datetime.datetime.now().isoformat(timespec="seconds"), "toplanti": md, "tarih": md[:10], "parca": top["parca"], "sn": round(top["sn"], 1), "kelime": top["kelime"],
            "wer_ham": oran(top["hata_ham"], top["kelime"]), "wer_sozluk": oran(top["hata_sozluk"], top["kelime"]),
            "kanal": {a: {"parca": k["parca"], "kelime": k["kelime"], "sn": round(k["sn"], 1), "wer_ham": oran(k["hata_ham"], k["kelime"]), "wer_sozluk": oran(k["hata_sozluk"], k["kelime"])} for a, k in sorted(K.items())},
            "terim_hakem": th, "terim_kacan": tk, "yerel_fazla": oran(top["fazla"], top["yerel"]), "cift": cift}
# --- bir toplantı ----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def hakem_toplanti(md, kuru=False, cikti=None, en_cok_sn=None, durdur=None):  # → özet {durum, …}; kuru: hakem.jsonl, ölçüm ve kullanım kaydı yalnız cikti klasörüne (canlıya yazılmaz)
    acik, neden = hakem_acik()
    if not acik: return {"durum": neden}  # beta / kapalı / gizli kip / anahtar yok: ağa çıkılmaz
    if _hk_gizli_mi(md): return {"durum": "gizli"}
    if kuru and not cikti: return {"durum": "cikti_yok"}
    kl = _hk_kl(md); okl = cikti or kl; kok = cikti if kuru else None; os.makedirs(okl, exist_ok=True)
    hy = os.path.join(okl, "hakem.jsonl"); H, son = _hk_oku(hy)
    if son: return {"durum": "bitti", "onceden": True}
    rs, kirp = _hk_sec(_hk_parcalar_oku(kl), en_cok_sn or hakem_en_cok_sn())
    if not rs: return {"durum": "bos"}
    model = hakem_model(); kalan = [r for r in rs if r["dosya"] not in H]; oz = {"usd": 0.0, "gecikme": 0.0, "giris": 0, "cikis": 0, "obek": 0}; kul = []  # kul: cevap veren gerçek modeller
    if not os.path.exists(hy): os.close(os.open(hy, os.O_CREAT | os.O_WRONLY, 0o600))
    for ob in _hk_obekler(kalan):
        if durdur and durdur(): return dict(oz, durum="ertelendi")
        sn = sum(r["sn"] for r in ob); har = hakem_bugun_usd() + (hakem_bugun_usd(kok) if kok else 0.0); sin = hakem_gunluk_usd()
        if har + hakem_tahmin_usd(sn, model) > sin:
            print(f"HAKEM: günlük sınır ({sin:.2f} $; bugün {har:.3f} $) — bugün durdu"); return dict(oz, durum="sinir")
        m, o = _hk_obek_gonder(model, ob, kl, kok); oz["obek"] += 1; gm = o.get("model") or model
        if m is not None and gm not in kul: kul.append(gm)
        for a in ("usd", "gecikme", "giris", "cikis"): oz[a] += o[a]
        if m is None: print(f"HAKEM: öbek gönderilemedi ({o['hata']}{': ' + o['mesaj'] if o.get('mesaj') else ''}; {o['gecikme']:.0f} sn)"); return dict(oz, durum="kota" if o["hata"] == "kota" else "hata", hata=o["hata"])
        t = datetime.datetime.now().isoformat(timespec="seconds")
        _so_ekle(hy, "".join(json.dumps({"dosya": r["dosya"], "kanal": r["kanal"], "metin": m.get(f"p{i + 1}", ""), "model": gm, "t": t, **({"eksik": True} if f"p{i + 1}" not in m else {})},
                                        ensure_ascii=False) + "\n" for i, r in enumerate(ob)))
    H, _ = _hk_oku(hy)
    _so_ekle(hy, json.dumps({"son": True, "parca": len(H), "kirpildi": kirp, "model": "+".join(kul) or model, "t": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    ol = dict(hakem_olcum(md, kl, H, so_bilinen() if "so_bilinen" in globals() else None), model="+".join(kul) or model, usd=round(oz["usd"], 4), gecikme_sn=round(oz["gecikme"], 1),
              giris_token=oz["giris"], cikis_token=oz["cikis"], kirpildi=kirp, **({"kuru": True} if kuru else {}))
    _so_ekle(os.path.join(cikti if kuru else BASE, HK_OLCUM), json.dumps(ol, ensure_ascii=False) + "\n")
    print(f"HAKEM: {len(H)} parça · {ol['sn']} sn ses · {oz['obek']} istek · {oz['usd']:.4f} $ · yerel↔hakem hata ham {ol['wer_ham']} / sözlüklü {ol['wer_sozluk']} · terim kaçan {ol['terim_kacan']}/{ol['terim_hakem']} · yerel fazla {ol['yerel_fazla']}")
    return dict(oz, durum="bitti", olcum=ol)
# --- döngü (aktarıcıda, yalnız geliştiricide) ---------------------------------------------------------------------------------------------------------------------------------------
def hakem_bekleyen(durum, simdi=None):  # biten (≥ HK_BITIS_DK önce) ve ses arşivi olan toplantılar; süren, gizli işaretli, bitmiş, vazgeçilmiş değil
    simdi = simdi or time.time(); kok = _so_yol("ses-arsivi"); ak = aktif_dosya() if "aktif_dosya" in globals() else None; out = []
    try: adlar = sorted(os.listdir(kok))
    except OSError: return out
    for ad in adlar:
        md = ad + ".md"
        if not SO_MD_RX.match(md) or md == ak or not os.path.exists(_so_yol(md)) or not os.path.isfile(os.path.join(kok, ad, "parcalar.jsonl")): continue
        try: mt = max(os.path.getmtime(_so_yol(md)), os.path.getmtime(os.path.join(kok, ad, "parcalar.jsonl")))
        except OSError: continue
        if simdi - mt < HK_BITIS_DK * 60 or simdi - mt > SO_TARAMA_GUN * 86400: continue
        s = (durum.get("toplantilar") or {}).get(md) or {}
        if s.get("durum") in ("bitti", "gizli", "bos", "vazgecildi") or _so_hakem_hazir(md): continue
        if s.get("durum") in ("hata", "ertelendi", "kota", "sinir") and simdi - float(s.get("t") or 0) < HK_YENIDEN_DK * 60: continue
        out.append(md)
    return out
HK_OLAY = threading.Event()
def hakem_tetik(): HK_OLAY.set()
def hakem_tur():  # bir tur: bekleyen toplantılar sırayla; sınır/kota dolunca tur biter
    yol = _so_yol(HK_DURUM); d = _so_json(yol, {}); d.setdefault("toplantilar", {})
    for md in hakem_bekleyen(d):
        if toplanti_acik() or kaynak_dar() or not hakem_acik()[0]: break
        r = hakem_toplanti(md, durdur=lambda: toplanti_acik() or ("gizli_acik" in globals() and gizli_acik()))
        s = d["toplantilar"].setdefault(md, {"deneme": 0}); s.update(durum=r["durum"], t=time.time(), usd=round(float(s.get("usd") or 0) + float(r.get("usd") or 0), 4))
        if r["durum"] == "hata":
            s["deneme"] = int(s.get("deneme") or 0) + 1
            if s["deneme"] >= HK_VAZGEC: s["durum"] = "vazgecildi"; print(f"HAKEM: {HK_VAZGEC} denemede olmadı, bu toplantı bırakıldı")
        _so_yaz(yol, json.dumps(d, ensure_ascii=False), 0o600)
        if r["durum"] == "bitti" and "so_tetik" in globals(): so_tetik()  # öğrenme döngüsü toplantıyı hakem kanıtıyla yeniden işler
        if r["durum"] in ("sinir", "kota", "ertelendi"): break
def _hk_dongu():
    HK_OLAY.wait(120)
    while True:
        HK_OLAY.clear()
        try:
            if not (toplanti_acik() or kaynak_dar()) and hakem_acik()[0]: hakem_tur()
        except Exception as e: print(f"HAKEM: hata ({e.__class__.__name__}: {e})")
        HK_OLAY.wait(HK_ARALIK_SN)
# yalnız asıl aktarıcıda ve geliştiricinin kurulumunda (beta'da iş parçacığı hiç başlamaz); test SUFLOR_HK_DENEME=1 ile açar
if "STATE" in globals() and AYAR.get("hakem") is not False and AYAR.get("sozluk_ogren") is not False and gelistirici_mi() and (os.environ.get("SUFLOR_HK_DENEME") or not deneme_aktarici()):
    threading.Thread(target=_hk_dongu, daemon=True).start()
