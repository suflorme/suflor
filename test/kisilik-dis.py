#!/usr/bin/env python3
# Üçüncü kişilik yuvası (ayar kisilik_dis, rol "dis" — dış işler asistanı; 10 Kasım): yükleme, varsayılan muhatap değil, adla çağrılınca cevaplar; Konuş isteminde üç kişilik;
# ≤ 4 harfli kısa takma adlar (hitap_kisa) yalnız cümle başında ve virgül/iki nokta ya da soru biçimiyle seslenme, ses benzerliğiyle eşlenmez, cümle içinde sayılmaz.
# Kurgu adlar: Atlas (toplantı), Matlas (toplantı dışı), Roxane (dış işler; kısa biçimler Roxy, Rox, Roks, Raks, Ro). Aktarıcının kendi tanımları AST/exec ile alınır; süreç açılmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisilik-dis.py      (kaldı → çıkış 1)
import ast, collections, json, os, re, shutil, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="kisdis-"); hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
def yaz(ad, govde): y = os.path.join(T, ad); open(y, "w", encoding="utf-8").write(govde); return y
k1 = yaz("a.md", "---\nad: Atlas\nhitap: Atlas, Atlaz\nhitap_bicimi: sen\n---\n## Kişilik: Atlas\nAdın Atlas. BİRİNCİ-İŞARET\n")
k2 = yaz("m.md", "---\nad: Matlas\nhitap: Matlas\nhitap_bicimi: sen\n---\n## Kişilik: Matlas\nAdın Matlas. İKİNCİ-İŞARET\n")
k3 = yaz("r.md", "---\nad: ROXANE\ngorunen_ad: Roxane\nhitap: Roxane, Roksi, Roxy, Rox, Roks, Raks, Ro\nokunus: Roksan\nhitap_bicimi: sen\nses: gemini:Kore\n---\n## Kişilik: Roxane\nDış işler asistanısın. ÜÇÜNCÜ-İŞARET\n")
def oku(d, f): return open(os.path.join(KOD, d, f), encoding="utf-8").read()
src = oku("aktarici", "bas-konus.py")
ns = {"re": re, "os": os, "json": json, "time": time, "collections": collections, "threading": threading, "print": lambda *a, **k: None, "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": T,
      "AYAR": {"kisilik": k1, "kisilik_toplanti_disi": k2, "kisilik_dis": k3}, "_KS": {}, "TOP": [False], "_ad_listesi": lambda: {}, "_onara_mod": lambda: None}
ns["toplanti_var"] = lambda: ns["TOP"][0]
exec(oku("aktarici", "kisilik.py"), ns)
agac = ast.parse(oku("aktarici", "sozluk.py"))
exec(compile(ast.Module([n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in ("hitap_duzelt", "_kisilik_hitap_rx", "_kisilik_hitap_ad", "_hitap_adlari", "_hitap_kisa_adlari", "_hitap_alt", "_hitap_rx",
                         "hitap_yalniz_ad", "hitap_icte", "hitap_ses_duzelt", "karsi_hitap_cozumle", "karsi_soru_bicimi", "hitap_aski")) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in (
                         "HITAP_RX", "HITAP_ORTA_RX", "HITAP_AD", "BULUT", "_KHR", "HITAP_ASKI", "HITAP_ASKI_SN", "HITAP_DEVAM_SN", "HITAP_AD_DEVAM_SN", "HITAP_ONCE_N", "HITAP_EN_COK_SN", "HITAP_EN_COK_SOZ",
                         "HITAP_ONCE", "HITAP_IC_2K", "HITAP_IC_YAKIN", "HITAP_IC_EDAT", "HITAP_IC_SOZ") for x in n.targets))], []), "sozluk.py", "exec"), ns)
bk = ast.parse(src)
exec(compile(ast.Module([n for n in bk.body if (isinstance(n, ast.FunctionDef) and n.name in ("_ad_anahtar", "_ad_mesafe", "hitap_yakin")) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in ("_AD_HARF", "HITAP_YER_RX") for x in n.targets))], []), "bas-konus.py", "exec"), ns)
exec(src[src.index("KONUS_ISTEM = {"):src.index("# --- Hızlı bilgi")], ns)
exec(oku("aktarici", "bellek.py"), ns)

