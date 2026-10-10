// Servis çalışanı: rozet (badge), bildirim, v0.7.0 kanıt ekran görüntüsü
let state = { ok: null, at: 0, meeting: "", failCount: 0, queued: 0 };
// arayüz dili (tr/en) — bildirim ve şerit toast metinleri. İçerik betiği ve popup aktarıcının /status "arayuz_dili"
// alanını chrome.storage.local "dil"e yazar; burada yalnız okunur (yoksa "tr"). Aktarıcıya giden metinler (/olay) çevrilmez.
let DIL = "tr";
chrome.storage.local.get({ dil: "tr" }, v => { DIL = v.dil === "en" ? "en" : "tr"; });
chrome.storage.onChanged.addListener((ch, alan) => { if (alan === "local" && ch.dil) DIL = ch.dil.newValue === "en" ? "en" : "tr"; });
importScripts("pano/dil.js");  // arayüz metinlerinin İngilizcesi (tek kaynak)
importScripts("yerel-anahtar.js");  // v0.14.0 yerel anahtar: aktarıcıya giden fetch'e başlık
const EN = globalThis.SUFLOR_EN || {};
function L(s, v) { let t = DIL === "en" && EN[s] || s; if (v) for (const k in v) t = t.split("{" + k + "}").join(v[k]); return t; }
// toplantı sekmesi adresleri manifest'ten — platform dosyası (platform-*.js) yükleyen içerik betiği girdileri.
// Yeni platform yalnız manifest'e eklenir. tabs.query kalıbında port olmaz (test sayfası 127.0.0.1:8797 → 127.0.0.1).
const TOPLANTI_URL = [...new Set(chrome.runtime.getManifest().content_scripts
  .filter(cs => (cs.js || []).some(j => j.startsWith("platform-"))).flatMap(cs => cs.matches).map(m => m.replace(/:\d+\//, "/")))];
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "status") {
    state = Object.assign(state, msg);
    if (sender.tab && msg.call) { callTab = sender.tab.id; callAt = Date.now(); }  // toplantıdaki sekme
    const queued = msg.queued || 0;
    // rozet yalnız eylem gerektiğinde: bekleyen satır sayısı ya da "!" (aktarıcıya ulaşılamıyor); her şey yolundayken boş
    chrome.action.setBadgeText({ text: queued ? String(Math.min(queued, 99)) : (msg.ok ? "" : "!") });
    chrome.action.setBadgeBackgroundColor({ color: "#b3412e" });
  }
  if (msg.type === "kanit") kanit(sender.tab, msg.kaynak, msg.istek, msg.not);
  if (msg.type === "otoKare") otoKare(sender.tab, msg.maske);
  if (msg.type === "whisperKarsi") karsiBaslat(null, "popup");       // popup düğmesi (eklenti çağrıldı: izin var)
  if (msg.type === "whisperKarsiDur") offDur();                       // toplantıdan çıkıldı
  if (msg.type === "offBitti") karsiTab = null;
});
// Üç kısayol (manifest "commands"): Option + Shift + K kanıt — hangi pencere önde olursa olsun Teams sekmesini çeker, pano öndeyken
// de çalışır; Option + Shift + O "Ne diyeyim?" (tek cümlelik replik); Option + Shift + M sessiz (10 dk kart yok, tekrar basınca kapanır). ⭐ önemli an
// panoda düğme; karşı tarafın sesi yerel ses yardımcısında (yedek: popup).
chrome.commands.onCommand.addListener(cmd => { if (cmd === "kanit") kanit(null, "kisayol"); if (cmd === "ozet" || cmd === "sessiz") komut(cmd); });
// "Ne diyeyim?" ve sessiz (kısayol) — "Suflor, …" sesli komutlarının yerine.
// Onay şeritte aktarıcının "komut" alanından gelir (Teams'te yeşil toast); aktarıcıya ulaşılamazsa bildirim.
async function komut(tur) {
  try {  // toplantı adı gönderilmez: aktarıcı süren toplantıya yazar (sekme başlığı "Calendar" olabiliyor)
    const r = await fetch((await relayAdr()) + "/komut", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur }) });
    if (!r.ok) throw new Error("aktarıcı HTTP " + r.status);
  } catch (e) {
    chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: "Suflor.me", message: L(tur === "onemli" ? "⭐ işaretlenemedi: " : tur === "sessiz" ? "Sessiz açılamadı: " : "Ne diyeyim? istenemedi: ") + (/Failed to fetch/i.test(String(e)) ? L("aktarıcıya ulaşılamadı (127.0.0.1:8765)") : L(String(e.message || e))) });
  }
}

