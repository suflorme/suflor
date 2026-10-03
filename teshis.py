#!/usr/bin/env python3
# Suflor.me teknik teşhis (v0.12.0, beta). Kural: BAĞLAM BİLGİSİ Mac DIŞINA ÇIKMAZ — döküm, kişi/toplantı adı, kart metni,
# not, takvim, proje belgesi, dosya adı gitmez. Dışarı yalnız geliştirme için teknik bilgi gider: sürüm, donanım, sayılar,
# gecikmeler, hata türü ve kodumuzdaki yeri.
# Güvence iki katmanlı: (1) paketler yalnız izinli alanlarla kurulur; (2) gönderimden hemen önce `temizle()` her metin
# değerini sözlük süzgecinden geçirir — Suflor'un kendi günlük/olay metinlerinde geçmeyen her kelime "…" olur, yol ve dosya
# adı "<yol>", tırnak içi "…". Tek istisna kullanıcının panodaki geri bildirim kutusuna kendisi yazdığı metin (gönderilmeden
# önce gösterilir). Gönderim yalnız ayarda `teshis: true` ise (kurulumda sorulur); panodan elle geri bildirim her zaman.
# Gönderilen her paketin kopyası <uygulama>/teshis/gonderilen/ altında durur: kullanıcı neyin gittiğini görebilir.
#   python3 teshis.py --sozluk <kod klasörü>   sözlüğü üret (aktarici-kur.command çağırır)
#   python3 teshis.py --dene "<satır>"         süzgeç denemesi
import json, os, re, sys, time, uuid, glob, threading, platform, subprocess, datetime, urllib.request

SURUM_SEMA = 1
ADRES_VARSAYILAN = "https://suflor-geri-bildirim.wg9w7njmgz.workers.dev/"  # Worker (sunucu/); ayar `teshis_adres` geçersiz kılar
BETA_ANAHTAR = "suflor-beta-1"  # gizli değil: yalnız rastgele isteği ayırmak için
KOD_DOSYALARI = ("relay.py", "toplanti-claude.py", "whisper-isci.py", "ses-isci.py", "baglam.py", "kurulum.py", "teshis.py",
                 "content.js", "platform-teams.js", "background.js", "offscreen.js", "mic-main.js", "popup.js", "launcher.js")
_BURASI = os.path.dirname(os.path.abspath(__file__))
SOZLUK_DOSYA = os.path.join(_BURASI, "teshis-sozluk.txt")

