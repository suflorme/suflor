// ---- Kararlar ve işler (adım 4, onaylı taslak Isler): başlık + ekip paylaşımı satırı + Yeni iş + ⋯; öneriler tek şeritte (İncele → tek tek gözden geçirme);
// sekmeler Açık · Geciken · Kararlar · Biten; tek satır süzgeç (Benim / Ekibin, arama, toplantı); satıra tıklayınca sağda ayrıntı (bnPanel ref r:<kayıt>), eylemler Planla · İlet · Diğer.
// knSekme eski değerleri ('is', 'soru') Açık sekmesine düşer (git('kayit','is'), testler). "Ekibin" = başkalarına ait işler (x.kendi değil); karar ve açık soru sahipsizdir, süzgeçten etkilenmez.
const knSek=()=>knSekme==='karar'||knSekme==='geciken'||knSekme==='biten'?knSekme:'acik'
function knSekmede(x,k){const kap=x.durum==='kapandi';if(k==='karar')return x.tur==='karar';if(x.tur==='karar')return false
  if(k==='geciken')return!kap&&!!x.gecikti;if(k==='biten')return kap;return!kap}
function knKayit(kid){if(!kid)return null;const b=bnV||{},ls=[...((knV||{}).kayitlar||[]),...(b.kendi||[]),...(b.baskalari||[]),...(b.teyit||[])];return ls.find(y=>y.kayit_id===kid||y.id===kid)||null}
const knKid=x=>x.kayit_id||x.id||''
const knTarihEt=x=>x.tur==='is'&&x.durum!=='kapandi'?(x.vade?goreliSpan(x.vade,'ktar'+(x.gecikti?' gec':''),true):`<span class="ktar sol">${L('Tarihsiz')}</span>`):x.vade?goreliSpan(x.vade,'ktar sol'):x.tarih?goreliSpan(String(x.tarih).slice(0,10),'ktar sol'):'<span class=ktar></span>'
const knBas=x=>x.kim?`<button type=button class=kbas data-bn=knkisi data-k="${esc(x.kim)}" title="${esc(x.kim)}" aria-label="${esc(L('{ad}: yalnız onun kayıtları',{ad:x.kim}))}">${esc(bnBas(x.kim))}</button>`:`<span class="kbas bos" aria-hidden=true></span>`
// TEK İŞ SATIRI (Bugün'ün Senden beklenenler listesi, Bugün'ün "Senin açık işlerin" paneli ve Kararlar ve işler aynı bileşeni kullanır): sabit genişlikte sol yuva · başlık + soluk meta (toplantı · tarih) · sağda kişi rozeti ve tarih sütunu.
// Yuva: iş/söz → boş yuvarlak "Yapıldı olarak işaretle" (/is-durum) · açık soru → "?" yuvarlağı "Cevaplandı olarak işaretle" (/kayit-eylem cevaplandi) · kapanmış → dolu tik (yalnız gösterim) · karar/dış kayıt → tıklanmaz yuva.
// Yazılı "Yapıldı" düğmesi yok. Tıklayınca satır üstü çizili ve soluk görünür, 5 sn "Geri al" (bnYap); sonra yazılır. Üstüne gelince Ertele ve ⋯ (yalnız panelde yok); satır ya da metin tıklanınca ayrıntı paneli.
const bnBitiyor=new Set()  // yazılması bekleyen yapıldı/cevaplandı işaretleri (id): satır listede kalır, çizili ve soluk
function knYuva(x,kap,kid){if(x.dis)return`<span class=yuva aria-hidden=true></span>`
  if(kap)return`<span class="yuva oldu" aria-label="${L(x.tur==='soru'?'Cevaplandı':'Bitti')}">${ic('check')}</span>`
  if(x.tur==='soru')return`<button type=button class="onay yq" data-bn=sorubit data-id="${esc(kid)}" aria-label="${L('Cevaplandı olarak işaretle')}" title="${L('Cevaplandı olarak işaretle')}">?</button>`
  return`<button type=button class=onay data-bn=isbit data-id="${esc(x.id)}" aria-label="${L('Yapıldı olarak işaretle')}" title="${L('Yapıldı olarak işaretle')}">${ic('check')}</button>`}
function knSatir(x,o){o=o||{};const kap=x.durum==='kapandi',kid=knKid(x),sec=!o.pn&&bnRef==='r:'+kid,bit=bnBitiyor.has(kid)||bnBitiyor.has(x.id),top=x.toplanti?tpAd(x):esc(x.baslik||'')
  const alt=[x.atayan?esc(L('Sana atandı · {ad}',{ad:x.atayan})):'',top,x.tur==='is'&&!kap?bsTarih(x.tarih):'',x.gundem&&x.gundem.baslik?esc(L('Gündemde: {t}',{t:x.gundem.baslik})):'',x.dis?`<span class="etiket notr">${esc(x.kaynak)}</span>`:''].filter(Boolean).join(' · ')
  const hz=x.dis||o.pn?'':kap?`<button type=button class="b sade" data-bn=knyeni data-kid="${esc(kid)}" title="${L('Yeniden aç')}">${L('Geri al')}</button>`:(x.tur==='is'?`<button type=button class="b sade kert" data-bn=knert data-kid="${esc(kid)}">${L('Ertele')}</button>`:'')+emDugme(x)
  const ac=x.dis||o.pn?'':` data-bn=knac data-kid="${esc(kid)}"`
  return`<div class="sat kns${o.bs?' bsi':''}${kap?' kapali':''}${bit?' bitiyor':''}${x.dis?' dis':''}${sec?' secili':''}" data-id="${esc(kap||x.tur==='soru'?kid:x.id||'')}"${ac}>${knYuva(x,kap,kid)}<${ac?'button type=button':'div'} class=m${ac}><span class=t>${esc(x.metin)}</span>${alt?`<span class=a>${alt}</span>`:''}</${ac?'button':'div'}><span class=hizli>${hz}</span>${knBas(x)}${knTarihEt(x)}</div>`}
// yazılması bekleyen işaret: satır çizilir, bildirimde Geri al 5 sn vazgeçirir; sonra yazar, veriyi yeniler
function bnYenile(){if(last)bnCiz(last);if(bnRef)bnPanelCiz(last)}
function bnYap(idler,mesaj,yap){idler=idler.filter(i=>i&&!bnBitiyor.has(i));if(!idler.length)return;idler.forEach(i=>bnBitiyor.add(i));bnYenile()
  const t=setTimeout(async()=>{try{await yap()}catch(e){}await bnVeriYukle(true);if(bnGor==='kayit')await knYukle(true);idler.forEach(i=>bnBitiyor.delete(i));bnYenile()},5000)
  bnBildir(mesaj,()=>{clearTimeout(t);idler.forEach(i=>bnBitiyor.delete(i));bnYenile()})}
const knKararEt=x=>emOnayIs(x.onay)||(x.durum==='teyit'?`<span class="etiket bekliyor">${L('Onay bekliyor')}</span>`:`<span class="etiket olumlu">${L('Onaylandı')}</span>`)
function knKararSatir(x){const kid=knKid(x),sec=bnRef==='r:'+kid,top=x.toplanti?tpAd(x):esc(x.baslik||''),alt=[top,x.durum==='teyit'?esc(x.neden||''):'',x.dis?`<span class="etiket notr">${esc(x.kaynak)}</span>`:''].filter(Boolean).join(' · ')
  const ac=x.dis?'':` data-bn=knac data-kid="${esc(kid)}"`
  const yv=x.dis?`<span class=yuva aria-hidden=true></span>`:x.durum==='teyit'?`<span class="yuva kar" aria-hidden=true></span>`:`<span class="yuva oldu" aria-hidden=true>${ic('check')}</span>`
  return`<div class="sat kns karar${x.dis?' dis':''}${sec?' secili':''}" data-id="${esc(x.id||'')}"${ac}>${yv}<${x.dis?'div':'button type=button'} class=m${ac}><span class=t>${esc(x.metin)}</span>${alt?`<span class=a>${alt}</span>`:''}</${x.dis?'div':'button'}><span class=hizli>${x.dis?'':emDugme(x)}</span>${x.dis?'':knKararEt(x)}${x.durum==='teyit'&&!x.dis?`<button type=button class=b data-bn=kararonay data-id="${esc(x.id)}">${L('Onayla')}</button>`:''}</div>`}