// Whisper karşı kanal: Teams sekmesinin sesi (diğer katılımcılar). chrome.tabCapture yalnız kullanıcı eklentiyi
// çağırınca (popup düğmesi) izin verir; akış offscreen belgesinde işlenir (servis çalışanında ses yok).
let karsiTab = null, callTab = null, callAt = 0;
async function offscreenAc() {
  const var_ = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (var_.length) return;
  await chrome.offscreen.createDocument({ url: "offscreen.html", reasons: ["USER_MEDIA"], justification: "Teams toplantı sesini yerel Whisper aktarıcısına (127.0.0.1) vermek" });
}
function bilgi(tab, text, renk, ms) { if (tab) chrome.tabs.sendMessage(tab.id, { type: "bilgi", text, renk, ms }, { frameId: 0 }).catch(() => {}); }
// adres önce bu tarayıcının yerel ayarından (çalışma alanı seçimi), yoksa eski eşitlenen ayardan
// Seçim yoksa aktarıcılar yoklanır: tek aktarıcı → o; birden fazla → hata (yanlış alana kanıt yazılmasın); hiç yok → eski ayar.
// (güvenlik denetimi O3) aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
// anahtar alınamadıysa nedeni (Chrome'un hata metni + eklenti kimliği) aktarıcı günlüğüne 10 dk'da bir — kimlik yardımcı tanımındakiyle
// tutmuyorsa ayara "eklenti_kimlik" eklenir. Kimlik gizli değil; anahtar gönderilmez.
let anahtarOlay = 0;
// yoklamada 401 de "aktarıcı burada" sayılır (v0.14: anahtarsız okuma 401) — yoksa yardımcısız eklenti kendi aktarıcısını görmez,
// aynı Mac'teki diğer hesabın eski aktarıcısını tek aday sanıp ona yazar
async function relayAdr() {
  const k = await SuflorAnahtar.al(); if (k) return `http://127.0.0.1:${k.port}`;  // v0.14.0: yardımcı bu kullanıcının aktarıcısını söyler
  if (Date.now() - anahtarOlay > 600000) { anahtarOlay = Date.now(); setTimeout(() => relayAdr().then(r => fetch(r + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "anahtar", metin: `yerel anahtar alınamadı: ${SuflorAnahtar.hata() || "?"} · eklenti ${chrome.runtime.id}` }) })).catch(() => {}), 0); }
  const l = relayGecerli((await chrome.storage.local.get({ relay: null })).relay); if (l) return l;
  const bul = (await Promise.all([8765, 8766, 8767, 8768].map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const r = await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal }); return r.ok || r.status === 401 ? `http://127.0.0.1:${p}` : null; } catch (e) { return null; } }))).filter(Boolean);
  if (bul.length > 1) throw new Error("Çalışma alanı seçilmedi — Suflor.me simgesine tıklayıp seç.");
  if (bul.length === 1) chrome.storage.local.set({ relay: bul[0], relayOto: true });  // tek aktarıcı kendiliğinden kaydedilir (content.js ile aynı)
  return bul[0] || relayGecerli((await chrome.storage.sync.get({ relay: RELAY_VARSAYILAN })).relay) || RELAY_VARSAYILAN;
}
async function karsiBaslat(hint, kaynak) {
  const tab = await toplantiSekmesi(hint);
  if (!tab) return chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: "Suflor.me Whisper", message: L("Açık toplantı sekmesi yok (Teams).") });
  let relay; try { relay = await relayAdr(); } catch (e) { return bilgi(tab, L(e.message), "#b26a00", 10000); }  // alan seçilmedi
  const olay = metin => fetch(relay + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur: "whisper-karsi", metin }) }).catch(() => {});
  // (2 Ekim denemesi) ikinci basış "Cannot capture a tab with an active stream" kırmızısı veriyordu — zaten açık
  if (karsiTab === tab.id) return bilgi(tab, L("🎙 Karşı tarafın sesi zaten yazılıyor"), "#1b8a3a", 3000);
  try {
    let id;
    try { id = await chrome.tabCapture.getMediaStreamId({ targetTabId: tab.id }); }
    catch (e) {
      // Chrome yalnız eklentinin çağrıldığı (öndeki) sekmeyi verir. Teams sekmesi arkadaysa öne getir, bir kez daha bastır.
      if (/active stream/i.test(String(e))) { karsiTab = tab.id; return bilgi(tab, L("🎙 Karşı tarafın sesi zaten yazılıyor"), "#1b8a3a", 3000); }
      if (tab.active) throw e;
      await chrome.tabs.update(tab.id, { active: true }); await chrome.windows.update(tab.windowId, { focused: true }).catch(() => {});
      bilgi(tab, L("Toplantı sekmesini öne getirdim — karşı tarafın sesi için Suflor.me simgesi → Karşı taraf → Aç'a bir kez daha bas"), "#1b6ef3", 10000);
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

// Kanıt: Teams sekmesinin görünen alanı PNG olarak aktarıcıya gider (kanit/<toplantı>/…png). Akış durmaz:
// diyalog yok; şerit ve uyarı çekim anında gizlenir, sonra 2 sn'lik yeşil onay. Çekim yalnız sekme penceresinde öndeyse
// mümkün (Chrome kısıtı); değilse kırmızı uyarı + bildirim.
let busy = false;
async function toplantiSekmesi(hint) {
  if (hint && hint.id != null) return hint;
  const tabs = await chrome.tabs.query({ url: TOPLANTI_URL });
  if (!tabs.length) return null;
  const [focused] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (focused && tabs.some(t => t.id === focused.id)) return focused;
  // toplantıdaki sekme (son 30 sn'de "call" bildirdi) — takvim/sohbet sekmesi ondan sonra gelir
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
// 1 Ekim 22:5x şerit 📷 kanıtı aktarıcıya hiç ulaşmadı (günlükte iz yok) — olası neden: yanıtlanmayan bir mesaj
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
    // Teams sekmesi penceresinde arkadaysa (pano/başka sekme önde) bir an öne getir, çek, eski sekmeye dön
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
    if (kaynak === "oto") {  // kendiliğinden kanıt: toast ve bildirim yok, yalnız günlük
      if (j.sinir && !OTO.sinir) { OTO.sinir = true; kanitOlay("oto: toplantı sınırı doldu, kendiliğinden kanıt durdu"); }
      else if (!j.ok) kanitOlay("oto: " + (j.err || "aktarıcı HTTP " + r.status));
      return;
    }
    if (!r.ok || !j.ok) return hata(tab, j.err || ("aktarıcı HTTP " + r.status));
    if (!j.dup) chrome.tabs.sendMessage(tab.id, { type: "kanitBitti", ok: true, n: j.n }, { frameId: 0 }).catch(() => {});
  } catch (e) {
    if (kaynak === "oto") return kanitOlay("oto: " + String(e.message || e).slice(0, 160));
    hata(tab, /Failed to fetch/i.test(String(e)) ? "Aktarıcıya ulaşılamadı (çalışma alanının aktarıcısı kapalı)." : String(e.message || e).slice(0, 160));
  } finally { busy = false; }
}
// Yaparken kaydet (kip panodan ya da Claude'dan açılır): içerik betiği 3 sn'de bir çağırır. Sekme penceresinde öndeyse küçük JPEG çekilir,
// 64×36 gri ızgarada önceki kareyle karşılaştırılır (şerit/uyarı maskeli). Belirgin değişimden (hücrelerin ≥ %6'sı) sonra ekran durulunca
// (< %1,5) ve son kendiliğinden kanıttan ≥ 10 sn geçtiyse tam kanıt alınır (kaynak "oto"). Kip açılınca ilk ekran da alınır. Sekme arkadaysa
// hiç çekilmez: kendiliğinden kanıt için sekme öne getirilmez. 15 sn kare gelmezse (kip kapandı, sekme arkada) karşılaştırma baştan başlar.
const OTO = { kare: null, degisti: false, son: 0, t: 0, sinir: false };
const OTO_W = 64, OTO_H = 36, OTO_FARK = 24, OTO_DEGISIM = 0.06, OTO_DURGUN = 0.015, OTO_ARA = 10000;
async function otoKare(tab, maske) {
  if (!tab || !tab.active || busy || OTO.sinir) return;
  if (Date.now() - OTO.t > 15000) Object.assign(OTO, { kare: null, degisti: false, son: 0 });
  OTO.t = Date.now();
  let g;
  try {
    const jpg = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 40 });
    const bmp = await createImageBitmap(await (await fetch(jpg)).blob());
    const c = new OffscreenCanvas(OTO_W, OTO_H), x = c.getContext("2d", { willReadFrequently: true });
    x.drawImage(bmp, 0, 0, OTO_W, OTO_H); bmp.close();
    const d = x.getImageData(0, 0, OTO_W, OTO_H).data; g = new Uint8Array(OTO_W * OTO_H);
    for (let i = 0; i < g.length; i++) g[i] = (d[i * 4] * 77 + d[i * 4 + 1] * 150 + d[i * 4 + 2] * 29) >> 8;
    for (const m of maske || []) {
      const x0 = Math.max(0, Math.floor(m.x * OTO_W)), x1 = Math.min(OTO_W, Math.ceil((m.x + m.w) * OTO_W));
      const y0 = Math.max(0, Math.floor(m.y * OTO_H)), y1 = Math.min(OTO_H, Math.ceil((m.y + m.h) * OTO_H));
      for (let y = y0; y < y1; y++) g.fill(0, y * OTO_W + x0, y * OTO_W + x1);
    }
  } catch (e) { return; }  // sekme o an çekilemiyor (pencere simge durumunda ya da sayfa değişiyor): sonraki karede
  const once = OTO.kare; OTO.kare = g;
  if (!once) { OTO.degisti = true; return otoAl(tab, 0); }  // kip yeni açıldı (ya da sekme geri geldi): ilk ekran
  let n = 0; for (let i = 0; i < g.length; i++) if (Math.abs(g[i] - once[i]) > OTO_FARK) n++;
  return otoAl(tab, n / g.length);
}
function otoAl(tab, oran) {
  if (oran >= OTO_DEGISIM) OTO.degisti = true;
  if (!OTO.degisti || oran >= OTO_DURGUN || Date.now() - OTO.son < OTO_ARA) return;
  OTO.degisti = false; OTO.son = Date.now(); return kanit(tab, "oto");
}

