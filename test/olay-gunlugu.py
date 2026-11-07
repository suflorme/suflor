#!/usr/bin/env python3
# Ortak karar katmanı A0 (yerel temel; ../planlar/ortak-karar-mimarisi-20261105.md §3, §8): yapi.py olay günlüğü + ortak_kayit izdüşümü.
# Denetlenen: aynı toplantı iki kez yazılınca kimlikler (yerel id ve kayit_id) aynı kalır, kapalı iş geri açılmaz, kullanıcının onayı korunur; değişen metin aynı kimlikte
# metin_duzeltildi olur; çıkan öğe yerelden kalkar, izdüşümde iptal; her yazma bir olay üretir (graf_yaz, soz_kapat, karar_teyit_kaldir, karar_yaz, soz_ekle, eylem_esle,
# ata, ertele, bol, geri_al, arşiv MCP); tarihçe "kim ne zaman kapattı"; günlük yalnız eklenir (UPDATE/DELETE durur); izdüşüm günlükten baştan kurulunca aynı tablo;
# gizli toplantının olayı gizli = 1 ve okuyanlarda görünmez; eski şemadan (v0.196.0) göç kayıpsız ve okuyanların çıktısı aynı; onay süresi (3. gün, 7. gün, sonraki dizi toplantısı).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/olay-gunlugu.py      (kaldı → çıkış 1; ~3 sn; aktarıcı açmaz)
import datetime, importlib.util, json, os, shutil, sqlite3, subprocess, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="suflor-olay-"); AY = os.path.join(T, "ayar.json")
json.dump({"ad": "Ayşe Deneme"}, open(AY, "w")); os.environ["SUFLOR_AYAR"] = AY  # yazan = "ad:Ayşe Deneme" (gerçek ayar okunmaz)
import yapi
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def dokum(C, ad, gizli=False):
    open(os.path.join(C, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n"
                                                                   + ("| 10:00:05 | **GİZLİ** | açıldı | |\n" if gizli else ""))
def db(C): return sqlite3.connect(os.path.join(C, "karar-grafi.sqlite"))
def olay_say(C): return db(C).execute("SELECT COUNT(*) FROM olay").fetchone()[0]
def kayitlar(C, top): return {r[1]: r for r in db(C).execute("SELECT id, metin, kayit_id, durum, onay FROM kayit WHERE toplanti = ? ORDER BY id", (top + ".md",))}
def ortak(C): return sorted(tuple(r) for r in db(C).execute("SELECT kayit_id, tur, metin, toplanti, roller, vade, durum, onay, onay_neden, ust, bag, gundem, gizli, son_saat FROM ortak_kayit"))
try:
    C = os.path.join(T, "canli"); os.makedirs(C); bugun = datetime.date(2026, 11, 5)
    D1, D2, G = "2026-11-03-1000-Haftalik-Butce", "2026-11-04-0900-Satis", "2026-11-04-1500-Ozel"
    for d in (D1, D2): dokum(C, d)
    dokum(C, G, True)
    Y1 = [{"tur": "karar", "metin": "Bütçe 120 bin olarak kalıyor", "kim": "Can Örnek", "saat": "10:05:00", "netlik": "ortuk"},
          {"tur": "karar", "metin": "Tedarikçi Mart'ta seçilecek", "kim": "Ayşe Deneme", "saat": "10:07:00", "netlik": "acik"},
          {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-10", "saat": "10:10:00"},
          {"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe Deneme", "saat": "10:12:00"},
          {"tur": "soz", "metin": "Listeyi getirecek", "sahip": "Zeynep Kaya", "tarih": "2026-11-07", "saat": "10:13:00"},
          {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Can Örnek", "saat": "10:14:00"},
          {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Can Örnek", "saat": "10:15:00"}]
    def yaz(top, og, tarih="2026-11-03", baslik="Haftalık bütçe"): return yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": og}]}, top + ".md")
    yaz(D1, Y1)
    bak("ilk yazma: ortak türlerin her biri bir kayit_olustu olayı (6), iddia olaysız", olay_say(C) == 6
        and db(C).execute("SELECT COUNT(*) FROM olay WHERE tur = 'kayit_olustu'").fetchone()[0] == 6)
    bak("şema sürümü 1, günlük ve izdüşüm tabloları var", db(C).execute("PRAGMA user_version").fetchone()[0] == yapi.SEMA_SURUM
        and db(C).execute("SELECT COUNT(*) FROM ortak_kayit").fetchone()[0] == 6)
    k1 = kayitlar(C, D1)
    bak("teyit metin eki değil alan: metin temiz, onay bekliyor", k1["Bütçe 120 bin olarak kalıyor"][4] == "bekliyor" and "teyit" not in k1["Bütçe 120 bin olarak kalıyor"][1]
        and k1["Tedarikçi Mart'ta seçilecek"][4] is None)
    bak("kayit_id küresel biçimde (26 karakter, hepsi farklı)", all(yapi.KIMLIK_RX.match(r[2] or "") for r in k1.values()) and len({r[2] for r in k1.values()}) == len(k1))
    roller = yapi.ortak_kayit(C, k1["Bütçe 120 bin olarak kalıyor"][2])["roller"]
    bak("roller: karar isteyen = söyleyen, onaylayan = yürüten (kullanıcı), sahip yok; iş sahibi", roller["isteyen"] == {"ad": "Can Örnek"} and roller["onaylayan"].get("ben")
        and roller["sahip"] is None and yapi.ortak_kayit(C, f"s{k1['Tabloyu güncelle'][0]}")["roller"]["sahip"] == {"ad": "Can Örnek"})
    # kullanıcı işleri: kapat, onayla
    sid = f"s{k1['Tabloyu güncelle'][0]}"; kid = f"k{k1['Bütçe 120 bin olarak kalıyor'][0]}"; n = olay_say(C)
    yapi.soz_kapat(C, sid, "yapildi"); bak("soz_kapat bir olay (durum_degisti)", olay_say(C) == n + 1)
    yapi.soz_kapat(C, sid, "yapildi"); bak("aynı durum ikinci kez: olay yok", olay_say(C) == n + 1)
    bak("karar_teyit_kaldir → karar_onaylandi olayı, metin döner", yapi.karar_teyit_kaldir(C, kid) == "Bütçe 120 bin olarak kalıyor" and olay_say(C) == n + 2
        and yapi.karar_teyit_kaldir(C, kid) is None)
    th = yapi.tarihce(C, sid)
    bak("tarihçe: kim ne zaman kapattı (yazan, UTC zaman, açık → yapıldı)", len(th) == 2 and th[-1]["tur"] == "durum_degisti" and th[-1]["yazan"] == "ad:Ayşe Deneme"
        and th[-1]["zaman"].endswith("Z") and "açık → yapıldı" in th[-1]["ozet"] and "Ayşe Deneme" in th[-1]["ozet"])
    # aynı toplantı ikinci kez (aynı yapı): kimlik %100, olay yok, kapalı iş açılmaz, onay korunur
    n = olay_say(C); yaz(D1, Y1); k2 = kayitlar(C, D1)
    bak("aynı yapı yeniden yazıldı: yerel id ve kayit_id %100 korundu, olay yok", {m: (r[0], r[2]) for m, r in k1.items()} == {m: (r[0], r[2]) for m, r in k2.items()} and olay_say(C) == n)
    bak("kapalı iş geri açılmadı, verilen onay korundu", k2["Tabloyu güncelle"][3] == "yapildi" and k2["Bütçe 120 bin olarak kalıyor"][4] == "onaylandi")
    # değişen özet: bir metin hafif değişti, vade değişti, bir iş çıktı, yeni iş geldi, soru cevaplandı
    Y2 = [dict(o) for o in Y1]
    Y2[0]["metin"] = "Bütçe 120 bin TL olarak kalıyor"; Y2[2]["tarih"] = "2026-11-12"; Y2[5]["cevap"] = "Hayır"; del Y2[3]
    Y2.append({"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "saat": "10:20:00"})
    n = olay_say(C); yaz(D1, Y2); k3 = kayitlar(C, D1)
    bak("hafif değişen karar: aynı kimlik, metin güncel, onay korundu", k3["Bütçe 120 bin TL olarak kalıyor"][2] == k1["Bütçe 120 bin olarak kalıyor"][2]
        and k3["Bütçe 120 bin TL olarak kalıyor"][4] == "onaylandi")
    bak("kapalı işin vadesi değişse de açılmaz", k3["Tabloyu güncelle"][3] == "yapildi" and k3["Tabloyu güncelle"][2] == k1["Tabloyu güncelle"][2])
    cikan = yapi.ortak_kayit(C, k1["Sözleşmeyi oku"][2])
    bak("çıkan iş: yerel tablodan kalktı, izdüşümde iptal (neden özet yeniden yazıldı)", "Sözleşmeyi oku" not in k3 and cikan["durum"] == "iptal"
        and yapi.tarihce(C, cikan["kayit_id"])[-1]["veri"].get("neden") == yapi.YENIDEN_YAZILDI)
    bak("yeni iş yeni kimlikle; cevaplanan soru kapandı", "Teklifi revize et" in k3 and k3["Teklifi revize et"][2] not in {r[2] for r in k1.values()} and k3["KDV dahil mi?"][3] == "cevaplandi")
    turler = [r[0] for r in db(C).execute("SELECT tur FROM olay WHERE saat > (SELECT MAX(saat) FROM olay) - ? ORDER BY saat", (olay_say(C) - n,)).fetchall()]
    bak(f"yeniden yazma yalnız farkı olay yaptı ({', '.join(turler)})", sorted(turler) == sorted(["metin_duzeltildi", "ertelendi", "durum_degisti", "durum_degisti", "kayit_olustu"]))
    # eylem menüsü işlevleri: ata, ertele, yorum, gündem, geri al
    yid = f"s{k3['Teklifi revize et'][0]}"; n = olay_say(C)
    o, x = yapi.ata(C, yid, {"sahip": {"ad": "Zeynep Kaya", "eposta": "zeynep" + "@" + "ornek.test"}, "bilgi": ["Can Örnek"]})
    bak("ata: is_atandi, sahip ve bilgi; yerel sahip sütunu eşitlendi", o and o["tur"] == "is_atandi" and x["roller"]["sahip"]["eposta"].startswith("zeynep")
        and x["roller"]["bilgi"] == [{"ad": "Can Örnek"}] and db(C).execute("SELECT sahip FROM kayit WHERE id = ?", (int(yid[1:]),)).fetchone()[0] == "Zeynep Kaya")
    o2, x = yapi.ertele(C, yid, "2026-11-20", "tedarikçi gecikti")
    bak("ertele: vade alanı ve yerel son_tarih", x["vade"] == "2026-11-20" and db(C).execute("SELECT son_tarih FROM kayit WHERE id = ?", (int(yid[1:]),)).fetchone()[0] == "2026-11-20")
    yapi.yorum_ekle(C, yid, "Fiyatlar perşembe gelir"); yapi.gundeme_ekle(C, yid, "etkinlik-1", "2026-11-10", "Satış")
    bak("yorum ve gündem olayları; gündem izdüşümde", olay_say(C) == n + 4 and yapi.ortak_kayit(C, yid)["gundem"]["etkinlik"] == "etkinlik-1")
    g = yapi.geri_al(C, o2["olay_id"])
    bak("geri al: yeni olay (günlük değişmez), vade eski hâline döndü", len(g) == 1 and g[0]["tur"] == "kayit_guncellendi" and yapi.ortak_kayit(C, yid)["vade"] == "")
    # elle söz, eylem kuyruğu
    n = olay_say(C); s = yapi.soz_ekle(C, "Bora Kaya", "Raporu gönderecek", "2026-11-09", D2 + ".md", "Satış")
    bak("soz_ekle: kayit_olustu", olay_say(C) == n + 1 and yapi.ortak_kayit(C, s["id"])["tur"] == "soz")
    E = [{"id": "e1", "tur": "eposta", "baslik": "Bora'ya takip", "durum": "bekliyor"}, {"id": "e2", "tur": "kayit", "baslik": "atlanır"}]
    n = olay_say(C); yapi.eylem_esle(C, E, "Ayşe Deneme", D2 + ".md"); yapi.eylem_esle(C, E, "Ayşe Deneme", ekle=False)
    bak("eylem_esle: dış iş bir olay; okumadan önceki eşitleme olay şişirmez", olay_say(C) == n + 1)
    E[0]["durum"] = "yapildi"; yapi.eylem_esle(C, E, "Ayşe Deneme", ekle=False)
    eid = db(C).execute("SELECT kayit_id FROM kayit WHERE bag = 'eylem:e1'").fetchone()[0]
    bak("eylem yapıldı → durum_degisti (kaynak eylem)", olay_say(C) == n + 2 and yapi.tarihce(C, eid)[-1]["kaynak"] == "eylem" and yapi.ortak_kayit(C, eid)["durum"] == "yapildi")
    E[0]["durum"] = "bekliyor"; yapi.eylem_esle(C, E, "Ayşe Deneme", ekle=False)
    bak("kuyruk 'bekliyor' dese de kapalı eylem işi geri açılmaz", yapi.ortak_kayit(C, eid)["durum"] == "yapildi")
    # gizli toplantı
    yaz(G, [{"tur": "karar", "metin": "Gizli karar", "kim": "Can Örnek"}, {"tur": "is", "metin": "Gizli iş", "sahip": "Ayşe Deneme"}], "2026-11-04", "Özel")
    gz = db(C).execute("SELECT DISTINCT o.gizli FROM olay o JOIN ortak_kayit k USING (kayit_id) WHERE k.toplanti = ?", (G + ".md",)).fetchall()
    bak("gizli toplantı: olay yazılır ama gizli = 1; okuyanlarda görünmez", gz == [(1,)] and db(C).execute("SELECT COUNT(*) FROM olay WHERE gizli = 1").fetchone()[0] == 2
        and not any("Gizli" in x["metin"] for x in yapi.kayit_listesi(C, "Ayşe Deneme", bugun)["kayitlar"]))
    # yalnız eklenir
    try: db(C).execute("UPDATE olay SET tur = 'x'"); deg = True
    except sqlite3.DatabaseError: deg = False
    try: db(C).execute("DELETE FROM olay"); sil = True
    except sqlite3.DatabaseError: sil = False
    bak("günlük yalnız eklenir: UPDATE ve DELETE durur", not deg and not sil)
    # izdüşüm günlükten baştan kurulunca aynı tablo; yerel kayit de aynı
    once, yerel = ortak(C), db(C).execute("SELECT id, kayit_id, metin, durum, onay, sahip, son_tarih FROM kayit ORDER BY id").fetchall()
    yapi.izdusum_kur(C)
    bak(f"izdüşüm günlükten baştan kuruldu: {len(once)} kayıt aynı, yerel tablo aynı", once == ortak(C) and yerel == db(C).execute("SELECT id, kayit_id, metin, durum, onay, sahip, son_tarih FROM kayit ORDER BY id").fetchall())
    bak("mantıksal saat kesintisiz artar, olay kimlikleri tekil", [r[0] for r in db(C).execute("SELECT saat FROM olay ORDER BY saat")] == list(range(1, olay_say(C) + 1)))
    # arşiv MCP: yazma olaya kaynak arsiv-mcp ile
    open(os.path.join(C, "kart-anahtari.txt"), "w").write("deneme")
    p = subprocess.Popen([sys.executable, "-B", os.path.join(KOD, "arsiv-mcp.py"), "--dir", C, "--relay", "http://127.0.0.1:9"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    def mcp(i, yontem, params):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": yontem, "params": params}) + "\n"); p.stdin.flush(); return json.loads(p.stdout.readline())
    mcp(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "d", "version": "1"}})
    sz = f"s{db(C).execute('SELECT id FROM kayit WHERE metin = ?', ('Listeyi getirecek',)).fetchone()[0]}"
    r = json.loads(mcp(2, "tools/call", {"name": "is_durumu", "arguments": {"id": sz, "durum": "yapildi", "onayla": True}})["result"]["content"][0]["text"])
    kk = json.loads(mcp(3, "tools/call", {"name": "kararlar", "arguments": {}})["result"]["content"][0]["text"])
    p.stdin.close(); p.wait(timeout=5)
    th = yapi.tarihce(C, sz)
    bak("arşiv MCP is_durumu: olay kaynak arsiv-mcp; kararlar metni bugünkü biçimde", r.get("uygulandi") and th[-1]["kaynak"] == "arsiv-mcp" and th[-1]["veri"]["durum"] == "tutuldu"
        and all("kayit_id" in x for x in kk["kararlar"]))
    # onay süresi (S227)
    od = lambda t, sn=None: yapi.onay_durumu("bekliyor", t, bugun, sn)
    bak("onay süresi: 2. gün bekliyor, 3. gün hatırlat, 6. gün hatırlat, 7. gün onaylanmadı", (od("2026-11-03")["durum"], od("2026-11-03")["hatirlat"]) == ("bekliyor", False)
        and od("2026-11-02")["hatirlat"] and od("2026-10-30")["durum"] == "bekliyor" and od("2026-10-29")["durum"] == "onaylanmadi")
    bak("onay süresi: dizinin sonraki toplantısı geçtiyse 1. günde de onaylanmadı; gelecekteki toplantı saymaz", od("2026-11-04", "2026-11-05")["durum"] == "onaylanmadi"
        and od("2026-11-04", "2026-11-06")["durum"] == "bekliyor" and yapi.onay_durumu("onaylandi", "2026-10-01", bugun)["durum"] == "onaylandi")
    C2 = os.path.join(T, "dizi"); os.makedirs(C2); A, B = "2026-10-27-1000-Haftalik-Butce", "2026-11-03-1000-Haftalik-Butce"
    for d in (A, B): dokum(C2, d)
    yapi.graf_yaz(C2, {"baslik": "Haftalık", "tarih": "2026-10-27", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "karar", "metin": "Eski karar", "netlik": "tek"}]}]}, A + ".md")
    yapi.graf_yaz(C2, {"baslik": "Haftalık", "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "karar", "metin": "Yeni karar", "netlik": "tek"}]}]}, B + ".md")
    ol = {x["metin"]: x["onay"] for x in yapi.onay_listesi(C2, datetime.date(2026, 11, 4))}
    bak("onay_listesi: dizi anahtarı takvim başlığından; önceki haftanın kararı sonraki toplantıda onaylanmadı, yenisi 1. gün bekliyor",
        yapi.dizi_anahtari(A + ".md") == "haftalik butce" and ol["Eski karar"]["durum"] == "onaylanmadi" and ol["Yeni karar"]["durum"] == "bekliyor")
    kl = {x["metin"]: x for x in yapi.kayit_listesi(C2, "", datetime.date(2026, 11, 6))["kayitlar"]}
    bak("kayit_listesi: bekleyen kararda hesaplanan onay (durum teyit kalır)", kl["Yeni karar"]["durum"] == "teyit" and kl["Yeni karar"]["onay"]["hatirlat"])
    # göç: v0.196.0 şemasıyla yazılmış veritabanı → kayıpsız, okuyanların çıktısı aynı
    sp = importlib.util.spec_from_file_location("yapi_eski", os.path.join(os.path.dirname(KOD), "_yedek", "yapi-v0.196.0.py"))
    if not os.path.exists(sp.origin): bak("göç: eski sürüm yedeği yok (../_yedek/yapi-v0.196.0.py)", False)
    else:
        ye = importlib.util.module_from_spec(sp); sp.loader.exec_module(ye)
        C3 = os.path.join(T, "goc"); os.makedirs(C3)
        for d in (D1, D2): dokum(C3, d)
        dokum(C3, G, True)
        for top, og, tr in ((D1, Y1, "2026-11-03"), (D2, Y2, "2026-11-04"), (G, [{"tur": "karar", "metin": "Gizli karar", "netlik": "ortuk"}], "2026-11-04")):
            ye.graf_yaz(C3, {"baslik": top[16:], "tarih": tr, "maddeler": [{"baslik": "G", "ogeler": og}]}, top + ".md")
        ye.soz_ekle(C3, "Bora Kaya", "Elle söz", None, D2 + ".md", "Satış"); ye.eylem_esle(C3, [{"id": "e1", "tur": "takip", "baslik": "Takip", "durum": "yapildi"}], "Ayşe Deneme", D1 + ".md")
        ye.soz_kapat(C3, "s3", "yapildi")
        once = {"liste": ye.kayit_listesi(C3, "Ayşe Deneme", bugun), "bugun": ye.bugun_veri(C3, "Ayşe Deneme", bugun), "graf": ye.graf_liste(C3, None, 100),
                "kisi": ye.graf_kisi(C3, "Can", 50), "disa": json.loads(ye.disa_aktar(C3, "json")[0])["kayitlar"], "sozler": ye.sozler(C3)}
        say0 = db(C3).execute("SELECT COUNT(*) FROM kayit").fetchone()[0]; ortak0 = db(C3).execute("SELECT COUNT(*) FROM kayit WHERE tur IN ('karar','is','soz','soru')").fetchone()[0]
        def temiz(v):  # yeni alanlar (kayit_id, onay; eylem menüsü: sahip_eposta, gundem, alt; S236: deneme, deneme_say) karşılaştırmada atılır
            if isinstance(v, dict): return {k: temiz(x) for k, x in v.items() if k not in ("kayit_id", "onay", "sahip_eposta", "gundem", "alt", "deneme", "deneme_say")}
            if isinstance(v, (list, tuple)): return [temiz(x) for x in v]
            return v
        sonra = {"liste": yapi.kayit_listesi(C3, "Ayşe Deneme", bugun), "bugun": yapi.bugun_veri(C3, "Ayşe Deneme", bugun), "graf": yapi.graf_liste(C3, None, 100),
                 "kisi": yapi.graf_kisi(C3, "Can", 50), "disa": json.loads(yapi.disa_aktar(C3, "json")[0])["kayitlar"], "sozler": yapi.sozler(C3)}
        bak(f"göç: kayıt sayısı eşit ({say0}), ortak kayıt = ice-aktarma olayı = izdüşüm ({ortak0})", db(C3).execute("SELECT COUNT(*) FROM kayit").fetchone()[0] == say0
            and db(C3).execute("SELECT COUNT(*) FROM olay WHERE kaynak = 'ice-aktarma'").fetchone()[0] == ortak0 == db(C3).execute("SELECT COUNT(*) FROM ortak_kayit").fetchone()[0])
        fark = [k for k in once if temiz(once[k]) != temiz(sonra[k])]
        bak(f"göç: okuyanların çıktısı aynı (kayit_listesi, bugun_veri, graf_liste, graf_kisi, disa_aktar, sozler){' — fark: ' + ', '.join(fark) if fark else ''}", not fark)
        bak("göç: teyit eki alana taşındı, metinde ek kalmadı", db(C3).execute("SELECT COUNT(*) FROM kayit WHERE metin LIKE '%teyit bekliyor%'").fetchone()[0] == 0
            and db(C3).execute("SELECT COUNT(*) FROM kayit WHERE onay = 'bekliyor'").fetchone()[0] == 3)
        bak("göç: gizli toplantının ice-aktarma olayı gizli = 1; kapalı durum korundu", db(C3).execute("SELECT o.gizli FROM olay o JOIN ortak_kayit k USING (kayit_id) WHERE k.metin = 'Gizli karar'").fetchone() == (1,)
            and db(C3).execute("SELECT durum FROM ortak_kayit WHERE kayit_id = (SELECT kayit_id FROM kayit WHERE id = 3)").fetchone()[0] == "yapildi")
        ye.soz_ekle(C3, "Can Örnek", "Eski aktarıcının sözü")  # kurulumdan önce çalışan eski sürüm kimliksiz satır ekler
        bak("eski sürümün eklediği kimliksiz satır ilk açılışta kimlik ve olay alır", yapi.ortak_kayit(C3, f"s{db(C3).execute('SELECT MAX(id) FROM kayit').fetchone()[0]}") is not None)
        o1 = olay_say(C3); yapi.izdusum_kur(C3); yapi.kayit_listesi(C3, "", bugun)
        bak("göç ikinci açılışta tekrar etmez", olay_say(C3) == o1)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("olay günlüğü: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı"))
sys.exit(1 if hata else 0)
