// Suflor.me menü çubuğu uygulaması (v0.27.0, Faz 5 çekirdek sürüm) — "Suflor Menü.app". Aktarıcı açar (ayar menu_cubugu: true):
//   --port <aktarıcı portu> --anahtar <canli/kart-anahtari.txt>
// - Menü çubuğunda Replik işareti; biçim durumu söyler: boş (bekliyor), dolu (dinliyor: Whisper kanalı akıyor), nokta (açık kart),
//   turuncu nokta (onay bekleyen iş). Durum aktarıcının şerit uzun yoklamasından (GET /cards?bekle=25).
// - Tıkla: buzlu cam (NSVisualEffectView) panelde mini pano — panonun ?gorunum=panel görünümü (WKWebView, saydam). Panel ekran
//   paylaşımında görünmez (sharingType none), odak çalmaz (nonactivating). Sağ tık: Panoyu aç · kısayol · Çık.
// - Mac geneli bas-konuş: Option + Shift + Boşluk basılı tut → mikrofon (16 kHz) → bırakınca POST /bas-konus (anahtar + pano kökeni).
//   Carbon sıcak tuşu basma/bırakmayı ayrı verir; Erişilebilirlik izni gerekmez, mikrofon izni bu uygulamaya sorulur.
// Ağ: yalnız 127.0.0.1. Ses yalnız aktarıcıya gider (Mac'ten çıkmaz).
import Cocoa
import WebKit
import AVFoundation
import Carbon.HIToolbox
import ApplicationServices

setvbuf(stdout, nil, _IOLBF, 0)  // günlük dosyasına satır satır (open --stdout)
let args = CommandLine.arguments
func arg(_ ad: String) -> String? { if let i = args.firstIndex(of: ad), i + 1 < args.count { return args[i + 1] }; return nil }
let PORT = Int(arg("--port") ?? "8765") ?? 8765
let ANAHTAR_YOL = arg("--anahtar") ?? ""
let KOK = "http://127.0.0.1:\(PORT)"
func anahtar() -> String { (try? String(contentsOfFile: ANAHTAR_YOL, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "" }
func istek(_ yol: String, _ govde: [String: Any]? = nil, sure: TimeInterval = 10, _ bitti: @escaping ([String: Any]?) -> Void) {
    guard let u = URL(string: KOK + yol) else { bitti(nil); return }
    var q = URLRequest(url: u, timeoutInterval: sure)
    q.setValue(anahtar(), forHTTPHeaderField: "X-Suflor-Anahtar")
    if let g = govde {
        q.httpMethod = "POST"; q.httpBody = try? JSONSerialization.data(withJSONObject: g)
        q.setValue(KOK, forHTTPHeaderField: "Origin")  // bas-konuş yalnız pano kökeniyle + anahtarla kabul edilir
        q.setValue("application/json", forHTTPHeaderField: "Content-Type")
    }
    URLSession.shared.dataTask(with: q) { d, _, _ in
        bitti(d.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] })
    }.resume()
}

// --- Replik işareti (marka/suflor-isaret.svg'nin iki tırnağı), 18 pt şablon görüntü ------------------------------------------
enum Durum { case bekliyor, dinliyor, kart, eylem, kayit }
func isaret(_ d: Durum) -> NSImage {
    let boy = NSSize(width: 22, height: 18)
    let img = NSImage(size: boy, flipped: true) { _ in
        let s: CGFloat = 18.0 / 64.0
        func tirnak(_ dx: CGFloat) -> NSBezierPath {
            let p = NSBezierPath(); let cx = (23.5 + dx) * s, cy = (37.6 - 3.3) * s, r = 7.6 * s
            p.appendArc(withCenter: NSPoint(x: cx, y: cy), radius: r, startAngle: 0, endAngle: 360)
            p.move(to: NSPoint(x: (31.1 + dx) * s, y: (30.38 - 3.3) * s))
            p.curve(to: NSPoint(x: (18.56 + dx) * s, y: (48.24 - 3.3) * s), controlPoint1: NSPoint(x: (31.48 + dx) * s, y: (39.5 - 3.3) * s),
                    controlPoint2: NSPoint(x: (26.16 + dx) * s, y: (45.58 - 3.3) * s))
            p.curve(to: NSPoint(x: (23.5 + dx) * s, y: (37.6 - 3.3) * s), controlPoint1: NSPoint(x: (23.65 + dx) * s, y: (44.44 - 3.3) * s),
                    controlPoint2: NSPoint(x: (25.17 + dx) * s, y: (40.79 - 3.3) * s))
            return p
        }
        NSColor.black.set()
        for dx: CGFloat in [0, 19] {
            let p = tirnak(dx)
            if d == .dinliyor || d == .kayit { p.fill() } else { p.lineWidth = 1.2; p.stroke() }
        }
        if d == .kart || d == .eylem || d == .kayit {
            (d == .eylem ? NSColor.systemOrange : d == .kayit ? NSColor.systemRed : NSColor.black).set()
            NSBezierPath(ovalIn: NSRect(x: 16.5, y: 1, width: 5, height: 5)).fill()
        }
        return true
    }
    img.isTemplate = (d == .bekliyor || d == .dinliyor || d == .kart)
    return img
}

