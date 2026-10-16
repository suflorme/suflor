#!/usr/bin/env python3
# Konuş için kayıt veritabanı sorgusu (v0.54.0, toplanti-claude.py vt-sema / vt-sor): yalnız okunur, tek SELECT/WITH, en çok 60 satır, gizli sütunlar maskeli.
# Yapay veritabanı ve ayar (SUFLOR_AYAR); gerçek veritabanına dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/vt-sor.py
import json, os, shutil, sqlite3, subprocess, sys, tempfile
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="vt-"); proje = os.path.join(T, "proje"); os.makedirs(proje); hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
db = os.path.join(proje, "kayit.db"); c = sqlite3.connect(db)
c.execute("CREATE TABLE kisiler (ad TEXT, rol TEXT, admin_sayisi INTEGER, sifre TEXT, api_key TEXT)")
c.executemany("INSERT INTO kisiler VALUES (?,?,?,?,?)", [("Ayla K", "BT", 7, "gizli123", "k-1"), ("Deniz T", "Satış", 2, "p4ss", "k-2")] + [(f"Kişi {i}", "Diğer", 0, "x", "y") for i in range(70)])
c.execute("CREATE VIEW yoneticiler AS SELECT ad, admin_sayisi FROM kisiler WHERE admin_sayisi > 0"); c.commit(); c.close()
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "proje": proje, "uygulama": T, "veritabani": {"yol": "kayit.db"}}, open(ay, "w"))
tc = lambda *a: subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), *a], capture_output=True, text=True, env=dict(os.environ, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1"))
try:
    o = tc("vt-sema").stdout
    ok("şema: tablo, görünüm, satır sayısı, gizli sütun işareti", "kisiler (tablo, 72 satır)" in o and "yoneticiler (görünüm" in o and "sifre [gizli]" in o and "api_key [gizli]" in o)
    o = tc("vt-sor", "SELECT ad, admin_sayisi FROM kisiler ORDER BY admin_sayisi DESC LIMIT 1").stdout
    ok("en fazla admin yetkisi: doğru satır", "Ayla K\t7" in o)
    o = tc("vt-sor", "SELECT ad, sifre, api_key FROM kisiler WHERE ad = 'Ayla K'").stdout
    ok("gizli sütunlar maskeli", "***" in o and "gizli123" not in o and "k-1" not in o)
    o = tc("vt-sor", "SELECT * FROM kisiler").stdout
    ok("en çok 60 satır + daralt uyarısı", o.count("\n") <= 63 and "daralt" in o)
    for q, ad in [("UPDATE kisiler SET rol = 'x'", "UPDATE"), ("SELECT 1; DROP TABLE kisiler", "çoklu sorgu"), ("WITH a AS (SELECT 1) DELETE FROM kisiler", "WITH içinde DELETE"), ("PRAGMA table_info(kisiler)", "PRAGMA")]:
        r = tc("vt-sor", q); ok(f"reddedildi: {ad}", r.returncode != 0 and "Yalnız tek" in r.stdout)
    # MCP sunucusu (Konuş süreci bu yoldan kullanır; Brifing yardımcısı komut aracını reddeder)
    girdi = "\n".join(json.dumps(m) for m in [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "vt_sor", "arguments": {"sorgu": "SELECT ad, sifre FROM kisiler ORDER BY admin_sayisi DESC LIMIT 1"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "vt_sor", "arguments": {"sorgu": "DELETE FROM kisiler"}}}]) + "\n"
    m = subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "vt-mcp"], input=girdi, capture_output=True, text=True, env=dict(os.environ, SUFLOR_AYAR=ay, PYTHONDONTWRITEBYTECODE="1"))
    c = {o["id"]: o for o in (json.loads(x) for x in m.stdout.splitlines() if x.strip())}
    ok("MCP: initialize + tools/list (vt_sema, vt_sor)", c.get(1, {}).get("result", {}).get("protocolVersion") == "2025-06-18" and [x["name"] for x in c.get(2, {}).get("result", {}).get("tools", [])] == ["vt_sema", "vt_sor"])
    t3 = c.get(3, {}).get("result", {}); t4 = c.get(4, {}).get("result", {})
    ok("MCP: vt_sor sonucu doğru ve gizli sütun maskeli; DELETE hata olarak döner", "Ayla K\t***" in t3.get("content", [{}])[0].get("text", "") and t4.get("isError") is True)
    ok("veritabanı değişmedi", sqlite3.connect(db).execute("SELECT count(*) FROM kisiler").fetchone()[0] == 72)
    json.dump({"alan": "Deneme", "proje": proje, "uygulama": T}, open(ay, "w")); r = tc("vt-sema")
    ok("ayar yoksa açık mesaj, hata kodu", r.returncode != 0 and "ayarlı değil" in r.stdout)
finally:
    if not any(hata): shutil.rmtree(T, ignore_errors=True)
    else: print("(deneme klasörü: " + T + ")")
print("vt-sor:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
