# Suflor.me aktarıcı bölümü: Basecamp OKUMA bağlayıcısı (S282, 12 Kasım). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("basecamp-oku")):
# AYAR, BASE, LOCK, time/json/re/os, gizli_acik, gelistirici_mi, _mtb_kanit (varsa) hazır. Yalnız OKUR (GET); Basecamp'e hiçbir şey yazmaz (yazma yönü S227, ayrı).
# Ne okunur: toplantının ilgili Basecamp projesindeki son yorumlar ve işler (to-do: metin, atanan, vade, durum). Claude'a bağlam olarak ve mutabakat kanıtı olarak gider.
# Ayar: basecamp_oku (açık/kapalı; ayar hiç yazılmamışsa yalnız geliştiricinin kurulumunda açık, beta'da kapalı) ve basecamp: {hesap: <hesap numarası>,
# proje_esleme: {"toplantı başlığı sözcüğü": "Basecamp proje adı"}, anahtar: <Anahtar Zinciri öğe adı, varsayılan suflor-basecamp>}. Belirteç dosyaya/günlüğe/çıktıya yazılmaz.
# GİZLİLİK: gizli toplantıda ve gizli kipte okunmaz; kanıt alıntısı ≤160 karakter, e-posta maskeli, özel nitelikli içerik atılır (_mtb_kanit). Ağ yoksa sessizce boş döner.
# Yenileme: erişim belirteci (~2 hafta) Anahtar Zinciri'nde <anahtar> öğesinde; yenileme bilgisi (refresh_token, client_id, client_secret, bitis) <anahtar>-oauth öğesinde tek JSON (base64; security -i tırnaklı değerde bozulur) (basecamp-baglan.py yazar).
# Süre dolmuşsa ya da 401 gelirse bir kez yenilenir ve istek bir kez tekrarlanır; yenilenemezse günlüğe tek satır, sessizce boş.
# Sınırlar: 30 dk önbellek; en çok 40 istek/10 sn (Basecamp sınırı 50); 429'da Retry-After en çok 1 kez beklenir; ağ/yetki hatasında 5 dk geri çekilme.
import base64, urllib.request as _ur_bc, urllib.error as _ue_bc, subprocess as _sp_bc
BC_API = "https://3.basecampapi.com"; BC_UA = "Suflor.me (https://github.com/suflorme/suflor)"
BC_LP = os.environ.get("SUFLOR_BC_LAUNCHPAD") or "https://launchpad.37signals.com"  # testte yerel sahte sunucuya yönlenir
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
def _bc_servis(): return str(bc_ayar().get("anahtar") or "suflor-basecamp")
def _bc_kc_oku(servis):
    if globals().get("BC_KC_OKU"): return globals()["BC_KC_OKU"](servis)
    try: return _sp_bc.run(["/usr/bin/security", "find-generic-password", "-s", servis, "-w"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception: return ""
def _bc_kc_yaz(servis, hesap, deger):  # değer komut satırına (ps'te görünür) konmaz: `security -i` komutu stdin'den okur
    if globals().get("BC_KC_YAZ"): return globals()["BC_KC_YAZ"](servis, hesap, deger)
    if any(c in str(deger) + servis + hesap for c in '"\\\n\r'): return False
    try: return _sp_bc.run(["/usr/bin/security", "-i"], input=f'add-generic-password -U -s "{servis}" -a "{hesap}" -w "{deger}"\n', capture_output=True, text=True, timeout=15).returncode == 0
    except Exception: return False
def _bc_oauth():
    try:
        v = _bc_kc_oku(_bc_servis() + "-oauth")
        try: v = base64.b64decode(v, validate=True).decode()
        except Exception: pass  # base64 değilse düz JSON
        d = json.loads(v); return d if isinstance(d, dict) else {}
    except Exception: return {}
def _bc_post(url):  # Launchpad yenileme isteği (gövdesiz POST, parametreler adreste) → json
    r = _ur_bc.Request(url, data=b"", method="POST", headers={"User-Agent": BC_UA, "Accept": "application/json"})
    with (globals().get("BC_URLOPEN") or _ur_bc.urlopen)(r, timeout=15) as f: return json.loads(f.read().decode("utf-8", "replace"))
def _bc_yenile():  # → yeni erişim belirteci ya da "" (başarısızlıkta günlüğe tek satır)
    import urllib.parse as _up
    o = _bc_oauth()
    try:
        q = _up.urlencode({"type": "refresh", "refresh_token": o["refresh_token"], "client_id": o["client_id"], "client_secret": o["client_secret"], "redirect_uri": o.get("redirect_uri") or "http://127.0.0.1:8770/basecamp/geri"})
        g = (globals().get("BC_POST") or _bc_post)(f"{BC_LP}/authorization/token?{q}"); yeni = str(g["access_token"])
        o["bitis"] = BC_ZAMAN() + int(g.get("expires_in") or 1209600)
        if g.get("refresh_token"): o["refresh_token"] = str(g["refresh_token"])
        if not (_bc_kc_yaz(_bc_servis(), "access_token", yeni) and _bc_kc_yaz(_bc_servis() + "-oauth", "oauth", base64.b64encode(json.dumps(o).encode()).decode())): raise OSError("anahtar zinciri yazılamadı")
        BC["belirtec"] = (BC_ZAMAN(), yeni); return yeni
    except Exception:
        print("BASECAMP: bağlantı yenilenemedi — basecamp-baglan.command'ı yeniden çalıştır"); BC["belirtec"] = (0.0, ""); return ""
def _bc_belirtec():
    t, v = BC["belirtec"]
    if v and BC_ZAMAN() - t < 600: return v
    v = _bc_kc_oku(_bc_servis()); o = _bc_oauth()
    if o.get("bitis") and BC_ZAMAN() >= float(o["bitis"]) - 60: v = _bc_yenile() or ""
    BC["belirtec"] = (BC_ZAMAN(), v); return v
def _bc_http(url, yenilendi=False):  # → (gövde, link_sonraki) ; hata → istisna. Testler BC_HTTP ile ezer (url → (json, sonraki_url))
    k = _bc_belirtec()
    if not k: raise OSError("belirteç yok")
    r = _ur_bc.Request(url, headers={"Authorization": "Bearer " + k, "User-Agent": BC_UA, "Accept": "application/json"})
    try:
        with (globals().get("BC_URLOPEN") or _ur_bc.urlopen)(r, timeout=12) as f:
            g = json.loads(f.read().decode("utf-8", "replace")); ln = f.headers.get("Link") or ""
    except _ue_bc.HTTPError as e:
        if e.code == 401 and not yenilendi and _bc_yenile(): return _bc_http(url, True)
        raise
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
