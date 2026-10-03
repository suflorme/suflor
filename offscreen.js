// Suflor.me v0.8.0 — offscreen belgesi: Teams sekmesinin sesi (diğer katılımcılar) → aktarıcı /ses, kanal "karsi".
// Arka plan betiği ⌥⇧W ya da popup ile chrome.tabCapture akış kimliğini alır, buraya gönderir. Sekme sesi yakalanınca
// Chrome sekmeyi kullanıcıya susturur — bu yüzden ses ayrı bir AudioContext ile hoparlöre geri verilir (kullanıcı duymaya
// devam eder). İşleme 16 kHz'te; parçalar 1 sn. Ses diske yazılmaz, yalnız 127.0.0.1'e gider.
let ak = null;
chrome.runtime.onMessage.addListener(m => {
  if (m.type === "offBasla") basla(m).catch(e => bitti("açılamadı: " + (e.name || e)));
  if (m.type === "offDur") bitti("istendi");
});
function olay(relay, tur, metin) { fetch(relay + "/olay", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tur, metin }) }).catch(() => {}); }
function b64(i16) { const u8 = new Uint8Array(i16.buffer); let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); }
async function basla({ id, relay, title }) {
  bitti("yeniden başlatılıyor", true);
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: id } }, video: false });
  const cal = new AudioContext(); cal.createMediaStreamSource(stream).connect(cal.destination);  // sekme sesi duyulmaya devam etsin
  const ctx = new AudioContext({ sampleRate: 16000 });
  const src = ctx.createMediaStreamSource(stream), proc = ctx.createScriptProcessor(4096, 1, 1), sus = ctx.createGain(); sus.gain.value = 0;
  ak = { stream, cal, ctx, relay, title, buf: [], n: 0, t0: 0 };
  proc.onaudioprocess = ev => {
    if (!ak) return; const f = ev.inputBuffer.getChannelData(0);
    if (!ak.n) ak.t0 = Date.now() - Math.round(f.length / 16);
    const i16 = new Int16Array(f.length); for (let i = 0; i < f.length; i++) i16[i] = Math.max(-1, Math.min(1, f[i])) * 32767;
    ak.buf.push(i16); ak.n += f.length; if (ak.n >= 16000) gonder();
  };
  src.connect(proc); proc.connect(sus); sus.connect(ctx.destination);
  stream.getAudioTracks().forEach(t => t.onended = () => bitti("sekme sesi bitti (sekme kapandı/yenilendi)"));
  olay(relay, "whisper-karsi", "açıldı — " + (title || "?"));
}
async function gonder() {
  const a0 = ak; if (!a0 || !a0.n) return;
  const a = new Int16Array(a0.n); let o = 0; a0.buf.forEach(p => { a.set(p, o); o += p.length; });
  const t0 = a0.t0; a0.buf = []; a0.n = 0;
  try {
    const r = await fetch(a0.relay + "/ses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kanal: "karsi", t: t0, pcm: b64(a), meeting: { title: a0.title } }) });
    const j = await r.json().catch(() => ({}));
    if (j.kapali) bitti("aktarıcıda Whisper yok");
  } catch (e) { /* aktarıcı kapalı: parça gider */ }
}
function bitti(neden, sessiz) {
  if (!ak) return; const a0 = ak; ak = null;
  a0.stream.getTracks().forEach(t => t.stop()); a0.ctx.close().catch(() => {}); a0.cal.close().catch(() => {});
  if (!sessiz) { olay(a0.relay, "whisper-karsi", "kapandı: " + neden); chrome.runtime.sendMessage({ type: "offBitti", neden }).catch(() => {}); }
}
