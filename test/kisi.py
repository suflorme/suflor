#!/usr/bin/env python3
# Mac Kişiler erişimi (S225, 5 Kasım; yalnız okuma): takvim.swift --kisi, aktarici/talimat.py kisi_bul/kisi_eposta/toplanti_davetli yedeği, relay /kisi,
# toplanti-claude.py kisi + MCP kisi_bul, Konuş izin listesi. Swift çağrılmaz (sahte yardımcı çıktısı); yapay adlar, ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisi.py
import os, re, sys, json, time, types
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
EP = lambda k: k + chr(64) + "ornek.test"
oku = lambda *y: open(os.path.join(KOD, *y), encoding="utf-8").read()
ns = {"re": re, "os": os, "json": json, "time": time, "datetime": __import__("datetime"), "urllib": __import__("urllib"), "AYAR": {}, "BASE": "/tmp/yok", "_t": lambda tr, en: tr}
exec(compile(oku("aktarici", "talimat.py"), "talimat.py", "exec"), ns)
cagri = []
def sahte(yanit):
    def f(args, istek=None): cagri.append(list(args)); return yanit
    return f
tek = {"durum": "ok", "kisiler": [{"ad": "Deniz Yıldız", "kurum": "Örnek A.Ş.", "eposta": [EP("deniz"), EP("deniz2")], "telefon": ["+90 555 000 00 00"], "adres": ["Örnek Cad. 1, Ankara"]}]}
os.environ["SUFLOR_TEST_BASLAT"] = "1"
ns["_takvim_yardimci"] = sahte(tek)
o = ns["kisi_bul"]("Deniz"); kontrol("deneme kipinde SUFLOR_TEST_KISI yokken yardımcı çağrılmaz", o["durum"] == "hata" and not cagri)
os.environ["SUFLOR_TEST_KISI"] = "1"
o = ns["kisi_bul"]("  Deniz  "); kontrol("kisi_bul: --kisi <ad> ile çağırır, alanlar süzülür", cagri[-1] == ["--kisi", "Deniz"] and o["kisiler"][0]["eposta"] == [EP("deniz"), EP("deniz2")] and o["kisiler"][0]["adres"] == ["Örnek Cad. 1, Ankara"])
n = len(cagri); ns["kisi_bul"]("deniz"); kontrol("aynı ad (büyük-küçük harf farksız) 10 dk önbellekten, yeniden sorulmaz", len(cagri) == n)
kontrol("kisi_eposta: tek kişi → ilk e-posta (küçük harf)", ns["kisi_eposta"]("Deniz") == EP("deniz"))
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "ok", "kisiler": [{"ad": "Ali Kaya", "eposta": [EP("ali")]}, {"ad": "Ali Demir", "eposta": [EP("ali.d")]}]})
kontrol("kisi_eposta: iki kişi eşleşirse belirsiz → None", ns["kisi_eposta"]("Ali") is None)
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "ok", "kisiler": [{"ad": "Veli", "eposta": [], "telefon": ["1"]}]})
kontrol("kisi_eposta: adresi olmayan kişi → None", ns["kisi_eposta"]("Veli") is None)
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "izin_yok", "hata": "Kişiler izni yok"})
o = ns["kisi_bul"]("Deniz"); kontrol("izin yok → açık hata, önbelleğe girmez", o == {"durum": "izin_yok", "hata": "Kişiler izni yok"} and not ns["_KISI_ONBELLEK"] and ns["kisi_eposta"]("Deniz") is None)
ns["AYAR"]["kisiler_arama"] = False; n = len(cagri); o = ns["kisi_bul"]("Deniz"); kontrol("ayar kisiler_arama: false → kapalı, yardımcı çağrılmaz", o["durum"] == "kapali" and len(cagri) == n); ns["AYAR"].clear()
kontrol("çok kısa ad reddedilir", ns["kisi_bul"]("a")["durum"] == "hata")
# davet akışı: önce takvim geçmişi, yoksa Kişiler, o da yoksa adressiz
ns["_KISI_ONBELLEK"].clear(); cagri.clear()
def adli(args, istek=None):
    cagri.append(list(args)); return tek if args[1] == "Deniz" else {"durum": "ok", "kisiler": [{"ad": "Ayşe Yıl", "eposta": [EP("ayse.y")]}]} if args[1] == "Ayşe" else {"durum": "ok", "kisiler": []}
