const assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require('jsdom');
const tick=()=>new Promise(r=>setImmediate(r));
function response(start=0){return {lecture_seule:true,publication_active:false,validation_juridique:'non_validee',perimetre:'revue_administrative_quarantaine',resultat:{type_recherche:'pages_pdf_natives',lot_id:'code_a',requete:'douanes',decalage:start,limite:20,publication_active:false,validation_juridique:'non_validee',ocr_effectue:false,classement_douanier_valide:false,restitution_juridique_a_date:false,articles_localises_automatiquement:false,archive:{manifest_sha256:'a'.repeat(64)},index_sha256:'b'.repeat(64),total_correspondances:21,resultats:Array.from({length:start===0?20:1},()=>({texte:'<img src=x onerror=evil()>'})),decalage_suivant:start===0?20:null}};}
async function setup(run){const dom=new JSDOM('<select><option value="code_a" data-lot-type="code">Code</option><option value="tarif_a" data-lot-type="tarif">Tarif</option></select><main></main>',{url:'https://test.invalid/#admin/revue-douaniere',runScripts:'outside-only'});const w=dom.window;w.sessionStorage.setItem('uniocr_token','TEST');let calls=[],answer=async()=>({ok:true,json:async()=>response()});w.fetch=(u,o)=>{calls.push({u,o});return answer(u,o);};w.eval(fs.readFileSync('web/customs-legal-pages.js','utf8'));const host=w.document.querySelector('main'),lot=w.document.querySelector('select');w.UniOCRCustomsLegalPages.mount(host,lot,()=>w.location.hash==='#admin/revue-douaniere');const inputs=host.querySelectorAll('input'),buttons=host.querySelectorAll('button');inputs[0].value='douanes';try{await run({w,host,lot,inputs,buttons,calls,respond:f=>{answer=f;}});for(const c of calls){assert.equal(c.o.method,'GET');assert.equal(c.o.cache,'no-store');assert.equal(c.o.credentials,'same-origin');assert.equal(c.o.headers.Authorization,'Bearer TEST');}}finally{w.close();}}

const longText='😀'.repeat(4500)+'Art. 137. NON OFFICIEL <img src=x onerror=evil()>'+ 'abc'.repeat(3000),points=Array.from(longText);
async function readerSetup(run){return setup(async ctx=>{
 const item={document_id:'TEST_O',page_pdf:1,pdf_sha256:'c'.repeat(64),sha256_texte_utf8:'d'.repeat(64),debut:4500};
 const origin=response();origin.resultat.resultats=[item];origin.resultat.total_correspondances=1;origin.resultat.decalage_suivant=null;
 ctx.respond(async()=>({ok:true,json:async()=>origin}));ctx.buttons[0].click();await tick();
 function page(url){const start=Number(new URL(url,'https://test.invalid').searchParams.get('offset')),end=Math.min(points.length,start+4000);return {lecture_seule:true,publication_active:false,validation_juridique:'non_validee',perimetre:'revue_administrative_quarantaine',resultat:{type_rapport:'lecture_page_pdf_indexee',lot_id:'code_a',document_id:item.document_id,page_pdf:1,pdf_sha256:item.pdf_sha256,sha256_texte_utf8:item.sha256_texte_utf8,index_sha256:origin.resultat.index_sha256,archive:origin.resultat.archive,publication_active:false,validation_juridique:'non_validee',ocr_effectue:false,lecture_seule:true,transcription_verification:'non_verifiee',unite_decalage:'points_de_code_unicode_python',nombre_pages_pdf:1,total_caracteres:points.length,decalage:start,limite:4000,fragment:points.slice(start,end).join(''),decalage_suivant:end<points.length?end:null}};}
 ctx.respond(async u=>({ok:true,json:async()=>page(u)}));
 const get=selector=>ctx.host.querySelector(selector),click=async selector=>{get(selector).click();await tick();};
 await click('[data-read-index-page]');await run({...ctx,page,get,click});
 });}
