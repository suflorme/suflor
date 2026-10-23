# Suflor.me yapay zekâ sağlayıcısı: seçim, anahtar, yerel model (Faz 11 Aşama 4; tasarım ~/Desktop/Suflor/planlar/beyin-saglayici.md §3.7–3.8).
# İki yerden kullanılır: aktarıcıda bölüm (relay.py bolum("saglayici"): panodaki ⚙ Ayarlar → Genel → Yapay zekâ, /status beyin, Ollama'yı başlatma)
# ve kurulum.py'de modül (importlib; sihirbazın "Yapay zekâ bağla" adımı). Bu yüzden yalnız standart kütüphane; işlevler ayarı parametre alır, relay'in
# ortak durumuna yalnız en alttaki aktarıcı işlevleri (sg_bekci, sg_durum_view) dokunur. Seçimi okuyan aktarici/beyin.py secim()'dir; burası ayar.json'daki
# "beyin" sözlüğünü yazar/okur. Ayar: "beyin": {"varsayilan": {…}, "konus": {…}, "ceviri": {…}, "proje_karti": {…}} — yoksa Claude Code (bugünkü yol).
# Seçenekler: claude-code · gemini (Anahtar Zinciri öğesi ayar gemini_anahtar ya da suflor-gemini) · ozel (OpenAI uyumlu başka hizmet; ayar beyin_ozel =
# {adres, model}, anahtar öğesi suflor-ozel) · ollama (bu Mac'te yerel model, <ortak>/ollama; metin Mac'ten çıkmaz).
# Anahtar yalnız Anahtar Zinciri'nde: yazarken `security -i`'ye standart girdiden verilir (komut satırında/ps'te görünmez), dosyaya ve ayara yalnız öğe adı.
import hashlib, json, os, re, shutil, subprocess, tarfile, tempfile, threading, time, urllib.error, urllib.request

SG_SECENEK = ("claude-code", "gemini", "ozel", "ollama")
SG_ISLER = ("konus", "ceviri", "proje_karti")  # panoda iş başına; telaffuz ve brifing varsayılanı izler; toplantı oturumu Claude Code'da kalır (K3)
SG_GEMINI_MODEL = "gemini-3.8-flash"  # Adım 1 gerçek denemesi 4/4, effort low ilk ses ortanca ~5,7 sn
SG_OZEL_OGE = "suflor-ozel"
SG_OLLAMA_MODEL = "qwen3.5:4b-q4_K_M"  # 3,3 GB; araç çağırır, çok dilli. Türkçe aramada zayıf (Adım 1: 0/4) — yalnız yedek
SG_OLLAMA_MODEL_GB = 3.3
# Resmî sürüm, sabit: adres + SHA-256 (sürümün sha256sum.txt'si) + Apple imzası (Ollama'nın ekip kimliği). Yalnız komut satırı aracı: Ollama.app kurulmaz,
# Mac açılışında kendiliğinden başlamaz; sunucuyu aktarıcı yalnız ayar onu gösterirken açar.
SG_OLLAMA = {"surum": "v0.40.9", "url": "https://github.com/ollama/ollama/releases/download/v0.40.9/ollama-darwin.tgz",
             "sha256": "cdfaee591d3ba7753e1bb4ae28be228ef7488199f263b7f202e0eddc900c08f4", "takim": "3MU9H2V9Y9", "mb": 181}
SG_OLLAMA_BAGLAM = "32768"  # varsayılan 4096'da Konuş istemi (~34 bin belirteç) kesilir
SG_HAZIR_ADRES = {"gemini": "https://generativelanguage.googleapis.com/v1beta/openai", "openai": "https://api.openai.com/v1"}
_SG_ONBELLEK = {}

def sg_ollama_port(ayar):
    try: return int(ayar.get("ollama_port") or 11434)
    except (TypeError, ValueError): return 11434
