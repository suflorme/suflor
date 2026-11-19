// --- Claude kartları, soru kutusu, mini pano (v0.4.0) ---
const KL={soyle:L("Söyle"),dur:L("Dur"),cevap:L("Cevap"),not:L("Not")}
// v0.194.0: kart türü simgeyle de ayrılır (renk tek başına anlam taşımasın): söyle balon, dur uyarı, cevap onay, not liste; onay zil, replik Suflor işareti
const KI={soyle:'sohbet',dur:'uyari',cevap:'check',not:'liste',onay:'zil',replik:'replik'}
const TL={olumlu:L("olumlu"),notr:L("nötr"),gergin:L("gergin"),olumsuz:L("olumsuz"),ilgili:L("ilgili"),heyecanli:L("heyecanlı"),tedirgin:L("tedirgin"),savunmada:L("savunmada"),ilgisiz:L("ilgisiz"),kararsiz:L("kararsız")}
// genel ton + kişi başına etiket (metin + ses sinyalleri; Claude tahmini)
// etiket yalnız değişince öne çıkar: ilk 8 sn parlak (2 sn yenilemeyle ~5 sn), sonra panoda soluk, mini panoda gizli
const TAZE_MS=8000, taze=at=>Date.now()-Date.parse(at)<TAZE_MS
function toneHtml(t,k,mini){const one=(ton,at,ad)=>{if(!TL[ton])return"";const tz=taze(at);if(mini&&!tz)return"";return`<span class="tn tn-${ton} ${tz?'taze':'eski'}" title="${L('Tahmin, {t}',{t:esc(at)})}">${ad}: ${TL[ton]}</span>`}
  return (t?one(t.ton,t.at,L('ton')):"")+Object.entries(k||{}).map(([n,v])=>one(v.ton,v.at,esc(n.split(" ")[0]))).join("")}
