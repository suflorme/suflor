#!/usr/bin/env python3
# Sesli onay Aşama 1b (6 Kasım): "evet ama …" düzeltmesi ve sesle iş ekleme — kota harcamadan (Claude yerine SUFLOR_TEST_DUZELT sahte model cevabı), Whisper'sız.
#  1) sesli_duzeltme ayrıştırma tablosu (düzeltme / yalın evet-hayır-sonra değişmedi)
#  2) süreç içi düzenek (brifing-ses.py sesli_cevap + talimat.py): "evet ama saat 3'te olsun" → onaylanmaz, kuralla ya da (sahte) modelle düzeltilir, teyit sorulur, "evet" düzeltilmiş işi onaylar;
#     "hayır, yeni istek" de düzeltme; yalın evet/hayır eskisi gibi; model cevap vermezse eski öneri aynen bekler
#  3) iş ayrıştırma tablosu + yalıtılmış aktarıcı: sesle iş → onay (toplantıda kart / dışında sesli soru) → karar grafında iş (sahip, vade); gizli/deneme toplantıda ortak klasöre gitmez
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-onay.py
import ast, contextlib, datetime, glob, io, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8786)
T = tempfile.mkdtemp(prefix="sesli-onay-"); canli = os.path.join(T, "canli"); os.makedirs(canli); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)
bs = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); ts = open(os.path.join(KOD, "aktarici", "talimat.py"), encoding="utf-8").read()
# 1) ayrıştırma
_ad = {"SES_CEVAP", "SES_PEKISTIRME", "SES_AMA", "SES_DOLGU", "SES_DUZELT_BAS", "sesli_ayir", "sesli_duzeltme", "sesli_cevap", "EYLEM_FIIL", "SORU_YENIDEN", "SORU_UZUN", "SORU_BIRAK", "SORU",
       "kullanici_ilk_ad", "_eylem_fiil", "_soru_metni", "_yeniden_sor", "_cumle"}
def sec(kaynak, adlar): return ast.Module([n for n in ast.parse(kaynak).body if (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in adlar for x in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name in adlar)], [])
EY = []; SOYLENEN = []; KONUS = []; KARAR = []; GUN = datetime.date.today()
def _yama(x, **k): x.update(k)
def ekle(p): x = dict(p, id="e1790000000%04dab" % len(EY), at=datetime.datetime.now().isoformat(timespec="seconds"), durum="bekliyor", file=None); EY.append(x); return x
def karar(p, kaynak): x = next(x for x in EY if x["id"] == p["id"]); x["durum"] = p["durum"]; KARAR.append((p["id"], p["durum"], kaynak))
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "subprocess": subprocess, "threading": threading, "urllib": urllib, "AYAR": {"ad": "Deniz T"}, "ARAYUZ_DILI": "tr", "_t": lambda a, b: a,
      "BASE": tempfile.mkdtemp(), "LOCK": threading.RLock(), "EYLEMLER": EY, "_eylem_yama": _yama, "write": lambda x: None, "toplanti_var": lambda: False, "GERI_AL_SN": 0, "CARDS": [],
      "EYLEM_TUR": {"yapilacak": "Yapılacak", "takvim": "Takvim", "is": "İş", "oturum": "Oturuma talimat"}, "eylem_sonuc": lambda p: None, "soru_baslat": lambda ids: None,
      "seslendir": lambda m, *a, **k: SOYLENEN.append(m), "add_card": lambda c: None, "eylem_ekle": ekle, "eylem_gorunen": lambda: EY, "eylem_karar": karar,
      "_konus_kur": lambda **k: KONUS.append(k), "soru_sonraki": lambda: None, "soru_bitir": lambda n: None}
