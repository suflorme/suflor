// Takvim görünümü (S167'nin yerine; kullanıcının seçtiği tasarım A — Google/Mac Takvim düzeni): Gün | Hafta | Ay seçici (seçim localStorage 'hfmod'), ana alanda tam genişlik Pazartesi–Pazar ızgarası, solda saat şeridi
// (her zaman 00–24: başka saat dilimindeki toplantılar ajandada gece geç saate düşer; açılışta şimdiye/ilk toplantıya/08:00'e kayar), saatine ve süresine göre bloklar, çakışanlar yan yana, bugün sütununda şimdi çizgisi, tüm gün şeridi.
// Blok rengi hazırlık (toplantı başına): hazır (bu toplantının brifingi kayıtlı) · eksik (brifing yok ama gündem, belge ya da aynı kişilerle son 30 günde Suflor kaydı var;
// ya da brifing sürüyor/hata) · yok. Gelecekteki toplantıda Hazırla (/brifing, toplantıyı başlatmadan), hazırsa Hazırlığı aç (kutuda brifing). Geçmiş soluk, reddedilen üstü çizili. ‹ › hafta gezer (aktarıcının verdiği
// aralıkta), bloğa tıklayınca ayrıntı kutusu: gelecekte Başlat (mevcut form), geçmişte Suflor kaydı varsa Özeti aç / Dökümü aç. Veri: /takvim?hafta=<n> (takvim_hafta).
// Gün: aynı ızgara tek sütun (o günü içeren haftanın verisinden süzülür; ‹ › bir gün). Ay: 7×6 ızgara (/takvim?ay=<n>, takvim_ay; ‹ › bir ay), hücrede en çok 4 satır ya da 3 + "+n tane daha";
// gün numarası ve "+n" o günün Gün görünümünü açar. Odak gün (hfOdak) üç görünümde ortaktır; Bugün odağı bugüne alır.
// Chrome panosunda takvimdeki "Bu hafta" düğmesi, Mac penceresinde kenar çubuğundaki "Bu hafta" açar.
let hfAcik=false,hfOnceTop=false,hfVeri=null,hfAyVeri=null,hfMod='hafta',hfOdak=null,hfLim=[-1,4],hfAyLim=[-1,1],hfArsiv=null,hfArsivT=0,hfZam=null,hfAralik=[0,1440],hfSecI=null,hfHzAcik=null,hfBekle=null,hfCizT=0
try{const m=localStorage.getItem('hfmod');if(m==='gun'||m==='hafta'||m==='ay')hfMod=m}catch(e){}  // seçili görünüm (Gün | Hafta | Ay) tarayıcıda hatırlanır
const hfAkt=()=>(hfMod==='ay'?hfAyVeri:hfVeri)||{olaylar:[]}  // ayrıntı kutusu ve tkBul: ekrandaki görünümün olayları (data-hf = bu listede sıra)
const tkBul=id=>tkListe.find(x=>x.id===id)||(typeof bnOlay!=='undefined'?bnOlay.find(x=>x.id===id):null)||tkOlaylar.find(x=>x.id===id)||((hfVeri&&hfVeri.olaylar)||[]).find(x=>x.id===id)||((hfAyVeri&&hfAyVeri.olaylar)||[]).find(x=>x.id===id)
const hfGun=s=>{const [y,m,d]=String(s).split('-').map(Number);return new Date(y,m-1,d)}, hfGunEk=(d,n)=>new Date(d.getFullYear(),d.getMonth(),d.getDate()+n)
const hfIso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
const hfBugunD=()=>{const n=new Date();return new Date(n.getFullYear(),n.getMonth(),n.getDate())}, hfPzt=d=>hfGunEk(d,-((d.getDay()+6)%7))
const hfHaftaOf=d=>Math.round((hfPzt(d)-hfPzt(hfBugunD()))/6048e5), hfAyOfs=d=>{const n=new Date();return(d.getFullYear()-n.getFullYear())*12+d.getMonth()-n.getMonth()}  // odak günün hafta / ay ofseti (bugüne göre)
function hfAc(ac){if(ac&&stAcik)stAc(false);hfAcik=!!ac;document.documentElement.classList.toggle('hafta-ac',hfAcik);document.getElementById('hfs').hidden=!hfAcik;document.getElementById('tkh7').classList.toggle('on',hfAcik);hfDetayKapat()
  clearInterval(hfZam);hfZam=null
  if(hfAcik){hfOdak=hfBugunD();hfYukle(true);hfZam=setInterval(()=>{if(hfAkt().bugun)hfCiz(false)},60000)}
  else if(kcSec==='tv'&&!stAcik){kcSec={bugun:'tks',kayit:'kr'}[bnGor]||bnGor;if(last)kenarCiz(last,document.documentElement.classList.contains('toplantida'))}
  tvCiz()}
async function hfYukle(kaydir){if(hfAcik&&tvMod!==hfMod){tvMod=hfMod;tvCiz()}const s=document.getElementById('hfs'),ay=hfMod==='ay';if(!(ay?hfAyVeri:hfVeri))s.innerHTML=`<p class=hint>${L('takvim okunuyor…')}</p>`
  const lm=ay?hfAyLim:hfLim,of=Math.max(lm[0],Math.min(lm[1],ay?hfAyOfs(hfOdak):hfHaftaOf(hfOdak)))  // odak gün veri aralığında kalır; gün görünümü o günü içeren haftanın verisini süzer
  let t=null;try{t=await j(ay?'/takvim?ay='+of:'/takvim?hafta='+of)}catch(e){}
  if(!hfAcik||ay!==(hfMod==='ay'))return;if(!t||!(ay?t.ay_bas:t.hafta_bas)){s.innerHTML=`<p class=hint>${L("Suflor.me'ye ulaşılamadı")}</p>`;return}
  if(ay){hfAyVeri=t;hfAyLim=[t.en_az,t.en_cok];if(hfAyOfs(hfOdak)!==t.ofset){const n=new Date();hfOdak=new Date(n.getFullYear(),n.getMonth()+t.ofset,1)}}
  else{hfVeri=t;hfLim=[t.en_az,t.en_cok];if(hfHaftaOf(hfOdak)!==t.ofset)hfOdak=hfGunEk(hfPzt(hfBugunD()),7*t.ofset)}
  hfCiz(kaydir);if(t.olaylar.some(o=>o.gecmis))hfArsivAl()
  const d=document.getElementById('hfd'),sid=d&&d.dataset.id  // açık ayrıntı kutusu yeni veriyle (brifing bitince yeşil, Hazırlığı aç)
  if(sid){const i=t.olaylar.findIndex(o=>o.id===sid),el=i>=0&&document.querySelector(`#hfs .hfo[data-hf="${i}"]`);if(el)hfDetay(i,el,true);else hfDetayKapat()}
  clearTimeout(hfBekle);hfBekle=t.olaylar.some(o=>o.brifing==='calisiyor')?setTimeout(()=>{if(hfAcik)hfYukle(false)},5000):null}
