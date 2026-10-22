#!/usr/bin/env python3
# Haftalık kullanım sayımı — tek kaynak (S141, 23 Ekim). İki yerden çağrılır: ölçüm aracı (`olcum.py kullanim`, geliştiricinin Mac'i) ve
# aktarıcının haftalık beta paketi (aktarici/beta-veri.py). Kural ikisinde aynı kalsın diye burada. Yalnız sayı döner: soru, kart ve
# toplantı metni, toplantı dosya adı çıktıya girmez (dosya adları yalnız iç sayımda küme anahtarı).
# Okunan kayıtlar (aktarıcının canli/ klasörü): claude-cagri.jsonl (is: bas-konus = asistana soru, is: toplanti = toplantı oturumu ve deneme
# etiketi), kartlar.jsonl (kartın ilk kaydı + son durumu), 20…-….jsonl (toplantı dökümü; kartsız toplantı da sayılsın), isteğe bağlı
# kullanim-etiket.jsonl (aralıkla deneme/gerçek etiketi; yalnız geliştirici kullanır).
import datetime, gzip, json, os, re

KAYNAK = {"bas": "sesli", "yazili": "yazili", "sohbet": "sohbet", "hitap": "herkese", "karsi": "karsi", "ozet": "ozet"}  # claude-cagri kaynak → sayım anahtarı (toplantıda sesli = kulaga)

def kayit_satirlari(canli, ad):
    # aktarıcı büyüyen ölçüm kayıtlarını döndürür (v0.24.2): eski satırlar canli/arsiv/<ad>.gz'de, yeniler canli/<ad>'de — ikisi sırayla
    out = []
    for yol, ac in ((os.path.join(canli, "arsiv", ad + ".gz"), lambda y: gzip.open(y, "rt", encoding="utf-8")), (os.path.join(canli, ad), lambda y: open(y, encoding="utf-8"))):
        try:
            with ac(yol) as f: out += [l for l in f if l.strip()]
        except (OSError, EOFError): pass
    return out
def zaman(t):
    d = datetime.datetime.fromisoformat(str(t).replace("Z", "+00:00")); return (d if d.tzinfo else d.astimezone()).timestamp()
def hafta_adi(t): return "%d-H%02d" % t.isocalendar()[:2]
def _an(x, son=False):  # "2026-10-22" (gün) ya da "2026-10-22T17:30" → datetime
    d = datetime.datetime.fromisoformat(x)
    return d + datetime.timedelta(days=1) if son and len(x) == 10 else d
def kart_sonu(durum):  # kartın son durumu → yarar (✓ yaptım / onay) | okundu | gecildi (✕ gerek yok / red) | acik (cevapsız)
    return "yarar" if durum in ("yapildi", "onaylandi") else "okundu" if durum == "okundu" else "gecildi" if durum in ("gecildi", "reddedildi") else "acik"

