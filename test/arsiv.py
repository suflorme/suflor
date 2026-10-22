#!/usr/bin/env python3
# Toplantı arşivi (aktarici/arsiv.py, v0.116.0): /toplantilar listesi, /toplantilar?q= araması (kök eşleşmesi, bütün sözcükler, özet satırları,
# vurgu parçaları), /toplantilar/dokum dökümü; anahtarsız 401, geçersiz kimlik. Yalıtılmış aktarıcı + yapay dökümler; gerçek _canli'ye dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/arsiv.py      (kaldı → çıkış 1; ~5 sn)
import json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8771)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-arsiv-"); canli = os.path.join(T, "canli"); os.makedirs(os.path.join(canli, "ozetler"))
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def dokum(ad, baslik, satirlar):
    open(os.path.join(canli, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {baslik}\n\n**Başlangıç: …**\n\n" + BAS
        + "".join(f"| {s} | {k} | {m} | |\n" for s, k, m in satirlar))
dokum("2026-10-20-1000-Depo-toplantisi", "Depo toplantısı", [("10:00:05", "Ayşe Deneme", "Stok sayımını cuma bitirelim."),
      ("10:01:10", "Can Örnek", "Sözlüğe yeni ürün adlarını ekledim."), ("10:02:00", "**CLAUDE · NOT**", "Karar: sayım cuma."), ("10:31:00", "Ayşe Deneme", "Tamam.")])
dokum("2026-10-21-1430-Haftalik", "Haftalık", [("14:30:00", "Can Örnek", "Sözler defterine bakalım."), ("14:31:00", "Ayşe Deneme", "Depo stok raporu hazır mı?")])
dokum("2026-10-21-1500-Bos", "Boş", [])
dokum("2026-10-21-1600-Notlu", "Toplantı", [("16:00:00", "**NOT**", "toplantısızken yazılan not")])  # konuşma yok, özet yok: listeye girmez
open(os.path.join(canli, "2026-10-21-1500-Bos.ceviri.jsonl"), "w").write("{}\n")  # yan dosya: listeye girmez
oz = os.path.join(canli, "ozetler", "depo-ozeti.md")
open(oz, "w", encoding="utf-8").write("# Depo toplantısı özeti\n\n## Kararlar\n- Envanter sayımı cuma tamamlanacak.\n")
open(os.path.join(canli, "son-toplantilar.jsonl"), "w", encoding="utf-8").write(json.dumps({"id": "s1", "at": "2026-10-20T10:40:00", "baslik": "Depo toplantısı (özetli)",
     "dosya": "2026-10-20-1000-Depo-toplantisi.md", "ozet": oz, "kopya": oz}, ensure_ascii=False) + "\n"
     + "".join(json.dumps({"id": f"x{i}", "at": "2026-10-20T11:00:00", "baslik": "Eski", "dosya": f"2026-10-01-0{i % 10}00-Yok.md", "ozet": "/yok.md"}) + "\n" for i in range(22)))
     # 22 kayıt daha: s1 aktarıcının bellekteki son 20 kaydının dışında kalır (arşivden "Özeti aç" yedek yolu)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
def gonder(yol, govde):
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(govde).encode(), method="POST",
        headers={"X-Suflor-Anahtar": open(os.path.join(canli, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{PORT}", "Content-Type": "application/json"})
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except urllib.error.HTTPError as e: return {"_kod": e.code}
def al(yol, anahtar=True):
    q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", headers={"X-Suflor-Anahtar": open(os.path.join(canli, "kart-anahtari.txt")).read().strip()} if anahtar else {})
    try: return json.loads(urllib.request.urlopen(q, timeout=10).read())
    except urllib.error.HTTPError as e: return {"_kod": e.code}
try:
    for _ in range(60):
        if "çalışıyor" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): break
        time.sleep(0.2)
    bak("anahtarsız /toplantilar 401", al("/toplantilar", False).get("_kod") == 401)
    bak("anahtarsız /toplantilar/dokum 401", al("/toplantilar/dokum?id=2026-10-21-1430-Haftalik", False).get("_kod") == 401)
    L = al("/toplantilar"); ls = L.get("toplantilar") or []
    bak("liste: iki toplantı, yeniden eskiye; boş döküm, yalnız not olan dosya ve yan dosya yok", [x["id"] for x in ls] == ["2026-10-21-1430-Haftalik", "2026-10-20-1000-Depo-toplantisi"])
    d0 = next((x for x in ls if x["id"].endswith("Depo-toplantisi")), {})
    bak("liste: özet kaydının başlığı, özet kimliği, süre, konuşan satır ve kişiler", d0.get("baslik") == "Depo toplantısı (özetli)" and d0.get("ozet") == "s1"
        and d0.get("sure_dk") == 31 and d0.get("satir") == 3 and d0.get("kisiler") == ["Ayşe Deneme", "Can Örnek"] and d0.get("at") == "2026-10-20T10:00")
    bak("liste: özetsiz toplantıda başlık dökümden", next((x for x in ls if x["id"].endswith("Haftalik")), {}).get("baslik") == "Haftalık" and ls[0].get("ozet") is None)
    def ara(q): return al("/toplantilar?q=" + urllib.parse.quote(q))
    a = ara("sözlük")
    bak("arama: 'sözlük' kökü 'Sözlüğe'yi bulur, 'Sözler'i bulmaz", [x["saat"] for x in a.get("sonuclar") or []] == ["10:01:10"])
    a = ara("depo stok")
    bak("arama: bütün sözcükleri içeren satır ('depo stok' → yalnız 14:31)", a.get("tam") is True and [x["saat"] for x in a["sonuclar"]] == ["14:31:00"])
    v = [p[0] for p in a["sonuclar"][0]["parcalar"] if p[1]] if a.get("sonuclar") else []
    bak("arama: vurgu parçaları eşleşen sözcükler", v == ["Depo", "stok"] and "".join(p[0] for p in a["sonuclar"][0]["parcalar"]) == "Depo stok raporu hazır mı?")
    a = ara("envanter")
    bak("arama: özet satırı bulunur (özet: true, saat yok)", [(x["ozet"], x["saat"], x["id"]) for x in a.get("sonuclar") or []] == [(True, "", "2026-10-20-1000-Depo-toplantisi")])
    bak("arama: sonuçta özet kimliği (özetten açılır)", (a.get("sonuclar") or [{}])[0].get("ozet_id") == "s1")
    o = gonder("/son-ac", {"id": "s1", "tur": ""})
    bak("Özeti aç: bellekteki son 20'nin dışındaki toplantı da açılır", o.get("ok") is True and "AÇ (deneme): özet depo-ozeti.md" in open(os.path.join(T, "relay.log"), encoding="utf-8").read())
    a = ara("kararlar")
    bak("arama: özet başlığı sonuç olmaz", not any(x["ozet"] for x in a.get("sonuclar") or []))
    a = ara("sayım xyzw")
    bak("arama: hiçbir satır hepsini içermiyorsa en çok sözcük içerenler (tam: false)", a.get("tam") is False and len(a.get("sonuclar") or []) >= 2)
    bak("arama: boş sorgu boş sonuç", ara("  ").get("sonuclar") == [] or "toplantilar" in ara("  "))
    d = al("/toplantilar/dokum?id=2026-10-20-1000-Depo-toplantisi")
    bak("döküm: satırlar, sistem satırı işaretli, özet kimliği", d.get("ok") and len(d["satirlar"]) == 4 and d["satirlar"][2]["sistem"] is True
        and d["satirlar"][2]["kim"] == "CLAUDE · NOT" and d.get("ozet") == "s1")
    bak("döküm: geçersiz kimlik reddedilir", al("/toplantilar/dokum?id=" + urllib.parse.quote("../ayar")).get("ok") is False)
    bak("döküm: olmayan toplantı", al("/toplantilar/dokum?id=2026-10-21-0000-Yok").get("ok") is False)
    log = open(os.path.join(T, "relay.log"), encoding="utf-8").read()
    bak("aktarıcıda hata yok", "Traceback" not in log)
finally: r.terminate(); r.wait(5); shutil.rmtree(T, ignore_errors=True)
print("arşiv: ✓ hepsi geçti" if not hata else f"arşiv: ✗ {len(hata)} kaldı")
sys.exit(1 if hata else 0)
