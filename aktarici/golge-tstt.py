# Gölge kipte turkish-stt (ayar golge_tstt, varsayılan kapalı; geliştirici denemesi): Whisper'a giden aynı ses yerel turkish-stt akış tanıyıcısına da verilir,
# döküme hiçbir şey girmez; ekrana yalnız ayar tstt_taslak (varsayılan açık) ile soluk "anlık ilk yazı" taslağı düşer (whisper-hat.py taslak_tstt), Whisper satırı gelince yerine geçer; yalnız ses arşivi klasörüne tstt-golge.jsonl yazılır (kıyas: _yedek/test-araclari/tstt-golge/kiyas.py). Ses Mac'ten çıkmaz.
# İşçi ayrı süreç (tstt-golge-isci.py, tstt-venv Python'u): kuyruk dolarsa parça bekletmeden atılır (dusen), 10 dk ses gelmezse kapanır, çökerse saatte ≤ 3 kez yeniden açılır.
import queue, subprocess, base64
GOLGE_PY = os.path.join(_ORT, "tstt-venv", "bin", "python"); GOLGE_MODEL = os.path.join(_ORT, "tstt-model")
GOLGE_ISCI = _ilk(os.path.join(_UYG, "tstt-golge-isci.py"), os.path.join(_APP, "tstt-golge-isci.py"))
GOLGE_BOSTA_SN = 600; GOLGE_COKME_SAAT = 3
GOLGE_Q = queue.Queue(maxsize=300); _GL = {"th": None, "p": None, "t": 0, "cokme": [], "dur": 0, "kilit": threading.Lock()}
STATE["golge_tstt"] = {"durum": "kapali", "dusen": 0, "satir": 0}
def _golge_yollar(): return AYAR.get("tstt_python") or GOLGE_PY, AYAR.get("tstt_model") or GOLGE_MODEL
def golge_acik():
    if AYAR.get("golge_tstt") is not True: return False
    py, md = _golge_yollar(); return os.path.exists(py) and os.path.isdir(md) and os.path.exists(GOLGE_ISCI)
def golge_besle(kanal, t_sn, pcm):
    try:
        if not golge_acik() or gizli_acik() or time.time() < _GL["dur"]: return
        _GL["t"] = time.time()
        try: GOLGE_Q.put_nowait({"k": kanal, "t": round(float(t_sn), 3), "pcm": base64.b64encode(pcm).decode()})
        except queue.Full: STATE["golge_tstt"]["dusen"] += 1
        with _GL["kilit"]:
            if not (_GL["th"] and _GL["th"].is_alive()): _GL["th"] = threading.Thread(target=_golge_dongu, daemon=True); _GL["th"].start()
    except Exception as e: print(f"GÖLGE TSTT: besleme hatası ({e.__class__.__name__})")
def _golge_oku(p):  # işçinin stdout'u → tstt-golge.jsonl (satırın yazıldığı andaki toplantı klasörü)
    for l in p.stdout:
        try:
            o = json.loads(l)
            if o.get("tur") == "ara":  # anlık ilk yazı (ayar tstt_taslak): yalnız taslak deposuna, tstt-golge.jsonl'a yazılmaz
                if "taslak_tstt" in globals(): taslak_tstt(str(o.get("k")), o.get("metin"), o.get("t"))
                continue
            if o.get("tur") == "hazir": STATE["golge_tstt"]["durum"] = "calisiyor"; print(f"GÖLGE TSTT: işçi hazır ({o.get('yukleme_sn')} sn)")
            yol = os.path.join(ses_arsivi_klasor(), "tstt-golge.jsonl"); os.makedirs(os.path.dirname(yol), exist_ok=True)
            with LOCK: write([(yol, l if l.endswith("\n") else l + "\n")])
            if o.get("tur") == "soz":
                STATE["golge_tstt"]["satir"] += 1
                if "taslak_tstt_bitti" in globals(): taslak_tstt_bitti(str(o.get("k")))
        except Exception as e: print(f"GÖLGE TSTT: satır yazılamadı ({e.__class__.__name__})")
def _golge_kapat(p, durum="kapali"):
    try:
        p.stdin.close()
        try: p.wait(5)
        except subprocess.TimeoutExpired: p.kill(); p.wait(5)
    except Exception: pass
    _GL["p"] = None; STATE["golge_tstt"]["durum"] = durum
def _golge_ac():
    py, md = _golge_yollar(); STATE["golge_tstt"]["durum"] = "yukleniyor"
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.Popen([py, "-I", "-B", GOLGE_ISCI, md], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, bufsize=1, text=True, encoding="utf-8")
    _GL["p"] = p; threading.Thread(target=_golge_oku, args=(p,), daemon=True).start(); return p
def _golge_coktu():
    simdi = time.time(); _GL["cokme"] = [x for x in _GL["cokme"] if simdi - x < 3600] + [simdi]; _GL["p"] = None
    if len(_GL["cokme"]) > GOLGE_COKME_SAAT:
        _GL["dur"] = simdi + 3600; STATE["golge_tstt"]["durum"] = "durdu"; print("GÖLGE TSTT: işçi saatte 3'ten fazla çöktü, bu saat için durduruldu")
    else: STATE["golge_tstt"]["durum"] = "durdu"; print("GÖLGE TSTT: işçi çöktü, yeniden açılacak")
def _golge_dongu():
    while True:
        p = _GL["p"]
        if p and (not golge_acik() or time.time() - _GL["t"] > GOLGE_BOSTA_SN):
            _golge_kapat(p); print("GÖLGE TSTT: işçi kapatıldı (ayar kapandı ya da 10 dk ses gelmedi)"); break
        if not p and not golge_acik(): break
        try: o = GOLGE_Q.get(timeout=5)
        except queue.Empty:
            if not p and time.time() - _GL["t"] > GOLGE_BOSTA_SN: break
            continue
        try:
            if time.time() < _GL["dur"]: continue
            if p and p.poll() is not None: _golge_coktu(); p = None
            if not p:
                if time.time() < _GL["dur"]: continue
                p = _golge_ac()
            p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
        except (BrokenPipeError, OSError): _golge_coktu()
        except Exception as e: print(f"GÖLGE TSTT: yazma hatası ({e.__class__.__name__})")
    while not GOLGE_Q.empty():
        try: GOLGE_Q.get_nowait()
        except queue.Empty: break
