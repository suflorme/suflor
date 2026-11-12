// Suflor.me — Konuş ses yardımcısı ("Suflor Konus.app", launchd etiketi local.suflor.konus). Aşama 2, Adım 1 (12 Kasım 2026).
// Toplantı dışındaki Konuş sohbetinde mikrofonu ve asistanın sesini TEK AVAudioEngine'de tutar: hoparlörde Apple ses işleme (VoiceProcessingIO,
// VPIO) açılır, motorun kendi çaldığı ses yankı başvurusu olur (10 Kasım ölçümü: kalıntı −74,5 dBFS, çift yönde söz korunuyor). Kulaklıkta VPIO kapalı.
// Toplantı hattı (ses-yardimcisi.swift, menü uygulaması, BlackHole) bu yardımcıdan ayrıdır ve değişmez: VPIO açıkken sistemdeki diğer mikrofon
// kayıtları ~22 dB kısık geldiği için toplantı uygulaması mikrofonu ≥ 1 sn alınca VPIO kendiliğinden kapanır (toplanti_mik olayı).
// İletişim: Unix soket <uygulama>/konus-ses.sock (0600), satır başına bir JSON; sözleşme ../planlar/konus-ses-protokol.md (aktarici/yerel-konus.py).
// Mikrofonu yalnız aktarıcının mik_ac komutu açar; yardımcı kendi başına hiçbir aygıt açmaz (boşta yalnız soketi dinler). Aktarıcının bağlantısı
// koparsa mikrofon ve çalma hemen kapanır. Ses diske yazılmaz, ağ yok (yalnız yerel soket).
// Kullanım: SuflorKonus --uygulama <klasör> [--kuru] [--bosta-sn 300] [--nabiz-sn 5] | --izin (kurulumda mikrofon izni penceresi, sonra çıkar)
// --kuru: ses aygıtı açmadan sözleşmeyi taklit eder (testler); SIGUSR1 = aygıt değişti (kulaklık takıldı/çıktı), SIGUSR2 = toplantı mikrofonu aç/kapa.
import Foundation
import CoreAudio
import AudioToolbox
import AVFoundation

let SURUM = "1.0.0"

// --- argümanlar ---
var arg: [String: String] = [:]
var kuru = false, izinKipi = false
do {
    let a = CommandLine.arguments; var i = 1
    while i < a.count {
        if a[i] == "--kuru" { kuru = true; i += 1 }
        else if a[i] == "--izin" { izinKipi = true; i += 1 }
        else if a[i].hasPrefix("--"), i + 1 < a.count { arg[String(a[i].dropFirst(2))] = a[i + 1]; i += 2 } else { i += 1 }
    }
}
let saatBicim: DateFormatter = { let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm:ss"; return f }()
func gunluk(_ s: String) { FileHandle.standardError.write((saatBicim.string(from: Date()) + " Suflor Konus: " + s + "\n").data(using: .utf8)!) }

// --- saat: ts = mach_absolute_time sn (AVAudioTime.hostTime ile aynı taban); duvar = aynı anın Unix saati (time.time()).
// Python 3.9'un time.monotonic()'i süreç başına sıfırdan sayar (mach_absolute_time − ilk çağrı) → süreçler arası karşılaştırılamaz; aktarıcı duvar'ı kullanır. ---
var tb = mach_timebase_info_data_t(); mach_timebase_info(&tb)
func hostSn(_ h: UInt64) -> Double { Double(h) * Double(tb.numer) / Double(tb.denom) / 1e9 }
func simdi() -> Double { hostSn(mach_absolute_time()) }
func duvar(_ ts: Double) -> Double { Date().timeIntervalSince1970 - (simdi() - ts) }
func uyanik() -> Double { ProcessInfo.processInfo.systemUptime }   // boşta sayacı: uykuda ilerlemez (ses-yardimcisi v0.97.0 dersi)

// --- izin kipi (kurulum: python3 kurulum.py kur → open -W -a "Suflor Konus.app" --args --izin) ---
if izinKipi {
    let durum = AVCaptureDevice.authorizationStatus(for: .audio)
    if durum == .authorized { print("izin=var"); exit(0) }
    if durum != .notDetermined { print("izin=yok"); exit(1) }
    let sem = DispatchSemaphore(value: 0); var verildi = false
    AVCaptureDevice.requestAccess(for: .audio) { verildi = $0; sem.signal() }
    _ = sem.wait(timeout: .now() + 120)
    print(verildi ? "izin=var" : "izin=yok"); exit(verildi ? 0 : 1)
}

let uygulama: String = {
    // varsayılan: paketin bulunduğu klasör (<uygulama>/Suflor Konus.app) — kurulum yardımcıyı uygulama klasörüne koyar
    let v = arg["uygulama"] ?? ProcessInfo.processInfo.environment["SUFLOR_UYGULAMA"] ?? Bundle.main.bundleURL.deletingLastPathComponent().path
    return (v as NSString).expandingTildeInPath
}()
let soketYol = (uygulama as NSString).appendingPathComponent("konus-ses.sock")
let anahtarYol = (uygulama as NSString).appendingPathComponent("ses-anahtari.txt")
let bostaSn = Double(arg["bosta-sn"] ?? "") ?? 300
let nabizSn = max(0.2, Double(arg["nabiz-sn"] ?? "") ?? 5)
let ana = DispatchQueue(label: "suflor.konus.ana", qos: .userInteractive)   // tüm durum bu sıradadır
let yazKuyruk = DispatchQueue(label: "suflor.konus.yaz", qos: .userInteractive)

// --- anahtar: <uygulama>/ses-anahtari.txt (0600). Yoksa yardımcı üretir (O_EXCL: aktarıcı da aynı anda üretiyorsa kazanan yazar, öbürü okur) ---
func anahtarOku() -> String {
    if let s = try? String(contentsOfFile: anahtarYol, encoding: .utf8) {
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines); if !t.isEmpty { return t }
    }
    var b = [UInt8](repeating: 0, count: 24)
    guard SecRandomCopyBytes(kSecRandomDefault, b.count, &b) == errSecSuccess else { return "" }
    let yeni = b.map { String(format: "%02x", $0) }.joined()
    let fd = open(anahtarYol, O_WRONLY | O_CREAT | O_EXCL, 0o600)
    if fd >= 0 { _ = yeni.withCString { write(fd, $0, strlen($0)) }; close(fd); return yeni }
    let s = (try? String(contentsOfFile: anahtarYol, encoding: .utf8)) ?? ""
    return s.trimmingCharacters(in: .whitespacesAndNewlines)
}
func esit(_ a: String, _ b: String) -> Bool {   // sabit süreli karşılaştırma
    let x = Array(a.utf8), y = Array(b.utf8); if x.count != y.count || x.isEmpty { return false }
    var f: UInt8 = 0; for i in 0..<x.count { f |= x[i] ^ y[i] }; return f == 0
}

