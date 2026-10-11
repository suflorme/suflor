#!/usr/bin/env python3
# Suflor.me — toplantı yapısı (v0.27.0, Faz 5): karar grafı + zihin haritası. toplanti-claude.py yapi/graf komutları bunu içe aktarır.
# Toplantı sonunda Claude özetle birlikte yapı dosyasını yazar (<özet>.yapi.json; biçim YAPI_ORNEK). Buradan:
#  - karar grafı: canli/karar-grafi.sqlite (yalnız bu Mac; başka kayıt sistemine yazılmaz) — kişi → karar/iddia/iş/söz → tarih → kaynak (toplantı, saat).
#    Hazırlıkta ve toplantıda (KATILIMCI olayı) kişinin geçmiş iddiaları ve açık işleri; Claude çelişkiyi aramadan graftan görür.
#  - zihin haritası: <özet>-zihin-haritasi.html (tek dosya, çevrimdışı; NotebookLM benzeri: merkezde toplantı, dallar gündem maddeleri,
#    altında karar · iş · açık soru · sayı · iddia; düğüm açılır/kapanır, yaprağa dokununca alıntı ve saat; "Resim olarak indir" PNG).
# Python 3.9, yalnız standart kütüphane. Metinler veridir; HTML'e kaçışlı (JSON) gömülür.
import datetime, html, json, os, re, sqlite3
TURLER = {"karar": "Karar", "is": "İş", "soru": "Açık soru", "sayi": "Sayı", "iddia": "İddia", "soz": "Söz"}
YAPI_ORNEK = {"baslik": "Ayşe — bütçe", "tarih": "2026-10-11", "maddeler": [
    {"baslik": "Bütçe", "durum": "konuşuldu", "ogeler": [
        {"tur": "karar", "metin": "Bütçe 120 bin olarak kalıyor", "kim": "Ayşe Yılmaz", "saat": "10:12:30", "alinti": "120'de kalalım"},
        {"tur": "is", "metin": "Teklifi revize et", "sahip": "Bora Kaya", "tarih": "2026-10-17", "saat": "10:15:02"},
        {"tur": "soru", "metin": "KDV dahil mi?", "kim": "Ali K"}, {"tur": "iddia", "metin": "Geçen yıl 95 bin harcandı", "kim": "Ayşe Yılmaz", "saat": "10:11:00"}]}]}
def kucuk(t): return str(t).replace("İ", "i").replace("I", "ı").lower()
def oku(yol):
    v = json.load(open(yol, encoding="utf-8"))
    if not isinstance(v, dict) or not isinstance(v.get("maddeler"), list): raise ValueError("yapı dosyası: {\"baslik\", \"tarih\", \"maddeler\": [...]} bekleniyor")
    for m in v["maddeler"]:
        m["ogeler"] = [o for o in (m.get("ogeler") or []) if isinstance(o, dict) and o.get("tur") in TURLER and str(o.get("metin") or "").strip()]
    return v
