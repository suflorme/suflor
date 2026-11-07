#!/usr/bin/env python3
# Toplantı dışı derin web araştırması (S243, v0.204.0): aktarici/web-arastirma.py — tetik cümleleri, istemin gizlilik sınırı (arama motoruna yalnız ad ve konu; döküm, iç sayı, e-posta/telefon,
# geçmiş toplantı başlığı gitmez), çıktı ayrıştırma ve bağımsız kaynak sayımı, kapalı/gizli/toplantı/sağlayıcı durumları, bekleme cümlesi, kayıt ve maliyet satırı; sonra yalıtılmış
# aktarıcıda pano kutusundan uçtan uca (sahte claude, sahte arama; gerçek ağa çıkılmaz). Brifing.app ya da Whisper gerekmez.
# aktarici/web-arastirma.py, beyin.py arastirma_args, bas-konus.py'deki kanca ya da relay.py /arastirma değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/web-arastirma.py      (kaldı → çıkış 1)
import json, os, re, shutil, subprocess, sys, tempfile, threading, time, datetime, urllib.request, urllib.error, importlib.util
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="webar-"); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
# --- sahte claude: argümanı ve stdin'i kaydeder, konuya göre stream-json üretir ---------------------------------------------------------------------------------------------
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude"); KAYIT = os.path.join(T, "cagrilar")
os.makedirs(KAYIT)
open(sahte, "w").write('''#!/usr/bin/env python3
import json, os, sys, time, glob
girdi = sys.stdin.read(); n = len(glob.glob(%r + "/*.json")) + 1
json.dump({"args": sys.argv[1:], "stdin": girdi}, open(%r + "/%%03d.json" %% n, "w"))
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
konu = girdi.split("KONU:")[1].splitlines()[0].strip() if "KONU:" in girdi else ""
if "Yavas" in konu: time.sleep(1.2)
if "Bozuk" in konu: pr({"type": "result", "is_error": True, "result": "API Error", "total_cost_usd": 0}); sys.exit(0)
for q in ("%%s resmi site" %% konu, "%%s son haber" %% konu, "%%s ticaret sicili" %% konu, "%%s controversy" %% konu):
    pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "WebSearch", "input": {"query": q}}]}})
for u in ("https://orbitek.example/hakkimizda", "https://ajans.example/haber/1", "https://sicil.example.gov/kayit"):
    pr({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "WebFetch", "input": {"url": u}}]}})
if "Tekkaynak" in konu:
    cikti = "[SESLİ]\\nYalnız tek kaynakta geçiyor.\\n[METİN]\\nBulgu ([a](https://tek.example/x), 02.11.2026).\\n## Çelişkiler\\nyok\\n## Doğrulanamadı\\nHer şey.\\n[KAYNAKLAR]\\nhttps://tek.example/x | Tek | 02.11.2026 | ikincil\\n"
else:
    cikti = ("[SESLİ]\\nOrbitek, yazılım şirketi; üç bağımsız kaynak aynı şeyi söylüyor, çelişki yok.\\n[METİN]\\nOrbitek 2014'te kuruldu ([Şirket sitesi](https://orbitek.example/hakkimizda), 01.10.2026).\\n"
             "## Çelişkiler\\nyok\\n## Doğrulanamadı\\nÇalışan sayısı.\\n[KAYNAKLAR]\\nhttps://orbitek.example/hakkimizda | Şirket sitesi | 01.10.2026 | birincil\\n"
             "https://ajans.example/haber/1 | Ajans | 28.10.2026 | ikincil\\nhttps://sicil.example.gov/kayit | Sicil | tarih yok | birincil\\nhttps://forum.example/k | Forum | 2025 | ikincil\\n")
pr({"type": "result", "is_error": False, "result": cikti, "total_cost_usd": 0.0432, "num_turns": 9, "duration_api_ms": 4200})
''' % (KAYIT, KAYIT)); os.chmod(sahte, 0o755)
def cagrilar(): return [json.load(open(os.path.join(KAYIT, f))) for f in sorted(os.listdir(KAYIT))]
# --- 1) birim: modül kaynağı sahte ad alanında ----------------------------------------------------------------------------------------------------------------------------
sp = importlib.util.spec_from_file_location("suflor_beyin", os.path.join(KOD, "aktarici", "beyin.py")); BEYIN = importlib.util.module_from_spec(sp); sp.loader.exec_module(BEYIN)
KANARYA = ["KANARYA-DOKUM-7731", "KANARYA-SAYI-4821", "kanarya" + "@" + "ic.example", "+90 555 000 11 22", "KANARYA-TOPLANTI-BASLIK"]
AYAR = {"claude": sahte}; BASE = os.path.join(T, "canli"); os.makedirs(BASE); LOCK = threading.Lock(); GIZLI = {"acik": False}; TOP = {"var": False}; SES = []
KONUS = {}; _KS = {"tur": None}; _t = lambda tr, en: tr
def write(l):
    for y, m in l: open(y, "a", encoding="utf-8").write(m)