ns["_takvim_yardimci"] = adli
ns["TAKVIM_TAM"] = {"a": {"kisiler": [{"ad": "Ali Kaya", "eposta": EP("ali")}]}, "b": {"kisiler": [{"ad": "Ayşe Su", "eposta": EP("ayse")}, {"ad": "Ayşe Ak", "eposta": EP("ayse.ak")}]}}
d = ns["toplanti_davetli"](["Ali Kaya", "Ayşe", "Deniz", EP("zeynep"), "Bilinmez"])
kontrol(f"davetli: takvimden bulunan Kişiler'e sorulmaz, takvimde belirsiz ya da yok olan Kişiler'e sorulur, yazılı e-posta aynen, hiçbirinde yoksa adressiz: {d}",
        [k["eposta"] for k in d] == [EP("ali"), EP("ayse.y"), EP("deniz"), EP("zeynep"), None] and [c[1] for c in cagri] == ["Ayşe", "Deniz", "Bilinmez"])
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "ok", "kisiler": []}); d = ns["toplanti_davetli"](["Bilinmez"])
kontrol("Kişiler'de de yoksa adressiz kalır (eski davranış)", d == [{"ad": "Bilinmez", "eposta": None}])
# toplanti-claude.py: komut + MCP aracı; relay: /kisi; Konuş izin listesi; Swift/plist
tc = oku("toplanti-claude.py")
kontrol("tc: kisi alt komutu, kisi_ara aktarıcı /kisi'ye gider, MCP kisi_bul aracı listede ve çağrılabilir",
        'sub.add_parser("kisi"' in tc and '"kisi": kisi_cmd' in tc and 'get("/kisi?ad="' in tc and '{"name": "kisi_bul"' in tc and 'if ad == "kisi_bul": metin, hata = kisi_ara(' in tc)
rl = oku("relay.py")
kontrol("relay: /kisi okuma ucu anahtar ister (VERI_GET) ve kisi_bul'a bağlı", '"/kisi"' in rl.split('VERI_GET = ',1)[1].split('}',1)[0] and 'if yol == "/kisi":' in rl and "kisi_bul(ad)" in rl)
bk = oku("aktarici", "bas-konus.py")
kontrol("Konuş: kisi_bul aracı izin listesinde ve istemde, brifing.swift mcp__suflorvt__ önekini zaten tanır", "mcp__suflorvt__kisi_bul" in bk and "kisi_bul'u kullan" in bk and 'hasPrefix("mcp__suflorvt__")' in oku("brifing.swift"))
sw = oku("takvim.swift"); ku = oku("kurulum.py")
kontrol("takvim.swift: Contacts, --kisi, en çok 20, izin_yok hatası, yazma/kaydetme çağrısı yok",
        "import Contacts" in sw and '"--kisi"' in sw and "prefix(en)" in sw and "let en = 20" in sw and '"izin_yok"' in sw and not re.search(r"CNSaveRequest|CNMutable", sw))
