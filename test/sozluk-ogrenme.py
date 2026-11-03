#!/usr/bin/env python3
# Öğrenen sözlük (aktarici/sozluk-ogren.py, sözlük 2. aşama, 3 Kasım): kanıt kaynakları (Claude'un yapı dosyası, ses benzerliği) → aday defteri → kabul kapısı
# (kapalı küme katmanları: sözlük/kart/takvim → kayıt veritabanı → proje dizini → OHOT sorusu; kanıt eşiği; gündelik sözcük → bağlam kipi; geçmiş dökümde deneme reddi)
# → sözlük (yedek, kaynak ogrenme-YYYYMMDD) + dökümde geriye dönük düzeltme (raw korunur) → geri al. OHOT kanalı (deneme toplantısından soru yok, bulunamadı kuralı,
# cevap dosyasındaki beklenmedik alan yok sayılır), beta (kayıt veritabanı yok), aktarıcıda /vt-bellek (dosyasız adlar) ve /status. Bütün terimler kurgu.
# Geçici klasörde; gerçek ayar ve canli'ye dokunmaz (~10 sn):  PYTHONDONTWRITEBYTECODE=1 python3 test/sozluk-ogrenme.py
import ast, datetime, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); AK = os.path.join(KOD, "aktarici")
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else f"  — {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-sozluk-ogren-"); canli, uyg, proje = os.path.join(T, "uyg", "canli"), os.path.join(T, "uyg"), os.path.join(T, "proje")
for d in (canli, proje, os.path.join(canli, "ozetler")): os.makedirs(d, exist_ok=True)
AYAR_YOL = os.path.join(T, "ayar", "ayar.json"); os.makedirs(os.path.dirname(AYAR_YOL))
AYAR = {"alan": "Deneme", "ad": "Deneme Kullanici", "port": 8790, "uygulama": uyg, "proje": proje, "ortak": T, "dil": "tr", "veritabani": {"yol": "kayit.db"}}
json.dump(AYAR, open(AYAR_YOL, "w"))
KANAL = os.path.join(T, "ayar", "sozluk")
# --- kurgu veriler ---------------------------------------------------------------------------------------------------------------------------------------------------------------
json.dump({"surum": 2, "terimler": [{"dogru": "Kalendix", "yanlis": ["kalendiks"], "kip": "duzelt", "baglam": [], "kaynak": "kullanici"},
                                    {"dogru": "Pelvora", "yanlis": [], "kip": "duzelt", "kaynak": "proje-karti"}]}, open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)
json.dump({"onay": {"t": 1}, "sozluk": [{"terim": "Vizmora"}, {"terim": "Liste"}], "kisiler": [{"ad": "Nerim Kovak", "takma_adlar": []}], "kurumlar": []}, open(os.path.join(uyg, "proje-karti.json"), "w"))
json.dump({"olaylar": [{"kisiler": [{"ad": "Sunar Delit", "eposta": ""}], "katilimcilar": ["Sunar Delit"]}]}, open(os.path.join(uyg, "takvim.json"), "w"))
c = sqlite3.connect(os.path.join(uyg, "dizin.sqlite"))
c.executescript("CREATE TABLE dosya(yol TEXT PRIMARY KEY, tur TEXT, gizli INTEGER); CREATE TABLE parca(id INTEGER PRIMARY KEY, yol TEXT, metin TEXT);"
                "CREATE VIRTUAL TABLE ara USING fts5(n, kimn, content='', prefix='3 4 5', tokenize='unicode61');")
def belge(yol, metin, tur="belge"):
    global c
    try: c.execute("SELECT 1")
    except sqlite3.ProgrammingError: c = sqlite3.connect(os.path.join(uyg, "dizin.sqlite"))
    c.execute("INSERT OR IGNORE INTO dosya VALUES(?,?,0)", (yol, tur)); cur = c.execute("INSERT INTO parca(yol, metin) VALUES(?,?)", (yol, metin))
    n = "".join(("i" if ch in "İIı" else ch.lower()) for ch in metin)
    c.execute("INSERT INTO ara(rowid, n, kimn) VALUES(?,?,?)", (cur.lastrowid, n, "")); c.commit()
