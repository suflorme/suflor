// 3 Kasım (ardışık toplantı): toplantı sürerken farklı konuyla Başlat → aktarıcı {soru:"suruyor"} döner; pano sorar: bitirip yenisi mi, bu toplantıya devam mı
function yeniSor(r){return new Promise(res=>{const d=document.getElementById('ybd');let v=false;const bitir=()=>{d.removeEventListener('close',bitir);res(v)}
  document.getElementById('ybb').textContent=L('Şu an «{a}» sürüyor',{a:r.ad||L('bir toplantı')});document.getElementById('ybh').textContent=L('Bitirip «{k}» toplantısını başlatayım mı? Bitenin özeti arka planda hazırlanır.',{k:r.konu||''})
  const e=document.getElementById('ybe'),v_=document.getElementById('ybv');e.textContent=L('Bitir ve başlat');v_.textContent=L('Bu toplantıya devam')
  e.onclick=()=>{v=true;d.close()};v_.onclick=()=>d.close();d.addEventListener('close',bitir);d.showModal()})}
async function baslatIstek(g){let r=await j('/baslat',{method:'POST',body:JSON.stringify(g)})
  if(r&&r.soru==='suruyor'){if(!(await yeniSor(r)))return{devam:true};r=await j('/baslat',{method:'POST',body:JSON.stringify(Object.assign({},g,{onay:'bitir'}))})}
  refresh().catch(()=>{});return r||{}}
// ardışık toplantı: biten toplantının hemen ardından takvimdeki "Sıradaki · Başlat" tek tıkla başlatır (bağlantı takvimde; rol ve dil aktarıcıda varsayılan)
async function hizliBaslat(o,b){b.disabled=true;let r={};try{r=await baslatIstek({olay:o.id,konu:o.baslik||''})}catch(e){r={err:L("Suflor.me'ye ulaşılamadı")}}
  b.disabled=false;if(r.devam)return;if(r.ok&&r.baglanti)chromeAc({baslatma:true})
  geciciDurum(r.ok?L(r.baglanti?"Başladı — toplantı açılıyor":"Başladı — toplantıya kendin katıl"):L('başlatılamadı'),r.ok?(o.baslik||''):(r.err||''),r.ok?4000:8000)}
// bitiyor/bitti: son toplantı tek satır (ad · durum · özet) + Döküm — engellemez; toplantı ekranı canlı toplantıya ayrılır
function sonCiz(s,top){const e=document.getElementById('tson'),v=(s.toplanti||{}).son;e.hidden=top||!v;if(e.hidden){e.dataset.sig='';return}
  const sig=JSON.stringify(v);if(e.dataset.sig===sig)return;e.dataset.sig=sig
  const d=v.durum==='bitiyor'?L('Toplantı bitiyor'):L('bitti {t}',{t:v.bitti||''}),oz=v.durum==='bitiyor'?'':v.ozet?L('özet hazır'):L('özet hazırlanıyor')
  setH(e,`<span class=t><b>${esc(v.ad||'')}</b> · ${esc(d)}${oz?' · '+esc(oz):''}</span><button class="gh lnk" type=button data-sond="${esc(String(v.dosya||'').replace(/\.md$/,''))}">${L('Döküm')}</button>`)}
document.getElementById('tson').addEventListener('click',ev=>{const b=ev.target.closest('[data-sond]');if(!b)return;const a=document.getElementById('ard');if(!a.open)a.showModal();arDokumAc(b.dataset.sond)})
function platformSor(){return new Promise(res=>{const d=document.getElementById('pld');let v='';const bitir=()=>{d.removeEventListener('close',bitir);d.querySelectorAll('#plp button').forEach(x=>x.onclick=null);res(v)}
  d.querySelectorAll('#plp button').forEach(x=>x.onclick=()=>{v=x.dataset.v;d.close()});document.getElementById('plv').onclick=()=>d.close();d.addEventListener('close',bitir);d.showModal()})}
