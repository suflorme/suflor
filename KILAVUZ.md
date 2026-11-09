# Suflor.me kılavuzu

README'de kısaca anlatılanların ayrıntısı: kurulumdan sonra, kullanım, ayarlar, sesler, gizlilik ve bileşenler.
Ürünün genel tanıtımı için [README](README.md).

- [Kurulumdan sonra](#kurulumdan-sonra)
- [Kullanım](#kullanım)
- [Asistan sohbet paneli ve sesle pano](#asistan-sohbet-paneli-ve-sesle-pano)
- [E-postalar ve Anımsatıcılar](#e-postalar-ve-anımsatıcılar)
- [İsteğe bağlı ayarlar](#isteğe-bağlı-ayarlar)
- [Yapay zekâ seçimi](#yapay-zekâ-seçimi)
- [Sesler](#sesler)
- [Claude'dan arşive erişim](#claudedan-arşive-erişim)
- [Sorun giderme](#sorun-giderme)
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
3. Mac uygulaması açıkken kartlar üç katmanda çıkar (ekran paylaşımında görünmez): **önemli kart** (Söyle, Dur, Cevap, onay) ekranın alt ortasında, tek tek, tam metinle ve sen kapatana kadar kalır; sıradakiler "+2 sırada" diye bekler, ✕ kartı okunmuş sayar. **Bilgi** (not, kalan süre, uzun konuşma uyarısı) sağ altta küçük satır olarak gelir, 10 sn sonra söner (ayar `kart_sure`, ör. `{"bilgi": 15}`). **Yan şerit** ekranın sağ kenarındaki ince çizgidir: okunmamış kart sayısını gösterir, tıklayınca bütün kartlar ve yazı kutusu açılır. Kartlar sürüklenip taşınabilir, çift tıkla yerine döner; uygulama yoksa toplantı ekranının sol altındaki küçük şeritte ve panoda görünür. ✓ yaptım · 👁 okudum · ✕ gerek yok. Kartı "Sonra" (⏸) ile gündemde sıradaki maddeye bırakabilirsin.
4. Toplantıda kutunun üstünde sağda: **Ne diyeyim?** (tek cümlelik replik önerisi), **Kanıt**, **Sessiz** (10 dk kart yok); "⋯" içinde önemli an, gizli toplantı, sesli çeviri.
   Kısayollar: **Option + Shift + K** kanıt · **Option + Shift + O** Ne diyeyim? · **Option + Shift + M** sessiz · **Option + Shift + S** asistan sussun.
   Panonun sağ sütunu toplantıda üç sekmedir: **Döküm** (canlı yazı), **Gündem** (maddeler, kalan süre) ve **Asistan** (o toplantıya özel sohbet).
   Mikrofona basılı tutarken pano "Dinliyorum… 5 sn" diye saniyeyi sayar; bıraktığında gönderilir.
5. Toplantı bitince özet hazırlanır ve sana sunulur.
6. Brifing ve özet panoda **Dışarı aktar** ile PDF, e-posta taslağı (alıcısız, katılımcılara ya da kendine), panoya kopya ya da .md dosyası olur.
   Taslağın açılacağı yeri (Gmail, Outlook web ya da Mac'in posta uygulaması) ve gönderen adresini sihirbazın takvim ekranında seçersin;
   sonradan ayar.json'da `"eposta"` ve `"eposta_adres"`. Seçmezsen takvimine bakılarak seçilir.
   Toplantı sonundaki takip e-postası taslağının üslubu ayar.json'da `"eposta_uslup"` (kısa serbest metin; yoksa sade, samimi ama profesyonel).
   Asistanın hazırladığı e-posta taslakları ([aşağıda](#e-postalar-ve-anımsatıcılar)) de aynı yerde açılır. Mac Mail okuma açıksa (`"eposta_oku": true`) ve taslak tek kişiye gidiyorsa, o kişiye gönderdiğin son iletilerin üslubu örnek alınır (yalnız üslup, içerik değil).

**Saatler:** panoda Bugün başlığındaki "Bugün | Bu hafta | Saatler" seçicisinden (Mac penceresinde kenar çubuğundan) açılır. Eklediğin şehirlerin saati, sana göre farkı ve mesai durumu (gündüz, akşam, gece) görünür; alttaki kaydırıcıyla iki gün içinde bir saat seçince hepsi birlikte değişir, takvimdeki sıradaki toplantı kaydırıcıda halkayla işaretlidir. Arama kutusunun yanındaki seçiciyle liste saate göre (erken → geç ya da tersi), ada göre ya da eklediğin sırayla dizilir (ayar `saatler_sira`). Hesap tarayıcının içinde yapılır, ağa bir şey gitmez; liste ayar.json'da `saatler`.

**Ayarlar:** panonun üst çubuğundaki ⚙ — yapay zekâ seçimi, e-posta, ses ve konuşma, toplantı uyarıları, çeviri ve masaüstü, gizlilik; kaydedince hemen geçerli.

## Kurulumu denetle
Güncellemeden sonra ya da toplantıdan önce "her şey yerinde mi" diye bakmak için. Hiçbir şeyi değiştirmez, yalnız okur ve her madde için ✓ (tamam), ✗ (düzeltilmeli) ya da ? (okunamadı) yazar; ✗ ve ? satırlarının altında tek satırlık "ne yapmalı" gelir.

- **Panodan:** ⚙ Ayarlar → altta "Kurulumu denetle". ✗ olan maddeler listelenir (en çok dakikada bir yenilenir).
- **Terminalden:** `python3 kurulum.py dogrula` (makine okunur çıktı için `--json`; ✗ varsa çıkış kodu 1). Güncelleme bitince bu denetim kendiliğinden çalışır ve kısa özetini yazar.
- **Maddeler:** kod, çalışan aktarıcı, Chrome eklentisi ve Swift yardımcılarının sürümleri tutuyor mu · arka plan ajanı yüklü mü, port cevap veriyor mu · Whisper ve anlam modelleri hazır mı · macOS izinleri (mikrofon, erişilebilirlik, ekran ve sistem sesi kaydı; bildirimler ve Masaüstü erişimi macOS dışarıdan okutmadığı için çoğunlukla "?") · asistan toplantıya sesle konuşacaksa (`toplantiya_ses`) BlackHole kurulu mu ve bir süreç onu okuyor mu (okunamazsa "Teams'te mikrofon BlackHole mu, elle bak") · boş bellek, takas, yük ve öbür hesabın aktarıcısı · varsayılandan farklı ayarların adları.
- **Ne yazılır:** sonuç uygulama klasöründeki `dogrula.json`'a gider. Beta kullanıcısında ayrıca ortak `geri-bildirim` klasörüne (`<tarih>-dogrula-<hesap>.md`) yazılır; geliştirici o dosyayı okuyabilir. Dosya yalnız sayı, durum ve ayar adı içerir: kişi, toplantı, proje ya da dosya adı, yol ve ayar değeri yazılmaz. Ağa hiçbir şey gitmez.

Toplantı sürerken 60 saniye hiçbir kanaldan (altyazı, sen, karşı taraf) satır gelmezse pano sarı uyarı gösterir: "Toplantı sürüyor ama 60 sn'dir döküm gelmiyor", yanında kanalların durumu. Satır gelince uyarı kendiliğinden kalkar.

## Deneme toplantısı
Önemli bir toplantıdan önce kısa bir toplantıya girip (ya da toplantı başında) "her şey gerçekten akıyor mu" diye bakmak için. **Toplantıya girdikten sonra** ⚙ Ayarlar → "Deneme toplantısı (3 dk)" düğmesine bas; en çok 3 dakika süren bir liste açılır, maddeler canlı ✓ (tamam), ✗ (olmadı), ? (ölçülemedi) ya da … (bekleniyor) olur. Toplantı yoksa başlamaz ("önce toplantıya gir"). Aynı anda tek deneme çalışır; "Bitir" erken kapatır.

- **Maddeler:** toplantı tanındı mı (platform ve adın kaynağı: takvim, Başlat ya da sinyal) · döküm dosyası açıldı mı · altyazı, sen ve karşı taraf kanallarından 30 saniyede en az bir satır geldi mi (kanal kurulu ya da açık değilse "?" ve nedeni) · Claude toplantı oturumu açık mı, açılışta kaç izin kartı çıktı · asistana sorduğun kısa soruya 60 saniyede cevap geldi mi, ilk metin kaç saniyede · asistan toplantıya sesle konuşacaksa (`toplantiya_ses`) BlackHole okunuyor mu · Mac kaynakları (takas, yük; "Kurulumu denetle"yle aynı eşikler).
- **Senin yapacakların:** bir-iki cümle konuş, karşı tarafın da konuşmasını bekle, asistana kısa bir soru sor. Deneme asistanı kendisi konuşturmaz.
- **Toplantıya dokunmaz:** döküme not düşmez, toplantıya bir şey yazmaz; yalnız okur ve ölçer.
- **Bitince:** panoda tek satırlık özet çıkar ("Meet: 6/7 geçti — karşı taraf satırı gelmedi"). Sonuç uygulama klasöründe `duman/<tarih>.json` dosyasına yazılır; beta kullanıcısında ayrıca ortak `geri-bildirim` klasörüne `<tarih>-duman-<platform>-<hesap>.md` yazılır. Dosyalar yalnız sayı, durum, süre ve platform içerir: toplantı, kişi ya da dosya adı, döküm metni ve yol yazılmaz; ad için yalnız kaynağı ("takvim", "Başlat", "sinyal") yazılır. Ağa hiçbir şey gitmez.

## Asistan sohbet paneli ve sesle pano
**Sohbet paneli:** panonun üst çubuğundaki **Asistan sohbeti** düğmesi, asistanla yazışılan paneli açar (Esc kapatır). Geniş ekranda panonun sağında ayrı bir sütun olarak durur ve
pano içeriğini üstüne kaydırmaz; dar ekranda panonun üstüne katman olarak biner. Panelin sol kenarından sürükleyerek genişliği ayarlarsın, çift tıklayınca varsayılan genişliğe döner.
Sohbet kutusundaki 🔊 düğmesi açıkken asistanın cevabı yazılı olduğu gibi sesli de okunur; kapatınca yalnız yazılı gelir.

**Sesle pano:** "kararları göster", "işleri aç", "takvimi göster" gibi bir istekte pano açılır ve ilgili bölüme kayar. Mikrofona basılı tutarken ya da eller serbest sohbette üstte "Dinliyorum… n sn" göstergesi çıkar.
**Sesle gündem ve toplantı:** "gündeme ekle: bütçe" ilgili toplantının gündemine madde ekler. "Toplantıyı başlat" ve "toplantıyı bitir" toplantıyı açar ya da kapatır; bitirme toplantıyı kapattığı için asistan önce sorar ve yalnız sesli "evet"i bekler.

## E-postalar ve Anımsatıcılar
**E-posta takibi (ayar `eposta_takip`, varsayılan açık; Mac Mail okuma `eposta_oku` da açık olmalı):** panoda **E-postalar** bölümü üç grupta gelir: **Senden cevap bekleyenler**, **Dönüş beklediklerin**
(sen yazdın, karşıdan cevap yok) ve **yalnız bilgi** olanlar (bilgiye eklendiğin, toplu ve otomatik iletiler; yalnız sayısı görünür). Önemli saymadan önce yapay zekâ zinciri baştan sona okur:
başkası cevaplamışsa ya da iş kapanmışsa ileti listeden düşer. Değerlendirilemeyen iletinin yanında "Değerlendirilmedi" yazar. Düşük öncelikli iletiler katlı bir satırda toplanır
("Düşük öncelikli (n)"); tıklayınca açılır. Her satırın "⋯" menüsünde **Bu kişi önemli** ve **Bu gönderen önemsiz** vardır; seçimin ileride benzer iletilere uygulanır.
Ayarlar (⚙ Ayarlar → Takvim ve e-posta): `eposta_onem_duzeyi` (`siki`: yalnız önemli kişiler ve en acil istekler · `dengeli`, varsayılan: tanıdığın kişilerden gelen somut istekler · `genis`: tanımadıkların da girer),
`eposta_onem_gun` (kaç günlük ileti, 14), `eposta_vip` (her zaman önemli sayılan kişiler; "Bu kişi önemli" buraya ekler), `eposta_onemsiz` (önemsiz gönderenler; "Bu gönderen önemsiz" buraya ekler).

**Asistanın e-posta ve mesaj taslağı:** asistana "Ayşe'ye cevap hazırla" ya da bir iş ya da karar sahibine "hatırlat" dersen asistan taslak yazar ve panoda onayına sunar. Onaylamadan taslak açılmaz,
hiçbir ileti kendiliğinden gönderilmez; **Gönder'e her zaman sen basarsın.** Taslak ayar `eposta_taslak_yeri` ile `mac` (Mac'in Mail uygulaması, varsayılan: Mail okuma açıksa) ya da `web` (seçtiğin web posta hizmeti) olarak açılır.
Kayıtta adı geçen kişiye (iş sahibi, karar sahibi) e-posta ya da Teams mesajı taslağı da hazırlanabilir; hiçbiri kendiliğinden gitmez.

**Mac Anımsatıcılar eşitlemesi (ayar `animsatici`, varsayılan kapalı):** açarsan Kararlar ve işler'deki kendi işlerin Mac'in Anımsatıcılar uygulamasında `animsatici_liste` adlı listeye
(varsayılan "Suflor.me"; yoksa açılır) anımsatıcı olarak eklenir: başlık iş metni, son tarih varsa bitiş tarihi, notta toplantı adı. Anımsatıcılar'da işi tamamlarsan birkaç dakika içinde Suflor'da da "yapıldı" olur,
Suflor'da bitirirsen anımsatıcı tamamlanır; yeniden açma da iki yöne işler. Anımsatıcıyı silersen iş silinmez, yalnız bir daha eklenmez. Yalnız senin işlerin gider; başkasına atanan işler, karar ve döküm gitmez.
**Gizli toplantının işleri hiç gönderilmez**; gizli kip açıkken eşitleme durur. Anımsatıcılar bulut hesabına (iCloud, Exchange) eşitliyorsa orada da görünür; bunu bilerek aç.
Açmak için ⚙ Ayarlar'dan; macOS ilk seferde Anımsatıcılar izni sorar.

## İsteğe bağlı ayarlar
**Sesle hatırlatma:** onayladığın saatli hatırlatma Mac Takvim'in varsayılan takvimine 15 dakikalık, başında uyaran bir etkinlik olarak eklenir
(Exchange/Google takvimiyse telefonuna da eşitlenir); başka bir takvim için `"hatirlatma_takvim": "<takvim adı>"`. Saati olmayan istek kendine e-posta taslağı olur.

**Sesle toplantı:** "yarın on ikide Deniz'le toplantı koy" gibi başka biriyle toplantı isteği hatırlatma değil toplantı olur. Onaylayınca takviminde
yeni toplantı sayfası açılır: başlık, saat, süre (söylenmezse 30 dk) ve davetliler dolu, Google'da Meet bağlantısıyla. Sen Kaydet'e basarsın. Davetlinin
adresi söylediğin e-postadan ya da son 30 günün takvim toplantılarından bulunur; bulunamayan ad sayfadaki notta yazar. Ayar `eposta` Outlook ise Outlook takvimi açılır.

**Paylaşılan takvimler:** Takvim'ine başkalarının paylaşılan takvimleri de eklenmişse (Google'dan eklenen bir iş arkadaşının takvimi gibi), Suflor bunlardaki toplantıları senin toplantın saymaz: Konuş, brifing ve toplantıyı kendiliğinden tanıma onlara bakmaz. Bu takvimleri panoda yine de görmek istersen Ayarlar → Toplantı → "Panoda gösterilecek paylaşılan takvimler" listesinden işaretle (ayar.json'da `"takvim_paylasilan": ["<takvim adı> · <hesap>"]`). Pano bu toplantıları soluk, kesikli bir blok olarak gösterir; Hazırla yoktur, Başlat vardır. Takvim 62 gün ileri okunur (pano hafta ve ay görünümü); Konuş ve brifing yine 30 günü görür.

**Menü çubuğu uygulaması (varsayılan açık; kapatmak için ayar.json'da `"menu_cubugu": false`):** pano Mac penceresinde açılır; menü çubuğu uygulaması (buzlu cam panelde yazı kutusu, mikrofon ve Claude'un durumu; kartlar ekranın alt ortasında ayrı kutularda,
Mac genelinde **Option + Shift + Boşluk** basılı tut-konuş ve yukarıdaki kısayollar, Teams/Zoom masaüstü toplantılarında da
çalışma: toplantıyı ve sessizi tanır, senin mikrofonunu ve karşı tarafın sesini yazar, kanıt ve
paylaşılan ekran görüntüsünü toplantı penceresinden alır; Erişilebilirlik, mikrofon ve Ekran Kaydı izni sorar (ayarı değiştirdiysen sonra `guncelle.command`).
Uygulama `~/Applications/Suflor.me.app`'e kurulur (hesaba özel): Launchpad'de, Spotlight'ta ve Finder'daki Uygulamalar'da Suflor.me adıyla
bulunur; açıkken simgesine tıklamak pano penceresini öne getirir.
Kapatmak için `"masaustu_mic": false`, `"kisayollar": false`; Kişiler panelinden ad okuma `"masaustu_kisiler": true` ile açılır — panel
3 dakikada bir açılıp kapanır, Teams penceresi öne gelir) · `"fisilti": true` — kulaklık takılıyken DUR kartı kısa sesle kulağına okunur ·
`"ceviri": true` — karşı tarafın İngilizce satırları panoda Türkçesiyle (metin Claude'a gider; 🎧 sesli çeviride toplantı sesi tarayıcıda
kısılır, masaüstü Teams/Zoom'da kısmak için ayrıca `"masaustu_ses_kis": true` — ses yardımcısı toplantı uygulamasının sesini kendi üzerinden
çalar; yardımcı takılırsa toplantı sesi kesilebilir; 🎧 kulaklığa her satırın kısa özü okunur, `"sesli_ceviri_tam": true` ile tam çeviri) · `"oda": true` — aynı
mikrofondaki ikinci kişinin sözleri "Odadaki kişi" diye ayrılır. Ses izi hafızasını kapatmak için `"ses_izi_hafiza": false`. Proje veritabanını (tablolar + proje kartı) kapatmak için `"proje_vt": false`.
Claude'un soruya bağlı olmayan SÖYLE/NOT kartları araya dakikada en çok bir kez girer (aynı dakikada gelenler birlikte görünür); aralık
`"kart_tavan_sn"` (varsayılan 60, 0 kapatır).
Karşı taraf adını söyleyince panoda ve şeritte hemen "Adın geçti — kim" (Claude'u beklemeden, yalnız sana); karşı taraf araya girmeden
90 sn'den uzun konuşursan "1,5 dk'dır sen konuşuyorsun". Sana başka adla da hitap ediliyorsa `"lakaplar": ["…"]`. Kapatmak için `"adin_gecti": false`, `"uzun_konusma_sn": 0` (süre de bu ayarla).

**Toplantıda dış bilgi kaynağı (varsayılan kapalı):** Claude Code'da bağlı bir MCP bağlayıcısı (ör. pazarlama ya da satış metrikleri) toplantıda konuşulan konuya
güncel rakam getirsin istersen: `"toplanti_bilgi_kaynaklari": [{"sunucu": "<bağlayıcının claude mcp list'teki adı>", "araclar": ["get_*", "list_*", "query_*", "compare_*"],
"konu": "<kısa tarif>", "ad": "<kartta görünecek kaynak adı>"}]`. Panodan başlatılan toplantı oturumunda o bağlayıcının yalnız okuma adlı araçları
(get_, list_, query_, compare_ … ile başlayan ve listedeki desene uyan) sorulmadan çalışır (toplantı başına en çok 8; sonrası sorulur); aynı bağlayıcının öbür araçları
reddedilir, başka bağlayıcılar eskisi gibi sorulur. Sonuç kısa bir NOT kartı olur ("Kaynak: <ad>, <saat>"); asistan sesli söylemez.
Kaynağa `"url": "<bağlayıcının https adresi>"` da yazarsan Konuş da (yalnız Claude Code'da) aynı okuma araçlarıyla o kaynaktan cevap verir ve rakamı
kaynağı ve dönemiyle söyler ("<ad>'a göre son 7 günde …"); Konuş'a yalnız bu bağlayıcı yüklenir. Gizli toplantıda kullanılmaz; bağlanamazsa 30 dk kaynaksız
devam eder. Toplantı öncesi brifing de aynı kaynağa bakar: toplantının konusu kaynağın konusuna giriyorsa brifinge kaynağı ve dönemiyle en çok üç rakam
ekler ("Güncel veri"); konu dışıysa kaynağa sormaz. Kaynaklı brifing bağlayıcının bağlanmasını beklediği için birkaç saniye uzun sürer.
İkisini birden kapatmak için `"konus_bilgi_kaynagi": false`.
Konuş'ta web araması (`"konus_web"`, varsayılan açık; `web_arastirma` ana şalteri de açık olmalı, toplantı dışında `web_arastirma_disari` da; Ayarlar → Toplantı → "Konuş'ta da web'de araştır"): sesle ya da yazıyla sorduğun
kişi, firma ve güncel bilgi sorularında Konuş internette arar ve herkese açık sayfaları ya da senin verdiğin bağlantıyı okur; Aramaya yalnız sorudaki konu gider, döküm alıntısı ve iç sayılar gitmez; gizli toplantıda
kapalı. Kapatmak için `"konus_web": false`. Suflor Brifing yardımcısının web araçlarını tanıyan sürümü gerekir; eski sürümde ayar açık olsa da Konuş internete çıkmaz (günlükte tek satır uyarı).

**Toplantı dışında derin web araştırması (`"web_arastirma_disari": true`, varsayılan açık; `web_arastirma` ana şalterdir, kapalıysa bu da kapanır):** Konuş'ta ya da pano kutusunda "X'i araştır", "şu firma hakkında ne biliniyor", "dünkü olay ne" dediğinde ayrı bir araştırma çalışır: birden çok arama sorgusu, bulunan sayfaların açılması, en az 3 bağımsız kaynak, resmî/birincil kaynak tercihi, çelişkilerin ve doğrulanamayan bilginin ayrı işaretlenmesi, her iddiada bağlantı ve tarih. Sonuç kısa bir sesli özet olarak okunur (yazıyla sorduysan yalnız yazılır); kaynaklı tam metin panoda "---" sonrasında ve `canli/arastirma/` altında (.json ve .md) durur. 15 saniyeden uzun sürerse kısa bir bekleme cümlesi söylenir. Aramaya yalnız ad ve konu gider (kişiyse Kişiler'deki kurum adı ayırt edici olarak); döküm alıntısı, iç sayılar, e-posta/telefon ve geçmiş toplantı bilgisi gitmez, yerel bilgi yalnız kayda sonradan eklenir. Toplantı sürerken, gizli kipte ve sağlayıcı Claude Code değilken çalışmaz. Süre ve maliyet `olcum.py maliyet`te görünür.

**Süreli ses arşivi (`"ses_arsivi": true`, varsayılan kapalı):** Whisper'a giden her ses parçası sonucuyla birlikte `canli/ses-arsivi/<toplantı>/` altına (WAV + `parcalar.jsonl`) yazılır; eşik, mikrofon ve uydurma kurallarını gerçek veriyle ayarlamak içindir. Ses yalnız bu Mac'te kalır: ağa, geri bildirime, teşhis paketine ve Time Machine'e girmez.
**`"ses_arsivi_tam"` (yalnız geliştirici kurulumu; `ses_arsivi` açıkken varsayılan açık, `false` kapatır):** toplantının ham sesi kanal başına (ben, karşı) sessizlik dahil kesintisiz `tam-ben` ve `tam-karsi` olarak aynı toplantı klasörüne yazılır; iki kayıt duvar saatiyle hizalıdır, başlangıç anı `tam.json`'dadır. Toplantı bitince AAC `.m4a`'ya çevrilir ve wav silinir (`"ses_arsivi_tam_m4a": false` wav'ı bırakır; wav saatte ~115 MB/kanal). Gizli toplantıda ve toplantı dışında kayıt yok; ağa, teşhis paketine ve arşiv aramasına girmez. Aynı klasörde kayıt yeniden açılırsa (aktarıcı yeniden başlar ya da 60 sn ses kesilir) var olan dosyaya dokunulmaz, yeni bölüm `tam-2-ben`, `tam-2-karsi`, `tam-2.json` adıyla (her birinin kendi `t0`'ı) açılır.
**`"ses_arsivi_gun": 14`:** arşivin saklama süresi (gün); süresi geçen toplantı klasörleri silinir, toplam boyut 5 GB'ı aşarsa en eskiden silinir. Kapatınca eski kayıtlar da süresi dolunca silinir.
**`"ses_arsivi_egitim": true` (varsayılan kapalı):** arşivden süresi dolan ya da boyut sınırı yüzünden atılacak toplantı klasörleri silinmek yerine `canli/egitim-havuzu/<klasör>` altına taşınır (Whisper ince ayarı için gerçek toplantı sesi biriktirmek; yalnız yerel, ağa hiçbir şey gitmez; Time Machine'e girmez). Ad çakışırsa sonuna `-2`, `-3` eklenir.
**`"golge_tstt": true` (geliştirici denemesi, varsayılan kapalı):** canlı toplantıda Whisper'a giden ses yerel turkish-stt akış tanıyıcısına da verilir; ekranda, dökümde ve kartlarda hiçbir şey görünmez, yalnız ses arşivi klasörüne `tstt-golge.jsonl` yazılır (gecikme ve sözcük farkı kayıttan ölçülür). Ayrıca kurulmuş turkish-stt ister (ortak klasörde `tstt-venv` ve `tstt-model`); gizli toplantıda çalışmaz, 10 dk ses gelmezse işçi kapanır. Ses yalnız bu Mac'te kalır.
**`"tstt_python"`, `"tstt_model"`:** gölge kipin Python'u ve model klasörü (varsayılan: ortak klasördeki `tstt-venv/bin/python` ve `tstt-model`).
**`"ses_arsivi_egitim_gb": 50`:** havuzun boyut sınırı; aşılacaksa klasör taşınmaz, eskisi gibi silinir (günlüğe bir kez yazılır). Havuzdaki eski veri kendiliğinden silinmez, yalnız elle temizlenir.

## Sesler
Doğal yerel Türkçe ses: Pocket TTS (kör dinlemede Mac sesinden belirgin iyi; işlemcide çalışır, ilk ses ~0,03 sn, ~1,3 GB bellek).
**Sihirbazdan:** asistan adımında "Kadın sesi" ya da "Erkek sesi" seçilince arka planda kurulur (seçmek indirme onayıdır; varsayılan Mac sesi):
Python paketleri PyPI'dan (`pocket-gereksinim.txt`, sabit sürümler, ~0,9 GB) ve ses modeli Hugging Face'ten (`wite-tech/pocket-tts-turkish`, sabit sürüm,
~0,4 GB); toplam ~1,3 GB, hızlı bağlantıda ~2 dk. Yer: ortak klasörde `pocket-venv` + `pocket-modeller` (Python 3.12, belge çevirmeyle ortak).
Deneme açılışı geçince ayara `pocket_python`, `pocket_hf` ve `ses_motoru: pocket` yazılır; olmazsa asistan Mac sesiyle konuşur, sihirbazda "Yeniden dene"
ya da sonraki güncelleme yeniden dener (günlük: `~/Library/Application Support/Suflor/pocket-kur.log`; elle: `python3 kurulum.py pocket`).
**Elle (başka model ya da ses):** kendi Python ortamına (≥ 3.10: `pip install pocket-tts pocket-tts-turkish`) kurup modelleri bir kez indir: `wite-tech/pocket-tts-turkish`
(3 kadın + 3 erkek hazır ses, duygu etiketi; CC-BY-4.0) ve istersen `alperiox/pocket-tts-turkish` (MIT; hazır sesi yok, wite-tech'in seslerini örnek alır).
Ayar: `"pocket_python"` (o ortamın python'u), `"pocket_hf"` (modellerin indirildiği HF_HOME), `"ses_motoru": "pocket"` ve `"pocket_ses": "wite:female_2"`;
kişilik dosyasında `yerel_ses: pocket:alperiox:female_2` o kişiliğe ayrı ses verir (Gemini toplantıya ayrıldığında da yerel okumalar bu sesle).
Pocket okuyamazsa ya da kurulu değilse Mac sesi. Ses ve metin Mac'ten çıkmaz; model dosyaları Suflor.me ile gelmez.

En doğal ses (isteğe bağlı, bulut): Gemini TTS. Google AI Studio'dan bir API anahtarı alıp Anahtar Zinciri'ne koy
(`security add-generic-password -a "$USER" -s suflor-gemini -w`; anahtar dosyaya yazılmaz), sonra panoda ⚙ Ayarlar → Ses → Gemini.
11 hazır ses (Gemini sesi) ve model (3.8 Flash-Lite, ilk ses ~0,7 sn; 3.8 Flash) oradan seçilir. Okunacak cevap metni Google'a gider (ses kaydı
gitmez); canlı kullanım için ücretli katman gerekir (ücretsiz katman günde 10 istek; metni eğitimde kullanır). İnternet yoksa Mac sesi okur.
Model başına günde 100 istek var; ayardaki model dolunca öbürüne (Flash-Lite ↔ 3.8 Flash) geçilir, ikisi de dolunca yerel ses okur
(ayar `gemini_yedek_model: false` yalnız seçili model).
Gizli toplantıda hiçbir bulut sesi kullanılmaz. Kişilik dosyasında `ses: gemini:Kore`, `ses_uslup: …` (ton yönergesi), `ses_uslup_en: …` (aynı
yönergenin İngilizcesi; Gemini'ye bu gider, Türkçe yönerge ara sıra sesli okunuyor — yoksa Türkçenin ilk cümlesi gider) ve `ses_etiket: evet` (<chuckle> gibi sözsüz sesler) kişiliğe özel ses verir;
toplantıda asistanın cevabı da o kişiliğin Gemini sesiyle okunur. Gemini açıkken sesli çeviri (çevirmen sesi ayar `ceviri_gemini_ses`), fısıltı ve
toplantı özeti de Gemini'yle okunur; iki kişiliğin sesi de Gemini ise özet iki sesle (⚙ Ayarlar → İki sesli özet). Ton cümleye göre değişir (kötü haber,
uyarı, acele); kişilik dosyasında `gerginlik_tonu: evet` o kişiliğin tonunu toplantı gerginliğine göre ayarlatır (karar Claude'da).
⚙ Ayarlar → Toplantıda duyuru (deneme): asistanlar toplantıda konuşurken Suflor toplantı başında kendini tanıtır ve onaylanan işi "Not aldım" diye duyurur.
Kullanım ve maliyet: `canli/gemini-ses.jsonl`.
Kişilik dosyasında `gorev_cikar: evet`: kişisel asistan hitapsız söylenen işi ve toplantıda sahipsiz kalan işi öneri olarak sunar (toplantıda onay kartı, dışında "ekleyeyim mi?"); varsayılan kapalı.

## Yapay zekâ seçimi
Konuş'taki cevapları, çeviriyi ve proje kartını yazan yapay zekâyı kurulum sihirbazının **Yapay zekâ bağla** adımında seçersin; sonra
⚙ Ayarlar → Genel'den hem genel seçimi (**Yapay zekâ**) hem iş başına seçimi (**Konuş'ta**, **Çeviride**, **Proje kartında**; boş = genel seçimi izler) değiştirirsin.
- **Claude Code** (varsayılan, önerilen): Claude aboneliğinle. Toplantı sırasında kart ve özet yazan oturum şimdilik yalnız bununla çalışır.
- **API anahtarı:** Gemini (Google; model `gemini-3.8-flash`) ya da OpenAI uyumlu başka bir hizmet (adres + model adı). Kullandıkça ücretlendirilir.
  Anahtar yalnız macOS **Anahtar Zinciri**'ne yazılır (öğe `suflor-gemini` — ayar `gemini_anahtar` başka öğe seçer — ya da `suflor-ozel`); ayar dosyasında yalnız öğenin adı,
  hizmetin adresi ve model adı durur. Sihirbaz anahtarı hizmetin model listesini isteyerek dener (metin gitmez).
- Seçilen hizmet hata verirse ve Claude Code kuruluysa o soru Claude Code'la cevaplanır. Seçilen hizmetin durumu (anahtar var mı) ⚙ Ayarlar → Genel'deki Yapay zekâ satırında.
- Ayar dosyasında: `"beyin": {"varsayilan": {…}, "konus": {…}, "ceviri": {…}, "proje_karti": {…}}` — sihirbaz ve pano yazar; elle yazılan model ve `effort` korunur.

## Yaklaşan kişisel tarihler
Suflor.me, Mac'in Kişiler'indeki doğum günlerini ve yıldönümlerini, Takvim'in Doğum Günleri takvimini, sesle eklediğin hatırlatmaları ve Anımsatıcılar'daki tarihli işleri yalnız okur (hiçbirini değiştirmez, Mac'ten çıkarmaz). Bir gün önce ve günün sabahı bildirim verir; toplantıdayken ya da gizli kipteyken vermez. "Bu hafta kimin doğum günü var" ya da "yarın neyi unutmamalıyım" diye sorabilir, "Ayşe'nin doğum gününü hatırlat" diyebilirsin (onayınla takvime eklenir). Doğum gününde kutlama taslağı e-posta ya da Teams sohbeti olarak açılır; göndermek sana kalır. İzinler ilk kullanımda ayrı ayrı sorulur (Kişiler, Takvim, Anımsatıcılar); biri verilmezse öbürleri yine okunur.
Ayarlar (`ayar.json`): `kisisel_tarihler` (açık), `kisisel_tarih_ufuk` (kaç gün ilerisi, 14), `kisisel_tarih_hatirlat` (bildirim, açık), `kisisel_tarih_sesli` (kısa sesli okuma, kapalı), `kisisel_tarih_saat` (sabah hatırlatma saati, 09:00), `kutlama_kanali` (`eposta` ya da `teams`).

## Claude'dan arşive erişim
`arsiv-mcp.py`, toplantı arşivini Claude Desktop ya da Claude Code'a araç olarak açan yerel bir MCP sunucusudur (Model Context Protocol). Yalnız bu Mac'te,
standart girdi/çıktı (stdio) üzerinden çalışır; ağ portu açmaz, ek paket istemez (Python 3.9). Suflor.me açık olmalı: listeleme, arama ve döküm aktarıcının yerel
uçlarından, kararlar ve işler kararlar grafından gelir. Gizli toplantılar hiçbir araçta görünmez.

Araçlar: `toplanti_ara`, `toplanti_listesi`, `toplanti_ozeti`, `toplanti_dokumu` (sayfalı), `kararlar`, `isler` (kişiye, duruma göre), `acik_sorular`; yazma:
`is_durumu` (yapıldı / yapılmadı), `karar_onayla`, `karar_duzelt`. Yazma araçları ilk çağrıda yalnız ne yapacaklarını söyler (`onay_gerekli`); kullanıcı onaylarsa
`onayla: true` ile uygulanır.

Claude Code: `claude mcp add suflor-arsiv -- python3 -B <SUFLOR-KLASÖRÜ>/arsiv-mcp.py`

Claude Desktop (`claude_desktop_config.json`):
```json
{ "mcpServers": { "suflor-arsiv": { "command": "python3", "args": ["-B", "<SUFLOR-KLASÖRÜ>/arsiv-mcp.py"] } } }
```
Ayar dosyasından (`~/Library/Application Support/Suflor/ayar.json`) port ve veri klasörü okunur; farklıysa `--dir <canlı klasör>` ve `--relay http://127.0.0.1:<port>` eklenir.
Test: `PYTHONDONTWRITEBYTECODE=1 python3 test/arsiv-mcp.py`.

## Başka bir karar kaydı
Firmada başka bir karar ya da toplantı defteri kullanılıyorsa Suflor.me onu okur, ona yazmaz. ⚙ Ayarlar → Dış karar kaydı (ayar `dis_defter`) iki tür alır:
- **Dosya:** o defterden dışa aktarılmış CSV ya da JSON dosyasının yolu (başlık satırı: tarih, toplantı, tür, metin/karar/iş, sahip, vade, durum; İngilizce adlar da
  tanınır). Kararlar ve işler Bugün'de ve toplantı hazırlığında (`tc hazirlik`) kaynak etiketiyle, yalnız okunur olarak görünür; Suflor'un kendi kayıtlarına karışmaz.
  Kapalı kayıtlar (done, kapandı, iptal …) listelenmez.
- **Bağlayıcı:** defterin MCP bağlayıcısı (sunucu adı, https adresi, okuma araçlarının deseni). Toplantı oturumu ve Konuş bu kaynağı yalnız okuma araçlarıyla
  sorgular; sorguya kişi adı ve döküm alıntısı girmez (Dış bilgi kaynağı kuralı). Yazan ya da değiştiren araç kullanılmaz.

Suflor'un kararlarını ve işlerini o deftere taşımak için Bugün'de "Kararları ve işleri dışa aktar" (CSV ya da JSON; alanlar: tarih, toplantı, tür, metin, sahip,
vade, durum, kaynak saat). Dosya `<canlı klasör>/disa-aktar/` altına yazılır ve Finder'da gösterilir; yüklemeyi sen yaparsın. Gizli toplantıların kaydı girmez.
Test: `PYTHONDONTWRITEBYTECODE=1 python3 test/dis-defter.py`.

## Ekiple paylaşım (kararlar ve işler)
İki-üç kişi aynı kararları ve işleri görsün diye Google'ın bulut veritabanı Firestore kullanılır (Drive klasörü eşitlemesi kaldırıldı). Ayar `"ortak_tasima": "firestore"` değilse özellik kapalıdır, hiçbir şey gönderilmez.
- **Ne gider:** yalnız karar ve iş kayıtlarının değişiklikleri (oluşturma, durum, onay, atama, vade, metin düzeltme, gündem, yorum). Toplantı dökümü, kartlar, not, Claude'un hazırlık notu ve taslaklar gitmez.
  **Gizli ve deneme toplantılarının kayıtları hiç yazılmaz** (yazma anında yeniden denetlenir). Ayar açılmadan önceki kayıtlar da gitmez; isteyen ayar dosyasına `"ortak_gecmis": true` yazar.
- **Kimlik:** şirket e-postan (ayar `eposta_kimlik`, yoksa `eposta_adres` ya da takvim adresin). Kişisel posta adresiyle (Gmail, iCloud …) özellik açılmaz.
- **Görünüm:** başkasının kararları ve işleri Kararlar ve işler'de görünür; sana atanan iş listede ve Bugün'de **"Sana atandı · <kişi>"** diye çıkar (son 7 günde atananlar Bugün'de vadesine bakılmadan görünür).
  Kayıtta rolü olmayan birinin değişikliği (ör. başkasının kararının metnini düzeltmek) uygulanmaz, tarihçede "uygulanmadı" diye görünür.
- Durum: `/ortak` (anahtarlı; yazılan, alınan, uygulanmayan değişiklikler).

### Firestore ile paylaşım (kişiye göre okuma, saniyelik eşitleme)
Olaylar ve süzgeç yukarıdakiyle aynı;
fark: **bir kaydın olaylarını yalnız o kayıtta rolü olanlar (sahip, isteyen, onaylayan, bilgi) görür**, her kullanıcı yalnız kendi adına yazar, kimse silemez —
bunu Firestore güvenlik kuralları sunucuda sağlar. Sonradan role eklenen kişi kaydın geçmişini de görür. Pano açıkken ya da toplantıda 5 sn'de, diğer zamanda 30 sn'de bir eşitlenir.
- **Kurulum (ekipte bir kişi, bir kez):** Firebase'de proje + Google girişi açık + Google Cloud'da masaüstü OAuth istemcisi (sırrı Anahtar Zinciri'nde
  `security add-generic-password -a suflor -s suflor-firestore-istemci-sirri -U -w`), sonra
  `python3 -B ortak_bulut.py kur --proje <proje> --istemci <istemci kimliği> --alan <şirket alan adı> [--alan <ikinci alan adı>]`: veritabanını, dizini, kuralları kurar,
  kuralları Google'ın sınama aracıyla dener, web API anahtarını alır, ayarı yazar ve seni giriş yaptırır. Yönetici izni saklanmaz; yeniden çalıştırmak güvenlidir (alan adı eklemek için de).
- **Ekibe katılma:** kuran kişi `python3 -B ortak_bulut.py davet` ile tek satırlık kod üretir ve özel mesajla gönderir; katılan `python3 -B ortak_bulut.py katil <kod>` çalıştırıp
  şirket hesabıyla bir kez girer. Yenileme belirteci ve anahtarlar yalnız Anahtar Zinciri'nde.
- **Durum:** `python3 -B ortak_bulut.py durum` ya da `/ortak` (`tasima`, giriş, son eşitleme, gecikme ortanca/p90). İzinli alan adı dışındaki ya da kişisel posta hesabıyla bağlanılmaz.
  Panoda Kararlar ve işler başlığının altında tek satır: iyiyse "Ekiple paylaşılıyor · son eşitleme · gecikme", sorun varsa ne yapılacağı (giriş gerekiyor, şirket e-postası gerekiyor, ağ yok, hesap uyuşmuyor).
Test: `PYTHONDONTWRITEBYTECODE=1 python3 test/firestore.py` (sahte sunucu; ağa çıkmaz).

### Asistanın kayıt yazması ve projenin kendi kayıt aracı
Asistan (Konuş ya da kutu) kayıtta değişiklik önerir, her yazmayı panoda tek tıkla onaylarsın. Masaüstü'ndeki dosyalara aktarıcı erişemediği için o kısmı
Masaüstü izni olan Suflor Brifing yardımcısı yapar (tek kullanımlık, imzalı, iki dakika geçerli iş dosyasıyla; Claude çalıştırmaz):
- **Asıl özet dosyası:** özet düzeltmesi panodaki kopyanın yanında `<çalışma klasörü>/gorusmeler` (ya da `<kod>/testler`) altındaki asıl `.md`/`.json` dosyaya da
  yazılır; eski metin dosyada tam bir kez geçmelidir.
- **Projenin kendi kayıt betiği (isteğe bağlı, varsayılan kapalı):** projende kayıtları tutan bir Python betiği varsa asistan onun izinli alt komutlarını önerebilir.
  ⚙ Ayarlar'da yoktur; ayar dosyasına elle yazılır:
  ```json
  "kayit_komutu": ["/usr/bin/python3", "~/Proje/araclar/kayit.py", "--sabit", "önek"],
  "kayit_alt_komutlar": ["karar", "olay"],
  "kayit_bayraklar": ["--kim", "--kaynak"],
  "kayit_sure_sn": 30
  ```
  İlk öğe bir `python3` yorumlayıcısı, ikincisi proje (ya da çalışma) klasörünün içindeki `.py` betik olmalıdır; sonraki öğeler her çağrıda aynen eklenir. Asistan
  yalnız `kayit_alt_komutlar`'daki alt komutları, `-` ile başlayan argüman olarak yalnız `kayit_bayraklar`'dakileri kullanabilir. Betik kabuksuz çalışır (argümanlar
  olduğu gibi gider), girişi boştur, `kayit_sure_sn` saniyede (en çok 120) bitmezse durdurulur; çıktısının başı cevabın altına düşer. Gizli kipte hiçbir kayıt yazılmaz.
  Silme ya da dosya okuyan alt komutları listeye koyma.

**Bağlayıcı şeması (yeni, A1):** `kayit_komutu` gibi eski anahtarlar hâlâ okunur; yeni yazılan ayarlar `baglayici` altında tek yerde durur. Örnek (`kayit` adlı bağlayıcı):
  ```json
  "baglayici": {"kayit": {"tur": "sqlite_kayit", "yol": "~/Proje/kayit.db",
    "sorgular": {"kisiler": "SELECT …", "kararlar": "SELECT …"},
    "kurallar": ["…"],
    "yazma": {"komut": ["/usr/bin/python3", "~/Proje/araclar/kayit.py"], "alt_komutlar": ["karar", "olay"], "bayraklar": ["--kim", "--kaynak"], "sure_sn": 30}}}
  ```
  Aynı alanlar eski anahtarlarla da yazılabilir (`veritabani.yol`, `veritabani.kisiler`, `kayit_komutu`, `kayit_alt_komutlar`, `kayit_bayraklar`, `kayit_sure_sn`). İkisi de varsa yeni olan kazanır ve günlüğe
  "AYAR: … gölgeliyor" satırı düşer. `"acik": false` bağlayıcıyı kapatır (eski anahtarlar dahil). Ayar dosyası bu geçişte hiçbir zaman kendiliğinden yazılmaz.
  Brifing.app'in kayıt yazma komutu (`yazma`) yeni şemayı henüz okumuyorsa, o alanlar üst düzey `kayit_*` anahtarlarında kalır.

## Döküm kontrolü (yalnız geliştirici kurulumu)
Beta kurulumunda görünmez; geliştirici kurulumunda ses arşivi açıkken (ayar `ses_arsivi`) çalışır, hepsi yerel (ağ çağrısı yok, beta veri paketine bir şey girmez). Gizli ve deneme toplantıları listeye girmez.
Toplantı bitip ses arşivi ve (varsa) hakem dökümü hazır olunca aktarıcı bir kontrol listesi hazırlar; panoda Bugün'de "Döküm kontrolü hazır" satırı çıkar, `Kontrole başla` sayfayı (`/dokum-kontrol`) açar.
- **Önemli satırlar önce:** tüm döküm yerine yaklaşık 200 satır (≈ 15–20 dk): Whisper ile Gemini/Teams altyazısının ayrıştığı, Gemini'nin duyup Whisper'ın atladığı, ad/terim geçen, karar-iş saatlerine yakın, dili/hızı/tekrarı tuhaf satırlar. Her satırda nedeni küçük etiketle görünür; `Tümü`ne geçilebilir. Hedef satır sayısı ayar `dokum_kontrol_satir`.
- **Dinleme:** her satırın kendi ses parçası çalınır (ben/karşı ayrı). Kısayollar: Boşluk çal/durdur · Enter doğru, sonraki satır · E düzelt (Enter kaydeder ve geçer, Esc vazgeçer) · 1/2/3 Whisper/Gemini/Teams metnini al · ↑ ↓ önceki/sonraki · R yeniden çal · [ ] hız · T öncelikli/tümü · S zaman/öncelik sırası. Her değişiklik kendiliğinden kaydedilir (`kontrol-durum.json`), sayfa kapanınca kaldığı yerden devam eder.
- **Bitir ve kaydet:** `duzeltme-elle.json` (ses arşivi klasöründe; {dosya, kanal, saat, whisper, gemini, dogru} + dinlenen listesi) yazılır ve üç iş olur: (1) ölçüm — yalnız dinlenen satırlara göre Whisper/Gemini/Teams sözcük hatası (5 dk bloklar, Gemini satır kayması blokta etkisiz) ve ad isabeti → `canli/dokum-olcum.jsonl` (yalnız sayı), rapor `olcum.py dokum`, Kulis'te ikinci seri; (2) ad/terim düzeltmeleri öğrenen sözlüğün mevcut onay yoluna aday olarak girer; (3) dinlenen satırların ses parçası ve doğru metni `egitim-havuzu/dogrulanmis/<toplantı>/` altına kopyalanır (ayar `ses_arsivi_egitim: false` kapatır; 14 günlük arşiv temizliği bunlara dokunmaz).

## Sorun giderme

Toplantıda bir şey beklediğin gibi gitmezse önce **⚙ Ayarlar → Kurulumu denetle**'ye bak (✗ olan maddenin altında ne yapacağın yazar). Aşağıdakiler en sık karşılaşılanlar; her satır "belirti: ne yapmalı" biçimindedir. Ayar adları `ayar.json`'a `"ayar_adi": değer` diye yazılır; panoda ⚙ Ayarlar'da karşılığı varsa oradan değiştirmek daha kolaydır.

### Döküm ve karşı tarafın sesi
- **Karşı taraf satırı hiç gelmiyor:** Kurulumu denetle'yi çalıştır; Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı'nda "Suflor Ses" açık olmalı. Altyazı açıksa Chrome'da Suflor.me simgesindeki "Karşı taraf → Aç" yedek yoldur.
- **Ekran paylaşımından sonra karşı ses kesildi:** karşı taraf konuşunca yardımcı yakalamayı kendisi yeniden kurar; kurmazsa Suflor Ses'in iznini kapatıp açmak yeterli.
- **Whisper'ın yazdığı bir ad ya da terim yanlış (ör. asistanın adı başka sözcük yazılıyor):** adı proje sözlüğüne ya da kişi listesine ekle; asistan adıyla seslenince cevap gelmiyorsa ilk bakılacak yer burasıdır.
- **Dökümde hı hı gibi kısa sözler senin adına çıkıyor:** hoparlör yerine kulaklık kullan; kapatmak için `"konus_alindi": false`.
- **Çok uzun toplantıda (4,5 saati aşınca) eski bölümler "kayıtta yok" çıkıyor:** döküm dosyasının kendisi eksiksizdir; yalnız Konuş'un bakabildiği pencere sınırlıdır, eski bir şeyi dosyadan açıp sor.
- **Terimli konuşmalarda döküm hataları arttı:** `"whisper_motor": "mlx"` ile eski motora (MLX) dönülür; ayarı kaldırınca yine whisper.cpp.
- **Toplantının ilk dakikasında döküm geç başladı:** whisper.cpp'nin ilk açılışında Core ML kodlayıcısı bir kez hazırlanır (birkaç dakika sürebilir); o sırada satırlar altyazıdan gelir. Sonraki açılışlar birkaç saniyedir.
- **Günlükte "WHISPER: cpp açılamadı (…) — MLX yedeği":** whisper.cpp bu Mac'te açılmadı; o gün MLX'le sürer, ertesi gün yeniden denenir. MLX modeli diskte yoksa o an iner (~1,6 GB; panoda/`/status`'ta Whisper "indiriliyor", bitene kadar döküm altyazıdan). Kurulumu denetle'deki "whisper.cpp" satırına bak; eksikse `python3 kurulum.py whispercpp`.

### Toplantı, platform ve kartlar
- **Google Meet'te altyazı açık ama satır gelmiyor ya da dökümde menü metinleri var:** Meet arayüzü değişmiş olabilir; Chrome'da Suflor.me eklentisini yenile (`chrome://extensions`) ve güncelleme çıkmışsa **Güncelle**'ye bas.
- **Toplantıya söyle (🔊) web'de çalışmıyor ya da "Toplantı bağlantısı bulunamadı" diyor:** masaüstü Teams ya da Zoom uygulamasını ve BlackHole sesini kullan; web sürümlerinde bu yol her zaman çalışmaz.
- **Karşı taraf seni duymuyor, "Menü uygulaması kapandı" bildirimi geldi:** uygulama 5 saniyede kendiliğinden açılır; açılmazsa Teams'te mikrofonu "Harici Mikrofon"a al.
- **Konuş'la sorduğun soruyu karşı taraf da duydu:** önce Teams'te kendini sessize al (hatırlatma kartı bunu yazar).
- **Toplantıda asistan hoparlörden okudu, karşı taraf duydu:** kulaklık algısı yanılmış olabilir; kulaklığı çıkarıp yeniden tak. Sürerse ⚙ Ayarlar → Toplantı → "Asistanlar toplantıda konuşsun"u kapat.
- **Hiçbir toplantı kaydedilmiyor, panoda 🔒 Gizli ve kırmızı şerit var:** gizli kip açık kalmış; 🔒'ye bas.
- **Ayarı yanlışlıkla değiştirdin:** ayarlar anında kaydedilir; aynı ayarı geri çevir.
- **Arka plandaki toplantı oturumu uzun süre "çalışıyor" görünüyor:** panoda Ayrıntı'dan araç adımlarına bak; gerekirse Terminal'de göster.
- **Paylaşım yokken "sunulan ekran" açılıyor:** `"ekran_oto": false` ile kendiliğinden ekran kaydını kapat.
- **Paylaşılan ekranın yazısı Claude'a toplu gider (ayar `ekran_toplu_sn`, varsayılan 45; gizli ayar, ⚙ Ayarlar'da yok):** ilk ekran yazısı beklemeden, sonrakiler en çok bu süre aralığıyla tek olayda (en son ekran tam, aradakiler kısa) gider; soru ya da başka bir olay giderken yanına eklenir; toplantı bitince bekleyen gönderilir. Her ekran değişiminde Claude'u ayrı uyandırmamak içindir (maliyet). `0` yazarsan eski davranış: her ekran değişimi hemen gider. Görüntü alma ve kanıt dosyaları değişmez.
- **Ekran görüntüsü yanlış pencereyi aldı ya da boş geldi:** tüm ekranı paylaşmayı dene; masaüstü toplantıda pencere adı değişmiş olabilir.
- **Sesli toplantı notu ("not al.") istemediğin yerde çıkıyor:** `"sesli_not": false`.
- **Takvime hatırlatma eklenemedi, e-posta taslağı açıldı:** Sistem Ayarları'nda Suflor Takvim'e tam erişim ver; farklı bir takvim için `"hatirlatma_takvim": "<takvim adı>"`.
- **Gmail taslağı yanlış hesapta açılıyor:** Chrome'da o hesapla oturum aç ya da ⚙ Ayarlar → E-posta'da gönderen adresini düzelt.

### Asistan ve seslenme
- **Asistan istenmeden cevap veriyor ya da üstüne konuşuyor:** "<asistanın adı>, dur" de ya da Option + Shift + S'ye bas. Sık oluyorsa insanlara sorduğun soruyu asistana saymasın diye `"hitap_devam_sn": 10` yap (0 kapatır).
- **Asistanın adını yalnızca anarken (ör. "… dün iyi cevap verdi") konuşuyor:** "<asistanın adı>, dur" de; sık oluyorsa toplantı başında ilk seslenmeyi sen yap.
- **Yanlış asistan ya da yanlış dilde cevap geliyor:** Konuş dilini ve otomatik dil seçimini ⚙ Ayarlar'dan kontrol et; kısa Türkçe cümleler bazen İngilizce sanılır, uzun cümle kurmak çözer.
- **"Hı hı" ya da "Tamam" araları yersiz geliyor:** `"konus_alindi": false`.
- **Sesle verdiğin onay yanlış anlaşıldı:** panoda 10 saniye içinde **Geri al**'a bas.
- **Sesle iletilen not hedef oturumda eksik ya da anlamsız:** aynı talimatı daha yavaş ve tam cümleyle tekrar et.

### Ses ve okuma
- **Okuma birden Mac'in kendi sesiyle geliyor:** buluttaki ses (Gemini) kotası dolmuş ya da anahtar geçersiz olabilir. Günlük kotası dolunca öbür modele geçilir, ikisi de dolarsa yerel ses okur. AI Studio'da faturalamayı ve anahtarı kontrol et.
- **Okuma panoda görünüyor ama duyulmuyor (kulaklığı takıp çıkarınca):** bir sonraki okuma yeni süreç açar; sürerse Suflor.me uygulamasını kapatıp yeniden aç.
- **Bir ad ya da sözcük garip okunuyor:** doğru okunuşu `canli/telaffuz.json` dosyasına `{"Ad": "Okunuş"}` biçiminde yaz.
- **Kulaklık takılı ama Suflor kendi sesini duyuyor ("araya girildi"):** Sohbet'i kapat; bas-tut (Option + Shift + Boşluk) ile konuş.
- **Sohbet açık kaldı ve odadaki konuşma soru sayıldı:** Sohbet'i kapat; 60 saniye sessizlikte kendiliğinden kapanır.

### Konuş
- **Cevap yaklaşık 30 saniye gecikti ya da "Claude cevap vermedi" yazdı:** soruyu yeniden sor; sık oluyorsa `"konus_zaman_asimi_sn"` değerini kısalt.
- **Konuş ve toplantı oturumu hiç cevap vermiyor:** Claude Code oturumun kapanmış olabilir. Terminal'de `claude` yazıp `/login` ile giriş yap.
- **Mac'te bellek baskısı var (iki Claude süreci açık):** `"konus_iki_surec": false`.
- **Her seferinde izin soruluyor:** proje klasörü Suflor klasörünün dışındaysa Claude belge okumak için izin ister; Claude Code'da o klasöre kalıcı izin ver.
- **Giriş denetimi kullanım payını yiyor:** `"claude_giris_yokla": false`.

### Proje ve arama
- **Toplantı başında Mac yavaşlıyor (Etkinlik İzleme'de `cevir-isci` ya da `gomme-isci`):** belge çevirme ve anlam araması bellek kullanır. `"cevir": false` çevirmeyi, `"anlam_arama": false` anlam aramasını kapatır; `"cevir_tur_sn"` ve `"anlam_bos_dk"` küçültülebilir. Çevirme toplantı başlayınca bir sonraki dosyada durur.
- **Proje hazırlığı takıldı (ilerleme durmuyor ya da eski):** sihirbazdan ya da ⚙ Ayarlar → Proje → **Projeyi yeniden hazırla** ile yeniden başlat.
- **Proje belgeleri, veritabanı ya da sözlük eskidi ("okuyamıyor" uyarısı):** Sistem Ayarları → Gizlilik ve Güvenlik → Dosyalar ve Klasörler → Suflor Brifing → Masaüstü'nü aç; sonra Kurulumu denetle'yi çalıştır.

### Kurulum ve izinler
- **Güncelleme ya da kurulum sonrası bir izin sessizce düştü (ekran kaydı, e-posta, mikrofon):** Sistem Ayarları'nda o iznin Suflor satırını − ile kaldır, + ile yeniden ekle; sonra Kurulumu denetle'yi çalıştır.
- **"Kurulmadı: sohbet açık" ya da Güncelle sürekli reddediliyor:** açık toplantı ya da Sohbet'i bitir; hâlâ olmuyorsa Kurulumu denetle'yi çalıştır ve gerekirse güncellemeyi toplantı dışında yap.
- **Panoya ulaşılamıyor (aktarıcı açılmıyor):** kurulum dosyalarından biri eksik kopyalanmış olabilir; `~/Suflor.me/guncelle.command`'a çift tıklayıp yeniden kur.
- **Panoda "Eklenti eski sürümde" yazıyor, şerit kart göstermiyor:** `chrome://extensions` → Suflor.me → yenile. Eklentiyi başka klasörden yüklediysen ayara `"eklenti_kimlik": ["<eklenti kimliği>"]` ekleyip güncellemeyi yeniden çalıştır.
- **Karşı ses ya da Whisper hiç yüklenmedi (panoda "kapalı"):** Kurulumu denetle'yi çalıştır; aktarıcı kendiliğinden yeniden başlayınca model geç kalkabilir, bir dakika sonra yeniden bak.

## Gizlilik ayrıntıları
- Ses ve döküm **Mac'inden çıkmaz.** Konuşma tanıma yereldir; ses diske yazılmaz.
- Aktarıcı yalnız `127.0.0.1` adresinde çalışır; toplantı içeriğini hiçbir sunucuya göndermez. İstisna isteğe bağlı Gemini sesi: açarsan (⚙ Ayarlar → Ses → Gemini)
  yalnız okunacak metin (cevap, özet, çeviri, fısıltı, duyuru) Google'a gider, ses kaydı gitmez; kapalıyken (varsayılan) sesler Mac'te üretilir.
- **Beta geliştirme verisi:** beta sürümü gönüllü geliştirme katılımıdır. Suflor.me'yi geliştirmek için yalnız sayılar gönderilir (kullanım, hız, hata):
  kurulum adımlarının süresi ve izinler, haftalık kullanım sayıları, toplantı sonu gecikme ve hata sayıları, konuşma tanıma motorunun açılış sonucu ve süresi, çağrı ve simge sayısı, seçili ayarlar
  (ses motoru, dil, tema gibi). Konuşmaların, metinlerin ve adların hiçbiri Mac'inden çıkmaz: döküm, kart, soru ve cevap, kişi/toplantı/proje/dosya
  ve asistan adı, e-posta, takvim, ses, ses izi ve ekran görüntüsü gitmez. Kimlik yalnız rastgele bir kurulum numarasıdır. Beta sürümünde kapatılmaz;
  giden her paketin kopyası `~/Library/Application Support/Suflor/teshis/gonderilen/` altında durur.
- Claude'a giden metin, senin Claude Code oturumunun gördükleridir (Anthropic'in kullanım koşulları geçerli).
- Toplantıda dış bilgi kaynağı açarsan (`toplanti_bilgi_kaynaklari`) Claude'un o kaynağa yazdığı sorgu (metrik, dönem, kanal) o hizmete gider; döküm, ad ve ses gitmez.
- **Claude dışında bir sağlayıcı seçersen metin bağlamı o sağlayıcıya gider, ses gitmez.** Metin bağlamı:
  sorun, toplantı dökümünden ve notlardan parçalar, proje belgelerinden aranan parçalar, proje kartı. O hizmetin kullanım koşulları geçerlidir
  (Gemini'nin ücretsiz katmanında Google gönderilen metni ürünlerini geliştirmek için kullanabiliyor; ücretli katman önerilir). Beta verisine yalnız seçeneğin türü girer
  (Claude Code / Gemini / OpenAI uyumlu / yerel); adres, model ve anahtar girmez.
- Toplantı dosyaları senin proje klasöründe durur; kişi adı içerir, iç belge gibi davran.

## Gerekenler
- Apple Silicon (M serisi) işlemcili Mac, macOS 14 ya da üstü
- En az 16 GB bellek (konuşma tanıma ve ses modeli toplantı sırasında ~4 GB kullanır)
- ~14 GB boş disk (modeller ~7 GB — whisper.cpp ~2,1 GB dahil, belge çevirme ve anlam araması ~3,3 GB)
- Google Chrome
- [Claude Code](https://claude.com/claude-code) ve bir Claude aboneliği (Pro ya da üstü) önerilir. Claude Code kurulu değilse sihirbaz kurar;
  Terminal'de `claude` → `/login` ile giriş gerekir (Claude masaüstü uygulamasındaki giriş Terminal'e geçmez). Yerine bir API anahtarı
  seçilebilir ([Yapay zekâ seçimi](#yapay-zekâ-seçimi)); o zaman toplantıdaki kartlar ve özet olmaz, döküm, pano ve Konuş çalışır.
  Claude Code'un oturumu zamanla düşebilir: Suflor.me bunu yarım saatte bir küçük bir denemeyle yoklar; düşünce sesli söyler, bildirim gösterir ve
  Konuş satırında yazar — Terminal'de `claude` → `/login` ile yeniden giriş yeter (yoklamayı kapatmak: ayar `claude_giris_yokla: false`).

## Bileşenler
| Parça | Ne iş yapar |
|---|---|
| Chrome eklentisi (`manifest.json`, `content.js`, `platform-teams.js`, `platform-meet.js`, `platform-zoom.js`, …) | Teams/Meet/Zoom sayfasından altyazı/döküm ve mikrofon sesini alır, şeridi gösterir |
| Aktarıcı (`relay.py`) | Yerel sunucu: satırları dosyaya yazar, kartları tutar, panoyu sunar |
| Menü çubuğu uygulaması (`menu-cubugu.swift` → `~/Applications/Suflor.me.app`) | Pano penceresi, menü çubuğu paneli, ekranın alt ortasında kart kutuları, Mac geneli bas-konuş, masaüstü toplantı sinyali |
| Ses yardımcısı (`ses-yardimcisi.swift` → Suflor Ses.app) | Toplantı uygulamasının sesini (karşı taraf) macOS'tan alır; mikrofonu almaz, ses diske yazılmaz |
| Konuşma tanıma (`whisper-isci.py`) | Canlı döküm: Apple Silicon'da varsayılan whisper.cpp + Core ML (Whisper large-v3-turbo 8 bit, kodlayıcı Neural Engine'de; `<ortak>/whisper-cpp/`, ~2,1 GB: model, Core ML kodlayıcısı ve Silero VAD Hugging Face'ten, `whisper-server` açık deponun sürüm sayfasından, boyut, SHA-256 ve imza denetlenerek). İlk açılışta Core ML bir kez hazırlanır (birkaç dakika). Açılamazsa aynı süreçte MLX'e geçer (geçici yedek; o gün yeniden denenmez). `"whisper_motor": "mlx"` eski motoru seçer. Dosyadan döküm de aynı motorla (MLX'ten 1,5–2,4 kat hızlı; cpp açılamazsa MLX'e düşer, MLX modeli yoksa yalnız o zaman iner; toplantı başlayınca iş sunucusuyla birlikte duraklar). Toplantı sonu konuşmacı etiketlemesi ve konuşmacı ses izi (ECAPA) MLX ile (Whisper turbo, kurulumda yerelde 8 bite indirilir) |
| Toplantıda asistan (`aktarici/toplantiya-ses.py`, `aktarici/otonom.py`, `soyle-main.js`; ⚙ Ayarlar → Asistanlar toplantıda konuşsun, ayar `toplantiya_ses`, varsayılan kapalı) | Toplantıda “<ad>, …” diye seslendiğin asistanın cevabını herkesin duyacağı şekilde okur (söz sırası gelince; “<ad>, dur” ya da Option + Shift + S susturur; sen bir kez çağırdıktan sonra diğer katılımcılar da ona adıyla sorabilir; yalnız sana cevap için Konuş düğmesi): web toplantısında yalnız okuma süresince mikrofon kanalına karıştırır (sessizdeysen okumaz); masaüstü Teams'te BlackHole ile |
| Anlık ilk yazı (`tstt-golge-isci.py`, `aktarici/golge-tstt.py`; ayar `tstt_taslak`, varsayılan açık, yalnız `golge_tstt` açıkken) | Konuşulurken sözün ilk kelimeleri ~0,4 sn içinde soluk taslak olarak görünür; Whisper’ın kesin satırı gelince yerine geçer. Taslak yalnız ekrandır: döküme, karta, Claude bağlamına ve hitap/komut algısına girmez (Teams altyazısı zaten taslak veriyorsa tstt gösterilmez). Yerel turkish-stt akış tanıyıcısı (mihuai, `mihuai/turkish-stt-66m-v2`) kullanılır; ses Mac’ten çıkmaz |
| Tur sonu (`tur-isci.py`) | smart-turn v3 (8,7 MB, yerel): konuşurken sözün bitip bitmediğini tahmin eder; kurulamazsa sessizlik süresine bakılır |
| Anlama göre arama (`gomme-isci.py`; `baglam.py gomme`) | multilingual-e5-base (MIT, ~1,1 GB, yerel): sorudaki sözcükler belgede geçmese de anlamca yakın parçaları bulur; sözcük aramasıyla birleştirilir. Arka planda bir sunucu açık kalır (~1 GB bellek), 30 dk sorgu gelmezse kapanır |
| Belge çevirme (`cevir-isci.py`; `baglam.py tara`, `baglam.py cevir`) | Proje klasörünü tarar (kopya, eski sürüm, dışa aktarım, gizli görünen dosya) ve PDF, sunum (PowerPoint, Keynote), Pages, Numbers, eski Excel (.xls) ve görüntüleri Mac'te metne çevirir: Docling + Apple Vision (.xls için xlrd), ayrı Python 3.12 ortamında, ağ kapalı. Eski Word (.doc), .rtf ve .odt macOS'un `textutil` aracıyla, OpenDocument tablo ve sunum (.ods, .odp) doğrudan okunur. Şifre, anahtar, kart ya da IBAN geçen parça aramaya girmez |
| Proje veritabanı (`baglam.py proje-vt`; `<uygulama>/proje.db`) | Excel, Numbers, CSV/TSV sayfaları (`t_…` tabloları; sayı sayı, tarih ISO; kaynak dosyası `tablolar` tablosunda) ve onaylı proje kartı (`kisi`, `kurum`, `karar`, `acik_is`, `olay`, `terim`, `proje`) tek SQLite dosyasında. Konuş ve toplantı oturumu yalnız okuyan SQL ile bakar (`vt_sema`, `vt_sor`; toplantıda `toplanti-claude.py proje`). Yalnız değişen dosya yeniden yazılır; gizli bilgi taşıyan hücre `[gizli]`. Kendi kayıt veritabanın ayarlıysa (`veritabani`) kurulmaz; `"proje_vt": false` kapatır |
| Yapay zekâ katmanı (`aktarici/beyin.py`, `aktarici/saglayici.py`) | Konuş, çeviri, telaffuz ve proje kartının yapay zekâ çağrıları tek yerden: Claude Code ya da OpenAI uyumlu uç (Gemini, OpenAI, LM Studio gibi); seçim, Anahtar Zinciri |
| Claude köprüsü (`toplanti-claude.py`, `baglam.py`, `yapi.py`) | Claude'un izlediği olay akışı, kart gönderme, proje araması, özet araçları |
| Kurallar (`TOPLANTI-KURALLARI.md`, `sablon/`) | Claude'un toplantıdaki davranış kuralları ve `/toplanti` komutu |

## Lisanslar
MIT — ayrıntı [LICENSE](LICENSE).

İsteğe bağlı indirilen bileşenler Suflor.me ile gelmez, kendi lisanslarıyla kullanılır: doğal Türkçe ses modeli
[wite-tech/pocket-tts-turkish](https://huggingface.co/wite-tech/pocket-tts-turkish) (CC-BY-4.0, wite-tech), Pocket TTS (Kyutai, MIT),
pocket-tts-turkish paketi (Apache-2.0); elle kurulursa [alperiox/pocket-tts-turkish](https://huggingface.co/alperiox/pocket-tts-turkish) (MIT).
Konuşma tanıma için kurulumda indirilenler: [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (MIT; `whisper-server` küçük bir yamayla derlenmiş hâli sürüm sayfasında),
Whisper large-v3-turbo ağırlıkları (OpenAI, MIT; ggml ve Core ML biçimi [ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp), MLX biçimi mlx-community),
Silero VAD (MIT; [ggml-org/whisper-vad](https://huggingface.co/ggml-org/whisper-vad)).
