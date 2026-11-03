# Suflor.me aktarıcı bölümü: Kendi kendine öğrenen sözlük (sözlük 2. aşama, 3 Kasım; plan ../planlar/sozluk-ogrenme-20261103.md). Ayrı modül değildir — relay.py bunu
# kendi ad alanında çalıştırır (bolum("sozluk-ogren")): sade, _kural_derle, sozluk_uygula (sozluk.py), _ad_anahtar, _ad_mesafe, AD_ILK_ESDEGER (bas-konus.py), LOCK, write,
# AYAR, BASE relay.py'nindir. toplanti-claude.py (sozluk --ogren / --ogrenilen / --geri-al) aynı dosyayı kendi ad alanında çalıştırır (ogren_ad_alani). import etme. Python 3.9.
# Döngü toplantı bitince arka planda (canlı toplantıda ve kaynak darken çalışmaz): kanıt kaynakları (SO_KAYNAKLAR; her biri {yanlis, aday_dogru, kaynak, toplanti, cumle} üretir —
# Claude'un yapı dosyasındaki "duzeltmeler", ses benzerliği; Gemini hakemi sozluk-hakem.py'de, aynı listeye eklenir) → aday defteri (canli/sozluk-aday.jsonl; sözlüğe doğrudan yazılmaz)
# → kabul kapısı (kapalı küme katmanları, kanıt eşiği, gündelik sözcük, geçmiş dökümde deneme) → sözlük (kaynak ogrenme-YYYYMMDD, önce yedek) + o toplantının dökümüne geriye dönük.
# Kayıt veritabanı Masaüstü'nde, aktarıcı okuyamaz: terimleri yardımcı (Suflor Brifing.app --vt-izle → toplanti-claude.py vt-izle) POST /vt-bellek ile verir; burada
# yalnız bellekte durur (kalıcı dosya yok; aktarıcı açılınca yardımcı yeniden gönderir). Günlüğe terim yazılmaz (yalnız sayı ve aday kimliği): günlük teşhis paketine girer.
import collections, hashlib, threading
VT_BELLEK = {"t": 0.0, "adlar": [], "terimler": []}  # adlar: ayar veritabani.kisiler (Konuş ad düzeltmesi); terimler: veritabani.terimler [{terim, tur, takma}]
def vt_bellek_al(p):  # POST /vt-bellek (anahtarlı) — yalnız beklenen alanlar, kısa dizgeler
    ad = [" ".join(str(x).split())[:120] for x in (p.get("adlar") or [])[:20000] if isinstance(x, str) and str(x).strip()]
    tr = []
    for x in (p.get("terimler") or [])[:20000]:
        if not isinstance(x, dict) or not isinstance(x.get("terim"), str) or not x["terim"].strip(): continue
        tr.append({"terim": " ".join(x["terim"].split())[:120], "tur": str(x.get("tur") or "")[:20],
                   "takma": [" ".join(str(t).split())[:120] for t in (x.get("takma") or [])[:20] if isinstance(t, str) and t.strip()]})
    VT_BELLEK.update(t=time.time(), adlar=ad, terimler=tr)
    if "_AD" in globals(): _AD["t"] = 0.0  # Konuş ad listesi yeniden kurulsun
    print(f"SÖZLÜK ÖĞRENME: kayıt veritabanından {len(ad)} ad, {len(tr)} terim belleğe alındı")
    if "so_tetik" in globals() and any(a.get("neden") == "oh_bekleniyor" for a in _so_defter_oku().values()): so_tetik()
    return {"ok": True, "adlar": len(ad), "terimler": len(tr)}
def vt_bellek_view(): return {"ok": True, "adlar": len(VT_BELLEK["adlar"]), "terimler": len(VT_BELLEK["terimler"]), "t": round(VT_BELLEK["t"]), "acilis": globals().get("ACILIS")}
if "STATE" in globals():  # yalnız aktarıcıda: eski kalıcı ad dosyası (v0.60.0) bir kez silinir — adlar artık yalnız bellekte (3 Kasım)
    try: os.remove(os.path.join(BASE, "vt-adlar.json")); print("SÖZLÜK ÖĞRENME: eski vt-adlar.json silindi (kayıt veritabanı adları artık yalnız bellekte)")
    except OSError: pass

SO_ADAY, SO_DURUM, SO_YEDEK = "sozluk-aday.jsonl", "sozluk-ogren.json", "sozluk-yedek"
SO_YEDEK_EN_COK = 20; SO_GECMIS_GUN = 30; SO_TARAMA_GUN = 3; SO_EN_AZ_SATIR = 10; SO_YAPI_BEKLE_DK = 60; SO_SURE_SN = 120; SO_ARALIK_SN = 300
# Eşikler (3 Kasım, gerçek geçmiş dökümde kuru çalıştırmayla seçildi — raporda): geçmiş denemede adayın kendi toplantıları dışında en çok max(SO_DIS_EN_AZ, kendi) satır
# değişebilir; gündelik sözcük = İngilizce sözlükte küçük harfli giriş, ya da geçmiş dökümde ≥ SO_GUNDELIK_TOPLANTI toplantıda küçük harfle, ya da proje belgelerinde
# ≥ SO_GUNDELIK_BELGE belgede küçük harfle geçen sözcük.
SO_DIS_EN_AZ = 2; SO_GUNDELIK_TOPLANTI = 3; SO_GUNDELIK_BELGE = 2; SO_BAGLAM_N = 4
# Kural sürümü (3 Kasım, v0.180.1): kapının kuralı değişince (ör. ad muafiyeti) kuraldan gelen retler yeniden değerlendirilir; OHOT "yanlış" cevabı kalıcıdır
SO_KURAL = 2; SO_RET_KALICI = ("ohot_yanlis",)
def so_yeniden(a): return a["durum"] == "ret" and a.get("kural") != SO_KURAL and a.get("neden") not in SO_RET_KALICI  # eski kural sürümünün reti
SO_SAYI = set("sifir bir iki uc dort bes alti yedi sekiz dokuz on yirmi otuz kirk elli altmis yetmis seksen doksan yuz bin milyon milyar bucuk yarim one two three four five six "
              "seven eight nine ten hundred thousand million billion percent yuzde".split())
SO_DUR = set("acaba aslinda bence boyle buna bunu bunun burada daha dedi diye evet gibi hani hayir henuz hepsi icin iste kadar kendi lazim nasil neden olan olarak oldu "
             "olsun sadece sonra simdi soyle sunu tamam yani yine zaten about after because could there their these those think where which would really should".split())
