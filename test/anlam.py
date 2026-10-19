#!/usr/bin/env python3
# Proje hazırlığı T4 — anlama göre arama (`baglam.py gomme`, gomme-isci.py, RRF): başka sözcüklerle sorulan soru bulunuyor; sunucu yokken arama
# beklemeden yalnız sözcükle döner ve sunucuyu açar; gömme kaldığı yerden sürer (ikinci tur 0), değişen dosyanın yalnız yeni parçası gömülür ve
# sunucu yeniden yükler; veritabanı kipinde dışa aktarım gömülmez; toplantıda gömme başlamaz; sunucu boşta kapanır; gecikme sözcük aramasına
# göre en çok +50 ms (§7/6). Gerçek model ister (<ortak>/cevir-venv + anlam-modeller; yoksa atlanır). ~1 dk.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/anlam.py      (kaldı → çıkış 1)
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import bosport  # noqa: canlı kullanım koruması (gerçek model)

KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = "/Users/Shared/Suflor"
if not (os.path.exists(os.path.join(ORTAK, "cevir-venv", "bin", "python")) and os.path.isdir(os.path.join(ORTAK, "anlam-modeller"))):
    print("anlam: atlandı (cevir-venv ya da anlam-modeller yok)"); sys.exit(0)
T = tempfile.mkdtemp(prefix="suflor-anlam-"); P = os.path.join(T, "proje"); U = os.path.join(T, "uyg"); os.makedirs(os.path.join(U, "canli"))
BELGE = {
    "lojistik/tuna-notlari.md": "# Lojistik görüşmesi\n\nKamyon rotalarını yalnız Tuna planlıyor; teslimat tarihleri de çoğunlukla yalnız onda. Depo etiketleri kendisine geliyor.\n",
    "satis/kampanya.md": "# Kampanya planı\n\nKasım indirimi için e-posta bülteni ve sosyal medya ilanları hazırlanacak. Bütçe pazarlama ekibinde.\n",
    "ik/izin.md": "# İzin süreci\n\nYıllık izin talepleri yönetici onayından sonra insan kaynaklarına iletiliyor. Form aylık kapanır.\n",
    "bt/yedek.md": "# Yedekleme\n\nSunucu yedekleri her gece alınıyor; geri yükleme denemesi üç ayda bir yapılıyor.\n",
    "finans/fatura.md": "# Fatura onayı\n\nTedarikçi faturaları muhasebe tarafından kontrol edildikten sonra ödeme listesine giriyor.\n",
    "veri/disa/stok.csv": "urun,adet\nPalet,14\nKoli bandı,300\n",
}
for k, m in BELGE.items():
    y = os.path.join(P, k); os.makedirs(os.path.dirname(y), exist_ok=True); open(y, "w", encoding="utf-8").write(m)
