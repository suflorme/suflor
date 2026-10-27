# Test portu: istenen port boşsa o, doluysa (başka test ya da süreç tutuyorsa) işletim sisteminin verdiği boş port.
# Kullanım (önbellek dosyası yazmadan; klasörde _ ile başlayan klasör olmaz):
#   sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
#   PORT = bos_port(8793)
import socket
_verilen = set()
def bos_port(tercih=0):
    for p in (tercih, 0):
        if p and p in _verilen: continue
        s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind(("127.0.0.1", p)); p = s.getsockname()[1]
        except OSError: continue
        finally: s.close()
        _verilen.add(p); return p
    raise OSError("boş port bulunamadı")

# Canlı kullanım koruması (v0.91.2, 20 Ekim ölçümü): aynı Mac'te iki Whisper aynı anda çalışınca ikisi de 2,5–3,3 kat yavaşlıyor (2 sn ses 1,1 → 2,8–3,6 sn;
# olcum.py isci iki kopya). 19 Ekim akşamı kullanıcının sohbetinde parçalar böyle yavaşladı (o saatte başka oturumların testleri koşuyordu). Gerçek model
# (Whisper, Pocket, Piper, gömme, çevirme) yükleyen test, canlı aktarıcıda toplantı / sohbet / süren Konuş cevabı varken başlamaz: en çok CANLI_BEKLE_SN
# bekler, sonra çıkış 3 ile durur. Bilerek koşturmak için SUFLOR_TEST_ZORLA=1. Liste: AGIR_TESTLER (yeni gerçek modelli test buraya).
import json, os, sys, time, urllib.request
AGIR_TESTLER = {"anlam.py", "bas-konus.py", "cevir.py", "dosyadan-pano.py", "dosyadan.py", "hihi.py", "konusmaci.py", "moderator-uctan.py", "otonom.py", "oda.py",
                "kisilik.py", "pocket.py", "pocket-kur.py", "piper.py", "sohbet.py", "talimat.py", "uydurma.py", "whisper-cpp.py", "whisper-refs.py", "yerel-ses.py"}
CANLI_BEKLE_SN = 900
def canli_mesgul():  # kurulum.py mesgul ile aynı ölçüt; canlı aktarıcıya ulaşılamazsa boş (meşgul değil)
    try:
        a = json.load(open(os.environ.get("SUFLOR_CANLI_AYAR") or os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8"))
        k = open(os.path.join(os.path.expanduser(a.get("uygulama") or ""), "canli", "kart-anahtari.txt")).read().strip()  # kurulum.py _anahtar ile aynı yer
        s = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{a.get('port') or 8765}/status", headers={"X-Suflor-Anahtar": k}), timeout=2).read())
    except Exception: return ""
    x = s.get("extension") or {}; ko = s.get("konus") or {}; n = []
    if x.get("call") and (x.get("age_s") is None or x["age_s"] < 60): n.append("web toplantısı")
    if (s.get("masaustu") or {}).get("toplantida"): n.append("masaüstü toplantısı")
    if (ko.get("sohbet") or {}).get("acik"): n.append("sohbet açık")
    if ko.get("durum") in ("yaziya", "dusunuyor", "konusuyor", "dinliyor"): n.append(f"Konuş ({ko['durum']})")
    return ", ".join(n)
def canli_bekle(ad=None):
    if os.environ.get("SUFLOR_TEST_ZORLA"): return
    t0 = time.time(); m = canli_mesgul(); yazdi = False
    while m:
        if not yazdi: print(f"⏸ canlı Suflor kullanılıyor ({m}) — gerçek modelli test ({ad or '?'}) bekliyor (en çok {CANLI_BEKLE_SN // 60} dk; SUFLOR_TEST_ZORLA=1 beklemez)", flush=True); yazdi = True
        if time.time() - t0 > CANLI_BEKLE_SN: print(f"⛔ canlı Suflor hâlâ kullanılıyor ({m}) — test başlamadı"); sys.exit(3)
        time.sleep(10); m = canli_mesgul()
    if yazdi: print(f"▶ canlı Suflor boşaldı ({time.time() - t0:.0f} sn beklendi) — test başlıyor", flush=True)
if os.path.basename(sys.argv[0] if sys.argv else "") in AGIR_TESTLER: canli_bekle(os.path.basename(sys.argv[0]))
