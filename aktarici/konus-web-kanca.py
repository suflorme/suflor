# Konuş WebFetch/WebSearch kancası (13 Kasım 2026, güvenlik denetimi G3): araç öncesi (PreToolUse) kancası. Stdin'den araç girdisi (JSON) okur;
# şüpheli adres/arama metni (S257: yalnız konu; ad, alıntı, iç sayı yok — web-kapi.py web_metin_suphe) ya da gizli toplantı varsa "deny" kararı + kısa neden basar (model kullanıcıya söyler), yoksa hiçbir şey basmadan 0 ile çıkar (izin sürer).
# Kullanım: python3 -I -B konus-web-kanca.py [canli klasörü] (beyin.py konus_onek_ayar komutu kurar; brifing.swift konusKancaUygun komutu birebir denetler).
# Yalnız standart kütüphane; web-kapi.py'yi tek başına çalıştırır. Yüklenemezse ya da girdi okunamazsa reddeder (Konuş çökmez).
import sys, os, json

def reddet(tr, en):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                      "permissionDecisionReason": (en if os.environ.get("SUFLOR_DIL", "tr") == "en" else tr)}}, ensure_ascii=False))
    sys.exit(0)

def main():
    if len(sys.argv) < 2: reddet("bu adresi açmadım: kanca ayarı eksik.", "I didn't open it: the hook setting is incomplete.")  # canlı klasör brifing.swift'te sabit argüman
    canli = sys.argv[1]
    try: girdi = json.load(sys.stdin)
    except Exception: reddet("bu adresi açmadım: istek okunamadı.", "I didn't open it: the request could not be read.")
    ad = str(girdi.get("tool_name") or "") if isinstance(girdi, dict) else ""
    if ad not in ("WebFetch", "WebSearch"): return
    # 19 Kasım (dış çıkış kapısı, aktarici/cikis.py): gizli kip VARSAYILAN KAPALI okunur — canlı klasör yok/okunamıyor ya da gizli.json'un varlığı belirlenemiyorsa ret.
    if not os.path.isdir(canli): reddet("web'e çıkmadım: aktarıcı klasörü okunamadı.", "I didn't go online: the relay folder could not be read.")
    try: os.lstat(os.path.join(canli, "gizli.json")); gizli = True  # relay.py GIZLI_FP: gizli toplantı açıkken dosya var
    except FileNotFoundError: gizli = False
    except OSError: gizli = True
    if gizli: reddet("web'e çıkmadım: gizli toplantı açık.", "I didn't go online: a private meeting is on.")
    try:
        g = {"__name__": "web_kapi"}
        exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web-kapi.py"), encoding="utf-8").read(), "web-kapi.py", "exec"), g)
        suz, hata = g["web_suzgec_oku"](canli)  # aktarıcının yazdığı ad/döküm özeti (metin yok); dosya yoksa yalnız genel sınırlar
        if hata == "gizli": reddet("web'e çıkmadım: gizli toplantı açık.", "I didn't go online: a private meeting is on.")
        if hata: reddet("web'e çıkmadım: denetim süzgeci okunamadı.", "I didn't go online: the check filter could not be read.")
        gi = girdi.get("tool_input") or {}
        sonuc = g["web_metin_suphe"](gi.get("query"), suz) if ad == "WebSearch" else g["web_getir_suphe"](gi.get("url"), suz)
    except SystemExit: raise
    except Exception:
        reddet("web'e çıkmadım: denetim yüklenemedi.", "I didn't go online: the check could not be loaded.")
    if sonuc: reddet(("bunu aramadım: " if ad == "WebSearch" else "bu adresi açmadım: ") + sonuc[0], ("I didn't search for this: " if ad == "WebSearch" else "I didn't open this address: ") + sonuc[1])

main()
