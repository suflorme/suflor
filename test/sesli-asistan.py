#!/usr/bin/env python3
# Sesli asistan (9 Kasım): KAYIT önerisine sesli onay + sonuç cümlesi, "devamını/tekrar oku", liste okuma, "panoyu aç", toplantı dışı devam penceresi.
# Bölüm 1: aktarıcı yalıtılmış kopyadan modül olarak yüklenir (ses çalınmaz, seslendir yakalanır). Bölüm 2: yalıtılmış aktarıcı + sahte claude (kota yok), SUFLOR_TEST_METIN ile
# Whisper'sız (söz metin olarak gelir), uçtan uca: KAYIT etiketi → sesli kart → "Evet" → Geri al süresi → yazıldı → "Yazıldı." ve devam penceresi.
# brifing-ses.py (soru_*, sesli_cevap, kayit_sonuc_sesle), bas-konus.py (_konus_cumle, DEVAM, konus_yerel_komut, konus_devam_pencere), sohbet.py, izin.py değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/sesli-asistan.py      (~1 dk; kaldı → çıkış 1)
import importlib.util as u, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8791)
T = os.path.realpath(tempfile.mkdtemp(prefix="sesli-as-")); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py", "baglam.py", "whisper-isci.py", "yapi.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc"): sys.exit("atlandı: Brifing.app ya da swiftc yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)  # Konuş açık süreç kipi bu uygulamayla çalışır (sahte claude'u o başlatır)
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
# ---------- Bölüm 1: modül ----------
os.environ.update(SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="1", SUFLOR_AYAR=os.path.join(T, "ayar1.json"))
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "ortak": os.path.join(T, "yok")}, open(os.path.join(T, "ayar1.json"), "w"))
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli1"), "--port", str(PORT)]; cwd0 = os.getcwd(); os.chdir(T)
sp = u.spec_from_file_location("relay_t", os.path.join(T, "relay.py")); m = u.module_from_spec(sp); sp.loader.exec_module(m)
SOY = []; m.seslendir = lambda metin, *a, **k: (SOY.append(metin), True)[1]; m.ses_durdur = lambda: None; m.AYAR["konusma"] = True; m.GERI_AL_SN = 0.3
sess = lambda: (lambda x: (SOY.clear(), x)[1])(list(SOY))
# -- 3/4: Markdown temizliği, liste okuma, saklama
md = "## Başlık\n**Kalın** metin [bağlantı](http://x.test) `kod`.\n| a | b |\n|---|---|\n| 1 | 2 |\n- madde bir\n2) madde iki\n```\nsil\n```"
t = m.md_temizle(md)
ok(f"Markdown temizliği: {t!r}", t == "Başlık. Kalın metin bağlantı kod. a, b. 1, 2. madde bir. madde iki." and "*" not in t and "|" not in t and "#" not in t and "http" not in t)
tur = {"sesli": True, "kaynak": "bas", "tampon": "", "metin": ""}
for parca in ("Şunlar var:\n- Bütçe onayı", "\n- Teslim tarihi\n- Ali'nin işi\n- Fiyat listesi\n- Rapor", "\nSon olarak kısa bir not."):
    tur["tampon"] += parca; m._konus_cumle(tur)
m._konus_cumle(tur, son=True); o = sess()
ok(f"liste: giriş + ilk 3 öğe sırayla, 'N tane daha var' bir kez: {o}", o[0] == "Şunlar var:" and o[1:4] == ["İlki: Bütçe onayı.", "Sonra: Teslim tarihi.", "Bir de: Ali'nin işi."]  # 9 Kasım (dost): sıra sözcükleri konuşma dilinde
   and "2 tane daha" in o[4] and "panoda" in o[4].lower() and o[4].endswith("Son olarak kısa bir not.") and len(o) == 5)
