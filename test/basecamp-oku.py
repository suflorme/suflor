#!/usr/bin/env python3
# Basecamp OKUMA bağlayıcısı (S282): aktarici/basecamp-oku.py — kapalı/gizli/beta durumları, proje seçimi, yorum+iş okuma, bc_kanit imzası (alıntı ≤160, maske, tarih süzgeci),
# 30 dk önbellek, 429 yeniden deneme, istek sınırı, ağ hatasında sessiz boş + geri çekilme, belirteç yokken boş. Sahte HTTP; gerçek ağ ve Anahtar Zinciri yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/basecamp-oku.py      (kaldı → çıkış 1)
import os, sys, json, time, re, urllib.error, io
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
SAAT = [1000.0]; BEKLE = []; ISTEK = []; MOD = {"hata": None}
POSTA = "a" + "@" + "b.test"
PROJELER = [{"id": 1, "name": "Orbitek Entegrasyon"}, {"id": 2, "name": "Kurumsal Site"}]
def sahte_http(url):
    ISTEK.append(url)
    if MOD["hata"] == "ag": raise OSError("ag yok")
    if MOD["hata"] == "429" and len([u for u in ISTEK if "projects.json" in u]) == 1:
        raise urllib.error.HTTPError(url, 429, "x", {"Retry-After": "3"}, io.BytesIO(b""))
    if url.endswith("/projects.json"): return PROJELER, None
    if "type=Comment&bucket=1" in url: return [{"content": f"<p>Sözleşme imzası tamamlandı, bkz {POSTA}</p>", "updated_at": "2026-11-09T10:00:00Z"},
                                                {"content": "Eski not", "updated_at": "2026-10-01T10:00:00Z"}], None
    if "type=Todo&bucket=1" in url: return [{"title": "Sözleşme imzası için entegrasyon planı", "completed": True, "due_on": "2026-11-08", "updated_at": "2026-11-10T08:00:00Z",
                                              "assignees": [{"name": "Atanan Kisi"}]}, {"title": "Alakasız iş", "completed": False, "updated_at": "2026-11-10T08:00:00Z"}], None
    return [], None
AYAR = {"basecamp_oku": True, "basecamp": {"hesap": "123", "proje_esleme": {}}}; GIZLI = {"acik": False}
def gizli_acik(): return GIZLI["acik"]
def gelistirici_mi(): return False
G = {"__name__": "bc", "AYAR": AYAR, "BASE": "/tmp", "time": time, "json": json, "re": re, "os": os, "gizli_acik": gizli_acik, "gelistirici_mi": gelistirici_mi,
     "BC_HTTP": sahte_http, "BC_ZAMAN": lambda: SAAT[0], "BC_BEKLE": lambda s: (BEKLE.append(s), SAAT.__setitem__(0, SAAT[0] + s))}
