// Suflor.me — kesintisiz ses çalıcı (v0.32.2). Piper'ın ürettiği cümleler tek akışta çalınır: her cümleye ayrı afplay açmak cümle başına
// ~0,75 sn ek boşluk veriyordu (13 Ekim ölçümü), duraklama süresi kodun elinde değildi. Kullanım: suflor-oynat <örnekleme hızı>
// stdin: ham 16 bit tek kanal PCM (parça parça gelir); stdin kapanınca kalan ses bitince çıkar. Sonlandırılınca (SIGTERM) ses hemen durur.
// Yalnız çıkış aygıtına çalar; ağ yok, izin gerekmez.
import AVFoundation
import Foundation

let sr = Double(CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "22050") ?? 22050
let motor = AVAudioEngine()
let oyuncu = AVAudioPlayerNode()
guard let bicim = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sr, channels: 1, interleaved: false) else { exit(2) }
motor.attach(oyuncu)
motor.connect(oyuncu, to: motor.mainMixerNode, format: bicim)
do { try motor.start() } catch { FileHandle.standardError.write("motor açılamadı\n".data(using: .utf8)!); exit(3) }
oyuncu.play()

let bekleyen = DispatchGroup()
let giris = FileHandle.standardInput
var artik = Data()
while true {
    let veri = giris.availableData  // parça gelene kadar bekler; boş = stdin kapandı
    if veri.isEmpty { break }
    artik.append(veri)
    let n = artik.count / 2
    if n == 0 { continue }
    guard let tampon = AVAudioPCMBuffer(pcmFormat: bicim, frameCapacity: AVAudioFrameCount(n)) else { exit(4) }
    tampon.frameLength = AVAudioFrameCount(n)
    let hedef = tampon.floatChannelData![0]
    artik.withUnsafeBytes { (p: UnsafeRawBufferPointer) in
        let s = p.bindMemory(to: Int16.self)
        for i in 0..<n { hedef[i] = Float(Int16(littleEndian: s[i])) / 32768.0 }
    }
    artik = artik.count % 2 == 1 ? artik.suffix(1) : Data()
    bekleyen.enter()
    oyuncu.scheduleBuffer(tampon, completionCallbackType: .dataPlayedBack) { _ in bekleyen.leave() }
}
bekleyen.wait()
motor.stop()
exit(0)
