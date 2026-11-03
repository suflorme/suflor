#!/usr/bin/env python3
# Dosyadan döküm (toplanti-claude.py dosyadan): yerel macOS sesleriyle (say) iki konuşmacılı, Türkçe/İngilizce karışık ~40 sn kayıt üretir,
# m4a'ya çevirir, gerçek Whisper işçisiyle döker. Denetim: dil ve konuşmacı paragraf başına doğru, --adlar, --bas saati, .vtt, hedef varsa
# Whisper'dan önce durma, sessiz ve bozuk dosya; ses izi hafızası (v0.26.0): Yelda'nın izi önceden hafızadaysa --adlar'sız dökümde Türkçe
# paragraflar onun adını alır, İngilizce "Konuşmacı 1" kalır. Whisper kurulu değilse atlar. Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/dosyadan.py
import os, re, subprocess, sys, tempfile, time, wave, json
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: canlı kullanım koruması (gerçek model)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TC = os.path.join(KOD, "toplanti-claude.py")
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
T = tempfile.mkdtemp(prefix="suflor-test-dosyadan-"); CANLI = os.path.join(T, "canli"); os.makedirs(CANLI)  # gerçek canli/ (sözlük, hafıza) karışmasın
def tc(*a): return subprocess.run([sys.executable, TC, "--relay", "http://127.0.0.1:9", "--dir", CANLI, *a], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
TR = ["Bugünkü toplantıda stok yönetimini konuşacağız. Toplam sipariş sayısı yüz kırk iki.", "Barkod okuyucular sık sık bağlantı kaybediyor, Cuma gününe kadar plan lazım."]
EN = ["Thanks. The carrier confirmed the new pickup window starts on Monday.", "I can take the action plan for the scanners and send a quote by Thursday."]
def wav(ses, metin, ad):
    subprocess.run(["say", "-v", ses, "-o", ad + ".aiff", metin], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", ad + ".aiff", ad + ".wav"], check=True)
    b = open(ad + ".wav", "rb").read(); return b[b.index(b"data") + 8:]
o = wave.open(os.path.join(T, "kayit.wav"), "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000)
for k, (s, m) in enumerate([("Yelda", TR[0]), ("Eddy", EN[0]), ("Yelda", TR[1]), ("Eddy", EN[1])]): o.writeframes(wav(s, m, os.path.join(T, f"p{k}")) + b"\0\0" * 12800)
o.close(); g = os.path.join(T, "Depo deneme.m4a"); subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", os.path.join(T, "kayit.wav"), g], check=True)
cik = os.path.join(T, "cikti"); os.makedirs(cik)
t = time.time(); r = tc("dosyadan", g, "--cikti", cik, "--bas", "2026-10-10 14:00", "--adlar", "Ayşe,John"); sn = time.time() - t
if "Whisper kurulu değil" in r.stdout + r.stderr: print("Whisper kurulu değil — atlandı"); sys.exit(0)
md = os.path.join(cik, "Suflor-Depo-deneme-transkript-20261010.md")
md = next((os.path.join(cik, f) for f in os.listdir(cik) if f.endswith(".md")), md)
kontrol(f"döküm yazıldı ({sn:.0f} sn)", r.returncode == 0 and os.path.exists(md))
L = [l for l in open(md, encoding="utf-8") if l.startswith("**[")] if os.path.exists(md) else []
def tr_mi(m): return bool(re.search(r"[çğıöşüÇĞİÖŞÜ]", m))
kontrol("4 paragraf, Türkçe → Ayşe, İngilizce → John", len(L) == 4 and all(("Ayşe" in l.split(":**")[0]) == tr_mi(l.split(":**", 1)[1]) for l in L))
kontrol("İngilizce paragraf Türkçeye zorlanmadı (carrier, Thursday)", any("carrier" in l for l in L) and any("Thursday" in l for l in L))
kontrol("--bas: ilk satır 14:00:00, başlıkta elle verilen adlar", L[:1] and L[0].startswith("**[14:00:00]") and "Konuşmacı adları elle verildi" in open(md, encoding="utf-8").read())
kontrol(".vtt yanında, <v Ayşe>", os.path.exists(md[:-3] + ".vtt") and "<v Ayşe>" in open(md[:-3] + ".vtt", encoding="utf-8").read())
t = time.time(); r2 = tc("dosyadan", g, "--cikti", cik, "--bas", "2026-10-10 14:00")
kontrol("hedef varsa Whisper'dan önce durur (< 3 sn)", r2.returncode != 0 and "zaten var" in r2.stderr + r2.stdout and time.time() - t < 3)
w = wave.open(os.path.join(T, "sessiz.wav"), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(b"\0\0" * 44100 * 3); w.close()
r3 = tc("dosyadan", os.path.join(T, "sessiz.wav"), "--cikti", cik)
kontrol("sessiz dosya: 'konuşma bulunamadı'", "konuşma bulunamadı" in r3.stderr + r3.stdout)
open(os.path.join(T, "bozuk.m4a"), "w").write("metin")
r4 = tc("dosyadan", os.path.join(T, "bozuk.m4a"), "--cikti", cik)
kontrol("bozuk dosya: 'ses çıkarılamadı'", "ses çıkarılamadı" in r4.stderr + r4.stdout)
# ses izi hafızası: Yelda'nın ilk cümlesinden iz (işçinin Ecapa'sı) → hafıza; ikinci döküm adları kendisi bulmalı
AY = json.load(open(os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
py = next((y for y in (os.path.join(d, "whisper-venv", "bin", "python") for d in (AY["ortak"], AY["uygulama"])) if os.path.exists(y)), None)
ec = next((y for y in (os.path.join(d, "ses-modeller", "spkrec-ecapa-voxceleb", "ecapa-mlx.npz") for d in (AY["ortak"], AY["uygulama"])) if os.path.exists(y)), None)
if py and ec:
    kod = ("import sys, json, base64, numpy as np, mlx.core as mx, importlib.util; s = importlib.util.spec_from_file_location('w', sys.argv[1]); w = importlib.util.module_from_spec(s); s.loader.exec_module(w)\n"
           "b = open(sys.argv[3], 'rb').read(); a = np.frombuffer(b[b.index(b'data') + 8:], np.int16).astype(np.float32) / 32768\n"
           "e = np.array(w.Ecapa(sys.argv[2], np, mx)(a), np.float32); e /= np.linalg.norm(e)\n"
           "print(json.dumps({'Yelda Hanım': {'iz': base64.b64encode(e.astype(np.float16).tobytes()).decode(), 'sn': 60, 'toplantilar': ['onceki.md']}}))")
    h = subprocess.run([py, "-c", kod, os.path.join(KOD, "whisper-isci.py"), ec, os.path.join(T, "p0.wav")], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    open(os.path.join(CANLI, "ses-izi-hafiza.json"), "w").write(h.stdout)
    cik2 = os.path.join(T, "cikti2"); os.makedirs(cik2); r5 = tc("dosyadan", g, "--cikti", cik2, "--bas", "2026-10-10 14:00")
    md2 = next((os.path.join(cik2, f) for f in os.listdir(cik2) if f.endswith(".md")), None)
    L2 = [l for l in open(md2, encoding="utf-8") if l.startswith("**[")] if md2 else []
    kontrol("hafıza: Türkçe → Yelda Hanım, İngilizce → Konuşmacı 1, başlıkta not",
            len(L2) == 4 and all(("Yelda Hanım" if tr_mi(l.split(":**", 1)[1]) else "Konuşmacı 1") in l.split(":**")[0] for l in L2)
            and "ses izi hafızasından" in r5.stdout and "Ses izi hafızasından adlanan" in open(md2, encoding="utf-8").read())
else: print("(ses izi modeli yok — hafıza denetimi atlandı)")
# --- Çözme motoru (3 Kasım, S188 adım 2): whisper.cpp varsayılan, MLX yedek, MLX modeli yalnız gerekince iner, toplantıda duraklatma sunucuyu da durdurur ---
import shutil, signal, glob
AY_YOL = os.environ.get("SUFLOR_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json")
CPP_VAR = all(os.path.exists(os.path.join(AY["ortak"], "whisper-cpp", f)) for f in ("whisper-server", "ggml-large-v3-turbo-q8_0.bin", "ggml-large-v3-turbo-encoder.mlmodelc")) and AY.get("whisper_motor") != "mlx"
def ayar_yaz(ad, **ek):
    d = dict(AY, **ek); y = os.path.join(T, ad); json.dump(d, open(y, "w", encoding="utf-8")); return y
def tcm(ayar, *a, **env): return subprocess.run([sys.executable, TC, "--relay", "http://127.0.0.1:9", "--dir", CANLI, *a], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ayar, **env))
def dokum_satirlari(c):
    f = next((os.path.join(c, x) for x in os.listdir(c) if x.endswith(".md")), None) if os.path.isdir(c) else None
    return f, [l for l in open(f, encoding="utf-8") if l.startswith("**[")] if f else []
if CPP_VAR:
    kontrol("varsayılan motor whisper.cpp ('Whisper yüklendi (whisper.cpp)')", "(whisper.cpp)" in r.stdout)
    c = os.path.join(T, "c-mlx"); os.makedirs(c); rm = tcm(ayar_yaz("ayar-mlx.json", whisper_motor="mlx"), "dosyadan", g, "--cikti", c, "--bas", "2026-10-10 14:00")
    f, L = dokum_satirlari(c); kontrol("whisper_motor: mlx → MLX yolu, dökümde cpp'siz aynı iki dil", "(MLX)" in rm.stdout and len(L) == 4 and any("Thursday" in l for l in L))
    # cpp açılamaz: ikili çalıştırılamıyor (izinsiz) → aynı işte MLX
    ort = os.path.join(T, "ortak-sahte"); os.makedirs(os.path.join(ort, "whisper-cpp", "ggml-large-v3-turbo-encoder.mlmodelc"))
    for f_ in ("whisper-server", "ggml-large-v3-turbo-q8_0.bin"): open(os.path.join(ort, "whisper-cpp", f_), "w").close()
    for f_ in ("whisper-venv", "whisper-modeller", "ses-modeller"):
        if os.path.exists(os.path.join(AY["ortak"], f_)): os.symlink(os.path.join(AY["ortak"], f_), os.path.join(ort, f_))
    ay_y = ayar_yaz("ayar-yedek.json", ortak=ort, uygulama=os.path.join(T, "uyg-sahte"), whisper_motor="cpp"); os.makedirs(os.path.join(T, "uyg-sahte"))
    c = os.path.join(T, "c-yedek"); os.makedirs(c); ry = tcm(ay_y, "dosyadan", g, "--cikti", c, "--bas", "2026-10-10 14:00")
    f, L = dokum_satirlari(c); kontrol("cpp açılamadı → aynı işte MLX yedeği, döküm yazıldı", ry.returncode == 0 and "(MLX)" in ry.stdout and len(L) == 4)
    # cpp açılamaz + MLX modeli diskte yok → yalnız şimdi iner (test: yerel anlık görüntüden kopya), sonra MLX'le biter
    kaynak = next(iter(sorted(glob.glob(os.path.join(AY["ortak"], "whisper-modeller", "hub", "models--mlx-community--whisper-large-v3-turbo", "snapshots", "*")))), None)
    if kaynak:
        ort2 = os.path.join(T, "ortak-bos"); shutil.copytree(ort, ort2, symlinks=True); os.remove(os.path.join(ort2, "whisper-modeller")); os.makedirs(os.path.join(ort2, "whisper-modeller"))
        ay_b = ayar_yaz("ayar-bos.json", ortak=ort2, uygulama=os.path.join(T, "uyg-sahte"), whisper_motor="cpp")
        c = os.path.join(T, "c-indir"); os.makedirs(c); rb = tcm(ay_b, "dosyadan", g, "--cikti", c, "--bas", "2026-10-10 14:00", SUFLOR_TEST_MLX_KAYNAK=kaynak)
        f, L = dokum_satirlari(c); kontrol("MLX modeli yok: 'iniyor' yazar, iner, MLX'le döküm yazılır", rb.returncode == 0 and "iniyor" in rb.stdout and "(MLX)" in rb.stdout and len(L) == 4)
        ort3 = os.path.join(T, "ortak-yazilamaz"); shutil.copytree(ort2, ort3, symlinks=True); shutil.rmtree(os.path.join(ort3, "whisper-modeller", "hub"), ignore_errors=True); os.chmod(os.path.join(ort3, "whisper-modeller"), 0o555)
        ay_c = ayar_yaz("ayar-yazilamaz.json", ortak=ort3, uygulama=os.path.join(T, "uyg-sahte"), whisper_motor="cpp"); c = os.path.join(T, "c-hata"); os.makedirs(c)
        rc = tcm(ay_c, "dosyadan", g, "--cikti", c, "--bas", "2026-10-10 14:00"); os.chmod(os.path.join(ort3, "whisper-modeller"), 0o755)
        kontrol("MLX modeli indirilemezse anlaşılır hata, döküm yok", rc.returncode != 0 and "MLX modeli indirilemedi" in rc.stdout + rc.stderr and not dokum_satirlari(c)[1])
    # toplantıda duraklatma: aktarıcının yaptığı gibi yeni oturum + SIGSTOP/SIGCONT süreç grubuna; whisper-server aynı grupta olmalı ve durmalı
    c = os.path.join(T, "c-dur"); os.makedirs(c)
    pr = subprocess.Popen([sys.executable, TC, "--relay", "http://127.0.0.1:9", "--dir", CANLI, "dosyadan", g, "--cikti", c, "--bas", "2026-10-10 14:00"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, start_new_session=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=AY_YOL))
    def sunucu(): return [x.split() for x in subprocess.run(["ps", "-axo", "pid=,pgid=,stat=,command="], capture_output=True, text=True).stdout.splitlines() if "whisper-server" in x and x.split()[1] == str(pr.pid)]
    t_ = time.time(); sv = []
    while time.time() - t_ < 90 and not sv and pr.poll() is None: time.sleep(0.5); sv = sunucu()
    kontrol("whisper-server dosyadan işiyle aynı süreç grubunda", bool(sv))
    if sv:
        os.killpg(pr.pid, signal.SIGSTOP); time.sleep(1.5)
        dur = [x[2] for x in sunucu()]; kontrol("SIGSTOP sunucuyu da durdurur", bool(dur) and all(d.startswith("T") for d in dur))
        os.killpg(pr.pid, signal.SIGCONT)
    cikti_ = pr.communicate(timeout=180)[0]; f, L = dokum_satirlari(c)
    kontrol("duraklatılıp sürdürülen iş bitti, döküm tam", pr.returncode == 0 and len(L) == 4)
    time.sleep(2); kontrol("iş bitince whisper-server kalmadı", not [x for x in subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines() if "whisper-server" in x and T in x] and not sunucu())
else: print("(whisper.cpp yok ya da ayar mlx — motor denetimleri atlandı)")
kontrol("geçici WAV kalmadı", not [f for f in os.listdir(tempfile.gettempdir()) if f.startswith("suflor-dosya-")])
subprocess.run(["rm", "-rf", T])
print(f"dosyadan: {'✓ hepsi geçti' if all(ok) else '✗ ' + str(ok.count(False)) + ' kaldı'} ({sum(ok)}/{len(ok)})"); sys.exit(0 if all(ok) else 1)
