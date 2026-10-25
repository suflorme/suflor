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
      p_veri: "Suflor.me'yi geliştirmek için yalnız sayılar gönderilir (kullanım, hız, hata); konuşmaların, metinlerin ve adların hiçbiri Mac'inden çıkmaz.",
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
      claude_b: "Yapay zekâyı bağlayalım", claude_a: "Konuş'taki cevapları, kartları ve özetleri bir yapay zekâ yazar. Üç yoldan birini seç; sonra panodaki ⚙ Ayarlar'dan iş başına değiştirebilirsin.",
      yz_claude: "Claude Code (önerilen)", yz_claude_a: "Claude aboneliğinle. Toplantıdaki kartlar ve özet bununla çalışır.",
      yz_anahtar: "API anahtarı", yz_anahtar_a: "Gemini ya da OpenAI uyumlu bir hizmet; kullandıkça ücretlendirilir.",
      yz_yerel: "Bu Mac'te yerel model", yz_yerel_a: "Ollama ile; internet ve ücret gerekmez. Türkçe aramada zayıf, yedek olarak önerilir.",
      yz_gizlilik: "Claude dışında bir sağlayıcı seçersen metin bağlamı (döküm, not, belge parçası) o sağlayıcıya gider, ses gitmez; yerel model seçersen metin de Mac'ten çıkmaz.",
      yz_toplanti: "Toplantı sırasında kart ve özet yazan oturum şimdilik yalnız Claude Code'la çalışır. Claude Code yoksa döküm, pano ve Konuş çalışır.",
      yz_gemini: "Gemini (Google)", yz_ozel: "OpenAI uyumlu başka hizmet",
      yz_gemini_al: "Anahtarı Google AI Studio'dan alırsın (aistudio.google.com → Get API key). Ücretli katman önerilir: ücretsiz katmanda Google gönderilen metni ürünlerini geliştirmek için kullanabiliyor.",
      yz_adres: "Adres", yz_adres_i: "Örnek: https://api.openai.com/v1", yz_model: "Model adı", yz_model_i: "Hizmetin model listesindeki ad",
      yz_anahtar_alan: "API anahtarı", yz_anahtar_ph: "Buraya yapıştır", yz_anahtar_i: "Anahtar yalnız macOS Anahtar Zinciri'ne yazılır; Suflor.me dosyalarında yalnız öğenin adı durur.",
      yz_kaydet: "Kaydet ve dene", yz_deneniyor: "Deneniyor…", yz_an_var: "Anahtar Anahtar Zinciri'nde", yz_an_yok: "Anahtar girilmedi",
      yz_an_iyi: "Hizmet anahtarı kabul etti", yz_an_anahtar: "Hizmet anahtarı kabul etmedi; anahtarı yeniden yapıştır.", yz_an_ag: "Hizmete ulaşılamadı; internet bağlantına ya da adrese bak.",
      yz_an_bicim: "Anahtar biçimi tanınmadı (harf, rakam, - _ . ; en az 16 karakter).", yz_an_zincir: "Anahtar Zinciri'ne yazılamadı.", yz_an_adres: "Adres https:// ile başlamalı.", yz_an_model: "Model adını yaz.",
      yz_ol_kur: "İndir ve kur", yz_ol_boyut: "İndirme ~{gb} GB: Ollama aracı (~{mb} MB, resmî sürüm, imzası denetlenir) ve qwen3.5 4B modeli. Mac açılışında kendiliğinden çalışmaz; Suflor.me gerekince açar.",
      yz_ol_uyari: "Yerel model kısa sorularda işe yarar ama Türkçe belgelerde aramayı çoğu zaman yanlış yapıyor (denemede 4 sorudan 0 doğru). Yedek olarak önerilir; daha iyi sonuç için Claude Code ya da bir API anahtarı.",
      yz_ol_iniyor: "Yerel model iniyor", yz_ol_hazir: "Yerel model hazır", yz_ol_yok: "Yerel model kurulu değil", yz_ol_hata: "Yerel model kurulamadı", yz_ol_yeniden: "Yeniden dene",
      yz_ol_baska: "Ortak klasöre yazılamıyor (başka macOS hesabı kurmuş); yerel modeli o hesapta kur.", yz_ol_bekle: "İndirme arka planda sürer; kuruluma devam edebilirsin.",
      yz_ol_bellek: "Bu Mac'te 16 GB'tan az bellek var; yerel model toplantıda konuşma tanımayla birlikte Mac'i yavaşlatabilir.",
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
      as_b: "Asistanına bir ad koy", as_a: "Toplantıda ve toplantı dışında seninle konuşan, sorularını cevaplayan asistan. Ona adıyla seslenirsin: “Defne, yarın neler var?” Adı ve ayarları yalnız bu Mac'te kalır.",
      as_ad: "Adı", as_ad_ph: "örneğin Defne", as_ad_i: "Kısa, kolay söylenen bir ad seç; iki-üç heceli ad, konuşma tanımanın en kolay yakaladığıdır.",
      as_bicim: "Sana nasıl hitap etsin?", as_siz: "siz", as_sen: "sen", as_tarz: "Tarzı", as_olculu: "Ölçülü", as_rahat: "Rahat ve esprili",
      as_ses: "Sesi", as_mac: "Mac'in Türkçe sesi", as_kadin: "Kadın sesi", as_erkek: "Erkek sesi", as_dinle: "Dinle", as_okuyor: "Okuyor…",
      as_pk_indir: "Kadın ve erkek ses bu Mac'e indirilir (~1,3 GB, birkaç dakika); seçince başlar. İstemezsen Mac'in sesi kalır.",
      as_pk_iniyor: "Doğal Türkçe ses indiriliyor", as_pk_bekle: "Bitene kadar asistan ve Dinle Mac sesiyle okur; kurulumun devam edebilir.",
      as_pk_hata: "Doğal ses kurulamadı; asistan şimdilik Mac sesiyle konuşur.", as_pk_yeniden: "Yeniden dene",
      as_pk_atif: "Ses modeli: wite-tech/pocket-tts-turkish (CC-BY-4.0) · Pocket TTS, Kyutai (MIT). Hugging Face ve PyPI'dan indirilir; ses ve metin Mac'ten çıkmaz.",
      as_iki: "Toplantı dışında ayrı bir asistan ister misin?", as_iki_a: "Örneğin toplantıda ölçülü bir asistan, kendi başınayken daha rahat konuşan ikinci bir asistan. Toplantıda öbürüne adıyla seslenirsen o cevaplar.",
      as_toplanti: "Toplantıda", as_disi: "Toplantı dışında", as_atla_a: "Atlarsan asistanın adı Suflor olur; sonra kurulumu yeniden açarak ad koyabilirsin.",
      as_ayni: "İki asistanın adı farklı olmalı.", as_suflor: "Suflor adı uygulamanın kendisine ayrıldı; başka bir ad seç.", as_gecersiz: "Ad 2–24 harf olmalı; rakam ve işaret kullanma.",
      as_var: "Bu asistan bu Mac'te zaten var; yalnız burada değiştirdiğin hitap, tarz ve ses dosyasına yazılır (önce yedeği alınır).",
      as_tarz_elle: "Bu asistanın tonu kişilik dosyasında elle yazılmış; burada değiştirilmez. Değiştirmek için dosyayı düzenle.",
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
      t_eposta: "Brifingi ya da özeti e-postayla gönderirken taslak nerede açılsın?", t_e_oto: "Kendin seç", t_e_gmail: "Gmail", t_e_outlook: "Outlook (web)", t_e_mailto: "Mac'in posta uygulaması",
      t_e_oto_a: "Takvim adresine ve toplantılarına bakıp ben seçerim (Gmail adresi → Gmail, Teams toplantıları → Outlook).", t_e_adres: "Gönderen adresin (\"kendime\" de buraya gider; Gmail'de taslak bu hesapla açılır)", t_e_adres_ph: "ör. Gmail adresin — boşsa takvim adresin",
      t_bugun: "Bugün gördüklerim", t_bos: "Bugün başka toplantın yok.", t_dogru: "Takvimlerin bunlar mı? İzlenmesini istemediklerinin işaretini kaldır.", t_adres: "Hangi adresler senin? Yalnız bu adreslerin davetli ya da düzenleyen olduğu toplantıları gösteririm; Takvim'e eklenmiş başkalarının takvimleri listeye girmez.",
      t_adres_bekle: "Takvimdeki adresleri okuyorum…", t_adres_ek: "Listede olmayan bir adresin", t_adres_yok: "Adres seçmezsen macOS'un seni tanıdığı yere bakarım; Takvim'e başkalarının takvimi eklenmişse onların toplantıları da görünebilir.",
                                    ek_b: "Chrome eklentisini ekle", ek_a: "Eklenti Teams sayfasından sesi ve altyazıyı alır, kartları ekranın köşesinde gösterir.",
      e1: "Chrome'un eklenti sayfasını aç ve sağ üstte Geliştirici modu'nu aç.", e1d: "Eklenti sayfasını aç",
      e2: "\"Paketlenmemiş öğe yükle\"ye bas ve Suflor.me klasörünü seç: açılan pencerede Command + Shift + G'ye bas, bu yolu yapıştır, Enter, sonra Seç.", e2d: "Klasörü Finder'da göster", e2k: "Yolu kopyala", e2k_ok: "Kopyalandı",
      e3: "Araç çubuğundaki yapboz simgesinden Suflor.me'yi sabitle.",
      e_bekle: "Eklentiyi bekliyorum…", e_bagli: "Eklenti bağlandı",
      e_coklu: "Bu Mac'te başka bir hesabın Suflor.me'si de çalışıyor. Chrome'da Suflor.me simgesine tıkla ve bu hesabın alanını seç: ", e_profil: "Eklentiyi Teams'e girdiğin Chrome profiline ekle; birden fazla Chrome profilin varsa doğru pencerede olduğuna bak.",
      bitti_b: "Hazırsın",
      // proje hazırlığı (T6, v0.76.0)
      hz_tara_b: "Projeni tanıyorum", hz_tara_a: "Klasöründeki dosyalara bakıyorum. Dizine girmesini istemediklerini işaretle; dosyalarına dokunulmaz, hiçbir yere gönderilmez.",
      hz_taraniyor: "Klasörü tarıyorum…", hz_bos: "Klasör şimdilik boş. Belge ekledikçe ve toplantı yaptıkça Suflor.me kendiliğinden dizinler.",
      hz_dosya: "dosya", hz_kopya: "Birebir kopya", hz_kopya_a: "Her biri dizine bir kez girer", hz_surum: "Eski sürüm", hz_surum_a: "Aramada en yenisi öne çıkar",
      hz_okunamaz: "Açılamayan", hz_okunamaz_a: "Parolalı, bozuk ya da boş", hz_ikincil: "Çıktı ya da dışa aktarım", hz_ikincil_a: "Aramada asıl belgenin arkasında kalır",
      hz_klasorler: "Dizine girecek klasörler", hz_klasor_i: "Dokunarak çıkar ya da geri al. Yedek, arşiv ve kişisel klasörleri çıkarabilirsin.",
      hz_gizli: "Adından gizli görünen dosyalar — dizine girmez", hz_dahil_et: "Dizine al", hz_dahil: "Senin isteğinle dizinde", hz_geri: "Geri al",
      hz_asil_b: "Çıktı sayılanlar", hz_asil_i: "Asıl belgeyse işaretle; aramada öne çıkar.", hz_asil_say: "Asıl say", hz_asil: "Asıl sayılıyor", hz_daha: "daha",
      hz_onay_b: "Ne kadar sürecek", hz_onay_a: "Belgelerin bu Mac'te metne çevrilir ve dizinlenir. Arka planda sürer; bu sırada kuruluma devam edebilirsin.",
      hz_cevir: "Metne çevrilecek", hz_cevir_yok: "Metne çevrilecek dosya yok", hz_cevir_model: "Çevirme modelleri henüz inmedi; inince arka planda çevrilir",
      hz_dizin: "Dizinlenecek", hz_parca: "parça", hz_sure: "Tahmini süre", hz_dk: "dk", hz_az: "1 dakikadan az",
      hz_kart_cikar: "Proje kartını da hazırla (Claude)", hz_kart_ac: "{n} belge · yaklaşık {d} dk · yaklaşık {u} $ karşılığı Claude kullanımı. Belge metni yalnız Claude'a gider; şifre ve hesap numarası içeren parçalar gitmez.",
      hz_kart_claude: "Claude Code ya da bir API anahtarı bağlı olmadığı için kart şimdi hazırlanamaz; sonra panodaki ⚙ Ayarlar → Proje'den.", hz_baslat: "Başlat",
      hz_ilerleme_b: "Hazırlanıyor", hz_ilerleme_a: "Arka planda sürüyor; bu pencereyi kapatsan da biter.",
      hz_e_tara: "Tarama", hz_e_cevir: "Metne çevirme", hz_e_dizin: "Dizinleme", hz_e_gomme: "Anlama göre arama dizini", hz_e_kart: "Proje kartı",
      hz_durdu: "Durdu: ", hz_hata: "Hata: ", hz_bitti_s: "Bitti", hz_kurulu_degil: "Kurulu değil (sözcükle arama çalışır)", hz_toplanti_not: "Toplantı başlarsa durur, sonra kaldığı yerden sürer.",
      hz_kart_b: "Proje kartı", hz_kart_a: "Belgelerinden çıkardıklarım. Yanlış satırın işaretini kaldır; seçtiğin terimleri konuşma tanıma doğru yazar. Onaylayınca toplantıda bunu kullanırım.",
      hz_kart_bekle: "Proje kartı hazırlanıyor…", hz_kart_yok: "Proje kartı hazırlanmadı. Sonra panodaki ⚙ Ayarlar → Proje'den hazırlayabilirsin.",
      hz_ozet: "Özet", hz_kisiler: "Kişiler", hz_kurumlar: "Kurumlar", hz_kararlar: "Kararlar", hz_tarihler: "Tarihler", hz_isler: "Açık işler", hz_sozluk: "Sözlüğe eklenecek terimler",
      hz_sozluk_i: "En çok {n} terim; konuşma tanıma bunları doğru yazar.", hz_celiski: "farklı tarihler", hz_kaynak: "kaynak", hz_onayla: "Onayla", hz_onaylandi: "Onaylandı",
      hz_vt: "Kişiler, kararlar ve işler kayıt veritabanından gelir; burada yalnız özet ve sözlük var.", hz_sonra: "Sonra onaylarım",
      hz_bitti_hazir: "Proje hazır: {b} belge, {p} parça, {c} dosya metne çevrildi.", hz_bitti_hazir0: "Proje hazır: {b} belge, {p} parça.", hz_bitti_tablo: "Tablolar: {n} sayfa, {r} satır proje veritabanında; toplam ve sayı sorularını asistan buradan hesaplar.", hz_bitti_suruyor: "Proje hazırlığı arka planda sürüyor; bitince Suflor.me kendiliğinden kullanır.",
      hz_bitti_b: "Proje hazırlığı tamam", hz_bitti_a: "Suflor.me toplantıda bu dizini ve proje kartını kullanır.", hz_bitir: "Panoya dön",
                                     },
    en: {
      sen_a: "So the cards are written from your point of view. Only your name is required; the rest can come now or later. This stays on this Mac.",
      araclar_tek: "Tools you use often (optional)", araclar_ek_i: "Separate with commas: e.g. Jira, Salesforce",
      kisiler_tek: "People you meet often (optional)", kisiler_i: "So speech recognition spells their names right. Separate with commas.",
      gor_birak: "Drop Teams transcripts here (optional)",
      sen_not: "Transcripts are the fastest way for Claude to get to know you: during setup it drafts a working note for you, and you approve it after your first meeting. Files are copied into your project folder and never sent anywhere.",
      sonra: "Later",
      p_veri: "To improve Suflor.me, only numbers are sent (usage, speed, errors); none of your conversations, texts or names leave your Mac.",
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
      claude_b: "Connect an AI", claude_a: "An AI writes the Talk answers, cards and summaries. Pick one of three ways; later you can change it per task in ⚙ Settings on the panel.",
      yz_claude: "Claude Code (recommended)", yz_claude_a: "With your Claude subscription. Cards and summaries during meetings use it.",
      yz_anahtar: "API key", yz_anahtar_a: "Gemini or an OpenAI-compatible service; billed by usage.",
      yz_yerel: "Local model on this Mac", yz_yerel_a: "With Ollama; no internet or fees. Weak at Turkish search, recommended as a fallback.",
      yz_gizlilik: "If you pick a provider other than Claude, text context (transcript, notes, document passages) goes to that provider, audio doesn't; with a local model, text doesn't leave your Mac either.",
      yz_toplanti: "For now the session that writes cards and summaries during meetings works only with Claude Code. Without Claude Code, transcription, the panel and Talk work.",
      yz_gemini: "Gemini (Google)", yz_ozel: "Other OpenAI-compatible service",
      yz_gemini_al: "Get a key from Google AI Studio (aistudio.google.com → Get API key). The paid tier is recommended: on the free tier Google may use the text sent to improve its products.",
      yz_adres: "Address", yz_adres_i: "Example: https://api.openai.com/v1", yz_model: "Model name", yz_model_i: "The name in the service's model list",
      yz_anahtar_alan: "API key", yz_anahtar_ph: "Paste here", yz_anahtar_i: "The key is written only to the macOS Keychain; Suflor.me files keep only the item's name.",
      yz_kaydet: "Save and test", yz_deneniyor: "Testing…", yz_an_var: "Key is in the Keychain", yz_an_yok: "No key entered",
      yz_an_iyi: "The service accepted the key", yz_an_anahtar: "The service rejected the key; paste it again.", yz_an_ag: "Couldn't reach the service; check your internet connection or the address.",
      yz_an_bicim: "Key format not recognised (letters, digits, - _ . ; at least 16 characters).", yz_an_zincir: "Couldn't write to the Keychain.", yz_an_adres: "The address must start with https://.", yz_an_model: "Enter the model name.",
      yz_ol_kur: "Download and install", yz_ol_boyut: "Download ~{gb} GB: the Ollama tool (~{mb} MB, official release, signature checked) and the qwen3.5 4B model. It doesn't start at login; Suflor.me starts it when needed.",
      yz_ol_uyari: "The local model handles short questions but often searches Turkish documents wrongly (0 of 4 right in our test). Recommended as a fallback; for better results use Claude Code or an API key.",
      yz_ol_iniyor: "Local model downloading", yz_ol_hazir: "Local model ready", yz_ol_yok: "Local model not installed", yz_ol_hata: "Local model couldn't be installed", yz_ol_yeniden: "Try again",
      yz_ol_baska: "Can't write to the shared folder (another macOS account installed it); install the local model from that account.", yz_ol_bekle: "The download continues in the background; you can go on with setup.",
      yz_ol_bellek: "This Mac has less than 16 GB of memory; during meetings the local model plus speech recognition may slow it down.",
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
      as_b: "Name your assistant", as_a: "The assistant that talks with you in and outside meetings and answers your questions. You call it by name: “Robin, what's on tomorrow?” Its name and settings stay on this Mac.",
      as_ad: "Name", as_ad_ph: "e.g. Robin", as_ad_i: "Pick a short name that's easy to say; two or three syllables are easiest for speech recognition to catch.",
      as_bicim: "How should it address you?", as_siz: "formal", as_sen: "informal", as_tarz: "Style", as_olculu: "Measured", as_rahat: "Relaxed and witty",
      as_ses: "Voice", as_mac: "Mac voice", as_kadin: "Female voice", as_erkek: "Male voice", as_dinle: "Listen", as_okuyor: "Speaking…",
      as_pk_indir: "The female and male voices are downloaded to this Mac (~1.3 GB, a few minutes) when you pick one. Otherwise the Mac voice stays.",
      as_pk_iniyor: "Downloading the natural Turkish voice", as_pk_bekle: "Until it finishes, the assistant and Listen use the Mac voice; you can continue setup.",
      as_pk_hata: "The natural voice could not be installed; the assistant uses the Mac voice for now.", as_pk_yeniden: "Try again",
      as_pk_atif: "Voice model: wite-tech/pocket-tts-turkish (CC-BY-4.0) · Pocket TTS, Kyutai (MIT). Downloaded from Hugging Face and PyPI; voice and text stay on this Mac.",
      as_iki: "Do you want a separate assistant outside meetings?", as_iki_a: "For example, a measured assistant in meetings and a more relaxed one when you're on your own. In a meeting, call the other one by name and it answers.",
      as_toplanti: "In meetings", as_disi: "Outside meetings", as_atla_a: "If you skip, the assistant is called Suflor; you can name it later by opening setup again.",
      as_ayni: "The two assistants need different names.", as_suflor: "Suflor is the app's own name; pick another.", as_gecersiz: "Use 2–24 letters; no digits or symbols.",
      as_var: "This assistant already exists on this Mac; only the form of address, style and voice you change here are written to its file (after a backup).",
      as_tarz_elle: "This assistant's tone is hand-written in its persona file, so it can't be changed here. Edit the file to change it.",
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
      t_eposta: "When you email a briefing or summary, where should the draft open?", t_e_oto: "You choose", t_e_gmail: "Gmail", t_e_outlook: "Outlook (web)", t_e_mailto: "Mac's mail app",
      t_e_oto_a: "I'll pick from your calendar address and meetings (Gmail address → Gmail, Teams meetings → Outlook).", t_e_adres: "Your sending address (\"to myself\" goes here too; in Gmail the draft opens with this account)", t_e_adres_ph: "e.g. your Gmail address — empty means your calendar address",
      t_bugun: "What I see today", t_bos: "No more meetings today.", t_dogru: "Are these your calendars? Untick any you don't want followed.", t_adres: "Which addresses are yours? I only show meetings where one of them is invited or organizes; other people's calendars added to Calendar stay out.",
      t_adres_bekle: "Reading the addresses in your calendar…", t_adres_ek: "Another address of yours", t_adres_yok: "With no address selected I go by who macOS thinks you are; if other people's calendars are added, their meetings may show too.",
                                    ek_b: "Add the Chrome extension", ek_a: "The extension takes sound and captions from the Teams page and shows the cards in a corner of the screen.",
      e1: "Open Chrome's extensions page and switch on Developer mode at the top right.", e1d: "Open extensions page",
      e2: "Click \"Load unpacked\" and choose the Suflor.me folder: in the window press Command + Shift + G, paste this path, press Enter, then Select.", e2d: "Show the folder in Finder", e2k: "Copy path", e2k_ok: "Copied",
      e3: "Pin Suflor.me from the puzzle icon in the toolbar.",
      e_bekle: "Waiting for the extension…", e_bagli: "Extension connected",
      e_coklu: "Another account's Suflor.me is also running on this Mac. Click the Suflor.me icon in Chrome and pick this account's workspace: ", e_profil: "Add the extension to the Chrome profile you use for Teams; if you have several profiles, make sure you're in the right window.",
      bitti_b: "You're all set",
      hz_tara_b: "Getting to know your project", hz_tara_a: "I'm looking at the files in your folder. Mark anything you don't want indexed; your files aren't changed or sent anywhere.",
      hz_taraniyor: "Scanning the folder…", hz_bos: "The folder is empty for now. As you add documents and hold meetings, Suflor.me indexes them by itself.",
      hz_dosya: "files", hz_kopya: "Exact copies", hz_kopya_a: "Each is indexed once", hz_surum: "Older versions", hz_surum_a: "Search puts the newest first",
      hz_okunamaz: "Can't be opened", hz_okunamaz_a: "Password-protected, damaged or empty", hz_ikincil: "Outputs or exports", hz_ikincil_a: "Search ranks them behind the original",
      hz_klasorler: "Folders to index", hz_klasor_i: "Tap to leave one out or bring it back. You can leave out backups, archives and personal folders.",
      hz_gizli: "Files that look private by name — not indexed", hz_dahil_et: "Index it", hz_dahil: "Indexed at your request", hz_geri: "Undo",
      hz_asil_b: "Counted as outputs", hz_asil_i: "Mark it if it's an original document; search will rank it first.", hz_asil_say: "It's an original", hz_asil: "Counted as original", hz_daha: "more",
      hz_onay_b: "How long it will take", hz_onay_a: "Your documents are converted to text and indexed on this Mac. It runs in the background; you can keep setting up meanwhile.",
      hz_cevir: "To convert to text", hz_cevir_yok: "Nothing needs converting", hz_cevir_model: "Conversion models haven't downloaded yet; files are converted in the background once they do",
      hz_dizin: "To index", hz_parca: "passages", hz_sure: "Estimated time", hz_dk: "min", hz_az: "under a minute",
      hz_kart_cikar: "Also prepare the project card (Claude)", hz_kart_ac: "{n} documents · about {d} min · about ${u} worth of Claude usage. Document text goes only to Claude; passages with passwords or account numbers don't.",
      hz_kart_claude: "Neither Claude Code nor an API key is connected, so the card can't be prepared now; do it later from ⚙ Settings → Project on the panel.", hz_baslat: "Start",
      hz_ilerleme_b: "Preparing", hz_ilerleme_a: "It runs in the background; it finishes even if you close this window.",
      hz_e_tara: "Scan", hz_e_cevir: "Converting to text", hz_e_dizin: "Indexing", hz_e_gomme: "Search-by-meaning index", hz_e_kart: "Project card",
      hz_durdu: "Paused: ", hz_hata: "Error: ", hz_bitti_s: "Done", hz_kurulu_degil: "Not installed (keyword search works)", hz_toplanti_not: "It pauses if a meeting starts and resumes later.",
      hz_kart_b: "Project card", hz_kart_a: "What I found in your documents. Untick anything wrong; terms you select will be spelled right by speech recognition. Once you approve, I use this in meetings.",
      hz_kart_bekle: "Preparing the project card…", hz_kart_yok: "The project card wasn't prepared. You can do it later from ⚙ Settings → Project on the panel.",
      hz_ozet: "Summary", hz_kisiler: "People", hz_kurumlar: "Organisations", hz_kararlar: "Decisions", hz_tarihler: "Dates", hz_isler: "Open tasks", hz_sozluk: "Terms to add to the glossary",
      hz_sozluk_i: "Up to {n} terms; speech recognition will spell them right.", hz_celiski: "conflicting dates", hz_kaynak: "source", hz_onayla: "Approve", hz_onaylandi: "Approved",
      hz_vt: "People, decisions and tasks come from the records database; only the summary and glossary are here.", hz_sonra: "Approve later",
      hz_bitti_hazir: "Project ready: {b} documents, {p} passages, {c} files converted to text.", hz_bitti_hazir0: "Project ready: {b} documents, {p} passages.", hz_bitti_tablo: "Tables: {n} sheets, {r} rows in the project database; the assistant works out totals and counts from here.", hz_bitti_suruyor: "Project preparation is still running in the background; Suflor.me uses it as soon as it's done.",
      hz_bitti_b: "Project preparation done", hz_bitti_a: "Suflor.me uses this index and the project card in meetings.", hz_bitir: "Back to the panel",
                                     },
  };
  // ---------- simgeler (çizgi, currentColor) ----------
  const S = {
    isaret: `<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="15" fill="var(--sahne)"/><g transform="translate(0 -3.3)"><path fill="var(--krem)" d="M23.50 37.60A7.60 7.60 0 1 1 31.10 30.38C31.48 39.50 26.16 45.58 18.56 48.24C23.65 44.44 25.17 40.79 23.50 37.60Z"/><path fill="var(--pirinc)" d="M42.50 37.60A7.60 7.60 0 1 1 50.10 30.38C50.48 39.50 45.16 45.58 37.56 48.24C42.65 44.44 44.17 40.79 42.50 37.60Z"/></g></svg>`,
    mac: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="12" y="14" width="40" height="27" rx="3"/><path d="M6 46h52l-3 4H9z"/><path d="M27 46h10" stroke-linecap="round"/></svg>`,
    claude: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M32 12v40M12 32h40M18 18l28 28M46 18 18 46"/><circle cx="32" cy="32" r="6" fill="var(--zemin)"/></svg>`,
    asistan: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="26" cy="26" r="9"/><path d="M10 51c2.3-8.5 8.4-13 16-13s13.7 4.5 16 13"/><path d="M44 20c2.5 2.2 2.5 9.8 0 12M50 15c5 4.5 5 17.5 0 22"/></svg>`,
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
  const kaydet = () => { kayitSira = kayitSira.then(() => api("kaydet", { dil: D.dil, adim: (D.durum || {}).mod === "hazirlik" ? D.kayitAdim : D.adim, adim_id: (D.durum || {}).mod === "hazirlik" ? D.kayitAdimId : ((gorunen()[D.adim] || {}).id), cevap: D.cevap })).catch(() => {}); return kayitSira; };  // hazırlık kipinde kurulumun kaldığı adım korunur
  async function durumAl() { try { D.durum = await api("durum"); } catch (e) { D.durum = D.durum || {}; } indirmeGoster(); if (C.asistan) pkGoster(); return D.durum; }

  // örnek veriler (önizleme)
  function ornek(yol) {
    const d = {
      mac: { islemci: "Apple M3", arm: true, macos: "15.1", macos_ok: true, bellek_gb: 16, disk_gb: 84, python: "3.9.6", chrome: true, teams_uygulama: true },
      claude: { kurulu: true, surum: "2.1.4", giris: true },
      beyin: { secim: "claude-code", gemini: false, ozel: { adres: "", model: "", anahtar: false }, ollama: { durum: "yok", yuzde: 0 }, ollama_gb: 3.3, ollama_mb: 181, dene: {} },
      modeller: { durum: "iniyor", yuzde: 38 }, eklenti: { bagli: false }, kod: "~/Suflor.me",
      proje: "~/Suflor", varsayilan_ad: "Ayşe Yılmaz", asistan: { pocket: true },
      takvim: { durum: "ok", takvimler: [{ ad: "İş", hesap: "Exchange", sec: true }, { ad: "Kişisel", hesap: "iCloud", sec: true }, { ad: "Türkiye tatilleri", hesap: "iCloud", sec: false }],
        adaylar: [["ayse", "Ayşe Yılmaz", 40], ["ekip", null, 12], ["ayse.yilmaz", null, 3]].map(([k, ad, sayi]) => ({ adres: k + "@" + "ornek.test", ad, sayi })), adresler: null,  // uydurma adresler
        olaylar: [{ saat: "14:00", bitis: "14:45", baslik: "Bütçe görüşmesi", platform: "teams" }, { saat: "16:30", bitis: "17:00", baslik: "Haftalık ekip", platform: "teams" }] },
      kur: { ayar: "iyi", proje: "iyi", not: "iyi", aktarici: "bekle", modeller: "bekle" },
    };
    if (yol === "durum") return Promise.resolve(d);
    if (yol === "hazirlik") return Promise.resolve({ bos: false, tara_suruyor: false, is: { evre: "cevir", calisiyor: true, kart_istendi: true, adim: { cevir: { n: 12, toplam: 43 } } },
      tarama: { t: Date.now() / 1000, sayilar: { dosya: 412, boyut: 3.2e9, tur: { belge: 180, goruntu: 120, tablo: 60 }, kopya: 9, eski_surum: 14, okunamayan: 2, kaynak_turu: { asil: 380, turetilmis: 20, disa_aktarim: 12 } },
        klasorler: [{ ad: "belgeler", dosya: 210, haric: false }, { ad: "gorusmeler", dosya: 80, haric: false }, { ad: "kisisel", dosya: 0, haric: true }], haric: [{ yol: "belgeler/sifreler.xlsx", neden: "ad: sifre" }], dahil: [], kaynak_turu: [], asil: [] },
      tahmin: { cevir: { ".pdf": 30, ".png": 13 }, cevir_n: 43, parca_yeni: 1800, gomme_n: 1800, kart_belge: 120, kart_sn: 540, kart_usd: 6, sn: 300, cevirme_kurulu: true } });
    return Promise.resolve({ ok: true, ...d });
  }

  // ---------- adımlar ----------
  const satir = (dur, ad, ac, eylem = "") => `<div class="satir"><span class="durum ${dur}">${dur === "bekle" ? "" : S[dur] || ""}</span><div><div class="ad">${esc(ad)}</div>${ac ? `<div class="ac">${esc(ac)}</div>` : ""}</div><div class="eylem">${eylem}</div></div>`;
  const dug = (id, yazi) => `<button class="ikincil-dug" type="button" data-eylem="${id}">${esc(yazi)}</button>`;
  // e-posta bloğu (takvim ekranı; takvim izni olmasa da gösterilir): değer ↔ görünen ad ayrı
  const epostaBlok = () => { const tk = (D.durum || {}).takvim || {}, sec = C.eposta != null ? C.eposta : (tk.eposta || "");
    return `<div class="alan"><span class="etiket">${esc(t.t_eposta)}</span><div class="yongalar">${[["", t.t_e_oto], ["gmail", t.t_e_gmail], ["outlook", t.t_e_outlook], ["mailto", t.t_e_mailto]]
      .map(([v, ad]) => `<button class="yonga" type="button" data-grup="eposta" data-deger="${esc(v)}" aria-pressed="${sec === v}">${esc(ad)}</button>`).join("")}</div>
      ${sec ? "" : `<div class="ipucu">${esc(t.t_e_oto_a)}</div>`}
      <span class="etiket" style="margin-top:10px">${esc(t.t_e_adres)}</span><input type="text" inputmode="email" autocomplete="email" data-eposta-adres value="${esc(C.eposta_adres != null ? C.eposta_adres : (tk.eposta_adres || ""))}" placeholder="${esc(t.t_e_adres_ph)}"></div>`; };
  const epostaKaydet = () => api("eposta", { eposta: C.eposta || "", eposta_adres: C.eposta_adres || "" }).catch(() => {});
  const yonga = (grup, deger, secili) => `<button class="yonga" type="button" data-grup="${grup}" data-deger="${esc(deger)}" aria-pressed="${!!secili}">${esc(deger)}</button>`;
  const C = D.cevap;
  const alan = (id, etiket, ipucu = "", tur = "text") => `<div class="alan"><label for="${id}">${esc(etiket)}</label>${tur === "textarea"
    ? `<textarea id="${id}" data-cevap="${id}">${esc(D.cevap[id] || "")}</textarea>` : `<input type="text" id="${id}" data-cevap="${id}" value="${esc(D.cevap[id] || "")}">`}${ipucu ? `<div class="ipucu">${esc(ipucu)}</div>` : ""}</div>`;


  // ---------- proje hazırlığı (T6, v0.76.0): B tarama · C süre/onay · D ilerleme · E proje kartı · F bitti içinde ----------
  // kurulum.py /api/hazirlik* → hazirlik.py. Panodaki "Projeyi yeniden hazırla" sihirbazı mod=hazirlik ile açar: yalnız bu ekranlar.
  const HZ_ADIM = ["hz_tara", "hz_onay", "hz_ilerleme", "hz_kart", "bitti"];
  const hzMod = () => ((D.durum || {}).mod === "hazirlik");
  const H = () => D.hz || {};
  const mb = b => b >= 1e9 ? (b / 1e9).toFixed(1) + " GB" : b < 1e6 ? "< 1 MB" : Math.round(b / 1e6) + " MB";
  const TUR_AD = { tr: { belge: "belge", sunum: "sunum", tablo: "tablo", veri: "veri", web: "web", goruntu: "görüntü", eposta: "e-posta", ses: "ses", video: "video", arsiv: "arşiv", kod: "kod", diger: "diğer" },
    en: { belge: "documents", sunum: "presentations", tablo: "spreadsheets", veri: "data", web: "web", goruntu: "images", eposta: "email", ses: "audio", video: "video", arsiv: "archives", kod: "code", diger: "other" } };
  const dk = sn => sn < 60 ? t.hz_az : "~" + Math.round(sn / 60) + " " + t.hz_dk;
  const tf = (m, o) => m.replace(/\{(\w+)\}/g, (_, k) => o[k] ?? "");
  async function hzAl() { try { D.hz = await api("hazirlik"); } catch (e) { D.hz = D.hz || {}; } return D.hz; }
  async function hzBekle(id, kosul, ms = 2000) {  // ekran açıkken yokla; kosul() doğru olunca biter
    while (gorunen()[D.adim] && gorunen()[D.adim].id === id) { await hzAl(); ciz(); if (kosul && kosul()) break; await new Promise(r => setTimeout(r, ms)); }
  }
  const hzBos = () => H().bos === true;
  const hzKartIstendi = () => !!((H().is || {}).kart_istendi);
  const hzIsDurum = () => (H().is || {});
  const hzKartVarsayilan = () => { if (C.hz_kart == null) C.hz_kart = kartYz(); };
  const isaretle = async (tur, yol, deger) => { await api("hazirlik/isaret", { tur, yol, deger }).catch(() => {}); D.hz = { ...H(), tara_suruyor: true }; ciz(); hzBekle("hz_tara", () => H().tarama && !H().tara_suruyor, 1500); };
  function kartSatir(bol, i, x, metin, ek) {
    const sec = !((D.kartCikar || {})[bol] || new Set()).has(i);
    const kay = (x.kaynaklar || []), ilk = kay.length ? String(kay[0][0]).split("/").pop() : "";
    return `<label class="anahtar kart-satir"><input type="checkbox" data-kart="${bol}" data-i="${i}" ${sec ? "checked" : ""}><span><b>${esc(metin)}</b>${ek ? " · " + esc(ek) : ""}${x.celiski ? ` <span class="ipucu">(${esc(t.hz_celiski)})</span>` : ""}<br><span class="ipucu">${esc(t.hz_kaynak)}: ${esc(ilk)}${kay.length > 1 ? " +" + (kay.length - 1) : ""}</span></span></label>`;
  }
  function kartBolum(bol, baslik, satirFn) {
    const l = ((D.kart || {})[bol] || []); if (!l.length) return "";
    const g = l.slice(0, 60);
    return `<div class="alan"><span class="etiket">${esc(baslik)} · ${l.length}</span>${g.map((x, i) => satirFn(x, i)).join("")}${l.length > g.length ? `<div class="ipucu">+${l.length - g.length} ${esc(t.hz_daha)}</div>` : ""}</div>`;
  }
  // ---------- yapay zekâ (Faz 11 Aşama 4) ----------
  const yzSec = () => C.yz || "claude-code";
  const yzGrup = () => ({ gemini: "anahtar", ozel: "anahtar", ollama: "ollama" })[yzSec()] || "claude-code";
  const BY = () => (D.durum || {}).beyin || {};
  function yzHazir() { const c = (D.durum || {}).claude || {}, b = BY(), y = yzSec();
    if (y === "gemini") return !!b.gemini && (((b.dene || {}).gemini || {}).sonuc !== "anahtar");
    if (y === "ozel") return !!((b.ozel || {}).anahtar && (b.ozel || {}).adres && (b.ozel || {}).model);
    if (y === "ollama") return ["hazir", "iniyor"].includes((b.ollama || {}).durum);
    return !!(c.kurulu && c.giris) || !!C.kartsiz; }
  const kartYz = () => { const c = (D.durum || {}).claude || {}, y = C.yz || BY().secim; return !!(c.kurulu && c.giris) || (["gemini", "ozel"].includes(y) && yzHazir()); };
  const YZ_HATA = { bicim: "yz_an_bicim", zincir: "yz_an_zincir", adres: "yz_an_adres", model: "yz_an_model", yok: "yz_an_yok" };
  function yzAnahtarIcerik() { const b = BY(), y = yzSec(), oz = b.ozel || {}, var_ = y === "gemini" ? b.gemini : oz.anahtar, r = D.yzSonuc;
    const kd = dug("yz-kaydet", t.yz_kaydet), durum = D.yzDen ? satir("bekle", t.yz_deneniyor)
      : r && r.sg === y ? (r.ok ? satir("iyi", t.yz_an_iyi, "", kd) : satir("kotu", r.dene ? t["yz_an_" + r.dene] || t.yz_an_ag : t[YZ_HATA[r.hata] || "yz_an_zincir"], r.dene && r.ayrinti ? r.ayrinti : "", kd))
      : satir(var_ ? "iyi" : "uyari", var_ ? t.yz_an_var : t.yz_an_yok, "", kd);
    return `<div class="yongalar">${[["gemini", t.yz_gemini], ["ozel", t.yz_ozel]].map(([v, a]) => `<button class="yonga" type="button" data-yz-sg="${v}" aria-pressed="${y === v}">${esc(a)}</button>`).join("")}</div>
      ${y === "ozel" ? `<div class="iki"><div class="alan"><label for="yz_adres">${esc(t.yz_adres)}</label><input type="text" id="yz_adres" data-yz-alan="adres" value="${esc(C.yz_adres != null ? C.yz_adres : (oz.adres || "https://api.openai.com/v1"))}" autocomplete="off"><div class="ipucu">${esc(t.yz_adres_i)}</div></div>
        <div class="alan"><label for="yz_model">${esc(t.yz_model)}</label><input type="text" id="yz_model" data-yz-alan="model" value="${esc(C.yz_model != null ? C.yz_model : (oz.model || ""))}" autocomplete="off"><div class="ipucu">${esc(t.yz_model_i)}</div></div></div>` : ""}
      <div class="alan"><label for="yz_anahtar">${esc(t.yz_anahtar_alan)}</label><input type="password" id="yz_anahtar" data-yz-alan="anahtar" placeholder="${esc(t.yz_anahtar_ph)}" autocomplete="off" spellcheck="false"><div class="ipucu">${esc(t.yz_anahtar_i)}</div></div>
      <div class="liste">${durum}</div>
      ${y === "gemini" ? `<p class="dipnot">${esc(t.yz_gemini_al)}</p>` : ""}`; }
  function yzYerelIcerik() { const b = BY(), o = b.ollama || {}, m = (D.durum || {}).mac || {};
    const st = o.durum === "hazir" ? satir("iyi", t.yz_ol_hazir) : o.durum === "iniyor" ? satir("bekle", `${t.yz_ol_iniyor} · %${o.yuzde || 0}`, t.yz_ol_bekle)
      : o.durum === "hata" ? satir("kotu", t.yz_ol_hata, o.tur === "baska_hesap" ? t.yz_ol_baska : (o.mesaj || ""), o.tur === "baska_hesap" ? "" : dug("yz-ollama", t.yz_ol_yeniden))
      : satir("uyari", t.yz_ol_yok, "", dug("yz-ollama", t.yz_ol_kur));
    return `<div class="liste">${st}</div><p class="dipnot">${esc(tf(t.yz_ol_boyut, { gb: (Number(b.ollama_gb || 3.3) + Number(b.ollama_mb || 181) / 1024).toLocaleString(D.dil === "en" ? "en" : "tr", { maximumFractionDigits: 1 }), mb: b.ollama_mb || 181 }))}</p>
      <div class="kart-not uyari" data-yz-uyari>${esc(t.yz_ol_uyari)}</div>${m.bellek_gb && m.bellek_gb < 16 ? `<p class="dipnot">${esc(t.yz_ol_bellek)}</p>` : ""}`; }
  async function yzKaydet() {  // anahtar alandan okunur, gönderilince alan boşalır (yeniden çizim); kurulum.json'a yazılmaz
    const y = yzSec(), e = $("[data-yz-alan=anahtar]"), anahtar = e ? e.value.trim() : "";
    if (y === "ozel") { const a = $("[data-yz-alan=adres]"), md = $("[data-yz-alan=model]"); if (a) C.yz_adres = a.value.trim(); if (md) C.yz_model = md.value.trim(); kaydet(); }
    D.yzDen = true; ciz(); let r;
    try { r = await api("beyin/anahtar", { saglayici: y, anahtar, adres: C.yz_adres, model: C.yz_model }); } catch (x) { r = { ok: false, hata: "zincir" }; }
    D.yzDen = false; D.yzSonuc = { ...r, sg: y }; await durumAl(); ciz();
  }
  async function ollamaBekle() {
    if (D.olBek) return; D.olBek = true;
    try { while (gorunen()[D.adim] && gorunen()[D.adim].id === "claude" && yzSec() === "ollama") {
      await durumAl(); ciz(); if (((BY().ollama || {}).durum) !== "iniyor") break; await new Promise(r => setTimeout(r, 3000)); } } finally { D.olBek = false; }
  }
  function claudeIcerik() { const c = (D.durum || {}).claude || {};
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
          ${c.kurulu && c.giris ? "" : `${c.kurulu ? "" : `<p class="dipnot">${esc(t.c_aciklama)}</p>`}<p class="dipnot">${dug("kartsiz", t.c_kartsiz)}<br>${esc(t.c_kartsiz_a)}</p>`}`; }
  // ---------- asistan ----------
  const AS_BOS = tarz => ({ ad: "", bicim: "siz", tarz, ses: "mac" });
  const asPocket = () => !!(((D.durum || {}).asistan || {}).pocket) && D.dil !== "en";  // kurulu
  const asTr = () => D.dil !== "en";  // Pocket Türkçe: kadın/erkek yalnız Türkçe kurulumda; kurulu değilse seçince indirilir (S135)
  function pkDurum() {  // ses satırlarının altında: indirme bilgisi, durum, atıf (CC-BY)
    const k = ((D.durum || {}).asistan || {}).pocket_kur || {}, sec = C.asistan.liste.slice(0, C.asistan.iki ? 2 : 1).some(x => x.ses && x.ses !== "mac");
    const ust = asPocket() ? "" : k.durum === "iniyor" ? `<b>${esc(t.as_pk_iniyor)} · %${k.yuzde || 0}</b><br>${esc(t.as_pk_bekle)}<br>`
      : k.durum === "hata" && sec ? `${esc(t.as_pk_hata)}${k.mesaj ? " (" + esc(k.mesaj) + ")" : ""} ${dug("pk-yeniden", t.as_pk_yeniden)}<br>` : `${esc(t.as_pk_indir)}<br>`;
    return ust + `<span class="ipucu">${esc(t.as_pk_atif)}</span>`;
  }
  const pkGoster = () => { const e = $("[data-pk-durum]"); if (e) e.innerHTML = pkDurum(); };
  function asistanHazirla() {
    if (C.asistan && Array.isArray(C.asistan.liste)) return;
    const m = (D.durum || {}).asistan || {}, tp = m.toplanti, ds = m.disi;
    C.asistan = { iki: !!(ds && (!tp || ds.ad !== tp.ad)), atla: false, liste: [tp ? { ...tp } : AS_BOS("olculu"), ds && (!tp || ds.ad !== tp.ad) ? { ...ds } : AS_BOS("rahat")] };
  }
  const asAdHata = ad => { ad = String(ad || "").trim().replace(/\s+/g, " ");
    if (!/^[A-Za-zÇĞİIÖŞÜçğıiöşüÂâÎîÛû][A-Za-zÇĞİIÖŞÜçğıiöşüÂâÎîÛû' -]{1,23}$/.test(ad)) return "gecersiz";
    return ad.toLocaleLowerCase("tr") === "suflor" ? "suflor" : null; };
  function asistanHata(i) {  // i verilirse yalnız o asistan; yoksa ekranın tamamı (Devam)
    asistanHazirla(); const l = C.asistan.liste, n = C.asistan.iki ? 2 : 1;
    for (const j of (i == null ? [...Array(n).keys()] : [i])) { const h = asAdHata(l[j].ad); if (h) return h;
      if (j === 1 && l[0].ad.trim().toLocaleLowerCase("tr") === l[1].ad.trim().toLocaleLowerCase("tr")) return "ayni"; }
    return null;
  }
  const asYonga = (i, alan, deger, yazi, secili) => `<button class="yonga" type="button" data-as="${alan}" data-i="${i}" data-deger="${deger}" aria-pressed="${!!secili}">${esc(yazi)}</button>`;
  function asistanBlok(i, iki) {
    const x = C.asistan.liste[i], pk = asTr(), ses = pk ? x.ses : "mac", h = x.ad.trim() ? asistanHata(i) : null;
    const mev = Object.values((D.durum || {}).asistan || {}).find(m => m && m.ad && m.ad.toLocaleLowerCase("tr") === x.ad.trim().toLocaleLowerCase("tr")), var_ = !!mev;
    const elle = !!(mev && mev.tarz_elle);  // ton dosyada elle yazılmış: tarz seçimi uygulanmaz (kurulum.py asistan_guncelle), seçenek yerine not
    return `${iki ? `<h2 class="etiket" style="margin-top:${i ? 18 : 0}px">${esc(i ? t.as_disi : t.as_toplanti)}</h2>` : ""}
      <div class="alan"><label for="as_ad_${i}">${esc(t.as_ad)}</label><input type="text" id="as_ad_${i}" data-as-ad="${i}" value="${esc(x.ad)}" placeholder="${esc(t.as_ad_ph)}" autocomplete="off" maxlength="24">
        <div class="ipucu" data-as-ipucu="${i}">${esc(h ? t["as_" + h] : var_ ? t.as_var : i ? "" : t.as_ad_i)}</div></div>
      <div class="iki"><div class="alan"><span class="etiket">${esc(t.as_bicim)}</span><div class="yongalar">${asYonga(i, "bicim", "siz", t.as_siz, x.bicim !== "sen")}${asYonga(i, "bicim", "sen", t.as_sen, x.bicim === "sen")}</div></div>
        <div class="alan"><span class="etiket">${esc(t.as_tarz)}</span>${elle ? `<div class="ipucu" data-as-tarz-elle="${i}">${esc(t.as_tarz_elle)}</div>` : `<div class="yongalar">${asYonga(i, "tarz", "olculu", t.as_olculu, x.tarz !== "rahat")}${asYonga(i, "tarz", "rahat", t.as_rahat, x.tarz === "rahat")}</div>`}</div></div>
      <div class="alan"><span class="etiket">${esc(t.as_ses)}</span><div class="yongalar">${asYonga(i, "ses", "mac", t.as_mac, ses === "mac")}${pk ? asYonga(i, "ses", "kadin", t.as_kadin, ses === "kadin") + asYonga(i, "ses", "erkek", t.as_erkek, ses === "erkek") : ""}
        <button class="ikincil-dug" type="button" data-eylem="as-dinle" data-i="${i}" ${D.asDinle != null ? "disabled" : ""}>${esc(D.asDinle === i ? t.as_okuyor : t.as_dinle)}</button></div></div>`;
  }
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
    // Faz 11 Aşama 4: "Yapay zekâ bağla" — Claude Code (bugünkü adım) · API anahtarı (Gemini / OpenAI uyumlu) · yerel model (Ollama). Kimlik "claude" kalır
    // (kurulum.json'daki kayıtlı adım). Seçim kurulumda beyin.varsayilan'a yazılır (kurulum.py tamamla); Claude Code seçilmediyse Claude denetimi beklenmez.
    { id: "claude", simge: "claude", b: "claude_b", a: "claude_a", hazir: () => yzHazir(),
      // adıma girince oturum bilinmiyorsa kendiliğinden denetler; Terminal'den dönünce (pencere odağı) yeniden denetler
      gir: async () => { await durumAl(); if (C.yz == null) { const s = ((D.durum || {}).beyin || {}).secim; C.yz = s || "claude-code"; } const c = (D.durum || {}).claude || {};
        if (yzSec() === "claude-code" && c.kurulu && c.giris !== true) await claudeDenetle(); if (yzSec() === "ollama") ollamaBekle(); },
      icerik: () => `<div class="liste-secim">${[["claude-code", t.yz_claude, t.yz_claude_a], ["anahtar", t.yz_anahtar, t.yz_anahtar_a], ["ollama", t.yz_yerel, t.yz_yerel_a]].map(([v, b, a]) =>
          `<label class="anahtar"><input type="radio" name="yz" data-yz="${v}" ${yzGrup() === v ? "checked" : ""}><span><b>${esc(b)}</b><br><span class="ipucu">${esc(a)}</span></span></label>`).join("")}</div>
        <div class="yz-panel">${yzGrup() === "anahtar" ? yzAnahtarIcerik() : yzGrup() === "ollama" ? yzYerelIcerik() : claudeIcerik()}</div>
        <p class="dipnot" data-yz-gizlilik>${esc(t.yz_gizlilik)}</p>${yzGrup() === "claude-code" ? "" : `<p class="dipnot">${esc(t.yz_toplanti)}</p>`}` },
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
    // asistan (S133): kullanıcı yalnız asistanla muhatap; ad, hitap, tarz, ses, isteğe bağlı toplantı dışı ikinci asistan → kurulum.py asistan_uygula
    { id: "asistan", simge: "asistan", b: "as_b", a: "as_a", gir: () => { asistanHazirla(); ciz(); }, hazir: () => !asistanHata(),
      devamEt: () => { asistanHazirla(); C.asistan.atla = false; kaydet(); },
      icerik: () => { asistanHazirla(); const s = C.asistan, iki = !!s.iki;
        return `${(iki ? [0, 1] : [0]).map(i => asistanBlok(i, iki)).join("")}
          ${asTr() ? `<p class="dipnot" data-pk-durum>${pkDurum()}</p>` : ""}
          <label class="anahtar"><input type="checkbox" data-as-iki ${iki ? "checked" : ""}><span><b>${esc(t.as_iki)}</b><br><span class="ipucu">${esc(t.as_iki_a)}</span></span></label>
          <p class="dipnot">${dug("as-atla", t.atla)}<br>${esc(t.as_atla_a)}</p>`; } },
    { id: "proje", simge: "klasor", b: "proje_b", a: "proje_a", gir: () => { if (!C.proje && D.durum) C.proje = D.durum.proje; },
      icerik: () => `<div class="liste">${satir("iyi", C.proje || "~/Suflor", t.proje_icerik, dug("klasor-sec", t.proje_sec))}</div>` },
    { id: "kur", simge: "kur", b: "kur_b", a: "kur_a", hazir: () => { const k = D.kurDurum || {}; return k.ayar === "iyi" && k.aktarici === "iyi"; },
      gir: async () => { D.kurDurum = { ayar: "bekle", proje: "bekle", not: "bekle", aktarici: "bekle" }; ciz();
        try { D.kurDurum = await api("kur/tamamla", { cevap: C, dil: D.dil }); } catch (e) { D.kurDurum = { ...D.kurDurum, hata: String(e.message || e) }; } await durumAl(); ciz(); },
      icerik: () => { const k = D.kurDurum || {}, m = (D.durum || {}).modeller || {}, ys = (D.durum || {}).yerel_ses;
        return `<div class="liste">${satir(k.ayar || "bekle", t.k_ayar)}${satir(k.proje || "bekle", t.k_proje, C.proje || "")}${k.not === "bos" ? "" : satir(k.not || "bekle", t.k_not, k.not === "iyi" ? t.k_not_a : "")}${satir(k.aktarici || "bekle", t.k_aktarici)}
          ${satir(m.durum === "hazir" ? "iyi" : m.durum === "hata" ? "kotu" : "bekle", t.k_modeller, m.durum === "hazir" ? "" : m.durum === "hata" ? (m.tur === "baska_hesap" ? t.k_m_baska : t.k_m_hata + (m.mesaj ? " (" + m.mesaj + ")" : "")) : `%${m.yuzde || 0}`, m.durum === "hata" ? dug("modeller-yeniden", t.k_m_yeniden) : "")}
          ${k.aktarici === "iyi" && ys ? satir(ys.kurulu ? "iyi" : "uyari", t.k_ses, ys.kurulu ? t.k_ses_ok : t.k_ses_yok, ys.kurulu ? dug("ses-izni", t.k_ses_izin) : "") : ""}</div>
          ${k.hata ? `<div class="kart-not uyari">${esc(k.hata)}</div><p class="dipnot">${dug("kur-yeniden", t.k_m_yeniden)}</p>` : ""}${k.asistan_hata ? `<div class="kart-not uyari">${esc(k.asistan_hata)}</div>` : ""}${(k.uyarilar || []).map(u => `<div class="kart-not uyari">${esc(u)}</div>`).join("")}
          <p class="dipnot" data-beta-veri>${esc(t.p_veri)}</p>`; } },  // S141: beta şartı — onay kutusu yok, tek cümle
    { id: "hz_tara", simge: "klasor", b: "hz_tara_b", a: "hz_tara_a", hazir: () => !!H().tarama && !H().tara_suruyor,
      gir: async () => { await hzAl(); const tr = H().tarama; if (!H().tara_suruyor && (!tr || Date.now() / 1000 - tr.t > 600)) { await api("hazirlik/tara", {}).catch(() => {}); D.hz = { ...H(), tara_suruyor: true }; }
        await hzBekle("hz_tara", () => H().tarama && !H().tara_suruyor, 1500); },
      icerik: () => { const h = H(), tr = h.tarama;
        if (!tr || h.tara_suruyor && !tr) return `<div class="liste">${satir("bekle", t.hz_taraniyor)}</div>`;
        if (h.bos) return `<div class="kart-not">${esc(t.hz_bos)}</div>`;
        const s = tr.sayilar, ik = (s.kaynak_turu.turetilmis || 0) + (s.kaynak_turu.disa_aktarim || 0);
        const tur = Object.entries(s.tur).slice(0, 5).map(([k, n]) => `${(TUR_AD[D.dil] || TUR_AD.tr)[k] || k} ${n}`).join(", ");
        const ozet = `<div class="liste">${satir(h.tara_suruyor ? "bekle" : "iyi", `${s.dosya} ${t.hz_dosya} · ${mb(s.boyut)}`, tur)}
          ${s.kopya ? satir("iyi", `${t.hz_kopya}: ${s.kopya}`, t.hz_kopya_a) : ""}${s.eski_surum ? satir("iyi", `${t.hz_surum}: ${s.eski_surum}`, t.hz_surum_a) : ""}
          ${ik ? satir("iyi", `${t.hz_ikincil}: ${ik}`, t.hz_ikincil_a) : ""}${s.okunamayan ? satir("uyari", `${t.hz_okunamaz}: ${s.okunamayan}`, t.hz_okunamaz_a) : ""}</div>`;
        const kl = tr.klasorler || [];
        const klasor = kl.length ? `<div class="alan"><span class="etiket">${esc(t.hz_klasorler)}</span><div class="yongalar">${kl.map(k =>
          `<button class="yonga" type="button" data-hz-klasor="${esc(k.ad)}" aria-pressed="${!k.haric}">${esc(k.ad)}${k.haric ? "" : ` · ${k.dosya}`}</button>`).join("")}</div><div class="ipucu">${esc(t.hz_klasor_i)}</div></div>` : "";
        const gz = (tr.haric || []), dh = (tr.dahil || []);
        const gizli = gz.length || dh.length ? `<div class="alan"><span class="etiket">${esc(t.hz_gizli)}</span><div class="liste">${gz.slice(0, 20).map(x => satir("uyari", x.yol, x.neden, `<button class="ikincil-dug" type="button" data-hz-dahil="${esc(x.yol)}" data-deger="1">${esc(t.hz_dahil_et)}</button>`)).join("")}
          ${dh.map(y => satir("iyi", y, t.hz_dahil, `<button class="ikincil-dug" type="button" data-hz-dahil="${esc(y)}" data-deger="">${esc(t.hz_geri)}</button>`)).join("")}</div>${gz.length > 20 ? `<div class="ipucu">+${gz.length - 20} ${esc(t.hz_daha)}</div>` : ""}</div>` : "";
        const kt = (tr.kaynak_turu || []), as = (tr.asil || []);
        const asil = kt.length || as.length ? `<details class="alan"><summary class="etiket">${esc(t.hz_asil_b)} · ${kt.length}</summary><div class="ipucu">${esc(t.hz_asil_i)}</div><div class="liste">${kt.slice(0, 30).map(x => satir("bos", x.yol, x.neden, `<button class="ikincil-dug" type="button" data-hz-asil="${esc(x.yol)}" data-deger="1">${esc(t.hz_asil_say)}</button>`)).join("")}
          ${as.map(y => satir("iyi", y, t.hz_asil, `<button class="ikincil-dug" type="button" data-hz-asil="${esc(y)}" data-deger="">${esc(t.hz_geri)}</button>`)).join("")}</div></details>` : "";
        return ozet + klasor + gizli + asil; } },
    { id: "hz_onay", simge: "kur", b: "hz_onay_b", a: "hz_onay_a", kosul: () => !hzBos(), devamYazi: () => hzIsDurum().calisiyor ? null : t.hz_baslat,
      gir: async () => { hzKartVarsayilan(); await hzAl(); ciz(); },
      devamEt: async () => { hzKartVarsayilan(); await api("hazirlik/baslat", { kart: !!(C.hz_kart && kartYz()) }).catch(() => {}); kaydet(); },
      icerik: () => { const th = H().tahmin || {}, c = { giris: kartYz() };
        const cv = th.cevir || {}, cvy = [[".pdf", "PDF"], [".pptx", "PowerPoint"]].map(([e, a]) => cv[e] ? `${a} ${cv[e]}` : "").filter(Boolean), gr = Object.entries(cv).filter(([e]) => ![".pdf", ".pptx"].includes(e)).reduce((a, [, n]) => a + n, 0);
        const cvAc = [...cvy, gr ? `${(TUR_AD[D.dil] || TUR_AD.tr).goruntu} ${gr}` : ""].filter(Boolean).join(", ");
        const kartSn = C.hz_kart && c.giris ? (th.kart_sn || 0) : 0;
        return `<div class="liste">${!th.cevirme_kurulu && th.cevir_n ? satir("uyari", `${t.hz_cevir}: ${th.cevir_n}`, t.hz_cevir_model) : satir("iyi", th.cevir_n ? `${t.hz_cevir}: ${th.cevir_n}` : t.hz_cevir_yok, cvAc)}
          ${satir("iyi", `${t.hz_dizin}: ~${(th.parca_yeni || 0) + (th.gomme_n || 0) ? (th.gomme_n || th.parca_yeni) : 0} ${t.hz_parca}`)}
          ${satir("iyi", `${t.hz_sure}: ${dk((th.sn || 0) + kartSn)}`, t.hz_toplanti_not)}</div>
          ${c.giris ? `<label class="anahtar"><input type="checkbox" data-hz-kart ${C.hz_kart ? "checked" : ""}><span><b>${esc(t.hz_kart_cikar)}</b><br><span class="ipucu">${esc(tf(t.hz_kart_ac, { n: th.kart_belge || 0, d: Math.max(1, Math.round((th.kart_sn || 0) / 60)), u: (th.kart_usd || 0).toLocaleString(D.dil === "en" ? "en" : "tr") }))}</span></span></label>`
            : `<div class="kart-not">${esc(t.hz_kart_claude)}</div>`}`; } },
    { id: "hz_ilerleme", simge: "kur", b: "hz_ilerleme_b", a: "hz_ilerleme_a", kosul: () => !hzBos(),
      gir: () => hzBekle("hz_ilerleme", () => { const e = hzIsDurum(); return !e.calisiyor && ["bitti", "durdu", "hata"].includes(e.evre); }),
      icerik: () => { const e = hzIsDurum(), sira = ["tara", "cevir", "dizin", "gomme", "kart"], su = sira.indexOf(e.evre), son = ["bitti", "durdu", "hata"].includes(e.evre);
        const ad = { tara: t.hz_e_tara, cevir: t.hz_e_cevir, dizin: t.hz_e_dizin, gomme: t.hz_e_gomme, kart: t.hz_e_kart };
        const satirlar = sira.filter(x => x !== "kart" || e.kart_istendi).map((x, i) => {
          const a = (e.adim || {})[x], bitti = son ? true : i < su, simdi = !son && i === su;
          let ac = a && a.toplam ? `${a.n} / ${a.toplam}` : "";
          if (x === "gomme" && e.gomme && e.gomme.durdu === "anlam araması kurulu değil") return satir("bos", ad[x], t.hz_kurulu_degil);
          if (x === "cevir" && e.cevir && e.cevir.durdu && son) return satir("uyari", ad[x], /ortamı yok/.test(e.cevir.durdu) ? t.hz_cevir_model : t.hz_durdu + e.cevir.durdu);
          return satir(bitti ? "iyi" : simdi ? "bekle" : "bos", ad[x], simdi ? (ac || "…") : bitti && a ? ac : "");
        }).join("");
        const alt = e.evre === "hata" ? `<div class="kart-not uyari">${esc(t.hz_hata + (e.hata || ""))}</div>` : e.evre === "durdu" && e.durdu ? `<div class="kart-not uyari">${esc(t.hz_durdu + e.durdu)}</div>` : "";
        return `<div class="liste">${satirlar}</div>${alt}<p class="dipnot">${esc(t.hz_toplanti_not)}</p>`; } },
    { id: "takvim", simge: "takvim", b: "takvim_b", a: "takvim_a", gir: takvimBekle,
      icerik: () => { const tk = (D.durum || {}).takvim || {};
        if (tk.durum !== "ok") return `<div class="liste">${satir(tk.durum === "izin_yok" ? "uyari" : "bos", t.t_izin_b, t.t_izin_a, dug("takvim-izin", t.t_izin))}</div>${epostaBlok()}`;
        const tl = tk.takvimler || [], sec = new Set(C.takvim_adres || []);
        const ad = [...new Set([...(tk.adaylar || []).map(x => x.adres), ...(C.takvim_adres || [])])];
        const adres = `<div class="alan"><span class="etiket">${esc(t.t_adres)}</span>${tk.adaylar == null ? `<div class="ipucu">${esc(t.t_adres_bekle)}</div>`
          : `<div class="yongalar">${ad.map(x => yonga("adres", x, sec.has(x))).join("")}</div>`}
          <input type="text" data-adres-ek placeholder="${esc(t.t_adres_ek)}" style="margin-top:8px">${tk.adaylar != null && !sec.size ? `<div class="ipucu">${esc(t.t_adres_yok)}</div>` : ""}</div>`;
        return `${adres}${tl.length ? `<div class="alan"><span class="etiket">${esc(t.t_dogru)}</span><div class="yongalar">${tl.map(x => yonga("takvim", x.ad + " · " + x.hesap, !(C.takvim_cikar || []).includes(x.ad + " · " + x.hesap) && x.sec !== false)).join("")}</div></div>`
          : `<div class="kart-not">${esc(t.t_hesap_yok)} ${dug("internet-hesaplari", t.t_hesap_ekle)}</div>`}
          <div class="alan"><span class="etiket">${esc(t.t_bugun)}</span><div class="liste">${(tk.olaylar || []).length ? tk.olaylar.map(o => satir("iyi", o.baslik, `${o.saat}–${o.bitis}${o.platform ? " · " + o.platform : ""}`)).join("") : satir("iyi", t.t_bos)}</div></div>
          ${epostaBlok()}`; } },
    { id: "eklenti", simge: "eklenti", b: "ek_b", a: "ek_a", hazir: () => ((D.durum || {}).eklenti || {}).bagli, gir: () => eklentiBekle(),
      icerik: () => { const e = (D.durum || {}).eklenti || {};
        return `<ol class="adimlar"><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e1)}<div class="eylem">${dug("chrome-eklentiler", t.e1d)}</div></div></li>
          <li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e2)}${(D.durum || {}).kod ? ` <code>${esc(D.durum.kod)}</code>` : ""}<div class="eylem">${(D.durum || {}).kod ? dug("kod-kopyala", t.e2k) : ""}${dug("eklenti-klasoru", t.e2d)}</div></div></li><li class="${e.bagli ? "tamam" : ""}"><div>${esc(t.e3)}</div></li></ol>
          <div class="liste">${satir(e.bagli ? "iyi" : "bekle", e.bagli ? t.e_bagli : t.e_bekle, e.surum ? "v" + e.surum : "")}</div>
          ${!e.bagli && e.coklu ? `<div class="kart-not uyari">${esc(t.e_coklu + (e.alan || ""))}</div>` : ""}
          ${e.bagli ? "" : `<p class="dipnot">${esc(t.e_profil)}</p><p class="dipnot">${dug("atla", t.atla)}</p>`}
          ${((D.durum || {}).mac || {}).teams_uygulama ? `<p class="dipnot">${esc(t.teams_not)}</p>` : ""}`; } },
    { id: "hz_kart", simge: "tanidim", b: "hz_kart_b", a: "hz_kart_a", kosul: () => !hzBos() && (hzKartIstendi() || !!(H().kart)),
      devamYazi: () => D.kart && !D.kart.yok && !D.kartOnay ? t.hz_onayla : null,
      gir: async () => { await hzBekle("hz_kart", () => { const e = hzIsDurum(); return !(e.calisiyor && e.evre === "kart") && !(e.calisiyor && e.kart_istendi); }, 3000);
        if (gorunen()[D.adim] && gorunen()[D.adim].id === "hz_kart" && H().kart) { try { D.kart = await api("hazirlik/kart"); } catch (e) { D.kart = null; }
          if (D.kart && !D.kart.yok && !D.kartTerim) D.kartTerim = new Set((D.kart.sozluk || []).filter(m => m.oneri).map(m => m.terim)); ciz(); } },
      devamEt: async () => { if (!D.kart || D.kart.yok || D.kartOnay) return;
        const cikar = {}; for (const [b, st] of Object.entries(D.kartCikar || {})) cikar[b] = [...st];
        try { D.kartOnay = await api("hazirlik/kart-onayla", { cikar, terimler: [...(D.kartTerim || [])] }); } catch (e) { D.kartOnay = { hata: String(e.message || e) }; } },
      icerik: () => { const e = hzIsDurum(), k = D.kart;
        if (e.calisiyor && (e.evre === "kart" || e.kart_istendi)) { const a = (e.adim || {}).kart; return `<div class="liste">${satir("bekle", t.hz_kart_bekle, a && a.toplam ? `${a.n} / ${a.toplam}` : "")}</div>`; }
        if (!k || k.yok) return `<div class="kart-not">${esc(t.hz_kart_yok)}</div>`;
        const ozet = k.ozet ? `<div class="alan"><span class="etiket">${esc(t.hz_ozet)}</span><div class="kart-not">${esc(k.ozet)}</div></div>` : "";
        const vt = k.veritabani_kipi ? `<div class="kart-not">${esc(t.hz_vt)}</div>` : "";
        const ks = kartBolum("kisiler", t.hz_kisiler, (x, i) => kartSatir("kisiler", i, x, x.ad, [...(x.roller || []).slice(0, 2), ...(x.kurumlar || []).slice(0, 1)].join(", ")));
        const ku = kartBolum("kurumlar", t.hz_kurumlar, (x, i) => kartSatir("kurumlar", i, x, x.ad));
        const kr = kartBolum("kararlar", t.hz_kararlar, (x, i) => kartSatir("kararlar", i, x, x.ne, x.ne_zaman));
        const ta = kartBolum("tarihler", t.hz_tarihler, (x, i) => kartSatir("tarihler", i, x, x.ne, x.tarih));
        const is = kartBolum("acik_isler", t.hz_isler, (x, i) => kartSatir("acik_isler", i, x, x.is, [...(x.sahip || []), x.tarih].filter(Boolean).join(" · ")));
        const sz = (k.sozluk || []).length ? `<div class="alan"><span class="etiket">${esc(t.hz_sozluk)} · ${(D.kartTerim || new Set()).size}/${k.sozluk_en_cok || 60}</span><div class="ipucu">${esc(tf(t.hz_sozluk_i, { n: k.sozluk_en_cok || 60 }))}</div>
          <div class="yongalar">${k.sozluk.slice(0, 150).map(m => `<button class="yonga" type="button" data-hz-terim="${esc(m.terim)}" aria-pressed="${(D.kartTerim || new Set()).has(m.terim)}" title="${esc(m.aciklama || "")}">${esc(m.terim)}</button>`).join("")}</div></div>` : "";
        const sonuc = D.kartOnay ? `<div class="kart-not ${D.kartOnay.hata ? "uyari" : ""}">${esc(D.kartOnay.hata ? t.hz_hata + D.kartOnay.hata : t.hz_onaylandi)}</div>` : "";
        return ozet + vt + ks + ku + kr + ta + is + sz + sonuc + (D.kartOnay ? "" : `<p class="dipnot">${dug("atla", t.hz_sonra)}</p>`); } },
    { id: "bitti", simge: "isaret", b: "bitti_b", a: "bitti_a", son: true, gir: async () => { if (D.hz) { await hzAl(); ciz(); } },
      icerik: () => { const e = hzIsDurum(), s = e.sonuc;
        if (!D.hz || hzBos()) return "";
        if (e.calisiyor) return `<div class="liste">${satir("bekle", t.hz_bitti_suruyor)}</div>`;
        return s && !s.bos ? `<div class="liste">${satir("iyi", tf(s.cevrilen ? t.hz_bitti_hazir : t.hz_bitti_hazir0, { b: s.belge, p: s.parca, c: s.cevrilen }))}`
          + (s.tablo ? satir("iyi", tf(t.hz_bitti_tablo, { n: s.tablo, r: s.tablo_satir })) : "") + `</div>` : ""; } },
  ];
  const gorunen = () => ADIMLAR.filter(a => (!hzMod() || HZ_ADIM.includes(a.id)) && (!a.kosul || a.kosul()));

  // ---------- çizim ----------
  let yon = 1;
  function ciz() {
    const ads = gorunen(); D.adim = Math.max(0, Math.min(D.adim, ads.length - 1)); const a = ads[D.adim];
    const sahne = $("#sahne");
    sahne.innerHTML = a.ciz ? a.ciz() : `<section class="adim ${yon < 0 ? "geri" : ""}" aria-labelledby="baslik">
      <div class="simge ${a.simge === "isaret" ? "isaret" : ""}">${S[a.simge] || ""}</div>
      <h1 id="baslik">${esc(t[a.id === "bitti" && hzMod() ? "hz_bitti_b" : a.b])}</h1><p class="alt">${esc(t[a.id === "bitti" && hzMod() ? "hz_bitti_a" : a.a])}</p>
      <div class="icerik">${a.icerik ? a.icerik() : ""}</div></section>`;
    const odak = sahne.querySelector("input, textarea"); if (odak && !odak.value && D.ilkCizim !== a.id) { odak.focus(); } D.ilkCizim = a.id;
    $("#alt-cubuk").style.visibility = a.cubuksuz ? "hidden" : "visible";
    $("#geri").textContent = t.geri; $("#geri").style.visibility = D.adim > 0 ? "visible" : "hidden";
    const d = $("#devam"); d.textContent = a.son ? (hzMod() ? t.hz_bitir : t.bitir) : (a.devamYazi && a.devamYazi()) || (a.id === "hosgeldin" ? t.basla : t.devam); d.disabled = a.hazir ? !a.hazir() : false;
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
    if (a && a.id === "claude" && yzSec() === "claude-code" && c.kurulu && !c.giris && !D.claudeDen && Date.now() - (D.sonDen || 0) > 15000) claudeDenetle();
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
    // proje hazırlığı yongaları genel .yonga işleyicisinden önce
    const hk = e.target.closest("[data-hz-klasor]"); if (hk) { isaretle("haric", hk.dataset.hzKlasor, hk.getAttribute("aria-pressed") === "true"); return; }
    const hd = e.target.closest("[data-hz-dahil]"); if (hd) { isaretle("dahil", hd.dataset.hzDahil, !!hd.dataset.deger); return; }
    const ha = e.target.closest("[data-hz-asil]"); if (ha) { isaretle("asil", ha.dataset.hzAsil, !!ha.dataset.deger); return; }
    const ht = e.target.closest("[data-hz-terim]");
    if (ht) { const s = D.kartTerim || (D.kartTerim = new Set()), v = ht.dataset.hzTerim, en = (D.kart || {}).sozluk_en_cok || 60;
      if (s.has(v)) s.delete(v); else if (s.size < en) s.add(v); ciz(); return; }
    const ys = e.target.closest("[data-yz-sg]"); if (ys) { C.yz = C.yz_sg = ys.dataset.yzSg; D.yzSonuc = null; kaydet(); ciz(); return; }
    const ay = e.target.closest("[data-as]");
    if (ay) { asistanHazirla(); C.asistan.liste[+ay.dataset.i][ay.dataset.as] = ay.dataset.deger; kaydet(); ciz();
      if (ay.dataset.as === "ses" && ay.dataset.deger !== "mac" && !asPocket()) api("pocket/baslat", {}).then(durumAl).then(pkGoster).catch(() => {});  // seçim = indirme onayı
      return; }
    const y = e.target.closest(".yonga");
    if (y) {
      const g = y.dataset.grup, v = y.dataset.deger, on = y.getAttribute("aria-pressed") !== "true";
      if (g === "alan") { C.is_alani = v; } else if (g === "eposta") { C.eposta = v; epostaKaydet(); } else {
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
      if (n === "kod-kopyala") { try { await navigator.clipboard.writeText((D.durum || {}).kod || ""); ey.textContent = t.e2k_ok; } catch (e) {} return; }  // eklenti adımı: Command + Shift + G'ye yapıştırılacak yol
      if (n === "atla") { git(D.adim + 1); return; }
      if (n === "as-atla") { asistanHazirla(); C.asistan.atla = true; kaydet(); git(D.adim + 1); return; }
      if (n === "pk-yeniden") { await api("pocket/baslat", {}).catch(() => {}); await durumAl(); pkGoster(); return; }
      if (n === "as-dinle") { const i = +ey.dataset.i, x = C.asistan.liste[i]; D.asDinle = i; ciz();
        try { await api("asistan/dinle", { ...x, ses: asTr() ? x.ses : "mac", dil: D.dil }); } catch (e) {} D.asDinle = null; ciz(); return; }
      if (n === "ornek") { C.ornek = !C.ornek; kaydet(); ciz(); return; }
      if (n === "claude-denetle") { await claudeDenetle(); return; }
      if (n === "yz-kaydet") { await yzKaydet(); return; }
      if (n === "yz-ollama") { await api("ollama/baslat", {}).catch(() => {}); await durumAl(); ciz(); ollamaBekle(); return; }
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
  document.addEventListener("change", e => {  // proje hazırlığı: kart çıkarılsın mı (C), kart satırı tutulsun mu (E)
    if (!e.target.matches) return;
    if (e.target.matches("[data-hz-kart]")) { C.hz_kart = e.target.checked; kaydet(); ciz(); return; }
    if (e.target.matches("[data-kart]")) { const b = e.target.dataset.kart, i = +e.target.dataset.i, m = D.kartCikar || (D.kartCikar = {}), st = m[b] || (m[b] = new Set());
      if (e.target.checked) st.delete(i); else st.add(i); }
  });
  document.addEventListener("change", e => {  // gönderen adresi: geçerliyse ya da boşsa yazılır
    if (!e.target.matches || !e.target.matches("[data-eposta-adres]")) return;
    const v = e.target.value.trim().toLowerCase(); if (v && !/^[^\s@,]+@[^\s@,]+\.[^\s@,]+$/.test(v)) return;
    C.eposta_adres = v; kaydet(); epostaKaydet();
  });
  document.addEventListener("change", e => {
    if (!e.target.matches || !e.target.matches("[data-adres-ek]")) return;
    const v = e.target.value.trim().toLowerCase(); if (!/^[^\s@,]+@[^\s@,]+\.[^\s@,]+$/.test(v)) return;
    C.takvim_adres = [...new Set([...(C.takvim_adres || []), v])]; kaydet(); takvimKaydet(); ciz();
  });
  document.addEventListener("input", e => {  // asistan adı: yeniden çizmeden (odak kaybolmasın) ipucu ve Devam güncellenir
    const i = e.target.dataset && e.target.dataset.asAd; if (i == null) return;
    asistanHazirla(); C.asistan.liste[+i].ad = e.target.value; const h = e.target.value.trim() ? asistanHata(+i) : null, ip = $(`[data-as-ipucu="${i}"]`);
    if (ip && (h || ip.dataset.h)) { ip.textContent = h ? t["as_" + h] : (+i ? "" : t.as_ad_i); ip.dataset.h = h || ""; }
    $("#devam").disabled = !!asistanHata(); clearTimeout(D.zz); D.zz = setTimeout(kaydet, 500);
  });
  document.addEventListener("change", e => {  // yapay zekâ seçimi (radyo): anahtar grubunda önceki hizmet (yoksa Gemini)
    if (!e.target.matches || !e.target.matches("[data-yz]")) return; const v = e.target.dataset.yz;
    C.yz = v === "anahtar" ? (["gemini", "ozel"].includes(C.yz) ? C.yz : C.yz_sg || "gemini") : v; D.yzSonuc = null; kaydet(); ciz();
    const c = (D.durum || {}).claude || {}; if (v === "claude-code" && c.kurulu && c.giris !== true) claudeDenetle(); if (v === "ollama") ollamaBekle(); });
  document.addEventListener("change", e => { if (e.target.matches && e.target.matches("[data-as-iki]")) { asistanHazirla(); C.asistan.iki = e.target.checked; kaydet(); ciz(); } });
  document.addEventListener("change", e => { if (e.target.dataset && e.target.dataset.asAd != null) ciz(); });  // ad alanından çıkınca: var olan asistan notu ve tarz seçeneği yeni ada göre
  document.addEventListener("input", e => { const k = e.target.dataset && e.target.dataset.cevap; if (k) { C[k] = e.target.value; const a = gorunen()[D.adim]; if (a.hazir) $("#devam").disabled = !a.hazir(); clearTimeout(D.zz); D.zz = setTimeout(kaydet, 500); } });
  document.addEventListener("keydown", e => { if (e.key === "Enter" && e.target.dataset && e.target.dataset.yzAlan) { e.preventDefault(); yzKaydet(); return; }
    if (e.key === "Enter" && !e.shiftKey && e.target.tagName !== "TEXTAREA" && !$("#devam").disabled && e.target.tagName !== "BUTTON") $("#devam").click(); });
  $("#devam").addEventListener("click", async () => { const a = gorunen()[D.adim]; if (a.son) { api("ac", { hedef: "pano" }).catch(() => {}); return; }
    if (a.devamEt) { const d = $("#devam"); d.disabled = true; try { await a.devamEt(); } finally { d.disabled = false; } }
    const s = gorunen().indexOf(a); git((s < 0 ? D.adim : s) + 1); });
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
    try { const k = await api("kayit"); if (k && k.dil) { D.dil = k.dil; D.adim = k.adim || 0; D.kayitAdimId = k.adim_id || ["karsilama", "hosgeldin", "mac", "claude", "sen", "proje", "kur", "takvim", "eklenti", "bitti"][k.adim || 0] /* v0.76.0 öncesi kayıt: eski sıra */; Object.assign(C, k.cevap || {}); } } catch (e) {}
    D.kayitAdim = D.adim;
    t = M[D.dil] || M.tr; await durumAl();
    if (hzMod()) D.adim = 0; else if (D.adim > 0) await hzAl();  // kurulum yarıda kaldıysa kart ekranı görünsün diye
    if (!hzMod() && D.kayitAdimId) { const i = gorunen().findIndex(a => a.id === D.kayitAdimId); if (i >= 0) D.adim = i; }  // v0.76.0: adım adıyla (yeni ekran araya girince sıra kayar)
    ciz();
    const a = gorunen()[D.adim]; if (a && a.gir) { await a.gir(); ciz(); }
    setInterval(() => { if (!document.hidden) durumAl(); }, 5000);
  })();
})();
