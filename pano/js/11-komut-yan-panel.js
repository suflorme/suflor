// ---- Takvim (adım 2): Gün · Hafta · Ay · Saatler tek yerde; üstte bölümlü seçici ve ⋯ (Elle başlat, Takvimi yenile). Hafta/gün/ay ızgarası #hfs (hfAc), saat dilimleri #sts (stAc)
let tvMod=hfMod;try{const m=localStorage.getItem('tvmod');if(['gun','hafta','ay','saat'].includes(m))tvMod=m}catch(e){}
function tvAc(m){tvMod=m;try{localStorage.setItem('tvmod',m)}catch(e){}
  if(m==='saat'){if(!stAcik)stAc(true)}else{const yeni=hfMod!==m;hfMod=m;try{localStorage.setItem('hfmod',m)}catch(e){}if(!hfAcik)hfAc(true);else if(yeni){hfDetayKapat();hfYukle(true)}}
  kcSec='tv';tvCiz();if(last)kenarCiz(last,document.documentElement.classList.contains('toplantida'))}
function tvCiz(){const e=document.getElementById('tvb');if(!e)return;const ac=hfAcik||stAcik;e.hidden=!ac;if(!ac)return;const m=stAcik?'saat':hfMod
  const h=`<div class="sayfab sik"><div class=sbas><h1>${L('Takvim')}</h1></div><div class=sag><div class=seg role=group aria-label="${L('Görünüm')}">${[['gun',L('Gün')],['hafta',L('Hafta')],['ay',L('Ay')],['saat',L('Saatler')]].map(([k,a])=>`<button type=button data-bn=tvmod data-m=${k} class="${m===k?'on':''}" aria-pressed=${m===k}>${a}</button>`).join('')}</div>${sayfaMenu('takvim')}</div></div>`
  if(e.__h!==h){e.innerHTML=h;e.__h=h}}
document.getElementById('tvb').addEventListener('click',ev=>bnTik(ev))
// ---- Komut penceresi (Command + K) ve sayfa ⋯ menüsü: her yere gitme ve nadir eylemler tek kayıtta. Yazarak süzülür, ok tuşları + Enter, Esc kapatır; kenar çubuğundaki kutu da açar.
// Elle başlat, Prova odası ve Dışa aktar (CSV/JSON) burada ve sayfa ⋯ menüsünde (eskiden Bugün sayfasında ve gizli takvim başlığında).
function kutuYaz(t){const n=document.getElementById('n');if(!n)return;n.value=t;n.focus();try{n.setSelectionRange(t.length,t.length)}catch(e){}n.dispatchEvent(new Event('input',{bubbles:true}))}
async function disaAktar(bicim,b){if(b)b.disabled=true;let r={};try{r=await bnYaz('/disa-aktar',{bicim})}catch(e){}if(b)b.disabled=false;bnBildir(r.ok?L('{n} kayıt yazıldı: {ad}',{n:r.n,ad:r.ad}):L('Dışa aktarılamadı')+(r.err?' — '+r.err:''))}
const takvimKapat=()=>{if(hfAcik)hfAc(false);if(stAcik)stAc(false)}
const KOMUT={
  bugun:{ad:()=>L('Bugün'),i:'gun',g:()=>L('Git'),yap:()=>git('bugun')},
  takvim:{ad:()=>L('Takvim'),i:'takvim',g:()=>L('Git'),ara:()=>L('hafta ay gün'),yap:()=>git('takvim')},
  saatler:{ad:()=>L('Saatler'),i:'saatDunya',g:()=>L('Takvim'),ara:()=>L('saat dilimi şehir'),yap:()=>git('takvim','saat')},
  kayit:{ad:()=>L('Kararlar ve işler'),i:'isler',g:()=>L('Git'),yap:()=>git('kayit')},
  ekip:{ad:()=>L('Ekip'),i:'ekip',g:()=>L('Git'),ara:()=>L('izleme başkaları kimde bekliyor'),yap:()=>git('ekip')},
  gecmis:{ad:()=>L('Geçmiş'),i:'clock',g:()=>L('Git'),ara:()=>L('son toplantılar arşiv araştırmalar'),yap:()=>git('gecmis')},
  ara:{ad:()=>L('Toplantılarda ara'),i:'ara',g:()=>L('Geçmiş'),ara:()=>L('arşiv döküm'),yap:q=>{document.getElementById('ara').value=q||'';arsivAc(true)}},
  dokumler:{ad:()=>L('Dökümler'),i:'dosya',g:()=>L('Geçmiş'),ara:()=>L('tüm toplantılar arşiv'),yap:()=>arsivAc(false)},
  konusma:{ad:()=>L('Konuşma geçmişi'),i:'hist',g:()=>L('Geçmiş'),yap:()=>gecmisAc()},
  elle:{ad:()=>L('Elle başlat'),i:'arti',g:()=>L('Eylem'),ara:()=>L('toplantı başlat yeni'),yap:()=>{takvimKapat();tkForm(null)}},
  yeniis:{ad:()=>L('Yeni iş'),i:'kalem',g:()=>L('Eylem'),ara:()=>L('görev ekle'),yap:()=>kutuYaz(L('Bana iş ekle: '))},
  prova:{ad:()=>L('Prova odası'),i:'sohbet',g:()=>L('Eylem'),ara:()=>L('karar sunum sına'),yap:()=>provaAc()},
  tkyenile:{ad:()=>L('Takvimi yenile'),i:'yenile',g:()=>L('Eylem'),yap:()=>{document.getElementById('tky').click();bnBildir(L('takvim yenileniyor…'));setTimeout(()=>{bnYukle(true);if(hfAcik)hfYukle(false)},2000)}},
  tarihsiz:{ad:()=>knSuz.durum==='tarihsiz'?L('Tüm işleri göster'):L('Yalnız tarihsiz işler'),i:'liste',g:()=>L('Kararlar ve işler'),ara:()=>L('süzgeç vade'),yap:()=>{knSuz.durum=knSuz.durum==='tarihsiz'?'':'tarihsiz';git('kayit')}},
  'disa-csv':{ad:()=>L('Kararları ve işleri dışa aktar (CSV)'),i:'dosya',g:()=>L('Eylem'),yap:()=>disaAktar('csv')},
  'disa-json':{ad:()=>L('Kararları ve işleri dışa aktar (JSON)'),i:'dosya',g:()=>L('Eylem'),yap:()=>disaAktar('json')},
  sohbet:{ad:()=>L('{ad} paneli',{ad:asGor((last||{}).konus)}),i:'sohbet',g:()=>L('Uygulama'),ara:()=>L('asistan sohbet konuş'),yap:()=>shAc(true,true)},  // 19 Kasım (Y1): başlıktaki panel düğmesi kalktı; kutudaki düğme ve ⌘K
  ayar:{ad:()=>L('Ayarlar'),i:'gear',g:()=>L('Uygulama'),yap:()=>ayarAc()},
  izayar:{ad:()=>L('İzleme ayarı'),i:'gear',g:()=>L('Uygulama'),ara:()=>L('monitör dosya'),yap:()=>ayarAc('izleme_dosyasi')},
  yardim:{ad:()=>L('Yardım ve sık sorulanlar'),i:'liste',g:()=>L('Uygulama'),yap:()=>yardimAc()},
  geri:{ad:()=>L('Geri bildirim gönder'),i:'chat',g:()=>L('Uygulama'),yap:()=>document.getElementById('gb').click()}}
