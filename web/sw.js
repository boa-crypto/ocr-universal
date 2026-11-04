/* Service worker UniOCR — cache de l'interface avec architecture refactorisée.
 *
 * Le service worker ne met JAMAIS en cache les réponses d'API : un document
 * importé, un export ou un résultat doit toujours venir du serveur local.
 * La coquille HTML et ses modules locaux sont stockés, pour que l'app
 * s'ouvre sans réseau. */
const CACHE = "unocr-shell-v38-finances-persistantes";
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./manifest.webmanifest",
  "./icon.svg",
  "./modules/i18n-controls.js",
  "./connectors.js",
  "./dossier.js",
  "./formulaire.js",
  "./tracabilite.js",
  "./transmission.js",
  "/web/refresh.css",
  "/web/uniocr-ds.css",
  "/web/palette.js",
  "/web/charts.js",
  "/web/shell.js",
  "/web/modules.js",
  "/web/rapports.js",
  "/web/souspages.js",
  "/web/navigation.js",
  "/web/cockpit.js",
  "/web/app-legacy.js",
  "/web/app-extras.js",
  "/web/dossiers.js",
  "/web/workspace.js",
  "/web/ecrans.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* Stratégie :
 *   - coquille (navigation, HTML, JS, CSS) → RÉSEAU D'ABORD : une correction
 *     livrée est visible au premier rechargement, jamais une version périmée ;
 *   - ressources statiques (icônes, polices locales) → cache d'abord, avec
 *     rafraîchissement en arrière-plan ;
 *   - hors ligne : on retombe sur le cache, puis sur la coquille. */
function estCoquille(req, url) {
  if (req.mode === "navigate") return true;
  if (url.pathname === "/" || url.pathname.endsWith("/index.html")) return true;
  return /\.(js|css|webmanifest)$/.test(url.pathname);
}

function mettreEnCache(req, reponse) {
  if (!reponse || !reponse.ok) return reponse;
  const copie = reponse.clone();
  caches.open(CACHE).then((c) => c.put(req, copie)).catch(() => {});
  return reponse;
}

function reseauDAbord(req) {
  return fetch(req)
    .then((fraiche) => mettreEnCache(req, fraiche))
    .catch(() =>
      caches.match(req).then((entree) => entree || caches.match("./index.html"))
    );
}

function cacheDAbord(req) {
  return caches.match(req).then((entree) => {
    if (entree) {
      fetch(req)
        .then((fraiche) => mettreEnCache(req, fraiche))
        .catch(() => {});
      return entree;
    }
    return fetch(req)
      .then((fraiche) => mettreEnCache(req, fraiche))
      .catch(() => caches.match("./index.html"));
  });
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                 // POST /api/* : jamais en cache
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;  // ressources tierces : réseau direct
  if (url.pathname.startsWith("/api/")) return;     // données fraîches obligatoires

  event.respondWith(estCoquille(req, url) ? reseauDAbord(req) : cacheDAbord(req));
});
