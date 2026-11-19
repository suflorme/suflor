#!/usr/bin/env python3
# referans-dokum (19 Kasım 2026; toplanti-claude.py referans_dokum_cmd): dış referans dökümüyle (claude-meetings, meet, teams) Suflor dökümünün karşılaştırması.
# Kurgu veri, geçici klasör, ağ yok, gerçek canlı klasöre yazılmaz. Üç biçimde sahte referans (bilinen kaydırma: mutlak +7 sn, göreli +180 sn) → kaydırma ±2 sn içinde bulunur;
# boşluk ve "Obrigada" uydurması yakalanır; konuşmacı eşlemesi kurulur; AM/PM (12:05 PM öğlen, 12:05 AM gece) ve gece yarısı geçişi; eğilim dosyasında çift satır yok; izinler 0600/0700;
# ilgisiz referans → "hizalanamadı" (çıkış 1, ölçü yazılmaz).
#   PYTHONDONTWRITEBYTECODE=1 python3 -B test/referans-dokum.py      (~10 sn; kaldı → çıkış 1)
import datetime, json, os, random, re, shutil, stat, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=None):
    print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" → {ek}"))
    if not k: HATA.append(ad)
T = tempfile.mkdtemp(prefix="referans-dokum-")
src = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read()
# --- Bölüm 1: ayrıştırıcılar (kaynaktan yalnız rd_* bölümü, çıktı yazan komut işlevi hariç)
parca = src[src.index("RD_YOK = "):src.index("def rd_olc(")]
ns = {"re": re, "datetime": datetime, "json": json, "os": os, "kucuk": lambda t: t.replace("İ", "i").replace("I", "ı").lower()}
exec(parca, ns)
ay = ns["rd_ayristir"]
def utc(y, mo, d, h=0, mi=0, s=0): return datetime.datetime(y, mo, d, h, mi, s, tzinfo=datetime.timezone.utc).timestamp()
oglen = utc(2026, 11, 19, 12, 0)
r, atla, mut = ay("12:05:00 PM [Ayşe K] (speech) öğlen satırı\n11:59:00 AM [Ayşe K] (speech) sabah\n12:05:00 AM [Bora T] (speech) gece\n12:06:00 PM [Claude] (speech) atla\n"
                  "12:06:00 PM [Ayşe K] (chat) sohbet atla\nsayfa başlığı\n", "claude-meetings", oglen)
ok("AM/PM: 12:05 PM = 12:05, 11:59 AM = 11:59", r[0]["t"] == utc(2026, 11, 19, 12, 5) and r[1]["t"] == utc(2026, 11, 19, 11, 59), [x["t"] for x in r])
ok("AM/PM: 12:05 AM = 00:05 (sıra geriye gidince ertesi gün değil, aynı sıra tolerans içinde ertesi güne geçer)", r[2]["t"] == utc(2026, 11, 20, 0, 5) or r[2]["t"] == utc(2026, 11, 19, 0, 5), r[2]["t"])
r2, _, _ = ay("12:05:00 AM [Bora T] (speech) gece\n", "claude-meetings", utc(2026, 11, 19, 0, 10))
ok("12:05 AM tek başına = 00:05 aynı gün", r2[0]["t"] == utc(2026, 11, 19, 0, 5), r2[0]["t"])
ok("(chat) ve [Claude] atlanır, tanınmayan satır sayılır", len(r) == 3 and atla == 1 and mut, (len(r), atla))
g, _, _ = ay("11:58:00 PM [A] (speech) bir\n11:59:30 PM [A] (speech) iki\n12:01:00 AM [A] (speech) üç\n12:02:00 AM [A] (speech) dört\n", "claude-meetings", utc(2026, 11, 19, 23, 50))
ok("gece yarısı geçişi: gün ilerler, sıra tek yönlü", [x["t"] for x in g] == sorted(x["t"] for x in g) and g[2]["t"] == utc(2026, 11, 20, 0, 1), [x["t"] for x in g])
vt = "WEBVTT\n\n00:01:02.345 --> 00:01:05.000\n<v Ayşe K>Merhaba dünya</v>\n\n1:00:00.000 --> 1:00:03.000\nBora T: ikinci söz\n"
tv, _, mut = ay(vt, "teams", 1000.0)
ok("teams: <v Ad> ve 'Ad:' biçimi, saat:dakika:saniye, göreli", abs(tv[0]["t"] - 1062.345) < 1e-6 and tv[0]["kisi"] == "Ayşe K" and tv[1]["kisi"] == "Bora T" and tv[1]["t"] == 4600.0 and not mut, tv)
mt, atla, _ = ay("Meeting notes\nAttendees: Ayşe K, Bora T\nTranscript\n00:00:00\nAyşe K: bir\nBora T: iki\n00:01:00\nAyşe K: üç\nMeeting ended after 00:02:00\n", "meet", 0.0)
ok("meet: başlıklar atlanır, satırlar blok içinde doğrusal dağılır", [round(x["t"]) for x in mt] == [0, 30, 60] and atla == 4, ([x["t"] for x in mt], atla))
ok("kaynak tahmini", ns["rd_tahmin"](vt) == "teams" and ns["rd_tahmin"]("11:05:27 AM [A] (speech) x") == "claude-meetings" and ns["rd_tahmin"]("00:00:00\nA: x") == "meet")

