# Suflor.me aktarıcı bölümü: Toplantı moderatörü. Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("moderator")):
# KONUS, _KS, OT, TS, AYAR, STATE, tail, agenda, toplanti_var, kanal_sessizlik, ts_caliyor, kisilik_sec, kisilikler, _konus_kur, _konus_sor … diğer bölümlerin. import etme.
# --- Moderatör (v0.83.0; S93, kullanıcı 19 Ekim: "toplantı yönetimini kişiliğe devret, otonom sürdürsün") -----------------------------------------
# Kullanıcı toplantıda kişiliğe seslenip "toplantıyı sen yönet" der (gündem aynı cümlede "gündem: A, B ve C" ya da agenda.json'dan). Moderatör yeni bir konuşma
# motoru değildir: ne zaman ne söyleneceğine karar verir, sözü Konuş sürecine "[Moderatör görevi]" olarak verir; cevap otonom yoldan (itiraz penceresi,
# söz sırası, kesilince susma) toplantıya okunur. Görevler: başla (gündemi ve ilk maddeyi aç) · madde aç · sessiz kalana söz ver · uzun konuşanı nazikçe
# toparla · uzun sessizlikte canlandır · süre dolunca özet + karar + onay · kapanış (kararlar, sorumlular, yönetimi geri ver). Katılımcıların kişiliğe
# soruları otonom yoldan cevaplanır (moderatör açıkken otonom ayarı kapalı olsa da). Kullanıcının komutları: sonraki madde · süre ver/uzat · özetle ·
# bekle/devam · yönetimi bırak. Toplantı bitince ya da kullanıcı bırakınca kapanır.
MOD = {"acik": False, "maddeler": [], "i": 0, "faz": None, "t_bas": 0.0, "t_madde": 0.0, "sure_sn": 420.0, "kisilik": None, "bekle": False,
       "gorev": None, "t_gorev": 0.0, "son_davet": {}, "t_son_mudahale": 0.0, "t_karar": 0.0, "kayit": [], "neden": None}
MOD_K = threading.RLock()
MOD_MADDE_DK, MOD_EN_AZ_DK = 7.0, 3.0  # gündemde süre yoksa madde başına; toplam süreden bölünce en az
MOD_DAVET_ORAN, MOD_DAVET_ARA_SN = 0.4, 150.0  # maddenin %40'ı geçince hiç konuşmayan katılımcıya söz; aynı kişiye en sık
MOD_UZUN_SN, MOD_SESSIZ_SN, MOD_ARA_SN = 120.0, 25.0, 45.0  # tek kişi kesintisiz · kimse konuşmuyor · iki müdahale arası en az
MOD_KARAR_SN = 12.0  # özet + "onaylıyor musunuz?" sonrası itiraz/ekleme süresi; biri konuşursa sessizlik beklenir
MOD_GOREV_SN = 75.0  # görev bu sürede bitmezse (Claude ya da söz sırası takıldı) bırakılır
if os.environ.get("SUFLOR_TEST_MOD_HIZLI"): MOD_DAVET_ARA_SN, MOD_UZUN_SN, MOD_SESSIZ_SN, MOD_ARA_SN, MOD_KARAR_SN, MOD_GOREV_SN = 3.0, 4.0, 3.0, 1.0, 1.5, 10.0
MOD_BASLA_RX = re.compile(r"\b(toplantıyı|toplantının yönetimini|yönetimi|moderatörlüğü|toplantıyı yönetmeyi)\s+(?:artık\s+|şimdi\s+|bundan sonra\s+)?(?:sen\s+|sana\s+)?"
                          r"(yönet|devral|al\b|üstlen|bırakıyorum|devrediyorum|veriyorum)|\bmoderatör(?:ümüz)?\s*(?:sen\s+)?ol\b|\bmoderatörlük\s+sende\b|"
                          r"\b(?:run|chair|moderate|take over)\s+(?:the\s+|this\s+)?meeting\b", re.I)
