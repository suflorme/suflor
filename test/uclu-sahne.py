#!/usr/bin/env python3
# Üçlü sohbet sahne kipi (aktarici/uclu-sahne.py): söz türü planı (dağılım, kısa tepki oranı, devrik/ima, soruya cevap, araya → devam, takılma → bozulma → barışma),
# satır ayırma, satır düzeltme (yinelenen tepki ve açılış, hitap, uzunluk), Claude'a giden mesaj, okuyucu (akarken okuma, kesme, kullanıcı konuşunca durma, araya
# tepkisinin öncekinin sonuna binmesi ve kendi ses süzgecine yazılması), söz alma kararı (üzgün sözde, toplantıda, ayar kapalıyken sahne yok). Nötr kişilik adları.
#   PYTHONDONTWRITEBYTECODE=1 python3 test/uclu-sahne.py
import collections, datetime, json, os, random, re, sys, tempfile, threading, time
sys.dont_write_bytecode = True
KOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); T = tempfile.mkdtemp(prefix="sahne-"); hata = []
def ok(ad, k, ek=None): print(("✓ " if k else "✗ ") + ad + ("" if k or ek is None else f" — {ek}")); hata.append(not k)
ka, kb = os.path.join(T, "atlas.md"), os.path.join(T, "matlas.md")
open(ka, "w", encoding="utf-8").write("---\nad: ATLAS\nhitap: ATLAS, Atlas\nuclu_ad: Atti\nuclu_takilma: Atti Hanım\nuclu_hitap: sen\n---\n## Kişilik: ATLAS\nSiz dersin.\n")
open(kb, "w", encoding="utf-8").write("---\nad: MATLAS\nhitap: MATLAS, Matlas\nuclu_ad: Mati\nhitap_bicimi: sen\n---\n## Kişilik: MATLAS\nSen dersin.\n")
LOG = []; SES = []; KENDI = []; POP = []
class W:
    def __init__(s): s.yaz = []
    def write(s, x): s.yaz.append(json.loads(x)["message"]["content"])
    def flush(s): pass
CAL = {"bit": 0.0}
def seslendir(m, kuyruk=False, k=None, cal=None, **_):
    SES.append((ns["_KSEC"].get("ad"), m, time.time())); CAL["bit"] = max(CAL["bit"], time.time()) + 0.012 * len(m)
    if cal: cal(time.time())
    return True
class P:
    def __init__(s, a, **k): POP.append((a, time.time()))
    def poll(s): return 0
    def terminate(s): pass
class SP: Popen = P; DEVNULL = None
ns = {"re": re, "os": os, "json": json, "time": time, "collections": collections, "threading": threading, "datetime": datetime, "random": random, "subprocess": SP,
      "print": lambda *a, **k: LOG.append(" ".join(map(str, a))), "_t": lambda a, b: a, "ARAYUZ_DILI": "tr", "BASE": T,
      "AYAR": {"kisilik": ka, "kisilik_toplanti_disi": kb, "ad": "Deniz T", "uclu_sohbet": True, "uygulama": T}, "TOP": [False]}
ns["toplanti_var"] = lambda: ns["TOP"][0]
exec(open(os.path.join(KOD, "aktarici", "kisilik.py"), encoding="utf-8").read(), ns)
exec(open(os.path.join(KOD, "aktarici", "uclu-sahne.py"), encoding="utf-8").read(), ns)
ns.update(_KS={"tur": None, "w": W()}, KONUS={"cevap": ""}, konus_canli=lambda: True, ses_caliyor=lambda: time.time() < CAL["bit"], LOCK=threading.Lock(),
          write=lambda l: None, ses_durdur=lambda: None, konus_kapat=lambda *a, **k: None, seslendir=seslendir, etiket_sil=lambda m: m, SOHBET={"acik": True, "biriken": None},
          kendi_ses_kaydet=lambda m, a, b: KENDI.append((m, a, b)), sohbet_kapat=lambda *a, **k: None)