// "Onayını bekleyenler": asistan kaynaklı bütün öneriler tek kutuda, aynı kart biçimiyle — belgelerden önerilen işler (/belge-oneri) · aynı iş olabilir çiftleri (/is-kopya) · senden onay bekleyen eylemler (eylem kuyruğu).
// Kart: tür etiketi, tek satır öneri, tek satır gerekçe (soluk), sağda ana düğme + Hayır. 3'ten fazlaysa ilk 3 + "Tümünü göster". Hiç öneri yoksa kutu yok. Yazma 5 sn sonra (Geri al bu sürede vazgeçer).
let onTum=false
const gpBek=new Set(),zkBek=new Set();let gpGordu='',bnOzetMetin=''  // günün planı (aktarici/dusunme.py): yanıtlanan 'Doğru mu?' soruları; planın görüldüğü gün; Dinle'nin okuyacağı düz metin
const boListe=()=>((boV||{}).oneriler||[]).filter(x=>!boBek.has(x.id))
function onKartlar(){const R=[]
  boListe().forEach(x=>{const k=x.kaynak||{},yer=k.tur==='veritabani'?L('iş takip kaydı'):[k.ad,k.konum].filter(Boolean).join(' · ')  // kayıt veritabanı satır no'su gösterilmez
    R.push({e:L('Belge önerisi'),m:x.metin,g:[x.sahip||L('sahipsiz'),x.vade?goreliTarih(x.vade,true):'',yer?L('Kaynak')+': '+yer:''].filter(Boolean).join(' · '),
      d:`<button type=button class="b ana" data-bn=bokabul data-id="${esc(x.id)}" title="${L('Kayda alınır; sahibi varsa ona atanır')}">${esc(x.sahip?L('Onayla ve ata'):L('Onayla'))}</button><button type=button class=b data-bn=bored data-id="${esc(x.id)}" title="${L('Bir daha önerilmez')}">${L('Reddet')}</button>`})})
  ikListe().forEach(x=>R.push({e:L('Aynı iş olabilir'),m:x.yeni.metin,g:[x.neden,L('Eski')+': '+x.eski.metin+(x.eski.baslik?' ('+x.eski.baslik+')':'')].filter(Boolean).join(' · '),
    d:`<button type=button class="b ana" data-bn=ikbirlestir data-id="${esc(x.cift)}" title="${L('Yeni kayıt kalır, eski kapanır')}">${L('Birleştir')}</button><button type=button class=b data-bn=ikayri data-id="${esc(x.cift)}" title="${L('Bir daha sorulmaz')}">${L('Ayrı')}</button>`}))
  if(last)bnBekleyen(last).forEach(x=>R.push({e:EYT[x.tur]||x.tur,m:(x.baslik||'')+(x.kim?' — '+x.kim:''),g:x.ayrinti&&x.tur!=='izin'?ayGor(x.ayrinti).replace(/\s+/g,' ').slice(0,140):'',
    d:`<button type=button class="b ana" data-bn=onay data-id="${esc(x.id)}">${L('Onayla')}</button><button type=button class=b data-bn=ret data-id="${esc(x.id)}">${L('Reddet')}</button>`}))
  return R}
function onCiz(){const R=onKartlar(),bl=((ikV||{}).birlesen||[]).filter(x=>!ikBek.has(x.cift))
  if(!R.length&&!bl.length)return''
  const gor=onTum?R:R.slice(0,3),kart=x=>`<div class=onk><div class=onm><span class="etiket notr">${esc(x.e)}</span><span class=onmt title="${esc(x.m)}">${esc(x.m)}</span></div>${x.g?`<div class=ong title="${esc(x.g)}">${esc(x.g)}</div>`:''}<div class=ond>${x.d}</div></div>`
  const geri=bl.map(x=>`<div class=onbirl><span>${esc(L('Aynı iş birleştirildi: {m}',{m:x.yeni_metin}))}</span><button type=button class=bag data-bn=ikgeri data-id="${esc(x.cift)}">${L('Geri al')}</button></div>`).join('')
  return`<section class=onkutu aria-label="${L('Onayını bekleyenler')}">${R.length?`<div class=onbas><h2 class=kb2>${esc(L('Onayını bekleyenler · {n}',{n:R.length}))}</h2>${R.length>3?`<button type=button class=bag data-bn=ontum aria-expanded="${onTum}">${L(onTum?'Daha az göster':'Tümünü göster')}</button>`:''}</div><div class=onliste>${gor.map(kart).join('')}</div>`:''}${geri}</section>`}
function boIsle(id,islem){boBek.add(id);if(last)bnCiz(last)
  const t=setTimeout(async()=>{try{await bnYaz('/belge-oneri',{id,islem})}catch(e){}boBek.delete(id);boV=null;await knYukle(true)},5000)
  bnBildir(islem==='kabul'?L('Öneri kayda alındı'):L('Öneri bir daha gösterilmeyecek'),()=>{clearTimeout(t);boBek.delete(id);if(last)bnCiz(last)})}
// Aynı iş olabilir (aktarici/is-kopya.py, 10 Kasım): aynı sahibin farklı toplantılarda yeniden konuştuğu iş. Asistan emin değilse çift burada sorulur: Birleştir (yeni kalır, eski kapanır) · Ayrı (bir daha sorulmaz).
// Otomatik birleştirilenler son 24 saat tek satırla görünür, Geri al iki işlemi de geri çevirir. Yazma 5 sn sonra (bildirimdeki Geri al bu sürede vazgeçer).
const ikListe=()=>((ikV||{}).sorular||[]).filter(x=>!ikBek.has(x.cift))
function ikIsle(id,islem){ikBek.add(id);if(last)bnCiz(last)
  const t=setTimeout(async()=>{try{await bnYaz('/is-kopya',{cift:id,islem})}catch(e){}ikBek.delete(id);ikV=null;await knYukle(true)},5000)
  bnBildir(islem==='birlestir'?L('İşler birleştirildi'):islem==='ayri'?L('İki iş ayrı kalacak'):L('Birleştirme geri alınacak'),()=>{clearTimeout(t);ikBek.delete(id);if(last)bnCiz(last)})}
// Ortak defter durumu (A7, S242): yalnız ekip paylaşımı açıkken tek satır — sorun varsa ne yapılacağı, iyiyse son eşitleme ve Firestore gecikmesi (ortanca, 10 kayıttan 9'u)
function ortSatir(){const o=knOrt;if(!o||!o.acik||['kapali','deneme'].includes(o.durum))return''
  const f=o.firestore||{},sn=x=>x<10?(Math.round(x*10)/10).toLocaleString(DIL==='en'?'en-US':'tr-TR'):String(Math.round(x))
  const m={giris_yok:L('Ekip paylaşımı duruyor: Google girişi gerekiyor. Terminal’de: python3 -B ortak_bulut.py giris'),alan_disi:L('Ekip paylaşımı kapalı: şirket e-postası gerekiyor, kişisel posta adresiyle paylaşılmaz.'),ag_yok:L('Ekip paylaşımı bekliyor: ağa ulaşılamıyor; bağlantı gelince kendiliğinden sürer.'),kimlik_uyumsuz:L('Ekip paylaşımı duruyor: Google’da giriş yapılan hesap Suflor’daki e-postanla aynı değil.'),kimlik_yok:L('Ekip paylaşımı kapalı: Suflor’da şirket e-postan tanımlı değil.'),ayar_eksik:L('Ekip paylaşımı yarım kurulmuş: kurulumu tamamla.'),bekliyor:L('Ekip paylaşımı başlıyor…')}[o.durum]
  if(m)return`<div class="ortak uyari">${esc(m)}</div>`
  if(o.durum!=='ok')return`<div class="ortak uyari">${L('Ekip paylaşımında hata: {h}',{h:esc(o.hata||o.durum)})}</div>`
  const saat=o.son?String(o.son).slice(11,16):'',g=o.tasima==='firestore'&&f.gecikme_ortanca!=null?(f.gecikme_p90!=null?L('gecikme ortanca {o} sn, 10 kayıttan 9’u {p} sn içinde',{o:sn(f.gecikme_ortanca),p:sn(f.gecikme_p90)}):L('gecikme ortanca {o} sn',{o:sn(f.gecikme_ortanca)})):''
  const gel=!!((last||{}).ayarlar||{}).gelistirici  // 19 Kasım (Y4): gecikme ölçüsü kullanıcı yüzünde yazmaz; yalnız geliştirici kurulumunda, satırın üstüne gelince
  return`<div class=ortak${gel&&g?` title="${esc(g)}"`:''}>${[L('Ekiple paylaşılıyor'),saat?L('son eşitleme {s}',{s:saat}):''].filter(Boolean).join(' · ')}</div>`}
// Açık sekmesi iki başlık: "İşler · N", sonra "Açık sorular · N" (boş başlık görünmez); öbür sekmeler tek liste. Süzgeç ve arama iki başlığa birlikte uygulanmış listeden gelir.
function knListe(liste,sk){if(!liste.length)return''
  const kl=l=>`<div class="ince knl${sk==='biten'?' biten':''}">${l.map(x=>x.tur==='karar'?knKararSatir(x):knSatir(x)).join('')}</div>`
  if(sk!=='acik')return kl(liste)
  const bl=(a,l)=>l.length?`<h2 class="kb2 knbl">${esc(a)} · ${l.length}</h2>${kl(l)}`:''
  return bl(L('İşler'),liste.filter(x=>x.tur!=='soru'))+bl(L('Açık sorular'),liste.filter(x=>x.tur==='soru'))}