// --- Core Audio yardımcıları (ses-yardimcisi.swift ile aynı düzen) ---
func ozellik<T>(_ nesne: AudioObjectID, _ secici: AudioObjectPropertySelector, _ bos: T, kapsam: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal) -> T? {
    var adr = AudioObjectPropertyAddress(mSelector: secici, mScope: kapsam, mElement: kAudioObjectPropertyElementMain)
    var boyut = UInt32(MemoryLayout<T>.size); var v = bos
    let r = withUnsafeMutablePointer(to: &v) { AudioObjectGetPropertyData(nesne, &adr, 0, nil, &boyut, $0) }
    return r == noErr ? v : nil
}
func dizi(_ nesne: AudioObjectID, _ secici: AudioObjectPropertySelector) -> [AudioObjectID] {
    var adr = AudioObjectPropertyAddress(mSelector: secici, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var boyut: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(nesne, &adr, 0, nil, &boyut) == noErr, boyut > 0 else { return [] }
    var ids = [AudioObjectID](repeating: 0, count: Int(boyut) / MemoryLayout<AudioObjectID>.size)
    guard AudioObjectGetPropertyData(nesne, &adr, 0, nil, &boyut, &ids) == noErr else { return [] }
    return ids
}
func metin(_ nesne: AudioObjectID, _ secici: AudioObjectPropertySelector) -> String? {
    var adr = AudioObjectPropertyAddress(mSelector: secici, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var boyut = UInt32(MemoryLayout<CFString?>.size); var s: Unmanaged<CFString>? = nil
    guard AudioObjectGetPropertyData(nesne, &adr, 0, nil, &boyut, &s) == noErr, let s else { return nil }
    return s.takeRetainedValue() as String
}
func dortHarf(_ v: UInt32) -> String {
    let b = [UInt8((v >> 24) & 0xff), UInt8((v >> 16) & 0xff), UInt8((v >> 8) & 0xff), UInt8(v & 0xff)]
    return String(bytes: b, encoding: .isoLatin1) ?? "?"
}
let SISTEM = AudioObjectID(kAudioObjectSystemObject)
struct Aygit: Equatable { var cikisID: AudioObjectID = 0; var girisID: AudioObjectID = 0; var cikis = "?"; var giris = "?"; var kulaklik = false }
// Kulaklık kararı aktarici/brifing-ses.py _kulaklik_karar ile aynı: Bluetooth / BLE / USB → evet; yerleşik aygıtta veri kaynağı "hdpn" ya da adı kulaklık diyen → evet;
// HDMI, AirPlay, DisplayPort, sanal → hayır.
let KULAKLIK_AD = try! NSRegularExpression(pattern: "kulakl[ıi]k|headphone|airpods|headset|earbuds|earpods", options: [.caseInsensitive])
func aygitOku() -> Aygit {
    var a = Aygit()
    a.cikisID = ozellik(SISTEM, kAudioHardwarePropertyDefaultOutputDevice, AudioObjectID(0)) ?? 0
    a.girisID = ozellik(SISTEM, kAudioHardwarePropertyDefaultInputDevice, AudioObjectID(0)) ?? 0
    if a.cikisID != 0 { a.cikis = metin(a.cikisID, kAudioObjectPropertyName) ?? "?" }
    if a.girisID != 0 { a.giris = metin(a.girisID, kAudioObjectPropertyName) ?? "?" }
    if a.cikisID != 0 {
        let tasima = dortHarf(ozellik(a.cikisID, kAudioDevicePropertyTransportType, UInt32(0)) ?? 0)
        let kaynak = tasima == "bltn" ? dortHarf(ozellik(a.cikisID, kAudioDevicePropertyDataSource, UInt32(0), kapsam: kAudioObjectPropertyScopeOutput) ?? 0) : ""
        if ["blue", "bleo", "usb "].contains(tasima) { a.kulaklik = true }
        else if tasima == "bltn" && kaynak == "hdpn" { a.kulaklik = true }
        else if !["hdmi", "airp", "dprt", "virt"].contains(tasima) {
            a.kulaklik = KULAKLIK_AD.firstMatch(in: a.cikis, range: NSRange(a.cikis.startIndex..., in: a.cikis)) != nil
        }
    }
    return a
}

// --- toplantı uygulaması mikrofonu: Core Audio süreç listesi (izin gerekmez), yalnız bu hesabın süreçleri. Liste ses-yardimcisi.swift AILELER ile aynı ---
let AILELER: [(onek: String, ad: String)] = [
    ("com.google.Chrome", "Chrome"), ("com.microsoft.edgemac", "Edge"), ("com.brave.Browser", "Brave"), ("company.thebrowser", "Arc"),
    ("com.apple.WebKit", "Safari"), ("com.apple.Safari", "Safari"), ("com.microsoft.teams", "Teams"), ("us.zoom", "Zoom"),
    ("com.tinyspeck.slackmacgap", "Slack"), ("com.apple.FaceTime", "FaceTime"), ("com.cisco.webex", "Webex"), ("Cisco-Systems.Spark", "Webex")]
func sahibi(_ pid: pid_t) -> uid_t? {
    var bilgi = kinfo_proc(); var boyut = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard sysctl(&mib, 4, &bilgi, &boyut, nil, 0) == 0, boyut > 0 else { return nil }
    return bilgi.kp_eproc.e_ucred.cr_uid
}
let benimUid = getuid(), benimPid = getpid()
var uidOnbellek: [pid_t: Bool] = [:]
func mikrofonluAileler() -> Set<String> {   // mikrofonu şu an kullanan toplantı uygulaması aileleri (ad)
    if uidOnbellek.count > 2000 { uidOnbellek.removeAll() }
    var s = Set<String>()
    for id in dizi(SISTEM, kAudioHardwarePropertyProcessObjectList) {
        guard (ozellik(id, kAudioProcessPropertyIsRunningInput, UInt32(0)) ?? 0) != 0 else { continue }
        let pid = ozellik(id, kAudioProcessPropertyPID, pid_t(0)) ?? 0
        guard pid > 0, pid != benimPid else { continue }
        let benim = uidOnbellek[pid] ?? { let b = sahibi(pid) == benimUid; uidOnbellek[pid] = b; return b }()
        guard benim, let bundle = metin(id, kAudioProcessPropertyBundleID), let a = AILELER.first(where: { bundle.hasPrefix($0.onek) }) else { continue }
        s.insert(a.ad)
    }
    return s
}

// --- bağlantı ---
final class Baglanti {
    let fd: Int32; var kimlikli = false; var tampon: [UInt8] = []; var kaynak: DispatchSourceRead? = nil
    var bitti = false                                   // ana sırada: kapatıldı (mantık)
    let kilit = NSLock(); var _kapali = false           // yazım sırasında: soket kapandı (bekleyen yazımlar bitti)
    var kapali: Bool { kilit.lock(); defer { kilit.unlock() }; return _kapali }
    init(_ fd: Int32) { self.fd = fd }
}
var istemci: Baglanti? = nil          // kimliği doğrulanmış tek istemci (aktarıcı)
var bekleyenler: [Baglanti] = []      // anahtar satırını bekleyenler
var sonBaglanti = uyanik()            // son kez istemci bağlıyken (boşta sayacı)

func yazHam(_ b: Baglanti, _ veri: Data) {
    yazKuyruk.async {
        if b.kapali { return }
        var hata = false
        veri.withUnsafeBytes { (p: UnsafeRawBufferPointer) in
            var kalan = p.count, ofs = 0
            while kalan > 0 {
                let n = send(b.fd, p.baseAddress! + ofs, kalan, 0)
                if n < 0 { if errno == EINTR { continue }; hata = true; return }
                kalan -= n; ofs += n
            }
        }
        if hata { ana.async { kapat(b, neden: "yazılamadı") } }
    }
}
func gonderB(_ b: Baglanti, _ o: [String: Any]) {
    guard var d = try? JSONSerialization.data(withJSONObject: o) else { return }
    d.append(10); yazHam(b, d)
}
func gonder(_ o: [String: Any]) { if let b = istemci { gonderB(b, o) } }
func kapat(_ b: Baglanti, neden: String) {
    if b.bitti { return }
    b.bitti = true
    b.kaynak?.cancel(); b.kaynak = nil   // iptal işleyicisi soketi yazım sırasında, bekleyen yazımlardan (ör. hata satırı) sonra kapatır
    bekleyenler.removeAll { $0 === b }
    if istemci === b {
        istemci = nil; sonBaglanti = uyanik()
        gunluk("aktarıcı bağlantısı kapandı (\(neden)) — mikrofon ve çalma kapanıyor")
        hepsiniKapat()
    }
}

// --- durum ---
var mikAcik = false, istenenVpio = false, sessizDugum = false
var toplantiMik: String? = nil            // mikrofonu ≥ 1 sn tutan toplantı uygulaması
var mikIlk: [String: Double] = [:], mikSonGorulme = 0.0
var aygit = Aygit(), sonHata: String? = nil
var kuruKulaklik = false

func hataBildir(_ neden: String, _ ayrinti: String) {
    sonHata = "\(neden): \(ayrinti)"; gunluk("hata \(neden): \(ayrinti)")
    gonder(["t": "hata", "neden": neden, "ayrinti": ayrinti])
}
func kulaklikta() -> Bool { kuru ? kuruKulaklik : aygit.kulaklik }
func etkinVpio() -> Bool { mikAcik && istenenVpio && !kulaklikta() && toplantiMik == nil }

// --- motor: tek AVAudioEngine (mikrofon girişi + çalıcı düğüm); kuru kipte yalnız zamanlayıcı ---
final class Motor {
    var eng: AVAudioEngine? = nil; var oyn: AVAudioPlayerNode? = nil
    var giris = false, vp = false, kurulus = 0.0, kusak = 0   // kusak: bu motorun öbeklerinin mikrofon kuşağı
    var kuruMik: DispatchSourceTimer? = nil
    var bosSince: Double? = nil   // gerekmediği andan beri (çıkış yalnız motor 30 sn sonra durur)
}
var motor: Motor? = nil
let OYN_FMT = AVAudioFormat(standardFormatWithSampleRate: 48000, channels: 1)!
let CIK_FMT = AVAudioFormat(standardFormatWithSampleRate: 48000, channels: 2)!   // açık 48 kHz bağlantı: aksi halde VPIO çıkış birimi −10875 verir
let MIK_FMT = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true)!
let OBEK = 1600                                    // 100 ms @ 16 kHz

// mikrofon öbekleme (ana sırada)
// Kuşak (12 Kasım denetimi): her mik_ac/mik_kapat'ta artar; tap'ten ya da zamanlayıcıdan kapanıştan önce kuyruğa girmiş öbek eski kuşakla gelir ve atılır.
// mik_kapat işlendikten sonra hiçbir mik olayı yazılmaz (gizli kip, toplantı kapatıcısı).
var mikTampon: [Int16] = [], mikTamponT = 0.0, mikKusak = 0
func mikEkle(_ x: [Int16], _ t: Double, kusak: Int) {
    guard mikAcik, kusak == mikKusak, istemci != nil else { mikTampon.removeAll(); return }
    if mikTampon.isEmpty { mikTamponT = t }
    mikTampon.append(contentsOf: x)
    while mikTampon.count >= OBEK {
        guard mikAcik, kusak == mikKusak else { mikTampon.removeAll(); return }   // gönderimden hemen önce
        let parca = Array(mikTampon[0..<OBEK]); mikTampon.removeFirst(OBEK)
        var top = 0.0; for v in parca { let f = Double(v); top += f * f }
        let rms = (top / Double(OBEK)).squareRoot(), duzey = rms > 0 ? max(-120, 20 * log10(rms / 32768)) : -120
        let veri = parca.withUnsafeBufferPointer { Data(buffer: $0) }
        gonder(["t": "mik", "b64": veri.base64EncodedString(), "duzey": (duzey * 10).rounded() / 10, "vpio": motor?.vp ?? false, "ts": mikTamponT, "duvar": duvar(mikTamponT)])
        mikTamponT += Double(OBEK) / 16000
    }
}

func motorDurdur(kesildiGonder: Bool) {
    guard let m = motor else { return }
    m.kuruMik?.cancel(); m.kuruMik = nil
    if let e = m.eng { if m.giris { e.inputNode.removeTap(onBus: 0) }; m.oyn?.stop(); e.stop() }
    motor = nil; mikTampon.removeAll()
    if let a = akis { akis = nil; if kesildiGonder { gonder(["t": "kesildi", "id": a.id]) } }
    gunluk("motor durdu")
}
func motorKur() {
    motorDurdur(kesildiGonder: true)
    let m = Motor(); m.giris = mikAcik; m.vp = etkinVpio(); m.kurulus = uyanik(); m.kusak = mikKusak
    if kuru {
        if m.giris {
            let z = DispatchSource.makeTimerSource(queue: ana); z.schedule(deadline: .now() + 0.1, repeating: 0.1)
            z.setEventHandler { if motor === m { mikEkle([Int16](repeating: 0, count: OBEK), simdi() - 0.1, kusak: m.kusak) } }; z.resume(); m.kuruMik = z
        }
        motor = m; gunluk("motor (kuru) kuruldu: mikrofon \(m.giris), vpio \(m.vp)"); return
    }
    let e = AVAudioEngine(); let o = AVAudioPlayerNode()
    if m.giris {
        let inp = e.inputNode   // girişe dokunmak mikrofonu açar: yalnız mik_ac'ta
        if m.vp {
            do {
                try inp.setVoiceProcessingEnabled(true)
                inp.voiceProcessingOtherAudioDuckingConfiguration = AVAudioVoiceProcessingOtherAudioDuckingConfiguration(enableAdvancedDucking: false, duckingLevel: .min)
            } catch { m.vp = false; hataBildir("vpio", "açılamadı (\(error.localizedDescription)) — VPIO'suz sürüyor") }
        }
    }
    e.attach(o); let mix = AVAudioMixerNode(); e.attach(mix)
    e.connect(o, to: mix, format: OYN_FMT); e.connect(mix, to: e.outputNode, format: CIK_FMT)
    if m.giris {
        let inp = e.inputNode; let fmt = inp.outputFormat(forBus: 0)
        guard fmt.sampleRate > 0, fmt.channelCount > 0,
              let monoFmt = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: fmt.sampleRate, channels: 1, interleaved: false),
              let donus = AVAudioConverter(from: monoFmt, to: MIK_FMT) else {
            hataBildir("motor", "giriş aygıtı yok ya da biçimi okunamadı"); mikAcik = false; return
        }
        inp.installTap(onBus: 0, bufferSize: 1024, format: fmt) { buf, zaman in   // ses iş parçacığı: yalnız dönüştür, öbekleme ana sırada
            guard let ch = buf.floatChannelData else { return }
            let n = Int(buf.frameLength); guard n > 0, let mb = AVAudioPCMBuffer(pcmFormat: monoFmt, frameCapacity: AVAudioFrameCount(n)) else { return }
            mb.frameLength = AVAudioFrameCount(n); memcpy(mb.floatChannelData![0], ch[0], n * 4)
            guard let cb = AVAudioPCMBuffer(pcmFormat: MIK_FMT, frameCapacity: AVAudioFrameCount(Double(n) * 16000 / fmt.sampleRate) + 64) else { return }
            var verildi = false; var hata: NSError?
            donus.convert(to: cb, error: &hata) { _, d in
                if verildi { d.pointee = .noDataNow; return nil }
                verildi = true; d.pointee = .haveData; return mb
            }
            guard hata == nil, cb.frameLength > 0 else { return }
            let x = Array(UnsafeBufferPointer(start: cb.int16ChannelData![0], count: Int(cb.frameLength)))
            let t = zaman.isHostTimeValid ? hostSn(zaman.hostTime) : simdi()
            ana.async { if motor === m { mikEkle(x, t, kusak: m.kusak) } }
        }
    }
    e.prepare()
    do { try e.start() } catch {
        if m.vp {   // VPIO'lu motor başlamadıysa VPIO'suz bir kez daha
            hataBildir("vpio", "motor VPIO ile başlamadı (\(error.localizedDescription)) — VPIO'suz deneniyor")
            istenenVpio = false; motorKur(); return
        }
        hataBildir("motor", "başlamadı (\(error.localizedDescription))"); mikAcik = false; return
    }
    m.eng = e; m.oyn = o; motor = m
    o.play()
    if sessizDugum { sessizCal() }
    gunluk("motor kuruldu: mikrofon \(m.giris), vpio \(m.vp), çıkış \(aygit.cikis), giriş \(aygit.giris)")
}
func motorGerekli() -> Bool { mikAcik || akis != nil || sessizDugum }
func motorGuncelle() {   // istenen durum değiştiyse motoru yeniden kurar (giriş ya da VPIO değişimi yeniden kurulum ister)
    if let m = motor {
        if m.giris != mikAcik || m.vp != etkinVpio() {
            if motorGerekli() { motorKur() } else { motorDurdur(kesildiGonder: true) }
        } else if !kuru, let e = m.eng, !e.isRunning, motorGerekli() { motorKur() }
    } else if motorGerekli() { motorKur() }
}
func hepsiniKapat() { mikAcik = false; sessizDugum = false; istenenVpio = false; motorDurdur(kesildiGonder: false) }

