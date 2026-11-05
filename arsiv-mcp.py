#!/usr/bin/env python3
# Suflor.me — toplantı arşivi için yerel MCP sunucusu (Model Context Protocol; Claude Desktop / Claude Code araç olarak bağlar).
# Yalnız bu Mac: stdio taşıması (satır başına bir JSON-RPC iletisi), ağ portu açmaz. Bağımlılıksız, Python 3.9, yalnız standart kütüphane.
# Veri kaynağı (çift kaynak yok):
#  - toplantı listesi, arama, döküm: aktarıcının /toplantilar uçları (127.0.0.1, X-Suflor-Anahtar = <canlı klasör>/kart-anahtari.txt; anahtar yoksa
#    ya da reddedilirse araç hata döner). Aktarıcı kapalıysa bu araçlar "aktarıcı yanıt vermiyor" der.
#  - özet: aktarıcının kayıt dosyası son-toplantilar.jsonl'in gösterdiği özet kopyası (canlı klasörün içinde olmalı).
#  - karar, iş, açık soru: karar grafı (canli/karar-grafi.sqlite); yazma yapi.py'nin işleviyle (soz_kapat) — toplanti-claude.py soz/yapi ile aynı yol.
# Gizli toplantılar (dökümde **GİZLİ** satırı ya da özet kaydında gizli: true) hiçbir araçta dönmez; listede, aramada, kararda, işte yok.
# Yazma araçları (is_durumu, karar_onayla, karar_duzelt): ilk çağrı yazmaz, {"onay_gerekli": true, "ozet": …} döner; aynı çağrı "onayla": true ile uygular.
# Kullanım (örnek yapılandırma KILAVUZ.md "Claude'dan arşive erişim"): python3 -B arsiv-mcp.py [--dir <canlı klasör>] [--relay http://127.0.0.1:<port>]
import argparse, datetime, json, os, re, sqlite3, sys, urllib.error, urllib.parse, urllib.request
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SURUM = "1.0.0"
PROTOKOLLER = ("2025-06-18", "2025-03-26", "2024-11-05")
AYAR_YOL = os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")
def ayar_oku():
    v = {"port": 8765, "uygulama": "~/Library/Application Support/Suflor"}
    try: v.update(json.load(open(AYAR_YOL, encoding="utf-8")))
    except (OSError, ValueError): pass
    v["uygulama"] = os.path.expanduser(str(v["uygulama"])); return v
AYAR = ayar_oku()
ap = argparse.ArgumentParser(description="Suflor.me toplantı arşivi MCP sunucusu (stdio)")
ap.add_argument("--dir", default=os.path.join(AYAR["uygulama"], "canli")); ap.add_argument("--relay", default=f"http://127.0.0.1:{AYAR['port']}")
ARG = ap.parse_args()
DIR = ARG.dir; RELAY = ARG.relay.rstrip("/")
if not re.match(r"^http://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", RELAY): sys.exit("yalnız yerel aktarıcı (127.0.0.1)")
ID_RX = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}-[^/\\]+$")
TARIH_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

class AracHatasi(Exception): pass
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # yerel adres: ortam vekili kullanılmaz

def anahtar():
    try: k = open(os.path.join(DIR, "kart-anahtari.txt"), encoding="utf-8").read().strip()
    except OSError: k = ""
    if not k: raise AracHatasi("yerel anahtar yok (kart-anahtari.txt okunamadı): Suflor.me kurulu ve açık mı?")
    return k
def aktarici(yol, parametre=None):
    url = RELAY + yol + ("?" + urllib.parse.urlencode(parametre) if parametre else "")
    try: return json.loads(_OPENER.open(urllib.request.Request(url, headers={"X-Suflor-Anahtar": anahtar()}), timeout=15).read())
    except urllib.error.HTTPError as e:
        raise AracHatasi("aktarıcı yerel anahtarı reddetti (401)" if e.code == 401 else f"aktarıcı hata verdi ({e.code})")
    except (urllib.error.URLError, OSError, ValueError): raise AracHatasi("aktarıcı yanıt vermiyor (Suflor.me açık mı?)")

