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
                c.execute("INSERT INTO kayit (toplanti, baslik, tarih, madde, tur, kim, sahip, metin, son_tarih, saat, alinti, eklendi) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (toplanti, str(v.get("baslik") or "")[:200], str(v.get("tarih") or "")[:10], str(m.get("baslik") or "")[:200], o["tur"],
                           str(o.get("kim") or "")[:80] or None, str(o.get("sahip") or "")[:80] or None,
                           (str(o["metin"])[:500] + (f" (teyit bekliyor — {teyit_neden(o)})" if o["tur"] == "karar" and o in teyitler else ""))[:600], str(o.get("tarih") or "")[:20] or None,
                           str(o.get("saat") or "")[:8] or None, str(o.get("alinti") or "")[:300] or None, datetime.datetime.now().isoformat(timespec="seconds")))
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
    # toplantı çıktısı sayıları yapı dosyasından: karar · iş (iş + söz) · açık (açık soru + konuşulmayan/kısmen madde)
    og = [o for m in v["maddeler"] for o in m["ogeler"]]
    acik_madde = sum(1 for m in v["maddeler"] if kucuk(m.get("durum") or "") in ("açık", "acik", "kısmen", "kismen", "konuşulmadı", "konusulmadi"))
    return {"karar": sum(o["tur"] == "karar" for o in og), "is": sum(o["tur"] in ("is", "soz") for o in og),
            "acik": sum(o["tur"] == "soru" for o in og) + acik_madde}
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
def harita_html(v):
    veri = json.dumps(harita_veri(v), ensure_ascii=False).replace("</", "<\\/")
    return HARITA.replace("__BASLIK__", html.escape(str(v.get("baslik") or "Toplantı"))).replace("__VERI__", veri)
