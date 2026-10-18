#!/usr/bin/env python3
# Sesin Gemini'ye devri (v0.80.0, S87): ton etiketi (<ton:…>) ayıklanır ve hiçbir yerde okunmaz; durum tonu kuralı (kötü haber, uyarı, acele) Gemini üslubuna
# eklenir; okuma kuyruğunda parça kendi sesi/üslubuyla; iki sesli özet (iki Gemini kişiliği); gerginlik puanı (döküm satırlarının ses düzeyi, söz kesme,
# sert söz) ve Konuş'a giden "[Toplantı havası]" bloğu yalnız gerginlik_tonu açık kişilikte ve toplantıda; kısa okuma (fısıltı/çeviri) Gemini'ye gider;
# toplantıda duyuru söz sırasını bekler, aralığa uyar. Aktarıcı yalıtılmış kopyadan modül olarak yüklenir; Gemini sahte sunucu, ses çalınmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-devir.py      (kaldı → çıkış 1; ~10 sn)
import base64, contextlib, http.server, importlib.util as u, io, json, os, shutil, sys, tempfile, threading, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT, GPORT = bos_port(8776), bos_port(0)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-sd-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
GELEN = []
class Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        GELEN.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        b = ("data: " + json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(b"\x01\x00" * 4800).decode()}}]}}]}) + "\r\n\r\n").encode()
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
s = http.server.ThreadingHTTPServer(("127.0.0.1", GPORT), Sahte); s.handle_error = lambda *a: None; threading.Thread(target=s.serve_forever, daemon=True).start()
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
kd = os.path.join(T, "kisilik"); os.makedirs(kd)
open(os.path.join(kd, "alfa.md"), "w").write("---\nad: ALFA\nses: gemini:Kore\nses_uslup: ölçülü ve sakin\n---\nToplantı kişiliği.\n")
open(os.path.join(kd, "beta.md"), "w").write("---\nad: BETA\nses: gemini:Charon\nses_uslup: nüktedan, dostça\ngerginlik_tonu: evet\n---\nToplantı dışı kişilik.\n")
json.dump({"alan": "Deneme", "ad": "Ali K", "port": PORT, "uygulama": T, "proje": T, "ortak": T, "kisilik": os.path.join(kd, "alfa.md"),
           "kisilik_toplanti_disi": os.path.join(kd, "beta.md"), "toplantiya_ses": True, "toplanti_duyuru": True}, open(os.path.join(T, "ayar.json"), "w"))
os.environ.update(SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_TS_AYGIT="1", SUFLOR_TEST_GEMINI_HOST=f"127.0.0.1:{GPORT}",
                  SUFLOR_TEST_GEMINI_ANAHTAR="deneme", SUFLOR_TEST_GEMINI_SESSIZ="1")
sys.argv = ["relay.py", "--dir", os.path.join(T, "canli"), "--port", str(PORT)]; os.chdir(T)
sp = u.spec_from_file_location("relay_t", os.path.join(T, "relay.py")); m = u.module_from_spec(sp)
with contextlib.redirect_stdout(io.StringIO()): sp.loader.exec_module(m)
def cikti(fn, *a, bekle=0.0, **k):
    o = io.StringIO()
    with contextlib.redirect_stdout(o):
        r = fn(*a, **k)
        if bekle: time.sleep(bekle)
    return r, o.getvalue()

# 1) ton etiketi
bak("ton etiketi ayıklanır", m.ton_ayikla("<ton:sakin> Anladım, bakıyorum.") == ("Anladım, bakıyorum.", "sakin"))
bak("bilinmeyen ton yok sayılır, etiket yine silinir", m.ton_ayikla("<ton:kizgin> Peki.") == ("Peki.", None))
bak("Mac sesinde, panoda ve toplantıya söylerken de silinir (etiket_sil)", m.etiket_sil("<ton:yumusak> Tamam <chuckle> olur.") == "Tamam olur.")
pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read()
bak("pano cevap gösteriminde ton etiketi gizli (iki yer)", pano.count("hmm|ton:\\s*[a-z_]+)>") == 2)
# 2) durum tonu kuralı
m.ton_sifirla()
bak("kural: kötü haber", m.ton_bul("Maalesef toplantı iptal edildi.") == "kotu_haber")
bak("kural: uyarı", m.ton_bul("Dikkat, burada bir risk var.") == "uyari")
bak("kural: olağan cümle tonsuz", m.ton_bul("Hemen bakıyorum, yarın görüşürüz.") is None)
m.ton_kur("sakin"); bak("Claude'un tonu kuralın önünde", m.ton_bul("Maalesef olmadı.") == "sakin")
m.ton_kur("normal"); bak("<ton:normal> kural tonunu da kapatır", m.ton_bul("Maalesef olmadı.") is None)
m.ton_sifirla()
k_m = m.kisilik("BETA"); u1 = m.ses_uslup_bul("Maalesef olmadı.", k_m)
bak(f"üslup = kişilik + durum: {u1!r}", u1.startswith("nüktedan, dostça") and "Kötü bir haber" in u1)
bak("tonsuz cümlede yalnız kişilik üslubu", m.ses_uslup_bul("Yarın görüşürüz.", k_m) == "nüktedan, dostça")
# 3) okuma kuyruğu: Konuş cevabının ilk cümlesindeki etiket sonraki cümlelere de geçer
m.ton_sifirla(); _, o = cikti(m.seslendir, "<ton:sakin> Anlıyorum.", kuyruk=True); _, o2 = cikti(m.seslendir, "Bir de şuna bakalım.", kuyruk=True)
bak("seslendir: etiket okunmaz, ton üsluba girer", "<ton" not in o and "Ortam gergin" in o)
bak("aynı cevabın sonraki cümlesi de o tonla", "Ortam gergin" in o2)
# 4) iki sesli özet
m.STATE["_cagri_son"] = 0; _, o = cikti(m.ozet_sesli, {"dosya": "x.md", "degerlendirme": "Toplantı verimliydi", "oneri": "Bütçeyi haftaya bağlayın"})
bak("iki sesli özet: ALFA (Kore) özeti, BETA (Charon) değerlendirmeyi okur", "iki sesle okunuyor (ALFA + BETA)" in o and "ses Kore" in o and "ses Charon" in o
    and o.index("Toplantı özeti hazır") < o.index("verimliydi"))
