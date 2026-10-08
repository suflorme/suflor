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
  const portu = u => { const m = /^http:\/\/(?:127\.0\.0\.1|localhost):(\d{4,5})\//.exec(String(u)); return m ? +m[1] : 0; };
  const f0 = globalThis.fetch.bind(globalThis);
  globalThis.fetch = async (u, o) => {
    const p = typeof u === "string" ? portu(u) : 0;
    if (!p) return f0(u, o);
    const k = await al();
    if (!k || k.port !== p) return f0(u, o);
    const ekle = a => { const x = Object.assign({}, o), h = new Headers((o && o.headers) || {}); h.set("X-Suflor-Anahtar", a); x.headers = h; return x; };
    const r = await f0(u, ekle(k.anahtar));
    if (r.status !== 401) return r;
    const k2 = await al(true);  // anahtar değişmiş (aktarıcı yeniden kuruldu): bir kez yeniden dene
    return k2 && k2.port === p && k2.anahtar !== k.anahtar ? f0(u, ekle(k2.anahtar)) : r;
  };
  if (yerli && chrome.runtime.onMessage) chrome.runtime.onMessage.addListener((m, _s, cevap) => {
    if (!m || m.type !== "anahtar") return;
    al().then(cevap); return true;
  });
  globalThis.SuflorAnahtar = { al, hata: () => (yerli ? hata : chrome.tabs ? "nativeMessaging izni yok (eklentiyi yeniden yükle)" : "içerik betiği") };
})();
