#!/usr/bin/env python3
# Konuş ön araması (S47, v0.40.0; aktarici/bas-konus.py konus_onara): soru Claude'a gitmeden baglam.py dizininde aranır, en iyi parçalar dosya yolu ve
# kesitle bağlam bloğuna eklenir. Geçici proje klasörü + dizin: doğru dosya ilk sırada, kesitte aranan bilgi, < 3 sözcüklü/kısa soruda blok yok,
# arama dizini güncellemez ve hızlı (< 300 ms), Türkçe büyük İ / sözlük biçimleri bozulmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/onara.py
import os, re, sys, json, shutil, tempfile, time, threading, importlib.util
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-onara-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
proje = os.path.join(T, "proje"); os.makedirs(os.path.join(proje, "notlar"))
open(os.path.join(proje, "notlar", "yedekleme-politikasi.md"), "w").write("# Yedekleme politikası\n\nGünlük yedek her gece saat 02:00'de alınır. Sorumlu Ayla Örnek; geri yükleme denemesi ayda bir.\n")
open(os.path.join(proje, "notlar", "butce.md"), "w").write("# Bütçe\n\nPazarlama bütçesi üçüncü çeyrekte yüzde on artırıldı. Onaylayan Deniz Test.\n")
for i in range(30): open(os.path.join(proje, "notlar", f"dolgu-{i}.md"), "w").write(f"# Not {i}\n\nToplantı notu {i}: genel konular, takvim, ekip.\n")
json.dump({"alan": "Deneme", "ad": "Deniz T", "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor"}, open(os.path.join(T, "ayar.json"), "w"))
os.environ["SUFLOR_AYAR"] = os.path.join(T, "ayar.json"); os.environ["SUFLOR_TEST_BASLAT"] = "1"; sys.dont_write_bytecode = True
try:
    # bas-konus.py'nin ön arama bölümü, relay ad alanı yerine küçük taklitle (bölüm dosyası relay.py'nin ad alanında çalışır; __file__ relay.py yanında)
    src = open(os.path.join(K, "aktarici", "bas-konus.py"), encoding="utf-8").read()
    g = {"os": os, "re": re, "sys": sys, "time": time, "threading": threading, "_t": lambda tr, en: tr, "__file__": os.path.join(K, "relay.py"), "AYAR": {}, "ARAYUZ_DILI": "tr", "BASE": os.path.join(T, "canli")}  # v0.84.0: takvim geçmişi dosya yolu BASE ister
    exec(src[src.index("# --- Hızlı bilgi (S47"):src.index("def konus_baglam(")], g)
    m = g["_onara_mod"](); bak("baglam.py yüklendi", m is not None)
    t = time.time(); m.guncelle(m.baglan()); print(f"   dizin kuruldu ({time.time() - t:.2f} sn)")
    t = time.time(); b = g["konus_onara"]("Yedekleme hangi saatte alınıyor, sorumlusu kim?"); sn = time.time() - t
    print("   " + b.replace("\n", "\n   ")[:600])
    bak("blok başı ve sonu", b.startswith("[Ön arama") and b.rstrip().endswith("[/Ön arama]"))
    bak("ilk sonuç doğru dosya", b.split("\n")[1].find("yedekleme-politikasi.md") > 0)
    bak("kesitte aranan bilgi (02:00, Ayla)", "02:00" in b and "Ayla" in b)
    bak(f"hızlı ({sn * 1000:.0f} ms < 300)", sn < 0.3)
    bak("kısa soruda blok yok ('saat kaç')", g["konus_onara"]("Saat kaç?") == "")
    bak("tek içerik sözcüğünde blok yok ('bütçe ne?')", g["konus_onara"]("Bütçe ne?") == "")
    # v0.80.5: toplantıda dönemsel dizin ısıtma (düğmesiz hitap ve karşı tarafın sorusu için)
    g.update(STATE={}, toplanti_var=lambda: False, toplanti_konus=lambda: True); g["_ONARA"]["isit_t"] = 0
    bak("toplantı yokken dönemsel ısıtma yok", g["onara_toplanti_isit_bak"]() is False and not g["_ONARA"]["isit_t"])
    g["toplanti_var"] = lambda: True; r_ = g["onara_toplanti_isit_bak"](); time.sleep(0.5)
    bak(f"toplantıda dizin ısıtılır ({g['_ONARA'].get('isit_ms')} ms)", r_ is True and g["_ONARA"]["isit_t"] > 0 and g["_ONARA"].get("isit_ms") is not None)
    g["toplanti_konus"] = lambda: False; g["_ONARA"]["isit_t"] = 0
    bak("toplantıda Konuş kapalıysa (toplanti_konus) ısıtma yok", g["onara_toplanti_isit_bak"]() is False)
    g["_ONARA"].pop("isit_ms", None)
    b2 = g["konus_onara"]("Pazarlama bütçesi ne kadar artırıldı?")
    bak("ikinci soru doğru dosya", "butce.md" in b2.split("\n")[1] and "yüzde on" in b2)
    open(os.path.join(proje, "notlar", "yeni.md"), "w").write("# Yeni\n\nKarbon ayak izi raporu cuma günü teslim.\n")
    bak("arama dizini güncellemez (yeni dosya ön aramada yok)", "yeni.md" not in g["konus_onara"]("Karbon ayak izi raporu ne zaman teslim?"))
    m.guncelle(m.baglan())
    bak("güncellemeden sonra yeni dosya bulunur", "yeni.md" in g["konus_onara"]("Karbon ayak izi raporu ne zaman teslim?"))
    # v0.42.0 / v0.94.0 bekleme cümlesi: son iki cümle tekrar yok, türe göre içerikli cümle, bilinmeyen türde kısa genel havuz, eski kalıplar yok
    bc, bt = g["bekleme_cumlesi"], g["bekleme_turu"]; s = [bc() for _ in range(40)]
    bak("bekleme cümlesi son ikisiyle aynı değil", all(c not in s[i - 2:i] for i, c in enumerate(s) if i >= 2) and all(a != b for a, b in zip(s, s[1:])))
    bak("türe göre içerikli cümle çıkıyor (görüşme)", "Görüşme kayıtlarına bakıyorum." in {bc("gorusme") for _ in range(40)})
    bak("tek cümlelik türde de art arda aynısı yok (tablo)", all(a != b for a, b in zip(*(lambda x: (x, x[1:]))([bc("tablo") for _ in range(30)]))))
    bak("bilinmeyen tür → kısa genel havuz", all(c in g["BEKLE_GENEL"]["tr"] for c in (bc("bilinmeyen") for _ in range(20))))
    havuz = str(g["BEKLE_GENEL"]) + str(g["BEKLE_TUR"])
    bak("eski kalıplar havuzda yok", not any(k in havuz for k in ("Hemen bakıyorum", "Kontrol ediyorum", "araştırma yapıyorum")))
    vt = "mcp__suflorvt__vt_sor"
    bak("v0.101.0 veritabanı aracında konuya göre: plan → plan, sayı → sayı, takvim → takvim, görüşme → görüşme, diğer → kayıtlar",
        bt("Günaydın Asistan. Bugün planımızda neler var?", vt) == "plan" and bt("Kaç tane açık iş var?", vt) == "sayi" and bt("Yarın takvimimde ne var?", vt) == "takvim"
        and bt("Ayla'yla en son ne zaman görüştük?", vt) == "gorusme" and bt("ne var", vt) == "kayit" and bc("plan") in g["BEKLE_TUR"]["plan"])
    bak("tür seçimi: takvim sorusu → takvim, sayı sorusu → sayı, dosya araması → not, sıradan soru → genel",
        True and bt("Yarın takvimimde ne var?") == "takvim" and bt("Perşembe müsait miyim?") == "takvim"
        and bt("Kaç tane açık sipariş var?") == "sayi" and bt("Ne konuştuk?", "Grep") == "not" and bt("Bu fikir hakkında ne düşünüyorsun?") is None
        and bt("x", tur_ad="defter") == "not" and bt("x", tur_ad="belge") == "belge")
    print("   örnek:", bc("takvim"), "|", bc("sayi"), "|", bc("not"), "|", bc())
    # v0.101.0 Konuş selamı: günün ilk sorusunda saate göre, 2 saat aradan sonra "Tekrar merhaba", konuşma sürerken yok; kullanıcının selamına aynısıyla
    okunan = []; os.makedirs(g["BASE"], exist_ok=True)
    g.update(json=json, seslendir=lambda m, kuyruk=False, cal=None: okunan.append(m) or True, toplanti_var=lambda: False, print=lambda *a, **k: None); g["AYAR"]["ad"] = "Deniz T"
    sm, ks, sa = g["selam_metni"], g["konus_selam"], g["selam_asamasi"]
    bak("saate göre ilk selam (sabah Günaydın, akşam İyi akşamlar, gün içi Merhaba/Selam)", sm("Bugün ne var?", "ilk", 9) == "Günaydın Deniz." and sm("x", "ilk", 20) == "İyi akşamlar Deniz."
        and sm("x", "ilk", 14) in ("Merhaba Deniz.", "Selam Deniz."))
    bak("kullanıcının selamına aynısıyla (hitaptan sonra da), uzun aradan sonra 'Tekrar merhaba'", sm("Günaydın Asistan. Planımızda ne var?", "ilk", 20) == "Günaydın Deniz."
        and sm("Asistan, selam. Nasılsın?", None) == "Selam Deniz." and sm("Merhaba, bugün ne var?", "tekrar") == "Tekrar merhaba Deniz." and sm("x", "tekrar") == "Tekrar merhaba Deniz.")
    bak("selamsız soruda konuşma sürerken selam yok; 'selamı ilet' selam sayılmaz", sm("Bir de yarına bak.", None) is None and sm("Ayla'ya selamı ilet.", None) is None)
    tur_ = {"sesli": True, "toplantida": False, "kaynak": "bas"}
    s1 = ks("Bugün ne var?", tur_); s2 = ks("Peki yarın?", tur_)
    bak("ilk soruda okundu, hemen ardından ikinci soruda yok; aşama artık yok", s1 and okunan == [s1] and s2 is None and sa() is None)
    g["_SELAM"]["son"] -= 3 * 3600; s3 = ks("Şimdi ne var?", dict(tur_))
    bak("3 saat sonra aynı gün 'Tekrar merhaba'", s3 == "Tekrar merhaba Deniz.")
    bak("toplantıda, karşı tarafın sorusunda, sessiz turda selam yok", [ks("Merhaba", dict(tur_, toplantida=True)), ks("Merhaba", dict(tur_, karsi="Ayla")), ks("Merhaba", dict(tur_, sesli=False))] == [None] * 3)
    g["_SELAM"].update(yuklendi=False, son=0, gun=None); bak("durum dosyadan geri yüklenir (aktarıcı yeniden başlasa da)", sa() is None and g["_SELAM"]["gun"])
    g["AYAR"]["konus_selam"] = False; g["_SELAM"]["son"] -= 3 * 3600; bak("ayar konus_selam: false kapatır", ks("Merhaba", dict(tur_)) is None and not g["selam_bekleniyor"]())
    # v0.101.4: Türkçe arayüzde İngilizce soruda bekleme cümlesi ve selam İngilizce (kullanıcı: İngilizce konuşmada "Belgelere bakıyorum" dendi)
    bsrc = open(os.path.join(K, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); csrc = open(os.path.join(K, "aktarici", "ceviri.py"), encoding="utf-8").read()
    exec(csrc[csrc.index("_EN_SOZ ="):csrc.index("def ceviri_ekle")], g); exec(bsrc[bsrc.index("_DIL_EN = set("):bsrc.index("def okuma_dili(")], g)
    g["AYAR"].pop("konus_selam", None)
    en_b = [bc("belge", g["konus_soru_dili"]("Can you check the documents for the budget?")) for _ in range(10)]
    bak(f"İngilizce soruda bekleme cümlesi İngilizce ({en_b[0]}), Türkçe soruda Türkçe", all(c in g["BEKLE_TUR_EN"]["belge"] + g["BEKLE_GENEL"]["en"] for c in en_b)
        and bc("belge", g["konus_soru_dili"]("Bütçe belgelerine bakar mısın?")) in g["BEKLE_TUR"]["belge"])
    bak("İngilizce soruya İngilizce selam (karşılık, sabah, tekrar)", sm("Good morning, what's on my calendar today?", "ilk", 20) == "Good morning Deniz."
        and sm("What do I have today?", "ilk", 9) == "Good morning Deniz." and sm("What about tomorrow then?", "tekrar") == "Hello again Deniz." and sm("Bugün ne var?", "ilk", 9) == "Günaydın Deniz.")
    bak("not metni: yeniden selamlama deme", "yeniden selamlama" in g["selam_notu"]("Günaydın Deniz.") and g["selam_notu"](None) == "")
finally:
    if not hata: shutil.rmtree(T, ignore_errors=True)
    else: print(f"(deneme klasörü: {T})")
print("ön arama: ✓ hepsi geçti" if not hata else f"ön arama: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
