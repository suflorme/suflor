#!/usr/bin/env python3
# Kararlar ve işler → eylem menüsünde «asistana sor» (10 Kasım; eski tek çağrı «Claude'a çalıştır» yerine): kaydın bağlamı Konuş'un yazılı turuna gider, cevap sohbet panelinde aynı konuşmada sürer.
#   A) yapi.marvin_kayit_blogu / dokum_bolumu (saf, hızlı): kayıt + tarihçe, kaynak saati çevresinden döküm (sınır 3500, saat yoksa kök araması), aynı toplantının ve aynı konunun açık kayıtları;
#      gizli toplantı kaydında hiçbir şey dönmez ve gizli içerik pakete girmez.
#   B) gerçek aktarıcı + sahte claude (kota yok; Brifing.app açık süreç kipi, swiftc): POST /girdi {kayit, text} → bloklar sürece gider (kişi modeli paketi dahil), devam sorusu aynı süreçte (blok yeniden
#      gitmez), gizli kayıtta ve gizli kipte çalışmaz, «Kayda not olarak ekle» (POST /kayit-not) yorumu asistan notu olarak yazar, gizli kayıt/kipte yazmaz, eski «claude» eylemi kalktı.
# yapi.py marvin_kayit_blogu/dokum_*, aktarici/eylem-menu.py marvin_kayit_baslat, bas-konus.py konus_yazili(ek=), notlar.py kayit_not_ekle, relay.py /girdi ya da /kayit-not değişince:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/marvin-kayit.py      (~40 sn; kaldı → çıkış 1)
import datetime, json, os, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD)
T = tempfile.mkdtemp(prefix="marvin-kayit-"); AY0 = os.path.join(T, "ayar0.json"); json.dump({"ad": "Ayşe Deneme"}, open(AY0, "w")); os.environ["SUFLOR_AYAR"] = AY0
import yapi
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {str(ek)[:300]}"))
    if not k: HATA.append(ad)
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def dokum(C, ad, satirlar, gizli=False):
    open(os.path.join(C, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {ad}\n\n" + BAS + "".join(f"| {s} | {k} | {m} | |\n" for s, k, m in satirlar) + ("| 10:00:05 | **GİZLİ** | açıldı | |\n" if gizli else ""))
def db(C): return sqlite3.connect(os.path.join(C, "karar-grafi.sqlite"))
def tohum(C):  # kurgu veri: bir toplantı (ilgili döküm, başka açık kayıtlar), başka bir toplantıda aynı konulu iş, gizli toplantı
    D1, D2, G = "2026-11-03-1000-Haftalik-Butce", "2026-11-02-0900-Tedarik-Gorusmesi", "2026-11-04-1500-Ozel"
    uzun = "Tedarikçi sözleşmesi için fiyat tablosunu gözden geçirdik ve " * 3
    dokum(C, D1, [("10:00:00", "Ayşe Deneme", "Günaydın, başlayalım."), ("10:02:00", "Can Örnek", "Önce geçen haftanın bütçesine bakalım."), ("10:08:40", "Can Örnek", "Fiyat tablosunu ben güncelleyeceğim, cuma gününe kadar."),
                   ("10:09:30", "Ayşe Deneme", "Tedarikçiye de haber verelim mi?"), ("10:10:30", "Zeynep Kaya", "Tedarikçi sözleşmesi Mart'ta bitiyor."), ("10:40:00", "Ayşe Deneme", "UZAKSATIR toplantıyı kapatalım."),
                   ("10:41:00", "**SİSTEM**", "SISTEMSATIRI toplantı bitti")] + [("10:%02d:%02d" % (11 + i // 60, i % 60), "Can Örnek", f"{uzun}{i}") for i in range(40)])
    dokum(C, D2, [("09:00:00", "Bora Kaya", "Tedarikçi sözleşmesi taslağı hazır.")]); dokum(C, G, [("15:00:00", "Ayşe Deneme", "özel")], gizli=True)
    yapi.graf_yaz(C, {"baslik": "Haftalık bütçe", "tarih": "2026-11-03", "maddeler": [{"baslik": "G", "ogeler": [
        {"tur": "is", "metin": "Fiyat tablosunu güncelle", "sahip": "Can Örnek", "tarih": "2026-11-10", "saat": "10:08:40"},
        {"tur": "is", "metin": "Bütçe sunumunu hazırla", "sahip": "Zeynep Kaya", "tarih": "2026-11-12", "saat": "10:12:00"},
        {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Can Örnek", "saat": "10:14:00"},
        {"tur": "is", "metin": "Eski iş kapanmış", "sahip": "Can Örnek", "tarih": "2026-11-01", "saat": "10:15:00"},
        {"tur": "karar", "metin": "Tedarikçi sözleşmesi Mart'ta yenilenecek", "kim": "Zeynep Kaya", "saat": "10:10:30", "netlik": "acik"}]}]}, D1 + ".md")
    yapi.graf_yaz(C, {"baslik": "Tedarik görüşmesi", "tarih": "2026-11-02", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "Tedarikçi sözleşmesi taslağını gönder", "sahip": "Bora Kaya", "tarih": "2026-11-08", "saat": "09:00:00"},
                                                                                                          {"tur": "is", "metin": "Fiyat tablosu için tedarikçiden teklif al", "sahip": "Bora Kaya", "tarih": "2026-11-09", "saat": "09:05:00"}]}]}, D2 + ".md")
    yapi.graf_yaz(C, {"baslik": "Özel", "tarih": "2026-11-04", "maddeler": [{"baslik": "G", "ogeler": [{"tur": "is", "metin": "GIZLIIS tedarikçi sözleşmesi maaş", "sahip": "Can Örnek", "saat": "15:00:05"}]}]}, G + ".md")
    return D1, D2, G
def kimlikler(C):
    v = yapi.kayit_listesi(C, "Ayşe Deneme", datetime.date(2026, 11, 5)); return {x["metin"]: x for x in v["kayitlar"]}, v
def idsi(C, metin): return "s" + str(db(C).execute("SELECT id FROM kayit WHERE metin = ?", (metin,)).fetchone()[0])
# ---------------------------------------------------------------- A) saf işlevler
C = os.path.join(T, "canli"); os.makedirs(C); D1, D2, G = tohum(C); K, V = kimlikler(C)
IS = K["Fiyat tablosunu güncelle"]["id"]; GIZLI = idsi(C, "GIZLIIS tedarikçi sözleşmesi maaş")
yapi.yorum_ekle(C, IS, "Önceki not: Zeynep'e sorulacak", yazan="ad:Ayşe Deneme", kaynak="eylem"); yapi.ata(C, IS, {"sahip": {"ad": "Can Örnek", "eposta": ""}}, None, "eylem")
blok, hata = yapi.marvin_kayit_blogu(C, IS, "Ayşe Deneme", datetime.date(2026, 11, 5))
ok("blok kuruldu", blok and not hata, hata)
ok("kayıt bölümü: kimlik, metin, toplantı, kaynak saat, sahip, vade", "[Kayıt]" in blok and "Fiyat tablosunu güncelle" in blok and "Haftalık bütçe" in blok and "kaynak saat 10:08:40" in blok and "Sahip: Can Örnek" in blok and "2026-11-10" in blok, blok[:600])
ok("tarihçe: önceki yorum metniyle", "Tarihçe:" in blok and "Önceki not: Zeynep'e sorulacak" in blok)
dk = blok.split("[Toplantı dökümünden ilgili bölüm")[1].split("[/Döküm]")[0] if "[Toplantı dökümünden ilgili bölüm" in blok else ""
ok("döküm: kaynak saati (10:08:40) çevresi — 10:08:40, 10:09:30, 10:10:30 var", "Fiyat tablosunu ben güncelleyeceğim" in dk and "Tedarikçiye de haber" in dk and "Mart'ta bitiyor" in dk, dk[:400])
ok("döküm: uzak satır (10:00, 10:40) ve sistem satırı yok", "Günaydın" not in dk and "UZAKSATIR" not in dk and "SISTEMSATIRI" not in dk)
ok("döküm bölümü ≤ 3500 karakter (çevrede çok satır olsa da)", len(dk) <= 3600, len(dk))
sat = yapi.dokum_satirlari(C, D1)
ok("dokum_satirlari: satırlar, sistem satırı atlanır", len(sat) >= 45 and not any("SISTEMSATIRI" in s[3] for s in sat) and sat[0][1] == "10:00:00")
dd = yapi.dokum_bolumu([(i * 3, "00:%02d:%02d" % (i * 3 // 60, i * 3 % 60), "K", "x" * 300 + str(i)) for i in range(60)], "00:01:30", "", 3500, pay=600)
ok("dokum_bolumu: sınır 3500; saate en yakın satırlar önce kalır", len(dd) <= 3500 and "00:01:30" in dd, len(dd))
ok("dokum_bolumu: saat yoksa maddeye göre kök araması (ilgili satır + önceki)", "Tedarikçiye de haber" in yapi.dokum_bolumu(sat, None, "Tedarikçi sözleşmesi") and "Günaydın" not in yapi.dokum_bolumu(sat, None, "Tedarikçi sözleşmesi", 3500))
ok("dokum_bolumu: ne saat ne eşleşme: boş", yapi.dokum_bolumu(sat, None, "xyz") == "" and yapi.dokum_bolumu([], "10:00:00", "a") == "")
ok("aynı toplantının diğer açık kayıtları: sunum, açık soru, karar; kendisi ve kapanmış iş yok", "[Aynı toplantının diğer açık kayıtları]" in blok and "Bütçe sunumunu hazırla" in blok and "KDV dahil mi?" in blok
   and blok.split("[Aynı toplantının diğer")[1].count("Fiyat tablosunu güncelle") == 0, blok)
yapi.soz_kapat(C, K["Eski iş kapanmış"]["id"], "yapildi"); blok2, _ = yapi.marvin_kayit_blogu(C, IS, "Ayşe Deneme", datetime.date(2026, 11, 5))
ok("kapanmış kayıt listede yok", "Eski iş kapanmış" not in blok2)
ok("aynı konudaki diğer açık kayıtlar: başka toplantıdan fiyat tablosu işi; ortak sözcüksüz iş ve gizli toplantının kaydı yok", "[Aynı konudaki diğer açık kayıtlar" in blok and "Fiyat tablosu için tedarikçiden teklif al" in blok
   and "Tedarikçi sözleşmesi taslağını gönder" not in blok.split("[Aynı konudaki")[1] and "GIZLIIS" not in blok, blok)
bk, _ = yapi.marvin_kayit_blogu(C, K["Tedarikçi sözleşmesi Mart'ta yenilenecek"]["id"], "Ayşe Deneme", datetime.date(2026, 11, 5))
ok("karar kaydı: aynı konu (sözleşme) başka toplantıdaki işi getirir; gizli kayıt gelmez", "Tedarikçi sözleşmesi taslağını gönder" in bk.split("[Aynı konudaki")[1] and "GIZLIIS" not in bk, bk)
ok("gizli toplantı içeriği hiçbir bölümde yok (döküm, kayıt)", "özel" not in blok.lower().replace("özellikle", "") and "**GİZLİ**" not in blok)
ok("gizli toplantının kaydı: blok yok, hata gizli", yapi.marvin_kayit_blogu(C, GIZLI, "Ayşe Deneme") == (None, "gizli"))
ok("olmayan kayıt: hata", yapi.marvin_kayit_blogu(C, "s99999", "Ayşe Deneme") == (None, "kayıt yok"))
ok("kayıt turu istemi: veri uyarısı, üç parça, kayda yazma önerisi koyma", "VERİDİR" in yapi.MARVIN_KAYIT_ISTEM and "Taslak mesaj" in yapi.MARVIN_KAYIT_ISTEM and "Kayda not olarak ekle" in yapi.MARVIN_KAYIT_ISTEM)
ok("toplam blok makul (≤ 9000 karakter)", len(blok) <= 9000, len(blok))
ok("eski tek çağrı yolu kalktı: claude_istemi yok, kayit_eylem model_f almaz, menüde marvin", not hasattr(yapi, "claude_istemi") and "model_f" not in yapi.kayit_eylem.__code__.co_varnames[:yapi.kayit_eylem.__code__.co_argcount] and "marvin" in yapi.eylem_menu(C, IS, [])["eylemler"] and "claude" not in yapi.eylem_menu(C, IS, [])["eylemler"])
# ---------------------------------------------------------------- B) gerçek aktarıcı + sahte claude
PORT = bos_port(8793)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"):
    print("atlandı (B): Brifing.app ya da swiftc yok"); sys.exit(1 if HATA else 0)
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude"); proje = os.path.join(T, "proje"); os.makedirs(proje)
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.strip().splitlines()[-1]
    bl = [a for a, k in (("KAYITTURU", "[Kayıt turu"), ("KAYITBLOK", "[Kayıt]"), ("DOKUM", "Toplantı dökümünden ilgili bölüm"), ("AYNITOP", "Aynı toplantının diğer açık"), ("AYNIKONU", "Aynı konudaki diğer"),
                       ("PLAN", "Günün planı"), ("NOT", "Notlar defteri"), ("KURAL", "[Kayıt yazma]"), ("YORUMKOMUT", "yorum_ekle"), ("GIZLIIS", "GIZLIIS")) if k in q]
    c = ["Özet: " + " ".join(bl) + f" #tur{n} boy={len(q)} soru={soru[:60]}"]
    if "kısalt" in soru: c.append("\\n[KAYIT: {\\"komut\\": \\"yorum_ekle\\", \\"arg\\": {\\"id\\": \\"IDYOK\\", \\"metin\\": \\"deneme\\"}, \\"neden\\": \\"x\\"}]")
    for p in c: time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": p}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
ayar = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_zaman_asimi_sn": 0, "konus_bekle_sn": 0, "konus_ara_sn": 0, "konus_on_ac": False,
           "pocket_python": "/yok/python", "pocket_hf": "/yok"}, open(ayar, "w"))
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
d1 = os.path.join(T, "canli1"); os.makedirs(d1); tohum(d1); K1, _ = kimlikler(d1); IS1 = K1["Fiyat tablosunu güncelle"]["id"]; GIZLI1 = idsi(d1, "GIZLIIS tedarikçi sözleşmesi maaş"); SORU1 = K1["KDV dahil mi?"]["id"]
bugun = datetime.date.today().isoformat()
json.dump({"tarih": bugun, "ozet": "Bugün bütçe haftası; tedarikçi görüşmesi öncelikli.", "odak": [], "dikkat": [], "sabit": []}, open(os.path.join(d1, "gun-plani.json"), "w"))
open(os.path.join(d1, "notlar.jsonl"), "w").write(json.dumps({"id": "n1", "at": datetime.datetime.now().isoformat(timespec="seconds"), "metin": "Tedarikçi fiyatı için Bora'yı ara"}, ensure_ascii=False) + "\n")
p = subprocess.Popen([sys.executable, "relay.py", "--dir", d1, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
                     stdout=open(os.path.join(T, "canli1.log"), "w"), stderr=subprocess.STDOUT)
for _ in range(60):
    if os.path.exists(os.path.join(d1, "kart-anahtari.txt")): break
    time.sleep(0.2)
time.sleep(1); AN = open(os.path.join(d1, "kart-anahtari.txt")).read().strip(); H = {"X-Suflor-Anahtar": AN, "Origin": f"http://127.0.0.1:{PORT}"}
def post(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=H), timeout=20).read())
def status(): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers=H), timeout=10).read())
def bekle(parca, sn=40):
    t0 = time.time()
    while time.time() - t0 < sn:
        k = status()["konus"]
        if parca in (k.get("soru") or "") and k["durum"] in ("hazir", "hata"): return k
        time.sleep(0.25)
    return status()["konus"]
def yorumlar(): return [r for r in db(d1).execute("SELECT kaynak, veri FROM olay WHERE tur = 'yorum_eklendi' ORDER BY saat")]
try:
    SORU_METNI = "«Fiyat tablosunu güncelle» kaydına bak: özet, en çok 3 yapılacak ve sahibine kısa taslak mesaj"
    g = post("/girdi", {"text": SORU_METNI, "kayit": IS1}); k = bekle("Fiyat tablosunu")
    c = k.get("cevap") or ""
    ok("panelden tura giden yol: /girdi {kayit} → tur asistan, cevap panelde yazılı", g.get("tur") == "asistan" and g.get("ok") and k["durum"] == "hazir" and "#tur1" in c, (g, c))
    ok("sürece giden bloklar: kayıt turu, kayıt, döküm, aynı toplantı, aynı konu", all(a in c for a in ("KAYITTURU", "KAYITBLOK", "DOKUM", "AYNITOP", "AYNIKONU")), c)
    ok("kişi modelinin ortak paketi de gitti (gün planı, notlar)", "PLAN" in c and "NOT" in c, c)
    ok("kayıt yazma kuralı (yorum_ekle dahil) ve gizli içerik: kural var, GIZLIIS yok", "KURAL" in c and "YORUMKOMUT" in c and "GIZLIIS" not in c, c)
    ok("görünen soru kısa kaldı (blok panoda soru olarak görünmez)", k.get("soru") == SORU_METNI, k.get("soru"))
    g2 = post("/girdi", {"text": "taslağı biraz kısalt"}); k2 = bekle("kısalt"); c2 = k2.get("cevap") or ""
    ok("devam sorusu aynı süreçte (tur2), kayıt bloğu yeniden gitmedi", "#tur2" in c2 and "KAYITTURU" not in c2 and "DOKUM" not in c2, c2)
    log = open(os.path.join(T, "canli1.log"), encoding="utf-8").read()
    ok("günlükte metin yok, yalnız boyut (kayıt metni, döküm sızmaz)", "asistana sor" in log and "Fiyat tablosunu ben güncelleyeceğim" not in log and "Önceki not" not in log)
    # kayda not olarak ekle
    n0 = len(yorumlar()); r = post("/kayit-not", {"id": IS1, "metin": "Özet: tablo güncellenecek.\n- Can'a sor\nTaslak: Merhaba Can…"})
    y = yorumlar()
    ok("Kayda not olarak ekle: yorum_eklendi yazıldı (kaynak asistan, uretici asistan), çok satırlı metin korunur", r.get("ok") and len(y) == n0 + 1 and y[-1][0] == "asistan" and json.loads(y[-1][1]).get("uretici") == "asistan" and "\n- Can'a sor" in json.loads(y[-1][1])["metin"], (r, y[-1:]))
    ok("tarihçede «asistan notu ekledi»", any("asistan notu ekledi" in o["ozet"] for o in yapi.tarihce(d1, yapi.ortak_kayit(d1, IS1)["kayit_id"])))
    r = post("/kayit-not", {"id": IS1, "metin": "x" * 2500}); ok("2000 karakteri aşan cevap kırpılarak yazılır", r.get("ok") and len(json.loads(yorumlar()[-1][1])["metin"]) <= 2000, r)
    ok("not: boş metin ve olmayan kayıt reddedilir", not post("/kayit-not", {"id": IS1, "metin": " "}).get("ok") and not post("/kayit-not", {"id": "s99999", "metin": "abc def"}).get("ok"))
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/kayit-not", data=json.dumps({"id": IS1, "metin": "abc def"}).encode(), headers={"Origin": f"http://127.0.0.1:{PORT}"}), timeout=10); anahtarsiz = False
    except urllib.error.HTTPError as e: anahtarsiz = e.code in (401, 403)
    ok("/kayit-not anahtarsız reddedilir (401/403)", anahtarsiz)
    # gizli kayıt
    n1 = len(yorumlar()); s1 = len(open(os.path.join(T, "canli1.log"), encoding="utf-8").read())
    g = post("/girdi", {"text": "gizli kayda bak", "kayit": GIZLI1})
    ok("gizli toplantı kaydı: tur başlamaz (err gizli), Claude'a bir şey gitmez", not g.get("ok") and g.get("err") == "gizli" and g.get("tur") is None, g)
    ok("gizli toplantı kaydına not yazılmaz", not post("/kayit-not", {"id": GIZLI1, "metin": "gizli not"}).get("ok") and len(yorumlar()) == n1)
    ok("olmayan kayıt ve kayıtsız girdi", post("/girdi", {"text": "x", "kayit": "s99999"}).get("err") == "kayıt yok")
    ok("eski «claude» eylemi kalktı (POST /kayit-eylem bilinmeyen eylem)", post("/kayit-eylem", {"id": IS1, "eylem": "claude"}).get("ok") is False)
    m = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/kayit-menu?id={IS1}", headers=H), timeout=10).read())
    ok("menü: marvin var, claude yok, gizli kayıt için menü yok", "marvin" in m["eylemler"] and "claude" not in m["eylemler"])
    # gizli kip: kayıt turu çalışmaz
    gk = post("/komut", {"tur": "gizli", "durum": "ac"}); time.sleep(0.3)
    g = post("/girdi", {"text": "kayda bak", "kayit": IS1}); n2 = len(yorumlar())
    ok("gizli kip açıkken: kayıt turu çalışmaz (kapıda durur)", not g.get("ok") and (g.get("gizli") or g.get("err") == "gizli") and g.get("tur") is None, (gk, g))
    ok("gizli kip açıkken: Kayda not olarak ekle yazmaz", not post("/kayit-not", {"id": IS1, "metin": "gizli kipte not"}).get("ok") and len(yorumlar()) == n2)
    post("/komut", {"tur": "gizli", "durum": "kapat"})
finally:
    p.terminate()
    try: p.wait(timeout=10)
    except subprocess.TimeoutExpired: p.kill()
print("\nhepsi geçti" if not HATA else f"\nKALDI: {len(HATA)}"); sys.exit(1 if HATA else 0)