ns["UCLU_CANLAN_SN"] = 1e9
U = ns["_UCLU"]; S = ns["_SAHNE"]; A, B = "ATLAS", "MATLAS"
def sifirla():
    U["akis"].clear(); U["son"].clear(); U["dagilim"].clear(); U["kul_soru"].clear(); S["tepki_son"].clear(); S["onay_son"].clear()
    U.update(sayi=0, hamle=[], nesil=U["nesil"] + 1, canlan=0, hedef=3); SES.clear(); LOG.clear(); KENDI.clear(); POP.clear(); ns["_KS"]["tur"] = None; CAL["bit"] = 0.0
# 1) plan
rng = random.Random(7); planlar = [ns["sahne_plan"](A, rng.choice((3, 4, 5, 6, 7)), rng=rng) for _ in range(400)]
sat = [p for pl in planlar for p in pl]; tur = collections.Counter(p["tur"] for p in sat)
ok(f"plan: kısa tepki payı %20–45 (%{100 * tur['tepki'] // len(sat)}), uzun en çok %12 (%{100 * tur['uzun'] // len(sat)})", 0.20 <= tur["tepki"] / len(sat) <= 0.45 and tur["uzun"] / len(sat) <= 0.12)
ok("plan: sahnede en çok bir uzun söz", all(sum(p["tur"] == "uzun" for p in pl) <= 1 for pl in planlar))
ok("plan: art arda iki tepki yok", all(not (x["tur"] == y["tur"] == "tepki") for pl in planlar for x, y in zip(pl, pl[1:])))
ok("plan: son satır kullanıcıya soru", all(pl[-1]["kalip"] == "kullanici" for pl in planlar))
ok("plan: her sahnede devrik ya da ima", all(any(p["kalip"] in ("devrik", "ima") or p.get("devrik") for p in pl) for pl in planlar if len(pl) >= 4))
ok("plan: her sahnede (≥ 4 satır) en az bir kısa tepki", all(any(p["tur"] == "tepki" for p in pl[:-1]) for pl in planlar if len(pl) >= 4))
ok("plan: soruya araya tepkisi yok, soruya cevap gelir", all(not y["araya"] and (y["kalip"] in ("cevap", "kullanici") or y is pl[-1]) for pl in planlar for x, y in zip(pl, pl[1:]) if x["kalip"] == "soru"))
ar = [(pl, i) for pl in planlar for i, p in enumerate(pl) if p["araya"]]
ok(f"plan: araya tepkisi var ({len(ar)}) ve sonrasında sözü kesilen 'devam' eder", len(ar) > 20 and all(pl[i + 1]["ad"] == pl[i - 1]["ad"] and pl[i + 1]["kalip"] == "devam" for pl, i in ar if i + 1 < len(pl) - 1))
ok("plan: araya yalnız orta/uzun sözün ardından, öbüründen", all(pl[i - 1]["tur"] in ("orta", "uzun") and pl[i - 1]["ad"] != pl[i]["ad"] for pl, i in ar))
tk = [(pl, i) for pl in planlar for i, p in enumerate(pl) if p["kalip"] == "takil" and i + 1 < len(pl) - 1]
ok(f"plan: takılmanın ardından bozulma ({len(tk)})", tk and all(pl[i + 1]["kalip"] == "bozul" for pl, i in tk))
ok("plan: kalıp çeşitliliği (devrik, ima, takil, guldur, itiraz, soru, onay hepsi görülür)", {"devrik", "ima", "takil", "guldur", "itiraz", "soru", "onay", "baris"} <= {p["kalip"] for p in sat})
ok("plan: sözlerin bir kısmı kısa tepkiyle açılır", 0.1 <= sum(p.get("acis", False) for p in sat) / len(sat) <= 0.4)
cp = ns["sahne_plan"](A, 3, son="kullanici", ilk="canlan"); ok("plan: canlan kipi ilk satırda", cp[0]["kalip"] == "canlan" and cp[0]["ad"] == A)
# 2) satır ayırma
s = ns["sahne_ayir"]("**ATLAS:** Hadi ya!\nMati: Valla öyle, dün de\nböyle oldu.\n3. MATLAS: PAS\nAtti (gülerek): Bak sen.\nnot: açıklama")
ok("ayırma: etiket, takma ad, kalın yazı, numara, PAS, devam satırı", s == [("ATLAS", "Hadi ya!"), ("MATLAS", "Valla öyle, dün de böyle oldu."), ("ATLAS", "Bak sen. not: açıklama")], s)
# 3) düzeltme
sifirla(); S["tepki_son"].extend(["Hadi ya!", "Evet evet."])
c = ns["sahne_duzelt"](A, "Hadi ya!", {"tur": "tepki", "kalip": "tepki"}); ok(f"düzeltme: yinelenen kısa tepki başkasıyla değişti («{c}»)", c and ns["_sahne_n"](c) != "hadi ya" and not c.endswith("?"))
c = ns["sahne_duzelt"](A, "Evet evet, bu iş böyle olmaz ki.", {"tur": "kisa", "kalip": "yeni"}); ok(f"düzeltme: yinelenen açılış değişti («{c}»)", c and not c.lower().startswith("evet evet") and "bu iş böyle olmaz ki" in c)
c = ns["sahne_duzelt"](A, "Deniz Bey, bu hafta sonu ne yapıyorsun?", {"tur": "kisa", "kalip": "kullanici"}); ok("düzeltme: üçlüde «Deniz Bey» → «Deniz»", c.startswith("Deniz,") and "Bey" not in c, c)
c = ns["sahne_duzelt"](B, "Atti Hanım, bunu biliyordun.", {"tur": "kisa", "kalip": "takil"}, takilma=False); ok("düzeltme: izinsiz takılma adı takma ada döner", "Atti Hanım" not in c and "Atti" in c, c)
uz = "Bu çok uzun bir söz. " + "Ve devam ediyor, bitmiyor da. " * 8
c = ns["sahne_duzelt"](A, uz, {"tur": "kisa", "kalip": "yeni"}); ok(f"düzeltme: kısa söz sınırı ({len(c)} kar)", len(c) <= ns["SAHNE_SINIR"]["kisa"] + 10)
# 4) mesaj
sifirla(); S["tepki_son"].extend(["Hmm.", "Bak sen."]); U["kul_soru"].append("Deniz, sen ne dersin?")
pl = [{"ad": A, "tur": "tepki", "kalip": "tepki", "araya": False}, {"ad": B, "tur": "orta", "kalip": "devrik", "araya": False, "acis": True},
      {"ad": A, "tur": "tepki", "kalip": "onay", "araya": True}, {"ad": B, "tur": "kisa", "kalip": "kullanici", "araya": False}]
