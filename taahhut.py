#!/usr/bin/env python3
# Suflor.me — taahhüt ve tutarlılık (S91 güncelleme, Faz 7). toplanti-claude.py izle her döküm satırını Taahhut.besle()'ye verir; yalnız metinden,
# kural tabanlı, "yalan" sözcüğü yok. Üç tür:
#  - net_degil: ileriye dönük bir iş üstlenen ama sahibi ya da zamanı belirsiz söz ("bakarız", "en kısa sürede hallederim", "I'll try").
#  - rakam: aynı toplantıda aynı şey için (sayının ardındaki ad + sıklık aynı) farklı sayı ("günde 40 sipariş" … "günde 60 sipariş").
#  - gecmis: kişinin karar grafındaki (önceki toplantılar) sayılı iddia/kararıyla aynı konuda farklı sayı.
# Canlı olay yalnız güçlü sinyalde (kaçamak söz, geçmişle fark) ve en çok ARALIK_SN'de bir (kullanıcı, 21 Ekim: canlı ama sınırlı). Tarihsiz söz
# ("göndereceğim") ve aynı toplantıda rakam yalnız kayıtta: 6 gerçek dökümde körlemesine etiketle kıyas (21 Ekim) — rakam kesinliği %9, tarihsiz
# söz anlatımla karışıyor; toplantı sonunda `toplanti-claude.py taahhut` aday listesi verir, Claude dökümle ayıklar. Python 3.9, standart kütüphane.
import re

ARALIK_SN = 600          # Claude'a giden taahhüt olayı en çok 10 dk'da bir
RAKAM_EN_AZ_ARA_SN = 20  # aynı cümlenin yeniden yazımı (Whisper düzeltmesi) değişiklik sayılmaz

def kucuk(t): return str(t).replace("İ", "i").replace("I", "ı").lower()

# ileriye dönük üstlenme: 1. kişi gelecek/geniş zaman ya da İngilizce "I'll / we'll / let me"
SOZ_RX = re.compile(r"\b\w{2,}(?:eceğim|acağım|eceğiz|acağız|ecem|acam|ecez|acaz|eyim|ayım|elim|alım)\b|"
                    r"\b(?:bak|hallet|gönder|ilet|ara|yaz|yap|sor|dön|getir|hazırla|kontrol ed|ayarla|çöz|düzelt|konuş|paylaş|at|ekle)\w*"
                    r"(?:ırım|irim|urum|ürüm|arım|erim|rım|rim|ruz|rüz|rız|riz|arız|eriz)\b|"
                    r"\b(?:i'll|i will|we'll|we will|let me|i can|we can|i'm going to|we're going to|i'd|i would)\b", re.I)
# belirsizlik: zaman ya da sahip yok, çaba sözü
BELIRSIZ_RX = re.compile(r"\b(?:bakarız|deneriz|deneyeceğ\w*|deneyelim|elimden gel\w*|en kısa sürede|en kısa zamanda|bir ara|"
                         r"fırsat bul\w*|müsait olunca|vakit bul\w*|duruma göre|"
                         r"try to|as soon as possible|asap|at some point|sometime soon|when i can|when we can|we'll see|"
                         r"look into|circle back|get back to you)\b", re.I)
# tek başına söz sayılanlar (1. çoğul gelecek / kalıp): "bakarız", "en kısa sürede", "get back to you"
KENDI_SOZ = ("bakarız", "deneriz", "deneyeceğ", "deneyelim", "en kısa sürede", "en kısa zamanda", "get back to you", "circle back", "look into")
# açık zaman: belirsiz sayılmaz
ZAMAN_RX = re.compile(r"\b(?:bugün|yarın|öbür gün|bu akşam|bu öğle\w*|bu hafta|haftaya|gelecek hafta|ay sonu\w*|hafta sonu\w*|"
                      r"pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar|saat \d|\d{1,2}[:.]\d{2}|"
                      r"\d{1,2} (?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)|"
                      r"today|tomorrow|tonight|this week|next week|monday|tuesday|wednesday|thursday|friday|by (?:end of|eod|eow)|"
                      r"\d+ (?:dakika|saat|gün|hafta) (?:içinde|sonra)|within \d+)\b", re.I)
