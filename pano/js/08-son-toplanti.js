// toplantı sonu: Claude özeti kaydedince (ozet-hazir) pano boşken son 7 günün en yeni 3 toplantısı — karar/iş/açık sayısı, kararlar, öneri, özeti aç
function gunTxt(at){const d=new Date(at),sa=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')
  return goreliTarih(d)+' '+sa}  // v0.107.0 Mac tarih dili; tasarım sistemi: tek yardımcı (Bugün / Dün / 3 gün önce / 19 Eki) + saat
function cikti(c){const p=ciktiP(c);return p.length?` <span class=chip>${esc(p.join(' · '))}</span>`:''}
// 5 Kasım: iş sayısı tarihsiz işleri de söyler ("4 iş (2'si tarihsiz)"; tile'da "İş · 2'si tarihsiz"); iyelik eki sayının okunuşuna göre
function iyelik(n){n=+n||0;const b=n%10;return(b?{1:"'i",2:"'si",3:"'ü",4:"'ü",5:"'i",6:"'sı",7:"'si",8:"'i",9:"'u"}[b]:{0:"'ı",10:"'u",20:"'si",30:"'u",40:"'ı",50:"'si",60:"'ı",70:"'i",80:"'i",90:"'ı"}[n%100])||"'i"}
function isMetin(c,tile){const n=c.is||0,t=c.tarihsiz||0
  if(!t||t>n)return tile?L('İş'):L('{n} iş',{n})
  if(t===n)return tile?L('İş · hepsi tarihsiz'):L('{n} iş (hepsi tarihsiz)',{n})
  return tile?L("İş · {t}{ek} tarihsiz",{t,ek:iyelik(t)}):L("{n} iş ({t}{ek} tarihsiz)",{n,t,ek:iyelik(t)})}
// v0.117.0 (S136): toplantı yokken kutudan yazılan notlar — son 24 saat (aktarici/notlar.py); toplantıda gizli. ✕ notu siler.
function renderNotlar(s){const ls=s.notlar||[],sec=document.getElementById('nts');sec.hidden=!!s.aktif||!ls.length;if(sec.hidden)return
  document.getElementById('ntn').textContent=ls.length
  setH(document.getElementById('nt'),ls.map(x=>`<div class=nt><span class=z>${esc(gunTxt(x.at))}</span><span class=m>${esc(x.metin)}</span><button class="ib gh" data-not-sil="${esc(x.id)}" title="${L('Notu sil')}" aria-label="${L('Notu sil')}">${ic('x')}</button></div>`).join(''))}
document.getElementById('nt').addEventListener('click',async ev=>{const b=ev.target.closest('[data-not-sil]');if(!b)return;let r={};try{r=await j('/notlar',{method:'POST',body:JSON.stringify({sil:b.dataset.notSil})})}catch(e){}
  if(!r.ok)geciciDurum(L('Not silinemedi'),r.err||'');refresh()})
// Son toplantılar (30 Ekim): başlık + tek satır gri meta (Dün 14:30 · 4 karar · 10 iş · 4 açık); değerlendirme ve öneri yalnız satıra dokununca, Özeti aç orada; ⋯ dışarı aktar
const snAcik=new Set()
function ciktiP(c){c=c||{};return[['karar','{n} karar'],['is','{n} iş'],['acik','{n} açık']].filter(([k])=>c[k]>0).map(([k,m])=>k==='is'?isMetin(c):L(m,{n:c[k]}))}
function renderSon(s){const ls=(s.son_toplantilar||[]).slice(0,4),sec=document.getElementById('sns');sec.hidden=!!s.aktif||!ls.length;if(sec.hidden)return
  setH(document.getElementById('sn'),ls.map(r=>{const ac=snAcik.has(r.id),de=r.degerlendirme&&!/^(yok|-|—)\.?$/i.test(String(r.degerlendirme).trim())?r.degerlendirme:''
    const z=r===ls[0]&&r.harita
    return `<div class="sn${z?' sn-z':''}${ac?' acik':''}"><span class=eyi>${ic('chat')}</span><div class=t data-snac="${esc(r.id)}" title="${esc(r.ad||'')}"><div class=b>${esc(r.baslik||r.ad)}</div><div class=m>${esc([gunTxt(r.at),...ciktiP(r.cikti)].join(' · '))}</div>`
      +(ac?`<div class=snx>${de?`<div class=d>${esc(de)}</div>`:''}${r.oneri?`<div class=d><b>${L('Öneri')}:</b> ${esc(r.oneri)}</div>`:''}${(r.tazi||[]).length?`<div class=d><b>${esc(r.tazi_etiket||'Tazı')} · ${L('Tazı notu')}:</b><ul>${r.tazi.map(x=>`<li>${esc(x.satir)}</li>`).join('')}</ul></div>`:''}<div class=bt><button class=gh data-son="${esc(r.id)}">${L('Özeti aç')}</button></div></div>`:'')
      +`</div>${z?`<span class=snz><button class=pri data-son="${esc(r.id)}" data-tur=harita>${esc(sonTurAd(r))}</button><button class=gh data-son="${esc(r.id)}" data-tur=pdf title="${L('PDF dosyası hazırlar, Finder\'da gösterir')}">PDF</button></span>`:''}<span class=akw><button class="ib akd" data-aktar="sn:${esc(r.id)}" aria-haspopup=menu aria-expanded="${akAcik==='sn:'+r.id}" title="${r.gorsel==='karar_is'?L('Karar ve iş panosu, dışarı aktar'):L('Zihin haritası, dışarı aktar')}" aria-label="${r.gorsel==='karar_is'?L('Karar ve iş panosu, dışarı aktar'):L('Zihin haritası, dışarı aktar')}">${ic('dahasi')}</button>${akAcik==='sn:'+r.id?akMenu('sn:'+r.id,-1,r.harita?`<button class=aki data-son="${esc(r.id)}" data-tur=harita role=menuitem>${ic('harita',r.gorsel==='karar_is'?L('Karar ve iş panosu'):L('Zihin haritası'))}</button><button class=aki data-son="${esc(r.id)}" data-tur=pdf role=menuitem>${ic('belge',r.gorsel==='karar_is'?L('Panoyu PDF olarak hazırla'):L('Haritayı PDF olarak hazırla'))}</button><button class=aki data-son="${esc(r.id)}" data-tur=pdf data-posta=1 role=menuitem>${ic('posta',L('PDF, Mail taslağına ekli'))}</button><hr>`:''):''}</span></div>`}).join('')+soSatir(s))}