const seenCards=new Set(); let firstCards=true, last=null, mini=null
// kart metnindeki web bağlantısı tıklanabilir (test toplantısı 7 Ekim 21:09); önce kaçış, sonra yalnız http(s) — sondaki noktalama dışarıda
function bag(h){return h.replace(/https?:\/\/[^\s<>"']+/g,u=>{const m=u.match(/^(.*?)([.,;:!?)]*)$/);return `<a href="${m[1]}" target=_blank rel="noopener noreferrer">${m[1]}</a>${m[2]}`})}
// sohbet paneli açıkken asistanın kayıt onay kartları (izin "kayit") yalnız panelde durur; ana sayfada gizlenir, panel kapanınca yeniden görünür. Toplantı kartları etkilenmez.
// 19 Kasım (K1): kartın toplantı anındaki önceliği, kartları listeleyen her yüzey bunu kullanır (pano, menü paneli; Teams şeridi content.js'te aynısı,
// test/kart-oncelik.py ikisini karşılaştırır). Küçük önce: 0 DUR · 1 karşı tarafın sorusu (süreli onay) · 2 senden şimdi iş bekleyen (onay, Ne diyeyim, Söyle) · 3 Cevap · 4 Not.
function kartOncelik(c){c=c||{};return c.kind==='dur'?0:c.onay&&c.eylem&&c.izin==='karsi_cevap'?1:(c.onay||c.replik||c.kind==='soyle')?2:c.kind==='cevap'?3:4}
// aynı öncelikte en yeni önce (ertelenip geri gelen kart geri geldiği an sayılır); eşitte aktarıcının sırasında sonraki önce
function kartSirala(cs){return (cs||[]).map((c,i)=>[c,i]).sort((a,b)=>kartOncelik(a[0])-kartOncelik(b[0])||String(b[0].geri||b[0].at||'').localeCompare(String(a[0].geri||a[0].at||''))||b[1]-a[1]).map(x=>x[0])}
// panoda en yeni Cevap/Not dışındaki bilgi kartları tek satıra katlanır; dokununca açılır (KAC). Menü panelinde tek kart + "+N kart" sayacı (KDAHA).
const KAC=new Set();let KDAHA=false
function shKartlar(v,mini_){const c=(v&&v.cards)||[];return !mini_&&shAcik?c.filter(x=>!(x.onay&&x.izin==='kayit')):c}
function cardsHtml(v,mini,tum){
  const qs=(v.questions||[]).map(q=>`<div class=kq>${q.tur==="ozet"?L("Ne diyeyim? — replik hazırlanıyor…"):L(q.tur==="girdi"?"İletildi: ":"Soruldu: ")+esc(q.text)}</div>`).join("")
  const kcs=karsiOnayKartlari(v),kcl=kartSirala(shKartlar(v,mini)),ilk=kcl.findIndex(c=>kartOncelik(c)>=3)  // tek öncelik (K1): DUR, karşı tarafın sorusu, senden iş bekleyen, Cevap, Not
  const katli=(c,i)=>!mini&&!tum&&i!==ilk&&kartOncelik(c)>=3&&!KAC.has(c.id)
  const kart=(c,i)=>kcs.has(c.id)?karsiKartHtml(c,v):`<div class="k k-${esc(c.kind)}${c.replik?" k-replik":""}${katli(c,i)?" kkat":""}${(firstCards||seenCards.has(c.id+(c.geri||"")))?"":" yeni"}" data-id="${esc(c.id)}"${c.onay?` data-onay=1`:` title="${katli(c,i)?L('Dokun: aç'):L('Dokun: kapat')}"`}><div class=km><b>${c.geri?`<span title="${L('Sonraya bırakmıştın; şimdi geri geldi')}">↩ </span>`:""}${ic(KI[c.onay?'onay':c.replik?'replik':c.kind]||'liste')}${c.onay?L("Onay bekliyor"):c.replik?L("Ne diyeyim"):KL[c.kind]||KL.not}${c.gizli?" · "+L("gizli"):""}</b>${c.q?`<div class=kw>↳ ${esc(c.q)}</div>`:""}${c.replik?`<span class=rp>${esc(c.text)}</span>`:bag(esc(c.text))}${c.durum?`<div class=kd>${esc(c.durum)}</div>`:""}${ayGor(c.why)&&!mini?`<div class=kw>${bag(esc(ayGor(c.why)))}</div>`:""}</div><div class=ka>${soyleBtn(c.text,true)}${ackBtns(c)}</div></div>`
  // menü paneli (K2): en önemli tek kart + sayaç; öbürleri sayaca dokununca (DOM'da durur)
  const oc=mini&&kcl.length>1?kart(kcl[0],0)+`<button type=button class=kdaha data-kdaha=1 aria-expanded=${KDAHA}>${esc(KDAHA?L("Daha az göster"):L("+{n} kart",{n:kcl.length-1}))}</button><div class="kdhs${KDAHA?" acik":""}">${kcl.slice(1).map((c,i)=>kart(c,i+1)).join("")}</div>`:kcl.map(kart).join("")
  const cc=(v.closed||[]).slice(-3).reverse().map(c=>`<div class=kc title="${esc(c.text)}">${ACK_ICON[c.status]||ic("x")}<span>${esc(c.text)}</span></div>`).join("")
  return ((oc+qs)||`<div class=empty>${L("Şimdilik kart yok. {asistan} toplantıyı izlerken öneriler buraya düşer.")}</div>`)+cc
}
// 3 Kasım: karşı taraf asistana adıyla sorunca cevap okunmadan önce onay kartı (aktarici/otonom.py izin_iste "karsi_cevap"); toplantıda gözden kaçıp 45 sn dolunca cevap okunmuyordu.
// Kart mini panoda ve panoda en üstte, belirgin; Oku / Okuma tek tıkla (kart onayıyla aynı /card-ack), kalan süre geri sayar. Aktarıcı kartın türünü açmaz: onay kartı + otonom itiraz penceresi + «…» metni.
const KO={id:null,son:0}
// aktarıcı izin kartına türünü (izin: karsi_cevap) ve bitiş zamanını (bitis, sn) yazar; onay bekleyen cevap kenara alınmış olsa da kart öne çıkar
function karsiOnayKartlari(v){const r=new Set();for(const c of (v&&v.cards)||[])if(c.onay&&c.eylem&&c.izin==='karsi_cevap'){r.add(c.id);if(c.bitis)KO[c.id]=c.bitis*1000}KO.id=r.size;return r}
const koKalan=id=>KO[id]?Math.max(0,Math.ceil((KO[id]-Date.now())/1000)):null
function karsiKartHtml(c,v){const k=v.konus||{},ad=AG((k.otonom||{}).ad)||asGor(k),n=koKalan(c.id),m=String(c.text||'').replace(/^İzin:\s*|^Permission:\s*/,'')
  return `<div class="k k-karsi" data-id="${esc(c.id)}" data-onay=1 role=alert><div class=km><b>${ic('hoparlor')}${esc(L("Karşı taraf sordu — {ad} okusun mu?",{ad}))} ${n==null?'':`<span class=kgs data-k="${esc(c.id)}">${esc(L("{n} sn",{n}))}</span>`}</b>${bag(esc(m))}<div class=kd>${esc(L("Süre dolunca okunmaz."))} ${esc(L("Sesle: «{ad}, oku»",{ad}))}</div></div><div class="ka kka"><button class="pri on" data-ack=onaylandi data-id="${esc(c.id)}">${esc(L("Oku"))}</button><button class="gh on" data-ack=reddedildi data-id="${esc(c.id)}">${esc(L("Okuma"))}</button></div></div>`}
setInterval(()=>{if(!KO.id)return;for(const d of [document,mini&&!mini.closed&&mini.document])if(d)d.querySelectorAll('.kgs').forEach(e=>{const t=L("{n} sn",{n:koKalan(e.dataset.k)||0});if(e.textContent!==t)e.textContent=t})},1000)
// karta dokunmak = okundu (kapat); ✓ yaptım, ✕ gerek yok ikincil. CEVAP ve NOT'ta "yaptım" anlamsız
const ACK_ICON={yapildi:ic("check"),okundu:ic("eye"),gecildi:ic("x"),yenilendi:ic("yenile"),onaylandi:ic("check"),reddedildi:ic("x")}
const NO_DO=["cevap","not"]
// onay kartı (#76): Claude'un yapacağı iç işi (kayıt, kendi oturumlarına mesaj) yazılı onaylarsın; karta dokunmak onay değil
function ackBtns(c){if(c.onay)return[["onaylandi","check",L("Onayla")],["reddedildi","x",L("Reddet")]].map(([s,i,t])=>`<button class="${s==="onaylandi"?"pri":"gh"} on" data-ack=${s} data-id="${esc(c.id)}" title="${t}">${ic(i,t)}</button>`).join("")
  return [["yapildi","check",L("Yaptım")],["ertele","pause",L("Sonra: gündemde sıradaki maddede (gündem yoksa 5 dk sonra) yeniden göster")],["gecildi","x",L("Gerek yok — bir daha önerilmesin")]].filter(([s])=>s!=="yapildi"||!NO_DO.includes(c.kind)).map(([s,i,t])=>`<button class=gh data-ack=${s} data-id="${esc(c.id)}" title="${t}" aria-label="${t}">${ic(i)}</button>`).join("")}
function paintCards(el,v,mini,tum){setH(el,cardsHtml(v,mini,tum))}
// S94 (19 Ekim): "toplantıya söyle" düğmesi kalktı — toplantıda asistan adıyla seslenince herkese konuşur, düğme gerekmez
const soyleBtn=()=>''
// Asistanın toplantıya cevabı (S94: itiraz penceresi yok): söz sırası → konuşuyor → sonuç; Dur her an
const otonomHtml=k=>{const o=k&&k.otonom;if(!o)return'';const n=o.neden||'',ad=AG(o.ad)||asGor(k),m={itiraz:L('{ad}: söz sırası bekleniyor',{ad}),sira:o.bekliyor>=5?L('{ad}: söz sırası bekleniyor ({n} sn)',{ad,n:o.bekliyor}):L('{ad}: söz sırası bekleniyor',{ad}),okunuyor:L('{ad} konuşuyor',{ad}),okundu:L('{ad} toplantıya konuştu',{ad}),kesildi:L('Okuma durdu — {n}',{n}),soylenmedi:L('Toplantıya söylenmedi — {n}',{n}),okunamadi:L('Toplantıya okunamadı — {n}',{n}),iptal:L('Toplantıya söylenmedi — {n}',{n})}[o.durum]||'',ac=['itiraz','sira','okunuyor'].includes(o.durum)
  return `<div class="oto oto-${esc(o.durum)}"${o.yeniden?' role=alert':''}><span class=sdi>${ic('hoparlor')}<span>${esc(m)}</span></span>${ac?`<span class=ota><button class=gh data-ot=iptal data-oid="${esc(o.id)}">${L('Dur')}</button></span>`:''}${o.yeniden?`<span class=ota><button class="pri on" data-ot=simdi data-oid="${esc(o.id)}">${L('Şimdi oku')}</button></span>`:''}</div>`}
// S94: toplantıda hangi asistanlar dinliyor, hangisi katıldı (adıyla seslenince)
const asistanHtml=k=>{const a=k&&k.asistan;if(!a)return'';if(!a.acik)return`<div class="oto"><span class=sdi>${ic('hoparlor')}<span>${esc(L('Asistanlar toplantıda konuşmuyor (⚙ Ayarlar)'))}</span></span></div>`
  const kat=a.katilan||[],dig=(a.adlar||[]).filter(x=>!kat.includes(x)),p=[];if(kat.length)p.push(L('{adlar} toplantıda',{adlar:kat.join(' · ')}));if(dig.length)p.push(L('{adlar} dinliyor — adıyla seslen',{adlar:dig.join(' · ')}))
  return `<div class="oto oto-asistan"><span class=sdi>${ic('hoparlor')}<span>${esc(p.join(' · '))}</span></span></div>`}
// v0.83.0 moderatör (S93): kişilik toplantıyı yönetirken madde, kalan süre; düğmeler ses komutunun yedeği
const modHtml=k=>{const o=k&&k.moderator;if(!o||!o.acik)return'';const dk=o.kalan_sn!=null?Math.max(0,Math.ceil(o.kalan_sn/60)):null
  const ne=o.madde?L('Madde {i}/{n}: {m}',{i:o.sira,n:o.toplam,m:o.madde})+(dk!=null?' · '+L('{d} dk kaldı',{d:dk}):''):L('Gündem bekleniyor')
  return `<div class="oto oto-mod"><span class=sdi>${ic('hoparlor')}<span>${esc(L('{ad} toplantıyı yönetiyor',{ad:AG(o.kisilik)||'Suflor'}))} · ${esc(ne)}${o.bekle?' · '+esc(L('bekliyor')):''}</span></span><span class=ota>${o.madde?`<button class=gh data-mod=sonraki>${L('Sonraki madde')}</button>`:''}<button class=gh data-mod=${o.bekle?'devam':'bekle'}>${o.bekle?L('Devam'):L('Bekle')}</button><button class=gh data-mod=birak>${L('Yönetimi al')}</button></span></div>`}
function bindMod(root){root.addEventListener("click",ev=>{const b=ev.target.closest("button[data-mod]");if(!b)return;ev.stopPropagation();b.disabled=true;j('/moderator',{method:'POST',body:JSON.stringify({komut:b.dataset.mod})}).catch(()=>{})})}
function bindOtonom(root){root.addEventListener("click",ev=>{const b=ev.target.closest("button[data-ot]");if(!b)return;ev.stopPropagation();b.disabled=true;j('/otonom',{method:'POST',body:JSON.stringify({id:b.dataset.oid,karar:b.dataset.ot})}).catch(()=>{})})}
function bindSoyle(root){root.addEventListener("click",ev=>{const b=ev.target.closest("button[data-soyle]");if(!b)return;ev.stopPropagation();b.disabled=true
  j('/komut',{method:'POST',body:JSON.stringify({tur:'soyle',metin:b.dataset.soyle})}).then(r=>{const m=String(r.metin||'').replace(/^⌨\s*/,'');if(m.startsWith('⚠'))geciciDurum(m.replace(/^⚠\s*/,''),'')}).catch(()=>geciciDurum(L("Suflor.me'ye ulaşılamadı"),'')).finally(()=>setTimeout(()=>b.disabled=false,800))},true)}
function bindAck(root){root.addEventListener("click",ev=>{if(ev.target.closest("a[href]")||ev.target.closest("button[data-soyle]"))return;if(ev.target.closest("button[data-kdaha]")){KDAHA=!KDAHA;if(last)paintMini(last);return}const b=ev.target.closest("button[data-ack]"),k=ev.target.closest(".k[data-id]")
  if(!b&&k&&k.classList.contains("kkat")){KAC.add(k.dataset.id);k.classList.remove("kkat");k.title=L("Dokun: kapat");return}  // katlı kart: ilk dokunuş açar
  if(!b&&(!k||k.dataset.onay))return
  if(b)b.disabled=true;if(k)k.classList.add("kapaniyor");fetch("/card-ack",{method:"POST",body:JSON.stringify({id:b?b.dataset.id:k.dataset.id,status:b?b.dataset.ack:"okundu"})}).then(refresh)})}
async function sendNote(t){await fetch("/note",{method:"POST",body:JSON.stringify({text:t,at:new Date().toISOString()})})}
async function sendAsk(t){await fetch("/ask",{method:"POST",body:JSON.stringify({text:t})})}
async function sendGirdi(t,soru){try{return await (await fetch("/girdi",{method:"POST",body:JSON.stringify({text:t,soru,sesli:kutuSesliAcik()||undefined,at:new Date().toISOString()})})).json()}catch(e){return{}}}
// kanıt — toplantı sekmesindeki eklenti ≤ 3 sn içinde görüntüyü alır; kutudaki yazı kanıtın notu olur
async function sendKanit(b,ta){const t=ta?ta.value.trim():"";if(ta)ta.value="";if(b){b.disabled=true;b.innerHTML=ic('cam','…')}await fetch("/kanit-iste",{method:"POST",body:JSON.stringify({not:t,kaynak:"pano"})});setTimeout(()=>{if(b){b.disabled=false;b.innerHTML=ic('cam')}refresh()},4000)}
// ⭐ önemli an — aktarıcı dökümde işaretler, özet öne çıkarır (eski Option + Shift + S)
async function sendOnemli(b){if(b)b.disabled=true;try{const r=await (await fetch("/komut",{method:"POST",body:JSON.stringify({tur:"onemli"})})).json();if(b&&r.ok){b.innerHTML=ic('star','✓');setTimeout(()=>{b.innerHTML=ic('star');b.disabled=false},2000);return}}catch(e){}if(b)b.disabled=false}
// sessiz (Option + Shift + M ile aynı): 10 dk kart yok, tekrar basınca kapanır; durum düğmede ve "Şimdi" başlığında
async function sendSessiz(b){if(b)b.disabled=true;try{await fetch("/komut",{method:"POST",body:JSON.stringify({tur:"sessiz"})})}catch(e){}if(b)b.disabled=false;refresh()}
async function sendGizli(b){if(b)b.disabled=true;try{await fetch("/komut",{method:"POST",body:JSON.stringify({tur:"gizli"})})}catch(e){}if(b)b.disabled=false;refresh()}
function gizliCiz(b,s){if(!b)return;const on=!!s.gizli;b.classList.toggle("on",on);setH(b,ic('kilit',on?L("Gizli"):""));const d=b.ownerDocument;let x=d.getElementById('gzb');if(on&&!x){x=d.createElement('div');x.id='gzb';x.style.cssText='background:var(--dikkat);color:var(--s1);padding:var(--bo-8) var(--bo-12);font-size:var(--yz-13);text-align:center;border-radius:var(--kose);margin:var(--bo-4) 0';x.innerHTML=ic('kilit')+' '+esc(L("Gizli toplantı — Suflor dinlemiyor, yazmıyor, hiçbir yapay zekâya göndermiyor"));x.querySelector('svg').style.verticalAlign='-3px';d.body.prepend(x)}else if(!on&&x)x.remove()}  // v0.89.1: steril kip, tekrar basana kadar
function sessizCiz(b,s){if(!b)return;const ss=s.sessiz,on=!!(ss&&ss.acik);b.classList.toggle("on",on);setH(b,ic('mute',on?L("{n} dk",{n:Math.max(1,Math.ceil(ss.kalan_sn/60))}):""))}
// ekran paylaşımı kaydı (aktarıcı paylaşım sürerken kendiliğinden açar; düğme yok): "Şimdi" başlığında kendiliğinden alınan görüntü sayısı
const sdi=(n,t)=>`<span class=sdi>${ic(n)}<span>${esc(t)}</span></span>`
function yaparkenTxt(s){const y=s.yaparken;return y?sdi('cam',L("sunulan ekran · {n} görüntü",{n:y.oto})+(y.oto>=y.sinir?L(" (sınır doldu)"):"")):""}
// sesli çeviri: 🎧 aç/kapat (kulaklık yoksa aktarıcı açmaz, uyarı komut metninde); açıkken "Şimdi" başlığında okunan öz sayısı
async function sendSesliCeviri(b){if(b)b.disabled=true;try{await fetch("/komut",{method:"POST",body:JSON.stringify({tur:"sesli_ceviri"})})}catch(e){}if(b)b.disabled=false;refresh()}
function sesliCiz(b,s){if(!b)return;const v=s.sesli_ceviri;b.classList.toggle("on",!!v);setH(b,ic('kulak',v?L("{n} okundu",{n:v.okunan}):""))}
function sesliTxt(s){const v=s.sesli_ceviri;return v?sdi('kulak',L("sesli çeviri")+(v.uyari==="kulaklik"?L(" · kulaklık yok, okunmuyor"):"")):""}
function sessizTxt(s){const ss=s.sessiz,n=(ss&&ss.tutulan||[]).length;return[ss&&ss.acik?sdi('mute',L("sessiz, bitiş {t}",{t:ss.bitis})+(n?L(" · {n} kart bekliyor",{n}):"")):n?sdi('zil',L("Sessiz bitti — {asistan} özetliyor ({n} kart)",{n})):"",s.ertelenen?sdi('pause',L("{n} kart sonraya bırakıldı",{n:s.ertelenen})):"",s.tavan&&s.tavan.n?sdi('clock',L("{n} kart sırada · {s} sn",{n:s.tavan.n,s:Math.max(1,Math.round(s.tavan.t-Date.now()/1000))})):""].filter(Boolean).join(" · ")}
// eylem kuyruğu: toplantıda yalnız sayı ("📋 n iş toplantı sonuna"); Claude sununca (eylem sun) liste — her satırda Onayla/Reddet,
// ayrıntı katlı (uygulanacak işin tam hâli). Karar anahtarlı panodan; Claude yalnız onaylananı uygular, sonucu satırda görünür.
// eylem ayrıntısı komutsa (python3 … kayit.py … --sahip "X") okunur satırlara çevrilir: "Sahip: X". Ham komut panoda gösterilmez
// (kullanıcı, 10 Ekim); onaylanan iş yine bu komuttur, tam hâli eylemler.jsonl'de. --yazan gibi iç bilgi gösterilmez.
// lk: metindeki http(s) bağlantıları tıklanabilir (yeni sekme); başka şema (javascript: vb.) bağlantı olmaz.
function lk(s){return String(s==null?'':s).split(/(https?:\/\/[^\s"<>]+)/).map((p,i)=>{if(!(i%2))return esc(p);const m=p.match(/^(.*?)([.,;:!?)\]]*)$/);return `<a href="${esc(m[1])}" target=_blank rel=noopener>${esc(m[1])}</a>${esc(m[2])}`}).join('')}
// Ham JSON kullanıcıya gösterilmez (izin/kayıt kartının ayrıntısı JSON olarak saklanır): nesne ise yalnız insan okur özet (ozet, yoksa neden), yoksa boş
function ayGor(a){if(a==null)return'';if(typeof a==='object')a=JSON.stringify(a);a=String(a);if(!/^\s*[\[{]/.test(a))return a;let o;try{o=JSON.parse(a)}catch(e){return a}if(!o||typeof o!=='object')return a;return String(o.ozet||o.neden||o.metin||'').trim()}
function eyAyr(a){
  const t=String(a||'').replace(/^\s*```[^\n]*\n?/,'').replace(/\n?```\s*$/,'').trim()
  const sat=t.split('\n')
  if(!sat.some(l=>/^\s*(python3?|\S+\.py)\s/.test(l)))return `<pre>${lk(a)}</pre>`
  const out=sat.map(l=>{
    if(!/^\s*(python3?|\S+\.py)\s/.test(l))return l.trim()?`<div>${lk(l)}</div>`:''
    const tok=[];l.replace(/"((?:\\.|[^"\\])*)"|'([^']*)'|(\S+)/g,(m,a1,a2,a3)=>{tok.push(a1!=null?a1.replace(/\\(.)/g,'$1'):a2!=null?a2:a3)})
    const r=[]
    for(let i=0;i<tok.length;i++){
      if(!/^--./.test(tok[i]))continue
      const k=tok[i].slice(2),v=i+1<tok.length&&!/^--./.test(tok[i+1])?tok[++i]:'✓'
      if(k==='yazan')continue
      r.push(`<div><b>${esc(k.charAt(0).toLocaleUpperCase('tr')+k.slice(1).replace(/[-_]/g,' '))}:</b> ${lk(v)}</div>`)
    }
    return r.join('')
  }).join('')
  return `<div class=eyr>${out}</div>`
}
const EYT={kayit:L("Kayıt"),takvim:L("Takvim"),eposta:L("E-posta"),belge:L("Belge"),takip:L("Takip e-postası"),mesaj:L("Ekip mesajı"),diger:L("Diğer"),oturum:L("Oturuma talimat"),yapilacak:L("Yapılacak"),is:L("İş")}
const EYD={onaylandi:L("onaylandı — uygulanıyor"),reddedildi:L("reddedildi"),yapildi:L("yapıldı"),hata:L("yapılamadı")}
// Bekleyenler (30 Ekim): satır = tür simgesi + tek satır başlık; sağda yalnız tek tıkla biten işte (takvim, kayıt, yapılacak, oturuma talimat; sesli sorulan) Onayla,
// diğerlerinde ›. Satıra dokununca ayrıntı ve eylemler (Reddet, Kopyala, e-posta metni) yerinde açılır; açık satırlar yenilemede açık kalır.
const EYI={kayit:'dosya',takvim:'takvim',eposta:'posta',belge:'belge',takip:'posta',mesaj:'chat',diger:'liste',oturum:'sohbet',yapilacak:'check',is:'check'},EY_TEK=['takvim','kayit','yapilacak','oturum','is'],eyAcik=new Set()
function renderEylem(s){const e=s.eylem||{},ls=(e.liste||[]).filter(x=>x.sunuldu),sec=document.getElementById('eys');sec.hidden=!ls.length;if(!ls.length)return
  const bek=ls.filter(x=>x.durum==="bekliyor").length;document.getElementById('eyn').textContent=bek?String(bek):"";document.getElementById('eyh').hidden=bek<2
  setH(document.getElementById('ey'),ls.map(x=>{const b=x.durum==="bekliyor",ses=x.id===e.sesli,tek=b&&(ses||EY_TEK.includes(x.tur)),id=esc(x.id)
    const onay=`<button class=pri data-ey="${id}" data-d=onaylandi>${L('Onayla')}</button>`,red=`<button class=gh data-ey="${id}" data-d=reddedildi>${L('Reddet')}</button>`
    const kop=x.tur==="mesaj"&&x.ayrinti&&x.durum!=="reddedildi"?`<button class=gh data-kopyala="${id}" title="${L('Metni kopyala — ekip aracına sen yapıştırırsın')}">${L('Kopyala')}</button>`:''
    const sag=b?(tek?onay:'')+(ses?`<button class=gh data-ses=sonra title="${L('Bu işi şimdilik geç; panoda bekler')}">${L('Sonra')}</button><button class=gh data-ses=sus title="${L('Sesli soruları bitir; işler panoda bekler')}">${L('Sus')}</button>`:'')
      :`<span class=meta>${esc(EYD[x.durum]||x.durum)}${x.kaynak==='ses'?' · <span class=eyses>'+ic('mic')+'</span>':''}</span>${x.geri_al_sn>0?`<button class=gh data-geri="${id}" title="${esc(L('Sesli karar: duyulan "{m}"',{m:x.ses_metin||''}))}">${L('Geri al')} · ${Math.ceil(x.geri_al_sn)}</button>`:''}`
    return `<div class="ey ey-${esc(x.durum)}${ses?' ey-ses':''}"><details data-eyid="${id}"${eyAcik.has(x.id)?' open':''}><summary><span class=eyi title="${esc(EYT[x.tur]||x.tur)}">${ses?`<span title="${L('Şimdi sesli soruluyor')}">${ic('hoparlor')}</span>`:ic(EYI[x.tur]||'liste')}</span><span class=t>${esc(x.baslik)}${x.kim?' — '+esc(x.kim):''}</span><span class=ea>${sag}</span>${tek?'':`<span class=chev>${ic('ileri')}</span>`}</summary>`
      +`<div class=eyb><span class=chip>${esc(EYT[x.tur]||x.tur)}</span>${ayGor(x.ayrinti)&&x.tur!=='izin'?eyAyr(ayGor(x.ayrinti)):''}${x.sonuc?`<div class=d>${esc(x.sonuc)}</div>`:''}${b||kop?`<div class=bt>${kop}${b&&!tek?onay:''}${b?red:''}</div>`:''}</div></details></div>`}).join(''))}
document.getElementById('ey').addEventListener('toggle',ev=>{const d=ev.target;if(d&&d.dataset&&d.dataset.eyid){if(d.open)eyAcik.add(d.dataset.eyid);else eyAcik.delete(d.dataset.eyid)}},true)
async function eylemKarar(id,d,b){if(b)b.disabled=true;try{await fetch('/eylem-karar',{method:'POST',body:JSON.stringify({id,durum:d})})}catch(e){}refresh()}
document.getElementById('ey').addEventListener('click',async ev=>{if(ev.target.closest('summary button'))ev.preventDefault()  // satırdaki düğme satırı açıp kapamasın
  const k=ev.target.closest('button[data-kopyala]')
  if(k){const x=((last&&last.eylem||{}).liste||[]).find(y=>y.id===k.dataset.kopyala);try{await navigator.clipboard.writeText(x?x.ayrinti:'');k.textContent='✓ '+L('kopyalandı')}catch(e){k.textContent=L('kopyalanamadı')}setTimeout(()=>{k.textContent=L('Kopyala')},1500);return}
  const g=ev.target.closest('button[data-geri]');if(g){g.disabled=true;let r={};try{r=await j('/eylem-geri-al',{method:'POST',body:JSON.stringify({id:g.dataset.geri})})}catch(e){}if(!r.ok)geciciDurum(L('Geri alınamadı'),L('süre doldu'));refresh();return}
  const z=ev.target.closest('button[data-ses]');if(z){z.disabled=true;try{await j('/eylem-sesli',{method:'POST',body:JSON.stringify({komut:z.dataset.ses})})}catch(e){}refresh();return}
  const b=ev.target.closest('button[data-ey]');if(b)eylemKarar(b.dataset.ey,b.dataset.d,b)})
document.getElementById('eyh').onclick=ev=>eylemKarar('hepsi','onaylandi',ev.currentTarget)
// "Ne diyeyim?" (eski "Son 1 dk") — Claude son 2 dk + gündemle tek cümlelik replik + tek satır durum kartı (CEVAP) gönderir
async function sendOzet(b){if(b)b.disabled=true;await fetch("/ask",{method:"POST",body:JSON.stringify({tur:"ozet"})});refresh();if(b)setTimeout(()=>b.disabled=false,5000)}
// kalan süre + gündem kayması, konuşma payı
function sureTxt(s){const v=s.sure;if(!v)return["","",""];const k=v.kalan_dk;let t=k>0?L("{n} dk kaldı",{n:k}):(k===0?L("süre doldu"):L("{n} dk aşıldı",{n:-k}))
  const ti=L("bitiş {t}",{t:v.bitis})+(v.toplam?L(" · gündem {a}/{b}",{a:v.bitti,b:v.toplam})+(v.beklenen!=null?L(" (beklenen {n})",{n:v.beklenen}):""):"")
  if(v.kayma>=2)t+=L(" · {n} madde geride",{n:v.kayma})
  return[t,k<=0?"ac":(k<=5||v.kayma>=2?"uy":""),ti]}
const yuz=v=>DIL==="en"?v+"%":"%"+v  // İngilizcede 52%
function payHtml(s){const p=s.pay;if(!p)return"";const f=l=>l.map(([k,v])=>k===p.ben?`<span class=ben>${esc(k)} ${yuz(v)}</span>`:`${esc(k)} ${yuz(v)}`).join(" · ")
  if(p.adsiz>=50)return L("Konuşma payı ölçülemiyor (konuşmacı adı gelmiyor)")
  return`${L("Konuşma payı")}${p.kelime_son?L(" (son 10 dk)"):``}: ${f(p.kelime_son?p.son:p.top)}${p.kelime_son?` <span class=hint>· ${L("toplam")}: ${f(p.top.slice(0,3))}</span>`:""}`}
function payUy(s){const p=s.pay;return!!(p&&p.ben_son!=null&&p.ben_son>=60&&p.kelime_son>=150)}
