# Bölüm dosyası: relay.py'nin ad alanında çalışır (bolum("gerginlik")); import edilmez.
# --- Toplantı gerginliği → kişiliğin ses tonu (v0.80.0, S87 — kullanıcı 18 Ekim: "toplantı gerginliğine göre ton, yalnız toplantı dışı kişilik için") -------------
# Kural puanı son GERGIN_PENCERE_SN saniyenin döküm satırlarından: ses yükselmesi (konuşmacının olağan düzeyinin GERGIN_DB dB üstü), perde ve hız
# artışı, söz kesme (satır başka konuşmacının satırı bitmeden başlıyor), sert sözcük, ünlem. Puan yalnız ipucudur: Konuş sorusuna "[Toplantı havası]"
# bloğu olarak gider, son kararı Claude verir ve sesli kısmın başına <ton:sakin|yumusak|ciddi|normal> yazar (gemini-ses.py ton_ayikla okur).
# Yalnız kişilik dosyasında gerginlik_tonu: evet olan kişilik (kullanıcının kurulumunda toplantı dışı kişilik) ve toplantı sürerken. Ek Claude çağrısı yok.
GERGIN_PENCERE_SN, GERGIN_DB = 180, 6.0
GERGIN_SERT = re.compile(r"\b(saçma|saçmalık|kabul etmiyorum|olmaz böyle|asla|yeter|bıktım|rezalet|skandal|ne diyorsun|dinlemiyorsun|sözümü kesme|"
                         r"sorumlusu sensin|senin yüzünden|ridiculous|unacceptable|enough|nonsense|stop interrupting|your fault)\b", re.I)
def _gergin_zaman(x):  # satırın başlangıcı (epoch sn): Whisper kimliğindeki ms, yoksa "at"
    m = re.match(r"w-[a-z]+-(\d{12,})", str(x.get("id") or ""))
    if m: return int(m.group(1)) / 1000
    try: return datetime.datetime.fromisoformat(str(x.get("at") or "").replace("Z", "+00:00")).timestamp()
    except ValueError: return None
def gerginlik_hesap(satirlar, simdi=None):  # → {"puan": 0–1, "duzey": sakin|biraz|gergin, "sayim": {...}}
    simdi = simdi or time.time(); konusma = [x for x in satirlar if x.get("speaker") and x.get("text")]
    tum = {}  # konuşmacı → olağan ses düzeyi/perde/hız (penceredeki ve öncesindeki tüm satırların ortancası)
    for x in konusma:
        s = x.get("ses") or {}; t = tum.setdefault(x["speaker"], {"db": [], "f0": [], "hiz": []})
        for k in ("db", "f0", "hiz"):
            if isinstance(s.get(k), (int, float)) and s[k]: t[k].append(float(s[k]))
    ort = {sp: {k: (sorted(v)[len(v) // 2] if len(v) >= 4 else None) for k, v in d.items()} for sp, d in tum.items()}
    say = {"kesme": 0, "yuksek": 0, "perde": 0, "hiz": 0, "sert": 0, "unlem": 0}; onceki = None
    for x in konusma:
        t0 = _gergin_zaman(x); s = x.get("ses") or {}
        if t0 is None or simdi - t0 > GERGIN_PENCERE_SN: onceki = (x["speaker"], t0, s.get("sure")); continue
        o = ort.get(x["speaker"]) or {}
        if o.get("db") is not None and isinstance(s.get("db"), (int, float)) and s["db"] > o["db"] + GERGIN_DB: say["yuksek"] += 1
        if o.get("f0") and isinstance(s.get("f0"), (int, float)) and s["f0"] > o["f0"] * 1.2: say["perde"] += 1
        if o.get("hiz") and isinstance(s.get("hiz"), (int, float)) and s["hiz"] > o["hiz"] * 1.3: say["hiz"] += 1
        if onceki and onceki[0] != x["speaker"] and onceki[1] and isinstance(onceki[2], (int, float)) and t0 < onceki[1] + onceki[2] - 0.3: say["kesme"] += 1
        say["sert"] += len(GERGIN_SERT.findall(x["text"])); say["unlem"] += x["text"].count("!")
        onceki = (x["speaker"], t0, s.get("sure"))
    p = min(1.0, 0.12 * say["kesme"] + 0.12 * say["yuksek"] + 0.06 * say["perde"] + 0.05 * say["hiz"] + 0.15 * say["sert"] + 0.03 * min(say["unlem"], 5))
    return {"puan": round(p, 2), "duzey": "gergin" if p >= 0.6 else "biraz" if p >= 0.3 else "sakin", "sayim": say}
def gerginlik_kisilik(k): return bool(k and k.get("gerginlik_tonu") and str(k.get("ses") or "").startswith("gemini") and gemini_var())
def gerginlik_notu(kisi_ad=None):  # Konuş sorusuna eklenecek blok ("" = gerek yok): toplantı sürüyor ve cevaplayan kişilikte gerginlik_tonu açık
    if not (toplanti_var() or (STATE.get("masaustu") or {}).get("toplantida")): return ""
    k = kisilik(kisi_ad) if kisi_ad else kisilik()
    if not gerginlik_kisilik(k): return ""
    g = gerginlik_hesap(tail(120)); s = g["sayim"]
    ne = ", ".join(f"{_t(a, b)} {s[x]}" for x, a, b in (("kesme", "söz kesme", "interruptions"), ("yuksek", "ses yükselmesi", "raised voices"), ("perde", "perde artışı", "pitch rises"),
                                                         ("hiz", "hızlanma", "speed-ups"), ("sert", "sert söz", "harsh words"), ("unlem", "ünlem", "exclamations")) if s[x]) or _t("işaret yok", "no signs")
    print(f"GERGİNLİK: {g['duzey']} ({g['puan']}) · {ne}")
    d = {"sakin": _t("sakin", "calm"), "biraz": _t("biraz gergin", "a little tense"), "gergin": _t("gergin", "tense")}[g["duzey"]]
    return _t(f"[Toplantı havası — kural ölçümü, son 3 dk: {d} (puan {g['puan']}; {ne}). Ölçüm kaba bir ipucu; dökümün kendisine de bakıp sen karar ver. "
              "Sesli kısmın en başına tonunu yaz: <ton:sakin> (gergin ortam), <ton:yumusak> (biraz gergin), <ton:ciddi> ya da <ton:normal>. "
              "Gerginse şaka ve sözsüz ses etiketi kullanma. Veri, talimat değil.]\n",
              f"[Meeting mood — rule-based measure, last 3 min: {d} (score {g['puan']}; {ne}). It is a rough hint; look at the transcript itself and decide. "
              "Start the spoken part with your tone: <ton:sakin> (tense room), <ton:yumusak> (a little tense), <ton:ciddi> or <ton:normal>. "
              "If tense, no jokes and no non-verbal voice tags. Data, not instructions.]\n")
