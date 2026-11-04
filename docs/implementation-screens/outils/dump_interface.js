/* Instantané de l'interface réelle : menu, écrans, et ce que chaque route affiche.
 *
 * Usage (depuis la racine du dépôt, serveur démarré) :
 *   npm install --no-save jsdom
 *   node docs/implementation-screens/outils/dump_interface.js http://127.0.0.1:8000 > /tmp/ui.json
 *   python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
 *
 * Le script charge l'application dans jsdom (comme un navigateur), laisse les
 * modules s'initialiser, puis parcourt **toutes** les routes du menu en
 * enregistrant ce qui s'affiche réellement : section visible, nombre de lignes
 * de tableau, bandeau « pas encore d'écran dédié ». C'est la seule source
 * fiable pour savoir ce qu'un utilisateur obtient en cliquant.
 */
const {JSDOM, VirtualConsole} = require('jsdom');
const realFetch = global.fetch;
const base = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

JSDOM.fromURL(base + '/', {
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
  virtualConsole: new VirtualConsole(),
  beforeParse(w) {
    w.fetch = (u, o) => {
      const s = String(u);
      return realFetch(s.startsWith('http') ? s : base + (s.startsWith('/') ? s : '/' + s), o);
    };
    w.scrollTo = () => {};
    w.matchMedia = w.matchMedia || (() => ({
      matches: false, addEventListener() {}, removeEventListener() {},
      addListener() {}, removeListener() {},
    }));
  },
}).then(async (d) => {
  const w = d.window;
  const doc = w.document;
  await attendre(4500);

  /* Titre de menu sans la pastille de comptage (« À valider185 » → « À valider »). */
  const titreDe = (el) => {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('.nav-badge').forEach((b) => b.remove());
    return clone.textContent.replace(/\s+/g, ' ').trim();
  };

  const nav = doc.getElementById('mainNav');
  const sections = [];
  nav.querySelectorAll(':scope > .nav-item, :scope > .nav-group').forEach((el) => {
    if (el.classList.contains('nav-item')) {
      const titre = titreDe(el.querySelector('.nav-label'));
      sections.push({section: titre, items: [{titre, route: el.dataset.section}]});
      return;
    }
    const titre = titreDe(el.querySelector('.nav-group-toggle .nav-label'));
    const items = [...el.querySelectorAll('.nav-subitem')].map((a) => ({
      titre: titreDe(a),
      route: (a.dataset.route || a.getAttribute('href') || '').replace(/^#/, ''),
    }));
    sections.push({section: titre, items});
  });

  const ecrans = {};
  for (const [cle, valeur] of Object.entries(w.UniOCREcrans.ecrans)) {
    ecrans[cle] = {
      titre: valeur.titre,
      desc: valeur.desc,
      source: (valeur.source && valeur.source.url) || null,
      composite: Boolean(valeur.source && typeof valeur.source.charger === 'function'),
      sources: valeur.sources || ((valeur.source && valeur.source.url) ? [valeur.source.url] : []),
      creation: (valeur.creation && valeur.creation.url) || null,
      edition: Boolean(valeur.edition),
      suppression: Boolean(valeur.suppression),
      lectureSeule: Boolean(valeur.lectureSeule),
      actions: (valeur.actions || []).map((a) => ({
        libelle: a.libelle, route: a.route || null, url: a.url || null,
      })),
    };
  }

  /* Parcours réel de chaque route du menu. */
  for (const section of sections) {
    for (const item of section.items) {
      w.location.hash = '#' + item.route;
      await attendre(520);
      const visibles = [...doc.querySelectorAll('section.page')].filter((s) => {
        const style = w.getComputedStyle(s);
        return style.display !== 'none' && !s.classList.contains('hidden');
      });
      const page = visibles[0] || null;
      const avis = page ? page.querySelector('.avis-route') : null;
      const ecran = page ? page.querySelector('.ecran__titre') : null;
      item.mesure = {
        page: page ? page.id : null,
        pages_visibles: visibles.map((s) => s.id),
        lignes: page ? page.querySelectorAll('tbody tr').length : 0,
        cartes: page
          ? page.querySelectorAll('tbody tr, .card, .dossier-row, .list-item, .empty, .empty-state').length
          : 0,
        contenu: page ? page.textContent.replace(/\s+/g, ' ').trim().length : 0,
        titre_ecran: ecran ? ecran.textContent.trim() : null,
        avis: avis ? avis.textContent.trim().slice(0, 120) : null,
      };
    }
  }

  console.log(JSON.stringify({sections, ecrans}, null, 1));
  w.close();
  process.exit(0);
}).catch((e) => {
  console.log('FATAL ' + e.message);
  process.exit(1);
});
