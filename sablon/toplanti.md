---
description: Suflor.me toplantı modu — kontrol, gündem, hazır kartlar, canlı izleme, bitince özet
argument-hint: <kişi — konu>   örn. Ayşe — bütçe ve takvim
---

Kullanıcı birazdan toplantısına (Teams, Zoom web ya da Meet) giriyor: **$ARGUMENTS**. Suflor.me toplantı modunu başlat.
Bu komut çalışma alanının proje klasöründe ({{PROJE}}) açılmış bir Claude Code oturumunda çalışır; aşağıdaki yollar bu
klasöre göredir. Kısa yaz; kullanıcı birkaç dakika içinde toplantıda olacak.
v0.7.0: kullanıcı toplantıda Option+Shift+K (⌥⇧K) ile (ya da şerit/pano 📷) ekranın kanıt görüntüsünü kaydedebilir — §4'teki ilk mesajda
bunu tek satırla hatırlat.

## 0. Kurallar
`{{KOD}}/TOPLANTI-KURALLARI.md` dosyasını ve bu klasörün `CLAUDE.md`'sini oku ve toplantı boyunca uygula (kart türleri,
sıklık, 120 karakter, DEĞİNME/DUYGU gizliliği, ✓/👁/✕ anlamları). Kurallar orada tek yerde durur; burada tekrarlanmaz.

## 1. Kontrol (tek mesajda, eksikleri tek satırda)
v0.8.5: önce `python3 {{KOD}}/toplanti-claude.py saglik` — ⚠ satırlarını (aktarıcı/eklenti sürümü, Whisper, ses modeli,
bellek, disk) önerisiyle birlikte kullanıcıya tek satırda ilet; "eklenti sinyali yok" toplantıdan önce normaldir. Sonra
`curl -s 127.0.0.1:{{PORT}}/status` çalıştır ve bak:
- Yanıt yok → aktarıcı kapalı: "Aktarıcı çalışmıyor — `{{KOD}}/aktarici-kur.command`'a çift tıkla."
- `extension` boş ya da `age_s` ≥ 30 → "Eklenti sinyali yok — toplantıya Chrome'da gir / Teams sekmesini yenile."
- `extension.panel` false → "Transkript paneli kapalı — Teams: Diğer → Kaydet ve transkript → Transkripti göster.
  Döküm başlamadıysa birinin 'Transkripsiyonu başlat' demesi gerekir."
