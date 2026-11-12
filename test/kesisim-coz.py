#!/usr/bin/env python3
# Kesişim F2 (kesisim-coz.py): sahte model yanıtı ve sahte Tazı çağrısıyla kararların uygulanması — duzelt (Tazı dosyası + geri alınabilir olay), arastir (kuyruk + sorgu, 3 koşuda sonuçsuz),
# birak (kalıcı bastırma: kesisim.kos o id'yi bir daha üretmez), günlük tavan, kişi alanında B derece sınırı, kaynaksız/düşük güvenli düzeltme, karar/iş kaydına dokunmama, proje veritabanına yazma çağrısının
# HİÇ yapılmaması (S293), geri al, olay satırında metin olmaması, cozum şeması + kos'un cozum'u taşıması, gizli/geliştirici/ayar kapıları, geçersiz model yanıtı. Gerçek model, ağ ve port yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kesisim-coz.py     (kaldı → çıkış 1)
import datetime, importlib.util, json, os, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOD)
T0 = tempfile.mkdtemp(prefix="suflor-kcoz-ayar-"); os.environ["SUFLOR_AYAR"] = os.path.join(T0, "ayar.json"); json.dump({}, open(os.environ["SUFLOR_AYAR"], "w"))
os.environ["TAZI_VT"] = "-"; os.environ["TAZI_DIR"] = os.path.join(T0, "tazi-yok")
sp = importlib.util.spec_from_file_location("kesisim_coz", os.path.join(KOD, "kesisim-coz.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
import kesisim

hata = []
def ok(ad, c, ek=""):
    print(("ok   " if c else "KALDI ") + ad + ("" if c else f"  {ek}"))
    if not c: hata.append(ad)
SIMDI = datetime.datetime(2026, 11, 12, 8, 0, 0)
def taze():
    d = tempfile.mkdtemp(prefix="suflor-kcoz-"); return d
def bulgu(i, tur="celiski", varlik="firma:novatek.test", kanit=("B", 2), tazi="nova-teknoloji#3", belirsiz=False, vt="dis_firma/novatek.test", ozet=None):
    ks = ([{"sistem": "tazi", "kayit": tazi, "baglanti": "tazi/x"}] if tazi else []) + ([{"sistem": "vt", "kayit": vt, "baglanti": "vt#x"}] if vt else [])
    return {"id": i, "tur": tur, "varlik": varlik, "ozet": ozet or f"Bulgu {i}", "kaynaklar": ks, "kanit": {"ham": kanit[0], "duzey": kanit[1]}, "ilk_gorulme": "2026-11-11T08:00:00",
            "durum": "yeni", "onerilen_eylem": "bak", "belirsiz": belirsiz}
def sonuc(*b): return {"surum": 1, "bugun": "2026-11-12", "bulgular": list(b), "ozet": {}}
def dz(metin="Firma 2019'da kuruldu.", kaynak="https://ornek.test/kurulus", derece="B", bolum="iz"): return {"bolum": bolum, "metin": metin, "kaynak": kaynak, "derece": derece}
def model(*k):   # kararlar → model_fn
    cagri = []
    def f(istem): cagri.append(istem); return "Tamam:\n" + json.dumps({"kararlar": list(k)}, ensure_ascii=False)
    f.cagri = cagri; return f
def karar(i, k, g=0.9, hedef="tazi", duzeltme=None): return dict(id=i, karar=k, gerekce="deneme gerekçesi", guven=g, hedef=hedef, duzeltme=duzeltme or {})
class Tazi:
    def __init__(s): s.args = []; s.no = 10
    def __call__(s, a):
        s.args.append(a)
        if a[0] == "dosya" and "--metin" in a: s.no += 1; return 0, f"eklendi: #{s.no} ({a[a.index('--bolum') + 1]})"
        return 0, "kapandı" if "--kapat" in a else "ok"
    def say(s, ilk): return sum(1 for a in s.args if a[0] == ilk)
def olaylar(canli):
    try: return [json.loads(l) for l in open(os.path.join(canli, "kesisim-coz.jsonl"), encoding="utf-8")]
    except OSError: return []
def calistir(canli, s, m, tazi=None, kuyruk=None, ayar=None, oh=None, simdi=SIMDI):
    tazi = tazi if tazi is not None else Tazi()
    c = C.coz(canli, ayar or {}, s, model_fn=m, tazi_fn=tazi, kuyruk_fn=kuyruk, oh_fn=oh, simdi=simdi)
    return c, tazi

# ---------- 1) duzelt: Tazı dosyası, geri alınabilir olay, metin yok ----------
cl = taze()
m = model(karar("a1", "duzelt", duzeltme=dz()))
c, tz = calistir(cl, sonuc(bulgu("a1")), m)
ok("duzelt: tazi.py dosya çağrılır (--kim kayıt, --kaynak, --derece B, [kesişim] işareti)", tz.say("dosya") == 1 and tz.args[0][tz.args[0].index("--kim") + 1] == "nova-teknoloji" and "B" in tz.args[0] and any(x.startswith("[kesişim]") for x in tz.args[0]), tz.args)
ok("cozum şeması: tarih, duzeltilen 1, arastirilan 0, birakilan 0, cozulemeyen_onemli []", c["tarih"] == "2026-11-12" and c["duzeltilen"] == 1 and c["arastirilan"] == 0 and c["birakilan"] == 0 and c["cozulemeyen_onemli"] == [] and c["model"] == "ok", c)
j = json.load(open(os.path.join(cl, "kesisim.json")))
ok("cozum kesisim.json'a yazıldı", j.get("cozum") == c)
ol = olaylar(cl)
ok("olay satırı: zaman, id, karar, eylem, guven, geri_al; metin yok", len(ol) == 1 and ol[0]["geri_al"] == {"sistem": "tazi", "kim": "nova-teknoloji", "kapat": 11} and ol[0]["eylem"] == "tazi_dosya_eklendi"
   and set(ol[0]) == {"t", "id", "karar", "eylem", "guven", "geri_al"} and "Firma 2019" not in open(os.path.join(cl, "kesisim-coz.jsonl")).read())
ok("istem tek çağrı: bulgu id'si ve kaynaklar modele gitti", len(m.cagri) == 1 and "a1" in m.cagri[0] and "kaynaklar" in m.cagri[0])
# aynı bulgu 7 gün içinde yeniden modele gitmez
m2 = model(); c2, tz2 = calistir(cl, sonuc(bulgu("a1")), m2)
ok("düzeltilen bulgu 7 gün içinde yeniden değerlendirilmez (model çağrılmaz)", not m2.cagri and c2["aday"] == 0 and c2["model"] == "yok")
# geri al
tzg = Tazi()
ok("geri al: dosya --kapat 11 çağrılır, olay geri_alindi, sayaç düşer, bulgu yeniden aday", C.geri_al(cl, "a1", tazi_fn=tzg, simdi=SIMDI) and tzg.args[0][:5] == ["dosya", "--kim", "nova-teknoloji", "--kapat", "11"]
   and olaylar(cl)[-1]["eylem"] == "geri_alindi" and C.durum_oku(cl)["gun"]["duzeltme_n"] == 0 and C.adaylar(sonuc(bulgu("a1")), C.durum_oku(cl), SIMDI))
ok("geri al: olmayan id → False", C.geri_al(cl, "yok", tazi_fn=Tazi()) is False)

# ---------- 2) günlük tavan ----------
cl = taze()
bs = [bulgu(f"t{i}") for i in range(4)]
c, tz = calistir(cl, sonuc(*bs), model(*[karar(b["id"], "duzelt", duzeltme=dz()) for b in bs]), ayar={"kesisim_coz_tavan": 2})
ok("tavan 2: 2 düzeltme, kalanlar çözülemeyen önemli (neden tavan)", c["duzeltilen"] == 2 and tz.say("dosya") == 2 and [x["neden"] for x in c["cozulemeyen_onemli"]] == ["tavan", "tavan"], c)
c, tz = calistir(cl, sonuc(*bs), model(*[karar(b["id"], "duzelt", duzeltme=dz()) for b in bs[2:]]), ayar={"kesisim_coz_tavan": 2})
ok("tavan aynı gün sonraki çağrıda da geçerli (sayaç durumda)", c["duzeltilen"] == 0 and tz.say("dosya") == 0)
c, tz = calistir(cl, sonuc(*bs), model(*[karar(b["id"], "duzelt", duzeltme=dz()) for b in bs[2:]]), ayar={"kesisim_coz_tavan": 2}, simdi=SIMDI + datetime.timedelta(days=1))
ok("ertesi gün sayaç sıfırlanır", c["duzeltilen"] == 2)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("v1")), model(karar("v1", "duzelt", duzeltme=dz())))
ok("varsayılan tavan 5", C.TAVAN_VARSAYILAN == 5 and c["duzeltilen"] == 1)

