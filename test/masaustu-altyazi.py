#!/usr/bin/env python3
# Masaüstü Teams canlı altyazısı (13 Kasım, aktarici/masaustu-altyazi.py + menu-cubugu.swift MasaustuAltyazi).
#   P) saf birleştirme (ma_birlestir): sistem satırı atılır, büyüyen girdi tek satır olarak sabitlenince gider, aynı görüntü yinelenince satır çoğalmaz,
#      Teams öğeyi yeniden kurunca (yeni ax) aynı kimlik, dış katılımcı etiketi ad sayılmaz, ekrandan düşen girdi kaybolmaz, aynı kişinin aynı başlı iki girdisi ayrı.
#   A) yalıtılmış aktarıcı: masaüstü toplantı + POST /masaustu-altyazi → .jsonl/.md'ye "captions" kaynağı ve konuşmacıyla, çift satır yok; kayıt
#      kaynaklarında altyazı; ayar masaustu_altyazi: false → uç "kapali", satır yazılmaz; "yok" bildirimi günlükte toplantı başına bir kez.
#   W) süreç içi aktarıcı: Whisper o kanalda akarken satır gölgeye (.altyazi.log) gider ve kümeye ad oyu verir; Whisper yokken ana döküme düşer.
# Metinler uydurma (gerçek döküm alıntısı yok). Koşturma (~35 sn, model gerekmez): PYTHONDONTWRITEBYTECODE=1 python3 test/masaustu-altyazi.py
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HATA = []
def ok(ad, k, ek=""):
    print(("✓ " if k else "✗ ") + ad + (f" — {ek}" if ek and not k else ""), flush=True)
    if not k: HATA.append(ad)

# --- P) saf işlev ---------------------------------------------------------------------------------------------------------------------------------------
NS = {"threading": threading}
exec(compile(open(os.path.join(KOD, "aktarici", "masaustu-altyazi.py"), encoding="utf-8").read(), "masaustu-altyazi.py", "exec"), NS)
ma_yeni, birles = NS["ma_yeni"], NS["ma_birlestir"]
G = lambda ax, *m: {"ax": ax, "m": list(m)}
d = ma_yeni(); t = 1000.0
f, ts = birles(d, [G(1, "Döküm başlatıldı. Alt yazılar artık devam edecek."), G(2, "Ali T dökümü başlattı")], t)
ok("P1 tek metinli sistem satırları atılır", not f and not ts and not d["pending"])
f, ts = birles(d, [G(3, "Ali T", "Bugün")], t + 0.0)
ok("P2a büyüyen girdi önce taslak", not f and len(ts) == 1 and ts[0]["speaker"] == "Ali T")
for i, m in enumerate(["Bugün bütçe", "Bugün bütçe konusunu", "Bugün, bütçe konusunu konuşalım."]): f, _ = birles(d, [G(3, "Ali T", m)], t + 1 + i)
ok("P2b konuşulurken (son girdi 2×3 sn) gönderilmez", not f)
f, _ = birles(d, [G(3, "Ali T", "Bugün, bütçe konusunu konuşalım.")], t + 3 + 6.1)
ok("P2c sabitlenince tek satır, tam metin", len(f) == 1 and f[0]["text"] == "Bugün, bütçe konusunu konuşalım." and f[0]["speaker"] == "Ali T" and f[0]["time"], str(f))
i1 = f[0]["id"] if f else None
fs = [birles(d, [G(3, "Ali T", "Bugün, bütçe konusunu konuşalım.")], t + 10 + k)[0] for k in range(4)]
ok("P3 aynı görüntü 4 kez daha okunur: yeni satır yok", not any(fs))
f, _ = birles(d, [G(30, "Ali T", "Bugün, bütçe konusunu konuşalım."), G(4, "Ayşe K", "Dış bilinmeyen", "Olur, rakamları")], t + 15)
ok("P4 Teams öğeyi yeniden kurdu (yeni ax, aynı metin): aynı kimlik, satır yok", not f and d["tok"][30]["id"] == i1, str(d["tok"].get(30)))
f, _ = birles(d, [G(30, "Ali T", "Bugün, bütçe konusunu konuşalım."), G(4, "Ayşe K", "Dış bilinmeyen", "Olur, rakamları getiririm."), G(5, "Ali T", "Tamam")], t + 16)
f, _ = birles(d, [G(30, "Ali T", "Bugün, bütçe konusunu konuşalım."), G(4, "Ayşe K", "Dış bilinmeyen", "Olur, rakamları getiririm."), G(5, "Ali T", "Tamam")], t + 19.2)
ok("P5 üstteki girdi 3 sn'de sabitlenir; dış katılımcı etiketi ad değil, söz son metin", [(x["speaker"], x["text"]) for x in f] == [("Ayşe K", "Olur, rakamları getiririm.")], str(f))
f, _ = birles(d, [G(4, "Ayşe K", "Dış bilinmeyen", "Olur, rakamları getiririm.")], t + 20)
ok("P6 ekrandan düşen, sabitlenmemiş girdi kaybolmaz (son hâliyle)", [(x["text"], x.get("flush")) for x in f] == [("Tamam", True)], str(f))
f, _ = birles(d, [G(6, "Ayşe K", "Peki o zaman yarın"), G(7, "Ayşe K", "Peki o zaman cuma")], t + 30)
ok("P7 aynı kişinin aynı başlı iki girdisi iki ayrı kimlik", d["tok"][6]["id"] != d["tok"][7]["id"])
f, _ = birles(d, [G(6, "Ayşe K", "Peki o zaman yarın"), G(7, "Ayşe K", "Peki o zaman cuma")], t + 36.5)
ok("P8 ikisi de sabitlenir (iki satır)", len(f) == 2 and {x["text"] for x in f} == {"Peki o zaman yarın", "Peki o zaman cuma"}, str(f))
f, _ = birles(d, [G(7, "Ayşe K", "Peki o zaman cuma, saat onda.")], t + 37)
f, _ = birles(d, [G(7, "Ayşe K", "Peki o zaman cuma, saat onda.")], t + 44)
ok("P9 gönderildikten sonra büyüyen girdi düzeltme olarak (revised) bir kez", len(f) == 1 and f[0].get("revised") is True and f[0]["text"].endswith("onda."), str(f))

