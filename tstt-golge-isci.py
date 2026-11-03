#!/usr/bin/env python3
# Gölge kipte turkish-stt işçisi (ayar golge_tstt): aktarıcı canlı sesi stdin'e satır başına {"k","t","pcm"(base64 int16 16 kHz)} verir; her kanala ayrı akış
# tanıyıcı (mihu_stt, sherpa-onnx, işlemci). Ekrana bir şey gitmez; stdout'a satır başına JSON: hazir | soz | cpu. Ağ yok (model yerel, HF_HUB_OFFLINE=1).
# soz satırındaki "ara": ara metin her değiştiğinde [ses zamanı, duvar saati, metin] — ara metinden soru sonu/hitap ne zaman yakalanırdı, ölçümü için.
# Çalıştırma: HF_HUB_OFFLINE=1 <tstt-venv python> -I -B tstt-golge-isci.py <model klasörü>. SUFLOR_GOLGE_SAHTE=1: gerçek model yok, deneme için sahte tanıyıcı.
import base64, json, os, sys, time, resource
SR = 16000
def yaz(o): sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n"); sys.stdout.flush()
class Sahte:  # deneme: 0,3 sn sesten sonra "kelime", 1 sn dolunca söz biter (son_mu)
    def __init__(self): self.n = 0
    def accept_pcm16(self, pcm, sr):
        self.n += len(pcm) // 2
        if self.n >= SR: self.n = 0; return "sahte kelime", True
        return ("sahte" if self.n >= SR * 0.3 else ""), False
def yukle(model):
    if os.environ.get("SUFLOR_GOLGE_SAHTE") == "1": return lambda: Sahte()
    import mihu_stt
    return lambda: mihu_stt.StreamingSTT(model_dir=model, num_threads=1)
class Kanal:
    def __init__(self, ad, st): self.ad = ad; self.st = st; self.sifirla()
    def sifirla(self): self.t0 = self.ilk_ses = self.ilk_duvar = self.t1 = None; self.degisim = 0; self.son = ""; self.ara = []
    def besle(self, t, pcm):
        bit = t + len(pcm) / 2 / SR
        metin, son = self.st.accept_pcm16(pcm, SR); metin = (metin or "").strip()
        if metin:
            if self.t0 is None: self.t0 = t; self.ilk_ses = bit; self.ilk_duvar = round(time.time(), 3)
            if metin != self.son: self.degisim += 1; self.son = metin; self.ara.append([round(bit, 2), round(time.time(), 2), metin])
            self.t1 = bit
        if son:
            if metin: self.yaz_soz(metin, False)
            self.sifirla()
    def yaz_soz(self, metin, yarim):
        o = {"tur": "soz", "k": self.ad, "t0": round(self.t0, 3), "ilk_ses": round(self.ilk_ses, 3), "ilk_duvar": self.ilk_duvar, "t1": round(self.t1, 3),
             "son_duvar": round(time.time(), 3), "metin": metin, "degisim": self.degisim, "ara": self.ara}
        if yarim: o["yarim"] = True
        yaz(o)
    def kapat(self):
        if self.son and self.t0 is not None: self.yaz_soz(self.son, True)
def cpu():
    r = resource.getrusage(resource.RUSAGE_SELF); rss = r.ru_maxrss / 1048576 if sys.platform == "darwin" else r.ru_maxrss / 1024  # macOS bayt, Linux KB
    yaz({"tur": "cpu", "t": round(time.time(), 1), "cpu_sn": round(r.ru_utime + r.ru_stime, 2), "rss_mb": round(rss, 1)})
def main():
    model = sys.argv[1] if len(sys.argv) > 1 else ""
    t = time.time(); yap = yukle(model); kanallar = {}; hazir_st = [yap()]  # ilk tanıyıcı açılışta kurulur (yükleme süresi gerçek), ilk kanal onu alır
    yaz({"tur": "hazir", "yukleme_sn": round(time.time() - t, 2)}); son_cpu = time.time()
    for satir in sys.stdin.buffer:
        try:
            o = json.loads(satir); k = str(o["k"]); pcm = base64.b64decode(o["pcm"]); t0 = float(o["t"])
            if k not in kanallar: kanallar[k] = Kanal(k, hazir_st.pop() if hazir_st else yap())
            kanallar[k].besle(t0, pcm[:len(pcm) // 2 * 2])
        except Exception as e: yaz({"tur": "hata", "hata": e.__class__.__name__})
        if time.time() - son_cpu >= 60: son_cpu = time.time(); cpu()
    for k in kanallar.values(): k.kapat()
main()