# ---------- 3) kişi/iletişim alanında B sınırı, kaynak, güven, karar/iş kaydı ----------
cl = taze()
kisi_c = bulgu("k1", varlik="kisi:p12", kanit=("C", 1), vt="kisi/p12", ozet="X için e-posta adresi veritabanında başka kişiye kayıtlı.")
kisi_b = bulgu("k2", varlik="kisi:p13", kanit=("B", 2), vt="kisi/p13")
kisi_dc = bulgu("k3", varlik="kisi:p14", kanit=("B", 2), vt="kisi/p14")
c, tz = calistir(cl, sonuc(kisi_c, kisi_b, kisi_dc), model(karar("k1", "duzelt", duzeltme=dz(derece="A")), karar("k2", "duzelt", duzeltme=dz(derece="B")), karar("k3", "duzelt", duzeltme=dz(derece="C"))))
e = {}
for o in olaylar(cl): e.setdefault(o["id"], o["eylem"])   # her bulgunun İLK olayı (engel), sonra araştır olayı gelebilir
ok("kişi alanı: kanıt düzeyi 1 (C) → düzeltme yok, araştır'a düşer", e["k1"] == "engellendi:kisi_kanit_b_alti" and "k1" in C.durum_oku(cl)["arastir"])
ok("kişi alanı: kanıt B + düzeltme derecesi B → yazılır", e["k2"] == "tazi_dosya_eklendi" and c["duzeltilen"] == 1)
ok("kişi alanı: kanıt B ama düzeltme derecesi C → yazılmaz", e["k3"] == "engellendi:kisi_kanit_b_alti")
cl = taze()
c, tz = calistir(cl, sonuc(bulgu("n1"), bulgu("n2"), bulgu("n3")), model(karar("n1", "duzelt", duzeltme=dz(kaynak="")), karar("n2", "duzelt", g=0.5, duzeltme=dz()), karar("n3", "duzelt", duzeltme=dz())))
ok("kaynaksız düzeltme uygulanmaz; güven < 0.7 uygulanmaz (araştır'a düşer); diğeri yazılır", tz.say("dosya") == 1 and c["duzeltilen"] == 1 and c["arastirilan"] == 2, c)
cl = taze()
isb = bulgu("is1", vt="karar/42"); isb2 = bulgu("is2", vt="is/7")
c, tz = calistir(cl, sonuc(isb, isb2), model(karar("is1", "duzelt", duzeltme=dz()), karar("is2", "duzelt", duzeltme=dz())))
ok("karar ve iş kayıtlarına dokunulmaz: düzeltme yok, çözülemeyen önemli (karar_is_kaydi)", tz.say("dosya") == 0 and [x["neden"] for x in c["cozulemeyen_onemli"]] == ["karar_is_kaydi"] * 2, c)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("tk", tazi=None)), model(karar("tk", "duzelt", duzeltme=dz())))
ok("Tazı kaydı olmayan bulguda Tazı düzeltmesi yapılmaz (tazi_kaydi_yok)", tz.say("dosya") == 0 and c["cozulemeyen_onemli"][0]["neden"] == "tazi_kaydi_yok")
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("bk")), model(karar("bk", "duzelt", duzeltme=dz(metin="x" * 401))))
ok("400 karakteri aşan metin uygulanmaz", tz.say("dosya") == 0)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("bl")), model(karar("bl", "duzelt", duzeltme=dz(bolum="kimlik"))))
ok("kimlik bölümü yazılamaz (eski hükmü silerdi): bölüm 'iz'e çevrilir", tz.args[0][tz.args[0].index("--bolum") + 1] == "iz")

