# Suflor.me

Toplantıda kulağına fısıldayan asistan. Suflor.me, Microsoft Teams toplantını Mac'inde canlı olarak yazıya döker.
Claude konuşmayı izler ve sana küçük kartlarla ne sorman, neyi belirtmen ya da neye dikkat etmen gerektiğini söyler.
Kartlara yalnız o toplantıyı değil, projenin belgelerini ve geçmiş toplantılarını da katar.

> Durum: erken sürüm. Yalnız Mac (Apple Silicon) ve Teams web (Chrome) destekleniyor; Google Meet ve Zoom web sırada.

## Ne yapar
- **Canlı döküm:** senin sesin ve karşı tarafın sesi Mac'te, yerel Whisper modeliyle yazıya döker. Teams'in altyazısı
  ya da dökümü açıksa konuşmacı adlarını oradan alır.
- **Kartlar:** Claude toplantıyı izler ve Teams ekranının köşesindeki küçük şeride ve panoya kart gönderir:
  *Sor*, *Belirt*, *Değinme*, *Dikkat*, *Bilgi*. Toplantıdaki rolüne (yöneten, katılımcı, dinleyici) göre az ya da çok konuşur.
- **Proje bağlamı:** konuşmada geçen bir iddia, rakam ya da sorumluluk daha önceki bir belgede ya da toplantıda farklı
  geçiyorsa bunu fark eder ve kaynağıyla birlikte söyler.
- **Soru sor, not düş:** panoya yazdığın metin `?`, `soru`, `Claude` ya da iki boşlukla başlıyorsa Claude'a soru olur
  ve birkaç saniyede kartla cevaplanır; başka bir şeyle başlıyorsa toplantıya not olarak düşer.
- **Kanıt:** Option + Shift + K ile toplantı ekranının görüntüsünü kaydeder (ekranda şifre görünürse uyarır).
- **Toplantı sonu:** özet ve başında toplantı çıktısı (kararlar, sahibi ve tarihi belli işler, açık kalanlar, tek öneri); özetin yanında
  gündem maddelerine göre **zihin haritası** (tarayıcıda açılır, resim olarak indirilir). Kararlar ve iddialar bu Mac'te bir
  **karar grafında** birikir: sonraki toplantıda aynı kişi farklı bir rakam söylerse Claude fark eder.
- **Konuşmacı adları:** altyazının ad verdiği kişilerin ses izi bu Mac'te saklanır (**ses izi hafızası**); altyazı yokken (Teams
  masaüstü, panoya bırakılan kayıt) adı oradan bulur. Silmek için: `toplanti-claude.py hafiza --sil "<ad>"`.
- **Platformlar:** Teams web; Google Meet ve Zoom web (altyazıdan; ilk sürüm). Teams ve Zoom masaüstü menü çubuğu uygulamasıyla.

## Gizlilik
- Ses ve döküm **Mac'inden çıkmaz.** Konuşma tanıma yereldir; ses diske yazılmaz.
- Aktarıcı yalnız `127.0.0.1` adresinde çalışır; hiçbir sunucuya veri göndermez. Tek istisna isteğe bağlı Gemini sesi: açarsan (⚙ Ayarlar → Ses → Gemini)
  yalnız okunacak metin (cevap, özet, çeviri, fısıltı, duyuru) Google'a gider, ses kaydı gitmez; kapalıyken (varsayılan) sesler Mac'te üretilir.
- Claude'a giden metin, senin Claude Code oturumunun gördükleridir (Anthropic'in kullanım koşulları geçerli).
- Toplantı dosyaları senin proje klasöründe durur; kişi adı içerir, iç belge gibi davran.

## Gerekenler
- Apple Silicon (M serisi) işlemcili Mac, macOS 14 ya da üstü
- En az 16 GB bellek (konuşma tanıma ve ses modeli toplantı sırasında ~4 GB kullanır)
- ~12 GB boş disk (modeller ~5 GB, belge çevirme ve anlam araması ~3,3 GB)
- Google Chrome
- [Claude Code](https://claude.com/claude-code) ve bir Claude aboneliği (Pro ya da üstü). Claude Code kurulu değilse sihirbaz kurar;
  Terminal'de `claude` → `/login` ile giriş gerekir (Claude masaüstü uygulamasındaki giriş Terminal'e geçmez).

## Kurulum
Terminal'e yapıştır:
```bash
curl -fsSL https://raw.githubusercontent.com/suflorme/suflor/main/kur.sh | bash
```
Kod `~/Suflor.me` klasörüne iner, kurulum sihirbazı Chrome'da açılır (Chrome yoksa varsayılan tarayıcıda) ve her adımı kendisi denetler.
Sihirbazı kapatırsan aynı komutu yeniden çalıştır; kaldığın adımdan sürer.

