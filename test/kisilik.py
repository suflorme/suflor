#!/usr/bin/env python3
# Kişilik (v0.53.0, aktarici/kisilik.py) uçtan uca, nötr örnek adla ("Atlas"; gerçek kişilik dosyası depoya girmez): /status konus.kisilik, kullanıcı satırında
# hitap → "Claude:" (karşı kanalda değil), toplantıya söyle'de ilk okumada kişiliğin tanıtımı + telaffuz satırı, ikinci okumada tanıtım yok; Konuş istemine
# kişilik metni (biçim kuralları önce, neşeli ünlem satırı çıkar); kişilik dosyası silinince nötr davranış, hata yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisilik.py
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8789)  # 8793 sohbet testinin
T = tempfile.mkdtemp(prefix="kis-"); canli = os.path.join(T, "canli"); os.makedirs(canli); hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
kd = os.path.join(T, "kisilik.md")
open(kd, "w", encoding="utf-8").write("---\nad: Atlas\nhitap: Atlas, Atlaz\nokunus: Atlas\ntanitim: Merhaba, ben Atlas. Deneme şirketi adına konuşan bir asistanım.\n"
                                      "selam: Merhaba, ben Atlas.\ntelaffuz: Deneme şirketi=Denemee şirketi\n---\n## Kişilik: Atlas\nAdın Atlas. Siz diye hitap edersin. KİŞİLİK-İŞARETİ\n")
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "kisilik": kd, "toplantiya_ses": True}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay,
                     SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_TS_AYGIT="1"), stdout=open(log, "w"), stderr=subprocess.STDOUT)