GECMIS_RX = re.compile(r"\w+(?:dım|dim|dum|düm|tım|tim|tum|tüm|dık|dik|duk|dük|tık|tik|tuk|tük|yordum|yorduk|mıştım|mıştık|miştim|miştik)\b|\b(?:did|was|were|had)\b", re.I)
SORU_RX = re.compile(r"\?\s*$|\bm[iıuü](?:s[iıuü]n(?:[iıuü]z)?|y[iıuü]z|y[iıuü]m)?\b", re.I)

# sayılar: rakam (1.200, 3,5, %40) ya da yazıyla; saat ve tarih biçimleri ayrı
_YAZI = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "yirmi": 20, "otuz": 30,
         "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90, "yüz": 100, "bin": 1000,
         "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "thirty": 30,
         "forty": 40, "fifty": 50, "hundred": 100, "thousand": 1000}
_CARP = {"bin": 1e3, "k": 1e3, "milyon": 1e6, "milyar": 1e9, "thousand": 1e3, "million": 1e6, "billion": 1e9, "m": 1e6}
SAYI_RX = re.compile(r"(%\s?)?(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s?(bin\b|milyon\b|milyar\b|thousand\b|million\b|billion\b|k\b|m\b)?\s?(%|yüzde\b|percent\b)?", re.I)
SAAT_RX = re.compile(r"\b\d{1,2}:\d{2}\b")
# birim: sayının hemen ardındaki (ya da önündeki) ölçü — aynı birim şartı farklı şeylerin sayılarını ayırır
BIRIMLER = [("yuzde", r"%|yüzde|percent"), ("para", r"dolar|\$|usd|tl|lira|euro|€|avro|bütçe|ciro|maaş|ücret|fiyat|budget|price|cost|revenue"),
            ("gun", r"gün|day"), ("hafta", r"hafta|week"), ("ay", r"\bay\b|\baylık|month"), ("yil", r"yıl|sene|year"), ("saat", r"saat|hour"),
            ("dakika", r"dakika|dk|minute"), ("kisi", r"kişi|çalışan|personel|insan|people|person|employee|staff"),
            ("siparis", r"sipariş|order"), ("adet", r"adet|tane|parça|ürün|unit|item|piece")]
# içerik kökü dışı: bağlaç, zamir, dolgu, sayı sözcükleri
DURAK = set("ve ile ama fakat çünkü için gibi kadar daha çok az bir bu şu o ben sen biz siz onlar evet hayır yani şey işte zaten artık "
            "olarak oldu olur olan var yok değil mi mı mu mü da de ki ne nasıl neden hangi kaç her hiç en abi ağabey hocam tamam okay yes "
            "the and or but for with that this these those there what which who how many much about like just yeah so then also "
            "is are was were be been have has had do does did will would can could i we you they he she it our your my".split())

def koklar(t):
    out = []
    for w in re.findall(r"[a-zçğıöşü]+", kucuk(t)):
        if len(w) < 3 or w in DURAK or w in _YAZI or w in _CARP: continue
        out.append(w[:5])
    return out

def _sayi(s):
    s = s.replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s): return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))

