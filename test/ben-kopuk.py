#!/usr/bin/env python3
# v0.255.1 (beta #89/#90, 25 Kasım 93 dk Meet): "ben" kanalı kopukken görünür uyarı ve eklentinin kendini onarması.
# 1) aktarici/saglik.py ben_kopuk_view: toplantı tarayıcıda sürerken mikrofon kanalı BEN_KOPUK_SN bağlı değilse uyarı (Safari'de toplantı → "tarayici";
#    eklenti sekmesi var ama mikrofon bilgisi yok → "sekme"), düzelince kalkar, günlüğe birer kez; sessiz/kapalı/masaüstü/altyazı/whisper yok → uyarı yok.
# 2) content.js çift yükleme koruması: canlı örnek varken ikinci örnek kurulmaz; ölü (yetim) örnek varken kurulur; eski sürümün bayrağı (true) yalnız
#    arka planın yeniden yükleme işaretiyle aşılır. 3) background.js/manifest/pano kaynakta.
# aktarici/saglik.py (ben_kopuk), content.js başı, background.js nabizYokla/betikYenidenYukle, pano durum() değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 -B test/ben-kopuk.py   (gerçek tarayıcıda: ../_yedek/test-araclari/test54.py)
import json, os, subprocess, sys, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from pano_kaynak import pano_kaynak
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad, flush=True)
    if not k: HATA.append(ad)

# --- 1) saglik.py ben_kopuk_view ---
s = open(os.path.join(KOD, "aktarici", "saglik.py"), encoding="utf-8").read()
src = s[s.index("BEN_KOPUK_SN ="):s.index("def _veri_yok_dongu")]
D = {"top": True, "mas": False, "wh": "hazir", "alt": False, "kod": "yok", "ek": None, "app": "Safari", "ys": "dinliyor", "now": 1000.0}
CIKTI = []
class Saat:
    @staticmethod
    def time(): return D["now"]
ns = {"os": type("o", (), {"environ": {}})(), "time": Saat, "print": lambda *a: CIKTI.append(" ".join(map(str, a))),
      "STATE": {"whisper": {}, "yerel_ses": {}},
      "toplanti_suruyor": lambda: D["top"], "masaustu_toplantida": lambda: D["mas"], "kanal_akiyor": lambda k, sn=None: D["alt"] if k == "altyazi" else False,
      "ben_kod": lambda: D["kod"], "eklenti_sayfa": lambda: D["ek"], "yerel_ses_durum": lambda: D["ys"]}
exec(src, ns)
def bak(**k):
    D.update(k); ns["STATE"]["whisper"]["durum"] = D["wh"]; ns["STATE"]["yerel_ses"]["uygulama"] = D["app"]; return ns["ben_kopuk_view"]()
ok("eşik 120 sn (2 dk; konuşmama değil kanal kopukluğu)", ns["BEN_KOPUK_SN"] == 120)
ok("Safari'de toplantı: eşikten önce uyarı yok", bak(now=1000.0) is None and bak(now=1100.0) is None)
v = bak(now=1121.0)
ok(f"Safari'de toplantı: 120 sn sonra uyarı (tarayici, Safari): {v}", v == {"sn": 121, "neden": "tarayici", "uygulama": "Safari"})
bak(now=1130.0); ok("günlüğe bir kez 'MİKROFON KANALI: kopuk'", sum("MİKROFON KANALI: kopuk" in c for c in CIKTI) == 1)
ok("mikrofon akınca uyarı kalktı + 'düzeldi' günlüğü", bak(kod="akiyor", now=1140.0) is None and any("MİKROFON KANALI: düzeldi" in c for c in CIKTI))
bak(kod="yok", now=1200.0); v = bak(now=1321.0, ek={"sayfa": True}, app="Chrome")
ok(f"eklenti sekmesi var ama mikrofon bilgisi yok → sekme: {v}", v and v["neden"] == "sekme")
v = bak(now=1330.0, kod="hata"); ok(f"mikrofon açılamadı → hata: {v}", v and v["neden"] == "hata")
v = bak(now=1331.0, kod="sorun"); ok(f"açık ama ses gelmiyor → sorun: {v}", v and v["neden"] == "sorun")
for ad, k in (("sessizde", {"kod": "sessiz"}), ("Whisper/mikrofon kapalı", {"kod": "kapali"}), ("masaüstü toplantı", {"kod": "yok", "mas": True}),
              ("altyazı akıyor", {"mas": False, "alt": True}), ("Whisper yok", {"alt": False, "wh": "yok"}), ("toplantı yok", {"wh": "hazir", "top": False}),
              ("tarayıcı izi yok (yüz yüze / masaüstü uygulama)", {"top": True, "ek": None, "app": "zoom.us"})):
    bak(**k); ok(f"{ad}: uyarı yok", bak(now=D["now"] + 500) is None)

