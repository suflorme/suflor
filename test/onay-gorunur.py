#!/usr/bin/env python3
# Bekleyen cevap görünürlüğü (aktarici/otonom.py _ot_dikkat/_ot_onay_bekle/_ot_yeniden/otonom_view/otonom_karar; 5 Kasım gerçek toplantı: cevap hazırdı,
# söz fırsatı çıkmadı, "söylenmedi" sessizce düştü, kullanıcı 3 dk sonra yeniden sordu). Otonom bölümünün işlevleri sahte ad alanında (ses/ağ yok, ~3 sn)
# + pano/dil/ayar kaynak denetimi.   PYTHONDONTWRITEBYTECODE=1 python3 test/onay-gorunur.py
import ast, os, re, sys, threading, time
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
src = open(os.path.join(KOD, "aktarici", "otonom.py"), encoding="utf-8").read()
ADLAR = {"_ot_uyari", "_ot_dikkat", "_ot_onay_bekle", "_ot_yeniden", "otonom_view", "otonom_karar", "OT_SON", "ONAY_HATIRLAT_SN", "SIRA_UYARI_SN", "OTONOM_GORUNUR_SN", "OTONOM_ITIRAZ_SN", "OTONOM_BEKLE_SN"}
sec = [n for n in ast.parse(src).body if (isinstance(n, ast.FunctionDef) and n.name in ADLAR) or (isinstance(n, ast.Assign) and any(
    (getattr(x, "id", None) in ADLAR) or (isinstance(x, ast.Tuple) and any(getattr(e, "id", None) in ADLAR for e in x.elts)) for x in n.targets))]
CAGRI = []; AYAR = {}; DONGU = []
ns = {"time": time, "os": os, "threading": threading, "subprocess": None, "AYAR": AYAR, "OT": {"id": None}, "OT_K": threading.Lock(),
      "_t": lambda a, b=None: a, "print": lambda *a, **k: CAGRI.append(("log", " ".join(map(str, a)))), "kulaklik": lambda: True, "IZIN": {},
      "_ot_fisilti": lambda m: CAGRI.append(("fisilti", m)), "toplanti_var": lambda: True,
      "_ot_dongu": lambda *a, **k: DONGU.append(a), "izin_bekle": lambda iz, sn: (CAGRI.append(("izin_bekle", round(sn, 1))) or "zaman_asimi")}
exec(compile(ast.Module(sec, []), "otonom.py", "exec"), ns)
ns["_ot_uyari"] = lambda v=0.35, ses="Tink": CAGRI.append(("ses", ses))  # gerçek afplay çalmasın
def sifirla(): CAGRI.clear(); DONGU.clear(); AYAR.clear()

# 1) _ot_dikkat: ayar açıkken Ping + fısıltı (kulaklıkta, toplantı kanalına değil); kapalıyken hiçbir şey
sifirla(); r = ns["_ot_dikkat"]("deneme", fisilti="Onay bekliyor"); time.sleep(0.1)
ok("dikkat: Ping sesi + fısıltı", r and ("ses", "Ping") in CAGRI and ("fisilti", "Onay bekliyor") in CAGRI)
sifirla(); AYAR["onay_uyari"] = False; r = ns["_ot_dikkat"]("deneme", fisilti="Onay bekliyor"); time.sleep(0.1)
ok("onay_uyari: false → ses de fısıltı da yok", r is False and not [c for c in CAGRI if c[0] in ("ses", "fisilti")])

# 2) onay beklerken hatırlatma: karar gelmezse ONAY_HATIRLAT_SN'de bir kez; karar gelirse yok
ns["ONAY_HATIRLAT_SN"] = 0.4
sifirla(); olay = threading.Event(); ns["IZIN"]["x"] = {"olay": olay, "karar": None}
k = ns["_ot_onay_bekle"]("x", 10.0); time.sleep(0.1)
ok("onay bekleyen kart: 15 sn eşiğinde (burada 0,4) bir hatırlatma, kalan süre izin_bekle'ye", sum(1 for c in CAGRI if c == ("fisilti", "Still waiting for approval") or c == ("fisilti", "Hâlâ onay bekliyor")) == 1 and ("izin_bekle", 9.6) in CAGRI)
sifirla(); olay = threading.Event(); ns["IZIN"]["y"] = {"olay": olay, "karar": None}
threading.Timer(0.1, lambda: (ns["IZIN"]["y"].__setitem__("karar", "onaylandi"), olay.set())).start()
ns["_ot_onay_bekle"]("y", 10.0); time.sleep(0.1)
ok("erken onay: hatırlatma çalmaz", not [c for c in CAGRI if c[0] in ("ses", "fisilti")])
sifirla(); ns["IZIN"]["z"] = {"olay": threading.Event(), "karar": None}; ns["_ot_onay_bekle"]("z", 2.0)
ok("süre ≤ eşik + 3 sn: hatırlatma yok, doğrudan izin_bekle", ("izin_bekle", 2.0) in CAGRI and not [c for c in CAGRI if c[0] == "ses"])

