#!/usr/bin/env python3
# Tazı v1+v2 (tazi.py): izleme listesi ayrıştırma, ilk tarama (taban), ikinci tarama (Yeni/Değişti/Artık görünmüyor), okunamayan kaynak,
# sosyal bütçe (LinkedIn/X), ekle doğrulaması, özet eşleşmesi, ABR kayıt kimliğinin hiçbir dosyaya yazılmaması; v2 dedektif kipi:
# Wayback, site taraması (robots/sitemap/sosyal/analitik/varlık), altyapı (DMARC/MX/SPF/IP RDAP), GitHub, bağlantı haritası ve
# bayraklar, soruşturma dosyası. Yerel sahte sunucu; gerçek ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/tazi.py      (kaldı → çıkış 1)
import datetime, email.utils, json, os, shutil, stat, subprocess, sys, tempfile, threading, time
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
AT = chr(64)  # kaynakta düz e-posta adresi durmasın
EP = "ben" + AT + "kuzgun-ornek.test"  # adres taramaya takılmasın diye parçalı
YEREL = "iletisimkisi77"; DMYEREL = "dmarcuser99"
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

ORN = "ornekdanisma.test"; KUZ = "kuzgun-ornek.test"; YAL = "yalicapkini.test"
HOME_ORN = (f'<html><head><title>Ana {ORN}</title><meta name="generator" content="TestCMS 4.2">'
            '<script src="https://cdn.vendor-x.test/lib.js"></script><script src="https://www.googletagmanager.com/gtag/js"></script>'
            "<script>gtag('config','G-ABCDEF123'); fbq('init', '1234567890123');</script></head><body><h1>Hoş geldiniz</h1>"
            "<p>Danışmanlık hizmetleri</p>"
            '<a href="/hakkimizda"></a><a href="/gizli/x"></a><a href="/iletisim"></a><a href="/foto.png"></a>'
            '<a href="https://twitter.com/ornekfirma"></a><a href="https://twitter.com/intent/tweet?text=x"></a><a href="https://x.com/share"></a>'
            '<a href="https://github.com/ornekorg"></a><a href="https://www.linkedin.com/company/ornek-danismanlik/"></a>'
            "</body></html>")
HOME_KUZ = (f'<html><head><title>Ana {KUZ}</title><script src="https://cdn.vendor-x.test/lib.js"></script>'
            "<script>gtag('config','G-ABCDEF123');</script></head><body><h1>Hoş geldiniz</h1><p>Danışmanlık hizmetleri</p>"
            '<a href="/privacy"></a><a href="https://github.com/kuzguner"></a></body></html>')
S = {"ns": {d: ["ns1.host.test", "ns2.host.test"] for d in DOMS}, "crt": {d: [f"www.{d}"] for d in DOMS},
     "site": {d: f"<html><title>Ana {d}</title><body><h1>Hoş geldiniz</h1><p>Danışmanlık hizmetleri</p><script>x=1</script></body></html>" for d in DOMS},
     "sayfa": {(ORN, "/hakkimizda"): "<html><title>Hakkımızda</title><body><p>Biz küçük bir ekibiz.</p></body></html>",
               (ORN, "/gizli/x"): "<html><title>Gizli</title><body>gizli</body></html>",
               (ORN, "/iletisim"): f"<html><title>İletişim</title><body><p>12 Mock Street, Sydney NSW 2000</p><p>info {YEREL}{AT}partner-ornek.test</p></body></html>",
               (ORN, "/kariyer"): "<html><title>Kariyer</title><body><p>Açık pozisyon yok.</p></body></html>",
               (KUZ, "/privacy"): "<html><title>Gizlilik</title><body><p>Bu site Parlak Cozum Pty Ltd tarafından işletilir. ABN 98 765 432 109</p></body></html>"},
     "robots": {ORN: "User-agent: *\nDisallow: /gizli/\n"},
     "sitemap": {ORN: f"<urlset><url><loc>https://{ORN}/hakkimizda</loc></url><url><loc>https://{ORN}/iletisim</loc></url></urlset>"},
     "kayit": {YAL: (ILK - datetime.timedelta(days=30)).isoformat()},
     "istek": [], "gh_repos": [("arac-bir", "2024-01-02T00:00:00Z", "2026-10-01T00:00:00Z")],
     "news": [(f"{OZEL_AD} eski bir proje duyurdu", "", BUG - datetime.timedelta(days=27)),
              ("Yalıçapkını dizisi yeni sezon", "bir dizi", ILK - datetime.timedelta(days=2))],
     "rdap_fail": False, "crt_fail": False, "abr_guid_gorulen": [], "abr_durum": "Active from 09 Oct 2026"}
S["site"][ORN] = HOME_ORN; S["site"][KUZ] = HOME_KUZ
DIG = {d: {"NS": ["ns1.host.test."], "MX": ["10 mx1.host.test.", "20 mx2.host.test."], "A": ["192.0.2.10"],
           "TXT": ['"v=spf1 include:_spf.host.test include:_spf.google.com ~all"', '"google-site-verification=abc123"', '"rastgele metin"']} for d in DOMS}
DIG["_dmarc." + KUZ] = {"TXT": ["\"v=DMARC1; p=reject; rua=mailto:" + DMYEREL + AT + "dmarc-vendor.test\""]}
DIG[YAL]["MX"] = ["10 aspmx.l.google.com."]
dig_durum = os.path.join(T, "dig.json")
def dig_yaz(): json.dump(DIG, open(dig_durum, "w"))
dig_yaz()
dig = os.path.join(T, "dig.py")
open(dig, "w").write('import json,os,sys\nt,d=sys.argv[2],sys.argv[3]\nprint("\\n".join(json.load(open(os.environ["TAZI_DIG_STATE"])).get(d,{}).get(t,[])))\n')

