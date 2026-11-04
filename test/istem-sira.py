#!/usr/bin/env python3
# Whisper istemi önem sırası (aktarici/whisper-hat.py istem_siralama, v0.162.4): 120 yapay terimle bu toplantının kişileri ve asistanın adı/hitabı
# düşük sıklıkta olsa da istemde kalır, istem 223 belirteç sınırının altında kalır (işçinin istem_kur'u gerçek belirteçleyiciyle); tekrar (büyük-küçük harf/aksan),
# küçük harfli terim ve çok sözcüklü terimde zaten geçen tek sözcük girmez. 4 Kasım (sözlük 4. aşama): kullanım kaydıyla puanlı seçim — bağlam, bu toplantıda geçen,
# yakınlık/sıklık, yaşlandırma (elle eklenen ve yeni öğrenilen yaşlanmaz), kayıt yoksa eski sıra, 215 belirteç sınırı. Model yüklenmez (yalnız belirteçleyici; whisper-venv yoksa atlanır, ~2 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/istem-sira.py      (kaldı → çıkış 1)
import ast, datetime, importlib.util, json, math, os, re, sqlite3, sys, tempfile, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = "/Users/Shared/Suflor/whisper-venv/bin/python"
if not os.path.exists(VENV): print("whisper-venv yok — atlandı"); sys.exit(0)
if sys.executable != VENV: os.execv(VENV, [VENV, "-I", os.path.abspath(__file__)])
ns = {"re": re, "math": math, "datetime": datetime, "json": json, "os": os, "time": time, "BEN_ESKI": {"ben", "kullanici"}, "AYAR": {}}
agac = ast.parse(open(os.path.join(KOD, "aktarici/whisper-hat.py"), encoding="utf-8").read())
AD = {"_TRSD", "_sd", "_istem_kisi", "istem_siralama", "ISTEM_KAT_ADLARI", "ISTEM_PUAN", "ISTEM_YASI_GUN", "ISTEM_YENI_GUN", "istem_elle", "_istem_gun", "istem_puan",
      "_ISTEM_KUL", "_istem_kayit", "_istem_canli", "_istem_baglam", "ISTEM_BAGLAM_DISI", "istem_kullanim", "ISTEM_SECIM_VARSAYILAN", "_istem_pay", "ISTEM_SOZLUK_TABAN", "ISTEM_SIK_ONCE"}
exec(compile(ast.Module([n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in AD) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in AD for x in n.targets))], []), "whisper-hat.py", "exec"), ns)
sp = importlib.util.spec_from_file_location("whisper_isci", os.path.join(KOD, "whisper-isci.py")); WI = importlib.util.module_from_spec(sp); sp.loader.exec_module(WI)
from mlx_whisper.tokenizer import get_tokenizer
tok = get_tokenizer(multilingual=True, num_languages=100)
hatalar = []
def kontrol(ad, kosul, ek=None):
    print(("✓ " if kosul else "✗ ") + ad + ("" if kosul or ek is None else f"  — {ek}"))
    if not kosul: hatalar.append(ad)
