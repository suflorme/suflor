#!/usr/bin/env python3
# v0.187.0 (5 Kasım): kendiliğinden kanıtın karar kuralı (background.js OTO-KARAR-BAS/SON bloğu) headless Chrome'da yapay ızgaralarla sınanır:
# ilk kararlı ekran, aynı ekran tekrar kaydedilmez, değişirken kaydedilmez, açılır pencere ve DÖNÜŞ kaydedilir, 10 sn aralık bekletir ama
# kaybettirmez, gidip gelme 2 dk'da en çok 3 dönüş, sekme arkadayken (kare yok) geri gelince aynı ekran yeniden kaydedilmez.
# background.js'te otoKarar değişince koştur:   PYTHONDONTWRITEBYTECODE=1 python3 test/ekran-oto.py   (~5 sn; headless Chrome — test kilidiyle)
import os, re, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if not os.path.exists(CHROME): sys.exit("atlandı: Chrome yok")
bg = open(os.path.join(KOD, "background.js"), encoding="utf-8").read()
m = re.search(r"^const OTO_W .*?(?=^// OTO-KARAR-SON)", bg, re.S | re.M)
if not m: sys.exit("✗ background.js'te OTO-KARAR bloğu bulunamadı")
SENARYO = r"""
const N = OTO_W * OTO_H, sonuc = [];
function izgara(tohum, kutu) {  // tohum: zemin deseni; kutu: [x0,y0,x1,y1] hücrede açık renkli dikdörtgen (açılır pencere)
  const g = new Uint8Array(N);
  for (let i = 0; i < N; i++) g[i] = (i * 37 + tohum * 101) % 200;
  if (kutu) for (let y = kutu[1]; y < kutu[3]; y++) for (let x = kutu[0]; x < kutu[2]; x++) g[y * OTO_W + x] = 250;
  return g;
}
function gurultu(g, n) { const h = g.slice(); for (let i = 0; i < n; i++) h[(i * 997) % N] ^= 0x80; return h; }  // n hücre değişir
const A = izgara(1), B = izgara(2), P = izgara(1, [20, 10, 44, 26]);  // P: A üstünde ~%16'lık açılır pencere
const D = otoYeni(); let t = 1000000; const kayit = [];
const kare = (g, sn = 1.5, bolgeli = true) => { t += sn * 1000; const k = otoKarar(D, g, bolgeli, t); if (k) kayit.push([Math.round((t - 1000000) / 100) / 10, k.donus]); return k; };
const ok = (ad, k) => sonuc.push((k ? "✓ " : "✗ ") + ad);
kare(A); ok("ilk kare tek başına kaydedilmez (kararlılık bekler)", kayit.length === 0);
kare(A); ok("ikinci aynı kare (1,5 sn kararlı) → ilk ekran kaydedilir", kayit.length === 1 && kayit[0][1] === false);
for (let i = 0; i < 20; i++) kare(gurultu(A, i % 3 ? 10 : 20));
ok("aynı ekran (küçük gürültüyle, 30 sn) tekrar kaydedilmez", kayit.length === 1);
for (let i = 0; i < 6; i++) kare(izgara(10 + i));
ok("ekran sürekli değişirken (video/kaydırma) kaydedilmez", kayit.length === 1);
kare(B); kare(B); ok("yeni ekran B kararlı → kaydedilir", kayit.length === 2);
kare(P); kare(P); ok("P, B'den 3 sn sonra: 10 sn dolmadan kaydedilmez", kayit.length === 2);
for (let i = 0; i < 5; i++) kare(P);
ok("P bekledi, 10 sn dolunca kaydedilir (kaybolmaz)", kayit.length === 3 && kayit[2][1] === false);
for (let i = 0; i < 8; i++) kare(B);  // P kaydından ≥ 10 sn sonra
ok("açılır pencere kapandı, B'ye dönüldü → dönüş kaydedilir (10 sn aralık dolunca)", kayit.length === 4 && kayit[3][1] === true);
for (let i = 0; i < 10; i++) kare(B);
ok("dönüşten sonra aynı ekran yeniden kaydedilmez", kayit.length === 4);
// gidip gelme: B ↔ P her 12 sn; 2 dk'da en çok 3 dönüş
const once = kayit.length;
for (let j = 0; j < 10; j++) { const g = j % 2 ? B : P; for (let i = 0; i < 8; i++) kare(g); }
const pp = kayit.slice(once);
ok(`gidip gelmede 2 dk'da en çok 3 dönüş (${pp.length} kayıt)`, pp.length <= 3 && pp.every(k => k[1] === true));
kare(A, 200); kare(A); ok("sekme 200 sn arkadaydı, yeni ekran A geri gelince kaydedilir (dönüş sınırı penceresi geçti)", kayit.length === once + pp.length + 1);
const n0 = kayit.length;
kare(A, 20); kare(A); kare(A);
ok("sekme 20 sn arkadaydı, aynı ekran yeniden kaydedilmez", kayit.length === n0);
kare(izgara(30), 1.5, false); kare(izgara(30), 1.5, false);
ok("bölgesiz ızgara bölgeliyle karşılaştırılmaz (ayrı geçmiş): kaydedilir", kayit.length === n0 + 1);
const n1 = kayit.length; let Z = izgara(30);
for (let i = 0; i < 40; i++) { Z = Z.slice(); for (let j = 0; j < 12; j++) Z[(i * 12 + j) * 7 % N] ^= 0x80; kare(Z, 1.5, false); }
ok("bölgesiz: yavaş birikim (her karede %0,5, toplam ~%20) kayıt üretmez (altyazı birikimi)", kayit.length === n1);
for (let i = 0; i < 40; i++) { Z = Z.slice(); for (let j = 0; j < 12; j++) Z[(i * 12 + j) * 7 % N] ^= 0x80; kare(Z); }
const n2 = kayit.length; ok(`bölgeli: yavaş değişim (içerik kayması) son kayıttan %6 farklılaşınca yine kaydedilir, her karede değil (${n2 - n1} kayıt / 40 kare)`, n2 - n1 >= 2 && n2 - n1 <= 5);
kare(A, 31 * 60); kare(A);
ok("30 dk sonra (yeni toplantı) geçmiş sıfırlanır: aynı ekran yeniden ilk ekran", kayit.length === n2 + 1 && D.kayit.length === 1);
D.sinir = true; kare(B); kare(B); ok("sınır doluysa kaydedilmez", kayit.length === n2 + 1);
document.body.textContent = "SONUC\n" + sonuc.join("\n") + "\nSON";
"""
T = tempfile.mkdtemp(prefix="ekranoto-"); h = os.path.join(T, "t.html")
open(h, "w", encoding="utf-8").write("<!doctype html><meta charset=utf-8><body><script>\n" + m.group(0) + "\n" + SENARYO + "\n</script>")
o = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={os.path.join(T, 'p')}", "--no-first-run", "--dump-dom", "file://" + h],
                   capture_output=True, text=True, timeout=60).stdout
shutil.rmtree(T, ignore_errors=True)
g = re.search(r"SONUC\n(.*?)\nSON", o, re.S)
if not g: print(o[-2000:]); sys.exit("✗ sonuç alınamadı (betik hatası?)")
print(g.group(1)); n = g.group(1).count("✗ ")
print("kendiliğinden kanıt kuralı:", "✓ hepsi geçti" if not n else f"✗ {n} sorun"); sys.exit(1 if n else 0)
