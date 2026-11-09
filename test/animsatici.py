#!/usr/bin/env python3
# Mac Anımsatıcılar eşitlemesi (S258; aktarici/animsatici.py): kullanıcının kendi işleri seçilen listeye anımsatıcı olarak gider, iki yönlü durum eşitlenir.
# Gerçek Anımsatıcılar'a DOKUNMAZ: sahte yardımcı (JSON dosyasında anımsatıcı deposu) SUFLOR_ANIM_YARDIMCI ile verilir; Swift tarafı yalnız derleme denetimiyle (swiftc) sınanır.
#   Beklenen: ayar kapalıyken yardımcı hiç çağrılmaz · kendi işler eklenir (başlık, tarih, not işareti), başkasının/gizli/deneme işi gitmez · kararlı durumda tek çağrı ·
#   Suflor'da bitince anımsatıcı tamamlanır · Anımsatıcıda tamamlanınca Suflor'da yapildi (olay kaynağı animsatici) · yeniden açılınca iş açılır · silinen anımsatıcı işi silmez,
#   yeniden eklenmez · metin/tarih değişimi yansır · eşleme kalıcı (yeniden yükleme) · liste değişince yeni listeye · izin yoksa çökmez, her 15 sn yeniden açmaz · gizli kipte tur yok ·
#   yalıtılmış aktarıcıda bölüm yüklenir, döngü kendiliğinden ekler ve tamamlar, ayar kapalıyken dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/animsatici.py      (kaldı → çıkış 1)
import contextlib, datetime, io, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)
import yapi; from bosport import bos_port
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="suflor-anim-"); C = os.path.join(T, "canli"); os.makedirs(C)
DB = os.path.join(T, "sahte-animsaticilar.json"); SAHTE = os.path.join(T, "sahte-yardimci.py")
open(SAHTE, "w", encoding="utf-8").write('''import json, os, sys, time
a = sys.argv[1:]; db = os.environ["ANIM_SAHTE_DB"]; cikti = a[a.index("--cikti") + 1]
st = json.load(open(db)) if os.path.exists(db) else {"listeler": {}, "n": 0, "izin": True, "cagri": 0, "diger": {}}
st["cagri"] += 1
def bitir(o):
    json.dump(st, open(db, "w")); json.dump(o, open(cikti, "w"))
    sys.exit(0)
if not st["izin"]: bitir({"durum": "izin_yok", "hata": "izin verilmedi"})
if "--anim-listeler" in a: bitir({"durum": "ok", "listeler": [{"ad": k, "hesap": "iCloud", "yazilabilir": True} for k in st["listeler"]]})
q = json.load(open(a[a.index("--anim-esitle") + 1])); ad = q["liste"]
if ad not in st["listeler"]:
    if not q.get("olustur"): bitir({"durum": "liste_yok"})
    st["listeler"][ad] = {}
L = st["listeler"][ad]; simdi = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); eklenen = []
for e in q.get("ekle") or []:
    st["n"] += 1; i = "R%d" % st["n"]; L[i] = {"id": i, "baslik": e["baslik"], "tamam": False, "not": e.get("not"), "degisti": simdi}
    if e.get("vade"): L[i]["vade"] = e["vade"]
    eklenen.append({"kayit_id": e["kayit_id"], "id": i})
for e in q.get("guncelle") or []:
    r = L.get(e["id"])
    if r:
        r["baslik"] = e.get("baslik") or r["baslik"]; r["degisti"] = simdi
        if "vade" in e:
            if e["vade"]: r["vade"] = e["vade"]
            else: r.pop("vade", None)
for e in q.get("tamamla") or []:
    r = L.get(e["id"])
    if r: r["tamam"] = bool(e.get("tamam", True)); r["degisti"] = simdi
for i in q.get("sil") or []: L.pop(i, None)
bitir({"durum": "ok", "liste": ad, "ogeler": list(L.values()), "eklenen": eklenen, "hata_say": 0})
''')
os.environ.update(ANIM_SAHTE_DB=DB, SUFLOR_TEST_BASLAT="1", SUFLOR_ANIM_YARDIMCI=SAHTE, SUFLOR_ANIM_DONGU_YOK="1")
def depo(): return json.load(open(DB)) if os.path.exists(DB) else {"listeler": {}, "cagri": 0}
def depo_yaz(st): json.dump(st, open(DB, "w"))
def anim(l="Suflor.me"): return list((depo()["listeler"].get(l) or {}).values())
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
D1, DG, DN = "2026-11-03-1000-Butce", "2026-11-04-0900-Ozel", "2026-11-04-1000-Test-1"
for d, s in ((D1, "| 10:00:00 | Ayşe Deneme | merhaba | |\n"), (DG, "| 09:00:10 | **GİZLİ** | açıldı | |\n"), (DN, "| 10:00:00 | Ayşe Deneme | merhaba | |\n")):
    open(os.path.join(C, d + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {d}\n\n" + BAS + s)
def graf(top, baslik, tarih, ogeler): yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
graf(D1, "Bütçe", "2026-11-03", [{"tur": "is", "metin": "Teklifi gönder", "sahip": "Ayşe Deneme", "tarih": "2026-11-12"}, {"tur": "is", "metin": "Raporu hazırla", "sahip": "Ayşe Deneme"},
                                  {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-02"}])
graf(DG, "Özel", "2026-11-04", [{"tur": "is", "metin": "Gizli iş", "sahip": "Ayşe Deneme", "tarih": "2026-11-01"}])
graf(DN, "Test-1", "2026-11-04", [{"tur": "is", "metin": "Deneme işi", "sahip": "Ayşe Deneme"}])
# --- bölümü relay.py'nin ad alanı gibi bir ad alanında yükle (yalnız gereken adlar: AYAR, AYAR_PANO, BASE, gizli_acik, _yapi_mod) -----------------------------------------
GIZLI = [False]; AYAR = {"ad": "Ayşe Deneme", "uygulama": T, "animsatici": False, "animsatici_liste": "Suflor.me"}
ns = {"os": os, "sys": sys, "json": json, "re": re, "time": time, "datetime": datetime, "threading": threading, "AYAR": AYAR, "AYAR_PANO": {}, "BASE": C, "gizli_acik": lambda: GIZLI[0], "_yapi_mod": lambda: yapi}
exec(compile(open(os.path.join(KOD, "aktarici", "animsatici.py"), encoding="utf-8").read(), "animsatici.py", "exec"), ns)
def tur(**k):
    g = io.StringIO()
    with contextlib.redirect_stdout(g): r = ns["anim_tur"](**k)
    return r, g.getvalue()
def isler(): return {x["metin"]: x for x in yapi.kayit_listesi(C, "Ayşe Deneme")["kayitlar"] if x["tur"] == "is"}
def cagri(): return depo()["cagri"]
try:
    ok("ayarlar AYAR_PANO'ya eklendi (animsatici bool kapalı, animsatici_liste metin)", ns["AYAR_PANO"]["animsatici"] == ("bool", False, None) and ns["AYAR_PANO"]["animsatici_liste"][0] == "metin")
    r, g = tur()
    ok("ayar kapalı: tur yapılmaz, sahte yardımcı hiç çalışmaz, eşleme dosyası yok", r == {"ok": False, "neden": "kapali"} and not os.path.exists(DB) and not os.path.exists(os.path.join(C, "animsatici-es.json")))
    AYAR["animsatici"] = True
    GIZLI[0] = True; r, g = tur()
    ok("gizli kip açıkken tur yok (yardımcı çağrılmadı)", r == {"ok": False, "neden": "gizli"} and not os.path.exists(DB))
    GIZLI[0] = False
    r, g = tur(); L = anim(); by = {x["baslik"]: x for x in L}
    ok("ilk tur: yalnız kullanıcının 2 işi eklendi (başkasının, gizli ve deneme işi yok)", r["ok"] and set(by) == {"Teklifi gönder", "Raporu hazırla"} and r["ekle"] == 2)
    ok("günlük satırı ANIMSATICI: +2 ~0 ✓0", "ANIMSATICI: +2 ~0 ✓0" in g)
    ok("başlık = iş metni; son tarih bitiş tarihi, tarihsizde yok", by["Teklifi gönder"].get("vade") == "2026-11-12" and "vade" not in by["Raporu hazırla"])
    kid = isler()["Teklifi gönder"]["kayit_id"]
    ok("not: toplantı adı + tarih + Suflor kayıt kimliği işareti", by["Teklifi gönder"]["not"] == f"Bütçe · 2026-11-03\nSuflor.me · kayıt {kid}")
    es_yol = os.path.join(C, "animsatici-es.json"); es = json.load(open(es_yol))
    ok("eşleme kalıcı: kayit_id → anımsatıcı kimliği, dosya 0600", es["liste"] == "Suflor.me" and set(es["es"]) == {isler()[m]["kayit_id"] for m in ("Teklifi gönder", "Raporu hazırla")} and oct(os.stat(es_yol).st_mode & 0o777) == "0o600")
    c0 = cagri(); r, g = tur()
    ok("kararlı durumda tek yardımcı çağrısı, günlük satırı yok", cagri() == c0 + 1 and r["ok"] and r["ekle"] == r["guncelle"] == r["tamamla"] == 0 and "ANIMSATICI" not in g and len(anim()) == 2)
    ok("yeniden yükleme: eşleme diskten okunur, yinelenen anımsatıcı eklenmez", (lambda: (tur(), len(anim()) == 2)[1])())
    # Suflor'da bitir → anımsatıcı tamamlanır
    yapi.soz_kapat(C, isler()["Raporu hazırla"]["id"], "yapildi"); r, g = tur(); by = {x["baslik"]: x for x in anim()}
    ok("Suflor'da bitince anımsatıcı tamamlanır (✓1), öbürü açık", by["Raporu hazırla"]["tamam"] is True and by["Teklifi gönder"]["tamam"] is False and "ANIMSATICI: +0 ~0 ✓1" in g)
    yapi.soz_kapat(C, isler()["Raporu hazırla"]["id"], "acik"); r, g = tur(); by = {x["baslik"]: x for x in anim()}
    ok("iş Suflor'da yeniden açılınca anımsatıcı da açılır", by["Raporu hazırla"]["tamam"] is False)
    # Anımsatıcılar'da tamamla → Suflor'da bitti
    st = depo(); rid = [i for i, x in st["listeler"]["Suflor.me"].items() if x["baslik"] == "Teklifi gönder"][0]
    st["listeler"]["Suflor.me"][rid]["tamam"] = True; depo_yaz(st); r, g = tur()
    ok("Anımsatıcılar'da tamamlanan iş Suflor'da kapandı olur (✓1)", isler()["Teklifi gönder"]["durum"] == "kapandi" and "✓1" in g)
    olay = [o for o in yapi.olaylar(C, kid) if o["tur"] == "durum_degisti"][-1]
    ok("olay günlüğünde kaynak animsatici, durum yapildi (geri alınabilir kayıt)", olay["kaynak"] == "animsatici" and olay["veri"]["durum"] == "yapildi" and olay["veri"]["onceki"]["durum"] == "acik")
    c0 = cagri(); r, g = tur()
    ok("tamamlanan iş döngü yaratmaz: sonraki tur boş", cagri() == c0 + 1 and r["tamamla"] == 0 and r["suflor"] == 0)
    st = depo(); st["listeler"]["Suflor.me"][rid]["tamam"] = False; depo_yaz(st); tur()
    ok("tamamlanmış anımsatıcı yeniden açılınca iş de açılır", isler()["Teklifi gönder"]["durum"] == "acik")
    # metin / tarih Suflor'da değişir → anımsatıcıya yansır
    yapi.metin_duzelt(C, isler()["Teklifi gönder"]["id"], "Teklifi gönder (revize)"); r, g = tur(); by = {x["baslik"]: x for x in anim()}
    ok("iş metni Suflor'da değişince anımsatıcı başlığı güncellenir (~1)", "Teklifi gönder (revize)" in by and "~1" in g and len(by) == 2)
    # silinen anımsatıcı → iş silinmez, bir daha eklenmez
    st = depo(); rr = [i for i, x in st["listeler"]["Suflor.me"].items() if x["baslik"] == "Raporu hazırla"][0]; del st["listeler"]["Suflor.me"][rr]; depo_yaz(st)
    r, g = tur(); ok("silinen anımsatıcı Suflor işini silmez; eşleme düşer", "Raporu hazırla" in isler() and isler()["Raporu hazırla"]["durum"] == "acik" and isler()[ "Raporu hazırla"]["kayit_id"] not in json.load(open(es_yol))["es"] and r["dus"] == 1)
    r, g = tur(); ok("silinen iş yeniden eklenmez (yoksay)", len(anim()) == 1 and r["ekle"] == 0)
    # yeni iş kendiliğinden eklenir; başkasına atanan iş eklenmez
    graf("2026-11-05-0900-Yeni", "Yeni toplantı", "2026-11-05", [{"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe Deneme", "tarih": "2026-11-20"}, {"tur": "is", "metin": "Başkasının işi", "sahip": "Zeynep Kaya"}])
    open(os.path.join(C, "2026-11-05-0900-Yeni.md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n" + BAS + "| 09:00:00 | Ayşe Deneme | merhaba | |\n")
    r, g = tur(); ok("sonradan gelen kendi işi eklenir, başkasının işi eklenmez", {x["baslik"] for x in anim()} == {"Teklifi gönder (revize)", "Sözleşmeyi oku"} and "ANIMSATICI: +1" in g)
    # biten iş yeni eklenmez
    graf("2026-11-06-0900-Bitmis", "Eski", "2026-11-06", [{"tur": "is", "metin": "Eski iş", "sahip": "Ayşe Deneme"}])
    open(os.path.join(C, "2026-11-06-0900-Bitmis.md"), "w", encoding="utf-8").write("# Canlı transkript — x\n\n" + BAS + "| 09:00:00 | Ayşe Deneme | merhaba | |\n")
    yapi.soz_kapat(C, isler()["Eski iş"]["id"], "yapildi"); tur(); ok("daha önce eşlenmemiş biten iş anımsatıcıya eklenmez", "Eski iş" not in {x["baslik"] for x in anim()})
    # gizli toplantıya dönüşen iş: kayıt listesinde yok → anımsatıcıya dokunulmaz
    # liste değişti
    AYAR["animsatici_liste"] = "Başka Liste"; r, g = tur()
    ok("liste adı değişince yeni listeye (eski listeye dokunulmaz), eşleme yeni listeye göre", {x["baslik"] for x in anim("Başka Liste")} == {"Teklifi gönder (revize)", "Sözleşmeyi oku"} and len(anim("Suflor.me")) == 2
       and json.load(open(es_yol))["liste"] == "Başka Liste")
    AYAR["animsatici_liste"] = "Suflor.me"
    # izin yok
    st = depo(); st["izin"] = False; depo_yaz(st); ns["ANIM"]["izin_log_t"] = 0
    r, g = tur(); ok("izin yoksa çökmez; neden izin_yok, günlükte bir satır", r == {"ok": False, "neden": "izin_yok"} and "ANIMSATICI: yardımcı yanıt vermedi" in g and ns["anim_view"]()["hata"])
    st = depo(); st["izin"] = True; depo_yaz(st)
    ok("anim_view: yalnız durum ve sayı (iş metni yok)", set(ns["anim_view"]()) == {"acik", "liste", "es", "son_s", "hata"} and "Teklif" not in json.dumps(ns["anim_view"]()))
    # yardımcı çıktısı bozuksa
    os.environ["SUFLOR_ANIM_YARDIMCI"] = "/yok/yardimci.py"; r, g = tur()
    ok("yardımcı çalışmazsa çökmez (hata)", r["ok"] is False); os.environ["SUFLOR_ANIM_YARDIMCI"] = SAHTE
    # saf karar işlevi: iki taraf birden değişirse aynı yöne; anımsatıcıda bilinmeyen kimlik → düş
    pl = ns["anim_planla"]([{"kayit_id": "K1", "metin": "a", "durum": "kapandi"}], {"es": {"K1": {"id": "R1", "tamam": False, "baslik": "a", "vade": ""}}, "yoksay": []}, {"R1": {"id": "R1", "tamam": True}})
    ok("plan: Suflor kapandı + anımsatıcı tamamlandı (ikisi de değişti) → çakışma yok, iş yapılacak yok", not pl["tamamla"] and not pl["suflor"] and pl["es"]["K1"]["tamam"] is True)
    pl = ns["anim_planla"]([{"kayit_id": "K2", "metin": "b", "durum": "acik", "vade": "cuma"}], {"es": {}, "yoksay": []}, {})
    ok("plan: serbest metin tarih ('cuma') anımsatıcıya gitmez", pl["ekle"][0]["vade"] == "")
finally: pass

# --- yalıtılmış aktarıcı: bölüm relay.py'nin ad alanında yüklenir, döngü kendiliğinden çalışır ----------------------------------------------------------------------------------
R = os.path.join(T, "relay"); os.makedirs(R)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), R)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(R, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(R, "pano"))
r_metin = open(os.path.join(R, "relay.py"), encoding="utf-8").read(); bagli = 'bolum("animsatici")' in r_metin
if not bagli:  # relay.py henüz bölümü yüklemiyorsa (entegrasyon bekliyor) deneme kopyasında yüklenir
    r_metin = r_metin.replace('bolum("duygu")', 'bolum("duygu")\nbolum("animsatici")', 1); open(os.path.join(R, "relay.py"), "w", encoding="utf-8").write(r_metin)
print(("  (relay.py bolum(\"animsatici\") satırını zaten içeriyor)" if bagli else "  (relay.py bolum satırı yok: deneme kopyasına eklendi — entegrasyon satırı raporda)"))
proje = os.path.join(R, "proje"); os.makedirs(proje)
class Uc:
    def __init__(s, ad, **ayar):
        s.port = bos_port(8793); s.d = os.path.join(R, ad); os.makedirs(s.d); s.log = os.path.join(R, ad + ".log"); yol = os.path.join(R, ad + ".json")
        json.dump(dict({"alan": "Deneme", "ad": "Ayşe Deneme", "port": s.port, "uygulama": R, "proje": proje, "ortak": os.path.join(R, "yok"), "claude": "/yok/claude", "konus_on_ac": False,
                        "pocket_python": "/yok/python", "pocket_hf": "/yok"}, **ayar), open(yol, "w"))
        open(os.path.join(s.d, D1 + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {D1}\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n")
        yapi.graf_yaz(s.d, {"baslik": "Bütçe", "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "Teklifi gönder", "sahip": "Ayşe Deneme", "tarih": "2026-11-12"},
                      {"tur": "is", "metin": "Raporu hazırla", "sahip": "Ayşe Deneme"}, {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek"}]}]}, D1 + ".md")
        env = {k: v for k, v in os.environ.items() if k != "SUFLOR_ANIM_DONGU_YOK"}
        env.update(PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0", SUFLOR_ANIM_HIZLI="1", ANIM_SAHTE_DB=os.path.join(R, ad + "-depo.json"), SUFLOR_ANIM_YARDIMCI=SAHTE)
        s.depo = env["ANIM_SAHTE_DB"]
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.d, "--port", str(s.port)], cwd=R, stdout=open(s.log, "w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(80):
            if os.path.exists(os.path.join(s.d, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1)
    def liste(s):
        try: return [x for x in json.load(open(s.depo))["listeler"].get("Suflor.me", {}).values()]
        except (OSError, ValueError, KeyError): return []
    def bekle(s, f, sn=15):
        t0 = time.time()
        while time.time() - t0 < sn:
            if f(): return True
            time.sleep(0.3)
        return False
    def metin(s): return open(s.log, encoding="utf-8").read()
    def kapat(s): s.p.terminate(); s.p.wait(timeout=10)
try:
    K = Uc("kapali")
    time.sleep(8)
    ok("aktarıcı: ayar kapalıyken (varsayılan) yardımcıya hiç dokunulmaz", not os.path.exists(K.depo) and "ANIMSATICI" not in K.metin()); K.kapat()
    A = Uc("acik", animsatici=True)
    ok("aktarıcı: ayar açık → döngü kendiliğinden 2 anımsatıcı ekler", A.bekle(lambda: len(A.liste()) >= 2)); ok("günlükte ANIMSATICI: +2 ~0 ✓0", A.bekle(lambda: "ANIMSATICI: +2 ~0 ✓0" in A.metin(), 10))
    # Anımsatıcılar'da tamamla → Suflor'da bitti (döngü 5 sn içinde alır)
    st = json.load(open(A.depo)); rid = [i for i, x in st["listeler"]["Suflor.me"].items() if x["baslik"] == "Raporu hazırla"][0]
    st["listeler"]["Suflor.me"][rid]["tamam"] = True; json.dump(st, open(A.depo, "w"))
    def bitti():
        try:
            v = yapi.kayit_listesi(A.d, "Ayşe Deneme"); return any(x["metin"] == "Raporu hazırla" and x["durum"] == "kapandi" for x in v["kayitlar"])
        except Exception: return False
    ok("aktarıcı: Anımsatıcılar'da tamamlanan iş Suflor'da bitti olur", A.bekle(bitti, 20))
    ok("aktarıcı: tamamlama günlüğü ANIMSATICI: +0 ~0 ✓1", A.bekle(lambda: "ANIMSATICI: +0 ~0 ✓1" in A.metin(), 10)); A.kapat()
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nKALDI: " + ", ".join(HATA) if HATA else "\nTüm denetimler geçti.")
sys.exit(1 if HATA else 0)
