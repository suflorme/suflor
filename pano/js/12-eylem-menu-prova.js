// ---- Eylem menüsü (ortak karar katmanı, yerel; 5 Kasım): her kayıtta ⋯ → ertele · böl · gündeme ekle · ata · e-posta/Teams taslağı · {asistan}'a sor (sohbet paneli) · onayla/reddet · tarihçe · Geri al.
// Aktarıcı: GET /kayit-menu?id= (menü bilgisi), POST /kayit-eylem {id, eylem, …} (aktarici/eylem-menu.py; her eylem bir olay). Taslaklar yalnız açılır, hiçbir şey gönderilmez; gizli toplantı kaydında eylem yok.
let emKid='',emV=null,emMod='',emMsj='',emYuk=false,emHedef='dlg'
{document.body.insertAdjacentHTML('beforeend',`<dialog id=emd aria-label="${L('Eylemler')}"><div class=emb><div><div class=eb id=emt></div><h2 id=emh></h2></div><button type=button class=ikon id=emx aria-label="${L('Kapat')}">${ic('x')}</button></div><div id=emg class=emk></div></dialog>`)}
const EML={onayla:L('Onayla'),reddet:L('Reddet'),yapildi:L('Yapıldı'),iptal:L('İptal et'),ac:L('Yeniden aç'),cevaplandi:L('Cevaplandı'),ertele:L('Ertele'),gundem:L('Gündeme ekle'),ata:L('Ata'),eposta:L('E-posta taslağı'),teams:L('Teams taslağı'),toplanti:L('Acil toplantı'),get marvin(){return L('{ad} sor',{ad:DIL==='en'?asGor(last&&last.konus):yonelme(asGor(last&&last.konus))})},tarihce:L('Tarihçe'),geri_al:L('Geri al')}
const EMI={onayla:'check',reddet:'x',yapildi:'check',iptal:'engel',ac:'yenile',cevaplandi:'check',ertele:'clock',gundem:'liste',ata:'kisi',eposta:'posta',teams:'sohbet',toplanti:'takvim',marvin:'panel',tarihce:'hist',geri_al:'geri'}
const EMA={eposta:L('Yalnız taslak açılır; göndermek sende'),teams:L('Yalnız taslak açılır; göndermek sende'),toplanti:L('İlgili kişilerle hemen toplantı; davet göndermek sende'),marvin:L('Kayıt bağlamıyla sohbet panelinde konuşursun; özet, yapılacaklar, taslak mesaj. Dışarı bir şey gitmez'),gundem:L('Sıradaki uygun toplantının gündemine girer'),}
const EMT={onayla:L('Karar onaylandı'),reddet:L('Karar reddedildi'),yapildi:L('Yapıldı olarak işaretlendi'),iptal:L('İptal edildi'),ac:L('Yeniden açıldı'),cevaplandi:L('Cevaplandı olarak işaretlendi'),ertele:L('Vade değişti'),ata:L('Atandı'),eposta:L('E-posta taslağı açıldı; göndermek sende'),teams:L('Teams taslağı açıldı; göndermek sende'),toplanti:L('Toplantı ekranı açıldı; davet göndermek sende'),geri_al:L('Son değişiklik geri alındı')}
// Eylemler: durum eylemleri ve Ertele/Ata üstte düğme; gerisi üç başlıkta — Planla · İlet · Diğer (İptal et gecikme renginde)
const EMU=['yapildi','onayla','cevaplandi','reddet','ac','ertele','ata'],EMB=[['Planla',['ertele','ata','gundem']],['İlet',['marvin','eposta','teams','toplanti']],['Diğer',['tarihce','geri_al','iptal']]]
const emGun=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
// onay süresi göstergesi (3. gün hatırlatma, 7. gün ya da sonraki dizi toplantısında "onaylanmadı"): ince nokta + kısa metin
const emOnayIs=o=>!o?'':o.durum==='onaylanmadi'?`<span class="etiket gec onayis son" title="${esc(o.neden||'')}">${L('Onaylanmadı')}</span>`:o.hatirlat?`<span class="etiket bekliyor onayis" title="${L('Toplantıdan beri {n} gün geçti',{n:o.gun})}">${L('{n}. gün: onay bekliyor',{n:o.gun})}</span>`:''
// sunucu hata metinleri (Türkçe, kısa) → arayüz dili; bilinmeyen tek sözcük (istisna sınıfı adı) anlaşılır "Yapılamadı."ya döner
const EMER={'vade yok':L('Vade seç.'),'yalnız iş ertelenir':L('Yalnız iş ertelenir.'),'toplantı yok':L('Takvimde sıradaki uygun toplantı yok.'),'toplantı bulunamadı':L('Seçilen toplantı takvimde bulunamadı.'),'kişi yok':L('Kişi adı yaz.'),'kayıt yok':L('Kayıt bulunamadı.'),
  'bu iş senin; kendine taslak yazılmaz':L('Bu iş senin; kendine taslak yazılmaz.'),'not metni yok':L('Not metni boş.'),'olay bu kayda ait değil':L('Yapılamadı.')}
