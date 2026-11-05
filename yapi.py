#!/usr/bin/env python3
# Suflor.me — toplantı yapısı (v0.27.0, Faz 5): karar grafı + zihin haritası. toplanti-claude.py yapi/graf komutları bunu içe aktarır.
# Toplantı sonunda Claude özetle birlikte yapı dosyasını yazar (<özet>.yapi.json; biçim YAPI_ORNEK). Buradan:
#  - karar grafı: canli/karar-grafi.sqlite (yalnız bu Mac; başka kayıt sistemine yazılmaz) — kişi → karar/iddia/iş/söz → tarih → kaynak (toplantı, saat).
#    Hazırlıkta ve toplantıda (KATILIMCI olayı) kişinin geçmiş iddiaları ve açık işleri; Claude çelişkiyi aramadan graftan görür.
#  - zihin haritası: <özet>-zihin-haritasi.html (tek dosya, çevrimdışı; NotebookLM benzeri: merkezde toplantı, dallar gündem maddeleri,
#    altında karar · iş · açık soru · sayı · iddia; düğüm açılır/kapanır, yaprağa dokununca alıntı ve saat; "Resim olarak indir" PNG).
#  - sözler defteri (v0.32.8, S44): ayrı dosya değil, grafın iş/söz kayıtları ("sN" = kayıt kimliği); eski sozler.json bir kez taşınır.
#    Eylem kuyruğunun dış işleri (takvim, e-posta, takip, mesaj) grafa kullanıcının işi olarak bağlanır (bag "eylem:eN"), durumu kuyruktan izlenir.
# Python 3.9, yalnız standart kütüphane. Metinler veridir; HTML'e kaçışlı (JSON) gömülür.
import datetime, html, json, os, re, sqlite3
TURLER = {"karar": "Karar", "is": "İş", "soru": "Açık soru", "sayi": "Sayı", "iddia": "İddia", "soz": "Söz"}
YAPI_ORNEK = {"baslik": "Ayşe — bütçe", "tarih": "2026-10-11", "gorsel": "karar_is", "maddeler": [
    {"baslik": "Bütçe", "durum": "konuşuldu", "ogeler": [
        {"tur": "karar", "metin": "Bütçe 120 bin olarak kalıyor", "kim": "Ayşe Yılmaz", "saat": "10:12:30", "alinti": "120'de kalalım",
         "netlik": "ortuk", "varsayim": "Kur yıl sonuna kadar aynı kalır"},
        {"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "tarih": "2026-10-17", "saat": "10:15:02"},
        {"tur": "soz", "metin": "Geçen yılın faturalarını gönderecek", "sahip": "Ayşe Yılmaz", "tarih": "2026-10-14"},
        {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Ali K", "cevap": "Hayır, KDV hariç", "kaynak": "proje belgesi: teklif.pdf"},
        {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Yılmaz", "saat": "10:11:00", "cevap": "Kısmen doğru: 92 bin", "kaynak": "Metrik kaynağı · get_metrics · Ekim 2026",
         "kaynak_url": "https://ornek.example/rapor"}]}],
    "oneri": "Gündemi bir gün önce gönder",
    "eposta_yeterdi": {"deger": False, "gerekce": ""},
    "duzeltmeler": [{"saat": "10:14:05", "yanlis": "Bora Kaplan", "dogru": "Bora Kaya"}, {"saat": "10:12:41", "yanlis": "on iki bin", "dogru": "yüz yirmi bin"}],
    "dokum_notu": "10:20–10:22 karşı tarafın sesi kesikti; o aradaki satırlar eksik"}
# "gorsel" (5 Kasım): toplantı sonu görselinin türü, özeti yazan Claude belirler — "karar_is" (karar ve iş panosu; varsayılan) ya da "harita" (zihin haritası:
# karar/iş çıkmayan keşif, beyin fırtınası, tanışma). soru/sayi/iddia öğelerinde isteğe bağlı "cevap" (doğru/yanlış/kısmen + değer ya da kısa net cevap),
# "kaynak" (nereden doğrulandı), "kaynak_url" (yalnız http/https). Bulunamayan alan boş bırakılır; uydurulmaz. Görselde öğenin altında etiket olur.
# Defter turu (S48, v0.35.0): toplantı sonunda oturum yapı dosyasına "duzeltmeler" (Whisper'ın yanlış duyduğu ad/sayı/terim: dökümdeki biçim → doğrusu,
# satır saatiyle; yalnız bağlamdan emin olunanlar) ve "dokum_notu" (boşluk, kesinti, güvenilmez aralık) ekler. bitir kaynak saatlerini dökümde doğrular
# (kaynak_dogrula); yapı dosyası aktarıcıya gider ve toplantı defterine "Toplantı sonu: kararlar, işler, düzeltmeler" bölümü olarak girer (Konuş okur).
def _sn(s):
    try: h, m, *x = [int(p) for p in str(s).strip().split(":")]; return h * 3600 + m * 60 + (x[0] if x else 0)
    except ValueError: return None
def kaynak_dogrula(v, saatler, pay=90):
    # → [(öge, sorun)]: karar/iş/söz/iddia saati dökümde (± pay sn) yoksa; karar ve iş saatsizse. saatler: dökümdeki satır saatleri ("HH:MM:SS")
    ss = sorted(x for x in (_sn(s) for s in saatler) if x is not None); sorun = []
    import bisect
    for m in v["maddeler"]:
        for o in m["ogeler"]:
            if o["tur"] not in ("karar", "is", "soz", "iddia"): continue
            t = _sn(o.get("saat")) if o.get("saat") else None
            if t is None:
                if o["tur"] in ("karar", "is") and o.get("saat") is None: sorun.append((o, "kaynak saati yok"))
                elif o.get("saat"): sorun.append((o, f"saat okunamadı ({o['saat']})"))
                continue
            i = bisect.bisect_left(ss, t - pay)
            if not (i < len(ss) and ss[i] <= t + pay): sorun.append((o, f"{o['saat']} dökümde yok (± {pay} sn)"))
    for d in v.get("duzeltmeler") or []:
        if not isinstance(d, dict) or not d.get("yanlis") or not d.get("dogru"): sorun.append(({"tur": "duzeltme", "metin": str(d)[:60]}, "düzeltmede yanlis/dogru eksik"))
    return sorun
def kucuk(t): return str(t).replace("İ", "i").replace("I", "ı").lower()
# "Gerçekten anlaştınız mı?" (Faz 6 #6): kararın netliği — acik (taraflar açıkça onayladı) · ortuk (itiraz yok ama kimse açıkça "tamam"
# demedi) · tek (bir kişi söyledi, öteki cevap vermedi); varsayim = kararın dayandığı, toplantıda konuşulmamış koşul (yalnız dökümde
# dayanağı varsa). Örtük/tek ya da varsayımlı karar toplantı sonunda kullanıcıya sorulur; grafta "teyit bekliyor" işaretiyle kalır.
def teyit_kararlar(v):
    return [o for m in v["maddeler"] for o in m["ogeler"] if o["tur"] == "karar"
            and (kucuk(o.get("netlik") or "").replace("ö", "o").replace("ü", "u") in ("ortuk", "tek") or str(o.get("varsayim") or "").strip())]
def teyit_neden(o):
    n = kucuk(o.get("netlik") or "").replace("ö", "o").replace("ü", "u"); va = " ".join(str(o.get("varsayim") or "").split())[:200]
    return "; ".join(x for x in ({"ortuk": "örtük kabul (kimse açıkça onaylamadı)", "tek": "tek taraflı (öteki taraf cevap vermedi)"}.get(n, ""),
                                 f"varsayım: {va}" if va else "") if x)
def oku(yol):
    v = json.load(open(yol, encoding="utf-8"))
    if not isinstance(v, dict) or not isinstance(v.get("maddeler"), list): raise ValueError("yapı dosyası: {\"baslik\", \"tarih\", \"maddeler\": [...]} bekleniyor")
    for m in v["maddeler"]:
        m["ogeler"] = [o for o in (m.get("ogeler") or []) if isinstance(o, dict) and o.get("tur") in TURLER and str(o.get("metin") or "").strip()]
    return v
# --- karar grafı -----------------------------------------------------------------------------------------------------
def _db(dizin):
    yol = os.path.join(dizin, "karar-grafi.sqlite"); yeni = not os.path.exists(yol)
    c = sqlite3.connect(yol)
    c.execute("""CREATE TABLE IF NOT EXISTS kayit (id INTEGER PRIMARY KEY, toplanti TEXT, baslik TEXT, tarih TEXT, madde TEXT, tur TEXT,
                 kim TEXT, sahip TEXT, metin TEXT, son_tarih TEXT, saat TEXT, alinti TEXT, durum TEXT DEFAULT 'acik', eklendi TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS kayit_kim ON kayit (kim)"); c.execute("CREATE INDEX IF NOT EXISTS kayit_sahip ON kayit (sahip)")
    if "bag" not in [x[1] for x in c.execute("PRAGMA table_info(kayit)")]: c.execute("ALTER TABLE kayit ADD COLUMN bag TEXT")  # söz/eylem bağı
    if yeni: os.chmod(yol, 0o600)
    return c
def graf_yaz(dizin, v, toplanti):
    # aynı toplantı yeniden yazılırsa eski kayıtları yerine geçer
    c = _db(dizin); n = 0
    with c:
        c.execute("DELETE FROM kayit WHERE toplanti = ? AND bag IS NULL", (toplanti,))  # elle eklenen söz ve eylem bağları kalır
        teyitler = teyit_kararlar(v)
        for m in v["maddeler"]:
            for o in m["ogeler"]:
                c.execute("INSERT INTO kayit (toplanti, baslik, tarih, madde, tur, kim, sahip, metin, son_tarih, saat, alinti, eklendi, durum) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (toplanti, str(v.get("baslik") or "")[:200], str(v.get("tarih") or "")[:10], str(m.get("baslik") or "")[:200], o["tur"],
                           str(o.get("kim") or "")[:80] or None, str(o.get("sahip") or "")[:80] or None,
                           (str(o["metin"])[:500] + (f" (teyit bekliyor — {teyit_neden(o)})" if o["tur"] == "karar" and o in teyitler else ""))[:600], str(o.get("tarih") or "")[:20] or None,
                           str(o.get("saat") or "")[:8] or None, str(o.get("alinti") or "")[:300] or None, datetime.datetime.now().isoformat(timespec="seconds"),
                           "cevaplandi" if o["tur"] == "soru" and str(o.get("cevap") or "").strip() else "acik"))  # 5 Kasım: cevabı yazılmış soru açık sayılmaz (Kararlar ve işler → Açık sorular)
                n += 1
    c.close(); return n
def _ilk(ad): return (str(ad or "").split() or [""])[0].casefold()
def graf_kisi(dizin, kim, n=5, haric=None):
    # kişinin (ad ya da ilk adı) son iddia/karar/sözleri ve sahibi olduğu açık işler — yeni toplantıdan önce
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")) or not kim: return []
    c = _db(dizin); ilk = _ilk(kim)
    rs = c.execute("SELECT tarih, tur, kim, sahip, metin, son_tarih, baslik, saat, toplanti FROM kayit WHERE durum = 'acik' ORDER BY tarih DESC, id DESC LIMIT 2000").fetchall()
    c.close()
    out = [r for r in rs if r[8] != haric and (_ilk(r[2]) == ilk or _ilk(r[3]) == ilk) and r[1] in ("iddia", "karar", "is", "soz", "sayi")]
    return out[:n]
def graf_satir(r):
    tarih, tur, kim, sahip, metin, son, baslik, saat = r[:8]
    return f"{tarih} {kucuk(TURLER.get(tur, tur))}: {metin}" + (f" (sahip {sahip}" + (f", {son}" if son else "") + ")" if tur == "is" and sahip else "") + f" — {baslik}"
def graf_liste(dizin, kim=None, n=20):
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return []
    if kim: return graf_kisi(dizin, kim, n)
    c = _db(dizin); rs = c.execute("SELECT tarih, tur, kim, sahip, metin, son_tarih, baslik, saat, toplanti FROM kayit ORDER BY tarih DESC, id DESC LIMIT ?", (n,)).fetchall(); c.close()
    return rs
def graf_sil(dizin, toplanti=None, hepsi=False):
    yol = os.path.join(dizin, "karar-grafi.sqlite")
    if not os.path.exists(yol): return 0
    if hepsi: os.remove(yol); return -1
    c = _db(dizin)
    with c: n = c.execute("DELETE FROM kayit WHERE toplanti = ?", (toplanti,)).rowcount
    c.close(); return n
def cikti_say(v):
    # toplantı çıktısı sayıları yapı dosyasından: karar · iş (iş + söz) · tarihsiz (tarihi olmayan iş/söz; panoda "4 iş · 2'si tarihsiz") ·
    # açık (açık soru varsa yalnız soru sayısı; soru yoksa konuşulmayan/kısmen madde — 5 Kasım: ikisi toplanınca "açık" özetteki sayıyla tutmuyordu)
    og = [o for m in v["maddeler"] for o in m["ogeler"]]; isler = [o for o in og if o["tur"] in ("is", "soz")]
    soru = sum(o["tur"] == "soru" for o in og)
    acik_madde = sum(1 for m in v["maddeler"] if kucuk(m.get("durum") or "") in ("açık", "acik", "kısmen", "kismen", "konuşulmadı", "konusulmadi"))
    return {"karar": sum(o["tur"] == "karar" for o in og), "is": len(isler), "tarihsiz": sum(1 for o in isler if not o.get("tarih")), "acik": soru or acik_madde}
def sayi_iyelik(n):  # sayının Türkçe iyelik eki: 2 → "'si" (2'si tarihsiz), 3 → "'ü", 10 → "'u"; 0–99
    n = int(n); b = n % 10
    return ({1: "'i", 2: "'si", 3: "'ü", 4: "'ü", 5: "'i", 6: "'sı", 7: "'si", 8: "'i", 9: "'u"}.get(b) if b else
            {0: "'ı", 10: "'u", 20: "'si", 30: "'u", 40: "'ı", 50: "'si", 60: "'ı", 70: "'i", 80: "'i", 90: "'ı"}.get(n % 100)) or "'i"
# "Bu toplantı e-postayla çözülebilir" (5 Kasım): yöneticinin zamanını korumak. İki an, ikisi de yalnız GÜÇLÜ işarette söyler (yanlış pozitif pahalı).
#  - toplantı öncesi: eposta_isaret(gündem maddeleri, başlık, kişi sayısı) kural tabanlı işaret verir (tc hazirlik "## E-posta yeterli mi?");
#    son kararı hazırlığı yapan Claude verir (geçmiş toplantılar, takvim notu dahil).
#  - toplantı sonu: yapı dosyasında "eposta_yeterdi": {"deger": bool, "gerekce": "…"}; eposta_yeterdi() kararsız/çelişkili değeri (karar çıkmışken true) düşürür.
BILGI_RX = re.compile(r"bilgilendirme|bilgi paylaşım|bilgi aktar|durum (?:güncelleme|raporu|paylaşım|özeti)|güncelleme|haftalık özet|aylık özet|duyuru|tanıtım|sunum|status|update|fyi|announcement|readout|share[- ]?out|briefing|recap", re.I)
KARAR_RX = re.compile(r"karar|onay|tartış|değerlendir|seç(?:im|enek)|öncelik|strateji|plan(?:lama)?\b|bütçe|pazarlık|müzakere|görüşme|beyin fırtınası|workshop|çalıştay|geri bildirim|retro|çöz(?:üm)?\b|sorun|decid|decision|approve|approval|discuss|brainstorm|negotiat|prioriti|review|feedback|align|plan\b|budget|problem|options?", re.I)
def eposta_isaret(maddeler, baslik="", kisi=None):
    # → {"guclu": bool, "nedenler": [..]}; maddeler: gündem metinleri. Güçlü: ≥1 madde, hepsi bilgi aktarımı kalıbında, hiçbirinde karar/tartışma kalıbı yok,
    # başlıkta karar/tartışma kalıbı yok, kişi sayısı biliniyorsa ≥ 3 (iki kişilik toplantı çoğunlukla ilişki/ayardır, e-postaya çevrilmez).
    m = [" ".join(str(x).split()) for x in (maddeler or []) if str(x).strip()]; ned = []
    bil = [x for x in m if BILGI_RX.search(x)]; kar = [x for x in m if KARAR_RX.search(x)]
    if not m: return {"guclu": False, "nedenler": ["gündem yok: işaret yok"]}
    if kar: ned.append(f"{len(kar)} gündem maddesi karar/tartışma kalıbında: " + "; ".join(x[:50] for x in kar[:3]))
    if len(bil) < len(m): ned.append(f"{len(m) - len(bil)}/{len(m)} madde bilgi aktarımı olarak açık değil")
    if baslik and KARAR_RX.search(baslik): ned.append("başlık karar/tartışma kalıbında")
    if kisi is not None and kisi < 3: ned.append(f"{kisi} kişilik toplantı")
    if ned: return {"guclu": False, "nedenler": ned}
    return {"guclu": True, "nedenler": [f"{len(m)}/{len(m)} gündem maddesi bilgi aktarımı" + (f"; {kisi} katılımcı" if kisi else "")]}
def eposta_yeterdi(v):
    # özet yapısından → (deger, gerekce, uyari). Karar çıkmışsa true düşer (özetin kendi sayısıyla çelişemez); gerekçesiz true geçmez.
    e = v.get("eposta_yeterdi")
    if not isinstance(e, dict): return False, "", "yok"
    g = " ".join(str(e.get("gerekce") or "").split())[:240]
    if e.get("deger") is not True: return False, "", ""
    if cikti_say(v)["karar"] > 0: return False, "", "karar çıkmış: eposta_yeterdi geçersiz"
    if not g: return False, "", "gerekçe yok: eposta_yeterdi geçersiz"
    return True, g, ""
def eksik_isler(v):  # sahibi ya da tarihi olmayan iş/söz (bitir uyarısı)
    return [o for m in v["maddeler"] for o in m["ogeler"] if o["tur"] in ("is", "soz") and (not (o.get("sahip") or o.get("kim")) or not o.get("tarih"))]
# --- sözler defteri: grafın iş/söz kayıtları -------------------------------------------------------------------------
def soz_dict(row):
    i, tarih, tur, kim, sahip, metin, son, baslik, durum, eklendi = row
    return {"id": f"s{i}", "kim": sahip or kim, "metin": metin, "tarih": son, "durum": durum, "toplanti": baslik, "at": eklendi or tarih, "tur": tur}
def sozler(dizin, kim=None):
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return []
    c = _db(dizin)
    rs = c.execute("SELECT id, tarih, tur, kim, sahip, metin, son_tarih, baslik, durum, eklendi FROM kayit WHERE tur IN ('is', 'soz') ORDER BY id").fetchall(); c.close()
    ilk = _ilk(kim) if kim else None
    return [soz_dict(x) for x in rs if not ilk or _ilk(x[4] or x[3]) == ilk or (kim and kucuk(kim) in kucuk(x[4] or x[3] or ""))]
def soz_ekle(dizin, kim, metin, tarih=None, toplanti=None, baslik=None):
    c = _db(dizin)
    with c:
        i = c.execute("INSERT INTO kayit (toplanti, baslik, tarih, madde, tur, kim, sahip, metin, son_tarih, eklendi, bag) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (toplanti, baslik, datetime.date.today().isoformat(), None, "soz", None, kim, metin, tarih, datetime.datetime.now().isoformat(timespec="seconds"), "soz")).lastrowid
    x = soz_dict(c.execute("SELECT id, tarih, tur, kim, sahip, metin, son_tarih, baslik, durum, eklendi FROM kayit WHERE id = ?", (i,)).fetchone()); c.close(); return x
def soz_kapat(dizin, sid, durum):
    if not re.fullmatch(r"s\d+", sid or "") or not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return None
    c = _db(dizin)
    with c: n = c.execute("UPDATE kayit SET durum = ? WHERE id = ? AND tur IN ('is', 'soz')", (durum, int(sid[1:]))).rowcount
    x = c.execute("SELECT id, tarih, tur, kim, sahip, metin, son_tarih, baslik, durum, eklendi FROM kayit WHERE id = ?", (int(sid[1:]),)).fetchone(); c.close()
    return soz_dict(x) if n and x else None
# --- Bugün sayfası ve arşiv MCP'nin ortak okuma/yazma yardımcıları (tek kaynak: pano ucu /bugun-veri, /karar-onay, /is-durum ve arsiv-mcp.py) ---
GIZLI_RX = re.compile(r"\|\s*\*\*GİZLİ\*\*\s*\|")
TEYIT_RX = re.compile(r"\s*\(teyit bekliyor(?:\s*[—-]\s*(.*))?\)\s*$")  # graf_yaz ekler; içinde iç içe parantez olabilir
ID_RX = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}-[^/\\]+$")
_GIZLI = {}  # (dizin, id) → (mtime, boyut, gizli mi)
def son_kayitlar(dizin):  # son-toplantilar.jsonl: dosya adı → son kayıt
    o = {}
    try:
        with open(os.path.join(dizin, "son-toplantilar.jsonl"), encoding="utf-8") as fh:
            for ln in fh:
                try: r = json.loads(ln)
                except ValueError: continue
                if isinstance(r, dict) and r.get("dosya"): o[str(r["dosya"])] = r
    except OSError: pass
    return o
def gizli_mi(dizin, i, kayitlar=None):  # kayıtta gizli: true ya da dökümde **GİZLİ** satırı; tanınmayan kimlik gösterilmez
    i = str(i or "")
    if i.endswith(".md"): i = i[:-3]
    if not ID_RX.match(i): return True
    r = (kayitlar if kayitlar is not None else son_kayitlar(dizin)).get(i + ".md") or {}
    if r.get("gizli"): return True
    yol = os.path.join(dizin, i + ".md")
    try: st = os.stat(yol)
    except OSError: return False
    on = _GIZLI.get((dizin, i))
    if on and on[0] == st.st_mtime and on[1] == st.st_size: return on[2]
    g = False
    try:
        with open(yol, encoding="utf-8", errors="replace") as fh: g = any(GIZLI_RX.search(ln) for ln in fh)
    except OSError: pass
    _GIZLI[(dizin, i)] = (st.st_mtime, st.st_size, g); return g
def kayit_bul(dizin, kimlik, turler):  # "k12" / "s7" / "q3" → (sözlük ya da None); gizli toplantıdaysa yok sayılır
    m = re.fullmatch(r"([ksq])(\d+)", str(kimlik or ""))
    if not m or not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return None
    c = _db(dizin)
    try: r = c.execute("SELECT id, toplanti, baslik, tarih, tur, kim, sahip, metin, son_tarih, saat, durum FROM kayit WHERE id = ?", (int(m.group(2)),)).fetchone()
    finally: c.close()
    if not r or r[4] not in turler or (r[1] and gizli_mi(dizin, r[1])): return None
    return {"id": f"{ {'karar': 'k', 'soru': 'q'}.get(r[4], 's') }{r[0]}", "toplanti": r[1], "baslik": r[2], "tarih": r[3], "tur": r[4], "kim": r[5], "sahip": r[6], "metin": r[7], "son_tarih": r[8], "durum": r[10]}
def karar_yaz(dizin, kimlik, metin):  # kararın metnini değiştirir (onay/düzeltme) → kayıt sayısı
    c = _db(dizin)
    try:
        with c: return c.execute("UPDATE kayit SET metin = ? WHERE id = ? AND tur = 'karar'", (str(metin)[:600], int(str(kimlik)[1:]))).rowcount
    finally: c.close()
def karar_teyit_kaldir(dizin, kimlik):  # "(teyit bekliyor — …)" ekini kaldırır → yeni metin ya da None (kayıt yok/gizli/ek yok)
    x = kayit_bul(dizin, kimlik, ("karar",))
    if not x or not TEYIT_RX.search(x["metin"]): return None
    yeni = TEYIT_RX.sub("", x["metin"])
    return yeni if karar_yaz(dizin, x["id"], yeni) else None
def _vade_gun(v, bugun):  # ISO tarih → bugüne kalan gün (negatif: gecikti); serbest metin ("cuma") → None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v or "")): return None
    try: return (datetime.date.fromisoformat(v) - bugun).days
    except ValueError: return None
def teyit_neden_sade(n):  # grafta tutulan iç terim → kullanıcı dili (Bugün satırı): "örtük kabul (kimse açıkça onaylamadı)" → "kimse açıkça onaylamadı"
    out = []
    for p in re.split(r";\s*", str(n or "")):
        p = p.strip()
        if not p: continue
        if p.startswith("örtük"): out.append("kimse açıkça onaylamadı")
        elif p.startswith("tek taraflı"): out.append("karşı taraf cevap vermedi")
        elif p.startswith("varsayım:"): out.append("varsayıma dayanıyor: " + p[len("varsayım:"):].strip())
        else: out.append(p)
    return "; ".join(out)
# --- dış karar kaydı (5 Kasım; kullanıcı kararı: önce okuma + dışa aktarma, dışarıya kendiliğinden yazma yok) -----------------------------------------
# Ayar dis_defter: [{"ad", "tur": "dosya", "yol": "~/…/kararlar.csv"} | {"ad", "tur": "mcp", "sunucu", "url", "araclar": [...]}]. Dosya türü burada okunur:
# CSV (virgül, noktalı virgül ya da sekme; başlık satırı zorunlu) ya da JSON (liste ya da liste alanları olan sözlük). Kayıtlar Suflor'un grafına girmez — ayrı,
# salt-okunur katman; Bugün'de ve hazırlıkta kaynak etiketiyle görünür. mcp türünü toplantı oturumu ve Konuş bilgi kaynağı olarak (yalnız okuma) kullanır.
DD_ALAN = {"tarih": ("tarih", "date", "created", "olusturma", "olusturuldu", "kayit tarihi"), "toplanti": ("toplanti", "meeting", "kaynak", "source", "oturum"),
           "tur": ("tur", "type", "kind", "kategori", "category"), "metin": ("metin", "text", "karar", "decision", "is", "task", "title", "baslik", "aciklama", "description", "item", "ozet", "summary", "konu", "subject"),
           "sahip": ("sahip", "owner", "assignee", "sorumlu", "kim", "who", "assigned to", "assigned_to", "atanan"), "vade": ("vade", "due", "due date", "due_date", "son tarih", "son_tarih", "deadline", "termin", "bitis", "hedef tarih"),
           "durum": ("durum", "status", "state")}
DD_KAPALI = {"yapildi", "done", "closed", "kapandi", "kapali", "tamam", "tamamlandi", "completed", "complete", "iptal", "cancelled", "canceled", "bitti", "resolved", "tutuldu"}
DD_EN_COK = 500
def _dd_norm(s): return re.sub(r"\s+", " ", kucuk(str(s or "")).replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")).strip()
def _dd_tur(t, satir):
    t = _dd_norm(t)
    if re.search(r"karar|decision", t): return "karar"
    if re.search(r"\bis\b|task|action|todo|gorev|yapilacak|soz|promise", t): return "is"
    if re.search(r"soru|question", t): return "soru"
    return "is" if (satir.get("sahip") or satir.get("vade")) else "karar"
def _dd_satir(r, tur_ipucu=""):
    if not isinstance(r, dict): return None
    h = {_dd_norm(k): v for k, v in r.items() if k is not None}; o = {}
    for alan, adlar in DD_ALAN.items():
        for a in adlar:
            if a in h and str(h[a] or "").strip(): o[alan] = " ".join(str(h[a]).split())[:300 if alan == "metin" else 80]; break
    if not o.get("metin"): return None
    o["tur"] = _dd_tur(o.get("tur") or tur_ipucu, o)
    o["kapali"] = _dd_norm(o.get("durum")) in DD_KAPALI
    for k in ("tarih", "toplanti", "sahip", "vade", "durum"): o.setdefault(k, "")
    return o
def dis_defter_oku(yol):
    # → {"ok": bool, "kayitlar": [{tarih, toplanti, tur, metin, sahip, vade, durum, kapali}], "hata": ""}; dosya yoksa/bozuksa ok False, hata kısa metin (kullanıcıya gider)
    import csv
    y = os.path.expanduser(str(yol or "").strip()); out = []
    if not y: return {"ok": False, "kayitlar": [], "hata": "dosya yolu boş"}
    uz = os.path.splitext(y)[1].lower()
    if uz not in (".csv", ".tsv", ".json"): return {"ok": False, "kayitlar": [], "hata": "yalnız .csv, .tsv ya da .json"}
    try:
        if os.path.getsize(y) > 20_000_000: return {"ok": False, "kayitlar": [], "hata": "dosya çok büyük (20 MB üstü)"}
        with open(y, encoding="utf-8-sig", errors="replace", newline="") as fh: ham = fh.read()
    except OSError as e: return {"ok": False, "kayitlar": [], "hata": f"dosya okunamadı ({e.__class__.__name__})"}
    if uz == ".json":
        try: v = json.loads(ham)
        except ValueError: return {"ok": False, "kayitlar": [], "hata": "JSON okunamadı"}
        listeler = [("", v)] if isinstance(v, list) else [(k, x) for k, x in v.items() if isinstance(x, list)] if isinstance(v, dict) else []
        if not listeler: return {"ok": False, "kayitlar": [], "hata": "JSON'da kayıt listesi yok"}
        for ad, l in listeler:
            for r in l:
                s = _dd_satir(r, ad)
                if s: out.append(s)
                if len(out) >= DD_EN_COK: break
    else:
        try:
            ilk = ham.splitlines()[0] if ham.strip() else ""
            ayrac = "\t" if uz == ".tsv" or ilk.count("\t") > ilk.count(",") else ";" if ilk.count(";") > ilk.count(",") else ","
            rd = csv.DictReader(ham.splitlines(), delimiter=ayrac)
            if not rd.fieldnames or not any(_dd_norm(f) in DD_ALAN["metin"] for f in rd.fieldnames): return {"ok": False, "kayitlar": [], "hata": "başlık satırında metin/karar/iş sütunu yok"}
            for r in rd:
                s = _dd_satir(r)
                if s: out.append(s)
                if len(out) >= DD_EN_COK: break
        except csv.Error: return {"ok": False, "kayitlar": [], "hata": "CSV okunamadı"}
    return {"ok": True, "kayitlar": out, "hata": ""}
def dis_defter_veri(ayar, kim=None, n=50):
    # Bugün/hazırlık için: ayar dis_defter listesindeki dosya türlerinin açık kayıtları (kapalı olanlar sayılır, listelenmez); kim verilirse o kişinin (ilk ad) kayıtları önce
    out = []
    for d in (ayar or []) if isinstance(ayar, list) else []:
        if not isinstance(d, dict) or str(d.get("tur") or "dosya") != "dosya": continue
        ad = " ".join(str(d.get("ad") or "").split())[:40] or os.path.basename(str(d.get("yol") or ""))[:40] or "dış defter"
        r = dis_defter_oku(d.get("yol")); ks = [x for x in r["kayitlar"] if not x["kapali"]]
        if kim: ks.sort(key=lambda x: _ilk(x.get("sahip")) != _ilk(kim))
        out.append({"ad": ad, "ok": r["ok"], "hata": r["hata"], "toplam": len(r["kayitlar"]), "acik": len(ks), "kayitlar": ks[:n]})
    return out
DISA_ALANLAR = ("tarih", "toplanti", "tur", "metin", "sahip", "vade", "durum", "kaynak_saat")
def disa_aktar(dizin, bicim="csv"):
    # Suflor'un karar grafı → CSV ya da JSON metni (kullanıcı dosyayı başka defterine kendisi yükler). Gizli toplantının kayıtları girmez; karar metnindeki teyit eki
    # durum sütununa taşınır ("teyit bekliyor"). → (metin, dosya adı, kayıt sayısı)
    satirlar = []
    if os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")):
        c = _db(dizin)
        try: rs = c.execute("SELECT toplanti, baslik, tarih, tur, kim, sahip, metin, son_tarih, saat, durum FROM kayit WHERE tur IN ('karar', 'is', 'soz', 'soru') ORDER BY tarih, id").fetchall()
        finally: c.close()
        ky = son_kayitlar(dizin); gz = {}
        for top, baslik, tarih, tur, kim, sahip, metin, son, saat, durum in rs:
            if top:
                if top not in gz: gz[top] = gizli_mi(dizin, top, ky)
                if gz[top]: continue
            m = TEYIT_RX.search(metin or "")
            satirlar.append({"tarih": tarih or "", "toplanti": baslik or "", "tur": tur, "metin": TEYIT_RX.sub("", metin or ""), "sahip": sahip or kim or "", "vade": son or "",
                             "durum": "teyit bekliyor" if m else (durum or "acik"), "kaynak_saat": saat or ""})
    damga = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    if bicim == "json":
        return json.dumps({"kaynak": "Suflor.me", "olusturma": datetime.datetime.now().isoformat(timespec="seconds"), "kayitlar": satirlar}, ensure_ascii=False, indent=1), f"suflor-kararlar-{damga}.json", len(satirlar)
    import csv, io
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(DISA_ALANLAR), lineterminator="\n"); w.writeheader()
    for s in satirlar: w.writerow(s)
    return "﻿" + buf.getvalue(), f"suflor-kararlar-{damga}.csv", len(satirlar)
BUGUN_KENDI_GUN = 14; BUGUN_BASKA_GUN = 30  # S226: "Senden beklenenler" son 14 gün (daha eskisi "Geride kalanlar"); "Başkalarından beklenenler" son 30 gün ya da vadesi gelecekte
def toplanti_rolu(dizin, top):
    # → (katildi, yurutuyor). Kaynak: <canlı>/gundemler/<toplantı>.json "rol" (yurutucu | katilimci | dinleyici; aktarıcı toplantı başında yazar, takvim düzenleyicisinden çıkar).
    # katildi = Suflor'un bu toplantı için dökümü ya da gündem kaydı var (kullanıcının kendi toplantısı). Rol kaydı yoksa ama döküm varsa yürüten sayılır (toplanti-claude.py varsayılanı da "yurutucu"); hiçbir kayıt yoksa ne katıldı ne yürüttü.
    top = str(top or "")
    if not top: return False, False
    ad = top[:-3] if top.endswith(".md") else top
    rol = ""; var = os.path.exists(os.path.join(dizin, ad + ".md"))
    try:
        with open(os.path.join(dizin, "gundemler", ad + ".json"), encoding="utf-8") as fh: g = json.load(fh)
        var = True; rol = str(g.get("rol") or "") if isinstance(g, dict) else ""
    except (OSError, ValueError): pass
    return var, var and rol in ("", "yurutucu")
def bugun_veri(dizin, ad, bugun=None):
    # Bugün sayfası için karar grafından: kullanıcının açık işleri, başkalarına atanmış açık işler, teyit bekleyen kararlar, son toplantının kararları.
    # Gizli toplantıdan gelen kayıt dönmez. Veri yoksa listeler boş (uydurma yok). ad boşsa "kendi" ve "baskalari" ayrılamaz → ikisi de boş.
    # S226 ("Senden beklenenler" kuralı): kendi = sahibi kullanıcı olan açık işler; teyit = yalnız kullanıcının yürüttüğü toplantının onay bekleyen kararları.
    # İkisinde de "yas" (toplantıdan beri gün) ve "geride" (yas > 14 ve vadesi gelecekte değil) var; geride olanlar arayüzde ayrı, katlanmış "Geride kalanlar"da.
    # baskalari = yalnız kullanıcının katıldığı toplantılardan ve son 30 gün ya da vadesi gelecekte olanlar.
    bugun = bugun or datetime.date.today(); out = {"ad": ad or "", "kendi": [], "baskalari": [], "teyit": [], "son_karar": None}
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return out
    c = _db(dizin)
    try: rs = c.execute("SELECT id, toplanti, baslik, tarih, tur, kim, sahip, metin, son_tarih, durum FROM kayit WHERE tur IN ('is', 'soz', 'karar') ORDER BY tarih DESC, id DESC LIMIT 3000").fetchall()
    finally: c.close()
    ky = son_kayitlar(dizin); gz = {}; rl = {}
    def gorunur(t):
        if not t: return True
        if t not in gz: gz[t] = not gizli_mi(dizin, t, ky)
        return gz[t]
    def rol(t):
        if t not in rl: rl[t] = toplanti_rolu(dizin, t)
        return rl[t]
    def yas_geride(tarih, gun):
        g = _vade_gun(tarih, bugun); yas = -g if g is not None else None
        return yas, bool(yas is not None and yas > BUGUN_KENDI_GUN and not (gun is not None and gun >= 0))
    ben = _ilk(ad); son_top = None; son_kararlar = []
    for i, top, baslik, tarih, tur, kim, sahip, metin, son, durum in rs:
        if not gorunur(top): continue
        if tur == "karar":
            m = TEYIT_RX.search(metin or ""); temiz = TEYIT_RX.sub("", metin or "")
            k = {"id": f"k{i}", "metin": temiz, "teyit": bool(m), "neden": teyit_neden_sade((m.group(1) or "").strip()) if m else "", "baslik": baslik or "", "tarih": tarih or "", "toplanti": top}
            if m and rol(top)[1] and len(out["teyit"]) < 20:
                out["teyit"].append(dict(k, **dict(zip(("yas", "geride"), yas_geride(tarih, None)))))
            if son_top is None: son_top = top
            if top == son_top: son_kararlar.append(k)
            continue
        if durum != "acik": continue
        kisi = sahip or kim or ""; gun = _vade_gun(son, bugun)
        x = {"id": f"s{i}", "metin": metin, "kim": kisi, "vade": son or "", "kalan_gun": gun, "gecikti": gun is not None and gun < 0, "baslik": baslik or "", "toplanti": top, "tarih": tarih or ""}
        x["yas"], x["geride"] = yas_geride(tarih, gun)
        if ad and kisi and _ilk(kisi) == ben: out["kendi"].append(x)
        elif ad and kisi and rol(top)[0] and (x["yas"] is None or x["yas"] <= BUGUN_BASKA_GUN or (gun is not None and gun >= 0)): out["baskalari"].append(x)
    srt = lambda l: sorted(l, key=lambda x: (x["geride"], x["kalan_gun"] is None, x["kalan_gun"] if x["kalan_gun"] is not None else 0))
    out["kendi"] = srt(out["kendi"])[:30]; out["baskalari"] = srt(out["baskalari"])[:60]
    if son_kararlar: out["son_karar"] = {"baslik": son_kararlar[0]["baslik"], "tarih": son_kararlar[0]["tarih"], "toplanti": son_top, "kararlar": son_kararlar[::-1][:12]}
    return out
# --- Kararlar ve işler görünümü, gündem taslağı, davet maddeleri (5 Kasım) ---------------------------------------------------------------------------
MADDE_DUR_RX = re.compile(r"^_{5,}|^-{5,}|microsoft teams|zoom|google meet|toplantıya katıl|join", re.I)
MADDE_ATLA_RX = re.compile(r"^(gündem|agenda|konular|topics)\s*:?$|https?:|www\.|passcode|password|parola|şifre|meeting id|kimli[gğ]i|pin\b", re.I)
MADDE_ISARET_RX = re.compile(r"^([-•*·▪◦]|\d+[.)])\s*")
def davet_maddeleri(notlar, en_cok=12):
    # takvim davetinin notunu gündem maddelerine böler (pano davetMaddeleri ile aynı kural): madde işareti ya da numara kalkar, bağlantı/parola/katılım satırları
    # atlanır, katılım bloğunun (Teams/Zoom/Meet) başında durur. → ["…"]
    out = []
    for l in re.split(r"\r?\n", str(notlar or "")):
        l = l.strip()
        if MADDE_DUR_RX.search(l): break
        if not l or MADDE_ATLA_RX.search(l): continue
        out.append(MADDE_ISARET_RX.sub("", l))
        if len(out) >= en_cok: break
    return out
def kisi_parcalari(ad):  # "Ayşe Yılmaz" · "Yılmaz, Ayşe" · "ad.soyad (e-posta kullanıcı adı)" → ["ayse", "yilmaz"] (sadeleşmiş, sırasıyla)
    s = str(ad or "").strip()
    if "@" in s: s = s.split("@", 1)[0]
    return [p for p in (_dd_norm(x) for x in re.split(r"[\s._\-,()]+", s)) if len(p) >= 2 and not p.isdigit()]
def kisi_eslesir(a, b):
    # gevşek eşleme (takvim katılımcısı ↔ graf kişi adı): ilk adlar aynı, biri ötekinin alt kümesi (yalnız soyad yazılmış) ya da e-posta kullanıcı adı adın bitişik hâli
    x, y = kisi_parcalari(a), kisi_parcalari(b)
    if not x or not y: return False
    if x[0] == y[0] or x == y: return True
    if (len(x) >= 2 and set(x) <= set(y)) or (len(y) >= 2 and set(y) <= set(x)): return True
    return "".join(x) == "".join(y) or (len(x) == 1 and x[0] == "".join(y)) or (len(y) == 1 and y[0] == "".join(x))
def kayit_listesi(dizin, ad="", bugun=None):
    # "Kararlar ve işler" görünümü: grafın karar/iş/söz/soru kayıtlarının tamamı (gizli toplantı hariç). Satır: id (k/s/q + kayıt no), tur (karar|is|soru), metin, kim, vade,
    # kalan_gun, gecikti, tarihsiz, durum (acik · teyit = onay bekleyen karar · kapandi = yapılmış/iptal iş, cevaplanmış soru, onaylı karar), neden (teyit), baslik, toplanti,
    # tarih, kendi (kullanıcının işi). toplantilar: dosya → özet kaydının id'si ve pano/harita var mı (satırdan "toplantıya git"). kisiler: süzgeç listesi.
    bugun = bugun or datetime.date.today(); out = {"ad": ad or "", "kayitlar": [], "toplantilar": [], "kisiler": []}
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return out
    c = _db(dizin)
    try: rs = c.execute("SELECT id, toplanti, baslik, tarih, tur, kim, sahip, metin, son_tarih, durum FROM kayit WHERE tur IN ('is', 'soz', 'karar', 'soru') ORDER BY tarih DESC, id DESC LIMIT 5000").fetchall()
    finally: c.close()
    ky = son_kayitlar(dizin); gz = {}; tops = {}; kisiler = {}; ben = _ilk(ad)
    for i, top, baslik, tarih, tur, kim, sahip, metin, son, durum in rs:
        if top:
            if top not in gz: gz[top] = gizli_mi(dizin, top, ky)
            if gz[top]: continue
            if top not in tops:
                r = ky.get(top) or {}
                tops[top] = {"dosya": top, "baslik": baslik or "", "tarih": tarih or "", "id": str(r.get("id") or ""), "harita": bool(r.get("harita"))}
        x = {"id": "", "tur": tur if tur != "soz" else "is", "metin": metin or "", "kim": sahip or kim or "", "vade": son or "", "kalan_gun": None, "gecikti": False, "tarihsiz": False,
             "durum": "acik", "neden": "", "baslik": baslik or "", "toplanti": top or "", "tarih": tarih or "", "kendi": False}
        if tur == "karar":
            m = TEYIT_RX.search(metin or ""); x["id"] = f"k{i}"; x["metin"] = TEYIT_RX.sub("", metin or ""); x["kim"] = kim or ""
            x["durum"] = "teyit" if m else "kapandi"; x["neden"] = teyit_neden_sade((m.group(1) or "").strip()) if m else ""
        elif tur == "soru":
            x["id"] = f"q{i}"; x["kim"] = kim or ""; x["durum"] = "acik" if durum == "acik" else "kapandi"
        else:
            x["id"] = f"s{i}"; gun = _vade_gun(son, bugun); x["kalan_gun"] = gun
            x["durum"] = "acik" if durum == "acik" else "kapandi"; x["gecikti"] = x["durum"] == "acik" and gun is not None and gun < 0
            x["tarihsiz"] = x["durum"] == "acik" and gun is None; x["kendi"] = bool(ben and x["kim"] and _ilk(x["kim"]) == ben)
        if x["kim"]: kisiler[x["kim"]] = kisiler.get(x["kim"], 0) + 1
        out["kayitlar"].append(x)
    out["toplantilar"] = sorted(tops.values(), key=lambda t: t["tarih"], reverse=True)
    out["kisiler"] = [k for k, _ in sorted(kisiler.items(), key=lambda kv: (-kv[1], kucuk(kv[0])))][:60]
    return out
def gundem_taslagi(dizin, katilimcilar, ad="", baslik="", bugun=None, en_cok=12):
    # Sıradaki toplantının gündem taslağı: katılımcılarla (takvim adları ↔ graf kişi adları, gevşek eşleme) ya da aynı başlıklı önceki toplantılarla ilgili açık iş/söz,
    # onay bekleyen karar ve açık soru. İlgili toplantı: bir katılımcının kim/sahip olduğu kayıt var ya da başlığı aynı. Kullanıcının kendi işleri yalnız ilgili toplantıdan.
    # → {"maddeler": [{id, tur, metin, kim, vade, gecikti, baslik, toplanti, satir}], "kisiler": [eşleşen graf adları], "metin": "- …\n- …"}
    v = kayit_listesi(dizin, ad, bugun); kat = [k for k in (katilimcilar or []) if str(k or "").strip()]
    if not kat and not baslik: return {"maddeler": [], "kisiler": [], "metin": ""}
    acik = [x for x in v["kayitlar"] if x["durum"] != "kapandi"]; es = {}
    for x in acik:
        if x["kim"] and x["kim"] not in es: es[x["kim"]] = any(kisi_eslesir(x["kim"], k) for k in kat) and not (ad and kisi_eslesir(x["kim"], ad))
    ilgili = {x["toplanti"] for x in acik if x["toplanti"] and (es.get(x["kim"]) or (baslik and _dd_norm(x["baslik"]) == _dd_norm(baslik)))}
    sec = [x for x in acik if es.get(x["kim"]) or (x["toplanti"] and x["toplanti"] in ilgili)]
    sira = {"is": 0, "karar": 1, "soru": 2}
    sec.sort(key=lambda x: (sira.get(x["tur"], 3), not x["gecikti"], x["kalan_gun"] is None, x["kalan_gun"] or 0, x["tarih"]))
    out = []
    for x in sec[:en_cok]:
        kim = (x["kim"].split() or [""])[0] if x["kim"] else ""
        if x["tur"] == "karar": s = f"Onay: {x['metin']}" + (f" ({kim})" if kim else "")
        elif x["tur"] == "soru": s = f"Soru: {x['metin']}" + (f" ({kim})" if kim else "")
        else: s = x["metin"] + (f" — {kim}" if kim else "") + (f", {-x['kalan_gun']} gün gecikti" if x["gecikti"] else f", {x['vade']}" if x["vade"] else "")
        out.append({"id": x["id"], "tur": x["tur"], "metin": x["metin"], "kim": x["kim"], "vade": x["vade"], "gecikti": x["gecikti"], "baslik": x["baslik"], "toplanti": x["toplanti"], "satir": s})
    return {"maddeler": out, "kisiler": sorted({x["kim"] for x in acik if es.get(x["kim"])}), "metin": "\n".join("- " + m["satir"] for m in out)}
def sozler_tasi(dizin):
    # eski sozler.json (Faz 3) → graf, bir kez; dosya sozler-tasindi.json olur (silinmez)
    yol = os.path.join(dizin, "sozler.json")
    if not os.path.exists(yol): return 0
    try: xs = json.load(open(yol, encoding="utf-8")).get("sozler") or []
    except (OSError, ValueError): return 0
    c = _db(dizin)
    with c:
        for x in xs:
            c.execute("INSERT INTO kayit (toplanti, baslik, tarih, tur, sahip, metin, son_tarih, durum, eklendi, bag) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (x.get("file"), x.get("toplanti"), str(x.get("at") or "")[:10], "soz", x.get("kim"), x.get("metin"), x.get("tarih"),
                       x.get("durum") or "acik", x.get("at"), "soz"))
    c.close(); os.replace(yol, os.path.join(dizin, "sozler-tasindi.json")); return len(xs)
def eylem_esle(dizin, eylemler, sahip, toplanti=None, ekle=True):
    # kuyruğun dış işleri grafta kullanıcının işi; durum kuyruktan: yapildi → yapildi, reddedildi → iptal, diğerleri açık
    # ekle=False: yalnız var olan bağların durumu (okumadan önce eşitleme — panodan onay/ret eylem komutu çalışmadan da yansır)
    c = _db(dizin); n = 0
    with c:
        for e in eylemler:
            if e.get("tur") not in ("takvim", "eposta", "takip", "mesaj", "diger") or not e.get("id"): continue
            bag = f"eylem:{e['id']}"; durum = {"yapildi": "yapildi", "reddedildi": "iptal"}.get(e.get("durum"), "acik")
            var = c.execute("SELECT id FROM kayit WHERE bag = ?", (bag,)).fetchone()
            if var: c.execute("UPDATE kayit SET durum = ? WHERE id = ?", (durum, var[0])); continue
            if not ekle: continue
            c.execute("INSERT INTO kayit (toplanti, tarih, tur, sahip, metin, durum, eklendi, bag) VALUES (?,?,?,?,?,?,?,?)",
                      (toplanti, datetime.date.today().isoformat(), "is", sahip, str(e.get("baslik") or "")[:600], durum,
                       datetime.datetime.now().isoformat(timespec="seconds"), bag)); n += 1
    c.close(); return n
# --- zihin haritası --------------------------------------------------------------------------------------------------
def _url(u):  # yalnız http/https bağlantı olur (javascript:, data: vb. atılır)
    u = str(u or "").strip(); return u if re.match(r"https?://[^\s<>\"']+$", u, re.I) else ""
def cevap_alanlari(o):  # soru/sayı/iddia öğesinin doğrulama alanları → görselin okuyacağı sözlük; cevap/kaynak yoksa boş
    c = " ".join(str(o.get("cevap") or "").split()); k = " ".join(str(o.get("kaynak") or "").split())
    if o.get("tur") not in ("soru", "sayi", "iddia") or not (c or k): return {}
    ck = kucuk(c).replace("ğ", "g").replace("ş", "s").replace("ı", "i")
    d = "dogru" if ck.startswith("dogru") else "yanlis" if ck.startswith("yanlis") else "kismen" if ck.startswith("kismen") else ""
    if d: c = re.sub(r"^\S+(\s+do[gğ]ru)?\s*[:—–-]\s*", "", c, count=1) or c  # 5 Kasım (kullanıcı): etiket rengi ve adı zaten gösteriyor — "Kısmen: …" öneki yinelenmez
    return {"cevap": c, "kaynak": k, "kaynak_url": _url(o.get("kaynak_url")), "cd": d}
def sayi_denetim(v, say):
    # özet .md "Toplantı çıktısı" sayıları (say: {karar, is, acik}) ↔ yapı dosyasındaki karar · iş+söz · soru öğe sayıları → [uyarı]; yalnız uyarır
    if not say: return []
    c = cikti_say(v); c["acik"] = sum(o["tur"] == "soru" for m in v["maddeler"] for o in m["ogeler"])  # özetin "açık kalanlar"ı görselde açık soru olarak çıkar (gündem durumu ayrı)
    ad = {"karar": "Kararlar", "is": "Sahipli işler", "acik": "Açık kalanlar"}; out = []
    for k in ("karar", "is", "acik"):
        if k in say and say[k] != c[k]:
            out.append(f"{ad[k]}: özette {say[k]}, yapı dosyasında {c[k]}" + (" — eksik olanı yapı dosyasına ekle" if c[k] < say[k] else " — fazla olanı özete ya da yapıdan kaldır"))
    return out
def harita_veri(v):
    kok = {"ad": str(v.get("baslik") or "Toplantı"), "alt": [], "tur": "kok", "not": str(v.get("tarih") or "")}
    for m in v["maddeler"]:
        d = {"ad": str(m.get("baslik") or "Gündem dışı"), "tur": "madde", "not": str(m.get("durum") or ""), "alt": []}
        for t in TURLER:
            os_ = [o for o in m["ogeler"] if o["tur"] == t]
            if not os_: continue
            g = {"ad": TURLER[t] + ("lar" if t in ("karar", "sayi", "iddia") and len(os_) > 1 else "ler" if t == "is" and len(os_) > 1 else ""), "tur": t, "alt": []}
            if t == "soru" and len(os_) > 1: g["ad"] = "Açık sorular"
            for o in os_:
                kim = o.get("sahip") if t == "is" else o.get("kim")
                g["alt"].append({"ad": str(o["metin"]), "tur": t, "kim": str(kim or ""), "saat": str(o.get("saat") or ""), "tarih": str(o.get("tarih") or ""),
                                 "alinti": str(o.get("alinti") or "")}); g["alt"][-1].update(cevap_alanlari(o))
            d["alt"].append(g)
        kok["alt"].append(d)
    return kok
# Görsel belgeler tek dosya ve çevrimdışı açılır (file:); marka yazı tipleri (Bricolage Grotesque, IBM Plex) yapi.py'nin yanındaki marka/yazi/ klasöründen
# mutlak file: adresiyle gömülür (depo ve kurulu uygulama aynı düzende). Dosya yoksa sistem yazı tipine düşer; dış ağ adresi yok.
_YAZI_ARALIK = {"latin-ext": "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
                "latin": "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"}
_YAZI_DOSYA = (("Bricolage Grotesque", "bricolage-grotesque", 300), ("Bricolage Grotesque", "bricolage-grotesque", 500), ("IBM Plex Sans", "ibm-plex-sans", 400),
               ("IBM Plex Sans", "ibm-plex-sans", 500), ("IBM Plex Sans", "ibm-plex-sans", 600), ("IBM Plex Mono", "ibm-plex-mono", 400))
def yazi_css(klasor=None):
    import urllib.request
    d = klasor or os.path.join(os.path.dirname(os.path.abspath(__file__)), "marka", "yazi")
    if not os.path.isdir(d): return ""
    kok = "file://" + urllib.request.pathname2url(os.path.abspath(d)); out = []
    for aile, dosya, agirlik in _YAZI_DOSYA:
        for alt, aralik in _YAZI_ARALIK.items():
            f = f"{dosya}-{alt}-{agirlik}-normal.woff2"
            if os.path.isfile(os.path.join(d, f)):
                out.append(f'@font-face{{font-family:"{aile}";font-weight:{agirlik};font-display:swap;src:url({kok}/{f}) format("woff2");unicode-range:{aralik}}}')
    return "\n".join(out)
def harita_html(v):
    veri = json.dumps(harita_veri(v), ensure_ascii=False).replace("</", "<\\/")
    return HARITA.replace("__YAZI__", yazi_css()).replace("__BASLIK__", html.escape(str(v.get("baslik") or "Toplantı"))).replace("__VERI__", veri)
HARITA = r"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>__BASLIK__ — zihin haritası</title>
<style>
/* kaynak: pano/renk.css + pano/yazi.css (--b-* belirteçleri; belge tek dosya ve çevrimdışı olduğu için kopya — değişince ikisini birlikte güncelle) */
:root{color-scheme:light dark;--b-zemin:#FAFAF8;--b-yuzey:#FFFFFF;--b-yuzey2:#F2F2EF;--b-murekkep:#1D1D1F;--b-m2:#5E5E63;--b-m3:#6E6E73;--b-cizgi:rgba(29,29,31,.08);--b-cizgi2:rgba(29,29,31,.16);--b-uzerinde:rgba(29,29,31,.045);--b-ton2:rgba(29,29,31,.11);
--b-vurgu:#175E46;--b-vurgu-hafif:rgba(23,94,70,.09);--b-gec:#B0533A;--b-ana:#175E46;--b-ana-yazi:#FFFFFF;--b-pirinc:#C9973A;--b-ipucu-zemin:#1D1D1F;--b-ipucu-yazi:#F5F5F7;--b-golge-panel:0 12px 40px rgba(0,0,0,.12);
--b-k-s:8px;--b-k-m:14px;--b-k-l:18px;--b-k-tam:999px;--b-yz-govde:15px;--b-yz-m:13.5px;--b-yz-k:12.5px;--b-yz-t:11.5px;--b-yz-e:10.5px;
--f-baslik:"Bricolage Grotesque","Avenir Next","Helvetica Neue",system-ui,sans-serif;--f-govde:"IBM Plex Sans",-apple-system,"Helvetica Neue",system-ui,sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--b-zemin:#161616;--b-yuzey:#1C1C1E;--b-yuzey2:#202022;--b-murekkep:#F2F2F2;--b-m2:#A1A1A6;--b-m3:#8A8A8F;--b-cizgi:rgba(242,242,242,.08);--b-cizgi2:rgba(242,242,242,.15);--b-uzerinde:rgba(242,242,242,.05);--b-ton2:rgba(242,242,242,.12);
--b-vurgu:#3E9B78;--b-vurgu-hafif:rgba(62,155,120,.15);--b-gec:#DE8467;--b-ana:#3E9B78;--b-ana-yazi:#0E1411;--b-pirinc:#D8A849;--b-ipucu-zemin:#F2F2F2;--b-ipucu-yazi:#161616;--b-golge-panel:0 12px 40px rgba(0,0,0,.45)}}
:root[data-theme=dark]{--b-zemin:#161616;--b-yuzey:#1C1C1E;--b-yuzey2:#202022;--b-murekkep:#F2F2F2;--b-m2:#A1A1A6;--b-m3:#8A8A8F;--b-cizgi:rgba(242,242,242,.08);--b-cizgi2:rgba(242,242,242,.15);--b-uzerinde:rgba(242,242,242,.05);--b-ton2:rgba(242,242,242,.12);
--b-vurgu:#3E9B78;--b-vurgu-hafif:rgba(62,155,120,.15);--b-gec:#DE8467;--b-ana:#3E9B78;--b-ana-yazi:#0E1411;--b-pirinc:#D8A849;--b-ipucu-zemin:#F2F2F2;--b-ipucu-yazi:#161616;--b-golge-panel:0 12px 40px rgba(0,0,0,.45)}
__YAZI__
:root{--kok:var(--b-vurgu);--madde:var(--b-murekkep);--karar:var(--b-vurgu);--is:var(--b-m2);--soru:var(--b-m3);--sayi:var(--b-m3);--iddia:var(--b-gec);--soz:var(--b-m2);--kok-yazi:var(--b-ana-yazi)}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--b-zemin);color:var(--b-murekkep);font:var(--b-yz-govde)/1.5 var(--f-govde);-webkit-font-smoothing:antialiased}
header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:18px 24px 14px}
header h1{font:300 24px/1.15 var(--f-baslik);letter-spacing:-.02em;margin:0 auto 0 0;overflow-wrap:anywhere}
header button{font:inherit;font-size:var(--b-yz-k);padding:6px 14px;border:1px solid var(--b-cizgi2);border-radius:var(--b-k-tam);background:transparent;color:var(--b-murekkep);cursor:pointer}
header button:hover{background:var(--b-uzerinde)}:focus-visible{outline:2px solid var(--b-vurgu);outline-offset:2px}
#alan{overflow:auto;height:calc(100% - 66px);padding:8px 24px 24px}svg{display:block}
.d rect{fill:var(--b-yuzey);stroke:var(--b-cizgi2);stroke-width:1}.d rect.ser{stroke:none}.d text{fill:var(--b-murekkep);font:13px var(--f-govde);dominant-baseline:middle}.d{cursor:pointer;outline:none}
.d .say{fill:var(--b-m3);font:400 11px var(--f-mono)}.d .cv{font-size:12px;font-weight:500}.d .kn{font-size:12px;opacity:.85}.d:hover rect:first-child,.d:focus-visible rect:first-child{stroke:var(--b-vurgu)}path.c{fill:none;stroke:var(--b-cizgi2);stroke-width:1.2}
#ayrinti{position:fixed;right:20px;bottom:20px;max-width:min(420px,calc(100% - 40px));background:var(--b-yuzey);border:1px solid var(--b-cizgi);border-radius:var(--b-k-l);padding:18px 20px 16px;box-shadow:var(--b-golge-panel);display:none}
#ayrinti b{display:block;margin:0 24px 6px 0;font:400 17px/1.3 var(--f-baslik);overflow-wrap:anywhere}#ayrinti .k{color:var(--b-m3);font-size:var(--b-yz-k)}#ayrinti q{display:block;margin-top:10px;color:var(--b-m2);font-size:var(--b-yz-m)}
#ayrinti button{position:absolute;right:8px;top:8px;width:28px;height:28px;border:0;border-radius:50%;background:none;color:var(--b-m3);font-size:18px;cursor:pointer}#ayrinti button:hover{background:var(--b-uzerinde);color:var(--b-murekkep)}
#ayrinti p{margin:8px 0 0;font-size:var(--b-yz-m);color:var(--b-m2);overflow-wrap:anywhere}#ayrinti a{color:var(--b-vurgu)}
.cd-dogru{color:var(--karar)}.cd-yanlis{color:var(--iddia)}.cd-kismen{color:var(--b-m2)}
</style>
<header><h1>__BASLIK__</h1><button id=ac>Hepsini aç</button><button id=kapa>Hepsini kapat</button><button id=png>Resim olarak indir</button></header>
<div id=alan><svg id=s xmlns="http://www.w3.org/2000/svg"></svg></div><div id=ayrinti role=dialog aria-live=polite></div>
<script>
const V=__VERI__;const RENK=t=>getComputedStyle(document.documentElement).getPropertyValue('--'+(t==='kok'?'kok':t==='madde'?'madde':t)).trim()||'#888';
const S=document.getElementById('s'),NS='http://www.w3.org/2000/svg',olc=document.createElement('canvas').getContext('2d');olc.font='13px "IBM Plex Sans",-apple-system,"Helvetica Neue",system-ui,sans-serif';
let sira=0,yaprak=0;(function say(d){if(!(d.alt||[]).length)yaprak++;(d.alt||[]).forEach(say)})(V);
(function kimlik(d,der){d.id=sira++;d.der=der;d.acik=yaprak<=30||der<2;(d.alt||[]).forEach(x=>kimlik(x,der+1))})(V,0);  // küçük harita tümüyle açık
// 5 Kasım (kullanıcı): metin kesilmez — uzun satır sözcük sınırından alt satıra geçer, kutu yüksekliği satır sayısıyla büyür
const ENX=420,SY=18;
function sar(metin,sp){const mx=ENX-sp,out=[];let s='';
  String(metin).split(/\s+/).filter(Boolean).forEach(k=>{const y=s?s+' '+k:k;if(!s||olc.measureText(y).width<=mx){s=y;return}out.push(s);s=k});
  if(s||!out.length)out.push(s);return out.map(x=>{if(olc.measureText(x).width<=mx)return x;let i=x.length;while(i>1&&olc.measureText(x.slice(0,i)).width>mx)i--;return x.slice(0,i)})}
function satirlar(d){return d.sat||(d.sat=sar(d.ad,(d.alt&&d.alt.length?46:28)+4))}
// 5 Kasım: doğrulanmış cevap ve kaynak öğenin altında küçük etiket (renk: doğru/yanlış/kısmen); bağlantı ayrıntı penceresinde
function ekler(d){if(d.ek)return d.ek;d.ek=[];if(d.cevap)d.ek=sar((d.cd==='dogru'?'✓ ':d.cd==='yanlis'?'✗ ':d.cd==='kismen'?'~ ':'→ ')+d.cevap,32).map(x=>['cv',x]);
  if(d.kaynak)d.ek=d.ek.concat(sar('Kaynak: '+d.kaynak,32).map(x=>['kn',x]));return d.ek}  // tek sözcük sığmazsa (uzun bağlantı) yalnız o kırpılır
function boy(d){const sat=satirlar(d),ek=ekler(d),sp=(d.alt&&d.alt.length?46:28)+4,ts=sat.concat(ek.map(x=>x[1]));return{w:Math.min(ENX,Math.max(60,Math.ceil(Math.max(...ts.map(x=>olc.measureText(x).width)))+sp)),h:Math.max(30,12+ts.length*SY)}}
const DX=48,DY=10;
function yerles(d,x,y){const b=boy(d);d.x=x;d.w=b.w;d.h=b.h;const c=d.acik?(d.alt||[]):[];if(!c.length){d.y=y;return y+d.h+DY}
let yy=y;c.forEach(k=>{yy=yerles(k,x+d.w+DX,yy)});const ilk=c[0].y,son=c[c.length-1].y;d.y=(ilk+son)/2;return Math.max(yy,d.y+d.h+DY)}
function el(ad,a,ust){const e=document.createElementNS(NS,ad);for(const k in a)e.setAttribute(k,a[k]);if(ust)ust.appendChild(e);return e}
function ciz(){S.innerHTML='';const H=yerles(V,8,8);let W=0;(function g(d){W=Math.max(W,d.x+d.w);if(d.acik)(d.alt||[]).forEach(g)})(V);
S.setAttribute('width',W+16);S.setAttribute('height',H+8);S.setAttribute('viewBox',`0 0 ${W+16} ${H+8}`);
(function g(d){if(!d.acik)return;(d.alt||[]).forEach(k=>{const x1=d.x+d.w,y1=d.y+d.h/2,x2=k.x,y2=k.y+k.h/2,m=(x1+x2)/2;el('path',{class:'c',d:`M${x1} ${y1}C${m} ${y1},${m} ${y2},${x2} ${y2}`},S);g(k)})})(V);
(function g(d){const gr=el('g',{class:'d',transform:`translate(${d.x},${d.y})`,tabindex:0,role:'button','aria-label':d.ad},S);
const r=el('rect',{width:d.w,height:d.h,rx:d.der===0?15:8},gr);const renk=RENK(d.tur);
if(d.der===0){r.style.fill=renk;r.style.stroke=renk}else el('rect',{width:4,height:d.h-10,x:6,y:5,rx:2,class:'ser'},gr).style.fill=renk;
const sat=satirlar(d),ek=ekler(d),tum=sat.map(x=>['',x]).concat(ek),tx=d.der===0?14:16,t=el('text',{x:tx,y:d.h/2-(tum.length-1)*SY/2},gr);const CR={dogru:'karar',yanlis:'iddia',kismen:'is'}[d.cd]||'madde';
  tum.forEach((x,i)=>{const ts=el('tspan',{x:tx,dy:i?SY:0},t);if(x[0]){ts.setAttribute('class',x[0]);ts.style.fill=RENK(x[0]==='cv'?CR:'madde')}ts.textContent=x[1]});if(d.der===0)t.style.fill=RENK('kok-yazi');
if(d.alt&&d.alt.length){const s=el('text',{class:'say',x:d.w-22,y:d.h/2},gr);s.textContent=d.acik?'‹':String(d.alt.length)+' ›';if(d.der===0)s.style.fill=RENK('kok-yazi')}
const tik=()=>{if(d.alt&&d.alt.length){d.acik=!d.acik;ciz()}else goster(d)};gr.onclick=tik;gr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tik()}};
if(d.acik)(d.alt||[]).forEach(g)})(V)}
const A=document.getElementById('ayrinti');const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function goster(d){A.innerHTML=`<button aria-label="Kapat">×</button><b>${esc(d.ad)}</b><div class=k>${[d.kim,d.tarih&&('tarih '+d.tarih),d.saat&&('saat '+d.saat)].filter(Boolean).map(esc).join(' · ')}</div>${d.alinti?'<q>'+esc(d.alinti)+'</q>':''}${cvHtml(d)}`;A.style.display='block';A.querySelector('button').onclick=()=>A.style.display='none'}
function cvHtml(d){return (d.cevap?'<p class="cd-'+esc(d.cd||'')+'">Cevap: '+esc(d.cevap)+'</p>':'')+(d.kaynak||d.kaynak_url?'<p>Kaynak: '+(d.kaynak_url?'<a href="'+esc(d.kaynak_url)+'" target=_blank rel="noopener noreferrer">'+esc(d.kaynak||d.kaynak_url)+'</a>':esc(d.kaynak))+'</p>':'')}
function hepsi(v){(function g(d){d.acik=v||d.der===0;(d.alt||[]).forEach(g)})(V);ciz()}
document.getElementById('ac').onclick=()=>hepsi(true);document.getElementById('kapa').onclick=()=>hepsi(false);
document.getElementById('png').onclick=()=>{const k=S.cloneNode(true),cs=getComputedStyle(document.body);k.querySelectorAll('.d rect:first-child').forEach(r=>{if(!r.style.fill){r.setAttribute('fill',getComputedStyle(document.documentElement).getPropertyValue('--b-yuzey'));r.setAttribute('stroke','rgba(0,0,0,.15)')}});
k.querySelectorAll('text').forEach(t=>{t.setAttribute('font-family','-apple-system,Helvetica Neue,sans-serif');t.setAttribute('font-size',t.classList.contains('say')?'11':'13');t.querySelectorAll('tspan.cv,tspan.kn').forEach(q=>q.setAttribute('font-size','12'));t.setAttribute('dominant-baseline','middle');if(!t.style.fill)t.setAttribute('fill',cs.color)});
k.querySelectorAll('path').forEach(p=>{p.setAttribute('fill','none');p.setAttribute('stroke','rgba(120,120,120,.6)');p.setAttribute('stroke-width','1.4')});
const w=+S.getAttribute('width'),h=+S.getAttribute('height'),o=2,img=new Image(),c=document.createElement('canvas');c.width=w*o;c.height=h*o;
img.onload=()=>{const x=c.getContext('2d');x.fillStyle=cs.backgroundColor;x.fillRect(0,0,c.width,c.height);x.scale(o,o);x.drawImage(img,0,0);const a=document.createElement('a');a.download=document.title.replace(/[\\/:*?"<>|]/g,'-')+'.png';a.href=c.toDataURL('image/png');a.click()};
img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(k))};
// yazı tipi (dosyadan) sonradan yüklenirse ölçüler değişir: önbelleği boşalt, yeniden çiz (açık/kapalı durumu düğümde kalır)
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>{if(!document.fonts.check('13px "IBM Plex Sans"'))return;(function g(d){delete d.sat;delete d.ek;(d.alt||[]).forEach(g)})(V);ciz()});
ciz();
</script></html>"""
# --- toplantı görseli: tür seçimi + karar ve iş panosu (v0.186.0) ---------------------------------------------------------
# 5 Kasım (kullanıcı): karar ve işin olduğu toplantıda okunacak şey "ne kararlaştı, kim neyi ne zamana yapacak"; zihin haritası bunu
# gündem dallarına dağıtıyor. Eşik: 2 karar (tek karar şeritte yalnız kalır, haritada da okunur) ya da 3 sahipli iş (üç işte kişi sütunu
# haritadan hızlı okunur). Yapı dosyasında "gorsel": "harita" | "karar_is" elle seçer. Dosya adı aynı kalır (<özet>-zihin-haritasi.html).
GORSEL_AD = {"harita": "Zihin haritası", "karar_is": "Karar ve iş panosu"}
def gorsel_tur(v):
    # tek kaynak "gorsel" alanı (Claude özeti yazarken doldurur); alan yoksa en az 1 karar ya da 1 sahipli iş/söz → pano, hiçbiri yoksa harita
    z = str(v.get("gorsel") or "").strip()
    if z in GORSEL_AD: return z
    og = [o for m in v["maddeler"] for o in m["ogeler"]]
    return "karar_is" if any(o["tur"] == "karar" or (o["tur"] in ("is", "soz") and str(o.get("sahip") or o.get("kim") or "").strip()) for o in og) else "harita"
def dokum_saatleri(yol):  # canlı döküm (.jsonl "time" ya da .md tablo satırı) → ["HH:MM:SS", …]; okunamazsa []
    try:
        if yol.endswith(".jsonl"): return [str(json.loads(l).get("time") or "") for l in open(yol, encoding="utf-8") if l.strip()]
        return re.findall(r"^\|\s*(\d{1,2}:\d{2}:\d{2})\s*\|", open(yol, encoding="utf-8").read(), re.M)
    except (OSError, ValueError): return []
def _hm(t): t = int(round(t)) % 86400; return f"{t // 3600:02d}:{t % 3600 // 60:02d}"
def _koken(ts):  # gece yarısını aşan toplantı: saatler çemberde, en büyük boşluktan sonraki saat başlangıç
    ts = sorted(set(ts)); n = len(ts)
    if n < 2: return ts[0]
    bos = [(ts[(i + 1) % n] - ts[i]) % 86400 or 86400 for i in range(n)]
    return ts[(bos.index(max(bos)) + 1) % n]
def zaman_seridi(v, saatler=None):
    # gündem şeridi: madde saatleri (madde "baslangic"/"saat", "bitis") → öğe saatleri (karar/iş/iddia…; ardışık aynı maddenin öğeleri bir blok,
    # sınır iki öğenin ortası) → döküm saatleri (yalnız toplam süre; maddelere eşit pay) → sıra (eşit pay). Kaynak görselde yazılır.
    M = v["maddeler"]; dk = [_sn(s) for s in (saatler or [])]; dk = [t for t in dk if t is not None]
    msa = [(i, _sn(m.get("baslangic") or m.get("saat")), _sn(m.get("bitis")) if m.get("bitis") else None) for i, m in enumerate(M)]
    msa = [x for x in msa if x[1] is not None]
    noktalar = [(i, t) for i, m in enumerate(M) for o in m["ogeler"] for t in [_sn(o.get("saat")) if o.get("saat") else None] if t is not None]
    def kirp(o, son):  # döküm saatlerinden toplantıya ait olanlar (ilk/son öğenin ± 30 dk'sı; aynı günün başka toplantısı karışmasın)
        r = [((t - o) % 86400) for t in dk]; r = [x - 86400 if x > 86400 - 1800 else x for x in r]
        return [x for x in r if -1800 <= x <= son + 1800]
    if len(msa) >= 2 or len(noktalar) >= 2:
        kaynak = "madde" if len(msa) >= 2 else "oge"
        o = _koken([t for _, t, *_ in msa] if kaynak == "madde" else [t for _, t in noktalar])
        rel = lambda t: (t - o) % 86400
        if kaynak == "madde":
            ns = sorted((rel(b), i, rel(e) if e is not None else None) for i, b, e in msa)
        else:
            ns = sorted((rel(t), i) for i, t in noktalar)
        son_n = ns[-1][0]; d = kirp(o, son_n)
        bas, son = min([0] + d), max([son_n] + ([e for *_, e in ns if e is not None] if kaynak == "madde" else []) + d)
        bl = []
        if kaynak == "madde":
            for j, (b, i, e) in enumerate(ns):
                sn_ = e if e is not None else (ns[j + 1][0] if j + 1 < len(ns) else son)
                bl.append([i, b if j else bas, max(sn_, b)])
        else:
            for j, (t, i) in enumerate(ns):
                if bl and bl[-1][0] == i: bl[-1][2] = t; continue
                if bl: orta = (bl[-1][2] + t) / 2; bl[-1][2] = orta; bl.append([i, orta, t])
                else: bl.append([i, bas, t])
            bl[-1][2] = son
        not_ = ("Süreler gündem maddelerinin saatlerinden." if kaynak == "madde" else
                "Süreler yaklaşık: kararların, işlerin ve iddiaların saatinden; iki maddenin sınırı aradaki öğelerin ortası." + (" Toplam süre dökümden." if d else ""))
        ber = lambda t: _hm(o + t)
    elif len(dk) >= 2:
        kaynak = "dokum"; o = _koken(dk); r = sorted((t - o) % 86400 for t in dk); bas, son = r[0], r[-1]
        pay = (son - bas) / max(1, len(M)); bl = [[i, bas + i * pay, bas + (i + 1) * pay] for i in range(len(M))]
        not_ = "Süreler tahmini: toplam süre dökümden, maddelere sırayla eşit bölündü."; ber = lambda t: _hm(o + t)
    else:
        kaynak = "sira"; bas, son = 0, max(1, len(M)); bl = [[i, i, i + 1] for i in range(len(M))]
        not_ = "Süreler tahmini: saat bilgisi yok, maddeler sırayla eşit gösterildi."; ber = None
    top = max(1e-9, son - bas); sure = None if kaynak == "sira" else round((son - bas) / 60)
    bloklar = [{"m": i, "bas": ber(b) if ber else "", "son": ber(e) if ber else "", "dk": None if not ber else round((e - b) / 60, 1),
                "pay": round((e - b) / top, 5)} for i, b, e in bl if e > b]
    mad = []
    for i, m in enumerate(M):
        bs = [x for x in bloklar if x["m"] == i]
        mad.append({"no": i + 1, "baslik": str(m.get("baslik") or "Gündem dışı"), "durum": str(m.get("durum") or ""),
                    "dk": None if not ber else round(sum(x["dk"] for x in bs)), "pay": round(sum(x["pay"] for x in bs), 4),
                    "araliklar": [f"{x['bas']}–{x['son']}" for x in bs] if ber else [],
                    "say": {t: sum(o["tur"] == t for o in m["ogeler"]) for t in TURLER if any(o["tur"] == t for o in m["ogeler"])}})
    return {"kaynak": kaynak, "not": not_, "tahmini": kaynak in ("dokum", "sira"), "bas": ber(bas) if ber else "", "son": ber(son) if ber else "",
            "sure_dk": sure, "bloklar": bloklar, "maddeler": mad}
def pano_veri(v, saatler=None):
    kararlar, isler, sorular, diger = [], [], [], []
    for i, m in enumerate(v["maddeler"]):
        mb = str(m.get("baslik") or "Gündem dışı")
        for o in m["ogeler"]:
            ortak = {"metin": str(o["metin"]), "saat": str(o.get("saat") or ""), "alinti": str(o.get("alinti") or ""), "madde": mb, "mno": i + 1,
                     "durum": str(o.get("durum") or "")}; ortak.update(cevap_alanlari(o))
            if o["tur"] == "karar":
                n = kucuk(o.get("netlik") or "").replace("ö", "o").replace("ü", "u"); ty = n in ("ortuk", "tek") or bool(str(o.get("varsayim") or "").strip())
                kararlar.append(dict(ortak, kim=str(o.get("kim") or ""), varsayim=str(o.get("varsayim") or ""),
                                     teyit=ty, neden=teyit_neden(o) if ty else "", net=(n == "acik" and not ty)))
            elif o["tur"] in ("is", "soz"):
                isler.append(dict(ortak, tur=o["tur"], sahip=" ".join(str(o.get("sahip") or o.get("kim") or "").split()), tarih=str(o.get("tarih") or "").strip()))
            elif o["tur"] == "soru": sorular.append(dict(ortak, kim=str(o.get("kim") or "")))
            else: diger.append(dict(ortak, tur=TURLER[o["tur"]], kim=str(o.get("kim") or "")))
    kisiler = {}
    for x in isler: kisiler.setdefault(x["sahip"] or "", []).append(x)
    sut = sorted(([k, xs] for k, xs in kisiler.items() if k), key=lambda a: (-len(a[1]), kucuk(a[0])))
    if "" in kisiler: sut.append(["", kisiler[""]])
    for _, xs in sut: xs.sort(key=lambda x: (not x["tarih"], x["tarih"], x["mno"]))  # tarihli olan önce, en yakın tarih üstte
    z = zaman_seridi(v, saatler)
    return {"baslik": str(v.get("baslik") or "Toplantı"), "tarih": str(v.get("tarih") or ""), "kararlar": kararlar,
            "sutunlar": [{"ad": k, "isler": xs} for k, xs in sut], "sorular": sorular, "diger": diger, "zaman": z,
            "say": {"karar": len(kararlar), "is": len(isler), "tarihsiz": sum(not x["tarih"] for x in isler), "soru": len(sorular), "sure_dk": z["sure_dk"]}}
def pano_html(v, saatler=None):
    veri = json.dumps(pano_veri(v, saatler), ensure_ascii=False).replace("</", "<\\/")
    return PANO.replace("__YAZI__", yazi_css()).replace("__BASLIK__", html.escape(str(v.get("baslik") or "Toplantı"))).replace("__VERI__", veri)
def gorsel_html(v, saatler=None):  # → (tür, html); yazılan dosya adı her iki türde <özet>-zihin-haritasi.html
    t = gorsel_tur(v); return t, (pano_html(v, saatler) if t == "karar_is" else harita_html(v))
PANO = r"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>__BASLIK__ — karar ve iş panosu</title>
<style>
/* kaynak: pano/renk.css + pano/yazi.css (--b-* belirteçleri; belge tek dosya ve çevrimdışı olduğu için kopya — değişince ikisini birlikte güncelle) */
:root{color-scheme:light dark;--b-zemin:#FAFAF8;--b-yuzey:#FFFFFF;--b-yuzey2:#F2F2EF;--b-murekkep:#1D1D1F;--b-m2:#5E5E63;--b-m3:#6E6E73;--b-cizgi:rgba(29,29,31,.08);--b-cizgi2:rgba(29,29,31,.16);--b-uzerinde:rgba(29,29,31,.045);--b-ton2:rgba(29,29,31,.11);
--b-vurgu:#175E46;--b-vurgu-hafif:rgba(23,94,70,.09);--b-gec:#B0533A;--b-ana:#175E46;--b-ana-yazi:#FFFFFF;--b-pirinc:#C9973A;--b-ipucu-zemin:#1D1D1F;--b-ipucu-yazi:#F5F5F7;--b-golge-panel:0 12px 40px rgba(0,0,0,.12);
--b-k-s:8px;--b-k-m:14px;--b-k-l:18px;--b-k-tam:999px;--b-yz-govde:15px;--b-yz-m:13.5px;--b-yz-k:12.5px;--b-yz-t:11.5px;--b-yz-e:10.5px;
--f-baslik:"Bricolage Grotesque","Avenir Next","Helvetica Neue",system-ui,sans-serif;--f-govde:"IBM Plex Sans",-apple-system,"Helvetica Neue",system-ui,sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--b-zemin:#161616;--b-yuzey:#1C1C1E;--b-yuzey2:#202022;--b-murekkep:#F2F2F2;--b-m2:#A1A1A6;--b-m3:#8A8A8F;--b-cizgi:rgba(242,242,242,.08);--b-cizgi2:rgba(242,242,242,.15);--b-uzerinde:rgba(242,242,242,.05);--b-ton2:rgba(242,242,242,.12);
--b-vurgu:#3E9B78;--b-vurgu-hafif:rgba(62,155,120,.15);--b-gec:#DE8467;--b-ana:#3E9B78;--b-ana-yazi:#0E1411;--b-pirinc:#D8A849;--b-ipucu-zemin:#F2F2F2;--b-ipucu-yazi:#161616;--b-golge-panel:0 12px 40px rgba(0,0,0,.45)}}
:root[data-theme=dark]{--b-zemin:#161616;--b-yuzey:#1C1C1E;--b-yuzey2:#202022;--b-murekkep:#F2F2F2;--b-m2:#A1A1A6;--b-m3:#8A8A8F;--b-cizgi:rgba(242,242,242,.08);--b-cizgi2:rgba(242,242,242,.15);--b-uzerinde:rgba(242,242,242,.05);--b-ton2:rgba(242,242,242,.12);
--b-vurgu:#3E9B78;--b-vurgu-hafif:rgba(62,155,120,.15);--b-gec:#DE8467;--b-ana:#3E9B78;--b-ana-yazi:#0E1411;--b-pirinc:#D8A849;--b-ipucu-zemin:#F2F2F2;--b-ipucu-yazi:#161616;--b-golge-panel:0 12px 40px rgba(0,0,0,.45)}
__YAZI__
@media print{@page{size:A4;margin:14mm 14mm 16mm}
:root,:root[data-theme=dark],:root:not([data-theme=light]){--b-zemin:#fff;--b-yuzey:#fff;--b-yuzey2:#F2F2EF;--b-murekkep:#1D1D1F;--b-m2:#5E5E63;--b-m3:#6E6E73;--b-cizgi:rgba(29,29,31,.14);--b-cizgi2:rgba(29,29,31,.22);--b-uzerinde:rgba(29,29,31,.06);--b-ton2:rgba(29,29,31,.13);
--b-vurgu:#175E46;--b-vurgu-hafif:rgba(23,94,70,.09);--b-gec:#B0533A;--b-ana:#175E46;--b-ana-yazi:#fff;--b-golge-panel:none;--b-yz-govde:12.5px;--b-yz-m:11.5px;--b-yz-k:11px;--b-yz-t:10.5px;--b-yz-e:9.5px}
html,body{background:#fff}header{padding:0 0 10px;margin-bottom:6px}main{padding:0;max-width:none}header h1{font-size:26px}
header button,#ayrinti{display:none!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.izgara{grid-template-columns:repeat(2,minmax(0,1fr))}.sutunlar{grid-template-columns:repeat(2,minmax(0,1fr))}
.kart,.sutun,.mad,.ozet{break-inside:avoid}h2{break-after:avoid;margin-top:26px}.sayim-kapat{break-before:auto}.serit{height:30px}}
*{box-sizing:border-box}html,body{margin:0;background:var(--b-zemin);color:var(--b-murekkep);font:var(--b-yz-govde)/1.55 var(--f-govde);-webkit-font-smoothing:antialiased}
main{max-width:1120px;margin:0 auto;padding:0 32px 72px}
header{max-width:1120px;margin:0 auto;padding:44px 32px 4px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 20px;align-items:end}
header .alt{grid-column:1;font:500 var(--b-yz-e) var(--f-mono);letter-spacing:.07em;text-transform:uppercase;color:var(--b-m3)}
header h1{grid-column:1;font:300 clamp(28px,3.6vw,40px)/1.1 var(--f-baslik);letter-spacing:-.02em;margin:0;overflow-wrap:anywhere;text-wrap:balance}
header button{grid-column:2;grid-row:1/3;align-self:end;font:inherit;font-size:var(--b-yz-k);padding:6px 14px;border:1px solid var(--b-cizgi2);border-radius:var(--b-k-tam);background:transparent;color:var(--b-murekkep);cursor:pointer;white-space:nowrap}
header button:hover{background:var(--b-uzerinde)}
:focus-visible{outline:2px solid var(--b-vurgu);outline-offset:2px}
.ozet{display:flex;flex-wrap:wrap;gap:12px 36px;margin:30px 0 4px}
.ozet span{display:grid;gap:2px;font-size:var(--b-yz-k);color:var(--b-m3)}.ozet b{font:300 30px/1 var(--f-baslik);letter-spacing:-.01em;color:var(--b-murekkep)}
.ozet .uy b{color:var(--b-gec)}
h2{display:flex;align-items:baseline;gap:8px;font:500 var(--b-yz-e) var(--f-mono);letter-spacing:.07em;text-transform:uppercase;color:var(--b-m3);margin:40px 0 12px}h2 small{font-size:inherit;font-weight:400;color:var(--b-m3)}
.izgara{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(min(290px,100%),1fr))}
.kart{display:flex;flex-direction:column;justify-content:flex-start;align-items:stretch;width:100%;text-align:left;font:inherit;color:inherit;background:var(--b-yuzey);border:1px solid var(--b-cizgi);border-radius:var(--b-k-m);padding:14px 16px 12px 32px;cursor:pointer;position:relative;transition:border-color .15s}
.kart:hover,.kart:focus-visible{border-color:var(--b-cizgi2);outline:none}.kart:focus-visible{box-shadow:0 0 0 2px var(--b-vurgu-hafif)}
.kart::before{content:"";position:absolute;left:14px;top:21px;width:7px;height:7px;border-radius:50%;background:var(--renk,var(--b-cizgi2))}
.kart .m{overflow-wrap:anywhere;white-space:normal;line-height:1.45}.kart .k{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;margin-top:8px;font-size:var(--b-yz-k);color:var(--b-m3)}
.kart .cv{margin-top:6px;font-size:var(--b-yz-m);color:var(--b-m2);overflow-wrap:anywhere}.kart .cv .kn{display:block;color:var(--b-m3);font-size:var(--b-yz-t);margin-top:2px}
.et{display:inline-block;font:500 var(--b-yz-e) var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--b-m3);padding:0 2px 0 0}
.et.tarih,.et.net,.et.dogru{color:var(--b-vurgu)}.et.tarihsiz,.et.teyit,.et.yanlis{color:var(--b-gec)}.et.kismen{color:var(--b-m2)}
.sutunlar{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr));align-items:start}
.sutun{background:var(--b-yuzey2);border-radius:var(--b-k-l);padding:14px}.sutun .bas{display:flex;align-items:baseline;gap:8px;padding:2px 4px 8px}
.sutun .ad{font:400 17px/1.25 var(--f-baslik);overflow-wrap:anywhere}.sutun.sahipsiz .ad{color:var(--b-m3);font-weight:300}.sutun .n{margin-left:auto;font:400 var(--b-yz-t) var(--f-mono);color:var(--b-m3);white-space:nowrap}
.cubuk{height:3px;border-radius:2px;background:var(--b-cizgi);margin:0 4px 12px}.cubuk i{display:block;height:100%;border-radius:2px;background:var(--b-vurgu)}
.sutun .kart+.kart{margin-top:8px}
.liste{display:grid;gap:8px}
.serit{display:flex;height:36px;border-radius:var(--b-k-s);overflow:hidden;gap:2px;margin:10px 0 4px}
.serit button{border:0;padding:0;margin:0;min-width:3px;font:500 var(--b-yz-k)/36px var(--f-mono);color:var(--b-m2);cursor:pointer;overflow:hidden;white-space:nowrap;text-align:center;border-radius:3px}
.serit button:hover,.serit button.sec{background:var(--b-vurgu)!important;color:var(--b-ana-yazi)}
.uclar{display:flex;justify-content:space-between;font:400 var(--b-yz-t) var(--f-mono);color:var(--b-m3)}
.sn{font-size:var(--b-yz-k);color:var(--b-m3);margin:2px 0 0}.sn.tah{color:var(--b-m2)}.sn.tah::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--b-gec);margin:0 7px 1px 0;vertical-align:middle}
.madlar{display:grid;margin-top:14px;border-top:1px solid var(--b-cizgi)}
.mad{display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:2px 12px;align-items:baseline;width:100%;text-align:left;font:inherit;color:inherit;background:none;border:0;border-bottom:1px solid var(--b-cizgi);border-radius:0;padding:11px 6px;cursor:pointer}
.mad:hover{background:var(--b-uzerinde)}.mad.sec{background:var(--b-vurgu-hafif)}
.mad .sw{font:500 var(--b-yz-t) var(--f-mono);color:var(--b-m3);text-align:right;padding-right:2px}.mad .b{overflow-wrap:anywhere}.mad .d{font:400 var(--b-yz-k) var(--f-mono);color:var(--b-m3);white-space:nowrap;text-align:right}
.mad .a{grid-column:2/4;font:400 var(--b-yz-t) var(--f-mono);color:var(--b-m3);overflow-wrap:anywhere}
.bos{color:var(--b-m3);font-size:var(--b-yz-m)}
#ayrinti{position:fixed;right:20px;bottom:20px;max-width:min(440px,calc(100% - 40px));background:var(--b-yuzey);border:1px solid var(--b-cizgi);border-radius:var(--b-k-l);padding:18px 20px 16px;box-shadow:var(--b-golge-panel);display:none;z-index:2}
#ayrinti b{display:block;margin:0 24px 6px 0;font:400 17px/1.3 var(--f-baslik);overflow-wrap:anywhere}#ayrinti .k{color:var(--b-m3);font-size:var(--b-yz-k);overflow-wrap:anywhere}
#ayrinti q{display:block;margin-top:10px;color:var(--b-m2);font-size:var(--b-yz-m);overflow-wrap:anywhere}
#ayrinti p{margin:8px 0 0;font-size:var(--b-yz-m);color:var(--b-m2);overflow-wrap:anywhere}#ayrinti a{color:var(--b-vurgu)}
#ayrinti button{position:absolute;right:8px;top:8px;width:28px;height:28px;border:0;border-radius:50%;background:none;color:var(--b-m3);font-size:18px;cursor:pointer}#ayrinti button:hover{background:var(--b-uzerinde);color:var(--b-murekkep)}
@media (max-width:640px){header{padding:28px 16px 4px}main{padding:0 16px 56px}header button{grid-column:1;grid-row:auto;justify-self:start;margin-top:8px}.ozet{gap:10px 24px}.ozet b{font-size:26px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<header><span class=alt id=alt></span><h1>__BASLIK__</h1><button id=yaz>Yazdır / PDF</button></header>
<main id=ana></main><div id=ayrinti role=dialog aria-live=polite></div>
<script>
const V=__VERI__;const A=document.getElementById('ayrinti'),ANA=document.getElementById('ana');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const AY=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const gun=t=>{const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(t||'');return m?`${+m[3]} ${AY[+m[2]-1]}`+(V.tarih&&V.tarih.slice(0,4)!==m[1]?' '+m[1]:''):String(t||'')};
const sure=d=>d==null?'':d<60?`${d} dk`:`${Math.floor(d/60)} sa`+(d%60?` ${d%60} dk`:'');
const G=i=>i%2?'var(--b-ton2)':'var(--b-uzerinde)';const S=V.say,Z=V.zaman;let say=0;const O=[];
const CE={dogru:'doğrulandı',yanlis:'yanlış',kismen:'kısmen'};
function cv(o){return o.cevap||o.kaynak?`<div class=cv>${o.cevap?`<span class="et ${esc(o.cd||'')}">${o.cd?CE[o.cd]:'cevap'}</span> ${esc(o.cevap)}`:''}${o.kaynak?`<span class=kn>Kaynak: ${esc(o.kaynak)}</span>`:''}</div>`:''}
function cvAyr(o){return (o.cevap?'<p>Cevap: '+esc(o.cevap)+'</p>':'')+(o.kaynak||o.kaynak_url?'<p>Kaynak: '+(o.kaynak_url?'<a href="'+esc(o.kaynak_url)+'" target=_blank rel="noopener noreferrer">'+esc(o.kaynak||o.kaynak_url)+'</a>':esc(o.kaynak))+'</p>':'')}
function kart(o,ic,renk){O.push(o);return `<button class=kart data-o="${O.length-1}" style="--renk:${renk}"><div class=m>${esc(o.metin)}</div>${cv(o)}<div class=k>${ic}</div></button>`}
document.getElementById('alt').textContent=[gun(V.tarih),'Karar ve iş panosu'].filter(Boolean).join(' · ');
let h=`<div class=ozet><span><b>${S.karar}</b> karar</span><span><b>${S.is}</b> iş</span>`+(S.tarihsiz?`<span class=uy><b>${S.tarihsiz}</b> tarihsiz iş</span>`:`<span><b>0</b> tarihsiz iş</span>`)
 +`<span><b>${S.soru}</b> açık soru</span>`+(S.sure_dk!=null?`<span>Süre <b>${esc(sure(S.sure_dk))}</b></span>`:'')+`</div>`;
h+=`<h2>Kararlar <small>(${S.karar})</small></h2>`+(V.kararlar.length?`<div class=izgara>`+V.kararlar.map(k=>kart(Object.assign({tur:'Karar'},k),
 [k.kim&&esc(k.kim),k.saat&&esc(k.saat.slice(0,5)),k.teyit?'<span class="et teyit">teyit bekliyor</span>':k.net?'<span class="et net">açıkça onaylandı</span>':''].filter(Boolean).join(' · '),'var(--b-vurgu)')).join('')+`</div>`:`<p class=bos>Karar yok.</p>`);
const mx=Math.max(1,...V.sutunlar.map(s=>s.isler.length));
h+=`<h2>Kim ne yapacak <small>(${S.is} iş)</small></h2>`+(V.sutunlar.length?`<div class=sutunlar>`+V.sutunlar.map(s=>`<section class="sutun${s.ad?'':' sahipsiz'}"><div class=bas><span class=ad>${esc(s.ad||'Sahipsiz')}</span><span class=n>${s.isler.length} iş`
 +(s.isler.filter(x=>!x.tarih).length?` · ${s.isler.filter(x=>!x.tarih).length} tarihsiz`:'')+`</span></div><div class=cubuk><i style="width:${Math.round(s.isler.length/mx*100)}%"></i></div>`
 +s.isler.map(x=>kart(Object.assign({tur:x.tur==='soz'?'Söz':'İş',kim:x.sahip},x),[x.tarih?`<span class="et tarih">${esc(gun(x.tarih))}</span>`:'<span class="et tarihsiz">tarihsiz</span>',
   x.tur==='soz'?'<span class=et>söz</span>':'',x.durum?`<span class=et>${esc(x.durum)}</span>`:'',`madde ${x.mno}`].filter(Boolean).join(''),x.tarih?'var(--b-m2)':'var(--b-gec)')).join('')+`</section>`).join('')+`</div>`:`<p class=bos>İş yok.</p>`);
if(V.sorular.length)h+=`<h2>Açık sorular <small>(${V.sorular.length})</small></h2><div class=izgara>`+V.sorular.map(q=>kart(Object.assign({tur:'Açık soru'},q),[q.kim&&esc(q.kim),`madde ${q.mno}`].filter(Boolean).join(' · '),'var(--b-m3)')).join('')+`</div>`;
if(V.diger.length)h+=`<h2>Sayılar ve iddialar <small>(${V.diger.length})</small></h2><div class=izgara>`+V.diger.map(q=>kart(q,[esc(q.tur),q.kim&&esc(q.kim),q.saat&&esc(q.saat.slice(0,5))].filter(Boolean).join(' · '),'var(--b-cizgi2)')).join('')+`</div>`;
h+=`<h2>Gündem ve süre</h2><p class="sn${Z.tahmini?' tah':''}">${esc(Z.not)}</p><div class=serit role=list>`+Z.bloklar.map((b,j)=>`<button role=listitem data-m="${b.m}" style="flex:${b.pay} 0 0;background:${G(b.m)}" title="${esc(V.zaman.maddeler[b.m].baslik)}${b.bas?' · '+b.bas+'–'+b.son:''}" aria-label="Madde ${b.m+1}${b.bas?', '+b.bas+'–'+b.son:''}">${b.m+1}</button>`).join('')
 +`</div>`+(Z.bas?`<div class=uclar><span>${esc(Z.bas)}</span><span>${esc(Z.son)}</span></div>`:'')
 +`<div class=madlar>`+Z.maddeler.map((m,i)=>`<button class=mad data-m="${i}"><span class=sw>${m.no}</span><span class=b>${esc(m.baslik)}${m.durum?` <span class=et>${esc(m.durum)}</span>`:''}</span><span class=d>${m.dk!=null?(m.dk?esc(sure(m.dk)):'saatli öğe yok'):(Math.round(m.pay*100)+'%')}</span>`
 +(m.araliklar.length?`<span class=a>${esc(m.araliklar.join(', '))}</span>`:'')+`</button>`).join('')+`</div>`;
ANA.innerHTML=h;
function goster(b,k,ek){A.innerHTML=`<button aria-label="Kapat">×</button><b>${esc(b)}</b><div class=k>${k.filter(Boolean).map(esc).join(' · ')}</div>${ek||''}`;A.style.display='block';A.querySelector('button').onclick=()=>A.style.display='none'}
ANA.addEventListener('click',e=>{const k=e.target.closest('[data-o]'),m=e.target.closest('[data-m]');
 if(k){const o=O[+k.dataset.o];goster(o.metin,[o.tur,o.kim,o.tarih?'son tarih '+gun(o.tarih):(o.tur==='İş'||o.tur==='Söz')?'tarihsiz':'',o.saat&&'saat '+o.saat,o.madde&&('madde '+o.mno+': '+o.madde)],
   (o.alinti?'<q>'+esc(o.alinti)+'</q>':'')+(o.neden?'<p>Teyit: '+esc(o.neden)+'</p>':'')+(o.durum?'<p>Durum: '+esc(o.durum)+'</p>':'')+cvAyr(o));return}
 if(m){const i=+m.dataset.m,d=Z.maddeler[i];document.querySelectorAll('.sec').forEach(x=>x.classList.remove('sec'));document.querySelectorAll(`[data-m="${i}"]`).forEach(x=>x.classList.add('sec'));
   goster(d.no+'. '+d.baslik,[d.durum,d.dk!=null?(d.dk?sure(d.dk):'saatli öğe yok'):'',Object.entries(d.say).map(([t,n])=>n+' '+({karar:'karar',is:'iş',soru:'açık soru',sayi:'sayı',iddia:'iddia',soz:'söz'})[t]).join(', ')],
     d.araliklar.length?'<p>'+esc(d.araliklar.join(', '))+'</p>':'')}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')A.style.display='none'});
document.getElementById('yaz').onclick=()=>{A.style.display='none';window.print()};
</script></html>"""