# --- gizli toplantı (ortak kaynak: yapi.py — pano Bugün ucuyla aynı kural) -----------------------------------------------
import yapi
def _kayitlar(): return yapi.son_kayitlar(DIR)
def gizli_mi(i, kayitlar=None): return yapi.gizli_mi(DIR, i, kayitlar)

# --- karar grafı ------------------------------------------------------------------------------------------------------
def _graf_yol(): return os.path.join(DIR, "karar-grafi.sqlite")
def graf_oku(sorgu, param=()):
    if not os.path.exists(_graf_yol()): return []
    try:
        c = sqlite3.connect("file:" + urllib.parse.quote(_graf_yol()) + "?mode=ro", uri=True, timeout=5)
        try: return c.execute(sorgu, param).fetchall()
        finally: c.close()
    except sqlite3.Error as e: raise AracHatasi(f"karar grafı okunamadı ({e.__class__.__name__})")
KOLON = "id, toplanti, baslik, tarih, tur, kim, sahip, metin, son_tarih, saat, durum"
def _satir(r):
    i, top, baslik, tarih, tur, kim, sahip, metin, son, saat, durum = r
    on = {"karar": "k", "soru": "q"}.get(tur, "s")
    x = {"id": f"{on}{i}", "tur": tur, "metin": metin, "toplanti": (top or "")[:-3] if (top or "").endswith(".md") else top, "baslik": baslik, "tarih": tarih, "durum": durum}
    for k, v in (("kim", kim), ("sahip", sahip), ("son_tarih", son), ("saat", saat)):
        if v: x[k] = v
    return x
def _gorunur(x, kayitlar):  # gizli toplantıdan gelen kayıt dönmez
    return not (x.get("toplanti") and gizli_mi(x["toplanti"], kayitlar))
def _kayit_bul(id_, turler):  # "k12" / "s7" / "q3" → graf satırı (gizli toplantıdaysa yok sayılır)
    m = re.fullmatch(r"([ksq])(\d+)", str(id_ or ""))
    if not m: raise AracHatasi("geçersiz kimlik (k<sayı> karar, s<sayı> iş/söz, q<sayı> açık soru)")
    rs = graf_oku(f"SELECT {KOLON} FROM kayit WHERE id = ?", (int(m.group(2)),))
    x = _satir(rs[0]) if rs else None
    if not x or x["tur"] not in turler or not _gorunur(x, None): raise AracHatasi(f"{id_} bulunamadı")
    return x

def _tarih_ara(a, b):
    for t in (a, b):
        if t and not TARIH_RX.match(str(t)): raise AracHatasi("tarih YYYY-AA-GG biçiminde olmalı")
def _aralikta(tarih, a, b): return (not a or tarih >= a) and (not b or tarih <= b)
def _sayi(v, varsayilan, en_az, en_cok):
    try: n = int(v)
    except (TypeError, ValueError): return varsayilan
    return max(en_az, min(en_cok, n))

# --- okuma araçları ---------------------------------------------------------------------------------------------------
def t_liste(a):
    _tarih_ara(a.get("baslangic"), a.get("bitis"))
    ky = _kayitlar(); ls = [x for x in aktarici("/toplantilar").get("toplantilar") or [] if not gizli_mi(x["id"], ky) and _aralikta(x["at"][:10], a.get("baslangic"), a.get("bitis"))]
    n, ofs = _sayi(a.get("limit"), 20, 1, 100), _sayi(a.get("baslangic_sirasi"), 0, 0, 100000)
    return {"toplam": len(ls), "gosterilen": len(ls[ofs:ofs + n]), "baslangic_sirasi": ofs, "toplantilar": ls[ofs:ofs + n]}
