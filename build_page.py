import json, datetime
data = json.load(open('binder.json', encoding='utf-8'))
today = datetime.date.today().strftime('%d %b %Y')
html = r'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Binder Ledger</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--bg:#f5f3ec;--surface:#fbfaf6;--ink:#1c1e22;--muted:#6b6a63;--line:#dcd8cc;--line2:#ece9df;--gold:#c99a2a;--gold-ink:#7a5a12;--up:#2f7d4f;--down:#b5423a;--row-h:#f0ede3;--eur:#2b5f8f}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15171b;--surface:#1d2025;--ink:#ecebe6;--muted:#9a9890;--line:#33363d;--line2:#272a30;--gold:#e0b44a;--gold-ink:#f0cb6a;--up:#5fbf87;--down:#e0736a;--row-h:#23262c;--eur:#7fb2e0}}
:root[data-theme="dark"]{--bg:#15171b;--surface:#1d2025;--ink:#ecebe6;--muted:#9a9890;--line:#33363d;--line2:#272a30;--gold:#e0b44a;--gold-ink:#f0cb6a;--up:#5fbf87;--down:#e0736a;--row-h:#23262c;--eur:#7fb2e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:14px;line-height:1.45}
.wrap{max-width:980px;margin:0 auto;padding:28px 20px 64px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:16px 32px;border-bottom:3px solid var(--gold);padding-bottom:18px}
h1{font-family:"Barlow Condensed",Impact,sans-serif;font-weight:700;font-size:40px;letter-spacing:.01em;margin:0;line-height:1;text-wrap:balance}
.sub{color:var(--muted);margin-top:6px;font-size:13px}
.theme{margin-left:10px;vertical-align:middle;font:inherit;font-size:11px;letter-spacing:.1em;text-transform:uppercase;padding:4px 9px;border:1px solid var(--line);border-radius:3px;background:var(--surface);color:var(--muted);cursor:pointer}
.theme:hover,.theme:focus{color:var(--ink);border-color:var(--gold);outline:none}
.total{text-align:right}
.total .lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.total .val{font-family:"Barlow Condensed",Impact,sans-serif;font-weight:700;font-size:56px;line-height:1;color:var(--gold-ink);font-variant-numeric:tabular-nums}
.total .val small{font-size:26px;font-weight:600;margin-right:4px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin:22px 0 26px;border:1px solid var(--line);border-bottom:0;border-right:0;background:var(--surface)}
.stat{padding:14px 16px;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.stat .k{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:"Barlow Condensed",Impact,sans-serif;font-weight:600;font-size:28px;line-height:1.1;margin-top:4px;font-variant-numeric:tabular-nums}
.stat .v.up{color:var(--up)}.stat .v.down{color:var(--down)}
.stat .n{font-size:12px;color:var(--muted);margin-top:2px}
.controls{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-bottom:10px;font-size:13px}
.controls label{color:var(--muted)}
select,input[type=search]{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:3px}
input[type=search]{min-width:200px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);background:var(--surface)}
table{border-collapse:collapse;width:100%}
caption{text-align:left;padding:10px 12px;font-size:13px;color:var(--muted);border-bottom:1px solid var(--line);background:var(--surface)}
caption b{color:var(--ink);font-weight:600;font-family:"Barlow Condensed",Impact,sans-serif;font-size:16px;letter-spacing:.02em;margin-right:8px}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line2);vertical-align:top}
th,td.num{white-space:nowrap}
td.card,td.set{white-space:normal;overflow-wrap:anywhere}
td.card{min-width:160px;font-weight:500}
td.set{min-width:150px;color:var(--muted);font-size:13px}
th{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--line)}
th.sorted{color:var(--ink)}
th .arr{display:inline-block;width:1em;color:var(--gold)}
td.num,th.num{text-align:right;font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;font-size:13px}
td.eur{color:var(--eur);font-weight:500}
td.chg.up{color:var(--up)}td.chg.down{color:var(--down)}
td.card a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--line)}
td.card a:hover,td.card a:focus{color:var(--eur);border-bottom-color:var(--eur)}
td.lang{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--muted)}
td.set .num{display:block;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;color:var(--ink);opacity:.75;white-space:nowrap}
tr.pagehead td{background:var(--row-h);font-family:"Barlow Condensed",Impact,sans-serif;font-weight:600;font-size:15px;letter-spacing:.02em;padding:6px 12px;border-bottom:1px solid var(--line)}
tr.pagehead td span{color:var(--muted);font-weight:500;font-size:13px;font-family:"IBM Plex Sans",sans-serif;margin-left:10px}
tbody tr:hover td{background:var(--row-h)}
.srch{margin-left:6px;color:var(--muted);text-decoration:none;font-size:13px;border:0}
.srch:hover,.srch:focus{color:var(--eur)}
td.card a.srch{border-bottom:0}
.rh{font-style:normal;color:var(--gold-ink);font-size:10px;letter-spacing:.05em;text-transform:uppercase}
.pend{margin-left:6px;font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:1px 5px;border-radius:3px;border:1px solid var(--muted);color:var(--muted);vertical-align:middle}
.pend.paid{text-transform:none;letter-spacing:0}
.qty{margin-left:6px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--gold-ink);font-weight:600}
.vf{display:inline-block;margin-left:6px;padding:0 5px;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--gold-ink);border:1px solid var(--gold);border-radius:2px;vertical-align:middle}
.addbox{margin:0 0 14px;border:1px solid var(--line);background:var(--surface);font-size:13px}
.addbox summary{cursor:pointer;padding:9px 12px;font-family:"Barlow Condensed",Impact,sans-serif;font-weight:600;font-size:15px;letter-spacing:.02em;list-style:none}
.addbox summary::-webkit-details-marker{display:none}
.addbox summary::before{content:"+";display:inline-block;width:14px;color:var(--gold)}
.addbox[open] summary::before{content:"-"}
.addbox .hint{margin:0 12px 10px;color:var(--muted);font-size:12px;max-width:80ch}
.addgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px 14px;padding:0 12px 10px}
.addgrid label{display:flex;flex-direction:column;gap:3px;color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.addgrid label.chk{flex-direction:row;align-items:center;gap:6px;text-transform:none;letter-spacing:0;font-size:13px;color:var(--ink);align-self:end;padding-bottom:6px}
.addgrid input,.addgrid select{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:3px}
.cmdrow{display:flex;gap:8px;align-items:stretch;margin:0 12px 12px}
.cmdrow code{flex:1;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;padding:8px 10px;background:var(--bg);border:1px solid var(--line);border-radius:3px;overflow-x:auto;white-space:nowrap;color:var(--ink)}
.cmdrow button,.addbox code{font-family:"IBM Plex Mono",ui-monospace,monospace}
.cmdrow button{font-size:12px;padding:0 12px;border:1px solid var(--gold);background:var(--surface);color:var(--gold-ink);border-radius:3px;cursor:pointer}
.cmdrow button:hover{background:var(--row-h)}
.sources{margin-top:28px;max-width:72ch;font-size:13px;color:var(--muted);line-height:1.55}
.sources h2{font-family:"Barlow Condensed",Impact,sans-serif;font-weight:600;font-size:20px;margin:22px 0 8px;letter-spacing:.01em;color:var(--ink)}
.sources p{margin:0 0 8px}
.sources b{color:var(--ink);font-weight:600}
.sources a{color:var(--eur);text-decoration:none;border-bottom:1px dotted var(--line)}
.sources a:hover{border-bottom-color:var(--eur)}
.sources ul{margin:0 0 8px;padding-left:18px}
.sources li{margin-bottom:4px}
select:focus,input:focus,th:focus{outline:2px solid var(--gold);outline-offset:1px}
@media (max-width:760px){.c-lang,.c-avg7{display:none}th,td{padding:7px 8px}body{font-size:13px}}
@media (max-width:640px){h1{font-size:32px}.total .val{font-size:44px}.total{text-align:left;flex-basis:100%}.c-set{display:none}td.card{min-width:0}td.num{font-size:12px}}
</style>
<div class="wrap">
<header>
  <div><h1>Binder Ledger</h1><div class="sub"><span id="sub"></span> <button id="theme" class="theme" type="button" aria-label="Switch colour theme">Dark</button></div></div>
  <div class="total"><div class="lbl">Cardmarket trend, near mint</div><div class="val"><small>€</small><span id="totEur"></span></div></div>
</header>
<div class="stats" id="stats"></div>
<div class="controls">
  <label>Sort <select id="sort"><option value="page">Binder page</option><option value="trend">Cardmarket €</option><option value="chg">Change since Dec 24</option><option value="name">Name</option></select></label>
  <label>Page <select id="pagef"><option value="">All</option></select></label>
  <input type="search" id="q" placeholder="Search card or set">
</div>
<details class="addbox" id="addbox">
<summary>Add or remove a card</summary>
<p class="hint">The page cannot write to the ledger on your PC. Fill this in, copy the command, run it in a terminal in the pokemon-ledger folder. It does the Cardmarket match, validates, and rolls back on any problem. Then run <code>py -3.13 refresh.py</code> and republish.</p>
<div class="addgrid">
<label>Card name <input id="a-name" placeholder="Mew"></label>
<label>Set code <input id="a-set" placeholder="cel25" list="setcodes"><datalist id="setcodes"></datalist></label>
<label>Number <input id="a-num" placeholder="11"></label>
<label>Set name <input id="a-setname" placeholder="Celebrations"></label>
<label>Binder page <input id="a-page" placeholder="Pikachu" list="pages"><datalist id="pages"></datalist></label>
<label>Language <select id="a-lang"><option>EN</option><option>JP</option><option>DE</option><option>FR</option></select></label>
<label class="chk"><input type="checkbox" id="a-rev"> reverse holo</label>
<label>Cardmarket id, only when asked <input id="a-cmid" placeholder="576756"></label>
</div>
<div class="cmdrow"><code id="a-cmd"></code><button type="button" id="a-copy">Copy</button></div>
<p class="hint">Set codes follow pokemontcg.io, list at github.com/PokemonTCG/pokemon-tcg-data/tree/master/cards/en. Remove a card: <code>py -3.13 manage.py remove &lt;#&gt;</code>, the # is shown when you hover a card name.</p>
</details>
<div class="tablewrap"><table id="t"><caption id="cap"></caption><thead><tr>
<th data-k="name">Card</th><th class="c-set" data-k="set">Set</th><th class="c-lang" data-k="lang">Lang</th>
<th class="num" data-k="trend">CM €</th><th class="num c-avg7" data-k="avg7">CM 7d €</th>
<th class="num" data-k="h0">CM € <span id="h0lbl"></span></th><th class="num" data-k="chg">Change</th>
</tr></thead><tbody id="tb"></tbody></table></div>
<section class="sources">
<h2>Sources</h2>
<ul>
<li><b>CM €, CM 7d €</b>: Cardmarket's own Price Trend and 7-day average, English card, near mint, regular print (<em class="rh">reverse holo</em> rows use the reverse-holo set). From Cardmarket's nightly export <a href="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json">price_guide_6.json</a>, offered on <a href="https://www.cardmarket.com/en/Pokemon/Data/Price-Guide">cardmarket.com &gt; Data &gt; Price Guide</a>. The date in the table header is the export's creation date.</li>
<li><b>CM € <span class="h0lbl"></span></b>: same field from an older copy of that export, <a href="https://web.archive.org/web/*/downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json">archived by the Wayback Machine</a>. Product IDs are stable, so it is a true Cardmarket history point. Every refresh saves a dated copy in <a href="history/">history/</a>.</li>
<li><b>Total</b>: sum of CM € × quantity over all cards (×2 marks a card owned twice). Net when selling is typically 60 to 75% after fees and shipping.</li>
</ul>
<h2>How a card is tied to its Cardmarket price</h2>
<p>The export has product IDs, names and expansion IDs, no set names or card numbers. Each card is matched once and its product ID stored. Expansion IDs are labelled by overlapping product names with the set's card list from <a href="https://github.com/PokemonTCG/pokemon-tcg-data/tree/master/cards/en">pokemon-tcg-data</a>; the product is then picked by name, and by price tier when several versions share it. Cards with a look-alike sibling carry a <span class="vf">verify</span> tag until checked on Cardmarket. Refreshing reads only Cardmarket's export; adding a card repeats the match once via <i>manage.py</i>. Mapping and reasoning: <a href="cm_expansions.json">cm_expansions.json</a>, <a href="cm_match.json">cm_match.json</a>, raw ledger <a href="binder.json">binder.json</a>.</p>
<p>Ledger last refreshed __TODAY__.</p>
</section>
</div>
<script>
const root=document.documentElement, tbtn=document.getElementById('theme');
function curTheme(){const t=root.getAttribute('data-theme');if(t)return t;return matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}
function applyTheme(t){if(t)root.setAttribute('data-theme',t);else root.removeAttribute('data-theme');tbtn.textContent=curTheme()==='dark'?'Light':'Dark'}
let saved=null;try{saved=localStorage.getItem('ledger-theme')}catch(e){}
applyTheme(saved);
tbtn.onclick=()=>{const next=curTheme()==='dark'?'light':'dark';try{localStorage.setItem('ledger-theme',next)}catch(e){}applyTheme(next)};
const D=__DATA__;
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const fdate=d=>{if(!d)return '';const [y,m,dd]=d.split('-');return `${+dd} ${MON[+m-1]} ${y}`};
const eur=v=>v==null?'–':v.toFixed(2);
const days=Object.keys(D[0].hist).sort(); const H0=days[0]; const NOW=D[0].cmd;
D.forEach(c=>{c.h0=c.hist[H0];c.chg=(c.h0&&c.trend)?(c.trend-c.h0)/c.h0*100:null});
const Q=c=>c.qty||1;
const tEur=D.reduce((a,c)=>a+(c.trend||0)*Q(c),0);
const both=D.filter(c=>c.h0!=null&&c.trend!=null);
const t0=both.reduce((a,c)=>a+c.h0*Q(c),0), tNow=both.reduce((a,c)=>a+c.trend*Q(c),0), pct=(tNow-t0)/t0*100;
document.getElementById('totEur').textContent=tEur.toFixed(0);
document.getElementById('sub').textContent=D.reduce((a,c)=>a+Q(c),0)+' cards, '+D.length+' distinct, '+new Set(D.map(c=>c.set)).size+' sets, 8 binder pages';
document.getElementById('cap').innerHTML=`<b>Cardmarket export of ${fdate(NOW)}</b> all CM € and CM 7d € values on this page carry that date`;
document.getElementById('h0lbl').textContent=fdate(H0).replace(/ (\d{4})$/,(m,y)=>' '+y.slice(2));
document.querySelectorAll('.h0lbl').forEach(e=>e.textContent=fdate(H0));
const bought=D.filter(c=>c.bought!=null), pending=bought.filter(c=>c.status==='pending');
const bPaid=bought.reduce((a,c)=>a+c.bought*Q(c),0), bNow=bought.reduce((a,c)=>a+(c.trend||0)*Q(c),0);
const top10=[...D].sort((a,b)=>(b.trend||0)*Q(b)-(a.trend||0)*Q(a)).slice(0,10).reduce((a,c)=>a+(c.trend||0)*Q(c),0);
document.getElementById('stats').innerHTML=`
<div class="stat"><div class="k">Cardmarket ${fdate(H0)}</div><div class="v">€${t0.toFixed(0)}</div><div class="n">same ${both.length} cards</div></div>
<div class="stat"><div class="k">Change since then</div><div class="v ${pct>=0?'up':'down'}">${pct>=0?'+':''}${pct.toFixed(0)}%</div><div class="n">€${t0.toFixed(0)} to €${tNow.toFixed(0)}</div></div>
<div class="stat"><div class="k">Top 10 cards</div><div class="v">€${top10.toFixed(0)}</div><div class="n">${(top10/tEur*100).toFixed(0)}% of total</div></div>
${bought.length?`<div class="stat"><div class="k">Bought cards, paid vs now</div><div class="v ${bNow>=bPaid?'up':'down'}">${bNow>=bPaid?'+':''}${(bNow-bPaid).toFixed(2)}</div><div class="n">paid €${bPaid.toFixed(2)}, now €${bNow.toFixed(2)}${pending.length?`, ${pending.length} pending`:``}</div></div>`:``}`;
const pages=[...new Set(D.map(c=>c.page))];
const pf=document.getElementById('pagef'); pages.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;pf.appendChild(o)});
let sortK='page',dir=1;
const numK=['trend','avg7','h0','chg'];
function render(){
  const q=document.getElementById('q').value.toLowerCase(), pg=pf.value;
  let rows=D.filter(c=>(!pg||c.page===pg)&&(!q||(c.name+' '+c.set+' '+c.num).toLowerCase().includes(q)));
  if(sortK==='page') rows.sort((a,b)=>a.n-b.n);
  else rows.sort((a,b)=>{let x=a[sortK],y=b[sortK]; if(numK.includes(sortK)){x=x==null?-Infinity:x;y=y==null?-Infinity:y;return (y-x)*dir} return String(x).localeCompare(String(y))*dir});
  const tb=document.getElementById('tb'); let h='',last=null;
  rows.forEach(c=>{
    if(sortK==='page'&&c.page!==last){last=c.page;const s=rows.filter(r=>r.page===c.page).reduce((a,r)=>a+(r.trend||0)*Q(r),0);h+=`<tr class="pagehead"><td colspan="7">${c.page}<span>€${s.toFixed(2)}</span></td></tr>`}
    const cls=c.chg==null?'':c.chg>=0?'up':'down';
    h+=`<tr><td class="card"><a href="${c.cm}" target="_blank" rel="noopener" title="#${c.n}  ·  manage.py remove ${c.n}">${c.name}</a>${Q(c)>1?`<span class="qty">×${Q(c)}</span>`:``}<a class="srch" href="${c.cm_search}" target="_blank" rel="noopener" title="Search this card on Cardmarket (expansion + name), fallback if the direct link is broken">⌕</a>${c.verify&&!c.verified?`<span class="vf" title="Two Cardmarket products share this name and set at a similar price. Open the link and confirm the trend shown there matches.">verify</span>`:``}${c.status==='pending'?`<span class="pend" title="Bought ${fdate(c.bought_on)} for €${eur(c.bought)} incl. shipping, not yet arrived. Clear with: manage.py arrived ${c.n}">pending</span>`:c.bought!=null?`<span class="pend paid" title="Bought ${fdate(c.bought_on)} for €${eur(c.bought)} incl. shipping">paid ${eur(c.bought)}</span>`:``}</td>
    <td class="set c-set">${c.set}<span class="num">${c.num}${c.finish==='reverse'?' <em class="rh">reverse holo</em>':''}</span></td><td class="lang c-lang">${c.lang}</td>
    <td class="num eur">${eur(c.trend)}</td><td class="num c-avg7">${eur(c.avg7)}</td>
    <td class="num">${eur(c.h0)}</td><td class="num chg ${cls}">${c.chg==null?'–':(c.chg>=0?'+':'')+c.chg.toFixed(0)+'%'}</td></tr>`});
  tb.innerHTML=h;
  document.querySelectorAll('th').forEach(th=>{th.classList.toggle('sorted',th.dataset.k===sortK);const a=th.querySelector('.arr');if(a)a.remove();if(th.dataset.k===sortK){const s=document.createElement('span');s.className='arr';s.textContent=dir>0?'▾':'▴';th.appendChild(s)}});
}
document.querySelectorAll('th').forEach(th=>{th.tabIndex=0;const f=()=>{const k=th.dataset.k;if(sortK===k){dir=-dir}else{sortK=k;dir=1}const sel=document.getElementById('sort');sel.value=[...sel.options].some(o=>o.value===sortK)?sortK:'page';render()};th.onclick=f;th.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();f()}}});
document.getElementById('sort').onchange=e=>{sortK=e.target.value;dir=1;render()};
pf.onchange=render; document.getElementById('q').oninput=render;
// add-card command builder
const dl=document.getElementById('pages'); pages.forEach(p=>{const o=document.createElement('option');o.value=p;dl.appendChild(o)});
const sc=document.getElementById('setcodes'); [...new Set(D.map(c=>c.setid))].sort().forEach(v=>{const o=document.createElement('option');o.value=v;sc.appendChild(o)});
const q=s=>'"'+String(s).replace(/"/g,'')+'"';
function buildCmd(){
  const g=id=>document.getElementById(id).value.trim();
  let cmd=`py -3.13 manage.py add ${q(g('a-name')||'Card Name')} ${g('a-set')||'setcode'} ${g('a-num')||'number'}`;
  if(g('a-page')) cmd+=` --page ${q(g('a-page'))}`;
  if(g('a-setname')) cmd+=` --set-name ${q(g('a-setname'))}`;
  if(g('a-lang')!=='EN') cmd+=` --lang ${g('a-lang')}`;
  if(document.getElementById('a-rev').checked) cmd+=' --reverse';
  if(g('a-cmid')) cmd+=` --cm-id ${g('a-cmid')}`;
  document.getElementById('a-cmd').textContent=cmd;
}
document.querySelectorAll('#addbox input,#addbox select').forEach(el=>{el.oninput=buildCmd;el.onchange=buildCmd});
document.getElementById('a-copy').onclick=async()=>{const t=document.getElementById('a-cmd').textContent;try{await navigator.clipboard.writeText(t);document.getElementById('a-copy').textContent='Copied';setTimeout(()=>document.getElementById('a-copy').textContent='Copy',1500)}catch(e){prompt('Copy this command:',t)}};
buildCmd();
render();
</script>'''
html = html.replace('__DATA__', json.dumps(data, separators=(',', ':'))).replace('__TODAY__', today)
open('binder_ledger.html', 'w', encoding='utf-8').write(html)
print('written', len(html))