**Asistan:** sihirbazda asistanına ad koyarsın; ona adıyla seslenirsin ("Defne, yarın neler var?"). Hitap (siz/sen), tarz (ölçülü ya da rahat
ve esprili) ve ses (Mac'in Türkçe sesi; Pocket kuruluysa kadın ya da erkek sesi) seçilir; istersen toplantı dışında konuşan ikinci bir asistan
eklersin. Sihirbaz kişilik dosyasını `~/Library/Application Support/Suflor/kisilik/<ad>.md` olarak yazar (aynı adlı dosya varsa üzerine yazmaz)
ve ayara bağlar (`kisilik`, ikinci asistan `kisilik_toplanti_disi`). Atlarsan asistanın adı Suflor olur. Dosyayı elle de düzenleyebilirsin
(biçim: `sablon/kisilik-ornek.md`); asistanları sonradan ⚙ Ayarlar → Konuş'ta değiştirirsin.
Her yayın geliştiricinin anahtarıyla imzalıdır: kurulum ve güncelleme indirilen kodun imzasını ve dosya özetlerini doğrular, tutmazsa hiçbir şey kurmaz.

**Proje hazırlığı:** sihirbaz proje klasörünü tarar (kopya, eski sürüm, adından gizli görünen dosyalar; dizine girmesini istemediğin klasörü
çıkarırsın), PDF, sunum ve görüntüleri bu Mac'te metne çevirip dizinler ve istersen proje kartını (özet, kişiler, kararlar, açık işler, terimler)
Claude'la hazırlar; kartı onaylamadan önce düzeltirsin. Arka planda sürer, sihirbazı kapatsan da biter. Sonradan: panoda ⚙ Ayarlar → Proje →
**Projeyi yeniden hazırla**.

**Güncelleme:** yeni sürüm çıkınca panonun sağ üstünde **Güncelle** düğmesi belirir (toplantı yokken); tıklaman yeter, Chrome
eklentisi de kendini yeniler. Elle: `~/Suflor.me/guncelle.command`'a çift tıkla (son sürümü indirir, aktarıcıyı yeniden kurar; ayarlarına ve
belgelerine dokunmaz). Eklenti kendini yenilemezse: Chrome'da `chrome://extensions` → Suflor.me → yenile.

## Kullanım (kısaca)
1. Toplantıdan önce panodaki takvimden **Başlat**'a bas (ya da proje klasöründeki Claude Code oturumunda `/toplanti`).
   Claude gündemi kurar, hazır olunca toplantıya katılırsın.
2. Karşı tarafın sesi kendiliğinden yazıya dökülür (Suflor Ses yardımcısı, macOS 14.4+; ilk kurulumda macOS "Sistem Sesi Kaydı" izni
   sorar — İzin Ver). Yardımcı yoksa ya da izin verilmediyse Chrome'daki toplantıda **Suflor.me simgesi → "Karşı taraf" satırındaki Aç** (satır yalnız sorun varken görünür; masaüstü Teams/Zoom'da yedek yok).