m = ns["sahne_mesaj"]({"kisi": B}, pl)
ok("mesaj: dört satır planı, AD: söz biçimi, iç not ve sahne işareti", all(f"{i}. " in m for i in range(1, 5)) and "«AD: söz»" in m and m.rstrip().endswith("[Bu sahneyi ATLAS ile MATLAS birlikte konuşuyor]"))
ok("mesaj: devrik ve araya tarifi, son sorular kalıbı, uydurma yasağı", "devrik cümle" in m and "araya giren tek tepki" in m and "Deniz, sen ne dersin?" in m and "uydurma" in m and "PAS" in m)
ok("mesaj: yakında kullanılan tepki örnek verilmez", "Hmm." not in m.split("[Satırlar:")[1] and "Bak sen." not in m.split("[Satırlar:")[1])
ok("mesaj: üçlü hitap (Deniz Bey yok)", "«Deniz Bey» yok" in m)
# 5) okuyucu — satırlar akarken okunur
def sahne(metin_parca, plan, ara=0.15, kes=None, biriken=None):
    sifirla(); tur = {"kaynak": "uclu", "kisi": A, "metin": "", "sahne": {"plan": plan, "bitti": False, "ev": threading.Event()},
                      "uclu": {"nesil": U["nesil"], "ksec": {"ad": None, "t": 0.0}, "t0": time.time()}}
    th = threading.Thread(target=ns["_sahne_okuyucu"], args=(tur,), daemon=True); th.start(); t0 = time.time(); ilk = None
    for i, x in enumerate(metin_parca):
        time.sleep(ara); tur["metin"] += x
        if kes is not None and i == kes: ns["uclu_kes"]("deneme", sustur=True)
        if biriken is not None and i == biriken: ns["SOHBET"]["biriken"] = b""
        if SES and ilk is None: ilk = time.time() - t0
    time.sleep(ara); tur["sahne"]["bitti"] = True; tur["sahne"]["ev"].wait(8); ns["SOHBET"]["biriken"] = None
    if SES and ilk is None: ilk = time.time() - t0
    return tur, ilk