# ---------- 4) proje veritabanına yazma: kapalı ----------
cl = taze(); oh_cagri = []
oh = lambda b, d: oh_cagri.append(b["id"])
c, tz = calistir(cl, sonuc(bulgu("o1"), bulgu("o2")), model(karar("o1", "duzelt", hedef="oh", duzeltme=dz()), karar("o2", "duzelt", hedef="oh", duzeltme=dz())), oh=oh)
d = C.durum_oku(cl)
ok("proje veritabanı hedefli düzeltme: oh_fn ÇAĞRILMAZ, Tazı'ya da yazılmaz; oh_kapali 2, durumda oh_bekleyen", not oh_cagri and tz.say("dosya") == 0 and c["oh_kapali"] == 2 and c["duzeltilen"] == 0 and set(d["oh_bekleyen"]) == {"o1", "o2"}, c)
ok("olay: oh_yazilacakti_kapali", [o["eylem"] for o in olaylar(cl)] == ["oh_yazilacakti_kapali"] * 2)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("o3")), model(karar("o3", "duzelt", hedef="oh", duzeltme=dz())), ayar={"kesisim_coz_oh": True}, oh=None)
ok("ayar açık olsa bile oh_fn verilmedikçe yazılmaz", c["oh_kapali"] == 1)
kaynak = open(os.path.join(KOD, "kesisim-coz.py"), encoding="utf-8").read()
ok("kodda kayit.py çağrısı yok (yorum dışında; proje veritabanı öneri kuyruğuna yazma kodu eklenmedi)", not [l for l in kaynak.splitlines() if "kayit.py" in l and not l.lstrip().startswith("#")])