document.getElementById('tkb').onclick=async ev=>{const b=ev.currentTarget,m=document.getElementById('tkm'),k=document.getElementById('tkk').value.trim();if(!k){m.className='er';m.textContent=L('Kişi ve konuyu yaz');return}
  b.disabled=true;m.className='';m.textContent=L('başlatılıyor…')
  // toplantı hemen açılır (kullanıcı, 21 Ekim: hazırlık sekmesi kalktı — izle dökümü baştan okur, erken katılınca satır kaybolmaz): takvim olayının
  // bağlantısı, yoksa formdaki, o da yoksa seçilen uygulamanın ana sayfası; hiçbiri yoksa sayfa açılmaz. Aktarıcı Chrome'da açar (pano Safari'de olabilir).
  const o0=tkBul(tkSecili), bl=(o0&&o0.baglanti)?"":document.getElementById('tkl').value.trim()
  // S166: bağlantı da platform da yoksa hiçbir uygulama açılmaz; kullanıcıya platform seçtirilir (vazgeçerse Başlat olmaz)
  let pl=bl?'':sgVal('tkp')
  if(!bl&&!(o0&&o0.baglanti)&&!pl){pl=await platformSor();if(!pl){m.textContent='';b.disabled=false;return}sgSet('tkp',pl)}
  try{const r=await baslatIstek({olay:tkSecili,konu:k,baglanti:bl,platform:pl,baglam:document.getElementById('tkc').value,gundem:document.getElementById('tkg').value,rol:sgVal('tkr'),dil:sgVal('tkd')});if(r.devam){m.textContent='';document.getElementById('tkf').hidden=true;if(last)renderTakvim(last);return}if(r.err==='köken'||r.err==='anahtar')r.err=L('Pano eski — sayfayı yenileyip tekrar dene');if(r.ok&&r.baglanti)chromeAc({baslatma:true});m.className=r.ok?'ok':'er';m.textContent=r.ok?L(r.baglanti?"Başladı — toplantı açılıyor":"Başladı — toplantıya kendin katıl"):(r.err||L('başlatılamadı'))
    if(r.ok)setTimeout(()=>{document.getElementById('tkf').hidden=true;if(last)renderTakvim(last)},1500)}  // v0.112.0: başlayınca form kapanır (Mac'te inen sayfa açık kalıp pencereyi kilitliyordu)
  catch(e){m.className='er';m.textContent=L("Suflor.me'ye ulaşılamadı")}finally{setTimeout(()=>b.disabled=false,3000)}}
// bas-konuş (Faz 4): toplantı dışında basılı tut → pano mikrofonu 16 kHz → /bas-konus → yerel Whisper → Claude (açık süreç) → Mac sesi
let kRec=null,kSure=null
// v0.46.0 konuşurken yazıya dökme: kayıt sürerken 0,5 sn'de bir (v0.47.0; konuşurken "hı hı" duraksamayı geç görmesin) yeni ses aktarıcıya (komut parca); bırakışta bütün kayıt yine gider (önek eşleşirse
// aktarıcı yalnız kalan kısmı döker). Tarayıcı 16 kHz vermezse akış yok (dönüşüm parça parça birebir olmaz).
function f2b64(f){const pcm=new Int16Array(f.length);for(let i=0;i<f.length;i++){const v=Math.max(-1,Math.min(1,f[i]));pcm[i]=v<0?v*32768:v*32767}
  const u=new Uint8Array(pcm.buffer);let bin='';for(let i=0;i<u.length;i+=32768)bin+=String.fromCharCode.apply(null,u.subarray(i,i+32768));return btoa(bin)}
function konusAkis(k){if(!k||!k.hazir)return;const yeni=k.parca.slice(k.gid);if(!yeni.length)return;k.gid=k.parca.length
  let n=yeni.reduce((a,b)=>a+b.length,0),f=new Float32Array(n),o=0;for(const b of yeni){f.set(b,o);o+=b.length}
  j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'parca',pcm:f2b64(f)})}).catch(()=>{})}
async function konusBasla(){if(kRec)return;if(kSoh)sohbetKapat(true);kRec={hazir:false};if(!toplantidaMi(last))shAc(true,false);konusCiz()
  let r={};try{r=await j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'basla'})})}catch(e){}
  if(!r.ok){kRec=null;konusCiz();geciciDurum(L('Bas-konuş başlamadı'),r.err||'');return}
  try{const st=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}}),ac=new AudioContext({sampleRate:16000}),src=ac.createMediaStreamSource(st),pr=ac.createScriptProcessor(4096,1,1),parca=[]
    pr.onaudioprocess=e=>parca.push(new Float32Array(e.inputBuffer.getChannelData(0)));src.connect(pr);pr.connect(ac.destination)
    if(!kRec){st.getTracks().forEach(t=>t.stop());ac.close();return}  // izin beklerken bırakıldı
    Object.assign(kRec,{st,ac,src,pr,parca,hazir:true,gid:0});duzeyKur(kRec);kayitSesi(true);if(ac.sampleRate===16000){const k=kRec;k.akis=setInterval(()=>konusAkis(k),500)}
    kSure=setTimeout(konusBitir,60000);if(kRec.birak)konusBitir()}
  catch(e){kRec=null;konusCiz();geciciDurum(L('Mikrofon açılamadı'),String(e&&e.name||''))}}
// v0.99.3 (erişilebilirlik): Konuş düğmesi odaktayken Boşluk ya da Enter basılı → kayıt, bırakınca gönder (fareyle basılı tutmanın klavye karşılığı);
// sohbet kipinde dokunuş gibi aç/kapat. Odak düğmeden çıkarsa kayıt biter. Option + Shift + Boşluk her yerde ayrıca çalışır.
function basTutTus(kb){const tus=e=>(e.code==='Space'||e.key==='Enter')&&!e.altKey&&!e.metaKey&&!e.ctrlKey
  kb.addEventListener('keydown',e=>{if(!tus(e))return;e.preventDefault();if(e.repeat)return;konusBasla()})
  kb.addEventListener('keyup',e=>{if(!tus(e))return;e.preventDefault();konusBitir()});kb.addEventListener('blur',()=>{if(kRec)konusBitir()})}
