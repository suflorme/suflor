#!/usr/bin/env python3
# Kişilik (v0.53.0, aktarici/kisilik.py) uçtan uca, nötr örnek adla ("Atlas"; gerçek kişilik dosyası depoya girmez): /status konus.kisilik, kullanıcı satırında
# hitap → "Claude:" (karşı kanalda değil), toplantıya söyle'de ilk okumada kişiliğin tanıtımı + telaffuz satırı, ikinci okumada tanıtım yok; Konuş istemine
# kişilik metni (biçim kuralları önce, neşeli ünlem satırı çıkar); kişilik dosyası silinince nötr davranış, hata yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/kisilik.py
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8789  # 8793 sohbet testinin
T = tempfile.mkdtemp(prefix="kis-"); canli = os.path.join(T, "canli"); os.makedirs(canli); hata = []
def ok(ad, k): print(("✓ " if k else "✗ ") + ad); hata.append(not k)
kd = os.path.join(T, "kisilik.md")
open(kd, "w", encoding="utf-8").write("---\nad: Atlas\nhitap: Atlas, Atlaz\nokunus: Atlas\ntanitim: Merhaba, ben Atlas. Deneme şirketi adına konuşan bir asistanım.\n"
                                      "selam: Merhaba, ben Atlas.\ntelaffuz: Deneme şirketi=Denemee şirketi\n---\n## Kişilik: Atlas\nAdın Atlas. Siz diye hitap edersin. KİŞİLİK-İŞARETİ\n")
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "kisilik": kd, "toplantiya_ses": True}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py", "tur-isci.py"): shutil.copy(os.path.join(KOD, f), T)
for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(T, d))
log = os.path.join(T, "relay.log")
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay,
                     SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_TS_AYGIT="1"), stdout=open(log, "w"), stderr=subprocess.STDOUT)
