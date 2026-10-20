#!/usr/bin/env python3
# Suflor.me — aynı çalışma klasöründe birden çok geliştirme oturumu (oturumlar arası commit ve kurulum protokolü, S104, 20 Ekim).
# Sorun (20 Ekim, iki kez): bir oturumun kurulumu öbürünün commit edilmemiş kodunu canlıya kopyaladı; bir commit başka oturumun satırlarını aldı.
# Çözüm: (1) sahiplik — oturum dokunacağı dosyaları yazar, başkası o dosyayı commit edemez; (2) kilit — sürüm artırma → commit → push → yayın → kurulum
# tek oturumda, sırayla; (3) temiz klasör — kurulum, kaydedilmemiş kod varken kurmaz. Kayıtlar .git/ içinde (depoya girmez, aynı klasördeki oturumlar paylaşır).
# Yalnız geliştirme klasöründe (.git/suflor-protokol işareti; "kur" yazar) çalışır; beta kullanıcısının kurulumunu etkilemez.
# Oturum adı ortam değişkeninde: SUFLOR_OTURUM=<ad> (komutun önüne yazılır; ör. SUFLOR_OTURUM=kisilik git commit …).
#   python3 -B oturum.py kur                         işaret + commit kancasına sahiplik denetimi (bir kez)
#   python3 -B oturum.py sahiplen <ad> <dosya>…      dosyaları bu oturuma ayır (başkasının etkin kaydı varsa durur, çıkış 2)
#   python3 -B oturum.py birak <ad> [dosya…]         kaydı kaldır (dosya verilmezse oturumun hepsi)
#   python3 -B oturum.py kilit <ad> <iş>             yayın kilidi (başkasındaysa durur, çıkış 2); coz <ad> bırakır
#   python3 -B oturum.py durum                       kayıtlar, kilit, kaydedilmemiş dosyalar ve sahipleri
#   (--kanca: commit kancası · --kurulum: aktarici-kur.command öncesi · --yayin: yayinla.py öncesi denetim)
import json, os, subprocess, sys, time
KOK = os.path.dirname(os.path.abspath(__file__))
def git(*a): return subprocess.run(["git", "-C", KOK] + list(a), capture_output=True, text=True).stdout
GIT = git("rev-parse", "--absolute-git-dir").strip() or None
ISARET, KAYIT, KILIT = (os.path.join(GIT or "/nonexistent", f) for f in ("suflor-protokol", "suflor-oturumlar.json", "suflor-kilit.json"))
SAHIP_SN, KILIT_SN = 4 * 3600, 30 * 60  # sahiplik 4 saat (her sahiplen/kilit tazeler), kilit 30 dk sonra bayat sayılır
DIS = ("test/",)  # kurulum denetiminde sayılmaz (testler canlıya kopyalanmaz)
def oku(p, v):
    try: return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError): return v
