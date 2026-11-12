#!/usr/bin/env python3
# Konuş yerel ses istemcisi (aktarici/yerel-konus.py, Aşama 2 Adım 2): sahte Unix soket sunucusuyla protokol uyumu — anahtar, olay sırası (cal_ac/ses/cal_bitir,
# cal_basladi → ses_basladi), mikrofon öbeklerinin sohbet gövdesine gitmesi, 2 sn cevap yoksa düşme (yerel_dusme), gizli kipte ve toplantıda mik_kapat,
# D yolunda sessiz_dugum, M yolunda say → PCM → yardımcı ve düşünce bugünkü say, yerel_konus false iken bağlanmama. Gerçek ses çalmaz (say -o dosyaya yazar).
#   PYTHONDONTWRITEBYTECODE=1 python3 test/yerel-konus.py
import base64, datetime, json, os, queue, shutil, socket, struct, subprocess, sys, tempfile, threading, time, wave
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
KLS = tempfile.mkdtemp(prefix="ky", dir="/tmp"); YOL = os.path.join(KLS, "konus-ses.sock"); ANAHTAR = "a" * 48
open(os.path.join(KLS, "ses-anahtari.txt"), "w").write(ANAHTAR + "\n")
class Sunucu:  # Swift yardımcısının yerine: tek bağlantı, ilk satır anahtar, satırları kaydeder
    def __init__(self):
        self.msj = []; self.baglanti = 0; self.c = None; self.kapali = False; self.kilit = threading.Lock()
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(YOL): os.remove(YOL)
        self.s.bind(YOL); os.chmod(YOL, 0o600); self.s.listen(2); threading.Thread(target=self.kabul, daemon=True).start()
    def kabul(self):
        while True:
            try: c, _ = self.s.accept()
            except OSError: return
            if self.c:
                try: self.c.close()
                except OSError: pass
            self.c = c; self.baglanti += 1; threading.Thread(target=self.oku, args=(c,), daemon=True).start()
    def oku(self, c):
        tamp = b""; ilk = True
        while True:
            try: b = c.recv(65536)
            except OSError: return
            if not b: return
            tamp += b
            while b"\n" in tamp:
                sat, tamp = tamp.split(b"\n", 1); o = json.loads(sat)
                if ilk:
                    ilk = False
                    if o.get("t") != "anahtar" or o.get("k") != ANAHTAR:
                        c.sendall(b'{"t":"hata","neden":"anahtar"}\n'); c.close(); self.msj.append(("YANLIS", o)); return
                    self.msj.append(("ANAHTAR", o)); c.sendall(b'{"t":"nabiz","vpio":false,"mik":false,"cal":false,"surum":"t0"}\n'); continue
                self.msj.append(("m", o))
    def gonder(self, o): self.c.sendall((json.dumps(o) + "\n").encode())
    def tipler(self, t): return [o for k, o in self.msj if k == "m" and o.get("t") == t]
    def kapat(self):
        try: self.s.close()
        except OSError: pass
        if self.c:
            try: self.c.close()
            except OSError: pass
def bekle(kosul, sn=4.0):
    t = time.time()
    while time.time() - t < sn:
        if kosul(): return True
        time.sleep(0.02)
    return bool(kosul())
GUN = []; ZAMAN = []; SOH = {"acik": True}; GOVDE = []; DURUM = {"toplanti": False, "gizli": False, "etkin": True}
SES = {"p": None, "q": []}
def ns_kur():
    n = {"os": os, "json": json, "time": time, "threading": threading, "queue": queue, "datetime": datetime, "base64": base64, "subprocess": subprocess,
         "AYAR": {"uygulama": KLS, "yerel_konus": True}, "gelistirici_mi": lambda: DURUM["etkin"], "LOCK": threading.Lock(), "BASE": KLS,
         "write": lambda satirlar: GUN.extend(s[1] for s in satirlar), "SES": SES, "ses_basladi": lambda kayit=None, t=None: ZAMAN.append((kayit is SES, t)),
         "toplanti_var": lambda: DURUM["toplanti"], "gizli_acik": lambda: DURUM["gizli"], "deneme_aktarici": lambda: True, "SOHBET": SOH,
         "_sohbet_parca_govde": lambda pcm, p: GOVDE.append((len(pcm), p)), "print": lambda *a, **k: None}
    exec(compile(open(os.path.join(KOD, "aktarici", "yerel-konus.py"), encoding="utf-8").read(), "yerel-konus.py", "exec"), n)
    n["KY_BAGLAN_ARA_SN"] = 0.2; n["KY_BAGLAN_AZAMI_SN"] = 0.5; n["KY_CAL_BASLA_SN"] = 0.4; n["KY_DUSME_BEKLE_SN"] = 1.5
    return n