// --- çalma: gelen Int16 mono (sr) → 48 kHz Float32 → çalıcı düğüm ---
final class Akis {
    let id: String; let sr: Double; let no: Int
    var donus: AVAudioConverter? = nil; var girisFmt: AVAudioFormat? = nil
    var bekleyen = 0, verildi = 0, bitirildi = false, basladi = false, baslaT = 0.0
    init(id: String, sr: Double, no: Int) { self.id = id; self.sr = sr; self.no = no }
}
var akis: Akis? = nil, akisNo = 0
var baslaZamanlayici: DispatchSourceTimer? = nil

func sessizCal() {   // D yolu: dış çalıcı kullanılırken motorda sessiz düğüm (VPIO başvurusu)
    guard let o = motor?.oyn, akis == nil, let b = AVAudioPCMBuffer(pcmFormat: OYN_FMT, frameCapacity: 4800) else { return }
    b.frameLength = 4800; o.scheduleBuffer(b, at: nil, options: .loops, completionHandler: nil); if !o.isPlaying { o.play() }
}
func akisKes(_ a: Akis, olay: Bool) {
    if akis === a { akis = nil }
    baslaZamanlayici?.cancel(); baslaZamanlayici = nil
    if !kuru, let o = motor?.oyn { o.stop(); o.play(); if sessizDugum { sessizCal() } }
    if olay { gonder(["t": "kesildi", "id": a.id]) }
}
func bittiMi(_ a: Akis) {
    guard akis === a, a.bitirildi else { return }
    if a.verildi == 0 { akis = nil; gonder(["t": "cal_bitti", "id": a.id]); return }
    if kuru {
        guard a.basladi else { return }
        let kalan = a.baslaT + Double(a.verildi) / a.sr - simdi()
        ana.asyncAfter(deadline: .now() + max(0, kalan)) { if akis === a { akis = nil; gonder(["t": "cal_bitti", "id": a.id]); if sessizDugum { sessizCal() } } }
        return
    }
    if a.bekleyen == 0 && a.basladi { akis = nil; gonder(["t": "cal_bitti", "id": a.id]); if sessizDugum { sessizCal() } }
}
func baslangicIzle(_ a: Akis) {   // ilk örneğin hoparlöre çıktığı an (ses saati): çalıcının örnek zamanı 0'ın ana makine saati + çıkış gecikmesi
    baslaZamanlayici?.cancel()
    let z = DispatchSource.makeTimerSource(queue: ana); z.schedule(deadline: .now(), repeating: 0.005)
    let bas = simdi()
    z.setEventHandler {
        guard akis === a, !a.basladi else { z.cancel(); return }
        var t: Double? = nil
        if kuru { t = bas + 0.05 }
        else if let o = motor?.oyn, let e = motor?.eng, let lt = o.lastRenderTime, lt.isHostTimeValid, let pt = o.playerTime(forNodeTime: lt), pt.sampleTime >= 0 {
            t = hostSn(lt.hostTime) - Double(pt.sampleTime) / pt.sampleRate + e.outputNode.presentationLatency
        } else if simdi() - bas > 2 { t = simdi() }   // örnek zamanı okunamadı: yaklaşık
        guard let tt = t else { return }
        a.basladi = true; a.baslaT = tt; z.cancel(); if baslaZamanlayici === z { baslaZamanlayici = nil }
        gonder(["t": "cal_basladi", "id": a.id, "ts": tt, "duvar": duvar(tt)])
        bittiMi(a)
    }
    z.resume(); baslaZamanlayici = z
}
func sesEkle(_ a: Akis, _ veri: Data) {
    let n = veri.count / 2; guard n > 0 else { return }
    if kuru { a.verildi += n; if a.verildi == n { baslangicIzle(a) }; return }
    guard let o = motor?.oyn else { return }
    if a.donus == nil {
        a.girisFmt = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: a.sr, channels: 1, interleaved: true)
        a.donus = a.girisFmt.flatMap { AVAudioConverter(from: $0, to: OYN_FMT) }
    }
    guard let gf = a.girisFmt, let d = a.donus, let gb = AVAudioPCMBuffer(pcmFormat: gf, frameCapacity: AVAudioFrameCount(n)),
          let cb = AVAudioPCMBuffer(pcmFormat: OYN_FMT, frameCapacity: AVAudioFrameCount(Double(n) * 48000 / a.sr) + 512) else { return }
    gb.frameLength = AVAudioFrameCount(n)
    veri.withUnsafeBytes { _ = memcpy(gb.int16ChannelData![0], $0.baseAddress!, n * 2) }
    var verildi = false; var hata: NSError?
    d.convert(to: cb, error: &hata) { _, dd in
        if verildi { dd.pointee = .noDataNow; return nil }
        verildi = true; dd.pointee = .haveData; return gb
    }
    guard hata == nil, cb.frameLength > 0 else { return }
    let ilk = a.verildi == 0
    a.verildi += n; a.bekleyen += 1
    o.scheduleBuffer(cb, completionCallbackType: .dataPlayedBack) { _ in ana.async { if akis === a { a.bekleyen -= 1; bittiMi(a) } } }
    if !o.isPlaying { o.play() }
    if ilk { baslangicIzle(a) }
}

