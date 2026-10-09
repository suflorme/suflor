// Suflor.me v0.9.3 — takvim yardımcısı ("Suflor Takvim.app"). Mac'in Takvim'indeki (Exchange/Outlook, Google, iCloud —
// Takvim uygulamasına eklenmiş tüm hesaplar) yaklaşan toplantıları okuyup JSON yazar ve kapanır. Ağ yok; yalnız yerel
// takvim veritabanı. Aktarıcı 5 dk'da bir `open -g -W -a "Suflor Takvim.app" --args --cikti <yol>` ile çalıştırır.
// Takvim izni macOS'ta uygulamaya verilir: ilk çalıştırmada "Suflor Takvim takvimlerine erişmek istiyor" sorulur.
// Kurulum: aktarici-kur.command derler (swiftc) ve uygulama klasörüne koyar.
import EventKit
import Foundation

var cikti = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Application Support/Suflor/takvim.json")
var saatOnce = 3.0, saatSonra = 24.0
var adaylar = false  // --adaylar: olay yerine kullanıcının olası takvim adresleri (kurulum sihirbazı seçtirir)
var ayrinti = false  // --ayrinti: her olaya katılımcı adresleri ve "current user" işareti (teşhis; aktarıcı kullanmaz)
var adresler = Set<String>()  // --adres a@x,b@y (ayar takvim_adreslerim): kullanıcının takvim adresleri, büyük-küçük harf duyarsız
var i = 1
let a = CommandLine.arguments
while i < a.count {
  if a[i] == "--cikti", i + 1 < a.count { cikti = a[i + 1]; i += 1 }
  else if a[i] == "--once", i + 1 < a.count { saatOnce = Double(a[i + 1]) ?? 3; i += 1 }
  else if a[i] == "--sonra", i + 1 < a.count { saatSonra = Double(a[i + 1]) ?? 24; i += 1 }
  else if a[i] == "--ayrinti" { ayrinti = true }
  else if a[i] == "--adaylar" { adaylar = true }
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
  var gorulen = Set<String>()
  for e in store.events(matching: p).sorted(by: { $0.startDate != $1.startDate ? $0.startDate < $1.startDate : kendiTakvimi($0) && !kendiTakvimi($1) }) {
    if e.status == .canceled { continue }
    let katilan = e.attendees ?? []
    let benKatilan = katilan.first(where: { ben($0) }), benDuzenleyen = ben(e.organizer)
    let digerleri = katilan.filter { !ben($0) && !($0.url == e.organizer?.url && benDuzenleyen) }
    if digerleri.isEmpty && !(e.organizer != nil && !benDuzenleyen) { continue }  // katılımcısız kayıt (yalnız kullanıcı)
    if ayrinti {
      olaylar.append(["baslik": e.title ?? "", "takvim": e.calendar.title, "duzenleyen": e.organizer.map { "\(adres($0)) cu=\($0.isCurrentUser)" } ?? "-",
                      "katilan": katilan.map { "\(adres($0)) cu=\($0.isCurrentUser) \($0.participantStatus.rawValue)" }])
      continue
    }
    if benKatilan == nil && !benDuzenleyen { continue }  // kullanıcının olmadığı etkinlik (paylaşılan takvim)
    if !gorulen.insert("\(e.startDate.timeIntervalSince1970)|\(e.title ?? "")").inserted { continue }  // başka takvimdeki kopya
    var o: [String: Any] = [
      "id": e.calendarItemIdentifier, "baslik": e.title ?? "", "baslangic": iso.string(from: e.startDate), "bitis": iso.string(from: e.endDate),
      "tum_gun": e.isAllDay, "takvim": e.calendar.title, "hesap": e.calendar.source.title,
    ]
    if let y = e.location, !y.isEmpty { o["yer"] = y }
    if let n = e.notes, !n.isEmpty { o["notlar"] = String(n.prefix(4000)) }
    let b = baglanti([e.url?.absoluteString, e.location, e.notes])
    if let b = b { o["baglanti"] = b; o["platform"] = platform(b) }
    if let org = e.organizer { o["duzenleyen"] = org.name ?? ""; o["ben_duzenleyen"] = benDuzenleyen }
    if benKatilan?.participantStatus == .declined && !benDuzenleyen { o["reddettin"] = true }
    if !katilan.isEmpty { o["katilimcilar"] = katilan.filter { !ben($0) }.compactMap { $0.name }.prefix(30).map { $0 } ; o["kisi_sayisi"] = katilan.count }
    olaylar.append(o)
  }
  yaz(["durum": "ok", "olaylar": olaylar])
}
if #available(macOS 14.0, *) { store.requestFullAccessToEvents { izin, hata in oku(izin, hata) } }
else { store.requestAccess(to: .event) { izin, hata in oku(izin, hata) } }
if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Takvim izni penceresi yanıtlanmadı", "olaylar": []]) }
