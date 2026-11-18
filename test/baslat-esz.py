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
g = {"os": os, "threading": threading, "json": json}; exec(compile(parca(["_json_yaz_esz"]), KOD, "exec"), g)
h, artik, son = yaz_dene(g["_json_yaz_esz"])
print(f"yeni kod: {len(h)} hata, {len(artik)} artık geçici dosya, son içerik geçerli JSON {isinstance(son, dict)}"); ok &= not h and not artik

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
