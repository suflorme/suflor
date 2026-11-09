#!/usr/bin/env python3
# İş kopyası (aktarici/is-kopya.py; 10 Kasım): aynı iş farklı toplantılarda yeniden konuşulunca tek kayıt. Birim: bölüm yalıtılmış ad alanında (degerlendir.py + is-kopya.py), yalıtılmış geçici klasörde yapi grafı,
# sahte model (gerçek claude çağrılmaz, ağ yok). Kurgu veri. Sınananlar: (a) aynı iş → otomatik birleşir (eski iptal + not, yeniye yorum, metin önerisi, vade taşıma); (b) hazırlık ≠ gönderim → ayrı kaydı,
# yeniden sorulmaz; (c) emin_değil/düşük güven → bekleyen soru, birleştir/ayrı işlemleri; (d) model başarısız → soruya düşer, hiçbir şey kapanmaz, geçici engelde çift taranmamış kalır; (e) gizli toplantı,
# farklı sahip, aynı toplantı içi aday olmaz; (f) geri al; (g) imleç (aynı kayıt yeniden taranmaz); ayrıca ayar/gizli kip/uç görünümü.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/is-kopya.py      (kaldı → çıkış 1)
import datetime, hashlib, inspect, json, os, re, shutil, stat, sys, tempfile, threading, time
sys.dont_write_bytecode = True; os.environ["SUFLOR_IK_DONGU_YOK"] = "1"
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="is-kopya-"); AY = os.path.join(T, "ayar.json"); json.dump({"ad": "Ece Deneme"}, open(AY, "w")); os.environ["SUFLOR_AYAR"] = AY
import yapi
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
SAAT = {"t": datetime.datetime(2026, 11, 11, 11, 0).timestamp()}
class Model:
    def __init__(s): s.cevaplar, s.istemler = [], []
    def cagri(s, istem, amac=None, soru=None, maske=None, is_adi=None, model=None):
        s.istemler.append(istem); c = s.cevaplar.pop(0) if s.cevaplar else None
        if callable(c): c = c(istem)
        return (None, "yanıt gelmedi") if c is None else (c if isinstance(c, str) else json.dumps(c, ensure_ascii=False), None)
