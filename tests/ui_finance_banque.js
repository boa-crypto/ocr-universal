/* Contrat UI banque : API simulée, aucune écriture réelle. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const attendre = ms => new Promise(r => setTimeout(r, ms));
async function jusque(condition, message) {
  const fin = Date.now() + 10000;
  while (Date.now() < fin) { if (condition()) return; await attendre(50); }
  throw new Error(message || 'État UI attendu non atteint');
}
async function verifier(role) {
  const ecritures = [], erreurs = [];
  let operations = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if (e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: false, virtualConsole: vc,
    beforeParse(w) {
      w.requestAnimationFrame = cb => w.setTimeout(() => cb(Date.now()), 16);
      w.cancelAnimationFrame = id => w.clearTimeout(id);
      w.scrollTo = () => {}; w.confirm = () => true;
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base), methode = options.method || 'GET';
        const json = (objet, status = 200) => new Response(JSON.stringify(objet), { status, headers: { 'Content-Type': 'application/json' } });
        if (cible.pathname === '/api/rbac/moi') return json(role === 'lecteur' ? { actif: true, roles: ['lecteur'], ecriture: false, supervision: false } : role === 'operateur' ? { actif: true, roles: ['operateur'], ecriture: true, supervision: false } : { actif: true, roles: ['superviseur'], ecriture: true, supervision: true });
        if (cible.pathname === '/api/frais/banque/operations' && methode === 'GET') return json(operations);
        if (cible.pathname === '/api/frais/banque/import-csv' && methode === 'POST') {
          assert.ok(options.body instanceof w.FormData);
          assert.equal(options.body.get('dossier_id'), 'dos_test');
          assert.equal(options.body.get('fichier').name, 'banque.csv');
          assert.equal(options.headers['Content-Type'], undefined);
          ecritures.push('csv');
          operations = [{ id: 'op_test', dossier_id: 'dos_test', date: '2026-11-11', montant: 100, devise: 'EUR', statut: 'non_rapprochee' }];
          return json({ importees: 1, doublons: 0, rejetees: [], operations: ['op_test'] });
        }
        if (cible.pathname === '/api/frais/banque/import' && methode === 'POST') {
          const payload = JSON.parse(options.body);
          assert.equal(payload.dossier_id, 'dos_test');
          assert.deepEqual(payload.operations, [{ date: '2026-11-12', montant: 50 }]);
          assert.equal(options.headers['Content-Type'], 'application/json');
          ecritures.push('json');
          return json({ importees: 1, doublons: 0, rejetees: [], operations: ['op_json'] });
        }
        if (methode !== 'GET') throw new Error('Écriture inattendue ' + methode + ' ' + cible.pathname);
        return fetch(cible, options);
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500); w.location.hash = '#finance/banque';
    const page = doc.querySelector('#tab-ecran');
    await jusque(() => page.textContent.includes('Opérations bancaires'));
    const bouton = libelle => [...page.querySelectorAll('button')].find(b => b.textContent === libelle);
    if (role === 'lecteur') {
      assert.equal(bouton('Importer CSV'), undefined);
      assert.equal(bouton('Importer JSON'), undefined);
      assert.deepEqual(ecritures, []);
    } else {
      bouton('Importer CSV').click();
      let boite = doc.querySelector('.ecran__boite[role=dialog]');
      let form = boite.querySelector('form');
      form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
      assert.match(boite.querySelector('[role=alert]').textContent, /Champs obligatoires/);
      assert.deepEqual(ecritures, []);
      boite.querySelector('#action-dossier_id').value = 'dos_test';
      const fichier = boite.querySelector('input[type=file]');
      Object.defineProperty(fichier, 'files', { configurable: true, value: [new w.File(['date;montant\n2026-11-11;100\n'], 'banque.csv', { type: 'text/csv' })] });
      form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
      await jusque(() => !doc.querySelector('.ecran__boite'));
      await jusque(() => page.textContent.includes('1 importée(s)'));
      bouton('Importer JSON').click();
      boite = doc.querySelector('.ecran__boite[role=dialog]');
      form = boite.querySelector('form');
      boite.querySelector('#action-dossier_id').value = 'dos_test';
      const jsonFile = boite.querySelector('input[type=file]');
      Object.defineProperty(jsonFile, 'files', { configurable: true, value: [new w.File([JSON.stringify([{ date: '2026-11-12', montant: 50 }])], 'banque.json', { type: 'application/json' })] });
      form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
      await jusque(() => !doc.querySelector('.ecran__boite'));
      await jusque(() => ecritures.length === 2);
      assert.deepEqual(ecritures, ['csv', 'json']);
      if (role === 'operateur') {
        w.location.hash = '#finance/reconciliation';
        await jusque(() => page.textContent.includes('Rapprochement financier'));
        assert.equal([...page.querySelectorAll('button')].some(b => b.textContent === 'Lancer le rapprochement'), false);
      }
    }
    assert.deepEqual(erreurs, []);
    console.log('OK UI banque ' + role + ' : ' + (role === 'lecteur' ? 'aucune écriture' : 'imports CSV/JSON simulés') + '.');
  } finally { dom.window.close(); }
}
(async () => { await verifier('lecteur'); await verifier('operateur'); await verifier('superviseur'); })().catch(e => { console.error(e); process.exitCode = 1; });