ok("fazla öğeler 'devamını oku' için saklandı", tur["kalan"] == ["Fiyat listesi.", "Rapor."] and len(tur["okunanlar"]) == 5)
tur2 = {"sesli": True, "kaynak": "bas", "tampon": "- Bir\n- İki\n- Üç\n- Dört\n- Beş", "metin": ""}; m._konus_cumle(tur2, son=True); o = sess()
ok(f"liste cevabın sonundaysa bildirim cevap bitince okunur: {o[-1]}", len(o) == 4 and "2 tane daha" in o[-1] and "panoda" in o[-1].lower())  # cümle dönüşümlü (kisilik.py cesit)
tur3 = {"sesli": True, "kaynak": "bas", "tampon": "", "metin": ""}
for c_ in ("Bir numara. ", "İki numara. ", "Üç numara. ", "Dört numara. ", "Beş numara. ", "Altı numara. ", "Yedi numara. "): tur3["tampon"] += c_; m._konus_cumle(tur3)
m._konus_cumle(tur3, son=True); o = sess()
ok(f"düz cevapta okuma sınırı aynı (5 cümle), kalan saklandı: {o}", o == ["Bir numara.", "İki numara.", "Üç numara.", "Dört numara.", "Beş numara."] and tur3["kalan"] == ["Altı numara.", "Yedi numara."])
# -- 3: devamını oku / tekrar oku
tur3["metin"] = "Bir numara. İki numara. Üç numara. Dört numara. Beş numara. Altı numara. Yedi numara.\n---\n## Ayrıntı\n- şu madde\n- bu madde\n\nSon cümle burada."
m.konus_devam_kaydet(tur3)
ok(f"saklanan: okunan 5 + okunmayan {m.DEVAM['tam'][5:]}", m.DEVAM["tam"][5:] == ["Altı numara.", "Yedi numara.", "Ayrıntı.", "şu madde.", "bu madde.", "Son cümle burada."] and m.DEVAM["i"] == 5)
for kalip, beklenen in (("Devamını oku.", "d"), ("devam", "d"), ("Peki, ayrıntıyı oku.", "d"), ("Continue reading", "d"), ("Tekrar oku.", "t"), ("Bir daha oku", "t"), ("Read that again.", "t"), ("Devamı nasıl olacak?", None),
                        ("Ayrıntıları panoda gördüm.", None), ("Bunu tekrar oku diye kaydet", None), ("Merhaba", None)):
    ok(f"komut kalıbı {kalip!r} → {beklenen}", bool(m.DEVAM_OKU_RX.match(kalip)) == (beklenen == "d") and bool(m.TEKRAR_OKU_RX.match(kalip)) == (beklenen == "t"))
c = m.konus_yerel_komut("Devamını oku.", {"kaynak": "bas"}); o = sess()
ok(f"devamını oku: 5 cümlelik parça, Claude'a gitmeden: {o}", o == ["Altı numara. Yedi numara. Ayrıntı. şu madde. bu madde."] and c.startswith("Altı numara.") and "Kalan 1" in c)
c = m.konus_yerel_komut("tekrar oku", {"kaynak": "bas"}); o = sess()
ok(f"tekrar oku: son okunan parça yeniden: {o}", o == ["Altı numara. Yedi numara. Ayrıntı. şu madde. bu madde."])
c = m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}); o = sess(); c2 = m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}); o2 = sess()
ok(f"son parça sonra 'okunacak başka bir şey kalmadı': {o} / {o2}", o == ["Son cümle burada."] and len(o2) == 1 and re.search(r"kalmadı|hepsi bu", o2[0]))  # dönüşümlü cümle: anlam denetimi
c = m.konus_yerel_komut("tekrar oku", {"kaynak": "bas"}); o = sess()
ok("kalan yokken tekrar oku son parçayı tekrarlar", o == ["Son cümle burada."])
tm = m.toplanti_var; m.toplanti_var = lambda: True
ok("toplantıda kapalı (Claude'a gider)", m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}) is None and m.konus_yerel_komut("panoyu aç", {"kaynak": "bas"}) is None)
m.toplanti_var = tm; g0 = m.GIZLI["acik"]; m.GIZLI["acik"] = True
ok("gizli kipte devamını oku kapalı", m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}) is None); m.GIZLI["acik"] = g0
m.DEVAM.update(tam=[], i=0, son=(0, 0))
ok("saklı cevap yokken 'devamını oku' Claude'a gider", m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}) is None)
yz = {"kaynak": "yazili", "sesli": False, "metin": "Yazılı bir cevap. İkinci cümle.\n---\nAyrıntı satırı."}; m.konus_devam_kaydet(yz)
ok("yazılı tur: hiçbir şey okunmamıştı, 'devamını oku' baştan okur", m.DEVAM["i"] == 0 and (m.konus_yerel_komut("devamını oku", {"kaynak": "bas"}), sess())[1] == ["Yazılı bir cevap. İkinci cümle. Ayrıntı satırı."])
# -- 5: panoyu aç
nb = []; m.STATE["_menu_yokluyor"] = time.time()
for soz, bolum in (("Panoyu aç.", None), ("Kararları göster.", "kararlar"), ("Kararlar ve işleri göster", "kararlar"), ("Takvimi göster", "takvim"), ("Peki, panoyu göster", None), ("Show the calendar", "takvim"), ("Open the panel", None)):
    c = m.konus_yerel_komut(soz, {"kaynak": "bas"}); pa = m.STATE.get("pano_ac") or {}
    ok(f"{soz!r} → pano açma isteği, bölüm {bolum}: {c}", bool(c) and pa.get("bolum") == bolum and time.time() - pa.get("t", 0) < 2); m.STATE.pop("pano_ac", None); sess()
