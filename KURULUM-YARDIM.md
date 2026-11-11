# Suflor.me kurulum sorun giderme (yapay zekâ asistanı için)

Bu dosya kurulumda yardım eden yapay zekâ asistanı içindir. İnsan okuyucu için yazılmadı: kısa, kesin, komutlar olduğu gibi.
Kullanıcı bu depoyu (github.com/suflorme/suflor) ve bir hata metnini yapıştırdı; sen teşhis edip adım adım yönlendireceksin.
Kaynak: `kur.sh`, `kurulum.py`, `sihirbaz/sihirbaz.js`, `*.command`. Aşağıdaki her olgu kodda doğrulandı; emin olmadığım yer "(doğrulanmadı)" diye işaretli.

## 0. Önce kullanıcıdan iste

1. Hatanın tam metni (Terminal çıktısı ya da sihirbazdaki kırmızı/sarı kutu). Ekran görüntüsü yerine metin tercih et.
2. Hangi aşamada: `kur.sh` (Terminal) mi, sihirbaz mı? Sihirbazdaysa ekran başlığı (bölüm 2'deki adım adları).
3. macOS sürümü ve çip: `sw_vers -productVersion; uname -m; sysctl -n machdep.cpu.brand_string`
4. RAM ve boş disk: `sysctl -n hw.memsize | awk '{print $1/2^30 " GB"}'; df -h ~ | tail -1`
5. Çıktısı istenecek tanılama komutları (bölüm 4): önce `tail -40 ~/Library/Logs/suflor-kurulum.log`; kurulum bitmişse `python3 ~/Suflor.me/kurulum.py dogrula`.
6. Chrome kurulu mu, kaç macOS hesabı var (aynı Mac'te başka hesap Suflor.me kullanıyor mu).

Anahtar, parola, API anahtarı isteme (bölüm 6).

## 1. Kurulum akışı: `kur.sh`

Komut (README'deki tek satır):
`curl -fsSL https://raw.githubusercontent.com/suflorme/suflor/main/kur.sh | bash`

`kur.sh` sırayla (`set -e`):
1. `uname -s` Darwin değilse çıkar: "Suflor.me yalnız Mac'te çalışır."
2. `uname -m` arm64 değilse çıkar: Apple Silicon yok. Intel Mac desteklenmez.
3. `/usr/bin/python3` ≥ 3.9 değilse: "Önce Apple'ın komut satırı araçları gerekiyor…" yazar, `xcode-select --install` açar, çıkar (çıkış 0). Kullanıcı yüklemeyi bitirince AYNI komutu yeniden yapıştırmalı.
4. `https://codeload.github.com/suflorme/suflor/tar.gz/refs/heads/main` indirilip geçici klasöre açılır (git gerekmez).
5. İmza doğrulama (hiçbiri geçmezse "Kurulum durdu: <neden>. Hiçbir şey kurulmadı; geliştiriciye haber ver."):
   - `IMZA/dosyalar.sha256` ve `.sig` yoksa: "indirilen kod imzasız"
   - `ssh-keygen -Y verify` (namespace `suflor-yayin`, gömülü genel anahtar) tutmazsa: "imza tutmadı"
   - `shasum -a 256 -c` tutmazsa: "dosya özetleri tutmadı"
   - paketteki dosya listesi imzalı listeyle aynı değilse: "pakette imzalı listede olmayan dosya var"
6. Kod `~/Suflor.me` klasörüne açılır (`mkdir -p`, üstüne `tar -xf`). Kullanıcının o klasöre koyduğu başka dosya silinmez; önceki imzalı listede olup yenisinde olmayan VE değişmemiş dosya silinir ("eski dosya kaldırıldı: …").
7. `chmod +x *.command *.sh`; `xattr -dr com.apple.quarantine ~/Suflor.me`.
8. Eski sihirbazı kapatır (`pkill -f "kurulum.py --port"`, yalnız bu kullanıcının), sonra `cd ~/Suflor.me` ve arka planda:
   `/usr/bin/python3 kurulum.py --port 8770 --ac > ~/Library/Logs/suflor-kurulum.log 2>&1`
9. Sihirbaz sunucusu `127.0.0.1:8770` (doluysa 8771…8779'u dener; hepsi doluysa "portlarının hepsi dolu" der). `--ac` ile Chrome'da (yoksa varsayılan tarayıcıda) `http://127.0.0.1:<port>/?k=<tek kullanımlık anahtar>` açılır. Adresteki `?k=` olmadan sayfa çalışmaz (çerez `suflor_kurulum`).
10. Yeniden çalıştırmak güvenlidir: kodu günceller, ayar ve belgelere dokunmaz. Sihirbaz cevapları `~/Library/Application Support/Suflor/kurulum.json`'a kaydeder; sekme kapansa da aynı komut kaldığı adımdan sürdürür. 30 dk istek gelmezse sihirbaz süreci "yarıda" sayar (beta kurulum paketi; yalnız sayı/seçenek).

## 2. Sihirbaz adımları (sırayla, arayüzdeki Türkçe başlıklarla)

Kimlikler `sihirbaz.js` `ADIMLAR` dizisinden. Başlık metinleri Türkçe arayüzdeki gibi.

| # | Kimlik | Ekranda | Ne yapar / yazar | Nasıl bozulur → çözüm |
|---|---|---|---|---|
| 1 | karsilama | "merhaba / hello" Türkçe/English | Dil seçimi (`kurulum.json`: `dil`) | Yok |
| 2 | hosgeldin | "Toplantıda kulağına fısıldayan asistan" | Tanıtım | Yok |
| 3 | mac | "Mac'ini denetliyorum" | Satırlar: Apple Silicon işlemci, macOS 14 ya da üstü, Bellek, Boş disk, Python, Google Chrome. Hepsi tamamsa modeller arka planda iner (`kurulum.py modeller`, günlük `~/Library/Application Support/Suflor/modeller-kur.log`) | Bölüm 5: Intel, <16 GB, disk <7 GB, Python yok ("Komut satırı araçları gerekiyor" + "Yükle" = `xcode-select --install`), Chrome yok ("İndir"). Bellek ≤ 8 GB ise "Hafif kurulum (önerilir)" / "Tam kurulum" seçeneği çıkar (`profil` ayarı) |
| 4 | claude | "Yapay zekâyı bağlayalım" | Seçenek: "Claude Code (önerilen)" ya da "API anahtarı" (Gemini / OpenAI uyumlu; anahtar yalnız macOS Anahtar Zinciri'ne yazılır). Claude Code için: kurulu mu, oturum açık mı denetlenir (`claude -p "Yalnız TAMAM yaz."`, en çok 90 sn) | Bölüm 5: "Claude Code bulunamadı", "Oturum açık değil", "Terminal'de claude komutu bulunmuyor", abonelik/kota. "Aboneliğim yok, kartsız devam et": döküm, pano, notlar çalışır; kart ve özet yok |
| 5 | sen | adın, rolün, şirket, iş alanı, araçlar, kişiler, isteğe bağlı döküm yükleme | Yalnız ad zorunlu (≥ 2 karakter). Cevaplar `kurulum.json`'a | Yok. "Dökümüm yok, örnek bir görüşmeyle dene" ve "Sonra" atlanabilir |
| 6 | asistan | asistanın adı, hitap, tarz, ses | `~/Library/Application Support/Suflor/kisilik/<ad>.md` yazar (aynı adlı dosya varsa dokunmaz); doğal Türkçe ses (Pocket, ~1,3 GB) seçilirse indirilir (`pocket-kur.log`) | Doğal ses inmezse "Doğal ses kurulamadı; asistan şimdilik Mac sesiyle konuşur" + "Yeniden dene". Kurulumu engellemez. "Atla" ile geçilebilir (asistan adı "Suflor") |
| 7 | proje | "Belgelerin nerede dursun?" | Proje klasörü (varsayılan `~/Suflor`). İçi dolu klasör seçilirse Suflor kendi dosyalarını içindeki tek `Suflor/` alt klasörüne yazar; belgelere dokunmaz | Yok |
| 8 | kur | "Kuruyorum" (satırlar: Ayarlar, Proje klasörü, Çalışma notu, Arka plan hizmeti, Konuşma tanıma modelleri, Hızlı konuşma tanıma (whisper.cpp + Core ML), Karşı tarafın sesi (Suflor Ses)) | `kurulum.py` `tamamla`: `ayar.json` yazar; proje iskeleti (`belgeler/ gorusmeler/ _kanit/ _arsiv/ .claude/commands`) + `CLAUDE.md` + `/toplanti` komutunu şablondan yazar; ardından `python3 kurulum.py kur` çalıştırır (bölüm 3'te ayrıntı). Modeller burada %'yle görünür | Bölüm 5. Satırlar: "Ayarlar" kötü = `ayar.json` yazılamadı; "Proje klasörü" kötü = klasör kurulamadı; "Arka plan hizmeti" kötü = `kur` hata verdi (sarı kutuda son satır, "Yeniden dene" düğmesi). Ayrıntı için `kurulum.py kur`'u Terminal'de elle çalıştır |
| 9–11 | hz_tara, hz_onay, hz_ilerleme | proje hazırlığı (yalnız proje klasöründe belge varsa görünür) | Tarama, PDF/sunum → metin (Docling, ~3,3 GB ek model/ortam), dizin, isteğe bağlı proje kartı. `~/Library/Logs/suflor-hazirlik.log` | Takılırsa panoda ⚙ Ayarlar → Proje → "Projeyi yeniden hazırla" ya da `hazirla.command`. Kurulumu engellemez |
| 12 | takvim | "Takvimini bağlayalım" | Suflor Takvim.app'e Takvim izni; takvim hesapları, kendi adreslerin, e-posta hizmeti seçimi, isteğe bağlı Anımsatıcılar | "Takvim izni" için macOS penceresi: izin ver. Hesap yoksa "Takvim hesabı ekle" = Sistem Ayarları → İnternet Hesapları. Atlanabilir |
| 13 | eklenti | "Chrome eklentisini ekle" | Elle yükleme (bölüm 5, "Eklenti bağlanmıyor"). Bağlanınca "Eklenti bağlandı vX" | "Eklentiyi bekliyorum…" takılırsa bölüm 5. "Atla" mümkün (Teams/Meet web için eklenti gerekir; masaüstü toplantı Mac uygulamasıyla) |
| 14 | hz_kart | proje kartı onayı | Yalnız kart istendiyse | Atlanabilir |
| 15 | bitti | bitiş ekranı | Pano açılır | — |

Adım atlanabilirliği ve "hazır" koşulları: `mac` (arm + macOS ≥ 14 + python), `claude` (yapay zekâ seçimi hazır), `sen` (ad), `kur` (ayar ve arka plan hizmeti "iyi"), `eklenti` (bağlı). Hazır değilken "Devam" kilitli kalır.

## 3. `kurulum.py kur` (arka plan hizmeti) ne yapar

Sihirbazın "Kuruyorum" adımı ve `aktarici-kur.command` bunu çalıştırır. Sırayla:
1. `relay.py` ve `aktarici/*.py` sözdizimi denetlenir; `pano/` dosyaları eksikse "HATA: pano/<dosya> eksik — kurulum yapılmadı" ile durur (çalışan aktarıcı olduğu gibi kalır).
2. Kod `~/Library/Application Support/Suflor/` altına kopyalanır (`KOPYA` listesi: `relay.py`, `aktarici/`, `pano/`, `*-isci.py`, …). `canli/` verisi buradadır.
3. Ses/ECAPA dönüştürme, Whisper 8 bit kopya, tur sonu modeli (`tur_kur`), whisper.cpp arka planda (`whispercpp_baslat`).
4. Swift yardımcıları `swiftc` ile derlenir: Suflor Takvim.app, Suflor Ses.app (macOS ≥ 14.4), Suflor Brifing.app, Suflor Oynat.app, Suflor Metin.app, Suflor Posta.app, `~/Applications/Suflor.me.app` (menü çubuğu). `swiftc` yoksa (komut satırı araçları eksik) derleme SESSİZCE atlanır; sonuç: "Kurulumu denetle"de "Swift yardımcıları ✗ … eksik". Derleme hatasında ekrana "UYARI: … derlenemedi" yazılır, kurulum sürer.
5. Yerel imza (`codesign`) ve menü uygulaması yerleştirme.
6. launchd ajanı `local.suflor.aktarici` yazılır: `~/Library/LaunchAgents/local.suflor.aktarici.plist` (`RunAtLoad`, `KeepAlive`), `launchctl bootstrap gui/<uid>`. Günlük `~/Library/Logs/suflor-aktarici.log`.
7. `http://127.0.0.1:<port>/status` yanıt vermezse: "UYARI: aktarıcı yanıt vermiyor. Günlük: …" + günlüğün son 5 satırı, çıkış 1.
8. İlk kurulumda Suflor Ses için macOS izin penceresi açılır (en çok 2 dk beklenir).

Aktarıcı portu: `ayar.json` içindeki `port` (sihirbaz boş bir port seçer; ikinci macOS hesabında farklıdır, 8765–8768 aralığı yoklanır).
Chrome yerel mesajlaşma tanımı aktarıcı açılırken yazılır: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/me.suflor.anahtar.json` (+ Chrome Beta/Canary, Chromium, Edge, Brave eşdeğerleri), yardımcı betik `~/Library/Application Support/Suflor/anahtar-yardimcisi.py`.

## 4. Dosya ve yol haritası

| Ne | Yol |
|---|---|
| Kod klasörü (kur.sh) | `~/Suflor.me` (içinde `kurulum.py`, `*.command`, `manifest.json`, `IMZA/`) |
| Chrome eklentisi (paketlenmemiş) | Aynı klasör: `~/Suflor.me` (içinde `manifest.json`); sihirbaz eklenti adımında bu yolu gösterir |
| Uygulama klasörü / ayar | `~/Library/Application Support/Suflor/` ; ayar `ayar.json` (kilit `ayar.json.kilit`) |
| Sihirbaz cevapları | `~/Library/Application Support/Suflor/kurulum.json` |
| Canlı veri (döküm, kartlar, anahtar) | `~/Library/Application Support/Suflor/canli/` ; yerel anahtar `canli/kart-anahtari.txt` (gizli) |
| Denetim sonucu | `~/Library/Application Support/Suflor/dogrula.json` |
| Kişilik (asistan) dosyaları | `~/Library/Application Support/Suflor/kisilik/<ad>.md` |
| Modeller ve Python ortamları | `/Users/Shared/Suflor` (ayar `ortak`). Bu klasör başka hesaba aitse ve bu hesap yazamıyorsa `~/Library/Application Support/Suflor-ortak` |
| Modeller içinde | `whisper-venv/`, `whisper-modeller/`, `whisper-cpp/`, `ses-modeller/`, `anlam-modeller/`, `cevir-venv/`, `python312/`, `pocket-venv/`, `pocket-modeller/` |
| Proje klasörü (varsayılan) | `~/Suflor` (ayar `proje`; içi doluysa Suflor dosyaları `<proje>/Suflor/`) |
| Menü uygulaması | `~/Applications/Suflor.me.app` |
| launchd ajanı | etiket `local.suflor.aktarici`; plist `~/Library/LaunchAgents/local.suflor.aktarici.plist` |
| Kurulum günlüğü | `~/Library/Logs/suflor-kurulum.log` (sihirbaz süreci; `kur.sh` yazar) |
| Aktarıcı günlüğü | `~/Library/Logs/suflor-aktarici.log` |
| Güncelleme günlüğü (panodaki Güncelle) | `~/Library/Logs/suflor-guncelle.log` |
| Proje hazırlığı günlüğü | `~/Library/Logs/suflor-hazirlik.log` |
| Menü uygulaması / ses yardımcısı günlükleri | `~/Library/Logs/suflor-menu.log`, `suflor-menu-hata.log`, `suflor-ses.log` |
| Model indirme günlükleri | `~/Library/Application Support/Suflor/modeller-kur.log`, `whispercpp-kur.log`, `pocket-kur.log` (+ `whispercpp-isit.log`, `anlam-dene.log` (doğrulanmadı: konumları yalnız kod yorumlarında)) |

### Güvenli (salt okur) tanılama komutları

```bash
# sihirbaz / kur.sh günlüğü
tail -60 ~/Library/Logs/suflor-kurulum.log
# aktarıcı günlüğü
tail -60 ~/Library/Logs/suflor-aktarici.log
# model indirme ilerlemesi
tail -20 ~/Library/Application\ Support/Suflor/modeller-kur.log
# arka plan ajanı yüklü mü (çıkış 0 = yüklü)
launchctl print gui/$(id -u)/local.suflor.aktarici | head -20
launchctl list | grep suflor
# kurulu sürüm
python3 -c "import json;print(json.load(open('$HOME/Suflor.me/manifest.json'))['version'])"
# KURULUMU DENETLE (salt okur; her madde ✓/✗/? ve "ne yapmalı"; ✗ varsa çıkış kodu 1)
python3 ~/Suflor.me/kurulum.py dogrula
python3 ~/Suflor.me/kurulum.py dogrula --hizli    # izin okumasını (menü uygulamasını açan) atlar
# toplantı/sohbet sürüyor mu (boş çıktı = müsait, çıkış 0)
python3 ~/Suflor.me/kurulum.py mesgul
# aktarıcı durumu: /status yerel anahtar ister (X-Suflor-Anahtar = canli/kart-anahtari.txt). Anahtarı EKRANA/sohbete YAZDIRMA:
APP="$HOME/Library/Application Support/Suflor"
PORT=$(python3 -c "import json;print(json.load(open('$APP/ayar.json')).get('port'))")
curl -s -H "X-Suflor-Anahtar: $(cat "$APP/canli/kart-anahtari.txt")" "http://127.0.0.1:$PORT/status" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print({k:d.get(k) for k in ('surum','alan','whisper','eklenti_kurulu','yerel_ses','saglik')})"
# yalnız "aktarıcı ayakta mı" (anahtarsız; 401 de ayakta demektir)
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:$PORT/status"
# izin/disk/çip
sw_vers; uname -m; df -h ~ | tail -1
```

`dogrula` maddeleri: aktarıcı sürümü, eklenti sürümü, Swift yardımcıları, arka plan ajanı (launchd), whisper.cpp (Core ML), Whisper modeli, anlam araması modeli, izinler (Mikrofon, Erişilebilirlik, Ekran ve Sistem Sesi Kaydı, Bildirimler, Masaüstü/dosya erişimi), BlackHole (yalnız `toplantiya_ses` açıksa), Mac kaynakları, öbür hesabın aktarıcısı, varsayılandan farklı ayarlar. Çıktıda yol yerine `[kullanıcı-klasörü]` yazar; kullanıcıdan çıktıyı olduğu gibi iste.

## 5. Bilinen sorunlar

| Belirti (kesin metin) | Neden | Çözüm |
|---|---|---|
| `Suflor.me yalnız Mac'te çalışır.` | Mac değil | Desteklenmez |
| `Bu Mac'te Apple Silicon (M serisi) işlemci yok…` / sihirbazda `m_intel`: "Suflor.me yalnız Apple Silicon (M1 ve sonrası) işlemcili Mac'lerde çalışır… Kurulum burada duruyor." | Intel Mac | Çözüm yok; yalnız Apple Silicon. Rosetta altında Terminal açılmışsa `uname -m` x86_64 görünür ama kod `sysctl hw.optional.arm64` ile gerçek donanımı sorar: önce `sysctl -n hw.optional.arm64` (1 = M serisi) |
| "Önce Apple'ın komut satırı araçları gerekiyor…" | `/usr/bin/python3` yok ya da < 3.9 | Açılan "Yükle" penceresini bitir (birkaç dakika), `kur.sh` komutunu yeniden yapıştır. Pencere açılmazsa: `xcode-select --install`. Sihirbazda aynısı Python satırı + "Yükle" düğmesi |
| Swift yardımcıları ✗ "N eksik" / `UYARI: … yardımcısı derlenemedi` | `swiftc` yok (komut satırı araçları eksik/yarım) ya da derleme hatası | `xcode-select -p` ve `which swiftc`; yoksa `xcode-select --install`. Sonra `~/Suflor.me/aktarici-kur.command` (çift tık). Etkilenen özellik günlükte adıyla yazar (takvim, karşı ses, brifing, menü uygulaması…) |
| `Kurulum durdu: indirilen kod imzasız` / `imza tutmadı` / `dosya özetleri tutmadı` / `pakette imzalı listede olmayan dosya var`. Güncellemede: `Güncelleme yapılmadı: … İndirilen kod doğrulanamadı; hiçbir dosya değişmedi.` | İndirme yarım/bozuk ya da arada çıkan yayın nedeniyle paket tutarsız (doğrulanmadı: ikinci olasılık çıkarımdır); kurumsal vekil sunucu içeriği değiştiriyor olabilir (doğrulanmadı) | Hiçbir şey kurulmaz, güvenlidir. 5–10 dk sonra komutu yeniden çalıştır. Sürerse: kullanıcının ağını/VPN'ini sor, `curl -I https://codeload.github.com/suflorme/suflor/tar.gz/refs/heads/main` çıktısını iste ve geliştiriciye bildir. Doğrulamayı ATLATMAYI önerme, kodu elle kopyalatma |
| `indirilemedi` / curl hatası / `tar` hatası | Ağ, vekil sunucu | Bağlantıyı denetle, yeniden çalıştır |
| `Suflor.me kurulum sihirbazı: 8770–8779 portlarının hepsi dolu` | Port işgal | `lsof -nP -iTCP:8770-8779 -sTCP:LISTEN`; takılı eski sihirbaz: `pkill -f "kurulum.py --port"`; yeniden dene |
| Sihirbaz sekmesi açılmadı / boş / "yetkisiz" | `?k=` anahtarlı adres kapandı | `kur.sh` komutunu yeniden çalıştır (yeni adres açar). Adres de `~/Library/Logs/suflor-kurulum.log` içinde ("Suflor.me kurulum sihirbazı: http://127.0.0.1:<port>/"); anahtarı elle üretme |
| Sihirbaz kapandı / sekme kapatıldı | — | Aynı komutu yeniden çalıştır; `kurulum.json` sayesinde kaldığı adımdan sürer |
| `Claude Code bulunamadı` (c_yok, c_n_yok) | Claude Code kurulu değil | Sihirbazdaki "Terminal'de kur ve giriş yap" düğmesi Terminal'de `curl -fsSL https://claude.ai/install.sh | bash` çalıştırır ve `~/.zshrc`'ye PATH satırı ekler. Elle: aynı komut |
| `Terminal'de claude komutu bulunmuyor` (c_yol_yok) | Claude `~/.local/bin`'de ama PATH'te değil | "Terminal'e tanıt" düğmesi `export PATH="$HOME/.local/bin:$PATH"` satırını `~/.zshrc` (bash ise `~/.bash_profile`) sonuna ekler. Yeni Terminal aç: `command -v claude` |
| `Oturum açılmamış ya da denetlenmedi` / `Claude Code'da oturum açılmamış.` (c_n_giris) | Terminal'deki Claude giriş yapmamış (Claude masaüstü uygulamasındaki giriş SAYILMAZ) | Terminal'de `claude` yaz, `/login`, hesabını (Pro ya da üstü) seç, bitince `/exit`; sihirbaza dön ("Yeniden denetle"). Sihirbazdaki "Terminal'de giriş yap" düğmesi aynısını açar |
| `Hesabında Claude Code kullanımı yok ya da kullanım sınırın doldu…` (c_n_abonelik) | Abonelik yok/kota dolu (çıktıda credit/subscription/usage limit/quota geçti) | Pro ya da üstü abonelik gerekir; ya sınır sıfırlanınca yeniden dene ya da "Aboneliğim yok, kartsız devam et" ya da "API anahtarı" (Gemini/OpenAI uyumlu) seç. Anahtarı sohbete yapıştırtma (bölüm 6) |
| `Claude 90 saniyede yanıt vermedi…` (c_n_zaman) | Ağ yavaş ya da vekil | İnterneti denetle, "Yeniden denetle" |
| `Claude denetimi başarısız: <ham metin>` (c_n_hata) | Başka hata | Ham metni iste; `claude -p "Yalnız TAMAM yaz."` Terminal'de elle çalıştırtıp çıktıyı iste |
| Mac adımında bellek uyarısı: "Suflor.me 16 GB altında kararlı değil" | RAM < 16 GB | Uyarıdır, devam edilir. ≤ 8 GB: "Hafif kurulum" önerilir (yerel doğal ses, anlamla arama, ikinci Konuş süreci kapalı). Toplantıda diğer uygulamaları kapatmasını söyle |
| Disk satırı kırmızı "7 GB" ; modellerde `Diskte N GB boş — en az 6 GB gerekli. Yer açıp yeniden çalıştır.` | Boş disk yetersiz | Toplam ihtiyaç ~14 GB (modeller ~7 GB, whisper.cpp+Core ML ~2,1 GB dahil, belge çevirme ve arama ~3,3 GB, doğal ses ~1,3 GB isteğe bağlı). `df -h ~`; yer aç; `~/Suflor.me/modeller-kur.command` (olanı yeniden indirmez) ya da sihirbazda "Yeniden dene" |
| "Konuşma tanıma modelleri" kötü: `Modeller kurulamadı. İnternet bağlantını denetleyip yeniden dene.` (+ parantezde günlüğün son hata satırı) | Ağ, disk, Hugging Face/GitHub erişimi | `tail -40 ~/Library/Application\ Support/Suflor/modeller-kur.log`; "Yeniden dene" ya da `~/Suflor.me/modeller-kur.command` (kaldığı yerden; var olanı atlar). Modeller önce açık deponun `modeller-v1` sürümünden (yalnız `gh` oturumu varsa), yoksa Hugging Face'ten iner |
| "Hızlı konuşma tanıma (whisper.cpp + Core ML)": `İnemedi; konuşma tanıma şimdilik MLX ile çalışır, sonraki güncellemede yeniden denenir.` | whisper.cpp paketi/modeli inmedi (SHA-256/imza denetimi) | Uyarıdır, kurulum durmaz. `python3 ~/Suflor.me/kurulum.py whispercpp`; günlük `whispercpp-kur.log`. İlk açılışta Core ML hazırlığı birkaç dakika sürebilir |
| `Modeller bu Mac'teki başka bir hesabın klasöründe ve eksik. O hesapta Suflor.me'yi güncelle (guncelle.command), sonra burada yeniden dene.` | `/Users/Shared/Suflor` başka hesaba ait ve bu hesap yazamıyor | O hesapta `guncelle.command`; ya da bu hesap için ayar `ortak`'ı kendi klasörüne al (doğrulanmadı: bu durumda kod `~/Library/Application Support/Suflor-ortak`'ı seçer; ~5–12 GB iner) |
| "Arka plan hizmeti" kötü: `Arka plan hizmeti kurulamadı: <son satır>` | `kur` hata verdi (HATA: … eksik, launchctl bootstrap hatası, vb.) | `python3 ~/Suflor.me/kurulum.py kur` Terminal'de çalıştır, tam çıktıyı iste; `tail ~/Library/Logs/suflor-aktarici.log`. `launchctl bootstrap` hatası verirse: `launchctl bootout gui/$(id -u)/local.suflor.aktarici` ardından `kur` (doğrulanmadı: bu yöntem koddaki `aktarici_durdur` akışının elle karşılığıdır) |
| `UYARI: aktarıcı yanıt vermiyor. Günlük: …` | Aktarıcı kalkmadı (port çakışması, Python hatası, eksik dosya) | Günlüğün son satırları; `lsof -nP -iTCP:<port> -sTCP:LISTEN`; `kur` yeniden. Panoya ulaşılamıyorsa `~/Suflor.me/guncelle.command` ile yeniden kurulum |
| Kurulum sırasında macOS "Suflor Ses" için izin sorar | Ses yardımcısı Core Audio tap | **İzin Ver**. Elle: Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı (macOS 27'de "Yalnızca Sistem Sesi Kaydı") → Suflor Ses/Suflor.me açık. Sihirbazda "İzin ayarını aç" düğmesi var |
| Takvim: "Takvim izni" bekliyor | Takvim izni verilmedi | macOS penceresinde izin ver. Elle: Sistem Ayarları → Gizlilik ve Güvenlik → Takvimler → Suflor Takvim. Takvim yoksa Sistem Ayarları → İnternet Hesapları'ndan ekle. Atlanabilir |
| Anımsatıcılar: "Anımsatıcılar'a erişilemedi; macOS izni verilmemiş olabilir." | İzin yok | İstenen "Tam erişim"i seç; ya da özelliği kapalı bırak (isteğe bağlı) |
| İzin listede açık görünüyor ama çalışmıyor (güncelleme/yeniden derleme sonrası) | Uygulama yeniden imzalanınca macOS eski izni geçersiz sayar | Sistem Ayarları → Gizlilik ve Güvenlik → ilgili izin → Suflor.me'yi `−` ile kaldır, `+` ile yeniden ekle (Finder'da Command + Shift + G → `~/Applications/Suflor.me.app`); sonra `dogrula` |
| Proje belgeleri/sözlük "okuyamıyor" uyarısı (proje Masaüstü'nde) | Dosya erişimi | Sistem Ayarları → Gizlilik ve Güvenlik → Dosyalar ve Klasörler → Suflor Brifing → Masaüstü'nü aç |
| Mikrofon izni | Eklenti Chrome'da mikrofon ister; masaüstü toplantı için menü uygulaması | Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon → Google Chrome ve Suflor.me açık |
| "Eklentiyi bekliyorum…" takılı | Eklenti yüklenmemiş, farklı Chrome profilinde, ya da Geliştirici modu kapalı | Adımlar (sihirbazda aynısı): (1) `chrome://extensions` aç, sağ üstte **Geliştirici modu**'nu aç. (2) **Paketlenmemiş öğe yükle** → `~/Suflor.me` klasörünü seç (açılan pencerede Command + Shift + G, yolu yapıştır, Enter, Seç). Klasör `manifest.json`'u içeren klasördür. (3) Araç çubuğundaki yapboz simgesinden Suflor.me'yi sabitle. Teams'e girdiğin Chrome PROFİLİNE ekle (birden çok profil varsa doğru pencere). Bağlanma yaklaşık bir dakika sürer (eklenti dakikada bir yoklar). Başka hesabın Suflor.me'si de çalışıyorsa eklenti simgesinden bu hesabın alanını seç |
| Pano/eklentide "Eklenti eski sürümde" | Güncelleme sonrası eklenti yenilenmedi | `chrome://extensions` → Suflor.me → ↻. Eklenti başka klasörden yüklendiyse ayara `"eklenti_kimlik": ["<kimlik>"]` ekle, güncellemeyi yeniden çalıştır |
| Eklenti bağlı ama toplantıda satır gelmiyor | İzin, platform, Chrome yerel mesajlaşma | `dogrula`; KILAVUZ.md "Sorun giderme" bölümüne bak |
| Aynı Mac'te iki macOS hesabı | Modeller ortak klasörde, her hesabın kendi aktarıcısı ve portu var | Bellek tutar (~9–13 GB); kurulumdan önce öbür hesaptan çıkış yap. Port ayrıdır |
| `Kurulmadı: web toplantısı sürüyor` / `sohbet açık` / `Konuş cevabı sürüyor (…)` / `Toplantı oturumu …` (`aktarici-kur.command`); `Güncellenmedi: …`; `Kaldırılmadı: …` | Toplantı, sohbet ya da Konuş cevabı sürerken aktarıcıyı yeniden başlatmak konuşmayı keser; `kurulum.py mesgul` bunu denetler | Toplantı/Sohbet bitince yeniden çalıştır. Başka çare gerekmiyorsa `--zorla` KULLANMA: bölünen toplantıya ve sürmekte olan yanıta mal olur. Yalnız kullanıcı "toplantı yok, yine de olmuyor" diyorsa ve `python3 ~/Suflor.me/kurulum.py mesgul` yanlışlıkla dolu dönüyorsa (örn. takılı sohbet) `--zorla` ile (`guncelle.command --zorla`, `aktarici-kur.command --zorla`) çalıştır ve riski anlat |
| Panoda **Güncelle** düğmesi yok / çalışmıyor | Toplantı sürüyor ya da bildirim haftalık yayınlanır | Elle: `~/Suflor.me/guncelle.command` (çift tık). Günlük `~/Library/Logs/suflor-guncelle.log` |
| `Güncelleme yapılmadı: indirilen vX, kurulu vY'dan eski` / `imzalı sürüm paketteki sürümle aynı değil` | Geri alma koruması / tutarsız paket | Güvenlidir; biraz sonra yeniden dene, sürerse geliştiriciye bildir |
| Güncellemeden sonra `UYARI: çalışan aktarıcı vX, kod vY` | Aktarıcı eski sürümde kaldı | `~/Suflor.me/aktarici-kur.command`; düzelmezse Mac'i yeniden başlat; `dogrula` |
| `git pull başarısız` / `Kod klasöründe kaydedilmemiş değişiklik var` | Yalnız `~/Suflor.me` git klonuysa (kur.sh klasörü klon değildir) | Klon kullanan geliştirici/ileri kullanıcı: `git -C ~/Suflor.me status`; değişiklikleri geri al ya da sakla |
| Her şey kurulu ama panoya erişilmiyor | Aktarıcı kalkmamış | `launchctl list | grep suflor`; `dogrula`; `tail ~/Library/Logs/suflor-aktarici.log`; `aktarici-kur.command` |

### Kaldırma ve güncelleme komutları

- **Güncelleme:** `~/Suflor.me/guncelle.command` (= `python3 kurulum.py guncelle`). İmzayı doğrular, kodu günceller, aktarıcıyı yeniden kurar, `/toplanti` komutunu şablondan yeniler, sonunda "Kurulum denetimi: N ✓, N ✗, N ?" yazar. Ayara ve belgelere dokunmaz.
- **Yalnız arka plan hizmetini yeniden kur:** `~/Suflor.me/aktarici-kur.command` (kaldırmak için `--kaldir`; verisi `canli/`'de kalır).
- **Yalnız modeller:** `~/Suflor.me/modeller-kur.command` (var olanı yeniden indirmez; en az 6 GB boş disk ister).
- **Tamamen kaldırma:** `~/Suflor.me/kaldir.command` (= `python3 kurulum.py sil`). Hiçbir şeyi KALICI silmez, Çöp Sepeti'ne taşır (Finder → Çöp Sepeti → Geri Koy). Taşınanlar: uygulama klasörü, `~/Applications/Suflor.me.app`, launchd plist'i, `~/Library/Logs/suflor*`, Chrome yerel mesajlaşma tanımları, verilen macOS izinleri sıfırlanır (`tccutil`). Modeller (`/Users/Shared/Suflor`), proje klasöründeki toplantı notları ve `~/Suflor.me` kod klasörü AYRICA sorulur. **Proje klasörünün kendisine (belgelere) asla dokunulmaz; kullanıcıya "proje klasörünü de sil" deme, sen de elle `rm` etme.** Başka bir macOS hesabı Suflor.me kullanıyorsa "Modeller de kaldırılsın mı?" sorusuna `h` de. Elle kalanlar: Chrome'da `chrome://extensions` → Suflor.me → Kaldır; Anahtar Zinciri'nde `suflor` ile başlayan öğeler (Gemini anahtarı vb.). Geliştirici git klonunda çalışmaz.
- **Baştan kurmak:** `kaldir.command` sonra `kur.sh` komutu; ya da yalnız `kur.sh` komutunu tekrarlamak (ayar korunur) çoğu zaman yeterlidir.

## 6. Yardım eden yapay zekâ için kurallar

1. Kullanıcıdan API anahtarı, parola, Claude/Google/GitHub oturum belirteci ya da `kart-anahtari.txt`/`ses-anahtari.txt` içeriği isteme ve yapıştırtma. Anahtar yalnız sihirbazdaki alana yazılır (Anahtar Zinciri'ne gider). Tanılama çıktısında anahtar görünürse "bunu sil, paylaşma" de.
2. Önce komutu yeniden çalıştırmayı dene: `kur.sh` ve `guncelle.command` güvenle yeniden çalışır ve kaldığı adımdan sürer.
3. `--zorla` yalnız `mesgul` gerçekten yanlış dolu veriyorsa ve kullanıcı bunu bilerek isterse; nedenini ve riskini (açık toplantı/sohbet/yanıt kesilir) söyle. İmza/özet doğrulamasını atlatma yolu önerme.
4. Silme: yalnız `kaldir.command` (Çöp Sepeti'ne taşır). `rm -rf` önerme. Proje klasörünü silme.
5. Dosya yazma/komut çalıştırma önerirken önce salt okur komutla (bölüm 4) durumu kanıtla; tahminle ayar düzenletme. `ayar.json`'ı elle düzenletecekse önce Suflor'un çalışmadığından emin ol (yazım kilidi var) ve bir kopyasını aldır.
6. Terminal komutlarını kullanıcıya olduğu gibi, tek tek ver. Hata çıktısını iste, sonra bir sonraki adımı ver.
7. Kullanıcı Suflor ile ilgisi olmayan bir hata getiriyorsa (ör. Chrome'un kendi sorunu) bunu söyle.
8. Bildirim: kurulum bittikten sonra panoda "Geri bildirim gönder" düğmesi var (kullanıcı metni + istenirse teknik paket; kimlik, döküm, ad gitmez). Kurulum tamamlanamıyorsa (pano yoksa) ya da imza/sürüm hatası varsa: hata metnini, `dogrula` çıktısını ve `suflor-kurulum.log` son satırlarını geliştiriciye iletmesini söyle (kullanıcı kurulum linkini ve daveti geliştiriciden almıştır; kodda ayrı bir destek adresi yok (doğrulanmadı)). İmza hatalarında kurulum mesajının kendisi de "geliştiriciye haber ver" der.
9. Gizlilik: beta kurulumda yalnız sayı ve seçenek (adım süreleri, hata türü, donanım) geliştiriciye gider; döküm, ses, kişi/proje adı gitmez. Kullanıcı sorarsa bunu söyle; ayrıntı README.md/KILAVUZ.md "Gizlilik" bölümlerinde.
10. Ayrıntılı kullanım ve toplantı sorunları için `KILAVUZ.md` "Sorun giderme" bölümünü kullan; bu dosya yalnız kurulum/güncelleme/kaldırma içindir.