def kisi_bul(ad): return {"durum": "ok", "kisiler": [{"ad": "Ayşe Örnek", "kurum": "Orbitek", "eposta": [KANARYA[2]], "telefon": [KANARYA[3]], "adres": ["Sokak 1"]}]} if ad == "Ayşe Örnek" else {"durum": "ok", "kisiler": []}
def arsiv_ara(q): return {"tam": True, "sonuclar": [{"id": "g1", "baslik": KANARYA[4], "at": "2026-10-30T10:00:00"}]}
def _konus_kur(**k): KONUS.update(k)
ns = dict(os=os, json=json, time=time, datetime=datetime, threading=threading, subprocess=subprocess, BEYIN=BEYIN, AYAR=AYAR, BASE=BASE, LOCK=LOCK, write=write, claude_yolu=lambda: sahte,
          gizli_acik=lambda: GIZLI["acik"], toplanti_var=lambda: TOP["var"], seslendir=lambda m, kuyruk=False, **k: SES.append(m), _konus_kur=_konus_kur, _KS=_KS, KONUS=KONUS, _t=_t,
          kisi_bul=kisi_bul, arsiv_ara=arsiv_ara, re=re)
exec(open(os.path.join(KOD, "aktarici", "web-arastirma.py"), encoding="utf-8").read(), ns)
tetik = ns["ar_tetik"]
# tetik: olumlu
for m, b in (("Orbitek Yazılım'ı araştır", "Orbitek Yazılım"), ("Orbitek Yazılım'ı araştırır mısın", "Orbitek Yazılım"), ("Ayşe Örnek hakkında araştırma yap", "Ayşe Örnek"),
             ("araştır: Orbitek Yazılım son yatırım turu", "Orbitek Yazılım son yatırım turu"), ("Orbitek Yazılım hakkında ne biliniyor?", "Orbitek Yazılım"), ("lütfen Orbitek Yazılım'ı derinlemesine araştır", "Orbitek Yazılım"),
             ("dünkü olay ne", "dünkü olay"), ("Research Orbitek Software", "Orbitek Software"), ("Ayşe Örnek ile ilgili internette araştırma yap.", "Ayşe Örnek")):
    ok(f"tetik: {m!r} → {b!r}", tetik(m) == b or (print("   alındı:", repr(tetik(m))) and False))
for m in ("Orbitek şirketi hakkında ne biliniyor?", ):
    ok(f"tetik (kısa firma sorusu): {m!r}", bool(tetik(m)))
ok("tetik: belirsiz konu '' (sorulur)", tetik("şu firmayı araştır") == "" and tetik("şu firma hakkında ne biliniyor") == "")
# tetik: olumsuz (yerel arama, erteleme, iş devri, sıradan soru)
for m in ("Dökümde Orbitek'i araştır", "projede Orbitek geçen dosyaları araştır", "yarın Orbitek'i araştır", "Ali'ye Orbitek'i araştırma işi ata", "Orbitek'i araştırmayı hatırlat", "toplantı kaçta", "Orbitek bugün kaçta toplantı",
          "Mailde Orbitek'i araştır", "bu işi araştırma listesine ekle", "araştır", "Son toplantıda sahipsiz kalan işler neler"):
    ok(f"tetik yok: {m!r}", tetik(m) is None)
