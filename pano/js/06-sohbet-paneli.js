// v0.212.0 sohbet paneli (kullanıcı, 9 Kasım — seçenek A): asistanla konuşma sağdan açılan panelde (#shp); yer yetiyorsa yan sütun, yetmiyorsa içeriğin üstüne katman (shYerlesim); her sayfada aynı panel ve
// aynı konuşma (KC). Açılış: toplantı dışında soru sorunca (kutu, Konuş, kısayol) kendiliğinden; başlıktaki düğme ya da kapalı panelin tek satırı. Toplantıda varsayılan kapalı (kartlar,
// döküm, Ne diyeyim? akışı aynen). Yenilenince son 20 tur /konus-gecmis'ten (tam yazılı cevap; gizli kip turları gösterilmez). Kutu (.kt) panel açıkken panelin altına taşınır.
// Onay bekleyen kayıt kartları (izin "kayit", /card-ack) ve sesli talimat onayları (eylem kuyruğu, /eylem-karar) ilgili cevabın altında. Mini pano ve Mac menü paneli eski kısa görünümde.
var shSekmeAcik=false,shSekme='gundem',shSekmeOnce='gundem',shSesBek=0,shSesSur=0,shAcik=false,shTop=false,shSor=false,shIlk=true,shYuk=0,shSig='',shSur=-1,shBagT=Date.now(),shKapSur=0,shW=420
const SH_ANA_EN=720,SH_MIN=340,SH_MAX=760,SH_VARS=420  // ana içeriğin en dar hâli (yan sütun kipi için), panelin en dar/en geniş/varsayılan genişliği
const SH_GECMIS=20,SH_TALIMAT=['oturum','yapilacak','is','sil','toplanti']
ICO.chev='<path d="M9 6l6 6-6 6"/>';ICO.panel='<rect x=3 y=4 width=18 height=16 rx=2 /><path d="M14.5 4v16"/>';ICO.genis='<path d="M14 4h6v6M10 20H4v-6M20 4l-6.5 6.5M4 20l6.5-6.5"/>';ICO.daral='<path d="M20 4l-6 6M14 5v5h5M4 20l6-6M10 19v-5H5"/>'
function shKayit(k,v){try{if(v==null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){}}  // yalnız kişisel kolaylık (panel açık mı, geniş mi); okunamazsa varsayılan
function shOku(k){try{return localStorage.getItem(k)}catch(e){return null}}
// S260: toplantıda (sekmeli sütun) açmak = {asistan} sekmesini seçmek, kapatmak = önceki sekmeye dönmek; katman açılmaz. Araç çubuğu, başlık düğmesi, shFab ve panoBolum('sohbet') buradan geçer.
function shAc(ac,odak){ac=ac!==false;if(shSekmeAcik){shSekmeSec(ac?'marvin':shSekmeOnce,odak,true);return}shAcIc(ac,odak)}
function shAcIc(ac,odak,kaydetme){const n=document.getElementById('n');if(ac===shAcik){if(ac&&odak)n.focus();return}
  if(ac&&/(^| )(panel|ayarlar|yardim)( |$)/.test(document.documentElement.className))return  // menü paneli, Ayarlar ve Yardım pencerelerinde sohbet paneli yok (kısa görünüm kalır)
  const f=document.activeElement===n,kt=n.closest('.kt'),kal=document.getElementById('kal'),yer=ac?document.getElementById('shk'):document.getElementById('nb')
  shAcik=ac;document.getElementById('shp').hidden=!ac;document.documentElement.classList.toggle('sh-acik',ac);yer.appendChild(kt);yer.appendChild(kal);shKapSur=kcSur;shYerlesim();shFab(last)
  const b=document.getElementById('shb');b.classList.toggle('on',ac);b.setAttribute('aria-expanded',String(ac))
  if(!toplantidaMi(last)&&!kaydetme)shKayit('shAcik',ac?'1':null)  // toplantıda açıp kapatmak toplantı dışı tercihini değiştirmez
  shSig='';shSur=-1;if(ac)shGecmisYukle();if(f||odak)n.focus();if(last){renderKonus(last);paintCards(document.getElementById("kc"),last);document.getElementById('sk').hidden=!last.aktif&&!shKartlar(last).length&&!(last.questions||[]).length&&!(last.claude_age_s!=null&&last.claude_age_s<120);document.title=(shKartlar(last).length?`(${shKartlar(last).length}) `:"")+"Suflor.me pano"}}
async function shGecmisYukle(){if(shYuk)return;shYuk=1;let r=null;try{r=await j('/konus-gecmis')}catch(e){}
  if(!r||!Array.isArray(r.kayitlar)){shYuk=0;return}  // aktarıcıya ulaşılamadı: sonraki açılışta yeniden
  const H=r.kayitlar.filter(x=>!x.gizli&&x.soru).slice(0,SH_GECMIS).reverse().map(x=>({soru:String(x.soru),cevap:kcTemiz(x.yazili||x.sesli||''),ad:AG(x.kisilik)||AS,sesli:['bas','sohbet','hitap'].includes(x.kaynak),t:Date.parse(x.at)||0,gecmis:true}))
    .filter(h=>!KC.some(e=>kcNorm(e.soru)===kcNorm(h.soru)))  // bu sayfada zaten olan tur (cevabı daha güncel) kalır
  KC.unshift(...H);while(KC.length>KC_N)KC.shift();kcSur++;shSig='';if(last)renderKonus(last)}
function shBekleyenEk(){return (((last||{}).baglam)||[]).filter(x=>['kutu','birak'].includes(x.kaynak)&&(Date.parse(x.at)||0)>shBagT-1000).map(x=>({ad:x.ad,tur:x.tur}))}
// kutudan gönderilen soru cevabı beklemeden panelde görünür (aktarıcı turu alınca aynı kayda işlenir); not ya da gönderilemeyen yazı geri alınır
function shGonder(t){shAc(true,true);const e={soru:t.trim(),cevap:'',ad:AS,sesli:false,t:Date.now(),bekliyor:true,ek:shBekleyenEk()};KC.push(e);if(KC.length>KC_N)KC.shift();shBagT=Date.now();kcSur++;if(last)renderKonus(last);return e}
function shGonderSonuc(e,t,ok){if(e&&!ok){const i=KC.indexOf(e);if(i>=0){KC.splice(i,1);kcSur++}}else if(!e&&ok&&shAcik){KC.push({soru:t.trim(),cevap:'',ad:AS,sesli:false,t:Date.now(),bekliyor:true,ek:shBekleyenEk()});shBagT=Date.now();kcSur++}if(last)renderKonus(last)}
// toplantı dışında yeni tur başladı (kısayol, sohbet, başka pencere): panel açılır. İlk çizimde yalnız kayıtlı tercih (açık bırakılmışsa) uygulanır.
function shYeniTur(s,s0){const top=toplantidaMi(s),gec=top!==shTop;shTop=top
  if(shIlk){shIlk=false;if(shOku('shAcik')==='1'&&!top&&!terminalAcik(s))setTimeout(()=>shAc(true,false));return}
  if(gec){shSesBek=0;if(top){kcTop=Date.now();setTimeout(()=>{if(shAcik&&!shSekmeAcik)shAc(false)})}else setTimeout(()=>{if(!shAcik&&shOku('shAcik')==='1'&&!terminalAcik(last||s))shAc(true,false)});return}  // toplantı başlayınca panel kapanır (kartlar, döküm öne; sekmeli sütunda son sekme), bitince tercih geri gelir
  if(top){const k=s.konus||{};if(kRec||k.durum==='yaziya'){shSesBek=Date.now();shSesSur=kcSur}  // S260: sesle başlatılan Konuş turu (basılı tut ya da kısayol) — cevap gelince {asistan} sekmesi öne gelir
    else if(shSesBek&&Date.now()-shSesBek>120000)shSesBek=0
    else if(shSesBek&&kcSur!==shSesSur&&(KC[KC.length-1]||{}).cevap){shSesBek=0;setTimeout(()=>{if(shSekmeAcik&&!shAcik)shSekmeSec('marvin',false)})}}
  const sor=!!(s.eylem&&s.eylem.sesli),yeniSor=sor&&!shSor;shSor=sor  // "Yazayım mı?" sesli onay sorusu da paneli açar (cevap ipucu orada)
  if((kcSur!==s0||yeniSor)&&!shAcik&&!top&&!terminalAcik(s))setTimeout(()=>shAc(true,false))}
function shGenisle(g,kaydetme){const h=document.documentElement;g=g==null?!h.classList.contains('sh-genis'):g;h.classList.toggle('sh-genis',g);const b=document.getElementById('shw'),t=L(g?'Paneli daralt':'Paneli genişlet')
  b.innerHTML=ic(g?'daral':'genis');b.title=t;b.setAttribute('aria-label',t);if(!kaydetme)shKayit('shGenis',g?'1':null);shYerlesim()}
// yerleşim: ana içerik panelden sonra en az SH_ANA_EN kalıyorsa yan sütun (içerik o kadar daralır), kalmıyorsa katman (içerik hiç daralmaz); odak kipinde ve dar ekranda katman
function shYerlesim(){const h=document.documentElement;if(!shAcik||shSekmeAcik){h.classList.remove('sh-yan','sh-katman');return}  // sekmeli sütunda panel akışın içinde
  const dar=matchMedia('(max-width:720px)').matches,g=h.classList.contains('sh-genis')&&!dar,m=document.querySelector('main'),yan0=h.classList.contains('sh-yan')
  const taban=m?m.getBoundingClientRect().width+(yan0?shW:0):0,yan=!g&&!dar&&taban-shW>=SH_ANA_EN
  h.classList.toggle('sh-yan',yan);h.classList.toggle('sh-katman',!yan&&!g)}
function shGenAyarla(w){shW=Math.round(Math.max(SH_MIN,Math.min(SH_MAX,w)));document.documentElement.style.setProperty('--sw',shW+'px')}
// kapalı paneli açan sağ alt düğme: yeni cevap (toplantıda) ya da sesli sohbetin devam penceresi varsa nokta
function shFab(s){const b=document.getElementById('shfab');if(!b)return;const so=((s||{}).konus||{}).sohbet||{},dv=!!(so.acik&&so.devam),n=b.querySelector('.nk')
  const yeni=!shAcik&&kcSur!==shKapSur&&toplantidaMi(s||{})  // toplantıda panel kendiliğinden açılmaz: kapandıktan sonra yeni tur → nokta
  n.hidden=!(yeni||dv);b.classList.toggle('devam',dv);{const sb=document.getElementById('shb');if(sb)sb.classList.toggle('nokta',(yeni||dv)&&!shAcik)}const ad=asGor((s||{}).konus),t=dv?L('{ad} dinliyor — paneli aç',{ad}):yeni?L('{ad} cevap verdi — paneli aç',{ad}):L('{ad} paneli',{ad})
  if(b.title!==t){b.title=t;b.setAttribute('aria-label',t)}}
// S260 (seçenek B): toplantıda tek sağ sütun, sekmeli — Döküm · Gündem · {asistan}. Sohbet paneli (#shp) sütunun içine taşınır; {asistan} sekmesi seçiliyken shAcik (kutu panelde,
// kayıt onay kartları panelde), değilken kapalı (kutu ana alanda, kartlar ana listede). Kapalı sekmeye yeni cevap → nokta, onay kartı → sayı. Son sekme hatırlanır (yanSekme).
const YSK=['dokum','gundem','marvin']
function shSekmeli(){const h=document.documentElement;return h.classList.contains('toplantida')&&!h.matches('.bugun,.hafta-ac,.saatler-ac,.panel,.ayarlar,.yardim')}
function shSekmeKur(){const on=shSekmeli();if(on===shSekmeAcik)return;const h=document.documentElement,p=document.getElementById('shp'),a=document.querySelector('aside')
  if(on){if(!shSekmeKur.yer)shSekmeKur.yer=[p.parentNode,p.nextSibling];shSekmeAcik=true;h.classList.add('sh-sekmeli');a.insertBefore(p,document.getElementById('dkh'))
    const t=shOku('yanSekme');shSekmeSec(YSK.includes(t)?t:'gundem',false,false);return}
  shSekmeAcik=false;shAcIc(false,false,true);h.classList.remove('sh-sekmeli');const [y,sn]=shSekmeKur.yer;y.insertBefore(p,sn&&sn.parentNode===y?sn:null)
  if(dkAcik!==(shOku('dk')==='1'))dokumAc(shOku('dk')==='1')}  // döküm katı toplantı dışı tercihine döner
// t: dokum|gundem|marvin; acik: kullanıcı ya da araç çubuğu istedi (gizli sütunu açar). Seçim kaydedilir; gizli Mac sütununda {asistan} seçilmez (kutu görünmez kalırdı)
function shSekmeSec(t,odak,acik){if(!YSK.includes(t))t='gundem';if(!shSekmeAcik)return;const h=document.documentElement,a=document.querySelector('aside')
  if(t==='marvin'&&h.classList.contains('yan-kapali')){if(acik)yanAcKapa();else t=shSekmeOnce}
  if(t!=='marvin')shSekmeOnce=t;shSekme=t;a.dataset.sekme=t;shKayit('yanSekme',t)
  if(t==='dokum'&&!dkAcik){dkAcik=true;a.classList.add('dk-acik');main.hidden=false;main.scrollTop=main.scrollHeight;atBottom=true}  // döküm sekmesi: katlı tercih ('dk') değişmez
  for(const b of a.querySelectorAll('.ysk [data-ysk]'))b.setAttribute('aria-selected',String(b.dataset.ysk===t))
  shAcIc(t==='marvin',odak);if(last)shSekmeCiz(last)}
function shSekmeCiz(s){if(!shSekmeAcik)return;const ad=asGor((s||{}).konus),e=document.getElementById('yska'),b=document.getElementById('yskm'),n=document.getElementById('yskn')
  if(e.textContent!==ad)e.textContent=ad
  const on=shAcik?0:shOnaylar(s||{}).length,yeni=!shAcik&&kcSur!==shKapSur,t=on?L('{ad} — {n} onay bekliyor',{ad,n:on}):yeni?L('{ad} cevap verdi',{ad}):ad
  n.hidden=!(on||yeni);n.classList.toggle('sy',!!on);const nt=on?String(on):'';if(n.textContent!==nt)n.textContent=nt
  if(b.title!==t){b.title=t;b.setAttribute('aria-label',t)}}
{const y=document.querySelector('aside .ysk');y.addEventListener('click',ev=>{const b=ev.target.closest('[data-ysk]');if(b)shSekmeSec(b.dataset.ysk,b.dataset.ysk==='marvin',true)})
  y.addEventListener('keydown',ev=>{const d={ArrowRight:1,ArrowLeft:-1}[ev.key];if(!d||!shSekmeAcik)return;ev.preventDefault();const t=YSK[(YSK.indexOf(shSekme)+d+3)%3];shSekmeSec(t,false,true);const b=y.querySelector(`[data-ysk=${t}]`);if(b)b.focus()})}
function shPil(k){const e=KC[KC.length-1];if(!e)return''
  const m=String(e.cevap||e.soru||'').split(/\n\s*-{3,}/)[0].replace(/[*`#>|_]/g,'').replace(/\s+/g,' ').trim()
  return `<button type=button class=shpil data-shac title="${esc(L('Konuşmayı panelde aç'))}">${ic('sohbet')}<span class=a>${esc(AG(e.ad)||asGor(k))}</span><span class=m>${esc(m)}</span><span class=o>${esc(L('Konuşmayı aç'))}</span></button>`}
const shSaat=t=>{try{return new Date(t).toLocaleTimeString(DIL==='en'?'en-GB':'tr-TR',{hour:'2-digit',minute:'2-digit'})}catch(e){return''}}
function shGun(t){if(!t)return'';const d=new Date(t),b=new Date(),g=x=>x.getFullYear()+'-'+x.getMonth()+'-'+x.getDate(),dun=new Date(b.getFullYear(),b.getMonth(),b.getDate()-1)
  if(g(d)===g(b))return L('Bugün');if(g(d)===g(dun))return L('Dün');try{return d.toLocaleDateString(DIL==='en'?'en-GB':'tr-TR',{day:'numeric',month:'long',weekday:'long'})}catch(e){return''}}
const shCip=x=>`<span class=shcp title="${esc(x.ad)}">${ic(x.tur==='dosya'?'dosya':'bag')}<span>${esc(x.ad)}</span></span>`
function shOnKart(m,a,r){return`<div class=shon role=group aria-label="${esc(L('Onay bekliyor'))}"><div class=shot>${ic('zil')}<span>${esc(L('Onay bekliyor'))}</span></div><div class=shom>${bag(esc(m))}</div><div class=shob><button type=button class=pri ${a}>${esc(L('Onayla'))}</button><button type=button class=gh ${r}>${esc(L('Reddet'))}</button></div></div>`}
// onay bekleyenler: asistanın kayıt önerisi (kart, izin "kayit") ve sesle verilen talimat (eylem kuyruğu, yerel). Zaman eylem kimliğinden (e<ms>…)
function shOnaylar(s){const r=[],T=id=>{const m=/^e(\d{12,})/.exec(id||'');return m?+m[1]:0}
  for(const c of s.cards||[])if(c.onay&&c.izin==='kayit')r.push({t:T(c.eylem)||Date.now(),h:shOnKart(String(c.text||'').replace(/^(?:İzin|Permission):\s*/,''),`data-ack=onaylandi data-id="${esc(c.id)}"`,`data-ack=reddedildi data-id="${esc(c.id)}"`)})
  for(const x of ((s.eylem||{}).liste||[]))if(x.durum==='bekliyor'&&x.yerel&&SH_TALIMAT.includes(x.tur))r.push({t:T(x.id)||Date.parse(x.at)||Date.now(),h:shOnKart((EYT[x.tur]||x.tur)+': '+(x.baslik||''),`data-shey=onaylandi data-id="${esc(x.id)}"`,`data-shey=reddedildi data-id="${esc(x.id)}"`)})
  return r}
// Kararlar ve işler → «asistana sor» turunda (e.kayit) cevabın altında: cevap tamamlandıysa «Kayda not olarak ekle» (bkz. kayitaNot); eklenince «Kayda eklendi»
function shKyz(e,i){if(!e.kayit||!(e.cevap||'').trim()||e.bekliyor||(i===KC.length-1&&KONUS_SUREN.includes(((last||{}).konus||{}).durum)))return''
  return e.kayitYazildi?`<span class=kyz>${ic('check')}${esc(L('Kayda eklendi'))}</span>`:`<button type=button class=kop data-kyz=${i}${e.kayitYaz?' disabled':''}>${ic('belge')}<span>${esc(L('Kayda not olarak ekle'))}</span></button>`}
function shTur(e,i,onh){const p=e.cevap?e.cevap.split(/\n\s*-{3,}\s*\n?/):[],ky=(p[0]||'').trim(),ay=p.slice(1).join('\n').trim()
  const ek=(e.ek||[]).length?`<div class=shc>${e.ek.map(shCip).join('')}</div>`:''
  const u=e.soru?`<div class="shu${e.bekliyor?' bek':''}"${e.sesli?` title="${esc(L('Sesle soruldu'))}"`:''}>${e.sesli?ic('mik'):''}${esc(e.soru)}</div>`:''
  const sg=kcKonus(ky),a=ky||ay?`<div class=sha>${sg?sg.map(g=>`${g.ad?`<div class=shad>${esc(g.ad)}</div>`:''}<div class=kcm>${kcMd(g.t)}</div>`).join(''):`<div class=kcm>${kcMd(ky)}</div>`}${ay?`<button type=button class="shay-d${e.ayAcik?' ac':''}" data-shay=${i} aria-expanded=${e.ayAcik?'true':'false'}>${ic('chev')}<span>${esc(L('Ayrıntı'))}</span></button>${e.ayAcik?`<div class=shay><div class=kcm>${kcMd(ay)}</div></div>`:''}`:''}<div class=shx><button type=button class=kop data-kop=${i} title="${esc(L('Kopyala'))}" aria-label="${esc(L('Kopyala'))}">${ic('kopya')}</button>${shKyz(e,i)}${e.t?`<span>${esc(shSaat(e.t))}</span>`:''}</div></div>`:''
  return`<div class=sht>${ek}${u}${a}${onh}</div>`}
function shDurum(s){const k=s.konus||{},ad=asGor(k),son=KC[KC.length-1]
  const nk=t=>`<div class=shd role=status><span class=shnk aria-hidden=true><i></i><i></i><i></i></span><span>${esc(t)}</span></div>`
  if(kRec)return''
  if(k.durum==='konusuyor')return`<div class="shd ok" role=status>${ic('hoparlor')}<span>${esc(L('{ad} sesli okuyor',{ad}))}</span><button type=button data-sus>${esc(L('Sus'))}</button></div>`
  if(k.durum==='yaziya')return nk(L('Yazıya döküyorum…'))
  if(k.durum==='dusunuyor'||(son&&son.bekliyor))return nk(L('{ad} düşünüyor…',{ad}))
  if(k.durum==='hata'&&k.hata)return`<div class="shd er" role=status>${ic('uyari')}<span>${esc(k.hata)}</span></div>`
  return kcDurum?`<div class=shd role=status><span>${esc(kcDurum)}</span></div>`:''}
function shBos(ad){const o=['Bugün neye bakmalıyım?','Geciken işlerim neler?','Son toplantıda neye karar verdik?']
  return`<div class=shbos><h3>${esc(ad)}</h3><p>${esc(L('Bugünü sor, iş ver, kararı kayda geçirt ya da bir konuyu araştırt. Yazabilir ya da mikrofonu basılı tutup konuşabilirsin.'))}</p>${kcDf}<div class=shoner>${o.map(x=>`<button type=button data-shoner="${esc(L(x))}">${esc(L(x))}</button>`).join('')}</div></div>`}
function shCiz(s){if(!shAcik)return;const k=s.konus||{},ad=asGor(k),ae=document.getElementById('shad');if(ae.textContent!==ad)ae.textContent=ad
  {const du=document.getElementById('shdu'),t=kRec?L('dinliyor'):k.durum==='konusuyor'?L('konuşuyor'):['yaziya','dusunuyor'].includes(k.durum)?L('düşünüyor'):'';if(du.textContent!==t)du.textContent=t;du.classList.toggle('on',!!t)}
  {const c=document.getElementById('shc'),yb=new Set(shBekleyenEk().map(x=>x.ad)),h=(s.baglam||[]).map(x=>shCip(x).replace('class=shcp',`class="shcp${yb.has(x.ad)?' yeni':''}"`)).join('');if(c.__h!==h){c.innerHTML=h;c.__h=h;c.title=h?L('{ad} bu belgeleri okur',{ad}):''}}  // 9 Kasım: toplantı yokken yan sütun gizli; bağlam belgeleri burada kaybolmaz
  const on=shOnaylar(s),bas=e=>e.gecmis?e.t-120000:e.t,yer=o=>{let r=-1;KC.forEach((e,i)=>{if(bas(e)<=o.t+2000)r=i});return r<0?KC.length-1:r}  // geçmiş kaydının zamanı turun sonu
  const kol={};for(const o of on){const i=yer(o);(kol[i]=kol[i]||[]).push(o.h)}
  let h='',gun='';KC.forEach((e,i)=>{const g=shGun(e.t);if(g&&g!==gun){gun=g;h+=`<div class=shg>${esc(g)}</div>`}h+=shTur(e,i,(kol[i]||[]).join(''))})
  if(!KC.length)h=shBos(ad)+(kol[-1]||[]).join('')
  h+=shDurum(s)
  const sc=document.getElementById('shl'),dip=sc.scrollHeight-sc.scrollTop-sc.clientHeight<48
  if(h!==shSig){shSig=h;const y=sc.scrollTop;setH(sc,h);sc.scrollTop=y}
  if(shSur!==kcSur){shSur=kcSur;const ts=sc.querySelectorAll('.sht'),t=ts[ts.length-1];  // yeni soru ya da cevap: uzun cevapta başı görünsün, kısada en alta
    sc.scrollTop=t&&t.offsetHeight>sc.clientHeight-32?t.offsetTop-sc.offsetTop-16:sc.scrollHeight}
  else if(dip)sc.scrollTop=sc.scrollHeight}  // altta okuyordu: durum satırı değişince altta kalır
{const sl=document.getElementById('shl');bindAck(sl)
  sl.addEventListener('click',ev=>{const b=ev.target.closest('button[data-shey]');if(b){ev.stopPropagation();eylemKarar(b.dataset.id,b.dataset.shey,b);return}
    const ay=ev.target.closest('button[data-shay]');if(ay){const e=KC[+ay.dataset.shay];if(e){e.ayAcik=!e.ayAcik;shSig='';if(last)shCiz(last)}return}
    const o=ev.target.closest('button[data-shoner]');if(o){const n=document.getElementById('n');n.value=o.dataset.shoner;boyla(n);n.focus();if(n.__gonder)n.__gonder(false)}})
  document.getElementById('shx').innerHTML=ic('x');document.getElementById('shx').onclick=()=>shAc(false,true)
  document.getElementById('shg').innerHTML=ic('hist');document.getElementById('shg').onclick=()=>gecmisAc()
  document.getElementById('shw').onclick=()=>shGenisle();shGenisle(shOku('shGenis')==='1',true)
  document.getElementById('shb').innerHTML=ic('panel');document.getElementById('shb').onclick=()=>shAc(!shAcik,true)
  document.getElementById('shp').addEventListener('keydown',ev=>{if(ev.key==='Escape'&&!shSekmeAcik&&!ev.defaultPrevented&&!document.querySelector('dialog[open]')){ev.preventDefault();if(document.documentElement.classList.contains('sh-genis'))shGenisle(false);else shAc(false,true)}})
  {const b=document.getElementById('shfab');b.insertAdjacentHTML('afterbegin',ic('sohbet'));b.onclick=()=>shAc(true,true)}
  {const v=parseInt(shOku('shW'),10);shGenAyarla(v>0?v:SH_VARS)}
  const rz=document.getElementById('shrz'),kaydet=()=>shKayit('shW',shW===SH_VARS?null:String(shW))
  const sinir=()=>{const h=document.documentElement,m=document.querySelector('main'),kw=parseFloat(getComputedStyle(h).getPropertyValue('--kw'))||0
    return h.classList.contains('sh-yan')?Math.max(SH_MIN,m.getBoundingClientRect().width+shW-SH_ANA_EN):Math.max(SH_MIN,innerWidth-kw-80)}  // yan sütunda içerik SH_ANA_EN'in altına inmez
  rz.addEventListener('pointerdown',ev=>{if(ev.button)return;ev.preventDefault();const mx=sinir();rz.setPointerCapture(ev.pointerId);rz.classList.add('on')
    const mv=e=>{shGenAyarla(Math.min(mx,innerWidth-e.clientX))},bit=()=>{rz.classList.remove('on');rz.removeEventListener('pointermove',mv);rz.removeEventListener('pointerup',bit);rz.removeEventListener('pointercancel',bit);kaydet();shYerlesim()}
    rz.addEventListener('pointermove',mv);rz.addEventListener('pointerup',bit);rz.addEventListener('pointercancel',bit)})
  rz.addEventListener('dblclick',()=>{shGenAyarla(SH_VARS);kaydet();shYerlesim()})
  rz.addEventListener('keydown',ev=>{const d={ArrowLeft:24,ArrowRight:-24}[ev.key];if(!d)return;ev.preventDefault();shGenAyarla(Math.min(sinir(),shW+d));kaydet();shYerlesim()})
  // katman ve odak kipinde dışarı tıklama kapatır (yan sütunda panel içeriğin yanında durur, kapatmaz)
  document.addEventListener('pointerdown',ev=>{const h=document.documentElement;if(!shAcik||shSekmeAcik||!h.matches('.sh-katman,.sh-genis'))return;const t=ev.target
    if(!(t instanceof Element)||t.closest('#shp,#shb,#shfab,[data-shac],dialog,#bnPanel,#bnPerde,.emk'))return;shAc(false)},true)
  {let rq=0;addEventListener('resize',()=>{if(!rq)rq=requestAnimationFrame(()=>{rq=0;shYerlesim()})})}
  {const nb=document.getElementById('nb');if(nb&&window.ResizeObserver)new ResizeObserver(()=>document.documentElement.style.setProperty('--nb-h',nb.offsetHeight+'px')).observe(nb)}}  // 19 Kasım (Y5): kutu + son cevap şeridinin yüksekliği → Bugün içeriğinin alt boşluğu (bugun.css)
// yan panelde konuşma geçmişi (cevaba dokununca; kaynak Konuş geçmişi — /konus-gecmis); "Tümü" Arşiv'deki pencereyi açar
async function konusmaAc(){const sec=document.getElementById('kos');sec.hidden=false;document.documentElement.classList.remove('yan-kapali','yan-bos');let r={};try{r=await j('/konus-gecmis')}catch(e){}
  const k=(r.kayitlar||[]).slice(0,20),tr=a=>{try{const x=new Date(a);return x.toLocaleDateString(DIL==='en'?'en-GB':'tr-TR',{day:'numeric',month:'short'})+' '+x.toLocaleTimeString(DIL==='en'?'en-GB':'tr-TR',{hour:'2-digit',minute:'2-digit'})}catch(e){return a||''}}
  setH(document.getElementById('ko'),k.length?k.map(x=>`<div class=kor><div class=z>${esc(tr(x.at))}${x.kisilik?' · '+esc(AG(x.kisilik)):''}</div><div class=s>${esc(x.soru||'')}</div><div class=c>${esc(x.sesli||'')}</div></div>`).join(''):`<div class=empty>${esc(r.acik===false?L('Kayıt kapalı — yeni soru kaydedilmez.'):L('Henüz kayıt yok.'))}</div>`)
  document.getElementById('yan').scrollTop=0}
document.getElementById('kosx').innerHTML=ic('x');document.getElementById('kosx').onclick=()=>{document.getElementById('kos').hidden=true}
document.getElementById('kosa').onclick=()=>gecmisAc()
// toplantı öncesi brifing: boş panoda seçili takvim toplantısı için, dokununca (Claude yalnız okur; sonuç gün boyu saklanır)
function renderBrifing(s){const sec=document.getElementById('brs'),izliyor=s.claude_age_s!=null&&s.claude_age_s<120,o=tkGor&&tkBul(tkGor)
  if(!!s.aktif||!o){sec.hidden=true;return}  // 3 Kasım: Claude toplantı sonunu yaparken (izliyor) de görünür
  sec.hidden=hzAc!==o.id  // 30 Ekim: kartın altında, yalnız kartın Hazırlık bağlantısıyla açılır
  // okunan brifing başlık hariç gizlenebilir (kullanıcı, 9 Ekim); toplantı başına tarayıcıda hatırlanır
  const kb=document.getElementById('brk');kb.textContent=L('Gizle');kb.setAttribute('aria-expanded',!sec.hidden);kb.dataset.olay=o.id
  document.getElementById('brn').textContent=o.baslik;const b=(s.brifing||{})[o.id]||(o.hazirlik_sonuc?{durum:'hazir',sonuc:o.hazirlik_sonuc}:{}),ls=(a,t)=>a&&a.length?`<div class=bb>${L(t)}</div><ul>${a.map(x=>`<li>${bag(esc(x))}</li>`).join('')}</ul>`:''
  setH(document.getElementById('br'),b.durum==='hazir'?`${b.sonuc.ozet?`<div class=b>${esc(b.sonuc.ozet)}</div>`:''}${ls(b.sonuc.veri,'Güncel veri')}${ls(b.sonuc.dikkat,'Dikkat')}${ls(b.sonuc.acik,'Açık kalanlar')}${ls(b.sonuc.dis_taraf,b.sonuc.dis_etiket||'Dış taraf')}${ls(b.sonuc.gecmis,'Geçmişte')}<div class=bt><button class=gh data-brf="${esc(o.id)}" data-dinle=1 title="${L('Brifingi sesli okur (Mac sesi); tekrar basınca susar')}">${ic('hoparlor',L('Dinle'))}</button><button class=gh data-brf="${esc(o.id)}" data-yeniden=1>${L('Yeniden hazırla')}</button>${akDug('br:'+o.id,(o.katilimci_eposta||[]).length)}</div>`
    :b.durum==='calisiyor'?`<div class=empty>${L('{asistan} brifingi hazırlıyor… (1–2 dk)')}</div>`
    :`${b.durum==='hata'?`<div class=empty>${esc(b.hata||'')}</div>`:`<div class=empty>${L('{asistan} geçmiş görüşmelere, açık sorulara ve belgelere bakıp kısa bir brifing hazırlar.')}</div>`}<div class=bt><button class=pri data-brf="${esc(o.id)}">${L(b.durum==='hata'?'Yeniden dene':'Brifing hazırla')}</button></div>`)}
let brMem=[];function brKapali(){try{return JSON.parse(localStorage.getItem('brk')||'[]')}catch(e){return brMem}}
document.getElementById('brk').onclick=()=>{hzAc=null;if(last){renderTakvim(last);renderBrifing(last)}}
// dışarı aktar (v0.33.2; v0.33.3 özet ve alıcılar): PDF (yazdır penceresi → "PDF olarak kaydet"), e-posta taslağı (ayar eposta: outlook | gmail | mailto;
// 14 Ekim: mailto Chrome'a düşüp hiçbir şey açmadı — web postada yeni sekmede taslak), katılımcılara e-posta (takvimdeki adresler), kopyala, .md.
// Gönderen hep kullanıcı. Metin yalnız kullanıcının seçtiği posta hizmetine (taslak adresinde) gider; aktarıcı dışarı bir şey göndermez.
let akAcik=null,akOn={}
function brAc(u,yeni){if(yeni)window.open(u,'_blank');else location.href=u}  // test bunu sarmalar
// v0.105.0 (kullanıcı, 22 Ekim: "⋯ gözümü tırmalıyor; alt menüyü düzenle, e-posta ayarına gerek var mı"): menü düğmenin altında yüzen, bölümlü
// dikey liste (Mac açılır menüsü gibi; satırları itmez); dışarı tıklayınca ya da Esc ile kapanır, seçince kapanır (Kopyala onayı görünsün diye açık kalır).
// Tek e-posta seçeneği (mail-o): katılımcı adresi varsa onlara, yoksa kendine, o da yoksa boş taslak. E-posta ayarı menüde yok: ⚙ Ayarlar → E-posta (Mac penceresinde Suflor.me → Ayarlar…). ek: menünün başına (son toplantıda Zihin haritası).
function akMenu(kay,n,ek,son){const b=(k,t,i)=>`<button class=aki data-ak=${k} data-kay="${esc(kay)}" role=menuitem>${ic(i,t)}</button>`
  return `<div class=akp role=menu>${ek||''}${b('pdf','PDF','belge')}${b('kopyala',L('Kopyala'),'kopya')}${b('md',L('Dosya (.md)'),'indir')}${b('mail-o',L('E-posta taslağı'),'posta')}${son||''}</div>`}
function akDug(kay,n){return `<span class=akw><button class=gh data-aktar="${esc(kay)}" aria-haspopup=menu aria-expanded="${akAcik===kay}" title="${L('PDF, e-posta, pano ya da dosya olarak dışarı al')}">${L('Dışarı aktar')} ${akAcik===kay?'▴':'▾'}</button>${akAcik===kay?akMenu(kay,n):''}</span>`}
function yerelGun(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}  // toISOString UTC: gece yarısından sonra önceki gün
function akDosya(t,d){return `${t} - ${yerelGun(d||new Date())}`.replace(/[\/\\:*?"<>|]+/g,' ').slice(0,120)}
// Hazırlıkta davet gündemi omurga (hr.gundem_yapi; yoksa hr.gundem metinleri), altında "Ek öneri" (gerekçeyle); boş alan gösterilmez
function hzGundem(hr){const y=Array.isArray(hr.gundem_yapi)&&hr.gundem_yapi.length?hr.gundem_yapi:null,g=Array.isArray(hr.gundem)?hr.gundem:[],eo=Array.isArray(hr.ek_oneri)?hr.ek_oneri:[]
  const mad=y?y.map(m=>{const ek=[m.saat,m.dk?m.dk+' '+L('dk'):''].filter(Boolean).join(', ')
    const al=(t,v)=>v?`<div class=gm-a><i>${L(t)}</i> ${esc(v)}</div>`:''
    return `<li class=gm><b>${m.no?esc(m.no)+' · ':''}${esc(m.baslik||'')}</b>${ek?` <span class=gm-s>(${esc(ek)})</span>`:''}${al('Hazırlık',m.hazirlik)}${al('Soru',m.soru)}${al('Seçenek',m.secenek)}${al('Risk',m.risk)}</li>`}).join('')
    :g.map(x=>`<li class=gm>${esc(x)}</li>`).join('')
  const ekh=eo.length?`<div class=bb>${L('Ek öneri')}</div><ul class=gm-ek>${eo.map(x=>{const t=typeof x==='string'?x:(x.metin||''),n=typeof x==='string'?'':(x.neden||'');return`<li>${esc(t)}${n?`<span class=gm-s> — ${esc(n)}</span>`:''}</li>`}).join('')}</ul>`:''
  return(mad?`<div class=bb>${L('Gündem')}</div><ul class=gml>${mad}</ul>`:'')+ekh}
function brIcerik(id){const o=tkOlaylar.find(x=>x.id===id),b=last&&(last.brifing||{})[id];if(!o||!b||b.durum!=='hazir')return null
  const r=b.sonuc||{},tarih=new Date().toLocaleDateString(L('tr-TR'),{day:'numeric',month:'long',year:'numeric'}),saat=`${o.saat||''}${o.bitis_saat?'–'+o.bitis_saat:''}`
  const bol=[['Güncel veri',r.veri],['Dikkat',r.dikkat],['Açık kalanlar',r.acik],[r.dis_etiket||'Dış taraf',r.dis_taraf],['Geçmişte',r.gecmis]].filter(x=>x[1]&&x[1].length),baslik=`${L('Brifing')} — ${o.baslik}`
  return {baslik,dosya:akDosya(`${L('Brifing')} - ${o.baslik}`),alicilar:o.katilimci_eposta||[],
    md:`# ${baslik}\n${tarih}${saat?', '+saat:''}\n\n${r.ozet||''}\n`+bol.map(([t,a])=>`\n## ${L(t)}\n`+a.map(x=>'- '+x).join('\n')+'\n').join('')}}
async function snIcerik(id){if(akOn[id])return akOn[id];let r={};try{r=await j('/son-ac',{method:'POST',body:JSON.stringify({id,tur:'metin'})})}catch(e){}
  if(!r.ok){geciciDurum(L('Özet okunamadı'),r.err||'');return null}
  const d=r.at?new Date(r.at):new Date();return akOn[id]={baslik:r.baslik,dosya:akDosya(`${L('Özet')} - ${r.baslik}`,d),alicilar:r.alicilar||[],md:r.metin}}
function mdDuz(m){return m.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,'$1 ($2)').replace(/^#{1,6}\s+/gm,'').replace(/\*\*(.+?)\*\*/g,'$1').replace(/`([^`]+)`/g,'$1').replace(/^\|?\s*-{3,}[-|\s:]*$/gm,'').replace(/\n{3,}/g,'\n\n').trim()+'\n'}
function mdHtml(m){const sat=m.split('\n'),o=[];let liste=false,tablo=false
  const ic=t=>esc(t).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[([^\]]+)\]\((https?:\/\/[^)\s"<]+)\)/g,(_,x,u)=>`<a href="${u}" target=_blank rel="noopener noreferrer">${x}</a>`)  // metin önce kaçırılır; yalnız http(s) bağlantısı
  const kapat=()=>{if(liste){o.push('</ul>');liste=false}if(tablo){o.push('</table>');tablo=false}}
  for(const l of sat){let x
    if(/^\s*\|/.test(l)){if(/^\s*\|?\s*-{3,}/.test(l.replace(/[|:\s]/g,'').length?l:'---'))continue;if(!tablo){kapat();o.push('<table>');tablo=true}
      o.push('<tr>'+l.trim().replace(/^\||\|$/g,'').split('|').map(c=>`<td>${ic(c.trim())}</td>`).join('')+'</tr>');continue}
    if(/^\s*-{3,}\s*$/.test(l)){kapat();o.push('<hr>');continue}
    if(x=l.match(/^(#{1,3})\s+(.*)/)){kapat();o.push(`<h${x[1].length}>${ic(x[2])}</h${x[1].length}>`);continue}
    if(x=l.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/)){if(tablo){o.push('</table>');tablo=false}if(!liste){o.push('<ul>');liste=true}o.push(`<li>${ic(x[1])}</li>`);continue}
    kapat();if(l.trim())o.push(`<p>${ic(l)}</p>`)}
  kapat();return o.join('')}
// gövde sınırı kodlanmış uzunlukla: Outlook'ta oturum kapalıysa taslak adresi giriş yönlendirmesine bir kez daha kodlanıp gömülüyor; 14 Ekim'de ~6000
// karakterlik gövde "AADSTS90015: Requested query string is too long" verdi → outlook 1500. Kısaltılınca tam metin panoya kopyalanır.
function postaUrl(c,alici){const tur=(last&&last.eposta)||'mailto',to=alici==='b'?(last&&last.eposta_ben)||'':alici?c.alicilar.join(','):'',duz=mdDuz(c.md),sinir={outlook:1500,gmail:6000}[tur]||1800
  let body=duz,kisa=false;while(encodeURIComponent(body).length>sinir&&body.length>120){body=body.slice(0,Math.floor(body.length*0.85));kisa=true}
  if(kisa)body=body.replace(/\s*\S*$/,'').trimEnd()+' …\n\n'+L('(Kısaltıldı — tam metin panoda: Command + V ile yapıştır)')
  const e=encodeURIComponent,u=tur==='outlook'?`https://outlook.office.com/mail/deeplink/compose?to=${e(to)}&subject=${e(c.baslik)}&body=${e(body)}`
    :tur==='gmail'?`https://mail.google.com/mail/${last&&last.eposta_hesap?'u/'+e(last.eposta_hesap)+'/':''}?view=cm&fs=1&to=${e(to)}&su=${e(c.baslik)}&body=${e(body)}`:`mailto:${e(to).replace(/%2C/g,',').replace(/%40/g,'@')}?subject=${e(c.baslik)}&body=${e(body)}`
  return {u,yeni:tur!=='mailto',kisa,duz}}
async function akYap(k,btn){const kay=btn.dataset.kay,[tur,id]=[kay.slice(0,kay.indexOf(':')),kay.slice(kay.indexOf(':')+1)]
  // PDF penceresi tıklamayla hemen açılır (beklemeden sonra açılırsa tarayıcı engeller), içerik sonra yazılır
  const w=k==='pdf'?window.open('','_blank'):null;if(k==='pdf'&&!w){geciciDurum(L('Yeni pencere açılamadı'),L('Tarayıcı açılır pencereyi engelledi'));return}
  const c=tur==='br'?brIcerik(id):tur==='tz'?tzIcerik(id):tur==='ar'?await arIcerik(id):await snIcerik(id);if(!c){if(w)w.close();if(tur==='br')geciciDurum(L('Brifing hazır değil'),'');if(tur==='tz')geciciDurum(L('Rapor hazır değil'),'');if(tur==='ar')geciciDurum(L('Araştırma kaydı okunamadı'),'');return}
  if(c.tam&&(k==='pdf'||k==='md'))c.md=c.tam  // araştırma: e-posta ve Kopyala kısa (başlık, özet, kaynaklar), PDF ve .md tam rapor
  if(k==='pdf'){w.document.write(`<!doctype html><html lang="${document.documentElement.lang||'tr'}"><head><meta charset=utf-8><title>${esc(c.dosya)}</title><style>body{font:14px/1.55 -apple-system,"Helvetica Neue",sans-serif;color:#18201c;max-width:720px;margin:40px auto;padding:0 24px}h1{font-size:22px;font-weight:500;margin:0 0 6px}h2{font-size:16px;font-weight:600;margin:22px 0 6px}h3{font-size:14px;font-weight:600;margin:16px 0 4px}p{margin:6px 0}ul{margin:4px 0;padding-left:20px}li{margin:3px 0}table{border-collapse:collapse;margin:8px 0;font-size:13px}td{border:1px solid #ccd;padding:4px 8px;vertical-align:top}code{font:12px ui-monospace,Menlo,monospace}.son{margin-top:28px;color:#646c66;font-size:11px}@page{margin:18mm}</style></head><body>${mdHtml(c.md)}<div class=son>Suflor.me</div></body></html>`)
    w.document.close();w.focus();setTimeout(()=>w.print(),300);return}
  if(k==='mail-o')k=c.alicilar.length?'mail-k':c.alicisiz?'mail':last&&last.eposta_ben?'mail-b':'mail'  // alicisiz (araştırma): alıcıyı kullanıcı yazar  // tek seçenek (kullanıcı, 22 Ekim): katılımcılar varsa onlara, yoksa kendine, o da yoksa boş taslak
  if(k==='mail-k'&&!c.alicilar.length){geciciDurum(L('Takvimde bu toplantının katılımcı adresi yok'),L('Alıcısız taslak için E-posta'));return}
  if(k.startsWith('mail')){const p=postaUrl(c,{'mail-k':'k','mail-b':'b'}[k]||'');if(p.kisa)try{await navigator.clipboard.writeText(p.duz)}catch(e){}brAc(p.u,p.yeni);return}
  if(k==='kopyala'){try{await navigator.clipboard.writeText(mdDuz(c.md));btn.textContent='✓ '+L('kopyalandı')}catch(e){btn.textContent=L('kopyalanamadı')}setTimeout(()=>{btn.textContent=L('Kopyala')},1500);return}
  if(k==='md'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([c.md.endsWith('\n')?c.md:c.md+'\n'],{type:'text/markdown;charset=utf-8'}));a.download=c.dosya+'.md';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),5000)}}
