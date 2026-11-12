#!/usr/bin/env python3
# Zekâ karnesi — tek kaynak (12 Kasım: "farklı iş ve fonksiyonlardaki başarı, öngörü ve analiz için zekâ puanı verelim ve gelişimini takip edelim").
# kullanim.py gibi iki yerden çağrılır: ölçüm aracı (`olcum.py zeka`, rapor) ve aktarıcı (aktarici/dusunme.py: günde bir kayıt + kullanıcı puanı sorusu;
# aktarici/beta-veri.py: haftalık beta paketine yalnız sayı). Hesap burada, aktarıcıya gömülmez. Hiçbir ağ işlemi yok.
#
# Çerçeve: işlev × boyut. Boyutlar: basari (doğru ya da işe yarar çıktı oranı) · ongoru (önceden söyleyip doğru çıkan) · analiz (doğru durum tespiti).
#   Her ölçüt bir oran (0–1) ve örnek sayısı (n) verir; n < asgari ise puanı yok ("yetersiz veri") — uydurulmaz, ortalamaya girmez.
#   Boyut puanı = ölçütlerin ağırlıklı ortalaması (yalnız yeterli verisi olanlar); işlev puanı = boyutların ağırlıklı ortalaması (basari 0,5 · ongoru 0,25 · analiz 0,25;
#   eksik boyutun ağırlığı ötekilere dağılır, "kismi" işaretlenir). Genel puan = puanı olan işlevlerin düz ortalaması.
#   Kullanıcının kendi puanı (1–5, canli/zeka-puan.jsonl) AYRI tutulur, karneyle karıştırılmaz; raporda yan yana durur.
# Örtük sinyaller: öneri yoksayıldı/reddedildi, kullanıcı aynı soruyu kısa sürede yeniden sordu, cevabı düzeltti ("hayır, …"), kart geçildi, cevap beklenen
#   denen e-postanın son iletisi zaten kullanıcının (= analiz hatası), birleştirilen çift iş geri alındı, öğrenilen bilgiye "Yanlış" dendi.
# Gizlilik: okuma yalnız yerel canli/ kayıtlarından; çıktı (zeka-karne.jsonl, beta paketi) yalnız sayı ve işlev/ölçüt adı. Soru metni yalnız bellekte
#   benzerlik için okunur, hiçbir yere yazılmaz. Deneme toplantıları (etiket "deneme" ya da dosya adında test/deneme) sayılmaz.
import datetime, gzip, json, os, re, time

ISLEVLER = {  # anahtar: (Türkçe ad, İngilizce ad) — anahtarlar teshis.py SAYIM "zeka_karne"/"zeka_kullanici" ile aynı kalmalı
    "konus": ("Konuş / sohbet", "Talk / chat"), "gun_plani": ("Gün planı (düşünme turu)", "Daily plan"), "eposta": ("E-posta takibi", "Email follow-up"),
    "toplanti": ("Toplantıda kartlar", "Meeting cards"), "hazirlik": ("Hazırlık ve gündem", "Preparation and agenda"),
    "proaktif": ("Kendiliğinden öneriler", "Proactive suggestions"), "kayit": ("Kararlar ve işler", "Decisions and tasks"),
    "dokum": ("Döküm", "Transcript"), "tazi": ("Tazı (dış araştırma)", "Tazı (outside research)"), "kesisim": ("Kesişim (çapraz kontrol)", "Cross-check")}
BOYUTLAR = {"basari": ("Başarı", 0.5), "ongoru": ("Öngörü", 0.25), "analiz": ("Analiz", 0.25)}
SORU_ISLEV = ("konus", "gun_plani", "eposta", "toplanti")  # kullanıcı puanı sorusu: en çok 4 işlev, yalnız son dönemde kullanılanlar
SORU_ARALIK_GUN, SORU_ERTELE_GUN = 7, 2  # haftada bir (12 Kasım; geliştiricide ve betada aynı)
KARNE, PUAN, PLAN_IZ = "zeka-karne.jsonl", "zeka-puan.jsonl", "dusunme-iz.jsonl"
DUZELTME = re.compile(r"(?i)^\s*(hayır|hayir|yok\b|yanlış|yanlis|öyle değil|oyle degil|değil|degil|no\b|wrong|that'?s not)|yanlış anla|yanlış söyle|demedim|bunu sormadım|i didn'?t (say|ask)")
DENEME = re.compile(r"(?i)(test|deneme)")

# ---------- okuma ----------
def kayit_satirlari(canli, ad):  # eski satırlar canli/arsiv/<ad>.gz, yeniler canli/<ad> (aktarıcı kayıt döndürme düzeni)
    out = []
    for yol, ac in ((os.path.join(canli, "arsiv", ad + ".gz"), lambda y: gzip.open(y, "rt", encoding="utf-8")), (os.path.join(canli, ad), lambda y: open(y, encoding="utf-8"))):
        try:
            with ac(yol) as f: out += [l for l in f if l.strip()]
        except (OSError, EOFError): pass
    return out
def jsonl(canli, ad):
    out = []
    for l in kayit_satirlari(canli, ad):
        try:
            r = json.loads(l)
            if isinstance(r, dict): out.append(r)
        except ValueError: pass
    return out
def json_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return None
def ts(x):  # float/int ya da ISO metin (Z ya da saat dilimsiz) → epoch; okunamazsa None
    if isinstance(x, bool) or x is None: return None
    if isinstance(x, (int, float)): return float(x)
    try:
        d = datetime.datetime.fromisoformat(str(x).strip().replace("Z", "+00:00"))
        return (d if d.tzinfo else d.astimezone()).timestamp()
    except ValueError: return None
