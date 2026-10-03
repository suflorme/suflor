// Suflor.me v0.13.0 — yerel ses yardımcısı ("Suflor Ses.app"). Toplantı uygulamasının çıkardığı sesi (karşı tarafın sesi) Core
// Audio process tap ile alır, 16 kHz tek kanal Int16'ya indirip aktarıcıya POST /ses-yerel ile verir. Option + Shift + W gerekmez.
// Mikrofonu ALMAZ: o eklentide kalır (toplantının sessiz bilgisi + tarayıcının yankı engellemesi). Apple ses işleme
// (VoiceProcessingIO) kullanılmaz: diğer sesleri ~9 dB kısıyor (4 Ekim ön denemesi). Ses diske yazılmaz; ağ yalnız 127.0.0.1.
// Toplantı anlama iki sinyalle: (1) aktarıcının nabız yanıtı — eklenti toplantıda ("toplanti": true) ve hangi tarayıcıda
// ("tarayici": User-Agent'tan) — tarayıcı ailesinin süreçlerinden tap; (2) 1 sn'de bir Core Audio süreç listesi (izin gerekmez) —
// bilinen bir toplantı uygulaması mikrofonu ≥ 2 sn kullanıyorsa. 4 Ekim denemesi: Chrome mikrofonu açtığı halde macOS süreç
// listesinde hiçbir süreç "mikrofon kullanıyor" görünmedi — (2) tek başına yetmez. İkisi de ≥ 8 sn kaybolunca durur. Yalnız bu macOS
// hesabının süreçleri (iki hesap aynı anda açık olabilir). Sınır: tarayıcıda sekme ayrımı yok (aynı tarayıcıdaki başka sekmenin sesi
// de girer).
// Aktarıcı başlatır: open -g -a "Suflor Ses.app" --args --port P --anahtar <dosya>  (anahtar komut satırında değil, 0600 dosyada:
// diğer macOS hesabı ps ile görmesin). 5 sn'de bir nabız; aktarıcıya 5 dk ulaşılamazsa kapanır (aktarıcı yeniden açar).
// --izin: izin penceresini kurulumda çıkarmak için kısa bir tap kurar ve çıkar (aktarici-kur.command).
// İzin: Info.plist NSAudioCaptureUsageDescription → Sistem Ayarları → Gizlilik ve Güvenlik → Ekran ve Sistem Sesi Kaydı (yalnız sistem sesi).
import Foundation
import CoreAudio
import AudioToolbox
import AVFoundation

let SURUM = "0.13.0"
var arg: [String: String] = [:]
var izinKipi = false
do {
    let a = CommandLine.arguments; var i = 1
    while i < a.count {
        if a[i] == "--izin" { izinKipi = true; i += 1 }
        else if a[i].hasPrefix("--"), i + 1 < a.count { arg[String(a[i].dropFirst(2))] = a[i + 1]; i += 2 } else { i += 1 }
    }
}
let port = Int(arg["port"] ?? "") ?? 8765
let anahtar: String = {
    guard let y = arg["anahtar"], let s = try? String(contentsOfFile: y, encoding: .utf8) else { return "" }
    return s.trimmingCharacters(in: .whitespacesAndNewlines)
}()
func gunluk(_ s: String) { FileHandle.standardError.write(("Suflor Ses: " + s + "\n").data(using: .utf8)!) }