# --- A) yalıtılmış aktarıcı ------------------------------------------------------------------------------------------------------------------------------
class Aktarici:
    def __init__(self, ayar_ek=None):
        self.T = os.path.realpath(tempfile.mkdtemp(prefix="masaustu-altyazi-")); self.canli = os.path.join(self.T, "canli"); os.makedirs(self.canli)
        self.port = bos_port(8783); self.U = f"http://127.0.0.1:{self.port}"; self.log = os.path.join(self.T, "relay.log")
        json.dump({"alan": "Deneme", "ad": "Ali T", "port": self.port, "uygulama": self.T, "ortak": self.T, "konusma": False, **(ayar_ek or {})}, open(os.path.join(self.T, "ayar.json"), "w"))
        json.dump({"durum": "ok", "olaylar": []}, open(os.path.join(self.T, "takvim.json"), "w"))
        for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py"): shutil.copy(os.path.join(KOD, f), self.T)
        for d in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, d), os.path.join(self.T, d))
        self.p = subprocess.Popen([sys.executable, "relay.py", "--dir", self.canli, "--port", str(self.port)], cwd=self.T, stdout=open(self.log, "a"), stderr=subprocess.STDOUT,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=os.path.join(self.T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTO="1", SUFLOR_TEST_HIZLI="1"))
        for _ in range(100):
            try: self.istek("/status"); return
            except Exception: time.sleep(0.1)
    def kapat(self): self.p.terminate(); self.p.wait(5); shutil.rmtree(self.T, ignore_errors=True)
    def istek(self, yol, g=None):
        k = open(os.path.join(self.canli, "kart-anahtari.txt")).read().strip()
        q = urllib.request.Request(self.U + yol, data=json.dumps(g).encode() if g is not None else None, headers={"Content-Type": "application/json", "X-Suflor-Anahtar": k})
        return json.load(urllib.request.urlopen(q, timeout=10))
    def altyazi(self, girdiler): return self.istek("/masaustu-altyazi", {"girdiler": girdiler})
    def jl(self):
        out = []
        for f in glob.glob(os.path.join(self.canli, "*.jsonl")):
            out += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        return [r for r in out if r.get("text")]
    def md(self): return "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(self.canli, "*.md")))
    def gunluk(self): return open(self.log, encoding="utf-8").read()

