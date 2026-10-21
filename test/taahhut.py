#!/usr/bin/env python3
# Taahhüt ve tutarlılık (taahhut.py, S91): net olmayan söz · aynı toplantıda değişen rakam · karar grafıyla fark · olay 10 dk'da en çok bir ·
# toplantı sonu `taahhut` komutu (<toplantı>.taahhut.log). Gerçek dökümlerden alınmış biçimler (cümleler boşluksuz birleşik, Whisper yazımı).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/taahhut.py      (kaldı → çıkış 1; ~1 sn)
import json, os, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
import taahhut as T
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)

# 1) net olmayan söz
EVET = ["Tamam, ona bakarız sonra.", "En kısa sürede hallederim, merak etme.", "Bunu deneyeceğim ama söz veremem.",
        "I'll try to get the list over to you.", "Let me look into it and get back to you.", "Fırsat bulunca gönderirim dosyayı."]
HAYIR = ["Yarın sabah dosyayı göndereceğim.", "Cuma'ya kadar listeyi atarım.", "Şöyle bakalım.Evet.", "Geçen hafta bakmıştım ona.",
         "Her sabah mailleri kontrol ederim.", "Bunu deneyecek misin?", "He tried to do the repair.", "I'll send it tomorrow morning.",
         "Tamam.Şu anda şu bakalım ne demiş?"]
for c in EVET: bak(f"net değil: {c}", bool(T.net_degil(c)))
for c in HAYIR: bak(f"net değil sayılmaz: {c}", not T.net_degil(c))
bak("birleşik satırda doğru cümle", (T.net_degil("Evet anladım.Ona bakarız sonra.Tamam.") or ("", ""))[1] == "Ona bakarız sonra.")

# 2) rakam: aynı ad + aynı sıklık + ortak bağlam; farklı şeyler eşleşmez
def akit(satirlar):
    t = T.Taahhut("Kullanıcı K"); ol = []
    for i, (kim, metin) in enumerate(satirlar): ol += t.besle({"speaker": kim, "time": f"10:{i:02d}:00", "text": metin}, i * 60.0)
    return t, ol
t, ol = akit([("Ayşe K", "Bu toplantıya 3 kişi katılıyor."), ("Kullanıcı K", "Tamam."), ("Ayşe K", "Ben, Can, Deniz katılıyor, 4 kişi katılıyor bu toplantıya.")])
r = [x for x in t.kayit if x["tur"] == "rakam"]
bak("aynı toplantı: 3 kişi → 4 kişi bulundu", len(r) == 1 and r[0]["onceki"]["deger"] == "3" and r[0]["deger"] == "4")
bak("aynı toplantıda rakam canlı olay değil (yalnız kayıt; kesinlik düşük)", not ol)
bak("rakam satırı biçimi (toplantı sonu listesi için) soru biçiminde", T.olay_satiri(r[0]).startswith("RAKAM DEĞİŞTİ:") and "hangisi?" in T.olay_satiri(r[0]))
t2 = T.Taahhut("Kullanıcı K"); ol = t2.besle({"speaker": "Ali V", "time": "10:00:00", "text": "Raporu Can Bey'e göndereceğim."}, 0.0)
bak("tarihsiz söz kayıtta, canlı olay yok", t2.kayit and t2.kayit[0]["isaret"] == "tarih yok" and not ol)
bak("anlatım geleceği söz sayılmaz", not T.net_degil("Şimdi ikinci bölüme geçeceğiz, sorular anonim."))
t, _ = akit([("Ali V", "Yani şu an geciken 13 tane siparişim var."), ("Ali V", "Fedex'in alması gereken 7 tane sipariş var.")])
bak("farklı bağlamda aynı ad (sipariş) eşleşmez", not [x for x in t.kayit if x["tur"] == "rakam"])
t, _ = akit([("Ali V", "Yaklaşık 20 dakika sürdü."), ("Ali V", "Bazen 5 dakika sürüyor.")])
bak("süre sayıları karşılaştırılmaz", not t.kayit)
t, _ = akit([("Ali V", "Ben 23 kişi var."), ("Ali V", "Çünkü biz 3 kişi çalışıyoruz.")])
bak("'3 kişi' bin sayılmaz (k harfi çarpan değil)", all(x["deger"] != "3.000" for x in t.kayit))
t, _ = akit([("Ali V", "Günlük 56 sipariş geliyor depoya."), ("Ali V", "Depoya günlük 56 sipariş geliyor, evet.")])
bak("aynı değer tekrarı değişiklik değil", not t.kayit)
t, _ = akit([("Ali V", "Depoya günde 40 sipariş geliyor."), ("Ali V", "Haftada 60 sipariş geliyor depoya.")])
bak("sıklık farklıysa (günde/haftada) eşleşmez", not [x for x in t.kayit if x["tur"] == "rakam"])