m.STATE.pop("_menu_yokluyor", None)
ok("menü uygulaması yoksa tarayıcıda açma yolu (deneme: günlüğe yazılır), cümle söylenir", bool(m.konus_yerel_komut("takvimi göster", {"kaynak": "bas"})) and re.fullmatch(r"(Panoyu açtım|Açtım)[,;] takvim Bugün.*", " ".join(sess())) is not None)
ok("pano komutu olmayan söz Claude'a gider", all(m.konus_yerel_komut(x, {"kaynak": "bas"}) is None for x in ("Takvimimde ne var?", "Panoyu neden açtın", "Kararları özetle")))
cv = m.cards_view(); m.STATE["pano_ac"] = {"id": "p1", "t": time.time(), "bolum": "kararlar"}
ok("cards_view pano_ac'ta bölüm gider (menü/pano ileride okur)", m.cards_view()["pano_ac"] == {"id": "p1", "bolum": "kararlar"}); m.STATE.pop("pano_ac", None)
# -- 1/2: KAYIT kartı sesli
def kart(ozet, neden="Kullanıcı istedi", sesli=True):
    x_ = m.izin_iste("kayit", f"Kayda yazayım mı? {neden} — {ozet}", {"komut": "karar_onayla", "arg": {"id": "k1"}, "ozet": ozet, "neden": neden}, sesli=sesli); return x_
m.SORU.update(liste=[], aktif=None); sess()
i1 = kart("Karar k1 onaylanacak"); o = sess()
ok(f"kayıt kartı sesle sorulur (neden + ne yazılacak + soru): {o}", o == ["Deniz, Kullanıcı istedi. Karar k1 onaylanacak. Kayda yazayım mı?"] and m.SORU["aktif"] == i1)
c = m.sesli_cevap("Evet.", i1); o = sess(); ey = next(x for x in m.EYLEMLER if x["id"] == i1)
ok(f"'Evet' yerelde çözüldü: {c!r}", c == "Yazıyorum." and ey["durum"] == "onaylandi" and ey["kaynak"] == "ses" and o == ["Yazıyorum."])
ok("Geri al süresi dolmadan yazma kararı uygulanmadı", m.IZIN[i1]["karar"] is None)
time.sleep(1.6)
ok("süre dolunca karar uygulandı (bekleyen yazar)", m.IZIN[i1]["karar"] == "onaylandi" and m.izin_bekle(i1, 1) == "onaylandi")
m.kayit_sonuc_sesle(i1, True, "onaylandi", "Karar k1 onaylandı"); o = sess()
ok(f"sonuç cümlesi (yalnız sesle sorulan): {o}", o == ["Yazıldı."])
m.kayit_sonuc_sesle(i1, True, "onaylandi"); ok("aynı kart için ikinci kez okunmaz", sess() == [])
i2 = kart("Karar k1 onaylanacak"); sess(); m.sesli_cevap("Evet.", i2); sess(); ok("Geri al: sesli karar geri alınır", m.eylem_geri_al({"id": i2}) and next(x for x in m.EYLEMLER if x["id"] == i2)["durum"] == "bekliyor"); sess()
time.sleep(1.6)
ok("geri alınan karar hiç uygulanmadı, soru yeniden okundu", m.IZIN[i2]["karar"] is None and m.SORU["aktif"] == i2)
m.SORU.update(liste=[], aktif=None)
i3 = kart("Karar k1 onaylanacak"); sess(); c = m.sesli_cevap("Hayır.", i3); o = sess(); time.sleep(1.6)
m.kayit_sonuc_sesle(i3, False, "reddedildi"); o2 = sess()
ok(f"'Hayır': {c!r}, yazılmadı, ek sonuç cümlesi yok: {o} {o2}", c == "Peki, yazmıyorum." and m.IZIN[i3]["karar"] == "reddedildi" and o == ["Peki, yazmıyorum."] and o2 == [])
m.SORU.update(liste=[], aktif=None); sess()
a1 = kart("Karar k1 onaylanacak"); a2 = kart("İş s3 yapıldı işaretlenecek"); a3 = kart("Karar k2 düzeltilecek"); d_ = m.izin_iste("yanki", "Başka bir izin", {}, sesli=True); o = sess()
ok(f"kuyruk: yalnız ilk kart soruldu: {o}", len(o) == 1 and m.SORU["aktif"] == a1 and m.SORU["liste"] == [a2, a3, d_])
c = m.sesli_cevap("Hepsini onayla.", a1); o = sess(); time.sleep(1.6)
ey = {x["id"]: x for x in m.EYLEMLER}
ok(f"'hepsi' yalnız kayıt kartlarını onaylar, başka izne dokunmaz, diziyi sürdürür: {c!r} {o}", c == "Tamam, 3 kaydı da yazıyorum." and all(ey[i]["durum"] == "onaylandi" and m.IZIN[i]["karar"] == "onaylandi" for i in (a1, a2, a3))
   and ey[d_]["durum"] == "bekliyor" and m.SORU["aktif"] == d_ and len(o) == 2)