def sayilar(t):
    # → [(değer, birim, konum, ham)] — saat (10:30), tek haneli sayı yazıları ("bir" çok anlamlı) ve yıl gibi duran 19xx/20xx atlanır
    low = kucuk(t); out = []
    saat = [m.span() for m in SAAT_RX.finditer(low)]
    for m in SAYI_RX.finditer(low):
        if any(a <= m.start() < b for a, b in saat): continue
        try: v = _sayi(m.group(2))
        except ValueError: continue
        if m.group(3): v *= _CARP.get(m.group(3).lower(), 1)
        if re.fullmatch(r"(19|20)\d\d", m.group(2)) and not m.group(3): continue
        yuzde = bool(m.group(1) or m.group(4))
        out.append((v, "yuzde" if yuzde else _birim(low, m.start(), m.end()), m.start(), m.group(0).strip()))
    for m in re.finditer(r"\b(on|yirmi|otuz|kırk|elli|altmış|yetmiş|seksen|doksan|yüz|bin|ten|twenty|thirty|forty|fifty|hundred|thousand)"
                         r"(?:\s+(bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz))?(?:\s+(bin|milyon|thousand|million))?\b", low):
        if any(a <= m.start() < a + len(h) for _, _, a, h in out): continue
        v = _YAZI[m.group(1)] + (_YAZI[m.group(2)] if m.group(2) else 0)
        if m.group(3): v *= _CARP[m.group(3)]
        out.append((float(v), _birim(low, m.start(), m.end()), m.start(), m.group(0)))
    return out

def _birim(low, a, b):
    sag, sol = low[b:b + 24], low[max(0, a - 24):a]
    for ad, rx in BIRIMLER:
        if re.search(rx, sag): return ad
    for ad, rx in BIRIMLER:
        if re.search(rx, sol): return ad
    return None

# sayının "neyin sayısı" olduğu: ardından gelen ilk içerik kökü (ölçü sözcükleri atlanır) + sıklık ("günde", "ayda", "per week")
ATLA = set("tane adet civarı civar küsur kadar falan filan üzeri üstü fazla daha yaklaşık about around over more than less roughly some".split())
ATLA_KOK = {w[:5] for w in ATLA}
BIRIM_AD = set("tl lira dolar usd euro avro $ € % yüzde percent dollars dollar bucks".split())
SIKLIK_RX = re.compile(r"\b(günde|günlük|haftada|haftalık|ayda|aylık|yılda|yıllık|saatte|saatlik|a day|per day|daily|a week|per week|weekly|a month|per month|monthly|a year|per year|yearly)\b")
_SIKLIK = {"günlük": "günde", "daily": "günde", "a day": "günde", "per day": "günde", "haftalık": "haftada", "a week": "haftada", "per week": "haftada",
           "weekly": "haftada", "aylık": "ayda", "a month": "ayda", "per month": "ayda", "monthly": "ayda", "yıllık": "yılda", "a year": "yılda",
           "per year": "yılda", "yearly": "yılda", "saatlik": "saatte"}
ZAMAN_AD = {w[:5] for w in "dakika saniye saat gün hafta yıl sene ocak şubat mart nisan mayıs haziran temmuz ağustos eylül ekim kasım aralık "
            "minute minutes second hour hours day days week weeks month months year years kere defa kez times".split()}
def cevre(c, konum, n=5):
    # sayının çevresindeki içerik kökleri (± n sözcük): aynı ad farklı şeyleri sayabilir ("3 order" / "14 order") — ek bağlam şartı
    low = kucuk(c); return {k for k in koklar(low[:konum])[-n:] + koklar(low[konum:])[:n] if k not in ATLA_KOK}
def anahtar(c, konum, ham):
    # → (ad kökü, sıklık) ya da None. Ad yoksa sayı karşılaştırılmaz ("biraz önce dokuzu şu an 13 oldu" gibi bağlamsız sayılar).
    low = kucuk(c); sonra = low[konum + len(ham):]
    ad = None
    for w in re.findall(r"[a-zçğıöşü$%€]+", sonra)[:3]:
        if w in ATLA or w in _CARP or w in _YAZI: continue
        if w in BIRIM_AD: ad = None; break  # "120 bin TL": neyin parası olduğu sayıdan önce ("bütçe toplamı 120 bin")
        if w in DURAK or len(w) < 3: break
        ad = w[:5]; break
    if not ad:
        once = [k for k in koklar(low[:konum])[-2:] if k not in ATLA_KOK]
        ad = once[-1] if once else None
    if not ad or ad in ZAMAN_AD: return None  # süre/tarih ("20 dakika sürdü", "25 ağustos") konuşmada sürekli değişir
    m = SIKLIK_RX.search(low); sk = _SIKLIK.get(m.group(1), m.group(1)) if m else None
    return ad, sk