async function hfArsivAl(){if(hfArsiv&&Date.now()-hfArsivT<60000)return;try{const r=await j('/toplantilar');hfArsiv=r.toplantilar||[];hfArsivT=Date.now()}catch(e){}}
function hfKayit(o){if(!hfArsiv)return null;const b=+new Date(o.baslangic),e=+new Date(o.bitis);let en=null,f=1e15  // Suflor kaydı: başlangıcı toplantı saatinde (20 dk erken açılmış olabilir)
  for(const x of hfArsiv){const t=+new Date(x.at);if(t>=b-20*6e4&&t<=e&&Math.abs(t-b)<f){f=Math.abs(t-b);en=x}}return en}
function hfYerlesim(ss){ss.sort((a,b)=>a.s-b.s||b.e-a.e);let kume=[],son=-1;const kol=[]  // çakışan kümeler: her blok ilk boş kolona, küme genişliği en çok kolon
  const bitir=()=>{const n=Math.max(...kume.map(x=>x.k))+1;kume.forEach(x=>x.n=n);kume=[];kol.length=0;son=-1}
  for(const x of ss){if(kume.length&&x.s>=son)bitir();let k=kol.findIndex(e=>e<=x.s);if(k<0){k=kol.length;kol.push(x.e)}else kol[k]=x.e;x.k=k;kume.push(x);son=Math.max(son,x.e)}
  if(kume.length)bitir();return ss}
function hfUst(baslik,bugunKapali,oncKapali,sonKapali){const dg={gun:['Önceki gün','Sonraki gün'],hafta:['Önceki hafta','Sonraki hafta'],ay:['Önceki ay','Sonraki ay']}[hfMod],hz={hazir:L('Hazır'),eksik:L('Eksik'),yok:L('Hazırlık yok')}
  return`<div class=hft><button type=button class=gh data-hfg=bugun ${bugunKapali?'disabled':''}>${L('Bugün')}</button><button type=button class="gh ib" data-hfg=-1 title="${L(dg[0])}" aria-label="${L(dg[0])}" ${oncKapali?'disabled':''}>‹</button><button type=button class="gh ib" data-hfg=1 title="${L(dg[1])}" aria-label="${L(dg[1])}" ${sonKapali?'disabled':''}>›</button><h2 id=hfb>${esc(baslik)}</h2><span class=sp1></span>`
    +`<div class=seg role=group aria-label="${L('Görünüm')}" id=hfm>${[['gun','Gün'],['hafta','Hafta'],['ay','Ay']].map(([k,a])=>`<button type=button data-hfmod=${k} class="${hfMod===k?'on':''}" aria-pressed=${hfMod===k}>${L(a)}</button>`).join('')}</div>`
    +`<span class=hfl title="${L('Blok rengi toplantının hazırlık durumu')}">${['hazir','eksik','yok'].map(k=>`<span><i class=hz-${k}></i>${hz[k]}</span>`).join('')}${(hfAkt().olaylar||[]).some(o=>o.paylasilan)?`<span><i class=hz-pay></i>${L('Paylaşılan')}</span>`:''}</span><button type=button class="ib gh kgx" data-hfg=kapat title="${L('Kapat')}" aria-label="${L('Kapat')}">${ic('x')}</button></div>`}
function hfNot(t,gun,bos){const loc=L('tr-TR'),kb=t.kapsam&&t.kapsam.bas,ks=t.kapsam&&t.kapsam.son,okuyok=d=>{const x=hfIso(d);return(kb&&x<kb)||(ks&&x>ks)}
  return!t.uygulama?L('Takvim bağlı değil — toplantıyı elle başlatabilirsin.'):t.durum==='izin_yok'?L('Takvim izni yok — Sistem Ayarları → Gizlilik ve Güvenlik → Takvimler → Suflor Takvim.')
    :t.durum&&t.durum!=='ok'&&t.durum!=='bekliyor'?L(t.hata||t.durum):gun.some(okuyok)?L('Takvim {a} – {b} arasını okuyor; taralı günlerde bilgi yok.',{a:hfGun(kb).toLocaleDateString(loc,{day:'numeric',month:'long'}),b:hfGun(ks).toLocaleDateString(loc,{day:'numeric',month:'long'})})
    :bos?L(bos):''}
