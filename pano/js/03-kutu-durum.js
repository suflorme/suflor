// tek kutu, tek düğme — yazılan her şey asistana gider (not mu soru mu talimat mı ayrımını asistan yapar; ⌘Enter ve başta ? doğrudan soru); asistan çalışamazsa yazı Notlara kalır.
// Gönderince düğmede kısa onay: "✓ not" / "✓ soru".
function wireBox(ta){
  const go=async soru=>{const t=ta.value;if(!t.trim())return;ta.value="";boyla(ta);const pn=ta.id==="n"&&!toplantidaMi(last)?shGonder(t):null,r=await sendGirdi(t,soru)
    if(ta.id==="n")shGonderSonuc(pn,t,r.tur==="asistan"&&!!r.ok);if(r.tur==="oturum")r.tur="{asistan} aldı";if(r.tur==="asistan")r.tur=r.ok?"{asistan} cevaplıyor":"";if(r.tur==="not"&&r.yedek)r.tur="Asistan meşgul; Notlara yazıldı";if(r.tur==="defter")r.tur=r.yedek?"Asistan meşgul; Notlara yazıldı":"Notlara yazıldı"
    if(!r.tur)ta.value=t;kutuIpucu(r.tur?"✓ "+L(r.tur):L("gönderilemedi"));refresh()}
  ta.__gonder=go
  ta.onkeydown=ev=>{if(ev.key==="Enter"&&!ev.shiftKey&&!ev.isComposing){ev.preventDefault();go(ev.metaKey||ev.ctrlKey)}}
  ta.addEventListener("input",()=>boyla(ta))
}
function boyla(ta){ta.style.height="auto";ta.style.height=Math.min(ta.scrollHeight,160)+"px"}
bindAck(document.getElementById("kc")); bindSoyle(document); bindOtonom(document); bindMod(document)
const PL={teams:"Teams",meet:"Google Meet",zoom:"Zoom"}, ROL={yurutucu:L("yürütücü"),katilimci:L("katılımcı"),dinleyici:L("dinleyici")}
// tek durum cümlesi — beş bağlantı noktası ve uyarı şeridinin yerine. En önemli sorun gösterilir (kırmızı > turuncu); diğerleri
// başlıkta (title). Sorun yoksa: toplantıda "Dinliyorum" (yeşil), değilse gri. Eylem yalnız panonun yapabildiği işte (Başlat).
// masaüstü toplantı (v0.31.0): menü uygulaması Teams/Zoom masaüstünde toplantıda olduğunu son 30 sn'de bildirdi
function masaustuTop(s){const m=s.masaustu;return!!(m&&m.toplantida&&Date.now()/1000-m.t<30)}
function durum(s){
  const x=s.extension, w=s.whisper||{}, ek=x&&x.age_s<30, top=!!s.aktif, mt=top&&masaustuTop(s)&&!(ek&&x.call), cagri=top&&ek&&x.call, ca=s.claude_age_s, izl=ca!=null&&ca<120, so=[]
  try{const g=JSON.parse(sessionStorage.getItem("guncellendi")||"null");if(g&&Date.now()-g.t<90000)so.push(["wa",L("Suflor.me güncellendi"),L("açık bir toplantı sekmesi varsa yenile")])}catch(e){}
  if(s.uyari)so.push(["er",s.uyari,""])
  if(s.anlik)so.push([s.anlik.tur==="uzun"?"er":"wa",s.anlik.metin,s.anlik.ayrinti||""])  // adın geçti (20 sn) / uzun konuşma (kırmızı, 45 sn; aktarici/anlik.py)
  if(s.anahtarsiz)so.push(["wa",L(s.anahtarsiz.tur==="yerel"?"Anahtarsız yerel istek geldi":"Eklenti eski sürümde"),L(s.anahtarsiz.tur==="yerel"?"toplantı yardımcısı eski olabilir — aktarici-kur ile yeniden kur":"chrome://extensions → Suflor.me → ↻ yenile")])
  if(s.dil&&s.dil.uyari)so.push(["er",L("Döküm dili yanlış"),s.dil.uyari])
  if(s.kaynak&&s.kaynak.duzey==="kritik")so.push(["wa",L("Mac aşırı yüklü — Suflor hafif kipte"),L("boş bellek %{b} · takas {t} GB · yük {y} — toplantı işleri sürer, önceden yapılan işler beklemede",{b:s.kaynak.bos_yuzde==null?"?":s.kaynak.bos_yuzde,t:s.kaynak.takas_gb==null?"?":s.kaynak.takas_gb,y:s.kaynak.yuk==null?"?":s.kaynak.yuk})])  // C fazı: kaynak bekçisi (aktarici/kaynak.py), kritik düzey kalıcı sarı kart
  if(s.kulaklik_yok)so.push(["wa",L("Kulaklık algılanmadı — cevaplar yalnız yazılı"),L("çıkış aygıtı")+": "+s.kulaklik_yok.cihaz])  // toplantı sürerken kulaklık yok: sesli cevap, fısıltı ve sesli çeviri kapalı (aktarici/brifing-ses.py kulaklik_yok_view)
  const bk=s.ben_kopuk  // v0.255.1 (beta #89/#90): toplantı tarayıcıda sürerken mikrofon kanalı 2 dk'dır bağlı değil (aktarici/saglik.py ben_kopuk); kanal düzelince kalkar
  if(bk&&top)so.push(["er",bk.neden==="tarayici"?L("Mikrofonun yazılmıyor — toplantı {u} tarayıcısında açık",{u:bk.uygulama}):L("Mikrofonun yazılmıyor"),
    bk.neden==="tarayici"?L("eklenti orada yok — Chrome'dan katıl"):bk.neden==="sorun"?L("mikrofon açık ama ses gelmiyor — toplantı sekmesini yenile"):bk.neden==="hata"?L("mikrofon açılamadı — toplantı sekmesini yenile"):L("eklenti toplantı sekmesine ulaşamıyor — sekmeyi yenile")])
  if(s.veri_yok){const v=s.veri_yok,k=v.kanallar||{}  // Faz D: toplantı sürüyor ama hiçbir kanaldan satır yok — sağlık "süreç çalışıyor" değil "veri akıyor mu"
    const A={acik:L("açık"),yok:L("yok")},B={yok:L("mikrofon bilgisi yok"),hata:L("mikrofon açılamadı"),kapali:L("mikrofon kanalı kapalı"),sessiz:L("mikrofon sessizde"),sorun:L("mikrofon açık ama ses gelmiyor")}
    const C={izin:L("ses kaydı izni yok"),yok:L("ses yardımcısı yok"),kapali:L("ses yardımcısı kapalı"),bekliyor:L("ses yardımcısı hazır, ses gelmiyor"),dinliyor:L("ses yardımcısı dinliyor, satır yok"),web:L("tarayıcı sesi, satır yok")}
    so.push(["wa",L("Toplantı sürüyor ama {n} sn'dir döküm gelmiyor",{n:v.sn}),L("altyazı")+": "+(A[k.altyazi]||k.altyazi)+" · "+L("ben")+": "+(B[k.ben]||k.ben)+" · "+L("karşı taraf")+": "+(C[k.karsi]||k.karsi)])}
  if(mt){  // masaüstü: altyazı yok, satırlar Whisper'dan (karşı: ses yardımcısı, sen: menü uygulamasının mikrofonu)
    const mm=s.masaustu_mic||{}
    if(!w.durum||w.durum==="yok")so.push(["wa",L("Satır gelmiyor"),L("masaüstü toplantıda döküm Whisper'la yazılır — Whisper kurulu değil")])
    else{
      if(w.yerel==="izin")so.push(["wa",L("Karşı tarafın sesi için izin gerekiyor"),L("Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı → Suflor Ses")])
      else if(!w.karsi&&!["bekliyor","dinliyor"].includes(w.yerel))so.push(["wa",L("Karşı tarafın sesi yazılmıyor"),L("ses yardımcısı kapalı — aktarici-kur ile yeniden kur")])
      if(!mm.akiyor&&s.masaustu.sessiz!==true)so.push(["wa",L("Senin sesin yazılmıyor"),L("Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon → Suflor.me")])}
    if(!izl)so.push(["wa",L("{asistan} izlemiyor — kart gelmez"),"",L("Başlat")])}
  else if(cagri){
    const yon=(x.yonerge&&x.yonerge.altyazi)||L("Diğer → Dil ve konuşma → Canlı altyazı")
    if(!(x.panel||x.captions||w.ben||w.karsi))so.push(["wa",L("Satır gelmiyor"),L("altyazıyı aç: ")+yon])
    else if(w.durum&&w.durum!=="yok"){
      if(w.yerel==="izin")so.push(["wa",L("Karşı tarafın sesi için izin gerekiyor"),L("Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı → Suflor Ses")])
      else if(!w.karsi&&!x.captions&&!x.panel&&!["bekliyor","dinliyor"].includes(w.yerel))so.push(["wa",L("Karşı tarafın sesi yazılmıyor"),L("Suflor.me simgesi → Karşı taraf → Aç")])
      if(!w.ben&&!bk&&["hata","sorun"].includes(w.ben_kod))so.push(["wa",L("Senin sesin yazılmıyor"),w.ben_kod==="hata"?L("mikrofon açılamadı — toplantı sekmesini yenile"):L("mikrofon açık ama ses gelmiyor")])}
    if(!izl)so.push(["wa",L("{asistan} izlemiyor — kart gelmez"),"",L("Başlat")])}
  else if(top&&s.toplanti&&s.toplanti.durum==="suruyor"&&!izl&&!(s.toplanti.neden||"").includes("öneri"))so.push(["wa",L("{asistan} izlemiyor — kart gelmez"),"",L("Başlat")])  // Faz B: eklenti yok (S165): ses + takvim; eklentinin yokluğu uyarı değil
  if(top&&s.toplanti&&s.toplanti.mic_bilinmiyor)so.push(["wa",L("Eklenti çalışmıyor: sessize alman Suflor'a ulaşmıyor"),L("özel bir şey söyleyeceksen gizli kipi aç")])
  if(s.bellek&&s.bellek.uyari)so.push(["wa",s.bellek.uyari,""])
  if(s.proje_erisim&&s.proje_erisim.uyari)so.push(["wa",s.proje_erisim.uyari,s.proje_erisim.yol||""])
  // masaüstü toplantıda mikrofon hoparlörle kullanılıyor: karşı ses mikrofona girer (yankı ayırıcı süzer ama kaçan olur)
  const mm=s.masaustu_mic;if(mm&&mm.akiyor&&mm.kulaklik===false&&mm.yanki_var&&yankiUyarGoster())so.push(["wa",L("Kulaklık önerilir"),L("Hoparlörden çıkan ses mikrofona giriyor; bazı satırlar iki kez yazılabilir. Kulaklık takarsanız düzelir.")])  // 19 Kasım: yalnız bu toplantıda yankı ölçülmüşse ve 7 günde en çok bir kez
  const ilk=so.find(([c])=>c==="er")||so[0]
  if(ilk)return{c:ilk[0],m:ilk[1],a:ilk[2],e:ilk[3]||"",hep:so.map(([,m,a])=>m+(a?" — "+a:"")).join("\n")}
  if(!top&&s.toplanti&&s.toplanti.bitiyor)return{c:"nt yt",m:L("Toplantı bitiyor"),a:(s.toplanti.son||{}).ad||"",e:L("Yeni toplantı")}  // 3 Kasım: bitiyor canlı toplantı gibi durmaz; yeni toplantı hemen başlatılabilir
  return cagri?{c:"ok",m:izl?L("Dinliyorum"):L("Toplantıdasın")}:{c:"nt",m:izl?L("{asistan} hazır — toplantı bekleniyor"):L("Hazır — toplantı bekleniyor")}
}
// kısa süreli durum (güncelleme hatası) — tarayıcı diyaloğu yerine
let gecici=null
function geciciDurum(m,a,ms){gecici={c:"wa",m,a:a||"",t:Date.now()+(ms||6000)};durumCiz()}
function durumCiz(){let d=last?durum(last):{c:"nt",m:L("bağlanıyor…")};if(gecici&&Date.now()<gecici.t)d=gecici;else gecici=null
  const e=document.getElementById('durum');e.className=d.c;e.title=d.hep||"";setH(document.getElementById('dm'),esc(d.m));setH(document.getElementById('da'),esc(d.a||""))
  const b=document.getElementById('de');b.hidden=!d.e;b.textContent=d.e||""
  const t=document.getElementById('tbit');t.hidden=!(last&&last.aktif);if(t.hidden&&t.dataset.emin){t.dataset.emin="";t.textContent=L("Bitir")}}