# --- yükleme ve varsayılan muhatap
ks = ns["kisilikler"]()
ok("üç kişilik yüklendi, sıra toplantı → toplantı dışı → dış", [k["ad"] for k in ks] == ["Atlas", "Matlas", "ROXANE"] and [k["rol"] for k in ks] == ["toplanti", "disi", "dis"])
ok("asistan_adlari üçünü de verir (görünen ad), asistan_ad toplantı kişiliği", ns["asistan_adlari"]() == ["Atlas", "Matlas", "Roxane"] and ns["asistan_ad"]() == "Atlas")
ok("varsayılan: toplantıda Atlas, toplantı dışında Matlas; dış kişilik hiçbir zaman varsayılan değil", ns["kisilik"]()["ad"] == "Matlas" and (ns["TOP"].__setitem__(0, True) or ns["kisilik"]()["ad"] == "Atlas"))
ns["TOP"][0] = False
ns["AYAR"]["kisilik"] = k1; ns["AYAR"]["kisilik_toplanti_disi"] = k1
ok("aynı dosya iki yuvada bir kez gelir", [k["ad"] for k in ns["kisilikler"]()] == ["Atlas", "ROXANE"])
ns["AYAR"]["kisilik"] = ""; ns["AYAR"]["kisilik_toplanti_disi"] = ""
ok("yalnız dış kişilik tanımlıysa o tek muhatap", [k["ad"] for k in ns["kisilikler"]()] == ["ROXANE"] and ns["asistan_ad"]() == "Roxane")
ns["AYAR"].update(kisilik=k1, kisilik_toplanti_disi=k2)
ok("hitap listesi: 2 harfli 'Ro' kalır, gündelik sözcük atılır", "Ro" in ks[2]["hitap"] and ns["hitap_suz"](["Oh", "Ah", "Ro", "R"], "Roxane") == ["Ro"])
uz, kisa = ns["hitap_ayir"](ks[2])
ok("kısa takma adlar: Roxy, Rox, Roks, Raks, Ro; uzun: Roxane, Roksi", sorted(kisa) == sorted(["Roxy", "Rox", "Roks", "Raks", "Ro"]) and sorted(uz) == sorted(["Roxane", "Roksi"]))
ok("adı ≤ 4 harfli kişilikte kısa biçim yok (Atlas'ın hitapları hepsi uzun)", ns["hitap_ayir"](ks[0])[1] == [] and ns["hitap_kisa"]({"ad": "ZETA", "hitap": ["Zeta"]}, "Zeta") is False)
ok("Whisper istemi/_hitap_adlari yalnız uzun biçimler", set(ns["_hitap_adlari"]()) == {"Atlas", "Atlaz", "Matlas", "Roxane", "Roksi"} and "Ro" in ns["_hitap_adlari"](hepsi=True))

# --- hitap: yazılı/sesli kullanıcı satırı (hitap_duzelt → "Claude: ")
def hd(t): ns["_KHR"].update(satir=None); c = ns["hitap_duzelt"](t)[0]; return c, ns["_KHR"].get("satir")
GEC = [("Ro, bu firma kim?", "Claude: bu firma kim?"), ("Rox, bu firma kim?", "Claude: bu firma kim?"), ("Roks: bu firmanın alan adı kaç yaşında?", "Claude: bu firmanın alan adı kaç yaşında?"),
       ("Raks bu firmayı biliyor musun?", "Claude: bu firmayı biliyor musun?"), ("Tamam, Ro, bir bak.", "Tamam, Claude: bir bak."), ("Roxane, bu firma kim?", "Claude: bu firma kim?"),
       ("Roksi bu firma kim?", "Claude: bu firma kim?"), ("Roxane gelsin.", "Claude: gelsin.")]
for g, b in GEC:
    c, ad = hd(g); ok(f"seslenme tanındı: {g!r} → {ad}", c == b and ad == "ROXANE")