exec(compile(open(os.path.join(KOD, "aktarici", "basecamp-oku.py"), encoding="utf-8").read(), "basecamp-oku.py", "exec"), G)
def sifirla(): G["BC"].update(onb={}, istek=[], geri=0.0, hata=0); ISTEK.clear(); BEKLE.clear(); MOD["hata"] = None; SAAT[0] += 5000
X = {"metin": "Sözleşme imzası için entegrasyon planı hazırlanacak", "tarih": "2026-11-05", "baslik": "Orbitek toplantısı"}
# 1) kapalı durumlar
sifirla(); AYAR["basecamp_oku"] = False; ok("kapalı → bc_acik False, istek yok", not G["bc_acik"]() and G["bc_kanit"](X) == [] and not ISTEK)
AYAR["basecamp_oku"] = True; GIZLI["acik"] = True; ok("gizli kipte okunmaz", not G["bc_acik"]() and G["bc_oku"]("Orbitek")["isler"] == [] and not ISTEK); GIZLI["acik"] = False
del AYAR["basecamp_oku"]; ok("ayar yok + geliştirici değil (beta) → kapalı", not G["bc_acik"]()); G["gelistirici_mi"] = lambda: True; ok("ayar yok + geliştirici → açık", G["bc_acik"]())
AYAR["basecamp_oku"] = True; AYAR["basecamp"]["hesap"] = ""; ok("hesap yok → kapalı", not G["bc_acik"]()); AYAR["basecamp"]["hesap"] = "123"
# 2) okuma + proje seçimi
sifirla(); d = G["bc_oku"]("Orbitek toplantısı")
ok("başlıkla ilgili proje seçildi (yalnız Orbitek)", d["projeler"] == ["Orbitek Entegrasyon"])
ok("yorum ve iş sayıları", len(d["yorumlar"]) == 2 and len(d["isler"]) == 2)
i = d["isler"][0]; ok("iş alanları (sahip, vade, tamam, tarih)", i["sahip"] == "Atanan Kisi" and i["vade"] == "2026-11-08" and i["tamam"] and i["tarih"] == "2026-11-10")
ok("yorumda HTML sıyrıldı", "<p>" not in d["yorumlar"][0]["metin"])
n = len(ISTEK); G["bc_oku"]("Orbitek toplantısı"); ok("30 dk önbellek: ikinci çağrıda istek yok", len(ISTEK) == n)
SAAT[0] += 1900; G["bc_oku"]("Orbitek toplantısı"); ok("önbellek 30 dk sonra tazelenir", len(ISTEK) > n)
AYAR["basecamp"]["proje_esleme"] = {"entegrasyon": "Kurumsal Site"}; sifirla(); ok("eşleme tablosu önce gelir", G["bc_oku"]("Entegrasyon haftası")["projeler"] == ["Kurumsal Site"]); AYAR["basecamp"]["proje_esleme"] = {}
# 3) bc_kanit
sifirla(); k = G["bc_kanit"](X)
ok("kanıt: kaynak basecamp, ≤160, en çok 2", 1 <= len(k) <= 2 and all(z["kaynak"] == "basecamp" and len(z["alinti"]) <= 160 and z["tarih"] for z in k))
ok("kanıt: e-posta maskeli", all(POSTA not in z["alinti"] for z in k) and any("[adres]" in z["alinti"] for z in k))
ok("kanıt: yeniden eskiye, alakasız iş yok", k == sorted(k, key=lambda z: z["tarih"], reverse=True) and not any("Alakasız" in z["alinti"] for z in k))
ok("kanıt: kayıt tarihinden önceki yorum yok", not any("Eski not" in z["alinti"] for z in k))
ok("bc_baglam kısa metin, adres yok", "Basecamp (Orbitek Entegrasyon)" in G["bc_baglam"]("Orbitek toplantısı") and POSTA not in G["bc_baglam"]("Orbitek toplantısı"))
G["_mtb_kanit"] = lambda kay, t, a: None if "imzası" in a else {"kaynak": kay, "tarih": t, "alinti": a}; sifirla(); ok("mutabakat süzgeci (_mtb_kanit None) kanıtı atar", G["bc_kanit"](X) == []); del G["_mtb_kanit"]
# 4) dayanıklılık
sifirla(); MOD["hata"] = "ag"; ok("ağ yok → sessiz boş", G["bc_oku"]("Orbitek")["isler"] == [] and G["bc_kanit"](X) == [])
n = len(ISTEK); G["bc_oku"]("Orbitek"); ok("hata sonrası 5 dk geri çekilme (yeni istek yok)", len(ISTEK) == n)
SAAT[0] += 400; MOD["hata"] = None; ok("geri çekilme bitince yeniden dener", len(G["bc_oku"]("Orbitek")["isler"]) == 2)
sifirla(); MOD["hata"] = "429"; ok("429 → Retry-After kadar bekleyip yeniden dener", len(G["bc_oku"]("Orbitek")["isler"]) == 2 and 3.0 in BEKLE)
sifirla(); G["BC"]["istek"] = [SAAT[0]] * 40; G["_bc_sinir"](); ok("istek penceresi dolunca bekler", BEKLE and BEKLE[0] > 9)
G2 = dict(G); G2.pop("BC_HTTP"); G2["BC_ZAMAN"] = time.time; G2["BC_BEKLE"] = time.sleep
exec(compile(open(os.path.join(KOD, "aktarici", "basecamp-oku.py"), encoding="utf-8").read(), "basecamp-oku.py", "exec"), G2)
G2["_bc_belirtec"] = lambda: ""; G2["AYAR"]["basecamp_oku"] = True; ok("belirteç yok → ağa çıkmadan boş", G2["bc_oku"]("Orbitek")["isler"] == [])
print(f"\n{'TAMAM' if not HATA else 'KALDI: ' + ', '.join(HATA)}"); sys.exit(1 if HATA else 0)