R = Aktarici()
try:
    R.istek("/masaustu", {"uygulama": "Teams", "toplantida": True}); time.sleep(0.5)
    ekran = [G(11, "Ali T", "Merhaba, başlayalım mı?"), G(12, "Ayşe K", "Dış bilinmeyen", "Evet, hazırım.")]
    t0 = time.time(); r = None
    while time.time() - t0 < 7.5: r = R.altyazi(ekran); time.sleep(1.0)  # menü uygulaması gibi ~1 sn'de bir aynı görüntü
    ok("A1 uç bekleyen satır sayısını döner", isinstance(r, dict) and r.get("ok") is True and "bekleyen" in r, str(r))
    rows = R.jl()
    ok("A-2 iki satır .jsonl'e captions kaynağı ve konuşmacıyla", sorted((x["speaker"], x["text"], x["src"]) for x in rows) == [("Ali T", "Merhaba, başlayalım mı?", "captions"), ("Ayşe K", "Evet, hazırım.", "captions")], str(rows))
    for _ in range(3): R.altyazi(ekran); time.sleep(0.3)
    ok("A3 aynı görüntü yinelenince çift satır yok", len(R.jl()) == 2, str(len(R.jl())))
    ok("A4 .md'de konuşmacılı satır, etiket ad olarak yok", "| Ayşe K | Evet, hazırım." in R.md() and "Dış bilinmeyen" not in R.md())
    st = R.istek("/status").get("toplanti") or {}
    ok("A5 masaüstü toplantı kaydının kaynaklarında altyazı (captions)", "altyazi" in (st.get("kaynaklar") or {}), str(st.get("kaynaklar")))
    R.istek("/masaustu-altyazi", {"durum": "yok"}); R.istek("/masaustu-altyazi", {"durum": "yok"}); time.sleep(0.3)
    ok("A6 'altyazı bulunamadı' toplantı başına bir kez günlükte", R.gunluk().count("MASAÜSTÜ ALTYAZI: altyazı bulunamadı") == 1)
    ok("A7 aktarıcıda hata yok", "Traceback" not in R.gunluk(), R.gunluk()[-800:])
finally: R.kapat()

R = Aktarici({"masaustu_altyazi": False})
try:
    R.istek("/masaustu", {"uygulama": "Teams", "toplantida": True}); time.sleep(0.3)
    r = R.altyazi([G(1, "Ayşe K", "Bu yazılmamalı.")])
    ok("K1 ayar kapalı: uç 'kapali' döner, satır yazılmaz", r.get("kapali") is True and not R.jl(), str(r))
finally: R.kapat()

