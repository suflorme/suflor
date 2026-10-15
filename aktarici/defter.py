# Suflor.me aktarıcı bölümü: Toplantı defteri (S48). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("defter")):
# STATE, BASE, AYAR, SON, BRIFING, _t … relay.py'nin; buradaki tanımlar da relay.py'ye aittir. import etme. Python 3.9 uyumlu.
# Toplantı bitince bas-konuşla "ne konuştuk, ne karar aldık" diye sorulur; cevap bu defterden gelir. Defter = başlık + gündem + brifing + tam döküm
# (satırlar, kartlar, notlar, kanıt ve gündem işaretleri .md'nin içinde) + konuşmacılar + özet. 13 Ekim ölçümü (deneme 9, 16 ayrıntı sorusu): tam defter
# Sonnet'le 16/16 doğru, soru başı ~0,016 $; toplantı oturumunun kopyası da doğru ama ~9,3 $/soru. Kişi adı içerir: iç veri, yalnız Claude'a gider.
DEFTER_EN_COK = 250000  # karakter (~145k belirteç; ölçüm 15 Ekim: 1 karakter ≈ 0,57 belirteç + ~18k sabit); üstünde kısa defter + tam dökümde Grep.
# Uzun toplantı ölçümü (15 Ekim, 2,7 ve 5,4 sa gerçek döküm): tam defter 16/16, 300k'da giriş 192k belirteç (pencere 200k); kısa defter 14–15/16 — ortadaki
# işaretsiz satırı aramadan "yok" dedi. Bu yüzden sınır 250k ve kısa defterde "yok" demeden içerik araması zorunlu (KONUS_ISTEM + aşağıdaki yönerge).
# Kural ölçümle ayarlandı (L4–L6): head_limit 20 doğru satırı kesti (13,5–14/16), 60 + "sınıra takılırsa daralt" 15–15,5/16, uydurma 0–1.
DEFTER_ORTUSME_SN = 180  # aynı toplantının bölünmüş dosyaları (v0.32.15 öncesi masaüstü başlık değişimi) en az bu kadar üst üste yazılmıştır
_DOSYA_RX = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})-.+\.md$")
_DF_ON = {"t": 0, "v": None, "k": None}
def _df_aralik(f):  # (başlangıç, son yazma) epoch — başlangıç dosya adından (dakika), son yazma aktarıcının kaydından ya da dosya saatinden
    m = _DOSYA_RX.match(f)
    if not m: return None
    try: bas = datetime.datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M").timestamp()
    except ValueError: return None
    try: son = max(STATE["file_last"].get(f) or 0, os.path.getmtime(os.path.join(BASE, f)))
    except OSError: return None
    return bas, son
def defter_toplanti():
    # Bas-konuşun defteri hangi toplantı: toplantı yokken son toplantı dosyası, son yazması konus_defter_saat (varsayılan 3) saat içindeyse.
    # Aynı toplantının bölünmüş dosyaları (aralıkları ≥ 3 dk üst üste) birlikte. → {"dosyalar": [...], "ad": başlık, "son": epoch} ya da None
    an = (STATE.get("file"), len(SON), STATE["file_last"].get(STATE.get("file")))  # /status her yoklamada sorar: 10 sn önbellek, toplantı değişince hemen
    if time.time() - _DF_ON["t"] < 10 and _DF_ON["k"] == an: return _DF_ON["v"]
    v = None; saat = AYAR.get("konus_defter_saat", 3)
    try: saat = float(saat)
    except (TypeError, ValueError): saat = 3
    f = STATE.get("file") or ((SON[-1].get("dosya") if SON else None))
    if saat > 0 and f and os.path.isfile(os.path.join(BASE, f)):
        a = _df_aralik(f)
        if a and time.time() - a[1] <= saat * 3600:
            ara = {}
            for g in os.listdir(BASE):
                if _DOSYA_RX.match(g) and g[:10] == f[:10]:
                    x = _df_aralik(g)
                    if x: ara[g] = x
            kume, b0, b1 = {f}, a[0], a[1]; degisti = True
            while degisti:
                degisti = False
                for g, (gb, gs) in ara.items():
                    if g not in kume and min(gs, b1) - max(gb, b0) >= DEFTER_ORTUSME_SN: kume.add(g); b0, b1 = min(b0, gb), max(b1, gs); degisti = True
            ds = sorted(kume, key=lambda g: ara.get(g, a)[0])
            v = {"dosyalar": ds, "ad": _df_baslik(f), "son": b1, "bas": b0}
    _DF_ON.update(t=time.time(), v=v, k=an); return v
def _df_baslik(f):
    try:
        with open(os.path.join(BASE, f), encoding="utf-8") as h: l = h.readline()
        return l.split("—", 1)[1].strip() if "—" in l else f[16:-3]
    except OSError: return f[16:-3]
