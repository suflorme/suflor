// Suflor.me v0.50.0 — toplantıya sesli söyle, web sürümü (sayfanın kendi bağlamı, MAIN world, document_start). Toplantı sitesinin kurduğu
// RTCPeerConnection'lar sayılır (sınıf alt sınıfla sarılır; davranış değişmez). İçerik betiği okunacak WAV'ı verince: canlı ses göndericisinin
// izi yalnız okuma süresince "mikrofon + Suflor" karışımıyla değiştirilir (replaceTrack), ses bitince ya da "dur"da asıl mikrofon izi geri konur.
// Özellik kullanılmadıkça toplantı sesine dokunulmaz. Mikrofon izi kapalıysa (enabled=false, sessiz) okunmaz. Sonuç içerik betiğine postMessage.
(() => {
  if (window.__suflorSoyle || !window.RTCPeerConnection) return; window.__suflorSoyle = true;
  const PCS = new Set(), Asil = window.RTCPeerConnection;
  class RTCPeerConnection extends Asil { constructor(...a) { super(...a); PCS.add(this); } }
  window.RTCPeerConnection = RTCPeerConnection;
  if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = RTCPeerConnection;
  const yaz = (id, durum) => window.postMessage({ __suflor: "soyleDurum", id, durum }, "*");
  let ak = null;  // {id, ctx, kaynak, degisen: [{s, asil, bizim}]}
  async function geriAl(neden) {
    const a = ak; if (!a) return; ak = null;
    try { a.kaynak.onended = null; a.kaynak.stop(); } catch (e) {}
    for (const d of a.degisen) { try { if (d.s.track === d.bizim) await d.s.replaceTrack(d.asil); } catch (e) {} }  // site izi değiştirdiyse ona dokunma
    a.ctx.close().catch(() => {}); yaz(a.id, neden);
  }
  async function cal(id, ses) {
    if (ak) await geriAl("durdu");
    const gonderen = [];
    for (const pc of [...PCS]) {
      if (pc.signalingState === "closed" || pc.connectionState === "closed") { PCS.delete(pc); continue; }
      for (const s of pc.getSenders()) if (s.track && s.track.kind === "audio" && s.track.readyState === "live") gonderen.push(s);
    }
    if (!gonderen.length) return yaz(id, "baglanti-yok");
    const acik = gonderen.filter(s => s.track.enabled && !s.track.muted);
    if (!acik.length) return yaz(id, "sessiz");
    let ctx = null;
    try {
      ctx = new AudioContext(); if (ctx.state === "suspended") await ctx.resume().catch(() => {});
      const tampon = await ctx.decodeAudioData(ses.slice(0)), kaynak = ctx.createBufferSource(); kaynak.buffer = tampon;
      const a = { id, ctx, kaynak, degisen: [] };
      for (const s of acik) {
        const hedef = ctx.createMediaStreamDestination(), asil = s.track;
        ctx.createMediaStreamSource(new MediaStream([asil])).connect(hedef); kaynak.connect(hedef);
        const bizim = hedef.stream.getAudioTracks()[0];
        await s.replaceTrack(bizim); a.degisen.push({ s, asil, bizim });
      }
      ak = a; kaynak.onended = () => { if (ak === a) geriAl("bitti"); };
      kaynak.start(); yaz(id, "caliyor");
    } catch (e) {
      if (ak) await geriAl("hata:" + (e.name || "?"));
      else { if (ctx) ctx.close().catch(() => {}); yaz(id, "hata:" + (e.name || "?")); }
    }
  }
  window.addEventListener("message", e => {
    if (e.source !== window || !e.data || e.data.__suflor !== "soyle") return;
    if (e.data.komut === "cal" && e.data.ses instanceof ArrayBuffer) cal(e.data.id, e.data.ses);
    if (e.data.komut === "dur") geriAl("durdu");
  });
})();