function hfCiz(kaydir){if(hfMod==='ay')return hfAyCiz();const t=hfVeri,G=hfMod==='gun';if(!t)return
  const s=document.getElementById('hfs'),loc=L('tr-TR'),H=44,simdi=new Date(),bas=hfGun(t.hafta_bas),bugun=hfIso(simdi),hg=[...Array(7)].map((_,i)=>hfGunEk(bas,i))
  if(G&&!hg.some(d=>hfIso(d)===hfIso(hfOdak)))return  // odak gün başka haftada: o haftanın verisi yükleniyor
  const gun=G?[hfOdak]:hg,ol=t.olaylar||[],kb=t.kapsam&&t.kapsam.bas,ks=t.kapsam&&t.kapsam.son
  const okuyok=d=>{const x=hfIso(d);return(kb&&x<kb)||(ks&&x>ks)}
  const son=hg[6],ayni=bas.getFullYear()===son.getFullYear(),of=hfHaftaOf(bas)
  const baslik=G?hfOdak.toLocaleDateString(loc,{weekday:'long',day:'numeric',month:'long',year:'numeric'}):bas.toLocaleDateString(loc,ayni?{day:'numeric',month:'long'}:{day:'numeric',month:'long',year:'numeric'})+' – '+son.toLocaleDateString(loc,{day:'numeric',month:'long',year:'numeric'})
  // saat aralığı: her zaman 00:00–24:00 (başka saat dilimindeki toplantılar ajandada gece geç saate düşebilir); açılışta kaydırma bugünün şimdisine / ilk toplantıya / 08:00'e
  const seg=gun.map(()=>[]),tum=gun.map(()=>[]);const a0=0,a1=1440
  ol.forEach((o,i)=>{const b=new Date(o.baslangic),e=new Date(o.bitis)
    gun.forEach((d,g)=>{const g0=+d,g1=+hfGunEk(d,1);if(+e<=g0||+b>=g1)return
      if(o.tum_gun){tum[g].push(i);return}
      const sb=Math.max(+b,g0),se=Math.min(+e,g1),x={i,s:Math.round((sb-g0)/6e4),e:Math.max(Math.round((se-g0)/6e4),Math.round((sb-g0)/6e4)+15)};seg[g].push(x)})})
  hfAralik=[a0,a1];const yuk=(a1-a0)/60*H,y=m=>(m-a0)/60*H
  const blok=(x,g)=>{const o=ol[x.i],top=y(x.s),h=Math.max(y(x.e)-top-2,18),kisa=h<34,w=100/x.n,l=x.k*w
    return`<button type=button class="hfo hz-${o.paylasilan?'pay':esc(o.hazirlik)}${o.gecmis?' gec':''}${o.reddettin?' red':''}${kisa?' kisa':''}${hfSecI===x.i?' sec':''}" data-hf="${x.i}" style="top:${top+1}px;height:${h}px;left:calc(${l}% + 2px);width:calc(${w}% - 4px);--sat:${Math.max(1,Math.floor((h-18)/15))}" title="${esc(o.saat+'–'+o.bitis_saat+' · '+o.baslik)}">`
      +(kisa?`<b><span class=z>${esc(o.saat)}</span> ${esc(o.baslik)}</b>`:`<span class=z>${esc(o.saat)}–${esc(o.bitis_saat)}</span><b>${esc(o.baslik)}</b>`)+`</button>`}
  const not=hfNot(t,gun,G?(seg[0].length||tum[0].length?'':hfIso(hfOdak)===bugun?'Bugün takvimde toplantı yok':'Bu günde takvimde toplantı yok'):!ol.length?(of===0?'Bu hafta takvimde toplantı yok':'Bu aralıkta takvimde toplantı yok'):'')
  const simdiDk=(simdi-hfGun(bugun))/6e4,bg=gun.findIndex(d=>hfIso(d)===bugun)
  const h=hfUst(baslik,G?hfIso(hfOdak)===bugun:of===0,G?hfHaftaOf(hfGunEk(hfOdak,-1))<t.en_az:of<=t.en_az,G?hfHaftaOf(hfGunEk(hfOdak,1))>t.en_cok:of>=t.en_cok)
    +`<p id=hfn class=hint>${esc(not)}</p>`
    +`<div class=hfk style="--kn:${gun.length}"><div class=hfu><div></div>${gun.map(d=>{const x=hfIso(d);return`<div class="${x===bugun?'bg':x<bugun?'gc':''}${okuyok(d)?' okuyok':''}">${esc(d.toLocaleDateString(loc,{weekday:'short'}))}<span class=n>${d.getDate()}</span></div>`}).join('')}</div>`
    +(tum.some(x=>x.length)?`<div class=hfa><div class=ad>${L('tüm gün')}</div>${tum.map((ix,g)=>`<div class="${okuyok(gun[g])?'okuyok':''}">${ix.map(i=>{const o=ol[i];return`<button type=button class="hfo kisa hz-${o.paylasilan?'pay':esc(o.hazirlik)}${o.gecmis?' gec':''}${o.reddettin?' red':''}" data-hf="${i}" title="${esc(o.baslik)}"><b>${esc(o.baslik)}</b></button>`}).join('')}</div>`).join('')}</div>`:'')
    +`<div class=hfg id=hfg><div class=hfs style="height:${yuk}px">${[...Array((a1-a0)/60)].map((_,k)=>`<span style="top:${k*H}px">${k?String(a0/60+k).padStart(2,'0')+':00':''}</span>`).join('')}</div>`
    +gun.map((d,g)=>`<div class="hfc${g===bg?' bg':''}${okuyok(d)?' okuyok':''}" data-gun="${hfIso(d)}" style="height:${yuk}px">${hfYerlesim(seg[g]).map(x=>blok(x,g)).join('')}${g===bg&&simdiDk>=a0&&simdiDk<=a1?`<div class=hfsim style="top:${y(simdiDk)}px"></div>`:''}</div>`).join('')+`</div></div>`
  const gg=document.getElementById('hfg'),st=gg?gg.scrollTop:0
  hfCizT=Date.now();s.innerHTML=h;const g2=document.getElementById('hfg')
  if(kaydir){const ilk=Math.min(...seg.flat().map(x=>x.s),1440),hedef=bg>=0?simdiDk-90:ilk<1440?ilk-30:8*60;g2.scrollTop=Math.max(0,y(hedef))}else g2.scrollTop=st}
function hfAyCiz(){const t=hfAyVeri;if(!t)return
  const s=document.getElementById('hfs'),loc=L('tr-TR'),simdi=new Date(),bugun=hfIso(simdi),bas=hfGun(t.aralik_bas),ab=hfGun(t.ay_bas),ol=t.olaylar||[],kb=t.kapsam&&t.kapsam.bas,ks=t.kapsam&&t.kapsam.son
  const okuyok=d=>{const x=hfIso(d);return(kb&&x<kb)||(ks&&x>ks)},gun=[...Array(42)].map((_,i)=>hfGunEk(bas,i)),ls=gun.map(()=>[])
  ol.forEach((o,i)=>{const b=+new Date(o.baslangic),e=+new Date(o.bitis);gun.forEach((d,g)=>{if(e<=+d||b>=+hfGunEk(d,1))return;ls[g].push(i)})})  // gün hücresine düşen olaylar; tüm gün olaylar başta (şerit), sonra başlangıç sırası
  ls.forEach(l=>l.sort((a,b)=>!!ol[b].tum_gun-!!ol[a].tum_gun))
  const satir=i=>{const o=ol[i];return`<button type=button class="hfo kisa ay hz-${o.paylasilan?'pay':esc(o.hazirlik)}${o.tum_gun?' tum':''}${o.gecmis?' gec':''}${o.reddettin?' red':''}${hfSecI===i?' sec':''}" data-hf="${i}" title="${esc((o.tum_gun?'':o.saat+'–'+o.bitis_saat+' · ')+o.baslik)}"><b>${o.tum_gun?'':`<span class=z>${esc(o.saat)}</span> `}${esc(o.baslik)}</b></button>`}
  const hucre=(d,g)=>{const x=hfIso(d),l=ls[g],n=l.length,goster=n<=4?l:l.slice(0,3),ek=d.getDate()===1?d.toLocaleDateString(loc,{month:'short'})+' ':''
    return`<div data-gun="${x}" class="${x===bugun?'bg':''}${d.getMonth()!==ab.getMonth()?' dis':''}${okuyok(d)?' okuyok':''}"><button type=button class=gn data-hfgun="${x}" title="${esc(d.toLocaleDateString(loc,{weekday:'long',day:'numeric',month:'long'}))}">${esc(ek)}${d.getDate()}</button>${goster.map(satir).join('')}${n>goster.length?`<button type=button class=mo data-hfgun="${x}">${esc(L('+{n} tane daha',{n:n-goster.length}))}</button>`:''}</div>`}
  const of=t.ofset,baslik=ab.toLocaleDateString(loc,{month:'long',year:'numeric'}),not=hfNot(t,gun,!ol.length?'Bu ay takvimde toplantı yok':'')
  const h=hfUst(baslik,of===0,of<=t.en_az,of>=t.en_cok)+`<p id=hfn class=hint>${esc(not)}</p>`
    +`<div class=hfk><div class="hfu ay">${gun.slice(0,7).map(d=>`<div>${esc(d.toLocaleDateString(loc,{weekday:'short'}))}</div>`).join('')}</div><div class=hfay id=hfg>${gun.map(hucre).join('')}</div></div>`
  hfCizT=Date.now();s.innerHTML=h}
