#!/usr/bin/env python3
# Toplantı yapısı (yapi.py, v0.27.0): `yapi` → karar grafı (canli/karar-grafi.sqlite, 0600) + zihin haritası (tek HTML) · aynı toplantı ikinci kez
# yazılınca çoğalmaz · `graf --kim` ilk adla bulur, başka kişiyi getirmez · hazırlıkta "karar grafı" bölümü · haritada "Resim olarak indir" PNG
# üretir (headless Chrome) · ozet-hazir haritayı aktarıcıya verir, panodaki "Zihin haritası" açar (deneme kipi).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yapi.py      (kaldı → çıkış 1; ~20 sn)
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8777)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from gizlichrome import chrome_yolu, CHROME_EK  # Dock'ta görünmeyen kopya
CHROME = chrome_yolu()
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-yp-"); canli = os.path.join(T, "canli"); os.makedirs(canli)
def tc(*a): return subprocess.run([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", *a],
                                  capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)
Y = {"baslik": "Ayşe — bütçe", "tarih": "2026-10-11", "gorsel": "harita", "maddeler": [
    {"baslik": "Bütçe", "durum": "konuşuldu", "ogeler": [{"tur": "karar", "metin": "Bütçe 120 bin", "kim": "Ayşe Yılmaz", "saat": "10:12:30", "alinti": "120'de kalalım",
                                                          "netlik": "örtük", "varsayim": "Kur yıl sonuna kadar aynı kalır"},
                                                         {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Yılmaz"}, {"tur": "yanlis", "metin": "atılmalı"}]},
    {"baslik": "Teklif", "ogeler": [{"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "tarih": "2026-10-17"}, {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Ali K"},
                                    {"tur": "soz", "metin": "Faturaları gönderecek", "sahip": "Ayşe Yılmaz"}]}], "oneri": "Gündemi bir gün önce gönder"}
yj = os.path.join(T, "ozet.yapi.json"); json.dump(Y, open(yj, "w"), ensure_ascii=False)
ozet = os.path.join(T, "ayse-toplanti-ozeti-20261011.md"); open(ozet, "w").write("# Özet\n\n## Toplantı çıktısı\n- **Kararlar (1):** Bütçe onaylandı\n- **Sahipli işler (2):** Ayşe — rapor — 15 Ekim; Ali — teklif — tarihsiz\n- **Açık kalanlar:** yok\n- **Öneri:** gündemi önceden gönder\n")
o = tc("yapi", yj, "--ozet", ozet)
db = os.path.join(canli, "karar-grafi.sqlite"); hy = ozet[:-3] + "-zihin-haritasi.html"
n = lambda: sqlite3.connect(db).execute("SELECT COUNT(*) FROM kayit").fetchone()[0]
# eski sözler defteri (sozler.json) bir kez grafa taşınır
json.dump({"sozler": [{"id": "s1", "kim": "Bora Kaya", "metin": "Eski söz", "tarih": "2026-01-02", "durum": "acik", "toplanti": "Eski", "at": "2026-01-01T10:00:00"}]},
          open(os.path.join(canli, "sozler.json"), "w"), ensure_ascii=False)
bak(f"yapi: 5 kayıt, geçersiz tür atıldı ({o.stdout.strip().splitlines()[0] if o.stdout else o.stderr[-200:]})", os.path.exists(db) and n() == 5)
bak("veritabanı 0600", os.path.exists(db) and not os.stat(db).st_mode & 0o077)
tc("yapi", yj, "--ozet", ozet); bak("aynı toplantı ikinci kez: çoğalmadı", n() == 5)
sl = tc("soz", "liste").stdout
bak("sözler defteri graftan: yapının işi ve sözü + taşınan eski söz", "Teklifi revize et" in sl and "Faturaları gönderecek" in sl and "Eski söz" in sl and "GEÇTİ" in sl
    and os.path.exists(os.path.join(canli, "sozler-tasindi.json")) and not os.path.exists(os.path.join(canli, "sozler.json")))
sid = re.search(r"(s\d+) \[acik\] Bora Kaya: Eski söz", sl)
k = tc("soz", "kapat", sid.group(1) if sid else "s0").stdout
bak("soz kapat: grafta kapanır, açık listede yok, --hepsi'de var", "[tutuldu]" in k and "Eski söz" not in tc("soz", "liste").stdout and "Eski söz" in tc("soz", "liste", "--hepsi").stdout)
tc("soz", "ekle", "Elle eklenen söz", "--kim", "Bora Kaya"); tc("yapi", yj, "--ozet", ozet)
bak("yapi yeniden yazılınca elle eklenen söz kalır", "Elle eklenen söz" in tc("soz", "liste", "--kim", "Bora").stdout)
g = tc("graf", "--kim", "ayşe").stdout
bak("graf --kim ilk adla: Ayşe'nin karar ve iddiası, Bora'nınki yok", "Bütçe 120 bin" in g and "95 bin" in g and "revize" not in g)
bak("graf --kim sahip: Bora'nın açık işi", "Teklifi revize et" in tc("graf", "--kim", "Bora").stdout)
h = tc("hazirlik", "--kim", "Ayşe Yılmaz").stdout
bak("hazırlıkta karar grafı bölümü", "karar grafı" in h and "95 bin" in h)
H = open(hy, encoding="utf-8").read() if os.path.exists(hy) else ""
bak("zihin haritası: tek dosya, dış kaynak yok, veri gömülü", H.startswith("<!doctype html>") and not re.search(r"(src|href)=[\"']https?://", H) and "Bütçe 120 bin" in H)
# PNG: indirme bağlantısının href'i yakalanır
dene = os.path.join(T, "dene.html"); open(dene, "w", encoding="utf-8").write(H.replace("ciz();\n</script>", "ciz();HTMLAnchorElement.prototype.click=function(){document.body.insertAdjacentHTML('beforeend','<pre id=png>'+this.download+'|'+this.href.slice(0,30)+'|'+this.href.length+'</pre>')};setTimeout(()=>document.getElementById('png').click(),300)\n</script>"))
cik = os.path.join(T, "o.html")
pr = subprocess.Popen([CHROME, "--headless=new", *CHROME_EK, "--disable-features=MacAppCodeSignClone", "--disable-gpu", f"--user-data-dir={T}/p", "--no-first-run", "--virtual-time-budget=4000", "--dump-dom", "file://" + dene], stdout=open(cik, "w"), stderr=subprocess.DEVNULL)
m = None
for _ in range(80):
    time.sleep(0.25); m = re.search(r'<pre id="png">(.*?)</pre>', open(cik, encoding="utf-8", errors="replace").read())
    if m: break
pr.kill(); pr.wait(5)
p = (m.group(1).split("|") if m else ["", "", "0"])
bak(f"Resim olarak indir: PNG ({p[0]}, {p[2]} karakter)", p[0].endswith(".png") and p[1].startswith("data:image/png;base64,") and int(p[2]) > 5000)
# 5 Kasım: görsel türü — "gorsel" alanı tek kaynak; alan yoksa en az 1 karar ya da 1 sahipli iş/söz → pano, hiçbiri yoksa zihin haritası (kurgu veri)
sys.path.insert(0, KOD); import yapi as YP
def yk(ogeler, **ek): return dict({"baslik": "Deneme", "tarih": "2026-10-11", "maddeler": [{"baslik": "A", "ogeler": ogeler}]}, **ek)
K2 = yk([{"tur": "karar", "metin": "K1", "kim": "Can Er", "saat": "10:00:00"}, {"tur": "karar", "metin": "K2", "kim": "Can Er", "saat": "10:05:00", "netlik": "tek"}])
bak("tür: alan yok, karar var → karar ve iş panosu", YP.gorsel_tur(K2) == "karar_is" and YP.gorsel_tur(yk([{"tur": "karar", "metin": "K"}])) == "karar_is")
bak("tür: alan yok, tek sahipli iş → pano; sahipsiz iş sayılmaz", YP.gorsel_tur(yk([{"tur": "is", "metin": "a", "sahip": "Can Er"}])) == "karar_is"
    and YP.gorsel_tur(yk([{"tur": "is", "metin": "a"}, {"tur": "soz", "metin": "b"}])) == "harita")
bak("tür: alan yok, karar ve iş yok → zihin haritası", YP.gorsel_tur(yk([{"tur": "soru", "metin": "Ne olacak?"}, {"tur": "iddia", "metin": "x"}])) == "harita")
bak("tür: \"gorsel\" alanı eşiği geçersiz kılar (iki yön)", YP.gorsel_tur(dict(K2, gorsel="harita")) == "harita"
    and YP.gorsel_tur(yk([{"tur": "soru", "metin": "Ne?"}], gorsel="karar_is")) == "karar_is" and YP.gorsel_tur(dict(K2, gorsel="saçma")) == "karar_is")
P = yk([{"tur": "karar", "metin": "K1", "kim": "Can Er", "saat": "23:50:00"}, {"tur": "is", "metin": "Uzun " * 60 + "son", "sahip": "Can Er", "tarih": "2026-10-20", "saat": "23:55:00"},
        {"tur": "is", "metin": "tarihsiz iş", "sahip": "Ece Su", "saat": "00:20:00"}, {"tur": "is", "metin": "kimsiz", "saat": "00:21:00"}, {"tur": "soru", "metin": "S?"}])
P["maddeler"].append({"baslik": "B", "ogeler": [{"tur": "karar", "metin": "K2", "saat": "00:10:00", "netlik": "ortuk"}]})
pv = YP.pano_veri(P, ["23:40:00", "00:40:00", "08:00:00"])  # 08:00 başka toplantı: kırpılır
z = pv["zaman"]
bak(f"pano: sayılar (karar 2, iş 3, tarihsiz 2, soru 1) {pv['say']}", pv["say"] == {"karar": 2, "is": 3, "tarihsiz": 2, "soru": 1, "sure_dk": 60})
bak("pano: sütunlar çoktan aza, Sahipsiz sonda; tarihli iş üstte", [c["ad"] for c in pv["sutunlar"]] == ["Can Er", "Ece Su", ""] and pv["sutunlar"][0]["isler"][0]["tarih"])
bak("pano: teyit bekleyen karar işaretli, veride netlik yoksa durum yok", [k["teyit"] for k in pv["kararlar"]] == [False, True] and not pv["kararlar"][0]["net"])
bak(f"zaman şeridi: öğe saatleri, gece yarısını aşar, döküm toplamı kırpılmış ({z['kaynak']} {z['bas']}–{z['son']})",
    z["kaynak"] == "oge" and z["bas"] == "23:40" and z["son"] == "00:40" and not z["tahmini"] and abs(sum(b["pay"] for b in z["bloklar"]) - 1) < 1e-3
    and [b["m"] for b in z["bloklar"]] == [0, 1, 0])
P2 = yk([{"tur": "karar", "metin": "K"}]); P2["maddeler"].append({"baslik": "B", "ogeler": []})
z2 = YP.zaman_seridi(P2, ["10:00:00", "10:30:00"]); z3 = YP.zaman_seridi(P2)
bak("zaman şeridi: saat yoksa döküm (eşit pay, tahmini), o da yoksa sıra", z2["kaynak"] == "dokum" and z2["tahmini"] and z2["sure_dk"] == 30
    and [m["dk"] for m in z2["maddeler"]] == [15, 15] and z3["kaynak"] == "sira" and z3["tahmini"] and "tahmini" in z3["not"] and z3["sure_dk"] is None)
P3 = yk([]); P3["maddeler"] = [{"baslik": "A", "baslangic": "10:00", "ogeler": []}, {"baslik": "B", "saat": "10:20", "bitis": "10:50", "ogeler": []}]
z4 = YP.zaman_seridi(P3)
bak("zaman şeridi: madde saatleri önce", z4["kaynak"] == "madde" and [m["dk"] for m in z4["maddeler"]] == [20, 30])
bak("döküm saatleri .md tablosundan", YP.dokum_saatleri(os.path.join(KOD, "test", "yapi.py")) == [] and
    (open(os.path.join(T, "d.md"), "w").write("| Saat | K |\n|---|---|\n| 10:00:01 | a |\n| 10:02:00 | b |\n") and YP.dokum_saatleri(os.path.join(T, "d.md")) == ["10:00:01", "10:02:00"]))
PH = YP.pano_html(P, ["23:40:00", "00:40:00"])
bak("pano: tek dosya, dış kaynak yok, veri gömülü, başlıkta tür", PH.startswith("<!doctype html>") and not re.search(r"(src|href)=[\"']https?://", PH)
    and "tarihsiz iş" in PH and "— karar ve iş panosu</title>" in PH)
# headless: kartlar çizilir, uzun metin kesilmez, karta tıklayınca ayrıntı; 420 px'de yatay taşma yok
ph = os.path.join(T, "pano.html"); open(ph, "w", encoding="utf-8").write(PH.replace("</script></html>", ";setTimeout(()=>{document.querySelector('.kart[data-o]').click();"
    "const u=[...document.querySelectorAll('.kart .m')].find(x=>x.textContent.endsWith('son'));document.body.insertAdjacentHTML('beforeend','<pre id=sonuc>'+document.querySelectorAll('.kart').length+'|'"
    "+getComputedStyle(document.getElementById('ayrinti')).display+'|'+(u&&u.scrollWidth<=u.clientWidth&&u.getClientRects().length>0)+'|'+document.querySelectorAll('.serit button').length+'</pre>')},200)</script></html>"))
sar = os.path.join(T, "sar.html"); open(sar, "w").write('<!doctype html><body style=margin:0><iframe id=f src="pano.html" style="width:420px;height:900px;border:0"></iframe><script>f.onload=()=>setTimeout(()=>{const d=f.contentDocument;'
    'document.body.insertAdjacentHTML("beforeend","<pre id=gen>"+d.documentElement.scrollWidth+"|"+(d.getElementById("sonuc")||{}).textContent+"</pre>")},600)</script></body>')
gd = subprocess.run([CHROME, "--headless=new", *CHROME_EK, "--disable-features=MacAppCodeSignClone", "--disable-gpu", "--allow-file-access-from-files", f"--user-data-dir={T}/p2", "--no-first-run",
                     "--window-size=500,900", "--virtual-time-budget=3000", "--dump-dom", "file://" + sar], capture_output=True, text=True, timeout=60).stdout
m2 = re.search(r'<pre id="gen">(\d+)\|(.*?)</pre>', gd); g2 = (m2.group(2).split("|") if m2 else [])
bak(f"pano headless 420 px: genişlik {m2 and m2.group(1)}, kart/ayrıntı/sarma/şerit {g2}", bool(m2) and int(m2.group(1)) <= 420 and g2[:3] == ["6", "block", "true"] and g2[3] == "3")
# 5 Kasım: cevap/kaynak — doğrulanan soru/sayı/iddia görselde etiket olur; bağlantı yalnız http/https; cevapsız öğe eskisi gibi (kurgu veri)
C = yk([{"tur": "soru", "metin": "Aylık kullanıcı kaç?", "kim": "Can Er", "cevap": "Doğru: 12 bin", "kaynak": "Örnek Metrik · get_metrics · Ekim 2026", "kaynak_url": "https://ornek.example/r?a=1&b=2"},
        {"tur": "iddia", "metin": "Oran yüzde 40", "cevap": "Yanlış, yüzde 35", "kaynak": "döküm 23:12", "kaynak_url": "javascript:alert(1)"},
        {"tur": "sayi", "metin": "3 ekip", "cevap": "Kısmen — 2 ekip", "kaynak": "proje belgesi: plan.pdf"}, {"tur": "soru", "metin": "Cevapsız soru"},
        {"tur": "karar", "metin": "K", "cevap": "karar öğesinde yok sayılır", "kim": "Can Er"}])
cv = sorted([a for g in YP.harita_veri(C)["alt"][0]["alt"] for a in g["alt"]], key=lambda x: x["ad"])  # ada göre: 3 ekip, Aylık…, Cevapsız, K, Oran
bak("cevap alanları: durum sınıfı, bağlantı süzgeci (javascript: düşer), cevapsız/karar öğesinde yok", (lambda b: b["3 ekip"]["cd"] == "kismen" and b["Aylık kullanıcı kaç?"]["cd"] == "dogru" and b["Oran yüzde 40"]["cd"] == "yanlis" and b["Aylık kullanıcı kaç?"]["kaynak_url"].startswith("https://")
    and b["Oran yüzde 40"]["kaynak_url"] == "" and "cevap" not in b["Cevapsız soru"] and "cevap" not in b["K"])({x["ad"]: x for x in cv}))
pc = YP.pano_veri(C)
bak("pano verisi: sorular ve diğerleri cevap taşır, kararda yok", pc["sorular"][0]["cd"] == "dogru" and pc["diger"][0]["cd"] == "yanlis" and "cevap" not in pc["sorular"][1] and "cevap" not in pc["kararlar"][0])
HC, PC = YP.harita_html(C), YP.pano_html(C)
tc_ = os.path.join(T, "cv-harita.html"); open(tc_, "w", encoding="utf-8").write(HC.replace("</script></html>", ";setTimeout(()=>{let n=null;"
    "document.querySelectorAll('.d').forEach(g=>{if(g.textContent.includes('Aylık'))n=g});n&&n.dispatchEvent(new MouseEvent('click'));document.body.insertAdjacentHTML('beforeend','<pre id=sonuc>'+document.querySelectorAll('tspan.cv').length+'|'+document.querySelectorAll('tspan.kn').length+'|'"
    "+(document.querySelector('#ayrinti a')?document.querySelector('#ayrinti a').getAttribute('href'):'-')+'|'+document.documentElement.scrollWidth+'</pre>')},300)</script></html>"))
tp_ = os.path.join(T, "cv-pano.html"); open(tp_, "w", encoding="utf-8").write(PC.replace("</script></html>", ";setTimeout(()=>{const a=[...document.querySelectorAll('.kart')].find(x=>x.textContent.includes('Aylık'));a.click();"
    "const b=[...document.querySelectorAll('.kart')].find(x=>x.textContent.includes('Oran'));const l1=document.querySelector('#ayrinti a');b.click();const l2=document.querySelector('#ayrinti a');"
    "document.body.insertAdjacentHTML('beforeend','<pre id=sonuc>'+document.querySelectorAll('.kart .cv').length+'|'+document.querySelectorAll('.kart .cv .et.dogru,.kart .cv .et.yanlis,.kart .cv .et.kismen').length+'|'+(l1?l1.getAttribute('href'):'-')+'|'+(l2?'link':'-')+'|'+(document.documentElement.scrollWidth<=innerWidth)+'</pre>')},300)</script></html>"))
def dom(yol, w=420):
    return subprocess.run([CHROME, "--headless=new", *CHROME_EK, "--disable-features=MacAppCodeSignClone", "--disable-gpu", "--allow-file-access-from-files", f"--user-data-dir={T}/p3", "--no-first-run",
                           f"--window-size={w},900", "--virtual-time-budget=3000", "--dump-dom", "file://" + yol], capture_output=True, text=True, timeout=60).stdout
import html as _h
mh = re.search(r'<pre id="sonuc">(.*?)</pre>', dom(tc_)); mp = re.search(r'<pre id="sonuc">(.*?)</pre>', dom(tp_))
mh = mh and _h.unescape(mh.group(1)); mp = mp and _h.unescape(mp.group(1))
bak(f"harita headless: cevap/kaynak satırları, ayrıntıda tıklanabilir bağlantı ({mh})", bool(mh) and mh.split("|")[:3] == ["3", "3", "https://ornek.example/r?a=1&b=2"])
bak(f"pano headless 420 px: 3 cevap etiketi, bağlantı yalnız http(s) ({mp})", bool(mp) and mp.split("|")[:5] == ["3", "3", "https://ornek.example/r?a=1&b=2", "-", "true"])
# özet ↔ yapı sayı denetimi (yalnız uyarır)
SV = yk([{"tur": "karar", "metin": "K", "kim": "Can Er"}, {"tur": "is", "metin": "a", "sahip": "Can Er"}, {"tur": "soru", "metin": "Q?"}])
bak("sayı denetimi: tutarsa sessiz; eksik/fazla açık uyarı", YP.sayi_denetim(SV, {"karar": 1, "is": 1, "acik": 1}) == [] and YP.sayi_denetim(SV, {}) == []
    and len(YP.sayi_denetim(SV, {"karar": 1, "is": 1, "acik": 5})) == 1 and "özette 5, yapı dosyasında 1" in YP.sayi_denetim(SV, {"acik": 5})[0] and "eksik" in YP.sayi_denetim(SV, {"acik": 5})[0]
    and "fazla" in YP.sayi_denetim(SV, {"karar": 0})[0])
sy = os.path.join(T, "sd.yapi.json"); json.dump(SV, open(sy, "w"), ensure_ascii=False); so = os.path.join(T, "sd-toplanti-ozeti-20261011.md")
open(so, "w").write("# Özet\n\n## Toplantı çıktısı\n- **Kararlar (1):** K\n- **Sahipli işler (1):** Can — a\n- **Açık kalanlar (5):** a; b; c; d; e\n- **Öneri:** x\n")
u = tc("yapi", sy, "--ozet", so).stdout; _m = open(so).read(); open(so, "w").write(_m.replace("(5)", "(1)")); u2 = tc("yapi", sy, "--ozet", so).stdout
bak("yapi komutu: sayı uyuşmazlığında UYARI, tutunca onay satırı; görsel türü yazılır", "UYARI: özet ile yapı" in u and "Açık kalanlar: özette 5" in u and "tutuyor" in u2 and "UYARI" not in u2 and "tür: karar ve iş panosu" in u)
# aktarıcı: ozet-hazir haritayı kopyalar, pano düğmesi açar
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"))
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(0.5); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    o = tc("ozet-hazir", ozet, "--baslik", "Ayşe — bütçe")
    bak("ozet-hazir: zihin haritası gitti", "zihin haritası" in o.stdout)
    bak("ozet-hazir: toplantı çıktısı okundu (1 karar, 2 iş, 0 açık)", "1 karar, 2 iş, 0 açık" in o.stdout and "öneri var" in o.stdout)
    st = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    son = (st.get("son_toplantilar") or [{}])[0]
    bak("panoda tür: zihin haritası (menü etiketi)", son.get("gorsel") == "harita")
    # 6 Kasım: aynı özetle ozet-hazir yeniden çalışınca (bitir tekrarı) ikinci kayıt, bildirim ve sesli okuma olmaz
    t0 = time.time(); o_b = tc("ozet-hazir", ozet, "--baslik", "Ayşe — bütçe"); time.sleep(0.7)
    lg = open(os.path.join(T, "relay.log"), encoding="utf-8", errors="replace").read()
    st_b = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    bak("ozet-hazir ikinci çağrı zararsız: tek kayıt, tek bildirim, 'zaten kayıtlı'", o_b.returncode == 0 and len(st_b.get("son_toplantilar") or []) == 1 and lg.count("ÖZET: hazır") == 1 and "aynı özet zaten kayıtlı" in lg and (st_b["son_toplantilar"][0].get("id") == son.get("id")))
    bak("panoda kayıtta harita, kopya aktarıcının klasöründe", son.get("harita", "").startswith(os.path.join(canli, "ozetler")) and os.path.exists(son.get("harita", "")))
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}/son-ac", data=json.dumps({"id": son.get("id"), "tur": "harita"}).encode(),
                               headers={"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{PORT}"})
    a = json.loads(urllib.request.urlopen(q, timeout=10).read()); time.sleep(0.3)
    # bitir: yapı → graf + harita → ozet-hazir (sayılar yapıdan) → eylem kuyruğu
    oz2 = os.path.join(T, "bora-toplanti-ozeti-20261012.md"); open(oz2, "w").write("# Özet\n\n## Toplantı çıktısı\n- **Kararlar (9):** metindeki sayı kullanılmamalı\n")
    tc("eylem", "ekle", "takip", "Bora — takip e-postası", "--ayrinti", "Kime: Bora Kaya (adres yok)", "--kim", "Bora Kaya")
    b = tc("bitir", oz2, "--yapi", yj, "--baslik", "Bora — teklif")
    bo = b.stdout + b.stderr
    bak("bitir: graf, harita, eksik uyarısı, sayılar yapıdan (1 karar, 2 iş, 1 açık), kuyruk onaya", "karar grafı:" in bo and "zihin haritası" in bo and "eksik:" in bo
        and "tarih yok" in bo and "1 karar, 2 iş, 1 açık" in bo and "onaya sunuldu" in bo)
    bak("bitir: yapı dosyası aktarıcıya gitti (defter turu: ozetler/ kopyası)", os.path.exists(os.path.join(canli, "ozetler", os.path.basename(oz2)[:-3] + ".yapi.json")))
    bak("bitir: Gerçekten anlaştınız mı? — örtük ve varsayımlı karar sorulur", "ANLAŞMA: 1 karar teyit istiyor" in bo and "örtük kabul" in bo and "varsayım: Kur yıl sonuna" in bo)
    bak("grafta karar 'teyit bekliyor' işaretiyle (hazırlıkta görünür)", "teyit bekliyor" in tc("graf", "--kim", "Ayşe").stdout)
    bak("bitir: öneri yapı dosyasından", "Gündemi bir gün önce gönder" in json.dumps(json.loads(urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read()).get("son_toplantilar"), ensure_ascii=False))
    bak("eylem kuyruğunun takip işi grafta açık iş (sahibi kullanıcı)", re.search(r"\[acik\] [^:]+: Bora — takip e-postası", tc("soz", "liste").stdout) is not None)
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/eylem-karar", data=json.dumps({"id": "hepsi", "durum": "reddedildi"}).encode(),
                           headers={"X-Suflor-Anahtar": K, "Origin": f"http://127.0.0.1:{PORT}"}), timeout=10)  # panodan Reddet: eylem komutu çalışmıyor
    bak("panoda reddedilince (eylem komutu olmadan) grafta iptal", "Bora — takip e-postası" not in tc("soz", "liste").stdout
        and re.search(r"\[iptal\] [^:]+: Bora — takip e-postası", tc("soz", "liste", "--hepsi").stdout) is not None)
    yk2 = os.path.join(T, "can-toplanti-ozeti-20261013.yapi.json"); json.dump(K2, open(yk2, "w"), ensure_ascii=False); oz3 = yk2[:-10] + ".md"
    open(oz3, "w").write("# Özet\n"); b3 = tc("bitir", oz3, "--baslik", "Can — karar")
    st3 = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    s3 = (st3.get("son_toplantilar") or [{}])[0]; h3 = open(oz3[:-3] + "-zihin-haritasi.html", encoding="utf-8").read()
    bak("bitir 2 karar: aynı adla karar ve iş panosu, aktarıcıda tür karar_is", "karar ve iş panosu" in b3.stdout and "— karar ve iş panosu</title>" in h3
        and s3.get("gorsel") == "karar_is" and os.path.exists(s3.get("harita", "")))
    pn = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read()
    bak("panoda menü etiketi türe göre", "r.gorsel==='karar_is'?L('Karar ve iş panosu'):L('Zihin haritası')" in pn)
    nb = tc("bitir", os.path.join(T, "yok.md"))
    bak("bitir: özet yoksa açık hata", nb.returncode != 0 and "özet .md bulunamadı" in nb.stderr)
    bak("Zihin haritası düğmesi açar (deneme)", a.get("ok") and "AÇ (deneme): harita" in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
finally: r.terminate(); r.wait(5)
if not hata: shutil.rmtree(T, ignore_errors=True)
else: print(f"(deneme klasörü: {T})")
print("yapı: ✓ hepsi geçti" if not hata else f"yapı: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
