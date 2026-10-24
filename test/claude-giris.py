#!/usr/bin/env python3
# Claude Code girişinin düşmesi (v0.130.0, aktarici/claude-giris.py): hata metni günlüğe; giriş hatası bir kez sesli uyarı + bildirim + Konuş satırında kalıcı
# uyarı; sıradan hata uyarı vermez; başarılı çağrı girişi geri getirir ve satırı temizler; yoklama (Brifing.app taklit) başarı/düşme; claude_json kancası.
# Gerçek Claude'a gidilmez.   PYTHONDONTWRITEBYTECODE=1 python3 test/claude-giris.py   (~1 sn)
import contextlib, io, json, os, re, subprocess, sys, tempfile, threading, time, types, datetime
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="suflor-giris-"); hata = []
def bak(ad, kosul): print(("✓ " if kosul else "✗ ") + ad); hata.extend([] if kosul else [ad])
os.environ["SUFLOR_TEST_BASLAT"] = "1"  # nöbet iş parçacığı başlamasın
UYARI, BILDIRIM, YAZILAN = [], [], []
KONUS = {"durum": "kapali", "hata": None}
def _konus_kur(**k): KONUS.update(**k)
CEVAP = {"j": {"is_error": False, "result": "tamam"}}
def sahte_run(args, **k):
    if args[:2] == ["open", "-g"]:
        istek = json.load(open(args[args.index("--istek") + 1])); open(istek["cikti"], "w").write(json.dumps(CEVAP["j"]))
    return subprocess.CompletedProcess(args, 0, "", "")
sp = types.SimpleNamespace(**{k: getattr(subprocess, k) for k in ("CompletedProcess", "TimeoutExpired", "PIPE", "DEVNULL")}, run=sahte_run)
BEYIN = types.SimpleNamespace(secim=lambda a, i: {"tur": "claude-code", "model": "m"}, claude_secim=lambda a, i: {"model": "m"},
                              telaffuz_args=lambda a, istem, m: ["-p", istem, "--model", m])
ad = {"__name__": "giris", "os": os, "re": re, "json": json, "time": time, "datetime": datetime, "threading": threading, "subprocess": sp,
      "AYAR": {"port": 8765}, "BASE": T, "KONUS": KONUS, "_KS": {}, "_konus_kur": _konus_kur, "_t": lambda a, b: a, "yerel_uyari": UYARI.append,
      "bildirim": lambda b, a, m, son=None: BILDIRIM.append(a), "BEYIN": BEYIN, "claude_yolu": lambda: "/bin/claude", "BRIFING_APP": T, "claude_yalin": lambda: [],
      "A": types.SimpleNamespace(port=8765)}
ad["claude_json"] = lambda ham, is_, t0, y, s=None, m=None: (lambda j: (ad["claude_hata_bildir"](j.get("result"), is_) if j.get("is_error") else ad["claude_ok"](), (j.get("result"), {}))[1])(json.loads(ham))
exec(compile(open(os.path.join(K, "aktarici", "claude-giris.py"), encoding="utf-8").read(), "claude-giris.py", "exec"), ad)

c = io.StringIO()
with contextlib.redirect_stdout(c): ad["claude_hata_bildir"]("Overloaded", "konus")
bak("sıradan hata: metin günlükte, uyarı yok", "CLAUDE: hata (konus) — Overloaded" in c.getvalue() and not UYARI and ad["GIRIS"]["durum"] is None)
c = io.StringIO()
with contextlib.redirect_stdout(c):
    ad["claude_hata_bildir"]("Failed to authenticate: OAuth session expired and could not be refreshed", "konus")
    ad["claude_hata_bildir"]("Failed to authenticate: OAuth session expired", "telaffuz")
bak(f"giriş hatası: durum düştü, tek günlük satırı, tek sesli uyarı ve bildirim ({len(UYARI)}, {len(BILDIRIM)})",
    ad["GIRIS"]["durum"] == "dustu" and c.getvalue().count("CLAUDE GİRİŞ: düştü") == 1 and len(UYARI) == 1 and "Terminal" in UYARI[0] and len(BILDIRIM) == 1)
bak(f"Konuş satırında kalıcı uyarı: {KONUS['hata']!r}", KONUS["durum"] == "hata" and "Terminal'de claude" in KONUS["hata"])
bak("durum görünümü", ad["claude_giris_view"]()["durum"] == "dustu")
KONUS.update(durum="dusunuyor", hata=None); ad["claude_giris_dustu"]("x", "konus"); bak("Konuş cevap verirken satır değiştirilmez", KONUS["durum"] == "dusunuyor")
KONUS.update(durum="hata", hata=ad["_t"](*ad["GIRIS_SATIR"]))
c = io.StringIO()
with contextlib.redirect_stdout(c): ad["claude_ok"]()
bak("başarılı çağrı: giriş tamam, 'geri geldi' satırı, Konuş uyarısı temizlenir", ad["GIRIS"]["durum"] == "tamam" and "geri geldi" in c.getvalue() and KONUS["hata"] is None)
# yoklama (Brifing.app taklit)
ad["GIRIS"]["son_ok"] = 0; r = ad["claude_giris_yokla"](zorla=True); bak("yoklama başarılı → True, son_ok güncel", r is True and time.time() - ad["GIRIS"]["son_ok"] < 5)
CEVAP["j"] = {"is_error": True, "result": "Failed to authenticate: OAuth session expired and could not be refreshed"}; UYARI.clear()
with contextlib.redirect_stdout(io.StringIO()): r = ad["claude_giris_yokla"](zorla=True)
bak("yoklama düşmüş → False, sesli uyarı", r is False and ad["GIRIS"]["durum"] == "dustu" and len(UYARI) == 1)
bak("istek dosyası silinir, yoklama kilidi açılır", not os.path.exists(os.path.join(T, "giris-istek.json")) and ad["GIRIS"]["yokluyor"] is False)
ad["AYAR"]["claude_giris_yokla"] = False; bak("ayar claude_giris_yokla: false → yoklanmaz", ad["claude_giris_yokla"]() is None)
BEYIN.secim = lambda a, i: {"tur": "openai", "model": "x"}; bak("sağlayıcı Claude Code değilse yoklanmaz", ad["claude_giris_yokla"](zorla=True) is None)
print("claude giriş: " + ("✓ hepsi geçti" if not hata else f"✗ {len(hata)} kaldı")); sys.exit(1 if hata else 0)
