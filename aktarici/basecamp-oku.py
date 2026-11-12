# Suflor.me aktarıcı bölümü: Basecamp OKUMA bağlayıcısı (S282, 12 Kasım). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("basecamp-oku")):
# AYAR, BASE, LOCK, time/json/re/os, gizli_acik, gelistirici_mi, _mtb_kanit (varsa) hazır. Yalnız OKUR (GET); Basecamp'e hiçbir şey yazmaz (yazma yönü S227, ayrı).
# Ne okunur: toplantının ilgili Basecamp projesindeki son yorumlar ve işler (to-do: metin, atanan, vade, durum). Claude'a bağlam olarak ve mutabakat kanıtı olarak gider.
# Ayar: basecamp_oku (açık/kapalı; ayar hiç yazılmamışsa yalnız geliştiricinin kurulumunda açık, beta'da kapalı) ve basecamp: {hesap: <hesap numarası>,
# proje_esleme: {"toplantı başlığı sözcüğü": "Basecamp proje adı"}, anahtar: <Anahtar Zinciri öğe adı, varsayılan suflor-basecamp>}. Belirteç dosyaya/günlüğe/çıktıya yazılmaz.
# GİZLİLİK: gizli toplantıda ve gizli kipte okunmaz; kanıt alıntısı ≤160 karakter, e-posta maskeli, özel nitelikli içerik atılır (_mtb_kanit). Ağ yoksa sessizce boş döner.
# Sınırlar: 30 dk önbellek; en çok 40 istek/10 sn (Basecamp sınırı 50); 429'da Retry-After en çok 1 kez beklenir; ağ/yetki hatasında 5 dk geri çekilme.
import urllib.request as _ur_bc, urllib.error as _ue_bc, subprocess as _sp_bc
BC_API = "https://3.basecampapi.com"; BC_UA = "Suflor.me (okuma)"
BC_ONBELLEK_SN, BC_PENCERE_SN, BC_PENCERE_EN_COK, BC_GERI_SN, BC_SAYFA_EN_COK, BC_EN_COK = 1800, 10, 40, 300, 3, 60
BC = {"onb": {}, "istek": [], "geri": 0.0, "belirtec": (0.0, ""), "hata": 0}
BC_ZAMAN = globals().get("BC_ZAMAN") or time.time
BC_BEKLE = globals().get("BC_BEKLE") or time.sleep
def bc_ayar():
    a = AYAR.get("basecamp") if isinstance(AYAR.get("basecamp"), dict) else {}
    return a
def bc_acik():
    v = AYAR.get("basecamp_oku")
    if v is None: v = bool(gelistirici_mi()) if "gelistirici_mi" in globals() else False
    if not v or ("gizli_acik" in globals() and gizli_acik()): return False
    return bool(str(bc_ayar().get("hesap") or "").strip())
