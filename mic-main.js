// Suflor.me v0.8.0 — Teams sayfasının kendi bağlamında (MAIN world) mikrofon yakalama. İçerik betiğinin yalıtılmış
// bağlamında Web Audio mikrofon akışından sessizlik okuyordu (headless Chrome, 1 Ekim: iz canlı, örnekler 0); sayfa
// bağlamında aynı kod çalışıyor. Bu betik yalnız içerik betiğinin komutuyla açılır/kapanır ve 16 kHz PCM parçalarını
// window.postMessage ile içerik betiğine verir; aktarıcıya gönderen içerik betiğidir. Teams'in kendi mikrofon izni kullanılır.
(() => {
  if (window.__suflorMic) return; window.__suflorMic = true;
  let ak = null;
  const yaz = o => window.postMessage(Object.assign({ __suflor: "micDurum" }, o), "*");
  window.addEventListener("message", async e => {
    if (e.source !== window || !e.data || e.data.__suflor !== "mic") return;
    if (e.data.komut === "basla" && !ak) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
        const ctx = new AudioContext({ sampleRate: 16000 });
        const src = ctx.createMediaStreamSource(s), p = ctx.createScriptProcessor(4096, 1, 1), g = ctx.createGain(); g.gain.value = 0;
        p.onaudioprocess = ev => {
          const f = ev.inputBuffer.getChannelData(0), i16 = new Int16Array(f.length);
          for (let i = 0; i < f.length; i++) i16[i] = Math.max(-1, Math.min(1, f[i])) * 32767;
          // devretme (transfer) yok: devredilen tampon içerik betiğinin yalıtılmış bağlamına boş ulaşıyor (headless, 1 Ekim)
          window.postMessage({ __suflor: "micPcm", t: Date.now() - Math.round(f.length / 16), pcm: i16.buffer }, "*");
        };
        src.connect(p); p.connect(g); g.connect(ctx.destination);
        if (ctx.state === "suspended") await ctx.resume().catch(() => {});
        ak = { s, ctx, p }; yaz({ on: true, state: ctx.state });
      } catch (err) { yaz({ on: false, hata: String(err.name || err) }); }
    }
    if (e.data.komut === "dur" && ak) { ak.p.onaudioprocess = null; ak.s.getTracks().forEach(t => t.stop()); ak.ctx.close().catch(() => {}); ak = null; yaz({ on: false }); }
  });
})();
