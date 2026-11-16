#!/usr/bin/env python3
"""Ortak ad alanı çakışma denetimi (16 Kasım 2026).

relay.py `aktarici/*.py` bölümlerini bolum() ile TEK ad alanına yükler: iki dosyada aynı üst düzey ad (işlev, sözlük,
sabit) tanımlanırsa sonra yüklenen öncekini sessizce ezer. Örnek: kapi.py KAPI sözlüğü whisper-hat.py ses kapısının
KAPI'sini ezdi (KeyError 'mik', beta #53); is-kopya.py _ik_kisa(x, n) notlar.py _ik_kisa(s, n=90)'ı ezdi (tek
argümanlı çağrı TypeError).

İzinli: tanımların kaynak metni birebir aynıysa, ya da sonraki tanım `globals().get("AD")` ile öncekini koruyorsa.
Çalıştır: PYTHONDONTWRITEBYTECODE=1 python3 test/ad-cakisma.py
"""
import ast, os, re, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bolumler():
    s = open(os.path.join(KOK, "relay.py"), encoding="utf-8").read()
    return ["relay.py"] + [f"aktarici/{a}.py" for a in re.findall(r'^bolum\("([a-z0-9-]+)"\)', s, re.M)]


def tanimlar(yol):
    kaynak = open(os.path.join(KOK, yol), encoding="utf-8").read()
    for n in ast.parse(kaynak).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield n.name, ast.get_source_segment(kaynak, n)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            hedefler = n.targets if isinstance(n, ast.Assign) else [n.target]
            metin = ast.get_source_segment(kaynak, n)
            for h in hedefler:
                for x in ast.walk(h):
                    if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
                        yield x.id, metin


def main():
    gor = {}
    hata = []
    for yol in bolumler():
        if not os.path.exists(os.path.join(KOK, yol)):
            hata.append(f"bölüm dosyası yok: {yol}"); continue
        yerel = set()
        for ad, metin in tanimlar(yol):
            if ad in yerel: continue  # aynı dosyada yeniden atama: dosyanın kendi işi
            yerel.add(ad)
            if ad in gor:
                onceki_yol, onceki_metin = gor[ad]
                if metin == onceki_metin or f'globals().get("{ad}")' in metin or f"globals().get('{ad}')" in metin:
                    continue
                hata.append(f"{ad}: {onceki_yol} tanımını {yol} eziyor")
            else:
                gor[ad] = (yol, metin)
    n = len(gor)
    if hata:
        print("BAŞARISIZ — ortak ad alanında çakışan adlar:")
        for h in hata: print("  ✗", h)
        sys.exit(1)
    print(f"GEÇTİ — {len(bolumler())} dosya, {n} üst düzey ad, çakışma yok")


if __name__ == "__main__":
    main()
