#!/usr/bin/env python3
# Whisper istemi önem sırası (aktarici/whisper-hat.py istem_siralama, v0.162.4): 120 yapay terimle bu toplantının kişileri ve asistanın adı/hitabı
# düşük sıklıkta olsa da istemde kalır, istem 223 belirteç sınırının altında kalır (işçinin istem_kur'u gerçek belirteçleyiciyle); tekrar (büyük-küçük harf/aksan),
# küçük harfli terim ve çok sözcüklü terimde zaten geçen tek sözcük girmez. Model yüklenmez (yalnız belirteçleyici; whisper-venv yoksa atlanır, ~2 sn).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/istem-sira.py      (kaldı → çıkış 1)
import ast, importlib.util, os, re, sys
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = "/Users/Shared/Suflor/whisper-venv/bin/python"
if not os.path.exists(VENV): print("whisper-venv yok — atlandı"); sys.exit(0)
if sys.executable != VENV: os.execv(VENV, [VENV, "-I", os.path.abspath(__file__)])
ns = {"re": re, "BEN_ESKI": {"ben", "kullanici"}}
agac = ast.parse(open(os.path.join(KOD, "aktarici/whisper-hat.py"), encoding="utf-8").read())
AD = {"_TRSD", "_sd", "_istem_kisi", "istem_siralama", "ISTEM_KAT_ADLARI"}
exec(compile(ast.Module([n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in AD) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in AD for x in n.targets))], []), "whisper-hat.py", "exec"), ns)
sp = importlib.util.spec_from_file_location("whisper_isci", os.path.join(KOD, "whisper-isci.py")); WI = importlib.util.module_from_spec(sp); sp.loader.exec_module(WI)
from mlx_whisper.tokenizer import get_tokenizer
tok = get_tokenizer(multilingual=True, num_languages=100)
hatalar = []
def kontrol(ad, kosul):
    print(("✓ " if kosul else "✗ ") + ad)
    if not kosul: hatalar.append(ad)
# 120 yapay sözlük terimi: hepsi sık (dökümde çok geçer), kişi ve asistan adları dökümde HİÇ geçmez (düşük sıklık)
ter = [{"dogru": f"Zeta{i}Sistemi", "yanlis": [f"zeta {i} sistemi"], "kaynak": "otomatik", "kip": "duzelt"} for i in range(120)]
ter += [{"dogru": "kucukterim", "yanlis": [], "kaynak": "ben"}, {"dogru": "Zeta7Sistemi", "yanlis": ["zeta7"], "kaynak": "ben"}]
dokum = " ".join(f"zeta{i}sistemi" for i in range(120) for _ in range(5 + i % 7))
ks = [{"ad": "ASISTANX", "gorunen_ad": "Orhan", "hitap": ["Orhan", "ASISTANX", "Orhanin", "Orchan", "Orhaan", "Organ", "Orhun"]}]
kisiler = ["Ayşe Yıldırım (Konuk)", "Bora Çelik", "ayse yildirim", "Cem Özkaya", "Defne Arslan", "Emre Şahin", "Işıl Tuna", None, ""]
ag = {"title": "Planlama NOVA toplantısı", "items": ["VeriAmbari maliyeti", "Q4 hedefleri"]}
sira = ns["istem_siralama"](ter, ag, [], ks, kisiler, ["AWS", "Google Workspace"], dokum, "Deniz K")
terimler = [t for _, t in sira]; kat = [k for k, _ in sira]
metin = ", ".join(terimler) + "."
istem, dusen = WI.istem_kur(tok, metin, "")
kalan = [t for t in terimler[:len(terimler) - dusen]]
kontrol(f"istem sınırın altında ({len(tok.encode(' ' + istem))} ≤ {WI.ISTEM_SINIR} belirteç)", len(tok.encode(" " + istem)) <= WI.ISTEM_SINIR)
kontrol(f"önceki metinle de sınırın altında", len(tok.encode(" " + (WI.istem_kur(tok, metin, "bir iki üç " * 30)[0] or ""))) <= WI.ISTEM_SINIR)
kontrol("120 terimin hepsi sığmaz (düşenler var)", dusen > 0)
kontrol("asistan görünen ad ve ad önde, hitap yazımı en çok 2 (çekimli «Orhanin» ve aynı kökler girmez)", kalan[:2] == ["Orhan", "ASISTANX"] and "Orhanin" not in terimler and "Orhaan" not in terimler and kat[:4] == ["asistan"] * 4 and kat[4] == "kişi")
kontrol("kök benzeri bozuk hitap yazımları girmez (≤ 2 hitap)", sum(1 for k in kat if k == "asistan") <= 4)
for ad in ("Ayşe Yıldırım", "Bora Çelik", "Cem Özkaya", "Işıl Tuna", "Deniz K"): kontrol(f"kişi istemde: {ad}", ad in kalan)
kontrol("e-posta/parantez ve tekrar (ayse yildirim) kişiye girmez", not any("@" in t or "(" in t or t == "ayse yildirim" for t in terimler))
kontrol("kişiler terimlerden önce", max(i for i, k in enumerate(kat) if k == "kişi") < min(i for i, k in enumerate(kat) if k in ("sık", "sözlük")))
kontrol("gündem terimleri (NOVA, VeriAmbari) kişiden sonra, sözlükten önce", {"NOVA", "VeriAmbari"} <= set(terimler[:len(kalan)]) and max(i for i, k in enumerate(kat) if k == "kişi") < terimler.index("NOVA") < min(i for i, k in enumerate(kat) if k == "sık"))
kontrol("küçük harfli sözlük terimi girmez", "kucukterim" not in terimler)
kontrol("sıklığı yüksek sözlük adı düşüğünden önce", terimler.index("Zeta5Sistemi") < terimler.index("Zeta0Sistemi") if "Zeta0Sistemi" in terimler else True)
kontrol("aynı terim bir kez (Zeta7Sistemi)", terimler.count("Zeta7Sistemi") == 1)
# kalabalık toplantı: > 8 kişide yalnız ilk ad
s2 = ns["istem_siralama"]([], {}, [], [], [f"Kişi{chr(65 + i)} Soyad{chr(65 + i)}" for i in range(12)], [], "", "")
kontrol("12 kişide ilk ad (kısa biçim)", all(" " not in t for _, t in s2) and len(s2) == 12)
# çok sözcüklü terimde zaten geçen tek sözcük
s3 = ns["istem_siralama"]([{"dogru": "Google Workspace", "yanlis": ["g suite"], "kaynak": "ben"}, {"dogru": "Workspace", "yanlis": ["workspeys"], "kaynak": "ben"}], {}, [], [], [], [], "", "")
kontrol("«Workspace» «Google Workspace» varken ayrıca girmez", [t for _, t in s3] == ["Google Workspace"])
# günlük eki
print("kategori sayıları:", {k: kat.count(k) for k in ns["ISTEM_KAT_ADLARI"]})
print("kaldı" if hatalar else "hepsi geçti"); sys.exit(1 if hatalar else 0)