# ---------- 5) arastir ----------
cl = taze(); kuyruk = []
def kf(ad, alan): kuyruk.append((ad, alan)); return "basladi"
c, tz = calistir(cl, sonuc(bulgu("r1", tazi=None, varlik="firma:yeni.test")), model(karar("r1", "arastir")), kuyruk=kf)
ok("arastir: kuyruk_fn(ad, alan) çağrılır, sorgu günlüğüne yazılır (zamanli), arastirilan 1", kuyruk == [("yeni.test", "yeni.test")] and tz.say("sorgu") == 1 and "zamanli" in tz.args[-1] and c["arastirilan"] == 1 and c["cozulemeyen_onemli"] == [], (kuyruk, tz.args))
for g in (1, 2):   # ertesi koşular: yeniden değerlendirilir, 3. koşuda sonuçsuz
    c, tz = calistir(cl, sonuc(bulgu("r1", tazi=None, varlik="firma:yeni.test")), model(karar("r1", "arastir")), kuyruk=kf, simdi=SIMDI + datetime.timedelta(days=g))
ok("arastir 3 koşuda sonuçsuz kalırsa çözülemeyen önemli (arastirma_sonucsuz)", [x["neden"] for x in c["cozulemeyen_onemli"]] == ["arastirma_sonucsuz"] and C.durum_oku(cl)["arastir"]["r1"]["n"] == 3)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("r2", tazi=None, varlik="firma:yeni.test")), model(karar("r2", "arastir")), kuyruk=lambda a, b: "tavan")
ok("Tazı kuyruğu tavanda: arastirilan sayılmaz, çözülemeyen önemli", c["arastirilan"] == 0 and c["cozulemeyen_onemli"][0]["neden"] == "tazi_tavan")
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("r3", tazi=None, varlik="sistem:vt")), model(karar("r3", "arastir")), kuyruk=kf)
ok("araştırma hedefi bulunamazsa (kayıt/firma yok) çözülemeyen önemli", c["cozulemeyen_onemli"][0]["neden"] == "arastirma_hedefi_yok")
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("r4", tazi=None, varlik="firma:yeni.test")), model(karar("r4", "arastir")))
ok("kuyruk_fn yoksa (bağımsız çalışma) tazi.py aday + sorgu", tz.say("aday") == 1 and tz.say("sorgu") == 1 and c["arastirilan"] == 1)

