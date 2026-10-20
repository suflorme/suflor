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
  globalThis.fetch = async (u, o) => {
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
  if (yerli && chrome.runtime.onMessage) chrome.runtime.onMessage.addListener((m, _s, cevap) => {
    if (!m || m.type !== "anahtar") return;
    al().then(cevap); return true;
  });
  globalThis.SuflorAnahtar = { al, hata: () => (yerli ? hata : chrome.tabs ? "nativeMessaging izni yok (eklentiyi yeniden yükle)" : "içerik betiği") };
})();