def haftalik(canli, hafta=4, etiket_dosya=None, simdi=None):
    """Son `hafta` ISO haftası: {"haftalar": [...], "kart_turu": {...}, "etiket_araligi": n}. Deneme toplantıları ve deneme etiketli sorular ayrı sayılır.
    simdi verilirse pencerenin sonu odur (sonrası sayılmaz; haftalık beta paketi biten haftayı sayar)."""
    yerel = lambda iso: datetime.datetime.fromtimestamp(zaman(iso))
    ust = simdi or datetime.datetime.max
    sinir = (simdi or datetime.datetime.now()) - datetime.timedelta(days=7 * hafta)
    cagri = []
    for l in kayit_satirlari(canli, "claude-cagri.jsonl"):
        try: cagri.append(json.loads(l))
        except ValueError: pass
    top, dosya_et = [], {}  # toplantı aralıkları (baş, son, etiket) ve dosya → etiket
    for r in cagri:
        if r.get("is") != "toplanti" or not r.get("etiket"): continue
        try: s_ = yerel(r["at"])
        except (KeyError, TypeError, ValueError): continue
        top.append((s_ - datetime.timedelta(minutes=r.get("sure_dk") or 0), s_, r["etiket"]))
        if r.get("dosya"): dosya_et[r["dosya"]] = r["etiket"]
    aralik = []
    try:
        for l in open(etiket_dosya, encoding="utf-8") if etiket_dosya else ():
            try: r = json.loads(l); aralik.append((_an(r["bas"]), _an(r["son"]), r["etiket"]))
            except (ValueError, KeyError): pass
    except OSError: pass
    def etiket(t, toplantida):
        if toplantida:
            e = next((e for b, s_, e in reversed(top) if b <= t <= s_ + datetime.timedelta(minutes=2)), None)
            if e: return e
        return next((e for b, s_, e in reversed(aralik) if b <= t < s_), None) or "gercek"
    H = {}; TUR = {}
    def kova(t): return H.setdefault(hafta_adi(t), {"disi": {}, "ici": {}, "disi_deneme": 0, "ici_deneme": 0, "disi_gun": set(), "gun": set(), "toplanti": {"gercek": set(), "deneme": set()},
                                                    "kart": 0, "yarar": 0, "okundu": 0, "gecildi": 0, "acik": 0})
    for r in cagri:
        try: t = yerel(r["at"])
        except (ValueError, KeyError, TypeError): continue
        if r.get("is") != "bas-konus" or not sinir <= t < ust: continue
        k = kova(t); yer = "ici" if r.get("toplantida") else "disi"
        if etiket(t, r.get("toplantida")) == "deneme": k[yer + "_deneme"] += 1; continue
        kay = KAYNAK.get(r.get("kaynak"), "diger")
        if yer == "ici" and kay == "sesli": kay = "kulaga"
        k[yer][kay] = k[yer].get(kay, 0) + 1; k["gun"].add(t.date())
        if yer == "disi": k["disi_gun"].add(t.date())
    son, ilk = {}, {}
    for l in kayit_satirlari(canli, "kartlar.jsonl"):
        try: r = json.loads(l)
        except ValueError: continue
        if r.get("kind") and r.get("id") not in ilk: ilk[r["id"]] = r
        if r.get("status"): son[r.get("id")] = r["status"]
    for i, r in ilk.items():
        try: t = yerel(r["at"])
        except (KeyError, TypeError, ValueError): continue
        if not sinir <= t < ust or r.get("kind") == "duygu": continue
        k = kova(t); e = dosya_et.get(r.get("file")) or etiket(t, True)
        if r.get("file"): k["toplanti"][e].add(r["file"])
        if e == "deneme": continue
        c = kart_sonu(son.get(i, "acik"))
        k["kart"] += 1; k[c] += 1; k["gun"].add(t.date())
        tr = TUR.setdefault(r["kind"], {"kart": 0, "yarar": 0, "okundu": 0, "gecildi": 0, "acik": 0}); tr["kart"] += 1; tr[c] += 1
    try: dosyalar = os.listdir(canli)
    except OSError: dosyalar = []
    for f in dosyalar:  # kartsız toplantı da sayılsın: en az 20 döküm satırı olan toplantı dosyası
        m = re.match(r"(\d{4}-\d{2}-\d{2})-\d{4}-.+\.jsonl$", f)
        if not m or f.count(".") != 1: continue
        t = datetime.datetime.strptime(m.group(1), "%Y-%m-%d")
        if not sinir <= t < ust: continue
        try: n = sum(1 for x in open(os.path.join(canli, f), encoding="utf-8", errors="replace") if '"text"' in x)
        except OSError: continue
        md = f[:-6] + ".md"
        if n >= 20:
            e = dosya_et.get(md) or "gercek"; kova(t)["toplanti"][e].add(md)
            if e == "gercek": kova(t)["gun"].add(t.date())
    yz = lambda a, b: round(100 * a / b) if b else None
    out = []
    for ad in sorted(H):
        k = H[ad]; cevap = k["yarar"] + k["okundu"] + k["gecildi"]; tg = k["toplanti"]["gercek"] - k["toplanti"]["deneme"]
        out.append({"hafta": ad, "toplanti_disi": dict(k["disi"], toplam=sum(k["disi"].values())), "toplanti_disi_deneme": k["disi_deneme"],
                    "toplanti_ici": dict(k["ici"], toplam=sum(k["ici"].values())), "toplanti_ici_deneme": k["ici_deneme"], "disi_gun": len(k["disi_gun"]), "gun": len(k["gun"]),
                    "toplanti_gercek": len(tg), "toplanti_deneme": len(k["toplanti"]["deneme"]), "kart": k["kart"],
                    "kart_toplanti_basi": round(k["kart"] / len(tg), 1) if tg else None,
                    "yapildi_yuzde": yz(k["yarar"], cevap), "okundu_yuzde": yz(k["okundu"], cevap), "gecildi_yuzde": yz(k["gecildi"], cevap), "cevapsiz_kart": k["acik"]})
    tur = {t: dict(v, yapildi_yuzde=yz(v["yarar"], v["yarar"] + v["okundu"] + v["gecildi"])) for t, v in sorted(TUR.items(), key=lambda x: -x[1]["kart"])}
    return {"haftalar": out, "kart_turu": tur, "etiket_araligi": len(aralik)}