def ns_kur(ad):
    C = os.path.join(T, ad); os.makedirs(C); m = Model(); durum = {"gizli": False}; log = []
    def write(pairs):
        for yol, metin in pairs:
            with open(yol, "a", encoding="utf-8") as f: f.write(metin)
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": {"ad": "Ece Deneme"}, "BASE": C, "LOCK": threading.Lock(), "write": write,
          "gizli_acik": lambda: durum["gizli"], "_yapi_mod": lambda: yapi, "eylem_model": m.cagri, "print": lambda *a, **k: log.append(" ".join(str(x) for x in a)),
          "DG_SAAT": lambda: SAAT["t"], "M": m, "C": C, "DURUM": durum, "LOG": log}
    for f in ("degerlendir.py", "is-kopya.py"): exec(compile(open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read(), f, "exec"), ns)
    return ns
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def toplanti(C, ad, gizli=False):
    open(os.path.join(C, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n" + BAS + "| 10:00:00 | Ece Deneme | merhaba | |\n" + ("| 12:00:05 | **GİZLİ** | açıldı | |\n" if gizli else ""))
def graf(C, top, tarih, baslik, isler):  # isler: [(metin, sahip, vade)]
    toplanti(C, top, gizli=top.endswith("Gizli")) if not os.path.exists(os.path.join(C, top + ".md")) else None
    yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": [dict({"tur": "is", "metin": m, "sahip": s}, **({"tarih": v} if v else {})) for m, s, v in isler]}]}, top + ".md")
def liste(C): return {x["metin"]: x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["tur"] == "is"}
def bul(C, parca): return next(x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["tur"] == "is" and parca in x["metin"])
def cev(*ogeler): return [dict(zip(("id", "karar", "oncelik", "neden", "metin"), o)) for o in ogeler]
def ilerle(N, sn=700): SAAT["t"] += sn  # tur sınırı (60 sn) ve hata bekleme (10 dk) sahte saatle geçilir

# --- (a) 1Password örneği: aynı iş → otomatik birleşir ---
N = ns_kur("a"); C = N["C"]
T1, T2 = "2026-10-29-1000-Proje", "2026-11-05-1000-Proje"
graf(C, T1, "2026-10-29", "Haftalık proje", [("1Password Business araştırmasını Kerem'le paylaşacak", "Deniz", "2026-11-01"), ("Kurulum rehberini çevir", "Deniz", None)])
graf(C, T2, "2026-11-05", "Proje değerlendirme", [("1Password Business araştırması", "Deniz", None), ("Bütçe tablosunu güncelle", "Selin", None)])
e0, y0 = bul(C, "paylaşacak"), bul(C, "araştırması")
ik = N["ik_adaylar"](yapi, N["ik_acik_isler"](yapi), N["ik_oku"]())
ok("aday: aynı sahip, farklı toplantı, kök örtüşmesi; yeni = sonraki toplantı, eski = öncekisi; başka sahip ve ilgisiz iş aday değil", [(c[0]["id"], c[1]["id"]) for c in ik[0]] == [(y0["id"], e0["id"])] and len(ik[1]) == 4, ik)
N["M"].cevaplar = [cev((f"{y0['id']}|{e0['id']}", "ayni", 3, "Aynı araştırma, aynı kişi", "1Password Business araştırmasını Kerem'le paylaşacak"))]
r = N["ik_tur"]()
ok("tur: bir çift değerlendirildi, birleşti", r.get("ok") and r["cift"] == 1 and r["birlesti"] == 1 and r["soru"] == 0, r)
ist = N["M"].istemler[0]
ok("istem: iki işin tarihi ve toplantı başlığı, güven ölçeği, <veri> sarmalı", "YENİ (2026-11-05, Proje değerlendirme)" in ist and "ESKİ (2026-10-29, Haftalık proje)" in ist and "GÜVEN" in ist and "ayni|farkli|emin_degil" in ist and "<veri>" in ist, ist[-700:])
L = liste(C); e1, y1 = [x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["id"] == e0["id"]][0], [x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["id"] == y0["id"]][0]
ok("eski kayıt kapandı (iptal), yeni açık", e1["durum"] == "kapandi" and y1["durum"] == "acik", (e1["durum"], y1["durum"]))
th_e = [o for o in yapi.tarihce(C, e0["id"])]; th_y = yapi.tarihce(C, y0["id"])
ok("eski kayıtta not: aynı iş — yeni tarih ve kimlik", any(o["tur"] == "durum_degisti" and o["veri"].get("durum") == "iptal" and f"5 Kasım".lower() not in "" and "2026-11-05" in o["veri"].get("not", "") and y0["id"] in o["veri"].get("not", "") for o in th_e), [o["veri"] for o in th_e])
ok("yeni kayıtta yorum: eski toplantı ve kimlik", any(o["tur"] == "yorum_eklendi" and "2026-10-29 Haftalık proje toplantısındaki aynı iş" in o["veri"]["metin"] and e0["id"] in o["veri"]["metin"] for o in th_y), [o["veri"] for o in th_y])
ok("model metni önerdi: yeni kayda uygulandı", y1["metin"] == "1Password Business araştırmasını Kerem'le paylaşacak", y1["metin"])
ok("yenide vade yoktu: eskinin vadesi taşındı", y1["vade"] == "2026-11-01", y1["vade"])
ok("günlük satırı: İŞ KOPYA … birleşti, iş metni yok", any("İŞ KOPYA" in l and "birleşti" in l and "1Password" not in l for l in N["LOG"]), N["LOG"])
d = N["ik_oku"]()
ok("durum dosyası 0600; birleşen kaydı; sayaç; taranan iki kayıt", stat.S_IMODE(os.stat(os.path.join(C, "is-kopya.json")).st_mode) == 0o600 and len(d["birlesen"]) == 1 and d["sayac"]["otomatik"] == 1 and len(d["taranan"]) >= 2, d["sayac"])
st = N["ik_status"]()
ok("/status is_kopya: taranan, bekleyen, son tur, otomatik", st["acik"] and st["taranan"] >= 4 and st["bekleyen"] == 0 and st["otomatik"] == 1 and st["son_s"] is not None, st)
v = N["ik_view"]()
ok("görünüm: son 24 saatin otomatik birleştirmesi (geri alınabilir), soru yok", v["ok"] and len(v["birlesen"]) == 1 and v["birlesen"][0]["cift"] == f"{y0['id']}|{e0['id']}" and v["birlesen"][0]["otomatik"] and not v["sorular"], v)
# --- (g) imleç: ikinci turda aynı kayıt yeniden taranmaz ---
n_ist = len(N["M"].istemler); r2 = N["ik_tur"]()
ok("imleç: ikinci tur model çağırmaz, çift yok", r2.get("ok") and r2["cift"] == 0 and len(N["M"].istemler) == n_ist, r2)
# --- (f) geri al ---
g = N["ik_islem"]({"islem": "geri_al", "cift": v["birlesen"][0]["cift"]})
y2 = bul(C, "araştırması"); e2 = [x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["id"] == e0["id"]][0]
ok("geri al: eski yeniden açık, yeninin metni ve vadesi önceki gibi", g.get("ok") and g["geri_alinan"] >= 2 and e2["durum"] == "acik" and y2["metin"] == "1Password Business araştırması" and not y2["vade"], (g, e2["durum"], y2["metin"], y2["vade"]))
d = N["ik_oku"](); v = N["ik_view"]()
ok("geri alınan birleştirme listeden düşer, çift 'ayrı' olur; ikinci geri al yok", d["birlesen"][0]["geri"] and len(d["ayri"]) == 1 and not v["birlesen"] and not N["ik_islem"]({"islem": "geri_al", "cift": g and f"{y0['id']}|{e0['id']}"}).get("ok"), d["ayri"])
ik = N["ik_adaylar"](yapi, N["ik_acik_isler"](yapi), dict(N["ik_oku"](), taranan=[]))
ok("ayrı denen çift taranmış listesi boşalsa da yeniden aday olmaz", not any({c[0]["id"], c[1]["id"]} == {y0["id"], e0["id"]} for c in ik[0]), ik[0])
sonuc_kayit = [json.loads(l) for l in open(os.path.join(C, "degerlendir.jsonl"), encoding="utf-8")]
ok("ölçüm kaydı: karar ve kullanıcı sonucu (geri al = ret), iş metni yok", any(r.get("olay") == "karar" and r.get("is") == "is_kopya" and r.get("karar") == "ayni" for r in sonuc_kayit) and any(r.get("olay") == "sonuc" and r.get("is") == "is_kopya" and r.get("sonuc") == "ret" for r in sonuc_kayit)
   and "1Password" not in open(os.path.join(C, "degerlendir.jsonl"), encoding="utf-8").read(), sonuc_kayit[-2:])

# --- (b) taslak hazırla ≠ taslağı gönder → farkli → ayrı kaydı, yeniden sorulmaz ---
N = ns_kur("b"); C = N["C"]
graf(C, "2026-11-03-1000-Satis", "2026-11-03", "Satış", [("Sunum taslağını hazırla", "Selin", None)])
graf(C, "2026-11-10-1000-Satis", "2026-11-10", "Satış", [("Sunum taslağını gönder", "Selin", None)])
sa, sb = bul(C, "hazırla"), bul(C, "gönder")
N["M"].cevaplar = [cev((f"{sb['id']}|{sa['id']}", "farkli", 3, "Hazırlık ile gönderim ayrı iş"))]
r = N["ik_tur"]()
d = N["ik_oku"]()
ok("farkli: çift ayrı kaydında, ikisi de açık, soru yok", r["ayri"] == 1 and len(d["ayri"]) == 1 and not d["sorular"] and bul(C, "hazırla")["durum"] == "acik" and bul(C, "gönder")["durum"] == "acik", (r, d["ayri"]))
n_ist = len(N["M"].istemler); N["ik_yaz"](dict(d, taranan=[])); r = N["ik_tur"]()
ok("taranan listesi silinse de ayrı çift yeniden sorulmaz (model çağrılmaz)", r["cift"] == 0 and len(N["M"].istemler) == n_ist and not N["ik_oku"]()["sorular"], r)

# --- (c) emin_degil ve düşük güven → bekleyen soru; birlestir / ayri ---
N = ns_kur("c"); C = N["C"]
graf(C, "2026-11-03-1000-Ekip", "2026-11-03", "Ekip", [("Müşteri teklifini revize et", "Doruk", "2026-11-14"), ("Tedarikçi sözleşmesini incele", "Doruk", None), ("Erişim listesini doğrula", "Doruk", None)])
graf(C, "2026-11-10-1000-Ekip", "2026-11-10", "Ekip", [("Müşteri teklifini revize et ve gönder", "Doruk", None), ("Tedarikçi sözleşmesini gözden geçir", "Doruk", None), ("Erişim listesini kontrol et", "Doruk", None)])
yeni = {k: bul(C, k) for k in ("revize et ve", "gözden geçir", "kontrol et")}; eski = {k: bul(C, k) for k in ("revize et", "incele", "doğrula")}
eski["revize et"] = next(x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["metin"] == "Müşteri teklifini revize et")
def cid(yk, ek): return f"{yeni[yk]['id']}|{eski[ek]['id']}"
N["M"].cevaplar = [cev((cid("revize et ve", "revize et"), "emin_degil", 1, "Biri öbürünün alt adımı olabilir"), (cid("gözden geçir", "incele"), "ayni", 1, "Olası aynı, güven düşük", "Tedarikçi sözleşmesini gözden geçir"),
                       (cid("kontrol et", "doğrula"), "emin_degil", 0, "Belirsiz"))]
r = N["ik_tur"](); v = N["ik_view"](); d = N["ik_oku"]()
ok("emin_değil ve düşük güvenli 'aynı' → üç bekleyen soru, hiçbir kayıt kapanmadı", r["soru"] == 3 and r["birlesti"] == 0 and len(v["sorular"]) == 3 and all(x["durum"] == "acik" for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["tur"] == "is"), (r, v["sorular"]))
s0 = next(x for x in v["sorular"] if x["cift"] == cid("revize et ve", "revize et"))
ok("soru: iki işin metni, vadesi, tarihi, toplantısı; neden", s0["yeni"]["metin"].endswith("ve gönder") and s0["eski"]["vade"] == "2026-11-14" and s0["eski"]["baslik"] == "Ekip" and s0["eski"]["tarih"] == "2026-11-03" and s0["neden"], s0)
b = N["ik_islem"]({"islem": "birlestir", "cift": cid("revize et ve", "revize et")}); ye = bul(C, "revize et ve"); ee = next(x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["id"] == eski["revize et"]["id"])
ok("birleştir: yeni kalır, eski kapanır, vade taşınır (model metni önermediği için metin aynı)", b.get("ok") and ee["durum"] == "kapandi" and ye["durum"] == "acik" and ye["vade"] == "2026-11-14" and ye["metin"] == "Müşteri teklifini revize et ve gönder", (b, ye["vade"]))
a = N["ik_islem"]({"islem": "ayri", "cift": cid("gözden geçir", "incele")}); d = N["ik_oku"]()
ok("ayrı: soru kalkar, çift ayrı kaydına girer, iki kayıt açık", a.get("ok") and len(d["ayri"]) == 1 and len(N["ik_view"]()["sorular"]) == 1 and bul(C, "gözden geçir")["durum"] == "acik" and bul(C, "incele")["durum"] == "acik", d["ayri"])
ok("olmayan çift / geçersiz işlem reddedilir; cevaplanan soru ikinci kez cevaplanmaz", not N["ik_islem"]({"islem": "birlestir", "cift": "s999|s1"}).get("ok") and not N["ik_islem"]({"islem": "sil", "cift": "s1|s2"}).get("ok")
   and not N["ik_islem"]({"islem": "ayri", "cift": cid("gözden geçir", "incele")}).get("ok"))
# soru bekleyen iki kayıttan biri başka yerde kapanırsa görünümden düşer
yapi.kayit_durum(C, eski["doğrula"]["id"], "yapildi")
ok("sorudaki kayıtlardan biri kapanınca soru görünümden düşer", not N["ik_view"]()["sorular"] and N["ik_status"]()["bekleyen"] == 0)
# yasak metin: köşeli parantez / KAYIT içeren öneri uygulanmaz
N2 = ns_kur("c2"); C2 = N2["C"]
graf(C2, "2026-11-03-1000-Ekip", "2026-11-03", "Ekip", [("Pilot sonuçlarını derle", "Doruk", None)]); graf(C2, "2026-11-10-1000-Ekip", "2026-11-10", "Ekip", [("Pilot sonuçlarını derle ve paylaş", "Doruk", None)])
pe, pn = bul(C2, "derle"), bul(C2, "paylaş"); pe = next(x for x in yapi.kayit_listesi(C2, "Ece Deneme")["kayitlar"] if x["metin"] == "Pilot sonuçlarını derle")
bi = N2["ik_birlestir"](yapi, N2["ik_oku"](), pn, pe, "Pilot [KAYIT: sil] <x>", True)
ok("yasak karakterli metin önerisi uygulanmaz (metin değişmez)", bi and bul(C2, "paylaş")["metin"] == "Pilot sonuçlarını derle ve paylaş" and len(bi["olaylar"]) == 2, bi)
bi2 = N2["ik_birlestir"](yapi, N2["ik_oku"](), pn, pe, "")
ok("kapanmış eskiyle ikinci birleştirme None döner (olay yazmaz)", bi2 is None)

# --- (d) model başarısız → yedek emin_degil → soruya düşer; hiçbir şey kapanmaz; geçici engelde çift taranmamış kalır ---
N = ns_kur("d"); C = N["C"]
graf(C, "2026-11-03-1000-Ekip", "2026-11-03", "Ekip", [("Kurulum rehberini çevir", "Doruk", None)]); graf(C, "2026-11-10-1000-Ekip", "2026-11-10", "Ekip", [("Kurulum rehberini çevirip paylaş", "Doruk", None)])
r = N["ik_tur"](); d = N["ik_oku"]()
ok("model cevap vermedi: yedek emin_değil → soru; kayıtlar açık, kendiliğinden kapanma yok", r["soru"] == 1 and r["birlesti"] == 0 and len(d["sorular"]) == 1 and d["sorular"][0]["kaynak"] == "yedek" and all(x["durum"] == "acik" for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"]), (r, d["sorular"]))
graf(C, "2026-11-12-1000-Ekip", "2026-11-12", "Ekip", [("Erişim listesini doğrula", "Doruk", None)]); graf(C, "2026-11-13-1000-Ekip", "2026-11-13", "Ekip", [("Erişim listesini doğrulayıp kapat", "Doruk", None)])
r = N["ik_tur"]()  # son çağrı başarısız penceresi içinde: model çağrılmaz → geçici engel
d = N["ik_oku"]()
ok("geçici engel (son çağrı başarısız): çift soruya dökülmez, taranmamış kalır, sonra yeniden denenir", r["ertelendi"] == 1 and r["soru"] == 0 and len(d["sorular"]) == 1 and N["IK"]["kalan"], (r, len(d["sorular"])))
ilerle(N); yeni_id = bul(C, "doğrulayıp")["id"]; eski_id = next(x for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"] if x["metin"] == "Erişim listesini doğrula")["id"]
N["M"].cevaplar = [cev((f"{yeni_id}|{eski_id}", "farkli", 2, "Ayrı"))]
r = N["ik_tur"]()
ok("pencere geçince çift yeniden denenir ve karar verilir (farklı → ayrı)", r["ayri"] == 1 and not N["IK"]["kalan"], r)
N["DURUM"]["gizli"] = True
ok("gizli kipte tur yok", N["ik_tur"]() == {"ok": False, "neden": "gizli"})
N["DURUM"]["gizli"] = False; N["AYAR"]["is_kopya"] = False
ok("ayar is_kopya=false: tur yok", N["ik_tur"]() == {"ok": False, "neden": "kapali"} and not N["ik_status"]()["acik"])
N["AYAR"]["is_kopya"] = True; N["AYAR"]["degerlendir"] = False
ok("değerlendirici kapalıysa tur yok (model yokken kendiliğinden bir şey yapılmaz)", N["ik_tur"]() == {"ok": False, "neden": "degerlendirici"})

# --- (e) gizli toplantı, farklı sahip, aynı toplantı içi aday olmaz ---
N = ns_kur("e"); C = N["C"]
graf(C, "2026-11-03-1000-Gizli", "2026-11-03", "Gizli", [("Lisans yenilemesini kontrol et", "Doruk", None)])
graf(C, "2026-11-10-1000-Ekip", "2026-11-10", "Ekip", [("Lisans yenilemesini kontrol et ve bildir", "Doruk", None), ("Bütçe raporunu hazırla", "Selin", None), ("Bütçe raporunu gözden geçir", "Selin", None)])
graf(C, "2026-11-04-1000-Ekip", "2026-11-04", "Ekip", [("Bütçe raporunu hazırla ve gönder", "Doruk", None)])
isler = N["ik_acik_isler"](yapi); ciftler = N["ik_adaylar"](yapi, isler, N["ik_oku"]())[0]
metinler = {frozenset((c[0]["metin"], c[1]["metin"])) for c in ciftler}
ok("gizli toplantının işi listede ve aday değil", "Lisans yenilemesini kontrol et" not in {x["metin"] for x in isler} and all("Lisans" not in m for c in metinler for m in c), (len(isler), metinler))
ok("farklı sahip aday olmaz (Selin ↔ Doruk)", not any("hazırla ve gönder" in m for c in metinler for m in c), metinler)
ok("aynı toplantı içi aday olmaz (Selin'in iki işi aynı toplantıda)", not any(set(c) == {"Bütçe raporunu hazırla", "Bütçe raporunu gözden geçir"} for c in metinler), metinler)
ok("hiç aday yok → tur model çağırmaz", N["ik_tur"]()["cift"] == 0 and not N["M"].istemler)
# tarih eşitliğinde yeni = büyük yerel kimlik; çift sırası
a_, b_ = {"id": "s5", "tarih": "2026-11-10", "kayit_id": "A"}, {"id": "s9", "tarih": "2026-11-10", "kayit_id": "B"}
ok("YENİ/ESKİ: tarih eşitse büyük kimlik yeni", N["_ik_cift_kim"](a_, b_) == (b_, a_) and N["_ik_cift_kim"]({"id": "s9", "tarih": "2026-10-01", "kayit_id": "C"}, a_) == (a_, {"id": "s9", "tarih": "2026-10-01", "kayit_id": "C"}))

# --- tur başına çift sınırı: kayıt başına en çok 3 aday, tur başına en çok 8 çift; sığmayan kayıt sonraki tura ---
N = ns_kur("f"); C = N["C"]
for i in range(6): graf(C, f"2026-10-{10 + i:02d}-1000-Ekip", f"2026-10-{10 + i:02d}", "Ekip", [(f"Pazaryeri entegrasyonunu tamamla {i}", "Doruk", None)])
ciftler, islenen = N["ik_adaylar"](yapi, N["ik_acik_isler"](yapi), N["ik_oku"]())
ok("çok aday: tur başına ≤ 8 çift, kayıt başına ≤ 3; sığmayanlar işlenmedi", 0 < len(ciftler) <= 8 and len(islenen) < 6 and len(set(c[0]["kayit_id"] for c in ciftler) | set(c[1]["kayit_id"] for c in ciftler)) >= 2, (len(ciftler), len(islenen)))
shutil.rmtree(T, ignore_errors=True)
print("\n" + ("hepsi geçti" if not HATA else f"KALDI: {HATA}")); sys.exit(1 if HATA else 0)