pl5 = ns["sahne_plan"](A, 5, rng=random.Random(3))
parca = ["ATLAS: Bugün hava çok güzeldi, dışarı çıktım biraz yürüdüm.\n", "MATLAS: Hadi ya!\n", "ATLAS: Valla, sahile kadar indim.\n", "MATLAS: Ben de gelirdim ama uyuyakaldım.\n", "ATLAS: Deniz, sen bugün dışarı çıktın mı?\n"]
tur, ilk = sahne(parca, pl5)
ok(f"okuyucu: beş satır, sırayla ve kendi kişiliğiyle okundu ({[a for a, _, _ in SES]})", [a for a, _, _ in SES] == [A, B, A, B, A] and SES[1][1] == "Hadi ya!")
ok(f"okuyucu: ilk satır sahne bitmeden okundu ({ilk:.2f} sn; metin {0.15 * 6:.2f} sn sürdü)", ilk is not None and ilk < 0.5)
ok("okuyucu: pano cevabına ve akışa eklendi, söz sayacı arttı", "MATLAS: Hadi ya!" in ns["KONUS"]["cevap"] and U["sayi"] == 5 and [x["ad"] for x in U["akis"]][-5:] == [A, B, A, B, A])
ok("okuyucu: son satır kullanıcıya soru → sıra kullanıcıda", U.get("son_donen") == A and "Deniz, sen bugün dışarı çıktın mı?" in list(U["kul_soru"]) and any("sıra kullanıcıda" in l for l in LOG))
tur, _ = sahne(parca, pl5, ara=0.25, kes=1)
ok(f"okuyucu: 'dur' (uclu_kes) sonrası kalan satırlar okunmadı ({len(SES)} okundu)", 1 <= len(SES) <= 2 and any("kalan satırlar okunmadı" in l or "söze girdi" in l for l in LOG))
tur, _ = sahne(parca, pl5, ara=0.25, biriken=1)
ok(f"okuyucu: kullanıcı konuşmaya başlayınca durdu ({len(SES)} okundu)", 1 <= len(SES) <= 2)
tur, _ = sahne(["ATLAS: PAS\n", "MATLAS: PAS\n"], pl5)
ok("okuyucu: PAS sahnesi hiç okunmaz, sıra değişmez", not SES and U["sayi"] == 0)
# araya: öbürü konuşurken klip öncekinin sonuna biner, kendi ses süzgecine yazılır
klip = os.path.join(T, "hi-hi.wav"); open(klip, "wb").write(b"RIFF")
ns["sahne_klip"] = lambda ad, metin: klip if ns["_sahne_n"](metin) in ("hı hı", "evet evet") else None
uzun = "ATLAS: Dün akşam eve dönerken bir sokak müzisyeni gördüm, öyle güzel çalıyordu ki durup yarım saat dinledim, saatin nasıl geçtiğini anlamadım.\n"
pla = [{"ad": A, "tur": "uzun", "kalip": "yeni", "araya": False}, {"ad": B, "tur": "tepki", "kalip": "tepki", "araya": True},
       {"ad": A, "tur": "kisa", "kalip": "devam", "araya": False}, {"ad": B, "tur": "kisa", "kalip": "kullanici", "araya": False}]
