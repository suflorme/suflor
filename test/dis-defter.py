#!/usr/bin/env python3
# Dış karar kaydı (yapi.py dis_defter_oku / dis_defter_veri / disa_aktar; S212): CSV (virgül, noktalı virgül, sekme) ve JSON içe aktarma, başlık eşleme, kapalı kayıt
# sayılır ama listelenmez, bozuk/eksik dosya hata metniyle döner (çökmez), dışa aktarma alanları sabit ve gizli toplantının kaydı dışarıda kalır.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dis-defter.py
import csv, datetime, io, json, os, shutil, sys, tempfile
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import yapi
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-disdefter-")
try:
    y = lambda ad, metin: (open(os.path.join(T, ad), "w", encoding="utf-8").write(metin), os.path.join(T, ad))[1]
    c1 = y("a.csv", "Tarih;Toplantı;Tür;Metin;Sahip;Vade;Durum\n2026-10-28;Yönetim;Karar;Yeni ofis yok;;;açık\n2026-10-28;Yönetim;İş;Kira teklifini iptal et;Ayşe Deneme;2026-11-06;açık\n2026-10-30;Pazarlama;Task;Bütçeyi gözden geçir;Can Örnek;2026-11-12;open\n2026-10-30;Pazarlama;İş;Eski iş;Can Örnek;2026-10-20;done\n;;;;;;\n")
    r = yapi.dis_defter_oku(c1)
    bak("CSV (noktalı virgül): 4 kayıt, boş satır atlanır", r["ok"] and len(r["kayitlar"]) == 4 and not r["hata"])
    bak("tür eşleme: Karar/İş/Task → karar/is; durum done → kapalı", [x["tur"] for x in r["kayitlar"]] == ["karar", "is", "is", "is"] and [x["kapali"] for x in r["kayitlar"]] == [False, False, False, True])
    bak("alanlar: sahip, vade, toplantı", r["kayitlar"][1]["sahip"] == "Ayşe Deneme" and r["kayitlar"][1]["vade"] == "2026-11-06" and r["kayitlar"][0]["toplanti"] == "Yönetim")
    c2 = y("b.csv", "﻿date,title,owner,due date,status\n2026-11-01,Decide vendor,Ayşe,2026-11-20,open\n2026-11-01,Ship report,,,\n")
    r2 = yapi.dis_defter_oku(c2)
    bak("CSV (virgül, İngilizce başlık, BOM): title → metin; sahip/vade varsa iş, yoksa karar", r2["ok"] and [(x["metin"], x["tur"]) for x in r2["kayitlar"]] == [("Decide vendor", "is"), ("Ship report", "karar")])
    t1 = y("c.tsv", "metin\tsahip\nSekmeli iş\tCan\n"); r3 = yapi.dis_defter_oku(t1)
    bak("TSV okunur", r3["ok"] and r3["kayitlar"][0]["metin"] == "Sekmeli iş" and r3["kayitlar"][0]["sahip"] == "Can")
    j1 = y("d.json", json.dumps({"decisions": [{"text": "JSON karar", "date": "2026-10-01"}], "tasks": [{"text": "JSON iş", "assignee": "Zeynep", "due": "2026-11-09", "status": "Done"}, {"text": "JSON iş 2", "assignee": "Zeynep"}], "meta": {"x": 1}}, ensure_ascii=False))
    r4 = yapi.dis_defter_oku(j1)
    bak("JSON (liste alanlı sözlük): alan adı türü verir, kapalı sayılır", r4["ok"] and [(x["metin"], x["tur"], x["kapali"]) for x in r4["kayitlar"]] == [("JSON karar", "karar", False), ("JSON iş", "is", True), ("JSON iş 2", "is", False)])
    j2 = y("e.json", json.dumps([{"karar": "Düz liste kararı", "kim": "Ali"}])); r5 = yapi.dis_defter_oku(j2)
    bak("JSON (düz liste): karar sütunu metin olur", r5["ok"] and r5["kayitlar"][0]["metin"] == "Düz liste kararı" and r5["kayitlar"][0]["sahip"] == "Ali")
    for ad, metin, bekle in (("bozuk.json", "{bozuk", "JSON okunamadı"), ("bos.json", "{\"a\": 1}", "kayıt listesi yok"), ("bas.csv", "a;b\n1;2\n", "metin/karar/iş sütunu yok")):
        r6 = yapi.dis_defter_oku(y(ad, metin)); bak(f"bozuk dosya hata metniyle döner: {ad}", not r6["ok"] and bekle in r6["hata"] and r6["kayitlar"] == [])
    r7 = yapi.dis_defter_oku(os.path.join(T, "yok.csv")); bak("olmayan dosya: ok False, çökmez", not r7["ok"] and "okunamadı" in r7["hata"])
    bak("uzantı sınırı (.txt yok) ve boş yol", not yapi.dis_defter_oku(y("x.txt", "metin\nx\n"))["ok"] and not yapi.dis_defter_oku("")["ok"])
    v = yapi.dis_defter_veri([{"ad": "Yönetim", "tur": "dosya", "yol": c1}, {"ad": "Hub", "tur": "mcp", "sunucu": "hub"}, {"ad": "Yok", "tur": "dosya", "yol": os.path.join(T, "yok.csv")}, "çöp"], "Can Örnek")
    bak("dis_defter_veri: yalnız dosya türü; kapalı sayılır listelenmez; kişinin kaydı önce; okunamayan hata ile", [d["ad"] for d in v] == ["Yönetim", "Yok"] and v[0]["toplam"] == 4 and v[0]["acik"] == 3 and v[0]["kayitlar"][0]["sahip"] == "Can Örnek" and not v[1]["ok"] and v[1]["hata"])
    bak("ayar liste değilse boş", yapi.dis_defter_veri(None) == [] and yapi.dis_defter_veri("x") == [])
    # dışa aktarma: karar grafı + gizli toplantı
    D1, G = "2026-11-05-0930-Butce", "2026-11-04-1500-Ozel"; BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    y(D1 + ".md", "# Canlı transkript — Bütçe\n\n" + BAS + "| 09:30:00 | Ayşe | merhaba | |\n"); y(G + ".md", "# Canlı transkript — Özel\n\n" + BAS + "| 15:00:10 | **GİZLİ** | açıldı | |\n")
    m, ad, n = yapi.disa_aktar(T, "csv"); bak("graf yokken: yalnız başlık satırı", n == 0 and m.lstrip("﻿").splitlines() == [",".join(yapi.DISA_ALANLAR)])
    yg = lambda top, og: yapi.graf_yaz(T, {"baslik": top, "tarih": "2026-11-05", "maddeler": [{"baslik": "G", "ogeler": og}]}, top + ".md")
    yg(G, [{"tur": "karar", "metin": "Gizli karar"}, {"tur": "is", "metin": "Gizli iş", "sahip": "Ayşe"}])
    yg(D1, [{"tur": "karar", "metin": "Bütçe kalıyor", "netlik": "ortuk", "saat": "09:40:00"}, {"tur": "is", "metin": "Tabloyu güncelle", "sahip": "Ayşe", "tarih": "2026-11-08", "saat": "09:41:00"},
            {"tur": "soz", "metin": "Fatura gönderecek", "sahip": "Can"}, {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Ali"}, {"tur": "sayi", "metin": "95 bin", "kim": "Ali"}])
    m, ad, n = yapi.disa_aktar(T, "csv"); rows = list(csv.DictReader(io.StringIO(m.lstrip("﻿"))))
    bak("CSV dışa aktarma: 4 kayıt (sayı girmez), alanlar sabit, BOM var, dosya adı tarihli", n == 4 and m.startswith("﻿") and list(rows[0].keys()) == list(yapi.DISA_ALANLAR) and ad.startswith("suflor-kararlar-") and ad.endswith(".csv"))
    bak("gizli toplantının kaydı dışarıda", not any("Gizli" in r["metin"] for r in rows))
    k = next(r for r in rows if r["tur"] == "karar"); i = next(r for r in rows if r["tur"] == "is")
    bak("karar: teyit eki metinden çıkar, durum 'teyit bekliyor', kaynak saat", k["metin"] == "Bütçe kalıyor" and k["durum"] == "teyit bekliyor" and k["kaynak_saat"] == "09:40:00" and k["toplanti"] == D1)
    bak("iş: sahip, vade, durum acik", i["sahip"] == "Ayşe" and i["vade"] == "2026-11-08" and i["durum"] == "acik")
    mj, adj, nj = yapi.disa_aktar(T, "json"); j = json.loads(mj)
    bak("JSON dışa aktarma: aynı kayıtlar, kaynak Suflor.me", nj == 4 and j["kaynak"] == "Suflor.me" and len(j["kayitlar"]) == 4 and set(j["kayitlar"][0]) == set(yapi.DISA_ALANLAR) and adj.endswith(".json"))
    bak("teyit nedeni kullanıcı dilinde", yapi.teyit_neden_sade("tek taraflı (öteki taraf cevap vermedi); varsayım: kur sabit") == "karşı taraf cevap vermedi; varsayıma dayanıyor: kur sabit" and yapi.teyit_neden_sade("örtük kabul (kimse açıkça onaylamadı)") == "kimse açıkça onaylamadı" and yapi.teyit_neden_sade("") == "")
finally: shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not hata else f"KALDI: {hata}")); sys.exit(1 if hata else 0)