# ---------- 6) birak: kalıcı bastırma ----------
cl = taze(); b = bulgu("b1")
c, tz = calistir(cl, sonuc(b, bulgu("b2")), model(karar("b1", "birak"), karar("b2", "birak", g=0.4)))
ok("birak: birakilan 2, durumda gerekçe, olay bastirildi", c["birakilan"] == 2 and set(C.durum_oku(cl)["birak"]) == {"b1", "b2"} and C.durum_oku(cl)["birak"]["b1"]["gerekce"] and tz.args == [])
m3 = model(); c3, _ = calistir(cl, sonuc(b), m3, simdi=SIMDI + datetime.timedelta(days=1))
ok("bırakılan bulgu bir daha modele gitmez", not m3.cagri and c3["aday"] == 0)
# kos düzeyinde: okunamayan veritabanı bulgusu (bayat/sistem) üret → bırak → bir daha üretilmez
cl = taze(); yok_vt = os.path.join(cl, "yok.db")
s1 = kesisim.kos(cl, yok_vt, os.path.join(cl, "tz"), ayar={"gelistirici": True}, simdi=SIMDI)
ids = [x["id"] for x in s1["bulgular"] if x["tur"] == "bayat" and x["varlik"] == "sistem:Proje veritabanı"]
ok("kos: okunamayan veritabanı bulgusu üretildi (deneme bulgusu)", len(ids) == 1, [x["tur"] + x["varlik"] for x in s1["bulgular"]])
d = C.durum_oku(cl); d["birak"][ids[0]] = {"t": "x", "gerekce": "g"}; C.durum_yaz(cl, d)
s2 = kesisim.kos(cl, yok_vt, os.path.join(cl, "tz"), ayar={"gelistirici": True}, simdi=SIMDI + datetime.timedelta(days=1))
ok("kos: bırakılan id bulgu listesine girmez ve 'kapandı' da yazılmaz", all(x["id"] != ids[0] for x in s2["bulgular"]) and not any(g.get("durum") == "kapandi" for g in [json.loads(l) for l in open(os.path.join(cl, "kesisim.jsonl"))]))
# kos cozum'u taşır
cl = taze(); s1 = kesisim.kos(cl, yok_vt, os.path.join(cl, "tz"), ayar={"gelistirici": True}, simdi=SIMDI)
cz = C.coz(cl, {}, s1, model_fn=model(), tazi_fn=Tazi(), simdi=SIMDI)
s2 = kesisim.kos(cl, yok_vt, os.path.join(cl, "tz"), ayar={"gelistirici": True}, simdi=SIMDI + datetime.timedelta(hours=2))
ok("kesişim koşusu yeniden yazınca cozum kaybolmaz", s2.get("cozum") == cz and json.load(open(os.path.join(cl, "kesisim.json"))).get("cozum") == cz)

# ---------- 7) model yanıtı ve adaylar ----------
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("m1"), bulgu("m2", tur="bayat", belirsiz=False), bulgu("m3", tur="eksik", varlik="firma:x.test"), bulgu("m4", belirsiz=True, tur="bayat")), lambda i: "bu JSON değil")
ok("model yanıtı çözümlenemezse: tüm önemli bulgular çözülemeyen (karar_yok), model hata, hiçbir yazma yok", c["model"] == "hata" and sorted(x["id"] for x in c["cozulemeyen_onemli"]) == ["m1", "m4"] and tz.args == [] and c["aday"] == 2, c)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("m5")), lambda i: None)
ok("model çağrısı olmadıysa (None): hata, düzeltme yok", c["model"] == "hata" and c["duzeltilen"] == 0)
ok("yanıt ayrıştırıcı: bilinmeyen karar ve eksik id atılır, güven [0,1]'e kırpılır", C.yanit_oku('{"kararlar":[{"id":"x","karar":"sil","guven":1},{"karar":"birak"},{"id":"y","karar":"birak","guven":7}]}') == {"y": {"karar": "birak", "gerekce": "", "guven": 1.0, "hedef": "tazi", "duzeltme": {}}})
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("e1", tur="yeni"), bulgu("e2", tur="rutin"), dict(bulgu("e3"), durum="kapandi")), model())
ok("önemli olmayan (yeni/rutin) ve kapanmış bulgular modele gitmez, çağrı da yapılmaz", c["aday"] == 0 and c["model"] == "yok")
cl = taze(); fazla = [bulgu(f"z{i:02d}") for i in range(45)]; m = model()
calistir(cl, sonuc(*fazla), m)
ok("en çok 30 aday, tek toplu çağrı", len(m.cagri) == 1 and m.cagri[0].count('"id": "z') == 30)
cl = taze(); c, tz = calistir(cl, sonuc(bulgu("g1"), bulgu("g2")), model(karar("g1", "birak")))
ok("modelin atladığı bulgu çözülemeyen (karar_yok)", [x["id"] for x in c["cozulemeyen_onemli"]] == ["g2"] and c["birakilan"] == 1)