GECMEZ = ["raks gösterisi", "Raks gösterisi çok güzeldi.", "rol dağılımı belli mi", "rota değişti.", "robot kolu geldi", "rapor hazır.", "Rostov'a gidiyoruz.", "Roxy gösterisi iyiydi.", "pro sürüm gerekli", "Ro gelsin.",
          "Rox gelsin.", "Ro. Bu firma kim", "Roksan'ın evi", "Ro... bu firma kim", "Rox kapıyı çaldı ve gitti.", "Roman okudum.", "Rok gibi sağlam."]
for g in GECMEZ:
    c, ad = hd(g); ok(f"seslenme değil: {g!r}", c == g and ad is None)
c, ad = hd("Ro, sen de bak: Raks mı demişti?"); ok("kısa ad ardından virgülle: cümlenin geri kalanındaki 'Raks' bir şeyi değiştirmez", c.startswith("Claude: sen de bak") and ad == "ROXANE")
# cümle içi (hitap_icte): kısa takma ad sayılmaz, uzun sayılır
r = ns["hitap_icte"]("Peki Rox, bu firma kim?"); ok("cümle ortasında kısa ad seslenme değil", r is None)
r = ns["hitap_icte"]("Peki Roxane, bu firma kim?"); ok("cümle ortasında uzun ad seslenme (eski kural)", r is not None and r[1] == "Roxane")
# ses benzerliği: kısa adlar hedef değil, uzun adlar eskisi gibi
ok("ses benzerliği: kısa adlar hedef değil ('Rahs bu kim?' → Raks olmaz; 'Rop bu kim?' değişmez)", ns["hitap_ses_duzelt"]("Rahs bu kim?") == "Rahs bu kim?" and ns["hitap_ses_duzelt"]("Rop bu kim?") == "Rop bu kim?")
ok("ses benzerliği: uzun ad hâlâ eşlenir ('Roxanne bu firma kim?' → Roxane)", ns["hitap_ses_duzelt"]("Roxanne bu firma kim?") == "Roxane bu firma kim?")
ok("hitap_yakin: kısa ad yakınlık hedefi değil ('Rahs, bu kim?' / 'Rax, bu kim?' değişmez); uzun ad eşlenir ('Roxanne, bu kim?' → Roxane)",
   ns["hitap_yakin"]("Rahs, bu kim?") == "Rahs, bu kim?" and ns["hitap_yakin"]("Rax, bu kim?") == "Rax, bu kim?" and ns["hitap_yakin"]("Roxanne, bu kim?") == "Roxane, bu kim?")
# tek başına satır (hitap_yalniz_ad) ve karşı taraf
ok("tek başına satır: 'Ro,' → hitap; 'Ro' / 'Ro.' değil; 'Roxane' hitap", ns["hitap_yalniz_ad"]("Ro,") == "Ro" and ns["hitap_yalniz_ad"]("Ro") is None and ns["hitap_yalniz_ad"]("Ro.") is None and ns["hitap_yalniz_ad"]("Roxane") == "Roxane")
cz = ns["karsi_hitap_cozumle"]
ok("karşı taraf: 'Rox, bu firma kim?' → Roxane; 'Raks gösterisi' / 'Rahs bu firma kim?' (ses benzerliği kapalı) / 'Ro gelsin' değil",
   (cz("Rox, bu firma kim?") or (None,))[0] == "ROXANE" and cz("Raks gösterisi başlıyor.") is None and cz("Rahs bu firma kim?") is None and cz("Ro gelsin.") is None)
ok("karşı taraf: uzun ad etiketle ve ses benzerliğiyle hâlâ çalışır; kısa adla etiket yok",
   (cz("Roxane Kaya: bu firma kim?") or (None, None, None))[2] == "etiket" and (cz("Roxanne, bu firma kim?") or (None, None, None))[2] == "ses" and (cz("Rox Kaya: bu işi bil.") or (None, None, None))[2] != "etiket")

