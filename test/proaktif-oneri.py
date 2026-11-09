#!/usr/bin/env python3
# Gün içi proaktif asistan önerisi + toplu onay / belge önerisi KAYIT komutları (9 Kasım; aktarici/toplanti-sonrasi.py pro_gun_*, aktarici/notlar.py kayit_*):
#   1) Birim: pro_aday_kur (öncelik, cuma tarihi, cümleler), pro_baglam / pro_bekliyor (asistana bağlam, en çok 2 tur, TTL), KAYIT_SONUC doğruluğu.
#   2) Birim: notlar.py kayit_dogrula / kayit_uygula — karar_toplu_onayla (en çok 10, tek tek karar_onayla kuralı, gevşek uygulama), belge_oneri_kabul / belge_oneri_reddet.
#   3) Yalıtılmış aktarıcı: tarama kuralları (kapalı, günlük sınır, aralık, gizli, toplantı, mesai, kullanıcı meşgul, tekrar önleme), durum alanı, menü bildirimi, Bakalım, kapat.
# Kurgu veri (gerçek kişi yok); gerçek claude çağrılmaz; canlı aktarıcıya dokunulmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/proaktif-oneri.py      (kaldı → çıkış 1)
import datetime, json, os, re, secrets, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
T = tempfile.mkdtemp(prefix="proaktif-"); HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
BUGUN = datetime.date.today(); ISO = lambda g: (BUGUN + datetime.timedelta(days=g)).isoformat()
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def graf(dizin, top, ogeler, rol="yurutucu"):
    open(os.path.join(dizin, top + ".md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n" + BAS + "| 09:30:00 | Ayşe Deneme | merhaba | |\n")
    os.makedirs(os.path.join(dizin, "gundemler"), exist_ok=True); json.dump({"title": top, "rol": rol}, open(os.path.join(dizin, "gundemler", top + ".json"), "w", encoding="utf-8"))
    yapi.graf_yaz(dizin, {"baslik": top, "tarih": ISO(-5), "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
TOP = ISO(-5) + "-0930-Planlama"
OGELER = [{"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Ayşe Deneme", "tarih": ISO(-3)}, {"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe Deneme", "tarih": ISO(-1)},
          {"tur": "is", "metin": "Raporu gönder", "sahip": "Ayşe Deneme", "tarih": ISO(0)},
          {"tur": "karar", "metin": "Lansman ocakta", "netlik": "ortuk"}, {"tur": "karar", "metin": "Fiyat sabit kalır", "netlik": "ortuk"}, {"tur": "karar", "metin": "Bütçe onaylandı", "netlik": "ortuk"}]

# ---------- 1) birim: aday kurma ve asistan bağlamı ----------
def ns_kur(dosyalar, **ek):
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "secrets": secrets, "AYAR": {}, "BASE": T, "print": lambda *a, **k: None,
          "_t": lambda tr, en: tr, "gizli_acik": lambda: False, "bildirim": lambda *a, **k: None}
    ns.update(ek)
    for f in dosyalar: exec(compile(open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read(), f, "exec"), ns)
    return ns
P = ns_kur(["toplanti-sonrasi.py"])
cuma = P["_pro_cuma"]
ok("cuma: pazartesi → o hafta cuması, cuma → gelecek hafta, hafta sonu → gelecek cuma", [cuma(datetime.date(2026, 11, 9)).isoformat(), cuma(datetime.date(2026, 11, 13)).isoformat(), cuma(datetime.date(2026, 11, 14)).isoformat()] == ["2026-11-13", "2026-11-20", "2026-11-20"])
veri = {"kendi": [{"id": "s1", "metin": "Tabloyu güncelle", "kalan_gun": -3, "gecikti": True}, {"id": "s2", "metin": "Sözleşmeyi oku", "kalan_gun": -1, "gecikti": True},
                  {"id": "s3", "metin": "Raporu gönder", "kalan_gun": 0, "gecikti": False}], "teyit": [{"id": "k1", "metin": "Lansman ocakta"}, {"id": "k2", "metin": "Fiyat sabit kalır"}]}
bel = [{"id": "o" + "a" * 15, "metin": "Tedarikçiyle görüş", "sahip": "Can Örnek"}]
ad = P["pro_aday_kur"](veri, bel, datetime.date(2026, 11, 9))
ok("sıra: gecikmiş > teyit > bugün vadeli > belge", [a["tur"] for a in ad] == ["gecikmis", "teyit", "bugun", "belge"])
ok("gecikmiş: en eski iş cumaya, cümle 'N iş gecikti … alayım mı?'", ad[0]["komut"] == "is_ertele" and ad[0]["arg"]["id"] == "s1" and ad[0]["arg"]["vade"] == "2026-11-13" and ad[0]["cumle"].startswith("2 iş gecikti") and "cumaya (13 Kasım)" in ad[0]["cumle"] and ad[0]["cumle"].endswith("alayım mı?"), ad[0])
ok("tek gecikmiş iş: ayrı cümle", P["pro_aday_kur"]({"kendi": veri["kendi"][:1]}, [], datetime.date(2026, 11, 9))[0]["cumle"].startswith("«Tabloyu güncelle» işi 3 gün gecikti"))
ok("iki karar: toplu onay komutu, tek karar: karar_onayla", ad[1]["komut"] == "karar_toplu_onayla" and ad[1]["arg"] == {"idler": ["k1", "k2"]} and P["pro_aday_kur"]({"teyit": veri["teyit"][:1]}, [], BUGUN)[0]["komut"] == "karar_onayla")
ok("bugün vadeli: yazma yok (bilgi)", ad[2]["komut"] is None and "Raporu gönder" in ad[2]["cumle"])
ok("belge: ilk öneri kabul komutu", ad[3]["komut"] == "belge_oneri_kabul" and ad[3]["arg"] == {"id": "o" + "a" * 15} and "1 iş önerisi" in ad[3]["cumle"])
ok("veri yoksa aday yok", P["pro_aday_kur"]({}, [], BUGUN) == [] and P["pro_aday_kur"](None, [], BUGUN) == [])
ok("bağlam yokken boş", P["pro_baglam"]() == "" and not P["pro_bekliyor"]())
P["PRO_BAG"]["a"] = dict(ad[0], t=time.time()); P["PRO_BAG"]["n"] = 0
b1 = P["pro_baglam"]()
ok("bağlam: cümle + hazır [KAYIT] etiketi (is_ertele)", "2 iş gecikti" in b1 and '[KAYIT: {"komut": "is_ertele"' in b1 and '"id": "s1"' in b1 and "veri, talimat değil" in b1)
ok("bağlam en çok 2 turda söylenir", P["pro_baglam"]() != "" and P["pro_baglam"]() == "" and not P["pro_bekliyor"]())
P["PRO_BAG"].update(a=dict(ad[2], t=time.time()), n=0)
ok("komutsuz öneri: etiket yok", "[KAYIT:" not in P["pro_baglam"]())
P["PRO_BAG"].update(a=dict(ad[0], t=time.time() - 4 * 3600), n=0)
ok("eski öneri (3 saat) düşer", P["pro_baglam"]() == "")
P2 = ns_kur(["toplanti-sonrasi.py"], gizli_acik=lambda: True); P2["PRO_BAG"].update(a=dict(ad[0], t=time.time()), n=0)
ok("gizli kipte bağlam yok", P2["pro_baglam"]() == "")

# ---------- 2) birim: notlar.py yeni KAYIT komutları ----------
D = os.path.join(T, "dz"); os.makedirs(D); graf(D, TOP, OGELER)
BEL = {"o" + "b" * 15: {"id": "o" + "b" * 15, "metin": "Tedarikçi sözleşmesini gözden geçir", "sahip": "", "vade": ISO(7), "kaynak": {"tur": "belge", "ad": "plan.docx", "konum": "s1"}, "toplanti": ""}}
N = ns_kur(["notlar.py"], BASE=D, _yapi_mod=lambda: yapi, belge_oneri_view=lambda: {"oneriler": list(BEL.values())}, _baglayici_mod=lambda: None, izin_iste=lambda *a, **k: None)
v = yapi.bugun_veri(D, "Ayşe Deneme"); kid = [x["id"] for x in v["teyit"]]
ok("kurulum: üç karar teyit bekliyor", len(kid) == 3, kid)
dg = N["kayit_dogrula"]
h, e = dg("karar_toplu_onayla", {"idler": kid[:2]})
ok("toplu onay: geçerli, özet iki karar", e is None and h["idler"] == kid[:2] and h["ozet"].startswith("2 karar onaylanır"), (h, e))
ok("toplu onay: tekrar eden kimlik tek sayılır", dg("karar_toplu_onayla", {"idler": [kid[0], kid[0]]})[0]["idler"] == [kid[0]])
ok("toplu onay: 11 kimlik reddedilir (en çok 10)", dg("karar_toplu_onayla", {"idler": [f"k{i}" for i in range(1, 12)]})[1] is not None)
ok("toplu onay: liste değil / boş / iş kimliği / karışık tür reddedilir", all(dg("karar_toplu_onayla", {"idler": z})[1] for z in ("k1", [], ["s1"], ["k1", 3], [kid[0], "x9"])))
ok("toplu onay: fazladan argüman reddedilir", dg("karar_toplu_onayla", {"idler": kid[:1], "x": "y"})[1] is not None)
ok("toplu onay: olmayan karar reddedilir (sıkı)", dg("karar_toplu_onayla", {"idler": [kid[0], "k999"]})[1] is not None)
ok("toplu onay: gevşek kipte olmayan atlanır", dg("karar_toplu_onayla", {"idler": [kid[0], "k999"]}, gevsek=True)[0]["atlanan"] == ["k999"])
ok("diğer komutlar metin olmayan argümanı yine reddeder", dg("karar_onayla", {"id": ["k1"]})[1] is not None)
sonuc, ne = N["kayit_uygula"]({"komut": "karar_toplu_onayla", "arg": {"idler": kid[:2]}})
ok("toplu onay uygulanır: iki karar onaylandı, üçüncü hâlâ bekler", sonuc and ne.startswith("2/2") and [x["id"] for x in yapi.bugun_veri(D, "Ayşe Deneme")["teyit"]] == kid[2:], (sonuc, ne))
ok("onaylanmışlar için yeniden toplu öneri reddedilir", dg("karar_toplu_onayla", {"idler": kid[:2]})[1] is not None)
h2, e2 = dg("karar_toplu_onayla", {"idler": kid})  # strict reddeder (ikisi onaylı) ama uygulama aradan onaylananları atlar
ok("sıkı doğrulama: aradan onaylananlar varsa reddeder", e2 is not None)
sonuc, ne = N["kayit_uygula"]({"komut": "karar_toplu_onayla", "arg": {"idler": kid}})
ok("uygulama gevşek: kalan tek karar onaylanır (1/1)", sonuc and ne.startswith("1/1") and not yapi.bugun_veri(D, "Ayşe Deneme")["teyit"], (sonuc, ne))
ok("hiç onay bekleyen kalmayınca uygulama hata verir", N["kayit_uygula"]({"komut": "karar_toplu_onayla", "arg": {"idler": kid}})[0] is False)
oid = "o" + "b" * 15
h, e = dg("belge_oneri_kabul", {"id": oid})
ok("belge kabul: geçerli, özet vade içerir", e is None and "kayda alınır" in h["ozet"] and ISO(7) in h["ozet"], (h, e))
ok("belge: kimlik biçimi / olmayan öneri reddedilir", dg("belge_oneri_kabul", {"id": "x1"})[1] and dg("belge_oneri_kabul", {"id": "o" + "c" * 15})[1] and dg("belge_oneri_reddet", {"id": "o" + "c" * 15})[1])
sonuc, ne = N["kayit_uygula"]({"komut": "belge_oneri_kabul", "arg": {"id": oid}})
kayit = [x for x in yapi.kayit_listesi(D, "Ayşe Deneme")["kayitlar"] if "Tedarikçi sözleşmesini" in x["metin"]]
ok("belge kabul uygulanır: iş kayda girdi, vade ve belge kaynağı", sonuc and len(kayit) == 1 and kayit[0]["vade"] == ISO(7), (sonuc, ne, kayit))
BEL.clear(); BEL["o" + "d" * 15] = {"id": "o" + "d" * 15, "metin": "Raporu yeniden yaz", "sahip": "", "vade": "", "kaynak": {"tur": "belge", "ad": "r.docx", "konum": ""}, "toplanti": ""}
sonuc, ne = N["kayit_uygula"]({"komut": "belge_oneri_reddet", "arg": {"id": "o" + "d" * 15}})
ok("belge reddet uygulanır: ret kaydı yapi'da", sonuc and "o" + "d" * 15 in (yapi._bo_dosya(D).get("red") or {}), (sonuc, ne))
ok("KAYIT_SONUC bekleyen öneri yokken boş, sonuç eklenince doğru", not N["KAYIT_SONUC"] and (N["KAYIT_SONUC"].append("x") or bool(N["KAYIT_SONUC"])))
N["KAYIT_SONUC"].clear(); N["pro_bekliyor"] = lambda: True; N["pro_baglam"] = lambda: "[ÖNERİ]\n"
ok("bekleyen öneri varken pro_bekliyor doğru (bas-konus koşulu açık), KAYIT_SONUC düz liste ve not öneriyi taşır", type(N["KAYIT_SONUC"]) is list and not N["KAYIT_SONUC"] and N["pro_bekliyor"]() and N["kayit_sonuc_notu"]() == "[ÖNERİ]\n")
N["KAYIT_SONUC"].append("✓ Yazıldı: x")
ok("sonuç ve öneri birlikte", "Yazıldı" in N["kayit_sonuc_notu"]() and not list(N["KAYIT_SONUC"]))
kural = N["kayit_kural"]()
ok("asistan kuralında üç yeni komut", all(s in kural for s in ("belge_oneri_kabul", "belge_oneri_reddet", "karar_toplu_onayla")))
N["gizli_acik"] = lambda: True
ok("gizli kipte yeni komutlar reddedilir", N["kayit_dogrula"]("karar_toplu_onayla", {"idler": kid})[1] is not None and N["kayit_dogrula"]("belge_oneri_kabul", {"id": oid})[1] is not None)

# ---------- 3) yalıtılmış aktarıcı ----------
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
proje = os.path.join(T, "proje"); os.makedirs(proje)
HER_GUN = {"gunler": [0, 1, 2, 3, 4, 5, 6], "bas": "00:00", "bit": "23:59"}
class Uc:
    def __init__(s, ad, tohum=True, **ayar):
        s.port = bos_port(8794); s.d = os.path.join(T, ad); os.makedirs(s.d); s.log = os.path.join(T, ad + ".log")
        if tohum: graf(s.d, TOP, OGELER)
        yol = os.path.join(T, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Ayşe Deneme", "port": s.port, "uygulama": T, "proje": proje, "ortak": os.path.join(T, "yok"), "claude": "/yok/claude", "konus_on_ac": False,
                        "pocket_python": "/yok/python", "pocket_hf": "/yok", "calisma_saatleri": HER_GUN, "proaktif_aralik_dk": 0, "proaktif_bosta_dk": 0}, **ayar), open(yol, "w"))
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=T, stdout=open(s.log, "w"), stderr=subprocess.STDOUT,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"))
        for _ in range(80):
            if os.path.exists(os.path.join(s.d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); s.h = {"X-Suflor-Anahtar": open(os.path.join(s.d, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{s.port}"}
    def post(s, yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=30).read())
    def status(s): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}/status", headers=s.h), timeout=10).read())
    def metin(s): return open(s.log, encoding="utf-8").read()
    def tara(s): return s.post("/proaktif", {"islem": "tara", "zorla": True}).get("sonuc")
    def kapat_oneri(s):
        pr = s.status().get("proaktif"); s.post("/proaktif", {"islem": "kapat", "id": (pr or {}).get("id")}); return pr
    def kapat(s): s.p.terminate(); s.p.wait(timeout=10)
try:
    A = Uc("a", proaktif_gunluk_en_cok=10)
    ok("açılışta hata yok (yeni ayarlar elle ayar dosyasından okunur)", "Traceback" not in A.metin())
    ok("öneri yokken durum alanı boş", A.status().get("proaktif") is None)
    s1 = A.tara(); pr = A.status().get("proaktif") or {}
    ok("1. tarama: gecikmiş iş önerisi sunuldu, durumda tür gun ve yazma", s1 == "gonderildi" and pr.get("tur") == "gun" and pr.get("yazma") is True and "iş gecikti" in pr.get("cumle", "") and pr["cumle"].endswith("alayım mı?"), (s1, pr))
    ok("menü bildirimi gitti, günlükte cümle yok", "BİLDİRİM (deneme): Öneri" in A.metin() and "Tabloyu güncelle" not in A.metin().split("PROAKTİF: gün içi öneri")[1].split("\n")[0])
    ok("panoda bekleyen öneri varken yenisi gelmez", A.tara() == "panoda bekleyen öneri var")
    A.kapat_oneri(); s2 = A.tara(); pr = A.status().get("proaktif") or {}
    ok("2. öneri: aynı öneri tekrarlanmadan sıradaki (3 karar teyit)", s2 == "gonderildi" and "3 karar" in pr.get("cumle", ""), (s2, pr))
    A.kapat_oneri(); s3 = A.tara(); pr = A.status().get("proaktif") or {}
    ok("3. öneri: bugün vadeli (yazmasız)", s3 == "gonderildi" and pr.get("yazma") is False and "Raporu gönder" in pr.get("cumle", ""), (s3, pr))
    A.kapat_oneri()
    ok("4. tarama: aynı öneriler 24 saat tekrarlanmaz → öneri yok", A.tara() == "öneri yok")
    ok("boş bakıştan sonra 20 dk bekler (zorla olmadan)", A.post("/proaktif", {"islem": "tara"}).get("sonuc") == "yakın zamanda bakıldı")
    ok("durum dosyası: sayaç ve anahtarlar kalıcı", len(json.load(open(os.path.join(A.d, "proaktif.json"))).get("oneri", {})) == 3 and json.load(open(os.path.join(A.d, "proaktif.json")))["gun"]["n"] == 3)
    # Bakalım: yazmalı öneri asistana gider
    AB2 = Uc("a2"); AB2.tara(); pr = AB2.status().get("proaktif")
    r = AB2.post("/proaktif", {"islem": "sor", "id": pr["id"]})
    ok("Bakalım: gün içi öneri asistana yazılı gider, şerit kalkar", r.get("ok") is True and AB2.status().get("proaktif") is None and "gün içi öneri — evet" in AB2.metin(), r)
    AB2.kapat()
    # günlük sınır ve aralık
    B = Uc("b", proaktif_gunluk_en_cok=1)
    ok("günlük sınır 1: ilk öneri gider", B.tara() == "gonderildi"); B.kapat_oneri()
    ok("günlük sınır dolunca yok", B.tara() == "günlük sınır"); B.kapat()
    C = Uc("c", proaktif_aralik_dk=90)
    ok("aralık 90 dk: ilk gider", C.tara() == "gonderildi"); C.kapat_oneri()
    ok("aralık dolmadan ikinci gelmez", C.tara() == "aralık dolmadı"); C.kapat()
    # kapalı ayarlar
    K1 = Uc("k1", proaktif_oneri=False); K2 = Uc("k2", proaktif_gunluk_en_cok=0)
    ok("proaktif_oneri false → kapalı", K1.tara() == "kapalı" and K1.status().get("proaktif") is None)
    ok("proaktif_gunluk_en_cok 0 → kapalı", K2.tara() == "kapalı"); K1.kapat(); K2.kapat()
    # mesai, meşgul, gizli, toplantı
    M = Uc("m", calisma_saatleri={"gunler": [], "bas": "09:00", "bit": "18:00"})
    ok("mesai dışında (çalışma günü yok) öneri yok", M.tara() == "mesai dışı"); M.kapat()
    E = Uc("e", proaktif_bosta_dk=60)
    E.post("/proaktif", {"islem": "gordu"})
    ok("kullanıcı az önce Kararlar ve işler'e baktı → meşgul", E.tara() == "kullanıcı meşgul")
    E.post("/komut", {"tur": "gizli"})
    ok("gizli kipte öneri yok", E.tara() == "gizli kip"); E.post("/komut", {"tur": "gizli"}); E.kapat()
    G = Uc("g")
    G.post("/ping", {"meeting": {"title": "Yeni toplantı"}, "panel": True, "rows": 1})
    G.post("/ingest", {"meeting": {"title": "Yeni toplantı"}, "source": "transcript", "entries": [{"id": "a/1", "speaker": "Ayşe Örnek", "time": "02:10", "text": "merhaba"}]})
    ok("toplantı sürerken öneri yok", G.tara() == "toplantı sürüyor" and G.status().get("proaktif") is None); G.kapat()
    # sesli ayar
    S = Uc("s", toplanti_sonrasi_sesli=True); S.tara(); time.sleep(2)
    ok("sesli ayar açıkken öneri cümlesi seslendirilir", "karakter · " in S.metin() and "iş gecikti" in S.metin(), S.metin()[-400:]); S.kapat()
    # tohum yok: öneri yok
    Z = Uc("z", tohum=False)
    ok("kayıt yokken öneri yok, durum boş", Z.tara() == "öneri yok" and Z.status().get("proaktif") is None); Z.kapat()
finally:
    for n in ("A", "AB2", "B", "C", "K1", "K2", "M", "E", "G", "S", "Z"):
        try: globals()[n].p.kill()
        except Exception: pass
print("\nTÜM TESTLER GEÇTİ" if not HATA else f"\n{len(HATA)} test kaldı: {HATA}"); shutil.rmtree(T, ignore_errors=True); sys.exit(1 if HATA else 0)
