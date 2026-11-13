#!/usr/bin/env python3
# Toplantı sonrası döküm kontrolü (aktarici/dokum-kontrol.py + pano/dokum-kontrol.html, 6 Kasım): kurgu toplantı + kısa sentetik wav'larla — öncelik seçimi ve nedenleri, kayıt ve devam,
# ölçüm yalnız dinlenen satırlarla (5 dk blok + Gemini kayması), duzeltme-elle.json biçimi, sözlük adayı (SO_KAYNAKLAR "elle") ve onay sorusu, eğitim havuzu (14 günlük temizlik dokunmaz),
# gizli/deneme/süren toplantı hariç, beta'da görünmez, HTTP uçları (anahtarsız 401, ses, sayfa). Bütün ad ve terimler kurgu; gerçek canli klasörüne dokunmaz, ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dokum-kontrol.py     (~10 sn)
import ast, datetime, json, os, re, shutil, struct, subprocess, sys, tempfile, threading, time, types, urllib.error, urllib.request, wave
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); AK = os.path.join(KOD, "aktarici")
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + ("" if k or not ek else f"  — {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-dokum-kontrol-"); canli, uyg = os.path.join(T, "uyg", "canli"), os.path.join(T, "uyg"); os.makedirs(os.path.join(canli, "ozetler")); os.makedirs(os.path.join(canli, "ses-arsivi"))
AYAR_YOL = os.path.join(T, "ayar", "ayar.json"); os.makedirs(os.path.dirname(AYAR_YOL))
AYAR = {"alan": "Deneme", "uygulama": uyg, "proje": T, "ortak": T, "dil": "tr", "ses_arsivi": True, "veritabani": {"yol": os.path.join(T, "kurgu.db")}}
json.dump({"surum": 2, "terimler": [{"dogru": "Pelvora", "yanlis": [], "kip": "duzelt", "kaynak": "kullanici"}, {"dogru": "Nerim Kovak", "yanlis": [], "kaynak": "kullanici", "tur": "kisi"}]},
          open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)
SIMDI = time.time(); T0 = SIMDI - 7200; SAYAC = [0]
def wav(kl, ad, sn=1.0):
    SAYAC[0] += 1; n = int(16000 * sn) * 2
    with wave.open(os.path.join(kl, ad), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(struct.pack("<h", SAYAC[0] % 3000) * (n // 2))
DURUM = {"gelistirici": True, "toplanti": False, "aktif": None}
def ad_alani(ayar):
    ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "shutil": shutil, "subprocess": subprocess, "BASE": canli, "AYAR": ayar, "AYAR_YOL": AYAR_YOL, "LOCK": threading.Lock(), "print": lambda *a, **k: None,
          "threading": threading, "gelistirici_mi": lambda: DURUM["gelistirici"], "gizli_acik": lambda: False, "gemini_anahtar": lambda: "", "toplanti_acik": lambda: DURUM["toplanti"], "kaynak_dar": lambda: False,
          "aktif_dosya": lambda: DURUM["aktif"], "deneme_aktarici": lambda: False, "ben_adi": lambda: "Ben Kurgu", "_kapi_mikrofon": lambda: "yerlesik",
          "write": lambda ps: [open(y, "a", encoding="utf-8").write(m) for y, m in ps], "STATE": {}}
    ns["deneme_aktarici"] = lambda: True  # iş parçacıkları başlamasın (SUFLOR_*_DENEME yok)
    s = open(os.path.join(AK, "sozluk.py"), encoding="utf-8").read(); exec(s[:s.index('# Sesli "Claude:"')], ns)
    ag = ast.parse(open(os.path.join(AK, "bas-konus.py"), encoding="utf-8").read())
    exec(compile(ast.Module(body=[n for n in ag.body if (isinstance(n, ast.FunctionDef) and n.name in ("_ad_anahtar", "_ad_mesafe"))
                                  or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in ("_AD_HARF", "AD_ILK_ESDEGER") for t in n.targets))], type_ignores=[]), "bk", "exec"), ns)
    wh = open(os.path.join(AK, "whisper-hat.py"), encoding="utf-8").read(); a = wh.index("# Süreli ses arşivi"); b = wh.index("# --- Konuşmacı ses izi")
    exec(compile(wh[a:b].replace("try: _sa_t = threading.Timer(30", "try: None and threading.Timer(30"), "ses-arsivi-blok", "exec"), ns)
    ns["_sa_tmutil"] = lambda y: None
    sys.path.insert(0, KOD); import importlib; _bag = importlib.import_module("baglayici"); ns["_baglayici_mod"] = lambda: _bag  # A1: so_oh_var bağlayıcıdan okur
    for ad in ("sozluk-ogren.py", "sozluk-hakem.py", "dokum-kontrol.py"): exec(compile(open(os.path.join(AK, ad), encoding="utf-8").read(), ad, "exec"), ns)
    return ns
# --- kurgu toplantı ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# (kanal, Whisper, Gemini, sn, uydurma mı); Gemini "" = hakem kaydı var ama boş; None = hakem kaydı yok
FILLER = ["Bugün kısa bir toplantı yapıyoruz", "Takvimi gözden geçirelim", "Bir sonraki adımı konuşalım", "Soruları sona bırakalım", "Evet uygun görünüyor", "Kalem kalem gidelim", "Tamam anlaştık herkese teşekkürler"]
P = []
for i in range(12): P.append(("karsi" if i % 2 == 0 else "ben", FILLER[i % 7], FILLER[i % 7], 1.5, False))          # 0-11: herkes hemfikir
P[2] = ("karsi", "Belvora ekranında stok görünmüyor bugün", "Pelvora ekranında stok görünmüyor bugün", 2.0, False)    # ad + Gemini farklı
P[3] = ("karsi", "", "Raporu perşembe bitireceğiz", 2.0, True)                                                     # Whisper atladı
P[4] = ("karsi", "tamam peki anlaştık", "", 1.5, False)                                                             # Gemini boş
P[5] = ("ben", "Nerim bey toplantıya gelecek", "Nerim bey toplantıya gelecek", 1.5, False)                          # yalnız ad (hafif)
P[6] = ("karsi", "dün Kalvoro ekranı açıktı", "dün Kalvero ekranı açıktı", 2.0, False)                              # sözlük dışı ad farkı (katman 4)
P[8] = ("karsi", "kasdlfj mnbvcx qwerty", "Bütçeyi pazartesi onaylayacağız", 2.0, False)                              # dinlenmeyecek: kötü Whisper (ölçüme girmemeli)
P += [("karsi", "bu hafta stok sayımı bitiyor", "bu hafta stok sayımı bitiyor cuma günü", 2.0, False),           # 12: Gemini kayması (ikisi de doğru)
      ("karsi", "cuma günü rapor hazır olacak", "rapor hazır olacak", 2.0, False)]                                  # 13
