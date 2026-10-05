// Suflor.me v0.9.0 — platform katmanı: Microsoft Teams (web) adaptörü.
// Çekirdek (content.js) platformdan bağımsızdır; sayfaya özgü her şeyi bu nesneden ister. Manifest bu dosyayı aynı
// içerik betiği bağlamında content.js'ten ÖNCE yükler. Yeni platform = aynı arayüzü veren yeni dosya (platform-meet.js…):
//   ad, etiket, yonerge{altyazi, dokum}, kur(yard)
//   toplantiAdi() · cagrida() · micDugme() · sessizMi()
//   dokumPaneli() · dokumOku(panel) → [{id, speaker, time, text}] | null (tanınmadı: çekirdek genel okuyucuyu dener)
//   dokumSatirSayisi(panel) · altyaziKutusu() · altyaziVar() (sıkı: gerçek altyazı metni görünüyor) · altyaziOku(box)
//   altyaziAdimlari: [[seçici, metin kalıbı]] — altyazıyı açan menü yolu (çekirdek güvenlik denetimiyle oynatır)
//   dilYollari(hedef "tr"|"en") → [[{sec, re, zaten?, kap?, icinde?, istege?}]] — altyazı konuşma dilini ayarlayan yollar (v0.13.10)
//   SKIP_RE: dökümde satır sayılmayacak sistem metinleri
// Seçiciler Eylül–Ekim 2026 Teams DOM'u (teams.cloud.microsoft, Türkçe arayüz); ayrıntı BRIEF-devir.md §3.
(() => {
  if (globalThis.SuflorPlatform) return;
  const TIME_RE = /^\d{1,2}:\d{2}(:\d{2})?$/;
  const SKIP_RE = /^(Transkript|Transcript|Yapay zeka tarafından oluşturulmuş içerik yanlış olabilir|AI-generated content may be incorrect|.*dökümü (başlattı|durdurdu)|.*started transcription|.*stopped transcription|Döküm başladı|Döküm başlatılıyor\.{0,3}|Transcription has started|Starting transcription\.{0,3})$/i;
  const CAPTION_SKIP_RE = /^(Türkçe|English|Deutsch|Français)?\s*\(?[A-Za-zÇĞİÖŞÜçğıöşü ]*\)?$|\((Türkiye|United States|United Kingdom)\)|^Altyazı|^Captions?$|^Canlı altyazı|^Konuşma dili|^Spoken language/i;
  const CC_SIKI = '[data-tid="closed-captions-renderer"], [data-tid="closed-caption-v2-window-wrapper"], [data-tid="closed-caption-text"]';
  let Y = null;  // çekirdeğin yardımcıları: leaves(root), capId(el, text)
  const whoById = new Map(); // satır kimliği → {speaker, time}; sanal listeden düşen satırların konuşmacısını hatırlar

  function toplantiAdi() {
    const t = document.title.replace(/^\(\d+\)\s*/, "");
    const parts = t.split("|").map(s => s.trim()).filter(Boolean);
    return parts.length >= 2 ? parts[parts.length - 2] : parts[0] || "Toplantı";
  }
  // v0.7.0: toplantıda mı (çağrı denetimleri görünüyor). Seçiciler gerçek Teams'te kısmen doğrulandı (ayrıl düğmesi).
  function cagrida() { return !!document.querySelector('[data-tid="hangup-main-btn"], [data-tid="call-hangup"], #hangup-button, button[aria-label^="Ayrıl"], button[aria-label^="Leave"], [data-tid="call-control-bar"]'); }
  function micDugme() { return document.querySelector('[data-tid="microphone-button"], #microphone-button, [data-tid="toggle-mute"], button[aria-label*="Sesi aç"], button[aria-label*="Sesi kapat"], button[aria-label*="Unmute"], button[aria-label*="Mute"]'); }
  function sessizMi() {
    const b = micDugme(); if (!b) return false;
    const l = (b.getAttribute("aria-label") || b.title || "").toLowerCase();
    return /sesi aç|sesini aç|unmute|mikrofonu aç|turn (on|the) mic/.test(l);
  }
  function dokumPaneli() {
    const vp = document.querySelector('[data-tid="call-transcript-panel-viewport"], [data-tid="call-transcript-panel"]');
    if (vp) return vp;
    const byTid = document.querySelector('[data-tid*="transcript" i], [data-testid*="transcript" i], [aria-label*="Transkript" i], [aria-label*="Transcript" i]');
    if (byTid && byTid.innerText && byTid.innerText.length > 20) return byTid;
    // Başlık metninden geriye doğru: "Transkript" yazan küçük düğüm → kaydırılabilir üst kapsayıcı
    const cands = [...document.querySelectorAll("h1,h2,h3,span,div")].filter(e => e.childElementCount === 0 && /^(Transkript|Transcript)$/i.test((e.textContent || "").trim()));
    for (const c of cands) { let p = c.parentElement, i = 0; while (p && i < 8) { if (p.scrollHeight > p.clientHeight + 40 && p.innerText.length > 40) return p; p = p.parentElement; i++; } }
    return null;
  }
  function dokumSatirSayisi(panel) { return panel.querySelectorAll('[data-tid="transcript-message-wrapper"]').length; }
  // Teams web (Eylül 2026 DOM): satır = [data-tid="transcript-message-wrapper"], içinde
  // transcript-chat-message-<id> (benzersiz kimlik), transcript-item-author (konuşmacı), call-transcript-panel-message (metin)
  function dokumOku(panel) {
    const isTeams = /call-transcript-panel/.test(panel.getAttribute("data-tid") || "");
    const ws = panel.querySelectorAll('[data-tid="transcript-message-wrapper"]');
    if (!ws.length) return isTeams ? [] : null;
    const entries = []; let lastSpeaker = "", lastTime = "";
    // Sanal liste, bir kişi uzun konuşunca adın yazılı olduğu ilk satırı DOM'dan atar; bu turda önceki satır yoksa
    // önceki turlarda görülen, kimlik numarası daha küçük en yakın satırdan devral (v0.3.2 — gerçek testte 143
    // satırın 120'si "?" çıkmıştı)
    // Yalnız aynı döküm önekinden (<uuid>/) devral (v0.4.1): Teams sekmesi iki toplantı arasında açık kalınca eski
    // toplantının satırları whoById'de duruyordu; 29 Eylül 21:31 testinde 171 satırın 147'si önceki toplantının
    // saatini (20:53) aldı. İki toplantının başlığı aynı olabildiği için başlığa bakmak yetmez.
    const idNum = id => { const m = /\/(\d+)$/.exec(id); return m ? +m[1] : NaN; };
    const idPre = id => id.slice(0, id.lastIndexOf("/") + 1);
    const recall = id => {
      const n = idNum(id), p = idPre(id); if (isNaN(n) || !p) return null; let best = null, bn = -1;
      whoById.forEach((v, k) => { if (!k.startsWith(p)) return; const kn = idNum(k); if (kn < n && kn > bn) { bn = kn; best = v; } });
      return best;
    };
    ws.forEach(w => {
      const msg = w.querySelector('[data-tid="call-transcript-panel-message"]');
      const text = msg ? (msg.innerText || "").trim() : "";
      if (!text || SKIP_RE.test(text)) return;
      const idEl = w.querySelector('[data-tid^="transcript-chat-message"]');
      const id = idEl ? idEl.getAttribute("data-tid").replace("transcript-chat-message-", "") : "";
      const a = w.querySelector('[data-tid="transcript-item-author"]');
      const speaker = a ? (a.innerText || a.textContent || "").trim() : "";
      const timeEl = [...w.querySelectorAll("span,div")].find(e => e.childElementCount === 0 && TIME_RE.test((e.textContent || "").trim()));
      const time = timeEl ? timeEl.textContent.trim() : "";
      // Teams aynı konuşmacının ardışık cümlelerinde adı ve saati yalnız ilk satırda gösterir: öncekinden devral
      if (!speaker && !lastSpeaker && id) { const r = recall(id); if (r) { lastSpeaker = r.speaker; if (!time && !lastTime) lastTime = r.time; } }
      if (speaker) { lastSpeaker = speaker; lastTime = time || ""; } else if (time) lastTime = time;
      const who = { speaker: speaker || lastSpeaker || "?", time: time || lastTime };
      if (id && who.speaker !== "?") { whoById.set(id, who); if (whoById.size > 400) whoById.delete(whoById.keys().next().value); }
      entries.push({ id, speaker: who.speaker, time: who.time, text });
    });
    return entries;
  }
  function altyaziKutusu() {
    // v0.4.8: önce altyazı metninin kendisi — eski seçici "caption" geçen ilk düğümü (ör. bir menü düğmesini) alabiliyordu
    const r = document.querySelector('[data-tid="closed-captions-renderer"], [data-tid="closed-caption-v2-window-wrapper"]');
    if (r) return r;
    if (document.querySelector('[data-tid="closed-caption-text"]')) return document.body;
    return document.querySelector('[data-tid*="caption" i], [data-testid*="caption" i], [aria-label*="altyazı" i], [aria-label*="caption" i]');
  }
  // altyazı ayar menüsü de aria-label'ında "altyazı" taşıyabilir (altyaziKutusu yedek seçicisi onu da yakalar) → burada yalnız metin
  function altyaziVar() { return !!document.querySelector(CC_SIKI); }
  function capAuthor(el) {  // metnin kendi satırındaki konuşmacı: tek altyazı metni içeren en yakın üst düğümdeki [data-tid="author"]
    let p = el.parentElement;
    for (let i = 0; p && i < 6; i++, p = p.parentElement) {
      if (p.querySelectorAll('[data-tid="closed-caption-text"]').length > 1) return "";
      const a = p.querySelector('[data-tid="author"]'); if (a) return (a.innerText || a.textContent || "").trim();
    }
    return "";
  }
  function altyaziOku(box) {
    // Teams canlı altyazı: [data-tid="closed-caption-text"] + aynı satırda [data-tid="author"]. Eskiden closest()
    // metnin kendisini buluyordu → konuşmacı hep "?" (30 Eylül: 3.242 satırın hepsi)
    const cc = box.querySelectorAll('[data-tid="closed-caption-text"]');
    const out = []; let speaker = "";
    if (cc.length) {
      cc.forEach(el => { const t = (el.innerText || el.textContent || "").trim(); if (!t || SKIP_RE.test(t)) return; speaker = capAuthor(el) || speaker; out.push({ id: Y.capId(el, t), speaker: speaker || "?", time: "", text: t }); });
    } else {
      // Yedek: "Konuşmacı" ayrı kısa düğüm, ardından metin
      const L = Y.leaves(box).filter(x => !SKIP_RE.test(x.t) && !CAPTION_SKIP_RE.test(x.t) && x.t.length > 3);
      for (let i = 0; i < L.length; i++) { const t = L[i].t; if (t.length < 40 && L[i + 1] && !/[.!?]$/.test(t)) { speaker = t; continue; } out.push({ id: Y.capId(L[i].el, t), speaker: speaker || "?", time: "", text: t }); }
    }
    if (out.length) out[out.length - 1].last = true;
    return out;
  }
  globalThis.SuflorPlatform = {
    ad: "teams", etiket: "Teams",
    // v0.12.2: kullanıcıya gösterilen yönerge arayüz diline göre (çekirdek P.dil'i "tr"/"en" yapar). Yalnız gösterilen metin;
    // Teams menüsünü bulan kalıplar (altyaziAdimlari, seçiciler) Teams'in kendi diline bağlıdır, burada çevrilmez.
    dil: "tr",
    YONERGE: {
      tr: { altyazi: "Diğer (…) → Dil ve konuşma → Canlı altyazıyı aç", dokum: "Diğer → Kaydet ve transkript → Transkripti göster" },
      en: { altyazi: "More (…) → Language and speech → Turn on live captions", dokum: "More → Record and transcribe → Show transcript" } },
    get yonerge() { return this.YONERGE[this.dil] || this.YONERGE.tr; },
    kur(yard) { Y = yard; },
    SKIP_RE, toplantiAdi, cagrida, micDugme, sessizMi, dokumPaneli, dokumSatirSayisi, dokumOku, altyaziKutusu, altyaziVar, altyaziOku,
    altyaziAdimlari: [  // metinle bulma: [seçici, metin/aria kalıbı]
      ['#callingButtons-showMoreBtn, [data-tid="more-button"], [data-tid="callingButtons-showMoreBtn"], button', /^(diğer|daha fazla|tümü|more)(\b|$)|^…$/i],  // 1 Ekim gerçek Teams (kanıt): çağrı çubuğunda "Tümü"
      ['[role="menuitem"], [role="menuitemcheckbox"], button', /^(dil ve konuşma|language and speech)/i],
      ['[role="menuitem"], [role="menuitemcheckbox"], button', /^(canlı altyazıları? aç|canlı altyazıyı aç|turn on live captions|show live captions)/i]],
    dilYollari,
  };
  // v0.13.10: altyazının konuşma dilini gündem diline ayarlama (5 Ekim kişisel deneme: Teams varsayılanı İngilizce (ABD) açıldı).
  // Microsoft'un anlattığı yol: altyazı çubuğundaki Altyazı ayarları (dişli) → Dil ayarları → Toplantı konuşma dili → Güncelle;
  // yedek yol Diğer → Dil ve konuşma → Dil ayarları. Gerçek Teams DOM'unda DOĞRULANMADI — adım bulunamazsa çekirdek menüde
  // görünen öğeleri capAuto'ya yazar. Adım: {sec, re, zaten (seçili değer buna uyuyorsa dur), istege (yoksa atla)}.
  // Konuşma dili toplantıdaki herkes için değişir (Teams kuralı); yalnız gündemde dil açıkça yazılıysa çağrılır.
  function dilYollari(hedef) {
    const R = { tr: /^(türkçe|turkish)\b/i, en: /^([iİ]ngilizce|english)\s*\((abd|amerika birleşik devletleri|united states|us)\)/i }[hedef];
    if (!R) return [];
    const MENU = '[role="menuitem"], [role="menuitemradio"], [role="menuitemcheckbox"], button';
    const sonu = [
      { sec: MENU, re: /^(dil ayarları|language settings)/i },
      { sec: '[role="combobox"], button[aria-haspopup="listbox"]', re: /konuşma dili|spoken language/i, zaten: R, kap: true },
      { sec: '[role="option"], [role="menuitemradio"]', re: R },
      // "Güncelle" yalnız dil panelinin içinde aranır (Teams'in uygulama güncelleme düğmesi sayfayı yeniler)
      { sec: 'button', re: /^(güncelle|update|onayla|confirm|kaydet|save)$/i, icinde: true },
      { sec: '[role="dialog"] button, [role="alertdialog"] button', re: /^(güncelle|update|onayla|confirm|evet|yes)$/i, istege: true }];  // "herkes için değişsin mi?" onayı
    return [
      [{ sec: 'button, [role="button"]', re: /^(altyazı ayarları|altyazı seçenekleri|captions? settings|captions? options)/i }, ...sonu],
      [{ sec: '#callingButtons-showMoreBtn, [data-tid="more-button"], [data-tid="callingButtons-showMoreBtn"], button', re: /^(diğer|daha fazla|tümü|more)(\b|$)|^…$/i },
       { sec: MENU, re: /^(dil ve konuşma|language and speech)/i }, ...sonu]];
  }
})();
