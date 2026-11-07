/* Tests UI isolés. Réponses de contrat NON OFFICIELLES, jamais en production.
 * Les habilitations réelles sont qualifiées séparément par test_customs_review.py.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const script = fs.readFileSync('web/customs-review.js', 'utf8');
const tick = () => new Promise(r => setImmediate(r));
const envelope = resultat => ({lecture_seule:true, publication_active:false,
  validation_juridique:'non_validee', perimetre:'revue_administrative_quarantaine', resultat});
const lot = (id, type_lot='code') => ({id, type_lot, manifest_sha256_attendu:'a'.repeat(64)});
let compte = 0;
async function scenario(nom, action, lotsInit=[lot('test-code'),lot('test-tarif','tarif')]) {
  const dom = new JSDOM('<div id="customs-review-host"></div>', {
    url:'https://preview.invalid/#admin/revue-douaniere', runScripts:'outside-only'});
  const w = dom.window, appels = [];
  let repondre = () => Promise.resolve({ok:true, json:async()=>envelope({lots:lotsInit})});
  w.fetch = (url, opts) => {appels.push({url, opts}); return repondre(url, opts);};
  w.sessionStorage.setItem('uniocr_token', 'JETON-TEST-NON-PRODUCTION');
  w.eval(script); await tick(); await tick();
  const host = w.document.getElementById('customs-review-host');
  const button = texte => [...host.querySelectorAll('button')].find(b => b.textContent.includes(texte));
  const status = () => host.querySelector('[role=status]').textContent;
  try {
    await action({w, host, appels, button, status,
      reponse: (body, code=200) => {repondre=()=>Promise.resolve({ok:code===200,status:code,json:async()=>body});},
      attendre: fn => {repondre=fn;}});
    for (const {url, opts} of appels) {
      assert(url.startsWith('/api/v1/customs-review/'));
      assert.equal(opts.method, 'GET'); assert.equal(opts.cache, 'no-store');
      assert.equal(opts.credentials, 'same-origin');
      assert.equal(opts.headers.Authorization, 'Bearer JETON-TEST-NON-PRODUCTION');
      assert.equal(opts.body, undefined);
    }
    compte++; console.log('OK', nom);
  } finally {w.close();}
}
(async()=>{
await scenario('registre et absence de données implicites', async({host, appels, status})=>{
  assert.equal(appels.length,1); assert.equal(appels[0].url,'/api/v1/customs-review/lots');
  assert(status().includes('Intégrité non contrôlée')); assert.equal(host.querySelectorAll('li').length,2);
  assert.equal(host.querySelector('fieldset').disabled,false);
});
await scenario('contrôle, texte hostile sans injection', async({host,button,reponse,status})=>{
  reponse(envelope({preuve:'<img src=x onerror=alert(1)> العربية'}));
  button('Contrôler').click(); await tick();
  assert(host.querySelector('pre').textContent.includes('<img')); assert.equal(host.querySelector('img'),null);
  assert(status().includes('non validé')); assert.equal(host.querySelector('pre').dir,'auto');
});
await scenario('recherche AR, filtres et pagination', async({w,host,appels,reponse})=>{
  const inputs=host.querySelectorAll('input');
  inputs[0].value='أداة & acier'; inputs[1].value='1'; inputs[2].value='source';
  inputs[3].value='10'; inputs[4].value='20';
  reponse(envelope({total_correspondances:0,resultats:[]}));
  host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true})); await tick();
  const u = new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.searchParams.get('q'),'أداة & acier'); assert.equal(u.searchParams.get('article'),'1');
  assert.equal(u.searchParams.get('limit'),'10'); assert.equal(u.searchParams.get('offset'),'20');
});
await scenario('filtres Code exclus sur tarif', async({w,host,appels,reponse})=>{
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  assert.equal(host.querySelector('fieldset').disabled,true);
  reponse(envelope({resultats:[]})); host.querySelector('input').value='test';
  host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true})); await tick();
  assert(appels.at(-1).url.includes('/test-tarif/search?')); assert(!appels.at(-1).url.includes('article='));
});
await scenario('diff types incompatibles sans appel', async({host,appels,button,status})=>{
  host.querySelectorAll('select')[1].value='test-tarif'; button('Comparer').click();
  assert.equal(appels.length,1); assert(status().includes('même type'));
});
await scenario('diff compatible par IDs seuls', async({appels,button,reponse})=>{
  reponse(envelope({archives:{},changements:[]})); button('Comparer').click(); await tick();
  assert.equal(appels.at(-1).url,'/api/v1/customs-review/diff?avant=test-code&apres=test-code');
});
for(const code of [401,403,404,409,422,503]) {
  await scenario('erreur '+code+' sans ancien résultat', async({host,button,reponse,status})=>{
    reponse(envelope({sensible:'ancienne valeur'})); button('Contrôler').click(); await tick();
    reponse({detail:'NE-PAS-AFFICHER /serveur/secret'},code); button('Contrôler').click(); await tick();
    assert.equal(host.querySelector('pre').textContent,''); assert(!host.textContent.includes('NE-PAS-AFFICHER'));
    assert(!status().includes('Chargement')); if([401,403,503].includes(code)) assert.equal(host.querySelector('select'),null);
  });
}
await scenario('registre vide explicite', async({host,button,reponse,status})=>{
  reponse(envelope({lots:[]})); button('Actualiser').click(); await tick();
  assert(status().includes('Aucun lot inscrit')); assert.equal(host.querySelector('select'),null);
});
await scenario('réponse publiée ou mal formée refusée', async({host,button,reponse,status})=>{
  reponse({...envelope({secret:'non affichable'}), publication_active:true}); button('Contrôler').click(); await tick();
  assert.equal(host.querySelector('pre').textContent,''); assert(status().includes('inattendue'));
});
await scenario('réponse tardive ignorée après navigation', async({w,host,button,attendre})=>{
  let fin; attendre(()=>new Promise(r=>{fin=r;})); button('Contrôler').click();
  w.history.replaceState(null,'','#admin/journal'); w.dispatchEvent(new w.HashChangeEvent('hashchange')); await tick();
  fin({ok:true,json:async()=>envelope({secret:'NE-PAS-AFFICHER'})}); await tick();
  assert.equal(host.textContent,'');
});
await scenario('résultat remplacé : la dernière requête gagne', async({host,button,attendre,reponse})=>{
  let fin; attendre(()=>new Promise(r=>{fin=r;})); button('Contrôler').click();
  reponse(envelope({ordre:'NOUVEAU'})); button('Contrôler').click(); await tick();
  fin({ok:true,json:async()=>envelope({ordre:'ANCIEN'})}); await tick();
  assert(host.querySelector('pre').textContent.includes('NOUVEAU')); assert(!host.textContent.includes('ANCIEN'));
});
await scenario('changement de compte pendant requête', async({w,host,button,attendre,status})=>{
  let fin; attendre(()=>new Promise(r=>{fin=r;})); button('Contrôler').click();
  w.sessionStorage.removeItem('uniocr_token');
  fin({ok:true,json:async()=>envelope({secret:'NE-PAS-AFFICHER'})}); await tick();
  assert(!host.textContent.includes('NE-PAS-AFFICHER')); assert.equal(host.querySelector('select'),null);
  assert(status().includes('Compte modifié'));
});
await scenario('départ de page efface les données', async({w,host,button,reponse})=>{
  reponse(envelope({secret:'TEST'})); button('Contrôler').click(); await tick();
  w.dispatchEvent(new w.Event('pagehide')); assert.equal(host.textContent,'');
});
await scenario('retour depuis cache de navigation relit le registre', async({w,host,appels})=>{
  w.dispatchEvent(new w.Event('pagehide'));
  const event=new w.Event('pageshow'); Object.defineProperty(event,'persisted',{value:true});
  w.dispatchEvent(event); await tick();
  assert.equal(appels.length,2); assert.equal(host.querySelectorAll('li').length,2);
});
await scenario('historique avec numéro exact et paginations indépendantes', async({host,appels,button,reponse})=>{
  host.querySelectorAll('input')[1].value='5 bis';
  host.querySelectorAll('input')[2].value='SOURCE_IGNOREE';
  host.querySelectorAll('input')[5].value='10'; host.querySelectorAll('input')[6].value='20';
  reponse(envelope({type_rapport:'historique_documentaire_article',versions_meme_numero:[]}));
  button('Afficher l’historique').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/history');
  assert.equal(u.searchParams.get('article'),'5 bis'); assert.equal(u.searchParams.get('source'),null);
  assert.equal(u.searchParams.get('relations_limit'),'10'); assert.equal(u.searchParams.get('relations_offset'),'20');
});
await scenario('historique vide et tarif refusés côté interface', async({w,host,appels,button,status})=>{
  button('Afficher l’historique').click(); assert.equal(appels.length,1); assert(status().includes('requis'));
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  assert.equal(host.querySelectorAll('fieldset')[1].disabled,true);
  button('Afficher l’historique').click(); assert.equal(appels.length,1);
});
await scenario('fiche tarif exacte, zéros conservés et pagination', async({w,host,appels,button,reponse})=>{
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  const fiche=host.querySelector('[data-code10]').closest('fieldset');
  assert.equal(fiche.disabled,false);
  const inputs=fiche.querySelectorAll('input'); inputs[0].value='0101000000'; inputs[1].value='2'; inputs[2].value='1';
  reponse(envelope({type_rapport:'fiche_tarifaire_documentaire',ligne_trouvee:true}));
  button('Consulter la fiche').click(); await tick();
  assert.equal(appels.at(-1).url,'/api/v1/customs-review/lots/test-tarif/tariff/0101000000?measures_limit=2&measures_offset=1');
});
await scenario('fiche désactivée sur Code et numéros invalides refusés', async({w,host,appels,button,status})=>{
  assert.equal(host.querySelector('[data-code10]').closest('fieldset').disabled,true);
  button('Consulter la fiche').click(); assert.equal(appels.length,1);
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  for(const value of ['', '010100', '٠١٠١٠٠٠٠٠٠']) {
    host.querySelector('[data-code10]').value=value; button('Consulter la fiche').click();
    assert.equal(appels.length,1); assert(status().includes('dix chiffres ASCII'));
  }
});
await scenario('diagnostic de couverture sans pourcentage inventé', async({w,host,appels,button,reponse})=>{
  for(const id of ['test-code','test-tarif']) {
    const select=host.querySelector('select'); select.value=id; select.dispatchEvent(new w.Event('change'));
    reponse(envelope({type_rapport:'couverture_documentaire_declaree',nombre_officiel_attendu:null,
      pourcentage_completude_reglementaire:null,completude_reglementaire:'non_etablie'}));
    button('Diagnostiquer la couverture').click(); await tick();
    assert.equal(appels.at(-1).url,'/api/v1/customs-review/lots/'+id+'/coverage');
    const rep=JSON.parse(host.querySelector('pre').textContent);
    assert.equal(rep.pourcentage_completude_reglementaire,null); assert.equal(rep.nombre_officiel_attendu,null);
  }
});
await scenario('navigation racine et SH6, parent exact conservé', async({w,host,appels,button,reponse})=>{
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  const level=host.querySelector('[data-tree-level]'), parent=host.querySelector('[data-tree-parent]');
  assert.equal(parent.disabled,true); parent.value='IGNORÉ_RACINE';
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',enfants_declares:[]}));
  button('Parcourir la hiérarchie').click(); await tick();
  assert.equal(appels.at(-1).url,'/api/v1/customs-review/lots/test-tarif/tree?level=sections&limit=20&offset=0');
  level.value='codes'; level.dispatchEvent(new w.Event('change')); assert.equal(parent.disabled,false);
  parent.value='010100'; button('Parcourir la hiérarchie').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.searchParams.get('parent'),'010100'); assert.equal(u.searchParams.get('level'),'codes');
});
await scenario('navigation indisponible sur Code et parent requis hors racine', async({w,host,appels,button,status})=>{
  assert.equal(host.querySelector('[data-tree-level]').closest('fieldset').disabled,true);
  button('Parcourir la hiérarchie').click(); assert.equal(appels.length,1);
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  const level=host.querySelector('[data-tree-level]'); level.value='chapitres'; level.dispatchEvent(new w.Event('change'));
  button('Parcourir la hiérarchie').click(); assert.equal(appels.length,1); assert(status().includes('parent exact requis'));
});
await scenario('lecture exacte FR/AR et fragment non interprété en HTML', async({w,host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='TEST_O_A'; host.querySelector('[data-read-field]').value='texte_arabe';
  const texte='<img src=x onerror=alert(1)>\nنص 😀';
  reponse(envelope({type_rapport:'lecture_article_documentaire',fragment:texte}));
  button('Lire le fragment').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.searchParams.get('article_id'),'TEST_O_A'); assert.equal(u.searchParams.get('field'),'texte_arabe');
  assert.equal(u.searchParams.get('limit'),'4000');
  assert.equal(host.querySelector('[data-article-fragment]').textContent,texte);
  assert.equal(host.querySelector('[data-article-fragment]').hidden,false); assert.equal(host.querySelector('img'),null);
  reponse(envelope({type_rapport:'lecture_article_documentaire',fragment:null}));
  button('Lire le fragment').click(); await tick();
  assert.equal(host.querySelector('[data-article-fragment]').textContent,''); assert.equal(host.querySelector('[data-article-fragment]').hidden,true);
});
await scenario('lecture refusée sans ID ou sur tarif', async({w,host,appels,button,status})=>{
  button('Lire le fragment').click(); assert.equal(appels.length,1); assert(status().includes('version requis'));
  const select=host.querySelector('select'); select.value='test-tarif'; select.dispatchEvent(new w.Event('change'));
  assert.equal(host.querySelector('[data-read-id]').closest('fieldset').disabled,true);
  button('Lire le fragment').click(); assert.equal(appels.length,1);
});
await scenario('recherche Code ouvre la version exacte sans URL source', async({w,host,appels,button,reponse})=>{
  const id='ID/<img src=x>';
  reponse(envelope({type_recherche:'code_documentaire',resultats:[{id, url:'https://externe.invalid/secret'}]}));
  host.querySelector('input').value='texte'; host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true})); await tick();
  const lien=button('Lire la version '+id); assert(lien); assert.equal(host.querySelector('img'),null);
  reponse(envelope({type_rapport:'lecture_article_documentaire',fragment:'TRANSCRIPTION TEST NON OFFICIELLE'}));
  lien.click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/article'); assert.equal(u.searchParams.get('article_id'),id);
  assert.equal(u.searchParams.get('field'),'texte_integral'); assert.equal(u.searchParams.get('offset'),'0');
});
await scenario('histoire propose versions et contexte sans doublon', async({host,button,reponse})=>{
  host.querySelectorAll('input')[1].value='5 bis';
  reponse(envelope({type_rapport:'historique_documentaire_article',versions_meme_numero:[{id:'V1'}],
    articles_contexte_relations:[{id:'V1'},{id:'MODIF_7'}]}));
  button('Afficher l’historique').click(); await tick();
  const textes=[...host.querySelector('[data-review-actions]').querySelectorAll('button')].map(b=>b.textContent).filter(t=>t.startsWith('Lire la version'));
  assert.deepEqual(textes,['Lire la version V1','Lire la version MODIF_7']);
});
await scenario('résultat tarifaire ouvre une fiche sans perdre les zéros', async({w,host,appels,button,reponse})=>{
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  reponse(envelope({type_recherche:'tarif_documentaire',resultats:[{ligne:{code_tarifaire_10:'0101000000'}}]}));
  host.querySelector('input').value='010100'; host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true})); await tick();
  reponse(envelope({type_rapport:'fiche_tarifaire_documentaire'})); button('Fiche documentaire 0101000000').click(); await tick();
  assert(appels.at(-1).url.includes('/tariff/0101000000?')); assert.equal(host.querySelector('[data-code10]').value,'0101000000');
});
await scenario('descente hiérarchique par enfant déclaré et pagination', async({w,host,appels,button,reponse})=>{
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',niveau:'sections',niveau_suivant:'chapitres',
    parent_exact:null,enfants_declares:[{id:'SECTION_AR'}],limite:1,decalage:0,decalage_suivant:1,total_enfants_declares:2}));
  button('Parcourir la hiérarchie').click(); await tick();
  const page=button('Page suivante des enfants'); assert(page);
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',niveau:'sections',niveau_suivant:'chapitres',
    parent_exact:null,enfants_declares:[{id:'SECTION_AR'}],limite:1,decalage:1,decalage_suivant:null,total_enfants_declares:2}));
  page.click(); await tick(); assert(appels.at(-1).url.includes('offset=1'));
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',niveau:'chapitres',niveau_suivant:'positions',enfants_declares:[]}));
  button('Enfants de SECTION_AR').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid'); assert.equal(u.searchParams.get('level'),'chapitres');
  assert.equal(u.searchParams.get('parent'),'SECTION_AR'); assert.equal(u.searchParams.get('offset'),'0');
});
await scenario('fragment suivant reprend points de code et identité de réponse', async({host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='V1';
  reponse(envelope({type_rapport:'lecture_article_documentaire',article_trouve:true,texte_renseigne:true,
    unite_decalage:'points_de_code_unicode_python',article_id_exact:'V1',champ_texte:'texte_arabe',fragment:'😀ع',limite:2,decalage:0,decalage_suivant:2,total_caracteres:4}));
  button('Lire le fragment').click(); await tick();
  reponse(envelope({type_rapport:'lecture_article_documentaire',fragment:'SUITE'}));
  button('Fragment suivant de l’article').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid'); assert.equal(u.searchParams.get('offset'),'2');
  assert.equal(u.searchParams.get('field'),'texte_arabe'); assert.equal(u.searchParams.get('article_id'),'V1');
});
await scenario('actions effacées et boutons détachés inertes après changement de lot', async({w,host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='V1';
  reponse(envelope({type_rapport:'lecture_article_documentaire',article_trouve:true,texte_renseigne:true,
    unite_decalage:'points_de_code_unicode_python',article_id_exact:'V1',champ_texte:'texte_integral',fragment:'AA',limite:2,decalage:0,decalage_suivant:2,total_caracteres:4}));
  button('Lire le fragment').click(); await tick();
  const ancien=button('Fragment suivant de l’article'), n=appels.length;
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  assert.equal(host.querySelector('[data-review-actions]').textContent,''); ancien.click(); await tick(); assert.equal(appels.length,n);
});
await scenario('offset de retour invalide et faux niveau suivant ne créent pas d’action', async({w,host,button,reponse})=>{
  host.querySelector('[data-read-id]').value='V1';
  reponse(envelope({type_rapport:'lecture_article_documentaire',article_trouve:true,texte_renseigne:true,
    unite_decalage:'points_de_code_unicode_python',article_id_exact:'V1',champ_texte:'texte_arabe',fragment:'AA',limite:2,decalage:0,decalage_suivant:0,total_caracteres:4}));
  button('Lire le fragment').click(); await tick(); assert.equal(button('Fragment suivant de l’article'),undefined);
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',niveau:'sections',niveau_suivant:'codes',enfants_declares:[{id:'FAUX'}]}));
  button('Parcourir la hiérarchie').click(); await tick(); assert.equal(button('Enfants de FAUX'),undefined);
});
await scenario('action après changement de jeton refuse sans nouveau fetch', async({w,host,appels,button,reponse,status})=>{
  host.querySelectorAll('input')[1].value='5 bis';
  reponse(envelope({type_rapport:'historique_documentaire_article',versions_meme_numero:[{id:'V1'}]}));
  button('Afficher l’historique').click(); await tick(); const n=appels.length;
  w.sessionStorage.removeItem('uniocr_token'); button('Lire la version V1').click(); await tick();
  assert.equal(appels.length,n); assert.equal(host.querySelector('select'),null); assert(status().includes('Compte modifié'));
});
await scenario('audit indisponible : 503 efface texte et actions, message serveur générique', async({host,button,reponse,status})=>{
  host.querySelector('[data-read-id]').value='V1';
  reponse(envelope({type_rapport:'lecture_article_documentaire',article_trouve:true,texte_renseigne:true,
    unite_decalage:'points_de_code_unicode_python',article_id_exact:'V1',champ_texte:'texte_integral',
    fragment:'TEXTE TEST CONFIDENTIEL',limite:2,decalage:0,decalage_suivant:2,total_caracteres:4}));
  button('Lire le fragment').click(); await tick(); assert(button('Fragment suivant de l’article'));
  reponse({detail:{code:'audit_revue_indisponible',path:'/NE/PAS/AFFICHER'}},503);
  button('Lire le fragment').click(); await tick();
  assert.equal(host.querySelector('pre').textContent,''); assert.equal(host.querySelector('[data-article-fragment]').textContent,'');
  assert.equal(host.querySelector('[data-review-actions]').textContent,''); assert.equal(host.querySelector('select'),null);
  assert(status().includes('journal d’audit')); assert(!host.textContent.includes('/NE/PAS/AFFICHER'));
});
await scenario('export relit le serveur et conserve provenance sans jeton', async({w,host,appels,button,reponse})=>{
  let blob, nom;
  w.URL.createObjectURL=b=>{blob=b; return 'blob:test';}; w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){nom=this.download;};
  reponse(envelope({version:'ANCIENNE',archive:{manifest_sha256:'a'.repeat(64)}}));
  button('Contrôler').click(); await tick(); const chemin=appels.at(-1).url;
  reponse(envelope({version:'FRAICHE',archive:{manifest_sha256:'b'.repeat(64)}}));
  button('Exporter ce rapport').click(); await tick();
  assert.equal(appels.at(-1).url,chemin); assert.equal(nom,'uniocr-revue-non-validee.json'); assert(blob);
  const texte=await new Promise((resolve,reject)=>{const r=new w.FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsText(blob);});
  const rep=JSON.parse(texte); assert.equal(rep.resultat.version,'FRAICHE'); assert.equal(rep.publication_active,false);
  assert.equal(rep.validation_juridique,'non_validee'); assert(!texte.includes('JETON-TEST-NON-PRODUCTION'));
});
await scenario('export refusé par audit ou droits sans fichier', async({w,host,button,reponse})=>{
  let fichiers=0; w.URL.createObjectURL=()=>{fichiers++; return 'blob:test';};
  reponse(envelope({rapport:'TEST'})); button('Contrôler').click(); await tick();
  reponse({detail:'INTERNE SECRET'},503); button('Exporter ce rapport').click(); await tick();
  assert.equal(fichiers,0); assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
await scenario('ancien bouton export inerte après remplacement', async({host,appels,button,reponse})=>{
  reponse(envelope({rapport:'TEST'})); button('Contrôler').click(); await tick(); const ancien=button('Exporter ce rapport');
  button('Contrôler').click(); await tick(); const n=appels.length; ancien.click(); await tick(); assert.equal(appels.length,n);
});
const pdfRapport = (extra={})=>({type_rapport:'lecture_page_pdf_recu', document_declare:{id:'DOC_TEST',sha256:'a'.repeat(64)},
  sha256_pdf_lu:'a'.repeat(64), methode:'texte_natif_pdfium_sans_ocr',unite_decalage:'points_de_code_unicode_python',
  page_physique:1,nombre_pages_pdf:2,page_physique_suivante:2,limite:4,decalage:0,total_caracteres:10,
  fragment:'أ😀é',decalage_suivant:4,texte_natif_non_vide:true,...extra});
await scenario('PDF natif : paramètres exacts et texte sans HTML',async({host,appels,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC & عربي'; host.querySelector('[data-pdf-page]').value='2';
  host.querySelector('[data-pdf-limit]').value='4'; host.querySelector('[data-pdf-offset]').value='7';
  reponse(envelope(pdfRapport({fragment:'<img src=x onerror=alert(1)>',decalage_suivant:null})));
  button('Lire le texte natif PDF').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid'); assert.equal(u.searchParams.get('document_id'),'DOC & عربي');
  assert.equal(u.searchParams.get('page'),'2'); assert.equal(u.searchParams.get('offset'),'7');
  assert.equal(host.querySelector('img'),null); assert(host.querySelector('[data-article-fragment]').textContent.includes('<img'));
});
await scenario('PDF suites : Unicode Python et page suivante remet offset zéro',async({host,appels,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST'; reponse(envelope(pdfRapport()));
  button('Lire le texte natif PDF').click(); await tick();
  button('Fragment suivant de la page PDF').click(); await tick();
  assert(new URL(appels.at(-1).url,'https://test.invalid').searchParams.get('offset')==='4');
  button('Page physique PDF suivante').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid'); assert.equal(u.searchParams.get('page'),'2'); assert.equal(u.searchParams.get('offset'),'0');
});
await scenario('PDF sans texte natif ne devient pas OCR ou droit absent',async({host,button,reponse,status})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST';
  reponse(envelope(pdfRapport({fragment:'',total_caracteres:0,texte_natif_non_vide:false,decalage_suivant:null})));
  button('Lire le texte natif PDF').click(); await tick();
  assert(status().includes('aucun OCR')); assert(!button('Fragment suivant de la page PDF'));
});
await scenario('PDF invalides et tarif ne déclenchent pas de requête',async({w,host,appels,button})=>{
  const n=appels.length; button('Lire le texte natif PDF').click(); await tick(); assert.equal(appels.length,n);
  host.querySelector('[data-pdf-id]').value='DOC_TEST'; host.querySelector('[data-pdf-page]').value='0';
  button('Lire le texte natif PDF').click(); await tick(); assert.equal(appels.length,n);
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  button('Lire le texte natif PDF').click(); await tick(); assert.equal(appels.length,n);
});
await scenario('PDF suites incohérentes non proposées',async({host,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST';
  reponse(envelope(pdfRapport({decalage_suivant:5,page_physique_suivante:99})));
  button('Lire le texte natif PDF').click(); await tick();
  assert(!button('Fragment suivant de la page PDF')); assert(!button('Page physique PDF suivante'));
});
await scenario('PDF actions anciennes inertes après changement de lot',async({w,host,appels,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST'; reponse(envelope(pdfRapport()));
  button('Lire le texte natif PDF').click(); await tick(); const ancien=button('Page physique PDF suivante');
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  const n=appels.length; ancien.click(); await tick(); assert.equal(appels.length,n);
});
await scenario('PDF actions après changement de jeton effacent sans lecture',async({w,host,appels,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST'; reponse(envelope(pdfRapport()));
  button('Lire le texte natif PDF').click(); await tick(); const ancien=button('Page physique PDF suivante');
  w.sessionStorage.setItem('uniocr_token','AUTRE_TEST'); const n=appels.length; ancien.click(); await tick();
  assert.equal(appels.length,n); assert.equal(host.querySelector('pre').textContent,'');
});
await scenario('PDF 503 audit efface fragment et actions',async({host,button,reponse})=>{
  host.querySelector('[data-pdf-id]').value='DOC_TEST'; reponse(envelope(pdfRapport()));
  button('Lire le texte natif PDF').click(); await tick(); reponse({detail:{code:'audit_revue_indisponible'}},503);
  button('Page physique PDF suivante').click(); await tick();
  assert.equal(host.querySelector('pre').textContent,''); assert.equal(host.querySelector('[data-article-fragment]').textContent,'');
  assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const enfantsMixtes = (extra={})=>({type_rapport:'navigation_tarifaire_documentaire',niveau:'subdivisions',niveau_suivant:'subdivisions',
  parent_exact:'010100',limite:20,decalage:0,decalage_suivant:null,total_enfants_declares:2,enfants_declares:[
    {type_noeud:'subdivision_nationale',code:'0101000',code_parent:'010100'},
    {type_noeud:'code10',code_tarifaire_10:'0101000001',code_sh_6:'010100',code_subdivision_nationale:null}],...extra});
await scenario('subdivisions : enfants mixtes subdivision et code direct',async({w,host,appels,button,reponse})=>{
  const lot=host.querySelector('select'); lot.value='test-tarif'; lot.dispatchEvent(new w.Event('change'));
  const niveau=host.querySelector('[data-tree-level]'); niveau.value='subdivisions'; niveau.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-tree-parent]').value='010100'; reponse(envelope(enfantsMixtes()));
  button('Parcourir la hiérarchie').click(); await tick(); assert(button('Fiche documentaire 0101000001'));
  button('Enfants de 0101000').click(); await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid'); assert.equal(u.searchParams.get('level'),'subdivisions'); assert.equal(u.searchParams.get('parent'),'0101000');
});
await scenario('subdivisions : aucune action pour rattachement incohérent',async({w,host,button,reponse})=>{
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  reponse(envelope(enfantsMixtes({enfants_declares:[
    {type_noeud:'subdivision_nationale',code:'0201000',code_parent:'010100'},
    {type_noeud:'subdivision_nationale',code:'0101000',code_parent:'010101'},
    {type_noeud:'code10',code_tarifaire_10:'0201000000',code_sh_6:'010100',code_subdivision_nationale:null}]})));
  button('Contrôler').click(); await tick(); assert(!button('Enfants de')); assert(!button('Fiche documentaire'));
});
await scenario('subdivisions : pagination conserve niveau et parent',async({w,host,appels,button,reponse})=>{
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  reponse(envelope(enfantsMixtes({limite:1,decalage_suivant:1})));
  button('Contrôler').click(); await tick();button('Page suivante des enfants').click();await tick();
  const u=new URL(appels.at(-1).url,'https://test.invalid');assert.equal(u.searchParams.get('level'),'subdivisions');assert.equal(u.searchParams.get('parent'),'010100');assert.equal(u.searchParams.get('offset'),'1');
});
await scenario('SH6 propose le niveau détaillé sans changer la projection disponible',async({w,host,appels,button,reponse})=>{
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  reponse(envelope({type_rapport:'navigation_tarifaire_documentaire',niveau:'sh6',niveau_suivant:'codes',niveau_suivant_detaille:'subdivisions',enfants_declares:[{code:'010100'}]}));
  button('Contrôler').click();await tick();button('Enfants de 010100').click();await tick();
  assert.equal(new URL(appels.at(-1).url,'https://test.invalid').searchParams.get('level'),'subdivisions');
  assert([...host.querySelector('[data-tree-level]').options].some(o=>o.value==='codes'));
});
await scenario('diff articles : IDs/champ exacts et suites indépendantes Unicode',async({host,appels,button,reponse})=>{
  host.querySelector('[data-diff-before]').value='AV & عربي';host.querySelector('[data-diff-after]').value='AP';
  const bloc=(texte)=>({decalage_dans_bloc:0,fragment_bloc_different:texte,total_caracteres_bloc_different:9,decalage_suivant:Array.from(texte).length});
  reponse(envelope({type_rapport:'comparaison_litterale_versions_article',champs_comparables:true,
    avant_id_exact:'AV & عربي',apres_id_exact:'AP',champ_texte:'texte_arabe',unite_decalage:'points_de_code_unicode_python',
    limite:4,avant:bloc('أ😀'),apres:bloc('TEST')}));
  button('Comparer les deux versions exactes').click();await tick();
  let u=new URL(appels.at(-1).url,'https://test.invalid');assert.equal(u.searchParams.get('avant_id'),'AV & عربي');
  button('Suite du bloc avant').click();await tick();u=new URL(appels.at(-1).url,'https://test.invalid');
  assert.equal(u.searchParams.get('offset_avant'),'2');assert.equal(u.searchParams.get('offset_apres'),'0');assert.equal(u.searchParams.get('field'),'texte_arabe');
});
await scenario('diff articles : absence de champ ne propose pas de suite',async({host,button,reponse})=>{
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';
  reponse(envelope({type_rapport:'comparaison_litterale_versions_article',champs_comparables:false,textes_identiques:null}));
  button('Comparer les deux versions exactes').click();await tick();assert(!button('Suite du bloc'));
});
await scenario('diff articles : IDs requis et tarif refusé sans lecture',async({w,host,appels,button})=>{
  let n=appels.length;button('Comparer les deux versions exactes').click();await tick();assert.equal(appels.length,n);
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';
  button('Comparer les deux versions exactes').click();await tick();assert.equal(appels.length,n);
});
await scenario('diff articles : audit indisponible efface le rapport',async({host,button,reponse})=>{
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';
  reponse(envelope({type_rapport:'comparaison_litterale_versions_article',texte:'NON OFFICIEL'}));
  button('Comparer les deux versions exactes').click();await tick();
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Comparer les deux versions exactes').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const codeRapport = (source, chemin, enfants, extra={}) => envelope({type_rapport:'navigation_code_documentaire',source_id_exact:source,
  chemin_exact:chemin,parent_trouve:source===null?null:true,enfants_declares:enfants,limite:20,decalage:0,decalage_suivant:null,...extra});
await scenario('Code hiérarchie : documents puis niveaux exacts puis lecture',async({host,appels,button,reponse})=>{
  reponse(codeRapport(null,[],[{type_noeud:'document',source_id:'SRC & عربي'}]));
  button('Parcourir la hiérarchie du Code').click();await tick();
  reponse(codeRapport('SRC & عربي',[],[{type_noeud:'niveau_declare',chemin:[{niveau:'texte_legislatif',identifiant:'T'}]}]));
  button('Parcourir le document SRC').click();await tick();assert.equal(new URL(appels.at(-1).url,'https://x').searchParams.get('source_id'),'SRC & عربي');
  reponse(codeRapport('SRC & عربي',[{niveau:'texte_legislatif',identifiant:'T'}],[{type_noeud:'version_article',version_declaree:{id:'VERSION',reference:{source_id:'SRC & عربي'}}}]));
  button('Parcourir le niveau T').click();await tick();button('Lire la version VERSION').click();await tick();
  assert.equal(new URL(appels.at(-1).url,'https://x').searchParams.get('article_id'),'VERSION');
});
await scenario('Code hiérarchie : pagination et remontée conservent chemin et source',async({host,appels,button,reponse})=>{
  const chemin=[{niveau:'texte_legislatif',identifiant:'T'},{niveau:'article',identifiant:'5 bis'}];
  reponse(codeRapport('SRC',chemin,[],{limite:1,decalage:0,decalage_suivant:1,total_enfants_declares:3}));
  button('Parcourir la hiérarchie du Code').click();await tick();button('Page suivante des enfants Code').click();await tick();
  let u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('offset'),'1');assert.deepEqual(JSON.parse(u.searchParams.get('path')),chemin);
  button('Remonter la hiérarchie du Code').click();await tick();u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('offset'),'0');assert.deepEqual(JSON.parse(u.searchParams.get('path')),chemin.slice(0,1));
});
await scenario('Code hiérarchie : chemins incohérents et source étrangère sans action',async({button,reponse})=>{
  reponse(codeRapport('SRC',[{niveau:'titre',identifiant:'I'}],[
    {type_noeud:'niveau_declare',chemin:[{niveau:'titre',identifiant:'II'},{niveau:'article',identifiant:'1'}]},
    {type_noeud:'version_article',version_declaree:{id:'ETRANGER',reference:{source_id:'AUTRE'}}}]));
  button('Parcourir la hiérarchie du Code').click();await tick();assert(!button('Parcourir le niveau'));assert(!button('Lire la version'));
});
await scenario('Code hiérarchie : JSON invalide, source manquante et tarif sans lecture',async({w,host,appels,button})=>{
  let n=appels.length;host.querySelector('[data-code-tree-path]').value='{';button('Parcourir la hiérarchie du Code').click();await tick();assert.equal(appels.length,n);
  host.querySelector('[data-code-tree-path]').value='[{"niveau":"titre","identifiant":"I"}]';button('Parcourir la hiérarchie du Code').click();await tick();assert.equal(appels.length,n);
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  button('Parcourir la hiérarchie du Code').click();await tick();assert.equal(appels.length,n);
});
await scenario('Code hiérarchie : ancienne action inerte après changement de lot',async({w,host,appels,button,reponse})=>{
  reponse(codeRapport(null,[],[{type_noeud:'document',source_id:'SRC'}]));button('Parcourir la hiérarchie du Code').click();await tick();
  const ancien=button('Parcourir le document SRC');let n=appels.length;const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  ancien.click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
await scenario('Code hiérarchie : audit 503 efface rapport et actions',async({host,button,reponse})=>{
  reponse(codeRapport(null,[],[{type_noeud:'document',source_id:'SRC'}]));button('Parcourir la hiérarchie du Code').click();await tick();
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Parcourir la hiérarchie du Code').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const matchRapport = extra => envelope({type_rapport:'rapprochement_litteral_fragment_article_pdf',
  article_id_exact:'VERSION',article_trouve:true,texte_renseigne:true,champ_texte:'texte_integral',
  unite_decalage:'points_de_code_unicode_python',limite:4,decalage:0,decalage_suivant:null,total_caracteres_article:2,
  fragment_article:'أ😀',page_physique_demandee:2,extraction_effectuee:true,fragment_present_litteralement:true,
  document_declare:{id:'SRC',sha256:'b'.repeat(64)},sha256_pdf_lu:'b'.repeat(64),position_debut_pdf:5,...extra});
await scenario('Rapprochement : paramètres exacts, source imposée et lecture de la page',async({host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='VERSION عربي';host.querySelector('[data-match-page]').value='2';
  host.querySelector('[data-pdf-id]').value='AUTRE';reponse(matchRapport({}));
  button('Rapprocher le fragment').click();await tick();let u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('article_id'),'VERSION عربي');assert.equal(u.searchParams.get('page'),'2');assert(!u.searchParams.has('document_id'));
  button('Lire la page PDF rapprochée').click();await tick();u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('document_id'),'SRC');assert.equal(u.searchParams.get('page'),'2');assert.equal(u.searchParams.get('offset'),'5');
});
await scenario('Rapprochement : suite Unicode conserve page et fragment',async({host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='VERSION';reponse(matchRapport({decalage_suivant:2,total_caracteres_article:8}));
  button('Rapprocher le fragment').click();await tick();button('Fragment suivant à rapprocher').click();await tick();
  const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('offset'),'2');assert.equal(u.searchParams.get('page'),'2');assert.equal(u.searchParams.get('limit'),'4');
});
await scenario('Rapprochement : indisponibilité reste indéterminée et rendu sans HTML',async({host,button,reponse})=>{
  host.querySelector('[data-read-id]').value='VERSION';
  reponse(matchRapport({fragment_article:'<img src=x onerror=alert(1)>',fragment_present_litteralement:null,
    extraction_effectuee:false,sha256_pdf_lu:null,constat:'champ_absent',transcription_verification:'non_verifiee'}));
  button('Rapprocher le fragment').click();await tick();assert(!button('Lire la page PDF rapprochée'));
  assert(!host.querySelector('img'));assert(host.querySelector('pre').textContent.includes('non_verifiee'));
});
await scenario('Rapprochement : IDs/page invalides et tarif sans requête',async({w,host,appels,button})=>{
  const n=appels.length;button('Rapprocher le fragment').click();await tick();assert.equal(appels.length,n);
  host.querySelector('[data-read-id]').value='VERSION';host.querySelector('[data-match-page]').value='0';
  button('Rapprocher le fragment').click();await tick();assert.equal(appels.length,n);
  const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-match-page]').value='1';button('Rapprocher le fragment').click();await tick();assert.equal(appels.length,n);
});
await scenario('Rapprochement : ancienne action inerte après changement de lot',async({w,host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='VERSION';reponse(matchRapport({}));button('Rapprocher le fragment').click();await tick();
  const ancien=button('Lire la page PDF rapprochée'),n=appels.length;const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  ancien.click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
await scenario('Rapprochement : panne audit efface fragment et actions',async({host,button,reponse})=>{
  host.querySelector('[data-read-id]').value='VERSION';reponse(matchRapport({}));button('Rapprocher le fragment').click();await tick();
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Rapprocher le fragment').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const scenarioInter=(nom,action)=>scenario(nom,action,[lot('test-code'),lot('test-tarif','tarif'),lot('code-b')]);
const interRapport=extra=>envelope({type_rapport:'comparaison_litterale_versions_article_inter_lots',champs_comparables:true,
  lots_exacts:{avant:'test-code',apres:'code-b'},avant_id_exact:'AV',apres_id_exact:'AP',champ_texte:'texte_arabe',
  unite_decalage:'points_de_code_unicode_python',limite:4,
  avant:{decalage_dans_bloc:0,fragment_bloc_different:'أ😀',total_caracteres_bloc_different:9,decalage_suivant:2},
  apres:{decalage_dans_bloc:0,fragment_bloc_different:'TEST',total_caracteres_bloc_different:9,decalage_suivant:4},...extra});
await scenarioInter('Diff inter-lots : deux lots et deux IDs exacts encodés',async({w,host,appels,button,reponse})=>{
  const b=host.querySelector('[data-comparison-after-lot]');b.value='code-b';b.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV & عربي';host.querySelector('[data-diff-after]').value='AP';reponse(interRapport({}));
  button('Comparer les versions entre deux lots').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.pathname,'/api/v1/customs-review/article-diff');assert.equal(u.searchParams.get('avant'),'test-code');
  assert.equal(u.searchParams.get('apres'),'code-b');assert.equal(u.searchParams.get('avant_id'),'AV & عربي');
});
await scenarioInter('Diff inter-lots : suite indépendante conserve paire et Unicode',async({w,host,appels,button,reponse})=>{
  const b=host.querySelector('[data-comparison-after-lot]');b.value='code-b';b.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';reponse(interRapport({}));
  button('Comparer les versions entre deux lots').click();await tick();button('Suite du bloc avant').click();await tick();
  const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('apres'),'code-b');
  assert.equal(u.searchParams.get('offset_avant'),'2');assert.equal(u.searchParams.get('offset_apres'),'0');assert.equal(u.searchParams.get('field'),'texte_arabe');
});
await scenarioInter('Diff inter-lots : tarif et paire incohérente sans action',async({w,host,appels,button,reponse})=>{
  const b=host.querySelector('[data-comparison-after-lot]');b.value='test-tarif';b.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';let n=appels.length;
  button('Comparer les versions entre deux lots').click();await tick();assert.equal(appels.length,n);
  b.value='code-b';b.dispatchEvent(new w.Event('change'));reponse(interRapport({lots_exacts:{avant:'test-code',apres:'test-tarif'}}));
  button('Comparer les versions entre deux lots').click();await tick();assert(!button('Suite du bloc'));
});
await scenarioInter('Diff inter-lots : changement du lot après efface et invalide les suites',async({w,host,appels,button,reponse})=>{
  const b=host.querySelector('[data-comparison-after-lot]');b.value='code-b';b.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';reponse(interRapport({}));
  button('Comparer les versions entre deux lots').click();await tick();const ancien=button('Suite du bloc avant'),n=appels.length;
  b.value='test-code';b.dispatchEvent(new w.Event('change'));ancien.click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('pre').textContent,'');
});
await scenarioInter('Diff inter-lots : réponse tardive ignorée après changement du lot après',async({w,host,button,attendre})=>{
  const b=host.querySelector('[data-comparison-after-lot]');b.value='code-b';b.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';let terminer;
  attendre(()=>new Promise(r=>{terminer=r;}));button('Comparer les versions entre deux lots').click();
  b.value='test-code';b.dispatchEvent(new w.Event('change'));terminer({ok:true,status:200,json:async()=>interRapport({})});await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert(!button('Suite du bloc'));
});
await scenarioInter('Diff inter-lots : panne audit sans ancien résultat',async({host,button,reponse})=>{
  host.querySelector('[data-comparison-after-lot]').value='code-b';host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';
  reponse(interRapport({}));button('Comparer les versions entre deux lots').click();await tick();
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Comparer les versions entre deux lots').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
await scenarioInter('Diff inter-lots : lecture du côté après utilise son lot et son ID',async({host,appels,button,reponse})=>{
  host.querySelector('[data-comparison-after-lot]').value='code-b';host.querySelector('[data-diff-before]').value='AV';host.querySelector('[data-diff-after]').value='AP';
  reponse(interRapport({apres:{version_declaree:{id:'AP'}}}));button('Comparer les versions entre deux lots').click();await tick();
  button('Lire la version apres du lot code-b').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.pathname,'/api/v1/customs-review/lots/code-b/article');assert.equal(u.searchParams.get('article_id'),'AP');assert.equal(host.querySelector('select').value,'code-b');
});
const relationsRapport=extra=>envelope({type_rapport:'relations_documentaires_version_article',article_trouve:true,article_id_exact:'V',
  version_declaree:{id:'V',reference:{source_id:'SEL'}},sens:'tous',type_relation_filtre:null,limite:20,decalage:0,decalage_suivant:null,total_relations_filtrees:1,
  documents_declares_page:[{id:'SRC',sha256:'a'.repeat(64)}],relations_declarees:[{relation_declaree:{id:'R',origine_id:'AUTRE',cible_id:'V',type_relation:'modifie',
    justification:'<img src=x onerror=alert(1)>',reference:{source_id:'SRC',localisateur:'Page imprimée 9, pas physique'}},
    sens_par_rapport_a_version:'entrante',autre_version_declaree:{id:'AUTRE',reference:{source_id:'SRC'}}}],...extra});
await scenario('Relations exactes : filtres encodés, justification safe et PDF preuve page 1',async({host,appels,button,reponse})=>{
  host.querySelector('[data-relations-id]').value='V & عربي';host.querySelector('[data-relations-direction]').value='entrantes';host.querySelector('[data-relations-type]').value='modifie';
  reponse(relationsRapport({}));button('Inspecter les relations déclarées').click();await tick();let u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('article_id'),'V & عربي');assert.equal(u.searchParams.get('direction'),'entrantes');assert.equal(u.searchParams.get('relation_type'),'modifie');
  assert(!host.querySelector('img'));button('Lire le PDF de preuve SRC').click();await tick();u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('document_id'),'SRC');assert.equal(u.searchParams.get('page'),'1');
});
await scenario('Relations exactes : ouverture de l’autre version et dédoublonnage',async({host,appels,button,reponse})=>{
  host.querySelector('[data-relations-id]').value='V';const r=relationsRapport({}).resultat; r.relations_declarees.push({...r.relations_declarees[0],relation_declaree:{...r.relations_declarees[0].relation_declaree,id:'R2'}});
  reponse(envelope(r));button('Inspecter les relations déclarées').click();await tick();
  assert.equal([...host.querySelectorAll('button')].filter(b=>b.textContent==='Lire la version AUTRE').length,1);
  button('Lire la version AUTRE').click();await tick();assert.equal(new URL(appels.at(-1).url,'https://x').searchParams.get('article_id'),'AUTRE');
});
await scenario('Relations exactes : pagination conserve version, direction et type',async({host,appels,button,reponse})=>{
  host.querySelector('[data-relations-id]').value='V';reponse(relationsRapport({sens:'entrantes',type_relation_filtre:'modifie',limite:1,decalage_suivant:1,total_relations_filtrees:3}));
  button('Inspecter les relations déclarées').click();await tick();button('Page suivante des relations déclarées').click();await tick();
  const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('article_id'),'V');assert.equal(u.searchParams.get('offset'),'1');
  assert.equal(u.searchParams.get('direction'),'entrantes');assert.equal(u.searchParams.get('relation_type'),'modifie');assert.equal(u.searchParams.get('limit'),'1');
});
await scenario('Relations exactes : lien non incident ou filtre contradictoire sans action',async({host,button,reponse})=>{
  host.querySelector('[data-relations-id]').value='V';reponse(relationsRapport({sens:'sortantes'}));
  button('Inspecter les relations déclarées').click();await tick();assert(!button('Lire la version AUTRE'));assert(!button('Lire le PDF de preuve'));
  const r=relationsRapport({}).resultat;r.relations_declarees[0].relation_declaree.cible_id='ETRANGER';reponse(envelope(r));
  button('Inspecter les relations déclarées').click();await tick();assert(!button('Lire la version AUTRE'));
});
await scenario('Relations exactes : ID requis, tarif refusé et ancienne preuve inerte',async({w,host,appels,button,reponse})=>{
  let n=appels.length;button('Inspecter les relations déclarées').click();await tick();assert.equal(appels.length,n);
  host.querySelector('[data-relations-id]').value='V';reponse(relationsRapport({}));button('Inspecter les relations déclarées').click();await tick();
  const ancien=button('Lire le PDF de preuve SRC');n=appels.length;const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  ancien.click();button('Inspecter les relations déclarées').click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
await scenario('Relations exactes : lecture d’article propose inspection puis panne audit efface',async({host,appels,button,reponse})=>{
  host.querySelector('[data-read-id]').value='V';reponse(envelope({type_rapport:'lecture_article_documentaire',article_trouve:true,article_id_exact:'V'}));
  button('Lire le fragment').click();await tick();reponse(relationsRapport({}));button('Inspecter les relations de cette version').click();await tick();
  assert.equal(new URL(appels.at(-1).url,'https://x').searchParams.get('article_id'),'V');
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Inspecter les relations déclarées').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const justificationRapport=extra=>envelope({type_rapport:'rapprochement_litteral_justification_relation_pdf',relation_id_exact:'R',relation_trouvee:true,
  fragment_justification:'أ😀',limite:4,decalage:0,decalage_suivant:2,total_caracteres_justification:8,page_physique_demandee:2,
  unite_decalage:'points_de_code_unicode_python',extraction_effectuee:true,document_declare:{id:'SRC',sha256:'a'.repeat(64)},
  sha256_pdf_lu:'a'.repeat(64),position_debut_pdf:5,preuve_juridique_verifiee:false,...extra});
await scenario('Justification : préparation depuis relation sans extraction ni page déduite',async({host,appels,button,reponse})=>{
  host.querySelector('[data-relations-id]').value='V';reponse(relationsRapport({}));button('Inspecter les relations déclarées').click();await tick();
  const n=appels.length;button('Préparer le rapprochement de justification R').click();await tick();assert.equal(appels.length,n);
  assert.equal(host.querySelector('[data-justification-id]').value,'R');assert.equal(host.querySelector('[data-justification-page]').value,'1');
});
await scenario('Justification : paramètres exacts, source imposée et page rapprochée',async({host,appels,button,reponse})=>{
  host.querySelector('[data-justification-id]').value='R & عربي';host.querySelector('[data-justification-page]').value='2';
  reponse(justificationRapport({}));button('Rapprocher la justification avec').click();await tick();let u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('relation_id'),'R & عربي');assert.equal(u.searchParams.get('page'),'2');assert(!u.searchParams.has('document_id'));
  button('Lire la page PDF rapprochée').click();await tick();u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('document_id'),'SRC');assert.equal(u.searchParams.get('offset'),'5');assert.equal(u.searchParams.get('page'),'2');
});
await scenario('Justification : suite Unicode conserve relation et page',async({host,appels,button,reponse})=>{
  host.querySelector('[data-justification-id]').value='R';reponse(justificationRapport({}));button('Rapprocher la justification avec').click();await tick();
  button('Justification suivante à rapprocher').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
  assert.equal(u.searchParams.get('offset'),'2');assert.equal(u.searchParams.get('page'),'2');assert.equal(u.searchParams.get('relation_id'),'R');
});
await scenario('Justification : indisponibilité et HTML sans preuve validée',async({host,button,reponse})=>{
  host.querySelector('[data-justification-id]').value='R';reponse(justificationRapport({fragment_justification:'<img src=x onerror=alert(1)>',
    extraction_effectuee:false,sha256_pdf_lu:null,fragment_present_litteralement:null,decalage_suivant:null}));
  button('Rapprocher la justification avec').click();await tick();assert(!host.querySelector('img'));assert(!button('Lire la page PDF rapprochée'));
  assert(host.querySelector('pre').textContent.includes('"preuve_juridique_verifiee": false'));
});
await scenario('Justification : invalides, tarif et anciennes actions sans lecture',async({w,host,appels,button,reponse})=>{
  let n=appels.length;button('Rapprocher la justification avec').click();await tick();assert.equal(appels.length,n);
  host.querySelector('[data-justification-id]').value='R';host.querySelector('[data-justification-page]').value='0';button('Rapprocher la justification avec').click();await tick();assert.equal(appels.length,n);
  host.querySelector('[data-justification-page]').value='1';reponse(justificationRapport({}));button('Rapprocher la justification avec').click();await tick();
  const ancien=button('Justification suivante');n=appels.length;const lot=host.querySelector('select');lot.value='test-tarif';lot.dispatchEvent(new w.Event('change'));
  ancien.click();button('Rapprocher la justification avec').click();await tick();assert.equal(appels.length,n);
});
await scenario('Justification : panne audit efface résultat et actions',async({host,button,reponse})=>{
  host.querySelector('[data-justification-id]').value='R';reponse(justificationRapport({}));button('Rapprocher la justification avec').click();await tick();
  reponse({detail:{code:'audit_revue_indisponible'}},503);button('Rapprocher la justification avec').click();await tick();
  assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const scenarioPaire=(nom,action)=>scenario(nom,action,[lot('test-code'),lot('test-tarif','tarif'),lot('tarif-b','tarif')]);
function choisirPaire(w,host) {const a=host.querySelector('select'),b=host.querySelector('[data-comparison-after-lot]');
 a.value='test-tarif';a.dispatchEvent(new w.Event('change'));b.value='tarif-b';b.dispatchEvent(new w.Event('change'));host.querySelector('[data-code10]').value='0101000000';}
const paireRapport=extra=>envelope({type_rapport:'juxtaposition_documentaire_fiches_tarifaires',code_tarifaire_10_exact:'0101000000',
 lots_exacts:{avant:'test-tarif',apres:'tarif-b'},avant:{ligne_trouvee:true,ligne_declaree:{code_tarifaire_10:'0101000000'},limite_mesures:1,decalage_mesures:0,decalage_mesures_suivant:1,total_mesures_declarees:4},
 apres:{ligne_trouvee:true,ligne_declaree:{code_tarifaire_10:'0101000000'},limite_mesures:2,decalage_mesures:2,decalage_mesures_suivant:null,total_mesures_declarees:4},...extra});
await scenarioPaire('Fiches séparées : code chaîne et paginations exactes',async({w,host,appels,button,reponse})=>{
 choisirPaire(w,host);host.querySelector('[data-measures-limit]').value='1';host.querySelector('[data-pair-after-limit]').value='2';host.querySelector('[data-pair-after-offset]').value='2';
 reponse(paireRapport({}));button('Consulter les deux fiches').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/tariff-compare');assert.equal(u.searchParams.get('code10'),'0101000000');assert.equal(u.searchParams.get('apres'),'tarif-b');assert.equal(u.searchParams.get('before_limit'),'1');assert.equal(u.searchParams.get('after_offset'),'2');
});
await scenarioPaire('Fiches séparées : suite avant conserve pagination après',async({w,host,appels,button,reponse})=>{
 choisirPaire(w,host);reponse(paireRapport({}));button('Consulter les deux fiches').click();await tick();button('Mesures suivantes côté avant').click();await tick();
 const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('before_offset'),'1');assert.equal(u.searchParams.get('after_offset'),'2');assert.equal(u.searchParams.get('after_limit'),'2');
});
await scenarioPaire('Fiches séparées : ouvrir côté après respecte lot et code',async({w,host,appels,button,reponse})=>{
 choisirPaire(w,host);reponse(paireRapport({}));button('Consulter les deux fiches').click();await tick();button('Fiche apres du lot tarif-b').click();await tick();
 const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.pathname,'/api/v1/customs-review/lots/tarif-b/tariff/0101000000');assert.equal(host.querySelector('select').value,'tarif-b');
});
await scenarioPaire('Fiches séparées : code invalide ou lot Code sans requête',async({w,host,appels,button})=>{
 choisirPaire(w,host);host.querySelector('[data-code10]').value='٠١٠١٠٠٠٠٠٠';let n=appels.length;button('Consulter les deux fiches').click();await tick();assert.equal(appels.length,n);
 host.querySelector('[data-code10]').value='0101000000';host.querySelector('[data-comparison-after-lot]').value='test-code';button('Consulter les deux fiches').click();await tick();assert.equal(appels.length,n);
});
await scenarioPaire('Fiches séparées : paire incohérente et code numérique sans actions',async({w,host,button,reponse})=>{
 choisirPaire(w,host);reponse(paireRapport({lots_exacts:{avant:'test-tarif',apres:'test-code'}}));button('Consulter les deux fiches').click();await tick();assert(!button('Fiche apres du lot'));assert(!button('Mesures suivantes côté'));
 reponse(paireRapport({code_tarifaire_10_exact:1010000000}));button('Consulter les deux fiches').click();await tick();assert(!button('Mesures suivantes côté'));
});
await scenarioPaire('Fiches séparées : changement du lot après invalide la suite',async({w,host,appels,button,reponse})=>{
 choisirPaire(w,host);reponse(paireRapport({}));button('Consulter les deux fiches').click();await tick();const ancien=button('Mesures suivantes côté avant'),n=appels.length;
 const b=host.querySelector('[data-comparison-after-lot]');b.value='test-tarif';b.dispatchEvent(new w.Event('change'));ancien.click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('pre').textContent,'');
});
await scenarioPaire('Fiches séparées : audit 503 efface les deux fiches',async({w,host,button,reponse})=>{
 choisirPaire(w,host);reponse(paireRapport({}));button('Consulter les deux fiches').click();await tick();reponse({detail:{code:'audit_revue_indisponible'}},503);
 button('Consulter les deux fiches').click();await tick();assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const mesuresRapport=extra=>envelope({type_recherche:'mesures_tarifaires_documentaires',requete:'معدات',filtres:{code10_exact:'0101000000',type_mesure:'restriction'},
 limite:1,decalage:0,decalage_suivant:1,total_correspondances:3,resultats:[{mesure_declaree:{code_tarifaire_10:'0101000000',description:'<img src=x onerror=alert(1)>'},ligne_declaree:{code_tarifaire_10:'0101000000'}}],...extra});
await scenario('Recherche mesures : texte AR et filtres exacts, rendu sans HTML',async({w,host,appels,button,reponse})=>{
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));
 host.querySelector('[data-measure-query]').value='معدات';host.querySelector('[data-measure-code]').value='0101000000';host.querySelector('[data-measure-type]').value='restriction';
 reponse(mesuresRapport({}));button('Rechercher dans les mesures').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/lots/test-tarif/measure-search');assert.equal(u.searchParams.get('q'),'معدات');assert.equal(u.searchParams.get('code10'),'0101000000');assert.equal(u.searchParams.get('measure_type'),'restriction');assert(!host.querySelector('img'));
});
await scenario('Recherche mesures : suite conserve réponse et filtres',async({w,host,appels,button,reponse})=>{
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));host.querySelector('[data-measure-type]').value='restriction';
 reponse(mesuresRapport({}));button('Rechercher dans les mesures').click();await tick();host.querySelector('[data-measure-query]').value='AUTRE';
 button('Page suivante des mesures trouvées').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.searchParams.get('q'),'معدات');assert.equal(u.searchParams.get('code10'),'0101000000');assert.equal(u.searchParams.get('offset'),'1');assert.equal(u.searchParams.get('limit'),'1');
});
await scenario('Recherche mesures : fiche du code source sans doublons',async({w,host,appels,button,reponse})=>{
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));host.querySelector('[data-measure-type]').value='restriction';
 const r=mesuresRapport({}).resultat;r.resultats.push(r.resultats[0]);reponse(envelope(r));button('Rechercher dans les mesures').click();await tick();
 assert.equal([...host.querySelectorAll('button')].filter(b=>b.textContent==='Fiche documentaire 0101000000').length,1);
 button('Fiche documentaire 0101000000').click();await tick();assert.equal(new URL(appels.at(-1).url,'https://x').pathname,'/api/v1/customs-review/lots/test-tarif/tariff/0101000000');
});
await scenario('Recherche mesures : requête/filtre requis et code ASCII exact',async({w,host,appels,button})=>{
 let n=appels.length;button('Rechercher dans les mesures').click();await tick();assert.equal(appels.length,n);
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));button('Rechercher dans les mesures').click();await tick();assert.equal(appels.length,n);
 host.querySelector('[data-measure-code]').value='٠١٠١٠٠٠٠٠٠';button('Rechercher dans les mesures').click();await tick();assert.equal(appels.length,n);
});
await scenario('Recherche mesures : action ancienne inerte sur Code',async({w,host,appels,button,reponse})=>{
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));host.querySelector('[data-measure-type]').value='restriction';
 reponse(mesuresRapport({}));button('Rechercher dans les mesures').click();await tick();const ancien=button('Page suivante des mesures trouvées'),n=appels.length;
 l.value='test-code';l.dispatchEvent(new w.Event('change'));ancien.click();button('Rechercher dans les mesures').click();await tick();assert.equal(appels.length,n);assert.equal(host.querySelector('pre').textContent,'');
});
await scenario('Recherche mesures : audit indisponible sans ancien résultat',async({w,host,button,reponse})=>{
 const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));host.querySelector('[data-measure-type]').value='restriction';
 reponse(mesuresRapport({}));button('Rechercher dans les mesures').click();await tick();reponse({detail:{code:'audit_revue_indisponible'}},503);
 button('Rechercher dans les mesures').click();await tick();assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
const extraitRecherche=extra=>({champ_texte:'texte_francais',terme_normalise:'equipement',unite_decalage:'points_de_code_unicode_python',
 decalage:700,fragment:'😀 Équipement <img src=x>',total_caracteres:1200,correspondance_debut:702,correspondance_fin:712,correspondance_entierement_visible:true,...extra});
const rechercheExtraits=extraits=>envelope({type_recherche:'code_documentaire',termes_normalises:['equipement'],resultats:[{id:'VERSION_EXACTE',extraits_correspondants:extraits}]});
await scenario('Extraits Code : contexte sûr et ouverture Unicode exacte',async({w,host,appels,button,reponse})=>{
 const ex=extraitRecherche({});reponse(rechercheExtraits([ex]));host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 assert.equal(host.querySelector('blockquote').textContent,ex.fragment);assert(!host.querySelector('img'));assert.equal(host.querySelector('blockquote').dir,'auto');
 button('Lire le passage VERSION_EXACTE').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.searchParams.get('article_id'),'VERSION_EXACTE');assert.equal(u.searchParams.get('field'),'texte_francais');assert.equal(u.searchParams.get('offset'),'700');assert.equal(u.searchParams.get('limit'),String(Array.from(ex.fragment).length));
});
await scenario('Extraits Code : titre visible mais sans lecture de champ interdit',async({w,host,button,reponse})=>{
 reponse(rechercheExtraits([extraitRecherche({champ_texte:'intitule'})]));host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 assert(host.querySelector('blockquote'));assert(!button('Lire le passage'));assert(button('Lire la version VERSION_EXACTE'));
});
await scenario('Extraits Code : positions incohérentes et terme étranger ignorés',async({w,host,button,reponse})=>{
 reponse(rechercheExtraits([extraitRecherche({decalage:'700'}),extraitRecherche({unite_decalage:'UTF16'}),extraitRecherche({terme_normalise:'invente'}),extraitRecherche({correspondance_fin:701})]));
 host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();assert(!host.querySelector('blockquote'));assert(!button('Lire le passage'));
});
await scenario('Extraits Code : un seul contexte par champ et limite de taille',async({w,host,button,reponse})=>{
 reponse(rechercheExtraits([extraitRecherche({fragment:'x'.repeat(385)}),extraitRecherche({}),extraitRecherche({})]));
 host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();assert.equal(host.querySelectorAll('blockquote').length,1);
 assert.equal([...host.querySelectorAll('button')].filter(b=>b.textContent.includes('Lire le passage')).length,1);
});
await scenario('Extraits Code : ancienne ouverture inerte après changement de lot',async({w,host,appels,button,reponse})=>{
 reponse(rechercheExtraits([extraitRecherche({})]));host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 const ancien=button('Lire le passage'),n=appels.length,l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));ancien.click();await tick();assert.equal(appels.length,n);assert(!host.querySelector('blockquote'));
});
await scenario('Extraits Code : audit indisponible efface contextes et actions',async({w,host,button,reponse})=>{
 reponse(rechercheExtraits([extraitRecherche({})]));host.querySelector('input').value='equipement';host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 reponse({detail:{code:'audit_revue_indisponible'}},503);button('Lire le passage').click();await tick();assert(!host.querySelector('blockquote'));assert.equal(host.querySelector('pre').textContent,'');
});
const catalogueSources=extra=>envelope({type_recherche:'sources_documentaires',type_lot:'code',requete:'معدات',filtres:{source_id_exact:null,nature_document:null},
 limite:1,decalage:0,decalage_suivant:1,total_correspondances:3,resultats:[{source_declaree:{id:'SOURCE_1',sha256:'a'.repeat(64),nature_document:'code_original',format:'pdf',titre:'<img src=x>',url:'https://externe.invalid'}}],...extra});
await scenario('Sources : paramètres FR/AR et filtres encodés sans HTML',async({host,appels,button,reponse})=>{
 host.querySelector('[data-sources-query]').value='معدات';host.querySelector('[data-sources-id]').value='ID / &';host.querySelector('[data-sources-nature]').value='code_original';
 reponse(catalogueSources({}));button('Inventorier les sources').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/sources');assert.equal(u.searchParams.get('q'),'معدات');assert.equal(u.searchParams.get('source_id'),'ID / &');assert.equal(u.searchParams.get('nature_document'),'code_original');assert(!host.querySelector('img'));
});
await scenario('Sources : suite reprend les filtres de la réponse',async({host,appels,button,reponse})=>{
 reponse(catalogueSources({filtres:{source_id_exact:'SOURCE_1',nature_document:'code_original'}}));button('Inventorier les sources').click();await tick();host.querySelector('[data-sources-query]').value='AUTRE';
 button('Page suivante des sources').click();await tick();const u=new URL(appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('q'),'معدات');assert.equal(u.searchParams.get('source_id'),'SOURCE_1');assert.equal(u.searchParams.get('offset'),'1');
});
await scenario('Sources : lecture PDF dans le lot local sans URL externe',async({host,appels,button,reponse})=>{
 reponse(catalogueSources({}));button('Inventorier les sources').click();await tick();button('Lire la source PDF SOURCE_1').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/pdf');assert.equal(u.searchParams.get('document_id'),'SOURCE_1');assert.equal(u.searchParams.get('page'),'1');assert.equal(u.searchParams.get('offset'),'0');
});
await scenario('Sources : articles par source et chemin racine exact',async({host,appels,button,reponse})=>{
 reponse(catalogueSources({}));button('Inventorier les sources').click();await tick();button('Articles de la source SOURCE_1').click();await tick();const u=new URL(appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/code-tree');assert.equal(u.searchParams.get('source_id'),'SOURCE_1');assert.equal(u.searchParams.get('path'),'[]');assert.equal(u.searchParams.get('offset'),'0');
});
await scenario('Sources : tarif sans nature Code ou action PDF',async({w,host,appels,button,reponse})=>{
 host.querySelector('[data-sources-nature]').value='compilation';const l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));
 reponse(catalogueSources({type_lot:'tarif'}));button('Inventorier les sources').click();await tick();const u=new URL(appels.at(-1).url,'https://x');assert(!u.searchParams.has('nature_document'));
 assert(host.querySelector('[data-sources-nature]').disabled);assert(!button('Lire la source PDF'));assert(!button('Articles de la source'));
});
await scenario('Sources : filtre contradictoire et empreinte invalide sans action',async({host,button,reponse})=>{
 reponse(catalogueSources({filtres:{source_id_exact:'AUTRE',nature_document:null}}));button('Inventorier les sources').click();await tick();assert(!button('Lire la source PDF'));
 reponse(catalogueSources({resultats:[{source_declaree:{id:'SOURCE_1',sha256:'non_hash',nature_document:'code_original',format:'pdf'}}]}));button('Inventorier les sources').click();await tick();assert(!button('Articles de la source'));
});
await scenario('Sources : ancienne action inerte après changement de lot',async({w,host,appels,button,reponse})=>{
 reponse(catalogueSources({}));button('Inventorier les sources').click();await tick();const ancien=button('Lire la source PDF'),n=appels.length,l=host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new w.Event('change'));ancien.click();await tick();assert.equal(appels.length,n);
});
await scenario('Sources : panne audit efface inventaire et actions',async({host,button,reponse})=>{
 reponse(catalogueSources({}));button('Inventorier les sources').click();await tick();reponse({detail:{code:'audit_revue_indisponible'}},503);button('Inventorier les sources').click();await tick();assert.equal(host.querySelector('pre').textContent,'');assert.equal(host.querySelector('[data-review-actions]').textContent,'');
});
async function preparerCopiePDF(ctx) {
 const {w,host,button,reponse,attendre}=ctx,cryptoNode=require('node:crypto');
 const octets=Buffer.from('%PDF-1.7\nFIXTURE NON OFFICIELLE\n%%EOF');const sha=cryptoNode.createHash('sha256').update(octets).digest('hex');
 Object.defineProperty(w.crypto,'subtle',{value:cryptoNode.webcrypto.subtle,configurable:true});
 const fichiers=[];w.URL.createObjectURL=b=>{fichiers.push(b);return 'blob:source-test';};w.URL.revokeObjectURL=()=>{};
 let nom;w.HTMLAnchorElement.prototype.click=function(){nom=this.download;};
 reponse(catalogueSources({resultats:[{source_declaree:{id:'SOURCE_1',sha256:sha,nature_document:'code_original',format:'pdf'}}]}));button('Inventorier les sources').click();await tick();
 const entetes={'content-type':'application/pdf','content-length':String(octets.length),'x-uniocr-source-sha256':sha,'x-uniocr-manifest-sha256':'a'.repeat(64),'x-uniocr-validation':'non_validee'};
 const r={ok:true,status:200,headers:{get:k=>entetes[k.toLowerCase()] ?? null},arrayBuffer:async()=>octets.buffer.slice(octets.byteOffset,octets.byteOffset+octets.length)};
 attendre(()=>Promise.resolve(r));return {r,entetes,octets,sha,fichiers,nom:()=>nom};
}
const finirCopie=async()=>{for(let i=0;i<8;i++)await new Promise(r=>setTimeout(r,3));};
await scenario('Copie PDF : octets SHA256, nom sûr et requête locale',async ctx=>{
 const t=await preparerCopiePDF(ctx);ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,1);
 assert.equal(t.nom(),'uniocr-source-non-validee-'+t.sha+'.pdf');assert.equal(t.fichiers[0].size,t.octets.length);
 const u=new URL(ctx.appels.at(-1).url,'https://x');assert.equal(u.pathname,'/api/v1/customs-review/lots/test-code/pdf-source');assert.equal(u.searchParams.get('document_id'),'SOURCE_1');assert.equal(ctx.appels.at(-1).opts.headers.Accept,'application/pdf');
});
await scenario('Copie PDF : provenance étrangère sans téléchargement',async ctx=>{
 const t=await preparerCopiePDF(ctx);t.entetes['x-uniocr-manifest-sha256']='b'.repeat(64);ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,0);assert(ctx.status().includes('Provenance'));
});
await scenario('Copie PDF : contenu altéré malgré entêtes sans téléchargement',async ctx=>{
 const t=await preparerCopiePDF(ctx);t.octets[0]=33;ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,0);assert(ctx.status().includes('Empreinte PDF différente'));
});
await scenario('Copie PDF : limite annoncée refusée avant lecture',async ctx=>{
 const t=await preparerCopiePDF(ctx);t.entetes['content-length']=String(64*1024*1024+1);let lu=false;t.r.arrayBuffer=async()=>{lu=true;return new ArrayBuffer(1);};
 ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,0);assert.equal(lu,false);
});
await scenario('Copie PDF : audit 503 sans fichier ni ancien résultat',async ctx=>{
 const t=await preparerCopiePDF(ctx);t.r.ok=false;t.r.status=503;ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,0);assert.equal(ctx.host.querySelector('pre').textContent,'');assert(ctx.status().includes('audit'));
});
await scenario('Copie PDF : changement de lot pendant réception annule fichier',async ctx=>{
 const t=await preparerCopiePDF(ctx);let terminer;t.r.arrayBuffer=()=>new Promise(resolve=>{terminer=resolve;});ctx.button('Télécharger le PDF reçu').click();await tick();
 const l=ctx.host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new ctx.w.Event('change'));terminer(new ArrayBuffer(t.octets.length));await finirCopie();assert.equal(t.fichiers.length,0);
});
await scenario('Copie PDF : changement de compte pendant réception annule fichier',async ctx=>{
 const t=await preparerCopiePDF(ctx);let terminer;t.r.arrayBuffer=()=>new Promise(resolve=>{terminer=resolve;});ctx.button('Télécharger le PDF reçu').click();await tick();
 ctx.w.sessionStorage.setItem('uniocr_token','AUTRE');terminer(t.octets.buffer.slice(t.octets.byteOffset,t.octets.byteOffset+t.octets.length));await finirCopie();assert.equal(t.fichiers.length,0);assert(ctx.status().includes('Compte modifié'));
});
await scenario('Copie PDF : navigateur sans SHA256 refuse avant fetch',async ctx=>{
 const t=await preparerCopiePDF(ctx);Object.defineProperty(ctx.w.crypto,'subtle',{value:undefined});const n=ctx.appels.length;ctx.button('Télécharger le PDF reçu').click();await finirCopie();assert.equal(t.fichiers.length,0);assert.equal(ctx.appels.length,n);assert(ctx.status().includes('SHA256 navigateur indisponible'));
});
const lotsAvecMesures=[lot('test-code'),lot('test-tarif','tarif'),lot('test-mesures','mesures')];
function choisirMesures(ctx){const l=ctx.host.querySelector('select');l.value='test-mesures';l.dispatchEvent(new ctx.w.Event('change'));return l;}
const rapportMesuresAutonomes=()=>mesuresRapport({type_recherche:'mesures_autonomes_documentaires',type_lot:'mesures',resultats:[{mesure_declaree:{code_tarifaire_10:'0101000000'},ligne_declaree:null}]} );
await scenario('Mesures autonomes : registre reconnu et outils compatibles seulement',async ctx=>{
 choisirMesures(ctx);assert(ctx.host.querySelector('[data-read-id]').closest('fieldset').disabled);assert(ctx.host.querySelector('[data-pdf-id]').closest('fieldset').disabled);
 assert(ctx.host.querySelector('[data-measure-query]').closest('fieldset').disabled===false);assert(ctx.host.querySelector('form button').disabled);assert(ctx.host.querySelector('[data-sources-nature]').disabled);
},lotsAvecMesures);
await scenario('Mesures autonomes : recherche FR/AR sans fiche fabriquée',async ctx=>{
 choisirMesures(ctx);ctx.host.querySelector('[data-measure-query]').value='معدات';ctx.host.querySelector('[data-measure-code]').value='0101000000';ctx.reponse(rapportMesuresAutonomes());ctx.button('Rechercher dans les mesures').click();await tick();
 assert.equal(new URL(ctx.appels.at(-1).url,'https://x').pathname,'/api/v1/customs-review/lots/test-mesures/measure-search');assert(!ctx.button('Fiche documentaire'));
},lotsAvecMesures);
await scenario('Mesures autonomes : suite indépendante conserve filtres',async ctx=>{
 choisirMesures(ctx);ctx.host.querySelector('[data-measure-type]').value='restriction';ctx.reponse(rapportMesuresAutonomes());ctx.button('Rechercher dans les mesures').click();await tick();ctx.button('Page suivante des mesures trouvées').click();await tick();
 const u=new URL(ctx.appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('offset'),'1');assert.equal(u.searchParams.get('q'),'معدات');
},lotsAvecMesures);
await scenario('Mesures autonomes : comparaisons et recherche de désignations sans appel',async ctx=>{
 choisirMesures(ctx);ctx.host.querySelector('[data-comparison-after-lot]').value='test-mesures';const n=ctx.appels.length;ctx.button('Comparer avant').click();ctx.host.querySelector('form').dispatchEvent(new ctx.w.Event('submit',{cancelable:true}));await tick();assert.equal(ctx.appels.length,n);
},lotsAvecMesures);
await scenario('Mesures autonomes : inventaire sans actions Code/PDF',async ctx=>{
 choisirMesures(ctx);ctx.reponse(catalogueSources({type_lot:'mesures'}));ctx.button('Inventorier les sources').click();await tick();assert(!ctx.button('Articles de la source'));assert(!ctx.button('Lire la source PDF'));assert(!ctx.button('Télécharger le PDF reçu'));
},lotsAvecMesures);
await scenario('Mesures autonomes : retour tarif puis Code restaure les outils',async ctx=>{
 const l=choisirMesures(ctx);l.value='test-tarif';l.dispatchEvent(new ctx.w.Event('change'));assert(!ctx.host.querySelector('form button').disabled);assert(!ctx.host.querySelector('[data-measure-query]').closest('fieldset').disabled);
 l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));assert(!ctx.host.querySelector('[data-read-id]').closest('fieldset').disabled);assert(ctx.host.querySelector('[data-measure-query]').closest('fieldset').disabled);assert(!ctx.host.querySelector('[data-sources-nature]').disabled);
},lotsAvecMesures);
await scenario('Mesures autonomes : ancienne suite inerte après changement de lot',async ctx=>{
 const l=choisirMesures(ctx);ctx.host.querySelector('[data-measure-type]').value='restriction';ctx.reponse(rapportMesuresAutonomes());ctx.button('Rechercher dans les mesures').click();await tick();const ancien=ctx.button('Page suivante des mesures trouvées'),n=ctx.appels.length;
 l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));ancien.click();await tick();assert.equal(ctx.appels.length,n);
},lotsAvecMesures);
await scenario('Mesures autonomes : panne audit sans données ni actions',async ctx=>{
 choisirMesures(ctx);ctx.host.querySelector('[data-measure-type]').value='restriction';ctx.reponse(rapportMesuresAutonomes());ctx.button('Rechercher dans les mesures').click();await tick();ctx.reponse({detail:{code:'audit_revue_indisponible'}},503);ctx.button('Rechercher dans les mesures').click();await tick();assert.equal(ctx.host.querySelector('pre').textContent,'');assert.equal(ctx.host.querySelector('[data-review-actions]').textContent,'');
},lotsAvecMesures);
const lotsMixtes=[...lotsAvecMesures,lot('mesures-b','mesures')];
function choisirMixte(ctx){const l=ctx.host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new ctx.w.Event('change'));ctx.host.querySelector('[data-code10]').value='0101000000';}
const rapportMixte=extra=>envelope({type_rapport:'consultation_documentaire_tarif_mesures_autonomes',rattachement_juridique_etabli:false,mesures_fusionnees:false,
 code_tarifaire_10_exact:'0101000000',lots_exacts:{tarif:'test-tarif',mesures:'test-mesures'},roles_archives:{avant:'nomenclature',apres:'mesures_autonomes'},
 fiche_nomenclature:{code_tarifaire_10_exact:'0101000000',ligne_trouvee:true,ligne_declaree:{code_tarifaire_10:'0101000000'},limite_mesures:2,decalage_mesures:0,decalage_mesures_suivant:2,total_mesures_declarees:7},
 mesures_autonomes:{type_lot:'mesures',filtres:{code10_exact:'0101000000',type_mesure:null},limite:3,decalage:3,decalage_suivant:6,total_correspondances:10},...extra});
await scenario('Tarif/mesures : paramètres exacts et sources distinctes',async ctx=>{
 choisirMixte(ctx);ctx.host.querySelector('[data-autonomous-limit]').value=3;ctx.host.querySelector('[data-autonomous-offset]').value=3;
 ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/tariff-measures');assert.equal(u.searchParams.get('tarif'),'test-tarif');assert.equal(u.searchParams.get('mesures'),'test-mesures');assert.equal(u.searchParams.get('code10'),'0101000000');assert.equal(u.searchParams.get('measures_offset'),'3');
},lotsMixtes);
await scenario('Tarif/mesures : suite autonome conserve pagination nomenclature',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();ctx.button('Mesures autonomes suivantes').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');
 assert.equal(u.searchParams.get('tariff_limit'),'2');assert.equal(u.searchParams.get('tariff_offset'),'0');assert.equal(u.searchParams.get('measures_limit'),'3');assert.equal(u.searchParams.get('measures_offset'),'6');
},lotsMixtes);
await scenario('Tarif/mesures : suite nomenclature conserve pagination autonome',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();ctx.button('Mesures suivantes de la nomenclature').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');
 assert.equal(u.searchParams.get('tariff_offset'),'2');assert.equal(u.searchParams.get('measures_offset'),'3');
},lotsMixtes);
await scenario('Tarif/mesures : ouvrir le lot autonome ne fabrique pas une fiche',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();ctx.button('Consulter ce lot de mesures autonomes').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');
 assert.equal(u.pathname,'/api/v1/customs-review/lots/test-mesures/measure-search');assert.equal(u.searchParams.get('code10'),'0101000000');assert.equal(ctx.host.querySelector('select').value,'test-mesures');
},lotsMixtes);
await scenario('Tarif/mesures : code invalide ou sélection Code sans lecture',async ctx=>{
 let n=ctx.appels.length;ctx.button('Consulter nomenclature et mesures').click();await tick();assert.equal(ctx.appels.length,n);
 choisirMixte(ctx);ctx.host.querySelector('[data-code10]').value='010100';ctx.button('Consulter nomenclature et mesures').click();await tick();assert.equal(ctx.appels.length,n);
},lotsMixtes);
await scenario('Tarif/mesures : changement de lot autonome invalide ancienne suite',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();const ancien=ctx.button('Mesures autonomes suivantes'),n=ctx.appels.length,s=ctx.host.querySelector('[data-autonomous-lot]');
 s.value='mesures-b';s.dispatchEvent(new ctx.w.Event('change'));ancien.click();await tick();assert.equal(ctx.appels.length,n);assert.equal(ctx.host.querySelector('pre').textContent,'');
},lotsMixtes);
await scenario('Tarif/mesures : provenance de rôles incohérente sans action',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({roles_archives:{avant:'mesures_autonomes',apres:'nomenclature'}}));ctx.button('Consulter nomenclature et mesures').click();await tick();assert(!ctx.button('Mesures autonomes suivantes'));assert(!ctx.button('Consulter ce lot'));
},lotsMixtes);
await scenario('Tarif/mesures : panne audit efface les deux côtés',async ctx=>{
 choisirMixte(ctx);ctx.reponse(rapportMixte({}));ctx.button('Consulter nomenclature et mesures').click();await tick();ctx.reponse({detail:{code:'audit_revue_indisponible'}},503);ctx.button('Consulter nomenclature et mesures').click();await tick();assert.equal(ctx.host.querySelector('pre').textContent,'');assert.equal(ctx.host.querySelector('[data-review-actions]').textContent,'');
},lotsMixtes);
const fiscalPDFRapport=(extra={})=>pdfRapport({type_rapport:'lecture_page_pdf_mesures_recu',type_lot:'mesures',document_declare:{id:'DOC_TEST',format:'pdf',sha256:'a'.repeat(64)},transcription_verification:'non_verifiee',mesures_transcrites_comparees:false,...extra});
function ouvrirFiscal(ctx,extra={}){choisirMesures(ctx);ctx.host.querySelector('[data-fiscal-pdf-id]').value='DOC_TEST';ctx.reponse(envelope(fiscalPDFRapport(extra)));ctx.button('Lire le PDF fiscal natif').click();}
await scenario('PDF fiscal : champ réservé aux mesures',async ctx=>{
 const f=ctx.host.querySelector('[data-fiscal-pdf-id]').closest('fieldset');assert(f.disabled);choisirMesures(ctx);assert(!f.disabled);assert(ctx.host.querySelector('[data-pdf-id]').closest('fieldset').disabled);
},lotsAvecMesures);
await scenario('PDF fiscal : route dédiée et texte hostile littéral',async ctx=>{
 ouvrirFiscal(ctx,{fragment:'<img src=x onerror=alert(1)>',decalage_suivant:null});await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert(u.pathname.endsWith('/test-mesures/fiscal-pdf'));assert.equal(u.searchParams.get('document_id'),'DOC_TEST');assert(!ctx.host.querySelector('img'));assert(ctx.host.querySelector('[data-article-fragment]').textContent.includes('<img'));
},lotsAvecMesures);
await scenario('PDF fiscal : paramètres invalides sans appel',async ctx=>{
 choisirMesures(ctx);ctx.host.querySelector('[data-fiscal-pdf-id]').value='DOC_TEST';ctx.host.querySelector('[data-fiscal-pdf-page]').value='0';const n=ctx.appels.length;ctx.button('Lire le PDF fiscal natif').click();await tick();assert.equal(ctx.appels.length,n);
},lotsAvecMesures);
await scenario('PDF fiscal : pagination Unicode et page physique',async ctx=>{
 ouvrirFiscal(ctx);await tick();ctx.button('Fragment suivant du PDF fiscal').click();await tick();assert.equal(new URL(ctx.appels.at(-1).url,'https://x').searchParams.get('offset'),'4');ctx.button('Page physique fiscale suivante').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('page'),'2');assert.equal(u.searchParams.get('offset'),'0');
},lotsAvecMesures);
await scenario('PDF fiscal : mauvaise empreinte sans suite',async ctx=>{
 ouvrirFiscal(ctx,{sha256_pdf_lu:'b'.repeat(64)});await tick();assert(!ctx.button('Page physique fiscale suivante'));assert(!ctx.button('Fragment suivant du PDF fiscal'));
},lotsAvecMesures);
await scenario('PDF fiscal : page sans texte ne déclenche pas OCR',async ctx=>{
 ouvrirFiscal(ctx,{fragment:'',texte_natif_non_vide:false,decalage_suivant:null});await tick();assert(ctx.status().includes('aucun OCR'));assert.equal(ctx.host.querySelector('[data-article-fragment]').textContent,'');
},lotsAvecMesures);
await scenario('PDF fiscal : changement de lot invalide ancien bouton',async ctx=>{
 ouvrirFiscal(ctx);await tick();const ancien=ctx.button('Page physique fiscale suivante');const l=ctx.host.querySelector('select');l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));const n=ctx.appels.length;ancien.click();await tick();assert.equal(ctx.appels.length,n);
},lotsAvecMesures);
await scenario('PDF fiscal : panne audit efface réponse et suites',async ctx=>{
 ouvrirFiscal(ctx);await tick();ctx.reponse({detail:{code:'audit_revue_indisponible'}},503);ctx.button('Lire le PDF fiscal natif').click();await tick();assert.equal(ctx.host.querySelector('pre').textContent,'');assert(!ctx.button('Page physique fiscale suivante'));
},lotsAvecMesures);
const mesureMatchRapport=(extra={})=>({type_rapport:'rapprochement_litteral_description_mesure_pdf',type_lot:'mesures',mesure_id_exact:'M_0',champ_texte:'description',fragment_description:'أ😀é',total_caracteres_description:10,limite:4,decalage:0,decalage_suivant:4,page_physique_demandee:2,transcription_verification:'non_verifiee',taux_et_periodes_verifies:false,...extra});
function ouvrirMesureMatch(ctx,extra={}){choisirMesures(ctx);ctx.host.querySelector('[data-measure-pdf-id]').value='M_0';ctx.host.querySelector('[data-measure-pdf-page]').value=2;ctx.reponse(envelope(mesureMatchRapport(extra)));ctx.button('Vérifier la présence du fragment de description').click();}
await scenario('Description/PDF : route et paramètres distincts',async ctx=>{ouvrirMesureMatch(ctx);await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert(u.pathname.endsWith('/measure-pdf-match'));assert.equal(u.searchParams.get('mesure_id'),'M_0');assert.equal(u.searchParams.get('page'),'2');},lotsAvecMesures);
await scenario('Description/PDF : suite garde la page et offset Unicode',async ctx=>{ouvrirMesureMatch(ctx);await tick();ctx.button('Fragment de description suivant').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('offset'),'4');assert.equal(u.searchParams.get('page'),'2');},lotsAvecMesures);
await scenario('Description/PDF : texte hostile non HTML',async ctx=>{ouvrirMesureMatch(ctx,{fragment_description:'<img onerror=x>',decalage_suivant:null});await tick();assert(!ctx.host.querySelector('img'));assert(ctx.host.querySelector('[data-article-fragment]').textContent.includes('<img'));},lotsAvecMesures);
await scenario('Description/PDF : paramètres invalides sans appel',async ctx=>{choisirMesures(ctx);const n=ctx.appels.length;ctx.button('Vérifier la présence du fragment de description').click();await tick();assert.equal(ctx.appels.length,n);},lotsAvecMesures);
await scenario('Description/PDF : changement source invalide ancien bouton',async ctx=>{ouvrirMesureMatch(ctx);await tick();const b=ctx.button('Fragment de description suivant');const l=ctx.host.querySelector('select');l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));const n=ctx.appels.length;b.click();await tick();assert.equal(ctx.appels.length,n);},lotsAvecMesures);
await scenario('Description/PDF : panne audit efface ancien constat',async ctx=>{ouvrirMesureMatch(ctx);await tick();ctx.reponse({detail:{code:'audit_revue_indisponible'}},503);ctx.button('Vérifier la présence du fragment de description').click();await tick();assert.equal(ctx.host.querySelector('pre').textContent,'');assert(!ctx.button('Fragment de description suivant'));},lotsAvecMesures);
const criteresRapport=(extra={})=>({type_recherche:'tarif_criteres_documentaires',attributs_techniques_certifies:false,classement_ia_effectue:false,filtres:{criteres:{designation:'équipement',matiere:'acier',fonction:null,usage:null,caracteristiques:null},code_prefix:'0101'},limite:1,decalage:0,decalage_suivant:1,total_correspondances:2,resultats:[{ligne:{code_tarifaire_10:'0101000000'}}],...extra});
function ouvrirCriteres(ctx,extra={}){const l=ctx.host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new ctx.w.Event('change'));ctx.host.querySelector('[data-tariff-criteria-designation]').value='équipement';ctx.host.querySelector('[data-tariff-criteria-matiere]').value='acier';ctx.reponse(envelope(criteresRapport(extra)));ctx.button('Rechercher les critères tarifaires').click();}
await scenario('Critères tarifaires : paramètres séparés et fiche',async ctx=>{ouvrirCriteres(ctx);await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert(u.pathname.endsWith('/tariff-criteria'));assert.equal(u.searchParams.get('matiere'),'acier');assert(ctx.button('Fiche documentaire'));});
await scenario('Critères tarifaires : suite restitue les critères du rapport',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.host.querySelector('[data-tariff-criteria-matiere]').value='AUTRE';ctx.button('Page suivante des critères tarifaires').click();await tick();const u=new URL(ctx.appels.at(-1).url,'https://x');assert.equal(u.searchParams.get('offset'),'1');assert.equal(u.searchParams.get('matiere'),'acier');assert.equal(u.searchParams.get('code_prefix'),'0101');});
await scenario('Critères tarifaires : requête vide refusée sans HTTP',async ctx=>{const l=ctx.host.querySelector('select');l.value='test-tarif';l.dispatchEvent(new ctx.w.Event('change'));const n=ctx.appels.length;ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(ctx.appels.length,n);});
await scenario('Critères tarifaires : préfixe non ASCII refusé',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.host.querySelector('[data-tariff-criteria-prefix]').value='١٢';const n=ctx.appels.length;ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(ctx.appels.length,n);});
await scenario('Critères tarifaires : ancienne suite inerte après changement de lot',async ctx=>{ouvrirCriteres(ctx);await tick();const b=ctx.button('Page suivante des critères tarifaires');const l=ctx.host.querySelector('select');l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));const n=ctx.appels.length;b.click();await tick();assert.equal(ctx.appels.length,n);});
await scenario('Critères tarifaires : audit 503 efface anciens résultats',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.reponse({detail:{code:'audit_revue_indisponible'}},503);ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(ctx.host.querySelector('pre').textContent,'');assert(!ctx.button('Page suivante des critères tarifaires'));});
function rapportExtraitTarif(modifier){const texte='😀 <img src=x> Équipement';const ex={critere:'designation',champ_texte:'designation_officielle_fr',terme_normalise:'equipement',unite_decalage:'points_de_code_unicode_python',decalage:0,fragment:texte,total_caracteres:Array.from(texte).length,correspondance_debut:Array.from('😀 <img src=x> ').length,correspondance_fin:Array.from(texte).length,correspondance_entierement_visible:true};if(modifier)modifier(ex);return criteresRapport({termes_normalises_par_critere:{designation:['equipement'],matiere:['acier']},resultats:[{ligne:{code_tarifaire_10:'0101000000',designation_officielle_fr:texte},extraits_correspondants:[ex]}]});}
await scenario('Extraits tarif : Unicode original, HTML inerte, sans lien distant',async ctx=>{ouvrirCriteres(ctx,rapportExtraitTarif());await tick();assert.equal(ctx.host.querySelector('blockquote').textContent,'😀 <img src=x> Équipement');assert.equal(ctx.host.querySelector('img'),null);assert.equal(ctx.host.querySelector('blockquote').dir,'auto');});
for(const [nom,changer] of [['champ interdit',ex=>{ex.champ_texte='texte_integral';}],['offset UTF16',ex=>{ex.total_caracteres++;}],['autre critère',ex=>{ex.critere='fonction';}],['terme non demandé',ex=>{ex.terme_normalise='invente';}],['fragment réécrit',ex=>{ex.fragment='AUTRE';}],['unité incorrecte',ex=>{ex.unite_decalage='octets';}],['fin hors texte',ex=>{ex.correspondance_fin=999;}],['visibilité incohérente',ex=>{ex.correspondance_entierement_visible=false;}]]){
  await scenario('Extraits tarif : refus '+nom,async ctx=>{ouvrirCriteres(ctx,rapportExtraitTarif(changer));await tick();assert.equal(ctx.host.querySelector('blockquote'),null);});
}
await scenario('Extraits tarif : disparition après changement de lot',async ctx=>{ouvrirCriteres(ctx,rapportExtraitTarif());await tick();assert(ctx.host.querySelector('blockquote'));const l=ctx.host.querySelector('select');l.value='test-code';l.dispatchEvent(new ctx.w.Event('change'));assert.equal(ctx.host.querySelector('blockquote'),null);});
await scenario('Extraits tarif : correspondance partiellement visible signalée',async ctx=>{const texte='a'+'ـ'.repeat(500)+'b';const ex={critere:'designation',champ_texte:'designation_officielle_ar',terme_normalise:'ab',unite_decalage:'points_de_code_unicode_python',decalage:0,fragment:texte.slice(0,384),total_caracteres:502,correspondance_debut:0,correspondance_fin:502,correspondance_entierement_visible:false};ouvrirCriteres(ctx,criteresRapport({termes_normalises_par_critere:{designation:['ab']},resultats:[{ligne:{code_tarifaire_10:'0101000000',designation_officielle_ar:texte},extraits_correspondants:[ex]}]}));await tick();assert.equal(ctx.host.querySelector('blockquote').textContent.length,384);assert(ctx.host.textContent.includes('correspondance partiellement visible'));});
await scenario('Modes tarif : défaut explicite sous-chaîne',async ctx=>{ouvrirCriteres(ctx);await tick();assert.equal(new URL(ctx.appels.at(-1).url,'https://x').searchParams.get('match_mode'),'sous_chaine');});
await scenario('Modes tarif : choix mots entiers transmis',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.host.querySelector('[data-tariff-criteria-mode]').value='mots_entiers';ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(new URL(ctx.appels.at(-1).url,'https://x').searchParams.get('match_mode'),'mots_entiers');});
await scenario('Modes tarif : suite restaure le mode du rapport',async ctx=>{const r=criteresRapport();r.filtres.match_mode='mots_entiers';ouvrirCriteres(ctx,r);await tick();ctx.host.querySelector('[data-tariff-criteria-mode]').value='sous_chaine';ctx.button('Page suivante des critères tarifaires').click();await tick();assert.equal(new URL(ctx.appels.at(-1).url,'https://x').searchParams.get('match_mode'),'mots_entiers');});
await scenario('Modes tarif : rapport ancien restaure le défaut',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.host.querySelector('[data-tariff-criteria-mode]').value='mots_entiers';ctx.button('Page suivante des critères tarifaires').click();await tick();assert.equal(new URL(ctx.appels.at(-1).url,'https://x').searchParams.get('match_mode'),'sous_chaine');});
await scenario('Modes tarif : mode invalide sans HTTP',async ctx=>{ouvrirCriteres(ctx);await tick();ctx.host.querySelector('[data-tariff-criteria-mode]').value='regex';const n=ctx.appels.length;ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(ctx.appels.length,n);});
await scenario('Modes tarif : pas de suite de rapport au mode inconnu',async ctx=>{const r=criteresRapport();r.filtres.match_mode='regex';ouvrirCriteres(ctx,r);await tick();assert.equal(ctx.button('Page suivante des critères tarifaires'),undefined);});
for(const code of [401,403,503])await scenario('Modes tarif : tous les outils retirés sur '+code,async ctx=>{ouvrirCriteres(ctx);await tick();ctx.reponse({detail:'NE-PAS-AFFICHER'},code);ctx.button('Rechercher les critères tarifaires').click();await tick();assert.equal(ctx.host.querySelectorAll('fieldset').length,0);assert.equal(ctx.host.querySelector('[data-tariff-criteria-mode]'),null);assert.equal(ctx.host.querySelector('[data-fiscal-pdf-page]'),null);assert.equal(ctx.host.querySelector('pre').textContent,'');});
function diagnosticRapport(extra={}){return {perimetre:'lignes_du_lot_apres_filtre_prefixe_avant_pagination',lignes_dans_prefixe:5,lignes_tous_criteres:0,constat:'aucune_conjonction_sur_meme_ligne',absence_de_droit_deduite:false,attributs_manquants_deduits:false,par_critere:{designation:{lignes_tous_termes:2},matiere:{lignes_tous_termes:1}},...extra};}
await scenario('Diagnostic critères : zéro conjonction, critères séparés présents',async ctx=>{ouvrirCriteres(ctx,criteresRapport({total_correspondances:0,resultats:[],decalage_suivant:null,diagnostic_recherche:diagnosticRapport()}));await tick();assert(ctx.host.textContent.includes('Aucune ligne ne réunit'));assert(ctx.host.textContent.includes('designation : 2 ligne(s)'));assert(ctx.host.textContent.includes('matiere : 1 ligne(s)'));assert(ctx.host.textContent.includes('Aucun droit ni attribut produit déduit'));});
await scenario('Diagnostic critères : page vide avec correspondances',async ctx=>{ouvrirCriteres(ctx,criteresRapport({decalage:99,resultats:[],diagnostic_recherche:diagnosticRapport({lignes_tous_criteres:2,constat:'page_hors_resultats'})}));await tick();assert(ctx.host.textContent.includes('cette page est au-delà'));});
await scenario('Diagnostic critères : préfixe sans ligne',async ctx=>{ouvrirCriteres(ctx,criteresRapport({total_correspondances:0,resultats:[],diagnostic_recherche:diagnosticRapport({lignes_dans_prefixe:0,constat:'aucune_ligne_dans_prefixe',par_critere:{}})}));await tick();assert(ctx.host.textContent.includes('Aucune ligne dans le périmètre'));});
for(const [nom,extra] of [['compteur incohérent',{lignes_tous_criteres:7}],['droit déduit',{absence_de_droit_deduite:true}],['constat inconnu',{constat:'CLASSEMENT_AUTOMATIQUE'}],['constat incompatible',{constat:'page_hors_resultats'}]])await scenario('Diagnostic critères : rejet '+nom,async ctx=>{ouvrirCriteres(ctx,criteresRapport({total_correspondances:0,resultats:[],diagnostic_recherche:diagnosticRapport(extra)}));await tick();assert(!ctx.host.textContent.includes('Diagnostic documentaire —'));});
await scenario('Diagnostic critères : disparition après audit 503',async ctx=>{ouvrirCriteres(ctx,criteresRapport({total_correspondances:0,resultats:[],diagnostic_recherche:diagnosticRapport()}));await tick();assert(ctx.host.textContent.includes('Diagnostic documentaire —'));ctx.reponse({detail:'NON_AFFICHABLE'},503);ctx.button('Rechercher les critères tarifaires').click();await tick();assert(!ctx.host.textContent.includes('Diagnostic documentaire —'));});
console.log(compte+' scénarios UI réussis (contrats NON OFFICIELS isolés).');
})().catch(e=>{console.error(e);process.exitCode=1;});
