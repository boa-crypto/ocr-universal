/* Contrat d'affichage jsdom, données terminal simulées, aucune écriture. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const attendre = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const lignes = ['demande', 'planifie', 'sortie_autorisee', 'sortis'].map((statut, i) => ({
    id: 'term_test_' + i, statut, numero_conteneur: 'CONT-' + i
  }));
  const ecritures = [], erreurs = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if (e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(w) {
      w.scrollTo = () => {};
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base);
        if ((options.method || 'GET') !== 'GET') {
          ecritures.push(cible.pathname);
          throw new Error('Écriture interdite');
        }
        if (cible.pathname === '/api/terminal') return new Response(JSON.stringify(lignes), {
          status: 200, headers: { 'Content-Type': 'application/json' }
        });
        return fetch(cible, options);
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500);
    w.location.hash = '#enlevissement/sortie-port';
    const page = doc.querySelector('#tab-ecran');
    const fin = Date.now() + 15000;
    while (page.querySelectorAll('tbody tr').length !== 4 && Date.now() < fin) await attendre(50);
    const rows = [...page.querySelectorAll('tbody tr')];
    assert.equal(rows.length, 4);
    const attendu = ['', 'Autoriser la sortie', 'Enregistrer la sortie', ''];
    for (let i = 0; i < rows.length; i++) {
      assert.equal([...rows[i].querySelectorAll('button')].map(b => b.textContent.trim()).join(''), attendu[i]);
    }
    assert.equal(w.UniOCREcrans.ecrans['enlevissement/sortie-port'].id, 'id');
    assert.deepEqual(ecritures, []);
    assert.deepEqual(erreurs, []);
    console.log('OK : quatre états, actions limitées aux étapes autorisées, clé id, aucune écriture.');
  } finally { dom.window.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
