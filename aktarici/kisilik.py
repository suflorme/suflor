# Suflor.me aktarıcı bölümü: Kişilik (v0.53.0). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("kisilik")). import etme. Python 3.9 uyumlu.
# Ayar "kisilik": kişilik dosyasının yolu (~ açılır; launchd Masaüstü'nü okuyamadığı için Application Support altında). Yoksa ya da okunamazsa bugünkü nötr davranış
# sürer (açık depo ve beta). Dosya: başta iki "---" satırı arasında ayar satırları, ardından Claude'a giden kişilik metni (Konuş isteminin sonuna eklenir; biçim
# kuralları önce gelir). Ayar satırları (hepsi isteğe bağlı, ad dışında):
#   ad: görünen ve okunan ad (panoda konuşma etiketi)        hitap: kullanıcının seslenme adları ve Whisper yazımları, virgülle (ayar hitap_ad listesi ezer)
#   okunus: adın Türkçe okunuşu                              tanitim: toplantıya söyle'de ilk okumadaki tanıtım cümlesi (ayar tanitim ezer)
#   selam: kişilik açıldıktan sonraki ilk konuşmada bir kez  telaffuz: SÖZCÜK=okunuş; SÖZCÜK2=okunuş2
# Kişiliğe özgü adlar ve metinler yalnız bu dosyada ve kullanıcının ayarında durur; kodda sabit ad yok (açık depoda örnek: sablon/kisilik-ornek.md).
# v0.61.0: iki kişilik. Ayar "kisilik_toplanti_disi": ikinci dosya — toplantı yokken o konuşur; toplantıda "kisilik" (ilk dosya). Kullanıcı cümleye birinin
# adıyla başlarsa ("<Ad>, …") o soru ve ardından KISILIK_SURE_SN içindeki adsız sorular o kişilikle cevaplanır. Ek ayar satırı: hitap_bicimi: sen (varsayılan siz).
# S94 (kullanıcı, 19 Ekim): toplantıda tek kural — "<Ad>, …" diye seslenilen kişilik toplantıya herkesin duyacağı şekilde cevap verir (hangisi olursa olsun);
# yalnız kullanıcıya cevap tek yoldan: Konuş düğmesi. Kişilik, kullanıcı onu toplantıda ilk kez çağırınca "katılır"; sonra karşı taraf da ona adıyla sorabilir.
# v0.71.0: ses: piper | <Mac ses adı> ve hiz: 1,15 (çarpan) — kişiliğin cevapları bu sesle okunur (iki kişilik ayrı duyulsun). Mac'in sistem (Siri) sesi say -r'yi
# yok sayar (ölçüm 17 Ekim: -r 180/220 aynı süre); hız yalnız Piper'da ve adı verilen Mac sesinde (ör. Yelda) işler. Toplantıya okuma (BlackHole) bundan etkilenmez.
# S93: yerel_ses: pocket:<model>:<ses> — kişiliğin Gemini dışındaki sesi (S92'den beri toplantı dışı ve kulağa okumalar yerel); Pocket'ta hız ayarı yok.
KISILIK_SURE_SN = 180
_KIS = {"yol": None, "mt": None, "v": None, "uyari": None}  # geriye uyum: tek kişilikte eski alanlar (konus_istem kisilik_mt)
_KIS_D = {}  # yol → {"mt", "v", "uyari"}
_KSEC = {"ad": None, "t": 0.0}
def _kisilik_oku(yol, rol):
    d = _KIS_D.setdefault(yol, {"mt": None, "v": None, "uyari": None})
    try: mt = os.path.getmtime(yol)
    except OSError:
        if d["uyari"] != yol: d["uyari"] = yol; print(f"KİŞİLİK: okunamadı ({os.path.basename(yol)}) — nötr davranış")
        d.update(mt=None, v=None); return None
    if d["mt"] == mt: return d["v"]
    v = None
    try:
        s = open(yol, encoding="utf-8").read()
        m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n?(.*)\Z", s, re.S)
        v = {"ad": None, "hitap": [], "okunus": None, "tanitim": None, "selam": None, "telaffuz": {}, "bicim": "siz", "ses": None, "yerel_ses": None, "yerel_ses_en": None, "hiz": None, "ses_uslup": None, "ses_etiket": False, "gerginlik_tonu": False, "kdili": False, "rol": rol, "metin": (m.group(2) if m else s).strip()}
        for sat in (m.group(1).splitlines() if m else []):
            k, _, d_ = sat.partition(":"); k = k.strip().lower(); d_ = d_.strip()
            if k in ("ad", "okunus", "tanitim", "selam"): v[k] = d_ or None
            elif k == "hitap": v["hitap"] = [x.strip() for x in d_.split(",") if x.strip()]
            elif k == "hitap_bicimi": v["bicim"] = "sen" if d_.lower() == "sen" else "siz"
            elif k == "konusma_dili": v["kdili"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.73.0
            elif k == "ses_uslup": v["ses_uslup"] = d_[:400] or None  # v0.79.0: Gemini sesine ton yönergesi ("nüktedan, dostça…")
            elif k == "ses_etiket": v["ses_etiket"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.79.0: <chuckle> gibi sözsüz ses etiketleri (yalnız Gemini)
            elif k == "gerginlik_tonu": v["gerginlik_tonu"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.80.0: toplantı gerginliğine göre ton (yalnız Gemini sesinde)
            elif k == "ses": v["ses"] = d_ or None  # v0.71.0: "piper" ya da Mac ses adı (say -v); yoksa ayardaki ses
            elif k == "yerel_ses_en": v["yerel_ses_en"] = d_ or None  # v0.101.3: İngilizce cümlelerin yerel sesi, ör. pocket:en:michael
            elif k == "yerel_ses": v["yerel_ses"] = d_ or None  # S93: Gemini dışındaki (yerel) ses, ör. pocket:alperiox:female_2; Gemini toplantıya ayrıldığı için (S92) ayrı
            elif k == "hiz":
                try: v["hiz"] = max(0.7, min(1.6, float(d_.replace(",", "."))))
                except ValueError: pass
            elif k == "telaffuz": v["telaffuz"] = {a.strip(): b.strip() for a, _, b in (x.partition("=") for x in d_.split(";")) if a.strip() and b.strip()}
        if not v["ad"] or not v["metin"]: print("KİŞİLİK: okunamadı (ad ya da metin yok) — nötr davranış"); v = None
    except OSError as e: print(f"KİŞİLİK: okunamadı ({e.__class__.__name__}) — nötr davranış"); v = None
    if v:
        if rol == "toplanti":  # ayardaki hitap_ad/tanitim ilk (toplantı) kişiliğe
            if isinstance(AYAR.get("hitap_ad"), list) and AYAR["hitap_ad"]: v["hitap"] = [str(x).strip() for x in AYAR["hitap_ad"] if str(x).strip()]
            if AYAR.get("tanitim"): v["tanitim"] = str(AYAR["tanitim"]).strip()
        if not v["hitap"]: v["hitap"] = [v["ad"]]
        print(f"KİŞİLİK: {v['ad']} ({rol}) · {len(v['metin'])} karakter · hitap {', '.join(v['hitap'][:8])}")
    d.update(mt=mt, v=v, uyari=None); return v
def kisilikler():  # → yüklü kişilikler, önce toplantı kişiliği; aynı ad iki kez gelmez
    out = []
    for ayar, rol in (("kisilik", "toplanti"), ("kisilik_toplanti_disi", "disi")):
        yol = os.path.expanduser(str(AYAR.get(ayar) or "").strip())
        v = _kisilik_oku(yol, rol) if yol else None
        if v and all(x["ad"] != v["ad"] for x in out): out.append(v)
    t = out[0] if out and out[0]["rol"] == "toplanti" else None
    _KIS.update(yol=None, mt=(tuple(_KIS_D[os.path.expanduser(str(AYAR.get(a) or "").strip())]["mt"] for a in ("kisilik", "kisilik_toplanti_disi") if str(AYAR.get(a) or "").strip()) if out else None), v=t)
    return out
def kisilik_varsayilan(ks=None):  # toplantıda toplantı kişiliği, değilse toplantı dışı kişilik (yoksa öteki)
    ks = kisilikler() if ks is None else ks
    if not ks: return None
    istenen = "toplanti" if toplanti_var() else "disi"
    return next((k for k in ks if k["rol"] == istenen), ks[0])
def kisilik(ad=None):  # → etkin kişilik {ad, hitap, okunus, tanitim, selam, telaffuz, bicim, rol, metin} ya da None (nötr)
    ks = kisilikler()
    if not ks: return None
    if ad: return next((k for k in ks if k["ad"] == ad), None)
    if _KSEC["ad"] and time.time() - _KSEC["t"] < KISILIK_SURE_SN:
        k = next((k for k in ks if k["ad"] == _KSEC["ad"]), None)
        if k: return k
    return kisilik_varsayilan(ks)
def kisilik_sec(ad):  # bu soru (ve KISILIK_SURE_SN içindeki adsız sorular) bu kişilikle; None → varsayılana dön
    onceki = _KSEC["ad"] if time.time() - _KSEC["t"] < KISILIK_SURE_SN else None
    _KSEC.update(ad=ad, t=time.time() if ad else 0.0)
    if ad and ad != onceki: print(f"KİŞİLİK: bu soru {ad} ile (adıyla seslenildi)")
# 19 Ekim test toplantısı: "<toplantı kişiliği> ile ilgili problem neydi?" (öteki kişiliğe soru, ondan söz) seslenme sayıldı → ad + söz etme sözcüğü ya da
# soru eki ("ile", "hakkında", "için", "gibi", "ve", "de", "mi" …) seslenme değil; kesmeli ek ("<Ad>'in") de değil. sozluk.py'deki kalıp da bunu kullanır.
# v0.101.1 (hitap ölçümü, kullanıcının sesiyle 21 Ekim): addan önce giriş sözü ya da selam ("Tamam, <ad>, not al", "Selam <ad>, yarına bakar mısın?") —
# Whisper "Tamam"dan sonra virgül yazıyor, eski kural adı yalnız cümle başında/noktadan sonra arıyordu (14 okumanın 12'si kaçtı). İki yer aynı tanımı kullanır.
KISILIK_GIRIS = r"(?:tamam|peki|evet|şimdi|hadi|hey|günaydın|tünaydın|merhaba|selamlar|selam|iyi akşamlar|iyi günler|okay|ok|hi|hello|good morning)"
KISILIK_SELAM = r"(?:günaydın|tünaydın|merhaba|selamlar|selam|iyi akşamlar|iyi günler|hi|hello|good morning)"
KISILIK_SOZ_ETME = r"(?:ile|hakkında\w*|için|gibi|ve|veya|ya|de|da|ki|mi|mı|mu|mü|kadar|konusunda|tarafından|yüzünden|sayesinde)\b"
# S94 (19 Ekim: "<Ad> gelsin" virgülsüz ve sorusuz kaçtı): noktalamasız ve sorusuz cümle yalnız istek içeriyorsa seslenme — 3. kişi emir (-sın/-sin),
# "…ır mısın / …ebilir misin" ya da istek fiili. "<Ad> markasının yeni ürünü güzel" gibi addan söz eden cümle seslenme değil.
KISILIK_ISTEK = (r"(?:\b(?:lütfen|söyle|anlat|özetle|açıkla|bak|kontrol et|devam et|başla|yönet|katıl|gel|dur|sus|cevap ver|yardım et|hatırlat|bul|ara|not al|kaydet|oku|"
                 r"tell|say|explain|summari[sz]e|check|join|stop|help)\b|\w+(?:s[ıiuü]n|s[ıiuü]nl[ae]r)\b|\w+[ıiuüae]r\s+m[ıiuü]s[ıiuü]n|\w+[ae]bilir\s+m[ıi]s[ıi]n)")
def kisilik_hitap_bul(metin):  # cümle başında bir kişiliğin adı → (kişilik, adsız metin) ya da (None, metin)
    ks = kisilikler()
    if len(ks) < 2 or not metin: return None, metin
    for k in sorted(ks, key=lambda k: -max(len(a) for a in k["hitap"])):
        m = re.match(r"\W*(" + KISILIK_GIRIS + r"\W+)?(?:" + "|".join(re.escape(a) for a in sorted(k["hitap"], key=len, reverse=True)) + r")(?:(?:'\w+)?\s*[,:.!]\s*|\s+(?!" + KISILIK_SOZ_ETME + r")(?=\w))", metin, re.I)  # 19 Ekim: ad + söz etme ("ile ilgili") seslenme değil
        if m and metin[m.end():].strip(): return k, metin[m.end():].strip()
        if m and m.group(1) and re.match(KISILIK_SELAM + r"\W*$", m.group(1), re.I): return k, metin.strip()  # yalnız selam ("Günaydın <ad>."): selamın kendisi soru
    return None, metin
# --- S94: toplantıda asistanlar — katılma durumu (toplantı başına) ---------------------------------------------------------------------
_KATIL = {"toplanti": None, "adlar": []}
def asistan_toplanti(): return AYAR.get("toplantiya_ses") is True and AYAR.get("konusma", True) is not False and not ("gizli_acik" in globals() and gizli_acik())  # tek anahtar: "Asistanlar toplantıda konuşsun"; v0.89.0: gizli toplantıda kapalı
def asistan_adlari(): ks = kisilikler(); return [k["ad"] for k in ks] if ks else ["Suflor"]  # kişilik yoksa (nötr kurulum) asistanın adı Suflor
def asistan_buyuk(): return asistan_ad().replace("i", "İ").replace("ı", "I").upper()  # dökümdeki kart etiketi (Türkçe büyük harf)
def asistan_ad():  # S133: kullanıcıya görünen tek muhatap — toplantı kişiliğinin adı (yoksa ilk kişilik, kişiliksiz kurulumda Suflor)
    ks = kisilikler(); return next((k["ad"] for k in ks if k["rol"] == "toplanti"), ks[0]["ad"] if ks else "Suflor")
def asistan_katilan():
    if not toplanti_var(): return []
    a = STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
    if _KATIL["toplanti"] != a: _KATIL.update(toplanti=a, adlar=[])
    return list(_KATIL["adlar"])
def asistan_katil(ad):
    if ad and ad not in asistan_katilan(): _KATIL["adlar"].append(ad); print(f"ASİSTAN: {ad} toplantıya katıldı (kullanıcı adıyla çağırdı)")
def asistan_view():  # /status konus.asistan — pano: "<adlar> dinliyor" / "<ad> toplantıda"
    if not toplanti_var(): return None
    return {"acik": asistan_toplanti(), "adlar": asistan_adlari(), "katilan": asistan_katilan()}
def kisilik_ad(): k = kisilik(); return k["ad"] if k else None
def kis_t(notr, kisilikli):  # sabit sesli cümle: kişilik açıkken "siz"li sürümü (Türkçe arayüzde; kişilik "sen" diyorsa nötr); İngilizce ayrı _t ile
    k = kisilik(); return kisilikli if k and k.get("bicim") != "sen" and ARAYUZ_DILI == "tr" else notr
_KIS_TANIT = {"yuklendi": False, "adlar": set()}
def kisilik_selam():  # kişilik açıldıktan sonraki ilk konuşmada bir kez (canli/kisilik-tanitim.json: tanıtılan adlar)
    k = kisilik()
    if not k or not k.get("selam"): return None
    yol = os.path.join(BASE, "kisilik-tanitim.json")
    if not _KIS_TANIT["yuklendi"]:
        _KIS_TANIT["yuklendi"] = True
        try: _KIS_TANIT["adlar"] = set(json.load(open(yol, encoding="utf-8")).get("adlar") or [])
        except (OSError, ValueError, AttributeError): pass
    if k["ad"] in _KIS_TANIT["adlar"]: return None
    _KIS_TANIT["adlar"].add(k["ad"])
    try:
        with open(yol + ".tmp", "w", encoding="utf-8") as f: json.dump({"adlar": sorted(_KIS_TANIT["adlar"])}, f, ensure_ascii=False)
        os.replace(yol + ".tmp", yol)
    except OSError: pass
    print(f"KİŞİLİK: {k['ad']} kendini tanıttı (ilk konuşma)"); return k["selam"]
def kisilik_telaffuz(metin):  # okunacak metinde ad → okunuş ve dosyadaki telaffuz satırları (Mac sesi ve Piper)
    ks = kisilikler()
    if not ks or not metin: return metin
    es = {}
    for k in ks:  # iki kişiliğin telaffuzu da (biri ötekinin adını söyleyebilir)
        for a, b in k["telaffuz"].items(): es.setdefault(a, b)
        es.setdefault(k["ad"], k.get("okunus") or k["ad"])
    for a, b in es.items():
        if a != b: metin = re.sub(r"(?<!\w)" + re.escape(a) + r"(?!\w)", b, metin)
    return metin
# v0.73.0 (kullanıcı, 17 Ekim): konuşma dili — kişilik dosyasında "konusma_dili: evet" ise o kişiliğin OKUNAN cümlesinde 1. kişi kip ekleri
# günlük söylenişe döner (okuyacağım → okuyacam, bakıyorum → bakıyom). v0.80.9 (kullanıcı, 19 Ekim): 2. kişi "-yon" (bakıyon, gidiyon) kulağa kaba geldi, kaldırıldı;
# "bakıyorsun", "geliyor musun" olduğu gibi okunur. Claude bu yazımı istemle de kullanmadı (gerçek deneme 3/3).
# Yazılı kısım (pano) ve toplantıya okunan metin değişmez. Gelecek zaman ortacı ("okuyacağım kitap") bozulmasın diye -acağım yalnız noktalama/satır sonu ya da
# bağlaçtan önce döner; -yorum fiilden başka sözcükte geçmez ("yorum" tek başına eşleşmez: önünde ünlü + y gerekir).
_KD_SON = r"(?=\s*(?:[.,!?;:…]|$|\s(?:ama|ve|ki|de|da|sonra|şimdi|hemen|yani|zaten|bence|tamam)\b))"
_KD_KURAL = [
    (re.compile(r"\b(\w+?)(a|e)ca(?:ğ|g)ı(m|z)\b" + _KD_SON, re.I), lambda m: m.group(1) + m.group(2) + "ca" + m.group(3)),   # okuyacağım → okuyacam, yapacağız → yapacaz
    (re.compile(r"\b(\w+?)(e)ce(?:ğ|g)i(m|z)\b" + _KD_SON, re.I), lambda m: m.group(1) + m.group(2) + "ce" + m.group(3)),     # gideceğim → gidecem
    (re.compile(r"\b(\w+[ıiuü])yor\s+muyum\b", re.I), lambda m: m.group(1) + "yom mu"),                                       # anlıyor muyum → anlıyom mu
    (re.compile(r"\b(\w+[ıiuü])yorum\b", re.I), lambda m: m.group(1) + "yom"),                                                   # bakıyorum → bakıyom
    (re.compile(r"\b(\w+[ıiuü])yoruz\b", re.I), lambda m: m.group(1) + "yoz"),                                                   # gidiyoruz → gidiyoz
]
def konusma_dili(metin, k=None):  # okunacak cümle → kişilik konuşma dili istiyorsa günlük söyleniş
    k = k or kisilik()
    if not k or not k.get("kdili") or not metin or ARAYUZ_DILI != "tr": return metin
    for rx, f in _KD_KURAL:
        metin = rx.sub(f, metin)
    return metin