// --- komutlar ---
func durumGovde(_ t: String) -> [String: Any] {
    var g: [String: Any] = ["t": t, "vpio": motor?.vp ?? false, "mik": mikAcik, "cal": akis != nil, "surum": SURUM]
    if t == "durum" {
        g["aygit"] = kuru ? ["cikis": "kuru", "giris": "kuru", "kulaklik": kuruKulaklik] as [String: Any] : ["cikis": aygit.cikis, "giris": aygit.giris, "kulaklik": aygit.kulaklik]
        g["hata"] = sonHata ?? NSNull(); g["kuru"] = kuru
        if let tm = toplantiMik { g["toplanti_mik"] = tm }
    }
    return g
}
func mikIzinliyse(_ devam: @escaping () -> Void) {
    if kuru { devam(); return }
    switch AVCaptureDevice.authorizationStatus(for: .audio) {
    case .authorized: devam()
    case .notDetermined: AVCaptureDevice.requestAccess(for: .audio) { v in ana.async { if v { devam() } else { mikAcik = false; hataBildir("izin", "mikrofon izni verilmedi") } } }
    default: mikAcik = false; hataBildir("izin", "mikrofon izni yok — Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon → Suflor Konus")
    }
}
func komut(_ o: [String: Any]) {
    let t = o["t"] as? String ?? ""
    switch t {
    case "mik_ac":
        istenenVpio = (o["vpio"] as? Bool) ?? false; mikAcik = true; mikKusak += 1; mikTampon.removeAll()
        let k = mikKusak
        mikIzinliyse { if mikAcik && k == mikKusak { motorGuncelle(); if let m = motor, m.giris { m.kusak = mikKusak } } }
    case "mik_kapat":
        mikAcik = false; mikKusak += 1; mikTampon.removeAll(); motorGuncelle()   // giriş kapanınca motor girişsiz yeniden kurulur ya da durur: VPIO açık kalmaz (diğer mikrofonlar kısılmasın)
    case "cal_ac":
        guard let id = o["id"] as? String, let sr = (o["sr"] as? NSNumber)?.doubleValue, sr >= 8000, sr <= 192000 else { hataBildir("komut", "cal_ac: id ya da sr eksik/geçersiz"); return }
        if let eski = akis { akisKes(eski, olay: true) }
        akisNo += 1; let a = Akis(id: id, sr: sr, no: akisNo); akis = a
        motorGuncelle()
        if akis === a, !kuru, let o = motor?.oyn { o.stop(); o.play() }   // örnek zamanı 0 = bu akışın ilk örneği
    case "ses":
        guard let a = akis, (o["id"] as? String) == a.id, !a.bitirildi else { return }   // kesilmiş/eski akışın verisi sessizce atılır
        guard let s = o["b64"] as? String, let veri = Data(base64Encoded: s) else { hataBildir("komut", "ses: b64 çözülemedi"); return }
        sesEkle(a, veri)
    case "cal_bitir":
        guard let a = akis, (o["id"] as? String) == a.id else { return }
        a.bitirildi = true; bittiMi(a)
    case "kes":
        if let a = akis { akisKes(a, olay: true) }
    case "durum":
        gonder(durumGovde("durum"))
    case "sessiz_dugum":
        sessizDugum = (o["ac"] as? Bool) ?? false; motorGuncelle()
        if sessizDugum { sessizCal() } else if akis == nil, !kuru, let o = motor?.oyn { o.stop(); o.play() }
    default:
        hataBildir("komut", "bilinmeyen komut: \(t.prefix(40))")
    }
}

