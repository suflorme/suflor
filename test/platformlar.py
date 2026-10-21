#!/usr/bin/env python3
# Meet ve Zoom web uyarlayıcıları (platform-meet.js, platform-zoom.js; v0.27.0): headless Chrome'da (eklentisiz) sahte toplantı sayfası +
# platform dosyası + çekirdeğin yardımcıları (leaves, capId) — toplantı adı, çağrıda mı, mikrofon sessiz mi, altyazı (konuşmacı + metin), Zoom
# tam döküm paneli. Sahte DOM herkese açık bilgiyle kuruldu: gerçek Meet/Zoom'un doğrulaması değildir, uyarlayıcının mantığını korur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/platformlar.py      (kaldı → çıkış 1)
import json, os, re, subprocess, sys, tempfile, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from gizlichrome import chrome_yolu, CHROME_EK  # Dock'ta görünmeyen kopya
CHROME = chrome_yolu()
YARD = """<script>
function leaves(root){const out=[];const w=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT);let n=root;while(n){if(n.childElementCount===0){const t=(n.innerText||n.textContent||'').trim();if(t)out.push({el:n,t})}n=w.nextNode()}return out}
let capN=0;const ids=new WeakMap();function capId(el,t){if(!ids.has(el))ids.set(el,'cap/'+(++capN));return ids.get(el)}
</script>"""
SAYFA = {
 "meet": ("""<title>Meet - Bütçe görüşmesi</title><div data-meeting-title="Bütçe görüşmesi"></div>
<button aria-label="Mikrofonu aç (⌘ + d)" data-is-muted="true"></button><button aria-label="Görüşmeden ayrıl"></button>
<div role="region" aria-label="Altyazılar"><div><div class="nMcdL"><img><div class="KcIKyf"><span class="NWpY1d">Ayşe Yılmaz</span></div><div class="bh44bd"><span>Bütçeyi gelecek hafta netleştireceğiz.</span></div></div>
<div class="nMcdL"><img><div><span>John Smith</span></div><div><span>We can ship on Monday.</span></div></div></div></div>""",
  """const P=globalThis.SuflorPlatform;P.kur({leaves,capId});const b=P.altyaziKutusu();
R={ad:P.toplantiAdi(),cagri:P.cagrida(),sessiz:P.sessizMi(),panel:P.dokumPaneli(),cc:P.altyaziVar(),satir:P.altyaziOku(b).map(x=>[x.speaker,x.text,!!x.last])}""",
  lambda R: [("toplantı adı", R["ad"] == "Bütçe görüşmesi"), ("çağrıda", R["cagri"]), ("mikrofon sessiz (data-is-muted)", R["sessiz"]), ("döküm paneli yok", R["panel"] is None),
             ("altyazı var", R["cc"]), ("altyazı: sınıf adıyla konuşmacı", R["satir"][:1] == [["Ayşe Yılmaz", "Bütçeyi gelecek hafta netleştireceğiz.", False]]),
             ("altyazı: sınıfsız blokta ilk kısa yaprak ad", R["satir"][1:] == [["John Smith", "We can ship on Monday.", True]])]),
 "zoom": ("""<title>Zoom</title><div class="meeting-info-container__topic">Haftalık durum</div>
<button class="footer__leave-btn" aria-label="Leave"></button><button class="join-audio-container__btn" aria-label="unmute my microphone"></button>
<div class="lt-full-transcript__list"><div class="lt-full-transcript__item"><span class="lt-full-transcript__display-name">Ayşe Yılmaz</span><span class="lt-full-transcript__time">10:02</span><div class="lt-full-transcript__message">Teklif cuma gelir.</div></div>
<div class="lt-full-transcript__item"><div class="lt-full-transcript__message">Sonra da sözleşme.</div></div>
<div class="lt-full-transcript__item"><span class="lt-full-transcript__display-name">John Smith</span><span class="lt-full-transcript__time">10:03</span><div class="lt-full-transcript__message">Sounds good.</div></div></div>
<div id="live-transcription-subtitle"><span class="live-transcription-subtitle__name">John Smith</span><span class="live-transcription-subtitle__item">Sounds good to me.</span></div>""",
  """const P=globalThis.SuflorPlatform;P.kur({leaves,capId});const p=P.dokumPaneli();
R={ad:P.toplantiAdi(),cagri:P.cagrida(),sessiz:P.sessizMi(),n:P.dokumSatirSayisi(p),dokum:P.dokumOku(p).map(x=>[x.speaker,x.time,x.text]),dokum2:P.dokumOku(p).map(x=>x.id),cc:P.altyaziVar(),alt:P.altyaziOku(P.altyaziKutusu()).map(x=>[x.speaker,x.text])}""",
  lambda R: [("toplantı adı", R["ad"] == "Haftalık durum"), ("çağrıda", R["cagri"]), ("mikrofon sessiz (unmute)", R["sessiz"]), ("döküm satır sayısı 3", R["n"] == 3),
             ("döküm: ad ve saat ardışık satıra devralınır", R["dokum"] == [["Ayşe Yılmaz", "10:02", "Teklif cuma gelir."], ["Ayşe Yılmaz", "10:02", "Sonra da sözleşme."], ["John Smith", "10:03", "Sounds good."]]),
             ("döküm kimliği ikinci okumada aynı", len(set(R["dokum2"])) == 3), ("altyazı var", R["cc"]), ("altyazı: ad + metin", R["alt"] == [["John Smith", "Sounds good to me."]])]),
}
hata = []
for ad, (govde, js, denet) in SAYFA.items():
    T = tempfile.mkdtemp(prefix="suflor-pl-"); f = os.path.join(T, "s.html")
    open(f, "w", encoding="utf-8").write(f"<!doctype html><meta charset=utf-8>{govde}{YARD}<script src='file://{KOD}/platform-{ad}.js'></script>"
                                         f"<script>let R;try{{{js}}}catch(e){{R={{hata:String(e)}}}}document.body.insertAdjacentHTML('beforeend','<pre id=sonuc>'+JSON.stringify(R).replace(/</g,'\\\\u003c')+'</pre>')</script>")
    # Chrome (154) --dump-dom çıktısını yazdıktan sonra kapanmıyor: çıktı dosyaya, sonuç görülünce süreç kapatılır
    cik = os.path.join(T, "o.html")
    pr = subprocess.Popen([CHROME, "--headless=new", *CHROME_EK, "--disable-features=MacAppCodeSignClone", "--disable-gpu", "--allow-file-access-from-files", f"--user-data-dir={T}/p", "--no-first-run", "--no-default-browser-check",
                           "--dump-dom", "file://" + f], stdout=open(cik, "w"), stderr=subprocess.DEVNULL)
    m = None
    for _ in range(120):
        time.sleep(0.25); m = re.search(r'<pre id="sonuc">(.*?)</pre>', open(cik, encoding="utf-8", errors="replace").read(), re.S)
        if m or pr.poll() is not None: break
    pr.kill(); pr.wait(5)
    R = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")) if m else {"hata": "sonuç yok"}
    if R.get("hata"): print(f"✗ {ad}: {R['hata']}"); hata.append(ad); continue
    for k, ok in denet(R):
        print(("✓ " if ok else "✗ ") + f"{ad}: {k}")
        if not ok: hata.append(k); print("    ", R)
print("platform: ✓ hepsi geçti" if not hata else f"platform: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
