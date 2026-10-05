// Servis çalışanı: rozet (badge), bildirim, v0.7.0 kanıt ekran görüntüsü
let state = { ok: null, at: 0, meeting: "", failCount: 0, queued: 0 };
// v0.12.2: arayüz dili (tr/en) — bildirim ve şerit toast metinleri. İçerik betiği ve popup aktarıcının /status "arayuz_dili"
// alanını chrome.storage.local "dil"e yazar; burada yalnız okunur (yoksa "tr"). Aktarıcıya giden metinler (/olay) çevrilmez.
let DIL = "tr";
chrome.storage.local.get({ dil: "tr" }, v => { DIL = v.dil === "en" ? "en" : "tr"; });
chrome.storage.onChanged.addListener((ch, alan) => { if (alan === "local" && ch.dil) DIL = ch.dil.newValue === "en" ? "en" : "tr"; });
const EN = {"Suflor.me — hassas ifade":"Suflor.me — sensitive phrase","⭐ işaretlenemedi: ":"⭐ couldn't be marked: ","Özet istenemedi: ":"Couldn't request a summary: ",
  "aktarıcıya ulaşılamadı (127.0.0.1:8765)":"can't reach the relay (127.0.0.1:8765)","Açık toplantı sekmesi yok (Teams).":"No open meeting tab (Teams).",
  "Çalışma alanı seçilmedi — Suflor.me simgesine tıklayıp seç.":"No workspace selected — click the Suflor.me icon and pick one.",
  "🎙 Karşı tarafın sesi zaten yazılıyor":"🎙 The other side's audio is already being transcribed",
  "Toplantı sekmesini öne getirdim — karşı tarafın sesi için Option + Shift + W'ye bir kez daha bas":"I brought the meeting tab to the front — press Option + Shift + W once more for the other side's audio",
  "🎙 Whisper: karşı tarafın sesi de yazılıyor":"🎙 Whisper: the other side's audio is now being transcribed too","Whisper karşı taraf açılamadı: ":"Couldn't start Whisper for the other side: ",
  "Suflor.me — kanıt kaydedilemedi":"Suflor.me — couldn't save evidence","Toplantı penceresi simge durumunda — pencereyi açıp tekrar dene.":"The meeting window is minimised — restore it and try again.",
  "Aktarıcıya ulaşılamadı (çalışma alanının aktarıcısı kapalı).":"Can't reach the relay (this workspace's relay is off).",
  "{n} dk sonra başlıyor":"Starts in {n} min","Başlıyor":"Starting",". Suflor.me'yi başlatayım mı?":". Start Suflor.me?","Suflor.me'yi başlat":"Start Suflor.me","Panoyu aç":"Open panel",
  "Suflor.me başlatılamadı":"Couldn't start Suflor.me","bilinmiyor":"unknown"};
