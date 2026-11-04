/* Contrat UI des pièces : API simulée ; aucune écriture dans les données réelles. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const attendre = ms => new Promise(r => setTimeout(r, ms));
async function jusque(condition) {
  const fin = Date.now() + 10000;
  while(Date.now() < fin) { if(condition()) return; await attendre(50); }
  throw new Error('État UI attendu non atteint');
}
async function verifier(lectureSeule) {
  let pieces = lectureSeule ? [{ id: 'just_test', nom_fichier: 'piece.pdf', taille_octets: 3 }] : [];
  let confirmer = false, refuser = false, refuserTelechargement = false;
  const ecritures = [], erreurs = [], telechargements = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if(e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.scrollTo = () => {}; w.confirm = () => confirmer;
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.URL.createObjectURL = blob => { telechargements.push(blob); return 'blob:test'; };
      w.URL.revokeObjectURL = () => {};
      w.HTMLAnchorElement.prototype.click = function () { assert.equal(this.download, 'piece.pdf'); };
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base), methode = options.method || 'GET';
        const json = (objet, status = 200) => new Response(JSON.stringify(objet), { status, headers: { 'Content-Type': 'application/json' } });
        if(cible.pathname === '/api/rbac/moi') return json(lectureSeule ? { actif: true, roles: ['lecteur'] } : { actif: false });
        if(cible.pathname === '/api/frais' && methode === 'GET') return json([{ id: 'frais_test', dossier_id: 'dos_test', montant: 42 }]);
        if(cible.pathname === '/api/frais/frais_test/justificatifs') return json(pieces);
        if(cible.pathname === '/api/frais/justificatif/just_test/download') return refuserTelechargement ? json({ detail: 'Empreinte invalide' }, 409) : new Response('abc');
        if(methode !== 'GET') {
          assert.equal(lectureSeule, false, 'Aucune écriture permise en lecture seule');
          ecritures.push(methode);
          if(methode === 'POST') {
            assert.equal(cible.pathname, '/api/frais/justificatif/upload');
            assert.equal(options.body.get('frais_id'), 'frais_test');
            assert.equal(options.body.get('fichier').name, 'piece.pdf');
            assert.equal(options.headers['Content-Type'], undefined, 'Frontière multipart gérée par le navigateur');
            if(refuser) return json({ detail: 'Refus de stockage simulé' }, 503);
            pieces = [{ id: 'just_test', nom_fichier: 'piece.pdf', taille_octets: 3 }]; return json(pieces[0]);
          }
          assert.equal(methode, 'DELETE');
          assert.equal(cible.pathname, '/api/frais/justificatif/just_test');
          pieces = []; return json({ deleted: true });
        }
        return fetch(cible, options);
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500); w.location.hash = '#finance/frais-dossier';
    const page = doc.querySelector('#tab-ecran');
    let declencheur;
    await jusque(() => (declencheur = [...page.querySelectorAll('button')].find(b => b.textContent === 'Justificatifs')));
    declencheur.focus(); declencheur.click();
    const boite = doc.querySelector('.ecran__boite[role=dialog]');
    assert.equal(boite.getAttribute('aria-label'), 'Justificatifs du frais');
    await jusque(() => !boite.querySelector('[role=status]').textContent.includes('Chargement'));
    if(!lectureSeule) {
      const form = boite.querySelector('form'), fichier = form.querySelector('input[type=file]');
      const soumettre = () => form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
      soumettre(); assert.match(boite.querySelector('[role=alert]').textContent, /Choisissez/);
      assert.equal(ecritures.length, 0);
      Object.defineProperty(fichier, 'files', { configurable: true, value: [new w.File([], 'vide.pdf')] });
      soumettre(); assert.match(boite.querySelector('[role=alert]').textContent, /non vide/);
      Object.defineProperty(fichier, 'files', { configurable: true, value: [{ size: 20 * 1024 * 1024 + 1 }] });
      soumettre(); assert.match(boite.querySelector('[role=alert]').textContent, /20 Mio/);
      assert.equal(ecritures.length, 0);
      Object.defineProperty(fichier, 'files', { configurable: true, value: [new w.File(['abc'], 'piece.pdf', { type: 'application/pdf' })] });
      refuser = true; soumettre();
      await jusque(() => boite.querySelector('[role=alert]').textContent.includes('Refus de stockage'));
      assert.equal(form.querySelector('button').disabled, false);
      refuser = false; soumettre();
      await jusque(() => boite.querySelector('.ecran__piece'));
    } else {
      assert.equal(boite.querySelector('input[type=file]'), null);
      assert.ok(!boite.textContent.includes('Supprimer la pièce'));
    }
    const telecharger = [...boite.querySelectorAll('button')].find(b => b.textContent === 'Télécharger');
    refuserTelechargement = true; telecharger.click();
    await jusque(() => boite.querySelector('[role=alert]').textContent.includes('Empreinte invalide'));
    assert.equal(telechargements.length, 0);
    refuserTelechargement = false; telecharger.click();
    await jusque(() => telechargements.length === 1);
    assert.equal(await telechargements[0].text(), 'abc');
    if(!lectureSeule) {
      const supprimer = [...boite.querySelectorAll('button')].find(b => b.textContent === 'Supprimer la pièce');
      supprimer.click(); assert.equal(ecritures.filter(m => m === 'DELETE').length, 0);
      confirmer = true; supprimer.click();
      await jusque(() => boite.querySelector('[role=status]').textContent.includes('Aucun justificatif'));
      assert.deepEqual(ecritures, ['POST', 'POST', 'DELETE']);
    } else assert.deepEqual(ecritures, []);
    const controles = boite.querySelectorAll('button:not([disabled]),input:not([disabled])');
    controles[controles.length - 1].focus();
    doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }));
    assert.equal(doc.activeElement, controles[0]);
    doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true }));
    assert.equal(doc.activeElement, controles[controles.length - 1]);
    doc.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    assert.equal(doc.querySelector('.ecran__boite[role=dialog]'), null);
    assert.equal(doc.activeElement, declencheur);
    assert.deepEqual(erreurs, []);
    console.log('OK justificatifs UI : ' + (lectureSeule ? 'lecteur sans mutation' : 'validation, erreur/reprise, ajout, téléchargement, suppression confirmée') + ', fermeture et focus.');
  } finally { dom.window.close(); }
}
(async () => { await verifier(false); await verifier(true); })().catch(e => { console.error(e); process.exitCode = 1; });