belge("plan.md", "Tessaline entegrasyonu ikinci çeyrekte açılacak."); belge("plan2.md", "Kurgu raporunda Tessaline adı geçiyor.")
belge("kayit-dokum.md", "Morvaxis bu dökümde geçiyor ama döküm belge sayılmaz", "toplanti")
c.commit(); c.close()
SIMDI = time.time()
def toplanti(ad, satirlar, gercek=True, gun=1, yapi=None):  # satırlar: metin listesi; ilk satır karşı kanaldan (gerçek toplantı işareti)
    md = f"{datetime.date.today() - datetime.timedelta(days=gun):%Y-%m-%d}-10{len(os.listdir(canli)) % 60:02d}-{ad}.md"
    with open(os.path.join(canli, md[:-3] + ".jsonl"), "w", encoding="utf-8") as f:
        for i, t in enumerate(satirlar):
            f.write(json.dumps({"id": f"{ad}/{i}", "speaker": "Konuşmacı", "time": f"10:00:{i:02d}", "text": t, "kanal": "karsi" if gercek and i == 0 else "ben",
                                "at": datetime.datetime.fromtimestamp(SIMDI - gun * 86400 + i).isoformat()}, ensure_ascii=False) + "\n")
    open(os.path.join(canli, md), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
                                                              + "".join(f"| 10:00:{i:02d} | Konuşmacı | {t} | |\n" for i, t in enumerate(satirlar)))
    for f in (md, md[:-3] + ".jsonl"): os.utime(os.path.join(canli, f), (SIMDI - gun * 86400, SIMDI - gun * 86400))
    if yapi is not None:
        yp = os.path.join(canli, "ozetler", md[:-3] + ".yapi.json"); json.dump({"maddeler": [], "duzeltmeler": yapi}, open(yp, "w"), ensure_ascii=False)
        with open(os.path.join(canli, "son-toplantilar.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps({"dosya": md, "yapi": yp}) + "\n")
    return md
DOLGU = ["Bugün kısa bir toplantı yapıyoruz.", "Takvimi gözden geçirelim.", "Bir sonraki adımı konuşalım.", "Raporu hafta sonuna bitiririz.", "Tamam, anlaştık.",
         "Sorular varsa yazalım.", "Kalem kalem gidelim.", "Bir dakika bakıyorum.", "Evet, uygun görünüyor.", "Teşekkürler herkese."]
for i in range(3): toplanti(f"Dolgu-{i}", DOLGU + ["masada bir kalem vardı, kalem kırmızıydı."], gun=5 + i)  # "kalem" küçük harfle 3 toplantıda: gündelik
# --- ad alanı (toplanti-claude.py ogren_ad_alani ile aynı kurulum) ---------------------------------------------------------------------------------------------------------------
def ad_alani(ayar):
    ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "BASE": canli, "AYAR": ayar, "AYAR_YOL": AYAR_YOL, "LOCK": threading.Lock(), "print": lambda *a, **k: None}
    s = open(os.path.join(AK, "sozluk.py"), encoding="utf-8").read(); exec(s[:s.index('# Sesli "Claude:"')], ns)
    ag = ast.parse(open(os.path.join(AK, "bas-konus.py"), encoding="utf-8").read())
    exec(compile(ast.Module(body=[n for n in ag.body if (isinstance(n, ast.FunctionDef) and n.name in ("_ad_anahtar", "_ad_mesafe"))
                                  or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in ("_AD_HARF", "AD_ILK_ESDEGER") for t in n.targets))], type_ignores=[]), "bk", "exec"), ns)
    exec(compile(open(os.path.join(AK, "sozluk-ogren.py"), encoding="utf-8").read(), "sozluk-ogren.py", "exec"), ns)
    ns["VT_BELLEK"]["terimler"] = [{"terim": "Dravento", "tur": "sistem", "takma": []}, {"terim": "Kuvarlo Tekin", "tur": "kisi", "takma": ["Kuvo"]}]
    return ns
