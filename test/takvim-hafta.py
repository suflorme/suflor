#!/usr/bin/env python3
# v0.55.0 (v0.59.0: her soruda 7 gün, ileri tarihte 30, boşluklar yalnız boş zaman sorusunda) — takvim haftası ve uygun zaman: bos_zamanlar (çalışma saatleri, dolu etkinlikler, hafta sonu), Konuş bağlamında 7 gün yalnız haftaya/boş zamana
# değinen soruda, sözlü iş talimatı kalıbı (HITAP_IS_RX: e-posta taslağı, toplantı koy), /takvim?gun=7 ve toplanti-claude.py takvim --gun 7.
# Kota yok, Whisper yok (~5 sn). Takvim/uygun zaman/iş talimatı kalıbı değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/takvim-hafta.py
import datetime as dt, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8789
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
# --- işlevler doğrudan (exec, sahte takvim) -----------------------------------------------------------------------------------------
simdi = dt.datetime(2026, 10, 16, 10, 7).astimezone()  # Cuma 10:07
def olay(i, gun, b, s, **k):
    g = simdi.replace(hour=0, minute=0) + dt.timedelta(days=gun)
    return dict({"id": f"e{i}", "baslik": f"Toplantı {i}", "baslangic": (g + dt.timedelta(hours=b)).isoformat(), "bitis": (g + dt.timedelta(hours=s)).isoformat(),
                 "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayla K"], "kisi_sayisi": 2}, **k)
TAK = {e["id"]: e for e in [olay(1, 0, 11, 12), olay(2, 3, 9, 10.5), olay(3, 3, 13, 18), olay(4, 4, 0, 24, tum_gun=True), olay(5, 5, 9, 18, reddettin=True),
                            olay(6, 6, 10, 11, takvim="Paylaşılan", hesap="Başkası")]}
ad = {"re": re, "datetime": dt, "AYAR": {"takvim_haric": ["Paylaşılan · Başkası"]}, "TAKVIM_TAM": TAK, "ARAYUZ_DILI": "tr", "STATE": {"takvim": {"durum": "ok"}},
      "_t": lambda a, b: a, "_zaman": lambda t: dt.datetime.fromisoformat(t).astimezone()}
exec(kod[kod.index("_GUN_TR = "):kod.index("# Kişilik (v0.53.0")], ad)
exec(kod[kod.index("# --- Takvim haftası ve uygun zaman"):kod.index("def _konus_kur(")], ad)
bz = {str(d): [f"{b:%H:%M}–{e:%H:%M}" for b, e in ar] for d, ar in ad["bos_zamanlar"](simdi)}
ok(f"bugün: şimdiden (çeyreğe yuvarlı) sonra, 11–12 dolu → 10:15–11:00, 12:00–18:00 ({bz.get('2026-10-16')})", bz.get("2026-10-16") == ["10:15–11:00", "12:00–18:00"])
ok("hafta sonu (Cumartesi, Pazar) yok", "2026-10-17" not in bz and "2026-10-18" not in bz)
ok(f"Pazartesi 9–10:30 ve 13–18 dolu → 10:30–13:00 ({bz.get('2026-10-19')})", bz.get("2026-10-19") == ["10:30–13:00"])
ok("tüm gün etkinlik ve reddedilen davet dolu sayılmaz; izlenmeyen takvim hariç", all(bz.get(f"2026-10-2{i}") == ["09:00–18:00"] for i in (0, 1, 2)))
ad["AYAR"]["calisma_saatleri"] = {"gunler": [0, 1, 2, 3, 4, 5], "bas": "10:00", "bit": "16:00"}
bz2 = {str(d): [f"{b:%H:%M}–{e:%H:%M}" for b, e in ar] for d, ar in ad["bos_zamanlar"](simdi)}
ok("ayar calisma_saatleri (Cumartesi dahil, 10–16)", bz2.get("2026-10-17") == ["10:00–16:00"] and bz2.get("2026-10-20") == ["10:00–16:00"] and "2026-10-18" not in bz2)
ad["AYAR"].pop("calisma_saatleri")
b_dar = ad["konus_baglam"](simdi, "", "Bugün kaçta toplantım var?"); b_gen = ad["konus_baglam"](simdi, "", "Gelecek hafta perşembe boş saatim var mı?")
ok("her soruda 7 gün (v0.59.0), boş zaman yalnız boş/uygun zaman sorusunda", "(önümüzdeki 7 gün)" in b_dar and "Boş zamanlar" not in b_dar and "Toplantı 2" in b_dar)
ok("boş zamana değinen soruda 7 gün + boş zamanlar (gün adıyla)", "(önümüzdeki 7 gün)" in b_gen and "Boş zamanlar" in b_gen and "Pazartesi 19 Ekim 13:00–18:00 · Toplantı 3" in b_gen
   and "- Salı 20 Ekim: 09:00–18:00" in b_gen and "Toplantı 6" not in b_gen)
