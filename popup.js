// Suflor.me eklenti penceresi (tr/en): tek durum cümlesi (panoyla aynı mantık) + varsa tek çözüm düğmesi, Panoyu aç, tek ayar
// (sesi Mac'te yazıya çevir); çalışma alanı seçimi yalnız bu Mac'te birden fazla aktarıcı varken.
// Durum doğrudan aktarıcıdan (/status) okunur — hangi sekme önde olursa olsun çalışır; öndeki toplantı sekmesi varsa
// bekleyen satır sayısı da ondan gelir.
const $ = id => document.getElementById(id);
// arayüz dili (tr/en). Kaynak aktarıcının /status "arayuz_dili" alanı; chrome.storage.local "dil"de saklanır, yoksa "tr".
// Anahtar Türkçe metnin kendisi (pano ile aynı yaklaşım ve terimler); İngilizcesi yoksa Türkçe kalır.
let DIL = "tr";
const EN = {"Bu Chrome'un yazdığı çalışma alanı": "The workspace this Chrome writes to", "Bu Chrome hangi çalışma alanına yazsın?": "Which workspace should this Chrome write to?", "Bu Mac'te birden fazla Suflor.me aktarıcısı çalışıyor. Bir kez seç; Ayarlar'dan değiştirebilirsin.": "More than one Suflor.me relay is running on this Mac. Pick one once; you can change it in Settings.", "bakılıyor…": "checking…", "Panoyu aç": "Open panel", "Ayarlar": "Settings", "Sesi Mac'te yazıya çevir": "Transcribe audio on this Mac", "Çalışma alanı": "Workspace", "Suflor.me kapalı": "Suflor.me is off", "kurulum klasöründe aktarici-kur'a çift tıkla": "double-click aktarici-kur in the install folder", "{n} satır bekliyor; Suflor.me açılınca gönderilir.": "{n} lines waiting; they'll be sent once Suflor.me is up.", "Döküm dili yanlış": "Transcript language is wrong", "altyazıyı aç": "turn on captions", "Satır gelmiyor": "No lines coming in", "Altyazıyı aç: ": "Turn on captions: ", "Karşı taraf: izin gerekiyor": "Other side: permission needed", "Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı → Suflor Ses": "System Settings → Privacy & Security → Screen & System Audio Recording → Suflor Ses", "Karşı taraf: ses yazılmıyor": "Other side: not being transcribed", "Aç": "Open", "istendi…": "requested…", "Senin sesin yazılmıyor": "Your voice isn't being transcribed", "mikrofon açılamadı — toplantı sekmesini yenile": "couldn't open the microphone — reload the meeting tab", "mikrofon açık ama ses gelmiyor": "microphone is on but no audio is coming in", "Claude izlemiyor — kart gelmez": "Claude isn't watching — no cards will come", "Panodan başlat": "Start it from the panel", "Dinliyorum": "Listening", "1 açık kart": "1 open card", "{n} açık kart": "{n} open cards", "Claude hazır — toplantı bekleniyor": "Claude is ready — waiting for a meeting", "Hazır — toplantı bekleniyor": "Ready — waiting for a meeting"};
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
// (güvenlik denetimi O3) aktarıcı adresi yalnız bu Mac (127.0.0.1/localhost, port 1024–65535) — döküm başka yere gitmesin
const RELAY_VARSAYILAN = "http://127.0.0.1:8765";
function relayGecerli(a) { const m = /^http:\/\/(127\.0\.0\.1|localhost):(\d{4,5})\/?$/.exec(String(a || "").trim()); return m && +m[2] >= 1024 && +m[2] <= 65535 ? `http://${m[1]}:${m[2]}` : null; }
let cfg = { relay: RELAY_VARSAYILAN, enabled: true, stableMs: 3000, autoCaptions: true, whisper: true };
// aktarıcı adresi bu tarayıcıda (storage.local) tutulur; diğer ayarlar eskisi gibi eşitlenir (sync)
chrome.storage.local.get({ dil: "tr" }, d => { DIL = d.dil === "en" ? "en" : "tr"; cevir(document.body); baslat(); });
function baslat() { chrome.storage.sync.get(cfg, v => {
  cfg = v; $("wh").checked = v.whisper;
  cfg.relay = relayGecerli(cfg.relay) || RELAY_VARSAYILAN;
  chrome.storage.local.get({ relay: null, relayOto: false }, l => { cfg.secildi = !!relayGecerli(l.relay); cfg.oto = !!l.relayOto; if (cfg.secildi) cfg.relay = relayGecerli(l.relay); kesfet().then(() => { durum(); setInterval(durum, 3000); }); });
}); }
$("wh").onchange = () => chrome.storage.sync.set({ whisper: $("wh").checked });  // tek ayar: değişince kaydedilir
function relaySec(adr) { adr = relayGecerli(adr) || RELAY_VARSAYILAN; cfg.relay = adr; cfg.secildi = true; chrome.storage.local.set({ relay: adr, relayOto: false, relayOtoUyari: false }); cfg.oto = false; $("sec").hidden = true; durum(); }
// bu Mac'teki aktarıcıları bul (her macOS hesabının kendi portu: 8765, 8766 …). Birden fazlaysa ve henüz
// seçilmediyse seçtir — yanlış alana (ör. kişisel toplantı iş dökümüne) yazılmasın.
let bulunan = [];
async function kesfet() {
  const ports = [8765, 8766, 8767, 8768];
  bulunan = (await Promise.all(ports.map(async p => { try { const c = new AbortController(); setTimeout(() => c.abort(), 800); const s = await (await fetch(`http://127.0.0.1:${p}/status`, { signal: c.signal })).json(); return { adr: `http://127.0.0.1:${p}`, alan: s.alan || "Suflor", ad: s.ad, port: p }; } catch { return null; } }))).filter(Boolean);
  $("alansec").replaceChildren(...bulunan.map(b => { const o = document.createElement("option"); o.value = b.adr; o.textContent = `${b.alan} · port ${b.port}`; return o; }));
  if (bulunan.some(b => b.adr === cfg.relay)) $("alansec").value = cfg.relay;
  $("alansec").onchange = () => relaySec($("alansec").value);
  $("alanl").hidden = bulunan.length < 2;  // tek aktarıcıda seçim yok
  if (bulunan.length > 1 && (!cfg.secildi || cfg.oto)) {  // kendiliğinden seçilmişse de sor (gönderim sürer)
    $("secb").replaceChildren(...bulunan.map(b => { const x = document.createElement("button"); x.className = "pri"; x.textContent = b.alan; x.title = `${b.adr}${b.ad ? " · " + b.ad : ""}`; x.onclick = () => relaySec(b.adr); return x; }));
    $("sec").hidden = false;
  } else if (bulunan.length === 1 && !cfg.secildi) { relaySec(bulunan[0].adr); chrome.storage.local.set({ relayOto: true }); cfg.oto = true; }
}
async function sekmeDurumu() {
  try { const [t] = await chrome.tabs.query({ active: true, currentWindow: true }); return await chrome.tabs.sendMessage(t.id, { type: "getStatus" }); } catch { return null; }
}
// tek durum: [renk, cümle, ayrıntı, düğme?]. Önce kırmızı, sonra turuncu sorun; yoksa toplantıda "Dinliyorum", değilse bekliyor.
// Karşı ses sorunu "Karşı taraf: …" + Aç olarak yazılır — yönergelerdeki "Suflor.me simgesi → Karşı taraf → Aç" yolu.
function ciz(c, m, a, e) {
  $("durum").className = "durum " + c; $("dd").className = "dot " + (c === "nt" ? "" : c); $("dm").textContent = m; $("da").textContent = a || "";
  const d = $("de"); d.replaceChildren(); if (e) { const b = document.createElement("button"); b.className = "pri sm"; b.textContent = e[0]; b.onclick = e[1]; d.append(b); }
}
const karsiAc = () => { chrome.runtime.sendMessage({ type: "whisperKarsi" }); $("da").textContent = L("istendi…"); };
async function durum() {
  let s = null; try { const r = await fetch(cfg.relay + "/status"); s = await r.json(); } catch {}
  const t = await sekmeDurumu(), bek = t && t.queued ? L("{n} satır bekliyor; Suflor.me açılınca gönderilir.", { n: t.queued }) : "";
  if (!s) return ciz("er", L("Suflor.me kapalı"), bek || L("kurulum klasöründe aktarici-kur'a çift tıkla"));
  dilGuncelle(s.arayuz_dili);  // alan yoksa "tr"
  $("alan").textContent = bulunan.length > 1 ? (s.alan || "") : "";
  const x = s.extension, ek = x && x.age_s < 30, cagri = ek && x.call, w = s.whisper || {}, ca = s.claude_age_s, izl = ca != null && ca < 120, so = [];
  if (s.uyari) so.push(["er", s.uyari]);
  if (s.dil && s.dil.uyari) so.push(["er", L("Döküm dili yanlış"), s.dil.uyari]);
  if (cagri) {
    const yon = (x.yonerge && x.yonerge.altyazi) || L("altyazıyı aç");
    if (!(x.panel || x.captions || w.ben || w.karsi)) so.push(["wa", L("Satır gelmiyor"), L("Altyazıyı aç: ") + yon]);
    else if (w.durum && w.durum !== "yok") {
      if (w.yerel === "izin") so.push(["wa", L("Karşı taraf: izin gerekiyor"), L("Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı → Suflor Ses"), [L("Aç"), karsiAc]]);
      else if (!w.karsi && !x.captions && !x.panel && !["bekliyor", "dinliyor"].includes(w.yerel)) so.push(["wa", L("Karşı taraf: ses yazılmıyor"), "", [L("Aç"), karsiAc]]);
      if (!w.ben && ["hata", "sorun"].includes(w.ben_kod)) so.push(["wa", L("Senin sesin yazılmıyor"), L(w.ben_kod === "hata" ? "mikrofon açılamadı — toplantı sekmesini yenile" : "mikrofon açık ama ses gelmiyor")]);
    }
    if (!izl) so.push(["wa", L("Claude izlemiyor — kart gelmez"), L("Panodan başlat")]);
  }
  if (bek) so.push(["wa", bek]);
  const o = so.find(([c]) => c === "er") || so[0];
  if (o) return ciz(o[0], o[1], o[2], o[3]);
  const n = (s.cards || []).length;
  if (cagri) return ciz("ok", L("Dinliyorum"), n ? L(n === 1 ? "1 açık kart" : "{n} açık kart", { n }) : "");
  ciz("nt", L(izl ? "Claude hazır — toplantı bekleniyor" : "Hazır — toplantı bekleniyor"));
}
// pano zaten açıksa o sekmeye geç (her pano sekmesi aktarıcıyı saniyede bir yokluyor; ikincisi gereksiz)
async function panoAc(relay) {
  const kok = relay.replace(/\/$/, "") + "/";
  const [t] = (await chrome.tabs.query({ url: kok + "*" })).filter(t => t.url === kok || t.url.startsWith(kok + "?") || t.url.startsWith(kok + "#"));
  if (t) { await chrome.tabs.update(t.id, { active: true }); await chrome.windows.update(t.windowId, { focused: true }); }
  else await chrome.tabs.create({ url: kok });
}
$("pano").onclick = () => panoAc(cfg.relay).then(() => window.close());