// --- soket sunucusu ---
func satirlar(_ b: Baglanti) {
    var bas = 0
    while let i = b.tampon[bas...].firstIndex(of: 10) {
        let satir = Data(b.tampon[bas..<i]); bas = i + 1
        if satir.isEmpty { continue }
        guard let o = (try? JSONSerialization.jsonObject(with: satir)) as? [String: Any] else {
            if !b.kimlikli { gonderB(b, ["t": "hata", "neden": "anahtar", "ayrinti": "ilk satır anahtar değil"]); kapat(b, neden: "anahtar"); return }
            hataBildir("komut", "JSON çözülemedi"); continue
        }
        if !b.kimlikli {
            let k = anahtarOku()
            guard (o["t"] as? String) == "anahtar", let gelen = o["k"] as? String, esit(gelen, k) else {
                gunluk("yanlış anahtar — bağlantı kapatıldı")
                gonderB(b, ["t": "hata", "neden": "anahtar", "ayrinti": "anahtar tutmadı"]); kapat(b, neden: "anahtar"); return
            }
            b.kimlikli = true; bekleyenler.removeAll { $0 === b }
            if let eski = istemci { gunluk("yeni aktarıcı bağlantısı — eskisi kapanıyor"); istemci = nil; kapat(eski, neden: "yeni bağlantı"); hepsiniKapat() }
            istemci = b; sonBaglanti = uyanik(); gunluk("aktarıcı bağlandı")
            gonderB(b, durumGovde("nabiz"))   // kabul işareti: anahtar tuttu
            continue
        }
        komut(o)
        if b.bitti { return }
    }
    if bas > 0 { b.tampon.removeFirst(bas) }
    if b.tampon.count > 8 << 20 { hataBildir("komut", "satır çok uzun"); kapat(b, neden: "satır çok uzun") }
}
func kabul(_ dinle: Int32) {
    let fd = accept(dinle, nil, nil); guard fd >= 0 else { return }
    var bir: Int32 = 1; setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &bir, socklen_t(MemoryLayout<Int32>.size))
    var zt = timeval(tv_sec: 2, tv_usec: 0); setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &zt, socklen_t(MemoryLayout<timeval>.size))
    let b = Baglanti(fd); bekleyenler.append(b)
    let k = DispatchSource.makeReadSource(fileDescriptor: fd, queue: ana)
    let boy = 1 << 16; var okuma = [UInt8](repeating: 0, count: boy)
    k.setEventHandler {
        let n = read(fd, &okuma, boy)
        if n <= 0 { kapat(b, neden: n == 0 ? "istemci kapattı" : "okuma hatası"); return }
        b.tampon.append(contentsOf: okuma[0..<n]); satirlar(b)
    }
    k.setCancelHandler { yazKuyruk.async { b.kilit.lock(); b._kapali = true; b.kilit.unlock(); close(fd) } }   // bekleyen yazımlardan sonra kapanır
    b.kaynak = k; k.resume()
    ana.asyncAfter(deadline: .now() + 5) { if !b.kimlikli && !b.bitti { gonderB(b, ["t": "hata", "neden": "anahtar", "ayrinti": "zaman aşımı"]); kapat(b, neden: "anahtar zaman aşımı") } }
}
func soketKur() -> Int32 {
    try? FileManager.default.createDirectory(atPath: uygulama, withIntermediateDirectories: true)
    var adr = sockaddr_un(); adr.sun_family = sa_family_t(AF_UNIX)
    let yolB = Array(soketYol.utf8)
    guard yolB.count < MemoryLayout.size(ofValue: adr.sun_path) else { gunluk("soket yolu çok uzun: \(soketYol)"); exit(2) }
    withUnsafeMutableBytes(of: &adr.sun_path) { p in for (i, c) in yolB.enumerated() { p[i] = c }; p[yolB.count] = 0 }
    let uz = socklen_t(MemoryLayout<sockaddr_un>.size)
    if FileManager.default.fileExists(atPath: soketYol) {   // başka bir kopya dinliyorsa çık; bayat dosyaysa sil
        let s = socket(AF_UNIX, SOCK_STREAM, 0)
        let r = withUnsafePointer(to: &adr) { $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(s, $0, uz) } }
        close(s)
        if r == 0 { gunluk("başka bir kopya zaten dinliyor — çıkılıyor"); exit(0) }
        unlink(soketYol)
    }
    let fd = socket(AF_UNIX, SOCK_STREAM, 0)
    let eskiMaske = umask(0o177)
    let r = withUnsafePointer(to: &adr) { $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, uz) } }
    umask(eskiMaske)
    guard r == 0 else { gunluk("soket bağlanamadı (\(errno))"); exit(2) }
    chmod(soketYol, 0o600)
    guard listen(fd, 4) == 0 else { gunluk("soket dinlenemedi (\(errno))"); exit(2) }
    return fd
}

