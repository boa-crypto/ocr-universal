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
  bouton('Diagnostiquer la couverture').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('couverture_documentaire_declaree'));
  const couverture=JSON.parse(host.querySelector('pre').textContent);
  assert.equal(couverture.indicateurs.compteurs.articles_transcrits,3);
  assert.equal(couverture.pourcentage_completude_reglementaire,null);
  assert.equal(couverture.utilisable_pour_calcul_douanier,false);
  host.querySelector('[data-read-id]').value='TEST_O_A'; host.querySelector('[data-read-field]').value='texte_arabe';
  bouton('Lire le fragment').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('lecture_article_documentaire'));
  const lecture=JSON.parse(host.querySelector('pre').textContent);
  assert.equal(lecture.article_trouve,true); assert.equal(lecture.version_declaree.nature_version,'originale');
  assert(lecture.fragment.includes('غير رسمية'));
  assert.equal(host.querySelector('[data-article-fragment]').textContent,lecture.fragment);
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
  const level=host.querySelector('[data-tree-level]'); level.value='codes'; level.dispatchEvent(new w.Event('change'));
  host.querySelector('[data-tree-parent]').value='010100'; bouton('Parcourir la hiérarchie').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('navigation_tarifaire_documentaire'));
  const tree=JSON.parse(host.querySelector('pre').textContent);
  assert.equal(tree.total_enfants_declares,5); assert.equal(tree.enfants_declares[0].code_tarifaire_10,'0101000000');
  assert.equal(tree.parent_trouve,true);
  host.querySelector('[data-code10]').value='0101000000'; bouton('Consulter la fiche').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('fiche_tarifaire_documentaire'));
  const fiche=JSON.parse(host.querySelector('pre').textContent);
  assert.equal(fiche.ligne_declaree.code_tarifaire_10,'0101000000');
  assert.equal(fiche.hierarchie_declaree.sh6.code,'010100'); assert.equal(fiche.fiscalite_applicable_etablie,false);
  host.querySelectorAll('select')[1].value='tarif_b'; bouton('Comparer').click();
  await attendre(()=>host.querySelector('pre').textContent.includes('archives'));
  const diff=JSON.parse(host.querySelector('pre').textContent);
  assert(diff.archives.avant.manifest_sha256); assert(diff.archives.apres.manifest_sha256);
  // Un vrai compte lecteur ne peut rien lire, même par le lien direct.
  w.sessionStorage.setItem('uniocr_token','TEST_LECTEUR_NON_PRODUCTION'); bouton('Actualiser').click();
  await attendre(()=>host.textContent.includes('Accès refusé'));
  assert.equal(host.querySelector('select'),null); assert.equal(host.querySelector('pre').textContent,'');
  assert(appels.some(p=>p.includes('/check')) && appels.some(p=>p.includes('/search?')) && appels.some(p=>p.includes('/diff?')) && appels.some(p=>p.includes('/history?')) && appels.some(p=>p.includes('/tariff/0101000000')) && appels.some(p=>p.includes('/coverage')) && appels.some(p=>p.includes('/tree?')) && appels.some(p=>p.includes('/article?')));
  console.log('Intégration réelle UI/HTTP/API : liste, navigation, contrôle, recherche, historique, fiche tarif, couverture, hiérarchie, lecture article, diff, refus lecteur OK.');
  w.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
