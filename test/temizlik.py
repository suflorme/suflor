#!/usr/bin/env python3
# temizlik.py: sürüm yedeği ayıklama, alt klasörlere dokunmama, kuru koşu, --uygula (sahte çöp), tanınmayan ortak klasör, kutu arşivi, meşgul durumu.
# Hepsi geçici klasörde; gerçek _yedek, ortak klasör ya da çöp kutusu kullanılmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/temizlik.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-tz-")
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
def yaz(yol, icerik="x", gun=0):
    os.makedirs(os.path.dirname(yol), exist_ok=True); open(yol, "w").write(icerik)
    if gun: t = time.time() - gun * 86400; os.utime(yol, (t, t))
def kos(*arg, env=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_TEMIZLIK_MESGUL=""); e.update(env or {})
    r = subprocess.run([sys.executable, "-B", os.path.join(KOD, "temizlik.py")] + list(arg), capture_output=True, text=True, env=e, timeout=60)
    return r
try:
    yd, ort, cop, kod, ses = (os.path.join(T, x) for x in ("_yedek", "ortak", "cop", "kod", "ses"))
    for v in ("0.9.0", "0.10.0", "0.2.0", "0.11.1", "0.3.0", "0.4.0", "0.12.0"):  # sayısal sıralama: 0.10.0 > 0.9.0 (metin sırası yanlış olurdu)
        yaz(os.path.join(yd, f"relay-v{v}.py"))
    for v in ("1.0.0", "1.0.1"): yaz(os.path.join(yd, f"pano-v{v}.html"))
    yaz(os.path.join(yd, "relay-v0.12.0.bak"), "başka uzantı ayrı grup")
    yaz(os.path.join(yd, "BRIEF-devir-20261109-oturum-sonu.md")); yaz(os.path.join(yd, "relay-v0.5.0-oncesi.py")); yaz(os.path.join(yd, "not.txt"))
    for v in ("0.1.0", "0.1.1", "0.1.2", "0.1.3", "0.1.4", "0.1.5", "0.1.6"): yaz(os.path.join(yd, "test-araclari", f"alt-v{v}.py"))  # alt klasör: dokunulmaz
    yaz(os.path.join(kod, "pkg", "__pycache__", "a.pyc")); yaz(os.path.join(kod, ".git", "__pycache__", "g.pyc")); yaz(os.path.join(kod, "x.py"))
    yaz(os.path.join(ort, "whisper-modeller", "m.bin")); yaz(os.path.join(ort, "gizemli-klasor", "a.bin"), "y" * 100); yaz(os.path.join(ort, "piper-ses", "m.onnx"))
    yaz(os.path.join(ort, "geri-bildirim", "20260101-0000-eski-okundu-mrt.md"), "a"); yaz(os.path.join(ort, "geri-bildirim", "20260101-0001-eski-okunmamis-mrt.md"), "a")
    bugun = time.strftime("%Y%m%d"); yaz(os.path.join(ort, "geri-bildirim", f"{bugun}-0000-yeni-okundu-mrt.md"), "a")
    ayar = os.path.join(T, "ayar.json"); json.dump({"ortak": ort, "piper_model": os.path.join(ort, "piper-ses", "m.onnx")}, open(ayar, "w"))
    okunan = os.path.join(T, "okunan.json"); json.dump(["20260101-0000-eski-okundu-mrt.md", f"{bugun}-0000-yeni-okundu-mrt.md"], open(okunan, "w"))
    yaz(os.path.join(T, "uyg", "buyuk.log"), "z" * 2048); yaz(os.path.join(ses, "ses-arsivi", "t1", "a.wav"), "s" * 10, gun=5)
    ortak_arg = ["--yedek-dizin", yd, "--kod", kod, "--ortak", ort, "--cop", cop, "--uygulama-dizin", os.path.join(T, "uyg"), "--ses-kok", f"ses-arsivi={ses}/ses-arsivi", "--okunan", okunan, "--ayar", ayar, "--yedek-sakla", "3", "--gunluk-mb", "0"]
    def agac(k): return sorted(os.path.relpath(os.path.join(a, f), k) for a, _, fs in os.walk(k) for f in fs)
    once = agac(T)

    r = kos(*ortak_arg, "--json"); j = json.loads(r.stdout); K = {k["kalem"]: k for k in j["kalemler"]}
    kontrol("kuru koşu: çıkış 0, kip kuru-kosu", r.returncode == 0 and j["kip"] == "kuru-kosu")
    kontrol("kuru koşu hiçbir şeyi taşımadı/silmedi", agac(T) == once and not os.path.exists(cop))
    kontrol("yedek: relay.py grubundan 7-3=4, pano 0, (relay.bak tek) → 4 öğe", K["yedek"]["dosya"] == 4)
    kalan = {os.path.basename(y) for y in K["yedek"]["yapilacak"]}
    kontrol("yedek: sayısal sıra (0.10.0, 0.11.1, 0.12.0 kalır; 0.2.0/0.3.0/0.4.0/0.9.0 gider)", kalan == {"relay-v0.9.0.py", "relay-v0.2.0.py", "relay-v0.3.0.py", "relay-v0.4.0.py"})
    kontrol("pycache: .git hariç yalnız kod altındaki bir klasör", K["pycache"]["dosya"] == 1 and "pkg" in K["pycache"]["yapilacak"][0])
    kontrol("ortak: yalnız tanınmayan klasör raporlandı (whisper-modeller ve ayardaki piper-ses değil)", [x["ad"] for x in K["ortak"]["klasorler"]] == ["gizemli-klasor"])
    kontrol("kutu: yalnız eski VE okunmuş rapor adayı", [os.path.basename(y) for y in K["geri_bildirim"]["yapilacak"]] == ["20260101-0000-eski-okundu-mrt.md"])
    kontrol("günlük ve ses arşivi yalnız rapor (yapılacak boş)", K["gunluk"]["dosya"] == 1 and K["gunluk"]["yapilacak"] == [] and K["ses_arsivi"]["dosya"] == 1 and K["ses_arsivi"]["en_eski"])

    r = kos(*ortak_arg, "--uygula", "--json", env={"SUFLOR_TEMIZLIK_MESGUL": "toplantı sürüyor"}); j = json.loads(r.stdout)
    kontrol("meşgulken --uygula durur (çıkış 2), hiçbir şey taşınmaz", r.returncode == 2 and j["durdu"] and agac(T) == once)

    r = kos(*ortak_arg, "--uygula", "--json"); j = json.loads(r.stdout); K = {k["kalem"]: k for k in j["kalemler"]}
    kontrol("--uygula: çıkış 0, yedek 4 + pycache 1 taşındı", r.returncode == 0 and K["yedek"]["yapildi"] == 4 and K["pycache"]["yapildi"] == 1)
    cope = set(os.listdir(cop)) if os.path.isdir(cop) else set()
    kontrol("--uygula: sahte çöpe gitti (kalıcı silme yok)", {"relay-v0.9.0.py", "relay-v0.2.0.py", "relay-v0.3.0.py", "relay-v0.4.0.py", "__pycache__"} <= cope)
    kontrol("yedek: en yeniler yerinde, sürüm biçimsiz dosyalar ve diğer uzantılar yerinde", all(os.path.exists(os.path.join(yd, f)) for f in ("relay-v0.10.0.py", "relay-v0.11.1.py", "relay-v0.12.0.py", "relay-v0.12.0.bak", "relay-v0.5.0-oncesi.py", "not.txt", "BRIEF-devir-20261109-oturum-sonu.md", "pano-v1.0.0.html", "pano-v1.0.1.html")))
    kontrol("alt klasöre (test-araclari) dokunulmadı", len(os.listdir(os.path.join(yd, "test-araclari"))) == 7)
    kontrol(".git altındaki __pycache__ ve ortak klasör içeriği yerinde", os.path.exists(os.path.join(kod, ".git", "__pycache__", "g.pyc")) and os.path.exists(os.path.join(ort, "gizemli-klasor", "a.bin")) and os.path.exists(os.path.join(ort, "whisper-modeller", "m.bin")))
    kg = os.path.join(ort, "geri-bildirim")
    kontrol("kutu: eski okunmuş arsiv/'e taşındı; okunmamış ve yeni yerinde", os.path.exists(os.path.join(kg, "arsiv", "20260101-0000-eski-okundu-mrt.md")) and os.path.exists(os.path.join(kg, "20260101-0001-eski-okunmamis-mrt.md")) and os.path.exists(os.path.join(kg, f"{bugun}-0000-yeni-okundu-mrt.md")))
    kontrol("günlük ve ses arşivi dokunulmadı", os.path.exists(os.path.join(T, "uyg", "buyuk.log")) and os.path.exists(os.path.join(ses, "ses-arsivi", "t1", "a.wav")))
    # çöpte aynı ad varsa zaman damgalı ad
    yaz(os.path.join(yd, "relay-v0.01.0.py")); yaz(os.path.join(yd, "relay-v0.02.0.py"))
    shutil.rmtree(os.path.join(yd, "relay-v0.12.0.bak"), ignore_errors=True)
    yaz(os.path.join(yd, "pano-v0.0.1.html")); yaz(os.path.join(yd, "pano-v0.0.2.html"))  # pano-v0.0.1/2 en eski → çöpe (sakla=3: 1.0.1,1.0.0,0.0.2 kalır; 0.0.1 gider)
    yaz(os.path.join(cop, "pano-v0.0.1.html"), "eski çöp")
    r = kos(*ortak_arg, "--uygula"); 
    kontrol("çöpte aynı ad varsa ezilmez, zaman damgalı ad alır", r.returncode == 0 and open(os.path.join(cop, "pano-v0.0.1.html")).read() == "eski çöp" and any(f.startswith("pano-v0.0.1-") for f in os.listdir(cop)))
    r = kos(*ortak_arg); kontrol("metin çıktısı Türkçe başlık içerir", "kuru koşu" in r.stdout and "Sürüm yedekleri" in r.stdout)
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} geçti"); sys.exit(0 if all(ok) else 1)