# 120 yapay sözlük terimi: hepsi sık (dökümde çok geçer), kişi ve asistan adları dökümde HİÇ geçmez (düşük sıklık)
ter = [{"dogru": f"Zeta{i}Sistemi", "yanlis": [f"zeta {i} sistemi"], "kaynak": "otomatik", "kip": "duzelt"} for i in range(120)]
ter += [{"dogru": "kucukterim", "yanlis": [], "kaynak": "ben"}, {"dogru": "Zeta7Sistemi", "yanlis": ["zeta7"], "kaynak": "ben"}]
dokum = " ".join(f"zeta{i}sistemi" for i in range(120) for _ in range(5 + i % 7))
ks = [{"ad": "ASISTANX", "gorunen_ad": "Orhan", "hitap": ["Orhan", "ASISTANX", "Orhanin", "Orchan", "Orhaan", "Organ", "Orhun"]}]
kisiler = ["Ayşe Yıldırım (Konuk)", "Bora Çelik", "ayse yildirim", "Cem Özkaya", "Defne Arslan", "Emre Şahin", "Işıl Tuna", None, ""]
ag = {"title": "Planlama NOVA toplantısı", "items": ["VeriAmbari maliyeti", "Q4 hedefleri"]}
sira = ns["istem_siralama"](ter, ag, [], ks, kisiler, ["AWS", "Google Workspace"], dokum, "Deniz K")
terimler = [t for _, t in sira]; kat = [k for k, _ in sira]
metin = ", ".join(terimler) + "."
istem, dusen = WI.istem_kur(tok, metin, "")
kalan = [t for t in terimler[:len(terimler) - dusen]]
kontrol(f"istem sınırın altında ({len(tok.encode(' ' + istem))} ≤ {WI.ISTEM_SINIR} belirteç)", len(tok.encode(" " + istem)) <= WI.ISTEM_SINIR)
kontrol(f"önceki metinle de sınırın altında", len(tok.encode(" " + (WI.istem_kur(tok, metin, "bir iki üç " * 30)[0] or ""))) <= WI.ISTEM_SINIR)
kontrol("120 terimin hepsi sığmaz (düşenler var)", dusen > 0)
kontrol("asistan görünen ad ve ad önde, hitap yazımı en çok 2 (çekimli «Orhanin» ve aynı kökler girmez)", kalan[:2] == ["Orhan", "ASISTANX"] and "Orhanin" not in terimler and "Orhaan" not in terimler and kat[:4] == ["asistan"] * 4 and kat[4] == "kişi")
kontrol("kök benzeri bozuk hitap yazımları girmez (≤ 2 hitap)", sum(1 for k in kat if k == "asistan") <= 4)
for ad in ("Ayşe Yıldırım", "Bora Çelik", "Cem Özkaya", "Işıl Tuna", "Deniz K"): kontrol(f"kişi istemde: {ad}", ad in kalan)
kontrol("e-posta/parantez ve tekrar (ayse yildirim) kişiye girmez", not any("@" in t or "(" in t or t == "ayse yildirim" for t in terimler))
kontrol("kişiler terimlerden önce", max(i for i, k in enumerate(kat) if k == "kişi") < min(i for i, k in enumerate(kat) if k in ("sık", "sözlük")))
kontrol("gündem terimleri (NOVA, VeriAmbari) kişiden sonra, sözlükten önce", {"NOVA", "VeriAmbari"} <= set(terimler[:len(kalan)]) and max(i for i, k in enumerate(kat) if k == "kişi") < terimler.index("NOVA") < min(i for i, k in enumerate(kat) if k == "sık"))
kontrol("küçük harfli sözlük terimi girmez", "kucukterim" not in terimler)
kontrol("sıklığı yüksek sözlük adı düşüğünden önce", terimler.index("Zeta5Sistemi") < terimler.index("Zeta0Sistemi") if "Zeta0Sistemi" in terimler else True)
kontrol("aynı terim bir kez (Zeta7Sistemi)", terimler.count("Zeta7Sistemi") == 1)
# kalabalık toplantı: > 8 kişide yalnız ilk ad
s2 = ns["istem_siralama"]([], {}, [], [], [f"Kişi{chr(65 + i)} Soyad{chr(65 + i)}" for i in range(12)], [], "", "")
kontrol("12 kişide ilk ad (kısa biçim)", all(" " not in t for _, t in s2) and len(s2) == 12)
# çok sözcüklü terimde zaten geçen tek sözcük
s3 = ns["istem_siralama"]([{"dogru": "Google Workspace", "yanlis": ["g suite"], "kaynak": "ben"}, {"dogru": "Workspace", "yanlis": ["workspeys"], "kaynak": "ben"}], {}, [], [], [], [], "", "")
kontrol("«Workspace» «Google Workspace» varken ayrıca girmez", [t for _, t in s3] == ["Google Workspace"])
# --- 4 Kasım: kullanım kaydıyla puanlı seçim (kul) ---------------------------------------------------------------------------------------------------------------------------
B = datetime.date(2026, 6, 15); G = lambda n: (B - datetime.timedelta(days=n)).isoformat(); sd = ns["_sd"]
def kul_(kay, canli=(), baglam=(), yas=60): return {"terimler": kay, "bugun": B, "canli": frozenset(sd(x) for x in canli), "baglam": frozenset(sd(x) for x in baglam), "yas_gun": yas}
def sigan(sira, onceki=""):
    ts = [t for _, t in sira]; ist, d = WI.istem_kur(tok, ", ".join(ts) + ".", onceki); return ts[:len(ts) - d], ist