const emHata=e=>{e=String(e||'');return EMER[e]||(/\s/.test(e)?L(e):L('Yapılamadı.'))}
const emTur=k=>['ertele','gundem','ata','toplanti','tarihce'].includes(k)?'mod':'run'
const emBtn=k=>{const ps=k==='teams'&&emV&&emV.pasif&&emV.pasif.teams;return`<button type=button class="emi${k==='iptal'?' gec':''}" data-em=${emTur(k)} data-e=${k}${emYuk?' disabled':''}${EMA[k]?` title="${esc(EMA[k])}"`:''}>${ic(EMI[k])}<span>${esc(EML[k])}${ps?`<small>${esc(L(ps))}</small>`:''}</span></button>`}
const emUst=(k,ana)=>`<button type=button class="emi emust b${ana?' ana':''}" data-em=${emTur(k)} data-e=${k}${emYuk?' disabled':''}${EMA[k]?` title="${esc(EMA[k])}"`:''}>${esc(EML[k])}</button>`
function emIcerik(){const v=emV;let h=''
  if(!v)h=`<p class=emsoluk>${L('Yükleniyor…')}</p>`
  else if(!v.ok)h=`<p class=emhata>${v.err==='gizli'?L('Gizli toplantının kaydı: eylem yapılmaz.'):L('Kayıt bulunamadı.')}</p>`
  else if(!emMod){const el=v.eylemler||[],ust=EMU.filter(k=>el.includes(k)),kul=new Set(ust)
    h=(ust.length?`<div class=emustd>${ust.map((k,i)=>emUst(k,i===0&&['yapildi','onayla','cevaplandi'].includes(k))).join('')}</div>`:'')
      +EMB.map(([b,ks])=>{const l=ks.filter(k=>el.includes(k)&&!kul.has(k));return l.length?`<div class=embl><div class=emba>${esc(L(b))}</div><div class=emgr>${l.map(emBtn).join('')}</div></div>`:''}).join('')
      +(v.geri_al?`<p class=emalt>${L('Geri al')}: ${esc(v.geri_al.ozet)}</p>`:'')}
  else h=`<button type=button class="b sade" data-em=geri>← ${L('Eylemler')}</button>`+emForm(v)
  return(emMsj?`<p class="emms${emYuk?' bekle':''}" role=status>${esc(emMsj)}</p>`:'')+h}
function emKayit(){return knKayit(emKid)||(emV&&emV.kayit)||null}
function emCiz(){if(emHedef==='yan'){if(bnRef==='r:'+emKid&&last)bnPanelCiz(last,true);return}
  const g=bnE('emg'),x=emKayit()||{}
  bnE('emt').textContent=x.tur==='karar'?L('Karar'):x.tur==='soru'?L('Açık soru'):L('İş');bnE('emh').textContent=String(x.metin||'')
  g.innerHTML=emIcerik()}
