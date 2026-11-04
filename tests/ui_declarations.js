/* Test de contrat navigateur : seules les ressources UI sont réelles.
 * Dossiers, déclarations et POST sont simulés, aucune donnée métier écrite. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const attendre = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const lignes = [], envois = [], erreurs = [];
  const consoleVirtuelle = new VirtualConsole();
  consoleVirtuelle.on('jsdomError', e => { if(e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true,
    virtualConsole: consoleVirtuelle,
    beforeParse(w) {
      w.scrollTo = () => {};
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.fetch = async (url, options = {}) => {
        const absolue = new URL(String(url), base);
        const methode = options.method || 'GET';
        const reponse = objet => Promise.resolve(new Response(JSON.stringify(objet), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        if (absolue.pathname === '/api/dossiers' && methode === 'GET') {
          return reponse([{ id: 'dos_contrat', label: 'Dossier de contrat', state_label: 'En préparation' }]);
        }
        if (absolue.pathname === '/api/declarations') {
          if (methode === 'GET') return reponse(lignes);
          if (methode === 'POST') {
            const corps = JSON.parse(options.body);
            envois.push(corps);
            const ligne = { ...corps, id: 'decl_contrat', statut: 'en_preparation' };
            lignes.push(ligne);
            return reponse(ligne);
          }
        }
        if (methode !== 'GET') throw new Error('Écriture réseau interdite : ' + absolue.pathname);
        return fetch(absolue, options);
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500);
    w.location.hash = '#douane/declarations';
    await attendre(1800);
    const page = doc.querySelector('#tab-ecran');
    assert.match(page.textContent, /Préparation des déclarations/);
    assert.match(page.textContent, /stockage local/);
    assert.match(page.textContent, /y compris après son redémarrage/);
    const nouveau = [...page.querySelectorAll('button')].find(b => b.textContent === 'Nouveau');
    assert.ok(nouveau, 'Bouton Nouveau');
    nouveau.click();
    await attendre(500);
    const boite = doc.querySelector('.ecran__boite');
    const form = boite.querySelector('form');
    const champ = boite.querySelector('#champ-dossier_id');
    const soumettre = () => form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
    champ.value = 'dos_inconnu';
    soumettre();
    assert.match(boite.querySelector('.ecran__erreur').textContent, /choisir dans la liste/);
    assert.equal(envois.length, 0);
    champ.value = 'dos_contrat';
    boite.querySelector('#champ-numero_declaration').value = 'DECL-CONTRAT';
    soumettre();
    await attendre(1000);
    assert.equal(envois.length, 1);
    assert.equal(envois[0].dossier_id, 'dos_contrat');
    assert.equal(envois[0].numero_declaration, 'DECL-CONTRAT');
    assert.equal(doc.querySelector('.ecran__boite'), null);
    assert.match(page.textContent, /DECL-CONTRAT/);
    assert.deepEqual(erreurs, []);
    console.log('OK : route, stockage local, choix dossier, refus inconnu, POST simulé, fermeture et liste actualisée.');
  } finally { dom.window.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
