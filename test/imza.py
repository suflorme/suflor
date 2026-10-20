#!/usr/bin/env python3
# İmzalı yayın (güvenlik denetimi O5, v0.99.0): yayinla.py'nin ürettiği IMZA/dosyalar.sha256 + .sig biçimi; kurulum.py imza_dogrula / guncelle ve
# kur.sh imza, özet ya da dosya listesi tutmazsa kurmaz. Deneme anahtarıyla sahte yayın (ağ yok; kur.sh'de curl sahte, HOME geçici, sihirbaz açılmaz).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/imza.py      (~5 sn)
import hashlib, importlib.util, io, os, shutil, subprocess, sys, tarfile, tempfile, contextlib
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="imza-"); ok = []
def kontrol(ad, k): ok.append(bool(k)); print(("✓ " if k else "✗ ") + ad)
def anahtar(ad):
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "deneme", "-f", os.path.join(T, ad)], check=True)
    return open(os.path.join(T, ad + ".pub")).read().strip()
ACIK, BASKA = anahtar("k1"), anahtar("k2")
def yayin(surum="9.9.9", bozul=None, ekle=None, ad="k1"):  # yayinla.py'nin biçimi: "# suflor <sürüm>", "<sha256>  <yol>", ssh-keygen -Y sign -n suflor-yayin
    d = tempfile.mkdtemp(dir=T); os.makedirs(os.path.join(d, "aktarici")); os.makedirs(os.path.join(d, "IMZA"))
    dos = {"manifest.json": '{"version": "%s"}' % surum, "relay.py": "print('aktarici')\n", "aktarici/x.py": "x = 1\n", ".gitignore": "*.pyc\n",
           "kurulum.py": "import sys; sys.exit(0)\n", "README.md": "deneme\n"}
    for y, m in dos.items(): open(os.path.join(d, y), "w").write(m)
    m = os.path.join(d, "IMZA", "dosyalar.sha256")
    open(m, "w").write(f"# suflor {surum}\n" + "".join(f"{hashlib.sha256(open(os.path.join(d, y), 'rb').read()).hexdigest()}  {y}\n" for y in sorted(dos)))
    subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", os.path.join(T, ad), "-n", "suflor-yayin", m], check=True)
    if bozul: open(os.path.join(d, bozul), "a").write("# eklenen satır\n")
    if ekle: open(os.path.join(d, ekle), "w").write("kötü\n")
    return d
def tar(d):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:gz") as t: t.add(d, arcname="suflor-main")
    p = os.path.join(T, f"y{len(os.listdir(T))}.tar.gz"); open(p, "wb").write(b.getvalue()); return p
