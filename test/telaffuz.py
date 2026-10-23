#!/usr/bin/env python3
# Telaffuz (v0.32.1): aktarici/brifing-ses.py telaffuz() — sabit sözlükteki (aktarici/telaffuz-sozluk.json) İngilizce sözcükler Türkçe yazımla
# değişir (Türkçe ek korunur, büyük harfle başlayan sözcüğün okunuşu da büyük harfle başlar),
# okunan metinde bilinmeyen yabancı görünümlü sözcükler kuyruğa girer (Türkçe sözcükler girmez), telaffuz_ekle sonrası yeni okunuş kullanılır.
# Claude çağrısı yok. Kural ya da liste değişince koştur.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/telaffuz.py      (kaldı → çıkış 1)
import os, re, sys, json, time, threading, tempfile, collections, subprocess
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
BASE = tempfile.mkdtemp(prefix="suflor-telaffuz-"); ARAYUZ_DILI = "tr"
kisilik_telaffuz = lambda m: m  # v0.53.0: kişilik okunuşları (aktarici/kisilik.py) bu testin konusu değil; test/kisilik.py denetler
_f = __file__; __file__ = os.path.join(KOD, "relay.py")  # bölüm relay.py'nin ad alanında çalışır: sözlük yolu relay.py'nin yanındaki aktarici/
exec(src[src.index("def _telaffuz_sozluk"):src.index("def telaffuz_adaylari")]); __file__ = _f
hata = 0
def bak(ad, v, b):
    global hata
    if v != b: hata += 1; print(f"✗ {ad}: {v!r}, beklenen {b!r}")