// 5 Kasım (panogor): Bugün'de son toplantı (Son toplantılar'ın ilk satırı, tekrarsız). En yeni kayıt, panosu/haritası varsa; toplantı bitince ertesi toplantıya kadar (kayıt 7 gün tutulur) görünür.
// Pano düğmesi tarayıcıda açar; PDF aktarıcıda hazırlanır (Chrome yazdırma), Finder'da seçili gösterilir ve dosya yolu panoya kopyalanır; Mail taslağı ayrı menüde, gönderme yok.
function sonTurAd(r){return r&&r.gorsel==='karar_is'?L('Karar ve iş panosu'):L('Zihin haritası')}
async function sonIs(id,tur,posta,dug){if(dug)dug.disabled=true;let r={};try{r=await j('/son-ac',{method:'POST',body:JSON.stringify({id,tur:tur||'',posta:!!posta})})}catch(e){}
  if(dug)dug.disabled=false
  if(!r.ok)geciciDurum(tur==='pdf'?L('PDF hazırlanamadı'):tur==='harita'?L('Zihin haritası açılamadı'):L('Özet açılamadı'),r.err||'')
  else if(tur==='pdf')geciciDurum(L('PDF hazır'),(r.ad||'')+(posta?'':' · '+L('Finder\'da gösterildi, dosya yolu panoda')),9000)
  return r}
// 3 Kasım (öğrenen sözlük): son toplantıların altında tek satır — son 7 günde öğrenilen biçim ve bekleyen aday (/status sozluk_ogrenme)
// Geçmiş sayfasında aynı bilgi sade satır (12 px, soluk): toplantı sonu öğrenen sözlüğün sayıları; ayrıntı sözlük onay kuyruğunda (döküm kontrolü / tc sozluk)
const gcSoSatir=s=>{const so=s.sozluk_ogrenme;return so&&(so.yeni||so.bekleyen)?`<p class=gcbilgi data-so=1>${esc(L('Sözlük: {n} yeni biçim öğrenildi, {m} aday bekliyor',{n:so.yeni||0,m:so.bekleyen||0}))}</p>`:''}
function soSatir(s){const so=s.sozluk_ogrenme;return so&&(so.yeni||so.bekleyen)?`<div class=m data-so=1>${esc(L('Sözlük: {n} yeni biçim öğrenildi, {m} aday bekliyor',{n:so.yeni||0,m:so.bekleyen||0}))}</div>`:''}
document.getElementById('sn').addEventListener('click',async ev=>{if(akTik(ev,renderSon))return;const b=ev.target.closest('[data-son]')
  if(!b){const a=ev.target.closest('[data-snac]');if(a&&!ev.target.closest('button')){const id=a.dataset.snac;if(snAcik.has(id))snAcik.delete(id);else snAcik.add(id);if(last)renderSon(last)}return}
  sonIs(b.dataset.son,b.dataset.tur||'',!!b.dataset.posta)})