// toplantı hatırlatması: dakikada bir aktarıcının takvimine bakar (Mac Takvim, Suflor Takvim yardımcısı). Bir toplantı
// ≤ 5 dk sonra başlıyorsa ve Claude bu alanda izlemiyorsa bildirim: "Suflor'u başlat" (Terminal'de /toplanti) · "Panoyu aç".
// Her toplantı için bir kez. Çalışma alanı seçilmemişse (iki aktarıcı) bildirim yok.
chrome.alarms.create("takvim", { periodInMinutes: 1 });
const bildirilen = new Set();
chrome.alarms.onAlarm.addListener(a => { if (a.name === "takvim") takvimBak(); if (a.name === "nabiz") nabizYokla(); });
// yüklenince ve Chrome açılınca hemen bir kez (sihirbazın eklenti adımı dakikayı beklemesin)
// "Aktarım açık" anahtarı popup'tan kalktı (v0.13.28): kapalı kalmışsa bir kez açılır, yoksa geri açmanın yolu olmaz
chrome.runtime.onInstalled.addListener(() => chrome.storage.sync.set({ enabled: true }));
chrome.runtime.onInstalled.addListener(() => takvimBak()); chrome.runtime.onStartup.addListener(() => takvimBak());
// nabız yedeği: 3 Ekim denemesinde Teams sekmesinin nabzı ~7 dk kesildi (mikrofon sesi akarken). 30 sn'de bir her
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
    const relay = await relayAdr(); const t = await (await fetch(relay + "/takvim?v=" + chrome.runtime.getManifest().version)).json();  // ?v= — sihirbaz eklentiyi Teams açık olmadan da görür
    // panodan güncellemeden sonra aktarıcı yeni sürümdeyse eklenti kendini diskten yeniler (Chrome'da elle ↻ gerekmez).
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
// pano zaten açıksa o sekmeye geç (her pano sekmesi aktarıcıyı saniyede bir yokluyor; ikincisi gereksiz). Yeni sekme anahtarla
// açılır (?k=; pano kendi deposuna alıp adres çubuğundan siler) — açık sekme de odaklanınca anahtarı bir kez daha alır.
const anahtarli = async (url) => { const k = await SuflorAnahtar.al(); return k && url.startsWith(`http://127.0.0.1:${k.port}/`) ? url + (url.includes("?") ? "&" : "?") + "k=" + k.anahtar : url; };
async function panoAc(relay) {
  const kok = relay.replace(/\/$/, "") + "/";
  const [t] = (await chrome.tabs.query({ url: kok + "*" })).filter(t => t.url === kok || t.url.startsWith(kok + "?") || t.url.startsWith(kok + "#"));
  if (t) { await chrome.tabs.update(t.id, Object.assign({ active: true }, (t.title || "").startsWith("🔑") ? { url: await anahtarli(kok) } : {})); await chrome.windows.update(t.windowId, { focused: true }); }  // 🔑: pano anahtarsız
  else await chrome.tabs.create({ url: await anahtarli(kok) });
}
chrome.notifications.onButtonClicked.addListener(async (id, i) => {
  if (!id.startsWith("tk:")) return;
  chrome.notifications.clear(id);
  try {
    const relay = await relayAdr();
    if (i === 1) return panoAc(relay);
    const r = await (await fetch(relay + "/baslat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ olay: id.slice(3) }) })).json();
    // hazırlık sekmesi — Claude izlemeye başlayınca (en geç 3 dk / toplantı saatinde) kendisi toplantıya geçer
    if (r.ok) chrome.tabs.create({ url: await anahtarli(relay + "/hazirlik") });
    if (!r.ok) chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me başlatılamadı"), message: r.err || L("bilinmiyor") });
  } catch (e) { chrome.notifications.create({ type: "basic", iconUrl: "icons/128.png", title: L("Suflor.me başlatılamadı"), message: L(String(e.message || e).slice(0, 160)) }); }
});
