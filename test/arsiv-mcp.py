#!/usr/bin/env python3
# Toplantı arşivi MCP sunucusu (arsiv-mcp.py): stdio üzerinden gerçek JSON-RPC — initialize, tools/list, okuma araçları, yazma araçlarında onay akışı,
# gizli toplantı (hiçbir araçta dönmez), anahtarsız/yanlış anahtarlı ret. Yalıtılmış deneme aktarıcısı + yapay arşiv; gerçek _canli ve 8765'e dokunmaz.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/arsiv-mcp.py      (kaldı → çıkış 1; ~6 sn)
import json, os, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8793)
sys.path.insert(0, KOD)
hata = []
def bak(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: hata.append(ad)
T = tempfile.mkdtemp(prefix="suflor-arsivmcp-"); canli = os.path.join(T, "canli"); os.makedirs(os.path.join(canli, "ozetler"))
for f in ("relay.py", "manifest.json"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici")); shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
BAS = "| Saat | Konuşmacı | Metin | İşaret |\n|---|---|---|---|\n"
def dokum(ad, baslik, satirlar):
    open(os.path.join(canli, ad + ".md"), "w", encoding="utf-8").write(f"# Canlı transkript — {baslik}\n\n" + BAS + "".join(f"| {s} | {k} | {m} | |\n" for s, k, m in satirlar))
D1, D2, G = "2026-10-20-1000-Depo-toplantisi", "2026-10-21-1430-Haftalik", "2026-10-22-0900-Ozel-gorusme"
dokum(D1, "Depo toplantısı", [("10:00:05", "Ayşe Deneme", "Stok sayımını cuma bitirelim.")] + [(f"10:{i // 60:02d}:{i % 60:02d}", "Can Örnek", f"Madde {i} konuşuldu.") for i in range(10, 400, 3)])
dokum(D2, "Haftalık", [("14:30:00", "Can Örnek", "Depo stok raporu hazır mı?")])
dokum(G, "Özel", [("09:00:00", "Ayşe Deneme", "Gizli maaş görüşmesi bordro"), ("09:00:10", "**GİZLİ**", "açıldı — kapanana kadar hiçbir şey kaydedilmez")])
oz = os.path.join(canli, "ozetler", "depo-ozeti.md"); open(oz, "w", encoding="utf-8").write("# Depo özeti\n\n## Kararlar\n- Envanter sayımı cuma tamamlanacak.\n")
goz = os.path.join(canli, "ozetler", "gizli-ozeti.md"); open(goz, "w", encoding="utf-8").write("# Gizli özet\n\n## Kararlar\n- bordro kararı\n")
dis = os.path.join(T, "dis-ozet.md"); open(dis, "w").write("dışarıdaki dosya")
open(os.path.join(canli, "son-toplantilar.jsonl"), "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in (
    {"id": "s1", "at": "2026-10-20T10:40:00", "baslik": "Depo toplantısı", "dosya": D1 + ".md", "ozet": oz, "kopya": oz},
    {"id": "s2", "at": "2026-10-21T15:00:00", "baslik": "Haftalık", "dosya": D2 + ".md", "ozet": dis, "kopya": dis},
    {"id": "s3", "at": "2026-10-22T10:00:00", "baslik": "Özel", "dosya": G + ".md", "ozet": goz, "kopya": goz})))
