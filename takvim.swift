// Suflor.me v0.9.3 — takvim yardımcısı ("Suflor Takvim.app"). Mac'in Takvim'indeki (Exchange/Outlook, Google, iCloud —
// Takvim uygulamasına eklenmiş tüm hesaplar) yaklaşan toplantıları okuyup JSON yazar ve kapanır. Ağ yok; yalnız yerel
// takvim veritabanı. Aktarıcı 5 dk'da bir `open -g -W -a "Suflor Takvim.app" --args --cikti <yol>` ile çalıştırır.
// Takvim izni macOS'ta uygulamaya verilir: ilk çalıştırmada "Suflor Takvim takvimlerine erişmek istiyor" sorulur.
// Kurulum: aktarici-kur.command derler (swiftc) ve uygulama klasörüne koyar.
import EventKit
import Foundation

var cikti = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Application Support/Suflor/takvim.json")
var saatOnce = 3.0, saatSonra = 24.0
var i = 1
let a = CommandLine.arguments
while i < a.count {
  if a[i] == "--cikti", i + 1 < a.count { cikti = a[i + 1]; i += 1 }
  else if a[i] == "--once", i + 1 < a.count { saatOnce = Double(a[i + 1]) ?? 3; i += 1 }
  else if a[i] == "--sonra", i + 1 < a.count { saatSonra = Double(a[i + 1]) ?? 24; i += 1 }
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
let baglantiRe = try! NSRegularExpression(pattern: "https://(teams\\.microsoft\\.com/l/meetup-join|teams\\.live\\.com/meet|teams\\.microsoft\\.com/meet|[a-z0-9.-]*zoom\\.us/(j|my|w)/|meet\\.google\\.com/)[^\\s<>\")]*", options: [.caseInsensitive])
func baglanti(_ metinler: [String?]) -> String? {
  for m in metinler {
    guard let m = m, !m.isEmpty else { continue }
    if let r = baglantiRe.firstMatch(in: m, range: NSRange(m.startIndex..., in: m)), let rr = Range(r.range, in: m) { return String(m[rr]) }
  }
  return nil
}
func platform(_ u: String?) -> String? {
  guard let u = u?.lowercased() else { return nil }
  if u.contains("teams.") { return "teams" }
  if u.contains("zoom.us") { return "zoom" }
  if u.contains("meet.google") { return "meet" }
  return nil
}

let store = EKEventStore()
let bitti = DispatchSemaphore(value: 0)
func oku(_ izin: Bool, _ hata: Error?) {
  defer { bitti.signal() }
  guard izin else { yaz(["durum": "izin_yok", "hata": hata?.localizedDescription ?? "Takvim izni verilmedi (Sistem Ayarları → Gizlilik ve Güvenlik → Takvimler → Suflor Takvim)", "olaylar": []]); return }
  let simdi = Date()
  let p = store.predicateForEvents(withStart: simdi.addingTimeInterval(-saatOnce * 3600), end: simdi.addingTimeInterval(saatSonra * 3600), calendars: nil)
  var olaylar: [[String: Any]] = []
  for e in store.events(matching: p).sorted(by: { $0.startDate < $1.startDate }) {
    if e.status == .canceled { continue }
    let ben = e.attendees?.first(where: { $0.isCurrentUser })
    if ben?.participantStatus == .declined { continue }
    var o: [String: Any] = [
      "id": e.calendarItemIdentifier, "baslik": e.title ?? "", "baslangic": iso.string(from: e.startDate), "bitis": iso.string(from: e.endDate),
      "tum_gun": e.isAllDay, "takvim": e.calendar.title, "hesap": e.calendar.source.title,
    ]
    if let y = e.location, !y.isEmpty { o["yer"] = y }
    if let n = e.notes, !n.isEmpty { o["notlar"] = String(n.prefix(4000)) }
    let b = baglanti([e.url?.absoluteString, e.location, e.notes])
    if let b = b { o["baglanti"] = b; o["platform"] = platform(b) }
    if let org = e.organizer { o["duzenleyen"] = org.name ?? ""; o["ben_duzenleyen"] = org.isCurrentUser }
    if let at = e.attendees { o["katilimcilar"] = at.filter { !$0.isCurrentUser }.compactMap { $0.name }.prefix(30).map { $0 } ; o["kisi_sayisi"] = at.count }
    olaylar.append(o)
  }
  yaz(["durum": "ok", "olaylar": olaylar])
}
if #available(macOS 14.0, *) { store.requestFullAccessToEvents { izin, hata in oku(izin, hata) } }
else { store.requestAccess(to: .event) { izin, hata in oku(izin, hata) } }
if bitti.wait(timeout: .now() + 120) == .timedOut { yaz(["durum": "zaman_asimi", "hata": "Takvim izni penceresi yanıtlanmadı", "olaylar": []]) }