# --- kisilik_hitap_bul (Konuş kutusu/sesli, bas-konuş; adla seçim)
b = ns["kisilik_hitap_bul"]
ok("kisilik_hitap_bul: 'Ro, bu firma kim?' / 'Roxane bak şuna' / 'Roksi?' → Roxane", b("Ro, bu firma kim?")[0]["ad"] == "ROXANE" and b("Roxane bak şuna")[0]["ad"] == "ROXANE" and b("Roksi?")[0]["ad"] == "ROXANE")
ok("kisilik_hitap_bul: 'Ro?' tek başına çağırır; 'Ro.' / 'Raks gösterisi' / 'rol dağılımı' / 'Ro gelsin' çağırmaz", b("Ro?")[0] and b("Ro?")[0]["ad"] == "ROXANE" and b("Ro.")[0] is None and b("Raks gösterisi")[0] is None and b("rol dağılımı")[0] is None and b("Ro gelsin")[0] is None)
ok("kisilik_hitap_bul: kısa ad + soru biçimi ('Rox nasıl ilerliyor?') evet; soru yoksa ('Rox gösterisi iyiydi') hayır", b("Rox nasıl ilerliyor?")[0]["ad"] == "ROXANE" and b("Rox gösterisi iyiydi")[0] is None)
ok("kisilik_hitap_bul: öteki kişilikler eskisi gibi ('Atlas bak', 'Matlas, özet?')", b("Atlas bak şuna")[0]["ad"] == "Atlas" and b("Matlas, özet?")[0]["ad"] == "Matlas")
# adla seslenince 3 dk sürer, sonra varsayılana döner
ns["kisilik_sec"]("ROXANE"); ok("adla seslenince Roxane cevaplar (sonraki adsız soru da, 3 dk içinde)", ns["kisilik"]()["ad"] == "ROXANE")
ns["_KSEC"]["t"] = time.time() - ns["KISILIK_SURE_SN"] - 5; ok("3 dk sonra varsayılana dönülür (toplantı dışı: Matlas)", ns["kisilik"]()["ad"] == "Matlas")
ns["kisilik_sec"](None)
# --- asistan_katil / toplantı akışı (S94)
ns["TOP"][0] = True; ns["STATE"] = {"meeting": "Deneme"}
ns["asistan_katil"]("ROXANE"); ok("toplantıda 'Roxane' çağrılınca katılır, görünüm adı 'Roxane'", ns["asistan_katilan"]() == ["ROXANE"] and ns["asistan_view"]()["katilan"] == ["Roxane"] and ns["asistan_view"]()["adlar"] == ["Atlas", "Matlas", "Roxane"])
ns["TOP"][0] = False
# --- Konuş istemi
ist = ns["konus_istem"]()
ok("istem: üç kişilik, dış kişilik yalnız adıyla çağrılır, üç metin de var", "Aşağıda üç kişilik var" in ist and "Atlas toplantıda, Matlas toplantı dışında varsayılandır" in ist and "ROXANE dış işler asistanıdır" in ist
   and "yalnız kullanıcı adıyla seslenince" in ist and all(x in ist for x in ("BİRİNCİ-İŞARET", "İKİNCİ-İŞARET", "ÜÇÜNCÜ-İŞARET")))
ok("istem: dış kişiliğin söyleniş listesi (Roksi, Roxy, Rox, Ro …) adının yanlış duyulması sayılır", "ROXANE: Roksi, Roxy, Rox, Roks, Raks, Ro" in ist)
ns["AYAR"]["kisilik_dis"] = ""; i2 = ns["konus_istem"]()
ok("dış yuva boşken iki kişilik istemi eskisi gibi", "Aşağıda iki kişilik var: Atlas toplantıda, Matlas toplantı dışında varsayılandır; kullanıcı adıyla seslenerek öbürünü çağırabilir. Her mesajın başında" in i2 and "ÜÇÜNCÜ" not in i2)
ns["AYAR"].update(kisilik="", kisilik_toplanti_disi=k2, kisilik_dis=k3); i3 = ns["konus_istem"]()
ok("toplantı kişiliği yokken: 'Matlas varsayılandır' + dış kişilik", "Aşağıda iki kişilik var: Matlas varsayılandır" in i3 and "ROXANE dış işler asistanıdır" in i3)
shutil.rmtree(T, ignore_errors=True)
print("kişilik-dis:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
