#!/usr/bin/env python3
# Zekâ altın seti (G3, 12 Kasım): kullanıcının düzelttirdiği gerçek hataların modelsiz sınanabilir örnekleri. Örnek verisi `testler/altin/*.json` (git DIŞI; kişi adı içerebilir ama kurgu/kısaltılmış tutulur;
# kural: her yeni düzeltme bir örnek ekler, `testler/altin/OKU.md`). Koşucu kural katmanını çağırır — model yok, ağ yok, gerçek canli/'ye yazmaz:
#   tur "gundem"  → yapi.guncellik_olay + gundem_taslagi (yapay graf: toplantılar + işler/kararlar); "olmali": gundem_basliklar (omurga), bagli/taslak (öneri listelerinde geçmesi gereken metin parçaları);
#                   "olmamali": önerilen listelerin (bağlı adaylar, ek öneri, belirsiz, taslak, gündem taslağı satırları) hiçbirinde geçmeyecek metin parçaları (bitmiş/bayat/ilgisiz/üçüncü kişi).
#   tur "eposta"  → aktarici/eposta-takip.py et_analiz (zincir birleştirme dahil): "olmali"/"olmamali" = "cevap bekliyor" listesinde bulunacak / bulunmayacak ileti kimlikleri.
# Her OLMALI/OLMAMALI satırı bir kontroldür; isabet = geçen/toplam kontrol. Klasör yoksa "atlandı" (başarısız sayılmaz; açık depoda klasör yok).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/zeka-altin.py [--klasor YOL] [--kaydet CANLI_YOLU]   (kalan kontrol → çıkış 1)
#   --kaydet: sonucu <canli>/altin-sonuc.json'a yazar (yalnız sayı; zeka.py karnesi "Altın set" ölçütü bunu okur). Varsayılan: yazmaz.
import datetime, glob, json, os, re, shutil, sys, tempfile, collections, threading, time
sys.dont_write_bytecode = True; KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
ARG = sys.argv[1:]
def arg(ad):
    return ARG[ARG.index(ad) + 1] if ad in ARG and ARG.index(ad) + 1 < len(ARG) else None
KLASOR = arg("--klasor") or os.path.join(KOD, "testler", "altin")
KAYDET = arg("--kaydet")
dosyalar = sorted(glob.glob(os.path.join(KLASOR, "*.json")))
if not dosyalar:
    print(f"atlandı — altın set klasörü yok ya da boş ({KLASOR}); git dışı olduğu için bu normal"); sys.exit(0)
import yapi
SONUC = []  # (örnek, kontrol, geçti, ek)
BILINEN = set()  # "bilinen_acik": true örnekler: hata bildirilmedi, tasarım sorusu; basılır ama toplamlara girmez
def bak(ornek, ad, k, ek=""):
    if ornek in BILINEN: print(("  ~ (bilinen açık, sayılmaz) " + ("tuttu " if k else "tutmadı ")) + ad); return
    SONUC.append((ornek, ad, bool(k), ek)); print(("  ✓ " if k else "  ✗ ") + ad + (f" — {ek}" if ek and not k else ""))

