#!/usr/bin/env python3
# Hafif profil (S188 adım 3): ≤ 8 GB'ta "hafif" önerisi, tek anahtardan türeyen ayarlar, elle ayarın önceliği, "tam"a dönüş, indirmelerin atlanması.
# Bellek miktarı sahte verilir (8 ve 32 GB). Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/profil.py
import ast, os, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "kurulum.py"), encoding="utf-8").read(); a = ast.parse(src); ns = {}
sec = [n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in {"donanim_durum", "profil_hafif"}) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in {"BELLEK_KARARLI_GB", "BELLEK_HAFIF_GB"} for x in n.targets))]
exec(compile(ast.Module(sec, []), "kurulum.py", "exec"), ns)
pm = {}; exec(compile(open(os.path.join(KOD, "aktarici", "profil.py"), encoding="utf-8").read(), "profil.py", "exec"), pm); ns.update(pm)  # tek kaynak: aktarici/profil.py
dd, pu, ph, PH = ns["donanim_durum"], ns["profil_uygula"], ns["profil_hafif"], ns["PROFIL_HAFIF"]; hata = 0
def kontrol(ad, ok):
    global hata; hata += not ok; print(("✓ " if ok else "✗ ") + ad)
kontrol("8 GB Apple Silicon → hafif", dd(True, 8) == "hafif"); kontrol("4 GB → hafif", dd(True, 4) == "hafif")
kontrol("12 GB → az_bellek (hafif önerilmez)", dd(True, 12) == "az_bellek"); kontrol("32 GB → tamam", dd(True, 32) == "tamam"); kontrol("8 GB Intel → intel", dd(False, 8) == "intel")
# 32 GB geliştirici: profil seçilmez, ayar değişmez
g = {"ses_motoru": "pocket", "whisper_motor": "cpp", "konus_iki_surec": True}; g0 = dict(g)
kontrol("kurulum.py tabloyu aktarici/profil.py'den yüklüyor (kopya yok)", "PROFIL_HAFIF = {" not in src and "aktarici\", \"profil.py" in src)
kontrol("geliştirici (profil yok) ayarı değişmez", g == g0 and not ph(g))
# 8 GB: hafif seçilince yalnız ayarda olmayanlar yazılır
b = {"ses_motoru": "pocket"}; pu(b, "hafif")
kontrol("hafif: profil işareti yazılır", b.get("profil") == "hafif" and ph(b))
kontrol("hafif: türetilen ayarlar (anlam kapalı, ikinci süreç/önceden açma/gölge kapalı)", b.get("anlam_arama") is False and b.get("konus_iki_surec") is False and b.get("konus_on_ac") is False and b.get("golge_tstt") is False)
kontrol("hafif: elle verilen ayar profili ezer (ses_motoru pocket kaldı)", b["ses_motoru"] == "pocket" and "ses_motoru" not in b["profil_turetilen"])
b2 = {}; pu(b2, "hafif"); kontrol("hafif: boş ayarda ses motoru Mac", b2["ses_motoru"] == "mac" and set(b2["profil_turetilen"]) == set(PH))
pu(b2, "hafif"); kontrol("hafif tekrar uygulanınca değişmez", set(b2["profil_turetilen"]) == set(PH))
# tam'a dönüş: yalnız türetilenler silinir; kullanıcı sonradan değiştirdiyse kalır
b2["anlam_arama"] = True; pu(b2, "tam")
kontrol("tam: profil ve türetilenler silinir", "profil" not in b2 and "profil_turetilen" not in b2 and "ses_motoru" not in b2 and "konus_iki_surec" not in b2)
kontrol("tam: kullanıcının sonradan açtığı anlam_arama kalır", b2.get("anlam_arama") is True)
kontrol("tam: elle verilen ses_motoru (pocket) kalır", pu(b, "tam").get("ses_motoru") == "pocket" and "profil" not in b)
# relay.py ayar_oku: profil hafif iken çalışma zamanında tablo elle ayarın altına türer (dosyaya yazılmadan)
import json, tempfile
rs = ast.parse(open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()); T = tempfile.mkdtemp(); rn = {"os": os, "json": json, "__file__": os.path.join(KOD, "relay.py")}
exec(compile(ast.Module([n for n in rs.body if isinstance(n, ast.FunctionDef) and n.name in ("_profil_modul", "ayar_oku")], []), "relay.py", "exec"), rn)
def oku(d): rn["AYAR_YOL"] = os.path.join(T, "ayar.json"); json.dump(d, open(rn["AYAR_YOL"], "w")); return rn["ayar_oku"]()
r = oku({"profil": "hafif", "ses_motoru": "pocket", "konus_on_ac": True})
kontrol("relay ayar_oku: hafifte türetilir (anlam kapalı, ikinci süreç kapalı)", r["anlam_arama"] is False and r["konus_iki_surec"] is False and r["golge_tstt"] is False)
kontrol("relay ayar_oku: elle verilen ayar kazanır (pocket, konus_on_ac true)", r["ses_motoru"] == "pocket" and r["konus_on_ac"] is True)
r = oku({"ses_motoru": "pocket"}); kontrol("relay ayar_oku: profilsiz (geliştirici) ayar hiç değişmez", "anlam_arama" not in r and r["ses_motoru"] == "pocket" and "profil" not in r)
r = oku({"profil": "tam"}); kontrol("relay ayar_oku: profil tam → türetme yok", "anlam_arama" not in r)
rl = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
kontrol("relay AYAR_PANO'da profil, ayar_yaz profil_uygula çağırıyor", '"profil": ("sec", "tam", ("tam", "hafif"))' in rl and 'profil_uygula(a, yeni["profil"])' in rl)
pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read(); dj = open(os.path.join(KOD, "pano", "dil.js"), encoding="utf-8").read()
kontrol("pano AYG'de Kurulum profili + dil.js İngilizcesi", "['profil','sec','Kurulum profili'" in pano and '"Kurulum profili": "Setup profile"' in dj)
# kaynak denetimi: indirme ve arayüz kancaları
for k in ('if profil_hafif(): return {"durum": "hata"', "if profil_hafif(): return pocket_durum()", "not anlam_ok and not hafif", "not hafif and not anlam_dene", '"/api/profil"', 'profil_uygula(a, c["profil"])'):
    kontrol(f"kurulum.py: {k[:46]}", src.count(k) == 1)
js = open(os.path.join(KOD, "sihirbaz", "sihirbaz.js"), encoding="utf-8").read()
for k in ("m_hafif_b:", "m_hafif_a:", "m_tam_b:", "m_hafif:", 'data-donanim="hafif"', 'data-profil="${v}"'):
    kontrol(f"sihirbaz.js: {k}", js.count(k) >= (2 if k.endswith(":") else 1))
print("profil: ✓ hepsi geçti" if not hata else f"profil: ✗ {hata} hata"); sys.exit(1 if hata else 0)