3. Kartlar Teams'in sol altındaki küçük şeritte ve panoda görünür: **SÖYLE** (şunu de/sor), **DUR** (yapma/açma), **CEVAP**; **NOT** yalnız panoda. ✓ yaptım · Okudum · ✕ gerek yok.
4. Kısayollar: **Option + Shift + K** kanıt · **Option + Shift + O** Ne diyeyim? (Claude tek cümlelik replik önerir) · **Option + Shift + M** sessiz (10 dk kart yok; tekrar basınca kapanır). Kartı "Sonra" (⏸) ile gündemde sıradaki maddeye bırakabilirsin. ⭐ önemli an panoda düğme.
5. Toplantı bitince Claude özeti çıkarır ve sana sunar.
6. Brifing ve özet panoda **Dışarı aktar** ile PDF, e-posta taslağı (alıcısız, katılımcılara ya da kendine), panoya kopya ya da .md dosyası olur.
   Taslağın açılacağı yeri (Gmail, Outlook web ya da Mac'in posta uygulaması) ve gönderen adresini sihirbazın takvim ekranında seçersin;
   sonradan ayar.json'da `"eposta"` ve `"eposta_adres"`. Seçmezsen takvimine bakılarak seçilir.

**Ayarlar:** panonun üst çubuğundaki ⚙ — e-posta, ses ve konuşma, toplantı uyarıları, çeviri ve masaüstü, gizlilik; kaydedince hemen geçerli.

**İsteğe bağlı (ayar.json, varsayılan kapalı):** `"menu_cubugu": true` — menü çubuğu uygulaması (buzlu cam panelde mini pano,
Mac genelinde **Option + Shift + Boşluk** basılı tut-konuş ve yukarıdaki kısayollar, Teams/Zoom masaüstü toplantılarında da
çalışma: toplantıyı ve sessizi tanır, senin mikrofonunu ve karşı tarafın sesini yazar, kanıt ve
paylaşılan ekran görüntüsünü toplantı penceresinden alır; Erişilebilirlik, mikrofon ve Ekran Kaydı izni sorar; sonra `guncelle.command`.
Kapatmak için `"masaustu_mic": false`, `"kisayollar": false`; Kişiler panelinden ad okuma `"masaustu_kisiler": true` ile açılır — panel
3 dakikada bir açılıp kapanır, Teams penceresi öne gelir) · `"fisilti": true` — kulaklık takılıyken DUR kartı kısa sesle kulağına okunur ·
`"ceviri": true` — karşı tarafın İngilizce satırları panoda Türkçesiyle (metin Claude'a gider; 🎧 sesli çeviride toplantı sesi tarayıcıda
kısılır, masaüstü Teams/Zoom'da kısmak için ayrıca `"masaustu_ses_kis": true` — ses yardımcısı toplantı uygulamasının sesini kendi üzerinden
çalar; yardımcı takılırsa toplantı sesi kesilebilir) · `"oda": true` — aynı
mikrofondaki ikinci kişinin sözleri "Odadaki kişi" diye ayrılır. Ses izi hafızasını kapatmak için `"ses_izi_hafiza": false`.
Claude'un soruya bağlı olmayan SÖYLE/NOT kartları araya dakikada en çok bir kez girer (aynı dakikada gelenler birlikte görünür); aralık
`"kart_tavan_sn"` (varsayılan 60, 0 kapatır).
Karşı taraf adını söyleyince panoda ve şeritte hemen "Adın geçti — kim" (Claude'u beklemeden, yalnız sana); karşı taraf araya girmeden
90 sn'den uzun konuşursan "1,5 dk'dır sen konuşuyorsun". Sana başka adla da hitap ediliyorsa `"lakaplar": ["…"]`. Kapatmak için `"adin_gecti": false`, `"uzun_konusma_sn": 0` (süre de bu ayarla).
Daha doğal Türkçe ses: Piper kuruluysa `"ses_motoru": "piper"`, `"piper_python"` (Piper'ın Python ortamı) ve `"piper_model"` (.onnx Türkçe ses)
— sesli çeviri, fısıltı, sesli özet ve cevaplar bu sesle okunur (Mac'te, yerel); ses dosyası Suflor.me ile gelmez. Hız: `"piper_hiz"`
(varsayılan 1,0), kısa okumalar `"piper_hiz_kisa"` (1,15). Piper yoksa ya da hata verirse Mac sesi.
En doğal yerel Türkçe ses: Pocket TTS (kör dinlemede Piper'dan ve Mac sesinden belirgin iyi; işlemcide çalışır, ilk ses ~0,03 sn, ~1,6 GB bellek).
Kendi Python ortamına (Python 3.11: `pip install pocket-tts pocket-tts-turkish`) kurup modelleri bir kez indir: `wite-tech/pocket-tts-turkish`
(3 kadın + 3 erkek hazır ses, duygu etiketi; CC-BY-4.0) ve istersen `alperiox/pocket-tts-turkish` (MIT; hazır sesi yok, wite-tech'in seslerini örnek alır).
Ayar: `"pocket_python"` (o ortamın python'u), `"pocket_hf"` (modellerin indirildiği HF_HOME), `"ses_motoru": "pocket"` ve `"pocket_ses": "wite:female_2"`;
kişilik dosyasında `yerel_ses: pocket:alperiox:female_2` o kişiliğe ayrı ses verir (Gemini toplantıya ayrıldığında da yerel okumalar bu sesle).
Pocket okuyamazsa ya da kurulu değilse Mac sesi (Piper ondan sonra). Ses ve metin Mac'ten çıkmaz; model dosyaları Suflor.me ile gelmez.

En doğal ses (isteğe bağlı, bulut): Gemini TTS. Google AI Studio'dan bir API anahtarı alıp Anahtar Zinciri'ne koy
(`security add-generic-password -a "$USER" -s suflor-gemini -w`; anahtar dosyaya yazılmaz), sonra panoda ⚙ Ayarlar → Ses → Gemini.
11 hazır ses (Gemini sesi) ve model (3.8 Flash-Lite, ilk ses ~0,7 sn; 3.8 Flash) oradan seçilir. Okunacak cevap metni Google'a gider (ses kaydı
gitmez); canlı kullanım için ücretli katman gerekir (ücretsiz katman günde 10 istek; metni eğitimde kullanır). İnternet yoksa Mac sesi okur.
Kişilik dosyasında `ses: gemini:Kore`, `ses_uslup: …` (ton yönergesi) ve `ses_etiket: evet` (<chuckle> gibi sözsüz sesler) kişiliğe özel ses verir;
toplantıda asistanın cevabı da o kişiliğin Gemini sesiyle okunur. Gemini açıkken sesli çeviri (çevirmen sesi ayar `ceviri_gemini_ses`), fısıltı ve
toplantı özeti de Gemini'yle okunur; iki kişiliğin sesi de Gemini ise özet iki sesle (⚙ Ayarlar → İki sesli özet). Ton cümleye göre değişir (kötü haber,
uyarı, acele); kişilik dosyasında `gerginlik_tonu: evet` o kişiliğin tonunu toplantı gerginliğine göre ayarlatır (karar Claude'da).
⚙ Ayarlar → Toplantıda duyuru (deneme): asistanlar toplantıda konuşurken Suflor toplantı başında kendini tanıtır ve onaylanan işi "Not aldım" diye duyurur.
Kullanım ve maliyet: `canli/gemini-ses.jsonl`.

## Bileşenler
| Parça | Ne iş yapar |
|---|---|
| Chrome eklentisi (`manifest.json`, `content.js`, `platform-teams.js`, `platform-meet.js`, `platform-zoom.js`, …) | Teams/Meet/Zoom sayfasından altyazı/döküm ve mikrofon sesini alır, şeridi gösterir |
| Aktarıcı (`relay.py`) | Yerel sunucu: satırları dosyaya yazar, kartları tutar, panoyu sunar |
| Menü çubuğu uygulaması (`menu-cubugu.swift` → Suflor Menü.app, isteğe bağlı) | Mini pano paneli, Mac geneli bas-konuş, masaüstü toplantı sinyali |
| Ses yardımcısı (`ses-yardimcisi.swift` → Suflor Ses.app) | Toplantı uygulamasının sesini (karşı taraf) macOS'tan alır; mikrofonu almaz, ses diske yazılmaz |
| Konuşma tanıma (`whisper-isci.py`) | Whisper large-v3-turbo (kurulumda yerelde 8 bite indirilir) ve konuşmacı ses izi (ECAPA), ikisi de MLX ile yerel |
| Toplantıda asistan (`aktarici/toplantiya-ses.py`, `aktarici/otonom.py`, `soyle-main.js`; ⚙ Ayarlar → Asistanlar toplantıda konuşsun, ayar `toplantiya_ses`, varsayılan kapalı) | Toplantıda “<ad>, …” diye seslendiğin asistanın cevabını herkesin duyacağı şekilde okur (söz sırası gelince; “<ad>, dur” ya da Option + Shift + S susturur; sen bir kez çağırdıktan sonra diğer katılımcılar da ona adıyla sorabilir; yalnız sana cevap için Konuş düğmesi): web toplantısında yalnız okuma süresince mikrofon kanalına karıştırır (sessizdeysen okumaz); masaüstü Teams'te BlackHole ile |
| Tur sonu (`tur-isci.py`) | smart-turn v3 (8,7 MB, yerel): konuşurken sözün bitip bitmediğini tahmin eder; kurulamazsa sessizlik süresine bakılır |
| Anlama göre arama (`gomme-isci.py`; `baglam.py gomme`) | multilingual-e5-base (MIT, ~1,1 GB, yerel): sorudaki sözcükler belgede geçmese de anlamca yakın parçaları bulur; sözcük aramasıyla birleştirilir. Arka planda bir sunucu açık kalır (~1 GB bellek), 30 dk sorgu gelmezse kapanır |
| Belge çevirme (`cevir-isci.py`; `baglam.py tara`, `baglam.py cevir`) | Proje klasörünü tarar (kopya, eski sürüm, dışa aktarım, gizli görünen dosya) ve PDF, sunum, görüntüleri Mac'te metne çevirir: Docling + Apple Vision, ayrı Python 3.12 ortamında, ağ kapalı. Şifre, anahtar, kart ya da IBAN geçen parça aramaya girmez |
| Claude köprüsü (`toplanti-claude.py`, `baglam.py`, `yapi.py`) | Claude'un izlediği olay akışı, kart gönderme, proje araması, özet araçları |
| Kurallar (`TOPLANTI-KURALLARI.md`, `sablon/`) | Claude'un toplantıdaki davranış kuralları ve `/toplanti` komutu |

## Lisans
MIT — ayrıntı [LICENSE](LICENSE).
