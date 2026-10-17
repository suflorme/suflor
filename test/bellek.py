#!/usr/bin/env python3
# Bellek (v0.64.0, S76): baglam.py bellek kaynakları (karar/kural/konusma türleri, kapsam, satır tarihi, zaman süzgeci, Masaüstü engelinde koruma) ve
# aktarici/bellek.py (Konuş geçmişi kaydı ve 90 gün döndürme, kullanıcı kartı istemde, kapsam kararı, sesle düzeltme sırası). Süreç açılmaz, Claude yok.
# Nötr adlar (Atlas/Matlas, Deniz); gerçek kart depoya girmez.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bellek.py
import datetime, gzip, importlib.util, json, os, re, shutil, stat, sys, tempfile, threading, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="bellek-"); canli = os.path.join(T, "canli"); proje = os.path.join(T, "proje"); dis = os.path.join(T, "dis"); kural = os.path.join(T, "kural")
for d in (canli, proje, dis, kural): os.makedirs(d)
hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
# --- kaynaklar -----------------------------------------------------------------------------------------------------------------------------
open(os.path.join(proje, "alan-kararlari.md"), "w", encoding="utf-8").write(
    "# Karar listesi\n\n| No | Tarih | Karar | Veren |\n|---|---|---|---|\n"
    "| 85 | 09.10.2026 | **Varsayılanla ilerleme.** Cevap gelmeyen istek varsayılanla gider; para ve rol açık onayla. | Deniz |\n"
    "| 96 | 09.10.2026 | Envanter ekran paylaşımıyla çıkarılmayacak; geçici salt okuma yetkisiyle çekilecek. | Deniz |\n"
    "| 123 | 14.10.2026 | Aktif iş sınırı yalnız Deniz'in yürüttüğü işe uygulanır. | Deniz |\n")
open(os.path.join(proje, "notlar.md"), "w", encoding="utf-8").write("# Notlar\nEnvanter ekran paylaşımı notu, sıradan belge.\n")
open(os.path.join(dis, "urun-defteri.md"), "w", encoding="utf-8").write(
    "| No | Tarih | Karar | Kim |\n|---|---|---|---|\n| S43 | 13.10.2026 | **Karne kaldırıldı.** Not toplantıyı ayırt etmiyordu; yerine toplantı çıktısı. | Deniz |\n"
    "| | 14.10.2026 | Güncelleme (14 Ekim): S43 çıktısı panoda da görünür. | Deniz |\n| S52 | 15.10.2026 | Ses: Elif dinleme testinde açık ara. | Deniz |\n")
open(os.path.join(kural, "MEMORY.md"), "w", encoding="utf-8").write("- [a](a.md) — dizin\n")
open(os.path.join(kural, "kisayol.md"), "w", encoding="utf-8").write("---\nname: kisayol\n---\nKısayollar açık yazılır: Option + Shift + K. Deniz 2 Ekim'de istedi.\n")
bugun = datetime.date.today(); gh = bugun - datetime.timedelta(days=bugun.weekday() + 5)  # geçen haftanın çarşambası
gecmis = os.path.join(canli, "konus-gecmis.jsonl")
open(gecmis, "w", encoding="utf-8").write(json.dumps({"at": f"{gh.isoformat()}T15:00:00+03:00", "kisilik": "Matlas", "kaynak": "bas", "soru": "Fotoğraf makinesi alsam mı?",
                                                      "sesli": "Önce lens bütçesini belirle.", "ayrinti": "", "toplanti": None}, ensure_ascii=False) + "\n")
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "uygulama": T, "proje": proje, "kisilik_bellek": os.path.join(T, "kart.md"),
           "bellek_kaynaklari": [{"yol": os.path.join(proje, "alan-kararlari.md"), "tur": "karar", "kapsam": "ortak"},
                                 {"yol": os.path.join(dis, "urun-defteri.md"), "tur": "karar", "kapsam": "ozel"},
                                 {"yol": os.path.join(kural, "*.md"), "tur": "kural", "kapsam": "ozel"}, {"yol": "/yok/bu/yol/*.md", "tur": "kural"}]}, open(ay, "w"))
