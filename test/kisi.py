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
kontrol("relay: /kisi okuma ucu anahtar ister (VERI_GET) ve kisi_bul'a bağlı", '"/gundem-taslagi", "/kisi"}' in rl and 'if yol == "/kisi":' in rl and "kisi_bul(ad)" in rl)
bk = oku("aktarici", "bas-konus.py")
kontrol("Konuş: kisi_bul aracı izin listesinde ve istemde, brifing.swift mcp__suflorvt__ önekini zaten tanır", "mcp__suflorvt__kisi_bul" in bk and "kisi_bul aracıyla" in bk and 'hasPrefix("mcp__suflorvt__")' in oku("brifing.swift"))
sw = oku("takvim.swift"); ku = oku("kurulum.py")
kontrol("takvim.swift: Contacts, --kisi, en çok 5, izin_yok hatası, yazma/kaydetme çağrısı yok",
        "import Contacts" in sw and '"--kisi"' in sw and "prefix(5)" in sw and '"izin_yok"' in sw and not re.search(r"CNSaveRequest|CNMutable", sw))
kontrol("TAKVIM_PLIST: NSContactsUsageDescription var", "NSContactsUsageDescription" in ku)
bs = oku("brifing.swift")
kontrol("brifing.swift araclar listesinde WebSearch ve WebFetch (konus_web için)", re.search(r'let araclar: Set<String> = \[[^\]]*"WebSearch"[^\]]*"WebFetch"', bs) is not None)
print("\nSONUÇ: " + ("hepsi geçti" if not hatalar else f"{len(hatalar)} hata: {hatalar}")); sys.exit(1 if hatalar else 0)