exec(compile(sec(bs, _ad), "brifing-ses", "exec"), ns)
TABLO = [("Evet ama saat üçte olsun.", True), ("Olur ama Ali'ye değil Ayşe'ye.", True), ("Tamam, konuyu şöyle yaz: bütçe onayı bekliyor.", True), ("Evet, Ali'nin raporunu da ekle lütfen.", True),
         ("Hayır, yarın cuma yap.", True), ("Hayır, Ayşe'ye gönder.", True), ("Evet ama sonra bildir.", False), ("Ama saat üçte olsun.", True), ("Evet gönder ama önce bana oku", True),
         ("Evet.", False), ("Evet, yaz.", False), ("Hayır.", False), ("Hayır, gerek yok.", False), ("Sonra.", False), ("Hayır hayır, gönderme bunu.", False), ("Evet yazma.", False), ("Evet ama.", False),
         ("Hayır, bunu şimdi değil.", False), ("Evet, evet, gönder. Kabul ediyorum, ilet.", False), ("Bunu yarın sabah ilk iş olarak yaz.", False), ("Sus.", False), ("Hepsini onayla.", False), ("", False)]
yanlis = [(m, b) for m, b in TABLO if bool(ns["sesli_duzeltme"](m)) != b]
ok(f"sesli_duzeltme tablosu {len(TABLO) - len(yanlis)}/{len(TABLO)}" + (f" — yanlış: {yanlis}" if yanlis else ""), not yanlis)
ok("yalın evet/hayır/sonra sınıfı (sesli_ayir) değişmedi", [ns["sesli_ayir"](m) for m in ("Evet.", "Hayır.", "Sonra.", "Evet ama saat üçte olsun.", "Evet, yaz.")] == ["onay", "red", "sonra", "uzun", "onay"])
# 2) süreç içi düzenek (brifing-ses.py'nin sesli bölümü + talimat.py aynı ad alanında; relay.py'deki gibi)
n2 = ns
exec(compile(ts, "talimat.py", "exec"), n2)
n2["SORU"].update(liste=[], aktif=None, t=0)
def bekle(f, sn=5):
    t0 = time.time()
    while time.time() - t0 < sn and not f(): time.sleep(0.05)
    return f()
def sor(x, metin):  # sesli cevap → hemen okunan cevap; düzeltme iş parçacığı bitene dek bekle
    n2["SORU"]["aktif"] = x["id"]; SOYLENEN.clear(); KONUS.clear()
    with contextlib.redirect_stdout(io.StringIO()): c = n2["sesli_cevap"](metin, x["id"])
    bekle(lambda: "duzeltme" not in n2["SORU"]); time.sleep(0.1); return c
def yeni(tur, baslik, ay=None, kim=None):
    x = ekle({"tur": tur, "baslik": baslik, "ayrinti": json.dumps(ay, ensure_ascii=False) if ay is not None else "", "kim": kim}); x["yerel"] = True if tur in ("yapilacak", "is", "oturum") else False; return x
