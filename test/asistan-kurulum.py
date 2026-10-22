# Sihirbazın asistan adımı (S133): kurulum.py asistan_uygula/asistan_dosya/asistan_durum — kişilik dosyası, ayar bağlantısı, var olan dosyaya dokunmama,
# atlama, iki asistan, Pocket sesi, arka plandaki yapay zekâ adının metinde geçmemesi. Yazılan dosya aktarıcının ayrıştırıcısıyla (aktarici/kisilik.py) okunur.
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