# --- karar grafı -----------------------------------------------------------------------------------------------------
def _db(dizin):
    yol = os.path.join(dizin, "karar-grafi.sqlite"); yeni = not os.path.exists(yol)
    c = sqlite3.connect(yol)
    c.execute("""CREATE TABLE IF NOT EXISTS kayit (id INTEGER PRIMARY KEY, toplanti TEXT, baslik TEXT, tarih TEXT, madde TEXT, tur TEXT,
                 kim TEXT, sahip TEXT, metin TEXT, son_tarih TEXT, saat TEXT, alinti TEXT, durum TEXT DEFAULT 'acik', eklendi TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS kayit_kim ON kayit (kim)"); c.execute("CREATE INDEX IF NOT EXISTS kayit_sahip ON kayit (sahip)")
    if yeni: os.chmod(yol, 0o600)
    return c
def graf_yaz(dizin, v, toplanti):
    # aynı toplantı yeniden yazılırsa eski kayıtları yerine geçer
    c = _db(dizin); n = 0
    with c:
        c.execute("DELETE FROM kayit WHERE toplanti = ?", (toplanti,))
        for m in v["maddeler"]:
            for o in m["ogeler"]:
                c.execute("INSERT INTO kayit (toplanti, baslik, tarih, madde, tur, kim, sahip, metin, son_tarih, saat, alinti, eklendi) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (toplanti, str(v.get("baslik") or "")[:200], str(v.get("tarih") or "")[:10], str(m.get("baslik") or "")[:200], o["tur"],
                           str(o.get("kim") or "")[:80] or None, str(o.get("sahip") or "")[:80] or None, str(o["metin"])[:600], str(o.get("tarih") or "")[:20] or None,
                           str(o.get("saat") or "")[:8] or None, str(o.get("alinti") or "")[:300] or None, datetime.datetime.now().isoformat(timespec="seconds")))
                n += 1
    c.close(); return n
def _ilk(ad): return (str(ad or "").split() or [""])[0].casefold()
def graf_kisi(dizin, kim, n=5, haric=None):
    # kişinin (ad ya da ilk adı) son iddia/karar/sözleri ve sahibi olduğu açık işler — yeni toplantıdan önce
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")) or not kim: return []
    c = _db(dizin); ilk = _ilk(kim)
    rs = c.execute("SELECT tarih, tur, kim, sahip, metin, son_tarih, baslik, saat, toplanti FROM kayit WHERE durum = 'acik' ORDER BY tarih DESC, id DESC LIMIT 2000").fetchall()
    c.close()
    out = [r for r in rs if r[8] != haric and (_ilk(r[2]) == ilk or _ilk(r[3]) == ilk) and r[1] in ("iddia", "karar", "is", "soz", "sayi")]
    return out[:n]
def graf_satir(r):
    tarih, tur, kim, sahip, metin, son, baslik, saat = r[:8]
    return f"{tarih} {kucuk(TURLER.get(tur, tur))}: {metin}" + (f" (sahip {sahip}" + (f", {son}" if son else "") + ")" if tur == "is" and sahip else "") + f" — {baslik}"
def graf_liste(dizin, kim=None, n=20):
    if not os.path.exists(os.path.join(dizin, "karar-grafi.sqlite")): return []
    if kim: return graf_kisi(dizin, kim, n)
    c = _db(dizin); rs = c.execute("SELECT tarih, tur, kim, sahip, metin, son_tarih, baslik, saat, toplanti FROM kayit ORDER BY tarih DESC, id DESC LIMIT ?", (n,)).fetchall(); c.close()
    return rs
def graf_sil(dizin, toplanti=None, hepsi=False):
    yol = os.path.join(dizin, "karar-grafi.sqlite")
    if not os.path.exists(yol): return 0
    if hepsi: os.remove(yol); return -1
    c = _db(dizin)
    with c: n = c.execute("DELETE FROM kayit WHERE toplanti = ?", (toplanti,)).rowcount
    c.close(); return n
# --- zihin haritası --------------------------------------------------------------------------------------------------
def harita_veri(v):
    kok = {"ad": str(v.get("baslik") or "Toplantı"), "alt": [], "tur": "kok", "not": str(v.get("tarih") or "")}
    for m in v["maddeler"]:
        d = {"ad": str(m.get("baslik") or "Gündem dışı"), "tur": "madde", "not": str(m.get("durum") or ""), "alt": []}
        for t in TURLER:
            os_ = [o for o in m["ogeler"] if o["tur"] == t]
            if not os_: continue
            g = {"ad": TURLER[t] + ("lar" if t in ("karar", "sayi", "iddia") and len(os_) > 1 else "ler" if t == "is" and len(os_) > 1 else ""), "tur": t, "alt": []}
            if t == "soru" and len(os_) > 1: g["ad"] = "Açık sorular"
            for o in os_:
                kim = o.get("sahip") if t == "is" else o.get("kim")
                g["alt"].append({"ad": str(o["metin"]), "tur": t, "kim": str(kim or ""), "saat": str(o.get("saat") or ""), "tarih": str(o.get("tarih") or ""),
                                 "alinti": str(o.get("alinti") or "")})
            d["alt"].append(g)
        kok["alt"].append(d)
    return kok
def harita_html(v):
    veri = json.dumps(harita_veri(v), ensure_ascii=False).replace("</", "<\\/")
    return HARITA.replace("__BASLIK__", html.escape(str(v.get("baslik") or "Toplantı"))).replace("__VERI__", veri)
HARITA = r"""<!doctype html><html lang=tr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>__BASLIK__ — zihin haritası</title>
<style>
:root{--bg:#f6f4ee;--s1:#fffdf8;--tx:#1d211e;--t2:#5b625d;--bd:rgba(29,33,30,.14);--cizgi:rgba(29,33,30,.28);
--kok:#175e46;--madde:#3c4a43;--karar:#1f7a4f;--is:#a86b12;--soru:#6b4f9e;--sayi:#1f6f78;--iddia:#b3412e;--soz:#8a6420}
@media (prefers-color-scheme:dark){:root{--bg:#121614;--s1:#1a201d;--tx:#e8ebe6;--t2:#a5ada7;--bd:rgba(232,235,230,.14);--cizgi:rgba(232,235,230,.3);
--kok:#2a8a66;--madde:#9fb1a7;--karar:#47b07c;--is:#d9a03c;--soru:#b39ddb;--sayi:#5fb7c0;--iddia:#e0705c;--soz:#e0bb6c}}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}
header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 16px;border-bottom:1px solid var(--bd)}
header h1{font-size:16px;font-weight:600;margin:0 auto 0 0}header button{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--bd);border-radius:7px;background:var(--s1);color:var(--tx);cursor:pointer}
header button:hover{border-color:var(--cizgi)}#alan{overflow:auto;height:calc(100% - 56px);padding:16px}svg{display:block}
.d rect{fill:var(--s1);stroke:var(--bd);stroke-width:1}.d rect.ser{stroke:none}.d text{fill:var(--tx);font-size:13px;dominant-baseline:middle}.d{cursor:pointer}
.d .say{fill:var(--t2);font-size:11px}.d:hover rect{stroke:var(--cizgi)}path.c{fill:none;stroke:var(--cizgi);stroke-width:1.4}
#ayrinti{position:fixed;right:16px;bottom:16px;max-width:min(420px,calc(100% - 32px));background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;box-shadow:0 6px 24px rgba(0,0,0,.12);display:none}
#ayrinti b{display:block;margin-bottom:4px}#ayrinti .k{color:var(--t2);font-size:12.5px}#ayrinti q{display:block;margin-top:6px;font-style:italic}
#ayrinti button{float:right;border:0;background:none;color:var(--t2);font-size:16px;cursor:pointer}
</style>
<header><h1>__BASLIK__</h1><button id=ac>Hepsini aç</button><button id=kapa>Hepsini kapat</button><button id=png>Resim olarak indir</button></header>
<div id=alan><svg id=s xmlns="http://www.w3.org/2000/svg"></svg></div><div id=ayrinti role=dialog aria-live=polite></div>
<script>
const V=__VERI__;const RENK=t=>getComputedStyle(document.documentElement).getPropertyValue('--'+(t==='kok'?'kok':t==='madde'?'madde':t)).trim()||'#888';
const S=document.getElementById('s'),NS='http://www.w3.org/2000/svg',olc=document.createElement('canvas').getContext('2d');olc.font='13px -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif';
let sira=0,yaprak=0;(function say(d){if(!(d.alt||[]).length)yaprak++;(d.alt||[]).forEach(say)})(V);
(function kimlik(d,der){d.id=sira++;d.der=der;d.acik=yaprak<=30||der<2;(d.alt||[]).forEach(x=>kimlik(x,der+1))})(V,0);  // küçük harita tümüyle açık
const KISA=s=>{s=String(s);return s.length>64?s.slice(0,62)+'…':s};
function boy(d){const w=Math.min(380,Math.max(60,olc.measureText(KISA(d.ad)).width+(d.alt&&d.alt.length?46:28)));return{w,h:30}}
const DX=48,DY=10;
function yerles(d,x,y){const b=boy(d);d.x=x;d.w=b.w;d.h=b.h;const c=d.acik?(d.alt||[]):[];if(!c.length){d.y=y;return y+d.h+DY}
let yy=y;c.forEach(k=>{yy=yerles(k,x+d.w+DX,yy)});const ilk=c[0].y,son=c[c.length-1].y;d.y=(ilk+son)/2;return Math.max(yy,d.y+d.h+DY)}
function el(ad,a,ust){const e=document.createElementNS(NS,ad);for(const k in a)e.setAttribute(k,a[k]);if(ust)ust.appendChild(e);return e}
function ciz(){S.innerHTML='';const H=yerles(V,8,8);let W=0;(function g(d){W=Math.max(W,d.x+d.w);if(d.acik)(d.alt||[]).forEach(g)})(V);
S.setAttribute('width',W+16);S.setAttribute('height',H+8);S.setAttribute('viewBox',`0 0 ${W+16} ${H+8}`);
(function g(d){if(!d.acik)return;(d.alt||[]).forEach(k=>{const x1=d.x+d.w,y1=d.y+d.h/2,x2=k.x,y2=k.y+k.h/2,m=(x1+x2)/2;el('path',{class:'c',d:`M${x1} ${y1}C${m} ${y1},${m} ${y2},${x2} ${y2}`},S);g(k)})})(V);
(function g(d){const gr=el('g',{class:'d',transform:`translate(${d.x},${d.y})`,tabindex:0,role:'button','aria-label':d.ad},S);
const r=el('rect',{width:d.w,height:d.h,rx:d.der===0?15:8},gr);const renk=RENK(d.tur);
if(d.der===0){r.style.fill=renk;r.style.stroke=renk}else el('rect',{width:4,height:d.h-10,x:6,y:5,rx:2,class:'ser'},gr).style.fill=renk;
const t=el('text',{x:d.der===0?14:16,y:d.h/2},gr);t.textContent=KISA(d.ad);if(d.der===0)t.style.fill='#fff';
if(d.alt&&d.alt.length){const s=el('text',{class:'say',x:d.w-22,y:d.h/2},gr);s.textContent=d.acik?'‹':String(d.alt.length)+' ›';if(d.der===0)s.style.fill='#fff'}
const tik=()=>{if(d.alt&&d.alt.length){d.acik=!d.acik;ciz()}else goster(d)};gr.onclick=tik;gr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tik()}};
if(d.acik)(d.alt||[]).forEach(g)})(V)}
const A=document.getElementById('ayrinti');const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function goster(d){A.innerHTML=`<button aria-label="Kapat">×</button><b>${esc(d.ad)}</b><div class=k>${[d.kim,d.tarih&&('tarih '+d.tarih),d.saat&&('saat '+d.saat)].filter(Boolean).map(esc).join(' · ')}</div>${d.alinti?'<q>'+esc(d.alinti)+'</q>':''}`;A.style.display='block';A.querySelector('button').onclick=()=>A.style.display='none'}
function hepsi(v){(function g(d){d.acik=v||d.der===0;(d.alt||[]).forEach(g)})(V);ciz()}
document.getElementById('ac').onclick=()=>hepsi(true);document.getElementById('kapa').onclick=()=>hepsi(false);
document.getElementById('png').onclick=()=>{const k=S.cloneNode(true),cs=getComputedStyle(document.body);k.querySelectorAll('.d rect:first-child').forEach(r=>{if(!r.style.fill){r.setAttribute('fill',getComputedStyle(document.documentElement).getPropertyValue('--s1'));r.setAttribute('stroke','rgba(0,0,0,.15)')}});
k.querySelectorAll('text').forEach(t=>{t.setAttribute('font-family','-apple-system,Helvetica Neue,sans-serif');t.setAttribute('font-size',t.classList.contains('say')?'11':'13');t.setAttribute('dominant-baseline','middle');if(!t.style.fill)t.setAttribute('fill',cs.color)});
k.querySelectorAll('path').forEach(p=>{p.setAttribute('fill','none');p.setAttribute('stroke','rgba(120,120,120,.6)');p.setAttribute('stroke-width','1.4')});
const w=+S.getAttribute('width'),h=+S.getAttribute('height'),o=2,img=new Image(),c=document.createElement('canvas');c.width=w*o;c.height=h*o;
img.onload=()=>{const x=c.getContext('2d');x.fillStyle=cs.backgroundColor;x.fillRect(0,0,c.width,c.height);x.scale(o,o);x.drawImage(img,0,0);const a=document.createElement('a');a.download=document.title.replace(/[\\/:*?"<>|]/g,'-')+'.png';a.href=c.toDataURL('image/png');a.click()};
img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(k))};
ciz();
</script></html>"""