async function konusBitir(){const k=kRec;if(!k)return;if(!k.hazir){k.birak=true;return}kRec=null;kayitSesi(false);clearTimeout(kSure);if(k.akis)clearInterval(k.akis);konusCiz()
  k.pr.disconnect();k.st.getTracks().forEach(t=>t.stop());const sr=k.ac.sampleRate;await k.ac.close()
  let n=k.parca.reduce((a,b)=>a+b.length,0),f=new Float32Array(n),o=0;for(const b of k.parca){f.set(b,o);o+=b.length}
  if(sr!==16000){const m=Math.floor(n*16000/sr),g=new Float32Array(m);for(let i=0;i<m;i++)g[i]=f[Math.floor(i*sr/16000)];f=g;n=m}  // tarayıcı 16 kHz vermezse
  let r={};try{r=await j('/bas-konus',{method:'POST',body:JSON.stringify({pcm:f2b64(f)})})}catch(e){}
  if(!r.ok)geciciDurum(L('Soru gönderilemedi'),r.err||'');refresh()}
// v0.49.0 sohbet kipi (eller serbest): bir dokunuş mikrofonu açık tutar, 0,5 sn'de bir yeni ses /bas-konus sohbet_parca'ya; tur sonuna, araya girmeye ve
// kapanışa aktarıcı karar verir (aktarici/sohbet.py). Yanıtta kapali ya da durumda sohbet kapalı görünürse mikrofon kapanır. Tarayıcı 16 kHz vermezse parça örneklenir.
let kSoh=null
function sohbetGonder(k){if(!k||!k.hazir)return;const yeni=k.parca.splice(0);if(!yeni.length)return
  let n=yeni.reduce((a,b)=>a+b.length,0),f=new Float32Array(n),o=0;for(const b of yeni){f.set(b,o);o+=b.length}
  const sr=k.ac.sampleRate;if(sr!==16000){const m=Math.floor(n*16000/sr),g=new Float32Array(m);for(let i=0;i<m;i++)g[i]=f[Math.floor(i*sr/16000)];f=g}
  j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'sohbet_parca',pcm:f2b64(f)})}).then(r=>{if(r&&r.kapali&&kSoh===k)sohbetKapat(false)}).catch(()=>{})}
async function sohbetAc(){if(kSoh)return sohbetKapat(true);if(kRec)return
  let r={};try{r=await j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'sohbet_basla'})})}catch(e){}
  if(!r.ok){geciciDurum(L('Sohbet açılmadı'),r.err||'');return}
  kSoh={hazir:false,t:Date.now()};konusCiz()
  if(r.yerel){Object.assign(kSoh,{hazir:true,yerel:true});kayitSesi(true);return}  // Adım 4: mikrofon aktarıcının yerel ses yardımcısından gelir; Chrome mikrofonu AÇILMAZ (yardımcı Chrome'u toplantı sanıp VPIO'yu kapatırdı)
  try{const st=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}}),ac=new AudioContext({sampleRate:16000}),src=ac.createMediaStreamSource(st),pr=ac.createScriptProcessor(4096,1,1),parca=[]
    pr.onaudioprocess=e=>parca.push(new Float32Array(e.inputBuffer.getChannelData(0)));src.connect(pr);pr.connect(ac.destination)
    if(!kSoh){st.getTracks().forEach(t=>t.stop());ac.close();return}
    Object.assign(kSoh,{st,ac,src,pr,parca,hazir:true});duzeyKur(kSoh);kayitSesi(true);const k=kSoh;k.akis=setInterval(()=>sohbetGonder(k),500)}
  catch(e){sohbetKapat(true);geciciDurum(L('Mikrofon açılamadı'),String(e&&e.name||''))}}
function sohbetKapat(bildir){const k=kSoh;kSoh=null;if(k){if(k.hazir)kayitSesi(false);if(k.akis)clearInterval(k.akis);if(!k.yerel)try{k.pr.disconnect();k.st.getTracks().forEach(t=>t.stop());k.ac.close()}catch(e){}}
  if(bildir)j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'sohbet_kapat'})}).catch(()=>{});konusCiz()}