function knCiz(){const v=knV,ks=v?v.kayitlar.filter(x=>!bnGizli.has(x.id)):[],sk=knSek()
  const dis=v?(v.dis||[]).flatMap(d=>d.ok?d.kayitlar.map(x=>({tur:x.tur,metin:x.metin,kim:x.sahip||'',baslik:x.toplanti||'',toplanti:'',vade:x.vade||'',durum:'acik',gecikti:false,tarihsiz:!x.vade,dis:true,kaynak:d.ad,id:''})):[]):[]
  const hepsi=[...ks,...dis],uyan=hepsi.filter(knSuzgec),say=k=>uyan.filter(x=>knSekmede(x,k)).length,liste=uyan.filter(x=>knSekmede(x,sk)).sort(knSira)
  const sek=[['acik',DIL==='en'?L('Açık (iş sekmesi)'):'Açık'],['geciken',L('Geciken')],['karar',L('Kararlar')],['biten',L('Biten')]].map(([k,a])=>`<button type=button role=tab class="sekme${sk===k?' etkin':''}" aria-selected="${sk===k}" data-bn=knsek data-s="${k}">${a}<span class=say>${say(k)}</span></button>`).join('')
  const opt=(l,sec)=>l.map(([d,a])=>`<option value="${esc(d)}"${sec===d?' selected':''}>${esc(a)}</option>`).join('')
  const top=opt([['',L('Tüm toplantılar')],...(v?v.toplantilar.map(t=>[t.dosya,toplantiAdi(t.dosya,t.baslik)+(t.tarih?' · '+goreliTarih(t.tarih):'')]):[])],knSuz.toplanti)
  const seg=sk==='karar'?'':`<div class="seg kimin" role=group aria-label="${L('Kimin')}">${[['ben',L('Benim')],['ekip',L('Ekibin')]].map(([k,a])=>`<button type=button data-bn=knsahip data-v="${k}" class="${knSuz.sahip===k?'on':''}" aria-pressed=${knSuz.sahip===k}>${a}</button>`).join('')}</div>`
  const cip=(t,a)=>`<button type=button class=cip ${a} title="${L('Süzgeci kaldır')}">${esc(t)} ${ic('x')}</button>`
  const suzlu=knSuz.kisi||knSuz.toplanti||knSuz.durum||knSuz.ara||(knSuz.sahip&&knSuz.sahip!=='ben')
  const BOS={acik:L('Açık iş yok. Toplantıda verilen işler buraya düşer.'),geciken:L('Geciken iş yok.'),karar:L('Henüz karar yok.'),biten:L('Biten iş yok.')}
  const bos=!v?L('Yükleniyor…'):!hepsi.length?L('Henüz kayıt yok: toplantı bittiğinde kararlar ve işler buraya düşer.'):!liste.length?(suzlu&&hepsi.some(x=>knSekmede(x,sk))?L('Süzgece uyan kayıt yok.'):BOS[sk]):''
  const alt=ortSatir()||(v?`<span class=alt>${esc(L('{k} karar · {i} iş · {s} açık soru',{k:hepsi.filter(x=>x.tur==='karar').length,i:hepsi.filter(x=>x.tur==='is').length,s:hepsi.filter(x=>x.tur==='soru').length}))}</span>`:'')
  return`<div class="sayfab kns"><div class=sbas><h1>${L('Kararlar ve işler')}</h1>${alt}</div><div class=sag><button type=button class="b ana iri" data-bn=kmk data-k=yeniis>${L('Yeni iş')}</button>${sayfaMenu('kayit')}</div></div>
    ${onCiz()}
    <section class="bolum knb"><div class=sekmeler role=tablist aria-label="${L('Kararlar ve işler')}">${sek}</div>
    <div class=suzgec>${seg}<input id=knAra type=search value="${esc(knSuz.ara)}" placeholder="${L('Ara')}" aria-label="${L('Ara')}"><select data-knf=toplanti aria-label="${L('Toplantı')}">${top}</select>${knSuz.kisi?cip(L('Kişi: {ad}',{ad:knSuz.kisi}),`data-bn=knkisi data-k="${esc(knSuz.kisi)}"`):''}${knSuz.durum==='tarihsiz'?cip(L('Yalnız tarihsiz işler'),'data-bn=kntarihsiz'):''}${v&&(v.deneme_say||knDen)?`<label class=kndn><input type=checkbox data-kndn${knDen?' checked':''}> ${L('Deneme toplantıları')}${v.deneme_say?` (${v.deneme_say})`:''}</label>`:''}</div>
    ${knListe(liste,sk)}${bos?`<p class="sakin knbos">${esc(bos)}</p>`:''}${v?(v.dis||[]).filter(d=>!d.ok).map(d=>`<p class=sakin>${esc(d.ad)}: ${L('defter okunamadı')} — ${esc(d.hata||'')}</p>`).join(''):''}
    <p class="sakin kucuk">${L('Dış kayıttan gelenler etiketli ve yalnız okunur; gizli toplantıların kayıtları burada yok.')}</p></section>`}
// Ayrıntı paneli (bnPanel ref r:<kayıt>): Kararlar ve işler, Bugün ve Ekip satırından aynı panel. Geniş ekranda Kararlar ve işler sayfasında sağa yerleşik (perde yok), 900 px ve altında tam ekran çekmece.
// Üstte tür · toplantı, tarih; başlık; Sahip, Son tarih, Kaynak (toplantı dökümü, özet), Görebilen; ana düğmeler (Yapıldı / Onayla …, Ertele, Ata); eylemler üç başlıkta (emIcerik).
function knAyrinti(kid){const x=knKayit(kid)||(emKid===kid&&emV&&emV.kayit)||null,kap=`<button type=button class=ikon data-bn=kapat aria-label="${L('Kapat')}">${ic('x')}</button>`
  if(!x)return`<div class=kpb><span class=kust>${L('Kayıt')}</span>${kap}</div><p class=alt2>${L('Kayıt bulunamadı.')}</p>`
  const tur=x.tur==='karar'?L('Karar'):x.tur==='soru'?L('Açık soru'):L('İş'),tad=x.toplanti?toplantiAdi(x.toplanti,x.baslik):(x.baslik||''),tp=knTop(x.toplanti)
  const ust=[tur,[tad,x.tarih?goreliTarih(String(x.tarih).slice(0,10)):''].filter(Boolean).join(', ')].filter(Boolean).join(' · ')
  const sat=(a,b)=>b?`<dt>${esc(a)}</dt><dd>${b}</dd>`:''
  const kay=[x.toplanti?`<button type=button class=bag data-bn=kngit data-top="${esc(x.toplanti)}" title="${esc(tpDos(x.toplanti))}">${L('Toplantı dökümü')}</button>`:'',tp&&tp.id?`<button type=button class=bag data-bn=kngit data-sid="${esc(tp.id)}" data-harita="${tp.harita?'1':''}">${L(tp.harita?'Toplantı panosu':'Özet')}</button>`:''].filter(Boolean).join(' · ')
  const o=knOrt,gor=o&&o.acik&&o.durum==='ok'?L('Ekip paylaşımında'):L('Yalnız sen (bu Mac)')
  const dur=x.tur==='karar'?knKararEt(x):x.durum==='kapandi'?`<span class="etiket olumlu">${L(x.tur==='soru'?'Cevaplandı':'Bitti')}</span>`:''
  return`<div class=kpb><span class=kust>${esc(ust)}</span>${kap}</div><h2 class=kh>${esc(x.metin||'')}</h2>
    <dl class=kiz>${sat(x.tur==='karar'?L('Söyleyen'):L('Sahip'),esc(x.kim||L('sahipsiz')))}${x.tur==='is'?sat(L('Son tarih'),x.vade?goreliSpan(x.vade,x.gecikti&&x.durum!=='kapandi'?'gec':'',true):esc(L('Tarihsiz'))):''}${sat(L('Durum'),dur)}${sat(L('Kaynak'),kay||(x.dis?esc(x.kaynak||''):''))}${sat(L('Görebilen'),esc(gor))}${x.atayan?sat(L('Atayan'),esc(x.atayan)):''}${x.gundem&&x.gundem.baslik?sat(L('Gündemde'),esc(x.gundem.baslik)):''}</dl>
    ${x.dis?`<p class=alt2>${L('Yalnız okunur; değişiklik o defterde yapılır.')}</p>`:`<div class="kneg emk">${emHedef==='yan'&&emKid===kid?emIcerik():`<p class=emsoluk>${L('Yükleniyor…')}</p>`}</div>`}`}
function knAc(kid,mod){if(!kid)return;bnRef='r:'+kid;emAc(kid,'yan',mod);bnPanelAc(bnRef);if(last)bnCiz(last)}
// ---- Bugün satırları (adım 3): renkli nokta, metin, alt satır (toplantı adı · göreli tarih; büyük harf etiket yok), sağda tek durum etiketi, tek küçük düğme, ⋯ eylem menüsü.
// Onay yuvarlağı yok: işaretleme düğmeyle (Yapıldı / Onayla). Eylem kuyruğu satırı İncele ile yan panelde (Onayla / Reddet).
// Toplantının kullanıcıya görünen adı: dosya adı (2026-11-03-1000-…) gösterilmez. Sıra: son toplantılar kaydının başlığı (özet) → Kararlar ve işler'in toplantı listesi → kaydın kendi başlığı;
// hiçbiri yoksa dosya adından tarih öneki atılır (son çare). Dosya adı yalnız title'da.
const tpDos=d=>String(d||'').replace(/\.md$/,'').split('/').pop()
function toplantiAdi(dosya,yedek){const d=tpDos(dosya),bul=ls=>(ls||[]).find(x=>d&&tpDos(x.dosya)===d)
  const r=bul((last||{}).son_toplantilar)||bul((knV||{}).toplantilar),b=r&&r.baslik||yedek||''
  if(b&&!/^\d{4}-\d\d-\d\d-\d{4}-/.test(b))return b;const t=(b||d).replace(/^\d{4}-\d\d-\d\d-\d{4}-/,'').replace(/-/g,' ').trim();return t||b||d}
