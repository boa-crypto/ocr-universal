const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const script=fs.readFileSync('web/customs-assessments.js','utf8');
const tick=()=>new Promise(r=>setImmediate(r));
const doc=(version=1)=>({id:'DEMO',lot_id:'tarif_a',version,statut:version===1?'brouillon':'en_revue',acteur:'admin-test',manifest_sha256:'a'.repeat(64),publication_active:false,validation_juridique:'non_validee',diagnostic:{classement_ia_effectue:false,produit_declare:{designation:'Équipement',matiere:null,fonction:null,usage:null,caracteristiques:null},questions_a_documenter:[],recherche:{resultats:[{ligne:{code_tarifaire_10:'0101000000',designation_officielle_fr:'<img src=x onerror=evil()>',designation_officielle_ar:'معدات',reference:{source_id:'S',localisateur:'L1'}},termes_non_retrouves_par_critere:{}}]}}});
const envelope=(d,read=true)=>({lecture_seule:read,publication_active:false,validation_juridique:'non_validee',perimetre:'revue_administrative_quarantaine',resultat:d});
let count=0;
async function scenario(name,run){
 const dom=new JSDOM('<select><option value="tarif_a" data-lot-type="tarif">tarif_a · tarif</option><option value="code_a" data-lot-type="code">code_a · code</option></select><div id="host"></div>',{url:'https://test.invalid/#admin/revue-douaniere',runScripts:'outside-only'});
 const w=dom.window;w.sessionStorage.setItem('uniocr_token','TEST-NON-PRODUCTION');let calls=[];
 let responder=async()=>({ok:true,status:200,json:async()=>envelope(doc())});
 w.fetch=(url,opts)=>{calls.push({url,opts});return responder(url,opts);};
 w.eval(script);const host=w.document.getElementById('host'),lot=w.document.querySelector('select');
 w.UniOCRCustomsAssessments.mount(host,lot,()=>w.location.hash==='#admin/revue-douaniere');
 const field=n=>host.querySelector('[data-field="'+n+'"]');const button=n=>host.querySelector('[data-action="'+n+'"]');
 field('id').value='DEMO';
 const load=async()=>{button('load').click();await tick();await tick();};
 try{await run({w,host,lot,calls,field,button,load,respond:fn=>{responder=fn;},reply:(d,read=true,status=200)=>{responder=async()=>({ok:status===200,status,json:async()=>envelope(d,read)});}});
 for(const c of calls){assert(c.url.startsWith('/api/v1/customs-review/lots/'));assert.equal(c.opts.cache,'no-store');assert.equal(c.opts.credentials,'same-origin');assert.equal(c.opts.headers.Authorization,'Bearer TEST-NON-PRODUCTION');}
 count++;console.log('OK',name);
 }finally{w.close();}
}
(async()=>{
 await scenario('GET, noms hostiles uniquement texte',async({host,load,button})=>{await load();assert(host.textContent.includes('<img'));assert(!host.querySelector('img'));assert(!button('save').disabled);});
 await scenario('création explicite sans acteur client',async({field,button,reply,calls})=>{field('designation').value='Équipement';reply(doc(),false);button('create').click();await tick();let p=JSON.parse(calls[0].opts.body);assert.equal(calls[0].opts.method,'POST');assert.equal(p.dossier_id,'DEMO');assert(!('user' in p));});
 await scenario('révision depuis version serveur uniquement',async({load,field,button,reply,calls})=>{await load();field('justification').value='Motivation non officielle';reply(doc(2),false);button('save').click();await tick();let p=JSON.parse(calls.at(-1).opts.body);assert.equal(p.version_attendue,1);assert.equal(p.statut,'en_revue');assert.equal(calls.at(-1).opts.method,'PATCH');});
 await scenario('pas sélection automatique, référence du candidat obligatoire',async({load,field,button,calls,reply})=>{await load();field('justification').value='Motivation non officielle';field('statut').value='proposition_humaine';field('rgi').value='Raisonnement NON OFFICIEL';field('notes').value='Exclusions NON OFFICIELLES';button('save').click();assert.equal(calls.length,1);field('code').value='0101000000';reply(doc(2),false);button('save').click();await tick();assert.deepEqual(JSON.parse(calls.at(-1).opts.body).references,[{source_id:'S',localisateur:'L1'}]);});
 await scenario('409 impose relecture, aucun rejeu automatique',async({load,field,button,reply,calls})=>{await load();field('justification').value='Motivation non officielle';reply(null,false,409);button('save').click();await tick();assert(button('save').disabled);assert.equal(calls.length,2);reply(doc(2));await load();assert(!button('save').disabled);});
 await scenario('503 commit possible, relire avant écriture',async({load,field,button,reply,host,calls})=>{await load();field('justification').value='Motivation non officielle';reply(null,false,503);button('save').click();await tick();assert(button('save').disabled);assert(button('create').disabled);assert(host.textContent.includes('sauvegarde possible'));assert.equal(calls.length,2);});
 await scenario('double clic ne double pas mutation',async({load,field,button,respond,calls})=>{await load();field('justification').value='Motivation non officielle';let end;respond(()=>new Promise(r=>{end=r;}));button('save').click();button('save').click();assert.equal(calls.length,2);end({ok:true,json:async()=>envelope(doc(2),false)});await tick();});
 await scenario('changement de lot efface produit et révision',async({load,lot,field,host,w})=>{await load();lot.value='code_a';lot.dispatchEvent(new w.Event('change'));assert.equal(field('designation').value,'');assert(host.querySelector('fieldset').disabled);});
 await scenario('réponse tardive après changement de route ignorée',async({w,load,respond,host})=>{let end;respond(()=>new Promise(r=>{end=r;}));const pending=load();w.location.hash='#autre';end({ok:true,json:async()=>envelope(doc())});await pending;assert(!host.textContent.includes('<img'));});
 await scenario('changement jeton purge données et refuse réponse',async({load,w,field,button})=>{await load();w.sessionStorage.setItem('uniocr_token','AUTRE');button('load').click();assert.equal(field('designation'),null);});
 await scenario('enveloppe de publication hostile non affichée',async({reply,respond,host,load,button})=>{respond(async()=>({ok:true,json:async()=>({...envelope(doc()),publication_active:true})}));await load();assert(button('save').disabled);assert(!host.textContent.includes('<img'));});
 await scenario('identifiant chemin refusé sans réseau',async({field,load,calls})=>{field('id').value='../escape';await load();assert.equal(calls.length,0);});

 await scenario('403 purge champs, historique et actions',async({load,field,button,reply,host})=>{await load();reply(null,true,403);await load();assert.equal(field('designation'),null);assert(!host.textContent.includes('Équipement'));assert.equal(button('save'),null);});
 await scenario('panne réseau en lecture verrouille ancienne version',async({load,respond,button})=>{await load();respond(async()=>{throw Error('network');});await load();assert(button('save').disabled);assert(button('create').disabled);});
 await scenario('réouverture sans modification implicite du produit',async({reply,load,field,button,calls})=>{const d=doc(2);d.statut='proposition_humaine';reply(d);await load();field('justification').value='Réouverture documentaire NON OFFICIELLE';reply(doc(3),false);button('save').click();await tick();assert(!('produit' in JSON.parse(calls.at(-1).opts.body)));});
 await scenario('réponse incomplète ne conserve pas révision utilisable',async({load,respond,button})=>{await load();const d=doc(2);delete d.diagnostic.produit_declare;respond(async()=>({ok:true,json:async()=>envelope(d)}));await load();assert(button('save').disabled);});

 await scenario('pièce textuelle ajoutée localement, sauvegarde explicite',async({host,field,button,calls,reply})=>{
   const p=n=>host.querySelector('[data-piece-field="'+n+'"]');
   p('piece_id').value='P1';p('nom').value='NON-OFFICIEL.txt';p('localisateur_declare').value='Section déclarée';p('texte').value='<img src=x onerror=evil()> NON OFFICIEL';
   button('add-piece').click();assert.equal(calls.length,0);assert(!host.querySelector('img'));
   field('designation').value='Équipement';reply(doc(),false);button('create').click();await tick();
   const pieces=JSON.parse(calls[0].opts.body).pieces_techniques;assert.equal(pieces.length,1);assert.equal(pieces[0].piece_id,'P1');assert(!('fourni_par' in pieces[0]));
 });
 await scenario('pièce chargée puis retrait versionné, jamais automatique',async({host,reply,load,calls,field,button})=>{
   const d=doc();d.pieces_techniques=[{piece_id:'P1',nom:'NON-OFFICIEL.txt',nature:'notice',criteres_declares:['matiere'],localisateur_declare:'Section reçue',texte:'<img src=x onerror=evil()>',sha256:'a'.repeat(64)}];
   reply(d);await load();assert(!host.querySelector('img'));host.querySelector('[data-remove-piece="P1"]').click();assert.equal(calls.length,1);
   field('justification').value='Retrait explicite NON OFFICIEL';reply(doc(2),false);button('save').click();await tick();assert.deepEqual(JSON.parse(calls.at(-1).opts.body).pieces_techniques,[]);
 });
 await scenario('version historique seulement lecture, puis retour version courante',async({field,button,reply,calls,load})=>{
   field('version_lecture').value='1';reply(doc());button('load-version').click();await tick();assert(calls.at(-1).url.endsWith('?version=1'));assert(button('save').disabled);assert(button('create').disabled);
   reply(doc(2));await load();assert(!button('save').disabled);
 });
 await scenario('version historique incorrecte refusée',async({field,button,reply,host})=>{
   field('version_lecture').value='1';reply(doc(2));button('load-version').click();await tick();assert(button('save').disabled);assert(host.textContent.includes('Version historique incohérente'));
 });
 await scenario('pièces locales effacées au changement de lot',async({host,lot,w,button})=>{
   const p=n=>host.querySelector('[data-piece-field="'+n+'"]');p('piece_id').value='P1';p('nom').value='PIECE.txt';p('localisateur_declare').value='Section';p('texte').value='DOCUMENT NON OFFICIEL';button('add-piece').click();
   lot.value='code_a';lot.dispatchEvent(new w.Event('change'));assert.equal(p('texte').value,'');assert(!host.querySelector('[data-remove-piece]'));
 });
 await scenario('texte UTF8 importé localement sans requête ni ajout automatique',async({host,w,calls})=>{
   w.TextDecoder=TextDecoder;const input=host.querySelector('input[type=file]');const bytes=new TextEncoder().encode('مادة NON OFFICIELLE');
   Object.defineProperty(input,'files',{configurable:true,value:[{name:'notice.txt',size:bytes.length,arrayBuffer:async()=>bytes.buffer}]});input.dispatchEvent(new w.Event('change'));await tick();
   assert(host.querySelector('[data-piece-field=texte]').value.includes('مادة'));assert.equal(calls.length,0);assert(!host.querySelector('[data-remove-piece]'));
 });
 await scenario('UTF8 invalide refusé localement',async({host,w,calls})=>{
   w.TextDecoder=TextDecoder;const input=host.querySelector('input[type=file]');Object.defineProperty(input,'files',{configurable:true,value:[{name:'notice.txt',size:1,arrayBuffer:async()=>new Uint8Array([255]).buffer}]});input.dispatchEvent(new w.Event('change'));await tick();assert.equal(host.querySelector('[data-piece-field=texte]').value,'');assert.equal(calls.length,0);assert(host.textContent.includes('Import refusé'));
 });

 await scenario('citation sélectionnée : indices Unicode, pas UTF16',async({host,button,field,reply,calls})=>{
   const p=n=>host.querySelector('[data-piece-field="'+n+'"]');p('piece_id').value='CITE';p('nom').value='NON-OFFICIEL.txt';p('localisateur_declare').value='Section';p('critere').value='matiere';p('texte').value='😀 acier NON OFFICIEL';p('valeur_declaree').value='acier';p('texte').setSelectionRange(3,8);button('cite-selection').click();button('add-piece').click();
   field('designation').value='Équipement';reply(doc(),false);button('create').click();await tick();const claim=JSON.parse(calls[0].opts.body).pieces_techniques[0].declarations_attributs[0];assert.equal(claim.debut,2);assert.equal(claim.fin,7);assert.equal(claim.citation,'acier');
 });
 await scenario('édition du texte invalide la citation locale',async({host,button,field,w,reply,calls})=>{
   const p=n=>host.querySelector('[data-piece-field="'+n+'"]');p('piece_id').value='CITE';p('nom').value='NON-OFFICIEL.txt';p('localisateur_declare').value='Section';p('texte').value='acier NON OFFICIEL';p('valeur_declaree').value='acier';p('texte').setSelectionRange(0,5);button('cite-selection').click();p('texte').value='AUTRE TEXTE NON OFFICIEL';p('texte').dispatchEvent(new w.Event('input'));button('add-piece').click();field('designation').value='Équipement';reply(doc(),false);button('create').click();await tick();assert.deepEqual(JSON.parse(calls[0].opts.body).pieces_techniques[0].declarations_attributs,[]);
 });

 await scenario('nouvel identifiant après historique permet une création explicite',async({field,button,reply,w})=>{
   field('version_lecture').value='1';reply(doc());button('load-version').click();await tick();assert(button('create').disabled);field('id').value='NOUVEAU';field('id').dispatchEvent(new w.Event('input'));field('id').dispatchEvent(new w.Event('change'));assert(!button('create').disabled);assert(button('save').disabled);
 });
 console.log(count+' scénarios métier UI réussis');
})().catch(e=>{console.error(e);process.exit(1);});
