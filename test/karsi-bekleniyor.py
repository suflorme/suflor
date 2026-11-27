#!/usr/bin/env python3
# beta #78: Whisper kuyruğunda ısınma öğesi ({"isinma": True, "kuyruga": ...}; relay.modelleri_isit) varken _karsi_bekleniyor KeyError verirdi.
# beta #74/#68: "WHISPER: istem sınırı" bilgi satırı sorun paketi sayılmaz. Kaynaklar yalıtılmış ad alanında koşar.
import os, queue, re, sys, time, threading
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(KOD, "aktarici", "whisper-hat.py"), encoding="utf-8").read()
src = s[s.index("def _karsi_bekleniyor("):s.index("def _yanki_say(")]
Q = queue.Queue()
ns = {"KANALLAR": {}, "WH_Q": Q}
exec(src, ns)
ok_ = []
def ok(ad, c): print(("✓ " if c else "✗ ") + ad); ok_.append(c)
now = time.time()
Q.put({"isinma": True, "kuyruga": now})
try: r = ns["_karsi_bekleniyor"](now - 2, now)
except Exception as e: r = repr(e)
ok("yalnız ısınma öğesi varken hata yok, False", r is False)
Q.put({"kanal": "ben", "t0": now - 2, "t1": now, "baslik": "x"})
ok("ben parçası karşı beklentisi sayılmaz", ns["_karsi_bekleniyor"](now - 2, now) is False)
Q.put({"kanal": "karsi", "t0": now - 2, "t1": now, "baslik": "x"})
ok("ısınma + çakışan karşı parçası: True", ns["_karsi_bekleniyor"](now - 2, now) is True)
ok("çakışmayan zamanda False", ns["_karsi_bekleniyor"](now + 10, now + 12) is False)
r_ = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
m = re.search(r'SORUN_RX = \[\("whisper", re\.compile\(r"([^"]+)"\)\)', r_)
rx = re.compile(m.group(1))
ok("istem sınırı satırı sorun değil", not rx.search("WHISPER: istem sınırı — 12 terim sığmadı (önem sırasında sondakiler)"))
ok("dil kilidi şüphesi satırı sorun değil", not rx.search("WHISPER: dil kilidi şüphesi (karsi kanalı, 'Evet.' lp -0.5 kp 0.2 süre 0.4 sn) — metin boş bırakıldı"))
ok("gerçek whisper hatası hâlâ sorun", bool(rx.search("WHISPER: parça 30 sn'de çevrilemedi (karsi)")))
print("SONUÇ:", "hepsi geçti" if all(ok_) else "başarısız"); sys.exit(0 if all(ok_) else 1)
