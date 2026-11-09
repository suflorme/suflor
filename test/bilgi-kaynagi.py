#!/usr/bin/env python3
# Konuş'ta dış bilgi kaynağı (1 Kasım; aktarici/beyin.py konus_bilgi/konus_args, bas-konus.py konus_bilgi_kaynaklari/bilgi_istem/bilgi_saglama,
# toplanti-oturum.py bilgi_kaynaklari url alanı, brifing.swift kümesi): kaynaksız argümanlar HEAD'deki beyin.py ile birebir aynı, kaynaklı düzen, beyin Claude
# değilken/gizli kipte/url'siz/ayar kapalıyken kaynaksız, istem eki, sağlama yedeği (30 dk), yazma sözcüğü kümesi Python ve Swift'te aynı. Yapay adlar; ağ yok.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/bilgi-kaynagi.py
import importlib.util, json, os, re, subprocess, sys, time, types
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.dont_write_bytecode = True
def yukle(ad, kaynak):
    m = types.ModuleType(ad); m.__file__ = os.path.join(KOD, "aktarici", "beyin.py"); exec(compile(kaynak, m.__file__, "exec"), m.__dict__); return m
BY = yukle("beyin_yeni", open(os.path.join(KOD, "aktarici", "beyin.py"), encoding="utf-8").read())
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)

K = {"ad": "Örnek Kaynak", "sunucu": "claude_ai_Ornek_Kaynak", "url": "https://ornek.test/mcp", "araclar": ["get_*", "list_*", "query_metrics", "compare_*"], "konu": "yapay satış verisi"}
A = {}; B = "/tmp/uyg"; VT = os.path.join(B, "konus-mcp.json")
def arg(a, k): return a[a.index(k) + 1]

# 1. kaynaksız: HEAD'deki (değişmemiş) beyin.py ile birebir aynı
try:
    eski = subprocess.run(["git", "show", "HEAD:aktarici/beyin.py"], cwd=KOD, capture_output=True, text=True, check=True).stdout
    EB = yukle("beyin_eski", eski) if "BILGI_YAZMA" not in eski else None
except Exception: EB = None
if EB is None: print("(HEAD'deki beyin.py zaten bilgi kaynaklı — birebir karşılaştırma atlandı)")
else:
    for ad, ayar, mcp, ek in [("ayarsız", {}, None, ""), ("veritabanıyla", {}, VT, "mcp__suflorvt__vt_sema,mcp__suflorvt__vt_sor"), ("önek kapalı", {"konus_onek_sabit": False}, None, ""),
                              ("yalın kapalı", {"claude_yalin": False}, VT, "mcp__suflorvt__vt_sema"), ("effort", {"konus_effort": "low"}, None, "")]:
        kontrol(f"kaynaksız argümanlar HEAD ile birebir: {ad}", BY.konus_args(ayar, "istem", ek, mcp, B, "sonnet") == EB.konus_args(ayar, "istem", ek, mcp, B, "sonnet")
                and BY.konus_args(ayar, "istem", ek, mcp, B, "sonnet", []) == EB.konus_args(ayar, "istem", ek, mcp, B, "sonnet"))
    kontrol("çeviri/telaffuz/brifing/kart argümanları değişmedi", BY.ceviri_args(A, "s") == EB.ceviri_args(A, "s") and BY.telaffuz_args(A, "i") == EB.telaffuz_args(A, "i")
            and BY.brifing_args(A, "i", B) == EB.brifing_args(A, "i", B) and BY.kart_args("m") == EB.kart_args("m") and BY.yalin(A) == EB.yalin(A))

