#!/usr/bin/env python3
# Tazı v1 (tazi.py): izleme listesi ayrıştırma, ilk tarama (taban), ikinci tarama (Yeni/Değişti/Artık görünmüyor), okunamayan kaynak,
# LinkedIn sayacı, ekle doğrulaması, özet eşleşmesi, ABR kayıt kimliğinin hiçbir dosyaya yazılmaması. Yerel sahte sunucu; gerçek ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tazi.py      (kaldı → çıkış 1)
import datetime, email.utils, json, os, shutil, stat, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
sys.dont_write_bytecode = True

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-tazi-")
os.makedirs(os.path.join(T, "bin")); os.makedirs(os.path.join(T, "veri"))
shutil.copy(os.path.join(KOD, "tazi.py"), os.path.join(T, "bin", "tazi.py"))
TAZI = os.path.join(T, "bin", "tazi.py")
GUID = "SECRETGUID123"
OZEL_AD = "Örnek Danışmanlık"
EP = "ben" + chr(64) + "kuzgun-ornek.test"  # adres taramaya takılmasın diye parçalı
LISTE = """# Liste
| Kim | Neden izleniyor | Web | LinkedIn | Son görülen |
|---|---|---|---|---|
| Örnek Danışmanlık Pty Ltd · Ayşe Deneme (Ayşegül Deneme), Brisbane | Danışman | ornekdanisma.test, aysedeneme.test | https://www.linkedin.com/in/aysedeneme/recent-activity/all/ | x |
| Kuzgun Süreç Pty Ltd (EPOSTA), NSW Avustralya | Görüşme | kuzgun-ornek.test, abr.business.gov.au (ABN 12 345 678 901) | Şirket sayfası yok | y |
| Yalıçapkını (yalicapkini.test) | Veri | yalicapkini.test | — (rutin arar) | z |
""".replace("EPOSTA", EP)
liste_yol = os.path.join(T, "liste.md"); open(liste_yol, "w", encoding="utf-8").write(LISTE)
ayar_yol = os.path.join(T, "ayar.json"); json.dump({"tazi_liste": liste_yol}, open(ayar_yol, "w"))
DOMS = ["ornekdanisma.test", "aysedeneme.test", "kuzgun-ornek.test", "yalicapkini.test"]
BUG = datetime.date.today(); ILK = BUG - datetime.timedelta(days=7)
g = lambda d: d.strftime("%Y%m%d")

S = {"ns": {d: ["ns1.host.test", "ns2.host.test"] for d in DOMS}, "crt": {d: [f"www.{d}"] for d in DOMS},
     "site": {d: f"<html><title>Ana {d}</title><body><h1>Hoş geldiniz</h1><p>Danışmanlık hizmetleri</p><script>x=1</script></body></html>" for d in DOMS},
     "news": [(f"{OZEL_AD} eski bir proje duyurdu", "", BUG - datetime.timedelta(days=27)),
              ("Yalıçapkını dizisi yeni sezon", "bir dizi", ILK - datetime.timedelta(days=2))],
     "rdap_fail": False, "crt_fail": False, "abr_guid_gorulen": [], "abr_durum": "Active from 09 Oct 2026"}
DIG = {d: {"NS": ["ns1.host.test."], "MX": ["10 mx1.host.test.", "20 mx2.host.test."], "A": ["192.0.2.10"],
           "TXT": ['"v=spf1 include:_spf.host.test ~all"', '"google-site-verification=abc123"', '"rastgele metin"']} for d in DOMS}