// deneme hatırlatması (v0.35.2): sıradaki gerçek toplantıda bir kez — panoda ve mini panoda; Tamam kapatır (aktarıcı dosyaya yazar)
function renderHat(d,s){const el=d.getElementById(d===document?'hat':'mhat'),h=s.hatirlat;if(!el)return;el.hidden=!h;if(!h)return
  if(el.dataset.id===h.id+(h.altyazi||''))return;el.dataset.id=h.id+(h.altyazi||'')
  setH(el,`<div class=sh><span>${esc(h.baslik||L('Deneme hatırlatması'))}</span><button class=gh data-hk>${L('Tamam')}</button></div><ul>${(h.maddeler||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${h.altyazi==='basladi'?`<div class=meta>${L('Altyazı ölçümü başladı (3 dk) — Teams’te canlı altyazı açık olsun.')}</div>`:''}`)
  el.querySelector('[data-hk]').onclick=()=>{j('/hatirlat',{method:'POST',body:JSON.stringify({id:h.id})}).catch(()=>{});el.hidden=true;const o=d===document?(mini&&!mini.closed&&mini.document.getElementById('mhat')):document.getElementById('hat');if(o)o.hidden=true}}
// v0.118.0 tek kutu (5. taslak; kullanıcı, 22 Ekim gece: "asistan her yerden ulaşılmalı; üç kapı yerine tek kutu"): mikrofon kutunun sağında.
// Basılı tut (200 ms'den uzun) = sesle sor, bırakınca gider; iki kez dokun = Sohbet (eller serbest; açılıp açılmayacağına aktarıcı karar verir:
// toplantıda ve kulaklıksız açılmaz); Sohbet açıkken bir dokunuş kapatır. Option + Shift + Boşluk her yerde basılı tut. Kayıtta simge vurgu renginde,
// yanında sesin gerçek düzeyi (AnalyserNode), altta "Dinliyorum". Köşedeki soluk nokta: asistan dinliyor (toplantıda Whisper seni duyuyor ya da Sohbet açık).
let mkT=null,mkSon=0,mkBas=0,kIp='',kIpT=0
function toplantidaMi(s){return!!(s&&s.aktif)}
function terminalAcik(s){const d=((s&&s.toplanti_oturum)||{}).durum;return!!s&&((s.claude_age_s!=null&&s.claude_age_s<120)||['bekliyor','calisiyor','izliyor','terminalde'].includes(d))}  // 16 Kasım: toplantı oturumu terminalde açıkken (izle yokluyor ya da oturum bekliyor) {asistan} paneli kendiliğinden açılmaz; yazışma terminalde sürer, el ile açmak serbest  // Faz B: tek kayıt (/status toplanti); 3 Kasım: aktif = canlı (algılandı/sürüyor) — bitiyor/bitti'de pano Bugün'e döner
function kutuIpucu(m){kIp=m;clearTimeout(kIpT);kIpT=setTimeout(()=>{kIp='';altCiz()},2500);altCiz()}
function altCiz(){const m=kRec?L('Dinliyorum · bırakınca gönderir'):kSoh?L('Sohbet açık · bir dokunuş kapatır'):kIp
  for(const d of [document,mini&&!mini.closed&&mini.document])if(d){const e=d.getElementById(d===document?'kal':'mkal');if(e&&e.textContent!==m)e.textContent=m}}
// sesli cevap düğmesi (v0.214): kutudan yazılan sorunun cevabı da okunsun; durum bu tarayıcıda hatırlanır, varsayılan kapalı. Aktarıcı toplantıda ve gizli kipte yine okumaz (yazılı kalır).
function kutuSesliAcik(){try{return localStorage.getItem('suflorSesliCevap')==='1'}catch(e){return false}}
function kutuSesliCiz(d,o){const b=d.getElementById(o+'ksb');if(!b)return;const a=kutuSesliAcik(),t=a?L('Cevapları sesli oku · açık (toplantıda okunmaz)'):L('Cevapları sesli oku');b.setAttribute('aria-pressed',a?'true':'false');b.title=t;b.setAttribute('aria-label',L('Cevapları sesli oku'));b.innerHTML=ic(a?'hoparlor':'hoparlorx')}
function kutuSesliDegis(){try{localStorage.setItem('suflorSesliCevap',kutuSesliAcik()?'0':'1')}catch(e){}kutuSesliCiz(document,'');if(mini&&!mini.closed)kutuSesliCiz(mini.document,'m');kutuIpucu(kutuSesliAcik()?L('Cevaplar sesli okunacak'):L('Cevaplar yalnız yazılı'))}
function mikCiz(kb,s){if(!kb)return;const w=(s&&s.whisper)||{};kb.classList.toggle('on',!!kRec);kb.classList.toggle('soh',!!kSoh);kb.classList.toggle('dinl',!!kSoh||!!(s&&s.aktif&&w.ben));kb.dataset.d=kRec?'':((s&&s.konus||{}).durum||'')}
function kutuBagla(d,o){const kb=d.getElementById(o+'kb'),ek=d.getElementById(o+'ek'),ekd=d.getElementById(o+'ekd'),ks=d.getElementById(o+'ksb');if(ks){ks.onclick=kutuSesliDegis;kutuSesliCiz(d,o)}
  ek.onclick=()=>ekd.click();ekd.onchange=()=>{const f=[...ekd.files];ekd.value='';if(f.length)baglamBirak(f)}  // sürükle-bırakla aynı yol
  kb.addEventListener('pointerdown',e=>{if(e.button)return;e.preventDefault();sesAc();if(kSoh){sohbetKapat(true);mkSon=0;return}
    try{kb.setPointerCapture(e.pointerId)}catch(x){}mkBas=Date.now();clearTimeout(mkT);mkT=setTimeout(()=>{mkT=null;konusBasla()},200)})
  const birak=()=>{if(!mkBas)return;mkBas=0;if(!mkT){konusBitir();return}clearTimeout(mkT);mkT=null;const t=Date.now()
    if(t-mkSon<400){mkSon=0;sohbetAc();return}mkSon=t;setTimeout(()=>{if(mkSon===t&&!kSoh&&!kRec)kutuIpucu(L('Basılı tut ve konuş · iki kez dokun: sohbet'))},420)}
  kb.addEventListener('pointerup',birak);kb.addEventListener('pointercancel',birak);basTutTus(kb)}