class H(BaseHTTPRequestHandler):
    server_version = "TestSrv/1.0"; sys_version = ""
    def log_message(self, *a): pass
    def yanit(self, kod, govde, tur="application/json"):
        b = govde.encode(); self.send_response(kod); self.send_header("Content-Type", tur + "; charset=utf-8")
        self.send_header("X-Powered-By", "TestPHP/8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); p = u.path
        S["istek"].append(p)
        if p == "/wb/cdx":
            d = q["url"][0]
            if d.endswith("/*"):
                d = d[:-2]
                return self.yanit(200, json.dumps([["timestamp", "original", "statuscode"],
                    ["20190214093000", f"http://{d}/eski-urun?x=1", "200"], ["20200101000000", f"https://{d}/", "200"],
                    ["20200202000000", f"https://{d}/hakkimizda", "200"], ["20200303000000", f"https://{d}/logo.png", "200"],
                    ["20200404000000", f"https://{d}/kayip", "404"]]))
            return self.yanit(200, json.dumps([["timestamp"], ["20190214093000"]]))
        if p == "/iana-ip": return self.yanit(200, json.dumps({"services": [[["192.0.2.0/24"], [f"http://127.0.0.1:{PORT}/iprdap/"]]]}))
        if p.startswith("/iprdap/ip/"):
            return self.yanit(200, json.dumps({"name": "TESTNET-AG", "country": "AU",
                "entities": [{"vcardArray": ["vcard", [["fn", {}, "text", "Ornek Barindirma"]]]}]}))
        if p.startswith("/gh/"):
            if p == "/gh/orgs/ornekorg": return self.yanit(200, json.dumps({"login": "ornekorg", "created_at": "2018-05-06T00:00:00Z", "public_repos": len(S["gh_repos"])}))
            if p == "/gh/orgs/ornekorg/repos":
                return self.yanit(200, json.dumps([{"name": n, "created_at": c, "pushed_at": pu} for n, c, pu in S["gh_repos"]]))
            if p == "/gh/users/kuzguner": return self.yanit(200, json.dumps({"login": "kuzguner", "created_at": "2021-01-01T00:00:00Z", "public_repos": 0}))
            if p == "/gh/users/kuzguner/repos": return self.yanit(200, "[]")
            return self.yanit(404, "{}")
        if p == "/iana": return self.yanit(200, json.dumps({"services": [[["test"], [f"http://127.0.0.1:{PORT}/rdap/"]]]}))
        if p.startswith("/rdap/domain/"):
            if S["rdap_fail"]: return self.yanit(500, "{}")
            d = p.split("/")[-1]
            return self.yanit(200, json.dumps({"events": [{"eventAction": "registration", "eventDate": S["kayit"].get(d, "2020-03-04") + "T00:00:00Z"},
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
            parca = p.split("/"); d = parca[2]; yol = "/" + "/".join(parca[3:])
            if yol == "/robots.txt": return self.yanit(200, S["robots"][d], "text/plain") if d in S["robots"] else self.yanit(404, "yok")
            if yol == "/sitemap.xml": return self.yanit(200, S["sitemap"][d], "application/xml") if d in S["sitemap"] else self.yanit(404, "yok")
            if yol == "/": return self.yanit(200, S["site"][d], "text/html") if d in S["site"] else self.yanit(404, "yok")
            return self.yanit(200, S["sayfa"][(d, yol)], "text/html") if (d, yol) in S["sayfa"] else self.yanit(404, "yok")
        self.yanit(404, "yok")

sunucu = ThreadingHTTPServer(("127.0.0.1", 0), H); PORT = sunucu.server_address[1]
threading.Thread(target=sunucu.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{PORT}"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TAZI_DIR=os.path.join(T, "veri"), SUFLOR_AYAR=ayar_yol, TAZI_IANA=B + "/iana",
           TAZI_CRTSH=B + "/crt/", TAZI_NEWS=B + "/news", TAZI_ABR=B + "/abr/", TAZI_HTTPS_OVERRIDE=B + "/site/",
           TAZI_WAYBACK=B + "/wb/cdx", TAZI_IANA_IP=B + "/iana-ip", TAZI_GITHUB=B + "/gh", TAZI_BEKLE="0",
           TAZI_DIG=f"{sys.executable} {dig}", TAZI_DIG_STATE=dig_durum, TAZI_SECURITY_CMD="/usr/bin/false",
           NO_PROXY="127.0.0.1", no_proxy="127.0.0.1", TAZI_BUGUN=g(ILK), TAZI_VT="-")
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

# 2b) v2 ilk tarama: arşiv, tarama, altyapı, kod, bağlantı
def satir(tur, alt_ek="", kayit=None):
    return [r for r in bulgular() if r["tur"] == tur and alt_ek in r["alt"] + " " + r["ozet"] and (kayit is None or r["kayit"] == kayit)]
ORN_ID = "ornek-danismanlik-pty-ltd"; KUZ_ID = "kuzgun-surec-pty-ltd"; YAL_ID = "yalicapkini"
kontrol("arşiv: ilk kayıt tarihi", any(r["deger"] == "2019-02-14" for r in satir("arsiv", ":ilk")), str(satir("arsiv")))
kontrol("arşiv: sayfa yolu normalleşti, sorgu ve varlık dosyası yok", satir("arsiv", "arşivde görülen sayfa: /eski-urun (ilk 2019-02-14)")
        and not satir("arsiv", "logo.png") and not satir("arsiv", "/kayip"), str(satir("arsiv", ":yol:")))
kontrol("arşiv: sayfa sayısı", any(r["alt"].endswith(":url_sayisi") and r["deger"] == "2" for r in satir("arsiv", kayit=ORN_ID)), str(satir("arsiv", ":url_sayisi")))
kontrol("robots: yasak yol olgusu", satir("teknoloji", "robots.txt yasak yolları", ORN_ID) and "/gizli/" in satir("teknoloji", "robots.txt", ORN_ID)[0]["deger"])
kontrol("robots: yasak yola hiç istek gitmedi", not [x for x in S["istek"] if "/gizli" in x], str([x for x in S["istek"] if "gizli" in x]))
kontrol("sitemap: olgu", satir("teknoloji", "sitemap.xml", ORN_ID))
kontrol("tarama: çok sayfa (ana + hakkımızda + iletişim)", {r["alt"] for r in bulgular() if r["tur"] == "site" and r["kayit"] == ORN_ID} ==
        {f"https://{ORN}/", f"https://{ORN}/hakkimizda", f"https://{ORN}/iletisim", f"https://{DOMS[1]}/"}, str([r["alt"] for r in bulgular() if r["tur"] == "site" and r["kayit"] == ORN_ID]))
kontrol("tarama: PNG indirilmedi", not [x for x in S["istek"] if x.endswith("foto.png")])
sh = {(r["plat"], r["handle"]) for r in bulgular() if r["tur"] == "sosyal_hesap" and r["kayit"] == ORN_ID}
kontrol("sosyal hesap: x (twitter.com), github, linkedin; intent/share atlandı", sh == {("x", "ornekfirma"), ("github", "ornekorg"), ("linkedin", "company/ornek-danismanlik")}, str(sh))
kontrol("analitik kimliği olgusu", satir("teknoloji", "analitik kimliği G-ABCDEF123", ORN_ID) and satir("teknoloji", "analitik kimliği 1234567890123", ORN_ID))
kontrol("üçüncü taraf kaynak olgusu", satir("teknoloji", "üçüncü taraf kaynak: cdn.vendor-x.test", ORN_ID))
kontrol("üretici ve başlıklar", satir("teknoloji", "TestCMS", ORN_ID) and satir("teknoloji", "TestSrv", ORN_ID) and satir("teknoloji", "TestPHP", ORN_ID))
kontrol("varlık: e-posta yalnız alan adı", satir("varlik", "e-posta alan adı: partner-ornek.test", ORN_ID))
kontrol("varlık: şirket adresi (iletişim sayfası)", satir("varlik", "12 Mock Street", ORN_ID) and satir("varlik", "12 Mock Street", ORN_ID)[0]["derece"] == "C")
kontrol("varlık: tüzel ad ve ABN (gizlilik sayfası)", satir("varlik", "Parlak Cozum Pty Ltd", KUZ_ID) and satir("varlik", "98765432109", KUZ_ID), str(satir("varlik", "", KUZ_ID)))
kontrol("altyapı: DMARC politikası ve rapor alanı", satir("teknoloji", "DMARC politikası", KUZ_ID) and satir("teknoloji", "dmarc-vendor.test", KUZ_ID))
kontrol("altyapı: DMARC yok olgusu", satir("teknoloji", "DMARC kaydı yok", ORN_ID))
kontrol("altyapı: MX sağlayıcısı", satir("teknoloji", "e-posta sağlayıcısı (yalicapkini.test): Google Workspace", YAL_ID))
kontrol("altyapı: SPF yetkili gönderici", satir("teknoloji", "SPF ile yetkili gönderici", ORN_ID) and satir("teknoloji", "_spf.host.test", ORN_ID) and satir("teknoloji", "Google Workspace", ORN_ID))
kontrol("altyapı: IP RDAP barındırma ağı", satir("teknoloji", "TESTNET-AG; Ornek Barindirma; AU", ORN_ID), str(satir("teknoloji", "barındırma", ORN_ID)))
kontrol("kod: GitHub org + depo (taban)", satir("kod", "ornekorg:org") and any(r["durum"] == "taban" and "arac-bir" in r["alt"] for r in bulgular()), str(satir("kod")))
kontrol("kod: kullanıcı yedeği (orgs 404 → users)", satir("kod", "kuzguner:org", KUZ_ID))
kontrol("bağlantı: aynı analitik kimliği iki kayıtta B", all(any(r["tur"] == "baglanti" and r["kayit"] == i and r.get("bk") == "analitik kimliği" and r.get("bv") == "G-ABCDEF123" and r["derece"] == "B" for r in bulgular()) for i in (ORN_ID, KUZ_ID)))
kontrol("bağlantı: ortak üçüncü taraf kaynak D, yaygın CDN atlandı", any(r.get("bk") == "üçüncü taraf kaynak" and r["derece"] == "D" and r.get("bv") == "cdn.vendor-x.test" for r in bulgular() if r["tur"] == "baglanti")
        and not any("googletagmanager" in str(r.get("bv")) for r in bulgular() if r["tur"] == "baglanti"))
kontrol("bayrak: yeni alan adı", satir("baglanti", "Bayrak: alan adı yalicapkini.test yalnız 30 gün", YAL_ID))
kontrol("bayrak: tüzel ad ABR'den farklı", satir("baglanti", "Bayrak: sitedeki tüzel ad «Parlak Cozum Pty Ltd»", KUZ_ID))
kontrol("bayrak: ABN alan adından genç (not)", satir("baglanti", "Bayrak: ABN etkin tarihi", KUZ_ID))
kontrol("bayrak: gizlilik sayfası yalnız olmayanda", satir("baglanti", "gizlilik/şartlar", ORN_ID) and not satir("baglanti", "gizlilik/şartlar", KUZ_ID), str(satir("baglanti", "gizlilik", KUZ_ID)))
rc, c = run("rapor"); r1 = oku("rapor", f"tazi-{g(ILK)}.md")
kontrol("rapor: Dosya bölümleri", all(x in r1 for x in ("### Dosya", "Kimlik doğrulama:", "Zaman çizelgesi:", "İddia ve kanıt:", "Çelişkiler ve bayraklar:", "Açık sorular:", "Sıradaki izler:")), r1[-1500:])
kontrol("rapor: zaman çizelgesi otomatik olaylar", "alan adı ornekdanisma.test kaydedildi" in r1 and "ilk arşiv kaydı" in r1 and "ilk sertifika kaydı" in r1 and "GitHub ornekorg kuruldu" in r1, r1)
kontrol("rapor: bayrak Dosya'da", "Bayrak: sitedeki tüzel ad" in r1, r1)
kontrol("rapor: Bağlantı haritası", "## Bağlantı haritası" in r1 and "analitik kimliği — G-ABCDEF123" in r1, r1)
kontrol("rapor: arşiv sayfaları ilk taramada taban özeti", "arşiv kaydı" in r1 or "arşiv" in r1)
for rr in bulgular(): kontrol("bulgu türü kapalı listede (v2)", rr["tur"] in tazi.TURLER, rr["tur"])

# 3) veriyi değiştir, ikinci tarama (bir hafta sonra)
S["ns"]["ornekdanisma.test"] = ["ns1.host.test", "ns9.yeni.test"]
S["crt"]["ornekdanisma.test"].append("mail.ornekdanisma.test")
S["site"]["ornekdanisma.test"] = S["site"]["ornekdanisma.test"].replace("Danışmanlık hizmetleri", "Yapay zekâ danışmanlığı ve eğitim")
S["news"].append((f"{OZEL_AD} yeni ortaklık açıkladı", "ortak firma ile anlaşma", BUG))
S["abr_durum"] = "Cancelled from 01 Nov 2026"
S["sitemap"][ORN] = S["sitemap"][ORN].replace("</urlset>", f"<url><loc>https://{ORN}/kariyer</loc></url></urlset>")
S["gh_repos"].append(("yeni-arac", "2026-11-01T00:00:00Z", "2026-11-05T00:00:00Z"))
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
kontrol("2. tarama: yeni sayfa (sitemap) Yeni", f"yeni sayfa izleniyor: https://{ORN}/kariyer" in r2, r2)
kontrol("2. tarama: yeni GitHub deposu Yeni", "yeni/güncellenen depo ornekorg/yeni-arac" in r2, r2)
kontrol("2. tarama: taban olmayan depo tekrar yazılmadı", "arac-bir" not in r2, r2)
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
kontrol("linkedin: sayaç kaydı", "log" in json.loads(oku("linkedin-sayac.json") or "{}").get("linkedin", {}))

# 5b) sosyal bütçe: X, keşfedilen hesap, ayrı sayaçlar, takma ad, göç
rc, c = run("sosyal-izin", "x", ORN_ID, "https://twitter.com/ornekfirma", TAZI_X_LIMIT="2"); kontrol("x: keşfedilen hesap (twitter.com → x.com) izinli", rc == 0 and "evet (1/2)" in c, c)
rc, c = run("sosyal-izin", "x", ORN_ID, "https://x.com/ornekfirma/status/12345?s=1", TAZI_X_LIMIT="2"); kontrol("x: /status/<no> izinli", rc == 0 and "evet (2/2)" in c, c)
rc, c = run("sosyal-izin", "x", ORN_ID, "https://x.com/ornekfirma", TAZI_X_LIMIT="2"); kontrol("x: sınır doldu", rc == 1 and "sınırı doldu" in c, c)
rc, c = run("sosyal-izin", "x", ORN_ID, "https://x.com/baskasi", TAZI_X_LIMIT="9"); kontrol("x: başka hesap reddi", rc == 1 and c.startswith("hayır"), c)
rc, c = run("sosyal-izin", "x", ORN_ID, "https://x.com/ornekfirma/followers", TAZI_X_LIMIT="9"); kontrol("x: yalnız profil kökü ve status", rc == 1, c)
rc, c = run("sosyal-izin", "x", KUZ_ID, "https://x.com/ornekfirma", TAZI_X_LIMIT="9"); kontrol("x: başka kaydın hesabı reddi", rc == 1, c)
rc, c = run("sosyal-izin", "linkedin", ORN_ID, "https://www.linkedin.com/company/ornek-danismanlik/about/", TAZI_LI_LIMIT="3"); kontrol("linkedin: keşfedilen şirket sayfasının alt sayfası; sayaç X'ten ayrı", rc == 0 and "evet (3/3)" in c, c)
sy = json.loads(oku("linkedin-sayac.json")); kontrol("sayaç: platform başına ayrı", sy["linkedin"]["n"] == 3 and sy["x"]["n"] == 2 and "hafta" in sy, str(sy))
hf = ILK.isocalendar(); open(os.path.join(T, "veri", "linkedin-sayac.json"), "w").write(json.dumps({"hafta": f"{hf[0]}-W{hf[1]:02d}", "n": 5, "log": []}))
rc, c = run("linkedin-izin", ORN_ID, url); kontrol("eski sayaç dosyası göçtü (linkedin-izin takma adı, varsayılan sınır 15)", rc == 0 and "evet (6/15)" in c, c)
kontrol("göçten sonra yeni biçim", "x" in json.loads(oku("linkedin-sayac.json")) and "n" not in json.loads(oku("linkedin-sayac.json")))
rc, c = run("durum"); kontrol("durum: iki sayaç", "LinkedIn bu hafta: 6/15" in c and "X bu hafta: 0/15" in c, c)


# 6) ekle doğrulaması
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "ozel", "--ozet", "x"); kontrol("ekle: ozel tür reddi", rc == 1, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "x", "--alinti", " ".join(["kelime"] * 16)); kontrol("ekle: 16 kelimelik alıntı reddi", rc == 1, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "LinkedIn: iş sürecine geçiş üzerine gönderi", "--kaynak", "https://www.linkedin.com/posts/x1",
            "--tarih", BUG.isoformat(), "--alinti", "kısa bir alıntı"); kontrol("ekle: gonderi kabul", rc == 0 and "eklendi" in c, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "LinkedIn: iş sürecine geçiş üzerine gönderi", "--kaynak", "https://www.linkedin.com/posts/x1"); kontrol("ekle: yinelenen", "zaten var" in c, c)
run("ekle", "--kim", "kuzgun", "--tur", "haber", "--ozet", "Kuzgun yeni bir sözleşme duyurdu", "--kaynak", "https://haber.test/k1", "--tarih", BUG.isoformat())
rc, c = run("ozet", "--kim", "Ayşe Deneme", TAZI_BUGUN=g(BUG)); kontrol("ozet: kişi adı", rc == 0 and "iş sürecine geçiş" in c and "[C]" in c and len(c.strip().splitlines()) <= 8, c)
rc, c = run("ozet", "--kim", EP, TAZI_BUGUN=g(BUG)); kontrol("ozet: e-posta alan adı", rc == 0 and "Kuzgun" in c and "sözleşme" in c and "Ayşe" not in c, c)
rc, c = run("ozet", "--kim", "yalicapkini.test", TAZI_BUGUN=g(BUG)); kontrol("ozet: alan adı", rc == 0 and "Yalıçapkını" in c, c)
rc, c = run("ozet", "--kim", "hiç yok bu", TAZI_BUGUN=g(BUG)); kontrol("ozet: eşleşme yok", rc == 1 and "eşleşme yok" in c, c)
rc, c = run("ozet", "--kim", "Ayşe Deneme", TAZI_BUGUN=g(BUG + datetime.timedelta(days=60))); kontrol("ozet: 45 gün sonra boş", "yeni bir şey yok" in c, c)
os.environ.update(TAZI_DIR=os.path.join(T, "veri"), SUFLOR_AYAR=ayar_yol, TAZI_BUGUN=g(BUG))
om = tazi.ozet_metni("Ayşe Deneme"); kontrol("ozet_metni içe aktarma", om and "Tazı · Örnek Danışmanlık" in om, str(om))
kontrol("ozet_metni eşleşmez → None", tazi.ozet_metni("zzzz yok") is None)
rc, c = run("durum"); kontrol("durum", rc == 0 and "son tarama" in c and "LinkedIn bu hafta" in c, c)


# 6b) liste: X sütunu ve herhangi hücredeki x.com/twitter.com adresi
XL = tazi.md_liste("| Kim | Web | X | Neden |\n|---|---|---|---|\n| Aaa Bbb Pty Ltd | aaabbb.test | https://twitter.com/AaaBbb | ayrıca https://x.com/aaa_ek ve https://x.com/intent/tweet |\n")
kontrol("liste: X sütunu + hücre taraması, intent atlanır, twitter → x", XL[0]["x"] == ["https://x.com/aaabbb", "https://x.com/aaa_ek"], str(XL))

# 6c) dosya
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "kimlik", "--metin", "İlk hüküm: kimlik doğrulanmadı."); kontrol("dosya: kimlik ekle", rc == 0 and "eklendi: #1" in c, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "kimlik", "--metin", "Son hüküm: site, sicil ve alan adı uyuşuyor.", "--derece", "B"); kontrol("dosya: ikinci kimlik", rc == 0, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "soru", "--metin", "Ortak firma kim?"); kontrol("dosya: soru", rc == 0, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "iz", "--metin", "Hibe veritabanında ara", "--kaynak", "https://hibe.test/x")
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "zaman", "--metin", "Danışmanlık işine başladığını duyurdu", "--tarih", "2024-05-06"); kontrol("dosya: zaman + tarih", rc == 0, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "bayrak", "--metin", "İki ayrı adres beyanı var", "--derece", "D")
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "iddia", "--metin", "Kendini kurucu olarak tanıtıyor", "--derece", "C")
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "kimlik", "--metin", "x" * 401); kontrol("dosya: 401 karakter reddi", rc == 1, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--bolum", "olmayan", "--metin", "x"); kontrol("dosya: geçersiz bölüm reddi", rc == 2, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme"); kontrol("dosya: yazdır, kimlik tek ve en son", rc == 0 and "Son hüküm" in c and "İlk hüküm" not in c and "#" in c and "Ortak firma kim?" in c, c)
dj = json.loads(oku("dosya", ORN_ID + ".json")); kontrol("dosya: kimlik tek öğe", sum(1 for o in dj["ogeler"] if o["bolum"] == "kimlik") == 1, str(dj))
no_soru = [o["no"] for o in dj["ogeler"] if o["bolum"] == "soru"][0]
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--kapat", str(no_soru), "--sonuc", "Ortak Parlak Cozum"); kontrol("dosya: kapat", rc == 0 and "kapandı" in c, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme", "--kapat", "999"); kontrol("dosya: olmayan öğe", rc == 1, c)
rc, c = run("dosya", "--kim", "Ayşe Deneme"); kontrol("dosya: kapanan öğe sonucuyla", "kapandı: Ortak Parlak Cozum" in c, c)
run("rapor", "--tarama", g(BUG), TAZI_BUGUN=g(BUG)); r2 = oku("rapor", f"tazi-{g(BUG)}.md")
kontrol("rapor: dosya kimlik hükmü, soru kapandı, açık iz kaldı", "Kimlik doğrulama: Son hüküm" in r2 and "Hibe veritabanında ara" in r2 and "Ortak firma kim?" not in r2.split("## Örnek Danışmanlık")[1].split("Açık sorular:")[1].split("Sıradaki izler:")[0], r2[-2500:])
kontrol("rapor: dosya zaman öğesi ve bayrak", "2024-05-06 — Danışmanlık işine" in r2 and "İki ayrı adres beyanı var" in r2 and "Kendini kurucu" in r2, r2)
rc, c = run("ozet", "--kim", "Ayşe Deneme", TAZI_BUGUN=g(BUG)); kontrol("ozet: ≤ 8 satır, kimlik hükmü, bayrak sayısı", rc == 0 and len(c.strip().splitlines()) <= 8 and "Kimlik: Son hüküm" in c and "Açık bayrak:" in c, c)
rc, c = run("ozet", "--kim", KUZ_ID, TAZI_BUGUN=g(BUG)); kontrol("ozet: bayrak satırı (otomatik)", "Açık bayrak:" in c and len(c.strip().splitlines()) <= 8, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--platform", "x", "--ozet", "X: etkinlik duyurusu", "--kaynak", "https://x.com/ornekfirma/status/777"); kontrol("ekle: platform x", rc == 0, c)
kontrol("ekle: platform kaydı", any(r["tur"] == "gonderi" and r.get("platform") == "x" for r in bulgular()) and any(r.get("platform") == "web" for r in bulgular() if r["tur"] == "gonderi"))
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "kod", "--ozet", "depo", "--kaynak", "https://gh.test/r"); kontrol("ekle: yeni tür kabul", rc == 0, c)
rc, c = run("ekle", "--kim", "Ayşe Deneme", "--tur", "gonderi", "--ozet", "z", "--platform", "tiktok"); kontrol("ekle: geçersiz platform", rc == 2, c)

