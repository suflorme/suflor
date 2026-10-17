# Suflor.me aktarıcı bölümü: Kişilik (v0.53.0). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("kisilik")). import etme. Python 3.9 uyumlu.
# Ayar "kisilik": kişilik dosyasının yolu (~ açılır; launchd Masaüstü'nü okuyamadığı için Application Support altında). Yoksa ya da okunamazsa bugünkü nötr davranış
# sürer (açık depo ve beta). Dosya: başta iki "---" satırı arasında ayar satırları, ardından Claude'a giden kişilik metni (Konuş isteminin sonuna eklenir; biçim
# kuralları önce gelir). Ayar satırları (hepsi isteğe bağlı, ad dışında):
#   ad: görünen ve okunan ad (panoda konuşma etiketi)        hitap: kullanıcının seslenme adları ve Whisper yazımları, virgülle (ayar hitap_ad listesi ezer)
#   okunus: adın Türkçe okunuşu                              tanitim: toplantıya söyle'de ilk okumadaki tanıtım cümlesi (ayar tanitim ezer)
#   selam: kişilik açıldıktan sonraki ilk konuşmada bir kez  telaffuz: SÖZCÜK=okunuş; SÖZCÜK2=okunuş2
# Kişiliğe özgü adlar ve metinler yalnız bu dosyada ve kullanıcının ayarında durur; kodda sabit ad yok (açık depoda örnek: sablon/kisilik-ornek.md).
# v0.61.0: iki kişilik. Ayar "kisilik_toplanti_disi": ikinci dosya — toplantı yokken o konuşur; toplantıda "kisilik" (ilk dosya). Kullanıcı cümleye birinin
# adıyla başlarsa ("<Ad>, …") o soru ve ardından KISILIK_SURE_SN içindeki adsız sorular o kişilikle cevaplanır. Toplantıda varsayılan olmayan kişilik yalnız
# kullanıcıya (kulaklık/pano) cevap verir; kullanıcı toplantıya söylemesini isterse (TOPLANTIYA_RX) toplantıya okunur. Ek ayar satırı: hitap_bicimi: sen (varsayılan siz).
# v0.71.0: ses: piper | <Mac ses adı> ve hiz: 1,15 (çarpan) — kişiliğin cevapları bu sesle okunur (iki kişilik ayrı duyulsun). Mac'in sistem (Siri) sesi say -r'yi
# yok sayar (ölçüm 17 Ekim: -r 180/220 aynı süre); hız yalnız Piper'da ve adı verilen Mac sesinde (ör. Yelda) işler. Toplantıya okuma (BlackHole) bundan etkilenmez.
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
        v = {"ad": None, "hitap": [], "okunus": None, "tanitim": None, "selam": None, "telaffuz": {}, "bicim": "siz", "ses": None, "hiz": None, "rol": rol, "metin": (m.group(2) if m else s).strip()}
        for sat in (m.group(1).splitlines() if m else []):
            k, _, d_ = sat.partition(":"); k = k.strip().lower(); d_ = d_.strip()
            if k in ("ad", "okunus", "tanitim", "selam"): v[k] = d_ or None
            elif k == "hitap": v["hitap"] = [x.strip() for x in d_.split(",") if x.strip()]
            elif k == "hitap_bicimi": v["bicim"] = "sen" if d_.lower() == "sen" else "siz"
            elif k == "ses": v["ses"] = d_ or None  # v0.71.0: "piper" ya da Mac ses adı (say -v); yoksa ayardaki ses
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
def kisilik_hitap_bul(metin):  # cümle başında bir kişiliğin adı → (kişilik, adsız metin) ya da (None, metin)
    ks = kisilikler()
    if len(ks) < 2 or not metin: return None, metin
    for k in sorted(ks, key=lambda k: -max(len(a) for a in k["hitap"])):
        m = re.match(r"\W*(?:" + "|".join(re.escape(a) for a in sorted(k["hitap"], key=len, reverse=True)) + r")(?:'\w+)?(?:\s*[,:.!]\s*|\s+(?=\w))", metin, re.I)
        if m and metin[m.end():].strip(): return k, metin[m.end():].strip()
    return None, metin
TOPLANTIYA_RX = re.compile(r"(toplantıya|toplantıda|herkese|onlara|karşı tarafa|ekibe|sesli|yüksek sesle|açıktan)\b.{0,25}\b(söyle|anlat|oku|açıkla|cevap ver|konuş|yanıtla|bildir)|"
                           r"\b(söyle|anlat|oku|açıkla)\w*\b.{0,15}\b(toplantıya|herkese|onlara|karşı tarafa)|"
                           r"\b(tell|say (it )?to|explain to|answer) (everyone|them|the (meeting|room|team))|\bout loud\b|\baloud\b", re.I)
def toplantiya_istendi(metin): return bool(TOPLANTIYA_RX.search(metin or ""))
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
