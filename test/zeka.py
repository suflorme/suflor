#!/usr/bin/env python3
# Zekâ karnesi (zeka.py + aktarici/dusunme.py tetik/uçları + aktarici/beta-veri.py paketi + teshis süzgeci): kurgu canli/ klasöründe ölçütler, asgari örnek
# ("yetersiz veri" uydurmaz), deneme toplantısı dışlama, işlev/boyut ağırlıkları, günlük satır (günde bir, metinsiz), eğilim, haftalık kullanıcı puanı sorusu,
# pano cevabı doğrulama, beta özeti süzgeçten sızıntısız geçer. Ağ yok, gerçek veri yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/zeka.py      (kaldı → çıkış 1)
import datetime, json, os, re, shutil, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import zeka, teshis
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
GIZLI = ["Zeynep", "Kartaloğlu", "teklif fiyatı", "Bozkurt"]
def sizinti(x): m = json.dumps(x, ensure_ascii=False).lower(); return [g for g in GIZLI if g.lower() in m]

TZ = datetime.datetime.now().astimezone().tzinfo
SIMDI = datetime.datetime(2026, 11, 12, 10, 0, tzinfo=TZ); S = SIMDI.timestamp()
def iso(gun_once, saat=10, dk=0): return (SIMDI - datetime.timedelta(days=gun_once)).replace(hour=saat, minute=dk).isoformat(timespec="seconds")
def t(gun_once, saat=10, dk=0): return datetime.datetime.fromisoformat(iso(gun_once, saat, dk)).timestamp()
U = tempfile.mkdtemp(prefix="zeka-"); C = os.path.join(U, "canli"); os.makedirs(C)
def yaz(ad, satirlar, kok=C):
    with open(os.path.join(kok, ad), "w", encoding="utf-8") as f: f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in satirlar))
def yazj(ad, v): json.dump(v, open(os.path.join(C, ad), "w", encoding="utf-8"), ensure_ascii=False)

# Konuş: 30 çağrı (3 hatalı), 40 eski (pencere dışı); sorular: 25 farklı + 1 tekrar + 1 düzeltme
yaz("claude-cagri.jsonl", [{"is": "bas-konus", "at": iso(2, 10, i), "hata": "zaman" if i < 3 else None} for i in range(30)]
    + [{"is": "bas-konus", "at": iso(45), "hata": "x"} for _ in range(40)] + [{"is": "toplanti", "etiket": "deneme", "dosya": "2026-11-10-1000-Satis.md", "at": iso(2)}])
