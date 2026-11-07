#!/usr/bin/env python3
# Suflor.me — bağlayıcı sözleşmesi (A1, S246). Dış iş/karar kaynakları (bugün: alanın kayıt veritabanı "Kayıt veritabanı") ve Suflor'un kendi proje veritabanı
# (<uygulama>/proje.db) aynı sözleşmenin arkasında: kişiler, kararlar, açık işler, terimler, değişme saati; SQL kaynaklarında tablo yapısı ve tek sorgu.
# İçe aktarılan saf modül: relay'in genel durumuna (BASE, LOCK, AYAR) dokunmaz, ayar sözlüğü ve klasörler parametreyle gelir; ayar dosyasını hiç yazmaz.
# Kullananlar: toplanti-claude.py (vt-izle, vt-mcp, vt-sema, vt-sor, SORU bağlamı; eski vt_* adları orada ince sarmalayıcı), sonra aktarıcı bölümleri (P3).
# Ayar: yeni şema "baglayici": {"kayit": {tur, ad, acik, yol, sorgular{…}, kurallar, disa_aktarim, yazma{komut, alt_komutlar, bayraklar, sure_sn},
# ayricalikli_okuma, iki_yonlu}}; eski anahtarlar (veritabani.*, kayit_*) okunmaya devam eder, ikisi de varsa yenisi kazanır (ayar_coz).
# Güvenlik (toplanti-claude.py'den aynen taşındı, v0.97.2 O4): mode=ro, PRAGMA query_only, gizli sütun yetkilendiricisi (_vt_yetki), VT_GIZLI maskesi,
# görünüm adlı CTE reddi, tek SELECT/WITH, en çok 60 satır.
import json, os, re, sys, time
from collections.abc import MutableMapping

SURUM = 1
class YetenekYok(Exception): pass     # bağlayıcı bu işi yapamaz (sorgu ayarda yok ya da kaynak türü desteklemiyor)
class BaglayiciHata(Exception): pass  # açılamadı / sorgu hatası (yalnız ayrıntılı çağrılarda: sema_metin, sor)

VT_GIZLI = re.compile(r"(?i)(sifre|şifre|parola|password|passwd|token|secret|gizli|anahtar|api_?key|\bkey\b|otp|2fa|totp|recovery|kurtarma)")
SORGU_ADLARI = ("kisiler", "kisi_adres", "gorevler", "kararlar", "sistemler", "sistemler_kart", "terimler")
YAZMA_ESKI = {"komut": "kayit_komutu", "alt_komutlar": "kayit_alt_komutlar", "bayraklar": "kayit_bayraklar", "sure_sn": "kayit_sure_sn"}
_ALT_RX, _BAYRAK_RX = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,40}$"), re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9_-]{0,40}$")
ARG_EN_COK, ARG_UZUNLUK = 20, 2000
class Oneri(dict):
    """oner()'in doğruladığı yazma önerisi {komut, alt, argumanlar}; yaz() yalnız bunu kabul eder (düz sözlük = onaysız öneri)"""
ONBELLEK_TAZE_SN = 150  # vt-mt.json'daki denetim bundan eskiyse araç sunucusu kapanmış sayılır (bas-konus._vt_mt kuralı)
# Öğrenen sözlüğün terimleri — kayıt veritabanı kayıt veritabanının şeması; yalnız sqlite_kayit türünün varsayılanı, ayar sorgular.terimler ezer.
VT_TERIMLER_SORGU = """with t as (
  select k.ad terim, 'kisi' tur,
    (select group_concat(kt.ad, ' | ') from kisi_takma kt
      where kt.kisi_id = k.id and kt.ad <> k.ad and kt.ad not like '%@%'
        and coalesce(kt.baglam,'') not like '%adı değil%') takma_adlar,
    k.guncelleme son_gorulme
  from kisi k where k.durum <> 'Birleştirildi' and k.tur <> 'ortak_hesap'
  union all select ad, 'firma', null, son_gorulme from dis_firma
  union all select ad, 'sistem', null, guncelleme from sistem
  union all select ad, 'sistem', null, null from ajan
) select * from t where terim is not null"""
# proje.db (baglam.py proje_vt_guncelle) — onaylı proje kartının kisi tablosu; ayar gerekmez
PROJE_KISILER_SORGU = ("SELECT ad || CASE WHEN takma_adlar != '' THEN ', ' || takma_adlar ELSE '' END, ad || CASE WHEN roller != '' THEN ' — ' || roller ELSE '' END "
                       "|| CASE WHEN kurumlar != '' THEN ' · ' || kurumlar ELSE '' END || CASE WHEN kaynak != '' THEN ' (kaynak: ' || kaynak || ')' ELSE '' END FROM kisi")

