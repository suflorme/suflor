#!/usr/bin/env python3
# Konuş'ta takılı süreç temizliği (2 Kasım; aktarici/bas-konus.py konus_yardimci_pidler/konus_yeni_pid/konus_sure_bitir/konus_artik_temizle):
# macOS izni bekleyen claude girişin kapandığını görmedi, Brifing + claude 2 saat açık kaldı. Sahte "SuflorBrifing" (gerçek süreç) + SIGTERM'i yok sayan alt süreçle denenir.
import os, re, subprocess, sys, tempfile, threading, time, signal
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + ("" if kosul else f"  ({ek})")); kosul or hatalar.append(ad)
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
T = tempfile.mkdtemp(prefix="suflor-yetim-"); BASE = os.path.join(T, "canli b"); os.makedirs(BASE)
ns = {"os": os, "re": re, "subprocess": subprocess, "time": time, "threading": threading, "BASE": BASE, "_g": [], "print": lambda *x: ns["_g"].append(" ".join(map(str, x)))}
exec(kod[kod.index("import signal\nKONUS_PIDLER"):kod.index("threading.Thread(target=konus_artik_temizle")], ns)
uyg = os.path.join(T, "MacOS"); os.makedirs(uyg); sahte = os.path.join(uyg, "SuflorBrifing")
with open(sahte, "w") as f:  # takili: alt süreç SIGTERM'i yok sayar ve ana süreç de bekler (izin bekleyen claude gibi); normal: kendisi hemen çıkar
    f.write("#!/usr/bin/env python3\nimport os, sys, subprocess, time\nk = os.environ.get('SAHTE_KIP', '0.5')\n"
            "if k == 'takili':\n"
            "    subprocess.Popen([sys.executable, '-c', 'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(300)'])\n"
            "    time.sleep(300)\n"
            "time.sleep(float(k))\n")
os.chmod(sahte, 0o755)
istek = os.path.join(BASE, "konus-istek.json")
def ac(sahte_kip="0.5", yol=istek, kip="--istek"): return subprocess.Popen([sahte, kip, yol], start_new_session=True, env=dict(os.environ, SAHTE_KIP=sahte_kip))
def bekle(kosul, sn=10):
    t = time.time()
    while time.time() - t < sn and not kosul(): time.sleep(0.1)
    return kosul()
def canli(pid):
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    try: return not subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip().startswith("Z")
    except OSError: return True
try:
    # 1. arama yalnız bu aktarıcının Konuş istek dosyası (başka klasör, başka kip, başka dosya sayılmaz)
    p1 = ac("2"); baska = ac("2", yol=os.path.join(T, "konus-istek.json")); vt = ac("2", kip="--vt-izle"); dosya = ac("2", yol=os.path.join(BASE, "brifing-istek.json")); bey = ac("2", kip="--beyin")
    time.sleep(0.4)
    bul = ns["konus_yardimci_pidler"]()
    kontrol("arama Konuş istek dosyasını bulur (--istek ve --beyin), başka klasör/kip/dosyayı bulmaz", sorted(bul) == sorted([p1.pid, bey.pid]), (bul, p1.pid, bey.pid))
    ns["KONUS_PIDLER"].add(bey.pid)
    y = ns["konus_yeni_pid"](); kontrol("yeni pid: daha önce görülmemiş tek süreç", y == p1.pid, y)
    kontrol("aynı süreç ikinci kez 'yeni' sayılmaz", ns["konus_yeni_pid"]() is None)
    for p in (p1, baska, vt, dosya, bey): p.wait()
    # 2. kendiliğinden çıkan süreç: dokunulmaz, iz kalmaz
    ns["KONUS_PIDLER"].clear(); ns["_g"].clear(); p2 = ac("1"); time.sleep(0.3); pid = ns["konus_yeni_pid"]()
    ns["konus_sure_bitir"](pid, "deneme", bekle=5); p2.wait(); time.sleep(0.5)
    kontrol("bekleme içinde çıkan süreçte sonlandırma yok, kayıt silinir", ns["_g"] == [] and pid not in ns["KONUS_PIDLER"], ns["_g"])
    # 3. takılı süreç: yardımcı + SIGTERM'i yok sayan alt süreç
    ns["_g"].clear(); p3 = ac("takili"); time.sleep(0.6); pid = ns["konus_yeni_pid"](); alt = ns["_alt_surecler"](pid)
    kontrol("takılı yardımcının alt süreci görülür", pid == p3.pid and len(alt) == 1, (pid, alt))
    t = time.time(); ns["konus_sure_bitir"](pid, "zaman aşımı", bekle=1)
    kontrol("takılı ağaç sonlandırılır (alt süreç SIGKILL'le)", bekle(lambda: not canli(alt[0]) and p3.poll() is not None, 10), (canli(alt[0]), p3.poll()))
    kontrol("günlükte tek satır: neden ve süreç sayısı", bekle(lambda: ns["_g"] == ["KONUŞ: takılı süreç sonlandırıldı (zaman aşımı; 2 süreç)"], 3), ns["_g"])
    kontrol("bekleme süresine uyar (1 sn'den önce dokunmaz, ~4 sn'de biter)", 1 <= time.time() - t < 6, round(time.time() - t, 1))
    # 4. açılışta önceki çalışmadan kalanlar
    ns["KONUS_PIDLER"].clear(); ns["_g"].clear(); p4 = ac("takili"); time.sleep(0.6); a4 = ns["_alt_surecler"](p4.pid)
    ns["konus_artik_temizle"]()
    kontrol("açılış temizliği önceki çalışmadan kalan yardımcıyı ve alt sürecini kapatır", bekle(lambda: p4.poll() is not None and not any(canli(x) for x in a4), 10), (p4.poll(), a4))
    kontrol("açılış temizliği nedenini yazar", bekle(lambda: any("önceki çalışmadan kalmış" in x for x in ns["_g"]), 3), ns["_g"])
    ns["_g"].clear(); ns["konus_artik_temizle"](); time.sleep(0.5); kontrol("temizlenecek süreç yoksa sessiz", ns["_g"] == [], ns["_g"])
finally:
    subprocess.run(["pkill", "-f", re.escape(sahte)], capture_output=True)
# 5. bağlantılar
kontrol("konus_kapat ve bekleyen yuva kapatması temizliği çağırır", kod.count("konus_sure_bitir(pid, neden)") == 2)
kontrol("pid açılışta kaydedilir ve yuvayla taşınır", '_KS["brifing_pid"] = konus_yeni_pid()' in kod and 'KONUS_P = ("saglayici", "w", "app", "brifing_pid",' in kod and "app=None, brifing_pid=None, defter_md=None" in kod)
kontrol("aktarıcı açılışında artık temizliği arka planda", "threading.Thread(target=konus_artik_temizle, daemon=True).start()" in kod)
print("yetim-surec: " + ("✓ hepsi geçti" if not hatalar else f"KALDI {len(hatalar)}")); sys.exit(1 if hatalar else 0)
