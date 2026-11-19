try{if(/[?&]mac=1(&|$)/.test(location.search))document.documentElement.classList.add('mac')}catch(e){}  // deneme: Mac penceresi (menü uygulamasının WKWebView'ı html.mac ekler) görünümünü tarayıcıda zorlar
// arayüz dili (ayar "dil"; aktarıcı __DIL__ yerine yazar). Anahtar Türkçe metnin kendisi; İngilizcesi yoksa Türkçe kalır.
// Sabit HTML yüklenince çevrilir (metin düğümleri + placeholder/title/aria-label), değişen metinler L() ile.
const DIL="__DIL__"
const EN=globalThis.SUFLOR_EN || {}
// S133: kullanıcıya görünen tek muhatap asistan — {asistan} = toplantı kişiliğinin adı (/status asistan; kişiliksiz "Suflor")
let AS="Suflor",ASM={};const AG=a=>ASM[a]||a;const asGor=k=>(k&&(k.kisilik_gorunen||AG(k.kisilik)))||AS
function L(s,v){let t=DIL==="en"&&EN[s]||s;if(v)for(const k in v)t=t.split("{"+k+"}").join(v[k]);if(DIL==="en"&&v)t=t.replace(/\b1 (day|week|hour|minute|item|card|task|record|meeting)s\b/g,"1 $1");return t.split("{asistan}").join(AS)}  // İngilizce tekil: "1 days" → "1 day"
// durağan HTML'deki {asistan}: özgün metin saklanır, ad değişince yeniden yazılır
// kutu ipucu: toplantıda (ve mini panoda) genel "Asistanla konuş" — toplantıda ve dışında asistan farklı; panoda toplantı yokken (Bugün) toplantı dışı kişiliğin adıyla "Marvin'e sor"
function yonelme(a){a=String(a||'').trim();const t=a.toLowerCase(),v=(t.match(/[aeıioöuü](?=[^aeıioöuü]*$)/)||['e'])[0];return a+"'"+(/[aeıioöuü]$/.test(t)?'y':'')+('aıou'.includes(v)?'a':'e')}
function yazIpucu(d){let s=null;try{s=last}catch(e){}  // ilk çizimde last henüz tanımlı değil
  const ad=asGor(s&&s.konus);return L('{ad} sor, iş ver ya da araştırt…',{ad:DIL==='en'?ad:yonelme(ad)})}  // 19 Kasım (Y1): her sayfada, toplantıda ve mini panoda aynı ipucu
function asYaz(kok){kok.querySelectorAll("[placeholder],[title],[aria-label]").forEach(e=>["placeholder","title","aria-label"].forEach(a=>{const o=(e.__as||{})[a]||e.getAttribute(a);if(o&&o.includes("{asistan}")){(e.__as=e.__as||{})[a]=o;e.setAttribute(a,o.split("{asistan}").join(AS))}}));const t=kok.getElementById&&kok.getElementById("tosad");if(t)t.textContent=AS;for(const id of ["n","mn"]){const n=kok.getElementById&&kok.getElementById(id);if(n&&!n.dataset.cevap)n.placeholder=yazIpucu(id==="n"?kok:null)}const b=kok.getElementById&&kok.getElementById("bgas");if(b)b.textContent=L("{asistan} okur")}
function cevir(kok){if(DIL!=="en")return;const w=document.createTreeWalker(kok,NodeFilter.SHOW_TEXT);const d=[];while(w.nextNode())d.push(w.currentNode)
  d.forEach(n=>{const k=n.nodeValue.trim();if(k&&EN[k])n.nodeValue=n.nodeValue.replace(k,EN[k])})
  kok.querySelectorAll("[placeholder],[title],[aria-label]").forEach(e=>["placeholder","title","aria-label"].forEach(a=>{const k=e.getAttribute(a);if(k&&EN[k])e.setAttribute(a,EN[k])}))}
