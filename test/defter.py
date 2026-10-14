#!/usr/bin/env python3
# S48 toplantı defteri (aktarici/defter.py) — yapay dosyalarla: bölünmüş dosyaların birleşmesi, art arda iki toplantının ayrı kalması, saat sınırı,
# toplantı sonu konuşmacı düzeltmesi, sıra (gündem → döküm → konuşanlar → özet), uzun toplantıda kısa defter. Aktarıcı çalıştırılmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/defter.py
import collections, datetime, json, os, re, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
BASE = tempfile.mkdtemp(prefix="defter-"); os.makedirs(os.path.join(BASE, "gundemler")); os.makedirs(os.path.join(BASE, "ozetler"))
STATE = {"file": None, "file_last": {}}; AYAR = {}; ARAYUZ_DILI = "tr"; BRIFING = {}; SON = []
_t = lambda a, b: a; toplanti_var = lambda: False
_AY_TR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
simdi = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)  # sabit öğlen: dosya adları gece yarısında da aynı güne sığar
class _Saat:  # defter.py'nin gördüğü saat (dosya saatleri de buna göre)
    time = staticmethod(lambda: simdi.timestamp())
time_gercek = time; time = _Saat
exec(compile(open(os.path.join(KOD, "aktarici", "defter.py"), encoding="utf-8").read(), "defter.py", "exec"))
def dosya(bas_dk_once, son_dk_once, ad, satirlar, baslik=None):  # bas_dk_once: kaç dk önce başladı (dosya adı), son_dk_once: son yazma
    b = simdi - datetime.timedelta(minutes=bas_dk_once); f = f"{b:%Y-%m-%d-%H%M}-{ad}.md"
    open(os.path.join(BASE, f), "w").write(f"# Canlı transkript — {baslik or ad}\n\n| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n" + "".join(f"| {s} | {k} | {m} |  |\n" for s, k, m in satirlar))
    t = time.time() - son_dk_once * 60; os.utime(os.path.join(BASE, f), (t, t)); return f
def yenile(): _DF_ON.update(t=0)
# bölünmüş toplantı: A 40 dk önce başladı, 2 dk önce bitti; B (başlık değişimi) 38 dk önce başladı, 20 dk önce bitti → üst üste 18 dk
a = dosya(40, 2, "Proje-gorusmesi", [("10:00:01", "Karşı taraf 1", "Bütçe kırk bin."), ("10:00:05", "Deniz T", "Tamam.")], "Proje görüşmesi")
b = dosya(38, 20, "Baska-baslik", [("10:02:00", "Karşı taraf 1", "Teslim cuma.")])
# art arda toplantı: C, A başlamadan 1 dk önce bitti (60 dk önce başladı) → ayrı kalmalı
c = dosya(60, 40.5, "Onceki-toplanti", [("09:20:00", "Can B", "Eski konu.")])
open(os.path.join(BASE, a[:-3] + ".jsonl"), "w").write(json.dumps({"id": "w-1", "time": "10:00:01", "speaker": "Karşı taraf 1", "text": "Bütçe kırk bin."}) + "\n")
json.dump({"ad": {"w-1": "Ayla K"}}, open(os.path.join(BASE, a[:-3] + ".konusmaci.json"), "w"))
json.dump({"title": "Proje görüşmesi", "baslangic": "10:00", "bitis": "10:45", "items": ["1 Bütçe", "2 Teslim"]}, open(os.path.join(BASE, "gundemler", a[:-3] + ".json"), "w"))
oz = os.path.join(BASE, "ozetler", "proje-ozet.md"); open(oz, "w").write("# Özet\nKarar: bütçe kırk bin.\n")
SON.append({"dosya": a, "kopya": oz, "ozet": "/yok/proje-ozet.md", "t": time.time()})
STATE["file"] = a; d = defter_toplanti()
ok("bölünmüş dosyalar birlikte (≥ 3 dk üst üste), art arda önceki toplantı ayrı", d and d["dosyalar"] == [a, b] and c not in d["dosyalar"])
ok("ad dosyanın başlığından", d["ad"] == "Proje görüşmesi")
m, kisa = defter_metni(d)
ok("konuşmacı düzeltmesi uygulandı (Karşı taraf 1 → Ayla K, yalnız eşlenen satır)", "| 10:00:01 | Ayla K | Bütçe kırk bin." in m and "| 10:02:00 | Karşı taraf 1 | Teslim cuma." in m)
ok("sıra: başlık → gündem → döküm → konuşanlar → özet", m.index("# Toplantı defteri") < m.index("## Gündem") < m.index("## Döküm") < m.index("## Konuşanlar") < m.index("## Toplantı sonu özeti")
   and m.rstrip().endswith("Karar: bütçe kırk bin."))