# 1. yerel_konus false: hiç bağlanmaz, ky_baslat başlatmaz
sun = Sunucu(); n = ns_kur(); n["AYAR"]["yerel_konus"] = False
ok("yerel_konus false: ky_baslat False ve dongü yok", n["ky_baslat"]() is False and n["KY"]["dongu"] is None)
time.sleep(1.0); ok("yerel_konus false: sunucuya bağlantı gelmedi", sun.baglanti == 0)
ok("yerel_konus false: ky_hazir False, ky_cal_ac None, ky_say_popen None", not n["ky_hazir"]() and n["ky_cal_ac"](24000) is None and n["ky_say_popen"]() is None)
DURUM["etkin"] = False; n["AYAR"]["yerel_konus"] = True
ok("geliştirici değilken ayar true olsa da etkin değil", n["ky_etkin"]() is False and n["ky_baslat"]() is False); DURUM["etkin"] = True
# 2. etkin: anahtar ilk satır
ok("etkin: ky_baslat başladı", n["ky_baslat"]())
ok("bağlandı, ilk mesaj doğru anahtar", bekle(lambda: sun.msj and sun.msj[0][0] == "ANAHTAR") and n["KY"]["bagli"])
ok("bağlanınca durum istendi", bekle(lambda: sun.tipler("durum")))
sun.gonder({"t": "nabiz", "vpio": False, "mik": False, "cal": False, "surum": "t"}); ok("nabız durumu işlendi", bekle(lambda: n["KY"]["durum"].get("surum") == "t"))
# 3. mikrofon: mik_ac, öbekler birleşip gövdeye, kapat sonrası atılır
ok("ky_mik_ac(True) mik_ac{vpio:true} yollar", n["ky_mik_ac"](True) and bekle(lambda: sun.tipler("mik_ac") and sun.tipler("mik_ac")[-1]["vpio"] is True))
sil = base64.b64encode(b"\x00\x01" * 1600).decode()  # 100 ms @ 16 kHz Int16
for i in range(8): sun.gonder({"t": "mik", "b64": sil, "duzey": -50.0, "vpio": True, "ts": 1.0 + i / 10})
ok(f"8 öbek (0,8 sn) birleşip sohbet gövdesine gitti", bekle(lambda: len(GOVDE) == 2) and all(g[0] == 12800 and "pcm" in g[1] for g in GOVDE))
n["ky_mik_kapat"](); del GOVDE[:]; sun.gonder({"t": "mik", "b64": sil}); time.sleep(0.5); ok("mik_kapat sonrası gelen öbek atılır, mik_kapat yollandı", not GOVDE and sun.tipler("mik_kapat"))
# 3b. (12 Kasım denetimi) kuşak: kapanıştan önce kuyruğa/tampona girmiş öbek kapanıştan sonra gövdeye gitmez
n["ky_mik_ac"](True); del GOVDE[:]; k0 = n["KY"]["mik_kusak"]
for i in range(3): sun.gonder({"t": "mik", "b64": sil})
time.sleep(0.3); n["ky_mik_kapat"](); n["ky_mik_ac"](True)
for i in range(2): sun.gonder({"t": "mik", "b64": sil})
time.sleep(0.4); ok("kapanıştan önceki yarım tampon (3 öbek) yeni açılışın 2 öbeğiyle birleşip gövdeye gitmez", not GOVDE)
for i in range(6): n["KY"]["mik_q"].put((k0, {"t": "mik", "b64": sil}))
time.sleep(0.4); ok("eski kuşakla kuyrukta kalan öbekler atılır", not GOVDE)
n["ky_mik_kapat"]()
# 4. çalıcı: olay sırası + ses saati
del ZAMAN[:]; c = n["ky_cal_ac"](24000, kayit=SES)
ok("cal_ac{id,sr} gitti", c is not None and bekle(lambda: sun.tipler("cal_ac")) and sun.tipler("cal_ac")[-1]["sr"] == 24000 and sun.tipler("cal_ac")[-1]["id"] == c.id)
c.stdin.write(b"\x01\x00" * 4800); c.stdin.flush(); c.stdin.write(b"\x02\x00" * 100); c.stdin.close()
ok("ses, ses, cal_bitir sırayla", bekle(lambda: sun.tipler("cal_bitir")) and [o["t"] for k, o in sun.msj if k == "m" and o["t"] in ("cal_ac", "ses", "cal_bitir")][-4:] == ["cal_ac", "ses", "ses", "cal_bitir"])
ok("poll() None (çalıyor)", c.poll() is None)
# protokol (Adım 1 eki): cal_basladi{id,ts,duvar}; ses saati = duvar (ts süreçler arası karşılaştırılamaz)
sun.gonder({"t": "cal_basladi", "id": c.id, "ts": 123.0, "duvar": time.time() - 0.2})
ok(f"cal_basladi → ses_basladi(SES, t) çağrıldı, t duvar saati ≈ şimdi−0,2", bekle(lambda: any(z[0] for z in ZAMAN)) and c.basladi and abs(time.time() - 0.2 - ZAMAN[-1][1]) < 0.3)
sun.gonder({"t": "cal_bitti", "id": c.id}); ok("cal_bitti: wait() döner, returncode 0", c.wait(2) == 0 and c.poll() == 0)
# 6. kes ve yeni cal_ac
c1 = n["ky_cal_ac"](24000, kayit=SES); c2 = n["ky_cal_ac"](24000, kayit=SES)
ok("yeni cal_ac öncekini keser (returncode -15)", c1.poll() == -15 and c2.poll() is None)
c2.terminate(); ok("terminate: kes komutu gitti, poll -15", bekle(lambda: sun.tipler("kes")) and c2.poll() == -15)
try: c2.stdin.write(b"xx"); yaz = False
except OSError: yaz = True
ok("kesik akışa yazmak OSError (Pocket/Gemini çalıcı koduyla aynı sözleşme)", yaz)
# 7. 2 sn düşme (testte 0,4 sn)
del GUN[:]; c = n["ky_cal_ac"](24000, kayit=SES); c.stdin.write(b"\x01\x00" * 480)
ok("cal_basladi gelmezse düşme: dustu, returncode -1", bekle(lambda: c.dustu, 2) and c.poll() == -1)
ok("yerel_dusme günlüğe yazıldı (neden cal_basladi_yok)", any('"yerel_dusme"' in g and "cal_basladi_yok" in g for g in GUN))
ok("düştükten sonra yerel yol kapalı: ky_hazir False, ky_cal_ac None, ky_say_popen None", not n["ky_hazir"]() and n["ky_cal_ac"](24000) is None and n["ky_say_popen"]() is None)
time.sleep(1.6); ok("bekleme bitince yerel yol geri gelir", n["ky_hazir"]())
# 8. aygıtlı yol hiç yerel olmaz
ok("aygıt verilince ky_cal_ac None (toplantıya ses yolu değişmez)", n["ky_cal_ac"](24000, aygit="BlackHole") is None)
# 9. gizli kip / toplantı: bekçi mik_kapat der, mik_ac reddedilir
n["ky_mik_ac"](True); n_once = len(sun.tipler("mik_kapat")); DURUM["gizli"] = True
ok("gizli kip: ≤ 1 sn içinde mik_kapat", bekle(lambda: len(sun.tipler("mik_kapat")) > n_once, 1.5) and not n["KY"]["mik"])
ok("gizli kipte mik_ac reddedilir", n["ky_mik_ac"](True) is False); DURUM["gizli"] = False
ok("gizli kapanınca mik_ac açılır", n["ky_mik_ac"](False)); n_once = len(sun.tipler("mik_kapat")); DURUM["toplanti"] = True
ok("toplantı: ≤ 1 sn içinde mik_kapat", bekle(lambda: len(sun.tipler("mik_kapat")) > n_once, 1.5) and not n["KY"]["mik"])
ok("toplantıda mik_ac reddedilir", n["ky_mik_ac"](False) is False)
del GOVDE[:]; sun.gonder({"t": "mik", "b64": sil}); time.sleep(0.4); ok("toplantıda yoldaki mik öbeği gövdeye gitmez", not GOVDE); DURUM["toplanti"] = False
# 9b. toplantı bitince sohbet açıksa mik_ac yeniden; toplantı_mik sonrası vpio:true yeniden
n["ky_mik_ac"](True); DURUM["toplanti"] = True; bekle(lambda: not n["KY"]["mik"], 1.5); ma = len(sun.tipler("mik_ac")); DURUM["toplanti"] = False
ok("toplantı bitti + sohbet açık: mik_ac{vpio:true} yeniden gönderilir", bekle(lambda: len(sun.tipler("mik_ac")) > ma and sun.tipler("mik_ac")[-1]["vpio"] is True, 2) and n["KY"]["mik"])
sun.gonder({"t": "toplanti_mik", "uygulama": "x", "vpio_kapatildi": True}); bekle(lambda: n["KY"]["vpio_bekle"] > 0, 1); n["KY"]["vpio_bekle"] -= 4; ma = len(sun.tipler("mik_ac"))
ok("toplanti_mik sonrası (toplantı yok, sohbet açık) mik_ac{vpio:true} yeniden", bekle(lambda: len(sun.tipler("mik_ac")) > ma, 2))
SOH["acik"] = False; n["ky_mik_ac"](True); DURUM["toplanti"] = True; bekle(lambda: not n["KY"]["mik"], 1.5); ma = len(sun.tipler("mik_ac")); DURUM["toplanti"] = False; time.sleep(1.0)
ok("sohbet kapalıysa toplantı bitince mikrofon açılmaz", len(sun.tipler("mik_ac")) == ma); SOH["acik"] = True
# kesildi (motor yeniden kuruldu): çalıcı kesildi
c = n["ky_cal_ac"](24000, kayit=SES); sun.gonder({"t": "kesildi", "id": c.id})
ok("kesildi olayı çalıcıyı bitirir (returncode -15, kesildi)", bekle(lambda: c.poll() == -15) and c.kesildi)
# 10. D yolu: sessiz_dugum yalnız vpio açıkken, çalıcı bitince ~1 sn sonra kapanır
class Oyn:
    def __init__(self): self.bit = False
    def poll(self): return 0 if self.bit else None