# 1) sabit liste, ek korunur, büyük/küçük harf
bak("Teams'te", telaffuz("Toplantıyı Teams'te yapalım."), "Toplantıyı Tims'te yapalım.")
bak("Zoom tek ünlü", telaffuz("Zoom'a geçelim"), "Zum'a geçelim")
bak("meeting", telaffuz("Yarınki meeting saat 10'da, deadline cuma."), "Yarınki miting saat 10'da, dedlayn cuma.")
bak("kısaltma yalnız büyük harfle", telaffuz("IP adresi verildi, ip atlamak yok, OK."), "Ay pi adresi verildi, ip atlamak yok, Okey.")
bak("Türkçe dokunulmaz", telaffuz("Bütçe onayını bekliyoruz."), "Bütçe onayını bekliyoruz.")
bak("IT yalnız büyük harfle (Türkçe 'it' değişmez)", telaffuz("IT ekibi geldi, it havlıyor."), "Ay ti ekibi geldi, it havlıyor.")
bak("maliyet şapkalı", telaffuz("Maliyeti düşük, maliyet tablosu hazır."), "Mâliyeti düşük, mâliyet tablosu hazır.")
bak("mimari şapkalı (ekli biçim)", telaffuz("Yeni mimarisi hazır, mimariyi konuştuk."), "Yeni mimârîsi hazır, mimârîyi konuştuk.")
bak("Mac sesi: doğru okuduğu sözcüğe dokunulmaz, okuyamadığına sözlük (v0.39.2)", telaffuz("Teams'te meeting var, feedback ve KPI tablosu hazır.", mac=True), "Teams'te meeting var, fidbek ve Ki pi ay tablosu hazır.")
bak("Piper: aynı cümlede hepsine sözlük", telaffuz("Teams'te meeting var, feedback ve KPI tablosu hazır."), "Tims'te miting var, fidbek ve Ki pi ay tablosu hazır.")
bak("lazım ekli biçimleri ve cümle başı (v0.70.5, kullanıcı isteği: lâzımsa, cevâbını)", telaffuz("Lazımsa yazarım. Cevabını sonra veririm, bu lazımdı."), "Lâzımsa yazarım. Cevâbını sonra veririm, bu lâzımdı.")
bak("uzun ünlü şapkayla (v0.39.1, Mac sesi)", telaffuz("Cevabı şöyle: hesabını kontrol ettim, kağıt lazım."), "Cevâbı şöyle: hesâbını kontrol ettim, kâğıt lâzım.")
bak("ünsüz yumuşayınca uzun ünlü (v0.47.2, Mac sesi \"sahip\"i uzatır, \"sahibini\"yi uzatmaz)", telaffuz("Sahibini sordum, takibinde kalsın; sahip ve takip aynen.", mac=True), "Sâhibini sordum, tâkibinde kalsın; sahip ve takip aynen.")
bak("uzun ünlü listesi (v0.48.1, telaffuz-uzun.json): yumuşamış biçim şapkalı, eş yazım ve incelme riski dokunulmaz", telaffuz("Mizacını biliyorum, inkılabını okudum; kabını getir, babası geldi.", mac=True), "Mizâcını biliyorum, inkılâbını okudum; kabını getir, babası geldi.")
# 1b) sözlük dosyası okundu, büyük harf korunur (Piper küçük harfle başlayanı yeni cümle saymaz); Türkçe i → İ
bak("sözlük dosyası", len(TELAFFUZ) > 200 and TELAFFUZ.get("Teams") == "Tims", True)
bak("büyük harf korunur", telaffuz("Feedback'leri topladık. Deadline cuma."), "Fidbek'leri topladık. Dedlayn cuma.")
bak("küçük harf aynen", telaffuz("bu feedback iyi"), "bu fidbek iyi")
bak("kısaltma büyük harf", telaffuz("Toplantı bitti. KPI tablosu hazır."), "Toplantı bitti. Ki pi ay tablosu hazır.")
bak("Türkçe büyük İ", telaffuz("Toplantı bitti. Influencer listesi hazır."), "Toplantı bitti. İnfluensır listesi hazır.")
# 2) bilinmeyen yabancı sözcük kuyruğu
_TEL_BEK["q"].clear()
telaffuz("Bunu Ali ile Hubspot üzerinden konuşalım, sonra Biweekly kickoff yaparız. KDV dahil, aile toplantısı yok.")
q = list(_TEL_BEK["q"])
for w in ("Hubspot", "Biweekly", "kickoff", "KDV", "Ali"): bak(f"kuyrukta {w}", w in q, True)
for w in ("Bunu", "ile", "konuşalım", "sonra", "yaparız", "dahil", "toplantısı", "yok"): bak(f"kuyrukta değil {w}", w in q, False)
_TEL_BEK["q"].clear(); telaffuz("Hubspot yine geldi.")
bak("ikinci kez sorulmaz", _TEL_BEK["q"], [])
telaffuz("Toplantı bitti. Sonra bakarız.")
bak("cümle başı büyük harf Türkçe", _TEL_BEK["q"], [])
# 3) telaffuz_ekle → sonraki okumada kullanılır, telaffuz.json (elle) önce gelir
telaffuz_ekle({"Hubspot": "Habspot", "Biweekly": "Bayvikli"})
bak("oto okunuş", telaffuz("Hubspot'ta Biweekly var"), "Habspot'ta Bayvikli var")
json.dump({"Hubspot": "Hab spat"}, open(os.path.join(BASE, "telaffuz.json"), "w")); _TEL["re"] = None
bak("elle düzeltme önce", telaffuz("Hubspot"), "Hab spat")
# 4) Faz 11 Aşama 2: okunuş tamamlama başka sağlayıcıda (beyin.telaffuz → `beyin.py tek`, sahte OpenAI uyumlu sunucu) ve hata olunca bir kez Claude Code (Brifing.app taklidi)
import http.server, socket, types, importlib.util
_GEL, _DUR = [], {"kod": 200}
class _Sahte(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        g = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); _GEL.append(g)
        if _DUR["kod"] != 200: b = b'{"error":{"message":"busy"}}'; self.send_response(_DUR["kod"]); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        b = json.dumps({"choices": [{"message": {"content": json.dumps({"Salesforce": "Seylsfors"})}}], "usage": {"prompt_tokens": 300, "completion_tokens": 20}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
_so = socket.socket(); _so.bind(("127.0.0.1", 0)); _sp = _so.getsockname()[1]; _so.close()
_SV = http.server.ThreadingHTTPServer(("127.0.0.1", _sp), _Sahte); threading.Thread(target=_SV.serve_forever, daemon=True).start()
_b = importlib.util.spec_from_file_location("beyin_tel", os.path.join(KOD, "aktarici", "beyin.py")); BEYIN = importlib.util.module_from_spec(_b); _b.loader.exec_module(BEYIN)
os.environ["SUFLOR_TEST_BEYIN_ANAHTAR"] = "x"
A = types.SimpleNamespace(port=1); LOCK = threading.Lock(); datetime = __import__("datetime")
def write(l):
    for y, m in l: open(y, "a", encoding="utf-8").write(m)
_ACIK = []
class _Sub:  # Brifing.app (open -a …) taklidi: çıktı dosyasına Claude Code json'u yazar; gerisi gerçek subprocess
    TimeoutExpired = subprocess.TimeoutExpired
    @staticmethod
    def run(args, **k):
        if args[0] == "open":
            ist = json.load(open(args[-1])); _ACIK.append(ist["args"])
            json.dump({"result": json.dumps({"Salesforce": "Seylsfors (claude)"}), "usage": {"input_tokens": 5}, "total_cost_usd": 0.01}, open(ist["cikti"], "w")); return None
        return subprocess.run(args, **k)
_gercek_sub = subprocess
exec(src[src.index("def claude_yalin"):src.index("# --- Sesli brifing")].replace("subprocess.", "_Sub."))
exec(src[src.index("def telaffuz_tamamla"):src.index("def _telaffuz_dongu")].replace("subprocess.", "_Sub."))
BRIFING_APP = BASE; claude_yolu = lambda: "/bin/echo"
def _kayit(): return [json.loads(l) for l in open(os.path.join(BASE, "claude-cagri.jsonl"))] if os.path.exists(os.path.join(BASE, "claude-cagri.jsonl")) else []
_cik = io_ = __import__("io").StringIO(); _std = sys.stdout
AYAR = {"port": 1, "beyin": {"telaffuz": {"tur": "openai-uyumlu", "saglayici": "gemini", "adres": f"http://127.0.0.1:{_sp}/v1", "model": "gemini-3.8-flash", "fiyat": [1, 0.1, 10]}}}
sys.stdout = _cik; telaffuz_tamamla(["Salesforce"]); sys.stdout = _std
bak("başka sağlayıcı: okunuş yazıldı, JSON kipi, Claude çağrılmadı, kayıtta saglayici gemini", (telaffuz_oto().get("Salesforce"), bool(_GEL and _GEL[0].get("response_format")), _ACIK,
    [(r["is"], r["saglayici"], r.get("model")) for r in _kayit()]), ("Seylsfors", True, [], [("telaffuz", "gemini", "gemini-3.8-flash")]))
_DUR["kod"] = 500; _TEL_OTO["calisiyor"] = False; sys.stdout = _cik; telaffuz_tamamla(["Salesforce"]); sys.stdout = _std
bak("sağlayıcı 500 → bir kez Claude Code (Claude modeli sonnet), günlükte BEYİN: yedek", (telaffuz_oto().get("Salesforce"), len(_ACIK), _ACIK[0][_ACIK[0].index("--model") + 1] if _ACIK else None,
    _cik.getvalue().count("BEYİN: yedek — telaffuz: gemini"), _kayit()[-1]["saglayici"]), ("Seylsfors (claude)", 1, "sonnet", 1, "claude-code"))
AYAR["beyin"]["telaffuz"]["yedek"] = False; claude_yolu = lambda: None; _TEL_OTO["calisiyor"] = False; sys.stdout = _cik; telaffuz_tamamla(["Hubspot2"]); sys.stdout = _std
bak("Claude Code yokken sağlayıcı hatası: yedek yok, tek satır", (len(_ACIK), "yanıt vermedi" in _cik.getvalue()), (1, True))
_SV.shutdown()
print(f"telaffuz: " + ("✓ hepsi geçti" if not hata else f"{hata} hata"))
sys.exit(1 if hata else 0)