HARITA = r"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>__BASLIK__ — zihin haritası</title>
<style>
:root{--bg:#f6f4ee;--s1:#fffdf8;--tx:#1d211e;--t2:#5b625d;--bd:rgba(29,33,30,.14);--cizgi:rgba(29,33,30,.28);
--kok:#175e46;--madde:#3c4a43;--karar:#1f7a4f;--is:#a86b12;--soru:#6b4f9e;--sayi:#1f6f78;--iddia:#b3412e;--soz:#8a6420}
@media (prefers-color-scheme:dark){:root{--bg:#121614;--s1:#1a201d;--tx:#e8ebe6;--t2:#a5ada7;--bd:rgba(232,235,230,.14);--cizgi:rgba(232,235,230,.3);
--kok:#2a8a66;--madde:#9fb1a7;--karar:#47b07c;--is:#d9a03c;--soru:#b39ddb;--sayi:#5fb7c0;--iddia:#e0705c;--soz:#e0bb6c}}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}
header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 16px;border-bottom:1px solid var(--bd)}
header h1{font-size:16px;font-weight:600;margin:0 auto 0 0}header button{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--bd);border-radius:7px;background:var(--s1);color:var(--tx);cursor:pointer}
header button:hover{border-color:var(--cizgi)}#alan{overflow:auto;height:calc(100% - 56px);padding:16px}svg{display:block}
.d rect{fill:var(--s1);stroke:var(--bd);stroke-width:1}.d rect.ser{stroke:none}.d text{fill:var(--tx);font:13px -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;dominant-baseline:middle}.d{cursor:pointer}
.d .say{fill:var(--t2);font-size:11px}.d .cv{font-size:12px;font-weight:500}.d .kn{font-size:12px;opacity:.85}.d:hover rect{stroke:var(--cizgi)}path.c{fill:none;stroke:var(--cizgi);stroke-width:1.4}
#ayrinti{position:fixed;right:16px;bottom:16px;max-width:min(420px,calc(100% - 32px));background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;box-shadow:0 6px 24px rgba(0,0,0,.12);display:none}
#ayrinti b{display:block;margin-bottom:4px}#ayrinti .k{color:var(--t2);font-size:12.5px}#ayrinti q{display:block;margin-top:6px;font-style:italic}
#ayrinti button{float:right;border:0;background:none;color:var(--t2);font-size:16px;cursor:pointer}#ayrinti p{margin:6px 0 0;font-size:12.5px;overflow-wrap:anywhere}#ayrinti a{color:var(--kok)}
.cd-dogru{color:var(--karar)}.cd-yanlis{color:var(--iddia)}.cd-kismen{color:var(--is)}
</style>
<header><h1>__BASLIK__</h1><button id=ac>Hepsini aç</button><button id=kapa>Hepsini kapat</button><button id=png>Resim olarak indir</button></header>
<div id=alan><svg id=s xmlns="http://www.w3.org/2000/svg"></svg></div><div id=ayrinti role=dialog aria-live=polite></div>
<script>
const V=__VERI__;const RENK=t=>getComputedStyle(document.documentElement).getPropertyValue('--'+(t==='kok'?'kok':t==='madde'?'madde':t)).trim()||'#888';
const S=document.getElementById('s'),NS='http://www.w3.org/2000/svg',olc=document.createElement('canvas').getContext('2d');olc.font='13px -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif';
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
  tum.forEach((x,i)=>{const ts=el('tspan',{x:tx,dy:i?SY:0},t);if(x[0]){ts.setAttribute('class',x[0]);ts.style.fill=RENK(x[0]==='cv'?CR:'madde')}ts.textContent=x[1]});if(d.der===0)t.style.fill='#fff';
if(d.alt&&d.alt.length){const s=el('text',{class:'say',x:d.w-22,y:d.h/2},gr);s.textContent=d.acik?'‹':String(d.alt.length)+' ›';if(d.der===0)s.style.fill='#fff'}
const tik=()=>{if(d.alt&&d.alt.length){d.acik=!d.acik;ciz()}else goster(d)};gr.onclick=tik;gr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tik()}};
if(d.acik)(d.alt||[]).forEach(g)})(V)}
const A=document.getElementById('ayrinti');const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function goster(d){A.innerHTML=`<button aria-label="Kapat">×</button><b>${esc(d.ad)}</b><div class=k>${[d.kim,d.tarih&&('tarih '+d.tarih),d.saat&&('saat '+d.saat)].filter(Boolean).map(esc).join(' · ')}</div>${d.alinti?'<q>'+esc(d.alinti)+'</q>':''}${cvHtml(d)}`;A.style.display='block';A.querySelector('button').onclick=()=>A.style.display='none'}
function cvHtml(d){return (d.cevap?'<p class="cd-'+esc(d.cd||'')+'">Cevap: '+esc(d.cevap)+'</p>':'')+(d.kaynak||d.kaynak_url?'<p>Kaynak: '+(d.kaynak_url?'<a href="'+esc(d.kaynak_url)+'" target=_blank rel="noopener noreferrer">'+esc(d.kaynak||d.kaynak_url)+'</a>':esc(d.kaynak))+'</p>':'')}
function hepsi(v){(function g(d){d.acik=v||d.der===0;(d.alt||[]).forEach(g)})(V);ciz()}
document.getElementById('ac').onclick=()=>hepsi(true);document.getElementById('kapa').onclick=()=>hepsi(false);
document.getElementById('png').onclick=()=>{const k=S.cloneNode(true),cs=getComputedStyle(document.body);k.querySelectorAll('.d rect:first-child').forEach(r=>{if(!r.style.fill){r.setAttribute('fill',getComputedStyle(document.documentElement).getPropertyValue('--s1'));r.setAttribute('stroke','rgba(0,0,0,.15)')}});
k.querySelectorAll('text').forEach(t=>{t.setAttribute('font-family','-apple-system,Helvetica Neue,sans-serif');t.setAttribute('font-size',t.classList.contains('say')?'11':'13');t.querySelectorAll('tspan.cv,tspan.kn').forEach(q=>q.setAttribute('font-size','12'));t.setAttribute('dominant-baseline','middle');if(!t.style.fill)t.setAttribute('fill',cs.color)});
k.querySelectorAll('path').forEach(p=>{p.setAttribute('fill','none');p.setAttribute('stroke','rgba(120,120,120,.6)');p.setAttribute('stroke-width','1.4')});
const w=+S.getAttribute('width'),h=+S.getAttribute('height'),o=2,img=new Image(),c=document.createElement('canvas');c.width=w*o;c.height=h*o;
img.onload=()=>{const x=c.getContext('2d');x.fillStyle=cs.backgroundColor;x.fillRect(0,0,c.width,c.height);x.scale(o,o);x.drawImage(img,0,0);const a=document.createElement('a');a.download=document.title.replace(/[\\/:*?"<>|]/g,'-')+'.png';a.href=c.toDataURL('image/png');a.click()};
img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(k))};
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
    return PANO.replace("__BASLIK__", html.escape(str(v.get("baslik") or "Toplantı"))).replace("__VERI__", veri)
def gorsel_html(v, saatler=None):  # → (tür, html); yazılan dosya adı her iki türde <özet>-zihin-haritasi.html
    t = gorsel_tur(v); return t, (pano_html(v, saatler) if t == "karar_is" else harita_html(v))
PANO = r"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>__BASLIK__ — karar ve iş panosu</title>
<style>
:root{--bg:#f6f4ee;--s1:#fffdf8;--s2:#f0ede4;--tx:#1d211e;--t2:#5b625d;--bd:rgba(29,33,30,.14);--cizgi:rgba(29,33,30,.28);
--kok:#175e46;--karar:#1f7a4f;--is:#a86b12;--soru:#6b4f9e;--iddia:#b3412e;--soz:#8a6420;--gt:#fff;
--g1:#3f7d6a;--g2:#9a6c2e;--g3:#55689e;--g4:#94566a;--g5:#3f7f86;--g6:#727339}
@media (prefers-color-scheme:dark){:root{--bg:#121614;--s1:#1a201d;--s2:#222a26;--tx:#e8ebe6;--t2:#a5ada7;--bd:rgba(232,235,230,.14);--cizgi:rgba(232,235,230,.3);
--kok:#2a8a66;--karar:#47b07c;--is:#d9a03c;--soru:#b39ddb;--iddia:#e0705c;--soz:#e0bb6c;--gt:#101412;
--g1:#7cc2ab;--g2:#dcb06e;--g3:#9fb0e0;--g4:#dc9cb0;--g5:#7fc4cb;--g6:#c3c47e}}
@media print{:root{--bg:#fff;--s1:#fff;--s2:#f3f1ea;--tx:#1d211e;--t2:#5b625d;--bd:rgba(29,33,30,.2);--karar:#1f7a4f;--is:#a86b12;--soru:#6b4f9e;--iddia:#b3412e;--soz:#8a6420;--gt:#fff;
--g1:#3f7d6a;--g2:#9a6c2e;--g3:#55689e;--g4:#94566a;--g5:#3f7f86;--g6:#727339}
header button,#ayrinti{display:none!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}.kart,.sutun,.mad{break-inside:avoid}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}
main{max-width:1180px;margin:0 auto;padding:0 16px 40px}
header{display:flex;gap:8px 12px;align-items:center;flex-wrap:wrap;padding:14px 16px;border-bottom:1px solid var(--bd);max-width:1180px;margin:0 auto}
header h1{font-size:17px;font-weight:600;margin:0;overflow-wrap:anywhere}header .alt{color:var(--t2);font-size:12.5px;margin-right:auto}
header button{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--bd);border-radius:7px;background:var(--s1);color:var(--tx);cursor:pointer}
header button:hover{border-color:var(--cizgi)}
.ozet{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 4px}
.ozet span{background:var(--s1);border:1px solid var(--bd);border-radius:999px;padding:4px 12px;font-size:13px;color:var(--t2)}.ozet b{color:var(--tx);font-weight:600}
.ozet .uy{border-color:color-mix(in srgb,var(--iddia) 55%,transparent);background:color-mix(in srgb,var(--iddia) 10%,var(--s1));color:var(--iddia)}.ozet .uy b{color:var(--iddia)}
h2{font-size:13px;font-weight:600;color:var(--t2);margin:26px 0 10px;letter-spacing:.01em}h2 small{font-weight:400}
.izgara{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(min(290px,100%),1fr))}
.kart{display:block;width:100%;text-align:left;font:inherit;color:inherit;background:var(--s1);border:1px solid var(--bd);border-radius:9px;padding:10px 12px 10px 14px;cursor:pointer;position:relative}
.kart:hover,.kart:focus-visible{border-color:var(--cizgi);outline:none}.kart:focus-visible{box-shadow:0 0 0 2px color-mix(in srgb,var(--kok) 40%,transparent)}
.kart::before{content:"";position:absolute;left:5px;top:9px;bottom:9px;width:3px;border-radius:2px;background:var(--renk,var(--bd))}
.kart .m{overflow-wrap:anywhere;white-space:normal}.kart .k{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;margin-top:6px;font-size:12px;color:var(--t2)}
.kart .cv{margin-top:6px;font-size:12.5px;overflow-wrap:anywhere}.kart .cv .kn{display:block;color:var(--t2);font-size:11.5px;margin-top:1px}
.et.dogru{background:color-mix(in srgb,var(--karar) 14%,var(--s1));color:var(--karar)}.et.yanlis{background:color-mix(in srgb,var(--iddia) 14%,var(--s1));color:var(--iddia)}.et.kismen{background:color-mix(in srgb,var(--is) 15%,var(--s1));color:var(--is)}
#ayrinti a{color:var(--kok)}.et{display:inline-block;border-radius:5px;padding:1px 7px;font-size:11.5px;font-weight:500;background:var(--s2);color:var(--t2)}
.et.tarih{background:color-mix(in srgb,var(--karar) 12%,var(--s1));color:var(--karar)}
.et.tarihsiz{background:color-mix(in srgb,var(--iddia) 14%,var(--s1));color:var(--iddia);font-weight:600}
.et.teyit{background:color-mix(in srgb,var(--is) 15%,var(--s1));color:var(--is)}.et.net{background:color-mix(in srgb,var(--karar) 12%,var(--s1));color:var(--karar)}
.sutunlar{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr));align-items:start}
.sutun{background:var(--s2);border-radius:11px;padding:10px}.sutun .bas{display:flex;align-items:baseline;gap:8px;padding:2px 4px 8px}
.sutun .ad{font-weight:600;overflow-wrap:anywhere}.sutun.sahipsiz .ad{font-style:italic;color:var(--t2)}.sutun .n{margin-left:auto;color:var(--t2);font-size:12px;white-space:nowrap}
.cubuk{height:4px;border-radius:2px;background:color-mix(in srgb,var(--is) 18%,transparent);margin:0 4px 10px}.cubuk i{display:block;height:100%;border-radius:2px;background:var(--is)}
.sutun .kart+.kart{margin-top:8px}
.liste{display:grid;gap:8px}
.serit{display:flex;height:38px;border-radius:8px;overflow:hidden;background:var(--s2);margin:8px 0 4px}
.serit button{border:0;padding:0;margin:0;min-width:3px;font:600 12px/38px -apple-system,BlinkMacSystemFont,sans-serif;color:var(--gt);cursor:pointer;overflow:hidden;white-space:nowrap;text-align:center;border-right:1px solid var(--bg)}
.serit button:last-child{border-right:0}.serit button:hover,.serit button.sec{filter:brightness(1.12)}
.uclar{display:flex;justify-content:space-between;font-size:12px;color:var(--t2)}.sn{font-size:12.5px;color:var(--t2);margin:2px 0 0}.sn.tah{color:var(--is);font-weight:500}
.madlar{display:grid;gap:6px;margin-top:12px}
.mad{display:grid;grid-template-columns:12px 1fr auto;gap:4px 10px;align-items:baseline;width:100%;text-align:left;font:inherit;color:inherit;background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:8px 12px;cursor:pointer}
.mad:hover,.mad.sec{border-color:var(--cizgi)}.mad .sw{width:10px;height:10px;border-radius:3px;align-self:center}.mad .b{overflow-wrap:anywhere}.mad .d{color:var(--t2);font-size:12.5px;white-space:nowrap;text-align:right}
.mad .a{grid-column:2/4;color:var(--t2);font-size:12px;overflow-wrap:anywhere}
.bos{color:var(--t2);font-size:13px}
#ayrinti{position:fixed;right:16px;bottom:16px;max-width:min(440px,calc(100% - 32px));background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;box-shadow:0 6px 24px rgba(0,0,0,.16);display:none;z-index:2}
#ayrinti b{display:block;margin:0 20px 4px 0;overflow-wrap:anywhere}#ayrinti .k{color:var(--t2);font-size:12.5px;overflow-wrap:anywhere}#ayrinti q{display:block;margin-top:6px;font-style:italic;overflow-wrap:anywhere}
#ayrinti p{margin:6px 0 0;font-size:12.5px;overflow-wrap:anywhere}#ayrinti button{position:absolute;right:8px;top:6px;border:0;background:none;color:var(--t2);font-size:18px;cursor:pointer}
</style>
<header><h1>__BASLIK__</h1><span class=alt id=alt></span><button id=yaz>Yazdır / PDF</button></header>
<main id=ana></main><div id=ayrinti role=dialog aria-live=polite></div>
<script>
const V=__VERI__;const A=document.getElementById('ayrinti'),ANA=document.getElementById('ana');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const AY=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
const gun=t=>{const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(t||'');return m?`${+m[3]} ${AY[+m[2]-1]}`+(V.tarih&&V.tarih.slice(0,4)!==m[1]?' '+m[1]:''):String(t||'')};
const sure=d=>d==null?'':d<60?`${d} dk`:`${Math.floor(d/60)} sa`+(d%60?` ${d%60} dk`:'');
const G=i=>`var(--g${(i%6)+1})`;const S=V.say,Z=V.zaman;let say=0;const O=[];
const CE={dogru:'doğrulandı',yanlis:'yanlış',kismen:'kısmen'};
function cv(o){return o.cevap||o.kaynak?`<div class=cv>${o.cevap?`<span class="et ${esc(o.cd||'')}">${o.cd?CE[o.cd]:'cevap'}</span> ${esc(o.cevap)}`:''}${o.kaynak?`<span class=kn>Kaynak: ${esc(o.kaynak)}</span>`:''}</div>`:''}
function cvAyr(o){return (o.cevap?'<p>Cevap: '+esc(o.cevap)+'</p>':'')+(o.kaynak||o.kaynak_url?'<p>Kaynak: '+(o.kaynak_url?'<a href="'+esc(o.kaynak_url)+'" target=_blank rel="noopener noreferrer">'+esc(o.kaynak||o.kaynak_url)+'</a>':esc(o.kaynak))+'</p>':'')}
function kart(o,ic,renk){O.push(o);return `<button class=kart data-o="${O.length-1}" style="--renk:${renk}"><div class=m>${esc(o.metin)}</div>${cv(o)}<div class=k>${ic}</div></button>`}
document.getElementById('alt').textContent=[gun(V.tarih),'Karar ve iş panosu'].filter(Boolean).join(' · ');
let h=`<div class=ozet><span><b>${S.karar}</b> karar</span><span><b>${S.is}</b> iş</span>`+(S.tarihsiz?`<span class=uy><b>${S.tarihsiz}</b> tarihsiz iş</span>`:`<span><b>0</b> tarihsiz iş</span>`)
 +`<span><b>${S.soru}</b> açık soru</span>`+(S.sure_dk!=null?`<span>Süre <b>${esc(sure(S.sure_dk))}</b></span>`:'')+`</div>`;
h+=`<h2>Kararlar <small>(${S.karar})</small></h2>`+(V.kararlar.length?`<div class=izgara>`+V.kararlar.map(k=>kart(Object.assign({tur:'Karar'},k),
 [k.kim&&esc(k.kim),k.saat&&esc(k.saat.slice(0,5)),k.teyit?'<span class="et teyit">teyit bekliyor</span>':k.net?'<span class="et net">açıkça onaylandı</span>':''].filter(Boolean).join(' · '),'var(--karar)')).join('')+`</div>`:`<p class=bos>Karar yok.</p>`);
const mx=Math.max(1,...V.sutunlar.map(s=>s.isler.length));
h+=`<h2>Kim ne yapacak <small>(${S.is} iş)</small></h2>`+(V.sutunlar.length?`<div class=sutunlar>`+V.sutunlar.map(s=>`<section class="sutun${s.ad?'':' sahipsiz'}"><div class=bas><span class=ad>${esc(s.ad||'Sahipsiz')}</span><span class=n>${s.isler.length} iş`
 +(s.isler.filter(x=>!x.tarih).length?` · ${s.isler.filter(x=>!x.tarih).length} tarihsiz`:'')+`</span></div><div class=cubuk><i style="width:${Math.round(s.isler.length/mx*100)}%"></i></div>`
 +s.isler.map(x=>kart(Object.assign({tur:x.tur==='soz'?'Söz':'İş',kim:x.sahip},x),[x.tarih?`<span class="et tarih">${esc(gun(x.tarih))}</span>`:'<span class="et tarihsiz">tarihsiz</span>',
   x.tur==='soz'?'<span class=et>söz</span>':'',x.durum?`<span class=et>${esc(x.durum)}</span>`:'',`madde ${x.mno}`].filter(Boolean).join(''),x.tarih?'var(--is)':'var(--iddia)')).join('')+`</section>`).join('')+`</div>`:`<p class=bos>İş yok.</p>`);
if(V.sorular.length)h+=`<h2>Açık sorular <small>(${V.sorular.length})</small></h2><div class=izgara>`+V.sorular.map(q=>kart(Object.assign({tur:'Açık soru'},q),[q.kim&&esc(q.kim),`madde ${q.mno}`].filter(Boolean).join(' · '),'var(--soru)')).join('')+`</div>`;
if(V.diger.length)h+=`<h2>Sayılar ve iddialar <small>(${V.diger.length})</small></h2><div class=izgara>`+V.diger.map(q=>kart(q,[esc(q.tur),q.kim&&esc(q.kim),q.saat&&esc(q.saat.slice(0,5))].filter(Boolean).join(' · '),'var(--bd)')).join('')+`</div>`;
h+=`<h2>Gündem ve süre</h2><p class="sn${Z.tahmini?' tah':''}">${esc(Z.not)}</p><div class=serit role=list>`+Z.bloklar.map((b,j)=>`<button role=listitem data-m="${b.m}" style="flex:${b.pay} 0 0;background:${G(b.m)}" title="${esc(V.zaman.maddeler[b.m].baslik)}${b.bas?' · '+b.bas+'–'+b.son:''}" aria-label="Madde ${b.m+1}${b.bas?', '+b.bas+'–'+b.son:''}">${b.m+1}</button>`).join('')
 +`</div>`+(Z.bas?`<div class=uclar><span>${esc(Z.bas)}</span><span>${esc(Z.son)}</span></div>`:'')
 +`<div class=madlar>`+Z.maddeler.map((m,i)=>`<button class=mad data-m="${i}"><span class=sw style="background:${G(i)}"></span><span class=b>${m.no}. ${esc(m.baslik)}${m.durum?` <span class=et>${esc(m.durum)}</span>`:''}</span><span class=d>${m.dk!=null?(m.dk?esc(sure(m.dk)):'saatli öğe yok'):(Math.round(m.pay*100)+'%')}</span>`
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
