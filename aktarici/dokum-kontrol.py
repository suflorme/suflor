# Suflor.me aktarıcı bölümü: toplantı sonrası döküm kontrolü (6 Kasım). Ayrı modül değildir — relay.py bunu kendi ad alanında sozluk-hakem.py'den sonra çalıştırır (bolum("dokum-kontrol")). import etme. Python 3.9.
# YALNIZ geliştiricinin kurulumunda (gelistirici_mi) ve ses arşivi açıkken (ayar ses_arsivi; kapatmak için ayar dokum_kontrol: false) çalışır. Hepsi yerel: ağ çağrısı, beta veri paketi yok.
# Gizli ve deneme toplantısı listeye girmez. Akış: toplantı biter, ses arşivi ve (varsa) Gemini hakem dökümü hazır olunca <ses-arsivi>/<toplantı>/kontrol-plan.json yazılır
# (öncelik sırası + nedenler); panoda "Döküm kontrolü" /dokum-kontrol sayfasını açar; kullanıcı satır satır dinler/düzeltir (kontrol-durum.json, kendiliğinden kayıt);
# "Bitir" duzeltme-elle.json'u (5 Kasım'daki elle düzeltmeyle aynı biçim) yazar ve (a) ölçüm canli/dokum-olcum.jsonl (yalnız sayı), (b) sözlük adayı (SO_KAYNAKLAR "elle"), (c) eğitim havuzu
# (egitim-havuzu/dogrulanmis/<toplantı>/ wav kopyası + dogrulanmis.jsonl; 14 günlük arşiv temizliği bunlara dokunmaz) işlerini yapar.
import hashlib
import shutil
DK_PLAN, DK_DURUM, DK_ELLE, DK_OLCUM, DK_SURUM = "kontrol-plan.json", "kontrol-durum.json", "duzeltme-elle.json", "dokum-olcum.jsonl", 1
DK_HEDEF = 200; DK_BLOK_SN = 300; DK_BAND = 80
DK_GEMINI_FARK = 0.22; DK_KARAR_PENCERE_SN = 40; DK_HIZ = 1.25; DK_KARAR_SN = 2.5  # tahmin: ses süresi / hız + satır başına karar süresi
DK_GERIDE_GUN = 7  # 12 Kasım: bitmemiş kontrol bu kadar günden eskiyse panoda gösterilmez ("geride"; ayar dokum_kontrol_gun, 1–60)
DK_BITIS_DK = 15; DK_BEKLE_SAAT = 3; DK_ARALIK_SN = 300; DK_TARAMA_GUN = 12
DK_RX_AD = re.compile(r"^[^\W\d_][\w.\-]*$"); DK_SOZ_RX = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?|\d+")
DK_NEDEN_AD = {"gemini": "Gemini farklı", "gemini_bos": "Gemini boş", "atlandi": "Whisper atladı", "ad": "ad/terim", "ad_gemini": "ad Gemini'de farklı", "karar": "karar/iş", "dil": "dil uyuşmuyor",
               "tekrar": "tekrar", "hiz": "hız tuhaf", "teams": "Teams farklı"}
def dk_acik():  # → (açık mı, neden)
    if AYAR.get("dokum_kontrol") is False: return False, "kapali"
    if not ("gelistirici_mi" in globals() and gelistirici_mi()): return False, "beta"
    if not AYAR.get("ses_arsivi"): return False, "ses_arsivi_kapali"
    return True, None
def _dk_kok(): return _so_yol("ses-arsivi")
def dk_gun_sinir():
    try: return int(min(60, max(1, float(AYAR.get("dokum_kontrol_gun", DK_GERIDE_GUN)))))
    except (TypeError, ValueError): return DK_GERIDE_GUN
def dk_kl(ad):  # klasör adı (toplantı kökü) → yol; ad klasör adından başka bir şey olamaz (ses arşivinin dışına çıkılmaz)
    ad = str(ad or "")
    if not ad or ad != os.path.basename(ad) or ad in (".", "..") or ad.startswith(("_", ".")): return None
    kok = os.path.realpath(_dk_kok()); y = os.path.realpath(os.path.join(kok, ad))
    return y if os.path.dirname(y) == kok and os.path.isdir(y) else None
def _dk_json(y, vars_=None):
    try: return json.load(open(y, encoding="utf-8"))
    except (OSError, ValueError): return vars_
def _dk_norm(t):
    t = str(t or "").replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"[^\wçğıöşü ]+", " ", t).split()
def _dk_gizli_mi(md):
    try: return _hk_gizli_mi(md)
    except Exception: return False