kontrol("TAKVIM_PLIST: NSContactsUsageDescription var", "NSContactsUsageDescription" in ku)
# --- v0.211 (okumaarac): kisi_bul genişledi (kurum/e-posta, doğum günü, 20), kisi_ozet, kayit_listele, kayit_tarihce
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "ok", "kisiler": [{"ad": "Ece Aydın", "kurum": "Örnek A.Ş.", "dogum": "1990-03-14", "eposta": [EP("ece")]}] + [{"ad": f"K{i}"} for i in range(30)]})
o = ns["kisi_bul"]("Örnek"); kontrol("kisi_bul: en çok 20 sonuç, doğum günü alanı geçer", len(o["kisiler"]) == 20 and o["kisiler"][0]["dogum"] == "1990-03-14" and o["kisiler"][1]["dogum"] == "")
OZ = {"durum": "ok", "toplam": 812, "telefonlu": 700, "epostali": 650, "adresli": 90, "dogumlu": 120, "kurumlu": 400, "kurumlar": [{"kurum": "Örnek A.Ş.", "sayi": 30}], "ad": "SIZMAMALI", "kisiler": [{"ad": "SIZMAMALI"}]}
ns["_KISI_ONBELLEK"].clear(); cagri.clear(); ns["_takvim_yardimci"] = sahte(OZ)
o = ns["kisi_ozet"](); kontrol(f"kisi_ozet: --kisi-ozet çağrılır, yalnız sayı alanları geçer (ad/kisiler sızmaz): {o}", cagri[-1] == ["--kisi-ozet"] and o == {"durum": "ok", "toplam": 812, "telefonlu": 700, "epostali": 650, "adresli": 90, "dogumlu": 120, "kurumlu": 400})
o = ns["kisi_ozet"](True); kontrol("kisi_ozet(kurum_say): --kurum-say, ilk 10 kurum sayımı", cagri[-1] == ["--kisi-ozet", "--kurum-say"] and o["kurumlar"] == [{"kurum": "Örnek A.Ş.", "sayi": 30}])
n = len(cagri); ns["kisi_ozet"](True); kontrol("kisi_ozet önbellekten gelir", len(cagri) == n)
ns["_KISI_ONBELLEK"].clear(); ns["_takvim_yardimci"] = sahte({"durum": "izin_yok", "hata": "Kişiler izni yok"}); o = ns["kisi_ozet"](); kontrol("kisi_ozet: izin yok → açık hata, önbelleğe girmez", o["durum"] == "izin_yok" and not ns["_KISI_ONBELLEK"])
ns["AYAR"]["kisiler_arama"] = False; o = ns["kisi_ozet"](); kontrol("kisi_ozet: kisiler_arama:false → kapalı", o["durum"] == "kapali"); ns["AYAR"].clear()
tc = oku("toplanti-claude.py"); i0 = tc.index("def kisi_ozet("); i1 = tc.index("def kisi_cmd()")
tn = {"re": re, "os": os, "json": json, "A": types.SimpleNamespace(dir="/tmp/yok"), "get": None, "_yapi": None}; exec(compile(tc[i0:i1], "tc-kayit", "exec"), tn)
KAY = [{"id": "s1", "kayit_id": "A" * 26, "tur": "is", "metin": "Rapor hazırla", "kim": "Ali Kaya", "vade": "2026-11-01", "gecikti": True, "durum": "acik", "baslik": "Haftalık", "tarih": "2026-10-28"},
       {"id": "s2", "kayit_id": "B" * 26, "tur": "is", "metin": "Sunum", "kim": "Deniz Yıldız", "vade": "2026-12-01", "gecikti": False, "durum": "acik", "baslik": "Plan", "tarih": "2026-11-05"},
       {"id": "k3", "kayit_id": "C" * 26, "tur": "karar", "metin": "Bütçe onaylandı", "kim": "Ali Kaya", "vade": "", "gecikti": False, "durum": "teyit", "baslik": "Plan", "tarih": "2026-11-06"},
       {"id": "q4", "kayit_id": "D" * 26, "tur": "soru", "metin": "Kim sorumlu?", "kim": "", "vade": "", "gecikti": False, "durum": "kapandi", "baslik": "Plan", "tarih": "2026-11-07"}] + [dict(KAY0, id=f"s{10+i}", kayit_id=f"{i:026d}") for i, KAY0 in enumerate([{"tur": "is", "metin": "toplu", "kim": "Veli", "vade": "", "gecikti": False, "durum": "acik", "baslik": "Toplu", "tarih": "2026-09-01"}] * 70)]
