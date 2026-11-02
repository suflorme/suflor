#!/usr/bin/env python3
# Takvim yardımcısının etkinlik süzgeci (2 Kasım; takvim.swift olayAlinir/kendiMi, v0.165.5): Exchange davetsiz etkinlikte düzenleyeni boş bırakır,
# kullanıcının kendi Teams bağlantılı deneme toplantısı atlanıyordu. Süzgeç bloğu (SUZGEC-BAS/SON) metinden çıkarılır, geçici klasörde derlenir ve çalıştırılır.
import itertools, os, re, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + ("" if kosul else f"  ({ek})")); kosul or hatalar.append(ad)
kaynak = open(os.path.join(KOD, "takvim.swift"), encoding="utf-8").read()
kontrol("süzgeç işaretleri var", "// SUZGEC-BAS" in kaynak and "// SUZGEC-SON" in kaynak)
blok = kaynak[kaynak.index("// SUZGEC-BAS"):kaynak.index("// SUZGEC-SON")]
kontrol("döngü olayAlinir( çağırıyor", bool(re.search(r"if !olayAlinir\(", kaynak[kaynak.index("// SUZGEC-SON"):])))
kontrol("kendi ayrinti çıktısında hâlâ var", '"kendi": kendi' in kaynak)
# durum: (ad, digerBos, duzenleyenVar, benDuzenleyen, benKatilan, yazilabilir, baglantiVar, beklenen)
D = [
 ("Exchange tek kişilik, düzenleyen yok, yazılabilir, bağlantı var", 1, 0, 0, 0, 1, 1, 1),
 ("aynısı bağlantısız (kişisel kayıt)", 1, 0, 0, 0, 1, 0, 0),
 ("düzenleyen yok, yazılamaz takvim (abone/tatil), bağlantı var", 1, 0, 0, 0, 0, 1, 0),
 ("Google: kullanıcı düzenler, katılımcı yok, bağlantı var", 1, 1, 1, 0, 1, 1, 1),
 ("kullanıcı düzenler, başka katılımcılar var", 0, 1, 1, 1, 1, 0, 1),
 ("başkası düzenler, kullanıcı katılımcı", 1, 1, 0, 1, 1, 0, 1),
 ("paylaşılan takvim: başkası düzenler, kullanıcı katılımcı değil", 0, 1, 0, 0, 0, 0, 0),
 ("başkası düzenler, katılımcı listesi boş (kullanıcı yok)", 1, 1, 0, 0, 1, 1, 0),
]
def b(x): return "true" if x else "false"
T = tempfile.mkdtemp(prefix="suflor-takvim-suzgec-")
ana = ["import Foundation", blok, "func eski(_ digerBos: Bool, _ duzenleyenVar: Bool, _ benDuzenleyen: Bool, _ benKatilan: Bool, _ yazilabilir: Bool, _ baglantiVar: Bool) -> Bool {",
       "  let kendi = benDuzenleyen || (!duzenleyenVar && yazilabilir)",
       "  if digerBos && !(duzenleyenVar && !benDuzenleyen) && !(kendi && baglantiVar) { return false }",
       "  if !benKatilan && !kendi { return false }",
       "  return true", "}", "var farkli = 0",
       "for m in 0..<64 {",
       "  let v = (0..<6).map { (m >> $0) & 1 == 1 }",
       "  if olayAlinir(digerBos: v[0], duzenleyenVar: v[1], benDuzenleyen: v[2], benKatilan: v[3], yazilabilir: v[4], baglantiVar: v[5]) != eski(v[0], v[1], v[2], v[3], v[4], v[5]) { farkli += 1 }",
       "}", 'print("FARK \\(farkli)")']
for i, d in enumerate(D):
    a = ", ".join(f"{n}: {b(x)}" for n, x in zip(["digerBos", "duzenleyenVar", "benDuzenleyen", "benKatilan", "yazilabilir", "baglantiVar"], d[1:7]))
    ana.append(f'print("D{i} \\(olayAlinir({a}))")')
yol = os.path.join(T, "main.swift"); open(yol, "w", encoding="utf-8").write("\n".join(ana) + "\n")
exe = os.path.join(T, "suzgec")
d = subprocess.run(["swiftc", yol, "-o", exe, "-module-cache-path", os.path.join(T, "mc")], capture_output=True, text=True)
kontrol("süzgeç bloğu derlenir", d.returncode == 0, d.stderr[-400:])
if d.returncode == 0:
    cikti = subprocess.run([exe], capture_output=True, text=True).stdout
    for i, x in enumerate(D):
        kontrol(x[0] + (" → alınır" if x[7] else " → atlanır"), f"D{i} {'true' if x[7] else 'false'}" in cikti.splitlines(), cikti)
    kontrol("64 bool birleşiminde eski ifadeyle aynı", "FARK 0" in cikti.splitlines(), cikti)
if hatalar: print(f"takvim-suzgec: ✗ KALDI {len(hatalar)}"); sys.exit(1)
print("takvim-suzgec: ✓ hepsi geçti")
