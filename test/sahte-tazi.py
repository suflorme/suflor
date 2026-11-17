#!/usr/bin/env python3
# Sahte Tazı hizmeti (S321): Suflor testleri Tazı'nın gerçek kodunu çalıştırmaz; istemci (aktarici/tazi-istemci.py) bu dosyayı
# TAZI_HIZMET ya da ayar tazi_yol ile gerçek tazi_hizmet.py yerine çağırır. Sözleşme aynı: `<islem> --json-girdi -`, çıktı tek JSON nesnesi, çıkış 0/1.
# Ortam: SAHTE_TAZI = durum dosyası (JSON: kayitlar [{id, ad, alanlar, kisiler, esler (ek eşleşme sözleri)}], ozet {id: metin}, satir {id: satır}, raporlar [..], rapor_metin {dosya: metin},
#        kesisim {kesisim_verisi sözlüğü}); yoksa boş. SAHTE_TAZI_GUNLUK = her çağrı bir JSON satırı ({"islem", ...girdi}).
#        SAHTE_TAZI_HATA = "islem:kod,…" (o işlem hata döner), SAHTE_TAZI_BOZUK=1 (JSON olmayan çıktı), SAHTE_TAZI_UYKU = saniye.
# Eşleştirme kuralı bilerek basittir (küçük harf alt dize): Tazı'nın gerçek eşleştirmesi Tazı deposunda sınanır.
import json, os, re, sys, time


def kucuk(s):
    return str(s or "").replace("I", "ı").replace("İ", "i").lower()


def slug(s):
    t = kucuk(s).translate(str.maketrans("çğıöşü", "cgiosu"))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "kayit"


def oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def bul(D, q):
    q = kucuk(q).strip()
    if not q:
        return None
    for k in D.get("kayitlar") or []:
        if q == k["id"] or q in [kucuk(a) for a in k.get("alanlar") or []]:
            return k
    for k in D.get("kayitlar") or []:
        if len(q) >= 3 and (q in kucuk(k["ad"]) or any(q in kucuk(p) for p in list(k.get("kisiler") or []) + list(k.get("esler") or []))):
            return k
    return None


def kisa(k):
    return {"id": k["id"], "ad": k["ad"], "alanlar": list(k.get("alanlar") or []), "aday": bool(k.get("aday"))}


def main():
    islem = sys.argv[1] if len(sys.argv) > 1 else ""
    g = json.loads(sys.stdin.read() or "{}") if "-" in sys.argv[2:] else {}
    yol = os.environ.get("SAHTE_TAZI") or ""
    D = oku(yol)
    if os.environ.get("SAHTE_TAZI_GUNLUK"):
        with open(os.environ["SAHTE_TAZI_GUNLUK"], "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(g, islem=islem), ensure_ascii=False, sort_keys=True) + "\n")
    time.sleep(float(os.environ.get("SAHTE_TAZI_UYKU") or 0))
    if os.environ.get("SAHTE_TAZI_BOZUK"):
        print("Traceback (most recent call last): bozuk")
        return 1
    hatalar = dict(x.split(":", 1) for x in (os.environ.get("SAHTE_TAZI_HATA") or "").split(",") if ":" in x)
    if islem in hatalar:
        print(json.dumps({"ok": False, "hata": hatalar[islem]}))
        return 1
    r = None
    if islem == "surum":
        r = {"islemler": []}
    elif islem == "durum":
        r = {"kayit_sayisi": len(D.get("kayitlar") or []), "aday_sayisi": sum(1 for k in D.get("kayitlar") or [] if k.get("aday")), "son_tarama": None, "indeks_var": False}
    elif islem == "eslesen_kayitlar":
        m = kucuk(g.get("metin"))
        yer = []
        for k in D.get("kayitlar") or []:
            ys = [m.find(kucuk(a)) for a in [k["ad"]] + list(k.get("alanlar") or []) + list(k.get("kisiler") or []) + list(k.get("esler") or []) if a and kucuk(a) in m]
            if ys:
                yer.append((min(ys), k))
        r = {"kayitlar": [kisa(k) for _, k in sorted(yer, key=lambda x: x[0])][:int(g.get("en_cok") or 3)]}
    elif islem == "kayit_bul":
        k = bul(D, g.get("sorgu"))
        r = {"kayit": kisa(k) if k else None}
    elif islem in ("ozet", "ozet_satiri"):
        k = bul(D, g.get("sorgu"))
        v = (D.get("ozet" if islem == "ozet" else "satir") or {}).get(k["id"]) if k else None
        r = {"metin": v} if islem == "ozet" else {"satir": v}
    elif islem == "aday_ekle":
        k = bul(D, g.get("alan") or g.get("ad")) or bul(D, g.get("ad"))
        if k:
            r = {"durum": "var", "kayit_id": k["id"]}
        else:
            k = {"id": slug(g.get("ad")), "ad": g.get("ad"), "alanlar": [g["alan"]] if g.get("alan") else [], "kisiler": [], "aday": True}
            D.setdefault("kayitlar", []).append(k)
            if yol:
                json.dump(D, open(yol, "w", encoding="utf-8"), ensure_ascii=False)
            r = {"durum": "yeni", "kayit_id": k["id"]}
    elif islem == "tara":
        r = {"cikti": "tarama bitti"} if bul(D, g.get("kim")) else None
        if r is None:
            print(json.dumps({"ok": False, "hata": "kayit_yok"}))
            return 1
    elif islem == "dosya_ekle":
        D["son_no"] = int(D.get("son_no") or 10) + 1
        if yol:
            json.dump(D, open(yol, "w", encoding="utf-8"), ensure_ascii=False)
        r = {"no": D["son_no"]}
    elif islem == "dosya_kapat":
        r = {"no": g.get("no")}
    elif islem == "sorgu_kaydet":
        r = {}
    elif islem == "raporlar":
        r = {"raporlar": (D.get("raporlar") or [])[:int(g.get("en_cok") or 5)]}
    elif islem == "rapor_oku":
        f = g.get("dosya")
        if f not in (D.get("rapor_metin") or {}):
            print(json.dumps({"ok": False, "hata": "yok"}))
            return 1
        r = {"dosya": f, "tur": "tazi", "t": 1_800_000_000, "metin": D["rapor_metin"][f]}
    elif islem == "kesisim_verisi":
        r = D.get("kesisim") or {"yok": True, "kayit": {}, "oge": [], "bulgu": [], "iletisim": [], "son_indeks": None, "tarama": {}}
    if r is None:
        print(json.dumps({"ok": False, "hata": "islem_yok"}))
        return 1
    print(json.dumps(dict(r, ok=True, arayuz_surum=1), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