# ---------- 8) kapılar: geliştirici, ayar, gizli ----------
cl = taze(); sayac = []
mm = lambda i: sayac.append(1) or "{}"
ok("geliştirici değilse çalışmaz", C.kos_ve_coz(cl, {}, gelistirici=False, model_fn=mm) == {"atlandi": "gelistirici_degil"} and not sayac)
ok("ayar kesisim_cozucu false: çalışmaz", C.kos_ve_coz(cl, {"kesisim_cozucu": False}, gelistirici=True, model_fn=mm) == {"atlandi": "kapali"} and not sayac)
ok("beta'da (geliştirici değil) ayar true olsa da çalışmaz", C.kos_ve_coz(cl, {"kesisim_cozucu": True}, gelistirici=False, model_fn=mm) == {"atlandi": "gelistirici_degil"})
ok("gizli toplantı açıkken çalışmaz ve kesisim.json yazılmaz", C.kos_ve_coz(cl, {}, gizli_fn=lambda: True, gelistirici=True, model_fn=mm) == {"atlandi": "gizli"} and not os.path.exists(os.path.join(cl, "kesisim.json")) and not sayac)
ok("acik_mi: ayar yoksa geliştiriciye bağlı", C.acik_mi({}, True) and not C.acik_mi({}, False) and C.acik_mi({"kesisim_cozucu": True}, False) and not C.acik_mi({"kesisim_cozucu": False}, True))
gizli_sira = iter([False, True])   # koşu sürerken gizli açılırsa model çağrısına gidilmez
ok("koşu sırasında gizli açılırsa model çağrılmaz", C.kos_ve_coz(cl, {}, gizli_fn=lambda: next(gizli_sira), gelistirici=True, vt=os.path.join(cl, "yok.db"), tazi_dizin=os.path.join(cl, "tz"), model_fn=mm) == {"atlandi": "gizli"} and not sayac)
c = C.kos_ve_coz(cl, {}, gelistirici=True, vt=os.path.join(cl, "yok.db"), tazi_dizin=os.path.join(cl, "tz"), model_fn=model(), tazi_fn=Tazi(), simdi=SIMDI)
ok("kos_ve_coz: tam akış cozum döner ve kesisim.json'da", c.get("tarih") == "2026-11-12" and json.load(open(os.path.join(cl, "kesisim.json")))["cozum"] == c)

# ---------- 9) relay zamanlayıcısı (kesisim_tur) ----------
src = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
ok("relay: ayar tablosunda kesisim_cozucu ve kesisim_coz_tavan; proje veritabanı ayarı tabloda yok", '"kesisim_cozucu": ("bool", False, None)' in src and '"kesisim_coz_tavan": ("sayi", 5, (0, 50))' in src and '"kesisim_coz_oh":' not in src)
i0 = src.index("def _kesisim_modul"); i1 = src.index("def _kesisim_dongu")
cl = taze(); olaylar_ = []
ns = {"os": os, "sys": sys, "json": json, "datetime": datetime, "BASE": cl, "AYAR": {"kod": KOD}, "print": lambda *a, **k: olaylar_.append(" ".join(map(str, a))), "gizli_acik": lambda: False,
      "toplanti_acik": lambda: False, "kaynak_dar": lambda: False, "gelistirici_mi": lambda: True, "__file__": os.path.join(KOD, "relay.py")}
exec(compile(src[i0:i1], "relay-kesisim", "exec"), ns)
ok("zamanlayıcı: 07:45'ten önce çalışmaz", ns["kesisim_tur"](datetime.datetime(2026, 11, 12, 7, 44)) == {"atlandi": "erken"})
ns["gizli_acik"] = lambda: True
ok("zamanlayıcı: gizli kipte bekler (gün işaretlenmez)", ns["kesisim_tur"](datetime.datetime(2026, 11, 12, 9, 0)) == {"bekliyor": "gizli"} and not os.path.exists(os.path.join(cl, "kesisim-zaman.json")))
ns["gizli_acik"] = lambda: False; ns["toplanti_acik"] = lambda: True
ok("zamanlayıcı: toplantı sürerken bekler", ns["kesisim_tur"](datetime.datetime(2026, 11, 12, 9, 0)) == {"bekliyor": "mesgul"})
ns["toplanti_acik"] = lambda: False
ns["AYAR"] = {"kod": os.path.join(cl, "yok")}; ns["__file__"] = os.path.join(cl, "relay.py")
ok("zamanlayıcı: kod klasörü yoksa atlar", ns["kesisim_tur"](datetime.datetime(2026, 11, 12, 9, 0)) == {"atlandi": "kod_yok"})
ok("relay: iş parçacığı yalnız asıl aktarıcıda, geliştiricide ve ayar kapalı değilken", 'AYAR.get("kesisim_cozucu") is not False and gelistirici_mi() and (os.environ.get("SUFLOR_KESISIM_DENEME") or not deneme_aktarici())' in src)

print(f"\n{'TAMAM' if not hata else 'KALDI: ' + str(len(hata))}")
sys.exit(1 if hata else 0)