# --- ayar ------------------------------------------------------------------------------------------------------------------------------------
_GOLGE = set()  # süreç başına bir kez: "baglayici.kayit.X eski anahtarı gölgeliyor"
def _gunluk_yaz(m):  # stdout'a asla (izle olay akışı, vt-mcp JSON-RPC); stderr
    try: sys.stderr.write(time.strftime("%H:%M:%S ") + m + "\n"); sys.stderr.flush()
    except Exception: pass
def _bos(v): return v is None or v == "" or v == [] or v == {}
def ayar_coz(ayar, gunluk=None):
    """→ {"kayit": {...}} ya da {} — yeni şema önce, yoksa eski anahtar; acik:false bağlayıcıyı (eski anahtarlar dahil) kapatır. Ayarı değiştirmez."""
    ayar = ayar if isinstance(ayar, dict) else {}
    gunluk = gunluk or _gunluk_yaz
    yeni = ((ayar.get("baglayici") or {}) if isinstance(ayar.get("baglayici"), dict) else {}).get("kayit")
    yeni = yeni if isinstance(yeni, dict) else {}
    if yeni.get("acik") is False: return {}
    eski = ayar.get("veritabani") if isinstance(ayar.get("veritabani"), dict) else {}
    ys = yeni.get("sorgular") if isinstance(yeni.get("sorgular"), dict) else {}
    yy = yeni.get("yazma") if isinstance(yeni.get("yazma"), dict) else {}
    def sec(alan, yv, ev):
        if not _bos(yv):
            if not _bos(ev) and ev != yv and alan not in _GOLGE: _GOLGE.add(alan); gunluk(f"AYAR: baglayici.kayit.{alan} eski anahtarı gölgeliyor")
            return yv
        return None if _bos(ev) else ev
    kv, sorgular, yazma = {}, {}, {}
    for a in ("yol", "kurallar", "disa_aktarim"):
        v = sec(a, yeni.get(a), eski.get(a))
        if v is not None: kv[a] = v
    adlar = list(SORGU_ADLARI) + sorted((set(ys) | {k for k, v in eski.items() if isinstance(v, str) and re.match(r"(?is)^\s*(select|with)\b", v)}) - set(SORGU_ADLARI))
    for a in adlar:
        v = sec("sorgular." + a, ys.get(a), eski.get(a))
        if v is not None: sorgular[a] = v
    for a, ea in YAZMA_ESKI.items():
        v = sec("yazma." + a, yy.get(a), ayar.get(ea))
        if v is not None: yazma[a] = v
    if sorgular: kv["sorgular"] = sorgular
    if yazma: kv["yazma"] = yazma
    if not kv: return {}
    kv.update(kimlik="kayit", tur=str(yeni.get("tur") or "sqlite_kayit"), ad=str(yeni.get("ad") or "Kayıt veritabanı"), acik=True, iki_yonlu=bool(yeni.get("iki_yonlu", False)))
    if isinstance(yeni.get("ayricalikli_okuma"), bool): kv["ayricalikli_okuma"] = yeni["ayricalikli_okuma"]
    return {"kayit": kv}

def _klasor(ayar, ad, var):
    return os.path.expanduser(str((ayar or {}).get(ad) or var))