# beyin.py secim() varsayılanla iş sözlüğünü birleştirir (iş üstte): iş başına başka sağlayıcı seçilince varsayılanın model/adres/sağlayıcısı sızmasın diye
# her profil bütün alanları taşır (kullanılmayan None; claude-code'da model None → eski anahtar konus_model … ya da bugünkü varsayılan).
SG_ALANLAR = ("model", "saglayici", "adres", "anahtar", "effort", "fiyat")
def sg_profil(ad, ayar):  # seçenek adı → beyin.py'nin okuduğu sözlük (None: kurulamaz)
    if ad == "claude-code": p = {"tur": "claude-code"}
    elif ad == "gemini": p = {"tur": "openai-uyumlu", "saglayici": "gemini", "model": SG_GEMINI_MODEL, "effort": "low"}
    elif ad == "ozel":
        o = ayar.get("beyin_ozel") if isinstance(ayar.get("beyin_ozel"), dict) else {}
        if not o.get("adres") or not o.get("model"): return None
        p = {"tur": "openai-uyumlu", "adres": str(o["adres"]).rstrip("/"), "model": str(o["model"]), "anahtar": SG_OZEL_OGE}
    elif ad == "ollama":
        p = {"tur": "openai-uyumlu", "saglayici": "ollama", "model": str(ayar.get("ollama_model") or SG_OLLAMA_MODEL), "effort": "none"}
        if sg_ollama_port(ayar) != 11434: p["adres"] = f"http://127.0.0.1:{sg_ollama_port(ayar)}/v1"
    else: return None
    return dict({k: None for k in SG_ALANLAR}, **p)
def sg_ad(d):  # beyin sözlüğü → seçenek adı ("" = yok/varsayılanı izler)
    if not isinstance(d, dict) or not d.get("tur"): return ""
    if d.get("tur") != "openai-uyumlu": return "claude-code"
    sg, adres = str(d.get("saglayici") or "").lower(), str(d.get("adres") or "")
    if sg == "gemini": return "gemini"
    if sg == "ollama" or re.match(r"^http://(127\.0\.0\.1|localhost):\d+/v1/?$", adres) and ":1234" not in adres: return "ollama"
    return "ozel"
def sg_secim(ayar):  # → {"varsayilan": ad, "konus": ad ya da "" …} (panodaki değerler)
    b = ayar.get("beyin") if isinstance(ayar.get("beyin"), dict) else {}
    v = {"varsayilan": sg_ad(b.get("varsayilan")) or "claude-code"}
    for i in SG_ISLER: v[i] = sg_ad(b.get(i))
    return v
def sg_etkin(ayar):  # her işin gerçekte kullandığı seçenek (iş boşsa varsayılan)
    s = sg_secim(ayar); return {i: s[i] or s["varsayilan"] for i in SG_ISLER}
def sg_yaz(ayar, degisen):  # degisen: {"varsayilan"|iş: ad ya da ""} → ayar sözlüğünü yerinde değiştirir; hata metni ya da None
    b = dict(ayar.get("beyin")) if isinstance(ayar.get("beyin"), dict) else {}
    for k, ad in degisen.items():
        if k != "varsayilan" and k not in SG_ISLER: return f"bilinmeyen iş: {k}"
        if ad == "" and k != "varsayilan": b.pop(k, None); continue
        if ad not in SG_SECENEK: return f"bilinmeyen seçenek: {ad}"
        if sg_ad(b.get(k)) == ad: continue  # aynı seçenek: elle yazılmış model/effort korunur
        if k == "varsayilan" and ad == "claude-code": b.pop(k, None); continue
        p = sg_profil(ad, ayar)
        if p is None: return "OpenAI uyumlu hizmet tanımlı değil (kurulum sihirbazında adres ve model)"
        b[k] = p
    if b: ayar["beyin"] = b
    else: ayar.pop("beyin", None)
    return None