// 13 Kasım: canlı toplantıyı panodan bitir (POST /toplanti bitir — sesli "toplantıyı bitir" ile aynı işlev). İki adımlı: ilk basış "Emin misin?", 4 sn içinde ikinci basış bitirir
document.getElementById('tbit').onclick=async ev=>{const b=ev.currentTarget
  if(!b.dataset.emin){b.dataset.emin="1";b.textContent=L("Emin misin? Bitir");setTimeout(()=>{if(b.dataset.emin){b.dataset.emin="";b.textContent=L("Bitir")}},4000);return}
  b.dataset.emin="";b.disabled=true;b.textContent=L("Bitir");let r={};try{r=await j('/toplanti',{method:'POST',body:JSON.stringify({islem:"bitir"})})}catch(e){}b.disabled=false;if(!r||!r.ok)geciciDurum(L("Toplantı bitirilemedi"),"",6000);refresh()}
document.getElementById('de').onclick=()=>{if(last&&!last.aktif&&last.toplanti&&last.toplanti.bitiyor)return tkForm(null,'');const ag=(last&&last.agenda)||{};tkForm(null,(last&&(ag.title!=="Gündem yok"&&ag.title||last.meeting))||"")}
const MINI_CSS=`.sdi{display:inline-flex;align-items:center;gap:var(--bo-4);vertical-align:-2px}.sdi svg.i{width:13px;height:13px}.oto{display:flex;gap:var(--bo-8);align-items:center;justify-content:space-between;font-size:var(--yz-12);font-weight:500;border:1px solid var(--bd);padding:var(--bo-4) var(--bo-12);margin:var(--bo-4) 0 var(--bo-4);background:var(--s1);border-radius:var(--kose)}.oto .ota{display:flex;gap:var(--bo-4);flex:none}.oto-soylenmedi[role=alert]{border-color:var(--ac)}.oto .pri.on{color:var(--ac-yazi);padding:var(--bo-4) var(--bo-12)}.oto .sdi svg.i{color:var(--ac)}.oto-okunuyor{border-color:var(--ac)}.oto-iptal,.oto-soylenmedi,.oto-okunamadi,.oto-kesildi{color:var(--t2);font-weight:400}.oto-iptal .sdi svg.i,.oto-soylenmedi .sdi svg.i,.oto-okunamadi .sdi svg.i,.oto-kesildi .sdi svg.i{color:var(--t3)}body{display:flex;flex-direction:column;height:100vh;padding:var(--bo-12);gap:var(--bo-8);background:var(--s2)}#mh{font-size:var(--yz-12);color:var(--t2);display:flex;flex-wrap:wrap;gap:var(--bo-8);align-items:center}#mh .w{color:var(--wa);font-weight:600;width:100%}#mc{flex:1;overflow:auto}#ml{font-size:var(--yz-12);color:var(--t3);border-top:1px solid var(--bd);padding-top:var(--bo-4);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}#ml.eski{color:var(--wa)}.mk{flex:none;max-height:42vh;overflow:auto;padding:var(--bo-4) 0;font-size:var(--yz-13)}.mk .d,.mk .meta,.mk summary{font-size:var(--yz-12);color:var(--t3)}.mk .b{margin-top:var(--bo-4)}.mcv{flex:none;max-height:42vh;overflow:auto;padding:var(--bo-4) var(--bo-4)}.mcv.acik{max-height:62vh}.mcv .ca{font-size:var(--yz-12);font-weight:500;color:var(--t3)}.tbr{margin:0}.kt{margin:0}.hat .sh{display:flex;justify-content:space-between;gap:var(--bo-8);font-weight:600}`
function miniCss(){return [...document.styleSheets[0].cssRules].map(r=>r.cssText).join("").replace(/url\("?\/marka\//g,'url("'+location.origin+'/marka/')+MINI_CSS}  // PiP penceresinin adresi yok: yazı tipi yolu tam olmalı
// v0.114.0: tema ayarı (sistem | acik | koyu) — pano, Ayarlar ve Yardım (data-theme; renk.css ve html.mac kuralları tanır), mini pano (PiP ve menü paneli; koyu
// tabanlı, açıkta data-theme=light). Mac uygulamasına bildirilir: pencere çerçeveleri ve menü paneli aynı görünüme geçer.
let TEMA='sistem';const TEMA_MQ='(prefers-color-scheme: dark)'
function temaUygula(t){if(t&&['sistem','acik','koyu'].includes(t)&&t!==TEMA){TEMA=t;try{webkit.messageHandlers.suflor.postMessage({tema:t})}catch(e){}}
  const h=document.documentElement;if(TEMA==='sistem')delete h.dataset.theme;else h.dataset.theme=TEMA==='koyu'?'dark':'light'
  try{if(mini&&!mini.closed&&mini.document){const m=mini.document.documentElement,koyu=TEMA==='koyu'||(TEMA!=='acik'&&matchMedia(TEMA_MQ).matches);if(koyu)delete m.dataset.theme;else m.dataset.theme='light'}}catch(e){}}
function buildMini(w){
  mini=w; const d=w.document; d.title="Suflor.me mini"; d.head.querySelectorAll("style").forEach(x=>x.remove()); const st=d.createElement("style"); st.textContent=miniCss()+":root[data-theme=light]{color-scheme:light}"; d.head.appendChild(st)
  // tema panodan (menü paneli iframe'i)
  const mq="(prefers-color-scheme: dark)",tk=()=>{if(mini===w)temaUygula()};tk();matchMedia(mq).addEventListener("change",tk)
  d.body.innerHTML=`<div id=mh></div><div id=mhat class="mk hat" hidden></div><div id=mto class=mk hidden></div><div id=mc></div><div id=ml></div><div id=mk class=mcv hidden></div><div id=mtbr class=tbr hidden><button id=moz class=ib title="${L("Ne diyeyim? · Option + Shift + O")}">${ic('replik')}</button><button id=mkz class=ib title="${L("Kanıt · Option + Shift + K")}">${ic('cam')}</button><button id=msz class=ib title="${L("Sessiz · Option + Shift + M")}">${ic('mute')}</button><details class=dm><summary class=ib title="${L("Diğer")}" aria-label="${L("Diğer")}">${ic('dahasi')}</summary><div class=dmk><button id=myz class=ib title="${L("Önemli an: şu anı özette öne çıkar")}">${ic('star')}</button><button id=mgz class=ib title="${L("Gizli toplantı: tekrar basana kadar Suflor tamamen kapalı — ses, Whisper, döküm, kanıt yok; yapay zekâ servislerine hiçbir şey gitmez")}">${ic('kilit')}</button><button id=msc class=ib title="${L("Sesli çeviri: karşı tarafın yabancı dildeki sözünün kısa özü kulaklığına okunur (yalnız kulaklık takılıyken; tekrar basınca kapanır)")}">${ic('kulak')}</button></div></details></div><div class=kt><button id=mek class="ib kte" title="${L("Belge ekle")}" aria-label="${L("Belge ekle")}">${ic('arti')}</button><input type=file id=mekd multiple hidden><textarea id=mn rows=1 placeholder="${esc(yazIpucu())}"></textarea><span id=mkdz class=kdz aria-hidden=true><i></i><i></i><i></i><i></i><i></i></span><button id=mksb class="ib ksb" type=button aria-pressed=false title="${L("Cevapları sesli oku")}" aria-label="${L("Cevapları sesli oku")}">${ic(kutuSesliAcik()?"hoparlor":"hoparlorx")}</button><button id=mkb class="ib ktm" title="${L("Basılı tut: sesle sor · iki kez dokun: sohbet (Option + Shift + Boşluk)")}" aria-label="${L("Mikrofon")}">${ic('mic')}</button></div><div id=mkal class=kal></div>`
  cubukAdlari(d); bindAck(d.getElementById("mc")); bindSoyle(d); bindOtonom(d); bindMod(d); wireBox(d.getElementById("mn"));kutuBagla(d,"m"); tosSecBagla(d); susBagla(d); d.getElementById("moz").onclick=ev=>sendOzet(ev.currentTarget); d.getElementById("myz").onclick=ev=>sendOnemli(ev.currentTarget); d.getElementById("msz").onclick=ev=>sendSessiz(ev.currentTarget); d.getElementById("mgz").onclick=ev=>sendGizli(ev.currentTarget); d.getElementById("msc").onclick=ev=>sendSesliCeviri(ev.currentTarget); d.getElementById("mkz").onclick=ev=>sendKanit(ev.currentTarget,d.getElementById("mn"))
  d.addEventListener('keydown',e=>{if(e.code==='Space'&&e.altKey&&e.shiftKey&&!d.getElementById('mkb').hidden){e.preventDefault();if(!e.repeat)konusBasla()}});d.addEventListener('keyup',e=>{if(kRec&&(e.code==='Space'||e.key==='Alt'||e.key==='Shift')){e.preventDefault();konusBitir()}})
  w.addEventListener("pagehide",()=>{if(mini===w)mini=null}); birakmaKur(w); ipucuKur(d); if(last)paintMini(last)
}
// v0.118.0: menü paneli — cevap kutunun üstünde (panodakiyle aynı görünüm); dokununca yerinde açılır; toplantı simgeleri yalnız toplantıda
function miniKonus(d,s){const kb=d.getElementById("mkb"),mk=d.getElementById("mk");if(!kb||!mk)return
  const k=s.konus||{};kb.hidden=!!s.aktif&&!k.toplanti;const ks=d.getElementById('mksb');if(ks)ks.hidden=kb.hidden;mikCiz(kb,s);const g=konusGorunum(s,true)
  mk.hidden=!g;if(mk.querySelector('.kcv'))mk.__kt=mk.scrollTop;if(g&&mk.dataset.h!==g){mk.dataset.h=g;setH(mk,g)}if(g)kcKonum(mk,mk);const tb=d.getElementById("mtbr");if(tb)tb.hidden=!toplantidaMi(s)}
function miniBos(){bnYukle()  // menü paneli (?gorunum=panel) Bugün'ü çizmediği için takvim burada da yoklanır (60 sn'de bir)
  const bug=new Date(),g=bnTarih(),dk=bug.getHours()*60+bug.getMinutes(),n=(bnOlay||[]).find(o=>bnDk(o.saat)>dk)||bnSonraki
  if(n&&n.saat){const ne=[n.tarih&&n.tarih!==g?goreliTarih(n.tarih):'',n.saat,n.baslik||''].filter(Boolean).join(' ');return L('Toplantı yok · sıradaki: {t}',{t:ne})}return L('Hazır')}
function paintMini(s){
  if(!mini||mini.closed)return; const d=mini.document, mc=d.getElementById("mc"); if(!mc)return
  // Süre sayacı yalnız toplantı sürerken: /status sure son toplantıdan kalan agenda.json'dan gelir ve toplantı bittikten sonra "107 dk aşıldı" gibi bayat süre gösteriyordu. Toplantı yokken boş hâl: sıradaki toplantı ya da Hazır.
  const du=durum(s), top=toplantidaMi(s), [sk,sc]=top?sureTxt(s):["",""], bosH=top?"":miniBos()
  setH(d.getElementById("mh"),(du.c==="wa"||du.c==="er"?`<span class=w title="${esc(du.hep)}">${esc(du.m)}${du.a?" — "+esc(du.a):""}</span>`:"")+(sk?`<span style="color:${sc?'var(--wa)':'inherit'}">${esc(sk)}</span>`:"")+(bosH?`<span class=bos>${esc(bosH)}</span>`:"")+(sessizTxt(s)?`<span>${sessizTxt(s)}</span>`:"")+toneHtml(s.tone,s.tone_kisi,true))
  paintCards(mc,s,!s.kart_katmani,!!s.kart_katmani);  // Mac kart katmanı açıkken menü paneli "tüm kartlar" listesidir (yan şeritten açılır): ayrıntı da görünür, metin kesilmez
   sessizCiz(d.getElementById("msz"),s); gizliCiz(d.getElementById("mgz"),s); sesliCiz(d.getElementById("msc"),s); miniKonus(d,s); renderHat(d,s); miniOturum(d,s)
  // Döküm yerine tek satır canlılık (v0.4.3, kullanıcı ✓): metni toplantıda zaten görüyor, burada yalnız akış sürüyor mu
  const le=(s.tail||[]).filter(e=>!e.note&&e.at).slice(-1)[0], ml=d.getElementById("ml")
  if(!top){ml.textContent="";ml.className=""}
  else if(!le){ml.textContent=L("henüz satır yok");ml.className=""}
  else{const a=Math.max(0,Math.round((Date.now()-Date.parse(le.at))/1000));ml.textContent=L("son satır {a} önce · {k}",{a:a<60?L("{n} sn",{n:a}):L("{n} dk",{n:Math.floor(a/60)}),k:le.speaker||"?"});ml.className=a>60?"eski":""}
}
// dosya bırakma → bağlam: panoya ya da mini panoya bırakılan dosya bu Mac'te toplantının bağlam klasörüne yazılır,
// {asistan} okur (izle: BAĞLAM). En çok 25 MB; aktarıcı yalnız pano anahtarıyla kabul eder.
// Ses/video dosyası (m4a, mp4, mov, wav, mp3…) bağlam olmaz: atlanır.
const SES_UZ=/\.(m4a|mp4|mov|m4v|wav|mp3|aac|caf|aif|aiff|3gp)$/i
async function baglamBirak(files){const ses=files.filter(f=>SES_UZ.test(f.name));files=files.filter(f=>!SES_UZ.test(f.name))
  if(ses.length)geciciDurum(L("Ses ve video dosyası bağlam olamaz"),ses[0].name,6000)
  for(const f of files){if(f.size>25*1048576){geciciDurum(L("Dosya çok büyük"),L("en çok 25 MB")+" · "+f.name);continue}
  const veri=await new Promise(r=>{const fr=new FileReader();fr.onload=()=>r(String(fr.result).split(',')[1]||'');fr.onerror=()=>r('');fr.readAsDataURL(f)})
  let r={};try{r=await j('/baglam-dosya',{method:'POST',body:JSON.stringify({ad:f.name,veri})})}catch(e){}
  geciciDurum(r.ok?L("Bağlam eklendi — {asistan} okuyacak"):L("Bağlam eklenemedi"),r.ok?r.ad:(r.err||f.name),4000)}refresh()}
function birakmaKur(w){const b=w.document.body;let n=0
  w.addEventListener('dragenter',ev=>{if([...(ev.dataTransfer&&ev.dataTransfer.types||[])].includes('Files')){n++;b.classList.add('surukle')}})
  w.addEventListener('dragleave',()=>{if(--n<=0){n=0;b.classList.remove('surukle')}})
  w.addEventListener('dragover',ev=>{if([...(ev.dataTransfer&&ev.dataTransfer.types||[])].includes('Files'))ev.preventDefault()})
  w.addEventListener('drop',ev=>{if(!ev.dataTransfer||!ev.dataTransfer.files.length)return;ev.preventDefault();n=0;b.classList.remove('surukle');baglamBirak([...ev.dataTransfer.files])})}
birakmaKur(window)
// ipucu: simgenin üstüne gelince hemen çıkar (tarayıcının kendi ipucu ~1 sn gecikiyor, mini pano penceresinde hiç çıkmayabiliyor).
// title okununca data-ipucu'ya taşınır (çift ipucu olmasın); yalnız simgeli düğmeye aria-label olarak da yazılır (ekran okuyucu).
function ipucuKur(d){const w=d.defaultView;let b=null,hedef=null,t=0
  const gizle=()=>{clearTimeout(t);hedef=null;if(b)b.hidden=true}
  d.addEventListener("mouseover",ev=>{const e=ev.target.closest&&ev.target.closest("[title],[data-ipucu]");if(!e||e===hedef)return
    if(e.hasAttribute("title")){e.dataset.ipucu=e.getAttribute("title");if(!e.hasAttribute("aria-label")&&!e.textContent.trim())e.setAttribute("aria-label",e.dataset.ipucu);e.removeAttribute("title")}
    const m=e.dataset.ipucu;if(!m){gizle();return}hedef=e;clearTimeout(t)
    t=setTimeout(()=>{if(hedef!==e||!e.isConnected)return;if(!b){b=d.createElement("div");b.className="ipucu";b.setAttribute("role","tooltip");d.body.appendChild(b)}
      b.textContent=m;b.hidden=false;const r=e.getBoundingClientRect(),bw=b.offsetWidth,bh=b.offsetHeight
      const y=r.bottom+6+bh>w.innerHeight-6?r.top-bh-6:r.bottom+6
      b.style.left=Math.max(6,Math.min(r.left+r.width/2-bw/2,w.innerWidth-bw-6))+"px";b.style.top=Math.max(6,y)+"px"},250)})
  d.addEventListener("mouseout",ev=>{if(hedef&&!(ev.relatedTarget&&hedef.contains(ev.relatedTarget)))gizle()})
  d.addEventListener("mousedown",gizle,true);w.addEventListener("scroll",gizle,true);w.addEventListener("blur",gizle)}
ipucuKur(document)
let agTotal=0
// geri bildirim — kullanıcının metni + isteğe bağlı teknik paket (aktarıcı süzer; önizleme aynı paketi gösterir)
{const d=document.getElementById("gbd"),m=document.getElementById("gbm"),dd=document.getElementById("gbd2")
 document.getElementById("gb").innerHTML=ic('chat')
 document.getElementById("gb").onclick=async()=>{dd.textContent="";d.showModal();m.focus()}
 document.getElementById("gbs").onclick=async ev=>{ev.preventDefault();const t=m.value.trim();if(!t){dd.textContent=L("Önce ne olduğunu yaz");return}
  dd.textContent=L("gönderiliyor…");let r={};try{r=await j("/geri-bildirim",{method:"POST",body:JSON.stringify({metin:t,teknik:document.getElementById("gbt").checked})})}catch(e){}
  if(r.ok){m.value="";dd.textContent=L("Teşekkürler — gönderildi");setTimeout(()=>d.close(),1400)}else dd.textContent=L("Gönderilemedi — sonra yeniden denenecek")}}
// takvimden sıradaki toplantılar + panodan başlatma (Claude izlemiyorken görünür). Anahtar sunucu tarafından gömülür.
let tkSecili=null, tkOlaylar=[], tkListe=[], tkGor=null  // tkGor: boş panoda gündemi gösterilen toplantı
// boş panoda seçili toplantının gündemi: Claude'un hazırladığı gündem başlığı uyuşuyorsa onun maddeleri, yoksa davet notundaki
// maddeler (ayırıcı çizgiden önceki kısım; bağlantı, parola, kimlik satırları atılır — Teams/Zoom katılım bilgisi gösterilmez)
const tkNot={}; let agTam=null, agTamT=0
function davetMaddeleri(n){const out=[];  // aktarıcıdaki eşi yapi.davet_maddeleri (e-posta işareti, tc hazirlik): kural değişince ikisini birlikte güncelle
for(let l of String(n||'').split(/\r?\n/)){l=l.trim();if(/^_{5,}|^-{5,}|microsoft teams|zoom|google meet|toplantıya katıl|join/i.test(l))break
  if(!l||/^(gündem|agenda|konular|topics)\s*:?$/i.test(l)||/https?:|www\.|passcode|password|parola|şifre|meeting id|kimli[gğ]i|pin\b/i.test(l))continue;out.push(l.replace(/^([-•*·▪◦]|\d+[.)])\s*/,''));if(out.length>=12)break}return out}
async function tkNotAl(id){if(id in tkNot)return;tkNot[id]=null;try{const t=await j('/takvim?tam=1');(t.olaylar||[]).forEach(o=>tkNot[o.id]=o.notlar||'')}catch(e){delete tkNot[id]}}
const norm=t=>String(t||'').toLocaleLowerCase('tr').replace(/[^a-zçğıöşü0-9 ]/g,' ').replace(/\s+/g,' ').trim()
function seciliGundem(ag){const o=tkOlaylar.find(x=>x.id===tkGor);if(!o)return null
  const a=norm(ag&&ag.title),b=norm(o.baslik);if(a&&b&&(a.includes(b)||b.includes(a))&&(ag.items||[]).length)return{o,items:ag.items,kaynak:''}
  if(!(o.id in tkNot)){tkNotAl(o.id);return{o,items:[],kaynak:L('davet notu okunuyor…')}}
  const m=davetMaddeleri(tkNot[o.id]);return{o,items:m,kaynak:m.length?L('davet notundan'):L('Bu toplantı için gündem yok — Başlat\'a basınca {asistan} hazırlar.')}}
// pano Chrome'da değilse (Safari varsayılan) toplantı ve hazırlık sekmesini aktarıcı Chrome'da açar — eklenti yalnız Chrome'da
const CHROME=/Chrome\//.test(navigator.userAgent)&&!/Edg\/|OPR\//.test(navigator.userAgent), chromeAc=b=>j('/ac',{method:'POST',body:JSON.stringify(b)}).catch(()=>{})
async function yerelSayfaAc(u,alan){  // 12 Kasım: Döküm kontrolü / Kesişim sayfasını aç; olmazsa sessiz kalma, nedenini söyle
  if(CHROME){const w=window.open(u,'_blank');if(!w)bnBildir(L('Sayfa açılamadı: tarayıcı yeni sekmeyi engelledi.'));return}
  let r=null;try{r=await j('/ac',{method:'POST',body:JSON.stringify({[alan]:'http://127.0.0.1:'+location.port+u})})}catch(e){}
  if(!r||!r.ok)bnBildir(L('Sayfa Chrome\'da açılamadı. Adresi elle açabilirsin.'))}
// Başlat formunda seçim düğmeleri (kullanıcı, 21 Ekim: açılır menü yerine): .sg grubu tek seçim; data-bos=1 ise seçili düğmeye yeniden basınca seçim kalkar
const sgVal=id=>(document.querySelector('#'+id+' button.on')||{}).dataset?.v||'', sgSet=(id,v)=>document.querySelectorAll('#'+id+' button').forEach(b=>b.classList.toggle('on',b.dataset.v===v))
document.querySelectorAll('.sg').forEach(g=>g.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b)return;sgSet(g.id,g.dataset.bos&&b.classList.contains('on')?'':b.dataset.v)}))
document.addEventListener('keydown',ev=>{const f=document.getElementById('tkf');if(ev.key==='Escape'&&f&&!f.hidden&&!document.querySelector('dialog[open]'))document.getElementById('tki').click()})  // Esc formu kapatır
function tkForm(o,konu){tkSecili=o?o.id:null;const f=document.getElementById('tkf');document.getElementById('tks').hidden=false;f.hidden=false;document.getElementById('tky2').hidden=!(o&&o.baglanti);const tl=document.getElementById('tkl');tl.value='';tl.hidden=!!(o&&o.baglanti);sgSet('tkp',(last&&last.son_platform)||'teams');document.getElementById('tkp').hidden=tl.hidden;document.getElementById('tkc').value='';tkGundemDoldur(o);document.getElementById('tkk').value=o?o.baslik:(konu||'');sgSet('tkr',o&&o.ben_duzenleyen?'yurutucu':(o?'katilimci':'yurutucu'));sgSet('tkd','tr');document.getElementById('tkm').textContent='';document.getElementById('tkk').focus()}
// Gündem alanı: takvim olayının davet notunda madde varsa onlarla dolar (not henüz okunmadıysa okununca; kullanıcı yazmaya başladıysa dokunulmaz)
function tkGundemDoldur(o){const g=document.getElementById('tkg');g.value='';g.dataset.el='';if(!o)return
  let n=0;const yaz=()=>{if(tkSecili!==o.id||g.dataset.el)return;if(typeof tkNot[o.id]==='string')g.value=davetMaddeleri(tkNot[o.id]).join('\n');else if(n++<20)setTimeout(yaz,300)}
  tkNotAl(o.id).then(yaz)}
document.getElementById('tkg').addEventListener('input',e=>e.target.dataset.el='1')
// Elle başlat aç/kapat: form zaten elle açıksa ikinci tıklama kapatır
document.getElementById('tke').onclick=()=>{const f=document.getElementById('tkf');if(!f.hidden&&tkSecili===null){f.hidden=true;if(last)renderTakvim(last)}else tkForm(null)}
document.getElementById('tki').onclick=()=>{document.getElementById('tkf').hidden=true;if(last)renderTakvim(last)}
document.getElementById('tky2').onclick=ev=>{ev.preventDefault();const o=tkBul(tkSecili);if(o&&o.baglanti){if(CHROME)window.open(o.baglanti,'_blank');else chromeAc({olay:o.id})}}