import yapi
def yapi_yaz(top, baslik, tarih, ogeler): yapi.graf_yaz(canli, {"baslik": baslik, "tarih": tarih, "maddeler": [{"baslik": "Gündem", "ogeler": ogeler}]}, top + ".md")
yapi_yaz(D1, "Depo toplantısı", "2026-10-20", [
    {"tur": "karar", "metin": "Sayım cuma yapılacak", "kim": "Ayşe Deneme", "netlik": "ortuk"}, {"tur": "karar", "metin": "Yeni raf alınacak", "kim": "Can Örnek", "netlik": "acik"},
    {"tur": "is", "metin": "Sayım listesini hazırla", "sahip": "Can Örnek", "tarih": "2026-10-23"}, {"tur": "soz", "metin": "Faturaları gönderecek", "sahip": "Ayşe Deneme", "tarih": "2026-01-05"},
    {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Can Örnek"}])
yapi_yaz(G, "Özel", "2026-10-22", [{"tur": "karar", "metin": "Bordro gizli kararı", "kim": "Ayşe Deneme"}, {"tur": "is", "metin": "Gizli iş", "sahip": "Ayşe Deneme"}, {"tur": "soru", "metin": "Gizli soru"}])
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Ayşe Deneme", "port": PORT, "uygulama": T, "proje": T, "ortak": T}, open(ay, "w"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT, env=env)
class MCP:
    def __init__(s, dizin=canli, port=PORT):
        s.p = subprocess.Popen([sys.executable, "-B", os.path.join(KOD, "arsiv-mcp.py"), "--dir", dizin, "--relay", f"http://127.0.0.1:{port}"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=dict(env, SUFLOR_AYAR=ay)); s.n = 0
    def gonder(s, yontem, params=None, bildirim=False):
        m = {"jsonrpc": "2.0", "method": yontem}
        if params is not None: m["params"] = params
        if not bildirim: s.n += 1; m["id"] = s.n
        s.p.stdin.write(json.dumps(m) + "\n"); s.p.stdin.flush()
        return None if bildirim else json.loads(s.p.stdout.readline())
    def arac(s, ad, **a):
        y = s.gonder("tools/call", {"name": ad, "arguments": a}); r = y["result"]
        return r["isError"], json.loads(r["content"][0]["text"])
    def kapat(s): s.p.stdin.close(); s.p.wait(timeout=5)
try:
    for _ in range(60):
        if "çalışıyor" in open(os.path.join(T, "relay.log"), encoding="utf-8").read(): break
        time.sleep(0.2)
    m = MCP()
    y = m.gonder("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "deneme", "version": "1"}})
    bak("initialize: istemcinin protokol sürümü, tools yeteneği, sunucu adı", y["result"]["protocolVersion"] == "2025-06-18" and "tools" in y["result"]["capabilities"] and y["result"]["serverInfo"]["name"] == "suflor-arsiv")
    m.gonder("notifications/initialized", bildirim=True)
    bak("ping", m.gonder("ping")["result"] == {})
    bak("bilinmeyen yöntem -32601", m.gonder("foo/bar")["error"]["code"] == -32601)
    ad = [t["name"] for t in m.gonder("tools/list")["result"]["tools"]]
    bak("tools/list: 7 okuma + 3 yazma aracı", len(ad) == 10 and {"toplanti_ara", "toplanti_listesi", "toplanti_ozeti", "toplanti_dokumu", "kararlar", "isler", "acik_sorular", "is_durumu", "karar_onayla", "karar_duzelt"} == set(ad))
    bak("bilinmeyen araç -32602", m.gonder("tools/call", {"name": "yok", "arguments": {}})["error"]["code"] == -32602)
    # okuma
    h, L = m.arac("toplanti_listesi")
    bak("liste: iki toplantı (gizli yok), yeniden eskiye", not h and [x["id"] for x in L["toplantilar"]] == [D2, D1])
    h, L = m.arac("toplanti_listesi", baslangic="2026-10-21")
    bak("liste: tarih aralığı", [x["id"] for x in L["toplantilar"]] == [D2])
    h, A = m.arac("toplanti_ara", sorgu="stok")
    bak("arama: 'stok' iki toplantıda", not h and sorted({x["id"] for x in A["sonuclar"]}) == [D1, D2])
    h, A = m.arac("toplanti_ara", sorgu="stok", baslangic="2026-10-21", bitis="2026-10-21")
    bak("arama: tarih aralığı süzer", [x["id"] for x in A["sonuclar"]] == [D2])
    h, A = m.arac("toplanti_ara", sorgu="bordro")
    bak("arama: gizli toplantı dönmez", not h and A["sonuclar"] == [])
    h, O = m.arac("toplanti_ozeti", id=D1)
    bak("özet: metin döner", not h and "Envanter sayımı" in O["ozet"])
    h, O = m.arac("toplanti_ozeti", id=D2)
    bak("özet: canlı klasör dışındaki kopya okunmaz", h and "özeti yok" in O["hata"])
    h, Dk = m.arac("toplanti_dokumu", id=D1, sayfa_boyutu=50)
    h2, Dk2 = m.arac("toplanti_dokumu", id=D1, sayfa=2, sayfa_boyutu=50)
    bak("döküm: sayfalı (50'şer satır, 2. sayfa farklı)", not h and Dk["toplam_satir"] == 131 and len(Dk["satirlar"]) == 50 and Dk["sayfa_sayisi"] == 3 and Dk2["satirlar"][0] != Dk["satirlar"][0]
        and Dk["satirlar"][0].startswith("10:00:05 Ayşe Deneme: Stok"))
    h, K = m.arac("kararlar")
    bak("kararlar: gizli toplantının kararı yok, teyit işareti var", not h and K["toplam"] == 2 and all("Bordro" not in x["metin"] for x in K["kararlar"]) and any("teyit bekliyor" in x["metin"] for x in K["kararlar"]))
    h, K = m.arac("kararlar", kisi="can")
    bak("kararlar: kişiye göre", [x["metin"] for x in K["kararlar"]] == ["Yeni raf alınacak"])
    h, K = m.arac("kararlar", id=D2)
    bak("kararlar: grafsız toplantı → boş", not h and K["toplam"] == 0)
    h, K = m.arac("kararlar", id=G)
    bak("kararlar: gizli toplantı kimliğiyle sorulunca bulunamadı", h and "bulunamadı" in K["hata"])
    h, I = m.arac("isler")
    bak("işler: açık iş ve söz, gizli iş yok; süresi geçen söz gecikti", not h and I["toplam"] == 2 and not any("Gizli" in x["metin"] for x in I["isler"]) and next(x for x in I["isler"] if x["tur"] == "soz")["gecikti"])
    h, I = m.arac("isler", kisi="can")
    bak("işler: kişiye göre", [x["metin"] for x in I["isler"]] == ["Sayım listesini hazırla"])
    h, Q = m.arac("acik_sorular")
    bak("açık sorular: gizli soru yok", not h and [x["metin"] for x in Q["sorular"]] == ["KDV dahil mi?"])
    # yazma: onay akışı
    sid = next(x["id"] for x in m.arac("isler", kisi="can")[1]["isler"])
    h, W = m.arac("is_durumu", id=sid, durum="yapildi")
    bak("is_durumu: ilk çağrı onay_gerekli, yazmaz", not h and W.get("onay_gerekli") is True and "ozet" in W and m.arac("isler", kisi="can")[1]["toplam"] == 1)
    h, W = m.arac("is_durumu", id=sid, durum="yapildi", onayla=True)
    bak("is_durumu: onayla true uygular", not h and W.get("uygulandi") is True and m.arac("isler", kisi="can")[1]["toplam"] == 0 and m.arac("isler", kisi="can", durum="yapildi")[1]["toplam"] == 1)
    import sqlite3
    c = sqlite3.connect(os.path.join(canli, "karar-grafi.sqlite")); gizli_is = c.execute("SELECT id FROM kayit WHERE metin = 'Gizli iş'").fetchone()[0]; c.close()
    h, W = m.arac("is_durumu", id=f"s{gizli_is}", durum="yapildi", onayla=True)
    bak("is_durumu: gizli toplantının işi bulunamadı, yazılmaz", h and "bulunamadı" in W["hata"])
    h, W = m.arac("is_durumu", id="x1", durum="yapildi")
    bak("is_durumu: geçersiz kimlik hata", h)
    kid = next(x["id"] for x in m.arac("kararlar")[1]["kararlar"] if "teyit" in x["metin"])
    h, W = m.arac("karar_onayla", id=kid)
    bak("karar_onayla: önce onay_gerekli", W.get("onay_gerekli") is True and any("teyit" in x["metin"] for x in m.arac("kararlar")[1]["kararlar"]))
    h, W = m.arac("karar_onayla", id=kid, onayla=True)
    bak("karar_onayla: işaret kalkar, metin korunur", W.get("uygulandi") is True and not any("teyit" in x["metin"] for x in m.arac("kararlar")[1]["kararlar"]) and "Sayım cuma yapılacak" in [x["metin"] for x in m.arac("kararlar")[1]["kararlar"]])
    h, W = m.arac("karar_duzelt", id=kid, metin="Sayım perşembe yapılacak")
    bak("karar_duzelt: önce onay_gerekli", W.get("onay_gerekli") is True and "Sayım cuma yapılacak" in [x["metin"] for x in m.arac("kararlar")[1]["kararlar"]])
    h, W = m.arac("karar_duzelt", id=kid, metin="Sayım perşembe yapılacak", onayla=True)
    bak("karar_duzelt: onayla true uygular", W.get("uygulandi") is True and "Sayım perşembe yapılacak" in [x["metin"] for x in m.arac("kararlar")[1]["kararlar"]])
    # anahtar
    m.kapat()
    os.rename(os.path.join(canli, "kart-anahtari.txt"), os.path.join(canli, "kart-anahtari.bak"))
    m2 = MCP(); m2.gonder("initialize", {"protocolVersion": "2025-06-18"})
    h, E = m2.arac("toplanti_listesi")
    bak("anahtarsız: araç hata verir, veri dönmez", h and "anahtar" in E["hata"] and "toplantilar" not in E); m2.kapat()
    shutil.copy(os.path.join(canli, "kart-anahtari.bak"), os.path.join(canli, "kart-anahtari.txt"))
    d2 = os.path.join(T, "canli-yanlis"); os.makedirs(d2); open(os.path.join(d2, "kart-anahtari.txt"), "w").write("yanlis-anahtar")
    m3 = MCP(d2); m3.gonder("initialize", {"protocolVersion": "2025-06-18"})
    h, E = m3.arac("toplanti_listesi")
    bak("yanlış anahtar: aktarıcı 401 → hata", h and "reddetti" in E["hata"]); m3.kapat()
    m4 = MCP(canli, 1); m4.gonder("initialize", {"protocolVersion": "2025-06-18"})
    h, E = m4.arac("toplanti_listesi")
    bak("aktarıcı kapalı: anlaşılır hata", h and "yanıt vermiyor" in E["hata"]); m4.kapat()
    kd = subprocess.run([sys.executable, "-B", os.path.join(KOD, "arsiv-mcp.py"), "--relay", "http://example.com:80"], capture_output=True, text=True)
    bak("uzak aktarıcı adresi reddedilir", kd.returncode != 0)
finally:
    r.terminate()
    try: r.wait(timeout=5)
    except Exception: r.kill()
    shutil.rmtree(T, ignore_errors=True)
print("kaldı: " + ", ".join(hata) if hata else "hepsi geçti"); sys.exit(1 if hata else 0)
