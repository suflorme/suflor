#!/usr/bin/env python3
# Kaynak bekçisi (aktarici/kaynak.py; mimari plan C / K4): düzey geçişleri ve titreşim payı (sahte ölçümle, ~0 sn), dar düzeyde ertelenenler
# (konus_on_ac, konus_iki_surec, dizin turu, Pocket boşta kapanma), PID ile süreç kapatma ve yalıtılmış aktarıcıda /status kaynak (~4 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kaynak.py      (kaldı → çıkış 1)
import ast, json, os, shutil, signal, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
LOG = []
ns = {"os": os, "time": time, "json": json, "AYAR": {}, "print": lambda *a, **k: LOG.append(" ".join(map(str, a))), "sistem_anlik": lambda: {}}
exec(compile(open(os.path.join(KOD, "aktarici", "kaynak.py"), encoding="utf-8").read(), "kaynak.py", "exec"), ns)
ES = ns["_kaynak_esikler"](); cek = os.cpu_count() or 4
def olc(bos=60, takas=0.0, yuk=1.0): return {"bos_yuzde": bos, "takas_gb": takas, "yuk": yuk}
def isle(o, n=1):
    for _ in range(n): ns["kaynak_isle"](o, ES)
    return ns["KAYNAK"]["duzey"]
ok("başlangıç normal; kaynak_dar() yanlış", ns["KAYNAK"]["duzey"] == "normal" and not ns["kaynak_dar"]())
ok("ham düzey: eşiklere göre", ns["kaynak_ham"](olc(60), ES) == "normal" and ns["kaynak_ham"](olc(20), ES) == "dar" and ns["kaynak_ham"](olc(35, 4.2), ES) == "dar"
   and ns["kaynak_ham"](olc(60, 0, cek * 1.6), ES) == "dar" and ns["kaynak_ham"](olc(10), ES) == "kritik" and ns["kaynak_ham"](olc(35, 7), ES) == "kritik" and ns["kaynak_ham"](olc(60, 0, cek * 3.5), ES) == "kritik")
ok("takas boş bellek bolken sayılmaz (30 Ekim: boş %84, takas 3,7 GB dar'da takılmıştı)", ns["kaynak_ham"](olc(84, 3.7), ES) == "normal" and ns["kaynak_ham"](olc(60, 7), ES) == "normal" and ns["kaynak_ham"](olc(42, 11.9), ES) == "normal")
ok("tek bozuk ölçüm düzeyi değiştirmez (titreşim yok)", isle(olc(20)) == "normal" and isle(olc(20)) == "normal" and isle(olc(60)) == "normal")
ok("3 ardışık dar ölçüm → dar; günlükte geçiş satırı", isle(olc(20), 3) == "dar" and ns["kaynak_dar"]() and any(l.startswith("KAYNAK: normal → dar (boş %20") for l in LOG))
ok("eşiğin hemen üstü (çıkış payı içinde) düzeyi düşürmez", isle(olc(24), 10) == "dar")
ok("5 iyi ölçüm yetmez, 6'ncı düşürür", isle(olc(60), 5) == "dar" and isle(olc(60)) == "normal")
isle(olc(8), 3); ok("kritik: 3 ardışık", ns["KAYNAK"]["duzey"] == "kritik" and ns["kaynak_dar"]())
ok("kritikten tek iyi ölçüm düşürmez; 6 iyi ölçüm normal olur", isle(olc(60)) == "kritik" and isle(olc(60), 5) == "normal")
ns["AYAR"]["kaynak_bekci"] = False; isle(olc(5), 3); ok("ayar kaynak_bekci: false → kaynak_dar() hep yanlış", not ns["kaynak_dar"]()); ns["AYAR"].pop("kaynak_bekci")
ns["KAYNAK"]["duzey"] = "normal"
ns["AYAR"]["kaynak_dar_bos"] = 40; ok("eşikler ayardan değişir", ns["_kaynak_esikler"]()["dar"]["bos"] == 40); ns["AYAR"].pop("kaynak_dar_bos")
v = ns["kaynak_view"](); ok("kaynak_view alanları", set(v) == {"duzey", "bos_yuzde", "takas_gb", "yuk", "t"})
# --- dar düzeyde ertelenenler (kaynak kodundaki gerçek işlevler, sahte süreçlerle) ---
src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
agac = ast.parse(src)
sec = [d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == "konus_on_ac"]
dar = {"v": True}; ac = []
ns2 = {"AYAR": {"konus_on_ac": True}, "kaynak_dar": lambda: dar["v"], "konus_canli": lambda: False, "_KS": {"tur": None}, "konus_beyin_var": lambda: True, "BRIFING_APP": KOD, "os": os,
       "time": time, "konus_ac": lambda *a, **k: ac.append(1) or True, "print": lambda *a, **k: None, "threading": threading, "subprocess": subprocess, "KONUS": {"durum": "kapali"}}