// --- Panel: odak çalmayan, paylaşımda görünmeyen, buzlu cam ------------------------------------------------------------
final class Panel: NSPanel {
    override var canBecomeKey: Bool { true }  // not/soru kutusuna yazılabilsin
}
final class Uygulama: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    var oge: NSStatusItem!; var panel: Panel!; var web: WKWebView!
    var durum: Durum = .bekliyor; var imza = ""; var gorulenKart = Set<String>(); var acikKart = Set<String>()
    var kayitci: Kayitci?; var sicakTus: EventHotKeyRef?; let masaustu = Masaustu(); var masaustuMic: MasaustuMic?
    func applicationDidFinishLaunching(_ n: Notification) {
        oge = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        oge.button?.image = isaret(.bekliyor); oge.button?.toolTip = "Suflor.me"
        oge.button?.target = self; oge.button?.action = #selector(tiklandi(_:)); oge.button?.sendAction(on: [.leftMouseUp, .rightMouseUp])
        panelKur(); yoklamaDongusu(); sicakTusKur()
        if !args.contains("--masaustu-kapali") {
            masaustu.dongu()
            if !args.contains("--masaustu-mic-kapali") { let m = MasaustuMic(masaustu) { [weak self] in self?.kayitci != nil }; masaustuMic = m; m.dongu() }
        }
    }
    func panelKur() {
        panel = Panel(contentRect: NSRect(x: 0, y: 0, width: 360, height: 500), styleMask: [.nonactivatingPanel, .borderless, .resizable], backing: .buffered, defer: true)
        panel.isFloatingPanel = true; panel.level = .statusBar; panel.hidesOnDeactivate = false; panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.sharingType = .none  // ekran paylaşımında görünmesin (kartlar karşı tarafa gitmesin)
        panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = true; panel.isMovableByWindowBackground = true
        let ve = NSVisualEffectView(frame: panel.contentView!.bounds); ve.autoresizingMask = [.width, .height]
        ve.material = .popover; ve.blendingMode = .behindWindow; ve.state = .active; ve.wantsLayer = true; ve.layer?.cornerRadius = 12; ve.layer?.masksToBounds = true
        let c = WKWebViewConfiguration(); c.websiteDataStore = .default()
        web = WKWebView(frame: ve.bounds, configuration: c); web.autoresizingMask = [.width, .height]; web.navigationDelegate = self; web.uiDelegate = self
        web.setValue(false, forKey: "drawsBackground")  // saydam: buzlu cam görünsün
        ve.addSubview(web); panel.contentView = ve
    }
    func panelYukle() {
        let k = anahtar().addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""
        if let u = URL(string: "\(KOK)/?gorunum=panel&k=\(k)") { web.load(URLRequest(url: u)) }
    }
    // bağlantılar (kart içi) varsayılan tarayıcıda
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if a.navigationType == .linkActivated, let u = a.request.url, !(u.absoluteString.hasPrefix(KOK + "/?gorunum")) { NSWorkspace.shared.open(u); decisionHandler(.cancel); return }
        decisionHandler(.allow)
    }
    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction, windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url { NSWorkspace.shared.open(u) }; return nil
    }
    @objc func tiklandi(_ s: NSStatusBarButton) {
        if NSApp.currentEvent?.type == .rightMouseUp { menuGoster(); return }
        if panel.isVisible { panel.orderOut(nil); return }
        if web.url == nil { panelYukle() }
        if let b = oge.button, let w = b.window {
            let r = w.convertToScreen(b.convert(b.bounds, to: nil)); let ekran = w.screen?.visibleFrame ?? NSScreen.main!.visibleFrame
            var x = r.midX - panel.frame.width / 2; x = max(ekran.minX + 8, min(x, ekran.maxX - panel.frame.width - 8))
            panel.setFrameOrigin(NSPoint(x: x, y: r.minY - panel.frame.height - 6))
        }
        panel.makeKeyAndOrderFront(nil); gorulenKart = acikKart; simgeGuncelle()
    }
    func menuGoster() {
        let m = NSMenu()
        m.addItem(withTitle: "Panoyu aç", action: #selector(panoAc), keyEquivalent: "").target = self
        m.addItem(withTitle: "Paneli yenile", action: #selector(panelYenile), keyEquivalent: "").target = self
        m.addItem(.separator())
        let b = m.addItem(withTitle: "Bas-konuş: Option + Shift + Boşluk basılı tut", action: nil, keyEquivalent: ""); b.isEnabled = false
        m.addItem(.separator())
        m.addItem(withTitle: "Suflor.me menüsünden çık", action: #selector(cik), keyEquivalent: "").target = self
        oge.menu = m; oge.button?.performClick(nil); oge.menu = nil
    }
    @objc func panoAc() { let k = anahtar().addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""; if let u = URL(string: "\(KOK)/?k=\(k)") { NSWorkspace.shared.open(u) } }
    @objc func panelYenile() { panelYukle() }
    @objc func cik() { NSApp.terminate(nil) }
    // --- durum: şeridin uzun yoklaması ---
    func yoklamaDongusu() {
        let im = imza.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""
        istek("/cards?bekle=25&imza=\(im)", sure: 35) { [weak self] v in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if let v = v { self.isle(v) }
                DispatchQueue.main.asyncAfter(deadline: .now() + (v == nil ? 5 : 0.2)) { self.yoklamaDongusu() }
            }
        }
    }
    func isle(_ v: [String: Any]) {
        imza = v["imza"] as? String ?? ""
        let kartlar = (v["cards"] as? [[String: Any]] ?? []).filter { ($0["status"] as? String) == "acik" && ($0["sessiz"] == nil) }
        acikKart = Set(kartlar.compactMap { $0["id"] as? String })
        let eylem = ((v["eylem"] as? [String: Any])?["liste"] as? [[String: Any]] ?? []).contains { ($0["durum"] as? String) == "bekliyor" && ($0["sunuldu"] != nil) }
        let wh = v["whisper"] as? [String: Any] ?? [:]
        let dinliyor = (wh["ben"] as? Bool ?? false) || (wh["karsi"] as? Bool ?? false)
        durum = eylem ? .eylem : !acikKart.subtracting(gorulenKart).isEmpty && !panel.isVisible ? .kart : dinliyor ? .dinliyor : .bekliyor
        if panel.isVisible { gorulenKart = acikKart }
        simgeGuncelle()
    }
    func simgeGuncelle() { oge.button?.image = isaret(kayitci != nil ? .kayit : durum) }
    // --- Mac geneli bas-konuş (Carbon sıcak tuş: basma + bırakma) ---
    func sicakTusKur() {
        var tur = [EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed)),
                   EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyReleased))]
        let ben = Unmanaged.passUnretained(self).toOpaque()
        InstallEventHandler(GetApplicationEventTarget(), { _, olay, veri in
            let u = Unmanaged<Uygulama>.fromOpaque(veri!).takeUnretainedValue()
            if GetEventKind(olay) == UInt32(kEventHotKeyPressed) { u.basBasla() } else { u.basBitir() }
            return noErr
        }, 2, &tur, ben, nil)
        let id = EventHotKeyID(signature: OSType(0x53464C52), id: 1)  // 'SFLR'
        let r = RegisterEventHotKey(UInt32(kVK_Space), UInt32(optionKey | shiftKey), id, GetApplicationEventTarget(), 0, &sicakTus)
        if r != noErr { oge.button?.toolTip = "Suflor.me — Option + Shift + Boşluk başka uygulamada kullanılıyor" }
    }
    func basBasla() {
        guard kayitci == nil else { return }
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .notDetermined: AVCaptureDevice.requestAccess(for: .audio) { _ in }; uyar("Mikrofon izni soruldu — izin verip yeniden bas"); return
        case .denied, .restricted: uyar("Mikrofon izni yok: Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon → Suflor Menü"); return
        default: break
        }
        let k = Kayitci(); guard k.basla() else { uyar("Mikrofon açılamadı"); return }
        kayitci = k; simgeGuncelle(); NSSound(named: "Pop")?.play()
        istek("/bas-konus", ["komut": "basla"]) { [weak self] v in
            if let v = v, (v["ok"] as? Bool) == false { DispatchQueue.main.async { _ = self?.kayitci?.durdur(); self?.kayitci = nil; self?.simgeGuncelle(); self?.uyar(v["err"] as? String ?? "Bas-konuş başlamadı") } }
        }
    }
    func basBitir() {
        guard let k = kayitci else { return }
        let pcm = k.durdur(); kayitci = nil; simgeGuncelle()
        istek("/bas-konus", ["pcm": pcm.base64EncodedString()], sure: 20) { [weak self] v in
            if let v = v, (v["ok"] as? Bool) == false { DispatchQueue.main.async { self?.uyar(v["err"] as? String ?? "Gönderilemedi") } }
        }
    }
    func uyar(_ m: String) { NSSound(named: "Basso")?.play(); oge.button?.toolTip = "Suflor.me — " + m; print("UYARI: " + m) }
}

