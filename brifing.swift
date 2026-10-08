// Suflor Brifing — toplantı öncesi brifing için aktarıcının hazırladığı tek `claude -p` çağrısını çalıştırır.
// Neden ayrı uygulama: aktarıcı launchd'den çalışır ve macOS onun Masaüstü/Belgeler'e erişimini engeller (proje klasörü orada
// olabilir). Uygulama paketi `open` ile açılınca izin bu uygulamaya sorulur (bir kez) ve alt süreç Claude da onu kullanır.
// Giriş: --istek <json>  {"claude": ".../claude", "args": [...], "cwd": "...", "cikti": "...", "sure": 240}
// Yalnız adı "claude" olan ikiliyi çalıştırır; yazma/komut aracı açan argümanları reddeder (salt okunur brifing).
// Açık süreç kipi (bas-konuş, v0.20.0): istekte "giris"/"cikis" (aktarıcının açtığı iki FIFO) varsa Claude'un girişi ve çıkışı onlara
// bağlanır, süreç aktarıcı girişi kapatana (ya da "sure" dolana) kadar açık kalır; izin yine bu uygulamaya sorulur.
import Foundation

func bitir(_ kod: Int32) -> Never { exit(kod) }
let a = CommandLine.arguments
guard let i = a.firstIndex(of: "--istek"), i + 1 < a.count,
      let veri = FileManager.default.contents(atPath: a[i + 1]),
      let j = (try? JSONSerialization.jsonObject(with: veri)) as? [String: Any],
      let claude = j["claude"] as? String, (claude as NSString).lastPathComponent == "claude",
      let arg = j["args"] as? [String], let cwd = j["cwd"] as? String, let cikti = j["cikti"] as? String else { bitir(2) }
let yasak = ["dangerously", "Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "bypassPermissions", "acceptEdits"]
if arg.contains(where: { x in yasak.contains(where: { x.contains($0) }) }) { bitir(3) }

let p = Process()
if let giris = j["giris"] as? String, let cikis = j["cikis"] as? String {
    guard let gir = FileHandle(forReadingAtPath: giris), let cik = FileHandle(forWritingAtPath: cikis) else { bitir(7) }
    p.executableURL = URL(fileURLWithPath: claude); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
    var e = ProcessInfo.processInfo.environment; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (e["PATH"] ?? ""); p.environment = e
    p.standardInput = gir; p.standardOutput = cik; p.standardError = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    let sure = (j["sure"] as? Double) ?? 7200
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
p.executableURL = URL(fileURLWithPath: claude); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
var env = ProcessInfo.processInfo.environment
env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
p.environment = env
let cik = Pipe(); p.standardOutput = cik; p.standardError = FileHandle.nullDevice; p.standardInput = FileHandle.nullDevice
do { try p.run() } catch { bitir(4) }

var sonuc = Data(); let okundu = DispatchSemaphore(value: 0)
DispatchQueue.global().async { sonuc = cik.fileHandleForReading.readDataToEndOfFile(); okundu.signal() }
if okundu.wait(timeout: .now() + ((j["sure"] as? Double) ?? 240)) == .timedOut { p.terminate(); bitir(5) }
p.waitUntilExit()
let gecici = cikti + ".tmp"
FileManager.default.createFile(atPath: gecici, contents: sonuc, attributes: [.posixPermissions: 0o600])
if rename(gecici, cikti) != 0 { bitir(6) }
bitir(p.terminationStatus)