n["ky_mik_ac"](True); sd0 = len(sun.tipler("sessiz_dugum")); o1 = Oyn(); n["ky_sessiz_sar"](o1)
ok("dış çalıcı çalarken sessiz_dugum ac:true", bekle(lambda: len(sun.tipler("sessiz_dugum")) > sd0 and sun.tipler("sessiz_dugum")[-1]["ac"] is True))
o2 = Oyn(); n["ky_sessiz_sar"](o2); o1.bit = True; time.sleep(1.6); ok("hâlâ bir çalıcı varken kapanmaz", sun.tipler("sessiz_dugum")[-1]["ac"] is True)
o2.bit = True; ok("tüm çalıcılar bitince ac:false", bekle(lambda: sun.tipler("sessiz_dugum")[-1]["ac"] is False, 3))
n["ky_mik_kapat"](); sd0 = len(sun.tipler("sessiz_dugum")); o3 = Oyn(); n["ky_sessiz_sar"](o3); time.sleep(0.4); o3.bit = True
ok("mikrofon/VPIO kapalıyken sessiz_dugum gönderilmez", len(sun.tipler("sessiz_dugum")) == sd0)
# 11. M yolu: say → PCM → yardımcı (gerçek say -o, ses çalınmaz)
if os.path.exists("/usr/bin/say"):
    ok("ky_say_popen yerel hazırken KySay", n["ky_say_popen"]() is n["KySay"])
    del ZAMAN[:]; ca0 = len(sun.tipler("cal_ac")); p = n["KySay"](["/usr/bin/say", "-f", "-"], stdin=None); p.stdin.write("Merhaba dünya.".encode()); p.stdin.close()
    ok("say metni PCM olarak cal_ac+ses+cal_bitir ile yardımcıya gitti", bekle(lambda: len(sun.tipler("cal_bitir")) > 0 and len(sun.tipler("cal_ac")) > ca0, 8) and sun.tipler("cal_ac")[-1]["sr"] == n["KY_SAY_SR"])
    cid = sun.tipler("cal_ac")[-1]["id"]; ok("say çalarken poll() None ve .yerel", p.poll() is None and p.yerel is True)
    sun.gonder({"t": "cal_basladi", "id": cid, "ts": 5.0, "duvar": time.time()}); ok("say yolunda ses_basladi cal_basladi'dan", bekle(lambda: any(z[0] for z in ZAMAN)))
    sun.gonder({"t": "cal_bitti", "id": cid}); ok("cal_bitti: say.wait() 0", p.wait(3) == 0)
    # kes: terminate
    p = n["KySay"](["/usr/bin/say", "-f", "-"]); p.stdin.write(b"Bir iki uc dort bes."); p.stdin.close(); bekle(lambda: sun.tipler("cal_bitir") and p.cal, 8)
    p.terminate(); ok("say terminate: poll -15 ve kes gitti", p.poll() == -15 and sun.tipler("kes"))
    # çalıcı yanıt vermezse bugünkü say'e düşer (sahte say: true)
    GUN.clear(); p = n["KySay"](["/usr/bin/true", "-f", "-"]); p.stdin.write(b"x"); p.stdin.close()
    ok("say -o başarısızsa bugünkü yola (doğrudan say) düşer, kayıp yok", p.wait(8) == 0 and p.yedek is not None)