function emForm(v){
  if(emMod==='ertele'){const ev=/^\d{4}-\d{2}-\d{2}$/.test(v.kayit.vade||'')?v.kayit.vade:emGun(1)
    return`<label class=emal>${L('Yeni vade')}<input type=date id=emVade value="${ev}"></label><div class=keylem><button type=button class="b sade" data-em=gun data-n=1>${L('Yarın')}</button><button type=button class="b sade" data-em=gun data-n=7>${L('Haftaya')}</button><button type=button class="b sade" data-em=gun data-n=30>${L('Ay sonuna doğru (30 gün)')}</button><button type=button class="b ana" data-em=yap data-e=ertele>${L('Ertele')}</button></div>`}
  if(emMod==='gundem'){const l=v.gundem||[]
    return l.length?`<div class=emal>${L('Hangi toplantının gündemine?')}</div><div class=emsec>${l.map((a,i)=>`<label><input type=radio name=emG value="${esc(a.id)}"${i?'':' checked'}><span>${esc(a.tarih+' '+a.saat)} · ${esc(a.baslik||L('(başlıksız)'))}${a.ilgili?` <small>${L('ilgili kişi katılıyor')}</small>`:''}</span></label>`).join('')}</div><div class=keylem><button type=button class="b ana" data-em=yap data-e=gundem>${L('Gündeme ekle')}</button></div>`
      :`<p class=emsoluk>${L('Takvimde sıradaki uygun toplantı yok.')}</p>`}
  if(emMod==='ata'){const s=v.sahip||{},kl=(((knV||{}).kisiler)||[])
    return`<label class=emal>${L('Kim')}<input type=text id=emKisi list=emKisiL maxlength=80 autocomplete=off value="${esc(s.ad||'')}"></label><datalist id=emKisiL>${kl.map(k=>`<option value="${esc(k)}">`).join('')}</datalist>
      <div id=emKim class=emkim>${emKimHtml(s)}</div><label class=emal>${L('E-posta adresi')}<input type=text id=emEp maxlength=120 autocomplete=off value="${esc(s.eposta||'')}"></label>
      <div class=keylem><button type=button class="b ana" data-em=yap data-e=ata>${L('Ata')}</button><button type=button class=b data-em=yap data-e=atamail>${L('Ata ve e-posta taslağı')}</button></div><p class=emalt>${L('Kişi Suflor kullanmıyorsa e-posta taslağıyla haber ver; göndermek sende.')}</p>`}
  if(emMod==='toplanti'){const t=v.toplanti||{},pl=t.platformlar||[],PA={teams:'Microsoft Teams',meet:'Google Meet',zoom:'Zoom'},dv=t.davetli||[],yok=t.eposta_yok||[]
    return`<div class=emal>${L('Hangi platformda?')}</div><div class=emgr>${pl.map((k,i)=>`<button type=button class=emi data-em=yap data-e=toplanti data-p="${esc(k)}"${emYuk?' disabled':''}>${ic('takvim')}<span>${esc(PA[k]||k)}${i?'':`<small>${L('Varsayılan')}</small>`}</span></button>`).join('')}</div>
      <p class=emalt>${dv.length?L('Davetliler: {k}',{k:dv.map(d=>d.ad||d.eposta).join(', ')}):L('E-postası bilinen davetli yok; toplantı kişisiz açılır.')}</p>${yok.length?`<p class=emalt>${L('E-postası bilinmiyor, davete eklenmez: {k}',{k:yok.join(', ')})}</p>`:''}
      <p class=emalt>${t.platformlar&&pl.includes('zoom')&&!t.zoom_baglanti?L('Zoom: kişisel bağlantı ayarda yok; Zoom açılır, davet metni panoya kopyalanır.'):L('Yalnız toplantı ekranı açılır; göndermek sende.')}</p>`}
  if(emMod==='tarihce'){const l=[...(v.tarihce||[])].reverse()
    return`<ul class=emtar>${l.map(o=>`<li><span>${esc(o.ozet)}</span>${o.metin?`<pre class=emnot>${esc(o.metin)}</pre>`:''}</li>`).join('')}</ul><p class="emalt emkid">${esc(L('Kayıt kimliği: {k}',{k:emKid}))}</p>`}
  return''}
function emKimHtml(k){if(!k||!k.ad&&!k.eposta&&!(k.adaylar||[]).length)return`<small>${L('Ad yazınca e-posta adresi bulunur.')}</small>`
  if(k.eposta)return`<small>${esc(k.eposta)}${k.kaynak?' · '+esc({takvim:L('takvim'),kisiler:L('Kişiler'),vt:L('kayıt veritabanı'),elle:L('elle'),ayar:L('ayar'),ad_icinde:L('adın içinde'),eposta_yerel:L('adresten tahmin')}[k.kaynak]||k.kaynak):''}</small>`
  return(k.adaylar||[]).length?`<small>${L('Birden çok aday var; birini seç:')}</small> ${k.adaylar.map(a=>`<button type=button class="b sade" data-em=aday data-ep="${esc(a)}">${esc(a)}</button>`).join('')}`:`<small>${L('E-posta bulunamadı; elle yazabilirsin.')}</small>`}
