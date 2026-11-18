# beta #57 (17 Kasım): iki eşzamanlı Başlat — (1) _json_yaz_esz aynı dosyaya eşzamanlı yazımda FileNotFoundError vermemeli, geçici dosya bırakmamalı;
# (2) baslat sırayla çalışmalı (BASLAT_KILIT): aynı anda iki _baslat gövdesi çalışmaz, aynı iş parçacığından iç içe çağrı kilitlenmez.
import ast, json, os, sys, tempfile, threading, time
KOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relay.py")
agac = ast.parse(open(KOD, encoding="utf-8").read())
def parca(adlar):
    dugum = [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in adlar)
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in adlar for t in n.targets))]
    assert len(dugum) == len(adlar), f"bulunamadı: {adlar}"
    return ast.Module(dugum, [])
def yaz_dene(yaz, n=8, tur=300):
    d = tempfile.mkdtemp(); hedef = os.path.join(d, "agenda.json"); hata = []
    def is_():
        for i in range(tur):
            try: yaz(hedef, {"i": i})
            except Exception as e: hata.append(e)
    T = [threading.Thread(target=is_) for _ in range(n)]; [t.start() for t in T]; [t.join() for t in T]
    return hata, [x for x in os.listdir(d) if x.endswith(".tmp")], json.load(open(hedef))
def eski_yaz(fp, veri):  # v0.250.4'e kadarki kalıp (gundem_yeni_konu, takvim-secilen.json)
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(veri, f)
    os.replace(tmp, fp)
ok = True
h, _, _ = yaz_dene(eski_yaz); print(f"eski kalıp: {len(h)} hata ({type(h[0]).__name__ if h else '-'})")
g = {"os": os, "threading": threading, "json": json}; exec(compile(parca(["gecici_ad", "dosya_yaz_esz", "_json_yaz_esz"]), KOD, "exec"), g)
h, artik, son = yaz_dene(g["_json_yaz_esz"])
print(f"yeni kod (_json_yaz_esz): {len(h)} hata, {len(artik)} artık geçici dosya, son içerik geçerli JSON {isinstance(son, dict)}"); ok &= not h and not artik
# genel yardımcı dosya_yaz_esz (relay.py + aktarici/*.py): 8 iş parçacığı × 300 yazım — metin, ikili, json (kwargs), izin korunur, hata olursa geçici dosya kalmaz
dy = g["dosya_yaz_esz"]
for ad, icerik, kw, izin, beklenen in (("m.txt", "merhaba ü\n", {}, None, "merhaba ü\n"), ("b.bin", b"\x00\x01\xff", {}, None, b"\x00\x01\xff"),
                                      ("j.json", {"ü": [1, 2]}, dict(ensure_ascii=False, indent=1), 0o600, '{\n "ü": [\n  1,\n  2\n ]\n}'), ("k.json", {"ü": 1}, {}, 0o600, '{"\\u00fc": 1}')):
    d = tempfile.mkdtemp(); hedef = os.path.join(d, ad); hata = []
    def is_(hedef=hedef, icerik=icerik, kw=kw, izin=izin):
        for i in range(300):
            try: dy(hedef, icerik, izin, **kw)
            except Exception as e: hata.append(e)
    T = [threading.Thread(target=is_) for _ in range(8)]; [t.start() for t in T]; [t.join() for t in T]
    artik = [x for x in os.listdir(d) if x != ad]
    oku = open(hedef, "rb").read(); oku = oku if isinstance(beklenen, bytes) else oku.decode("utf-8")
    im = oct(os.stat(hedef).st_mode & 0o777)
    iyi = not hata and not artik and oku == beklenen and (izin is None or im == "0o600")
    print(f"dosya_yaz_esz {ad}: {len(hata)} hata, {len(artik)} artık, içerik {'tamam' if oku == beklenen else 'FARKLI'}, izin {im}"); ok &= iyi
d = tempfile.mkdtemp()
try: dy(os.path.join(d, "yok", "x.json"), {"a": 1}); ok = False
except OSError: pass
try: dy(os.path.join(d, "x.json"), {"a": object()}); ok = False
except TypeError: pass
artik = os.listdir(d); print(f"hata yolu: artık geçici dosya {artik}"); ok &= artik == [] or artik == ["yok"]

g = {"threading": threading}; exec(compile(parca(["BASLAT_KILIT", "baslat"]), KOD, "exec"), g)
say = {"en": 0, "cagri": 0}; ic = {}; kl = threading.Lock()
def sahte(p):
    me = threading.get_ident()
    with kl: ic[me] = ic.get(me, 0) + 1; say["en"] = max(say["en"], sum(1 for v in ic.values() if v)); say["cagri"] += 1  # iş parçacığı sayısı (iç içe çağrı aynı iş parçacığı)
    time.sleep(0.05)
    if p.get("ic"): g["baslat"]({})  # aynı iş parçacığından iç içe çağrı (RLock) kilitlenmemeli
    with kl: ic[me] -= 1
    return {"ok": True}
g["_baslat"] = sahte
T = [threading.Thread(target=g["baslat"], args=({"ic": i == 0},), daemon=True) for i in range(6)]; [t.start() for t in T]; [t.join(5) for t in T]
asili = sum(t.is_alive() for t in T)
print(f"baslat: aynı anda en çok {say['en']} iş parçacığında gövde, {say['cagri']} çağrı, {asili} asılı iş parçacığı")
ok &= say["en"] == 1 and say["cagri"] == 7 and not asili
print("TAMAM" if ok else "HATA"); sys.exit(0 if ok else 1)