# --- W) Whisper ile birlikte (aktarıcı süreç içinde): masaüstü altyazı satırı ingest'in var olan kuralından geçer — o kanalda Whisper akarken gölgeye
# (.altyazi.log) gider ve ses izi kümesine ad oyu verir (kume_oyla → CAP_OY); Whisper yokken ana döküme (.jsonl) düşer. Yeni öncelik kuralı yok.
import importlib.util as _u
T = os.path.realpath(tempfile.mkdtemp(prefix="masaustu-altyazi-w-")); C = os.path.join(T, "canli"); os.makedirs(C)
try:
    json.dump({"alan": "Deneme", "ad": "Ali T", "port": bos_port(8785), "uygulama": T, "ortak": T, "konusma": False}, open(os.path.join(T, "ayar.json"), "w"))
    json.dump({"durum": "ok", "olaylar": []}, open(os.path.join(T, "takvim.json"), "w"))
    for f in ("relay.py", "manifest.json", "toplanti-claude.py", "baglayici.py"): shutil.copy(os.path.join(KOD, f), T)
    for dd in ("aktarici", "pano"): shutil.copytree(os.path.join(KOD, dd), os.path.join(T, dd))
    os.environ.update(SUFLOR_AYAR=os.path.join(T, "ayar.json"), SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_OTO="1", SUFLOR_TEST_HIZLI="1")
    _cwd = os.getcwd(); _argv = sys.argv; sys.argv = ["relay.py", "--dir", C, "--port", "0"]; os.chdir(T)
    sp = _u.spec_from_file_location("relay_ma", os.path.join(T, "relay.py")); m = _u.module_from_spec(sp); sp.loader.exec_module(m)
    os.chdir(_cwd); sys.argv = _argv
    m.masaustu_al({"uygulama": "Teams", "toplantida": True}); time.sleep(0.5)
    def jl_w(): return [json.loads(l) for f in glob.glob(os.path.join(C, "*.jsonl")) for l in open(f, encoding="utf-8") if l.strip() and '"text"' in l]
    def golge_w(): return [json.loads(l) for f in glob.glob(os.path.join(C, "*.altyazi.log")) for l in open(f, encoding="utf-8") if l.strip()]
    def bes(ekran, sn):
        t0 = time.time()
        while time.time() - t0 < sn: m.masaustu_altyazi_al({"girdiler": ekran}); time.sleep(0.5)
    # 1) Whisper iki kanalda akıyor
    w = m.STATE["whisper"]; w["durum"] = "hazir"; w["kanallar"]["karsi"] = w["kanallar"]["ben"] = time.time(); m.KANALLAR.clear()
    ok("W0 deneme ortamı: whisper_akiyor karşı ve ben", m.whisper_akiyor("karsi") and m.whisper_akiyor("ben"))
    bes([G(1, "Ayşe K", "Dış bilinmeyen", "Teklifi cuma gönderiyoruz."), G(2, "Ali T", "Anlaştık, teşekkürler.")], 7.2)
    g = golge_w()
    ok("W1 Whisper akarken satırlar gölgeye (.altyazi.log), ana dökümde yok", {x.get("speaker") for x in g} == {"Ayşe K", "Ali T"} and not jl_w(), f"gölge {g} · döküm {jl_w()}")
    ok("W2 karşı tarafın adı ses izi kümesine oy olarak gitti (kume_oyla), kullanıcınınki gitmedi", any(k == "Ayşe K" for _, k, _t in m.CAP_OY) and not any(k == "Ali T" for _, k, _t in m.CAP_OY), str(m.CAP_OY[-5:]))
    # 2) Whisper durdu: altyazı ana döküm
    w["durum"] = "yok"; w["kanallar"].clear()
    bes([G(3, "Ayşe K", "Dış bilinmeyen", "Rakamları da ekleyeceğim."), G(4, "Ali T", "Tamam, bekliyorum.")], 7.2)
    rows = jl_w()
    ok("W3 Whisper yokken satırlar ana dökümde (.jsonl), captions kaynağı ve konuşmacıyla", sorted((x["speaker"], x["src"]) for x in rows) == [("Ali T", "captions"), ("Ayşe K", "captions")] and len(golge_w()) == 2, f"{rows}")
    ok("W4 kullanıcının satırı ben sayılır (ben_satiri: ad), karşınınki karşı", m.ben_satiri({"speaker": "Ali T"}, "captions") and not m.ben_satiri({"speaker": "Ayşe K"}, "captions"))
except Exception as e:
    import traceback; traceback.print_exc(); ok("W süreç içi aktarıcı", False, repr(e))
finally: shutil.rmtree(T, ignore_errors=True)

print("\n" + ("TAMAM" if not HATA else f"HATA: {len(HATA)} — " + ", ".join(HATA)))
sys.exit(1 if HATA else 0)
