// Suflor.me v0.85.0 — posta yardımcısı ("Suflor Posta.app"). Mac'teki Mail uygulamasının yerel ileti dizinini (~/Library/Mail/V*/MailData/Envelope Index,
// SQLite) YALNIZ OKUR; son günlerin iletilerinden gönderen, konu, tarih, kutu, okundu ve Mail'in kendi kısa özetini JSON'a yazar ve kapanır. Ağ yok;
// ileti gövdesi (.emlx) açılmaz, hiçbir şey değiştirilmez. Mail klasörü macOS korumasında: izin (Gizlilik ve Güvenlik → Tam Disk Erişimi) yalnız bu
// uygulamaya verilir. İzin yoksa {"durum": "izin"} yazar. Aktarıcı `open -g -W -a "Suflor Posta.app" --args --cikti <yol> --gun 14` ile çalıştırır.
// Şema sürümden sürüme değişebildiği için sütunlar PRAGMA ile denetlenir; zorunlu olanlar yoksa {"durum": "sema"}.
// Deneme: --db <yol> (sahte dizin), --cikti <yol>; --db yalnız deneme derlemesinde (swiftc -D SUFLOR_DENEME).
// v0.97.4 (güvenlik denetimi O3): Tam Disk Erişimi bu uygulamada — aynı hesaptaki başka bir program onu argümanla çalıştırıp izni ödünç alamasın:
// çıktı yalnız uygulama klasörünün (<uygulama>, bu paketin bulunduğu klasör) altına ve yalnız posta.json / posta-govde.json adıyla; geçici dosya
// sembolik bağı izlemeden açılır; --db (başka SQLite dosyasını okutma) kurulu sürümde yok.
import Foundation
import SQLite3

func gercek(_ y: String) -> String {  // sembolik bağları çözülmüş mutlak yol (C realpath; dosya yoksa klasörü çözülür — Foundation /private önekini tutarsız atıyor)
    let s = URL(fileURLWithPath: y).standardizedFileURL.path
    if let r = realpath(s, nil) { defer { free(r) }; return String(cString: r) }
    let ust = (s as NSString).deletingLastPathComponent
    if let r = realpath(ust, nil) { defer { free(r) }; return (String(cString: r) as NSString).appendingPathComponent((s as NSString).lastPathComponent) }
    return s
}
let uygulamaKlasor = gercek(Bundle.main.bundleURL.deletingLastPathComponent().path)
var cikti = (uygulamaKlasor as NSString).appendingPathComponent("posta.json")
var gun = 14.0, enCok = 400
var dbYol: String? = nil
var govdeIds: [Int64] = []  // --govde 12,34: yalnız bu iletilerin ham metni (v0.86.0; kullanıcının belli bir iletiyi hedefleyen sorusunda)
var benAdres = Set<String>()  // --ben a@x,b@y: kullanıcının kendi adresleri (aktarıcı ayardan verir) — bunlardan gelen ileti gönderilen sayılır
var i = 1
let a = CommandLine.arguments
while i < a.count {
  if a[i] == "--cikti", i + 1 < a.count { cikti = a[i + 1]; i += 1 }
  else if a[i] == "--gun", i + 1 < a.count { gun = Double(a[i + 1]) ?? 14; i += 1 }
  else if a[i] == "--en-cok", i + 1 < a.count { enCok = Int(a[i + 1]) ?? 400; i += 1 }
  else if a[i] == "--db", i + 1 < a.count {
    #if SUFLOR_DENEME
    dbYol = a[i + 1]
    #else
    exit(3)
    #endif
    i += 1
  }
  else if a[i] == "--govde", i + 1 < a.count { govdeIds = a[i + 1].split(separator: ",").compactMap { Int64($0.trimmingCharacters(in: .whitespaces)) }.prefix(3).map { $0 }; i += 1 }
  else if a[i] == "--ben", i + 1 < a.count { benAdres = Set(a[i + 1].split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }.filter { $0.contains("@") }); i += 1 }
  i += 1
}
#if !SUFLOR_DENEME
do {  // çıktı yolu: adı sabit, klasörü uygulama klasörünün altında (sembolik bağlar çözülerek)
  let ad = (cikti as NSString).lastPathComponent
  let ust = gercek((cikti as NSString).deletingLastPathComponent)
  guard ad == "posta.json" || ad == "posta-govde.json", ust == uygulamaKlasor || ust.hasPrefix(uygulamaKlasor + "/") else { exit(3) }
  cikti = (ust as NSString).appendingPathComponent(ad)
}
#endif
let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]

