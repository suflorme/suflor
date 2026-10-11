#!/usr/bin/env python3
# Faz 4 — bas-konuş uçtan uca, kota harcamadan: say → 16 kHz PCM → /bas-konus → yerel Whisper → Brifing.app açık süreç kipi (brifing.swift
# bu sınamada derlenir) → sahte "claude" (stream-json konuşur, soruyu yankılar) → cümle cümle okuma (SUFLOR_TEST_BASLAT: ses çalınmaz).
# Aktarıcıda konus_* / Whisper döngüsünün bas dalı / brifing.swift açık süreç kipi / panodaki Konuş değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bas-konus.py
# Gerekenler: swiftc, kurulu Brifing.app (ayar.json'daki uygulama klasöründe; paket iskeleti için), whisper-venv (/Users/Shared/Suflor).
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request, wave
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = 8791
T = tempfile.mkdtemp(prefix="bas-"); canli = os.path.join(T, "canli"); os.makedirs(canli); proje = os.path.join(T, "proje"); os.makedirs(proje)
HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
try: _uyg = json.load(open(os.path.expanduser("~/Library/Application Support/Suflor/ayar.json"), encoding="utf-8")).get("uygulama")
except (OSError, ValueError): _uyg = None
kaynak = os.path.join(os.path.expanduser(_uyg or "~/Library/Application Support/Suflor"), "Suflor Brifing.app")
if not os.path.isdir(kaynak) or not shutil.which("swiftc") or not os.path.exists("/Users/Shared/Suflor/whisper-venv/bin/python"): sys.exit("atlandı: Brifing.app, swiftc ya da whisper-venv yok")
app = os.path.join(T, "Suflor Brifing.app"); shutil.copytree(kaynak, app, symlinks=True)
subprocess.run(["swiftc", "-O", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
open(sahte, "w").write('''#!/usr/bin/env python3
import json, sys, time
arg = sys.argv[1:]; assert "--input-format" in arg and "stream-json" in arg and not any("Bash" in a or "Write" in a for a in arg) and arg[arg.index("--model") + 1] == "sonnet"
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = 0
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = q.split("Soru: ", 1)[-1]
    b = "[Bağlam" in q and "Şimdi:" in q and "Deneme planlama" in q and "GİZLİ NOT" not in q  # davet notu girmez
    if n == 2: pr({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "tool_use", "name": "Grep"}}}); time.sleep(0.3)
    for parca in ["Sorduğun: ", soru.rstrip(".?!") + ".", " Basecamp takvimi", " geldi." if b else " gelmedi."] + ([" Önceki konuşma geldi."] if "[Önceki konuşma" in q and "Önceki soru: " in q else []):
        time.sleep(0.15); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    pr({"type": "result", "duration_api_ms": 500, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_tur_en_cok": 3}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py"): shutil.copy(os.path.join(KOD, f), T)
import datetime as _dt
_y = (_dt.datetime.now().astimezone() + _dt.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "e1", "baslik": "Deneme planlama", "baslangic": _y.isoformat(), "bitis": (_y + _dt.timedelta(minutes=30)).isoformat(),
           "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Deniz T"], "kisi_sayisi": 2, "notlar": "GİZLİ NOT"}]}, open(os.path.join(T, "takvim.json"), "w"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
def pcm(metin):
    a, w = os.path.join(T, "q.aiff"), os.path.join(T, "q.wav")
    subprocess.run(["say", "-v", "Yelda", "-o", a, metin]); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w])
    with wave.open(w) as f: return base64.b64encode(f.readframes(f.getnframes())).decode()
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1"),
                     stdout=open(os.path.join(T, "relay.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        if os.path.exists(os.path.join(canli, "kart-anahtari.txt")): break
        time.sleep(0.2)
    time.sleep(1); K = open(os.path.join(canli, "kart-anahtari.txt")).read().strip()
    def post(v, pano=True):
        h = {"X-Suflor-Anahtar": K, **({"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/bas-konus", data=json.dumps(v).encode(), headers=h), timeout=20).read())
        except urllib.error.HTTPError as e: return {"kod": e.code}
    st = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["konus"]
    log = lambda: open(os.path.join(T, "relay.log")).read()
    def sor(metin):
        p = pcm(metin); post({"komut": "basla"}); time.sleep(1.5); post({"pcm": p}); t0 = time.time()
        while time.time() - t0 < 60:
            k = st()
            if k["durum"] in ("hazir", "hata"): return k
            time.sleep(0.2)
        return st()
    ok("yalnız panodan (pano kökeni yoksa 403)", post({"komut": "basla"}, pano=False).get("kod") == 403)
    k = sor("Toplantı en çok kaç dakika sürmeli?")
    ok("soru yazıya döküldü ve Claude'a gitti", k["durum"] == "hazir" and "dakika" in (k.get("soru") or "").lower() and "Sorduğun" in (k.get("cevap") or ""))
    ok("cümle cümle okundu (ilk cümle sonuçtan önce)", log().count("SES (deneme)") == 2 and k["olcum"]["ses_ms"] < k["olcum"]["sure_ms"])
    ok("soruya tarih + yarının takvimi eklendi", "takvimi geldi" in (k.get("cevap") or ""))
    ok("okunurken yabancı ad Türkçe yazımla, pano metni aynen", "Beyskemp takvimi geldi" in log() and "Basecamp takvimi" in (k.get("cevap") or ""))
    ok("açık süreç bir kez açıldı", log().count("KONUŞ: açık süreç açıldı") == 1)
    k2 = sor("Toplantının sonunda ne yazılır?")
    ok("araç başlayınca 'Bakıyorum' söylendi (yalnız ikinci soruda)", log().count("Bakıyorum.") == 1 and log().count("SES (deneme)") == 5)
    ok("ikinci soru aynı süreçte, tur maliyeti farkla", k2["durum"] == "hazir" and log().count("KONUŞ: açık süreç açıldı") == 1 and abs(k2["olcum"]["maliyet"] - 0.01) < 1e-6)
    c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    ok("ölçüm claude-cagri.jsonl'de (bas-konus, wh/ilk/ses)", len(c) >= 2 and all(x["is"] == "bas-konus" and x["wh_ms"] and x["ilk_ms"] and x["ses_ms"] for x in c)
       and c[0]["arac"] == 0 and c[1]["arac"] == 1 and c[1]["araclar"] == ["Grep"] and c[1]["arac_ilk_ms"])
    ok("döküme yazılmadı", not any(f.endswith(".md") for f in os.listdir(canli)))
    k3 = sor("Yarın ne var?")
    t0 = time.time()
    while time.time() - t0 < 10 and "tur sınırı" not in log(): time.sleep(0.2)
    ok("tur sınırı (3 soru): üçüncü cevaptan sonra süreç kapandı, panoda cevap 'hazır' kaldı", k3["durum"] == "hazir" and st()["durum"] == "hazir" and "KONUŞ: süreç kapandı (tur sınırı: 3 soru" in log())
    k4 = sor("Peki saat kaçta?")
    ok("sonraki soru yeni süreçte, önceki soru-cevap bağlamıyla", k4["durum"] == "hazir" and log().count("KONUŞ: açık süreç açıldı") == 2
       and "Önceki konuşma geldi" in (k4.get("cevap") or "") and "saat" in (k4.get("soru") or "").lower())
    k5 = sor("Kim katılıyor?")
    ok("yeni süreçte ikinci soruya önceki konuşma eklenmez", k5["durum"] == "hazir" and "Önceki konuşma geldi" not in (k5.get("cevap") or "") and log().count("KONUŞ: açık süreç açıldı") == 2)
    ok("çok kısa kayıt reddedildi", post({"komut": "basla"}).get("ok") and not post({"pcm": base64.b64encode(b"\0" * 3200).decode()}).get("ok"))
    # S24 Aşama 1: "yazayım mı?" sorulurken bas-konuş = sesli cevap (Claude'a gitmez, yerel ayırıcı), 10 sn Geri al, eylem bekle 10 sn sonra alır
    def uc(yol, v, pano=False):
        h = {"X-Suflor-Anahtar": K, **({"Origin": f"http://127.0.0.1:{PORT}"} if pano else {})}
        return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers=h), timeout=10).read())
    ey = lambda: {x["id"]: x for x in ((json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read()).get("eylem") or {}).get("liste") or [])}
    sesli = lambda: (json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read()).get("eylem") or {}).get("sesli")
    ids = [uc("/eylem", {"tur": t, "baslik": b})["eylem"]["id"] for t, b in (("takvim", "Perşembe tekrar toplantı"), ("kayit", "Karar yaz"), ("takip", "Teşekkür e-postası"), ("belge", "Sözleşme notu"))]
    uc("/eylem-sun", {}); time.sleep(0.5)
    cagri0 = len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines())
    t0 = time.time(); k = sor("Evet."); sn_ = time.time() - t0; t_karar = time.time()
    e = ey()
    ok(f"'Evet.' → takvim onaylandı (kaynak ses, duyulan metin kayıtta), Claude'a gitmedi ({sn_:.1f} sn)", e[ids[0]]["durum"] == "onaylandi" and e[ids[0]]["kaynak"] == "ses" and "evet" in (e[ids[0]]["ses_metin"] or "").lower()
       and len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) == cagri0 and "Takvim onaylandı" in (k.get("cevap") or ""))
    ok("geri okuma sonra sıradaki soru okundu", log().rfind("Takvim onaylandı.") < log().rfind("Kayıt: Karar yaz") and sesli() == ids[1])
    ok("panoda Geri al süresi (≤ 10 sn)", 0 < e[ids[0]]["geri_al_sn"] <= 10)
    bekle_p = subprocess.Popen([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "eylem", "bekle", "--sn", "40"],
                               stdout=subprocess.PIPE, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay))
    k = sor("Hayır, gerek yok.")
    erken = (bekle_p.poll() is None) if time.time() - t_karar < 9 else None  # (9 sn geçtiyse ölçülemez)
    ok("'Hayır, gerek yok.' → kayıt reddedildi", ey()[ids[1]]["durum"] == "reddedildi" and sesli() == ids[2])
    ok("Geri al → kayıt yeniden bekliyor, soru yeniden okundu", uc("/eylem-geri-al", {"id": ids[1]}, pano=True)["ok"] and ey()[ids[1]]["durum"] == "bekliyor" and sesli() == ids[1] and log().count("Kayıt: Karar yaz") == 2)
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/eylem-geri-al", data=b'{"id": "x"}', headers={"X-Suflor-Anahtar": K}), timeout=5); kod = 200
    except urllib.error.HTTPError as e_: kod = e_.code
    ok("pano dışından Geri al yok (403)", kod == 403)
    k = sor("Evet yazma.")
    ok("'Evet yazma.' (iki yönlü) → karar yok, yeniden sorar", ey()[ids[1]]["durum"] == "bekliyor" and "Anlamadım" in (k.get("cevap") or "") and sesli() == ids[1])
    k = sor("Sonra.")
    ok("'Sonra.' → iş bekler, sıradaki soru", ey()[ids[1]]["durum"] == "bekliyor" and sesli() == ids[2])
    k = sor("Evet ama saati on bir yap.")
    ok("'Evet ama…' → kısa cevap iste, karar yok", ey()[ids[2]]["durum"] == "bekliyor" and "Kısa cevap" in (k.get("cevap") or ""))
    t1 = time.time(); out = bekle_p.communicate(timeout=60)[0]
    ok("eylem bekle sesli onayı 10 sn dolmadan vermedi, sonra verdi; geri alınan reddi vermedi", erken is not False and f"UYGULA: {ids[0]}" in out and ids[1] not in out)
    k = sor("Hepsini onayla.")
    e = ey()
    ok("'Hepsini onayla.' → kalan sunulanlar onaylandı, dizi bitti", all(e[i]["durum"] == "onaylandi" for i in ids[1:]) and sesli() is None and "Hepsi onaylandı" in (k.get("cevap") or ""))
    ok("sesli cevaplarda Claude süreci hiç çağrılmadı", len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) == cagri0)
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/ping", data=json.dumps({"call": True, "panel": True}).encode(), headers={"X-Suflor-Anahtar": K}))
    ok("toplantı sürerken kapalı", not post({"komut": "basla"}).get("ok"))
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); subprocess.run(["pkill", "-f", T])
print("bas-konuş:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
