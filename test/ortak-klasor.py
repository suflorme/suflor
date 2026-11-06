#!/usr/bin/env python3
# Ortak klasör — ortak karar katmanı A3 (Drive pilotu; yapi.ortak_*, aktarici/ortak-klasor.py, /ortak). İki yalıtılmış aktarıcı (ayrı canli + ayar, boş portlar) ve ortak bir geçici
# "Drive" klasörü: A'da karar/iş → B'de görünür; B'de durum değişikliği → A'da; çift olay 0 (yeniden okumada da); yarım ve bozuk satır dayanıklılığı; gizli ve deneme toplantısından
# olay 0 (yazma anında denetim + denetim betiği); ayar açılmadan önceki kayıt gitmez; ayar kapalıyken hiçbir şey yazılmaz; başka Mac'ten atanan iş "Sana atandı" (Bugün, Kararlar ve işler);
# yetkisiz değişiklik iki yanda da uygulanmaz. Kurgu veri; ağ yok, gerçek claude yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ortak-klasor.py      (kaldı → çıkış 1; ~15 sn)
AT = "@"  # e-posta biçimi kaynakta geçmesin (açık depo taraması)
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)  # kod önce: test/yapi.py adı çakışır
import yapi; from bosport import bos_port
hata = []
def bak(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-ortak-"); DRIVE = os.path.join(T, "Drive", "Ortak Suflor")  # boşluklu yol (Drive klasör adları gibi)
os.makedirs(DRIVE)
EA, EB, EC = "ayse" + AT + "ornek.test", "bora" + AT + "ornek.test", "can" + AT + "ornek.test"
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
M_NORMAL, M_GIZLI, M_DENEME, M_ESKI = "2026-11-05-1400-Haftalik-Plan", "2026-11-05-1500-Butce-Ozel-Gorusme", "2026-11-05-1600-Deneme-Toplantisi", "2026-11-04-1000-Eski-Toplanti"
class Mac:
    def __init__(s, ad, kisi, ep, port, ortak):
        s.ad = ad; s.kok = os.path.join(T, ad); s.canli = os.path.join(s.kok, "canli"); os.makedirs(s.canli); s.port = port
        for f in ("relay.py", "manifest.json", "yapi.py", "ortak_bulut.py"): shutil.copy(os.path.join(KOD, f), s.kok)
        for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(s.kok, d))
        s.ayar = os.path.join(s.kok, "ayar.json"); a = {"alan": "Deneme", "ad": kisi, "port": port, "uygulama": s.kok, "proje": s.kok, "ortak": s.kok, "eposta_kimlik": ep}
        if ortak: a["ortak_klasor"] = DRIVE
        json.dump(a, open(s.ayar, "w"))
    def baslat(s):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=s.ayar, SUFLOR_TEST_BASLAT="1")
        s.p = subprocess.Popen([sys.executable, "relay.py", "--dir", s.canli, "--port", str(s.port)], cwd=s.kok, stdout=open(os.path.join(s.kok, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(100):
            if "çalışıyor" in s.log(): return
            time.sleep(0.1)
    def log(s):
        try: return open(os.path.join(s.kok, "relay.log"), encoding="utf-8").read()
        except OSError: return ""
    def istek(s, yol, govde=None):
        k = open(os.path.join(s.canli, "kart-anahtari.txt")).read().strip()
        q = urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(govde).encode() if govde is not None else None, method="POST" if govde is not None else "GET",
                                   headers={"X-Suflor-Anahtar": k, "Origin": f"http://127.0.0.1:{s.port}", "Content-Type": "application/json"})
        try: return json.loads(urllib.request.urlopen(q, timeout=20).read())
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    def esitle(s): return s.istek("/ortak", {"islem": "esitle"})
    def yaz(s, top, baslik, ogeler, gizli=False):  # toplantı sonu (toplanti-claude.py yapi → graf_yaz) yerine doğrudan; yazan bu Mac'in kullanıcısı
        open(os.path.join(s.canli, top + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {top}\n\n" + BAS + ("| 14:00:01 | **GİZLİ** | açıldı | |\n" if gizli else "| 14:00:01 | X | merhaba | |\n"))
        os.environ["SUFLOR_AYAR"] = s.ayar; yapi.graf_yaz(s.canli, {"baslik": baslik, "tarih": top[:10], "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    def kayit(s, metin, deneme=False): return next((x for x in s.istek("/kayitlar" + ("?deneme=1" if deneme else ""))["kayitlar"] if x["metin"] == metin), None)
    def olay_say(s):
        c = sqlite3.connect(os.path.join(s.canli, "karar-grafi.sqlite"))
        try: return c.execute("SELECT COUNT(*), COUNT(DISTINCT olay_id) FROM olay").fetchone()
        finally: c.close()
def drive_metin():
    out = ""
    for k, _, fs in os.walk(DRIVE):
        for f in fs: out += open(os.path.join(k, f), encoding="utf-8", errors="replace").read()
    return out
PA = bos_port(8781); PB = bos_port(PA + 1)
A = Mac("a", "Ayşe Deneme", EA, PA, True); B = Mac("b", "Bora Kaya", EB, PB, False)
try:
    B.yaz(M_ESKI, "Eski toplantı", [{"tur": "is", "metin": "Ayar öncesi eski iş", "sahip": "Bora Kaya", "tarih": "2026-11-20"}])  # ayar açılmadan önceki kayıt: gitmemeli
    A.baslat(); B.baslat()
    bak("iki aktarıcı açıldı", "çalışıyor" in A.log() and "çalışıyor" in B.log(), (A.log()[-400:], B.log()[-400:]))
    v = B.esitle()
    bak("ayar kapalıyken: durum kapalı, Drive'a hiçbir şey yazılmaz", v.get("durum") == "kapali" and v.get("acik") is False and not os.listdir(DRIVE), v)
    v = A.esitle()
    bak("A: açık, kimlik şirket e-postası, durum ok", v.get("acik") and v.get("durum") == "ok" and v.get("kimlik") == EA, v)
    r = B.istek("/ayar", {"degisen": {"ortak_klasor": DRIVE}})
    bak("⚙ Ayarlar'dan ortak_klasor yazılır (boşluklu yol aynen)", r.get("ok") is True and json.load(open(B.ayar)).get("ortak_klasor") == DRIVE, r)
    bak("B: ayar açılınca ilk tur ok; ayar öncesi kayıt gitmez", B.esitle().get("durum") == "ok" and "Ayar öncesi eski iş" not in drive_metin())
    # --- A'da toplantı: karar + işler; gizli ve deneme toplantıları; iddia
    A.yaz(M_NORMAL, "Haftalık Plan", [{"tur": "karar", "metin": "Bütçe 120 bin olarak kalıyor", "kim": "Ayşe Deneme", "saat": "14:02:00", "alinti": "yuz yirmide kalalim dedik", "netlik": "acik"},
                                     {"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-12", "saat": "14:05:00"},
                                     {"tur": "is", "metin": "Tedarikçiyi ara", "sahip": "Can Örnek", "tarih": "2026-11-13"},
                                     {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Deneme"}])
    A.yaz(M_GIZLI, "Bütçe özel görüşme", [{"tur": "karar", "metin": "GIZLIKARAR maaş artışı yüzde on", "kim": "Ayşe Deneme", "netlik": "acik"},
                                          {"tur": "is", "metin": "GIZLIIS kadro planı", "sahip": "Bora Kaya", "sahip_eposta": EB}], gizli=True)
    A.yaz(M_DENEME, "Deneme toplantısı", [{"tur": "karar", "metin": "DENEMEKARAR deneme kararı", "kim": "Ayşe Deneme", "netlik": "acik"}])
    v = A.esitle(); d = drive_metin()
    dosyalar = [os.path.relpath(os.path.join(k, f), DRIVE) for k, _, fs in os.walk(DRIVE) for f in fs]
    bak("A'nın dosyası tek yazarlı düzende: olaylar/<e-posta>/<cihaz>/<YYYY-AA>.jsonl", len(dosyalar) == 1 and dosyalar[0].startswith(os.path.join("olaylar", EA, "c-")) and dosyalar[0].endswith(".jsonl"), dosyalar)
    bak("karar ve iki iş yazıldı (3 kayit_olustu)", d.count('"tur": "kayit_olustu"') == 3 and "Teklifi revize et" in d and "Bütçe 120 bin" in d, v)
    bak("gizli toplantının kaydı ve başlığı yazılmadı", "GIZLIKARAR" not in d and "GIZLIIS" not in d and "Bütçe özel görüşme" not in d and M_GIZLI not in d)
    bak("deneme toplantısının kaydı yazılmadı", "DENEMEKARAR" not in d and M_DENEME not in d)
    bak("alıntı, iddia, döküm gitmez", "yuz yirmide" not in d and "Geçen yıl 95 bin" not in d and "merhaba" not in d)
    bak("atlananlar sayılır (gizli 2, deneme 1)", (v.get("son_tur") or {}).get("atlanan", {}).get("gizli") == 2 and v["son_tur"]["atlanan"].get("deneme") == 1, v.get("son_tur"))
    bak("denetim betiği: A'nın ortak klasöründe gizli/deneme izi 0", v.get("denetim") == 0, v.get("denetim"))
    bak("rol 'ben' dışarıda e-postaya çevrilir, yazan e-posta", '"ben": true' not in d and all(json.loads(l)["yazan"] == EA for l in d.splitlines()))
    # --- B okur
    v = B.esitle()
    bak("B: 3 olay alındı, çift 0, bozuk 0", (v.get("alinan"), v["son_tur"]["cift"], v["son_tur"]["bozuk"]) == (3, 0, 0), v)
    bak("B: kişiler listesinde A", v.get("kisiler") == [EA], v.get("kisiler"))
    kt, kk = B.kayit("Teklifi revize et"), B.kayit("Bütçe 120 bin olarak kalıyor")
    bak("B'nin Kararlar ve işler'inde A'nın kararı ve işi", bool(kt and kk and B.kayit("Tedarikçiyi ara")), (kt, kk))
    bak("Kararlar ve işler: 'Sana atandı' (atayan A) ve kendi işi", kt and kt.get("atayan") == "Ayşe Deneme" and kt.get("kendi") is True, kt)
    bak("başkasına (C) atanan işte 'Sana atandı' yok", "atayan" not in (B.kayit("Tedarikçiyi ara") or {"atayan": 1}))
    bg = B.istek("/bugun-veri"); bk = [x for x in bg.get("kendi", []) if x["metin"] == "Teklifi revize et"]
    bak("Bugün'de senden beklenenlerde, 'Sana atandı · Ayşe Deneme' (yeni atama: vadesinden bağımsız görünür)", len(bk) == 1 and bk[0].get("atayan") == "Ayşe Deneme" and bk[0]["vade"] == "2026-11-12" and bk[0].get("atama_yeni") is True, bg.get("kendi"))
    bak("B'de gizli ve deneme kaydı yok (deneme süzgeci açıkken de)", not any(x["metin"].startswith(("GIZLI", "DENEME")) for x in B.istek("/kayitlar?deneme=1")["kayitlar"]))
    # --- B'de durum değişikliği → A
    r = B.istek("/is-durum", {"id": kt["id"], "durum": "yapildi"})
    bak("B işi 'yapıldı' yaptı (sahip: yetkili)", r.get("ok") is True and B.kayit("Teklifi revize et")["durum"] == "kapandi", r)
    B.esitle(); v = A.esitle()
    bak("A: B'nin değişikliği alındı → iş kapandı", v.get("alinan") == 1 and A.kayit("Teklifi revize et")["durum"] == "kapandi", (v.get("alinan"), A.kayit("Teklifi revize et")))
    th = yapi.tarihce(A.canli, A.kayit("Teklifi revize et")["kayit_id"])
    bak("A'nın tarihçesinde B'nin olayı (kaynak ortak, yazan B)", any(o["yazan"] == EB and o["kaynak"].startswith("ortak:") and o["tur"] == "durum_degisti" for o in th), [(o["yazan"], o["kaynak"], o["tur"]) for o in th])
    # --- yetki: B karar metnini değiştirmeye kalkar (isteyen değil) → iki yanda da uygulanmaz
    os.environ["SUFLOR_AYAR"] = B.ayar; o, _ = yapi.metin_duzelt(B.canli, kk["kayit_id"], "Bütçe 200 bin olsun")
    bak("B'de yetkisiz değişiklik yerelde de uygulanmaz", o is not None and o["uygulandi"] is False and B.kayit("Bütçe 120 bin olarak kalıyor") is not None)
    B.esitle(); v = A.esitle()
    bak("A: yetkisiz olay günlükte, uygulanmadı; 'uygulanmayan değişiklik' listede", A.kayit("Bütçe 120 bin olarak kalıyor") is not None and len(v.get("reddedilen") or []) == 1 and v["reddedilen"][0]["yazan"] == EB, v.get("reddedilen"))
    # --- çift olay 0: tekrar turları ve okuma konumu sıfırlanınca
    sa, sb = A.olay_say(), B.olay_say()
    for _ in range(2): A.esitle(); B.esitle()
    bak("tekrar turlarında yeni olay yok; olay_id'ler tekil", A.olay_say() == sa and B.olay_say() == sb and sa[0] == sa[1] and sb[0] == sb[1], (sa, A.olay_say(), sb, B.olay_say()))
    dd = json.load(open(os.path.join(B.canli, "ortak-durum.json"))); [k.pop("okuma", None) for k in dd["klasorler"].values()]; json.dump(dd, open(os.path.join(B.canli, "ortak-durum.json"), "w"))
    v = B.esitle()
    bak("okuma konumu silinip baştan okununca: alınan 0, çift > 0, olay sayısı aynı", v["son_tur"]["cift"] == 3 and B.olay_say() == sb and v.get("alinan") == 3, v.get("son_tur"))
    # --- üçüncü kişinin dosyası: yarım satır + bozuk satır; ona ait iş B'ye atanmış
    cd = os.path.join(DRIVE, "olaylar", EC, "c-0123456789ab"); os.makedirs(cd); cy = os.path.join(cd, "2026-11.jsonl")
    kid1, kid2 = yapi.yeni_kimlik(), yapi.yeni_kimlik()
    def ol(kid, metin, sahip, saat): return json.dumps({"v": 1, "olay_id": yapi.yeni_kimlik(), "kayit_id": kid, "tur": "kayit_olustu", "zaman": "2026-10-01T12:00:00Z", "saat": saat, "yazan": EC, "yazan_ad": "Can Örnek",
                                                        "cihaz": "c-0123456789ab", "kaynak": "suflor", "veri": {"tur": "is", "metin": metin, "toplanti": "2026-11-05-1200-Can-Toplantisi.md", "baslik": "Can'ın toplantısı",
                                                        "tarih": "2026-11-05", "roller": {"sahip": sahip, "isteyen": {"ad": "Can Örnek", "eposta": EC}}, "vade": "2026-11-15", "durum": "acik"}}, ensure_ascii=False)
    l1, l2 = ol(kid1, "Sözleşme taslağını oku", {"ad": "Bora Kaya", "eposta": EB}, 5), ol(kid2, "Sunumu hazırla", {"ad": "Bora Kaya", "eposta": EB}, 6)
    open(cy, "w", encoding="utf-8").write(l1 + "\n{bozuk satır\n" + l2[:40])  # ikinci olay yarım (Drive henüz bitirmedi)
    v = B.esitle()
    bak("yarım satır atlanır, tam satır alınır, bozuk satır sayılır", v.get("alinan") == 4 and v["son_tur"]["yarim"] == 1 and v["son_tur"]["bozuk"] == 1 and B.kayit("Sözleşme taslağını oku") and not B.kayit("Sunumu hazırla"), v.get("son_tur"))
    open(cy, "a", encoding="utf-8").write(l2[40:] + "\n")
    v = B.esitle()
    bak("satır tamamlanınca kalınan bayttan okunur: yalnız o olay (çift 0)", v["son_tur"]["cift"] == 0 and v["son_tur"]["yarim"] == 0 and B.kayit("Sunumu hazırla") is not None, v.get("son_tur"))
    bk = {x["metin"]: x for x in B.istek("/bugun-veri")["kendi"]}
    bak("üçüncü kişiden atanan iş: Bugün'de 'Sana atandı · Can Örnek' (7 günden eski atama 'yeni' değil)", (bk.get("Sunumu hazırla") or {}).get("atayan") == "Can Örnek" and bk["Sunumu hazırla"].get("atama_yeni") is False, list(bk))
    bak("B başkasının (C) dosyasına yazmaz", sorted(os.listdir(cd)) == ["2026-11.jsonl"] and open(cy, encoding="utf-8").read().count("\n") == 3)
    v = A.esitle()
    bak("A da C'nin olaylarını alır (A'nın işi değil: 'Sana atandı' yok)", v.get("kisiler") == [EB, EC] and A.kayit("Sunumu hazırla") and "atayan" not in A.kayit("Sunumu hazırla"), v.get("kisiler"))
    # --- yarım kalmış kendi yazması: sonraki ek ayrı satırdan başlar
    ay = [os.path.join(k, f) for k, _, fs in os.walk(os.path.join(DRIVE, "olaylar", EA)) for f in fs][0]
    open(ay, "a", encoding="utf-8").write('{"yarim": ')
    A.yaz(M_NORMAL.replace("1400", "1700"), "İkinci toplantı", [{"tur": "is", "metin": "Raporu gönder", "sahip": "Bora Kaya", "sahip_eposta": EB, "tarih": "2026-11-14"}])
    A.esitle(); v = B.esitle()
    bak("A'nın yarım kalan son satırı sonrakine yapışmaz (B yeni işi alır, bozuk 1)", B.kayit("Raporu gönder") is not None and v["son_tur"]["bozuk"] == 1, v.get("son_tur"))
    # --- denetim betiği: biri gizli kaydı klasöre koyarsa yakalar
    gk = next(r[0] for r in sqlite3.connect(os.path.join(A.canli, "karar-grafi.sqlite")).execute("SELECT kayit_id FROM ortak_kayit WHERE gizli = 1"))
    open(cy, "a", encoding="utf-8").write(json.dumps({"v": 1, "kayit_id": gk, "not": "Bütçe özel görüşme"}) + "\n")
    bak("denetim betiği klasördeki gizli kaydı ve başlığı yakalar", len(yapi.ortak_denetim(A.canli, DRIVE)) >= 2 and A.esitle().get("denetim", 0) >= 2)
    bak("günlüğe metin yazılmaz (yalnız sayı)", "ORTAK:" in A.log() and "Teklifi" not in A.log() and "Bütçe" not in A.log())
    bak("teshis KOD_DOSYALARI'nda ortak-klasor.py", '"ortak-klasor.py"' in open(os.path.join(KOD, "teshis.py"), encoding="utf-8").read())
    bak("aktarıcılar hatasız", "Traceback" not in A.log() + B.log(), (A.log() + B.log())[-1500:])
finally:
    for m in (A, B):
        try: m.p.terminate(); m.p.wait(5)
        except Exception: pass
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{'TAMAM' if not hata else 'KALDI: ' + str(len(hata))}"); sys.exit(1 if hata else 0)
