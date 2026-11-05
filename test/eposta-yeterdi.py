#!/usr/bin/env python3
# "Bu toplantı e-postayla çözülebilir": yapi.eposta_isaret (öncesi) ve yapi.eposta_yeterdi (özet alanı), tc hazirlik/bitir çıktısı.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/eposta-yeterdi.py
import os, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, KOD); sys.dont_write_bytecode = True
import yapi as Y; HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
bilgi = ["Haftalık durum güncellemesi", "Q4 duyuru: yeni takvim", "Satış raporu bilgilendirme"]
ok("bilgi aktarımı gündemi, 8 kişi → güçlü", Y.eposta_isaret(bilgi, "Haftalık güncelleme", 8)["guclu"])
ok("kişi sayısı bilinmiyorsa da güçlü", Y.eposta_isaret(bilgi, "", None)["guclu"])
ok("kararlı gündem → zayıf", not Y.eposta_isaret(["Bütçe kararı", "Durum güncellemesi"], "", 6)["guclu"])
ok("tek karar kalıbı yetiyor: hepsi bilgi değilse zayıf", not Y.eposta_isaret(bilgi + ["Yeni ofis"], "", 6)["guclu"])
ok("iki kişilik toplantı → zayıf", not Y.eposta_isaret(bilgi, "", 2)["guclu"])
ok("başlıkta tartışma → zayıf", not Y.eposta_isaret(bilgi, "Strateji workshop", 6)["guclu"])
ok("gündem yok → zayıf", not Y.eposta_isaret([], "Haftalık güncelleme", 8)["guclu"])
def yapi(karar, ey):
    og = [{"tur": "karar", "metin": "X"}] if karar else [{"tur": "soru", "metin": "Y?"}]
    return {"maddeler": [{"baslik": "A", "durum": "konuşuldu", "ogeler": og}], "eposta_yeterdi": ey} if ey is not None else {"maddeler": [{"baslik": "A", "ogeler": og}]}
ok("karar yok + gerekçe → true", Y.eposta_yeterdi(yapi(False, {"deger": True, "gerekce": "42 dk'nın 38'i durum aktarımı"}))[:2] == (True, "42 dk'nın 38'i durum aktarımı"))
ok("karar çıkmışsa true düşer, uyarı verir", Y.eposta_yeterdi(yapi(True, {"deger": True, "gerekce": "x"}))[0] is False and "karar" in Y.eposta_yeterdi(yapi(True, {"deger": True, "gerekce": "x"}))[2])
ok("gerekçesiz true geçersiz", Y.eposta_yeterdi(yapi(False, {"deger": True, "gerekce": " "}))[0] is False)
ok("deger false → sessiz", Y.eposta_yeterdi(yapi(False, {"deger": False})) == (False, "", ""))
ok("alan yok → 'yok' uyarısı", Y.eposta_yeterdi(yapi(False, None))[2] == "yok")
src = open(os.path.join(KOD, "toplanti-claude.py"), encoding="utf-8").read()
ok("hazirlik ve bitir çıktısına bağlı", "E-posta yeterli mi?" in src and "EPOSTA:" in src and '"--kisi"' in src)
for f in ("TOPLANTI-MODU.md", "TOPLANTI-KURALLARI.md"):
    t = open(os.path.join(KOD, f), encoding="utf-8").read(); ok(f + ": §9 ve alan adı", "## 9." in t and "eposta_yeterdi" in t)
print("eposta-yeterdi:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
