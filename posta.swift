// Suflor.me v0.85.0 — posta yardımcısı ("Suflor Posta.app"). Mac'teki Mail uygulamasının yerel ileti dizinini (~/Library/Mail/V*/MailData/Envelope Index,
// SQLite) YALNIZ OKUR; son günlerin iletilerinden gönderen, konu, tarih, kutu, okundu ve Mail'in kendi kısa özetini JSON'a yazar ve kapanır. Ağ yok;
// ileti gövdesi (.emlx) açılmaz, hiçbir şey değiştirilmez. Mail klasörü macOS korumasında: izin (Gizlilik ve Güvenlik → Tam Disk Erişimi) yalnız bu
// uygulamaya verilir. İzin yoksa {"durum": "izin"} yazar. Aktarıcı `open -g -W -a "Suflor Posta.app" --args --cikti <yol> --gun 14` ile çalıştırır.
// Şema sürümden sürüme değişebildiği için sütunlar PRAGMA ile denetlenir; zorunlu olanlar yoksa {"durum": "sema"}.
// Deneme: --db <yol> (sahte dizin), --cikti <yol>.
import Foundation
import SQLite3

var cikti = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Application Support/Suflor/posta.json")
var gun = 14.0, enCok = 400
var dbYol: String? = nil
var i = 1
let a = CommandLine.arguments
while i < a.count {
  if a[i] == "--cikti", i + 1 < a.count { cikti = a[i + 1]; i += 1 }
  else if a[i] == "--gun", i + 1 < a.count { gun = Double(a[i + 1]) ?? 14; i += 1 }
  else if a[i] == "--en-cok", i + 1 < a.count { enCok = Int(a[i + 1]) ?? 400; i += 1 }
  else if a[i] == "--db", i + 1 < a.count { dbYol = a[i + 1]; i += 1 }
  i += 1
}
let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]

