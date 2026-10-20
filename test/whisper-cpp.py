#!/usr/bin/env python3
# whisper.cpp + Core ML motoru (ayar whisper_motor: cpp → SUFLOR_WHISPER_CPP): yerel macOS sesiyle (say) Türkçe/İngilizce parçalar üretir,
# canlı Whisper işçisini bu motorla açar. Denetim: hazır satırında motor cpp, Türkçe ve İngilizce metin, dil kodu, ses izi ve bölüm izleri,
# sessizlik süzgeci (boş metin), istem geri okuma süzgeci, işçi öldürülünce whisper-server'ın da kapanması, aktarıcının ayar → ortam eşlemesi.
# Kurulu değilse (<ortak>/whisper-cpp yok) atlar. Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/whisper-cpp.py (~1 dk; ilk açılışta Core ML derlemesi)
import base64, json, os, re, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: canlı kullanım koruması (gerçek model)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORT = "/Users/Shared/Suflor"; CPP = os.path.join(ORT, "whisper-cpp"); PY = os.path.join(ORT, "whisper-venv", "bin", "python")
ECAPA = os.path.join(ORT, "ses-modeller", "spkrec-ecapa-voxceleb", "ecapa-mlx.npz")
if not (os.path.exists(os.path.join(CPP, "whisper-server")) and os.path.exists(PY)): print("whisper.cpp ya da whisper-venv kurulu değil — atlandı"); sys.exit(0)
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
T = tempfile.mkdtemp(prefix="suflor-test-wcpp-")
def pcm(ses, metin, ad):
    subprocess.run(["say", "-v", ses, "-o", os.path.join(T, ad + ".aiff"), metin], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", os.path.join(T, ad + ".aiff"), os.path.join(T, ad + ".wav")], check=True)
    b = open(os.path.join(T, ad + ".wav"), "rb").read(); return b[b.index(b"data") + 8:]
TR = pcm("Yelda", "Bugünkü toplantıda stok yönetimini konuşacağız. Barkod okuyucular sık sık bağlantı kaybediyor.", "tr")
EN = pcm("Eddy", "The carrier confirmed the new pickup window starts on Monday.", "en")
IKI = TR + b"\0\0" * 8000 + pcm("Eddy", "Thanks, I will send the quote on Thursday.", "en2")

env = dict(os.environ, SUFLOR_WHISPER_CPP=CPP, PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", **({"SUFLOR_ECAPA": ECAPA} if os.path.exists(ECAPA) else {}))
t = time.time()
p = subprocess.Popen([PY, "-u", os.path.join(KOD, "whisper-isci.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
h = json.loads(p.stdout.readline() or "{}")
kontrol(f"işçi hazır, motor cpp ({time.time() - t:.0f} sn)", h.get("hazir") and h.get("motor") == "cpp" and "whisper.cpp" in (h.get("model") or ""))
def gonder(b, **k):
    p.stdin.write(json.dumps(dict(id=k.pop("id", "x"), pcm=base64.b64encode(b).decode(), baslik="Deneme", **k)) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline() or "{}")
r = gonder(TR, id="tr", dil="tr", istem="Kubernetes, Grafana.", onceki="", kanal="karsi")
kontrol(f"Türkçe metin ({r.get('sn')} sn): {r.get('text')!r}", re.search(r"stok", r.get("text") or "", re.I) and re.search(r"barkod", r.get("text") or "", re.I) and r.get("dil") == "tr")
kontrol("karşı kanalda ses izi ve küme", bool(r.get("iz")) and r.get("kume") if os.path.exists(ECAPA) else True)
r = gonder(EN, id="en", dil="en", kanal="karsi")
kontrol(f"İngilizce metin: {r.get('text')!r}", re.search(r"pickup", r.get("text") or "", re.I) and r.get("dil") == "en")
r = gonder(IKI, id="iki", dil=None, diller=["tr", "en"], kanal="karsi")
kontrol(f"iki dilli parça, bölüm izleri ({len(r.get('bol') or [])}): {r.get('text')!r}", r.get("text") and (len(r.get("bol") or []) >= 2 or not os.path.exists(ECAPA)))
r = gonder(b"\0\0" * 16000 * 3, id="sessiz", dil="tr", kanal="karsi")
kontrol(f"sessizlikte boş metin (atlanan {r.get('atlanan')})", r.get("text") == "" and not r.get("hata"))
r = gonder(b"\0\0" * 16000 * 2, id="istem", dil="tr", istem="Kubernetes, Terraform, Grafana, Jira, Prometheus.", kanal="ben")
kontrol(f"istem geri okunmuyor: {r.get('text')!r}", "Terraform" not in (r.get("text") or "") and "Prometheus" not in (r.get("text") or ""))
srv = subprocess.run(["pgrep", "-P", str(p.pid), "-f", "whisper-server"], capture_output=True, text=True).stdout.split()
kontrol("whisper-server işçinin alt süreci, yalnız 127.0.0.1", srv and "127.0.0.1" in subprocess.run(["ps", "-o", "command=", "-p", srv[0]], capture_output=True, text=True).stdout)
p.kill(); time.sleep(4)
kontrol("işçi öldürülünce whisper-server kapandı", not any(subprocess.run(["ps", "-p", s], capture_output=True).returncode == 0 for s in srv))

# aktarıcı: ayar whisper_motor → işçi ortamı (whisper-hat.py wh_cpp)
src = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
kontrol("aktarıcı SUFLOR_WHISPER_CPP'yi yalnız whisper_motor: cpp iken verir", 'AYAR.get("whisper_motor") == "cpp"' in src and '"SUFLOR_WHISPER_CPP": WH_CPP} if wh_cpp()' in src)
print(f"\n{sum(ok)}/{len(ok)} geçti"); sys.exit(0 if all(ok) else 1)