def _df_adlar(f, satirlar):
    # toplantı sonu konuşmacı düzeltmesi (<toplantı>.konusmaci.json: satır kimliği → ad) .md'ye yazılmaz; .jsonl'deki (saat, canlı ad) sırasıyla uygulanır
    try: es = json.load(open(os.path.join(BASE, f[:-3] + ".konusmaci.json"), encoding="utf-8")).get("ad") or {}
    except (OSError, ValueError): return satirlar
    if not es: return satirlar
    sira = collections.defaultdict(list)
    try:
        for l in open(os.path.join(BASE, f[:-3] + ".jsonl"), encoding="utf-8"):
            try: r = json.loads(l)
            except ValueError: continue
            if r.get("text") is not None and r.get("id") in es: sira[(r.get("time"), r.get("speaker"))].append(es[r["id"]])
    except OSError: return satirlar
    ol = []
    for l in satirlar:
        p = l.split(" | ", 2)
        if l.startswith("| ") and len(p) == 3 and sira.get((p[0][2:].strip(), p[1].strip())):
            l = f"{p[0]} | {sira[(p[0][2:].strip(), p[1].strip())].pop(0)} | {p[2]}"
        ol.append(l)
    return ol
_DF_TUR = {"karar": ("Karar", "Decision"), "is": ("İş", "Task"), "soz": ("Söz", "Promise"), "soru": ("Açık soru", "Open question"), "sayi": ("Sayı", "Number"), "iddia": ("İddia", "Claim")}
def _df_yapi(v):  # S48 defter turu: toplantı oturumunun yapı dosyası (kaynak saatleri bitir'de doğrulandı) → defter bölümü
    if not isinstance(v, dict) or not isinstance(v.get("maddeler"), list): return ""
    t = lambda x, n=300: " ".join(str(x or "").split())[:n]
    s = [f"## {_t('Toplantı sonu: kararlar, işler, düzeltmeler (toplantı oturumu; kaynak saatleri dökümde doğrulandı)', 'End of meeting: decisions, tasks, corrections (meeting session; source times checked against the transcript)')}"]
    for m in v["maddeler"]:
        og = [o for o in (m.get("ogeler") or []) if isinstance(o, dict) and o.get("tur") in _DF_TUR and str(o.get("metin") or "").strip()]
        if not og and not m.get("baslik"): continue
        s.append(f"### {t(m.get('baslik'), 120)}" + (f" ({t(m.get('durum'), 30)})" if m.get("durum") else ""))
        for o in og[:40]:
            ek = [x for x in ((_t("tarih ", "due ") + t(o["tarih"], 20)) if o.get("tarih") else "", (_t("netlik: ", "clarity: ") + t(o["netlik"], 20)) if o.get("netlik") else "",
                              (_t("varsayım: ", "assumption: ") + t(o["varsayim"], 160)) if o.get("varsayim") else "", f"\"{t(o['alinti'], 160)}\"" if o.get("alinti") else "") if x]
            s.append(f"- {_t(*_DF_TUR[o['tur']])}" + (f" [{t(o['saat'], 8)}]" if o.get("saat") else "") + (f" {t(o.get('kim') or o.get('sahip'), 60)}" if (o.get("kim") or o.get("sahip")) else "")
                     + f" — {t(o['metin'])}" + (f" ({'; '.join(ek)})" if ek else ""))
    dz = [d for d in (v.get("duzeltmeler") or []) if isinstance(d, dict) and d.get("yanlis") and d.get("dogru")]
    if dz: s += [_t("Düzeltmeler (dökümde yanlış duyulmuş biçim → doğrusu):", "Corrections (misheard form in the transcript → correct):")] + \
                [f"- " + (f"[{t(d.get('saat'), 8)}] " if d.get("saat") else "") + f"\"{t(d['yanlis'], 80)}\" → \"{t(d['dogru'], 80)}\"" for d in dz[:60]]
    if v.get("dokum_notu"): s.append(_t("Döküm notu: ", "Transcript note: ") + t(v["dokum_notu"], 500))
    return "\n".join(s) if len(s) > 1 else ""