MOD_BIRAK_RX = re.compile(r"\b(yönetimi|toplantıyı)\s+(?:ben\s+)?(?:geri\s+)?(alıyorum|devralıyorum|bırak)|\bmoderatörlüğü\s+bırak|\bben\s+devam\s+ediyorum\b|\bI'?ll take it from here\b", re.I)
MOD_SONRAKI_RX = re.compile(r"\b(sonraki|bir sonraki|diğer)\s+maddeye?\b|\bmaddeye\s+geç|\bnext (item|topic)\b", re.I)
MOD_UZAT_RX = re.compile(r"\b(süre\s+ver|uzat|biraz daha\s+(?:konuşalım|süre)|(\d+)\s*dakika\s+daha)\b|\bmore time\b", re.I)
MOD_OZET_RX = re.compile(r"^\W*(özetle|toparla|özet geç)\b|\bsummari[sz]e\b", re.I)
MOD_BEKLE_RX = re.compile(r"^\W*(bekle|biraz bekle|araya girme|sus bir|bir dakika bekle)\b|\bhold on\b", re.I)
MOD_DEVAM_RX = re.compile(r"^\W*(devam et|devam|sen devam et|yönetmeye devam)\b|\bcarry on\b", re.I)
MOD_GUNDEM_RX = re.compile(r"\bgündem(?:imiz|de|i)?\b\s*(?:şu|şöyle|de)?\s*[:,]?\s*(.+)$|\bagenda\s*[:,]?\s*(.+)$", re.I)

def moderator_acik(): return bool(MOD["acik"])
def moderator_view():
    if not MOD["acik"] and not MOD.get("neden"): return None
    m = MOD["maddeler"]; i = MOD["i"]
    return {"acik": MOD["acik"], "kisilik": MOD["kisilik"], "faz": MOD["faz"], "madde": (m[i] if i < len(m) else None), "sira": i + 1, "toplam": len(m),
            "kalan_sn": max(0, round(MOD["sure_sn"] - (time.time() - MOD["t_madde"]))) if MOD["acik"] and MOD["t_madde"] else None,
            "bekle": MOD["bekle"], "neden": MOD.get("neden")}

def _mod_gundem_coz(metin):  # "gündem: bütçe, takvim ve riskler" → ["Bütçe", "Takvim", "Riskler"]
    m = MOD_GUNDEM_RX.search(metin or "")
    if not m: return []
    s = re.split(r"[.!?](?:\s|$)", (m.group(1) or m.group(2) or "").strip())[0]
    parca = [p.strip(" .,:;-–") for p in re.split(r"\s*(?:,|;|\bve\b|\band\b|\b\d+[.)]\s)\s*", s) if p and p.strip(" .,:;-–")]
    sure_rx = re.compile(r"\b\d+\s*(?:dk|dakika|minutes?)\b|\bsüre\b|\btoplam\b", re.I)  # "her madde 5 dakika", "toplam yarım saat" madde değil
    return [p[:1].upper() + p[1:] for p in parca if 1 < len(p) <= 120 and not sure_rx.search(p)][:8]

def _mod_gundem_dosya():  # agenda.json maddeleri: baştaki sıra numarası ve " — beklenen" kısmı atılır
    out = []
    for x in (agenda().get("items") or []):
        t = x.get("text") or x.get("baslik") if isinstance(x, dict) else str(x)
        t = re.sub(r"^\s*\d+[.)]?\s+", "", str(t or "")).split(" — ")[0].strip()
        if t: out.append(t[:120])
    return out[:12]

def _mod_sure(n, metin=""):  # madde başına sn: "her madde 5 dakika" / "toplam 30 dakika" / agenda.json bitis / varsayılan
    m = re.search(r"(\d+)\s*(?:dk|dakika)", metin or "")
    if m:
        dk = float(m.group(1))
        return 60 * max(MOD_EN_AZ_DK if not os.environ.get("SUFLOR_TEST_MOD_HIZLI") else 0.05, dk / n if MOD_TOPLAM_RX.search(metin) else dk)
    try:
        b = agenda().get("bitis")
        if b and n:
            kalan = (_saat(b) - datetime.datetime.now()).total_seconds()
            if kalan > 120: return max(60 * MOD_EN_AZ_DK, (kalan - 120) / n)
    except Exception: pass
    return 60 * float(AYAR.get("moderator_madde_dk") or MOD_MADDE_DK)

