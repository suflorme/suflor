#!/usr/bin/env python3
# Kararlar ve işler görünümü, gündem taslağı ve davet maddeleri (5 Kasım): yapi.kayit_listesi (tüm karar/iş/soru, durum etiketi, gizli toplantı yok, toplantı → özet kaydı),
# yapi.gundem_taslagi (takvim katılımcısı ↔ graf kişi adı gevşek eşleme, aynı başlıklı toplantı, kullanıcının kendi işi yalnız ilgili toplantıdan), yapi.davet_maddeleri
# (pano davetMaddeleri ile aynı kural), graf_yaz'da cevaplı soru açık sayılmaz; aktarıcıda /kayitlar, /gundem-taslagi, /takvim?hafta=0 eposta işareti (anahtarlı).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kayitlar.py      (kaldı → çıkış 1)
AT = "@"  # e-posta biçimi kaynakta geçmesin (açık depo taraması)
import datetime, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(KOD, "test")); sys.path.insert(0, KOD)  # kod önce: test/yapi.py adı çakışır
import yapi; from bosport import bos_port
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-kayit-"); C = os.path.join(T, "canli"); os.makedirs(os.path.join(C, "ozetler")); bugun = datetime.date(2026, 11, 5); rl = None
try:
    bak("davet maddeleri: numara ve işaret kalkar, başlık/bağlantı/parola atlanır, katılım bloğunda durur",
        yapi.davet_maddeleri("Gündem:\n1. Bütçe durumu\n- Tedarikçi seçimi\n• Duyuru\nhttps://ornek.test/x\n________\nMicrosoft Teams toplantısı\n- sonra gelen") == ["Bütçe durumu", "Tedarikçi seçimi", "Duyuru"])
    bak("davet maddeleri: boş not → []", yapi.davet_maddeleri("") == [] and yapi.davet_maddeleri(None) == [])
    bak("kişi eşleme: e-posta kullanıcı adı, 'Soyad, Ad', yalnız ilk ad, bitişik ad", yapi.kisi_eslesir("Ayşe Yılmaz", "ayse.yilmaz"+AT+"firma.test") and yapi.kisi_eslesir("Ayşe Yılmaz", "Yılmaz, Ayşe")
        and yapi.kisi_eslesir("Ayşe", "Ayşe Kaya") and yapi.kisi_eslesir("David Mut", "davidmut"+AT+"x.test") and not yapi.kisi_eslesir("Can Örnek", "Ayşe Yılmaz") and not yapi.kisi_eslesir("", "Ayşe"))
    bak("graf yokken boş liste", yapi.kayit_listesi(C, "Ayşe Deneme", bugun) == {"ad": "Ayşe Deneme", "kayitlar": [], "toplantilar": [], "kisiler": [], "deneme": False, "deneme_say": 0})
    BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    D1, D2, G = "2026-11-03-1000-Butce", "2026-10-28-1500-Proje", "2026-11-04-0900-Ozel"
    for d, s in ((D1, "| 10:00:00 | Ayşe Deneme | merhaba | |\n"), (D2, "| 15:00:00 | Ayşe Deneme | merhaba | |\n"), (G, "| 09:00:10 | **GİZLİ** | açıldı | |\n")):
        open(os.path.join(C, d + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {d}\n\n" + BAS + s)
    def y(top, baslik, tarih, ogeler): yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
    y(G, "Özel", "2026-11-04", [{"tur": "karar", "metin": "Gizli karar", "netlik": "ortuk"}, {"tur": "is", "metin": "Gizli iş", "sahip": "Can Örnek", "tarih": "2026-11-01"}])
    y(D2, "Proje planı", "2026-10-28", [{"tur": "karar", "metin": "Plan Q1'e göre", "netlik": "acik"}, {"tur": "is", "metin": "Plan belgesini paylaş", "sahip": "Zeynep Kaya", "tarih": "2026-10-30"},
                                          {"tur": "soru", "metin": "Kaynak onaylandı mı?", "kim": "Can Örnek", "cevap": "Evet"}, {"tur": "is", "metin": "Risk listesi", "sahip": "Ayşe Deneme", "tarih": "2026-11-20"}])
    y(D1, "Bütçe", "2026-11-03", [{"tur": "karar", "metin": "Bütçe 120 bin", "netlik": "acik"}, {"tur": "karar", "metin": "Tedarikçi Mart'ta", "netlik": "ortuk"},
                                   {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-02"}, {"tur": "is", "metin": "Sözleşmeyi oku", "sahip": "Ayşe Deneme"},
                                   {"tur": "soz", "metin": "Listeyi getirecek", "sahip": "Zeynep Kaya", "tarih": "2026-11-07"}, {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Can Örnek"}])
    hp = os.path.join(C, "ozetler", D1 + "-ozet-zihin-haritasi.html"); open(hp, "w").write("<!doctype html><title>d</title>")
    open(os.path.join(C, "son-toplantilar.jsonl"), "w", encoding="utf-8").write(json.dumps({"id": "son1", "dosya": D1 + ".md", "baslik": "Bütçe", "at": "2026-11-03T11:00:00+03:00", "ozet": hp, "harita": hp, "gorsel": "karar_is"}) + "\n")
    v = yapi.kayit_listesi(C, "Ayşe Deneme", bugun); d = {x["metin"]: x for x in v["kayitlar"]}
    # S236: deneme (Test) toplantısı kayıtları varsayılan gizli; deneme=True ile gelir
    DN = "2026-11-04-1000-Test-1"; open(os.path.join(C, DN + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {DN}\n\n" + BAS + "| 10:00:00 | Ayşe Deneme | merhaba | |\n")
    y(DN, "Test-1", "2026-11-04", [{"tur": "is", "metin": "Deneme işi", "sahip": "Deniz Test", "tarih": "2026-11-01"}, {"tur": "karar", "metin": "Deneme kararı", "netlik": "acik"}])
    v0 = yapi.kayit_listesi(C, "Ayşe Deneme", bugun); v1 = yapi.kayit_listesi(C, "Ayşe Deneme", bugun, deneme=True)
    bak("deneme toplantısı: varsayılanda kayıt, toplantı ve kişi yok; deneme_say 2", not any("Deneme işi" == x["metin"] or x["metin"] == "Deneme kararı" for x in v0["kayitlar"]) and all(t["dosya"] != DN + ".md" for t in v0["toplantilar"])
        and "Deniz Test" not in v0["kisiler"] and v0["deneme_say"] == 2 and v0["deneme"] is False)
    bak("deneme=True: kayıtlar satırda deneme işaretiyle gelir, diğerlerinde deneme false", {x["metin"] for x in v1["kayitlar"] if x["deneme"]} == {"Deneme işi", "Deneme kararı"} and len(v1["kayitlar"]) == len(v0["kayitlar"]) + 2 and any(t["dosya"] == DN + ".md" for t in v1["toplantilar"]))
    bak("deneme tanımı: ad (deneme/test/echo/prova/trial) ya da kayıtta deneme: true", yapi.deneme_mi(C, "2026-11-03-1702-Test-1") and yapi.deneme_mi(C, "2026-10-13-2009-Suflorme-deneme-9.md") and not yapi.deneme_mi(C, D1) and not yapi.deneme_mi(C, "") and yapi.deneme_mi(C, D1, {D1 + ".md": {"deneme": True}}))
    bv = yapi.bugun_veri(C, "Ayşe Deneme", bugun); bv1 = yapi.bugun_veri(C, "Ayşe Deneme", bugun, deneme=True)
    bak("Bugün: deneme toplantısı işi ve kararı varsayılanda yok (son_karar yine Bütçe), deneme=True ile gelir", not any(x["metin"] == "Deneme işi" for x in bv["kendi"] + bv["baskalari"]) and bv["son_karar"] and bv["son_karar"]["baslik"] == "Bütçe"
        and bv1["son_karar"] and bv1["son_karar"]["baslik"] == "Test-1")
    bak("gizli toplantıdan kayıt yok; 10 kayıt", not any("Gizli" in m for m in d) and len(v["kayitlar"]) == 10)
    bak("karar: teyit eki ayrılır → durum teyit + neden; onaylı karar kapandi", d["Tedarikçi Mart'ta"]["durum"] == "teyit" and d["Tedarikçi Mart'ta"]["neden"] == "kimse açıkça onaylamadı" and d["Bütçe 120 bin"]["durum"] == "kapandi")
    bak("iş: gecikme, tarihsiz, kendi; söz de iş sayılır", d["Tabloyu güncelle"]["gecikti"] and d["Tabloyu güncelle"]["kalan_gun"] == -3 and d["Sözleşmeyi oku"]["tarihsiz"] and d["Sözleşmeyi oku"]["kendi"]
        and d["Listeyi getirecek"]["tur"] == "is" and d["Listeyi getirecek"]["id"].startswith("s"))
    bak("soru: cevaplı soru kapandi, cevapsız açık", d["Kaynak onaylandı mı?"]["durum"] == "kapandi" and d["KDV dahil mi?"]["durum"] == "acik" and d["KDV dahil mi?"]["id"].startswith("q"))
    bak("toplantılar: özet kaydı olan toplantının id'si ve haritası, olmayanın boş; yeni önce", [(t["dosya"], t["id"], t["harita"]) for t in v["toplantilar"]] == [(D1 + ".md", "son1", True), (D2 + ".md", "", False)])
    bak("kişiler: en çok kaydı olan önce", v["kisiler"][0] in ("Can Örnek", "Ayşe Deneme", "Zeynep Kaya") and "Gizli" not in str(v["kisiler"]))
    yapi.soz_kapat(C, d["Plan belgesini paylaş"]["id"], "yapildi")
    bak("yapılan iş kapandi olur", {x["metin"]: x["durum"] for x in yapi.kayit_listesi(C, "Ayşe", bugun)["kayitlar"]}["Plan belgesini paylaş"] == "kapandi")
    g = yapi.gundem_taslagi(C, ["can.ornek"+AT+"firma.test"], "Ayşe Deneme", "", bugun)
    bak("gündem taslağı: e-posta katılımcısı graf adıyla eşleşir; ilgili toplantıdan kendi işi, onay bekleyen karar ve açık soru gelir; gecikmiş önce; üçüncü kişinin (Zeynep) işi gelmez (12 Kasım)",
        g["kisiler"] == ["Can Örnek"] and [m["metin"] for m in g["maddeler"]] == ["Tabloyu güncelle", "Sözleşmeyi oku", "Tedarikçi Mart'ta", "KDV dahil mi?"] and g["davet"] is False)
    bak("satır metni: kişi ilk adı ve gecikme; karar 'Onay:', soru 'Soru:'", g["maddeler"][0]["satir"] == "Tabloyu güncelle — Can, 3 gün gecikti" and g["maddeler"][2]["satir"].startswith("Onay: ")
        and g["maddeler"][3]["satir"] == "Soru: KDV dahil mi? (Can)" and g["metin"].startswith("- Tabloyu güncelle"))
    bak("eşleşen katılımcı yokken aynı başlıklı toplantı yeter", [m["metin"] for m in yapi.gundem_taslagi(C, ["Deniz Yeni"], "Ayşe Deneme", "Proje Planı", bugun)["maddeler"]] == ["Risk listesi"])
    bak("katılımcı ve başlık eşleşmezse boş; gizli toplantıdan madde gelmez", yapi.gundem_taslagi(C, ["Deniz Yeni"], "Ayşe Deneme", "Yeni konu", bugun)["maddeler"] == [] and yapi.gundem_taslagi(C, [], "Ayşe", "", bugun)["maddeler"] == []
        and "Gizli" not in yapi.gundem_taslagi(C, ["Can Örnek"], "Ayşe Deneme", "Özel", bugun)["metin"])
    # aktarıcı uçları (anahtarlı): /kayitlar, /gundem-taslagi?olay=, /takvim?hafta=0 eposta
    PORT = bos_port(8799); U = f"http://127.0.0.1:{PORT}"; g0 = datetime.date.today().isoformat()
    ol = lambda i, b, kat, n, ks: {"id": i, "baslik": b, "baslangic": f"{g0}T23:40:00+03:00", "bitis": f"{g0}T23:55:00+03:00", "platform": "teams", "katilimcilar": kat, "katilimci_eposta": ["can.ornek"+AT+"firma.test"], "kisi_sayisi": ks, "notlar": n, "tum_gun": False, "hesap": "D", "takvim": "T"}
    json.dump({"durum": "ok", "olaylar": [ol("ev1", "Haftalık durum paylaşımı", ["can.ornek"+AT+"firma.test"], "Gündem:\n- Haftalık özet ve durum güncellemesi\n- Duyurular\nhttps://ornek.test", 4),
                                          ol("ev2", "Bütçe kararı", ["Can Örnek"], "- Bütçe için karar", 2)]}, open(os.path.join(T, "takvim.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor", "port": PORT, "gelistirici": True, "konusma": False, "yerel_ses": False}, open(os.path.join(T, "ayar.json"), "w"))
    rl = subprocess.Popen([sys.executable, "relay.py", "--dir", C, "--port", str(PORT)], cwd=KOD, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")),
                          stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(40):
        if os.path.exists(os.path.join(C, "kart-anahtari.txt")): break
        time.sleep(0.25)
    time.sleep(1); key = open(os.path.join(C, "kart-anahtari.txt")).read().strip()
    def al(yol, anahtar=True):
        r = urllib.request.Request(U + yol, headers={"X-Suflor-Anahtar": key} if anahtar else {})
        try: return json.load(urllib.request.urlopen(r, timeout=10))
        except urllib.error.HTTPError as e: return {"_kod": e.code}
    bak("/kayitlar anahtarsız 401", al("/kayitlar", False).get("_kod") == 401 and al("/gundem-taslagi?olay=ev1", False).get("_kod") == 401)
    k = al("/kayitlar")
    bak("/kayitlar: ok, kayıtlar + toplantılar + kişiler; gizli yok", k.get("ok") and len(k["kayitlar"]) == 10 and k["toplantilar"][0]["id"] == "son1" and "Gizli" not in json.dumps(k, ensure_ascii=False))
    gt = al("/gundem-taslagi?olay=ev1")
    bak("/gundem-taslagi: davette gündem varsa maddeler davetin maddeleridir (omurga; 12 Kasım), karar satırları uçta dönmez", gt.get("ok") and gt["olay"] == "ev1" and gt.get("davet") is True
        and [m["metin"] for m in gt["maddeler"]] == ["Haftalık özet ve durum güncellemesi", "Duyurular"] and "kararlar" not in gt)
    bak("/gundem-taslagi: gündem yükü (2 madde × 10 dk varsayılan > 15 dk toplantı) → fazla 5, 1 madde ertelenebilir; yük yoksa None",
        gt.get("gundem_yuk") == {"tahmini_dk": 20, "toplanti_dk": 15, "fazla_dk": 5, "ertelenebilir": ["Duyurular"]}
        and yapi.gundem_yuk([{"metin": "A", "dk": 30}, {"metin": "B", "dk": 20}, {"metin": "C"}], 45) == {"tahmini_dk": 60, "toplanti_dk": 45, "fazla_dk": 15, "ertelenebilir": ["C", "B"]}
        and yapi.gundem_yuk([{"metin": "A", "dk": 20}], 45) is None and yapi.gundem_yuk([{"metin": "A"}], 0) is None and yapi.gundem_yuk([], 30) is None)
    gt2 = al("/gundem-taslagi?olay=ev2")
    bak("/gundem-taslagi: gündemsiz davette süzülmüş açık kayıtlar (Can'ın işi önce)", gt2.get("ok") and gt2.get("davet") is False and [m["metin"] for m in gt2["maddeler"]][:1] == ["Tabloyu güncelle"])
    gk = [json.loads(l) for l in open(os.path.join(C, "guncellik.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(C, "guncellik.jsonl")) else []
    bak("/gundem-taslagi: karne satırları yazılır (metin yok: id/durum/karar), aynı karar kümesi yeniden yazılmaz", gk and all("metin" not in k for k in gk) and any(k.get("karar") == "taslak" for k in gk)
        and (al("/gundem-taslagi?olay=ev2") and len(open(os.path.join(C, "guncellik.jsonl"), encoding="utf-8").readlines()) == len(gk)))
    bak("/gundem-taslagi: bilinmeyen olay → ok false, boş", al("/gundem-taslagi?olay=yok").get("ok") is False and al("/gundem-taslagi?olay=yok")["maddeler"] == [])
    tk = al("/takvim?hafta=0"); e = {o["id"]: o.get("eposta") for o in tk.get("olaylar") or []}
    bak("/takvim: bilgi aktarımı gündemli 4 kişilik toplantıda e-posta işareti (maddeler + alıcılar); karar gündemli 2 kişilikte yok",
        e.get("ev1") and e["ev1"]["guclu"] and e["ev1"]["maddeler"] == ["Haftalık özet ve durum güncellemesi", "Duyurular"] and e["ev1"]["alicilar"] == ["can.ornek"+AT+"firma.test"] and e.get("ev2") is None)
    # tc hazirlik --katilimci: aynı bölüm metin çıktısında
    json.dump({"title": "Haftalık durum paylaşımı", "items": ["Haftalık özet ve durum güncellemesi", "Duyurular"]}, open(os.path.join(C, "agenda.json"), "w"))
    r = subprocess.run([sys.executable, "-B", "toplanti-claude.py", "--dir", C, "--relay", U, "hazirlik", "--katilimci", "can.ornek"+AT+"firma.test, Deniz Yeni", "--kisi", "4"], cwd=KOD, capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "ayar.json")))
    bak("tc hazirlik --katilimci: gündem omurga bölümü (güncellik katmanı), G1/G2 maddeleri, eşleşen kişi, ayıklanan sayısı; e-posta işareti", "## Gündem ve ilgili kayıtlar (gündem omurga; eşleşen: Can Örnek)" in r.stdout
        and "G1. Haftalık özet ve durum güncellemesi" in r.stdout and "G2. Duyurular" in r.stdout and "Kayıtlardan ayıklanan:" in r.stdout and "GÜÇLÜ" in r.stdout)
finally:
    if rl: rl.terminate()
    shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
