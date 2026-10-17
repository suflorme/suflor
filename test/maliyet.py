#!/usr/bin/env python3
# Toplantı oturumu maliyeti (v0.57.0; toplanti-claude.py maliyet, aktarıcının toplanti_maliyet_yaz'ı). Sahte Claude Code oturum dökümleriyle (geçici HOME), ağ yok:
# fiyat (giriş, çıkış, önbellekten okuma, önbelleğe yazma 5 dk 1,25× · 1 sa 2×), aynı message.id teke iner, /toplanti olmayan oturum sayılmaz, 30 dk içinde biten
# oturum beklenir, toplantı dosyası eşleşmesi ve etiket kuralı (karşı kanal + başlık), --json yazmaz, ikinci koşu yinelemez (arşivdeki satırlar da sayılır), --etiket.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/maliyet.py
import gzip, json, os, re, shutil, subprocess, sys, tempfile, time, datetime
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
PORT = bos_port(8790)
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UYG = re.search(r'^UYG = os\.path\.join\(EV, "([^"]+)"\)', open(os.path.join(KOD, ".claude/skills/suflor-olcum/olcum.py"), encoding="utf-8").read(), re.M).group(1)  # olcum.py'nin canlı klasörü
T = tempfile.mkdtemp(prefix="maliyet-"); EV = os.path.join(T, "ev"); canli = os.path.join(EV, _UYG, "canli"); proje = os.path.join(T, "proje")
for d in (EV, canli, proje): os.makedirs(d)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor"}, open(ay, "w"))
kok = os.path.join(EV, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", proje)); os.makedirs(kok)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat().replace("+00:00", "Z")
def oturum(ad, t0, sure_dk, ilk, cagri):  # cagri: [(id, model, usage)] — her çağrı iki satır (içerik bloğu başına), aynı id
    with open(os.path.join(kok, ad + ".jsonl"), "w") as f:
        f.write(json.dumps({"type": "user", "timestamp": iso(t0), "message": {"role": "user", "content": ilk}}) + "\n")
        for k, (i, m, u) in enumerate(cagri):
            for _ in range(2): f.write(json.dumps({"type": "assistant", "timestamp": iso(t0 + (k + 1) * sure_dk * 60 / len(cagri)), "message": {"id": i, "model": m, "usage": u}}) + "\n")
simdi = time.time(); gun = simdi - 2 * 86400
U = {"input_tokens": 1000, "cache_creation_input_tokens": 300000, "cache_creation": {"ephemeral_1h_input_tokens": 100000}, "cache_read_input_tokens": 2000000, "output_tokens": 10000}
# beklenen: giriş 1000×4 + yazma 5 dk 200k×4×1,25 + 1 sa 100k×4×2 + okuma 2M×0,20 + çıkış 10k×20 (MTok başına)
BEK = (1000 * 4 + 200000 * 4 * 1.25 + 100000 * 4 * 2 + 2000000 * 0.20 + 10000 * 20) / 1e6
oturum("a-gercek", gun, 40, "<command-message>toplanti</command-message>\n<command-name>/toplanti</command-name>", [("m1", "claude-opus-5-5", U), ("m2", "claude-opus-5-5", U)])
oturum("b-sonnet", gun + 7200, 20, "<command-name>/toplanti</command-name>", [("s1", "claude-sonnet-5-5", U)])
oturum("c-baska", gun + 3600, 10, "Bu bir /toplanti komutundan söz eden normal oturum", [("x1", "claude-opus-5-5", U)])
oturum("d-suruyor", simdi - 600, 5, "<command-name>/toplanti</command-name>", [("d1", "claude-opus-5-5", U)])
def dosya(t, ad, karsi):
    b = os.path.join(canli, datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d-%H%M") + "-" + ad)
    open(b + ".md", "w").write("# " + ad + "\n")
    open(b + ".jsonl", "w").write(json.dumps({"kanal": "ben", "text": "merhaba"}) + "\n" + (json.dumps({"kanal": "karsi", "text": "selam"}) + "\n" if karsi else ""))
    os.utime(b + ".md", (t + 45 * 60, t + 45 * 60)); return os.path.basename(b) + ".md"
d_a = dosya(gun - 120, "Musteri-gorusmesi", True); d_b = dosya(gun + 7200 - 60, "Suflor-deneme", True)
env = dict(os.environ, HOME=EV, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1")
tc = lambda *a: subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "maliyet", *a], capture_output=True, text=True, env=env)
try:
    r = tc("--json"); sat = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    ok(f"--json: 2 biten /toplanti oturumu, dosyaya yazmadı ({len(sat)})", len(sat) == 2 and not os.path.exists(os.path.join(canli, "claude-cagri.jsonl")))
    a = next((x for x in sat if x["oturum"] == "a-gercek"), {}); b = next((x for x in sat if x["oturum"] == "b-sonnet"), {})
    ok(f"fiyat: aynı message.id teke indi, 1 sa yazma 2× ({a.get('maliyet')} $ = 2 × {BEK:.4f})", abs((a.get("maliyet") or 0) - 2 * BEK) < 1e-3 and a.get("tur") == 2)
    ok(f"Sonnet fiyatı ayrı ({b.get('maliyet')} $)", abs((b.get("maliyet") or 0) - (1000 * 2 + 200000 * 2 * 1.25 + 100000 * 2 * 2 + 2000000 * 0.20 + 10000 * 10) / 1e6) < 1e-3)
    ok(f"toplantı dosyası eşleşti, karşı kanal + başlık temiz → gercek ({a.get('dosya')}, {a.get('etiket')})", a.get("dosya") == d_a and a.get("etiket") == "gercek")
    ok(f"başlıkta 'deneme' → deneme ({b.get('dosya')}, {b.get('etiket')})", b.get("dosya") == d_b and b.get("etiket") == "deneme")
    ok("/toplanti olmayan ve 30 dk içinde biten oturum sayılmadı", not any(x["oturum"] in ("c-baska", "d-suruyor") for x in sat))
    ok(f"süre ve dakika başı ({a.get('sure_dk')} dk, {a.get('dk_maliyet')} $/dk)", a.get("sure_dk") == 40 and abs(a["dk_maliyet"] - a["maliyet"] / 40) < 1e-3)
    r = tc(); n1 = open(os.path.join(canli, "claude-cagri.jsonl")).read().count('"is": "toplanti"')
    r2 = tc(); n2 = open(os.path.join(canli, "claude-cagri.jsonl")).read().count('"is": "toplanti"')
    ok(f"yazdı ve ikinci koşu yinelemedi ({n1} → {n2})", n1 == 2 and n2 == 2 and "0 yeni" in r2.stdout)
    os.makedirs(os.path.join(canli, "arsiv")); y = os.path.join(canli, "claude-cagri.jsonl")
    with gzip.open(os.path.join(canli, "arsiv", "claude-cagri.jsonl.gz"), "ab") as f: f.write(open(y, "rb").read())
    open(y, "w").close(); r3 = tc("--json")
    ok("döndürülüp arşive giden satırlar da sayıldı (yinelenmedi)", not [l for l in r3.stdout.splitlines() if l.startswith("{")])
    tc("--etiket", "b-sonnet", "gercek"); e = json.load(open(os.path.join(canli, "toplanti-etiket.json")))
    ok("--etiket elle düzeltme dosyaya", e.get("b-sonnet") == "gercek")
    # olcum.py maliyet: dönemdeki her oturum tabloda, tablo toplamı özetle tutar (dosyası olmayan oturum da; v0.57.2 — önce son 15 satır)
    for k in range(17): oturum(f"e{k}", gun - 86400 - k * 3600, 5, "<command-name>/toplanti</command-name>", [(f"e{k}m", "claude-opus-5-5", U)])
    tc()
    o = subprocess.run([sys.executable, "-B", os.path.join(KOD, ".claude/skills/suflor-olcum/olcum.py"), "maliyet", "--json"], capture_output=True, text=True, env=env)
    try: m = json.loads(o.stdout)
    except ValueError: m = {}
    tb = sum(r["maliyet"] for r in m.get("toplantilar", [])); oz = (m.get("gercek") or {}).get("maliyet", 0) + (m.get("deneme") or {}).get("maliyet", 0)
    n_oz = (m.get("gercek") or {}).get("toplanti", 0) + (m.get("deneme") or {}).get("toplanti", 0)
    ok(f"olcum.py tablosu her oturumu gösterir ({len(m.get('toplantilar', []))} satır = {n_oz}) ve toplamı özetle tutar ({tb:.2f} = {oz:.2f})",
       len(m.get("toplantilar", [])) == n_oz == 19 and abs(tb - oz) < 0.02)
    ok("etiket düzeltmesi raporda (b-sonnet gerçek)", (m.get("gercek") or {}).get("toplanti") == 2)
    r = tc("--geri", "--json")
    ok("hata yok", "Traceback" not in r.stderr + r3.stderr)
finally:
    if not HATA: shutil.rmtree(T, ignore_errors=True)
    else: print("klasör:", T)
print("maliyet:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun")