const SM={bugun:['elle','prova'],takvim:['elle','tkyenile'],kayit:['tarihsiz','disa-csv','disa-json'],ekip:['izayar'],gecmis:['dokumler','konusma']}
let smAcik=null
function sayfaMenu(y){const ls=SM[y]||[];if(!ls.length)return'';const ac=smAcik===y
  return`<span class=smw><button type=button class=smd data-bn=smenu data-y=${y} aria-haspopup=menu aria-expanded="${ac}" title="${L('Diğer')}" aria-label="${L('Diğer')}">${ic('dahasi')}</button>${ac?`<div class=smp role=menu>${ls.map(k=>`<button type=button role=menuitem class=smi data-bn=kmk data-k="${k}">${ic(KOMUT[k].i)}<span>${esc(KOMUT[k].ad())}</span></button>`).join('')}</div>`:''}</span>`}
function smYeniden(){if(last)bnCiz(last);tvCiz()}
document.addEventListener('click',ev=>{let d=false;if(smAcik&&!ev.target.closest('.smw')){smAcik=null;d=true}if((gcAk||arAk)&&!ev.composedPath().some(e=>e.classList&&e.classList.contains('akw'))){gcAk=null;arAk=null;d=true}if(d)smYeniden()})
document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&(smAcik||gcAk||arAk)){smAcik=null;gcAk=null;arAk=null;smYeniden()}})
let kpI=0,kpLs=[]
{document.body.insertAdjacentHTML('beforeend',`<dialog id=kpd aria-label="${L('Komut penceresi')}"><input id=kpq type=search autocomplete=off spellcheck=false placeholder="${L('Ara ya da komut ver')}" aria-label="${L('Ara ya da komut ver')}" aria-controls=kpl role=combobox aria-expanded=true><div id=kpl role=listbox></div><div class=kpa><span><kbd>↑</kbd><kbd>↓</kbd> ${L('seç')}</span><span><kbd>↵</kbd> ${L('aç')}</span><span><kbd>esc</kbd> ${L('kapat')}</span></div></dialog>`)}
const kpNorm=t=>String(t||'').toLocaleLowerCase('tr').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/ı/g,'i')
function kpSuz(){const q=document.getElementById('kpq').value.trim(),p=kpNorm(q).split(/\s+/).filter(Boolean)
  const ls=Object.entries(KOMUT).filter(([k,c])=>!p.length||p.every(w=>kpNorm(c.ad()+' '+(c.ara?c.ara():'')+' '+c.g()).includes(w))).map(([k,c])=>({k,c,ad:c.ad(),i:c.i,g:c.g()}))
  if(q){ls.push({k:'ara',c:KOMUT.ara,q,ad:L('Toplantılarda ara: {q}',{q}),i:'ara',g:L('Geçmiş')});ls.push({k:'kutu',q,ad:L('Kutuya yaz: {q}',{q}),i:'sohbet',g:L('Asistan')})}
  kpLs=ls;kpI=Math.max(0,Math.min(kpI,ls.length-1));kpCiz()}
function kpCiz(){const l=document.getElementById('kpl');l.innerHTML=kpLs.map((x,i)=>`<button type=button role=option id=kpi${i} class="kpi${i===kpI?' sec':''}" aria-selected="${i===kpI}" data-i=${i}>${ic(x.i)}<span class=kad>${esc(x.ad)}</span><small>${esc(x.g)}</small></button>`).join('')||`<p class=kpb>${L('Sonuç yok')}</p>`
  document.getElementById('kpq').setAttribute('aria-activedescendant','kpi'+kpI);const s=document.getElementById('kpi'+kpI);if(s)s.scrollIntoView({block:'nearest'})}
function kpYap(i){const x=kpLs[i];if(!x)return;document.getElementById('kpd').close();if(x.k==='kutu')return kutuYaz(x.q);x.c.yap(x.q)}
function kpAc(){const d=document.getElementById('kpd');if(d.open){d.close();return}const q=document.getElementById('kpq');q.value='';kpI=0;kpSuz();d.showModal();q.focus()}
{const d=document.getElementById('kpd'),q=document.getElementById('kpq')
  q.addEventListener('input',()=>{kpI=0;kpSuz()})
  q.addEventListener('keydown',ev=>{if(ev.key==='ArrowDown'||ev.key==='ArrowUp'){ev.preventDefault();kpI=(kpI+(ev.key==='ArrowDown'?1:-1)+kpLs.length)%Math.max(1,kpLs.length);kpCiz()}else if(ev.key==='Enter'){ev.preventDefault();kpYap(kpI)}})
  document.getElementById('kpl').addEventListener('click',ev=>{const b=ev.target.closest('.kpi');if(b)kpYap(+b.dataset.i)})
  d.addEventListener('click',ev=>{if(ev.target===d)d.close()})}
