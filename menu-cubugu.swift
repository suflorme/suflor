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
import ScreenCaptureKit

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
    var kayitci: Kayitci?; var sicakTus: EventHotKeyRef?; let masaustu = Masaustu(); var masaustuMic: MasaustuMic?; var masaustuKanit: MasaustuKanit?
    var digerTuslar: [EventHotKeyRef?] = []
    func applicationDidFinishLaunching(_ n: Notification) {
        oge = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        oge.button?.image = isaret(.bekliyor); oge.button?.toolTip = "Suflor.me"
        oge.button?.target = self; oge.button?.action = #selector(tiklandi(_:)); oge.button?.sendAction(on: [.leftMouseUp, .rightMouseUp])
        panelKur(); yoklamaDongusu(); sicakTusKur()
        if !args.contains("--masaustu-kapali") {
            masaustu.dongu()
            if !args.contains("--masaustu-mic-kapali") { let m = MasaustuMic(masaustu) { [weak self] in self?.kayitci != nil }; masaustuMic = m; m.dongu() }
            let k = MasaustuKanit(masaustu); masaustuKanit = k; k.dongu()
        }
        // panel Esc ile kapanır (12 Ekim: açık kalan panel kapatılamıyordu)
        NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] e in
            if e.keyCode == 53, let p = self?.panel, p.isVisible { p.orderOut(nil); return nil }
            return e
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
        if panel.isVisible { m.addItem(withTitle: "Paneli kapat (Esc)", action: #selector(panelKapat), keyEquivalent: "").target = self }
        m.addItem(.separator())
        for t in ["Bas-konuş: Option + Shift + Boşluk basılı tut", "Kanıt: Option + Shift + K", "Ne diyeyim?: Option + Shift + O", "Sessiz (10 dk kart yok): Option + Shift + M"] {
            let b = m.addItem(withTitle: t, action: nil, keyEquivalent: ""); b.isEnabled = false
        }
        m.addItem(.separator())
        m.addItem(withTitle: "Suflor.me menüsünden çık", action: #selector(cik), keyEquivalent: "").target = self
        oge.menu = m; oge.button?.performClick(nil); oge.menu = nil
    }
    @objc func panoAc() { let k = anahtar().addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""; if let u = URL(string: "\(KOK)/?k=\(k)") { NSWorkspace.shared.open(u) } }
    @objc func panelYenile() { panelYukle() }
    @objc func panelKapat() { panel.orderOut(nil) }
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
        masaustuKanit?.iste(v["kanit_iste"] as? [String: Any])  // masaüstü toplantıdayken kanıtı toplantı penceresinden al
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
            var hk = EventHotKeyID()
            GetEventParameter(olay, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &hk)
            let basildi = GetEventKind(olay) == UInt32(kEventHotKeyPressed)
            switch hk.id {
            case 1: if basildi { u.basBasla() } else { u.basBitir() }
            case 2: if basildi { u.kisayol("kanit") }
            case 3: if basildi { u.kisayol("ozet") }
            case 4: if basildi { u.kisayol("sessiz") }
            default: break
            }
            return noErr
        }, 2, &tur, ben, nil)
        let id = EventHotKeyID(signature: OSType(0x53464C52), id: 1)  // 'SFLR'
        let r = RegisterEventHotKey(UInt32(kVK_Space), UInt32(optionKey | shiftKey), id, GetApplicationEventTarget(), 0, &sicakTus)
        if r != noErr { oge.button?.toolTip = "Suflor.me — Option + Shift + Boşluk başka uygulamada kullanılıyor" }
        // v0.31.0: eklentinin kısayolları Mac genelinde (masaüstü Teams/Zoom'da da). Chrome'daki aynı kısayolu bu uygulama yakalar; iş aynı kalır:
        // kanıt isteği aktarıcıya gider, tarayıcıdaki toplantıda eklenti, masaüstünde bu uygulama çeker. Ayar `kisayollar: false` kapatır.
        if !args.contains("--kisayol-kapali") {
            for (i, tus) in [(UInt32(2), kVK_ANSI_K), (3, kVK_ANSI_O), (4, kVK_ANSI_M)] {
                var ref: EventHotKeyRef?
                if RegisterEventHotKey(UInt32(tus), UInt32(optionKey | shiftKey), EventHotKeyID(signature: OSType(0x53464C52), id: i), GetApplicationEventTarget(), 0, &ref) == noErr { digerTuslar.append(ref) }
                else { print("KISAYOL: Option + Shift + \(["", "", "K", "O", "M"][Int(i)]) başka uygulamada kullanılıyor") }
            }
        }
    }
    func kisayol(_ tur: String) {
        NSSound(named: "Tink")?.play()
        let (yol, govde): (String, [String: Any]) = tur == "kanit" ? ("/kanit-iste", ["kaynak": "kisayol"]) : ("/komut", ["tur": tur])
        istek(yol, govde) { [weak self] v in if v == nil { DispatchQueue.main.async { self?.uyar("Aktarıcıya ulaşılamadı") } } }
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

// --- Masaüstü toplantı uygulaması: Erişilebilirlik ile toplantı durumu (Teams yeni sürüm, Zoom) ---------------------------------
// İzin: Sistem Ayarları → Gizlilik ve Güvenlik → Erişilebilirlik → Suflor Menü. Teams (WebView2/Chromium) erişilebilirlik ağacını yalnız
// istenince kurar: uygulama öğesine AXManualAccessibility ve AXEnhancedUserInterface verilir (12 Ekim gerçek Teams: ikisi de hata kodu döndü ama
// ağaç ancak ikincisiyle açıldı — her taramada yeniden verilir; `--ax-dokum` etiketleri döker). 3 sn'de bir, pencere başına en çok 6000 öğe;
// durum değişince ya da toplantıda 10 sn'de bir POST /masaustu. Okunanlar (v0.31.0): "Ayrıl" (toplantıda), mikrofon düğmesi (sessiz),
// ekran paylaşımı (karşı taraf paylaşıyor / kullanıcı kendisi paylaşıyor), konuşan kişi göstergesi ve Kişiler paneli (katılımcı adları;
// panel kapalıysa 3 dk'da bir açılıp okunur ve kapatılır — kullanıcı onayı, 12 Ekim). Teams'te "Ayrıl" ve mikrofon adları gerçek uygulamada
// doğrulandı (12 Ekim); paylaşım, konuşan, Kişiler ve Zoom adları herkese açık bilgiyle — ilk gerçek kullanımda `--ax-dokum` ile genişlet.
final class Masaustu {
    let UYG: [(bundle: String, ad: String)] = [("com.microsoft.teams2", "Teams"), ("com.microsoft.teams", "Teams"), ("us.zoom.xos", "Zoom")]
    static func rx(_ p: String) -> NSRegularExpression { try! NSRegularExpression(pattern: p, options: [.caseInsensitive]) }
    let AYRIL = rx("^(leave|ayrıl|end meeting|end|toplantıdan ayrıl|toplantıyı sonlandır|hang ?up)\\b")
    let SESSIZ = rx("^(unmute|sesi aç|sesini aç|mikrofonun sesini aç|mikrofonu aç|turn on mic)")
    let ACIK = rx("^(mute|sesi kapat|sesini kapat|mikrofonu sessize al|mikrofonu kapat|turn off mic)")
    // kullanıcının kendi paylaşımı (paylaşılan ekran kendi ekranı: kanıt alınmaz) — karşı tarafın paylaşımı
    let KENDI_PAYLAS = rx("paylaşmayı durdur|sunmayı durdur|sunuyu durdur|paylaşımı durdur|sunuyorsunuz|ekranınızı paylaşıyorsunuz|stop sharing|stop presenting|stop share|you('| a)re (presenting|sharing)")
    let PAYLAS = rx("(ekran(ı|ını)?|içeri(k|ği)) paylaşıyor|ekranı paylaşılıyor|\\bsunuyor$|is (sharing|presenting)|'s screen|ekranını görüntülüyorsunuz|you are viewing|^view options$|^görünüm seçenekleri$|paylaşılan (ekran|içerik)|shared (screen|content)")
    let KONUSAN = rx("^(.{2,40}?)[,\\s–-]+(konuşuyor|is speaking|speaking|is talking)$")
    let KISILER = rx("^(kişiler|katılımcılar|katılımcıları yönet|participants|manage participants|people|show participants)\\b")
    let ARAYUZ = Set(["mute", "unmute", "invite", "all", "share", "more", "participants", "people", "in", "the", "meeting", "waiting", "room", "lobby", "admit",
                      "close", "search", "leave", "host", "co-host", "organizer", "presenter", "attendee", "attendees", "you", "me", "guest", "raise", "hand", "chat",
                      "kişiler", "katılımcılar", "toplantıda", "davet", "et", "sessize", "al", "herkesi", "düzenleyici", "sunucu", "katılımcı", "konuk", "siz", "ben",
                      "ara", "kapat", "bekleme", "odası", "lobi", "kabul", "microsoft", "teams", "zoom"])
    var micDugme: AXUIElement?; let kilit = NSLock()  // toplantı penceresinin mikrofon düğmesi: 0,5 sn'de bir yalnız onun etiketi okunur
    var son: [String: Any] = [:]; var sonGonder = Date.distantPast; var izinSoruldu = false, izinYazildi = false
    var toplantiPid: pid_t = 0, toplantiBaslik = ""  // kanıt görüntüsü bu pencereden
    var paylasimAday: Bool? = nil, paylasimSay = 0, paylasim: Bool? = nil  // iki tarama aynıysa kararlı
    var kisilerSon = Date.distantPast, toplantiBas = Date.distantPast, katilimcilar: [String]? = nil, kisilerDugme: AXUIElement?
    func uy(_ r: NSRegularExpression, _ t: String) -> Bool { r.firstMatch(in: t, range: NSRange(t.startIndex..., in: t)) != nil }
    func yakala(_ r: NSRegularExpression, _ t: String) -> String? {
        guard let m = r.firstMatch(in: t, range: NSRange(t.startIndex..., in: t)), m.numberOfRanges > 1, let g = Range(m.range(at: 1), in: t) else { return nil }
        return String(t[g]).trimmingCharacters(in: .whitespaces)
    }
    func deger(_ e: AXUIElement, _ a: String) -> AnyObject? { var v: AnyObject?; return AXUIElementCopyAttributeValue(e, a as CFString, &v) == .success ? v : nil }
    func etiket(_ e: AXUIElement) -> String {
        [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute].compactMap { deger(e, $0) as? String }.first { !$0.isEmpty }?.trimmingCharacters(in: .whitespaces) ?? ""
    }
    func ac(_ kok: AXUIElement) {
        AXUIElementSetAttributeValue(kok, "AXManualAccessibility" as CFString, kCFBooleanTrue)
        AXUIElementSetAttributeValue(kok, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
    }
    // bir pencerenin taraması: düğmeler (ayrıl, mikrofon, kişiler, kendi paylaşımı) + tüm etiket/metinler (paylaşım, konuşan)
    struct Tarama { var ayril = false, sessiz: Bool? = nil, md: AXUIElement? = nil, kisiler: AXUIElement? = nil, kendi = false, karsi = false, konusan: String? = nil }
    func pencereTara(_ w: AXUIElement) -> Tarama {
        var s = Tarama(), n = 0, yigin: [(AXUIElement, Int)] = [(w, 0)]
        while let (e, d) = yigin.popLast(), n < 6000 {
            n += 1
            let rol = (deger(e, kAXRoleAttribute) as? String) ?? ""
            if rol == kAXButtonRole as String || rol == "AXCheckBox" || rol == "AXMenuButton" {
                let t = etiket(e)
                if uy(AYRIL, t) { s.ayril = true } else if uy(SESSIZ, t) { s.sessiz = true; s.md = s.md ?? e } else if uy(ACIK, t) { s.sessiz = false; s.md = s.md ?? e }
                else if uy(KISILER, t) { s.kisiler = s.kisiler ?? e }
                if uy(KENDI_PAYLAS, t) { s.kendi = true }
            }
            for t in [deger(e, kAXDescriptionAttribute) as? String, rol == kAXStaticTextRole as String ? deger(e, kAXValueAttribute) as? String : nil].compactMap({ $0 }) where t.count < 160 {
                let tt = t.trimmingCharacters(in: .whitespaces)
                if uy(KENDI_PAYLAS, tt) { s.kendi = true } else if uy(PAYLAS, tt) { s.karsi = true }
                if s.konusan == nil, let ad = yakala(KONUSAN, tt) { s.konusan = ad }
            }
            if d < 45, let c = deger(e, kAXChildrenAttribute) as? [AXUIElement] { yigin.append(contentsOf: c.map { ($0, d + 1) }) }
        }
        return s
    }
    func tara() -> [String: Any]? {
        guard AXIsProcessTrusted() else {
            if !izinYazildi { izinYazildi = true; print("MASAÜSTÜ: Erişilebilirlik izni yok (Aygıt Denetimi ve Veri Erişimi → Suflor Menü)") }
            if !izinSoruldu, NSWorkspace.shared.runningApplications.contains(where: { a in UYG.contains { $0.bundle == a.bundleIdentifier } }) {
                izinSoruldu = true; AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary)
            }
            return nil
        }
        var bos: [String: Any]? = nil  // toplantıda olmayan ilk uygulama (Teams açık ama toplantı Zoom'daysa Zoom'a da bakılır)
        for app in NSWorkspace.shared.runningApplications {
            guard let u = UYG.first(where: { $0.bundle == app.bundleIdentifier }) else { continue }
            let kok = AXUIElementCreateApplication(app.processIdentifier); ac(kok)
            for w in (deger(kok, kAXWindowsAttribute) as? [AXUIElement] ?? []) {
                let s = pencereTara(w)
                guard s.ayril else { continue }
                let baslik = (deger(w, kAXTitleAttribute) as? String) ?? ""
                kilit.lock(); micDugme = s.md; toplantiPid = app.processIdentifier; toplantiBaslik = baslik; kisilerDugme = s.kisiler; kilit.unlock()
                // paylaşım: kendi paylaşımı → false; karşı → true; iki tarama aynı olunca kararlı
                let p = s.kendi ? false : s.karsi
                if p == paylasimAday { paylasimSay += 1 } else { paylasimAday = p; paylasimSay = 1 }
                if paylasimSay >= 2 { paylasim = p }
                var v: [String: Any] = ["uygulama": u.ad, "toplantida": true, "sessiz": s.sessiz as Any, "baslik": baslik]
                if let pp = paylasim { v["paylasim"] = pp }
                if let k = s.konusan { v["konusan"] = k }
                return v
            }
            if bos == nil { bos = ["uygulama": u.ad, "toplantida": false] }
        }
        kilit.lock(); micDugme = nil; toplantiPid = 0; kisilerDugme = nil; kilit.unlock()
        paylasimAday = nil; paylasimSay = 0; paylasim = nil; katilimcilar = nil
        return bos
    }
    // tüm pencerelerin metinleri (Kişiler paneli açılmadan önce/sonra farkı = katılımcı adları; Zoom'da panel ayrı pencere olabilir)
    func metinler(_ pid: pid_t) -> Set<String> {
        let kok = AXUIElementCreateApplication(pid); var out = Set<String>()
        for w in (deger(kok, kAXWindowsAttribute) as? [AXUIElement] ?? []) {
            var n = 0, yigin: [(AXUIElement, Int)] = [(w, 0)]
            while let (e, d) = yigin.popLast(), n < 8000 {
                n += 1
                for a in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] { if let t = deger(e, a) as? String, !t.isEmpty, t.count < 80 { out.insert(t.trimmingCharacters(in: .whitespaces)) } }
                if d < 45, let c = deger(e, kAXChildrenAttribute) as? [AXUIElement] { yigin.append(contentsOf: c.map { ($0, d + 1) }) }
            }
        }
        return out
    }
    // ad gibi mi: 1–4 sözcük, harf (ve . ' -), her sözcük büyük harfle, arayüz sözcüğü yok. "(Siz)", ", Düzenleyici" gibi ekler atılır.
    func adMi(_ ham: String) -> String? {
        var t = ham.replacingOccurrences(of: "\\s*\\((siz|you|ben|me|düzenleyici|organizer|host|konuk|guest|misafir)\\)", with: "", options: [.regularExpression, .caseInsensitive])
        t = t.components(separatedBy: ",").first?.trimmingCharacters(in: .whitespaces) ?? ""
        let ks = t.split(separator: " ").map(String.init)
        guard (1...4).contains(ks.count), t.count >= 2, t.count <= 40 else { return nil }
        for k in ks {
            guard let i = k.first, i.isUppercase, k.allSatisfy({ $0.isLetter || ".'’-".contains($0) }), !ARAYUZ.contains(k.lowercased(with: Locale(identifier: "tr"))) else { return nil }
        }
        return t
    }
    // Kişiler paneli: kapalıysa aç (AXPress), adları oku, açan bizsek kapat. Toplantı başından 15 sn sonra ve 3 dk'da bir.
    func katilimciOku() -> [String]? {
        kilit.lock(); let pid = toplantiPid, dugme = kisilerDugme; kilit.unlock()
        guard pid != 0, let d = dugme else { return nil }
        let once = metinler(pid)
        guard AXUIElementPerformAction(d, kAXPressAction as CFString) == .success else { return nil }
        Thread.sleep(forTimeInterval: 2.0)
        let sonra = metinler(pid)
        let yeni = sonra.subtracting(once)
        var adlar: [String]
        if yeni.count >= 1 {  // panel bizimle açıldı: yeni metinlerden adlar; sonra kapat
            adlar = yeni.compactMap { adMi($0) }
            AXUIElementPerformAction(d, kAXPressAction as CFString)
        } else {  // panel zaten açıktı ve biz kapattık: geri aç, açıkken görünen (kapanınca kaybolan) metinlerden adlar
            AXUIElementPerformAction(d, kAXPressAction as CFString); Thread.sleep(forTimeInterval: 1.5)
            adlar = metinler(pid).subtracting(sonra).compactMap { adMi($0) }
            if adlar.isEmpty { adlar = once.subtracting(sonra).compactMap { adMi($0) } }
        }
        let tekil = Array(Set(adlar)).sorted()
        print("MASAÜSTÜ: Kişiler paneli okundu · \(tekil.count) ad")
        return tekil.isEmpty ? nil : Array(tekil.prefix(50))
    }
    // Teşhis: `--ax-dokum` → toplantı uygulamasının pencerelerindeki düğme etiketleri ve diğer metinler stdout'a (gerçek ağaçla adları doğrulamak için)
    func dokum() {
        print("izin:", AXIsProcessTrusted())
        for app in NSWorkspace.shared.runningApplications {
            guard UYG.contains(where: { $0.bundle == app.bundleIdentifier }) else { continue }
            let kok = AXUIElementCreateApplication(app.processIdentifier); ac(kok); Thread.sleep(forTimeInterval: 2.5)
            for w in (deger(kok, kAXWindowsAttribute) as? [AXUIElement] ?? []) {
                print("== \(app.bundleIdentifier ?? "") · \((deger(w, kAXTitleAttribute) as? String) ?? "")")
                var n = 0, yigin: [(AXUIElement, Int)] = [(w, 0)], metin = Set<String>()
                while let (e, d) = yigin.popLast(), n < 8000 {
                    n += 1; let r = (deger(e, kAXRoleAttribute) as? String) ?? ""
                    let t = [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute].compactMap { deger(e, $0) as? String }.filter { !$0.isEmpty }
                    if r == "AXButton" || r == "AXCheckBox" || r == "AXMenuButton" || r == "AXToggle" { if !t.isEmpty { print("  \(r) · \(t.joined(separator: " | ").prefix(120))") } }
                    else { for x in t + [(r == kAXStaticTextRole as String ? deger(e, kAXValueAttribute) as? String : nil) ?? ""] where !x.isEmpty && x.count < 120 { metin.insert("\(r) · \(x)") } }
                    if d < 45, let c = deger(e, kAXChildrenAttribute) as? [AXUIElement] { yigin.append(contentsOf: c.map { ($0, d + 1) }) }
                }
                for m in metin.sorted().prefix(300) { print("  ~ \(m)") }
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
    var paylasimVar: Bool { kilit.lock(); defer { kilit.unlock() }; return (son["paylasim"] as? Bool) ?? false }
    var pencere: (pid_t, String) { kilit.lock(); defer { kilit.unlock() }; return (toplantiPid, toplantiBaslik) }
    func dongu() {
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 3) { [weak self] in
            guard let self = self else { return }
            var v = self.tara() ?? [:]
            let top = v["toplantida"] as? Bool ?? false, once = self.son["toplantida"] as? Bool ?? false
            if top && !once { self.toplantiBas = Date(); self.kisilerSon = .distantPast }
            // Kişiler paneli: toplantı başından 15 sn sonra, sonra 3 dk'da bir
            if top, !args.contains("--kisiler-kapali"), Date().timeIntervalSince(self.toplantiBas) > 15, Date().timeIntervalSince(self.kisilerSon) > 180 {
                self.kisilerSon = Date()
                if let k = self.katilimciOku() { self.katilimcilar = k; v["katilimcilar"] = k }
            }
            let degisti = self.son.isEmpty || top != once || (v["sessiz"] as? Bool) != (self.son["sessiz"] as? Bool) || (v["paylasim"] as? Bool) != (self.son["paylasim"] as? Bool)
                || v["katilimcilar"] != nil || (v["konusan"] as? String) != nil
            if !v.isEmpty && (degisti || (top && Date().timeIntervalSince(self.sonGonder) > 10)) {
                var g = v; if g["sessiz"] is NSNull || (g["sessiz"] as? Bool) == nil { g.removeValue(forKey: "sessiz") }
                istek("/masaustu", g) { _ in }; self.sonGonder = Date()
            }
            self.kilit.lock(); self.son = v; self.kilit.unlock(); self.dongu()
        }
    }
}

// --- Masaüstü toplantı penceresinin görüntüsü (v0.31.0; ScreenCaptureKit, izin: Ekran ve Sistem Sesi Kaydı → Suflor Menü) --------
// Kanıt isteği (pano 📷, Option + Shift + K, Claude) masaüstü toplantıdayken toplantı penceresinden alınır → POST /kanit-masaustu.
// Karşı taraf ekran paylaşırken 3 sn'de bir küçük (64×40 gri) görüntü karşılaştırılır: belirgin değişip duruluyunca ve son kendiliğinden
// görüntüden ≥ 10 sn geçtiyse tam görüntü (kaynak "oto"; eklentinin web kuralının karşılığı). Görüntü yalnız aktarıcıya (127.0.0.1) gider.
final class MasaustuKanit {
    let masaustu: Masaustu; var sonIstek = "", oncekiKucuk: [UInt8]? = nil, degisti = false, sonOto = Date.distantPast, mesgul = false, izinYazildi = false
    init(_ m: Masaustu) { masaustu = m }
    func pencereBul(_ pid: pid_t, _ baslik: String) async -> SCWindow? {
        guard let ic = try? await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false) else {
            if !izinYazildi { izinYazildi = true; print("MASAÜSTÜ KANIT: ekran kaydı izni yok (Ekran ve Sistem Sesi Kaydı → Suflor Menü)") }
            return nil
        }
        // ekranda görünen, başlıklı pencereler önce (Teams'in gizli/başlıksız yardımcı pencereleri siyah görüntü verir — 12 Ekim denemesi)
        let hepsi = ic.windows.filter { $0.owningApplication?.processID == pid && $0.frame.width > 300 && $0.frame.height > 200 }
        let gorunen = hepsi.filter { $0.isOnScreen && !($0.title ?? "").isEmpty }, ws = gorunen.isEmpty ? hepsi : gorunen
        return ws.first { !baslik.isEmpty && ($0.title ?? "") == baslik } ?? ws.max { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height }
    }
    func goruntu(_ w: SCWindow, en: Int, boy: Int) async -> CGImage? {
        let c = SCStreamConfiguration(); c.width = en; c.height = boy; c.showsCursor = false
        return try? await SCScreenshotManager.captureImage(contentFilter: SCContentFilter(desktopIndependentWindow: w), configuration: c)
    }
    func tam(_ kaynak: String, istek idx: String?) {
        let (pid, baslik) = masaustu.pencere
        guard pid != 0, !mesgul else { return }
        mesgul = true
        Task {
            defer { self.mesgul = false }
            guard let w = await pencereBul(pid, baslik) else { return }
            let olcek = NSScreen.main?.backingScaleFactor ?? 2
            guard let im = await goruntu(w, en: Int(w.frame.width * olcek), boy: Int(w.frame.height * olcek)),
                  let png = NSBitmapImageRep(cgImage: im).representation(using: .png, properties: [:]) else { print("MASAÜSTÜ KANIT: görüntü alınamadı"); return }
            var g: [String: Any] = ["png": png.base64EncodedString(), "kaynak": kaynak, "w": Int(w.frame.width), "h": Int(w.frame.height)]
            if let i = idx { g["istek"] = i }
            istek("/kanit-masaustu", g, sure: 30) { v in if (v?["ok"] as? Bool) != true { print("MASAÜSTÜ KANIT: kaydedilmedi (\(v?["err"] as? String ?? "yanıt yok"))") } }
        }
    }
    func iste(_ ki: [String: Any]?) {  // şeridin uzun yoklamasındaki kanit_iste
        guard let ki = ki, let id = ki["id"] as? String, id != sonIstek, masaustu.toplantida else { return }
        sonIstek = id; tam(ki["kaynak"] as? String ?? "pano", istek: id)
    }
    func kucuk(_ im: CGImage) -> [UInt8] {
        var b = [UInt8](repeating: 0, count: 64 * 40)
        b.withUnsafeMutableBytes { p in
            if let cx = CGContext(data: p.baseAddress, width: 64, height: 40, bitsPerComponent: 8, bytesPerRow: 64, space: CGColorSpaceCreateDeviceGray(), bitmapInfo: 0) {
                cx.interpolationQuality = .low; cx.draw(im, in: CGRect(x: 0, y: 0, width: 64, height: 40))
            }
        }
        return b
    }
    func dongu() {
        Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            guard self.masaustu.toplantida, self.masaustu.paylasimVar, !self.mesgul else { self.oncekiKucuk = nil; self.degisti = false; return }
            let (pid, baslik) = self.masaustu.pencere
            self.mesgul = true
            Task {
                defer { self.mesgul = false }
                guard let w = await self.pencereBul(pid, baslik), let im = await self.goruntu(w, en: 256, boy: 160) else { return }
                let k = self.kucuk(im)
                let fark = self.oncekiKucuk.map { o in zip(o, k).reduce(0) { $0 + abs(Int($1.0) - Int($1.1)) } / k.count } ?? 255
                self.oncekiKucuk = k
                if fark > 6 { self.degisti = true; return }  // değişiyor: durulmasını bekle
                if self.degisti && Date().timeIntervalSince(self.sonOto) >= 10 {
                    self.degisti = false; self.sonOto = Date()
                    DispatchQueue.main.async { self.tam("oto", istek: nil) }
                }
            }
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
// Ekran Kaydı izni (masaüstü kanıt görüntüsü, v0.31.0): `--ekran-izni` izni sorar ve sonucu yazar (kurulumda ya da elle bir kez)
// Teşhis: `--kanit-dene <dosya.png>` → açık Teams/Zoom penceresinin görüntüsü dosyaya (ekran kaydı izni ve ScreenCaptureKit denemesi)
if let yol = arg("--kanit-dene") {
    _ = NSApplication.shared; let m = Masaustu(); let k = MasaustuKanit(m)
    guard let app = NSWorkspace.shared.runningApplications.first(where: { a in m.UYG.contains { $0.bundle == a.bundleIdentifier } }) else { print("toplantı uygulaması açık değil"); exit(1) }
    Task {
        if let w = await k.pencereBul(app.processIdentifier, ""), let im = await k.goruntu(w, en: Int(w.frame.width * 2), boy: Int(w.frame.height * 2)),
           let png = NSBitmapImageRep(cgImage: im).representation(using: .png, properties: [:]) {
            try? png.write(to: URL(fileURLWithPath: yol)); print("görüntü: \(im.width)×\(im.height) · \(w.title ?? "") · \(png.count / 1024) KB")
            let kc = k.kucuk(im); print("küçük ortalama: \(kc.reduce(0) { $0 + Int($1) } / kc.count)")
        } else { print("görüntü alınamadı") }
        exit(0)
    }
    NSApplication.shared.run()
}
if args.contains("--ekran-izni") { print("ekran izni:", CGPreflightScreenCaptureAccess() ? "var" : (CGRequestScreenCaptureAccess() ? "verildi" : "soruldu")); exit(0) }
let uyg = NSApplication.shared
let d = Uygulama()
uyg.delegate = d
uyg.setActivationPolicy(.accessory)
uyg.run()
