#!/usr/bin/env python3
# v0.134.0 — kurulum.py: hesaba özel ortak klasör seçimi (_ortak_sec) ve tamamen kaldırma (sil, kaldir.command). Deneme ev klasöründe
# (SUFLOR_EV), sahte paylaşılan klasörle (SUFLOR_TEST_PAYLASILAN); gerçek ayara, /Users/Shared'a ve süreçlere dokunmaz (~2 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kaldir.py
import json, os, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
def ortam(ev, pay): return dict(os.environ, SUFLOR_EV=ev, SUFLOR_TEST_PAYLASILAN=pay, PYTHONDONTWRITEBYTECODE="1")
def ortak(ev, pay):
    r = subprocess.run([sys.executable, "-B", "-c", f"import sys; sys.argv=['k']; sys.path.insert(0, {KOD!r}); import kurulum; print(kurulum.ORTAK)"],
                       env=ortam(ev, pay), capture_output=True, text=True, timeout=60)
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
def sil(ev, pay, *ek):
    return subprocess.run([sys.executable, "-B", os.path.join(KOD, "kurulum.py"), "sil", "--evet", *ek], env=ortam(ev, pay), capture_output=True, text=True, timeout=60)

kok = tempfile.mkdtemp(prefix="kaldir-")
try:
    # 1) ortak klasör seçimi
    ev = os.path.join(kok, "ev1"); os.makedirs(ev); pay = os.path.join(kok, "paylasilan")
    ok("paylaşılan klasör yoksa: paylaşılan yol (ilk hesap orayı kurar)", ortak(ev, pay) == pay)
    os.makedirs(pay); ok("paylaşılan klasör bu hesabınsa (yazılabilir): paylaşılan yol", ortak(ev, pay) == pay)
    os.chmod(pay, 0o555)
    oz = os.path.join(ev, "Library", "Application Support", "Suflor-ortak")
    ok("paylaşılan klasör başka hesabınsa (yazılamaz): hesaba özel Suflor-ortak", ortak(ev, pay) == oz)
    d = os.path.join(ev, "Library", "Application Support", "Suflor"); os.makedirs(d)
    json.dump({"ortak": "~/elle-ortak"}, open(os.path.join(d, "ayar.json"), "w"))
    ok("ayarda yol varsa o korunur", ortak(ev, pay) == os.path.expanduser("~/elle-ortak"))
    os.chmod(pay, 0o755)

    # 2) tamamen kaldırma
    def kur_sahte(ev, ortak_yol):
        dest = os.path.join(ev, "Library", "Application Support", "Suflor"); os.makedirs(os.path.join(dest, "canli"), exist_ok=True)
        open(os.path.join(dest, "canli", "Toplanti.md"), "w").write("döküm")
        json.dump({"uygulama": dest, "proje": os.path.join(ev, "Suflor"), "ortak": ortak_yol}, open(os.path.join(dest, "ayar.json"), "w"))
        for y in ("Applications/Suflor.me.app/Contents", "Suflor/belgeler", "Library/Logs/suflor-ax"): os.makedirs(os.path.join(ev, y), exist_ok=True)
        for y in ("Library/LaunchAgents/local.suflor.aktarici.plist", "Library/Logs/suflor-aktarici.log", "Library/Logs/baska.log",
                  "Library/Application Support/Google/Chrome/NativeMessagingHosts/me.suflor.anahtar.json"):
            os.makedirs(os.path.dirname(os.path.join(ev, y)), exist_ok=True); open(os.path.join(ev, y), "w").write("x")
        os.makedirs(os.path.join(ortak_yol, "whisper-venv"), exist_ok=True)
    ev = os.path.join(kok, "ev2"); oy = os.path.join(ev, "Library", "Application Support", "Suflor-ortak"); kur_sahte(ev, oy)
    r = sil(ev, pay); cop = os.path.join(ev, ".Trash")
    ok("sil --evet çıkış 0", r.returncode == 0)
    ok("uygulama/ayar klasörü Çöp Sepeti'nde (döküm içinde)", os.path.exists(os.path.join(cop, "Suflor", "canli", "Toplanti.md"))
       and not os.path.exists(os.path.join(ev, "Library", "Application Support", "Suflor")))
    ok("Mac uygulaması, açılış ajanı, günlükler, yerel mesajlaşma tanımı taşındı",
       all(os.path.exists(os.path.join(cop, x)) for x in ("Suflor.me.app", "local.suflor.aktarici.plist", "suflor-aktarici.log", "suflor-ax", "me.suflor.anahtar.json")))
    ok("Suflor'a ait olmayan günlük yerinde", os.path.exists(os.path.join(ev, "Library", "Logs", "baska.log")))
    ok("bayraksız: modeller ve proje klasörü yerinde", os.path.isdir(oy) and os.path.isdir(os.path.join(ev, "Suflor", "belgeler")))
    ok("kod klasörüne dokunulmadı", os.path.isfile(os.path.join(KOD, "kurulum.py")))
    ok("çıktıda elle kalanlar (Chrome eklentisi)", "chrome://extensions" in r.stdout)

    ev = os.path.join(kok, "ev3"); oy = os.path.join(ev, "Library", "Application Support", "Suflor-ortak"); kur_sahte(ev, oy)
    r = sil(ev, pay, "--modeller", "--proje"); cop = os.path.join(ev, ".Trash")
    ok("--modeller --proje: ikisi de Çöp Sepeti'nde", os.path.isdir(os.path.join(cop, "Suflor-ortak", "whisper-venv")) and not os.path.exists(oy)
       and any(os.path.isdir(os.path.join(cop, f, "belgeler")) for f in os.listdir(cop)))

    # 3) güvenlik: ayardaki ortak ev klasörü dışındaysa (deneme) taşınmaz; başka hesabın klasörü yazılamıyorsa hiç listelenmez
    ev = os.path.join(kok, "ev4"); dis = os.path.join(kok, "dis-ortak"); kur_sahte(ev, dis)
    r = sil(ev, pay, "--modeller")
    ok("deneme: ev dışındaki klasör taşınmadı", os.path.isdir(os.path.join(dis, "whisper-venv")) and "taşınamadı" in r.stdout)
    ev = os.path.join(kok, "ev5"); kur_sahte(ev, pay); os.chmod(pay, 0o555)
    r = sil(ev, pay, "--modeller"); os.chmod(pay, 0o755)
    ok("başka hesabın paylaşılan klasörüne dokunulmaz", os.path.isdir(os.path.join(pay, "whisper-venv")) and "başka bir hesabın" in r.stdout)
    ev = os.path.join(kok, "ev6"); os.makedirs(ev); r = sil(ev, pay)
    ok("kurulu bir şey yoksa sorunsuz biter", r.returncode == 0 and "bulunmadı" in r.stdout)
finally:
    for k, _, _ in os.walk(kok): os.chmod(k, 0o755)
    shutil.rmtree(kok, ignore_errors=True)
print("kaldir: " + ("✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} hata: " + "; ".join(HATA))); sys.exit(1 if HATA else 0)
