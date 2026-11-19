#!/usr/bin/env python3
# 19 Kasım Claude Meetings kıyasından çıkan üç döküm düzeltmesi (işçi ve aktarıcı yüklenmez, ~0 sn):
#  1) whisper-isci.py UYDURMA: sessizlikte tek başına yabancı teşekkür ("Obrigada.") atılır; cümle içinde kalır.
#  2) whisper-isci.py tr_harf: duraksama sesi "Ğııı"/"ĞI"/"Ğ" silinir; sözcük içindeki ğ ("dağ", "Ağrı") kalır.
#  3) toplanti-claude.py soz_suphe_cozum: canlıda "? X=Y" işaretli satır, aynı toplantıda "✎ X=Y" kesinleşmişse temiz dökümde düzeltilir.
#   PYTHONDONTWRITEBYTECODE=1 python3 -B test/dokum-temizlik.py
import ast, os, re, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def al(dosya, adlar):
    ns = {"re": re, "os": os}; a = ast.parse(open(os.path.join(KOD, dosya), encoding="utf-8").read())
    exec(compile(ast.Module([n for n in a.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or
                             (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in adlar for t in n.targets))], []), dosya, "exec"), ns)
    return ns
hata = 0
def bak(v, b, ad):
    global hata; hata += v != b; print(("✓ " if v == b else "✗ ") + f"{ad}: {v!r}")
w = al("whisper-isci.py", {"UYDURMA", "TR_DURAKSAMA", "tr_harf"})
for m, b in [("Obrigada.", True), ("Obrigado!", True), ("Merci beaucoup.", True), ("obrigada pela ajuda", False), ("Thank you.", False), ("Teşekkürler.", False)]:
    bak(bool(w["UYDURMA"].search(m)), b, f"uydurma '{m}'")
for m, b in [("neyse gireyim bari Ğ abi", "neyse gireyim bari abi"), ("Ğııı Amazon'un neydi Ğı Amazon'da", "Amazon'un neydi Amazon'da"),
             ("ı ĞI etkin", "ı etkin"), ("Ğıı, tamam", "tamam"), ("dağ yoğurt ağır Ağrı", "dağ yoğurt ağır Ağrı"), ("Ğ.", "")]:
    bak(w["tr_harf"](m, "tr"), b, f"duraksama '{m}'")
bak(w["tr_harf"]("Ğııı", "en"), "Ğııı", "İngilizce çözümde dokunulmaz")
t = al("toplanti-claude.py", {"SOZ_IS_RX", "soz_suphe_cozum", "soz_suphe_uygula"})
d = tempfile.mkdtemp(); md = os.path.join(d, "x.md")
open(md, "w", encoding="utf-8").write("| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
    "| 10:00:01 | Ayşe K | Hoş geldin Cloud. | ? Cloud=Claude |\n| 10:00:05 | Bora T | AWS Cloud tarafı | ? Bulut=Bora |\n"
    "| 10:01:00 | Ayşe K | Claude bunu not alsın | ✎ Cloud=Claude |\n| 10:02:00 | Bora T | cloud maliyeti yüksek |  |\n")
class A: dir = d
t["A"] = A; c = t["soz_suphe_cozum"]("x.md")
bak(c.get(("10:00:01", "Hoş geldin Cloud.")), [("Cloud", "Claude")], "kesinleşmiş şüphe düzeltilir")
bak(("10:00:05", "AWS Cloud tarafı") in c, False, "kesinleşmeyen şüphe dokunulmaz")
bak(len(c), 1, "işaretsiz satır listede yok")
bak(t["soz_suphe_uygula"]("Hoş geldin Cloud. Cloudflare", [("Cloud", "Claude")]), "Hoş geldin Claude. Cloudflare", "yalnız tam sözcük")
print("döküm temizlik: " + ("✓ hepsi geçti" if not hata else f"✗ {hata} hata")); sys.exit(1 if hata else 0)