cevir(document.body);asYaz(document)
// arayüz: üst çubuk (toplantı, rol, süre, tek durum cümlesi), solda kartlar (boşken "Sıradaki · Başlat") ve tek giriş,
// sağda Gündem/Açık sorular/Kanıtlar ve katlanan döküm. /status 2 sn, /taslak 1 sn (yalnız döküm açıkken).
const ICO={hoparlorx:'<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M16 9.5l5 5M21 9.5l-5 5"/>',hoparlor:'<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4.5 4.5 0 0 1 0 6M18 6.5a8 8 0 0 1 0 11"/>',yenile:'<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/>',zil:'<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',liste:'<rect x=5 y=4.5 width=14 height=16 rx=2 /><path d="M9 4.5V3h6v1.5M8.5 10h7M8.5 13.5h7M8.5 17h4"/>',dosya:'<path d="M6 3.5h8l4 4V20.5H6z"/><path d="M14 3.5v4h4"/>',bag:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',kalem:'<path d="M4.5 19.5l1-4L16 5l3 3L8.5 18.5z"/><path d="M14 7l3 3"/>',uyari:'<path d="M12 4l9 15.5H3z"/><path d="M12 10v4M12 17v.01"/>',dur:'<rect x=7 y=7 width=10 height=10 rx=2.5 />',mic:'<rect x=9 y=2.5 width=6 height=11.5 rx=3 /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>',sohbet:'<path d="M20.5 12a8.5 8.5 0 0 1-12.4 7.6L3.5 20.5l1-4.2A8.5 8.5 0 1 1 20.5 12z"/><path d="M9 10.5v3M12 9v6M15 10.5v3"/>',gear:'<circle cx=12 cy=12 r=3 /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',clock:'<circle cx=12 cy=12 r=9 /><path d="M12 7v5l3 2"/>',star:'<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.8l-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/>',cam:'<path d="M4 8h3l2-2.5h6L17 8h3v11H4z"/><circle cx=12 cy=13 r=3.5 />',hist:'<path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.5"/><path d="M4 4v4.5h4.5"/><path d="M12 8v4l2.5 1.5"/>',
 win:'<rect x=3 y=5 width=18 height=14 rx=2 /><rect x=12 y=11 width=7 height=6 rx=1 />',check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',eye:'<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx=12 cy=12 r=2.8 />',x:'<path d="M6 6l12 12M18 6L6 18"/>',chat:'<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',replik:'<path d="M4 5h16v11H9l-5 4z"/><path d="M10 8.6a2 2 0 1 1 2.6 1.9c-.4.2-.6.5-.6.9v.4"/><path d="M12 13.6v.1"/>',pause:'<path d="M9 6v12M15 6v12"/>',rec:'<rect x=3 y=5 width=18 height=13 rx=2 /><circle cx=12 cy=11.5 r=3 /><path d="M8 21h8"/>',kulak:'<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x=3.5 y=14 width=4 height=6 rx=1.5 /><rect x=16.5 y=14 width=4 height=6 rx=1.5 />',kilit:'<rect x=5 y=10.5 width=14 height=10 rx=2 /><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3"/>',mute:'<path d="M6.5 16v-4.5a5.5 5.5 0 0 1 8.6-4.5M17.5 11.5V16l1.5 2H8"/><path d="M10 20.5a2 2 0 0 0 4 0"/><path d="M4 4l16 16"/>',
 arti:'<path d="M12 5.5v13M5.5 12h13"/>', dahasi:'<circle cx=5.5 cy=12 r=.9 /><circle cx=12 cy=12 r=.9 /><circle cx=18.5 cy=12 r=.9 />',belge:'<path d="M6 3.5h8l4 4v13H6z"/><path d="M14 3.5v4h4M9 13h6M9 16.5h4"/>',
 kopya:'<rect x=8.5 y=8.5 width=11 height=12 rx=2 /><path d="M15.5 8.5V5.5a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h2"/>',indir:'<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14"/>',
 posta:'<rect x=3.5 y=5.5 width=17 height=13 rx=2 /><path d="M4 7l8 6 8-6"/>',harita:'<circle cx=12 cy=12 r=2.5 /><circle cx=5 cy=6 r=1.8 /><circle cx=19 cy=6 r=1.8 /><circle cx=19 cy=18 r=1.8 /><path d="M7 7l3.2 3.4M17 7l-3.2 3.4M17.3 16.7l-3.3-3"/>',bos:'',hafta:'<rect x=4 y=5 width=16 height=15 rx=2 /><path d="M4 10h16M9 3v4M15 3v4M9.3 10v10M14.7 10v10"/>',takvim:'<rect x=4 y=5 width=16 height=15 rx=2 /><path d="M4 10h16M9 3v4M15 3v4"/>',mik:'<rect x=9 y=3 width=6 height=11 rx=3 /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>'}
