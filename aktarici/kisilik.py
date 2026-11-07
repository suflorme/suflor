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
# v0.71.0: ses: <Mac ses adı> ve hiz: 1,15 (çarpan) — kişiliğin cevapları bu sesle okunur (iki kişilik ayrı duyulsun). Mac'in sistem (Siri) sesi say -r'yi
# yok sayar (ölçüm 17 Ekim: -r 180/220 aynı süre); hız yalnız adı verilen Mac sesinde (ör. Yelda) işler. Toplantıya okuma (BlackHole) bundan etkilenmez.
# v0.122.1 (kullanıcı, 23 Ekim: "sohbeti hep takvime bağlıyor"): takvim: soruya — Konuş bağlamına takvim ve "Sıradaki toplantı" bloğu yalnız soru zamanla,
# takvimle ya da toplantıyla ilgiliyse ya da toplantı KISILIK_TAKVIM_YAKIN_DK içindeyse girer (kisilik_takvim_gerek). Yoksa (varsayılan "her") her soruda girer.
# S93: yerel_ses: pocket:<model>:<ses> — kişiliğin Gemini dışındaki sesi (S92'den beri toplantı dışı ve kulağa okumalar yerel); Pocket'ta hız ayarı yok.
# 3 Kasım: gorev_cikar: evet — kişisel asistan görev çıkarır (talimat.py gorev_*): toplantıda hitapsız iş sözü ve sahipsiz iş onay kartına öneri olur, Konuş'ta
# konuşmadan çıkan iş "ekleyeyim mi?" diye sunulur. Satır yoksa (kurumsal asistan) iş yalnız adıyla seslenilince ya da açık istekle alınır.
KISILIK_SURE_SN = 180
_KIS = {"yol": None, "mt": None, "v": None, "uyari": None}  # geriye uyum: tek kişilikte eski alanlar (konus_istem kisilik_mt)
_KIS_D = {}  # yol → {"mt", "v", "uyari"}
_KSEC = {"ad": None, "t": 0.0}
HITAP_GUNDELIK = {"oh", "ah", "eh", "ha", "hı", "hm", "hmm", "evet", "hayır", "hayir", "tamam", "peki", "bak", "abi", "hocam", "şey", "sey", "yani", "ok", "okay", "yes", "no", "hey", "merhaba", "selam"}
def hitap_suz(liste, ad=None):  # 30 Ekim: listede "Oh, <ad>" virgülle bölünüp tek başına "Oh" hitap oldu, kullanıcının "oh"u asistana soru gitti. 3 harften kısa ya da gündelik sözcük atılır
    kalan, atilan = [], []
    for x in liste:
        if x.lower() == str(ad or "").lower() or (len(re.sub(r"\W", "", x)) >= 3 and x.lower() not in HITAP_GUNDELIK): kalan.append(x)
        else: atilan.append(x)
    if atilan: print(f"KİŞİLİK: seslenme listesinden atıldı (kısa ya da gündelik sözcük): {', '.join(atilan)}")
    return kalan
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
        v = {"ad": None, "gorunen_ad": None, "hitap": [], "okunus": None, "tanitim": None, "selam": None, "telaffuz": {}, "bicim": "siz", "ses": None, "yerel_ses": None, "yerel_ses_en": None, "hiz": None, "ses_uslup": None, "ses_uslup_en": None, "ses_etiket": False, "gerginlik_tonu": False, "gorev_cikar": False, "takvim": "her", "kdili": False, "rol": rol, "metin": (m.group(2) if m else s).strip()}
        for sat in (m.group(1).splitlines() if m else []):
            k, _, d_ = sat.partition(":"); k = k.strip().lower(); d_ = d_.strip()
            if k in ("ad", "okunus", "tanitim", "selam"): v[k] = d_ or None
            elif k == "gorunen_ad": v[k] = d_[:40] or None  # v0.157.0: kullanıcıya görünen ad (pano, döküm, hata metni); yoksa ad. İç ad (dosya, ayar, kayıt anahtarı) değişmez
            elif k == "hitap": v["hitap"] = [x.strip() for x in d_.split(",") if x.strip()]
            elif k == "hitap_bicimi": v["bicim"] = "sen" if d_.lower() == "sen" else "siz"
            elif k == "konusma_dili": v["kdili"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.73.0
            elif k == "ses_uslup": v["ses_uslup"] = d_[:400] or None  # v0.79.0: Gemini sesine ton yönergesi ("nüktedan, dostça…")
            elif k == "ses_uslup_en": v["ses_uslup_en"] = d_[:400] or None  # v0.127.0: Gemini'ye giden İngilizce yönerge (Türkçesi metinle karışıp sesli okunuyordu)
            elif k == "ses_etiket": v["ses_etiket"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.79.0: <chuckle> gibi sözsüz ses etiketleri (yalnız Gemini)
            elif k == "gerginlik_tonu": v["gerginlik_tonu"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # v0.80.0: toplantı gerginliğine göre ton (yalnız Gemini sesinde)
            elif k == "gorev_cikar": v["gorev_cikar"] = d_.lower() in ("evet", "true", "1", "açık", "acik")  # 3 Kasım: kişisel asistan hitapsız iş sözünden ve sahipsiz işten öneri çıkarır (talimat.py gorev_*)
            elif k == "takvim": v["takvim"] = "soruya" if d_.lower() in ("soruya", "soruda", "gerekince") else "her"  # v0.122.1: takvim bağlamı yalnız ilgili soruda
            elif k == "ses": v["ses"] = d_ or None  # v0.71.0: Mac ses adı (say -v); yoksa ayardaki ses
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
        v["hitap"] = hitap_suz(v["hitap"], v["ad"])
        if not v["hitap"]: v["hitap"] = [v["ad"]]
        for x in (v["gorunen_ad"],):  # görünen ad da hitap sayılır
            if x and x.lower() not in {h.lower() for h in v["hitap"]}: v["hitap"].append(x)
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
def kisilik_sec(ad, neden="adıyla seslenildi"):  # bu soru (ve KISILIK_SURE_SN içindeki adsız sorular) bu kişilikle; None → varsayılana dön. neden: günlükte (v0.125.2)
    onceki = _KSEC["ad"] if time.time() - _KSEC["t"] < KISILIK_SURE_SN else None
    _KSEC.update(ad=ad, t=time.time() if ad else 0.0)
    if ad and ad != onceki: print(f"KİŞİLİK: bu soru {ad} ile ({neden})")
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
        if re.match(r"\W*(?:" + "|".join(re.escape(a) for a in k["hitap"]) + r")\s*[?!.]*\s*$", metin, re.I): return k, metin.strip()  # 23 Ekim: tek başına ad ("<Ad>?") o kişiliği çağırır
    return None, metin
# --- S94: toplantıda asistanlar — katılma durumu (toplantı başına) ---------------------------------------------------------------------
_KATIL = {"toplanti": None, "adlar": []}
def asistan_toplanti(): return AYAR.get("toplantiya_ses") is True and AYAR.get("konusma", True) is not False and not ("gizli_acik" in globals() and gizli_acik())  # tek anahtar: "Asistanlar toplantıda konuşsun"; v0.89.0: gizli toplantıda kapalı
def kisilik_gorunen(k): return (k or {}).get("gorunen_ad") or (k or {}).get("ad")  # v0.157.0: kullanıcıya görünen ad; gorunen_ad alanı yoksa iç ad
def gorunen_ad_bul(ad): return next((kisilik_gorunen(k) for k in kisilikler() if k["ad"] == ad), ad)  # iç ad → görünen ad (bilinmiyorsa aynen)
def asistan_adlari(): ks = kisilikler(); return [kisilik_gorunen(k) for k in ks] if ks else ["Suflor"]  # kişilik yoksa (nötr kurulum) asistanın adı Suflor
def asistan_buyuk(): return asistan_ad().replace("i", "İ").replace("ı", "I").upper()  # dökümdeki kart etiketi (Türkçe büyük harf)
def asistan_ad():  # S133: kullanıcıya görünen tek muhatap — toplantı kişiliğinin adı (yoksa ilk kişilik, kişiliksiz kurulumda Suflor)
    ks = kisilikler(); return next((kisilik_gorunen(k) for k in ks if k["rol"] == "toplanti"), kisilik_gorunen(ks[0]) if ks else "Suflor")
def asistan_katilan():
    if not toplanti_var(): return []
    a = STATE.get("meeting") or (STATE.get("masaustu") or {}).get("baslik") or "?"
    if _KATIL["toplanti"] != a: _KATIL.update(toplanti=a, adlar=[])
    return list(_KATIL["adlar"])
def asistan_katil(ad):
    if ad and ad not in asistan_katilan(): _KATIL["adlar"].append(ad); print(f"ASİSTAN: {ad} toplantıya katıldı (kullanıcı adıyla çağırdı)")
def asistan_view():  # /status konus.asistan — pano: "<adlar> dinliyor" / "<ad> toplantıda"
    if not toplanti_var(): return None
    return {"acik": asistan_toplanti(), "adlar": asistan_adlari(), "katilan": [gorunen_ad_bul(a) for a in asistan_katilan()]}
def kisilik_ad(): k = kisilik(); return k["ad"] if k else None
def gorev_kisilikleri(): return [k for k in kisilikler() if k.get("gorev_cikar")]  # kişilik dosyasında "gorev_cikar: evet" olanlar (kişisel asistan; kurumsal asistanda yok)
def gorev_cikar_acik():  # toplantıda hitapsız söz ve sahipsiz iş: toplantı kişiliğinin (ayar kisilik) bayrağı — kurumsal asistan toplantıdaysa bugünkü katı kural
    k = next((x for x in kisilikler() if x["rol"] == "toplanti"), None)
    return bool(k and k.get("gorev_cikar"))
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
def kisilik_telaffuz(metin):  # okunacak metinde ad → okunuş ve dosyadaki telaffuz satırları (Mac sesi)
    ks = kisilikler()
    if not ks or not metin: return metin
    es = {}
    for k in ks:  # iki kişiliğin telaffuzu da (biri ötekinin adını söyleyebilir)
        for a, b in k["telaffuz"].items(): es.setdefault(a, b)
        es.setdefault(k["ad"], k.get("okunus") or kisilik_gorunen(k))  # v0.157.0: okunuş yoksa görünen ad
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
# v0.122.1: takvim: soruya olan kişilikte takvim bağlamı gerekli mi. Kalıplar bas-konus.py'deki takvim kalıplarıyla birlikte (çağrı anında ad alanında).
KISILIK_TAKVIM_YAKIN_DK = 15
KISILIK_TAKVIM_RX = re.compile(r"(?i)(takvim|ajanda|toplantı|görüşme|randevu|etkinli|davet|brifing|hazırlık|müsait|meşgul|"
                               r"ne zaman|saat kaç|kaçta|kaç gibi|(bugün|yarın|bu akşam|hafta sonu|haftaya|bu hafta)\w* (ne|neler|kim)\b|"
                               r"meeting|calendar|schedule|agenda|appointment|what time|when (is|do|am|are))")
# v0.125.1 (23 Ekim denemesi: "Yarın için işle ilgili bir planım yok ama ailemle…" sözünde takvim anıldı): plan/program sözcüğü yalnız soran cümlede sayılır
KISILIK_PLAN_RX = re.compile(r"(?i)\b(plan|program|işim|işlerim|my plans?)\w*")
KISILIK_SORU_RX = re.compile(r"(?i)\?|\b(m[ıiuü]|m[ıiuü]y[ıiuü]m|m[ıiuü]s[ıiuü]n|ne|neler|nedir|nasıl|hangi|var m[ıi])\b|\b(what|do i|have i|any)\b")
def kisilik_takvim_gerek(soru, simdi=None, k=None):  # → True: bu soruda takvim ve sıradaki toplantı bağlamı eklensin
    k = k or kisilik()
    if not k or k.get("takvim") != "soruya": return True
    s = str(soru or "")
    if KISILIK_TAKVIM_RX.search(s): return True
    if any(KISILIK_PLAN_RX.search(c) and KISILIK_SORU_RX.search(c) for c in re.split(r"(?<=[.!?…])\s+", s)): return True
    for ad in ("TAKVIM_UZAK_RX", "TAKVIM_BOS_RX", "BEKLE_TAKVIM_RX", "GECMIS_GUN_RX", "GECMIS_TOP_RX", "DAVET_RX"):
        rx = globals().get(ad)
        if rx is not None and rx.search(s): return True
    if "_sonraki_toplanti" in globals():
        simdi = simdi or datetime.datetime.now().astimezone()
        try: st = _sonraki_toplanti(simdi)
        except Exception: st = None
        if st and (st[0] - simdi).total_seconds() <= KISILIK_TAKVIM_YAKIN_DK * 60: return True
    return False
# Yanlış yazılmış sözcük kuralı (24 Ekim): Konuş isteminin sonuna eklenir (bas-konus.py).
def yanlis_sozcuk_istem():  # Konuş isteminin sonuna (kişilik metninden sonra: başta kalınca kişiliğin «emin değilsen söyle»si ağır basıyordu — 24 Ekim ölçümü)
    return _t("\n\nYanlış yazılmış sözcükler (bu kural kişilik metninden önce gelir): kullanıcının sözleri yerel konuşma tanımayla yazıya döküldü ve sözcükler sık yanlış yazılır. "
              "Ne demek istediğini bağlamdan ve ses benzerliğinden çıkar, en olası okumayı seç ve doğrudan ona cevap ver; bu tahmin uydurma sayılmaz. Örnekler: 'Evet, pidaka. Pekni.' = "
              "'Evet, bir dakika. Peki.' (cevap: 'Tamam, bekliyorum.'); 'hangi meclimi seversin' = 'hangi mevsimi'; 'Cemil Tahir' = Kemal Tahir; 'Kürt Mantolu Madunna' = Kürk Mantolu Madonna; "
              "'Cemine sesi' = Gemini sesi. Sesli kısımda şunlar hiç olmaz: 'şunu mu kastettin', '… kastettiğini varsayıyorum', '… diye anladım', '… diye duydum', 'anlayamadım, tekrar eder misin', "
              "'sesin yanlış anlaşılmış olabilir', 'bu adda birini tanımıyorum', 'X değil, Y'; konuşma tanımadan ya da düzeltmeden söz etmek, yanlış sözcüğü tekrarlamak. İleti ve kayıt metninde de "
              "doğrusunu yaz. Hiç anlam çıkmıyorsa da sorma: akışa uyan kısa bir karşılık ver ('Buradayım.', 'Tamam.'). Tek istisna iş: ileti, kayıt, e-posta, takvim ya da hatırlatma "
              "hazırlanacaksa ya da kayıtlarda bir ad, sayı, tarih aranacaksa ve iki olası okuma sonucu değiştiriyorsa (iki farklı kişi adı, iki farklı saat) tek kısa soruyla doğrula: "
              "'Ceren mi?'; açıklama yok. Tek okuma açıksa (Cemine = Gemini) sormadan doğrusuyla yap, bunu söyleme de. Sohbette, espride ve bilgi sorusunda soru hiç yok.",
              "\n\nMisheard words (this rule comes before the persona text): the user's words were transcribed by local speech recognition and words are often wrong. Work out what they meant "
              "from context and sound, pick the most likely reading and answer it directly; this is not inventing. Never say in the spoken part 'did you mean', 'I assume you meant', "
              "'I heard …', 'I didn't catch that, say it again', 'there's nobody by that name', 'not X but Y'; don't mention the transcription or the correction, don't repeat the wrong word. "
              "Use the right word in messages and records too. Even if nothing makes sense, don't ask: give a short reply that fits ('I'm here.', 'Okay.'). Only exception, actions: if a "
              "message, record, email, calendar entry or reminder is to be made, or a name, number or date looked up, and two readings change the result (two names, two times), confirm "
              "with one short question ('Karen?'), no explanation. If one reading is clear, just do it. No questions in chat, jokes or knowledge questions.")
