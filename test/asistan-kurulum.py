# Sihirbazın asistan adımı (S133): kurulum.py asistan_uygula/asistan_dosya/asistan_durum — kişilik dosyası, ayar bağlantısı, var olan dosyaya dokunmama,
# atlama, iki asistan, Pocket sesi, var olan asistanda yalnız değişen alan (S135), arka plandaki yapay zekâ adının metinde geçmemesi. Yazılan dosya aktarıcının ayrıştırıcısıyla (aktarici/kisilik.py) okunur.
# Deneme kipinde (SUFLOR_EV: geçici ev klasörü; gerçek ayara dokunmaz). Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/asistan-kurulum.py
import os, sys, json, re, tempfile, shutil, importlib.util, time
KOD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV = tempfile.mkdtemp(prefix="asistan-"); os.environ["SUFLOR_EV"] = EV; sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("kurulum", os.path.join(KOD, "kurulum.py")); K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
ns = {"os": os, "re": re, "time": time, "AYAR": {}, "print": lambda *a, **k: None}
exec(open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read(), ns)
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
def oku(yol): ns["_KIS_D"].clear(); return ns["_kisilik_oku"](K.gen(yol), "toplanti")
try:
    a = {"ad": "Ayşe Yılmaz"}
    adlar = K.asistan_uygula(a, {"asistan": {"liste": [{"ad": "Defne", "bicim": "siz", "tarz": "olculu", "ses": "mac"}]}}, "tr")
    v = oku(a.get("kisilik", ""))
    kontrol("tek asistan: dosya yazıldı, ayar kisilik bağlandı, ikinci ayar yok", adlar == ["Defne"] and a["kisilik"] == "~/Library/Application Support/Suflor/kisilik/defne.md" and "kisilik_toplanti_disi" not in a)
    kontrol("aktarıcı okuyor: ad, hitap, siz, tanıtım kullanıcı adıyla", v and v["ad"] == "Defne" and "Defne" in v["hitap"] and v["bicim"] == "siz" and "Ayşe Yılmaz adına" in v["tanitim"])
    kontrol("kişilik metninde arka plandaki yapay zekâ adı yok; model sorusuna cevap var", "claude" not in open(K.gen(a["kisilik"]), encoding="utf-8").read().lower() and "Bunu söyleyemem" in v["metin"])
    kontrol("ölçülü tarz metinde, Mac sesinde ses satırı yok", "Ton (ölçülü)" in v["metin"] and not v["ses"] and not v["yerel_ses"])
    # var olan dosya: üzerine yazılmaz
    yol = K.gen(a["kisilik"]); open(yol, "a", encoding="utf-8").write("ELLE EKLENDİ\n")
    a2 = {"ad": "Ayşe Yılmaz"}; K.asistan_uygula(a2, {"asistan": {"liste": [{"ad": "defne", "bicim": "sen", "tarz": "rahat"}]}}, "tr")
    kontrol("aynı adlı dosya varsa üzerine yazılmaz, ayar ona bağlanır", a2["kisilik"] == a["kisilik"] and "ELLE EKLENDİ" in open(yol, encoding="utf-8").read())
    # iki asistan
    a3 = {"ad": "Ayşe Yılmaz", "kisilik_toplanti_disi": "~/eski.md"}
    adlar = K.asistan_uygula(a3, {"asistan": {"iki": True, "liste": [{"ad": "Çınar", "tarz": "olculu"}, {"ad": "Işık", "bicim": "sen", "tarz": "rahat"}]}}, "tr")
    v1, v2 = oku(a3["kisilik"]), oku(a3["kisilik_toplanti_disi"])
    kontrol("iki asistan: kisilik + kisilik_toplanti_disi, dosya adı Türkçe harfsiz", adlar == ["Çınar", "Işık"] and a3["kisilik"].endswith("/cinar.md") and a3["kisilik_toplanti_disi"].endswith("/isik.md"))
    kontrol("ikinci asistan: sen, rahat tarz, selam 'seninle', hitapta harfsiz yazım", v2["bicim"] == "sen" and "Ton (rahat)" in v2["metin"] and "seninle" in v2["selam"] and "Isik" in v2["hitap"] and v1["bicim"] == "siz")
    a4 = {"ad": "Ayşe", "kisilik": "~/x.md", "kisilik_toplanti_disi": "~/y.md"}
    K.asistan_uygula(a4, {"asistan": {"iki": False, "liste": [{"ad": "Defne"}, {"ad": "Işık"}]}}, "tr")
    kontrol("tek asistana dönünce toplantı dışı ayarı kalkar", a4["kisilik"].endswith("/defne.md") and "kisilik_toplanti_disi" not in a4)
    a5 = {"ad": "Ayşe"}; K.asistan_uygula(a5, {"asistan": {"iki": True, "liste": [{"ad": "Defne"}, {"ad": "DEFNE"}]}}, "tr")
    kontrol("iki asistana aynı ad: yalnız ilki bağlanır", a5["kisilik"].endswith("/defne.md") and "kisilik_toplanti_disi" not in a5)
    # atla / geçersiz ad
    a6 = {"ad": "Ayşe", "kisilik": "~/var.md"}
    kontrol("atlanırsa ayara dokunulmaz", K.asistan_uygula(a6, {"asistan": {"atla": True, "liste": [{"ad": "Defne"}]}}, "tr") == [] and a6["kisilik"] == "~/var.md")
    kontrol("Suflor adı ve rakamlı ad reddedilir", K.asistan_uygula({"ad": "A"}, {"asistan": {"liste": [{"ad": "Suflor"}]}}, "tr") == [] and K.asistan_ad_temiz("R2D2") is None and K.asistan_ad_temiz(" Defne  Su ") == "Defne Su")
    # Pocket sesi (kurulu gibi davran)
    gercek = K.pocket_kurulu; K.pocket_kurulu = lambda a=None: True
    a7 = {"ad": "Ayşe"}; K.asistan_uygula(a7, {"asistan": {"iki": True, "liste": [{"ad": "Nehir", "ses": "kadin"}, {"ad": "Kaya", "ses": "mac"}]}}, "tr")
    v1, v2 = oku(a7["kisilik"]), oku(a7["kisilik_toplanti_disi"])
    kontrol("Pocket kadın sesi: yerel_ses wite:female_2, motor pocket; öbürü Mac'te kalır", v1["yerel_ses"] == "pocket:wite:female_2" and a7.get("ses_motoru") == "pocket" and v2["yerel_ses"] == "mac")
    a8 = {"ad": "Ayşe", "ses_motoru": "gemini"}; K.asistan_uygula(a8, {"asistan": {"liste": [{"ad": "Deniz", "ses": "erkek"}]}}, "tr")
    kontrol("ses motoru seçiliyse (gemini) değişmez; erkek sesi male_1", a8["ses_motoru"] == "gemini" and oku(a8["kisilik"])["yerel_ses"] == "pocket:wite:male_1")
    K.pocket_kurulu = lambda a=None: False
    a9 = {"ad": "Ayşe"}; K.asistan_uygula(a9, {"asistan": {"liste": [{"ad": "Ege", "ses": "kadin"}]}}, "tr")
    kontrol("Pocket kurulu değilse Mac sesi, motor yazılmaz", not oku(a9["kisilik"])["yerel_ses"] and "ses_motoru" not in a9)
    # var olan asistan (S135): yalnız sihirbazda değişen alan güncellenir, önce .bak yedeği; değişmeyen dosya bayt bayt aynı
    import glob
    oz = os.path.join(K.KISILIK_DIR, "nova.md")
    OZ = ("---\nad: NOVA\nhitap: NOVA, Nova\nokunus: Nova\ntanitim: Merhaba, ben NOVA.\nselam: Merhaba, ben NOVA. Bundan sonra sizinle ben konuşacağım.\n"
          "telaffuz: Kahve=Kahfe\nses: gemini:Kore\nyerel_ses: pocket:alperiox:female_2\nhiz: 1,0\n---\n## Kişilik: NOVA\nHitap: \"siz\" dersin. Özel kural.\nTon: elle yazılmış ton.\n")
    open(oz, "w", encoding="utf-8").write(OZ); bak = lambda y: glob.glob(y + ".bak-*")
    K.pocket_kurulu = lambda a=None: False
    d0 = K._kis_oku(oz); x0 = {"ad": "NOVA", "bicim": "siz", "tarz": d0["tarz"], "ses": K._kis_ses(d0)}
    K.asistan_uygula({"ad": "Ayşe"}, {"asistan": {"liste": [x0]}}, "tr")
    kontrol("var olan asistan, değişiklik yok: dosya bayt bayt aynı, yedek yok", open(oz, encoding="utf-8").read() == OZ and not bak(oz))
    K.asistan_uygula({"ad": "Ayşe"}, {"asistan": {"liste": [dict(x0, tarz="rahat", ses="erkek")]}}, "tr")
    kontrol("Pocket ne kurulu ne istenmiş + elle yazılmış ton: erkek sesi ve tarz uygulanmaz, dosya aynı", open(oz, encoding="utf-8").read() == OZ and not bak(oz))
    K.asistan_uygula({"ad": "Ayşe"}, {"asistan": {"liste": [dict(x0, bicim="sen")]}}, "tr")
    yeni = open(oz, encoding="utf-8").read()
    kontrol("yalnız hitap değişti: hitap_bicimi sen, Hitap satırı ve selam 'sen'; telaffuz, gemini ve yerel ses aynı; .bak yedeği eski hâl",
            "hitap_bicimi: sen" in yeni and 'Hitap: "sen" dersin. Özel kural.' in yeni and "seninle ben konuşacağım" in yeni and "telaffuz: Kahve=Kahfe" in yeni
            and "ses: gemini:Kore" in yeni and "yerel_ses: pocket:alperiox:female_2" in yeni and "Ton: elle yazılmış ton." in yeni
            and len(bak(oz)) == 1 and open(bak(oz)[0], encoding="utf-8").read() == OZ and oku("~" + oz[len(EV):])["bicim"] == "sen")
    ky = K.gen(a7["kisilik_toplanti_disi"]); kd = open(ky, encoding="utf-8").read()  # Kaya: sihirbazın yazdığı, Mac sesi (yerel_ses: mac)
    K.pocket_kurulu = lambda a=None: True
    a11 = {"ad": "Ayşe"}; K.asistan_uygula(a11, {"asistan": {"liste": [{"ad": "Kaya", "bicim": "siz", "tarz": "rahat", "ses": "erkek"}]}}, "tr")
    kk = open(ky, encoding="utf-8").read()
    kontrol("ses Mac'ten Pocket'a (+ tarz): yerel_ses wite:male_1, ton satırı rahat, motor pocket; geri kalan aynı",
            "yerel_ses: pocket:wite:male_1" in kk and "yerel_ses: mac" not in kk and "Ton (rahat)" in kk and "Ton (ölçülü)" not in kk and a11.get("ses_motoru") == "pocket"
            and kk.count("\n") == kd.count("\n") and len(bak(ky)) == 1)
    K.pocket_kurulu = gercek
    # İngilizce kurulum
    a10 = {"ad": "Jane Doe"}; K.asistan_uygula(a10, {"asistan": {"liste": [{"ad": "Robin", "tarz": "rahat"}]}}, "en")
    v = oku(a10["kisilik"])
    kontrol("İngilizce: metin ve tanıtım İngilizce", v["metin"].startswith("## Persona: Robin") and "Tone (relaxed)" in v["metin"] and "on behalf of Jane Doe" in v["tanitim"])
    # sihirbazı doldurmak için durum
    os.makedirs(os.path.dirname(K.AYAR_YOL), exist_ok=True); json.dump(a3, open(K.AYAR_YOL, "w"))
    d = K.asistan_durum()
    kontrol("asistan_durum: bağlı iki asistan sihirbaza döner", d["toplanti"]["ad"] == "Çınar" and d["disi"] == {"ad": "Işık", "bicim": "sen", "tarz": "rahat", "ses": "mac"} and "pocket" in d)
    # tamamla: ayar + Whisper terimi
    json.dump({"ad": "Ayşe Yılmaz", "whisper_terimler": ["Jira"]}, open(K.AYAR_YOL, "w"))
    s = K.tamamla({"ad": "Ayşe Yılmaz", "proje": EV + "/Suflor", "asistan": {"liste": [{"ad": "Defne"}]}}, "tr")
    ay = json.load(open(K.AYAR_YOL))
    kontrol("tamamla: ayara kisilik yazıldı, ad Whisper terimlerinin başında", s["ayar"] == "iyi" and ay.get("kisilik", "").endswith("/defne.md") and ay["whisper_terimler"][:2] == ["Defne", "Jira"])
    json.dump({"ad": "Ayşe Yılmaz"}, open(K.AYAR_YOL, "w"))
    K.tamamla({"ad": "Ayşe Yılmaz", "proje": EV + "/Suflor"}, "tr")
    kontrol("asistan adımı hiç görülmeden tamamla: kişilik yazılmaz (Suflor kalır)", "kisilik" not in json.load(open(K.AYAR_YOL)))
finally:
    shutil.rmtree(EV, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}")
sys.exit(0 if all(ok) else 1)