# 3) görünüm: söz sırasında bekleme süresi; söylenmedi → yeniden (Şimdi oku)
OT, K = ns["OT"], ns["OT_K"]
with K: OT.clear(); OT.update(id="a1", metin="Cevap metni", durum="sira", t_durum=time.time() - 9, son=0)
v = ns["otonom_view"]()
ok("sira: bekliyor ≈ 9 sn, yeniden yok", v["bekliyor"] in (9, 10) and v["yeniden"] is False)
with K: OT.update(durum="soylenmedi", t_durum=time.time(), neden="20 sn içinde söz fırsatı çıkmadı")
v = ns["otonom_view"]()
ok("soylenmedi: yeniden True (Şimdi oku düğmesi)", v["yeniden"] is True and v["bekliyor"] is None)
with K: OT.update(durum="iptal")
ok("iptal: yeniden yok", ns["otonom_view"]()["yeniden"] is False)

# 4) Şimdi oku: söylenmeyen cevap söz sırası beklenmeden okunur (simdi=True, _ot_dongu yeniden)
sifirla()
with K: OT.clear(); OT.update(id="b2", metin="Cevap", durum="soylenmedi", t_durum=time.time(), neden="x", izin="iz1")
r = ns["otonom_karar"](None, "simdi"); time.sleep(0.2)
ok("otonom_karar(simdi) soylenmedi → okuma yeniden başladı", r == {"ok": True} and OT["durum"] == "itiraz" and OT.get("simdi") is True and "neden" not in OT and "izin" not in OT and len(DONGU) == 1 and DONGU[0][0] == "b2")
sifirla()
with K: OT.clear(); OT.update(id="c3", metin="Cevap", durum="soylenmedi", t_durum=time.time() - 200)
r = ns["otonom_karar"]("c3", "simdi")
ok("görünür süre (60 sn) geçtiyse okunmaz", r.get("ok") is False and not DONGU and OT["durum"] == "soylenmedi")
sifirla(); ns["toplanti_var"] = lambda: False
with K: OT.clear(); OT.update(id="d4", metin="Cevap", durum="soylenmedi", t_durum=time.time())
r = ns["otonom_karar"]("d4", "simdi"); ok("toplantı bittiyse okunmaz", r.get("ok") is False and not DONGU)
ns["toplanti_var"] = lambda: True

# 5) kaynak denetimi: bağlantılar yerinde
ok("otonom_sun: onay kartında dikkat + onay_uyari açıkken tek Tink yerine Ping", '_ot_dikkat("karşı tarafa cevap onay bekliyor"' in src and 'not (iz and AYAR.get("onay_uyari", True) is not False)' in src)
ok("_ot_dongu: onay beklemesi hatırlatmalı", "k = _ot_onay_bekle(iz," in src and "izin_bekle(iz, max(0.0" not in src)
ok("söz sırası: SIRA_UYARI_SN uyarısı ve fırsat çıkmayınca dikkat", "SIRA_UYARI_SN and not OT.get" in src and "söz fırsatı çıkmadı — panoda" in src)
ok("onay süresi dolunca da dikkat (Şimdi oku açık)", 'if k == "zaman_asimi": _ot_dikkat("onay süresi doldu' in src)
ok("fısıltı toplantı kanalına gitmez (toplantiya_soyle çağrılmaz)", "toplantiya_soyle" not in src[src.index("def _ot_fisilti"):src.index("def _ot_dikkat")])
pano = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read(); dil = open(os.path.join(KOD, "pano", "dil.js"), encoding="utf-8").read()
relay = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
ok("pano: soylenmedi'de Şimdi oku düğmesi (data-ot=simdi), mini pano CSS'i dahil", "data-ot=simdi" in pano and pano.count(".oto-soylenmedi[role=alert]") == 2)
ok("pano: karşı kartında sesle onay ipucu, söz sırası sayacı", "Sesle: «{ad}, oku»" in pano and "söz sırası bekleniyor ({n} sn)" in pano)
ok("ayar onay_uyari: AYAR_PANO + panodaki AYG", '"onay_uyari": ("bool", True, None)' in relay and "['onay_uyari','bool'" in pano)
for m in ("Şimdi oku", "Sesle: «{ad}, oku»", "{ad}: söz sırası bekleniyor ({n} sn)", "Bekleyen cevap uyarısı"):
    ok(f"dil.js: «{m[:40]}» İngilizcesi var", f'"{m}":' in dil)
print("\nHATA: %d" % len(HATA) if HATA else "\nHepsi geçti")
sys.exit(1 if HATA else 0)