// Bugün (toplantı yokken, 30 Ekim — kullanıcı onayladı: "sırada ne var, beni ne bekliyor, ne oldu"): başlık satırı (tarih + Bugün, Bugün | Bu hafta), sıradaki
// toplantı kartı (solda hazırlık şeridi — hafta görünümünün hazir/eksik/yok'u; saat, başlık, platform · kişi · hazırlık; Hazırlık / Başlat), altında tek satır
// "Sonra …". Bugün toplantı kalmadıysa ilk gelecek toplantı (Yarın 09:30): /takvim?hafta=0 (gerekirse 1), hazırlık da oradan. Claude izlerken gizli.
let bgHz=[],bgHzT=0,bgHzYuk=false,hzAc=null
async function bgHzYukle(zorla){if(bgHzYuk||(!zorla&&Date.now()-bgHzT<60000))return;bgHzYuk=true;bgHzT=Date.now()
  try{let ol=[];for(const h of [0,1]){const t=await j('/takvim?hafta='+h);ol=ol.concat((t.olaylar||[]).filter(o=>!o.gecmis&&!o.tum_gun&&o.baslatilir&&!o.paylasilan));if(ol.length>=3||!(t.en_cok>=1))break}
    if(JSON.stringify(ol)!==JSON.stringify(bgHz)){bgHz=ol;if(last){renderTakvim(last);renderBrifing(last)}}}catch(e){}
  bgHzYuk=false}
const HZW={hazir:'Hazır',eksik:'Eksik',yok:'Hazırlık yok'}
function hzDurum(o,s){const b=((s&&s.brifing)||{})[o.id]||{};return b.durum==='hazir'||o.hazirlik==='hazir'?'hazir':b.durum==='calisiyor'||b.durum==='hata'?'eksik':(o.hazirlik||'yok')}
function gunAd(o){const [y,m,d]=String(o.tarih||'').split('-').map(Number);if(!y)return'';const b=new Date();b.setHours(0,0,0,0);const g=Math.round((new Date(y,m-1,d)-b)/864e5)
  return g<=0?'':g===1?L('Yarın'):new Date(y,m-1,d).toLocaleDateString(L('tr-TR'),{weekday:'long'})}
// Hazırlık bağlantısı: hazırsa (ya da hazırlanıyor/hata) kartın altındaki brifingi açar-kapar; değilse brifingi başlatır (/brifing, hafta görünümündeki Hazırla ile aynı) ve açar
async function hazirlikTik(id,b){const o=tkBul(id);if(!o)return;const s=last||{},bd=((s.brifing||{})[id]||{}).durum
  if(hzAc===id)hzAc=null
  else if(bd||hzDurum(o,s)==='hazir')hzAc=id
  else{b.disabled=true;let r={};try{r=await j('/brifing',{method:'POST',body:JSON.stringify({olay:id})})}catch(e){}b.disabled=false
    if(!r.ok){geciciDurum(L('Brifing başlatılamadı'),r.err||'');return}hzAc=id;bgHzT=0}
  tkGor=id;if(last){renderTakvim(last);renderBrifing(last)}refresh()}
