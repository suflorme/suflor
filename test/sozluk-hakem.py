#!/usr/bin/env python3
# Gemini hakemi (aktarici/sozluk-hakem.py, öğrenen sözlük 3. aşama, 3 Kasım): sahte Gemini sunucusuna karşı — beta'da ve gizli toplantıda ağa çıkılmaz, istekte yalnız ses + sabit yönerge
# (döküm/ad/terim yok; terim istemi ayarla açılır, kişi adı girmez), JSON cevap çözme ve bozuk cevap, yeniden deneme, günlük kota, günlük harcama sınırı, öbeklere bölme ve süre sınırı,
# hakem.jsonl 0600 + son işareti, hizalama (gerçek terim farkı kanıt; harf/noktalama/ek/sayı farkı kanıt değil), kabul kapısı (hakem tek başına bekler, hakem + Claude kabul),
# ölçüm kaydı yalnız sayı, kullanım kaydı gemini-ses.jsonl, öğrenme döngüsü hakem gelince toplantıyı yeniden işler. Bütün terimler kurgu; Google'a gidilmez, canli'ye dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sozluk-hakem.py     (~5 sn)
import ast, base64, datetime, http.server, json, os, struct, sys, tempfile, threading, time, types, wave
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); AK = os.path.join(KOD, "aktarici")
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else f"  — {ek}"))
    if not k: HATA.append(ad)
# --- sahte Gemini: gelen her ses parçasını içeriğinden tanır, METIN'deki dökümü döndürür ---------------------------------------------------------------------------------------
GELEN = []; DAV = {"tur": "ok", "n": 0}; METIN = {}
class Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def yaz(self, kod, b):
        b = b.encode() if isinstance(b, str) else b
        self.send_response(kod); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        ham = self.rfile.read(int(self.headers["Content-Length"])); g = json.loads(ham)
        GELEN.append({"yol": self.path, "anahtar": self.headers.get("x-goog-api-key"), "govde": g}); DAV["n"] += 1; tur = DAV["tur"]
        if tur == "500bir" and DAV["n"] % 2 == 1: return self.yaz(500, '{"error":{"code":500}}')
        if tur == "503ilk" and "3.6-flash" in self.path: return self.yaz(503, '{"error":{"code":503,"message":"high demand"}}')
        if tur == "kota": return self.yaz(429, '{"error":{"code":429,"message":"Quota exceeded for metric: generate_requests_per_model_per_day"}}')
        if tur == "401": return self.yaz(401, '{"error":{"code":401}}')
        ids, parts = [], g["contents"][0]["parts"]; out = []
        for i, p in enumerate(parts):
            if "inlineData" in p: out.append({"id": parts[i - 1]["text"].strip("[]"), "metin": METIN.get(base64.b64decode(p["inlineData"]["data"])[-64:], "")})
        if tur == "eksikcift" and len(out) == 10: out = [o for o in out if o["id"] != "p2"] + [dict(o, metin="başka bir cümle") for o in out if o["id"] == "p3"] * 1 + [o for o in out if o["id"] == "p3"]
        u = {"promptTokenCount": 1000, "candidatesTokenCount": 200, "thoughtsTokenCount": 50, "promptTokensDetails": [{"modality": "AUDIO", "tokenCount": 900}, {"modality": "TEXT", "tokenCount": 100}]}
        t = "bu JSON değil {" if tur == "bozuk" else ("```json\n" + json.dumps({"parcalar": out + [{"id": "p99", "metin": "uydurma"}]}, ensure_ascii=False) + "\n```")
        self.yaz(200, json.dumps({"candidates": [{"content": {"parts": [{"text": "düşünce", "thought": True}, {"text": t}]}}], "usageMetadata": u}, ensure_ascii=False))
PORT = bos_port(); sunucu = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Sahte); sunucu.handle_error = lambda *a: None
threading.Thread(target=sunucu.serve_forever, daemon=True).start()
# --- geçici kurulum -----------------------------------------------------------------------------------------------------------------------------------------------------------------
T = tempfile.mkdtemp(prefix="suflor-sozluk-hakem-"); canli, uyg = os.path.join(T, "uyg", "canli"), os.path.join(T, "uyg"); os.makedirs(os.path.join(canli, "ozetler"))
AYAR_YOL = os.path.join(T, "ayar", "ayar.json"); os.makedirs(os.path.dirname(AYAR_YOL))
AYAR = {"alan": "Deneme", "uygulama": uyg, "proje": T, "ortak": T, "dil": "tr", "kod": KOD}
json.dump({"surum": 2, "terimler": [{"dogru": "Pelvora", "yanlis": [], "kip": "duzelt", "kaynak": "kullanici"}, {"dogru": "DravenSync", "yanlis": [], "kaynak": "kullanici"},
                                    {"dogru": "Nerim Kovak", "yanlis": [], "kaynak": "kullanici", "tur": "kisi"}, {"dogru": "Kalendix", "yanlis": ["kalendiks"], "kaynak": "kullanici"}]},
          open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)
