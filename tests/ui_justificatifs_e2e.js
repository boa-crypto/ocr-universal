/* Vraie API temporaire, lancée exclusivement par pytest test_justificatifs_e2e.py. */
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const [base, phase, fraisId] = process.argv.slice(2);
assert.equal(process.env.UNOCR_E2E_ISOLATED, '1', 'Utiliser pytest tests/test_justificatifs_e2e.py');
assert.equal(new URL(base).hostname, '127.0.0.1');
const attendre = ms => new Promise(r => setTimeout(r, ms));
async function jusque(condition, message) {
  const fin = Date.now() + 15000;
  while(Date.now() < fin) { if(condition()) return; await attendre(50); }
  throw new Error(message);
}
(async () => {
  const erreurs = [], ecritures = [], blobs = [];
  let confirmer = false;
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => { if(e.type !== 'not implemented') erreurs.push(e.message); });
  const dom = await JSDOM.fromURL(base + '/', {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: false, virtualConsole: vc,
    beforeParse(w) {
      // Évite la file rAF interne de jsdom 24 lors de window.close() sous Node 22.
      w.requestAnimationFrame = callback => w.setTimeout(() => callback(Date.now()), 16);
      w.cancelAnimationFrame = id => w.clearTimeout(id);
      w.scrollTo = () => {}; w.confirm = () => confirmer;
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.URL.createObjectURL = blob => { blobs.push(blob); return 'blob:test'; };
      w.URL.revokeObjectURL = () => {};
      w.HTMLAnchorElement.prototype.click = function () { assert.equal(this.download, 'piece-e2e.txt'); };
      w.fetch = async (url, options = {}) => {
        const cible = new URL(String(url), base), methode = options.method || 'GET';
        assert.equal(cible.origin, base);
        let transmis = options;
        if(options.body instanceof w.FormData) {
          // Pont de transport seulement : File jsdom → Blob/FormData natifs de Node.
          // Aucun endpoint ni réponse métier n'est simulé.
          const multipart = new FormData();
          for(const [cle, valeur] of options.body.entries()) {
            if(typeof valeur === 'string') multipart.append(cle, valeur);
            else {
              const octets = await new Promise((resolve, reject) => {
                const lecteur = new w.FileReader();
                lecteur.onload = () => resolve(new Uint8Array(lecteur.result));
                lecteur.onerror = () => reject(lecteur.error);
                lecteur.readAsArrayBuffer(valeur);
              });
              multipart.append(cle, new Blob([octets], { type: valeur.type }), valeur.name);
            }
          }
          transmis = { ...options, body: multipart };
        }
        transmis = { ...transmis, headers: { ...transmis.headers, connection: 'close' } };
        if(methode !== 'GET') {
          assert.ok((methode === 'POST' && cible.pathname === '/api/frais/justificatif/upload') ||
                    (methode === 'DELETE' && /^\/api\/frais\/justificatif\/just_[a-z0-9]+$/.test(cible.pathname)));
          ecritures.push(methode);
        }
        const rep = await fetch(cible, transmis).catch(error => {
          console.error('Échec fetch E2E ' + cible.href, error.cause || error);
          throw error;
        });
        if(!rep.ok) erreurs.push(cible.pathname + ' → ' + rep.status);
        return rep;
      };
    }
  });
  try {
    const w = dom.window, doc = w.document;
    await attendre(4500); w.location.hash = '#finance/frais-dossier';
    const page = doc.querySelector('#tab-ecran');
    let ouvrir;
    await jusque(() => (ouvrir = [...page.querySelectorAll('button')].find(b => b.textContent === 'Justificatifs')), 'Action pièces absente').catch(e => {
      const etat = {
        hash: w.location.hash,
        current: w.__ecranCourant && w.__ecranCourant.ecran.titre,
        page: page.textContent.slice(0, 800),
      };
      throw new Error(e.message + ' — ' + JSON.stringify(etat));
    });
    ouvrir.click();
    const boite = doc.querySelector('.ecran__boite[role=dialog]');
    await jusque(() => !boite.querySelector('[role=status]').textContent.includes('Chargement'), 'Liste non chargée');
    if(phase === 'ajouter') {
      const form = boite.querySelector('form'), fichier = form.querySelector('input[type=file]');
      Object.defineProperty(fichier, 'files', { value: [new w.File(['Pièce E2E réelle\n'], 'piece-e2e.txt', { type: 'text/plain' })] });
      form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
      await jusque(() => boite.querySelector('.ecran__piece'), 'Pièce non ajoutée : ' + boite.textContent);
      assert.deepEqual(ecritures, ['POST']);
    } else {
      assert.equal(phase, 'supprimer');
      assert.match(boite.textContent, /piece-e2e.txt/);
      [...boite.querySelectorAll('button')].find(b => b.textContent === 'Télécharger').click();
      await jusque(() => blobs.length === 1, 'Téléchargement manquant');
      assert.equal(await blobs[0].text(), 'Pièce E2E réelle\n');
      const supprimer = [...boite.querySelectorAll('button')].find(b => b.textContent === 'Supprimer la pièce');
      supprimer.click(); assert.deepEqual(ecritures, []);
      confirmer = true; supprimer.click();
      await jusque(() => boite.querySelector('[role=status]').textContent.includes('Aucun justificatif'), 'Pièce non supprimée');
      assert.deepEqual(ecritures, ['DELETE']);
    }
    assert.deepEqual(erreurs, []);
    console.log('OK E2E réel justificatifs : ' + phase + ', frais ' + fraisId);
  } finally { dom.window.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
