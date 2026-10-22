#!/usr/bin/env python3
# S133: kullanıcıya görünen dökümde asistanın adı (aktarici/sozluk.py asistan_goster). İçeride (jsonl, izle, Konuş) hitap biçimi "Claude:" kalır;
# .md dökümde, panodaki canlı dökümde (/status tail) ve notta seslenilen asistanın adı yazılır. Kota harcamaz, Whisper ve Claude yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/dokum-asistan.py
import ast, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, v): print(("✓ " if v else "✗ ") + ad); v or HATA.append(ad)
# 1) birim
ns = {"re": re, "asistan_ad": lambda: "ATLAS"}
agac = ast.parse(open(os.path.join(KOD, "aktarici/sozluk.py"), encoding="utf-8").read())
exec(compile(ast.Module([n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name == "asistan_goster") or
                         (isinstance(n, ast.Assign) and any(getattr(x, "id", None) == "_ASG_RX" for x in n.targets))], []), "sozluk.py", "exec"), ns)
g = ns["asistan_goster"]
for girdi, ad, bek, ne in [
        ("Claude: kaç kart açık?", "NOVA", "NOVA, kaç kart açık?", "satır başı, seslenilen ad"),
        ("Tamam. Claude: özet çıkar.", None, "Tamam. ATLAS, özet çıkar.", "cümle sonrası, ad yoksa toplantı asistanı"),
        ("Tamam... Claude: burada mısın?", "NOVA", "Tamam... NOVA, burada mısın?", "üç noktadan sonra"),
        ("Claude: e-posta yaz (Konuş düğmesiyle)", None, "ATLAS, e-posta yaz (Konuş düğmesiyle)", "Konuş notu"),
        ("Claude mu yazdı bunu?", "NOVA", "Claude mu yazdı bunu?", "hitap değil: değişmez"),
        ("✎ Cloud=Claude:", "NOVA", "✎ → NOVA", "işaret sütunu"),
        ("", "NOVA", "", "boş")]:
    ok(f"asistan_goster: {ne}", g(girdi, ad) == bek)
# 2) yalıtılmış aktarıcı: kişilik NOVA
T = tempfile.mkdtemp(prefix="suflor-dokum-asistan-"); canli = os.path.join(T, "canli"); PORT = 8796
os.makedirs(os.path.join(T, "kisilik"))
kis = os.path.join(T, "kisilik", "nova.md")
open(kis, "w", encoding="utf-8").write("---\nad: NOVA\nhitap: Nova\nhitap_bicimi: siz\n---\n## Kişilik: NOVA\nDeneme kişiliği.\n")
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": T, "kisilik": kis}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py", "toplanti-claude.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log"); env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_HIZLI="1", SUFLOR_TEST_METIN="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None):
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None,
                                                                        headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    M = {"title": "Döküm asistan deneme"}
    uc("/ping", {"meeting": M, "call": True, "panel": True})
    uc("/ingest", {"meeting": M, "source": "whisper", "entries": [{"id": "d/1", "speaker": "Deniz T", "time": "10:00:01", "text": "Nova, kaç kart açık?", "kanal": "ben"}]})
    uc("/note", {"meeting": M, "text": "Claude: e-posta taslağı hazırla (Konuş düğmesiyle)"}); time.sleep(1)
    md = next(os.path.join(canli, f) for f in os.listdir(canli) if f.endswith(".md") and f.startswith("20"))
    mt, jt = open(md, encoding="utf-8").read(), open(md[:-3] + ".jsonl", encoding="utf-8").read()
    ok(".md dökümde asistanın adı, 'Claude:' yok", "NOVA, kaç kart açık?" in mt and "NOVA, e-posta taslağı" in mt and "Claude:" not in mt)
    ok(".jsonl içeride 'Claude:' ve seslenilen ad (hitap)", '"text": "Claude: kaç kart açık?"' in jt and '"hitap": "NOVA"' in jt and '"note": "Claude: e-posta' in jt)
    tl = uc("/status").get("tail") or []; gor = " ".join(str(x.get("text") or x.get("note") or "") for x in tl)  # pano metni ve notu gösterir (sözlük alanını değil)
    ok("panodaki canlı döküm (/status tail) asistanın adıyla", "NOVA, kaç kart açık?" in gor and "NOVA, e-posta taslağı" in gor and "Claude:" not in gor)
    ok("aktarıcıda hata yok", "Traceback" not in open(log, encoding="utf-8", errors="replace").read())
finally:
    r.terminate(); r.wait(5)
    if HATA: print("günlük:", log)
    else: shutil.rmtree(T, ignore_errors=True)
print("dokum-asistan:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