# 3) geçmiş: karar grafındaki sayılı beyan
graf = {"ayşe": [("2026-10-11", "Bütçe toplamı 95 bin TL olarak kalacak")]}
t = T.Taahhut("Kullanıcı K", lambda kim: graf.get(T.kucuk(kim).split(" ")[0], []))
ol = t.besle({"speaker": "Ayşe Yılmaz", "time": "10:05:00", "text": "Bütçe toplamı 120 bin TL olacak gibi görünüyor."}, 0.0)
g = [x for x in t.kayit if x["tur"] == "gecmis"]
bak("geçmişle fark: 95 bin → 120 bin", len(g) == 1 and g[0]["onceki"]["deger"] == "95.000" and g[0]["deger"] == "120.000")
bak("olay GEÇMİŞLE FARK, tarihli, 'yalan' yok", ol and ol[0].startswith("GEÇMİŞLE FARK:") and "2026-10-11" in ol[0] and "yalan\"" not in ol[0].split("→")[0])
ol = t.besle({"speaker": "Bora K", "time": "10:06:00", "text": "Bütçe toplamı 120 bin TL olacak."}, 30.0)
bak("başka kişinin grafı karşılaştırılmaz", not [x for x in t.kayit if x["tur"] == "gecmis" and x["kim"] == "Bora K"])

# 4) sınır: olay 10 dk'da en çok bir, hepsi kayıtta
t = T.Taahhut("Kullanıcı K"); ol = []
for i, c in enumerate(["Ona bakarız.", "En kısa sürede hallederim.", "Deneyeceğim ama bilmiyorum."]):
    ol += t.besle({"speaker": "Ali V", "time": f"10:0{i}:00", "text": c}, i * 60.0)
bak("3 bulgu, 1 olay (10 dk sınırı)", len(t.kayit) == 3 and len(ol) == 1)
ol2 = t.besle({"speaker": "Ali V", "time": "10:11:00", "text": "Fırsat bulunca gönderirim."}, 660.0)
bak("10 dk sonra yeni olay", len(ol2) == 1)

# 5) toplantı sonu komutu: <toplantı>.taahhut.log → türe göre, tekrarsız
D = tempfile.mkdtemp(prefix="suflor-th-"); md = "2026-10-21-1000-deneme.md"
open(os.path.join(D, md), "w").write("# Deneme\n")
with open(os.path.join(D, md[:-3] + ".taahhut.log"), "w", encoding="utf-8") as f:
    for x in t.kayit + t.kayit[:1]: f.write(json.dumps(x, ensure_ascii=False) + "\n")
o = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", D, "--relay", "http://127.0.0.1:9", "taahhut", "--toplanti", md],
                   capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=30)
bak("taahhut komutu: NET OLMAYAN SÖZ (4), tekrar yok", o.returncode == 0 and "NET OLMAYAN SÖZ (4)" in o.stdout and o.stdout.count("Ona bakarız.") == 1)
os.remove(os.path.join(D, md[:-3] + ".taahhut.log"))
o = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", D, "--relay", "http://127.0.0.1:9", "taahhut", "--toplanti", md],
                   capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=30)
bak("kayıt yoksa 'bulgusu yok'", o.returncode == 0 and "bulgusu yok" in o.stdout)

print(("KALDI: " + ", ".join(hata)) if hata else "GEÇTİ")
sys.exit(1 if hata else 0)
