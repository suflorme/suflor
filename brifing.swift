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
import CommonCrypto

func bitir(_ kod: Int32) -> Never { exit(kod) }
// 6 Kasım: Foundation Process argümanları NFD'ye çeviriyor ("ü" → "u" + birleşik işaret; ölçüldü) — claude'a giden Türkçe argüman bozuk gitmesin diye
// Process'in yerine posix_spawn (argümanlar UTF-8 olduğu gibi). Yalnız kullanılan kısım: argüman, cwd, ortam, stdin/stdout/stderr, terminate, bekleme.
final class NfcSurec {
    var executableURL = URL(fileURLWithPath: "/"), arguments: [String] = [], currentDirectoryURL: URL? = nil, environment: [String: String]? = nil
    var stdinFd: Int32? = nil, stdoutFd: Int32? = nil   // yok → /dev/null
    private(set) var pid: pid_t = 0, durum: Int32 = 0, bitti = false
    private let bekle = DispatchSemaphore(value: 0), kilit = NSLock()
    var isRunning: Bool { kilit.lock(); defer { kilit.unlock() }; return pid != 0 && !bitti }
    var processIdentifier: pid_t { pid }
    var terminationStatus: Int32 { (durum & 0x7f) == 0 ? (durum >> 8) & 0xff : (durum & 0x7f) }
    func run() throws {
        let argv: [UnsafeMutablePointer<CChar>?] = ([executableURL.path] + arguments).map { strdup($0) } + [nil]
        let envp: [UnsafeMutablePointer<CChar>?] = (environment ?? ProcessInfo.processInfo.environment).map { strdup("\($0.key)=\($0.value)") } + [nil]
        defer { argv.forEach { free($0) }; envp.forEach { free($0) } }
        var fa: posix_spawn_file_actions_t? = nil, at: posix_spawnattr_t? = nil
        posix_spawn_file_actions_init(&fa); posix_spawnattr_init(&at)
        if let g = stdinFd { posix_spawn_file_actions_adddup2(&fa, g, 0) } else { posix_spawn_file_actions_addopen(&fa, 0, "/dev/null", O_RDONLY, 0) }
        if let c = stdoutFd { posix_spawn_file_actions_adddup2(&fa, c, 1) } else { posix_spawn_file_actions_addopen(&fa, 1, "/dev/null", O_WRONLY, 0) }
        posix_spawn_file_actions_addopen(&fa, 2, "/dev/null", O_WRONLY, 0)
        if let d = currentDirectoryURL { posix_spawn_file_actions_addchdir_np(&fa, d.path) }
        var yok = sigset_t(); sigemptyset(&yok); sigaddset(&yok, SIGPIPE)   // aktarıcı SIGPIPE'ı yok sayıyor; claude varsayılanla başlasın (Process gibi)
        posix_spawnattr_setsigdefault(&at, &yok)
        posix_spawnattr_setflags(&at, Int16(POSIX_SPAWN_CLOEXEC_DEFAULT | POSIX_SPAWN_SETSIGDEF))
        var yeni: pid_t = 0
        let rs = posix_spawn(&yeni, executableURL.path, &fa, &at, argv, envp)
        posix_spawn_file_actions_destroy(&fa); posix_spawnattr_destroy(&at)
        guard rs == 0 else { throw NSError(domain: NSPOSIXErrorDomain, code: Int(rs)) }
        kilit.lock(); pid = yeni; kilit.unlock()
        Thread.detachNewThread { [self] in
            var st: Int32 = 0
            while waitpid(yeni, &st, 0) < 0 && errno == EINTR {}
            kilit.lock(); durum = st; bitti = true; kilit.unlock(); bekle.signal()
        }
    }
    func terminate() { if isRunning { kill(pid, SIGTERM) } }
    func waitUntilExit() { bekle.wait(); bekle.signal() }
}

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
// Beyin kipi (v0.122.0, Faz 11 Aşama 1): --beyin <istek> → Konuş başka bir yapay zekâyla (openai-uyumlu: Gemini, OpenAI, Ollama, LM Studio).
// Yalnız uygulama klasöründeki aktarici/beyin.py'yi `/usr/bin/python3 -I -B … calis <istek>` ile çalıştırır; claude çalıştırılmaz. Güvence Suflor'un kendi
// araç kodunda (beyin.py: salt okunur, kök sınırlı araçlar; ağ yalnız https ya da 127.0.0.1). Burada da: istek ve FIFO'lar uygulama klasörünün altında aynı
// klasörde, istek anahtarları izin listesinden, araç sunucusu yalnız istek klasöründeki konus-mcp.json, kökler var olan klasörler; anahtarın kendisi istekte yok.
if let bi = a.firstIndex(of: "--beyin") {
    guard bi + 1 < a.count, let veri = FileManager.default.contents(atPath: a[bi + 1]),
          let j = (try? JSONSerialization.jsonObject(with: veri)) as? [String: Any],
          let giris = j["giris"] as? String, let cikis = j["cikis"] as? String, let b = j["beyin"] as? [String: Any] else { bitir(2) }
    let klasor = (gercek(a[bi + 1]) as NSString).deletingLastPathComponent
    guard altinda(klasor, uygulamaKlasor) else { bitir(3) }
    for y in [giris, cikis] where (gercek(y) as NSString).deletingLastPathComponent != klasor { bitir(3) }
    var izinli: Set<String> = ["beyin", "sistem", "mcp", "kokler", "cwd", "giris", "cikis", "dil", "sure"]
    #if SUFLOR_DENEME
    izinli.insert("ayar")  // deneme aktarıcısının ayar dosyası (SUFLOR_AYAR)
    #endif
    guard Set(j.keys).isSubset(of: izinli),
          Set(b.keys).isSubset(of: ["tur", "model", "saglayici", "adres", "anahtar", "effort", "fiyat"]), b["tur"] as? String == "openai-uyumlu",
          let adres = b["adres"] as? String, let u = URLComponents(string: adres), u.user == nil, u.password == nil, u.query == nil, let h = u.host, !h.isEmpty,
          u.scheme == "https" || (u.scheme == "http" && ["127.0.0.1", "localhost", "::1"].contains(h)) else { bitir(3) }
    if let m = j["mcp"] as? String { guard gercek(m) == (klasor as NSString).appendingPathComponent("konus-mcp.json") else { bitir(3) } }
    for k in (j["kokler"] as? [String]) ?? [] { var d: ObjCBool = false; guard FileManager.default.fileExists(atPath: k, isDirectory: &d), d.boolValue else { bitir(3) } }
    let beyin = (uygulamaKlasor as NSString).appendingPathComponent("aktarici/beyin.py")
    guard FileManager.default.isReadableFile(atPath: beyin), let gir = FileHandle(forReadingAtPath: giris), let cik = FileHandle(forWritingAtPath: cikis) else { bitir(7) }
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/python3"); p.arguments = ["-I", "-B", beyin, "calis", gercek(a[bi + 1])]
    p.currentDirectoryURL = URL(fileURLWithPath: NSTemporaryDirectory())
    var e = ProcessInfo.processInfo.environment; e["PYTHONDONTWRITEBYTECODE"] = "1"; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"; p.environment = e
    signal(SIGPIPE, SIG_IGN)
    let boru = Pipe()
    p.standardInput = boru; p.standardOutput = cik; p.standardError = FileHandle.nullDevice
    do { try p.run() } catch { bitir(4) }
    Thread.detachNewThread {  // açık süreç kipindeki gibi: FIFO kapanınca boru kapanır, beyin.py çıkar
        while true { let d = gir.availableData; if d.isEmpty { break }; do { try boru.fileHandleForWriting.write(contentsOf: d) } catch { break } }
        try? boru.fileHandleForWriting.close()
    }
    let sure = (j["sure"] as? Double) ?? 7200
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
// Kayıt kipi (5 Kasım): --kayit <iş dosyası> → asistanın önerip kullanıcının panoda onayladığı kayıt işinin Masaüstü'ne dokunan kısmı (aktarıcı oraya
// erişemez). Claude çalıştırılmaz. İş dosyası aktarıcının canlı klasöründe tek kullanımlık: ad kayit-<32 onaltılık>.json, düz dosya, bu hesabın, 0600; okunur
// okunmaz silinir; gövde aynı klasördeki kart-anahtari.txt ile HMAC-SHA256 imzalı, son kullanma ≤ 5 dk, kimlik (nonce) bir kez. Komut Python'a güvenilmeden
// burada YENİDEN doğrulanır; izinli klasörler ve proje kayıt komutu iş dosyasından değil kullanıcının ayar dosyasından okunur. Yalnız iki iş:
//  ozet_duzelt_asil {yol, eski, yeni}: <calisma|proje>/gorusmeler ya da <kod>/testler altındaki .md/.json (gizli ad yok) dosyada eski metin TAM BİR KEZ geçiyorsa değiştirir (geçici dosya + rename).
//  proje_kayit {alt, argumanlar}: ayar kayit_komutu = [python3 yorumlayıcısı, <proje|calisma> altındaki .py betik, sabit önek…] + kayit_alt_komutlar'daki alt komut +
//    argümanlar (metin; "-" ile başlayan yalnız kayit_bayraklar'dakiler). Kabuksuz Process, giriş boş, zaman aşımı (kayit_sure_sn, varsayılan 30). Ayar yoksa kapalı.
// Silme, ağ, keyfi komut yok. Sonuç <klasör>/kayit-<nonce>.sonuc.json (0600): {ok, kod, cikti, hata}. Reddedince çıkış 3.
if let ki = a.firstIndex(of: "--kayit") {
    guard ki + 1 < a.count else { bitir(2) }
    let isYol = gercek(a[ki + 1]), klasor = (isYol as NSString).deletingLastPathComponent, ad = (isYol as NSString).lastPathComponent
    guard altinda(klasor, uygulamaKlasor), ad.range(of: "^kayit-[0-9a-f]{32}\\.json$", options: .regularExpression) != nil else { bitir(3) }
    var st = stat()
    guard lstat(isYol, &st) == 0, (st.st_mode & S_IFMT) == S_IFREG, st.st_uid == getuid(), (st.st_mode & 0o077) == 0, st.st_size < 64_000,
          let veri = FileManager.default.contents(atPath: isYol) else { bitir(3) }
    guard unlink(isYol) == 0 else { bitir(3) }  // tek kullanımlık: önce sil, sonra iş
    let anahtarYol = (klasor as NSString).appendingPathComponent("kart-anahtari.txt"); var sa = stat()
    guard lstat(anahtarYol, &sa) == 0, (sa.st_mode & S_IFMT) == S_IFREG, sa.st_uid == getuid(),
          let anahtar = (try? String(contentsOfFile: anahtarYol, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines), anahtar.count >= 16,
          let dis = (try? JSONSerialization.jsonObject(with: veri)) as? [String: Any], Set(dis.keys) == ["govde", "imza"],
          let govdeMetin = dis["govde"] as? String, let imza = dis["imza"] as? String, let govdeVeri = govdeMetin.data(using: .utf8) else { bitir(3) }
    var mac = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
    let kv = Array(anahtar.utf8), gv = Array(govdeVeri)
    CCHmac(CCHmacAlgorithm(kCCHmacAlgSHA256), kv, kv.count, gv, gv.count, &mac)
    let beklenen = mac.map { String(format: "%02x", $0) }.joined()
    guard imza.count == beklenen.count, zip(imza.utf8, beklenen.utf8).reduce(UInt8(0), { $0 | ($1.0 ^ $1.1) }) == 0 else { bitir(3) }
    guard let g = (try? JSONSerialization.jsonObject(with: govdeVeri)) as? [String: Any], let komut = g["komut"] as? String, let arg = g["arg"] as? [String: Any],
          let son = g["son"] as? Double, let nonce = g["nonce"] as? String, g["v"] as? Int == 1, ad == "kayit-\(nonce).json" else { bitir(3) }
    var izinliAnahtar: Set<String> = ["v", "komut", "arg", "son", "nonce"]
    #if SUFLOR_DENEME
    izinliAnahtar.insert("ayar")  // deneme aktarıcısının ayar dosyası (SUFLOR_AYAR)
    #endif
    let simdi = Date().timeIntervalSince1970
    guard Set(g.keys).isSubset(of: izinliAnahtar), son > simdi, son <= simdi + 300 else { bitir(3) }
    let kullanilan = (klasor as NSString).appendingPathComponent("kayit-kullanilan.txt")
    var satirlar = ((try? String(contentsOfFile: kullanilan, encoding: .utf8)) ?? "").split(separator: "\n").map(String.init)
    guard !satirlar.contains(where: { $0.hasPrefix(nonce) }) else { bitir(3) }
    satirlar.append("\(nonce) \(Int(simdi))"); satirlar = Array(satirlar.suffix(200))
    FileManager.default.createFile(atPath: kullanilan, contents: (satirlar.joined(separator: "\n") + "\n").data(using: .utf8), attributes: [.posixPermissions: 0o600])
    let sonucYol = (klasor as NSString).appendingPathComponent("kayit-\(nonce).sonuc.json")
    func sonucYaz(_ ok: Bool, _ kod: Int, _ cikti: String, _ hata: String, _ cikis: Int32) -> Never {
        let o: [String: Any] = ["ok": ok, "kod": kod, "cikti": String(cikti.prefix(4000)), "hata": hata]
        if let d = try? JSONSerialization.data(withJSONObject: o) {
            let gec = sonucYol + ".tmp"; FileManager.default.createFile(atPath: gec, contents: d, attributes: [.posixPermissions: 0o600]); _ = rename(gec, sonucYol)
        }
        bitir(cikis)
    }
    var ayarYol = NSHomeDirectory() + "/Library/Application Support/Suflor/ayar.json"
    #if SUFLOR_DENEME
    if let y = g["ayar"] as? String { ayarYol = y }
    #endif
    guard let ad0 = FileManager.default.contents(atPath: ayarYol), let ayar = (try? JSONSerialization.jsonObject(with: ad0)) as? [String: Any] else { sonucYaz(false, -1, "", "ayar okunamadı", 2) }
    func ayarKlasor(_ k: String) -> String? { (ayar[k] as? String).flatMap { $0.isEmpty ? nil : gercek(($0 as NSString).expandingTildeInPath) } }
    func metinUygun(_ v: Any?, _ enAz: Int, _ enCok: Int) -> String? {
        guard let s = v as? String, !s.contains("\0"), s.count >= enAz, s.count <= enCok else { return nil }; return s
    }
    if komut == "ozet_duzelt_asil" {
        guard Set(arg.keys) == ["yol", "eski", "yeni"], let y0 = metinUygun(arg["yol"], 1, 1024), let eski = metinUygun(arg["eski"], 2, 1000),
              let yeni = metinUygun(arg["yeni"], 0, 2000), eski != yeni else { sonucYaz(false, -1, "", "argümanlar uymuyor", 3) }
        var kokler: [String] = []
        if let c = ayarKlasor("calisma") ?? ayarKlasor("proje") { kokler.append((c as NSString).appendingPathComponent("gorusmeler")) }
        if let k = ayarKlasor("kod") { kokler.append((k as NSString).appendingPathComponent("testler")) }
        let yol = gercek((y0 as NSString).expandingTildeInPath)
        guard let kok = kokler.map({ gercek($0) }).first(where: { yol.hasPrefix($0 + "/") }),
              !yol.dropFirst(kok.count + 1).split(separator: "/").contains(where: { $0.hasPrefix(".") }),
              yol.hasSuffix(".md") || yol.hasSuffix(".json") else { sonucYaz(false, -1, "", "izinli özet klasörü dışında", 3) }
        var sy = stat()
        guard lstat(yol, &sy) == 0, (sy.st_mode & S_IFMT) == S_IFREG, sy.st_size < 4_000_000, let icerik = try? String(contentsOfFile: yol, encoding: .utf8)
        else { sonucYaz(false, -1, "", "dosya okunamadı", 1) }
        let ns = icerik as NSString; var n = 0, ara = NSRange(location: 0, length: ns.length)
        while true {
            let r = ns.range(of: eski, options: .literal, range: ara); if r.location == NSNotFound { break }
            n += 1; let bas = r.location + r.length; ara = NSRange(location: bas, length: ns.length - bas)
        }
        guard n == 1 else { sonucYaz(false, -1, "", n == 0 ? "eski metin dosyada yok" : "eski metin birden çok yerde geçiyor", 1) }
        let yeniIcerik = ns.replacingOccurrences(of: eski, with: yeni, options: .literal, range: NSRange(location: 0, length: ns.length))
        let gec = (yol as NSString).deletingLastPathComponent + "/.suflor-\(nonce).tmp"
        guard FileManager.default.createFile(atPath: gec, contents: yeniIcerik.data(using: .utf8), attributes: [.posixPermissions: Int(sy.st_mode & 0o777)]),
              rename(gec, yol) == 0 else { unlink(gec); sonucYaz(false, -1, "", "yazılamadı", 1) }
        sonucYaz(true, 0, "", "", 0)
    }
    guard komut == "proje_kayit" else { sonucYaz(false, -1, "", "izinli olmayan komut", 3) }
    guard let kk = ayar["kayit_komutu"] as? [String], kk.count >= 2, let altlar = ayar["kayit_alt_komutlar"] as? [String], !altlar.isEmpty
    else { sonucYaz(false, -1, "", "proje kayıt komutu ayarlı değil", 3) }
    let bayraklar = Set((ayar["kayit_bayraklar"] as? [String]) ?? [])
    let yorumlayici = (kk[0] as NSString).expandingTildeInPath, betik = gercek((kk[1] as NSString).expandingTildeInPath)
    let pyAdi = "^python3(\\.[0-9]+)?$"  // bağ çözülmüş adı da python3: yorumlayıcı yerine başka bir araç (rm gibi) betik yolunu argüman olarak alamasın
    let kokler = ["proje", "calisma"].compactMap { ayarKlasor($0) }
    guard yorumlayici.hasPrefix("/"), (yorumlayici as NSString).lastPathComponent.range(of: pyAdi, options: .regularExpression) != nil,
          (gercek(yorumlayici) as NSString).lastPathComponent.range(of: pyAdi, options: .regularExpression) != nil,
          FileManager.default.isExecutableFile(atPath: yorumlayici), betik.hasSuffix(".py"), let kok = kokler.first(where: { betik.hasPrefix($0 + "/") }),
          FileManager.default.isReadableFile(atPath: betik), kk.dropFirst(2).allSatisfy({ !$0.contains("\0") && $0.count <= 200 })
    else { sonucYaz(false, -1, "", "proje kayıt komutu uygun değil", 3) }
    guard Set(arg.keys) == ["alt", "argumanlar"], let alt = arg["alt"] as? String, altlar.contains(alt),
          alt.range(of: "^[A-Za-z][A-Za-z0-9_-]{0,40}$", options: .regularExpression) != nil,
          let ar = arg["argumanlar"] as? [Any], ar.count <= 20 else { sonucYaz(false, -1, "", "alt komut izinli değil", 3) }
    var argumanlar: [String] = []
    for x in ar {
        guard let s = metinUygun(x, 0, 2000) else { sonucYaz(false, -1, "", "argüman uygun değil", 3) }
        if s.hasPrefix("-") { guard bayraklar.contains(s) else { sonucYaz(false, -1, "", "izinli olmayan bayrak", 3) } }
        argumanlar.append(s)
    }
    // Foundation Process argümanları NFD'ye çeviriyor ("ü" → "u" + birleşik işaret; 5 Kasım ölçümü) — Türkçe metin kayda bozuk girmesin diye posix_spawn,
    // argümanlar UTF-8 olduğu gibi. Süreç kendi süreç grubunda: zaman aşımında alt süreçleriyle birlikte durdurulur.
    var e = ProcessInfo.processInfo.environment.filter { !$0.key.hasPrefix("PYTHON") && !$0.key.hasPrefix("DYLD_") }
    e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"; e["PYTHONDONTWRITEBYTECODE"] = "1"
    let argv: [UnsafeMutablePointer<CChar>?] = ([yorumlayici, betik] + Array(kk.dropFirst(2)) + [alt] + argumanlar).map { strdup($0) } + [nil]
    let envp: [UnsafeMutablePointer<CChar>?] = e.map { strdup("\($0.key)=\($0.value)") } + [nil]
    var fds: [Int32] = [0, 0]
    guard pipe(&fds) == 0 else { sonucYaz(false, -1, "", "çalıştırılamadı", 4) }
    var fa: posix_spawn_file_actions_t? = nil, at: posix_spawnattr_t? = nil
    posix_spawn_file_actions_init(&fa); posix_spawnattr_init(&at)
    posix_spawn_file_actions_addopen(&fa, 0, "/dev/null", O_RDONLY, 0)
    posix_spawn_file_actions_adddup2(&fa, fds[1], 1); posix_spawn_file_actions_adddup2(&fa, fds[1], 2)
    posix_spawn_file_actions_addclose(&fa, fds[0]); posix_spawn_file_actions_addclose(&fa, fds[1])
    posix_spawn_file_actions_addchdir_np(&fa, kok)
    posix_spawnattr_setflags(&at, Int16(POSIX_SPAWN_SETPGROUP)); posix_spawnattr_setpgroup(&at, 0)
    var pid: pid_t = 0
    let rs = posix_spawn(&pid, yorumlayici, &fa, &at, argv, envp)
    close(fds[1])
    guard rs == 0 else { close(fds[0]); sonucYaz(false, -1, "", "çalıştırılamadı", 4) }
    var cikti = Data(); let okundu = DispatchSemaphore(value: 0)
    let okuyucu = FileHandle(fileDescriptor: fds[0], closeOnDealloc: true)
    DispatchQueue.global().async {
        while true { let d = okuyucu.availableData; if d.isEmpty { break }; if cikti.count < 16_000 { cikti.append(d) } }
        okundu.signal()
    }
    let sure = min(max((ayar["kayit_sure_sn"] as? Double) ?? 30, 1), 120)
    var asim = false, bitti = false
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) {
        if !bitti { asim = true; kill(-pid, SIGTERM); Thread.sleep(forTimeInterval: 2); if !bitti { kill(-pid, SIGKILL) } }
    }
    var durum: Int32 = 0
    while waitpid(pid, &durum, 0) < 0 && errno == EINTR {}
    bitti = true; _ = okundu.wait(timeout: .now() + 3)
    let kod: Int32 = (durum & 0x7f) == 0 ? (durum >> 8) & 0xff : -(durum & 0x7f)
    let metin = String(decoding: cikti.prefix(8000), as: UTF8.self)
    if asim { sonucYaz(false, -1, metin, "zaman aşımı (\(Int(sure)) sn)", 5) }
    sonucYaz(kod == 0, Int(kod), metin, kod == 0 ? "" : "çıkış kodu \(kod)", 0)
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
    let tek: Set<String> = ["-p", "--print", "--verbose", "--chrome"]  // --chrome (5 Kasım): Claude in Chrome araçları; hangilerinin çalışacağını aktarıcının izin kararı (toplanti-oturum.py topo_chrome_karar) sınırlar
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
    let p = NfcSurec()
    p.executableURL = URL(fileURLWithPath: claudeGercek); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
    var e = ProcessInfo.processInfo.environment; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (e["PATH"] ?? ""); p.environment = e
    signal(SIGPIPE, SIG_IGN)
    let boru = Pipe()
    p.stdinFd = boru.fileHandleForReading.fileDescriptor; p.stdoutFd = cik.fileDescriptor
    do { try p.run() } catch { bitir(4) }
    try? boru.fileHandleForReading.close()
    Thread.detachNewThread {
        while true { let d = gir.availableData; if d.isEmpty { break }; do { try boru.fileHandleForWriting.write(contentsOf: d) } catch { break } }
        try? boru.fileHandleForWriting.close()
        // v0.112.0: giriş kapanınca (Bitir, yeni Başlat, Terminal'e alma) Monitor çalışan claude çıkmıyordu (arka plan işini bekliyor) — 5 sn sonra kapatılır
        Thread.sleep(forTimeInterval: 5); if p.isRunning { p.terminate() }
        Thread.sleep(forTimeInterval: 3); if p.isRunning { kill(p.processIdentifier, SIGKILL) }
    }
    let sure = (j["sure"] as? Double) ?? 21600
    DispatchQueue.global().asyncAfter(deadline: .now() + sure) { if p.isRunning { p.terminate() } }
    p.waitUntilExit(); bitir(p.terminationStatus)
}
// izin listesi: değersiz bayraklar, değerli bayraklar (değer denetimiyle); -p'den hemen sonraki tek metin istemdir, başka konumsal argüman yok
let tekBayrak: Set<String> = ["-p", "--print", "--verbose", "--include-partial-messages", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
// WebSearch/WebFetch (5 Kasım, S208): yalnız Python tarafı ayar konus_web açıkken ve gizli olmayan toplantıda ister (bas-konus.py konus_web_acik); bu liste yalnız yardımcının reddetmemesi içindir. bas-konus.py KONUS_WEB_RX bu satırı arar.
let araclar: Set<String> = ["Read", "Grep", "Glob", "WebSearch", "WebFetch"]
// Dış bilgi kaynağı araçları (Konuş, 1 Kasım): mcp__<sunucu>__<okuma önekli desen>; sunucu adında "__" yok, desen yalnız [A-Za-z0-9_*], okuma öneki
// (get|list|query|compare|search|fetch|read|describe|lookup|find)_ ile başlar ve "_" parçalarında yazma sözcüğü yok. Python'daki beyin.py BILGI_YAZMA ile AYNI küme:
// ikisini birlikte değiştir (test/bilgi-kaynagi.py eşitliği denetler). mcp__suflorvt__ eskisi gibi.
let bilgiYazma: Set<String> = ["send", "forward", "reply", "create", "update", "delete", "remove", "trash", "upload", "share", "move", "rename", "copy", "respond", "set", "write",
    "post", "put", "patch", "edit", "modify", "add", "insert", "pause", "resume", "enable", "disable", "publish", "archive", "cancel", "approve", "execute",
    "run", "javascript", "navigate", "computer", "label", "draft", "mark", "schedule", "import", "sync", "trigger", "start", "stop", "apply", "assign",
    "invite", "grant", "revoke", "reset", "change", "save", "submit", "merge", "duplicate", "launch", "activate", "deactivate"]
let bilgiOkuma: [String] = ["get", "list", "query", "compare", "search", "fetch", "read", "describe", "lookup", "find"]
func bilgiAracUygun(_ t: String) -> Bool {
    guard t.hasPrefix("mcp__") else { return false }
    let r = String(t.dropFirst(5)), p = r.components(separatedBy: "__")
    guard p.count == 2, p[0].range(of: "^[A-Za-z0-9_-]+$", options: .regularExpression) != nil else { return false }
    let d = p[1]
    guard d.range(of: "^(get|list|query|compare|search|fetch|read|describe|lookup|find)_[A-Za-z0-9_*]*$", options: .regularExpression) != nil else { return false }
    return Set(d.lowercased().replacingOccurrences(of: "*", with: "").components(separatedBy: "_")).isDisjoint(with: bilgiYazma)
}
func aracUygun(_ v: String) -> Bool { v.split(separator: ",").allSatisfy { let t = $0.trimmingCharacters(in: .whitespaces); return araclar.contains(t) || t.hasPrefix("mcp__suflorvt__") || bilgiAracUygun(t) } }
func ayarUygun(_ v: String) -> Bool {  // --settings: yalnız "env" (CLAUDE_CODE_DISABLE_CLAUDE_MDS, CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS) ve "allowedMcpServers" (kanca, izin, model yok)
    guard let d = v.data(using: .utf8), let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any], !o.isEmpty, Set(o.keys).isSubset(of: ["env", "allowedMcpServers"]) else { return false }
    if let e0 = o["env"] {
        guard let e = e0 as? [String: Any], Set(e.keys).isSubset(of: ["CLAUDE_CODE_DISABLE_CLAUDE_MDS", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"]),
              e.values.allSatisfy({ $0 is String }) else { return false }
    }
    if let a0 = o["allowedMcpServers"] {
        guard let a = a0 as? [[String: Any]], a.count >= 1, a.count <= 4 else { return false }
        for k in a {
            if Set(k.keys) == ["serverUrl"] {
                guard let u = k["serverUrl"] as? String, u.hasPrefix("https://"), u.count <= 200, u.count > 8,
                      u.range(of: "^https://[^\\s\"'\\\\]+$", options: .regularExpression) != nil else { return false }
            } else if Set(k.keys) == ["serverName"] { guard k["serverName"] as? String == "suflorvt" else { return false } }
            else { return false }
        }
    }
    return true
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
// Dış bilgi kaynağı aracı izinliyse bağlayıcılar allowedMcpServers ile sınırlı olmalı (yoksa strict'siz süreçte bu Mac'teki her bağlayıcı yüklenir).
func degerOf(_ b: String) -> [String] { arg.indices.filter { arg[$0] == b && $0 + 1 < arg.count }.map { arg[$0 + 1] } }
if degerOf("--allowedTools").contains(where: { $0.split(separator: ",").contains { bilgiAracUygun($0.trimmingCharacters(in: .whitespaces)) && !$0.contains("mcp__suflorvt__") } }),
   !degerOf("--settings").contains(where: { ($0.data(using: .utf8).flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any])?["allowedMcpServers"] != nil }) { bitir(3) }

let p = NfcSurec()
if let giris = j["giris"] as? String, let cikis = j["cikis"] as? String {
    guard let gir = FileHandle(forReadingAtPath: giris), let cik = FileHandle(forWritingAtPath: cikis) else { bitir(7) }
    p.executableURL = URL(fileURLWithPath: claudeGercek); p.arguments = arg; p.currentDirectoryURL = URL(fileURLWithPath: cwd)
    var e = ProcessInfo.processInfo.environment; e["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + (e["PATH"] ?? ""); p.environment = e
    // v0.57.6: Claude Code adlı FIFO girişinde dosya sonunu görmüyor (17 Ekim denemesi: anonim boruda giriş kapanınca çıkıyor, FIFO'da hiç çıkmıyor) —
    // aktarıcı süreci yenileyince eski claude + veritabanı yardımcısı açık kalıyordu (süreç başına ~250 MB). FIFO'yu burada okuyup anonim boruyla
    // aktarırız; FIFO kapanınca boru kapanır, claude çıkar, uygulama biter.
    signal(SIGPIPE, SIG_IGN)
    let boru = Pipe()
    p.stdinFd = boru.fileHandleForReading.fileDescriptor; p.stdoutFd = cik.fileDescriptor
    do { try p.run() } catch { bitir(4) }
    try? boru.fileHandleForReading.close()
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
let cik = Pipe(); p.stdoutFd = cik.fileHandleForWriting.fileDescriptor
do { try p.run() } catch { bitir(4) }
try? cik.fileHandleForWriting.close()  // yazma ucu yalnız claude'da kalsın: o çıkınca okuma biter

var sonuc = Data(); let okundu = DispatchSemaphore(value: 0)
DispatchQueue.global().async { sonuc = cik.fileHandleForReading.readDataToEndOfFile(); okundu.signal() }
if okundu.wait(timeout: .now() + ((j["sure"] as? Double) ?? 240)) == .timedOut { p.terminate(); bitir(5) }
p.waitUntilExit()
let gecici = cikti + ".tmp"
FileManager.default.createFile(atPath: gecici, contents: sonuc, attributes: [.posixPermissions: 0o600])
if rename(gecici, cikti) != 0 { bitir(6) }
bitir(p.terminationStatus)