// --- Masaüstü toplantı uygulaması: Erişilebilirlik ile "Ayrıl" ve "Sesi aç/kapat" düğmeleri (Teams yeni sürüm, Zoom) -------------
// İzin: Sistem Ayarları → Gizlilik ve Güvenlik → Erişilebilirlik → Suflor Menü. Teams (WebView2/Chromium) erişilebilirlik ağacını yalnız
// istenince kurar: uygulama öğesine AXManualAccessibility ve AXEnhancedUserInterface verilir (12 Ekim gerçek Teams: ikisi de hata kodu döndü ama
// ağaç ancak ikincisiyle açıldı — her taramada yeniden verilir; `--ax-dokum` düğme adlarını döker). 3 sn'de bir, en çok 6000 öğe; durum değişince ya da toplantıda 10 sn'de
// bir POST /masaustu. Düğme adları herkese açık bilgiyle; gerçek uygulamada doğrulanınca genişletilir.
final class Masaustu {
    let UYG: [(bundle: String, ad: String)] = [("com.microsoft.teams2", "Teams"), ("com.microsoft.teams", "Teams"), ("us.zoom.xos", "Zoom")]
    let AYRIL = try! NSRegularExpression(pattern: "^(leave|ayrıl|end meeting|end|toplantıdan ayrıl|hang ?up)\\b", options: [.caseInsensitive])
    let SESSIZ = try! NSRegularExpression(pattern: "^(unmute|sesi aç|sesini aç|mikrofonun sesini aç|mikrofonu aç|turn on mic)", options: [.caseInsensitive])
    let ACIK = try! NSRegularExpression(pattern: "^(mute|sesi kapat|sesini kapat|mikrofonu sessize al|mikrofonu kapat|turn off mic)", options: [.caseInsensitive])
    var micDugme: AXUIElement?; let kilit = NSLock()  // toplantı penceresinin mikrofon düğmesi: 0,5 sn'de bir yalnız onun etiketi okunur
    var son: [String: Any] = [:]; var sonGonder = Date.distantPast; var acilmis = Set<pid_t>(); var izinSoruldu = false, izinYazildi = false
    func uy(_ r: NSRegularExpression, _ t: String) -> Bool { r.firstMatch(in: t, range: NSRange(t.startIndex..., in: t)) != nil }
    func deger(_ e: AXUIElement, _ a: String) -> AnyObject? { var v: AnyObject?; return AXUIElementCopyAttributeValue(e, a as CFString, &v) == .success ? v : nil }
    func etiket(_ e: AXUIElement) -> String {
        [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute].compactMap { deger(e, $0) as? String }.first { !$0.isEmpty }?.trimmingCharacters(in: .whitespaces) ?? ""
    }
    func tara() -> [String: Any]? {
        guard AXIsProcessTrusted() else {
            if !izinYazildi { izinYazildi = true; print("MASAÜSTÜ: Erişilebilirlik izni yok (Aygıt Denetimi ve Veri Erişimi → Suflor Menü)") }
            if !izinSoruldu, NSWorkspace.shared.runningApplications.contains(where: { a in UYG.contains { $0.bundle == a.bundleIdentifier } }) {
                izinSoruldu = true; AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary)
            }
            return nil
        }
        for app in NSWorkspace.shared.runningApplications {
            guard let u = UYG.first(where: { $0.bundle == app.bundleIdentifier }) else { continue }
            let kok = AXUIElementCreateApplication(app.processIdentifier)
            AXUIElementSetAttributeValue(kok, "AXManualAccessibility" as CFString, kCFBooleanTrue)
            AXUIElementSetAttributeValue(kok, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
            for w in (deger(kok, kAXWindowsAttribute) as? [AXUIElement] ?? []) {
                var ayril = false, sessiz: Bool? = nil, n = 0, yigin: [(AXUIElement, Int)] = [(w, 0)], md: AXUIElement? = nil
                while let (e, d) = yigin.popLast(), n < 6000 {
                    n += 1
                    if (deger(e, kAXRoleAttribute) as? String) == kAXButtonRole as String || (deger(e, kAXRoleAttribute) as? String) == "AXCheckBox" {
                        let t = etiket(e)
                        if uy(AYRIL, t) { ayril = true } else if uy(SESSIZ, t) { sessiz = true; md = md ?? e } else if uy(ACIK, t) { sessiz = false; md = md ?? e }
                    }
                    if d < 45, let c = deger(e, kAXChildrenAttribute) as? [AXUIElement] { yigin.append(contentsOf: c.map { ($0, d + 1) }) }
                }
                if ayril { kilit.lock(); micDugme = md; kilit.unlock(); return ["uygulama": u.ad, "toplantida": true, "sessiz": sessiz as Any, "baslik": (deger(w, kAXTitleAttribute) as? String) ?? ""] }
            }
            kilit.lock(); micDugme = nil; kilit.unlock()
            return ["uygulama": u.ad, "toplantida": false]
        }
        return nil
    }
    // Teşhis: `--ax-dokum` → toplantı uygulamasının pencerelerindeki düğme/onay kutusu etiketleri stdout'a (gerçek ağaçla düğme adlarını doğrulamak için)
    func dokum() {
        print("izin:", AXIsProcessTrusted())
        for app in NSWorkspace.shared.runningApplications {
            guard UYG.contains(where: { $0.bundle == app.bundleIdentifier }) else { continue }
            let kok = AXUIElementCreateApplication(app.processIdentifier)
            let r1 = AXUIElementSetAttributeValue(kok, "AXManualAccessibility" as CFString, kCFBooleanTrue)
            let r2 = AXUIElementSetAttributeValue(kok, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue); Thread.sleep(forTimeInterval: 2.5)
            print("açma: manual \(r1.rawValue) · enhanced \(r2.rawValue)")
            for w in (deger(kok, kAXWindowsAttribute) as? [AXUIElement] ?? []) {
                print("== \(app.bundleIdentifier ?? "") · \((deger(w, kAXTitleAttribute) as? String) ?? "")")
                var n = 0, yigin: [(AXUIElement, Int)] = [(w, 0)]
                while let (e, d) = yigin.popLast(), n < 8000 {
                    n += 1; let r = (deger(e, kAXRoleAttribute) as? String) ?? ""
                    if r == "AXButton" || r == "AXCheckBox" || r == "AXMenuButton" || r == "AXToggle" {
                        let t = [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute].compactMap { deger(e, $0) as? String }.filter { !$0.isEmpty }
                        if !t.isEmpty { print("  \(r) · \(t.joined(separator: " | ").prefix(120))") }
                    }
                    if d < 45, let c = deger(e, kAXChildrenAttribute) as? [AXUIElement] { yigin.append(contentsOf: c.map { ($0, d + 1) }) }
                }
                print("  öğe: \(n)")
            }
        }
    }
    // sessiz mi (hızlı yol): saklanan düğmenin etiketi; düğme yoksa ya da okunamazsa son taramanın sonucu
    func sessizHizli() -> Bool? {
        kilit.lock(); let d = micDugme, s = son["sessiz"] as? Bool; kilit.unlock()
        if let d = d { let t = etiket(d); if uy(SESSIZ, t) { return true }; if uy(ACIK, t) { return false } }
        return s
    }
    var toplantida: Bool { kilit.lock(); defer { kilit.unlock() }; return (son["toplantida"] as? Bool) ?? false }
    func dongu() {
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 3) { [weak self] in
            guard let self = self else { return }
            let v = self.tara() ?? [:]
            let degisti = (v["toplantida"] as? Bool) != (self.son["toplantida"] as? Bool) || (v["sessiz"] as? Bool) != (self.son["sessiz"] as? Bool)
            if !v.isEmpty && (degisti || ((v["toplantida"] as? Bool ?? false) && Date().timeIntervalSince(self.sonGonder) > 10)) {
                var g = v; if g["sessiz"] is NSNull || (g["sessiz"] as? Bool) == nil { g.removeValue(forKey: "sessiz") }
                istek("/masaustu", g) { _ in }; self.sonGonder = Date()
            }
            self.kilit.lock(); self.son = v; self.kilit.unlock(); self.dongu()
        }
    }
}