def yukle(ayar):
    """→ ayarlı dış bağlayıcılar (A1: en çok kayıt veritabanı; okuma yolu yoksa yok)"""
    c = ayar_coz(ayar).get("kayit")
    if not c or not c.get("yol") or c.get("tur") != "sqlite_kayit": return []
    return [SqliteKayit(c, proje=_klasor(ayar, "proje", "~/Suflor"), uygulama=_klasor(ayar, "uygulama", "~/Library/Application Support/Suflor"))]
def etkin_vt(ayar):
    """kayıt veritabanı varsa kayıt veritabanı, yoksa ProjeVT (proje.db varsa ve proje_vt != false), yoksa None"""
    b = yukle(ayar)
    if b: return b[0]
    if (ayar or {}).get("proje_vt", True) is False: return None
    y = os.path.join(_klasor(ayar, "uygulama", "~/Library/Application Support/Suflor"), "proje.db")
    return ProjeVT(y) if os.path.isfile(y) else None
def yazan(ayar):
    """yazma ayarı geçerli olan kayıt veritabanı bağlayıcısı ya da None. Okuma yolu (yol) gerekmez: proje kayıt betiği tek başına ayarlanabilir (bugünkü kayit_komutu davranışı)"""
    c = ayar_coz(ayar).get("kayit")
    if not c or c.get("tur") != "sqlite_kayit": return None
    b = SqliteKayit(c, proje=_klasor(ayar, "proje", "~/Suflor"), uygulama=_klasor(ayar, "uygulama", "~/Library/Application Support/Suflor"))
    return b if b.yazma_ayari() else None
def bos(proje=""):
    """ayarlı olmayan SQLite yer tutucusu: yolu yok, her okuma boş, sema_metin/sor eski "ayarlı değil" iletisini verir (eski VT = {} davranışı)"""
    return _Sqlite(None, {}, proje)
def onbellek_okuyucu(canli, bellek=None):
    """ayrıcalıklı okumanın aktarıcı tarafı: launchd'deki aktarıcı Masaüstü'ndeki dosyayı açmaz, vt-izle'nin yazdığı önbellekleri ve VT_BELLEK'i okur"""
    return OnbellekOkuyucu(canli, bellek)

# --- kayıt biçimleri -------------------------------------------------------------------------------------------------------------------------
_TARIH = re.compile(r"^\d{4}-\d{2}-\d{2}")
def _tarih(v):
    s = "" if v is None else str(v).strip()
    return s[:10] if _TARIH.match(s) else None
def _adlar_bol(s, en_az=2): return [x.strip() for x in str(s or "").split(",") if len(x.strip()) >= en_az]
def is_satiri(i):  # İş kaydı → bugünkü vt_isler satırı [iş, sahip, vade, konum] (yapi.belge_onerileri sonraki adıma dek bunu alır)
    return [str(i.get("metin") or ""), str(i.get("sahip") or ""), str(i.get("vade") or ""), str(i.get("konum") or "")]
def _is_kaydi(r, kaynak):
    r = ["" if x is None else str(x) for x in r]
    while len(r) < 4: r.append("")
    vade = r[2].strip()
    return {"metin": r[0], "sahip": r[1], "vade": _tarih(vade) or (vade or None), "durum": "acik", "konum": r[3], "dis_id": None, "kaynak": kaynak}
def _kisi_suz(isler, kisi):
    if not kisi: return isler
    k = str(kisi).casefold().strip()
    return [i for i in isler if k and (k in str(i.get("sahip") or "").casefold())]
