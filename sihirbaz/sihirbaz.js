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
      sen_a: "Kartlar senin bakışından yazılsın diye. Yalnız adın gerekli; gerisini şimdi ya da sonra verebilirsin. Bu bilgiler yalnız bu Mac'te kalır.",
      araclar_tek: "Sık kullandığın araçlar (isteğe bağlı)", araclar_ek_i: "Virgülle ayır: örneğin Jira, Logo Tiger",
      kisiler_tek: "Sık görüştüğün kişiler (isteğe bağlı)", kisiler_i: "Konuşma tanıma adları doğru yazsın diye. Virgülle ayır.",
      gor_birak: "Teams dökümlerini buraya bırak (isteğe bağlı)",
      sen_not: "Dökümler Claude'un seni tanımasının en hızlı yolu: kurulumda senin için bir çalışma notu taslağı hazırlar, ilk toplantının sonunda onaylarsın. Dosyalar proje klasörüne kopyalanır, hiçbir yere gönderilmez.",
      sonra: "Sonra",
      p_anahtar: "Bir şey aksarsa teknik bilgi geliştiriciye gitsin (beta)",
      p_gider_a: "Gider: sürümler, Mac modeli, hata türü ve yeri, gecikmeler ve sayılar.", p_gitmez_a: "Asla gitmez: döküm, kişi ve toplantı adları, kartlar, notlar, takvim, belgeler.",
      teams_not: "Teams uygulaması kurulu: toplantıya davetteki bağlantıdan katıl ve \"Bu tarayıcıda devam et\"i seç; Suflor.me Teams'i Chrome'da izler. Panodaki Başlat toplantıyı her zaman tarayıcıda açar.",
      bitti_a: "Toplantından önce panodaki Başlat'a bas. Kartlar panoda ve toplantı penceresinin köşesinde görünür.",
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
      c_kurulu: "Claude Code kurulu", c_yok: "Claude Code bulunamadı", c_giris: "Oturum açık", c_giris_yok: "Oturum açılmamış ya da denetlenmedi", c_giris_degil: "Oturum açık değil",
      c_kur: "Terminal'de kur ve giriş yap", c_denetle: "Yeniden denetle",
      c_aciklama: "Terminal açılır ve kurulum komutu hazır yazılı olur. Bitince açılan Claude'da hesabınla giriş yap, sonra buraya dön.",
      c_kartsiz: "Aboneliğim yok, kartsız devam et",
      c_yol_yok: "Terminal'de claude komutu bulunmuyor", c_yol_ac: "Claude Code kurulu ama Terminal onu tanımıyor; /toplanti için gerekli.", c_yol_dug: "Terminal'e tanıt",
      c_denetleniyor: "Denetleniyor… (en çok 90 sn)", c_giris_dug: "Terminal'de giriş yap",
      c_n_giris: "Claude Code'da oturum açılmamış.", c_n_zaman: "Claude 90 saniyede yanıt vermedi. İnternet bağlantına bakıp yeniden denetle.",
      c_n_hata: "Claude denetimi başarısız: ", c_n_yok: "Claude Code bulunamadı.",
      c_n_abonelik: "Hesabında Claude Code kullanımı yok ya da kullanım sınırın doldu. Pro ya da üstü abonelik gerekir; istersen kartsız devam edebilirsin.",
      c_ga_b: "Terminal'de giriş", c_ga1: "\"Terminal'de giriş yap\"a bas: Claude, Terminal'de açılır.", c_ga2: "Giriş isterse yönergeyi izle; istemezse /login yazıp Return'e bas.",
      c_ga3: "Claude aboneliğinin olduğu hesapla gir, girişi görünce /exit yaz.", c_ga4: "Buraya dön: sihirbaz kendisi yeniden denetler.",
      c_masaustu: "Claude masaüstü uygulamasındaki giriş sayılmaz; Terminal'deki Claude ayrıca giriş ister.",
      c_kartsiz_a: "Kartsız kipte döküm, pano ve notlar çalışır; kart ve özet olmaz. Sonradan Claude bağlayabilirsin.",
      sen_b: "Seni tanıyalım",       ad: "Adın", ad_i: "Toplantılarda göründüğü gibi", rol: "Rolün ya da unvanın", sirket: "Şirketin (isteğe bağlı)", is_alani: "İş alanın",
      alanlar: ["E-ticaret", "Yazılım", "Danışmanlık", "Finans", "Sağlık", "Eğitim", "Üretim", "Kamu", "Diğer"],
                                                                              gor_tur: ".docx · .vtt · .txt · .md",
      gor_ornek: "Dökümüm yok, örnek bir görüşmeyle dene",       proje_b: "Belgelerin nerede dursun?", proje_a: "Suflor.me toplantı özetlerini bu klasöre yazar; buraya koyduğun belgeler kartlara kaynak olur.",
      proje_sec: "Başka bir klasör seç…", proje_icerik: "İçinde belgeler, görüşmeler ve kanıtlar için alt klasörler açılır.",
                                                kur_b: "Kuruyorum", kur_a: "Ayarlarını yazıyor, arka plan hizmetini, takvim ve ses yardımcılarını kuruyorum. macOS \"Suflor Ses\" için sistem sesi kaydı izni sorarsa İzin Ver de.",
      k_ayar: "Ayarlar", k_proje: "Proje klasörü", k_not: "Çalışma notu", k_not_a: "Claude arka planda taslağını hazırlıyor; ilk toplantının sonunda onaylarsın", k_aktarici: "Arka plan hizmeti", k_modeller: "Konuşma tanıma modelleri",
      k_m_yeniden: "Yeniden dene", k_m_hata: "Modeller kurulamadı. İnternet bağlantını denetleyip yeniden dene.", k_m_baska: "Modeller bu Mac'teki başka bir hesabın klasöründe ve eksik. O hesapta Suflor.me'yi güncelle (guncelle.command), sonra burada yeniden dene.",
      k_ses: "Karşı tarafın sesi (Suflor Ses)", k_ses_ok: "Hazır; ilk toplantıda izin istenebilir", k_ses_yok: "Kurulamadı; karşı ses için Suflor.me simgesi → Karşı taraf → Aç", k_ses_izin: "İzin ayarını aç",
      takvim_b: "Takvimini bağlayalım", takvim_a: "Toplantından birkaç dakika önce hatırlatır, gündemi ve katılımcıları davetten alır.",
      t_izin: "Erişim ver", t_izin_b: "Takvim izni", t_izin_a: "macOS bir izin penceresi açacak: \"Tam erişim\"i seç.",
      t_hesap_yok: "Mac'in Takvim uygulamasında hesap görünmüyor.", t_hesap_ekle: "Google, iCloud ya da Outlook hesabını ekle",
      t_bugun: "Bugün gördüklerim", t_bos: "Bugün başka toplantın yok.", t_dogru: "Takvimlerin bunlar mı? İzlenmesini istemediklerinin işaretini kaldır.", t_adres: "Hangi adresler senin? Yalnız bu adreslerin davetli ya da düzenleyen olduğu toplantıları gösteririm; Takvim'e eklenmiş başkalarının takvimleri listeye girmez.",
      t_adres_bekle: "Takvimdeki adresleri okuyorum…", t_adres_ek: "Listede olmayan bir adresin", t_adres_yok: "Adres seçmezsen macOS'un seni tanıdığı yere bakarım; Takvim'e başkalarının takvimi eklenmişse onların toplantıları da görünebilir.",
                                    ek_b: "Chrome eklentisini ekle", ek_a: "Eklenti Teams sayfasından sesi ve altyazıyı alır, kartları ekranın köşesinde gösterir.",
      e1: "Chrome'un eklenti sayfasını aç ve sağ üstte Geliştirici modu'nu aç.", e1d: "Eklenti sayfasını aç",
      e2: "\"Paketlenmemiş öğe yükle\"ye bas ve Suflor.me klasörünü seç.", e2d: "Klasörü Finder'da göster",
      e3: "Araç çubuğundaki yapboz simgesinden Suflor.me'yi sabitle.",
      e_bekle: "Eklentiyi bekliyorum…", e_bagli: "Eklenti bağlandı",
      e_coklu: "Bu Mac'te başka bir hesabın Suflor.me'si de çalışıyor. Chrome'da Suflor.me simgesine tıkla ve bu hesabın alanını seç: ", e_profil: "Eklentiyi Teams'e girdiğin Chrome profiline ekle; birden fazla Chrome profilin varsa doğru pencerede olduğuna bak.",
      bitti_b: "Hazırsın",                             },
    en: {
      sen_a: "So the cards are written from your point of view. Only your name is required; the rest can come now or later. This stays on this Mac.",
      araclar_tek: "Tools you use often (optional)", araclar_ek_i: "Separate with commas: e.g. Jira, Salesforce",
      kisiler_tek: "People you meet often (optional)", kisiler_i: "So speech recognition spells their names right. Separate with commas.",
      gor_birak: "Drop Teams transcripts here (optional)",
      sen_not: "Transcripts are the fastest way for Claude to get to know you: during setup it drafts a working note for you, and you approve it after your first meeting. Files are copied into your project folder and never sent anywhere.",
      sonra: "Later",
      p_anahtar: "If something breaks, send technical details to the developer (beta)",
      p_gider_a: "Sent: versions, Mac model, error type and location, delays and counts.", p_gitmez_a: "Never sent: transcripts, names of people and meetings, cards, notes, calendar, documents.",
      teams_not: "The Teams app is installed: join from the invitation link and choose \"Continue on this browser\"; Suflor.me follows Teams in Chrome. Start on the panel always opens the meeting in the browser.",
      bitti_a: "Before your meeting, press Start on the panel. Cards appear on the panel and in the corner of the meeting window.",
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
      c_kurulu: "Claude Code is installed", c_yok: "Claude Code not found", c_giris: "Signed in", c_giris_yok: "Not signed in or not checked yet", c_giris_degil: "Not signed in",
      c_kur: "Install and sign in with Terminal", c_denetle: "Check again",
      c_aciklama: "Terminal opens with the install command ready. When it finishes, sign in to Claude, then come back here.",
      c_kartsiz: "No subscription, continue without cards",
      c_yol_yok: "Terminal doesn't know the claude command", c_yol_ac: "Claude Code is installed but Terminal can't find it; /toplanti needs it.", c_yol_dug: "Add to Terminal",
      c_denetleniyor: "Checking… (up to 90 s)", c_giris_dug: "Sign in with Terminal",
      c_n_giris: "You're not signed in to Claude Code.", c_n_zaman: "Claude didn't answer within 90 seconds. Check your internet connection and try again.",
      c_n_hata: "Claude check failed: ", c_n_yok: "Claude Code not found.",
      c_n_abonelik: "Your account has no Claude Code access or has hit its usage limit. A Pro or higher subscription is needed; you can also continue without cards.",
      c_ga_b: "Signing in with Terminal", c_ga1: "Press \"Sign in with Terminal\": Claude opens in Terminal.", c_ga2: "If it asks you to sign in, follow the prompts; if not, type /login and press Return.",
      c_ga3: "Sign in with the account that has your Claude subscription, then type /exit.", c_ga4: "Come back here: the wizard checks again by itself.",
      c_masaustu: "Being signed in to the Claude desktop app doesn't count; Claude in Terminal needs its own sign-in.",
      c_kartsiz_a: "Without cards you still get the transcript, the panel and notes; no cards or summaries. You can connect Claude later.",
      sen_b: "Tell us about you",       ad: "Your name", ad_i: "As it appears in meetings", rol: "Your role or title", sirket: "Company (optional)", is_alani: "Your field",
      alanlar: ["E-commerce", "Software", "Consulting", "Finance", "Healthcare", "Education", "Manufacturing", "Public sector", "Other"],
                                                                              gor_tur: ".docx · .vtt · .txt · .md",
      gor_ornek: "No transcripts, try a sample meeting",       proje_b: "Where should your documents live?", proje_a: "Suflor.me writes meeting summaries here; documents you keep here become sources for the cards.",
      proje_sec: "Choose another folder…", proje_icerik: "Subfolders for documents, meetings and evidence are created inside.",
                                                kur_b: "Setting up", kur_a: "Writing your settings and installing the background service, calendar and audio helpers. If macOS asks for system audio recording permission for \"Suflor Ses\", choose Allow.",
      k_ayar: "Settings", k_proje: "Project folder", k_not: "Working note", k_not_a: "Claude is drafting it in the background; you approve it after your first meeting", k_aktarici: "Background service", k_m_yeniden: "Try again", k_m_hata: "The models couldn't be installed. Check your internet connection and try again.",
      k_m_baska: "The models are in another account's folder on this Mac and incomplete. Update Suflor.me in that account (guncelle.command), then try again here.",
      k_ses: "Other side's audio (Suflor Ses)", k_ses_ok: "Ready; permission may be asked in your first meeting", k_ses_yok: "Couldn't be installed; for the other side's audio: Suflor.me icon → Other side → Open", k_ses_izin: "Open permission settings",
      k_modeller: "Speech recognition models",
      takvim_b: "Connect your calendar", takvim_a: "It reminds you a few minutes before a meeting and takes the agenda and attendees from the invitation.",
      t_izin: "Allow access", t_izin_b: "Calendar permission", t_izin_a: "macOS will ask for permission: choose \"Full Access\".",
      t_hesap_yok: "No accounts in the Mac Calendar app.", t_hesap_ekle: "Add your Google, iCloud or Outlook account",
      t_bugun: "What I see today", t_bos: "No more meetings today.", t_dogru: "Are these your calendars? Untick any you don't want followed.", t_adres: "Which addresses are yours? I only show meetings where one of them is invited or organizes; other people's calendars added to Calendar stay out.",
      t_adres_bekle: "Reading the addresses in your calendar…", t_adres_ek: "Another address of yours", t_adres_yok: "With no address selected I go by who macOS thinks you are; if other people's calendars are added, their meetings may show too.",
                                    ek_b: "Add the Chrome extension", ek_a: "The extension takes sound and captions from the Teams page and shows the cards in a corner of the screen.",
      e1: "Open Chrome's extensions page and switch on Developer mode at the top right.", e1d: "Open extensions page",
      e2: "Click \"Load unpacked\" and choose the Suflor.me folder.", e2d: "Show the folder in Finder",
      e3: "Pin Suflor.me from the puzzle icon in the toolbar.",
      e_bekle: "Waiting for the extension…", e_bagli: "Extension connected",
      e_coklu: "Another account's Suflor.me is also running on this Mac. Click the Suflor.me icon in Chrome and pick this account's workspace: ", e_profil: "Add the extension to the Chrome profile you use for Teams; if you have several profiles, make sure you're in the right window.",
      bitti_b: "You're all set",                             },
  };
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
        adaylar: [["ayse", "Ayşe Yılmaz", 40], ["ekip", null, 12], ["ayse.yilmaz", null, 3]].map(([k, ad, sayi]) => ({ adres: k + "@" + "ornek.test", ad, sayi })), adresler: null,  // uydurma adresler
        olaylar: [{ saat: "14:00", bitis: "14:45", baslik: "Bütçe görüşmesi", platform: "teams" }, { saat: "16:30", bitis: "17:00", baslik: "Haftalık ekip", platform: "teams" }] },
      kur: { ayar: "iyi", proje: "iyi", not: "iyi", aktarici: "bekle", modeller: "bekle" },
    };
    if (yol === "durum") return Promise.resolve(d);
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
      gir: async () => { await durumAl(); const m = D.durum.mac || {}; if (m.arm && m.macos_ok && m.python) api("modeller/baslat", {}).then(durumAl).catch(() => {});
        if (yon > 0 && m.arm && m.macos_ok && m.python && m.bellek_gb >= 16 && m.disk_gb >= 7 && m.chrome)
          setTimeout(() => { const a = gorunen()[D.adim]; if (a && a.id === "mac") git(D.adim + 1); }, 2000); },
      icerik: () => { const m = (D.durum || {}).mac; if (!m) return `<div class="liste">${satir("bekle", t.m_islemci)}${satir("bekle", t.m_macos)}${satir("bekle", t.m_python)}</div>`;
        return `<div class="liste">${satir(m.arm ? "iyi" : "kotu", t.m_islemci, m.islemci)}${satir(m.macos_ok ? "iyi" : "kotu", t.m_macos, "macOS " + m.macos)}
          ${satir(m.bellek_gb >= 16 ? "iyi" : "uyari", t.m_bellek + " · " + m.bellek_gb + " GB", m.bellek_gb >= 16 ? "" : t.m_bellek_az)}
          ${satir(m.disk_gb >= 7 ? "iyi" : "kotu", t.m_disk + " · " + m.disk_gb + " GB", m.disk_gb >= 7 ? "" : "7 GB")}
          ${satir(m.python ? "iyi" : "kotu", t.m_python, m.python ? m.python : t.m_python_ac, m.python ? "" : dug("python", t.m_python_dug))}
          ${satir(m.chrome ? "iyi" : "uyari", t.m_chrome, m.chrome ? "" : t.m_chrome_ac, m.chrome ? "" : dug("chrome-indir", t.m_chrome_dug))}</div>`; } },
    { id: "claude", simge: "claude", b: "claude_b", a: "claude_a", hazir: () => { const c = (D.durum || {}).claude || {}; return (c.kurulu && c.giris) || C.kartsiz; },
      // adıma girince oturum bilinmiyorsa kendiliğinden denetler; Terminal'den dönünce (pencere odağı) yeniden denetler
      gir: async () => { await durumAl(); const c = (D.durum || {}).claude || {}; if (c.kurulu && c.giris !== true) await claudeDenetle(); },
      icerik: () => { const c = (D.durum || {}).claude || {};
        // Terminal'de komut yoksa söyle; denetim başarısızsa nedeni. v0.13.5: oturum yoksa giriş düğmesi her zaman + adım adım yönerge
        const n = !c.giris && c.neden ? c.neden : null;
        const nm = n ? (n.tur === "giris" ? t.c_n_giris : n.tur === "abonelik" ? t.c_n_abonelik : n.tur === "zaman" ? t.c_n_zaman : n.tur === "yok" ? t.c_n_yok : t.c_n_hata + (n.ham || "")) : "";
        const girisSatiri = D.claudeDen ? satir("bekle", t.c_denetleniyor)
          : satir(c.giris ? "iyi" : "uyari", c.giris ? t.c_giris : n ? t.c_giris_degil : t.c_giris_yok, nm, (c.kurulu && !c.giris ? dug("claude-giris", t.c_giris_dug) : "") + dug("claude-denetle", t.c_denetle));
        const adimlar = c.kurulu && !c.giris && !D.claudeDen && (!n || n.tur === "giris" || n.tur === "hata")
          ? `<div class="alan"><span class="etiket">${esc(t.c_ga_b)}</span><ol class="adimlar"><li>${esc(t.c_ga1)}</li><li>${esc(t.c_ga2)}</li><li>${esc(t.c_ga3)}</li><li>${esc(t.c_ga4)}</li></ol><p class="dipnot">${esc(t.c_masaustu)}</p></div>` : "";
        return `<div class="liste">${satir(c.kurulu ? "iyi" : "kotu", c.kurulu ? t.c_kurulu : t.c_yok, c.surum || "", c.kurulu ? "" : dug("claude-kur", t.c_kur))}
          ${c.kurulu && c.yolda === false ? satir("uyari", t.c_yol_yok, t.c_yol_ac, dug("claude-yol", t.c_yol_dug)) : ""}
          ${c.kurulu ? girisSatiri : ""}</div>${adimlar}
          ${c.kurulu && c.giris ? "" : `${c.kurulu ? "" : `<p class="dipnot">${esc(t.c_aciklama)}</p>`}<p class="dipnot">${dug("kartsiz", t.c_kartsiz)}<br>${esc(t.c_kartsiz_a)}</p>`}`; } },
    // profil tek ekran (17 → 10 ekran, 8 Ekim): ad zorunlu, gerisi isteğe bağlı; Claude'un çalışma notu kurulumda dökümlerden
    // arka planda taslak olarak yazılır (kurulum.py profil), ilk toplantı sonunda /toplanti onayını sorar
    { id: "sen", simge: "sen", b: "sen_b", a: "sen_a", hazir: () => (C.ad || "").trim().length > 1,
      gir: () => { if (!C.ad && D.durum && D.durum.varsayilan_ad) C.ad = D.durum.varsayilan_ad; },
      icerik: () => `${alan("ad", t.ad, t.ad_i)}<div class="iki">${alan("rol", t.rol)}${alan("sirket", t.sirket)}</div>
        <div class="alan"><span class="etiket">${esc(t.is_alani)}</span><div class="yongalar">${t.alanlar.map((a, i) => yonga("alan", a, C.is_alani === M.tr.alanlar[i] || C.is_alani === a)).join("")}</div></div>
        <div class="iki">${alan("araclar_ek", t.araclar_tek, t.araclar_ek_i)}${alan("kisiler", t.kisiler_tek, t.kisiler_i)}</div>
        <div class="birak" data-yukle="gorusme" tabindex="0"><b>${esc(t.gor_birak)}</b> <span class="ipucu">· ${esc(t.gor_tur)}</span></div>
        ${(C.gorusmeler || []).length ? `<div class="dosyalar">${C.gorusmeler.map(d => `<div><span>${esc(d)}</span><span>✓</span></div>`).join("")}</div>` : ""}
        <p class="dipnot">${esc(t.sen_not)}</p><p class="dipnot">${dug("ornek", (C.ornek ? "✓ " : "") + t.gor_ornek)} ${dug("atla", t.sonra)}</p>` },
    { id: "proje", simge: "klasor", b: "proje_b", a: "proje_a", gir: () => { if (!C.proje && D.durum) C.proje = D.durum.proje; },
      icerik: () => `<div class="liste">${satir("iyi", C.proje || "~/Suflor", t.proje_icerik, dug("klasor-sec", t.proje_sec))}</div>` },
    { id: "kur", simge: "kur", b: "kur_b", a: "kur_a", hazir: () => { const k = D.kurDurum || {}; return k.ayar === "iyi" && k.aktarici === "iyi"; },
      gir: async () => { D.kurDurum = { ayar: "bekle", proje: "bekle", not: "bekle", aktarici: "bekle" }; ciz();
        try { D.kurDurum = await api("kur/tamamla", { cevap: C, dil: D.dil }); } catch (e) { D.kurDurum = { ...D.kurDurum, hata: String(e.message || e) }; } await durumAl(); ciz(); },
      icerik: () => { const k = D.kurDurum || {}, m = (D.durum || {}).modeller || {}, ys = (D.durum || {}).yerel_ses;
        return `<div class="liste">${satir(k.ayar || "bekle", t.k_ayar)}${satir(k.proje || "bekle", t.k_proje, C.proje || "")}${k.not === "bos" ? "" : satir(k.not || "bekle", t.k_not, k.not === "iyi" ? t.k_not_a : "")}${satir(k.aktarici || "bekle", t.k_aktarici)}
          ${satir(m.durum === "hazir" ? "iyi" : m.durum === "hata" ? "kotu" : "bekle", t.k_modeller, m.durum === "hazir" ? "" : m.durum === "hata" ? (m.tur === "baska_hesap" ? t.k_m_baska : t.k_m_hata + (m.mesaj ? " (" + m.mesaj + ")" : "")) : `%${m.yuzde || 0}`, m.durum === "hata" ? dug("modeller-yeniden", t.k_m_yeniden) : "")}
          ${k.aktarici === "iyi" && ys ? satir(ys.kurulu ? "iyi" : "uyari", t.k_ses, ys.kurulu ? t.k_ses_ok : t.k_ses_yok, ys.kurulu ? dug("ses-izni", t.k_ses_izin) : "") : ""}</div>
          ${k.hata ? `<div class="kart-not uyari">${esc(k.hata)}</div><p class="dipnot">${dug("kur-yeniden", t.k_m_yeniden)}</p>` : ""}${(k.uyarilar || []).map(u => `<div class="kart-not uyari">${esc(u)}</div>`).join("")}
          <label class="anahtar"><input type="checkbox" data-teshis ${C.teshis === true ? "checked" : ""}><span><b>${esc(t.p_anahtar)}</b><br><span class="ipucu">${esc(t.p_gider_a)} ${esc(t.p_gitmez_a)}</span></span></label>`; } },
    { id: "takvim", simge: "takvim", b: "takvim_b", a: "takvim_a", gir: takvimBekle,
      icerik: () => { const tk = (D.durum || {}).takvim || {};
        if (tk.durum !== "ok") return `<div class="liste">${satir(tk.durum === "izin_yok" ? "uyari" : "bos", t.t_izin_b, t.t_izin_a, dug("takvim-izin", t.t_izin))}</div>`;
        const tl = tk.takvimler || [], sec = new Set(C.takvim_adres || []);
        const ad = [...new Set([...(tk.adaylar || []).map(x => x.adres), ...(C.takvim_adres || [])])];
        const adres = `<div class="alan"><span class="etiket">${esc(t.t_adres)}</span>${tk.adaylar == null ? `<div class="ipucu">${esc(t.t_adres_bekle)}</div>`
          : `<div class="yongalar">${ad.map(x => yonga("adres", x, sec.has(x))).join("")}</div>`}
          <input type="text" data-adres-ek placeholder="${esc(t.t_adres_ek)}" style="margin-top:8px">${tk.adaylar != null && !sec.size ? `<div class="ipucu">${esc(t.t_adres_yok)}</div>` : ""}</div>`;
        return `${adres}${tl.length ? `<div class="alan"><span class="etiket">${esc(t.t_dogru)}</span><div class="yongalar">${tl.map(x => yonga("takvim", x.ad + " · " + x.hesap, !(C.takvim_cikar || []).includes(x.ad + " · " + x.hesap) && x.sec !== false)).join("")}</div></div>`
          : `<div class="kart-not">${esc(t.t_hesap_yok)} ${dug("internet-hesaplari", t.t_hesap_ekle)}</div>`}
          <div class="alan"><span class="etiket">${esc(t.t_bugun)}</span><div class="liste">${(tk.olaylar || []).length ? tk.olaylar.map(o => satir("iyi", o.baslik, `${o.saat}–${o.bitis}${o.platform ? " · " + o.platform : ""}`)).join("") : satir("iyi", t.t_bos)}</div></div>`; } },
    { id: "eklenti", simge: "eklenti", b: "ek_b", a: "ek_a", hazir: () => ((D.durum || {}).eklenti || {}).bagli, gir: () => eklentiBekle(),
      icerik: () => { const e = (D.durum || {}).eklenti || {};
        return `<ol class="adimlar"><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e1)}<div class="eylem">${dug("chrome-eklentiler", t.e1d)}</div></div></li>
          <li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e2)}<div class="eylem">${dug("eklenti-klasoru", t.e2d)}</div></div></li><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e3)}</div></li></ol>
          <div class="liste">${satir(e.bagli ? "iyi" : "bekle", e.bagli ? t.e_bagli : t.e_bekle, e.surum ? "v" + e.surum : "")}</div>
          ${!e.bagli && e.coklu ? `<div class="kart-not uyari">${esc(t.e_coklu + (e.alan || ""))}</div>` : ""}
          ${e.bagli ? "" : `<p class="dipnot">${esc(t.e_profil)}</p><p class="dipnot">${dug("atla", t.atla)}</p>`}
          ${((D.durum || {}).mac || {}).teams_uygulama ? `<p class="dipnot">${esc(t.teams_not)}</p>` : ""}`; } },
    { id: "bitti", simge: "isaret", b: "bitti_b", a: "bitti_a", son: true },
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
  async function claudeDenetle() {  // tek yerden; aynı anda ikinci denetim başlamaz
    if (D.claudeDen) return; D.claudeDen = true; D.sonDen = Date.now(); ciz();
    try { await api("claude/denetle", {}); } catch (e) {} D.claudeDen = false; await durumAl(); ciz();
  }
  window.addEventListener("focus", () => {  // Terminal'de giriş yapıp dönünce
    const a = gorunen()[D.adim], c = (D.durum || {}).claude || {};
    if (a && a.id === "claude" && c.kurulu && !c.giris && !D.claudeDen && Date.now() - (D.sonDen || 0) > 15000) claudeDenetle();
  });
  // takvim ekranı: adaylar arka planda okunur (kurulum.py takvim_adaylari); gelince adı kullanıcının adına benzeyenler önceden seçilir
  const sadele = x => String(x || "").toLocaleLowerCase("tr").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/ı/g, "i");
  const takvimKaydet = () => api("takvim", { adresler: C.takvim_adres || [], cikar: C.takvim_cikar || [] }).catch(() => {});
  async function takvimBekle() {
    for (let i = 0; i < 30 && gorunen()[D.adim] && gorunen()[D.adim].id === "takvim"; i++) {
      await durumAl(); const tk = (D.durum || {}).takvim || {};
      if (tk.durum !== "ok" || tk.adaylar == null) { ciz(); await new Promise(r => setTimeout(r, 3000)); continue; }
      if (!C.takvim_adres) {
        const ilk = sadele((C.ad || "").trim().split(/\s+/)[0]);
        C.takvim_adres = (tk.adresler || []).length ? tk.adresler : ilk.length > 1 ? tk.adaylar.filter(x => sadele(x.ad).split(/[^a-z0-9]+/).includes(ilk) || sadele(x.adres).split("@")[0].split(/[^a-z0-9]+/).includes(ilk)).map(x => x.adres) : [];
        kaydet(); await takvimKaydet();
      }
      ciz(); break;
    }
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
      if (g === "alan") { C.is_alani = v; } else {
        const anahtar = { takvim: "takvim_cikar", adres: "takvim_adres" }[g]; const l = new Set(C[anahtar] || []);
        if (g === "adres" ? on : !on) l.add(v); else l.delete(v); C[anahtar] = [...l];
        takvimKaydet();  // takvim ekranı kurulumdan sonra: seçim ayara hemen yazılır
      }
      kaydet(); ciz(); return;
    }
    const ey = e.target.closest("[data-eylem]");
    if (ey) {
      const n = ey.dataset.eylem;
      if (n === "kartsiz") { C.kartsiz = true; kaydet(); ciz(); return; }
      if (n === "atla") { git(D.adim + 1); return; }
      if (n === "ornek") { C.ornek = !C.ornek; kaydet(); ciz(); return; }
      if (n === "claude-denetle") { await claudeDenetle(); return; }
      if (n === "kur-yeniden") { const a = gorunen()[D.adim]; if (a && a.gir) await a.gir(); return; }  // kurulum adımı başarısızsa
      if (n === "modeller-yeniden") { await api("modeller/baslat", {}).catch(() => {}); await durumAl(); ciz(); return; }
      if (n === "claude-yol") { await api("ac", { hedef: n }).catch(() => {}); await durumAl(); ciz(); return; }
      if (n === "klasor-sec") { const r = await api("klasor-sec", {}).catch(() => ({})); if (r.yol) { C.proje = r.yol; kaydet(); ciz(); } return; }
      if (n === "takvim-izin") { await api("ac", { hedef: n }).catch(() => {}); await durumAl(); ciz(); return; }
      api("ac", { hedef: n }).catch(() => {});
      return;
    }
    const bk = e.target.closest(".birak"); if (bk) dosyaSec(bk.dataset.yukle);
  });
  // teşhis anahtarı (Kuruyorum ekranı): kurulum bittiyse ayara yazılır, aktarıcı yeniden başlar (kurulum.py /api/teshis)
  document.addEventListener("change", async e => {
    if (!e.target.matches || !e.target.matches("[data-teshis]")) return;
    C.teshis = e.target.checked; kaydet(); if ((D.kurDurum || {}).ayar === "iyi") await api("teshis", { acik: C.teshis }).catch(() => {});
  });
  document.addEventListener("change", e => {
    if (!e.target.matches || !e.target.matches("[data-adres-ek]")) return;
    const v = e.target.value.trim().toLowerCase(); if (!/^[^\s@,]+@[^\s@,]+\.[^\s@,]+$/.test(v)) return;
    C.takvim_adres = [...new Set([...(C.takvim_adres || []), v])]; kaydet(); takvimKaydet(); ciz();
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
  function dosyaSec(tur) { const i = document.createElement("input"); i.type = "file"; i.multiple = true; i.accept = ".docx,.vtt,.txt,.md";
    i.onchange = () => yukle(tur, [...i.files]); i.click(); }
  async function yukle(tur, dosyalar) {
    for (const f of dosyalar) {
      try { await api(`yukle?tur=${tur}&ad=${encodeURIComponent(f.name)}`, f, true); } catch (e) { continue; }
      C.gorusmeler = [...new Set([...(C.gorusmeler || []), f.name])];
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