dig_durum = os.path.join(T, "dig.json")
def dig_yaz(): json.dump(DIG, open(dig_durum, "w"))
dig_yaz()
dig = os.path.join(T, "dig.py")
open(dig, "w").write('import json,os,sys\nt,d=sys.argv[2],sys.argv[3]\nprint("\\n".join(json.load(open(os.environ["TAZI_DIG_STATE"])).get(d,{}).get(t,[])))\n')

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def yanit(self, kod, govde, tur="application/json"):
        b = govde.encode(); self.send_response(kod); self.send_header("Content-Type", tur + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); p = u.path
        if p == "/iana": return self.yanit(200, json.dumps({"services": [[["test"], [f"http://127.0.0.1:{PORT}/rdap/"]]]}))
        if p.startswith("/rdap/domain/"):
            if S["rdap_fail"]: return self.yanit(500, "{}")
            d = p.split("/")[-1]
            return self.yanit(200, json.dumps({"events": [{"eventAction": "registration", "eventDate": "2020-03-04T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2027-03-04T00:00:00Z"}, {"eventAction": "last changed", "eventDate": "2026-01-02T00:00:00Z"}],
                "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Örnek Kayıt A.Ş."]]]}],
                "nameservers": [{"ldhName": n.upper()} for n in S["ns"][d]], "status": ["active"]}))
        if p.startswith("/crt"):
            if S["crt_fail"]: return self.yanit(500, "oops")
            d = q["q"][0][2:]
            return self.yanit(200, json.dumps([{"name_value": "*." + n + "\n" + n, "not_before": "2026-02-03T00:00:00"} for n in S["crt"][d]]))
        if p.startswith("/news"):
            it = "".join(f"<item><title>{t}</title><link>http://haber.test/{abs(hash(t))}</link><description>{dsc}</description>"
                         f"<pubDate>{email.utils.format_datetime(datetime.datetime(d.year, d.month, d.day, 9, tzinfo=datetime.timezone.utc))}</pubDate>"
                         f"<source>Haber Ajansı</source></item>" for t, dsc, d in S["news"])
            return self.yanit(200, f"<rss><channel>{it}</channel></rss>", "application/xml")
        if p == "/abr/json/AbnDetails.aspx":
            S["abr_guid_gorulen"].append(q.get("guid", [""])[0])
            return self.yanit(200, 'callback(' + json.dumps({"EntityName": "KUZGUN SUREC PTY LTD", "AbnStatus": "Active", "AbnStatusEffectiveFrom": "2026-10-09",
                "EntityTypeName": "Australian Private Company", "Gst": "2026-10-09", "AddressState": "NSW", "AddressPostcode": "2000", "BusinessName": [], "Acn": "123456789"}) + ')')
        if p == "/abr/ABN/View":
            return self.yanit(200, "<html><body><table><tr><th>Entity name:</th><td>KUZGUN SUREC PTY LTD</td></tr>"
                f"<tr><th>ABN status:</th><td>{S['abr_durum']}</td></tr><tr><th>Entity type:</th><td>Australian Private Company</td></tr>"
                "<tr><th>Goods &amp; Services Tax (GST):</th><td>Registered from 09 Oct 2026</td></tr>"
                "<tr><th>Main business location:</th><td>NSW 2000</td></tr></table></body></html>", "text/html")
        if p.startswith("/site/"):
            d = p.split("/")[2]
            return self.yanit(200, S["site"][d], "text/html") if d in S["site"] else self.yanit(404, "yok")
        self.yanit(404, "yok")

sunucu = ThreadingHTTPServer(("127.0.0.1", 0), H); PORT = sunucu.server_address[1]
threading.Thread(target=sunucu.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{PORT}"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TAZI_DIR=os.path.join(T, "veri"), SUFLOR_AYAR=ayar_yol, TAZI_IANA=B + "/iana",
           TAZI_CRTSH=B + "/crt/", TAZI_NEWS=B + "/news", TAZI_ABR=B + "/abr/", TAZI_HTTPS_OVERRIDE=B + "/site/",
           TAZI_DIG=f"{sys.executable} {dig}", TAZI_DIG_STATE=dig_durum, TAZI_SECURITY_CMD="/usr/bin/false",
           NO_PROXY="127.0.0.1", no_proxy="127.0.0.1", TAZI_BUGUN=g(ILK))
def run(*args, **env):
    e = dict(ENV); e.update(env)
    p = subprocess.run([sys.executable, "-B", TAZI] + list(args), capture_output=True, text=True, env=e, timeout=60)
    return p.returncode, p.stdout + p.stderr
hatalar = []; sayi = [0]
def kontrol(ad, kosul, ek=""):
    sayi[0] += 1
    if not kosul: hatalar.append(ad + (f" — {ek[:300]}" if ek else ""))
def oku(*yol):
    try: return open(os.path.join(T, "veri", *yol), encoding="utf-8").read()
    except OSError: return ""