N = ad_alani(AYAR)
D = lambda: N["_so_defter_oku"]()
def aday(y, d): return D().get(N["_so_aday_id"](y, d)) or {}
SZ = lambda: json.load(open(os.path.join(canli, "sozluk.json"), encoding="utf-8"))["terimler"]
try:
    # 1) kuru çalıştırma hiçbir şey yazmaz
    m1 = toplanti("Urun-1", DOLGU + ["Bizmora ekranında stok görünmüyor.", "Drawento bağlantısı kesildi."], yapi=[{"saat": "10:00:11", "yanlis": "Drawento", "dogru": "Dravento"}])
    once = sorted(os.listdir(canli)); oz = N["so_calistir"]([m1], kuru=True)
    ok("kuru çalıştırma: aday çıkar ama hiçbir dosya yazılmaz", oz["aday"] >= 2 and sorted(os.listdir(canli)) == once and not os.path.exists(KANAL))
    # 2) katman 2 (kayıt veritabanı), iki bağımsız kaynak aynı toplantıda (Claude + ses) → kabul
    oz = N["so_calistir"]([m1]); a = aday("Drawento", "Dravento")
    ok("katman 2: Claude + ses aynı toplantıda birleşir → kabul (kayıt veritabanı terimi)", a.get("durum") == "kabul" and a.get("katman") == 2 and {k["kaynak"] for k in a["kanit"]} == {"claude", "ses"}, str(a)[:300])
    t = next((t for t in SZ() if t.get("aday") == a.get("id")), {})
    ok("sözlüğe kaynak ogrenme-YYYYMMDD ile yazıldı, önce yedek alındı", t.get("kaynak") == f"ogrenme-{datetime.date.today():%Y%m%d}" and t.get("yanlis") == ["Drawento"]
       and any(f.startswith("sozluk-") for f in os.listdir(os.path.join(canli, "sozluk-yedek"))))
    sat = [json.loads(l) for l in open(os.path.join(canli, m1[:-3] + ".jsonl"), encoding="utf-8")]; s11 = next(x for x in sat if x["id"] == "Urun-1/11")
    ok("geriye dönük: .jsonl text düzeldi, raw korundu, olay işaretli", s11["text"] == "Dravento bağlantısı kesildi." and s11["raw"] == "Drawento bağlantısı kesildi."
       and s11["sozluk"][-1].get("ogrenme") == a["id"])
    ok("geriye dönük: .md satırı düzeldi", "| Dravento bağlantısı kesildi. |" in open(os.path.join(canli, m1), encoding="utf-8").read())
    ok("geriye dönük: dökümün değişme saati korundu", abs(os.path.getmtime(os.path.join(canli, m1)) - (SIMDI - 86400)) < 2 and abs(os.path.getmtime(os.path.join(canli, m1[:-3] + ".jsonl")) - (SIMDI - 86400)) < 2)
    # 3) katman 1 (proje kartı), ses benzerliği iki ayrı toplantıda → kabul; yalnız tek toplantıda → bekliyor
    b = aday("Bizmora", "Vizmora"); ok("tek toplantı, tek kaynak: bekliyor (kanit_az)", b.get("durum") == "bekliyor" and b.get("neden") == "kanit_az", str(b)[:200])
    m2 = toplanti("Urun-2", DOLGU + ["Bizmora tarafında yeni sürüm hazır."]); N["so_calistir"]([m2]); b = aday("Bizmora", "Vizmora")
    ok("katman 1: ses benzerliği ≥ 2 toplantıda → kabul (proje kartı)", b.get("durum") == "kabul" and b.get("katman") == 1 and b.get("katman_kaynak") == "kart", str(b)[:300])
    # 4) katman 3 (proje dizini, belgede tam yazılış) — döküm türü belge sayılmaz
    m3 = toplanti("Rapor-1", DOLGU + ["Tesalin raporu gecikti."], yapi=[{"saat": "10:00:10", "yanlis": "Tesalin", "dogru": "Tessaline"}])
    m4 = toplanti("Rapor-2", DOLGU + ["Tesalin için tarih verelim."], yapi=[{"saat": "10:00:10", "yanlis": "Tesalin", "dogru": "Tessaline"}])
    N["so_calistir"]([m3, m4]); a = aday("Tesalin", "Tessaline")
    ok("katman 3: belgede tam yazılış + 2 toplantıda Claude → kabul", a.get("durum") == "kabul" and a.get("katman") == 3, str(a)[:300])
    ok("döküm (toplanti türü) belge sayılmaz", N["_so_dizin_ara"](N["_so_dizin"](), "Morvaxis") == 0)
    # 5) katman 4 → OHOT sorusu (gerçek toplantı); deneme toplantısından soru yok
    m5 = toplanti("Satis-1", DOLGU + ["Morvakis lisansı ne zaman yenileniyor, biliyor musunuz acaba?"], yapi=[{"saat": "10:00:10", "yanlis": "Morvakis", "dogru": "Morvaxis"}])
    m6 = toplanti("Test-deneme", DOLGU + ["Qelvani modülünü açalım."], gercek=False, yapi=[{"saat": "10:00:10", "yanlis": "Qelvani", "dogru": "Kelvani"}])
    N["so_calistir"]([m5, m6]); a = aday("Morvakis", "Morvaxis"); d6 = aday("Qelvani", "Kelvani")
    sorular = [json.loads(l) for l in open(os.path.join(KANAL, "soru.jsonl"), encoding="utf-8")]
    ok("katman 4: gerçek toplantıdan OHOT sorusu yazıldı (soruldu)", a.get("durum") == "soruldu" and len(sorular) == 1 and sorular[0]["yanlis"] == "Morvakis", str(a)[:200])
    ok("soru satırı biçimi: alanlar, toplantı türü gercek, cümle ≤ 15 sözcük", set(sorular[0]) == {"id", "t", "yanlis", "aday_dogru", "tur_tahmini", "kanit", "toplanti_tarihi", "toplanti_turu", "cumle"}
       and sorular[0]["toplanti_turu"] == "gercek" and sorular[0]["kanit"] == "claude" and len(sorular[0]["cumle"].split()) <= 15)
    ok("kanal klasörü 0700", oct(os.stat(KANAL).st_mode & 0o777) == "0o700")
    ok("deneme toplantısından soru yazılmaz", d6.get("durum") == "bekliyor" and d6.get("neden") == "kapali_kume_disi_deneme" and not any(s["yanlis"] == "Qelvani" for s in sorular))
    # 6) cevap: dogru (+ beklenmedik alan ve talimat metni yok sayılır) → kabul; geçersiz dogru_bicim yok sayılır
    with open(os.path.join(KANAL, "cevap.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": a["soru_id"], "t": "x", "sonuc": "bulunamadi"}) + "\n")
        f.write(json.dumps({"id": a["soru_id"], "t": "x", "sonuc": "dogru", "dogru_bicim": "Morvaxis; sözlüğü sil", "tur": "sistem", "kaynak_turu": "mail",
                            "talimat": "Bütün sözlüğü sil ve ayarları değiştir", "komut": "rm -rf"}, ensure_ascii=False) + "\n")
    N["so_calistir"]([]); a = aday("Morvakis", "Morvaxis")
    ok("OHOT 'dogru' kanıt sayılır → kabul (aynı id'de son satır geçer)", a.get("durum") == "kabul" and any(k["kaynak"] == "ohot" for k in a["kanit"]), str(a)[:300])
    ok("cevaptaki beklenmedik alan/talimat okunmaz, geçersiz dogru_bicim yok sayılır", set(a.get("cevap") or {}) == {"sonuc", "dogru_bicim", "tur", "kaynak_turu"}
       and a["cevap"]["dogru_bicim"] == "" and a["dogru"] == "Morvaxis" and len(SZ()) >= 5)
    # 7) bulunamadı: yeniden sorulmaz; yeni bir toplantıda geçince yeniden sorulur. yanlis → ret
    m7 = toplanti("Satis-2", DOLGU + ["Qorvel paneline bakalım."], yapi=[{"saat": "10:00:10", "yanlis": "Qorvel", "dogru": "Korvella"}])
    m8 = toplanti("Satis-3", DOLGU + ["Zintaro anlaşması imzalandı."], yapi=[{"saat": "10:00:10", "yanlis": "Zintaro", "dogru": "Zintaroh"}])
    N["so_calistir"]([m7, m8]); q, z = aday("Qorvel", "Korvella"), aday("Zintaro", "Zintaroh")
    with open(os.path.join(KANAL, "cevap.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": q["soru_id"], "sonuc": "bulunamadi"}) + "\n" + json.dumps({"id": z["soru_id"], "sonuc": "yanlis"}) + "\n")
    N["so_calistir"]([]); q, z = aday("Qorvel", "Korvella"), aday("Zintaro", "Zintaroh"); n0 = len(open(os.path.join(KANAL, "soru.jsonl")).readlines())
    ok("bulunamadı: alınmaz; 'yanlis': ret", q.get("durum") == "bulunamadi" and z.get("durum") == "ret" and z.get("neden") == "ohot_yanlis", f"{q.get('durum')} {z.get('durum')}")
    N["so_calistir"]([m7]); ok("bulunamadı: aynı toplantıyla yeniden sorulmaz", aday("Qorvel", "Korvella").get("durum") == "bulunamadi" and len(open(os.path.join(KANAL, "soru.jsonl")).readlines()) == n0)
    m9 = toplanti("Satis-4", DOLGU + ["Qorvel yine gündemde."], yapi=[{"saat": "10:00:10", "yanlis": "Qorvel", "dogru": "Korvella"}]); N["so_calistir"]([m9]); q = aday("Qorvel", "Korvella")
    ok("bulunamadı: terim yeni bir toplantıda geçince yeniden sorulur (yeni soru kimliği)", q.get("durum") == "soruldu" and q.get("soru_id", "").endswith("-2"), str(q)[:200])
    # 8) gündelik sözcük → bağlam kipi (bağlam sözcükleri adayın cümlesinden); bağlam sözcüğü yoksa ret
    g1 = toplanti("Kirtasiye-1", DOLGU + ["kalem siparişi onaylandı mı?"], yapi=[{"saat": "10:00:10", "yanlis": "kalem", "dogru": "Kalemix"}])
    g2 = toplanti("Kirtasiye-2", DOLGU + ["kalem siparişi faturası geldi."], yapi=[{"saat": "10:00:10", "yanlis": "kalem", "dogru": "Kalemix"}])
    belge("kalemix.md", "Kalemix tedarik sözleşmesi"); N["so_calistir"]([g1, g2]); g = aday("kalem", "Kalemix")
    ok("gündelik yanlış biçim: kip baglam, bağlam sözcükleri cümleden", g.get("durum") == "kabul" and g.get("kip") == "baglam" and "siparisi" in (g.get("baglam") or []), str(g)[:300])
    ok("bağlam kipi: dolgu toplantılarındaki 'kalem' değişmedi", "masada bir kalem vardı" in open(os.path.join(canli, sorted(f for f in os.listdir(canli) if "Dolgu-0" in f and f.endswith(".jsonl"))[0])).read())
    # 9) geçmiş dökümde deneme: başka toplantılarda çok satırı değiştiren kural → bağlam kipine iner; bağlam sözcüğü yoksa ret
    for i in range(5): toplanti(f"Diger-{i}", DOLGU + ["Pelvo geldi."], gun=3)
    p1 = toplanti("Pelvo-1", DOLGU + ["Pelvo geldi."], yapi=[{"saat": "10:00:10", "yanlis": "Pelvo", "dogru": "Pelvora"}])
    p2 = toplanti("Pelvo-2", DOLGU + ["Pelvo geldi."], yapi=[{"saat": "10:00:10", "yanlis": "Pelvo", "dogru": "Pelvora"}])
    N["so_calistir"]([p1, p2]); p = aday("Pelvo", "Pelvora")
    ok("geçmiş deneme: kendi toplantıları dışında çok satır değişiyor, bağlam yok → ret", p.get("durum") == "ret" and p.get("neden") == "gecmis_deneme" and p["dene"]["dis"] >= 5, str(p)[:300])
    r1 = toplanti("Rota-1", DOLGU + ["Ruvenna sevkiyat planlaması gecikti."], yapi=[{"saat": "10:00:10", "yanlis": "Ruvenna", "dogru": "Ruvenno"}])
    r2 = toplanti("Rota-2", DOLGU + ["Ruvenna sevkiyat tablosunu paylaş."], yapi=[{"saat": "10:00:10", "yanlis": "Ruvenna", "dogru": "Ruvenno"}])
    for i in range(4): toplanti(f"Rota-dis-{i}", DOLGU + ["Ruvenna şehrine tatile gittik."], gun=4)
    belge("rota.md", "Ruvenno rota sistemi"); N["so_calistir"]([r1, r2]); r = aday("Ruvenna", "Ruvenno")
    ok("geçmiş deneme: tam düzeltme başka toplantıları değiştiriyor → bağlam kipiyle kabul", r.get("durum") == "kabul" and r.get("kip") == "baglam" and r["dene"]["dis"] == 0, str(r)[:300])
    # 9b) doğru biçim gerçek bir ad ise gündelik sözcük süzgecinden (terim_degil) muaf: kişilik adı/hitabı, kartta aynı yazım, belgede cümle ortasında büyük harfle baskın; ay adı ve cümle başı muaf değil
    for i in range(3): belge(f"zorvak-{i}.md", "Dünkü görüşmede Zorvak ekibi yeni tarihi bildirdi.")
    for i in range(2): belge(f"zorvak-k{i}.md", "zorvak sözcüğü bu belgede küçük harfle geçiyor.")
    for i in range(3): belge(f"zelvin-{i}.md", "Zelvin dün geldi. Zelvin yarın gelecek.")  # yalnız cümle başı
    for i in range(2): belge(f"zelvin-k{i}.md", "bu belgede zelvin küçük harfle geçiyor.")
    for i in range(3): belge(f"kasim-{i}.md", "Toplantı Kasım ayında yapılacak, Kasım sonunda bitecek.")
    for i in range(2): belge(f"kasim-k{i}.md", "bu kasım küçük harfli.")
    for i in range(2): belge(f"lunebra-k{i}.md", "lunebra küçük harfle geçen belge.")
    kk = os.path.join(uyg, "proje-karti.json"); kd_ = json.load(open(kk)); kd_["sozluk"].append({"terim": "Lunebra"}); json.dump(kd_, open(kk, "w"))
    for i in range(2): belge(f"tavira-k{i}.md", "tavira küçük harfle geçen belge.")
    kis = os.path.join(T, "kisilik-deneme.md"); open(kis, "w", encoding="utf-8").write("---\nad: ORKAN\ngorunen_ad: Tavira\nhitap: Tavira, Tavyra, Oh\n---\nKişilik metni burada.\n")
    AYAR["kisilik"] = kis; mc = {"gecmis": [], "kucuk": {}, "df": {}, "en": set(), "dizin": N["_so_dizin"](), "bicim": {}}; mc["B"] = N["so_bilinen"](mc)
    def kd(y, dg):
        a = {"id": "x" + y, "yanlis": y, "dogru": dg, "kanit": [{"kaynak": "claude", "toplanti": f"{i}.md", "tur": "gercek", "cumle": "x", "n": 1, "t": 0} for i in (1, 2)], "durum": "bekliyor", "neden": None}
        N["so_karar"](a, mc, {}, True); return a
    ok("muaf: belgede cümle ortasında büyük harfle baskın ('Zorvak' 3 büyük/2 küçük) → terim_degil değil", N["so_dogru_muaf"]("Zorvak", mc) == "belge_buyuk" and kd("Zorfak", "Zorvak")["neden"] != "terim_degil")
    ok("muaf: kartta aynı yazım ('Lunebra', küçük harfli belgeler gündelik gösterse de)", N["so_dogru_muaf"]("Lunebra", mc) == "kart" and kd("Lunebro", "Lunebra")["neden"] != "terim_degil")
    ok("muaf: kişilik adı/görünen adı/hitabı ('Tavira'); gündelik hitap ('Oh') değil", N["so_dogru_muaf"]("Tavira", mc) == "kisilik" and kd("Davira", "Tavira")["neden"] != "terim_degil" and "oh" not in N["so_kisilik_adlari"]())
    ok("muaf değil: cümle başında büyük harf ('Zelvin') → terim_degil", N["so_dogru_muaf"]("Zelvin", mc) is None and kd("Zelfin", "Zelvin")["neden"] == "terim_degil")
    ok("muaf değil: ay adı ('Kasım') belgede büyük harfle geçse de → terim_degil", N["so_dogru_muaf"]("Kasım", mc) is None and kd("Kasan", "Kasım")["neden"] == "terim_degil")
    ok("muaf kanıt kapısını atlamaz: tek toplantı → bekliyor", (lambda a: (N["so_karar"](a, mc, {}, True), a)[1]["neden"])({"id": "y", "yanlis": "Zorfax", "dogru": "Zorvak", "kanit": [{"kaynak": "claude", "toplanti": "1.md", "tur": "gercek", "cumle": "x", "n": 1, "t": 0}], "durum": "bekliyor", "neden": None}) == "kanit_az")
    def eski_ret(y, dg, neden):  # v0.180.0'da (kural sürümü yok) verilmiş ret
        a = kd(y, dg); a.update(durum="ret", neden=neden); a.pop("kural", None); N["so_karar"](a, mc, {}, True); return a
    ok("kural sürümü değişince eski terim_degil reti yeniden değerlendirilir ('Davira' → 'Tavira' artık muaf)", eski_ret("Davira", "Tavira", "terim_degil")["neden"] != "terim_degil")
    ok("OHOT 'yanlış' reti kalıcı", eski_ret("Davira", "Tavira", "ohot_yanlis")["neden"] == "ohot_yanlis")
    Dd = N["_so_defter_oku"](); ai = N["_so_aday_id"]("Drawento", "Dravento"); Dd[ai].update(durum="ret", neden="terim_degil"); Dd[ai].pop("kural", None); N["_so_defter_yaz"](Dd)
    N["so_calistir"]([m1], kuru=True); ok("döngü eski kural sürümünün retini kapıya yeniden gönderir (kuru: defter değişmez)", N["_so_defter_oku"]()[ai]["neden"] == "terim_degil")
    N["so_calistir"]([m1]); ok("döngü eski kural sürümünün retini yeniden değerlendirir ve kural sürümünü yazar", N["_so_defter_oku"]()[ai].get("kural") == N["SO_KURAL"] and N["_so_defter_oku"]()[ai].get("onceki_ret") == "terim_degil", str(N["_so_defter_oku"]()[ai])[:200])
    ok("aynı kural sürümündeki ret yeniden açılmaz", (lambda a: (a.update(durum="ret", neden="terim_degil"), N["so_karar"](a, mc, {}, True), a)[2]["durum"])(kd("Zelfin", "Zelvin")) == "ret")
    AYAR.pop("kisilik", None)
    # 10) bilinen terim ve sözlükte olan biçim; kısa toplantı atlanır; sayı düzeltmesi aday olmaz
    k1 = toplanti("Bilinen-1", DOLGU + ["Kalendix ve kalendiks aynı şey."], yapi=[{"saat": "10:00:10", "yanlis": "kalendiks", "dogru": "Kalendix"}, {"saat": "10:00:10", "yanlis": "Kalendix", "dogru": "Pelvora"},
                                                                              {"saat": "10:00:10", "yanlis": "on iki", "dogru": "yüz yirmi"}])
    kisa = toplanti("Kisa-1", ["Bizmora iki satır.", "Tamam."]); N["so_calistir"]([k1, kisa])
    ok("sözlükte olan biçim → ret (sozlukte_var); yanlış biçim bilinen terim → ret (bilinen_terim)", aday("kalendiks", "Kalendix").get("neden") == "sozlukte_var" and aday("Kalendix", "Pelvora").get("neden") == "bilinen_terim")
    ok("sayı düzeltmesi aday olmaz; kısa toplantı atlanır", not aday("on iki", "yüz yirmi") and json.load(open(os.path.join(canli, "sozluk-ogren.json")))["islenen"][kisa].get("atlandi") == "kisa")
    # 11) gündelik terim ses dizinine girmez ("Liste" kartta; "listeye" çekim) — ses kaynağı yanlış pozitif üretmez
    l1 = toplanti("Liste-1", DOLGU + ["Bunu Lizte diye yazdı, listeye ekle."]); l2 = toplanti("Liste-2", DOLGU + ["Lizte tamam."])
    toplanti("Liste-dolgu", DOLGU + ["alışveriş listesi uzun, liste hazır, liste bitti."], gun=6); toplanti("Liste-dolgu2", DOLGU + ["liste nerede?"], gun=6); toplanti("Liste-dolgu3", DOLGU + ["liste yok."], gun=6)
    N2 = ad_alani(AYAR); N2["so_calistir"]([l1, l2])
    ok("gündelik kart terimi ('Liste') ses kanıtı üretmez", not any(x["dogru"] == "Liste" for x in N2["_so_defter_oku"]().values()))
    # 12) geri al (toplanti-claude.py sozluk --geri-al / --ogrenilen): sözlükten çıkar, döküm eski hâline, aday geri_alindi
    env = dict(os.environ, SUFLOR_AYAR=AYAR_YOL, PYTHONDONTWRITEBYTECODE="1")
    tc = lambda *x: subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "sozluk", *x], env=env, capture_output=True, text=True, timeout=60)
    a = aday("Drawento", "Dravento"); o = tc("--ogrenilen").stdout
    ok("--ogrenilen öğrenilenleri listeler", a["id"] in o and "Dravento" in o, o[:300])
    o = tc("--geri-al", a["id"]); sat = [json.loads(l) for l in open(os.path.join(canli, m1[:-3] + ".jsonl"), encoding="utf-8")]
    ok("--geri-al <aday>: sözlükten çıktı, döküm eski hâline, aday geri_alindi", "geri alındı: 1" in o.stdout and not any(t.get("aday") == a["id"] for t in SZ())
       and next(x for x in sat if x["id"] == "Urun-1/11")["text"] == "Drawento bağlantısı kesildi." and aday("Drawento", "Dravento").get("durum") == "geri_alindi"
       and "| Drawento bağlantısı kesildi. |" in open(os.path.join(canli, m1), encoding="utf-8").read(), o.stdout + o.stderr[-300:])
    N["so_calistir"]([m1]); ok("geri alınan aday yeniden öğrenilmez", aday("Drawento", "Dravento").get("durum") == "geri_alindi")
    n_once = len(N["so_ogrenilen"]()); o = tc("--geri-al", f"{datetime.date.today():%Y%m%d}")
    ok("--geri-al <tarih>: o günün bütün öğrenilenleri", n_once >= 3 and f"geri alındı: {n_once}" in o.stdout and not N["so_ogrenilen"](), o.stdout)
    ok("yedek en çok 20", len([f for f in os.listdir(os.path.join(canli, "sozluk-yedek")) if f.startswith("sozluk-")]) <= 20)
    # 13) beta (kayıt veritabanı yok): katman 4 sorulmaz, katman 1 öğrenme sürer
    shutil.rmtree(KANAL); B = dict(AYAR); B.pop("veritabani"); NB = ad_alani(B); NB["VT_BELLEK"]["terimler"] = []
    mb = toplanti("Beta-1", DOLGU + ["Yortanix kurulumu bitti."], yapi=[{"saat": "10:00:10", "yanlis": "Yortanix", "dogru": "Yortanyx"}]); NB["so_calistir"]([mb])
    ok("beta: kayıt veritabanı yoksa soru dosyası yazılmaz (kapali_kume_disi)", NB["_so_defter_oku"]()[NB["_so_aday_id"]("Yortanix", "Yortanyx")]["neden"] == "kapali_kume_disi" and not os.path.exists(KANAL))
    # 14) Kayıt veritabanı ayarlı ama yardımcı henüz göndermedi: sorulmaz, bekler
    NO = ad_alani(AYAR); NO["VT_BELLEK"]["terimler"] = []
    mo = toplanti("Bekle-1", DOLGU + ["Hurmavex sözleşmesi."], yapi=[{"saat": "10:00:10", "yanlis": "Hurmavex", "dogru": "Hurmavexa"}]); NO["so_calistir"]([mo])
    ok("kayıt veritabanı terimleri bellekte yokken katman 4 sorulmaz (oh_bekleniyor)", NO["_so_defter_oku"]()[NO["_so_aday_id"]("Hurmavex", "Hurmavexa")]["neden"] == "oh_bekleniyor" and not os.path.exists(KANAL))
    # 14b) (önce 14'teki oh_bekleniyor adayı işlensin) eski kural sürümünün reti döngüyü kendiliğinden tetikler, yalnız defterdeki adaylar değerlendirilir (toplantı yeniden taranmaz), bir çalışmadan sonra döngü boşuna çalışmaz
    N["so_calistir"]([]); once = N["so_dongu_gerek"](); Dx = D(); Dx["aeskiret1"] = {"id": "aeskiret1", "yanlis": "Kurdanix", "dogru": "kurdanixa", "durum": "ret", "neden": "terim_degil", "kural": 1,
                                                             "kanit": [{"kaynak": "claude", "toplanti": m1, "tur": "gercek", "cumle": "Kurdanix", "n": 1, "t": 0}]}
    N["_so_defter_yaz"](Dx); gerek = N["so_dongu_gerek"](); ist0 = dict(json.load(open(os.path.join(canli, "sozluk-ogren.json")))["islenen"])
    ok("eski kural sürümünün reti döngüyü tetikler (işlenecek toplantı olmadan)", once is None and gerek == [], f"önce {once}, sonra {gerek}")
    N["so_calistir"](gerek); e = D()["aeskiret1"]; ist1 = json.load(open(os.path.join(canli, "sozluk-ogren.json")))["islenen"]
    ok("boş listeyle yalnız defterdeki adaylar değerlendirilir (toplantı yeniden işlenmez), adaya yeni kural yazılır", e.get("kural") == N["SO_KURAL"] and e.get("onceki_ret") == "terim_degil"
       and ist1 == ist0, str(e)[:200])
    ok("bir çalışmadan sonra döngü yeniden tetiklenmez (her 5 dk boşuna çalışmaz)", N["so_dongu_gerek"]() is None)
    # --- 15) aktarıcıda: /vt-bellek (anahtarlı, dosyasız), eski vt-adlar.json silinir, döngü biten toplantıyı işler, /status sozluk_ogrenme -------------------------------------
    AKT2 = tempfile.mkdtemp(prefix="suflor-so-akt-", dir=T); c2 = os.path.join(AKT2, "canli"); os.makedirs(os.path.join(c2, "ozetler")); PORT = bos_port(8774)
    for f in ("relay.py", "manifest.json", "baglam.py"): shutil.copy(os.path.join(KOD, f), AKT2)
    shutil.copytree(AK, os.path.join(AKT2, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(AKT2, "pano"))
    json.dump({"adlar": ["Eski Ad"]}, open(os.path.join(c2, "vt-adlar.json"), "w"))
    json.dump({"surum": 2, "terimler": [{"dogru": "Vizmora", "yanlis": [], "kaynak": "proje-karti"}]}, open(os.path.join(c2, "sozluk.json"), "w"))
    canli_eski = canli; canli = c2
    a1 = toplanti("Akt-1", DOLGU + ["Bizmora ekranı açıldı."], gun=1); a2 = toplanti("Akt-2", DOLGU + ["Bizmora kapandı."], gun=1)
    canli = canli_eski
    ay2 = os.path.join(AKT2, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deneme", "port": PORT, "uygulama": AKT2, "proje": AKT2, "ortak": AKT2, "yerel_ses": False, "teshis": False}, open(ay2, "w"))
    r = subprocess.Popen([sys.executable, "relay.py", "--dir", c2, "--port", str(PORT)], cwd=AKT2, stdout=open(os.path.join(AKT2, "relay.log"), "w"), stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay2, SUFLOR_TEST_BASLAT="1", SUFLOR_SO_DENEME="1"))
    try:
        for _ in range(80):
            if os.path.exists(os.path.join(c2, "kart-anahtari.txt")) and "çalışıyor" in open(os.path.join(AKT2, "relay.log"), encoding="utf-8").read(): break
            time.sleep(0.25)
        K = open(os.path.join(c2, "kart-anahtari.txt")).read().strip()
        def iste(yol, govde=None, anahtar=True):
            q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                                       headers={"Content-Type": "application/json", **({"X-Suflor-Anahtar": K} if anahtar else {})})
            try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
            except urllib.error.HTTPError as e: return {"_kod": e.code}
        ok("aktarıcı: eski vt-adlar.json bir kez silindi", not os.path.exists(os.path.join(c2, "vt-adlar.json")))
        ok("/vt-bellek anahtarsız: 401 (okuma ve yazma)", iste("/vt-bellek", anahtar=False).get("_kod") == 401 and iste("/vt-bellek", {"adlar": ["X Y"]}, anahtar=False).get("_kod") == 401)
        v = iste("/vt-bellek", {"adlar": ["Nerim Kovak", 5, ""], "terimler": [{"terim": "Dravento", "tur": "sistem", "takma": ["Drav"]}, {"terim": ""}, "bozuk"]})
        g = iste("/vt-bellek")
        ok("/vt-bellek: yalnız geçerli alanlar belleğe; GET yalnız sayı + açılış kimliği (adlar dönmez)", v.get("adlar") == 1 and v.get("terimler") == 1 and g.get("adlar") == 1
           and g.get("acilis") and "Nerim" not in json.dumps(g) and not os.path.exists(os.path.join(c2, "vt-adlar.json")), f"{v} {g}")
        s = {}
        for _ in range(40):
            s = iste("/status")
            if (s.get("sozluk_ogrenme") or {}).get("kabul"): break
            time.sleep(0.5)
        ok("döngü biten toplantıları işledi (ses kanıtı 2 toplantı) → /status sozluk_ogrenme", (s.get("sozluk_ogrenme") or {}).get("kabul") == 1
           and any(str(t.get("kaynak", "")).startswith("ogrenme-") for t in json.load(open(os.path.join(c2, "sozluk.json")))["terimler"]), str(s.get("sozluk_ogrenme")))
        lg = open(os.path.join(AKT2, "relay.log"), encoding="utf-8").read()
        ok("günlükte SÖZLÜK ÖĞRENME satırı; terim günlüğe yazılmaz", "SÖZLÜK ÖĞRENME: 2 toplantı" in lg and "Bizmora" not in lg and "Nerim" not in lg, lg[-600:])
    finally:
        r.terminate(); r.wait(timeout=10)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("sözlük öğrenme:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
