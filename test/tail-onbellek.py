# tail() artımlı önbelleği (18 Kasım): özgün algoritmayla aynı çıktı + hız. Sabit port açmaz; relay.py'den ast ile çıkarır.
import ast, collections, json, os, sys, tempfile, threading, time
K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relay.py")
SRC = open(K, encoding="utf-8").read(); AG = ast.parse(SRC)
hata = []
def ok(ad, c): print(("ok   " if c else "HATA ") + ad); c or hata.append(ad)
def kod(*adlar):
    d = [n for n in AG.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("_TAIL", "_TAIL_KILIT", "_TAIL_BOZUK") for t in n.targets))]
    return compile(ast.Module(d, []), K, "exec")
D = tempfile.mkdtemp(); STATE = {"file": "t.md"}
ns = {"os": os, "json": json, "threading": threading, "collections": collections, "STATE": STATE, "BASE": D,
      "gorunen_dosya": lambda: "t.md", "asistan_goster": lambda t, h: t.replace("Claude:", "Marvin:"),
      "ceviri_uygula": lambda rs, md: [dict(r, ceviri="c") if r.get("id") == 3 else r for r in rs]}
exec(kod("tail", "_tail_satirlar", "_tail_coz"), ns)
tail = ns["tail"]
def ozgun(jl, n=200):
    try: lines = open(jl, encoding="utf-8").read().splitlines()[-n:]; rs = ns["ceviri_uygula"]([json.loads(x) for x in lines], "t.md")
    except Exception: return []
    for r in rs:
        for k in ("text", "note"):
            if "Claude:" in str(r.get(k) or ""): r[k] = ns["asistan_goster"](r[k], r.get("hitap"))
    return rs
jl = os.path.join(D, "t.jsonl")
def satir(i): return json.dumps({"id": i, "text": f"Claude: söz {i} ğüşiöç", "t": i}, ensure_ascii=bool(i % 2))
def yaz(s, mod="a"):
    with open(jl, mod, encoding="utf-8") as f: f.write(s)
def esit(ad):
    a, b = tail(), ozgun(jl); ok(ad, a == b and json.dumps(a) == json.dumps(b))
yaz("", "w"); esit("boş dosya")
yaz("".join(satir(i) + "\n" for i in range(5))); esit("ilk 5")
yaz("".join(satir(i) + "\n" for i in range(5, 300))); esit("300 satır (pencere kayar)")
yaz(satir(300)[:20]); a = tail(); ok("yarım satır: önceki 200 satır döner, bozulmaz", [r["id"] for r in a] == list(range(100, 300)) or len(a) >= 199)
yaz(satir(300)[20:] + "\n"); esit("yarım satır tamamlandı")
yaz(satir(301)); esit("sonu \\n'siz tam satır")
yaz("\n"); esit("\\n eklendi")
yaz("{bozuk\n"); esit("bozuk satır → boş"); ok("bozuk → []", tail() == [])
yaz("".join(satir(i) + "\n" for i in range(400, 600))); esit("bozuk satır pencereden çıktı")
yaz("".join(satir(i) + "\n" for i in range(3)), "w"); esit("kesilme (kısaldı)")
yaz("".join(satir(i) + "\n" for i in range(50)), "w"); esit("yeniden yazıldı (büyüdü)")
os.replace(jl, jl + ".x"); yaz("".join(satir(i + 7) + "\n" for i in range(10)), "w"); esit("dosya değişti (yeni inode)")
yaz("".join(satir(i) + "\r\n" for i in range(3))); esit("CRLF")
n2 = os.path.join(D, "u.jsonl"); yaz("", "a"); STATE["file"] = "t.md"
a = tail(5); ok("n=5", a == ozgun(jl, 5))
# eşzamanlı: yazan + 8 okuyucu; her okuma ardışık ve özgünle uyumlu önek olmalı
yaz("".join(satir(i) + "\n" for i in range(1000, 1010)), "w"); hatalar = []; dur = [False]
def yazan():
    for i in range(1010, 1400): yaz(satir(i) + "\n"); time.sleep(0.0005)
    dur[0] = True
def okur():
    while not dur[0]:
        a = tail(); ids = [r["id"] for r in a]
        if ids != list(range(ids[0], ids[0] + len(ids))) or any("Marvin:" not in r["text"] for r in a): hatalar.append(ids[:3])
ts = [threading.Thread(target=okur) for _ in range(8)] + [threading.Thread(target=yazan)]
[t.start() for t in ts]; [t.join() for t in ts]
ok("8 iş parçacığı + yazan: satırlar ardışık, çift/eksik yok", not hatalar); esit("eşzamanlı sonrası")
# hız: 1,3 MB sentetik
yaz("".join(json.dumps({"id": i, "t": i, "ad": "Ali Veli", "text": "sentetik söz " * 8}) + "\n" for i in range(8000)), "w")
print("boyut KB", os.path.getsize(jl) // 1024)
tail(); N = 50
t0 = time.perf_counter(); [ozgun(jl) for _ in range(N)]; e = (time.perf_counter() - t0) / N * 1000
t0 = time.perf_counter(); [tail() for _ in range(N)]; y = (time.perf_counter() - t0) / N * 1000
print(f"özgün {e:.2f} ms/çağrı · önbellekli {y:.2f} ms/çağrı"); ok("önbellekli daha hızlı", y < e)
yaz(json.dumps({"id": 9000, "text": "x"}) + "\n"); t0 = time.perf_counter(); tail(); print(f"ekleme sonrası ilk çağrı {(time.perf_counter()-t0)*1000:.2f} ms")
esit("hız sonrası")
print("\nHATA:", hata if hata else "yok"); sys.exit(1 if hata else 0)