m.AYAR["ozet_iki_ses"] = False; _, o = cikti(m.ozet_sesli, {"dosya": "y.md", "degerlendirme": "İyi geçti"})
bak("ayar kapalıyken tek ses", "iki sesle" not in o and "SES: özet okunuyor" in o); m.AYAR.pop("ozet_iki_ses")
# 5) gerginlik puanı
def satir(i, kim, t0, db, metin, sure=2.0, kanal="karsi"):
    return {"id": f"w-{kanal}-{int(t0 * 1000)}", "speaker": kim, "text": metin, "ses": {"db": db, "sure": sure, "f0": 120, "hiz": 150}}
n = time.time() - 100; olagan = [satir(i, "Ayşe", n - 400 + i * 10, -25, "Olağan bir konuşma.") for i in range(6)] + [satir(i, "Can", n - 300 + i * 10, -24, "Peki.", kanal="ben") for i in range(6)]
sakin = m.gerginlik_hesap(olagan + [satir(0, "Ayşe", n, -25, "Bence plan uygun."), satir(0, "Can", n + 5, -24, "Katılıyorum.", kanal="ben")])
gergin = m.gerginlik_hesap(olagan + [satir(0, "Ayşe", n, -14, "Bu kabul etmiyorum, saçma!", sure=5), satir(0, "Can", n + 2, -15, "Sözümü kesme!", kanal="ben"),
                                     satir(0, "Ayşe", n + 3, -13, "Yeter artık!", sure=4)])
bak(f"sakin döküm: {sakin['duzey']} ({sakin['puan']})", sakin["duzey"] == "sakin")
bak(f"gergin döküm: {gergin['duzey']} ({gergin['puan']}) {gergin['sayim']}", gergin["duzey"] == "gergin" and gergin["sayim"]["kesme"] >= 1 and gergin["sayim"]["yuksek"] >= 2)
bak("toplantı yokken blok yok", m.gerginlik_notu("BETA") == "")
m.STATE["_cagri_son"] = time.time()
_, o = cikti(m.gerginlik_notu, "BETA"); blok = m.gerginlik_notu("BETA")
bak("toplantıda BETA'e blok (ton seçimi Claude'da)", "[Toplantı havası" in blok and "<ton:sakin>" in blok and "<ton:normal>" in blok)
bak("ALFA'e (gerginlik_tonu yok) blok yok", m.gerginlik_notu("ALFA") == "")
# 6) kısa okuma (fısıltı, sesli çeviri) Gemini'ye
n0 = len(GELEN); r, o = cikti(m.gemini_kisa, "DUR, söz sende.", ses="Kore", uslup="Kulağa fısıldar gibi")
g = GELEN[-1] if len(GELEN) > n0 else {}
bak("gemini_kisa: istek Gemini'ye, ses ve üslupla", r is True and '"voice_name": "Kore"' in json.dumps(g) and "Kulağa fısıldar" in json.dumps(g, ensure_ascii=False))
m.AYAR["ses_motoru"] = "mac"; bak("ses motoru Mac olsa da kişilik Gemini ise kısa okumalar Gemini", m.gemini_kullan() is True)
fis = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); cev = open(os.path.join(KOD, "aktarici", "ceviri.py"), encoding="utf-8").read()
bak("fısıltı ve sesli çeviri gemini_kisa'yı çağırır", "gemini_kisa(metin, ses=kv" in fis and "gemini_kisa(kisa, ses=AYAR.get(\"ceviri_gemini_ses\")" in cev)
# 7) toplantıda duyuru
m.STATE["meeting"] = "Deneme Toplantı"; m.kanal_sessizlik = lambda: 2.0; m.DUYURU["son"] = 0; m.SES["test_bit"] = 0  # önceki deneme okumaları "çalıyor" sayılmasın
r, o = cikti(m.toplanti_duyuru, "not", "Bütçe tablosu güncellenecek", bekle=1.0)
bak("duyuru söz sırası boşalınca toplantıya okunur", r is True and "DUYURU: not · Not aldım: Bütçe tablosu güncellenecek." in o and "TOPLANTIYA SÖYLE (deneme)" in o)
r, o = cikti(m.toplanti_duyuru, "not", "İkinci iş", bekle=0.3)
bak("60 sn dolmadan ikinci duyuru yok", r is False and "dolmadı" in o)
m.DUYURU["son"] = 0; m.kanal_sessizlik = lambda: 0.2; m.DUYURU_SIRA_SN = 1.0
r, o = cikti(m.toplanti_duyuru, "not", "Üçüncü iş", bekle=1.6)
bak("biri konuşuyorsa beklenir, sıra boşalmazsa okunmaz", "söz sırası boşalmadı" in o and "Not aldım: Üçüncü" not in o)
m.AYAR["toplanti_duyuru"] = False; bak("ayar kapalıyken duyuru yok", m.toplanti_duyuru("not", "X") is False)
shutil.rmtree(T, ignore_errors=True)
print("ses devri: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı")); sys.exit(1 if hata else 0)