// kayıt sesi: basınca kısa yükselen, bırakınca pes ton (~120 ms, kısık). Toplantıda yalnız kulaklık takılıyken (hoparlörden toplantıya gitmesin); ayar kayit_sesi kapatır.
let kSesAc=null
function sesAc(){try{if(!kSesAc)kSesAc=new AudioContext();if(kSesAc.state==='suspended')kSesAc.resume()}catch(e){}}
function kayitSesi(yukari){const s=last||{},a=s.ayarlar&&s.ayarlar.deger;if(a&&a.kayit_sesi===false)return;if(toplantidaMi(s)&&!(s.konus&&s.konus.kulaklik))return
  try{sesAc();const c=kSesAc,o=c.createOscillator(),g=c.createGain(),t=c.currentTime;o.type='sine';o.frequency.setValueAtTime(yukari?520:700,t);o.frequency.exponentialRampToValueAtTime(yukari?780:440,t+.12)
    g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.045,t+.015);g.gain.exponentialRampToValueAtTime(.0001,t+.12);o.connect(g);g.connect(c.destination);o.start(t);o.stop(t+.13);window._kses=(window._kses||0)+1}catch(e){}}
// ses düzeyi: mikrofonun frekans enerjisi beş banda (konuşma aralığı ~250–4000 Hz) bölünür, her çubuk bir bant
let dzR=0
function duzeyKur(k){try{const an=k.ac.createAnalyser();an.fftSize=64;an.smoothingTimeConstant=.5;k.src.connect(an);k.an=an}catch(e){}if(!dzR)dzR=requestAnimationFrame(duzeyDongu)}
function duzeyDongu(){dzR=0;const k=kRec&&kRec.an?kRec:kSoh&&kSoh.an?kSoh:null,ds=[document,mini&&!mini.closed&&mini.document].filter(Boolean)
  let h=null;if(k){const a=new Uint8Array(k.an.frequencyBinCount);k.an.getByteFrequencyData(a);h=[0,1,2,3,4].map(i=>{let t=0;for(let j=1+i*3;j<4+i*3;j++)t+=a[j]||0;return 3+Math.round(t/765*19)})}
  for(const d of ds){const z=d.getElementById(d===document?'kdz':'mkdz');if(!z)continue;z.classList.toggle('on',!!h);if(h)[...z.children].forEach((c,i)=>c.style.height=h[i]+'px')}
  if(k)dzR=requestAnimationFrame(duzeyDongu)}