function renderTakvim(s){const sur=!!((s.oto_toplanti&&s.oto_toplanti.oturum)||(s.toplanti_oturum&&['aciliyor','calisiyor','bekliyor','izliyor'].includes(s.toplanti_oturum.durum))),t=s.takvim||{},ca=s.claude_age_s,izliyor=ca!=null&&ca<120,sec=document.getElementById('tks')
  // toplantı sürerken büyük kart yok: durum cümlesindeki Başlat yalnız formu açar
  const top=!!s.aktif,form=!document.getElementById('tkf').hidden
  if(top&&!hfOnceTop){if(hfAcik)hfAc(false);if(stAcik)stAc(false)}hfOnceTop=top  // toplantı başlayınca hafta görünümü kapanır (Şimdi bölümü görünsün)
  // 3 Kasım (ardışık toplantı): takvim ve Başlat yalnız canlı toplantıda gizli — bitiyor/bitti'de ve Claude toplantı sonunu yaparken (izliyor) görünür
  sec.hidden=top&&!form
  ;['tk','tkh','tkalt'].forEach(i=>document.getElementById(i).style.display=top?'none':'');sonCiz(s,top);if(top)return
  bgHzYukle()
  tkOlaylar=t.olaylar||[];const h=document.getElementById('tkh'),loc=L('tr-TR'),nw=new Date()
  h.textContent=!t.uygulama?L('Takvim bağlı değil — toplantıyı elle başlatabilirsin.'):t.durum==='izin_yok'?L('Takvim izni yok — Sistem Ayarları → Gizlilik ve Güvenlik → Takvimler → Suflor Takvim.'):t.durum==='bekliyor'?L('takvim okunuyor…'):(t.durum&&t.durum!=='ok'?L(t.hata||t.durum):'')
  setH(document.getElementById('tktr'),esc(nw.toLocaleDateString(loc,{weekday:'long'})+', '+nw.toLocaleDateString(loc,{day:'numeric',month:'long'})))
  const hz=Object.fromEntries(bgHz.map(x=>[x.id,x])),bid=new Set(tkOlaylar.map(x=>x.id)),an=Date.now()
  tkListe=[...tkOlaylar.map(x=>Object.assign({},hz[x.id],x)),...bgHz.filter(x=>!bid.has(x.id)&&!x.reddettin&&+new Date(x.baslangic)>an).map(x=>Object.assign({},x,{dk:Math.round((+new Date(x.baslangic)-an)/6e4)}))]
  if(!tkListe.some(x=>x.id===tkGor))tkGor=tkListe.length?tkListe[0].id:null
  const o=tkListe.find(x=>x.id===tkGor),ilk=o&&o===tkListe[0];let html
  if(o){const hd=hzDurum(o,s),bd=((s.brifing||{})[o.id]||{}).durum,gn=gunAd(o),ks=o.kisi_sayisi||(o.katilimcilar||[]).length,ac=hzAc===o.id
    const e=[o.suruyor?L('Şimdi'):gn||(ilk?L('Sıradaki'):L('Bugün')),`${o.saat}–${o.bitis_saat}`,!o.suruyor&&!gn&&o.dk>0&&o.dk<=60?L('{n} dk sonra',{n:o.dk}):''].filter(Boolean).join(' · ')
    const alt=[o.platform?`<span class=pl>${ic('video')}${esc(PL[o.platform]||o.platform)}</span>`:'',ks?esc(L('{n} kişi',{n:ks})):'',o.ben_duzenleyen?esc(L('düzenleyen sen')):'',o.reddettin?esc(L('daveti reddettin')):'',`<span class="hzw hz-${esc(hd)}">${esc(L(HZW[hd]||HZW.yok))}</span>`].filter(Boolean).join('<i class=nk>·</i>')
    const hzl=bd==='calisiyor'?L('Hazırlanıyor…'):hd==='hazir'||bd==='hata'?L('Hazırlık'):L('Hazırla')
    html=`<div class="sira hz-${esc(hd)}" data-sec="${esc(o.id)}"><div class=t><div class=e>${esc(e)}</div><div class=b title="${esc(o.baslik||'')}">${esc(o.baslik||L('(başlıksız)'))}</div><div class=sp>${alt}</div></div><div class=ss><button class="gh lnk" data-hz="${esc(o.id)}" aria-expanded="${ac}" title="${L('{asistan} geçmiş görüşmelere, açık sorulara ve belgelere bakıp kısa bir brifing hazırlar.')}">${esc(hzl)}</button><button class=pri data-bas="${esc(o.id)}">${L(sur&&o.suruyor?'Toplantı sürüyor':'Başlat')}</button></div></div>`
    const dig=tkListe.filter(x=>x!==o).slice(0,2)
    if(dig.length)html+=`<div class=sonra><span>${L(ilk?'Sonra':'Diğer')}</span> ${dig.map(x=>{const g=gunAd(x);return`<button type=button class=lnk data-sec="${esc(x.id)}" title="${esc(x.baslik||'')}">${esc((g?g+' ':'')+x.saat+' '+(x.baslik||''))}</button>`}).join('<i class=nk>·</i>')}</div>`}
  else html=`<div class="sira bos"><div class=t><div class=b>${L('Takvimde yakın toplantı yok')}</div></div><div class=ss><button class=pri data-bas="">${L(sur?'Toplantı sürüyor':'Toplantı başlat')}</button></div></div>`
  setH(document.getElementById('tk'),html)
  document.getElementById('tke').hidden=!o}
// panodan güncelleme düğmesi; aktarıcı yeni sürümle kalkınca pano kendini yeniler
let ilkSurum=null
function guncellemeCiz(s){const g=s.guncelleme||{},b=document.getElementById('gun')
  if(!ilkSurum)ilkSurum=s.surum;else if(s.surum&&s.surum!==ilkSurum){try{sessionStorage.setItem("guncellendi",JSON.stringify({v:s.surum,t:Date.now()}))}catch(e){};location.reload();return}
  const goster=g.durum==="calisiyor"||g.durum==="hata"||(g.durum==="var"&&!s.aktif);b.hidden=!goster;if(!goster)return
  b.className=g.durum==="var"?"pri":"";b.disabled=g.durum==="calisiyor";b.title=g.durum==="hata"?(g.hata||""):""
  if(b.dataset.onay&&g.durum==="var")return;b.textContent=g.durum==="var"?L(g.acil?"Önemli güncelleme":"Güncelle"):g.durum==="calisiyor"?L("Güncelleniyor…"):L("Güncelleme başarısız — yeniden dene");if(g.durum==="var")b.title=L(g.acil?"Güvenlik ya da kurulum düzeltmesi — toplantı yokken güncelle":"Yeni sürüm hazır")}
