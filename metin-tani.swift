// Suflor.me — kanıt görüntüsündeki yazı (v0.36.0). Apple Vision metin tanıma; görüntü Mac'ten çıkmaz, ağ yok, izin gerekmez.
// Paylaşılan ekranda görünen ama söylenmeyen bilgi (slayt başlığı, tablo, rakam) toplantı defterine metin olarak girsin diye (S48).
// Kullanım: SuflorMetin <görüntü.png> → stdout JSON {"satirlar": [...], "diller": [...]} (yukarıdan aşağı, soldan sağa)
//           SuflorMetin --deneme-resim <çıktı.png> <metin> → deneme görüntüsü (test/kanit-metin.py)
import AppKit
import Foundation
import Vision

let a = CommandLine.arguments
func yaz(_ o: [String: Any]) {
    if let d = try? JSONSerialization.data(withJSONObject: o), let s = String(data: d, encoding: .utf8) { print(s) }
}
if a.count >= 4 && a[1] == "--deneme-resim" {
    let im = NSImage(size: NSSize(width: 1280, height: 720)); im.lockFocus()
    NSColor.white.setFill(); NSRect(x: 0, y: 0, width: 1280, height: 720).fill()
    let st: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 44), .foregroundColor: NSColor.black]
    (a[3] as NSString).draw(in: NSRect(x: 60, y: 60, width: 1160, height: 600), withAttributes: st); im.unlockFocus()
    guard let t = im.tiffRepresentation, let b = NSBitmapImageRep(data: t), let p = b.representation(using: .png, properties: [:]) else { exit(1) }
    try? p.write(to: URL(fileURLWithPath: a[2])); exit(0)
}
guard a.count >= 2, let im = NSImage(contentsOfFile: a[1]), let cg = im.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    yaz(["hata": "görüntü okunamadı"]); exit(1)
}
let r = VNRecognizeTextRequest()
r.recognitionLevel = .accurate; r.usesLanguageCorrection = true
let destek = (try? r.supportedRecognitionLanguages()) ?? []
let diller = ["tr-TR", "en-US"].filter { destek.contains($0) }
if !diller.isEmpty { r.recognitionLanguages = diller }
do { try VNImageRequestHandler(cgImage: cg, options: [:]).perform([r]) } catch { yaz(["hata": "tanıma: \(error.localizedDescription)"]); exit(1) }
let gozlem = (r.results ?? []).filter { ($0.topCandidates(1).first?.confidence ?? 0) >= 0.3 }
let sirali = gozlem.sorted { x, y in
    abs(x.boundingBox.midY - y.boundingBox.midY) > 0.012 ? x.boundingBox.midY > y.boundingBox.midY : x.boundingBox.minX < y.boundingBox.minX
}
yaz(["satirlar": sirali.compactMap { $0.topCandidates(1).first?.string }, "diller": diller])
