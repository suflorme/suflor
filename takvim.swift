// Suflor.me v0.9.3 — takvim yardımcısı ("Suflor Takvim.app"). Mac'in Takvim'indeki (Exchange/Outlook, Google, iCloud —
// Takvim uygulamasına eklenmiş tüm hesaplar) yaklaşan toplantıları okuyup JSON yazar ve kapanır. Ağ yok; yalnız yerel
// takvim veritabanı. Aktarıcı 5 dk'da bir `open -g -W -a "Suflor Takvim.app" --args --cikti <yol>` ile çalıştırır.
// Takvim izni macOS'ta uygulamaya verilir: ilk çalıştırmada "Suflor Takvim takvimlerine erişmek istiyor" sorulur.
// Kurulum: aktarici-kur.command derler (swiftc) ve uygulama klasörüne koyar.
import Contacts
import EventKit
import Foundation

var cikti = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Application Support/Suflor/takvim.json")
var saatOnce = 3.0, saatSonra = 24.0
var adaylar = false  // --adaylar: olay yerine kullanıcının olası takvim adresleri (kurulum sihirbazı seçtirir)
var ayrinti = false  // --ayrinti: her olaya katılımcı adresleri ve "current user" işareti (teşhis; aktarıcı kullanmaz)
var etkinlik: String? = nil  // v0.132.0: --etkinlik <istek.json> {"baslik", "zaman": "YYYY-MM-DDTHH:MM" (yerel), "dk", "not", "takvim"} → takvime hatırlatma etkinliği
var etkinlikSil: String? = nil  // --etkinlik-sil <kimlik>: Suflor'un eklediği etkinliği siler
var kisiAd: String? = nil  // S225 (5 Kasım): --kisi <ad> → Mac Kişiler'de ada göre arama (yalnız okuma; en çok 20 eşleşme: ad, kurum, e-postalar, telefonlar, posta adresi, doğum günü; ad, kurum ya da e-postada arar)
var kisiOzet = false  // --kisi-ozet: Kişiler'de yalnız SAYILAR (toplam, telefonlu, e-postalı, adresli, doğum günlü, kurumlu); --kurum-say ile kuruma göre ilk 10 sayım. Ad/iletişim verisi yazılmaz
var kurumSay = false
var tarihGun: Int? = nil  // S243: --tarihler <gün> → Kişiler'deki doğum günü/tarihler + Takvim'in doğum günleri/tüm gün etkinlikleri/Suflor hatırlatmaları + Anımsatıcılar'daki tarihli öğeler (yalnız okuma; ham, pencere hesabı aktarıcıda)
var takvimler = false  // --takvimler: yazılabilir takvimler (ayar hatirlatma_takvim seçimi için)
var animListeler = false  // S258: --anim-listeler → Anımsatıcılar listeleri (ad, hesap, yazılabilir); izin penceresini de bu açar
var animEsitle: String? = nil  // S258: --anim-esitle <istek.json> {"liste", "olustur", "ekle": [{kayit_id, baslik, vade?, not}], "guncelle": [{id, baslik, vade?}], "tamamla": [{id, tamam}], "sil": [id]} → uygular, listenin son durumunu yazar
var adresler = Set<String>()  // --adres a@x,b@y (ayar takvim_adreslerim): kullanıcının takvim adresleri, büyük-küçük harf duyarsız
var goster = Set<String>()  // v0.167.0: --goster "<takvim adı> · <hesap>" (yinelenir): bu takvimlerde süzgeçten geçmeyen etkinlikler de "paylasilan": true ile yazılır (aktarıcı yalnız panoda gösterir; ayar takvim_paylasilan)
var i = 1
let a = CommandLine.arguments
while i < a.count {
  if a[i] == "--cikti", i + 1 < a.count { cikti = a[i + 1]; i += 1 }
  else if a[i] == "--once", i + 1 < a.count { saatOnce = Double(a[i + 1]) ?? 3; i += 1 }
  else if a[i] == "--sonra", i + 1 < a.count { saatSonra = Double(a[i + 1]) ?? 24; i += 1 }
  else if a[i] == "--ayrinti" { ayrinti = true }
  else if a[i] == "--adaylar" { adaylar = true }
  else if a[i] == "--etkinlik", i + 1 < a.count { etkinlik = a[i + 1]; i += 1 }
  else if a[i] == "--etkinlik-sil", i + 1 < a.count { etkinlikSil = a[i + 1]; i += 1 }
  else if a[i] == "--takvimler" { takvimler = true }
  else if a[i] == "--anim-listeler" { animListeler = true }
  else if a[i] == "--anim-esitle", i + 1 < a.count { animEsitle = a[i + 1]; i += 1 }
  else if a[i] == "--tarihler", i + 1 < a.count { tarihGun = max(1, min(Int(a[i + 1]) ?? 14, 90)); i += 1 }
  else if a[i] == "--kisi", i + 1 < a.count { kisiAd = a[i + 1]; i += 1 }
  else if a[i] == "--kisi-ozet" { kisiOzet = true }
  else if a[i] == "--kurum-say" { kurumSay = true }
  else if a[i] == "--goster", i + 1 < a.count { goster.insert(a[i + 1].trimmingCharacters(in: .whitespaces)); i += 1 }
  else if a[i] == "--adres", i + 1 < a.count {
    adresler = Set(a[i + 1].split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }.filter { !$0.isEmpty }); i += 1
  }
  i += 1
}
let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]

