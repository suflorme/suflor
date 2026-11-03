# S188 hafif profil — tek kaynak: kurulum.py (sihirbaz) ve relay.py (ayar okuma, ⚙ Ayarlar) burayı yükler. Düz sözlük/işlev; ad alanına bağımlı değil.
# S188 hafif profil: tek anahtar (ayar `profil: "hafif"`); aşağıdakiler ondan türetilir. Kullanıcının ayar.json'a elle yazdığı değer ezilmez
# (yalnız ayarda olmayan anahtar yazılır; yazılanlar `profil_turetilen`de tutulur, "tam"a dönünce yalnız onlar silinir). Kurulumda ayrıca:
# yerel ses (Pocket) kurulmaz, anlam modeli (~1,1 GB) inmez. Geliştiricinin (32 GB) kurulumu profil yazmaz.
PROFIL_HAFIF = {"anlam_arama": False, "ses_motoru": "mac", "konus_iki_surec": False, "konus_on_ac": False, "golge_tstt": False}
def profil_uygula(a, profil):  # a: ayar sözlüğü (yerinde değişir); profil "hafif" | "tam"
    onceki = [k for k in (a.get("profil_turetilen") or []) if k in PROFIL_HAFIF]
    if profil != "hafif":
        for k in onceki:
            if a.get(k) == PROFIL_HAFIF[k]: a.pop(k, None)  # kullanıcı sonradan değiştirdiyse dokunulmaz
        a.pop("profil", None); a.pop("profil_turetilen", None); return a
    yaz = []
    for k, v in PROFIL_HAFIF.items():
        if k not in a: a[k] = v; yaz.append(k)  # ayarda olmayanlar; var olan (elle verilmiş) değer profili ezer
    a["profil"] = "hafif"; a["profil_turetilen"] = sorted({k for k in onceki if k in a} | set(yaz)); return a
