#!/usr/bin/env python3
# Dosyadan döküm (toplanti-claude.py dosyadan): yerel macOS sesleriyle (say) iki konuşmacılı, Türkçe/İngilizce karışık ~40 sn kayıt üretir,
# m4a'ya çevirir, gerçek Whisper işçisiyle döker. Denetim: dil ve konuşmacı paragraf başına doğru, --adlar, --bas saati, .vtt, hedef varsa
# Whisper'dan önce durma, sessiz ve bozuk dosya. Whisper kurulu değilse atlar. Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/dosyadan.py
import os, re, subprocess, sys, tempfile, time, wave, json
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TC = os.path.join(KOD, "toplanti-claude.py")
ok = []
def kontrol(ad, kosul): ok.append(bool(kosul)); print(("✓ " if kosul else "✗ ") + ad)
def tc(*a): return subprocess.run([sys.executable, TC, "--relay", "http://127.0.0.1:9", *a], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
T = tempfile.mkdtemp(prefix="suflor-test-dosyadan-")
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
kontrol("geçici WAV kalmadı", not [f for f in os.listdir(tempfile.gettempdir()) if f.startswith("suflor-dosya-")])
subprocess.run(["rm", "-rf", T])
print(f"dosyadan: {'✓ hepsi geçti' if all(ok) else '✗ ' + str(ok.count(False)) + ' kaldı'} ({sum(ok)}/{len(ok)})"); sys.exit(0 if all(ok) else 1)