# istem sınırı
ist = ns["ar_istem"]("Orbitek", "Orbitek Holding")
ok("istemde konu, kurum ipucu, tarih, ≥3 bağımsız kaynak ve 'doğrulanamadı' kuralı var", "KONU: Orbitek" in ist and "Orbitek Holding" in ist and datetime.date.today().strftime("%d.%m.%Y") in ist and "3 BAĞIMSIZ kaynak" in ist and "doğrulanamadı" in ist)
ok("istemde yerel bilgi yok (kanarya, e-posta, telefon, toplantı başlığı)", not any(k.lower() in ist.lower() for k in KANARYA))
y = ns["ar_yerel"]("Ayşe Örnek")
ok("yerel bilgi: tek eşleşmede kurum ayırt edici, satırlarda Kişiler ve geçmiş toplantı (Claude'a gitmeyecek)", y[0] == "Orbitek" and any("Kişiler: Ayşe Örnek (Orbitek)" in s for s in y[1]) and any(KANARYA[4] in s for s in y[1]))
ok("yerel satırlara e-posta/telefon girmez", not any(KANARYA[2] in s or KANARYA[3] in s for s in y[1]))
ok("şirket adı kişi sayılmaz (Kişiler'e gitmez)", ns["ar_yerel"]("Orbitek")[0] == "")
# ayrıştırma
cikti = "[SESLİ]\nKısa özet.\n[METİN]\nMetin ([a](https://a.example.com/x), 01.10.2026).\n[KAYNAKLAR]\nhttps://a.example.com/x | A | 01.10.2026 | birincil\nhttps://www.b.example.org/y | B | tarih yok | ikincil\nhttps://a.example.com/x | tekrar | - | ikincil\nbağlantı değil\n"
a = ns["ar_ayristir"](cikti)
ok("çıktı ayrıştırma: sesli, metin, yinelenmeyen kaynak", a["sesli"] == "Kısa özet." and a["metin"].startswith("Metin") and [k["url"] for k in a["kaynaklar"]] == ["https://a.example.com/x", "https://www.b.example.org/y"] and a["kaynaklar"][0]["tur"] == "birincil")
ok("başlıksız çıktı tümüyle metin olur", ns["ar_ayristir"]("düz yazı")["metin"] == "düz yazı")
ok("alan adı: www atılır, ortak sonek", ns["_ar_alan_adi"]("https://www.b.example.org/y") == "example.org" and ns["_ar_alan_adi"]("https://x.bbc.co.uk/a") == "bbc.co.uk")
# açık/kapalı
ok("varsayılan açık", ns["ar_acik"]()[0] is True)
AYAR["web_arastirma_disari"] = False; ok("web_arastirma_disari kapalı", ns["ar_acik"]()[0] is False); del AYAR["web_arastirma_disari"]
AYAR["web_arastirma"] = False; ok("ana şalter web_arastirma kapalı → toplantı dışı da kapalı", ns["ar_acik"]()[0] is False); del AYAR["web_arastirma"]
GIZLI["acik"] = True; ok("gizli kipte kapalı", ns["ar_acik"]()[0] is False); GIZLI["acik"] = False
AYAR["beyin"] = {"varsayilan": {"tur": "openai-uyumlu", "saglayici": "gemini", "model": "m", "adres": "https://generativelanguage.googleapis.com/v1beta/openai"}}
ok("sağlayıcı Claude Code değilse kapalı (metin sağlayıcının dışına çıkmaz)", ns["ar_acik"]()[0] is False and "Claude Code" in ns["ar_acik"]()[1]); del AYAR["beyin"]
# argümanlar
ar = BEYIN.arastirma_args(AYAR)
ok("claude argümanı: yalnız WebSearch,WebFetch, stream-json, oturum kaydı yok", ar[ar.index("--tools") + 1] == "WebSearch,WebFetch" and ar[ar.index("--allowedTools") + 1] == "WebSearch,WebFetch" and "--no-session-persistence" in ar and "stream-json" in ar)
# kanca: bas-konus.py
bk = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read(); i = bk.index("def _konus_sor"); j = bk.index("arastirma_dene(metin, tur)", i)
ok("kanca _konus_sor'da 'düşünüyor' durumundan ve süreç açmadan önce", 0 < j - i < 9000 and j < bk.index('_konus_kur(durum="dusunuyor", soru=metin)', i) and j < bk.index("konus_ac()", i))
# arastirma_dene
def bekle_bitsin(sn=20):
    t0 = time.time()
    while time.time() - t0 < sn and ns["ARASTIRMA"]["aktif"]: time.sleep(0.05)
    time.sleep(0.2)