function hfDetayKapat(tut){const d=document.getElementById('hfd');if(d)d.remove();if(!tut)hfHzAcik=null;if(hfSecI!==null){hfSecI=null;document.querySelectorAll('#hfs .hfo.sec').forEach(x=>x.classList.remove('sec'))}}
function hfDetay(i,el,tut){hfDetayKapat(tut);const o=(hfAkt().olaylar||[])[i];if(!o)return;hfSecI=i;el.classList.add('sec');const loc=L('tr-TR'),b=new Date(o.baslangic)
  const kim=(o.katilimcilar||[]),ks=o.kisi_sayisi||kim.length,kay=o.gecmis?hfKayit(o):null
  const hz={hazir:L('Hazırlık hazır — brifing var'),eksik:o.brifing?L('Hazırlık eksik'):L('Hazırlık eksik — bağlam var, brifing yok'),yok:L('Hazırlık yok')}
  const nd={gundem:L('davette gündem var'),belge:L('davette belge bağlantısı var'),gecmis:L('bu kişilerle son 30 günde Suflor kaydı var')}
  const hzs=o.brifing==='calisiyor'?L('{asistan} brifingi hazırlıyor… (1–2 dk)'):o.brifing==='hata'?(o.brifing_hata||L('Brifing hazırlanamadı')):o.hazirlik==='eksik'&&(o.hazirlik_neden||[]).length?o.hazirlik_neden.map(x=>nd[x]).filter(Boolean).join(' · '):''
  const hr=o.hazirlik_sonuc,ls=(a,t)=>a&&a.length?`<div class=bb>${L(t)}</div><ul>${a.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''
  const hzAcik=!!hr&&hfHzAcik===o.id,yeni=!o.gecmis&&o.baslatilir&&!o.paylasilan
  const hzDug=o.brifing==='calisiyor'?`<button type=button class=gh disabled>${L('Hazırlanıyor…')}</button>`:hr?`<button type=button class=gh data-hfhz="${esc(o.id)}" aria-expanded="${hzAcik}">${L(hzAcik?'Hazırlığı gizle':'Hazırlığı aç')}</button>`
    :yeni?`<button type=button class=gh data-hfhb="${esc(o.id)}" title="${L('{asistan} geçmiş görüşmelere, açık sorulara ve belgelere bakıp kısa bir brifing hazırlar.')}">${L(o.brifing==='hata'?'Yeniden dene':'Hazırla')}</button>`:''
  const d=document.createElement('div');d.id='hfd';d.dataset.id=o.id;d.setAttribute('role','dialog');d.setAttribute('aria-label',o.baslik||'')
  d.innerHTML=`<div class=bas><b class="${o.reddettin?'red':''}">${esc(o.baslik||L('(başlıksız)'))}</b><button type=button class="ib gh kgx" data-hfx title="${L('Kapat')}" aria-label="${L('Kapat')}">${ic('x')}</button></div>`
    +`<div class=sat>${esc(b.toLocaleDateString(loc,{weekday:'long',day:'numeric',month:'long'}))} · ${o.tum_gun?L('tüm gün'):esc(o.saat+'–'+o.bitis_saat)}${o.suruyor?' · '+L('şimdi'):''}</div>`
    +(o.platform||o.yer?`<div class=sat>${o.platform?`<span class=chip>${PL[o.platform]||esc(o.platform)}</span> `:''}${o.yer&&!/^https?:/i.test(o.yer)?esc(o.yer):''}</div>`:'')
    +(ks?`<div class="sat kim">${esc(L('{n} kişi',{n:ks}))}${kim.length?': '+esc(kim.slice(0,8).join(', '))+(kim.length>8||ks>kim.length+1?' …':''):''}</div>`:'')
    +(o.ben_duzenleyen?`<div class="sat kim">${L('düzenleyen sen')}</div>`:o.duzenleyen?`<div class="sat kim">${esc(L('Düzenleyen: {ad}',{ad:o.duzenleyen}))}</div>`:'')
    +(o.reddettin?`<div class="sat kim">${L('daveti reddettin')}</div>`:'')
    +(o.paylasilan?`<div class="sat hz"><i class=hz-pay></i>${esc(L('Paylaşılan takvim: {ad}',{ad:o.takvim_adi||''}))}</div>`:`<div class="sat hz"><i class=hz-${esc(o.hazirlik)}></i>${hz[o.hazirlik]||hz.yok}</div>`)+(hzs&&!o.paylasilan?`<div class="sat kim">${esc(hzs)}</div>`:'')
    +(hzAcik?`<div class=hzb>${hr.ozet?`<div class=b>${esc(hr.ozet)}</div>`:''}${hzGundem(hr)}${ls(hr.veri,'Güncel veri')}${ls(hr.dikkat,'Dikkat')}${ls(hr.acik,'Açık kalanlar')}${ls(hr.dis_taraf,hr.dis_etiket||'Dış taraf')}${ls(hr.gecmis,'Geçmişte')}</div>`:'')
    +(o.gecmis&&hfArsiv&&!kay?`<div class="sat kim">${L('Bu toplantının Suflor kaydı yok')}</div>`:'')
    +`<div class=bt>${hzDug}${o.baslatilir?`<button type=button class=pri data-hfb="${esc(o.id)}">${L('Başlat')}</button>`:''}${kay&&kay.ozet?`<button type=button class=pri data-hfoz="${esc(kay.ozet)}">${L('Özeti aç')}</button>`:''}${kay?`<button type=button class=gh data-hfdk="${esc(kay.id)}">${L('Dökümü aç')}</button>`:''}</div>`
  hfKonum(d,el.getBoundingClientRect())
  if(o.gecmis&&!hfArsiv)hfArsivAl().then(()=>{if(hfSecI===i&&document.getElementById('hfd'))hfDetay(i,document.querySelector(`#hfs .hfo[data-hf="${i}"]`)||el)})}
function hfKonum(d,r){document.body.appendChild(d);const w=d.offsetWidth,hh=d.offsetHeight,vw=innerWidth,vh=innerHeight
  let x=r.right+8,yy=Math.max(8,Math.min(r.top,vh-hh-8))  // sağına; sığmazsa soluna; ikisi de sığmazsa altına (dar pencere)
  if(x+w>vw-8){x=r.left-w-8;if(x<8){x=Math.max(8,Math.min(vw-w-8,r.left));yy=r.bottom+6+hh<vh?r.bottom+6:Math.max(8,r.top-hh-6)}}
  d.style.left=x+'px';d.style.top=yy+'px'}
// Takvimden toplantı oluşturma (v0.166.0): Gün/Hafta ızgarasında boş alana tıkla (yarım saate yuvarlanır) ya da Ay'da boş hücreye çift tıkla (09:00) → küçük kutu (#hfd.hfy);
// "Takvimde aç" /takvim-toplanti ile takvimin dolu "yeni etkinlik" sayfasını açar (Chrome panosunda sayfayı tarayıcı, Mac penceresinde aktarıcı açar); Kaydet kullanıcıda. Davetli çözümü yazarken önizlenir.
let hfYeniOn=0,hfYeniT=null
function hfYeni(gun,dk,ev){hfDetayKapat();const d=document.createElement('div');d.id='hfd';d.className='hfy';d.setAttribute('role','dialog');d.setAttribute('aria-label',L('Yeni toplantı'))
  d.innerHTML=`<div class=bas><b>${L('Yeni toplantı')}</b><button type=button class="ib gh kgx" data-hfx title="${L('Kapat')}" aria-label="${L('Kapat')}">${ic('x')}</button></div>`
    +`<input id=hyb maxlength=300 placeholder="${L('Başlık')}" aria-label="${L('Başlık')}" autocomplete=off>`
    +`<div class=hyr><input id=hyd type=date value="${esc(gun)}" aria-label="${L('Tarih')}"><input id=hyt type=time step=900 value="${String(Math.floor(dk/60)).padStart(2,'0')}:${String(dk%60).padStart(2,'0')}" aria-label="${L('Saat')}"><select id=hys aria-label="${L('Süre')}">${[15,30,45,60,90].map(n=>`<option value=${n}${n===30?' selected':''}>${L('{n} dk',{n})}</option>`).join('')}</select></div>`
    +`<input id=hyk placeholder="${L('Davetliler (virgülle: ad ya da e-posta)')}" aria-label="${L('Davetliler (virgülle: ad ya da e-posta)')}" autocomplete=off><div id=hyo class="sat kim"></div><div id=hyu class="sat kim er" hidden>${L('Geçmiş bir saat — toplantı oluşturulamaz')}</div>`
    +`<div class=bt><button type=button class=pri data-hfyeni>${L('Takvimde aç')}</button></div><div class=sat>${L("Takvim sayfası dolu açılır; Kaydet'e sen basarsın.")}</div>`
  hfKonum(d,{left:ev.clientX,right:ev.clientX,top:ev.clientY,bottom:ev.clientY})
  const q=x=>d.querySelector(x),zm=()=>q('#hyd').value+'T'+q('#hyt').value
  const gecmis=()=>{const t=new Date(zm());const g=isNaN(t)||t<new Date()-6e4;q('#hyu').hidden=!(g&&!isNaN(t));q('[data-hfyeni]').disabled=g;return g}
  const adlar=()=>q('#hyk').value.split(/[,;]/).map(x=>x.trim()).filter(Boolean).slice(0,20)
  const onizle=async()=>{const n=++hfYeniOn,ad=adlar(),o=q('#hyo');if(!ad.length){o.innerHTML='';return}
    let r=null;try{r=await j('/takvim-toplanti',{method:'POST',body:JSON.stringify({onizle:true,baslik:q('#hyb').value,zaman:zm(),dk:+q('#hys').value,davetli:ad})})}catch(e){}
    if(n!==hfYeniOn||!d.isConnected)return
    o.innerHTML=r&&r.davetli?r.davetli.map(k=>`<div>${esc(k.eposta?L('{ad} → adres bulundu: {eposta}',{ad:k.ad,eposta:k.eposta}):L('{ad} → adres yok',{ad:k.ad}))}</div>`).join(''):''}
  q('#hyk').addEventListener('input',()=>{clearTimeout(hfYeniT);hfYeniT=setTimeout(onizle,350)})
  ;['#hyd','#hyt'].forEach(x=>q(x).addEventListener('input',gecmis));q('#hyb').addEventListener('keydown',e=>{if(e.key==='Enter')q('[data-hfyeni]').click()})
  d._gonder=async b=>{if(gecmis())return;const baslik=q('#hyb').value.trim();if(!baslik){q('#hyb').focus();return}b.disabled=true
    let r={};try{r=await j('/takvim-toplanti',{method:'POST',body:JSON.stringify({baslik,zaman:zm(),dk:+q('#hys').value,davetli:adlar(),ac:!CHROME})})}catch(e){}
    if(!r.ok){b.disabled=false;geciciDurum(L('Toplantı oluşturulamadı'),r.err||'');return}
    if(CHROME&&r.url)window.open(r.url,'_blank');hfDetayKapat();geciciDurum(L("Takvim sayfası açıldı — Kaydet'e sen basarsın"),'',8000)
    setTimeout(()=>{fetch('/takvim-yenile',{method:'POST',body:'{}'});setTimeout(()=>{if(hfAcik)hfYukle(false)},12000)},60000)}  // Kaydedilen toplantı ~1 dk sonra takvime yansır
  gecmis();q('#hyb').focus()}
document.getElementById('hfs').addEventListener('click',ev=>{
  if(ev.target.classList&&ev.target.classList.contains('hfc')&&ev.target.dataset.gun){ev.stopPropagation();const r=ev.target.getBoundingClientRect(),dk=Math.max(0,Math.min(1410,Math.floor((ev.clientY-r.top)/(r.height/24)*2)*30));hfYeni(ev.target.dataset.gun,dk,ev);return}  // boş alan: yarım saate yuvarlanmış başlangıç
  const g=ev.target.closest('[data-hfg]');if(g){const v=g.dataset.hfg
    if(v==='kapat'){hfAc(false);return}hfDetayKapat()
    if(v==='bugun')hfOdak=hfBugunD();else{const n=Number(v);if(hfMod==='gun')hfOdak=hfGunEk(hfOdak,n);else if(hfMod==='hafta')hfOdak=hfGunEk(hfOdak,7*n)
      else{const a=new Date(hfOdak.getFullYear(),hfOdak.getMonth()+n,1),b=hfBugunD();hfOdak=a.getFullYear()===b.getFullYear()&&a.getMonth()===b.getMonth()?b:a}}  // ay: ayın 1'i (bu ay ise bugün)
    hfYukle(true);return}
  const m=ev.target.closest('[data-hfmod]');if(m){hfDetayKapat();hfMod=m.dataset.hfmod;try{localStorage.setItem('hfmod',hfMod)}catch(e){}hfYukle(true);return}
  const gd=ev.target.closest('[data-hfgun]');if(gd){hfDetayKapat();hfOdak=hfGun(gd.dataset.hfgun);hfMod='gun';try{localStorage.setItem('hfmod',hfMod)}catch(e){}hfYukle(true);return}  // ay hücresinde gün numarası ya da "+n tane daha" → o günün Gün görünümü
  const b=ev.target.closest('.hfo[data-hf]');if(b){ev.stopPropagation();if(hfSecI===Number(b.dataset.hf)){hfDetayKapat();return}hfDetay(Number(b.dataset.hf),b)}})
document.addEventListener('click',async ev=>{const d=document.getElementById('hfd');if(!d)return
  if(!d.contains(ev.target)){if(!ev.target.closest('#hfs .hfo'))hfDetayKapat();return}
  if(ev.target.closest('[data-hfx]')){hfDetayKapat();return}
  const yn=ev.target.closest('[data-hfyeni]');if(yn){if(d._gonder)d._gonder(yn);return}
  const hzb=ev.target.closest('[data-hfhz]');if(hzb){const i=hfSecI;hfHzAcik=hfHzAcik===hzb.dataset.hfhz?null:hzb.dataset.hfhz;hfDetay(i,document.querySelector(`#hfs .hfo[data-hf="${i}"]`),true);return}
  const hh=ev.target.closest('[data-hfhb]');if(hh){hh.disabled=true;let r={};try{r=await j('/brifing',{method:'POST',body:JSON.stringify({olay:hh.dataset.hfhb})})}catch(e){}
    if(!r.ok){hh.disabled=false;geciciDurum(L('Brifing başlatılamadı'),r.err||'');return}hfYukle(false);return}
  const bs=ev.target.closest('[data-hfb]');if(bs){const o=tkBul(bs.dataset.hfb);hfAc(false);if(o)tkForm(o);return}
  const oz=ev.target.closest('[data-hfoz]');if(oz){hfDetayKapat();arOzet(oz.dataset.hfoz);return}
  const dk=ev.target.closest('[data-hfdk]');if(dk){hfDetayKapat();const a=document.getElementById('ard');if(!a.open)a.showModal();arDokumAc(dk.dataset.hfdk)}})
document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&document.getElementById('hfd')){hfDetayKapat();ev.stopPropagation()}},true)
document.getElementById('hfs').addEventListener('scroll',()=>{if(Date.now()-hfCizT>500)hfDetayKapat()},true)  // yeniden çizimin kaydırma geri yüklemesi kutuyu kapatmasın
document.getElementById('hfs').addEventListener('dblclick',ev=>{const c=ev.target.closest('.hfay>div');if(!c||ev.target.closest('button')||!c.dataset.gun)return;hfYeni(c.dataset.gun,540,ev)})  // Ay: boş hücreye çift tıklama → 09:00
document.getElementById('tkh7').onclick=()=>hfAc(!hfAcik);document.getElementById('tkbg').onclick=()=>{if(hfAcik)hfAc(false);if(stAcik)stAc(false)}
// Saatler (4 Kasım, kullanıcı): saat dilimi çevirici — şehir listesi, 48 saatlik kaydırıcı, mesai rengi. Hepsi tarayıcının Intl'iyle (ağ yok). Liste ayar `saatler`.
// Bu hafta ile karşılıklı kapanır; Chrome panosunda Bugün başlığındaki seçiciden, Mac penceresinde kenar çubuğundan açılır.
Object.assign(ICO,{dunya:'<circle cx=12 cy=12 r=8.5 /><path d="M3.5 12h17M12 3.5c2.6 2.6 2.6 14.4 0 17M12 3.5c-2.6 2.6-2.6 14.4 0 17"/>',stgun:'<circle cx=12 cy=12 r=3.5 /><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M18 6l-1.4 1.4M7.4 16.6 6 18"/>',stufuk:'<path d="M7 16a5 5 0 0 1 10 0M3.5 16h17M12 6.5v2M5.8 9.3l1.4 1.4M18.2 9.3l-1.4 1.4M6 19.5h12"/>',stay:'<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>'})
const STC=[['İstanbul','Istanbul','Europe/Istanbul'],['Londra','London','Europe/London'],['New York','New York','America/New_York'],['Doğu','Eastern','America/New_York',1],['Pasifik','Pacific','America/Los_Angeles',1],['Los Angeles','Los Angeles','America/Los_Angeles'],['San Francisco','San Francisco','America/Los_Angeles'],['Chicago','Chicago','America/Chicago'],['Denver','Denver','America/Denver'],['Toronto','Toronto','America/Toronto'],['Meksiko','Mexico City','America/Mexico_City'],['Sao Paulo','Sao Paulo','America/Sao_Paulo'],['Buenos Aires','Buenos Aires','America/Argentina/Buenos_Aires'],['Honolulu','Honolulu','Pacific/Honolulu'],['Anchorage','Anchorage','America/Anchorage'],
 ['Köln','Cologne','Europe/Berlin',1],['Berlin','Berlin','Europe/Berlin'],['Münih','Munich','Europe/Berlin'],['Frankfurt','Frankfurt','Europe/Berlin'],['Paris','Paris','Europe/Paris'],['Madrid','Madrid','Europe/Madrid'],['Roma','Rome','Europe/Rome'],['Amsterdam','Amsterdam','Europe/Amsterdam'],['Brüksel','Brussels','Europe/Brussels'],['Zürih','Zurich','Europe/Zurich'],['Viyana','Vienna','Europe/Vienna'],['Stokholm','Stockholm','Europe/Stockholm'],['Varşova','Warsaw','Europe/Warsaw'],['Atina','Athens','Europe/Athens'],['Kiev','Kyiv','Europe/Kyiv'],['Moskova','Moscow','Europe/Moscow'],['Lizbon','Lisbon','Europe/Lisbon'],['Dublin','Dublin','Europe/Dublin'],['Reykjavik','Reykjavik','Atlantic/Reykjavik'],
 ['Dubai','Dubai','Asia/Dubai'],['Riyad','Riyadh','Asia/Riyadh'],['Tahran','Tehran','Asia/Tehran'],['Karaçi','Karachi','Asia/Karachi'],['Delhi','Delhi','Asia/Kolkata'],['Mumbai','Mumbai','Asia/Kolkata'],['Dakka','Dhaka','Asia/Dhaka'],['Bangkok','Bangkok','Asia/Bangkok'],['Singapur','Singapore','Asia/Singapore'],['Manila','Manila','Asia/Manila'],['Hong Kong','Hong Kong','Asia/Hong_Kong'],['Şanghay','Shanghai','Asia/Shanghai'],['Pekin','Beijing','Asia/Shanghai'],['Seul','Seoul','Asia/Seoul'],['Tokyo','Tokyo','Asia/Tokyo'],
 ['Sidney','Sydney','Australia/Sydney'],['Melbourne','Melbourne','Australia/Melbourne'],['Auckland','Auckland','Pacific/Auckland'],['Kahire','Cairo','Africa/Cairo'],['Lagos','Lagos','Africa/Lagos'],['Nairobi','Nairobi','Africa/Nairobi'],['Johannesburg','Johannesburg','Africa/Johannesburg']]
