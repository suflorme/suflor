// Suflor.me v0.9.1 eklenti penceresi (v0.12.2: tr/en): bağlantı listesi (aktarıcı, toplantı, iki ses kanalı, Claude), pano, not, ayarlar.
// Durum doğrudan aktarıcıdan (/status) okunur — hangi sekme önde olursa olsun çalışır; öndeki toplantı sekmesi varsa
// bekleyen satır sayısı da ondan gelir.
const $ = id => document.getElementById(id);
// v0.12.2: arayüz dili (tr/en). Kaynak aktarıcının /status "arayuz_dili" alanı; chrome.storage.local "dil"de saklanır, yoksa "tr".
// Anahtar Türkçe metnin kendisi (pano ile aynı yaklaşım ve terimler); İngilizcesi yoksa Türkçe kalır.
let DIL = "tr";
const EN = {"Bu Chrome'un yazdığı çalışma alanı":"The workspace this Chrome writes to","Bu Chrome hangi çalışma alanına yazsın?":"Which workspace should this Chrome write to?",
"Bu Mac'te birden fazla Suflor.me aktarıcısı çalışıyor. Bir kez seç; Ayarlar'dan değiştirebilirsin.":"More than one Suflor.me relay is running on this Mac. Pick one once; you can change it in Settings.",
"Aktarıcı":"Relay","bakılıyor…":"checking…","Toplantı":"Meeting","Senin sesin":"Your voice","Karşı taraf":"Other side","Panoyu aç":"Open panel",
"Not düş · soru için başa ?, soru, Claude ya da iki boşluk (Enter: gönder)":"Write a note · start with ?, Claude or two spaces to ask (Enter: send)",
"Gönder":"Send","Ayarlar":"Settings","Aktarım açık":"Sending on","Whisper: konuşmayı bu Mac'te yazıya çevir":"Whisper: transcribe speech on this Mac",
"Toplantıya girince altyazıyı kendisi açsın":"Turn on captions automatically when joining","Satırı göndermeden önce bekleme":"Wait before sending a line",
"3 sn (hızlı)":"3 s (fast)","6 sn":"6 s","Uyarı kelimeleri (virgülle)":"Alert words (comma-separated)","Çalışma alanı":"Workspace","Aktarıcı adresi":"Relay address",
"Kaydet":"Save","Kaydedildi":"Saved","kapalı — aktarici-kur.command'a çift tıkla":"off — double-click aktarici-kur.command",
"{n} satır bekliyor; aktarıcı açılınca gönderilir.":"{n} lines waiting; they'll be sent once the relay is up.","çalışıyor · v{v}":"running · v{v}",
"toplantı sekmesi yok":"no meeting tab","{p} · transkript açık":"{p} · transcript open","{p} · altyazı açık":"{p} · captions on","{p} · döküm/altyazı kapalı":"{p} · transcript/captions off",
"{p} · toplantıda değil":"{p} · not in a meeting","Satır gelmiyor: ":"No lines coming in: ","altyazıyı aç":"turn on captions","Whisper kurulu değil":"Whisper not installed",
"altyazıdan":"from captions","yazılıyor":"transcribing","toplantıda sessizdesin":"you're muted in the meeting","kapalı":"off",
"Toplantı sekmesinde Option + Shift + W":"Option + Shift + W in the meeting tab","yazılıyor (yerel yardımcı)":"transcribing (local helper)","yerel yardımcı hazır":"local helper ready","Sistem sesi kaydı izni yok olabilir (Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı)":"System audio recording permission may be missing (System Settings → Privacy & Security → Screen & System Audio Recording)","Aç":"Turn on","istendi…":"requested…","izliyor":"watching",
"izlemiyor — /toplanti":"not watching — /toplanti","Dil: ":"Language: ","{n} satır aktarıcıya gönderilmeyi bekliyor.":"{n} lines waiting to be sent to the relay.",
"Claude'a soruldu":"Asked Claude","Geçersiz aktarıcı adresi — yalnız http://127.0.0.1:<port> ya da http://localhost:<port>; varsayılan kullanılıyor.":"Invalid relay address — only http://127.0.0.1:<port> or http://localhost:<port>; using the default.","Not kaydedildi":"Note saved","Aktarıcıya ulaşılamadı":"Can't reach the relay"};
function L(s, v) { let t = DIL === "en" && EN[s] || s; if (v) for (const k in v) t = t.split("{" + k + "}").join(v[k]); return t; }
function cevir(kok) {  // sabit HTML: metin düğümleri + placeholder/title/aria-label (yalnız tr → en)
  if (DIL !== "en") return; document.documentElement.lang = "en";
  const w = document.createTreeWalker(kok, NodeFilter.SHOW_TEXT), d = []; while (w.nextNode()) d.push(w.currentNode);
  d.forEach(n => { const k = n.nodeValue.trim(); if (k && EN[k]) n.nodeValue = n.nodeValue.replace(k, EN[k]); });
  kok.querySelectorAll("[placeholder],[title],[aria-label]").forEach(e => ["placeholder", "title", "aria-label"].forEach(a => { const k = e.getAttribute(a); if (k && EN[k]) e.setAttribute(a, EN[k]); }));
}
// Aktarıcının söylediği dil saklanandan farklıysa kaydet; sabit metinler yeniden çizilsin diye pencere bir kez yenilenir
function dilGuncelle(d) { if (d !== "tr" && d !== "en") d = "tr"; if (d === DIL) return; chrome.storage.local.set({ dil: d }); location.reload(); }
const PL = { teams: "Teams", meet: "Google Meet", zoom: "Zoom" };
// v0.12.3 (güvenlik denetimi O3): aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
let cfg = { relay: RELAY_VARSAYILAN, keywords: [], enabled: true, stableMs: 3000, autoCaptions: true, whisper: true };
$("ver").textContent = "v" + chrome.runtime.getManifest().version;
// v0.9.2: aktarıcı adresi bu tarayıcıda (storage.local) tutulur; diğer ayarlar eskisi gibi eşitlenir (sync)
chrome.storage.local.get({ dil: "tr" }, d => { DIL = d.dil === "en" ? "en" : "tr"; cevir(document.body); baslat(); });
function baslat() { chrome.storage.sync.get(cfg, v => {
  cfg = v; $("ac").checked = v.autoCaptions; $("wh").checked = v.whisper; $("kw").value = v.keywords.join(", "); $("en").checked = v.enabled; $("stab").value = String(v.stableMs);
  cfg.relay = relayGecerli(cfg.relay) || RELAY_VARSAYILAN;
  chrome.storage.local.get({ relay: null, relayOto: false }, l => { cfg.secildi = !!relayGecerli(l.relay); cfg.oto = !!l.relayOto; if (cfg.secildi) cfg.relay = relayGecerli(l.relay); $("relay").value = cfg.relay; kesfet().then(() => { durum(); setInterval(durum, 3000); }); });
}); }
function relaySec(adr) { adr = relayGecerli(adr) || RELAY_VARSAYILAN; cfg.relay = adr; cfg.secildi = true; $("relay").value = adr; chrome.storage.local.set({ relay: adr, relayOto: false, relayOtoUyari: false }); cfg.oto = false; $("sec").hidden = true; durum(); }
$("save").onclick = () => { chrome.storage.sync.set({ keywords: $("kw").value.split(",").map(s => s.trim()).filter(Boolean), enabled: $("en").checked, autoCaptions: $("ac").checked, whisper: $("wh").checked, stableMs: +$("stab").value });
  const gecerli = relayGecerli($("relay").value); relaySec($("relay").value);
  $("saveRes").textContent = gecerli ? L("Kaydedildi") : L("Geçersiz aktarıcı adresi — yalnız http://127.0.0.1:<port> ya da http://localhost:<port>; varsayılan kullanılıyor."); setTimeout(() => $("saveRes").textContent = "", gecerli ? 2500 : 6000); };