// --- Masaüstü toplantıda kullanıcının mikrofonu (v0.30.0) -----------------------------------------------------------------
// Toplantı uygulamasında toplantıdayken mikrofon açılır (aktarıcı "ben" kanalı; eklentinin web Teams'teki işinin karşılığı). 1 sn'lik parça
// 1 sn bekletilir: o arada mikrofon düğmesi "sesini aç" gösterirse (sessize alındı) parça atılır — sessizdeki söz yazılmaz. Düğme 0,5 sn'de bir
// okunur. Bas-konuş basılıyken parça gönderilmez (Claude'a söylenen toplantı dökümüne girmez). Aygıt değişince (kulaklık takıldı) motor yeniden
// başlar. Ses yalnız 127.0.0.1'deki aktarıcıya gider, diske yazılmaz.
final class MasaustuMic {
    let masaustu: Masaustu; var kayitci: Kayitci?; var bas: () -> Bool
    var tampon = Data(), t0 = 0.0, bekleyen: [(t0: Double, veri: Data, hazir: Double)] = [], sonSessiz = 0.0, izinYazildi = false
    let kilit = NSLock(); var gozlem: NSObjectProtocol?
    init(_ m: Masaustu, bas: @escaping () -> Bool) { masaustu = m; self.bas = bas }
    var aygitAd = "?"
    func aygit() -> String { aygitAd }
    func dongu() {
        Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in self?.tik() }
    }
    func tik() {
        let simdi = Date().timeIntervalSince1970
        guard masaustu.toplantida else { if kayitci != nil { durdur() }; return }
        if kayitci == nil { baslat(); return }
        let sessiz = masaustu.sessizHizli() == true || bas()
        kilit.lock()
        if sessiz { sonSessiz = simdi; tampon = Data(); bekleyen.removeAll() }
        // hazır parçalar: bekleme süresi doldu ve parçanın başından beri sessize alınmadı
        let gidecek = bekleyen.filter { simdi >= $0.hazir && sonSessiz < $0.t0 }
        bekleyen.removeAll { simdi >= $0.hazir }
        kilit.unlock()
        for g in gidecek { istek("/ses-masaustu", ["t": Int(g.t0 * 1000), "pcm": g.veri.base64EncodedString(), "aygit": aygit()]) { _ in } }
    }
    func baslat() {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .notDetermined: AVCaptureDevice.requestAccess(for: .audio) { _ in }; return
        case .denied, .restricted:
            if !izinYazildi { izinYazildi = true; print("MASAÜSTÜ MİKROFON: izin yok"); istek("/ses-masaustu", ["olay": "izin"]) { _ in } }
            return
        default: break
        }
        aygitAd = AVCaptureDevice.default(for: .audio)?.localizedName ?? "?"
        let k = Kayitci()
        k.akis = { [weak self] veri, t in
            guard let self = self else { return }
            self.kilit.lock(); defer { self.kilit.unlock() }
            if self.tampon.isEmpty { self.t0 = t }
            self.tampon.append(veri)
            if self.tampon.count >= 32000 {  // 1 sn (16 kHz × 2 bayt)
                self.bekleyen.append((self.t0, self.tampon, Date().timeIntervalSince1970 + 1.0)); self.tampon = Data()
            }
        }
        guard k.basla() else { print("MASAÜSTÜ MİKROFON: açılamadı"); return }
        kayitci = k; print("MASAÜSTÜ MİKROFON: açıldı · \(aygit())"); istek("/ses-masaustu", ["olay": "acildi", "aygit": aygit()]) { _ in }
        gozlem = NotificationCenter.default.addObserver(forName: .AVAudioEngineConfigurationChange, object: k.motor, queue: .main) { [weak self] _ in
            print("MASAÜSTÜ MİKROFON: aygıt değişti, yeniden açılıyor"); self?.durdur(sessizce: true)  // sonraki tik yeniden açar
        }
    }
    func durdur(sessizce: Bool = false) {
        if let g = gozlem { NotificationCenter.default.removeObserver(g); gozlem = nil }
        _ = kayitci?.durdur(); kayitci = nil
        kilit.lock(); tampon = Data(); bekleyen.removeAll(); kilit.unlock()
        if !sessizce { print("MASAÜSTÜ MİKROFON: kapandı"); istek("/ses-masaustu", ["olay": "kapandi"]) { _ in } }
    }
}

