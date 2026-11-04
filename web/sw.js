/* Service worker UniOCR — cache de l'interface avec architecture refactorisée.
 *
 * Le service worker ne met JAMAIS en cache les réponses d'API : un document
 * importé, un export ou un résultat doit toujours venir du serveur local.
 * La coquille HTML et ses modules locaux sont stockés, pour que l'app
 * s'ouvre sans réseau. */
const CACHE = "unocr-shell-v4-refresh";
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
  "/web/cockpit.js",
  "/web/dossiers.js",
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                 // POST /api/* : jamais en cache
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;     // données fraîches obligatoires

  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) {
        // sert le cache, rafraîchit en arrière-plan
        fetch(req).then((fresh) => {
          if (fresh && fresh.ok) caches.open(CACHE).then((c) => c.put(req, fresh.clone()));
        }).catch(() => {});
        return hit;
      }
      return fetch(req).then((fresh) => {
        if (fresh && fresh.ok && url.origin === self.location.origin) {
          const copy = fresh.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return fresh;
      }).catch(() => caches.match("./index.html"));
    })
  );
});