async function emAc(kid,hedef,mod){if(!kid)return;emHedef=hedef||'dlg';emKid=kid;emV=null;emMod='';emMsj='';emYuk=false;if(emHedef==='dlg'){const d=bnE('emd');if(!d.open)d.showModal()}emCiz()
  let v={ok:false,err:'kayıt yok'};try{v=await j('/kayit-menu?id='+encodeURIComponent(kid))}catch(e){}
  if(emKid===kid){emV=v;if(mod&&v&&v.ok&&(v.eylemler||[]).includes(mod))emMod=mod;emCiz()}}
const emYenile=()=>{bnVeriYukle(true);if(bnGor==='kayit')knYukle(true)}
function emTaslakAc(t){if(!t)return
  if(t.tur==='teams'){const a=document.createElement('a');a.href=t.teams;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();return}
  const p=postaUrl({md:t.govde,baslik:t.konu,alicilar:t.alicilar||[]},(t.alicilar||[]).length?'k':'');if(p.kisa)try{navigator.clipboard.writeText(p.duz)}catch(e){};brAc(p.u,p.yeni)}
async function emRun(e,p){if(emYuk)return{ok:false};emYuk=true;emMsj='';emCiz()
  let r={};try{r=await bnYaz('/kayit-eylem',Object.assign({id:emKid,eylem:e},p||{}))}catch(x){r={ok:false,err:'ağ'}}
  emYuk=false
  if(!r.ok){emMsj=r.err==='gizli'?L('Gizli toplantının kaydı: eylem yapılmaz.'):r.err==='ağ'?L('Aktarıcıya ulaşılamadı.'):emHata(r.err);emCiz();return r}
  emMsj=e==='gundem'&&r.toplanti?L('Gündeme eklendi: {t}',{t:r.toplanti.baslik||''}):r.olay===null&&e!=='geri_al'?L('Zaten böyle; değişiklik yok.'):(EMT[e]||'')+(r.alici_yok?' — '+L('alıcı adresi bulunamadı, taslak alıcısız açıldı'):'')
  if(r.taslak)emTaslakAc(r.taslak)
  if(e==='toplanti'&&r.toplanti&&r.toplanti.url){const t=r.toplanti;if(t.kopyala)try{navigator.clipboard.writeText(t.kopyala)}catch(x){};brAc(t.url,true)
    emMsj=(t.kopyala?L('Zoom açıldı; davet metni panoya kopyalandı. Göndermek sende.'):EMT.toplanti)+((t.eposta_yok||[]).length?' — '+L('E-postası bilinmiyor, davete eklenmedi: {k}',{k:t.eposta_yok.join(', ')}):'')}
  try{emV=await j('/kayit-menu?id='+encodeURIComponent(emKid))}catch(x){}
  emMod=['ertele','gundem','ata','toplanti'].includes(emMod)?'':emMod;emCiz();emYenile();return r}
// {asistan}'a sor: kayıt menüsü kapanır, sohbet paneli açılır, kayıt bağlamıyla (aktarıcı kurar) konuşma başlar; soru panelde kısa görünür, cevap aynı konuşmada sürer ("taslağı kısalt" …). Cevabın altında «Kayda not olarak ekle».
async function emMarvin(){const kid=emKid,x=emKayit()||{};if(!kid||emYuk)return
  const m=String(x.metin||'').replace(/\s+/g,' ').trim(),t=L('«{k}» kaydına bak: özet, en çok 3 yapılacak ve sahibine kısa taslak mesaj',{k:m.length>140?m.slice(0,139)+'…':m})
  if(emHedef==='yan')bnPanelKapat();else{const d=bnE('emd');if(d.open)d.close()}
  const pn=shGonder(t);let r={};try{r=await (await fetch('/girdi',{method:'POST',body:JSON.stringify({text:t,kayit:kid,at:new Date().toISOString()})})).json()}catch(e){r={}}
  const ok=r.tur==='asistan'&&!!r.ok;shGonderSonuc(pn,t,ok)
  if(ok){pn.kayit=kid;if(last)renderKonus(last)}
  else bnBildir(r.err==='gizli'?L('Gizli toplantının kaydı: eylem yapılmaz.'):/hâlâ cevaplıyor/.test(String(r.err||''))?L('{ad} hâlâ cevaplıyor; bitince yeniden dene.',{ad:asGor(last&&last.konus)}):L('Yapılamadı.'))
  refresh()}