# 6d) site takma adı ve sayfa sınırı
G3 = g(BUG + datetime.timedelta(days=3))
rc, c = run("tara", "--kim", "kuzgun", "--kaynak", "site", TAZI_BUGUN=G3, TAZI_SAYFA_MAX="1"); kontrol("site takma adı çalışır", rc == 0, c)
sn = json.loads(open(os.path.join(T, "veri", "tarama", G3, KUZ_ID + ".json"), encoding="utf-8").read())
kontrol("sayfa sınırı: alan adı başına ≤ 1", len(sn["site"]) <= 1 and sn["kaynaklar"] == ["tarama"], str(list(sn["site"])))
kontrol("v2 dosyaları kimliksiz: yerel kısımlar yazılmadı", not [f for d_, _, fs in os.walk(os.path.join(T, "veri")) for f in fs
        if any(x in open(os.path.join(d_, f), errors="ignore").read() for x in (YEREL, DMYEREL))])

# 6e) Suflor aday listesi (aday.json) ve hızlı tarama (--hizli)
AD_ALAN = "adayfirma.test"; AD_ID = "yeni-aday-firma"
S["ns"][AD_ALAN] = ["ns1.host.test"]; S["crt"][AD_ALAN] = []; S["site"][AD_ALAN] = f"<html><title>Ana {AD_ALAN}</title><body><h1>Merhaba</h1><a href=\"/hakkimizda\"></a></body></html>"
S["sitemap"][AD_ALAN] = f"<urlset><url><loc>https://{AD_ALAN}/hakkimizda</loc></url></urlset>"; S["sayfa"][(AD_ALAN, "/hakkimizda")] = "<html><title>H</title><body>biz</body></html>"
DIG[AD_ALAN] = {"NS": ["ns1.host.test."], "MX": ["10 mx1.host.test."], "A": ["192.0.2.10"], "TXT": []}; dig_yaz()
ana_once = open(liste_yol, "rb").read()
rc, c = run("aday", "--ad", "Yeni Aday Firma", "--alan", "https://www." + AD_ALAN + "/", "--neden", "brifing"); kontrol("aday: eklendi", rc == 0 and "aday eklendi" in c, c)
rc, c = run("aday", "--ad", "yeni aday firma", "--neden", "konus"); kontrol("aday: aynı ad tekrar eklenmez", rc == 0 and "zaten listede" in c, c)
rc, c = run("aday", "--ad", "Örnek Danışmanlık Pty Ltd"); kontrol("aday: ana listedeki ad eklenmez", "zaten listede" in c, c)
ay = json.loads(oku("aday.json")); kontrol("aday.json: tek kayıt, alan adı temiz, neden", len(ay) == 1 and ay[0]["alanlar"] == [AD_ALAN] and ay[0]["neden"] == "brifing" and ay[0]["ad"] == "Yeni Aday Firma", str(ay))
kontrol("aday: ana izleme listesine hiç yazılmadı", open(liste_yol, "rb").read() == ana_once)
tazi.os.environ["TAZI_DIR"] = os.path.join(T, "veri"); L2 = tazi.liste_oku(liste_yol)
kontrol("liste_oku: ana liste + aday birleşik, aday kaynak işaretli", len(L2) == 4 and L2[-1]["kaynak"] == "suflor-aday" and L2[-1]["id"] == AD_ID and "kaynak" not in L2[0], str(L2[-1]))
rc, c = run("durum"); kontrol("durum: aday sayısı", "Suflor aday listesi: 1 kayıt" in c, c)
LI_AD = "https://www.linkedin.com/in/yeniadayfirma/"
rc, c = run("sosyal-izin", "linkedin", AD_ID, LI_AD); kontrol("aday: profil adresi yokken sosyal-izin hayır", c.strip().startswith("hayır"), c)
rc, c = run("aday", "--ad", "Yeni Aday Firma", "--linkedin", LI_AD, "--linkedin", "https://ornek.test/degil"); kontrol("aday: var olan adaya LinkedIn adresi eklenir", rc == 0 and "sosyal adres eklendi" in c, c)
rc, c = run("aday", "--ad", "Yeni Aday Firma", "--linkedin", LI_AD); kontrol("aday: aynı adres ikinci kez eklenmez", "zaten listede" in c, c)
ay = json.loads(oku("aday.json")); kontrol("aday.json: yalnız geçerli LinkedIn adresi", ay[0].get("linkedin") == [LI_AD], str(ay))
rc, c = run("sosyal-izin", "linkedin", AD_ID, LI_AD + "recent-activity/all/"); kontrol("aday: eklenen profil ve alt sayfası sosyal-izin evet", c.strip().startswith("evet"), c)
rc, c = run("aday", "--ad", "Örnek Danışmanlık Pty Ltd", "--linkedin", LI_AD); kontrol("aday: ana listedeki kayda adres yazılmaz", "zaten listede" in c and open(liste_yol, "rb").read() == ana_once, c)
AT = chr(64); EP = "Kisi.Ornek" + AT + "Ornek.test"
rc, c = run("aday", "--ad", "Yeni Aday Firma", "--eposta", EP, "--eposta", "gecersiz-adres"); kontrol("aday: e-posta izi eklenir", "sosyal adres eklendi" in c, c)
ay_ = oku("aday.json"); kontrol("aday.json: e-posta adresi yazılmaz, yalnız iz", "kisi.ornek" not in ay_.lower() and len(json.loads(ay_)[0].get("eposta_iz", [])) == 1, ay_)
L3 = tazi.liste_oku(liste_yol)
kontrol("metinden_kayitlar: takvimdeki e-posta adresiyle aday dosyası bulunur", [k["id"] for k in tazi.metinden_kayitlar("katılımcılar: kisi.ornek" + AT + "ornek.test, baska" + AT + "x.test", L3)] == [AD_ID])
kontrol("metinden_kayitlar: başka adres eşleşmez", tazi.metinden_kayitlar("baska.kisi" + AT + "ornek.test", L3) == [])
S["istek"].clear(); n_once = len(bulgular()); G4 = g(BUG + datetime.timedelta(days=4)); t0 = time.time()
rc, c = run("tara", "--kim", "Yeni Aday Firma", "--hizli", TAZI_BUGUN=G4, TAZI_BEKLE="5"); sure = time.time() - t0
kontrol("hızlı tarama: çıkış 0, TAZI_BEKLE yok sayıldı (0,3 sn)", rc == 0 and sure < 12, f"{sure:.1f} {c}")
snp = json.loads(open(os.path.join(T, "veri", "tarama", G4, AD_ID + ".json"), encoding="utf-8").read())
kontrol("hızlı tarama: yalnız hızlı kaynaklar", snp["kaynaklar"] == ["rdap", "dns", "tarama", "haber"], str(snp["kaynaklar"]))
kontrol("hızlı tarama: Wayback, crt.sh, sitemap, ikinci sayfa, GitHub'a istek yok", not [x for x in S["istek"] if x.startswith(("/wb", "/crt", "/gh")) or "sitemap" in x or "hakkimizda" in x], str(S["istek"]))
kontrol("hızlı tarama: yalnız ana sayfa", list(snp["site"]) == [f"https://{AD_ALAN}/"], str(list(snp["site"])))
kontrol("hızlı tarama: alan adı kaydı ve DNS olgusu geldi", any(r["kayit"] == AD_ID and r["tur"] == "alan_adi" for r in bulgular()) and any(r["kayit"] == AD_ID and r["tur"] == "dns" for r in bulgular()))
rc, c = run("ozet", "--kim", "Yeni Aday Firma", TAZI_BUGUN=G4); kontrol("ozet: başlıkta (aday)", rc == 0 and c.splitlines()[0].startswith("Tazı · Yeni Aday Firma (aday) — son tarama"), c)
rc, c = run("ozet", "--kim", "Yeni Aday Firma", TAZI_BUGUN=g(BUG + datetime.timedelta(days=20))); kontrol("ozet: bayat dosyada 'N gün önce'", "gün önce" in c.splitlines()[0], c)
S["istek"].clear(); rc, c = run("tara", "--kim", "Yeni Aday Firma", TAZI_BUGUN=g(BUG + datetime.timedelta(days=5)))
kontrol("tam tarama eskisi gibi: Wayback ve sitemap istendi", rc == 0 and any(x.startswith("/wb") for x in S["istek"]) and any("sitemap" in x for x in S["istek"]), str(S["istek"]))

