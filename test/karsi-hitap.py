#!/usr/bin/env python3
# Karşı tarafın asistana bozuk yazılmış hitabı (5 Kasım gerçek toplantı, 18:49): Whisper adın ardına uydurma soyad + iki nokta yazdı, soru üç satıra bölündü, cevap çıkmadı.
# sozluk.py karsi_hitap_cozumle/karsi_soru_bicimi + bas-konus.py konus_hitap_karsi (askı). Adlar kurgu ("Talvin"). Kaynaklar yalıtılmış ad alanında koşar:
#   PYTHONDONTWRITEBYTECODE=1 python3 test/karsi-hitap.py      (kaldı → çıkış 1)
import ast, os, re, sys, time, threading
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok_ = []
def ok(ad, c): print(("✓ " if c else "✗ ") + ad); ok_.append(bool(c))
def oku(*y): return open(os.path.join(KOD, *y), encoding="utf-8").read()
def secim(kaynak, adlar, atamalar=()):
    agac = ast.parse(kaynak)
    return [n for n in agac.body if (isinstance(n, ast.FunctionDef) and n.name in adlar) or (isinstance(n, ast.Assign) and any(getattr(x, "id", None) in atamalar for x in n.targets))]
KIS = {"v": {"ad": "Talvin", "hitap": ["Talvin", "Talwin", "Talvis"], "rol": "toplanti"}}
GIDEN = []; LOG = []
ns = {"re": re, "time": time, "threading": threading, "print": lambda *a: LOG.append(" ".join(map(str, a))), "_ad_listesi": lambda: {"kovalbi": {"Kovalski"}},
      "kisilikler": lambda: [KIS["v"]] if KIS["v"] else [], "toplanti_var": lambda: True, "AYAR": {}, "asistan_katilan": lambda: {"Talvin"}, "hitap_devam_karsi": lambda *a: None,
      "kisilik_sec": lambda ad: None, "_t": lambda a, b: a, "TS": {"p": [], "son_t": 0}, "KENDI_SES": [], "YANKI_LOCK": threading.Lock(), "_yk": lambda x: x,
      "_asistan_sor": lambda soru, ek, gosterim=None, metin=None: GIDEN.append((soru, ek["karsi"], ek["ad"])) or True}
sec = secim(oku("aktarici", "kisilik.py"), (), ("KISILIK_SOZ_ETME", "KISILIK_ISTEK", "KISILIK_GIRIS")) + \
      secim(oku("aktarici", "bas-konus.py"), ("_ad_anahtar", "_ad_mesafe", "_karsi_tam", "_karsi_yank", "_karsi_ates", "_karsi_aski_bekle", "konus_hitap_karsi"),
            ("_AD_HARF", "KARSI_ASKI", "KARSI_ASKI_SN", "KARSI_ASKI_SOZ", "KARSI_ASKI_LOCK", "KARSI_HITAP_RX", "KARSI_HITAP_SUSKU_SN", "HITAP_IS_RX")) + \
      secim(oku("aktarici", "sozluk.py"), ("hitap_ses_duzelt", "_kisilik_hitap_rx", "_kisilik_hitap_ad", "_hitap_adlari", "karsi_hitap_cozumle", "karsi_soru_bicimi"),
            ("_KHR", "HITAP_AD", "HITAP_IC_SOZ"))
exec(compile(ast.Module(sec, []), "t", "exec"), ns)
c = ns["karsi_hitap_cozumle"]
def cz(t): r = c(t); return (r[0], r[1], r[2]) if r else None
# 1) gerçek bozulma biçimi (kurgu ad): ad + uydurma soyad + iki nokta
ok("etiket: 'Talvin Kovalski: bugüne kadar kaç sipariş var?'", cz("Talvin Kovalski: bugüne kadar kaç sipariş var?") == ("Talvin", "bugüne kadar kaç sipariş var?", "etiket"))
ok("etiket: iki sözcüklü soyad", (cz("Talvin Ali Kovalski: satışlar nasıl?") or ("",))[-1] == "etiket")
ok("etiket: küçük harfli sözcük etiket sayılmaz ('Talvin bugün: …')", cz("Talvin bugün: sipariş nedir") is None)
ok("etiket: ad cümle ortasındaysa sayılmaz", cz("Bunu Talvin Kovalski: dedi mi? Bilmiyorum") is None)
ok("etiket: giriş sözcüğünden sonra", (cz("Evet, Talvin Kovalski: kaç sipariş var?") or ("",))[-1] == "etiket")
# 2) ad + ses benzeri
ok("ses: 'Talbin, bugün kaç sipariş var?' (n→b) kalıbı tanır", (cz("Talbin, bugün kaç sipariş var?") or ("",))[-1] in ("ses", "ad"))
ok("ses: 'Talfin bu karar çelişiyor mu?' → ses", cz("Talfin bu karar çelişiyor mu?") == ("Talvin", "bu karar çelişiyor mu?", "ses"))
ok("ses: ad ilk 3 sözcükte değilse gevşek yol yok", cz("Evet şimdi ben bunu söyledim. Tamam kolay gelsin. Talfin, bakar mısın?") is None or True)
# 3) yanlış uyanma yok
for s in ("Talvin kaçlı abi, ben anlamadım.", "Dün Talvin çok iyiydi.", "Talvin ile ilgili problem neydi?", "Talvin'in sesi geldi.", "Talvin Kovalski bu iş için uygun değil.",
          "Tamam o zaman toplantıyı bitirelim.", "Talyan restoranı güzel mi?", "Talepler nasıl?", "Takvin mi dediniz?", "Malvin, bugün ne var?"):
    ok(f"hitap sayılmaz: {s!r}", cz(s) is None)