ns["SAHNE_KAR_SN"] = 1 / 0.012  # deneme çalıcısının hızı
tur, _ = sahne([uzun, "MATLAS: Hı hı.\n", "ATLAS: İşte, sonra da şapkasına biraz para bıraktım.\n", "MATLAS: Deniz, sen sokak müziği sever misin?\n"], pla, ara=0.05)
time.sleep(0.3); t_a = SES[0][2] if SES else 0; bit_a = t_a + 0.012 * len(uzun.split(": ", 1)[1].strip())
ok(f"araya: klip ayrı çalıcıda, öncekinin sözü sürerken ({[round(t - t_a, 2) for _, t in POP]} sn; söz {bit_a - t_a:.2f} sn)", len(POP) == 1 and t_a + 0.4 * (bit_a - t_a) < POP[0][1] < bit_a and POP[0][0][:2] == ["/usr/bin/afplay", "-v"])
ok("araya: klip kuyruğa girmedi, sonraki satırlar sırayla", [m for _, m, _ in SES] == [uzun.split(": ", 1)[1].strip(), "İşte, sonra da şapkasına biraz para bıraktım.", "Deniz, sen sokak müziği sever misin?"])
ok("araya: kendi ses süzgecine yazıldı ve akışa girdi", KENDI and KENDI[0][0] == "Hı hı." and any(x["metin"] == "Hı hı." for x in U["akis"]))
# 6) söz alma kararı ve sahne turu
sifirla(); w = ns["_KS"]["w"]; w.yaz.clear()
ana = {"kaynak": "sohbet", "kisi": A, "soru": "Bu akşam ne yapalım?", "sesli": True}
ok("tetik: kullanıcıya cevaptan sonra sahne turu başladı (öbürü ilk konuşan)", ns["sahne_tetik"](ana) and ns["_KS"]["tur"]["sahne"]["plan"][0]["ad"] == B and "[Bu sahneyi" in w.yaz[-1])
t = ns["_KS"]["tur"]; t["metin"] = "MATLAS: Hadi ya!\n"; ns["sahne_tetik"](t); ok("tetik: sahnenin sonucu gelince yeni tur açılmaz, okuyucu bitirir", t["sahne"]["bitti"])
t["sahne"]["ev"].wait(3); ns["_KS"]["tur"] = None
ok("tetik: üzgün sözde sahne yok", not ns["sahne_tetik"](dict(ana, soru="Bugün çok yorgunum, moralim bozuk.")) and ns["_KS"]["tur"] is None)
ok("tetik: cevap onay sorusuyla bitince (Göndereyim mi?) öbürü araya girmez", not ns["sahne_tetik"](dict(ana, soru="Yarın için bir hatırlatma metni yaz", metin="Yazdım: yarın onda arama. Kaydedeyim mi?")) and ns["_KS"]["tur"] is None)
ok("tetik: seçenekli sohbet sorusu engellenmez", ns["uclu_talimat"](dict(ana, metin="Bence yürüyüş. Sen deniz mi seçersin, orman mı?")) is False)
ns["TOP"][0] = True; ok("tetik: toplantıda sahne kipi kapalı", not ns["sahne_acik"]()); ns["TOP"][0] = False
ns["AYAR"]["uclu_sahne"] = False; ok("ayar uclu_sahne: false → sahne kipi kapalı", not ns["sahne_acik"]()); ns["AYAR"].pop("uclu_sahne")
ok("ana not: sahne kipinde kullanıcıya kısa cevap", "kısa konuş" in ns["sahne_ana_notu"]())
# 7) v0.126.1 — kullanıcının ilk sahne denemesi (24 Ekim)
v = ns["uclu_veda"]
ok("veda: teşekkür + ikinize, test oturumu, görüşmek üzere, sitem", all(v(x) for x in ("Teşekkür ederim ikinize de, bu bir test oturumuydu, görüşmek üzere.", "İyi geceler demiştim, hâlâ konuşuyorsunuz.", "Tamam, yeter bu kadar.")))
ok("veda değil: sözün ortasındaki 'demiştim', teşekkürlü istek", not any(v(x) for x in ("Ben sana demiştim, kahvaltı önemli.", "Bir film önerin, teşekkürler.")))
sifirla(); t0 = time.time()
U["akis"].extend([{"t": t0 - 30, "ad": None, "metin": "Kahvaltı mı akşam yemeği mi daha önemli?"}, {"t": t0 - 29, "ad": A, "metin": "Kahvaltı bence, simit ve çayla."},
                  {"t": t0 - 25, "ad": B, "metin": "Kahvaltı tartışılmaz, simit şart."}, {"t": t0 - 5, "ad": None, "metin": "Kahvaltı sorusunu geçtim. Matlas, dün akşam ne yaptım?"},
                  {"t": t0 - 4, "ad": B, "metin": "Dün akşam film izledin galiba."}])
