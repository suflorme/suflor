# Suflor.me aktarıcı bölümü: Notlar defteri — toplantı yokken pano kutusu (v0.117.0, S136).
# Ayrı modül değildir — relay.py bunu kendi ad alanında çalıştırır (bolum("notlar")): BASE, write, aktif_dosya … relay.py'nin. import etme.
# Kullanıcı (22 Ekim): toplantı yokken kutuya yazılan not sahte bir "Toplantı" dökümü açıyor, pano 20 dk toplantı görünümüne geçiyordu
# (Başlat ve takvim gizli); soru izleyen olmadığı için cevapsız kalıyordu. Artık ne süren, ne de hazırlanan
# (son 30 dk'da Başlat/gündem, arka planda toplantı oturumu) toplantı varsa: soru toplantı dışı asistana yazılı gider (konus_yazili: cevap
# panoda, okunmaz), not canli/notlar.jsonl'e. Defter kişisel: panoya yalnız anahtarlı /status ile gider. Silme ayrı satırla ({"sil": id}).
NOTLAR_DOSYA, NOT_HAZIRLIK_SN, NOT_GOSTER_SA, NOT_GOSTER_EN_COK = "notlar.jsonl", 1800, 24, 20

def toplantisiz():  # kutu: süren, yeni biten ya da hazırlanan toplantı yok
    if aktif_dosya() or topo_canli(): return False  # Faz B: süren (algılandı/sürüyor/bitiyor) toplantı
    for y in ("takvim-secilen.json", "agenda.json"):  # Başlat ya da gündem: yeni toplantı hazırlanıyor, not ona (PRE) gider
        try:
            if time.time() - os.path.getmtime(os.path.join(BASE, y)) < NOT_HAZIRLIK_SN: return False
        except OSError: pass
    return True

def not_defter_yaz(metin, at=None):
    o = {"id": "n" + secrets.token_hex(4), "at": str(at or datetime.datetime.now().isoformat(timespec="seconds"))[:40], "metin": str(metin)[:4000]}
    write([(os.path.join(BASE, NOTLAR_DOSYA), json.dumps(o, ensure_ascii=False) + "\n")])
    print(f"NOT: toplantı yok — Notlar defterine ({len(o['metin'])} karakter)"); return {"ok": True, "id": o["id"]}

def _notlar_oku():
    ls, sil = [], set()
    try:
        with open(os.path.join(BASE, NOTLAR_DOSYA), encoding="utf-8") as f:
            for ln in f:
                try: o = json.loads(ln)
                except ValueError: continue
                if not isinstance(o, dict): continue
                if o.get("sil"): sil.add(str(o["sil"]))
                elif o.get("id") and o.get("metin"): ls.append(o)
    except OSError: pass
    return [o for o in ls if o["id"] not in sil]

def notlar_view():  # /status "notlar": son NOT_GOSTER_SA saatin notları, yeniden eskiye
    sinir = (datetime.datetime.now() - datetime.timedelta(hours=NOT_GOSTER_SA)).isoformat(timespec="seconds")
    return [{"id": o["id"], "at": o.get("at"), "metin": o["metin"]} for o in reversed(_notlar_oku()) if str(o.get("at") or "")[:19] >= sinir[:19]][:NOT_GOSTER_EN_COK]

def notlar_islem(p):  # POST /notlar {"sil": id} (pano, anahtarlı)
    i = str(p.get("sil") or "")
    if not i or not any(o["id"] == i for o in _notlar_oku()): return {"ok": False, "err": _t("not yok", "no such note")}
    write([(os.path.join(BASE, NOTLAR_DOSYA), json.dumps({"sil": i, "at": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")])
    return {"ok": True}