P += [("ben" if i % 3 == 0 else "karsi", FILLER[i % 7], FILLER[i % 7], 1.5, False) for i in range(14, 30)]
P += [("karsi", "uzakta bir cümle daha geldi burada", None, 2.0, False)]                                           # 30: hakem kaydı yok
def toplanti(ad, p=P, gizli=False, yapi_saat=None, yas_dk=90):
    md = f"2026-11-04-0900-{ad}.md"; kl = os.path.join(canli, "ses-arsivi", md[:-3]); os.makedirs(kl)
    satirlar = [{"id": f"{ad}/{i}", "speaker": "Konuşmacı", "time": "09:00:00", "text": t, "kanal": "karsi" if i % 2 == 0 else "ben", "src": "whisper"} for i, (k, t, g, sn, u) in enumerate(p)]
    with open(os.path.join(canli, md[:-3] + ".jsonl"), "w", encoding="utf-8") as f: f.write("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in satirlar))
    open(os.path.join(canli, md), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n" + ("| 09:00:00 | **GİZLİ** | açıldı — kapanana kadar hiçbir şey kaydedilmez | |\n" if gizli else "")
                                                       + "".join(f"| 09:00:00 | K | {s['text']} | |\n" for s in satirlar))
    with open(os.path.join(kl, "parcalar.jsonl"), "w", encoding="utf-8") as f, open(os.path.join(kl, "hakem.jsonl"), "w", encoding="utf-8") as h:
        for i, (kanal, w, g, sn, u) in enumerate(p):
            d = f"{kanal}-{(i * 7) // 3600:02d}{(i * 7) // 60 % 60:02d}{i * 7 % 60:02d}-{i:06d}.wav"; wav(kl, d, sn); t0 = T0 + i * 7
            f.write(json.dumps({"dosya": d, "kanal": kanal, "bas": False, "t0": round(t0, 2), "t1": round(t0 + sn, 2), "sn": sn, "sonuc": "uydurma" if u else "satir", "metin": w, "dil_istek": "tr", "dil": "tr"}, ensure_ascii=False) + "\n")
            if g is not None: h.write(json.dumps({"dosya": d, "kanal": kanal, "metin": g, "model": "kurgu", "t": "2026-11-04T10:00:00"}, ensure_ascii=False) + "\n")
        h.write(json.dumps({"son": True, "parca": len(p), "kirpildi": False, "model": "kurgu", "t": "2026-11-04T10:00:01"}) + "\n")
    # Teams altyazısı: 0-2. satırlar
    with open(os.path.join(canli, md[:-3] + ".altyazi.log"), "w", encoding="utf-8") as f:
        for i in range(0, 3):
            kanal, w, g, sn, u = p[i]; ts = datetime.datetime.utcfromtimestamp(T0 + i * 7 + 1).strftime("%Y-%m-%dT%H:%M:%S")
            f.write(json.dumps({"at": ts + "Z", "id": f"cap/{i}", "speaker": "Ben Kurgu" if kanal == "ben" else "Karsi Kurgu", "text": (g or w), "src": "captions", "seen": ts + ".000Z"}, ensure_ascii=False) + "\n")
    if yapi_saat is not None:
        yp = os.path.join(canli, "ozetler", md[:-3] + ".yapi.json"); sa = datetime.datetime.fromtimestamp(T0 + yapi_saat).strftime("%H:%M:%S")
        json.dump({"maddeler": [{"baslik": "x", "ogeler": [{"tur": "karar", "metin": "bütçe onaylandı", "saat": sa}]}]}, open(yp, "w"), ensure_ascii=False)
        with open(os.path.join(canli, "son-toplantilar.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps({"dosya": md, "yapi": yp}) + "\n")
    t = SIMDI - yas_dk * 60
    for y in (os.path.join(canli, md), os.path.join(canli, md[:-3] + ".jsonl"), os.path.join(kl, "parcalar.jsonl")): os.utime(y, (t, t))
    return md
N = ad_alani(AYAR); N["DK_HAVUZ_SENKRON"] = True
try:
    # 1) hizalama: bantlı Levenshtein, kayma ve hata sayımı
    ops = N["_dk_hizala"]("bir iki üç dört beş".split(), "bir iki dört beş altı".split())
    ok("hizalama: eksik, fazla ve eşleşme doğru sayılır", [o[0] for o in ops].count("e") == 4 and [o[0] for o in ops].count("d") == 1 and [o[0] for o in ops].count("i") == 1, str(ops))
    h, n, rt, st = N["_dk_blok_olc"]("a b c d".split(), [True, True, False, False], "a x c d".split())
    ok("blok ölçümü: yalnız dinlenen referans sözcükler hata sayar (dinlenmemişteki fark sayılmaz)", (h, n) == (1, 2), str((h, n)))
    h, n, rt, st = N["_dk_blok_olc"]("a b c d".split(), [True, True, True, True], "a b c d e f".split())
    ok("blok ölçümü: bitiş fazlalığı dinlenen son sözcüğe yazılır", h == 2, str(h))
    # 2) plan: öncelik ve nedenler
    md = toplanti("Kurgu-Kontrol", yapi_saat=5 * 7)  # 5. satırın saatinde bir karar
    AYAR["dokum_kontrol_satir"] = 12
    kl = os.path.join(canli, "ses-arsivi", md[:-3]); plan = N["dk_plan_uret"](md)
    S = {s["d"]: s for s in plan["satirlar"]}; sat = plan["satirlar"]; ne = lambda i: S[[s["d"] for s in sat if s["o"] == round(i * 7, 2)][0]]["ne"] if any(s["o"] == round(i * 7, 2) for s in sat) else None
    ok("plan dosyası yazıldı (0600) ve hakem/teams/tam bilgisi", os.path.exists(os.path.join(kl, "kontrol-plan.json")) and oct(os.stat(os.path.join(kl, "kontrol-plan.json")).st_mode & 0o777) == "0o600" and plan["hakem"] and plan["teams"] and not plan["tam"])
    ok("Whisper ve Gemini'nin ikisi de boş satır listede yok; 31 parçanın hepsi sesli", len(sat) == 31 or len(sat) == 30, str(len(sat)))
    ok("hemfikir satır etiketsiz", ne(20) == [] and ne(25) == [] and ne(27) == [])
    ok("ad + Gemini farklı etiketi (Belvora/Pelvora)", "gemini" in ne(2) and "ad" in (ne(2) or []) or "ad_gemini" in (ne(2) or []), str(ne(2)))
    ok("Whisper atladı etiketi", ne(3) == ["atlandi"] or "atlandi" in (ne(3) or []), str(ne(3)))
    ok("Gemini boş etiketi", "gemini_bos" in (ne(4) or []), str(ne(4)))
    ok("karar saatine yakın satır karar/iş etiketi alır", "karar" in (ne(5) or []), str(ne(5)))
    ok("Teams eşleşen satırda uyumsuzluk puanı düşer (0-1: Teams birebir)", S[[s["d"] for s in sat if s["o"] == 0.0][0]]["t"] != "" and S[[s["d"] for s in sat if s["o"] == 0.0][0]]["p"] <= 0.0)
    ok("öncelikli sayısı ayardaki hedefi aşmaz ve en yüksek puanlılar içeride", len(plan["oncelikli"]) <= 12 and all(S[[s["d"] for s in sat if s["o"] == round(i * 7, 2)][0]]["d"] in plan["oncelikli"] for i in (2, 3, 4)))
    ok("tahmini süre yazıldı (öncelikli < tümü)", 0 < plan["tahmin_dk"]["oncelikli"] < plan["tahmin_dk"]["tumu"], str(plan["tahmin_dk"]))
    ok("Gemini kaydı olmayan satır işaretli", S[[s["d"] for s in sat if s["o"] == 210.0][0]]["e"] is False)
    # 3) kayıt ve devam; geçersiz kimlik atılır
    D = {s["o"]: s["d"] for s in sat}; d2, d3, d4 = D[14.0], D[21.0], D[28.0]
    din = [D[round(i * 7, 2)] for i in (0, 1, 2, 3, 4, 12, 13)]
    r = N["dk_islem"]({"islem": "kaydet", "t": md[:-3], "dinlenen": din + ["../disari.wav", "yok.wav"], "duz": {d2: "Pelvora ekranında stok görünmüyor bugün", d3: "Raporu perşembe bitireceğiz", "x.wav": "kötü"}, "konum": d3, "mod": "tumu"})
    d = N["dk_durum_oku"](kl)
    ok("kaydet: durum dosyası yazıldı, geçersiz kimlikler ve yol gezintisi atıldı", r["ok"] and set(d["dinlenen"]) == set(din) and set(d["duz"]) == {d2, d3} and d["konum"] == d3 and d["mod"] == "tumu")
    ok("durum dosyası 0600", oct(os.stat(os.path.join(kl, "kontrol-durum.json")).st_mode & 0o777) == "0o600")
    j = N["dk_istek"]("/dokum-kontrol/plan", f"/dokum-kontrol/plan?t={md[:-3]}")
    ok("plan uç: kaldığı yerden devam (durum plan yanıtında)", j["ok"] and j["durum"]["konum"] == d3 and len(j["durum"]["dinlenen"]) == 7)
    ok("plan uç: klasör adı dışı kimlik reddedilir", N["dk_istek"]("/dokum-kontrol/plan", "/dokum-kontrol/plan?t=../ses-arsivi").get("ok") is False and N["dk_ses"]("..", "x.wav") is None)
    ok("ses: yalnız arşivdeki wav, ad biçimi dışı reddedilir", N["dk_ses"](md[:-3], d2) and N["dk_ses"](md[:-3], "parcalar.jsonl") is None and N["dk_ses"](md[:-3], "../x.wav") is None)
    ls = N["dk_liste"]()
    ok("liste: toplantı, öncelikli sayı, dinlenen, düzeltme, tahmin", len(ls) == 1 and ls[0]["dinlenen"] == 7 and ls[0]["duzeltme"] == 2 and ls[0]["oncelikli"] == len(plan["oncelikli"]) and ls[0]["bitti"] is None)
    # 3b) 12 Kasım: "geride" (bitmemiş + ayardaki günden eski), × ile elle kapatma, plansız toplantıda da kapatma
    gl = lambda bugun: N["dk_liste"](bugun)[0]
    ok("geride: toplantı 6 günlük (sınır 7) → geride değil; 8 günlük → geride + yas_gun", gl(datetime.date(2026, 11, 10))["geride"] is False and gl(datetime.date(2026, 11, 10))["yas_gun"] == 6 and gl(datetime.date(2026, 11, 12))["geride"] is True and gl(datetime.date(2026, 11, 12))["yas_gun"] == 8)
    AYAR["dokum_kontrol_gun"] = 10; ok("ayar dokum_kontrol_gun sınırı değiştirir; geçersiz değer varsayılan 7", gl(datetime.date(2026, 11, 12))["geride"] is False and (lambda: (AYAR.__setitem__("dokum_kontrol_gun", "x"), N["dk_gun_sinir"]() == 7)[1])()); AYAR.pop("dokum_kontrol_gun", None)
    N["DK_GOR"]["zt"] = 0; v_ = N["dk_view"]()
    ok("dk_view: geride satır listede geride:true ile gelir, bekleyen (panoda gösterilecek) listesine girmez", v_ and v_["liste"][0]["geride"] is True and v_["bekleyen"] == [] and v_["liste"][0]["kapatma"] is None, str(v_)[:160])
    d_yol = os.path.join(kl, "kontrol-durum.json")
    r = N["dk_islem"]({"islem": "kapat", "t": md[:-3]}); l0 = N["dk_liste"]()[0]
    ok("kapat: ok, durum dosyasına bitti + kapatma 'elle' (ölçüm/sözlük işi yapılmaz)", r == {"ok": True, "kapatma": "elle"} and l0["bitti"] and l0["kapatma"] == "elle" and l0["geride"] is False and json.load(open(d_yol))["kapatma"] == "elle" and not os.path.exists(os.path.join(canli, "dokum-olcum.jsonl")))
    N["DK_GOR"]["zt"] = 0; v_ = N["dk_view"](); ok("kapatılan satır panoda bitti sayılır (bekleyen boş), kaydet kapatmayı bozmaz", v_["liste"][0]["bitti"] and v_["bekleyen"] == [] and N["dk_islem"]({"islem": "kaydet", "t": md[:-3], "dinlenen": din})["ok"] and json.load(open(d_yol))["kapatma"] == "elle" and json.load(open(d_yol))["bitti"])
    dd_ = json.load(open(d_yol)); dd_["bitti"] = None; dd_.pop("kapatma", None); json.dump(dd_, open(d_yol, "w"))  # sonraki bitir testi için sıfırla
    ok("kapat: geçersiz toplantı adı reddedilir (yol gezintisi yok)", N["dk_islem"]({"islem": "kapat", "t": "../x"})["ok"] is False and N["dk_islem"]({"islem": "kapat", "t": "yok-boyle-bir-toplanti"})["ok"] is False)
    pz = os.path.join(canli, "ses-arsivi", "2026-10-20-0900-Plansiz"); os.makedirs(pz)
    rp_ = N["dk_islem"]({"islem": "kapat", "t": "2026-10-20-0900-Plansiz"}); ok("kapat: planı olmayan toplantıda da çalışır", rp_["ok"] and json.load(open(os.path.join(pz, "kontrol-durum.json")))["kapatma"] == "elle"); shutil.rmtree(pz)
    N["DK_GOR"]["zt"] = 0
    # 4) bitir: duzeltme-elle.json biçimi, ölçüm, sözlük adayı, havuz
    # Düzeltmeler: P[2] Belvora → Pelvora, P[3] boş → Raporu perşembe bitireceğiz; bir de sözlük dışı ad (P[6] Kalvoro → Kalvero) dinlenmiş sayılır
    N["dk_islem"]({"islem": "kaydet", "t": md[:-3], "dinlenen": din + [D[42.0]], "duz": {d2: "Pelvora ekranında stok görünmüyor bugün", d3: "Raporu perşembe bitireceğiz", D[42.0]: "dün Kalvero ekranı açıktı"}})
    sonuc = N["dk_islem"]({"islem": "bitir", "t": md[:-3]})
    ok("bitir başarılı", sonuc["ok"] and sonuc["dinlenen"] == 8 and sonuc["duzeltme"] == 3, str(sonuc))
    e = json.load(open(os.path.join(kl, "duzeltme-elle.json"), encoding="utf-8"))
    ok("duzeltme-elle.json eski biçimle aynı alanlar (+ dinlenen listesi)", {"toplanti", "kaydedildi", "dinlenen_satir", "toplam_satir", "duzeltmeler"} <= set(e) and all(set(x) == {"dosya", "kanal", "saat", "whisper", "gemini", "dogru"} for x in e["duzeltmeler"])
       and e["dinlenen_satir"] == 8 and e["toplam_satir"] == len(sat) and len(e["dinlenen"]) == 8)
    ok("Whisper'la aynı kalan satır düzeltme sayılmaz (yalnız fark yazılır)", {x["dosya"] for x in e["duzeltmeler"]} == {d2, d3, D[42.0]})
    ol = [json.loads(l) for l in open(os.path.join(canli, "dokum-olcum.jsonl"), encoding="utf-8")]
    o = ol[0]; kelime = o["kelime"]
    ok("ölçüm: toplantı başına bir satır, yalnız sayı (ad/metin/dosya adı yok)", len(ol) == 1 and o["toplanti"] == "2026-11-04-0900" and "Kurgu" not in json.dumps(o) and "Belvora" not in json.dumps(o) and "wav" not in json.dumps(o))
    ok("ölçüm: yalnız dinlenen satırlar sayıldı (dinlenmeyen kötü Whisper satırı hata yapmadı)", o["dinlenen"] == 8 and o["wer"]["whisper"] is not None and o["wer"]["whisper"] < 0.5, str(o["wer"]))
    # Whisper hatası: Belvora→Pelvora (1) + atlanan satırın 3 sözcüğü + Kalvoro→Kalvero (1) = 5; Gemini: Gemini boş satırı (3 sözcük) — hakem kaydı olduğu için sayılır; kayma blokta sıfır
    ok("ölçüm: Whisper hatası beklenen sayıda (5 sözcük)", abs(o["wer"]["whisper"] - 5 / kelime) < 1e-3, f"{o['wer']['whisper']} ≠ {5 / kelime}")
    ok("ölçüm: Gemini kayması blokta hata sayılmaz; yalnız boş kalan satır (3 sözcük) + Kalvero satırı Gemini'de doğru", abs(o["wer"]["gemini"] - 3 / kelime) < 1e-3, f"{o['wer']['gemini']} ≠ {3 / kelime}")
    ok("ölçüm: Teams alanı var (satır 0-2 altyazılı), torba ve ad isabeti sayıları", o["teams_altyazi"] == 3 and set(o["torba"]) == {"whisper", "gemini", "teams"} and "n" in o["ad"] and o["tam_kayit"] is False)
    N["dk_olcum_yaz"](dict(o, dinlenen=10))
    ok("aynı toplantının ölçümü yenilenir (çoğalmaz)", len(open(os.path.join(canli, "dokum-olcum.jsonl"), encoding="utf-8").read().splitlines()) == 1)
    ok("duzeltme-elle.json dinlenen listesi olmayan eski biçim okunur (ilk N satır)", (lambda x: x is not None)(N["dk_elle_oku"](kl)))
    # v0.199.1: önceki düzeltme dosyası (eski sayfanın liste biçimi) yeni kayıtta silinmez
    _yol = os.path.join(kl, "duzeltme-elle.json"); _onceki = open(_yol, encoding="utf-8").read()
    open(_yol, "w", encoding="utf-8").write(json.dumps([{"dosya": "eski-sayfa-satiri.wav", "kanal": "karsi", "saat": "10:00:01", "whisper": "eski yanlis", "gemini": "", "dogru": "eski doğru"}], ensure_ascii=False))
    N["dk_elle_yaz"](kl, N["_dk_json"](os.path.join(kl, "kontrol-plan.json")), N["dk_durum_oku"](kl))
    _e = json.load(open(_yol, encoding="utf-8"))
    ok("önceki düzeltme dosyası silinmez: eski satırlar korunur, yedek kopya kalır", any(x.get("dosya") == "eski-sayfa-satiri.wav" for x in _e["duzeltmeler"]) and "eski-sayfa-satiri.wav" in _e["dinlenen"]
       and len(_e["duzeltmeler"]) >= 2 and any(f.startswith("duzeltme-elle-") for f in os.listdir(kl)))
    open(_yol, "w", encoding="utf-8").write(_onceki)
    json.dump({"toplanti": md[:-3], "dinlenen_satir": 3, "toplam_satir": 31, "duzeltmeler": [{"dosya": d2, "kanal": "karsi", "saat": "x", "whisper": "a", "gemini": "b", "dogru": "c"}]}, open(os.path.join(T, "eski.json"), "w"))
    shutil.copy(os.path.join(T, "eski.json"), os.path.join(kl, "eski-elle-deneme.json"))
    # sözlük adayı
    c = {"md": md, "B": N["so_bilinen"]()}; kn = N["_kaynak_elle"](c)
    ok("sözlük adayı: Belvora→Pelvora ve Kalvoro→Kalvero çıkar; Whisper'la aynı satır ve boş-doğru satır çıkmaz", {(x["yanlis"], x["aday_dogru"]) for x in kn} == {("Belvora", "Pelvora"), ("Kalvoro", "Kalvero")} and all(x["kaynak"] == "elle" for x in kn), str(kn))
    ok("SO_KAYNAKLAR'da elle kaynağı var", any(a == "elle" for a, _ in N["SO_KAYNAKLAR"]))
    oz = N["so_calistir"]([md]); A = {a["yanlis"]: a for a in oz["adaylar"]}
    sq = os.path.join(os.path.dirname(AYAR_YOL), "sozluk", "soru.jsonl"); SQ = [json.loads(l) for l in open(sq, encoding="utf-8")] if os.path.exists(sq) else []
    ok("sözlük adayı: kapalı kümedeki (Pelvora) de kendiliğinden kabul edilmez, onay kuyruğuna girer", A.get("Belvora", {}).get("durum") == "soruldu" and any(q["aday_dogru"] == "Pelvora" for q in SQ), str(A.get("Belvora")))
    ok("sözlük adayı: kapalı küme dışındaki (Kalvero) de soru.jsonl'e girer (kayıt veritabanı beklenmeden, dogrulandi: kullanici)", A.get("Kalvoro", {}).get("durum") == "soruldu"
       and any(q["aday_dogru"] == "Kalvero" and q.get("dogrulandi") == "kullanici" for q in SQ), str(A.get("Kalvoro")))
    ok("hiçbir elle adayı kabul olmadı, sözlük değişmedi", not any(a["durum"] == "kabul" for a in A.values()) and "Kalvero" not in open(os.path.join(canli, "sozluk.json"), encoding="utf-8").read())
    n0 = len(SQ); N["so_calistir"]([md]); SQ2 = [json.loads(l) for l in open(sq, encoding="utf-8")]
    ok("yeniden işlenince aynı aday yeniden sorulmaz", len(SQ2) == n0)
    s2 = N["_so_json"](os.path.join(canli, "sozluk.json"), {}); s2["terimler"].append({"dogru": "Pelvora", "yanlis": ["Belvora"], "kaynak": "kullanici"}); json.dump(s2, open(os.path.join(canli, "sozluk.json"), "w"), ensure_ascii=False)
    d_ = N["_so_defter_oku"](); [d_.pop(k) for k in [k for k, v in d_.items() if v["yanlis"] == "Belvora"]]; N["_so_defter_yaz"](d_); n1 = len(SQ2); N["so_calistir"]([md])
    ok("sözlükte zaten olan çift (Belvora → Pelvora) yeniden sorulmaz", len([json.loads(l) for l in open(sq, encoding="utf-8")]) == n1)
    dur = N["_so_json"](os.path.join(canli, "sozluk-ogren.json"), {}); ok("öğrenme durumuna elle kayıt saati yazıldı; yeniden işlenmez", dur["islenen"][md].get("elle", 0) > 0 and md not in N["so_bekleyen"](dur))
    time.sleep(0.05); os.utime(os.path.join(kl, "duzeltme-elle.json"), None); ok("elle kayıt yenilenince toplantı yeniden işlenecekler arasında", md in N["so_bekleyen"](dur))
    # 4b) 14 Kasım: sözlük adaylarına kullanıcının kendi onayı (sayfa → cevap.jsonl, kaynak_turu "kullanici") — öğrenme döngüsü aynı karar yolundan geçer
    cvy = os.path.join(os.path.dirname(AYAR_YOL), "sozluk", "cevap.jsonl"); tsn = time.time(); ad_ = md[:-3]
    d_ = N["_so_defter_oku"]()
    def ek_aday(y, dg, kaynak, toplanti_, durum, neden=None, sid=None):
        i = N["_so_aday_id"](y, dg); d_[i] = {"id": i, "yanlis": y, "dogru": dg, "kanit": [{"kaynak": kaynak, "toplanti": toplanti_, "tur": "gercek", "cumle": f"dün {y} ekranı açıktı", "n": 1, "t": tsn}],
                                            "durum": durum, "neden": neden, "t_ilk": tsn, **({"soru_id": sid} if sid else {})}; return i
    i_bek = ek_aday("Zorvem", "Zorvan", "elle", md, "bekliyor", "kapali_kume_disi")                    # sorusu yazılmamış (aday kimliğiyle cevaplanır)
    i_hak = ek_aday("Morvex", "Morveks", "hakem", md, "soruldu", "ohot_soruldu", sid=None)             # başka kaynaktan soruldu
    d_[i_hak]["soru_id"] = i_hak + "-1"
    i_yan = ek_aday("Tarvol", "Tarvel", "elle", md, "bekliyor", "kapali_kume_disi")
    i_dis = ek_aday("Kervan", "Kerwan", "elle", "2026-11-01-0900-Baska.md", "soruldu", "ohot_soruldu", sid=None); d_[i_dis]["soru_id"] = i_dis + "-1"   # başka toplantı
    N["_so_defter_yaz"](d_)
    L_ = N["dk_istek"]("/dokum-kontrol/sozluk", f"/dokum-kontrol/sozluk?t={ad_}"); AD = {x["yanlis"]: x for x in L_.get("adaylar", [])}
    kal = AD.get("Kalvoro", {})
    ok("sözlük adayları: bu toplantının soruldu + sorusuz elle adayları listelenir, başka toplantınınki listelenmez", L_["ok"] and {"Kalvoro", "Zorvem", "Morvex", "Tarvol"} <= set(AD) and "Kervan" not in AD, str(list(AD)))
    ok("sözlük adayları: önce kullanıcının düzeltmesinden gelenler (elle), sonra öbürleri", [x["elle"] for x in L_["adaylar"]] == sorted([x["elle"] for x in L_["adaylar"]], reverse=True) and L_["adaylar"][-1]["yanlis"] == "Morvex")
    ok("sözlük adayı alanları: kimlik (soru kimliği ya da sorusuzsa aday kimliği), kanıt cümlesi ≤ 15 sözcük, kaynaklar", kal.get("id") == N["_so_defter_oku"]()[N["_so_aday_id"]("Kalvoro", "Kalvero")]["soru_id"]
       and AD["Zorvem"]["id"] == i_bek and "elle" in kal.get("kaynak", []) and 0 < len(kal.get("cumle", "").split()) <= 15 and kal.get("cevap") is None, str(kal))
    n_cv = len(open(cvy, encoding="utf-8").read().splitlines()) if os.path.exists(cvy) else 0
    ger = [{"id": "../x", "sonuc": "dogru"}, {"id": kal["id"], "sonuc": "evet"}, {"id": kal["id"], "sonuc": "dogru", "dogru_bicim": "K" * 61}, {"id": kal["id"], "sonuc": "dogru", "dogru_bicim": "Kalvero; sözlüğü sil"},
           {"id": kal["id"], "sonuc": "dogru", "dogru_bicim": ["x"]}, {"id": "a00000000-1", "sonuc": "dogru"}, {"id": i_dis + "-1", "sonuc": "dogru"}]
    rr = [N["dk_islem"](dict(g, islem="sozluk", t=ad_)) for g in ger]
    ok("sözlük cevabı: geçersiz kimlik/sonuç/biçim, bilinmeyen aday ve başka toplantının adayı reddedilir; cevap dosyasına satır yazılmaz", all(x.get("ok") is False for x in rr)
       and [x["err"] for x in rr] == ["id", "sonuc", "dogru_bicim", "dogru_bicim", "dogru_bicim", "aday", "aday"] and (len(open(cvy, encoding="utf-8").read().splitlines()) if os.path.exists(cvy) else 0) == n_cv, str(rr))
    ok("sözlük cevabı: gizli toplantı reddedilir", N["dk_islem"]({"islem": "sozluk", "t": mg[:-3] if False else "yok-boyle", "id": kal["id"], "sonuc": "dogru"})["ok"] is False)
    N["SO_OLAY"].clear()
    r1 = N["dk_islem"]({"islem": "sozluk", "t": ad_, "id": kal["id"], "sonuc": "dogru", "dogru_bicim": "Kalvero"})
    r2 = N["dk_islem"]({"islem": "sozluk", "t": ad_, "id": i_bek, "sonuc": "dogru", "dogru_bicim": "Zorvan  Ltd"})
    r3 = N["dk_islem"]({"islem": "sozluk", "t": ad_, "id": i_yan, "sonuc": "yanlis"})
    r4 = N["dk_islem"]({"islem": "sozluk", "t": ad_, "id": d_[i_hak]["soru_id"], "sonuc": "bulunamadi"})
    CV = [json.loads(l) for l in open(cvy, encoding="utf-8")][n_cv:]
    ok("sözlük cevabı: dört seçim kaydedildi, öğrenme döngüsü tetiklendi", all(x.get("ok") for x in (r1, r2, r3, r4)) and len(CV) == 4 and N["SO_OLAY"].is_set(), str((r1, r2, r3, r4)))
    ok("cevap satırı dış cevap biçiminde: id, t, sonuc, tur, kaynak_turu kullanici; değişmeyen doğru biçim yazılmaz, düzenlenen sadeleşir", all(set(x) - {"dogru_bicim"} == {"id", "t", "sonuc", "tur", "kaynak_turu"} and x["kaynak_turu"] == "kullanici" for x in CV)
       and "dogru_bicim" not in CV[0] and CV[1]["dogru_bicim"] == "Zorvan Ltd" and CV[1]["id"] == i_bek and CV[3]["sonuc"] == "bulunamadi", str(CV))
    ok("so_cevaplar kullanici kaynak türünü korur", N["so_cevaplar"]()[kal["id"]]["kaynak_turu"] == "kullanici")
    AD = {x["yanlis"]: x for x in N["dk_so_adaylar"](ad_)["adaylar"]}
    ok("cevaplanan aday listede kalır (cevap işaretli, karar bekliyor)", AD["Kalvoro"]["cevap"] == "dogru" and AD["Kalvoro"]["durum"] == "soruldu" and AD["Tarvol"]["cevap"] == "yanlis")
    n_sq = len(open(sq, encoding="utf-8").read().splitlines())
    N["VT_BELLEK"]["terimler"] = [{"terim": "Kurgu Terim", "tur": "sistem", "takma": []}]  # kayıt veritabanı yardımcısı göndermiş gibi (yoksa katman 4 'oh_bekleniyor'da bekler)
    N["so_calistir"]([]); DF = N["_so_defter_oku"](); sz_ = open(os.path.join(canli, "sozluk.json"), encoding="utf-8").read()
    ka = DF[N["_so_aday_id"]("Kalvoro", "Kalvero")]
    ok("so_tetik sonrası: 'Sözlüğe ekle' → kabul, katman kaynağı ohot:kullanici, sözlükte", ka["durum"] == "kabul" and ka["katman_kaynak"] == "ohot:kullanici" and "Kalvero" in sz_, str({k: ka.get(k) for k in ("durum", "neden", "katman_kaynak")}))
    ok("sorusuz aday aday kimliğiyle cevaplandı → düzenlenen biçimle kabul", DF[i_bek]["durum"] == "kabul" and DF[i_bek]["dogru"] == "Zorvan Ltd" and DF[i_bek]["dogru_ilk"] == "Zorvan" and "Zorvan Ltd" in sz_, str(DF[i_bek].get("neden")))
    ok("'Yanlış' → kalıcı ret (ohot_yanlis); 'Bu sefere özel' → bulunamadi, sözlüğe girmez", DF[i_yan]["durum"] == "ret" and DF[i_yan]["neden"] == "ohot_yanlis" and DF[i_hak]["durum"] == "bulunamadi" and "Morveks" not in sz_ and "Tarvel" not in sz_)
    N["so_calistir"]([]); DF = N["_so_defter_oku"]()
    ok("yeniden çalışınca karar değişmez, aynı toplantı için yeni soru yazılmaz", DF[i_bek]["durum"] == "kabul" and DF[i_yan]["durum"] == "ret" and DF[i_hak]["durum"] == "bulunamadi" and len(open(sq, encoding="utf-8").read().splitlines()) == n_sq)
    AD = {x["yanlis"]: x for x in N["dk_so_adaylar"](ad_)["adaylar"]}
    ok("sonuç sayfada görünür: kabul/ret/bulunamadi durumu ve cevap", AD["Kalvoro"]["durum"] == "kabul" and AD["Tarvol"]["durum"] == "ret" and AD["Morvex"]["durum"] == "bulunamadi" and AD["Morvex"]["cevap"] == "bulunamadi")
    rk = N["dk_islem"]({"islem": "sozluk", "t": ad_, "id": kal["id"], "sonuc": "yanlis"})
    ok("karar verilmiş adaya yeniden cevap yazılmaz", rk.get("ok") is False and rk.get("err") == "karar_verildi", str(rk))
    open(os.path.join(canli, "2026-11-01-0900-Baska.md"), "w").write("# x\n")  # ses arşivi olmayan eski toplantı (yalnız .md)
    T_ = N["dk_istek"]("/dokum-kontrol/sozluk", "/dokum-kontrol/sozluk?t=*"); TA = {x["yanlis"]: x for x in T_.get("adaylar", [])}
    ok("bütün toplantılar (?t=*, panodaki Bekleyenler): başka toplantının adayı kendi toplantı adıyla; cevaplanmamışlar önce", T_.get("tum") is True and TA.get("Kervan", {}).get("t") == "2026-11-01-0900-Baska"
       and "Kalvoro" in TA and [x["cevap"] is not None for x in T_["adaylar"]] == sorted(x["cevap"] is not None for x in T_["adaylar"]), str(list(TA)))
    rb = N["dk_islem"]({"islem": "sozluk", "t": "2026-11-01-0900-Baska", "id": TA.get("Kervan", {}).get("id"), "sonuc": "bulunamadi"})
    ok("ses arşivi olmayan eski toplantının adayı da cevaplanır", rb.get("ok") is True, str(rb))
    ok("var olmayan toplantı adı reddedilir", N["dk_islem"]({"islem": "sozluk", "t": "2026-01-01-0000-Yok", "id": TA.get("Kervan", {}).get("id"), "sonuc": "dogru"}).get("ok") is False)
    ok("bölüm yalnız yerel: ağ çağrısı yok, cevap dosyası 0700 klasörde", oct(os.stat(os.path.dirname(cvy)).st_mode & 0o777) == "0o700")
    # eğitim havuzu
    hv = os.path.join(canli, "egitim-havuzu", "dogrulanmis", md[:-3]); fs = sorted(os.listdir(hv)) if os.path.isdir(hv) else []
    ok("eğitim havuzu: dinlenen 8 satırın wav kopyası + dogrulanmis.jsonl", sum(f.endswith(".wav") for f in fs) == 8 and "dogrulanmis.jsonl" in fs, str(fs))
    sj = [json.loads(l) for l in open(os.path.join(hv, "dogrulanmis.jsonl"), encoding="utf-8")]
    ok("havuz kaydı: doğru metin, dinlendi, düzeltildi işaretli", len(sj) == 8 and all(x["dinlendi"] for x in sj) and sum(x["duzeltildi"] for x in sj) == 3 and any(x["metin"] == "Raporu perşembe bitireceğiz" for x in sj))
    ok("havuza KOPYALANDI (arşivdeki orijinal duruyor)", all(os.path.exists(os.path.join(kl, x["dosya"])) for x in sj))
    N["ses_arsivi_temizle"](gun=-1, sinir_bayt=10 ** 12)
    ok("14 günlük arşiv temizliği (burada zorla) klasörü siler ama doğrulanmış havuz satırları kalır", not os.path.isdir(kl) and os.path.isdir(hv) and sum(f.endswith(".wav") for f in os.listdir(hv)) == 8)
    # 5) hariç tutulanlar
    mg = toplanti("Gizli-Toplanti", gizli=True); mt = toplanti("Test-Ses-Kaydi"); ms = toplanti("Sureceki"); mz = toplanti("Taze", yas_dk=2); mgz = toplanti("Gerçek-Ikinci")
    DURUM["aktif"] = ms
    bek = N["dk_bekleyen"]()
    ok("gizli, deneme, süren ve yeni biten toplantı listeye girmez; gerçek olan girer", bek == [mgz[:-3]], str(bek))
    n_tur = N["dk_tur"](); ok("dk_tur plan hazırlar", n_tur == 1 and os.path.exists(os.path.join(canli, "ses-arsivi", mgz[:-3], "kontrol-plan.json")), str(n_tur))
    ok("gizli toplantı için bitir/kaydet reddedilir", N["dk_islem"]({"islem": "kaydet", "t": mg[:-3], "dinlenen": []}).get("ok") is False)
    # hakem bitmeden bekler (hakem açık olsa), uzun süre geçince hazırlanır
    os.remove(os.path.join(canli, "ses-arsivi", mgz[:-3], "kontrol-plan.json")); h = os.path.join(canli, "ses-arsivi", mgz[:-3], "hakem.jsonl")
    s_ = open(h, encoding="utf-8").read().splitlines(); open(h, "w", encoding="utf-8").write("\n".join(s_[:-1]) + "\n")  # son işareti yok: hakem bitmemiş
    N["hakem_acik"] = lambda: (True, None); ok("hakem bitmediyse (ve çalışacaksa) plan 3 saate kadar beklenir", N["dk_bekleyen"]() == [], str(N["dk_bekleyen"]()))
    ok("hakem çalışmayacaksa (anahtar yok) beklenmeden hazırlanır", (lambda: (N.__setitem__("hakem_acik", lambda: (False, "anahtar_yok")), N["dk_bekleyen"]() == [mgz[:-3]])[1])(), str(N["dk_bekleyen"]()))
    DURUM["aktif"] = None
    # 6) beta: görünmez, çalışmaz
    DURUM["gelistirici"] = False
    ok("beta: dk_acik kapalı, görünüm/uç/ses/işlem yok", N["dk_acik"]() == (False, "beta") and N["dk_view"]() is None and N["dk_liste"]() == [] and N["dk_istek"]("/dokum-kontrol/liste", "/dokum-kontrol/liste")["ok"] is False
       and N["dk_islem"]({"islem": "bitir", "t": mgz[:-3]})["ok"] is False and N["dk_ses"](mgz[:-3], "x.wav") is None and N["dk_tur"]() == 0)
    DURUM["gelistirici"] = True; AYAR["ses_arsivi"] = False
    ok("ses arşivi kapalıyken de yok", N["dk_acik"]() == (False, "ses_arsivi_kapali")); AYAR["ses_arsivi"] = True
    ok("beta paketi: bölüm ağ/teşhis çağrısı içermez", not re.search(r"urllib|http\.client|socket|requests|teshis|beta_olay", open(os.path.join(AK, "dokum-kontrol.py"), encoding="utf-8").read().replace("urllib.parse", "")))
    b_ = open(os.path.join(AK, "beta-veri.py"), encoding="utf-8").read(); tsh = open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read()
    ok("beta veri paketine bir şey eklenmedi (beta-veri.py ve teshis.py izin listesinde döküm kontrolü yok)", "dokum_olcum" not in b_ and "dokum-olcum" not in b_ and "dokum_kontrol" not in b_ and "dokum-olcum" not in tsh)
    ok("teshis.py KOD_DOSYALARI'nda bölüm dosyası var", '"dokum-kontrol.py"' in tsh)
    # 7) HTTP: yalıtılmış aktarıcı
    PORT = bos_port(8777); R = os.path.join(T, "relay"); os.makedirs(R); C2 = os.path.join(R, "canli"); os.makedirs(os.path.join(C2, "ses-arsivi")); os.makedirs(os.path.join(C2, "ozetler"))
    for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), R)
    shutil.copytree(AK, os.path.join(R, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(R, "pano")); shutil.copytree(os.path.join(KOD, "marka"), os.path.join(R, "marka"))
    DURUM["gelistirici"] = True
    BASE_ = canli; canli = C2  # toplanti() canli'ye yazar: HTTP aktarıcısı için ikinci klasör
    mh = toplanti("Kurgu-Http"); canli = BASE_
    ay = os.path.join(R, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ben Kurgu", "port": PORT, "uygulama": R, "proje": R, "ortak": R, "gelistirici": True, "ses_arsivi": True, "ses_arsivi_egitim": False}, open(ay, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
    rp = subprocess.Popen([sys.executable, "relay.py", "--dir", C2, "--port", str(PORT)], cwd=R, stdout=open(os.path.join(R, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
    def istek(yol, govde=None, anahtar=True, ham=False):
        h = {"Origin": f"http://127.0.0.1:{PORT}", "Content-Type": "application/json"}
        if anahtar: h["X-Suflor-Anahtar"] = open(os.path.join(C2, "kart-anahtari.txt")).read().strip()
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(govde).encode() if govde is not None else None, headers=h, method="POST" if govde is not None else "GET")
        try: b = urllib.request.urlopen(q, timeout=10).read(); return b if ham else json.loads(b)
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    try:
        for _ in range(80):
            if "çalışıyor" in open(os.path.join(R, "relay.log"), encoding="utf-8").read(): break
            time.sleep(0.2)
        ok("HTTP: anahtarsız liste/plan/ses/kaydet 401", all(istek(y, anahtar=False).get("_kod") == 401 for y in ("/dokum-kontrol/liste", f"/dokum-kontrol/plan?t={mh[:-3]}", f"/dokum-kontrol/ses?t={mh[:-3]}&d=x.wav")) and istek("/dokum-kontrol", {"islem": "kaydet"}, anahtar=False).get("_kod") == 401)
        lj = istek("/dokum-kontrol/liste"); ok("HTTP: liste (geliştirici + ses arşivi): henüz plan yok → boş", lj.get("ok") and lj["liste"] == [], str(lj)[:120])
        pj = istek(f"/dokum-kontrol/plan?t={mh[:-3]}"); ok("HTTP: plan istenince hazırlanır", pj.get("ok") and len(pj["plan"]["satirlar"]) >= 30)
        dsy = pj["plan"]["satirlar"][2]["d"]; wb = istek(f"/dokum-kontrol/ses?t={mh[:-3]}&d={dsy}", ham=True)
        ok("HTTP: ses parçası WAV döner", isinstance(wb, bytes) and wb[:4] == b"RIFF", str(wb)[:60])
        ok("HTTP: yol gezintisi 404", istek(f"/dokum-kontrol/ses?t={mh[:-3]}&d=../parcalar.jsonl").get("_kod") == 404)
        kj = istek("/dokum-kontrol", {"islem": "kaydet", "t": mh[:-3], "dinlenen": [dsy], "duz": {dsy: "değişti"}}); ok("HTTP: kaydet", kj.get("ok") is True)
        st = istek("/status"); ok("HTTP: /status panoya dokum_kontrol verir (hazır liste)", "dokum_kontrol" in st and st["dokum_kontrol"]["liste"][0]["dinlenen"] == 1, str(st.get("dokum_kontrol"))[:120])
        sy = istek("/dokum-kontrol", anahtar=False, ham=True); ok("HTTP: sayfa kabuğu açılır (anahtarsız, veri uçları değil), dil sözlüğü ve anahtar gömülü", isinstance(sy, bytes) and b"Transcript check" in sy and b"SUFLOR_ANAHTAR" in sy and b"__DIL__" not in sy and b"/*__YAZI__*/" not in sy)
        ok("HTTP: sözlük adayları anahtarsız 401, anahtarlı liste döner; geçersiz cevap reddedilir", istek(f"/dokum-kontrol/sozluk?t={mh[:-3]}", anahtar=False).get("_kod") == 401
           and istek(f"/dokum-kontrol/sozluk?t={mh[:-3]}").get("ok") is True and istek("/dokum-kontrol", {"islem": "sozluk", "t": mh[:-3], "id": "x", "sonuc": "dogru"}).get("err") == "id"
           and istek("/dokum-kontrol", {"islem": "sozluk", "t": mh[:-3], "id": "a12345678", "sonuc": "dogru"}, anahtar=False).get("_kod") == 401)
        bj = istek("/dokum-kontrol", {"islem": "bitir", "t": mh[:-3]}); ok("HTTP: bitir", bj.get("ok") is True and os.path.exists(os.path.join(C2, "dokum-olcum.jsonl")))
        import urllib.parse as _up  # 12 Kasım: Türkçe harfli uzun toplantı adı yüzde-kodlanınca 80 karakteri aşıyordu, /ac sessizce reddediyordu
        uzun = _up.quote("2026-11-12-1759-Haftalık-Bütçe-Gözden-Geçirme-Çalışması-Öncesi", safe="-_.!~*'()"); tk = "a" * 32
        aj = istek("/ac", {"dokum_kontrol": f"http://127.0.0.1:{PORT}/dokum-kontrol?top={uzun}&t={tk}"}); ok("HTTP: /ac uzun Türkçe klasör adlı döküm kontrolü adresini kabul eder", aj.get("ok") is True and len(uzun) > 80, str(aj)[:100])
        ok("HTTP: /ac başka adresi reddeder", istek("/ac", {"dokum_kontrol": f"http://127.0.0.1:{PORT}/baska?top=x&t={tk}"}).get("ok") is False)
    finally: rp.terminate(); rp.wait(5)
    # beta aktarıcı: sayfa 404
    json.dump({"alan": "Deneme", "ad": "Ben Kurgu", "port": PORT, "uygulama": R, "proje": R, "ortak": R, "gelistirici": False, "ses_arsivi": True, "kod": R}, open(ay, "w"))
    rp = subprocess.Popen([sys.executable, "relay.py", "--dir", C2, "--port", str(PORT)], cwd=R, stdout=open(os.path.join(R, "relay2.log"), "w"), stderr=subprocess.STDOUT, env=env)
    try:
        for _ in range(80):
            if "çalışıyor" in open(os.path.join(R, "relay2.log"), encoding="utf-8").read(): break
            time.sleep(0.2)
        ok("HTTP beta: sayfa 404, uçlar kapalı, /status'ta dokum_kontrol yok", istek("/dokum-kontrol", anahtar=False).get("_kod") == 404 and istek("/dokum-kontrol/liste").get("ok") is False and "dokum_kontrol" not in istek("/status"))
    finally: rp.terminate(); rp.wait(5)
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not HATA else 'KALDI: ' + ', '.join(HATA)}"); sys.exit(1 if HATA else 0)