function konusCiz(){mikCiz(document.getElementById('kb'),last);if(mini&&!mini.closed)mikCiz(mini.document.getElementById('mkb'),last);altCiz();if(last)renderKonus(last)}
// cevap kutunun üstünde: asistanın adı küçük etiket; panoda cevabın tamamı (uzunsa kendi içinde kayar — sesli okuma 5 cümlede durup "kalanı panoda" der), mini panoda
// en çok iki satır (dokununca yerinde açılır); panoda dokununca yan panelde konuşma geçmişi; durum tek soluk satır
const KONUS_SUREN=['dinliyor','yaziya','dusunuyor','konusuyor']
// sohbet görünümü: aktarıcı yalnız son soru-cevabı verir; son 6 çift bu sayfada tutulur (yenilenince sıfırlanır; kalıcı geçmiş yan panelde/Tümü'de). kcSur: yeni soru ya da cevap gelince artar → alan o soruya kayar.
// v0.212.0: KC sohbet panelinin de kaynağı — 30 tur tutulur (panel açılınca /konus-gecmis'ten son 20 tur başa eklenir); toplantıdaki kısa görünüm ve mini pano son KC_KISA turu gösterir.
const KC=[],KC_N=30,KC_KISA=6;let kcSur=0,kcDurum='',kcDf='',kcTop=0  // kcTop: toplantının başladığı an; toplantıdaki kısa görünüm ondan önceki turları göstermez
const kcNorm=t=>String(t||'').replace(/\s+/g,' ').trim().toLowerCase()
const kcTemiz=t=>String(t||'').replace(/\s*<(?:chuckles?|laugh(?:ter)?|sighs?|gasp|giggle|short pause|long pause|exhales|breath|hmm|ton:\s*[a-z_]+)>\s*/gi,' ').trim()
// aynı soru son üç turdan birindeyse o tura işlenir (panelden gönderilen soru cevabı gelmeden listede durur; aktarıcı o sırada önceki turu vermeye devam eder)
function kcKaydet(k,taze){const q=String(k.soru||'').trim(),nq=kcNorm(q);let c=taze?kcTemiz(k.cevap):'';if(!q&&!c)return
  if(c&&['dinliyor','yaziya','dusunuyor'].includes(k.durum)&&KC.some(x=>x.cevap===c&&kcNorm(x.soru)!==nq))c=''  // yeni tur başlarken aktarıcı bir süre önceki cevabı verir: o cevap yeni soruya yazılmaz
  const ad=asGor(k),sl=!!k.sesli_cevap,kt=k.at?Date.parse(k.at):0
  for(let i=KC.length-1;i>=Math.max(0,KC.length-3);i--){const e=KC[i];if(kcNorm(e.soru)!==nq)continue
    if(e.bekliyor&&kt&&kt<e.t-3000)continue  // bekleyen (yeni gönderilen) soru, aynı metinli eski turun cevabını almasın
    if(e.cevap&&c&&!c.startsWith(e.cevap.slice(0,40)))break  // aynı soru yeniden soruldu, cevap farklı → yeni tur
    if(c&&!e.cevap)kcSur++;if(c)e.cevap=c;e.ad=ad;if(!e.bekliyor)e.sesli=sl;delete e.bekliyor;return}
  KC.push({soru:q,cevap:c,ad,sesli:sl,t:kt||Date.now()});kcSur++;if(KC.length>KC_N)KC.shift()}