def yaz(p, o):
    t = p + ".gec"; json.dump(o, open(t, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(t, p)
def kayitlar():
    k = oku(KAYIT, {}); simdi = time.time()
    return {d: v for d, v in k.items() if simdi - v.get("t", 0) < SAHIP_SN}
def kilit_al():
    k = oku(KILIT, None)
    return k if k and time.time() - k.get("t", 0) < KILIT_SN else None
def kirli():  # [(durum, yol)] — kaydedilmemiş (değişmiş, eklenmiş, izlenmeyen) dosyalar
    o = []
    for l in git("status", "--porcelain", "--untracked-files=all").splitlines():
        y = l[3:].split(" -> ")[-1].strip().strip('"'); o.append((l[:2], y))
    return o
def ben(): return (os.environ.get("SUFLOR_OTURUM") or "").strip()
def yol_(d): return os.path.relpath(os.path.abspath(d), KOK)
def sahiplen(ad, dosyalar):
    k = kayitlar(); cak = [(d, k[d]["ad"]) for d in map(yol_, dosyalar) if d in k and k[d]["ad"] != ad]
    if cak: print("Durdu — başka oturumun dosyası: " + ", ".join(f"{d} ({a})" for d, a in cak) + ". O oturuma yaz ya da bitirmesini bekle."); return 2
    for d in map(yol_, dosyalar): k[d] = {"ad": ad, "t": time.time()}
    for d, v in k.items():
        if v["ad"] == ad: v["t"] = time.time()
    yaz(KAYIT, k); print(f"{ad}: {len(dosyalar)} dosya ayrıldı"); return 0
def birak(ad, dosyalar):
    k = kayitlar(); ds = set(map(yol_, dosyalar))
    k = {d: v for d, v in k.items() if not (v["ad"] == ad and (not ds or d in ds))}; yaz(KAYIT, k); print(f"{ad}: bırakıldı"); return 0
def kilit(ad, is_):
    k = kilit_al()
    if k and k["ad"] != ad: print(f"Durdu — yayın kilidi {k['ad']}'de ({k.get('is')}, {int(time.time() - k['t'])} sn önce). Bitince yeniden dene."); return 2
    yaz(KILIT, {"ad": ad, "is": is_, "t": time.time()})
    k = kayitlar()
    for v in k.values():
        if v["ad"] == ad: v["t"] = time.time()
    yaz(KAYIT, k); print(f"{ad}: yayın kilidi alındı ({is_})"); return 0
def coz(ad):
    k = kilit_al()
    if k and k["ad"] != ad: print(f"Kilit {k['ad']}'de — bırakılmadı"); return 2
    try: os.remove(KILIT)
    except OSError: pass
    print(f"{ad}: yayın kilidi bırakıldı"); return 0
def durum():
    k = kayitlar(); kl = kilit_al()
    print("Yayın kilidi: " + (f"{kl['ad']} ({kl.get('is')}, {int(time.time() - kl['t'])} sn)" if kl else "boş"))
    for ad in sorted({v["ad"] for v in k.values()}): print(f"  {ad}: " + ", ".join(sorted(d for d, v in k.items() if v["ad"] == ad)))
    kr = kirli(); print("Kaydedilmemiş: " + ("yok" if not kr else ""))
    for s, y in kr: print(f"  {s} {y}  ← " + (k[y]["ad"] if y in k else "SAHİPSİZ"))
    return 0
def kanca():  # commit kancası: başka oturumun dosyası commit'e girmez
    if not os.path.exists(ISARET): return 0
    k = kayitlar(); b = ben(); alinan = [l.strip() for l in git("diff", "--cached", "--name-only").splitlines() if l.strip()]
    cak = [(d, k[d]["ad"]) for d in alinan if d in k and k[d]["ad"] != b]
    if cak:
        print("✗ OTURUM: commit durdu — başka oturumun sahiplendiği dosya: " + ", ".join(f"{d} ({a})" for d, a in cak)
              + (". Kendi oturumunsa komutun önüne SUFLOR_OTURUM=<ad> yaz." if not b else ". Yalnız kendi dosyalarını ekle (git restore --staged <dosya>) ya da o oturuma yaz."))
        return 1
    kl = kilit_al()
    if kl and kl["ad"] != b: print(f"✗ OTURUM: commit durdu — yayın kilidi {kl['ad']}'de ({kl.get('is')}); sürüm numarası çakışmasın. Bitince yeniden dene."); return 1
    return 0
def kurulum():  # aktarici-kur.command öncesi: kaydedilmemiş kod ya da başkasının kilidi varken kurmaz
    if not os.path.exists(ISARET): return 0
    kr = [(s, y) for s, y in kirli() if not y.startswith(DIS)]; k = kayitlar(); kl = kilit_al(); b = ben()
    if kr:
        print("Kurulmadı — kaydedilmemiş değişiklik var (canlıya yarım kod gitmesin; önce commit):")
        for s, y in kr: print(f"  {s} {y}  ← " + (k[y]["ad"] if y in k else "sahipsiz"))
        return 1
    if kl and kl["ad"] != b: print(f"Kurulmadı — yayın kilidi {kl['ad']}'de ({kl.get('is')}). O oturum bitirince kurar."); return 1
    return 0
def yayin():  # yayinla.py --gonder öncesi: başkasının yayın kilidi açıkken yayın yok
    if not os.path.exists(ISARET): return 0
    kl = kilit_al()
    if kl and kl["ad"] != ben(): print(f"Yayın durdu — yayın kilidi {kl['ad']}'de ({kl.get('is')}). O oturum bitirince yeniden dene."); return 1
    return 0
def kur():
    if not GIT: print("git deposu değil"); return 1
    open(ISARET, "w").write("Suflor.me oturum protokolü açık (oturum.py)\n")
    h = os.path.join(GIT, "hooks", "pre-commit"); s = open(h).read() if os.path.exists(h) else "#!/bin/sh\n"
    if "oturum.py" not in s:
        s = s.replace("exec env PYTHONDONTWRITEBYTECODE=1", "env PYTHONDONTWRITEBYTECODE=1", 1).rstrip("\n")
        s += (" || exit 1\n" if "yayinla.py" in s else "\n") + 'exec env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$(git rev-parse --show-toplevel)/oturum.py" --kanca\n'
        open(h, "w").write(s); os.chmod(h, 0o755)
    print("oturum protokolü kuruldu (işaret + commit kancası)"); return 0
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__ or open(__file__).read().split("import ")[0]); sys.exit(0)
    if a[0] == "--kanca": sys.exit(kanca())
    if a[0] == "--kurulum": sys.exit(kurulum())
    if a[0] == "--yayin": sys.exit(yayin())
    is_ = {"kur": lambda: kur(), "durum": lambda: durum(), "sahiplen": lambda: sahiplen(a[1], a[2:]), "birak": lambda: birak(a[1], a[2:]),
           "kilit": lambda: kilit(a[1], " ".join(a[2:]) or "yayın"), "coz": lambda: coz(a[1])}.get(a[0])
    if not is_ or (a[0] in ("sahiplen", "birak", "kilit", "coz") and len(a) < 2): print("kullanım: oturum.py kur|durum|sahiplen <ad> <dosya…>|birak <ad> [dosya…]|kilit <ad> <iş>|coz <ad>"); sys.exit(1)
    sys.exit(is_())