// --- mikrofon → 16 kHz tek kanal Int16 ----------------------------------------------------------------------------------
final class Kayitci {
    let motor = AVAudioEngine(); var veri = Data(); let kilit = NSLock(); var donus: AVAudioConverter?
    var akis: ((Data, Double) -> Void)?  // akış kipi (masaüstü toplantı): her tampon (16 kHz Int16, ilk örneğin epoch sn'si) buraya, veri biriktirilmez
    let hedef = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true)!
    func basla() -> Bool {
        let giris = motor.inputNode; let bic = giris.outputFormat(forBus: 0)
        guard bic.sampleRate > 0, let d = AVAudioConverter(from: bic, to: hedef) else { return false }
        donus = d
        giris.installTap(onBus: 0, bufferSize: 4096, format: bic) { [weak self] buf, _ in
            guard let self = self, let d = self.donus else { return }
            let cap = AVAudioFrameCount(Double(buf.frameLength) * 16000 / bic.sampleRate) + 32
            guard let cik = AVAudioPCMBuffer(pcmFormat: self.hedef, frameCapacity: cap) else { return }
            var verildi = false
            d.convert(to: cik, error: nil) { _, durum in if verildi { durum.pointee = .noDataNow; return nil }; verildi = true; durum.pointee = .haveData; return buf }
            guard let p = cik.int16ChannelData else { return }
            let parca = Data(buffer: UnsafeBufferPointer(start: p[0], count: Int(cik.frameLength)))
            if let a = self.akis { a(parca, Date().timeIntervalSince1970 - Double(buf.frameLength) / bic.sampleRate); return }
            self.kilit.lock(); self.veri.append(parca); self.kilit.unlock()
        }
        do { try motor.start() } catch { giris.removeTap(onBus: 0); return false }
        return true
    }
    func durdur() -> Data { motor.inputNode.removeTap(onBus: 0); motor.stop(); kilit.lock(); defer { kilit.unlock() }; return veri }
}

if args.contains("--ax-dokum") { Masaustu().dokum(); exit(0) }
let uyg = NSApplication.shared
let d = Uygulama()
uyg.delegate = d
uyg.setActivationPolicy(.accessory)
uyg.run()