# 2. kaynaklı düzen
a = BY.konus_args(A, "istem", "", None, B, "sonnet", [K])
kontrol("strict yok", "--strict-mcp-config" not in a)
kontrol("--setting-sources yalnız project (local yok)", arg(a, "--setting-sources") == "project" and "local" not in " ".join(a[:a.index("--append-system-prompt")] + a[a.index("--append-system-prompt") + 2:])[0:0] + arg(a, "--setting-sources"))
ar = arg(a, "--allowedTools").split(",")
kontrol("allowedTools: Read,Grep,Glob + kaynağın okuma desenleri", ar[:3] == ["Read", "Grep", "Glob"] and "mcp__claude_ai_Ornek_Kaynak__get_*" in ar and "mcp__claude_ai_Ornek_Kaynak__query_metrics" in ar and len(ar) == 7, ar)
st = json.loads(arg(a, "--settings"))
kontrol("settings: allowedMcpServers yalnız kaynağın url'si (suflorvt yok: mcp yok)", st["allowedMcpServers"] == [{"serverUrl": "https://ornek.test/mcp"}], st)
kontrol("settings env: yalnız önek sabit anahtarları (PREWAIT yok); tek --settings", set(st["env"]) == {"CLAUDE_CODE_DISABLE_CLAUDE_MDS", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"}
        and a.count("--settings") == 1 and "PREWAIT" not in " ".join(a) and "PREWAIT" not in open(os.path.join(KOD, "aktarici", "beyin.py"), encoding="utf-8").read().split("BILGI_OKUMA_ON =")[0].split("def konus_onek_ayar")[1].split("# Dış bilgi")[0])
kontrol("yalın bayrak dizisi bugünküyle aynı, yalnız --strict-mcp-config çıkmış", (lambda k, b: k[k.index("--setting-sources"):k.index("--tools")] == [x for x in b[b.index("--strict-mcp-config"):b.index("--tools")] if x != "--strict-mcp-config"])(a, BY.konus_args(A, "i", "", None, B, "s")))
kontrol("--tools Read,Grep,Glob ve --disable-slash-commands korunur", arg(a, "--tools") == "Read,Grep,Glob" and "--disable-slash-commands" in a and "--no-session-persistence" in a)
a2 = BY.konus_args(A, "istem", "mcp__suflorvt__vt_sema,mcp__suflorvt__vt_sor", VT, B, "sonnet", [K])
kontrol("veritabanıyla birlikte: allowlist url + serverName suflorvt, mcp-config durur", json.loads(arg(a2, "--settings"))["allowedMcpServers"] == [{"serverUrl": "https://ornek.test/mcp"}, {"serverName": "suflorvt"}]
        and arg(a2, "--mcp-config") == VT and "mcp__suflorvt__vt_sor" in arg(a2, "--allowedTools"))
a3 = BY.konus_args({"konus_onek_sabit": False}, "istem", "", None, B, "sonnet", [K])
kontrol("önek kapalıyken allowlist gider, env hiç yok", set(json.loads(arg(a3, "--settings"))) == {"allowedMcpServers"})
a4 = BY.konus_args({"claude_yalin": False}, "istem", "", None, B, "sonnet", [K])
kontrol("yalın kapalı: setting-sources/strict eklenmez, allowlist yine gider", "--setting-sources" not in a4 and "--strict-mcp-config" not in a4 and "allowedMcpServers" in arg(a4, "--settings"))

# 3. elenenler
kontrol("url'siz kaynak elenir", BY.konus_bilgi([dict(K, url="")]) == [] and BY.konus_args(A, "i", "", None, B, "s", [dict(K, url="")]) == BY.konus_args(A, "i", "", None, B, "s"))
kontrol("http adres elenir", BY.konus_bilgi([dict(K, url="http://ornek.test/mcp")]) == [])
kontrol("boşluklu / tırnaklı / 200+ karakterli adres elenir", all(BY.konus_bilgi([dict(K, url=u)]) == [] for u in ("https://ornek.test/a b", 'https://ornek.test/"x', "https://ornek.test/" + "a" * 200)))
kontrol("yazan sözcüklü ya da okuma öneksiz desen elenir", BY.konus_bilgi([dict(K, araclar=["create_*", "get_and_delete", "send_x", "*", "get_*_update", "label_x"])]) == [])
kontrol("karışık desenden yalnız okuyanlar kalır", BY.konus_bilgi([dict(K, araclar=["get_*", "create_x", "list_*"])])[0]["araclar"] == ["get_*", "list_*"])
kontrol("sunucu adında çift alt çizgi ya da geçersiz karakter elenir", BY.konus_bilgi([dict(K, sunucu="a__b")]) == [] and BY.konus_bilgi([dict(K, sunucu="a b")]) == [])
kontrol("en çok 4 kaynak", len(BY.konus_bilgi([dict(K, url=f"https://ornek.test/{i}") for i in range(6)])) == 4)
kontrol("yazma sözcüğü kümesi Python'da iki yerde aynı", BY.BILGI_YAZMA == eval(re.search(r"BILGI_YAZMA = (\{.*?\})", open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read(), re.S).group(1)))
sw = open(os.path.join(KOD, "brifing.swift"), encoding="utf-8").read()
kontrol("yazma sözcüğü kümesi Swift'te aynı", set(re.findall(r'"(\w+)"', re.search(r"let bilgiYazma: Set<String> = \[(.*?)\]", sw, re.S).group(1))) == BY.BILGI_YAZMA)
kontrol("okuma önekleri Swift'te aynı", re.findall(r'"(\w+)"', re.search(r"let bilgiOkuma: \[String\] = \[(.*?)\]", sw).group(1)) == list(BY.BILGI_OKUMA_ON))

# 4. bas-konus.py: kaynak seçimi, istem eki, sağlama
kod = open(os.path.join(KOD, "aktarici", "bas-konus.py"), encoding="utf-8").read()
ns = {"time": time, "re": __import__("re"), "os": os, "json": json, "__file__": os.path.join(KOD, "aktarici", "bas-konus.py"), "BEYIN": BY, "AYAR": {}, "_KS": {},
      "print": lambda *x: ns["_g"].append(" ".join(map(str, x))), "_g": [], "_t": lambda tr, en: tr, "bilgi_kaynaklari": lambda: [dict(K)], "gizli_acik": lambda: ns["_gizli"], "_gizli": False}
exec(kod[kod.index("BILGI_YEDEK_SN = "):kod.index("def konus_istem(")], ns)
exec(kod[kod.index("BILGI_ILK_SN, "):kod.index("def _konus_oku(")], ns)
kontrol("kaynak açık: varsayılan", [k["sunucu"] for k in ns["konus_bilgi_kaynaklari"]()] == ["claude_ai_Ornek_Kaynak"])
ns["AYAR"]["konus_bilgi_kaynagi"] = False; kontrol("ayar konus_bilgi_kaynagi: false → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["AYAR"].clear()
ns["_gizli"] = True; kontrol("gizli toplantı → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["_gizli"] = False
ns["bilgi_kaynaklari"] = lambda: [dict(K, url="")]; kontrol("url'siz kaynak → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["bilgi_kaynaklari"] = lambda: [dict(K)]
ist = ns["bilgi_istem"](BY.konus_bilgi([K]))
kontrol("istem eki: kaynak adı, konu, kaynağı ve dönemi söyle, kişi adı koyma, yazan araç yok", all(x in ist for x in ("Örnek Kaynak", "yapay satış verisi", "kaynağı ve dönemi", "kişi adı", "Yazan ya da değiştiren araç yok")) and ns["bilgi_istem"]([]) == "")
kontrol("konus_istem iki dönüş yolunda da eki ekler", kod.count("+ bilgi_istem(bilgi) + web_istem(web)") == 2 and "def konus_istem(vt=None, bilgi=None, web=False):" in kod)
kontrol("konus_ac: yalnız Claude Code beyninde kaynak, argüman ve istem birlikte", 'bilgi = konus_bilgi_kaynaklari() if sec["tur"] == "claude-code" else []' in kod and "konus_istem(vt, bilgi, web)" in kod and "sec[\"model\"], bilgi, web" in kod)  # 9 Kasım: derin tur model/düşünme argümanı eklendi (ds["model"] if ds else sec["model"], bilgi, web, ds["effort"] …); kaynak yine birlikte gider
# sağlama: her turun init'i; boş/pending yedeğe geçirmez, failed/needs-auth geçirir, 60 sn + 2 tur kuralı
SN, AD = "claude_ai_Ornek_Kaynak", "Örnek Kaynak"
def init(sunucular, araclar): return {"type": "system", "subtype": "init", "mcp_servers": sunucular, "tools": araclar}
BAGLI = init([{"name": "claude.ai Ornek Kaynak", "status": "connected"}], ["Read", "mcp__claude_ai_Ornek_Kaynak__get_x", "mcp__claude_ai_Ornek_Kaynak__list_y"])
def yeni(t0=None):
    ns["_g"].clear(); ns["_KS"].clear(); ns["_KS"].update(bilgi_bekle=[(SN, AD)], bilgi_bagli=set(), bilgi_tur=0, bilgi_t0=time.time() if t0 is None else t0)
def durum(st): return init([{"name": "claude.ai Ornek Kaynak", "status": st}] if st else [], [])
yeni(); ns["bilgi_saglama"](BAGLI); ns["bilgi_saglama"](BAGLI)
kontrol("bağlandı: 'hazır — Örnek Kaynak (2 araç)' bir kez, yedek yok", ns["_g"] == ["KONUŞ: bilgi kaynağı hazır — Örnek Kaynak (2 araç)"] and not ns["_KS"].get("bilgi_yedek_t"), ns["_g"])
yeni(); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](BAGLI)
kontrol("ilk tur boş, ikincisi connected: yedek yok, hazır yazılır", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == ["KONUŞ: bilgi kaynağı hazır — Örnek Kaynak (2 araç)"], ns["_g"])
yeni(); ns["bilgi_saglama"](init([], []))
kontrol("tek boş init yedeğe geçirmez (henüz bağlanmadı)", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == [] and ns["konus_bilgi_kaynaklari"]() != [])
yeni(); ns["bilgi_saglama"](durum("pending"))
kontrol("tek pending yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == [])
for st in ("failed", "needs-auth"):
    yeni(); ns["bilgi_saglama"](durum(st))
    kontrol(f"{st}: ilk init'te hemen yedek (günlük + 30 dk)", ns["_g"] == [f"KONUŞ: bilgi kaynağı bağlanamadı — {AD} ({st})"] and 1790 < ns["_KS"]["bilgi_yedek_t"] - time.time() <= 1800, ns["_g"])
    kontrol(f"  yedek sürerken kaynaksız ({st})", ns["konus_bilgi_kaynaklari"]() == [])
yeni(t0=time.time() - 10); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](durum("pending"))
kontrol("60 sn içinde 2 turda hiç connected yok → yedek", ns["_g"] == [f"KONUŞ: bilgi kaynağı bağlanamadı — {AD} (pending)"] and ns["_KS"].get("bilgi_yedek_t"), ns["_g"])
yeni(t0=time.time() - 61); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](durum("pending"))
kontrol("60 sn geçtikten sonra boş/pending turları yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == [], ns["_g"])
yeni(); ns["bilgi_saglama"](BAGLI); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](init([], []))
kontrol("bir kez connected görüldükten sonra boş turlar yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t"))
yeni(t0=time.time() - 10); ns["bilgi_saglama"](init([{"name": "claude.ai Ornek Kaynak", "status": "connected"}], ["Read"])); ns["bilgi_saglama"](init([{"name": "claude.ai Ornek Kaynak", "status": "connected"}], ["Read"]))
kontrol("bağlı ama araç yok: sayılır, 2 turda yedek (araç yok)", ns["_g"] == [f"KONUŞ: bilgi kaynağı bağlanamadı — {AD} (araç yok)"], ns["_g"])
yeni(); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](durum("pending")); ns["bilgi_saglama"](durum("pending"))
kontrol("bağlanma süresi (8 sn) içindeki erken turlar yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == [], ns["_g"])
# 4b. Yeni süreçte kaynağı anan soru bağlantıyı bekler (1 Kasım canlı: ilk soru 6 sn'lik bağlantıdan önce gidip "bağlanamıyorum" dedi)
yeni(); b = ns["bilgi_bekle_sn"]("Örnek verisine göre son 7 günün satışı?")
kontrol("yeni süreç + soru kaynağı anıyor → ~8 sn bekle", 7 < b <= 8, b)
kontrol("büyük harf / İ ile de tanır", ns["bilgi_bekle_sn"]("ÖRNEK KAYNAĞI'NDAN ne var?") > 0)
kontrol("kaynağı anmayan soru beklemez", ns["bilgi_bekle_sn"]("Bugün günlerden ne?") == 0)
yeni(t0=time.time() - 9); kontrol("süreç 8 sn'den eskiyse beklemez", ns["bilgi_bekle_sn"]("Örnek verisi?") == 0)
yeni(); ns["bilgi_saglama"](BAGLI); kontrol("kaynak bu süreçte bağlandıysa beklemez", ns["bilgi_bekle_sn"]("Örnek verisi?") == 0)
yeni(); ns["_KS"].update(bilgi_bekle=[]); kontrol("kaynaksız süreçte beklemez", ns["bilgi_bekle_sn"]("Örnek verisi?") == 0)
kontrol("gonder() soruyu yazmadan önce bekler", kod.index("bks = bilgi_bekle_sn(ms)") < kod.index('tur["t_gonder"] = time.time(); tur.pop("t_ilk_yanit"'))
ns["_KS"]["bilgi_yedek_t"] = time.time() - 1; kontrol("yedek süresi dolunca kaynak geri gelir", len(ns["konus_bilgi_kaynaklari"]()) == 1)
yeni(); ns["_KS"].update(bilgi_bekle=[]); ns["bilgi_saglama"](init([], [])); kontrol("kaynaksız süreçte sağlama sessiz", ns["_g"] == [])
rl = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read(); gd = rl[rl.index("def gizli_degistir("):rl.index("def gizli_view(")]
kontrol("gizli kip açılınca açık Konuş süreci kapanır (kaynaklı süreç dahil; sonraki açılış gizli kipte kaynaksız)", 'konus_kapat("gizli toplantı")' in gd and 'GIZLI["acik"]' in gd)
kontrol("okuyucu init'i tur beklemeden sağlar (nesil denetimiyle)", 'subtype") == "init" and _KS.get("nesil") == nesil: bilgi_saglama(j)' in kod)

# 5. toplanti-oturum.py: url alanı, Faz 1 davranışı aynı
to = open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read()
n2 = {"re": re, "AYAR": {"kisi_kaynaklari": [], "toplanti_bilgi_kaynaklari": [{"sunucu": "claude.ai Ornek Kaynak", "araclar": ["get_*"], "konu": "x", "url": "https://ornek.test/mcp"},
                                                                   {"sunucu": "claude.ai Baska", "araclar": ["list_*"], "url": "http://x.test"}, {"sunucu": "claude.ai Yok", "araclar": ["get_*"]}]}}
exec(to[to.index("BILGI_OKUMA_RX = "):to.index("def bilgi_kaynagi_arac(")], n2)
bk = n2["bilgi_kaynaklari"]()
kontrol("bilgi_kaynaklari: url yalnız geçerli https ise gelir, öbür alanlar aynı", [k["url"] for k in bk] == ["https://ornek.test/mcp", "", ""] and bk[0]["sunucu"] == "claude_ai_Ornek_Kaynak" and bk[0]["ad"] == "Ornek Kaynak")
kontrol("beyin.mcp_ad = toplantı oturumunun mcp_sunucu_adi'si", all(BY.mcp_ad(x) == n2["mcp_sunucu_adi"](x) for x in ("claude.ai Ornek Kaynak", "claude.ai  A-B (c)", "suflorvt", "x y")))
# 6. Hazırlıkta kaynak (brifing; 2 Kasım): tek seferlik -p bağlayıcıyı ilk turda göremediği için FIFO kipi, istem stdin'den
ba = BY.brifing_args(A, "ISTEM", B, True, [K]); bs = json.loads(arg(ba, "--settings"))
kontrol("brifing kaynaklı: stream-json giriş/çıkış, istem argümanda yok", ba[:6] == ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"] and "ISTEM" not in ba, ba[:8])
kontrol("brifing kaynaklı: okuma araçları + Read/Grep/Glob, strict yok, allowedMcpServers yalnız kaynağın url'si",
        arg(ba, "--allowedTools").startswith("Read,Grep,Glob,mcp__claude_ai_Ornek_Kaynak__get_*") and "--strict-mcp-config" not in ba and bs.get("allowedMcpServers") == [{"serverUrl": K["url"]}] and arg(ba, "--add-dir") == B)
kontrol("brifing: kaynak yoksa ya da tam (yalın olmayan) çağrıda eski tek seferlik düzen", BY.brifing_args(A, "ISTEM", B, True, []) == BY.brifing_args(A, "ISTEM", B) and
        BY.brifing_args(A, "ISTEM", B, False, [K]) == BY.brifing_args(A, "ISTEM", B, False) and "--strict-mcp-config" in BY.brifing_args(A, "ISTEM", B))
kontrol("brifing: url'siz kaynak süzülür (eski düzen)", BY.brifing_args(A, "ISTEM", B, True, [dict(K, url="")]) == BY.brifing_args(A, "ISTEM", B))
bf = open(os.path.join(KOD, "aktarici", "brifing-ses.py"), encoding="utf-8").read(); n3 = {"json": json, "os": os, "time": time}
exec(bf[bf.index("BRIFING_ISTEM = "):bf.index("BRIFING_BILGI_SN")], n3)
for dl in ("tr", "en"):
    bos = n3["BRIFING_ISTEM"][dl].format(canli="/c", olay="{}", bilgi="", veri="", va="")
    bi, vj, va = n3["BRIFING_BILGI"][dl]; dolu = n3["BRIFING_ISTEM"][dl].format(canli="/c", olay="{}", bilgi=bi.format(kay="«Örnek»"), veri=vj, va=va)
    kontrol(f"brifing istemi ({dl}): kaynaksız 'veri' ve kaynak satırı yok; kaynaklıda ikisi de var, kişi adı yasağı ve konu dışı kuralı",
            '"veri"' not in bos and "«Örnek»" not in bos and '"dikkat": ["…"], "veri": ["…"]}' in dolu and "«Örnek»" in dolu and ("kişi adı" in dolu or "person names" in dolu) and ("Konu dışıysa" in dolu or "off-topic" in dolu))
kontrol("brifing sonucu: veri yalnız kaynak açıkken ve doluysa eklenir", 'if bilgi and temiz(j.get("veri"), 3): sonuc["veri"]' in bf)
kontrol("brifing kaynağı Konuş'la aynı kuraldan (ayar, gizli kip, yedek)", "bilgi = konus_bilgi_kaynaklari()" in bf and "BEYIN.brifing_args(AYAR, istem, BASE, yalin, bilgi if yalin else None)" in bf)
kontrol("FIFO kipinde mesaj BRIFING_BILGI_SN sonra yazılır, giriş kapanır", "time.sleep(max(0, BRIFING_BILGI_SN - (time.time() - t0)))" in bf and "os.close(w)" in bf)
pn = open(os.path.join(KOD, "pano", "pano.html"), encoding="utf-8").read(); df = open(os.path.join(KOD, "aktarici", "defter.py"), encoding="utf-8").read()
kontrol("'Güncel veri' panoda dört yerde (hazırlık, brifing, brifing penceresi, Bugün), defterde ve Konuş'un sıradaki toplantı bloğunda", pn.count("'Güncel veri'") == 4 and '("veri", "dikkat", "acik", "gecmis")' in df and '("veri", _t("Güncel veri"' in kod)
# 7. toplantı oturumu izin kararı (5 Kasım): okuma araçları ve web onaysız; yazma sorulur; aynı araç yeniden/paralel sorulmaz; gizli toplantıda web yok
import threading
def izin_ns(ayar, gizli=False):
    n = {"re": re, "threading": threading, "json": json, "os": os, "time": time, "AYAR": dict(ayar), "_t": lambda a_, b_: a_, "gizli_acik": lambda: n["_gz"], "_gz": gizli}
    exec(compile(to, "toplanti-oturum.py", "exec"), n)
    n.update(_gonder=[], sorulan=[], karar="onaylandi", _topo_gonder=lambda o: n["_gonder"].append(o["response"]["response"]["behavior"]), _topo_mesaj=lambda *a, **k: None,
             _topo_izle_mi=lambda ad, gi: False, _topo_tc_okuma=lambda ad, gi: False, _topo_oto=lambda ad, gi: None, arac_cumlesi=lambda ad, gi=None: ad,
             izin_metni=lambda ad, gi=None: ad, izin_bekle=lambda iid, *a: (time.sleep(0.2), n["karar"])[1])
    n["izin_iste"] = lambda tur, ne, ay=None, **k: (n["sorulan"].append(ne), "i%d" % len(n["sorulan"]))[1]
    n["TOPO"].update(izin_hatirla=set(), bilgi_sorgu=0, web_sorgu=0)
    return n
KS = [{"sunucu": "claude.ai Ornek Kaynak", "araclar": ["get_*", "list_*", "query_*"], "konu": "x"}]
def sor(n, ad, gi=None):
    n["_topo_izin"]({"request_id": "r", "request": {"tool_name": ad, "input": gi or {}}}); return n["_gonder"][-1], len(n["sorulan"])
OK = "mcp__claude_ai_Ornek_Kaynak__"
n = izin_ns({"toplanti_bilgi_kaynaklari": KS})
kontrol("bilgi_onaysiz varsayılan açık: kaynağın okuma aracı sorulmadan geçer, sınırsız gibi (9 sorgu)", all(sor(n, OK + "query_metrics", {"d": i}) == ("allow", 0) for i in range(9)))
kontrol("yazma aracı (kaynağın içinde) reddedilir, sorulmaz", sor(n, OK + "update_campaign") == ("deny", 0))
kontrol("e-posta gönderme (başka bağlayıcı) sorulur", sor(n, "mcp__claude_ai_Posta__send_mail", {"to": "a"}) == ("allow", 1))
kontrol("e-posta gönderme farklı girdiyle yeniden sorulur (yazma araçları girdiye bağlı hatırlanır)", sor(n, "mcp__claude_ai_Posta__send_mail", {"to": "b"}) == ("allow", 2))
kontrol("aynı girdiyle ikinci kez sorulmaz", sor(n, "mcp__claude_ai_Posta__send_mail", {"to": "b"}) == ("allow", 2))
kontrol("web araması varsayılan onaysız; WebFetch genel adres onaysız", sor(n, "WebSearch", {"query": "Firma Ltd"}) == ("allow", 2) and sor(n, "WebFetch", {"url": "https://www.linkedin.com/company/x"}) == ("allow", 2))
kontrol("WebFetch yerel/özel adres reddedilir", all(sor(n, "WebFetch", {"url": u})[0] == "deny" for u in ("http://localhost:8765/status", "http://127.0.0.1/x", "http://192.168.1.5/", "file:///etc/passwd", "http://[::1]/", "http://nas.local/x", "https://tek")))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS}, gizli=True)
kontrol("gizli toplantıda WebSearch/WebFetch reddedilir, sorulmaz", sor(n, "WebSearch", {"query": "x"}) == ("deny", 0) and sor(n, "WebFetch", {"url": "https://a.com"}) == ("deny", 0))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS, "web_arastirma": False})
kontrol("web_arastirma kapalı: web araçları reddedilir; istemde web bölümü yok", sor(n, "WebSearch", {"query": "x"}) == ("deny", 0) and "WebSearch" not in n["topo_istem"]())
kontrol("web_arastirma açıkken istemde sınır cümlesi (yalnız ad ve konu, döküm alıntısı yok, gizli toplantı, kaynak bağlantısı)", all(x in izin_ns({})["topo_istem"]() for x in ("yalnız firma ya da kişi adı", "döküm alıntısı", "Gizli toplantıda", "Kaynak: <site>, <bağlantı>")))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS, "bilgi_onaysiz": False})
kontrol("bilgi_onaysiz kapalı: kaynağın okuma aracı ve web ilk kez sorulur", sor(n, OK + "get_x", {"a": 1}) == ("allow", 1) and sor(n, "WebSearch", {"query": "x"}) == ("allow", 2))
kontrol("kapalıyken de onaylanan araç yeniden sorulmaz (farklı girdiyle bile)", sor(n, OK + "get_x", {"a": 2}) == ("allow", 2) and sor(n, "WebSearch", {"query": "y"}) == ("allow", 2) and sor(n, "WebFetch", {"url": "https://a.com"}) == ("allow", 3))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS, "bilgi_onaysiz": False}); n["karar"] = "reddedildi"
kontrol("reddedilen araç hatırlanmaz (yeniden sorulur)", sor(n, OK + "get_x") == ("deny", 1) and sor(n, OK + "get_x") == ("deny", 2))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS, "bilgi_onaysiz": False}); n["_gonder"].clear()
ts = [threading.Thread(target=n["_topo_izin"], args=({"request_id": "r", "request": {"tool_name": OK + "query_metrics", "input": {"d": i}}},)) for i in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
kontrol("aynı araç aynı anda iki kez çağrılınca tek soru (çift soru hatası)", len(n["sorulan"]) == 1 and n["_gonder"] == ["allow", "allow"], (n["sorulan"], n["_gonder"]))
n = izin_ns({"toplanti_bilgi_kaynaklari": KS}); n["TOPO"]["bilgi_sorgu"] = n["TOPO_BILGI_EN_COK"]
kontrol("kaçak döngü tavanı (200) dolunca sorulur", sor(n, OK + "query_metrics") == ("allow", 1) and n["TOPO_BILGI_EN_COK"] == 200)
# 7b. Claude in Chrome (yalnız linkedin.com okuma) ve kişi araştırma yedek zinciri (5 Kasım)
C = "mcp__claude-in-chrome__"
n = izin_ns({})
kontrol("chrome: okuma araçları sorulmadan geçer (tabs, navigate linkedin, get_page_text, find, read_page)", all(sor(n, C + a, g) == ("allow", 0) for a, g in (("tabs_create_mcp", {}), ("navigate", {"url": "https://www.linkedin.com/in/x"}), ("get_page_text", {}), ("find", {"query": "x"}), ("read_page", {}), ("tabs_close_mcp", {}))))
kontrol("chrome: linkedin dışı ya da http/benzer alan adı navigate reddedilir", all(sor(n, C + "navigate", {"url": u})[0] == "deny" for u in ("https://example.com", "http://linkedin.com/x", "https://linkedin.com.evil.test/x", "https://evillinkedin.com/", "")))
kontrol("chrome: yazma/etkileşim araçları reddedilir, sorulmaz", all(sor(n, C + a, {"action": "left_click"}) == ("deny", 0) for a in ("computer", "form_input", "javascript_tool", "file_upload", "upload_image", "browser_batch", "shortcuts_execute", "gif_creator", "read_network_requests")))
kontrol("kanca yolu (izin_arac) aynı karar", n["topo_chrome_karar"](C + "navigate", {"url": "https://www.linkedin.com/company/x"}) == "allow" and n["topo_chrome_karar"](C + "computer", {}) == "deny" and n["topo_chrome_karar"]("Read", {}) is None)
n = izin_ns({}, gizli=True); kontrol("gizli toplantıda chrome araçları da reddedilir", sor(n, C + "get_page_text") == ("deny", 0))
n = izin_ns({"linkedin_chrome": False}); kontrol("linkedin_chrome kapalı: chrome reddedilir, --chrome bayrağı yok, istemde Chrome adımı atlanır", sor(n, C + "get_page_text") == ("deny", 0) and not n["topo_chrome_acik"]() and "(Chrome kapalı: atla)" in n["topo_istem"]())
n = izin_ns({"bilgi_onaysiz": False}); kontrol("bilgi_onaysiz kapalı: izinli chrome aracı ilk kez sorulur, sonra hatırlanır", sor(n, C + "get_page_text") == ("allow", 1) and sor(n, C + "get_page_text") == ("allow", 1))
ist = izin_ns({})["topo_istem"]()
kontrol("istem: zincir chrome → bağlayıcı → web, yalnız okuma, oturum kapalıysa not + sonraki, kaynak kartta", all(x in ist for x in ("1) Claude in Chrome", "YALNIZ OKUMA", "2) Kişi/firma bilgi bağlayıcısı", "3) WebSearch", "oturum açık değil", "Chrome'u açmaya çalışma", "Kaynak: LinkedIn (Chrome)")))
kt = open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read(); sw2 = open(os.path.join(KOD, "brifing.swift"), encoding="utf-8").read(); iz = open(os.path.join(KOD, "aktarici", "izin.py"), encoding="utf-8").read()
kontrol("--chrome yalnız ayar açıkken oturum argümanında; Brifing.app toplantı kipi bayrağı kabul eder; kanca yolu topo_chrome_karar'ı çağırır", '(["--chrome"] if topo_chrome_acik() else [])' in kt and '["-p", "--print", "--verbose", "--chrome"]' in sw2 and "topo_chrome_karar" in iz)
# kişi bağlayıcısı: kisi_kaynaklari + açık okuma adları (adı okuma önekli olmayan okuma araçları), yazma adı yine reddedilir
APO = {"sunucu": "plugin:sales:apollo", "araclar": [], "okuma": ["apollo_people_match", "apollo_mixed_people_api_search", "apollo_contacts_create"], "konu": "kişi/firma", "ad": "Apollo"}
n = izin_ns({"kisi_kaynaklari": [APO]}); P = "mcp__plugin_sales_apollo__"
kontrol("kisi_kaynaklari: listedeki okuma araçları onaysız; yazma adı ('create') listede olsa da reddedilir; listede olmayan reddedilir", sor(n, P + "apollo_people_match") == ("allow", 0) and sor(n, P + "apollo_mixed_people_api_search") == ("allow", 0) and sor(n, P + "apollo_contacts_create") == ("deny", 0) and sor(n, P + "apollo_tasks_update") == ("deny", 0))
kontrol("kişi bağlayıcısı istemde listelenir", "Apollo" in n["topo_istem"]())
# günlük: akıştan tek satırlık KİŞİ ARAŞTIRMA (chrome yok → web; chrome hata; bağlayıcı yok; ikisi de yok)
import tempfile
def akis(satirlar, ayar):
    n = izin_ns(ayar); g = []; n["print"] = lambda *a: g.append(" ".join(map(str, a))); n["TOPO"].update(nesil=5, kapali_nesil=5, durum="calisiyor")
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8"); f.write("\n".join(json.dumps(x, ensure_ascii=False) for x in satirlar) + "\n"); f.close()
    n["_topo_oku"](f.name, 5); os.unlink(f.name); return [x for x in g if x.startswith("KİŞİ ARAŞTIRMA")]
init = lambda ms: {"type": "system", "subtype": "init", "session_id": "s", "mcp_servers": ms}
tu = lambda i, ad: {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": ad, "input": {}}]}}
tr = lambda i, e: {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "is_error": e, "content": "x"}]}}
g1 = akis([init([])], {}); kontrol("Chrome yok: 'chrome yok → web' tek satır", len(g1) == 1 and "chrome yok → web" in g1[0], g1)
g2 = akis([init([{"name": "claude-in-chrome", "status": "connected"}]), tu("a", C + "get_page_text"), tr("a", True), tu("b", "WebSearch"), tr("b", False)], {})
kontrol("Chrome bağlı ama araç hata (oturum kapalı): hata satırı web'e düşülür; web tamam; kaynak etiketli", g2[0].endswith("bağlı") and "chrome → hata (sonraki kaynağa geçilir: web)" in g2[1] and "web → tamam" in g2[2], g2)
g3 = akis([init([]), tu("c", "WebSearch"), tr("c", False)], {"kisi_kaynaklari": [APO]}); kontrol("bağlayıcı yok + chrome yok → web ile sürer (bağlayıcı çağrısı yok, hata yok)", len(g3) == 2 and "web → tamam" in g3[1], g3)
g4 = akis([init([]), tu("d", P + "apollo_people_match"), tr("d", True), tu("e", "WebSearch"), tr("e", False)], {"kisi_kaynaklari": [APO]})
kontrol("bağlayıcı hata verirse sonraki: web", "bağlayıcı → hata (sonraki kaynağa geçilir: web)" in g4[1] and "web → tamam" in g4[2], g4)
ay = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read()
kontrol("kisi_kaynaklari ayarsızken Apollo varsayılanı: yalnız ücretsiz iki okuma aracı onaysız; kredi harcayan/yazan her Apollo aracı reddedilir", all(sor(izin_ns({}), "mcp__plugin_sales_apollo__" + a) == (r, 0) for a, r in (("apollo_mixed_people_api_search", "allow"), ("apollo_organizations_lookup", "allow"), ("apollo_mixed_companies_search", "deny"), ("apollo_organizations_job_postings", "deny"), ("apollo_people_match", "deny"), ("apollo_organizations_enrich", "deny"), ("apollo_people_bulk_match", "deny"), ("apollo_contacts_create", "deny"), ("apollo_emailer_messages_send_now", "deny"), ("apollo_sequences_update", "deny"), ("apollo_agent_bulk_enrich", "deny"))))
kontrol("kisi_kaynaklari: [] Apollo'yu kapatır (araç sorulur, kaynak sayılmaz)", sor(izin_ns({"kisi_kaynaklari": []}), "mcp__plugin_sales_apollo__apollo_people_match")[1] == 1)
kontrol("ayarlar: web_arastirma ve bilgi_onaysiz varsayılan açık, AYAR_PANO'da ve panoda (AYG)", '"web_arastirma": ("bool", True, None)' in ay and '"bilgi_onaysiz": ("bool", True, None)' in ay and "['web_arastirma','bool'" in pn and "['bilgi_onaysiz','bool'" in pn)
# 8. Konuş'ta web araştırması (5 Kasım): ayar konus_web varsayılan kapalı; açıkken de gizli toplantıda ve web_arastirma kapalıyken kapalı; kurulu Brifing yardımcısı
# WebSearch/WebFetch'i tanımıyorsa (derleme.json SHA'sı web'li brifing.swift'e eşit değil) kapalı + tek uyarı; destek varsa konus_args web araçlarını ekler, istemde sınır cümlesi
import hashlib, tempfile
kontrol("ayar konus_web varsayılan kapalı, AYAR_PANO'da ve panoda (AYG)", '"konus_web": ("bool", False, None)' in ay and "['konus_web','bool'" in pn)
TW = tempfile.mkdtemp(prefix="konus-web-"); eski = os.path.join(TW, "eski.swift"); yeni = os.path.join(TW, "yeni.swift")
open(eski, "w").write('let araclar: Set<String> = ["Read", "Grep", "Glob"]\n'); open(yeni, "w").write('let araclar: Set<String> = ["Read", "Grep", "Glob", "WebSearch", "WebFetch"]\n')
def derleme(y): json.dump({"SuflorBrifing": hashlib.sha256(open(y, "rb").read()).hexdigest()}, open(os.path.join(TW, "derleme.json"), "w"))
derleme(eski); kontrol("yardımcı eski kaynakla derlenmiş → web desteği yok", ns["konus_web_destek"](TW, [eski, yeni]) is False)
derleme(yeni); kontrol("yardımcı web'li kaynakla derlenmiş → destek var", ns["konus_web_destek"](TW, [eski, yeni]) is True)
kontrol("derleme kaydı yok → destek yok", ns["konus_web_destek"](os.path.join(TW, "yok"), [yeni]) is False)
sw_gercek = open(os.path.join(KOD, "brifing.swift"), encoding="utf-8").read()
kontrol("depodaki brifing.swift henüz web araçlarını tanımıyorsa kurulu yardımcı 'destek yok' sayılır (yeniden derleme kullanıcı yanındayken)",
        bool(ns["KONUS_WEB_RX"].search(sw_gercek)) == ("\"WebSearch\", \"WebFetch\"" in sw_gercek))