Z = (datetime.datetime.now() + datetime.timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
# 2a) saatli yapılacak: yalın saat değişimi → kural (model çağrısı yok: SUFLOR_TEST_DUZELT yok)
os.environ.pop("SUFLOR_TEST_DUZELT", None)
x = yeni("yapilacak", "Ali'yi ara", {"hedef": None, "metin": "Ali'yi ara", "zaman": Z.strftime("%Y-%m-%dT%H:%M")})
c = sor(x, "Evet ama saat 3'te olsun.")
a = json.loads(x["ayrinti"])
ok(f"evet ama saat üçte → onaylanmadı, saat kuralla 15:00 (gün aynı): {a.get('zaman')}", x["durum"] == "bekliyor" and not KARAR and a["zaman"] == Z.strftime("%Y-%m-%dT") + "15:00" and c == "Düzeltiyorum.")
ok(f"teyit sorusu sesli okundu: {SOYLENEN[-1:]}", any("saat 15.00 olarak ekliyorum, tamam mı?" in m for m in SOYLENEN) and x.get("duzeltildi") is True)
ok("teyitten sonra soru hâlâ aynı işte, 'evet' düzeltilmiş işi onaylar", n2["SORU"]["aktif"] == x["id"] and (sor(x, "Evet.") or True) and x["durum"] == "onaylandi" and KARAR[-1] == (x["id"], "onaylandi", "ses"))
# 2b) yalnız gün: saat kalır
x = yeni("yapilacak", "Ali'yi ara", {"hedef": None, "metin": "Ali'yi ara", "zaman": Z.strftime("%Y-%m-%dT%H:%M")}); KARAR.clear()
sor(x, "Olur ama yarın olsun."); a = json.loads(x["ayrinti"]); y1 = (GUN + datetime.timedelta(days=1)).isoformat()
ok(f"yalnız gün söylendi → gün yarın, saat 10:00 kaldı: {a['zaman']}", a["zaman"] == y1 + "T10:00" and x["durum"] == "bekliyor")
# 2c) serbest düzeltme (kural yetmez) → model: Claude'a öneri + düzeltme gider, cevap uygulanır
sahte = os.path.join(T, "sahte-model.txt"); os.environ["SUFLOR_TEST_DUZELT"] = sahte
open(sahte, "w").write('Tamam.\n{"baslik": "Ayşe\'ye teklif gönder", "metin": "Ayşe\'ye teklifi gönder", "teyit": "Ayşe\'ye gönderiyorum, tamam mı?"}')
x = yeni("oturum", "Ali'ye teklifi gönder", {"hedef": "proje", "etiket": "proje oturumu", "metin": "Ali'ye teklifi gönder"}); KARAR.clear()
sor(x, "Olur ama Ali'ye değil Ayşe'ye."); a = json.loads(x["ayrinti"])
ok(f"model düzeltmesi: ileti metni ve başlık güncellendi, onaylanmadı: {x['baslik']!r}", x["baslik"] == "Ayşe'ye teklifi gönder" and a["metin"] == "Ayşe'ye teklifi gönder" and a["hedef"] == "proje" and x["durum"] == "bekliyor" and not KARAR)
ok("model teyit cümlesi okundu, 'tamam mı?' ile bitiyor", SOYLENEN[-1] == "Ayşe'ye gönderiyorum, tamam mı?")
# 2d) yerel olmayan tür (toplantı oturumunun uyguladığı): başlık + ayrıntı güncellenir
open(sahte, "w").write('{"baslik": "Perşembe 15.00 tekrar toplantısı", "ayrinti": "Perşembe 15.00, Ali ve Ayşe", "teyit": "Perşembe saat 15.00 olarak ekliyorum."}')
x = yeni("takvim", "Perşembe 14.00 tekrar toplantısı", None); x["ayrinti"] = "Perşembe 14.00, Ali ve Ayşe"; sor(x, "Evet ama saat üçte olsun, öğleden sonra.")
ok(f"takvim: başlık ve ayrıntı güncellendi, teyit '?' ile: {SOYLENEN[-1]!r}", x["baslik"] == "Perşembe 15.00 tekrar toplantısı" and x["ayrinti"] == "Perşembe 15.00, Ali ve Ayşe" and SOYLENEN[-1].endswith("tamam mı?") and x["durum"] == "bekliyor")
# 2e) hayır + yeni istek de düzeltme (gün söylendi → kural)
x = yeni("yapilacak", "Ali'yi ara", {"hedef": None, "metin": "Ali'yi ara", "zaman": Z.strftime("%Y-%m-%dT%H:%M")}); KARAR.clear(); sor(x, "Hayır, cuma günü yap bunu."); a = json.loads(x["ayrinti"])
ok(f"'hayır, cuma günü yap bunu' → reddedilmedi, düzeltildi (cuma, saat 10:00 kaldı): {a['zaman']}", x["durum"] == "bekliyor" and not KARAR and datetime.datetime.fromisoformat(a["zaman"]).weekday() == 4 and a["zaman"].endswith("T10:00"))
# 2f) model cevap vermezse: eski öneri aynen, iş bekliyor, yeniden soru
open(sahte, "w").write("anlamadım")
x = yeni("oturum", "Raporu ilet", {"hedef": "proje", "metin": "Raporu ilet"}); KARAR.clear(); n2["SORU"]["deneme"] = 0; sor(x, "Evet ama başlığı değiştir bence.")
ok(f"model çıktısı okunamadı: iş değişmedi, onaylanmadı, bir daha soruldu: {SOYLENEN[-1:]}", x["baslik"] == "Raporu ilet" and x["durum"] == "bekliyor" and not KARAR and "emin olayım" in SOYLENEN[-1] and not x.get("duzeltildi"))
# 2g) yalın evet / hayır / sonra eskisi gibi
for m, d in (("Evet.", "onaylandi"), ("Hayır, gerek yok.", "reddedildi")):
    x = yeni("oturum", "Raporu ilet", {"hedef": "proje", "metin": "Raporu ilet"}); KARAR.clear(); sor(x, m)
    ok(f"yalın {m!r} → doğrudan {d}, düzeltme yolu çalışmadı", x["durum"] == d and KARAR[-1][2] == "ses" and not x.get("duzeltildi"))
# 2h) düzeltme hazırlanırken gelen "evet" eski öneriyi onaylamaz
x = yeni("oturum", "Raporu ilet", {"hedef": "proje", "metin": "Raporu ilet"}); KARAR.clear(); n2["SORU"].update(aktif=x["id"], duzeltme=x["id"]); SOYLENEN.clear()
with contextlib.redirect_stdout(io.StringIO()): n2["sesli_cevap"]("Evet.", x["id"])
ok("düzeltme sürerken 'evet' → onay yok, 'bir saniye'", x["durum"] == "bekliyor" and not KARAR and "Bir saniye" in SOYLENEN[-1]); n2["SORU"].pop("duzeltme", None)
# 2i) ayar kapatır
n2["AYAR"]["sesli_duzeltme"] = False; n2["SORU"]["deneme"] = 0; x = yeni("oturum", "Raporu ilet", {"hedef": "proje", "metin": "Raporu ilet"}); KARAR.clear(); sor(x, "Evet ama saat üçte olsun.")
ok("ayar sesli_duzeltme: false → eski davranış (uzun cevap: yeniden sorar, onaylamaz)", x["durum"] == "bekliyor" and not KARAR and "emin olayım" in SOYLENEN[-1]); n2["AYAR"].pop("sesli_duzeltme")
# 3) iş ayrıştırma
nt = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "AYAR": {"ad": "Deniz T"}, "_t": lambda a, b: a, "kisilik_hitap_bul": lambda m: (None, re.sub(r"^Atlas,\s*", "", m)), "toplanti_var": lambda: False}
exec(ts[ts.index("TALIMAT_FIIL ="):ts.index("def _talimat_kayit")] + ts[ts.index("_SC_AY = ("):ts.index("_GOREV = {")] + ts[ts.index("IS_ATA_RX ="):ts.index("def _is_kaydet")], nt)
for g, b in [("Bana bir iş ekle: Cuma'ya kadar teklif hazırla.", ("is", "Cuma'ya kadar teklif hazırla")), ("Atlas, yeni iş aç: tedarikçi sözleşmesini gözden geçir", ("is", "tedarikçi sözleşmesini gözden geçir")),
             ("Ali'ye iş ata: bütçe tablosunu güncelle.", ("is", "bütçe tablosunu güncelle")), ("Ayşe'ye bir iş ver, müşteri sunumunu hazırlasın.", ("is", "müşteri sunumunu hazırlasın")),
             ("Yapılacaklarıma ekle: vergi beyannamesini kontrol et", ("yapilacak", "vergi beyannamesini kontrol et")), ("Bu iş çok zor.", None), ("İş ekle", None), ("Proje oturumuna ilet: iş ekle bunu", ("oturum", "bunu"))]:
    c = nt["talimat_coz"](g); c = (c[0], c[2]) if c else None
    if g.startswith("Proje oturumuna"): c = (c[0], None) if c else None; b = (b[0], None)
    ok(f"iş ayrıştırma: {g!r} → {c}", c == b)