// v0.9.2: bu Mac'teki aktarıcıları bul (her macOS hesabının kendi portu: 8765, 8766 …). Birden fazlaysa ve henüz
// seçilmediyse seçtir — yanlış alana (ör. kişisel toplantı iş dökümüne) yazılmasın.
let bulunan = [];
async function kesfet() {
  const ports = [8765, 8766, 8767, 8768];
  bulunan = (await Promise.all(ports.map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const s = await (await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal })).json(); return { adr: `http://127.0.0.1:${p}`, alan: s.alan || "Suflor", ad: s.ad, port: p }; } catch { return null; } }))).filter(Boolean);
  $("alansec").replaceChildren(...bulunan.map(b => { const o = document.createElement("option"); o.value = b.adr; o.textContent = `${b.alan} · port ${b.port}`; return o; }));
  if (bulunan.some(b => b.adr === cfg.relay)) $("alansec").value = cfg.relay;
  $("alansec").onchange = () => relaySec($("alansec").value);
  if (bulunan.length > 1 && (!cfg.secildi || cfg.oto)) {  // v0.13.5: kendiliğinden seçilmişse de sor (gönderim sürer)
    $("secb").replaceChildren(...bulunan.map(b => { const x = document.createElement("button"); x.className = "pri"; x.textContent = b.alan; x.title = `${b.adr}${b.ad ? " · " + b.ad : ""}`; x.onclick = () => relaySec(b.adr); return x; }));
    $("sec").hidden = false;
  } else if (bulunan.length === 1 && !cfg.secildi) { relaySec(bulunan[0].adr); chrome.storage.local.set({ relayOto: true }); cfg.oto = true; }
}
function satir(id, renk, metin, dugme) {
  $("d-" + id).className = "dot " + (renk || ""); const v = $("v-" + id); v.replaceChildren();
  if (dugme) { const b = document.createElement("button"); b.className = "sm"; b.textContent = dugme[0]; b.onclick = dugme[1]; v.append(b); } else v.textContent = metin;
  if (dugme && metin) v.title = metin;
}
async function sekmeDurumu() {
  try { const [t] = await chrome.tabs.query({ active: true, currentWindow: true }); return await chrome.tabs.sendMessage(t.id, { type: "getStatus" }); } catch { return null; }
}
async function durum() {
  let s = null; try { const r = await fetch(cfg.relay + "/status"); s = await r.json(); } catch {}
  const t = await sekmeDurumu(), uy = [];
  if (!s) {
    satir("ak", "er", L("kapalı — aktarici-kur.command'a çift tıkla"));
    ["tp", "sn", "kr", "cl"].forEach(k => satir(k, "", "—"));
    if (t && t.queued) uy.push(L("{n} satır bekliyor; aktarıcı açılınca gönderilir.", { n: t.queued }));
    $("uy").textContent = uy.join(" "); return;
  }
  dilGuncelle(s.arayuz_dili);  // alan yoksa "tr"
  satir("ak", "ok", L("çalışıyor · v{v}", { v: s.surum || "?" })); $("alan").textContent = s.alan || "";
  const x = s.extension, ek = x && x.age_s < 30, w = s.whisper || {}, wak = ["hazir", "yukleniyor"].includes(w.durum);
  const pl = PL[(x && x.platform) || "teams"] || L("Toplantı");
  if (!ek) satir("tp", "", L("toplantı sekmesi yok"));
  else if (x.panel) satir("tp", "ok", L("{p} · transkript açık", { p: pl }));
  else if (x.captions) satir("tp", "ok", L("{p} · altyazı açık", { p: pl }));
  else if (wak && (w.ben || w.karsi)) satir("tp", "ok", `${pl} · Whisper`);
  else if (x.call) satir("tp", "er", L("{p} · döküm/altyazı kapalı", { p: pl }));
  else satir("tp", "", L("{p} · toplantıda değil", { p: pl }));
  if (ek && x.call && !x.panel && !x.captions && !(w.ben || w.karsi)) uy.push(L("Satır gelmiyor: ") + ((x.yonerge && x.yonerge.altyazi) || L("altyazıyı aç")) + ".");
  if (w.durum === "yok") { satir("sn", "", L("Whisper kurulu değil")); satir("kr", "", L("altyazıdan")); }
  else {
    satir("sn", w.ben ? "ok" : (ek && x.call ? "wa" : ""), L(w.ben ? "yazılıyor" : (t && t.whisper && t.whisper.sessiz ? "toplantıda sessizdesin" : "kapalı")));
    if (w.karsi) satir("kr", "ok", L(w.yerel_akiyor ? "yazılıyor (yerel yardımcı)" : "yazılıyor"));
    else if (["bekliyor", "dinliyor"].includes(w.yerel)) satir("kr", "", L("yerel yardımcı hazır"));  // v0.13.0
    else if (w.yerel === "izin") satir("kr", "wa", L("Sistem sesi kaydı izni yok olabilir (Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı)"), [L("Aç"), () => { chrome.runtime.sendMessage({ type: "whisperKarsi" }); satir("kr", "wa", L("istendi…")); }]);
    else satir("kr", ek && x.call ? "wa" : "", L("Toplantı sekmesinde Option + Shift + W"), [L("Aç"), () => { chrome.runtime.sendMessage({ type: "whisperKarsi" }); satir("kr", "wa", L("istendi…")); }]);
  }
  const ca = s.claude_age_s;
  satir("cl", ca != null && ca < 30 ? "ok" : (ca != null && ca < 120 ? "wa" : ""), L(ca != null && ca < 120 ? "izliyor" : "izlemiyor — /toplanti"));
  if (s.uyari) uy.push(s.uyari); if (s.dil && s.dil.uyari) uy.push(L("Dil: ") + s.dil.uyari);
  if (t && t.queued) uy.push(L("{n} satır aktarıcıya gönderilmeyi bekliyor.", { n: t.queued }));
  $("uy").textContent = uy.join(" ");
}
// v0.9.4: pano zaten açıksa o sekmeye geç (her pano sekmesi aktarıcıyı saniyede bir yokluyor; ikincisi gereksiz)
async function panoAc(relay) {
  const kok = relay.replace(/\/$/, "") + "/";
  const [t] = (await chrome.tabs.query({ url: kok + "*" })).filter(t => t.url === kok || t.url.startsWith(kok + "?") || t.url.startsWith(kok + "#"));
  if (t) { await chrome.tabs.update(t.id, { active: true }); await chrome.windows.update(t.windowId, { focused: true }); }
  else await chrome.tabs.create({ url: kok });
}
$("pano").onclick = () => panoAc(cfg.relay).then(() => window.close());
async function notGonder() {
  // v0.9.7: tek kutu — "?", "soru", "Claude" ya da iki boşlukla başlayan Claude'a soru, gerisi not (ayrım aktarıcıda; metin kırpılmaz)
  const text = $("note").value; if (!text.trim()) return;
  try { const r = await fetch(cfg.relay + "/girdi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, at: new Date().toISOString() }) }); if (!r.ok) throw 0; const j = await r.json(); $("note").value = ""; $("noteRes").textContent = L(j.tur === "soru" ? "Claude'a soruldu" : "Not kaydedildi"); }
  catch { $("noteRes").textContent = L("Aktarıcıya ulaşılamadı"); }
  setTimeout(() => $("noteRes").textContent = "", 2500);
}
$("send").onclick = notGonder;
$("note").onkeydown = ev => { if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); notGonder(); } };
