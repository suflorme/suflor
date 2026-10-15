#!/usr/bin/env python3
# Doğal okuma düzeni (v0.41.0, aktarici/brifing-ses.py ses_duzen): Mac sesinde "Ee/eee/ıı/hmm" silinir ya da "Hm." + 0,3 sn sessizliğe döner, "Şey," ardına
# 0,25 sn, cümle başı ünlemde yalnız o sözcükte perde +6; Claude metnindeki [[…]] komutları silinir; Piper'da komut eklenmez. Ses çalınmaz; son
# bölümde say -o ile komutlu metnin sesli okunmadığı (süre makul, "pbas" sözcüğü yok) Whisper'sız kaba ölçülür.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/ses-duzen.py
import os, re, sys, subprocess, tempfile
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); hata = 0
src = open(os.path.join(K, "aktarici", "brifing-ses.py"), encoding="utf-8").read()
g = {"re": re}; exec(src[src.index("_SD_DOLGU = "):src.index("# Tepki sesleri (v0.43.0")], g); sd = g["ses_duzen"]
def bak(ad, v, b):
    global hata
    ok = v == b; hata += not ok; print(("✓ " if ok else "✗ ") + ad + ("" if ok else f": {v!r}, beklenen {b!r}"))
bak("Eee silinir, baş harf büyük kalır", sd("Eee, şöyle söyleyeyim: toplantı yarın."), "Şöyle söyleyeyim: toplantı yarın.")
bak("ortadaki ıı silinir", sd("Bütçe ıı yüzde on arttı."), "Bütçe yüzde on arttı.")
bak("Hmm → Hm. + sessizlik", sd("Hmm, bir bakayım."), "Hm. [[slnc 300]] bir bakayım.")
bak("Hımm → Hm. + sessizlik", sd("Hımm. Bakıyorum."), "Hm. [[slnc 300]] Bakıyorum.")
bak("Şey, + sessizlik", sd("Şey, nasıl desem, iki seçenek var."), "Şey, [[slnc 250]] nasıl desem, iki seçenek var.")
bak("cümle başı ünlemde perde", sd("Vay! Bunu hiç beklemiyordum."), "[[pbas +6]] Vay! [[pbas -6]] [[slnc 150]] Bunu hiç beklemiyordum.")
bak("Harika! perde", sd("Harika! Bu çok iyi bir haber."), "[[pbas +6]] Harika! [[pbas -6]] [[slnc 150]] Bu çok iyi bir haber.")
bak("ünlemsiz Harika dokunulmaz", sd("Harika bir sonuç çıktı."), "Harika bir sonuç çıktı.")
bak("Claude'un [[…]] komutu silinir", sd("Toplantı [[inpt PHON]] yarın [[rate 400]] saat onda."), "Toplantı yarın saat onda.")
bak("Piper: komut eklenmez", sd("Hmm, Vay! Şey, bakalım.", mac=False), "Hm, Vay! Şey, bakalım.")
bak("Türkçe sözcük bozulmaz (seyir, eee değil 'ee' içinde)", sd("Teşekkür ederim, seyir defteri hazır."), "Teşekkür ederim, seyir defteri hazır.")
bak("mi? dokunulmaz", sd("Gerçekten mi? Öyle mi?"), "Gerçekten mi? Öyle mi?")
# say gerçekten komutları uyguluyor mu (sesli okumuyor mu): komutlu metin, komutsuzdan perde komutu yüzünden uzun olmamalı (en çok +0,8 sn: 0,3+0,15 sessizlik)
with tempfile.TemporaryDirectory() as d:
    def sure(m):
        f = os.path.join(d, "x.aiff"); subprocess.run(["/usr/bin/say", "-o", f, m], check=True)
        return float(re.search(r"estimated duration: ([\d.]+)", subprocess.run(["afinfo", f], capture_output=True, text=True).stdout).group(1))
    a, b = sure("Vay! Bunu hiç beklemiyordum."), sure(sd("Vay! Bunu hiç beklemiyordum."))
    bak(f"say komutları okumadı ({a:.2f} → {b:.2f} sn)", 0 <= b - a <= 0.8, True)
print("ses düzeni: ✓ hepsi geçti" if not hata else f"ses düzeni: ✗ {hata} kaldı"); sys.exit(1 if hata else 0)
