#!/usr/bin/env python3
# Proje hazırlığı T5 — proje kartı (proje-karti.py): sahte claude ile (kota yok). Aday seçimi (eski sürüm, dışa aktarım, kopya, adla hariç,
# toplantı dökümü girmez; sınır; düzenli klasör belgeleri önde), belge başına çıkarım ve önbellek (ikinci tur 0 çağrı, değişen belge yeniden),
# birleştirme (tek sözcüklü ad + tam ad + takma ad tek kişi), çelişen tarih işareti, düzenli klasörde "fark", veritabanı kipi (kişiler
# veritabanından, istemde yalnız özet + sözlük), toplantıda durma, bozuk JSON'da bir yeniden deneme, onay (kart dosyası, sözlüğe aktarma, proje notu).
# Faz 11 Aşama 2: proje notu <uygulama>/proje-notu.md (0600; CLAUDE.md'ye yazılmaz; tc proje-notu eski taslak bölümü bir kez taşır), sahte OpenAI uyumlu
# sunucuyla (beyin.proje_karti) JSON kipi + kayıtta sağlayıcı, sağlayıcı hata verince bir kez Claude Code (yedek).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/proje-karti.py      (kaldı → çıkış 1)
import http.server, importlib.util, io, contextlib, json, os, shutil, socket, sqlite3, subprocess, sys, tempfile, threading

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp(prefix="suflor-kart-"); P = os.path.join(T, "proje"); U = os.path.join(T, "uyg"); os.makedirs(os.path.join(U, "canli"))
SAHTE = os.path.join(T, "claude"); SAYAC = os.path.join(T, "sayac.jsonl")
# sahte claude: istemdeki "KISI: ad | rol" vb. satırlardan JSON üretir; "BOZUK" geçen belgede ilk cevap bozuk; istemin türünü sayaca yazar
open(SAHTE, "w").write(r'''#!/usr/bin/env python3
import sys, json, re, os
istem = sys.stdin.read(); S = os.environ.get("SAYAC") or "''' + SAYAC + r'''"
yol = (re.search(r"BELGE: (\S+)", istem) or [None, "ozet"])[1]
onceki = sum(1 for l in open(S) if json.loads(l)["yol"] == yol) if os.path.exists(S) else 0
open(S, "a").write(json.dumps({"yol": yol, "tam": '"kisiler"' in istem}) + "\n")
if "BOZUK" in istem and onceki == 0: print(json.dumps({"result": "bozuk cevap", "total_cost_usd": 0.001})); sys.exit()
if yol == "ozet": print(json.dumps({"result": "Deneme projesi: depo taşıma ve tedarikçi seçimi.", "total_cost_usd": 0.002})); sys.exit()
o = {"ozet": f"{yol} özeti", "kisiler": [], "kurumlar": [], "kararlar": [], "tarihler": [], "acik_isler": [], "sozluk": []}
k = "-"
for ln in istem.splitlines():
    km = re.match(r"\[([^\]]+)\] ", ln)
    if km: k = km.group(1)
    m = re.search(r"(KISI|KARAR|TARIH|IS|TERIM|KURUM): (.*)", ln)
    if not m: continue
    tur, v = m.group(1), [x.strip() for x in m.group(2).split("|")]
    if tur == "KISI": o["kisiler"].append({"ad": v[0], "rol": v[1] if len(v) > 1 else "", "takma_adlar": v[2].split(",") if len(v) > 2 and v[2] else [], "konum": k})
    if tur == "KARAR": o["kararlar"].append({"ne": v[0], "ne_zaman": v[1], "kim": v[2] if len(v) > 2 else "", "konum": k})
    if tur == "TARIH": o["tarihler"].append({"ne": v[0], "tarih": v[1], "konum": k})
    if tur == "IS": o["acik_isler"].append({"is": v[0], "sahip": v[1], "tarih": v[2], "konum": k})
    if tur == "TERIM": o["sozluk"].append({"terim": v[0], "aciklama": v[1], "konum": k})
    if tur == "KURUM": o["kurumlar"].append({"ad": v[0], "konum": k})
print(json.dumps({"result": "```json\n" + json.dumps(o, ensure_ascii=False) + "\n```", "total_cost_usd": 0.003}))
''')
os.chmod(SAHTE, 0o755)
BELGE = {
    "CLAUDE.md": "# Proje\n\nKISI: Ayşe Yılmaz | proje yöneticisi | AY\n\nKARAR: Depo Gebze'ye taşınacak | 2026-11-01 | Ayşe\n",
    "belgeler/toplanti-notu.md": "# Not\n\nKISI: Ayşe | yönetici\n\nKISI: AY | koordinatör\n\nKARAR: Depo Gebze'ye taşınacak | 2026-11-15 | Ayşe\n\nTERIM: Gebze Lojistik Merkezi | yeni depo\n\nKURUM: Atlas Taşımacılık\n",
    "belgeler/plan.md": "# Plan\n\nIS: Tedarikçi listesini çıkar | Deniz | 2026-10-25\n\nTARIH: Açılış töreni | 2026-12-01\n\nKISI: Kemal Demir | satın alma\n\nTERIM: Gebze Lojistik Merkezi | depo\n\nTERIM: Tek Belgede Geçen | x\n\nTERIM: kayit.py | betik\n",
    "belgeler/eski-plan-v1.md": "# Plan\n\nIS: Eski iş | Biri | 2026-01-01\n" * 30,
    "belgeler/eski-plan-v2.md": "# Plan\n\nIS: Eski iş | Biri | 2026-01-01\n" * 30 + "ek\n",
    "veri/disa/kisiler.csv": "ad,rol\nKISI: Gizli Kisi | yok\n",
    "belgeler/sifreler.md": "# Hesaplar\n\nKISI: Hariç Kişi | yok\n",
    "belgeler/bozuk.md": "# Bozuk\n\nBOZUK ilk cevap\n\nKISI: Selin Ak | muhasebe\n",
}
for k, m in BELGE.items():
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w", encoding="utf-8").write(m)
os.utime(os.path.join(P, "belgeler/eski-plan-v1.md"), (1e9, 1e9))
os.makedirs(os.path.join(U, "canli"), exist_ok=True); os.symlink(os.path.join(U, "canli"), os.path.join(P, "_canli"))
open(os.path.join(U, "canli", "2026-10-17-1000-deneme.jsonl"), "w").write(json.dumps({"speaker": "Deniz", "time": "10:00", "text": "KISI: Toplantı Kişisi | yok"}) + "\n")
ay = os.path.join(T, "ayar.json")
def ayar_yaz(**ek): json.dump(dict({"alan": "Deneme", "uygulama": U, "proje": P, "ortak": os.path.join(T, "yok"), "claude": SAHTE}, **ek), open(ay, "w"))
ayar_yaz(); os.environ["SUFLOR_AYAR"] = ay; os.environ["SAYAC"] = SAYAC; sys.dont_write_bytecode = True
def yukle():
    sp = importlib.util.spec_from_file_location("kart", os.path.join(KOD, "proje-karti.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
cagri = lambda: [json.loads(l) for l in open(SAYAC)] if os.path.exists(SAYAC) else []
try:
    K = yukle(); c = K.B.baglan(); K.B.tara(c); K.B.guncelle(c)
    ad = [a[0] for a in K.aday_belgeler(c)]
    kontrol("adaylar: düzenli klasör belgesi önde; eski sürüm, dışa aktarım, adla hariç, toplantı dökümü yok",
            ad[0] == "CLAUDE.md" and set(ad) == {"CLAUDE.md", "belgeler/toplanti-notu.md", "belgeler/plan.md", "belgeler/eski-plan-v2.md", "belgeler/bozuk.md"}, str(ad))
    kontrol("sınır: en çok N belge", len(K.aday_belgeler(c, 2)) == 2)
    t = K.cikar(tahmin=True)
    kontrol("tahmin Claude'a sormaz", t["belge"] == 5 and not cagri(), json.dumps(t))
    k = K.cikar(paralel=2)
    ay_ = [p for p in k["kisiler"] if p["ad"] == "Ayşe Yılmaz"]
    kontrol("birleştirme: 'Ayşe Yılmaz', 'Ayşe' ve takma ad 'AY' tek kişi", len(ay_) == 1 and {"Ayşe", "AY"} <= set(ay_[0]["takma_adlar"]) and not any(p["ad"] in ("Ayşe", "AY") for p in k["kisiler"]),
            json.dumps(k["kisiler"], ensure_ascii=False)[:300])
    kr = [x for x in k["kararlar"] if "Gebze" in x["ne"]]
    kontrol("çelişen tarih silinmedi, işaretlendi", len(kr) == 1 and kr[0].get("celiski") == {"ne_zaman": ["2026-11-01", "2026-11-15"]}, json.dumps(kr, ensure_ascii=False))
    kontrol("düzenli klasör: CLAUDE.md'den gelen satır fark değil, yalnız diğer belgeden gelen fark", kr[0]["fark"] is False and
            [x for x in k["kisiler"] if x["ad"] == "Kemal Demir"][0]["fark"] is True and k["kip"] == "duzenli")
    kontrol("sözlük tekilleşti, kaynakları birikti", [m["terim"] for m in k["sozluk"]][:1] == ["Gebze Lojistik Merkezi"] and len(k["sozluk"][0]["kaynaklar"]) == 2)
    kontrol("bozuk JSON'da bir kez daha soruldu, belge girdi", any(p["ad"] == "Selin Ak" for p in k["kisiler"]) and sum(1 for x in cagri() if x["yol"] == "belgeler/bozuk.md") == 2)
    kontrol("proje özeti tek çağrıyla, kaynak satırlarında konum var", k["ozet"].startswith("Deneme projesi") and all(len(s) == 2 and s[1] for p in k["kisiler"] for s in p["kaynaklar"]))
    n1 = len(cagri()); k2 = K.cikar()
    kontrol("ikinci tur: önbellekten, 0 Claude çağrısı", len(cagri()) == n1 and k2["onbellek"] == 5, f"{len(cagri()) - n1} çağrı")
    open(os.path.join(P, "belgeler/plan.md"), "a", encoding="utf-8").write("\nKISI: Yeni Kişi | analist\n"); K.B.guncelle(c); n2 = len(cagri()); k3 = K.cikar()
    kontrol("değişen belge: yalnız o belge + proje özeti yeniden soruldu", len(cagri()) - n2 == 2 and any(p["ad"] == "Yeni Kişi" for p in k3["kisiler"]), f"{len(cagri()) - n2} çağrı")
    json.dump({"meeting": {"title": "x"}}, open(os.path.join(U, "canli", "heartbeat.json"), "w"))
    open(os.path.join(P, "belgeler/plan.md"), "a", encoding="utf-8").write("\nKISI: Bir Kişi Daha | x\n"); K.B.guncelle(c); n3 = len(cagri()); k4 = K.cikar(paralel=1)
    os.remove(os.path.join(U, "canli", "heartbeat.json"))
    kontrol("toplantıda: Claude'a sorulmadı, nedeni yazıldı", len(cagri()) == n3 and "toplantı" in (k4["durdu"] or ""), json.dumps(k4.get("durdu")))
    r = K.onayla(k3)
    s = json.load(open(K.SOZLUK, encoding="utf-8"))
    kontrol("onay: kart dosyası 0600, sözlüğe 1 terim (tek belgede geçen ve dosya adı aktarılmaz), düzenli klasörde CLAUDE.md'ye dokunulmadı", os.stat(K.KART).st_mode & 0o777 == 0o600 and r["sozluk_eklenen"] == 1
            and [t["dogru"] for t in s["terimler"]] == ["Gebze Lojistik Merkezi"] and r["proje_notu"] is False and not os.path.exists(K.PROJE_NOTU) and "Proje kartı" not in open(os.path.join(P, "CLAUDE.md")).read())
    kontrol("ikinci onay sözlüğe tekrar eklemez", K.onayla(k3)["sozluk_eklenen"] == 0)
    # genel kip (kökte düzenli belge yok) → proje notu uygulama klasöründe (K4); CLAUDE.md'ye dokunulmaz
    os.rename(os.path.join(P, "CLAUDE.md"), os.path.join(P, "belgeler", "giris.md")); open(os.path.join(P, "CLAUDE.md"), "w").write("# Notlar\n")
    K.B.guncelle(c); kg = K.cikar(); kg["kip"] = "genel"
    r2 = K.onayla(kg); r2b = K.onayla(kg); nt = open(K.PROJE_NOTU, encoding="utf-8").read()
    kontrol("genel kipte proje notu <uygulama>/proje-notu.md (0600, yeniden onayda tek başlık), CLAUDE.md değişmedi", r2["proje_notu"] is True and r2b["proje_notu"] is True
            and os.stat(K.PROJE_NOTU).st_mode & 0o777 == 0o600 and nt.count("## Proje kartı (taslak)") == 1 and "Deneme projesi" in nt and open(os.path.join(P, "CLAUDE.md")).read() == "# Notlar\n", nt[:200])
    tcn = lambda: subprocess.run([sys.executable, "-B", os.path.join(KOD, "toplanti-claude.py"), "--dir", os.path.join(U, "canli"), "proje-notu"], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    o1 = tcn().stdout
    os.remove(K.PROJE_NOTU); open(os.path.join(P, "CLAUDE.md"), "w").write("# Notlar\n\n## Proje kartı (taslak)\nEski not satırı\n\n## Başka bölüm\nx\n")
    o2 = tcn().stdout; nt2 = open(K.PROJE_NOTU, encoding="utf-8").read() if os.path.exists(K.PROJE_NOTU) else ""
    kontrol("tc proje-notu: notu verir; not yoksa CLAUDE.md'deki eski taslak bölüm bir kez taşınır (yalnız o bölüm, 0600)", "Deneme projesi" in o1 and "Eski not satırı" in o2
            and nt2 == "## Proje kartı (taslak)\nEski not satırı\n" and os.stat(K.PROJE_NOTU).st_mode & 0o777 == 0o600 and "Başka bölüm" in open(os.path.join(P, "CLAUDE.md")).read(), o1[:120] + " | " + o2[:200])
    # Faz 11 Aşama 2: başka sağlayıcı (sahte OpenAI uyumlu sunucu; cevabı sahte claude üretir) ve hata → Claude Code yedeği
    GELEN, DURUM = [], {"kod": 200}
    class Sahte(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *a): pass
        def do_POST(self):
            g = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); GELEN.append(g)
            if DURUM["kod"] != 200: b = b'{"error":{"message":"overloaded"}}'; self.send_response(DURUM["kod"]); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
            r = json.loads(subprocess.run([SAHTE], input=g["messages"][-1]["content"], capture_output=True, text=True, env=dict(os.environ, SAYAC=os.path.join(T, "sayac-gemini.jsonl"))).stdout)
            b = json.dumps({"choices": [{"message": {"role": "assistant", "content": r["result"]}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1000, "completion_tokens": 100}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    so = socket.socket(); so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]; so.close()
    SV = http.server.ThreadingHTTPServer(("127.0.0.1", port), Sahte); threading.Thread(target=SV.serve_forever, daemon=True).start()
    os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = "deneme"
    def gm(model): return {"beyin": {"proje_karti": {"tur": "openai-uyumlu", "saglayici": "gemini", "adres": f"http://127.0.0.1:{port}/v1", "model": model, "fiyat": [1, 0.1, 10]}}}
    ayar_yaz(**gm("gemini-3.8-flash")); K3 = yukle(); n5 = len(cagri()); kay = os.path.join(U, "canli", "claude-cagri.jsonl"); k0 = sum(1 for _ in open(kay))
    kgm = K3.cikar(paralel=2); yk = [json.loads(l) for l in open(kay)][k0:]
    kontrol("başka sağlayıcı: belge başına çağrı JSON kipinde (özet düz), Claude çağrılmadı, kart aynı, kayıtta saglayici gemini + maliyet",
            len(GELEN) == kgm["belge"] + 2 and sum(1 for g in GELEN if g.get("response_format") == {"type": "json_object"}) == kgm["belge"] + 1 and len(cagri()) == n5  # +1: bozuk.md ilk cevabı bozuk → yeniden
            and kgm["ozet"].startswith("Deneme projesi") and kgm["model"] == "gemini-3.8-flash" and any(p["ad"] == "Kemal Demir" for p in kgm["kisiler"])
            and all(r["saglayici"] == "gemini" and r["model"] == "gemini-3.8-flash" and abs(r["maliyet"] - 0.002) < 1e-6 for r in yk) and len(yk) == len(GELEN), f"{len(GELEN)} istek, {len(cagri()) - n5} claude")
    DURUM["kod"] = 503; GELEN.clear(); ayar_yaz(**gm("gemini-yedek-deneme")); K4 = yukle(); n6 = len(cagri()); e = io.StringIO()
    with contextlib.redirect_stderr(e): ky = K4.cikar(paralel=1)
    kontrol("sağlayıcı 503 → her çağrı bir kez Claude Code'la (kart tam, günlükte BEYİN: yedek, kayıtta iki satır)", len(GELEN) == ky["belge"] + 1 and len(cagri()) - n6 == ky["belge"] + 1
            and ky["ozet"].startswith("Deneme projesi") and not ky["hatalar"] and e.getvalue().count("BEYİN: yedek — proje-karti") == ky["belge"] + 1, e.getvalue()[:300])
    ayar_yaz(**dict(gm("gemini-yedeksiz"), beyin={"proje_karti": dict(gm("gemini-yedeksiz")["beyin"]["proje_karti"], yedek=False)})); K5 = yukle(); n7 = len(cagri())
    with contextlib.redirect_stderr(io.StringIO()): kh = K5.cikar(paralel=1)
    kontrol("yedek: false → Claude'a düşmez, hata kartın hatalarında", len(cagri()) == n7 and kh["hatalar"] and "503" in kh["hatalar"][0][1], str(kh["hatalar"][:1]))
    SV.shutdown(); ayar_yaz()
    # veritabanı kipi
    vt = os.path.join(P, "kayit.db"); v = sqlite3.connect(vt); v.execute("CREATE TABLE kisi(ad, gorev)"); v.execute("INSERT INTO kisi VALUES('Zeynep Kaya', 'finans')"); v.commit(); v.close()
    ayar_yaz(veritabani={"yol": "kayit.db", "kisiler": "SELECT ad, gorev FROM kisi"}); K2 = yukle(); n4 = len(cagri())
    kv = K2.cikar()
    yeni = cagri()[n4:]
    kontrol("veritabanı kipi: kişiler veritabanından, belgelerden yalnız özet + sözlük istendi", kv["veritabani"]["kisiler"] == [["Zeynep Kaya", "finans"]] and kv["kisiler"] == []
            and yeni and not any(x["tam"] for x in yeni) and kv["sozluk"] and kv["veritabani"]["kararlar"] is None, json.dumps(kv.get("veritabani"), ensure_ascii=False))
finally:
    shutil.rmtree(T, ignore_errors=True)
print(f"proje kartı: {len(hatalar)} sorun" if hatalar else "proje kartı: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
