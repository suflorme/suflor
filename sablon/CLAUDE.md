# {{ALAN}} — Suflor çalışma alanı

Bu klasör Suflor.me'nin **{{ALAN}}** çalışma alanıdır. Claude bu klasörde açılan oturumda toplantıları izler, kartlarını
bu klasördeki belgelere dayandırır ve özetleri buraya yazar. İçerik iç belgedir (kişi adı içerebilir).

- Toplantı: bu klasörde Claude Code'u aç, `/toplanti <kişi — konu>` yaz.
- Genel toplantı kuralları: `{{KOD}}/TOPLANTI-KURALLARI.md`. Bu dosya alana özgü kuralları ekler; çelişirse bu dosya geçer.
- Suflor.me ayarı: `~/Library/Application Support/Suflor/ayar.json` (alan, ad, port, klasörler). Pano: http://127.0.0.1:{{PORT}}/

## Ben kimim
<!-- 2–4 satır: adın, işin/rolün, hangi kurumla/kimlerle çalıştığın. Claude kartları bu bakış açısıyla yazar. -->
- Ad: {{AD}}
- İş / rol:
- Kurum / müşteriler:

## Kişiler
<!-- Toplantılarda sık geçen kişiler. Claude adları buradan doğru yazar, kime ne sorulacağını buna göre önerir.
     Takma ad ya da aynı adlı iki kişi varsa açıkça yaz. -->
| Ad | Rol / ilişki | Not |
|---|---|---|
| | | |

## Terimler ve doğru yazımlar
<!-- Sistem, ürün, şirket adları ve sık yanlış yazılanlar. Konuşma tanıma yanlış yazarsa Claude özetin
     "Sözlük önerileri" bölümüne ekler; onaylarsan `toplanti-claude.py sozluk --ekle "<yanlış>" "<doğru>"`. -->
| Terim | Anlamı | Yanlış yazımlar |
|---|---|---|
| | | |

## Esas belgeler
<!-- Güncel kayıt sayılan belgeler (durum, karar listesi, tablolar). Toplantıda bunlarla çelişen bir şey söylenirse
     Claude belirt/sor kartı gönderir; özetin sonunda bu belgelere önerilen değişiklikleri yazar (sen onaylamadan yazmaz). -->
- `belgeler/DURUM.md` — işlerin güncel durumu
- `belgeler/KARARLAR.md` — karar listesi (numaralı, eski satır değiştirilmez)

## Klasör haritası
- `belgeler/` — notlar, raporlar, tablolar (.md, .txt, .docx, .xlsx, .csv, .html, .json). Claude toplantıda bunlarda arar.
- `gorusmeler/` — toplantı özetleri ve görüşme dökümleri (Suflor.me özetleri buraya yazar; "görüşme" türünde aranır).
- `_canli/` — canlı dökümler, kartlar, gündem (Suflor.me yönetir; kısayol). Elle düzenleme.
- `_kanit/` — toplantıda alınan ve saklamaya değer ekran görüntüleri.
- `_arsiv/` — eski, güncel olmayan belgeler: aramaya girmez.

## Toplantı özeti
- Yer: `gorusmeler/<kişi>-toplanti-ozeti-<YYYYMMDD>.md`
- Esas belgelere yalnız sen onaylayınca kısa satır eklenir.