MOD_TOPLAM_RX = re.compile(r"\btoplam(?:da)?\b|\bbütün toplantı|\btoplantı\s+(?:süresi|boyunca)|\bin total\b", re.I)  # "toplantıyı sen yönet" toplam süre değil
def _mod_ben(): return " ".join(str(AYAR.get("ad") or "").split()[:1]).lower()
def _mod_konusanlar(t0):  # t0'dan beri döküm: {konuşan: sözcük}, son konuşan, onun kesintisiz süresi (sn), kullanıcı hariç katılımcılar (bütün toplantı)
    say, sira, hepsi = {}, [], set()
    ben = _mod_ben()
    for e in tail(400):
        k = str(e.get("speaker") or "").strip(); t = e.get("text") or ""
        if not k or not t or e.get("note") or e.get("kanal") == "ben" or (ben and k.lower().startswith(ben)) or "suflor" in k.lower() or "🔊" in t: continue
        if k.lower() in ("karşı taraf", "the other side", "?"): k = _t("Karşı taraf", "The other side")
        hepsi.add(k)
        try: te = _epoch(e.get("at"))
        except Exception: te = time.time()
        if te >= t0: say[k] = say.get(k, 0) + len(t.split()); sira.append((te, k))
    son = sira[-1][1] if sira else None; bas = None
    for te, k in reversed(sira):
        if k != son: break
        bas = te
    return say, son, (time.time() - bas if bas else 0.0), sorted(hepsi)

def _mod_baslik():
    m = MOD["maddeler"]; i = MOD["i"]
    gd = "; ".join(f"{n + 1}) {x}" + (_t(" (şu an)", " (now)") if n == i else "") for n, x in enumerate(m)) or _t("verilmedi", "none given")
    _, _, _, kat = _mod_konusanlar(MOD["t_bas"] - 3600)
    gecen = round((time.time() - MOD["t_madde"]) / 60, 1) if MOD["t_madde"] else 0
    return _t(f"[Moderatör görevi — {AYAR.get('ad') or 'kullanıcı'} toplantının yönetimini sana devretti; bu toplantıyı sen yönetiyorsun. Bu görev kullanıcının değil sistemin; "
              f"cevabının sesli kısmı doğrudan toplantıya okunur, herkes duyar: katılımcılara hitap et; en çok 2–3 kısa cümle, doğal ve akıcı, kendinden emin; "
              f"espri ölçülü; iç not, kullanıcıya özel bilgi, başka toplantı ya da projenin bilgisi yok; kaynak ya da 'defter' deme. "
              f"Gündem: {gd}. Madde süresi {round(MOD['sure_sn'] / 60)} dk, bu maddede geçen {gecen} dk. Katılımcılar: {', '.join(kat) or 'bilinmiyor'} (bir de kullanıcı).]\n",
              f"[Moderator task — {AYAR.get('ad') or 'the user'} handed the running of this meeting to you; you are chairing it. This task comes from the system, not the user; "
              f"the spoken part of your answer is read into the meeting and everyone hears it: address the participants; at most 2–3 short sentences, natural, confident; "
              f"light humour only; no internal notes, nothing private to the user, nothing from other meetings or projects; don't mention sources. "
              f"Agenda: {gd}. Item time {round(MOD['sure_sn'] / 60)} min, elapsed {gecen} min. Participants: {', '.join(kat) or 'unknown'} (plus the user).]\n")