(async()=>{
 await setup(async({host,buttons,calls,respond})=>{assert.equal(calls.length,0);buttons[0].click();await tick();assert(!host.querySelector('img'));assert(host.textContent.includes('<img'));respond(async()=>({ok:true,json:async()=>response(20)}));buttons[1].click();await tick();assert(calls[1].u.includes('offset=20'));assert(buttons[1].disabled);});
 await setup(async({host,buttons,respond})=>{respond(async()=>({ok:false,status:403}));buttons[0].click();await tick();assert.equal(host.querySelector('input'),null);});
 await setup(async({host,buttons,respond})=>{respond(async()=>({ok:false,status:409}));buttons[0].click();await tick();assert(host.textContent.includes('non épinglé'));assert(buttons[1].disabled);});
 await setup(async({w,host,lot,inputs,buttons,respond})=>{let end;respond(()=>new Promise(r=>{end=r;}));buttons[0].click();lot.value='tarif_a';lot.dispatchEvent(new w.Event('change'));end({ok:true,json:async()=>response()});await tick();assert.equal(inputs[0].value,'');assert.equal(host.querySelector('pre').textContent,'');assert(host.querySelector('fieldset').disabled);});
 await setup(async({w,host,buttons,respond})=>{let end;respond(()=>new Promise(r=>{end=r;}));buttons[0].click();w.sessionStorage.setItem('uniocr_token','AUTRE');end({ok:true,json:async()=>response()});await tick();assert.equal(host.textContent,'');});
 await setup(async({host,buttons,respond})=>{const r=response();r.publication_active=true;respond(async()=>({ok:true,json:async()=>r}));buttons[0].click();await tick();assert(host.textContent.includes('non conforme'));assert.equal(host.querySelector('pre').textContent,'');});

 await setup(async({w,host,inputs,buttons,respond,calls})=>{
   const mode=host.querySelector('[data-pdf-mode]');mode.value='reperes';mode.dispatchEvent(new w.Event('change'));inputs[0].value='137';
   const item={document_id:'TEST_O',page_pdf:1,pdf_sha256:'c'.repeat(64),sha256_texte_utf8:'d'.repeat(64),numero_litteral:'137',debut:300,fin:308};
   const r=response();r.resultat.type_recherche='reperes_articles_pdf';r.resultat.requete='137';r.resultat.reperes_detectes_automatiquement=true;r.resultat.total_correspondances=1;r.resultat.resultats=[item];r.resultat.decalage_suivant=null;
   respond(async()=>({ok:true,json:async()=>r}));buttons[0].click();await tick();assert(calls.at(-1).u.includes('/pdf-article-markers?'));assert(calls.at(-1).u.includes('numero=137'));
   const p={lecture_seule:true,publication_active:false,validation_juridique:'non_validee',perimetre:'revue_administrative_quarantaine',resultat:{type_rapport:'lecture_page_pdf_indexee',lot_id:'code_a',document_id:'TEST_O',page_pdf:1,pdf_sha256:item.pdf_sha256,sha256_texte_utf8:item.sha256_texte_utf8,index_sha256:r.resultat.index_sha256,archive:r.resultat.archive,publication_active:false,validation_juridique:'non_validee',ocr_effectue:false,lecture_seule:true,transcription_verification:'non_verifiee',unite_decalage:'points_de_code_unicode_python',nombre_pages_pdf:1,total_caracteres:132,decalage_suivant:null,decalage:100,limite:4000,fragment:'Art. 137 <img src=x onerror=evil()>'}};
   p.resultat.total_caracteres=100+Array.from(p.resultat.fragment).length;
   respond(async()=>({ok:true,json:async()=>p}));host.querySelector('[data-read-index-page]').click();await tick();assert(calls.at(-1).u.includes('/pdf-index-page?'));assert(host.querySelector('[data-index-page]').textContent.includes('<img'));assert(!host.querySelector('img'));
   p.resultat.index_sha256='e'.repeat(64);respond(async()=>({ok:true,json:async()=>p}));host.querySelector('[data-read-index-page]').click();await tick();assert.equal(host.querySelector('[data-index-page]').textContent,'');assert(host.textContent.includes('non conforme'));
   mode.value='texte';mode.dispatchEvent(new w.Event('change'));assert.equal(host.querySelector('[data-read-index-page]'),null);assert.equal(inputs[0].value,'');
 });

 await setup(async({host,buttons,respond})=>{buttons[0].click();await tick();const r=response(20);r.resultat.index_sha256='f'.repeat(64);respond(async()=>({ok:true,json:async()=>r}));buttons[1].click();await tick();assert.equal(host.querySelector('pre').textContent,'');assert(host.textContent.includes('Index changé'));assert(buttons[1].disabled);});

 await readerSetup(async({get,click,calls,host})=>{
  assert(get('[data-index-page]').textContent.includes('décalage Unicode 4300'));
  assert(get('[data-anchor-fragment]').disabled);assert(!get('[data-previous-fragment]').disabled);
  await click('[data-next-fragment]');assert(calls.at(-1).u.includes('offset=8300'));
  await click('[data-anchor-fragment]');assert(calls.at(-1).u.includes('offset=4300'));
  await click('[data-previous-fragment]');assert(calls.at(-1).u.includes('offset=300'));
  await click('[data-previous-fragment]');assert(get('[data-previous-fragment]').disabled);
  let reconstructed=get('[data-index-page]').textContent.split('\n').slice(2).join('\n');
  while(!get('[data-next-fragment]').disabled){await click('[data-next-fragment]');reconstructed+=get('[data-index-page]').textContent.split('\n').slice(2).join('\n');}
  assert.equal(reconstructed,longText);assert(!host.querySelector('img'));assert.equal(calls.at(-1).o.method,'GET');
 });
 for(const corrupt of [p=>{p.decalage_suivant=p.decalage;},p=>{p.total_caracteres++;},p=>{p.fragment+='x';},p=>{p.index_sha256='e'.repeat(64);},p=>{p.unite_decalage='octets';}]){
  await readerSetup(async({respond,page,click,get,host})=>{respond(async u=>{const r=page(u);corrupt(r.resultat);return {ok:true,json:async()=>r};});await click('[data-next-fragment]');assert.equal(get('[data-index-page]').textContent,'');assert(get('[data-next-fragment]').disabled);assert(host.textContent.includes('non conforme'));});
 }
 await readerSetup(async({respond,click,host})=>{respond(async()=>({ok:false,status:403}));await click('[data-next-fragment]');assert.equal(host.textContent,'');});
 await readerSetup(async({respond,page,click,w,inputs,get})=>{let end,url;respond(u=>{url=u;return new Promise(r=>{end=r;});});await click('[data-next-fragment]');inputs[0].value='autre';inputs[0].dispatchEvent(new w.Event('input'));end({ok:true,json:async()=>page(url)});await tick();assert.equal(get('[data-index-page]').textContent,'');assert(get('[data-next-fragment]').disabled);});
 await readerSetup(async({respond,page,click,w,host})=>{let end,url;respond(u=>{url=u;return new Promise(r=>{end=r;});});await click('[data-next-fragment]');w.sessionStorage.setItem('uniocr_token','AUTRE');end({ok:true,json:async()=>page(url)});await tick();assert.equal(host.textContent,'');});
 console.log('17 scénarios recherche/repères/fragments PDF réussis');
})().catch(e=>{console.error(e);process.exit(1);});