def _kisi_kayitlari(kisi_satir, adres_satir, kaynak):
    out, idx = [], {}
    for r in kisi_satir:
        if not r or not r[0]: continue
        adlar = _adlar_bol(r[0])
        if not adlar: continue
        k = {"ad": adlar[0], "takma": adlar[1:], "adresler": [], "ozet": str(r[1] or "") if len(r) > 1 else "", "dis_id": None, "kaynak": kaynak}
        out.append(k)
        for a in adlar: idx.setdefault(a.casefold(), k)
    for r in adres_satir:
        adlar = _adlar_bol((r or [""])[0])
        adresler = [x.strip().lower() for x in str((r[1] if len(r) > 1 else "") or "").split(",") if "@" in x]
        if not adlar or not adresler: continue
        k = next((idx[a.casefold()] for a in adlar if a.casefold() in idx), None)
        if k is None:
            k = {"ad": adlar[0], "takma": adlar[1:], "adresler": [], "ozet": "", "dis_id": None, "kaynak": kaynak}; out.append(k)
            for a in adlar: idx.setdefault(a.casefold(), k)
        else: k["takma"] += [a for a in adlar if a != k["ad"] and a not in k["takma"]]
        k["adresler"] += [a for a in adresler if a not in k["adresler"]]
    return out

# --- sözleşme --------------------------------------------------------------------------------------------------------------------------------
class Baglayici:
    kimlik = ""; tur = ""; ad = ""
    ayricalikli_okuma = False; iki_yonlu = False
    def __init__(self): self.son_hata = None
    def yetenekler(self): return set()
    def kisiler(self): raise YetenekYok("kisiler")
    def kararlar(self, en_cok=500): raise YetenekYok("kararlar")
    def acik_isler(self, kisi=None): raise YetenekYok("acik_isler")
    def belgeler(self): raise YetenekYok("belgeler")
    def terimler(self): raise YetenekYok("terimler")
    def degisim_zamani(self): return None
    # yazma (P4): oner doğrular (yazmaz), yaz onaylı öneriyi çalıştırır
    def yazma_ayari(self): return None
    def oner(self, kayit): raise YetenekYok("oner")
    def yaz(self, oneri, calistir): raise YetenekYok("yaz")
    def durum_guncelle(self, dis_id, durum): raise YetenekYok("durum_guncelle")
    # SQL kaynaklarına özgü (sözleşme dışı)
    def sema_metin(self): raise YetenekYok("sema_metin")
    def sor(self, q): raise YetenekYok("sor")
    def satirlar(self, anahtar, *param): raise YetenekYok("satirlar")

def _vt_yetki(eylem, a1, a2, kaynak, gorunumler):
    # v0.97.2 (güvenlik denetimi O4): maske yalnız sonuç sütununun adına bakıyordu — "SELECT sifre AS x", ifade içi ya da alt sorgu açık değer veriyordu.
    # Yetkilendirici gizli sütunun sorgudaki her okumasını NULL'a çevirir (WHERE'de de: değer tahmin edilemez). Görünümün kendi içindeki okuma serbest
    # (görünüm tanımı veritabanı sahibinin; dışarıya çıkan görünüm sütunu yine ada göre NULL). WITH (CTE) da "kaynak" adı taşır: yalnız veritabanında
    # tanımlı görünümün adı serbest. ATTACH ve table_info dışı PRAGMA reddedilir.
    import sqlite3
    if eylem == sqlite3.SQLITE_READ: return sqlite3.SQLITE_IGNORE if kaynak not in gorunumler and a2 and VT_GIZLI.search(a2) else sqlite3.SQLITE_OK
    if eylem == sqlite3.SQLITE_ATTACH: return sqlite3.SQLITE_DENY
    if eylem == sqlite3.SQLITE_PRAGMA: return sqlite3.SQLITE_OK if str(a1 or "").lower() in ("table_info", "query_only") else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK

class _Sqlite(Baglayici):
    """SQLite kaynağının ortak okuması (yalnız okunur). Yol her çağrıda çözülür: eski VT görünümünden yapılan değişiklik hemen geçer."""
    def __init__(self, yol, sorgular=None, proje=""):
        super().__init__(); self.yol = yol; self.sorgular = dict(sorgular or {}); self.proje = proje; self.ayar = {}
    def dosya(self):
        if not self.yol: return None
        return os.path.join(self.proje, os.path.expanduser(str(self.yol)))
    def _uri(self):
        import pathlib
        return pathlib.Path(self.dosya()).resolve().as_uri() + "?mode=ro"
    def degisim_zamani(self):  # WAL kipinde yazma önce -wal'a gider; .db'nin saati ancak checkpoint'te değişir — ikisinin en yenisi
        y = self.dosya()
        if not y: return None
        mt = [os.path.getmtime(f) for f in (y, y + "-wal") if os.path.exists(f)]
        return max(mt) if mt else None
    def _calistir(self, q, param=()):  # yapılandırılmış (sahibin) sorgusu; kilitte 1,5 sn bekleyip bir kez daha (WAL; immutable=1 kullanılmaz)
        import sqlite3
        for den in range(2):
            try:
                con = sqlite3.connect(self._uri(), uri=True, timeout=2)
                try: r = con.execute(q, param).fetchall()
                finally: con.close()
                self.son_hata = None; return r
            except sqlite3.OperationalError as e:
                if den == 0 and re.search(r"locked|busy", str(e), re.I): time.sleep(1.5); continue
                self.son_hata = f"{e.__class__.__name__}: {str(e)[:120]}"; return []
            except Exception as e: self.son_hata = f"{e.__class__.__name__}: {str(e)[:120]}"; return []
        return []
    def dene(self):  # açılabiliyor mu: None = evet, değilse hata metni ("SınıfAdı: ileti")
        if not self.yol: return "BaglayiciHata: yol yok"
        return None if self._calistir("SELECT 1") else (self.son_hata or "OperationalError: açılamadı")
    def satirlar(self, anahtar, *param):  # adlı sorgu (yalnız SELECT/WITH, tek komut); yoksa ya da okunamazsa [] (eski vt_sorgu)
        q = str(self.sorgular.get(anahtar) or "").strip()
        if not self.yol or not re.match(r"(?is)^(select|with)\b", q) or ";" in q.rstrip(";"): return []
        return self._calistir(q, param)
    def _baglan(self):
        if not self.yol: raise BaglayiciHata("Kayıt veritabanı ayarlı değil (ayar veritabani.yol).")
        import sqlite3
        try:
            con = sqlite3.connect(self._uri(), uri=True, timeout=3)
            con.execute("PRAGMA query_only = ON"); gor = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'view'")}
            con.set_authorizer(lambda e, a1, a2, vt, kaynak: _vt_yetki(e, a1, a2, kaynak, gor)); return con
        except Exception as e: raise BaglayiciHata(f"Kayıt veritabanı açılamadı ({e.__class__.__name__}).")
    def sema_metin(self):
        con = self._baglan(); sat = []
        for ad, tur in con.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            kol = [r[1] for r in con.execute(f'PRAGMA table_info("{ad}")')]
            try: n = con.execute(f'SELECT count(*) FROM "{ad}"').fetchone()[0]
            except Exception: n = "?"
            sat.append(f"{ad} ({'görünüm' if tur == 'view' else 'tablo'}, {n} satır): " + ", ".join(k + (" [gizli]" if VT_GIZLI.search(k) else "") for k in kol))
        return "\n".join(sat)
    def sor(self, q):
        q = str(q or "").strip().rstrip(";").strip()
        if not re.match(r"(?is)^(select|with)\b", q) or ";" in q or re.search(r"(?i)\b(attach|detach|pragma|insert|update|delete|drop|create|alter|replace|vacuum|reindex|load_extension)\b", q):
            raise BaglayiciHata("Yalnız tek bir SELECT/WITH sorgusu çalışır.")
        con = self._baglan()
        for v, in con.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall():  # O4: görünüm adlı CTE yetkilendiriciyi şaşırtır
            if re.search(r'(?i)["`\[]?\b' + re.escape(v) + r'\b["`\]]?\s*(\([^()]*\))?\s*AS\s+(NOT\s+)?(MATERIALIZED\s+)?\(', q):
                raise BaglayiciHata(f"WITH adı bir görünümün adıyla aynı olamaz ({v}).")
        try: cur = con.execute(q)
        except Exception as e: raise BaglayiciHata(f"Sorgu hatası: {str(e)[:200]}")
        kol = [d[0] for d in (cur.description or [])]; gz = [bool(VT_GIZLI.search(k)) for k in kol]; rows = cur.fetchmany(61)
        sat = ["\t".join(kol)] + ["\t".join("***" if g else ("" if v is None else " ".join(str(v).split())[:200]) for v, g in zip(r, gz)) for r in rows[:60]]
        return "\n".join(sat + [f"({min(len(rows), 60)} satır" + ("; 60'tan fazla — sorguyu daralt" if len(rows) > 60 else "") + ")"])
    def _var(self, anahtar): return bool(str(self.sorgular.get(anahtar) or "").strip())
    def yetenekler(self):
        y = {"sema_metin", "sor", "satirlar"}
        if self._var("kisiler") or self._var("kisi_adres"): y.add("kisiler")
        if self._var("gorevler"): y.add("acik_isler")
        if self._var("kararlar"): y.add("kararlar")
        return y
    def kisiler(self):
        if "kisiler" not in self.yetenekler(): raise YetenekYok("kisiler")
        return _kisi_kayitlari(self.satirlar("kisiler"), self.satirlar("kisi_adres"), self.kimlik)
    def acik_isler(self, kisi=None):
        if not self._var("gorevler"): raise YetenekYok("acik_isler")
        return _kisi_suz([_is_kaydi(r, self.kimlik) for r in self.satirlar("gorevler")[:500] if r and r[0]], kisi)
    def kararlar(self, en_cok=500):  # sütunlar: metin, tarih, kim, durum (eksikler boş)
        if not self._var("kararlar"): raise YetenekYok("kararlar")
        out = []
        for r in self.satirlar("kararlar")[:en_cok]:
            if not r or not r[0]: continue
            r = list(r) + [None] * 4
            out.append({"metin": str(r[0]), "tarih": _tarih(r[1]), "kim": "" if r[2] is None else str(r[2]), "durum": "" if r[3] is None else str(r[3]), "dis_id": None, "kaynak": self.kimlik})
        return out