ICO.ileri='<path d="M9.5 6l6 6-6 6"/>';ICO.asagi='<path d="M6 9.5l6 6 6-6"/>';ICO.claude='<path d="M14.2 12.3L20.7 13.2M13.7 13.4L17.4 16.2M12.8 14.0L15.3 20.2M11.7 14.2L11.1 18.7M10.6 13.7L6.6 18.9M10.0 12.8L5.7 14.5M9.8 11.7L3.3 10.8M10.3 10.6L6.6 7.8M11.2 10.0L8.7 3.8M12.3 9.8L12.9 5.3M13.4 10.3L17.4 5.1M14.0 11.2L18.3 9.5"/>';ICO.kisi='<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.9-3.8 3.7-5.8 7-5.8s6.1 2 7 5.8"/>';ICO.geri='<path d="M9 8L4.5 12.5 9 17"/><path d="M4.5 12.5h9a6 6 0 0 1 0 7H11"/>';ICO.engel='<circle cx="12" cy="12" r="8.5"/><path d="M6 6l12 12"/>';ICO.video='<rect x="3" y="6.5" width="12.5" height="11" rx="2.5"/><path d="M15.5 10.5l5-3v9l-5-3"/>'
const ic=(n,t)=>`<svg class=i viewBox="0 0 24 24" aria-hidden=true>${ICO[n]}</svg>${t?'<span>'+t+'</span>':''}`
document.getElementById('oz').innerHTML=ic('replik');document.querySelector('#dkh .ok-i').innerHTML=ic('ileri');document.getElementById('tke').innerHTML=ic('arti');document.getElementById('ek').innerHTML=ic('arti');document.getElementById('kb').innerHTML=ic('mic');document.querySelector('#tbm>summary').innerHTML=ic('dahasi'); document.getElementById('yz').innerHTML=ic('star'); document.getElementById('sz').innerHTML=ic('mute'); document.getElementById('gz').innerHTML=ic('kilit'); document.getElementById('kz').innerHTML=ic('cam'); document.getElementById('sc').innerHTML=ic('kulak')
// Sağ sütun sürüklenerek genişletilir; genişlik bu tarayıcıda hatırlanır (v0.3.3)
const rz=document.getElementById('rz'), root=document.documentElement
function setAw(px){px=Math.max(260,Math.min(innerWidth*0.7,px));root.style.setProperty('--aw',px+'px');return px}
try{const w=+localStorage.getItem('aw');if(w)setAw(w)}catch(e){}
rz.onpointerdown=ev=>{rz.setPointerCapture(ev.pointerId);rz.classList.add('on')
  rz.onpointermove=m=>{const w=setAw(innerWidth-m.clientX-3);try{localStorage.setItem('aw',w)}catch(e){}}
  rz.onpointerup=()=>{rz.onpointermove=null;rz.classList.remove('on')}}
rz.ondblclick=()=>{root.style.removeProperty('--aw');try{localStorage.removeItem('aw')}catch(e){}}
async function j(u,o){const r=await fetch(u,o);return r.json()}
let atBottom=true, agSig=""
const main=document.getElementById('dkg'), lines=document.getElementById('lines'), liveBtn=document.getElementById('live')  // döküm kaydırma alanı
// döküm sağ sütunda katlı durur (toplantıda en az bakılan yer); açınca sütunun altını alır, gündem üstte görünür kalır (en çok %45).
// Seçim bu tarayıcıda hatırlanır.
let dkAcik=false
function dokumAc(v){dkAcik=v;const a=document.querySelector('aside'),h=document.getElementById('dkh');a.classList.toggle('dk-acik',v);main.hidden=!v;h.setAttribute('aria-expanded',v);h.querySelector('.ok-i').innerHTML=ic(v?'asagi':'ileri')
  try{localStorage.setItem('dk',v?'1':'')}catch(e){}if(v){main.scrollTop=main.scrollHeight;atBottom=true}}