MOD_GOREV = {
    "basla": ("Toplantıyı devraldığını bir cümleyle söyle, gündemi ve süreyi kısaca an, ilk maddeyi aç: «{m}». Konuyu tek cümleyle çerçevele ve bir katılımcıya söz vererek bitir.",
              "Say in one sentence that you are taking over, mention the agenda and timing briefly, open the first item: «{m}». Frame it in one sentence and end by giving someone the floor."),
    "basla_gundemsiz": ("Toplantıyı devraldığını bir cümleyle söyle. Gündem verilmedi: katılımcılara bugün neyi konuşmak istediklerini sor.",
                        "Say in one sentence that you are taking over. No agenda was given: ask the participants what they want to cover today."),
    "ac": ("Önceki madde kapandı. Sıradaki maddeyi aç: «{m}». Konuyu tek cümleyle çerçevele ve bir katılımcıya söz ver.",
           "The previous item is closed. Open the next one: «{m}». Frame it in one sentence and give someone the floor."),
    "davet": ("{kim} bu maddede henüz konuşmadı. Nazikçe ona söz ver: «{m}» konusunda ona somut, kısa bir soru sor.",
              "{kim} hasn't spoken on this item yet. Kindly give them the floor with one concrete, short question about «{m}»."),
    "uzun": ("{kim} uzun süredir kesintisiz konuşuyor. Söylediğinin özünü yarım cümleyle takdir et ve nazikçe sözü diğerlerine aç.",
             "{kim} has been speaking for a long time. Acknowledge the gist in half a sentence and kindly open the floor to the others."),
    "sessiz": ("Bir süredir kimse konuşmuyor. «{m}» maddesini canlandıracak tek bir soru sor ya da karara geçmeyi öner.",
               "Nobody has spoken for a while. Ask one question to revive «{m}» or suggest moving to a decision."),
    "ozet": ("«{m}» maddesinin süresi doldu (ya da kullanıcı özet istedi). Bu maddede konuşulanları toplantı dökümüne dayanarak iki cümlede özetle; karar ve sorumlu varsa söyle, "
             "yoksa açık kalan noktayı söyle; sonunda 'Onaylıyor musunuz, eklemek istediğiniz var mı?' diye sor. Dökümde olmayanı uydurma.",
             "Time is up for «{m}» (or the user asked for a summary). Summarise what was said on this item in two sentences based on the transcript; state the decision and owner if any, "
             "otherwise the open point; end by asking whether everyone agrees or wants to add something. Don't invent anything not in the transcript."),
    "ozet_serbest": ("Şu ana kadar konuşulanları toplantı dökümüne dayanarak iki cümlede özetle, açık kalan noktayı söyle ve devam etmek mi yoksa kapatmak mı istediklerini sor.",
                     "Summarise the discussion so far in two sentences based on the transcript, state the open point and ask whether to continue or wrap up."),
    "kapanis": ("Gündem bitti. Alınan kararları ve sorumluları toplantı dökümüne dayanarak kısaca say (yoksa 'karar çıkmadı' de), katılımcılara teşekkür et ve yönetimi {ben}'e geri ver.",
                "The agenda is done. Briefly list the decisions and owners from the transcript (or say none were made), thank everyone and hand the meeting back to {ben}."),
}

def _mod_mesgul():  # kişilik şu an düşünüyor ya da konuşuyor (Konuş turu, otonom cevap, toplantıya okuma)
    try:
        if _KS.get("tur"): return True
        if OT.get("id") and OT.get("durum") not in OT_SON: return True
        if any(p.poll() is None for p in (TS.get("p") or [])): return True
    except Exception: pass
    return False

def _mod_gorev(ad, **k):  # görevi Konuş sürecine verir; cevap otonom yoldan toplantıya
    if _mod_mesgul(): return False
    m = MOD["maddeler"][MOD["i"]] if MOD["i"] < len(MOD["maddeler"]) else ""
    tr, en = MOD_GOREV[ad]; ben = (AYAR.get("ad") or _t("kullanıcı", "the user")).split(" ")[0]
    metin = _mod_baslik() + _t(tr, en).format(m=m, kim=k.get("kim") or "", ben=ben)
    if MOD["kisilik"]: kisilik_sec(MOD["kisilik"])
    MOD.update(gorev=ad, t_gorev=time.time(), t_son_mudahale=time.time()); MOD["kayit"].append({"t": time.time(), "gorev": ad, "madde": m, "kim": k.get("kim")})
    print(f"MODERATÖR: {ad}" + (f" · {m[:50]}" if m else "") + (f" · {k['kim']}" if k.get("kim") else ""))
    if os.environ.get("SUFLOR_TEST_BASLAT") and os.environ.get("SUFLOR_TEST_MOD_HIZLI"): print(f"MODERATÖR (deneme): istem {len(metin)} karakter"); return True
    tur = {"t_birak": time.time(), "t_metin": time.time(), "metin": "", "tampon": "", "kaynak": "moderator", "otonom": True}; _KS["tur"] = tur
    _konus_kur(durum="dusunuyor", soru=_t(f"Moderatör: {ad}", f"Moderator: {ad}"), cevap="", hata=None, olcum=None, sesli_cevap=False, kaynak="moderator")
    threading.Thread(target=_konus_sor, args=(metin, tur), daemon=True).start(); return True