func yaz(_ o: [String: Any]) {
  var o = o
  o["guncel"] = iso.string(from: Date())
  if let d = try? JSONSerialization.data(withJSONObject: o, options: [.prettyPrinted]) {
    try? FileManager.default.createDirectory(atPath: (cikti as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
    let gecici = cikti + ".tmp"
    FileManager.default.createFile(atPath: gecici, contents: d)
    _ = try? FileManager.default.replaceItemAt(URL(fileURLWithPath: cikti), withItemAt: URL(fileURLWithPath: gecici))
    if !FileManager.default.fileExists(atPath: cikti) { try? FileManager.default.moveItem(atPath: gecici, toPath: cikti) }
  }
}

// Toplantı bağlantısı: konum, adres alanı ya da davet metnindeki ilk Teams / Zoom / Meet adresi
// v0.12.3 (güvenlik denetimi D2): alan adı tam eşleşir — eskiden [a-z0-9.-]*zoom\.us "evilzoom.us"u da kabul ediyordu.
// Zoom yalnız zoom.us ya da alt alanı (us02web.zoom.us); ardından hemen "/" gelmeli (zoom.us.evil.com, @ ile kullanıcı adı geçmez).
let baglantiRe = try! NSRegularExpression(pattern: "https://(teams\\.microsoft\\.com/l/meetup-join/|teams\\.microsoft\\.com/meet/|teams\\.live\\.com/meet/|teams\\.cloud\\.microsoft/|([a-z0-9-]+\\.)*zoom\\.us/(j|my|w)/|meet\\.google\\.com/)[^\\s<>\")]*", options: [.caseInsensitive])
func baglanti(_ metinler: [String?]) -> String? {
  for m in metinler {
    guard let m = m, !m.isEmpty else { continue }
    if let r = baglantiRe.firstMatch(in: m, range: NSRange(m.startIndex..., in: m)), let rr = Range(r.range, in: m) { return String(m[rr]) }
  }
  return nil
}
func platform(_ u: String?) -> String? {
  guard let u = u, let h = URL(string: u)?.host?.lowercased() else { return nil }
  if ["teams.microsoft.com", "teams.live.com", "teams.cloud.microsoft"].contains(h) { return "teams" }
  if h == "zoom.us" || h.hasSuffix(".zoom.us") { return "zoom" }
  if h == "meet.google.com" { return "meet" }
  return nil
}

// Yalnız kullanıcının toplantıları: Takvim'e eklenmiş başkalarının paylaşılan takvimlerindeki etkinlikler (kullanıcı ne davetli
// ne düzenleyen) ve katılımcısız kişisel kayıtlar listeye girmez. Kullanıcı = EventKit'in "current user"ı ya da adresi
// --adres listesinde olan kişi; adres verildiyse yalnız adres: EventKit paylaşılan takvimde takvim sahibini "current user"
// sayıyor (9 Ekim ölçümü). Aynı toplantı birkaç takvimde varsa (kullanıcının ve katılımcının paylaşılan takvimi) bir kez yazılır,
// kullanıcının kendi takvimindeki kopya seçilir. Reddedilen davet "reddettin" işaretiyle kalır.
func adres(_ p: EKParticipant) -> String {
  let u = p.url.absoluteString.lowercased()
  return u.hasPrefix("mailto:") ? String(u.dropFirst(7)) : u
}
func ben(_ p: EKParticipant?) -> Bool { guard let p = p else { return false }; return adresler.isEmpty ? p.isCurrentUser : adresler.contains(adres(p)) }
// v0.167.0: Ayarlar'daki "paylaşılan takvimler" listesi için her okumada tüm etkinlik takvimleri (ad, hesap, tür)
func takvimTur(_ c: EKCalendar) -> String {
  let ad = c.title.lowercased(), kaynak = c.source.title.lowercased()
  switch c.source.sourceType {
  case .exchange: return "exchange"
  case .local: return "yerel"
  case .birthdays: return "dogumgunu"
  case .subscribed: return ad.contains("tatil") || ad.contains("holiday") ? "tatil" : "abonelik"
  case .mobileMe: return "icloud"
  default:
    if c.type == .subscription { return ad.contains("tatil") || ad.contains("holiday") ? "tatil" : "abonelik" }
    return kaynak.contains("google") ? "google" : kaynak.contains("icloud") ? "icloud" : "caldav"
  }
}
func kendiTakvimi(_ e: EKEvent) -> Bool { ((e.attendees ?? []) + (e.organizer.map { [$0] } ?? [])).contains { ben($0) && $0.isCurrentUser } }

let store = EKEventStore()
let bitti = DispatchSemaphore(value: 0)
func oku(_ izin: Bool, _ hata: Error?) {
  defer { bitti.signal() }
  guard izin else { yaz(["durum": "izin_yok", "hata": hata?.localizedDescription ?? "Takvim izni verilmedi (Sistem Ayarları → Gizlilik ve Güvenlik → Takvimler → Suflor Takvim)", "olaylar": []]); return }
  let simdi = Date()
  let p = store.predicateForEvents(withStart: simdi.addingTimeInterval(-saatOnce * 3600), end: simdi.addingTimeInterval(saatSonra * 3600), calendars: nil)
  var olaylar: [[String: Any]] = []
  if adaylar {
    // Aday: olaylarda "current user" işaretli katılımcı/düzenleyen adresleri ve adı e-posta olan takvimler (Google'da kendi takvimin).
    // Paylaşılan takvimde sahibi de "current user" göründüğü için hangisinin kullanıcı olduğu burada bilinmez — sihirbaz sorar.
    var ad = [String: [String: Any]]()
    func ekle(_ adr: String, _ isim: String?, _ e: EKCalendar) {
      guard adr.contains("@"), !adr.contains(" ") else { return }
      var x = ad[adr] ?? ["adres": adr, "sayi": 0, "takvim": e.title, "hesap": e.source.title]
      x["sayi"] = (x["sayi"] as? Int ?? 0) + 1
      if let isim = isim, !isim.isEmpty, x["ad"] == nil { x["ad"] = isim }
      ad[adr] = x
    }
    for c in store.calendars(for: .event) where c.title.contains("@") { ekle(c.title.lowercased(), nil, c) }
    for e in store.events(matching: p) {
      for k in (e.attendees ?? []) + (e.organizer.map { [$0] } ?? []) where k.isCurrentUser { ekle(adres(k), k.name, e.calendar) }
    }
    yaz(["durum": "ok", "adaylar": ad.values.sorted { ($0["sayi"] as? Int ?? 0) > ($1["sayi"] as? Int ?? 0) }.prefix(20).map { $0 }])
    return
  }
// SUZGEC-BAS
// Etkinlik süzgeci (EventKit'siz saf karar; test/takvim-suzgec.py bu bloğu metinden çıkarıp derler)
// Exchange davetsiz etkinlikte düzenleyeni boş bırakır: kullanıcının yazabildiği takvimdeki düzenleyensiz etkinlik onundur
func kendiMi(duzenleyenVar: Bool, benDuzenleyen: Bool, yazilabilir: Bool) -> Bool { benDuzenleyen || (!duzenleyenVar && yazilabilir) }
func olayAlinir(digerBos: Bool, duzenleyenVar: Bool, benDuzenleyen: Bool, benKatilan: Bool, yazilabilir: Bool, baglantiVar: Bool) -> Bool {
  let kendi = kendiMi(duzenleyenVar: duzenleyenVar, benDuzenleyen: benDuzenleyen, yazilabilir: yazilabilir)
  // katılımcısız kayıt (yalnız kullanıcı) atlanır; kullanıcının düzenlediği bağlantılı toplantı kalır (deneme toplantısı tek kişilik açılır)
  if digerBos && !(duzenleyenVar && !benDuzenleyen) && !(kendi && baglantiVar) { return false }
  if !benKatilan && !kendi { return false }  // kullanıcının olmadığı etkinlik (paylaşılan takvim)
  return true
}
// SUZGEC-SON

  var gorulen = Set<String>(), gorulenPay = Set<String>()
  for e in store.events(matching: p).sorted(by: { $0.startDate != $1.startDate ? $0.startDate < $1.startDate : kendiTakvimi($0) && !kendiTakvimi($1) }) {
    if e.status == .canceled { continue }
    let katilan = e.attendees ?? []
    let benKatilan = katilan.first(where: { ben($0) }), benDuzenleyen = ben(e.organizer)
    let kendi = kendiMi(duzenleyenVar: e.organizer != nil, benDuzenleyen: benDuzenleyen, yazilabilir: e.calendar.allowsContentModifications)
    let digerleri = katilan.filter { !ben($0) && !($0.url == e.organizer?.url && benDuzenleyen) }
    if ayrinti {  // teşhis: atlananlar da yazılır
      olaylar.append(["baslik": e.title ?? "", "takvim": e.calendar.title, "duzenleyen": e.organizer.map { "\(adres($0)) cu=\($0.isCurrentUser)" } ?? "-",
                      "katilan": katilan.map { "\(adres($0)) cu=\($0.isCurrentUser) \($0.participantStatus.rawValue)" }, "kendi": kendi,
                      "baglanti": baglanti([e.url?.absoluteString, e.location, e.notes]) != nil])
      continue
    }
    let alinir = olayAlinir(digerBos: digerleri.isEmpty, duzenleyenVar: e.organizer != nil, benDuzenleyen: benDuzenleyen, benKatilan: benKatilan != nil,
                            yazilabilir: e.calendar.allowsContentModifications, baglantiVar: baglanti([e.url?.absoluteString, e.location, e.notes]) != nil)
    let anahtar = "\(e.startDate.timeIntervalSince1970)|\(e.title ?? "")"
    var paylasilan = false
    if !alinir {  // v0.167.0: kullanıcının seçtiği paylaşılan takvimde süzgeçten geçmeyen etkinlik (reddedilen hariç); süzgeç mantığı değişmez
      guard goster.contains("\(e.calendar.title) · \(e.calendar.source.title)"), benKatilan?.participantStatus != .declined, !gorulen.contains(anahtar), gorulenPay.insert(anahtar).inserted else { continue }
      paylasilan = true
    } else if !gorulen.insert(anahtar).inserted { continue }  // başka takvimdeki kopya
    var o: [String: Any] = [
      "id": e.calendarItemIdentifier, "baslik": e.title ?? "", "baslangic": iso.string(from: e.startDate), "bitis": iso.string(from: e.endDate),
      "tum_gun": e.isAllDay, "takvim": e.calendar.title, "hesap": e.calendar.source.title,
    ]
    if paylasilan { o["paylasilan"] = true }
    if let y = e.location, !y.isEmpty { o["yer"] = y }
    if let n = e.notes, !n.isEmpty { o["notlar"] = String(n.prefix(4000)) }
    let b = baglanti([e.url?.absoluteString, e.location, e.notes])
    if let b = b { o["baglanti"] = b; o["platform"] = platform(b) }
    if let org = e.organizer { o["duzenleyen"] = org.name ?? ""; o["ben_duzenleyen"] = benDuzenleyen }
    if benKatilan?.participantStatus == .declined && !benDuzenleyen { o["reddettin"] = true }
    if !katilan.isEmpty { o["katilimcilar"] = katilan.filter { !ben($0) }.compactMap { $0.name }.prefix(30).map { $0 } ; o["kisi_sayisi"] = katilan.count }
    // panodan "E-posta: katılımcılara" taslağı için adresler (kullanıcının kendisi hariç; düzenleyen katılımcılarda yoksa eklenir)
    var ep = katilan.filter { !ben($0) }.map { adres($0) }
    if let org = e.organizer, !benDuzenleyen, !ep.contains(adres(org)) { ep.append(adres(org)) }
    ep = ep.filter { $0.contains("@") && !$0.contains("/") && !$0.contains(" ") }
    if !ep.isEmpty { o["katilimci_eposta"] = Array(ep.prefix(30)) }
    // v0.143.0: ad–adres eşleri (sesle istenen toplantının davetlileri adla söylenir; adres geçmiş toplantılardan bulunur)
    let kisiler: [[String: String]] = (katilan + (e.organizer.map { [$0] } ?? [])).filter { !ben($0) }.compactMap { k in
      let a = adres(k); guard let n = k.name, !n.isEmpty, a.contains("@"), !a.contains("/"), !a.contains(" ") else { return nil }; return ["ad": n, "eposta": a] }
    if !kisiler.isEmpty { o["kisiler"] = Array(kisiler.prefix(30)) }
    olaylar.append(o)
  }
  yaz(["durum": "ok", "olaylar": olaylar, "takvimler": store.calendars(for: .event).map { ["ad": $0.title, "hesap": $0.source.title, "tur": takvimTur($0)] }])
}
// v0.132.0 (kullanıcı 25 Ekim: hatırlatma Anımsatıcılar'da değil takvimde görünsün): sesle istenen hatırlatma takvime saatinde başlayan, başında uyaran
// kısa etkinlik olur (varsayılan takvim ya da istekteki "takvim" adı — Exchange/Google takvimiyse sunucuya, telefona eşitlenir). Silme yalnız verilen kimlikle.
func zamanOku(_ s: String) -> Date? {
  let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.timeZone = TimeZone.current
  for b in ["yyyy-MM-dd'T'HH:mm", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd HH:mm"] { f.dateFormat = b; if let d = f.date(from: s) { return d } }
  return nil
}
func yazilabilir() -> [EKCalendar] { store.calendars(for: .event).filter { $0.allowsContentModifications } }
func etkinlikIs(_ izin: Bool, _ hata: Error?) {
  defer { bitti.signal() }
  guard izin else { yaz(["durum": "izin_yok", "hata": hata?.localizedDescription ?? "Takvim izni verilmedi"]); return }
  if takvimler {
    let v = store.defaultCalendarForNewEvents
    yaz(["durum": "ok", "takvimler": yazilabilir().map { ["ad": $0.title, "hesap": $0.source.title, "varsayilan": $0.calendarIdentifier == v?.calendarIdentifier] }]); return
  }
  if let k = etkinlikSil {
    guard let e = store.event(withIdentifier: k) else { yaz(["durum": "yok", "hata": "etkinlik bulunamadı (silinmiş olabilir)"]); return }
    do { try store.remove(e, span: .thisEvent, commit: true); yaz(["durum": "ok", "baslik": e.title ?? ""]) } catch { yaz(["durum": "hata", "hata": error.localizedDescription]) }
    return
  }
  guard let yol = etkinlik, let d = FileManager.default.contents(atPath: yol), let j = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
        let baslik = j["baslik"] as? String, !baslik.isEmpty, let z = j["zaman"] as? String, let t = zamanOku(z) else { yaz(["durum": "hata", "hata": "istek okunamadı (başlık ve saat gerekir)"]); return }
  let ad = (j["takvim"] as? String) ?? ""
  guard let tk = (ad.isEmpty ? nil : yazilabilir().first { $0.title == ad }) ?? store.defaultCalendarForNewEvents, tk.allowsContentModifications else {
    yaz(["durum": "hata", "hata": ad.isEmpty ? "yazılabilir varsayılan takvim yok" : "takvim bulunamadı: \(ad)"]); return }
  let e = EKEvent(eventStore: store); e.title = String(baslik.prefix(300)); e.calendar = tk
  e.startDate = t; e.endDate = t.addingTimeInterval(Double((j["dk"] as? Int) ?? 15) * 60); e.addAlarm(EKAlarm(relativeOffset: 0))
  if let n = j["not"] as? String, !n.isEmpty { e.notes = String(n.prefix(2000)) }
  do { try store.save(e, span: .thisEvent, commit: true); yaz(["durum": "ok", "id": e.eventIdentifier ?? "", "takvim": tk.title, "hesap": tk.source.title]) }
  catch { yaz(["durum": "hata", "hata": error.localizedDescription]) }
}
// --kisi <ad> (S225): Mac Kişiler'den yalnız okuma. Çıktı {"durum": "ok", "kisiler": [{"ad","kurum","eposta":[],"telefon":[],"adres":[]}]} ya da
// {"durum": "izin_yok"|"hata", "hata": "<açık metin>"}. Takvim izni istenmez; Kişiler izni bu uygulamaya verilir (NSContactsUsageDescription).
func kisiFold(_ s: String) -> String { s.folding(options: [.diacriticInsensitive, .caseInsensitive, .widthInsensitive], locale: Locale(identifier: "tr_TR")).replacingOccurrences(of: "ı", with: "i") }
func kisiAra(_ ad: String) {
  let anahtar: [CNKeyDescriptor] = [CNContactGivenNameKey, CNContactFamilyNameKey, CNContactOrganizationNameKey, CNContactEmailAddressesKey, CNContactPhoneNumbersKey, CNContactPostalAddressesKey, CNContactBirthdayKey].map { $0 as CNKeyDescriptor }
  let kt = CNContactStore()
  let en = 20  // en çok eşleşme
  var bul: [CNContact] = []
  var gorulen = Set<String>()
  do {
    for c in try kt.unifiedContacts(matching: CNContact.predicateForContacts(matchingName: ad), keysToFetch: anahtar) where bul.count < en { if gorulen.insert(c.identifier).inserted { bul.append(c) } }
    // Türkçe harf/büyük-küçük farkı ve kurum/e-posta alanı: tüm kişilerde katlanmış karşılaştırma (sorgu sözcüklerinin hepsi ad, kurum ya da e-postalarda geçmeli)
    let n = kisiFold(ad).split(separator: " ").map(String.init)
    if !n.isEmpty && bul.count < en {
      try kt.enumerateContacts(with: CNContactFetchRequest(keysToFetch: anahtar)) { c, dur in
        if gorulen.contains(c.identifier) { return }
        let tam = kisiFold(c.givenName + " " + c.familyName + " " + c.organizationName + " " + c.emailAddresses.map { String($0.value) }.joined(separator: " "))
        if n.allSatisfy({ tam.contains($0) }) { gorulen.insert(c.identifier); bul.append(c); if bul.count >= en { dur.pointee = true } }
      }
    }
  } catch { yaz(["durum": "hata", "hata": error.localizedDescription]); return }
  let cikis: [[String: Any]] = bul.prefix(en).map { c in
    let adres = c.postalAddresses.map { CNPostalAddressFormatter.string(from: $0.value, style: .mailingAddress).replacingOccurrences(of: "\n", with: ", ") }
    var o: [String: Any] = ["ad": (c.givenName + " " + c.familyName).trimmingCharacters(in: .whitespaces), "kurum": c.organizationName,
            "eposta": c.emailAddresses.map { String($0.value) }, "telefon": c.phoneNumbers.map { $0.value.stringValue }, "adres": adres]
    if let b = c.birthday, let m = b.month, let g = b.day { o["dogum"] = (b.year.map { $0 > 1900 ? String(format: "%04d-", $0) : "" } ?? "") + String(format: "%02d-%02d", m, g) }
    return o
  }
  yaz(["durum": "ok", "kisiler": cikis])
}
// --kisi-ozet: yalnız sayılar. {"durum":"ok","toplam","telefonlu","epostali","adresli","dogumlu","kurumlu", "kurumlar"?: [{"kurum","sayi"}] (yalnız --kurum-say, ilk 10)}
func kisiOzetle() {
  let anahtar: [CNKeyDescriptor] = [CNContactOrganizationNameKey, CNContactEmailAddressesKey, CNContactPhoneNumbersKey, CNContactPostalAddressesKey, CNContactBirthdayKey].map { $0 as CNKeyDescriptor }
  var top = 0, tel = 0, ep = 0, adr = 0, dg = 0, kur = 0
  var kurumlar: [String: Int] = [:]
  do {
    try CNContactStore().enumerateContacts(with: CNContactFetchRequest(keysToFetch: anahtar)) { c, _ in
      top += 1
      if !c.phoneNumbers.isEmpty { tel += 1 }
      if !c.emailAddresses.isEmpty { ep += 1 }
      if !c.postalAddresses.isEmpty { adr += 1 }
      if let b = c.birthday, b.month != nil, b.day != nil { dg += 1 }
      let k = c.organizationName.trimmingCharacters(in: .whitespaces)
      if !k.isEmpty { kur += 1; kurumlar[k, default: 0] += 1 }
    }
  } catch { yaz(["durum": "hata", "hata": error.localizedDescription]); return }
  var o: [String: Any] = ["durum": "ok", "toplam": top, "telefonlu": tel, "epostali": ep, "adresli": adr, "dogumlu": dg, "kurumlu": kur]
  if kurumSay { o["kurumlar"] = kurumlar.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(10).map { ["kurum": $0.key, "sayi": $0.value] as [String: Any] } }
  yaz(o)
}
func kisiIzinle(_ is_: @escaping () -> Void) {
  switch CNContactStore.authorizationStatus(for: .contacts) {
  case .authorized: is_()
  case .notDetermined:
    CNContactStore().requestAccess(for: .contacts) { izin, hata in
      if izin { is_() } else { yaz(["durum": "izin_yok", "hata": hata?.localizedDescription ?? "Kişiler izni verilmedi: Sistem Ayarları → Gizlilik ve Güvenlik → Kişiler → Suflor Takvim"]) }
      bitti.signal()
    }
    if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Kişiler izni penceresi yanıtlanmadı"]) }
  default: yaz(["durum": "izin_yok", "hata": "Kişiler izni yok: Sistem Ayarları → Gizlilik ve Güvenlik → Kişiler → Suflor Takvim'i aç"])
  }
}
if kisiOzet { kisiIzinle { kisiOzetle() }; exit(0) }
if let ad = kisiAd {
  let a = ad.trimmingCharacters(in: .whitespacesAndNewlines)
  if a.isEmpty || a.count > 80 { yaz(["durum": "hata", "hata": "ad boş ya da çok uzun"]); exit(0) }
  switch CNContactStore.authorizationStatus(for: .contacts) {
  case .authorized: kisiAra(a)
  case .notDetermined:
    CNContactStore().requestAccess(for: .contacts) { izin, hata in
      if izin { kisiAra(a) } else { yaz(["durum": "izin_yok", "hata": hata?.localizedDescription ?? "Kişiler izni verilmedi: Sistem Ayarları → Gizlilik ve Güvenlik → Kişiler → Suflor Takvim"]) }
      bitti.signal()
    }
    if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Kişiler izni penceresi yanıtlanmadı"]) }
  default: yaz(["durum": "izin_yok", "hata": "Kişiler izni yok: Sistem Ayarları → Gizlilik ve Güvenlik → Kişiler → Suflor Takvim'i aç"])
  }
  exit(0)
}
// --tarihler <gün> (S243): yaklaşan kişisel tarihler, YALNIZ OKUMA. Üç izin ayrı istenir ve ayrı raporlanır; biri yoksa öbürleri yine okunur:
//   {"durum": "ok", "izinler": {"kisiler": Bool, "animsaticilar": Bool, "takvim": Bool},
//    "kisiler": [{"ad", "dogum": {"ay","gun","yil"?}?, "tarihler": [{"etiket","yildonumu": Bool,"ay","gun","yil"?}]}],        // Kişiler: doğum günü ve diğer tarihler (yıl yoksa alan yok)
//    "dogum_takvimi": [{"baslik","tarih"}],        // Takvim'in Doğum Günleri takvimi (pencere içi; "YYYY-MM-DD")
//    "suflor": [{"baslik","tarih","saat"?}],       // sesle eklenen hatırlatmalar (notunda Suflor.me işareti)
//    "etkinlikler": [{"baslik","tarih"}],          // tatil/abonelik olmayan takvimlerdeki tüm gün etkinlikleri
//    "animsaticilar": [{"baslik","tarih","saat"?}]} // tamamlanmamış, bitiş tarihi pencerede olan Anımsatıcılar
// Yazma/kaydetme çağrısı yok; içerik bu Mac dışına gitmez (aktarıcı yerel).
func gunYaz(_ d: Date) -> String { let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.timeZone = TimeZone.current; f.dateFormat = "yyyy-MM-dd"; return f.string(from: d) }
func bilesenGun(_ c: DateComponents) -> String? {
  guard let y = c.year, let m = c.month, let g = c.day else { return nil }
  return String(format: "%04d-%02d-%02d", y, m, g)
}
func tarihlerOku(_ gun: Int) {
  var izinler: [String: Bool] = ["kisiler": false, "animsaticilar": false, "takvim": false]
  var cikis: [String: Any] = ["durum": "ok"]
  let bugun = Calendar.current.startOfDay(for: Date()), son = Calendar.current.date(byAdding: .day, value: gun + 1, to: bugun)!
  // 1) Kişiler
  let kt = CNContactStore()
  var kd = CNContactStore.authorizationStatus(for: .contacts)
  if kd == .notDetermined {
    let s = DispatchSemaphore(value: 0); kt.requestAccess(for: .contacts) { _, _ in s.signal() }; _ = s.wait(timeout: .now() + 120)
    kd = CNContactStore.authorizationStatus(for: .contacts)
  }
  var kisiler: [[String: Any]] = []
  if kd == .authorized {
    izinler["kisiler"] = true
    let anahtar: [CNKeyDescriptor] = [CNContactGivenNameKey, CNContactFamilyNameKey, CNContactNicknameKey, CNContactOrganizationNameKey, CNContactBirthdayKey, CNContactDatesKey].map { $0 as CNKeyDescriptor }
    func bil(_ c: DateComponents) -> [String: Any]? {
      guard let m = c.month, let g = c.day else { return nil }
      var o: [String: Any] = ["ay": m, "gun": g]
      if let y = c.year, y > 1900 { o["yil"] = y }
      return o
    }
    try? kt.enumerateContacts(with: CNContactFetchRequest(keysToFetch: anahtar)) { c, _ in
      let dogum = c.birthday.flatMap { bil($0) }
      let diger: [[String: Any]] = c.dates.compactMap { d in
        guard var o = bil(d.value as DateComponents) else { return nil }
        let et = d.label ?? ""
        o["etiket"] = et.isEmpty ? "" : CNLabeledValue<NSDateComponents>.localizedString(forLabel: et)
        o["yildonumu"] = et.lowercased().contains("anniversary")
        return o
      }
      if dogum == nil && diger.isEmpty { return }
      var ad = (c.givenName + " " + c.familyName).trimmingCharacters(in: .whitespaces)
      if ad.isEmpty { ad = c.nickname.isEmpty ? c.organizationName : c.nickname }
      if ad.isEmpty { return }
      var o: [String: Any] = ["ad": ad, "tarihler": diger]
      if let d = dogum { o["dogum"] = d }
      kisiler.append(o)
    }
  }
  cikis["kisiler"] = kisiler
  // 2) Takvim: doğum günleri takvimi, Suflor hatırlatmaları, tüm gün etkinlikleri
  var tizin = false
  let ds = DispatchSemaphore(value: 0)
  if #available(macOS 14.0, *) { store.requestFullAccessToEvents { ok, _ in tizin = ok; ds.signal() } }
  else { store.requestAccess(to: .event) { ok, _ in tizin = ok; ds.signal() } }
  _ = ds.wait(timeout: .now() + 120)
  var dogumT: [[String: Any]] = [], suflorT: [[String: Any]] = [], etk: [[String: Any]] = []
  if tizin {
    izinler["takvim"] = true
    var gorulen = Set<String>()
    for e in store.events(matching: store.predicateForEvents(withStart: bugun, end: son, calendars: nil)).sorted(by: { $0.startDate < $1.startDate }) {
      if e.status == .canceled { continue }
      let baslik = e.title ?? ""; if baslik.isEmpty { continue }
      let tarih = gunYaz(e.startDate)
      if tarih < gunYaz(bugun) || !gorulen.insert(tarih + "|" + baslik).inserted { continue }
      let tur = takvimTur(e.calendar)
      if tur == "dogumgunu" { dogumT.append(["baslik": baslik, "tarih": tarih]); continue }
      let not = e.notes ?? ""
      if not.contains("Suflor.me") && (not.contains("sesle eklendi") || not.contains("added by voice")) {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "HH:mm"
        suflorT.append(["baslik": baslik, "tarih": tarih, "saat": f.string(from: e.startDate)]); continue
      }
      if e.isAllDay && tur != "tatil" && tur != "abonelik" { etk.append(["baslik": baslik, "tarih": tarih]) }
    }
  }
  cikis["dogum_takvimi"] = dogumT; cikis["suflor"] = suflorT; cikis["etkinlikler"] = etk
  // 3) Anımsatıcılar
  var rizin = false
  let rs = DispatchSemaphore(value: 0)
  if #available(macOS 14.0, *) { store.requestFullAccessToReminders { ok, _ in rizin = ok; rs.signal() } }
  else { store.requestAccess(to: .reminder) { ok, _ in rizin = ok; rs.signal() } }
  _ = rs.wait(timeout: .now() + 120)
  var an: [[String: Any]] = []
  if rizin {
    izinler["animsaticilar"] = true
    let fs = DispatchSemaphore(value: 0)
    store.fetchReminders(matching: store.predicateForIncompleteReminders(withDueDateStarting: bugun, ending: son, calendars: nil)) { liste in
      for r in liste ?? [] {
        guard let dc = r.dueDateComponents, let t = Calendar.current.date(from: dc), let b = r.title, !b.isEmpty else { continue }
        var o: [String: Any] = ["baslik": b, "tarih": gunYaz(t)]
        if dc.hour != nil, let h = dc.hour { o["saat"] = String(format: "%02d:%02d", h, dc.minute ?? 0) }
        an.append(o)
      }
      fs.signal()
    }
    _ = fs.wait(timeout: .now() + 60)
  }
  cikis["animsaticilar"] = an
  cikis["izinler"] = izinler
  yaz(cikis)
}
// S258: Anımsatıcılar eşitlemesi. Yalnız kullanıcının seçtiği tek listeye dokunur; öğeler aktarıcının verdiği kimlikle (calendarItemIdentifier) bulunur, başka listedeki öğeye ya da
// listenin dışındaki kimliğe yazılmaz. Kabuk metni yok: istek JSON dosyası. Silme yalnız "sil" listesindeki, bu listeden gelen kimlikler.
func animIzin() -> Bool {
  let s = DispatchSemaphore(value: 0); var ok = false
  if #available(macOS 14.0, *) { store.requestFullAccessToReminders { o, _ in ok = o; s.signal() } }
  else { store.requestAccess(to: .reminder) { o, _ in ok = o; s.signal() } }
  _ = s.wait(timeout: .now() + 120); return ok
}
func animTarih(_ s: String?) -> DateComponents? {
  guard let s = s, s.count >= 10 else { return nil }
  let p = s.prefix(10).split(separator: "-").compactMap { Int($0) }
  if p.count != 3 { return nil }
  var dc = DateComponents(); dc.calendar = Calendar.current; dc.year = p[0]; dc.month = p[1]; dc.day = p[2]; return dc
}
func animListeIs() {
  guard animIzin() else { yaz(["durum": "izin_yok", "hata": "Anımsatıcılar izni verilmedi"]); return }
  var l: [[String: Any]] = []
  for c in store.calendars(for: .reminder) { l.append(["ad": c.title, "hesap": c.source.title, "yazilabilir": c.allowsContentModifications]) }
  yaz(["durum": "ok", "listeler": l])
}
func animEsitleIs(_ yol: String) {
  guard animIzin() else { yaz(["durum": "izin_yok", "hata": "Anımsatıcılar izni verilmedi"]); return }
  guard let d = FileManager.default.contents(atPath: yol), let q = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] else { yaz(["durum": "hata", "hata": "İstek okunamadı"]); return }
  let ad = ((q["liste"] as? String) ?? "").trimmingCharacters(in: .whitespaces)
  if ad.isEmpty { yaz(["durum": "hata", "hata": "Liste adı yok"]); return }
  var cal = store.calendars(for: .reminder).first(where: { $0.title == ad && $0.allowsContentModifications })
  if cal == nil && (q["olustur"] as? Bool) == true {
    let yeni = EKCalendar(for: .reminder, eventStore: store); yeni.title = ad
    guard let kaynak = store.defaultCalendarForNewReminders()?.source ?? store.sources.first(where: { $0.sourceType == .local }) ?? store.sources.first else { yaz(["durum": "hata", "hata": "Liste kaynağı yok"]); return }
    yeni.source = kaynak
    do { try store.saveCalendar(yeni, commit: true); cal = yeni } catch { yaz(["durum": "hata", "hata": "Liste oluşturulamadı: " + error.localizedDescription]); return }
  }
  guard let liste = cal else { yaz(["durum": "liste_yok", "hata": "Liste bulunamadı"]); return }
  func oge(_ id: Any?) -> EKReminder? {
    guard let id = id as? String, let r = store.calendarItem(withIdentifier: id) as? EKReminder, r.calendar.calendarIdentifier == liste.calendarIdentifier else { return nil }
    return r
  }
  var hata = 0; var eklenen: [[String: Any]] = []
  for e in (q["ekle"] as? [[String: Any]]) ?? [] {
    guard let b = e["baslik"] as? String, !b.isEmpty else { hata += 1; continue }
    let r = EKReminder(eventStore: store); r.calendar = liste; r.title = b; r.notes = e["not"] as? String
    if let dc = animTarih(e["vade"] as? String) { r.dueDateComponents = dc }
    do { try store.save(r, commit: false); eklenen.append(["kayit_id": (e["kayit_id"] as? String) ?? "", "id": r.calendarItemIdentifier]) } catch { hata += 1 }
  }
  for e in (q["guncelle"] as? [[String: Any]]) ?? [] {
    guard let r = oge(e["id"]) else { hata += 1; continue }
    if let b = e["baslik"] as? String, !b.isEmpty { r.title = b }
    if e.keys.contains("vade") { r.dueDateComponents = animTarih(e["vade"] as? String) }
    if let n = e["not"] as? String { r.notes = n }
    do { try store.save(r, commit: false) } catch { hata += 1 }
  }
  for e in (q["tamamla"] as? [[String: Any]]) ?? [] {
    guard let r = oge(e["id"]) else { hata += 1; continue }
    r.isCompleted = (e["tamam"] as? Bool) ?? true
    do { try store.save(r, commit: false) } catch { hata += 1 }
  }
  for id in (q["sil"] as? [String]) ?? [] {
    guard let r = oge(id) else { continue }
    do { try store.remove(r, commit: false) } catch { hata += 1 }
  }
  do { try store.commit() } catch { hata += 1 }
  var ogeler: [[String: Any]] = []
  let fs = DispatchSemaphore(value: 0)
  store.fetchReminders(matching: store.predicateForReminders(in: [liste])) { rs in
    for r in rs ?? [] {
      var o: [String: Any] = ["id": r.calendarItemIdentifier, "baslik": r.title ?? "", "tamam": r.isCompleted]
      if let dc = r.dueDateComponents, let y = dc.year, let m = dc.month, let g = dc.day { o["vade"] = String(format: "%04d-%02d-%02d", y, m, g) }
      if let t = r.lastModifiedDate { o["degisti"] = iso.string(from: t) }
      ogeler.append(o)
    }
    fs.signal()
  }
  _ = fs.wait(timeout: .now() + 60)
  yaz(["durum": "ok", "liste": ad, "ogeler": ogeler, "eklenen": eklenen, "hata_say": hata])
}
if animListeler { animListeIs(); exit(0) }
if let y = animEsitle { animEsitleIs(y); exit(0) }
if let g = tarihGun { tarihlerOku(g); exit(0) }
if etkinlik != nil || etkinlikSil != nil || takvimler {
  if #available(macOS 14.0, *) { store.requestFullAccessToEvents { izin, hata in etkinlikIs(izin, hata) } }
  else { store.requestAccess(to: .event) { izin, hata in etkinlikIs(izin, hata) } }
  if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Takvim izni penceresi yanıtlanmadı"]) }
  exit(0)
}
if #available(macOS 14.0, *) { store.requestFullAccessToEvents { izin, hata in oku(izin, hata) } }
else { store.requestAccess(to: .event) { izin, hata in oku(izin, hata) } }
if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Takvim izni penceresi yanıtlanmadı", "olaylar": []]) }
