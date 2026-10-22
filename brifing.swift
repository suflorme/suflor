// Suflor Brifing — toplantı öncesi brifing için aktarıcının hazırladığı tek `claude -p` çağrısını çalıştırır.
// Neden ayrı uygulama: aktarıcı launchd'den çalışır ve macOS onun Masaüstü/Belgeler'e erişimini engeller (proje klasörü orada
// olabilir). Uygulama paketi `open` ile açılınca izin bu uygulamaya sorulur (bir kez) ve alt süreç Claude da onu kullanır.
// Giriş: --istek <json>  {"claude": ".../claude", "args": [...], "cwd": "...", "cikti": "...", "sure": 240}
// Yalnız adı "claude" olan ikiliyi çalıştırır; yazma/komut aracı açan argümanları reddeder (salt okunur brifing).
// Açık süreç kipi (bas-konuş, v0.20.0): istekte "giris"/"cikis" (aktarıcının açtığı iki FIFO) varsa Claude'un girişi ve çıkışı onlara
// bağlanır (giriş bu uygulamadan anonim boruyla geçer), süreç aktarıcı girişi kapatana (ya da "sure" dolana) kadar açık kalır; izin yine bu uygulamaya sorulur.
// v0.97.4 (güvenlik denetimi O3): Masaüstü izni bu uygulamada — aynı hesaptaki başka bir program onu istek dosyasıyla çalıştırıp izni ödünç alamasın:
// claude ikilisi Anthropic imzalı olmalı (deneme derlemesi `-D SUFLOR_DENEME` sahte claude'a izin verir); argümanlar yasak listesi yerine izin listesinden
// (salt okunur araçlar, --add-dir yalnız istek klasörü, --mcp-config yalnız istek klasöründeki konus-mcp.json, --settings yalnız iki env anahtarı);
// istek, çıktı ve FIFO'lar uygulama klasörünün (bu paketin bulunduğu klasör) altında aynı klasörde. Reddedilince çıkış 3.
import Foundation
import Security