L = lambda: open(log, encoding="utf-8").read()
try:
    for _ in range(60):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def uc(yol, v=None):
        q = urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode() if v is not None else None, headers={"X-Suflor-Anahtar": K})
        return json.loads(urllib.request.urlopen(q, timeout=10).read())
    ok("status: konuşma etiketi kişiliğin adı", uc("/status")["konus"].get("kisilik") == "Atlas")
    uc("/ping", {"meeting": {"title": "Kişilik deneme"}, "panel": True})  # çağrı bilgisi yok: BlackHole (deneme) yolu
    uc("/ingest", {"meeting": {"title": "Kişilik deneme"}, "source": "whisper", "entries": [
        {"id": "w/1", "speaker": "Deniz T", "time": "10:00:00", "text": "Atlas, bugün kaç toplantım var?", "kanal": "ben"},
        {"id": "w/2", "speaker": "Deniz T", "time": "10:00:10", "text": "Atlas markasının yeni ürünü güzel olmuş.", "kanal": "ben"},
        {"id": "k/1", "speaker": "Ayla Ö", "time": "10:00:20", "text": "Atlas, bize de bir özet çıkar.", "kanal": "karsi"}]})
    time.sleep(0.5); md = " ".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))
    ok("kullanıcı satırında hitap 'Claude:' oldu", "Claude: bugün kaç toplantım var?" in md)
    ok("hitap olmayan cümle değişmedi", "Atlas markasının yeni ürünü güzel olmuş." in md)
    ok("karşı kanaldaki ad hitap sayılmadı", "Atlas, bize de bir özet çıkar." in md and "Claude: bize" not in md)
    uc("/komut", {"tur": "soyle", "metin": "Toplantı yarın onda."})
    s1 = [l for l in L().splitlines() if "TOPLANTIYA SÖYLE (deneme)" in l]
    ok("toplantıya söyle: ilk okumada kişiliğin tanıtımı (telaffuz satırı uygulandı), nötr tanıtım yok",
       bool(s1) and "Merhaba, ben Atlas" in s1[-1] and "Denemee şirketi" in s1[-1] and "asistanı Suflor" not in s1[-1])
    uc("/komut", {"tur": "soyle", "metin": "İkinci cümle."})
    s2 = [l for l in L().splitlines() if "TOPLANTIYA SÖYLE (deneme)" in l]
    ok("ikinci okumada tanıtım yok", len(s2) == 2 and "Merhaba" not in s2[-1])
    # Konuş istemi (aktarıcının kendi tanımları; süreç açılmaz)
    src = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read(); ks = open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read()
    ns = {"re": re, "os": os, "json": json, "time": time, "print": lambda *a, **k: None, "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": canli, "AYAR": {"kisilik": kd}, "_KS": {}, "TOP": [False]}
    ns["toplanti_var"] = lambda: ns["TOP"][0]
    exec(ks, ns); exec(src[src.index("KONUS_ISTEM = {"):src.index("# --- Hızlı bilgi")], ns)
    ist = ns["konus_istem"]()
    ok("Konuş istemi: kişilik metni sonda, biçim kuralları önce, neşeli ünlem satırı çıktı",
       ist.endswith("KİŞİLİK-İŞARETİ") and "biçim kuralları" in ist.split("## Kişilik")[0][-400:] and "'Vay!'" not in ist and "en çok dört cümle" in ist and "Şey," not in ist)
    # v0.61.0: iki kişilik — toplantı dışı kişilik (ayar kisilik_toplanti_disi), adla seçim, toplantıda yalnız kulağa
    kd2 = os.path.join(T, "kisilik2.md")
    open(kd2, "w", encoding="utf-8").write("---\nad: Matlas\nhitap: Matlas, Oh Matlas\nhitap_bicimi: sen\nselam: Selam, ben Matlas.\ntelaffuz: Sir=sör\n---\n## Kişilik: Matlas\nAdın Matlas. Sen dersin. İKİNCİ-İŞARET\n")
    ns["AYAR"]["kisilik_toplanti_disi"] = kd2
    ist2 = ns["konus_istem"]()
    ok("iki kişilik: istemde ikisi de, açıklama satırı, biçim kuralları önce", "KİŞİLİK-İŞARETİ" in ist2 and ist2.endswith("İKİNCİ-İŞARET") and "Aşağıda iki kişilik var: Atlas toplantıda, Matlas toplantı dışında" in ist2)
    ok("toplantı yokken etkin kişilik ikincisi", ns["kisilik"]()["ad"] == "Matlas")
    ns["TOP"][0] = True; ok("toplantıda etkin kişilik birincisi", ns["kisilik"]()["ad"] == "Atlas")
    kb, kalan = ns["kisilik_hitap_bul"]("Matlas, bugün neler yaptım?"); ok("adla seslenme bulundu", kb and kb["ad"] == "Matlas" and kalan == "bugün neler yaptım?")
    kb, _ = ns["kisilik_hitap_bul"]("Atlas, özet?"); ok("birincinin adı da bulunur", kb and kb["ad"] == "Atlas")
    kb, _ = ns["kisilik_hitap_bul"]("Dün Matlas'la konuştum"); ok("cümle ortası ad seçmez", kb is None)
    ns["kisilik_sec"]("Matlas"); ok("adla seçilen kişilik toplantıda da sürer (süre içinde)", ns["kisilik"]()["ad"] == "Matlas")
    ok("'sen' diyen kişilikte kis_t nötr cümle", ns["kis_t"]("Söyler misin?", "Söyler misiniz?") == "Söyler misin?")
    ns["_KSEC"]["t"] -= ns["KISILIK_SURE_SN"] + 1; ok("süre dolunca varsayılana döner", ns["kisilik"]()["ad"] == "Atlas")
    ok("'siz' diyen kişilikte kis_t kişilikli cümle", ns["kis_t"]("Söyler misin?", "Söyler misiniz?") == "Söyler misiniz?")
    ok("telaffuz iki kişilikten", ns["kisilik_telaffuz"]("Tamam Sir, Deneme şirketi.") == "Tamam sör, Denemee şirketi.")
    ok("toplantıya söyleme isteği tanınır", all(ns["toplantiya_istendi"](x) for x in ("toplantıya söyle bunu", "herkese anlat lütfen", "bunu onlara söyle", "sesli söyle", "tell everyone")))
    ok("sıradan soru toplantıya söyleme isteği değil", not any(ns["toplantiya_istendi"](x) for x in ("bugün ne söyledim?", "toplantı kaçta bitiyor?", "Ali ne anlattı?")))
    ns["TOP"][0] = False; ns["AYAR"]["kisilik_toplanti_disi"] = ""
    ok("ikinci kaldırılınca tek kişilik (eski istem)", ns["konus_istem"]().endswith("KİŞİLİK-İŞARETİ") and ns["kisilik"]()["ad"] == "Atlas")
    ns["AYAR"]["kisilik"] = ""; ok("kişilik yokken istem nötr (ünlem satırı yerinde)", "'Vay!'" in ns["konus_istem"]() and "KİŞİLİK-İŞARETİ" not in ns["konus_istem"]())
    # kişilik dosyası silinince nötr
    os.remove(kd); time.sleep(0.2)
    ok("dosya silinince status nötr", uc("/status")["konus"].get("kisilik") is None)
    uc("/ingest", {"meeting": {"title": "Kişilik deneme"}, "source": "whisper", "entries": [{"id": "w/3", "speaker": "Deniz T", "time": "10:01:00", "text": "Atlas, yarın ne var?", "kanal": "ben"}]})
    time.sleep(0.5); md = " ".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))
    ok("dosya silinince ad hitap sayılmıyor, günlükte 'KİŞİLİK: okunamadı'", "Atlas, yarın ne var?" in md and "KİŞİLİK: okunamadı" in L())
    ok("aktarıcıda hata yok", "Traceback" not in L())
finally:
    r.terminate(); r.wait(5)
    if not any(hata): shutil.rmtree(T, ignore_errors=True)
    else: print("(deneme klasörü: " + T + ")")
print("kişilik:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
