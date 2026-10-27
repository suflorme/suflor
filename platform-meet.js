// Suflor.me v0.27.0 (seçiciler 21 Ekim'de gerçek Meet'te düzeltildi) — platform katmanı: Google Meet (web) adaptörü. Arayüz platform-teams.js başında.
// Meet'te canlı döküm paneli yok (döküm toplantı sonunda Drive'a gider): kaynak altyazı (CC) ve yerel Whisper. Seçiciler herkese açık
// bilgiyle yazıldı; altyazı kutusu ve blokları 21 Ekim'de gerçek Meet'te (İngilizce arayüz) doğrulandı: sınıf adları sık değişir, bu yüzden önce aria etiketleri ve yapı; tanınmazsa
// çekirdeğin genel okuyucusu (yaprak düğümler). İlk gerçek kullanımda capAuto/günlükteki "altyazı yok" ve satır adlarına bak.
(() => {
  if (globalThis.SuflorPlatform) return;
  const SKIP_RE = /^(Altyazılar?|Captions?|Altyazıları (aç|kapat)|Turn (on|off) captions|Dil|Language|Türkçe|English.*|Ayarlar|Settings|Kapat|Close|Siz|You)$/i;
  // Öncelik sırasıyla (21 Ekim, gerçek Meet): .a4cQT altyazı ayarlarını (dil listesi, yazı boyutu) da içerir — tek seçici listesi belge sırasında onu bulup dil
  // listesini satır diye gönderiyordu. Asıl kutu role=region aria-label="Captions"; içinde her konuşma bloğu .nMcdL (ad .NWpY1d, metin .ygicle).
  const CC = ['div[role="region"][aria-label*="altyazı" i]', 'div[role="region"][aria-label*="caption" i]', '[jsname="dsyhDe"]'];
  let Y = null;
  // Toplantı adresi meet.google.com/abc-defg-hij (bekleme odası dahil). Ana sayfa ve "Share your new meeting" (/getalink) toplantı değil:
  // 21 Ekim denemesinde bağlantı sayfasının nabzı toplantınınkini eziyordu (ad yanlış, "çağrıda değil"). Meet tek sayfa uygulaması —
  // ana sayfadan toplantıya adres değişerek geçer, bu yüzden her çağrıda bakılır.
  // 27 Ekim: Meet toplantıyı meet.google.com/meet/<kod> adresinde açmaya başladı — kod yolun herhangi bir yerinde aranır (eski /<kod> da çalışır).
  const KOD_RE = /(?:^|\/)([a-z]{3,4}-[a-z]{4}-[a-z]{3,4})(?:\/|$)/i;
  function toplantiSayfasi() { return KOD_RE.test(location.pathname); }
  function toplantiAdi() {
    const m = document.querySelector("[data-meeting-title]");
    if (m && m.getAttribute("data-meeting-title")) return m.getAttribute("data-meeting-title").trim();
    const t = document.title.replace(/^Meet\s*[-–—:]\s*/i, "").replace(/\s*[-–—]\s*Google Meet$/i, "").trim();
    return t && !/^(Google )?Meet$/i.test(t) ? t : ((location.pathname.match(KOD_RE) || [])[1] || "Meet");
  }
  const LEAVE = /^(görüşmeden ayrıl|aramadan ayrıl|ayrıl|leave call|leave)$/i;
  function cagrida() { return [...document.querySelectorAll('button[aria-label], [role="button"][aria-label]')].some(b => LEAVE.test((b.getAttribute("aria-label") || "").trim())); }
  function micDugme() {
    return document.querySelector('button[data-is-muted][aria-label*="mikrofon" i], button[data-is-muted][aria-label*="microphone" i], [role="button"][data-is-muted][aria-label*="microphone" i]')
      || [...document.querySelectorAll("button[aria-label]")].find(b => /mikrofonu (aç|kapat)|turn (on|off) microphone/i.test(b.getAttribute("aria-label") || ""));
  }
  function sessizMi() {
    const b = micDugme(); if (!b) return false;
    if (b.hasAttribute("data-is-muted")) return b.getAttribute("data-is-muted") === "true";
    return /mikrofonu aç|turn on microphone/i.test(b.getAttribute("aria-label") || "");
  }
  function dokumPaneli() { return null; }  // Meet'te canlı döküm paneli yok
  function dokumSatirSayisi() { return 0; }
  function dokumOku() { return null; }
  function altyaziKutusu() { for (const s of CC) { const b = document.querySelector(s); if (b) return b; } return null; }
  function altyaziVar() { const b = altyaziKutusu(); return !!(b && (b.innerText || "").trim().length > 1); }
  // Altyazı bloğu: konuşmacı adı (kısa düğüm, çoğu zaman resmin yanında) + metin (bir ya da birkaç span). Blok = kutunun doğrudan
  // çocuğu ya da onun tek çocuğu; adı sınıf adıyla (bilinen: .NWpY1d, .KcIKyf) ya da "ilk kısa yaprak" kuralıyla bulur.
  function bloklar(box) {
    const nm = box.querySelectorAll(".nMcdL"); if (nm.length) return [...nm].filter(b => (b.innerText || "").trim());
    let k = box; for (let i = 0; i < 3 && k.children.length === 1; i++) k = k.children[0];
    return [...k.children].filter(b => (b.innerText || "").trim());
  }
  function altyaziOku(box) {
    const out = [];
    for (const b of bloklar(box)) {
      const adEl = b.querySelector(".NWpY1d, .KcIKyf, [data-self-name], [data-participant-name]");
      const yap = Y.leaves(b).filter(x => !SKIP_RE.test(x.t));
      let ad = adEl ? (adEl.innerText || adEl.textContent || "").trim() : "";
      if (!ad && yap.length > 1 && yap[0].t.length < 40 && !/[.!?]$/.test(yap[0].t)) ad = yap[0].t;
      const metinEl = b.querySelector(".bh44bd, .ygicle, [jsname='tgaKEf']");
      const metin = metinEl ? (metinEl.innerText || "").trim() : yap.filter(x => x.t !== ad).map(x => x.t).join(" ").trim();
      if (!metin || SKIP_RE.test(metin)) continue;
      out.push({ id: Y.capId(metinEl || b, metin), speaker: ad || "?", time: "", text: metin });
    }
    if (out.length) out[out.length - 1].last = true;
    return out;
  }
  globalThis.SuflorPlatform = {
    ad: "meet", etiket: "Google Meet", dil: "tr",
    YONERGE: { tr: { altyazi: "Alttaki CC düğmesi (Altyazıları aç)", dokum: "Meet'te canlı döküm paneli yok — altyazıyı aç" },
               en: { altyazi: "CC button at the bottom (Turn on captions)", dokum: "Meet has no live transcript panel — turn on captions" } },
    get yonerge() { return this.YONERGE[this.dil] || this.YONERGE.tr; },
    kur(yard) { Y = yard; },
    SKIP_RE, toplantiSayfasi, toplantiAdi, cagrida, micDugme, sessizMi, dokumPaneli, dokumSatirSayisi, dokumOku, altyaziKutusu, altyaziVar, altyaziOku,
    altyaziAdimlari: [['button[aria-label], [role="button"][aria-label]', /^(altyazıları aç|turn on captions)/i]],
    dilYollari() { return []; },  // Meet'te altyazı dili altyazı ayarından; otomasyon kapalı (Faz 0)
  };
})();