func bitir(_ kod: Int32) -> Never { exit(kod) }
let a = CommandLine.arguments
func gercek(_ y: String) -> String {  // sembolik bağları çözülmüş mutlak yol (C realpath; dosya yoksa klasörü çözülür — Foundation /private önekini tutarsız atıyor)
    let s = URL(fileURLWithPath: y).standardizedFileURL.path
    if let r = realpath(s, nil) { defer { free(r) }; return String(cString: r) }
    let ust = (s as NSString).deletingLastPathComponent
    if let r = realpath(ust, nil) { defer { free(r) }; return (String(cString: r) as NSString).appendingPathComponent((s as NSString).lastPathComponent) }
    return s
}
func altinda(_ y: String, _ k: String) -> Bool { y == k || y.hasPrefix(k + "/") }
let uygulamaKlasor = gercek(Bundle.main.bundleURL.deletingLastPathComponent().path)
// O3 kalan sınırı (v0.99.4): Python betikleri hep -I (yalıtılmış) ile — PYTHON* ortam değişkenleri, kullanıcı site-packages ve çalışma klasörü okunmaz;
// araya kod sokmanın kolay yolu kapanır. Betiklerin kendisi paket dışında: aynı hesaptaki program onları değiştirebilir (kabul edilen risk, S108).
// Arama dizini kipi (v0.58.0): --dizin → uygulama klasöründeki baglam.py'yi (bu paketin yanında) `dizin` komutuyla çalıştırır; başka argüman almaz.
// Aktarıcı proje klasörünü okuyamayınca 10 dk'lık ön arama güncellemesini buna yaptırır (Masaüstü izni bu uygulamada).
if a.contains("--dizin") {
    let baglam = Bundle.main.bundleURL.deletingLastPathComponent().appendingPathComponent("baglam.py").path
    guard FileManager.default.isReadableFile(atPath: baglam) else { bitir(2) }
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/python3"); p.arguments = ["-I", "-B", baglam, "dizin"]
    p.currentDirectoryURL = URL(fileURLWithPath: NSTemporaryDirectory())
    p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice; p.standardInput = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    DispatchQueue.global().asyncAfter(deadline: .now() + 600) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
// Veritabanı önbelleği kipi (v0.62.0, proje hazırlığı T0): --vt-izle <canli klasörü> → paketin yanındaki toplanti-claude.py'yi `vt-izle` ile çalıştırır
// (kayıt veritabanı Masaüstü'nde; aktarıcı okuyamaz). Süreç dakikada bir önbellekleri yazar, 6 saatte kendisi kapanır; aktarıcı eskiyince yeniden açar.
if let i = a.firstIndex(of: "--vt-izle") {
    guard i + 1 < a.count else { bitir(2) }
    var d: ObjCBool = false
    let dir = a[i + 1], tc = Bundle.main.bundleURL.deletingLastPathComponent().appendingPathComponent("toplanti-claude.py").path
    guard FileManager.default.fileExists(atPath: dir, isDirectory: &d), d.boolValue, FileManager.default.isReadableFile(atPath: tc) else { bitir(2) }
    guard altinda(gercek(dir), uygulamaKlasor) else { bitir(3) }  // O3: önbellekler yalnız uygulama klasörünün altına
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/python3"); p.arguments = ["-I", "-B", tc, "--dir", dir, "vt-izle"]
    p.currentDirectoryURL = URL(fileURLWithPath: NSTemporaryDirectory())
    var e = ProcessInfo.processInfo.environment; e["PYTHONDONTWRITEBYTECODE"] = "1"; p.environment = e
    p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice; p.standardInput = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
guard let i = a.firstIndex(of: "--istek"), i + 1 < a.count,
      let veri = FileManager.default.contents(atPath: a[i + 1]),
      let j = (try? JSONSerialization.jsonObject(with: veri)) as? [String: Any],
      let claude = j["claude"] as? String, (claude as NSString).lastPathComponent == "claude",
      var arg = j["args"] as? [String], let cwd = j["cwd"] as? String, let cikti = j["cikti"] as? String else { bitir(2) }
let istekKlasor = (gercek(a[i + 1]) as NSString).deletingLastPathComponent
guard altinda(istekKlasor, uygulamaKlasor) else { bitir(3) }
for y in [cikti, j["giris"] as? String, j["cikis"] as? String].compactMap({ $0 }) where (gercek(y) as NSString).deletingLastPathComponent != istekKlasor { bitir(3) }
#if !SUFLOR_DENEME
func anthropicImzali(_ yol: String) -> Bool {  // Claude Code'un yerel ikilisi Anthropic'in Developer ID'siyle imzalı (ekip Q6L2SF6YDW)
    var kod: SecStaticCode?, gerek: SecRequirement?
    guard SecStaticCodeCreateWithPath(URL(fileURLWithPath: yol) as CFURL, [], &kod) == errSecSuccess, let k = kod,
          SecRequirementCreateWithString("anchor apple generic and identifier \"com.anthropic.claude-code\" and certificate leaf[subject.OU] = \"Q6L2SF6YDW\"" as CFString, [], &gerek) == errSecSuccess
    else { return false }
    return SecStaticCodeCheckValidity(k, [], gerek) == errSecSuccess
}
let claudeGercek = gercek(claude)
guard anthropicImzali(claudeGercek) else { bitir(3) }
#else
let claudeGercek = claude
#endif
// Toplantı oturumu kipi (v0.111.0; kullanıcı 22 Ekim: "Claude Code terminalini görmesine gerek yok"): istekte "kip": "toplanti" → panodan Başlat'la açılan
// toplantı oturumu Terminal yerine burada, girişi/çıkışı aktarıcının FIFO'larında. Araçlar kısıtlanmaz (Terminal'deki oturumla aynı proje izinleri);
// izin modu verilemez — proje izinlerinde olmayan her araç sorusu stream-json'la aktarıcıya gelir (--permission-prompt-tool stdio), kullanıcı panoda onaylar.
// Argümanlar ayrı izin listesinden: istem metni yok (ilk mesaj girişten), --settings yalnız uygulama klasöründeki toplanti-kanca.json ve içeriği tek
// PreToolUse kancası (izin-kanca; komut burada yeniden kurulup karşılaştırılır), --resume yalnız oturum kimliği. Risk Terminal'le aynı: aynı hesaptaki
// bir program .command dosyasıyla Terminal'de de oturum açtırabiliyordu.
func kabukTirnak(_ s: String) -> String {  // Python shlex.quote ile aynı
    if !s.isEmpty, s.range(of: "^[A-Za-z0-9@%+=:,./_-]+$", options: .regularExpression) != nil { return s }
    return "'" + s.replacingOccurrences(of: "'", with: "'\"'\"'") + "'"
}
func kancaDenetle(_ y: String) -> String? {
    guard gercek(y) == (uygulamaKlasor as NSString).appendingPathComponent("toplanti-kanca.json"), let d = FileManager.default.contents(atPath: y),
          let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any], Set(o.keys) == ["hooks"],
          let h = o["hooks"] as? [String: Any], Set(h.keys) == ["PreToolUse"], let pt = h["PreToolUse"] as? [[String: Any]], pt.count == 1,
          Set(pt[0].keys) == ["matcher", "hooks"], pt[0]["matcher"] as? String == "Bash|mcp__.*", let hk = pt[0]["hooks"] as? [[String: Any]], hk.count == 1,
          Set(hk[0].keys) == ["type", "timeout", "command"], hk[0]["type"] as? String == "command", let c = hk[0]["command"] as? String,
          let r = c.range(of: " --relay http://127\\.0\\.0\\.1:[0-9]{2,5} izin-kanca$", options: .regularExpression) else { return nil }
    let tc = (uygulamaKlasor as NSString).appendingPathComponent("toplanti-claude.py")
    guard String(c[..<r.lowerBound]) == "/usr/bin/python3 -I -B \(kabukTirnak(tc)) --dir \(kabukTirnak(istekKlasor))" else { return nil }
    return String(data: d, encoding: .utf8)
}
if j["kip"] as? String == "toplanti" {
    guard let giris = j["giris"] as? String, let cikis = j["cikis"] as? String else { bitir(2) }
    let tek: Set<String> = ["-p", "--print", "--verbose"]
    let deg: [String: (String) -> Bool] = [
        "--input-format": { $0 == "stream-json" }, "--output-format": { $0 == "stream-json" }, "--permission-prompt-tool": { $0 == "stdio" },
        "--append-system-prompt": { _ in true }, "--settings": { kancaDenetle($0) != nil },
        "--model": { $0.range(of: "^[A-Za-z0-9._\\[\\]-]{1,64}$", options: .regularExpression) != nil },
        "--effort": { ["low", "medium", "high", "xhigh", "max"].contains($0) },
        "--resume": { $0.range(of: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", options: .regularExpression) != nil }]
    var k = 0
    while k < arg.count {
        let x = arg[k]
        if tek.contains(x) { k += 1; continue }
        guard let uygun = deg[x], k + 1 < arg.count, uygun(arg[k + 1]) else { bitir(3) }
        if x == "--settings", let metin = kancaDenetle(arg[k + 1]) { arg[k + 1] = metin }
        k += 2
    }
    guard arg.contains("--permission-prompt-tool"), arg.contains("--input-format") else { bitir(3) }
    guard let gir = FileHandle(forReadingAtPath: giris), let cik = FileHandle(forWritingAtPath: cikis) else { bitir(7) }
    let p = Process()
    p.executableURL = URL(fileURLWithPath: claudeGercek); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
    var e = ProcessInfo.processInfo.environment; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (e["PATH"] ?? ""); p.environment = e
    signal(SIGPIPE, SIG_IGN)
    let boru = Pipe()
    p.standardInput = boru; p.standardOutput = cik; p.standardError = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    Thread.detachNewThread {
        while true { let d = gir.availableData; if d.isEmpty { break }; do { try boru.fileHandleForWriting.write(contentsOf: d) } catch { break } }
        try? boru.fileHandleForWriting.close()
    }
    let sure = (j["sure"] as? Double) ?? 21600
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
// izin listesi: değersiz bayraklar, değerli bayraklar (değer denetimiyle); -p'den hemen sonraki tek metin istemdir, başka konumsal argüman yok
let tekBayrak: Set<String> = ["-p", "--print", "--verbose", "--include-partial-messages", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
let araclar: Set<String> = ["Read", "Grep", "Glob"]
func aracUygun(_ v: String) -> Bool { v.split(separator: ",").allSatisfy { let t = $0.trimmingCharacters(in: .whitespaces); return araclar.contains(t) || t.hasPrefix("mcp__suflorvt__") } }
func ayarUygun(_ v: String) -> Bool {  // --settings: yalnız {"env": {CLAUDE_CODE_DISABLE_CLAUDE_MDS, CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS}} (kanca, izin, model yok)
    guard let d = v.data(using: .utf8), let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any], Set(o.keys) == ["env"],
          let e = o["env"] as? [String: Any] else { return false }
    return Set(e.keys).isSubset(of: ["CLAUDE_CODE_DISABLE_CLAUDE_MDS", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"]) && e.values.allSatisfy { $0 is String }
}
// --mcp-config: yalnız istek klasöründeki konus-mcp.json ve içeriği tek sunucu "suflorvt" = /usr/bin/python3 -I -B <uygulama>/toplanti-claude.py --dir <istek klasörü> vt-mcp.
// Denetlenen içerik Claude'a dosya yolu olarak değil metin olarak verilir (denetimden sonra dosya değişse de fark etmez).
func mcpDenetle(_ y: String) -> String? {
    guard gercek(y) == (istekKlasor as NSString).appendingPathComponent("konus-mcp.json"), let d = FileManager.default.contents(atPath: y),
          let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any], Set(o.keys) == ["mcpServers"],
          let m = o["mcpServers"] as? [String: Any], Set(m.keys) == ["suflorvt"], let v = m["suflorvt"] as? [String: Any],
          Set(v.keys).isSubset(of: ["command", "args", "env", "type"]), v["command"] as? String == "/usr/bin/python3",
          let ar = v["args"] as? [String], ar.count == 6, ar[0] == "-I", ar[1] == "-B", gercek(ar[2]) == (uygulamaKlasor as NSString).appendingPathComponent("toplanti-claude.py"),
          ar[3] == "--dir", gercek(ar[4]) == istekKlasor, ar[5] == "vt-mcp" else { return nil }
    if let t = v["type"] { guard t as? String == "stdio" else { return nil } }
    var izinliEnv: Set<String> = ["PYTHONDONTWRITEBYTECODE", "SUFLOR_VT_SEMA_YOK"]
    #if SUFLOR_DENEME
    izinliEnv.insert("SUFLOR_AYAR")
    #endif
    if let e = v["env"] { guard let e = e as? [String: String], Set(e.keys).isSubset(of: izinliEnv) else { return nil } }
    return String(data: d, encoding: .utf8)
}
let degerli: [String: (String) -> Bool] = [
    "--output-format": { ["json", "stream-json", "text"].contains($0) }, "--input-format": { ["stream-json", "text"].contains($0) },
    "--allowedTools": aracUygun, "--tools": aracUygun,
    "--add-dir": { gercek($0) == istekKlasor }, "--mcp-config": { mcpDenetle($0) != nil },
    "--append-system-prompt": { _ in true }, "--system-prompt": { _ in true }, "--settings": ayarUygun,
    "--model": { $0.range(of: "^[A-Za-z0-9._\\[\\]-]{1,64}$", options: .regularExpression) != nil },
    "--effort": { ["low", "medium", "high", "xhigh", "max"].contains($0) },
    "--setting-sources": { $0.split(separator: ",").allSatisfy { ["user", "project", "local"].contains(String($0)) } }]
var k = 0
while k < arg.count {
    let x = arg[k]
    if tekBayrak.contains(x) {
        if (x == "-p" || x == "--print"), k + 1 < arg.count, !arg[k + 1].hasPrefix("-") { k += 1 }  // istem metni
    } else if let uygun = degerli[x] {
        guard k + 1 < arg.count, uygun(arg[k + 1]) else { bitir(3) }
        if x == "--mcp-config", let metin = mcpDenetle(arg[k + 1]) { arg[k + 1] = metin }
        k += 1
    } else { bitir(3) }
    k += 1
}

let p = Process()
if let giris = j["giris"] as? String, let cikis = j["cikis"] as? String {
    guard let gir = FileHandle(forReadingAtPath: giris), let cik = FileHandle(forWritingAtPath: cikis) else { bitir(7) }
    p.executableURL = URL(fileURLWithPath: claudeGercek); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
    var e = ProcessInfo.processInfo.environment; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (e["PATH"] ?? ""); p.environment = e
    // v0.57.6: Claude Code adlı FIFO girişinde dosya sonunu görmüyor (17 Ekim denemesi: anonim boruda giriş kapanınca çıkıyor, FIFO'da hiç çıkmıyor) —
    // aktarıcı süreci yenileyince eski claude + veritabanı yardımcısı açık kalıyordu (süreç başına ~250 MB). FIFO'yu burada okuyup anonim boruyla
    // aktarırız; FIFO kapanınca boru kapanır, claude çıkar, uygulama biter.
    signal(SIGPIPE, SIG_IGN)
    let boru = Pipe()
    p.standardInput = boru; p.standardOutput = cik; p.standardError = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    Thread.detachNewThread {
        while true { let d = gir.availableData; if d.isEmpty { break }; do { try boru.fileHandleForWriting.write(contentsOf: d) } catch { break } }
        try? boru.fileHandleForWriting.close()
    }
    let sure = (j["sure"] as? Double) ?? 7200
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
p.executableURL = URL(fileURLWithPath: claudeGercek); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
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