// ilk tıklama onay ister (5 sn), ikincisi günceller — tarayıcının onay penceresi yerine
document.getElementById('gun').onclick=async ev=>{const b=ev.currentTarget
  if(!b.dataset.onay){b.dataset.onay="1";b.textContent=L("Onayla — birkaç saniye kesilir");setTimeout(()=>{delete b.dataset.onay;if(last)guncellemeCiz(last)},5000);return}
  delete b.dataset.onay;b.disabled=true;b.textContent=L("Güncelleniyor…");let r={};try{r=await j('/guncelle',{method:'POST',body:"{}"})}catch(e){}
  if(!r.ok){b.disabled=false;b.textContent=L("Güncelleme başarısız — yeniden dene");geciciDurum(L("Güncellenemedi"),r.err||"")}}
// v0.111.0: arka plandaki toplantı oturumu — /status'ta özet (n: ileti sayısı), yeni iletiler /toplanti-oturum?n= ile; kutudaki yazı oturum soru sorunca ona gider
let tosM=[],tosN=0,tosT0=null,tosAyr=false,tosYuk=false,tosAcik=false
const TOS_D={aciliyor:"açılıyor…",calisiyor:"çalışıyor",izliyor:"toplantıyı izliyor",bekliyor:"cevabını bekliyor",kapali:"kapandı",hata:"durdu",terminalde:"Terminal'de"}
// v0.115.0 (kullanıcı, 22 Ekim: Claude'un ne yaptığı görünmüyordu): tek satır canlı durum — panoda, mini panoda ve Mac panelinde aynı
function tosSatir(o){if(!o)return"";if((o.izinler||[]).length)return L("{asistan} iznini bekliyor")
  if(o.durum==="aciliyor")return L("{asistan} açılıyor…");if(o.durum==="izliyor")return L("{asistan} şu an: toplantıyı izliyor")
  if(o.durum!=="calisiyor")return"";const e=o.etkinlik,sn=e?e.sn:o.sn
  return (e?L("{asistan} şu an: {m}…",{m:e.metin}):L("{asistan} şu an: düşünüyor…"))+(sn>=15?" · "+L("{n} sn",{n:sn}):"")}
