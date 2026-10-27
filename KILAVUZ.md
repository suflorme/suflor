# Suflor.me kılavuzu

README'de kısaca anlatılanların ayrıntısı: kurulumdan sonra, kullanım, ayarlar, sesler, gizlilik ve bileşenler.
Ürünün genel tanıtımı için [README](README.md).

- [Kurulumdan sonra](#kurulumdan-sonra)
- [Kullanım](#kullanım)
- [İsteğe bağlı ayarlar](#isteğe-bağlı-ayarlar)
- [Yapay zekâ seçimi](#yapay-zekâ-seçimi)
- [Sesler](#sesler)
- [Gizlilik ayrıntıları](#gizlilik-ayrıntıları)
- [Gerekenler](#gerekenler)
- [Bileşenler](#bileşenler)
- [Lisanslar](#lisanslar)

## Kurulumdan sonra
**Asistan:** sihirbazda asistanına ad koyarsın; ona adıyla seslenirsin ("Defne, yarın neler var?"). Hitap (siz/sen), tarz (ölçülü ya da rahat
ve esprili) ve ses (Mac'in Türkçe sesi ya da doğal Türkçe kadın/erkek sesi: Pocket, seçince indirilir) seçilir; istersen toplantı dışında konuşan ikinci bir asistan
eklersin. Sihirbaz kişilik dosyasını `~/Library/Application Support/Suflor/kisilik/<ad>.md` olarak yazar (aynı adlı dosya varsa üzerine yazmaz)
ve ayara bağlar (`kisilik`, ikinci asistan `kisilik_toplanti_disi`). Atlarsan asistanın adı Suflor olur. Dosyayı elle de düzenleyebilirsin
(biçim: `sablon/kisilik-ornek.md`); asistanları sonradan ⚙ Ayarlar → Konuş'ta değiştirirsin.
Her yayın geliştiricinin anahtarıyla imzalıdır: kurulum ve güncelleme indirilen kodun imzasını ve dosya özetlerini doğrular, tutmazsa hiçbir şey kurmaz.

**Proje hazırlığı:** sihirbaz proje klasörünü tarar (kopya, eski sürüm, adından gizli görünen dosyalar; dizine girmesini istemediğin klasörü
çıkarırsın), PDF, sunum ve görüntüleri bu Mac'te metne çevirip dizinler ve istersen proje kartını (özet, kişiler, kararlar, açık işler, terimler)
Claude'la hazırlar; kartı onaylamadan önce düzeltirsin. Arka planda sürer, sihirbazı kapatsan da biter. Sonradan: panoda ⚙ Ayarlar → Proje →
**Projeyi yeniden hazırla**.
Proje klasörün buluttaysa (iCloud Drive, Google Drive, OneDrive, Dropbox): yalnız bulutta duran dosyalar indirilmez, adı ve yeriyle tanınır;
içinde arama için dosyayı Mac'e indirmen gerekir (sonraki turda kendiliğinden okunur). Google Dokümanlar/E-Tablolar/Slaytlar Mac'te yalnız kısayol
olduğu için bugün okunmaz.

**Güncelleme:** yeni sürüm çıkınca panonun sağ üstünde **Güncelle** düğmesi belirir (toplantı yokken); tıklaman yeter, Chrome
eklentisi de kendini yeniler. Elle: `~/Suflor.me/guncelle.command`'a çift tıkla (son sürümü indirir, aktarıcıyı yeniden kurar; ayarlarına ve
belgelerine dokunmaz). Eklenti kendini yenilemezse: Chrome'da `chrome://extensions` → Suflor.me → yenile.

**Kaldırma:** `~/Suflor.me/kaldir.command`'a çift tıkla. Aktarıcıyı durdurur; Mac uygulamasını, ayarları, dökümleri, günlükleri ve verilen
izinleri kaldırır. Hiçbir şeyi silmez, Çöp Sepeti'ne taşır (Finder'da Çöp Sepeti → sağ tık → Geri Koy). Proje klasörünün kendisine ve
belgelerine dokunmaz; yalnız Suflor'un eklediklerini (`_canli` kısayolu, `/toplanti` komutu, değiştirmediğin `CLAUDE.md`, boş klasörler)
kaldırır. Toplantı notlarını (`gorusmeler/`), modelleri ve `~/Suflor.me` klasörünü ayrıca sorar. Sonra Chrome'da `chrome://extensions` → Suflor.me → Kaldır.

**Proje klasörü:** sihirbazda içi dolu bir belge klasörü seçersen Suflor belgelerine dokunmaz, yalnız okur ve arar; kendi dosyalarını
(`CLAUDE.md`, `/toplanti` komutu, toplantı notları, kanıtlar, `_canli` kısayolu) o klasörün içindeki tek bir `Suflor/` klasörüne yazar ve Claude
oturumları orada açılır. Boş ya da yeni bir klasör seçersen bu dosyalar klasörün kendisinde durur.

**Modellerin yeri:** `/Users/Shared/Suflor`. Aynı Mac'te bu klasörü başka bir hesap kurduysa her hesap kendi modellerini
`~/Library/Application Support/Suflor-ortak` altına indirir (~5–12 GB).

## Kullanım
1. Toplantıya nereden istersen katıl: takvimdeki bağlantı, Teams, Meet ya da Zoom sayfası, masaüstü Teams ya da Zoom. Suflor toplantıyı kendisi tanır.
   Takvimde o saatte (±15 dk) bir toplantı varsa adı, katılımcıları ve gündemi oradan alır, döküm dosyasını hemen açar ve asistanın toplantı
   oturumunu sormadan başlatır (yalnız toplantı uygulaması ya da sayfası toplantıyı bildirdiğinde; yalnızca mikrofon ve takvim eşleşmesiyle
   başlatmaz — panoda "Toplantı algılandı — Claude'u başlat" kartı çıkar, Onayla'ya basınca başlar). Önceden hazırlanmak istersen panodaki takvimden **Başlat**'a basabilirsin; toplantı sürerken basılan Başlat yeni
   kayıt açmaz, süren toplantıya katılır. Gizli toplantı açıkken toplantı tanınmaz. Asistanın kendiliğinden açılmasını istemediğin toplantılar için
   ayar.json'da `"oto_haric": ["<adın bir parçası>", …]` (döküm yine tutulur); hepsini kapatmak için `"oto_toplanti": false`.
2. Karşı tarafın sesi kendiliğinden yazıya dökülür (Suflor Ses yardımcısı, macOS 14.4+; ilk kurulumda macOS "Sistem Sesi Kaydı" izni
   sorar — İzin Ver). Yardımcı yoksa ya da izin verilmediyse Chrome'daki toplantıda **Suflor.me simgesi → "Karşı taraf" satırındaki Aç** (satır yalnız sorun varken görünür; masaüstü Teams/Zoom'da yedek yok).
3. Kartlar toplantı ekranının sol altındaki küçük şeritte ve panoda görünür. ✓ yaptım · 👁 okudum · ✕ gerek yok. Kartı "Sonra" (⏸) ile gündemde sıradaki maddeye bırakabilirsin.
4. Toplantıda kutunun üstünde sağda: **Ne diyeyim?** (tek cümlelik replik önerisi), **Kanıt**, **Sessiz** (10 dk kart yok); "⋯" içinde önemli an, gizli toplantı, sesli çeviri.
   Kısayollar: **Option + Shift + K** kanıt · **Option + Shift + O** Ne diyeyim? · **Option + Shift + M** sessiz · **Option + Shift + S** asistan sussun.
5. Toplantı bitince özet hazırlanır ve sana sunulur.
6. Brifing ve özet panoda **Dışarı aktar** ile PDF, e-posta taslağı (alıcısız, katılımcılara ya da kendine), panoya kopya ya da .md dosyası olur.
   Taslağın açılacağı yeri (Gmail, Outlook web ya da Mac'in posta uygulaması) ve gönderen adresini sihirbazın takvim ekranında seçersin;
   sonradan ayar.json'da `"eposta"` ve `"eposta_adres"`. Seçmezsen takvimine bakılarak seçilir.

**Ayarlar:** panonun üst çubuğundaki ⚙ — yapay zekâ seçimi, e-posta, ses ve konuşma, toplantı uyarıları, çeviri ve masaüstü, gizlilik; kaydedince hemen geçerli.

## İsteğe bağlı ayarlar
**Sesle hatırlatma:** onayladığın saatli hatırlatma Mac Takvim'in varsayılan takvimine 15 dakikalık, başında uyaran bir etkinlik olarak eklenir
(Exchange/Google takvimiyse telefonuna da eşitlenir); başka bir takvim için `"hatirlatma_takvim": "<takvim adı>"`. Saati olmayan istek kendine e-posta taslağı olur.

**Sesle toplantı:** "yarın on ikide Deniz'le toplantı koy" gibi başka biriyle toplantı isteği hatırlatma değil toplantı olur. Onaylayınca takviminde
yeni toplantı sayfası açılır: başlık, saat, süre (söylenmezse 30 dk) ve davetliler dolu, Google'da Meet bağlantısıyla. Sen Kaydet'e basarsın. Davetlinin
adresi söylediğin e-postadan ya da son 30 günün takvim toplantılarından bulunur; bulunamayan ad sayfadaki notta yazar. Ayar `eposta` Outlook ise Outlook takvimi açılır.

**Menü çubuğu uygulaması (varsayılan açık; kapatmak için ayar.json'da `"menu_cubugu": false`):** pano Mac penceresinde açılır; menü çubuğu uygulaması (buzlu cam panelde mini pano,
Mac genelinde **Option + Shift + Boşluk** basılı tut-konuş ve yukarıdaki kısayollar, Teams/Zoom masaüstü toplantılarında da
çalışma: toplantıyı ve sessizi tanır, senin mikrofonunu ve karşı tarafın sesini yazar, kanıt ve
paylaşılan ekran görüntüsünü toplantı penceresinden alır; Erişilebilirlik, mikrofon ve Ekran Kaydı izni sorar (ayarı değiştirdiysen sonra `guncelle.command`).
Uygulama `~/Applications/Suflor.me.app`'e kurulur (hesaba özel): Launchpad'de, Spotlight'ta ve Finder'daki Uygulamalar'da Suflor.me adıyla
bulunur; açıkken simgesine tıklamak pano penceresini öne getirir.
Kapatmak için `"masaustu_mic": false`, `"kisayollar": false`; Kişiler panelinden ad okuma `"masaustu_kisiler": true` ile açılır — panel
3 dakikada bir açılıp kapanır, Teams penceresi öne gelir) · `"fisilti": true` — kulaklık takılıyken DUR kartı kısa sesle kulağına okunur ·
`"ceviri": true` — karşı tarafın İngilizce satırları panoda Türkçesiyle (metin Claude'a gider; 🎧 sesli çeviride toplantı sesi tarayıcıda
kısılır, masaüstü Teams/Zoom'da kısmak için ayrıca `"masaustu_ses_kis": true` — ses yardımcısı toplantı uygulamasının sesini kendi üzerinden
çalar; yardımcı takılırsa toplantı sesi kesilebilir) · `"oda": true` — aynı
mikrofondaki ikinci kişinin sözleri "Odadaki kişi" diye ayrılır. Ses izi hafızasını kapatmak için `"ses_izi_hafiza": false`. Proje veritabanını (tablolar + proje kartı) kapatmak için `"proje_vt": false`.
Claude'un soruya bağlı olmayan SÖYLE/NOT kartları araya dakikada en çok bir kez girer (aynı dakikada gelenler birlikte görünür); aralık
`"kart_tavan_sn"` (varsayılan 60, 0 kapatır).
Karşı taraf adını söyleyince panoda ve şeritte hemen "Adın geçti — kim" (Claude'u beklemeden, yalnız sana); karşı taraf araya girmeden
90 sn'den uzun konuşursan "1,5 dk'dır sen konuşuyorsun". Sana başka adla da hitap ediliyorsa `"lakaplar": ["…"]`. Kapatmak için `"adin_gecti": false`, `"uzun_konusma_sn": 0` (süre de bu ayarla).

## Sesler
Daha doğal Türkçe ses: Piper kuruluysa `"ses_motoru": "piper"`, `"piper_python"` (Piper'ın Python ortamı) ve `"piper_model"` (.onnx Türkçe ses)
— sesli çeviri, fısıltı, sesli özet ve cevaplar bu sesle okunur (Mac'te, yerel); ses dosyası Suflor.me ile gelmez. Hız: `"piper_hiz"`
(varsayılan 1,0), kısa okumalar `"piper_hiz_kisa"` (1,15). Piper yoksa ya da hata verirse Mac sesi.
En doğal yerel Türkçe ses: Pocket TTS (kör dinlemede Piper'dan ve Mac sesinden belirgin iyi; işlemcide çalışır, ilk ses ~0,03 sn, ~1,3 GB bellek).
**Sihirbazdan:** asistan adımında "Kadın sesi" ya da "Erkek sesi" seçilince arka planda kurulur (seçmek indirme onayıdır; varsayılan Mac sesi):
Python paketleri PyPI'dan (`pocket-gereksinim.txt`, sabit sürümler, ~0,9 GB) ve ses modeli Hugging Face'ten (`wite-tech/pocket-tts-turkish`, sabit sürüm,
~0,4 GB); toplam ~1,3 GB, hızlı bağlantıda ~2 dk. Yer: ortak klasörde `pocket-venv` + `pocket-modeller` (Python 3.12, belge çevirmeyle ortak).
Deneme açılışı geçince ayara `pocket_python`, `pocket_hf` ve `ses_motoru: pocket` yazılır; olmazsa asistan Mac sesiyle konuşur, sihirbazda "Yeniden dene"
ya da sonraki güncelleme yeniden dener (günlük: `~/Library/Application Support/Suflor/pocket-kur.log`; elle: `python3 kurulum.py pocket`).
**Elle (başka model ya da ses):** kendi Python ortamına (≥ 3.10: `pip install pocket-tts pocket-tts-turkish`) kurup modelleri bir kez indir: `wite-tech/pocket-tts-turkish`
(3 kadın + 3 erkek hazır ses, duygu etiketi; CC-BY-4.0) ve istersen `alperiox/pocket-tts-turkish` (MIT; hazır sesi yok, wite-tech'in seslerini örnek alır).
Ayar: `"pocket_python"` (o ortamın python'u), `"pocket_hf"` (modellerin indirildiği HF_HOME), `"ses_motoru": "pocket"` ve `"pocket_ses": "wite:female_2"`;
kişilik dosyasında `yerel_ses: pocket:alperiox:female_2` o kişiliğe ayrı ses verir (Gemini toplantıya ayrıldığında da yerel okumalar bu sesle).
Pocket okuyamazsa ya da kurulu değilse Mac sesi (Piper ondan sonra). Ses ve metin Mac'ten çıkmaz; model dosyaları Suflor.me ile gelmez.

En doğal ses (isteğe bağlı, bulut): Gemini TTS. Google AI Studio'dan bir API anahtarı alıp Anahtar Zinciri'ne koy
(`security add-generic-password -a "$USER" -s suflor-gemini -w`; anahtar dosyaya yazılmaz), sonra panoda ⚙ Ayarlar → Ses → Gemini.
11 hazır ses (Gemini sesi) ve model (3.8 Flash-Lite, ilk ses ~0,7 sn; 3.8 Flash) oradan seçilir. Okunacak cevap metni Google'a gider (ses kaydı
gitmez); canlı kullanım için ücretli katman gerekir (ücretsiz katman günde 10 istek; metni eğitimde kullanır). İnternet yoksa Mac sesi okur.
Model başına günde 100 istek var; ayardaki model dolunca öbürüne (Flash-Lite ↔ 3.8 Flash) geçilir, ikisi de dolunca yerel ses okur
(ayar `gemini_yedek_model: false` yalnız seçili model).
Yedek bulut ses (isteğe bağlı): Azure MAI sesi. Gemini okuyamayınca (sınır dolu ya da hata) Elif (kadın Gemini sesleri) ya da Aydın (erkek) okur, o da olmazsa yerel ses.
Azure Speech kaynağının anahtarını Anahtar Zinciri'ne koy (`security add-generic-password -a "$USER" -s suflor-azure-speech -w`), ayara `"azure_yedek": true` yaz;
bölge `azure_bolge` (varsayılan westeurope), ses `azure_ses_kadin` / `azure_ses_erkek`. Duygu biçimi (11: meraklı, heyecanlı, üzgün, ciddi, şefkatli …) cümleye ve Gemini'deki duruma göre seçilir;
kişilik dosyasında `azure_stil: friendlycheerful` o kişiliğin varsayılanı, ayar `azure_stil: false` biçimsiz okur. Okunacak cevap metni Microsoft'a gider (ses kaydı gitmez; Azure anlık
seslendirmede metni saklamaz); ücretsiz katman (F0) sınırda durur, ücret çıkmaz. Gizli toplantıda hiçbir bulut sesi kullanılmaz. Kişilik dosyasında `ses: gemini:Kore`, `ses_uslup: …` (ton yönergesi), `ses_uslup_en: …` (aynı
yönergenin İngilizcesi; Gemini'ye bu gider, Türkçe yönerge ara sıra sesli okunuyor — yoksa Türkçenin ilk cümlesi gider) ve `ses_etiket: evet` (<chuckle> gibi sözsüz sesler) kişiliğe özel ses verir;
toplantıda asistanın cevabı da o kişiliğin Gemini sesiyle okunur. Gemini açıkken sesli çeviri (çevirmen sesi ayar `ceviri_gemini_ses`), fısıltı ve
toplantı özeti de Gemini'yle okunur; iki kişiliğin sesi de Gemini ise özet iki sesle (⚙ Ayarlar → İki sesli özet). Ton cümleye göre değişir (kötü haber,
uyarı, acele); kişilik dosyasında `gerginlik_tonu: evet` o kişiliğin tonunu toplantı gerginliğine göre ayarlatır (karar Claude'da).
⚙ Ayarlar → Toplantıda duyuru (deneme): asistanlar toplantıda konuşurken Suflor toplantı başında kendini tanıtır ve onaylanan işi "Not aldım" diye duyurur.
Kullanım ve maliyet: `canli/gemini-ses.jsonl`.

## Yapay zekâ seçimi
Konuş'taki cevapları, çeviriyi ve proje kartını yazan yapay zekâyı kurulum sihirbazının **Yapay zekâ bağla** adımında seçersin; sonra
⚙ Ayarlar → Genel'den hem genel seçimi (**Yapay zekâ**) hem iş başına seçimi (**Konuş'ta**, **Çeviride**, **Proje kartında**; boş = genel seçimi izler) değiştirirsin.
- **Claude Code** (varsayılan, önerilen): Claude aboneliğinle. Toplantı sırasında kart ve özet yazan oturum şimdilik yalnız bununla çalışır.
- **API anahtarı:** Gemini (Google; model `gemini-3.8-flash`) ya da OpenAI uyumlu başka bir hizmet (adres + model adı). Kullandıkça ücretlendirilir.
  Anahtar yalnız macOS **Anahtar Zinciri**'ne yazılır (öğe `suflor-gemini` — ayar `gemini_anahtar` başka öğe seçer — ya da `suflor-ozel`); ayar dosyasında yalnız öğenin adı,
  hizmetin adresi ve model adı durur. Sihirbaz anahtarı hizmetin model listesini isteyerek dener (metin gitmez).
- **Bu Mac'te yerel model (Ollama):** resmî Ollama sürümü (yalnız komut satırı aracı, ~181 MB; SHA-256 ve Apple imzası denetlenir) ve `qwen3.5:4b-q4_K_M`
  modeli (~3,3 GB) modellerin yerine (`ollama/`) iner. Mac açılışında kendiliğinden başlamaz: aktarıcı, ayar yerel modeli gösterdiği sürece
  sunucuyu `127.0.0.1:11434`'te (ayar `ollama_port`) ve 32 768 belirteçlik bağlamla açar, seçim değişince kapatır; günlük `canli/ollama.log`.
  Yerel model Türkçe belgelerde aramayı çoğu zaman yanlış yapıyor; yedek olarak önerilir. Başka model için ayar `ollama_model`.
- Seçilen hizmet hata verirse ve Claude Code kuruluysa o soru Claude Code'la cevaplanır. Seçilen hizmetin durumu (anahtar var mı, yerel model kurulu mu) ⚙ Ayarlar → Genel'deki Yapay zekâ satırında.
- Ayar dosyasında: `"beyin": {"varsayilan": {…}, "konus": {…}, "ceviri": {…}, "proje_karti": {…}}` — sihirbaz ve pano yazar; elle yazılan model ve `effort` korunur.

## Gizlilik ayrıntıları
- Ses ve döküm **Mac'inden çıkmaz.** Konuşma tanıma yereldir; ses diske yazılmaz.
- Aktarıcı yalnız `127.0.0.1` adresinde çalışır; toplantı içeriğini hiçbir sunucuya göndermez. İstisna isteğe bağlı Gemini sesi: açarsan (⚙ Ayarlar → Ses → Gemini)
  yalnız okunacak metin (cevap, özet, çeviri, fısıltı, duyuru) Google'a gider, ses kaydı gitmez; kapalıyken (varsayılan) sesler Mac'te üretilir.
- **Beta geliştirme verisi:** beta sürümü gönüllü geliştirme katılımıdır. Suflor.me'yi geliştirmek için yalnız sayılar gönderilir (kullanım, hız, hata):
  kurulum adımlarının süresi ve izinler, haftalık kullanım sayıları, toplantı sonu gecikme ve hata sayıları, çağrı ve simge sayısı, seçili ayarlar
  (ses motoru, dil, tema gibi). Konuşmaların, metinlerin ve adların hiçbiri Mac'inden çıkmaz: döküm, kart, soru ve cevap, kişi/toplantı/proje/dosya
  ve asistan adı, e-posta, takvim, ses, ses izi ve ekran görüntüsü gitmez. Kimlik yalnız rastgele bir kurulum numarasıdır. Beta sürümünde kapatılmaz;
  giden her paketin kopyası `~/Library/Application Support/Suflor/teshis/gonderilen/` altında durur.
- Claude'a giden metin, senin Claude Code oturumunun gördükleridir (Anthropic'in kullanım koşulları geçerli).
- **Claude dışında bir sağlayıcı seçersen metin bağlamı o sağlayıcıya gider, ses gitmez; yerel model seçersen metin de Mac'ten çıkmaz.** Metin bağlamı:
  sorun, toplantı dökümünden ve notlardan parçalar, proje belgelerinden aranan parçalar, proje kartı. O hizmetin kullanım koşulları geçerlidir
  (Gemini'nin ücretsiz katmanında Google gönderilen metni ürünlerini geliştirmek için kullanabiliyor; ücretli katman önerilir). Beta verisine yalnız seçeneğin türü girer
  (Claude Code / Gemini / OpenAI uyumlu / yerel); adres, model ve anahtar girmez.
- Toplantı dosyaları senin proje klasöründe durur; kişi adı içerir, iç belge gibi davran.

## Gerekenler
- Apple Silicon (M serisi) işlemcili Mac, macOS 14 ya da üstü
- En az 16 GB bellek (konuşma tanıma ve ses modeli toplantı sırasında ~4 GB kullanır)
- ~12 GB boş disk (modeller ~5 GB, belge çevirme ve anlam araması ~3,3 GB)
- Google Chrome
- [Claude Code](https://claude.com/claude-code) ve bir Claude aboneliği (Pro ya da üstü) önerilir. Claude Code kurulu değilse sihirbaz kurar;
  Terminal'de `claude` → `/login` ile giriş gerekir (Claude masaüstü uygulamasındaki giriş Terminal'e geçmez). Yerine bir API anahtarı ya da
  yerel model seçilebilir ([Yapay zekâ seçimi](#yapay-zekâ-seçimi)); o zaman toplantıdaki kartlar ve özet olmaz, döküm, pano ve Konuş çalışır.
  Claude Code'un oturumu zamanla düşebilir: Suflor.me bunu yarım saatte bir küçük bir denemeyle yoklar; düşünce sesli söyler, bildirim gösterir ve
  Konuş satırında yazar — Terminal'de `claude` → `/login` ile yeniden giriş yeter (yoklamayı kapatmak: ayar `claude_giris_yokla: false`).
- Yerel model seçilirse ~3,5 GB ek disk.

## Bileşenler
| Parça | Ne iş yapar |
|---|---|
| Chrome eklentisi (`manifest.json`, `content.js`, `platform-teams.js`, `platform-meet.js`, `platform-zoom.js`, …) | Teams/Meet/Zoom sayfasından altyazı/döküm ve mikrofon sesini alır, şeridi gösterir |
| Aktarıcı (`relay.py`) | Yerel sunucu: satırları dosyaya yazar, kartları tutar, panoyu sunar |
| Menü çubuğu uygulaması (`menu-cubugu.swift` → `~/Applications/Suflor.me.app`) | Pano penceresi, mini pano paneli, Mac geneli bas-konuş, masaüstü toplantı sinyali |
| Ses yardımcısı (`ses-yardimcisi.swift` → Suflor Ses.app) | Toplantı uygulamasının sesini (karşı taraf) macOS'tan alır; mikrofonu almaz, ses diske yazılmaz |
| Konuşma tanıma (`whisper-isci.py`) | Whisper large-v3-turbo (kurulumda yerelde 8 bite indirilir) ve konuşmacı ses izi (ECAPA), ikisi de MLX ile yerel |
| Toplantıda asistan (`aktarici/toplantiya-ses.py`, `aktarici/otonom.py`, `soyle-main.js`; ⚙ Ayarlar → Asistanlar toplantıda konuşsun, ayar `toplantiya_ses`, varsayılan kapalı) | Toplantıda “<ad>, …” diye seslendiğin asistanın cevabını herkesin duyacağı şekilde okur (söz sırası gelince; “<ad>, dur” ya da Option + Shift + S susturur; sen bir kez çağırdıktan sonra diğer katılımcılar da ona adıyla sorabilir; yalnız sana cevap için Konuş düğmesi): web toplantısında yalnız okuma süresince mikrofon kanalına karıştırır (sessizdeysen okumaz); masaüstü Teams'te BlackHole ile |
| Tur sonu (`tur-isci.py`) | smart-turn v3 (8,7 MB, yerel): konuşurken sözün bitip bitmediğini tahmin eder; kurulamazsa sessizlik süresine bakılır |
| Anlama göre arama (`gomme-isci.py`; `baglam.py gomme`) | multilingual-e5-base (MIT, ~1,1 GB, yerel): sorudaki sözcükler belgede geçmese de anlamca yakın parçaları bulur; sözcük aramasıyla birleştirilir. Arka planda bir sunucu açık kalır (~1 GB bellek), 30 dk sorgu gelmezse kapanır |
| Belge çevirme (`cevir-isci.py`; `baglam.py tara`, `baglam.py cevir`) | Proje klasörünü tarar (kopya, eski sürüm, dışa aktarım, gizli görünen dosya) ve PDF, sunum (PowerPoint, Keynote), Pages, Numbers, eski Excel (.xls) ve görüntüleri Mac'te metne çevirir: Docling + Apple Vision (.xls için xlrd), ayrı Python 3.12 ortamında, ağ kapalı. Eski Word (.doc), .rtf ve .odt macOS'un `textutil` aracıyla, OpenDocument tablo ve sunum (.ods, .odp) doğrudan okunur. Şifre, anahtar, kart ya da IBAN geçen parça aramaya girmez |
| Proje veritabanı (`baglam.py proje-vt`; `<uygulama>/proje.db`) | Excel, Numbers, CSV/TSV sayfaları (`t_…` tabloları; sayı sayı, tarih ISO; kaynak dosyası `tablolar` tablosunda) ve onaylı proje kartı (`kisi`, `kurum`, `karar`, `acik_is`, `olay`, `terim`, `proje`) tek SQLite dosyasında. Konuş ve toplantı oturumu yalnız okuyan SQL ile bakar (`vt_sema`, `vt_sor`; toplantıda `toplanti-claude.py proje`). Yalnız değişen dosya yeniden yazılır; gizli bilgi taşıyan hücre `[gizli]`. Kendi kayıt veritabanın ayarlıysa (`veritabani`) kurulmaz; `"proje_vt": false` kapatır |
| Yapay zekâ katmanı (`aktarici/beyin.py`, `aktarici/saglayici.py`) | Konuş, çeviri, telaffuz ve proje kartının yapay zekâ çağrıları tek yerden: Claude Code ya da OpenAI uyumlu uç (Gemini, OpenAI, Ollama, LM Studio); seçim, Anahtar Zinciri, yerel modeli gerekince açma |
| Ollama (isteğe bağlı, modellerin yerinde `ollama/`) | Yerel model sunucusu; yalnız 127.0.0.1, yalnız yapay zekâ seçimi yerel modeli gösterirken çalışır |
| Claude köprüsü (`toplanti-claude.py`, `baglam.py`, `yapi.py`) | Claude'un izlediği olay akışı, kart gönderme, proje araması, özet araçları |
| Kurallar (`TOPLANTI-KURALLARI.md`, `sablon/`) | Claude'un toplantıdaki davranış kuralları ve `/toplanti` komutu |

## Lisanslar
MIT — ayrıntı [LICENSE](LICENSE).

İsteğe bağlı indirilen bileşenler Suflor.me ile gelmez, kendi lisanslarıyla kullanılır: doğal Türkçe ses modeli
[wite-tech/pocket-tts-turkish](https://huggingface.co/wite-tech/pocket-tts-turkish) (CC-BY-4.0, wite-tech), Pocket TTS (Kyutai, MIT),
pocket-tts-turkish paketi (Apache-2.0); elle kurulursa [alperiox/pocket-tts-turkish](https://huggingface.co/alperiox/pocket-tts-turkish) (MIT).
Yerel model seçilirse [Ollama](https://github.com/ollama/ollama) (MIT) ve qwen3.5 modeli (lisansı Ollama kütüphanesindeki model sayfasında) indirilir.
