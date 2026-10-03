// Suflor.me kurulum sihirbazı — ön yüz. Yerel sunucu (kurulum.py, 127.0.0.1) /api/* uçlarıyla konuşur; dosya olarak
// açılırsa (file:) ya da ?onizleme ile örnek verilerle çalışır. Durum sunucuda (kurulum.json) tutulur: sekme kapanırsa
// kaldığı adımdan sürer. Metinler iki dilde (tr/en); her adım: simge, başlık, açıklama, içerik, "devam edebilir mi".
(() => {
  const ONIZLEME = location.protocol === "file:" || new URLSearchParams(location.search).has("onizleme");
  const $ = (s, k = document) => k.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  // ---------- metinler ----------
  const M = {
    tr: {
      geri: "Geri", devam: "Devam", basla: "Başla", bitir: "Suflor.me'yi aç", atla: "Şimdilik geç",
      hosgeldin_b: "Toplantıda kulağına fısıldayan asistan",
      hosgeldin_a: "Suflor.me toplantını Mac'inde yazıya döker. Claude da konuşmayı izleyip sana ne sorman, neyi belirtmen gerektiğini küçük kartlarla söyler.",
      hg1: "Ses Mac'inden çıkmaz", hg1a: "Konuşma tanıma bu Mac'te çalışır, ses diske yazılmaz.",
      hg2: "Projeni bilir", hg2a: "Belgelerin ve geçmiş toplantıların kartlara kaynak olur.",
      hg3: "Yaklaşık 15 dakika", hg3a: "Her adım kendini denetler; istersen ara verip kaldığın yerden sürersin.",
      mac_b: "Mac'ini denetliyorum", mac_a: "Gerekenler tamamsa modelleri arka planda indirmeye başlıyorum; sen kuruluma devam edersin.",
      m_islemci: "Apple Silicon işlemci", m_macos: "macOS 14 ya da üstü", m_bellek: "Bellek", m_disk: "Boş disk", m_python: "Python", m_chrome: "Google Chrome",
      m_python_ac: "Komut satırı araçları gerekiyor", m_python_dug: "Yükle", m_chrome_ac: "Teams toplantıları Chrome'da açılır", m_chrome_dug: "İndir",
      m_bellek_az: "16 GB önerilir; daha azında toplantıda diğer uygulamaları kapatman gerekebilir",
      indiriliyor: "Modeller iniyor", indi: "Modeller hazır",
      claude_b: "Claude'u bağlayalım", claude_a: "Kartları ve özetleri Claude yazar. Bunun için bu Mac'te Claude Code ve bir Claude aboneliği gerekiyor.",
      c_kurulu: "Claude Code kurulu", c_yok: "Claude Code bulunamadı", c_giris: "Oturum açık", c_giris_yok: "Oturum açılmamış ya da denetlenmedi",
      c_kur: "Terminal'de kur ve giriş yap", c_denetle: "Yeniden denetle",
      c_aciklama: "Terminal açılır ve kurulum komutu hazır yazılı olur. Bitince açılan Claude'da hesabınla giriş yap, sonra buraya dön.",
      c_kartsiz: "Aboneliğim yok, kartsız devam et",
      c_kartsiz_a: "Kartsız kipte döküm, pano ve notlar çalışır; kart ve özet olmaz. Sonradan Claude bağlayabilirsin.",
      sen_b: "Seni tanıyalım", sen_a: "Kartlar senin bakışından yazılsın diye. Bu bilgiler yalnız bu Mac'te kalır.",
      ad: "Adın", ad_i: "Toplantılarda göründüğü gibi", rol: "Rolün ya da unvanın", sirket: "Şirketin (isteğe bağlı)", is_alani: "İş alanın",
      alanlar: ["E-ticaret", "Yazılım", "Danışmanlık", "Finans", "Sağlık", "Eğitim", "Üretim", "Kamu", "Diğer"],
      arac_b: "Neyle çalışıyorsun?", arac_a: "Konuşmada geçen sistem adlarını tanır ve doğru yazar.",
      araclar_e: "Sık kullandığın araçlar", araclar_ek: "Listede olmayanlar", araclar_ek_i: "Virgülle ayır: örneğin Logo Tiger, Netsis",
      kisiler: "Sık görüştüğün kişiler (isteğe bağlı)", kisiler_i: "Konuşma tanıma adları doğru yazsın diye. Virgülle ayır.",
      anlat_b: "Biraz anlatır mısın?", anlat_a: "Kısa cevaplar yeter. Claude bunlardan senin için bir çalışma notu hazırlar; onaylamadan hiçbir şey kaydedilmez.",
      s1: "Görevin ne, ekibin kim?", s2: "Toplantılarının çoğu ne tür? Yönettiğin mi, katıldığın mı, dinlediğin mi?",
      s3: "Toplantıda en çok neyi kaçırıyorsun ya da sonradan \"keşke sorsaydım\" diyorsun?",
      s4: "Hangi konuda uyarılmak istersin, hangisinde rahatsız edilmek istemezsin?",
      linkedin: "LinkedIn profilin (isteğe bağlı)",
      linkedin_a: "LinkedIn'de profilinde Daha fazla → PDF olarak kaydet, sonra dosyayı buraya bırak. Ya da profil metnini yapıştır.",
      linkedin_yapistir: "Profil metnini buraya yapıştırabilirsin",
      birak: "Dosyayı buraya bırak", birak_ya: "ya da tıklayıp seç",
      gor_b: "Geçmiş görüşmelerin var mı?", gor_a: "Teams'ten indirdiğin birkaç döküm, Suflor.me'nin seni en hızlı tanıdığı yol: kişi adlarını, terimleri ve senin toplantı tarzını öğrenir.",
      gor_birak: "Teams dökümlerini buraya bırak", gor_tur: ".docx · .vtt · .txt · .md",
      gor_ornek: "Dökümüm yok, örnek bir görüşmeyle dene", gor_not: "Dosyalar proje klasörüne kopyalanır; asılları yerinde kalır. Hiçbir yere gönderilmez.",
      proje_b: "Belgelerin nerede dursun?", proje_a: "Suflor.me toplantı özetlerini bu klasöre yazar; buraya koyduğun belgeler kartlara kaynak olur.",
      proje_sec: "Başka bir klasör seç…", proje_icerik: "İçinde belgeler, görüşmeler ve kanıtlar için alt klasörler açılır.",
      tanidim_b: "Seni böyle tanıdım", tanidim_a: "Claude anlattıklarından bir çalışma notu çıkardı. Düzeltebilirsin; toplantıda kartlar buna göre yazılır.",
      tanidim_bekle: "Claude notunu hazırlıyor…", tanidim_yok: "Claude bağlı değil; notu kendin yazabilir ya da sonra tamamlayabilirsin.",
      tanidim_not: "Çalışma notu", tanidim_terim: "Öğrendiğim adlar ve terimler",
      paylas_b: "Gelişmesine yardım et", paylas_a: "Suflor.me beta sürümünde. Bir şey aksarsa teknik bilgisi geliştiriciye gitsin mi? Toplantılarının içeriği hiçbir zaman bu Mac'ten çıkmaz.",
      p_gider: "Gider", p_gider_a: "Sürümler, Mac modeli, hata türü ve kodun neresinde olduğu, gecikmeler ve sayılar (kaç satır, kaç kart).",
      p_gitmez: "Asla gitmez", p_gitmez_a: "Döküm, kişi ve toplantı adları, kartlar, notlar, takvimin, belgelerin.",
      p_evet: "Paylaş", p_hayir: "Paylaşma", p_not: "Sonradan ayarlardan değiştirebilirsin. Panodaki Geri bildirim düğmesi her zaman çalışır.",
      kur_b: "Kuruyorum", kur_a: "Ayarlarını yazıyor, arka plan hizmetini ve takvim yardımcısını kuruyorum.",
      k_ayar: "Ayarlar", k_proje: "Proje klasörü", k_not: "Çalışma notu ve sözlük", k_aktarici: "Arka plan hizmeti", k_modeller: "Konuşma tanıma modelleri",
      takvim_b: "Takvimini bağlayalım", takvim_a: "Toplantından birkaç dakika önce hatırlatır, gündemi ve katılımcıları davetten alır.",
      t_izin: "Erişim ver", t_izin_b: "Takvim izni", t_izin_a: "macOS bir izin penceresi açacak: \"Tam erişim\"i seç.",
      t_hesap_yok: "Mac'in Takvim uygulamasında hesap görünmüyor.", t_hesap_ekle: "Google, iCloud ya da Outlook hesabını ekle",
      t_bugun: "Bugün gördüklerim", t_bos: "Bugün başka toplantın yok.", t_dogru: "Takvimlerin bunlar mı? İzlenmesini istemediklerinin işaretini kaldır.",
      teams_b: "Teams uygulaması kurulu", teams_a: "Suflor.me Teams'i Chrome'da izler. Davet bağlantısı uygulamada açılırsa çalışmaz.",
      tm1: "Toplantıya davetteki bağlantıdan katıl; Chrome \"Microsoft Teams açılsın mı?\" diye sorarsa \"Her zaman izin ver\"i işaretleme, Vazgeç de.",
      tm2: "Teams'in ara sayfasında \"Bu tarayıcıda devam et\"i seç. Suflor.me eklentisi bunu senin yerine de seçer.",
      tm3: "Panodaki \"Katıl\" düğmesi toplantıyı her zaman tarayıcıda açar.",
      tm_dene: "Deneme bağlantısını aç", tm_tamam: "Anladım",
      ek_b: "Chrome eklentisini ekle", ek_a: "Eklenti Teams sayfasından sesi ve altyazıyı alır, kartları ekranın köşesinde gösterir.",
      e1: "Chrome'un eklenti sayfasını aç ve sağ üstte Geliştirici modu'nu aç.", e1d: "Eklenti sayfasını aç",
      e2: "\"Paketlenmemiş öğe yükle\"ye bas ve Suflor.me klasörünü seç.", e2d: "Klasörü Finder'da göster",
      e3: "Araç çubuğundaki yapboz simgesinden Suflor.me'yi sabitle.",
      e_bekle: "Eklentiyi bekliyorum…", e_bagli: "Eklenti bağlandı",
      bitti_b: "Hazırsın", bitti_a: "Bir sonraki toplantından önce takvimdeki Başlat'a bas ya da Suflor.me simgesine tıkla.",
      b1: "Teams sekmesinde bir kez Option + Shift + W: karşı tarafın sesi de yazılır.",
      b2: "Option + Shift + K kanıt, Option + Shift + S önemli an, Option + Shift + O son bir dakikanın özeti.",
      b3: "Panoya ?, soru, Claude ya da iki boşlukla başlayan yazı Claude'a soru olur.",
    },
    en: {
      geri: "Back", devam: "Continue", basla: "Get started", bitir: "Open Suflor.me", atla: "Skip for now",
      hosgeldin_b: "The assistant that whispers in your ear",
      hosgeldin_a: "Suflor.me transcribes your meeting on your Mac. Claude follows the conversation and tells you, in small cards, what to ask and what to point out.",
      hg1: "Audio stays on your Mac", hg1a: "Speech recognition runs on this Mac; audio is never saved.",
      hg2: "It knows your project", hg2a: "Your documents and past meetings become sources for the cards.",
      hg3: "About 15 minutes", hg3a: "Every step checks itself; take a break and pick up where you left off.",
      mac_b: "Checking your Mac", mac_a: "If everything is in place I'll start downloading the models in the background while you continue.",
      m_islemci: "Apple silicon", m_macos: "macOS 14 or later", m_bellek: "Memory", m_disk: "Free disk space", m_python: "Python", m_chrome: "Google Chrome",
      m_python_ac: "Command line tools are needed", m_python_dug: "Install", m_chrome_ac: "Teams meetings open in Chrome", m_chrome_dug: "Download",
      m_bellek_az: "16 GB recommended; with less you may need to close other apps during meetings",
      indiriliyor: "Downloading models", indi: "Models ready",
      claude_b: "Connect Claude", claude_a: "Claude writes the cards and summaries. This needs Claude Code on this Mac and a Claude subscription.",
      c_kurulu: "Claude Code is installed", c_yok: "Claude Code not found", c_giris: "Signed in", c_giris_yok: "Not signed in or not checked yet",
      c_kur: "Install and sign in with Terminal", c_denetle: "Check again",
      c_aciklama: "Terminal opens with the install command ready. When it finishes, sign in to Claude, then come back here.",
      c_kartsiz: "No subscription, continue without cards",
      c_kartsiz_a: "Without cards you still get the transcript, the dashboard and notes; no cards or summaries. You can connect Claude later.",
      sen_b: "Tell us about you", sen_a: "So the cards are written from your point of view. This stays on this Mac.",
      ad: "Your name", ad_i: "As it appears in meetings", rol: "Your role or title", sirket: "Company (optional)", is_alani: "Your field",
      alanlar: ["E-commerce", "Software", "Consulting", "Finance", "Healthcare", "Education", "Manufacturing", "Public sector", "Other"],
      arac_b: "What do you work with?", arac_a: "So it recognises and spells the systems that come up in conversation.",
      araclar_e: "Tools you use often", araclar_ek: "Anything not listed", araclar_ek_i: "Separate with commas",
      kisiler: "People you meet often (optional)", kisiler_i: "So speech recognition spells their names right. Separate with commas.",
      anlat_b: "Tell us a little more", anlat_a: "Short answers are fine. Claude turns them into a working note for you; nothing is saved until you approve it.",
      s1: "What is your job, who is on your team?", s2: "What are most of your meetings like? Do you run them, take part, or listen?",
      s3: "What do you miss most in meetings, the questions you wish you had asked?",
      s4: "What should you be warned about, and what should never interrupt you?",
      linkedin: "Your LinkedIn profile (optional)",
      linkedin_a: "On your LinkedIn profile choose More → Save to PDF, then drop the file here. Or paste the profile text.",
      linkedin_yapistir: "You can paste your profile text here",
      birak: "Drop the file here", birak_ya: "or click to choose",
      gor_b: "Do you have past meetings?", gor_a: "A few transcripts downloaded from Teams are the fastest way for Suflor.me to learn names, terms and how you run meetings.",
      gor_birak: "Drop Teams transcripts here", gor_tur: ".docx · .vtt · .txt · .md",
      gor_ornek: "No transcripts, try a sample meeting", gor_not: "Files are copied into your project folder; originals stay where they are. Nothing is sent anywhere.",
      proje_b: "Where should your documents live?", proje_a: "Suflor.me writes meeting summaries here; documents you keep here become sources for the cards.",
      proje_sec: "Choose another folder…", proje_icerik: "Subfolders for documents, meetings and evidence are created inside.",
      tanidim_b: "Here's how I see you", tanidim_a: "Claude drafted a working note from your answers. Edit it freely; cards in meetings follow it.",
      tanidim_bekle: "Claude is drafting your note…", tanidim_yok: "Claude isn't connected; write the note yourself or finish it later.",
      tanidim_not: "Working note", tanidim_terim: "Names and terms I picked up",
      paylas_b: "Help make it better", paylas_a: "Suflor.me is in beta. If something breaks, may its technical details go to the developer? Your meeting content never leaves this Mac.",
      p_gider: "Sent", p_gider_a: "Versions, Mac model, error type and where in the code it happened, delays and counts (how many lines, how many cards).",
      p_gitmez: "Never sent", p_gitmez_a: "Transcripts, names of people and meetings, cards, notes, your calendar, your documents.",
      p_evet: "Share", p_hayir: "Don't share", p_not: "You can change this later in settings. The Feedback button on the panel always works.",
      kur_b: "Setting up", kur_a: "Writing your settings and installing the background service and calendar helper.",
      k_ayar: "Settings", k_proje: "Project folder", k_not: "Working note and glossary", k_aktarici: "Background service", k_modeller: "Speech recognition models",
      takvim_b: "Connect your calendar", takvim_a: "It reminds you a few minutes before a meeting and takes the agenda and attendees from the invitation.",
      t_izin: "Allow access", t_izin_b: "Calendar permission", t_izin_a: "macOS will ask for permission: choose \"Full Access\".",
      t_hesap_yok: "No accounts in the Mac Calendar app.", t_hesap_ekle: "Add your Google, iCloud or Outlook account",
      t_bugun: "What I see today", t_bos: "No more meetings today.", t_dogru: "Are these your calendars? Untick any you don't want followed.",
      teams_b: "The Teams app is installed", teams_a: "Suflor.me follows Teams in Chrome. If the invitation opens in the app, it can't help.",
      tm1: "Join from the link in the invitation; if Chrome asks to open Microsoft Teams, don't tick \"Always allow\" and choose Cancel.",
      tm2: "On Teams' landing page choose \"Continue on this browser\". The Suflor.me extension also picks it for you.",
      tm3: "The Join button on the dashboard always opens the meeting in the browser.",
      tm_dene: "Open a test link", tm_tamam: "Got it",
      ek_b: "Add the Chrome extension", ek_a: "The extension takes sound and captions from the Teams page and shows the cards in a corner of the screen.",
      e1: "Open Chrome's extensions page and switch on Developer mode at the top right.", e1d: "Open extensions page",
      e2: "Click \"Load unpacked\" and choose the Suflor.me folder.", e2d: "Show the folder in Finder",
      e3: "Pin Suflor.me from the puzzle icon in the toolbar.",
      e_bekle: "Waiting for the extension…", e_bagli: "Extension connected",
      bitti_b: "You're all set", bitti_a: "Before your next meeting press Start in the calendar list or click the Suflor.me icon.",
      b1: "Press Option + Shift + W once in the Teams tab so the other side is transcribed too.",
      b2: "Option + Shift + K evidence, Option + Shift + S key moment, Option + Shift + O summary of the last minute.",
      b3: "Text on the dashboard starting with ?, \"soru\", Claude or two spaces becomes a question for Claude.",
    },
  };
  const ARACLAR = ["Microsoft 365", "Google Workspace", "Slack", "Jira", "Confluence", "Notion", "Asana", "Trello", "Salesforce", "HubSpot",
    "SAP", "Zendesk", "GitHub", "Figma", "Power BI", "Excel", "AWS", "Azure"];

  // ---------- simgeler (çizgi, currentColor) ----------
  const S = {
    isaret: `<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="15" fill="var(--sahne)"/><g transform="translate(0 -3.3)"><path fill="var(--krem)" d="M23.50 37.60A7.60 7.60 0 1 1 31.10 30.38C31.48 39.50 26.16 45.58 18.56 48.24C23.65 44.44 25.17 40.79 23.50 37.60Z"/><path fill="var(--pirinc)" d="M42.50 37.60A7.60 7.60 0 1 1 50.10 30.38C50.48 39.50 45.16 45.58 37.56 48.24C42.65 44.44 44.17 40.79 42.50 37.60Z"/></g></svg>`,
    mac: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="12" y="14" width="40" height="27" rx="3"/><path d="M6 46h52l-3 4H9z"/><path d="M27 46h10" stroke-linecap="round"/></svg>`,
    claude: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M32 12v40M12 32h40M18 18l28 28M46 18 18 46"/><circle cx="32" cy="32" r="6" fill="var(--zemin)"/></svg>`,
    sen: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="32" cy="24" r="9"/><path d="M15 51c2.5-9 9-14 17-14s14.5 5 17 14" stroke-linecap="round"/></svg>`,
    arac: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="13" y="13" width="15" height="15" rx="4"/><rect x="36" y="13" width="15" height="15" rx="4"/><rect x="13" y="36" width="15" height="15" rx="4"/><circle cx="43.5" cy="43.5" r="7.5"/></svg>`,
    anlat: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 16h40a4 4 0 0 1 4 4v20a4 4 0 0 1-4 4H30l-10 8v-8h-8a4 4 0 0 1-4-4V20a4 4 0 0 1 4-4z"/><path d="M19 27h26M19 34h16" stroke-linecap="round"/></svg>`,
    gorusme: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M20 10h18l10 10v32a2 2 0 0 1-2 2H20a2 2 0 0 1-2-2V12a2 2 0 0 1 2-2z"/><path d="M38 10v10h10M24 30h16M24 37h16M24 44h10" stroke-linecap="round"/></svg>`,
    klasor: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M8 20a4 4 0 0 1 4-4h13l5 5h22a4 4 0 0 1 4 4v23a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4z"/><path d="M8 28h48"/></svg>`,
    tanidim: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="14" y="10" width="36" height="44" rx="4"/><path d="M22 22h20M22 30h20M22 38h12" stroke-linecap="round"/><path d="M40 44l4 4 8-9" stroke-linecap="round" stroke="var(--pirinc)"/></svg>`,
    kur: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="32" cy="32" r="20"/><path d="M32 20v12l8 5"/></svg>`,
    takvim: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="10" y="14" width="44" height="40" rx="5"/><path d="M10 25h44M22 9v9M42 9v9" stroke-linecap="round"/><rect x="18" y="32" width="9" height="8" rx="2" fill="var(--pirinc)" stroke="none"/></svg>`,
    teams: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="14" width="48" height="36" rx="5"/><path d="M8 23h48" /><circle cx="14" cy="18.5" r="1.4" fill="currentColor"/><circle cx="19" cy="18.5" r="1.4" fill="currentColor"/><path d="M26 36h12M33 31l5 5-5 5" stroke-linecap="round"/></svg>`,
    eklenti: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M14 22h10a5 5 0 1 1 10 0h10v10a5 5 0 1 1 0 10v10H34a5 5 0 1 0-10 0H14V42a5 5 0 1 0 0-10z"/></svg>`,
    iyi: `<svg viewBox="0 0 22 22" aria-hidden="true"><circle cx="11" cy="11" r="10" fill="currentColor" opacity=".14"/><path d="M6.5 11.2l3 3 6-6.4" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    uyari: `<svg viewBox="0 0 22 22" aria-hidden="true"><circle cx="11" cy="11" r="10" fill="currentColor" opacity=".14"/><path d="M11 6.5v5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/><circle cx="11" cy="15.2" r="1.1" fill="currentColor"/></svg>`,
    kotu: `<svg viewBox="0 0 22 22" aria-hidden="true"><circle cx="11" cy="11" r="10" fill="currentColor" opacity=".14"/><path d="M7.5 7.5l7 7M14.5 7.5l-7 7" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>`,
  };

  // ---------- durum ----------
  let D = { dil: "tr", adim: 0, cevap: {}, durum: null };
  let t = M.tr;
  const api = async (yol, govde, ham) => {
    if (ONIZLEME) return ornek(yol, govde);
    const o = govde === undefined ? {} : { method: "POST", headers: ham ? {} : { "Content-Type": "application/json" }, body: ham ? govde : JSON.stringify(govde) };
    const r = await fetch("/api/" + yol, o); if (!r.ok) throw new Error((await r.text()) || r.status); return r.json();
  };
  let kayitSira = Promise.resolve();
  const kaydet = () => { kayitSira = kayitSira.then(() => api("kaydet", { dil: D.dil, adim: D.adim, cevap: D.cevap })).catch(() => {}); return kayitSira; };
  async function durumAl() { try { D.durum = await api("durum"); } catch (e) { D.durum = D.durum || {}; } indirmeGoster(); return D.durum; }

  // örnek veriler (önizleme)
  function ornek(yol) {
    const d = {
      mac: { islemci: "Apple M3", arm: true, macos: "15.1", macos_ok: true, bellek_gb: 16, disk_gb: 84, python: "3.9.6", chrome: true, teams_uygulama: true },
      claude: { kurulu: true, surum: "2.1.4", giris: true },
      modeller: { durum: "iniyor", yuzde: 38 }, eklenti: { bagli: false }, kod: "~/Suflor.me",
      proje: "~/Suflor", varsayilan_ad: "Ayşe Yılmaz",
      takvim: { durum: "ok", takvimler: [{ ad: "İş", hesap: "Exchange", sec: true }, { ad: "Kişisel", hesap: "iCloud", sec: true }, { ad: "Türkiye tatilleri", hesap: "iCloud", sec: false }],
        olaylar: [{ saat: "14:00", bitis: "14:45", baslik: "Bütçe görüşmesi", platform: "teams" }, { saat: "16:30", bitis: "17:00", baslik: "Haftalık ekip", platform: "teams" }] },
      profil: { durum: "hazir", metin: "Ayşe, operasyon müdürü. Toplantılarının çoğunu kendisi yönetiyor; tedarikçi ve ekip toplantıları ağırlıkta.\n\nKartlarda önce: sahibi ve tarihi belli olmayan işler, rakam tutarsızlıkları.\nRahatsız etme: genel bilgi, terim açıklaması.", terimler: ["Logo Tiger", "Jira", "Can Demir", "Elif Kaya"] },
      kur: { ayar: "iyi", proje: "iyi", not: "iyi", aktarici: "bekle", modeller: "bekle" },
    };
    if (yol === "durum") return Promise.resolve(d);
    if (yol === "profil") return Promise.resolve(d.profil);
    return Promise.resolve({ ok: true, ...d });
  }

  // ---------- adımlar ----------
  const satir = (dur, ad, ac, eylem = "") => `<div class="satir"><span class="durum ${dur}">${dur === "bekle" ? "" : S[dur] || ""}</span><div><div class="ad">${esc(ad)}</div>${ac ? `<div class="ac">${esc(ac)}</div>` : ""}</div><div class="eylem">${eylem}</div></div>`;
  const dug = (id, yazi) => `<button class="ikincil-dug" type="button" data-eylem="${id}">${esc(yazi)}</button>`;
  const yonga = (grup, deger, secili) => `<button class="yonga" type="button" data-grup="${grup}" data-deger="${esc(deger)}" aria-pressed="${!!secili}">${esc(deger)}</button>`;
  const C = D.cevap;
  const alan = (id, etiket, ipucu = "", tur = "text") => `<div class="alan"><label for="${id}">${esc(etiket)}</label>${tur === "textarea"
    ? `<textarea id="${id}" data-cevap="${id}">${esc(D.cevap[id] || "")}</textarea>` : `<input type="text" id="${id}" data-cevap="${id}" value="${esc(D.cevap[id] || "")}">`}${ipucu ? `<div class="ipucu">${esc(ipucu)}</div>` : ""}</div>`;

  const ADIMLAR = [
    { id: "karsilama", simge: null, cubuksuz: true,
      ciz: () => `<div class="adim karsilama"><div class="simge isaret">${S.isaret}</div>
        <div class="selam" aria-label="Merhaba, Hello"><span>merhaba</span><span>hello</span></div>
        <div class="diller"><button class="dil" type="button" data-dil="tr" aria-pressed="${D.dil === "tr"}">Türkçe</button><button class="dil" type="button" data-dil="en" aria-pressed="${D.dil === "en"}">English</button></div></div>` },
    { id: "hosgeldin", simge: "isaret", b: "hosgeldin_b", a: "hosgeldin_a",
      icerik: () => `<div class="liste">${satir("iyi", t.hg1, t.hg1a)}${satir("iyi", t.hg2, t.hg2a)}${satir("iyi", t.hg3, t.hg3a)}</div>` },
    { id: "mac", simge: "mac", b: "mac_b", a: "mac_a", hazir: () => { const m = (D.durum || {}).mac; return m && m.arm && m.macos_ok && m.python; },
      gir: async () => { await durumAl(); const m = D.durum.mac || {}; if (m.arm && m.macos_ok && m.python) api("modeller/baslat", {}).then(durumAl).catch(() => {}); },
      icerik: () => { const m = (D.durum || {}).mac; if (!m) return `<div class="liste">${satir("bekle", t.m_islemci)}${satir("bekle", t.m_macos)}${satir("bekle", t.m_python)}</div>`;
        return `<div class="liste">${satir(m.arm ? "iyi" : "kotu", t.m_islemci, m.islemci)}${satir(m.macos_ok ? "iyi" : "kotu", t.m_macos, "macOS " + m.macos)}
          ${satir(m.bellek_gb >= 16 ? "iyi" : "uyari", t.m_bellek + " · " + m.bellek_gb + " GB", m.bellek_gb >= 16 ? "" : t.m_bellek_az)}
          ${satir(m.disk_gb >= 7 ? "iyi" : "kotu", t.m_disk + " · " + m.disk_gb + " GB", m.disk_gb >= 7 ? "" : "7 GB")}
          ${satir(m.python ? "iyi" : "kotu", t.m_python, m.python ? m.python : t.m_python_ac, m.python ? "" : dug("python", t.m_python_dug))}
          ${satir(m.chrome ? "iyi" : "uyari", t.m_chrome, m.chrome ? "" : t.m_chrome_ac, m.chrome ? "" : dug("chrome-indir", t.m_chrome_dug))}</div>`; } },
    { id: "claude", simge: "claude", b: "claude_b", a: "claude_a", hazir: () => { const c = (D.durum || {}).claude || {}; return (c.kurulu && c.giris) || C.kartsiz; },
      gir: durumAl,
      icerik: () => { const c = (D.durum || {}).claude || {};
        return `<div class="liste">${satir(c.kurulu ? "iyi" : "kotu", c.kurulu ? t.c_kurulu : t.c_yok, c.surum || "", c.kurulu ? "" : dug("claude-kur", t.c_kur))}
          ${satir(c.giris ? "iyi" : "uyari", c.giris ? t.c_giris : t.c_giris_yok, "", dug("claude-denetle", t.c_denetle))}</div>
          ${c.kurulu && c.giris ? "" : `<p class="dipnot">${esc(t.c_aciklama)}</p><p class="dipnot">${dug("kartsiz", t.c_kartsiz)}<br>${esc(t.c_kartsiz_a)}</p>`}`; } },
    { id: "sen", simge: "sen", b: "sen_b", a: "sen_a", hazir: () => (C.ad || "").trim().length > 1,
      gir: () => { if (!C.ad && D.durum && D.durum.varsayilan_ad) C.ad = D.durum.varsayilan_ad; },
      icerik: () => `${alan("ad", t.ad, t.ad_i)}<div class="iki">${alan("rol", t.rol)}${alan("sirket", t.sirket)}</div>
        <div class="alan"><span class="etiket">${esc(t.is_alani)}</span><div class="yongalar">${t.alanlar.map((a, i) => yonga("alan", a, C.is_alani === M.tr.alanlar[i] || C.is_alani === a)).join("")}</div></div>` },
    { id: "arac", simge: "arac", b: "arac_b", a: "arac_a",
      icerik: () => `<div class="alan"><span class="etiket">${esc(t.araclar_e)}</span><div class="yongalar">${ARACLAR.map(a => yonga("arac", a, (C.araclar || []).includes(a))).join("")}</div></div>
        ${alan("araclar_ek", t.araclar_ek, t.araclar_ek_i)}${alan("kisiler", t.kisiler, t.kisiler_i)}` },
    { id: "anlat", simge: "anlat", b: "anlat_b", a: "anlat_a",
      icerik: () => `<div class="sorular">${["s1", "s2", "s3", "s4"].map((s, i) => `<div class="alan"><label for="${s}"><span class="soru-no">${i + 1} · </span>${esc(t[s])}</label><textarea id="${s}" data-cevap="${s}" rows="2" style="min-height:64px">${esc(C[s] || "")}</textarea></div>`).join("")}</div>
        <div class="alan"><span class="etiket">${esc(t.linkedin)}</span><div class="ipucu">${esc(t.linkedin_a)}</div>
          <div class="birak" data-yukle="linkedin" tabindex="0"><b>${esc(t.birak)}</b> · ${esc(t.birak_ya)} <span class="ipucu">(PDF)</span></div>
          ${(C.linkedin_dosya ? `<div class="dosyalar"><div><span>${esc(C.linkedin_dosya)}</span><span>✓</span></div></div>` : "")}
          <textarea id="linkedin_metin" data-cevap="linkedin_metin" placeholder="${esc(t.linkedin_yapistir)}" style="min-height:64px">${esc(C.linkedin_metin || "")}</textarea></div>` },
    { id: "gorusme", simge: "gorusme", b: "gor_b", a: "gor_a",
      icerik: () => `<div class="birak" data-yukle="gorusme" tabindex="0"><b>${esc(t.gor_birak)}</b><br><span class="ipucu">${esc(t.gor_tur)}</span></div>
        ${(C.gorusmeler || []).length ? `<div class="dosyalar">${C.gorusmeler.map(d => `<div><span>${esc(d)}</span><span>✓</span></div>`).join("")}</div>` : ""}
        <p class="dipnot">${dug("ornek", (C.ornek ? "✓ " : "") + t.gor_ornek)}</p><p class="dipnot">${esc(t.gor_not)}</p>` },
    { id: "proje", simge: "klasor", b: "proje_b", a: "proje_a", gir: () => { if (!C.proje && D.durum) C.proje = D.durum.proje; },
      icerik: () => `<div class="liste">${satir("iyi", C.proje || "~/Suflor", t.proje_icerik, dug("klasor-sec", t.proje_sec))}</div>` },
    { id: "tanidim", simge: "tanidim", b: "tanidim_b", a: "tanidim_a",
      gir: async () => { if (C.kartsiz) return; if (!C.profil_metin) { try { await api("profil/olustur", { cevap: C, dil: D.dil }); } catch (e) {} profilBekle(); } },
      icerik: () => { if (!C.profil_metin && !C.kartsiz && D.profilDurum !== "yok") return `<div class="liste">${satir("bekle", t.tanidim_bekle)}</div>`;
        return `<div class="ozet"><h3>${esc(t.tanidim_not)}</h3><textarea id="profil_metin" data-cevap="profil_metin">${esc(C.profil_metin || "")}</textarea>
          ${C.kartsiz || D.profilDurum === "yok" ? `<div class="ipucu">${esc(t.tanidim_yok)}</div>` : ""}</div>
          ${(C.terimler || []).length ? `<div class="alan"><span class="etiket">${esc(t.tanidim_terim)}</span><div class="yongalar">${C.terimler.map(x => yonga("terim", x, !(C.terim_cikar || []).includes(x))).join("")}</div></div>` : ""}`; } },
    { id: "paylas", simge: "isaret", b: "paylas_b", a: "paylas_a", hazir: () => typeof C.teshis === "boolean",
      icerik: () => `<div class="liste">${satir("iyi", t.p_gider, t.p_gider_a)}${satir("kotu", t.p_gitmez, t.p_gitmez_a)}</div>
        <div class="yongalar" style="justify-content:center">${yonga("teshis", t.p_evet, C.teshis === true)}${yonga("teshis", t.p_hayir, C.teshis === false)}</div>
        <p class="dipnot">${esc(t.p_not)}</p>` },
    { id: "kur", simge: "kur", b: "kur_b", a: "kur_a", hazir: () => { const k = D.kurDurum || {}; return k.ayar === "iyi" && k.aktarici === "iyi"; },
      gir: async () => { D.kurDurum = { ayar: "bekle", proje: "bekle", not: "bekle", aktarici: "bekle" }; ciz();
        try { D.kurDurum = await api("kur/tamamla", { cevap: C, dil: D.dil }); } catch (e) { D.kurDurum = { ...D.kurDurum, hata: String(e.message || e) }; } await durumAl(); ciz(); },
      icerik: () => { const k = D.kurDurum || {}, m = (D.durum || {}).modeller || {};
        return `<div class="liste">${satir(k.ayar || "bekle", t.k_ayar)}${satir(k.proje || "bekle", t.k_proje, C.proje || "")}${satir(k.not || "bekle", t.k_not)}${satir(k.aktarici || "bekle", t.k_aktarici)}
          ${satir(m.durum === "hazir" ? "iyi" : m.durum === "hata" ? "kotu" : "bekle", t.k_modeller, m.durum === "hazir" ? "" : m.durum === "hata" ? (m.mesaj || "") : `%${m.yuzde || 0}`)}</div>
          ${k.hata ? `<div class="kart-not uyari">${esc(k.hata)}</div>` : ""}`; } },
    { id: "takvim", simge: "takvim", b: "takvim_b", a: "takvim_a", gir: durumAl,
      icerik: () => { const tk = (D.durum || {}).takvim || {};
        if (tk.durum !== "ok") return `<div class="liste">${satir(tk.durum === "izin_yok" ? "uyari" : "bos", t.t_izin_b, t.t_izin_a, dug("takvim-izin", t.t_izin))}</div>`;
        const tl = tk.takvimler || [];
        return `${tl.length ? `<div class="alan"><span class="etiket">${esc(t.t_dogru)}</span><div class="yongalar">${tl.map(x => yonga("takvim", x.ad + " · " + x.hesap, !(C.takvim_cikar || []).includes(x.ad + " · " + x.hesap) && x.sec !== false)).join("")}</div></div>`
          : `<div class="kart-not">${esc(t.t_hesap_yok)} ${dug("internet-hesaplari", t.t_hesap_ekle)}</div>`}
          <div class="alan"><span class="etiket">${esc(t.t_bugun)}</span><div class="liste">${(tk.olaylar || []).length ? tk.olaylar.map(o => satir("iyi", o.baslik, `${o.saat}–${o.bitis}${o.platform ? " · " + o.platform : ""}`)).join("") : satir("iyi", t.t_bos)}</div></div>`; } },
    { id: "teams", simge: "teams", b: "teams_b", a: "teams_a", kosul: () => ((D.durum || {}).mac || {}).teams_uygulama,
      icerik: () => `<ol class="adimlar"><li>${esc(t.tm1)}</li><li>${esc(t.tm2)}</li><li>${esc(t.tm3)}</li></ol><p class="dipnot">${dug("teams-dene", t.tm_dene)}</p>` },
    { id: "eklenti", simge: "eklenti", b: "ek_b", a: "ek_a", hazir: () => ((D.durum || {}).eklenti || {}).bagli, gir: () => eklentiBekle(),
      icerik: () => { const e = (D.durum || {}).eklenti || {};
        return `<ol class="adimlar"><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e1)}<div class="eylem">${dug("chrome-eklentiler", t.e1d)}</div></div></li>
          <li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e2)}<div class="eylem">${dug("eklenti-klasoru", t.e2d)}</div></div></li><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e3)}</div></li></ol>
          <div class="liste">${satir(e.bagli ? "iyi" : "bekle", e.bagli ? t.e_bagli : t.e_bekle, e.surum ? "v" + e.surum : "")}</div>
          ${e.bagli ? "" : `<p class="dipnot">${dug("atla", t.atla)}</p>`}`; } },
    { id: "bitti", simge: "isaret", b: "bitti_b", a: "bitti_a", son: true,
      icerik: () => `<ol class="adimlar"><li>${esc(t.b1)}</li><li>${esc(t.b2)}</li><li>${esc(t.b3)}</li></ol>` },
  ];
  const gorunen = () => ADIMLAR.filter(a => !a.kosul || a.kosul());

  // ---------- çizim ----------
  let yon = 1;
  function ciz() {
    const ads = gorunen(); D.adim = Math.max(0, Math.min(D.adim, ads.length - 1)); const a = ads[D.adim];
    const sahne = $("#sahne");
    sahne.innerHTML = a.ciz ? a.ciz() : `<section class="adim ${yon < 0 ? "geri" : ""}" aria-labelledby="baslik">
      <div class="simge ${a.simge === "isaret" ? "isaret" : ""}">${S[a.simge] || ""}</div>
      <h1 id="baslik">${esc(t[a.b])}</h1><p class="alt">${esc(t[a.a])}</p>
      <div class="icerik">${a.icerik ? a.icerik() : ""}</div></section>`;
    const odak = sahne.querySelector("input, textarea"); if (odak && !odak.value && D.ilkCizim !== a.id) { odak.focus(); } D.ilkCizim = a.id;
    $("#alt-cubuk").style.visibility = a.cubuksuz ? "hidden" : "visible";
    $("#geri").textContent = t.geri; $("#geri").style.visibility = D.adim > 0 ? "visible" : "hidden";
    const d = $("#devam"); d.textContent = a.son ? t.bitir : a.id === "hosgeldin" ? t.basla : t.devam; d.disabled = a.hazir ? !a.hazir() : false;
    $("#noktalar").innerHTML = ads.map((_, i) => `<i class="${i === D.adim ? "su" : i < D.adim ? "bitti" : ""}"></i>`).join("");
    document.documentElement.lang = D.dil;
  }
  async function git(n) {
    const ads = gorunen(); yon = n > D.adim ? 1 : -1; D.adim = n; ciz(); kaydet();
    const a = ads[D.adim]; if (a && a.gir) { await a.gir(); if (gorunen()[D.adim] === a) ciz(); }
  }
  function indirmeGoster() {
    const m = (D.durum || {}).modeller || {}; const k = $("#indirme");
    if (!m.durum || m.durum === "yok" || D.adim < 2) { k.hidden = true; return; }  // karşılamada gösterme
    k.hidden = false; $("#indirme-yazi").textContent = m.durum === "hazir" ? t.indi : `${t.indiriliyor} · %${m.yuzde || 0}`;
    $("#indirme-cubuk").style.width = (m.durum === "hazir" ? 100 : m.yuzde || 0) + "%";
  }
  async function profilBekle() {
    for (let i = 0; i < 90; i++) {
      const p = await api("profil").catch(() => ({}));
      if (p.durum === "hazir") { C.profil_metin = p.metin; C.terimler = p.terimler || []; D.profilDurum = "hazir"; kaydet(); break; }
      if (p.durum === "yok" || p.durum === "hata") { D.profilDurum = "yok"; break; }
      await new Promise(r => setTimeout(r, 2000));
    }
    if (gorunen()[D.adim].id === "tanidim") ciz();
  }
  async function eklentiBekle() {
    while (gorunen()[D.adim] && gorunen()[D.adim].id === "eklenti") {
      await durumAl(); ciz(); if (((D.durum || {}).eklenti || {}).bagli) break; await new Promise(r => setTimeout(r, 3000));
    }
  }

  // ---------- olaylar ----------
  document.addEventListener("click", async e => {
    const dl = e.target.closest("[data-dil]");
    if (dl) { D.dil = dl.dataset.dil; t = M[D.dil]; git(1); return; }
    const y = e.target.closest(".yonga");
    if (y) {
      const g = y.dataset.grup, v = y.dataset.deger, on = y.getAttribute("aria-pressed") !== "true";
      if (g === "alan") { C.is_alani = v; } else if (g === "teshis") { C.teshis = v === t.p_evet; } else {
        const anahtar = { arac: "araclar", terim: "terim_cikar", takvim: "takvim_cikar" }[g]; const l = new Set(C[anahtar] || []);
        if (g === "arac" ? on : !on) l.add(v); else l.delete(v); C[anahtar] = [...l];
      }
      kaydet(); ciz(); return;
    }
    const ey = e.target.closest("[data-eylem]");
    if (ey) {
      const n = ey.dataset.eylem;
      if (n === "kartsiz") { C.kartsiz = true; kaydet(); ciz(); return; }
      if (n === "atla") { git(D.adim + 1); return; }
      if (n === "ornek") { C.ornek = !C.ornek; kaydet(); ciz(); return; }
      if (n === "claude-denetle") { await api("claude/denetle", {}).catch(() => {}); await durumAl(); ciz(); return; }
      if (n === "klasor-sec") { const r = await api("klasor-sec", {}).catch(() => ({})); if (r.yol) { C.proje = r.yol; kaydet(); ciz(); } return; }
      if (n === "takvim-izin") { await api("ac", { hedef: n }).catch(() => {}); await durumAl(); ciz(); return; }
      api("ac", { hedef: n }).catch(() => {});
      return;
    }
    const bk = e.target.closest(".birak"); if (bk) dosyaSec(bk.dataset.yukle);
  });
  document.addEventListener("input", e => { const k = e.target.dataset && e.target.dataset.cevap; if (k) { C[k] = e.target.value; const a = gorunen()[D.adim]; if (a.hazir) $("#devam").disabled = !a.hazir(); clearTimeout(D.zz); D.zz = setTimeout(kaydet, 500); } });
  document.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && e.target.tagName !== "TEXTAREA" && !$("#devam").disabled && e.target.tagName !== "BUTTON") $("#devam").click(); });
  $("#devam").addEventListener("click", () => { const a = gorunen()[D.adim]; if (a.son) { api("ac", { hedef: "pano" }).catch(() => {}); return; } git(D.adim + 1); });
  $("#geri").addEventListener("click", () => git(D.adim - 1));

  // dosya bırakma / seçme
  ["dragover", "dragleave", "drop"].forEach(ev => document.addEventListener(ev, e => {
    const bk = e.target.closest && e.target.closest(".birak"); if (!bk) return; e.preventDefault();
    bk.classList.toggle("ustunde", ev === "dragover"); if (ev === "drop") yukle(bk.dataset.yukle, [...e.dataTransfer.files]);
  }));
  function dosyaSec(tur) { const i = document.createElement("input"); i.type = "file"; i.multiple = tur === "gorusme"; i.accept = tur === "linkedin" ? ".pdf" : ".docx,.vtt,.txt,.md";
    i.onchange = () => yukle(tur, [...i.files]); i.click(); }
  async function yukle(tur, dosyalar) {
    for (const f of dosyalar) {
      try { await api(`yukle?tur=${tur}&ad=${encodeURIComponent(f.name)}`, f, true); } catch (e) { continue; }
      if (tur === "linkedin") C.linkedin_dosya = f.name; else C.gorusmeler = [...new Set([...(C.gorusmeler || []), f.name])];
    }
    kaydet(); ciz();
  }

  // ---------- başlangıç ----------
  (async () => {
    try { const k = await api("kayit"); if (k && k.dil) { D.dil = k.dil; D.adim = k.adim || 0; Object.assign(C, k.cevap || {}); } } catch (e) {}
    t = M[D.dil] || M.tr; await durumAl(); ciz();
    const a = gorunen()[D.adim]; if (a && a.gir) { await a.gir(); ciz(); }
    setInterval(() => { if (!document.hidden) durumAl(); }, 5000);
  })();
})();