CUMLE_RX = re.compile(r"(?<=[.!?…])\s*|\n")
def cumleler(t):
    # Whisper/Teams satırı çoğu kez birkaç cümleyi boşluksuz birleştirir ("…olmuyor.Bakın…"): her cümle ayrı değerlendirilir
    return [c.strip() for c in CUMLE_RX.split(t) if c and len(c.strip()) > 1]

# 1. kişi gelecek: "taşıyacağım", "göndereceğiz", "bakacağım"; geniş zamanla söz yalnız iş fiillerinde ("atarım", "hallederim")
GELECEK_RX = re.compile(r"\b\w{2,}(?:y?eceğim|y?acağım|y?eceğiz|y?acağız|y?ecem|y?acam)\b|"
                        r"\b(?:bak|hallet|halleder|gönder|ilet|ara|yaz|yap|sor|dön|getir|hazırla|kontrol eder|ayarla|çöz|düzelt|paylaş|at|ekle|devred|toparla|bitir|anlat|göster)"
                        r"(?:ar|er|ır|ir|ur|ür|r)(?:ım|im|um|üm|ız|iz|uz|üz)\b|"
                        r"\b(?:i'll|i will|we'll|we will|i'm going to|we're going to|i'm gonna|we're gonna|let me|i hope to)\b", re.I)
GELECEK_HARIC_RX = re.compile(r"^(?:ol|geç|di|de|gel|başla|devam ed|edil|görü)y?(?:eceğ|acağ|ecem|acam)", re.I)  # akış/anlatım: "ikinci bölüme geçeceğiz", "uyumlu olacağız"
KOSUL_RX = re.compile(r"\b(?:eğer|şayet|if|unless)\b|\w+(?:sa|se)(?:m|k|n|nız|niz)?\b", re.I)
def net_degil(t):
    # ileriye dönük üstlenme + açık zaman yok (ister kaçamak "bakarız", ister yalnız tarihsiz "göndereceğim") → (işaret, cümle)
    for c in cumleler(t):
        low = kucuk(c)
        if len(low.split()) < 2 or SORU_RX.search(low) or ZAMAN_RX.search(low): continue
        b = BELIRSIZ_RX.search(low); g = GELECEK_RX.search(low)
        if b and (g or b.group(0).startswith(KENDI_SOZ)): return b.group(0), c
        if g and not KOSUL_RX.search(low) and len(low.split()) >= 3 and not GELECEK_HARIC_RX.search(g.group(0)): return "tarih yok", c
    return None

def _bicim(v):
    return (f"{v:,.0f}".replace(",", ".") if v == int(v) else f"{v:.2f}".rstrip("0").replace(".", ","))