def _dk_saat(t): return datetime.datetime.fromtimestamp(float(t)).strftime("%H:%M:%S")
# --- sözcük hizalama (bantlı Levenshtein, geri izleme): 5 dk bloklarda hata ve sözcük torbası --------------------------------------------------------------------------------------------------
def _dk_hizala(R, S, band=None):  # → ops: ("e"|"s", ri, si) eşleşme/yerine, ("d", ri) eksik (R'de var), ("i", si, ri_yakin) fazla (S'de var)
    n, m = len(R), len(S)
    if not n: return [("i", j, -1) for j in range(m)]
    if not m: return [("d", i) for i in range(n)]
    band = max(band or DK_BAND, abs(n - m) + 8); INF = 10 ** 9; satir = []
    dp_onceki = None
    for i in range(n + 1):
        c = int(round(i * m / n)); lo, hi = max(0, c - band), min(m, c + band)
        sat = {}
        for j in range(lo, hi + 1):
            if i == 0: sat[j] = (j, 2 if j else 0); continue
            en = (INF, 0)
            if j >= 1 and (j - 1) in dp_onceki: x = dp_onceki[j - 1][0] + (R[i - 1] != S[j - 1]); en = (x, 0)  # çapraz
            if j in dp_onceki and dp_onceki[j][0] + 1 < en[0]: en = (dp_onceki[j][0] + 1, 1)  # R'de var, S'de yok (eksik)
            if (j - 1) in sat and sat[j - 1][0] + 1 < en[0]: en = (sat[j - 1][0] + 1, 2)  # S'de var, R'de yok (fazla)
            sat[j] = en
        satir.append(sat); dp_onceki = sat
    ops = []; i, j = n, m
    while i > 0 or j > 0:
        d, y = satir[i][j]
        if i > 0 and j > 0 and y == 0: ops.append(("e" if R[i - 1] == S[j - 1] else "s", i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and y == 1: ops.append(("d", i - 1)); i -= 1
        else: ops.append(("i", j - 1, i - 1)); j -= 1
    ops.reverse(); return ops
def _dk_blok_olc(R, F, S):  # R: referans (doğru ya da dinlenmemişte Whisper) sözcükleri, F: o sözcük dinlenen satırdan mı, S: sistemin sözcükleri
    # → (hata, dinlenen_ref, ref_torba(dinlenen), sistem_torba(dinlenen'e atanan), ad_ref, ad_sistem) — hata yalnız dinlenen referans sözcükler ve onlara bitişik fazlalıklar için sayılır
    ops = _dk_hizala(R, S); hata = 0; rt = collections.Counter(); st = collections.Counter()
    for o in ops:
        if o[0] in ("e", "s"):
            if F[o[1]]:
                rt[R[o[1]]] += 1; st[S[o[2]]] += 1; hata += o[0] == "s"
        elif o[0] == "d":
            if F[o[1]]: rt[R[o[1]]] += 1; hata += 1
        else:
            k = o[2] if o[2] >= 0 else 0
            if F and F[min(k, len(F) - 1)]: st[S[o[1]]] += 1; hata += 1
    return hata, sum(F), rt, st
def dk_hata_oranlari(sistemler, ad_set=None):  # sistemler: {ad: (ref_satirlari [(blok, sözcükler, dinlenen mi)], {blok: sistem sözcükleri})} — blok bazında yukarıdaki yöntem
    sonuc = {}
    for ad, (ref, B) in sistemler.items():
        hata = n = 0; rt = collections.Counter(); st = collections.Counter(); R = collections.defaultdict(list); F = collections.defaultdict(list)
        for b, w, f in ref: R[b] += w; F[b] += [f] * len(w)
        for b in sorted(R):
            if not any(F[b]): continue
            h, nn, r_, s_ = _dk_blok_olc(R[b], F[b], B.get(b, [])); hata += h; n += nn; rt += r_; st += s_
        ad_n = ad_h = 0
        if ad_set:
            for k, c in rt.items():
                if k in ad_set: ad_n += c; ad_h += min(c, st.get(k, 0))
        sonuc[ad] = {"hata": hata, "n": n, "eksik": sum((rt - st).values()), "fazla": sum((st - rt).values()), "ad_n": ad_n, "ad_hit": ad_h}
    return sonuc
# --- veri: parçalar, Gemini, Teams altyazısı, kararlar -------------------------------------------------------------------------------------------------------------------------------------------------
def _dk_altyazi(md, T0):  # canlı klasördeki <toplantı>.altyazi.log: captions satırları, aynı kimliğin son hâli → [(epoch, konuşmacı, metin)] zaman sırasıyla
    son = {}
    try:
        for l in open(_so_yol(md[:-3] + ".altyazi.log"), encoding="utf-8", errors="replace"):
            try: j = json.loads(l)
            except ValueError: continue
            if isinstance(j, dict) and j.get("src") == "captions" and j.get("id") and j.get("text"): son[j["id"]] = j
    except OSError: return []
    out = []
    for j in son.values():
        try: t = datetime.datetime.strptime(str(j.get("seen") or j.get("at"))[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError: continue
        out.append((t, str(j.get("speaker") or ""), str(j["text"])))
    return sorted(out)
def _dk_kararlar(md, T0):  # toplantı özeti yapı dosyasındaki karar/iş maddelerinin saatleri → epoch listesi (yapı dosyası yoksa boş)
    y = _so_yapi_yol(md) if "_so_yapi_yol" in globals() else None; d = _dk_json(y, {}) if y else {}
    out = []; gun = datetime.datetime.fromtimestamp(T0).date()
    for m in d.get("maddeler") or []:
        for o in (m.get("ogeler") or []) if isinstance(m, dict) else []:
            if isinstance(o, dict) and o.get("tur") in ("karar", "is", "iş", "gorev"):
                try: h, mi, s = (list(map(int, str(o.get("saat")).split(":"))) + [0])[:3]; out.append(datetime.datetime.combine(gun, datetime.time(h % 24, mi, s)).timestamp())
                except (ValueError, TypeError): pass
    return out
def _dk_adlar():  # kapalı küme ad/terim sözcükleri (sade anahtar): sözlük, kişi kayıtları, proje kartı, takvim, kayıt veritabanı; büyük harfle başlayan yazımlar
    try: B = so_bilinen()
    except Exception: return set()
    out = set()
    for i in (0, 1):
        for x, _ in list(B["k"][i].values()) + list(B["tok"][i].values()):
            for w in str(x).split():
                if w[:1].isupper() and len(_so_k(w)) >= 3 and not w.isdigit(): out.add(_so_k(w).split(" ")[0])
    return out - {"bey", "hanim", "hanım", "abi", "hoca"}
def _dk_gemini_eslesme(P, G):  # Gemini parça sınırına uymaz (kayar): ±3 komşu içinde aynı kanaldan en benzeyen kayıt; → [(metin ("" = benzeyen yok), benzerlik)]
    out = []
    for i, p in enumerate(P):
        a = " ".join(_dk_norm(p.get("metin"))); en = (0.0, "")
        if p["dosya"] in G and len(a) >= 4:
            for j in range(max(0, i - 3), min(len(P), i + 4)):
                if P[j]["kanal"] != p["kanal"] or P[j]["dosya"] not in G: continue
                gm = G[P[j]["dosya"]].get("metin") or ""
                if not gm: continue
                r = difflib.SequenceMatcher(None, a, " ".join(_dk_norm(gm))).ratio()
                if r > en[0]: en = (r, gm)
        out.append((en[1] if en[0] >= 0.6 else "", en[0]))
    return out
def _dk_tekrar(w):  # ardışık üç aynı sözcük ya da bir ikilinin üç tekrarı
    n = len(w)
    for i in range(n - 2):
        if w[i] == w[i + 1] == w[i + 2]: return True
    for i in range(n - 5):
        if w[i:i + 2] == w[i + 2:i + 4] == w[i + 4:i + 6]: return True
    return False
def dk_plan_uret(md, kaydet=True, kl=None):  # → plan sözlüğü ya da None (parça yok); kaydet: kontrol-plan.json
    kl = kl or _hk_kl(md); P = _hk_parcalar_oku(kl)
    if not P: return None
    H, hson = _hk_oku(os.path.join(kl, "hakem.jsonl")); T0 = float(P[0]["t0"]); adlar = _dk_adlar(); karar = _dk_kararlar(md, T0)
    G = _dk_gemini_eslesme(P, H); alt = _dk_altyazi(md, T0); ben = ""
    try: ben = ben_adi() or ""
    except Exception: pass
    # Teams altyazısı → satır: kanal (konuşmacı ben mi) uyan, [t0 - 1, t1 + 2] içinde yakalanan; birden çok satıra uyanda t0'ı en yakın olan
    TA = collections.defaultdict(list)
    for t, kim, tx in alt:
        kanal = "ben" if ben and kim == ben else "karsi"; en = None
        for i, p in enumerate(P):
            if p["kanal"] == kanal and p["t0"] - 1 <= t <= p["t1"] + 2.5 and (en is None or abs(p["t0"] - t) < abs(P[en]["t0"] - t)): en = i
        if en is not None: TA[en].append(tx)
    sat = []
    for i, p in enumerate(P):
        m = " ".join(str(p.get("metin") or "").split()); w = _dk_norm(m); kayit = p["dosya"] in H; ham = " ".join(str((H.get(p["dosya"]) or {}).get("metin") or "").split()); hw = _dk_norm(ham)
        if not w and not hw: continue  # Whisper boş, Gemini de boş (ya da hakem yok): sessizlik — kontrol edilecek bir şey yok
        g, benz = G[i]; gw = _dk_norm(g); ne, puan = [], 0.0
        # Ağırlıklar 5 Kasım'da elle düzeltilen 919 satıra bakılarak seçildi (kaynakların uyuşmaması düzeltme olasılığını artırır; hepsinin uyuştuğu satırda düzeltme oranı 0,14 / taban 0,31)
        if not w: ne.append("atlandi"); puan += 4.0; g = ham if len(hw) >= 2 else ""  # Whisper atladı (uydurma süzgeci ya da boş), Gemini duymuş
        elif kayit and not hw and len(w) >= 3: ne.append("gemini_bos"); puan += 1.5  # Gemini hiçbir şey duymadı: Whisper uydurmuş olabilir
        elif kayit and hw and not gw and len(w) >= 3: ne.append("gemini"); puan += 3.0; g = ham  # komşularda da benzeyen yok: tamamen ayrışıyor
        elif gw:
            fark = 1 - difflib.SequenceMatcher(None, w, gw).ratio()
            if fark >= DK_GEMINI_FARK and max(len(w), len(gw)) >= 3: ne.append("gemini"); puan += 2.5 + 0.5 * fark
        tw = _dk_norm(" ".join(TA.get(i, [])))  # Teams: Whisper sözcüklerinin Teams'te bulunmayan oranı (te) ve tersi (tf); 5 harflik köklerle (ek farkı sayılmaz)
        if tw and w:
            kt, kw = {x[:5] for x in tw}, {x[:5] for x in w}; te = sum(1 for x in w if x[:5] not in kt) / len(w); tf = sum(1 for x in tw if x[:5] not in kw) / len(tw)
            puan += 2.5 * te + 2.5 * tf
            if te == 0 and tf == 0: puan -= 1.5  # Whisper ve Teams birebir uyuşuyor
            elif te >= 0.3 or tf >= 0.4: ne.append("teams")
        sw = {_so_k(x) for x in w}; sg = {_so_k(x) for x in _dk_norm(g)}
        if sw & adlar: ne.append("ad"); puan += 0.3
        elif sg & adlar: ne.append("ad_gemini"); puan += 1.0
        if w and any(abs(p["t0"] - k) <= DK_KARAR_PENCERE_SN for k in karar): ne.append("karar"); puan += 1.5
        if w and p.get("dil") and p.get("dil_istek") and p["dil"] != p["dil_istek"]: ne.append("dil"); puan += 0.3
        if _dk_tekrar(w): ne.append("tekrar"); puan += 2.0
        sn = float(p.get("sn") or 0)
        if w and sn >= 1.5 and (len(w) / sn > 5.5 or (sn >= 3 and len(w) / sn < 0.4)): ne.append("hiz"); puan += 1.0
        if p["kanal"] == "ben": puan -= 1.5  # kendi mikrofonu: yakın ses, düzeltme oranı daha düşük
        sat.append({"d": p["dosya"], "k": p["kanal"], "s": _dk_saat(p["t0"]), "o": round(p["t0"] - T0, 2), "n": round(sn, 2), "m": m, "g": g if " ".join(_dk_norm(g)) != " ".join(w) else "",
                    "t": " ".join(TA.get(i, []))[:400], "ne": ne, "p": round(puan, 2), "e": kayit})
    sirali = sorted((s for s in sat if s["p"] > 1.0), key=lambda s: (-s["p"], s["o"]))
    hedef = int(AYAR.get("dokum_kontrol_satir") or DK_HEDEF); sec = {s["d"] for s in sirali[:hedef]}
    tahmin = lambda L: round(sum(s["n"] / DK_HIZ + DK_KARAR_SN for s in L) / 60, 1)
    tam = any(f.startswith("tam") and f.endswith((".m4a", ".wav")) for f in os.listdir(kl))
    plan = {"surum": DK_SURUM, "toplanti": md, "t0": T0, "uretildi": datetime.datetime.now().isoformat(timespec="seconds"), "hakem": bool(hson), "teams": bool(alt), "tam": tam,
            "satirlar": sat, "oncelikli": [s["d"] for s in sat if s["d"] in sec], "tahmin_dk": {"oncelikli": tahmin([s for s in sat if s["d"] in sec]), "tumu": tahmin(sat)}}
    if kaydet: _so_yaz(os.path.join(kl, DK_PLAN), json.dumps(plan, ensure_ascii=False), 0o600)
    return plan
# --- kayıtlı durum ve bitirme -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def dk_durum_oku(kl):
    d = _dk_json(os.path.join(kl, DK_DURUM), {}); d = d if isinstance(d, dict) else {}
    return {"dinlenen": [x for x in (d.get("dinlenen") or []) if isinstance(x, str)], "duz": {k: v for k, v in (d.get("duz") or {}).items() if isinstance(k, str) and isinstance(v, str)},
            "konum": d.get("konum") if isinstance(d.get("konum"), str) else "", "mod": d.get("mod") if d.get("mod") in ("oncelikli", "tumu") else "oncelikli", "bitti": d.get("bitti") or None, "kapatma": "elle" if d.get("kapatma") == "elle" else None, "t": d.get("t")}
def dk_kaydet(kl, plan, p):  # sayfanın kendiliğinden kaydı: yalnız plandaki satırlar; metin sadeleştirilir, uzunluk sınırlanır
    bilinen = {s["d"] for s in plan["satirlar"]}; eski = dk_durum_oku(kl)
    din = [x for x in (p.get("dinlenen") or []) if isinstance(x, str) and x in bilinen]
    duz = {k: " ".join(v.split())[:600] for k, v in (p.get("duz") or {}).items() if isinstance(k, str) and k in bilinen and isinstance(v, str) and v.strip()}
    d = {"dinlenen": sorted(set(din)), "duz": duz, "konum": p.get("konum") if p.get("konum") in bilinen else eski["konum"], "mod": p.get("mod") if p.get("mod") in ("oncelikli", "tumu") else eski["mod"],
         "bitti": eski["bitti"], "kapatma": eski["kapatma"], "t": datetime.datetime.now().isoformat(timespec="seconds")}
    _so_yaz(os.path.join(kl, DK_DURUM), json.dumps(d, ensure_ascii=False), 0o600); return d
def dk_elle_yaz(kl, plan, d):  # 5 Kasım'daki duzeltme-elle.json biçimi (+ dinlenen liste): {dosya, kanal, saat, whisper, gemini, dogru}
    S = {s["d"]: s for s in plan["satirlar"]}
    out = {"toplanti": os.path.basename(kl), "kaydedildi": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z", "dinlenen_satir": len(d["dinlenen"]), "toplam_satir": len(S),
           "duzeltmeler": [{"dosya": x, "kanal": S[x]["k"], "saat": S[x]["s"], "whisper": S[x]["m"], "gemini": S[x]["g"], "dogru": v} for x, v in sorted(d["duz"].items(), key=lambda kv: S[kv[0]]["o"])
                           if x in S and " ".join(_dk_norm(v)) != " ".join(_dk_norm(S[x]["m"]))],
           "dinlenen": sorted(d["dinlenen"], key=lambda x: S[x]["o"] if x in S else 0)}
    # 6 Kasım: önceki düzeltmeler hiç kaybolmaz — eski dosyadaki (başka sayfayla ya da önceki turda yapılmış) satırlar korunur, bu turdakiler üstüne yazar;
    # yazmadan önce önceki dosya zaman damgalı yedeğe kopyalanır (v0.199.0 ilk kayıtta 5 Kasım'daki 287 düzeltmeyi silmişti)
    yol = os.path.join(kl, DK_ELLE); eski = _dk_json(yol)
    if isinstance(eski, (dict, list)) and eski:
        try: shutil.copy2(yol, os.path.join(kl, "duzeltme-elle-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"))
        except OSError: pass
        e_duz = eski if isinstance(eski, list) else (eski.get("duzeltmeler") or [])
        bu = {x["dosya"] for x in out["duzeltmeler"]} | set(d["dinlenen"])
        kalan = [x for x in e_duz if isinstance(x, dict) and x.get("dosya") and x["dosya"] not in bu]
        out["duzeltmeler"] = kalan + out["duzeltmeler"]
        e_din = [] if isinstance(eski, list) else (eski.get("dinlenen") or [])
        out["dinlenen"] = sorted(set(out["dinlenen"]) | set(e_din) | {x["dosya"] for x in kalan}, key=lambda x: S[x]["o"] if x in S else 0)
        out["dinlenen_satir"] = len(out["dinlenen"])
    _so_yaz(yol, json.dumps(out, ensure_ascii=False, indent=1), 0o600); return out
def dk_elle_oku(kl, plan=None):  # → (düzeltme {dosya: doğru}, dinlenen kümesi, ham) ya da None; eski dosyada dinlenen listesi yok: ilk N satır (eski sayfa baştan sona dinlerdi)
    e = _dk_json(os.path.join(kl, DK_ELLE))
    if not isinstance(e, dict): return None
    duz = {x["dosya"]: x["dogru"] for x in e.get("duzeltmeler") or [] if isinstance(x, dict) and isinstance(x.get("dosya"), str) and isinstance(x.get("dogru"), str)}
    din = e.get("dinlenen")
    if isinstance(din, list): din = {x for x in din if isinstance(x, str)}
    else:
        n = int(e.get("dinlenen_satir") or 0); P = _hk_parcalar_oku(kl); din = {p["dosya"] for p in P[:n]}
    return duz, din | set(duz), e
def dk_olcum(md, kl, plan, duz, din):  # → ölçüm kaydı (yalnız sayı; toplantı adı yok: yalnız başlangıç dakikası). Referans: dinlenen satırda doğru metin, dinlenmeyende Whisper (yalnız hizalamayı tutar, hata sayılmaz)
    S = {s["d"]: s for s in plan["satirlar"]}; T0 = plan["t0"]; adlar = _dk_adlar(); H, _ = _hk_oku(os.path.join(kl, "hakem.jsonl")); P = [p for p in _hk_parcalar_oku(kl) if p["dosya"] in S]
    blok = lambda t: int((t - T0) // DK_BLOK_SN)
    ref, ref_g, W, Gm, Tm = [], [], collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for p in P:
        s = S[p["dosya"]]; b = blok(p["t0"]); f = p["dosya"] in din; wm = _dk_norm(s["m"]); rw = _dk_norm(duz.get(p["dosya"], s["m"])) if f else wm
        ref.append((b, rw, f)); W[b] += wm
        if p["dosya"] in H: ref_g.append((b, rw, f)); Gm[b] += _dk_norm(H[p["dosya"]].get("metin"))
        else: ref_g.append((b, wm, False)); Gm[b] += wm  # hakem kaydı yok (kırpıldı): Gemini için hata sayılmaz
    alt = _dk_altyazi(md, T0)
    for t, kim, tx in alt: Tm[blok(t)] += _dk_norm(tx)
    sis = {"whisper": (ref, W)}
    if any(p["dosya"] in H for p in P): sis["gemini"] = (ref_g, Gm)  # kaynağı olmayan sistem ölçülmez (null)
    if alt: sis["teams"] = (ref, Tm)
    r = dk_hata_oranlari(sis, adlar); r = {a: r.get(a, {"hata": 0, "n": 0, "eksik": None, "fazla": None, "ad_n": 0, "ad_hit": None}) for a in ("whisper", "gemini", "teams")}
    oran = lambda a, b: round(a / b, 4) if b else None
    sn = sum(S[x]["n"] for x in din if x in S); dz = [x for x in duz if x in din and x in S and " ".join(_dk_norm(duz[x])) != " ".join(_dk_norm(S[x]["m"]))]
    return {"t": datetime.datetime.now().isoformat(timespec="seconds"), "toplanti": md[:15], "tarih": md[:10], "dinlenen": len(din & set(S)), "toplam": len(S), "oncelikli": len(plan["oncelikli"]),
            "oncelikli_dinlenen": len(set(plan["oncelikli"]) & din), "duzeltme": len(dz), "sn_dinlenen": round(sn, 1), "kelime": r["whisper"]["n"], "gemini_kelime": r["gemini"]["n"],
            "teams_altyazi": len(alt), "tam_kayit": bool(plan.get("tam")), "hakem": bool(plan.get("hakem")),
            "wer": {a: oran(r[a]["hata"], r[a]["n"]) for a in r}, "torba": {a: {"eksik": r[a]["eksik"], "fazla": r[a]["fazla"]} for a in r},
            "ad": {"n": r["whisper"]["ad_n"], **{a: r[a]["ad_hit"] for a in r}}}
def dk_olcum_yaz(kayit, kok=None):  # toplantı başına tek satır: aynı başlangıç dakikasının eski satırı yenisiyle değişir
    yol = os.path.join(kok or BASE, DK_OLCUM); L = []
    try: L = [l for l in open(yol, encoding="utf-8").read().splitlines() if l.strip()]
    except OSError: pass
    def anahtar(l):
        try: return json.loads(l).get("toplanti")
        except ValueError: return None
    L = [l for l in L if anahtar(l) != kayit["toplanti"]] + [json.dumps(kayit, ensure_ascii=False)]
    _so_yaz(yol, "\n".join(L) + "\n", 0o600)
def _kaynak_elle(c):  # SO_KAYNAKLAR: kullanıcının dinleyip düzelttiği satırlar → Whisper (sözlük sonrası) yanlış → doğru; yalnız gerçek ad/terim farkı (hakem hizalayıcısının süzgeci)
    kl = _hk_kl(c["md"]); o = dk_elle_oku(kl)
    if not o or not o[0]: return []
    S = {p["dosya"]: p for p in _hk_parcalar_oku(kl)}; out = []
    for dosya, dogru in o[0].items():
        p = S.get(dosya)
        if not p: continue
        yer = _hk_yerel(p)
        for y, d in hakem_ciftler(yer, " ".join(str(dogru).split()), c.get("B")): out.append({"yanlis": y, "aday_dogru": d, "kaynak": "elle", "toplanti": c["md"], "cumle": _so_cumle(yer, y)})
    return out
if not any(a == "elle" for a, _ in SO_KAYNAKLAR): SO_KAYNAKLAR.append(("elle", _kaynak_elle))
DK_HAVUZ_SENKRON = False  # test: havuz kopyası aynı iş parçacığında (üretimde arka planda: ilk tmutil addexclusion ~10 sn sürebilir)
def dk_havuz_uygun(plan): return AYAR.get("ses_arsivi_egitim") is not False and "gelistirici_mi" in globals() and gelistirici_mi() and not _dk_gizli_mi(plan["toplanti"])
def dk_havuza(kl, plan, din, duz):  # eğitim havuzu: dinlenen satırların wav kopyası + doğru metin → egitim-havuzu/dogrulanmis/<toplantı>/ ; → eklenen dosya sayısı (sınır aşılırsa 0)
    if not dk_havuz_uygun(plan): return 0
    try:
        hk = os.path.join(_sa_havuz(), "dogrulanmis"); hedef = os.path.join(hk, os.path.basename(kl)); os.makedirs(hedef, exist_ok=True)
        if not _SA.get("havuz_tm"): _SA["havuz_tm"] = True; _sa_tmutil(_sa_havuz())
        sinir = float(AYAR.get("ses_arsivi_egitim_gb") or 50) * 1024 ** 3; S = {s["d"]: s for s in plan["satirlar"]}; n = 0; satirlar = []
        for x in sorted(din, key=lambda x: S[x]["o"] if x in S else 0):
            s = S.get(x)
            if not s or not os.path.isfile(os.path.join(kl, x)): continue
            dst = os.path.join(hedef, x)
            if not os.path.exists(dst):
                if _sa_boy(_sa_havuz()) + os.path.getsize(os.path.join(kl, x)) > sinir: print("DÖKÜM KONTROLÜ: eğitim havuzu sınırda, kalan satırlar kopyalanmadı"); break
                shutil.copy2(os.path.join(kl, x), dst); n += 1
            dg = duz.get(x, s["m"]); satirlar.append({"dosya": x, "kanal": s["k"], "sn": s["n"], "saat": s["s"], "metin": dg, "whisper": s["m"], "duzeltildi": " ".join(_dk_norm(dg)) != " ".join(_dk_norm(s["m"])), "dinlendi": True})
        _so_yaz(os.path.join(hedef, "dogrulanmis.jsonl"), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in satirlar), 0o600)
        return n
    except Exception as e: print(f"DÖKÜM KONTROLÜ: havuza yazılamadı ({e.__class__.__name__})"); return 0
def dk_temiz_yenile(md):  # 13 Kasım: elle düzeltmeler temiz dökümde de görünsün (özet, karar, iş temiz dökümden) — toplanti-claude.py dokum --yenile
    try:
        r = subprocess.run(["/usr/bin/python3", "-B", os.path.join(os.path.dirname(os.path.abspath(__file__)), "toplanti-claude.py"), "--dir", BASE, "dokum", md, "--yenile"],
                           capture_output=True, text=True, timeout=180, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        print("DÖKÜM KONTROLÜ: temiz döküm " + ("yenilendi" if r.returncode == 0 and "yazıldı" in r.stdout else "yenilenmedi") + f" ({(r.stdout or r.stderr).strip().splitlines()[-1][:120] if (r.stdout or r.stderr).strip() else r.returncode})")
    except Exception as e: print(f"DÖKÜM KONTROLÜ: temiz döküm yenilenemedi ({type(e).__name__})")
def dk_bitir(ad, kuru_kok=None):  # kaydet düğmesi: duzeltme-elle.json + ölçüm + sözlük adayı + eğitim havuzu; → özet
    acik, neden = dk_acik()
    if not acik: return {"ok": False, "err": neden}
    kl = dk_kl(ad)
    if not kl: return {"ok": False, "err": "toplanti"}
    md = ad + ".md"; plan = _dk_json(os.path.join(kl, DK_PLAN))
    if not plan: return {"ok": False, "err": "plan_yok"}
    d = dk_durum_oku(kl)
    if not d["dinlenen"] and not d["duz"]: return {"ok": False, "err": "bos"}
    d["dinlenen"] = sorted(set(d["dinlenen"]) | set(d["duz"])); e = dk_elle_yaz(kl, plan, d); duz = {x["dosya"]: x["dogru"] for x in e["duzeltmeler"]}; din = set(e["dinlenen"])
    kayit = dk_olcum(md, kl, plan, duz, din); dk_olcum_yaz(kayit, kuru_kok); havuz = len(din) if dk_havuz_uygun(plan) else 0
    if DK_HAVUZ_SENKRON: dk_havuza(kl, plan, din, duz)
    elif havuz: threading.Thread(target=dk_havuza, args=(kl, plan, set(din), dict(duz)), daemon=True, name="dk-havuz").start()
    d["bitti"] = datetime.datetime.now().isoformat(timespec="seconds"); d["kapatma"] = None; _so_yaz(os.path.join(kl, DK_DURUM), json.dumps(d, ensure_ascii=False), 0o600)
    if "so_tetik" in globals(): so_tetik()  # öğrenen sözlük bu toplantıyı elle düzeltmeyle yeniden işler (so_bekleyen)
    if kuru_kok is None and duz: threading.Thread(target=dk_temiz_yenile, args=(md,), daemon=True, name="dk-temiz").start()
    print(f"DÖKÜM KONTROLÜ: kaydedildi · {len(din)} satır dinlendi · {len(e['duzeltmeler'])} düzeltme · hata Whisper {kayit['wer']['whisper']} Gemini {kayit['wer']['gemini']} Teams {kayit['wer']['teams']} · havuza {havuz} satır")
    return {"ok": True, "dinlenen": len(din), "duzeltme": len(e["duzeltmeler"]), "olcum": kayit, "havuz": havuz}
# --- hazırlık döngüsü ve panoya görünüm -----------------------------------------------------------------------------------------------------------------------------------------------------------------
def dk_bekleyen(simdi=None):  # plan hazırlanacak toplantılar (klasör adları): biten, ses arşivi var, gerçek, gizli değil, planı yok; hakem bitti ya da hakem çalışmayacak/uzun süre geçti
    simdi = simdi or time.time(); kok = _dk_kok(); ak = aktif_dosya() if "aktif_dosya" in globals() else None; out = []
    try: adlar = sorted(os.listdir(kok))
    except OSError: return out
    hacik = hakem_acik()[0] if "hakem_acik" in globals() else False
    for ad in adlar:
        md = ad + ".md"; kl = os.path.join(kok, ad)
        if not SO_MD_RX.match(md) or md == ak or not os.path.isdir(kl) or os.path.exists(os.path.join(kl, DK_PLAN)) or not os.path.exists(_so_yol(md)) or not os.path.isfile(os.path.join(kl, "parcalar.jsonl")): continue
        try: mt = max(os.path.getmtime(_so_yol(md)), os.path.getmtime(os.path.join(kl, "parcalar.jsonl")))
        except OSError: continue
        yas = simdi - mt
        if yas < DK_BITIS_DK * 60 or yas > DK_TARAMA_GUN * 86400: continue
        hazir = _hk_oku(os.path.join(kl, "hakem.jsonl"))[1] is not None
        if not hazir and hacik and yas < DK_BEKLE_SAAT * 3600: continue  # hakem çalışacak: bitmesini bekle (en çok DK_BEKLE_SAAT)
        if _dk_gizli_mi(md): continue
        try:
            if so_toplanti_turu(md, _so_satirlar(md)) != "gercek": continue
        except Exception: continue
        out.append(ad)
    return out
def dk_tur():
    if not dk_acik()[0]: return 0
    n = 0
    for ad in dk_bekleyen():
        if toplanti_acik() or kaynak_dar(): break
        try:
            if dk_plan_uret(ad + ".md"): n += 1
        except Exception as e: print(f"DÖKÜM KONTROLÜ: {ad[:16]} planı hazırlanamadı ({e.__class__.__name__}: {e})")
    if n: print(f"DÖKÜM KONTROLÜ: {n} toplantının kontrol listesi hazırlandı")
    return n
DK_OLAY = threading.Event(); DK_GOR = {"v": None, "zt": 0}
def dk_tetik(): DK_OLAY.set()
def dk_liste(bugun=None):  # → [{ad, tarih, satir, oncelikli, dinlenen, duzeltme, tahmin_dk, bitti, kapatma, geride, yas_gun, hakem, teams}] yeniden eskiye; yalnız planı hazır toplantılar
    # geride: bitmemiş ve dk_gun_sinir() günden eski (toplantı tarihi klasör adından) — pano göstermez; kapatma: "elle" (kullanıcı × ile kapattı) ya da None
    acik, _ = dk_acik()
    if not acik: return []
    bugun = bugun or datetime.date.today(); sinir = dk_gun_sinir(); out = []
    try: adlar = sorted(os.listdir(_dk_kok()), reverse=True)
    except OSError: return out
    for ad in adlar:
        kl = dk_kl(ad); pl = os.path.join(kl, DK_PLAN) if kl else None
        if not pl or not os.path.isfile(pl): continue
        plan = _dk_json(pl)
        if not isinstance(plan, dict) or not plan.get("satirlar"): continue
        d = dk_durum_oku(kl); n_on = len(plan.get("oncelikli") or []); din = set(d["dinlenen"])
        try: yas = (bugun - datetime.date.fromisoformat(ad[:10])).days
        except ValueError: yas = None
        out.append({"yas_gun": yas, "geride": bool(not d["bitti"] and yas is not None and yas > sinir), "kapatma": d["kapatma"], **{"ad": ad, "baslik": ad[16:].replace("-", " ") or ad, "tarih": ad[:10], "saat": ad[11:13] + ":" + ad[13:15] if re.match(r"\d{4}-\d\d-\d\d-\d{4}", ad) else "", "satir": len(plan["satirlar"]), "oncelikli": n_on,
                    "oncelikli_dinlenen": len(set(plan.get("oncelikli") or []) & din), "dinlenen": len(din), "duzeltme": len(d["duz"]), "tahmin_dk": (plan.get("tahmin_dk") or {}).get("oncelikli"), "bitti": d["bitti"],
                    "hakem": bool(plan.get("hakem")), "teams": bool(plan.get("teams"))}})
    return out
def dk_view():  # /status dokum_kontrol: panoda "Döküm kontrolü" (yalnız geliştirici + ses arşivi açık); 30 sn önbellek (kaydet/bitir sıfırlar)
    if not dk_acik()[0]: return None
    if time.time() - (DK_GOR.get("zt") or 0) > 30: DK_GOR.update(v=sorted(dk_liste(), key=lambda x: bool(x["geride"]))[:6], zt=time.time())  # geride olanlar sona: en güncel 6 satırı eski bitmemişler tüketmez
    L = DK_GOR["v"] or []
    return {"liste": L, "bekleyen": [x["ad"] for x in L if not x["bitti"] and not x["geride"]][:3]} if L else None
def dk_ses(ad, dosya):  # → wav baytları ya da None; yalnız plandaki satırın dosyası (yol gezintisi yok)
    kl = dk_kl(ad)
    if not kl or not dk_acik()[0] or not re.fullmatch(r"(ben|karsi)-\d{6}-[\w-]{1,12}\.wav", str(dosya or "")): return None
    y = os.path.join(kl, dosya)
    try: return open(y, "rb").read() if os.path.isfile(y) and not os.path.islink(y) else None
    except OSError: return None
def dk_istek(yol, tam_yol):  # GET /dokum-kontrol/liste | /dokum-kontrol/plan?t=<klasör>
    from urllib.parse import urlsplit, parse_qs
    sorgu = parse_qs(urlsplit(tam_yol).query); acik, neden = dk_acik()
    if not acik: return {"ok": False, "err": neden}
    if yol.endswith("/liste"): return {"ok": True, "liste": dk_liste(), "hiz": DK_HIZ}
    kl = dk_kl((sorgu.get("t") or [""])[0])
    if not kl: return {"ok": False, "err": "toplanti"}
    ad = os.path.basename(kl); plan = _dk_json(os.path.join(kl, DK_PLAN))
    if not plan:
        if not (os.path.isfile(os.path.join(kl, "parcalar.jsonl")) and not _dk_gizli_mi(ad + ".md")): return {"ok": False, "err": "plan_yok"}
        plan = dk_plan_uret(ad + ".md")
        if not plan: return {"ok": False, "err": "plan_yok"}
    return {"ok": True, "plan": plan, "durum": dk_durum_oku(kl), "ad": ad, "hiz": DK_HIZ}
def dk_islem(p):  # POST /dokum-kontrol {islem: kaydet|bitir|yenile|kapat, t, …}
    acik, neden = dk_acik()
    if not acik: return {"ok": False, "err": neden}
    ad = str(p.get("t") or ""); kl = dk_kl(ad)
    if not kl or _dk_gizli_mi(ad + ".md"): return {"ok": False, "err": "toplanti"}
    plan = _dk_json(os.path.join(kl, DK_PLAN))
    if p.get("islem") == "kapat":  # "atla/kapat": × düğmesi ya da sayfadaki "Bu kontrolü kapat" — plan olmasa da; ölçüm/sözlük/havuz işi yapılmaz, yalnız satır kapanır (bitti + kapatma "elle")
        d = dk_durum_oku(kl)
        if d["bitti"]: return {"ok": True, "kapatma": d["kapatma"]}  # zaten bitirilmiş (ölçüm yapılmış) ya da kapatılmış: dokunma
        d["bitti"] = datetime.datetime.now().isoformat(timespec="seconds"); d["kapatma"] = "elle"
        _so_yaz(os.path.join(kl, DK_DURUM), json.dumps(d, ensure_ascii=False), 0o600); DK_GOR["zt"] = 0; print(f"DÖKÜM KONTROLÜ: kontrol elle kapatıldı ({ad[:10]})"); return {"ok": True, "kapatma": "elle"}
    if p.get("islem") == "yenile":  # plan yeniden hesaplanır (durum korunur)
        plan = dk_plan_uret(ad + ".md"); DK_GOR["zt"] = 0; return {"ok": bool(plan)}
    if not plan: return {"ok": False, "err": "plan_yok"}
    if p.get("islem") == "kaydet": d = dk_kaydet(kl, plan, p); DK_GOR["zt"] = 0; return {"ok": True, "t": d["t"]}
    if p.get("islem") == "bitir":
        if "dinlenen" in p or "duz" in p: dk_kaydet(kl, plan, p)  # sayfa son durumu da gönderir
        r = dk_bitir(ad); DK_GOR["zt"] = 0; return r
    return {"ok": False, "err": "islem"}
def _dk_dongu():
    DK_OLAY.wait(90)
    while True:
        DK_OLAY.clear()
        try:
            if not (toplanti_acik() or kaynak_dar()): dk_tur()
        except Exception as e: print(f"DÖKÜM KONTROLÜ: hata ({e.__class__.__name__}: {e})")
        DK_OLAY.wait(DK_ARALIK_SN)
# yalnız asıl aktarıcıda ve geliştiricinin kurulumunda (beta'da iş parçacığı hiç başlamaz); test SUFLOR_DK_DENEME=1 ile açar
if "STATE" in globals() and AYAR.get("dokum_kontrol") is not False and gelistirici_mi() and (os.environ.get("SUFLOR_DK_DENEME") or not deneme_aktarici()):
    threading.Thread(target=_dk_dongu, daemon=True).start()