m.SORU.update(liste=[], aktif=None); sess()
i4 = kart("Karar k1 onaylanacak"); sess(); c = m.sesli_cevap("Evet ama Ali'ye ata.", i4); o = sess()
ok(f"'evet ama…' kayıt kartını onaylamaz (yeniden sorar): {c!r}", ey is not None and next(x for x in m.EYLEMLER if x["id"] == i4)["durum"] == "bekliyor" and ("yazayım mı" in c.lower()))
m.SORU.update(liste=[], aktif=None); sess()
i5 = kart("Karar k1 onaylanacak", sesli=False); ok("sesli=False (yazılı/toplantı turu): sesli soru yok, yalnız kart", sess() == [] and m.SORU["aktif"] is None)
tm = m.toplanti_var; m.toplanti_var = lambda: True; i6 = kart("Karar k1 onaylanacak"); ok("toplantı sürerken sesli soru yok (kart akışı aynen)", sess() == [] and m.SORU["aktif"] is None); m.toplanti_var = tm
m.SORU.update(liste=[], aktif=None)
# -- 6: devam penceresi: yankı ve kapanış sözü
t1 = time.time(); m.KENDI_SES.clear(); m.kendi_ses_kaydet("Bütçe yüz yirmi bin lira olarak onaylandı.", t1 - 3, t1 - 0.5)
ok("devam penceresinde yankı sayılmaz", m.devam_yanki("Bütçe yüz yirmi bin lira olarak onaylandı.", {"t_birak": t1, "kayit_sn": 2.5}) and not m.devam_yanki("Peki ya teslim tarihi ne olacak?", {"t_birak": t1, "kayit_sn": 2.5}))
for soz, kapanir in (("Tamam.", True), ("Teşekkürler.", True), ("Tamam, teşekkürler.", True), ("Sağ ol.", True), ("Thanks.", True), ("Tamam ama saati değiştir", False), ("Peki ya yarın?", False), ("Teşekkürler, bir şey daha soracağım", False)):
    ok(f"kapanış sözü {soz!r} → {kapanir}", bool(m.DEVAM_KAPAT_RX2.match(soz)) == kapanir)
