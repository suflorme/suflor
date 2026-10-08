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
- **Toplantı sonu:** özet, kararlar, takip işleri, cevapsız kalan sorular ve toplantı için 1–5 arası bir not.

## Gizlilik
- Ses ve döküm **Mac'inden çıkmaz.** Konuşma tanıma yereldir; ses diske yazılmaz.
- Aktarıcı yalnız `127.0.0.1` adresinde çalışır; hiçbir sunucuya veri göndermez.
- Claude'a giden metin, senin Claude Code oturumunun gördükleridir (Anthropic'in kullanım koşulları geçerli).
- Toplantı dosyaları senin proje klasöründe durur; kişi adı içerir, iç belge gibi davran.

## Gerekenler
- Apple Silicon (M serisi) işlemcili Mac, macOS 14 ya da üstü
- En az 16 GB bellek (konuşma tanıma ve ses modeli toplantı sırasında ~4 GB kullanır)
- ~7 GB boş disk (modeller ~5 GB)
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

**Güncelleme:** yeni sürüm çıkınca panonun sağ üstünde **Güncelle** düğmesi belirir (toplantı yokken); tıklaman yeter, Chrome
eklentisi de kendini yeniler. Elle: `~/Suflor.me/guncelle.command`'a çift tıkla (son sürümü indirir, aktarıcıyı yeniden kurar; ayarlarına ve
belgelerine dokunmaz). Eklenti kendini yenilemezse: Chrome'da `chrome://extensions` → Suflor.me → yenile.

## Kullanım (kısaca)
1. Toplantıdan önce panodaki takvimden **Başlat**'a bas (ya da proje klasöründeki Claude Code oturumunda `/toplanti`).
   Claude gündemi kurar, hazır olunca toplantıya katılırsın.
2. Karşı tarafın sesi kendiliğinden yazıya dökülür (Suflor Ses yardımcısı, macOS 14.4+; ilk kurulumda macOS "Sistem Sesi Kaydı" izni
   sorar — İzin Ver). Yardımcı yoksa ya da izin verilmediyse **Suflor.me simgesi → Karşı taraf → Aç**.
3. Kartlar Teams'in sol altındaki küçük şeritte ve panoda görünür: **SÖYLE** (şunu de/sor), **DUR** (yapma/açma), **CEVAP**; **NOT** yalnız panoda. ✓ yaptım · Okudum · ✕ gerek yok.
4. Kısayollar: **Option + Shift + K** kanıt · **Option + Shift + O** son 1 dakikanın özeti · **Option + Shift + M** sessiz (10 dk kart yok; tekrar basınca kapanır). Kartı "Sonra" (⏸) ile gündemde sıradaki maddeye bırakabilirsin. ⭐ önemli an panoda düğme.
5. Toplantı bitince Claude özeti çıkarır ve sana sunar.

## Bileşenler
| Parça | Ne iş yapar |
|---|---|
| Chrome eklentisi (`manifest.json`, `content.js`, `platform-teams.js`, …) | Teams sayfasından altyazı/döküm ve mikrofon sesini alır, şeridi gösterir |
| Aktarıcı (`relay.py`) | Yerel sunucu: satırları dosyaya yazar, kartları tutar, panoyu sunar |
| Ses yardımcısı (`ses-yardimcisi.swift` → Suflor Ses.app) | Toplantı uygulamasının sesini (karşı taraf) macOS'tan alır; mikrofonu almaz, ses diske yazılmaz |
| Konuşma tanıma (`whisper-isci.py`) | Whisper large-v3-turbo (kurulumda yerelde 8 bite indirilir) ve konuşmacı ses izi (ECAPA), ikisi de MLX ile yerel |
| Claude köprüsü (`toplanti-claude.py`, `baglam.py`) | Claude'un izlediği olay akışı, kart gönderme, proje araması, özet araçları |
| Kurallar (`TOPLANTI-KURALLARI.md`, `sablon/`) | Claude'un toplantıdaki davranış kuralları ve `/toplanti` komutu |

## Lisans
MIT — ayrıntı [LICENSE](LICENSE).