L = lambda: open(log, encoding="utf-8").read()
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K})
        return json.loads(urllib.request.urlopen(q, timeout=10).read())
    ok("status: konuşma etiketi kişiliğin adı", uc("/status")["konus"].get("kisilik") == "Atlas")
    uc("/ping", {"meeting": {"title": "Kişilik deneme"}, "panel": True})  # çağrı bilgisi yok: BlackHole (deneme) yolu
    uc("/ingest", {"meeting": {"title": "Kişilik deneme"}, "source": "whisper", "entries": [
        {"id": "w/1", "speaker": "Deniz T", "time": "10:00:00", "text": "Atlas, bugün kaç toplantım var?", "kanal": "ben"},
        {"id": "w/2", "speaker": "Deniz T", "time": "10:00:10", "text": "Atlas markasının yeni ürünü güzel olmuş.", "kanal": "ben"},
        {"id": "k/1", "speaker": "Ayla Ö", "time": "10:00:20", "text": "Atlas, bize de bir özet çıkar.", "kanal": "karsi"}]})
    time.sleep(0.5); md = " ".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))
    ok("kullanıcı satırında hitap tanındı (satırda ✎ → ad, soru Konuş'a gitti)", "bugün kaç toplantım var? | ✎ → Atlas" in md and "KONUŞ: Atlas adıyla soruldu (hitap)" in L())
    ok("hitap olmayan cümle değişmedi", "Atlas markasının yeni ürünü güzel olmuş." in md)
    ok("karşı kanaldaki ad hitap sayılmadı", "Atlas, bize de bir özet çıkar." in md and "Claude: bize" not in md)
    uc("/komut", {"tur": "soyle", "metin": "Toplantı yarın onda."})
    s1 = [l for l in L().splitlines() if "TOPLANTIYA SÖYLE (deneme)" in l]
    ok("toplantıya söyle: ilk okumada kişiliğin tanıtımı (telaffuz satırı uygulandı), nötr tanıtım yok",
       bool(s1) and "Merhaba, ben Atlas" in s1[-1] and "Denemee şirketi" in s1[-1] and "asistanı Suflor" not in s1[-1])
    uc("/komut", {"tur": "soyle", "metin": "İkinci cümle."})
    s2 = [l for l in L().splitlines() if "TOPLANTIYA SÖYLE (deneme)" in l]
    ok("ikinci okumada tanıtım yok", len(s2) == 2 and "Merhaba" not in s2[-1])
    # Konuş istemi (aktarıcının kendi tanımları; süreç açılmaz)
    src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read(); ks = open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read()
    import collections; ns = {"re": re, "os": os, "json": json, "time": time, "collections": collections, "print": lambda *a, **k: None, "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": canli, "AYAR": {"kisilik": kd}, "_KS": {}, "TOP": [False]}
    ns["toplanti_var"] = lambda: ns["TOP"][0]
    ns["_onara_mod"] = lambda: None  # v0.121.0: proje_ozeti_istem dilimin dışındaki ön arama modülünü çağırır; proje kartı yok
    exec(ks, ns); exec(src[src.index("KONUS_ISTEM = {"):src.index("# --- Hızlı bilgi")], ns)
    exec(open(os.path.join(KOD, "aktarici", "bellek.py"), encoding="utf-8").read(), ns)  # v0.64.0: istemin sonundaki kullanıcı kartı (ayar yok → boş)
    ist = ns["konus_istem"]()
    ok("Konuş istemi: kişilik metni sonda, biçim kuralları önce, neşeli ünlem satırı çıktı",
       ist.split("\n\nYanlış yazılmış sözcükler")[0].endswith("KİŞİLİK-İŞARETİ") and ist.rstrip().endswith("bilgi sorusunda soru hiç yok.") and "biçim kuralları" in ist.split("## Kişilik")[0][-400:] and "'Vay!'" not in ist and "en çok dört cümle" in ist and "Şey," not in ist)
    # v0.61.0: iki kişilik — toplantı dışı kişilik (ayar kisilik_toplanti_disi), adla seçim, toplantıda yalnız kulağa
    kd2 = os.path.join(T, "kisilik2.md")
    open(kd2, "w", encoding="utf-8").write("---\nad: Matlas\nhitap: Matlas, Oh Matlas\nhitap_bicimi: sen\nselam: Selam, ben Matlas.\ntelaffuz: Sir=sör\n---\n## Kişilik: Matlas\nAdın Matlas. Sen dersin. İKİNCİ-İŞARET\n")
    ns["AYAR"]["kisilik_toplanti_disi"] = kd2
    ist2 = ns["konus_istem"]()
    ok("iki kişilik: istemde ikisi de, açıklama satırı, biçim kuralları önce", "KİŞİLİK-İŞARETİ" in ist2 and ist2.split("\n\nYanlış yazılmış sözcükler")[0].endswith("İKİNCİ-İŞARET") and "\n\nYanlış yazılmış sözcükler" in ist2 and "Aşağıda iki kişilik var: Atlas toplantıda, Matlas toplantı dışında" in ist2)
    ok("adın söylenişleri kuralı: hitap listesi, düzeltme yok, kişilik metninden önce (v0.97.5)", "Adının söylenişleri" in ist2 and "Matlas: Oh Matlas" in ist2
       and "Adını düzeltme" in ist2 and ist2.index("Adının söylenişleri") < ist2.index("## Kişilik"))
    ok("toplantı yokken etkin kişilik ikincisi", ns["kisilik"]()["ad"] == "Matlas")
    ns["TOP"][0] = True; ok("toplantıda etkin kişilik birincisi", ns["kisilik"]()["ad"] == "Atlas")
    kb, kalan = ns["kisilik_hitap_bul"]("Matlas, bugün neler yaptım?"); ok("adla seslenme bulundu", kb and kb["ad"] == "Matlas" and kalan == "bugün neler yaptım?")
    kb, _ = ns["kisilik_hitap_bul"]("Atlas, özet?"); ok("birincinin adı da bulunur", kb and kb["ad"] == "Atlas")
    kb, _ = ns["kisilik_hitap_bul"]("Dün Matlas'la konuştum"); ok("cümle ortası ad seçmez", kb is None)
    kb, kalan = ns["kisilik_hitap_bul"]("Tamam, Matlas, bunu not al."); kb2, k2 = ns["kisilik_hitap_bul"]("Günaydın Atlas."); kb3, _ = ns["kisilik_hitap_bul"]("Tamam Atlas.")
    ok("v0.101.1: giriş sözünden sonra ad; yalnız selam ('Günaydın <ad>.') o kişiliğe soru olarak; selamsız giriş sözü tek başına değil",
       kb and kb["ad"] == "Matlas" and kalan == "bunu not al." and kb2 and kb2["ad"] == "Atlas" and k2 == "Günaydın Atlas." and kb3 is None)
    kb, _ = ns["kisilik_hitap_bul"]("Atlas ile ilgili problem neydi?"); kb2, _ = ns["kisilik_hitap_bul"]("Atlas'ın sesi neden kesildi?")
    ok("19 Ekim: kişilikten söz etmek (ile ilgili, kesmeli ek) o kişiliği seçmez", kb is None and kb2 is None)
    ns["kisilik_sec"]("Matlas"); ok("adla seçilen kişilik toplantıda da sürer (süre içinde)", ns["kisilik"]()["ad"] == "Matlas")
    ok("'sen' diyen kişilikte kis_t nötr cümle", ns["kis_t"]("Söyler misin?", "Söyler misiniz?") == "Söyler misin?")
    ns["_KSEC"]["t"] -= ns["KISILIK_SURE_SN"] + 1; ok("süre dolunca varsayılana döner", ns["kisilik"]()["ad"] == "Atlas")
    ok("'siz' diyen kişilikte kis_t kişilikli cümle", ns["kis_t"]("Söyler misin?", "Söyler misiniz?") == "Söyler misiniz?")
    ok("telaffuz iki kişilikten", ns["kisilik_telaffuz"]("Tamam Sir, Deneme şirketi.") == "Tamam sör, Denemee şirketi.")
    # S94: toplantıda asistanlar — kullanıcı adıyla ilk kez çağırınca katılır, toplantı değişince sıfırlanır
    ns["STATE"] = {"meeting": "T1"}
    ok("S94: asistan adları iki kişilik", ns["asistan_adlari"]() == ["Atlas", "Matlas"])
    ok("S94: toplantı başında katılan yok", ns["asistan_katilan"]() == [])
    ns["asistan_katil"]("Matlas"); ns["asistan_katil"]("Matlas"); ok("S94: çağrılan asistan katılır (bir kez)", ns["asistan_katilan"]() == ["Matlas"])

    # v0.157.0: görünen ad (gorunen_ad) — alan varken görünen ad, yokken iç ad; hitap iç ad + görünen ad ile çalışır
    kd3 = os.path.join(T, "kisilik3.md")
    open(kd3, "w", encoding="utf-8").write("---\nad: ZETA\ngorunen_ad: Kemal\nhitap: ZETA, Zeta\nokunus: \n---\n## Kişilik: ZETA\nAdın ZETA. GORUNEN-İŞARET\n")
    ns3 = {k_: v_ for k_, v_ in ns.items() if k_ in ("re", "os", "json", "time", "collections", "print", "_t", "ARAYUZ_DILI", "BASE", "_KS", "TOP", "toplanti_var")}; ns3["AYAR"] = {"kisilik": kd3}
    exec(ks, ns3)
    ok("görünen ad: alan varken asistan_ad/asistan_adlari görünen ad, iç ad aynı", ns3["asistan_ad"]() == "Kemal" and ns3["asistan_adlari"]() == ["Kemal"] and ns3["kisilik_ad"]() == "ZETA")
    ok("görünen ad: hitap listesinde iç ad, yazılışlar ve görünen ad var", all(a in ns3["kisilik"]()["hitap"] for a in ("ZETA", "Zeta", "Kemal")))
    ok("görünen ad: dökümdeki etiket görünen adla", ns3["asistan_buyuk"]() == "KEMAL" and ns3["asistan_goster"]("Claude: saat kaç") == "Kemal, saat kaç" if "asistan_goster" in ns3 else ns3["asistan_buyuk"]() == "KEMAL")
    ok("görünen ad: okunuş yokken iç ad görünen adla okunur", ns3["kisilik_telaffuz"]("ZETA burada") == "Kemal burada")
    # 3 Kasım: kişisel asistanın görünen adı Marvin, iç adı (dosya, "Yalnız <ad>" bölümü) NOVA; "Marvin," birincil, eski "Nova,"/"NOVA," ve Whisper yazımları hâlâ tanınır
    kd5 = os.path.join(T, "kisilik5.md")
    open(kd5, "w", encoding="utf-8").write("---\nad: NOVA\ngorunen_ad: Marvin\nhitap: Marvin, NOVA, Nova, Novva, Marvın\nokunus: Marvin\n---\n## Kişilik: Marvin\nAdın Marvin. MARVIN-İŞARETİ\n")
    ns5 = {k_: v_ for k_, v_ in ns3.items() if k_ in ("re", "os", "json", "time", "collections", "print", "_t", "ARAYUZ_DILI", "BASE", "_KS", "TOP", "toplanti_var")}; ns5["AYAR"] = {"kisilik": kd, "kisilik_toplanti_disi": kd5}; ns5["_KSEC"] = {"ad": None, "t": 0.0}; ns5["_KIS_TANIT"] = {"yuklendi": False, "adlar": set()}; ns5["_KISILIK"] = {}
    exec(ks, ns5)
    km = ns5["kisilik"]("NOVA"); ok("Marvin: görünen ad Marvin, iç ad NOVA, okunuş Marvin", km and km["gorunen_ad"] == "Marvin" and km["ad"] == "NOVA" and "Marvin" in ns5["asistan_adlari"]() and ns5["kisilik_telaffuz"]("NOVA burada") == "Marvin burada")
    for soz in ("Marvin, bugün ne var?", "Nova, bugün ne var?", "NOVA, bugün ne var?", "Novva, bugün ne var?", "Marvın, bugün ne var?"):
        kb, kalan = ns5["kisilik_hitap_bul"](soz); ok(f"Marvin: «{soz.split(',')[0]},» hitabı tanındı (iç ad NOVA)", kb and kb["ad"] == "NOVA" and kalan == "bugün ne var?")
    kb, _ = ns5["kisilik_hitap_bul"]("Dün Nova'yla konuştum"); ok("Marvin: cümle ortası ad seçmez", kb is None)
    ns4 = dict(ns3); ns4["AYAR"] = {"kisilik": kd2}; ns4["_KSEC"] = {"ad": None, "t": 0.0}; ns4["_KIS_TANIT"] = {"yuklendi": False, "adlar": set()}; ns4["_KISILIK"] = {}; exec(ks, ns4)
    ok("görünen ad: alan yokken iç ad (Matlas)", ns4["asistan_ad"]() == "Matlas" and ns4["asistan_adlari"]() == ["Matlas"])
    ns["STATE"]["meeting"] = "T2"; ok("S94: yeni toplantıda katılım sıfırlanır", ns["asistan_katilan"]() == [])
    ns["TOP"][0] = False; ok("S94: toplantı yokken durum yok", ns["asistan_view"]() is None and ns["asistan_katilan"]() == []); ns["TOP"][0] = True
    # v0.71.0: kişilik başına ses ve hız (brifing-ses.py kisilik_sesi)
    open(kd2, "a", encoding="utf-8").write("")
    s2 = open(kd2, encoding="utf-8").read().replace("hitap_bicimi: sen\n", "hitap_bicimi: sen\nses: Yelda\nhiz: 1,15\n"); open(kd2, "w", encoding="utf-8").write(s2)
    bs = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); i = bs.index("def kisilik_sesi("); exec(bs[i:bs.index("\ndef ses_secimi", i)], ns)
    ns["ses_secimi"] = lambda: None; ns["GEM"] = [False]; ns["gemini_var"] = lambda: ns["GEM"][0]; ns["pocket_var"] = lambda: False; ns["pocket_ses_adi"] = lambda x: None; ns["pocket_varsayilan"] = lambda: "wite:female_2"; ns["gemini_acik"] = lambda: False; ns["gemini_izinli"] = lambda toplantiya=False: ns["GEM"][0] and (toplantiya or ns["AYAR"].get("gemini_kapsam") == "hepsi"); ns["AYAR"].update(piper_python="/x/python", piper_model="/x/m.onnx"); ns["_KSEC"].update(ad=None, t=0)
    ns["TOP"][0] = False; ok("toplantı dışı kişilik: Mac sesi Yelda, hız 1,15", ns["kisilik_sesi"]() == ("mac", "Yelda", 1.15))
    ns["TOP"][0] = True; ok("toplantı kişiliği: sistem sesi, hız 1", ns["kisilik_sesi"]() == ("mac", None, 1.0))
    ns["TOP"][0] = False
    ok("Mac ses adı verilirse o ses", ns["kisilik_sesi"]() == ("mac", "Yelda", 1.15))
    # v0.78.0: kişilikte Gemini sesi ("gemini:Kore"); anahtar yoksa Mac sesi (ses adı Mac'e gitmez)
    open(kd2, "w", encoding="utf-8").write(s2.replace("ses: Yelda", "ses: gemini:Kore")); os.utime(kd2, (time.time() + 10, time.time() + 10))
    ns["GEM"][0] = True; ns["AYAR"]["gemini_kapsam"] = "hepsi"; ok("kişilikte gemini:Kore → Gemini, Kore (kapsam hepsi)", ns["kisilik_sesi"]() == ("gemini", "Kore", 1.15))
    ns["AYAR"].pop("gemini_kapsam"); ok("S92: kapsam toplantı → kullanıcıya okunan Mac sistem sesi", ns["kisilik_sesi"]() == ("mac", None, 1.15))
    ok("S92: toplantıya söylenen Gemini, Kore", ns["kisilik_sesi"](toplantiya=True) == ("gemini", "Kore", 1.15))
    ns["AYAR"]["ses_hizi"] = "1.2"; ok("v0.110.0: Okuma hızı Mac sesinde kişilik hızıyla çarpılır, Gemini'de değil", abs(ns["kisilik_sesi"]()[2] - 1.38) < 1e-9 and ns["kisilik_sesi"](toplantiya=True)[2] == 1.15)
    ns["AYAR"].pop("ses_hizi")
    ns["AYAR"]["ses_motoru"] = "mac"; ok("S92: Ayarlar'da Mac sesi seçiliyse Elif (sistem sesi)", ns["kisilik_sesi"]() == ("mac", None, 1.15))
    ns["AYAR"]["ses_motoru"] = "gemini"; ok("S92: Ayarlar'da Gemini seçiliyken toplantı dışı Mac sesi", ns["kisilik_sesi"]() == ("mac", None, 1.15)); ns["AYAR"].pop("ses_motoru")
    ns["GEM"][0] = False; ok("Gemini anahtarı yoksa Mac sistem sesi", ns["kisilik_sesi"]() == ("mac", None, 1.15))
    # v0.79.0: ses üslubu ve sözsüz ses etiketleri (yalnız Gemini sesli, ses_etiket: evet kişilikte; istemde yalnız onun adı)
    open(kd2, "w", encoding="utf-8").write(s2.replace("ses: Yelda", "ses: gemini:Kore\nses_uslup: nüktedan, dostça\nses_uslup_en: witty, friendly\nses_etiket: evet")); os.utime(kd2, (time.time() + 15, time.time() + 15))
    ns["GEM"][0] = True; kk = ns["kisilik"]()
    ok("kişilik alanları: ses_uslup, ses_uslup_en, ses_etiket", kk["ses_uslup"] == "nüktedan, dostça" and kk["ses_uslup_en"] == "witty, friendly" and kk["ses_etiket"] is True)
    ist3 = ns["konus_istem"](); ok("istemde etiket kuralı yalnız etiketli kişiliğe", "[Ses etiketleri] Matlas sesli kısımda" in ist3 and "<chuckle>" in ist3 and "Öteki kişilik etiket kullanmaz" in ist3)
    # v0.96.2: toplantı dışında Gemini kapalıyken (kapsam toplanti) yerel ses okur → o cevapta etiket yok; toplantıya okunan (otonom) cevapta etiket serbest
    etn = ns["_etiket_tur_notu"]; ns["AYAR"].pop("gemini_kapsam", None)
    ok("v0.96.2: toplantı dışı, Gemini yalnız toplantıda → 'etiket kullanma' notu", "ses etiketi" in etn({"sesli": True}))
    ok("v0.96.2: toplantıya okunan cevap (Gemini) → not yok", etn({"otonom": True, "sesli": False}) == "")
    ns["AYAR"]["gemini_kapsam"] = "hepsi"; ok("v0.96.2: Gemini her yerde açık → not yok", etn({"sesli": True}) == "")
    ok("v0.96.2: kulaklık yok (yalnız pano) → not var", "ses etiketi" in etn({"sesli": False})); ns["AYAR"].pop("gemini_kapsam")
    ns["GEM"][0] = False; ok("Gemini anahtarı yoksa etiket kuralı yok", "[Ses etiketleri]" not in ns["konus_istem"]())
    # v0.122.1: takvim: soruya — takvim bağlamı yalnız zamanla/takvimle ilgili soruda ya da toplantı yakınsa (alanı olmayan toplantı kişiliğinde her soruda)
    import datetime; ns["datetime"] = datetime; kd3 = os.path.join(T, "kisilik3.md")
    open(kd3, "w", encoding="utf-8").write("---\nad: Rüzgar\ntakvim: soruya\n---\nAdın Rüzgar.\n"); k3 = ns["_kisilik_oku"](kd3, "disi"); tg = ns["kisilik_takvim_gerek"]
    simdi = datetime.datetime(2026, 10, 23, 19, 50).astimezone(); YAK = [None]; ns["_sonraki_toplanti"] = lambda s_: YAK[0]
    ok("takvim: soruya okundu", k3["takvim"] == "soruya" and ns["_kisilik_oku"](kd, "toplanti")["takvim"] == "her")
    ok("sohbet, espri, moral sorusunda takvim yok", not any(tg(q, simdi, k3) for q in ("Dostum burada mısın?", "Sadece sesini duymak istedim.", "Akşam yemeğinde ne önerirsin?",
       "Bugün çok yoruldum, moralim bozuk.", "Bana bir fıkra anlat.", "Bu projede eleştirilecek bir şey söyle.")))
    ok("takvim sorusunda takvim var", all(tg(q, simdi, k3) for q in ("Yarın ne var?", "Takvimimde bu hafta ne var?", "Bir sonraki toplantım ne zaman?",
       "Perşembe öğleden sonra müsait miyim?", "Dünkü görüşmede ne konuştuk?", "What's on my calendar tomorrow?")))
    ok("v0.125.1: plan sözcüğü yalnız soran cümlede ('Yarın için … planım yok' takvim değil; 'Yarın planım ne?' takvim)",
       not tg("Yarın için işle ilgili bir planım yok ama ailemle beraber vakit geçirmek istiyorum.", simdi, k3) and not tg("Hafta sonu programım belli değil, bakarız.", simdi, k3)
       and tg("Yarın planım ne?", simdi, k3) and tg("Bu akşam programım var mı?", simdi, k3))
    YAK[0] = (simdi + datetime.timedelta(minutes=10), simdi + datetime.timedelta(minutes=40), {})
    ok("toplantı 10 dk sonra: sohbette de takvim var", tg("Dostum burada mısın?", simdi, k3))
    YAK[0] = (simdi + datetime.timedelta(minutes=90), simdi + datetime.timedelta(minutes=120), {})
    ok("toplantı 90 dk sonra: sohbette takvim yok", not tg("Dostum burada mısın?", simdi, k3))
    ok("alanı olmayan kişilikte her soruda takvim (toplantı kişiliği aynı)", tg("Bana bir fıkra anlat.", simdi, ns["_kisilik_oku"](kd, "toplanti")))
    # konus_baglam uçtan uca: alanı olmayan kişilik her soruda takvim satırı, takvim: soruya olan yalnız zaman/takvim sorusunda; yer tutucu satır yok
    i0 = src.index("# --- Takvim haftası ve uygun zaman"); i1 = src.index("def _konus_kur(")
    ns.update(_zaman=lambda t: datetime.datetime.fromisoformat(str(t)).astimezone(), STATE={"takvim": {"durum": "ok"}}, TAKVIM_GEC={"olaylar": []}, SON=[], ben_adi=lambda: "Deniz T",
              TAKVIM_TAM={"e1": {"baslik": "Bütçe sunumu", "baslangic": (simdi + datetime.timedelta(days=1)).isoformat(), "bitis": (simdi + datetime.timedelta(days=1, hours=1)).isoformat()}})
    kis0 = ns["kisilik"]; exec(src[i0:i1], ns); ns["_sonraki_toplanti"] = lambda s_: None; KB = ns["konus_baglam"]
    ns["kisilik"] = lambda ad=None: ns["_kisilik_oku"](kd, "toplanti")
    ok("konus_baglam: alanı olmayan kişilikte sohbette de takvim", "Bütçe sunumu" in KB(simdi, "", "Bana bir fıkra anlat."))
    ns["kisilik"] = lambda ad=None: k3
    b1, b2 = KB(simdi, "", "Bana bir fıkra anlat."), KB(simdi, "", "Yarın ne var?")
    ok("konus_baglam: takvim: soruya — sohbette takvim yok, yer tutucu da yok, saat var", "Takvim" not in b1 and "Bütçe" not in b1 and "Şimdi:" in b1)
    ok("konus_baglam: takvim: soruya — takvim sorusunda takvim var", "Mac Takvim" in b2 and "Bütçe sunumu" in b2)
    ns["kisilik"] = kis0; ns.pop("_sonraki_toplanti")
    # Kişilik seçimi: tek başına ad çağırır, seçim nedeni günlükte
    import collections, threading, random; ns.update(collections=collections, threading=threading, datetime=datetime); random.seed(7)
    ns["AYAR"]["ad"] = "Deniz T"; ns["TOP"][0] = False; ns["_KSEC"].update(ad=None, t=0)
    kb, _ = ns["kisilik_hitap_bul"]("Matlas?"); kb2, _ = ns["kisilik_hitap_bul"]("Matlas"); kb3, _ = ns["kisilik_hitap_bul"]("Tamam Atlas.")
    ok("hitap: tek başına ad ('<Ad>?') o kişiliği çağırır; giriş sözü + ad yine değil", kb and kb["ad"] == "Matlas" and kb2 and kb2["ad"] == "Matlas" and kb3 is None)
    pr0 = ns["print"]; GL = []; ns["print"] = lambda *a, **k: GL.append(" ".join(map(str, a)))
    ns["_KSEC"].update(ad=None, t=0); ns["kisilik_sec"]("Matlas"); ns["print"] = pr0
    ok(f"günlük: seçim nedeni doğru ({[x for x in GL if 'KİŞİLİK' in x]})", "KİŞİLİK: bu soru Matlas ile (adıyla seslenildi)" in GL)
    ns["AYAR"].pop("ad", None)
    ns["TOP"][0] = False; ns["AYAR"]["kisilik_toplanti_disi"] = ""
    ok("ikinci kaldırılınca tek kişilik (eski istem)", ns["konus_istem"]().split("\n\nYanlış yazılmış sözcükler")[0].endswith("KİŞİLİK-İŞARETİ") and ns["kisilik"]()["ad"] == "Atlas")
    ns["AYAR"]["kisilik"] = ""; ok("kişilik yokken istem nötr (ünlem satırı yerinde)", "'Vay!'" in ns["konus_istem"]() and "KİŞİLİK-İŞARETİ" not in ns["konus_istem"]())
    # kişilik dosyası silinince nötr
    os.remove(kd); time.sleep(0.2)
    ok("dosya silinince status nötr", uc("/status")["konus"].get("kisilik") is None)
    uc("/ingest", {"meeting": {"title": "Kişilik deneme"}, "source": "whisper", "entries": [{"id": "w/3", "speaker": "Deniz T", "time": "10:01:00", "text": "Atlas, yarın ne var?", "kanal": "ben"}]})
    time.sleep(0.5); md = " ".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))
    ok("dosya silinince ad hitap sayılmıyor, günlükte 'KİŞİLİK: okunamadı'", "Atlas, yarın ne var?" in md and "KİŞİLİK: okunamadı" in L())
    ok("seslenme listesi: kısa/gündelik sözcük atılır, adı içeren öbek kalır", ns["hitap_suz"](["Atlas", "Oh", "evet", "Oh Atlas", "At"], "Atlas") == ["Atlas", "Oh Atlas"])
    ok("aktarıcıda hata yok", "Traceback" not in L())
finally:
    r.terminate(); r.wait(5)
    if not any(hata): shutil.rmtree(T, ignore_errors=True)
    else: print("(deneme klasörü: " + T + ")")
print("kişilik:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
