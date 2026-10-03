// Suflor.me v0.9.1 eklenti penceresi: bağlantı listesi (aktarıcı, toplantı, iki ses kanalı, Claude), pano, not, ayarlar.
// Durum doğrudan aktarıcıdan (/status) okunur — hangi sekme önde olursa olsun çalışır; öndeki toplantı sekmesi varsa
// bekleyen satır sayısı da ondan gelir.
const $ = id => document.getElementById(id);
const PL = { teams: "Teams", meet: "Google Meet", zoom: "Zoom" };
let cfg = { relay: "http://127.0.0.1:8765", keywords: [], enabled: true, stableMs: 3000, autoCaptions: true, whisper: true };
$("ver").textContent = "v" + chrome.runtime.getManifest().version;
// v0.9.2: aktarıcı adresi bu tarayıcıda (storage.local) tutulur; diğer ayarlar eskisi gibi eşitlenir (sync)
chrome.storage.sync.get(cfg, v => {
  cfg = v; $("ac").checked = v.autoCaptions; $("wh").checked = v.whisper; $("kw").value = v.keywords.join(", "); $("en").checked = v.enabled; $("stab").value = String(v.stableMs);
  chrome.storage.local.get({ relay: null }, l => { cfg.secildi = !!l.relay; if (l.relay) cfg.relay = l.relay; $("relay").value = cfg.relay; kesfet().then(() => { durum(); setInterval(durum, 3000); }); });
});
function relaySec(adr) { cfg.relay = adr; cfg.secildi = true; $("relay").value = adr; chrome.storage.local.set({ relay: adr }); $("sec").hidden = true; durum(); }
$("save").onclick = () => { chrome.storage.sync.set({ keywords: $("kw").value.split(",").map(s => s.trim()).filter(Boolean), enabled: $("en").checked, autoCaptions: $("ac").checked, whisper: $("wh").checked, stableMs: +$("stab").value });
  relaySec($("relay").value.trim()); $("saveRes").textContent = "Kaydedildi"; setTimeout(() => $("saveRes").textContent = "", 2500); };
// v0.9.2: bu Mac'teki aktarıcıları bul (her macOS hesabının kendi portu: 8765, 8766 …). Birden fazlaysa ve henüz
// seçilmediyse seçtir — yanlış alana (ör. kişisel toplantı iş dökümüne) yazılmasın.
let bulunan = [];
async function kesfet() {
  const ports = [8765, 8766, 8767, 8768];
  bulunan = (await Promise.all(ports.map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const s = await (await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal })).json(); return { adr: `http://127.0.0.1:${p}`, alan: s.alan || "Suflor", ad: s.ad, port: p }; } catch { return null; } }))).filter(Boolean);
  $("alansec").replaceChildren(...bulunan.map(b => { const o = document.createElement("option"); o.value = b.adr; o.textContent = `${b.alan} · port ${b.port}`; return o; }));
  if (bulunan.some(b => b.adr === cfg.relay)) $("alansec").value = cfg.relay;
  $("alansec").onchange = () => relaySec($("alansec").value);
  if (bulunan.length > 1 && !cfg.secildi) {
    $("secb").replaceChildren(...bulunan.map(b => { const x = document.createElement("button"); x.className = "pri"; x.textContent = b.alan; x.title = `${b.adr}${b.ad ? " · " + b.ad : ""}`; x.onclick = () => relaySec(b.adr); return x; }));
    $("sec").hidden = false;
  } else if (bulunan.length === 1 && !cfg.secildi && bulunan[0].adr !== cfg.relay) relaySec(bulunan[0].adr);
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
    satir("ak", "er", "kapalı — aktarici-kur.command'a çift tıkla");
    ["tp", "sn", "kr", "cl"].forEach(k => satir(k, "", "—"));
    if (t && t.queued) uy.push(`${t.queued} satır bekliyor; aktarıcı açılınca gönderilir.`);
    $("uy").textContent = uy.join(" "); return;
  }
  satir("ak", "ok", "çalışıyor · v" + (s.surum || "?")); $("alan").textContent = s.alan || "";
  const x = s.extension, ek = x && x.age_s < 30, w = s.whisper || {}, wak = ["hazir", "yukleniyor"].includes(w.durum);
  const pl = PL[(x && x.platform) || "teams"] || "Toplantı";
  if (!ek) satir("tp", "", "toplantı sekmesi yok");
  else if (x.panel) satir("tp", "ok", `${pl} · transkript açık`);
  else if (x.captions) satir("tp", "ok", `${pl} · altyazı açık`);
  else if (wak && (w.ben || w.karsi)) satir("tp", "ok", `${pl} · Whisper`);
  else if (x.call) satir("tp", "er", `${pl} · döküm/altyazı kapalı`);
  else satir("tp", "", `${pl} · toplantıda değil`);
  if (ek && x.call && !x.panel && !x.captions && !(w.ben || w.karsi)) uy.push("Satır gelmiyor: " + ((x.yonerge && x.yonerge.altyazi) || "altyazıyı aç") + ".");
  if (w.durum === "yok") { satir("sn", "", "Whisper kurulu değil"); satir("kr", "", "altyazıdan"); }
  else {
    satir("sn", w.ben ? "ok" : (ek && x.call ? "wa" : ""), w.ben ? "yazılıyor" : (t && t.whisper && t.whisper.sessiz ? "toplantıda sessizdesin" : "kapalı"));
    if (w.karsi) satir("kr", "ok", "yazılıyor");
    else satir("kr", ek && x.call ? "wa" : "", "Toplantı sekmesinde Option + Shift + W", ["Aç", () => { chrome.runtime.sendMessage({ type: "whisperKarsi" }); satir("kr", "wa", "istendi…"); }]);
  }
  const ca = s.claude_age_s;
  satir("cl", ca != null && ca < 30 ? "ok" : (ca != null && ca < 120 ? "wa" : ""), ca != null && ca < 120 ? "izliyor" : "izlemiyor — /toplanti");
  if (s.uyari) uy.push(s.uyari); if (s.dil && s.dil.uyari) uy.push("Dil: " + s.dil.uyari);
  if (t && t.queued) uy.push(`${t.queued} satır aktarıcıya gönderilmeyi bekliyor.`);
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
  try { const r = await fetch(cfg.relay + "/girdi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, at: new Date().toISOString() }) }); if (!r.ok) throw 0; const j = await r.json(); $("note").value = ""; $("noteRes").textContent = j.tur === "soru" ? "Claude'a soruldu" : "Not kaydedildi"; }
  catch { $("noteRes").textContent = "Aktarıcıya ulaşılamadı"; }
  setTimeout(() => $("noteRes").textContent = "", 2500);
}
$("send").onclick = notGonder;
$("note").onkeydown = ev => { if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); notGonder(); } };