def _bc_belirtec():
    t, v = BC["belirtec"]
    if v and BC_ZAMAN() - t < 600: return v
    try: v = _sp_bc.run(["/usr/bin/security", "find-generic-password", "-s", str(bc_ayar().get("anahtar") or "suflor-basecamp"), "-w"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception: v = ""
    BC["belirtec"] = (BC_ZAMAN(), v); return v
def _bc_http(url):  # → (gövde, link_sonraki) ; hata → istisna. Testler BC_HTTP ile ezer (url → (json, sonraki_url))
    k = _bc_belirtec()
    if not k: raise OSError("belirteç yok")
    r = _ur_bc.Request(url, headers={"Authorization": "Bearer " + k, "User-Agent": BC_UA, "Accept": "application/json"})
    with _ur_bc.urlopen(r, timeout=12) as f:
        g = json.loads(f.read().decode("utf-8", "replace")); ln = f.headers.get("Link") or ""
    m = re.search(r'<([^>]+)>;\s*rel="next"', ln)
    return g, (m.group(1) if m else None)
def _bc_sinir():  # kayan pencerede istek sayacı; doluysa pencere bitene kadar bekler (en çok BC_PENCERE_SN)
    n = BC_ZAMAN(); BC["istek"] = [t for t in BC["istek"] if n - t < BC_PENCERE_SN]
    if len(BC["istek"]) >= BC_PENCERE_EN_COK: BC_BEKLE(max(0.0, BC_PENCERE_SN - (n - BC["istek"][0])) + 0.05)
    BC["istek"].append(BC_ZAMAN())
def _bc_al(url):  # tek istek: sınır + 429 bir kez; başarısızlık → None (5 dk geri çekilme)
    for deneme in (0, 1):
        _bc_sinir()
        try: return (globals().get("BC_HTTP") or _bc_http)(url)
        except _ue_bc.HTTPError as e:
            if e.code == 429 and deneme == 0:
                try: bk = min(float(e.headers.get("Retry-After") or 2), 10.0)
                except Exception: bk = 2.0
                BC_BEKLE(bk); continue
            BC["hata"] += 1; BC["geri"] = BC_ZAMAN() + BC_GERI_SN; return None
        except Exception:
            BC["hata"] += 1; BC["geri"] = BC_ZAMAN() + BC_GERI_SN; return None
    return None
def _bc_liste(url, en_cok=BC_EN_COK):
    out = []
    for _ in range(BC_SAYFA_EN_COK):
        if not url or len(out) >= en_cok or BC_ZAMAN() < BC["geri"]: break
        r = _bc_al(url)
        if r is None: break
        g, url = r
        out += [x for x in g if isinstance(x, dict)] if isinstance(g, list) else []
    return out[:en_cok]
def _bc_duz(h): return " ".join(re.sub(r"<[^>]+>", " ", str(h or "")).replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").split())
def _bc_kok(s): return {w[:5] for w in re.findall(r"\w+", str(s or "").replace("İ", "i").replace("I", "ı").lower()) if len(w) >= 4}
def _bc_proje_sec(projeler, baslik):  # toplantı başlığına göre ilgili projeler: önce eşleme tablosu, sonra ad–başlık ortak kökleri
    b = str(baslik or "").lower(); esl = bc_ayar().get("proje_esleme") if isinstance(bc_ayar().get("proje_esleme"), dict) else {}
    ad = [str(v).lower() for k, v in esl.items() if str(k).lower() and str(k).lower() in b]
    if ad: return [p for p in projeler if str(p.get("name") or "").lower() in ad][:2]
    kb = _bc_kok(baslik)
    return [p for p in projeler if kb and len(kb & _bc_kok(p.get("name"))) >= 1][:2]
def bc_oku(baslik=None):
    """→ {"projeler": [ad], "yorumlar": [{proje, tarih, yazan_yok, metin}], "isler": [{proje, metin, sahip, vade, tamam, tarih}]}; kapalı/gizli/ağ yok → boş. 30 dk önbellek."""
    bos = {"projeler": [], "yorumlar": [], "isler": []}
    if not bc_acik() or BC_ZAMAN() < BC["geri"]: return bos
    hs = str(bc_ayar().get("hesap")).strip(); kok = f"{BC_API}/{hs}"; an = (hs, str(baslik or "").lower()); o = BC["onb"].get(an)
    if o and BC_ZAMAN() - o[0] < BC_ONBELLEK_SN: return o[1]
    try:
        tum = _bc_liste(f"{kok}/projects.json", 100)
        if not tum: return bos
        sec = _bc_proje_sec(tum, baslik) if baslik else tum[:3]; s = {"projeler": [str(p.get("name") or "")[:80] for p in sec], "yorumlar": [], "isler": []}
        for p in sec:
            pid, pad = p.get("id"), str(p.get("name") or "")[:80]
            for r in _bc_liste(f"{kok}/projects/recordings.json?type=Comment&bucket={pid}&sort=updated_at&direction=desc", 20):
                m = _bc_duz(r.get("content") or r.get("title"))
                if m: s["yorumlar"].append({"proje": pad, "tarih": str(r.get("updated_at") or r.get("created_at") or "")[:10], "metin": m[:400]})
            for r in _bc_liste(f"{kok}/projects/recordings.json?type=Todo&bucket={pid}&sort=updated_at&direction=desc", 40):
                m = _bc_duz(r.get("title") or r.get("content"))
                if m: s["isler"].append({"proje": pad, "metin": m[:300], "sahip": ", ".join(str(a.get("name") or "") for a in (r.get("assignees") or []) if isinstance(a, dict))[:120],
                                         "vade": str(r.get("due_on") or "")[:10], "tamam": bool(r.get("completed")), "tarih": str(r.get("updated_at") or "")[:10]})
        BC["onb"][an] = (BC_ZAMAN(), s)
        if len(BC["onb"]) > 20: BC["onb"].pop(next(iter(BC["onb"])))
        return s
    except Exception: return bos
def _bc_es(a, metin, en_az=2): return bool(a) and len(a & _bc_kok(metin)) >= min(en_az, len(a))
def bc_kanit(x):
    """mutabakat.py imzası: x = kayıt {metin, tarih, baslik, …} → [{kaynak:"basecamp", tarih, alinti ≤160}] (en çok 2; kayıt tarihinden sonraki, konuyla örtüşen yorum/iş)"""
    try:
        if not isinstance(x, dict) or not bc_acik(): return []
        d = bc_oku(x.get("baslik")); a = _bc_kok(x.get("metin")); t0 = str(x.get("tarih") or "")[:10]; out = []
        for y in d["yorumlar"]:
            if y["tarih"] >= t0 and _bc_es(a, y["metin"]): out.append((y["tarih"], f"{y['proje']} yorum: {y['metin']}"))
        for i in d["isler"]:
            if i["tarih"] >= t0 and _bc_es(a, i["metin"]):
                out.append((i["tarih"], f"{i['proje']} iş ({'tamamlandı' if i['tamam'] else 'açık'}" + (f", vade {i['vade']}" if i["vade"] else "") + (f", {i['sahip']}" if i["sahip"] else "") + f"): {i['metin']}"))
        k = [_mtb_kanit("basecamp", t, m) if "_mtb_kanit" in globals() else {"kaynak": "basecamp", "tarih": t, "alinti": re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[adres]", m)[:160]} for t, m in sorted(out, reverse=True)]
        return [z for z in k if z][:2]
    except Exception: return []
def bc_baglam(baslik=None, en_cok=6):  # Claude bağlamına kısa metin (kapalı/gizli/boş → ""); kişi e-postası yok, atanan adı iş sahibi olarak gelir
    d = bc_oku(baslik)
    if not (d["yorumlar"] or d["isler"]): return ""
    s = [f"Basecamp ({', '.join(d['projeler'])}):"]
    s += [f"- yorum {y['tarih']}: {y['metin'][:160]}" for y in d["yorumlar"][:en_cok]] + [f"- iş ({'tamam' if i['tamam'] else 'açık'}{', vade ' + i['vade'] if i['vade'] else ''}{', ' + i['sahip'] if i['sahip'] else ''}): {i['metin'][:160]}" for i in d["isler"][:en_cok]]
    return re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[adres]", "\n".join(s))
