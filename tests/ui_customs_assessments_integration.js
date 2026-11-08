const assert=require('node:assert/strict'), fs=require('node:fs'), {JSDOM}=require('jsdom');
const base=process.argv[2];
(async()=>{
 const dom=new JSDOM('<select><option value="tarif_a" data-lot-type="tarif">tarif_a · tarif</option></select><main></main>',{url:base+'/#admin/revue-douaniere',runScripts:'outside-only'});
 const w=dom.window,requests=[];w.sessionStorage.setItem('uniocr_token','TEST_ADMIN_NON_PRODUCTION');
 w.fetch=async(url,opts)=>{const response=await fetch(base+url,opts);requests.push({method:opts.method,status:response.status});return response;};
 try{
 w.eval(fs.readFileSync('web/customs-assessments.js','utf8'));
 w.UniOCRCustomsAssessments.mount(w.document.querySelector('main'),w.document.querySelector('select'),()=>true);
 const field=n=>w.document.querySelector('[data-field="'+n+'"]'),button=n=>w.document.querySelector('[data-action="'+n+'"]');
 const idle=async()=>{const start=Date.now();while(w.document.querySelector('fieldset').disabled){if(Date.now()-start>5000)throw Error('Délai UI');await new Promise(r=>setTimeout(r,10));}};
 field('id').value='HTTP-NON-OFFICIEL';field('designation').value='Équipement';
 const piece=n=>w.document.querySelector('[data-piece-field="'+n+'"]');piece('piece_id').value='HTTP-PIECE';piece('nom').value='NON-OFFICIEL.txt';piece('localisateur_declare').value='Section technique déclarée';piece('texte').value='DOCUMENT NON OFFICIEL مادة';button('add-piece').click();
 button('create').click();await idle();assert.equal(requests.at(-1).status,200);assert(w.document.body.textContent.includes('Version 1'));assert(w.document.body.textContent.includes('Extraits reçus :'));assert(!w.document.body.textContent.includes('Extraits reçus : undefined'));
 field('justification').value='Revue documentaire HTTP NON OFFICIELLE';button('save').click();await idle();assert.equal(requests.at(-1).status,200);assert(w.document.body.textContent.includes('Version 2'));
 button('load').click();await idle();assert.equal(requests.at(-1).status,200);assert(w.document.body.textContent.includes('admin-test'));assert(w.document.body.textContent.includes('en_revue'));assert(w.document.body.textContent.includes('HTTP-PIECE'));assert(w.document.body.textContent.includes('non_verifiee'));
 field('version_lecture').value='1';button('load-version').click();await idle();assert.equal(requests.at(-1).status,200);assert(button('save').disabled);assert(w.document.body.textContent.includes('DOCUMENT NON OFFICIEL مادة'));
 button('compare').click();await idle();assert.equal(requests.at(-1).status,200);assert(w.document.querySelector('[data-comparison]').textContent.includes('Comparaison de la version enregistrée 1'));assert(button('save').disabled);
 assert.deepEqual(requests.map(x=>x.method),['POST','PATCH','GET','GET','GET']);
 console.log('HTTP_REEL_DOSSIER_OK');
 }finally{w.close();}
})().catch(e=>{console.error(e);process.exit(1);});