document.addEventListener('keydown',ev=>{if((ev.metaKey||ev.ctrlKey)&&!ev.altKey&&!ev.shiftKey&&String(ev.key).toLowerCase()==='k'&&!document.documentElement.matches('.panel,.ayarlar,.yardim')){if(document.querySelector('dialog[open]:not(#kpd)'))return;ev.preventDefault();kpAc()}})
// Gündem taslağı: sıradaki toplantının katılımcılarıyla önceki toplantılardan açık kalan iş/karar/soru (/gundem-taslagi?olay=); kartta "Gündem taslağı: N madde", yan panelde liste, Kopyala, Başlat formunun gündem alanına
async function gtYukle(id){if(gtYukSet.has(id))return;gtYukSet.add(id);let r=null;try{const v=await j('/gundem-taslagi?olay='+encodeURIComponent(id));r=v&&v.ok?v:null}catch(e){}gtV[id]=r;if(last)bnCiz(last)}
function gtSatir(o){const g=gtV[o.id];if(g===undefined){gtYukle(o.id);return''}if(!g||!(g.maddeler.length||(g.ek_oneri||[]).length))return''
  const ek=(g.ek_oneri||[]).length?` <span class=alt2>${esc(L('Ek öneri: {n}',{n:g.ek_oneri.length}))}</span>`:''
  const bas=g.davet?L('Davet gündemi: {n} madde',{n:g.maddeler.length}):L('Gündem taslağı: {n} madde',{n:g.maddeler.length})
  const y=g.gundem_yuk,yuk=y&&y.fazla_dk>0?`<div class="haz eksik gyuk" title="${esc((y.ertelenebilir||[]).join(' · '))}">${ic('clock')}<span>${esc(L('Gündem {t} dk tutar, toplantı {m} dk — {n} maddeyi ertelemeyi düşün',{t:y.tahmini_dk,m:y.toplanti_dk,n:(y.ertelenebilir||[]).length}))}</span></div>`:''
  return`<div class="haz gundem">${ic('liste')}<span><b>${bas}</b> ${esc(g.maddeler.slice(0,2).map(m=>m.metin).join(' · '))}${g.maddeler.length>2?' …':''}${ek}</span><button type=button class="b sade" data-bn=gtac data-id="${esc(o.id)}">${L('Aç')}</button></div>${yuk}`}
// "Bu toplantı e-postayla çözülebilir": takvim olayının davet notundan yalnız GÜÇLÜ işaret (aktarıcı /takvim eposta alanı; yapi.eposta_isaret) — Taslak mevcut posta yolunu (postaUrl) kullanır
function epSatir(o){const e=o.eposta;if(!e||!e.guclu)return''
  return`<div class="sakin eposta">${ic('posta')}<span>${L('Bu toplantı e-postayla çözülebilir')}: ${esc(e.neden||'')} <button type=button class="b sade" data-bn=eptaslak data-id="${esc(o.id)}">${L('Taslak')}</button></span></div>`}
async function epTaslakAc(o){const e=o&&o.eposta;if(!e||!e.guclu)return
    const md=[L('Merhaba,'),'',L('{t} için gündem bilgi paylaşımından ibaret; toplantı yerine bu e-postayla ilerleyelim:',{t:o.baslik||''}),'',...(e.maddeler||[]).map(m=>'- '+m),'',L('Sorusu olan yazsın; gerekirse kısa bir görüşme ayarlarız.')].join('\n')
    const p=postaUrl({md,baslik:o.baslik||'',alicilar:e.alicilar||[]},(e.alicilar||[]).length?'k':'');if(p.kisa)try{await navigator.clipboard.writeText(p.duz)}catch(x){}brAc(p.u,p.yeni)}
// Süren toplantının panosunda aynı uyarı (S226): toplantının takvim kaydında (oto_toplanti.olay ya da aynı ad) davet notundan güçlü "e-postayla çözülebilir" işareti varsa, toplantı başında (ilk 20 dk) sade bir kart; ✕ ile kapanır
const epKapali=new Set()
function epCanli(s){if(!s.aktif)return null;const t=s.toplanti||{},oid=(s.oto_toplanti||{}).olay,ad=String(t.ad||'').trim().toLowerCase()
  const o=(bnOlay||[]).find(x=>oid&&x.id===oid)||(ad?(bnOlay||[]).find(x=>String(x.baslik||'').trim().toLowerCase()===ad):null)
  if(!o||!o.eposta||!o.eposta.guclu||epKapali.has(o.id))return null
  if(t.bas){const d=new Date(),k=d.getHours()*60+d.getMinutes()-bnDk(t.bas);if((k<0?k+1440:k)>20)return null}return o}
function renderEposta(s){const sec=document.getElementById('eps');if(!sec)return;const o=epCanli(s);sec.hidden=!o;if(!o){sec.dataset.id='';return}
  sec.dataset.id=o.id;setH(sec,`<div class=epk>${ic('posta')}<div class=epm><b>${L('Bu toplantı e-postayla çözülebilir')}</b><span>${esc(o.eposta.neden||'')}</span></div><button type=button class="b sade" data-ep=taslak>${L('Taslak')}</button><button type=button class="gh ib" data-ep=kapat aria-label="${L('Kapat')}">${ic('x')}</button></div>`)}
document.getElementById('eps').addEventListener('click',ev=>{const b=ev.target.closest('[data-ep]');if(!b)return;const id=document.getElementById('eps').dataset.id,o=bnOlay.find(x=>x.id===id)
  if(b.dataset.ep==='kapat'){epKapali.add(id);if(last)renderEposta(last)}else epTaslakAc(o)})
