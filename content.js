// Suflor.me — içerik betiği (content script)
// Toplantı sayfasındaki transkript ve canlı altyazı panelini izler, yeni satırları yerel aktarıcıya gönderir.
// platformdan bağımsız çekirdek. Sayfaya özgü seçiciler ve metinler platform dosyasında (platform-teams.js …),
// manifest onu bu dosyadan önce yükler ve globalThis.SuflorPlatform olarak verir; arayüz platform-teams.js başında.
(() => {
  if (window.__ohCanliLoaded) return; window.__ohCanliLoaded = true;
  const P = globalThis.SuflorPlatform; if (!P) return;  // platform dosyası yüklenmedi: bu sayfada Suflor.me çalışmaz
  const TIME_RE = /^\d{1,2}:\d{2}(:\d{2})?$/;
  const SKIP_RE = P.SKIP_RE || /^$/;
  // (güvenlik denetimi O3) aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
  const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
  function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
  let cfg = { relay: RELAY_VARSAYILAN, enabled: true, stableMs: 3000, autoCaptions: true, whisper: true };
  let sentKeys = new Set(); const pending = new Map(); const sentById = new Map(); let lastPanelSig = ""; let meeting = null; let lastOk = 0; let failCount = 0;
  const MAX_QUEUE = 500; let queue = []; // aktarıcıya ulaşamayınca bekleyen gönderim paketleri
  // kuyruk chrome.storage.local'da da tutulur — Teams sekmesi yenilenir/kapanırsa bekleyen satırlar kaybolmaz.
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
  // arayüz dili (tr/en) — şerit, toast'lar, kart düğmeleri. Kaynak aktarıcının /status "arayuz_dili" alanı (dakikada bir
  // okunur), chrome.storage.local "dil"de saklanır; yoksa "tr". Anahtar Türkçe metnin kendisi, terimler panoyla aynı.
  // Aktarıcıya giden metinler (/olay, /komut) ve Claude'un kart metinleri çevrilmez.
  let DIL = "tr";
  const EN = globalThis.SUFLOR_EN || {};
  const L = (s, v) => { let t = DIL === "en" && EN[s] || s; if (v) for (const k in v) t = t.split("{" + k + "}").join(v[k]); return t; };
  function dilAyarla(d) { DIL = d === "en" ? "en" : "tr"; P.dil = DIL; }
  try { chrome.storage.local.get({ dil: "tr" }, v => dilAyarla(v.dil)); } catch (e) {}

  // aktarıcı adresi yalnız bu tarayıcıda (storage.local) — iki macOS hesabının Chrome'u aynı Google hesabıyla eşitlenirse
  // adres karşı hesaba geçmesin (iki aktarıcı aynı anda açık, ikisine de 127.0.0.1'den ulaşılır). Eski sync değeri yalnız yedek.
  // Seçim yoksa bu Mac'teki aktarıcılar yoklanır (8765–8768). Birden fazlaysa seçim yapılana kadar HİÇBİR ŞEY gönderilmez (satırlar
  // kuyrukta bekler) ve bir kez uyarılır. v0.13.5: tek aktarıcı varsa o "kendiliğinden" (relayOto) kaydedilir — önceden kaydedilmiyordu ve
  // aynı Mac'e ikinci hesap kurulunca ilk hesabın Chrome'u sessizce göndermeyi bırakıyordu (5 Ekim). Sonradan ikinci alan belirirse
  // gönderim sürer, bir kez "bu Chrome X alanına yazıyor; değiştirmek için simgeye tıkla" denir.
  let alanBekliyor = false, alanSecili = false, alanUyarildi = false, sonHata = "";
  async function alanKesfet() {  // 401 de aktarıcıdır (v0.14 anahtar ister) — background.js relayAdr ile aynı
    if (alanSecili) return;
    const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok || r.status === 401 ? `http://127.0.0.1:${p}` : null; } catch (e) { return null; } }))).filter(Boolean);
    alanBekliyor = bul.length > 1;
    if (bul.length === 1) { cfg.relay = bul[0]; alanSecili = true; chrome.storage.local.set({ relay: bul[0], relayOto: true }); }
    if (alanBekliyor && !alanUyarildi && window.top === window) { alanUyarildi = true; toast(L("Çalışma alanını seç: Suflor.me simgesi"), "#b26a00", 15000); }
  }
  // v0.14.0: yerel anahtar yardımcısı varsa bu kullanıcının aktarıcısı odur — yoklama ve alan seçimi gerekmez. Adres belli olana
  // kadar istekler bekler (en çok 3 sn): ilk satırlar varsayılan porttaki başka hesabın aktarıcısına gitmesin.
  let hazirCoz; const hazir = new Promise(r => { hazirCoz = r; setTimeout(r, 3000); });
  chrome.storage.sync.get(cfg, v => { cfg = Object.assign(cfg, v); globalThis.SuflorAnahtar.al().then(k => {
    if (k) { cfg.relay = `http://127.0.0.1:${k.port}`; alanSecili = true; alanBekliyor = false; return hazirCoz(); }
    chrome.storage.local.get({ relay: null, relayOto: false }, l => { if (l.relay) { cfg.relay = l.relay; alanSecili = true; hazirCoz(); if (l.relayOto) otoDenetle(); } else alanKesfet().finally(hazirCoz); }); }); });
  async function otoDenetle() {  // kendiliğinden seçilmiş alan + bu Mac'te başka alan var → bir kez bilgi (gönderim durmaz)
    if (window.top !== window) return;
    const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok || r.status === 401 ? Object.assign({ port: p }, await r.json().catch(() => ({}))) : null; } catch (e) { return null; } }))).filter(Boolean);
    if (bul.length < 2) return;
    const { relayOtoUyari } = await chrome.storage.local.get({ relayOtoUyari: false }); if (relayOtoUyari) return;
    const su = bul.find(s => cfg.relay && cfg.relay.endsWith(":" + s.port)); chrome.storage.local.set({ relayOtoUyari: true });
    toast(L("Bu Chrome \"{a}\" alanına yazıyor", { a: (su && su.alan) || cfg.relay }), "#b26a00", 8000);
  }
  setInterval(alanKesfet, 30000);
  chrome.storage.onChanged.addListener((ch, alan) => {
    for (const k in ch) if (!(k === "relay" && alan === "sync")) cfg[k] = ch[k].newValue;
    if (alan === "local" && ch.relay && ch.relay.newValue) { alanSecili = true; alanBekliyor = false; }
    if (alan === "local" && ch.dil) dilAyarla(ch.dil.newValue);  // popup ya da başka sekme dili güncelledi
  });
  // her istek en çok 8 sn bekler — 3 Ekim denemesinde nabız ~7 dk kesildi, mikrofon sesi akmaya devam etti; zaman aşımı
  // olmayan bir istek takılırsa onu bekleyen her şey (nabız → kuyruk boşaltma) de takılıyordu
  const rf = (yol, o) => hazir.then(() => alanBekliyor ? Promise.reject(new Error("çalışma alanı seçilmedi")) : fetch((relayGecerli(cfg.relay) || RELAY_VARSAYILAN) + yol, Object.assign({ signal: AbortSignal.timeout(8000) }, o)));
  // arayüz dilini aktarıcıdan oku (yalnız üst çerçeve, dakikada bir); değişince storage.local "dil" — diğer sekmeler ve
  // popup onChanged ile alır. Alan yoksa (eski aktarıcı) "tr".
  async function dilOku() {
    if (window.top !== window) return;
    try { const j = await (await rf("/status")).json(); const d = j.arayuz_dili === "en" ? "en" : "tr"; if (d !== DIL) { dilAyarla(d); chrome.storage.local.set({ dil: d }); } } catch (e) {}
  }
  setTimeout(dilOku, 2000); setInterval(dilOku, 60000);

  function meetingInfo() {
    const title = P.toplantiAdi();
    if (!meeting || meeting.title !== title) { meeting = { title, startedAt: new Date().toISOString(), url: location.origin, platform: P.ad }; capWords = []; capEn = []; capLang = null; } // yeni toplantıda dil yeniden ölçülür
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
  // altyazı birinci sınıf mod (kullanıcı, 30 Eylül: döküm yetkisi olmayan toplantıda altyazıyı kendisi açabiliyor).
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
  // sık kelime sayımı anlamsız İngilizce'yi yakalamadı (1 Ekim gerçek testi: ~2 dk "karışık"). Yeni ölçüt: son
  // 60 kelimede Türkçe harf (ç ğ ı ş ö ü) içeren kelime oranı. Gerçek veride Türkçe pencereler 0,25–0,55, anlamsız
  // İngilizce 0,00–0,08 → ≥ 0,15 tr, ≤ 0,05 en, arası karisik; karar 30 kelimede (o veride uyarı ~4 satırda çıkardı).
  // Türkçe ayarla dökülen İngilizce konuşma yarı Türkçe yarı İngilizce bozuk çıkıyor (gerçek
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
  function toast(msg, renk, ms) {  // renk/süre (kanıt onayı yeşil, kısa)
    let t = document.getElementById("suflor-toast");
    if (!t) { t = document.createElement("div"); t.id = "suflor-toast"; Object.assign(t.style, { position: "fixed", top: "10px", left: "50%", transform: "translateX(-50%)", zIndex: 999999, color: "#fff", padding: "8px 16px", borderRadius: "999px", font: "13px/1.4 -apple-system,BlinkMacSystemFont,system-ui,sans-serif", boxShadow: "0 4px 14px rgba(0,0,0,.25)", maxWidth: "70vw" }); document.body.appendChild(t); }
    t.style.background = renk || "#b00020"; t.textContent = msg; t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", ms || 8000);
  }
  // toplantıda mı (çağrı denetimleri görünüyor) — döküm/altyazı kapalıyken satır kaçırmamak için uyarı.
  // Seçiciler gerçek Teams'te doğrulanmadı (ayrıl düğmesi); bulunamazsa uyarı hiç çıkmaz, başka bir şey bozulmaz.
  const inCall = () => P.cagrida();
  let callSince = 0, callWarned = "";
  // altyazıyı eklenti kendisi açar. Teams menüsünün data-tid'leri bilinmiyor; iki yol:
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
    // öğrenemezse nedeni capAuto'ya (1 Ekim 22:42 gerçek Teams: kullanıcı Tümü → Dil ve konuşma → Canlı altyazıları aç
    // tıkladı, yol kaydolmadı, neden görünmüyordu)
    const neden = !son.length ? "tık kaydı yok" : !ALTYAZI_RE.test(son[son.length - 1].d.text) ? "son tık altyazı değil"
      : son.some(k => TEHLIKE_RE.test(k.d.text) && !ALTYAZI_RE.test(k.d.text)) ? "tehlikeli öğe" : "";
    if (neden) { if (!capAuto.startsWith("acildi")) capAuto = (capAuto.split(" · öğrenme")[0] + ` · öğrenme yok: ${neden}` +
      (son.length ? ` (${son.map(k => `${k.d.role}:${k.d.text || "?"}`).join(" → ")})` : "")).slice(0, 400); return; }
    const yol = son.map(k => k.d); chrome.storage.local.set({ ohCapPath: yol }); if (!capAuto.startsWith("acildi")) capAuto = "ogrenildi " + yol.map(d => d.text).join(" → ");
    console.log("Suflor.me: altyazı yolu öğrenildi", yol);
  }
  // aria-labelledby ile adlanan öğe (Teams açılır listesi: görünen metni seçili değer, adı ayrı etikette)
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
  // adım {istege} bulunamazsa atlanır; {zaten} seçili değer hedefse "zaten" döner (menü kapatılır); {kap} öğenin
  // panelini hatırlar, {icinde} sonraki adımı yalnız o panelde arar. bitti: son denetim (altyazı için görünür mü; dil için yok)
  async function oynat(adimlar, bitti = capSiki) {
    let kap = null;
    for (let i = 0; i < adimlar.length; i++) {
      const a = adimlar[i], kok = a.icinde ? kap : null;
      if (a.icinde && !kap) return `adım ${i + 1}: panel bulunamadı`;
      let el = null; for (let t = 0; t < (a.istege ? 8 : 20) && !(el = bul(a, kok)); t++) await bekle(150);
      if (!el && a.istege) continue;
      if (!el) {  // görünen menü öğelerini de yaz — gerçek Teams'te adın/rolün ne olduğu görülsün
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

  // altyazının konuşma dili — aktarıcı "hedef" verirse (gündemde dil açıkça yazılı, agenda.json taze) altyazı
  // göründükten 4 sn sonra Teams'in dil ayarına bakılır; farklıysa hedef seçilip Güncelle'ye basılır. Toplantı başına bir
  // deneme; sonuç capAuto'ya ("dil: …") eklenir. Başarısızsa eskisi gibi dil uyarısı (dil_view) devrede kalır.
  let dilHedef = null, dilTried = "", capGorundu = 0;
  // (6 Ekim ilk gerçek iki kişilik deneme, kullanıcı kararı) Teams menüsüne tıklayan otomasyonlar kapalı. Dil yolu dişliyi bulamadı,
  // yedek yol katılımcı menüsünü açtı; altyazı açma gerçek Teams'te hiç çalışmadı. Kod kalır; altyazı açmayı OTO_ALTYAZI, dil ayarını
  // aktarıcının "altyazi_dili_ayarla" ayarı açar (dilHedef ancak o zaman gelir). Yerine 45 sn'de tek satır "altyazıyı aç" uyarısı.
  const OTO_ALTYAZI = false;
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

  // Whisper: kullanıcının mikrofonu → aktarıcı (/ses, kanal "ben"; aktarıcı sessizliğe göre böler, Whisper metne çevirir).
  // Teams sayfasının mikrofon izni kullanılır (ayrı izin sorulmaz). Teams'te mikrofon kapalıyken ("Sesi aç" görünüyorsa)
  // gönderilmez. Ses diske yazılmaz; yalnız 127.0.0.1'e gider. Karşı tarafın sesi ayrı: yerel ses yardımcısı ya da popup → arka plan + offscreen.
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
    dilBak();
  }
  setInterval(whisperTick, 2000);
  function captureHint(panel, caps) {
    if (window.top !== window) return;
    const siki = capSiki(); if (siki && !capWas) ogren(); capWas = siki;
    if (!inCall() && !capBusy) capTried = dilTried = "";  // toplantıdan çıkıp yeniden girince yeniden dener
    if (!inCall() || panel || siki) { callSince = 0; return; }  // gevşek findCaptions menüdeki "altyazı" öğesini de sayar
    callSince = callSince || Date.now(); const m = meetingInfo().title;
    if (OTO_ALTYAZI && Date.now() - callSince > 12000) altyaziAc(m);
    // Whisper yazıyorsa satırlar kaydediliyor; altyazı yalnız karşı tarafın adı için gerekir — uyarı buna göre, tek satır
    const whAkiyor = whisperView && whisperView.durum !== "yok" && (whisperView.ben || whisperView.karsi);
    // gevşek findCaptions menüdeki "altyazıyı aç" öğesini de altyazı sanıyordu (uyarıyı otomasyonun hata tostu taşıyordu);
    // buraya ancak sıkı seçici (capSiki) altyazı görmediyse gelinir, ek koşul yok
    if (Date.now() - callSince > 45000 && callWarned !== m) { callWarned = m;
      toast(whAkiyor ? L("Ad için altyazıyı aç: {y}", { y: P.yonerge.altyazi }) : L("Altyazı kapalı: {y}", { y: P.yonerge.altyazi }), "#b26a00", 12000); }
  }
  function tick() {
    if (!cfg.enabled) return;
    let entries = [], source = "";
    const panel = findTranscriptPanel();
    if (panel) { entries = parsePanel(panel); source = "transcript"; }
    if (!panel) { const cap = findCaptions(); if (cap) { entries = parseCaptions(cap); source = "captions"; } }
    // panel/altyazı kapanınca (ya da kaynak değişince) sabitlenmeyi bekleyen son satırlar kaybolmasın —
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
    send(fresh, source);
  }
  // taslak — sabitlenmeyi bekleyen (hâlâ konuşulan) satırın o anki hâli /taslak'a gider; pano soluk gösterir,
  // kesin satır (sabitlenmiş Teams satırı ya da Whisper) gelince aktarıcı siler. Kuyruğa girmez: kaybolursa önemsiz.
  let taslakSig = "";
  function taslakGonder(list, source) {
    // yalnız son 3 satır: panel ilk açıldığında görünen eski satırların hepsi "yeni" sayılır, taslak olmamalı
    const ents = list.filter(e => e.text && e.idx >= e.n - 3 && sentById.get(e.id) !== e.text).map(e => ({ id: e.id, speaker: e.speaker || "?", text: e.text }));
    const sig = JSON.stringify(ents); if (!ents.length || sig === taslakSig) return; taslakSig = sig;
    rf("/taslak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ meeting: meetingInfo(), source, entries: ents }) }).catch(() => {});
  }
  let lastSrc = "";
  setInterval(tick, 1000); // 3 sn → 1 sn (sabitleme süresi ayrı: cfg.stableMs)
  // nabız kuyruğu beklemez (boşaltma takılırsa nabız da susuyordu); arka plan servis çalışanı da 30 sn'de bir
  // "nabiz" mesajıyla ping() çağırır — Chrome arka plandaki sekmenin zamanlayıcılarını kısarsa mesaj yine işlenir.
  // Gövdede kim (zamanlayici|arka-plan) ve sekme görünürlüğü: aktarıcı 30 sn'yi aşan boşlukları bununla günlüğe yazar.
  let pingSon = 0;
  async function ping(kim = "zamanlayici") {
    if (!cfg.enabled) return;
    if (kim !== "zamanlayici" && Date.now() - pingSon < 8000) return;  // zamanlayıcı yeni attıysa tekrar etme
    pingSon = Date.now();
    if (queue.length) drainQueue(); // yeni satır gelmese de kuyruğu boşaltmayı dene
    const panel = findTranscriptPanel();
    const caps = !!findCaptions(); captureHint(panel, caps); if (queue.length) saveQueue(); else adoptQueues();
    const body = { ver: chrome.runtime.getManifest().version, meeting: meetingInfo(), panel: !!panel, rows: panel ? P.dokumSatirSayisi(panel) : 0, platform: P.ad, yonerge: P.yonerge, captions: caps, call: window.top === window ? inCall() : false, lang: capLang, langSrc, capAuto, sent: sentById.size + sentKeys.size, at: new Date().toISOString(), kim, vis: document.visibilityState, mic: window.top === window ? { on: mic.on, sessiz: mic.on && teamsSessiz(), hata: mic.hata || "" } : null };
    try { const r = await rf("/ping", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (r.ok) { lastOk = Date.now(); failCount = 0; } }
    catch (e) { failCount++; }
    chrome.runtime.sendMessage({ type: "status", ok: failCount === 0, panel: !!panel, call: body.call, meeting: body.meeting.title, at: lastOk, failCount, queued: queue.length }).catch(() => {});
  }
  setInterval(() => ping(), 10000); setTimeout(() => ping(), 1500);
  // Popup'tan gelen "not" ve "durum" istekleri
  // Kanıt anında paylaşılan ekranın ölçeği (9 Ekim: karşı tarafın ekranı küçük gösterilince kanıttaki yazı okunmadı). Görünür alanın ≥ %25'ini
// kaplayan en büyük oynayan video = sahnedeki paylaşım (galerideki küçük kamera karoları sayılmaz); ölçek = ekrandaki cihaz pikseli / videonun
// gerçek pikseli (object-fit: contain). Teams seçicisi gerekmez: platformdan bağımsız.
function paylasimOlcek() {
  let en = null;
  for (const v of document.querySelectorAll("video")) {
    if (!v.videoWidth || !v.videoHeight) continue;
    const r = v.getBoundingClientRect(), alan = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
    if (alan < innerWidth * innerHeight * 0.25 || (en && alan <= en.alan)) continue;
    en = { alan, olcek: Math.round(Math.min(r.width / v.videoWidth, r.height / v.videoHeight) * devicePixelRatio * 100) / 100, vw: v.videoWidth, vh: v.videoHeight };
  }
  return en && { olcek: en.olcek, vw: en.vw, vh: en.vh };
}
chrome.runtime.onMessage.addListener((msg, _s, reply) => {
    if (msg.type === "nabiz") { ping("arka-plan"); reply({ ok: true, vis: document.visibilityState }); return; }
    if (msg.type === "note") { rf("/note", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ meeting: meetingInfo(), text: msg.text, at: new Date().toISOString() }) }).then(() => reply({ ok: true })).catch(e => reply({ ok: false, err: String(e) })); return true; }
    // kanıt: arka plan betiği çekmeden önce şeridi/uyarıyı gizletir (görüntüye girmesin), sonra geri açtırır
    if (msg.type === "kanitHazirla") {
      if (window.top !== window) return;
      document.querySelectorAll("#suflor-serit, #suflor-toast").forEach(e => { e.dataset.sfDisp = e.style.display; e.style.display = "none"; });
      requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(() => reply({ meeting: meetingInfo(), w: innerWidth, h: innerHeight, paylasim: paylasimOlcek() }), 30))); return true;
    }
    if (msg.type === "bilgi") { if (window.top === window) toast(msg.text, msg.renk || "#1b6ef3", msg.ms || 5000); return; }
    if (msg.type === "kanitBitti") {
      if (window.top !== window) return;
      document.querySelectorAll("#suflor-serit, #suflor-toast").forEach(e => { e.style.display = e.dataset.sfDisp || ""; });
      if (msg.ok && msg.kucuk) toast(L("📷 Kanıt {n} kaydedildi — paylaşılan ekran küçük gösteriliyor (%{p}), yazı okunmayabilir: ekranı büyütüp yeniden al", { n: msg.n || "", p: msg.kucuk }), "#b26a00", 7000);
      else if (msg.ok) toast(L("📷 Kanıt {n} kaydedildi", { n: msg.n || "" }), "#1b8a3a", 2000); else if (msg.ok === false) toast(L("📷 Kanıt kaydedilemedi: ") + (msg.err || L("bilinmiyor"))); // null: yalnız şeridi geri aç
      return;
    }
    if (msg.type === "getStatus") { reply({ alan: { bekliyor: alanBekliyor, secili: alanSecili, relay: cfg.relay, sonHata }, meeting: meetingInfo().title, lastOk, failCount, sent: sentById.size + sentKeys.size, queued: queue.length, panel: !!findTranscriptPanel(), captions: !!findCaptions(), lang: capLang, langSrc, dilUyari,
      whisper: { mic: mic.on, sessiz: mic.on && teamsSessiz(), hata: mic.hata, durum: whisperView && whisperView.durum, karsi: !!(whisperView && whisperView.karsi), satir: whisperView && whisperView.satir } }); }
  });
  // --- Claude şeridi -----------------------------------------------------------------------------------------
  // Toplantı sayfasının sol altında küçük hap: renkli nokta + açık kart sayısı (metin yok; paylaşımda görünse de anlamsız).
  // Hapa tıklayınca kartlar bu sekmeden açılan küçük, her zaman üstte duran pencerede (Document Picture-in-Picture); tarayıcı
  // açamazsa hapın üstünde liste. Kartın kendisine dokunmak kapatır (okundu); ✓ yaptım, ✕ gerek yok ikincil. Şeritte SÖYLE,
  // DUR ve CEVAP; NOT yalnız panoda. Gizli DUR'un metni sekmedeki listede yok, yalnız ayrı pencerede ve panoda.
  if (window.top === window) {
    const KL = { soyle: "Söyle", dur: "Dur", cevap: "Cevap" };  // gösterirken L(); NOT kartı yalnız kart penceresinde (mini pano)
    const COL = { dur: "#c0503b", soyle: "#b0832e", cevap: "#8b938d", not: "#8b938d" }; // iki sınıf: Yap (Söyle pirinç, Dur kırmızı) · Bil (Cevap gri)
    const PRI = ["dur", "soyle", "cevap"];
    let host = null, root = null, sig = "", first = true, acik = false, pip = null, sonV = null; const seen = new Set();
    function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
    const CSS = `
        .w{font:13px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",system-ui,sans-serif;color:#18201c;
          --s1:#fff;--s2:#f9faf7;--tx:#18201c;--t2:#5c655f;--t3:#8b938d;--bd:rgba(24,32,28,.11);--bd2:rgba(24,32,28,.2);--hov:rgba(24,32,28,.05)}
        @media (prefers-color-scheme:dark){.w{color:#ecebe7;--s1:#171d1a;--s2:#1b221e;--tx:#e8ebe6;--t2:#a5ada7;--t3:#78807a;--bd:rgba(232,235,230,.1);--bd2:rgba(232,235,230,.2);--hov:rgba(232,235,230,.07)}}
        .pill{display:inline-flex;align-items:center;gap:6px;background:var(--s1);color:var(--tx);border:1px solid var(--bd2);border-radius:999px;padding:5px 10px;min-height:28px;box-sizing:border-box;
          box-shadow:0 2px 8px rgba(0,0,0,.18);cursor:pointer;user-select:none;font-size:12px;font-weight:600;white-space:nowrap}
        .pill i{width:8px;height:8px;border-radius:50%;background:var(--pc,#8c8b85);flex:none}.pill:empty{display:none}
        .list{display:none;width:320px;max-height:58vh;overflow:auto;background:var(--s2);border:1px solid var(--bd2);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.22);padding:8px;margin-bottom:8px}
        .w.acik .list{display:block}
        .k{position:relative;background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:8px 8px 8px 12px;margin:0 0 6px;overflow:hidden;color:var(--tx);cursor:pointer;display:flex;gap:6px;align-items:flex-start}
        .k:hover{border-color:var(--bd2)}.k .m{flex:1;min-width:0}
        .k::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--kc,#8c8b85)}
        .k b{display:block;font-size:11px;font-weight:600;letter-spacing:.03em;color:var(--kc,#8c8b85);margin-bottom:1px}
        .a{display:flex;gap:2px;flex:none}
        button{font:12px/1 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;color:var(--t3);background:transparent;border:1px solid transparent;border-radius:6px;padding:4px 6px;cursor:pointer}
        button:hover{background:var(--hov);color:var(--tx)}button:disabled{opacity:.6}
        .q{font-size:12px;color:var(--t2);padding:4px 2px}.top{font-size:12px;color:var(--t2);margin:0 2px 6px}.top:empty{display:none}.uy{color:#c0503b}
        .bos{font-size:12px;color:var(--t3);padding:6px 2px}
        .gir{display:flex;gap:6px;align-items:flex-end;margin:0 0 6px}.son{font-size:11px;color:var(--t3);border-top:1px solid var(--bd);padding:4px 2px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.son.eski{color:#b0832e}
        .alt{display:flex;gap:4px;justify-content:flex-end}.alt button{color:var(--t2);border-color:var(--bd)}
        .gir textarea{flex:1;min-width:0;resize:none;font:12px/1.4 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;color:var(--tx);background:var(--s1);
          border:1px solid var(--bd2);border-radius:8px;padding:6px 8px;box-sizing:border-box}.gir button{color:var(--tx);border-color:var(--bd2);padding:6px 9px}
        .kd{font-size:12px;color:var(--t2);margin-top:2px}.rp{font-weight:600}
        .ipucu{position:fixed;z-index:1000;max-width:240px;padding:5px 8px;border-radius:6px;background:#18201c;color:#fff;font:12px/1.35 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;white-space:pre-line;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,.2)}
        .ipucu[hidden]{display:none}@media (prefers-color-scheme:dark){.ipucu{background:#e8ebe6;color:#171d1a}}
        .yeni{animation:p 1s 3}@keyframes p{0%{box-shadow:0 0 0 0 rgba(176,131,46,.75)}100%{box-shadow:0 0 0 12px rgba(176,131,46,0)}}`;
    // Kart penceresi = mini pano: kartlar (NOT dahil), son satır, Claude'a not/soru kutusu, ⭐ / Ne diyeyim? / 🔇 / Kanıt.
    // Kutu pano ve mini panodakiyle aynı: aktarıcı /girdi soru mu not mu ayırır (başta ? → soru); Enter gönderir, ⌘Enter her zaman
    // soru, Shift+Enter yeni satır. Sayfa içi listede kutu yok (ayrı pencere açılamazsa yalnız kartlar).
    function altDugmeler(d, ta) {
      const a = d.createElement("div"); a.className = "alt";
      const dg = (metin, ipucu, is) => { const b = d.createElement("button"); b.textContent = metin; b.title = L(ipucu); b.onclick = async () => { b.disabled = true; try { await is(); } catch (e) {} setTimeout(() => { b.disabled = false; }, 2500); pollCards(); }; a.append(b); };
      const post = (yol, g) => rf(yol, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(g) });
      dg("⭐", "⭐ Önemli an: şu anı özette öne çıkar", () => post("/komut", { tur: "onemli", meeting: meetingInfo() }));  // ad: not süren toplantının dosyasına
      dg(L("Ne diyeyim?"), "Ne diyeyim? Claude son dakikalara bakıp tek cümlelik replik önersin (Option + Shift + O)", () => post("/ask", { tur: "ozet" }));
      dg("🔇", "Sessiz: 10 dk kart gösterme — DUR ve cevaplar yine gelir (Option + Shift + M; tekrar basınca kapanır)", () => post("/komut", { tur: "sessiz" }));
      dg(L("Kanıt"), "Toplantı ekranını kanıt olarak kaydet; kutudaki yazı not olur", () => { const not = ta.value.trim(); ta.value = ""; chrome.runtime.sendMessage({ type: "kanit", kaynak: "serit", not }); });
      return a;
    }
    // ipucu (pano ile aynı): kart penceresinde tarayıcının kendi ipucu çıkmayabiliyor — üstüne gelince hemen, title → data-ipucu
    function ipucuKur(d) {
      const w = d.defaultView; let b = null, hedef = null, t = 0;
      const gizle = () => { clearTimeout(t); hedef = null; if (b) b.hidden = true; };
      d.addEventListener("mouseover", ev => {
        const x = ev.target.closest && ev.target.closest("[title],[data-ipucu]"); if (!x || x === hedef) return;
        if (x.hasAttribute("title")) { x.dataset.ipucu = x.getAttribute("title"); if (!x.hasAttribute("aria-label")) x.setAttribute("aria-label", x.dataset.ipucu); x.removeAttribute("title"); }
        if (!x.dataset.ipucu) return gizle(); hedef = x; clearTimeout(t);
        t = setTimeout(() => {
          if (hedef !== x || !x.isConnected) return;
          if (!b) { b = d.createElement("div"); b.className = "ipucu"; b.setAttribute("role", "tooltip"); d.body.appendChild(b); }
          b.textContent = x.dataset.ipucu; b.hidden = false; const r = x.getBoundingClientRect(), bw = b.offsetWidth, bh = b.offsetHeight;
          b.style.left = Math.max(6, Math.min(r.left + r.width / 2 - bw / 2, w.innerWidth - bw - 6)) + "px";
          b.style.top = Math.max(6, r.bottom + 6 + bh > w.innerHeight - 6 ? r.top - bh - 6 : r.bottom + 6) + "px";
        }, 250);
      });
      d.addEventListener("mouseout", ev => { if (hedef && !(ev.relatedTarget && hedef.contains(ev.relatedTarget))) gizle(); });
      d.addEventListener("mousedown", gizle, true); w.addEventListener("blur", gizle);
    }
    function kutu(d) {
      const f = d.createElement("div"); f.className = "gir";
      const ta = d.createElement("textarea"); ta.rows = 2; ta.placeholder = L("Not ya da soru (başa ?)");
      const b = d.createElement("button"); b.textContent = L("Gönder");
      const git = async soru => {
        const t = ta.value; if (!t.trim()) return; ta.value = ""; b.disabled = true; let r = {};
        try { r = await (await rf("/girdi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: t, soru, at: new Date().toISOString(), meeting: meetingInfo() }) })).json(); } catch (e) {}
        b.textContent = r.tur ? "✓ " + L(r.tur) : L("gönderilemedi"); if (!r.tur) ta.value = t;
        setTimeout(() => { b.textContent = L("Gönder"); b.disabled = false; }, 1500); pollCards();
      };
      b.onclick = () => git(false);
      // sayfa içindeyken tuşlar Teams'in kısayollarına gitmesin
      ta.addEventListener("keydown", ev => { ev.stopPropagation(); if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); git(ev.metaKey || ev.ctrlKey); } });
      ["keyup", "keypress"].forEach(t => ta.addEventListener(t, ev => ev.stopPropagation()));
      f.append(ta, b); return f;
    }
    function ensure() {
      if (host && host.isConnected) return;
      host = el("div"); host.id = "suflor-serit";
      Object.assign(host.style, { position: "fixed", left: "12px", bottom: "12px", zIndex: 999998 });
      root = host.attachShadow({ mode: "open" });
      const st = el("style"); st.textContent = CSS;
      const w = el("div", "w"); w.append(el("div", "list"), el("div", "pill"));
      root.append(st, w); document.body.appendChild(host);
      root.addEventListener("click", tikla);
    }
    // hap: ayrı pencereyi aç/kapat; açılamazsa (eski Chrome, izin) listeyi hapın üstünde aç/kapat
    async function hapTik() {
      if (pip && !pip.closed) { pip.close(); pip = null; return; }
      if (window.documentPictureInPicture) {
        try {
          pip = await documentPictureInPicture.requestWindow({ width: 320, height: 420 });
          const d = pip.document; d.title = "Suflor.me mini";
          // tema açıkça: PiP penceresi sistem açıkken de koyu açılıyordu (9 Ekim denemesi). Karar toplantı sekmesinin gördüğü
          // açık/koyudan; PiP'in kendi değeri ve sekmeninki günlüğe (EKLENTİ: mini-tema) — farklılarsa neden orada görünür
          const mq = "(prefers-color-scheme: dark)", temaKur = () => { d.documentElement.dataset.tema = matchMedia(mq).matches ? "koyu" : "acik"; };
          temaKur(); matchMedia(mq).addEventListener("change", () => { if (pip && !pip.closed) temaKur(); });
          olay("mini-tema", `pip ${pip.matchMedia(mq).matches ? "koyu" : "açık"} · sekme ${matchMedia(mq).matches ? "koyu" : "açık"}`);
          const temali = c => c.replace(/@media \(prefers-color-scheme:dark\)\{([^{}]+)\{([^{}]*)\}\}/g, (_, sec, govde) => sec.split(",").map(x => "html[data-tema=koyu] " + x.trim()).join(",") + "{" + govde + "}");
          const st = d.createElement("style"); st.textContent = "html{color-scheme:light}html[data-tema=koyu]{color-scheme:dark}" + temali(CSS + `html,body{margin:0;height:100%}body{background:#f9faf7}@media (prefers-color-scheme:dark){body{background:#1b221e}}.w{padding:8px;box-sizing:border-box;min-height:100%}.w .list{display:block;width:auto;max-height:none;border:0;box-shadow:none;padding:0;margin:0;background:transparent}`);
          const w = d.createElement("div"); w.className = "w"; const g = kutu(d);
          w.append(Object.assign(d.createElement("div"), { className: "list" }), Object.assign(d.createElement("div"), { className: "son" }), g, altDugmeler(d, g.querySelector("textarea")));
          d.head.appendChild(st); d.body.appendChild(w); d.addEventListener("click", tikla); ipucuKur(d);
          pip.addEventListener("pagehide", () => { pip = null; });
          const yas = setInterval(() => { if (!pip || pip.closed) return clearInterval(yas); if (sonV) sonCiz(pip.document, sonV.son); }, 5000);
          acik = false; root.querySelector(".w").classList.remove("acik"); if (sonV) { sig = ""; paint(sonV); } return;
        } catch (e) { pip = null; }
      }
      acik = !acik; root.querySelector(".w").classList.toggle("acik", acik);
    }
    function tikla(ev) {
      if (ev.target.closest(".pill")) return hapTik();
      const b = ev.target.closest("button[data-ack]"), k = ev.target.closest(".k[data-id]");
      if (!b && (!k || k.dataset.onay)) return;  // onay kartına dokunmak onay değil (#76)
      const id = b ? b.dataset.id : k.dataset.id, st = b ? b.dataset.ack : "okundu";  // karta dokunmak = okundu
      if (k) k.style.opacity = ".45";
      rf("/card-ack", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id, status: st }) }).then(pollCards).catch(() => {});
    }
    // toplantıdayken (transkript paneli ya da altyazı açık) kart olmasa da hap görünür (nokta yeşil). Toplantı dışındaki
    // sayfalarda yalnız kart/uyarı varken.
    function inMeeting() { return !!(findTranscriptPanel() || capSiki()); }
    let kanitSon = null, komutSon;  // sesli komut onayı (ilk yoklamada eski komut gösterilmez)
    function listeCiz(list, v, cards, qs, warn, dil, ayri) {
      const d = list.ownerDocument, e = (t, c, x) => { const n = d.createElement(t); if (c) n.className = c; if (x != null) n.textContent = x; return n; };
      const sv = v.sure, kal = sv ? sv.kalan_dk : null;
      const top = e("div", "top", sv ? (kal > 0 ? L("{n} dk kaldı", { n: kal }) : kal === 0 ? L("süre doldu") : L("+{n} dk", { n: -kal })) + (sv.kayma >= 2 ? L(" · {n} madde geride", { n: sv.kayma }) : "") : "");
      list.replaceChildren(top);
      const ss = v.sessiz, sn = (ss && ss.tutulan || []).length;
      if (ss && ss.acik) list.append(e("div", "top", "🔇 " + L("Sessiz · {n} dk", { n: Math.max(1, Math.ceil(ss.kalan_sn / 60)) }) + (sn ? L(" · {n} kart bekliyor", { n: sn }) : "")));
      else if (sn) list.append(e("div", "top", "🔔 " + L("Sessiz bitti — Claude özetliyor ({n} kart)", { n: sn })));
      if (v.ertelenen) list.append(e("div", "top", "⏸ " + L("{n} kart sonraya bırakıldı", { n: v.ertelenen })));
      if (dil) list.append(e("div", "top uy", "⚠ " + L("Döküm dili yanlış — panoya bak")));
      if (warn) list.append(e("div", "top uy", "⚠ " + warn));
      cards.forEach(c => {
        const k = e("div", "k"); k.dataset.id = c.id; k.style.setProperty("--kc", COL[c.kind]);
        if (c.onay) k.dataset.onay = "1"; else k.title = L("Dokun: kapat");
        const m = e("div", "m"); m.append(e("b", null, (c.geri ? "↩ " : "") + L(c.onay ? "Onay bekliyor" : c.replik ? "Ne diyeyim" : KL[c.kind] || "Not")));
        if (!c.gizli || ayri) m.append(c.replik ? e("span", "rp", c.text) : d.createTextNode(c.text));
        if (c.durum && (!c.gizli || ayri)) m.append(e("div", "kd", c.durum));  // Ne diyeyim?: şu an ne konuşuluyor
        const a = e("div", "a");
        // onay kartı (#76): Claude'un yapacağı iç işi yazılı onayla — yalnız anahtarlı eklentiden geçer
        (c.onay ? [["onaylandi", "✓ " + L("Onayla"), "Onayla"], ["reddedildi", "✕ " + L("Reddet"), "Reddet"]] :
        [["yapildi", "✓", "Yaptım"], ["ertele", "⏸", "Sonra: gündemde sıradaki maddede (gündem yoksa 5 dk sonra) yeniden göster"], ["gecildi", "✕", "Gerek yok — Claude bir daha önermesin"]].filter(([st]) => st !== "yapildi" || !["cevap", "not"].includes(c.kind)))
          .forEach(([st, lbl, tip]) => { const x = e("button", null, lbl); x.dataset.ack = st; x.dataset.id = c.id; x.title = L(tip); a.append(x); });
        k.append(m, a); list.append(k);
      });
      qs.forEach(q => list.append(e("div", "q", "⏳ " + (q.tur === "ozet" ? L("Ne diyeyim? — replik hazırlanıyor…") : L("Claude'a soruldu: ") + q.text))));
      if (!cards.length && !qs.length && !dil && !warn) list.append(e("div", "bos", L("Şimdilik kart yok")));
    }
    function sonCiz(d, son) {  // mini panodaki gibi tek satır canlılık: son döküm satırı ne zaman, kimden
      const n = d.querySelector(".son"); if (!n) return;
      if (!son || !son.at) { n.textContent = L("henüz satır yok"); n.className = "son"; return; }
      const a = Math.max(0, Math.round((Date.now() - Date.parse(son.at)) / 1000));
      n.textContent = L("son satır {a} önce · {k}", { a: a < 60 ? L("{n} sn", { n: a }) : L("{n} dk", { n: Math.floor(a / 60) }), k: son.speaker || "?" }); n.className = a > 60 ? "son eski" : "son";
    }
    // Yaparken kaydet: kip açıkken toplantı sekmesi 3 sn'de bir arka plana "kare" der; karşılaştırma ve kendiliğinden kanıt background.js'te.
    // Şerit ve uyarı alanı maskelenir (kart gelince "ekran değişti" sayılmasın). Sekme görünür değilse istenmez.
    let otoZaman = null;
    function otoAyarla(acik) {
      if (acik && !otoZaman && window.top === window) otoZaman = setInterval(() => {
        if (document.visibilityState !== "visible" || !(inMeeting() || inCall())) return;
        const maske = [...document.querySelectorAll("#suflor-serit, #suflor-toast")].map(e => e.getBoundingClientRect()).filter(r => r.width && r.height)
          .map(r => ({ x: r.left / innerWidth, y: r.top / innerHeight, w: r.width / innerWidth, h: r.height / innerHeight }));
        chrome.runtime.sendMessage({ type: "otoKare", maske }).catch(() => {});
      }, 3000);
      else if (!acik && otoZaman) { clearInterval(otoZaman); otoZaman = null; }
    }
    function paint(v) {
      sonV = v; otoAyarla(!!v.yaparken);
      // panodan/mini panodan kanıt istendi — toplantıdaki sekme çeker (çift isteği aktarıcı ayıklar). Arkadaysa da ister;
      // arka plan sekmeyi bir an öne getirip çeker (2 Ekim: pano aynı penceredeyken kanıt düşüyordu)
      if (v.kanit_iste && v.kanit_iste.id !== kanitSon) { kanitSon = v.kanit_iste.id; if (window.top === window && (inMeeting() || inCall())) chrome.runtime.sendMessage({ type: "kanit", kaynak: v.kanit_iste.kaynak || "pano", istek: v.kanit_iste.id, not: v.kanit_iste.not }).catch(() => {}); }
      if (v.komut && v.komut.id !== komutSon) { if (komutSon !== undefined && window.top === window) toast(v.komut.metin, "#0a8f5a", 3500); komutSon = v.komut.id; }
      else if (!v.komut && komutSon === undefined) komutSon = null;
      // Whisper durumu; karşı tarafın sesi henüz verilmediyse toplantı başına bir kez hatırlatma
      whisperView = v.whisper || null;
      // yerel ses yardımcısı açıksa (bekliyor/dinliyor) karşı sesi o alır — hatırlatma yok
      if (whisperView && cfg.whisper && whisperView.durum !== "yok" && inCall() && !whisperView.karsi && !["bekliyor", "dinliyor"].includes(whisperView.yerel) && karsiIpucu !== meetingInfo().title) {
        karsiIpucu = meetingInfo().title; toast(L("Karşı tarafın sesi için: simge → Karşı taraf → Aç"), "#1b6ef3", 10000);
      }
      const cards = (v.cards || []).filter(c => KL[c.kind]), qs = v.questions || [], live = inMeeting();  // NOT kartı şeritte değil
      const warn = v.uyari || ""; // disk dolu / az yer — kart olmasa da şerit görünür
      const dil = (v.dil && v.dil.uyari) || ""; // konuşma dili beklenenden farklı (ayrıntı panoda)
      dilHedef = (v.dil && v.dil.hedef) || null;
      if (dil && dil !== dilUyari) toast("⚠ " + L("Döküm dili yanlış — panoya bak")); dilUyari = dil;
      if (!document.body || (!cards.length && !qs.length && !warn && !dil && !live)) { if (host) host.style.display = "none"; if (pip && !pip.closed) { pip.close(); pip = null; } return; }
      ensure(); host.style.display = "block";
      if (pip && !pip.closed) sonCiz(pip.document, v.son);  // her yoklamada (yaş değişir)
      const tum = (v.cards || []).filter(c => KL[c.kind] || c.kind === "not");  // kart penceresi (mini pano) NOT'u da gösterir
      const ss = v.sessiz;  // sessiz: hapta 🔇; ertelenip geri gelen kart yeni sayılır (hap yeniden parlar)
      const s = JSON.stringify([tum.map(c => c.id + (c.geri || "")), qs.map(q => q.id), warn, dil, v.sure && [v.sure.kalan_dk, v.sure.kayma], live, DIL, !!pip,
        ss && [ss.acik, Math.ceil(ss.kalan_sn / 60), (ss.tutulan || []).length], v.ertelenen]); if (s === sig) return; sig = s;
      const top = PRI.find(k => cards.some(c => c.kind === k)) || "cevap";
      const pill = root.querySelector(".pill");
      // hap = nokta (en önemli kartın sınıf rengi; uyarıda kırmızı; kartsız toplantıda yeşil) + açık kart sayısı
      const pc = (warn || dil) ? COL.dur : cards.length ? COL[top] : (live ? "#1f7a4f" : "#8b938d");
      pill.style.setProperty("--pc", pc); pill.replaceChildren(el("i")); if (cards.length) pill.append(el("span", null, String(cards.length)));
      if (ss && ss.acik) pill.append(el("span", null, "🔇"));
      pill.title = ss && ss.acik ? L("Suflor.me — sessiz; kartlar bekliyor") : L("Suflor.me — kartlar için tıkla");
      const fresh = cards.some(c => !seen.has(c.id + (c.geri || ""))); cards.forEach(c => seen.add(c.id + (c.geri || "")));
      if (fresh && !first) { pill.classList.remove("yeni"); void pill.offsetWidth; pill.classList.add("yeni"); }
      first = false;
      listeCiz(root.querySelector(".list"), v, cards, qs, warn, dil, false);
      if (pip && !pip.closed) { const l = pip.document.querySelector(".list"); if (l) listeCiz(l, v, tum, qs, warn, dil, true); }
    }
    // toplantıdaki sekmede uzun yoklama — aktarıcı kart/✓/kanıt isteği değişince hemen döner (önce 3 sn yoklama,
    // kart → şerit ortanca 2,1 sn). Yanıtta "imza" yoksa (eski aktarıcı) ya da hata olursa 3 sn'lik yoklamaya döner.
    let imza = "", uzunAcik = false;
    async function pollCards(uzun) {
      if (!cfg.enabled) { if (host) host.style.display = "none"; return false; }
      try {
        const r = uzun === true ? await rf("/cards?bekle=25&imza=" + encodeURIComponent(imza), { signal: AbortSignal.timeout(35000) }) : await rf("/cards");
        if (r.ok) { const v = await r.json(); imza = v.imza || ""; paint(v); return !!v.imza; }
      } catch (e) { /* aktarıcı kapalı: şerit değişmez */ }
      return false;
    }
    async function uzunDongu() {
      if (uzunAcik) return; uzunAcik = true;
      try {
        while (cfg.enabled && (inMeeting() || inCall())) {
          const t = Date.now(); if (!(await pollCards(true))) break;
          if (Date.now() - t < 200) await new Promise(r => setTimeout(r, 200));  // aynı anda çok değişiklikte dönmesin
        }
      } finally { uzunAcik = false; }
    }
    setInterval(() => { if (uzunAcik) return; pollCards(); if (cfg.enabled && (inMeeting() || inCall())) uzunDongu(); }, 3000); setTimeout(pollCards, 1000);
  }
  setTimeout(adoptQueues, 3000); // önceki sekmeden kalan bekleyen satırlar
  log("yüklendi");
})();