class SqliteKayit(_Sqlite):
    """kayıt veritabanı kayıt veritabanı (tur sqlite_kayit): ayardaki yol ve sorgular; varsayılan terimler sorgusu VT_TERIMLER_SORGU"""
    tur = "sqlite_kayit"
    def __init__(self, c, proje="", uygulama=""):
        super().__init__(c.get("yol"), c.get("sorgular"), proje)
        self.kimlik = str(c.get("kimlik") or "kayit"); self.ad = str(c.get("ad") or "Kayıt veritabanı"); self.ayar = c
        self.iki_yonlu = bool(c.get("iki_yonlu", False))
        if isinstance(c.get("ayricalikli_okuma"), bool): self.ayricalikli_okuma = c["ayricalikli_okuma"]
        else:  # uygulama klasörünün dışındaysa (Masaüstü vb.) launchd'deki aktarıcı açamaz → okuma Brifing.app --vt-izle ile
            try: d, u = os.path.realpath(self.dosya()), os.path.realpath(uygulama) if uygulama else ""
            except (TypeError, ValueError): d, u = "", ""
            self.ayricalikli_okuma = not (u and (d == u or d.startswith(u.rstrip(os.sep) + os.sep)))
    def yetenekler(self):
        y = super().yetenekler() | {"terimler"}
        return y | ({"yaz"} if self.yazma_ayari() else set())
    def yazma_ayari(self):  # → {"komut", "alt", "bayrak", "sure"} ya da None (yazma ayarı yoksa/uygunsuzsa yazma hiç yok); ayar_coz: baglayici.kayit.yazma önce, yoksa eski kayit_* anahtarları
        y = self.ayar.get("yazma") if isinstance(self.ayar.get("yazma"), dict) else {}
        k, alt = y.get("komut"), y.get("alt_komutlar")
        if not (isinstance(k, list) and len(k) >= 2 and all(isinstance(x, str) and x and "\0" not in x for x in k)): return None
        if not (isinstance(alt, list) and alt and all(isinstance(x, str) and _ALT_RX.match(x) for x in alt)): return None
        bay = [x for x in (y.get("bayraklar") or []) if isinstance(x, str) and _BAYRAK_RX.match(x)]
        return {"komut": k, "alt": list(alt), "bayrak": bay, "sure": y.get("sure_sn")}
    def oner(self, kayit):  # → Oneri {komut: proje_kayit, alt, argumanlar} ya da BaglayiciHata(kod[, ayrinti]); kodlar: yazma_yok · arguman_uymuyor · alt_izinli_degil · arguman_liste · bayrak_izinli_degil
        pk = self.yazma_ayari()
        if not pk: raise BaglayiciHata("yazma_yok")
        if not isinstance(kayit, dict) or set(kayit) != {"alt", "argumanlar"}: raise BaglayiciHata("arguman_uymuyor")
        alt, ar = kayit["alt"], kayit["argumanlar"]
        if not isinstance(alt, str) or alt not in pk["alt"]: raise BaglayiciHata("alt_izinli_degil", str(alt)[:40])
        if not isinstance(ar, list) or len(ar) > ARG_EN_COK or any(not isinstance(x, str) or len(x) > ARG_UZUNLUK or "\0" in x for x in ar): raise BaglayiciHata("arguman_liste")
        kotu = [x for x in ar if x.startswith("-") and x not in pk["bayrak"]]
        if kotu: raise BaglayiciHata("bayrak_izinli_degil", kotu[0][:40])
        return Oneri(komut="proje_kayit", alt=alt, argumanlar=list(ar))
    def yaz(self, oneri, calistir):  # onaylı öneriyi çalıştırır: calistir(komut, arg) → (ok, sonuç); → dış kimlik (A1: None). Hata: BaglayiciHata("onaysiz_oneri" | "calistirilamadi", neden | "betik_hata", sonuç sözlüğü)
        if not isinstance(oneri, Oneri): raise BaglayiciHata("onaysiz_oneri")
        self.oner({"alt": oneri.get("alt"), "argumanlar": oneri.get("argumanlar")})  # ayar bu arada değiştiyse ya da öneri elle bozulduysa yeniden doğrular
        ok, r = calistir("proje_kayit", {"alt": oneri["alt"], "argumanlar": oneri["argumanlar"]})
        if not ok: raise BaglayiciHata("calistirilamadi", r)
        if isinstance(r, dict) and not r.get("ok"): raise BaglayiciHata("betik_hata", r)
        return None
    def terimler(self):  # → [{terim, tur, takma}]
        q = str(self.sorgular.get("terimler") or VT_TERIMLER_SORGU).strip().rstrip(";")
        if not self.yol or not re.match(r"(?is)^(select|with)\b", q) or ";" in q: return []
        rows = self._calistir(q)
        return [{"terim": str(r[0]).strip(), "tur": str(r[1] or "") if len(r) > 1 else "", "takma": [x.strip() for x in str((r[2] if len(r) > 2 else "") or "").split("|") if x.strip()]}
                for r in rows if r and r[0] and str(r[0]).strip()]