- `extension.captions` true, `panel` false → altyazı modu: sorun değil (döküm yetkisi yoksa tek yol).
- v0.8.0 `whisper` (yanıtta): `durum` "yok" → Whisper kurulu değil, altyazıyla devam. Toplantı başladıysa `whisper.ben` true
  olmalı (kullanıcının sesi Whisper'a gidiyor); `whisper.karsi` false ise kullanıcıya tek satır: "Karşı tarafın sesi için Teams
  sekmesinde bir kez ⌥⇧W". Whisper akarken Teams altyazısının açık olması yalnız karşı tarafın adı için gerekir.
- Yanıttaki `dil.uyari` doluysa (v0.6.1) kullanıcıya aynen yaz: konuşma dili yanlış ayarlı.
- `python3 {{KOD}}/toplanti-claude.py sozluk | tail -3`: "UYARI: … daha yeni" görürsen
  `sozluk --birlestir` çalıştır (ayardaki dış sözlük kaynağı güncellenmiş). kullanıcıya yazmana gerek yok.
Toplantı henüz başlamadıysa eklenti/panel eksikliği normaldir; uyar ama hazırlığa devam et.

## 2. Rol ve gündem
**v0.9.3 — takvim:** Önce `_canli/takvim-secilen.json`'a bak: son 30 dk içinde yazıldıysa toplantı panodan ya da bildirimden
başlatılmıştır — `konu`, `rol`, `dil` oradan (sorma), `olay` varsa saat (`baslangic`/`bitis` → `agenda.json` `baslangic`/`bitis`,
Mac yerel saati), katılımcılar ve davet notu (`notlar`; içinde gündem maddeleri varsa `items` taslağı onlardan) da oradan.
Dosya yoksa ya da eskiyse: `python3 {{KOD}}/toplanti-claude.py takvim` (Mac Takvim, Takvim uygulamasındaki tüm hesaplar) —
$ARGUMENTS'a uyan toplantıyı bul (`--id` ile tek toplantının tam notu), saatini, katılımcılarını ve davet notunu kullan;
düzenleyen kullanıcıysa rol önerisi `yurutucu`. Takvim boşsa ya da izin yoksa aşağıdaki gibi devam et.

**Rol:** $ARGUMENTS içinde "yürütücü", "katılımcı" ya da "dinleyici" geçiyorsa onu al. Geçmiyorsa gündem sorusuyla
**aynı mesajda** sor: "Rolün: yürütücü (sen yönetiyorsun) · katılımcı · dinleyici? Dil: Türkçe · İngilizce · karışık?"
Dil davetten/katılımcılardan belliyse sorma, yaz . `agenda.json`'a `"dil": "tr" | "en" | "karisik"`;
cevap yoksa `tr`. Dil yanlış ayarlanırsa döküm anlamsız çıkar; Suflor.me bunu iki yönde uyarır. Toplantı başlayana (ilk
`SATIRLAR`) kadar cevap gelmezse: toplantıyı kullanıcı kendisi düzenlediyse `yurutucu`, değilse `katilimci`; sohbete
tek satır yaz ("Rol: katılımcı varsaydım — değiştirmek için 'Claude: dinleyiciyim' notu yaz").
Rolü `_canli/agenda.json`'a `"rol": "yurutucu" | "katilimci" | "dinleyici"` olarak yaz.

**Süre (v0.6.0):** Takvimden (yukarıda) bulunduysa bu adımı atla. Bulunmadıysa: Takvim bağlantısında toplantıyı ara (Outlook ya da Google Takvim, bugün, konu/kişi adıyla; saat
diliminin takvimin döndürdüğü dilim olduğuna dikkat — Mac yerel saatine çevir). Bulursan `agenda.json`'a
`"baslangic": "HH:MM"`, `"bitis": "HH:MM"` yaz; bulamazsan rol sorusuyla aynı mesajda "bitiş saati?" diye sor.
Bitiş yoksa kalan süre/kayma kapalı kalır, sorun değil. Maddelerin süresi farklıysa isteğe bağlı
`"sureler": [dk, …]` (madde sayısı kadar). kullanıcının toplantıdaki adı ayar dosyasındaki adla ({{AD}}) başlamıyorsa `"ben": "<ad>"`.
Yeni gündem yazınca `python3 {{KOD}}/toplanti-claude.py acik sifirla` (v0.7.0: önceki toplantının açık
soruları silinmez, `acik-arsiv.jsonl`'e taşınır; aynı kişiyle sonraki hazırlıkta geri gelir). Kart sınırları rol
tablosunda (TOPLANTI-KURALLARI.md madde 3).

**Gündem:** `_canli/agenda.json` dosyasını oku. Başlığı $ARGUMENTS ile uyuşmuyorsa kullanıcıya tek soru sor: mevcut gündem mi,
yeni gündem mi. `dinleyici`/`katilimci`da gündem çoğu zaman kullanıcının değildir: 6–12 madde taslaklama; kullanıcının
takip etmek istediği 0–5 konuyu sor ya da davetten çıkar, yoksa `items` boş kalır. Yeni gündem gerekiyorsa proje klasöründen taslakla (önce bu klasörün `CLAUDE.md`'sindeki esas belgeler; sonra kişi adıyla `ara`), 6–12 madde; kullanıcı onaylayınca `_canli/agenda.json`'a yaz
(`{"title": "…", "rol": "…", "items": ["…"]}`). Varsa kişiye ait hazırlık notlarını da oku.

## 2b. Bağlam paketi (v0.5.0)
Proje araması: `python3 {{KOD}}/toplanti-claude.py ara "<sorgu>" [--kim <kişi>] [--tur …] [--n 8]`
(tüm proje klasörü: belgeler, tablolar, görüşme dökümleri, `_canli/` toplantıları). Toplantıdan önce (v0.7.0: tek komut):
- `python3 {{KOD}}/toplanti-claude.py hazirlik --kim <kişi>` — kişinin geçmişte söyledikleri, her gündem
  maddesi için ilk 3 sonuç, **önceki toplantılarda o kişiye sorulup cevapsız kalan sorular** (`acik-arsiv.jsonl`) ve
  esas belgelerde kişinin geçtiği satırlar. Yetmeyen madde için ayrıca `ara "…"`.
- Cevapsız kalan eski sorular varsa hazır kart yap (`sor`, tetik o konunun kelimeleri) ve kullanıcıya özetin başında söyle.
- Çıkanlardan kullanıcıya 3–6 satırlık "geçmişte ne dendi / açık kalan ne" özeti yaz (kaynak `dosya @konum`); hazır kartları
  bu açık noktalardan kur, kaynağı `neden`'e yaz. Esas belgeler ve tablolar güncel kayıttır;
  döküm ile tablo çelişiyorsa tabloyu esas al ve çelişkiyi kullanıcıya söyle.

## 3. Hazır kartlar
`_canli/hazir.json` dosyasını bu toplantı için yeniden yaz (eskisinin üzerine):
```json
{"toplanti": "…", "kartlar": [
  {"id": "h1", "gundem": 0, "tetik": ["root", "mfa"], "tur": "sor", "metin": "…", "neden": "…"},
  {"id": "h9", "gundem": 4, "tetik": [], "tur": "cevap", "soru": "kullanıcının sorabileceği soru", "metin": "cevap", "neden": "kaynak dosya"}
]}
```
- Gündem maddesi başına 1–3 kart; çoğu `sor`/`belirt`, gerekiyorsa `deginme`. BİLGİ kartı hazırlama.
- `dinleyici`: `sor`/`belirt` hazırlama; yalnız `cevap` (kullanıcının soracağı olası sorular) ve gerekiyorsa `deginme`.
  `katilimci`: yalnız kullanıcının işini doğrudan ilgilendiren konularda `sor`/`belirt`.
- `tetik`: konu açılınca konuşmada geçecek 2–4 **ayırt edici** kelime/ifade, küçük harf ("iam", "kişisel repo").
  "hesap", "erişim", "şifre" gibi her yerde geçen kelimeleri tetik yapma — yanlış alarm üretir.
  Tetiklerden en az biri **sistem adı** olsun (github, jira, iam) ve dökümdeki olası yanlış yazımı ekle.
  Genel kelime ya da kişi adı tetiği yalnız o madde konuşulurken çalışır.
- `cevap` kartları: kullanıcının toplantıda "Claude'a sor" ile sorabileceği sorular; `tetik` boş kalır, SORU gelince
  kullanılır. Cevabı proje dosyalarından çıkar ve `neden`'e kaynağı yaz; bilmediğini yazma.
- Metin ≤ 120 karakter, emir kipi, tek iş. Şifre/anahtar değeri yok; kişi hakkında yargı yok.
Sonra kullanıcıya kısa liste göster (`h1 · gündem 1 · SOR · metin`) ve bekleme: "çıkar/değiştir" derse düzelt;
`izle` dosya değişince kendiliğinden yeniden yükler.

## 4. İzlemeyi başlat
Monitor aracıyla: `python3 {{KOD}}/toplanti-claude.py izle` (30 dakikada bir yeniden kur).
Sonra: `python3 {{KOD}}/toplanti-claude.py kart bilgi "Suflor.me izliyor · rol <rol> · <N> gündem · <M> hazır kart"`.
kullanıcıya tek satır: "İzliyorum. Kartlar panoda ve Teams şeridinde. Kanıt için Option+Shift+K."

## 5. Toplantı boyunca
Olaylar (satırlar ~20 sn'de bir toplu; SORU hemen): `DURUM`, `DOSYA`, `SATIRLAR (n)`, `NOT (<ad>)`, `SORU q…`, `KART ✓/👁/✕`, `HAZIR hN`;
v0.6.0: `ÖZET İSTEĞİ q…` (SORU gibi, önce bu), `AÇIK SORU aN`, `SÜRE`, `PAY`, satır başında `❓`;
v0.7.0: `KANIT n`, paket altında `BAĞLAM · <sistem>`, `GÜNDEM ▶ i`. Ne yapılacağı: `{{KOD}}/TOPLANTI-KURALLARI.md`
"v0.6.0 olayları" ve "v0.7.0 olayları".
- `SORU q…` → önce `hazir.json`'da uyan `cevap` kartı var mı bak: varsa
  `python3 {{KOD}}/toplanti-claude.py hazir hN --cevap q…`, yoksa `kart cevap "…" --cevap q…`. 30 sn içinde.
- `HAZIR hN` → tetik gerçekten o konuyu mu gösteriyor, konu konuşmada zaten cevaplandı mı, açık kart 3'ü geçiyor
  mu — bunlara bak; uygunsa `python3 {{KOD}}/toplanti-claude.py hazir hN`. Uygun değilse gönderme.
- **Önce kartı gönder, sonra sohbete yaz** (tek satır: ne gönderdin, neden). Gecikme ölçümü için bu sıra önemli.
- **Kart göndermediğin olayda sohbete hiçbir şey yazma** — "kart göndermiyorum" mesajı da yok. Her mesaj bir
  sonraki SORU'yu geciktirir.
- `KART ✕` gelen konuyu bir daha önerme; `👁` gelen kartı tekrar gönderme.

## 6. Toplantı bitince (panel kapanır ya da 5 dk satır gelmez)
Monitor'ü durdur. `_canli/` altındaki bu toplantının `.md` dosyasından özet taslağı çıkar:
Kaynak altyazıysa (başlıkta "Kaynak: Teams canlı altyazı") ya da konuşmacı çoğunlukla "?" ise özetin başına bunu yaz;
kararları ve takip işlerini kişiye bağlama ("kim: belirtilmedi"), metinden emin olmadığın yeri "döküm belirsiz" diye işaretle.
`dinleyici`/`katilimci`da özetin başı "kullanıcı için çıkanlar"dır: kullanıcıya verilen işler, onu etkileyen kararlar ve
tarihler, kullanıcının sorması gereken açık noktalar; sonra kısa genel özet. Gündem yoksa gündem bölümünü atla.
kararlar · gündem maddesi başına durum (konuşuldu / kısmen / açık) · takip işleri (kim — ne — ne zaman) ·
kartlar (✓ yapılan, 👁 okunan, ✕ gerek görülmeyen) · cevapsız sorular (`toplanti-claude.py acik`; kime soruldu) ·
konuşma payı (yürütücüde tek satır, `curl -s 127.0.0.1:{{PORT}}/cards` → `pay`) · hassas ifade uyarıları (yalnız işaret, değer yok) ·
sözlük önerileri (dökümde tekrar eden yanlış yazım → önerilen doğru ad, örnek satır; kullanıcı onaylarsa `sozluk --ekle`).
v0.7.0 — özete üç bölüm daha (ayrıntı CLAUDE.md madde 5): **kanıtlar** (`toplanti-claude.py kanit`; açıklamasızları
Read ile aç; `_kanit/`'a kopyalanacakları öner), **esas belgelere önerilen değişiklikler** (karar kaydı satır
taslakları, DURUM tek satır, xlsx "sekme · satır · sütun: eski → yeni (kaynak)"), ve en başa **karne**:
takip işlerini say, `python3 {{KOD}}/toplanti-claude.py karne --takip T/S --karar K --kaydet`, çıktıyı
"## Karne — not X/5" olarak koy, altına 1–2 cümle nitel değerlendirme (karar çıktı mı, en zayıf boyut, bir dahaki
toplantıya tek öneri). kullanıcıya sunarken ilk satır karnenin notu olsun.
v0.7.2: kullanıcı Teams'in dökümünü indirdiyse (Downloads'ta toplantıdan sonra yeni .docx/.vtt) `python3 {{KOD}}/toplanti-claude.py
karsilastir <dosya> --kaydet` çalıştır; özete tek satır "Döküm kapsamı %X, kaçan N satır" ve en büyük kaçan bölüm konuşma
açısından önemliyse onu Teams dökümünden özete ekle. İndirmediyse hatırlatma yapma.
v0.8.3 (ses verisi; Whisper satırı yoksa boş çıkar, bölümü atla): `toplanti-claude.py kesinlik` → **Kesinleşmesi gereken
iddialar** (kim, ne, kime ne sorulacak) · `anlar` → **Öne çıkan anlar** (saat + bir cümle) · `koc` → **Konuşma koçluğu**
(3–5 satır + tek öneri). ⭐ ÖNEMLİ AN notlarını (v0.8.6: Option + Shift + S) "Öne çıkan anlar"a koy.
Kişi duygu etiketleri özete girmez.
Taslağı `gorusmeler/<kişi>-toplanti-ozeti-<YYYYMMDD>.md` (bu klasörün `CLAUDE.md`'si başka yer söylemiyorsa) olarak kaydet (başına "iç belge, kişi adı
içerir" notu) ve kullanıcıya sun. Esas belgeleri güncellemeyi **öner**; kullanıcı onaylamadan değiştirme.

**Geliştiriciye geri bildirim (v0.9.9, her toplantı sonunda):** özeti sunduktan sonra kullanıcıya tek soru: "Suflor.me'de
aksayan bir şey oldu mu?" Cevabını ve senin gördüğün teknik sorunları (eklenti sinyali kesildi, kart geç gitti, yanlış
konuşmacı, Whisper boş satır, kısayol çalışmadı — saatleriyle) içerik yazmadan topla, sonra:
`python3 {{KOD}}/toplanti-claude.py rapor --not "<gözlemler>"`. Rapor yalnız sürüm, sayı, gecikme ve günlüğün teknik
satırlarını taşır (döküm, kart metni, ad yok); ortak klasöre (`/Users/Shared/Suflor/geri-bildirim`) yazılır ve geliştirme
oturumu açılınca kendiliğinden görünür. Sorun yoksa da çalıştır (`--not "sorun yok"`): ölçümler yine işe yarar.