// STVAR yalnız geliştirici kurulumunda (ayarlar.gelistirici) ve kullanıcı kendi listesini kaydetmemişken varsayılan; beta'da yalnız yerel saat dilimi (aşağıda kendiliğinden eklenir)
const STVAR=[['Pasifik','America/Los_Angeles'],['Doğu','America/New_York'],['Köln','Europe/Berlin'],['İstanbul','Europe/Istanbul'],['Manila','Asia/Manila']]
let stSira=null,stAcik=false,stListe=null,stT=null,stZam=null,stOner=[],stFC={}
const stYerel=()=>{try{return Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC'}catch(e){return 'UTC'}}
const stKatla=s=>String(s).toLocaleLowerCase('tr').replace(/ı/g,'i').normalize('NFD').replace(/[̀-ͯ]/g,'')  // aramada Türkçe harfler ve büyük/küçük ayrımı yok
const stAd=it=>{const e=STC.find(x=>x[0]===it.ad);return DIL==='en'&&e?e[1]:it.ad}
function stParca(tz,t){let f=stFC[tz];if(!f)f=stFC[tz]=new Intl.DateTimeFormat('en-US',{timeZone:tz,hourCycle:'h23',weekday:'short',year:'numeric',month:'numeric',day:'numeric',hour:'numeric',minute:'numeric',second:'numeric'})
  const o={};f.formatToParts(t).forEach(p=>o[p.type]=p.value);const sa=+o.hour%24
  return{ofs:(Date.UTC(+o.year,+o.month-1,+o.day,sa,+o.minute,+o.second)-Math.floor(t/1000)*1000)/6e4,wd:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].indexOf(o.weekday),dk:sa*60+(+o.minute)}}
const stUtc=m=>'UTC '+(m<0?'-':'+')+Math.floor(Math.abs(m)/60)+(Math.abs(m)%60?':'+String(Math.abs(m)%60).padStart(2,'0'):'')
function stFark(d){if(!d)return L('senle aynı saat');const a=Math.abs(d),sa=Math.floor(a/60),dk=a%60;return(sa?sa+' '+L('sa'):'')+(dk?(sa?' ':'')+dk+' '+L('dk'):'')+' '+(d>0?L('ileride'):L('geride'))}
// mesai içi = iyi; mesai dışında 07:00–22:00 arası (mesaiye yakın, akşam, hafta sonu gündüzü) = orta; gece = kötü
const stRuh=(p,c)=>c.gunler.includes(p.wd)&&p.dk>=c.bas&&p.dk<c.bit?'iyi':p.dk>=420&&p.dk<1320?'orta':'kotu'
function stSatirlar(){const a=last&&last.ayarlar&&last.ayarlar.deger&&last.ayarlar.deger.saatler,l=(stListe||(Array.isArray(a)?a:null)||(last&&last.ayarlar&&last.ayarlar.gelistirici?STVAR.map(([ad,tz])=>({ad,tz})):[])).map((x,i)=>({ad:x.ad,tz:x.tz,i})),y=stYerel()
  if(!l.some(x=>x.tz===y)){const e=STC.find(x=>x[2]===y&&!x[3]);l.unshift({ad:e?e[0]:y.split('/').pop().replace(/_/g,' '),tz:y,i:-1})}  // kullanıcının kendi dilimi listede yoksa kendiliğinden eklenir
  return l}
const stBaz=()=>{const d=new Date();d.setHours(0,0,0,0);return+d}, ST_ADIM=9e5, ST_N=192  // kaydırıcı: bugün 00:00'dan 48 saat, 15 dk adım
function stCiz(){if(!stAcik)return;const loc=L('tr-TR'),t=stT==null?Date.now():stT,y=stYerel(),c=(last&&last.ayarlar&&last.ayarlar.calisma)||{gunler:[0,1,2,3,4],bas:540,bit:1080},ruhAd={iyi:L('Mesai saati'),orta:L('Mesai dışı, makul saat'),kotu:L('Gece')}
  let py;try{py=stParca(y,t)}catch(e){return}
  const sr0=(last&&last.ayarlar&&last.ayarlar.deger&&last.ayarlar.deger.saatler_sira)||'saat',sira=stSira||sr0,sel=document.getElementById('stsr');if(sel.value!==sira)sel.value=sira
  const h=stSirala(stSatirlar(),sira,t).map(it=>{let p;try{p=stParca(it.tz,t)}catch(e){return''}const ben=it.tz===y,ruh=stRuh(p,c),dt=new Date(t)
    const tarih=dt.toLocaleDateString(loc,{timeZone:it.tz,weekday:'short',day:'numeric',month:'short'}),saat=dt.toLocaleTimeString(loc,{timeZone:it.tz,hour:'2-digit',minute:'2-digit',hourCycle:'h23'})
    return`<div class="str${ben?' ben':''}" data-tz="${esc(it.tz)}"><div class=stn><b>${esc(stAd(it))}${ben?`<i class=stsen>${esc(L('sen'))}</i>`:''}</b><span>${stUtc(p.ofs)} · ${esc(stFark(p.ofs-py.ofs))}</span></div><span class=std>${esc(tarih)}</span><span class=stt>${saat}</span><span class="stm ${ruh}" title="${esc(ruhAd[ruh])}" data-ruh=${ruh}>${ic(ruh==='iyi'?'stgun':ruh==='orta'?'stufuk':'stay')}</span>${ben||it.i<0?'<span class=stx0></span>':`<button type=button class="gh ib stx" data-stx="${it.i}" title="${esc(L('Kaldır'))}" aria-label="${esc(L('Kaldır'))}">${ic('x')}</button>`}</div>`}).join('')
  setH(document.getElementById('stl'),h)
  document.getElementById('sttr').textContent=new Date().toLocaleDateString(loc,{weekday:'long'})+', '+new Date().toLocaleDateString(loc,{day:'numeric',month:'long'})  // başlık hep bugün; seçilen an alttaki satırda
  const B=stBaz(),sl=document.getElementById('stsl'),v=Math.max(0,Math.min(ST_N,Math.round((t-B)/ST_ADIM)));if(String(v)!==sl.value)sl.value=v;sl.style.setProperty('--stp',v/ST_N*100+'%')  // koyu temada tarayıcının beyaz izi yerine kendi izimiz
  document.getElementById('stkz').textContent=stT==null?L('Şimdi'):new Date(t).toLocaleString(loc,{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})
  document.getElementById('stsim').hidden=stT==null  // şimdideyken yalnız "Şimdi" yazısı; düğme kaydırınca çıkar
  const an=Date.now(),bs=o=>o.baslangic?+new Date(o.baslangic):o.tarih&&o.saat?+new Date(o.tarih+'T'+o.saat):0,sr=(tkOlaylar||[]).filter(o=>o&&bs(o)>an&&!o.reddettin&&!o.tum_gun).sort((a,b)=>bs(a)-bs(b))[0],mk=document.getElementById('stmk')  // takvimde sıradaki toplantı: kaydırıcıda işaret, tıklayınca oraya gider
  const ms=sr?Math.round(bs(sr)/ST_ADIM)*ST_ADIM:0
  setH(mk,sr&&ms>=B&&ms<=B+ST_N*ST_ADIM?`<button type=button class=stmkb data-stmk="${ms}" style="left:${(ms-B)/(ST_N*ST_ADIM)*100}%" title="${esc((sr.baslik||L('Toplantı'))+' · '+new Date(bs(sr)).toLocaleTimeString(loc,{hour:'2-digit',minute:'2-digit',hourCycle:'h23'}))}" aria-label="${esc(sr.baslik||L('Toplantı'))}"></button>`:'')}
function stAc(ac){stAcik=!!ac;if(stAcik&&hfAcik)hfAc(false);document.documentElement.classList.toggle('saatler-ac',stAcik);document.getElementById('sts').hidden=!stAcik;document.getElementById('tkst').classList.toggle('on',stAcik);clearInterval(stZam);stZam=null
  if(stAcik){stT=null;kcSec='tv';stCiz();stZam=setInterval(()=>{if(stT==null)stCiz()},60000);if(last)kenarCiz(last,document.documentElement.classList.contains('toplantida'))}  // kaydırma şimdi değilken dakikalık yenileme yok
  else if(kcSec==='tv'&&!hfAcik){kcSec={bugun:'tks',kayit:'kr'}[bnGor]||bnGor;if(last)kenarCiz(last,document.documentElement.classList.contains('toplantida'))}
  tvCiz()}
// sıralama (4 Kasım, kullanıcı): saate göre (UTC farkı; aynı farkta ada göre), ada göre ya da eklenme sırası — yalnız görünüm, liste sırası değişmez; seçim ayar `saatler_sira`
function stSirala(l,sira,t){if(sira==='ekleme')return l;const ad=it=>stKatla(stAd(it)),of=it=>{try{return stParca(it.tz,t).ofs}catch(e){return 0}}
  const k=sira==='ad'?(a,b)=>ad(a).localeCompare(ad(b),L('tr-TR')):(a,b)=>(of(a)-of(b))*(sira==='saat_azalan'?-1:1)||ad(a).localeCompare(ad(b),L('tr-TR'))
  return l.slice().sort(k)}
document.getElementById('stsr').addEventListener('change',async ev=>{stSira=ev.target.value;stCiz();let r={};try{r=await j('/ayar',{method:'POST',body:JSON.stringify({degisen:{saatler_sira:stSira}})})}catch(e){}if(!r.ok)geciciDurum(L('Sıralama kaydedilemedi'),r.err||'')})
async function stYaz(){let r={};try{r=await j('/ayar',{method:'POST',body:JSON.stringify({degisen:{saatler:stListe}})})}catch(e){}if(!r.ok)geciciDurum(L('Saat listesi kaydedilemedi'),r.err||'')}
function stEkle(ad,tz){stListe=(stListe||stSatirlar().filter(x=>x.i>=0)).map(x=>({ad:x.ad,tz:x.tz})).concat([{ad,tz}]);stYaz();stCiz()}
function stAra(q){q=stKatla(q.trim());if(!q)return[];const gor=new Set(stSatirlar().map(x=>x.tz)),out=[]
  STC.forEach(([tr,en,tz])=>{if(gor.has(tz))return;const a=stKatla(tr),b=stKatla(en);if(a.includes(q)||b.includes(q))out.push({ad:tr,tz,etiket:DIL==='en'?en:tr,s:a.startsWith(q)||b.startsWith(q)?0:1})})
  let z=[];try{z=Intl.supportedValuesOf('timeZone')}catch(e){}
  z.forEach(tz=>{if(gor.has(tz)||out.some(o=>o.tz===tz))return;const se=tz.split('/').pop().replace(/_/g,' ');if(stKatla(se).includes(q)||stKatla(tz).includes(q))out.push({ad:se,tz,etiket:se,s:stKatla(se).startsWith(q)?0:2})})
  return out.sort((a,b)=>a.s-b.s).slice(0,8)}
function stOnerCiz(){const q=document.getElementById('stq').value,o=document.getElementById('stoner');stOner=stAra(q);o.hidden=!stOner.length;o.innerHTML=stOner.map((x,i)=>`<button type=button data-stek="${i}"${i?'':' class=on'}><span>${esc(x.etiket)}</span><small>${esc(x.tz)}</small></button>`).join('')}
function stSec(i){const x=stOner[i];if(!x)return;stEkle(x.ad,x.tz);document.getElementById('stq').value='';stOnerCiz()}
document.getElementById('stq').addEventListener('input',stOnerCiz)
document.getElementById('stq').addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();stSec(0)}else if(ev.key==='Escape'){ev.target.value='';stOnerCiz();ev.stopPropagation()}})
document.getElementById('stoner').addEventListener('click',ev=>{const b=ev.target.closest('[data-stek]');if(b)stSec(+b.dataset.stek)})
document.getElementById('stl').addEventListener('click',ev=>{const b=ev.target.closest('[data-stx]');if(!b||!stListe&&!stSatirlar().some(x=>x.i>=0))return;const i=+b.dataset.stx;stListe=stSatirlar().filter(x=>x.i>=0&&x.i!==i).map(x=>({ad:x.ad,tz:x.tz}));stYaz();stCiz()})
document.getElementById('stsl').addEventListener('input',ev=>{stT=stBaz()+(+ev.target.value)*ST_ADIM;stCiz()})
document.getElementById('stsim').onclick=()=>{stT=null;stCiz()}
document.getElementById('stmk').addEventListener('click',ev=>{const b=ev.target.closest('[data-stmk]');if(b){stT=+b.dataset.stmk;stCiz()}})
document.getElementById('stbg').onclick=()=>stAc(false);document.getElementById('sth7').onclick=()=>hfAc(true);document.getElementById('tkst').onclick=()=>stAc(true)
document.addEventListener('click',ev=>{if(!ev.target.closest('.sta')){const o=document.getElementById('stoner');if(o)o.hidden=true}})
document.getElementById('tky').onclick=()=>{fetch('/takvim-yenile',{method:'POST',body:'{}'});document.getElementById('tkh').textContent=L('takvim yenileniyor…')}
document.getElementById('tk').addEventListener('click',ev=>{const k=ev.target.closest('button[data-kat]');if(k&&/^https:\/\//.test(k.dataset.kat))return window.open(k.dataset.kat,'_blank');const b=ev.target.closest('button[data-bas]');if(b){const o=b.dataset.bas?tkBul(b.dataset.bas):null;if(o&&o.baglanti&&last&&!last.aktif&&last.toplanti&&last.toplanti.son)return hizliBaslat(o,b);return tkForm(o)}
  const hz=ev.target.closest('button[data-hz]');if(hz)return hazirlikTik(hz.dataset.hz,hz)
  const sec=ev.target.closest('[data-sec]');if(sec){tkGor=sec.dataset.sec;if(last){renderTakvim(last);agSig="";refresh()}}})