function L(s, v) { let t = DIL === "en" && EN[s] || s; if (v) for (const k in v) t = t.split("{" + k + "}").join(v[k]); return t; }
// v0.9.0: toplantı sekmesi adresleri manifest'ten — platform dosyası (platform-*.js) yükleyen içerik betiği girdileri.
// Yeni platform yalnız manifest'e eklenir. tabs.query kalıbında port olmaz (test sayfası 127.0.0.1:8797 → 127.0.0.1).
const TOPLANTI_URL = [...new Set(chrome.runtime.getManifest().content_scripts
  .filter(cs => (cs.js || []).some(j => j.startsWith("platform-"))).flatMap(cs => cs.matches).map(m => m.replace(/:\d+\//, "/")))];
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "status") {
    state = Object.assign(state, msg);
    if (sender.tab && msg.call) { callTab = sender.tab.id; callAt = Date.now(); }  // v0.8.6: toplantıdaki sekme
    const queued = msg.queued || 0;
    chrome.action.setBadgeText({ text: queued ? String(Math.min(queued, 99)) : (msg.ok ? "●" : "!") });
    chrome.action.setBadgeBackgroundColor({ color: queued ? "#b00020" : (msg.ok ? "#1b8a3a" : "#b00020") });
  }
  if (msg.type === "flag") { chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me — hassas ifade"), message: (msg.flags || []).join(", ") + ": " + (msg.text || "").slice(0, 120) }); }
  if (msg.type === "kanit") kanit(sender.tab, msg.kaynak, msg.istek, msg.not);
  if (msg.type === "whisperKarsi") karsiBaslat(null, "popup");       // v0.8.0: popup düğmesi (eklenti çağrıldı: izin var)
  if (msg.type === "whisperKarsiDur") offDur();                       // toplantıdan çıkıldı
  if (msg.type === "offBitti") karsiTab = null;
});
// Option + Shift + K (manifest "commands"): hangi pencere önde olursa olsun Teams sekmesini çeker — pano öndeyken de çalışır
chrome.commands.onCommand.addListener(cmd => { if (cmd === "kanit") kanit(null, "kisayol"); if (cmd === "whisper") karsiBaslat(null, "kisayol");
  if (cmd === "onemli" || cmd === "ozet") komut(cmd); });
// v0.8.6: ⭐ önemli an (Option + Shift + S) ve son 1 dk özeti (Option + Shift + O) — "Suflor, …" sesli komutlarının yerine.
// Onay şeritte aktarıcının "komut" alanından gelir (Teams'te yeşil toast); aktarıcıya ulaşılamazsa bildirim.
async function komut(tur) {
  try {  // toplantı adı gönderilmez: aktarıcı süren toplantıya yazar (sekme başlığı "Calendar" olabiliyor)
    const r = await fetch((await relayAdr()) + "/komut", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur }) });
    if (!r.ok) throw new Error("aktarıcı HTTP " + r.status);
  } catch (e) {
    chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: "Suflor.me", message: L(tur === "onemli" ? "⭐ işaretlenemedi: " : "Özet istenemedi: ") + (/Failed to fetch/i.test(String(e)) ? L("aktarıcıya ulaşılamadı (127.0.0.1:8765)") : L(String(e.message || e))) });
  }
}

// v0.8.0 — Whisper karşı kanal: Teams sekmesinin sesi (diğer katılımcılar). chrome.tabCapture yalnız kullanıcı eklentiyi
// çağırınca (⌥⇧W kısayolu ya da popup) izin verir; akış offscreen belgesinde işlenir (servis çalışanında ses yok).
let karsiTab = null, callTab = null, callAt = 0;
async function offscreenAc() {
  const var_ = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (var_.length) return;
  await chrome.offscreen.createDocument({ url: "offscreen.html", reasons: ["USER_MEDIA"], justification: "Teams toplantı sesini yerel Whisper aktarıcısına (127.0.0.1) vermek" });
}
function bilgi(tab, text, renk, ms) { if (tab) chrome.tabs.sendMessage(tab.id, { type: "bilgi", text, renk, ms }, { frameId: 0 }).catch(() => {}); }
// v0.9.2: adres önce bu tarayıcının yerel ayarından (çalışma alanı seçimi), yoksa eski eşitlenen ayardan
// Seçim yoksa aktarıcılar yoklanır: tek aktarıcı → o; birden fazla → hata (yanlış alana kanıt yazılmasın); hiç yok → eski ayar.
// v0.12.3 (güvenlik denetimi O3): aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
async function relayAdr() {
  const l = relayGecerli((await chrome.storage.local.get({ relay: null })).relay); if (l) return l;
  const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok ? `http://127.0.0.1:${p}` : null; } catch (e) { return null; } }))).filter(Boolean);
  if (bul.length > 1) throw new Error("Çalışma alanı seçilmedi — Suflor.me simgesine tıklayıp seç.");
  if (bul.length === 1) chrome.storage.local.set({ relay: bul[0], relayOto: true });  // v0.13.5: tek aktarıcı kendiliğinden kaydedilir (content.js ile aynı)
  return bul[0] || relayGecerli((await chrome.storage.sync.get({ relay: RELAY_VARSAYILAN })).relay) || RELAY_VARSAYILAN;
}
async function karsiBaslat(hint, kaynak) {
  const tab = await toplantiSekmesi(hint);
  if (!tab) return chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: "Suflor.me Whisper", message: L("Açık toplantı sekmesi yok (Teams).") });
  let relay; try { relay = await relayAdr(); } catch (e) { return bilgi(tab, L(e.message), "#b26a00", 10000); }  // v0.9.2: alan seçilmedi
  const olay = metin => fetch(relay + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "whisper-karsi", metin }) }).catch(() => {});
  // v0.8.6 (2 Ekim denemesi): ikinci basış "Cannot capture a tab with an active stream" kırmızısı veriyordu — zaten açık
  if (karsiTab === tab.id) return bilgi(tab, L("🎙 Karşı tarafın sesi zaten yazılıyor"), "#1b8a3a", 3000);
  try {
    let id;
    try { id = await chrome.tabCapture.getMediaStreamId({ targetTabId: tab.id }); }
    catch (e) {
      // Chrome yalnız eklentinin çağrıldığı (öndeki) sekmeyi verir. Teams sekmesi arkadaysa öne getir, bir kez daha bastır.
      if (/active stream/i.test(String(e))) { karsiTab = tab.id; return bilgi(tab, L("🎙 Karşı tarafın sesi zaten yazılıyor"), "#1b8a3a", 3000); }
      if (tab.active) throw e;
      await chrome.tabs.update(tab.id, { active: true }); await chrome.windows.update(tab.windowId, { focused: true }).catch(() => {});
      bilgi(tab, L("Toplantı sekmesini öne getirdim — karşı tarafın sesi için Option + Shift + W'ye bir kez daha bas"), "#1b6ef3", 10000);
      return olay(`öne getirildi (${kaynak}): Teams sekmesi arkadaydı, ikinci basış bekleniyor`);
    }
    await offscreenAc();
    const title = (tab.title || "").replace(/^\(\d+\)\s*/, "").split("|").map(x => x.trim()).filter(Boolean).slice(-2, -1)[0] || "Toplantı";
    chrome.runtime.sendMessage({ type: "offBasla", id, relay, title }).catch(() => {});
    karsiTab = tab.id; bilgi(tab, L("🎙 Whisper: karşı tarafın sesi de yazılıyor"), "#1b8a3a", 4000);
  } catch (e) {
    const err = String(e.message || e).slice(0, 160);
    bilgi(tab, L("Whisper karşı taraf açılamadı: ") + err, "#b00020", 8000);
    olay(`açılamadı (${kaynak}): ${err}`);
  }
}
function offDur() { if (karsiTab == null) return; karsiTab = null; chrome.runtime.sendMessage({ type: "offDur" }).catch(() => {}); }
chrome.tabs.onRemoved.addListener(id => { if (id === karsiTab) offDur(); });

