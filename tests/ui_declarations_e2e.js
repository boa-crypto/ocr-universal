/* Réservé au serveur temporaire créé par test_declarations_e2e.py.
 * Vrais POST/PUT/DELETE, pas de mock API ni de données du poste. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const [base, phase, dossierId] = process.argv.slice(2);
assert.equal(process.env.UNOCR_E2E_ISOLATED, '1', 'Lancer via pytest tests/test_declarations_e2e.py');
assert.equal(new URL(base).hostname, '127.0.0.1');
const attendre = ms => new Promise(r => setTimeout(r, ms));
async function jusque(condition, message) {
  const fin = Date.now() + 15000;
  while (Date.now() < fin) {
    if (condition()) return;
    await attendre(50);
  }
  throw new Error(message);
}
(async () => {
  const erreurs = [], ecritures = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if (e.type !== 'not implemented') erreurs.push(e.message); });
  let confirmer = false;
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(w) {
      w.scrollTo = () => {};
      w.confirm = () => confirmer;
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base);
        const methode = options.method || 'GET';
        if (methode !== 'GET') {
          assert.equal(cible.origin, base);
          assert.match(cible.pathname, /^\/api\/declarations(?:\/decl_[a-z0-9]+)?$/);
          assert.ok(['POST', 'PUT', 'DELETE'].includes(methode));
          ecritures.push({ methode, chemin: cible.pathname });
        }
        const rep = await fetch(cible, options);
        if (rep.status >= 500) erreurs.push(cible.pathname + ' : ' + rep.status);
        return rep;
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    w.location.hash = '#douane/declarations';
    const page = doc.querySelector('#tab-ecran');
    const bouton = (zone, texte) => [...zone.querySelectorAll('button')].find(b => b.textContent.trim() === texte);
    const soumettre = boite => boite.querySelector('form').dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
    await jusque(() => bouton(page, 'Nouveau'), 'Écran Déclarations non prêt');
    if (phase === 'creer-modifier') {
      bouton(page, 'Nouveau').click();
      const boite = doc.querySelector('.ecran__boite');
      await jusque(() => boite.querySelector('datalist option'), 'Dossiers non chargés');
      boite.querySelector('#champ-dossier_id').value = dossierId;
      boite.querySelector('#champ-numero_declaration').value = 'DECL-E2E';
      boite.querySelector('#champ-date_depot').value = '2026-11-04';
      boite.querySelector('#champ-agent_declarant').value = 'Agent E2E';
      soumettre(boite);
      await jusque(() => !doc.querySelector('.ecran__boite') && page.textContent.includes('DECL-E2E'), 'Création non visible');
      assert.match(page.textContent, /Agent E2E/);
      bouton(page, 'Modifier').click();
      const edition = doc.querySelector('.ecran__boite');
      edition.querySelector('#champ-statut').value = 'deposee';
      edition.querySelector('#champ-numero_declaration').value = 'DECL-E2E-MODIFIEE';
      soumettre(edition);
      await jusque(() => !doc.querySelector('.ecran__boite') && page.textContent.includes('DECL-E2E-MODIFIEE'), 'Modification non visible');
      assert.deepEqual(ecritures.map(e => e.methode), ['POST', 'PUT']);
    } else {
      assert.equal(phase, 'supprimer');
      await jusque(() => page.textContent.includes('DECL-E2E-MODIFIEE'), 'Déclaration non relue après redémarrage');
      bouton(page, 'Supprimer').click();
      await attendre(100);
      assert.equal(ecritures.length, 0, 'Annulation ignorée');
      confirmer = true;
      bouton(page, 'Supprimer').click();
      await jusque(() => !page.textContent.includes('DECL-E2E-MODIFIEE') && page.textContent.includes('Aucune déclaration préparée'), 'Suppression non visible');
      assert.deepEqual(ecritures.map(e => e.methode), ['DELETE']);
    }
    assert.deepEqual(erreurs, []);
    console.log('OK E2E réel : ' + phase + ', ' + ecritures.length + ' écriture(s) isolée(s).');
  } finally { dom.window.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