class Taahhut:
    def __init__(s, ben, graf=None):
        # ben: kullanıcının adı (kendi sözü de sayılır — kullanıcı da net olmayan söz verebilir); graf: kim → [(tarih, metin)] (karar grafı)
        s.ben = ben; s.graf = graf or (lambda kim: []); s.sayilar = []; s.kayit = []; s.son_olay = -1e9; s.graf_onbellek = {}
    def besle(s, r, simdi):
        # → Claude'a gidecek olay satırları (sınırlı); her bulgu s.kayit'a
        kim = r.get("speaker") or "?"; t = (r.get("text") or "").strip(); saat = str(r.get("time") or "")[:8]
        if not t: return []
        bul = []
        nd = net_degil(t)
        if nd: bul.append({"tur": "net_degil", "kim": kim, "saat": saat, "metin": nd[1][:200], "isaret": nd[0]})
        for c in cumleler(t):
            for v, birim, konum, ham in sayilar(c):
                if v < 2: continue  # "bir" / 1 çok anlamlı
                k = anahtar(c, konum, ham)
                if not k: continue
                cv = cevre(c, konum)
                for e in reversed(s.sayilar):
                    if e["k"] != k or (birim == "yuzde") != (e["birim"] == "yuzde") or simdi - e["t"] < RAKAM_EN_AZ_ARA_SN: continue
                    if len(cv & e["cv"] - {k[0]}) < 1: continue  # ad dışında en az bir ortak kök
                    if abs(e["v"] - v) <= 0.05 * max(e["v"], v): break  # aynı değer: konu teyit edildi, daha eskisine bakma
                    bul.append({"tur": "rakam", "kim": kim, "saat": saat, "metin": c[:200], "deger": _bicim(v), "birim": birim,
                                "onceki": {"kim": e["kim"], "saat": e["saat"], "metin": e["metin"][:200], "deger": _bicim(e["v"])}, "anahtar": list(k)})
                    break
                s.sayilar.append({"t": simdi, "kim": kim, "saat": saat, "metin": c, "v": v, "birim": birim, "k": k, "cv": cv})
                for tarih, gm in s._graf(kim):
                    for gc in cumleler(gm):
                        for gv, gb, gk, gh in sayilar(gc):
                            if anahtar(gc, gk, gh) != k or (gb == "yuzde") != (birim == "yuzde") or abs(gv - v) <= 0.05 * max(gv, v): continue
                            if len(cv & cevre(gc, gk) - {k[0]}) < 1: continue
                            bul.append({"tur": "gecmis", "kim": kim, "saat": saat, "metin": c[:200], "deger": _bicim(v), "birim": birim,
                                        "onceki": {"tarih": tarih, "metin": gm[:200], "deger": _bicim(gv)}})
                            break
        if not bul: return []
        s.kayit.extend(bul)
        canli = [x for x in bul if x["tur"] == "gecmis" or (x["tur"] == "net_degil" and x["isaret"] != "tarih yok")]
        if not canli or simdi - s.son_olay < ARALIK_SN: return []
        s.son_olay = simdi
        return [olay_satiri(canli[0])]
    def _graf(s, kim):
        ilk = kucuk(kim).split(" ")[0] if kim else ""
        if not ilk or ilk == "?": return []
        if ilk not in s.graf_onbellek:
            try: s.graf_onbellek[ilk] = list(s.graf(kim))
            except Exception: s.graf_onbellek[ilk] = []
        return s.graf_onbellek[ilk]

def olay_satiri(x):
    if x["tur"] == "net_degil":
        return (f"TAAHHÜT: [{x['saat']} {x['kim']}] \"{x['metin']}\" — iş üstleniyor ama sahibi ya da zamanı belli değil (\"{x['isaret']}\") → "
                f"önemliyse SÖYLE kartı: kim, ne zamana kadar? (ör. \"Ne zamana kadar? — tarih iste\"); yoksa geç")
    o = x["onceki"]
    if x["tur"] == "rakam":
        return (f"RAKAM DEĞİŞTİ: [{o['saat']} {o['kim']}] {o['deger']} → [{x['saat']} {x['kim']}] {x['deger']} · önce \"{o['metin'][:120]}\" · şimdi \"{x['metin'][:120]}\" "
                f"→ yalnız aynı şeyden söz ediliyorsa SÖYLE kartı (\"{o['saat'][:5]}'te {o['deger']} dendi — hangisi?\"); farklı şeyse geç")
    return (f"GEÇMİŞLE FARK: [{x['saat']} {x['kim']}] {x['deger']} · {o['tarih']}'de \"{o['metin'][:120]}\" ({o['deger']}) · şimdi \"{x['metin'][:120]}\" "
            f"→ aynı şeyse SÖYLE kartı, kaynağıyla (\"{o['tarih']}'de {o['deger']} demiştiniz — değişti mi?\"); \"yalan\" deme")

def ozet_satirlari(kayit):
    # toplantı sonu: türe göre, tekrarsız (aynı metin bir kez)
    gor = set(); out = {"net_degil": [], "rakam": [], "gecmis": []}
    for x in kayit:
        k = (x["tur"], x["metin"])
        if k in gor: continue
        gor.add(k); out[x["tur"]].append(x)
    return out