SO_DENEME_RX = re.compile(r"(?i)(deneme|test|echo|prova|trial)")  # toplanti-claude.py DENEME_RX ile aynı (maliyet etiketi)
SO_MD_RX = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}-.+\.md$")
SO_SOZ_RX = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?")
SO_OZET = {"son": None, "kabul": 0, "bekleyen": 0, "sorulan": 0, "yeni": 0}  # /status sozluk_ogrenme: kabul = sözlükteki öğrenilmiş kural, yeni = son 7 günde öğrenilen, bekleyen = bekliyor + soruldu
def _so_k(x): return " ".join(re.findall(r"[0-9a-z]+", sade(str(x or ""))))
def _so_yol(*a): return os.path.join(BASE, *a)
def so_kanal():  # OHOT kanalı: ayar klasörünün yanında sozluk/ (Suflor kurar, 0700; /Users/Shared değil — herkes okur)
    return os.path.expanduser(str(AYAR.get("sozluk_kanal") or os.path.join(os.path.dirname(globals().get("AYAR_YOL") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")), "sozluk")))
def so_oh_var():  # kayıt veritabanı ayarlı mı — beta'da yok: soru dosyası yazılmaz
    v = AYAR.get("veritabani"); return isinstance(v, dict) and bool(v.get("yol"))
def _so_json(yol, vars_):
    try: return json.load(open(yol, encoding="utf-8"))
    except (OSError, ValueError): return vars_
def _so_yaz(yol, metin, izin=None, saat_koru=False):  # geçici dosya + os.replace; saat_koru: dökümün değişme saati korunur (süren toplantı, arşiv ve geçmiş penceresi saate bakar)
    st = os.stat(yol) if saat_koru and os.path.exists(yol) else None
    tmp = f"{yol}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(metin)
    if izin: os.chmod(tmp, izin)
    elif st: os.chmod(tmp, st.st_mode & 0o777)
    os.replace(tmp, yol)
    if st: os.utime(yol, (st.st_atime, st.st_mtime))
def _so_ekle(yol, metin):  # satır ekleme: aktarıcıda write() (LOCK ile; disk dolunca bekletir), toplanti-claude.py ad alanında doğrudan
    if "write" in globals() and "STATE" in globals():
        with LOCK: write([(yol, metin)])
    else:
        with open(yol, "a", encoding="utf-8") as f: f.write(metin)
# --- aday defteri ------------------------------------------------------------------------------------------------------------------------------------------------------------------
def _so_aday_id(y, d): return "a" + hashlib.sha1((sade(y).strip() + "|" + d).encode()).hexdigest()[:8]
def _so_defter_oku():
    D = {}
    try:
        for l in open(_so_yol(SO_ADAY), encoding="utf-8"):
            try: a = json.loads(l)
            except ValueError: continue
            if isinstance(a, dict) and a.get("id"): D[a["id"]] = a
    except OSError: pass
    return D
def _so_defter_yaz(D): _so_yaz(_so_yol(SO_ADAY), "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in D.values()), 0o600)
# --- kapalı küme: (1) sözlük, proje kartı, takvim katılımcıları → (2) kayıt veritabanı (VT_BELLEK) → (3) proje dizini (belgede tam yazılış) → (4) OHOT sorusu ----------------------
def so_bilinen(ctx=None):
    B = {"k": [{}, {}], "tok": [{}, {}], "kucuk": set()}  # k[i]: anahtar → (yazım, kaynak) · tok[i]: çok sözcüklü adların sözcükleri (≥ 3 harf)
    def ekle(i, x, kaynak):
        x = " ".join(str(x or "").split())
        if not x or "@" in x or len(x) > 80: return
        k = _so_k(x)
        if len(k) < 2: return
        B["k"][i].setdefault(k, (x, kaynak)); B["kucuk"].add(k)
        if " " in k:
            for w in x.split():
                if len(_so_k(w)) >= 3: B["tok"][i].setdefault(_so_k(w), (w.strip(",.;:()"), kaynak)); B["kucuk"].add(_so_k(w))
    for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []): ekle(0, t.get("dogru"), "sozluk")
    kart = _so_json(os.path.join(AYAR["uygulama"], "proje-karti.json"), {})
    if kart.get("onay"):  # yalnız onaylı kart
        for x in kart.get("sozluk") or []: ekle(0, x.get("terim") if isinstance(x, dict) else x, "kart")
        for x in (kart.get("kisiler") or []) + (kart.get("kurumlar") or []):
            if isinstance(x, dict):
                ekle(0, x.get("ad"), "kart")
                for t in x.get("takma_adlar") or []: ekle(0, t, "kart")
        for x in kart.get("cikarilan_terimler") or []: ekle(0, x.get("terim") if isinstance(x, dict) else x, "kart")
    for o in _so_json(os.path.join(AYAR["uygulama"], "takvim.json"), {}).get("olaylar") or []:
        for x in o.get("kisiler") or []: ekle(0, x.get("ad") if isinstance(x, dict) else x, "takvim")
        for x in o.get("katilimcilar") or []: ekle(0, x, "takvim")
    for x in VT_BELLEK["terimler"]:
        ekle(1, x["terim"], "vt:" + (x.get("tur") or "?"))
        for t in x.get("takma") or []: ekle(1, t, "vt:" + (x.get("tur") or "?"))
    # ses benzerliği dizini: tek sözcüklü terim ve çok sözcüklü adın büyük harfli sözcükleri (anahtar ≥ 4) + çok sözcüklü terimin bitişik anahtarı (yalnız tam eşleşme)
    ses, bitisik = {}, {}
    for i in (0, 1):
        for k, (x, _) in list(B["k"][i].items()) + list(B["tok"][i].items()):
            if " " in x:
                if ctx and so_gundelik(x, ctx): continue
                bk = _ad_anahtar(x.replace(" ", ""))
                if len(bk) >= 5: bitisik.setdefault(bk, set()).add(x)
                continue
            a = _ad_anahtar(x)
            if len(a) >= 4 and x[:1].isupper() and not (ctx and so_gundelik(x, ctx)): ses.setdefault(a, set()).add(x)  # gündelik terim ("Liste", "Media") ses dizinine girmez
    B["ses"], B["bitisik"] = ses, bitisik
    return B
def _so_dizin():
    import sqlite3, pathlib
    y = os.path.join(AYAR["uygulama"], "dizin.sqlite")
    if not os.path.exists(y): return None
    try: return sqlite3.connect(pathlib.Path(y).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    except Exception: return None
SO_BELGE_DISI = ("toplanti", "gorusme", "konusma")  # dökümler (Whisper çıktısı) belge sayılmaz
def _so_dizin_ara(c, yazim, kucuk=False, n=200, harf=False):  # → yazımın (kucuk: küçük harfli sözcük olarak; harf: büyük/küçük ayırmadan sözcük olarak) geçtiği belge sayısı
    if c is None: return 0
    k = _so_k(yazim)
    if not k: return 0
    try: rows = c.execute("SELECT p.yol, p.metin FROM ara JOIN parca p ON p.id = ara.rowid JOIN dosya d ON d.yol = p.yol WHERE ara MATCH ? AND coalesce(d.gizli, 0) = 0 "
                          "AND d.tur NOT IN (?, ?, ?) LIMIT ?", ('n : "' + k + '"',) + SO_BELGE_DISI + (n,)).fetchall()
    except Exception: return 0
    rx = re.compile(r"(?<![^\W\d_])" + re.escape(yazim.lower() if kucuk else yazim) + (r"(?![^\W\d_])" if kucuk or harf else ""), re.I if harf else 0)
    return len({y for y, m in rows if rx.search(m or "")})
def so_katman(dogru, B, ctx=None):  # → (katman 1–4, kaynak)
    k = _so_k(dogru)
    for i in (0, 1):
        if k in B["k"][i]: return i + 1, B["k"][i][k][1]
        if " " not in k and k in B["tok"][i]: return i + 1, B["tok"][i][k][1]
    if _so_dizin_ara((ctx or {}).get("dizin"), dogru) >= 1: return 3, "dizin"
    return 4, None
# --- gündelik sözcük ve geçmiş döküm -----------------------------------------------------------------------------------------------------------------------------------------------
def _so_gecmis(gun):  # → [(toplantı .md, ham metin)]; ham = "raw" (sözlük değiştirdiyse özgün hâli) yoksa "text"; aynı (dosya, id) tek (son kayıt)
    sinir = time.time() - gun * 86400; out = {}
    for f in sorted(os.listdir(BASE)):
        if not (f.endswith(".jsonl") and f.count(".") == 1 and SO_MD_RX.match(f[:-6] + ".md")): continue
        try:
            if os.path.getmtime(_so_yol(f)) < sinir: continue
            for i, l in enumerate(open(_so_yol(f), encoding="utf-8", errors="replace")):
                try: o = json.loads(l)
                except ValueError: continue
                t = o.get("raw") or o.get("text")
                if isinstance(t, str) and t.strip(): out[(f, o.get("id") or i)] = (f[:-6] + ".md", t)
        except OSError: continue
    return list(out.values())
def _so_kucuk_say(gecmis):  # sade sözcük → küçük harfle (cümle başı dışında) geçtiği toplantı sayısı; df: sözcüğün geçtiği toplantı sayısı (bağlam sözcüğü seçimi)
    kucuk, df = collections.defaultdict(set), collections.defaultdict(set)
    for md, t in gecmis:
        for m in SO_SOZ_RX.finditer(t):
            w = re.split(r"['’]", m.group(0))[0]; s = sade(w); df[s].add(md)
            if w[:1].islower(): kucuk[s].add(md)
    return {k: len(v) for k, v in kucuk.items()}, {k: len(v) for k, v in df.items()}
_SO_EN = {}
def _so_ingilizce():  # macOS'un yerel İngilizce sözcük listesi (indirme yok); yalnız küçük harfli girişler — büyük harfliler özel ad
    if "s" not in _SO_EN:
        try: _SO_EN["s"] = {l.strip() for l in open("/usr/share/dict/words", encoding="utf-8", errors="replace") if l[:1].islower() and len(l.strip()) >= 3}
        except OSError: _SO_EN["s"] = set()
    return _SO_EN["s"]
def so_gundelik(yanlis, ctx):  # → gerekçe ya da None; çok sözcüklü biçimde her sözcük gündelikse gündelik
    neden = []
    for w in re.findall(r"[^\W\d_]+", yanlis):
        s = sade(w); lo = w.replace("İ", "i").replace("I", "ı").lower()
        if lo in ctx["en"] or s in ctx["en"]: neden.append("ingilizce")
        elif ctx["kucuk"].get(s, 0) >= SO_GUNDELIK_TOPLANTI: neden.append("dokum")
        elif _so_dizin_ara(ctx.get("dizin"), lo, kucuk=True) >= SO_GUNDELIK_BELGE: neden.append("belge")
        else: return None
    return ",".join(sorted(set(neden))) or None
SO_AY_GUN = set("ocak subat mart nisan mayis haziran temmuz agustos eylul ekim kasim aralik pazartesi sali carsamba persembe cuma cumartesi pazar".split())
_SO_AD = {}
def _so_ozel_adlar():  # macOS'un İngilizce özel ad listesi (propernames): gerçek bir ad başka bir ada çevrilmez
    if "s" not in _SO_AD:
        try: _SO_AD["s"] = {l.strip().lower() for l in open("/usr/share/dict/propernames", encoding="utf-8", errors="replace") if l.strip()}
        except OSError: _SO_AD["s"] = set()
    return _SO_AD["s"]
def so_gercek_sozcuk(w, ctx):  # ses kanıtı için: sözcük gerçek bir sözcük/ad mı (gündelik, ay/gün adı, İngilizce özel ad ya da proje belgelerinde aynı yazımla geçiyor) — öyleyse yanlış duyulmuş sayılmaz
    s = sade(w)
    return bool(so_gundelik(w, ctx) or s in SO_AY_GUN or s in _so_ozel_adlar() or _so_dizin_ara(ctx.get("dizin"), w, harf=True) >= 1)
def so_gundelik_dogru(d, ctx):  # doğru biçim gündelik mi: bu kurulumun dökümlerinde/belgelerinde küçük harfle kullanılan sözcük (İngilizce sözlüğe bakılmaz: bazı marka ve kişi adları orada küçük harfle de var)
    ws = re.findall(r"[^\W\d_]+", d)
    if len(ws) != 1: return None  # çok sözcüklü ad (iki İngilizce sözcükten marka adı) gündelik sayılmaz
    w = ws[0]; s = sade(w)
    return "dokum" if ctx["kucuk"].get(s, 0) >= SO_GUNDELIK_TOPLANTI else "belge" if _so_dizin_ara(ctx.get("dizin"), w.replace("İ", "i").replace("I", "ı").lower(), kucuk=True) >= SO_GUNDELIK_BELGE else None
SO_MUAF_BUYUK_EN_AZ = 2  # 3 Kasım: doğru biçim proje belgelerinde cümle ortasında büyük harfle ≥ 2 kez geçmeli ve küçük harfli geçişinden çok olmalı ("Marvin" 8/1; "Transkript" 1/18, "Evet" 175/5796, "Panoda" 5/54 muaf değil)
def so_kisilik_adlari():  # kişilik dosyalarının (ayar kisilik, kisilik_toplanti_disi) ad / gorunen_ad / uclu_ad / uclu_takilma / hitap girişleri → sade anahtarlar (aktarıcı ve toplanti-claude.py ad alanında aynı: kisilik.py'ye bağımlı değil)
    out = set(); gundelik = globals().get("HITAP_GUNDELIK") or {"oh", "ah", "eh", "evet", "hayır", "tamam", "peki", "merhaba", "selam"}
    for ayar in ("kisilik", "kisilik_toplanti_disi"):
        yol = os.path.expanduser(str(AYAR.get(ayar) or "").strip())
        if not yol: continue
        try: s = open(yol, encoding="utf-8").read()
        except OSError: continue
        m = re.match(r"\s*---\s*\n(.*?)\n---", s, re.S)
        for sat in (m.group(1).splitlines() if m else []):
            k, _, v = sat.partition(":"); k = k.strip().lower()
            if k in ("ad", "gorunen_ad", "uclu_ad", "uclu_takilma", "hitap"):
                for x in (v.split(",") if k == "hitap" else [v]):
                    x = x.strip()
                    if len(_so_k(x).replace(" ", "")) >= 3 and x.lower() not in gundelik: out.add(_so_k(x))
    return out
def _so_dizin_buyuk(c, yazim, n=200):  # → (cümle ortasında tam bu büyük harfli yazımla geçiş, küçük harfle geçiş) — dökümler sayılmaz; cümle başı (nokta/soru/ünlem/iki nokta/satır başı/liste ve başlık işareti sonrası) büyük sayımına girmez
    if c is None: return 0, 0
    k = _so_k(yazim)
    if not k: return 0, 0
    try: rows = c.execute("SELECT p.yol, p.metin FROM ara JOIN parca p ON p.id = ara.rowid JOIN dosya d ON d.yol = p.yol WHERE ara MATCH ? AND coalesce(d.gizli, 0) = 0 "
                          "AND d.tur NOT IN (?, ?, ?) LIMIT ?", ('n : "' + k + '"',) + SO_BELGE_DISI + (n,)).fetchall()
    except Exception: return 0, 0
    rx = re.compile(r"(?<![^\W\d_])" + re.escape(yazim) + r"(?![^\W\d_])", re.I); b = kc = 0
    for y, m in rows:
        for mm in rx.finditer(m or ""):
            if mm.group(0)[:1].islower() and yazim[:1].isupper(): kc += 1; continue
            if mm.group(0) != yazim: continue
            onc = (m[:mm.start()]).rstrip(" \t")
            if onc and onc[-1] not in ".!?:;\n|#*>-•—\"“": b += 1
    return b, kc
def so_dogru_muaf(d, ctx):  # → gerekçe ya da None: doğru biçim gerçek bir ad (kişilik adı/hitabı, onaylı proje kartında aynı yazım, proje belgelerinde cümle ortasında büyük harfle baskın) — terim_degil süzgecinden muaf. Ay ve gün adı muaf olmaz
    if not re.search(r"[A-ZÇĞİÖŞÜ]", d) or _so_k(d) in SO_AY_GUN: return None
    if "kis" not in ctx: ctx["kis"] = so_kisilik_adlari()
    if _so_k(d) in ctx["kis"]: return "kisilik"
    for t in (ctx["B"]["k"][0], ctx["B"]["tok"][0]):
        if t.get(_so_k(d), (None, None))[1] == "kart" and t[_so_k(d)][0] == d: return "kart"
    b, kc = _so_dizin_buyuk(ctx.get("dizin"), d)
    return "belge_buyuk" if b >= SO_MUAF_BUYUK_EN_AZ and kc < b else None
def _so_baglam_sec(a, ctx):  # bağlam kipi için adayın cümlelerinden en ayırt edici (geçmişte en az toplantıda geçen) ≥ 5 harfli sözcükler
    harici = set(_so_k(a["yanlis"]).split()) | set(_so_k(a["dogru"]).split()); say = collections.Counter()
    for k in a["kanit"]:
        for w in re.findall(r"[0-9a-z]+", sade(k.get("cumle") or "")):
            if len(w) >= 5 and w not in harici and w not in SO_DUR and w not in SO_SAYI: say[w] += 1
    return [w for w, _ in sorted(say.items(), key=lambda x: (ctx["df"].get(x[0], 0), -x[1], x[0]))[:SO_BAGLAM_N]]
def _so_terim(a, kip=None, baglam=None):
    return {"dogru": a["dogru"], "yanlis": [a["yanlis"]], "kip": kip or a.get("kip") or "duzelt", "baglam": list(baglam if baglam is not None else a.get("baglam") or [])}
def so_dene(terim, gecmis, kendi):  # tek kural geçmiş dökümde: → (kendi toplantılarında değişen satır, başka toplantılarda değişen satır)
    kur = _kural_derle(terim); ke = di = 0
    if not kur: return 0, 0
    for md, t in gecmis:
        if sozluk_uygula(t, None, kurallar=kur)[0] != t:
            if md in kendi: ke += 1
            else: di += 1
    return ke, di
# --- kanıt kaynakları (takılabilir): f(c) → [{yanlis, aday_dogru, kaynak, toplanti, cumle}]; c = {md, recs, yapi, tur, B, ctx} -------------------------------------------------------
def _so_cumle(metin, yanlis, n=15):  # ≤ n sözcük, yanlış biçim ortada
    s = sade(metin); i = s.find(sade(yanlis).split()[0]) if yanlis.split() else -1
    w = metin.split()
    if i < 0 or len(w) <= n: return " ".join(w[:n])
    j = len(metin[:i].split()); b = max(0, min(j - n // 2, len(w) - n)); return " ".join(w[b:b + n])
def _so_bul(recs, yanlis, dogru, saat=None):  # yanlış biçimin dökümde geçtiği satır (Claude düzeltmesi dökümde dayanaksızsa kanıt sayılmaz); saat verildiyse en yakını
    kur = _kural_derle({"dogru": dogru, "yanlis": [yanlis]})
    if not kur: return None
    bul = [r for r in recs if any(kur[0][0].search(sade(r.get(a) or "")) for a in ("raw", "text"))]
    if not bul: return None
    def sn(x):
        try: h, m, *s = [int(p) for p in str(x).split(":")]; return h * 3600 + m * 60 + (s[0] if s else 0)
        except ValueError: return None
    t = sn(saat) if saat else None
    return min(bul, key=lambda r: abs((sn(r.get("time")) or 0) - t)) if t is not None else bul[0]
def _kaynak_claude(c):  # toplantı oturumunun defter turu: yapı dosyasında "duzeltmeler" (dökümdeki biçim → doğrusu; yalnız bağlamdan emin olunanlar, yapi.py)
    out = []
    for d in ((c.get("yapi") or {}).get("duzeltmeler") or [])[:80]:
        if not isinstance(d, dict): continue
        y, dg = [re.sub(r"^[^\w]+|[^\w'’]+$", "", " ".join(str(d.get(a) or "").split())) for a in ("yanlis", "dogru")]
        yw, dw = y.split(), dg.split()
        while len(yw) > 1 and len(dw) > 1 and sade(yw[-1]) == sade(dw[-1]): yw.pop(); dw.pop()  # ortak son/baş sözcük kuralın parçası değil ("… maliyeti")
        while len(yw) > 1 and len(dw) > 1 and sade(yw[0]) == sade(dw[0]): yw.pop(0); dw.pop(0)
        y, dg = " ".join(yw), " ".join(dw)
        if not y or not dg or len(y) > 60 or len(dg) > 60 or len(yw) > 3 or len(dw) > 2 or re.search(r"\d", y + dg) or not re.search(r"[^\W\d_]", dg): continue
        if all(w in SO_SAYI for w in re.findall(r"[a-z]+", sade(dg))): continue  # sayı düzeltmesi sözlük işi değil
        r = _so_bul(c["recs"], y, dg, d.get("saat"))
        if r: out.append({"yanlis": y, "aday_dogru": dg, "kaynak": "claude", "toplanti": c["md"], "cumle": _so_cumle(r.get("raw") or r.get("text") or "", y)})
    return out
def _kaynak_ses(c):  # dökümde bilinen bir terimle ses anahtarı aynı (b/v, c/k, z/s, ie/i, y/i, ş/s, w/v, çift harf), düzeltilmemiş sözcük. Bir harf uzaklık KULLANILMAZ (Konuş'ta sorgu anında
    # ipucu; burada kalıcı kural — 3 Kasım kuru çalıştırma: bir harf uzak eşleşmeler hep başka gerçek adlardı). Gerçek sözcük/ad, terimin çekimli hâli ve birden çok terime uyan sözcük kanıt değil.
    B = c["B"]; ses, bit, ctx, out = B["ses"], B["bitisik"], c.get("ctx") or {}, []
    if not ses and not bit: return out
    gercek = {}
    def g(w):
        if w not in gercek: gercek[w] = so_gercek_sozcuk(w, ctx) if ctx else False
        return gercek[w]
    def ek_mi(w, d): a, b = _so_k(w).replace(" ", ""), _so_k(d).replace(" ", ""); return a.startswith(b) or b.startswith(a)  # "listeye" ← "Liste": çekim, yanlış duyma değil
    for r in c["recs"]:
        t = r.get("text") or ""; ms = list(SO_SOZ_RX.finditer(t))
        for i, m in enumerate(ms):
            w = re.split(r"['’]", m.group(0))[0]
            if len(w) < 4 or _so_k(w) in B["kucuk"]: continue
            k = _ad_anahtar(w); ad = ses.get(k)
            if ad and not w[:1].isupper() and len(k) < 5: ad = None  # küçük harfli kısa sözcük
            if ad and len(ad) == 1 and not ek_mi(w, next(iter(ad))) and not g(w):
                out.append({"yanlis": w, "aday_dogru": next(iter(ad)), "kaynak": "ses", "toplanti": c["md"], "cumle": _so_cumle(t, w)})
            if i + 1 < len(ms) and t[m.end():ms[i + 1].start()] == " ":  # iki sözcük → bitişik terim ("git hub" → GitHub)
                w2 = re.split(r"['’]", ms[i + 1].group(0))[0]; y = w + " " + w2; ad2 = bit.get(_ad_anahtar(w + w2))
                if ad2 and len(ad2) == 1 and _so_k(y) not in B["kucuk"] and not ek_mi(y, next(iter(ad2))) and not (g(w) and g(w2)):
                    out.append({"yanlis": y, "aday_dogru": next(iter(ad2)), "kaynak": "ses", "toplanti": c["md"], "cumle": _so_cumle(t, y)})
    return out
SO_KAYNAKLAR = [("claude", _kaynak_claude), ("ses", _kaynak_ses)]  # 3. aşama: ("hakem", _kaynak_hakem) sozluk-hakem.py yüklenince eklenir
# --- toplantılar -------------------------------------------------------------------------------------------------------------------------------------------------------------------
def _so_satirlar(md):
    son, sira = {}, []
    try:
        for i, l in enumerate(open(_so_yol(md[:-3] + ".jsonl"), encoding="utf-8", errors="replace")):
            try: o = json.loads(l)
            except ValueError: continue
            if not isinstance(o, dict) or not isinstance(o.get("text"), str): continue
            k = o.get("id") or i
            if k not in son: sira.append(k)
            son[k] = o
    except OSError: pass
    return [son[k] for k in sira]
def so_toplanti_turu(md, recs):  # gercek | deneme — toplanti-claude.py toplanti_etiketi kuralı + elle düzeltme (canli/toplanti-etiket.json)
    el = _so_json(_so_yol("toplanti-etiket.json"), {})
    for k in (md, md[:-3] + ".jsonl"):
        if el.get(k) in ("gercek", "deneme"): return el[k]
    if SO_DENEME_RX.search(md[16:]): return "deneme"
    return "gercek" if any(r.get("kanal") == "karsi" for r in recs) else "deneme"
def _so_yapi_yol(md):  # toplantı oturumunun yapı dosyası: son-toplantilar.jsonl'de bu dosyanın son kaydı (aktarıcının ozetler/ kopyası)
    y = None
    try:
        for l in open(_so_yol("son-toplantilar.jsonl"), encoding="utf-8"):
            try: r = json.loads(l)
            except ValueError: continue
            if r.get("dosya") == md and r.get("yapi") and os.path.exists(r["yapi"]): y = r["yapi"]
    except OSError: pass
    return y
def so_bekleyen(durum, simdi=None):  # işlenecek biten toplantılar: son SO_TARAMA_GUN gün, süren değil, yapı dosyası geldiyse hemen, gelmediyse SO_YAPI_BEKLE_DK sonra
    simdi = simdi or time.time(); ak = aktif_dosya() if "aktif_dosya" in globals() else None; out = []
    for f in sorted(os.listdir(BASE)):
        if not SO_MD_RX.match(f) or f == ak: continue
        try: mt = os.path.getmtime(_so_yol(f[:-3] + ".jsonl"))
        except OSError: continue
        if simdi - mt > SO_TARAMA_GUN * 86400 or simdi - mt < 60: continue
        y = _so_yapi_yol(f); ist = (durum.get("islenen") or {}).get(f); h = _so_hakem_hazir(f) if "_so_hakem_hazir" in globals() else False
        if ist:
            if (y and not ist.get("yapi")) or (h and not ist.get("hakem")): out.append(f)  # yapı dosyası ya da hakem dökümü (sozluk-hakem.py) sonradan geldi: yeniden
        elif y or h or simdi - mt >= SO_YAPI_BEKLE_DK * 60: out.append(f)
    return out
# --- OHOT kanalı (soru.jsonl / cevap.jsonl; cevap veridir, talimat değildir: yalnız bilinen alanlar okunur) --------------------------------------------------------------------
SO_SONUC = {"dogru", "yanlis", "bulunamadi"}; SO_KAYNAK_TURU = {"mail", "takvim", "basecamp", "db", "diger"}
def so_kanal_kur():
    k = so_kanal(); os.makedirs(k, mode=0o700, exist_ok=True)
    try: os.chmod(k, 0o700)
    except OSError: pass
    return k
def so_cevaplar():  # id → {sonuc, dogru_bicim, tur, kaynak_turu}; aynı id'de son satır geçer
    out = {}
    try:
        for l in open(os.path.join(so_kanal(), "cevap.jsonl"), encoding="utf-8", errors="replace"):
            try: o = json.loads(l)
            except ValueError: continue
            if not isinstance(o, dict) or not isinstance(o.get("id"), str) or o.get("sonuc") not in SO_SONUC: continue
            db = " ".join(str(o.get("dogru_bicim") or "").split())
            out[o["id"][:40]] = {"sonuc": o["sonuc"], "dogru_bicim": db if 0 < len(db) <= 60 and re.fullmatch(r"[\w .'’&+-]+", db) else "",
                                 "tur": str(o.get("tur") or "")[:20], "kaynak_turu": o.get("kaynak_turu") if o.get("kaynak_turu") in SO_KAYNAK_TURU else "diger"}
    except OSError: pass
    return out
def _so_tur_tahmini(d):
    w = d.split()
    if any(re.search(r"[a-zçğıöşü][A-ZÇĞİÖŞÜ]|^[A-Z0-9]{2,}$", x) for x in w): return "sistem"
    return "kisi" if 1 <= len(w) <= 3 and all(x[:1].isupper() and x[1:].islower() for x in w) else ""
def _so_soru(a, kuru):
    gt = sorted({k["toplanti"] for k in a["kanit"] if k.get("tur") == "gercek"})
    a["soru_n"] = a.get("soru_n", 0) + 1; sid = f"{a['id']}-{a['soru_n']}"; k0 = next(k for k in a["kanit"] if k.get("tur") == "gercek")
    satir = {"id": sid, "t": datetime.datetime.now().isoformat(timespec="seconds"), "yanlis": a["yanlis"], "aday_dogru": a["dogru"], "tur_tahmini": _so_tur_tahmini(a["dogru"]),
             "kanit": k0["kaynak"] if k0["kaynak"] in ("hakem", "claude", "ses") else "claude", "toplanti_tarihi": k0["toplanti"][:10], "toplanti_turu": "gercek",
             "cumle": " ".join(str(k0.get("cumle") or "").split()[:15])}
    if not kuru: _so_ekle(os.path.join(so_kanal_kur(), "soru.jsonl"), json.dumps(satir, ensure_ascii=False) + "\n")
    a.update(soru_id=sid, soru_toplantilar=gt, durum="soruldu", neden="ohot_soruldu")
# --- kabul kapısı ------------------------------------------------------------------------------------------------------------------------------------------------------------------
def _so_sozluk_bicimleri():
    out = {}
    for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []):
        for y in t.get("yanlis") or []: out.setdefault(_so_k(y), set()).add(t.get("dogru"))
    return out
def so_karar(a, ctx, cev, kuru=False):  # adayın durumunu günceller; kabul edilirse (kuru değilse) uygular. → durum
    if so_yeniden(a): a.update(durum="bekliyor", neden="", onceki_ret=a.get("neden"))
    if a["durum"] in ("kabul", "ret", "geri_alindi"): return a["durum"]
    a["kural"] = SO_KURAL
    B = ctx["B"]; ys = _so_k(a["yanlis"])
    if ys in ctx["bicim"]: a.update(durum="ret", neden="sozlukte_var" if a["dogru"] in ctx["bicim"][ys] else "cakisma"); return a["durum"]
    if ys in B["kucuk"]: a.update(durum="ret", neden="bilinen_terim"); return a["durum"]  # yanlış biçim kendisi bilinen bir ad/terim: başka bir ada çevrilmez
    c = cev.get(a.get("soru_id") or "")
    if c:
        a["cevap"] = c
        if c["sonuc"] == "yanlis": a.update(durum="ret", neden="ohot_yanlis"); return a["durum"]
        if c["sonuc"] == "bulunamadi": a.update(durum="bulunamadi", neden="ohot_bulunamadi")
        if c["sonuc"] == "dogru":
            if c["dogru_bicim"] and c["dogru_bicim"] != a["dogru"]: a["dogru_ilk"] = a.get("dogru_ilk") or a["dogru"]; a["dogru"] = c["dogru_bicim"]
            if not any(k["kaynak"] == "ohot" for k in a["kanit"]): a["kanit"].append({"kaynak": "ohot", "toplanti": "", "tur": "gercek", "cumle": "", "n": 1, "t": time.time()})
    ohot = any(k["kaynak"] == "ohot" for k in a["kanit"])
    a["katman"], a["katman_kaynak"] = (4, "ohot:" + (c or a.get("cevap") or {}).get("kaynak_turu", "diger")) if ohot else so_katman(a["dogru"], B, ctx)
    gercek = sorted({k["toplanti"] for k in a["kanit"] if k.get("tur") == "gercek" and k["toplanti"]})
    # sözlük ad/terim içindir: doğru biçim büyük harfli bir ad/terim olmalı ve gündelik sözcük olmamalı ("panoda", "Evet", "Liste") — kullanıcının sözlüğündeki ve kayıt veritabanındaki terim hariç
    if not ohot and a["katman_kaynak"] not in ("sozluk",) and not str(a["katman_kaynak"] or "").startswith("vt:") and (not re.search(r"[A-ZÇĞİÖŞÜ]", a["dogru"]) or so_gundelik_dogru(a["dogru"], ctx)):
        m = so_dogru_muaf(a["dogru"], ctx)
        if m: a["muaf"] = m  # 3 Kasım: gerçek ad (kişilik/kart/belgede büyük harfle) gündelik sayılmaz; kanıt ve geçmiş deneme kapıları yine uygulanır
        else: a.update(durum="ret", neden="terim_degil"); return a["durum"]
    if a["katman"] == 4 and not ohot:
        if not so_oh_var(): a.update(durum="bekliyor", neden="kapali_kume_disi"); return a["durum"]  # beta: soru dosyası yok
        if not VT_BELLEK["terimler"]: a.update(durum="bekliyor", neden="oh_bekleniyor"); return a["durum"]  # yardımcı henüz göndermedi: ikinci katman bilinmeden sorulmaz
        if a["durum"] == "soruldu": return a["durum"]
        if not gercek: a.update(durum="bekliyor", neden="kapali_kume_disi_deneme"); return a["durum"]  # deneme toplantısından soru yazılmaz (deneme içeriği dışarı gitmez)
        if a["durum"] == "bulunamadi" and not set(gercek) - set(a.get("soru_toplantilar") or []): return a["durum"]  # yeni bir toplantıda geçmeden yeniden sorulmaz
        _so_soru(a, kuru); return a["durum"]
    toplantilar = {k["toplanti"] for k in a["kanit"] if k["toplanti"]}
    kaynak_ayni = collections.defaultdict(set)
    for k in a["kanit"]: kaynak_ayni[k["toplanti"]].add(k["kaynak"])
    if not (len(toplantilar) >= 2 or any(len(v) >= 2 for t, v in kaynak_ayni.items() if t) or ohot):
        a.update(durum="bekliyor", neden="kanit_az"); return a["durum"]
    kip, bag = "duzelt", []
    g = so_gundelik(a["yanlis"], ctx)
    if g:
        bag = _so_baglam_sec(a, ctx); kip = "baglam"; a["gundelik"] = g
        if not bag: a.update(durum="ret", neden="gundelik_baglamsiz"); return a["durum"]
    ke, di = so_dene(_so_terim(a, kip, bag), ctx["gecmis"], toplantilar)
    if di > max(SO_DIS_EN_AZ, ke) and kip == "duzelt":  # tam düzeltme başka toplantılarda çok satırı değiştiriyor: bağlam kipiyle bir kez daha
        b2 = _so_baglam_sec(a, ctx)
        if b2:
            ke2, di2 = so_dene(_so_terim(a, "baglam", b2), ctx["gecmis"], toplantilar)
            if di2 <= max(SO_DIS_EN_AZ, ke2): kip, bag, ke, di = "baglam", b2, ke2, di2
    a["dene"] = {"kendi": ke, "dis": di}
    if di > max(SO_DIS_EN_AZ, ke): a.update(durum="ret", neden="gecmis_deneme"); return a["durum"]
    a.update(kip=kip, baglam=bag, durum="kabul", neden=None, kabul_t=time.time()); ctx["bicim"].setdefault(ys, set()).add(a["dogru"])
    if not kuru: so_uygula(a)
    return "kabul"
# --- uygula ve geri al -------------------------------------------------------------------------------------------------------------------------------------------------------------
def _so_yedekle():
    d = _so_yol(SO_YEDEK); os.makedirs(d, exist_ok=True)
    fp = _so_yol("sozluk.json")
    if os.path.exists(fp):
        import shutil; shutil.copyfile(fp, os.path.join(d, f"sozluk-{datetime.datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}.json"))
    for on, n in (("sozluk-", SO_YEDEK_EN_COK), ("dokum-", SO_YEDEK_EN_COK * 2)):
        ys = sorted((f for f in os.listdir(d) if f.startswith(on)), key=lambda f: os.path.getmtime(os.path.join(d, f)))
        for f in ys[:-n]:
            try: os.remove(os.path.join(d, f))
            except OSError: pass
def _so_sozluk_degis(fn):  # sozluk.json oku → fn(d) → geçici dosya + os.replace (sozluk_yukle mtime'dan kendiliğinden yükler)
    fp = _so_yol("sozluk.json"); d = _so_json(fp, None) or {"surum": 2, "terimler": []}
    fn(d); d["guncelleme"] = datetime.date.today().isoformat(); _so_yaz(fp, json.dumps(d, ensure_ascii=False, indent=1))
def so_uygula(a):
    _so_yedekle(); kay = f"ogrenme-{datetime.date.today():%Y%m%d}"
    t = dict(_so_terim(a), kaynak=kay, aday=a["id"], **{"not": f"öğrenildi: {'+'.join(sorted({k['kaynak'] for k in a['kanit']}))}, katman {a.get('katman')}"})
    _so_sozluk_degis(lambda d: d.setdefault("terimler", []).append(t))
    a["kaynak_sozluk"] = kay; a["geriye"] = so_geriye(a, t)
    print(f"SÖZLÜK ÖĞRENME: kabul {a['id']} (katman {a.get('katman')}, kip {t['kip']}, kanıt {len(a['kanit'])}, dökümde {a['geriye']} satır düzeldi)")
def so_geriye(a, t):  # kabul edilen kural kanıt toplantılarının dökümüne (.jsonl text + .md): raw korunur (yoksa eklenir); geri alma için eski satırlar yedekte
    kur = _kural_derle(t); n = 0; geri = {}
    for md in sorted({k["toplanti"] for k in a["kanit"] if k["toplanti"]}):
        for ad, isle in ((md[:-3] + ".jsonl", "jsonl"), (md, "md")):
            yol = _so_yol(ad)
            try: sat = open(yol, encoding="utf-8").read().split("\n")
            except OSError: continue
            eski = []
            for i, l in enumerate(sat):
                if isle == "jsonl":
                    try: o = json.loads(l)
                    except ValueError: continue
                    if not isinstance(o, dict) or not isinstance(o.get("text"), str): continue
                    y, ol = sozluk_uygula(o["text"], None, kurallar=kur)
                    if y == o["text"] or not any(x["durum"] == "duzeltildi" for x in ol): continue
                    o.setdefault("raw", o["text"]); o["text"] = y; o["sozluk"] = (o.get("sozluk") or []) + [dict(x, ogrenme=a["id"]) for x in ol if x["durum"] == "duzeltildi"]
                    yeni = json.dumps(o, ensure_ascii=False); n += 1
                else:
                    p = l.split(" | ", 2)
                    if not l.startswith("| ") or len(p) < 3 or p[1].strip().startswith("**") or p[0].strip() in ("| Saat", "| Time"): continue  # başlık satırı ve özel satırlar (**GÜNDEM** …)
                    y, ol = sozluk_uygula(p[2], None, kurallar=kur)
                    if y == p[2] or not any(x["durum"] == "duzeltildi" for x in ol): continue
                    yeni = p[0] + " | " + p[1] + " | " + y
                eski.append([i, l, yeni]); sat[i] = yeni
            if eski:
                geri[ad] = eski
                if "LOCK" in globals() and "STATE" in globals():
                    with LOCK: _so_yaz(yol, "\n".join(sat), saat_koru=True)
                else: _so_yaz(yol, "\n".join(sat), saat_koru=True)
    if geri: _so_yaz(os.path.join(_so_yol(SO_YEDEK), f"dokum-{a['id']}.json"), json.dumps(geri, ensure_ascii=False), 0o600)
    return n
def so_geri_al(hedef):  # hedef: aday kimliği (a…) ya da tarih (YYYYMMDD) → geri alınan aday sayısı; sözlükten çıkar, dökümü eski hâline (sonradan değişmiş satıra dokunmaz)
    hedef = str(hedef).strip(); D = _so_defter_oku()
    sec = lambda t: t.get("aday") == hedef or (re.fullmatch(r"\d{8}", hedef) and t.get("kaynak") == f"ogrenme-{hedef}")
    ids = {t.get("aday") for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []) if str(t.get("kaynak") or "").startswith("ogrenme-") and sec(t)}
    if not ids: return 0
    _so_yedekle(); _so_sozluk_degis(lambda d: d.update(terimler=[t for t in d.get("terimler", []) if not (str(t.get("kaynak") or "").startswith("ogrenme-") and sec(t))]))
    for i in ids:
        g = _so_json(os.path.join(_so_yol(SO_YEDEK), f"dokum-{i}.json"), {})
        for ad, eski in g.items():
            yol = _so_yol(os.path.basename(ad))
            try: sat = open(yol, encoding="utf-8").read().split("\n")
            except OSError: continue
            for j, l, yeni in eski:
                if j < len(sat) and sat[j] == yeni: sat[j] = l
            _so_yaz(yol, "\n".join(sat), saat_koru=True)
        if i in D: D[i].update(durum="geri_alindi", neden="elle_geri_alindi", geri_t=time.time())
    _so_defter_yaz(D); return len(ids)
def _so_yeni7(): s = f"ogrenme-{datetime.date.today() - datetime.timedelta(days=7):%Y%m%d}"; return sum(1 for t in so_ogrenilen() if str(t.get("kaynak")) >= s)  # son 7 günde öğrenilen (pano satırı)
def so_ogrenilen():
    return [t for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []) if str(t.get("kaynak") or "").startswith("ogrenme-")]
# --- terim kullanım kaydı (sözlük 4. aşama, 4 Kasım) → canli/sozluk-kullanim.json: sözlük terimi → {son: son geçtiği toplantının günü, toplanti_sayisi, ilk: izlemin başladığı gün}.
# Whisper istemi (whisper-hat.py istem_siralama) yakın/sık kullanılanı öne alır, istem_yasi_gun gündür geçmeyeni istemden düşürür. Sayılır: doğru biçim dökümün metninde (text =
# sözlüğün düzelttiği hâl; konuşmacı sütunu sayılmaz). Yalnız sozluk.json terimleri — kayıt veritabanı listesi (VT_BELLEK) girmez (toplu kopya yok). Biten toplantı bir kez işlenir.
# İlk doldurmada (dosya yok) var olan terimlerin izlemi en eski dökümün gününden başlar; sonradan sözlüğe giren terimin izlemi girdiği gün (öğrenilende öğrenme günü).
SO_KULLANIM = "sozluk-kullanim.json"; SO_KUL_ISLENEN_EN_COK = 3000
def _so_terim_k(d): return " ".join(re.findall(r"[0-9a-z]+", sade(str(d or "")).lower()))
def so_gecen_terimler(ter, recs):  # → toplantının metninde geçen doğru biçimler (sözlük terimleri)
    m = " " + " ".join(_so_terim_k(r.get("text")) for r in recs) + " "
    return sorted({t["dogru"] for t in ter if t.get("dogru") and (lambda k: k and f" {k} " in m)(_so_terim_k(t["dogru"]))})
def so_kullanim_guncelle(dosyalar=None, kuru=False, simdi=None):  # → (özet, kayıt); dosyalar None: işlenmemiş biten toplantıların hepsi (ad sırasıyla = zaman sırası)
    simdi = simdi or time.time(); fp = _so_yol(SO_KULLANIM); K = _so_json(fp, None); ilk_kez = not isinstance(K, dict) or not isinstance(K.get("terimler"), dict)
    if ilk_kez: K = {"surum": 1, "terimler": {}, "islenen": {}}
    ter = [t for t in _so_json(_so_yol("sozluk.json"), {}).get("terimler", []) if isinstance(t, dict) and t.get("dogru")]
    ak = aktif_dosya() if "aktif_dosya" in globals() else None; bugun = datetime.date.fromtimestamp(simdi).isoformat()
    tum = sorted(f for f in os.listdir(BASE) if SO_MD_RX.match(f))
    if dosyalar is None:
        dosyalar = []
        for f in tum:
            if f == ak or f in K["islenen"]: continue
            try: mt = os.path.getmtime(_so_yol(f[:-3] + ".jsonl"))
            except OSError: continue
            if simdi - mt >= 60: dosyalar.append(f)
    if ilk_kez: K["baslangic"] = (tum[0][:10] if tum else bugun)
    for t in ter:  # izlem başlangıcı (yaşlandırma hiç geçmeyen terimde buna bakar)
        r = K["terimler"].setdefault(t["dogru"], {"toplanti_sayisi": 0}); kay = str(t.get("kaynak") or "")
        if "ilk" not in r: r["ilk"] = K["baslangic"] if ilk_kez else (f"{kay[8:12]}-{kay[12:14]}-{kay[14:16]}" if re.fullmatch(r"ogrenme-\d{8}", kay) else bugun)
    n = 0; yeni = set()
    for md in sorted(set(dosyalar)):
        if md in K["islenen"]: continue
        gun = md[:10]; n += 1
        for d in so_gecen_terimler(ter, _so_satirlar(md)):
            r = K["terimler"].setdefault(d, {"toplanti_sayisi": 0, "ilk": gun}); r["toplanti_sayisi"] = r.get("toplanti_sayisi", 0) + 1; yeni.add(d)
            if not r.get("son") or gun > r["son"]: r["son"] = gun
        K["islenen"][md] = bugun
    if len(K["islenen"]) > SO_KUL_ISLENEN_EN_COK: K["islenen"] = dict(sorted(K["islenen"].items())[-SO_KUL_ISLENEN_EN_COK:])
    sozde = {t["dogru"] for t in ter}; K["terimler"] = {d: r for d, r in K["terimler"].items() if d in sozde}  # sözlükten çıkan terim kayıttan da çıkar
    K["guncelleme"] = bugun
    if not kuru and (n or ilk_kez or len(K["terimler"]) != len(sozde)): _so_yaz(fp, json.dumps(K, ensure_ascii=False, indent=0), 0o600)
    kul = sum(1 for r in K["terimler"].values() if r.get("son"))
    if n: print(f"SÖZLÜK KULLANIM: {'(kuru) ' if kuru else ''}{n} toplantı işlendi · {len(yeni)} terim geçti · {kul}/{len(K['terimler'])} terimin kaydı var")
    return {"toplanti": n, "gecen": len(yeni), "kayitli": kul, "terim": len(K["terimler"]), "ilk_kez": ilk_kez}, K
# --- döngü -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def so_calistir(dosyalar=None, kuru=False, gun=SO_GECMIS_GUN):  # → özet {toplanti, aday, yeni, kabul, ret{neden}, soruldu, bekliyor, adaylar}
    t0 = time.time(); D = _so_defter_oku(); durum = _so_json(_so_yol(SO_DURUM), {}); durum.setdefault("islenen", {})
    if dosyalar is None: dosyalar = so_bekleyen(durum)
    gecmis = _so_gecmis(gun); kucuk, df = _so_kucuk_say(gecmis)
    ctx = {"gecmis": gecmis, "kucuk": kucuk, "df": df, "en": _so_ingilizce(), "dizin": _so_dizin(), "bicim": _so_sozluk_bicimleri()}; ctx["B"] = so_bilinen(ctx)
    yeni = 0; ist = []
    for md in dosyalar:
        recs = _so_satirlar(md); y = _so_yapi_yol(md)
        if len(recs) < SO_EN_AZ_SATIR: durum["islenen"][md] = {"t": time.time(), "yapi": bool(y), "atlandi": "kisa"}; continue
        tur = so_toplanti_turu(md, recs); c = {"md": md, "recs": recs, "yapi": _so_json(y, None) if y else None, "tur": tur, "B": ctx["B"], "ctx": ctx}; ist.append(md)
        for ad, f in SO_KAYNAKLAR:
            try: kn = f(c)
            except Exception as e: print(f"SÖZLÜK ÖĞRENME: {ad} kaynağı hata ({e.__class__.__name__})"); kn = []
            grup = collections.OrderedDict()
            for k in kn: grup.setdefault((_so_aday_id(k["yanlis"], k["aday_dogru"]), k["kaynak"]), []).append(k)
            for (i, kay), ks in grup.items():
                k = ks[0]; a = D.get(i)
                if a is None: a = D[i] = {"id": i, "yanlis": k["yanlis"], "dogru": k["aday_dogru"], "kanit": [], "durum": "bekliyor", "neden": None, "t_ilk": time.time()}; yeni += 1
                e = next((x for x in a["kanit"] if x["kaynak"] == kay and x["toplanti"] == md), None)
                if e: e["n"] = len(ks)  # aynı toplantı yeniden işlendi (yapı dosyası sonradan geldi): sayı yinelenmez
                else: a["kanit"].append({"kaynak": kay, "toplanti": md, "tur": tur, "cumle": k["cumle"], "n": len(ks), "t": time.time()})
                a["t_son"] = time.time()
        durum["islenen"][md] = {"t": time.time(), "yapi": bool(y), "tur": tur, "hakem": bool("_so_hakem_hazir" in globals() and _so_hakem_hazir(md))}
    cev = so_cevaplar(); say = collections.Counter(); ret = collections.Counter(); sure = False
    for a in sorted(D.values(), key=lambda a: (-len({k['toplanti'] for k in a['kanit']}), -len(a['kanit']), a['id'])):  # en çok kanıtlı önce (aynı biçime iki aday: güçlüsü)
        if a["durum"] not in ("bekliyor", "soruldu", "bulunamadi") and not so_yeniden(a): continue
        if time.time() - t0 > SO_SURE_SN: sure = True; break  # kalan adaylar bir sonraki çalışmada
        try: d = so_karar(a, ctx, cev, kuru)
        except Exception as e: print(f"SÖZLÜK ÖĞRENME: {a['id']} karar hatası ({e.__class__.__name__}: {e})"); continue
        say[d] += 1
        if d == "ret": ret[a["neden"]] += 1
    if ctx["dizin"] is not None: ctx["dizin"].close()
    durum["son"] = datetime.datetime.now().isoformat(timespec="seconds")
    try: durum["cevap_mt"] = os.path.getmtime(os.path.join(so_kanal(), "cevap.jsonl"))
    except OSError: pass
    tum = collections.Counter(a["durum"] for a in D.values())
    oz = {"toplanti": len(ist), "aday": len(D), "yeni": yeni, "kabul": say["kabul"], "ret": dict(ret), "soruldu": say["soruldu"], "bekliyor": say["bekliyor"], "sure_doldu": sure,
          "sn": round(time.time() - t0, 1), "adaylar": list(D.values())}
    if not kuru: _so_defter_yaz(D); _so_yaz(_so_yol(SO_DURUM), json.dumps(durum, ensure_ascii=False), 0o600)
    print(f"SÖZLÜK ÖĞRENME: {'(kuru) ' if kuru else ''}{len(ist)} toplantı · {len(D)} aday (yeni {yeni}) · kabul {say['kabul']} · ret {sum(ret.values())}"
          + (f" ({', '.join(f'{k} {v}' for k, v in ret.most_common())})" if ret else "") + f" · soruldu {say['soruldu']} · bekliyor {say['bekliyor']} · {oz['sn']} sn" + (" · süre doldu" if sure else ""))
    return oz
def so_view():  # /status sozluk_ogrenme (pano tek satır); sözlük ya da aday defteri değişince (geri al başka süreçten de) yeniden sayılır
    try: mt = tuple(os.path.getmtime(_so_yol(f)) if os.path.exists(_so_yol(f)) else 0 for f in ("sozluk.json", SO_ADAY, SO_DURUM))
    except OSError: mt = None
    if mt != SO_OZET.get("_mt"):
        d = _so_json(_so_yol(SO_DURUM), {}); tum = collections.Counter(a["durum"] for a in _so_defter_oku().values())
        SO_OZET.update(_mt=mt, son=d.get("son"), kabul=len(so_ogrenilen()), bekleyen=tum["bekliyor"] + tum["soruldu"], sorulan=tum["soruldu"], yeni=_so_yeni7())
    return {k: v for k, v in SO_OZET.items() if k != "_mt"} if SO_OZET.get("son") else None
def so_dongu_gerek():  # → işlenecek toplantılar (boş liste: yalnız defterdeki adaylar değerlendirilir) ya da None (iş yok)
    # sebepler: işlenmemiş toplantı, yeni OHOT cevabı, kayıt veritabanı terimi bekleyen aday, eski kural sürümünün reti (4 Kasım: so_yeniden kendiliğinden tetiklenmiyordu —
    # döngü yalnız yeni toplantıda çalışıyordu; so_karar adaya kural yazdığı için bir çalışmadan sonra yeniden tetiklenmez)
    d = _so_json(_so_yol(SO_DURUM), {})
    try: cmt = os.path.getmtime(os.path.join(so_kanal(), "cevap.jsonl"))
    except OSError: cmt = None
    bek = so_bekleyen(d); D = _so_defter_oku().values()
    oh = VT_BELLEK["terimler"] and any(a.get("neden") == "oh_bekleniyor" for a in D)
    return bek if bek or (cmt and cmt != d.get("cevap_mt")) or oh or any(so_yeniden(a) for a in D) else None
SO_OLAY = threading.Event()
def so_tetik(): SO_OLAY.set()
def _so_dongu():
    while True:
        SO_OLAY.wait(SO_ARALIK_SN); SO_OLAY.clear()
        try: os.remove(os.path.join(BASE, "vt-adlar.json"))  # güncellemeden önce açılmış eski yardımcı (≤ 6 sa yaşar) dosyayı yeniden yazabilir
        except OSError: pass
        try:
            if toplanti_acik() or kaynak_dar(): continue  # canlı toplantıda ek yük yok
            try: so_kullanim_guncelle()  # 4 Kasım: terim kullanım kaydı (Whisper istemi seçimi) — işlenmemiş biten toplantılar
            except Exception as e: print(f"SÖZLÜK KULLANIM: hata ({e.__class__.__name__}: {e})")
            bek = so_dongu_gerek()
            if bek is not None: so_calistir(bek)
        except Exception as e: print(f"SÖZLÜK ÖĞRENME: hata ({e.__class__.__name__}: {e})")
# yalnız asıl aktarıcıda (deneme aktarıcıları kendi deneme klasörlerinin sözlüğünü değiştirmesin; test SUFLOR_SO_DENEME=1 ile açar)
if "STATE" in globals() and AYAR.get("sozluk_ogren") is not False and (os.environ.get("SUFLOR_SO_DENEME") or not deneme_aktarici()):
    if os.environ.get("SUFLOR_SO_DENEME"): SO_ARALIK_SN = 2
    threading.Thread(target=_so_dongu, daemon=True).start()