// --- Core Audio yardımcıları ---
func ozellik<T>(_ nesne: AudioObjectID, _ secici: AudioObjectPropertySelector, _ bos: T) -> T? {
    var adr = AudioObjectPropertyAddress(mSelector: secici, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
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
func sahibi(_ pid: pid_t) -> uid_t? {
    var bilgi = kinfo_proc(); var boyut = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard sysctl(&mib, 4, &bilgi, &boyut, nil, 0) == 0, boyut > 0 else { return nil }
    return bilgi.kp_eproc.e_ucred.cr_uid
}
struct Surec { let id: AudioObjectID; let pid: pid_t; let bundle: String; let giris: Bool; let cikis: Bool }
let benimUid = getuid(), benimPid = getpid()
var uidOnbellek: [pid_t: Bool] = [:]
func surecler() -> [Surec] {
    if uidOnbellek.count > 2000 { uidOnbellek.removeAll() }
    return dizi(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyProcessObjectList).compactMap { id in
        let pid = ozellik(id, kAudioProcessPropertyPID, pid_t(0)) ?? 0
        guard pid > 0, pid != benimPid else { return nil }
        let benim = uidOnbellek[pid] ?? { let b = sahibi(pid) == benimUid; uidOnbellek[pid] = b; return b }()
        guard benim else { return nil }
        return Surec(id: id, pid: pid, bundle: metin(id, kAudioProcessPropertyBundleID) ?? "",
                     giris: (ozellik(id, kAudioProcessPropertyIsRunningInput, UInt32(0)) ?? 0) != 0,
                     cikis: (ozellik(id, kAudioProcessPropertyIsRunningOutput, UInt32(0)) ?? 0) != 0)
    }
}
// Toplantı uygulaması aileleri: mikrofonu tutan süreç bu öneklerden biriyle başlıyorsa, aynı önekli tüm süreçlerin sesi alınır
// (tarayıcıda ses ve mikrofon yardımcı süreçlerde: Chrome → com.google.Chrome.helper, Safari → com.apple.WebKit.GPU).
let AILELER: [(onek: String, ad: String)] = [
    ("com.google.Chrome", "Chrome"), ("com.microsoft.edgemac", "Edge"), ("com.brave.Browser", "Brave"), ("company.thebrowser", "Arc"),
    ("com.apple.WebKit", "Safari"), ("com.apple.Safari", "Safari"), ("com.microsoft.teams", "Teams"), ("us.zoom", "Zoom"),
    ("com.tinyspeck.slackmacgap", "Slack"), ("com.apple.FaceTime", "FaceTime"), ("com.cisco.webex", "Webex"), ("Cisco-Systems.Spark", "Webex")]
func aile(_ bundle: String) -> (onek: String, ad: String)? { AILELER.first { bundle.hasPrefix($0.onek) } }
func varsayilanCikis() -> AudioObjectID? { ozellik(AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyDefaultSystemOutputDevice, AudioObjectID(0)) }

// --- zaman ---
var tb = mach_timebase_info_data_t(); mach_timebase_info(&tb)
func hostSn(_ h: UInt64) -> Double { Double(h) * Double(tb.numer) / Double(tb.denom) / 1e9 }

// --- tap: süreçlerin sesi → özel toplu aygıt → IOProc → halka (tek kanal Float, tap hızında) ---
final class Halka { var ornek: [Float] = []; var ilkHost: UInt64 = 0 }
let halka = Halka(); let kilit = NSLock()
var tapID = AudioObjectID(kAudioObjectUnknown), topluID = AudioObjectID(kAudioObjectUnknown)
var ioProc: AudioDeviceIOProcID? = nil
var tapHz = 48000.0, tapSurecler: [AudioObjectID] = [], tapCikis: AudioObjectID = 0
func tapDurdur() {
    if let p = ioProc { AudioDeviceStop(topluID, p); AudioDeviceDestroyIOProcID(topluID, p); ioProc = nil }
    if topluID != kAudioObjectUnknown { AudioHardwareDestroyAggregateDevice(topluID); topluID = AudioObjectID(kAudioObjectUnknown) }
    if tapID != kAudioObjectUnknown { AudioHardwareDestroyProcessTap(tapID); tapID = AudioObjectID(kAudioObjectUnknown) }
    tapSurecler = []
    kilit.lock(); halka.ornek.removeAll(keepingCapacity: true); kilit.unlock()
}
func tapKur(_ hedef: [AudioObjectID]?) -> String? {  // hedef nil: tüm sistem (yalnız --izin)
    tapDurdur()
    let tanim = hedef.map { CATapDescription(stereoMixdownOfProcesses: $0) } ?? CATapDescription(stereoGlobalTapButExcludeProcesses: [])
    tanim.uuid = UUID(); tanim.muteBehavior = .unmuted; tanim.isPrivate = true; tanim.name = "Suflor.me karşı ses"
    var r = AudioHardwareCreateProcessTap(tanim, &tapID)
    if r != noErr { tapID = AudioObjectID(kAudioObjectUnknown); return "tap kurulamadı (\(r))" }
    guard let cikisID = varsayilanCikis(), let cikisUID = metin(cikisID, kAudioDevicePropertyDeviceUID) else { tapDurdur(); return "çıkış aygıtı yok" }
    let tanimT: [String: Any] = [
        kAudioAggregateDeviceNameKey: "Suflor.me karşı ses", kAudioAggregateDeviceUIDKey: UUID().uuidString,
        kAudioAggregateDeviceMainSubDeviceKey: cikisUID, kAudioAggregateDeviceIsPrivateKey: true, kAudioAggregateDeviceIsStackedKey: false,
        kAudioAggregateDeviceTapAutoStartKey: true, kAudioAggregateDeviceSubDeviceListKey: [[kAudioSubDeviceUIDKey: cikisUID]],
        kAudioAggregateDeviceTapListKey: [[kAudioSubTapDriftCompensationKey: true, kAudioSubTapUIDKey: tanim.uuid.uuidString]]]
    r = AudioHardwareCreateAggregateDevice(tanimT as CFDictionary, &topluID)
    if r != noErr { topluID = AudioObjectID(kAudioObjectUnknown); tapDurdur(); return "toplu aygıt kurulamadı (\(r))" }
    var asbd = AudioStreamBasicDescription()
    var adr = AudioObjectPropertyAddress(mSelector: kAudioTapPropertyFormat, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var boyut = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
    AudioObjectGetPropertyData(tapID, &adr, 0, nil, &boyut, &asbd)
    guard asbd.mFormatFlags & kAudioFormatFlagIsFloat != 0, asbd.mBitsPerChannel == 32 else { tapDurdur(); return "beklenmeyen ses biçimi" }
    tapHz = asbd.mSampleRate > 0 ? asbd.mSampleRate : 48000
    var mono = [Float](repeating: 0, count: 8192)
    r = AudioDeviceCreateIOProcIDWithBlock(&ioProc, topluID, DispatchQueue(label: "suflor.tap", qos: .userInteractive)) { _, giris, girisZaman, _, _ in
        let abl = UnsafeMutableAudioBufferListPointer(UnsafeMutablePointer(mutating: giris))
        var kare = 0, kanalTop = 0
        for b in abl {
            guard let p = b.mData?.assumingMemoryBound(to: Float.self) else { continue }
            let kk = max(1, Int(b.mNumberChannels)), n = min(Int(b.mDataByteSize) / 4 / kk, mono.count)
            if kare == 0 { for i in 0..<n { mono[i] = 0 } }
            kare = max(kare, n); kanalTop += kk
            for i in 0..<n { var s: Float = 0; for c in 0..<kk { s += p[i * kk + c] }; mono[i] += s }
        }
        guard kare > 0, kanalTop > 0 else { return }
        let bol = 1 / Float(kanalTop)
        kilit.lock()
        if halka.ornek.isEmpty { halka.ilkHost = girisZaman.pointee.mHostTime }
        if halka.ornek.count < Int(tapHz) * 10 { for i in 0..<kare { halka.ornek.append(mono[i] * bol) } }  // gönderim takılırsa en çok 10 sn
        kilit.unlock()
    }
    if r != noErr { tapDurdur(); return "ses okuyucu kurulamadı (\(r))" }
    r = AudioDeviceStart(topluID, ioProc)
    if r != noErr { tapDurdur(); return "ses başlatılamadı (\(r)) — izin verilmedi olabilir" }
    tapSurecler = hedef ?? []; tapCikis = cikisID
    donusturucuKur()
    return nil
}

// --- 16 kHz tek kanal Int16'ya dönüştürme (AVAudioConverter, durumlu: parçalar arası kesintisiz) ---
let cikisBicim = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true)!
var girisBicim: AVAudioFormat? = nil, donusturucu: AVAudioConverter? = nil
func donusturucuKur() {
    girisBicim = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: tapHz, channels: 1, interleaved: false)
    donusturucu = girisBicim.flatMap { AVAudioConverter(from: $0, to: cikisBicim) }
}
func donustur(_ x: [Float]) -> Data? {
    guard let gb = girisBicim, let d = donusturucu, !x.isEmpty,
          let giris = AVAudioPCMBuffer(pcmFormat: gb, frameCapacity: AVAudioFrameCount(x.count)) else { return nil }
    giris.frameLength = AVAudioFrameCount(x.count)
    x.withUnsafeBufferPointer { _ = memcpy(giris.floatChannelData![0], $0.baseAddress!, x.count * 4) }
    guard let cikis = AVAudioPCMBuffer(pcmFormat: cikisBicim, frameCapacity: AVAudioFrameCount(Double(x.count) * 16000 / tapHz) + 256) else { return nil }
    var verildi = false; var hata: NSError?
    d.convert(to: cikis, error: &hata) { _, durum in
        if verildi { durum.pointee = .noDataNow; return nil }
        verildi = true; durum.pointee = .haveData; return giris
    }
    if hata != nil || cikis.frameLength == 0 { return nil }
    return Data(bytes: cikis.int16ChannelData![0], count: Int(cikis.frameLength) * 2)
}

// --- aktarıcıya gönderim ---
let oturum: URLSession = { let c = URLSessionConfiguration.ephemeral; c.timeoutIntervalForRequest = 5; c.connectionProxyDictionary = [:]; return URLSession(configuration: c) }()
var sonUlasma = Date(), ulasilamadi = 0
func gonder(_ govde: [String: Any], _ tamam: (([String: Any]?) -> Void)? = nil) {
    var r = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/ses-yerel")!)
    r.httpMethod = "POST"; r.setValue("application/json", forHTTPHeaderField: "Content-Type"); r.setValue(anahtar, forHTTPHeaderField: "X-Suflor-Anahtar")
    r.httpBody = try? JSONSerialization.data(withJSONObject: govde)
    oturum.dataTask(with: r) { veri, yanit, _ in
        let ok = (yanit as? HTTPURLResponse)?.statusCode == 200
        let j = ok ? veri.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] } : nil
        DispatchQueue.main.async { if ok { sonUlasma = Date() } else { ulasilamadi += 1 }; tamam?(j) }
    }.resume()
}