# 7) ABR kayıt kimliği yalnız Anahtar Zinciri komutundan; dosyalara ve çıktıya yazılmaz
gk = os.path.join(T, "sec.py"); open(gk, "w").write(f'print("{GUID}")\n')
rc, c = run("tara", "--kim", "kuzgun", "--kaynak", "sicil", TAZI_SECURITY_CMD=f"{sys.executable} {gk}", TAZI_BUGUN=g(BUG + datetime.timedelta(days=2)))
kontrol("ABR JSON yolu kimlikle çağrıldı", S["abr_guid_gorulen"] == [GUID], str(S["abr_guid_gorulen"]))
kontrol("ABR JSON: acn okundu", any(r["alt"] == "abn:acn" and r["deger"] == "123456789" for r in bulgular()))
sizdi = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(T, "veri")) for f in fs if GUID in open(os.path.join(d, f), errors="ignore").read()]
kontrol("kimlik hiçbir dosyada yok", not sizdi and GUID not in c, str(sizdi))
kontrol("keychain yokken yedek yol (herkese açık sayfa) kullanıldı", any(r["alt"] == "abn:entity_name" for r in bulgular()))


# 8) indeks (tazi.db), sorgu günlüğü, geçmiş, iletişim, proje veritabanı bağlantısı
import sqlite3, hashlib
def tdb(q, *p):
    con = sqlite3.connect(os.path.join(T, "veri", "tazi.db"))
    try: return con.execute(q, p).fetchall()
    finally: con.close()