os.environ["SUFLOR_AYAR"] = ay; sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("bg", os.path.join(KOD, "baglam.py")); bg = importlib.util.module_from_spec(sp); sp.loader.exec_module(bg)
try:
    c = bg.baglan(); bg.guncelle(c)
    tur = dict(c.execute("SELECT yol, tur FROM dosya"))
    kap = dict(c.execute("SELECT yol, COALESCE(kapsam, 'ortak') FROM dosya"))
    ok("proje içindeki karar listesi 'karar' türü, sıradan belge 'belge'", tur.get("alan-kararlari.md") == "karar" and tur.get("notlar.md") == "belge")
    ok("proje dışı karar listesi tam yolla, özel kapsam", tur.get(os.path.realpath(os.path.join(dis, "urun-defteri.md"))) == "karar" and kap.get(os.path.realpath(os.path.join(dis, "urun-defteri.md"))) == "ozel")
    ok("kural dosyası girdi, MEMORY.md girmedi", tur.get(os.path.realpath(os.path.join(kural, "kisayol.md"))) == "kural" and not any(y.endswith("MEMORY.md") for y in tur))
    ok("Konuş geçmişi 'konusma' türü, özel kapsam", tur.get(gecmis) == "konusma" and kap.get(gecmis) == "ozel")
    sat = c.execute("SELECT konum, tarih, metin FROM parca WHERE yol = ? ORDER BY id", (os.path.realpath(os.path.join(dis, "urun-defteri.md")),)).fetchall()
    ok("karar listesi: satır başına parça, numara ve satır tarihi; Güncelleme satırı önceki numaraya +",
       [(a, b) for a, b, _ in sat] == [("S43", "2026-10-13"), ("S43+", "2026-10-14"), ("S52", "2026-10-15")] and "**" not in sat[0][2])
    r, _ = bg.ara("envanter ekran paylaşımı", guncel=False)
    ok("arama karar satırını buluyor (satırın tarihiyle)", any(x[1] == "alan-kararlari.md" and x[2] == "96" and x[6] == "2026-10-09" for x in r))
    r, _ = bg.ara("karne toplantı çıktısı", guncel=False); r2, _ = bg.ara("karne toplantı çıktısı", guncel=False, kapsam="ortak")
    ok("özel kapsam: hepsinde var, kapsam=ortak'ta yok", any(x[5] == "karar" for x in r) and not any("urun-defteri" in x[1] for x in r2))
    r2, _ = bg.ara("fotoğraf makinesi lens", guncel=False, kapsam="ortak"); r, _ = bg.ara("fotoğraf makinesi lens", guncel=False)
    ok("Konuş geçmişi ortak aramada yok, tam aramada var", not r2 and any(x[5] == "konusma" for x in r))
    # zaman süzgeci (17 Ekim 2026 cumartesi)
    B = datetime.date(2026, 10, 17); Z = lambda q: bg.zaman_araligi(q, B)
    ok("zaman: dün / geçen hafta / bu hafta / geçen ay", Z("Dün ne konuştuk?") == ("2026-10-16", "2026-10-16") and Z("geçen hafta ne demiştim") == ("2026-10-05", "2026-10-11")
       and Z("bu hafta neye karar verdik") == ("2026-10-12", "2026-10-17") and Z("Geçen ay ne demiştim?") == ("2026-09-01", "2026-09-30"))
    ok("zaman: geçen salı / 3 gün önce / son 7 gün / 12 Ekim / evvelsi gün", Z("geçen salı ne konuştuk") == ("2026-10-06", "2026-10-06")
       and Z("3 gün önce sana ne sordum") == ("2026-10-13", "2026-10-15") and Z("son 7 günde neye karar verdik") == ("2026-10-10", "2026-10-17")
       and Z("12 Ekim'de ne demiştim") == ("2026-10-12", "2026-10-12") and Z("evvelsi gün ne konuştuk") == ("2026-10-15", "2026-10-15") and Z("20 Aralık'ta ne dedim") == ("2025-12-20", "2025-12-20"))
    ok("zaman ifadesi yoksa süzgeç yok", Z("Toplantı kaçta başlıyor?") is None and Z("Dünya kupası ne zaman?") is None)
    r, zr = bg.bellek_ara("Geçen hafta sana ne sormuştum?")
    ok("bellek araması: sözcük kalmayınca aralığın en yeni konuşması", zr and r and r[0][5] == "konusma" and "Fotoğraf" in r[0][4])
    r, zr = bg.bellek_ara("Geçen hafta sana ne sormuştum?", kapsam="ortak"); ok("bellek araması kapsam=ortak: konuşma yok", not r)
    r, zr = bg.bellek_ara("Envanteri neden ekran paylaşımıyla çıkarmaktan vazgeçtik?")
    ok("hatırlama kalıbı (neden vazgeçtik): karar satırı önde", zr is None and r and r[0][5] == "karar" and r[0][2] == "96")
    r, zr = bg.bellek_ara("Envanter dosyası nerede?"); ok("hatırlama/zaman yoksa bellek araması boş", r == [] and zr is None)
    with open(gecmis, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "kisilik": "Matlas", "soru": "Kuş gözlemi için dürbün önerir misin?",
                            "sesli": "Sekiz kırk iki iyi başlangıç.", "ayrinti": "8x42", "toplanti": None}, ensure_ascii=False) + "\n")
    n = bg.gecmis_guncelle(); r, _ = bg.ara("kuş gözlemi dürbün", guncel=False)
    ok("geçmişe eklenen satır tek dosya güncellemesiyle hemen aranır", n == 2 and any(x[5] == "konusma" and "dürbün" in x[4] for x in r))
    # Masaüstü engeli benzeri: proje dışı klasör okunamıyor → kayıtları korunur
    os.chmod(dis, 0)
    try:
        bg.guncelle(c); kalan = c.execute("SELECT count(*) FROM dosya WHERE yol = ?", (os.path.realpath(os.path.join(dis, "urun-defteri.md")),)).fetchone()[0]
        ok("okunamayan bellek klasörü: kayıt korundu, okunamayan listesinde", kalan == 1 and any(e == os.path.realpath(dis) for e in bg.ERISILEMEYEN))
    finally: os.chmod(dis, 0o755)
    import subprocess
    ta = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "ara", "karne toplantı çıktısı"], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).stdout
    tb = subprocess.run([sys.executable, "-B", os.path.join(KOD, "baglam.py"), "ara", "karne toplantı çıktısı"], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).stdout
    ok("toplantı oturumunun araması (tc ara) yalnız ortak: özel karar listesi yok; baglam.py ara'da var", "urun-defteri" not in ta and "urun-defteri" in tb)
    os.remove(os.path.join(dis, "urun-defteri.md")); bg.guncelle(c)
    ok("okunabilen klasörde silinen kaynak dizinden çıkar", not c.execute("SELECT 1 FROM dosya WHERE yol LIKE '%urun-defteri.md'").fetchone())
    # --- aktarıcı bölümü (aktarici/bellek.py), süreçsiz -------------------------------------------------------------------------------------
    kd1, kd2, kart = os.path.join(T, "k1.md"), os.path.join(T, "k2.md"), os.path.join(T, "kart.md")
    open(kd1, "w", encoding="utf-8").write("---\nad: Atlas\nhitap: Atlas\n---\nAdın Atlas. BIRINCI-ISARET\n")
    open(kd2, "w", encoding="utf-8").write("---\nad: Matlas\nhitap: Matlas\nhitap_bicimi: sen\n---\nAdın Matlas. IKINCI-ISARET\n")
    open(kart, "w", encoding="utf-8").write("# Kullanıcı kartı\n## Ortak\n- Sayı bölenle yazılır. [rehber, 29 Eylül]\n## Yalnız Matlas\n- Kuş gözlemi sever. [profil, 17 Ekim]\n")
    yazilan = []
    def write(pairs):
        for y, m in pairs:
            with open(y, "a", encoding="utf-8") as f: f.write(m)
            yazilan.append(y)
    src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
    ns = {"re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "print": lambda *a, **k: LOG.append(" ".join(map(str, a))), "_t": lambda a, b: a,
          "ARAYUZ_DILI": "tr", "BASE": canli, "LOCK": threading.Lock(), "write": write, "TOP": [False], "KONUS": {"soru": None},
          "AYAR": {"kisilik": kd1, "kisilik_toplanti_disi": kd2, "kisilik_bellek": kart}, "_KS": {}, "_ONARA": {"kilit": threading.Lock()}, "_onara_mod": lambda: None}
    LOG = []; ns["toplanti_var"] = lambda: ns["TOP"][0]
    exec(open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read(), ns); exec(src[src.index("KONUS_ISTEM = {"):src.index("# --- Hızlı bilgi")], ns)
    exec(open(os.path.join(KOD, "aktarici", "bellek.py"), encoding="utf-8").read(), ns)
    ist = ns["konus_istem"]()
    ok("istem: kişiliklerden sonra kartın ortak kısmı ve kuralları; 'Yalnız Matlas' bölümü istemde değil", ist.index("IKINCI-ISARET") < ist.index("[Kullanıcı kartı") and "Sayı bölenle" in ist
       and "Kuş gözlemi sever" not in ist and "Kartın 'Yalnız Matlas' bölümü istemde değildir" in ist and "'Bunu bilmiyorum.'" in ist and "Kaynağı ve tarihini yalnız yazılı kısma" in ist and ns["_KS"]["kart_mt"])
    ob = ns["kart_ozel_blok"]("Matlas")
    ok("özel bölüm yalnız o kişiliğe (mesajda): Matlas'ta var, Atlas'ta boş", "Kuş gözlemi sever" in ob and "Sayı bölenle" not in ob and ns["kart_ozel_blok"]("Atlas") == "")
    ns["AYAR"]["kisilik_bellek"] = ""; ok("kart ayarı yokken istemde kart yok", "[Kullanıcı kartı" not in ns["konus_istem"]())
    ns["AYAR"]["kisilik_bellek"] = os.path.join(T, "yok.md"); ok("kart dosyası yokken kartsız, günlükte 'okunamadı'", "[Kullanıcı kartı" not in ns["konus_istem"]() and any("kullanıcı kartı okunamadı" in l for l in LOG))
    ns["AYAR"]["kisilik_bellek"] = kart
    open(kart, "a", encoding="utf-8").write("- Write ile dosya yazdırma.\n"); os.utime(kart, (time.time() + 5, time.time() + 5))
    ok("kartta yardımcının yasak sözcüğü → kart isteme girmez", "[Kullanıcı kartı" not in ns["konus_istem"]() and any("yasak sözcüğü" in l for l in LOG))
    open(kart, "w", encoding="utf-8").write("## Ortak\n" + "- uzun satır [k, 1 Ekim]\n" * 1200); os.utime(kart, (time.time() + 10, time.time() + 10))
    k_ = ns["kullanici_karti"](); ok("uzun kart sınırda kesilir", k_ and len(k_) == ns["KART_EN_COK"] and any("karakter — ilk" in l for l in LOG))
    open(kart, "w", encoding="utf-8").write("## Ortak\n- Sayı bölenle yazılır. [rehber, 29 Eylül]\n## Yalnız Matlas\n- Kuş gözlemi sever. [profil, 17 Ekim]\n"); os.utime(kart, (time.time() + 15, time.time() + 15))
    # kapsam kararı
    K = ns["kisilik"]; at, mt = K("Atlas"), K("Matlas")
    ok("kapsam: toplantı kişiliği, karşı taraf, toplantıya okunan → ortak; toplantı dışı kişilik → hepsi",
       ns["bellek_kapsam"]({}, at) == "ortak" and ns["bellek_kapsam"]({"kaynak": "karsi"}, at) == "ortak" and ns["bellek_kapsam"]({"otonom": True}, mt) == "ortak"
       and ns["bellek_kapsam"]({}, mt) is None and ns["bellek_kapsam"]({"kaynak": "hitap"}, mt) is None)
    # Konuş geçmişi
    os.remove(gecmis); ns["AYAR"]["konus_gecmis"] = True
    ns["konus_gecmis_yaz"]({"kaynak": "bas", "soru": "Yarın ne var?", "kisi": "Matlas"}, "Yarın iki toplantın var.\n---\nSaat 10 ve 14.")
    ns["konus_gecmis_yaz"]({"kaynak": "karsi", "karsi": "Ayla", "soru": "Ayla: özet?"}, "Özet şu.")
    ns["konus_gecmis_yaz"]({"kaynak": "ozet", "soru": "Toplantı bitti"}, "Toplantı özeti: …")
    ns["konus_gecmis_yaz"]({"kaynak": "hitap", "soru": "Matlas, bunu nasıl söylerim?", "kisi": "Matlas", "toplantida": True}, "Kısa söyle.", "Haftalık")
    g = [json.loads(l) for l in open(gecmis, encoding="utf-8")]
    ok("geçmiş: yalnız kullanıcının soruları (karşı taraf ve hızlı özet yok), sesli/ayrıntı ayrı, toplantı adı yalnız toplantıda",
       len(g) == 2 and g[0]["sesli"] == "Yarın iki toplantın var." and g[0]["ayrinti"] == "Saat 10 ve 14." and g[0]["kisilik"] == "Matlas" and g[0]["toplanti"] is None and g[1]["toplanti"] == "Haftalık")
    ok("geçmiş dosyası 0600", stat.S_IMODE(os.stat(gecmis).st_mode) == 0o600)
    ns["AYAR"]["konus_gecmis"] = False; ns["konus_gecmis_yaz"]({"kaynak": "bas", "soru": "Kapalıyken?"}, "Cevap.")
    ok("ayar konus_gecmis: false → yazılmaz", len(open(gecmis, encoding="utf-8").readlines()) == 2); ns["AYAR"].pop("konus_gecmis")
    ok("konus_gecmis ayarı yoksa kart varken açık", ns["konus_gecmis_acik"]())
    eski = json.dumps({"at": "2026-06-01T10:00:00+03:00", "soru": "Eski soru", "sesli": "Eski."}, ensure_ascii=False) + "\n"
    open(gecmis, "a", encoding="utf-8").write(eski)
    n = ns["konus_gecmis_dondur"](datetime.datetime(2026, 10, 17, 12, tzinfo=datetime.timezone.utc))
    ars = os.path.join(canli, "arsiv", "konus-gecmis.jsonl.gz")
    ok("döndürme: 90 günden eski satır arşive (gz, 0600), yenileri kalır", n == 1 and gzip.open(ars, "rt", encoding="utf-8").read() == eski
       and len(open(gecmis, encoding="utf-8").readlines()) == 2 and stat.S_IMODE(os.stat(ars).st_mode) == 0o600 and stat.S_IMODE(os.stat(gecmis).st_mode) == 0o600)
    ok("döndürülecek satır yoksa dokunmaz", ns["konus_gecmis_dondur"](datetime.datetime(2026, 10, 17, 12, tzinfo=datetime.timezone.utc)) == 0)
    # panodaki liste ve silme (v0.67.0)
    lst = ns["konus_gecmis_liste"]()
    ok("geçmiş listesi: en yeni önce, kimlikli, toplam ve gün", lst["ok"] and lst["toplam"] == 2 and lst["kayitlar"][0]["soru"] == "Matlas, bunu nasıl söylerim?" and all(x["id"] for x in lst["kayitlar"]) and lst["gun"] == 90)
    r_ = ns["konus_gecmis_sil"](lst["kayitlar"][1]["id"]); kal = open(gecmis, encoding="utf-8").read()
    ok("silme: yalnız o kayıt çıkar, dosya 0600, bilinmeyen kimlik hata", r_["ok"] and r_["kalan"] == 1 and "Yarın ne var?" not in kal and "nasıl söylerim" in kal
       and stat.S_IMODE(os.stat(gecmis).st_mode) == 0o600 and not ns["konus_gecmis_sil"]("yok")["ok"])
    # sesle düzeltme sırası
    T_ = ns["bellek_sira_turu"]
    ok("sıra kalıpları: hatırla / yanlış / unut", T_("Matlas, bunu hatırla: cuma günleri koşuya gidiyorum.") == "hatirla" and T_("Bu yanlış, toplantı perşembe.") == "yanlis"
       and T_("Bunu unut, artık kullanmıyorum.") == "unut" and T_("Bunu unutma, kahveyi sade içerim.") == "hatirla" and T_("Yanlış biliyorsun, Ankara'da değil.") == "yanlis")
    ok("sıradan soru ve 'hatırlıyor musun' sıra değil", not any(T_(x) for x in ("Geçen hafta ne konuştuk, hatırlıyor musun?", "Yarın ne var?", "Bu sunum doğru mu?", "Unutulan iş var mı?")))
    n_ = ns["bellek_sira"]("Matlas, bunu hatırla: cuma koşuya gidiyorum.", {"kisi": "Matlas"}, mt)
    sira = os.path.join(canli, "bellek-sira.jsonl"); s = [json.loads(l) for l in open(sira, encoding="utf-8")]
    ok("sıra kaydı: tür, metin, önceki soru-cevap, bekliyor; 0600; bağlam notu", s[0]["tur"] == "hatirla" and "cuma" in s[0]["metin"] and s[0]["onceki_soru"] == "Matlas, bunu nasıl söylerim?"
       and s[0]["durum"] == "bekliyor" and stat.S_IMODE(os.stat(sira).st_mode) == 0o600 and "haftalık kart onayında" in n_)
    ok("toplantı kişiliği ve karşı taraf sıraya almaz", ns["bellek_sira"]("Bunu hatırla.", {}, at) == "" and ns["bellek_sira"]("Bunu hatırla.", {"kaynak": "karsi"}, mt) == "" and len(open(sira).readlines()) == 1)
    ns["AYAR"]["kisilik_bellek"] = ""; ok("kart ayarı yokken sıra yok", ns["bellek_sira"]("Bunu hatırla.", {}, mt) == "")
finally:
    if not any(hata): shutil.rmtree(T, ignore_errors=True)
    else: print("(deneme klasörü: " + T + ")")
print("bellek:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
