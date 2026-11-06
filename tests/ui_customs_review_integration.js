/* Intégration JSDOM → HTTP → véritable middleware/API, magasin temporaire.
 * Aucun service de production, aucune réponse métier simulée par ce test.
 */
const assert = require('node:assert/strict');
const {JSDOM} = require('jsdom');
(async()=>{
  const base = process.argv[2];
  const authentifier = {headers:{Authorization:'Bearer TEST_ADMIN_NON_PRODUCTION'}};
  const page = await fetch(base+'/', authentifier); assert.equal(page.status,200);
  const html = await page.text();
  const dom = new JSDOM(html, {url:base+'/#admin/revue-douaniere', runScripts:'outside-only'});
  const w=dom.window, doc=w.document, appels=[];
  w.fetch=(url, opts={})=>{
    assert(!opts.method || opts.method==='GET');
    appels.push(String(url)); return fetch(new URL(url,base),opts);
  };
  w.sessionStorage.setItem('uniocr_token','TEST_ADMIN_NON_PRODUCTION');
  for (const path of ['/web/navigation.js','/web/customs-review.js']) {
    w.eval(await (await fetch(base+path, authentifier)).text());
  }
  w.Navigation.init();
  const host=doc.getElementById('customs-review-host');
  const attendre=async pred=>{
    const fin=Date.now()+8000;
    while(!pred()) {if(Date.now()>fin)throw new Error('Délai dépassé : '+host.textContent.slice(0,500)); await new Promise(r=>setTimeout(r,15));}
  };
  const bouton=t=>[...host.querySelectorAll('button')].find(b=>b.textContent.includes(t));
  await attendre(()=>host.querySelectorAll('li').length===3);
  assert(!doc.getElementById('tab-customs-review').classList.contains('hidden'));
  assert(doc.querySelector('a[href="#admin/revue-douaniere"]'));
  assert.equal([...doc.querySelectorAll('section.page')].filter(s=>!s.classList.contains('hidden')).length,1);
  const lot=host.querySelector('select'); lot.value='code_a'; lot.dispatchEvent(new w.Event('change'));
  bouton('Contrôler').click(); await attendre(()=>host.querySelector('pre').textContent.includes('manifest_sha256'));
  const q=host.querySelector('input'); q.value='';
  host.querySelectorAll('input')[1].value='5 bis';
  host.querySelectorAll('select')[2].value='originale';
  host.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));
  await attendre(()=>host.querySelector('pre').textContent.includes('total_correspondances'));
  assert.equal(JSON.parse(host.querySelector('pre').textContent).total_correspondances,1);
  bouton('Afficher l’historique').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('historique_documentaire_article'));
  const historique=JSON.parse(host.querySelector('pre').textContent);
  assert.equal(historique.total_versions_meme_numero,2);
  assert.equal(historique.relations_declarees[0].origine_id,'TEST_M_A');
  assert.equal(historique.succession_juridique_etablie,false);
  lot.value='tarif_a'; lot.dispatchEvent(new w.Event('change'));
  host.querySelectorAll('select')[1].value='tarif_b'; bouton('Comparer').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('archives'));
  const diff=JSON.parse(host.querySelector('pre').textContent);
  assert(diff.archives.avant.manifest_sha256); assert(diff.archives.apres.manifest_sha256);
  // Un vrai compte lecteur ne peut rien lire, même par le lien direct.
  w.sessionStorage.setItem('uniocr_token','TEST_LECTEUR_NON_PRODUCTION'); bouton('Actualiser').click();
  await attendre(()=>host.textContent.includes('Accès refusé'));
  assert.equal(host.querySelector('select'),null); assert.equal(host.querySelector('pre').textContent,'');
  assert(appels.some(p=>p.includes('/check')) && appels.some(p=>p.includes('/search?')) && appels.some(p=>p.includes('/diff?')) && appels.some(p=>p.includes('/history?')));
  console.log('Intégration réelle UI/HTTP/API : liste, navigation, contrôle, recherche, historique, diff, refus lecteur OK.');
  w.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