rc, c = run("indeksle"); kontrol("indeksle çıkış 0", rc == 0 and "tazi.db:" in c, c)
sy1 = {t: tdb(f"SELECT count(*) FROM {t}")[0][0] for t in ("kayit", "bulgu", "dosya_oge", "rapor", "sorgu", "iletisim")}
rc, c = run("indeksle"); sy2 = {t: tdb(f"SELECT count(*) FROM {t}")[0][0] for t in sy1}
kontrol("indeksle idempotent", sy1 == sy2, f"{sy1} {sy2}")
kontrol("indeks: bulgu sayısı dosyayla aynı", sy1["bulgu"] == len(bulgular()) and sy1["bulgu"] > 0, str(sy1))
kontrol("indeks: kayıt var, aday kaynaklı işaretli", sy1["kayit"] >= 4 and tdb("SELECT kaynak FROM kayit WHERE id=?", AD_ID)[0][0] == "aday", str(sy1))
kontrol("indeks: user_version", tdb("PRAGMA user_version")[0][0] == 1)
kontrol("indeks: dosya_oge satırları", sy1["dosya_oge"] == sum(len(json.loads(oku("dosya", f))["ogeler"]) for f in os.listdir(os.path.join(T, "veri", "dosya"))), str(sy1))
rc, c = run("rapor", TAZI_BUGUN=g(BUG)); rapor_yol = c.strip().splitlines()[-1] if rc == 0 else ""
kontrol("rapor sonrası otomatik indeks: rapor tablosu ve DIZIN.md", tdb("SELECT count(*) FROM rapor")[0][0] >= 1 and "Raporlar" in oku("rapor", "DIZIN.md"), c)
rc, c = run("sorgu", "--istek", "Yeni Aday Firma kim, dürüst mü", "--kim", AD_ID + ",bilinmeyen-kayit", "--rapor", rapor_yol, "--yapan", "elle", "--tarih", "2026-11-10")
kontrol("sorgu: eklendi, bilinmeyen kayıt uyarısı", rc == 0 and "sorgu kaydedildi" in c and "uyarı" in c, c)
sj = [json.loads(l) for l in oku("sorgular.jsonl").splitlines()]
kontrol("sorgular.jsonl: alanlar", len(sj) == 1 and sj[0]["kayitlar"][0] == AD_ID and sj[0]["zaman"].startswith("2026-11-10") and sj[0]["rapor"].startswith("rapor/"), str(sj))
kontrol("sorgu tabloya ve DIZIN.md'ye girdi", tdb("SELECT count(*) FROM sorgu")[0][0] == 1 and "Yeni Aday Firma kim" in oku("rapor", "DIZIN.md"))
rc, c = run("sorgu", "--liste"); kontrol("sorgu --liste", "Yeni Aday Firma kim" in c, c)
rc, c = run("gecmis", "Yeni Aday Firma"); kontrol("gecmis: ad ile kayıt, sorgu ve rapor görünür", "● Yeni Aday Firma" in c and "Sorgu 2026-11-10" in c and len(c.splitlines()) <= 30, c)
EP2 = "Kisi.Ornek" + AT + "Ornek.test"
rc, c = run("gecmis", EP2); kontrol("gecmis: e-posta izi eşleşir, adres yazdırılmaz", "● Yeni Aday Firma" in c and "kisi.ornek" not in c.lower(), c)
rc, c = run("gecmis", "yok-boyle-biri-xyz"); kontrol("gecmis: eşleşme yok", "geçmiş çalışma yok" in c, c)
rc, c = run("ara", "Wayback"); rc2, c2 = run("ara", AD_ALAN)
kontrol("ara (FTS): bulgu ya da kayıt bulur", rc == 0 and rc2 == 0 and "eşleşme yok" not in c2, c + c2)
kontrol("FTS tablosu kuruldu", tdb("SELECT v FROM meta WHERE k='fts'")[0][0] in ("0", "1"))
rc, c = run("durum"); kontrol("durum: indeks satırı", "indeks:" in c and "tazi.db" in c and "son indeksleme" in c, c)