class ProjeVT(_Sqlite):
    """Suflor'un proje veritabanı (<uygulama>/proje.db, baglam.py proje_vt_guncelle); ayar gerekmez, aktarıcı doğrudan okuyabilir"""
    tur = "proje"; kimlik = "proje"; ad = "Proje"
    def __init__(self, yol):
        super().__init__(yol, {"kisiler": PROJE_KISILER_SORGU}, "")
        self.ayricalikli_okuma = False; self.iki_yonlu = False

class OnbellekOkuyucu(Baglayici):
    """aktarıcı tarafı: canli/vt-kisi-adres.json, vt-gorevler.json, vt-mt.json + bellek (VT_BELLEK: adlar, terimler); yazma yok, dosya açmaz"""
    tur = "onbellek"; kimlik = "kayit"; ad = "Kayıt veritabanı (önbellek)"; ayricalikli_okuma = False
    def __init__(self, canli, bellek=None):
        super().__init__(); self.canli = canli; self.bellek = bellek if bellek is not None else {}
    def _oku(self, ad):
        try: return json.load(open(os.path.join(self.canli, ad), encoding="utf-8"))
        except (OSError, ValueError) as e: self.son_hata = f"{ad}: {e.__class__.__name__}"; return None
    def yetenekler(self):
        y = set()
        if os.path.exists(os.path.join(self.canli, "vt-kisi-adres.json")) or self.bellek.get("adlar"): y.add("kisiler")
        if os.path.exists(os.path.join(self.canli, "vt-gorevler.json")): y.add("acik_isler")
        if self.bellek.get("terimler"): y.add("terimler")
        return y
    def kisiler(self):
        d = self._oku("vt-kisi-adres.json") or {}
        adres = [[", ".join(k.get("adlar") or []), ", ".join(k.get("adresler") or [])] for k in (d.get("kisiler") or []) if isinstance(k, dict)]
        return _kisi_kayitlari([[a, ""] for a in (self.bellek.get("adlar") or [])], adres, self.kimlik)
    def acik_isler(self, kisi=None):
        d = self._oku("vt-gorevler.json")
        if d is None: raise YetenekYok("acik_isler")
        return _kisi_suz([_is_kaydi(r, self.kimlik) for r in (d.get("satirlar") or [])[:500] if isinstance(r, list) and r and r[0]], kisi)
    def terimler(self):
        t = self.bellek.get("terimler")
        if not t: raise YetenekYok("terimler")
        return [dict(x) for x in t if isinstance(x, dict)]
    def degisim_zamani(self):
        d = self._oku("vt-mt.json")
        try: return float(d["mt"]) if d and d.get("mt") and time.time() - float(d.get("kontrol") or 0) <= ONBELLEK_TAZE_SN else None
        except (ValueError, TypeError, KeyError): return None

