/* Comparaison en lecture seule : serveur actif requis. */
(async()=>{
const {JSDOM,VirtualConsole}=require('jsdom');
const realFetch=global.fetch; const base=process.argv[2] || 'http://127.0.0.1:8000'; const echecs=[];
const att=ms=>new Promise(r=>setTimeout(r,ms));
const dom=await JSDOM.fromURL(base+'/',{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,virtualConsole:new VirtualConsole(),
 beforeParse(w){w.fetch=(u,o)=>{const s=String(u);const abs=s.startsWith('http')?s:base+(s.startsWith('/')?s:'/'+s);if(o && o.method && o.method !== 'GET') {echecs.push('Écriture interdite');throw new Error('Écriture interdite');}return realFetch(abs,o).then(r=>{if(r.status>=400)echecs.push(abs.slice(base.length)+' → '+r.status);return r;});};
   w.scrollTo=()=>{}; w.confirm=()=>true;
   w.matchMedia=w.matchMedia||(()=>({matches:false,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}));}});
const w=dom.window, doc=w.document; await att(5200);
const p=()=>[...doc.querySelectorAll('section.page')].filter(s=>w.getComputedStyle(s).display!=='none'&&!s.classList.contains('hidden'))[0];
w.location.hash='#rapports/comparaison'; await att(2600);
const page=p();
console.log('page =', page.id, '| titre =', (page.querySelector('.ecran__titre')||{}).textContent);
const rows=[...page.querySelectorAll('tbody tr')];
if(rows.length !== 6) throw new Error('Six indicateurs attendus');
const note=page.querySelector('[role=status]');
if(!note || !note.textContent.includes('Photographie des états actuels')) throw new Error('Limites de lecture absentes');
console.log('limites =', note.textContent);
console.log('lignes =', rows.length);
rows.forEach(r=>console.log(' •', [...r.querySelectorAll('td')].slice(0,5).map(t=>t.textContent.trim()).join(' | ')));
// filtre tendance
const sel=page.querySelector('select');
if(sel){ const opt=[...sel.options].map(o=>o.value).filter(Boolean); console.log('filtres =', opt.join(','));
  sel.value=opt[0]; sel.dispatchEvent(new w.Event('change',{bubbles:true})); await att(600);
  console.log('après filtre "'+opt[0]+'" :', page.querySelectorAll('tbody tr').length, 'ligne(s)');
}
console.log('échecs =', echecs.length?echecs.slice(0,3):'aucun');
if(echecs.length) throw new Error(echecs.join(', '));
w.close(); process.exit(0);
})().catch(e=>{console.log('FATAL',e.message);process.exit(1);});
