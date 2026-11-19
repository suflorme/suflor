async function refresh(){let s;try{s=await j('/status')}catch(e){s=null}
if(s&&s.konus&&s.konus.kisilik_harita)ASM=s.konus.kisilik_harita;if(s&&s.asistan&&s.asistan!==AS){AS=s.asistan;asYaz(document)}
  if(s&&s.err==="anahtar"){document.title=L("Suflor.me — anahtar gerekli");const d=document.getElementById('durum');d.className='er';setH(document.getElementById('dm'),esc(L("Pano anahtarsız açıldı")));setH(document.getElementById('da'),esc(L("Suflor.me simgesine tıkla → Panoyu aç")));return}
  if(!s){const d=document.getElementById('durum');d.className='er';setH(document.getElementById('dm'),esc(L("Suflor.me'ye ulaşılamıyor")));setH(document.getElementById('da'),esc(L('birkaç saniye içinde yeniden denenir')));return}last=s;guncellemeCiz(s);dumanCiz(s);const x=s.extension, ag=s.agenda||{items:[]}
setH(document.getElementById('t'),s.aktif?esc(L(((ag.items||[]).length&&ag.title)||(s.toplanti||{}).ad||s.meeting||'Toplantı')):'')
setH(document.getElementById('chips'),s.aktif&&ag.rol?`<span class=chip>${ROL[ag.rol]||esc(ag.rol)}</span>`:"")
{const [t,c,ti]=sureTxt(s),e=document.getElementById('sure');setH(e,s.aktif&&t?ic('clock',esc(t)):"");e.className=c;e.title=ti}
durumCiz()
{const st=document.getElementById('st');st.textContent=!s.aktif&&s.file?L('önceki toplantınınki gizli'):(s.aktif&&s.last?L('son satır {t}',{t:String(s.last).slice(-8,-3)}):'')}
const wasBottom=atBottom
renderLines(s.tail); renderTaslak(s.taslak)
if(wasBottom)main.scrollTop=main.scrollHeight
paintCards(document.getElementById("kc"),s); paintMini(s); renderTakvim(s); renderNotlar(s); renderBrifing(s); renderKonus(s); renderHat(document,s); renderSon(s); renderKapanis(s); renderOturum(s); bnYukle(); renderEposta(s); bnVeriYukle(); bnEkYukle(); bnCiz(s)
if(s.ayarlar&&s.ayarlar.deger)temaUygula(s.ayarlar.deger.tema||'sistem');if(s.ayarlar&&s.ayarlar.deger){const h=document.documentElement;if(s.ayarlar.deger.renk_duzeni!=='notr')h.dataset.renk='yesil';else delete h.dataset.renk}  // taslak varsayılanı yeşil kenar çubuğu; yalnız açıkça 'notr' seçilince gri  // tema başka pencereden (Ayarlar) değiştiyse de
// arayüz dili başka pencereden (Ayarlar) değiştiyse bu sayfa da yeni dille yeniden yüklenir
if(s.ayarlar&&s.ayarlar.deger&&s.ayarlar.deger.dil&&s.ayarlar.deger.dil!==DIL&&!new URLSearchParams(location.search).get('dil')&&!window._dilYeni){window._dilYeni=1;location.reload()}
// Mac penceresi (html.mac, v0.106.0): toplantıda mı (araç çubuğundaki toplantı düğmeleri), toplantı dışında yan sütun boş mu (gizlenir)
sinifKur(s)
document.getElementById('sk').hidden=!s.aktif&&!shKartlar(s).length&&!(s.questions||[]).length&&!(s.claude_age_s!=null&&s.claude_age_s<120)
setH(document.getElementById("tone"),toneHtml(s.tone,s.tone_kisi))
;(s.cards||[]).forEach(c=>seenCards.add(c.id+(c.geri||""))); firstCards=false
sessizCiz(document.getElementById("sz"),s); gizliCiz(document.getElementById("gz"),s); sesliCiz(document.getElementById("sc"),s); renderEylem(s)
{const n=((s.eylem||{}).liste||[]).filter(x=>x.durum==="bekliyor"&&!x.sunuldu).length,t=[sessizTxt(s),yaparkenTxt(s),sesliTxt(s)].filter(Boolean).join(" · ");setH(document.getElementById("szd"),t+(n?(t?" · ":"")+sdi('liste',L("{n} iş toplantı sonuna",{n})):""))}
document.title=(shKartlar(s).length?`(${shKartlar(s).length}) `:"")+"Suflor.me pano"
{const fl=s.flags||[];document.getElementById('fls').hidden=!fl.length;setH(document.getElementById('fl'),fl.slice(-10).map(e=>`<div class="l f">${esc(e.time)} ${esc(e.speaker)}: ${esc(e.text)}</div>`).join(''))}
{const e=document.getElementById('py'),h=payHtml(s);setH(e,h);e.className='py'+(payUy(s)?' uy':'');e.style.display=h?'':'none'}
{const k=s.kanitlar||[];document.getElementById('kls').hidden=!k.length;setH(document.getElementById('kl'),k.slice().reverse().map(x=>`<div class=kl><a href="/${esc(x.kanit)}${kq()}" target=_blank><img src="/${esc(x.kanit)}${kq()}" alt=""></a><span>${esc(x.n)} · ${esc((x.at||'').slice(11,16))}${x.not?' — '+esc(x.not):''}</span></div>`).join(''))}
{const b=s.baglam||[],NK={baslat:L("Başlat"),kutu:L("kutu"),birak:L("bırakıldı")};document.getElementById('bgs').hidden=!b.length;setH(document.getElementById('bg'),b.map(x=>`<div class=bg title="${esc(x.ad)}">${ic(x.tur==="dosya"?"dosya":"bag")}<span>${esc(x.ad)}</span><span class=sp>${esc(NK[x.kaynak]||x.kaynak)}</span></div>`).join(''))}
{const a=s.acik||[];document.getElementById('aks').hidden=!a.length;setH(document.getElementById('ak'),a.map(q=>`<div class=ak>${esc(q.metin)}${q.kim?`<span class=sp>— ${esc(q.kim)}</span>`:''}</div>`).join(''))}
// gündem her yenilemede karşılaştırılır — Claude `gundem i` ile işaretleyince ya da agenda.json değişince görünsün
const bos=!s.aktif&&!(s.claude_age_s!=null&&s.claude_age_s<120)
if(bos&&Date.now()-agTamT>10000){agTamT=Date.now();j('/agenda').then(v=>{agTam=v}).catch(()=>{})}  // /status boşken gündemi gizler; eşleştirme için tamı
if(bos&&tkGor){const g=seciliGundem(agTam)
  const sig='sec|'+JSON.stringify([tkGor,g&&g.items,g&&g.kaynak]);if(g&&sig!==agSig){agSig=sig;agTotal=0
  document.getElementById('agn').textContent=g.o.baslik
  document.getElementById('ag').innerHTML=(g.items.length?g.items.map(it=>`<div class=agm>${esc(it)}</div>`).join(''):'')+(g.kaynak?`<div class=${g.items.length?'hint':'empty'}>${esc(g.kaynak)}</div>`:'')}}
else{const sig=JSON.stringify([ag.items,s.agenda_ticks,s.agenda_aktif]);if(sig!==agSig){agSig=sig;agTotal=ag.items.length;const tk=s.agenda_ticks||{},n=ag.items.filter((_,i)=>tk[i]).length
document.getElementById('agn').textContent=ag.items.length?`${n}/${ag.items.length}`:''
document.getElementById('ag').innerHTML=ag.items.map((it,i)=>`<label class="${s.agenda_aktif===i&&!tk[i]?'ak-on':''}" title="${s.agenda_aktif===i?L('Tahmin: şu an bu madde konuşuluyor'):''}"><input type=checkbox data-i=${i} ${tk[i]?'checked':''}><span class="${tk[i]?'done':''}">${esc(it)}</span></label>`).join('')||`<div class=empty>${L('Toplantı başlayınca gündem burada görünür.')}</div>`
document.querySelectorAll('#ag input').forEach(c=>c.onchange=()=>fetch('/agenda-tick',{method:'POST',body:JSON.stringify({i:c.dataset.i,v:c.checked,label:ag.items[c.dataset.i]})}).then(refresh))}}
}
wireBox(document.getElementById("n"));kutuBagla(document,"")
document.getElementById("oz").onclick=ev=>sendOzet(ev.currentTarget)
document.getElementById("yz").onclick=ev=>sendOnemli(ev.currentTarget)
document.getElementById("sz").onclick=ev=>sendSessiz(ev.currentTarget); document.getElementById("gz").onclick=ev=>sendGizli(ev.currentTarget)
document.getElementById("kz").onclick=ev=>sendKanit(ev.currentTarget,document.getElementById("n"))
document.getElementById("sc").onclick=ev=>sendSesliCeviri(ev.currentTarget)
function cubukAdlari(d){for(const[i,ad]of[["yz","Önemli an"],["myz","Önemli an"],["gz","Gizli toplantı"],["mgz","Gizli toplantı"],["sc","Sesli çeviri"],["msc","Sesli çeviri"]]){const b=d.getElementById(i);if(b)b.dataset.ad=L(ad)}
  d.querySelectorAll(".ib[title]").forEach(b=>{if(!b.getAttribute("aria-label"))b.setAttribute("aria-label",b.title.split(/[:—(]/)[0].trim())})
  d.querySelectorAll(".dmk").forEach(m=>m.addEventListener("click",()=>m.parentElement.removeAttribute("open")))}
cubukAdlari(document)
// v0.99.2 (sistem analizi §3.6): yenileme duruma göre — toplantı/Konuş/sohbet sürerken 2 sn, boşta 5 sn, sekme gizliyken 15 sn (mini pano açıksa 2 sn:
// onu bu sayfa çizer); görünür olunca hemen. Önceden koşulsuz 2 sn (sohbette Chrome işlemcisi). Kartlar ayrıca uzun yoklamayla anında gelir.
let sonEtkin=Date.now()  // etkinlik bittikten sonra 15 sn daha hızlı (kapanış, Geri al gibi kısa süreli durumlar kaçmasın)
function yenileAralik(){const s=last||{},k=s.konus||{},mOn=mini&&!mini.closed
  if(s.aktif||["aciliyor","calisiyor","bekliyor","izliyor"].includes((s.toplanti_oturum||{}).durum)||(k.durum&&!["kapali","hazir","hata"].includes(k.durum))||(k.sohbet||{}).acik)sonEtkin=Date.now()
  if(document.hidden&&!mOn)return 15000
  return Date.now()-sonEtkin<15000?2000:5000}
let yT=0;async function yDongu(){clearTimeout(yT);try{await refresh()}catch(e){}clearTimeout(yT);yT=setTimeout(yDongu,yenileAralik())}
document.addEventListener("visibilitychange",()=>{if(!document.hidden)yDongu()})
// sesle ya da menüden "panoyu aç": adres #bolum=<ad> (açılışta) ya da panoBolum('<ad>') (pencere zaten açıkken, menü uygulaması) → ilgili sayfaya geç, bölüme kaydır, kısa süre vurgula. Bilinmeyen ad: yalnız pano açık kalır.
const BOLUM_YOL={bugun:'bugun',kararlar:'kayit',isler:'kayit',takvim:'takvim',ekip:'ekip',gecmis:'gecmis'},BOLUM_EL={bugun:'#bgn',kararlar:'.knb',isler:'.knb',takvim:'#tvb',ekip:'#bgn',gecmis:'#bgn',sohbet:'#shp'};let bolumT=0
function panoBolum(b){b=String(b||'').toLowerCase();if(!/^[a-z]{1,12}$/.test(b)||(!BOLUM_YOL[b]&&b!=='sohbet'))return false
  if(b==='sohbet')shAc(true,false);else git(BOLUM_YOL[b])
  clearInterval(bolumT);let n=0;bolumT=setInterval(()=>{const e=document.querySelector(BOLUM_EL[b]);if(e&&!e.hidden&&e.offsetParent!==null){clearInterval(bolumT);e.scrollIntoView({block:'start',behavior:'smooth'});e.classList.remove('yeni');void e.offsetWidth;e.classList.add('yeni');setTimeout(()=>e.classList.remove('yeni'),2600)}else if(++n>12)clearInterval(bolumT)},300);return true}
function bolumHash(){const m=/^#bolum=([a-z]+)$/.exec(location.hash||'');if(!m)return;try{history.replaceState(null,'',location.pathname+location.search)}catch(e){}panoBolum(m[1])}
window.addEventListener('hashchange',bolumHash)
bolumHash()
yDongu()
// menü çubuğu uygulamasının paneli (?gorunum=panel): aynı kökenli bir iframe'de ayrı belge;
// pano gizli kalır ama yenilemeyi o yapar. Zemin saydam: panelin buzlu cam (vibrancy) zemini görünür.
if(new URLSearchParams(location.search).get('gorunum')==='panel'){document.documentElement.classList.add('panel');const f=document.createElement('iframe');f.id='panelf';f.title='Suflor.me';document.body.appendChild(f)
  buildMini(f.contentWindow);const st=f.contentDocument.createElement('style');st.textContent='html,body{background:transparent!important}';f.contentDocument.head.appendChild(st)}
// kart/✓/soru/kanıt isteği değişince pano ve mini pano hemen yenilenir (aktarıcıda uzun yoklama, şeritle aynı imza);
// 2 sn yenileme diğer alanlar için sürer. Eski aktarıcıda (imza yok) döngü kapanır.
let kImza="";(async function kartBekle(){for(;;){try{const v=await (await fetch('/cards?bekle=25&imza='+encodeURIComponent(kImza),{signal:AbortSignal.timeout(35000)})).json()
if(!v.imza)return;if(v.imza!==kImza){const ilk=!kImza;kImza=v.imza;if(!ilk)refresh().catch(()=>{})}}catch(e){await new Promise(r=>setTimeout(r,3000))}}})()
