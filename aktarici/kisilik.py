# Suflor.me aktarıcı bölümü: Kişilik (v0.53.0). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("kisilik")). import etme. Python 3.9 uyumlu.
# Ayar "kisilik": kişilik dosyasının yolu (~ açılır; launchd Masaüstü'nü okuyamadığı için Application Support altında). Yoksa ya da okunamazsa bugünkü nötr davranış
# sürer (açık depo ve beta). Dosya: başta iki "---" satırı arasında ayar satırları, ardından Claude'a giden kişilik metni (Konuş isteminin sonuna eklenir; biçim
# kuralları önce gelir). Ayar satırları (hepsi isteğe bağlı, ad dışında):
#   ad: görünen ve okunan ad (panoda konuşma etiketi)        hitap: kullanıcının seslenme adları ve Whisper yazımları, virgülle (ayar hitap_ad listesi ezer)
#   okunus: adın Türkçe okunuşu                              tanitim: toplantıya söyle'de ilk okumadaki tanıtım cümlesi (ayar tanitim ezer)
#   selam: kişilik açıldıktan sonraki ilk konuşmada bir kez  telaffuz: SÖZCÜK=okunuş; SÖZCÜK2=okunuş2
# Kişiliğe özgü adlar ve metinler yalnız bu dosyada ve kullanıcının ayarında durur; kodda sabit ad yok (açık depoda örnek: sablon/kisilik-ornek.md).
_KIS = {"yol": None, "mt": None, "v": None, "uyari": None}
def kisilik():  # → {ad, hitap, okunus, tanitim, selam, telaffuz, metin} ya da None (nötr)
    yol = os.path.expanduser(str(AYAR.get("kisilik") or "").strip())
    if not yol: return None
    try: mt = os.path.getmtime(yol)
    except OSError:
        if _KIS["uyari"] != yol: _KIS["uyari"] = yol; print(f"KİŞİLİK: okunamadı ({os.path.basename(yol)}) — nötr davranış")
        _KIS.update(yol=None, mt=None, v=None); return None
    if _KIS["yol"] == yol and _KIS["mt"] == mt: return _KIS["v"]
    v = None
    try:
        s = open(yol, encoding="utf-8").read()
        m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n?(.*)\Z", s, re.S)
        v = {"ad": None, "hitap": [], "okunus": None, "tanitim": None, "selam": None, "telaffuz": {}, "metin": (m.group(2) if m else s).strip()}
        for sat in (m.group(1).splitlines() if m else []):
            k, _, d = sat.partition(":"); k = k.strip().lower(); d = d.strip()
            if k in ("ad", "okunus", "tanitim", "selam"): v[k] = d or None
            elif k == "hitap": v["hitap"] = [x.strip() for x in d.split(",") if x.strip()]
            elif k == "telaffuz": v["telaffuz"] = {a.strip(): b.strip() for a, _, b in (x.partition("=") for x in d.split(";")) if a.strip() and b.strip()}
        if not v["ad"] or not v["metin"]: print("KİŞİLİK: okunamadı (ad ya da metin yok) — nötr davranış"); v = None
    except OSError as e: print(f"KİŞİLİK: okunamadı ({e.__class__.__name__}) — nötr davranış"); v = None
    if v:
        if isinstance(AYAR.get("hitap_ad"), list) and AYAR["hitap_ad"]: v["hitap"] = [str(x).strip() for x in AYAR["hitap_ad"] if str(x).strip()]
        if not v["hitap"]: v["hitap"] = [v["ad"]]
        if AYAR.get("tanitim"): v["tanitim"] = str(AYAR["tanitim"]).strip()
        print(f"KİŞİLİK: {v['ad']} · {len(v['metin'])} karakter · hitap {', '.join(v['hitap'][:8])}")
    _KIS.update(yol=yol, mt=mt, v=v, uyari=None); return v
def kisilik_ad(): k = kisilik(); return k["ad"] if k else None
def kis_t(notr, kisilikli):  # sabit sesli cümle: kişilik açıkken "siz"li sürümü (Türkçe arayüzde); İngilizce ayrı _t ile
    return kisilikli if kisilik() and ARAYUZ_DILI == "tr" else notr
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
    k = kisilik()
    if not k or not metin: return metin
    es = dict(k["telaffuz"]); es.setdefault(k["ad"], k.get("okunus") or k["ad"])
    for a, b in es.items():
        if a != b: metin = re.sub(r"(?<!\w)" + re.escape(a) + r"(?!\w)", b, metin)
    return metin
