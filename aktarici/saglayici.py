# Suflor.me yapay zekâ sağlayıcısı: seçim, anahtar (Faz 11 Aşama 4; tasarım ~/Desktop/Suflor/planlar/beyin-saglayici.md §3.7–3.8).
# İki yerden kullanılır: aktarıcıda bölüm (relay.py bolum("saglayici"): panodaki ⚙ Ayarlar → Genel → Yapay zekâ, /status beyin)
# ve kurulum.py'de modül (importlib; sihirbazın "Yapay zekâ bağla" adımı). Bu yüzden yalnız standart kütüphane; işlevler ayarı parametre alır, relay'in
# ortak durumuna yalnız en alttaki aktarıcı işlevleri (sg_bekci, sg_durum_view) dokunur. Seçimi okuyan aktarici/beyin.py secim()'dir; burası ayar.json'daki
# "beyin" sözlüğünü yazar/okur. Ayar: "beyin": {"varsayilan": {…}, "konus": {…}, "ceviri": {…}, "proje_karti": {…}} — yoksa Claude Code (bugünkü yol).
# Seçenekler: claude-code · gemini (Anahtar Zinciri öğesi ayar gemini_anahtar ya da suflor-gemini) · ozel (OpenAI uyumlu başka hizmet; ayar beyin_ozel =
# {adres, model}, anahtar öğesi suflor-ozel).
# Anahtar yalnız Anahtar Zinciri'nde: yazarken `security -i`'ye standart girdiden verilir (komut satırında/ps'te görünmez), dosyaya ve ayara yalnız öğe adı.
import json, os, re, subprocess, time, urllib.error, urllib.request

SG_SECENEK = ("claude-code", "gemini", "ozel")
SG_ISLER = ("konus", "ceviri", "proje_karti", "prova")  # panoda iş başına; telaffuz ve brifing varsayılanı izler; toplantı oturumu Claude Code'da kalır (K3)
SG_GEMINI_MODEL = "gemini-3.8-flash"  # Adım 1 gerçek denemesi 4/4, effort low ilk ses ortanca ~5,7 sn
SG_OZEL_OGE = "suflor-ozel"
SG_HAZIR_ADRES = {"gemini": "https://generativelanguage.googleapis.com/v1beta/openai", "openai": "https://api.openai.com/v1"}
_SG_ONBELLEK = {}

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
    else: return None
    return dict({k: None for k in SG_ALANLAR}, **p)
def sg_ad(d):  # beyin sözlüğü → seçenek adı ("" = yok/varsayılanı izler)
    if not isinstance(d, dict) or not d.get("tur"): return ""
    if d.get("tur") != "openai-uyumlu": return "claude-code"
    sg, adres = str(d.get("saglayici") or "").lower(), str(d.get("adres") or "")
    if sg == "gemini": return "gemini"
    if sg == "ollama": return "claude-code"  # iptal edilen yerel model seçeneği (v0.178.0): eski ayar Claude Code'a düşer
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
    return out

# --- aktarıcı (bölüm olarak) ---------------------------------------------------------------------------------------------------------------
def sg_claude_ok():  # Claude Code yoksa False; varsa aktarıcının kısa denemesi (claude_surum_bak; None = henüz denenmedi)
    return False if not claude_yolu() else (STATE.get("claude_saglik") or {}).get("ok")
def sg_ayar_view():  # panodaki ⚙ Ayarlar: hangi seçenek kullanılabilir + sağlık satırları
    o = AYAR.get("beyin_ozel") if isinstance(AYAR.get("beyin_ozel"), dict) else {}
    return {"gemini": sg_anahtar_var(sg_oge("gemini", AYAR)), "ozel": bool(o.get("adres") and o.get("model")) and sg_anahtar_var(SG_OZEL_OGE),
            "saglik": sg_durum_view()["saglik"]}
_SG_DURUM = {"t": 0.0, "v": None}
def sg_durum_view():  # /status beyin (15 sn önbellek; pano saniyede bir yoklar): işlerin seçeneği + sağlık — tc saglik ve sihirbaz buradan okur
    if time.time() - _SG_DURUM["t"] > 15: _SG_DURUM.update(t=time.time(), v={"etkin": sg_etkin(AYAR), "saglik": sg_saglik(AYAR, sg_claude_ok())})
    return _SG_DURUM["v"]