def _gun(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except ValueError: return None

class Baglam:
    """Bir hesaplamanın girdileri: canli klasörü, uygulama klasörü (ogrenilen.jsonl), pencere, şimdi; dosyalar bir kez okunur."""
    def __init__(self, canli, gun=30, simdi=None, gecmis=None):
        self.canli = canli; self.uyg = os.path.dirname(os.path.abspath(canli)); self.gun = gun
        self.simdi = float(simdi if simdi is not None else time.time()); self.sinir = self.simdi - gun * 86400; self.gecmis = gecmis; self._o = {}
    def j(self, ad):
        if ad not in self._o: self._o[ad] = jsonl(self.canli, ad)
        return self._o[ad]
    def d(self, ad):
        k = "@" + ad
        if k not in self._o: self._o[k] = json_oku(os.path.join(self.canli, ad))
        return self._o[k]
    def icinde(self, t): return t is not None and self.sinir <= t <= self.simdi + 60
    def deneme_dosyalar(self):
        if "@deneme" not in self._o:
            self._o["@deneme"] = {r.get("dosya") for r in self.j("claude-cagri.jsonl") if r.get("is") == "toplanti" and r.get("etiket") == "deneme" and r.get("dosya")}
        return self._o["@deneme"]
    def deneme_mi(self, dosya): return bool(dosya) and (dosya in self.deneme_dosyalar() or bool(DENEME.search(str(dosya))))

def _soz(b):  # soz.jsonl → {söz kimliği: {kaynak, sunuldu, sonuc}} (pencere içinde); sonuç: kullanıcının ilk gerçek işlemi, yalnız otomatik yoksay varsa yoksay
    if "@soz" in b._o: return b._o["@soz"]
    s = {}
    for r in b.j("soz.jsonl"):
        t = ts(r.get("t")); i = r.get("id")
        if not i or not b.icinde(t): continue
        d = s.setdefault(i, {"kaynak": r.get("kaynak") or "?", "sunuldu": False, "sonuc": None, "yoksay": False}); o = r.get("olay")
        if o == "teslim" or (o == "sunuldu" and r.get("karar") == "simdi"): d["sunuldu"] = True
        elif o == "iptal": d["sunuldu"] = False
        elif o == "sonuc":
            if r.get("sonuc") == "yoksay": d["yoksay"] = True
            elif d["sonuc"] is None: d["sonuc"] = r.get("sonuc")
    for d in s.values(): d["son"] = d["sonuc"] or ("yoksay" if d["yoksay"] else None)
    b._o["@soz"] = s; return s
def _soz_say(b, kaynaklar):
    say = {"kabul": 0, "ret": 0, "ertele": 0, "yoksay": 0}
    for d in _soz(b).values():
        if d["sunuldu"] and d["kaynak"] in kaynaklar and d["son"] in say: say[d["son"]] += 1
    return say

# ---------- ölçütler: her biri (oran, n, kanıt) ya da None (kaynak yok) döner ----------
def m_konus_hatasiz(b):
    rs = [r for r in b.j("claude-cagri.jsonl") if r.get("is") == "bas-konus" and b.icinde(ts(r.get("at")))]
    hata = sum(1 for r in rs if r.get("hata"))
    return ((len(rs) - hata) / len(rs) if rs else None), len(rs), f"{hata}/{len(rs)} cevapta hata"
def _konus_sorular(b):
    rs = []
    for r in b.j("konus-gecmis.jsonl"):
        t = ts(r.get("at")); q = str(r.get("soru") or "").strip()
        if q and b.icinde(t): rs.append((t, q))
    rs.sort(); return rs
def _kelimeler(q): return {w for w in re.findall(r"\w{3,}", q.lower())}
def m_konus_tekrar(b):  # 10 dk içinde aynı (Jaccard ≥ 0,6) soru yeniden = önceki cevap yetmedi
    rs = _konus_sorular(b); tekrar = 0
    for i, (t, q) in enumerate(rs):
        a = _kelimeler(q)
        for t0, q0 in rs[max(0, i - 6):i]:
            b0 = _kelimeler(q0)
            if t - t0 <= 600 and a and b0 and len(a & b0) / len(a | b0) >= 0.6: tekrar += 1; break
    return ((len(rs) - tekrar) / len(rs) if rs else None), len(rs), f"{tekrar}/{len(rs)} soru 10 dk içinde yeniden soruldu"
def m_konus_duzeltme(b):  # bir sonraki soru 3 dk içinde "hayır, …/yanlış …" ile başlıyorsa önceki cevap düzeltildi
    rs = _konus_sorular(b); n = max(0, len(rs) - 1)
    d = sum(1 for (t0, _), (t, q) in zip(rs, rs[1:]) if t - t0 <= 180 and DUZELTME.search(q))
    return ((n - d) / n if n else None), n, f"{d}/{n} cevap bir sonraki soruda düzeltildi"

def _plan_izleri(b):  # dusunme-iz.jsonl (aktarici/dusunme.py, metinsiz): gün başına son başarılı plan {gun, odak, dikkat, damga}
    g = {}
    for r in b.j(PLAN_IZ):
        if r.get("durum") == "tamam" and isinstance(r.get("damga"), dict) and _gun(r.get("gun")): g[r["gun"]] = r
    return [g[k] for k in sorted(g)]
def m_plan_tur(b):
    rs = [r for r in b.j(PLAN_IZ) if b.icinde(ts(r.get("t")))]
    ok = sum(1 for r in rs if r.get("durum") == "tamam")
    return ((ok / len(rs)) if rs else None), len(rs), f"{len(rs) - ok}/{len(rs)} turda plan çıkmadı (hata/bozuk)"
def m_plan_kabul(b):
    s = _soz_say(b, {"gun_plani"}); n = sum(s.values())
    return ((s["kabul"] / n) if n else None), n, f"{s['kabul']}/{n} plan bildirimi açıldı ya da onaylandı; {s['yoksay']} yoksay, {s['ret']} ret"
def m_plan_odak(b):  # odaktaki iş 3 gün içinde kapandı mı (sonraki planların damgasından çıktı)
    ps = _plan_izleri(b); n = ok = 0
    for i, p in enumerate(ps):
        g = _gun(p["gun"]); sonra = [q for q in ps[i + 1:] if 0 < (_gun(q["gun"]) - g).days <= 3]
        if not sonra or not b.icinde(ts(p["gun"] + "T12:00:00")): continue
        for k in p.get("odak") or []:
            n += 1; ok += k not in sonra[-1]["damga"]
    return ((ok / n) if n else None), n, f"{ok}/{n} odak işi 3 gün içinde kapandı"
def _vade(v):
    try: return _gun(str(v).split("|", 1)[1]) if "|" in str(v) else None
    except IndexError: return None
def m_plan_risk(b):  # vadesi kayan ya da geçen iş, önceki 3 günün planında (odak/dikkat) önceden anılmış mıydı
    ps = _plan_izleri(b); n = ok = 0
    for p, q in zip(ps, ps[1:]):
        gp, gq = _gun(p["gun"]), _gun(q["gun"])
        if not b.icinde(ts(q["gun"] + "T12:00:00")): continue
        anilan = set()
        for r in ps:
            if 0 <= (gp - _gun(r["gun"])).days <= 3: anilan |= set(r.get("odak") or []) | set(r.get("dikkat") or [])
        for k, vq in q["damga"].items():
            if k not in p["damga"]: continue
            a, z = _vade(p["damga"][k]), _vade(vq)
            if (a and z and z > a) or (z and gp <= z < gq):
                n += 1; ok += k in anilan
    return ((ok / n) if n else None), n, f"vadesi kayan/geçen {n} işten {ok}'i önceden plandaydı"
def m_ogrenilen(b):  # düşünme turunun öğrendiği bilgiler: son durum onaylı (Doğru) / geçersiz (Yanlış ya da model geçersizledi); hâlâ "otomatik" olan sayılmaz
    son, ilk = {}, {}
    for r in jsonl(b.uyg, "ogrenilen.jsonl") if os.path.isfile(os.path.join(b.uyg, "ogrenilen.jsonl")) else []:
        i = r.get("id")
        if not i: continue
        if i not in ilk: ilk[i] = r
        son[i] = r.get("durum")
    n = ok = 0
    for i, r in ilk.items():
        if not str(r.get("kaynak") or "").startswith("düşünme turu") or not b.icinde(ts(r.get("tarih"))) or son[i] == "otomatik": continue
        n += 1; ok += son[i] == "onayli"
    return ((ok / n) if n else None), n, f"{ok}/{n} öğrenilen bilgi onaylandı"

def _posta(b):
    p = b.d("posta.json") or {}; ms = p.get("iletiler") if isinstance(p, dict) else None
    return {str(m.get("id")): m for m in ms or [] if isinstance(m, dict)}
def _zd(b):  # eposta-takip.json "zd": {"z:<zincir>|<son ileti id>": {d: durum, t}} — pencere içindekiler
    zd = ((b.d("eposta-takip.json") or {}).get("zd") or {})
    out = []
    for k, v in zd.items():
        if not isinstance(v, dict) or "|" not in k: continue
        t = ts(v.get("t"))
        if b.icinde(t): out.append((k.split("|", 1)[0].split(":", 1)[-1], k.split("|", 1)[1], v.get("d"), t))
    return out
def _zd5(b):  # _zd + aciliyet: (zincir, son ileti, durum, aciliyet, zaman)
    zd = ((b.d("eposta-takip.json") or {}).get("zd") or {}); out = []
    for k, v in zd.items():
        if not isinstance(v, dict) or "|" not in k: continue
        t = ts(v.get("t"))
        if b.icinde(t): out.append((k.split("|", 1)[0].split(":", 1)[-1], k.split("|", 1)[1], v.get("d"), v.get("a") if isinstance(v.get("a"), int) else 1, t))
    return out
def m_eposta_kacirma(b):  # kaçırma: "bilgi" ya da düşük öncelikli (aciliyet ≤ 1) "senden bekleniyor" denen zincire kullanıcı 7 gün içinde cevap yazdı = önemsiz sanılan önemliymiş (yalnız sayı; olgunlaşma: 3 gün geçti ya da yazdı)
    ms = _posta(b).values(); n = kac = 0
    if not ms: return None, 0, "posta.json yok"
    en_eski = min((ts(m.get("t")) or 9e12) for m in ms)
    for z, _son, d, a, t in _zd5(b):
        if t < en_eski or not (d == "bilgi" or (d == "senden_bekleniyor" and a <= 1)): continue
        yazdi = any(str(m.get("zincir")) == z and m.get("gonderilen") and t < (ts(m.get("t")) or 0) <= t + 7 * 86400 for m in ms)
        if yazdi or b.simdi - t >= 3 * 86400: n += 1; kac += yazdi
    return (((n - kac) / n) if n else None), n, f"bilgi/düşük öncelikli denen {n} zincirin {kac}'ine sonradan cevap yazıldı (kaçırma)"
def m_eposta_duzeltme(b):  # kullanıcı düzeltmesi: "yanlış öncelik" tepkisi + "bu kişi önemli" (canli/eposta-tepki.jsonl, yalnız sayım) / pencerede değerlendirilen zincir
    rs = [r for r in b.j("eposta-tepki.jsonl") if b.icinde(ts(r.get("t")))]; yo = sum(1 for r in rs if r.get("islem") == "yanlis_oncelik"); ok_ = sum(1 for r in rs if r.get("islem") == "onemli_kisi")
    n = len({(z, son) for z, son, _d, _a, _t in _zd5(b)})
    return (max(0.0, 1 - (yo + ok_) / n) if n else None), n, f"{yo + ok_} düzeltme ({yo} yanlış öncelik, {ok_} 'bu kişi önemli') / {n} değerlendirilen zincir"
def m_eposta_kabul(b):
    s = _soz_say(b, {"eposta"}); n = sum(s.values())
    return ((s["kabul"] / n) if n else None), n, f"{s['kabul']}/{n} e-posta bildirimi işe yaradı; {s['yoksay']} yoksay, {s['ret']} ret"
def m_eposta_ongoru(b):  # "senden bekleniyor" denen zincire kullanıcı 7 gün içinde gerçekten yazdı mı (olgunlaşma: 3 gün geçti ya da yazdı)
    ms = _posta(b).values(); n = ok = 0
    if not ms: return None, 0, "posta.json yok"
    en_eski = min((ts(m.get("t")) or 9e12) for m in ms)
    for z, _son, d, t in _zd(b):
        if d != "senden_bekleniyor" or t < en_eski: continue
        yazdi = any(str(m.get("zincir")) == z and m.get("gonderilen") and t < (ts(m.get("t")) or 0) <= t + 7 * 86400 for m in ms)
        if yazdi or b.simdi - t >= 3 * 86400: n += 1; ok += yazdi
    return ((ok / n) if n else None), n, f"cevap bekleniyor denen {n} zincirin {ok}'ine 7 gün içinde cevap yazıldı"
def m_eposta_durum(b):  # değerlendirme anındaki son ileti: senden_bekleniyor ise son yazan sen olmamalı; donus_bekliyorsun ise son yazan sen olmalısın
    ms = _posta(b); n = hata = 0
    for _z, son, d, _t in _zd(b):
        m = ms.get(son)
        if d not in ("senden_bekleniyor", "donus_bekliyorsun") or not m: continue
        n += 1; hata += bool(m.get("gonderilen")) == (d == "senden_bekleniyor")
    return (((n - hata) / n) if n else None), n, f"{hata}/{n} e-posta durumu yanlış (ör. cevaplanmış maile 'bekliyor')"
def m_eposta_yoksay(b):  # kullanıcı bildirilen e-postayı kalıcı "önemsiz" saydı = önem tespiti yanlış
    d = b.d("eposta-takip.json") or {}
    bil = [k for k, v in (d.get("bildirilen") or {}).items() if b.icinde(ts(v))]
    yok = [k for k, v in (d.get("yoksay") or {}).items() if b.icinde(ts(v)) or not isinstance(v, (str, int, float))]
    n = len(bil)
    return (((n - min(len(yok), n)) / n) if n else None), n, f"{len(yok)}/{n} bildirilen e-posta kalıcı yoksayıldı"

def _kartlar(b, turler):  # kartın ilk kaydı (tür, dosya, zaman) + son durumu → (yarar, olumsuz); okundu/açık sayılmaz
    ilk, son = {}, {}
    for r in b.j("kartlar.jsonl"):
        i = r.get("id")
        if r.get("kind") and i not in ilk: ilk[i] = r
        if r.get("status"): son[i] = r["status"]
    y = o = 0
    for i, r in ilk.items():
        if r.get("kind") not in turler or not b.icinde(ts(r.get("at"))) or b.deneme_mi(r.get("file")): continue
        s = son.get(i)
        if s in ("yapildi", "onaylandi"): y += 1
        elif s in ("gecildi", "reddedildi"): o += 1
    return y, o
def m_kart_yarar(b):
    y, o = _kartlar(b, {"cevap", "soyle", "not", "bilgi", "sor"}); n = y + o
    return ((y / n) if n else None), n, f"{y}/{n} kart ✓ (geçilen {o}; yalnız okunan sayılmaz)"
def m_kart_uyari(b):
    y, o = _kartlar(b, {"dikkat", "dur", "belirt", "duygu"}); n = y + o
    return ((y / n) if n else None), n, f"{y}/{n} uyarı kartı ✓ (geçilen {o})"
def _gundem_izlendi(b, dosya):  # toplantı dökümünde (canli/<dosya>) en az bir "**GÜNDEM**" satırı (✓ ya da ✗) var mı = gündem toplantıda gerçekten izlendi mi
    try:
        with open(os.path.join(b.canli, os.path.basename(str(dosya))), encoding="utf-8") as f:
            return any("**GÜNDEM**" in l for l in f)
    except OSError: return False
def m_gundem(b):  # karne: gündemin kaçı konuşuldu (hazırlığın toplantıda çıkacak konuyu bilmesi)
    # 12 Kasım bulgusu: 0/13, 0/12, 0/10 gibi sıfırlar "hiçbiri konuşulmadı" değil "gündem izlenmedi" (dökümde tek GÜNDEM satırı yok, işaretleme hiç çalışmamış; toplantılar 33–158 dk, 4–6 karar).
    # Sıfır işaret + dökümde GÜNDEM satırı yok (ya da döküm bulunamıyor) → ölçülemedi: payda dışı. Sıfır işaret ama GÜNDEM satırları var (✗) → gerçek sıfır, sayılır.
    # Satırdaki "gundem_izlendi" alanı (toplanti-claude.py karne_satiri_yaz, 12 Kasım) tercih edilir; yoksa (eski satır) döküm dosyasına bakılır.
    son = {}; izl = {}  # aynı toplantının karnesi birden çok kez yazılabilir (ara karne): dosya başına son karne
    for r in b.j("karneler.jsonl"):
        g = str(((r.get("olcu") or {}).get("gundem")) or ""); m = re.fullmatch(r"(\d+)/(\d+)", g)
        if m and b.icinde(ts(r.get("at"))) and not b.deneme_mi(r.get("dosya")):
            k = r.get("dosya") or r.get("at"); son[k] = (int(m.group(1)), int(m.group(2)))
            if isinstance(r.get("gundem_izlendi"), bool): izl[k] = r["gundem_izlendi"]
            else: izl.pop(k, None)
    izlenmeyen = [k for k, (x, _) in son.items() if x == 0 and not (izl[k] if k in izl else _gundem_izlendi(b, k))]
    for k in izlenmeyen: del son[k]
    a = sum(x for x, _ in son.values()); t = sum(y for _, y in son.values()); top = len(son)
    ek = f" ({len(izlenmeyen)} toplantıda gündem izlenmedi, payda dışı)" if izlenmeyen else ""
    return ((min(a, t) / t) if t else None), t, f"{top} toplantıda {a}/{t} gündem maddesi konuşuldu{ek}"
def _guncellik_satirlari(b):  # guncellik.jsonl (yapi.guncellik_karne, metinsiz): zaman sırasıyla aday satırları; özet satırları ("ozet") ve deneme/pencere dışı atılır
    xs = [r for r in b.j("guncellik.jsonl") if isinstance(r, dict) and r.get("id") and r.get("durum") and b.icinde(ts(r.get("at")))]
    return sorted(xs, key=lambda r: ts(r.get("at")) or 0)
GN_ONERILEN = {"gundeme_bagla", "ek_oneri", "taslak"}  # kullanıcıya "açık ve ilgili" diye sunulan kararlar (belirsiz yalnız modele gider, gecmis bağlamdır)
GN_BAYAT = {"bayat", "bitti", "yerini_aldi"}
def m_bayat_oneri(b):  # önerilen kayıt (kimlik başına), son gözlemde bayat/bitmiş/yerini alınmış çıktıysa kötü; oran = bayat çıkmayan
    son = {}
    for r in _guncellik_satirlari(b): son[r["id"]] = r["durum"]  # son gözlem
    oner = {r["id"] for r in _guncellik_satirlari(b) if r.get("karar") in GN_ONERILEN}
    n = len(oner); kot = sum(1 for i in oner if son.get(i) in GN_BAYAT)
    return (((n - kot) / n) if n else None), n, f"{kot}/{n} önerilen kayıt sonradan bayat/bitmiş çıktı (ele alınma kaydı yok; yalnız bu ölçülebiliyor)"
GN_CIKARIM = {"vade_cok_gecti", "eski_dokunulmamis", "eski_soru", "onay_suresi_doldu", "sonra_kapandi", "sonra_ele_alindi"}  # Suflor'un kendi çıkarımı olan durumlar; kapandi (kullanıcı kapattı) kesin, sayılmaz
def m_kayit_durum(b):  # bayat/bitti/yerini_aldi diye çıkarılan kayıt sonra yeniden "acik" göründüyse (kullanıcı dokundu ya da vadeyi yeniledi) çıkarım yanlıştı. G2 teyit cevapları gelince buraya eklenir.
    cik, ters = set(), set()
    for r in _guncellik_satirlari(b):
        if r["durum"] in GN_BAYAT and GN_CIKARIM & set(r.get("neden") or []): cik.add(r["id"])
        elif r["durum"] == "acik" and r["id"] in cik: ters.add(r["id"])
    n = len(cik)
    return (((n - len(ters)) / n) if n else None), n, f"{len(ters)}/{n} bayat/bitti çıkarımı sonra 'açık' görünerek çürüdü (kullanıcı teyidi henüz yok)"
def m_altin(b):  # test/zeka-altin.py'nin yazdığı altin-sonuc.json {"gecen","toplam","zaman"}: yalnız sayı; en son koşu (pencere yok; set küçük ve sabit)
    d = b.d("altin-sonuc.json") or {}
    g, t = d.get("gecen"), d.get("toplam")
    if not (isinstance(g, int) and isinstance(t, int) and t > 0): return None, 0, "altın set koşusu yok (test/zeka-altin.py)"
    return g / t, t, f"{g}/{t} altın kontrol geçti ({str(d.get('zaman') or '?')[:16]})"
def m_proje_bulma(b):  # olcum.py proje: proje bilgisini ilk 5 sonuçta bulma (test seti; anlam araması)
    if not b.gecmis: return None, 0, "olcum-gecmis yok"
    son = None
    for r in jsonl(os.path.dirname(b.gecmis), os.path.basename(b.gecmis)):
        if isinstance(r.get("proje"), dict) and (r["proje"].get("isabet") or {}).get("anlam"): son = r["proje"]
    if not son: return None, 0, "proje ölçümü yok"
    a = son["isabet"]["anlam"]; ok = sum(int(x.get("ilk5") or 0) for x in a.values()); n = sum(int(x.get("n") or 0) for x in a.values())
    return ((ok / n) if n else None), n, f"{ok}/{n} soru ilk 5 sonuçta bulundu (test seti, {son.get('zaman', '?')})"
def m_proaktif_kabul(b):
    s = _soz_say(b, {"gun_ici", "kisisel_tarih", "toplanti_hatirlat", "toplanti_sonrasi", "toplanti_cikis"}); n = sum(s.values())
    return ((s["kabul"] / n) if n else None), n, f"{s['kabul']}/{n} öneri kabul; {s['ret']} ret, {s['yoksay']} yoksay, {s['ertele']} ertele"
def m_proaktif_zaman(b):  # "ertele" = doğru şey yanlış an
    s = _soz_say(b, {"gun_ici", "kisisel_tarih", "toplanti_hatirlat", "toplanti_sonrasi", "toplanti_cikis", "eposta"}); n = sum(s.values())
    return (((n - s["ertele"]) / n) if n else None), n, f"{s['ertele']}/{n} öneri ertelendi"
def m_is_kopya(b):  # çift iş birleştirmesi: geri alınan ya da kullanıcının "ayrı" dediği = yanlış tespit
    d = b.d("is-kopya.json") or {}
    bl = [x for x in d.get("birlesen") or [] if isinstance(x, dict) and b.icinde(ts(x.get("zaman")))]
    ayri = len(d.get("ayri") or []); n = len(bl) + ayri; ok = sum(1 for x in bl if not x.get("geri"))
    return ((ok / n) if n else None), n, f"{ok}/{n} çift iş tespiti tuttu ({ayri} 'ayrı' dendi, {len(bl) - ok} geri alındı)"
def m_belge(b):
    d = b.d("belge-oneri.json") or {}
    gir = lambda v: ts(v) is None or b.icinde(ts(v))  # değer kimi zaman tarih, kimi zaman kayıt kimliği (tarihsiz: sayılır)
    k = sum(1 for v in (d.get("kabul") or {}).values() if gir(v)); r = sum(1 for v in (d.get("red") or {}).values() if gir(v)); n = k + r
    return ((k / n) if n else None), n, f"{k}/{n} belge önerisi kabul"
def m_dokum(b):  # hakem ölçümü (Gemini dökümüyle kıyas): 1 − kelime hatası, kelimeyle ağırlıklı; n = ölçülen toplantı
    rs = [r for r in b.j("hakem-olcum.jsonl") if b.icinde(ts(r.get("t"))) and not b.deneme_mi(r.get("toplanti")) and isinstance(r.get("wer_sozluk", r.get("wer_ham")), (int, float)) and r.get("kelime")]
    k = sum(int(r["kelime"]) for r in rs)
    if not k: return None, len(rs), "hakem ölçümü yok"
    w = sum(float(r.get("wer_sozluk", r.get("wer_ham"))) * int(r["kelime"]) for r in rs) / k
    return max(0.0, 1 - w), len(rs), f"{len(rs)} toplantıda kelime hatası %{w * 100:.0f} ({k} kelime)"

# (işlev, boyut, ölçüt anahtarı, ad, işlev ya da None (= veri kaynağı yok; nasıl toplanacağı "kaynak"ta), asgari n, ağırlık, kaynak)
OLCUTLER = [
    ("konus", "basari", "hatasiz", "Hatasız cevap", m_konus_hatasiz, 20, 1, "claude-cagri.jsonl is=bas-konus, hata alanı"),
    ("konus", "basari", "tekrarsiz", "Yeniden sorulmayan", m_konus_tekrar, 20, 1, "konus-gecmis.jsonl (10 dk içinde benzer soru)"),
    ("konus", "analiz", "duzeltilmeyen", "Düzeltilmeyen cevap", m_konus_duzeltme, 20, 1, "konus-gecmis.jsonl (3 dk içinde 'hayır, …')"),
    ("konus", "ongoru", "ihtiyac", "Sorulmadan önce söylediği", None, 0, 1, "yok — Konuş cevabında 'bunu sormadan söyledim' işareti ve sonraki soruyla eşleşme gerekir"),
    ("gun_plani", "basari", "tur", "Plan çıktı", m_plan_tur, 5, 0.5, "dusunme-iz.jsonl durum"),
    ("gun_plani", "basari", "kabul", "Plan bildirimi açıldı", m_plan_kabul, 5, 1, "soz.jsonl kaynak gun_plani"),
    ("gun_plani", "basari", "odak", "Odak işi 3 günde bitti", m_plan_odak, 5, 1, "dusunme-iz.jsonl odak + sonraki damga"),
    ("gun_plani", "ongoru", "risk", "Kayan/geçen işi önceden andı", m_plan_risk, 5, 1, "dusunme-iz.jsonl damga (vade) + odak/dikkat"),
    ("gun_plani", "analiz", "ogrenilen", "Öğrendiği bilgi doğru", m_ogrenilen, 5, 1, "ogrenilen.jsonl (Doğru/Yanlış)"),
    ("eposta", "basari", "kabul", "Bildirim işe yaradı", m_eposta_kabul, 10, 1, "soz.jsonl kaynak eposta"),
    ("eposta", "ongoru", "cevap", "Cevap gerekecek maili bildi", m_eposta_ongoru, 5, 1, "eposta-takip.json zd + posta.json gönderilen"),
    ("eposta", "analiz", "durum", "Zincir durumu doğru", m_eposta_durum, 10, 1, "eposta-takip.json zd + posta.json son ileti"),
    ("eposta", "analiz", "onem", "Önemli dediği önemsiz çıkmadı", m_eposta_yoksay, 10, 0.5, "eposta-takip.json bildirilen/yoksay"),
    ("eposta", "analiz", "kacirma", "Düşük/bilgi dediğine sonradan cevap yazılmadı", m_eposta_kacirma, 5, 1, "eposta-takip.json zd + posta.json gönderilen (yanlış negatif)"),
    ("eposta", "analiz", "duzeltme", "Kullanıcı düzeltmesi az", m_eposta_duzeltme, 10, 0.5, "eposta-tepki.jsonl yanlis_oncelik + onemli_kisi (yalnız sayı)"),
    ("toplanti", "basari", "kart", "Kart işe yaradı", m_kart_yarar, 20, 1, "kartlar.jsonl son durum"),
    ("toplanti", "analiz", "uyari", "Uyarı kartı yerinde", m_kart_uyari, 10, 1, "kartlar.jsonl dikkat/dur/belirt/duygu"),
    ("toplanti", "ongoru", "soru", "Gelecek soruyu önceden hazırladı", None, 0, 1, "yok — hazır kartın (hazir.json) toplantıda sorulan soruyla eşleşmesi kaydedilmiyor"),
    ("hazirlik", "ongoru", "gundem", "Gündem konuşuldu", m_gundem, 10, 1, "karneler.jsonl olcu.gundem"),
    ("hazirlik", "analiz", "bayat_oneri", "Öneri bayat çıkmadı", m_bayat_oneri, 10, 1, "guncellik.jsonl karar + durum (kimlik başına son gözlem)"),
    ("hazirlik", "analiz", "altin", "Altın set (bilinen hatalar)", m_altin, 3, 1, "altin-sonuc.json (test/zeka-altin.py; yalnız sayı)"),
    ("hazirlik", "basari", "bulma", "Proje bilgisini buldu (test seti)", m_proje_bulma, 10, 1, "olcum-gecmis.jsonl proje.isabet (olcum.py proje)"),
    ("proaktif", "basari", "kabul", "Öneri kabul", m_proaktif_kabul, 10, 1, "soz.jsonl (gün içi, kişisel tarih, toplantı hatırlatma/sonrası)"),
    ("proaktif", "analiz", "zaman", "Doğru an (ertelenmedi)", m_proaktif_zaman, 10, 1, "soz.jsonl ertele"),
    ("kayit", "analiz", "kopya", "Çift iş tespiti doğru", m_is_kopya, 5, 1, "is-kopya.json birlesen/ayri/geri"),
    ("kayit", "analiz", "durum", "Bayat/bitti çıkarımı tuttu", m_kayit_durum, 10, 1, "guncellik.jsonl durum + neden (sonradan 'acik' dönüş)"),
    ("kayit", "basari", "belge", "Belge önerisi kabul", m_belge, 5, 1, "belge-oneri.json"),
    ("kayit", "ongoru", "gecikme", "Gecikecek işi önceden söyledi", None, 0, 1, "yok — işe 'gecikme riski' tahmini yazılmıyor (gün planı riski bunu kısmen ölçer)"),
    ("dokum", "basari", "wer", "Döküm doğruluğu (1 − kelime hatası)", m_dokum, 2, 1, "hakem-olcum.jsonl"),
    ("tazi", "basari", "bulgu", "Bulgu işe yaradı", None, 0, 1, "yok — Tazı bulgusuna kullanıcı tepkisi (işe yaradı/yanlış) kaydedilmiyor"),
    ("kesisim", "analiz", "celiski", "Çelişki gerçek çıktı", None, 0, 1, "yok — kesisim.jsonl durum geçişi var ama 'bulgu doğru/yanlış' tepkisi yok"),
]

def karne(canli, gun=30, simdi=None, gecmis=None):
    """→ {"gun", "tarih", "genel", "islev": {ad: {"puan", "kismi", "boyut": {b: puan|None}}}, "olcut": [ {islev, boyut, anahtar, ad, oran, n, asgari, puan, kanit, kaynak, durum} ], "kullanici": {...}}"""
    b = Baglam(canli, gun, simdi, gecmis); ol = []
    for isl, boy, ank, ad, fn, asg, w, kay in OLCUTLER:
        o = {"islev": isl, "boyut": boy, "anahtar": ank, "ad": ad, "asgari": asg, "agirlik": w, "kaynak": kay, "oran": None, "n": 0, "puan": None, "kanit": ""}
        if fn is None: o["durum"] = "kaynak_yok"
        else:
            try: oran, n, kanit = fn(b)
            except Exception as e: oran, n, kanit = None, 0, f"okunamadı ({e.__class__.__name__})"
            o.update(oran=None if oran is None else round(oran, 3), n=n, kanit=kanit)
            o["durum"] = "tamam" if oran is not None and n >= asg else "yetersiz"
            if o["durum"] == "tamam": o["puan"] = round(100 * oran)
        ol.append(o)
    isl = {}
    for ad in ISLEVLER:
        bo = {}
        for boy in BOYUTLAR:
            xs = [o for o in ol if o["islev"] == ad and o["boyut"] == boy and o["puan"] is not None]
            bo[boy] = round(sum(o["puan"] * o["agirlik"] for o in xs) / sum(o["agirlik"] for o in xs)) if xs else None
        var = [k for k, v in bo.items() if v is not None]
        p = round(sum(bo[k] * BOYUTLAR[k][1] for k in var) / sum(BOYUTLAR[k][1] for k in var)) if var else None
        tanimli = {o["boyut"] for o in ol if o["islev"] == ad}  # kaynağı olmayan boyut da "eksik" sayılır: puan o boyutu kapsamıyor
        isl[ad] = {"puan": p, "kismi": bool(var) and len(var) < len(tanimli), "boyut": bo}
    ps = [v["puan"] for v in isl.values() if v["puan"] is not None]
    return {"gun": gun, "tarih": datetime.datetime.fromtimestamp(b.simdi).date().isoformat(), "genel": round(sum(ps) / len(ps)) if ps else None, "islev_sayi": len(ps),
            "islev": isl, "olcut": ol, "kullanici": kullanici_ozet(canli, gun, b.simdi)}

# ---------- kullanıcı puanı (1–5) ----------
def kullanici_ozet(canli, gun=30, simdi=None):  # → {işlev: {"n", "ort"}} pencere içinde; "gec" satırları sayılmaz
    simdi = float(simdi if simdi is not None else time.time()); out = {}
    for r in jsonl(canli, PUAN):
        t = ts(r.get("t")); p = r.get("puan")
        if r.get("islev") not in ISLEVLER or not isinstance(p, int) or not 1 <= p <= 5 or t is None or not simdi - gun * 86400 <= t <= simdi + 60: continue
        o = out.setdefault(r["islev"], {"n": 0, "top": 0}); o["n"] += 1; o["top"] += p
    return {k: {"n": v["n"], "ort": round(v["top"] / v["n"], 1)} for k, v in out.items()}
def puan_satiri(islev=None, puan=None, gec=False, simdi=None):  # pano cevabı → yazılacak satır (metinsiz) ya da None (geçersiz)
    t = round(float(simdi if simdi is not None else time.time()), 1)
    if gec: return json.dumps({"t": t, "gec": True}) + "\n"
    if islev not in SORU_ISLEV or isinstance(puan, bool) or not isinstance(puan, int) or not 1 <= puan <= 5: return None
    return json.dumps({"t": t, "islev": islev, "puan": puan}) + "\n"
def soru_gerekli(canli, simdi=None):
    """Kullanıcı puanı sorusu zamanı geldiyse sorulacak işlevler (en çok 4), yoksa []. Kural: son cevap (puan ya da "geç") SORU_ARALIK_GUN'den eski
    — "geç" denmişse SORU_ERTELE_GUN sonra yeniden; ilk soru, karnenin ilk günlük kaydından en az SORU_ARALIK_GUN gün sonra. Yalnız son SORU_ARALIK_GUN günde kullanılan işlevler sorulur."""
    simdi = float(simdi if simdi is not None else time.time()); son_p = son_g = None
    for r in jsonl(canli, PUAN):
        t = ts(r.get("t"))
        if t is None: continue
        if r.get("gec"): son_g = max(son_g or 0, t)
        elif r.get("islev"): son_p = max(son_p or 0, t)
    if son_p and simdi - son_p < SORU_ARALIK_GUN * 86400: return []
    if son_g and simdi - son_g < SORU_ERTELE_GUN * 86400: return []
    if not son_p:
        ilk = next((ts(r.get("t")) for r in jsonl(canli, KARNE) if ts(r.get("t"))), None)
        if not ilk or simdi - ilk < SORU_ARALIK_GUN * 86400: return []
    b = Baglam(canli, SORU_ARALIK_GUN, simdi); kul = []
    if sum(1 for r in b.j("claude-cagri.jsonl") if r.get("is") == "bas-konus" and b.icinde(ts(r.get("at")))) >= 3: kul.append("konus")
    if sum(1 for r in b.j(PLAN_IZ) if r.get("durum") == "tamam" and b.icinde(ts(r.get("t")))) >= 3: kul.append("gun_plani")
    if any(d["kaynak"] == "eposta" and d["sunuldu"] for d in _soz(b).values()): kul.append("eposta")
    if any(r.get("kind") and b.icinde(ts(r.get("at"))) and not b.deneme_mi(r.get("file")) for r in b.j("kartlar.jsonl")): kul.append("toplanti")
    return [k for k in SORU_ISLEV if k in kul][:4]

# ---------- günlük kayıt ----------
def ozet_satir(k, simdi=None):  # karne → zeka-karne.jsonl satırı: yalnız sayılar ve işlev/ölçüt anahtarları
    return {"v": 1, "tarih": k["tarih"], "t": round(float(simdi if simdi is not None else time.time()), 1), "gun": k["gun"], "genel": k["genel"],
            "islev": {a: {"p": v["puan"], **{b[0]: v["boyut"][b] for b in BOYUTLAR}} for a, v in k["islev"].items()},
            "olcut": {f"{o['islev']}.{o['anahtar']}": [o["puan"], o["n"]] for o in k["olcut"] if o["durum"] != "kaynak_yok"},
            "kullanici": k["kullanici"]}
def son_tarih(canli):
    try:
        with open(os.path.join(canli, KARNE), encoding="utf-8") as f: ls = [l for l in f if l.strip()]
        return json.loads(ls[-1]).get("tarih") if ls else None
    except (OSError, ValueError, IndexError): return None
def gunluk(canli, simdi=None, gecmis=None, yaz=None):
    """Bugünün satırı yoksa karneyi hesaplar ve zeka-karne.jsonl'e ekler → satır ya da None (bugün zaten var). yaz(yol, metin): aktarıcının write() sarmalayıcısı; yoksa doğrudan ekler (0600)."""
    simdi = float(simdi if simdi is not None else time.time()); bugun = datetime.datetime.fromtimestamp(simdi).date().isoformat()
    if son_tarih(canli) == bugun: return None
    s = ozet_satir(karne(canli, 30, simdi, gecmis), simdi); metin = json.dumps(s, ensure_ascii=False) + "\n"; yol = os.path.join(canli, KARNE)
    if yaz: yaz(yol, metin)
    else:
        with open(os.open(yol, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "a", encoding="utf-8") as f: f.write(metin)
    return s
def gecmis_satirlar(canli): return [r for r in jsonl(canli, KARNE) if r.get("v") == 1 and _gun(r.get("tarih"))]
def egilim(canli, islev_puan, simdi=None, gun=7):  # → {işlev: bugünkü puan − `gun` gün önceki (en yakın eski) kayıttaki puan} (kayıt yoksa None)
    simdi = float(simdi if simdi is not None else time.time()); hedef = datetime.datetime.fromtimestamp(simdi).date() - datetime.timedelta(days=gun)
    eski = [r for r in gecmis_satirlar(canli) if _gun(r["tarih"]) <= hedef]
    if not eski: return {a: None for a in islev_puan}
    r = eski[-1]; out = {}
    for a, p in islev_puan.items():
        q = ((r.get("islev") or {}).get(a) or {}).get("p")
        out[a] = None if p is None or q is None else p - q
    out["_genel_once"] = r.get("genel"); return out

# ---------- beta (yalnız sayı; teshis.temizle'den de geçer) ----------
def beta_ozet(canli, bas, son):
    """Biten hafta için: haftanın son karne satırındaki işlev puanları + haftada verilen kullanıcı puanları (sayı ve ortalama). Metin, ad, ölçüt kanıtı gitmez."""
    rs = [r for r in gecmis_satirlar(canli) if bas <= (ts(r.get("t")) or 0) < son]
    k = rs[-1] if rs else None
    kar = {a: {"puan": v.get("p"), "basari": v.get("b"), "ongoru": v.get("o"), "analiz": v.get("a")} for a, v in ((k or {}).get("islev") or {}).items() if a in ISLEVLER}
    ku = {}
    for r in jsonl(canli, PUAN):
        t = ts(r.get("t")); p = r.get("puan")
        if r.get("islev") in ISLEVLER and isinstance(p, int) and 1 <= p <= 5 and t is not None and bas <= t < son:
            o = ku.setdefault(r["islev"], {"n": 0, "top": 0}); o["n"] += 1; o["top"] += p
    return {"zeka_genel": (k or {}).get("genel"), "zeka_karne": kar, "zeka_kullanici": {a: {"n": v["n"], "ort": round(v["top"] / v["n"], 1)} for a, v in ku.items()},
            "zeka_gec": sum(1 for r in jsonl(canli, PUAN) if r.get("gec") and bas <= (ts(r.get("t")) or 0) < son)}