// v0.115.0: arka plandaki oturumun araç izni ayrı kart değil — Claude bölümünde ve mini panoda Onayla / Reddet (/eylem-karar, anahtarlı)
function tosIzinHtml(o){return (o.izinler||[]).map(x=>`<div class=tiz><div class=d>${esc(x.metin)}</div><div class=tsc><button class=pri data-tiz="${esc(x.id)}" data-d=onaylandi>${esc(L("Onayla"))}</button><button class=gh data-tiz="${esc(x.id)}" data-d=reddedildi>${esc(L("Reddet"))}</button></div></div>`).join('')}
function tosMd(t){return esc(t).replace(/\*\*([^*\n]+)\*\*/g,'<b>$1</b>').replace(/`([^`\n]+)`/g,'<code>$1</code>')}
async function renderOturum(s){const o=s.toplanti_oturum,sec=document.getElementById('tos'),ta=document.getElementById('n');sec.hidden=!o
  if(!o){if(ta){delete ta.dataset.cevap;ta.placeholder=yazIpucu(document)}return}
  if(o.t0!==tosT0){tosT0=o.t0;tosM=[];tosN=0}
  if(o.n>tosN&&!tosYuk){tosYuk=true;try{const v=await j('/toplanti-oturum?n='+tosN);(v.mesaj||[]).forEach(m=>{if(m.i>tosN){tosM.push(m);tosN=m.i}});tosM=tosM.slice(-400)}catch(e){}tosYuk=false}
  const sor=o.soru&&o.soru.secenek?o.soru:null,bek=o.durum==="bekliyor"||!!sor,canli=["aciliyor","calisiyor","bekliyor","izliyor"].includes(o.durum);sec.classList.toggle('bek',bek)
  document.getElementById('tosd').textContent=L(TOS_D[o.durum]||o.durum)+(o.konu?" · "+o.konu:"")
  document.getElementById('tosx').hidden=o.durum!=="calisiyor";{const k=document.getElementById('tosk');k.hidden=!canli;if(!canli){k.dataset.emin="";k.textContent=L("Kapat")}}document.getElementById('tost').hidden=!(o.terminal&&o.durum!=="terminalde");document.getElementById('tosa').textContent=L(tosAyr?"Kısa":"Ayrıntı")
  const box=document.getElementById('tom'),alt=box.scrollHeight-box.scrollTop-box.clientHeight<30,gor=tosM.filter(m=>tosAyr||m.kim!=="arac")
  const sig=gor.length+"|"+(gor.length?gor[gor.length-1].i:0)+"|"+tosAyr+"|"+(sor?sor.i:0)
  if(box.dataset.sig!==sig){box.dataset.sig=sig;setH(box,gor.map(m=>`<div class="tm ${esc(m.kim)}"><span class=tt>${esc(m.t)}</span>${m.kim==="izin"?esc(L("İzin istedi: "))+esc(m.metin):m.kim==="ben"?esc(L("Sen: "))+tosMd(m.metin):tosMd(m.metin)}${sor&&m.i===sor.i?tosSecHtml(sor):''}</div>`).join('')||`<div class=hint>${esc(L("{asistan} hazırlanıyor…"))}</div>`);if(alt)box.scrollTop=box.scrollHeight}
  {const t=tosSatir(o),l=document.getElementById('tol');l.hidden=!t;l.textContent=t;l.title=t;l.classList.toggle('iz',!!(o.izinler||[]).length)
   const z=document.getElementById('tiz'),zs=(o.izinler||[]).map(x=>x.id).join();if(z.dataset.sig!==zs){z.dataset.sig=zs;setH(z,tosIzinHtml(o))}}
  const b=document.getElementById('tob');b.className='tob'+(o.durum==="hata"?' er':'')
  b.textContent=o.durum==="hata"?(o.hata||L("Oturum kapandı")):(o.izinler||[]).length?"":sor?L("{asistan} cevabını bekliyor — bir düğmeye bas ya da kutuya yaz."):bek?L("{asistan} cevabını bekliyor — aşağıdaki kutuya yaz, Return'e bas."):""
  if(ta){if(bek)ta.dataset.cevap=1;else delete ta.dataset.cevap;ta.placeholder=bek?L("Cevabını yaz"):yazIpucu(document)}
  // 30 Ekim (Bugün): toplantı yokken oturumun durum/rapor metinleri katlı — başlıkta durum, altında son iletinin iki satırı; dokununca tamamı ve düğmeler
  {const kap=!s.aktif&&!tosAcik&&!bek&&!(o.izinler||[]).length,p=document.getElementById('tosn'),son=[...tosM].reverse().find(m=>m.kim==="claude"),t=son?String(son.metin).replace(/[*`#>|]/g,'').replace(/\s+/g,' ').trim():''
   sec.classList.toggle('kapali',kap);p.hidden=!kap||!t;p.textContent=t}}
// Kapanış turu (6 Kasım, S211/S227): toplantı sürerken bu toplantının dizisinden/katılımcılarından açık işler (vadesi geçen önce) ve teyit bekleyen kararlar (/kapanis-turu).
// İş: Bitti (/is-durum yapildi) · Ertele (/kayit-eylem ertele, bir hafta sonra) · İptal (/is-durum yapilmadi) · Sonra (yalnız bu toplantıda gizlenir). Karar: Onayla (/karar-onay) · Reddet (/kayit-eylem) · Sonra.
// Yazma 5 sn sonra (Geri al bu sürede vazgeçer); her yazma bir olay. Deneme toplantısında aktarıcı yalnız deneme kayıtlarını verir.
let ktV=null,ktT=0,ktTop='',ktSonra=new Set(),ktBek=new Set(),ktGiz=false
async function ktYukle(){try{const v=await j('/kapanis-turu');ktV=v&&v.ok?v:null}catch(e){ktV=null}ktT=Date.now();if(last)renderKapanis(last)}
function ktSat(x){const ka=x.tur==='karar',o=x.onay||{},kim=x.kim?esc(x.kim)+' · ':''
  const d=ka?(o.durum==='onaylanmadi'?L('onaylanmadı'):(o.gun>=1?L('{n} gündür onay bekliyor',{n:o.gun}):L('onay bekliyor'))):x.vade?esc(goreliTarih(x.vade,true)):L('tarihsiz')
  const dg=(ka?(o.durum==='onaylanmadi'||x.eski):x.gecikti)?' gec':'',kay=[x.baslik,x.tarih?goreliTarih(String(x.tarih).slice(0,10)):''].filter(Boolean).join(', ')
  const bt=(a,t)=>`<button type=button class=gh data-kt=${a}>${esc(t)}</button>`
  return`<div class=kts data-id="${esc(x.id)}"><span class=ktm>${esc(x.metin)}</span><span class="ktd${dg}">${kim}${d}${kay?' · '+esc(kay):''}</span><span class=kte>${ka?bt('onayla',L('Onayla'))+bt('reddet',L('Reddet')):bt('bitti',L('Bitti'))+bt('ertele',L('Ertele'))+bt('iptal',L('İptal'))}${bt('sonra',L('Sonra'))}</span></div>`}