tn["get"] = lambda y, zaman=3: {"ok": True, "kayitlar": KAY}
L = lambda **ar: tn["kayit_listele"](ar)[0]
kontrol("kayit_listele: süzgeçsiz en çok 25, toplam sayısı ve kesme notu", L().startswith("74 kayıt eşleşti, ilk 25 gösteriliyor") and L().count("\n- ") == 25 and L(en_cok=500).count("\n- ") == 50)
kontrol("kayit_listele: gecikmiş önce, sonra yeni toplantı önce", L(en_cok=3).split("\n- ")[1].startswith("A" * 26) and L(en_cok=3).split("\n- ")[2].startswith("D" * 26))
kontrol("kayit_listele: tür/durum/sahip (parça, büyük-küçük harf farksız)/gecikmiş", L(tur="karar").startswith("1 kayıt") and L(durum="teyit").startswith("1 kayıt") and L(sahip="ali").startswith("2 kayıt") and L(gecikmis=True).startswith("1 kayıt") and "GECİKTİ" in L(gecikmis=True))
kontrol("kayit_listele: tarih ve vade aralığı, metin araması", L(tarih_bas="2026-11-01", tarih_son="2026-11-06").startswith("2 kayıt") and L(vade_bas="2026-11-15").startswith("1 kayıt") and L(ara="BÜTÇE").startswith("1 kayıt") and L(ara="plan", tur="is").startswith("1 kayıt"))
kontrol("kayit_listele: eşleşme yoksa açık mesaj", L(sahip="yok kişi") == "Bu süzgeçle kayıt yok.")
tn["get"] = lambda y, zaman=3: {"ok": False}; kontrol("kayit_listele: kayıt grafı yoksa hata", tn["kayit_listele"]({})[1] is True)
def _hata(y, zaman=3): raise OSError("x")
tn["get"] = _hata; kontrol("kayit_listele: aktarıcı yoksa hata (istisna sızmaz)", tn["kayit_listele"]({})[1] is True and tn["kayit_tarihce"]("s1")[1] is True)
tn["get"] = lambda y, zaman=3: {"ok": True, "kayitlar": KAY}; CAG = []
tn["_yapi"] = lambda: types.SimpleNamespace(tarihce=lambda d, k: CAG.append(k) or [{"ozet": f"2026-11-0{i} 10:00 UTC · Ali · olay{i}", "tur": "x"} for i in range(1, 6)])
m, h = tn["kayit_tarihce"]("s1"); kontrol("kayit_tarihce: yerel kimlikle kayit_id'ye çözülür, olaylar eskiden yeniye", not h and CAG == ["A" * 26] and m.count("\n- ") == 5 and "olay5" in m)
m, h = tn["kayit_tarihce"]("B" * 26); kontrol("kayit_tarihce: kayit_id ile", CAG[-1] == "B" * 26)
CAG.clear(); m, h = tn["kayit_tarihce"]("Z" * 26); kontrol("kayit_tarihce: listede görünmeyen (gizli/deneme/yok) kaydın tarihçesi verilmez, yapı çağrılmaz", not CAG and "görünür kayıt yok" in m)
kontrol("kayit_tarihce: boş kimlik hata", tn["kayit_tarihce"]("")[1] is True)
kontrol("tc: MCP araç listesi 6 araç, çağrı yolları bağlı, get zaman aşımı parametreli", all(f'{{"name": "{a}"' in tc for a in ("kayit_listele", "kayit_tarihce", "kisi_ozet")) and 'ad == "kayit_listele"' in tc and 'ad == "kayit_tarihce"' in tc and 'ad == "kisi_ozet"' in tc and "def get(path, zaman=3)" in tc)
kontrol("relay: /kisi-ozet okuma ucu anahtar ister (VERI_GET), kisi_ozet'e bağlı", '"/kisi-ozet"' in rl.split('VERI_GET = ',1)[1].split('}',1)[0] and 'yol == "/kisi-ozet"' in rl and "kisi_ozet(" in rl)
kontrol("takvim.swift: --kisi-ozet yalnız sayı yazar (toplam…kurumlu), --kurum-say, kurum/e-posta aramasında doğum günü", '"--kisi-ozet"' in sw and '"--kurum-say"' in sw and "func kisiOzetle" in sw and "CNContactBirthdayKey" in sw and '"toplam": top' in sw and not re.search(r'o\["(ad|eposta|telefon)"\]', sw[sw.index("func kisiOzetle"):sw.index("func kisiIzinle")]))
kontrol("bas-konus.py VT_MCP_ARACLAR yeni araçları (kayit_listele, kayit_tarihce, kisi_ozet) içeriyor ve istemde anlatılıyor", all(f"mcp__suflorvt__{a}" in bk for a in ("kayit_listele", "kayit_tarihce", "kisi_ozet")) and "kisi_ozet kullan" in bk and "N kayıt eşleşti" in bk)
bs = oku("brifing.swift")
kontrol("brifing.swift araclar listesinde WebSearch ve WebFetch (konus_web için)", re.search(r'let araclar: Set<String> = \[[^\]]*"WebSearch"[^\]]*"WebFetch"', bs) is not None)
print("\nSONUÇ: " + ("hepsi geçti" if not hatalar else f"{len(hatalar)} hata: {hatalar}")); sys.exit(1 if hatalar else 0)