// --- aygıt değişimi: varsayılan giriş/çıkış ve yerleşik çıkışın veri kaynağı (kulaklık girişi) ---
var aygitNo = 0, kaynakDinlenen: AudioObjectID = 0, sonMotorUyari = 0.0
let kaynakDinleyici: AudioObjectPropertyListenerBlock = { _, _ in aygitDegisti() }
func kaynakDinle() {
    var adr = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyDataSource, mScope: kAudioObjectPropertyScopeOutput, mElement: kAudioObjectPropertyElementMain)
    if kaynakDinlenen != 0 { AudioObjectRemovePropertyListenerBlock(kaynakDinlenen, &adr, ana, kaynakDinleyici) }
    kaynakDinlenen = aygit.cikisID
    if kaynakDinlenen != 0 { AudioObjectAddPropertyListenerBlock(kaynakDinlenen, &adr, ana, kaynakDinleyici) }
}
func aygitDegisti() {   // 0,4 sn yatıştırma: tak-çıkar sırasında birkaç bildirim gelir
    aygitNo += 1; let no = aygitNo
    ana.asyncAfter(deadline: .now() + 0.4) {
        guard no == aygitNo else { return }
        let yeni = aygitOku(); let eski = aygit
        if yeni == eski { if let m = motor, let e = m.eng, !e.isRunning, motorGerekli() { gunluk("motor durmuş — yeniden kuruluyor"); motorKur() }; return }
        aygit = yeni; if yeni.cikisID != eski.cikisID { kaynakDinle() }
        gunluk("aygıt değişti: çıkış \(yeni.cikis), giriş \(yeni.giris), kulaklık \(yeni.kulaklik)")
        gonder(["t": "aygit_degisti", "cikis": yeni.cikis, "giris": yeni.giris, "kulaklik": yeni.kulaklik])
        if motor != nil { if motorGerekli() { motorKur() } else { motorDurdur(kesildiGonder: true) } }   // yeni aygıtta yeniden kur (kulaklıkta VPIO kapalı)
    }
}
func aygitDinle() {
    aygit = aygitOku(); kaynakDinle()
    for s in [kAudioHardwarePropertyDefaultOutputDevice, kAudioHardwarePropertyDefaultInputDevice] {
        var adr = AudioObjectPropertyAddress(mSelector: s, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
        AudioObjectAddPropertyListenerBlock(SISTEM, &adr, ana) { _, _ in aygitDegisti() }
    }
    NotificationCenter.default.addObserver(forName: .AVAudioEngineConfigurationChange, object: nil, queue: nil) { _ in ana.async { aygitDegisti() } }
}

// --- toplantı kapatıcısı: toplantı uygulaması mikrofonu ≥ 1 sn tutarsa VPIO kapanır ---
func toplantiDegisti(_ yeni: String?) {
    let eski = toplantiMik; toplantiMik = yeni
    if let ad = yeni, eski == nil {
        let vpAcikti = motor?.vp ?? false
        if vpAcikti { motorKur() }   // etkinVpio() artık false
        gunluk("toplantı uygulaması mikrofonda: \(ad)\(vpAcikti ? " — VPIO kapatıldı" : "")")
        gonder(["t": "toplanti_mik", "uygulama": ad, "vpio_kapatildi": vpAcikti])
    } else if yeni == nil, eski != nil {
        gunluk("toplantı uygulaması mikrofonu bıraktı (VPIO, aktarıcı yeniden mik_ac{vpio:true} derse açılır)")
    }
}
func toplantiYokla() {
    guard !kuru, mikAcik || (motor?.vp ?? false) else { mikIlk.removeAll(); return }
    let t = uyanik(), simdiki = mikrofonluAileler()
    for a in simdiki where mikIlk[a] == nil { mikIlk[a] = t }
    for a in Array(mikIlk.keys) where !simdiki.contains(a) { mikIlk[a] = nil }
    if !simdiki.isEmpty { mikSonGorulme = t }
    if toplantiMik == nil, let e = mikIlk.first(where: { t - $0.value >= 1.0 }) { toplantiDegisti(e.key) }
    else if toplantiMik != nil, simdiki.isEmpty, t - mikSonGorulme >= 3 { toplantiDegisti(nil) }
}

// --- başlangıç ---
signal(SIGPIPE, SIG_IGN)
let dinleFd = soketKur()
let dinleKaynak = DispatchSource.makeReadSource(fileDescriptor: dinleFd, queue: ana)
dinleKaynak.setEventHandler { kabul(dinleFd) }; dinleKaynak.resume()
func cikis(_ neden: String) -> Never {
    gunluk(neden); if let m = motor, let e = m.eng { if m.giris { e.inputNode.removeTap(onBus: 0) }; e.stop() }
    unlink(soketYol); exit(0)
}
var sinyaller: [DispatchSourceSignal] = []
for s in [SIGTERM, SIGINT, SIGUSR1, SIGUSR2] {
    signal(s, SIG_IGN)
    let k = DispatchSource.makeSignalSource(signal: s, queue: ana)
    k.setEventHandler {
        switch s {
        case SIGUSR1 where kuru:   // kuru: aygıt değişimi taklidi (kulaklık takıldı/çıktı)
            kuruKulaklik.toggle()
            gonder(["t": "aygit_degisti", "cikis": "kuru", "giris": "kuru", "kulaklik": kuruKulaklik])
            if motor != nil { if motorGerekli() { motorKur() } else { motorDurdur(kesildiGonder: true) } }
        case SIGUSR2 where kuru:   // kuru: toplantı uygulaması mikrofonu aldı / bıraktı
            toplantiDegisti(toplantiMik == nil ? "Teams" : nil)
        case SIGUSR1, SIGUSR2: break
        default: cikis("sinyal \(s) — kapanıyor")
        }
    }
    k.resume(); sinyaller.append(k)
}
if !kuru { aygitDinle() }
_ = anahtarOku()   // anahtar dosyası yoksa şimdi üretilir (aktarıcı okur)
let nabizZ = DispatchSource.makeTimerSource(queue: ana); nabizZ.schedule(deadline: .now() + nabizSn, repeating: nabizSn)
nabizZ.setEventHandler { if istemci != nil { gonder(durumGovde("nabiz")) } }; nabizZ.resume()
let bekciZ = DispatchSource.makeTimerSource(queue: ana); bekciZ.schedule(deadline: .now() + 0.25, repeating: 0.25)
bekciZ.setEventHandler {
    toplantiYokla()
    if istemci != nil { sonBaglanti = uyanik() }
    else if uyanik() - sonBaglanti >= bostaSn { cikis("\(Int(bostaSn)) sn aktarıcı bağlantısı yok — kapanıyor") }
    if let m = motor, !motorGerekli() {   // yalnız çıkışlı motor boşta 30 sn sonra durur (giriş açık kalmaz: motorGuncelle hemen kapatır)
        if m.bosSince == nil { m.bosSince = uyanik() } else if uyanik() - m.bosSince! >= 30 { motorDurdur(kesildiGonder: false) }
    } else { motor?.bosSince = nil }
}
bekciZ.resume()
gunluk("başladı v\(SURUM)\(kuru ? " (kuru)" : "") · \(soketYol)")
dispatchMain()