def moderator_basla(metin, kis_ad=None):
    if not toplanti_var(): return {"ok": False, "err": _t("Toplantı yok", "No meeting")}
    if AYAR.get("toplantiya_ses") is not True:
        print("MODERATÖR: toplantıya söyle kapalı — başlamadı")
        seslendir(_t("Toplantıyı yönetebilmem için Ayarlar'da 'Toplantıya sesli söyle'yi açman gerek.", "To chair the meeting, turn on 'Speak into the meeting' in Settings."), kuyruk=True)
        return {"ok": False, "err": _t("Toplantıya sesli söyle kapalı (⚙ Ayarlar)", "Speaking into the meeting is off (⚙ Settings)")}
    g = _mod_gundem_coz(metin) or _mod_gundem_dosya()
    with MOD_K:
        MOD.update(acik=True, maddeler=g, i=0, faz="basla", t_bas=time.time(), t_madde=time.time(), sure_sn=_mod_sure(max(1, len(g)), metin), kisilik=kis_ad or kisilik_ad(),
                   bekle=False, gorev=None, t_gorev=0.0, son_davet={}, t_son_mudahale=0.0, t_karar=0.0, kayit=[], neden=None)
        if not MOD.get("isci"): MOD["isci"] = True; threading.Thread(target=_mod_dongu, daemon=True).start()
    print(f"MODERATÖR: başladı · {MOD['kisilik'] or '-'} · {len(g)} madde · madde başına {round(MOD['sure_sn'] / 60, 1)} dk" + (f" · {' | '.join(x[:30] for x in g)}" if g else " · gündem yok"))
    return {"ok": True}

def moderator_bitir(neden):
    with MOD_K:
        if not MOD["acik"]: return False
        MOD.update(acik=False, faz=None, neden=neden)
    print(f"MODERATÖR: kapandı ({neden})"); return True

def moderator_komut(metin, kis_ad=None):  # kullanıcının kendi sözü (toplantıda kişiliğe hitap ya da Konuş) → True: moderatör komutuydu (Claude'a gitmez)
    m = metin or ""
    if MOD_BIRAK_RX.search(m) and MOD["acik"]:
        moderator_bitir(_t("kullanıcı yönetimi geri aldı", "the user took over")); return True
    if MOD_BASLA_RX.search(m) and toplanti_var():
        if MOD["acik"]:  # zaten yönetiyor: yeni gündem verildiyse güncelle
            g = _mod_gundem_coz(m)
            if g: MOD.update(maddeler=g, i=0, faz="ac", t_madde=time.time(), sure_sn=_mod_sure(len(g), m)); print(f"MODERATÖR: gündem güncellendi ({len(g)} madde)")
            return True
        moderator_basla(m, kis_ad); return True
    if not MOD["acik"]: return False
    if MOD_SONRAKI_RX.search(m):
        MOD.update(faz="kapat_gec", bekle=False); print("MODERATÖR: kullanıcı — sonraki madde"); return True
    if MOD_UZAT_RX.search(m):
        dk = re.search(r"(\d+)\s*dakika", m); ek = 60 * float(dk.group(1)) if dk else 300.0
        MOD["sure_sn"] += ek; print(f"MODERATÖR: süre +{round(ek / 60)} dk"); return True
    if MOD_OZET_RX.search(m):
        MOD.update(faz="ozet_iste", bekle=False); print("MODERATÖR: kullanıcı — özet"); return True
    if MOD_BEKLE_RX.search(m): MOD["bekle"] = True; print("MODERATÖR: bekliyor (kullanıcı)"); return True
    if MOD_DEVAM_RX.search(m): MOD["bekle"] = False; print("MODERATÖR: devam"); return True
    g = _mod_gundem_coz(m)
    if g: MOD.update(maddeler=g, i=0, faz="ac", t_madde=time.time(), sure_sn=_mod_sure(len(g), m)); print(f"MODERATÖR: gündem verildi ({len(g)} madde)"); return True
    return False