ter2 = [{"dogru": f"Kappa{i}Modul", "yanlis": [], "kaynak": "proje-karti"} for i in range(120)]
kay = {f"Kappa{i}Modul": {"son": G(100), "toplanti_sayisi": 1, "ilk": G(200)} for i in range(120)}  # hepsi yaşlı (100 gün önce)
for i in range(0, 30): kay[f"Kappa{i}Modul"] = {"son": G(i % 50), "toplanti_sayisi": 1 + i % 4, "ilk": G(200)}  # 30'u yakında kullanıldı
ter2 += [{"dogru": "Lumora", "yanlis": [], "kaynak": "kullanici"}, {"dogru": "Brenvik", "yanlis": [], "kaynak": "sozluk-genisletme-20260601"},
         {"dogru": "Ostrava Pay", "yanlis": ["ostrava pey"], "kaynak": f"ogrenme-{B - datetime.timedelta(days=5):%Y%m%d}"},
         {"dogru": "Eskivora", "yanlis": [], "kaynak": f"ogrenme-{B - datetime.timedelta(days=30):%Y%m%d}"}, {"dogru": "Yenikart", "yanlis": [], "kaynak": "proje-karti"}]
kay.update({"Lumora": {"ilk": G(200), "toplanti_sayisi": 0}, "Brenvik": {"ilk": G(200), "toplanti_sayisi": 0}, "Ostrava Pay": {"ilk": G(5), "toplanti_sayisi": 0},
            "Eskivora": {"ilk": G(30), "son": G(90), "toplanti_sayisi": 1}})  # Yenikart kayıtta yok (izlem bilinmiyor): yaşlanmaz
ag2 = {"title": "Haftalık durum", "items": []}
k = kul_(kay); s4 = ns["istem_siralama"](ter2, ag2, [], ks, ["Ayşe Yıldırım"], ["AWS"], "", "Deniz K", k); t4 = [t for _, t in s4]; c4 = dict((t, kk) for kk, t in s4)
kontrol(f"yaşlandırma: 100 gün geçmeyen 90 terim + 90 gündür geçmeyen eski öğrenilen istemden düşer (kul yasli = {k.get('yasli')})", k.get("yasli") == 91 and "Kappa50Modul" not in t4 and "Kappa119Modul" not in t4)
kontrol("yaşlı terim sözlükte kalır (yalnız istemden çıkar): sıralama girdisi değişmez", len(ter2) == 125)
kontrol("elle eklenen (kullanici, sozluk-genisletme) yaşlanmaz", "Lumora" in t4 and "Brenvik" in t4)
kontrol("≤ 14 gün önce öğrenilen yaşlanmaz, 30 gün önce öğrenilip 90 gündür geçmeyen yaşlanır", "Ostrava Pay" in t4 and "Eskivora" not in t4)
kontrol("kayıtta olmayan terim (izlem başlangıcı yok) yaşlanmaz", "Yenikart" in t4)
kontrol("yakınlık: dün kullanılan, 49 gün önce kullanılandan önce", t4.index("Kappa1Modul") < t4.index("Kappa49Modul") if "Kappa49Modul" in t4 else True)
kontrol("kayıt varken 'sık' kategorisi yok (puan yerine geçer), kişi ve asistan yine önde", "sık" not in c4.values() and [kk for kk, _ in s4][:4] == ["asistan"] * 4 and c4.get("Ayşe Yıldırım") == "kişi")
s5 = ns["istem_siralama"](ter2, ag2, [], ks, [], ["AWS"], "", "", kul_(kay, canli=["Kappa90Modul"], baglam=["Kappa95Modul"])); t5 = [t for _, t in s5]; c5 = dict((t, kk) for kk, t in s5)
sg5, ist5 = sigan(s5, "bir iki üç " * 30)
kontrol("bu toplantıda geçen yaşlı terim 'bağlam'da ve istemin sığan kısmında (önceki metin doluyken de)", c5.get("Kappa90Modul") == "bağlam" and "Kappa90Modul" in sg5)
kontrol("dizin bağlamındaki yaşlı terim 'bağlam'da, ayar terimlerinden önce", c5.get("Kappa95Modul") == "bağlam" and t5.index("Kappa95Modul") < t5.index("AWS"))
kontrol("bu toplantıda geçen, bağlamdakinden önce (puan 8 > 3)", t5.index("Kappa90Modul") < t5.index("Kappa95Modul"))
kontrol(f"yeni seçimde de 215 belirteç sınırı ({len(tok.encode(' ' + ist5))} ≤ {WI.ISTEM_SINIR})", len(tok.encode(" " + ist5)) <= WI.ISTEM_SINIR and len(tok.encode(" " + sigan(s5)[1])) <= WI.ISTEM_SINIR)
# öncelik: kullanılmayan kullanıcı terimi, sık ve yakın kullanılan proje kartı teriminin arkasında; ama kullanılmayan proje kartı teriminin önünde
ter3 = [{"dogru": "Sarvona", "yanlis": [], "kaynak": "kullanici"}, {"dogru": "Pemtrik", "yanlis": [], "kaynak": "proje-karti"}, {"dogru": "Dulmara", "yanlis": [], "kaynak": "proje-karti"}]
s6 = [t for _, t in ns["istem_siralama"](ter3, {}, [], [], [], [], "", "", kul_({"Sarvona": {"ilk": G(10), "toplanti_sayisi": 0}, "Pemtrik": {"son": G(1), "toplanti_sayisi": 9, "ilk": G(90)},
                                                                                   "Dulmara": {"ilk": G(10), "toplanti_sayisi": 0}}))]
