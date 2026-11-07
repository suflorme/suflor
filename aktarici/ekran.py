# --- Paylaşılan ekranın yazısı (v0.187.0, 5 Kasım) ----------------------------------------------------------------
# Kullanıcı isteği (4 Kasım gerçek toplantısı): sunumda ekranda görünen müşteri/firma adı, başlık, rakam Claude'un bağlamına girsin, kartta ve
# cevapta kullanılsın. 4 Kasım'da 74 kendiliğinden kanıt alındı ama toplantı oturumu onları "tek tek bakma" diye görmedi, yazı okuma (yazı okuma
# da kapalıydı). Şimdi her kanıtta görüntü yerel Apple Vision ile okunur (Suflor Metin.app; görüntü ve yazı Mac'ten çıkmaz, yalnız
# Claude'a gider) — eklenti paylaşılan içeriğin yerini (`bolge`) verdiyse YALNIZ o bölge (Teams arayüzü, canlı altyazı, kameralar dışarıda):
#   · kısa özet (adlar, başlıklar, sayılar; ≤ 600 karakter) → kanit/<toplantı>/ekran.jsonl → izle "EKRAN n" olayı (toplanti-claude.py)
#   · son ekranın özeti → Konuş sorusunun bağlamı (`ekran_baglam`, bas-konus.py), yalnız süren toplantıda ve son 15 dk içindeyse
# Bölge yoksa (menü uygulamasının pencere görüntüsü, eski eklenti) EKRAN üretilmez: bütün pencerenin yazısı çoğunlukla arayüz ve altyazı
# (15 Ekim ölçümü). Gizli toplantıda kanıt zaten alınmaz; okuma sürerken gizli açılırsa yazılmaz, Konuş'a da eklenmez.
METIN_APP = os.path.join(AYAR["uygulama"], "Suflor Metin.app", "Contents", "MacOS", "SuflorMetin")
EKRAN_OZET_EN_COK = 600; EKRAN_BAGLAM_SN = 15 * 60; EKRAN_GECMIS = 8
EKRAN_SON = {}     # toplantı dosyası → {"n", "saat", "t", "ozet"}: şu an ekranda olanın özeti (Konuş)
EKRAN_YAZILAN = {}  # toplantı dosyası → [(n, özet sözcükleri, özet)] son yazılan EKRAN olayları (tekrar ayıklama)

def _bolge_temiz(b):  # eklentiden gelen {x,y,w,h} (görünen alana oran) → güvenli dörtlü ya da None
    try: x, y, w, h = (float(b[k]) for k in ("x", "y", "w", "h"))
    except (TypeError, ValueError, KeyError): return None
    if not (0 <= x < 1 and 0 <= y < 1 and 0.05 <= w <= 1.001 and 0.05 <= h <= 1.001): return None
    return {"x": round(x, 4), "y": round(y, 4), "w": round(min(w, 1 - x), 4), "h": round(min(h, 1 - y), 4)}

def ekran_oku(fp, bolge=None):  # → satır listesi (yukarıdan aşağı) ya da None (okunamadı)
    arg = [METIN_APP, fp] + (["--bolge", ",".join(str(bolge[k]) for k in ("x", "y", "w", "h"))] if bolge else [])
    try: o = json.loads(subprocess.run(arg, capture_output=True, text=True, timeout=90).stdout or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired) as e: return None, e.__class__.__name__
    return [" ".join(str(x).split()) for x in (o.get("satirlar") or []) if str(x).strip()], o.get("hata")

_EKRAN_SAYI = re.compile(r"\d")
_EKRAN_AD = re.compile(r"(?:^|\s)[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ&.'-]+")
def ekran_ozet(satirlar, en_cok=EKRAN_OZET_EN_COK):
    # Kısa özet: ilk 3 satır (başlık), sayı ya da büyük harfle başlayan sözcük (ad, firma) geçen satırlar önce; sonra kalanlar. Sıra
    # ekrandaki gibi (yukarıdan aşağı) korunur, satır en çok 120 karakter, toplam ≤ en_cok. Tek harfli ve tekrarlanan satır atılır.
    gor, sat = set(), []
    for s in satirlar:
        s = " ".join(str(s).split()).replace("|", "¦")
        if len(s) < 2 or not re.search(r"\w\w", s) or s.lower() in gor: continue
        gor.add(s.lower()); sat.append(s[:120].rsplit(" ", 1)[0] + " …" if len(s) > 120 else s)
    puan = lambda i, s: 3 if i < 3 else 2 if _EKRAN_SAYI.search(s) or len(_EKRAN_AD.findall(s)) >= (1 if len(s) <= 40 else 2) else 1
    sec, top = set(), 0
    for i, s in sorted(enumerate(sat), key=lambda x: (-puan(*x), x[0])):
        if top + len(s) + 3 > en_cok: continue
        sec.add(i); top += len(s) + 3
    return " · ".join(s for i, s in enumerate(sat) if i in sec)