sz, gc, es = ns["sahne_konu"]()
ok(f"konu geçişi: 'geçtim' işareti tanındı, eski konu sözcükleri yasak ({es})", gc and sz.startswith("Kahvaltı sorusunu geçtim") and "simit" in es and "kahvaltı" in es and "matlas" not in es)
m = ns["sahne_mesaj"]({"kisi": B}, ns["sahne_plan"](A, 3, rng=random.Random(1)))
ok("konu geçişi: mesajda son söz esas, önceki konu kapandı, eski konuşma gitmedi", "son sözünden açılır" in m and "konuyu değiştirdi" in m and "Kahvaltı bence, simit" not in m)
U["akis"].append({"t": t0, "ad": None, "metin": "Peki bu akşam ne yiyelim?"}); sz, gc, _ = ns["sahne_konu"]()
ok("işaretsiz yeni söz: konu değişmedi sayılır ama son söz esas", not gc and sz == "Peki bu akşam ne yiyelim?" and "son sözünden açılır" in ns["sahne_mesaj"]({"kisi": B}, ns["sahne_plan"](A, 3)))
pl3 = [ns["sahne_plan"](A, random.Random(i).choice((3, 3, 4)), rng=random.Random(i)) for i in range(50)]; ok("sahne uzunluğu: varsayılan 3–4 satır", all(3 <= len(p) <= 4 for p in pl3))
ns["SOHBET"]["acik"] = True
def kapat_sonra(): time.sleep(0.35); ns["SOHBET"]["acik"] = False
sifirla(); tur = {"kaynak": "uclu", "kisi": A, "metin": "", "sahne": {"plan": pl5, "bitti": False, "ev": threading.Event()},
                  "uclu": {"nesil": U["nesil"], "ksec": {"ad": None, "t": 0.0}, "t0": time.time(), "sohbet_acik": True}}
threading.Thread(target=ns["_sahne_okuyucu"], args=(tur,), daemon=True).start(); threading.Thread(target=kapat_sonra, daemon=True).start()
for x in parca: time.sleep(0.25); tur["metin"] += x
tur["sahne"]["bitti"] = True; tur["sahne"]["ev"].wait(5)
ok(f"sohbet kapanınca sahne durdu ({len(SES)} satır okundu), sürdürme tetiklenmedi", 1 <= len(SES) <= 2 and not any("sıra kullanıcıda" in l for l in LOG))
ok("sohbet kapalıyken canlan sahnesi başlamaz", ns["sahne_tetik"]({"kisi": A, "kaynak": "uclu", "uclu": {"sohbet_acik": True}}, canlan=True) is False and ns["_KS"]["tur"] is None)
ns["SOHBET"]["acik"] = True; ns["SAHNE_TAVAN_SN"] = 0.05
tur, _ = sahne(parca, pl5, ara=0.05)
ok(f"süre tavanı: aradaki satırlar atlandı, kullanıcıya dönen son satır okundu ({[m for _, m, _ in SES]})", len(SES) < 5 and SES[-1][1] == "Deniz, sen bugün dışarı çıktın mı?")
ns["SAHNE_TAVAN_SN"] = 20.0
print("üçlü sahne:", "✓ hepsi geçti" if not any(hata) else f"✗ {sum(hata)} kaldı"); sys.exit(1 if any(hata) else 0)
