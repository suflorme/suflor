#!/usr/bin/env python3
# Mutabakat turu (aktarici/mutabakat.py + yapi.py durum_onerisi; zekâ Y1, 12 Kasım): gece, açık/bayat kayıtlara kanıtla durum ÖNERİSİ. Birim: bölüm yalıtılmış ad alanında
# (degerlendir.py + mutabakat.py), yalıtılmış geçici klasörde yapi grafı, sahte model (gerçek claude çağrılmaz, ağ yok), sahte posta/takvim/arama. Kurgu veri.
# Sınananlar: (a) aday seçimi + kanıt toplama (graf, gönderilmiş e-posta, takvim, döküm araması), gizli toplantı ve #53 özel nitelikli kayıt modele gitmez, kanıtsız kayıt gitmez, adres maskelenir;
# (b) olay yazımı + izdüşüm (durum_onerisi alanı), kayıt KAPANMAZ, dokunulma (bayatlık) değişmez, kanıtsız "bitti" → belirsiz; (c) /status görünümü şeması; (d) onay → var olan kapatma yolu
# (iş yapıldı, karar reddedildi), red → öneri düşer + 14 gün yeniden önerilmez, 7 gün aynı kayıt yeniden sorulmaz; (e) ölçüm satırları metinsiz; (f) izdüşüm yeniden kurulunca alan korunur;
# (g) model hatası, günlük tavan, gizli kip, ayar (beta'da kapalı), günde bir gece turu.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/mutabakat.py      (kaldı → çıkış 1)
import datetime, json, os, re, stat, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="mutabakat-"); AY = os.path.join(T, "ayar.json"); json.dump({"ad": "Ece Deneme"}, open(AY, "w")); os.environ["SUFLOR_AYAR"] = AY
import yapi
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
SAAT = {"t": datetime.datetime(2026, 11, 12, 3, 30).timestamp()}
GUN = 86400
class Model:
    def __init__(s): s.cevaplar, s.istemler = [], []
    def cagri(s, istem, amac=None, soru=None, maske=None, is_adi=None, model=None):
        s.istemler.append(istem); c = s.cevaplar.pop(0) if s.cevaplar else None
        if callable(c): c = c(istem)
        return (None, "yanıt gelmedi") if c is None else (c if isinstance(c, str) else json.dumps(c, ensure_ascii=False), None)
class Arama:  # baglam.py yerine: (pid, yol, konum, kim, metin, tur, tarih, baslik, puan)
    def __init__(s): s.satirlar, s.sorgular = [], []
    def ara(s, q, n=8, guncel=True, kapsam=None, aralik=None, **k):
        s.sorgular.append((q, kapsam, aralik)); return [r for r in s.satirlar if any(w in q.lower() for w in r[4].lower().split()[:1])][:n], []