func yaz(_ o: [String: Any]) {
  var o = o
  o["guncel"] = iso.string(from: Date())
  guard let d = try? JSONSerialization.data(withJSONObject: o, options: []) else { return }
  try? FileManager.default.createDirectory(atPath: (cikti as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
  let gecici = cikti + ".tmp"
  unlink(gecici)  // hazır duran sembolik bağı izleme (O3); ileti başlıkları kişi adı içerir → 0600
  let fd = open(gecici, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
  guard fd >= 0 else { return }
  _ = d.withUnsafeBytes { write(fd, $0.baseAddress, d.count) }; close(fd)
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
// --- Gövde kipi: istenen iletilerin .emlx dosyası kutusunun klasöründe (<hesap>/<kutu>.mbox/…/Messages/<ROWID>[.partial].emlx) aranır;
// ham ileti (ilk 256 KB, base64) yazılır — MIME çözümü ve düz metin aktarıcıda (Python email). Ekler ayrı dosyada (Attachments/) — açılmaz.
if !govdeIds.isEmpty {
  let mailKok = (yol as NSString).deletingLastPathComponent.components(separatedBy: "/").dropLast().joined(separator: "/")  // …/Mail/V10
  var sonuc: [String: Any] = [:]
  for id in govdeIds {
    var st: OpaquePointer?; var url = ""
    if sqlite3_prepare_v2(db, "SELECT mbx.url FROM messages m LEFT JOIN mailboxes mbx ON mbx.ROWID = m.mailbox WHERE m.ROWID = ?", -1, &st, nil) == SQLITE_OK {
      sqlite3_bind_int64(st, 1, id)
      if sqlite3_step(st) == SQLITE_ROW, let c = sqlite3_column_text(st, 0) { url = String(cString: c) }
    }
    sqlite3_finalize(st)
    guard let u = URL(string: url), let hesap = u.host else { sonuc[String(id)] = ["hata": "kutu yok"]; continue }
    let kutular = u.pathComponents.filter { $0 != "/" }.map { ($0.removingPercentEncoding ?? $0) + ".mbox" }
    let kutuYol = ([mailKok, hesap] + kutular).joined(separator: "/")
    var bulunan: String? = nil
    if let en = FileManager.default.enumerator(atPath: kutuYol) {
      while let f = en.nextObject() as? String {
        let ad = (f as NSString).lastPathComponent
        if ad == "\(id).emlx" || ad == "\(id).partial.emlx" { bulunan = (kutuYol as NSString).appendingPathComponent(f); break }
      }
    }
    guard let b = bulunan, let h = FileManager.default.contents(atPath: b) else { sonuc[String(id)] = ["hata": "dosya yok"]; continue }
    sonuc[String(id)] = ["ham": h.prefix(262144).base64EncodedString(), "kismi": b.hasSuffix(".partial.emlx")]
  }
  sqlite3_close(db); yaz(["durum": "ok", "govde": sonuc]); exit(0)
}
let okundu = m.contains("read") ? "m.read" : "NULL"
let silindi = m.contains("deleted") ? "AND IFNULL(m.deleted, 0) = 0" : ""
let ozet = (m.contains("summary") && sm.contains("summary")) ? "(SELECT s.summary FROM summaries s WHERE s.ROWID = m.summary)" : "NULL"
let yorum = ad.contains("comment") ? "a.comment" : "NULL"
let onek = m.contains("subject_prefix") ? "m.subject_prefix" : "NULL"
let sinir = Date().timeIntervalSince1970 - gun * 86400
let sql = """
SELECT m.date_received, \(yorum), a.address, \(onek), su.subject, mbx.url, \(okundu), \(ozet), m.ROWID
FROM messages m LEFT JOIN addresses a ON a.ROWID = m.sender LEFT JOIN subjects su ON su.ROWID = m.subject LEFT JOIN mailboxes mbx ON mbx.ROWID = m.mailbox
WHERE m.date_received >= ? \(silindi) ORDER BY m.date_received DESC LIMIT ?
"""
var st: OpaquePointer?
guard sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK else {
  yaz(["durum": "sema", "hata": "sorgu hazırlanamadı: " + String(cString: sqlite3_errmsg(db)), "iletiler": []]); exit(0)
}
sqlite3_bind_double(st, 1, sinir); sqlite3_bind_int(st, 2, Int32(enCok * 4))
func metin(_ k: Int32) -> String? { if let c = sqlite3_column_text(st, k) { return String(cString: c) }; return nil }
// kutu adı: URL'nin son bölümü (yüzde kodlu) — INBOX, Sent Messages, [Gmail]/Gönderilmiş Postalar …
let atla = try! NSRegularExpression(pattern: "(trash|junk|spam|deleted|drafts|çöp|gereksiz|taslak|silin|istenmeyen|bin)", options: [.caseInsensitive])
let gonder = try! NSRegularExpression(pattern: "(sent|gönderil|giden)", options: [.caseInsensitive])
// v0.85.2 (gerçek veri, 19 Ekim): Gmail aynı iletiyi Gelen Kutusu ve "[Gmail]/All Mail"da tutar → (gönderen, konu, saniye) bir kez; gönderdiklerin de All Mail'de →
// gönderilen kutularındaki gönderen adresleri "benim" sayılır; kutu adı Mac'te ayrık harfle (o + ¨) gelir → eşleşmeden önce birleşik biçime çevrilir.
struct Satir { let t: Double; let ad: String?; let adres: String; let konu: String; let kutu: String; let okundu: Int32?; let ozet: String?; let id: Int64 }
var satirlar: [Satir] = []
while sqlite3_step(st) == SQLITE_ROW {
  let url = metin(5) ?? ""
  let kutu = ((URL(string: url)?.pathComponents.filter { $0 != "/" }.joined(separator: "/")).flatMap { $0.removingPercentEncoding ?? $0 } ?? url).precomposedStringWithCanonicalMapping
  satirlar.append(Satir(t: sqlite3_column_double(st, 0), ad: metin(1), adres: (metin(2) ?? "").lowercased(), konu: ((metin(3) ?? "") + (metin(4) ?? "")).trimmingCharacters(in: .whitespaces),
                        kutu: kutu, okundu: (okundu != "NULL" && sqlite3_column_type(st, 6) != SQLITE_NULL) ? sqlite3_column_int(st, 6) : nil, ozet: metin(7), id: sqlite3_column_int64(st, 8)))
}
func eslesir(_ re: NSRegularExpression, _ k: String) -> Bool { re.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil }
let benim = Set(satirlar.filter { eslesir(gonder, $0.kutu) && !$0.adres.isEmpty }.map { $0.adres }).union(benAdres)
// Gönderilen iletinin alıcı adresleri (tür ayrımı yok; en çok 10): "tc posta-uslup" bir kişiye gönderdiklerini bulur. Tablo/sütun yoksa alan yazılmaz.
let rc = sutunlar("recipients")
var alSt: OpaquePointer?
if rc.isSuperset(of: ["message", "address"]) {
  if sqlite3_prepare_v2(db, "SELECT a.address, \(ad.contains("comment") ? "a.comment" : "NULL") FROM recipients r JOIN addresses a ON a.ROWID = r.address WHERE r.message = ? ORDER BY \(rc.contains("position") ? "r.position" : "r.ROWID") LIMIT 10", -1, &alSt, nil) != SQLITE_OK { alSt = nil }
}
func alicilar(_ id: Int64) -> (adres: [String], ad: [String]) {
  guard let s = alSt else { return ([], []) }
  sqlite3_reset(s); sqlite3_bind_int64(s, 1, id)
  var adr: [String] = [], adlar: [String] = []
  while sqlite3_step(s) == SQLITE_ROW {
    if let c = sqlite3_column_text(s, 0) { adr.append(String(cString: c).lowercased()) }
    if let c = sqlite3_column_text(s, 1), !String(cString: c).isEmpty { adlar.append(String(cString: c)) }
  }
  return (adr, adlar)
}
var goruldu = Set<String>()
var iletiler: [[String: Any]] = []
for x in satirlar where iletiler.count < enCok {
  if eslesir(atla, x.kutu) { continue }
  let anahtar = "\(x.adres)|\(x.konu)|\(Int(x.t))"
  if goruldu.contains(anahtar) { continue }
  goruldu.insert(anahtar)
  let t = x.t, kutu = x.kutu
  var o: [String: Any] = ["id": x.id, "t": iso.string(from: Date(timeIntervalSince1970: t)), "adres": x.adres, "konu": x.konu,
                          "kutu": String(kutu.suffix(60)), "gonderilen": eslesir(gonder, kutu) || benim.contains(x.adres)]
  if let y = x.ad, !y.isEmpty { o["ad"] = y }
  if o["gonderilen"] as? Bool == true, alSt != nil { let r = alicilar(x.id); o["alici"] = r.adres; if !r.ad.isEmpty { o["alici_ad"] = r.ad } }
  if let r = x.okundu { o["okundu"] = r != 0 }
  if let z = x.ozet, !z.isEmpty { o["ozet"] = String(z.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ").prefix(300)) }
  iletiler.append(o)
}
sqlite3_finalize(st); if let s = alSt { sqlite3_finalize(s) }; sqlite3_close(db)
yaz(["durum": "ok", "hata": NSNull(), "iletiler": iletiler, "dizin": (yol as NSString).deletingLastPathComponent.components(separatedBy: "/").suffix(2).joined(separator: "/")])