# iletişim bilgisi
TEL = "+61 400 111 222"; EP3 = "yeni.adres" + AT + "ornek.test"
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "eposta", "--deger", EP3, "--kaynak", "e-posta imzası", "--derece", "B"); kontrol("iletisim: eposta eklendi", rc == 0 and "eklendi" in c, c)
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "eposta", "--deger", EP3.upper(), "--kaynak", "başka"); kontrol("iletisim: aynı değer (büyük harf) tekrarlanmaz", "zaten kayıtlı" in c, c)
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "telefon", "--deger", TEL, "--kaynak", "https://ornek.test/iletisim"); rc2, c2 = run("iletisim", "--kim", AD_ID, "--tur", "telefon", "--deger", "+61400111222", "--kaynak", "x")
kontrol("iletisim: telefon eklenir, biçim farkı tekrar sayılır", rc == 0 and "zaten kayıtlı" in c2, c + c2)
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "ev_adresi", "--deger", "1 Sokak", "--kaynak", "x"); kontrol("iletisim: listede olmayan tür reddedilir", rc == 1 and "ev adresi" in c, c)
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "eposta", "--deger", "gecersiz", "--kaynak", "x"); kontrol("iletisim: geçersiz e-posta reddedilir", rc == 1, c)
rc, c = run("iletisim", "--kim", AD_ID, "--tur", "web", "--deger", "https://ornek.test/"); kontrol("iletisim: kaynaksız reddedilir", rc == 1, c)
rc, c = run("iletisim", "--kim", AD_ID); kontrol("iletisim: liste", EP3 in c and TEL in c and "e-posta imzası" in c, c)
kontrol("iletisim.jsonl dosyada, eposta_iz eşleşmesi çalışır", len(oku("iletisim.jsonl").splitlines()) == 2
        and tazi.eposta_iz(EP3) in [i for k in tazi.liste_oku(liste_yol, os.path.join(T, "veri")) if k["id"] == AD_ID for i in k.get("eposta_iz", [])])