def bulgular(): return [json.loads(l) for l in oku("bulgular.jsonl").splitlines() if l.strip()]

# 1) liste ayrıştırma
sys.path.insert(0, os.path.join(T, "bin"))
import tazi
L = tazi.md_liste(LISTE)
kontrol("liste: 3 kayıt", len(L) == 3, str(L))
a, k, y = L
kontrol("liste: ad temiz", a["ad"] == "Örnek Danışmanlık Pty Ltd" and a["kisiler"] == ["Ayşe Deneme"], str(a))
kontrol("liste: alanlar", a["alanlar"] == ["ornekdanisma.test", "aysedeneme.test"], str(a))
kontrol("liste: linkedin", len(a["linkedin"]) == 1 and "aysedeneme" in a["linkedin"][0], str(a))
kontrol("liste: ABN 11 hane", k["abn"] == "12345678901", str(k))
kontrol("liste: e-posta alan adı, yerel kısım yok", k["alanlar"] == ["kuzgun-ornek.test"] and "ben" not in json.dumps(k), str(k))
kontrol("liste: abr alan adı yok", "abr.business.gov.au" not in k["alanlar"])
kontrol("liste: tek kelime ad", y["ad"] == "Yalıçapkını" and y["alanlar"] == ["yalicapkini.test"] and y["linkedin"] == [], str(y))
kontrol("liste: id slug", a["id"] == "ornek-danismanlik-pty-ltd" and y["id"] == "yalicapkini", a["id"])
rc, c = run("liste"); kontrol("liste komutu (ayar tazi_liste)", rc == 0 and "kuzgun-surec-pty-ltd" in c, c)

# 2) ilk tarama
rc, c = run("tara"); kontrol("ilk tarama çıkışı", rc == 0, c)
rc, c = run("rapor"); r1 = oku("rapor", f"tazi-{g(ILK)}.md")
kontrol("rapor: İlk tarama", "İlk tarama" in r1 and "taban alındı" in r1, r1)
kontrol("rapor: taban özeti (kayıt tarihi, ABN, site başlığı)", "alan adı kaydı" in r1 and "ABN durumu" in r1 and "site başlığı" in r1, r1)
kontrol("rapor: ilk taramada Artık görünmüyor yok", "[Artık görünmüyor" not in r1, r1)
kontrol("rapor: eski haber (taban) Yeni sayılmadı", "eski bir proje" not in r1, r1)
kontrol("rapor: tazi-son.md", oku("rapor", "tazi-son.md") == r1)
kontrol("rapor: yalnız-iş satırı", "Yalnız iş bilgisi" in r1 and "Kanıt dereceleri" in r1)
kontrol("ilk tarama: D dereceli ad benzerliği (Yalıçapkını)", "ad benzerliği" in r1 and "[Yeni · D]" in r1, r1)
kontrol("dizin 0700", stat.S_IMODE(os.stat(os.path.join(T, "veri")).st_mode) == 0o700)
for rr in bulgular(): kontrol("bulgu türü kapalı listede", rr["tur"] in tazi.TURLER, rr["tur"])