kon = [{"at": iso(3, 9, 0) if i == 0 else iso(3, 9 + i // 2, (i % 2) * 30), "soru": f"Zeynep {i} numaralı konu kelime{i} başka{i} şey{i} hakkında ne düşünüyorsun"} for i in range(25)]
kon += [{"at": iso(3, 9, 5), "soru": "Zeynep 0 numaralı konu kelime0 başka0 şey0 hakkında ne düşünüyorsun acaba"},  # 5 dk sonra aynı soru → tekrar
        {"at": iso(3, 21, 1), "soru": "Hayır, teklif fiyatı öyle değil"}]  # öncekinden 1 dk sonra → düzeltme
yaz("konus-gecmis.jsonl", sorted(kon, key=lambda r: r["at"]))
# Kartlar: 18 gerçek (12 yapıldı, 4 geçildi, 2 okundu) + deneme toplantısı (sayılmaz) + uyarı kartları 3 (2 ✓ 1 ✕)
k = []
for i in range(18):
    k.append({"id": f"k{i}", "kind": "cevap", "file": "2026-11-09-1000-Haftalik.md", "at": iso(3), "text": "Zeynep kart metni"})
    k.append({"id": f"k{i}", "status": "yapildi" if i < 12 else "gecildi" if i < 16 else "okundu", "at": iso(3)})
for i in range(10):
    k += [{"id": f"d{i}", "kind": "soyle", "file": "2026-11-10-1000-Satis.md", "at": iso(2)}, {"id": f"d{i}", "status": "gecildi", "at": iso(2)}]  # deneme etiketli
    k += [{"id": f"t{i}", "kind": "soyle", "file": "2026-11-10-test.md", "at": iso(2)}, {"id": f"t{i}", "status": "gecildi", "at": iso(2)}]   # adında test
for i in range(3): k += [{"id": f"u{i}", "kind": "dikkat", "file": "x.md", "at": iso(3)}, {"id": f"u{i}", "status": "yapildi" if i < 2 else "gecildi", "at": iso(3)}]
yaz("kartlar.jsonl", k)
# Söz kapısı: e-posta 10 sunuldu (6 kabul, 1 ret, 3 otomatik yoksay), gün içi 12 sunuldu (3 kabul, 2 ertele, 7 yoksay), 1 iptal
sz = []
for i in range(10):
    sz += [{"olay": "teslim", "id": f"e{i}", "kaynak": "eposta", "t": t(4)}, {"olay": "sonuc", "id": f"e{i}", "kaynak": "eposta", "t": t(4) + 60, "sonuc": "kabul" if i < 6 else "ret" if i == 6 else "yoksay"}]
for i in range(12):
    sz += [{"olay": "sunuldu", "karar": "simdi", "id": f"g{i}", "kaynak": "gun_ici", "t": t(4)}, {"olay": "sonuc", "id": f"g{i}", "kaynak": "gun_ici", "t": t(4) + 60, "sonuc": "kabul" if i < 3 else "ertele" if i < 5 else "yoksay"}]
sz += [{"olay": "sunuldu", "karar": "simdi", "id": "x", "kaynak": "gun_ici", "t": t(4)}, {"olay": "iptal", "id": "x", "kaynak": "gun_ici", "t": t(4)}]
yaz("soz.jsonl", sz)
# E-posta: posta.json + zd — 6 "senden bekleniyor" (4'üne cevap yazılmış, 1'inin son iletisi zaten senin = analiz hatası), 5 "dönüş bekliyorsun" (1'inde son ileti karşıdan = hata)
il = []; zd = {}
for i in range(6):
    il.append({"id": 100 + i, "zincir": str(i), "gonderilen": i == 5, "t": iso(6), "adres": "a@b"})
    if i < 4: il.append({"id": 200 + i, "zincir": str(i), "gonderilen": True, "t": iso(5)})
    zd[f"z:{i}|{100 + i}"] = {"d": "senden_bekleniyor", "a": 1, "n": "Zeynep teklif fiyatı", "t": iso(6, 12)}
for i in range(10, 15):
    il.append({"id": 100 + i, "zincir": str(i), "gonderilen": i != 14, "t": iso(6)})
    zd[f"z:{i}|{100 + i}"] = {"d": "donus_bekliyorsun", "a": 0, "n": "", "t": iso(6, 12)}
yazj("posta.json", {"iletiler": il}); yazj("eposta-takip.json", {"zd": zd, "bildirilen": {f"o{i}": iso(5) for i in range(12)}, "yoksay": {"o1": iso(4)}})
yaz("eposta-tepki.jsonl", [{"t": iso(3), "islem": "yanlis_oncelik", "konu": "Kurgu konu", "beklenen": "dusuk"}, {"t": iso(2), "islem": "yanlis_oncelik", "konu": "Kurgu konu 2", "beklenen": "yuksek"},
                           {"t": iso(2), "islem": "onemli_kisi"}, {"t": iso(60), "islem": "yanlis_oncelik", "konu": "pencere dışı", "beklenen": "dusuk"}])
# Gün planı izleri: 5 gün; s1..s3 odak, s4 dikkat; s4'ün vadesi kayıyor (önceden anıldı), s9'unki geçiyor (anılmadı)
dm = lambda **x: {k: v for k, v in x.items()}
izler = []
for g in range(5, 0, -1):
    gun = (SIMDI - datetime.timedelta(days=g)).date()
    d = {"s1": "kendi|", "s2": "kendi|", "s3": "kendi|", "s4": "kendi|" + (gun + datetime.timedelta(days=1)).isoformat(), "s9": "kendi|" + (SIMDI.date() - datetime.timedelta(days=2)).isoformat()}
    if g <= 3: d.pop("s1")  # s1 2. günden sonra kapandı
    izler.append({"t": t(g, 4), "gun": gun.isoformat(), "durum": "tamam", "odak": ["s1", "s2", "s3"], "dikkat": ["s4"], "damga": d})
izler.append({"t": t(6, 4), "gun": (SIMDI - datetime.timedelta(days=6)).date().isoformat(), "durum": "bozuk"})
yaz("dusunme-iz.jsonl", izler)
yaz("ogrenilen.jsonl", [{"id": f"o{i}", "metin": "Zeynep sabahları odaklanır", "kaynak": "düşünme turu: x", "tarih": iso(4), "durum": "otomatik"} for i in range(6)]
    + [{"id": f"o{i}", "durum": "onayli" if i < 4 else "gecersiz", "tarih": iso(3)} for i in range(5)], kok=U)
yazj("is-kopya.json", {"birlesen": [{"zaman": t(3), "geri": i == 0} for i in range(5)], "ayri": ["a|b"]})
yazj("belge-oneri.json", {"kabul": {f"b{i}": "01M6PE6FC00M4XT1E8NZDZNM54" for i in range(4)}, "red": {"r1": iso(2)}})
yaz("karneler.jsonl", [{"at": iso(3), "dosya": "a.md", "olcu": {"gundem": "0/10"}}, {"at": iso(3, 11), "dosya": "a.md", "olcu": {"gundem": "8/10"}},
                       {"at": iso(2), "dosya": "b.md", "olcu": {"gundem": "2/4"}}, {"at": iso(2), "dosya": "c-test.md", "olcu": {"gundem": "0/20"}},
                       {"at": iso(2), "dosya": "d.md", "olcu": {"gundem": "0/12"}}, {"at": iso(2), "dosya": "e.md", "olcu": {"gundem": "0/5"}},
                       {"at": iso(2), "dosya": "f.md", "olcu": {"gundem": "0/6"}, "gundem_izlendi": True}, {"at": iso(2), "dosya": "g.md", "olcu": {"gundem": "0/3"}, "gundem_izlendi": False}])
open(os.path.join(C, "g.md"), "w", encoding="utf-8").write("| 10:00:00 | **GÜNDEM** | ✗ Açılış | |\n")  # g: satırdaki alan (izlenmedi) dosyadan önce gelir; f: alan "izlendi" (döküm yok) = gerçek sıfır
open(os.path.join(C, "e.md"), "w", encoding="utf-8").write("| 10:00:00 | **GÜNDEM** | ✗ Açılış | |\n")  # e: gündem izlendi, hiçbiri işaretlenmedi = gerçek sıfır; d: döküm/GÜNDEM satırı yok = izlenmedi
# güncellik satırları (yapi.guncellik_karne): 12 önerilen kayıt (3'ü sonra bitti), 10 bayat + 3 sonra_kapandi çıkarımı (2'si sonra yeniden açık), 1 kesin kapanmış (sayılmaz), 1 özet satırı
gs = [{"at": iso(4), "is": "hazirlik", "olay": "x", "id": f"g{i}", "tur": "is", "durum": "acik", "ilgi": .5, "karar": "gundeme_bagla", "neden": []} for i in range(1, 13)]
gs += [{"at": iso(1), "is": "hazirlik", "olay": "y", "id": f"g{i}", "tur": "is", "durum": "bitti", "ilgi": .5, "karar": "gecmis", "neden": ["sonra_kapandi"]} for i in (1, 2, 3)]
gs += [{"at": iso(4), "is": "hazirlik", "olay": "x", "id": f"k{i}", "tur": "is", "durum": "bayat", "ilgi": .1, "karar": "ele", "neden": ["vade_cok_gecti"]} for i in range(1, 11)]
gs += [{"at": iso(1), "is": "hazirlik", "olay": "y", "id": f"k{i}", "tur": "is", "durum": "acik", "ilgi": .1, "karar": "ele", "neden": []} for i in (1, 2)]
gs += [{"at": iso(3), "is": "hazirlik", "olay": "x", "id": "z1", "tur": "is", "durum": "bitti", "ilgi": .1, "karar": "ele", "neden": ["kapandi"]}, {"at": iso(3), "is": "hazirlik", "olay": "x", "ozet": {"bitti": 1}}]
yaz("guncellik.jsonl", gs); yazj("altin-sonuc.json", {"gecen": 15, "toplam": 16, "ornek": 3, "zaman": iso(1)})
yaz("hakem-olcum.jsonl", [{"t": iso(3), "toplanti": "x.md", "kelime": 1000, "wer_sozluk": 0.2}, {"t": iso(2), "toplanti": "y.md", "kelime": 3000, "wer_sozluk": 0.1},
                          {"t": iso(2), "toplanti": "z-test.md", "kelime": 9000, "wer_sozluk": 0.9}])

K = zeka.karne(C, 30, S); O = {f"{o['islev']}.{o['anahtar']}": o for o in K["olcut"]}
ok("konuş: hatasız 27/30 (pencere dışı 40 hatalı sayılmaz)", O["konus.hatasiz"]["n"] == 30 and O["konus.hatasiz"]["puan"] == 90, O["konus.hatasiz"])
ok("konuş: 10 dk içinde benzer soru tekrar sayılır (26/27)", O["konus.tekrarsiz"]["n"] == 27 and O["konus.tekrarsiz"]["oran"] == round(26 / 27, 3), O["konus.tekrarsiz"])
ok("konuş: 'Hayır, …' düzeltme analiz hatası (25/26)", O["konus.duzeltilmeyen"]["n"] == 26 and O["konus.duzeltilmeyen"]["oran"] == round(25 / 26, 3), O["konus.duzeltilmeyen"])
ok("konuş: öngörü ölçütü kaynak yok, puan uydurulmaz", O["konus.ihtiyac"]["durum"] == "kaynak_yok" and K["islev"]["konus"]["boyut"]["ongoru"] is None and K["islev"]["konus"]["kismi"])
ok("kart: deneme toplantısı (etiket ve adında test) dışlanır, okunan sayılmaz → 12/16; 16 < asgari 20 → puan yok", O["toplanti.kart"]["n"] == 16 and O["toplanti.kart"]["oran"] == 0.75 and O["toplanti.kart"]["puan"] is None, O["toplanti.kart"])
ok("uyarı kartı: 3 < asgari 10 → yetersiz veri, puan yok", O["toplanti.uyari"]["durum"] == "yetersiz" and O["toplanti.uyari"]["puan"] is None)
ok("e-posta bildirimi: 6 kabul / 10 (otomatik yoksay olumsuz)", O["eposta.kabul"]["puan"] == 60, O["eposta.kabul"])
ok("e-posta öngörü: 'bekleniyor' denen 6 zincirin 4'üne cevap yazıldı", O["eposta.cevap"]["n"] == 6 and O["eposta.cevap"]["puan"] == 67, O["eposta.cevap"])
ok("e-posta analiz: son ileti zaten senin / karşıdan dönüş gelmiş = 2 hata / 11 (asgari 10)", O["eposta.durum"]["n"] == 11 and O["eposta.durum"]["puan"] == 82, O["eposta.durum"])
ok("e-posta önem: 1/12 kalıcı yoksay", O["eposta.onem"]["n"] == 12 and O["eposta.onem"]["puan"] == 92, O["eposta.onem"])
ok("e-posta kaçırma (yanlış negatif): düşük öncelikli denen 6 zincirin 4'üne sonradan cevap yazıldı → 2/6", O["eposta.kacirma"]["n"] == 6 and O["eposta.kacirma"]["puan"] == 33 and "4'ine" in O["eposta.kacirma"]["kanit"], O["eposta.kacirma"])
ok("e-posta düzeltme: 2 yanlış öncelik + 1 önemli kişi (pencere dışı sayılmaz) / 11 zincir → %73; yalnız sayı", O["eposta.duzeltme"]["n"] == 11 and O["eposta.duzeltme"]["puan"] == 73 and "2 yanlış öncelik" in O["eposta.duzeltme"]["kanit"] and not sizinti(O["eposta.kacirma"]) and not sizinti(O["eposta.duzeltme"]), O["eposta.duzeltme"])
ok("öneri: iptal edilen sunulmuş sayılmaz; 3/12 kabul, 2 ertele", O["proaktif.kabul"]["n"] == 12 and O["proaktif.kabul"]["puan"] == 25 and O["proaktif.zaman"]["n"] == 22, (O["proaktif.kabul"], O["proaktif.zaman"]))
ok("gün planı: tur 5/6 (bozuk tur sayılır)", O["gun_plani.tur"]["n"] == 6 and O["gun_plani.tur"]["puan"] == 83, O["gun_plani.tur"])
ok("gün planı: odak 3 gün içinde kapanan (s1) ölçülür", O["gun_plani.odak"]["n"] >= 6 and 0 < O["gun_plani.odak"]["oran"] < 1, O["gun_plani.odak"])
ok("gün planı öngörü: kayan s4 anıldı, vadesi geçen s9 anılmadı", O["gun_plani.risk"]["kanit"].endswith("önceden plandaydı") and O["gun_plani.risk"]["n"] >= 2 and 0 < O["gun_plani.risk"]["oran"] < 1, O["gun_plani.risk"])
ok("öğrenilen: 4 onaylı / 5 sonuçlanan (hâlâ otomatik olan sayılmaz)", O["gun_plani.ogrenilen"]["n"] == 5 and O["gun_plani.ogrenilen"]["puan"] == 80, O["gun_plani.ogrenilen"])
ok("çift iş: geri alınan ve 'ayrı' denen hata → 4/6", O["kayit.kopya"]["n"] == 6 and O["kayit.kopya"]["puan"] == 67, O["kayit.kopya"])
ok("belge önerisi: tarihsiz kabul değerleri de sayılır → 4/5", O["kayit.belge"]["n"] == 5 and O["kayit.belge"]["puan"] == 80, O["kayit.belge"])
ok("gündem: son karne, deneme dışı; GÜNDEM satırı olmayan 0/12 izlenmemiştir (payda dışı), satırlı 0/5 gerçek sıfırdır; satırdaki gundem_izlendi alanı dosyadan önce gelir (f 0/6 sayılır, g 0/3 payda dışı) → 10/25",
   O["hazirlik.gundem"]["n"] == 25 and O["hazirlik.gundem"]["puan"] == 40 and "2 toplantıda gündem izlenmedi" in O["hazirlik.gundem"]["kanit"], O["hazirlik.gundem"])
ok("bayat öneri: 12 önerilenden 3'ü sonra bitmiş çıktı → bayat çıkmayan 9/12", O["hazirlik.bayat_oneri"]["n"] == 12 and O["hazirlik.bayat_oneri"]["puan"] == 75, O["hazirlik.bayat_oneri"])
ok("kayıt durumu: 13 çıkarım (10 bayat + 3 sonra_kapandi) içinden 2'si sonra açık göründü (kesin 'kapandi' sayılmaz) → 11/13", O["kayit.durum"]["n"] == 13 and O["kayit.durum"]["puan"] == 85, O["kayit.durum"])
ok("altın set: koşu sonucu 15/16 (yalnız sayı dosyası)", O["hazirlik.altin"]["n"] == 16 and O["hazirlik.altin"]["puan"] == 94, O["hazirlik.altin"])
ok("döküm: deneme dışı, kelimeyle ağırlıklı 1 − WER = 0,875", O["dokum.wer"]["oran"] == 0.875 and O["dokum.wer"]["n"] == 2, O["dokum.wer"])
ok("proje bulma: olcum-gecmis verilmezse yetersiz (uydurmaz)", O["hazirlik.bulma"]["puan"] is None)
e = K["islev"]["eposta"]; beklenen = round((e["boyut"]["basari"] * .5 + e["boyut"]["ongoru"] * .25 + e["boyut"]["analiz"] * .25))
ok("işlev puanı: boyut ağırlıkları (0,5/0,25/0,25)", e["puan"] == beklenen and not e["kismi"], e)
ok("işlev puanı: verisi olmayan işlev puansız, genel ortalamaya girmez", K["islev"]["tazi"]["puan"] is None and K["islev_sayi"] == sum(1 for v in K["islev"].values() if v["puan"] is not None))

# Günlük satır: günde bir, yalnız sayı
r1 = zeka.gunluk(C, S); r2 = zeka.gunluk(C, S + 3600)
satir = open(os.path.join(C, zeka.KARNE), encoding="utf-8").read()
ok("günlük: bugünün satırı bir kez yazılır", r1 and r2 is None and satir.count("\n") == 1)
ok("günlük: satırda metin yok (kanıt/ad/soru metni sızmaz)", not sizinti(satir) and "kanit" not in satir and "Hatasız" not in satir, satir[:200])
ok("günlük: dosya 0600", oct(os.stat(os.path.join(C, zeka.KARNE)).st_mode & 0o777) == "0o600")
eski = dict(json.loads(satir)); eski.update(tarih=(SIMDI.date() - datetime.timedelta(days=8)).isoformat(), t=S - 8 * 86400); eski["islev"] = dict(eski["islev"], eposta=dict(eski["islev"]["eposta"], p=50))
open(os.path.join(C, zeka.KARNE), "w", encoding="utf-8").write(json.dumps(eski) + "\n" + satir)
eg = zeka.egilim(C, {a: v["puan"] for a, v in K["islev"].items()}, S, 7)
ok("eğilim: 7 gün önceki kayda göre fark", eg["eposta"] == e["puan"] - 50 and eg["konus"] == 0, eg)

# Kullanıcı puanı sorusu (haftada bir)
ok("soru: karnenin ilk kaydı 8 gün önce, hiç cevap yok → kullanılan işlevler sorulur (en çok 4)", zeka.soru_gerekli(C, S) == ["konus", "gun_plani", "eposta", "toplanti"], zeka.soru_gerekli(C, S))
ok("puan satırı: geçersiz işlev/puan reddedilir", zeka.puan_satiri("tazi", 3) is None and zeka.puan_satiri("konus", 6) is None and zeka.puan_satiri("konus", True) is None and zeka.puan_satiri("konus", "4") is None)
open(os.path.join(C, zeka.PUAN), "a").write(zeka.puan_satiri("konus", 4, simdi=S - 3 * 86400))
ok("soru: 3 gün önce cevaplandı → bu hafta sorulmaz", zeka.soru_gerekli(C, S) == [])
ok("soru: 8 gün sonra yeniden sorulur", zeka.soru_gerekli(C, S + 5 * 86400 + 60) != [])
PY = open(os.path.join(C, zeka.PUAN)).read()
open(os.path.join(C, zeka.PUAN), "w").write(zeka.puan_satiri("konus", 4, simdi=S - 10 * 86400) + zeka.puan_satiri(gec=True, simdi=S - 86400)); a1 = zeka.soru_gerekli(C, S)
open(os.path.join(C, zeka.PUAN), "w").write(zeka.puan_satiri("konus", 4, simdi=S - 10 * 86400) + zeka.puan_satiri(gec=True, simdi=S - 3 * 86400)); a2 = zeka.soru_gerekli(C, S)
open(os.path.join(C, zeka.PUAN), "w").write(PY)
ok("soru: 'Şimdi değil' 2 gün erteler", a1 == [] and a2 != [], (a1, a2))
ok("kullanıcı puanı karneye karışmaz, ayrı döner", zeka.karne(C, 30, S)["kullanici"] == {"konus": {"n": 1, "ort": 4.0}} and zeka.karne(C, 30, S)["islev"]["konus"]["puan"] == K["islev"]["konus"]["puan"])

# Yeni sinyaller: mutabakat, tepki, Kesişim (yalnız sayı, az veride oran yok)
SG0 = zeka.karne(C, 30, S)["sinyal"]
ok("sinyal: veri yokken sıfır ve oran None (puan uydurulmaz)", SG0["mutabakat"]["oneri"] == 0 and SG0["mutabakat"]["onay_orani"] is None and set(SG0["tepki"]) <= {"eposta"} and (SG0["tepki"].get("eposta") or {}).get("iyi") in (None, 0) and SG0["kesisim"]["geri_orani"] is None, SG0)
yaz("mutabakat.jsonl", [{"t": t(2), "olay": "tur", "durum": "tamam", "aday": 8}] + [{"t": t(2), "olay": "oneri", "kayit": f"m{i}", "oneri": "bitti" if i < 4 else "belirsiz", "guven": 0.9 if i < 4 else 0.2} for i in range(8)]
     + [{"t": t(1), "olay": "sonuc", "kayit": f"m{i}", "oneri": "bitti", "sonuc": "onay" if i < 4 else "red"} for i in range(6)] + [{"t": t(40), "olay": "oneri", "kayit": "eski", "oneri": "bitti", "guven": 1.0}])
yaz("tepki.jsonl", [{"zaman": iso(2), "kaynak": "tazi", "id": f"b{i}", "deger": "iyi" if i < 4 else "yanlis"} for i in range(6)] + [{"zaman": iso(2), "kaynak": "kesisim", "id": "k1", "deger": "yanlis"}])
yaz("kesisim-coz.jsonl", [{"t": iso(2), "id": f"c{i}", "karar": "duzelt", "eylem": "tazi_dosya_eklendi", "guven": 0.9} for i in range(5)] + [{"t": iso(2), "id": "a", "karar": "arastir", "eylem": "tazi_kuyrukta"}, {"t": iso(2), "id": "b", "karar": "birak", "eylem": "birakildi"},
     {"t": iso(1), "id": "c0", "karar": "duzelt", "eylem": "geri_alindi"}, {"t": iso(2), "id": "y", "karar": "duzelt", "eylem": "oh_yazilacakti_kapali"}])
SG = zeka.karne(C, 30, S)["sinyal"]; mu, tp, ke = SG["mutabakat"], SG["tepki"], SG["kesisim"]
ok("sinyal mutabakat: 8 öneri (pencere dışı sayılmaz), 6 sonuç → onay %67, red %33, 2 bekleyen, 1 tur", mu["oneri"] == 8 and mu["onay"] == 4 and mu["red"] == 2 and mu["bekleyen"] == 2 and mu["onay_orani"] == 0.667 and mu["red_orani"] == 0.333 and mu["tur"] == 1, mu)
ok("sinyal mutabakat: karar başına ortalama güven", mu["guven"] == {"bitti": {"n": 4, "ort": 0.9}, "belirsiz": {"n": 4, "ort": 0.2}}, mu["guven"])
ok("sinyal tepki: kaynak başına iyi/yanlış; 6 örnekle oran var, 1 örnekle yok", tp["tazi"] == {"iyi": 4, "yanlis": 2, "n": 6, "iyi_orani": 0.667} and tp["kesisim"]["iyi_orani"] is None and tp["kesisim"]["n"] == 1, tp)
ok("sinyal tepki: tazi/kesisim ölçütleri karneye girer (6 ≥ asgari 5 → puan 67; kesisim yetersiz)", {o["anahtar"]: o for o in zeka.karne(C, 30, S)["olcut"] if o["islev"] in ("tazi", "kesisim")}["bulgu"]["puan"] == 67 and {o["anahtar"]: o for o in zeka.karne(C, 30, S)["olcut"] if o["islev"] == "kesisim"}["celiski"]["durum"] == "yetersiz")
gk = list(ke["gunler"].values())[0] if len(ke["gunler"]) == 1 else None
ok("sinyal kesişim: düzeltilen 5 (kapalı yazma sayılmaz), araştırılan 1, bırakılan 1, geri alınan 1 → geri oranı %20", ke["duzeltilen"] == 5 and ke["geri_alinan"] == 1 and ke["geri_orani"] == 0.2 and sum(v["araştırılan".replace("ş", "s").replace("ı", "i")] for v in ke["gunler"].values()) == 1 and sum(v["birakilan"] for v in ke["gunler"].values()) == 1, ke)
ok("sinyal: karne özet satırına metinsiz girer", zeka.ozet_satir(zeka.karne(C, 30, S), S)["sinyal"]["mutabakat"]["onay"] == 4 and not sizinti(SG))
for _a in ("mutabakat.jsonl", "tepki.jsonl", "kesisim-coz.jsonl"): os.remove(os.path.join(C, _a))
# Altın set gece turuna bağlı: dus_altin_kos günde bir, sahte kod klasöründe test/zeka-altin.py + testler/altin varsa koşar
AK = tempfile.mkdtemp(prefix="zeka-altin-kod-"); os.makedirs(os.path.join(AK, "test")); os.makedirs(os.path.join(AK, "testler", "altin")); AC = os.path.join(AK, "canli"); os.makedirs(AC)
shutil.copy(os.path.join(KOD, "zeka.py"), AK); open(os.path.join(AK, "test", "zeka-altin.py"), "w").write("import sys, json, os\nd = sys.argv[sys.argv.index('--kaydet') + 1]\njson.dump({'gecen': 3, 'toplam': 4, 'zaman': '2026-11-12T03:00:00'}, open(os.path.join(d, 'altin-sonuc.json'), 'w'))\n")
_ak = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": {"kod": AK}, "BASE": AC, "LOCK": threading.Lock(), "write": lambda pairs: [open(y, "a").write(m) for y, m in pairs],
       "gizli_acik": lambda: False, "_t": lambda tr, en: tr, "print": lambda *a, **k: None}
exec(compile(open(os.path.join(KOD, "aktarici", "dusunme.py"), encoding="utf-8").read(), "dusunme.py", "exec"), _ak)
_r1 = _ak["dus_altin_kos"](); _r2 = _ak["dus_altin_kos"]()
ok("altın set: günde bir koşar, sonucu canli/altin-sonuc.json'a yazar", _r1 == 0 and _r2 is None and json.load(open(os.path.join(AC, "altin-sonuc.json")))["gecen"] == 3, (_r1, _r2))
_ak["DUS"]["altin_gun"] = ""; os.remove(os.path.join(AC, "altin-sonuc.json")); _ak["gizli_acik"] = lambda: True
ok("altın set: gizli kipte koşmaz", _ak["dus_altin_kos"]() is None and not os.path.exists(os.path.join(AC, "altin-sonuc.json")))
_ak["gizli_acik"] = lambda: False; _ak["DUS"]["altin_gun"] = ""; _ak["AYAR"]["kod"] = os.path.join(AK, "yok")
_pr = []; _ak["print"] = lambda *x, **k: _pr.append(" ".join(map(str, x)))
ok("altın set: atlanınca günlüğe 'ALTIN: atlandı (neden)' + altin-atla.jsonl", _ak["dus_altin_kos"]() is None and any(l.startswith("ALTIN: atlandı (") for l in _pr) and json.loads(open(os.path.join(AC, "altin-atla.jsonl")).readline())["altin"] is None)
_nk = zeka.karne(AC, 30); _ol = [o for o in _nk["olcut"] if o["anahtar"] == "altin"][0]
ok("altın set: atlanan koşu karneye altin: null + neden", "atlandı:" in _ol["kanit"] and zeka.ozet_satir(_nk)["altin"]["altin"] is None and zeka.ozet_satir(_nk)["altin"]["neden"], _ol)
# kurulum kopyası önce denenir (<uygulama>/altin/), kod klasörü gerekmez
os.makedirs(os.path.join(AK, "altin", "ornek")); shutil.copy(os.path.join(AK, "test", "zeka-altin.py"), os.path.join(AK, "altin", "zeka-altin.py")); shutil.rmtree(os.path.join(AK, "test")); _ak["DUS"]["altin_gun"] = ""
ok("altın set: <uygulama>/altin/ kopyasından koşar (kod klasörü yokken de)", _ak["dus_altin_kos"]() == 0 and os.path.isfile(os.path.join(AC, "altin-sonuc.json")))
os.remove(os.path.join(AC, "altin-sonuc.json")); shutil.rmtree(os.path.join(AK, "altin")); os.makedirs(os.path.join(AK, "test")); open(os.path.join(AK, "test", "zeka-altin.py"), "w").write("import sys, json, os\nd = sys.argv[sys.argv.index('--kaydet') + 1]\njson.dump({'gecen': 3, 'toplam': 4, 'zaman': 'x'}, open(os.path.join(d, 'altin-sonuc.json'), 'w'))\n")
# kurulum.altin_kopyala: yalnız geliştiricide kopyalar, beta'da eski kopyayı siler
import importlib.util as _iu
_sp = _iu.spec_from_file_location("kurulum_t", os.path.join(KOD, "kurulum.py")); _kz = _iu.module_from_spec(_sp); _sp.loader.exec_module(_kz)
_kk = tempfile.mkdtemp(prefix="altin-kur-"); _ap = tempfile.mkdtemp(prefix="altin-app-")
os.makedirs(os.path.join(_kk, "test")); os.makedirs(os.path.join(_kk, "testler", "altin")); open(os.path.join(_kk, "test", "zeka-altin.py"), "w").write("#"); open(os.path.join(_kk, "testler", "altin", "01.json"), "w").write("{}")
_kz.KOD = _kk; _kz._gelistirici = lambda: True
ok("kurulum: geliştiricide altın set <uygulama>/altin/ altına kopyalanır", _kz.altin_kopyala(_ap) is True and os.path.isfile(os.path.join(_ap, "altin", "zeka-altin.py")) and os.path.isfile(os.path.join(_ap, "altin", "ornek", "01.json")))
_kz._gelistirici = lambda: False
ok("kurulum: beta'da altın kopyası yok, eski kopya silinir", _kz.altin_kopyala(_ap) is False and not os.path.exists(os.path.join(_ap, "altin")))
_ak["print"] = lambda *a, **k: None; _ak["DUS"]["altin_gun"] = ""
ok("kurulum: altin/ ve testler/ KOPYA listesinde değil (beta paketine girmez)", "altin" not in " ".join(_kz.KOPYA) and "testler" not in " ".join(_kz.KOPYA))
_ak["AYAR"]["kod"] = os.path.join(AK, "yok")
_ak["AYAR"]["kod"] = AK; _ak["DUS"]["altin_gun"] = ""; _ak["DUS"]["zeka_gun"] = ""; _ak["dus_zeka_gunluk"]()
ok("altın set: günlük karne öncesi koşar (karne satırı altın sonucunu okur)", os.path.isfile(os.path.join(AC, "altin-sonuc.json")) and json.loads(open(os.path.join(AC, "zeka-karne.jsonl")).readline())["olcut"]["hazirlik.altin"][1] == 4)

# Beta özeti + teshis süzgeci
bo = zeka.beta_ozet(C, S - 7 * 86400, S + 86400); tz = teshis.temizle({"zeka": bo})["zeka"]
ok("beta: işlev puanı ve kullanıcı puanı süzgeçten geçer", tz["zeka_karne"]["eposta"]["puan"] == e["puan"] and tz["zeka_kullanici"]["konus"]["ort"] == 4.0 and tz["zeka_gec"] == 0, tz)
ok("beta: bilinmeyen işlev anahtarı '?n' olur, metin yok", "?1" in teshis.temizle({"zeka_karne": {"Zeynep Bozkurt": {"puan": 3}}})["zeka_karne"] and not sizinti(tz))

# dusunme.py: tur izi, günlük tetik, /dusunme zeka_puan/zeka_gec, dus_view zeka_soru (yalıtılmış ad alanı)
D = os.path.join(tempfile.mkdtemp(prefix="zeka-dus-"), "canli"); os.makedirs(D)
def write(pairs):
    for yol, metin in pairs:
        with open(yol, "a", encoding="utf-8") as f: f.write(metin)
ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": {"kod": KOD}, "BASE": D, "LOCK": threading.Lock(), "write": write,
      "gizli_acik": lambda: False, "_t": lambda tr, en: tr, "print": lambda *a, **k: None}
exec(compile(open(os.path.join(KOD, "aktarici", "dusunme.py"), encoding="utf-8").read(), "dusunme.py", "exec"), ns)
ok("dusunme: zeka.py kod klasöründen yüklenir", ns["_ZEKA"] is not None)
ns["_dus_iz"]("2026-11-12", "tamam", {"odak": [{"id": "s1", "metin": "Zeynep"}], "dikkat": [{"metin": "kimliksiz"}], "damga": {"s1": "kendi|2026-11-13"}})
iz = open(os.path.join(D, "dusunme-iz.jsonl"), encoding="utf-8").read()
ok("dusunme: tur izi metinsiz (yalnız kimlik + damga)", json.loads(iz)["odak"] == ["s1"] and json.loads(iz)["dikkat"] == [] and not sizinti(iz), iz)
ok("dusunme: günlük karne günde bir", ns["dus_zeka_gunluk"]() is not None and ns["dus_zeka_gunluk"]() is None and os.path.isfile(os.path.join(D, "zeka-karne.jsonl")))
ok("dusunme: /dusunme zeka_puan yazar, geçersizi reddeder", ns["dus_islem"]({"islem": "zeka_puan", "islev": "konus", "puan": 5})["ok"] and not ns["dus_islem"]({"islem": "zeka_puan", "islev": "konus", "puan": 9})["ok"]
   and not ns["dus_islem"]({"islem": "zeka_puan", "islev": "Zeynep", "puan": 3})["ok"])
ok("dusunme: zeka_gec yazar", ns["dus_islem"]({"islem": "zeka_gec"})["ok"] and '"gec": true' in open(os.path.join(D, "zeka-puan.jsonl")).read())
ns["DUS"]["zeka_soru"] = (time.time(), ["konus", "eposta"])
ok("dusunme: plan yokken dus_view yalnız zeka_soru taşır", ns["dus_view"]() == {"zeka_soru": ["konus", "eposta"]}, ns["dus_view"]())
ns["gizli_acik"] = lambda: True
ok("dusunme: gizli kipte soru da karne de yok", ns["dus_view"]() is None and ns["dus_zeka_soru"]() == [])

# Kaynak denetimi: kurulum KOPYA, teshis KOD_DOSYALARI, pano/dil
src = lambda p: open(os.path.join(KOD, p), encoding="utf-8").read()
ok("kurulum.py KOPYA ve teshis.py KOD_DOSYALARI zeka.py içerir", '"zeka.py"' in src("kurulum.py").split("KOPYA = [", 1)[1].split("]", 1)[0] and "zeka.py" in teshis.KOD_DOSYALARI)
ok("beta-veri.py haftalık pakette 'zeka' alanı", '"zeka": _beta_zeka(bas, son)' in src("aktarici/beta-veri.py"))
ok("pano: zkpuan/zkgec düğmeleri /dusunme'ye gider; metinlerin İngilizcesi dil.js'de", "islem:'zeka_puan'" in src("pano/pano.html") and "{a} bu hafta ne kadar akıllıydı?" in src("pano/dil.js") and '"Şimdi değil"' in src("pano/dil.js"))
# toplanti-claude.py karne_satiri_yaz (12 Kasım): karneler.jsonl'e metinsiz satır + gundem_izlendi; gündemsiz ve gizli toplantıda yazılmaz
import types as _ty
_tc = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read(); _kd = tempfile.mkdtemp(prefix="karne-satir-")
_ns = {"os": os, "json": json, "datetime": datetime, "A": _ty.SimpleNamespace(dir=_kd), "_yapi": lambda: _ty.SimpleNamespace(gizli_mi=lambda d, f: f == "gizli.md")}
exec(_tc[_tc.index("def karne_satiri_yaz(v):"):_tc.index("def sonuc_cmd():")], _ns)
_ns["karne_satiri_yaz"]({"dosya": "x.md", "olcu": {"gundem": "3/5"}, "gundem_izlendi": True, "baslik": "GİZLİ-BAŞLIK"}); _ns["karne_satiri_yaz"]({"dosya": "y.md", "olcu": {}, "gundem_izlendi": False})
_ns["karne_satiri_yaz"]({"dosya": "gizli.md", "olcu": {"gundem": "1/2"}, "gundem_izlendi": True})
_kl = [json.loads(l) for l in open(os.path.join(_kd, "karneler.jsonl"), encoding="utf-8")]
ok("karne_satiri_yaz: yalnız gündemli ve gizli olmayan toplantı; dosya, gündem x/y, gundem_izlendi; başlık/metin yok", len(_kl) == 1 and _kl[0]["dosya"] == "x.md" and _kl[0]["olcu"] == {"gundem": "3/5"} and _kl[0]["gundem_izlendi"] is True and "BAŞLIK" not in json.dumps(_kl, ensure_ascii=False), _kl)
ok("toplanti-claude.py: sonuc karne_hesap'tan hemen sonra karne satırını yazar; karne_hesap gundem_izlendi'yi işaretlerden çıkarır", "v = karne_hesap(md); sf = v[\"suflor\"]; o = v[\"olcu\"]\n    karne_satiri_yaz(v)" in _tc and '"gundem_izlendi": bool(ticks)' in _tc)
print("\n" + ("hepsi geçti" if not HATA else f"{len(HATA)} kaldı")); sys.exit(1 if HATA else 0)