# --- Anahtar Zinciri ----------------------------------------------------------------------------------------------------------------
def sg_oge(ad, ayar): return str(ayar.get("gemini_anahtar") or "suflor-gemini") if ad == "gemini" else SG_OZEL_OGE
def sg_anahtar_var(oge):  # yalnız öğe var mı (anahtar okunmaz); 60 sn önbellek. Deneme: SUFLOR_TEST_BEYIN_ANAHTAR (beyin.py ile aynı)
    if os.environ.get("SUFLOR_TEST_BEYIN_ANAHTAR") is not None: return bool(os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"])
    if not re.match(r"^[A-Za-z0-9._-]{1,64}$", str(oge or "")): return False
    o = _SG_ONBELLEK.get(("an", oge))
    if o and time.time() - o[0] < 60: return o[1]
    try: v = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", oge], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired): v = False
    _SG_ONBELLEK[("an", oge)] = (time.time(), v); return v
SG_ANAHTAR_RX = re.compile(r"^[A-Za-z0-9._\-]{16,256}$")  # API anahtarları bu harflerden; security -i alıntısında kaçış gerekmez
def sg_anahtar_yaz(oge, anahtar):  # → None ya da hata metni. Anahtar standart girdiden (komut satırında değil); varsa güncellenir (-U)
    anahtar = str(anahtar or "").strip()
    if not SG_ANAHTAR_RX.match(anahtar): return "anahtar biçimi tanınmadı (harf, rakam, - _ . ; en az 16 karakter)"
    if not re.match(r"^[A-Za-z0-9._-]{1,64}$", str(oge or "")): return "öğe adı geçersiz"
    _SG_ONBELLEK.pop(("an", oge), None)
    if os.environ.get("SUFLOR_TEST_BEYIN_ANAHTAR") is not None: return None  # deneme: Anahtar Zinciri'ne dokunulmaz
    try: r = subprocess.run(["/usr/bin/security", "-i"], input=f'add-generic-password -U -a suflor -s {oge} -l "Suflor.me {oge}" -w "{anahtar}"\n',
                            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e: return e.__class__.__name__
    return None if sg_anahtar_var(oge) else ("Anahtar Zinciri'ne yazılamadı" + (f": {r.stderr.strip()[:120]}" if r.stderr.strip() else ""))
def sg_anahtar_oku(oge):
    if os.environ.get("SUFLOR_TEST_BEYIN_ANAHTAR") is not None: return os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"]
    try: return subprocess.run(["/usr/bin/security", "find-generic-password", "-s", oge, "-w"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): return ""
def sg_anahtar_dene(adres, oge):  # hizmetin model listesini anahtarla ister (metin gitmez, ücretsiz) → ("iyi"|"anahtar"|"ag", ayrıntı)
    adres = os.environ.get("SUFLOR_TEST_BEYIN_ADRES") or adres
    an = sg_anahtar_oku(oge)
    if not an: return "anahtar", "Anahtar Zinciri'nde yok"
    if not re.match(r"^https://[^/?#@\s]+(/[^?#@\s]*)?$", str(adres or "")) and not re.match(r"^http://127\.0\.0\.1:\d+(/[^?#@\s]*)?$", str(adres or "")):
        return "ag", "adres https olmalı"
    try:
        urllib.request.urlopen(urllib.request.Request(adres.rstrip("/") + "/models", headers={"Authorization": "Bearer " + an}), timeout=15).read(2000)
        return "iyi", ""
    except urllib.error.HTTPError as e: return ("anahtar" if e.code in (400, 401, 403) else "ag"), f"HTTP {e.code}"
    except Exception as e: return "ag", e.__class__.__name__

# --- Ollama (yerel model) -------------------------------------------------------------------------------------------------------------
def sg_ollama_yol(ortak): return os.path.join(ortak, "ollama", "ollama")
def sg_ollama_kurulu(ortak): p = sg_ollama_yol(ortak); return os.path.isfile(p) and os.access(p, os.X_OK)
def sg_ollama_model_var(ortak, model=SG_OLLAMA_MODEL):  # indirilmiş modelin bildirim dosyası (sunucu açık olmasa da)
    ad, _, etiket = model.partition(":")
    return os.path.isfile(os.path.join(ortak, "ollama", "modeller", "manifests", "registry.ollama.ai", "library", ad, etiket or "latest"))
def sg_ollama_ortam(ortak, port=11434):
    return dict(os.environ, OLLAMA_MODELS=os.path.join(ortak, "ollama", "modeller"), OLLAMA_HOST=f"127.0.0.1:{port}", OLLAMA_CONTEXT_LENGTH=SG_OLLAMA_BAGLAM,
                OLLAMA_NOHISTORY="1")
def sg_ollama_acik(port=11434, zaman=1.0):
    try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=zaman).read(200); return True
    except Exception: return False
def sg_ollama_baslat(ortak, port=11434, gunluk=None):  # → Popen; kendi oturumunda (aktarıcı yeniden başlasa da sürer, sonraki aktarıcı açık bulur)
    return subprocess.Popen([sg_ollama_yol(ortak), "serve"], env=sg_ollama_ortam(ortak, port), stdin=subprocess.DEVNULL,
                            stdout=open(gunluk, "a") if gunluk else subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)
def sg_ollama_kur(ortak, durum_yol, model=SG_OLLAMA_MODEL, port=11434):  # sihirbazın arka plan işi (kurulum.py ollama): araç + model; ilerleme durum_yol'a
    def yaz(**d):
        d["t"] = time.time(); tmp = durum_yol + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, durum_yol)
    toplam = SG_OLLAMA["mb"] / 1024 + SG_OLLAMA_MODEL_GB
    kok = os.path.join(ortak, "ollama"); os.makedirs(kok, exist_ok=True)
    try:
        if not sg_ollama_kurulu(ortak):
            url = os.environ.get("SUFLOR_TEST_OLLAMA_URL") or SG_OLLAMA["url"]; sha = os.environ.get("SUFLOR_TEST_OLLAMA_SHA") or SG_OLLAMA["sha256"]
            gec = os.path.join(kok, ".indirme.tgz"); h = hashlib.sha256(); n = 0
            with urllib.request.urlopen(url, timeout=60) as r, open(gec, "wb") as f:
                boy = int(r.headers.get("Content-Length") or SG_OLLAMA["mb"] * 2 ** 20)
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b); h.update(b); n += len(b)
                    yaz(durum="iniyor", evre="arac", yuzde=min(99, round(100 * n / 2 ** 30 / toplam)), mb=round(n / 2 ** 20))
            if h.hexdigest() != sha: os.remove(gec); return yaz(durum="hata", mesaj="indirilen dosyanın SHA-256'sı resmî sürümle uyuşmuyor")
            with tarfile.open(gec) as t:
                for m in t.getmembers():  # yalnız düz dosya/bağ, klasör dışına çıkan yol yok
                    if m.name.startswith(("/", "..")) or "/../" in m.name or not (m.isfile() or m.issym() or m.isdir()): os.remove(gec); return yaz(durum="hata", mesaj=f"arşivde beklenmeyen öğe: {m.name[:80]}")
                t.extractall(kok)
            os.remove(gec)
            if not os.environ.get("SUFLOR_TEST_OLLAMA_URL"):
                v = subprocess.run(["/usr/bin/codesign", "--verify", "--strict", sg_ollama_yol(ortak)], capture_output=True, text=True, timeout=60)
                d = subprocess.run(["/usr/bin/codesign", "-dv", sg_ollama_yol(ortak)], capture_output=True, text=True, timeout=60)
                if v.returncode or f"TeamIdentifier={SG_OLLAMA['takim']}" not in (d.stderr or ""):
                    os.remove(sg_ollama_yol(ortak)); return yaz(durum="hata", mesaj="Ollama'nın imzası doğrulanamadı")
        if sg_ollama_model_var(ortak, model): return yaz(durum="hazir", yuzde=100)
        p = None
        if not sg_ollama_acik(port): p = sg_ollama_baslat(ortak, port)
        for _ in range(60):
            if sg_ollama_acik(port): break
            time.sleep(0.5)
        try:
            ilk = SG_OLLAMA["mb"] / 1024
            r = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/pull", data=json.dumps({"model": model, "stream": True}).encode(),
                                                              headers={"Content-Type": "application/json"}), timeout=600)
            for satir in r:
                try: o = json.loads(satir)
                except ValueError: continue
                if o.get("error"): return yaz(durum="hata", mesaj=str(o["error"])[:200])
                if o.get("total") and o.get("completed") is not None and o["total"] > 50 * 2 ** 20:  # büyük katman: ağırlıklar
                    yaz(durum="iniyor", evre="model", yuzde=min(99, round(100 * (ilk + o["completed"] / 2 ** 30) / toplam)))
                if o.get("status") == "success": break
        finally:
            if p:
                p.terminate()
                try: p.wait(10)
                except subprocess.TimeoutExpired: p.kill()
        return yaz(durum="hazir", yuzde=100) if sg_ollama_model_var(ortak, model) else yaz(durum="hata", mesaj="model indirilemedi")
    except Exception as e: return yaz(durum="hata", mesaj=f"{e.__class__.__name__}: {str(e)[:160]}")