// v0.7.0 — Kanıt: Teams sekmesinin görünen alanı PNG olarak aktarıcıya gider (kanit/<toplantı>/…png). Akış durmaz:
// diyalog yok; şerit ve uyarı çekim anında gizlenir, sonra 2 sn'lik yeşil onay. Çekim yalnız sekme penceresinde öndeyse
// mümkün (Chrome kısıtı); değilse kırmızı uyarı + bildirim.
let busy = false;
async function toplantiSekmesi(hint) {
  if (hint && hint.id != null) return hint;
  const tabs = await chrome.tabs.query({ url: TOPLANTI_URL });
  if (!tabs.length) return null;
  const [focused] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (focused && tabs.some(t => t.id === focused.id)) return focused;
  // v0.8.6: toplantıdaki sekme (son 30 sn'de "call" bildirdi) — takvim/sohbet sekmesi ondan sonra gelir
  const call = Date.now() - callAt < 30000 && tabs.find(t => t.id === callTab);
  if (call) return call;
  const act = tabs.filter(t => t.active); // penceresinde önde olan Teams sekmeleri; en son kullanılan
  return (act.length ? act : tabs).sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0];
}
function hata(tab, err) {
  kanitOlay("hata: " + err);  // aktarıcı günlüğüne Türkçe; kullanıcıya gösterilen hâli L() ile
  chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me — kanıt kaydedilemedi"), message: L(err) });
  if (tab) chrome.tabs.sendMessage(tab.id, { type: "kanitBitti", ok: false, err: L(err) }, { frameId: 0 }).catch(() => {});
}
// v0.8.0: 1 Ekim 22:5x şerit 📷 kanıtı aktarıcıya hiç ulaşmadı (günlükte iz yok) — olası neden: yanıtlanmayan bir mesaj
// "busy"yi kilitli bıraktı. Artık 15 sn'de kilit açılır, şeridin hazırlık yanıtı 1,5 sn beklenir, her hata günlüğe gider.
let busyAt = 0;
function kanitOlay(metin) { relayAdr().then(r => fetch(r + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "kanit", metin }) })).catch(() => {}); }
async function kanit(hint, kaynak, istek, not) {
  if (busy && Date.now() - busyAt < 15000) return kanitOlay(`${kaynak}: önceki çekim sürüyor, atlandı`);
  busy = true; busyAt = Date.now();
  let tab = null;
  try {
    tab = await toplantiSekmesi(hint);
    if (!tab) return hata(null, "Açık toplantı sekmesi yok (Teams).");
    // v0.8.6: Teams sekmesi penceresinde arkadaysa (pano/başka sekme önde) bir an öne getir, çek, eski sekmeye dön
    let geri = null;
    if (!tab.active) {
      const w = await chrome.windows.get(tab.windowId).catch(() => null);
      if (w && w.state === "minimized") return hata(tab, "Toplantı penceresi simge durumunda — pencereyi açıp tekrar dene.");
      [geri] = await chrome.tabs.query({ active: true, windowId: tab.windowId });
      await chrome.tabs.update(tab.id, { active: true });
      await new Promise(r => setTimeout(r, 700));  // sayfa yeniden çizilsin
    }
    let info = {};
    try { info = await Promise.race([chrome.tabs.sendMessage(tab.id, { type: "kanitHazirla" }, { frameId: 0 }), new Promise(r => setTimeout(() => r(null), 1500))]) || {}; } catch (e) { /* betik yok: şerit de yok, doğrudan çek */ }
    let png;
    try { png = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" }); }
    finally {
      chrome.tabs.sendMessage(tab.id, { type: "kanitBitti", ok: null }, { frameId: 0 }).catch(() => {});
      if (geri) chrome.tabs.update(geri.id, { active: true }).catch(() => {});
    }
    const relay = await relayAdr();
    const r = await fetch(relay + "/kanit", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ png, meeting: info.meeting || { title: (tab.title || "").split("|").slice(-2, -1)[0]?.trim() || "Toplantı" }, kaynak, istek, not, w: info.w, h: info.h }) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.ok) return hata(tab, j.err || ("aktarıcı HTTP " + r.status));
    if (!j.dup) chrome.tabs.sendMessage(tab.id, { type: "kanitBitti", ok: true, n: j.n }, { frameId: 0 }).catch(() => {});
  } catch (e) {
    hata(tab, /Failed to fetch/i.test(String(e)) ? "Aktarıcıya ulaşılamadı (çalışma alanının aktarıcısı kapalı)." : String(e.message || e).slice(0, 160));
  } finally { busy = false; }
}