ns["AYAR"].clear(); ns["_KS"].clear(); ns["_g"].clear(); ns["AYAR"]["uygulama"] = TW; derleme(yeni); ns["_konus_swift_yerler"] = lambda: [yeni]
kontrol("konus_web ayarı yokken kapalı (web_arastirma açık olsa da)", ns["konus_web_acik"]() is False and not ns["_g"])
ns["AYAR"]["konus_web"] = True; kontrol("konus_web açık + destek var → açık", ns["konus_web_acik"]() is True)
ns["_gizli"] = True; kontrol("gizli toplantı → kapalı", ns["konus_web_acik"]() is False); ns["_gizli"] = False
ns["AYAR"]["web_arastirma"] = False; kontrol("web_arastirma kapalı → kapalı", ns["konus_web_acik"]() is False); del ns["AYAR"]["web_arastirma"]
derleme(eski); kontrol("destek yok → kapalı, günlükte tek uyarı (yinelenmez)", ns["konus_web_acik"]() is False and ns["konus_web_acik"]() is False and sum("yeniden derleme" in x for x in ns["_g"]) == 1)
wi = ns["web_istem"](True)
kontrol("web istemi: yalnız ad ve konu, döküm alıntısı/iç sayı yasağı, kaynak ve tarih, doğrulanmadı; kapalıyken boş", all(x in wi for x in ("yalnız kişi ya da firma adı ve konu", "döküm alıntısı", "iç sayı", "kaynağı (site, bağlantı)", "doğrulanmadı")) and ns["web_istem"](False) == "")
aw = BY.konus_args(A, "ISTEM", "", None, B, web=True); ab = BY.konus_args(A, "ISTEM", "", None, B)
kontrol("konus_args web=True: --allowedTools ve --tools'ta WebSearch,WebFetch; web=False eskisiyle aynı", aw[aw.index("--allowedTools") + 1] == "Read,Grep,Glob,WebSearch,WebFetch" and aw[aw.index("--tools") + 1] == "Read,Grep,Glob,WebSearch,WebFetch"
        and "WebSearch" not in " ".join(ab) and ab[ab.index("--tools") + 1] == "Read,Grep,Glob")
kontrol("çağrı yeri: Konuş süreci konus_web_acik ile açılır, istem web_istem alır", "web = sec[\"tur\"] == \"claude-code\" and konus_web_acik()" in kod and "konus_istem(vt, bilgi, web)" in kod and "bilgi, web)" in kod)
kontrol("__pycache__ yazılmadı", not [d for d, _, f in os.walk(KOD) if "__pycache__" in d and ".git" not in d and "_yedek" not in d])
print(f"{len(hatalar) and 'KALDI: ' + str(len(hatalar)) or 'hepsi geçti'}"); sys.exit(1 if hatalar else 0)