kontrol("puan sırası: sık+yakın (Pemtrik) > elle eklenen kullanılmamış (Sarvona) > kullanılmamış (Dulmara)", s6 == ["Pemtrik", "Sarvona", "Dulmara"], s6)
s7 = [t for _, t in ns["istem_siralama"](ter3, {}, [], [], [], [], "", "", kul_({}, yas=60))]
kontrol("kayıt boşken (yeni kurulumdan sonraki ilk gün) eski sıra korunur: kullanıcı önce", s7[0] == "Sarvona", s7)
kontrol("ayar istem_yasi_gun: 120 günde 100 gün önceki terim yaşlı değil", "Kappa50Modul" in [t for _, t in ns["istem_siralama"](ter2, ag2, [], [], [], [], "", "", kul_(kay, yas=120))])
# istem_metni'nin kul'u: kayıt dosyası yoksa None (eski sıra); varsa dict; ayar kapalıysa None; süren toplantının dökümünde geçen terim canlı
T = tempfile.mkdtemp(prefix="suflor-istem-sira-"); ns["BASE"] = T; ns["aktif_dosya"] = lambda: "2026-06-15-1000-Kurgu.md"
json.dump({"id": "x", "speaker": "Kappa7Modul", "text": "Kappa3Modul'ü açtık"}, open(os.path.join(T, "2026-06-15-1000-Kurgu.jsonl"), "w"), ensure_ascii=False)
kontrol("kullanım kaydı yokken kul None (eski sıra aynen)", ns["istem_kullanim"](ter2, ag2, [], []) is None)
json.dump({"surum": 1, "terimler": kay}, open(os.path.join(T, "sozluk-kullanim.json"), "w"))
kontrol("kayıt varken de varsayılan kapalı (ayar istem_secim yok → eski sıra)", ns["ISTEM_SECIM_VARSAYILAN"] or ns["istem_kullanim"](ter2, ag2, [], []) is None)
ns["AYAR"]["istem_secim"] = True; k8 = ns["istem_kullanim"](ter2, ag2, [], ["Lumora Kişi"])
kontrol("kayıt varken kul dolu: süren toplantıda geçen terim canlı (konuşmacı sütunu değil), katılımcıda geçen terim bağlam",
        k8 is not None and sd("Kappa3Modul") in k8["canli"] and sd("Kappa7Modul") not in k8["canli"] and sd("Lumora") in k8["baglam"], k8 and (sorted(k8["canli"]), sorted(k8["baglam"])))
# proje dizini bağlamı: gündem sözcüğüyle aynı belgede geçen terim bağlam; yalnız döküm türündeki belgede geçen sayılmaz (sozluk-ogren.py SO_BELGE_DISI)
dz = os.path.join(T, "dizin.sqlite"); c = sqlite3.connect(dz)
c.executescript("CREATE TABLE dosya(yol TEXT PRIMARY KEY, tur TEXT, gizli INTEGER); CREATE TABLE parca(id INTEGER PRIMARY KEY, yol TEXT, metin TEXT);"
                "CREATE VIRTUAL TABLE ara USING fts5(n, kimn, content='', prefix='3 4 5', tokenize='unicode61');")