os.chdir(cwd0)
# ---------- Bölüm 2: aktarıcı + sahte claude ----------
d = os.path.join(T, "canli"); os.makedirs(d); proje = os.path.join(T, "proje"); os.makedirs(proje)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")
open(sahte, "w").write('''#!/usr/bin/env python3
import json, re, sys, time
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.strip().splitlines()[-1]
    if "LISTEYE" in soru: c = ["Şunlar var:\\n", "- Bütçe onayı\\n", "- Teslim tarihi\\n", "- Ali'nin işi\\n", "- Fiyat listesi\\n", "- Rapor\\n"]
    elif "UZUN" in soru: c = ["Bir numara. ", "İki numara. ", "Üç numara. ", "Dört numara. ", "Beş numara. ", "Altı numara. ", "Yedi numara.\\n---\\n", "## Ayrıntı\\n", "**Kalın** madde bir.\\n", "Son cümle burada.\\n"]
    elif "ETIKET:" in soru: c = ["Onayına sundum."] + ["\\n[KAYIT: " + e + "]" for e in re.findall(r"ETIKET:(\\{.*?\\})(?=\\s*ETIKET:|\\s*$)", soru)]
    else: c = ["Merhaba, buradayım."]
    for p in c: time.sleep(0.05); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": p}}})
    pr({"type": "result", "duration_api_ms": 100, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
sys.path.insert(0, T); import yapi
A_ = "2026-11-04-1000-Plan-Toplantisi"; c_ = yapi._db(d)
with c_:
    c_.execute("INSERT INTO kayit (id, toplanti, baslik, tarih, tur, sahip, metin, durum) VALUES (?,?,?,?,?,?,?,?)", (3, A_ + ".md", "Deneme toplantısı", "2026-11-04", "is", "Deniz T", "Raporu hazırla", "acik"))
c_.close()
open(os.path.join(d, "son-toplantilar.jsonl"), "w", encoding="utf-8").write(json.dumps({"id": "s1", "at": "2026-11-04T11:00:00", "dosya": A_ + ".md", "baslik": "Deneme toplantısı", "ozet": "", "kopya": ""}) + "\n")
yol = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_zaman_asimi_sn": 0, "konus_bekle_sn": 0,
    "konus_ara_sn": 0, "konus_on_ac": False, "konus_devam_sn": 3, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, open(yol, "w"))
P = None
class Uc:
    def __init__(s, port, anahtar): s.port, s.h = port, {"X-Suflor-Anahtar": anahtar, "Origin": f"http://127.0.0.1:{port}"}
    def post(s, yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}{yol}", data=json.dumps(v).encode(), headers=s.h), timeout=20).read())
    def status(s): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{s.port}/status", headers=s.h), timeout=10).read())
    def bekle(s, parca, sn=40):
        t0 = time.time()
        while time.time() - t0 < sn:
            k = s.status()["konus"]
            if parca in (k.get("soru") or "") and k["durum"] in ("hazir", "hata", "dinliyor"): return k
            time.sleep(0.25)
        return s.status()["konus"]
    def kosul(s, f, sn=20):
        t0 = time.time()
        while time.time() - t0 < sn:
            if f(): return True
            time.sleep(0.25)
        return False
try:
    P = subprocess.Popen([sys.executable, "relay.py", "--dir", d, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=yol, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="1", SUFLOR_TEST_METIN="1"),
                         stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        if os.path.exists(os.path.join(d, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); uc = Uc(PORT, open(os.path.join(d, "kart-anahtari.txt")).read().strip()); log = lambda: open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    db = lambda sql: (lambda c: (lambda r: (c.close(), r)[1])(c.execute(sql).fetchall()))(sqlite3.connect(os.path.join(d, "karar-grafi.sqlite")))
    ses = lambda: [l.split("SES (deneme):", 1)[1].split(" · ", 1)[1] for l in log().splitlines() if "SES (deneme):" in l and " · " in l]
    E = "ETIKET:" + json.dumps({"komut": "is_durum", "arg": {"id": "s3", "durum": "yapildi"}, "neden": "Kullanıcı istedi"}, ensure_ascii=False)
    # liste okuma, uçtan uca
    r0 = uc.post("/bas-konus", {"metin": "bana LISTEYE göre say"}); uc.bekle("LISTEYE"); time.sleep(0.5); L = log()
    if os.environ.get("HATA_AYIKLA"): print(r0, uc.status()["konus"], log()[-1500:])
    ok("uçtan uca liste: ilk 3 öğe + 'N tane daha var'; tire işareti okunmadı", "İlki: Bütçe onayı." in L and "Bir de: Ali'nin işi." in L and "2 tane daha" in L and "Fiyat listesi" not in "\n".join(ses()) and "- Bütçe" not in "\n".join(ses()))
    pen = lambda: uc.status()["konus"]["sohbet"]
    ok("devam penceresi: okuma bitince açıldı (sohbet.acik + devam kalan sn göstergesi)", uc.kosul(lambda: pen().get("acik") is True, 40) and isinstance(pen().get("devam"), (int, float)) and pen()["devam"] <= 3 and "devam penceresi açıldı — 3 sn" in log())
    ok("sessizlikte 3 sn sonra sessizce kapandı (panoda 'Sohbet kapandı' izi yok)", uc.kosul(lambda: pen().get("acik") is False, 10) and "SOHBET: kapandı (devam penceresi bitti" in log() and "kapandi" not in pen())
    uc.post("/bas-konus", {"metin": "bana LISTEYE göre say"}); uc.bekle("LISTEYE"); uc.kosul(lambda: pen().get("acik") is True, 40)
    k = uc.post("/bas-konus", {"metin": "devamını oku"}); time.sleep(0.5)
    ok("pencere açıkken 'devamını oku' Claude'a gitmeden liste fazlasını okur", ses()[-1].startswith("Fiyat listesi. Rapor.") and "devamını oku — 2 cümle" in log() and log().count("ön arama sonuç yok") == 2)
    uc.post("/bas-konus", {"metin": "Tamam, teşekkürler."}); time.sleep(0.5)
    ok("kapanış sözü pencereyi kapatır, Claude'a gitmez", not uc.status()["konus"]["sohbet"]["acik"] and "devam: kapanış sözü" in log() and "Merhaba, buradayım" not in "\n".join(ses()))
    # uzun cevap + ayrıntı
    uc.post("/bas-konus", {"metin": "bana UZUN anlat"}); uc.bekle("UZUN"); uc.kosul(lambda: pen().get("acik") is True, 40)
    ok("5 cümleden sonrası okunmadı", "Altı numara." not in "\n".join(ses()[-6:]))
    uc.post("/bas-konus", {"metin": "devamını oku"}); time.sleep(0.4); uc.post("/bas-konus", {"metin": "Tekrar oku."}); time.sleep(0.4)
    s_ = ses()
    ok(f"ayrıntı ('---' sonrası) Markdown'sız parçayla okunur, tekrar oku aynısını yineler: {s_[-2:]}", s_[-2] == "Altı numara. Yedi numara. Ayrıntı. Kalın madde bir. Son cümle burada." and s_[-1] == s_[-2] and "**" not in s_[-1] and "#" not in s_[-1])
    # panoyu aç
    uc.post("/bas-konus", {"metin": "Kararları göster."}); time.sleep(0.4)
    ok("'kararları göster' yerelde (menü yoksa tarayıcı yolu: deneme günlüğü), Claude'a gitmez", "AÇ (deneme): pano #kararlar" in log() and re.search(r"(Panoyu açtım|Açtım)[,;] kararlar ve işler", "\n".join(ses())) is not None)
    # KAYIT sesli onay, uçtan uca (kota yok)
    uc.kosul(lambda: pen().get("acik") is False, 15); n0 = len(ses()); p0 = log().count("devam penceresi açıldı")
    uc.post("/bas-konus", {"metin": "s3 işini yapıldı işaretle " + E}); uc.bekle("s3 işini"); time.sleep(0.6)
    ok(f"KAYIT kartı sesle soruldu: {ses()[n0:]}", any(x.startswith("Deniz, Kullanıcı istedi.") and x.endswith("Kayda yazayım mı?") for x in ses()[n0:]) and "SES: yazayım mı?" in log())
    time.sleep(6); ok("kayıt sorusu beklerken devam penceresi açılmadı (cevap kartta)", log().count("devam penceresi açıldı") == p0 and not pen().get("acik"))
    uc.post("/bas-konus", {"metin": "Evet."}); time.sleep(0.5); e0 = db("SELECT durum FROM kayit WHERE id = 3")[0][0]
    ok(f"'Evet' Claude'a gitmedi, 'Yazıyorum.' söylendi, Geri al süresi dolmadan yazılmadı ({e0})", "Yazıyorum." in ses() and e0 == "acik" and "Merhaba, buradayım" not in "\n".join(ses()[n0:]))
    ok("Geri al süresi sonunda iş yazıldı ve 'Yazıldı.' okundu", uc.kosul(lambda: db("SELECT durum FROM kayit WHERE id = 3")[0][0] != "acik", 20) and uc.kosul(lambda: "Yazıldı." in ses(), 5))
    # reddet
    uc.post("/bas-konus", {"metin": "s3 işini tekrar açık yap " + E.replace("yapildi", "acik")}); uc.bekle("tekrar açık"); time.sleep(0.6)
    uc.post("/bas-konus", {"metin": "Hayır."}); time.sleep(0.4)
    ok("'Hayır' → 'Peki, yazmıyorum.'", ses()[-1] == "Peki, yazmıyorum." or "Peki, yazmıyorum." in ses()[-2:])
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    if P: P.terminate(); P.wait(5)
    if HATA or sys.exc_info()[0]: print("günlük:", os.path.join(T, "relay.log"))
    else: shutil.rmtree(T, ignore_errors=True)
print("sesli-asistan:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun: {HATA}"); sys.exit(1 if HATA else 0)