def t_ara(a):
    q = str(a.get("sorgu") or "").strip()[:200]
    if not q: raise AracHatasi("sorgu gerekli")
    _tarih_ara(a.get("baslangic"), a.get("bitis"))
    ky = _kayitlar(); r = aktarici("/toplantilar", {"q": q})
    out = []
    for x in r.get("sonuclar") or []:
        if gizli_mi(x["id"], ky) or not _aralikta(x["at"][:10], a.get("baslangic"), a.get("bitis")): continue
        out.append({"id": x["id"], "baslik": x["baslik"], "at": x["at"], "saat": x["saat"], "kim": x["kim"], "ozet_satiri": bool(x["ozet"]),
                    "metin": "".join(p[0] for p in x["parcalar"])})
    n = _sayi(a.get("limit"), 20, 1, 60)
    return {"sorgu": q, "tum_sozcukler": r.get("tam"), "sonuc_sayisi": len(out), "sonuclar": out[:n]}
def _ozet_dosyasi(id_):
    r = _kayitlar().get(id_ + ".md") or {}
    yol = os.path.realpath(str(r.get("kopya") or "")) if r.get("kopya") else ""
    if yol and yol.endswith(".md") and os.path.isfile(yol) and (yol + os.sep).startswith(os.path.realpath(DIR) + os.sep): return yol, r
    return None, r
def _gorunur_toplanti(id_):
    id_ = str(id_ or "")
    if not ID_RX.match(id_) or gizli_mi(id_): raise AracHatasi("toplantı bulunamadı")
    return id_
def t_ozet(a):
    i = _gorunur_toplanti(a.get("id")); yol, r = _ozet_dosyasi(i)
    if not yol: raise AracHatasi("bu toplantının özeti yok (özet kopyası kaydedilmemiş)")
    metin = open(yol, encoding="utf-8", errors="replace").read(60000)
    return {"id": i, "baslik": r.get("baslik"), "at": r.get("at"), "ozet": metin}