exec(compile(ast.Module(sec, []), "bas-konus.py", "exec"), ns2)
r = ns2["konus_on_ac"]("deneme"); ok("dar: Konuş önceden açılmaz", r is False and not ac)
dar["v"] = False; ok("normal: önceden açma çalışır (denetim yalnız dar'a bağlı)", ns2["konus_on_ac"]("deneme") is True and len(ac) == 1)
ok("kod: konus_iki_surec dar'da kapalı", 'AYAR.get("konus_iki_surec") is True and not kaynak_dar()' in src)
ok("kod: dizin turu (_onara_guncelle) ve veritabanı yardımcısı (vt_izle_bak) dar'da ertelenir", "if kaynak_dar(): time.sleep(60); continue" in src and "or kaynak_dar(): return False" in src)
pk = open(os.path.join(KOD, "aktarici", "pocket-ses.py"), encoding="utf-8").read()
ok("kod: Pocket boşta kapanma dar'da 60 sn'ye iner, Whisper/Konuş tek süreci/toplantı oturumuna dokunulmaz", "bos = min(bos, 60)" in pk and "kaynak_dar" not in open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
   and "kaynak_dar" not in open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read())
# --- PID ile kapatma: yalnız bu kullanıcının, yalnız eşleşen süreç ---
iz = "suflor-kaynak-deneme-" + str(os.getpid())
p1 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)", iz]); p2 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)", "baska"]); time.sleep(0.3)
n = ns["surec_kapat"](iz); time.sleep(0.2)
ok("surec_kapat yalnız eşleşen süreci kapatır (SIGTERM, PID ile)", n == 1 and p1.poll() is not None and p2.poll() is None); p2.kill(); p2.wait()
ok("eşleşen süreç yoksa 0", ns["surec_kapat"]("suflor-yok-" + iz) == 0)
# --- yalıtılmış aktarıcı: /status kaynak ---
T = tempfile.mkdtemp(prefix="suflor-kaynak-"); PORT = bos_port(8793); URL = f"http://127.0.0.1:{PORT}"
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
canli = os.path.join(T, "canli"); os.makedirs(canli); sahte = os.path.join(T, "olcum.json"); json.dump(olc(60), open(sahte, "w"))
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT,
                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1", SUFLOR_KAYNAK_OLCUM=sahte, SUFLOR_TEST_KOKEN="http://sahte.test"))
def istek(yol):
    q = urllib.request.Request(URL + yol, headers={"X-Suflor-Anahtar": open(os.path.join(canli, "kart-anahtari.txt"), encoding="utf-8").read().strip(), "Origin": "http://sahte.test"})
    return json.load(urllib.request.urlopen(q, timeout=5))
def duzey(): return (istek("/status").get("kaynak") or {}).get("duzey")
def bekle(d, sn=8):
    son = time.time() + sn
    while time.time() < son:
        try:
            if duzey() == d: return True
        except (urllib.error.URLError, OSError, KeyError): pass
        time.sleep(0.2)
    return False
try:
    ok("/status kaynak: normal", bekle("normal"))
    bekle("normal"); time.sleep(0.8); k = istek("/status")["kaynak"]; ok(f"alanlar dolu ({k})", k["bos_yuzde"] == 60 and k["takas_gb"] == 0 and k["t"])
    json.dump(olc(8, 7.0, 1.0), open(sahte, "w")); ok("sahte ölçüm kritik → /status kaynak.duzey kritik", bekle("kritik"))
    ok("günlükte geçiş satırı", "KAYNAK: normal → " in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
    html = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read(); dil = open(os.path.join(KOD, "pano", "dil.js"), encoding="utf-8").read()
    ok("pano kartı ve İngilizcesi var", 'kaynak.duzey==="kritik"' in html and "Mac is overloaded" in dil)
    json.dump(olc(60), open(sahte, "w")); ok("ölçüm düzelince (6 ardışık) normale döner", bekle("normal", 10))
finally:
    r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("\nKALDI: " + "; ".join(HATA) if HATA else "\nTAMAM"); sys.exit(1 if HATA else 0)
