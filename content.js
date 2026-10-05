// Suflor.me — içerik betiği (content script)
// Toplantı sayfasındaki transkript ve canlı altyazı panelini izler, yeni satırları yerel aktarıcıya gönderir.
// v0.9.0: platformdan bağımsız çekirdek. Sayfaya özgü seçiciler ve metinler platform dosyasında (platform-teams.js …),
// manifest onu bu dosyadan önce yükler ve globalThis.SuflorPlatform olarak verir; arayüz platform-teams.js başında.
(() => {
  if (window.__ohCanliLoaded) return; window.__ohCanliLoaded = true;
  const P = globalThis.SuflorPlatform; if (!P) return;  // platform dosyası yüklenmedi: bu sayfada Suflor.me çalışmaz
  const TIME_RE = /^\d{1,2}:\d{2}(:\d{2})?$/;
  const SKIP_RE = P.SKIP_RE || /^$/;
  const DEFAULT_KEYWORDS = ["şifre", "parola", "password", "token", "anahtar", "api key", "secret", "gizli anahtar"];
  // v0.12.3 (güvenlik denetimi O3): aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
  const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
  function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
  let cfg = { relay: RELAY_VARSAYILAN, keywords: DEFAULT_KEYWORDS, enabled: true, stableMs: 3000, autoCaptions: true, whisper: true };
  let sentKeys = new Set(); const pending = new Map(); const sentById = new Map(); let lastPanelSig = ""; let meeting = null; let lastOk = 0; let failCount = 0;
  const MAX_QUEUE = 500; let queue = []; // aktarıcıya ulaşamayınca bekleyen gönderim paketleri
  // v0.7.0: kuyruk chrome.storage.local'da da tutulur — Teams sekmesi yenilenir/kapanırsa bekleyen satırlar kaybolmaz.
  // Her betik örneği kendi anahtarına yazar (ohQ:<örnek>); sahibi 25 sn'dir yenilemediği anahtarı (sekme yenilendi,
  // kapandı) başka bir örnek devralır. Aynı kimlikli satır iki kez giderse aktarıcı ayıklar (SEEN).
  const QKEY = "ohQ:" + Math.random().toString(36).slice(2, 10); let qSaved = false;
  function saveQueue() {
    try {
      if (queue.length) { chrome.storage.local.set({ [QKEY]: { t: Date.now(), q: queue } }); qSaved = true; }
      else if (qSaved) { chrome.storage.local.remove(QKEY); qSaved = false; }
    } catch (e) { /* eklenti yeniden yüklendi: bağlam geçersiz */ }
  }
  function adoptQueues() {
    try {
      chrome.storage.local.get(null, all => {
        const old = Object.keys(all || {}).filter(k => k.startsWith("ohQ:") && k !== QKEY && all[k] && Date.now() - (all[k].t || 0) > 25000);
        if (!old.length) return;
        let n = 0; old.forEach(k => { const q = all[k].q || []; n += q.length; queue = q.concat(queue); });
        chrome.storage.local.remove(old); if (queue.length > MAX_QUEUE) queue.splice(0, queue.length - MAX_QUEUE);
        log("önceki sekmeden kalan", n, "paket devralındı"); saveQueue(); drainQueue().then(saveQueue);
      });
    } catch (e) {}
  }
  const log = (...a) => console.debug("[Suflor.me]", ...a);
  // v0.12.2: arayüz dili (tr/en) — şerit, toast'lar, kart düğmeleri. Kaynak aktarıcının /status "arayuz_dili" alanı (dakikada bir
  // okunur), chrome.storage.local "dil"de saklanır; yoksa "tr". Anahtar Türkçe metnin kendisi, terimler panoyla aynı.
  // Aktarıcıya giden metinler (/olay, /komut) ve Claude'un kart metinleri çevrilmez.
  let DIL = "tr";
  const EN = {"Suflor.me: bu Mac'te başka bir çalışma alanı da var. Bu Chrome \"{a}\" alanına yazmaya devam ediyor; değiştirmek için Suflor.me simgesine tıkla.":
    "Suflor.me: there's another workspace on this Mac. This Chrome keeps writing to \"{a}\"; click the Suflor.me icon to change it.",
    "Suflor.me: bu Mac'te birden fazla çalışma alanı var — Suflor.me simgesine tıklayıp bu Chrome'un alanını seç. O zamana kadar satırlar bekletiliyor.":
    "Suflor.me: there's more than one workspace on this Mac — click the Suflor.me icon and pick this Chrome's workspace. Lines are held until then.",
    "Suflor.me: canlı altyazı açıldı":"Suflor.me: live captions turned on",
    "Suflor.me: altyazı konuşma dili {d} yapıldı (gündem dili)":"Suflor.me: caption spoken language set to {d} (agenda language)", "İngilizce":"English", "Türkçe":"Turkish",
    "Suflor.me: altyazıyı açamadım — bir kez elle aç ({y}), yolu öğrenirim":"Suflor.me: couldn't turn on captions — turn them on once by hand ({y}) and I'll learn the way",
    "Suflor.me: toplantıdasın ama döküm/altyazı kapalı — satır kaydedilmiyor. ":"Suflor.me: you're in a meeting but transcript/captions are off — no lines are being saved. ",
    "⚠ Ekranda/konuşmada hassas ifade: ":"⚠ Sensitive phrase on screen/in conversation: ","📷 Kanıt {n} kaydedildi":"📷 Evidence {n} saved",
    "📷 Kanıt kaydedilemedi: ":"📷 Couldn't save evidence: ","bilinmiyor":"unknown",
    "Suflor.me Whisper: senin sesin yazılıyor. Karşı tarafın sesi için bir kez Option + Shift + W'ye bas (ya da Suflor.me simgesi → Karşı taraf)":
    "Suflor.me Whisper: your voice is being transcribed. For the other side's audio, press Option + Shift + W once (or Suflor.me icon → Other side)",
    "⏱ {n} dk":"⏱ {n} min","⏱ süre doldu":"⏱ time's up","⏱ +{n} dk":"⏱ +{n} min"," · {n} madde geride":" · {n} items behind",
    "{n} dk kaldı":"{n} min left","süre doldu":"time's up","+{n} dk":"+{n} min","⚠ disk":"⚠ disk","⚠ dil":"⚠ language",
    "1 kart":"1 card","{n} kart":"{n} cards","1 soru bekliyor":"1 question waiting","{n} soru bekliyor":"{n} questions waiting",
    "Son 1 dk özeti":"Last 1 min summary","Claude son dakikayı 1–2 cümleyle özetlesin":"Claude sums up the last minute in 1–2 sentences",
    "📷 Kanıt":"📷 Evidence","{p} ekranını kanıt olarak kaydet (klavye: Option + Shift + K)":"Save the {p} screen as evidence (keyboard: Option + Shift + K)",
    "istendi…":"requested…","Sor":"Ask","Belirt":"Say","Değinme":"Don't raise","Dikkat":"Caution","Cevap":"Answer","Bilgi":"Info","Duygu":"Mood",
    "metin yalnız mini panoda / panoda":"text only in the mini panel / panel","✓ Yaptım":"✓ Done","Okudum":"Seen","✕ Gerek yok":"✕ Not needed",
    "Önerileni yaptım":"I did what was suggested","Gördüm, kapat (reddetmiyorum)":"Seen, close it (not rejecting)","Bu konu gereksiz; Claude bir daha önermesin":"Not relevant; Claude won't suggest it again",
    "Son 1 dk özeti hazırlanıyor…":"Preparing the last-minute summary…","Claude'a soruldu: ":"Asked Claude: ",
    "Option + Shift + H: şeridi gizle · Option + Shift + K: kanıt · Option + Shift + S: önemli an · Option + Shift + O: son 1 dk":"Option + Shift + H: hide strip · Option + Shift + K: evidence · Option + Shift + S: key moment · Option + Shift + O: last 1 min",
    "Claude şeridi gizlendi (Option + Shift + H ile geri aç)":"Claude strip hidden (Option + Shift + H to show it again)","Claude şeridi açık":"Claude strip shown"};
  const L = (s, v) => { let t = DIL === "en" && EN[s] || s; if (v) for (const k in v) t = t.split("{" + k + "}").join(v[k]); return t; };
  function dilAyarla(d) { DIL = d === "en" ? "en" : "tr"; P.dil = DIL; }
  try { chrome.storage.local.get({ dil: "tr" }, v => dilAyarla(v.dil)); } catch (e) {}

  // v0.9.2: aktarıcı adresi yalnız bu tarayıcıda (storage.local) — iki macOS hesabının Chrome'u aynı Google hesabıyla eşitlenirse
  // adres karşı hesaba geçmesin (iki aktarıcı aynı anda açık, ikisine de 127.0.0.1'den ulaşılır). Eski sync değeri yalnız yedek.
  // Seçim yoksa bu Mac'teki aktarıcılar yoklanır (8765–8768). Birden fazlaysa seçim yapılana kadar HİÇBİR ŞEY gönderilmez (satırlar
  // kuyrukta bekler) ve bir kez uyarılır. v0.13.5: tek aktarıcı varsa o "kendiliğinden" (relayOto) kaydedilir — önceden kaydedilmiyordu ve
  // aynı Mac'e ikinci hesap kurulunca ilk hesabın Chrome'u sessizce göndermeyi bırakıyordu (5 Ekim). Sonradan ikinci alan belirirse
  // gönderim sürer, bir kez "bu Chrome X alanına yazıyor; değiştirmek için simgeye tıkla" denir.
  let alanBekliyor = false, alanSecili = false, alanUyarildi = false, sonHata = "";
  async function alanKesfet() {
    if (alanSecili) return;
    const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok ? `http://127.0.0.1:${p}` : null; } catch (e) { return null; } }))).filter(Boolean);
    alanBekliyor = bul.length > 1;
    if (bul.length === 1) { cfg.relay = bul[0]; alanSecili = true; chrome.storage.local.set({ relay: bul[0], relayOto: true }); }
    if (alanBekliyor && !alanUyarildi && window.top === window) { alanUyarildi = true; toast(L("Suflor.me: bu Mac'te birden fazla çalışma alanı var — Suflor.me simgesine tıklayıp bu Chrome'un alanını seç. O zamana kadar satırlar bekletiliyor."), "#b26a00", 15000); }
  }
  chrome.storage.sync.get(cfg, v => { cfg = Object.assign(cfg, v); chrome.storage.local.get({ relay: null, relayOto: false }, l => { if (l.relay) { cfg.relay = l.relay; alanSecili = true; if (l.relayOto) otoDenetle(); } else alanKesfet(); }); });
  async function otoDenetle() {  // v0.13.5: kendiliğinden seçilmiş alan + bu Mac'te başka alan var → bir kez bilgi (gönderim durmaz)
    if (window.top !== window) return;
    const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok ? await r.json() : null; } catch (e) { return null; } }))).filter(Boolean);
    if (bul.length < 2) return;
    const { relayOtoUyari } = await chrome.storage.local.get({ relayOtoUyari: false }); if (relayOtoUyari) return;
    const su = bul.find(s => cfg.relay && cfg.relay.endsWith(":" + s.port)); chrome.storage.local.set({ relayOtoUyari: true });
    toast(L("Suflor.me: bu Mac'te başka bir çalışma alanı da var. Bu Chrome \"{a}\" alanına yazmaya devam ediyor; değiştirmek için Suflor.me simgesine tıkla.", { a: (su && su.alan) || cfg.relay }), "#b26a00", 15000);
  }
  setInterval(alanKesfet, 30000);
  chrome.storage.onChanged.addListener((ch, alan) => {
    for (const k in ch) if (!(k === "relay" && alan === "sync")) cfg[k] = ch[k].newValue;
    if (alan === "local" && ch.relay && ch.relay.newValue) { alanSecili = true; alanBekliyor = false; }
    if (alan === "local" && ch.dil) dilAyarla(ch.dil.newValue);  // v0.12.2: popup ya da başka sekme dili güncelledi
  });
  // v0.9.6: her istek en çok 8 sn bekler — 3 Ekim denemesinde nabız ~7 dk kesildi, mikrofon sesi akmaya devam etti; zaman aşımı
  // olmayan bir istek takılırsa onu bekleyen her şey (nabız → kuyruk boşaltma) de takılıyordu
  const rf = (yol, o) => alanBekliyor ? Promise.reject(new Error("çalışma alanı seçilmedi")) : fetch((relayGecerli(cfg.relay) || RELAY_VARSAYILAN) + yol, Object.assign({ signal: AbortSignal.timeout(8000) }, o));
  // v0.12.2: arayüz dilini aktarıcıdan oku (yalnız üst çerçeve, dakikada bir); değişince storage.local "dil" — diğer sekmeler ve
  // popup onChanged ile alır. Alan yoksa (eski aktarıcı) "tr".
  async function dilOku() {
    if (window.top !== window) return;
    try { const j = await (await rf("/status")).json(); const d = j.arayuz_dili === "en" ? "en" : "tr"; if (d !== DIL) { dilAyarla(d); chrome.storage.local.set({ dil: d }); } } catch (e) {}
  }
  setTimeout(dilOku, 2000); setInterval(dilOku, 60000);

  function meetingInfo() {
    const title = P.toplantiAdi();
    if (!meeting || meeting.title !== title) { meeting = { title, startedAt: new Date().toISOString(), url: location.origin, platform: P.ad }; capWords = []; capEn = []; capLang = null; } // v0.6.1: yeni toplantıda dil yeniden ölçülür
    return meeting;
  }
  function leaves(root) {
    const out = []; const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    let n = root; 
    while (n) {
      if (n.childElementCount === 0) { const t = (n.innerText || n.textContent || "").trim(); if (t) out.push({ el: n, t }); }
      n = walker.nextNode();
    }
    return out;
  }
  const findTranscriptPanel = () => P.dokumPaneli(), findCaptions = () => P.altyaziKutusu();
  function parsePanel(panel) {
    const t = P.dokumOku(panel); if (t) return t;  // null: platform tanımadı → genel okuyucu (yaprak düğümler)
    const L = leaves(panel).filter(x => !SKIP_RE.test(x.t));
    const entries = []; let speaker = "?", time = "";
    for (let i = 0; i < L.length; i++) {
      const cur = L[i].t, nxt = L[i + 1] ? L[i + 1].t : null;
      if (nxt && TIME_RE.test(nxt) && cur.length < 60 && !/[.!?]$/.test(cur)) { speaker = cur; time = nxt; i++; continue; }
      if (TIME_RE.test(cur)) { time = cur; continue; }
      entries.push({ speaker, time, text: cur });
    }
    return entries;
  }
  // v0.4.8 — altyazı birinci sınıf mod (kullanıcı, 30 Eylül: döküm yetkisi olmayan toplantıda altyazıyı kendisi açabiliyor).
  // Altyazı satırının Teams'te kimliği yok; eskiden cümlenin her büyüyen hâli ayrı satır gidiyordu (~50 satır/dk).
  // Artık her altyazı düğümüne yapay kimlik (cap-<oturum>/<n>) verilir, transkriptle aynı sabitleme kullanılır:
  // son (hâlâ konuşulan) satır 2×stableMs, üstündekiler stableMs değişmezse gider. Düğüm başka bir cümleye yeniden
  // kullanılırsa (baş kısım tutmuyorsa) yeni kimlik alır.
  const capIds = new WeakMap(); const CAP_SES = Math.random().toString(36).slice(2, 8); let capN = 0;
  const norm = t => t.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, "").replace(/\s+/g, " ").trim();
  function capId(el, text) {
    const c = capIds.get(el), n = norm(text), k = c ? Math.min(8, n.length, c.head.length) : 0;
    if (c && c.head.slice(0, k) === n.slice(0, k)) { c.head = n.length > c.head.length ? n : c.head; return c.id; }
    const id = `cap-${CAP_SES}/${++capN}`; capIds.set(el, { id, head: n }); return id;
  }
  const parseCaptions = box => P.altyaziOku(box);
  P.kur({ leaves, capId });
  // Konuşma dili (v0.4.8 altyazı; v0.6.1 transkript de): konuşma dili yanlış ayarlıysa Teams metni ayarlı dilde ama
  // anlamsız döker (30 Eylül: Türkçe konuşma → İngilizce altyazı). Son gönderilen satırlarda İngilizce/Türkçe sık kelime
  // sayılır (v0.6.2: Türkçe harf oranı, aşağıda). Beklenen dille karşılaştırma aktarıcıda (agenda.json "dil"); uyarı oradan gelir.
  // v0.6.2: sık kelime sayımı anlamsız İngilizce'yi yakalamadı (1 Ekim gerçek testi: ~2 dk "karışık"). Yeni ölçüt: son
  // 60 kelimede Türkçe harf (ç ğ ı ş ö ü) içeren kelime oranı. Gerçek veride Türkçe pencereler 0,25–0,55, anlamsız
  // İngilizce 0,00–0,08 → ≥ 0,15 tr, ≤ 0,05 en, arası karisik; karar 30 kelimede (o veride uyarı ~4 satırda çıkardı).
  // v0.7.4 (Faz 2.3, ters yön): Türkçe ayarla dökülen İngilizce konuşma yarı Türkçe yarı İngilizce bozuk çıkıyor (gerçek
  // örnek: bir dökümün 12 dakikası telefonda İngilizce) — Türkçe harf oranı 0,03–0,27 dolaştı, eski ölçüt %57 "karisik",
  // %15 "en" dedi → İngilizce toplantıda uyarı hiç çıkmazdı. İkinci ölçüt: İngilizce sık kelime (the, and, you…) oranı.
  // 20 dökümde gerçek İngilizce en az 0,28 (ortanca 0,48), bozuk döküm en çok 0,12, gerçek Türkçe en çok 0,10.
  // Kural: İng. sık kelime ≥ 0,20 → en; değilse Türkçe harf ≥ 0,15 → tr; ikisi de değilse karisik (İngilizce toplantıda uyarır).
  const EN_SIK = new Set("the a an and or but to of in on at for with from by is are was were be been it its this that these those you your we our they their he she his her i me my not no yes do does did have has had will would can could should what which who when where how if so as just like about there here".split(" "));
  let capWords = []; let capEn = []; let capLang = null; let dilUyari = "";
  let langSrc = null;
  function trackLang(text, src) {
    if (src !== langSrc) { capWords = []; capEn = []; langSrc = src; } // transkript ↔ altyazı geçişinde pencere sıfırlanır
    for (const w of text.toLowerCase().split(/[^\p{L}]+/u)) if (w) { capWords.push(/[çğışöü]/.test(w)); capEn.push(EN_SIK.has(w)); }
    if (capWords.length > 60) { capWords = capWords.slice(-60); capEn = capEn.slice(-60); }
    if (capWords.length < 30) return;
    const f = capWords.filter(Boolean).length / capWords.length, e = capEn.filter(Boolean).length / capEn.length;
    capLang = e >= 0.20 ? "en" : f >= 0.15 ? "tr" : "karisik";
  }
  function flag(text) { const low = text.toLowerCase(); return cfg.keywords.filter(k => low.includes(k.toLowerCase())); }
  async function sendBatch(payload) {
    try {
      const r = await rf("/ingest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      lastOk = Date.now(); failCount = 0; return true;
    } catch (e) { failCount++; sonHata = String(e && e.message || e).slice(0, 120); return false; }
  }
  // Aktarıcı kapalıyken satırlar kuyrukta bekler (bellek içi; sekme kapanırsa kaybolur); geri gelince sırayla boşalır.
  // Aynı anda tek boşaltma (v0.3.5): send() ile ping() eşzamanlı boşaltınca aynı paket iki kez gidiyor, sonra
  // iki shift() gönderilmemiş bir paketi de siliyordu (29 Eylül gerçek testinde 48 satırdan 4'ü çift yazıldı)
  let draining = null;
  function drainQueue() {
    if (draining) return draining;
    draining = (async () => {
      let n = 0;
      while (queue.length && n < 20) { if (!(await sendBatch(queue[0]))) break; queue.shift(); n++; }
    })().finally(() => { draining = null; saveQueue(); });
    return draining;
  }
  async function send(entries, source) {
    const m = meetingInfo();
    const payload = { meeting: m, source, capturedAt: new Date().toISOString(), entries };
    queue.push(payload);
    if (queue.length > MAX_QUEUE) queue.splice(0, queue.length - MAX_QUEUE);
    await drainQueue();
    chrome.runtime.sendMessage({ type: "status", ok: failCount === 0, n: entries.length, meeting: m.title, at: lastOk, failCount, queued: queue.length }).catch(() => {});
  }
  function toast(msg, renk, ms) {  // v0.7.0: renk/süre (kanıt onayı yeşil, kısa)
    let t = document.getElementById("suflor-toast");
    if (!t) { t = document.createElement("div"); t.id = "suflor-toast"; Object.assign(t.style, { position: "fixed", top: "10px", left: "50%", transform: "translateX(-50%)", zIndex: 999999, color: "#fff", padding: "8px 16px", borderRadius: "999px", font: "13px/1.4 -apple-system,BlinkMacSystemFont,system-ui,sans-serif", boxShadow: "0 4px 14px rgba(0,0,0,.25)", maxWidth: "70vw" }); document.body.appendChild(t); }
    t.style.background = renk || "#b00020"; t.textContent = msg; t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", ms || 8000);
  }
  // v0.7.0: toplantıda mı (çağrı denetimleri görünüyor) — döküm/altyazı kapalıyken satır kaçırmamak için uyarı.
  // Seçiciler gerçek Teams'te doğrulanmadı (ayrıl düğmesi); bulunamazsa uyarı hiç çıkmaz, başka bir şey bozulmaz.
  const inCall = () => P.cagrida();
  let callSince = 0, callWarned = "";
  // v0.7.2: altyazıyı eklenti kendisi açar. Teams menüsünün data-tid'leri bilinmiyor; iki yol:
  // (1) öğrenilmiş yol — kullanıcı altyazıyı bir kez elle açınca son tıklamalar (≤ 4, 20 sn içinde, sonuncusu "altyazı"
  //     sözlü) chrome.storage.local ohCapPath'e yazılır; sonraki toplantılarda aynı adımlar aynı sırayla bulunup tıklanır.
  // (2) metinle — Diğer/More → Dil ve konuşma → Canlı altyazıyı aç. Yalnız metni bu kalıplara uyan öğeye tıklanır.
  // Güvenlik: TEHLIKE kalıbına uyan öğeye (ayrıl, sessiz, kamera, kapat, kayıt, döküm…) asla tıklanmaz; adım bulunamazsa
  // Escape ile menü kapatılır, toplantı başına tek deneme. Popup'ta kapatılabilir (cfg.autoCaptions).
  const TEHLIKE_RE = /ayrıl|leave|hang ?up|sonlandır|end (call|meeting)|sessiz|mute|mikrofon|microphone|kamera|camera|kapat|turn off|stop|durdur|kayıt|record|döküm|transcri|paylaş|share|el kaldır|raise|tepki|react|sohbet|chat|kişiler|people|participants/i;
  const ALTYAZI_RE = /altyazı|caption/i;
  const ADIMLAR = P.altyaziAdimlari || [];  // (2) metinle bulma: [seçici, metin/aria kalıbı] — platform dosyasında
  const capSiki = () => P.altyaziVar();
  const etiket = el => ((el.getAttribute("aria-label") || el.innerText || el.textContent || "").trim().replace(/\s+/g, " ")).slice(0, 80);
  const gorunur = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; };
  function tanim(el) { return { tid: el.getAttribute("data-tid") || "", id: el.id || "", role: el.getAttribute("role") || el.tagName.toLowerCase(), text: etiket(el) }; }
  let tiklar = [], capAuto = "", capTried = "", capWas = false, capBusy = false;
  document.addEventListener("click", ev => {  // öğrenme: yalnız toplantıdayken, döküm/altyazı kapalıyken
    if (window.top !== window || !inCall() || findTranscriptPanel() || capSiki()) return;
    const el = ev.target.closest && ev.target.closest('button, [role="menuitem"], [role="menuitemcheckbox"], [role="menuitemradio"], [role="button"]');
    if (!el || el.closest("#suflor-serit")) return;
    tiklar.push({ t: Date.now(), d: tanim(el) }); tiklar = tiklar.slice(-6);
  }, true);
  function ogren() {  // altyazı yeni göründü: son tıklamalar onu açtıysa yolu kaydet
    const now = Date.now(), son = tiklar.filter(k => now - k.t < 20000).slice(-4); tiklar = [];
    // v0.7.5: öğrenemezse nedeni capAuto'ya (1 Ekim 22:42 gerçek Teams: kullanıcı Tümü → Dil ve konuşma → Canlı altyazıları aç
    // tıkladı, yol kaydolmadı, neden görünmüyordu)
    const neden = !son.length ? "tık kaydı yok" : !ALTYAZI_RE.test(son[son.length - 1].d.text) ? "son tık altyazı değil"
      : son.some(k => TEHLIKE_RE.test(k.d.text) && !ALTYAZI_RE.test(k.d.text)) ? "tehlikeli öğe" : "";
    if (neden) { if (!capAuto.startsWith("acildi")) capAuto = (capAuto.split(" · öğrenme")[0] + ` · öğrenme yok: ${neden}` +
      (son.length ? ` (${son.map(k => `${k.d.role}:${k.d.text || "?"}`).join(" → ")})` : "")).slice(0, 400); return; }
    const yol = son.map(k => k.d); chrome.storage.local.set({ ohCapPath: yol }); if (!capAuto.startsWith("acildi")) capAuto = "ogrenildi " + yol.map(d => d.text).join(" → ");
    console.log("Suflor.me: altyazı yolu öğrenildi", yol);
  }
  // v0.13.10: aria-labelledby ile adlanan öğe (Teams açılır listesi: görünen metni seçili değer, adı ayrı etikette)
  const etiketBag = el => (el.getAttribute("aria-labelledby") || "").split(/\s+/).filter(Boolean).map(i => { const e = document.getElementById(i); return e ? (e.textContent || "").trim() : ""; }).join(" ");
  function bul(adim, kok) {
    let aday;
    if (adim.tid) aday = [...document.querySelectorAll(`[data-tid="${CSS.escape(adim.tid)}"]`)];
    else if (adim.id) aday = [document.getElementById(adim.id)].filter(Boolean);
    else aday = [...(kok || document).querySelectorAll(adim.sec || 'button, [role="menuitem"], [role="menuitemcheckbox"]')];
    return aday.find(el => gorunur(el) && (adim.re ? adim.re.test(etiket(el)) || adim.re.test(etiketBag(el)) : etiket(el) === adim.text) && !(TEHLIKE_RE.test(etiket(el)) && !ALTYAZI_RE.test(etiket(el)))
      && !/kapat|turn off|hide|gizle/i.test(etiket(el)));
  }
  const bekle = ms => new Promise(r => setTimeout(r, ms));
  // v0.13.10: adım {istege} bulunamazsa atlanır; {zaten} seçili değer hedefse "zaten" döner (menü kapatılır); {kap} öğenin
  // panelini hatırlar, {icinde} sonraki adımı yalnız o panelde arar. bitti: son denetim (altyazı için görünür mü; dil için yok)
  async function oynat(adimlar, bitti = capSiki) {
    let kap = null;
    for (let i = 0; i < adimlar.length; i++) {
      const a = adimlar[i], kok = a.icinde ? kap : null;
      if (a.icinde && !kap) return `adım ${i + 1}: panel bulunamadı`;
      let el = null; for (let t = 0; t < (a.istege ? 8 : 20) && !(el = bul(a, kok)); t++) await bekle(150);
      if (!el && a.istege) continue;
      if (!el) {  // v0.7.5: görünen menü öğelerini de yaz — gerçek Teams'te adın/rolün ne olduğu görülsün
        const gor = [...document.querySelectorAll('[role="menuitem"], [role="menuitemcheckbox"], [role="menuitemradio"], [role="menu"] button, [role="option"], [role="combobox"], [role="dialog"] button')]
          .filter(gorunur).map(e => `${e.getAttribute("role") || e.tagName.toLowerCase()}:${etiket(e)}`).slice(0, 10);
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        return `adım ${i + 1} bulunamadı (menüde: ${gor.length ? gor.join(" | ") : "öğe yok"})`.slice(0, 400);
      }
      if (a.kap) kap = el.closest('[role="dialog"], [role="complementary"], aside, [data-tid*="panel" i], [data-tid*="settings" i]') || el.parentElement;
      if (a.zaten && a.zaten.test(((el.value || el.innerText || el.textContent) || "").trim())) {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); return "zaten";
      }
      el.click(); await bekle(350);
    }
    if (!bitti) return "";
    for (let t = 0; t < 20; t++) { if (bitti()) return ""; await bekle(250); }
    return "tıklandı ama altyazı görünmedi";
  }
  async function altyaziAc(m) {
    if (capBusy || capTried === m || !cfg.autoCaptions) return; capBusy = true; capTried = m;
    const { ohCapPath } = await chrome.storage.local.get({ ohCapPath: null });
    let hata = ohCapPath && ohCapPath.length ? await oynat(ohCapPath) : "öğrenilmiş yol yok", yol = "öğrenilmiş";
    if (hata) { const h2 = await oynat(ADIMLAR.map(([sec, re]) => ({ sec, re }))); yol = "metinle"; hata = h2 ? `${hata}; metinle: ${h2}` : ""; }
    capAuto = hata ? "basarisiz: " + hata : "acildi (" + yol + ")"; capBusy = false;
    if (!hata) toast(L("Suflor.me: canlı altyazı açıldı"), "#1b8a3a", 4000);
    else callWarned = m, toast(L("Suflor.me: altyazıyı açamadım — bir kez elle aç ({y}), yolu öğrenirim", { y: P.yonerge.altyazi }), "#b26a00", 12000);
  }

  // v0.13.10: altyazının konuşma dili — aktarıcı "hedef" verirse (gündemde dil açıkça yazılı, agenda.json taze) altyazı
  // göründükten 4 sn sonra Teams'in dil ayarına bakılır; farklıysa hedef seçilip Güncelle'ye basılır. Toplantı başına bir
  // deneme; sonuç capAuto'ya ("dil: …") eklenir. Başarısızsa eskisi gibi dil uyarısı (dil_view) devrede kalır.
  let dilHedef = null, dilTried = "", capGorundu = 0;
  async function altyaziDili(m) {
    if (capBusy || dilTried === m || !cfg.autoCaptions || !P.dilYollari) return;
    const yollar = P.dilYollari(dilHedef); if (!yollar.length) return;
    capBusy = true; dilTried = m; const hata = [];
    let sonuc = "";
    for (const y of yollar) { const h = await oynat(y, null); if (!h || h === "zaten") { sonuc = h ? "zaten " + dilHedef : "ayarlandi " + dilHedef; break; } hata.push(h); }
    capBusy = false;
    capAuto = (capAuto.split(" · dil:")[0] + " · dil: " + (sonuc || "basarisiz: " + hata.join("; "))).slice(0, 600);
    if (sonuc.startsWith("ayarlandi")) toast(L("Suflor.me: altyazı konuşma dili {d} yapıldı (gündem dili)", { d: dilHedef === "en" ? L("İngilizce") : L("Türkçe") }), "#1b8a3a", 5000);
  }
  function dilBak() {
    if (window.top !== window || !inCall() || !capSiki()) { capGorundu = 0; return; }
    if (!dilHedef) return;
    capGorundu = capGorundu || Date.now();
    if (Date.now() - capGorundu > 4000) altyaziDili(meetingInfo().title);
  }

  // v0.8.0 Whisper: kullanıcının mikrofonu → aktarıcı (/ses, kanal "ben"; aktarıcı sessizliğe göre böler, Whisper metne çevirir).
  // Teams sayfasının mikrofon izni kullanılır (ayrı izin sorulmaz). Teams'te mikrofon kapalıyken ("Sesi aç" görünüyorsa)
  // gönderilmez. Ses diske yazılmaz; yalnız 127.0.0.1'e gider. Karşı tarafın sesi ayrı: ⌥⇧W → arka plan + offscreen.
  const mic = { on: false, busy: false, buf: [], n: 0, t0: 0, kapaliTil: 0, hata: "", gonderilen: 0 };
  let whisperView = null, karsiIpucu = "", callOnce = false;
  function olay(tur, metin) { rf("/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur, metin }) }).catch(() => {}); }
  const micDugme = () => P.micDugme(), teamsSessiz = () => P.sessizMi();  // platformun mikrofon düğmesi "Sesi aç" gösteriyor mu
  function b64(i16) { const u8 = new Uint8Array(i16.buffer, i16.byteOffset, i16.byteLength); let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); }
  async function micGonder() {
    const n = mic.n, parcalar = mic.buf, t0 = mic.t0; mic.buf = []; mic.n = 0; if (!n) return;
    const a = new Int16Array(n); let o = 0; parcalar.forEach(p => { a.set(p, o); o += p.length; });
    try {
      const r = await rf("/ses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kanal: "ben", t: t0, pcm: b64(a), meeting: meetingInfo() }) });
      const j = await r.json().catch(() => ({})); mic.gonderilen += n;
      if (j.kapali) { mic.kapaliTil = Date.now() + 600000; mic.hata = "aktarıcıda Whisper yok"; micDurdur(); }
    } catch (e) { /* aktarıcı kapalı: bu parça gider, akış sürer */ }
  }
  // Yakalama mic-main.js'te (sayfa bağlamı); burada yalnız komut, Teams sessiz denetimi ve aktarıcıya gönderim
  window.addEventListener("message", e => {
    if (e.source !== window || !e.data || window.top !== window) return;
    if (e.data.__suflor === "micPcm" && mic.on) {
      if (teamsSessiz()) { if (mic.n) micGonder(); return; }  // Teams'te mikrofon kapalı: kullanıcının odadaki sesi yazılmaz
      const i16 = new Int16Array(e.data.pcm); if (!mic.n) mic.t0 = e.data.t;
      mic.buf.push(i16); mic.n += i16.length; if (mic.n >= 16000) micGonder();
    }
    if (e.data.__suflor === "micDurum") {
      mic.busy = false;
      if (e.data.on) { mic.on = true; mic.hata = ""; const d = micDugme(); olay("whisper-mic", `açıldı (bağlam ${e.data.state}; mikrofon düğmesi: ${d ? (d.getAttribute("aria-label") || d.getAttribute("data-tid") || "?") : "bulunamadı"})`); }
      else if (e.data.hata) { mic.hata = e.data.hata; mic.kapaliTil = Date.now() + 60000; olay("whisper-mic", "açılamadı: " + mic.hata); }
    }
  });
  function micBaslat() {
    if (mic.on || mic.busy || Date.now() < mic.kapaliTil) return;
    mic.busy = true; setTimeout(() => { mic.busy = false; }, 15000);  // izin penceresi/yanıt gelmezse yeniden denensin
    window.postMessage({ __suflor: "mic", komut: "basla" }, "*");
  }
  function micDurdur(sessiz) {
    if (mic.on) window.postMessage({ __suflor: "mic", komut: "dur" }, "*");
    if (mic.on && !sessiz) olay("whisper-mic", "kapandı");
    Object.assign(mic, { on: false, buf: [], n: 0 });
  }
  function whisperTick() {
    if (window.top !== window) return;
    const call = inCall();
    if (cfg.enabled && cfg.whisper && call && !(whisperView && whisperView.durum === "yok")) micBaslat(); else if (mic.on) micDurdur();
    if (callOnce && !call) chrome.runtime.sendMessage({ type: "whisperKarsiDur" }).catch(() => {});  // toplantıdan çıkınca karşı kanal da kapansın
    callOnce = call;
    dilBak();  // v0.13.10
  }
  setInterval(whisperTick, 2000);
  function captureHint(panel, caps) {
    if (window.top !== window) return;
    const siki = capSiki(); if (siki && !capWas) ogren(); capWas = siki;
    if (!inCall() && !capBusy) capTried = dilTried = "";  // toplantıdan çıkıp yeniden girince yeniden dener
    if (!inCall() || panel || siki) { callSince = 0; return; }  // gevşek findCaptions menüdeki "altyazı" öğesini de sayar
    callSince = callSince || Date.now(); const m = meetingInfo().title;
    if (Date.now() - callSince > 12000) altyaziAc(m);
    if (Date.now() - callSince > 45000 && !caps && callWarned !== m) { callWarned = m; toast(L("Suflor.me: toplantıdasın ama döküm/altyazı kapalı — satır kaydedilmiyor. ") + P.yonerge.altyazi, "#b26a00", 15000); }
  }
  function tick() {
    if (!cfg.enabled) return;
    let entries = [], source = "";
    const panel = findTranscriptPanel();
    if (panel) { entries = parsePanel(panel); source = "transcript"; }
    if (!panel) { const cap = findCaptions(); if (cap) { entries = parseCaptions(cap); source = "captions"; } }
    // v0.7.2: panel/altyazı kapanınca (ya da kaynak değişince) sabitlenmeyi bekleyen son satırlar kaybolmasın —
    // 1 Ekim testi: Teams dökümünün son satırı ("Bitiriyorum görüşmek üzere.") Suflor'da yoktu.
    if (lastSrc && source !== lastSrc) {
      const kalan = [], now = Date.now();
      pending.forEach((v, id) => { if (v.e && v.src === lastSrc && now - v.since < 120000 && sentById.get(id) !== v.text) {
        const e = Object.assign({}, v.e); if (sentById.has(id)) e.revised = true; delete e.last;
        e.seen = new Date(v.seen).toISOString(); e.chg = new Date(v.since).toISOString(); e.stableMs = 0; e.flush = true;
        sentById.set(id, v.text); kalan.push(e); } });
      if (kalan.length) send(kalan, lastSrc);
    }
    lastSrc = source;
    if (!entries.length) return;
    const fresh = [], taslak = [];
    entries.forEach((e, idx) => {
      if (e.id) {
        const need = source === "captions" && e.last ? 2 * (+cfg.stableMs || 3000) : (+cfg.stableMs || 3000);
        // Teams canlı dökümde son cümle konuşurken değişir: metin stableMs boyunca değişmediyse gönder (v0.4.6:
        // eskiden 3 sn'lik iki tur aynı olmalıydı → 3–6 sn; şimdi 1 sn'de bir bakılıyor → stableMs + ≤1 sn).
        // seen/chg: ilk görülme ve son değişme anı — gecikme ölçümü için dosyaya yazılır
        const now = Date.now(), prev = pending.get(e.id);
        if (!prev || prev.text !== e.text) { pending.set(e.id, { text: e.text, since: now, seen: prev ? prev.seen : now, e, src: source }); taslak.push({ id: e.id, speaker: e.speaker, text: e.text, idx, n: entries.length }); return; }
        if (now - prev.since < need) { taslak.push({ id: e.id, speaker: e.speaker, text: e.text, idx, n: entries.length }); return; }
        const sentText = sentById.get(e.id);
        if (sentText === e.text) return;
        if (sentText !== undefined) e.revised = true;
        e.seen = new Date(prev.seen).toISOString(); e.chg = new Date(prev.since).toISOString(); e.stableMs = need; delete e.last;
        sentById.set(e.id, e.text); fresh.push(e); trackLang(e.text, source); return;
      }
      const key = e.time + "|" + e.speaker + "|" + e.text + "|" + (entries.slice(0, idx).filter(x => x.time === e.time && x.text === e.text).length);
      if (!sentKeys.has(key)) { sentKeys.add(key); fresh.push(e); }
    });
    taslakGonder(taslak, source);
    if (pending.size > 3000) { const old = Date.now() - 600000; pending.forEach((v, k) => { if (v.since < old) pending.delete(k); }); }
    if (!fresh.length) return;
    fresh.forEach(e => { const f = flag(e.text); if (f.length) { e.flags = f; toast(L("⚠ Ekranda/konuşmada hassas ifade: ") + f.join(", ") + " — " + e.text.slice(0, 60)); chrome.runtime.sendMessage({ type: "flag", text: e.text, flags: f }).catch(() => {}); } });
    send(fresh, source);
  }
  // v0.8.1: taslak — sabitlenmeyi bekleyen (hâlâ konuşulan) satırın o anki hâli /taslak'a gider; pano soluk gösterir,
  // kesin satır (sabitlenmiş Teams satırı ya da Whisper) gelince aktarıcı siler. Kuyruğa girmez: kaybolursa önemsiz.
  let taslakSig = "";
  function taslakGonder(list, source) {
    // yalnız son 3 satır: panel ilk açıldığında görünen eski satırların hepsi "yeni" sayılır, taslak olmamalı
    const ents = list.filter(e => e.text && e.idx >= e.n - 3 && sentById.get(e.id) !== e.text).map(e => ({ id: e.id, speaker: e.speaker || "?", text: e.text }));
    const sig = JSON.stringify(ents); if (!ents.length || sig === taslakSig) return; taslakSig = sig;
    rf("/taslak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ meeting: meetingInfo(), source, entries: ents }) }).catch(() => {});
  }
  let lastSrc = "";
  setInterval(tick, 1000); // v0.4.6: 3 sn → 1 sn (sabitleme süresi ayrı: cfg.stableMs)
  // v0.9.6: nabız kuyruğu beklemez (boşaltma takılırsa nabız da susuyordu); arka plan servis çalışanı da 30 sn'de bir
  // "nabiz" mesajıyla ping() çağırır — Chrome arka plandaki sekmenin zamanlayıcılarını kısarsa mesaj yine işlenir.
  // Gövdede kim (zamanlayici|arka-plan) ve sekme görünürlüğü: aktarıcı 30 sn'yi aşan boşlukları bununla günlüğe yazar.
  let pingSon = 0;
  async function ping(kim = "zamanlayici") {
    if (!cfg.enabled) return;
    if (kim !== "zamanlayici" && Date.now() - pingSon < 8000) return;  // zamanlayıcı yeni attıysa tekrar etme
    pingSon = Date.now();
    if (queue.length) drainQueue(); // yeni satır gelmese de kuyruğu boşaltmayı dene
    const panel = findTranscriptPanel();
    const caps = !!findCaptions(); captureHint(panel, caps); if (queue.length) saveQueue(); else adoptQueues(); // v0.7.0
    const body = { ver: chrome.runtime.getManifest().version, meeting: meetingInfo(), panel: !!panel, rows: panel ? P.dokumSatirSayisi(panel) : 0, platform: P.ad, yonerge: P.yonerge, captions: caps, call: window.top === window ? inCall() : false, lang: capLang, langSrc, capAuto, sent: sentById.size + sentKeys.size, at: new Date().toISOString(), kim, vis: document.visibilityState, mic: window.top === window ? { on: mic.on, sessiz: mic.on && teamsSessiz(), hata: mic.hata || "" } : null };
    try { const r = await rf("/ping", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (r.ok) { lastOk = Date.now(); failCount = 0; } }
    catch (e) { failCount++; }
    chrome.runtime.sendMessage({ type: "status", ok: failCount === 0, panel: !!panel, call: body.call, meeting: body.meeting.title, at: lastOk, failCount, queued: queue.length }).catch(() => {});
  }
  setInterval(() => ping(), 10000); setTimeout(() => ping(), 1500);
  // Popup'tan gelen "not" ve "durum" istekleri
  chrome.runtime.onMessage.addListener((msg, _s, reply) => {
    if (msg.type === "nabiz") { ping("arka-plan"); reply({ ok: true, vis: document.visibilityState }); return; }  // v0.9.6
    if (msg.type === "note") { rf("/note", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ meeting: meetingInfo(), text: msg.text, at: new Date().toISOString() }) }).then(() => reply({ ok: true })).catch(e => reply({ ok: false, err: String(e) })); return true; }
    // v0.7.0 kanıt: arka plan betiği çekmeden önce şeridi/uyarıyı gizletir (görüntüye girmesin), sonra geri açtırır
    if (msg.type === "kanitHazirla") {
      if (window.top !== window) return;
      document.querySelectorAll("#suflor-serit, #suflor-toast").forEach(e => { e.dataset.sfDisp = e.style.display; e.style.display = "none"; });
      requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(() => reply({ meeting: meetingInfo(), w: innerWidth, h: innerHeight }), 30))); return true;
    }
    if (msg.type === "bilgi") { if (window.top === window) toast(msg.text, msg.renk || "#1b6ef3", msg.ms || 5000); return; }  // v0.8.0
    if (msg.type === "kanitBitti") {
      if (window.top !== window) return;
      document.querySelectorAll("#suflor-serit, #suflor-toast").forEach(e => { e.style.display = e.dataset.sfDisp || ""; });
      if (msg.ok) toast(L("📷 Kanıt {n} kaydedildi", { n: msg.n || "" }), "#1b8a3a", 2000); else if (msg.ok === false) toast(L("📷 Kanıt kaydedilemedi: ") + (msg.err || L("bilinmiyor"))); // null: yalnız şeridi geri aç
      return;
    }
    if (msg.type === "getStatus") { reply({ alan: { bekliyor: alanBekliyor, secili: alanSecili, relay: cfg.relay, sonHata }, meeting: meetingInfo().title, lastOk, failCount, sent: sentById.size + sentKeys.size, queued: queue.length, panel: !!findTranscriptPanel(), captions: !!findCaptions(), lang: capLang, langSrc, dilUyari,
      whisper: { mic: mic.on, sessiz: mic.on && teamsSessiz(), hata: mic.hata, durum: whisperView && whisperView.durum, karsi: !!(whisperView && whisperView.karsi), satir: whisperView && whisperView.satir } }); }
  });
  // --- Claude şeridi (v0.4.0) -------------------------------------------------------------------------------
  // Teams sayfasının sol altında küçük hap: "◆ Suflor.me · N". Üzerine gelince kartlar açılır, ✓/✕ ile kapatılır.
  // DEĞİNME ve DUYGU kartlarının metni burada gösterilmez (Teams sekmesi paylaşılırsa görünmesin); ⌥⇧H şeridi gizler/açar.
  if (window.top === window) {
    const KL = { sor: "Sor", belirt: "Belirt", deginme: "Değinme", dikkat: "Dikkat", cevap: "Cevap", bilgi: "Bilgi", duygu: "Duygu" };  // gösterirken L()
    const COL = { dikkat: "#c0503b", sor: "#1f7a5a", belirt: "#b0832e", cevap: "#2a8590", deginme: "#7a5fb0", bilgi: "#8b938d", duygu: "#b25a78" }; // v0.11.3: marka paleti (pano ile aynı türler; iki temada okunur ara tonlar)
    const PRI = ["dikkat", "sor", "belirt", "cevap", "deginme", "duygu", "bilgi"];
    const PRIVATE = ["deginme", "duygu"]; // metni şeritte gösterilmez: Teams sekmesi paylaşılırsa görünmesin
    let hidden = false, host = null, root = null, sig = "", first = true; const seen = new Set();
    chrome.storage.local.get({ ohHidden: false }, v => { hidden = !!v.ohHidden; });
    function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
    function ensure() {
      if (host && host.isConnected) return;
      host = el("div"); host.id = "suflor-serit";
      Object.assign(host.style, { position: "fixed", left: "12px", bottom: "12px", zIndex: 999998 });
      root = host.attachShadow({ mode: "open" });
      // v0.9.1: sade görünüm — beyaz/koyu yüzey, ince kenar, tek renkli durum noktası; kart türü yalnız sol çizgi ve etiket rengiyle
      const st = el("style"); st.textContent = `
        .w{font:13px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",system-ui,sans-serif;color:#18201c;
          --s1:#fff;--s2:#f9faf7;--tx:#18201c;--t2:#5c655f;--t3:#8b938d;--bd:rgba(24,32,28,.11);--bd2:rgba(24,32,28,.2);--hov:rgba(24,32,28,.05)}
        @media (prefers-color-scheme:dark){.w{color:#ecebe7;--s1:#171d1a;--s2:#1b221e;--tx:#e8ebe6;--t2:#a5ada7;--t3:#78807a;--bd:rgba(232,235,230,.1);--bd2:rgba(232,235,230,.2);--hov:rgba(232,235,230,.07)}}
        .pill{display:inline-flex;align-items:center;gap:7px;background:var(--s1);color:var(--tx);border:1px solid var(--bd2);border-radius:999px;padding:5px 12px 5px 10px;
          box-shadow:0 2px 8px rgba(0,0,0,.18);cursor:default;user-select:none;font-size:12px;white-space:nowrap}
        .pill i{width:8px;height:8px;border-radius:50%;background:var(--pc,#8c8b85);flex:none}.pill b{font-weight:600}.pill .m{color:var(--t2)}.pill .c{color:var(--pc,var(--t2));font-weight:500}
        .list{display:none;width:340px;max-height:58vh;overflow:auto;background:var(--s2);border:1px solid var(--bd2);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.22);padding:8px;margin-bottom:8px}
        .w:hover .list{display:block}
        .k{position:relative;background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:8px 10px 8px 12px;margin:0 0 6px;overflow:hidden;color:var(--tx)}
        .k::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--kc,#8c8b85)}
        .k b{display:block;font-size:11px;font-weight:600;letter-spacing:.03em;color:var(--kc,#8c8b85);margin-bottom:1px}
        .why{font-size:12px;color:var(--t2);margin-top:2px}.a{margin-top:6px;display:flex;gap:4px}
        button{font:11px/1.4 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;color:var(--t2);background:transparent;border:1px solid transparent;border-radius:6px;padding:2px 7px;cursor:pointer}
        button:hover{background:var(--hov);color:var(--tx)}button:disabled{opacity:.6}
        .q{font-size:12px;color:var(--t2);padding:4px 2px}.hint{font-size:11px;color:var(--t3);padding:2px 2px 0}
        .top{display:flex;justify-content:space-between;align-items:center;gap:6px;margin:0 0 6px;font-size:12px;color:var(--t2)}.top button{border-color:var(--bd2)}
        .yeni{animation:p 1s 3}@keyframes p{0%{box-shadow:0 0 0 0 rgba(47,111,214,.75)}100%{box-shadow:0 0 0 12px rgba(47,111,214,0)}}`;
      const w = el("div", "w"); w.append(el("div", "list"), el("div", "pill"));
      root.append(st, w); document.body.appendChild(host);
      root.addEventListener("click", ev => {
        // v0.6.0: "Son 1 dk" — Claude son dakikanın kısa özetini CEVAP kartı olarak gönderir
        const kz = ev.target.closest("button[data-kanit]"); // v0.7.0
        if (kz) { chrome.runtime.sendMessage({ type: "kanit", kaynak: "serit" }).catch(() => {}); return; }
        const o = ev.target.closest("button[data-ozet]");
        if (o) { o.disabled = true; o.textContent = L("istendi…"); rf("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "ozet" }) }).then(pollCards).catch(() => {}); return; }
        const b = ev.target.closest("button[data-ack]"); if (!b) return; b.disabled = true;
        rf("/card-ack", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: b.dataset.id, status: b.dataset.ack }) }).then(pollCards).catch(() => {});
      });
    }
    // v0.6.0: toplantıdayken (transkript paneli ya da altyazı açık) kart olmasa da şerit görünür — "Son 1 dk" düğmesi
    // ve kalan süre için. Toplantı dışındaki Teams sayfalarında eskisi gibi yalnız kart/uyarı varken.
    function inMeeting() { return !!(findTranscriptPanel() || capSiki()); }
    let kanitSon = null, komutSon;  // v0.8.3: sesli komut onayı (ilk yoklamada eski komut gösterilmez)
    function paint(v) {
      // v0.7.0: panodan/mini panodan kanıt istendi — toplantıdaki sekme çeker (çift isteği aktarıcı ayıklar). v0.8.6: arkadaysa
      // da ister; arka plan sekmeyi bir an öne getirip çeker (2 Ekim: pano aynı penceredeyken kanıt düşüyordu)
      if (v.kanit_iste && v.kanit_iste.id !== kanitSon) { kanitSon = v.kanit_iste.id; if (window.top === window && (inMeeting() || inCall())) chrome.runtime.sendMessage({ type: "kanit", kaynak: v.kanit_iste.kaynak || "pano", istek: v.kanit_iste.id, not: v.kanit_iste.not }).catch(() => {}); }
      if (v.komut && v.komut.id !== komutSon) { if (komutSon !== undefined && window.top === window) toast(v.komut.metin, "#0a8f5a", 3500); komutSon = v.komut.id; }
      else if (!v.komut && komutSon === undefined) komutSon = null;
      // v0.8.0: Whisper durumu; karşı tarafın sesi henüz verilmediyse toplantı başına bir kez ⌥⇧W hatırlatması
      whisperView = v.whisper || null;
      // v0.13.0: yerel ses yardımcısı açıksa (bekliyor/dinliyor) karşı sesi o alır — hatırlatma yok
      if (whisperView && cfg.whisper && whisperView.durum !== "yok" && inCall() && !whisperView.karsi && !["bekliyor", "dinliyor"].includes(whisperView.yerel) && karsiIpucu !== meetingInfo().title) {
        karsiIpucu = meetingInfo().title; toast(L("Suflor.me Whisper: senin sesin yazılıyor. Karşı tarafın sesi için bir kez Option + Shift + W'ye bas (ya da Suflor.me simgesi → Karşı taraf)"), "#1b6ef3", 12000);
      }
      const cards = v.cards || [], qs = v.questions || [], live = inMeeting();
      const warn = v.uyari || ""; // v0.4.9: disk dolu / az yer — kart olmasa da şerit görünür
      const dil = (v.dil && v.dil.uyari) || ""; // v0.6.1: konuşma dili beklenenden farklı
      dilHedef = (v.dil && v.dil.hedef) || null;  // v0.13.10
      if (dil && dil !== dilUyari) toast("⚠ " + dil); dilUyari = dil;
      if (hidden || !document.body || (!cards.length && !qs.length && !warn && !dil && !live)) { if (host) host.style.display = "none"; return; }
      ensure(); host.style.display = "block";
      const sv = v.sure, kal = sv ? sv.kalan_dk : null;
      const sure = sv ? (kal > 0 ? L("⏱ {n} dk", { n: kal }) : kal === 0 ? L("⏱ süre doldu") : L("⏱ +{n} dk", { n: -kal })) + (sv.kayma >= 2 ? L(" · {n} madde geride", { n: sv.kayma }) : "") : "";
      const sureKisa = sv ? (kal > 0 ? L("{n} dk kaldı", { n: kal }) : kal === 0 ? L("süre doldu") : L("+{n} dk", { n: -kal })) : "";  // haptaki kısa biçim
      const s = JSON.stringify([cards.map(c => c.id), qs.map(q => q.id), warn, dil, sure, live, v.kanit_n, DIL]); if (s === sig) return; sig = s;
      const top = PRI.find(k => cards.some(c => c.kind === k)) || "bilgi";
      const pill = root.querySelector(".pill"), list = root.querySelector(".list");
      // v0.9.1: hap = durum noktası + "Suflor" + kart sayısı (en önemli kartın renginde) + bekleyen soru, kanıt, kalan süre
      const pc = (warn || dil) ? COL.dikkat : cards.length ? COL[top] : (kal != null && (kal <= 5 || sv.kayma >= 2)) ? "#c08a2a" : (live ? "#1f7a4f" : "#8b938d");
      pill.style.setProperty("--pc", pc); pill.replaceChildren(el("i"), el("b", null, "Suflor.me"));
      const parca = [];
      if (warn) parca.push(["c", L("⚠ disk")]); if (dil) parca.push(["c", L("⚠ dil")]);
      if (cards.length) parca.push(["c", L(cards.length === 1 ? "1 kart" : "{n} kart", { n: cards.length })]); if (qs.length) parca.push(["m", L(qs.length === 1 ? "1 soru bekliyor" : "{n} soru bekliyor", { n: qs.length })]);
      if (v.kanit_n) parca.push(["m", `📷 ${v.kanit_n}`]); if (sureKisa) parca.push(["m", sureKisa]);
      parca.forEach(([k, t]) => pill.append(el("span", k, "· " + t)));
      const fresh = cards.some(c => !seen.has(c.id)); cards.forEach(c => seen.add(c.id));
      if (fresh && !first) { pill.classList.remove("yeni"); void pill.offsetWidth; pill.classList.add("yeni"); }
      first = false; list.replaceChildren();
      { const t = el("div", "top"), b = el("button", null, L("Son 1 dk özeti")); b.dataset.ozet = "1"; b.title = L("Claude son dakikayı 1–2 cümleyle özetlesin");
        const kz = el("button", null, L("📷 Kanıt")); kz.dataset.kanit = "1"; kz.title = L("{p} ekranını kanıt olarak kaydet (klavye: Option + Shift + K)", { p: P.etiket });
        const sg = el("span"); sg.append(kz, document.createTextNode(" "), b);
        t.append(el("span", null, sure || ""), sg); list.append(t); }
      if (dil) { const k = el("div", "k", "⚠ " + dil); k.style.setProperty("--kc", COL.dikkat); list.append(k); }
      if (warn) { const k = el("div", "k", "⚠ " + warn); k.style.setProperty("--kc", COL.dikkat); list.append(k); }
      cards.forEach(c => {
        const k = el("div", "k"); k.style.setProperty("--kc", COL[c.kind] || COL.bilgi);
        k.append(el("b", null, L(KL[c.kind] || "Bilgi")));
        if (PRIVATE.includes(c.kind)) k.append(el("span", "hint", L("metin yalnız mini panoda / panoda")));
        else { k.append(document.createTextNode(c.text)); if (c.why) k.append(el("div", "why", c.why)); }
        const a = el("div", "a");
        // v0.4.4: üç düğme; BİLGİ/CEVAP/DUYGU'da "yaptım" yok
        [["yapildi", "✓ Yaptım", "Önerileni yaptım"], ["okundu", "Okudum", "Gördüm, kapat (reddetmiyorum)"], ["gecildi", "✕ Gerek yok", "Bu konu gereksiz; Claude bir daha önermesin"]]
          .filter(([st]) => st !== "yapildi" || !["bilgi", "cevap", "duygu"].includes(c.kind))
          .forEach(([st, lbl, tip]) => { const x = el("button", null, L(lbl)); x.dataset.ack = st; x.dataset.id = c.id; x.title = L(tip); a.append(x); });
        k.append(a); list.append(k);
      });
      qs.forEach(q => list.append(el("div", "q", "⏳ " + (q.tur === "ozet" ? L("Son 1 dk özeti hazırlanıyor…") : L("Claude'a soruldu: ") + q.text))));
      list.append(el("div", "hint", L("Option + Shift + H: şeridi gizle · Option + Shift + K: kanıt · Option + Shift + S: önemli an · Option + Shift + O: son 1 dk")));
    }
    async function pollCards() {
      if (!cfg.enabled) { if (host) host.style.display = "none"; return; }
      try { const r = await rf("/cards"); if (r.ok) paint(await r.json()); } catch (e) { /* aktarıcı kapalı: şerit değişmez */ }
    }
    window.addEventListener("keydown", ev => {
      if (ev.altKey && ev.shiftKey && ev.code === "KeyH") {
        hidden = !hidden; chrome.storage.local.set({ ohHidden: hidden }); sig = "";
        toast(L(hidden ? "Claude şeridi gizlendi (Option + Shift + H ile geri aç)" : "Claude şeridi açık")); pollCards();
      }
    }, true);
    setInterval(pollCards, 3000); setTimeout(pollCards, 1000);
  }
  setTimeout(adoptQueues, 3000); // v0.7.0: önceki sekmeden kalan bekleyen satırlar
  log("yüklendi");
})();
