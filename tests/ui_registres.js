/* Vérification en lecture seule : npm run ui:registres [URL].
 * Nécessite un serveur et au moins un dossier existant. Aucune création. */
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
w.location.hash='#douane/controles'; await att(2200);
const page=p();
let bouton=[...page.querySelectorAll('button')].find(b=>/nouvelle|ajouter|créer/i.test(b.textContent));
if(!bouton){ bouton=[...page.querySelectorAll('button')].find(b=>b.textContent.trim() === "Nouveau"); }
if(!bouton) throw new Error("Bouton Nouveau absent");
console.log('boutons =', [...page.querySelectorAll('button')].slice(0,6).map(b=>b.textContent.trim()).join(' / '));
console.log('bouton =', bouton && bouton.textContent.trim());
bouton.click(); await att(2500);
const boite=doc.querySelector('.ecran__boite');
console.log('boite =', !!boite, '| champs =', boite?[...boite.querySelectorAll('[id^=champ-]')].map(e=>e.id).join(','):'-');
const champ=boite.querySelector('#champ-dossier_id');
const liste=doc.getElementById(champ.getAttribute('list'));
const note=boite.querySelector('.ecran__champ .ecran__aide--ref');
if(!liste || !liste.options.length) throw new Error('Aucun dossier proposé (ce test exige un dossier existant)');
console.log('options datalist =', liste.options.length);
console.log('note =', note && note.textContent);
console.log('1re suggestion =', liste.options[0].value, '|', liste.options[0].label);
// validation : un identifiant inventé est refusé
const valider=[...boite.querySelectorAll('button')].find(b=>/créer/i.test(b.textContent));
champ.value='dos_inconnu'; champ.dispatchEvent(new w.Event('input',{bubbles:true}));
valider.click(); await att(500);
const refus=boite.querySelector('.ecran__erreur').textContent;
if(!refus.includes('choisir dans la liste')) throw new Error('Identifiant inconnu non refusé');
console.log('refus =', refus);
console.log('échecs =', echecs.length?echecs.slice(0,3):'aucun');
if(echecs.length) throw new Error(echecs.join(', '));
w.close(); process.exit(0);
})().catch(e=>{console.log('FATAL',e.message);process.exit(1);});