# --- eski VT sözlüğü görünümü (toplanti-claude.py ve testler VT["yol"], VT["<sorgu>"] okur/yazar) ----------------------------------------------
class EskiGorunum(MutableMapping):
    """bağlayıcının eski "veritabani" sözlüğü gibi görünümü: yol, proje_vt, kurallar/disa_aktarim, öteki anahtarlar = sorgular. Bağlayıcı yoksa boş sözlük."""
    _AYAR = ("kurallar", "disa_aktarim")
    def __init__(self, bag): self.bag = bag; self._bos = {}
    def __getitem__(self, k):
        b = self.bag
        if b is None or not isinstance(b, _Sqlite): return self._bos[k]
        if k == "yol":
            if not b.yol: raise KeyError(k)
            return b.yol
        if k == "proje_vt":
            if b.tur != "proje": raise KeyError(k)
            return True
        if k in self._AYAR:
            v = getattr(b, "ayar", {}).get(k)
            if v is None: raise KeyError(k)
            return v
        return b.sorgular[k]
    def __setitem__(self, k, v):
        b = self.bag
        if b is None or not isinstance(b, _Sqlite): self._bos[k] = v
        elif k == "yol": b.yol = v
        elif k == "proje_vt": pass
        elif k in self._AYAR: getattr(b, "ayar", {})[k] = v
        else: b.sorgular[k] = v
    def __delitem__(self, k):
        b = self.bag
        if b is None or not isinstance(b, _Sqlite): del self._bos[k]
        elif k == "yol": b.yol = None
        elif k in self._AYAR: del getattr(b, "ayar", {})[k]
        else: del b.sorgular[k]
    def _anahtarlar(self):
        b = self.bag
        if b is None or not isinstance(b, _Sqlite): return list(self._bos)
        k = (["yol"] if b.yol else []) + (["proje_vt"] if b.tur == "proje" else [])
        return k + [a for a in self._AYAR if getattr(b, "ayar", {}).get(a) is not None] + list(b.sorgular)
    def __iter__(self): return iter(self._anahtarlar())
    def __len__(self): return len(self._anahtarlar())