tur = {"kaynak": "bas"}; TOP["var"] = True
ok("toplantı sürerken araştırma kipine girmez (davranış değişmez)", ns["arastirma_dene"]("Orbitek'i araştır", tur) is False and not cagrilar())
TOP["var"] = False
ok("hitap/karşı tur kaynağı (toplantı yolu) girmez", ns["arastirma_dene"]("Orbitek'i araştır", {"kaynak": "hitap"}) is False)
ok("araştırma isteği olmayan soru normal yola gider", ns["arastirma_dene"]("Yarın saat kaçta toplantı var", tur) is False)
AYAR["web_arastirma_disari"] = False; ok("kapalıyken istek bugünkü gibi asistana gider (False)", ns["arastirma_dene"]("Orbitek'i araştır", tur) is False); del AYAR["web_arastirma_disari"]
GIZLI["acik"] = True; SES.clear(); r = ns["arastirma_dene"]("Orbitek'i araştır", tur); GIZLI["acik"] = False
ok("gizli kipte: araştırma yok, sebebi söylenir, claude çağrılmaz", r is True and "Gizli" in KONUS.get("cevap", "") and not cagrilar())
SES.clear(); r = ns["arastirma_dene"]("şu firmayı araştır", tur)
ok("belirsiz konuda hangisi diye sorar, claude çağrılmaz", r is True and "Hangi" in KONUS.get("cevap", "") and not cagrilar())
# gerçek akış (sesli, bekleme cümlesi)
ns["AR_BEKLE_SN"] = 0.3; SES.clear(); AYAR["kisilik"] = None
r = ns["arastirma_dene"]("Yavas Orbitek'i araştır", tur); ok("istek araştırma kipine alındı, durum düşünüyor", r is True and KONUS.get("durum") == "dusunuyor" and ns["ARASTIRMA"]["aktif"] == "Yavas Orbitek")
ok("sürerken ikinci araştırma reddedilir", ns["arastirma_dene"]("Başka Firma'yı araştır", tur) is True and "sürüyor" in KONUS.get("cevap", "") and KONUS.get("durum") == "hazir")
bekle_bitsin()
ok("uzun sürünce kısa bekleme cümlesi söylendi (bir kez)", sum(1 for m in SES if "Araştırıyorum" in m) == 1)
ok("sonunda Konuş cevabı: sesli özet, '---', kaynaklı tam metin; sesli özet okundu", KONUS.get("durum") == "hazir" and "\n\n---\n" in KONUS.get("cevap", "") and "üç bağımsız kaynak" in KONUS["cevap"].split("---")[0] and "https://orbitek.example/hakkimizda" in KONUS["cevap"] and any("üç bağımsız" in m for m in SES))
c = cagrilar()[-1]
ok("claude'a giden istemde kanarya yok (döküm, iç sayı, e-posta, telefon, toplantı başlığı); yalnız konu", not any(k.lower() in (c["stdin"] + " ".join(c["args"])).lower() for k in KANARYA) and "KONU: Yavas Orbitek" in c["stdin"])
dos = sorted(os.listdir(os.path.join(BASE, "arastirma"))); kj = json.load(open(os.path.join(BASE, "arastirma", [f for f in dos if f.endswith(".json")][-1]), encoding="utf-8"))
ok("kayıt: konu, 4 sorgu, 3 sayfa, 4 kaynak (3 bağımsız alan adı…), süre, maliyet, kanal", kj["konu"] == "Yavas Orbitek" and kj["sorgu_sayisi"] == 4 and kj["sayfa_sayisi"] == 3 and kj["kaynak_sayisi"] == 4 and kj["bagimsiz_kaynak"] == 4 and kj["maliyet"] == 0.0432 and kj["kanal"] == "bas" and kj["sure_sn"] >= 1 and kj["durum"] == "ok")
ok("kayıt .md dosyası kaynaklı ve izinli (0600)", any(f.endswith(".md") for f in dos) and oct(os.stat(os.path.join(BASE, "arastirma", dos[-1])).st_mode & 0o777) == "0o600")
cg = [json.loads(l) for l in open(os.path.join(BASE, "claude-cagri.jsonl"), encoding="utf-8")]
ok("claude-cagri.jsonl: is arastirma, süre, maliyet, sorgu/sayfa/kaynak sayıları; metin yok", cg[-1]["is"] == "arastirma" and cg[-1]["maliyet"] == 0.0432 and cg[-1]["sorgu"] == 4 and cg[-1]["bagimsiz"] == 4 and "Orbitek" not in json.dumps(cg[-1]))
# kişi araştırması: kurum aramaya gider, kişi iletişim bilgisi gitmez; yerel bilgi kayıtta
ns["arastirma_dene"]("Ayşe Örnek hakkında araştırma yap", tur); bekle_bitsin(); c = cagrilar()[-1]
ok("kişi: istemde ad + kurum ipucu, e-posta/telefon/geçmiş toplantı yok", "KONU: Ayşe Örnek" in c["stdin"] and "Orbitek" in c["stdin"] and not any(k.lower() in c["stdin"].lower() for k in KANARYA))
def kayit_konu(k): return [j for j in (json.load(open(os.path.join(BASE, "arastirma", f), encoding="utf-8")) for f in os.listdir(os.path.join(BASE, "arastirma")) if f.endswith(".json")) if j["konu"] == k][0]
kj = kayit_konu("Ayşe Örnek")
ok("kişi kaydında yerel bilgi (Kişiler, geçmiş toplantı) aktarıcıda tutulur", any("Kişiler" in s for s in kj["yerel"]) and any(KANARYA[4] in s for s in kj["yerel"]))
# tek kaynak → uyarı; hata
SES.clear(); ns["arastirma_dene"]("Tekkaynak A.Ş.'yi araştır", tur); bekle_bitsin()
ok("3'ten az bağımsız kaynak: kayıtta uyarı, sesli özette 'doğrulanmadı'", "doğrulanmadı" in KONUS.get("cevap", "").split("---")[0] and "Yalnız" in " ".join(kayit_konu("Tekkaynak A.Ş.")["uyari"]))
ns["arastirma_dene"]("Bozuk Firma'yı araştır", tur); bekle_bitsin()
ok("claude hata dönerse Konuş cevabı hatayı söyler, aktif araştırma temizlenir", "tamamlanamadı" in KONUS.get("cevap", "") and ns["ARASTIRMA"]["aktif"] is None)
v = ns["arastirma_view"](); ok("arastirma_view listesi: son kayıtlar, tam metin yok", len(v["kayitlar"]) >= 4 and "metin" not in v["kayitlar"][0] and v["kayitlar"][0]["konu"].startswith("Bozuk"))
ok("arastirma_view kötü id reddedilir", ns["arastirma_view"]("../ayar")["hata"] == "id")
# --- 2) uçtan uca: yalıtılmış aktarıcı, pano kutusu → /girdi → araştırma ------------------------------------------------------------------------------------------------
PORT = bos_port(8791); E = os.path.join(T, "e2e"); canli = os.path.join(E, "canli"); os.makedirs(canli); proje = os.path.join(E, "proje"); os.makedirs(proje)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglam.py", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), E)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(E, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(E, "pano"))
# geçmiş toplantı: Orbitek geçiyor; döküm satırında kanarya (yalnız yerelde kalmalı)
open(os.path.join(canli, "2026-10-30-1000-Gecmis-Toplanti.md"), "w", encoding="utf-8").write("# Gecmis Toplanti\n\n| 10:01 | Deniz T | Orbitek Yazılım sözleşmesi KANARYA-DOKUM-7731 üzerinden konuşuldu. | |\n")
ayar_y = os.path.join(E, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": E, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_on_ac": False,
                                                    "pocket_python": "/yok/python", "pocket_hf": "/yok", "konusma": False}, open(ayar_y, "w"))
p = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=E, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar_y, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
                     stdout=open(os.path.join(E, "r.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1.5); H = {"X-Suflor-Anahtar": open(os.path.join(canli, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{PORT}"}
    def post(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=H), timeout=20).read())
    def get(yol): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", headers=H), timeout=10).read())
    n0 = len(cagrilar()); g = post("/girdi", {"text": "Orbitek Yazılım'ı araştır"}); k = {}
    for _ in range(120):
        k = get("/status")["konus"]
        if "Orbitek" in (k.get("soru") or "") and k.get("durum") in ("hazir", "hata"): break
        time.sleep(0.25)
    ok("kutu: yazı araştırma kipine girdi, cevap sesli özet + '---' + kaynaklı metin", k.get("durum") == "hazir" and "\n---\n" in (k.get("cevap") or "") and "https://sicil.example.gov/kayit" in k["cevap"])
    c = cagrilar()[n0:]
    ok("tek claude çağrısı; geçmiş toplantı döküm kanaryası ve başlığı istemde yok", len(c) == 1 and "KONU: Orbitek Yazılım" in c[0]["stdin"] and "KANARYA" not in c[0]["stdin"] + " ".join(c[0]["args"]) and "gecmis" not in c[0]["stdin"].lower())
    kayit = [f for f in os.listdir(os.path.join(canli, "arastirma")) if f.endswith(".json")]; kj = json.load(open(os.path.join(canli, "arastirma", kayit[-1]), encoding="utf-8"))
    print("   yerel:", kj["yerel"], kj["kanal"])
    ok("kayıt canli/arastirma/: kanal kutu; yerel bilgide geçmiş toplantı başlığı var, döküm satırı yok", kj["kanal"] == "kutu" and any("Geçmiş toplantı" in s for s in kj["yerel"]) and "KANARYA" not in json.dumps(kj))
    ok("/arastirma uçları (anahtarlı): liste ve tek kayıt", get("/arastirma")["kayitlar"][0]["id"] == kj["id"] and get("/arastirma?id=" + kj["id"])["kaynaklar"])
    try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/arastirma", timeout=5); anahtarsiz = False
    except urllib.error.HTTPError as e: anahtarsiz = e.code == 401
    ok("/arastirma anahtarsız 401", anahtarsiz)
    ok("aktarıcıda hata yok, günlükte ARAŞTIRMA satırları", "Traceback" not in open(os.path.join(E, "r.log"), encoding="utf-8").read() and "ARAŞTIRMA: bitti" in open(os.path.join(E, "r.log"), encoding="utf-8").read())
finally:
    p.terminate()
    try: p.wait(10)
    except subprocess.TimeoutExpired: p.kill()
shutil.rmtree(T, ignore_errors=True)
print("\n" + ("TAMAM" if not HATA else f"KALDI: {len(HATA)}")); sys.exit(1 if HATA else 0)