const tpAd=x=>x.toplanti?`<span title="${esc(tpDos(x.toplanti))}">${esc(toplantiAdi(x.toplanti,x.baslik))}</span>`:esc(x.baslik||'')
// Senden beklenenler — tek tanım (başlıktaki N, "Tümü · N", kenar rozeti): senden onay bekleyen eylemler + onayını bekleyen kararlar + açık işlerin (14 günden eskiler hariç: Geride kalanlar).
// Sıra: gecikmiş, yeni atanmış, vadesi yakın, tarihsiz en sonda
// v0.248.0 (16 Kasım, S271 d): bugünün gün planında odak varsa sayılan işler yalnız odaktaki hâlâ açık işler (plan sırasıyla); öbür açık işler
// sayılmaz ama "Tümü · nTum" ile erişilir. Odak bitince n = onay + karar. Plan yoksa (null, başka gün, odak yok) eski davranış
function bnBeklenen(s){const knTum=bnKendiT().slice().sort((a,b)=>(!!b.gecikti-!!a.gecikti)||(!!b.atama_yeni-!!a.atama_yeni)||((a.kalan_gun==null)-(b.kalan_gun==null))||((a.kalan_gun||0)-(b.kalan_gun||0)))
  const bek=s?bnBekleyen(s):[],kt=bnTeyitT(),gp=s&&s.gun_plani,od=gp&&gp.tarih===bnTarih()&&Array.isArray(gp.odak)?gp.odak.filter(x=>x&&x.id&&(!x.kapsam||x.kapsam==='kendi')):[]
  const plan=od.length>0,acik=new Map(bnKendi().map(x=>[x.id,x])),kn=plan?od.map(x=>acik.get(x.id)).filter(Boolean):knTum
  return{bek,kt,kn,knTum,plan,n:bek.length+kt.length+kn.length,nTum:bek.length+kt.length+knTum.length}}
const bsSat=x=>`<div class="sat bs" data-id="${esc(x.id||'')}"${x.ek||''}>${x.ikon?`<span class=sik aria-hidden=true>${ic(x.ikon)}</span>`:`<span class="nokta ${x.nokta||''}" aria-hidden=true></span>`}<div class=m><div class=t>${x.t}</div>${x.a?`<div class=a>${x.a}</div>`:''}</div><div class=eylem>${x.e||''}${x.d||''}${x.x||''}</div></div>`
const bsTarih=t=>t?goreliSpan(String(t).slice(0,10),''):''
const bsIs=x=>knSatir(x,{bs:1})
function bsKarar(x){return bsSat({id:x.id,ek:knKid(x)?` data-bn=knac data-kid="${esc(knKid(x))}"`:'',nokta:'bek',t:esc(x.metin),a:[tpAd(x),bsTarih(x.tarih),esc(x.neden||'')].filter(Boolean).join(' · '),e:emOnayIs(x.onay)||`<span class="etiket bekliyor">${L('Onay bekliyor')}</span>`,d:`<button type=button class=b data-bn=kararonay data-id="${esc(x.id)}">${L('Onayla')}</button>`,x:emDugme(x)})}
function bsEylem(x){const ay=x.ayrinti&&x.tur!=='izin'?esc(ayGor(x.ayrinti).replace(/\s+/g,' ').slice(0,140)):''
  return bsSat({id:x.id,nokta:'bek',t:esc(x.baslik||'')+(x.kim?' — '+esc(x.kim):''),a:[esc(EYT[x.tur]||x.tur),ay].filter(Boolean).join(' · '),e:`<span class="etiket bekliyor">${L('Onay bekliyor')}</span>`,d:`<button type=button class=b data-bn=panel data-ref="e:${esc(x.id)}">${L('İncele')}</button>`})}
// Sıradaki toplantı: saat kutusu (saat + süre), başlık, alt satır (platform · kişi · hazırlık), Hazırlığı aç; altında gündem taslağı / izleme adayları / e-posta işareti ve saat şeridi
function bsSira(o,s,serit){const hd=hzDurum(o,s),ks=o.kisi_sayisi||(o.katilimcilar||[]).length,sure=Math.max(0,bnDk(o.bitis_saat)-bnDk(o.saat)),kim=o.katilimcilar||[]
  const alt=[o.platform?(PL[o.platform]||o.platform):'',ks?(kim.length?kim.slice(0,3).map(bnIlk).join(', ')+(ks>3?' '+L('+{n} kişi',{n:ks-3}):''):L('{n} kişi',{n:ks})):'',L(HZW[hd]||HZW.yok)].filter(Boolean).join(' · '),ekS=gtSatir(o)+izSatir(o)+epSatir(o)
  return`<section class="bolum sira2" aria-label="${L('Sıradaki toplantı')}"><h2 class=kb2>${L(o.suruyor?'Şimdi':'Sıradaki')}</h2><div class=sirak><div class=sirab><div class=saatk><span class=mono>${esc(o.saat)}</span><span>${esc(L('{n} dk',{n:sure}))}</span></div><div class=sm><span class=ad>${esc(o.baslik||L('(başlıksız)'))}</span><span class=alt>${esc(alt)}</span></div><div class=keylem>`
    +(o.suruyor?`<button type=button class="b ana iri" data-bn=bas data-id="${esc(o.id)}">${ic('video')}${L('Toplantıyı başlat')}</button><button type=button class="b iri" data-bn=panel data-ref="t:${esc(o.id)}">${L('Hazırlığı aç')}</button>`
      :`<button type=button class="b sade" data-bn=bas data-id="${esc(o.id)}">${L('Başlat')}</button><button type=button class="b ana iri" data-bn=panel data-ref="t:${esc(o.id)}">${L('Hazırlığı aç')}</button>`)
    +`</div></div>${ekS?`<div class=siraek>${ekS}</div>`:''}</div>${serit}</section>`}
// durum hapı: asistan konuşuyor/dinliyor/düşünüyor, değilse panonun durum satırının kısa hâli (Hazır, uyarı)
function bnHap(s){const k=s.konus||{},d=durum(s);let c=String(d.c||'nt').split(' ')[0],m=String(d.m||'').split(' — ')[0]
  if(bnDin||k.durum==='konusuyor'){c='ok';m=L('Konuşuyor')}else if(k.durum==='yaziya'||k.durum==='dinliyor'){c='ok';m=L('Dinliyor')}else if(k.durum==='dusunuyor'){c='ok';m=L('Düşünüyor')}
  return`<span class="hap ${c==='wa'?'wa':c==='er'?'er':''}" role=status title="${esc(d.a||'')}"><i aria-hidden=true></i>${esc(m)}</span>`}
// ---- Önemli e-postalar (GET /eposta-onemli) ve Yaklaşan tarihler (GET /yaklasan-tarihler): uç yoksa, izin yoksa ya da boşsa blok gizli. Eylemler POST'la; taslak hiçbir şey göndermez.
let epV=null,ytV=null,arV=null,arDetay={},bnEkT=0,bnEkYuk=false,epSec=null,epMenuId=''  // epMenuId: ⋯ menüsü açık olan satır (yeniden çizimde korunur)
const dkKapali=new Set()  // elle kapatılan döküm kontrolleri (arka uç kaydedene kadar gizli)
async function bnEkYukle(zorla){if(bnEkYuk||(!zorla&&Date.now()-bnEkT<60000))return;bnEkYuk=true;bnEkT=Date.now()
  const al=async u=>{try{return await j(u)}catch(e){return null}},[e,k,a]=await Promise.all([al('/eposta-onemli'),al('/yaklasan-tarihler'),al('/arastirma')]),ayni=(x,y)=>JSON.stringify(x)===JSON.stringify(y);let d=false
  const e2=e&&e.ok&&e.izin!==false?e:null,k2=k&&k.ok&&Array.isArray(k.tarihler)?k:null,a2=a&&Array.isArray(a.kayitlar)?a:null
  if(!ayni(e2,epV)){epV=e2;d=true}if(!ayni(k2,ytV)){ytV=k2;d=true}if(!ayni(a2,arV)){arV=a2;d=true}
  bnEkYuk=false;if(d&&last)bnCiz(last)}