# --- sağlık: seçilen her sağlayıcı için tek satır (panoda Ayarlar, tc saglik, sihirbaz) --------------------------------------------------
def sg_saglik(ayar, claude_ok=None):  # → [{"ad", "ok", "metin", "metin_en", "oneri"}]; claude_ok: aktarıcının Claude Code denemesi (None = bilinmiyor)
    ortak = os.path.expanduser(str(ayar.get("ortak") or "/Users/Shared/Suflor")); out = []
    for ad in sorted(set(sg_etkin(ayar).values()), key=SG_SECENEK.index):
        if ad == "claude-code":
            ok = claude_ok is not False
            out.append({"ad": ad, "ok": ok, "metin": "Claude Code" + ("" if ok else ": kısa deneme olmadı"), "metin_en": "Claude Code" + ("" if ok else ": the short test failed"),
                        "oneri": "Terminal'de claude açıp girişi denetle"})
        elif ad in ("gemini", "ozel"):
            oge = sg_oge(ad, ayar); var = sg_anahtar_var(oge); ad_tr, ad_en = ("Gemini", "Gemini") if ad == "gemini" else ("OpenAI uyumlu hizmet", "OpenAI-compatible service")
            out.append({"ad": ad, "ok": var, "metin": ad_tr + (" anahtarı Anahtar Zinciri'nde" if var else f": anahtar yok ({oge})"),
                        "metin_en": ad_en + (" key is in the Keychain" if var else f": no key ({oge})"), "oneri": "kurulum sihirbazındaki Yapay zekâ adımından anahtarı gir"})
        elif ad == "ollama":
            port = sg_ollama_port(ayar); m = str(ayar.get("ollama_model") or SG_OLLAMA_MODEL)
            k, mv, ac = sg_ollama_kurulu(ortak), sg_ollama_model_var(ortak, m), sg_ollama_acik(port, 0.5)
            out.append({"ad": ad, "ok": k and mv, "metin": "yerel model (Ollama) " + ("hazır" + (" · çalışıyor" if ac else " · gerekince açılır") if k and mv else "kurulu değil" if not k else f"modeli ({m}) inmemiş"),
                        "metin_en": "local model (Ollama) " + ("ready" + (" · running" if ac else " · starts when needed") if k and mv else "not installed" if not k else f"model ({m}) not downloaded"),
                        "oneri": "kurulum sihirbazındaki Yapay zekâ adımından yerel modeli kur"})
    return out