kontrol("iletisim tabloda ve FTS'te", tdb("SELECT count(*) FROM iletisim")[0][0] == 2 and run("ara", "400")[1].count("iletisim") >= 1)
rc, c = run("gecmis", "Yeni Aday Firma"); kontrol("gecmis: iletişim görünür", "İletişim:" in c and TEL in c, c)
rc, c = run("gecmis", EP3); kontrol("gecmis: sorulan adres geri yazdırılmaz", "● Yeni Aday Firma" in c and EP3 not in c and TEL in c, c)
rc, c = run("dosya", "--kim", AD_ID); kontrol("dosya: iletişim bölümü", "[iletisim]" in c and TEL in c, c)

# proje veritabanı bağlantısı (salt okunur)
vtd = os.path.join(T, "proje-deneme.db"); con = sqlite3.connect(vtd)
con.executescript("CREATE TABLE kisi(id TEXT PRIMARY KEY, ad TEXT); CREATE TABLE kisi_takma(kisi_id TEXT, ad TEXT); CREATE TABLE hesap(adres TEXT PRIMARY KEY, kisi_id TEXT, alan_adi TEXT);"
                  "CREATE TABLE dis_firma(alan_adi TEXT PRIMARY KEY, ad TEXT);")
con.execute("INSERT INTO kisi VALUES('kp1','Baska Ad'),('kp2','Kuzgun Süreç')"); con.execute("INSERT INTO kisi_takma VALUES('kp2','Kuzgun Süreç')")
con.execute("INSERT INTO hesap VALUES(?,?,?)", (EP2.lower(), "kp1", "ornek.test")); con.execute("INSERT INTO dis_firma VALUES(?,?)", (ORN, "Örnek"))
con.commit(); con.close()
h0 = hashlib.sha256(open(vtd, "rb").read()).hexdigest(); m0 = os.path.getmtime(vtd)
rc, c = run("indeksle", "--baglanti", "--vt", vtd)
kontrol("bağlantı: e-posta izi → kisi_id", f"[{AD_ID}] -> kişi: kp1" in c, c)
kontrol("bağlantı: kisi_takma adı → kisi_id", "-> kişi: kp2" in c, c)
kontrol("bağlantı: dis_firma alanı → firma alanı", f"firma alanı: {ORN}" in c, c)
kontrol("bağlantı: iletişim önerisi (yalnız veritabanında olmayan)", f"öneri: Yeni Aday Firma için eposta {EP3}" in c and "için eposta " + EP2 not in c, c)
kontrol("bağlantı: telefon sütunu yoksa telefon önerilmez", "için telefon" not in c, c)
kontrol("tabloda vt sütunları", tdb("SELECT vt_kisi_id FROM kayit WHERE id=?", AD_ID)[0][0] == "kp1")
kontrol("proje veritabanı değişmedi", hashlib.sha256(open(vtd, "rb").read()).hexdigest() == h0 and os.path.getmtime(vtd) == m0 and not [f for f in os.listdir(T) if f.startswith("proje-deneme.db-")])
rc, c = run("indeksle", "--baglanti", "--vt", os.path.join(T, "yok.db")); kontrol("bağlantı: veritabanı açılamazsa bağlantı yok, hata yok", rc == 0 and "bağlı: 0/" in c, c)
kontrol("yazan komutlar indeksi sessiz tazeler", "tazi.db" not in run("aday", "--ad", "Ek Aday Kisi")[1] and tdb("SELECT count(*) FROM kayit WHERE id='ek-aday-kisi'")[0][0] == 1)

kod = open(TAZI).read()
kontrol("kaynakta kimlik değeri yok", GUID not in kod)
shutil.rmtree(T, ignore_errors=True)
if hatalar:
    print("HATA:\n- " + "\n- ".join(hatalar)); print(f"BAŞARISIZ {sayi[0] - len(hatalar)}/{sayi[0]}"); sys.exit(1)
print(f"TAMAM {sayi[0]}/{sayi[0]}")
