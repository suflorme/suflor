#!/usr/bin/env python3
# whisper-server sürüm denetimi ve Core ML ön ısıtma (6 Kasım, kurulum.py wcpp_sunucu_eski / whispercpp_kur güncelleme kolu / wcpp_isit).
# Gerçek indirme ve gerçek model YOK: sahte sürüm sayfası (yerel http, deneme anahtarıyla imzalı paket), sahte whisper-server (HTTP sunan Python betiği).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/cpp-surum.py   (~10 sn)
import hashlib, http.server, io, json, os, shutil, subprocess, sys, tarfile, tempfile, threading, time
sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__)); KOD = os.path.dirname(BURA)
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != BURA]
sys.path.insert(0, os.path.join(KOD, "test")); from bosport import bos_port; sys.path.pop(0)
ok = []
def kontrol(ad, k, ek=""): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad + ("" if k else f"  [{str(ek)[:400]}]"))
T = tempfile.mkdtemp(prefix="suflor-test-cppsurum-")
os.environ["SUFLOR_EV"] = os.path.join(T, "ev"); os.makedirs(os.environ["SUFLOR_EV"])
sys.path.insert(0, KOD); import kurulum
h = lambda b: hashlib.sha256(b).hexdigest()
SUNUCU_BETIK = "#!%s\n" % sys.executable + '''
import sys, http.server, threading
if "--help" in sys.argv: sys.exit(0)
if open(__file__).read().splitlines()[-1].startswith("#" + "{HATA}"): sys.exit(3)
port = int(sys.argv[sys.argv.index("--port") + 1])
class H(http.server.BaseHTTPRequestHandler):
    def log_message(s, *a): pass
    def do_GET(s): s.send_response(200); s.end_headers(); s.wfile.write(b"ok")
    def do_POST(s): s.rfile.read(int(s.headers.get("Content-Length") or 0)); s.send_response(200); s.end_headers(); s.wfile.write(b'{"text":""}')
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
'''
def sunucu_dosyasi(etiket, hata=False): return (SUNUCU_BETIK + f"#{'{HATA}' if hata else 'iyi'} {etiket}\n").encode()
try:
    ank = os.path.join(T, "anahtar"); ank2 = os.path.join(T, "anahtar2")
    for a in (ank, ank2): subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "suflor-yayin", "-f", a], check=True)
    os.environ["SUFLOR_TEST_IMZA_ACIK"] = open(ank + ".pub").read().split(" suflor")[0].strip()
    rnd = os.urandom; Q8_B, VAD_B = rnd(3000), rnd(500); KOD_D = {"weights/weight.bin": rnd(2000), "model.mil": b"mil", "coremldata.bin": b"cd", "metadata.json": b"{}", "analytics/coremldata.bin": b"an"}
    import zipfile
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w") as z:
        for k, v in KOD_D.items(): z.writestr("ggml-large-v3-turbo-encoder.mlmodelc/" + k, v)
    ZIP_B = zb.getvalue()
    kurulum.WCPP_PARCA = [("ggml-large-v3-turbo-q8_0.bin", "g/w", "r1", "ggml-large-v3-turbo-q8_0.bin", len(Q8_B), h(Q8_B), "dosya"),
                          ("ggml-large-v3-turbo-encoder.mlmodelc", "g/w", "r1", "enc.zip", len(ZIP_B), h(ZIP_B), "zip"), ("ggml-silero-v6.2.0.bin", "g/v", "r2", "v.bin", len(VAD_B), h(VAD_B), "dosya")]
    kurulum.WCPP_KODLAYICI = {k: len(v) for k, v in KOD_D.items()}
    SUN = {f"/{d}/resolve/{r}/{u}": {"ggml-large-v3-turbo-q8_0.bin": Q8_B, "enc.zip": ZIP_B}.get(u, VAD_B) for _, d, r, u, *_ in kurulum.WCPP_PARCA}; ISTEK = []
    def paket_yayinla(etiket, imza_anahtari=None):  # sürüm sayfasına imzalı paket koy
        pk = os.path.join(T, "pk-" + etiket); os.makedirs(pk, exist_ok=True); sv = os.path.join(pk, "whisper-server"); open(sv, "wb").write(sunucu_dosyasi(etiket)); os.chmod(sv, 0o755)
        pa = os.path.join(pk, kurulum.WCPP_PAKET)
        with tarfile.open(pa, "w:gz") as t: t.add(sv, "whisper-server")
        ls = pa + ".sha256"; open(ls, "w").write(f"# suflor-whisper-cpp {kurulum.WCPP_SURUM}\n{h(open(pa, 'rb').read())}  {kurulum.WCPP_PAKET}\n")
        if os.path.exists(ls + ".sig"): os.remove(ls + ".sig")
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", imza_anahtari or ank, "-n", "suflor-whisper-cpp", ls], check=True)
        for f in os.listdir(pk):
            if f != "whisper-server": SUN["/rel/" + f] = open(os.path.join(pk, f), "rb").read()
    class Sun(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            ISTEK.append(self.path); b = SUN.get(self.path)
            if b is None: self.send_response(404); self.end_headers(); return
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    SP = bos_port(8786); srv = http.server.ThreadingHTTPServer(("127.0.0.1", SP), Sun); threading.Thread(target=srv.serve_forever, daemon=True).start()
    kurulum.WCPP_HF = f"http://127.0.0.1:{SP}"; kurulum.WCPP_REL = f"http://127.0.0.1:{SP}/rel"
    kurulum.mesgul = lambda: ""  # toplantı yok
    def dosyalar(ort):
        d = os.path.join(ort, "whisper-cpp"); os.makedirs(os.path.join(d, "ggml-large-v3-turbo-encoder.mlmodelc"), exist_ok=True)
        for ad, *_r in kurulum.WCPP_PARCA[:1] + kurulum.WCPP_PARCA[2:]: open(os.path.join(d, ad), "wb").write(Q8_B if ad.startswith("ggml-large") else VAD_B)
        for k, v in KOD_D.items(): os.makedirs(os.path.dirname(os.path.join(d, "ggml-large-v3-turbo-encoder.mlmodelc", k)), exist_ok=True); open(os.path.join(d, "ggml-large-v3-turbo-encoder.mlmodelc", k), "wb").write(v)
        return d
    def sv_icerik(d): return open(os.path.join(d, "whisper-server"), "rb").read()

    # ---------- 1) sürüm denetimi ----------
    paket_yayinla("v-yeni")
    o1 = os.path.join(T, "ortak1"); d1 = dosyalar(o1)
    eski = os.path.join(d1, "whisper-server"); open(eski, "wb").write(sunucu_dosyasi("v-eski")); os.chmod(eski, 0o755)
    kontrol("eski sunucu çalışıyor, işareti yok → eksik değil ama sürümü eski", not kurulum.wcpp_eksik(o1) and kurulum.wcpp_sunucu_eski(o1) and kurulum.wcpp_guncelle_gerek(o1), kurulum.wcpp_eksik(o1))
    acik = open(eski, "rb"); ino = os.stat(eski).st_ino  # çalışan süreç gibi: eski dosyayı açık tutan tanıtıcı
    r = kurulum.whispercpp_kur(o1)
    kontrol("eski sunucu imzalı yeni paketle değişti (içerik yeni, 755, işaret yazıldı, geçici dosya yok)",
            r is True and b"v-yeni" in sv_icerik(d1) and os.stat(eski).st_mode & 0o777 == 0o755 and not kurulum.wcpp_sunucu_eski(o1) and not any(f.startswith(".sunucu") or ".indir" in f for f in os.listdir(d1))
            and kurulum.oku_json(os.path.join(d1, "whisper-server.surum")).get("surum") == kurulum.WCPP_SURUM, [r, os.listdir(d1)])
    kontrol("değişim atomik: açık tutan eski tanıtıcı eski içeriği okur, yol yeni dosyada (çalışan sunucu bozulmaz)", os.stat(eski).st_ino != ino and b"v-eski" in acik.read(), "")
    acik.close()
    kontrol("yalnız sunucu indi: model/kodlayıcı/VAD isteği yok", ISTEK and all(x.startswith("/rel/") for x in ISTEK), ISTEK)
    n = len(ISTEK); r = kurulum.whispercpp_kur(o1)
    kontrol("beklenen sürüm yerinde → yeniden inmez", r is True and len(ISTEK) == n, ISTEK[n:])
    open(eski, "ab").write(b"#kurcalandi")  # özet işaretle tutmaz
    kontrol("dosya özeti işaretle tutmuyorsa eski sayılır", kurulum.wcpp_sunucu_eski(o1), "")
    # sürüm etiketi başka
    paket_yayinla("v-yeni"); r = kurulum.whispercpp_kur(o1); kontrol("tutmayan özet yeniden indirilir ve düzelir", r is True and not kurulum.wcpp_sunucu_eski(o1) and b"kurcalandi" not in sv_icerik(d1), "")
    k0 = kurulum.WCPP_SURUM; kurulum.WCPP_SURUM = "9.9.9-x"
    kontrol("beklenen sürüm kodda artınca (tek yer WCPP_SURUM) yerleşik sunucu eski sayılır", kurulum.wcpp_sunucu_eski(o1), ""); kurulum.WCPP_SURUM = k0

    # ---------- 2) başarısız indirme eskiyi korur ----------
    o2 = os.path.join(T, "ortak2"); d2 = dosyalar(o2); e2 = os.path.join(d2, "whisper-server"); open(e2, "wb").write(sunucu_dosyasi("v-eski")); os.chmod(e2, 0o755); ESKI = sv_icerik(d2)
    yedek = {k: v for k, v in SUN.items() if k.startswith("/rel/")}
    pa = "/rel/" + kurulum.WCPP_PAKET; SUN[pa] = SUN[pa][:-1] + bytes([SUN[pa][-1] ^ 1])  # bozuk indirme
    r = kurulum.whispercpp_kur(o2)
    kontrol("bozuk indirme (özet tutmuyor): eski sunucu yerinde, kurulum başarılı sayılır, geçici dosya yok", r is True and sv_icerik(d2) == ESKI and not any(f.startswith(".sunucu") or ".indir" in f for f in os.listdir(d2)) and kurulum.wcpp_eksik(o2) == [], [r, os.listdir(d2)])
    kontrol("durum 'hazir' kalır (eski sunucu çalışıyor), deneme kaydı yazıldı ve 6 saat yeniden denenmez", kurulum.oku_json(kurulum._wcpp_kayit()).get("durum") == "hazir" and kurulum.oku_json(kurulum._wcpp_surum_deneme()).get("surum") == kurulum.WCPP_SURUM
            and kurulum.wcpp_sunucu_eski(o2) and not kurulum.wcpp_guncelle_gerek(o2), kurulum.oku_json(kurulum._wcpp_kayit()))
    n = len(ISTEK); r = kurulum.whispercpp_kur(o2); kontrol("beklerken yeniden indirme denenmez", r is True and len(ISTEK) == n and sv_icerik(d2) == ESKI, ISTEK[n:])
    SUN.update(yedek); os.remove(kurulum._wcpp_surum_deneme()); r = kurulum.whispercpp_kur(o2)
    kontrol("bekleme bitince (kayıt silindi) yeniden denenir ve yeni sürüm gelir", r is True and b"v-yeni" in sv_icerik(d2) and not kurulum.wcpp_sunucu_eski(o2), "")
    # başka anahtarla imza
    o3 = os.path.join(T, "ortak3"); d3 = dosyalar(o3); e3 = os.path.join(d3, "whisper-server"); open(e3, "wb").write(sunucu_dosyasi("v-eski")); os.chmod(e3, 0o755)
    paket_yayinla("v-yeni", ank2); r = kurulum.whispercpp_kur(o3)
    kontrol("başka anahtarla imzalı paket kurulmaz, eski yerinde", r is True and b"v-eski" in sv_icerik(d3) and kurulum.wcpp_sunucu_eski(o3), "")
    paket_yayinla("v-yeni")
    # açılmayan yeni sunucu
    o4 = os.path.join(T, "ortak4"); d4 = dosyalar(o4); e4 = os.path.join(d4, "whisper-server"); open(e4, "wb").write(sunucu_dosyasi("v-eski")); os.chmod(e4, 0o755)
    pk = os.path.join(T, "pk-bozuk"); os.makedirs(pk); sv = os.path.join(pk, "whisper-server"); open(sv, "w").write("#!/bin/sh\nexit 9\n"); os.chmod(sv, 0o755); pa = os.path.join(pk, kurulum.WCPP_PAKET)
    with tarfile.open(pa, "w:gz") as t: t.add(sv, "whisper-server")
    ls = pa + ".sha256"; open(ls, "w").write(f"# suflor-whisper-cpp {kurulum.WCPP_SURUM}\n{h(open(pa, 'rb').read())}  {kurulum.WCPP_PAKET}\n"); subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", ank, "-n", "suflor-whisper-cpp", ls], check=True)
    kurulum._SUNUCU_OK.clear()
    for f in os.listdir(pk):
        if f != "whisper-server": SUN["/rel/" + f] = open(os.path.join(pk, f), "rb").read()
    r = kurulum.whispercpp_kur(o4); kontrol("bu Mac'te açılmayan yeni sunucu değişmez (eski çalışmaya devam)", r is True and b"v-eski" in sv_icerik(d4), "")
    paket_yayinla("v-yeni")
    # yazılamayan klasör (öbür hesap): güncelleme denenmez
    o5 = os.path.join(T, "ortak5"); d5 = dosyalar(o5); e5 = os.path.join(d5, "whisper-server"); open(e5, "wb").write(sunucu_dosyasi("v-eski")); os.chmod(e5, 0o755); os.chmod(d5, 0o555)
    kontrol("klasör bu hesaba yazılamıyorsa güncelleme gerekmez (öbür hesabın işi, sessiz geçilir)", not kurulum.wcpp_guncelle_gerek(o5), ""); os.chmod(d5, 0o755)

    # ---------- 3) Core ML ön ısıtma ----------
    kurulum.WCPP_ISINMA_SN = 20
    n = len(ISTEK)
    s = kurulum.wcpp_isit(o1, sinir=20)
    kontrol("ön ısıtma: sunucu açıldı, sessizlik çözdürüldü, kapandı; işaret hazır + süre yazıldı", s == "hazir" and kurulum.oku_json(kurulum._wcpp_isinma_kayit()).get("sonuc") == "hazir"
            and isinstance(kurulum.oku_json(kurulum._wcpp_isinma_kayit()).get("sn"), (int, float)), [s, kurulum.oku_json(kurulum._wcpp_isinma_kayit())])
    kalan = subprocess.run(["pgrep", "-f", os.path.join(d1, "whisper-server")], capture_output=True, text=True).stdout.strip()
    kontrol("ön ısıtma sunucusu kapandı (süreç kalmadı)", kalan == "", kalan)
    kontrol("zaten ısınmışsa atlanır", kurulum.wcpp_isit(o1, sinir=20) == "atlandi" and not kurulum.wcpp_isinma_gerek(o1), "")
    kontrol("sunucu sürümü değişince yeniden ısıtılmaz (işaret kodlayıcıya bağlı)", (lambda: (open(os.path.join(d1, "whisper-server"), "ab").write(b"#x"), not kurulum.wcpp_isinma_gerek(o1))[1])(), "")
    w = os.path.join(d1, "ggml-large-v3-turbo-encoder.mlmodelc", "weights", "weight.bin"); os.utime(w, (time.time() - 5000, time.time() - 5000))  # yeniden indirilmiş kodlayıcı (boyut aynı, mtime farklı)
    kontrol("kodlayıcı değişince yeniden ısıtılır", kurulum.wcpp_isinma_gerek(o1), "")
    os.remove(kurulum._wcpp_isinma_kayit()); kurulum.mesgul = lambda: "web toplantısı sürüyor"
    s = kurulum.wcpp_isit(o1, sinir=20)
    kontrol("toplantı sürerken ısıtma yok (sunucu açılmaz, işaret yazılmaz)", s == "mesgul" and not os.path.exists(kurulum._wcpp_isinma_kayit()), s); kurulum.mesgul = lambda: ""
    # aktarıcı bu kodlayıcıyı zaten açtıysa (whisper-cpp-ilk.json) atla
    kurulum.yaz_json(os.path.join(kurulum.yollar()["uygulama"], "whisper-cpp-ilk.json"), {"parmak": "123:4|" + kurulum.wcpp_kodlayici_parmak(o1)})
    kontrol("aktarıcı kodlayıcıyı zaten açmışsa (ilk açılış kaydı) atlanır", not kurulum.wcpp_isinma_gerek(o1), ""); os.remove(os.path.join(kurulum.yollar()["uygulama"], "whisper-cpp-ilk.json"))
    # açılmayan sunucu: hata kaydı, kurulumu bozmaz, 6 saat yeniden denenmez
    d6 = dosyalar(os.path.join(T, "ortak6")); e6 = os.path.join(d6, "whisper-server"); open(e6, "wb").write(sunucu_dosyasi("v-bozuk", hata=True)); os.chmod(e6, 0o755)
    s = kurulum.wcpp_isit(os.path.join(T, "ortak6"), sinir=5); k = kurulum.oku_json(kurulum._wcpp_isinma_kayit())
    kontrol("açılmayan sunucuda ısıtma 'hata' yazar, sonra denenmez (ilk toplantıda aktarıcı yapar)", s == "hata" and k.get("sonuc") == "hata" and not kurulum.wcpp_isinma_gerek(os.path.join(T, "ortak6")), [s, k])
    kontrol("beta kurulum özeti: sonuc seçeneği + sn sayısı (başka alan yok)", kurulum._isinma_ozet() == {"sonuc": "hata", "sn": k["sn"]}, kurulum._isinma_ozet())
    kontrol("deneme kipinde (SUFLOR_EV) arka plan ısıtması başlamaz", kurulum.wcpp_isit_baslat() is None and kurulum.whispercpp_baslat() is None, "")
    srv.shutdown()
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} geçti"); sys.exit(0 if all(ok) else 1)