const epBek=()=>epV?(Array.isArray(epV.bekleyen)?epV.bekleyen:(epV.onemli||[])).filter(x=>x&&x.id):[]
const epDon=()=>epV?(Array.isArray(epV.donus)?epV.donus:(epV.cevapsiz||[]).filter(x=>x.yon==='giden')).filter(x=>x&&x.id):[]
const epDus=()=>epV&&Array.isArray(epV.dusuk)?epV.dusuk:[]  // düşük öncelikli (katlı satır; Günün özeti sayacına girmez)
const epListe=()=>[...epBek(),...epDon(),...epDus()]
let epDusAcik=false;try{epDusAcik=localStorage.getItem('epdus')==='1'}catch(e){}
const epSay=()=>epV?(typeof epV.ozet_sayi==='number'?epV.ozet_sayi:epBek().length):0  // Günün özeti sayacı: senden cevap bekleyenler
function goreliSaat(t){const d=new Date(t);if(!t||isNaN(d))return'';const dk=Math.round((Date.now()-d)/6e4);if(dk<1)return L('az önce');if(dk<60)return L('{n} dk önce',{n:dk});if(dk<1440&&d.getDate()===new Date().getDate())return L('{n} saat önce',{n:Math.round(dk/60)});return goreliTarih(d)}
// S263: seçili e-postanın düğmeleri satırın hemen altında, satırla aynı yüzeyde (.epsar.sec); her öğede neden satırı; Claude değerlendirmediyse sade "Değerlendirilmedi" öneki
function epEylem(o,dus){const id=esc(o.id)
  return`<div class=epek><button type=button class="b sade epbir" data-bn=eptas data-id="${id}">${L(o.yon==='giden'?'Takip taslağı':'Cevap taslağı')}</button>`
  +`<details class=epdiger data-id="${id}"${epMenuId===o.id?' open':''}><summary class="b sade" aria-label="${L('Diğer')}">⋯</summary><div class=epmenu><button type=button class="b sade" data-bn=epert data-id="${id}">${L('Yarın hatırlat')}</button><button type=button class="b sade" data-bn=epyok data-id="${id}">${L(o.yon==='giden'?'Takibi bırak':'Cevapladım, listeden kaldır')}</button><button type=button class="b sade" data-bn=epkisi data-id="${id}">${L('Bu kişi önemli')}</button><button type=button class="b sade" data-bn=epnone data-id="${id}">${L('Bu gönderen önemsiz')}</button>`
  +(o.tepki?`<span class="sakin epmenu-not">${L('Öncelik işaretlendi')}</span>`:`<button type=button class="b sade" data-bn=epyanlis data-id="${id}" data-b="${dus?'yuksek':'dusuk'}">${L('Öncelik yanlış')}</button>`)+`</div></details></div>`}
function epMailUyari(){const p=last&&last.posta;if(!p||!p.mail_uyari)return'';const t=p.son_gelen||p.guncel,d=t?new Date(t):null,ok=d&&!isNaN(d),z=ok?`${goreliTarih(d)} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`:''
  return`<div class="epmail" role=status><span>${esc(ok?L('Mail uygulaması kapalı — e-postalar {t}’ten beri güncellenmiyor',{t:z}):L('Mail uygulaması kapalı — e-postalar güncellenmiyor'))}</span><button type=button class=b data-bn=mailac>${L('Mail’i aç')}</button></div>`}
function epBlok(){const uy=epMailUyari(),bk=epBek().slice(0,3),dn=epDon().slice(0,3),tum=[...bk,...dn],ds=epDus(),hepsi=[...tum,...ds];if(!hepsi.length)return uy?`<section class=blk id=bnEp aria-label="${L('E-postalar')}"><div class=bbas><h2>${L('E-postalar')}</h2></div>${uy}</section>`:'';const sec=hepsi.some(x=>x.id===epSec)?epSec:null,bg=epV.bilgi_sayi||0
  const bayNed={kayit_kapandi:L('kayıt kapanmış'),toplantida_konusuldu:L('toplantıda konuşulmuş')}
  const sat=(x,dus)=>{const vg=x.vurgu||(dus?'dusuk':(x.yon!=='giden'&&(x.gun>=3||x.aciliyet>=3)?'yuksek':'normal')),gn=x.gun||x.cevapsiz_gun||0,bay=x.bayat&&x.bayat.neden?x.bayat:null
    const et=x.etiket||(gn>=3||x.yon==='giden'&&gn?L('{n} gün',{n:gn}):gunTxt(x.tarih)),oz=bay?L('teyit et: {n}',{n:bayNed[bay.neden]||bay.neden}):(x.ozet||x.neden_kisa||x.neden||'')
    const ned=oz||x.degerlendirilmedi?`<span class=ned${bay&&bay.kaynak?` title="${esc(bay.kaynak)}"`:''}>${x.degerlendirilmedi&&!x.ozet?`<i class=dy>${esc(L('Değerlendirilmedi'))}</i>${oz?' · ':''}`:''}${esc(oz)}</span>`:''
    return`<div class="epsar ${vg}${bay?' bayat':''}${x.id===sec?' sec':''}" role=presentation><button type=button role=option class="epr${x.id===sec?' sec':''}" aria-selected="${x.id===sec}" data-bn=epsec data-id="${esc(x.id)}"><span class=ust><b class=kim>${esc(x.kim||'')}</b><span class=konu>${esc(x.konu||'')}</span><span class="etk${vg==='yuksek'?' gec':''}">${esc(et)}</span></span>${ned}</button>${epEylem(x,dus)}</div>`}
  const grup=(b,ls)=>ls.length?`<h3 class=epalt>${esc(b)}</h3><div class=bliste role=listbox aria-label="${esc(b)}">${ls.map(x=>sat(x,false)).join('')}</div>`:''
  return`<section class=blk id=bnEp aria-label="${L('E-postalar')}"><div class=bbas><h2>${L('E-postalar')}</h2><span class=sag>${esc(L('Mail · güncellendi {t}',{t:goreliSaat(epV.guncel)}))}</span></div>`+uy
    +grup(L('Senden cevap bekleyenler'),bk)+grup(L('Senin dönüş beklediklerin'),dn)
    +(bg?`<p class="sakin epbilgi">${esc(L('{n} ileti yalnız bilgi (CC, toplu, otomatik)',{n:bg}))}</p>`:'')
    +(ds.length?`<button type=button class="b sade epdusbas" data-bn=epdus aria-expanded="${epDusAcik}">${esc(L('Düşük öncelikli ({n})',{n:ds.length}))}</button><div class="bliste epdusl" role=listbox aria-label="${esc(L('Düşük öncelikli ({n})',{n:ds.length}))}"${epDusAcik?'':' hidden'}>${ds.map(x=>sat(x,true)).join('')}</div>`:'')+`</section>`}
function ytBlok(){const v=ytV,ls=v?(v.tarihler||[]).slice(0,4):[];if(!ls.length)return'';const iz=v.izinler||{},kay=[iz.kisiler?L('Kişiler'):'',iz.takvim?L('Takvim'):'',iz.animsaticilar?L('Anımsatıcılar'):''].filter(Boolean).join(' · '),dg=ls.find(x=>x.tur==='dogum_gunu'&&x.kisi)
  return`<section class=blk aria-label="${L('Yaklaşan tarihler')}"><div class=bbas><h2>${L('Yaklaşan tarihler')}</h2>${kay?`<span class=sag>${esc(kay)}</span>`:''}</div><div class=bliste>`
    +ls.map(x=>`<div class=ktr><span class="ne mono" title="${esc(goreliTam(x.tarih))}">${esc(goreliTarih(x.tarih))}</span><span class=km>${esc(x.metin||'')}</span></div>`).join('')
    +`</div>${dg?`<div class=keylem><button type=button class=b data-bn=ktkut data-tarih="${esc(dg.tarih)}" data-kisi="${esc(dg.kisi)}" title="${esc(dg.metin||'')}">${L('Kutlama mesajı taslağı')}</button></div>`:''}</section>`}
async function epIslem(islem,id,b,ek){if(!id)return;if(b)b.disabled=true;let r={};try{r=await bnYaz('/eposta-onemli',{islem,id,...(ek||{})})}catch(e){}if(b)b.disabled=false
  if(!r.ok){bnBildir(L('Yapılamadı')+(r.err?' — '+r.err:''));return}
  if(islem==='taslak'&&r.taslak){const t=r.taslak,p=postaUrl({md:t.govde||'',baslik:t.konu||'',alicilar:t.alicilar||[]},(t.alicilar||[]).length?'k':'');if(p.kisa)try{await navigator.clipboard.writeText(p.duz)}catch(e){}brAc(p.u,p.yeni);bnBildir(L('Taslak açıldı; göndermek sende'));return}
  if(epV)epV={...epV,bekleyen:r.bekleyen||epV.bekleyen,donus:r.donus||epV.donus,dusuk:r.dusuk||epV.dusuk,bilgi_sayi:r.bilgi_sayi!=null?r.bilgi_sayi:epV.bilgi_sayi,ozet_sayi:r.ozet_sayi!=null?r.ozet_sayi:epV.ozet_sayi,onemli:r.onemli||epV.onemli,cevapsiz:r.cevapsiz||epV.cevapsiz};epSec=null;epMenuId=''
  bnBildir(islem==='yanlis_oncelik'?L('Not aldım; öncelik düzeltilecek'):islem==='onemli_kisi'?L('Bu kişi artık önemli sayılacak'):islem==='onemsiz_gonderen'?L('Bu gönderen artık yalnız bilgi olarak sayılacak'):islem==='yoksay'?L('Listeden kaldırıldı'):L('Yarın sabah yeniden hatırlatılacak'));if(last)bnCiz(last)}