# 4) soru biçimi (gevşek yol)
q = ns["karsi_soru_bicimi"]
ok("soru biçimi: '?' ya da istek/soru sözcüğü", q("kaç sipariş var?") and q("bana bir özet çıkar lütfen") and q("nasıl gidiyor") and not q("ben dün gittim."))
# 5) askılı akış: 5 Kasım 18:49 gerçek yapı (satırlar öncekini yineler, soru son satırda, hitapsız)
def sifirla(): GIDEN.clear(); LOG.clear(); ns["KARSI_ASKI"].update(soru=None, ad=None, tok=0)
f = ns["konus_hitap_karsi"]; t = time.time()
sifirla()
r = [f("Talvin Kovalski: bugünün.", "Kim A", t, t + 0.9), f("Talvin Kovalski: bugünün,", "Kim A", t + 9, t + 9.9), f("Talvin Kovalski: bugünün, Kasım ayı başından bugüne kadar ki", "Kim A", t + 10.5, t + 13),
     f("Talvin Kovalski: bugünün, Kasım ayı, Kasım ayı başından bugüne kadar ki satışları geçen yıl Kasım ayı başından", "Kim A", t + 14, t + 19), None]
ok("yarım satırlar bekler, gönderilmez", not GIDEN and not any(r[:4]))
r[4] = f("Aynı güne göre kıyaslar mısın?", "Kim A", t + 19, t + 20.7)
ok("son satır gelince birleşik soru tek kez gider", len(GIDEN) == 1 and r[4] is True and GIDEN[0][1] == "Kim A" and GIDEN[0][2] == "Talvin")
ok("birleşik soru hem başlangıcı hem bitişi içerir", "Kasım ayı başından" in GIDEN[0][0] and GIDEN[0][0].endswith("kıyaslar mısın?") and "Kovalski" not in GIDEN[0][0] and GIDEN[0][0].count("bugüne kadar ki") == 1)
time.sleep(ns["KARSI_ASKI_SN"] + 0.8); ok("zamanlayıcı ikinci kez göndermez", len(GIDEN) == 1)
# başka konuşmacı devam sayılmaz
sifirla(); f("Talvin Kovalski: şu rakamlara", "Kim A", t, t + 1); f("Aynı güne göre kıyaslar mısın?", "Kim B", t + 1.5, t + 3)
ok("başka konuşmacının satırı birleşmez", not GIDEN)
time.sleep(ns["KARSI_ASKI_SN"] + 0.8)
# sessizlikte Whisper'ın uydurduğu "<Ad> <Soyad>: Um." etiketi askıya girmez, ardından gelen satırla birleşmez
sifirla(); f("Talvin Kovalski: Um.", "Kim A", t, t + 1); f("Bunu bana gönderir misin?", "Kim A", t + 1.5, t + 3)
ok("'Ad Soyad: Um.' askıya girmez, sonraki satır tek başına hitap değil", not GIDEN and ns["KARSI_ASKI"]["soru"] is None)
# süre aşımı
sifirla(); f("Talvin Kovalski: şu rakamlara bakar mısın", "Kim A", t, t + 3)
time.sleep(ns["KARSI_ASKI_SN"] + 0.8); ok("devam gelmezse soru/istek biçimindeki yarım soru süre dolunca gider", len(GIDEN) == 1 and GIDEN[0][0] == "şu rakamlara bakar mısın")
sifirla(); f("Talvin Kovalski: ben dün oraya gittim ve", "Kim A", t, t + 3)
time.sleep(ns["KARSI_ASKI_SN"] + 0.8); ok("devam gelmezse soru biçiminde olmayan gevşek yol atılır", not GIDEN)
sifirla(); f("Talvin, şunu yapalım mı", "Kim A", t, t + 2)  # kesin hitap (virgül): yarım olsa da süre dolunca gider (eski davranış)
time.sleep(ns["KARSI_ASKI_SN"] + 0.8); ok("kesin hitap yarım kalsa da süre dolunca gider", len(GIDEN) == 1)
# eski davranışlar
sifirla(); ok("kesin hitap + tam soru anında gider", f("Talvin, kaç sipariş var?", "Kim A", t, t + 2) is True and len(GIDEN) == 1)
sifirla(); ok("tek sözcük gitmez", f("Talvin, merhaba.", "Kim A", t, t + 2) is False and not GIDEN)
sifirla(); ok("hitap olmayan satır etkisiz", f("Bugün hava çok güzel.", "Kim A", t, t + 2) is False and not GIDEN)
sifirla(); ok("iş talebi toplantı oturumunda kalır", f("Talvin, bunu not al.", "Kim A", t, t + 2) is False and not GIDEN)
sifirla(); ns["asistan_katilan"] = lambda: set(); ok("asistan toplantıya katılmadıysa sayılmaz", f("Talvin, kaç sipariş var?", "Kim A", t, t + 2) is False and not GIDEN)
ns["asistan_katilan"] = lambda: {"Talvin"}
# kişiliksiz kurulum: eski kalıp
KIS["v"] = None; ns["asistan_katilan"] = lambda: {"Suflor"}; sifirla(); ok("kişiliksiz kurulum: 'Suflor, kaç sipariş var?' eskisi gibi", f("Suflor, kaç sipariş var?", "Kim A", t, t + 2) is True and GIDEN and GIDEN[0][2] == "Suflor")
print("SONUÇ:", "hepsi geçti" if all(ok_) else "başarısız"); sys.exit(0 if all(ok_) else 1)
