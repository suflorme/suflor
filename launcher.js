// Suflor.me — Teams davet ara sayfası (dl/launcher) yardımcısı (v0.3.4)
// Mac'te bu sayfa masaüstü Teams'i gizli bir iframe'le (msteams: bağlantısı) açmaya çalışır; eklenti ise yalnız
// Chrome'daki Teams web'i okuyabilir. Teams'in kendi desteklediği "webjoin=true" değeri toplantı adresine eklenince
// sayfa uygulamayı hiç denemeden web'e katılır (launcher.js kaynağında joinInfo.forceWebJoin, gerekçe "UrlParameter").
// Sayfa yüklenmeye başlarken (document_start) çalışır; değer zaten varsa ya da eklenti kapalıysa dokunmaz.
(() => {
  const p = new URLSearchParams(location.search);
  const inner = p.get("url") || "";
  if (!/meetup-join/.test(inner) && p.get("type") !== "meetup-join") return;
  chrome.storage.sync.get({ enabled: true, webJoin: true }, cfg => {
    if (!cfg.enabled || !cfg.webJoin) return;
    if (!/[?&]webjoin=true/i.test(inner)) {
      p.set("url", inner + (inner.includes("?") ? "&" : "?") + "webjoin=true");
      location.replace(location.pathname + "?" + p.toString() + location.hash);
      return;
    }
    // Yedek: sayfa yine de seçim ekranını gösterirse "Bu tarayıcıda devam et"e bas
    let n = 0;
    const t = setInterval(() => {
      const b = document.querySelector('[data-tid="joinOnWeb"]');
      if (b) { clearInterval(t); b.click(); }
      else if (++n > 40) clearInterval(t);
    }, 250);
  });
})();
