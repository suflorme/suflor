#!/usr/bin/env python3
# Temiz dökümde elle düzeltme (v0.242.4, 13 Kasım): döküm kontrolündeki düzeltmeler (ses-arsivi/<toplantı>/duzeltme-elle.json) okuma anında
# satıra işlenir (toplanti-claude.py elle_uygula): metin değişir, boş düzeltme satırı düşürür, satırı olmayan parça yeni satır olur (zaman sırasında);
# .jsonl değişmez. dokum --yenile Kaynak satırı bu toplantıyı gösteren temiz dökümü aynı adla yeniden yazar, öncekini ses arşivine yedekler.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/temiz-dokum.py      (kaldı → çıkış 1)
import json, os, shutil, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-td-"); OUT = os.path.join(T, "cikti"); os.makedirs(OUT)
md = "2026-11-13-2059-Deneme-Toplantisi"; t = 1794592857.76
rows = [{"at": "x", "id": "w-karsi-1", "time": "21:00:57", "speaker": "Ayşe Yılmaz", "text": "16.000 kabaydı evet.", "src": "whisper", "kanal": "karsi", "t0": t, "t1": t + 2},
        {"at": "x", "id": "w-ben-2", "time": "21:01:10", "speaker": "Deniz Ak", "text": "Uydurma satır.", "src": "whisper", "kanal": "ben", "t0": t + 13, "t1": t + 14},
        {"at": "x", "id": "w-karsi-3", "time": "21:01:30", "speaker": "Ayşe Yılmaz", "text": "Değişmeyen satır.", "src": "whisper", "kanal": "karsi", "t0": t + 33, "t1": t + 35},
        {"at": "x", "id": "w-ben-4", "time": "21:01:40", "speaker": "Deniz Ak", "text": "Benim satırım.", "src": "whisper", "kanal": "ben", "t0": t + 43, "t1": t + 44}]
open(os.path.join(T, md + ".jsonl"), "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
open(os.path.join(T, md + ".md"), "w").write("# Deneme\n")
kl = os.path.join(T, "ses-arsivi", md); os.makedirs(kl)
par = [{"dosya": "karsi-a.wav", "kanal": "karsi", "t0": t, "t1": t + 2}, {"dosya": "ben-b.wav", "kanal": "ben", "t0": t + 13, "t1": t + 14},
       {"dosya": "ben-c.wav", "kanal": "ben", "t0": t + 20, "t1": t + 21}]
open(os.path.join(kl, "parcalar.jsonl"), "w").write("".join(json.dumps(p) + "\n" for p in par))
json.dump({"toplanti": md, "duzeltmeler": [{"dosya": "karsi-a.wav", "kanal": "karsi", "saat": "21:00:57", "whisper": "16.000 kabaydı evet.", "dogru": "16 gb evet."},
                                           {"dosya": "ben-b.wav", "kanal": "ben", "saat": "21:01:10", "whisper": "Uydurma satır.", "dogru": ""},
                                           {"dosya": "ben-c.wav", "kanal": "ben", "saat": "21:01:17", "whisper": "", "dogru": "Evet evet."}]}, open(os.path.join(kl, "duzeltme-elle.json"), "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
def cli(*a): return subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", T, "dokum", md + ".md", "--cikti", OUT, *a], capture_output=True, text=True, env=env)
hata = []
def bak(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(ad) if not k else None
r = cli("--kim", "Ayse"); dosya = [f for f in os.listdir(OUT) if f.endswith(".md")]
bak("temiz döküm yazıldı", r.returncode == 0 and len(dosya) == 1)
m = open(os.path.join(OUT, dosya[0]), encoding="utf-8").read() if dosya else ""
bak("düzeltilmiş metin dökümde", "16 gb evet." in m and "16.000 kabaydı" not in m)
bak("boş düzeltme satırı düşürdü", "Uydurma satır." not in m)
bak("satırı olmayan parça yeni satır (kullanıcının adıyla)", "Evet evet." in m and m.index("Evet evet.") < m.index("Değişmeyen satır."))
bak("değişmeyen satır duruyor", "Değişmeyen satır." in m and "Benim satırım." in m)
bak(".jsonl değişmedi", "16.000 kabaydı" in open(os.path.join(T, md + ".jsonl"), encoding="utf-8").read())
d = json.load(open(os.path.join(kl, "duzeltme-elle.json"))); d["duzeltmeler"][0]["dogru"] = "16 gigabayt evet."; json.dump(d, open(os.path.join(kl, "duzeltme-elle.json"), "w"))
r = cli("--yenile"); dosya2 = sorted(f for f in os.listdir(OUT) if f.endswith(".md"))
bak("--yenile aynı adla yeniden yazdı (yeni dosya yok)", r.returncode == 0 and dosya2 == dosya and "16 gigabayt evet." in open(os.path.join(OUT, dosya[0]), encoding="utf-8").read())
bak("--yenile önceki hâli yedekledi", os.path.exists(os.path.join(kl, "temiz-dokum-onceki", dosya[0])))
shutil.rmtree(OUT); os.makedirs(OUT); r = cli("--yenile")
bak("--yenile: temiz döküm yoksa bir şey yazmaz", r.returncode == 0 and not os.listdir(OUT))
shutil.rmtree(T, ignore_errors=True)
print("temiz döküm: ✓ hepsi geçti" if not hata else f"temiz döküm: ✗ {len(hata)} kaldı"); sys.exit(1 if hata else 0)