SIMDI = time.time()
DOLGU = ["Bugün kısa bir toplantı yapıyoruz.", "Takvimi gözden geçirelim.", "Bir sonraki adımı konuşalım.", "Raporu hafta sonuna bitiririz.", "Tamam, anlaştık.",
         "Sorular varsa yazalım.", "Kalem kalem gidelim.", "Bir dakika bakıyorum.", "Evet, uygun görünüyor.", "Teşekkürler herkese."]
SAYAC = [0]
def wav(kl, ad, sn=1.0):
    SAYAC[0] += 1; imza = (f"parca-{SAYAC[0]:06d}".encode() * 8)[:64]; n = int(16000 * sn) * 2 - 64
    with wave.open(os.path.join(kl, ad), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0" * n + imza)
    return imza
def toplanti(ad, parcalar, gizli=False, dk_once=60, yapi=None):  # parcalar: [(kanal, yerel metin, hakem metni, sn, bas)]
    md = f"{datetime.date.today():%Y-%m-%d}-09{SAYAC[0] % 60:02d}-{ad}.md"; kl = os.path.join(canli, "ses-arsivi", md[:-3]); os.makedirs(kl)
    satir = DOLGU + [p[1] for p in parcalar]
    with open(os.path.join(canli, md[:-3] + ".jsonl"), "w", encoding="utf-8") as f:
        for i, t in enumerate(satir): f.write(json.dumps({"id": f"{ad}/{i}", "speaker": "Konuşmacı", "time": f"09:00:{i:02d}", "text": t, "kanal": "karsi" if i == 0 else "ben"}, ensure_ascii=False) + "\n")
    open(os.path.join(canli, md), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
                                                              + ("| 09:00:00 | **GİZLİ** | açıldı — kapanana kadar hiçbir şey kaydedilmez | |\n" if gizli else "")
                                                              + "".join(f"| 09:00:{i:02d} | Konuşmacı | {t} | |\n" for i, t in enumerate(satir)))
    with open(os.path.join(kl, "parcalar.jsonl"), "w", encoding="utf-8") as f:
        for i, (kanal, yerel, hakem, sn, bas) in enumerate(parcalar):
            d = f"{kanal}-0900{i:02d}-{i:06d}.wav"; METIN[wav(kl, d, sn)] = hakem
            f.write(json.dumps({"dosya": d, "kanal": kanal, "bas": bas, "t0": SIMDI - 3600 + i * 5, "t1": SIMDI - 3600 + i * 5 + sn, "sn": sn, "sonuc": "satir", "metin": yerel}, ensure_ascii=False) + "\n")
    t = SIMDI - dk_once * 60
    for f in (os.path.join(canli, md), os.path.join(canli, md[:-3] + ".jsonl"), os.path.join(kl, "parcalar.jsonl")): os.utime(f, (t, t))
    if yapi is not None:
        yp = os.path.join(canli, "ozetler", md[:-3] + ".yapi.json"); json.dump({"maddeler": [], "duzeltmeler": yapi}, open(yp, "w"), ensure_ascii=False)
        with open(os.path.join(canli, "son-toplantilar.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps({"dosya": md, "yapi": yp}) + "\n")
    return md
DURUM = {"gelistirici": True, "gizli": False, "toplanti": False, "aktif": None}
def ad_alani(ayar, state=False):  # state: aktarıcı gibi (STATE var) — deneme aktarıcısı sayılır, hakem iş parçacığı yalnız SUFLOR_HK_DENEME ile (öğrenme döngüsü başlamaz)
    zaman = types.SimpleNamespace(time=time.time, sleep=lambda s: None, strftime=time.strftime, localtime=time.localtime)  # yeniden denemede beklenmesin
    ns = {"re": __import__("re"), "os": os, "json": json, "time": zaman, "datetime": datetime, "BASE": canli, "AYAR": ayar, "AYAR_YOL": AYAR_YOL, "LOCK": threading.Lock(), "print": lambda *a, **k: None,
          "gelistirici_mi": lambda: DURUM["gelistirici"], "gizli_acik": lambda: DURUM["gizli"], "gemini_anahtar": lambda: "deneme-anahtar", "GEMINI_HOST": f"127.0.0.1:{PORT}",
          "toplanti_acik": lambda: DURUM["toplanti"], "kaynak_dar": lambda: False, "aktif_dosya": lambda: DURUM["aktif"], "deneme_aktarici": lambda: False}
    if state: os.environ["SUFLOR_HK_DENEME"] = "1"; ns.update(STATE={}, deneme_aktarici=lambda: True, write=lambda ps: [open(y, "a", encoding="utf-8").write(m) for y, m in ps])
    s = open(os.path.join(AK, "sozluk.py"), encoding="utf-8").read(); exec(s[:s.index('# Sesli "Claude:"')], ns)
    ag = ast.parse(open(os.path.join(AK, "bas-konus.py"), encoding="utf-8").read())
    exec(compile(ast.Module(body=[n for n in ag.body if (isinstance(n, ast.FunctionDef) and n.name in ("_ad_anahtar", "_ad_mesafe"))
                                  or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in ("_AD_HARF", "AD_ILK_ESDEGER") for t in n.targets))], type_ignores=[]), "bk", "exec"), ns)
    for ad in ("sozluk-ogren.py", "sozluk-hakem.py"): exec(compile(open(os.path.join(AK, ad), encoding="utf-8").read(), ad, "exec"), ns)
    return ns
N = ad_alani(AYAR)
HY = lambda md: os.path.join(canli, "ses-arsivi", md[:-3], "hakem.jsonl")
def satirlar(y):
    try: return [json.loads(l) for l in open(y, encoding="utf-8")]
    except OSError: return []
try:
    # 1) hizalama
    C = lambda a, b: N["hakem_ciftler"](a, b, None)
    ok("gerçek terim farkı kanıt: Belvora → Pelvora (cümle ortasında)", C("Dün Belvora ekranında stok yoktu.", "Dün Pelvora ekranında stok yoktu.") == [("Belvora", "Pelvora")])
    ok("cümle başındaki ad yalnız kapalı kümedeyse kanıt", C("Belvora ekranı açık.", "Pelvora ekranı açık.") == [] and N["hakem_ciftler"]("Belvora ekranı açık.", "Pelvora ekranı açık.", N["so_bilinen"]()) == [("Belvora", "Pelvora")])
    ok("kesmeli ek kuralın parçası değil: Belvoraya → Pelvora'ya = Belvora → Pelvora", C("yarın Belvoraya gidelim", "yarın Pelvora'ya gidelim") == [("Belvora", "Pelvora")], str(C("yarın Belvoraya gidelim", "yarın Pelvora'ya gidelim")))
    ok("bitişik terim: git hab → GitHub", C("onu git hab hesabına koy", "onu GitHub hesabına koy") == [("git hab", "GitHub")], str(C("onu git hab hesabına koy", "onu GitHub hesabına koy")))
    ok("büyük/küçük harf ve noktalama farkı kanıt değil", C("pelvora ekranı, açık mı", "Pelvora ekranı açık mı?") == [] and C("tamam geldik", "Tamam, geldik.") == [])
    ok("ek farkı kanıt değil (raporu / raporunu)", C("Raporu bitirdik", "Raporunu bitirdik") == [] and C("Dravento'ya yazdım", "Draventoya yazdım") == [])
    ok("sayı yazımı farkı kanıt değil", C("on iki kişi geldi", "12 kişi geldi") == [] and C("yüz kişi geldi", "iki yüz kişi geldi") == [] and C("saat 3'te", "saat üçte") == [])
    ok("sıradan küçük harfli sözcük farkı kanıt değil", C("masada kalem var", "masada kitap var") == [])
    ok("cümle başındaki büyük harfli sıradan sözcük kanıt değil", C("bunu yaptık", "Şunu yaptık") == [])
    ok("hizalama kayması (benzerliği düşük çift) kanıt değil", C("dün akşam Ortel geldi", "dün akşam Vizmorakanta geldi") == [])
    # 2) JSON çözme
    m, k = N["hakem_coz"](json.dumps({"candidates": [{"content": {"parts": [{"text": '{"parcalar":[{"id":"p1","metin":"bir  iki"},{"id":"[p2]","metin":"üç"},{"id":"p7","metin":"x"}]}'}]}}],
                                      "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4}}), 2)
    ok("cevap çözülür (boşluk sadeleşir, köşeli kimlik kabul, bilinmeyen kimlik atılır)", m == {"p1": "bir iki", "p2": "üç"} and k["giris"] == 10, str(m))
    ok("bozuk cevap → None", N["hakem_coz"]("<html>", 1)[0] is None and N["hakem_coz"]('{"candidates":[{"content":{"parts":[{"text":"{\\"x\\":1}"}]}}]}', 1)[0] is None)
    PRC = [("karsi", "Belvora ekranında stok görünmüyor.", "Pelvora ekranında stok görünmüyor.", 2.0, False), ("ben", "Nerim bey toplantıya katılacak.", "Nerim Bey toplantıya katılacak.", 1.5, False),
          ("ben", "Konuş sorusu burada.", "x", 1.0, True), ("ben", "on iki kişi geldi", "12 kişi geldi", 1.0, False)]
    # 3) beta: ağa çıkılmaz; iş parçacığı başlamaz
    m1 = toplanti("Hakem-1", PRC); DURUM["gelistirici"] = False; n0 = len(GELEN); r = N["hakem_toplanti"](m1)
    ok("beta (geliştirici değil): hakem çalışmaz, istek yok, dosya yok", r["durum"] == "beta" and len(GELEN) == n0 and not os.path.exists(HY(m1)))
    th = threading.active_count(); ad_alani(AYAR, state=True); ok("beta: aktarıcıda hakem iş parçacığı başlamaz", threading.active_count() == th)
    DURUM["gelistirici"] = True; ad_alani(dict(AYAR, hakem=False), state=True); ad_alani(dict(AYAR, sozluk_ogren=False), state=True)
    ok("geliştiricide hakem: false ya da sozluk_ogren: false iken başlamaz", threading.active_count() == th)
    ad_alani(AYAR, state=True); ok("geliştiricide hakem iş parçacığı başlar", threading.active_count() == th + 1)
    # 4) gizli kip ve gizli işaretli toplantı
    DURUM["gizli"] = True; r = N["hakem_toplanti"](m1); DURUM["gizli"] = False
    ok("gizli kip açıkken istek yok", r["durum"] == "gizli" and len(GELEN) == n0)
    mg = toplanti("Gizli-1", PRC, gizli=True); r = N["hakem_toplanti"](mg); ok("dökümünde GİZLİ satırı olan toplantının sesi gitmez", r["durum"] == "gizli" and len(GELEN) == n0)
    # 5) normal çalışma: istek gövdesi
    r = N["hakem_toplanti"](m1); g = GELEN[-1] if len(GELEN) > n0 else {}
    ok("geliştiricide istek gitti, durum bitti", r["durum"] == "bitti" and len(GELEN) == n0 + 1, str(r)[:200])
    pr = g.get("govde", {}).get("contents", [{}])[0].get("parts", []); yazi = " ".join(p.get("text", "") for p in pr)
    ok("istek: generateContent + model + anahtar başlıkta (adreste değil)", g.get("yol") == "/v1beta/models/gemini-3.6-flash:generateContent" and g.get("anahtar") == "deneme-anahtar")
    ok("istekte yalnız sabit yönerge + [pN] + ses (Konuş parçası yok)", sum(1 for p in pr if "inlineData" in p) == 3 and [p["text"] for p in pr if "text" in p][1:] == ["[p1]", "[p2]", "[p3]"]
       and yazi.split(" [p1]")[0] == N["HK_YONERGE"])
    yasak = ["Belvora", "Pelvora", "Nerim", "Kovak", "DravenSync", "Kalendix", "stok", "Hakem-1", "ben-", "karsi-", ".wav", "Konuşmacı"]
    ok("istekte döküm metni, ad, sözlük terimi, dosya/toplantı adı yok", not any(x in yazi for x in yasak), [x for x in yasak if x in yazi])
    gc = g.get("govde", {}).get("generationConfig", {})
    ok("JSON şeması + sıcaklık 0 + düşük düşünme", gc.get("responseMimeType") == "application/json" and gc.get("responseSchema", {}).get("required") == ["parcalar"] and gc.get("temperature") == 0
       and gc.get("thinkingConfig") == {"thinkingLevel": "low"})
    hs = satirlar(HY(m1))
    ok("hakem.jsonl ses arşivi klasöründe, 0600, parça başına satır + son işareti", oct(os.stat(HY(m1)).st_mode & 0o777) == "0o600" and len([x for x in hs if x.get("dosya")]) == 3 and hs[-1].get("son")
       and next(x for x in hs if x.get("kanal") == "karsi")["metin"] == "Pelvora ekranında stok görünmüyor.")
    ku = [x for x in satirlar(os.path.join(canli, "gemini-ses.jsonl")) if x.get("is") == "hakem"]
    ok("kullanım kaydı gemini-ses.jsonl (is: hakem, belirteç, tutar)", len(ku) == 1 and ku[0]["giris_token"] == 1000 and ku[0]["cikis_token"] == 200 and ku[0]["dusunce_token"] == 50
       and abs(ku[0]["usd"] - (1000 * N["HAKEM_FIYAT"]["gemini-3.6-flash"][0] + 250 * N["HAKEM_FIYAT"]["gemini-3.6-flash"][1]) / 1e6) < 1e-5 and ku[0]["durum"] == "ok", str(ku)[:300])
    ol = satirlar(os.path.join(canli, "hakem-olcum.jsonl"))
    ok("ölçüm kaydı yazıldı (kanal başına, sözcük hata oranı)", len(ol) == 1 and ol[0]["parca"] == 3 and set(ol[0]["kanal"]) == {"ben", "karsi"} and ol[0]["kanal"]["karsi"]["wer_sozluk"] == 0.25
       and ol[0]["wer_ham"] is not None, str(ol)[:300])
    def yalniz_sayi(o, yol=""):
        if isinstance(o, dict): return all(yalniz_sayi(v, k) for k, v in o.items())
        if isinstance(o, str): return yol in ("t", "toplanti", "tarih", "model", "guven")
        return o is None or isinstance(o, (int, float, bool))
    ok("ölçüm kaydında yalnız sayı (+ zaman, toplantı dosyası, tarih, model); terim/metin yok", ol and yalniz_sayi(ol[0]) and not any(x in json.dumps(ol[0], ensure_ascii=False) for x in ("Pelvora", "Belvora", "Nerim", "stok")))
    ok("terim isabeti: kapalı kümedeki terim hakemde var, yerelde kaçtı", ol and ol[0]["terim_hakem"] >= 1 and ol[0]["terim_kacan"] >= 1, str(ol[0] if ol else None)[:200])
    n1 = len(GELEN); r = N["hakem_toplanti"](m1); ok("bitmiş toplantı yeniden gönderilmez", r.get("onceden") and len(GELEN) == n1)
    # 6) terim istemi (ayarla): yalnız sistem/ürün biçimli terim, kişi adı yok
    m2 = toplanti("Hakem-2", PRC[:1]); N["AYAR"]["hakem_terim_istemi"] = True; N["hakem_toplanti"](m2); N["AYAR"]["hakem_terim_istemi"] = False
    y2 = GELEN[-1]["govde"]["contents"][0]["parts"][0]["text"]
    ok("hakem_terim_istemi: sistem terimi istemde, kişi adı ve sıradan ad yok", "DravenSync" in y2 and "Nerim" not in y2 and "Pelvora" not in y2, y2[-120:])
    # 7) kabul kapısı: hakem tek başına bekler; hakem + Claude aynı toplantıda kabul
    oz = N["so_calistir"]([m1]); a = N["_so_defter_oku"]().get(N["_so_aday_id"]("Belvora", "Pelvora")) or {}
    ok("hakem tek başına, tek toplantıda: bekliyor (kanit_az)", a.get("durum") == "bekliyor" and a.get("neden") == "kanit_az" and [k["kaynak"] for k in a["kanit"]] == ["hakem"], str(a)[:300])
    ok("hakem kanıtının cümlesi yerel metinden (≤ 15 sözcük)", a and "Belvora" in a["kanit"][0]["cumle"] and len(a["kanit"][0]["cumle"].split()) <= 15)
    ok("sayı farkı ve harf farkı aday olmadı", not any(x["dogru"] in ("12", "Bey") for x in N["_so_defter_oku"]().values()))
    ys = os.path.join(canli, "ozetler", m1[:-3] + ".yapi.json"); json.dump({"duzeltmeler": [{"saat": "09:00:10", "yanlis": "Belvora", "dogru": "Pelvora"}]}, open(ys, "w"))
    with open(os.path.join(canli, "son-toplantilar.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps({"dosya": m1, "yapi": ys}) + "\n")
    ok("yapı dosyası sonradan gelince toplantı yeniden işlenecek", m1 in N["so_bekleyen"](json.load(open(os.path.join(canli, "sozluk-ogren.json")))))
    N["so_calistir"]([m1]); a = N["_so_defter_oku"]().get(N["_so_aday_id"]("Belvora", "Pelvora")) or {}
    ok("hakem + Claude aynı toplantıda → kabul, sözlüğe yazıldı", a.get("durum") == "kabul" and {k["kaynak"] for k in a["kanit"]} == {"hakem", "claude"}
       and any(t.get("aday") == a.get("id") for t in json.load(open(os.path.join(canli, "sozluk.json")))["terimler"]), str(a)[:300])
    # hakem sonradan gelince yeniden işleme (so_bekleyen)
    m3 = toplanti("Hakem-3", PRC[:1]); N["so_calistir"]([m3]); d = json.load(open(os.path.join(canli, "sozluk-ogren.json")))
    ok("hakem gelmeden işlenen toplantı: hakem yok işaretli", d["islenen"][m3].get("hakem") is False and m3 not in N["so_bekleyen"](d))
    N["hakem_toplanti"](m3); ok("hakem bitince toplantı yeniden işlenecek", m3 in N["so_bekleyen"](d))
    # 8) hatalar: bozuk cevap, 500 sonra başarı, günlük kota, 401
    m4 = toplanti("Hakem-4", PRC[:2]); DAV["tur"] = "bozuk"; n1 = len(GELEN); r = N["hakem_toplanti"](m4)
    ok("bozuk cevap: en çok 3 deneme, durum hata, son işareti yok", r["durum"] == "hata" and r.get("hata") == "bozuk_cevap" and len(GELEN) - n1 == 3 and not N["_so_hakem_hazir"](m4))
    DAV.update(tur="500bir", n=0); n1 = len(GELEN); r = N["hakem_toplanti"](m4); ok("HTTP 500 bir kez → yeniden denenir, bitti", r["durum"] == "bitti" and len(GELEN) - n1 == 2, str(r)[:200])
    m5 = toplanti("Hakem-5", PRC[:2]); DAV["tur"] = "kota"; n1 = len(GELEN); r = N["hakem_toplanti"](m5); ok("günlük kota (429 per_day): yeniden denenmez, durum kota", r["durum"] == "kota" and len(GELEN) - n1 == 1)
    DAV["tur"] = "401"; n1 = len(GELEN); r = N["hakem_toplanti"](m5); ok("401: yeniden denenmez, durum hata", r["durum"] == "hata" and len(GELEN) - n1 == 1)
    DAV["tur"] = "ok"
    # 8b) ölçüm: kanal düzeyinde hizalama, normalleştirme (harf/noktalama) sonrası
    KAY = [("ben", "Dün Kormand ekranında stok görünmüyor.", "Dün Gormand ekranında stok görünmüyor.", 2.0, False), ("ben", "Sonra rapor hazır oldu.", "Sonra rapor hazır oldu.", 2.0, False),
           ("ben", "Nerim bey yarın gelecek.", "Nerim Bey yarın gelecek.", 2.0, False), ("karsi", "Tamam anlaştık.", "Tamam, anlaştık.", 2.0, False)]
    m11 = toplanti("Hakem-11", KAY); r = N["hakem_toplanti"](m11); hs = [x for x in satirlar(HY(m11)) if x.get("dosya")]
    ol = satirlar(os.path.join(canli, "hakem-olcum.jsonl"))[-1]
    ok("ölçüm: kanal düzeyinde hizalama (ben 1/13 hata, yerelde fazla sözcük yok)", r["durum"] == "bitti" and ol["kanal"]["ben"]["wer_sozluk"] == 0.077 and ol["kanal"]["karsi"]["wer_sozluk"] == 0 and ol["yerel_fazla"] == 0
       and "hakem_bos_yerel_dolu" not in ol, str(ol)[:300])
    ok("kayma: çift çıktı (Kormand → Gormand; harf farkı Nerim bey çift değil), ölçümde çift sayısı 1", ol["cift"] == 1 and [(c["yanlis"], c["aday_dogru"]) for c in N["_kaynak_hakem"]({"md": m11, "B": None})] == [("Kormand", "Gormand")])
    ok("kayma: kanıt cümlesi doğru parçadan (yerel taraftaki sözcüğün parçası)", "Kormand" in N["_kaynak_hakem"]({"md": m11, "B": None})[0]["cumle"] and "Nerim" not in N["_kaynak_hakem"]({"md": m11, "B": None})[0]["cumle"])
    ok("kayma: kimliği kayan boş parça eksik sayılmaz ölçümü bozmaz (parça kaydı 4)", len(hs) == 4 and ol["parca"] == 4)
    # gerçek model: yedeğe geçilince kayıtlara cevap veren model yazılır
    DAV.update(tur="503ilk", n=0); m12 = toplanti("Hakem-12", PRC[:1]); r = N["hakem_toplanti"](m12); DAV["tur"] = "ok"
    hs = satirlar(HY(m12)); ol = satirlar(os.path.join(canli, "hakem-olcum.jsonl"))[-1]
    ok("503 → yedek model: hakem.jsonl ve ölçümde model cevap veren (gemini-3.8-flash), ilk istenen değil", r["durum"] == "bitti" and hs[0]["model"] == "gemini-3.8-flash" and hs[-1]["model"] == "gemini-3.8-flash" and ol["model"] == "gemini-3.8-flash", str(hs)[:200])
    # 9) günlük harcama sınırı
    N["AYAR"]["hakem_gunluk_usd"] = 0.0005; m6 = toplanti("Hakem-6", PRC[:2]); n1 = len(GELEN); r = N["hakem_toplanti"](m6)
    ok("günlük harcama sınırı dolunca istek atılmaz (sinir)", r["durum"] == "sinir" and len(GELEN) == n1)
    N["AYAR"]["hakem_gunluk_usd"] = 1.0
    # 10) öbeklere bölme ve toplantı başına süre sınırı
    m7 = toplanti("Hakem-7", [("ben", f"cümle {i}", f"cümle {i}", 2.0, False) for i in range(6)]); N["HK_OBEK_SN"] = 4.5; n1 = len(GELEN)
    r = N["hakem_toplanti"](m7, en_cok_sn=9); N["HK_OBEK_SN"] = 300
    hs = satirlar(HY(m7)); ok("öbeklere bölünür (≤ 4,5 sn) ve süre sınırında kırpılır (9 sn → 4 parça)", len(GELEN) - n1 == 2 and len([x for x in hs if x.get("dosya")]) == 4 and hs[-1].get("kirpildi") is True, f"{len(GELEN) - n1} istek, {hs[-1:]}")
    # 11) kuru çalıştırma: canli'ye yazılmaz
    m8 = toplanti("Hakem-8", PRC[:2]); cik = os.path.join(T, "kuru"); once = {f: os.path.getsize(os.path.join(canli, f)) for f in ("gemini-ses.jsonl", "hakem-olcum.jsonl")}
    r = N["hakem_toplanti"](m8, kuru=True, cikti=cik)
    ok("kuru: hakem.jsonl, ölçüm ve kullanım yalnız çıktı klasöründe", r["durum"] == "bitti" and not os.path.exists(HY(m8)) and os.path.exists(os.path.join(cik, "hakem.jsonl"))
       and os.path.exists(os.path.join(cik, "hakem-olcum.jsonl")) and os.path.exists(os.path.join(cik, "gemini-ses.jsonl"))
       and once == {f: os.path.getsize(os.path.join(canli, f)) for f in once})
    # 12) döngü seçimi: süren, yeni biten, gizli, bitmiş
    m9 = toplanti("Hakem-9", PRC[:1], dk_once=3); m10 = toplanti("Hakem-10", PRC[:1]); DURUM["aktif"] = m10
    b = N["hakem_bekleyen"]({}); DURUM["aktif"] = None
    ok("bekleyen: süren ve 10 dk'dan yeni biten toplantı yok, bitmiş yok, gizli işaretli var (turda gizli olur)", m9 not in b and m10 not in b and m1 not in b and mg in b, str(b))
    n1 = len(GELEN); N["hakem_tur"](); d = json.load(open(os.path.join(canli, "sozluk-hakem.json")))["toplantilar"]
    ok("tur: gizli toplantı işaretlenir, istek gitmez; bekleyen toplantı işlenir", d[mg]["durum"] == "gizli" and d.get(m10, {}).get("durum") == "bitti" and N["_so_hakem_hazir"](m10), str(d)[:300])
    ok("durum dosyası 0600", oct(os.stat(os.path.join(canli, "sozluk-hakem.json")).st_mode & 0o777) == "0o600")
    DURUM["toplanti"] = True; n1 = len(GELEN); N["hakem_tur"](); DURUM["toplanti"] = False
    ok("toplantı sürerken tur istek atmaz", len(GELEN) == n1)
    # 14) 10 Kasım düzeltmesi: öbek ≤ 10 parça, kimlik doğrulama (eksik/çift → hizasız), ortak normalleştirme ve dışlama
    sys.path.insert(0, KOD); import zeka as ZK
    ok("normalleştirme: Türkçe İ/ı, yüzde/%, sayı → yazı, kesme, dolgu ve (gülme) atılır", ZK.dokum_norm("İşte %20 arttı (gülme) hı, ıı Pelvora'ya 3'te IŞIK :D") == ["işte", "yüzde", "yirmi", "arttı", "pelvoraya", "üçte", "ışık"], str(ZK.dokum_norm("İşte %20 arttı (gülme) hı, ıı Pelvora'ya 3'te IŞIK :D")))
    ok("normalleştirme: 'yüzde yirmi' = '%20' = '20%'; 100 → yüz; 150 olduğu gibi", ZK.dokum_norm("yüzde yirmi") == ZK.dokum_norm("%20") == ZK.dokum_norm("20%") and ZK.dokum_norm("100 ve 150") == ["yüz", "ve", "150"])
    ok("öbek en çok 10 parça", N["HK_OBEK_PARCA"] == 10 and [len(o) for o in N["_hk_obekler"]([{"sn": 1.0, "dosya": str(i)} for i in range(23)])] == [10, 10, 3])
    ok("hakem_coz: aynı kimlik iki kez gelirse ikisi de atılır", N["hakem_coz"](json.dumps({"candidates": [{"content": {"parts": [{"text": '{"parcalar":[{"id":"p1","metin":"a"},{"id":"p1","metin":"b"},{"id":"p2","metin":"c"}]}'}]}}]}), 2)[0] == {"p2": "c"})
    m13 = toplanti("Hakem-13", [("ben", f"cümle numara {i} bir iki üç", f"cümle numara {i} bir iki üç", 2.0, False) for i in range(12)]); DAV["tur"] = "eksikcift"; n1 = len(GELEN)
    r = N["hakem_toplanti"](m13); DAV["tur"] = "ok"; hs = [x for x in satirlar(HY(m13)) if x.get("dosya")]; ol = satirlar(os.path.join(canli, "hakem-olcum.jsonl"))[-1]
    ok("12 parça → 2 istek (10 + 2)", r["durum"] == "bitti" and len(GELEN) - n1 == 2, str(len(GELEN) - n1))
    ok("kimliği eksik parça eksik+hizasız, çift kimlikli parça hizasız; öteki parçalar temiz", [bool(x.get("hizasiz")) for x in hs] == [False, True, True] + [False] * 9 and hs[1].get("eksik") is True, str([(x.get("hizasiz"), x.get("eksik")) for x in hs]))
    ok("ölçüm sürüm 2: hizasız parçalar dışlanan olarak sayılır, kalan 10 parça hatasız", ol["surum"] == 2 and ol["parca"] == 12 and ol["olculen"] == 10 and ol["dislanan"] == {"hizasiz": 2} and ol["wer_sozluk"] == 0.0, str(ol)[:300])
    ok("sözlük öğrenmesi hizasız parçayı kullanmaz", len(N["_hk_kanallar"](os.path.join(canli, "ses-arsivi", m13[:-3]), N["_hk_oku"](HY(m13))[0])["ben"]) == 10 and len(N["_hk_kanallar"](os.path.join(canli, "ses-arsivi", m13[:-3]), N["_hk_oku"](HY(m13))[0], True)["ben"]) == 12)
    # birleşmiş (uzunluğu bağdaşmayan) cevap: hizasız
    m15 = toplanti("Hakem-15", [("ben", "Dün akşam rapor hazırdı bence.", "Dün akşam rapor hazırdı bence. Sonra herkes eve gitti ve yarın görüşecekler.", 3.0, False)]); N["hakem_toplanti"](m15)
    ok("hakem metni yerelden çok uzunsa (kelime/süre uyuşmazlığı) parça hizasız", [x.get("hizasiz") for x in satirlar(HY(m15)) if x.get("dosya")] == ["uyusmaz"])
    # dışlama: kayma, uydurma, kısa, sayı yazımı
    Y = ["alfa beta gama delta epsilon", "zeta eta teta iota kapa", "lambda mü nü ksi omikron", "pi ro sigma tau üpsilon", "fi hi psi omega bir", "yüzde yirmi arttı mı ee tamam"]
    Hh = [Y[0], Y[2], Y[2], Y[3], Y[4], "%20 arttı mı tamam"]
    m14 = toplanti("Hakem-14", [("ben", y, h, 2.0, False) for y, h in zip(Y, Hh)]); pj = os.path.join(canli, "ses-arsivi", m14[:-3], "parcalar.jsonl")
    ls = [json.loads(l) for l in open(pj, encoding="utf-8")]; ls[4]["sonuc"] = "uydurma"; open(pj, "w", encoding="utf-8").write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ls))
    N["hakem_toplanti"](m14); ol = satirlar(os.path.join(canli, "hakem-olcum.jsonl"))[-1]
    ok("kayma (hakem metni komşunun yerel metni) ve uydurma işaretli parça dışlanır; sayı yazımı farkı hata değil", ol["dislanan"] == {"kayma": 1, "uydurma": 1} and ol["olculen"] == 4 and ol["wer_sozluk"] == 0.0, str(ol)[:300])
    D = ZK.dokum_dislama([{"sn": 1.0, "yerel": "evet tamam", "hakem": "evet"}, {"sn": 3.0, "yerel": "bir iki", "hakem": ""}, {"sn": 2.0, "yerel": "", "hakem": "ıı hı"},
                          {"sn": 2.0, "yerel": "a b c d e f g h", "hakem": " ".join("kelime" for _ in range(20))}, {"sn": 4.0, "yerel": "tamam herkese teşekkürler bol şans", "hakem": "tamam herkese teşekkürler bol şans"}])
    ok("dışlama nedenleri: kısa (< 2 sn), boş, boş (dolgu atılınca), hız (> 8 sözcük/sn), geçerli", D == ["kisa", "bos", "bos", "hiz", None], str(D))
    # 13) toplanti-claude.py ad alanı: hakem kanıtı okunur, ağ yok
    ok("toplanti-claude.py ogren_ad_alani hakem bölümünü de yükler", "sozluk-hakem.py" in open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read())
finally:
    sunucu.shutdown()
    import shutil; shutil.rmtree(T, ignore_errors=True)
print(f"\n{'HEPSİ GEÇTİ' if not HATA else str(len(HATA)) + ' HATA: ' + '; '.join(HATA)}")
sys.exit(1 if HATA else 0)