ok("konuşan sayımı", "Ayla K (1)" in m and "Deniz T (1)" in m and not kisa)
ok("panoda görünüm (ad, saat)", defter_view() == {"ad": "Proje görüşmesi", "saat": datetime.datetime.fromtimestamp(d["son"]).strftime("%H:%M")})
# S48 defter turu (v0.35.0): yapı dosyası (toplantı oturumu; kaynak saatleri bitir'de doğrulanır) → "Toplantı sonu" bölümü, özetten önce
yp = os.path.join(BASE, "ozetler", "proje-ozet.yapi.json")
json.dump({"baslik": "Proje", "maddeler": [{"baslik": "Bütçe", "durum": "konuşuldu", "ogeler": [
    {"tur": "karar", "metin": "Bütçe kırk bin", "kim": "Ayla K", "saat": "10:00:01", "netlik": "ortuk"},
    {"tur": "is", "metin": "Teklifi gönder", "sahip": "Deniz T", "tarih": "2026-10-20", "saat": "10:00:05"}, {"tur": "bilinmez", "metin": "atla"}]}],
    "duzeltmeler": [{"saat": "10:02:00", "yanlis": "cuma", "dogru": "çarşamba"}, {"yanlis": "eksik"}], "dokum_notu": "10:01 ses kesik"}, open(yp, "w"))
SON[-1]["yapi"] = yp; m2, _ = defter_metni(d)
ok("yapı dosyası defterde: karar/iş saatli, düzeltme, döküm notu; bilinmeyen tür ve eksik düzeltme yok",
   "- Karar [10:00:01] Ayla K — Bütçe kırk bin (netlik: ortuk)" in m2 and "- İş [10:00:05] Deniz T — Teklifi gönder (tarih 2026-10-20)" in m2
   and '"cuma" → "çarşamba"' in m2 and "Döküm notu: 10:01 ses kesik" in m2 and "atla" not in m2 and "eksik" not in m2)
ok("sıra: konuşanlar → toplantı sonu bölümü → özet", m2.index("## Konuşanlar") < m2.index("## Toplantı sonu: kararlar") < m2.index("## Toplantı sonu özeti"))
SON[-1].pop("yapi")
sys.path.insert(0, KOD); import yapi as Y
v = Y.oku(yp)
sr = Y.kaynak_dogrula(v, ["10:00:01", "10:02:00"])
ok("kaynak doğrulama: ± 90 sn içinde satır varsa geçer, eksik düzeltme bildirilir", [n for _, n in sr] == ["düzeltmede yanlis/dogru eksik"])
v["maddeler"][0]["ogeler"][0]["saat"] = "10:30:00"; v["maddeler"][0]["ogeler"][1].pop("saat")
ok("kaynak doğrulama: dökümde olmayan saat ve saatsiz iş", [n for _, n in Y.kaynak_dogrula(v, ["10:00:01"])][:2] == ["10:30:00 dökümde yok (± 90 sn)", "kaynak saati yok"])
# saat sınırı
AYAR["konus_defter_saat"] = 0; yenile(); ok("ayar 0 → defter yok", defter_toplanti() is None)
AYAR["konus_defter_saat"] = 0.02; yenile(); ok("son yazma sınırdan eski → defter yok (2 dk > 1,2 dk)", defter_toplanti() is None)
AYAR.pop("konus_defter_saat"); yenile(); ok("varsayılan 3 saat içinde → var", defter_toplanti() is not None)
toplanti_var = lambda: True; ok("toplantı sürerken panoda satır yok", defter_view() is None); toplanti_var = lambda: False
# önbellek: toplantı değişince hemen
STATE["file"] = c; ok("toplantı değişince önbellek beklemez", (defter_toplanti() or {}).get("dosyalar") == [c])
# uzun toplantı → kısa defter: işaretli satırlar + son 30 dk + tam dosya yolu
uzun = [(f"{(simdi - datetime.timedelta(minutes=170) + datetime.timedelta(seconds=i * 4)):%H:%M:%S}", "Karşı taraf 1", "uzun bir konuşma satırı " * 6) for i in range(2500)]
uzun.insert(10, (uzun[10][0], "**CLAUDE · CEVAP**", "Önemli kart satırı"))
e = dosya(170, 0.5, "Uzun-toplanti", uzun); STATE["file"] = e; SON.clear(); yenile()
m, kisa = defter_metni()
ok("uzun toplantı → kısa defter (≤ 300 bin karakter, kart satırı ve dosya yolu var, eski satırlar yok)",
   kisa and len(m) <= DEFTER_EN_COK and "Önemli kart satırı" in m and os.path.join(BASE, e) in m and uzun[50][0] not in m and uzun[-1][0] in m)
print("defter:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