for i, (yol, tur, m) in enumerate([("a.md", "belge", "Tedarik planında Kappa60Modul ve sevkiyat takvimi"), ("b.md", "toplanti", "tedarik konuşulurken Kappa61Modul geçti")]):
    c.execute("INSERT INTO dosya VALUES(?,?,0)", (yol, tur)); c.execute("INSERT INTO parca VALUES(?,?,?)", (i + 1, yol, m)); c.execute("INSERT INTO ara(rowid, n, kimn) VALUES(?,?,?)", (i + 1, m.lower(), ""))
c.commit(); c.close()
ns.update(_so_dizin=lambda: sqlite3.connect(dz), SO_BELGE_DISI=("toplanti", "gorusme", "konusma"))
k9 = ns["istem_kullanim"](ter2, {"title": "Tedarik planı görüşmesi", "items": ["sevkiyat"]}, [], [])
kontrol("proje dizininde gündem sözcüğüyle birlikte geçen terim bağlam, döküm türü belgedeki değil", sd("Kappa60Modul") in k9["baglam"] and sd("Kappa61Modul") not in k9["baglam"], sorted(k9["baglam"]))
ns["AYAR"]["istem_secim"] = False; kontrol("ayar istem_secim: false → kul None", ns["istem_kullanim"](ter2, ag2, [], []) is None); ns["AYAR"].pop("istem_secim")
ns["AYAR"].update(istem_secim=True, istem_yasi_gun=30); kontrol("ayar istem_yasi_gun kul'a geçer", ns["istem_kullanim"](ter2, ag2, [], [])["yas_gun"] == 30); ns["AYAR"].clear()
s1b = ns["istem_siralama"](ter, ag, [], ks, kisiler, ["AWS", "Google Workspace"], dokum, "Deniz K", None)
kontrol("kul=None çıktısı parametresiz çağrıyla birebir (eski davranış)", s1b == sira)
# 5 Kasım: kalabalık istemde sözlük adil pay alır (4 Kasım toplantısı: "sözlük 0/46"); kategori sırası bozulmaz
tp = [{"dogru": f"Sik{chr(65 + i)}Modul", "yanlis": [], "kaynak": "x"} for i in range(19)] + [{"dogru": f"Soz{chr(65 + i)}Birim", "yanlis": [], "kaynak": "ben" if i == 3 else "x"} for i in range(20)]
dk = " ".join(f"sik{chr(97 + i)}modul" for i in range(19)) * 3
kr = {"terimler": {f"Soz{chr(65 + i)}Birim": {"toplanti_sayisi": i, "son": "2026-11-01", "ilk": "2026-10-01"} for i in range(20)}}
sc = ns["istem_siralama"](tp, {}, [], [], [], ["AWS"], dk, "", None, kr); tc = [t for _, t in sc]; kc = [k for k, _ in sc]
kontrol("kalabalık: sözlük terimleri sık'ın kalanından önce, ilk 20 terimde en az 6 sözlük", sum(1 for k in kc[:20] if k == "sözlük") >= 6, kc[:24])
kontrol("kalabalık: sık'ın ilk 6 terimi sözlük tabanından önce", kc[:6] == ["sık"] * 6, kc[:12])
kontrol("kalabalık: taban sırası kullanıcı terimi önde, sonra kullanım sayısı çok olan", tc[6] == "SozDBirim" and tc[7] == "SozTBirim", tc[4:10])
kontrol("kalabalık: hiçbir terim yinelenmedi/kaybolmadı", len(tc) == len(set(tc)) and len(tc) == 40, len(tc))
kontrol("az sık (≤ 6): sıra değişmez", [k for k, _ in ns["istem_siralama"](tp[19:], {}, [], [], [], [], "", "", None)] == ["sözlük"] * 20)
# günlük eki
print("kategori sayıları:", {k: kat.count(k) for k in ns["ISTEM_KAT_ADLARI"]})
print("kaldı" if hatalar else "hepsi geçti"); sys.exit(1 if hatalar else 0)