document.addEventListener('toggle',ev=>{const d=ev.target;if(d&&d.classList&&d.classList.contains('epdiger'))epMenuId=d.open?d.dataset.id:''},true)
function epSecUygula(id){const e=document.getElementById('bnEp');if(!e)return;e.querySelectorAll('.epr').forEach(r=>{const o=r.dataset.id===id;r.classList.toggle('sec',o);r.setAttribute('aria-selected',o);r.parentElement.classList.toggle('sec',o)});epMenuId=''}  // eylemler satırda hazır; seçim yalnız işaret (dokunmatikte eylemleri gösterir)
async function ytKutla(b){b.disabled=true;let r={};try{r=await bnYaz('/yaklasan-tarihler',{islem:'taslak',tarih:b.dataset.tarih,kisi:b.dataset.kisi})}catch(e){}b.disabled=false
  bnBildir(r.ok?(r.sonuc||L('Taslak açıldı; göndermek sende')):r.err==='toplantida'?L('Toplantı bitince yeniden dene'):L('Taslak açılamadı')+(r.err?' — '+r.err:''))}
// ---- Ekip (adım 2'de taşındı, 5. adımda süslenecek): kimde bekliyor (başkalarının açık işleri kişiye göre), başkalarından beklediklerin, İzleme (Monitör), dış karar kayıtları, ekip paylaşımı durumu
function ekipIc(){const bs=bnBaskasi(),bg=bs.filter(x=>x.gecikti).length,z=izV,gr=new Map(),dis=((bnV||{}).dis||[])
  bs.forEach(x=>{const k=x.kim||'';if(!gr.has(k))gr.set(k,[]);gr.get(k).push(x)})
  const kis=[...gr].map(([ad,ls])=>{const g=ls.filter(x=>x.gecikti);return{ad,ls,g,eski:g.length?Math.max(...g.map(x=>-(x.kalan_gun||0))):0}}).sort((a,b)=>b.g.length-a.g.length||b.ls.length-a.ls.length).slice(0,8)
  const alt=[bs.length?L('Başkalarından beklediklerin: {n} iş',{n:bs.length}):'',bg?L('{g} tanesi gecikti',{g:bg}):'',z&&z.acik&&z.yeni_sapma_sayi?L('izlemede {n} yeni sapma',{n:z.yeni_sapma_sayi}):''].filter(Boolean).join(' · ')
  let h=`<div class=sayfab><div class=sbas><h1>${L('Ekip')}</h1>${alt?`<span class=alt>${esc(alt)}</span>`:''}${ortSatir()}</div><div class=sag>${sayfaMenu('ekip')}</div></div>`
  if(kis.length)h+=`<section class=bolum aria-label="${L('Kimde bekliyor')}"><div class=bbas><h2>${L('Kimde bekliyor')}</h2></div><div class=kisiler2>${kis.map(k=>`<button type=button class=kisikart data-bn=ekipkisi data-k="${esc(k.ad)}" title="${esc(L('Kararlar ve işlerde bu kişiyi göster'))}"><span class=kk><span class=kisi-yuz aria-hidden=true>${esc(bnBas(k.ad)||'–')}</span><b>${esc(k.ad||L('sahipsiz'))}</b></span><span class=ks><span class=sayi>${k.ls.length}</span><span>${L('açık iş')}</span></span><span class="kd ${k.g.length?'gec':'ok'}">${esc(k.g.length?L('{n} gecikmiş · en eski {g} gün',{n:k.g.length,g:k.eski}):L('Zamanında'))}</span></button>`).join('')}</div></section>`
  if(bs.length)h+=`<section class=bolum aria-label="${L('Başkalarından beklediklerin')}"><div class=bbas><h2>${L('Başkalarından beklediklerin')}</h2>${bs.length>6?`<button type=button class=bag data-bn=panel data-ref=bsk>${esc(L('Tümü · {n}',{n:bs.length}))}</button>`:''}</div><div class=liste>${bs.slice(0,6).map(bsBaskasi).join('')}</div></section>`
  if(z&&z.acik)h+=`<section class=bolum aria-label="${L('İzleme')}"><div class=bbas><h2>${L('İzleme')}</h2><button type=button class=bag data-bn=kmk data-k=izayar>${L('İzleme ayarı')}</button></div>${izBolum()}</section>`
  dis.forEach(d=>{if(!d.ok){h+=`<section class=bolum><p class=sakin>${esc(d.ad)}: ${L('defter okunamadı')} — ${esc(d.hata||'')}</p></section>`;return}
    if(!d.kayitlar.length)return  // dış karar kaydı (ayar dis_defter, dosya türü): salt-okunur katman, kaynak etiketiyle; Suflor'un grafına karışmaz
    h+=`<section class=bolum><div class=bbas><h2>${esc(d.ad)}</h2><span class=sag>${esc(L('{n} açık kayıt (yalnız okunur)',{n:d.acik}))}</span></div><div class=ince>${d.kayitlar.slice(0,5).map(x=>bnDisSatir(x,d.ad)).join('')}</div>${d.acik>5?`<div class=keylem><button type=button class="b sade" data-bn=panel data-ref="d:${esc(d.ad)}">${L('Tümü ({n})',{n:d.acik})}</button></div>`:''}</section>`})
  if(!bs.length&&!(z&&z.acik)&&!dis.some(d=>d.ok&&d.kayitlar.length))h+=`<p class=sakin>${L('Başkalarına atanmış açık iş yok. Toplantıda birine iş verildiğinde burada kişiye göre görünür.')}</p>`
  return h}
const bsBaskasi=x=>bsSat({id:x.id,ek:!x.dis&&knKid(x)?` data-bn=knac data-kid="${esc(knKid(x))}"`:'',nokta:x.gecikti?'gec':'',t:esc(x.metin),a:[x.kim?`<button type=button class=varlik data-bn=panel data-ref="k:${esc(x.kim)}">${esc(x.kim)}</button>`:'',tpAd(x)].filter(Boolean).join(' · '),e:x.vade?goreliSpan(x.vade,x.gecikti?'etiket gec':'etiket notr',true):'',d:x.dis||!(x.kayit_id||x.id)?'':`<button type=button class=b data-bn=emenu data-kid="${esc(x.kayit_id||x.id)}" title="${L('E-posta ya da Teams taslağı, ertele, ata')}">${L('Hatırlat')}</button>`,x:`<button type=button class=em data-bn=isbit data-id="${esc(x.id)}" title="${L('Yapıldı')}" aria-label="${L('Yapıldı')}">${ic('check')}</button>`})
// ---- Geçmiş (adım 2): Toplantılarda ara + Dökümler + Konuşma geçmişi, son toplantılar (özet / karar ve iş panosu, satır ⋯ ve sağ tık: PDF · Kopyala · .md · e-posta), Araştırmalar (GET /arastirma)
let gcAk=null
function gcSatir(r){const har=!!r.harita,ad=r.gorsel==='karar_is',ac=gcAk===r.id
  const men=ac?akMenu('sn:'+r.id,-1,(har?`<button class=aki data-son="${esc(r.id)}" data-tur=harita role=menuitem>${ic('harita',ad?L('Karar ve iş panosu'):L('Zihin haritası'))}</button><button class=aki data-son="${esc(r.id)}" data-tur=pdf role=menuitem>${ic('belge',ad?L('Panoyu PDF olarak hazırla'):L('Haritayı PDF olarak hazırla'))}</button><button class=aki data-son="${esc(r.id)}" data-tur=pdf data-posta=1 role=menuitem>${ic('posta',L('PDF, Mail taslağına ekli'))}</button>`:'')+`<button class=aki data-son="${esc(r.id)}" data-tur="" role=menuitem>${ic('belge',L('Özeti aç'))}</button><hr>`):''
  return bsSat({id:'gc-'+r.id,ek:` data-gc="${esc(r.id)}"`,ikon:'chat',t:esc(r.baslik||r.ad),a:[esc(gunTxt(r.at)),...ciktiP(r.cikti).map(esc)].join(' · '),
    e:`<span class="etiket notr">${esc(har?(ad?L('Karar ve iş panosu'):L('Zihin haritası')):L('Özet'))}</span>`,d:`<button type=button class=b data-bn=son data-id="${esc(r.id)}" data-tur="${har?'harita':''}">${L('Aç')}</button>`,
    x:`<span class=akw><button type=button class=em data-bn=gcak data-id="${esc(r.id)}" aria-haspopup=menu aria-expanded="${ac}" title="${L('Dışarı aktar')}" aria-label="${L('Dışarı aktar')}">${ic('dahasi')}</button>${men}</span>`})}