def ekran_gorsel(satirlar):
    # Görsel ağırlıklı mı (grafik, tablo, diyagram, beyaz tahta): yazı okuması görüntüyü anlatmaya yetmez → izle olayına işaret, Claude Read ile bakar.
    # Ölçülebilir kural (ilk eşleşen): yazı yok (toplam < 15 karakter) · az yazı (< 150 karakter ya da < 6 satır) · çok sayı (rakamlar harf+rakamın ≥ %30'u ve ≥ 15 rakam) ·
    # tablo (≥ 4 satırda ikişer ya da daha çok sayı simgesi). Boş dize: yazı ağırlıklı (slayt metni), görüntüye bakmaya gerek yok.
    sat = [" ".join(str(s).split()) for s in (satirlar or []) if str(s).strip()]; top = sum(len(s) for s in sat)
    if top < 15: return "yazı yok"
    if top < 150 or len(sat) < 6: return "az yazı"
    rak = sum(c.isdigit() for c in "".join(sat)); har = sum(c.isalnum() for c in "".join(sat))
    if rak >= 15 and har and rak / har >= 0.30: return "çok sayı"
    if sum(1 for s in sat if len(re.findall(r"\d[\d.,%]*", s)) >= 2) >= 4: return "tablo"
    return ""

def _ekran_soz(s): return {w for w in re.findall(r"\w+", (s or "").lower()) if len(w) > 1}

def kanit_isle(md, rel, n, saat, bolge=None, ekran=False):  # kanıt kaydedilince ayrı iş parçacığında (relay.py kanit())
    bolge = _bolge_temiz(bolge) if bolge else None
    if not os.access(METIN_APP, os.X_OK) or ekran: return  # ekran: kullanıcının o an baktığı pencere — toplantı ekranı değil
    if not bolge: return
    s, hata = ekran_oku(os.path.join(BASE, rel), bolge)
    if s is None: print(f"KANIT {n} METNİ: okunamadı ({hata})"); return
    if not s:
        print(f"KANIT {n} METNİ: yazı yok" + (f" ({hata})" if hata else "") + (" · bölge" if bolge else ""))
        if bolge and not hata and not gizli_acik(): ekran_kaydet(md, rel, n, saat, "", "yazı yok")  # grafik/beyaz tahta: yazı yok ama görüntü anlamlı olabilir
        return
    if gizli_acik(): return
    if bolge: ekran_kaydet(md, rel, n, saat, ekran_ozet(s), ekran_gorsel(s))

def ekran_kaydet(md, rel, n, saat, ozet, gorsel=""):
    # EKRAN olayı: son yazılanla neredeyse aynıysa (sözcüklerin ≥ %90'ı ortak) yazılmaz; son 8 olaydan biriyle aynıysa "KANIT k ile aynı"
    # (açılır pencere kapanıp önceki ekrana dönüldü) — metin yinelenmez. Konuş için şu anki ekran her durumda güncellenir.
    if not ozet and not gorsel: return
    try:
        if gizli_acik(): return  # gizli toplantıda ne özet ne görüntü yolu yazılır
    except NameError: pass
    k = os.path.basename(md); sz = _ekran_soz(ozet); gec = EKRAN_YAZILAN.setdefault(k, [])
    benzer = lambda a: (not sz and not a) or (len(sz | a) and len(sz & a) / len(sz | a) >= 0.9)
    with LOCK:
        EKRAN_SON[k] = {"n": n, "saat": saat, "t": time.time(), "ozet": ozet, "gorsel": rel, "gorsel_neden": gorsel}
        if gec and benzer(gec[-1][1]): print(f"EKRAN {n}: yazı öncekiyle aynı — olay yok"); return
        es = next((x for x in reversed(gec[:-1]) if benzer(x[1])), None)
        rec = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "n": n, "saat": saat, "gorsel": rel, **({"ayni": es[0]} if es else {"ozet": ozet, **({"gorsel_neden": gorsel} if gorsel else {})})}
        gec.append((n, sz, ozet)); del gec[:-EKRAN_GECMIS]
        write([(os.path.join(BASE, "kanit", k[:-3], "ekran.jsonl"), json.dumps(rec, ensure_ascii=False) + "\n")])
    print(f"EKRAN {n}: " + (f"KANIT {es[0]} ile aynı yazı" if es else f"{len(ozet)} karakter özet"))

def ekran_baglam():  # Konuş sorusunun [Bağlam]'ına: süren toplantıda son 15 dk içindeki ekranın özeti (gizli toplantıda yok)
    try:
        f = aktif_dosya()
        if not f or gizli_acik(): return ""
    except NameError: return ""
    e = EKRAN_SON.get(f)
    if not e or time.time() - e["t"] > EKRAN_BAGLAM_SN: return ""
    yol = os.path.join(BASE, e["gorsel"]) if e.get("gorsel_neden") and e.get("gorsel") else ""  # S220: görsel ağırlıklı ekranda görüntü yolu (Konuş Read ile açabilir; yalnız kullanıcı ekranı soruyorsa)
    return _t(f"Paylaşılan ekranda son görünen yazı (KANIT {e['n']}, {e['saat']}; yerel okundu, okuma hatası olabilir): {e['ozet'] or '(yazı yok)'}\n"
              + (f"Bu ekran görsel ağırlıklı ({e['gorsel_neden']}); kullanıcı ekranda ne olduğunu ya da tabloyu/grafiği yorumlamanı isterse görüntüyü Read ile aç: {yol}\n" if yol else ""),
              f"Text last seen on the shared screen (evidence {e['n']}, {e['saat']}; read locally, may contain recognition errors): {e['ozet'] or '(no text)'}\n"
              + (f"This screen is visual-heavy ({e['gorsel_neden']}); if the user asks what is on screen or to interpret the table/chart, open the image with Read: {yol}\n" if yol else ""))