// v0.9.3 — toplantı hatırlatması: dakikada bir aktarıcının takvimine bakar (Mac Takvim, Suflor Takvim yardımcısı). Bir toplantı
// ≤ 5 dk sonra başlıyorsa ve Claude bu alanda izlemiyorsa bildirim: "Suflor'u başlat" (Terminal'de /toplanti) · "Panoyu aç".
// Her toplantı için bir kez. Çalışma alanı seçilmemişse (iki aktarıcı) bildirim yok.
chrome.alarms.create("takvim", { periodInMinutes: 1 });
const bildirilen = new Set();
chrome.alarms.onAlarm.addListener(a => { if (a.name === "takvim") takvimBak(); if (a.name === "nabiz") nabizYokla(); });
// v0.13.5: yüklenince ve Chrome açılınca hemen bir kez (sihirbazın eklenti adımı dakikayı beklemesin)
chrome.runtime.onInstalled.addListener(() => takvimBak()); chrome.runtime.onStartup.addListener(() => takvimBak());
// v0.9.6 — nabız yedeği: 3 Ekim denemesinde Teams sekmesinin nabzı ~7 dk kesildi (mikrofon sesi akarken). 30 sn'de bir her
// toplantı sekmesinin üst çerçevesine "nabiz" mesajı; içerik betiği ping() atar (mesaj, kısılan zamanlayıcıyı beklemez).
// Yanıt yoksa (betik yüklü değil / bağlam koptu) aktarıcı günlüğüne bir kez yazılır; sekme yeniden yanıt verince yine.
chrome.alarms.create("nabiz", { periodInMinutes: 0.5 });
const sessizSekme = new Set();
async function nabizYokla() {
  for (const t of await chrome.tabs.query({ url: TOPLANTI_URL })) {
    if (t.discarded) continue;
    const r = await chrome.tabs.sendMessage(t.id, { type: "nabiz" }, { frameId: 0 }).catch(e => ({ err: String(e && e.message || e) }));
    const ok = !!(r && r.ok), onceki = sessizSekme.has(t.id);
    if (ok === !onceki || (!ok && t.id !== callTab)) continue;  // durum değişmedi; yalnız toplantıdaki sekme günlüğe yazılır
    if (ok) sessizSekme.delete(t.id); else sessizSekme.add(t.id);
    try { await fetch((await relayAdr()) + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "nabiz", metin: ok ? "toplantı sekmesi yeniden yanıt veriyor" : `toplantı sekmesi yanıt vermiyor (${(r && r.err) || "yanıt yok"}) — sekmeyi yenile` }) }); } catch (e) {}
  }
}
function surumBuyuk(a, b) { const x = String(a).split(".").map(Number), y = String(b).split(".").map(Number); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; }
async function takvimBak() {
  try {
    const relay = await relayAdr(); const t = await (await fetch(relay + "/takvim?v=" + chrome.runtime.getManifest().version)).json();  // v0.13.5: ?v= — sihirbaz eklentiyi Teams açık olmadan da görür
    // v0.13.9: panodan güncellemeden sonra aktarıcı yeni sürümdeyse eklenti kendini diskten yeniler (Chrome'da elle ↻ gerekmez).
    // Toplantı sürerken yenilenmez (Teams sekmesindeki betik kopar); her aktarıcı sürümü için en çok bir kez (klasör güncellenmediyse döngü olmasın).
    if (t.surum && t.surum !== chrome.runtime.getManifest().version && !t.toplanti && surumBuyuk(t.surum, chrome.runtime.getManifest().version)) {
      const { yenilenen } = await chrome.storage.local.get({ yenilenen: null });
      if (yenilenen !== t.surum) { await chrome.storage.local.set({ yenilenen: t.surum }); chrome.runtime.reload(); return; }
    }
    if (t.claude_age_s != null && t.claude_age_s < 120) return;
    for (const o of t.olaylar || []) {
      if (o.dk > 5 || o.dk < -2 || bildirilen.has(o.id)) continue;
      bildirilen.add(o.id);
      chrome.notifications.create("tk:" + o.id, { type: "basic", iconUrl: "icons/128.png", requireInteraction: true, priority: 2,
        title: `${o.saat} · ${o.baslik}`.slice(0, 80), message: (o.dk > 0 ? L("{n} dk sonra başlıyor", { n: o.dk }) : L("Başlıyor")) + (o.platform ? ` (${({ teams: "Teams", meet: "Google Meet", zoom: "Zoom" })[o.platform] || o.platform})` : "") + L(". Suflor.me'yi başlatayım mı?"),
        buttons: [{ title: L("Suflor.me'yi başlat") }, { title: L("Panoyu aç") }] });
    }
  } catch (e) { /* aktarıcı kapalı ya da alan seçilmedi */ }
}
// v0.9.4: pano zaten açıksa o sekmeye geç (her pano sekmesi aktarıcıyı saniyede bir yokluyor; ikincisi gereksiz)
async function panoAc(relay) {
  const kok = relay.replace(/\/$/, "") + "/";
  const [t] = (await chrome.tabs.query({ url: kok + "*" })).filter(t => t.url === kok || t.url.startsWith(kok + "?") || t.url.startsWith(kok + "#"));
  if (t) { await chrome.tabs.update(t.id, { active: true }); await chrome.windows.update(t.windowId, { focused: true }); }
  else await chrome.tabs.create({ url: kok });
}
chrome.notifications.onButtonClicked.addListener(async (id, i) => {
  if (!id.startsWith("tk:")) return;
  chrome.notifications.clear(id);
  try {
    const relay = await relayAdr();
    if (i === 1) return panoAc(relay);
    const r = await (await fetch(relay + "/baslat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ olay: id.slice(3) }) })).json();
    // v0.9.5: hazırlık sekmesi — Claude izlemeye başlayınca (en geç 3 dk / toplantı saatinde) kendisi toplantıya geçer
    if (r.ok) chrome.tabs.create({ url: relay + "/hazirlik" });
    if (!r.ok) chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me başlatılamadı"), message: r.err || L("bilinmiyor") });
  } catch (e) { chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me başlatılamadı"), message: L(String(e.message || e).slice(0, 160)) }); }
});
