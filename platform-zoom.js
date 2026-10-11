// Suflor.me v0.27.0 — platform katmanı: Zoom web istemcisi (app.zoom.us/wc/…) adaptörü. Arayüz platform-teams.js başında.
// Kaynaklar: tam döküm paneli ("View Full Transcript", konuşmacı + saat + metin) ve altyazı (Captions); ikisi de yoksa yerel Whisper.
// Seçiciler herkese açık bilgiyle yazıldı, GERÇEK ZOOM WEB'DE DOĞRULANMADI (11 Ekim): önce aria etiketleri ve lt-* sınıfları, tanınmazsa
// çekirdeğin genel okuyucusu. Zoom masaüstü uygulaması bu dosyanın konusu değil (ses yardımcısı karşı sesi yine alır).
(() => {
  if (globalThis.SuflorPlatform) return;
  const TIME_RE = /^\d{1,2}:\d{2}(:\d{2})?(\s?[AP]M)?$/i;
  const SKIP_RE = /^(Transkript|Transcript|Altyazı|Captions?|Live Transcript|Canlı Döküm|Save Transcript|Transkripti kaydet|Search|Ara)$/i;
  const PANEL = '.lt-full-transcript__list, [class*="full-transcript__list"], [aria-label*="transcript" i][role="list"], [aria-label*="transkript" i][role="list"]';
  const SATIR = '.lt-full-transcript__item, [class*="full-transcript__item"]';
  const CC = '.live-transcription-subtitle__box, #live-transcription-subtitle, [class*="live-transcription-subtitle"], [class*="lt-subtitle"]';
  let Y = null;
  function toplantiAdi() {
    const m = document.querySelector('.meeting-info-container__topic, [class*="meeting-info"] [class*="topic"], .meeting-title');
    if (m && (m.innerText || "").trim()) return m.innerText.trim();
    const t = document.title.replace(/\s*[-–|]\s*Zoom.*$/i, "").trim();
    return t && !/^zoom$/i.test(t) ? t : "Zoom";
  }
  function cagrida() {
    return !!document.querySelector('.footer__leave-btn, button[aria-label^="Leave" i], button[aria-label^="Ayrıl" i], button[aria-label^="End" i]');
  }
  function micDugme() {
    return document.querySelector('.join-audio-container__btn, button[aria-label*="microphone" i], button[aria-label*="mikrofon" i], button[aria-label^="mute" i], button[aria-label^="unmute" i], button[aria-label*="sesi" i]');
  }
  function sessizMi() {
    const b = micDugme(); if (!b) return false;
    return /^unmute|unmute my|sesi aç|sesini aç|mikrofonu aç/i.test((b.getAttribute("aria-label") || b.title || "").trim());
  }
  function dokumPaneli() { return document.querySelector(PANEL); }
  function dokumSatirSayisi(panel) { return panel.querySelectorAll(SATIR).length; }
  let sira = 0; const kimlik = new WeakMap();
  function dokumOku(panel) {
    const ws = panel.querySelectorAll(SATIR);
    if (!ws.length) return null;
    const out = []; let son = "?", saat = "";
    ws.forEach(w => {
      const a = w.querySelector('.lt-full-transcript__display-name, [class*="display-name"], [class*="__name"]');
      const z = w.querySelector('.lt-full-transcript__time, [class*="__time"]');
      const m = w.querySelector('.lt-full-transcript__message, [class*="__message"], [class*="__content"]');
      const text = m ? (m.innerText || "").trim() : "";
      if (!text || SKIP_RE.test(text)) return;
      if (a && (a.innerText || "").trim()) son = a.innerText.trim();
      if (z && TIME_RE.test((z.innerText || "").trim())) saat = z.innerText.trim();
      if (!kimlik.has(w)) kimlik.set(w, `zoom/${++sira}`);  // Zoom satırında kimlik yok: düğüme yapay kimlik (satır yeniden çizilirse yeni satır)
      out.push({ id: kimlik.get(w), speaker: son, time: saat, text });
    });
    return out;
  }
  function altyaziKutusu() { return document.querySelector(CC); }
  function altyaziVar() { const b = altyaziKutusu(); return !!(b && (b.innerText || "").trim().length > 1); }
  function altyaziOku(box) {
    // Zoom altyazısı tek konuşmacının son cümlesi; ad ayrı düğümde (varsa)
    const adEl = box.querySelector('[class*="display-name"], [class*="speaker"], [class*="__name"]');
    const ad = adEl ? (adEl.innerText || "").trim() : "";
    const metinEl = box.querySelector('[class*="subtitle__item"], [class*="__text"], [class*="__content"]') || box;
    const metin = (metinEl.innerText || "").replace(ad, "").trim();
    if (!metin || SKIP_RE.test(metin)) return [];
    return [{ id: Y.capId(metinEl, metin), speaker: ad || "?", time: "", text: metin, last: true }];
  }
  globalThis.SuflorPlatform = {
    ad: "zoom", etiket: "Zoom", dil: "tr",
    YONERGE: { tr: { altyazi: "Alttaki Altyazılar (CC) düğmesi → Altyazıyı göster", dokum: "Altyazılar (CC) → Tam dökümü göster" },
               en: { altyazi: "Captions (CC) at the bottom → Show captions", dokum: "Captions (CC) → View full transcript" } },
    get yonerge() { return this.YONERGE[this.dil] || this.YONERGE.tr; },
    kur(yard) { Y = yard; },
    SKIP_RE, toplantiAdi, cagrida, micDugme, sessizMi, dokumPaneli, dokumSatirSayisi, dokumOku, altyaziKutusu, altyaziVar, altyaziOku,
    altyaziAdimlari: [['button[aria-label], [role="button"][aria-label]', /^(captions|altyazı|show captions|altyazıyı göster|cc)/i],
                      ['[role="menuitem"], [role="menuitemcheckbox"], li, button', /^(show captions?|altyazıyı göster|altyazıları göster)/i]],
    dilYollari() { return []; },
  };
})();