const REPLIKSVG='<svg class=replik viewBox="0 0 64 64" aria-hidden=true width=24 height=24><rect width="64" height="64" rx="15" fill="#175E46"/><g transform="translate(0 -3.3)"><path fill="#F1E6CF" d="M23.50 37.60A7.60 7.60 0 1 1 31.10 30.38C31.48 39.50 26.16 45.58 18.56 48.24C23.65 44.44 25.17 40.79 23.50 37.60Z"/><path fill="#C9973A" d="M42.50 37.60A7.60 7.60 0 1 1 50.10 30.38C50.48 39.50 45.16 45.58 37.56 48.24C42.65 44.44 44.17 40.79 42.50 37.60Z"/></g></svg>'
// ---- yan panel, bildirim ----
{const b=document.body;b.insertAdjacentHTML('beforeend',`<div id=bnPerde hidden></div><div id=bnPanel role=dialog aria-label="${L('Ayrıntı')}" aria-hidden=true></div><div id=bnBild role=status><span id=bnBildM></span><button type=button id=bnGeri>${L('Geri al')}</button></div>`)}
const bnE=id=>document.getElementById(id)
function bnBildir(m,geri){bnE('bnBildM').textContent=m;bnGeri=geri||null;bnE('bnGeri').hidden=!geri;bnE('bnBild').classList.add('acik');clearTimeout(bnBildT);bnBildT=setTimeout(()=>bnE('bnBild').classList.remove('acik'),5000)}
function bnPanelCiz(s,zorla){const p=bnE('bnPanel');if(!bnRef||!s)return;let h=''
  const kn=bnRef.startsWith('r:');p.classList.toggle('kns',kn);document.documentElement.classList.toggle('kn-yan',kn&&bnGor==='kayit')
  if(kn&&!zorla&&emHedef==='yan'&&emMod&&p.__h)return  // açık form (ertele, ata, böl…) yazarken yenileme silmesin
  const blok=(t,ls)=>ls&&ls.length?`<div class=blok><h4>${esc(t)}</h4><ul>${ls.map(x=>`<li><span class=mt>${esc(x)}</span></li>`).join('')}</ul></div>`:''
  const bas=(tur,ad,alt)=>`<div class=pb><div><div class=eb>${esc(tur)}</div><h2>${esc(ad)}</h2>${alt?`<div class=alt2>${esc(alt)}</div>`:''}</div><button type=button class=ikon data-bn=kapat aria-label="${L('Kapat')}">${ic('x')}</button></div>`
  const isListe=(ls,kim)=>ls.length?`<div class="ince pnl">${ls.map(x=>knSatir(x,{pn:1})).join('')}</div>`:`<p class=alt2>${L('Açık iş yok.')}</p>`
  if(kn)h=knAyrinti(bnRef.slice(2))
  else if(bnRef==='kendi'){const ls=bnKendiT(),ge=bnKendi().filter(x=>x.geride);h=bas(L('İşlerin'),L('Senin açık işlerin'),L('{n} iş',{n:ls.length}))+isListe(ls)+(ge.length?`<div class=blok><h4>${L('Geride kalanlar')}</h4>${isListe(ge)}</div>`:'')}
  else if(bnRef==='bsk'){const ls=bnBaskasi();h=bas(L('Başkalarında'),L('Başkalarından beklediklerin'),L('{n} iş',{n:ls.length}))+isListe(ls,true)}
  else if(bnRef.startsWith('k:')){const ad=bnRef.slice(2),ls=[...bnKendi(),...bnBaskasi()].filter(x=>x.kim===ad);h=bas(L('Kişi'),ad,L('{n} açık iş',{n:ls.length}))+isListe(ls)}
  else if(bnRef==='bek'){const bk=bnBekleyen(s),kt=bnTeyitT(),kn=bnKendiT().filter(x=>x.gecikti||bnYakin(x)||x.atama_yeni);h=bas(L('Bekleyen işler'),L('Senden onay bekleyen'),L('{n} iş',{n:bk.length}))+`<div class=blok><ul>${bk.map(x=>`<li><span class=mt>${esc(x.baslik||'')}${x.kim?' — '+esc(x.kim):''}</span><span class=keylem><button type=button class="b ana" data-bn=onay data-id="${esc(x.id)}" data-pn=1>${L('Onayla')}</button><button type=button class="b sade" data-bn=ret data-id="${esc(x.id)}" data-pn=1>${L('Reddet')}</button></span></li>`).join('')}</ul></div>`+(kt.length?`<div class=blok><h4>${L('Onayını bekleyen kararlar')}</h4><ul>${kt.map(x=>`<li><span class=mt>${esc(x.metin)}</span><span class=keylem><button type=button class="b ana" data-bn=kararonay data-id="${esc(x.id)}" data-pn=1>${L('Onayla')}</button></span></li>`).join('')}</ul></div>`:'')+(kn.length?`<div class=blok><h4>${L('Süresi yaklaşan işlerin')}</h4>${isListe(kn)}</div>`:'')+(bk.length||kt.length||kn.length?'':`<p class=alt2>${L('Bekleyen iş kalmadı.')}</p>`)}
  else if(bnRef.startsWith('e:')){const x=(((s.eylem||{}).liste)||[]).find(y=>y.id===bnRef.slice(2));h=!x?bas(L('Bekleyen iş'),L('Bulunamadı')):bas(EYT[x.tur]||x.tur,x.baslik||'',x.kim||'')+(ayGor(x.ayrinti)&&x.tur!=='izin'?`<div class=blok><p style="white-space:pre-wrap">${esc(ayGor(x.ayrinti).slice(0,1500))}</p></div>`:'')+(x.durum==='bekliyor'?`<div class=keylem><button type=button class="b ana" data-bn=onay data-id="${esc(x.id)}" data-pn=1>${L('Onayla')}</button><button type=button class=b data-bn=ret data-id="${esc(x.id)}" data-pn=1>${L('Reddet')}</button></div>`:'')}
  else if(bnRef.startsWith('d:')){const ad=bnRef.slice(2),d=((bnV||{}).dis||[]).find(x=>x.ad===ad)||{kayitlar:[],acik:0}
    h=bas(L('Başka defter'),ad,L('{n} açık kayıt',{n:d.acik||0}))+(d.kayitlar.length?`<div class=blok><ul>${d.kayitlar.map(x=>`<li><span class=mt>${esc(x.metin)}${x.sahip?' — '+esc(x.sahip):''}</span>${x.vade?goreliSpan(x.vade,'vade',true):''}</li>`).join('')}</ul></div>`:`<p class=alt2>${L('Açık kayıt yok.')}</p>`)+`<p class=alt2>${L('Yalnız okunur; değişiklik o defterde yapılır.')}</p>`}
  else if(bnRef==='iz'||bnRef.startsWith('iza:'))h=izPanel(bnRef,bas)
  else if(bnRef.startsWith('g:')){const id=bnRef.slice(2),o=bnOlay.find(x=>x.id===id),g=gtV[id],dv=!!(g&&g.davet),eo=g&&g.ek_oneri||[]
    const ekb=eo.length?`<div class=blok><h4>${L('Ek öneri')}</h4><ul>${eo.map(x=>`<li><span class="mt alt2">${esc(x.metin||'')}${x.neden?`<small style="display:block">${esc(x.neden)}</small>`:''}</span></li>`).join('')}</ul></div>`:''
    h=bas(dv?L('Davet gündemi'):L('Gündem taslağı'),o?o.baslik||'':'',g?L('{n} madde',{n:g.maddeler.length}):'')+(g&&g.maddeler.length?`<div class=blok><ul>${g.maddeler.map(m=>`<li><span class=mt>${esc(m.satir)}${m.baslik?`<small class=alt2 style="display:block">${esc(m.baslik)}</small>`:''}</span></li>`).join('')}</ul></div>${ekb}<div class=keylem><button type=button class="b ana" data-bn=gtbas data-id="${esc(id)}">${L('Başlat’ta gündem olarak kullan')}</button><button type=button class=b data-bn=gtkopya data-id="${esc(id)}">${L('Kopyala')}</button></div>${dv?'':`<p class=alt2>${L('Önceki toplantılardan bu katılımcılarla açık kalanlar; Başlat formunda düzenleyebilirsin.')}</p>`}`:ekb+`<p class=alt2>${L('Bu katılımcılarla açık kalan kayıt yok.')}</p>`)}
  else if(bnRef==='son'){const r=(s.son_toplantilar||[])[0];h=!r?bas(L('Son toplantı'),L('Bulunamadı')):bas(L('Toplantı'),r.baslik||r.ad,gunTxt(r.at))+blok(L('Çıktı'),ciktiP(r.cikti))+(r.degerlendirme?`<div class=blok><p>${esc(r.degerlendirme)}</p></div>`:'')+(r.oneri?`<div class=blok><h4>${L('Öneri')}</h4><p>${esc(r.oneri)}</p></div>`:'')+blok(r.tazi_etiket?r.tazi_etiket+' · '+L('Tazı notu'):'',(r.tazi||[]).map(x=>x.satir))+bnSonDug(r,false)}
  else if(bnRef.startsWith('tz:')){const f=bnRef.slice(3),li=((s.tazi||{}).raporlar||[]).find(y=>y.dosya===f),k=tzDetay[f];if(k===undefined||(k&&li&&k.t!==li.t)){tzDetay[f]=false;tzDetayAl(f)}  // dosya aynı gün yenilendiyse (t değişti) yeniden alınır
    const x=k||{dosya:f,tur:'',t:0};h=!k?bas(L('Tazı raporu'),k===false?L('Yükleniyor…'):L('Bulunamadı')):bas(L('Tazı raporu'),tzAd(x),goreliTarih(tzTarih(x)))+`<div class="blok armetin">${arMd(k.metin)}</div>`+tzEylem(f)}
  else if(bnRef.startsWith('ar:')){const id=bnRef.slice(3),k=arDetay[id];if(k===undefined){arDetay[id]=false;arDetayAl(id)}
    h=!k?bas(L('Araştırma'),k===false?L('Yükleniyor…'):L('Bulunamadı')):bas(L('Araştırma'),k.konu||'',[goreliTarih(k.at),L('{n} kaynak',{n:(k.kaynaklar||[]).length})].filter(Boolean).join(' · '))+`<div class="blok armetin">${arMd(k.metin)}</div>`
      +((k.kaynaklar||[]).length?`<div class=blok><h4>${L('Kaynaklar')}</h4><ul>${k.kaynaklar.map(x=>`<li><span class=mt>${/^https?:\/\//.test(x.url||'')?`<a href="${esc(x.url)}" target=_blank rel="noopener noreferrer">${esc(x.baslik||x.url)}</a>`:esc(x.baslik||'')}</span>${x.tarih?`<span class=vade>${esc(x.tarih)}</span>`:''}</li>`).join('')}</ul></div>`:'')
      +((k.uyari||[]).length?`<div class=blok><h4>${L('Uyarılar')}</h4><ul>${k.uyari.map(u=>`<li><span class=mt>${esc(typeof u==='string'?u:JSON.stringify(u))}</span></li>`).join('')}</ul></div>`:'')}
  else if(bnRef.startsWith('t:')){const o=bnOlay.find(x=>x.id===bnRef.slice(2));if(!o)h=bas(L('Toplantı'),L('Bulunamadı'));else{const hd=hzDurum(o,s),hz=bnHazMetin(o,s,hd),so=bnBrifing(o,s),b=(s.brifing||{})[o.id]||{},ks=o.kisi_sayisi||(o.katilimcilar||[]).length
    h=bas(L('Toplantı'),o.baslik||L('(başlıksız)'),[o.saat+'–'+o.bitis_saat,ks?L('{n} kişi',{n:ks}):'',o.platform?(PL[o.platform]||o.platform):''].filter(Boolean).join(' · '))
     +`<div class=blok><h4>${L('Hazırlık')}</h4><p>${hz.m}</p>${b.durum==='hata'?`<p>${esc(b.hata||L('Brifing hazırlanamadı'))}</p>`:''}</div>`
     +(so?blok(L('Güncel veri'),so.veri)+blok(L('Dikkat'),so.dikkat)+blok(L('Açık kalanlar'),so.acik)+blok(so.dis_etiket||L('Dış taraf'),so.dis_taraf)+blok(L('Geçmişte'),so.gecmis):'')+blok(L('Katılımcılar'),o.katilimcilar)
     +`<div class=keylem><button type=button class="b ana" data-bn=bas data-id="${esc(o.id)}">${L('Başlat')}</button><button type=button class=b data-bn=hazirla data-id="${esc(o.id)}" ${b.durum==='calisiyor'?'disabled':''}>${L(b.durum==='calisiyor'?'Hazırlanıyor…':hd==='hazir'?'Yeniden hazırla':'Hazırla')}</button>${so&&so.ozet?`<button type=button class=b data-bn=dinle data-id="${esc(o.id)}">${ic('hoparlor')}${L('Dinle')}</button>`:''}</div>`
     +(b.durum==='hazir'?`<div class=blok><h4>${L('Brifingi dışarı aktar')}</h4><div class=keylem>${[['pdf','PDF'],['kopyala',L('Kopyala')],['md',L('Dosya (.md)')],['mail-o',L('E-posta taslağı')]].map(([k,a])=>`<button type=button class="b sade" data-ak=${k} data-kay="br:${esc(o.id)}">${esc(a)}</button>`).join('')}</div></div>`:'')}}
  if(p.__h!==h){p.innerHTML=h;p.__h=h}}
function bnPanelAc(ref){bnRef=ref;bnPanelCiz(last);const p=bnE('bnPanel');p.classList.add('acik');p.setAttribute('aria-hidden','false');bnE('bnPerde').hidden=false;const k=p.querySelector('.ikon');if(k)k.focus()}
function bnPanelKapat(){bnRef=null;if(emHedef==='yan'){emKid='';emV=null;emMod=''}document.documentElement.classList.remove('kn-yan');bnE('bnPanel').classList.remove('kns');if(last&&bnGor==='kayit')bnCiz(last);const p=bnE('bnPanel');p.classList.remove('acik');p.setAttribute('aria-hidden','true');bnE('bnPerde').hidden=true;kenarCekmece(false)}
// işaretle: satır 200 ms'de kapanır, karar 5 sn sonra gider; Geri al bu sürede satırı geri getirir
function bnOnayla(id,tur,pn){const x=(((last||{}).eylem||{}).liste||[]).find(y=>y.id===id);if(!x||bnGizli.has(id))return;bnGizli.add(id)
  const sat=document.querySelector(`#bgn .sat[data-id="${CSS.escape(id)}"]`);if(sat){const h=sat.offsetHeight;sat.style.height=h+'px';void sat.offsetHeight;sat.classList.add('kapan');sat.style.height='0px'}
  const t=setTimeout(async()=>{await eylemKarar(id,tur);bnGizli.delete(id);if(last)bnCiz(last)},5000)
  bnBildir(tur==='onaylandi'?L('Onaylandı: {t}',{t:x.baslik||''}):L('Reddedildi: {t}',{t:x.baslik||''}),()=>{clearTimeout(t);bnGizli.delete(id);if(last)bnCiz(last)})
  if(pn)setTimeout(()=>{bnPanelCiz(last)},220);if(last)setTimeout(()=>bnCiz(last),210)}
function bnDinleBit(){bnDin=null;clearTimeout(bnDinT);if(last)bnCiz(last)}
let bnDinT=null
let bnDinMetin=''
// Dinle: brifing hazırsa eski yol {olay, dinle}; hazır brifing yokken kartın düz metni {dinle, metin} ile okunur (aktarıcı yerel ses kuyruğu). İkinci basış susar; toplantıda ok:false.
async function bnDinle(id,metin){const yaz=metin?(bnOzetMetin||(document.querySelector('#bgn .ozet p')||{}).innerText||'').replace(/\s+/g,' ').trim():''
  if(bnDin){const o=bnDin,m=bnDinMetin;bnDinleBit();try{await j('/brifing',{method:'POST',body:JSON.stringify(o==='ozet'?{dinle:true,metin:m}:{olay:o,dinle:true})})}catch(e){}return}
  if(metin&&!yaz)return
  bnDin=metin?'ozet':id;bnDinMetin=yaz;if(last)bnCiz(last);let r={};try{r=await j('/brifing',{method:'POST',body:JSON.stringify(metin?{dinle:true,metin:yaz}:{olay:id,dinle:true})})}catch(e){}
  if(!r.ok){bnDinleBit();geciciDurum(L('Brifing okunamadı'),r.err||L('Ses kapalı (ayar konusma) ya da brifing hazır değil'));return}
  if(r.ses===false){bnDinleBit();return}
  const so=metin?{ozet:yaz}:bnBrifing(bnOlay.find(o=>o.id===id)||{},last||{}),sn=so&&so.ozet?Math.round(String(so.ozet).split(/\s+/).length/2.4)+3:20;bnDinT=setTimeout(bnDinleBit,sn*1000)}
// "n e-posta" bağlantısı: Önemli e-postalar bloğuna kaydırır (yoksa listeyi tazeleyip bir kez daha dener); kısa vurgu. Kaydırma tarayıcıya bırakılmaz: bölüm değişmeden önce yeniden çizim akıcı kaydırmayı keserse (WKWebView) sayfa başa dönerdi.
function bnEpGit(dene){if(!document.getElementById('bnEp')&&!bnDfzAcik&&bnGor==='bugun'&&last){bnDfzAcik=true;bnCiz(last)}  // e-posta bloğu "Daha fazla" altındaysa önce açılır
  const e=document.getElementById('bnEp');if(!e){if(!dene)bnEkYukle(true).then(()=>setTimeout(()=>bnEpGit(true),400));return}
  let k=e.parentElement;while(k&&k!==document.body&&k.scrollHeight<=k.clientHeight+2)k=k.parentElement
  const kutu=k&&k!==document.body&&k!==document.documentElement?k:(document.scrollingElement||document.documentElement),r=e.getBoundingClientRect(),ust=kutu===document.scrollingElement||kutu===document.documentElement?0:kutu.getBoundingClientRect().top
  kutu.scrollTo({top:Math.max(0,kutu.scrollTop+r.top-ust-24),behavior:'auto'});e.classList.remove('yeni');void e.offsetWidth;e.classList.add('yeni');setTimeout(()=>e.classList.remove('yeni'),2600)}
async function bnTik(ev){{const ak=ev.target.closest('#bgn .akp button[data-ak],#bnPanel button[data-ak]');if(ak){akYap(ak.dataset.ak,ak);if(ak.dataset.ak!=='kopyala'&&(gcAk||arAk)){gcAk=null;arAk=null;if(last)bnCiz(last)}return}
    const so=ev.target.closest('#bgn .akp [data-son]');if(so){gcAk=null;if(last)bnCiz(last);sonIs(so.dataset.son,so.dataset.tur||'',!!so.dataset.posta);return}}  // Geçmiş satırının dışa aktar menüsü, yan paneldeki brifing dışa aktarma
  const b=ev.target.closest('[data-bn]');if(!b)return;const a=b.dataset.bn,id=b.dataset.id
  if(a==='git')return git(b.dataset.g,b.dataset.m)
  if(a==='komut')return kpAc()
  if(a==='smenu'){smAcik=smAcik===b.dataset.y?null:b.dataset.y;return smYeniden()}
  if(a==='kmk'){smAcik=null;smYeniden();const c=KOMUT[b.dataset.k];if(c)c.yap();return}
  if(a==='tvmod')return tvAc(b.dataset.m)
  if(a==='gcak'){gcAk=gcAk===id?null:id;arAk=null;if(last)bnCiz(last);return}
  if(a==='arak'){arAk=arAk===id?null:id;gcAk=null;if(last)bnCiz(last);return}
  if(a==='aris')return arIsAc(id)
  if(a==='arot')return arOturum(id,b.dataset.h)
  if(a==='aras')return arAsistan(id,b.dataset.a)
  if(a==='argiz')return arGizle(id,true)
  if(a==='argos')return arGizle(id,false)
  if(a==='argz'){arGzAcik=!arGzAcik;if(arGzAcik){arGz=null;arGzYukle()}if(last)bnCiz(last);return}
  if(a==='mailac'){b.disabled=true;let r={};try{r=await bnYaz('/mail-ac',{})}catch(e){}b.disabled=false;bnBildir(r&&r.ok?L('Mail açılıyor; yeni iletiler birazdan gelir'):L('Mail açılamadı'));return}
  if(a==='tzac'){tzAcik=!tzAcik;b.setAttribute('aria-expanded',tzAcik);const l=document.getElementById('tzliste');if(l)l.hidden=!tzAcik;return}  // yeniden çizim yok: kaydırma yerinde
  if(a==='epdus'){epDusAcik=!epDusAcik;try{localStorage.setItem('epdus',epDusAcik?'1':'0')}catch(e){}b.setAttribute('aria-expanded',epDusAcik);const l=document.querySelector('#bnEp .epdusl');if(l)l.hidden=!epDusAcik;return}  // yeniden çizim yok: kaydırma yerinde
  if(a==='epsec'){epSec=id;epSecUygula(id);return}  // yeniden çizim yok: kaydırma konumu ve odak yerinde kalır
  if(a==='eptas')return epIslem('taslak',id,b)
  if(a==='epert')return epIslem('ertele',id,b)
  if(a==='epkisi')return epIslem('onemli_kisi',id,b)
  if(a==='epnone')return epIslem('onemsiz_gonderen',id,b)
  if(a==='epyok')return epIslem('yoksay',id,b)
  if(a==='ktkut')return ytKutla(b)
  if(a==='epgit')return bnEpGit()
  if(a==='panel')return bnPanelAc(b.dataset.ref)
  if(a==='emenu')return emAc(b.dataset.kid)
  if(a==='ikbirlestir')return ikIsle(id,'birlestir')
  if(a==='ikayri')return ikIsle(id,'ayri')
  if(a==='ikgeri')return ikIsle(id,'geri_al')
  if(a==='ontum'){onTum=!onTum;if(last)bnCiz(last);return}
  if(a==='bokabul')return boIsle(id,'kabul')
  if(a==='bored')return boIsle(id,'reddet')
  if(a==='kapat')return bnPanelKapat()
  if(a==='menu')return kenarCekmece(true)
  if(a==='onay')return bnOnayla(id,'onaylandi',!!b.dataset.pn)
  if(a==='ret')return bnOnayla(id,'reddedildi',!!b.dataset.pn)
  if(a==='dinle')return bnDinle(id,b.dataset.metin==='1')
  if(a==='isbit')return bnYap([id],L('İş yapıldı olarak işaretlendi'),()=>bnYaz('/is-durum',{id,durum:'yapildi'}))
  if(a==='sorubit')return bnYap([id],L('Cevaplandı olarak işaretlendi'),()=>bnYaz('/kayit-eylem',{id,eylem:'cevaplandi'}))
  if(a==='kararonay')return bnIsle([id],L('Karar onaylandı'),()=>bnYaz('/karar-onay',{idler:[id]}),!!b.dataset.pn)
  if(a==='kararlar'){const idler=String(b.dataset.idler||'').split(',').filter(Boolean);return bnIsle(idler,L('{n} karar onaylandı',{n:idler.length}),()=>bnYaz('/karar-onay',{idler}))}
  if(a==='thaz'||a==='that'||a==='thkap'){b.disabled=true;j('/toplanti-hatirlat',{method:'POST',body:JSON.stringify({islem:a==='thaz'?'hazirlik':a==='that'?'ac':'kapat',id})}).catch(()=>{});if(a==='thkap'&&last)last.toplanti_hatirlat=null;if(last)bnCiz(last);return}
  if(a==='proakt'||a==='proakap'){b.disabled=true;j('/proaktif',{method:'POST',body:JSON.stringify({islem:a==='proakt'?'sor':'kapat',id})}).catch(()=>{});if(last&&last.proaktif)last.proaktif=null;if(last)bnCiz(last);return}
  if(a==='gpeylem'){const e=b.dataset.e  // Günün özeti maddesinin eylem düğmesi: var olan uçlar (/karar-onay, /is-durum; taslak = /kayit-eylem eposta, yalnız açılır)
    if(e==='onayla')return bnIsle([id],L('Karar onaylandı'),()=>bnYaz('/karar-onay',{idler:[id]}))
    if(e==='yapildi')return bnIsle([id],L('İş yapıldı olarak işaretlendi'),()=>bnYaz('/is-durum',{id,durum:'yapildi'}))
    if(e==='taslak'){b.disabled=true;let r={};try{r=await bnYaz('/kayit-eylem',{id,eylem:'eposta'})}catch(x){}b.disabled=false
      if(r&&r.ok&&r.taslak){emTaslakAc(r.taslak);bnBildir(L('Taslak açıldı; göndermek sende'))}else bnBildir(L('Yapılamadı.'));return}
    return}
  if(a==='gpdogru'||a==='gpyanlis'){b.disabled=true;gpBek.add(id);if(last)bnCiz(last);j('/dusunme',{method:'POST',body:JSON.stringify({islem:a==='gpdogru'?'dogru':'yanlis',id})}).catch(()=>{});bnBildir(a==='gpdogru'?L('Not aldım, teşekkürler'):L('Tamam, bunu geçersiz saydım'));return}  // günün planındaki "Doğru mu?" (aktarici/dusunme.py): Doğru → onaylı, Yanlış → geçersiz
  if(a==='zkpuan'||a==='zkgec'){const i=b.dataset.i||'*';zkBek.add(i);if(last)bnCiz(last);j('/dusunme',{method:'POST',body:JSON.stringify(a==='zkpuan'?{islem:'zeka_puan',islev:i,puan:+b.dataset.p}:{islem:'zeka_gec'})}).catch(()=>{});if(a==='zkpuan')bnBildir(L('Not aldım, teşekkürler'));return}  // zekâ karnesi kullanıcı puanı
  if(a==='dksz'){let u='/dokum-kontrol?sozluk=1';try{const r=await bnYaz('/tek-kullanim',{}),m=r&&r.url&&String(r.url).match(/[?&]t=([0-9a-f]{32})/);if(m)u+='&t='+m[1]}catch(e){}  // 14 Kasım: Bekleyenler → sözlük önerileri (döküm kontrolü sayfası, bütün toplantılar)
    return yerelSayfaAc(u,'dokum_kontrol')}
  if(a==='dkac'){let u='/dokum-kontrol?top='+encodeURIComponent(b.dataset.t);try{const r=await bnYaz('/tek-kullanim',{}),m=r&&r.url&&String(r.url).match(/[?&]t=([0-9a-f]{32})/);if(m)u+='&t='+m[1]}catch(e){}  // sayfa tek kullanımlık anahtarla açılır (2 dk)
    return yerelSayfaAc(u,'dokum_kontrol')}
  if(a==='dkkapat'){const t=b.dataset.t;dkKapali.add(t);if(last)bnCiz(last);bnYaz('/dokum-kontrol',{islem:'kapat',t}).then(r=>{if(!r||!r.ok){dkKapali.delete(t);bnBildir(L('Yapılamadı'));if(last)bnCiz(last)}}).catch(()=>{dkKapali.delete(t);if(last)bnCiz(last)});return}
  if(a==='mtb'){const o=b.dataset.i;return bnIsle([id],o==='onay'?L('Kayıt kapatıldı'):L('Tamam, açık kalsın'),()=>bnYaz('/mutabakat',{kayit:id,islem:o}))}  // gece durum önerisi: Onayla kaydı kapatır (Geri al 5 sn), Hayır öneriyi reddeder
  if(a==='ksac'){let u='/kesisim';try{const r=await bnYaz('/tek-kullanim',{}),m=r&&r.url&&String(r.url).match(/[?&]t=([0-9a-f]{32})/);if(m)u+='?t='+m[1]}catch(e){}  // sayfa tek kullanımlık anahtarla açılır (2 dk)
    return yerelSayfaAc(u,'kesisim')}
  if(a==='tepki'){ev.stopPropagation();tpYap(b);return}
  if(a==='epyanlis')return epIslem('yanlis_oncelik',id,b,{beklenen:b.dataset.b})
  if(a==='bekac'){bnBekAcik=!bnBekAcik;if(last)bnCiz(last);return}
  if(a==='gerac'){bnGerAcik=!bnGerAcik;if(last)bnCiz(last);return}
  if(a==='dfzac'){bnDfzAcik=!bnDfzAcik;if(last)bnCiz(last);return}
  if(a==='knsek'){knSekme=b.dataset.s;if(last)bnCiz(last);return}
  if(a==='knac')return knAc(b.dataset.kid)
  if(a==='knert')return knAc(b.dataset.kid,'ertele')
  if(a==='knsahip'){knSuz.sahip=b.dataset.v||'';try{localStorage.setItem('knSahip',knSuz.sahip)}catch(e){}if(last)bnCiz(last);return}
  if(a==='kntarihsiz'){knSuz.durum=knSuz.durum==='tarihsiz'?'':'tarihsiz';if(last)bnCiz(last);return}
  if(a==='knyeni'){b.disabled=true;let r={};try{r=await bnYaz('/kayit-eylem',{id:b.dataset.kid,eylem:'ac'})}catch(e){}bnBildir(r.ok?L('Yeniden açıldı'):L('Yapılamadı.'));await bnVeriYukle(true);await knYukle(true);return}
  if(a==='ekipkisi'){knSuz={kisi:b.dataset.k||'',toplanti:'',durum:'',ara:'',sahip:''};knSekme='acik';git('kayit');return}
  if(a==='knkisi'){knSuz.kisi=knSuz.kisi===b.dataset.k?'':b.dataset.k;if(last)bnCiz(last);return}
  if(a==='kntop'){knSuz.toplanti=knSuz.toplanti===b.dataset.t?'':b.dataset.t;if(last)bnCiz(last);return}
  if(a==='knsifirla'){knSuz={kisi:'',toplanti:'',durum:'',ara:'',sahip:'ben'};if(last)bnCiz(last);return}
  if(a==='kngit'){if(b.dataset.sid){b.disabled=true;await sonIs(b.dataset.sid,b.dataset.harita?'harita':'');b.disabled=false}else if(b.dataset.top)arDokumAc(String(b.dataset.top).replace(/\.md$/,''));return}
  if(a==='gtac')return bnPanelAc('g:'+id)
  if(a==='izac')return bnPanelAc('iza:'+id)
  if(a==='gtkopya'){const g=gtV[id];if(!g)return;try{await navigator.clipboard.writeText(g.metin);bnBildir(L('Gündem kopyalandı'))}catch(e){bnBildir(L('kopyalanamadı'))}return}
  if(a==='gtbas'){const g=gtV[id],o=bnOlay.find(x=>x.id===id);if(!g)return;bnPanelKapat();bnGor='bugun';if(last)bnCiz(last);tkForm(o||null);const t=document.getElementById('tkg');t.value=g.maddeler.map(m=>m.satir).join('\n');t.dataset.el='1';return}
  if(a==='eptaslak'){epTaslakAc(bnOlay.find(x=>x.id===id));return}
  if(a==='disa')return disaAktar(b.dataset.bicim,b)
  if(a==='hazirla'){b.disabled=true;let r={};try{r=await j('/brifing',{method:'POST',body:JSON.stringify({olay:id,yeniden:hzDurum(bnOlay.find(o=>o.id===id)||{},last||{})==='hazir'})})}catch(e){}
    if(!r.ok){b.disabled=false;geciciDurum(L('Brifing başlatılamadı'),r.err||'');return}bnT=0;refresh();return}
  if(a==='bas'){const o=bnOlay.find(x=>x.id===id);bnPanelKapat();if(o&&o.baglanti&&last&&!last.aktif&&last.toplanti&&last.toplanti.son)return hizliBaslat(o,b);return tkForm(o||null)}
  if(a==='katil'){const o=bnOlay.find(x=>x.id===id);if(o&&o.baglanti){if(CHROME)window.open(o.baglanti,'_blank');else chromeAc({olay:o.id})}return}
  if(a==='son'){const r=((last||{}).son_toplantilar||[]).find(x=>x.id===id);b.disabled=true;await sonIs(id,b.dataset.tur||'',!!b.dataset.posta,b);b.disabled=false;return}}
document.getElementById('bgn').addEventListener('click',bnTik);document.getElementById('bgn').addEventListener('change',ev=>{if(ev.target.matches('input[data-kndn]')){knDen=ev.target.checked;knSuz.toplanti='';knSuz.kisi='';knV=null;if(last)bnCiz(last);knYukle(true);return}const s=ev.target.closest('select[data-knf]');if(!s)return;knSuz[s.dataset.knf]=s.value;if(last)bnCiz(last)})
document.getElementById('bgn').addEventListener('input',ev=>{if(ev.target.id!=='knAra')return;knSuz.ara=ev.target.value;clearTimeout(knAraT);knAraT=setTimeout(()=>{if(last)bnCiz(last)},150)});document.getElementById('bgn').addEventListener('submit',ev=>{if(ev.target.id==='gcF'){ev.preventDefault();const q=(document.getElementById('gcAra')||{}).value||'';document.getElementById('ara').value=q.trim();arsivAc(true);return}if(ev.target.id!=='bnPrF')return;ev.preventDefault();const k=document.getElementById('bnPrK');provaAc(k?k.value.trim():'');if(k)k.value=''})
// Geçmiş: son toplantı satırına sağ tık — aynı dışa aktar menüsü, farenin olduğu yerde
document.getElementById('bgn').addEventListener('contextmenu',ev=>{const r=ev.target.closest('.sat[data-gc]');if(!r||!last)return;ev.preventDefault();gcAk=r.dataset.gc;bnCiz(last);const m=document.querySelector('#bgn .akp');if(m)Object.assign(m.style,{position:'fixed',left:Math.min(ev.clientX,innerWidth-240)+'px',top:Math.max(8,Math.min(ev.clientY,innerHeight-m.offsetHeight-8))+'px',right:'auto'})});bnE('bnPanel').addEventListener('click',bnTik);bnE('bnPerde').addEventListener('click',bnPanelKapat)
bnE('bnGeri').addEventListener('click',ev=>{ev.stopPropagation();if(bnGeri)bnGeri();bnGeri=null;bnE('bnBild').classList.remove('acik')})
document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&bnRef)bnPanelKapat()})