async function emKimBul(){const ad=(bnE('emKisi')||{}).value||'';if(ad.trim().length<2)return;let k={};try{k=await j('/kimlik?ad='+encodeURIComponent(ad.trim()))}catch(e){}
  const el=bnE('emKim'),ep=bnE('emEp');if(!el||(bnE('emKisi').value||'')!==ad)return;el.innerHTML=emKimHtml(Object.assign({ad},k));if(ep&&k.eposta)ep.value=k.eposta}
async function emTik(ev){const b=ev.target.closest('[data-em]');if(!b||b.disabled)return;const a=b.dataset.em,e=b.dataset.e
  if(a==='run')return e==='marvin'?emMarvin():emRun(e)
  if(a==='mod'){emMod=e;emMsj='';emCiz();return}
  if(a==='geri'){emMod='';emMsj='';emCiz();return}
  if(a==='gun'){const i=bnE('emVade');if(i)i.value=emGun(+b.dataset.n);return}
  if(a==='aday'){const i=bnE('emEp');if(i)i.value=b.dataset.ep;return}
  if(a==='yap'){
    if(e==='ertele')return emRun('ertele',{vade:(bnE('emVade')||{}).value||''})
    if(e==='toplanti')return emRun('toplanti',{platform:b.dataset.p||''})
    if(e==='gundem'){const r=document.querySelector('input[name=emG]:checked');return emRun('gundem',{etkinlik:r?r.value:''})}
    if(e==='ata'||e==='atamail'){const ad=(bnE('emKisi')||{}).value||'',ep=((bnE('emEp')||{}).value||'').trim();if(!ad.trim()&&!ep){emMsj=L('Kişi adı yaz.');emCiz();return}
      const r=await emRun('ata',{sahip:ad,eposta:ep});if(e==='atamail'&&r.ok)return emRun('eposta',{alicilar:(r.eposta||ep)?[r.eposta||ep]:[],alici_ad:ad})}}}
{const d=bnE('emd');d.addEventListener('click',ev=>{if(ev.target===d){d.close();return}emTik(ev)});bnE('emx').addEventListener('click',()=>d.close());d.addEventListener('close',()=>{if(d.open||emHedef!=='dlg')return  // close olayı eş zamansız gelir: araya yeni açılış (showModal ya da yan panel) girdiyse onun durumunu silme
  emKid='';emV=null;emMod='';if(bnRef&&bnRef.startsWith('r:'))emAc(bnRef.slice(2),'yan')})
 d.addEventListener('change',ev=>{if(ev.target.id==='emKisi')emKimBul()})
 const p=bnE('bnPanel');p.addEventListener('click',ev=>{if(ev.target.closest('[data-em]'))emTik(ev)});p.addEventListener('change',ev=>{if(ev.target.id==='emKisi')emKimBul()})}
// «İş olarak ekle» penceresi (arIsAc/arIsYaz Araştırmalar bölümünde): bnE tanımlandıktan sonra kurulur
{document.body.insertAdjacentHTML('beforeend',`<dialog id=aid aria-label="${L('İş olarak ekle')}"><div class=emb><div><div class=eb>${L('Araştırma')}</div><h2 id=aih></h2></div><button type=button class=ikon id=aix aria-label="${L('Kapat')}">${ic('x')}</button></div><div class=emk><label class=emal>${L('İş')}<input type=text id=aim maxlength=300 autocomplete=off></label><label class=emal>${L('Son tarih (isteğe bağlı)')}<input type=date id=ait></label><div class=keylem><button type=button class="b ana" id=aie>${L('Ekle')}</button></div><p class=emalt id=aih2 hidden></p></div></dialog>`)
 const d=bnE('aid');d.addEventListener('click',ev=>{if(ev.target===d)d.close()});bnE('aix').addEventListener('click',()=>d.close())
 bnE('aim').addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();arIsYaz()}});bnE('aie').addEventListener('click',arIsYaz)}

