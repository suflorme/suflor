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
ns = {"time": time, "BEYIN": BY, "AYAR": {}, "_KS": {}, "print": lambda *x: ns["_g"].append(" ".join(map(str, x))), "_g": [],
      "_t": lambda tr, en: tr, "bilgi_kaynaklari": lambda: [dict(K)], "gizli_acik": lambda: ns["_gizli"], "_gizli": False}
exec(kod[kod.index("BILGI_YEDEK_SN = "):kod.index("def konus_istem(")], ns)
exec(kod[kod.index("BILGI_ILK_SN, "):kod.index("def _konus_oku(")], ns)
kontrol("kaynak açık: varsayılan", [k["sunucu"] for k in ns["konus_bilgi_kaynaklari"]()] == ["claude_ai_Ornek_Kaynak"])
ns["AYAR"]["konus_bilgi_kaynagi"] = False; kontrol("ayar konus_bilgi_kaynagi: false → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["AYAR"].clear()
ns["_gizli"] = True; kontrol("gizli toplantı → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["_gizli"] = False
ns["bilgi_kaynaklari"] = lambda: [dict(K, url="")]; kontrol("url'siz kaynak → kaynaksız", ns["konus_bilgi_kaynaklari"]() == []); ns["bilgi_kaynaklari"] = lambda: [dict(K)]
ist = ns["bilgi_istem"](BY.konus_bilgi([K]))
kontrol("istem eki: kaynak adı, konu, kaynağı ve dönemi söyle, kişi adı koyma, yazan araç yok", all(x in ist for x in ("Örnek Kaynak", "yapay satış verisi", "kaynağı ve dönemi", "kişi adı", "Yazan ya da değiştiren araç yok")) and ns["bilgi_istem"]([]) == "")
kontrol("konus_istem iki dönüş yolunda da eki ekler", kod.count("+ bilgi_istem(bilgi)") == 2 and "def konus_istem(vt=None, bilgi=None):" in kod)
kontrol("konus_ac: yalnız Claude Code beyninde kaynak, argüman ve istem birlikte", 'bilgi = konus_bilgi_kaynaklari() if sec["tur"] == "claude-code" else []' in kod and "konus_istem(vt, bilgi)" in kod and "sec[\"model\"], bilgi)" in kod)
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
yeni(); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](durum("pending"))
kontrol("60 sn içinde 2 turda hiç connected yok → yedek", ns["_g"] == [f"KONUŞ: bilgi kaynağı bağlanamadı — {AD} (pending)"] and ns["_KS"].get("bilgi_yedek_t"), ns["_g"])
yeni(t0=time.time() - 61); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](durum("pending"))
kontrol("60 sn geçtikten sonra boş/pending turları yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t") and ns["_g"] == [], ns["_g"])
yeni(); ns["bilgi_saglama"](BAGLI); ns["bilgi_saglama"](init([], [])); ns["bilgi_saglama"](init([], []))
kontrol("bir kez connected görüldükten sonra boş turlar yedeğe geçirmez", not ns["_KS"].get("bilgi_yedek_t"))
yeni(); ns["bilgi_saglama"](init([{"name": "claude.ai Ornek Kaynak", "status": "connected"}], ["Read"])); ns["bilgi_saglama"](init([{"name": "claude.ai Ornek Kaynak", "status": "connected"}], ["Read"]))
kontrol("bağlı ama araç yok: sayılır, 2 turda yedek (araç yok)", ns["_g"] == [f"KONUŞ: bilgi kaynağı bağlanamadı — {AD} (araç yok)"], ns["_g"])
ns["_KS"]["bilgi_yedek_t"] = time.time() - 1; kontrol("yedek süresi dolunca kaynak geri gelir", len(ns["konus_bilgi_kaynaklari"]()) == 1)
yeni(); ns["_KS"].update(bilgi_bekle=[]); ns["bilgi_saglama"](init([], [])); kontrol("kaynaksız süreçte sağlama sessiz", ns["_g"] == [])
rl = open(os.path.join(KOD, "relay.py"), encoding="utf-8").read(); gd = rl[rl.index("def gizli_degistir("):rl.index("def gizli_view(")]
kontrol("gizli kip açılınca açık Konuş süreci kapanır (kaynaklı süreç dahil; sonraki açılış gizli kipte kaynaksız)", 'konus_kapat("gizli toplantı")' in gd and 'GIZLI["acik"]' in gd)
kontrol("okuyucu init'i tur beklemeden sağlar (nesil denetimiyle)", 'subtype") == "init" and _KS.get("nesil") == nesil: bilgi_saglama(j)' in kod)

# 5. toplanti-oturum.py: url alanı, Faz 1 davranışı aynı
to = open(os.path.join(KOD, "aktarici", "toplanti-oturum.py"), encoding="utf-8").read()
n2 = {"re": re, "AYAR": {"toplanti_bilgi_kaynaklari": [{"sunucu": "claude.ai Ornek Kaynak", "araclar": ["get_*"], "konu": "x", "url": "https://ornek.test/mcp"},
                                                                   {"sunucu": "claude.ai Baska", "araclar": ["list_*"], "url": "http://x.test"}, {"sunucu": "claude.ai Yok", "araclar": ["get_*"]}]}}
exec(to[to.index("BILGI_OKUMA_RX = "):to.index("def bilgi_kaynagi_arac(")], n2)
bk = n2["bilgi_kaynaklari"]()
kontrol("bilgi_kaynaklari: url yalnız geçerli https ise gelir, öbür alanlar aynı", [k["url"] for k in bk] == ["https://ornek.test/mcp", "", ""] and bk[0]["sunucu"] == "claude_ai_Ornek_Kaynak" and bk[0]["ad"] == "Ornek Kaynak")
kontrol("beyin.mcp_ad = toplantı oturumunun mcp_sunucu_adi'si", all(BY.mcp_ad(x) == n2["mcp_sunucu_adi"](x) for x in ("claude.ai Ornek Kaynak", "claude.ai  A-B (c)", "suflorvt", "x y")))
kontrol("__pycache__ yazılmadı", not [d for d, _, f in os.walk(KOD) if "__pycache__" in d and ".git" not in d and "_yedek" not in d])
print(f"{len(hatalar) and 'KALDI: ' + str(len(hatalar)) or 'hepsi geçti'}"); sys.exit(1 if hatalar else 0)