else: print("- say yok, M yolu testi atlandı")
# 12. anahtar yanlış: sunucu hata+kapat → istemci vurmaz (geri çekilme)
n["ky_durdur"](); time.sleep(0.4); ANAHTAR_ESKI = ANAHTAR; open(os.path.join(KLS, "ses-anahtari.txt"), "w").write("b" * 48 + "\n")
sun.baglanti = 0; n2 = ns_kur(); n2["KY_BAGLAN_ARA_SN"] = 0.3; n2["KY_BAGLAN_AZAMI_SN"] = 0.6; n2["ky_baslat"]()
ok("yanlış anahtar: sunucu reddetti, istemci bağlı sayılmaz", bekle(lambda: any(k == "YANLIS" for k, _ in sun.msj)) and bekle(lambda: not n2["KY"]["bagli"]))
time.sleep(1.5); ok(f"yanlış anahtarda yeniden bağlanma geri çekilir (1,5 sn'de {sun.baglanti} deneme)", sun.baglanti <= 6)
open(os.path.join(KLS, "ses-anahtari.txt"), "w").write(ANAHTAR + "\n"); ok("anahtar düzelince bağlanır (her denemede dosya yeniden okunur)", bekle(lambda: n2["KY"]["bagli"], 3))
# 13. yardımcı kapanır: yeniden bağlanma
sun.c.close(); ok("bağlantı koptu → bagli False", bekle(lambda: not n2["KY"]["bagli"], 2)); ok("kendiliğinden yeniden bağlandı", bekle(lambda: n2["KY"]["bagli"], 3))
n2["ky_durdur"](); sun.kapat(); shutil.rmtree(KLS, ignore_errors=True)
print(f"\n{'TAMAM' if not HATA else 'HATA: ' + str(len(HATA))}"); sys.exit(1 if HATA else 0)