TAK["e7"] = olay(7, 20, 14, 15); TAK["e7"]["baslik"] = "Uzak gözden geçirme"
b_7, b_30 = ad["konus_baglam"](simdi, "", "Ne var önümüzde?"), ad["konus_baglam"](simdi, "", "Kasım başında ne var?")
ok("20 gün sonraki etkinlik 7 günlük bağlamda yok, ileri tarih sorusunda 30 günde var", "Uzak gözden geçirme" not in b_7 and "(önümüzdeki 30 gün)" in b_30 and "Uzak gözden geçirme" in b_30)
ok("uzak tarih kalıbı: ay adı, gelecek ay, iki hafta sonra tutar; genel ve bu hafta sorusu tutmaz", all(ad["TAKVIM_UZAK_RX"].search(x) for x in ("21 Ekim'de ne var?", "Ay sonunda toplantı var mı?", "Gelecek ay ne var?", "İki hafta sonra ne var?", "Kasım'da müsait miyim?", "What's on next month?"))
   and not any(ad["TAKVIM_UZAK_RX"].search(x) for x in ("Bütçe ne kadar?", "Sen kimsin?", "Yarın ne var?", "Gelecek hafta ne var?", "Bu hafta neler var?", "Ayla ne dedi?")))
ok("boş zaman kalıbı: müsait, uygun zaman tutar; takvim sorusu tutmaz", all(ad["TAKVIM_BOS_RX"].search(x) for x in ("Salı müsait miyim?", "Uygun bir zaman öner", "When am I available?"))
   and not any(ad["TAKVIM_BOS_RX"].search(x) for x in ("Salı ne var?", "Gelecek hafta ne var?")))
ad3 = {"re": re}; exec(kod[kod.index("HITAP_IS_RX = "):kod.index("def konus_hitap(")].split("# v0.55.0 (S70): toplantıda Konuş")[0], ad3)
ISR = ad3["HITAP_IS_RX"]
evet = ["Ayla'ya bütçe için bir e-posta taslağı hazırla.", "Ali'ye kısa bir mail yaz.", "Bir taslak hazırla, teklifi özetlesin.", "Perşembe saat on dörde Ayla ile toplantı koy.",
        "Salı için bir görüşme ayarla.", "Bunu takvime ekle.", "Davet gönder ekibe.", "kuyruğa al teklif e-postasını", "Draft an email to Ayla."]
hayir = ["Gelecek hafta ne var?", "Perşembe boş saatim var mı?", "Ayla'nın e-posta adresi ne?", "Son toplantıda ne konuşuldu?", "Bütçe ne kadar?"]
ok("iş talimatı kalıbı: e-posta taslağı, toplantı koy, takvime ekle tutar", all(ISR.search(x) for x in evet))
ok("takvim sorusu ve bilgi sorusu iş talimatı sayılmaz (konuşan cevaplar)", not any(ISR.search(x) for x in hayir))
# --- uçtan uca: /takvim?gun=7 ve toplanti-claude.py takvim --gun 7 ------------------------------------------------------------------
T = tempfile.mkdtemp(prefix="takvim-hafta-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": "/Users/Shared/Suflor"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
s0 = dt.datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "u1", "baslik": "Uzak toplantı", "baslangic": (s0 + dt.timedelta(days=4)).isoformat(), "bitis": (s0 + dt.timedelta(days=4, hours=1)).isoformat(),
           "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayla K"], "kisi_sayisi": 2}]}, open(os.path.join(T, "takvim.json"), "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    get = lambda y: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{y}", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    t1, t7, t30 = get("/takvim?tam=1"), get("/takvim?tam=1&gun=7"), get("/takvim?tam=1&gun=30")
    ok("/takvim (eski): 4 gün sonraki toplantı yok, boş zaman alanı yok", not any(o["id"] == "u1" for o in t1["olaylar"]) and "bos" not in t1)
    ok("/takvim?gun=7: 4 gün sonraki toplantı tarihiyle, boş zaman listesi", any(o["id"] == "u1" and o.get("tarih") for o in t7["olaylar"]) and isinstance(t7.get("bos"), list) and t7.get("gun") == 7)
    ok("/takvim?gun=30: 30 güne kadar açılır (v0.59.0)", t30.get("gun") == 30)
    out = subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "takvim", "--gun", "7"],
                         capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay)).stdout
    ok("toplanti-claude.py takvim --gun 7: boş zamanlar + uzak toplantı tarihli", "# Boş zamanlar (7 gün" in out and "Uzak toplantı" in out and (s0 + dt.timedelta(days=4)).strftime("%Y-%m-%d") in out)
    ok("aktarıcıda hata yok", "Traceback" not in open(os.path.join(T, "relay.log")).read())
finally:
    r.terminate(); r.wait(); shutil.rmtree(T, ignore_errors=True)
print("takvim haftası:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
