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
async function scenario(nom, action) {
  const dom = new JSDOM('<div id="customs-review-host"></div>', {
    url:'https://preview.invalid/#admin/revue-douaniere', runScripts:'outside-only'});
  const w = dom.window, appels = [];
  let repondre = () => Promise.resolve({ok:true, json:async()=>envelope({lots:[lot('test-code'),lot('test-tarif','tarif')]})});
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
console.log(compte+' scénarios UI réussis (contrats NON OFFICIELS isolés).');
})().catch(e=>{console.error(e);process.exitCode=1;});