// ---- Prova odası: bir karar ya da sunumu karşı taraf kişilikleriyle sına (aktarıcıda aktarici/prova.py; /prova) ----
{document.body.insertAdjacentHTML('beforeend',`<dialog id=prd aria-label="${L('Prova odası')}"><div class=prb><div><div class=eb>${L('Prova odası')}</div><h2 id=prh></h2></div><span class=prnokta id=prn aria-hidden=true></span><button type=button class=ikon id=prx aria-label="${L('Kapat')}">${ic('x')}</button></div><div id=prg></div></dialog>`)}
const prKapat=()=>{clearTimeout(prT);const d=bnE('prd');if(d.open)d.close()}
function prKisiler(izin){const ks=prD.durum==='yok'?prKisi:(prD.kisiler||[]);const sil=izin&&ks.length>3
  return`<div class=prk><div class=eb>${L('Karşı taraf')}</div><div class=prkl>${ks.map(k=>`<span class=prkc title="${esc(k.odak||'')}">${esc(k.ad)}${sil?`<button type=button data-pr=cikar data-ad="${esc(k.ad)}" aria-label="${L('Çıkar')}">×</button>`:''}</span>`).join('')||`<span class=prsoluk>${L('Boş bırakırsan konuya göre 3–5 kişilik önerilir.')}</span>`}</div>
    ${izin&&ks.length<5?`<div class=prkekle><input id=prke type=text maxlength=80 placeholder="${L('Kişilik ekle (ör. CFO — maliyet)')}" aria-label="${L('Kişilik ekle')}"><button type=button class="b sade" data-pr=ekle>${L('Ekle')}</button>${prD.durum==='yok'?`<button type=button class="b sade" data-pr=oner>${L('Öner')}</button>`:''}</div>`:''}</div>`}
function prRapor(r){const T={veri:L('Veri'),belge:L('Belge'),cumle:L('Cümle')}
  return`<div class=prpuan><span class=prp>${r.puan}<small>/100</small></span><div><div class=eb>${L('Hazır mısın')}</div><p>${esc(r.puan_gerekce||'')}</p></div></div>${r.genel?`<p class=prgenel>${esc(r.genel)}</p>`:''}
  <div class=prb2><h4>${L('En zayıf 3 nokta')}</h4><ol>${(r.zayif||[]).map(x=>`<li><b>${esc(x.nokta)}</b>${x.neden?`<span>${esc(x.neden)}</span>`:''}</li>`).join('')}</ol></div>
  <div class=prb2><h4>${L('Cevabı ikna etmeyen itirazlar')}</h4>${(r.ikna_etmeyen||[]).length?`<ul>${r.ikna_etmeyen.map(x=>`<li><b>${esc(x.kisi)}</b><span>${esc(x.soru)}${x.neden?' — '+esc(x.neden):''}</span></li>`).join('')}</ul>`:`<p class=prsoluk>${L('Yok.')}</p>`}</div>
  <div class=prb2><h4>${L('Önerilen hazırlık')}</h4><ul>${(r.hazirlik||[]).map(x=>`<li><b>${esc(T[x.tur]||x.tur)}</b><span>${esc(x.oneri)}</span></li>`).join('')}</ul></div>
  <div class=keylem><button type=button class="b ana" data-pr=kopyala>${ic('kopya')}<span>${L('Raporu kopyala')}</span></button><button type=button class=b data-pr=indir>${L('.md olarak indir')}</button><button type=button class="b sade" data-pr=sifirla>${L('Yeni prova')}</button></div>`}