for g, kim, tarih in [("Bana bir iş ekle: Cuma'ya kadar teklif hazırla.", "Deniz T", "cuma"), ("Ali'ye iş ata: bütçe tablosunu güncelle.", "Ali", None), ("Ayşe'ye bir iş ver, yarın müşteri sunumunu hazırlasın.", "Ayşe", "yarın"),
                      ("Denize iş ata: faturayı kontrol et", "Deniz", None), ("Yeni iş aç: tedarikçiyi ara 12 Kasım'a kadar", "Deniz T", "12")]:
    e = nt["_is_ek"](g); t_ = e["tarih"]
    sonra = {"cuma": lambda t: t and datetime.date.fromisoformat(t).weekday() == 4, "yarın": lambda t: t == (datetime.date.today() + datetime.timedelta(days=1)).isoformat(), "12": lambda t: t and t.endswith("-11-12"), None: lambda t: t is None}[tarih]
    ok(f"iş sahibi/vade: {g!r} → {e['kim']}, {t_}", e["kim"] == kim and sonra(t_))
# 4) yalıtılmış aktarıcı: toplantıda sesle iş → onay kartı → karar grafı; toplantı dışında sesli soru → panodan onay; 
EP = "ben" + chr(64) + "ornek.test"
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "eposta_kimlik": EP, "ortak_gecmis": True}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py", "toplanti-claude.py", "baglayici.py", "yapi.py", "ortak_bulut.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log"); env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_METIN="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
L = lambda: open(log, encoding="utf-8", errors="replace").read()
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None, pano=False):
        h = {"X-Suflor-Anahtar": K, **({"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers=h), timeout=15).read())
    isler = lambda: (lambda c: c.execute("SELECT id, sahip, metin, son_tarih, toplanti, tur FROM kayit WHERE tur IN ('is','soz')").fetchall())(sqlite3.connect(os.path.join(canli, "karar-grafi.sqlite"))) if os.path.exists(os.path.join(canli, "karar-grafi.sqlite")) else []
    n = [0]
    def satir(kanal, metin, kim="Deniz T"):
        n[0] += 1; uc("/ingest", {"meeting": {"title": "Sesli onay deneme"}, "source": "whisper", "entries": [{"id": f"t/{n[0]}", "speaker": kim, "time": time.strftime("%H:%M:%S"), "text": metin, "kanal": kanal}]})
    NABIZ = threading.Event()
    def nabiz():
        while not NABIZ.is_set(): uc("/ping", {"meeting": {"title": "Sesli onay deneme"}, "call": True, "panel": True}); time.sleep(2)
    threading.Thread(target=nabiz, daemon=True).start(); time.sleep(0.5)
    satir("ben", "Claude: Ali'ye iş ata: Cuma'ya kadar tedarikçi teklifini hazırla."); time.sleep(1)
    kart = next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and "tedarikçi teklifini" in c.get("text", "") and c.get("status") == "acik"), None)
    ok(f"toplantıda sesle iş → onay kartı (sesle okunmaz): {(kart or {}).get('text')!r}", bool(kart) and "iş kaydı" in kart["text"] and "SES (deneme)" not in L())
    ey = next((x for x in (uc("/cards").get("eylem") or {}).get("liste") or [] if x["tur"] == "is"), None)
    ok("eylem kuyruğunda yerel 'is' işi (sahip Ali, vade ayrıntıda), toplantı oturumu görmez", bool(ey) and ey["kim"] == "Ali" and ey["yerel"] and "Ali" in (ey["ayrinti"] or "") and ey["durum"] == "bekliyor"
       and "tedarikçi teklifini" not in subprocess.run([sys.executable, "-B", os.path.join(T, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "eylem", "liste"], capture_output=True, text=True, env=env, timeout=30).stdout)
    ok("onaylanmadan karar grafına yazılmadı", not isler())
    TOP = json.load(open(os.path.join(canli, "toplanti.json")))["aktif"]["dosya"]  # bu toplantı deneme sayılsın (son-toplantilar.jsonl: deneme: true) — işi ortak klasöre gitmemeli
    open(os.path.join(canli, "son-toplantilar.jsonl"), "w").write(json.dumps({"dosya": TOP, "deneme": True}) + "\n")
    uc("/card-ack", {"id": kart["id"], "status": "onaylandi"}, pano=True); time.sleep(1.5)
    ls = isler()
    ok(f"onayla → iş karar grafında: {[(i[1], i[2][:30], i[3], bool(i[4])) for i in ls]}", len(ls) == 1 and ls[0][1] == "Ali" and "tedarikçi teklifini" in ls[0][2] and ls[0][3] and datetime.date.fromisoformat(ls[0][3]).weekday() == 4)
    ok("iş açık toplantı dosyasına bağlandı", bool(ls) and ls[0][4] == TOP)
    satir("ben", "Claude: bana iş ekle: ben toplantıda kendime iş yazıyorum."); time.sleep(1)
    k2 = next((c for c in uc("/cards").get("cards") or [] if c.get("onay") and "kendime iş" in c.get("text", "") and c.get("status") == "acik"), None); uc("/card-ack", {"id": k2["id"], "status": "reddedildi"}, pano=True); time.sleep(1)
    ok("reddedilen iş yazılmadı", len(isler()) == 1)
    NABIZ.set(); t0 = time.time()
    while time.time() - t0 < 40 and (json.load(open(os.path.join(canli, "toplanti.json"))).get("aktif") or {}).get("durum") == "suruyor": time.sleep(0.5)  # toplantı biter (SUFLOR_TEST_HIZLI: 6 sn nabızsız)
    time.sleep(1)
    # toplantı dışında: Konuş'a söylenen → sesli soru → panodan onay → iş (toplantıya bağlı değil)
    uc("/bas-konus", {"metin": "Bana bir iş ekle: yarın bütçe sunumunu kontrol et."}, pano=True); time.sleep(1.2)
    x = next((x for x in (uc("/cards").get("eylem") or {}).get("liste") or [] if x["tur"] == "is" and "bütçe sunumunu" in x["baslik"]), None)
    ok(f"toplantı dışında: sesli 'İş olarak kaydedeyim mi?' sorusu, Claude'a gitmedi", bool(x) and "bütçe sunumunu kontrol et. İş olarak kaydedeyim mi?" in L() and "açık süreç açıldı" not in L())
    uc("/eylem-karar", {"id": x["id"], "durum": "onaylandi"}, pano=True); time.sleep(1.0)
    t0 = time.time()
    while time.time() - t0 < 20 and len(isler()) < 2: time.sleep(0.5)  # sesli karar değil (pano): Geri al beklenmez
    ls = isler(); yeni_ = [i for i in ls if "bütçe sunumunu" in i[2]]
    ok(f"onay → iş kaydedildi: sahip kendisi, vade yarın, toplantıya bağlı değil", len(yeni_) == 1 and yeni_[0][1] == "Deniz T" and yeni_[0][3] == (GUN + datetime.timedelta(days=1)).isoformat() and not yeni_[0][4])
    ok("aktarıcıda hata yok", "Traceback" not in L())
finally:
    r.terminate(); r.wait(5)
    if HATA or sys.exc_info()[0]: print("günlük:", log)
    else: shutil.rmtree(T, ignore_errors=True)
print("sesli-onay:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun: {HATA}"); sys.exit(1 if HATA else 0)