def moderator_pano(komut):  # panodaki düğmeler (ses tanıma komutu kaçırırsa): sonraki | ozet | bekle | devam | birak
    if not MOD["acik"]: return {"ok": False, "err": _t("Moderatör kapalı", "Moderator is off")}
    with MOD_K:
        if komut == "sonraki": MOD.update(faz="kapat_gec", bekle=False)
        elif komut == "ozet": MOD.update(faz="ozet_iste", bekle=False)
        elif komut == "bekle": MOD["bekle"] = True
        elif komut == "devam": MOD["bekle"] = False
        elif komut == "birak": moderator_bitir(_t("kullanıcı yönetimi geri aldı (pano)", "the user took over (panel)"))
        else: return {"ok": False, "err": "komut"}
    print(f"MODERATÖR: panodan {komut}"); return {"ok": True}
def _mod_sonraki():
    MOD["i"] += 1; MOD["son_davet"] = {}
    if MOD["i"] >= len(MOD["maddeler"]): MOD["faz"] = "kapanis"
    else: MOD.update(faz="ac", t_madde=time.time())

def _mod_adim():  # bir yoklama; görev verdiyse True
    if not MOD["acik"]: return False
    if not toplanti_var(): moderator_bitir(_t("toplantı bitti", "meeting ended")); return False
    if _mod_mesgul():
        if MOD["gorev"] and time.time() - MOD["t_gorev"] > MOD_GOREV_SN: print(f"MODERATÖR: görev zaman aşımı ({MOD['gorev']})"); MOD["gorev"] = None
        return False
    if MOD["gorev"]:  # görev bitti (söylendi ya da söylenmedi)
        if MOD["gorev"] in ("ozet", "ozet_serbest"): MOD["t_karar"] = time.time()
        if MOD["gorev"] == "kapanis": moderator_bitir(_t("gündem bitti", "agenda done")); return False
        MOD["gorev"] = None
    if MOD["bekle"]: return False
    faz = MOD["faz"]; madde_var = MOD["i"] < len(MOD["maddeler"])
    if faz == "basla": MOD["faz"] = "surdur"; MOD["t_madde"] = time.time(); return _mod_gorev("basla" if MOD["maddeler"] else "basla_gundemsiz")
    if faz == "ac" and madde_var: MOD["faz"] = "surdur"; MOD["t_madde"] = time.time(); return _mod_gorev("ac")
    if faz == "kapanis": return _mod_gorev("kapanis")
    s = kanal_sessizlik()
    if faz in ("ozet_iste",) or (faz == "surdur" and time.time() - MOD["t_madde"] >= MOD["sure_sn"] and s is not None and s >= 1.5):
        MOD["faz"] = "karar"; return _mod_gorev("ozet" if madde_var else "ozet_serbest")
    if faz == "kapat_gec": MOD["t_karar"] = 0.0; _mod_sonraki(); return False
    if faz == "karar":  # özet okundu: itiraz/ekleme süresi; biri konuşuyorsa sessizlik beklenir
        if not MOD["t_karar"] or time.time() - MOD["t_karar"] < MOD_KARAR_SN or (s is not None and s < 3.0): return False
        MOD["t_karar"] = 0.0
        if madde_var: _mod_sonraki()
        else: MOD.update(faz="surdur", t_madde=time.time())  # gündemsiz: bir tur daha
        return False
    if faz != "surdur" or time.time() - MOD["t_son_mudahale"] < MOD_ARA_SN: return False
    gecen = time.time() - MOD["t_madde"]
    say, son, sure, kat = _mod_konusanlar(MOD["t_madde"])
    if son and sure >= MOD_UZUN_SN and s is not None and s >= 1.0 and len(kat) >= 2:
        return _mod_gorev("uzun", kim=son)
    if gecen >= MOD_DAVET_ORAN * MOD["sure_sn"] and s is not None and s >= 1.5:
        for k in kat:
            if k == _t("Karşı taraf", "The other side") or say.get(k): continue
            if time.time() - MOD["son_davet"].get(k, 0) < MOD_DAVET_ARA_SN: continue
            MOD["son_davet"][k] = time.time(); return _mod_gorev("davet", kim=k)
    if s is not None and s >= MOD_SESSIZ_SN and gecen >= 60: return _mod_gorev("sessiz")
    return False

def _mod_dongu():
    while True:
        time.sleep(0.2 if os.environ.get("SUFLOR_TEST_MOD_HIZLI") else 1.0)
        try:
            with MOD_K: _mod_adim()
        except Exception as e: print(f"MODERATÖR: hata {e.__class__.__name__}: {e}")