function renderKapanis(s){const sec=document.getElementById('kts'),o=s&&s.toplanti_oturum,t0=o&&o.t0?String(o.t0):''
  if(!s||!s.aktif||!o){sec.hidden=true;return}
  if(t0!==ktTop){ktTop=t0;ktSonra=new Set();ktGiz=false;ktV=null;ktT=0}
  if(!ktT||Date.now()-ktT>120000){ktT=Date.now();ktYukle();return}
  const gz=x=>!ktSonra.has(x.id)&&!ktBek.has(x.id),is=((ktV||{}).isler||[]).filter(gz),ka=((ktV||{}).kararlar||[]).filter(gz)
  sec.hidden=ktGiz||!(is.length+ka.length);if(sec.hidden)return
  const sy=(ktV||{}).say||{};document.getElementById('ktn').textContent=L('{n} iş, {k} karar',{n:sy.is||0,k:sy.karar||0})
  setH(document.getElementById('kt'),(is.length?`<div class=ktb>${esc(L('Açık işler'))}</div>`+is.map(ktSat).join(''):'')+(ka.length?`<div class=ktb>${esc(L('Teyit bekleyen kararlar'))}</div>`+ka.map(ktSat).join(''):''))}
function ktHafta(){const d=new Date();d.setDate(d.getDate()+7);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
document.getElementById('ktk').onclick=()=>{ktGiz=true;if(last)renderKapanis(last)}
document.getElementById('kt').addEventListener('click',ev=>{const b=ev.target.closest('button[data-kt]');if(!b)return;const id=b.closest('.kts').dataset.id,a=b.dataset.kt
  if(a==='sonra'){ktSonra.add(id);if(last)renderKapanis(last);return}
  const yap={bitti:()=>bnYaz('/is-durum',{id,durum:'yapildi'}),iptal:()=>bnYaz('/is-durum',{id,durum:'yapilmadi'}),ertele:()=>bnYaz('/kayit-eylem',{id,eylem:'ertele',vade:ktHafta(),neden:L('kapanış turu')}),
    onayla:()=>bnYaz('/karar-onay',{idler:[id]}),reddet:()=>bnYaz('/kayit-eylem',{id,eylem:'reddet'})}[a]
  const msj={bitti:L('İş yapıldı olarak işaretlendi'),iptal:L('İş iptal edildi'),ertele:L('İş bir hafta ertelendi'),onayla:L('Karar onaylandı'),reddet:L('Karar reddedildi')}[a]
  if(!yap)return;ktBek.add(id);if(last)renderKapanis(last)
  const t=setTimeout(async()=>{try{await yap()}catch(e){}ktBek.delete(id);await ktYukle()},5000)
  bnBildir(msj,()=>{clearTimeout(t);ktBek.delete(id);if(last)renderKapanis(last)})})
document.getElementById('tos').addEventListener('click',ev=>{if(last&&last.aktif)return;if(ev.target.closest('button,a,.tom,#tiz'))return;if(!ev.target.closest('.sh,#tosn'))return;tosAcik=!tosAcik;if(last)renderOturum(last)})
document.getElementById('tosx').onclick=async ev=>{ev.currentTarget.disabled=true;try{await fetch('/toplanti-oturum',{method:'POST',body:JSON.stringify({islem:"durdur"})})}catch(e){}ev.currentTarget.disabled=false;refresh()}
document.getElementById('tost').onclick=async ev=>{ev.currentTarget.disabled=true;try{const r=await (await fetch('/toplanti-oturum',{method:'POST',body:JSON.stringify({islem:"terminal"})})).json();if(!r.ok)geciciDurum(r.err||L("Açılamadı"),"",6000)}catch(e){}ev.currentTarget.disabled=false;refresh()}
document.getElementById('tosa').onclick=()=>{tosAyr=!tosAyr;if(last)renderOturum(last)}
// Kapat iki adımlı (onay penceresi Mac penceresinde açılmayabilir): ilk basış "Emin misin?", 4 sn içinde ikinci basış kapatır
document.getElementById('tosk').onclick=async ev=>{const b=ev.currentTarget
  if(!b.dataset.emin){b.dataset.emin="1";b.textContent=L("Emin misin? Kapat");setTimeout(()=>{if(b.dataset.emin){b.dataset.emin="";b.textContent=L("Kapat")}},4000);return}
  b.dataset.emin="";b.disabled=true;b.textContent=L("Kapat");try{await fetch('/toplanti-oturum',{method:'POST',body:JSON.stringify({islem:"kapat"})})}catch(e){}b.disabled=false;refresh()}
// v0.112.0: Claude'un seçim sorusu ([[seç: …]]) — düğmeler panoda ve mini panoda; basınca seçim oturuma gider
function tosSecHtml(q){return `<div class=tsc>${q.secenek.map(x=>`<button class=gh data-tsec="${esc(x)}" data-ti="${q.i}">${esc(x)}</button>`).join('')}</div>`}
function tosSecBagla(d){d.addEventListener('click',async ev=>{const z=ev.target.closest('button[data-tiz]');if(z){z.closest('.tsc').querySelectorAll('button').forEach(x=>x.disabled=true);eylemKarar(z.dataset.tiz,z.dataset.d);return}
  const b=ev.target.closest('button[data-tsec]');if(!b)return;b.closest('.tsc').querySelectorAll('button').forEach(x=>x.disabled=true)
  let r={};try{r=await (await fetch('/toplanti-oturum',{method:'POST',body:JSON.stringify({islem:"sec",i:+b.dataset.ti,secim:b.dataset.tsec})})).json()}catch(e){}
  if(!r.ok){geciciDurum(r.err||L("gönderilemedi"),"",5000);b.closest('.tsc').querySelectorAll('button').forEach(x=>x.disabled=false)}refresh()})}
tosSecBagla(document)
// mini pano (ve Mac paneli): açık soru — son ileti, varsa seçenek düğmeleri; cevap mini kutudan da yazılır
function miniOturum(d,s){const e=d.getElementById("mto"),o=s.toplanti_oturum,q=o&&o.soru,mn=d.getElementById("mn");if(!e)return
  if(mn){if(q)mn.dataset.cevap=1;else delete mn.dataset.cevap;mn.placeholder=q?L("Cevabını yaz"):yazIpucu()}
  const iz=(o&&o.izinler)||[]
  if(iz.length){const sig="iz|"+iz.map(x=>x.id).join();e.hidden=false;if(e.dataset.sig===sig)return;e.dataset.sig=sig
    setH(e,`<div class=meta><b>${esc(L("{asistan} iznini bekliyor"))}</b></div>${tosIzinHtml(o)}`);return}
  if(!q){const t=tosSatir(o);e.hidden=!t;if(!t){e.dataset.sig="";return}const sig="t|"+t;if(e.dataset.sig===sig)return;e.dataset.sig=sig;setH(e,`<div class=meta>${esc(t)}</div>`);return}
  const sig=q.i+"|"+(q.secenek?1:0);e.hidden=false;if(e.dataset.sig===sig)return;e.dataset.sig=sig
  setH(e,`<div class=meta><b>${esc(L("{asistan} soruyor"))}</b></div><div class=d>${tosMd(q.metin.length>=400?"…"+q.metin:q.metin)}</div>${q.secenek?tosSecHtml(q):`<div class=meta>${esc(L("Cevabı aşağıdaki kutuya yaz."))}</div>`}`)}
// Faz D2: Deneme toplantısı penceresi — /status duman (aktarici/duman.py); koşarken canlı ✓ ✗ ? …, bitince özet. Kip toplantıya hiçbir şey yazmaz.
let DM_ID=null;const DM_SIM={ok:'✓',hata:'✗','?':'?',bekliyor:'…',atla:'—'}
function dumanCiz(s,zorla){const d=s&&s.duman,w=document.getElementById('dmd');if(!d||!w)return
  if(d.aktif&&(zorla||DM_ID!==d.t0)){DM_ID=d.t0;if(!w.open)w.showModal()}
  if(!w.open)return
  document.getElementById('dmy').textContent=d.aktif?L('Süre: {g}/{s} sn',{g:d.gecen,s:d.sure})+' · '+(d.yonerge||[]).join(' '):(d.ozet||'')
  document.getElementById('dmi').innerHTML=(d.maddeler||[]).map(x=>'<div class="dr '+esc(x.durum)+'"><b>'+(DM_SIM[x.durum]||'?')+'</b><span>'+esc(x.ad)+'<small>'+esc(x.not||'')+'</small></span></div>').join('')+(!d.aktif&&d.ozet?'<div class=dr><b></b><span><b>'+esc(d.ozet)+'</b></span></div>':'')
  const b=document.getElementById('dmb');b.textContent=d.aktif?L('Bitir'):L('Kapat');b.onclick=async()=>{if(d.aktif){try{await j('/duman',{method:'POST',body:JSON.stringify({islem:'bitir'})})}catch(e){}refresh()}else w.close()}}
{const x=document.getElementById('dmx');if(x){x.innerHTML=ic('x');x.onclick=()=>document.getElementById('dmd').close()}}
