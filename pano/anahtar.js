// Suflor.me yerel anahtar (v0.14.0) — pano, mini pano ve hazırlık sayfası aktarıcıya her istekte X-Suflor-Anahtar başlığı
// gönderir. Anahtar bu sayfanın kendi deposunda (localStorage; köken 127.0.0.1:<port> — diğer port/macOS hesabı göremez).
// İlk kez eklentinin "Panoyu aç"ı ya da kurulum ?k=<anahtar> ile verir; adres çubuğundan hemen silinir. Aktarıcının kendi
// açtığı sekme tek kullanımlık ?t= ile gelir, anahtarı aktarıcı sayfaya gömer.
const SUFLOR_ANAHTAR = (() => {
  const gecerli = k => /^[0-9a-f]{32,64}$/.test(k || ""), gomulu = "__SAYFA_ANAHTAR__";
  let k = "";
  try {
    const u = new URL(location.href), q = u.searchParams.get("k");
    if (u.searchParams.has("k") || u.searchParams.has("t")) { u.searchParams.delete("k"); u.searchParams.delete("t"); history.replaceState(null, "", u.pathname + u.search + u.hash); }
    k = gecerli(q) ? q : gecerli(gomulu) ? gomulu : "";
    if (k) localStorage.setItem("suflorAnahtar", k); else k = localStorage.getItem("suflorAnahtar") || "";
  } catch (e) { /* depo kapalı (gizli pencere): yalnız bu açılış */ }
  return k;
})();
(() => {
  const f0 = window.fetch.bind(window);
  window.fetch = (u, o) => {
    if (typeof u === "string" && u.startsWith("/")) { o = Object.assign({}, o); const h = new Headers(o.headers || {}); h.set("X-Suflor-Anahtar", SUFLOR_ANAHTAR); o.headers = h; }
    return f0(u, o);
  };
})();