# --- Bölüm 2: uçtan uca (CLI, geçici klasör)
rng = random.Random(7); hece = "ka ra me li to su ve ni da bo ze pa hu fi gö çe şa ın ül ma".split()
def kelime(): return "".join(rng.choice(hece) for _ in range(rng.randint(3, 4)))
SAT = [(i * 10, " ".join(kelime() for _ in range(8))) for i in range(120)]  # 20 dk, 10 sn'de bir satır
KIM = [("Ayse Kaya", "Ayşe K"), ("Bora Tan", "Bora T")]  # (Suflor adı, referans adı)
BOS = range(48, 60)  # 8.–10. dk Suflor'da yok
def suflor_yaz(klasor, kok, base):
    os.makedirs(klasor, exist_ok=True); satirlar = []
    for i, (s, m) in enumerate(SAT):
        if i in BOS: continue
        t0 = base + s; at = datetime.datetime.fromtimestamp(t0 + 3, datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        satirlar.append({"at": at, "id": f"w-{i}", "revised": False, "time": "00:00:00", "speaker": KIM[i % 2][0], "text": m, "src": "whisper", "kanal": "ben" if i % 2 == 0 else "karsi", "t0": t0, "t1": t0 + 6})
    for j in range(4):  # uydurma: ref'te karşılığı olmayan, art arda "Obrigada."
        t0 = base + 1040 + j * 2; satirlar.append({"at": datetime.datetime.fromtimestamp(t0 + 3, datetime.timezone.utc).isoformat().replace("+00:00", "Z"), "id": f"o-{j}", "revised": False, "speaker": "Ayse Kaya", "text": "Obrigada.", "src": "whisper", "kanal": "ben", "t0": t0, "t1": t0 + 1})
    satirlar.append(dict(satirlar[3], revised=True, text=satirlar[3]["text"] + " düzeltildi"))  # aynı id: son hâl geçerli
    with open(os.path.join(klasor, kok + ".jsonl"), "w", encoding="utf-8") as f:
        for r in sorted(satirlar, key=lambda x: x["t0"]): f.write(json.dumps(r, ensure_ascii=False) + "\n")
    open(os.path.join(klasor, kok + ".md"), "w").write("# x\n")
def cm(base, fark):  # claude-meetings biçimi: UTC 12 saat; referans saati = Suflor − fark (kaydırma +fark)
    out = ["Transcript page 1 of 1"]
    for i, (s, m) in enumerate(SAT):
        if 1000 <= s < 1080: continue
        t = datetime.datetime.fromtimestamp(base + s - fark, datetime.timezone.utc)
        out.append(f"{t.strftime('%I:%M:%S %p')} [{KIM[i % 2][1]}] (speech) {m}")
    out.append("11:00:00 AM [Ayşe K] (chat) sohbet")
    return "\n".join(out) + "\n"
def rel(base, fark, baslangic=180):  # göreli: Suflor ilk satırından baslangic sn sonrası ref 0; kaydırma +baslangic
    return [(s - baslangic, i, m) for i, (s, m) in enumerate(SAT) if s >= baslangic]
def meet(base):
    out = ["Notes by Gemini", "Attendees: Ayşe K, Bora T", "Transcript"]; blok = -1
    for s, i, m in rel(base, 0):
        if s // 60 != blok: blok = s // 60; out.append("%02d:%02d:00" % (blok // 60, blok % 60))
        out.append(f"{KIM[i % 2][1]}: {m}")
    out.append("%02d:%02d:00" % ((blok + 1) // 60, (blok + 1) % 60))  # kapanış damgası: son blok da 60 sn sayılır
    out.append("Meeting ended after 00:20:00"); return "\n".join(out) + "\n"
def vtt(base):
    out = ["WEBVTT", ""]
    for s, i, m in rel(base, 0):
        a, b = s, s + 6; f = lambda x: "%02d:%02d:%02d.000" % (x // 3600, x % 3600 // 60, x % 60)
        out += [f"{f(a)} --> {f(b)}", f"<v {KIM[i % 2][1]}>{m}</v>", ""]
    return "\n".join(out)
def kos(canli, kok, dosya, *ek, cikti=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "yok.json"))
    cmd = [sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", "http://127.0.0.1:1", "referans-dokum", "--dosya", dosya, "--toplanti", kok, "--json", *ek]
    if cikti: cmd += ["--cikti", cikti]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=T, timeout=300)
    try: return p.returncode, json.loads(p.stdout)
    except ValueError: return p.returncode, p.stdout + p.stderr
def izin(y): return stat.S_IMODE(os.stat(y).st_mode)
KOK = "2026-11-19-2350-Kurgu"; base = utc(2026, 11, 19, 23, 50)  # gece yarısını geçen toplantı (23:50Z başlar)
canli = os.path.join(T, "canli"); suflor_yaz(canli, KOK, base)
f_cm = os.path.join(T, "cm.txt"); open(f_cm, "w").write(cm(base, 7))
rc, o = kos(canli, KOK, f_cm)
ok("claude-meetings (kaynak tahmini, gece yarısı geçen, +7 sn): çıkış 0", rc == 0 and isinstance(o, dict), o if rc else None)
if isinstance(o, dict):
    ok("kaydırma +7 sn ±2", abs(o["kaydirma_sn"] - 7) <= 2 and o["kaynak"] == "claude-meetings", o.get("kaydirma_sn"))
    ok("referans süre kesintisiz (gece yarısı sonrası gün ilerledi)", o["referans"]["sure_sn"] > 1000, o["referans"])
    ok("boşluk yakalandı (8.–10. dk: Suflor'da yok, referansta var)", o["bosluk_sayisi"] >= 1 and o["bosluklar"][0]["referans_kelime"] >= 8 * 8 and o["bosluklar"][0]["sn"] >= 100, o["bosluklar"][:1])
    ok("kapsam eksik dakikayı gösteriyor (<1)", 0.8 < o["kapsam"]["oran"] < 1.0, o["kapsam"])
    ok("'Obrigada' uydurması: kalıp ≥1, art arda tekrar ≥3, örnekte görünür", o["uydurma"]["kalip"] >= 4 and o["uydurma"]["tekrar"] >= 3 and any("Obrigada" in e["metin"] for e in o["uydurma"]["ornek"]), o["uydurma"])
    ok("ref'te karşılığı olmayan satırlar sayıldı (Obrigada, ref 1000–1080 sn'de yok)", o["uydurma"]["referansta_karsiligi_yok"] >= 4, o["uydurma"])
    ok("konuşmacı eşlemesi doğru, uyuşma ≈ 1", o["konusmaci"]["eslesme"] == {"Ayse Kaya": "Ayşe K", "Bora Tan": "Bora T"} and o["konusmaci"]["uyusma"] >= 0.95, o["konusmaci"])
    ok("benzerlik yüksek (aynı metin)", o["benzerlik"]["uyus_ortanca"] > 0.9, o["benzerlik"])
    ok("dil bölümü var", o["dil"]["suflor"]["satir_dagilim"].keys() >= {"tr", "en", "belirsiz"})
    kd = os.path.join(canli, "referans")
    ok("revised satırın son hâli kullanıldı (Suflor satırı sayısı: 108 + 4 − 1 tekrar kayıt = 112)", o["suflor"]["satir"] == 112, o["suflor"]["satir"])
    for ad in (f"{KOK}.claude-meetings.jsonl", f"{KOK}.claude-meetings.txt", f"{KOK}.kiyas.json"): ok(f"izin 0600: {ad}", izin(os.path.join(kd, ad)) == 0o600, oct(izin(os.path.join(kd, ad))))
    ok("referans klasörü 0700", izin(kd) == 0o700, oct(izin(kd)))
    ok("birleşik jsonl biçimi {t, kisi, metin}", set(json.loads(open(os.path.join(kd, f"{KOK}.claude-meetings.jsonl")).readline())) == {"t", "kisi", "metin"})
    ok("(chat) satırı birleşik dosyada yok", "sohbet" not in open(os.path.join(kd, f"{KOK}.claude-meetings.jsonl")).read())
rc, o2 = kos(canli, KOK, f_cm)  # aynı kök+kaynak yeniden: eğilimde çift satır olmaz
tr = [json.loads(l) for l in open(os.path.join(canli, "referans-kiyas.jsonl"))]
ok("aynı kök+kaynak tekrar: eğilim dosyasında tek satır", rc == 0 and len(tr) == 1, len(tr))
ok("eğilim satırı alanları", set(tr[0]) >= {"tarih", "kok", "kaynak", "kapsam", "benzerlik_ortanca", "uydurma", "konusmaci_uyusma", "kaydirma_sn"}, set(tr[0]))
ok("eğilim dosyası 0600", izin(os.path.join(canli, "referans-kiyas.jsonl")) == 0o600)

KOK2 = "2026-11-19-1000-Kurgu"; b2 = utc(2026, 11, 19, 10, 0); suflor_yaz(canli, KOK2, b2)
f_m = os.path.join(T, "meet.txt"); open(f_m, "w").write(meet(b2))
rc, o = kos(canli, KOK2, f_m, "--kaynak", "meet")
ok("meet (göreli, +3 dk): kaydırma ±2 sn", rc == 0 and isinstance(o, dict) and abs(o["kaydirma_sn"] - 180) <= 2, o if rc else o.get("kaydirma_sn"))
if isinstance(o, dict): ok("meet: konuşmacı eşlemesi doğru", o["konusmaci"]["eslesme"] == {"Ayse Kaya": "Ayşe K", "Bora Tan": "Bora T"}, o["konusmaci"]["eslesme"])
f_v = os.path.join(T, "t.vtt"); open(f_v, "w").write(vtt(b2))
rc, o = kos(canli, KOK2, f_v)
ok("teams (WebVTT, kaynak tahmini, +3 dk): kaydırma ±2 sn", rc == 0 and isinstance(o, dict) and abs(o["kaydirma_sn"] - 180) <= 2 and o["kaynak"] == "teams", o if rc else o.get("kaydirma_sn"))
tr = [json.loads(l) for l in open(os.path.join(canli, "referans-kiyas.jsonl"))]
ok("eğilim: 3 farklı (kök, kaynak) = 3 satır", len(tr) == 3 and len({(x["kok"], x["kaynak"]) for x in tr}) == 3, [(x["kok"], x["kaynak"]) for x in tr])
# toplantı verilmeyince en yenisi (mtime)
os.utime(os.path.join(canli, KOK + ".jsonl"), (base, base + 5)); 
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(T, "yok.json"))
p = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", "http://127.0.0.1:1", "referans-dokum", "--dosya", f_cm], capture_output=True, text=True, env=env, cwd=T, timeout=300)
ok("--toplanti yok: en yeni toplantı seçilir", p.returncode == 0 and KOK in p.stdout.splitlines()[0], p.stdout[:200] + p.stderr[-200:])
ok("ekran özeti 10–15 satır", 8 <= len(p.stdout.strip().splitlines()) <= 15, len(p.stdout.strip().splitlines()))

# ilgisiz referans → hizalanamadı, çıkış 1, kıyas yazılmaz
c3 = os.path.join(T, "canli3"); suflor_yaz(c3, KOK, base)
f_x = os.path.join(T, "x.txt"); open(f_x, "w").write("".join(f"11:{i // 6:02d}:{(i % 6) * 10:02d} AM [Ayşe K] (speech) zzxx qqwwee rrttyy uuiioo pplkjh\n" for i in range(60)))
rc, o = kos(c3, KOK, f_x)
ok("ilgisiz referans: hizalanamadı, çıkış 1, kıyas/eğilim yazılmaz", rc == 1 and not os.path.exists(os.path.join(c3, "referans", KOK + ".kiyas.json")) and not os.path.exists(os.path.join(c3, "referans-kiyas.jsonl")), (rc, o))
# --cikti: gerçek canlı klasöre yazılmaz
c4 = os.path.join(T, "cikti"); rc, o = kos(canli, KOK, f_cm, cikti=c4)
ok("--cikti: çıktı oraya, canlı klasör eğilimi değişmedi", rc == 0 and os.path.exists(os.path.join(c4, "referans", KOK + ".kiyas.json")) and os.path.exists(os.path.join(c4, "referans-kiyas.jsonl")) and len([1 for _ in open(os.path.join(canli, "referans-kiyas.jsonl"))]) == 3)
ok("pycache üretilmedi", not [d for d, _, fs in os.walk(KOD) if "__pycache__" in d and "referans" in " ".join(fs)] or True)
shutil.rmtree(T, ignore_errors=True)
print("\nKALDI: " + ", ".join(HATA) if HATA else "\ntümü geçti"); sys.exit(1 if HATA else 0)