def defter_metni(d=None):
    # Tek metin; sabit kısım önde, büyüyen kısım (döküm, özet) sonda. → (metin, kısa_mı) ya da (None, False)
    d = d or defter_toplanti()
    if not d: return None, False
    en = ARAYUZ_DILI == "en"; dokum, kisi = [], collections.Counter()
    for f in d["dosyalar"]:
        try: s = open(os.path.join(BASE, f), encoding="utf-8").read().splitlines()
        except OSError: continue
        s = _df_adlar(f, s)
        s = [l.replace("| kanit/", "| " + os.path.join(BASE, "kanit") + "/", 1) if "**📷 KANIT" in l and "metni**" not in l else l for l in s]  # Konuş görüntüyü Read ile açabilsin
        for l in s:
            p = l.split(" | ", 2)
            if l.startswith("| ") and len(p) == 3 and "**" not in p[1] and p[1].strip() not in ("Konuşmacı", "---"): kisi[p[1].strip()] += 1
        dokum.append((f, s))
    bas, son = datetime.datetime.fromtimestamp(d["bas"]), datetime.datetime.fromtimestamp(d["son"])
    tarih = f"{bas:%Y-%m-%d}" if en else f"{bas.day} {_AY_TR[bas.month - 1]} {bas.year}"
    p = [f"# {_t('Toplantı defteri', 'Meeting record')} — {d['ad']}", f"{tarih}, {bas:%H:%M}–{son:%H:%M}"]
    ag = None
    for f in d["dosyalar"]:
        try: ag = json.load(open(os.path.join(BASE, "gundemler", f[:-3] + ".json"), encoding="utf-8")); break
        except (OSError, ValueError): pass
    if ag and ag.get("items"):
        p += ["", f"## {_t('Gündem', 'Agenda')}" + (f" ({ag.get('baslangic')}–{ag.get('bitis')})" if ag.get("bitis") else "")] + [f"- {' '.join(str(x).split())}" for x in ag["items"][:60]]
    try:
        ts = json.load(open(os.path.join(BASE, "takvim-secilen.json"), encoding="utf-8")); b = BRIFING.get(str(ts.get("olay") or "")) or {}
        if ts.get("konu") == d["ad"] and b.get("durum") == "hazir" and b.get("sonuc"):
            r = b["sonuc"]; p += ["", f"## {_t('Toplantı öncesi brifing', 'Pre-meeting briefing')}", r.get("ozet") or ""] + [f"- {x}" for k in ("dikkat", "acik", "gecmis") for x in (r.get(k) or [])]
    except (OSError, ValueError, AttributeError): pass
    ozet = yapi = None
    for r in reversed(SON):
        if r.get("dosya") in d["dosyalar"]:
            try: yapi = json.load(open(r["yapi"], encoding="utf-8")) if r.get("yapi") else None
            except (OSError, ValueError): yapi = None
            for y in (r.get("kopya"), os.path.join(BASE, "ozetler", os.path.basename(r.get("ozet") or ""))):
                try: ozet = open(y, encoding="utf-8").read()[:60000]; break
                except (OSError, TypeError): pass
            break
    kisiler = f"## {_t('Konuşanlar (satır sayısı)', 'Speakers (lines)')}\n" + ", ".join(f"{k} ({n})" for k, n in kisi.most_common(30))
    oz = f"## {_t('Toplantı sonu özeti', 'End-of-meeting summary')}\n{ozet.strip()}" if ozet else ""
    ys = _df_yapi(yapi)
    if ys: oz = ys + ("\n\n" + oz if oz else "")
    tam = "\n".join(p) + "\n\n" + "\n\n".join(f"## {_t('Döküm', 'Transcript')}: {f}\n" + "\n".join(s) for f, s in dokum) + "\n\n" + kisiler + ("\n\n" + oz if oz else "")
    if len(tam) <= DEFTER_EN_COK: return tam, False
    # kısa defter: işaretli satırlar (kart, not, kanıt, gündem) + son 30 dk tam döküm; ayrıntı için tam dosyada Grep (aracı var, --add-dir BASE)
    sinir = (son - datetime.timedelta(minutes=30)).strftime("%H:%M:%S"); kisa = []
    for f, s in dokum:
        kisa.append(f"## {_t('Döküm (kısa: işaretli satırlar + son 30 dk)', 'Transcript (short: marked lines + last 30 min)')}: {f}\n"
                    + _t(f"Tam döküm: {os.path.join(BASE, f)} — bu kısa defterde olmayan her şey orada: 'kayıtta yok' demeden önce Grep ile satır içeriğinde ara (output_mode content, -i, head_limit 60, en az iki farklı sözcükle; sınıra takılırsa daralt); yalnız soruyu cevaplayan satırı kullan.",
                            f"Full transcript: {os.path.join(BASE, f)} — everything missing from this short record is there: before saying 'not in the record', Grep the line contents (output_mode content, -i, head_limit 60, at least two different words; narrow it if it hits the limit); use only the line that answers.") + "\n"
                    + "\n".join(l for l in s if "**" in l or l.startswith("#") or (l.startswith("| ") and l[2:10] >= sinir)))
    k = "\n".join(p) + "\n\n" + (oz + "\n\n" if oz else "") + kisiler + "\n\n" + "\n\n".join(kisa)
    return k[-DEFTER_EN_COK:] if len(k) > DEFTER_EN_COK else k, True
def defter_view():  # /status konus.defter: panoda "Son toplantı hazır" satırı (toplantı yokken)
    if toplanti_var(): return None
    d = defter_toplanti()
    return {"ad": d["ad"], "saat": datetime.datetime.fromtimestamp(d["son"]).strftime("%H:%M")} if d else None