document.getElementById('dkh').onclick=()=>dokumAc(!dkAcik)
try{if(localStorage.getItem('dk'))setTimeout(()=>dokumAc(true))}catch(e){}
function nearBottom(){return main.scrollHeight-main.scrollTop-main.clientHeight<40}
main.addEventListener('scroll',()=>{atBottom=nearBottom();liveBtn.style.display=atBottom?'none':'block'})
liveBtn.onclick=()=>{main.scrollTop=main.scrollHeight;atBottom=true;liveBtn.style.display='none'}
// kanıt görseli/bağlantısı başlık gönderemez: anahtar adreste (yalnız /kanit/ için kabul edilir)
const kq=()=>"?k="+encodeURIComponent(SUFLOR_ANAHTAR)
// Metin HTML diye yorumlanmasın: "<", "&" içeren not/cümle aynen görünsün (v0.3.2)
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function setH(el,h){if(el&&el.__h!==h){el.innerHTML=h;el.__h=h}}
// Anahtar satırın konumuna değil kendisine bağlı: pencere kayınca not yerinden oynamaz (v0.3.2)
function rowKey(e,i){return e.kanit?('kanit|'+e.kanit):e.note?('note|'+(e.at||'')+'|'+e.note):(e.id||('k|'+e.time+'|'+e.speaker+'|'+e.text))}
function rowHtml(e){return e.kanit?`<div class="l kn">${ic('cam')} ${L('Kanıt')} ${esc(e.n)} · ${esc((e.at||'').slice(11,19))} · <a href="/${esc(e.kanit)}${kq()}" target=_blank>${L('aç')}</a>${e.not?' — '+esc(e.not):''}</div>`:e.note?`<div class="l note">${ic('kalem')} ${esc(e.note)}</div>`:`<div class="l ${e.flags&&e.flags.length?'f':''}"><span class=sp><b>${esc(e.speaker)}</b>${e.time?' · <span class=z>'+esc(e.time)+'</span>':''}</span><br>${esc(e.text)}${e.ceviri?'<div class=cv>'+esc(e.ceviri)+'</div>':''}</div>`}
// Satır öğeleri Map'te tutulur: anahtar metin içerdiği için CSS seçiciyle aranmaz (v0.3.3)
const rowEls=new Map()
function renderLines(tail){
  const keep=new Set()
  tail.forEach((e,i)=>{
    const k=rowKey(e,i); keep.add(k)
    let el=rowEls.get(k)
    const html=rowHtml(e)
    if(!el){el=document.createElement('div');rowEls.set(k,el);lines.appendChild(el)}
    if(el.__html!==html){el.innerHTML=html;el.__html=html}
  })
  rowEls.forEach((el,k)=>{if(!keep.has(k)){el.remove();rowEls.delete(k)}})
  if(!tail.length&&!lines.querySelector('.empty')){const d=document.createElement('div');d.className='empty';d.textContent=L('Toplantı başlayınca konuşma burada akar.');lines.appendChild(d)}
  else if(tail.length){const d=lines.querySelector('.empty');if(d)d.remove()}
}
// taslak — henüz sabitlenmemiş metin; kesin satır (Whisper ya da sabit satır) gelince yerine geçer. 1 sn'de bir
function renderTaslak(t){const h=(t||[]).map(e=>`<div class="l ts" title="${L('Taslak ({d}); kesin metin gelince yerine geçer',{d:L(e.sabit?'Whisper bekleniyor':'konuşuluyor')})}"><span class=sp><b>${esc(e.speaker)}</b> · ${L('taslak')}</span><br>${esc(e.text)}${e.sabit?'':' …'}</div>`).join('');const el=document.getElementById('tsl');if(el.__h===h)return;const b=nearBottom();el.innerHTML=h;el.__h=h;if(b&&atBottom)main.scrollTop=main.scrollHeight}
setInterval(()=>{if(dkAcik)j('/taslak?pano=1').then(v=>renderTaslak(v.taslak)).catch(()=>{})},1000)