ay = os.path.join(T, "ayar.json")
json.dump({"alan": "Deneme", "uygulama": U, "proje": P, "ortak": ORTAK, "veritabani": {"yol": "yok.db"}, "anlam_bos_dk": 0.15}, open(ay, "w"))
os.environ["SUFLOR_AYAR"] = ay; sys.dont_write_bytecode = True
sp = importlib.util.spec_from_file_location("baglam_anlam", os.path.join(KOD, "baglam.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
hatalar = []
def kontrol(ad, kosul, ek=""):
    print(("✓ " if kosul else "✗ ") + ad + (f" — {ek}" if ek and not kosul else ""))
    if not kosul: hatalar.append(ad)
yollar = lambda q: [x[1] for x in m.ara(q, n=3, guncel=False)[0]]
SORU = "Taşımacılık güzergâhlarını kim belirliyor?"  # belgede bu sözcüklerin hiçbiri yok
def sunucu_bekle(sn=60):
    t = time.time()
    while time.time() - t < sn:
        if m.anlam_ara("deneme") is not None: return True
        time.sleep(1)
    return False
c = m.baglan()
try:
    m.tara(c); m.guncelle(c)
    kontrol("gömmeden önce: anlam yok, yalnız sözcük; soru bulunamıyor", m.anlam_ara(SORU) is None and "lojistik/tuna-notlari.md" not in yollar(SORU))
    g = m.gomme(c)
    n_aranir = c.execute("SELECT count(*) FROM parca p JOIN dosya d ON d.yol = p.yol WHERE " + m.gomme_kosul()).fetchone()[0]
    kontrol("gömme: aranabilir parçaların hepsi, dışa aktarım hariç", g["yapilan"] == n_aranir and n_aranir == c.execute("SELECT count(*) FROM parca").fetchone()[0] - c.execute("SELECT count(*) FROM parca WHERE yol LIKE 'veri/disa/%'").fetchone()[0], json.dumps(g))
    kontrol("ikinci tur: eksik 0 (kaldığı yerden)", m.gomme(c)["eksik"] == 0)
    t = time.time(); ilk = yollar(SORU); sure = time.time() - t
    kontrol("sunucu yokken arama beklemedi (< 0,3 sn) ve sunucuyu açtı", sure < 0.3 and sunucu_bekle(), f"{sure:.2f} sn")
    r = yollar(SORU)
    kontrol("başka sözcüklerle sorulan soru bulundu (ilk 3)", "lojistik/tuna-notlari.md" in r, str(r))
    kontrol("sözcük eşleşen soru yine ilk sırada", yollar("yıllık izin talepleri")[:1] == ["ik/izin.md"])
    kontrol("dışa aktarım anlamla da gelmiyor", "veri/disa/stok.csv" not in yollar("depodaki palet ve koli sayısı"))
    # gecikme: §7/6 en çok +50 ms
    def ort(kapali):
        m.ANLAM_KAPALI = kapali; ms = []
        for q in ("fatura ödeme listesi", "sunucu yedekleri", SORU, "kampanya bülteni", "izin onayı") * 4:
            t = time.time(); m.ara(q, n=5, guncel=False); ms.append((time.time() - t) * 1000)
        m.ANLAM_KAPALI = False; ms.sort(); return ms[len(ms) // 2]
    f, a = ort(True), ort(False)
    kontrol("gecikme farkı ≤ 50 ms (ortanca)", a - f <= 50, f"sözcük {f:.1f} ms, birlikte {a:.1f} ms")
    print(f"  ortanca: sözcük {f:.1f} ms · sözcük + anlam {a:.1f} ms")
    # değişen dosya: yalnız yeni parça gömülür, sunucu yeniden yükler
    open(os.path.join(P, "bt/yedek.md"), "a", encoding="utf-8").write("\nFelaket kurtarma tatbikatı İzmir veri merkezinde yapılacak.\n")
    m.guncelle(c); g2 = m.gomme(c)
    kontrol("değişen dosyanın yalnız yeni parçası gömüldü", g2["yapilan"] == c.execute("SELECT count(*) FROM parca WHERE yol='bt/yedek.md'").fetchone()[0], json.dumps(g2))
    t = time.time()
    while "bt/yedek.md" not in yollar("afet senaryosu provası nerede") and time.time() - t < 12: time.sleep(0.5)  # sunucu 5 sn'de bir arka planda yükler
    kontrol("sunucu yeni gömmeyi arka planda yükledi (≤ 12 sn)", "bt/yedek.md" in yollar("afet senaryosu provası nerede"), str(yollar("afet senaryosu provası nerede")))
    json.dump({"meeting": {"title": "Deneme"}}, open(os.path.join(U, "canli", "heartbeat.json"), "w"))
    open(os.path.join(P, "ik/izin.md"), "a", encoding="utf-8").write("\nMazeret izni için belge gerekir.\n"); m.guncelle(c)
    g3 = m.gomme(c); os.remove(os.path.join(U, "canli", "heartbeat.json"))
    kontrol("toplantıda gömme başlamadı", g3["yapilan"] == 0 and g3["durdu"] == "toplantı", json.dumps(g3))
    m.ANLAM_KAPALI = True
    kontrol("ayar anlam_arama: false → yalnız sözcük", m.anlam_ara(SORU) is None and "lojistik/tuna-notlari.md" not in yollar(SORU))
    m.ANLAM_KAPALI = False
    t = time.time()
    while os.path.exists(m.ANLAM_SOKET) and time.time() - t < 40: time.sleep(1)
    kontrol("sunucu boşta kapandı (soket kalktı)", not os.path.exists(m.ANLAM_SOKET))
finally:
    subprocess.run(["pkill", "-f", f"gomme-isci.py --sunucu --db {m.DB}"], capture_output=True)
    c.close(); shutil.rmtree(T, ignore_errors=True)
print(f"anlam: {len(hatalar)} sorun" if hatalar else "anlam: ✓ hepsi geçti")
sys.exit(1 if hatalar else 0)
