#!/usr/bin/env python3
# Konuş'a eklenen belge (9 Kasım canlı deneme: panoya eklenen kitap PDF'ini asistan okumadan cevapladı) — bas-konus.py `belge_*`: PDF/metin metne çevrilir,
# her soruda kısa blok (kısa belgede metin, uzunda dosya yolu + "önce belgede ara" talimatı), okunamazsa "uydurma" uyarısı, gizli kipte yok, bir kez çevrilir.
# Kurgu belge (cupsfilter), gerçek PDFKit (swift), Docling yok (_onara_mod stub). Süreç/ağ/Claude yok (~10 sn):
#   PYTHONDONTWRITEBYTECODE=1 python3 test/belge-baglam.py
import os, re, shutil, subprocess, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
if not os.path.exists("/usr/bin/swift") or not os.path.exists("/usr/sbin/cupsfilter"): sys.exit("atlandı: swift ya da cupsfilter yok")
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
T = tempfile.mkdtemp(prefix="belge-"); KAYNAK = []; GIZLI = [False]
ad = {"os": os, "re": re, "time": time, "threading": threading, "sys": sys, "AYAR": {}, "BASE": os.path.join(T, "canli"), "_t": lambda a, b: a,
      "baglam_oku": lambda: list(KAYNAK), "gizli_acik": lambda: GIZLI[0], "_onara_mod": lambda: None}
exec(kod[kod.index("import hashlib, subprocess\nBELGE_DOGRUDAN"):kod.index("def konus_baglam(")], ad)
blok = ad["belge_baglam"]
ok("konus_baglam her soruda belge bloğunu ekler", "gt += belge_baglam()" in kod)
rl = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
ok("baglam_ekle yeni dosyayı hemen metne çevirmeye başlatır", re.search(r'if yeni and "belge_hazirla" in globals\(\)', rl) is not None)
ok("kaynak yokken blok yok", blok() == "")
def pdf(ad_, satirlar):
    t = os.path.join(T, ad_ + ".txt"); open(t, "w", encoding="utf-8").write("\n".join(satirlar) + "\n")
    p = os.path.join(T, ad_ + ".pdf"); open(p, "wb").write(subprocess.run(["/usr/sbin/cupsfilter", t], capture_output=True).stdout); return p
def ekle(i, yol): KAYNAK.append({"id": f"b{i}", "tur": "dosya", "deger": yol, "ad": os.path.basename(yol)})
# 1) uzun belge (kitap gibi): ~120 satır ≈ 4 sayfa
uzun = pdf("kurgu-kitap", [f"Bolum {i}: Deneme satiri numara {i} kurgu belge metnidir ve yeterince uzundur ki dort bin karakteri asar." for i in range(1, 121)] + ["Ozel cumle: kayisi agacinin golgesinde piramit ilkesi uygulanir."])
ekle(1, uzun); t0 = time.time(); b = blok(); sure = time.time() - t0
yol = re.search(r"metin dosyası (\S+\.txt)", b)
ok("uzun belge: blokta metin dosyası yolu + sayfa sayısı", yol is not None and re.search(r"\d+ sayfa", b) is not None)
ok("uzun belge: tüm metin bloğa girmez (kısa blok), Grep/Read talimatı + sayfa belirt + belgede yoksa söyle", len(b) < 1800 and "Grep" in b and "Read" in b and "sayfa/bölüm belirt" in b and "belgede bulamadım" in b)
txt = open(yol.group(1), encoding="utf-8").read() if yol else ""
ok("metin dosyası canlı klasörün altında (Konuş --add-dir=canlı: Read edilebilir), sayfa işaretli, içerik aranabilir", yol is not None and yol.group(1).startswith(ad["BASE"] + os.sep) and "=== sayfa 2 ===" in txt and "piramit ilkesi" in txt)
ok(f"çeviri hızlı ({sure:.1f} sn)", sure < 15)
n0 = len(ad["_BELGE"]); b2 = blok()
ok("ikinci soruda yeniden çevrilmez (aynı kayıt)", len(ad["_BELGE"]) == n0 and b2 == b)
# 2) kısa belge: metin doğrudan
kisa = pdf("kurgu-kisa", ["Kisa belge: toplanti 14 Aralik tarihinde yapilacaktir.", "Gundem: butce onayi."] * 6 + ["Bu bir kurgu belgedir ve baska hicbir amac tasimaz; yalnizca denemede kullanilir."]); ekle(2, kisa)
t = os.path.join(T, "k.txt"); open(t, "w", encoding="utf-8").write("Kisa not: tek satir. " * 3)
b = blok()
ok("kısa PDF: metin doğrudan bloğa girer", "--- belge metni ---" in b and "butce onayi" in b)
# 3) düz metin dosyası → doğrudan metin
open(t, "w", encoding="utf-8").write("Not: " + "kisa metin icerigi " * 20); ekle(3, t)
b = blok(); ok("kısa düz metin doğrudan bloğa girer", "--- belge metni ---" in b and "kisa metin icerigi" in b)
# 4) okunamayan (bozuk PDF; Docling yok) → uydurma uyarısı
KAYNAK.clear(); bozuk = os.path.join(T, "bozuk.pdf"); open(bozuk, "wb").write(b"%PDF-1.4 bozuk"); ekle(4, bozuk)
b = blok(); ok("okunamayan belge: 'OKUYAMADIN, uydurma' uyarısı, içerik yok", "OKUYAMADIN" in b and "uydurma" in b and "--- belge metni ---" not in b)
# 5) hâlâ çevriliyor
KAYNAK.clear(); ad["BELGE_BEKLE_SN"] = 0.3; asil = ad["_belge_metin"]; ad["_belge_metin"] = lambda y: (time.sleep(2), (None, "x"))[1]
ekle(5, t); b = blok(); ok("çeviri sürerken: 'HENÜZ BİLMİYORSUN, tahmin yürütme'", "HENÜZ BİLMİYORSUN" in b); ad["_belge_metin"] = asil; time.sleep(2.2)
# 6) gizli kip + dosya yok
GIZLI[0] = True; ok("gizli kipte blok yok", blok() == ""); GIZLI[0] = False
KAYNAK.clear(); KAYNAK.append({"id": "b9", "tur": "baglanti", "deger": "https://example.org", "ad": "x"}); ok("yalnız bağlantı eklenmişse blok yok", blok() == "")
KAYNAK.clear(); ekle(6, os.path.join(T, "yok.pdf")); ok("silinmiş dosya: okunamadı bildirimi, hata yok", "OKUYAMADIN" in blok())
shutil.rmtree(T, ignore_errors=True)
print("belge bağlamı: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")); sys.exit(1 if HATA else 0)