function prCiz(){const d=bnE('prd');if(!d)return;const g=bnE('prg'),du=prD.durum,mesgul=prBusy||du==='dusunuyor';let h=''
  bnE('prh').textContent=du==='yok'?L('Neyi sınayalım?'):(prD.konu||L('Prova'));bnE('prn').className='prnokta'+(mesgul?' dusunuyor':'')
  if(mesgul)h=`<div class=prduz><span class=prnokta2></span><span>${L('Düşünüyor…')}</span></div><p class=prsoluk>${L('Soru ya da rapor hazırlanıyor; bu bir dakika sürebilir.')}</p>`
  else if(du==='yok')h=`<div class=prf><label><span class=eb>${L('Konu')}</span><textarea id=prkonu rows=2 maxlength=2000 placeholder="${L('Sınanacak karar, öneri ya da sunum')}">${esc(prForm.konu)}</textarea></label>
      <label><span class=eb>${L('Bağlam (isteğe bağlı)')}</span><textarea id=prbag rows=4 maxlength=8000 placeholder="${L('Sunum metni, rakamlar, gerekçe')}">${esc(prForm.baglam)}</textarea></label>
      <label><span class=eb>${L('Belge yolu (isteğe bağlı)')}</span><input id=prbel type=text value="${esc(prForm.belge)}" placeholder="~/Documents/oneri.md" autocomplete=off></label>${prKisiler(true)}
      <p class=prsoluk>${L('Konu ve bağlam yalnız asistanın yapay zekâ servisine gider.')}</p>
      <div class=keylem><button type=button class="b ana iri" data-pr=baslat>${L('Provayı başlat')}</button><button type=button class="b sade iri" data-pr=kapat>${L('Kapat')}</button></div></div>`
  else if(du==='bekliyor'){const sn=prD.siradaki||{},gec=(prD.gecmis||[]).filter(x=>x.cevap!==null&&x.cevap!==undefined),cevapli=gec.length>0
    h=`<div class=prilerle><span class="eb mono">${L('Soru {n}/{m}',{n:prD.soru_no||1,m:prD.soru_toplam||'?'})}</span></div><div class=prsoru><div class=eb>${esc(sn.kisi||'')}</div><p class=prs>${esc(sn.soru||'')}</p></div>
      <textarea id=prcev rows=5 maxlength=4000 placeholder="${L('Cevabın')}" aria-label="${L('Cevabın')}"></textarea>
      <div class=keylem><button type=button class="b ana" data-pr=cevap>${L('Yanıtla')}</button><button type=button class=b data-pr=atla>${L('Atla')}</button><button type=button class="b sade" data-pr=bitir ${cevapli?'':'disabled'}>${L('Bitir ve rapor al')}</button></div>
      ${gec.length?`<details class=prgec><summary>${L('Önceki sorular')} (${gec.length})</summary>${gec.map(x=>`<div class=prgi><b>${esc(x.kisi)}</b> ${esc(x.soru)}<div class=prcv>${esc(x.cevap||L('(atlandı)'))}</div></div>`).join('')}</details>`:''}${prKisiler(true)}`}
  else if(du==='tamam')h=`<p class=prgenel>${L('Sorular bitti. Raporu alabilir ya da yeni bir kişilik ekleyip devam edebilirsin.')}</p><div class=keylem><button type=button class="b ana iri" data-pr=bitir>${L('Rapor al')}</button></div>${prKisiler(true)}`
  else if(du==='hata')h=`<p class=prgenel>${L('Soru hazırlanamadı.')}</p><div class=keylem><button type=button class="b ana" data-pr=yeniden>${L('Yeniden dene')}</button>${(prD.gecmis||[]).some(x=>x.cevap!==null&&x.cevap!==undefined)?`<button type=button class=b data-pr=bitir>${L('Bitir ve rapor al')}</button>`:''}<button type=button class="b sade" data-pr=sifirla>${L('Vazgeç')}</button></div>`
  else if(du==='bitti')h=prRapor(prD.rapor||{})
  const hata=prHata||(du==='hata'?prD.hata:'');if(hata)h+=`<p class=prhata role=alert>${esc(hata)}</p>`
  if(g.__h!==h){const kk=g.querySelector('#prcev'),kv=kk?kk.value:'',ke=g.querySelector('#prke'),ev=ke?ke.value:'';g.innerHTML=h;g.__h=h;const k2=g.querySelector('#prcev');if(k2&&kv)k2.value=kv;const e2=g.querySelector('#prke');if(e2&&ev)e2.value=ev}}