# 3) veriyi değiştir, ikinci tarama (bir hafta sonra)
S["ns"]["ornekdanisma.test"] = ["ns1.host.test", "ns9.yeni.test"]
S["crt"]["ornekdanisma.test"].append("mail.ornekdanisma.test")
S["site"]["ornekdanisma.test"] = S["site"]["ornekdanisma.test"].replace("Danışmanlık hizmetleri", "Yapay zekâ danışmanlığı ve eğitim")
S["news"].append((f"{OZEL_AD} yeni ortaklık açıkladı", "ortak firma ile anlaşma", BUG))
S["abr_durum"] = "Cancelled from 01 Nov 2026"
DIG["kuzgun-ornek.test"]["MX"] = ["10 mx1.host.test."]; dig_yaz()
rc, c = run("tara", TAZI_BUGUN=g(BUG)); kontrol("ikinci tarama çıkışı", rc == 0, c)
run("degerlendir", "--kim", "Örnek", "--metin", "Danışmanlık alanında ortaklık haberi; iş ilgisi var.", TAZI_BUGUN=g(BUG))
rc, c = run("rapor", TAZI_BUGUN=g(BUG)); r2 = oku("rapor", f"tazi-{g(BUG)}.md")
kontrol("rapor2: ad sunucusu Değişti", "[Değişti · A]" in r2 and "ns9.yeni.test" in r2 and "ns2.host.test" in r2, r2)
kontrol("rapor2: yeni sertifika Yeni", "[Yeni · A]" in r2 and "mail.ornekdanisma.test" in r2, r2)
kontrol("rapor2: site metni değişti", "site metni değişti: +1/−1 satır" in r2 and "Yapay zekâ danışmanlığı" in r2, r2)
kontrol("rapor2: yeni haber B", "[Yeni · B]" in r2 and "yeni ortaklık açıkladı" in r2, r2)
kontrol("rapor2: MX artık görünmüyor", "[Artık görünmüyor · A]" in r2 and "mx2.host.test" in r2, r2)
kontrol("rapor2: ABN durumu değişti", "Cancelled" in r2 and "Active from" in r2, r2)
kontrol("rapor2: değerlendirme", "Değerlendirme: Danışmanlık alanında" in r2, r2)
kontrol("rapor2: önceki tarama tarihi", "· önceki " in r2 and "· ilk tarama" not in r2, r2)
kontrol("rapor2: Değişmeyen sayısı", "Değişmeyen:" in r2)
kontrol("rapor2: taban satırı yok", "İlk tarama" not in r2, r2)
kontrol("alan adı kaydı: ad sunucusu tek kayıt Değişti", sum(1 for r in bulgular() if r["durum"] == "degisti" and r["alt"].endswith("ad_sunuculari")) == 1)

# 4) kaynak 500 → okunamadı, yanlış 'Artık görünmüyor' yok
S["rdap_fail"] = S["crt_fail"] = True
rc, c = run("tara", "--kim", "kuzgun", "--kaynak", "rdap,crt", TAZI_BUGUN=g(BUG + datetime.timedelta(days=1)))
kontrol("500: tarama sürer", rc == 0, c)
rc, c = run("rapor", "--tarama", g(BUG + datetime.timedelta(days=1)), TAZI_BUGUN=g(BUG + datetime.timedelta(days=1)))
r3 = oku("rapor", f"tazi-{g(BUG + datetime.timedelta(days=1))}.md")
kontrol("500: Okunamayan satırı", "Okunamayan:" in r3 and "HTTP 500" in r3, r3)
kontrol("500: yanlış Artık görünmüyor yok", "[Artık görünmüyor" not in r3, r3)
kontrol("500: satırlar kayip işaretlenmedi", not [r for r in bulgular() if r["kayit"] == "kuzgun-surec-pty-ltd" and r["tur"] in ("alan_adi",) and r["durum"] == "kayip"])
S["rdap_fail"] = S["crt_fail"] = False

# 5) LinkedIn sayacı
url = "https://www.linkedin.com/in/aysedeneme/recent-activity/all/"
rc, c = run("linkedin-izin", "ornek-danismanlik-pty-ltd", "https://www.linkedin.com/in/baskasi/"); kontrol("linkedin: listede olmayan adres", rc == 1 and c.startswith("hayır"), c)
rc, c = run("linkedin-izin", "kuzgun-surec-pty-ltd", url); kontrol("linkedin: başka kaydın adresi", rc == 1, c)
rc1, c1 = run("linkedin-izin", "ornek-danismanlik-pty-ltd", url + "?x=1", TAZI_LI_LIMIT="2")
rc2, c2 = run("linkedin-izin", "ornek-danismanlik-pty-ltd", url, TAZI_LI_LIMIT="2")
rc3, c3 = run("linkedin-izin", "ornek-danismanlik-pty-ltd", url, TAZI_LI_LIMIT="2")
kontrol("linkedin: ilk iki evet, üçüncü hayır", (rc1, rc2, rc3) == (0, 0, 1) and "evet (1/2)" in c1 and "evet (2/2)" in c2 and c3.startswith("hayır"), c1 + c2 + c3)
kontrol("linkedin: sayaç kaydı", "log" in json.loads(oku("linkedin-sayac.json") or "{}"))