def t_dokum(a):
    i = _gorunur_toplanti(a.get("id")); d = aktarici("/toplantilar/dokum", {"id": i})
    if not d.get("ok"): raise AracHatasi(str(d.get("err") or "döküm yok"))
    sat = d["satirlar"]; boy = _sayi(a.get("sayfa_boyutu"), 200, 20, 500); sayfa = _sayi(a.get("sayfa"), 1, 1, 100000)
    sayfa_sayisi = max(1, -(-len(sat) // boy)); parca = sat[(sayfa - 1) * boy: sayfa * boy]
    return {"id": i, "baslik": d.get("baslik"), "at": d.get("at"), "sure_dk": d.get("sure_dk"), "sayfa": sayfa, "sayfa_sayisi": sayfa_sayisi,
            "toplam_satir": len(sat), "aktarici_kesti": bool(d.get("kesildi")),
            "satirlar": [f"{x['saat']} {x['kim']}: {x['metin']}" for x in parca]}
def _ozet_kararlari(i):  # grafta kayıt yoksa özetin "## Kararlar" bölümü
    yol, _ = _ozet_dosyasi(i)
    if not yol: return []
    out, ic = [], False
    for ln in open(yol, encoding="utf-8", errors="replace").read(60000).splitlines():
        if ln.startswith("#"): ic = bool(re.match(r"#+\s*Kararlar\b", ln.strip(), re.I)); continue
        t = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", ln).replace("**", "").strip()
        if ic and len(t) >= 3 and not t.startswith("|---"): out.append(t)
    return out
def t_kararlar(a):
    ky = _kayitlar(); i = a.get("id"); kisi = str(a.get("kisi") or "").strip().lower()
    if i: i = _gorunur_toplanti(i)
    _tarih_ara(a.get("baslangic"), a.get("bitis"))
    rs = graf_oku(f"SELECT {KOLON} FROM kayit WHERE tur = 'karar' ORDER BY tarih DESC, id DESC LIMIT 3000")
    out = [x for x in map(_satir, rs) if _gorunur(x, ky) and (not i or x["toplanti"] == i) and _aralikta(x["tarih"] or "", a.get("baslangic"), a.get("bitis"))
           and (not kisi or kisi in (x.get("kim") or "").lower() or kisi in x["metin"].lower())]
    n = _sayi(a.get("limit"), 30, 1, 100); r = {"toplam": len(out), "kararlar": out[:n]}
    if i and not out and not kisi:
        oz = _ozet_kararlari(i)
        if oz: r["ozetten"] = oz; r["not"] = "karar grafında kayıt yok; özetin Kararlar bölümü"
    return r
def t_isler(a):
    ky = _kayitlar(); kisi = str(a.get("kisi") or "").strip().lower(); durum = str(a.get("durum") or "acik").strip().lower()
    if durum not in ("acik", "yapildi", "tutuldu", "iptal", "hepsi"): raise AracHatasi("durum: acik | yapildi | tutuldu | iptal | hepsi")
    i = _gorunur_toplanti(a.get("id")) if a.get("id") else None
    rs = graf_oku(f"SELECT {KOLON} FROM kayit WHERE tur IN ('is', 'soz') ORDER BY id DESC LIMIT 3000")
    out = []
    for x in map(_satir, rs):
        if not _gorunur(x, ky) or (i and x["toplanti"] != i): continue
        if durum != "hepsi" and x["durum"] != durum: continue
        if kisi and kisi not in ((x.get("sahip") or "") + " " + (x.get("kim") or "")).lower(): continue
        x["gecikti"] = bool(x["durum"] == "acik" and x.get("son_tarih") and TARIH_RX.match(str(x["son_tarih"])) and x["son_tarih"] < datetime.date.today().isoformat())
        out.append(x)
    n = _sayi(a.get("limit"), 50, 1, 200); return {"toplam": len(out), "isler": out[:n]}
def t_sorular(a):
    ky = _kayitlar(); i = _gorunur_toplanti(a.get("id")) if a.get("id") else None
    rs = graf_oku(f"SELECT {KOLON} FROM kayit WHERE tur = 'soru' AND durum = 'acik' ORDER BY id DESC LIMIT 1000")
    out = [x for x in map(_satir, rs) if _gorunur(x, ky) and (not i or x["toplanti"] == i)]
    n = _sayi(a.get("limit"), 50, 1, 200); return {"toplam": len(out), "sorular": out[:n]}

# --- yazma araçları (önce onay_gerekli) ---------------------------------------------------------------------------------
def _onay(a, ozet, uygula):
    if a.get("onayla") is not True: return {"onay_gerekli": True, "ozet": ozet, "nasil": "Kullanıcı onaylarsa aynı çağrıyı \"onayla\": true ile yeniden gönder; yazılmadı."}
    return dict(uygula(), uygulandi=True)
def t_is_durumu(a):
    x = _kayit_bul(a.get("id"), ("is", "soz")); d = str(a.get("durum") or "").strip().lower()
    yeni = {"yapildi": "tutuldu" if x["tur"] == "soz" else "yapildi", "yapilmadi": "iptal", "acik": "acik"}.get(d)
    if not yeni: raise AracHatasi("durum: yapildi | yapilmadi | acik")
    if x["durum"] == yeni: return {"degisiklik_yok": True, "kayit": x}
    def uygula():
        r = yapi.soz_kapat(DIR, x["id"], yeni)
        if not r: raise AracHatasi("iş güncellenemedi")
        return {"kayit": dict(x, durum=yeni)}
    return _onay(a, f"{x['id']} \"{x['metin'][:120]}\" işi: {x['durum']} → {yeni}" + (f" (sahip {x['sahip']})" if x.get("sahip") else ""), uygula)
TEYIT_RX = yapi.TEYIT_RX  # yapi.graf_yaz ekler
def _karar_yaz(id_, metin):
    if not yapi.karar_yaz(DIR, id_, metin): raise AracHatasi("karar güncellenemedi")
def t_karar_onayla(a):
    x = _kayit_bul(a.get("id"), ("karar",))
    if not TEYIT_RX.search(x["metin"]): return {"degisiklik_yok": True, "not": "bu kararda teyit bekliyor işareti yok", "kayit": x}
    yeni = TEYIT_RX.sub("", x["metin"])
    def uygula():
        if yapi.karar_teyit_kaldir(DIR, x["id"]) is None: raise AracHatasi("karar güncellenemedi")
        return {"kayit": dict(x, metin=yeni)}
    return _onay(a, f"{x['id']} kararı onaylanır (teyit bekliyor işareti kalkar): \"{yeni[:160]}\"", uygula)
def t_karar_duzelt(a):
    x = _kayit_bul(a.get("id"), ("karar",)); yeni = " ".join(str(a.get("metin") or "").split())[:500]
    if not yeni: raise AracHatasi("metin gerekli (kararın düzeltilmiş hali)")
    if yeni == x["metin"]: return {"degisiklik_yok": True, "kayit": x}
    return _onay(a, f"{x['id']} kararı düzeltilir: \"{x['metin'][:160]}\" → \"{yeni[:160]}\"", lambda: (_karar_yaz(x["id"], yeni), {"kayit": dict(x, metin=yeni)})[1])

def _sema(ozellikler, gerekli=()): return {"type": "object", "properties": ozellikler, "required": list(gerekli), "additionalProperties": False}
S, SAY = {"type": "string"}, {"type": "integer"}
TARIHLER = {"baslangic": {"type": "string", "description": "YYYY-AA-GG"}, "bitis": {"type": "string", "description": "YYYY-AA-GG"}}
ONAY = {"onayla": {"type": "boolean", "description": "Yalnız kullanıcı onayladıktan sonra true; yoksa onay_gerekli ve özet döner, yazılmaz"}}
OKU = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
YAZ = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
ARACLAR = [
    ("toplanti_ara", "Toplantı dökümlerinde ve özetlerinde anahtar sözcükle arar (Türkçe ek toleranslı; bütün sözcükleri içeren satırlar önce). İsteğe bağlı tarih aralığı.",
     _sema({"sorgu": S, "limit": SAY, **TARIHLER}, ["sorgu"]), OKU, t_ara),
    ("toplanti_listesi", "Toplantıları yeniden eskiye listeler (kimlik, başlık, tarih, süre, kişiler). Tarih aralığı ve sayfalama isteğe bağlı.",
     _sema({"limit": SAY, "baslangic_sirasi": SAY, **TARIHLER}), OKU, t_liste),
    ("toplanti_ozeti", "Bir toplantının kaydedilmiş özetini (Markdown) döndürür.", _sema({"id": S}, ["id"]), OKU, t_ozet),
    ("toplanti_dokumu", "Bir toplantının dökümünü sayfa sayfa döndürür (saat, konuşmacı, metin). Uzun toplantıda sayfa ve sayfa_boyutu kullan.",
     _sema({"id": S, "sayfa": SAY, "sayfa_boyutu": SAY}, ["id"]), OKU, t_dokum),
    ("kararlar", "Toplantılarda alınan kararlar (karar grafı). Toplantıya, kişiye ya da tarih aralığına göre süzülür.",
     _sema({"id": S, "kisi": S, "limit": SAY, **TARIHLER}), OKU, t_kararlar),
    ("isler", "Toplantılardan çıkan işler ve verilen sözler. Kişiye (sahip), duruma (acik | yapildi | tutuldu | iptal | hepsi; varsayılan acik) ve toplantıya göre süzülür.",
     _sema({"kisi": S, "durum": S, "id": S, "limit": SAY}), OKU, t_isler),
    ("acik_sorular", "Toplantılarda cevaplanmadan kalan açık sorular.", _sema({"id": S, "limit": SAY}), OKU, t_sorular),
    ("is_durumu", "Bir işi ya da sözü yapıldı / yapılmadı olarak işaretler (ya da yeniden açar). Önce onay_gerekli döner; kullanıcı onaylarsa onayla: true ile yeniden çağır.",
     _sema({"id": S, "durum": {"type": "string", "enum": ["yapildi", "yapilmadi", "acik"]}, **ONAY}, ["id", "durum"]), YAZ, t_is_durumu),
    ("karar_onayla", "Teyit bekleyen (örtük ya da tek taraflı) bir kararı onaylar. Önce onay_gerekli döner; onayla: true ile uygulanır.",
     _sema({"id": S, **ONAY}, ["id"]), YAZ, t_karar_onayla),
    ("karar_duzelt", "Bir kararın metnini düzeltir. Önce onay_gerekli döner; onayla: true ile uygulanır.",
     _sema({"id": S, "metin": S, **ONAY}, ["id", "metin"]), YAZ, t_karar_duzelt),
]
TABLO = {a[0]: a for a in ARACLAR}

# --- JSON-RPC (stdio, satır başına bir ileti) -------------------------------------------------------------------------
def yanit(i, sonuc=None, hata=None):
    m = {"jsonrpc": "2.0", "id": i}
    if hata: m["error"] = hata
    else: m["result"] = sonuc
    sys.stdout.write(json.dumps(m, ensure_ascii=False) + "\n"); sys.stdout.flush()
def arac_cagir(ad, args):
    a = TABLO.get(ad)
    if not a: return None
    if not isinstance(args, dict): args = {}
    try: s = a[4](args); hata = False
    except AracHatasi as e: s, hata = {"hata": str(e)}, True
    except Exception as e: s, hata = {"hata": f"beklenmeyen hata ({e.__class__.__name__})"}, True
    return {"content": [{"type": "text", "text": json.dumps(s, ensure_ascii=False, indent=1)}], "isError": hata}
def isle(m):
    if not isinstance(m, dict) or m.get("jsonrpc") != "2.0": return
    i, yontem, p = m.get("id"), m.get("method"), m.get("params") or {}
    bildirim = "id" not in m
    if not isinstance(yontem, str): return  # istemcinin yanıtı ya da bozuk ileti
    if yontem == "initialize":
        ist = p.get("protocolVersion"); yanit(i, {"protocolVersion": ist if ist in PROTOKOLLER else PROTOKOLLER[0], "capabilities": {"tools": {"listChanged": False}},
                                                  "serverInfo": {"name": "suflor-arsiv", "title": "Suflor.me toplantı arşivi", "version": SURUM},
                                                  "instructions": "Suflor.me toplantı arşivi (yalnız bu Mac). Yazma araçları önce onay_gerekli döner; kullanıcı onaylamadan onayla: true gönderme."})
    elif yontem == "ping": yanit(i, {}) if not bildirim else None
    elif yontem == "tools/list": yanit(i, {"tools": [{"name": a[0], "description": a[1], "inputSchema": a[2], "annotations": a[3]} for a in ARACLAR]})
    elif yontem == "tools/call":
        s = arac_cagir(p.get("name"), p.get("arguments"))
        if s is None: yanit(i, hata={"code": -32602, "message": f"bilinmeyen araç: {p.get('name')}"})
        else: yanit(i, s)
    elif not bildirim: yanit(i, hata={"code": -32601, "message": f"yöntem yok: {yontem}"})
def main():
    for ln in sys.stdin:
        ln = ln.strip()
        if not ln: continue
        try: m = json.loads(ln)
        except ValueError: yanit(None, hata={"code": -32700, "message": "geçersiz JSON"}); continue
        if isinstance(m, list):
            for x in m: isle(x)
        else: isle(m)
if __name__ == "__main__":
    try: main()
    except (KeyboardInterrupt, BrokenPipeError): pass