function prFormOku(){const g=bnE('prg'),k=g.querySelector('#prkonu');if(k){prForm.konu=k.value;prForm.baglam=g.querySelector('#prbag').value;prForm.belge=g.querySelector('#prbel').value}}
async function prCagir(govde){prFormOku();prBusy=true;prHata='';prCiz();if(last)bnCiz(last);let r={}
  try{r=await bnYaz('/prova',govde)}catch(e){r={hata:L('Aktarıcıya ulaşılamadı')}}
  prBusy=false;if(r&&r.durum){prD=r;prHata=r.hata||''}else if(r&&r.kisiler){prKisi=r.kisiler}else if(r&&r.hata)prHata=r.hata
  prCiz();if(last)bnCiz(last);prYokla();return r}
async function prYokla(){clearTimeout(prT);if(prBusy||!bnE('prd').open)return
  if(prD.durum==='dusunuyor')prT=setTimeout(async()=>{try{const v=await j('/prova');if(v&&v.durum)prD=v}catch(e){}prCiz();if(last)bnCiz(last);prYokla()},2000)}
async function provaAc(konu){const d=bnE('prd');try{const v=await j('/prova');if(v&&v.durum)prD=v}catch(e){}
  if(konu&&(prD.durum==='yok'))prForm.konu=konu
  prHata='';prCiz();if(!d.open)d.showModal();const k=bnE('prg').querySelector('#prkonu')||bnE('prg').querySelector('#prcev');if(k)k.focus();prYokla()}
bnE('prd').addEventListener('close',()=>{clearTimeout(prT)})
bnE('prx').addEventListener('click',prKapat)
bnE('prg').addEventListener('click',async ev=>{const b=ev.target.closest('[data-pr]');if(!b)return;const a=b.dataset.pr,g=bnE('prg')
  if(a==='kapat')return prKapat()
  if(a==='baslat'){prFormOku();const bel=prForm.belge.trim();return prCagir({islem:'baslat',konu:prForm.konu,baglam:prForm.baglam,belge:bel||undefined,kisiler:prKisi.length?prKisi:undefined})}
  if(a==='oner'){prFormOku();return prCagir({islem:'oner',konu:prForm.konu||prForm.baglam.slice(0,300),baglam:prForm.baglam,n:4})}
  if(a==='ekle'||a==='cikar'){const ad=a==='cikar'?b.dataset.ad:(g.querySelector('#prke')||{}).value||'';if(!ad.trim())return
    if(prD.durum==='yok'){prFormOku();if(a==='cikar')prKisi=prKisi.filter(k=>k.ad!==ad);else{const m=ad.split(/\s*(?:—|–| - |:)\s*/,2);if(prKisi.length<5&&!prKisi.some(k=>k.ad.toLowerCase()===m[0].trim().toLowerCase()))prKisi.push({ad:m[0].trim(),odak:(m[1]||'').trim()})}prCiz();return}
    const m=a==='ekle'?ad.split(/\s*(?:—|–| - |:)\s*/,2):[ad];return prCagir({islem:'kisi',kisi_islem:a,ad:m[0].trim(),odak:(m[1]||'').trim()})}
  if(a==='cevap'){const t=(g.querySelector('#prcev')||{}).value||'';if(!t.trim()){prHata=L('Cevap boş');prCiz();return}return prCagir({islem:'cevap',metin:t})}
  if(a==='atla')return prCagir({islem:'atla'})
  if(a==='bitir')return prCagir({islem:'bitir'})
  if(a==='yeniden')return prCagir({islem:'yeniden'})
  if(a==='sifirla'){prKisi=[];prForm={konu:'',baglam:'',belge:''};return prCagir({islem:'sifirla'})}
  if(a==='kopyala'){try{await navigator.clipboard.writeText(prD.rapor_md||'');b.querySelector('span').textContent=L('Kopyalandı')}catch(e){prHata=L('Kopyalanamadı');prCiz()}return}
  if(a==='indir'){const u=URL.createObjectURL(new Blob([prD.rapor_md||''],{type:'text/markdown;charset=utf-8'})),x=document.createElement('a');x.href=u;x.download='prova-raporu.md';document.body.appendChild(x);x.click();x.remove();setTimeout(()=>URL.revokeObjectURL(u),2000)}})