// markdown'ın güvenli alt kümesi: önce her satır kaçırılır (esc), sonra yalnız bilinen işaretler etikete döner; bağlantı yalnız http(s)
function kcMd(m){const sat=String(m||'').split('\n'),o=[];let lt='',tb=false,kod=false
  const ic=t=>esc(t).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?![*\w])/g,'$1<i>$2</i>').replace(/\[([^\]]+)\]\((https?:\/\/[^)\s"<]+)\)/g,'<a href="$2" target=_blank rel="noopener noreferrer">$1</a>')
  const kapat=()=>{if(lt){o.push('</'+lt+'>');lt=''}if(tb){o.push('</table>');tb=false}}
  for(const l of sat){let x
    if(/^\s*```/.test(l)){if(kod){o.push('</pre>');kod=false}else{kapat();o.push('<pre>');kod=true}continue}
    if(kod){o.push(esc(l)+'\n');continue}
    if(!l.trim())continue
    if(/^\s*\|/.test(l)){if(/^[\s|:-]+$/.test(l))continue;if(!tb){kapat();o.push('<table>');tb=true}o.push('<tr>'+l.trim().replace(/^\||\|$/g,'').split('|').map(c=>`<td>${ic(c.trim())}</td>`).join('')+'</tr>');continue}
    if(x=l.match(/^\s*#{1,4}\s+(.*)/)){kapat();o.push(`<h4>${ic(x[1])}</h4>`);continue}
    if(x=l.match(/^\s*(?:([-*•])|(\d{1,3})[.)])\s+(.*)/)){const t=x[2]?'ol':'ul';if(tb){o.push('</table>');tb=false}if(lt!==t){kapat();o.push(t==='ol'?`<ol start="${+x[2]}">`:'<ul>');lt=t}o.push(`<li>${ic(x[3])}</li>`);continue}
    kapat();o.push(`<p>${ic(l)}</p>`)}
  kapat();if(kod)o.push('</pre>');return o.join('')}
// 10 Kasım: iki sesli tur (dış işler asistanı + varsayılan asistan) — cevabın satırları «[Ad] söz»; bilinen asistan adıyla başlayan satırlar ad etiketli ayrı bloklar olur (aktarıcı etiketleri yalnız bu turda yazar)
function kcKonus(ky){const ad=new Set([...Object.keys(ASM),...Object.values(ASM),AS].map(x=>String(x).toLowerCase())),g=[];let n=0
  for(const l of String(ky||'').split('\n')){const m=l.match(/^\s*\[([^\]\n:]{1,40})\]\s+(.*)$/);if(m&&ad.has(m[1].trim().toLowerCase())){g.push({ad:m[1].trim(),t:m[2]});n++}else if(g.length)g[g.length-1].t+='\n'+l;else g.push({ad:'',t:l})}
  return n?g.filter(x=>x.t.trim()||x.ad):null}
function kcKonusHtml(e,i,ky,mini_){const kop=`<button type=button class=kop data-kop=${i} title="${esc(L('Kopyala'))}" aria-label="${esc(L('Kopyala'))}">${ic('kopya')}</button>`,os=mini_?` data-kos title="${esc(L('Tamamını göster'))}"`:'',sg=kcKonus(ky)||[{ad:'',t:ky}]
  return sg.map((g,j)=>`<div class=ca><span>${esc(g.ad||e.ad)}</span>${j?'':kop}</div><div class=kcm${os}>${kcMd(g.t)}</div>`).join('')}
function kcOge(e,i,son,mini_){const p=e.cevap.split(/\n\s*-{3,}\s*\n?/),ky=p[0].trim(),ay=p.slice(1).join('\n').trim()
  const q=e.soru?`<div class=d><b>${L(e.sesli?'Duyulan':'Soru')}:</b> ${esc(e.soru)}</div>`:''
  const a=ky?`${kcKonusHtml(e,i,ky,mini_)}${ay?`<details class=kay><summary>${L('Ayrıntı')}</summary><div class=kcm>${kcMd(ay)}</div></details>`:''}`:''
  return`<div class="kcq${son?' son':''}">${q}${a}</div>`}
async function kcKopya(b,d){const e=KC[+b.dataset.kop];if(!e)return;const t=e.cevap;let ok=false
  try{await (d.defaultView||window).navigator.clipboard.writeText(t);ok=true}catch(x){try{const ta=d.createElement('textarea');ta.value=t;ta.style.cssText='position:fixed;opacity:0';d.body.appendChild(ta);ta.select();ok=d.execCommand('copy');ta.remove()}catch(y){}}
  b.textContent=ok?'✓ '+L('Kopyalandı'):L('Kopyalanamadı');setTimeout(()=>{b.innerHTML=ic('kopya')},1500)}
// yeniden çizimde okuma yeri korunur; yeni soru/cevap gelince son sorunun başına kayar
function kcKonum(kok,sc){const h=kok.__kt;sc=sc||kok;if(!sc||!kok.querySelector('.kcq'))return
  if(kok.__ks!==kcSur){kok.__ks=kcSur;const son=kok.querySelector('.kcq.son');if(son)sc.scrollTop=son.getBoundingClientRect().top-sc.getBoundingClientRect().top+sc.scrollTop}else if(h!=null)sc.scrollTop=h}
function konusGorunum(s,mini_,ust_){const k=s.konus||{},cvp=!!(s.eylem&&s.eylem.sesli),ad=asGor(k)
  if(s.aktif&&!k.toplanti)return''
  if(kSoh&&!(k.sohbet&&k.sohbet.acik)&&kSoh.hazir&&Date.now()-kSoh.t>3000)sohbetKapat(false)  // aktarıcı kapattı (sessizlik, "tamam teşekkürler", toplantı, kulaklık)
  const yas=k.at?(Date.now()-Date.parse(k.at))/1000:0,sur=KONUS_SUREN.includes(k.durum),taze=kRec||sur||yas<(s.aktif?300:1800)
  if(!kRec)kcKaydet(k,taze)
  const dt={yaziya:L('Yazıya döküyorum…'),dusunuyor:L('{ad} düşünüyor…',{ad}),konusuyor:kSoh?(s.ayarlar&&s.ayarlar.deger&&s.ayarlar.deger.sohbet_araya_girme?L('{ad} cevaplıyor — konuşursan susar',{ad}):L('{ad} cevaplıyor — sonuna kadar okur',{ad})):L('{ad} cevaplıyor',{ad}),hata:k.hata||''}
  const d=kRec?'':cvp&&k.durum!=='yaziya'?(kSoh?L('Yazayım mı? Cevap ver: evet · hayır · sonra · sus'):L('Yazayım mı? Basılı tut ve cevap ver: evet · hayır · sonra · sus')):(dt[k.durum]||(k.sohbet&&k.sohbet.acik&&typeof k.sohbet.devam==='number'&&k.durum!=='yaziya'?L('Dinliyorum… {n} sn',{n:Math.max(1,Math.ceil(k.sohbet.devam))}):k.sohbet&&k.sohbet.kapandi&&!kSoh?L('Sohbet kapandı — {n}',{n:{sessizlik:L('1 dakika ses gelmedi'),kulaklik:L('kulaklık çıktı'),toplanti:L('toplantı başladı'),kullanici:L('sen bitirdin'),pano:L('sen bitirdin')}[k.sohbet.kapandi]||k.sohbet.kapandi}):''))
  const df=k.defter&&!kRec&&!k.soru?`<div class=meta title="${esc(k.defter.ad||'')}">${esc(L('Son toplantı hazır: {a} · {s} — ne konuşulduğunu sorabilirsin',{a:toplantiAdi(k.defter.ad,''),s:k.defter.saat||''}))}</div>`:''  // dosya adı yalnız title'da
  if(!mini_){kcDurum=d;kcDf=df}
  const kl=kRec||!taze?[]:(s.aktif?KC.filter(e=>!e.gecmis&&e.t>=kcTop):KC).slice(-KC_KISA),off=KC.length-kl.length,son=kl[kl.length-1],ky=son&&son.cevap?son.cevap.split(/\n\s*-{3,}\s*\n?/)[0].trim():''
  const ust=modHtml(k)+(otonomHtml(k)||asistanHtml(k)),sus=k.durum==='konusuyor'?`<button class=gh data-sus>${L('Sus')}</button>`:'',sb=ky&&!kRec&&!sur?soyleBtn(ky):''
  if(ust_)return (ust+(shAcik?'':df+shPil(k))).trim()  // v0.212.0: sohbet paneli açıkken ya da toplantı dışında konuşma panelde; burada yalnız toplantı durumu (ve kapalı panelin tek satırı)
  const h=`${ust}${df}${d?`<div class=meta>${esc(d)}</div>`:''}${kl.length?`<div class=kcv>${kl.map((e,i)=>kcOge(e,off+i,i===kl.length-1,mini_)).join('')}</div>`:''}${sus||sb||(kl.some(e=>e.cevap)&&!mini_)?`<div class=kdb>${sus}${sb}${kl.some(e=>e.cevap)&&!mini_?(s.aktif?`<button class=gh data-kos title="${esc(L('Konuşma geçmişini aç'))}">${L('Geçmiş')}</button>`:`<button class=gh data-kgec title="${esc(L('Konuşma geçmişini aç'))}">${L('Tümü')}</button>`):''}</div>`:''}`
  return h.trim()}
function renderKonus(s){const sec=document.getElementById('kns'),s0=kcSur,h=konusGorunum(s,false,shAcik||!toplantidaMi(s));sec.hidden=!h;mikCiz(document.getElementById('kb'),s);document.getElementById('ksb').hidden=document.getElementById('kb').hidden=!!s.aktif&&!(s.konus||{}).toplanti
  document.getElementById('tbr').hidden=!toplantidaMi(s);document.getElementById('nb').classList.toggle('bos',shAcik&&!h&&!toplantidaMi(s));shYeniTur(s,s0);shCiz(s);shFab(s);shSekmeCiz(s);const kd=document.getElementById('knd'),c0=kd.querySelector('.kcv');if(c0)kd.__kt=c0.scrollTop
  if(h&&sec.dataset.h!==h){sec.dataset.h=h;setH(kd,h)}if(h){const c1=kd.querySelector('.kcv');if(c1)kcKonum(kd,c1)}}
{document.addEventListener('keydown',e=>{if(e.code==='Space'&&e.altKey&&e.shiftKey&&!document.getElementById('kb').hidden){e.preventDefault();if(!e.repeat)konusBasla()}})
  document.addEventListener('keyup',e=>{if(kRec&&(e.code==='Space'||e.key==='Alt'||e.key==='Shift')){e.preventDefault();konusBitir()}})}
// «Kayda not olarak ekle»: cevabın tamamı kayda yorum olarak yazılır (aktarıcı /kayit-not → asistanın yorum_ekle komutuyla aynı doğrulama; tıklama onaydır)
async function kayitaNot(i){const e=KC[i];if(!e||!e.kayit||e.kayitYaz||e.kayitYazildi)return;e.kayitYaz=true;if(last)renderKonus(last)
  let r={};try{r=await (await fetch('/kayit-not',{method:'POST',body:JSON.stringify({id:e.kayit,metin:String(e.cevap||'').replace(/\n\s*-{3,}\s*\n?/g,'\n\n')})})).json()}catch(x){r={}}
  e.kayitYaz=false;if(r.ok)e.kayitYazildi=true;bnBildir(r.ok?L('Kayda not eklendi'):r.err&&/gizli|private/i.test(String(r.err))?L('Gizli kip açık: kayıt yazılmaz.'):L('Yapılamadı.'));if(last)renderKonus(last);if(r.ok){try{emYenile()}catch(x){}}}
function susBagla(d){d.addEventListener('click',ev=>{if(ev.target.closest('button[data-sus]')){ev.stopPropagation();j('/bas-konus',{method:'POST',body:JSON.stringify({komut:'sus'})}).catch(()=>{});return}
  const kp=ev.target.closest('button[data-kop]');if(kp){ev.stopPropagation();kcKopya(kp,d);return}
  if(ev.target.closest('button[data-kgec]')){gecmisAc();return}
  const ky=ev.target.closest('button[data-kyz]');if(ky){ev.stopPropagation();kayitaNot(+ky.dataset.kyz);return}
  if(d===document&&ev.target.closest('[data-shac]')){shAc(true,true);return}
  const b=ev.target.closest('[data-kos]');if(!b)return;if(d===document){shAc(true,true)}else{const m=d.getElementById('mk');if(m){m.classList.toggle('acik');const sn=m.querySelector('.kcq.son');if(sn&&m.classList.contains('acik'))m.scrollTop=sn.getBoundingClientRect().top-m.getBoundingClientRect().top+m.scrollTop}}})}
susBagla(document)
