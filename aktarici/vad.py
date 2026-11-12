# Suflor.me aktarıcı bölümü: konuşma algılayıcı istemcisi (Konuş Aşama 2, Adım 3; bolum("vad")). Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır:
# os, json, time, base64, queue, threading, subprocess, _ORT, _UYG, _APP, _ilk, WH_SR bas-konus.py / whisper-hat.py'nin. import etme. Python 3.9 uyumlu.
# vad-isci.py (Silero VAD v6.2.3, MIT) ayrı süreçte, tur-isci.py ile aynı düzen: smart-turn-venv Python'u, stdin/stdout JSON satırı. Model yoksa
# ya da açılamazsa vad_olasilik None döner (çağıran "bilmiyorum" der; araya girme kapalı kalır). Kullanım (Adım 5):
#   vad_baslat()  →  hazır/yükleniyor True, yok/hata False;  vad_olasilik(pcm) → {"son","p","konusma","olay","ms"} ya da None;  vad_sifirla(), vad_kapat().
VAD_URL = "https://github.com/snakers4/silero-vad/raw/v6.2.3/src/silero_vad/data/silero_vad.onnx"  # resmî depo, sürüm etiketli (kurulum.py vad_kur için)
VAD_SHA = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
VAD_PY = os.environ.get("SUFLOR_VAD_PY") or os.path.join(_ORT, "smart-turn-venv", "bin", "python")
VAD_MODEL = os.environ.get("SUFLOR_VAD_MODEL") or os.path.join(_ORT, "ses-modeller", "silero-vad", "silero_vad.onnx")
VAD_ISCI = _ilk(os.path.join(_UYG, "vad-isci.py"), os.path.join(_APP, "vad-isci.py"))
VAD = {"p": None, "durum": None, "kilit": threading.Lock(), "bek": {}, "n": 0, "baslat_t": 0.0}
def _vad_okuyucu(p):
    for sat in p.stdout:
        try: o = json.loads(sat)
        except ValueError: continue
        if o.get("hazir"): VAD["durum"] = "hazir"; print("KONUŞ: konuşma algılayıcı (Silero) hazır"); continue
        if o.get("yok"): VAD["durum"] = "yok"; print("KONUŞ: konuşma algılayıcı modeli yok"); continue
        if "hata" in o and o.get("id") is None: VAD["durum"] = "hata"; print(f"KONUŞ: konuşma algılayıcı açılamadı ({o['hata'][:120]})"); continue
        q = VAD["bek"].pop(o.get("id"), None)
        if q: q.put(o)
    if VAD["p"] is p: VAD.update(p=None, durum="hata" if VAD["durum"] not in ("yok",) else "yok")
def vad_baslat():
    with VAD["kilit"]:
        p = VAD["p"]
        if p and p.poll() is None: return True
        if VAD["durum"] == "yok" or (VAD["durum"] == "hata" and time.time() - VAD["baslat_t"] < 60): return False
        eksik = next((y for y in (VAD_PY, VAD_MODEL, VAD_ISCI) if not y or not os.path.exists(y)), None)
        if eksik is not None:
            VAD["durum"] = "yok"; print(f"KONUŞ: konuşma algılayıcı yok ({os.path.basename(eksik) or 'model'})"); return False
        VAD.update(baslat_t=time.time(), durum="yukleniyor")
        try: p = subprocess.Popen([VAD_PY, "-I", "-B", VAD_ISCI, VAD_MODEL], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        except OSError as e: VAD["durum"] = "hata"; print(f"KONUŞ: konuşma algılayıcı başlatılamadı ({e.__class__.__name__})"); return False
        VAD["p"] = p; threading.Thread(target=_vad_okuyucu, args=(p,), daemon=True).start(); return True
def _vad_gonder(istek, zaman):  # istek JSON → cevap sözlüğü; işçi hazır değilse/geç kalırsa None
    if VAD["durum"] != "hazir" or not VAD["p"]: return None
    q = queue.Queue()
    with VAD["kilit"]:
        VAD["n"] += 1; i = VAD["n"]; VAD["bek"][i] = q
        try: VAD["p"].stdin.write(json.dumps(dict(istek, id=i)) + "\n"); VAD["p"].stdin.flush()
        except (OSError, ValueError): VAD["bek"].pop(i, None); return None
    try: return q.get(timeout=zaman)
    except queue.Empty: VAD["bek"].pop(i, None); print("KONUŞ: konuşma algılayıcı geç kaldı"); return None
def vad_olasilik(pcm, esik=None, min_konusma_ms=None, min_sessizlik_ms=None, zaman=0.25):
    # int16 16 kHz mono öbek (herhangi uzunluk; 512 örnekten artan kısım sonraki çağrıya kalır) → {"son", "p"[], "konusma", "olay"[], "ms"}; hazır değilse None
    o = _vad_gonder({"pcm": base64.b64encode(bytes(pcm)).decode(), "esik": esik, "min_konusma_ms": min_konusma_ms, "min_sessizlik_ms": min_sessizlik_ms}, zaman)
    return o if o and "hata" not in o else None
def vad_sifirla(zaman=0.25):  # yeni konuşma/tur başında model durumunu ve olay makinesini sıfırla
    return bool(_vad_gonder({"sifirla": True}, zaman))
def vad_kapat():
    with VAD["kilit"]:
        p, VAD["p"] = VAD["p"], None
        if VAD["durum"] != "yok": VAD["durum"] = None
    if p:
        try: p.stdin.close(); p.terminate()
        except Exception: pass
