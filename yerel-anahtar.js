// Suflor.me yerel anahtar (v0.14.0, #76) — eklentinin her bağlamında (arka plan, offscreen, popup, içerik betiği) aktarıcıya giden
// isteklere X-Suflor-Anahtar başlığı ekler. Anahtarı Chrome yerel mesajlaşmasıyla (native messaging) bu macOS kullanıcısının
// anahtar yardımcısından alır (aktarıcı kurar: me.suflor.anahtar); içerik betiği yerel mesajlaşmayı kullanamaz, arka plandan ister.
// Yardımcı aktarıcının portunu da verir: başlık yalnız o porta gider — aynı Mac'teki diğer hesabın aktarıcısına (8766 …) anahtar
// gitmez. Yardımcı yoksa (eski aktarıcı) istekler anahtarsız gider; aktarıcı geçiş döneminde yazma isteklerini yine kabul eder.
(() => {
  if (globalThis.SuflorAnahtar) return;
  const AD = "me.suflor.anahtar", SURE = 10 * 60 * 1000;
  let bel = null, zaman = 0, bekleyen = null, hata = "";
  const yerli = !!(chrome.runtime && chrome.runtime.sendNativeMessage);  // içerik betiğinde yok
  async function iste() {
    if (yerli) {
      try {
        const r = await chrome.runtime.sendNativeMessage(AD, { iste: "anahtar" });
        hata = r && r.anahtar ? "" : "yardımcı anahtar vermedi";
        return r && /^[0-9a-f]{32,64}$/.test(r.anahtar || "") && +r.port >= 1024 ? { port: +r.port, anahtar: r.anahtar, alan: r.alan || "" } : null;
      } catch (e) { hata = String(e && e.message || e).slice(0, 160); return null; }  // yardımcı yok / bu eklenti kimliğine izin yok
    }
    try { return (await chrome.runtime.sendMessage({ type: "anahtar" })) || null; } catch (e) { return null; }
  }
  function al(yenile) {
    if (!yenile && Date.now() - zaman < SURE) return Promise.resolve(bel);
    if (!bekleyen) bekleyen = iste().then(k => { bel = k; zaman = Date.now(); bekleyen = null; return k; });
    return bekleyen;
  }
  // v0.99.0 (güvenlik denetimi O1): anahtar ve veri gitmeden önce karşıdaki aktarıcı bu hesabınki mi — /kimlik?n=<nonce> → HMAC(anahtar, "suflor-kimlik|n|port").
  // Doğrulama DOGRU_SURE geçerli; ağ hatasından sonra (aktarıcı yeniden başlıyor: port el değiştirebilir) yeniden sorulur. Doğrulanamazsa istek gönderilmez.
  const DOGRU_SURE = 30 * 1000, TE = new TextEncoder();
  let dog = { port: 0, anahtar: "", t: 0, p: null };
  const hex = b => Array.from(new Uint8Array(b), x => x.toString(16).padStart(2, "0")).join("");
  async function imza(anahtar, metin) {
    const k = await crypto.subtle.importKey("raw", TE.encode(anahtar), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    return hex(await crypto.subtle.sign("HMAC", k, TE.encode(metin)));
  }
  function dogrula(p, anahtar) {
    if (dog.port === p && dog.anahtar === anahtar) { if (Date.now() - dog.t < DOGRU_SURE) return Promise.resolve(true); if (dog.p) return dog.p; }
    const d = dog = { port: p, anahtar, t: 0, p: null };
    d.p = (async () => {
      const n = hex(crypto.getRandomValues(new Uint8Array(16)));
      try {
        const j = await (await f0(`http://127.0.0.1:${p}/kimlik?n=${n}`, { cache: "no-store" })).json();
        const ok = !!j && typeof j.h === "string" && j.h === await imza(anahtar, `suflor-kimlik|${n}|${p}`);
        if (ok) d.t = Date.now(); else hata = "aktarıcı doğrulanamadı (port başka bir süreçte olabilir)";
        return ok;
      } catch (e) { return false; } finally { d.p = null; }
    })();
    return d.p;
  }
  const portu = u => { const m = /^http:\/\/(?:127\.0\.0\.1|localhost):(\d{4,5})\//.exec(String(u)); return m ? +m[1] : 0; };
  const f0 = globalThis.fetch.bind(globalThis);
  const anahtarli = async (u, o) => {
    const p = typeof u === "string" ? portu(u) : 0;
    if (!p) return f0(u, o);
    let k = await al();
    if (!k || k.port !== p) return f0(u, o);
    if (!(await dogrula(p, k.anahtar))) {  // anahtar değişmiş olabilir (aktarıcı yeniden kuruldu): bir kez taze anahtarla
      const k2 = await al(true);
      if (!k2 || k2.port !== p || !(await dogrula(p, k2.anahtar))) throw new TypeError("Suflor: aktarıcı doğrulanamadı");
      k = k2;
    }
    const ekle = a => { const x = Object.assign({}, o), h = new Headers((o && o.headers) || {}); h.set("X-Suflor-Anahtar", a); x.headers = h; return x; };
    let r;
    try { r = await f0(u, ekle(k.anahtar)); } catch (e) { dog.t = 0; throw e; }
    if (r.status !== 401) return r;
    const k2 = await al(true);  // anahtar değişmiş (aktarıcı yeniden kuruldu): bir kez yeniden dene
    return k2 && k2.port === p && k2.anahtar !== k.anahtar && await dogrula(p, k2.anahtar) ? f0(u, ekle(k2.anahtar)) : r;
  };
  // v0.142.0: Chrome 142'den beri herkese açık siteden (https://meet.google.com …) 127.0.0.1'e istek "yerel ağ erişimi" izni ister; izin yoksa
  // gönderilmez (27 Ekim, ikinci hesapta Meet: içerik betiğinden hiç nabız gelmedi, arka planın istekleri geçti). İçerik betiği aktarıcı
  // isteğini arka plana iletir (eklenti kökeni bu izne takılmaz); arka plana ulaşılamazsa eskisi gibi doğrudan gider.
  const icerik = typeof location !== "undefined" && !/^chrome-extension:$/.test(location.protocol);
  const b64e = b => { const u8 = new Uint8Array(b); let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  const b64d = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  async function vekil(u, o) {
    if (!portu(u)) return f0(u, o);
    const sig = o && o.signal; if (sig && sig.aborted) throw new DOMException("aborted", "AbortError");
    const h = {}; new Headers((o && o.headers) || {}).forEach((v, k) => { h[k] = v; });
    const istek = { type: "aktarici-istek", url: u, method: (o && o.method) || "GET", headers: h, body: o && typeof o.body === "string" ? o.body : null };
    let c;
    try {
      c = await new Promise((coz, red) => {
        if (sig) sig.addEventListener("abort", () => red(new DOMException("aborted", "AbortError")), { once: true });
        chrome.runtime.sendMessage(istek).then(coz, red);
      });
    } catch (e) { if (e && e.name === "AbortError") throw e; c = null; }
    if (!c || c.vekil !== 1) return anahtarli(u, o);  // arka plan yok ya da eski: doğrudan
    if (c.hata) throw new TypeError(c.hata);
    return new Response(c.b64 != null ? b64d(c.b64) : c.metin, { status: c.status, headers: c.ct ? { "Content-Type": c.ct } : {} });
  }
  globalThis.fetch = icerik && !yerli ? vekil : anahtarli;
  if (yerli && chrome.runtime.onMessage) chrome.runtime.onMessage.addListener((m, _s, cevap) => {
    if (!m || m.type !== "anahtar") return;
    al().then(cevap); return true;
  });
  const arkaPlan = typeof ServiceWorkerGlobalScope !== "undefined" && globalThis instanceof ServiceWorkerGlobalScope;
  if (arkaPlan && chrome.runtime.onMessage) chrome.runtime.onMessage.addListener((m, s, cevap) => {  // yalnız arka plan (popup cevap vermez: istek iki kez gitmesin)
    if (!m || m.type !== "aktarici-istek" || !s || s.id !== chrome.runtime.id || !portu(m.url)) return;
    (async () => {
      try {
        const r = await anahtarli(m.url, { method: m.method, headers: m.headers, body: m.body, signal: AbortSignal.timeout(40000) });
        const ct = r.headers.get("Content-Type") || "";
        return /json|text|javascript/i.test(ct) || !ct ? { vekil: 1, status: r.status, ct, metin: await r.text() } : { vekil: 1, status: r.status, ct, b64: b64e(await r.arrayBuffer()) };
      } catch (e) { return { vekil: 1, hata: String(e && e.message || e).slice(0, 200) }; }
    })().then(cevap);
    return true;
  });
  globalThis.SuflorAnahtar = { al, hata: () => (yerli ? hata : chrome.tabs ? "nativeMessaging izni yok (eklentiyi yeniden yükle)" : "içerik betiği") };
})();
