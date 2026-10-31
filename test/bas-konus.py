#!/usr/bin/env python3
# Faz 4 — bas-konuş uçtan uca, kota harcamadan: say → 16 kHz PCM → /bas-konus → yerel Whisper → Brifing.app açık süreç kipi (brifing.swift
# bu sınamada derlenir) → sahte "claude" (stream-json konuşur, soruyu yankılar) → cümle cümle okuma (SUFLOR_TEST_BASLAT: ses çalınmaz).
# Aktarıcıda konus_* / Whisper döngüsünün bas dalı / brifing.swift açık süreç kipi / panodaki Konuş değişince koştur:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bas-konus.py
# Gerekenler: swiftc, kurulu Brifing.app (ayar.json'daki uygulama klasöründe; paket iskeleti için), whisper-venv (/Users/Shared/Suflor).
import glob, base64, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request, wave
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PORT = bos_port(8791)
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
subprocess.run(["swiftc", "-O", "-D", "SUFLOR_DENEME", "-o", os.path.join(app, "Contents/MacOS/SuflorBrifing"), os.path.join(KOD, "brifing.swift")], check=True, capture_output=True)
subprocess.run(["codesign", "-s", "-", "--force", "--deep", app], capture_output=True)
os.makedirs(os.path.join(T, "bin")); sahte = os.path.join(T, "bin", "claude")  # Brifing.app yalnız adı "claude" olanı çalıştırır
open(sahte, "w").write('''#!/usr/bin/env python3
import json, os, re, sys, time
arg = sys.argv[1:]; assert "--input-format" in arg and "stream-json" in arg and not any("Bash" in a or "Write" in a for a in arg) and arg[arg.index("--model") + 1] == "sonnet"
pr = lambda o: (sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\\n"), sys.stdout.flush())
n = ns = 0; defter = None; ek = False; isaret = os.path.join(os.path.dirname(sys.argv[0]), "takildi")
for l in sys.stdin:
    q = json.loads(l)["message"]["content"]; n += 1; soru = re.sub(r"(?s)\\[Ön arama.*?\\[/Ön arama\\]\\s*", "", q.split("Soru: ", 1)[-1])  # v0.64.0: ön aramada Konuş geçmişi de çıkabilir
    d = re.search(r"\\[Toplantı defteri — (.+?);", q)
    if d and "[/Toplantı defteri]" in q: defter = d.group(1)  # soruyla gelen defter: sonraki cevap "Defter geldi" der
    ek = ek or "[Defter eki" in q
    if "donma" in soru.lower() or ("takılma" in soru.lower() and not os.path.exists(isaret)):  # takılan Claude: hiç cevap yok
        open(isaret, "w").close(); time.sleep(600); continue
    ns += 1; b = "[Bağlam" in q and "Şimdi:" in q and "Deneme planlama" in q and "GİZLİ NOT" not in q  # davet notu girmez
    if ns == 2:  # v0.77.3: ilk yanıt + düşünme bloğu (ölçüm alanları)
        pr({"type": "stream_event", "event": {"type": "message_start"}}); pr({"type": "stream_event", "event": {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking"}}})
        pr({"type": "stream_event", "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "abcde"}}}); time.sleep(0.2)
        pr({"type": "stream_event", "event": {"type": "content_block_stop", "index": 0}})
    if ns == 2: pr({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "tool_use", "name": "Grep"}}}); time.sleep(0.3)
    if "listeden" in soru.lower():  # v0.101.1: Claude oturuma iletiyi hazırlar — etiket sesli kısımda, "---" yok (okunmamalı)
        for parca in ["Tamam, ana oturuma iletiyi hazırladım.", " [İLET proje: R12 Ali raporu işini listeden çıkar; ", "günlük plandaki 8. satır da düşsün.]"]:
            time.sleep(0.15); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
        pr({"type": "result", "duration_api_ms": 500, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}}); continue
    for parca in ["Sorduğun: ", soru.rstrip(".?!") + ".", " Basecamp takvimi", " geldi." if b else " gelmedi."] + ([" Önceki konuşma geldi."] if "[Önceki konuşma" in q and "Önceki soru: " in q else []) \
            + ([f" Defter geldi: {defter}."] if defter else []) + ([" Ek geldi."] if ek else []) + ([" Geçmiş toplantı geldi."] if "[Sıradaki toplantı" in q and "Bütçe takibi" in q and "ortak: ayla" in q else []) \\
            + ([" Toplantı bağlamı geldi."] if "Toplantı sürüyor:" in q and "yalnız panoda" in q else []) + ([" Selam notu geldi."] if "[Suflor cevaptan önce kullanıcıyı sesli selamladı" in q else []) + (["\\n---\\n", "Ayrıntı satırı 10:01."] if defter or ek else []):
        time.sleep(0.15); pr({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": parca}}})
    defter = None; ek = False
    pr({"type": "result", "duration_api_ms": 500, "total_cost_usd": 0.01 * n, "num_turns": n, "usage": {"input_tokens": 5, "cache_read_input_tokens": 95}})
''')
os.chmod(sahte, 0o755)
ay = os.path.join(T, "ayar.json"); json.dump({"alan": "Deneme", "tepki_sesleri": os.path.join(T, "tepki-yok"), "ad": "Deniz T", "port": PORT, "uygulama": T, "proje": proje, "ortak": "/Users/Shared/Suflor", "claude": sahte, "konus_tur_en_cok": 3, "konus_zaman_asimi_sn": 3, "konus_bekle_sn": 1.5, "konus_ara_sn": 2, "konus_gecmis": True, "konus_on_ac": True, "konus_iki_surec": True, "pocket_python": "/yok/python", "pocket_hf": "/yok"}, open(ay, "w"))
for f in ("relay.py", "manifest.json", "whisper-isci.py", "baglam.py"): shutil.copy(os.path.join(KOD, f), T)
shutil.copytree(os.path.join(KOD, "aktarici"), os.path.join(T, "aktarici"))  # relay.py bölüm dosyaları
import datetime as _dt
_y = (_dt.datetime.now().astimezone() + _dt.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
json.dump({"durum": "ok", "olaylar": [{"id": "e1", "baslik": "Deneme planlama", "baslangic": _y.isoformat(), "bitis": (_y + _dt.timedelta(minutes=30)).isoformat(),
           "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Deniz T"], "kisi_sayisi": 2, "notlar": "GİZLİ NOT"},
          {"id": "e2", "baslik": "Bütçe takibi", "baslangic": (_dt.datetime.now().astimezone() + _dt.timedelta(minutes=90)).isoformat(),  # S48: toplantı öncesi blok
           "bitis": (_dt.datetime.now().astimezone() + _dt.timedelta(minutes=120)).isoformat(), "tum_gun": False, "takvim": "İş", "hesap": "Yerel", "katilimcilar": ["Ayla K"], "kisi_sayisi": 2}]},
          open(os.path.join(T, "takvim.json"), "w"))
