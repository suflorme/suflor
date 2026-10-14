#!/usr/bin/env python3
# Dışarı aktarmada e-posta hizmeti seçimi (relay.py eposta_tur, eposta_ben): ayar eposta önce; yoksa takvim adresinin alanı, sonra toplantı platformu.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/eposta.py
import collections, os, sys
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); src = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
kod = src[src.index("def eposta_ben():"):src.index("def son_view():")]; HATA = []
def ok(ad, k):
    print(("✓ " if k else "✗ ") + ad)
    if not k: HATA.append(ad)
A = lambda k, d: k + "@" + d  # örnek adresler çalışırken kurulur (açık depo taraması adres biçimini durdurur)
def dene(ayar, olaylar=()):
    g = {"AYAR": ayar, "TAKVIM_TAM": {str(i): {"platform": p} for i, p in enumerate(olaylar)}, "collections": collections}; exec(kod, g)
    return g["eposta_tur"](), g["eposta_ben"]()
ok("ayar önce gelir", dene({"eposta": "gmail", "takvim_adreslerim": [A("a", "sirket.com")]}, ["teams"])[0] == "gmail")
ok("Gmail adresi → gmail", dene({"takvim_adreslerim": [A("deniz", "gmail.com")]}, ["teams"])[0] == "gmail")
ok("outlook.com / onmicrosoft → outlook", dene({"takvim_adreslerim": [A("d", "outlook.com")]})[0] == "outlook" and dene({"takvim_adreslerim": [A("d", "x.onmicrosoft.com")]})[0] == "outlook")
ok("şirket alanı: toplantıların çoğu Teams → outlook, Meet → gmail", dene({"takvim_adreslerim": [A("d", "sirket.com")]}, ["teams", "teams", "meet"])[0] == "outlook"
   and dene({"takvim_adreslerim": [A("d", "sirket.com")]}, ["meet", None])[0] == "gmail")
ok("hiç ipucu yok → mailto; geçersiz ayar yok sayılır", dene({})[0] == "mailto" and dene({"eposta": "posta"})[0] == "mailto")
ok("kendime: eposta_adres önce, yoksa takvim adreslerinin ilki, yoksa yok", dene({"takvim_adreslerim": [A("a", "b.com"), A("c", "d.com")]})[1] == A("a", "b.com")
   and dene({"eposta_adres": A("e", "f.com")})[1] == A("e", "f.com") and dene({})[1] is None
   and dene({"eposta_adres": A("e", "gmail.com"), "takvim_adreslerim": [A("a", "b.com")]})[1] == A("e", "gmail.com"))
print("eposta:", "✓ hepsi geçti" if not HATA else f"✗ {len(HATA)} sorun"); sys.exit(1 if HATA else 0)
