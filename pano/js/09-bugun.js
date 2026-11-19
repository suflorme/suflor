// ===== Bugün ana sayfası (v0.189.0; onaylı tasarım, 5 Kasım): selam → durum paragrafı → gün şeridi → senden beklenenler → sıradaki toplantı → son toplantı. Yalnız mevcut veri: takvim (/takvim?hafta=0), hazırlık/brifing (s.brifing),
// eylem kuyruğu (s.eylem), son toplantılar (s.son_toplantilar, çıktı sayıları). Veri yoksa bölüm ya da cümle yok. Kurallar ve renkler pano/bugun.css, renk.css, yazi.css. =====
Object.entries({isler:'<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',ekip:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 010 7M18.5 14.8c1.6.9 2.6 2.6 3 5.2"/>',oynat:'<path d="M8 5.5v13l10.5-6.5z"/>',gun:'<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>',karar:'<path d="M12 3.5l7 3v5c0 4.3-3 7.6-7 9-4-1.4-7-4.7-7-9v-5z"/><path d="M8.8 12l2.3 2.3 4.3-4.6"/>',menu:'<path d="M4 7h16M4 12h16M4 17h10"/>',ara:'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',video:'<rect x="3.5" y="6.5" width="12" height="11" rx="2"/><path d="M15.5 10.5l5-3v9l-5-3z"/>',saatDunya:'<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.4 3.6 5.2 3.6 8.5s-1.1 6.1-3.6 8.5c-2.5-2.4-3.6-5.2-3.6-8.5S9.5 5.9 12 3.5z"/>'}).forEach(([k,v])=>{if(!ICO[k])ICO[k]=v})
let prD={durum:'yok'},prBusy=false,prHata='',prKisi=[],prForm={konu:'',baglam:'',belge:''},prT=0
let bnOlay=[],bnSonraki=null,bnTakOk=false,bnHazir=false,bnT=0,bnYuk=false,bnRef=null,bnGeri=null,bnBildT=null,bnDin=null
const bnGizli=new Set()
// Kararlar ve işler görünümü (5 Kasım): kenar çubuğundan tam sayfa liste (/kayitlar) — sekme karar/iş/açık soru, süzgeç kişi/toplantı/durum/arama; gündem taslağı (/gundem-taslagi) hazırlık kartında
let ikV=null,ikBek=new Set(),boV=null,boBek=new Set(),bnGor='bugun',knV=null,knOrt=null,knT=0,knYuk=false,knSekme='is',knSuz={kisi:'',toplanti:'',durum:'',ara:'',sahip:(()=>{try{const v=localStorage.getItem('knSahip');return['ben','ekip'].includes(v)?v:'ben'}catch(e){return'ben'}})()},knDen=false,knAraT=null,gtV={},gtYukSet=new Set()
const bnTarih=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
const bnDk=h=>{const [a,b]=String(h||'0:0').split(':').map(Number);return (a||0)*60+(b||0)}
const bnIlk=a=>String(a||'').trim().split(/\s+/)[0]
const bnBas=a=>String(a||'').trim().split(/\s+/).map(x=>x[0]||'').join('').slice(0,2).toUpperCase()
async function bnYukle(zorla){if(bnYuk||(!zorla&&Date.now()-bnT<60000))return;bnYuk=true;bnT=Date.now()
  try{const t=await j('/takvim?hafta=0'),g=bnTarih(),ol=(t.olaylar||[]).filter(o=>o.tarih===g&&!o.tum_gun&&!o.reddettin&&!o.paylasilan).sort((a,b)=>bnDk(a.saat)-bnDk(b.saat))
    const sn=(t.olaylar||[]).filter(o=>o.tarih>g&&!o.tum_gun&&!o.reddettin&&!o.paylasilan).sort((a,b)=>String(a.tarih+a.saat).localeCompare(String(b.tarih+b.saat)))[0]||null  // bugün toplantı yoksa tek satırda sıradaki
    bnTakOk=t.durum==='ok'||(t.olaylar||[]).length>0  // takvim okunamıyorsa "toplantı yok" denmez
    const ilk=!bnHazir;bnHazir=true;if(ilk||JSON.stringify(ol)!==JSON.stringify(bnOlay)||JSON.stringify(sn)!==JSON.stringify(bnSonraki)){bnOlay=ol;bnSonraki=sn;if(last)bnCiz(last)}}catch(e){}
  bnYuk=false}
const bnYuzler=k=>`<span class=yuzler>${k.slice(0,5).map(x=>`<span class=kisi-yuz title="${esc(x)}">${esc(bnBas(x))}</span>`).join('')}</span>`
const bnOldu=t=>`<span class=oldu>${ic('check')}${esc(t)}</span>`
const bnVarlik=(ref,t)=>`<span style="white-space:nowrap"><button type=button class=varlik data-bn=panel data-ref="${esc(ref)}">${esc(t)}</button></span>`
// Bugün verisi (karar grafı; /bugun-veri): açık işler, teyit bekleyen kararlar, son toplantının kararları. Veri yoksa bölüm görünmez.
let bnV=null,bnVT=0,bnVYuk=false,bnBekAcik=false,bnGerAcik=false,bnDfzAcik=false,izV=null
async function bnVeriYukle(zorla){if(!zorla&&(bnVYuk||Date.now()-bnVT<30000))return;bnVYuk=true;bnVT=Date.now()
  try{const v=await j('/bugun-veri');if(v&&v.ok){const ilk=!bnV;if(ilk||JSON.stringify(v)!==JSON.stringify(bnV)){bnV=v;if(last)bnCiz(last)}}}catch(e){}
  try{const z=await j('/izleme');if(z&&z.ok&&JSON.stringify(z)!==JSON.stringify(izV)){izV=z;if(last)bnCiz(last)}}catch(e){}  // İzleme (aktarici/izleme.py): ayar izleme_dosyasi yoksa {acik:false}, bölüm görünmez
  bnVYuk=false}
const bnKendi=()=>((bnV||{}).kendi||[]).filter(x=>!bnGizli.has(x.id)),bnBaskasi=()=>((bnV||{}).baskalari||[]).filter(x=>!bnGizli.has(x.id)),bnTeyit=()=>((bnV||{}).teyit||[]).filter(x=>!bnGizli.has(x.id))
const bnYakin=x=>x.kalan_gun!=null&&x.kalan_gun<=2
// S226: "Senden beklenenler" yalnız son 14 günün kendi işleri + kendi yürüttüğün toplantıların onay bekleyen kararları; daha eskisi (x.geride, sunucu işaretler) ayrı, katlanmış "Geride kalanlar"
const bnKendiT=()=>bnKendi().filter(x=>!x.geride),bnTeyitT=()=>bnTeyit().filter(x=>!x.geride),bnGeride=()=>[...bnKendi().filter(x=>x.geride),...bnTeyit().filter(x=>x.geride)]
const emDugme=x=>x.dis||!(x.kayit_id||x.id)?'':`<button type=button class=em data-bn=emenu data-kid="${esc(x.kayit_id||x.id)}" title="${L('Eylemler')}" aria-label="${L('Eylemler')}">${ic('dahasi')}</button>`
function bnVadeEt(x){if(!x.vade)return'';return goreliSpan(x.vade,x.gecikti?'etiket gec':'vade',true)}
function bnIsSatir(x,baskasi){const k=baskasi&&x.kim?`<button type=button class=varlik data-bn=panel data-ref="k:${esc(x.kim)}">${esc(x.kim)}</button>`:''
  return`<div class=sat data-id="${esc(x.id)}"><button type=button class=onay data-bn=isbit data-id="${esc(x.id)}" aria-label="${L('Yapıldı')}">${ic('check')}</button>
    <div class=m><div class=t>${esc(x.metin)}</div><div class=a>${k}${x.atayan?`<span class="etiketk karar">${L('Sana atandı · {ad}',{ad:esc(x.atayan)})}</span>`:''}<span class=etiketk>${esc(x.baslik||L('İş'))}</span></div></div><div class=eylem>${bnVadeEt(x)}${emDugme(x)}</div></div>`}
// İzleme (aktarici/izleme.py): başka panonun Drive'a yazdığı anlık görüntü, yalnız okunur. Sapma/kırmızı hesabı dosyada hazırdır; burada aynen gösterilir. Kart başlığı bağlantıysa dış sekmede açılır (https).
const izBag=(t,u)=>u&&/^https:\/\//.test(u)?`<a href="${esc(u)}" target=_blank rel="noopener noreferrer">${esc(t)}</a>`:esc(t)
const izOk=(a,b)=>a==null?'–':b==null||b===a?String(a):a+(a>b?' ↑':' ↓')  // önceki dönemle yön; yorum yok
const izSat=(t,a,e)=>`<div class="sat dis"><span class=kaynakn aria-hidden=true></span><div class=m><div class=t>${t}</div><div class=a>${a}</div></div><div class=eylem>${e||''}</div></div>`
const izGun=n=>n==null?'':`<span class=vade>${esc(L('{n} gün',{n}))}</span>`
const izNedenler=x=>x.neden||x.metin||x.kod||''
function izBolum(){const z=izV;if(!z||!z.acik)return'';const ad=esc(z.ad||'')
  if(z.durum==='bicim')return`<section class="bolum iz"><p class="giris kucuk">${ad}: ${L('biçim tanınmadı')}</p></section>`
  if(!z.uretim&&!z.kimde)return`<section class="bolum iz"><p class="giris kucuk">${L('Monitör verisi henüz yok')}</p></section>`  // dosya yok ya da okunamıyor, son geçerli veri de yok
  const eski=z.eski?` <span class="etiket bekliyor">${esc(L('veri eski ({n} saat)',{n:z.eski_saat}))}</span>`:'',bz=z.durum==='bozuk'?` <span class="etiket bekliyor">${esc(L('dosya okunamadı, son geçerli veri'))}</span>`:''
  // Ekip'te İzleme (onaylı taslak): başlık satırı kaynak · N yeni sapma · göreli zaman, nabız hapları, sapma satırları (ad yeşil bağlantı, birim · kişi, sağda durum etiketi + gün mono), "N sapma daha". Kimde bekliyor ve sahipsiz kart ayrıntıları Tümü panelinde.
  const tum=z.yeni_sapmalar||[],sp=tum.slice(0,5),sh=z.sahipsiz||{},nb=z.nabiz||[],say=z.yeni_sapma_sayi!=null?z.yeni_sapma_sayi:tum.length,fazla=Math.max(0,say-sp.length),zm=goreliSaat(z.kaynak_okuma||z.uretim)
  const bilgi=[`<b>${ad}</b>`,say?esc(L('{n} yeni sapma',{n:say})):'',zm?esc(zm):''].filter(Boolean).join(' · ')
  const hap=(b,t)=>`<span class=izhap><b>${esc(b)}</b><span>${t}</span></span>`
  const haps=nb.map(n=>hap(n.birim,`${esc(L('Biten'))} ${izOk(n.biten.sayi,n.biten.onceki)} · ${esc(L('Yeni'))} ${izOk(n.yeni.sayi,n.yeni.onceki)} · ${esc(L('Sapma'))} ${izOk(n.sapma.sayi,n.sapma.onceki)}`)).join('')+(sh.toplam?hap(L('Sahipsiz'),esc(L('{n} kart',{n:sh.toplam}))):'')
  return`<section class="bolum iz"><p class="giris kucuk izb">${bilgi}${eski}${bz}</p>`
    +(haps?`<div class=izhaps>${haps}</div>`:'')
    +(sp.length?`<div class=ince>${sp.map(x=>izSat(izBag(x.baslik||x.id,x.url),[x.birim,x.sahip].filter(Boolean).map(esc).join(' · '),(izNedenler(x)?`<span class="etiket uyari">${esc(izNedenler(x))}</span>`:'')+izGun(x.gun))).join('')}</div>`:'')
    +`<div class=izalt><button type=button class=bag data-bn=panel data-ref=iz>${fazla?esc(L('{n} sapma daha',{n:fazla})):L('Tümü')}</button></div></section>`}
function izSatir(o){const e=((izV||{}).eslesen||{})[o.id];if(!e||!e.adaylar.length)return''  // takvim toplantısı dosyadaki bir toplantıyla eşleşirse adayları hazırlıkta
  return`<div class="haz gundem">${ic('liste')}<span><b>${L('Gündem adayları ({ad}): {n}',{ad:esc(izV.ad||''),n:e.adaylar.length})}</b> ${esc(e.adaylar.slice(0,2).map(m=>m.baslik).join(' · '))}${e.adaylar.length>2?' …':''}</span><button type=button class="b sade" data-bn=izac data-id="${esc(o.id)}">${L('Aç')}</button></div>`}
function izPanel(ref,bas){const z=izV||{},blok=(t,h)=>h?`<div class=blok>${t?`<h4>${esc(t)}</h4>`:''}${h}</div>`:'',li=(a,b)=>`<li><span class=mt>${a}</span>${b||''}</li>`
  if(ref==='iz'){const eski=z.eski?esc(L('veri eski ({n} saat)',{n:z.eski_saat})):''
    return bas(L('İzleme'),z.ad||'',eski)
      +blok(L('Yeni sapmalar: {n}',{n:z.yeni_sapma_sayi||0}),(z.yeni_sapmalar||[]).length?`<ul>${z.yeni_sapmalar.map(x=>li(izBag(x.baslik||x.id,x.url)+(izNedenler(x)?' — '+esc(izNedenler(x)):'')+(x.sahip?' · '+esc(x.sahip):''),izGun(x.gun))).join('')}</ul>`:'')
      +blok(L('Kimde bekliyor'),(z.kimde||[]).length?`<ul>${z.kimde.map(k=>li(`<b>${esc(k.ad)}</b> — ${esc(L('{n} açık',{n:k.acik}))}, ${esc(L('{n} onay bekliyor',{n:k.onay}))}`+(k.onayEnUzun!=null?', '+esc(L('en uzun {n} gün',{n:k.onayEnUzun})):'')+(k.kartlar||[]).map(c=>`<br>${izBag(c.baslik||c.id,c.url)}${c.asama?' · '+esc(c.asama):''}`).join(''))).join('')}</ul>`:'')
      +blok(L('Sahipsiz: {n} kart',{n:(z.sahipsiz||{}).toplam||0}),((z.sahipsiz||{}).kartlar||[]).length?`<ul>${z.sahipsiz.kartlar.map(c=>li(izBag(c.baslik||c.id,c.url),c.asama?`<span class=vade>${esc(c.asama)}</span>`:'')).join('')}</ul>`:'')
      +blok(L('Nabız'),(z.nabiz||[]).length?`<ul>${z.nabiz.map(n=>li(`<b>${esc(n.birim)}</b> — ${esc(L('Biten'))} ${izOk(n.biten.sayi,n.biten.onceki)}, ${esc(L('Yeni'))} ${izOk(n.yeni.sayi,n.yeni.onceki)}, ${esc(L('Sapma'))} ${izOk(n.sapma.sayi,n.sapma.onceki)}`)).join('')}</ul>`:'')
      +`<p class=alt2>${esc(L('Yalnız okunur; veri başka bir panodan gelir ve günde birkaç kez yenilenir.'))}</p>`}
  const id=ref.slice(4),e=(z.eslesen||{})[id],o=bnOlay.find(x=>x.id===id)
  return bas(L('Gündem adayları ({ad})',{ad:z.ad||''}),o?o.baslik||'':'',e?L('{n} aday',{n:e.adaylar.length}):'')+(e&&e.adaylar.length?`<div class=blok><ul>${e.adaylar.map(c=>li(izBag(c.baslik||c.id,c.url)+(c.nedenler||[]).map(n=>'<br>'+esc(n.metin||n.kod)).join(''),c.asama?`<span class=vade>${esc(c.asama)}</span>`:'')).join('')}</ul></div>`:`<p class=alt2>${L('Aday yok.')}</p>`)}
function bnDisSatir(x,kaynak){const tur=x.tur==='karar'?L('Karar'):x.tur==='soru'?L('Açık soru'):L('İş')  // dış defter satırı: onay düğmesi yok (yalnız okunur), kaynak etiketi
  return`<div class="sat dis"><span class=kaynakn aria-hidden=true></span><div class=m><div class=t>${esc(x.metin)}</div><div class=a><span class="etiketk${x.tur==='karar'?' karar':''}">${esc(tur)}</span>${x.sahip?`<span>${esc(x.sahip)}</span>`:''}${x.toplanti?`<span>${esc(x.toplanti)}</span>`:''}<span class="etiket notr">${esc(kaynak)}</span></div></div><div class=eylem>${x.vade?`<span class=vade>${esc(x.vade)}</span>`:''}</div></div>`}
function bnKararSatir(x){return`<div class=sat data-id="${esc(x.id)}"><button type=button class="onay karar" data-bn=kararonay data-id="${esc(x.id)}" aria-label="${L('Onayla')}">${ic('check')}</button>
    <div class=m><div class=t>${esc(x.metin)}</div><div class=a><span class="etiketk karar">${L('Karar')}</span><span>${esc(x.neden||L('onay bekliyor'))}</span>${emOnayIs(x.onay)}</div></div><div class=eylem>${emDugme(x)}</div></div>`}
function bnKararBlok(r){const sk=(bnV||{}).son_karar;if(!sk||!r||String(sk.toplanti||'').replace(/\.md$/,'')!==String(r.dosya||'').replace(/\.md$/,''))return''
  const ks=(sk.kararlar||[]).map(x=>({...x,teyit:x.teyit&&!bnGizli.has(x.id)}));if(!ks.length)return'';const tl=ks.filter(x=>x.teyit).map(x=>x.id)
  return`<ul class=kararlar>${ks.map(x=>`<li><span class=km>${esc(x.metin)}</span>${x.teyit?`<span class=sakin>${esc(x.neden||L('onay bekliyor'))}</span>`:''}</li>`).join('')}</ul>${tl.length?`<div class=keylem><button type=button class=b data-bn=kararlar data-idler="${esc(tl.join(','))}">${ic('check')}${L('Kararları onayla')}</button></div>`:''}`}
// kayıt yazan eylemler (iş yapıldı, karar onayı): satır kapanır, 5 sn sonra yazılır; Geri al bu sürede vazgeçer
function bnIsle(idler,mesaj,yap,pn){idler=idler.filter(i=>!bnGizli.has(i));if(!idler.length)return;idler.forEach(id=>{bnGizli.add(id)
    const sat=document.querySelector(`#bgn .sat[data-id="${CSS.escape(id)}"]`);if(sat){const h=sat.offsetHeight;sat.style.height=h+'px';void sat.offsetHeight;sat.classList.add('kapan');sat.style.height='0px'}})
  const t=setTimeout(async()=>{try{await yap()}catch(e){}await bnVeriYukle(true);if(bnGor==='kayit')await knYukle(true);idler.forEach(i=>bnGizli.delete(i));if(last)bnCiz(last);if(bnRef)bnPanelCiz(last)},5000)
  bnBildir(mesaj,()=>{clearTimeout(t);idler.forEach(i=>bnGizli.delete(i));if(last)bnCiz(last);if(bnRef)bnPanelCiz(last)})
  if(pn)setTimeout(()=>{bnPanelCiz(last)},220);if(last)setTimeout(()=>bnCiz(last),210)}
const bnYaz=(yol,govde)=>j(yol,{method:'POST',body:JSON.stringify(govde)})
function bnBekleyen(s){return(((s.eylem||{}).liste)||[]).filter(x=>x.sunuldu&&x.durum==='bekliyor'&&!bnGizli.has(x.id))}
function bnBrifing(o,s){const b=(s.brifing||{})[o.id]||{};return b.durum==='hazir'&&b.sonuc?b.sonuc:(o.hazirlik_sonuc||null)}
function bnHazMetin(o,s,hd){const b=(s.brifing||{})[o.id]||{},so=bnBrifing(o,s)
  if(b.durum==='calisiyor')return{c:'eksik',i:'clock',m:`<b>${L('Hazırlanıyor…')}</b>`}
  if(hd==='hazir')return{c:'hazir',i:'check',m:`<b>${L('Hazır.')}</b>${so&&so.ozet?' '+esc(String(so.ozet).slice(0,220)):''}`}
  if(hd==='eksik')return{c:'eksik',i:'uyari',m:`<b>${L('Hazırlık eksik.')}</b> ${L('Bağlam var, brifing hazırlanmadı.')}`}
  return{c:'yok',i:'clock',m:L('Hazırlık henüz yok.')}}
function bnBosGun(){const o=bnSonraki;let t=L('Bugün toplantı yok')
  if(o){const k=goreliKok(o.tarih),gun=k&&k.g===1?L('yarın'):new Date(o.tarih+'T12:00').toLocaleDateString(L('tr-TR'),{weekday:'long'});t+=' · '+L('sıradaki: {g} {s} — {b}',{g:gun,s:o.saat||'',b:o.baslik||L('(başlıksız)')})}
  return`<p class=bosgun>${esc(t)}</p>`}
function bnSerit(s,ol,now){const c=((s.ayarlar||{}).deger||{}).calisma||{},sa=(v,d)=>typeof v==='number'?v/60:typeof v==='string'&&v?parseInt(v,10):d  // mesai: ayarlar.deger.calisma (dakika; eski biçim "09:00")
  let b0=Math.floor(sa(c.bas,8)),b1=Math.ceil(sa(c.bit,18));if(!(b1>b0)||b0<0||b1>24){b0=8;b1=18}
  // eksen mesaiyi ve günün bütün toplantılarını kapsar; kenara dayanan toplantı için bir saat pay (18:00–19:00 toplantısı sağda kırpılmasın), 00–24 dışına çıkmaz
  const bit=o=>o.bitis_saat?bnDk(o.bitis_saat):bnDk(o.saat)+60
  ol.forEach(o=>{b0=Math.min(b0,Math.floor(bnDk(o.saat)/60));b1=Math.max(b1,Math.ceil(bit(o)/60))})
  if(ol.some(o=>bnDk(o.saat)-b0*60<20))b0=Math.max(0,b0-1);if(ol.some(o=>b1*60-bit(o)<20))b1=Math.min(24,b1+1)
  const top=(b1-b0)*60,y=m=>Math.max(0,Math.min(100,(m-b0*60)/top*100)),adim=b1-b0>12?3:2;let saat='';for(let h=b0;h<=b1;h+=adim)saat+=`<span style="left:${y(h*60)}%">${String(h%24).padStart(2,'0')}</span>`
  if((b1-b0)%adim)saat+=`<span style="left:100%">${String(b1%24).padStart(2,'0')}</span>`
  const sira=ol.find(o=>bnDk(o.bitis_saat)>now)
  const bar=ol.map(o=>{const hd=hzDurum(o,s),l=y(bnDk(o.saat)),w=Math.max(y(bnDk(o.bitis_saat))-l,1.2),ad=L(HZW[hd]||HZW.yok)
    return`<button type=button class="sb ${hd} ${bnDk(o.bitis_saat)<=now?'gecti':''} ${o===sira?'sira':''} ${l<22?'sol':l>72?'sag':''}" style="left:${l}%;width:${w}%" data-bn=panel data-ref="t:${esc(o.id)}" aria-label="${esc(o.saat+' '+(o.baslik||'')+', '+ad)}"><span class=nk></span><span class=cb></span><span class=ipu><span class=mono>${esc(o.saat)}</span>${esc(o.baslik||'')}<i></i>${esc(ad)}</span></button>`}).join('')
  const sim=now>=b0*60&&now<=b1*60?`<span class=simdi style="left:${y(now)}%"><span>${String(Math.floor(now/60)).padStart(2,'0')}:${String(now%60).padStart(2,'0')}</span></span>`:''
  return`<div class=serit aria-label="${L('Günün toplantıları')}"><div class=yol><span class=ray></span>${bar}${ol.length?'':`<span class=takvimbos>${L('Takvim boş')}</span>`}${sim}</div><div class=saatler>${saat}</div></div>`}
function bnSatir(x){const kim=x.kim?' — '+esc(x.kim):'',ay=x.ayrinti&&x.tur!=='izin'?esc(ayGor(x.ayrinti).replace(/\s+/g,' ').slice(0,140)):''
  return`<div class=sat data-id="${esc(x.id)}"><button type=button class="onay karar" data-bn=onay data-id="${esc(x.id)}" aria-label="${L('Onayla')}">${ic('check')}</button>
    <div class=m><div class=t>${esc(x.baslik||'')}${kim}</div><div class=a><span class="etiketk karar">${esc(EYT[x.tur]||x.tur)}</span>${ay?`<span>${ay}</span>`:''}</div></div>
    <div class=eylem><button type=button class="b sade" data-bn=panel data-ref="e:${esc(x.id)}">${L('Aç')}</button><button type=button class="b sade" data-bn=ret data-id="${esc(x.id)}">${L('Reddet')}</button></div></div>`}
function bnKartTop(o,s,hd){const hz=bnHazMetin(o,s,hd),ks=o.kisi_sayisi||(o.katilimcilar||[]).length,kim=o.katilimcilar||[],kala=bnDk(o.saat)-(new Date().getHours()*60+new Date().getMinutes())
  const kd=[o.suruyor?L('Şimdi'):kala>0&&kala<=60?L('{n} dk sonra',{n:kala}):'',o.platform?(PL[o.platform]||o.platform):''].filter(Boolean).join(' · ')
  const so=bnBrifing(o,s),dl=hd==='hazir'&&so&&so.ozet?`<button type=button class="b sade" data-bn=dinle data-id="${esc(o.id)}">${ic('hoparlor')}${L('Hazırlık notunu dinle')}</button>`:''
  return`<article class=kart><div class=kbas><span class="saat mono">${esc(o.saat)}</span><span class=ad>${esc(o.baslik||L('(başlıksız)'))}</span><span class="zaman mono">${esc(o.bitis_saat)}${kd?' · '+esc(kd):''}</span></div>
    ${ks?`<div class=kisiler>${bnYuzler(kim)}<span>${esc(kim.length?kim.slice(0,4).map(bnIlk).join(', ')+(ks>4?' '+L('+{n} kişi',{n:ks-4}):''):L('{n} kişi',{n:ks}))}</span></div>`:''}
    <div class="haz ${hz.c}">${ic(hz.i)}<span>${hz.m}</span></div>${gtSatir(o)}${izSatir(o)}${epSatir(o)}
    <div class=keylem><button type=button class="b ana" data-bn=bas data-id="${esc(o.id)}">${ic('video')}${L(o.suruyor?'Toplantıyı başlat':'Başlat')}</button><button type=button class=b data-bn=panel data-ref="t:${esc(o.id)}">${ic('belge')}${L(hd==='hazir'?'Hazırlık':'Hazırla')}</button>${dl}</div></article>`}
function bnOdakOnce(o,s,hd,kala){const hz=bnHazMetin(o,s,hd),kim=o.katilimcilar||[],ks=o.kisi_sayisi||kim.length,so=bnBrifing(o,s)
  const acik=so&&so.acik&&so.acik.length?`<div class=mini><h4>${L('Açık kalanlar')}</h4><ul>${so.acik.slice(0,4).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'',dik=so&&so.dikkat&&so.dikkat.length?`<div class=mini><h4>${L('Dikkat')}</h4><ul>${so.dikkat.slice(0,4).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''
  return`<div class=camkenar><section class=odak aria-label="${L('Toplantıya hazırlık')}"><div class=ust2><span class=sayac>${kala}<small>${L('dk')}</small></span><div class=baslik><span class=eb>${L('Toplantıya hazırlık')} · ${esc(o.saat)}</span><span class=ad>${esc(o.baslik||'')}</span>${ks?`<div class=kisiler>${bnYuzler(kim)}<span>${esc(kim.length?kim.slice(0,4).map(bnIlk).join(', '):L('{n} kişi',{n:ks}))}</span></div>`:''}</div></div><hr>
    <div class="haz ${hz.c}">${ic(hz.i)}<span>${hz.m}</span></div>${gtSatir(o)}${izSatir(o)}${epSatir(o)}${acik||dik?`<div class=ikili>${acik}${dik}</div>`:''}
    <div class=keylem><button type=button class="b ana iri" data-bn=bas data-id="${esc(o.id)}">${ic('video')}${L('Başlat')}</button>${o.baglanti?`<button type=button class="b iri" data-bn=katil data-id="${esc(o.id)}">${L('Suflor.me olmadan katıl')}</button>`:''}<button type=button class="b iri" data-bn=panel data-ref="t:${esc(o.id)}">${ic('belge')}${L(hd==='hazir'?'Hazırlık':'Hazırla')}</button></div></section></div>`}
function bnSonDug(r,ana){const har=!!r.harita;return`<div class=keylem>${har?`<button type=button class="b ${ana?'ana iri':''}" data-bn=son data-id="${esc(r.id)}" data-tur=harita>${ic('harita')}${esc(sonTurAd(r))}</button><button type=button class="b ${ana?'iri':''}" data-bn=son data-id="${esc(r.id)}" data-tur=pdf title="${L('PDF dosyası hazırlar, Finder\'da gösterir')}">${ic('belge')}PDF</button><button type=button class="b sade ${ana?'iri':''}" data-bn=son data-id="${esc(r.id)}" data-tur=pdf data-posta=1>${ic('posta')}${L('Mail taslağına ekle')}</button>`:''}<button type=button class="b ${har?'sade':''} ${ana&&!har?'ana iri':ana?'iri':''}" data-bn=son data-id="${esc(r.id)}" data-tur="">${L('Özeti aç')}</button></div>`}
function bnSonKart(r,ust){const cp=ciktiP(r.cikti),d=new Date(r.at),z=ust?(d.toLocaleTimeString(L('tr-TR'),{hour:'2-digit',minute:'2-digit'})):gunTxt(r.at)
  const sy=ust&&r.cikti?`<div class=sayim>${[['karar','Karar'],['is','İş'],['acik','Açık']].filter(([k])=>r.cikti[k]>0).map(([k,a])=>`<div><b>${r.cikti[k]}</b><span>${esc(k==='is'?isMetin(r.cikti,true):L(a))}</span></div>`).join('')}</div>`:''
  const de=(r.degerlendirme&&!/^(yok|-|—)\.?$/i.test(String(r.degerlendirme).trim())?`<div class=sakin>${esc(r.degerlendirme)}</div>`:'')
    +(r.eposta?`<div class="sakin eposta">${ic('posta')}${L('Bir dahakine e-postayla çözülebilirdi')}: ${esc(r.eposta)}</div>`:'')  // özet yapısındaki eposta_yeterdi (karar çıkmamış, gerekçeli)
  const kb=bnKararBlok(r)  // 6 Kasım (adım 3): özet paragrafı ya da karar maddeleri — ikisi birden değil
  if(ust)return`<section class=kararkart aria-label="${L('Son toplantı')}"><div class=bbas><h2>${esc(L('Son toplantı'))}: ${esc(r.baslik||r.ad)}</h2><span class=sag>${esc(z)}${sy?'':cp.length?' · '+esc(cp.join(', ')):''}</span></div>${sy}${kb||de}${bnSonDug(r,true)}</section>`
  return`<article class=kart><div class=kbas><span class=ad>${esc(r.baslik||r.ad)}</span><span class="zaman mono">${esc(z)}</span></div>${cp.length?`<div class=sakin>${esc(cp.join(' · '))}</div>`:''}${kb||de}${bnSonDug(r,false)}</article>`}
// Türkçede saate ek: dakika sıfırsa saate, değilse dakikaya göre (18:00’de, 09:30’da, 11:15’te); İngilizcede ek yok
const bnSaatEk=s=>{if(DIL==='en')return s;const [h,m]=String(s||'').split(':').map(Number),n=m?m:(h||0),son=n%10||n;return s+'’'+({0:'da',1:'de',2:'de',3:'te',4:'te',5:'te',6:'da',7:'de',8:'de',9:'da',10:'da',20:'de',30:'da',40:'ta',50:'de',60:'ta',70:'te',80:'de',90:'da'}[son]||'de')}
// Paragrafta bir toplantı bir kez anılır: kısa ad (parantez içi atılır; tam ad kartta ve yan panelde), tek toplantıda hazırlık ve "N dakika sonra" aynı cümlede
// ("… toplantın var; hazırlığı hazır."), birden çok toplantıda sıra sözcüğüyle ("İlkinin hazırlığı eksik."; sıra = kalan toplantıların sırası, sıradaki hep ilki)
const bnKisaAd=o=>{const t=String(o.baslik||''),k=t.replace(/\s*\([^()]*\)/g,'').replace(/\s{2,}/g,' ').trim();return k||t}
const bnSiraSoz=i=>[L('ilkinin'),L('ikincisinin'),L('üçüncüsünün'),L('dördüncüsünün'),L('beşincisinin')][i]||''
function bnDurum(s,ol,now,sira,kala,hdS,bek,son,ek){const P=[],kalan=ol.filter(o=>bnDk(o.bitis_saat)>now),ad_=o=>bnVarlik('t:'+o.id,bnKisaAd(o)),adSaat=o=>L('{saat} {ad}',{saat:bnSaatEk(o.saat),ad:ad_(o)})
  const lst=ks=>{const a=ks.slice(0,2).map(adSaat);return ks.length>2?a.join(', ')+' '+L('ve {n} toplantı daha',{n:ks.length-2}):a.join(' '+L('ve')+' ')}  // toplantılar adı ve saatiyle: ilk ikisi + "ve N toplantı daha"
  const bas=t=>t.charAt(0).toLocaleUpperCase(DIL==='en'?'en':'tr')+t.slice(1),birles=(c,k)=>c.replace(/\.$/,'')+'; '+k+'.'  // cümle başı büyük harf (İ) · iki cümle noktalı virgülle
  if(ol.length){const liste=lst(kalan),tek=kalan.length===1,hepsi=kalan.length===ol.length,yakin=!!(sira&&kala!=null&&kala>=0&&kala<=15)
    let c=hepsi?(ol.length===1?L('Bugün {liste} toplantın var.',{liste}):ol.length===2?L('Bugün {liste} toplantıların var.',{liste}):L('Bugün {liste} var.',{liste}))
      :kalan.length?L('Bugün {b} toplantın bitti; sırada {liste} var.',{b:ol.length-kalan.length,liste}):L('Bugünkü {n} toplantın bitti.',{n:ol.length})
    const eksik=kalan.filter(o=>hzDurum(o,s)==='eksik'),hazir=!!(sira&&hdS==='hazir'),kuyruk=[]  // tek toplantıda cümleye eklenen kuyruk; bitmiş toplantı varsa ayrı cümle
    if(tek&&yakin)kuyruk.push(L('{n} dakika sonra başlıyor',{n:kala}));else if(tek&&hazir)kuyruk.push(L('hazırlığı hazır'));else if(tek&&eksik.length)kuyruk.push(L('hazırlığı eksik'))
    else if(!tek&&yakin)kuyruk.push(L('ilki {n} dakika sonra başlıyor',{n:kala}))
    if(kuyruk.length&&hepsi)c=birles(c,kuyruk[0]);P.push(c);if(kuyruk.length&&!hepsi)P.push(bas(kuyruk[0])+'.')
    if(!tek){const ek=eksik.filter(o=>!(yakin&&o===sira)).slice(0,2),sz=ek.map(o=>bnSiraSoz(kalan.indexOf(o)))
      if(ek.length&&sz.every(Boolean))P.push(bas(L('{k} hazırlığı eksik.',{k:sz.join(' '+L('ve')+' ')})));else ek.forEach(o=>P.push(L('{ad} için hazırlık eksik.',{ad:ad_(o)})))
      if(hazir&&!yakin)P.push(bas(L('{k} hazırlığı hazır.',{k:bnSiraSoz(0)})))}}
  if(bek.length)P.push(L('Senden onay bekleyen {x} var.',{x:bnVarlik('bek',L('{n} iş',{n:bek.length}))}))
  {const kt=bnTeyitT(),kg=bnKendiT().filter(x=>x.gecikti)
    if(kt.length)P.push(L('Onayını bekleyen {x} var.',{x:bnVarlik('bek',L('{n} karar',{n:kt.length}))}))
    if(kg.length)P.push(L('Gecikmiş {x} var.',{x:bnVarlik('kendi',L('{n} işin',{n:kg.length}))}))
    else{const bb=bnBeklenen(s),kn=bb.knTum,kb=kn.filter(x=>x.kalan_gun===0).length  // özet başlıktaki "senden N şey bekleniyor" ile çelişmez (bnBeklenen ile aynı küme): gecikmiş yoksa bugün vadeli, o da yoksa açık işlerin sayısı
      if(kb)P.push(L('Bugün vadesi gelen {x} var.',{x:bnVarlik('kendi',L('{n} işin',{n:kb}))}))
      else if(bb.plan){if(bb.kn.length)P.push(L('Bugünün odağında {x} var.',{x:bnVarlik('kendi',L('{n} işin',{n:bb.kn.length}))}))}  // v0.248.0 (16 Kasım): planlı günde N odaktaki işleri sayar
      else if(kn.length)P.push(L('Gecikmiş ya da bugün vadesi gelen işin yok; {x} var.',{x:bnVarlik('kendi',L('{n} açık işin',{n:kn.length}))}))}}
  if(son&&Date.now()-new Date(son.at)<108e5&&ciktiP(son.cikti).length)P.push(L('{ad} bitti: {c}.',{ad:bnVarlik('son',son.baslik||son.ad||''),c:ciktiP(son.cikti).join(', ')}))
  if(!P.length)P.push(L('Bugün senden bekleyen bir şey yok.'))
  if(bnHazir&&!ol.length&&(s.takvim||{}).durum==='ok')P.push(L('Takviminde bugün toplantı yok.'))
  if(ek&&ek.length){if(P.length===1&&/bekleyen bir şey yok|nothing waiting/i.test(P[0]))P.length=0;P.splice(Math.max(2,4-ek.length));P.push(...ek)}  // e-posta ve yakın tarih cümlesi kesilmez (sayaçla aynı sayı görünür)
  return P.slice(0,4).join(' ')}  // Günün özeti kısa kalır: en çok dört cümle
function bnCiz(s){const el=document.getElementById('bgn');if(!el||(s.aktif&&!bnToplantida()))return
  const d=new Date(),now=d.getHours()*60+d.getMinutes(),ol=bnHazir?bnOlay:[],kalan=ol.filter(o=>bnDk(o.bitis_saat)>now),sira=kalan[0]||null,kala=sira?bnDk(sira.saat)-now:null,bek=bnBekleyen(s),sl=(s.son_toplantilar||[]),son=sl[0]||null
  const taze=son&&Date.now()-new Date(son.at)<72e5&&(son.harita||ciktiP(son.cikti).length),odakOnce=sira&&kala>=0&&kala<=15  // taze: son 2 saat
  const sa=d.getHours(),selam=sa<12?L('Günaydın'):sa<18?L('İyi günler'):L('İyi akşamlar'),ad=bnIlk(s.ad),loc=L('tr-TR')
  const tarih=d.toLocaleDateString(loc,{weekday:'long'})+', '+d.toLocaleDateString(loc,{day:'numeric',month:'long'})+' · '+String(sa).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')
  const hdS=sira?hzDurum(sira,s):'',dtgt=kalan.find(o=>{const so=bnBrifing(o,s);return so&&so.ozet&&hzDurum(o,s)==='hazir'}),ses=!(s.ayarlar&&s.ayarlar.deger&&s.ayarlar.deger.konusma===false)
  const sn=dtgt?Math.max(5,Math.round(String(bnBrifing(dtgt,s).ozet).split(/\s+/).length/2.4)):0,dk=sn?Math.max(1,Math.round(sn/60)):0
  const dinliyor=!!bnDin,dusunuyor=prBusy||prD.durum==='dusunuyor'
  const serit=bnHazir&&ol.length?bnSerit(s,ol,now):bnHazir&&bnTakOk?bnBosGun():''  // takvim boşken yarım ekranlık boş şerit yerine tek satır
  const html=`<div class=ana><div class="icerik y-${bnGor}">${bnGor==='kayit'?knCiz():bnGor==='ekip'?ekipIc():bnGor==='gecmis'?gecmisIc(s):bugunIc()}</div></div>`
  if(el.__h===html)return
  const odak=document.activeElement&&el.contains(document.activeElement)?document.activeElement.id:'',deg={};{const g=el.querySelector('#gcAra');if(g)deg.gcAra=g.value}
  const kay=[];for(let n=el;n;n=n.parentElement)if(n.scrollTop>0)kay.push([n,n.scrollTop]);const wy=window.scrollY  // yeniden çizim sayfayı başa atmasın
  el.innerHTML=html;el.__h=html
  kay.forEach(([n,y])=>{if(n.scrollTop!==y)n.scrollTop=y});if(window.scrollY!==wy)window.scrollTo(0,wy)
  {const g=el.querySelector('#gcAra');if(g&&deg.gcAra)g.value=deg.gcAra}
  if(odak){const y=document.getElementById(odak);if(y&&el.contains(y)&&y.matches('input')){y.focus();try{y.setSelectionRange(y.value.length,y.value.length)}catch(e){}}}  // Kararlar ve Geçmiş aramasında yazarken yeniden çizim odağı bozmaz
  if(bnGor==='kayit'||bnGor==='ekip')knYukle()
  if(bnRef)bnPanelCiz(s)
  if(bnGor==='bugun'&&s.gun_plani&&gpGordu!==s.gun_plani.tarih){gpGordu=s.gun_plani.tarih;j('/dusunme',{method:'POST',body:JSON.stringify({islem:'gordu'})}).catch(()=>{})}  // plan Bugün'de görüldü: söz kapısına kabul
  // ---- Bugün (adım 3, onaylı taslak Main): başlık (tarih + "senden N şey bekleniyor", durum hapı) → Günün özeti (Dinle, sayaçlar) → Sıradaki + saat şeridi → Senden beklenenler (≤ 5 + Tümü) → Önemli e-postalar · Yaklaşan tarihler
  function bugunIc(){const bb=bnBeklenen(s),kt=bb.kt,kn=bb.kn,dkk=s.dokum_kontrol,dl=dkk?(dkk.liste||[]).filter(x=>!x.bitti&&!x.geride&&!dkKapali.has(x.ad)).slice(0,3):[]
    const R=[]
    if(s.toplanti_hatirlat&&!toplantidaMi(s))R.push(bsSat({nokta:'vurgu',t:esc(s.toplanti_hatirlat.cumle),a:esc(L('Toplantı hatırlatma')),d:`<button type=button class=b data-bn=thaz data-id="${esc(s.toplanti_hatirlat.id)}">${L('Hazırlık')}</button>${s.toplanti_hatirlat.baglanti?`<button type=button class=b data-bn=that data-id="${esc(s.toplanti_hatirlat.id)}">${L('Katıl')}</button>`:''}`,x:`<button type=button class=em data-bn=thkap data-id="${esc(s.toplanti_hatirlat.id)}" title="${L('Kapat')}" aria-label="${L('Kapat')}">${ic('x')}</button>`}))  // planlı toplantı hatırlatması (aktarici/toplanti-hatirlat.py)
    if(s.proaktif)R.push(bsSat({nokta:'vurgu',t:esc(s.proaktif.cumle),a:esc(L('Toplantı sonrası hatırlatma')),d:`<button type=button class=b data-bn=proakt data-id="${esc(s.proaktif.id)}">${L(s.proaktif.yazma?'Evet, onaya sun':s.proaktif.tur==='gun'?'Birlikte bakalım':'Bakalım')}</button>`,x:`<button type=button class=em data-bn=proakap data-id="${esc(s.proaktif.id)}" title="${L('Sonra')}" aria-label="${L('Sonra')}">${ic('x')}</button>`}))  // toplantı sonrası açık uç hatırlatması (aktarici/toplanti-sonrasi.py)
    R.push(...bek.map(bsEylem),...kt.map(bsKarar),...kn.map(bsIs),...mtbSat(s))
    if(dl.length)R.push(bsSat({nokta:'vurgu',t:esc(L('{baslik} dökümünü kontrol et',{baslik:dl[0].baslik})),a:esc(L('Öncelikli {n} satır · yaklaşık {m} dk',{n:dl[0].oncelikli,m:Math.round(dl[0].tahmin_dk||0)}))+dl.slice(1).map(x=>` · <button type=button class=varlik data-bn=dkac data-t="${esc(x.ad)}" title="${esc(x.baslik)}">${esc(goreliTarih(x.tarih))}</button>`).join(''),e:`<span class="etiket notr">${L('Döküm')}</span>`,d:`<button type=button class=b data-bn=dkac data-t="${esc(dl[0].ad)}">${L('Başla')}</button>`,x:`<button type=button class=em data-bn=dkkapat data-t="${esc(dl[0].ad)}" title="${L('Kapat')}" aria-label="${L('Kapat')}">${ic('x')}</button>`}))  // toplantı sonrası döküm kontrolü (yalnız geliştirici; aktarici/dokum-kontrol.py)
    const N=bb.n,gor=bnBekAcik||R.length<=4?R:R.slice(0,4),tum=bb.nTum,ge=bnGeride()  // v0.248.0 (16 Kasım): Tümü bütün açık işleri sayar (plan odağı dışındakiler dahil)
    const isaret=`<span class="varlikisaret${dinliyor?' dinliyor':''}${dusunuyor?' dusunuyor':''}" id=bnIsaret><span class=nefes aria-hidden=true></span><span class=dalga aria-hidden=true><i></i><i></i><i></i><i></i></span>${dusunuyor?`<span class=dusunce>${L('düşünüyor…')}</span>`:''}</span>`
    const bas=`<div class=sayfab><div class=sbas><span class=tarih>${esc(tarih)}</span><h1>${esc(selam+(ad?' '+ad:''))}${N?esc('. '+L('Bugün senden {n} şey bekleniyor.',{n:N})):''} ${isaret}</h1></div><div class=sag>${bnHap(s)}${sayfaMenu('bugun')}</div></div>`
    // Günün özeti: durum cümleleri (bnDurum) + cevapsız e-posta ve yakın tarih; Dinle hazır brifingi okur; altta sayaç bağlantıları
    const ek=[],epc=epSay(),yk=((ytV&&ytV.tarihler)||[]).find(x=>{const g=goreliKok(x.tarih);return g&&g.g>=0&&g.g<=1&&x.tur!=='etkinlik'})
    const epN=epc  // sayaç ve metin aynı sayı: ozet_sayi = senden cevap bekleyen e-postalar (S262)
    if(epc)ek.push(L('{n} e-posta senden cevap bekliyor.',{n:epc}));if(yk)ek.push(goreliKok(yk.tarih).g?L('Yarın: {m}.',{m:esc(yk.metin)}):L('Bugün: {m}.',{m:esc(yk.metin)}))
    const say=[[bnKendiT().length,'{n} iş','data-bn=git data-g=kayit data-m=is'],[kt.length,'{n} karar','data-bn=git data-g=kayit data-m=karar'],[bek.length,'{n} onay','data-bn=panel data-ref=bek'],[epN,'{n} e-posta','data-bn=epgit'],[kalan.length,'{n} toplantı','data-bn=git data-g=takvim data-m=gun']].filter(x=>x[0]>0).map(([n,m,a])=>`<button type=button class=bag ${a}>${esc(L(m,{n}))}</button>`)
    // Günün planı (aktarici/dusunme.py, günde bir düşünme turu) varsa özet ondan gelir ve odak/dikkat/"doğru mu?" satırları aynı kartta durur; yoksa bugünkü durum cümleleri
    const gp=s.gun_plani&&s.gun_plani.ozet?s.gun_plani:null,gpAcik=bnV?new Set(bnKendi().map(x=>x.id)):null,gpTey=bnV?new Set(bnTeyit().map(x=>x.id)):null  // odaktaki iş / dikkattaki karar bu arada kapandıysa satır gizlenir
    const gpGec=x=>!x.id||(x.kapsam==='kendi'&&gpAcik?gpAcik.has(x.id):x.kapsam==='teyit'&&gpTey?gpTey.has(x.id):true)
    const gpEt=x=>x.yeni?` <span class="etiket notr">${L('Yeni')}</span>`:x.degisti?` <span class="etiket notr">${L('Değişti')}</span>`:''  // yeni/değişti işareti aktarıcıdaki farktan gelir (son açılıştan bu yana)
    const gpEy={onayla:L('Onayla'),yapildi:L('Yapıldı'),taslak:L('Taslağını hazırla'),teyit:L('Teyit et')},gpDug=x=>x.eylem==='teyit'&&x.id?`<button type=button class="b sade" data-bn=panel data-ref="r:${esc(x.id)}">${esc(gpEy.teyit)}</button>`:x.eylem&&gpEy[x.eylem]&&x.id?`<button type=button class="b${x.eylem==='taslak'?' sade':''}" data-bn=gpeylem data-e="${esc(x.eylem)}" data-id="${esc(x.id)}">${esc(gpEy[x.eylem])}</button>`:''  // yalnız var olan onay/taslak yolunu açar; kendiliğinden bir şey göndermez
    const gpSat=(x,nokta,ek)=>bsSat({id:x.id,nokta,t:esc(x.metin)+gpEt(x),a:esc([ek,x.neden,x.kim,x.vade].filter(Boolean).join(' · ')),d:gpDug(x)})
    const gpOdak=gp?(gp.odak||[]).filter(gpGec):[],gpDik=gp?(gp.dikkat||[]).filter(gpGec):[],gpSoru=gp?(gp.soru||[]).filter(x=>!gpBek.has(x.id)):[]
    const dp=gp?esc(gp.ozet):bnDurum(s,ol,now,sira,kala,hdS,bek,son,ek),dmetin=gp?(()=>{let m=gp.ozet;[...gpOdak.map(x=>(x.saat?x.saat+' ':'')+x.metin+(x.neden?'. '+x.neden:'')),...gpDik.map(x=>x.metin)].forEach(c=>{if((m+' '+c).length<1450)m+=' '+(/[.!?]$/.test(c)?c:c+'.')});return m})():(()=>{const t=document.createElement('div');t.innerHTML=dp;return(t.textContent||'').replace(/\s+/g,' ').trim()})()  // Dinle brifing yokken de görünür: kartın düz metni okunur
    bnOzetMetin=dmetin
    const gpGrup=(b,h)=>h?`<div class=gpgrup><h2 class=kb2>${b}</h2><div class=liste>${h}</div></div>`:''
    const gpB=gp?gpGrup(L('Bugünün odağı'),gpOdak.map(x=>gpSat(x,'',x.saat)).join(''))
      +gpGrup(L('Dikkat'),gpDik.map(x=>gpSat(x,'bek','')).join(''))
      +gpGrup(L('Dün öğrendiklerim'),gpSoru.map(x=>bsSat({nokta:'',t:esc(x.metin),d:`<button type=button class=b data-bn=gpdogru data-id="${esc(x.id)}">${L('Doğru')}</button><button type=button class="b sade" data-bn=gpyanlis data-id="${esc(x.id)}">${L('Yanlış')}</button>`})).join('')):''
    // zekâ karnesi: haftada bir kısa kullanıcı puanı (aktarici/dusunme.py "zeka_soru" → zeka.py); yalnız işlev ve 1–5 sayısı kaydedilir
    const zkAd={konus:L('Konuş ve sohbet'),gun_plani:L('Gün planı'),eposta:L('E-posta takibi'),toplanti:L('Toplantı kartları')}
    const zkS=((s.gun_plani&&s.gun_plani.zeka_soru)||[]).filter(i=>zkAd[i]&&!zkBek.has(i))
    const zkB=zkS.length&&!zkBek.has('*')?`<div class=gpgrup><h2 class=kb2>${esc(L('{a} bu hafta ne kadar akıllıydı?',{a:s.asistan||'Marvin'}))}</h2><div class=liste>${zkS.map(i=>bsSat({nokta:'',t:esc(zkAd[i]),a:esc(L('1 = hiç, 5 = çok')),d:[1,2,3,4,5].map(n=>`<button type=button class="b sade" data-bn=zkpuan data-i="${i}" data-p="${n}" aria-label="${esc(zkAd[i]+' '+n)}">${n}</button>`).join('')})).join('')}</div><div class=keylem><button type=button class="b sade" data-bn=zkgec>${L('Şimdi değil')}</button></div></div>`:''
    const dsn=dtgt?sn:Math.max(5,Math.round(dmetin.split(/\s+/).length/2.4)),ddk=Math.max(1,Math.round(dsn/60))
    const ozet=`<section class=ozet aria-label="${L('Günün özeti')}"><div class=obas><h2>${L('Günün özeti')}</h2><div class=keylem>${sira&&bnBrifing(sira,s)?`<button type=button class="b sade" data-bn=panel data-ref="t:${esc(sira.id)}">${L('Brifingi aç')}</button>`:''}${ses&&(dtgt||dmetin)?`<button type=button class="b dinle${dinliyor?' on':''}" data-bn=dinle ${dtgt?`data-id="${esc(dtgt.id)}"`:'data-metin=1'}>${ic(dinliyor?'dur':'oynat')}<span>${dinliyor?L('Durdur'):L('Dinle')}</span><span class=mono>· ${esc(L('~{n} dk',{n:dtgt?dk:ddk}))}</span></button>`:''}</div></div><p>${dp}</p>${gpB}${zkB}${say.length?`<div class=sayac2>${say.join('<span aria-hidden=true>·</span>')}</div>`:''}</section>`
    const siraB=odakOnce?bnOdakOnce(sira,s,hdS,kala)+(serit?`<section class="bolum sira2">${serit}</section>`:''):sira?bsSira(sira,s,serit):serit&&!ol.length?`<section class="bolum sira2" aria-label="${L('Günün toplantıları')}">${serit}</section>`:serit?`<section class="bolum sira2" aria-label="${L('Günün toplantıları')}"><h2 class=kb2>${L('Günün toplantıları')}</h2>${serit}</section>`:''
    const bekB=`<section class="bolum bekl" aria-label="${L('Senden beklenenler')}"><div class=bbas><h2>${L('Senden beklenenler')}</h2>${tum?`<button type=button class=bag data-bn=git data-g=kayit>${esc(L('Tümü · {n}',{n:tum}))}</button>`:''}</div>${R.length?`<div class=liste>${gor.join('')}</div>`:`<p class=sakin>${L('Şu an senden beklenen bir şey yok.')}</p>`}${R.length>4?`<div class=keylem><button type=button class="b sade" data-bn=bekac>${bnBekAcik?L('Daha az göster'):L('{n} tane daha',{n:R.length-4})}</button></div>`:''}`
      +(ge.length?`<div class="keylem geride"><button type=button class="b sade" data-bn=gerac aria-expanded="${bnGerAcik}">${L('Geride kalanlar')} · ${ge.length}</button></div>${bnGerAcik?`<div class=liste>${ge.map(x=>x.tur==='karar'||x.id[0]==='k'?bsKarar(x):bsIs(x)).join('')}</div><div class=sakin>${L('{n} günden eski olanlar burada.',{n:14})}</div>`:''}`:'')+`</section>`
    const epB=epBlok(),ktB=ytBlok()
    // Tek "Bekleyenler" satırı: okunmamış sesli talimat (gelen kutusu) · sözlük önerisi (onay sorusu açık aday) · cevap bekleyen e-posta; sıfırlar yazılmaz, hepsi sıfırsa satır yok. Yeni veri yok: /bugun-veri, /status, /eposta-onemli
    const bkp=[[bnV&&bnV.bekleyen_talimat||0,'{n} talimat','data-bn=panel data-ref=bek'],[(s.sozluk_ogrenme&&s.sozluk_ogrenme.sorulan)||0,'{n} sözlük önerisi','data-bn=dksz'],[epN,'{n} e-posta','data-bn=epgit']].filter(x=>x[0]>0)
    const bkB=bkp.length?`<p class="sakin bekler">${esc(L('Bekleyenler'))}: ${bkp.map(([n,m,a])=>`<button type=button class=bag ${a}>${esc(L(m,{n}))}</button>`).join(' · ')}</p>`:''
    // 19 Kasım (pano sadeleştirme 3. dalga, Y5): en üstte Sıradaki toplantı; ilk ekranda en çok 3 blok, kalanı "Daha fazla" altında katlı (açık/kapalı bnDfzAcik, sayfa içinde)
    const blk=[siraB,ozet,bekB+bkB,epB||ktB?`<div class=ikiblok>${epB}${ktB}</div>`:'',taze?bnSonKart(son,true):'',tzBlok(s),ksBlok(s)].filter(Boolean),dfz=blk.slice(3)
    return bas+blk.slice(0,3).join('')+(dfz.length?`<div class="keylem dahafazla"><button type=button class="b sade" data-bn=dfzac aria-expanded="${bnDfzAcik}">${bnDfzAcik?L('Daha az göster'):L('Daha fazla')+' · '+dfz.length}</button></div>${bnDfzAcik?dfz.join(''):''}`:'')}}
async function knYukle(zorla){if(knYuk||(!zorla&&Date.now()-knT<30000))return;knYuk=true;knT=Date.now();const den=knDen  // S236: deneme (Test) toplantı kayıtları varsayılan gelmez; anahtar açıkken ?deneme=1
  try{const o=await j('/ortak');const ov=o&&o.ok?o:null;if(JSON.stringify(ov)!==JSON.stringify(knOrt)){knOrt=ov;if(last)bnCiz(last)}}catch(e){}  // ortak defter durumu (A7)
  try{const o=await j('/belge-oneri');const ov=o&&o.ok?o:null;if(JSON.stringify(ov)!==JSON.stringify(boV)){boV=ov;if(last)bnCiz(last)}}catch(e){}
  try{const o=await j('/is-kopya');const ov=o&&o.ok?o:null;if(JSON.stringify(ov)!==JSON.stringify(ikV)){ikV=ov;if(last)bnCiz(last)}}catch(e){}  // aynı iş olabilir çiftleri (aktarici/is-kopya.py)
  try{const v=await j('/kayitlar'+(den?'?deneme=1':''));if(den!==knDen){knYuk=false;return knYukle(true)}if(v&&v.ok&&JSON.stringify(v)!==JSON.stringify(knV)){knV=v;if(last)bnCiz(last)}}catch(e){}knYuk=false}
const knTop=d=>((knV||{}).toplantilar||[]).find(t=>t.dosya===d)
function knSuzgec(x){const s=knSuz
  if(s.kisi&&x.kim!==s.kisi)return false;if(s.toplanti&&x.toplanti!==s.toplanti)return false
  if(s.sahip&&x.tur==='is'){const k=!!x.kendi&&!x.dis;if(s.sahip==='ben'?!k:k)return false}  // Benim = senin işlerin (sana atananlar dahil), Ekibin = başkalarınınki
  if(s.durum==='tarihsiz'&&!(x.tur==='is'&&x.tarihsiz))return false
  if(s.ara){const q=s.ara.toLocaleLowerCase('tr');if(!(x.metin+' '+x.kim+' '+x.baslik+' '+(x.toplanti?toplantiAdi(x.toplanti,x.baslik):'')).toLocaleLowerCase('tr').includes(q))return false}
  return true}
const knSira=(a,b)=>((a.durum==='kapandi')-(b.durum==='kapandi'))||((b.gecikti?1:0)-(a.gecikti?1:0))||((a.kalan_gun==null)-(b.kalan_gun==null))||((a.kalan_gun||0)-(b.kalan_gun||0))||String(b.tarih||'').localeCompare(String(a.tarih||''))