# ---- gündem / hazırlık ----
def gundem_ornegi(ad, d):
    T = tempfile.mkdtemp(prefix="suflor-altin-"); C = os.path.join(T, "canli"); os.makedirs(C)
    try:
        bugun = datetime.date.fromisoformat(d.get("bugun") or "2026-11-12"); kullanici = d.get("ad") or ""; kapat = []
        for t in d.get("toplantilar") or []:
            open(os.path.join(C, t["toplanti"] + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {t['toplanti']}\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n| 10:00:00 | X | m | |\n")
            ogeler = []
            for o in t.get("ogeler") or []:
                o = dict(o)
                if o.pop("kapat", None): kapat.append(o.get("metin"))
                ogeler.append(o)
            yapi.graf_yaz(C, {"baslik": t.get("baslik") or t["toplanti"], "tarih": t.get("tarih"), "maddeler": [{"baslik": "G", "ogeler": ogeler}]}, t["toplanti"] + ".md")
        for m in kapat:
            for x in yapi.kayit_listesi(C, kullanici, bugun)["kayitlar"]:
                if x["metin"] == m: yapi.soz_kapat(C, x["id"], "yapildi"); break
        o = d.get("olay") or {}
        v = yapi.guncellik_olay(C, o, kullanici, bugun=bugun, epostalar=d.get("epostalar"))
        kat = [str(x) for x in o.get("katilimcilar") or []]
        gt = yapi.gundem_taslagi(C, kat, kullanici, str(o.get("baslik") or ""), bugun=bugun, etkinlik=str(o.get("id") or ""), notlar=str(o.get("notlar") or ""), epostalar=d.get("epostalar"), ilgi=v)
        oner = [x["metin"] for g in v["gundem"] for x in g["adaylar"]] + [x["metin"] for k in ("ek_oneri", "belirsiz", "taslak") for x in v[k]] + [m["satir"] for m in gt["maddeler"] if m.get("tur") != "gundem"] + [a for m in gt["maddeler"] for a in m.get("adaylar") or []]
        yaz = lambda m: any(p.lower() in str(s).lower() for s in oner for p in [m])
        ol = d.get("olmali") or {}
        if "gundem_basliklar" in ol:
            bak(ad, "omurga: davetin maddeleri sırasıyla (gündem varken kendi madde uydurmaz)", v["davet"] and [g["baslik"] for g in v["gundem"]] == ol["gundem_basliklar"], [g["baslik"] for g in v["gundem"]])
        for m in (ol.get("bagli") or []) + (ol.get("taslak") or []):
            bak(ad, f"OLMALI: «{m}» önerilir", yaz(m))
        for m in d.get("olmamali") or []:
            bak(ad, f"OLMAMALI: «{m}» önerilmez", not yaz(m), [s for s in oner if m.lower() in str(s).lower()][:1])
    finally: shutil.rmtree(T, ignore_errors=True)

# ---- e-posta zinciri ----
_NS = None
def eposta_ns():
    global _NS
    if _NS: return _NS
    class Beyin:
        tur = "claude-code"
        @staticmethod
        def secim(ayar, is_): return {"tur": Beyin.tur, "model": None}
    ns = {"__name__": "et", "collections": collections, "re": re, "os": os, "json": json, "time": time, "datetime": datetime, "threading": threading, "BASE": tempfile.mkdtemp(prefix="suflor-altin-et-"),
          "AYAR": {"eposta_oku": True, "eposta_takip": True}, "POSTA": {"iletiler": [], "durum": "ok"}, "_t": lambda tr, en: tr, "ARAYUZ_DILI": "tr", "bildirim": lambda *a, **k: None, "seslendir": lambda *a, **k: None,
          "toplanti_var": lambda: False, "aktif_dosya": lambda: None, "gizli_acik": lambda: False, "SOHBET": {"acik": False}, "BEYIN": Beyin, "eylem_model": lambda *a, **k: ("[]", None), "baglam_paketi": lambda *a, **k: "",
          "posta_vt_kisiler": lambda: [], "posta_govde_al": lambda ids, kar=None: {}, "posta_kullanici_sorusu": lambda: True, "_yapi_mod": lambda: None}
    exec(compile(open(os.path.join(KOD, "aktarici", "eposta-takip.py"), encoding="utf-8").read(), "eposta-takip.py", "exec"), ns); _NS = ns; return ns
def eposta_ornegi(ad, d):
    ns = eposta_ns(); simdi = datetime.datetime.fromisoformat(d["simdi"])
    c = ns["et_analiz"](d["iletiler"], simdi, kisiler=set(d.get("kisiler") or []), kayit_kelime=[], durum={"yoksay": {}, "ertele": {}, "zd": {}}, beklenen=False)
    bek = [str(o["id"]) for o in c["bekleyen"]]
    for i in (d.get("olmali") or {}).get("bekleyen") or []: bak(ad, f"OLMALI: ileti {i} «cevap bekliyor» listesinde", str(i) in bek, bek)
    for i in d.get("olmamali") or []: bak(ad, f"OLMAMALI: ileti {i} «cevap bekliyor» listesinde (cevaplandı)", str(i) not in bek, bek)

for f in dosyalar:
    ad = os.path.basename(f); print(ad)
    try: d = json.load(open(f, encoding="utf-8"))
    except Exception as e: bak(ad, "örnek dosyası okunamadı", False, str(e)); continue
    if d.get("bilinen_acik"): BILINEN.add(ad)
    try:
        {"gundem": gundem_ornegi, "eposta": eposta_ornegi}.get(d.get("tur"), lambda a, x: bak(a, f"bilinmeyen tür {d.get('tur')!r}", False))(ad, d)
    except Exception as e: bak(ad, "koşu hatası", False, f"{e.__class__.__name__}: {e}")
g = sum(1 for s in SONUC if s[2]); t = len(SONUC); ornek = len({s[0] for s in SONUC}); kalan_ornek = len({s[0] for s in SONUC if not s[2]})
print(f"\nAltın set isabeti: {g}/{t} kontrol (%{100 * g // t if t else 0}); {ornek} örnek, {kalan_ornek} örnekte kalan var")
if KAYDET:
    os.makedirs(KAYDET, exist_ok=True)
    json.dump({"gecen": g, "toplam": t, "ornek": ornek, "zaman": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}, open(os.path.join(KAYDET, "altin-sonuc.json"), "w"))
    print(f"sonuç yazıldı: {os.path.join(KAYDET, 'altin-sonuc.json')}")
sys.exit(0 if g == t else 1)