// --- durum makinesi (1 sn) ---
var micIlk: [String: Date] = [:]       // aile öneki → mikrofonu kesintisiz kullanmaya başladığı an
var micSon: [String: Date] = [:]       // aile öneki → mikrofonu son kullandığı an
var aktif: (onek: String, ad: String)? = nil
var aktarıcıToplanti = Date.distantPast, tarayiciIpucu = ""   // aktarıcının son "toplantı var" yanıtı + tarayıcı adı
let TARAYICILAR = ["Chrome", "Edge", "Brave", "Arc", "Safari"]
func tarayiciAilesi(_ ss: [Surec]) -> (onek: String, ad: String)? {
    // ipucu (User-Agent: Brave kendini Chrome diye tanıtır) önce; sesi çalan tarayıcı ailesi öne geçer, yoksa süreci olan
    let adaylar = AILELER.filter { TARAYICILAR.contains($0.ad) }
    let sirali = adaylar.filter { $0.ad == tarayiciIpucu } + adaylar.filter { $0.ad != tarayiciIpucu }
    return sirali.first { a in ss.contains { $0.bundle.hasPrefix(a.onek) && $0.cikis } } ?? sirali.first { a in ss.contains { $0.bundle.hasPrefix(a.onek) } }
}
var sonKurma = Date.distantPast, sonHata: String? = nil, tepe: Int16 = 0
func adim() {
    let ss = surecler(), simdi = Date()
    var micAileler = Set<String>()
    for s in ss where s.giris { if let a = aile(s.bundle) { micAileler.insert(a.onek) } }
    for a in micAileler { micSon[a] = simdi; if micIlk[a] == nil { micIlk[a] = simdi } }
    for a in micIlk.keys where !micAileler.contains(a) { micIlk[a] = nil }
    let aktarıcıDiyor = simdi.timeIntervalSince(aktarıcıToplanti) < 8
    if let ak = aktif {
        let tarayiciMi = TARAYICILAR.contains(ak.ad)
        if simdi.timeIntervalSince(micSon[ak.onek] ?? .distantPast) >= 8 && !(tarayiciMi && aktarıcıDiyor) {   // toplantı bitti
            tapDurdur(); aktif = nil; gunluk("durdu (\(ak.ad))"); return
        }
        let hedef = ss.filter { $0.bundle.hasPrefix(ak.onek) }.map { $0.id }.sorted()
        let cikis = varsayilanCikis() ?? 0
        if (Set(hedef) != Set(tapSurecler) && !hedef.isEmpty || cikis != tapCikis || ioProc == nil) && simdi.timeIntervalSince(sonKurma) >= 3 {
            sonKurma = simdi; sonHata = tapKur(hedef)
            if let h = sonHata { gunluk("yeniden kurulamadı: \(h)") }
        }
        return
    }
    // mikrofonu ≥ 2 sn kullanan ilk toplantı uygulaması; yoksa aktarıcı "toplantı var" diyorsa tarayıcı ailesi
    guard simdi.timeIntervalSince(sonKurma) >= 3 else { return }
    var secilen: (onek: String, ad: String)? = nil
    if let (onek, bas) = micIlk.min(by: { $0.value < $1.value }), simdi.timeIntervalSince(bas) >= 2 { secilen = AILELER.first { $0.onek == onek } }
    if secilen == nil, aktarıcıDiyor { secilen = tarayiciAilesi(ss) }
    guard let a = secilen else { return }
    let hedef = ss.filter { $0.bundle.hasPrefix(a.onek) }.map { $0.id }.sorted()
    guard !hedef.isEmpty else { return }
    sonKurma = simdi
    sonHata = tapKur(hedef)
    if let h = sonHata { gunluk("\(a.ad): \(h)") } else { aktif = a; gunluk("dinliyor: \(a.ad) (\(hedef.count) süreç, \(Int(tapHz)) Hz)") }
}
func paket() {   // 0,5 sn: halkadaki örnekleri 16 kHz'e indirip gönder
    kilit.lock(); let x = halka.ornek; let ilk = halka.ilkHost; halka.ornek.removeAll(keepingCapacity: true); kilit.unlock()
    guard let ak = aktif, !x.isEmpty, let pcm = donustur(x) else { return }
    let t = Date().timeIntervalSince1970 * 1000 - (hostSn(mach_absolute_time()) - hostSn(ilk)) * 1000
    pcm.withUnsafeBytes { b in for v in b.bindMemory(to: Int16.self) { let m = v == Int16.min ? Int16.max : abs(v); if m > tepe { tepe = m } } }
    gonder(["kanal": "karsi", "kaynak": "yerel", "uygulama": ak.ad, "t": Int64(t), "pcm": pcm.base64EncodedString()])
}
func nabiz() {   // 5 sn: durum + son 5 sn'nin tepe seviyesi (izin yoksa tap yalnız sıfır verir — aktarıcı uzun sürerse işaretler)
    var g: [String: Any] = ["nabiz": true, "surum": SURUM, "durum": aktif == nil ? "bekliyor" : "dinliyor", "tepe": Int(tepe)]
    if let a = aktif { g["uygulama"] = a.ad }
    if let h = sonHata { g["hata"] = h }
    tepe = 0
    gonder(g) { j in
        if (j?["toplanti"] as? Bool) == true { aktarıcıToplanti = Date() }
        if let t = j?["tarayici"] as? String { tarayiciIpucu = t }
    }
    if Date().timeIntervalSince(sonUlasma) > 300 { gunluk("aktarıcıya 5 dk ulaşılamadı — kapanıyor"); tapDurdur(); exit(0) }
}

if izinKipi {
    // kurulum: izin penceresi çıksın (yanıt beklenirken AudioDeviceStart bekleyebilir), sonra kapan
    let h = tapKur(nil); gunluk(h.map { "izin denemesi: \($0)" } ?? "izin denemesi: tap çalıştı")
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 2)); tapDurdur(); exit(h == nil ? 0 : 1)
}
signal(SIGTERM, SIG_IGN)
let sinyal = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
sinyal.setEventHandler { tapDurdur(); exit(0) }; sinyal.resume()
gunluk("başladı v\(SURUM) · port \(port)\(anahtar.isEmpty ? " · ANAHTAR YOK" : "")")
for (sn, is_) in [(1.0, adim), (0.5, paket), (5.0, nabiz)] as [(Double, () -> Void)] {
    let z = Timer(timeInterval: sn, repeats: true) { _ in is_() }; RunLoop.main.add(z, forMode: .common)
}
nabiz()
RunLoop.main.run()