# --- 2) content.js çift yükleme koruması (node, sahte window/chrome) ---
c = open(os.path.join(KOD, "content.js"), encoding="utf-8").read()
on = c[:c.index("  const P = globalThis.SuflorPlatform")] + "  window.kurulan = (window.kurulan || 0) + 1;\n})();\n"
js = r"""
const vm = require("vm"); const kaynak = process.argv[1];
const sil = []; const doc = { getElementById: id => ({ remove: () => sil.push(id) }) };
function ornek(win, canli) { const ctx = { window: win, document: doc, chrome: { runtime: { id: canli ? "x" : undefined } } }; vm.runInNewContext(kaynak, ctx); return ctx; }
const w = {}; const a = ornek(w, true); ornek(w, true); const r1 = w.kurulan;            // canlı örnek varken ikinci yükleme
a.chrome.runtime.id = undefined; ornek(w, true); const r2 = w.kurulan;                     // önceki yetim → yeni örnek kurulur
const e = { __ohCanliLoaded: true }; ornek(e, true); const r3 = e.kurulan || 0;          // eski sürüm bayrağı, işaret yok → kurulmaz
const f = { __ohCanliLoaded: true, __suflorYenidenYukle: 1 }; ornek(f, true); const r4 = f.kurulan || 0;  // işaretle → kurulur, işaret silinir
console.log(JSON.stringify({ r1, r2, r3, r4, isaret: "__suflorYenidenYukle" in f, sil }));
"""
o = json.loads(subprocess.run(["node", "-e", js, on], capture_output=True, text=True, check=True).stdout)
ok(f"canlı örnek varken ikinci yükleme kurulmadı: {o['r1']}", o["r1"] == 1)
ok(f"yetim örnek varken yeni örnek kuruldu, eski şerit kaldırıldı: {o['r2']} {o['sil']}", o["r2"] == 2 and "suflor-serit" in o["sil"])
ok("eski sürüm bayrağı (true) işaretsiz: kurulmadı", o["r3"] == 0)
ok("eski sürüm bayrağı + arka plan işareti: kuruldu, işaret silindi", o["r4"] == 1 and not o["isaret"])
ok("yetim örnek susar: zamanlayıcı, aktarıcı isteği ve mikrofon dinleyicisi oldu() bakar",
   "const setInterval = (f, ms, ...a) => window.setInterval(() => { if (!oldu())" in c and 'const rf = (yol, o) => oldu() ? Promise.reject' in c and "window.top !== window || oldu()) return;" in c)

# --- 3) background.js, manifest, pano ---
b = open(os.path.join(KOD, "background.js"), encoding="utf-8").read(); m = json.load(open(os.path.join(KOD, "manifest.json"), encoding="utf-8"))
ok("manifest: scripting izni", "scripting" in m["permissions"])
ok("nabız yüklenen sekmeyi atlar (25 Kasım 23:40 yanlış alarmı)", 't.status !== "complete"' in b)
ok("art arda iki yanıtsız yoklamada betik yeniden yüklenir, sekme yenilenmez", "nabizHata.get(t.id) >= 2" in b and "chrome.scripting.executeScript" in b and "chrome.tabs.reload" not in b)
p = pano_kaynak()
ok("pano durum(): ben_kopuk kırmızı uyarı (pano + mini pano aynı durum())", "s.ben_kopuk" in p and "Mikrofonun yazılmıyor" in p and 'so.push(["er"' in p)
print("\nSONUÇ: " + ("hepsi geçti" if not HATA else f"{len(HATA)} başarısız: {HATA}")); sys.exit(1 if HATA else 0)