# --- aktarıcı (bölüm olarak): Ollama'yı yalnız ayar gösterirken aç, ayar değişince kapat --------------------------------------------------
SG_OLLAMA_P = {"p": None}
def sg_ollama_gerekli(ayar): return "ollama" in sg_etkin(ayar).values()
def sg_bak():  # 30 sn'de bir (sg_bekci) ve panodan ayar değişince
    ortak = AYAR["ortak"]; port = sg_ollama_port(AYAR); p = SG_OLLAMA_P["p"]
    if sg_ollama_gerekli(AYAR):
        if (p is None or p.poll() is not None) and sg_ollama_kurulu(ortak) and not sg_ollama_acik(port):
            if deneme_aktarici() and not os.environ.get("SUFLOR_TEST_OLLAMA"): return
            SG_OLLAMA_P["p"] = sg_ollama_baslat(ortak, port, os.path.join(BASE, "ollama.log")); print(f"OLLAMA: başlatıldı (127.0.0.1:{port}, bağlam {SG_OLLAMA_BAGLAM})")
    elif p is not None and p.poll() is None:
        p.terminate(); SG_OLLAMA_P["p"] = None; print("OLLAMA: ayar artık yerel modeli göstermiyor — kapatıldı")
def sg_bekci():
    while True:
        try: sg_bak()
        except Exception as e: print(f"OLLAMA: denetim hata ({e.__class__.__name__})")
        time.sleep(30)
def sg_claude_ok():  # Claude Code yoksa False; varsa aktarıcının kısa denemesi (claude_surum_bak; None = henüz denenmedi)
    return False if not claude_yolu() else (STATE.get("claude_saglik") or {}).get("ok")
def sg_ayar_view():  # panodaki ⚙ Ayarlar: hangi seçenek kullanılabilir + sağlık satırları
    o = AYAR.get("beyin_ozel") if isinstance(AYAR.get("beyin_ozel"), dict) else {}
    return {"gemini": sg_anahtar_var(sg_oge("gemini", AYAR)), "ozel": bool(o.get("adres") and o.get("model")) and sg_anahtar_var(SG_OZEL_OGE),
            "ollama": sg_ollama_kurulu(AYAR["ortak"]) and sg_ollama_model_var(AYAR["ortak"], str(AYAR.get("ollama_model") or SG_OLLAMA_MODEL)),
            "saglik": sg_durum_view()["saglik"]}
_SG_DURUM = {"t": 0.0, "v": None}
def sg_durum_view():  # /status beyin (15 sn önbellek; pano saniyede bir yoklar): işlerin seçeneği + sağlık — tc saglik ve sihirbaz buradan okur
    if time.time() - _SG_DURUM["t"] > 15: _SG_DURUM.update(t=time.time(), v={"etkin": sg_etkin(AYAR), "saglik": sg_saglik(AYAR, sg_claude_ok())})
    return _SG_DURUM["v"]