shutil.copytree(os.path.join(KOD, "pano"), os.path.join(T, "pano"))
def pcm(metin):
    a, w = os.path.join(T, "q.aiff"), os.path.join(T, "q.wav")
    subprocess.run(["say", "-v", "Yelda", "-o", a, metin]); subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w])
    with wave.open(w) as f: return base64.b64encode(f.readframes(f.getnframes())).decode()
r = subprocess.Popen([sys.executable, "relay.py", "--dir", canli, "--port", str(PORT)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
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
    ok("cümle cümle okundu (ilk cümle sonuçtan önce; önünde günün selamı)", log().count("SES (deneme)") == 4 and k["olcum"]["ses_ms"] < k["olcum"]["sure_ms"])
    ok("v0.101.0: günün ilk sorusunda selam okundu, Claude'a 'selam verildi' notu gitti", "KONUŞ: selam (ilk): " in log() and "Deniz." in log() and "Selam notu geldi" in (k.get("cevap") or ""))
    ok("soruya tarih + yarının takvimi eklendi", "takvimi geldi" in (k.get("cevap") or ""))
    ok("okunurken yabancı ad Türkçe yazımla, pano metni aynen", "Beyskemp takvimi geldi" in log() and "Basecamp takvimi" in (k.get("cevap") or ""))
    ok("açık süreç bir kez açıldı", log().count("KONUŞ: açık süreç açıldı") == 1)
    k2 = sor("Toplantının sonunda ne yazılır?")
    ok("araç başlayınca konuya özgü cümle söylendi (yalnız ikinci soruda)", log().count("KONUŞ: araç cümlesi") == 1 and log().count("SES (deneme)") == 7)
    ok("v0.101.0: konuşma sürerken ikinci soruda selam yok", log().count("KONUŞ: selam") == 1 and "Selam notu geldi" not in (k2.get("cevap") or ""))
    ok("ikinci soru aynı süreçte, tur maliyeti farkla", k2["durum"] == "hazir" and log().count("KONUŞ: açık süreç açıldı") == 1 and abs(k2["olcum"]["maliyet"] - 0.01) < 1e-6)
    c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    ok("ölçüm claude-cagri.jsonl'de (bas-konus, wh/ilk/ses)", len(c) >= 2 and all(x["is"] == "bas-konus" and x["wh_ms"] and x["ilk_ms"] and x["ses_ms"] and x.get("ses_cal_ms") is not None for x in c)
       and c[0]["arac"] == 0 and c[1]["arac"] == 1 and c[1]["araclar"] == ["Grep"] and c[1]["arac_ilk_ms"])
    ok("ölçümde o anki sistem durumu: yük, boş bellek %, takas (v0.91.1)", all(isinstance((x.get("sistem") or {}).get("yuk"), float) and 0 <= (x["sistem"].get("bos_yuzde") or -1) <= 100 for x in c))
    ok("ölçüm: soru gönderimi, ilk yanıt, düşünme süresi/uzunluğu (v0.77.3)", c[1]["gonder_ms"] is not None and c[1]["ilk_yanit_ms"] and c[1]["dusunme"] == 1
       and c[1]["dusunme_kar"] == 5 and 150 <= c[1]["dusunme_ms"] < 2000 and c[0]["dusunme_kar"] == 0 and c[0]["ilk_yanit_ms"] is None)
    ok("döküme yazılmadı", not any(f.endswith(".md") for f in os.listdir(canli)))
    pid_ = lambda: set(subprocess.run(["pgrep", "-f", "SuflorBrifing --istek " + T], capture_output=True, text=True).stdout.split())
    eski_ = pid_()
    k3 = sor("Yarın ne var?")
    t0 = time.time()
    while time.time() - t0 < 10 and "tur sınırı" not in log(): time.sleep(0.2)
    ok("tur sınırı (3 soru): üçüncü cevaptan sonra süreç kapandı, panoda cevap 'hazır' kaldı", k3["durum"] == "hazir" and st()["durum"] == "hazir" and "KONUŞ: süreç kapandı (tur sınırı: 3 soru" in log())
    # v0.57.6: kapatılan süreç gerçekten çıkar — Brifing girişi anonim boruyla aktarır (gerçek claude adlı FIFO'da dosya sonunu görmüyordu, süreç açık kalıyordu)
    t_ = time.time()
    while time.time() - t_ < 10 and eski_ & pid_(): time.sleep(0.3)
    ok(f"kapatılan süreç çıktı: eski Brifing yardımcısı açık kalmadı ({round(time.time() - t_, 1)} sn)", eski_ and not (eski_ & pid_()))
    while time.time() - t_ < 10 and "KONUŞ: süreç önceden açıldı (tur sınırı)" not in log(): time.sleep(0.2)
    ok("v0.96.0: tur sınırında yeni süreç önceden açıldı (mesajsız)", "KONUŞ: süreç önceden açıldı (tur sınırı)" in log())
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
       and len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) == cagri0 and "Takvimine ekliyorum" in (k.get("cevap") or ""))
    ok("geri okuma sonra sıradaki soru okundu", log().rfind("Takvimine ekliyorum.") < log().rfind("Karar yaz. Bunu kayda") and sesli() == ids[1])
    ok("panoda Geri al süresi (≤ 10 sn)", 0 < e[ids[0]]["geri_al_sn"] <= 10)
    bekle_p = subprocess.Popen([sys.executable, os.path.join(KOD, "toplanti-claude.py"), "--dir", canli, "--relay", f"http://127.0.0.1:{PORT}", "eylem", "bekle", "--sn", "40"],
                               stdout=subprocess.PIPE, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay))
    k = sor("Hayır, gerek yok.")
    erken = (bekle_p.poll() is None) if time.time() - t_karar < 9 else None  # (9 sn geçtiyse ölçülemez)
    ok("'Hayır, gerek yok.' → kayıt reddedildi", ey()[ids[1]]["durum"] == "reddedildi" and sesli() == ids[2])
    ok("Geri al → kayıt yeniden bekliyor, soru yeniden okundu", uc("/eylem-geri-al", {"id": ids[1]}, pano=True)["ok"] and ey()[ids[1]]["durum"] == "bekliyor" and sesli() == ids[1] and log().count("Karar yaz. Bunu kayda") == 2)
    try: urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/eylem-geri-al", data=b'{"id": "x"}', headers={"X-Suflor-Anahtar": K}), timeout=5); kod = 200
    except urllib.error.HTTPError as e_: kod = e_.code
    ok("pano dışından Geri al yok (403)", kod == 403)
    k = sor("Evet yazma.")
    ok(f"'Evet yazma.' (iki yönlü) → karar yok, doğal cümleyle yeniden sorar ({k.get('cevap')!r})", ey()[ids[1]]["durum"] == "bekliyor" and re.search("duyamadım|kaçırdım|yeterli", k.get("cevap") or "") and "evet, hayır ya da" not in (k.get("cevap") or "").lower() and sesli() == ids[1])
    k = sor("Sonra.")
    ok("'Sonra.' → iş bekler, sıradaki soru", ey()[ids[1]]["durum"] == "bekliyor" and sesli() == ids[2])
    k = sor("Evet ama saati on bir yap.")
    ok("'Evet ama…' → kısa cevap iste, karar yok", ey()[ids[2]]["durum"] == "bekliyor" and "emin olayım" in (k.get("cevap") or ""))
    t1 = time.time(); out = bekle_p.communicate(timeout=60)[0]
    ok("eylem bekle sesli onayı 10 sn dolmadan vermedi, sonra verdi; geri alınan reddi vermedi", erken is not False and f"UYGULA: {ids[0]}" in out and ids[1] not in out)
    k = sor("Hepsini onayla.")
    e = ey()
    ok("'Hepsini onayla.' → kalan sunulanlar onaylandı, dizi bitti", all(e[i]["durum"] == "onaylandi" for i in ids[1:]) and sesli() is None and "hepsini onaylıyorum" in (k.get("cevap") or ""))
    ok("sesli cevaplarda Claude süreci hiç çağrılmadı", len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) == cagri0)
    # S48: biten toplantının defteri — süreç başına bir kez tam defter, aynı süreçte yalnız ek, "---" sonrası okunmaz, toplantı değişince yeni süreç
    ok("toplantı yokken panoda defter satırı yok", st().get("defter") is None)
    def uc2(yol, v): return json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}{yol}", data=json.dumps(v).encode(), headers={"X-Suflor-Anahtar": K}), timeout=10).read())
    satir = lambda b, i, kim, s, m: uc2("/ingest", {"meeting": {"title": b}, "source": "transcript", "entries": [{"id": f"{b[:3]}/{i}", "speaker": kim, "time": s, "text": m}]})
    satir("Defter denemesi", 1, "Ayla K", "10:01", "Bütçe kırk bin olsun."); satir("Defter denemesi", 2, "Deniz T", "10:02", "Teslim cuma günü.")
    tad = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K}), timeout=10).read())["toplanti"].get("ad")
    AD1 = tad()  # Faz B: toplantının adı kayıttan (sayfa başlığı değil)
    md = next(f for f in os.listdir(canli) if f.endswith(".md")); oz = os.path.join(T, "defter-ozet.md"); open(oz, "w").write("# Özet\nKarar: bütçe kırk bin.\n")
    uc2("/son-toplanti", {"ozet": oz, "baslik": "Defter denemesi", "dosya": md, "metin": open(oz).read()}); time.sleep(0.5)
    ok("bitişten sonra panoda 'Son toplantı hazır' (ad)", (st().get("defter") or {}).get("ad") == AD1)
    ses0 = log().count("SES (deneme)")
    k6 = sor("Toplantıda bütçe ne oldu?")
    ok("defter soruyla birlikte gitti; cevapta '---' ayrıntı", k6["durum"] == "hazir" and f"Defter geldi: {AD1}" in (k6.get("cevap") or "")
       and "---" in k6["cevap"] and "DEFTER: bas-konuşa gitti — 1 dosya" in log() and "ısınma" not in log())
    ok("'---' sonrası okunmadı", "Ayrıntı satırı" not in log() and log().count("SES (deneme)") > ses0)
    c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    ok("ölçümde defter işareti, ısınma kaydı yok", c[-1].get("defter") is True and c[-1]["is"] == "bas-konus" and not any(x["is"] == "bas-konus-isinma" for x in c))
    t0 = time.time()
    while time.time() - t0 < 10 and log().count("tur sınırı") < 2: time.sleep(0.2)
    k7 = sor("Teslim ne zaman?")
    ok("süreç yenilenince defter yeniden gitti", "Defter geldi" in (k7.get("cevap") or "") and log().count("DEFTER: bas-konuşa gitti") == 2)
    ok("toplantı öncesi: sıradaki toplantının bloğu, aynı kişiyle geçmiş toplantı (Ayla K) içinde", "Geçmiş toplantı geldi" in (k7.get("cevap") or "") and "KONUŞ: sıradaki toplantı bloğu gitti" in log())
    k8 = sor("Başka ne konuşuldu?")
    ok("aynı süreçte ikinci soruda defter yok", k8["durum"] == "hazir" and "Defter geldi" not in (k8.get("cevap") or "") and "Ek geldi" not in (k8.get("cevap") or "")
       and log().count("DEFTER: bas-konuşa gitti") == 2)
    uc2("/note", {"text": "Toplantı sonrası not: fatura ayrı kesilecek."}); time.sleep(0.3)
    k9 = sor("Not ne yazıldı?")
    ok("bitişten sonra not biten toplantının defterine girmez (S163)", "Ek geldi" not in (k9.get("cevap") or "") and "Defter geldi" not in k9["cevap"])
    t0 = time.time()
    while time.time() - t0 < 10 and log().count("tur sınırı") < 3: time.sleep(0.2)
    k10 = sor("Kim katıldı?")
    satir("Başka toplantı", 1, "Can B", "11:00", "Yeni konu."); time.sleep(0.3); AD2 = tad()
    k11 = sor("Bu toplantıda ne konuşuldu?")
    ok("toplantı değişince süreç yenilendi, yeni defter", "KONUŞ: süreç kapandı (yeni toplantı)" in log() and f"Defter geldi: {AD2}" in (k11.get("cevap") or ""))
    # v0.33.1: zaman aşımı (test ayarı 3 sn) — süreç yenilenir, soru bir kez daha gider; ikincide de cevap yoksa hata
    k12 = sor("Takılma denemesi var mı?")
    ok("takılan soru: 3 sn sonra süreç yenilendi, soru yeniden gitti ve cevaplandı (defter yeni süreçte soruyla)", k12["durum"] == "hazir" and "Sorduğun" in (k12.get("cevap") or "")
       and "KONUŞ: zaman aşımı — 3 sn cevap yok" in log() and "KONUŞ: süreç kapandı (zaman aşımı)" in log() and f"Defter geldi: {AD2}" in k12["cevap"])
    ok("v0.42.0: takılan soruda (test ayarı) 1,5 sn sonra bekleme cümlesi söylendi, yalnız bir kez (yeniden gönderimde tekrar yok)", log().count("KONUŞ: bekleme cümlesi") == 1)
    k13 = sor("Donma denemesi var mı?")
    ok("ikinci denemede de cevap yoksa panoda hata", k13["durum"] == "hata" and "cevap vermedi" in (k13.get("hata") or "") and "ikinci denemede de 6 sn cevap yok" in log())
    ok(f"v0.113.1: cevap gecikince (test ayarı 2 sn) ara bilgi — iki takılan soruda birer kez ({log().count('KONUŞ: ara bilgi')})", log().count("KONUŞ: ara bilgi (2 sn cevap yok)") == 2)
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/ping", data=json.dumps({"call": True, "panel": True}).encode(), headers={"X-Suflor-Anahtar": K}))
    ok("toplantı sürerken panoda defter satırı yok", st().get("defter") is None)
    # S48 (v0.35.0): toplantı sırasında aynı konuşan süreç — kulaklık yok (SUFLOR_TEST_KULAKLIK=0): cevap okunmaz, yalnız panoda
    ses0 = log().count("SES (deneme)")
    k14 = sor("Toplantıda ne konuşuldu?")
    ok("toplantı sürerken Konuş: cevap geldi, bağlamda 'Toplantı sürüyor … yalnız panoda'", k14["durum"] == "hazir" and "Toplantı bağlamı geldi" in (k14.get("cevap") or ""))
    ok("kulaklık yokken toplantıda cevap okunmadı", log().count("SES (deneme)") == ses0)
    def ben(i, metin): uc2("/ingest", {"meeting": {"title": "Başka toplantı"}, "source": "whisper", "entries": [{"id": f"w/{i}", "speaker": "Deniz T", "time": f"11:0{i}:00", "text": metin, "kanal": "ben"}]})
    ben(1, "Suflor, bütçe ne kadardı?"); t0 = time.time()
    while time.time() - t0 < 30 and not (st().get("kaynak") == "hitap" and st()["durum"] in ("hazir", "hata")): time.sleep(0.2)
    k15 = st(); c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    jl = [json.loads(l) for f in os.listdir(canli) if f.endswith(".jsonl") and not f.startswith("claude") for l in open(os.path.join(canli, f)) if '"w/1"' in l]
    ok("sesli 'Suflor, …' sorusu konuşana gitti, cevap panoda", k15["durum"] == "hazir" and "bütçe ne kadardı" in (k15.get("soru") or "") and "Sorduğun" in (k15.get("cevap") or "")
       and c[-1].get("kaynak") == "hitap" and c[-1].get("toplantida") is True and c[-1].get("sesli") is False)
    ok("döküm satırında konusan işareti (izle: toplantı oturumu cevap kartı yazmaz)", bool(jl) and jl[-1].get("konusan") is True)
    # 30 Ekim (bulgu 9): cevaptan sonra hitap_devam_sn (20) içinde adsız soru da konuşana gider; karşı taraf konuşunca pencere kapanır
    time.sleep(1.0); c0 = len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines())
    ben("1b", "Peki bu bütçe kimde kaldı?"); t0 = time.time()
    while time.time() - t0 < 30 and not (len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) > c0 and st()["durum"] in ("hazir", "hata")): time.sleep(0.2)
    ok("adsız devam sorusu (cevaptan sonra 20 sn içinde) konuşana gitti", "KONUŞ: devam sorusu (ad olmadan" in log() and "kimde kaldı" in (st().get("soru") or ""))
    time.sleep(1.0); karsi_ = lambda i, metin: uc2("/ingest", {"meeting": {"title": "Başka toplantı"}, "source": "whisper", "entries": [{"id": f"kd/{i}", "speaker": "Ayla Ö", "time": f"11:0{i}:30", "text": metin, "kanal": "karsi"}]})
    karsi_(1, "Bence bunu yarın tekrar konuşalım."); time.sleep(0.5); nd = log().count("KONUŞ: devam sorusu (ad olmadan")
    ben("1c", "Peki takvim ne durumda?"); time.sleep(1.0)
    ok("karşı taraf konuşunca devam penceresi kapandı, adsız soru gitmedi", "devam penceresi kapandı — karşı taraf konuştu" in log() and log().count("KONUŞ: devam sorusu (ad olmadan") == nd)
    n0 = log().count("konuşana gitti")
    ben(2, "Claude: kuyruğa al teklif e-postasını."); time.sleep(1)
    jl2 = [json.loads(l) for f in os.listdir(canli) if f.endswith(".jsonl") and not f.startswith("claude") for l in open(os.path.join(canli, f)) if '"w/2"' in l]
    ok("iş talimatı ('kuyruğa al') konuşana gitmedi, toplantı oturumunda kaldı", log().count("konuşana gitti") == n0 and bool(jl2) and not jl2[-1].get("konusan"))
    # v0.55.0: toplantıda Konuş'a basılı tutup söylenen iş talimatı Claude'a gitmez, dökümde kullanıcının notu olarak "Claude: …" (toplantı oturumu uygular)
    cagri1 = len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines())
    kis = sor("Ayla'ya bütçe için bir e-posta taslağı hazırla.")
    md_ = "".join(open(os.path.join(canli, f), encoding="utf-8").read() for f in os.listdir(canli) if f.endswith(".md"))
    ok("Konuş'la iş talimatı: Claude'a gitmedi, dökümde 'Claude: … (Konuş düğmesiyle)' notu, panoda kısa onay", kis["durum"] == "hazir" and "hallediyorum" in (kis.get("cevap") or "")
       and len(open(os.path.join(canli, "claude-cagri.jsonl")).readlines()) == cagri1 and "(Konuş düğmesiyle)" in md_ and "taslağı hazırla" in md_.lower() and "iş talimatı toplantı oturumuna iletildi" in log())
    n2 = log().count("konuşana gitti"); ben(3, "Claude, perşembe saat on dörde Ayla ile toplantı koy."); time.sleep(1)
    ok("sesli 'Claude, … toplantı koy' konuşana gitmedi (iş talimatı)", log().count("konuşana gitti") == n2)
    # v0.46.0: konuşurken yazıya dökme — kayıt saniyede bir parça gelir, duraksamada ilk kısım Whisper'a gider; bırakışta yalnız kuyruk dökülür
    while st()["durum"] not in ("hazir", "hata", "kapali"): time.sleep(0.2)
    pb = base64.b64decode(pcm("Yarın saat onda toplantı var. [[slnc 900]] Bütçe konusunu da konuşacak mıyız acaba?")) + b"\x00\x00" * int(16000 * 0.7)  # konuşma bitince tuş ~0,7 sn sonra bırakılır
    post({"komut": "basla"}); n0a = log().count("akış parçası")
    for i in range(0, len(pb), 32000): post({"komut": "parca", "pcm": base64.b64encode(pb[i:i + 32000]).decode()}); time.sleep(1.0)
    time.sleep(0.5); post({"pcm": base64.b64encode(pb).decode()}); t0 = time.time()
    while time.time() - t0 < 60 and st()["durum"] not in ("hazir", "hata"): time.sleep(0.2)
    k17 = st(); c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    ok(f"akış: konuşurken parça Whisper'a gitti, bırakışta birleşti, soru iki cümleyi içeriyor ({(k17.get('soru') or '')[:70]!r}, yazıya {c[-1].get('wh_ms')} ms)",
       log().count("akış parçası") > n0a and "parça birleşti" in log() and k17["durum"] == "hazir" and "toplantı" in (k17.get("soru") or "").lower() and "bütçe" in (k17.get("soru") or "").lower())
    p2 = base64.b64encode(pb).decode()
    post({"komut": "basla"}); time.sleep(1.0); post({"pcm": p2}); t0 = time.time()
    while time.time() - t0 < 60 and st()["durum"] not in ("hazir", "hata"): time.sleep(0.2)
    c2 = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    print(f"   yazıya dökme: akışlı {c[-1].get('wh_ms')} ms · akışsız {c2[-1].get('wh_ms')} ms")
    ok("akışlı yazıya dökme akışsızdan kısa", (9e9 if c[-1].get("wh_ms") is None else c[-1]["wh_ms"]) < (c2[-1].get("wh_ms") or 0))  # 0 ms: parçalar bırakıştan önce bitti
    # v0.44.0: karşı tarafın "Suflor, …" sorusu (Whisper yazımı "Süflör") konuşana, soranın adıyla; iş talebi ve tetiksiz satır gitmez
    def karsi(i, metin): uc2("/ingest", {"meeting": {"title": "Başka toplantı"}, "source": "whisper", "entries": [{"id": f"k/{i}", "speaker": "Ayla Ö", "time": f"11:1{i}:00", "text": metin, "kanal": "karsi"}]})
    karsi(1, "Süflör, bu projenin teslim tarihi ne?"); t0 = time.time()
    while time.time() - t0 < 30 and not (st().get("kaynak") == "karsi" and st()["durum"] in ("hazir", "hata")): time.sleep(0.2)
    k16 = st(); c = [json.loads(l) for l in open(os.path.join(canli, "claude-cagri.jsonl"))]
    jl3 = [json.loads(l) for f in os.listdir(canli) if f.endswith(".jsonl") and not f.startswith("claude") for l in open(os.path.join(canli, f)) if '"k/1"' in l]
    ok("karşı tarafın 'Süflör, …' sorusu konuşana gitti (soranın adıyla), cevap panoda, satırda konusan", k16["durum"] == "hazir" and (k16.get("soru") or "").startswith("Ayla Ö")
       and "Sorduğun" in (k16.get("cevap") or "") and c[-1].get("kaynak") == "karsi" and bool(jl3) and jl3[-1].get("konusan") is True)
    n1 = log().count("konuşana gitti")
    karsi(2, "Suflor, not al bunu lütfen."); karsi(3, "Teslim tarihi cuma olabilir mi?"); karsi(4, "Suflör'ün dediği doğru."); time.sleep(1)
    ok("karşı tarafta iş talebi, hitapsız satır ve ek almış ad konuşana gitmedi", log().count("konuşana gitti") == n1)
    # v0.52.0 hızlı sesli özet: tarayıcıda çağrı bitince (üst çerçeve nabzı call=false) Konuş sürecine üç cümlelik özet sorulur ve okunur; yazılı özet ikinci kez okunmaz
    for i in range(5, 10): ben(i, f"Toplantıda {i}. madde konuşuldu, karar alındı.")
    uc2("/ping", {"meeting": {"title": "Başka toplantı"}, "call": True, "panel": True, "mic": {"on": True}}); time.sleep(0.5)
    ses1 = log().count("SES (deneme)")
    uc2("/ping", {"meeting": {"title": "Başka toplantı"}, "call": False, "panel": False, "mic": {"on": False}})
    t1 = time.time()
    while time.time() - t1 < 25 and not ("ÖZET (hızlı)" in log() and st()["durum"] == "hazir" and "az önce bitti" in (st().get("soru") or "")): time.sleep(0.3)
    ko = st(); dosya_ = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/status", headers={"X-Suflor-Anahtar": K})).read()).get("file")
    ok(f"hızlı sesli özet: çağrı bitince Konuş'a soruldu ve okundu ({round(time.time() - t1, 1)} sn)", "ÖZET (hızlı): toplantıdan çıkış (tarayıcı)" in log() and "az önce bitti" in (ko.get("soru") or "") and log().count("SES (deneme)") > ses1)
    oz_ = os.path.join(T, "ozet-deneme.md"); open(oz_, "w").write("# Özet\n")
    uc2("/son-toplanti", {"ozet": oz_, "dosya": dosya_, "baslik": "Başka toplantı", "degerlendirme": "İyi geçti."}); time.sleep(1)
    ok("yazılı özet gelince ikinci kez okunmadı", "hızlı özet okunmuştu, yeniden okunmadı" in log())
    # v0.64.0 (S76): Konuş geçmişi — kullanıcının kendi soruları; karşı tarafın sorusu ve hızlı özet girmez; toplantıdaki soruda toplantı adı; 0600; dizinde konuşma türü
    gp = os.path.join(canli, "konus-gecmis.jsonl"); gk = [json.loads(l) for l in open(gp, encoding="utf-8")] if os.path.exists(gp) else []
    ok(f"Konuş geçmişi: {len(gk)} kayıt, karşı taraf ve hızlı özet yok, toplantıdaki soruda toplantı adı, 0600",
       len(gk) >= 10 and not any(str(x["soru"]).startswith("Ayla Ö") or "az önce bitti" in x["soru"] for x in gk) and any(x.get("toplanti") for x in gk)
       and any("bütçe ne kadardı" in x["soru"] and x.get("kaynak") == "hitap" for x in gk) and all(x["sesli"] for x in gk) and (os.stat(gp).st_mode & 0o777) == 0o600)
    import sqlite3 as _sq; _db = _sq.connect(os.path.join(T, "dizin.sqlite"))
    ok("Konuş geçmişi arama dizininde (konuşma türü, tek dosya güncellemesiyle)", (_db.execute("SELECT tur, parca FROM dosya WHERE yol = ?", (gp,)).fetchone() or ("", 0))[0] == "konusma")
    # v0.51.1 okuma sınırı: _konus_cumle beş cümlelik cevabın yalnız üçünü okur (işlev doğrudan; uçtan uca akışta tur sayısını bozmasın)
    import re as _re
    kod_ = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
    import threading as _th0
    ad_ = {"re": _re, "time": time, "threading": _th0, "print": lambda *a, **k: None, "konusma_dili": lambda m: m, "SES": {"kes": 0}, "kisilik_sesi": lambda *a, **k: ("pocket", None, 1.0)}; okunan_ = []; ad_["seslendir"] = lambda m, kuyruk=False, cal=None, ozet=False: okunan_.append(m) or True
    exec(kod_[kod_.index("KONUS_OKU_EN_COK = "):kod_.index("def _konus_oku(")], ad_)
    t_ = {"tampon": "Vay! Birinci cümle burada. İkinci cümle de var. Üçüncü cümle geliyor. Dördüncü cümle de. Beşinci cümle son. Altıncı okunmamalı. Yedinci de okunmamalı"}
    ad_["_konus_cumle"](t_); ad_["_konus_cumle"](t_, son=True)
    ok(f"okuma en çok beş cümle ('Vay!' sayılmaz; okunan {len(okunan_)})", okunan_[-1].startswith("Beşinci") and len(okunan_) == 6 and t_.get("kesik"))
    # v0.54.0 anlamsız söz: Whisper'ın "!" gibi metni Claude'a gitmez
    ad2 = {"re": _re}; exec(kod_[kod_.index("KONUS_SES_SOZ = "):kod_.index("# İş talimatı (toplantı")], ad2)
    ok("anlamsız söz Claude'a gitmez ('!', 'Hı hı.', 'A.'), gerçek söz gider ('Evet.', soru)", all(ad2["konus_anlamsiz"](x) for x in ("!", "?", "Hı hı.", "A.", "Ee, ıı.")) and not any(ad2["konus_anlamsiz"](x) for x in ("Evet.", "Bugün ne var?", "Tamam")))
    # v0.125.2 (23 Ekim üçlü sohbet ikinci denemesi): ses etiketi ve İngilizce uydurma kırpılır; ilk parça "en" + Türkçe söz → kayıt Türkçe yeniden çözülür
    ad4 = {"re": _re}; exec(kod_[kod_.index("KONUS_TR_RX = "):kod_.index("def _konus_yeniden_coz")], ad4); kr = lambda x: ad4["konus_uydurma_kirp"](x)[0]
    ok("uydurma: '- Thank you. Evet…' ve '*sad* …' kırpılır, '[Music]' kırpılır; tek başına 'Thank you.' ve İngilizce cümle kalır",
       kr("- Thank you. Evet, ben de İnce Memed'i seçiyorum.") == "Evet, ben de İnce Memed'i seçiyorum." and kr("*sad* İnce Memed'i bırakalım, başka kitap konuşalım.") == "İnce Memed'i bırakalım, başka kitap konuşalım."
       and kr("[Music] Tamam arkadaşlar, başlayalım.") == "Tamam arkadaşlar, başlayalım." and kr("Thank you.") == "Thank you." and kr("Thank you for the update, see you tomorrow.") == "Thank you for the update, see you tomorrow."
       and kr("Bence film güzeldi, izleyelim. Thank you for watching!") == "Bence film güzeldi, izleyelim." and kr("Peki.") == "Peki.")
    import threading as _th
    ad5 = {"re": _re, "time": time, "threading": _th, "print": lambda *a, **k: KAYIT5.append(" ".join(map(str, a))), "ARAYUZ_DILI": "tr", "AYAR": {}, "SORU": {}, "WH_SR": 16000,
           "AKIS": {"pcm": bytearray(), "kesik": 0, "metin": {}, "bekleyen": 0, "sira": 0, "kilit": _th.Lock(), "kosul": _th.Condition(), "nesil": 0},
           "_rms": lambda b: 5000, "sohbet_ses_izi_red": lambda iz: False, "AKIS_PENCERE": 640}; KAYIT5 = []
    exec(kod_[kod_.index("KONUS_DIL_SN, KONUS_DIL_EN_AZ_SN = "):kod_.index("def _akis_kesim(")], ad5); exec(kod_[kod_.index("def _akis_birlestir("):kod_.index("def konus_basla(")], ad5)
    ad5["_akis_sifirla"] = lambda: ad5["AKIS"].update(pcm=bytearray(), kesik=0, metin={}, sira=0, dil=None); YC = []
    ad5["_konus_yeniden_coz"] = lambda pcm, dil, sn=20.0: (YC.append((len(pcm), dil)), "Evet, ben de İnce Memed'i seçiyorum.")[1]
    def birles(metinler, dil):
        A = ad5["AKIS"]; pcm = b"\x01" * 32000 * len(metinler); A.update(pcm=bytearray(pcm), kesik=len(pcm), sira=len(metinler), metin=dict(enumerate(metinler)), dil=dil, bekleyen=0)
        out = []; ev = _th.Event(); ad5["_akis_birlestir"](pcm, lambda m, h: (out.append(m), ev.set())); ev.wait(3); return out[0] if out else None
    ad5["_KDIL"].update(son="en", t=time.time()); r1 = birles(["- Thank you. Evet, ben de", "İnce Memed'i seçiyorum."], "en")
    ok(f"dil: ilk parça 'en', söz Türkçe → bütün kayıt Türkçe yeniden çözülür, dil Türkçeye döner ({r1!r})", r1 == "Evet, ben de İnce Memed'i seçiyorum." and YC == [(64000, "tr")] and ad5["konus_dil_son"]() == "tr")
    YC.clear(); r2 = birles(["Let me check the", "budget for next week."], "en"); r3 = birles(["Bugün ne var", "takvimde?"], "tr")
    ok("dil: gerçek İngilizce söz ve Türkçe bulunan söz yeniden çözülmez", r2 == "Let me check the budget for next week." and r3 == "Bugün ne var takvimde?" and YC == [])
    ok("bekleme cümlelerinde ve istemde 'şey' yok", "Şey" not in kod_[kod_.index("BEKLE_GENEL = "):kod_.index("BEKLE_TUR = ")] and "'Şey,'" not in kod_[kod_.index("KONUS_ISTEM = {"):kod_.index("# --- Hızlı bilgi")])
    # v0.57.5 veritabanı tazelik notu: son vt_sor'dan sonra dosya değişince bir kez; okunamazsa son sorgu VT_TAZE_SN'den eskiyse
    vtd = os.path.join(proje, "vt.db"); open(vtd, "w").close()
    ad3 = {"os": os, "time": time, "json": json, "BASE": proje, "print": lambda *a: None, "_t": lambda tr, en: tr, "AYAR": {"proje": proje, "veritabani": {"yol": "vt.db"}}, "_KS": {}}
    exec(kod_[kod_.index("VT_TAZE_SN = "):kod_.index("BRIFING_YASAK = ")], ad3)
    ks = ad3["_KS"]; n0 = ad3["_vt_tazele_notu"]()
    ks["vt_son"] = (time.time(), ad3["_vt_mt"]()); n1 = ad3["_vt_tazele_notu"]()
    os.utime(vtd, (time.time() + 5, time.time() + 5)); n2 = ad3["_vt_tazele_notu"](); n3 = ad3["_vt_tazele_notu"]()
    ad3["AYAR"]["veritabani"]["yol"] = "yok.db"; ks["vt_son"] = (time.time() - 700, None); n4 = ad3["_vt_tazele_notu"]()
    ks["vt_son"] = (time.time() - 60, None); n5 = ad3["_vt_tazele_notu"]()
    ok("veritabanı tazelik notu: sorgu yokken ve değişmeden yok, değişince bir kez, okunamazsa 10 dk sonra",
       not n0 and not n1 and "değişti" in n2 and "vt_sor" in n2 and not n3 and "11 dk önce" in n4 and not n5)
    # v0.58.2: dosya okunamazsa araç sunucusunun vt-mt.json'ı (taze) — değişme yine anlaşılır; eski kayıt sayılmaz
    mtj = os.path.join(proje, "vt-mt.json"); json.dump({"mt": 1000.0, "kontrol": time.time()}, open(mtj, "w"))
    ks["vt_son"] = (time.time(), ad3["_vt_mt"]()); n6 = ad3["_vt_tazele_notu"]()
    json.dump({"mt": 2000.0, "kontrol": time.time()}, open(mtj, "w")); n7 = ad3["_vt_tazele_notu"]()
    json.dump({"mt": 3000.0, "kontrol": time.time() - 400}, open(mtj, "w")); m8 = ad3["_vt_mt"](); os.remove(mtj)
    ok("tazelik: dosya okunamazsa araç sunucusunun değişme saati (vt-mt.json) kullanılır, eskisi sayılmaz",
       ks["vt_son"][1] == 1000.0 and not n6 and "değişti" in (n7 or "") and m8 is None)
    ok("not soruyla gider, vt_sor turu tazelik kaydını yeniler", "vt_sor çağırmadan\" in bz" in kod_ and 'any("suflorvt__vt_so" in x for x in tur.get("araclar")' in kod_)
    # v0.57.6 önceki benzer sorunun sorgusu: vt_sor sorgusu soruyla kaydedilir; yeni süreçte benzer soruya not, açık süreçteki ya da ilgisiz soruya yok
    import datetime as _dt
    ad3.update({"re": _re, "json": json, "datetime": _dt, "BASE": canli, "AYAR": {"proje": proje, "veritabani": {"yol": "vt.db"}}})
    ks["acilis_t"] = 0; ad3["_vt_sorgu_kaydet"]("Şu anda en fazla admin yetkisi kimde?", ["SELECT kisi, COUNT(*) FROM v_yetki WHERE rol='admin' GROUP BY kisi"]); ks["acilis_t"] = time.time() + 5  # sonra açılan süreç
    b1 = ad3["_vt_benzer_notu"]("Admin yetkisi en fazla kimde şu an?"); b2 = ad3["_vt_benzer_notu"]("Yarın hava nasıl olacak?")
    ks["acilis_t"] = 0; b3 = ad3["_vt_benzer_notu"]("Admin yetkisi en fazla kimde şu an?"); ks["acilis_t"] = time.time() + 5  # kayıttan önce açılmış süreç
    ad3["AYAR"] = {"proje": proje}; b4 = ad3["_vt_benzer_notu"]("Admin yetkisi en fazla kimde şu an?"); ad3["AYAR"] = {"proje": proje, "veritabani": {"yol": "vt.db"}}
    for i in range(70): ad3["_vt_sorgu_kaydet"](f"soru {i}", ["SELECT 1"])
    sat_ = open(os.path.join(canli, "konus-sorgu.jsonl"), encoding="utf-8").read().splitlines()
    ok("benzer soru: yeni süreçte önceki sorgu notu, ilgisiz/açık süreç/veritabanısız soruda yok, kayıt 60 satırda kalır",
       "v_yetki" in b1 and "yeniden çalıştır" in b1 and not b2 and not b3 and not b4 and len(sat_) == 60)
    # v0.77.0 özel ad farkı: farklı kişinin aynı sorusu benzer sayılmaz; aynı kişinin kısa/tam adı ve adsız eş anlamlı soru sayılır
    ks["acilis_t"] = 0; ad3["_vt_sorgu_kaydet"]("Ali'nin açık işleri neler?", ["SELECT * FROM v_is WHERE kisi='Ali'"]); ks["acilis_t"] = time.time() + 5
    a1 = ad3["_vt_benzer_notu"]("Ayşe'nin açık işleri neler?"); a2 = ad3["_vt_benzer_notu"]("Açık işler neler, Ali'nin?"); a3 = ad3["_vt_benzer_notu"]("Açık işleri neler?")
    ks["acilis_t"] = 0; ad3["_vt_sorgu_kaydet"]("Bugün Kemal Demir ile açık işleri konuştuk mu?", ["SELECT 2"]); ks["acilis_t"] = time.time() + 5
    a4 = ad3["_vt_benzer_notu"]("Kemal'le bugün açık işleri konuştuk mu?")
    ok("özel ad: Ali ↔ Ayşe eşleşmez, Ali ↔ Ali eşleşir, adsız soru adlı soruyla eşleşmez, Kemal ⊆ Kemal Demir eşleşir",
       not a1 and "kisi='Ali'" in a2 and "kisi='Ali'" not in a3 and "SELECT 2" in a4)
    if not (not a1 and "kisi='Ali'" in a2 and "kisi='Ali'" not in a3 and "SELECT 2" in a4): print("   ", repr(a1)[:80], repr(a2)[:80], repr(a3)[:80], repr(a4)[:80])
    ok("vt_sor girdisi akıştan toplanır, karşı tarafın sorusunda not ve kayıt yok", '"input_json_delta"' in kod_ and "_vt_benzer_notu(metin) if tur.get(\"kaynak\") != \"karsi\" and not tur.get(\"karsi\")" in kod_)
    # v0.57.8 taze sonuç: veritabanı aracının önbelleğinde 150 sn içinde denetlenmiş sonuç varsa not sonucu taşır ve "vt_sor çağırmadan" der (açık süreçte de)
    q_ = "SELECT kisi, COUNT(*) FROM v_yetki WHERE rol='admin' GROUP BY kisi"
    json.dump({q_: {"t": time.time(), "kontrol": time.time() - 20, "mt": None, "sonuc": "kisi\tn\nAyla\t5\n(1 satır)"}}, open(os.path.join(canli, "vt-sonuc.json"), "w"))
    ks["acilis_t"] = 0; ad3["_vt_sorgu_kaydet"]("Şu anda en fazla admin yetkisi kimde?", [q_])
    c1 = ad3["_vt_benzer_notu"]("Admin yetkisi en fazla kimde şu an?")
    json.dump({q_: {"t": time.time() - 900, "kontrol": time.time() - 400, "mt": None, "sonuc": "eski"}}, open(os.path.join(canli, "vt-sonuc.json"), "w"))
    c2 = ad3["_vt_benzer_notu"]("Admin yetkisi en fazla kimde şu an?")
    ok("taze önbellek sonucu: açık süreçte de notta sonuç + 'vt_sor çağırmadan'; bayatsa (400 sn) açık süreçte not yok",
       "Ayla\t5" in c1 and "vt_sor çağırmadan" in c1 and not c2)
    # v0.101.1: Claude'un hazırladığı oturum iletisi (kalıp tutmadığında) — istemde yol var, etiket okunmaz/panoda görünmez, aynı onay yoluna girer
    while st()["durum"] not in ("hazir", "hata", "kapali"): time.sleep(0.2)
    ses0 = len(re.findall(r"SES \(deneme\).*", log()))
    kt = sor("R12 işini listeden çıkaralım lütfen.")
    t0 = time.time()
    while time.time() - t0 < 5 and "Claude hazırladı" not in log(): time.sleep(0.2)
    okunan = "\n".join(re.findall(r"SES \(deneme\).*", log())[ses0:])
    ist = json.load(open(os.path.join(canli, "konus-istek.json")))["args"]
    ok("istemde oturuma ileti yolu ve hedef (iki kişilikte de ortak kısımda)", any("[İLET <hedef>: <ileti>]" in a and "proje = " in a for a in ist))
    ok("Claude'un [İLET …] etiketi okunmadı, panoda görünmedi; ileti onaya sunuldu (aynı yol)", kt["durum"] == "hazir" and "iletiyi hazırladım" in (kt.get("cevap") or "")
       and "[İLET" not in (kt.get("cevap") or "") and "İLET" not in okunan and "R12" not in "\n".join(okunan.split("\n")[:next((i for i, x in enumerate(okunan.split("\n")) if "İleteyim mi?" in x), 0)]) and "İleteyim mi?" in okunan
       and "TALİMAT: Claude hazırladı · oturum → proje onay bekliyor" in log())
    if "TALİMAT: Claude hazırladı" not in log(): print("   okunan:", okunan[:300], "| cevap:", (kt.get("cevap") or "")[:200])
    # v0.117.0 (S136): toplantı yokken pano kutusundaki soru asistana yazılı gider — cevap panoda, sesli okunmaz. Ayrı deneme aktarıcısıyla
    # (bu aktarıcıda toplantılar geçti, toplantısız durum yok; yukarıdaki süreç sayaçları ve ölçüm sırası da bozulmasın)
    canli2 = os.path.join(T, "canli2"); os.makedirs(canli2); P2 = bos_port(PORT + 7)
    r2 = subprocess.Popen([sys.executable, "relay.py", "--dir", canli2, "--port", str(P2)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
                          stdout=open(os.path.join(T, "relay2.log"), "w"), stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            if os.path.exists(os.path.join(canli2, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); H2 = {"X-Suflor-Anahtar": open(os.path.join(canli2, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{P2}"}
        g = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{P2}/girdi", data=json.dumps({"text": "?Yazılı kutu sorusu"}).encode(), headers=H2), timeout=20).read())
        st2 = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{P2}/status", headers=H2), timeout=10).read())["konus"]
        t0 = time.time()
        while time.time() - t0 < 40 and not ("Yazılı kutu" in (st2().get("soru") or "") and st2()["durum"] in ("hazir", "hata")): time.sleep(0.3)
        k = st2(); l2 = open(os.path.join(T, "relay2.log"), encoding="utf-8").read()
        ok("v0.117.0: toplantı yokken kutudaki soru asistana yazılı, cevap panoda, okunmadı, döküm açılmadı", g.get("tur") == "asistan" and k["durum"] == "hazir"
           and "Sorduğun" in (k.get("cevap") or "") and "SES (deneme)" not in l2 and not [f for f in os.listdir(canli2) if f.endswith(".md")] and "Traceback" not in l2)
    finally: r2.terminate(); r2.wait()
    # Faz 11 Aşama 2: Konuş başka sağlayıcıda (beyin.konus; sahte OpenAI uyumlu sunucu hep 503) → soru bir kez Claude Code'la (sahte claude), günlükte BEYİN: yedek
    import http.server, threading
    GL = []
    class _S503(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *a): pass
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"])); GL.append(1); b_ = b'{"error":{"message":"high demand"}}'
            self.send_response(503); self.send_header("Content-Length", str(len(b_))); self.end_headers(); self.wfile.write(b_)
    P3s = bos_port(PORT + 9); SV3 = http.server.ThreadingHTTPServer(("127.0.0.1", P3s), _S503); threading.Thread(target=SV3.serve_forever, daemon=True).start()
    ay3 = os.path.join(T, "ayar3.json"); a3 = json.load(open(ay)); a3["beyin"] = {"konus": {"tur": "openai-uyumlu", "saglayici": "gemini", "adres": f"http://127.0.0.1:{P3s}/v1", "model": "gemini-3.8-flash"}}
    P3 = bos_port(PORT + 11); a3["port"] = P3; json.dump(a3, open(ay3, "w"))
    canli3 = os.path.join(T, "canli3"); os.makedirs(canli3)
    r3 = subprocess.Popen([sys.executable, "relay.py", "--dir", canli3, "--port", str(P3)], cwd=T, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SUFLOR_AYAR=ay3, SUFLOR_TEST_BASLAT="1", SUFLOR_TEST_KULAKLIK="0"),
                          stdout=open(os.path.join(T, "relay3.log"), "w"), stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            if os.path.exists(os.path.join(canli3, "kart-anahtari.txt")): break
            time.sleep(0.2)
        time.sleep(1); H3 = {"X-Suflor-Anahtar": open(os.path.join(canli3, "kart-anahtari.txt")).read().strip(), "Origin": f"http://127.0.0.1:{P3}"}
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{P3}/girdi", data=json.dumps({"text": "?Yedek deneme sorusu"}).encode(), headers=H3), timeout=20).read()
        st3 = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{P3}/status", headers=H3), timeout=10).read())["konus"]
        t0 = time.time()
        while time.time() - t0 < 60 and not (("Sorduğun" in (st3().get("cevap") or "") and st3()["durum"] == "hazir") or st3()["durum"] == "hata"): time.sleep(0.3)
        time.sleep(1)  # ölçüm satırı cevaptan sonra yazılır
        k3 = st3(); l3 = open(os.path.join(T, "relay3.log"), encoding="utf-8").read()
        cg3 = [json.loads(x) for x in open(os.path.join(canli3, "claude-cagri.jsonl"))] if os.path.exists(os.path.join(canli3, "claude-cagri.jsonl")) else []
        ok("Aşama 2: sağlayıcı 503 → Konuş sorusu bir kez Claude Code'la cevaplandı (günlükte tek BEYİN: yedek, kayıtta iki sağlayıcı)", GL and k3["durum"] == "hazir" and "Yedek deneme" in (k3.get("cevap") or "")
           and l3.count("BEYİN: yedek — konus: gemini") == 1 and [x.get("saglayici") for x in cg3 if x.get("is") == "bas-konus"] == ["gemini", "claude-code"] and "Traceback" not in l3)
        if k3["durum"] != "hazir" or "BEYİN: yedek" not in l3: print("   ", k3, l3[-800:])
    finally: r3.terminate(); r3.wait(); SV3.shutdown()
    ok("aktarıcıda hata yok", "Traceback" not in log())
finally:
    r.terminate(); r.wait(); subprocess.run(["pkill", "-f", T])
print("bas-konuş:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