os.environ["SUFLOR_AYAR"] = os.path.join(T, "yok-ayar.json")
spec = importlib.util.spec_from_file_location("kr", os.path.join(KOD, "kurulum.py")); kr = importlib.util.module_from_spec(spec); sys.argv = ["kurulum.py"]
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(kr)
try:
    kontrol("sağlam paket doğrulanır, sürüm okunur", kr.imza_dogrula(yayin(), ACIK) == (None, "9.9.9"))
    kontrol("değişmiş dosya → red", "değişmiş" in (kr.imza_dogrula(yayin(bozul="relay.py"), ACIK)[0] or ""))
    kontrol("imzalı listede olmayan dosya → red", "aynı değil" in (kr.imza_dogrula(yayin(ekle="aktarici/ek.py"), ACIK)[0] or ""))
    kontrol("başka anahtarla imza → red", kr.imza_dogrula(yayin(ad="k2"), ACIK)[0] == "imza tutmadı")
    d = yayin(); os.remove(os.path.join(d, "IMZA", "dosyalar.sha256.sig")); kontrol("imzasız paket → red", kr.imza_dogrula(d, ACIK)[0] == "pakette imza yok")
    kontrol("kurulu sürümdeki açık anahtar gerçek yayın anahtarı (ssh-ed25519)", kr.YAYIN_ACIK.startswith("ssh-ed25519 ") and kr.YAYIN_ACIK not in (ACIK, BASKA))
    # guncelle: kurulu kod (KOD) geçici kopya; doğrulanamayan paket hiçbir dosyayı değiştirmez
    kopya = os.path.join(T, "kurulu"); os.makedirs(kopya); open(os.path.join(kopya, "manifest.json"), "w").write('{"version": "1.0.0"}'); kr.KOD = kopya
    kr.mesgul = lambda: ""; os.environ["SUFLOR_TEST_IMZA_ACIK"] = ACIK
    def gunc(p):
        try:
            with contextlib.redirect_stdout(io.StringIO()): kr.guncelle(p, zorla=True)
        except SystemExit as e: return str(e)
        return ""
    r = gunc(tar(yayin(bozul="relay.py"))); kontrol(f"guncelle: bozuk paket kurulmaz, dosya değişmez", "değişmiş" in r and not os.path.exists(os.path.join(kopya, "relay.py")))
    r = gunc(tar(yayin(surum="0.5.0"))); kontrol("guncelle: kuruludan eski sürüm kurulmaz (geri alma saldırısı)", "eski" in r and not os.path.exists(os.path.join(kopya, "relay.py")))
    kr.subprocess_run_gercek = kr.subprocess.run
    r = gunc(tar(yayin(surum="1.1.0"))); kontrol("guncelle: sağlam paket kopyalanır", os.path.exists(os.path.join(kopya, "relay.py")) and '"1.1.0"' in open(os.path.join(kopya, "manifest.json")).read())
    # kur.sh: sahte curl (tar'ı verir), HOME geçici, sihirbaz satırları ve gerçek süreç öldürme yok; açık anahtar deneme anahtarı
    def kur(paket):
        ev = tempfile.mkdtemp(dir=T); b = os.path.join(T, "bin"); os.makedirs(b, exist_ok=True)
        open(os.path.join(b, "curl"), "w").write(f"#!/bin/sh\ncat '{paket}'\n"); os.chmod(os.path.join(b, "curl"), 0o755)
        s = open(os.path.join(KOD, "kur.sh"), encoding="utf-8").read()
        s = s.replace(kr.YAYIN_ACIK, ACIK).split('echo "→ Kurulum sihirbazı açılıyor"')[0] + "echo KURULDU\n"
        k = os.path.join(T, "kur-deneme.sh"); open(k, "w").write(s)
        r = subprocess.run(["bash", k], capture_output=True, text=True, env=dict(os.environ, HOME=ev, PATH=b + ":/usr/bin:/bin:/usr/sbin:/sbin"), timeout=60)
        return r.stdout + r.stderr, os.path.join(ev, "Suflor.me")
    o, kd = kur(tar(yayin())); kontrol("kur.sh: sağlam paket kurulur", "KURULDU" in o and os.path.isfile(os.path.join(kd, "relay.py")))
    o, kd = kur(tar(yayin(bozul="aktarici/x.py"))); kontrol("kur.sh: değişmiş dosya → durur, klasör yok", "özetleri tutmadı" in o and not os.path.exists(kd))
    o, kd = kur(tar(yayin(ekle="ek.sh"))); kontrol("kur.sh: fazladan dosya → durur", "listede olmayan" in o and not os.path.exists(kd))
    o, kd = kur(tar(yayin(ad="k2"))); kontrol("kur.sh: başka anahtar → durur", "imza tutmadı" in o and not os.path.exists(kd))
    if kr.YAYIN_ACIK not in open(os.path.join(KOD, "kur.sh")).read(): kontrol("kur.sh ve kurulum.py aynı açık anahtar", False)
    else: kontrol("kur.sh ve kurulum.py aynı açık anahtar", True)
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"{sum(ok)}/{len(ok)}"); sys.exit(0 if all(ok) else 1)