def ns_kur(ad, ayar=None, gelistirici=True):
    C = os.path.join(T, ad); os.makedirs(C); m = Model(); durum = {"gizli": False}; log = []; arama = Arama(); posta = {"iletiler": []}; takvim = []
    def write(pairs):
        for yol, metin in pairs:
            with open(yol, "a", encoding="utf-8") as f: f.write(metin)
    ns = {"os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "AYAR": dict({"ad": "Ece Deneme", "eposta_oku": True}, **(ayar or {})), "BASE": C,
          "LOCK": threading.Lock(), "write": write, "gizli_acik": lambda: durum["gizli"], "gizli_red": lambda: {"ok": False, "gizli": True}, "_yapi_mod": lambda: yapi, "eylem_model": m.cagri,
          "print": lambda *a, **k: log.append(" ".join(str(x) for x in a)), "DG_SAAT": lambda: SAAT["t"], "MTB_SAAT": lambda: SAAT["t"], "gelistirici_mi": lambda: gelistirici,
          "_onara_mod": lambda: arama, "POSTA": posta, "posta_acik": lambda: True, "_t": lambda tr, en: tr,
          "_takvim_olaylari": lambda b, s_: [(x[0], x[1], x[2]) for x in takvim if b <= x[0] <= s_],
          "M": m, "C": C, "DURUM": durum, "LOG": log, "ARAMA": arama, "TAKVIM": takvim}
    for f in ("degerlendir.py", "mutabakat.py"): exec(compile(open(os.path.join(KOD, "aktarici", f), encoding="utf-8").read(), f, "exec"), ns)
    return ns
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def toplanti(C, ad, gizli=False):
    open(os.path.join(C, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n" + BAS + "| 10:00:00 | Ece Deneme | merhaba | |\n" + ("| 12:00:05 | **GİZLİ** | açıldı | |\n" if gizli else ""))
def graf(C, top, tarih, baslik, ogeler):
    if not os.path.exists(os.path.join(C, top + ".md")): toplanti(C, top, gizli="Gizli" in top)
    yapi.graf_yaz(C, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, top + ".md")
def kayit(C, parca):  # tam eşleşen önce, yoksa parçayı içeren ilk kayıt
    ls = yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"]
    return next((x for x in ls if x["metin"] == parca), None) or next(x for x in ls if parca in x["metin"])
def eslem(istem):  # istemdeki kayıt kimlikleri: {"Teklif": "m1", …} (kayıt metninin ilk sözcüğü → mN)
    return {m.group(2).split()[0]: m.group(1) for m in re.finditer(r"\[kayıt (m\d+)\] [^:]+: (.+)", istem)}
def kur(N):
    C = N["C"]
    graf(C, "2026-10-01-1000-Satis", "2026-10-01", "Satış haftalık", [
        {"tur": "is", "metin": "Teklif dosyasını müşteriye gönder", "sahip": "Ece Deneme", "tarih": "2026-10-10", "saat": "10:01:00"},
        {"tur": "is", "metin": "Kampanya görsellerini onayla", "sahip": "Ece Deneme", "tarih": "2026-10-08", "saat": "10:02:00"},
        {"tur": "is", "metin": "Depo envanter sayımını tamamla", "sahip": "Bora Örnek", "tarih": "2026-10-05", "saat": "10:03:00"},
        {"tur": "is", "metin": "Doktor raporunu insan kaynaklarına ilet", "sahip": "Ece Deneme", "tarih": "2026-10-05", "saat": "10:04:00"},
        {"tur": "karar", "metin": "Fuar katılımı bu yıl iptal edilsin", "kim": "Ece Deneme", "netlik": "ortuk", "saat": "10:05:00"},
        {"tur": "soru", "metin": "Lojistik sözleşmesi yenilenecek mi?", "kim": "Bora Örnek"}])
    graf(C, "2026-10-02-1000-Gizli", "2026-10-02", "Gizli görüşme", [{"tur": "is", "metin": "Teklif paketini gizli müşteriye gönder", "sahip": "Ece Deneme", "tarih": "2026-10-10", "saat": "10:01:00"}])
    graf(C, "2026-11-05-1000-Satis", "2026-11-05", "Satış haftalık", [{"tur": "is", "metin": "Kampanya görsellerini onayla ve yayına al", "sahip": "Ece Deneme", "saat": "10:01:00"}])
    toplanti(C, "2026-11-06-1000-Lojistik"); toplanti(C, "2026-11-07-1000-Gizli", gizli=True)
    N["POSTA"]["iletiler"] += [{"t": "2026-10-20T10:00:00", "gonderilen": True, "konu": "Teklif dosyası gönderimi", "ozet": "Teklif dosyasını ekte gönderiyorum, soru olursa iletisim" + "@" + "ornek.example adresine yazın"},
                               {"t": "2026-10-21T10:00:00", "gonderilen": False, "konu": "Teklif dosyası hakkında", "ozet": "Gelen ileti, sayılmaz"}]
    N["TAKVIM"].append((datetime.datetime(2026, 11, 3, 14, 0).astimezone(), datetime.datetime(2026, 11, 3, 15, 0).astimezone(), {"baslik": "Fuar katılımı iptal değerlendirmesi"}))
    N["ARAMA"].satirlar += [("p1", "2026-11-06-1000-Lojistik.md", "", "", "Lojistik sözleşmesi yenilendi, imzalar tamamlandı", "dokum", "2026-11-06", "Lojistik", 1.0),
                            ("p2", "2026-11-07-1000-Gizli.md", "", "", "Lojistik sözleşmesi hakkında gizli değerlendirme", "dokum", "2026-11-07", "Gizli", 1.0),
                            ("p3", "2026-09-01-1000-Eski.md", "", "", "Lojistik sözleşmesi eski konuşma", "dokum", "2026-09-01", "Eski", 1.0)]

# --- (a) aday seçimi ve kanıt ---
N = ns_kur("a"); C = N["C"]; kur(N)
y = yapi; ad_, say, hepsi = N["mtb_adaylar"](y)
metin = {x["metin"] for x in ad_}
ok("aday: bayat iş, onay süresi dolmuş karar, eski soru; yeni (7 g) kayıt aday değil", {"Teklif dosyasını müşteriye gönder", "Fuar katılımı bu yıl iptal edilsin", "Lojistik sözleşmesi yenilenecek mi?",
   "Kampanya görsellerini onayla", "Depo envanter sayımını tamamla"} <= metin and "Kampanya görsellerini onayla ve yayına al" not in metin, metin)
ok("gizli toplantının kaydı aday değil; #53 özel nitelikli kayıt sayılır ama aday değil", not any("gizli" in m for m in metin) and "Doktor raporunu insan kaynaklarına ilet" not in metin and say["ozel"] == 1, (metin, say))
tek = kayit(C, "Teklif dosyasını"); ks = N["mtb_kanitlar"](y, next(x for x in ad_ if x["id"] == tek["id"]), hepsi)
ok("kanıt: gönderilmiş e-posta (gelen ileti değil), adres maskeli, alıntı ≤ 160", len(ks) == 1 and ks[0]["kaynak"] == "eposta" and ks[0]["tarih"] == "2026-10-20" and "[adres]" in ks[0]["alinti"]
   and "@" not in ks[0]["alinti"] and len(ks[0]["alinti"]) <= 160, ks)
lj = kayit(C, "Lojistik"); ks = N["mtb_kanitlar"](y, next(x for x in ad_ if x["id"] == lj["id"]), hepsi)
ok("kanıt: döküm araması — gizli toplantının dökümü ve kayıttan önceki parça atılır; arama kapsamı ortak, tarih aralığı kayıttan bugüne", [k["alinti"] for k in ks] == ["Lojistik: Lojistik sözleşmesi yenilendi, imzalar tamamlandı"]
   and N["ARAMA"].sorgular[-1][1] == "ortak" and N["ARAMA"].sorgular[-1][2] == ("2026-10-01", "2026-11-12"), (ks, N["ARAMA"].sorgular[-1]))
fu = kayit(C, "Fuar"); ks = N["mtb_kanitlar"](y, next(x for x in ad_ if x["id"] == fu["id"]), hepsi)
ok("kanıt: takvim etkinliği (geçmiş: yapıldı)", [(k["kaynak"], k["tarih"]) for k in ks] == [("takvim", "2026-11-03")] and "(yapıldı)" in ks[0]["alinti"], ks)
ka = kayit(C, "Kampanya görsellerini onayla"); ks = N["mtb_kanitlar"](y, next(x for x in ad_ if x["id"] == ka["id"]), hepsi)
ok("kanıt: sonraki toplantının benzer kaydı (graf)", [(k["kaynak"], k["tarih"]) for k in ks] == [("toplanti", "2026-11-05")] and "yayına al" in ks[0]["alinti"], ks)

# --- (b) tur: olay yazımı, izdüşüm, kayıt kapanmaz ---
def cevap(istem):
    e = eslem(istem)
    return [{"id": e["Teklif"], "oneri": "bitti", "guven": 0.9, "kanit": e["Teklif"] + ".k1", "neden": "Teklif e-postayla gönderilmiş"},
            {"id": e["Fuar"], "oneri": "yerini_aldi", "guven": 0.8, "kanit": e["Fuar"] + ".k1", "neden": "Sonra yeniden değerlendirilmiş"},
            {"id": e["Lojistik"], "oneri": "bitti", "guven": 0.85, "kanit": e["Lojistik"] + ".k1", "neden": "Sözleşme yenilenmiş"},
            {"id": e["Kampanya"], "oneri": "bitti", "guven": 0.9, "kanit": "m99.k1", "neden": "Kanıt kimliği yanlış"},
            {"id": "m77", "oneri": "bitti", "guven": 1, "kanit": "", "neden": "uydurma kimlik"}]
son0 = yapi.ortak_kayit(C, tek["id"])["guncellendi"]
N["M"].cevaplar = [cevap]; r = N["mtb_calistir"]()
ist = N["M"].istemler[0] if N["M"].istemler else ""
ok("tur: tek çağrı, 4 kanıtlı kayıt; kanıtsız (depo) modele gitmedi", r.get("ok") and r["durum"] == "tamam" and r["secilen"] == 4 and r["kanitsiz"] == 1 and r["yazilan"] == 4 and len(N["M"].istemler) == 1, r)
ok("istem: kanıt satırları ve <veri>; gizli, özel nitelikli, kanıtsız kayıt ve e-posta adresi yok", "<veri>" in ist and ".k1 · gönderilmiş e-posta · 2026-10-20" in ist and "gizli" not in ist.lower().replace("gizli ", "", 0)
   and "Teklif paketini" not in ist and "Doktor" not in ist and "Depo envanter" not in ist and "@ornek" not in ist and "gizli değerlendirme" not in ist, ist[-1200:])
x = yapi.ortak_kayit(C, tek["id"]); dn = x["durum_onerisi"]
ok("izdüşüm: durum_onerisi = son öneri (öneri, güven, kanıt kaynak/tarih/alıntı, neden, zaman)", dn and dn["oneri"] == "bitti" and dn["guven"] == 0.9 and dn["kanit"]["kaynak"] == "eposta"
   and dn["kanit"]["tarih"] == "2026-10-20" and len(dn["kanit"]["alinti"]) <= 160 and dn["neden"] and dn["zaman"] and dn["olay_id"], dn)
ok("kayıt KAPANMADI; son değişiklik (dokunulma) değişmedi; durum kapısı hâlâ bayat", x["durum"] == "acik" and x["guncellendi"] == son0
   and N["mtb_adaylar"](yapi, SAAT["t"] + 8 * GUN)[0] and yapi.kayit_durumlari(C, "Ece Deneme", datetime.date(2026, 11, 12), {tek["id"]})[tek["id"]]["durum"] == "bayat", (x["durum"], x["guncellendi"], son0))
ok("tarihçe: 'durum önerdi' olayı (asistan, kaynak mutabakat)", any(o["tur"] == "durum_onerisi" and o["kaynak"] == "mutabakat" and "durum önerdi: bitti" in o["ozet"] for o in yapi.tarihce(C, tek["id"])))
dk = yapi.ortak_kayit(C, ka["id"])["durum_onerisi"]
ok("geçersiz kanıt kimlikli 'bitti' → belirsiz, güven ≤ 0,3, kanıt yok; uydurma kimlik atıldı", dk["oneri"] == "belirsiz" and dk["guven"] <= 0.3 and dk["kanit"] is None, dk)
ok("e-posta ve gelen ileti: sayılmaz satırı istemde yok", "Gelen ileti" not in ist)
# --- (c) /status görünümü ---
v = N["mtb_view"]()
ok("görünüm: son_kos + belirsiz olmayan 3 öneri, güvene göre; şema", v and v["son_kos"].startswith("2026-11-12") and [o["oneri"] for o in v["oneriler"]] == ["bitti", "bitti", "yerini_aldi"]
   and set(v["oneriler"][0]) >= {"kayit", "kayit_id", "tur", "baslik", "toplanti", "oneri", "guven", "neden", "kanit"} and set(v["oneriler"][0]["kanit"]) == {"kaynak", "tarih", "alinti"}
   and v["oneriler"][0]["kayit"] == tek["id"], v)
ok("düşünme girdisi satırı: kimlik | öneri | kanıt kaynağı ve tarihi (alıntı yok)", any(l.startswith(tek["id"] + " | bitmiş görünüyor (güven 0.9) | kanıt: gönderilmiş e-posta 2026-10-20") for l in N["mtb_dus_satirlari"]())
   and not any("Teklif" in l for l in N["mtb_dus_satirlari"]()), N["mtb_dus_satirlari"]())
# --- (d) onay / red ---
a = N["mtb_islem"]({"kayit": tek["id"], "islem": "onay"}); x = yapi.ortak_kayit(C, tek["id"])
ok("onay (iş, bitti): kayıt yapıldı olarak kapandı (var olan kapatma yolu), öneri düştü", a.get("ok") and a["kapanis"] == "yapildi" and x["durum"] == "yapildi" and x["durum_onerisi"] is None and kayit(C, "Teklif dosyasını")["durum"] == "kapandi", (a, x["durum"]))
ok("kapanış ayrı olay, Geri al ile geri alınabilir", any(o["tur"] == "durum_degisti" and "mutabakat önerisi onaylandı" in o["veri"].get("not", "") for o in yapi.tarihce(C, tek["id"]))
   and yapi.geri_al(C, a["olay_id"]) and yapi.ortak_kayit(C, tek["id"])["durum"] == "acik")
yapi.kayit_durum(C, tek["id"], "yapildi")
b = N["mtb_islem"]({"kayit": fu["id"], "islem": "onay"}); x = yapi.ortak_kayit(C, fu["id"])
ok("onay (karar, yerini aldı): karar reddedildi (onay beklemiyor), öneri düştü", b.get("ok") and b["kapanis"] == "reddedildi" and x["onay"] == "reddedildi" and x["durum_onerisi"] is None, (b, x["onay"]))
c = N["mtb_islem"]({"kayit": lj["id"], "islem": "red"}); x = yapi.ortak_kayit(C, lj["id"])
ok("red: öneri düştü, kayıt açık kaldı", c.get("ok") and "kapanis" not in c and x["durum"] == "acik" and x["durum_onerisi"] is None, (c, x["durum"]))
ok("öneri yokken onay / geçersiz işlem reddedilir", not N["mtb_islem"]({"kayit": lj["id"], "islem": "onay"}).get("ok") and not N["mtb_islem"]({"kayit": lj["id"], "islem": "sil"}).get("ok")
   and not N["mtb_islem"]({"kayit": "s9999", "islem": "red"}).get("ok"))
ok("görünüm: cevaplanan öneriler düştü", N["mtb_view"]()["oneriler"] == [], N["mtb_view"]())
# --- (e) ölçüm satırları: metin yok ---
ol = [json.loads(l) for l in open(os.path.join(C, "mutabakat.jsonl"), encoding="utf-8")]; ham = open(os.path.join(C, "mutabakat.jsonl"), encoding="utf-8").read()
ok("mutabakat.jsonl: 4 öneri + 3 sonuç (onay 2, red 1) + tur satırı; kayıt metni, alıntı, neden yok; 0600", sum(o["olay"] == "oneri" for o in ol) == 4 and [o["sonuc"] for o in ol if o["olay"] == "sonuc"] == ["onay", "onay", "red"]
   and any(o["olay"] == "tur" for o in ol) and all(set(o) <= {"t", "z", "olay", "kayit", "oneri", "guven", "kaynak", "sonuc", "durum", "aday", "yazilan", "kanitsiz"} for o in ol)
   and "Teklif" not in ham and "Lojistik" not in ham and "e-postayla" not in ham and stat.S_IMODE(os.stat(os.path.join(C, "mutabakat.jsonl")).st_mode) == 0o600, ol[-3:])
dg = open(os.path.join(C, "degerlendir.jsonl"), encoding="utf-8").read()
dgs = [json.loads(l) for l in dg.splitlines() if l.strip()]; dgm = [o for o in dgs if o.get("is") == "mutabakat"]
ok("degerlendir.jsonl: çağrı (maliyet → ortak tavan) + 4 karar + 3 sonuç satırı is=mutabakat; kayıt metni yok", any(o["olay"] == "cagri" and o.get("maliyet") is not None for o in dgm)
   and sum(o["olay"] == "karar" for o in dgm) == 4 and [o["sonuc"] for o in dgm if o["olay"] == "sonuc"] == ["kabul", "kabul", "ret"] and "Teklif dosyas" not in dg, dgm)
# --- (f) izdüşüm yeniden kurulunca öneri alanı korunur ---
once = yapi.ortak_kayit(C, ka["id"])["durum_onerisi"]; yapi.izdusum_kur(C)
ok("izdusum_kur: durum_onerisi günlükten yeniden kuruldu", yapi.ortak_kayit(C, ka["id"])["durum_onerisi"] == once and yapi.ortak_kayit(C, lj["id"])["durum_onerisi"] is None)
# --- (d2) 14 gün ve 7 gün kuralları ---
n0 = len(N["M"].istemler); SAAT["t"] += GUN; r2 = N["mtb_calistir"](zorla=True)
ok("ertesi gün: reddedilen (14 g) ve yeni öneri almış (7 g) kayıt yeniden sorulmaz; kanıtlı aday kalmadı → model çağrılmaz", r2.get("durum") == "bos" and r2["red"] == 1 and r2["yeni_oneri"] >= 1 and len(N["M"].istemler) == n0, r2)
SAAT["t"] += 15 * GUN; N["M"].cevaplar = [lambda i: [{"id": m, "oneri": "suruyor", "guven": 0.6, "kanit": m + ".k1", "neden": "Sürüyor"} for m in eslem(i).values()]]
r3 = N["mtb_calistir"](zorla=True); e3 = eslem(N["M"].istemler[-1]) if len(N["M"].istemler) > n0 else {}
ok("15 gün sonra: reddedilen kayıt ve 7 günü geçen öneri yeniden aday", r3.get("durum") == "tamam" and "Lojistik" in e3 and "Kampanya" in e3, (r3, e3))
ok("yeni öneri eskisinin yerine geçer (son öneri)", yapi.ortak_kayit(C, ka["id"])["durum_onerisi"]["oneri"] == "suruyor")

# --- (g) model hatası, günlük tavan, gizli kip, ayar, gece turu ---
N = ns_kur("g"); C = N["C"]; kur(N); SAAT["t"] = datetime.datetime(2026, 11, 12, 3, 30).timestamp()
r = N["mtb_calistir"]()
ok("model cevap vermedi: öneri yok, durum hata, kayıt yok", not r.get("ok") and r["durum"] == "hata" and not yapi.durum_onerileri(C) and N["mtb_durum"]()["durum"] == "hata", r)
N["M"].cevaplar = ["bu bir JSON değil"]; SAAT["t"] += 700; r = N["mtb_calistir"]()
ok("bozuk çıktı: öneri yok", r["durum"] == "hata" and not yapi.durum_onerileri(C), r)
N["AYAR"]["degerlendir_gunluk_usd"] = 0.01; n0 = len(N["M"].istemler); r = N["mtb_calistir"]()
ok("günlük tavan (değerlendiricinin) dolu: tur yok, model çağrılmaz", r["durum"] == "tavan" and len(N["M"].istemler) == n0, r)
N["AYAR"].pop("degerlendir_gunluk_usd"); N["DURUM"]["gizli"] = True
ok("gizli kip: tur yok, görünüm yok, uç reddeder", N["mtb_calistir"]()["durum"] == "gizli" and N["mtb_view"]() is None and N["mtb_islem"]({"islem": "calistir"}).get("gizli"))
N["DURUM"]["gizli"] = False
ok("ayar: yoksa geliştiricide açık", N["mtb_acik"]())
B = ns_kur("beta", gelistirici=False); kur(B)
ok("ayar: beta'da (geliştirici değil) varsayılan kapalı; tur ve görünüm yok", not B["mtb_acik"]() and B["mtb_calistir"]()["durum"] == "kapali" and B["mtb_view"]() is None and B["mtb_gece"]() is None
   and not B["mtb_islem"]({"islem": "calistir", "bekle": True}).get("ok") and not B["M"].istemler)
B["AYAR"]["mutabakat"] = True
ok("ayar: beta'da açıkça açılınca açık", B["mtb_acik"]())
N["AYAR"]["mutabakat"] = False
ok("ayar false: geliştiricide de kapalı, gece turu yok", not N["mtb_acik"]() and N["mtb_gece"]() is None)
N["AYAR"].pop("mutabakat"); N["M"].cevaplar = [cevap]
g1 = N["mtb_gece"](datetime.datetime.fromtimestamp(SAAT["t"] + GUN))
n1 = len(N["M"].istemler); g2 = N["mtb_gece"](datetime.datetime.fromtimestamp(SAAT["t"] + GUN + 3600))
ok("gece turu günde bir: ilk çağrı çalışır, aynı gün ikincisi çalışmaz", g1 and g1.get("durum") == "tamam" and g2 is None and len(N["M"].istemler) == n1, (g1, g2))
dosya = os.path.join(C, "mutabakat.json")
ok("durum dosyası 0600: son_kos, son_gun, sayılar", stat.S_IMODE(os.stat(dosya).st_mode) == 0o600 and N["mtb_durum"]()["son_gun"] == "2026-11-13" and N["mtb_durum"]()["sayi"]["yazilan"] == 4, N["mtb_durum"]())
r = N["mtb_islem"]({"islem": "calistir", "bekle": True})
ok("elle tetikleme (uç, bekle): günde-bir atlanır", r.get("ok") or r.get("durum") in ("bos", "tamam"), r)
# --- yapi API'si: gizli toplantı kaydına öneri yazılmaz ---
gz = next(x for x in yapi.kayit_listesi(C, "Ece Deneme", deneme=True)["kayitlar"] if "Teklif paketini" in x["metin"]) if any("Teklif paketini" in x["metin"] for x in yapi.kayit_listesi(C, "Ece Deneme")["kayitlar"]) else None
c_ = yapi._db(C); kid_g = c_.execute("SELECT kayit_id FROM kayit WHERE metin LIKE 'Teklif paketini%'").fetchone()[0]; c_.close()
o, _ = yapi.durum_onerisi_yaz(C, kid_g, "bitti", 0.9, {"kaynak": "eposta", "tarih": "2026-10-20", "alinti": "x"})
ok("yapi: gizli toplantının kaydına durum önerisi yazılmaz; cevap da reddedilir", gz is None and o is None and not yapi.durum_onerisi_cevap(C, kid_g, "onay").get("ok"))
try: yapi.durum_onerisi_yaz(C, tek["id"], "kapandi", 1); gec = False
except ValueError: gec = True
ok("yapi: şema dışı öneri ValueError", gec)
ok("yapi: öneri olayları ekip paylaşımına gitmez", not any(t.startswith("durum_onerisi") for t in yapi.PAYLASILAN_OLAY))

print(("\nKALDI: " + ", ".join(HATA)) if HATA else "\nHepsi geçti.")
import shutil; shutil.rmtree(T, ignore_errors=True)
sys.exit(1 if HATA else 0)
