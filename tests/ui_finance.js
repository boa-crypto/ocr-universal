/* Contrat Paiements : API financière simulée, aucun virement/aucune écriture réelle. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const attendre = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const factures = [{ id: 'fac_test', numero_facture: 'FACTURE-TEST', statut_paiement: 'en_attente' },
                    { id: 'fac_payee', numero_facture: 'FACTURE-PAYEE', statut_paiement: 'payee' }];
  const liquidations = [{ id: 'liqu_test', date_liquidation: '2026-11-04', statut: 'en_attente' },
                        { id: 'liqu_payee', date_liquidation: '2026-10-01', statut: 'payee' }];
  const envois = [], erreurs = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if(e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.scrollTo = () => {}; w.confirm = () => true;
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base), methode = options.method || 'GET';
        const reponse = objet => new Response(JSON.stringify(objet), { status: 200, headers: { 'Content-Type': 'application/json' } });
        if (methode === 'GET' && cible.pathname === '/api/frais/facture') return reponse(factures);
        if (methode === 'GET' && cible.pathname === '/api/declarations/liquidation') return reponse(liquidations);
        if (methode !== 'GET') {
          const payload = JSON.parse(options.body);
          envois.push({ chemin: cible.pathname, methode, payload });
          assert.equal(methode, 'PUT');
          if(cible.pathname === '/api/frais/facture/fac_test') {
            assert.deepEqual(payload, { statut_paiement: 'payee' });
            factures[0].statut_paiement = 'payee'; return reponse(factures[0]);
          }
          assert.equal(cible.pathname, '/api/declarations/liquidation/liqu_test');
          assert.deepEqual(payload, { statut: 'payee' });
          liquidations[0].statut = 'payee'; return reponse(liquidations[0]);
        }
        return fetch(cible, options);
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500); w.location.hash = '#finance/paiements';
    const page = doc.querySelector('#tab-ecran');
    async function lignes(nombre) {
      const fin = Date.now() + 10000;
      while(Date.now() < fin) {
        const boutons = [...page.querySelectorAll('tbody button')].filter(b => b.textContent === 'Marquer payé');
        if(boutons.length === nombre) return boutons;
        await attendre(50);
      }
      throw new Error('Nombre de paiements attendu : ' + nombre);
    }
    let boutons = await lignes(2);
    assert.ok(!page.textContent.includes('FACTURE-PAYEE'));
    boutons[0].click();
    boutons = await lignes(1);
    boutons[0].click();
    await lignes(0);
    assert.equal(envois.length, 2);
    assert.deepEqual(erreurs, []);
    console.log('OK : deux sources avec id réel, lignes déjà payées exclues, PUT simulés et retrait après paiement.');
  } finally { dom.window.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