# ---------- sözlük: yalnız kodun kendi günlük/olay metinleri + hata dili ----------
# Python'da print(...) satırları, JS'de olay(...)/kanitOlay(...) satırlarındaki dizgelerin sabit kısımları ({...} hariç).
TABAN = """traceback most recent call last file line in error exception oserror ioerror valueerror keyerror typeerror indexerror
attributeerror runtimeerror timeouterror connectionerror connectionrefusederror connectionreseterror brokenpipeerror
filenotfounderror permissionerror jsondecodeerror unicodedecodeerror memoryerror recursionerror zerodivisionerror
nameerror importerror modulenotfounderror notimplementederror assertionerror stopiteration systemexit keyboardinterrupt
subprocesserror calledprocesserror timeoutexpired urlerror httperror errno no space left on device such or directory
not found permission denied connection refused reset by peer broken pipe timed out timeout invalid expecting value
property name enclosed double quotes char column codec can't decode byte position start unexpected end of data
during handling the above another occurred exception thread ignored started by killed signal exit code returned
non-zero status memory out cannot read write open closed is a an to from with for on at none null true false
undefined failed fetch network aborted the of and hidden visible arka-plan zamanlayici yurutucu katilimci dinleyici
tr en karisik popup kisayol teams meet zoom""".split()
_KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû][A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû'_-]*")
def _kucuk(s): return s.replace("I", "ı").replace("İ", "i").lower()
def _dizgeler(satir):
    for m in re.finditer(r'''(?:f|r|rf|fr)?("([^"\\]|\\.)*"|'([^'\\]|\\.)*'|`([^`\\]|\\.)*`)''', satir):
        yield re.sub(r"\{[^{}]*\}|\$\{[^{}]*\}", " ", m.group(1)[1:-1])
def sozluk_uret(kod):
    s = set(TABAN)
    for ad in KOD_DOSYALARI:
        try: satirlar = open(os.path.join(kod, ad), encoding="utf-8").read().splitlines()
        except OSError: continue
        py = ad.endswith(".py")
        for l in satirlar:
            if (py and "print(" in l) or (not py and re.search(r"\bolay\(|kanitOlay\(|tur: ?\"", l)):
                for d in _dizgeler(l): s.update(_kucuk(w) for w in _KELIME.findall(d))
    return sorted(w for w in s if len(w) > 1 or w in ("a",))
_SOZ = None
def sozluk():
    global _SOZ
    if _SOZ is None:
        try: _SOZ = set(open(SOZLUK_DOSYA, encoding="utf-8").read().split())
        except OSError: _SOZ = set(sozluk_uret(_BURASI))
    return _SOZ

# ---------- süzgeç ----------
# Önce bilinen bağlam alanları açıkça atılır (sözlük katmanından bağımsız): konu, toplantı başlığı, söylenen cümle, dosya adı.
BAGLAM_ALANI = [(re.compile(r"(BAŞLAT: ).*?( · rol|$)"), r"\1<konu>\2"),
                (re.compile(r"(açıldı|öne getirildi|kapandı)( — ).*?( · |$)"), r"\1\2<başlık>\3"),
                (re.compile(r"(ses komutu — ).*"), r"\1<cümle>"),
                (re.compile(r"(Durum kuruldu: |kuruldu: |dosya(?:sına|sı)? )\S+"), r"\1<dosya>"),
                (re.compile(r"(meeting|title|baslik|konu|speaker|text|note|not)(\"?\s*[:=]\s*)\"[^\"]*\""), r"\1\2…")]
_YOL = re.compile(r"""(?:~|/|[A-Za-z]:\\)[^\s'",)]*|[^\s'",(]*\.(?:md|jsonl|json|png|txt|log|wav|py|js|html|xlsx|docx|pdf|vtt)\b""")
_TIRNAK = re.compile(r"\"[^\"]*\"|“[^”]*”|'[^'\s][^']*'")
_URL = re.compile(r"https?://\S+")
_SAYI = re.compile(r"^[v]?\d[\d.,:%+-]*(sn|dk|ms|kb|mb|gb|s)?$", re.I)
# v0.12.3 (güvenlik denetimi D1): boşluk/tire/nokta ile ayrılmış rakam dizisi (telefon, kart, IBAN, kimlik no) toplam 7+
# rakamsa "N". Saat (iki nokta) ve ISO tarih (2026-10-03) ayraç sayılmaz; sürüm (0.12.2) ve IP 7 rakamın altında kalır.
_RAKAM_DIZI = re.compile(r"(?<![\w.-])\d+(?:[ .-]\d+)+(?![\w:])")
_ISO_TARIH = re.compile(r"\d{4}-\d\d-\d\d")
def _rakam_dizi(m):
    d = m.group(0)
    if _ISO_TARIH.fullmatch(d) or sum(c.isdigit() for c in d) < 7: return d
    return "<N>"
def sade(metin, en_cok=300):
    """Bir metin satırını teknik iskeletine indirger: sözlükte olmayan kelime "…", yol "<yol>", tırnak içi "…"."""
    if metin is None: return None
    t = str(metin).replace("\n", " ")
    for k, y in BAGLAM_ALANI: t = k.sub(y, t)
    t = _URL.sub(lambda m: "<adres:yerel>" if re.match(r"https?://(127\.0\.0\.1|localhost)", m.group(0)) else "<adres>", t)
    def yol(m):
        b = os.path.basename(m.group(0).rstrip("/"))
        return b if b in KOD_DOSYALARI else "<yol>"
    t = _YOL.sub(yol, t); t = _TIRNAK.sub("…", t); t = _RAKAM_DIZI.sub(_rakam_dizi, t)
    soz = sozluk(); cikti = []
    for parca in re.split(r"(\s+)", t):
        if not parca or parca.isspace(): cikti.append(parca); continue
        if _SAYI.match(parca.strip("(),;:")): cikti.append(re.sub(r"\d{5,}", "N", parca)); continue  # ölçü/sürüm kalır; 5+ hane (kod, kimlik) gitmez
        def kelime(m):
            w = m.group(0)
            return w if (_kucuk(w) in soz or _kucuk(w).strip("'-_") in soz or w in KOD_DOSYALARI) else "…"
        p = re.sub(r"<[^<>\s]+>|" + _KELIME.pattern, lambda m: m.group(0) if m.group(0).startswith("<") else kelime(m), parca)
        if "…" in p and re.search(r"\d", p): p = "…"  # bilinmeyen kelimeye yapışık rakam (şifre, kod, kimlik parçası) gitmez
        else: p = re.sub(r"\d{5,}", "N", p)  # 5+ hane: zaman damgası, doğrulama kodu, kimlik — gitmez
        cikti.append(p)
    t = re.sub(r"…(\s*…)+", "…", "".join(cikti)).replace("<N>", "N")
    return re.sub(r"\s+", " ", t).strip()[:en_cok]

# ---------- izin listesi doğrulaması (gönderimden hemen önce, her pakete) ----------
# Bu anahtarların değerleri yapılandırılmış ve kalıba uyarsa olduğu gibi kalır; gerisi sade()'den geçer.
KALIP = {"kurulum": r"[0-9a-f]{12}", "surum": r"v?\d{1,3}(\.\d{1,4}){0,3}|\?", "eklenti": r"v?\d{1,3}(\.\d{1,4}){0,3}|\?",
         "kod": r"v?\d{1,3}(\.\d{1,4}){0,3}|\?", "model": r"[A-Za-z]{2,16}\d{0,3}(,\d{1,3})?|\?", "macos": r"[\d.]{1,12}|\?",
         "python": r"\d{1,2}\.\d{1,2}\.\d{1,3}[a-z0-9]{0,4}", "zaman": r"[\d:T+.-]{10,32}",
         "claude_model": r"(claude-)?(opus|sonnet|haiku|fable)[a-z0-9.-]{0,30}|varsayilan|default|\?",
         "islev": r"[\w<>.-]{1,40}", "parmak": r"[0-9a-f]{12}", "toplanti_kimlik": r"[0-9a-f]{12}", "isim": r"[A-Za-z_]\w{0,40}",
         "isabet": r"\d{1,4}/\d{1,4}"}  # v0.12.3: kart isabeti "yapıldı/(yapıldı+geçildi)" — eskiden "/1" yol sanılıyordu
# v0.12.3 (D1c): kalıba uyan serbest küçük harfli değer ("gizli_proje_kartal") geçmesin — bu alanlar yalnız kodda gerçekten
# üretilen değerleri alır (relay.py, toplanti-claude.py, content.js taranarak toplandı); bilinmeyen değer "?". Yeni değer
# üreten kod yazınca buraya ekle.
_DURUMLAR = {"kapali", "yukleniyor", "hazir", "yok", "hata", "zaman_asimi", "bekliyor", "ok", "izin_yok"}
SABIT = {"tur": {"hata", "sorun", "toplanti_sonu", "geri_bildirim"},
         "kategori": {"whisper", "ses_modeli", "disk", "eklenti", "nabiz", "takvim", "baslat", "sozluk"},  # relay.py SORUN_RX
         "kaynak": {"aktarici", "claude"}, "platform": {"teams", "meet", "zoom"}, "rol": {"yurutucu", "katilimci", "dinleyici"},
         "dil": {"tr", "en", "karisik"}, "arayuz": {"tr", "en"}, "durum": _DURUMLAR, "whisper": _DURUMLAR, "ses_modeli": _DURUMLAR,
         "sebep": set(),  # bugün üreten kod yok
         "dosya": set(KOD_DOSYALARI) | {"<kütüphane>"}}
# v0.12.3 (D1b): sözlük anahtarları da süzülür. Anahtar kalıba uymalı; sayım sözlüklerinin anahtarı veriden geldiği için
# (kaynak, kanal, kart türü, dönüş, karne boyutu) yalnız bilinen değerler. Uymayan anahtar "?<sıra>" olur (değer yine süzülür).
ANAHTAR = re.compile(r"[a-z_][a-z0-9_]{0,39}")
ANAHTAR_CEVIR = {"?": "bilinmeyen", "gündem": "gundem", "açık sorular": "acik_sorular", "konuşma payı": "konusma_payi", "takip sahipli": "takip_sahipli"}
SAYIM = {"kaynak": {"transcript", "captions", "whisper", "bilinmeyen"}, "kanal": {"ben", "karsi"},
         "tur": {"sor", "belirt", "deginme", "dikkat", "cevap", "bilgi", "duygu"},  # relay.py CARD_KINDS
         "donus": {"acik", "yenilendi", "yapildi", "okundu", "gecildi"},
         "boyut": {"gundem", "zaman", "acik_sorular", "konusma_payi", "takip_sahipli"}}
SERBEST = {"kullanici_metni"}  # kullanıcının panoda yazdığı metin (gönderilmeden önce gösterilir); v0.12.3: gozlem artık sade()'den geçer
def _anahtar(k, ust, i):
    k = ANAHTAR_CEVIR.get(str(k), str(k))
    izin = SAYIM.get(ust)
    return k if (k in izin if izin is not None else ANAHTAR.fullmatch(k)) else f"?{i}"
def temizle(x, anahtar=None):
    if isinstance(x, dict): return {_anahtar(k, anahtar, i): temizle(v, _anahtar(k, anahtar, i)) for i, (k, v) in enumerate(list(x.items())[:80], 1)}
    if isinstance(x, list): return [temizle(v, anahtar) for v in x[:200]]
    if isinstance(x, bool) or x is None or isinstance(x, (int, float)): return x
    s = str(x)
    if anahtar in SERBEST: return s[:4000]
    if anahtar == "gozlem": return sade(s, 3000)  # v0.12.3 (O2): Claude'un toplantı sonu gözlemi — ad/içerik kaçmasın
    if anahtar in SABIT: return s if s in SABIT[anahtar] or s == "?" else "?"
    if anahtar in KALIP: return s if re.fullmatch(KALIP[anahtar], s) else sade(s, 60)
    return sade(s)

# ---------- ortam ----------
def kurulum_id(uyg):
    fp = os.path.join(uyg, "kurulum-id")
    try: return open(fp).read().strip()[:12]
    except OSError: pass
    k = uuid.uuid4().hex[:12]
    try: os.makedirs(uyg, exist_ok=True); open(fp, "w").write(k)
    except OSError: pass
    return k
def _sh(*c):
    try: return (subprocess.run(list(c), capture_output=True, text=True, timeout=5).stdout or "").strip()
    except Exception: return ""
def ortam(ayar, uyg, eklenti=None, aktarici=None):
    try: kod = json.load(open(os.path.join(os.path.expanduser(str(ayar.get("kod") or _BURASI)), "manifest.json"))).get("version")
    except Exception: kod = None
    return {"kurulum": kurulum_id(uyg), "kod": kod or "?", "surum": aktarici or "?", "eklenti": eklenti or "?",
            "model": _sh("sysctl", "-n", "hw.model") or "?", "macos": platform.mac_ver()[0] or "?",
            "bellek_gb": round(int(_sh("sysctl", "-n", "hw.memsize") or 0) / 2**30), "arayuz": "en" if ayar.get("dil") == "en" else "tr",
            "claude_model": str(ayar.get("claude_model") or "varsayilan"), "python": platform.python_version()}

# ---------- hata özeti ----------
def hata_ozeti(tur, deger, tb):
    """Exception → {isim, errno, cerceve: [dosya:satır işlev], mesaj (süzülmüş), parmak}. Yalnız kodumuzdaki çerçeveler adlı."""
    import traceback, hashlib
    cer = []
    for f in traceback.extract_tb(tb) if tb else []:
        ad = os.path.basename(f.filename)
        cer.append({"dosya": ad, "satir": f.lineno, "islev": f.name} if ad in KOD_DOSYALARI else {"dosya": "<kütüphane>", "satir": 0, "islev": "<kütüphane>"})
    sade_cer = [c for i, c in enumerate(cer) if c["dosya"] != "<kütüphane>" or i == len(cer) - 1][-8:]
    isim = getattr(tur, "__name__", str(tur)); en = getattr(deger, "errno", None)
    yer = next((f"{c['dosya']}:{c['islev']}" for c in reversed(cer) if c["dosya"] != "<kütüphane>"), "?")
    return {"isim": isim, "errno": en if isinstance(en, int) else None, "mesaj": sade(str(deger), 200), "cerceve": sade_cer,
            "parmak": hashlib.sha1(f"{isim}|{en}|{yer}".encode()).hexdigest()[:12]}

# ---------- gönderim ----------
_KILIT = threading.Lock()
def _klasor(uyg, alt):
    d = os.path.join(uyg, "teshis", alt); os.makedirs(d, exist_ok=True); return d
def gonder(paket, ayar, uyg, zorla=False, arka=True):
    """Paketi temizleyip ayardaki adrese gönderir (yalnız `teshis: true` ya da zorla=True — elle geri bildirim).
    Kopyası teshis/gonderilen/'e yazılır; adres yoksa ya da ağ yoksa teshis/bekleyen/'e, sonraki gönderimde yeniden denenir.
    Döner: {"ok": bool, "durum": "gonderildi|bekliyor|kapali", "dosya": yol}"""
    if not (zorla or ayar.get("teshis") is True): return {"ok": False, "durum": "kapali"}
    p = temizle(dict(paket, sema=SURUM_SEMA, zaman=datetime.datetime.now().astimezone().isoformat(timespec="seconds")))
    ad = f"{time.strftime('%Y%m%d-%H%M%S')}-{p.get('tur', 'paket')}.json"
    try: fp = os.path.join(_klasor(uyg, "bekleyen"), ad); json.dump(p, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except OSError as e: return {"ok": False, "durum": "yazilamadi", "hata": str(e)[:100]}
    def isle():
        with _KILIT: _bekleyenleri_gonder(ayar, uyg)
    if arka: threading.Thread(target=isle, daemon=True).start(); return {"ok": True, "durum": "kuyrukta", "dosya": fp}
    isle(); return {"ok": not os.path.exists(fp), "durum": "gonderildi" if not os.path.exists(fp) else "bekliyor", "dosya": fp}
def _bekleyenleri_gonder(ayar, uyg):
    adres = str(ayar.get("teshis_adres") or ADRES_VARSAYILAN)
    if not (adres.startswith("https://") or adres.startswith("http://127.0.0.1:")): return  # yerel: yalnız deneme
    bek, gon = _klasor(uyg, "bekleyen"), _klasor(uyg, "gonderilen")
    for fp in sorted(glob.glob(os.path.join(bek, "*.json")))[:20]:
        try:
            veri = open(fp, "rb").read()
            r = urllib.request.Request(adres, data=veri, method="POST", headers={"Content-Type": "application/json", "X-Suflor-Beta": BETA_ANAHTAR})
            with urllib.request.urlopen(r, timeout=10) as y:
                if y.status >= 300: break
            os.replace(fp, os.path.join(gon, os.path.basename(fp)))
        except Exception: break  # ağ yok / sunucu yok: sonra yeniden
    for eski in sorted(glob.glob(os.path.join(gon, "*.json")))[:-200]:
        try: os.remove(eski)
        except OSError: pass

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--sozluk":
        print("\n".join(sozluk_uret(sys.argv[2])))
    elif len(sys.argv) > 2 and sys.argv[1] == "--dene":
        print(sade(sys.argv[2]))
    else: print(__doc__ or "python3 teshis.py --sozluk <kod> | --dene <satır>")