func yaz(_ o: [String: Any]) {
  var o = o
  o["guncel"] = iso.string(from: Date())
  guard let d = try? JSONSerialization.data(withJSONObject: o, options: []) else { return }
  try? FileManager.default.createDirectory(atPath: (cikti as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
  let gecici = cikti + ".tmp"
  FileManager.default.createFile(atPath: gecici, contents: d, attributes: [.posixPermissions: 0o600])  // ileti başlıkları kişi adı içerir
  _ = try? FileManager.default.replaceItemAt(URL(fileURLWithPath: cikti), withItemAt: URL(fileURLWithPath: gecici))
  if !FileManager.default.fileExists(atPath: cikti) { try? FileManager.default.moveItem(atPath: gecici, toPath: cikti) }
}

// En yeni Mail sürüm klasörü (V10, V11 …)
func dizinBul() -> String? {
  if let d = dbYol { return d }
  let mail = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Mail")
  guard let ic = try? FileManager.default.contentsOfDirectory(atPath: mail) else { return nil }
  let v = ic.filter { $0.hasPrefix("V") && Int($0.dropFirst()) != nil }.sorted { Int($0.dropFirst())! > Int($1.dropFirst())! }
  for x in v {
    let y = (mail as NSString).appendingPathComponent("\(x)/MailData/Envelope Index")
    if FileManager.default.fileExists(atPath: y) { return y }
  }
  return nil
}

// Mail klasörü korumalıysa listeleme de başarısız olur: izin yok
let mailKlasor = (NSHomeDirectory() as NSString).appendingPathComponent("Library/Mail")
if dbYol == nil, (try? FileManager.default.contentsOfDirectory(atPath: mailKlasor)) == nil {
  yaz(["durum": "izin", "hata": "Mail klasörü okunamadı — Tam Disk Erişimi Suflor Posta'ya verilmeli", "iletiler": []]); exit(0)
}
guard let yol = dizinBul() else { yaz(["durum": "yok", "hata": "Mail ileti dizini bulunamadı (Mail hiç açılmamış olabilir)", "iletiler": []]); exit(0) }

var db: OpaquePointer?
let uri = "file:" + (yol.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? yol) + "?mode=ro"
if sqlite3_open_v2(uri, &db, SQLITE_OPEN_READONLY | SQLITE_OPEN_URI, nil) != SQLITE_OK {
  yaz(["durum": "izin", "hata": "ileti dizini açılamadı", "iletiler": []]); exit(0)
}
sqlite3_busy_timeout(db, 3000)

func sutunlar(_ tablo: String) -> Set<String> {
  var s = Set<String>(); var st: OpaquePointer?
  if sqlite3_prepare_v2(db, "PRAGMA table_info(\(tablo))", -1, &st, nil) == SQLITE_OK {
    while sqlite3_step(st) == SQLITE_ROW { if let c = sqlite3_column_text(st, 1) { s.insert(String(cString: c)) } }
  }
  sqlite3_finalize(st); return s
}
let m = sutunlar("messages"), ad = sutunlar("addresses"), sj = sutunlar("subjects"), mb = sutunlar("mailboxes"), sm = sutunlar("summaries")
guard m.isSuperset(of: ["sender", "subject", "date_received", "mailbox"]), ad.contains("address"), sj.contains("subject"), mb.contains("url") else {
  yaz(["durum": "sema", "hata": "Mail ileti dizininin yapısı tanınmadı", "iletiler": []]); exit(0)
}
let okundu = m.contains("read") ? "m.read" : "NULL"
let silindi = m.contains("deleted") ? "AND IFNULL(m.deleted, 0) = 0" : ""
let ozet = (m.contains("summary") && sm.contains("summary")) ? "(SELECT s.summary FROM summaries s WHERE s.ROWID = m.summary)" : "NULL"
let yorum = ad.contains("comment") ? "a.comment" : "NULL"
let onek = m.contains("subject_prefix") ? "m.subject_prefix" : "NULL"
let sinir = Date().timeIntervalSince1970 - gun * 86400
let sql = """
SELECT m.date_received, \(yorum), a.address, \(onek), su.subject, mbx.url, \(okundu), \(ozet)
FROM messages m LEFT JOIN addresses a ON a.ROWID = m.sender LEFT JOIN subjects su ON su.ROWID = m.subject LEFT JOIN mailboxes mbx ON mbx.ROWID = m.mailbox
WHERE m.date_received >= ? \(silindi) ORDER BY m.date_received DESC LIMIT ?
"""
var st: OpaquePointer?
guard sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK else {
  yaz(["durum": "sema", "hata": "sorgu hazırlanamadı: " + String(cString: sqlite3_errmsg(db)), "iletiler": []]); exit(0)
}
sqlite3_bind_double(st, 1, sinir); sqlite3_bind_int(st, 2, Int32(enCok * 2))
func metin(_ k: Int32) -> String? { if let c = sqlite3_column_text(st, k) { return String(cString: c) }; return nil }
// kutu adı: URL'nin son bölümü (yüzde kodlu) — INBOX, Sent Messages, [Gmail]/Gönderilmiş Postalar …
let atla = try! NSRegularExpression(pattern: "(trash|junk|spam|deleted|drafts|çöp|gereksiz|taslak|silin|istenmeyen|bin)", options: [.caseInsensitive])
let gonder = try! NSRegularExpression(pattern: "(sent|gönderil|giden)", options: [.caseInsensitive])
var iletiler: [[String: Any]] = []
while sqlite3_step(st) == SQLITE_ROW && iletiler.count < enCok {
  let t = sqlite3_column_double(st, 0)
  let url = metin(5) ?? ""
  let kutu = (URL(string: url)?.pathComponents.filter { $0 != "/" }.joined(separator: "/")).flatMap { $0.removingPercentEncoding ?? $0 } ?? url
  let r = NSRange(kutu.startIndex..., in: kutu)
  if atla.firstMatch(in: kutu, range: r) != nil { continue }
  var o: [String: Any] = ["t": iso.string(from: Date(timeIntervalSince1970: t)), "adres": metin(2) ?? "", "konu": ((metin(3) ?? "") + (metin(4) ?? "")).trimmingCharacters(in: .whitespaces),
                          "kutu": String(kutu.suffix(60)), "gonderilen": gonder.firstMatch(in: kutu, range: r) != nil]
  if let y = metin(1), !y.isEmpty { o["ad"] = y }
  if okundu != "NULL", sqlite3_column_type(st, 6) != SQLITE_NULL { o["okundu"] = sqlite3_column_int(st, 6) != 0 }
  if let z = metin(7), !z.isEmpty { o["ozet"] = String(z.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ").prefix(300)) }
  iletiler.append(o)
}
sqlite3_finalize(st); sqlite3_close(db)
yaz(["durum": "ok", "hata": NSNull(), "iletiler": iletiler, "dizin": (yol as NSString).deletingLastPathComponent.components(separatedBy: "/").suffix(2).joined(separator: "/")])
