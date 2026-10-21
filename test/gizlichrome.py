#!/usr/bin/env python3
# Testlerin headless Chrome'u Dock'ta görünmesin. Chrome sıradan uygulama olarak açılıp ancak sonra arka plana geçtiği için her açılışta Dock'ta
# simge bir an belirir (22 Ekim, lsappinfo: önce Foreground, sonra BackgroundOnly). Çözüm: Chrome'un APFS klonu (diskte yer kaplamaz) +
# Info.plist'te LSBackgroundOnly + yerel imza. LSUIElement kullanılmaz: Chrome kendini yardımcı süreç sanıp ICU verisini bulamıyor.
# Kopya Chrome sürümü değişince kendiliğinden yenilenir; kurulamazsa gerçek Chrome'un yolu döner (test yine çalışır, yalnız simge görünür).
#   from gizlichrome import chrome_yolu, CHROME_EK   →   [chrome_yolu(), "--headless=new", *CHROME_EK, ...]
import fcntl, os, plistlib, shutil, subprocess
KAYNAK = "/Applications/Google Chrome.app"
YER = os.path.expanduser("~/Library/Caches/suflor-test-chrome")
KOPYA = os.path.join(YER, "Suflor Test Chrome.app")
IKILI = "Contents/MacOS/Google Chrome"   # ad aynı kalır: testlerin pkill -f "Google Chrome.*--headless" kalıbı kopyayı da yakalar
CHROME_EK = ["--use-mock-keychain"]       # yeniden imzalı kopya gerçek Chrome'un Anahtar Zinciri öğesini isteyip izin penceresi açmasın

def _surum(app):
    try:
        with open(os.path.join(app, "Contents/Info.plist"), "rb") as f: return plistlib.load(f).get("CFBundleVersion")
    except (OSError, plistlib.InvalidFileException): return None

def _kur(surum):
    gecici = KOPYA + ".kuruluyor"
    shutil.rmtree(gecici, ignore_errors=True)
    subprocess.run(["cp", "-c", "-R", KAYNAK, gecici], check=True)
    pl = os.path.join(gecici, "Contents/Info.plist")
    with open(pl, "rb") as f: d = plistlib.load(f)
    d["LSBackgroundOnly"] = True
    with open(pl, "wb") as f: plistlib.dump(d, f)
    subprocess.run(["codesign", "--force", "--sign", "-", gecici], check=True, capture_output=True)
    shutil.rmtree(KOPYA, ignore_errors=True); os.rename(gecici, KOPYA)

def chrome_yolu():
    gercek = os.path.join(KAYNAK, IKILI)
    if os.environ.get("SUFLOR_GIZLI_CHROME") == "0": return gercek
    surum = _surum(KAYNAK)
    if not surum: return gercek
    if _surum(KOPYA) == surum and os.path.exists(os.path.join(KOPYA, IKILI)): return os.path.join(KOPYA, IKILI)
    try:
        os.makedirs(YER, exist_ok=True)
        with open(os.path.join(YER, ".kilit"), "w") as k:   # aynı anda test koşan iki oturum kopyayı birlikte kurmasın
            fcntl.flock(k, fcntl.LOCK_EX)
            if _surum(KOPYA) != surum: _kur(surum)
        return os.path.join(KOPYA, IKILI)
    except (OSError, subprocess.CalledProcessError):
        return gercek

if __name__ == "__main__": print(chrome_yolu())