// Araştırmalar satırı (13 Kasım): ⋯ menüsü Geçmiş satırınınkiyle aynı (akMenu): üstte İlet (talimat hedefinin gelen kutusu · asistana «derinleştir»), ortada dışarı aktar
// (PDF · Kopyala · .md · E-posta taslağı — alıcısız, gönderen kullanıcı), altta Gizle. Gizlenen kayıt silinmez (aktarıcıda gizlenen.jsonl); Geri al ve «Gizlenenler» listesinden Geri getir.
let arAk=null,arGzAcik=false,arGz=null
function arSatir(x,gz){const ac=!gz&&arAk===x.id,hd=(arV&&arV.hedefler)||{},i=esc(x.id)
  const ib=(bn,ikon,t,ek)=>`<button class=aki data-bn=${bn} data-id="${i}"${ek||''} role=menuitem>${ic(ikon,t)}</button>`
  const ilet=(hd.oturum||[]).map(o=>ib('arot','sohbet',L('İlet: {h}',{h:o.etiket||o.ad}),` data-h="${esc(o.ad)}"`)).join('')+(hd.asistan||[]).map(a=>ib('aras','chat',L('{ad}: derinleştir',{ad:a.gorunen||a.ad}),` data-a="${esc(a.ad)}"`)).join('')
  const isb=ib('aris','liste',L('İş olarak ekle'))
  const men=ac?akMenu('ar:'+x.id,-1,(ilet||'')+isb+'<hr>','<hr>'+ib('argiz','x',L('Gizle'))):''
  return bsSat({id:(gz?'arg-':'ar-')+x.id,ek:gz?'':` data-arm="${i}"`,ikon:'ara',t:esc(x.konu||''),a:[bsTarih(x.at),esc(L('{n} kaynak',{n:x.kaynak_sayisi||0}))].filter(Boolean).join(' · '),e:x.durum==='hata'?`<span class="etiket gec">${L('Hata')}</span>`:'',
    d:gz?`<button type=button class=b data-bn=argos data-id="${i}">${L('Geri getir')}</button>`:`<button type=button class=b data-bn=panel data-ref="ar:${i}">${L('Aç')}</button>`,
    x:gz?'':`<span class=akw><button type=button class=em data-bn=arak data-id="${i}" aria-haspopup=menu aria-expanded="${ac}" title="${L('Eylemler')}" aria-label="${L('Eylemler')}">${ic('dahasi')}</button>${men}</span>`})}