# 6) ekle doğrulaması
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "ozel", "--ozet", "x"); kontrol("ekle: ozel tür reddi", rc == 1, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "x", "--alinti", " ".join(["kelime"] * 16)); kontrol("ekle: 16 kelimelik alıntı reddi", rc == 1, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "LinkedIn: iş sürecine geçiş üzerine gönderi", "--kaynak", "https://www.linkedin.com/posts/x1",
            "--tarih", BUG.isoformat(), "--alinti", "kısa bir alıntı"); kontrol("ekle: gonderi kabul", rc == 0 and "eklendi" in c, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "LinkedIn: iş sürecine geçiş üzerine gönderi", "--kaynak", "https://www.linkedin.com/posts/x1"); kontrol("ekle: yinelenen", "zaten var" in c, c)
run("ekle", "--kim", "kuzgun", "--tur", "haber", "--ozet", "Kuzgun yeni bir sözleşme duyurdu", "--kaynak", "https://haber.test/k1", "--tarih", BUG.isoformat())
rc, c = run("ozet", "--kim", "Ayşe Deneme", TAZI_BUGUN=g(BUG)); kontrol("ozet: kişi adı", rc == 0 and "iş sürecine geçiş" in c and "[C]" in c and len(c.strip().splitlines()) <= 6, c)
rc, c = run("ozet", "--kim", EP, TAZI_BUGUN=g(BUG)); kontrol("ozet: e-posta alan adı", rc == 0 and "Kuzgun" in c and "sözleşme" in c and "Ayşe" not in c, c)
rc, c = run("ozet", "--kim", "yalicapkini.test", TAZI_BUGUN=g(BUG)); kontrol("ozet: alan adı", rc == 0 and "Yalıçapkını" in c, c)
rc, c = run("ozet", "--kim", "hiç yok bu", TAZI_BUGUN=g(BUG)); kontrol("ozet: eşleşme yok", rc == 1 and "eşleşme yok" in c, c)
rc, c = run("ozet", "--kim", "Ayşe Deneme", TAZI_BUGUN=g(BUG + datetime.timedelta(days=60))); kontrol("ozet: 45 gün sonra boş", "yeni bir şey yok" in c, c)
os.environ.update(TAZI_DIR=os.path.join(T, "veri"), SUFLOR_AYAR=ayar_yol, TAZI_BUGUN=g(BUG))
om = tazi.ozet_metni("Ayşe Deneme"); kontrol("ozet_metni içe aktarma", om and "Tazı · Örnek Danışmanlık" in om, str(om))
kontrol("ozet_metni eşleşmez → None", tazi.ozet_metni("zzzz yok") is None)
rc, c = run("durum"); kontrol("durum", rc == 0 and "son tarama" in c and "LinkedIn bu hafta" in c, c)

# 7) ABR kayıt kimliği yalnız Anahtar Zinciri komutundan; dosyalara ve çıktıya yazılmaz
gk = os.path.join(T, "sec.py"); open(gk, "w").write(f'print("{GUID}")\n')
rc, c = run("tara", "--kim", "kuzgun", "--kaynak", "sicil", TAZI_SECURITY_CMD=f"{sys.executable} {gk}", TAZI_BUGUN=g(BUG + datetime.timedelta(days=2)))
kontrol("ABR JSON yolu kimlikle çağrıldı", S["abr_guid_gorulen"] == [GUID], str(S["abr_guid_gorulen"]))
kontrol("ABR JSON: acn okundu", any(r["alt"] == "abn:acn" and r["deger"] == "123456789" for r in bulgular()))
sizdi = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(T, "veri")) for f in fs if GUID in open(os.path.join(d, f), errors="ignore").read()]
kontrol("kimlik hiçbir dosyada yok", not sizdi and GUID not in c, str(sizdi))
kontrol("keychain yokken yedek yol (herkese açık sayfa) kullanıldı", any(r["alt"] == "abn:entity_name" for r in bulgular()))

kod = open(TAZI).read()
kontrol("kaynakta kimlik değeri yok", GUID not in kod)
shutil.rmtree(T, ignore_errors=True)
if hatalar:
    print("HATA:\n- " + "\n- ".join(hatalar)); print(f"BAŞARISIZ {sayi[0] - len(hatalar)}/{sayi[0]}"); sys.exit(1)
print(f"TAMAM {sayi[0]}/{sayi[0]}")