async function arIcerik(id){let k=arDetay[id];if(!k){try{k=await j('/arastirma?id='+encodeURIComponent(id))}catch(e){k=null}if(!k||k.hata)return null;arDetay[id]=k}
  const oz=String(k.sesli||'').trim()||(String(k.metin||'').split(/\n\s*\n/).find(p=>p.trim()&&!/^\s*[#>|-]/.test(p))||'').trim(),kay=(k.kaynaklar||[]).filter(x=>/^https?:\/\//.test(x.url||'')),d=k.at?new Date(k.at):new Date()
  const ks=kay.length?`\n## ${L('Kaynaklar')}\n`+kay.map(x=>`- [${String(x.baslik||x.url).replace(/[\[\]]/g,'')}](${x.url})`).join('\n')+'\n':'',bas=`# ${k.konu||''}\n${goreliTam(k.at)}\n\n`
  return {baslik:L('Araştırma')+' — '+(k.konu||''),dosya:akDosya(L('Araştırma')+' - '+(k.konu||''),isNaN(d)?undefined:d),alicilar:[],alicisiz:true,md:bas+oz+'\n'+ks,tam:bas+String(k.metin||'')+'\n'+ks}}
async function arGzYukle(){let r=null;try{r=await j('/arastirma?gizli=1')}catch(e){}arGz=r&&Array.isArray(r.kayitlar)?r.kayitlar:[];if(last)bnCiz(last)}
async function arGizle(id,gizle){if(gizle&&arV){arV={...arV,kayitlar:(arV.kayitlar||[]).filter(x=>x.id!==id),gizli_sayi:(arV.gizli_sayi||0)+1};arAk=null;if(last)bnCiz(last)}  // hemen düşer; doğrusu aktarıcıdan gelir
  let r={};try{r=await bnYaz('/arastirma',{islem:gizle?'gizle':'goster',id})}catch(e){}
  await bnEkYukle(true);if(arGzAcik)await arGzYukle()
  if(!r.ok){bnBildir(L('Yapılamadı.'));return}
  if(gizle)bnBildir(L('Araştırma gizlendi'),()=>arGizle(id,false));else bnBildir(L('Araştırma geri getirildi'))}
// «İş olarak ekle» (13 Kasım): küçük pencerede iş metni (varsayılan «<konu> araştırmasını değerlendir») ve isteğe bağlı son tarih; Ekle → POST /arastirma {islem:'is'} →
// aktarıcı var olan iş kaydı yolunu kullanır (talimat.py _is_kaydet → Kararlar ve işler), kayıt id'si is-bag.jsonl'de iş numarasına bağlanır. Gizli kipte aktarıcı reddeder.
let arIsId=''
function arIsAc(id){const x=((arV&&arV.kayitlar)||[]).find(y=>y.id===id)||{};arAk=null;if(last)bnCiz(last);arIsId=id
  bnE('aih').textContent=x.konu||'';bnE('aim').value=L('«{k}» araştırmasını değerlendir',{k:x.konu||''});bnE('ait').value='';bnE('aie').disabled=false;bnE('aih2').hidden=true;bnE('aid').showModal();bnE('aim').select()}
async function arIsYaz(){const m=bnE('aim').value.trim(),t=bnE('ait').value,he=bnE('aih2');if(m.split(/\s+/).length<2){he.textContent=L('İş metni kısa; en az iki sözcük yaz.');he.hidden=false;return}
  bnE('aie').disabled=true;let r={};try{r=await bnYaz('/arastirma',{islem:'is',id:arIsId,metin:m,tarih:t||''})}catch(e){}
  if(!r.ok){bnE('aie').disabled=false;he.textContent=r.err==='gizli'?L('Gizli kipte iş eklenmez.'):L('İş eklenemedi.');he.hidden=false;return}
  bnE('aid').close();bnBildir(L('İş olarak eklendi: Kararlar ve işler'));try{await bnVeriYukle(true);if(bnGor==='kayit')await knYukle(true)}catch(e){}}
async function arOturum(id,h){arAk=null;if(last)bnCiz(last);let r={};try{r=await bnYaz('/arastirma',{islem:'oturum',id,hedef:h})}catch(e){}
  bnBildir(r.ok?(r.sonuc||L('Gelen kutusuna bırakıldı')):r.err==='kapalı'?L('Oturuma iletme kapalı (ayar talimat)'):L('İletilemedi'))}
// {asistan}: derinleştir — Kararlar ve işler «asistana sor» gibi: sohbet paneli açılır, kayıt aktarıcıda veri bloğu olarak Konuş'un yazılı turuna gider
async function arAsistan(id,a){const x=((arV&&arV.kayitlar)||[]).find(y=>y.id===id)||{},as=(((arV||{}).hedefler||{}).asistan||[]).find(y=>y.ad===a)||{},ad=as.gorunen||a;arAk=null;if(last)bnCiz(last)
  const t=L('{ad}, «{k}» kaydını derinleştir: eksikler, çelişkiler ve sonraki adımlar',{ad,k:x.konu||''}),pn=shGonder(t);let r={};try{r=await bnYaz('/arastirma',{islem:'asistan',id,asistan:a})}catch(e){}
  const ok=!!r.ok;shGonderSonuc(pn,t,ok)
  if(!ok)bnBildir(r.err==='gizli'?L('Gizli kipte asistana verilmez.'):/hâlâ cevaplıyor|still answering/.test(String(r.err||''))?L('{ad} hâlâ cevaplıyor; bitince yeniden dene.',{ad}):L('Yapılamadı.'))
  refresh()}
function gecmisIc(s){const sl=s.son_toplantilar||[],ar=(arV&&arV.kayitlar)||[]
  let h=`<div class=sayfab><div class=sbas><h1>${L('Geçmiş')}</h1><span class=alt>${esc(L('Toplantılar, dökümler, konuşmalar ve araştırmalar'))}</span></div><div class=sag>${sayfaMenu('gecmis')}</div></div>`
  h+=`<section class=bolum aria-label="${L('Toplantılarda ara')}"><form class=gcara id=gcF role=search><input id=gcAra type=search placeholder="${L('Toplantılarda ara')}" aria-label="${L('Toplantılarda ara')}" autocomplete=off><button type=submit class=b>${ic('ara')}${L('Ara')}</button></form><div class=keylem><button type=button class="b sade" data-bn=kmk data-k=dokumler>${ic('dosya')}${L('Dökümler')}</button><button type=button class="b sade" data-bn=kmk data-k=konusma>${ic('hist')}${L('Konuşma geçmişi')}</button></div></section>`
  h+=`<section class=bolum aria-label="${L('Son toplantılar')}"><div class=bbas><h2>${L('Son toplantılar')}</h2><button type=button class=bag data-bn=kmk data-k=dokumler>${L('Tüm toplantılar')}</button></div>${sl.length?`<div class=liste>${sl.map(gcSatir).join('')}</div>`:`<p class=sakin>${L('Henüz özeti çıkmış toplantı yok.')}</p>`}${gcSoSatir(s)}</section>`
  const gzn=(arV&&arV.gizli_sayi)||0
  if(ar.length||gzn)h+=`<section class=bolum aria-label="${L('Araştırmalar')}"><div class=bbas><h2>${L('Araştırmalar')}</h2>${arV.aktif?`<span class=sag>${L('Araştırılıyor…')}</span>`:''}${gzn?`<button type=button class=bag data-bn=argz aria-expanded="${arGzAcik}">${arGzAcik?L('Gizlenenleri kapat'):L('Gizlenenler ({n})',{n:gzn})}</button>`:''}</div>${ar.length?`<div class=liste>${ar.map(x=>arSatir(x)).join('')}</div>`:`<p class=sakin>${L('Görünen araştırma yok.')}</p>`}${arGzAcik&&gzn?`<div class="liste argz" aria-label="${L('Gizlenen araştırmalar')}">${(arGz||[]).map(x=>arSatir(x,true)).join('')||`<p class=sakin>${L('Yükleniyor…')}</p>`}</div>`:''}</section>`
  return h}
// ---- Tazı raporu (v0.228.0): Bugün'de son raporlar (s.tazi.raporlar), tıklayınca sağ panelde okunur (bnRef tz:<dosya>; POST /tazi islem=rapor). Metin esc'li mdHtml ile çizilir.
let tzDetay={},tzAcik=false  // liste kapalı gelir; açık/kapalı durumu oturum içinde bellekte (yeniden çizimde korunur)
const tzTarih=x=>{const m=String(x.dosya||'').match(/(\d{4})-?(\d{2})-?(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:new Date((x.t||0)*1000).toISOString().slice(0,10)}
const tzAd=x=>x.tur==='tazi'?L('Tazı raporu'):x.tur==='toplanti'?L('Toplantı katılımcıları'):String(x.dosya||'').replace(/\.md$/,'').replace(/-?(?:\d{8}|\d{4}-\d{2}-\d{2})$/,'').replace(/-/g,' ').replace(/(^|\s)\S/g,c=>c.toLocaleUpperCase('tr'))
async function tzDetayAl(f){let r=null;try{r=await j('/tazi',{method:'POST',body:JSON.stringify({islem:'rapor',dosya:f})})}catch(e){}tzDetay[f]=r&&r.ok?r:null;if(bnRef==='tz:'+f&&last)bnPanelCiz(last)}
// Dışarı aktar yolu (akYap, tur 'tz'): Kopyala · E-postayla paylaş (yalnız taslak açar) · PDF olarak kaydet (yazdırma penceresi)
function tzIcerik(f){const k=tzDetay[f];if(!k||!k.metin)return null;const g=tzTarih(k),d=new Date(g+'T12:00:00');return{baslik:tzAd(k)+' — '+g,dosya:akDosya(tzAd(k),isNaN(d)?undefined:d),alicilar:[],md:k.metin}}
function tzEylem(f){const b=(k,t)=>`<button type=button class="b sade" data-ak=${k} data-kay="${esc('tz:'+f)}">${t}</button>`
  return `<div class="keylem tzeylem">${b('kopyala',L('Kopyala'))}${b('mail-o',L('E-posta'))}${b('pdf','PDF')}</div>`}
function tzBlok(s){const ls=(s.tazi&&s.tazi.acik&&s.tazi.raporlar)||[];if(!ls.length)return ''
  return `<section class="bolum tzb" aria-label="${L('Tazı raporu')}"><div class=bbas><h2><button type=button class=tzbas data-bn=tzac aria-expanded="${tzAcik}" aria-controls=tzliste>${esc(L('Tazı raporu ({n})',{n:ls.length}))}</button></h2></div><div class=liste id=tzliste${tzAcik?'':' hidden'}>${ls.map(x=>bsSat({id:'tz-'+x.dosya,ikon:'ara',ek:` data-bn=panel data-ref="tz:${esc(x.dosya)}"`,t:esc(tzAd(x)),a:bsTarih(tzTarih(x)),d:tpDug('tazi',x.dosya)+`<button type=button class=b data-bn=panel data-ref="tz:${esc(x.dosya)}">${L('Aç')}</button>`})).join('')}</div></section>`}
// ---- Tepkiler (12 Kasım): Tazı raporu ve Kesişim satırlarında küçük "işe yaradı / yanlış"; seçim işaretli kalır (tarayıcıda), POST /tepki yalnız kaynak+kimlik+değer yazar (metin yok)
let tpSec={};try{tpSec=JSON.parse(localStorage.getItem('tepki')||'{}')||{}}catch(e){}
const tpDug=(k,id)=>{const d=tpSec[k+':'+id],bt=(v,ik,ad)=>`<button type=button class="em${d===v?' on':''}" data-bn=tepki data-k="${k}" data-id="${esc(id)}" data-d=${v} aria-pressed="${d===v}" title="${esc(ad)}" aria-label="${esc(ad)}">${ic(ik)}</button>`
  return`<span class=tepki role=group aria-label="${L('Tepki')}">${bt('iyi','check',L('İşe yaradı'))}${bt('yanlis','x',L('Yanlış'))}</span>`}
function tpYap(b){const k=b.dataset.k,id=b.dataset.id,d=b.dataset.d,a=k+':'+id,yeni=tpSec[a]===d?'':d  // aynı düğmeye yeniden basmak seçimi kaldırır (arka uca yalnız seçim gider)
  if(yeni)tpSec[a]=yeni;else delete tpSec[a];try{localStorage.setItem('tepki',JSON.stringify(tpSec))}catch(e){}
  const g=b.parentElement;if(g)g.querySelectorAll('button').forEach(x=>{const o=x.dataset.d===yeni;x.classList.toggle('on',o);x.setAttribute('aria-pressed',o)})
  if(yeni)bnYaz('/tepki',{kaynak:k,id,deger:yeni}).catch(()=>{})}
function ksBlok(s){const k=s.kesisim;if(!k)return'';const d=k.duzeltilen||0,a=k.arastirilan||0,q=(k.cozulemeyen_onemli||[]).filter(x=>x&&x.id).length;if(!d&&!a&&!q)return''  // F3: Bugün'de yalnız bağlantı; ayrıntı ve tepki /kesisim sayfasında
  const p=[];if(d)p.push(L('{n} düzeltme',{n:d}));if(a)p.push(L('{n} araştırma',{n:a}));if(q)p.push(L('{n} soru',{n:q}))
  return`<button type=button class=ksbag data-bn=ksac aria-label="${esc(L('Kesişim sayfasını aç'))}">${esc(L('Kesişim: bugün {x}',{x:p.join(', ')}))} →</button>`}
// Gece durum önerileri (aktarici/mutabakat.py, /status mutabakat): kayıt bitmiş/yerini başka kayıt almış görünüyor; kanıt satırı + Onayla / Hayır
const mtbTarih=t=>{const d=new Date(String(t).slice(0,10)+'T12:00');return isNaN(d)?'':d.toLocaleDateString(L('tr-TR'),{day:'numeric',month:'long'})}
const MTB_KAYNAK={toplanti:'toplantı',dokum:'döküm',belge:'belge',eposta:'e-posta',takvim:'takvim',basecamp:'Basecamp'}
function mtbSat(s){const m=s.mutabakat;if(!m||!Array.isArray(m.oneriler))return[]
  return m.oneriler.filter(o=>o&&o.kayit&&(o.oneri==='bitti'||o.oneri==='yerini_aldi')&&!bnGizli.has(o.kayit)).map(o=>{const k=o.kanit,kt=k?[MTB_KAYNAK[k.kaynak]?L(MTB_KAYNAK[k.kaynak]):'',k.tarih?mtbTarih(k.tarih):''].filter(Boolean).join(', '):''
    return bsSat({id:o.kayit,nokta:'bek',ek:k&&k.alinti?` title="${esc(k.alinti)}"`:'',t:esc(o.baslik||''),a:esc((o.oneri==='bitti'?L('Bitmiş görünüyor'):L('Yerini başka karar almış görünüyor'))+(kt?' ('+L('kanıt: {k}',{k:kt})+')':'')),
      d:`<button type=button class=b data-bn=mtb data-i=onay data-id="${esc(o.kayit)}">${L('Onayla')}</button><button type=button class="b sade" data-bn=mtb data-i=red data-id="${esc(o.kayit)}">${L('Hayır')}</button>`})})}
async function arDetayAl(id){let r=null;try{r=await j('/arastirma?id='+encodeURIComponent(id))}catch(e){}arDetay[id]=r&&!r.hata?r:null;if(bnRef==='ar:'+id&&last)bnPanelCiz(last)}
const arMd=m=>mdHtml(String(m||'')).replace(/\[([^\]]+)\]\((https?:\/\/[^)\s"<]+)\)/g,(_,t,u)=>`<a href="${u}" target=_blank rel="noopener noreferrer">${t}</a>`)  // iddia kaynakları bağlantı (yeşil); metin önce kaçırılır
