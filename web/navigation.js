/**
 * Navigation Dynamique UniOCR - Module principal
 * Gère le chargement des permissions RBAC, le routage hash et l'affichage
 * conditionnel des sections selon les droits de l'utilisateur.
 */
(function() {
  'use strict';

  // Configuration de navigation complète selon la spec
  const NAV_CONFIG = [
    {
      key: 'cockpit',
      title: 'Tableau de bord',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>',
      route: '#cockpit',
      requiredRole: 'lecteur',
      subitems: []
    },
    {
      key: 'workspace',
      title: 'Mon espace de travail',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4v16l12-8 4 8V4H4z"/></svg>',
      route: '#workspace',
      requiredRole: 'lecteur',
      subitems: [
        { key: 'my-tasks', title: 'Mes tâches', route: '#workspace/taches', icon: 'task' },
        { key: 'to-validate', title: 'À valider', route: '#workspace/valider', icon: 'validation' },
        { key: 'in-progress', title: 'En attente', route: '#workspace/en-attente', icon: 'clock' },
        { key: 'alerts', title: 'Mes alertes', route: '#workspace/alertes', icon: 'alert' },
        { key: 'recent-dossiers', title: 'Dossiers récents', route: '#workspace/recents', icon: 'folder' }
      ]
    },
    {
      key: 'dossiers',
      title: 'Gestion des dossiers',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
      route: '#dossiers',
      requiredRole: 'agent_de_transit',
      subitems: [
        { key: 'new-folder', title: 'Nouveau dossier', route: '#dossiers/nouveau', icon: 'plus' },
        { key: 'all-folders', title: 'Tous les dossiers', route: '#dossiers/tous', icon: 'folder' },
        { key: 'in-progress', title: 'Dossiers en cours', route: '#dossiers/en-cours', icon: 'clock' },
        { key: 'blocked', title: 'Dossiers bloqués', route: '#dossiers/bloques', icon: 'alert' },
        { key: 'closed', title: 'Dossiers clôturés', route: '#dossiers/clotures', icon: 'check' },
        { key: 'clients', title: 'Clients', route: '#dossiers/clients', icon: 'users' }
      ]
    },
    {
      key: 'documents',
      title: 'Documents & OCR',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
      route: '#documents',
      requiredRole: 'lecteur',
      subitems: [
        { key: 'scanner', title: 'Scanner / Importer', route: '#documents/import', icon: 'upload' },
        { key: 'inbox', title: 'Boîte de réception', route: '#documents/inbox', icon: 'inbox' },
        { key: 'classification', title: 'Classification', route: '#documents/classif', icon: 'tag' },
        { key: 'extraction', title: 'Extraction OCR', route: '#documents/ocr', icon: 'scan' },
        { key: 'result', title: "Résultat d'analyse", route: '#documents/resultat', icon: 'file-search' },
        { key: 'quality', title: 'Contrôle qualité', route: '#documents/qualite', icon: 'gauge' },
        { key: 'human-review', title: 'Révision humaine', route: '#documents/revue', icon: 'user-check' },
        { key: 'verification', title: 'Vérification', route: '#documents/verification', icon: 'check-circle' },
        { key: 'profiles', title: 'Profils d\'extraction', route: '#documents/profils', icon: 'sliders' },
        { key: 'connectors', title: 'Connecteur Hub', route: '#documents/connecteurs', icon: 'plug' },
        { key: 'settings', title: 'Configuration', route: '#documents/configuration', icon: 'settings' },
        { key: 'archives', title: 'Archives', route: '#documents/archives', icon: 'archive' },
        { key: 'versions', title: 'Gestion des versions', route: '#documents/versions', icon: 'history' }
      ]
    },
    {
      key: 'controle',
      title: 'Contrôle & conformité',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>',
      route: '#controle',
      requiredRole: 'controleur_documentaire',
      subitems: [
        { key: 'document-control', title: 'Contrôle documentaire', route: '#controle/documentaire', icon: 'check-square' },
        { key: 'comparison', title: 'Comparaison documents', route: '#controle/comparaison', icon: 'compare' },
        { key: 'missing', title: 'Documents manquants', route: '#controle/manquants', icon: 'minus' },
        { key: 'anomalies', title: 'Anomalies', route: '#controle/anomalies', icon: 'alert-triangle' },
        { key: 'history', title: 'Historique contrôles', route: '#controle/historique', icon: 'history' },
        { key: 'rules', title: 'Règles de contrôle', route: '#controle/regles', icon: 'list-checks' }
      ]
    },
    {
      key: 'maritime',
      title: 'Opérations maritimes',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 19l5-5 5 5 5-5 5 5v-5"/></svg>',
      route: '#maritime',
      requiredRole: 'agent_de_transit',
      subitems: [
        { key: 'port-calls', title: 'Escales', route: '#maritime/escales', icon: 'anchor' },
        { key: 'vessels', title: 'Navires', route: '#maritime/navires', icon: 'ship' },
        { key: 'voyages', title: 'Voyages', route: '#maritime/voyages', icon: 'route' },
        { key: 'bl', title: 'Connaissances B/L', route: '#maritime/bl', icon: 'file-text' },
        { key: 'containers', title: 'Conteneurs', route: '#maritime/conteneurs', icon: 'package' },
        { key: 'arrivals', title: 'Suivi arrivées', route: '#maritime/arrivees', icon: 'trending-up' },
        { key: 'deadlines', title: 'Échéances maritimes', route: '#maritime/echeances', icon: 'calendar-clock' }
      ]
    },
    {
      key: 'douane',
      title: 'Douane & réglementation',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9l2 2 4-4"/></svg>',
      route: '#douane',
      requiredRole: 'agent_de_transit',
      subitems: [
        { key: 'tariff', title: 'Classement tarifaire', route: '#douane/tarif', icon: 'code' },
        { key: 'declarations', title: 'Déclarations', route: '#douane/declarations', icon: 'file-plus' },
        { key: 'controls', title: 'Contrôles douaniers', route: '#douane/controles', icon: 'search-check' },
        { key: 'liquidation', title: 'Liquidation', route: '#douane/liquidation', icon: 'calculator' },
        { key: 'payments', title: 'Paiements', route: '#douane/paiements', icon: 'dollar' },
        { key: 'mainlevee', title: 'Mainlevées', route: '#douane/mainlevee', icon: 'unlock' },
        { key: 'authorizations', title: 'Autorisations', route: '#douane/autorisations', icon: 'badge-check' },
        { key: 'repository', title: 'Référentiel réglementaire', route: '#douane/referentiel', icon: 'book-open' }
      ]
    },
    {
      key: 'enlevissement',
      title: 'Enlèvement & livraison',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l2-2 4 4 4-4 4 4 4-4 4 4v10"/></svg>',
      route: '#enlevissement',
      requiredRole: 'agent_de_transit',
      subitems: [
        { key: 'orders', title: 'Ordres d\'enlèvement', route: '#enlevissement/ordres', icon: 'clipboard' },
        { key: 'planning', title: 'Planification', route: '#enlevissement/planning', icon: 'calendar' },
        { key: 'carriers', title: 'Transporteurs', route: '#enlevissement/transporteurs', icon: 'truck' },
        { key: 'exit-port', title: 'Sortie portuaire', route: '#enlevissement/sortie-port', icon: 'arrow-right' },
        { key: 'delivery', title: 'Livraison', route: '#enlevissement/livraison', icon: 'map-pin' },
        { key: 'proofs', title: 'Preuves de livraison', route: '#enlevissement/preuves', icon: 'check-circle' },
        { key: 'tracking', title: 'Suivi des opérations', route: '#enlevissement/suivi', icon: 'activity' }
      ]
    },
    {
      key: 'finance',
      title: 'Finance & facturation',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
      route: '#finance',
      requiredRole: 'responsable_financier',
      subitems: [
        { key: 'case-fees', title: 'Frais du dossier', route: '#finance/frais-dossier', icon: 'credit-card' },
        { key: 'debits', title: 'Débours', route: '#finance/debours', icon: 'wallet' },
        { key: 'supplier-invoices', title: 'Factures fournisseurs', route: '#finance/factures-fournisseurs', icon: 'file-minus' },
        { key: 'billing', title: 'Facturation client', route: '#finance/facturation', icon: 'file-plus' },
        { key: 'payments', title: 'Paiements', route: '#finance/paiements', icon: 'dollar-sign' },
        { key: 'reconciliation', title: 'Rapprochement', route: '#finance/reconciliation', icon: 'git-compare' },
        { key: 'closure', title: 'Clôture financière', route: '#finance/cloture', icon: 'ban' }
      ]
    },
    {
      key: 'reports',
      title: 'Rapports & statistiques',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 7v5l3 3"/></svg>',
      route: '#rapports',
      requiredRole: 'lecteur',
      subitems: [
        { key: 'statistics', title: 'Statistiques', route: '#rapports/statistiques', icon: 'bar-chart' },
        { key: 'charts', title: 'Graphiques', route: '#rapports/graphes', icon: 'line-chart' },
        { key: 'exports', title: 'Exports', route: '#rapports/exports', icon: 'download' }
      ]
    },
    {
      key: 'referentiels',
      title: 'Référentiels & paramètres',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg>',
      route: '#referentiels',
      requiredRole: 'lecteur',
      subitems: [
        { key: 'profiles', title: 'Profils', route: '#referentiels/profiles', icon: 'layers' },
        { key: 'doc-types', title: 'Types de documents', route: '#referentiels/types-documents', icon: 'file-text' },
        { key: 'clients', title: 'Clients', route: '#referentiels/clients', icon: 'users' },
        { key: 'suppliers', title: 'Fournisseurs', route: '#referentiels/fournisseurs', icon: 'factory' },
        { key: 'carriers', title: 'Transporteurs', route: '#referentiels/transporteurs', icon: 'truck' },
        { key: 'vessels', title: 'Navires', route: '#referentiels/navires', icon: 'ship' },
        { key: 'ports', title: 'Ports', route: '#referentiels/ports', icon: 'anchor' },
        { key: 'countries', title: 'Pays', route: '#referentiels/pays', icon: 'globe' },
        { key: 'currencies', title: 'Devises', route: '#referentiels/devises', icon: 'coins' },
        { key: 'goods', title: 'Types de marchandises', route: '#referentiels/types-marchandises', icon: 'package' },
        { key: 'tariffs', title: 'Référentiels tarifaires', route: '#referentiels/tarifs', icon: 'receipt' },
        { key: 'doc-rules', title: 'Règles documentaires', route: '#referentiels/regles-documentaires', icon: 'file-check' },
        { key: 'business', title: 'Paramètres métier', route: '#referentiels/parametres-metier', icon: 'sliders' },
        { key: 'settings', title: 'Paramètres généraux', route: '#referentiels/parametres', icon: 'sliders' }
      ]
    },
    {
      key: 'admin',
      title: 'Administration & sécurité',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m4.24-4.24l4.24-4.24"/></svg>',
      route: '#admin',
      requiredRole: 'administrateur',
      subitems: [
        { key: 'users', title: 'Utilisateurs', route: '#admin/utilisateurs', icon: 'users' },
        { key: 'roles', title: 'Rôles', route: '#admin/roles', icon: 'shield' },
        { key: 'permissions', title: 'Permissions', route: '#admin/permissions', icon: 'key-round' },
        { key: 'teams', title: 'Équipes', route: '#admin/equipes', icon: 'user-group' },
        { key: 'settings', title: 'Configuration & sécurité', route: '#admin/parametres', icon: 'shield' },
        { key: 'ocr-settings', title: 'Paramètres OCR', route: '#admin/parametres-ocr', icon: 'cpu' },
        { key: 'engines', title: 'Moteurs OCR', route: '#admin/moteurs-ocr', icon: 'database' },
        { key: 'connectors', title: 'Connecteurs API', route: '#admin/connecteurs-api', icon: 'plug' },
        { key: 'workflows', title: 'Workflows', route: '#admin/workflows', icon: 'git-branch' },
        { key: 'referentiels', title: 'Référentiels', route: '#admin/referentiels', icon: 'book-open' },
        { key: 'audit', title: 'Journal d\'audit', route: '#admin/journal', icon: 'scroll-text' },
        { key: 'backups', title: 'Sauvegardes', route: '#admin/sauvegardes', icon: 'save' }
      ]
    }
  ];

  // Hiérarchie des rôles RBAC (ordre croissant de privilèges)
  const ROLE_HIERARCHY = [
    'lecteur',
    'operateur',
    'superviseur',
    'agent_de_transit',
    'responsable_transit',
    'declarant_habile',
    'controleur_documentaire',
    'responsable_financier',
    'administrateur'
  ];

  // Éléments DOM
  let dom = {
    navContainer: null,
    pageSections: new Map(),
    currentHash: ''
  };

  /**
   * Charger les permissions RBAC de l'utilisateur
   */
  async function loadUserPermissions() {
    try {
      const token = sessionStorage.getItem('uniocr_token') || '';
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const response = await fetch('/api/rbac/moi', { headers });
      if (!response.ok) {
        // Pas de RBAC actif - comportement par défaut
        return { actif: false, roles: [], dossiers: [] };
      }
      return await response.json();
    } catch (error) {
      console.warn('[Navigation] Erreur chargement permissions:', error);
      return { actif: false, roles: [], dossiers: [] };
    }
  }

  /**
   * Vérifier si l'utilisateur a accès à une section
   * @param {string} sectionKey - La clé de la section NAV_CONFIG
   * @param {Array} roles - Les rôles de l'utilisateur
   * @returns {boolean}
   */
  function hasSectionAccess(sectionKey, roles) {
    const config = NAV_CONFIG.find(s => s.key === sectionKey);
    if (!config) return true;

    // RBAC inactif (aucun rôle fourni) : on n'enferme pas l'utilisateur.
    if (!roles.length) return true;

    // Administrateur a toujours accès
    if (roles.includes('administrateur')) return true;

    // Vérifier la hiérarchie des rôles
    const userHighestIndex = Math.max(...roles.map(r =>
      ROLE_HIERARCHY.indexOf(r)
    ));

    const requiredIndex = ROLE_HIERARCHY.indexOf(config.requiredRole);

    return userHighestIndex >= requiredIndex;
  }

  /**
   * Générer le HTML de la navigation principale.
   *
   * Le cockpit reste une entrée simple ; chaque autre section devient un
   * groupe repliable dont la première entrée ouvre la vue d'ensemble du
   * module. Chaque lien porte une infobulle (`data-tip`) utilisée quand la
   * barre latérale est réduite.
   */
  function generateNavHTML(roles) {
    var html = '';

    var cockpit = NAV_CONFIG[0];
    html += '<a href="#cockpit" class="nav-item' + (estActif(cockpit.route) ? ' active' : '') + '"';
    html += ' data-section="cockpit" data-tip="' + escAttr(cockpit.title) + '">';
    html += '<span class="nav-icon">' + cockpit.icon + '</span>';
    html += '<span class="nav-label">' + escAttr(cockpit.title) + '</span>';
    html += '</a>';

    for (var i = 1; i < NAV_CONFIG.length; i++) {
      var section = NAV_CONFIG[i];
      if (!hasSectionAccess(section.key, roles)) continue;
      html += generateGroupeHTML(section);
    }

    return html;
  }

  /* Sous-rubriques déclarées : sert à dire honnêtement quand un écran dédié
     n'existe pas encore, plutôt que d'afficher une page qui n'a rien à voir. */
  const SOUS_ROUTES = {};
  NAV_CONFIG.forEach(function (section) {
    (section.subitems || []).forEach(function (sub) {
      SOUS_ROUTES[String(sub.route).replace(/^#/, '')] =
        { titre: sub.title, section: section.title };
    });
  });

  function escAttr(valeur) {
    return String(valeur == null ? "" : valeur)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function estActif(route) {
    var hash = window.location.hash || "#cockpit";
    return hash === route || hash.indexOf(route + "/") === 0;
  }

  function groupeOuvert(section) {
    if (estActif(section.route)) return true;
    try {
      var memorise = localStorage.getItem("uniocr_nav_" + section.key);
      if (memorise === "1") return true;
      if (memorise === "0") return false;
    } catch (e) { /* stockage indisponible */ }
    return false;
  }

  function generateGroupeHTML(section) {
    var ouvert = groupeOuvert(section);
    var courant = estActif(section.route);
    var classes = "nav-group" + (ouvert ? " is-open" : "") + (courant ? " is-current" : "");

    var html = '<div class="' + classes + '" data-group="' + escAttr(section.key) + '">';
    html += '<button type="button" class="nav-group-toggle" aria-expanded="' + (ouvert ? "true" : "false") + '"';
    html += ' data-tip="' + escAttr(section.title) + '">';
    html += '<span class="nav-icon">' + section.icon + '</span>';
    html += '<span class="nav-label">' + escAttr(section.title) + '</span>';
    html += '<span class="nav-chevron" aria-hidden="true">';
    html += '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M9 6l6 6-6 6"/></svg>';
    html += '</span></button>';
    html += '<div class="nav-group-items"><div class="nav-group-inner">';

    html += '<a href="' + escAttr(section.route) + '" class="nav-subitem' + (estActif(section.route) && (window.location.hash || "") === section.route ? ' active' : '') + '"';
    html += ' data-route="' + escAttr(section.route) + '">Vue d\'ensemble</a>';

    (section.subitems || []).forEach(function (sub) {
      var actif = (window.location.hash || "") === sub.route ? ' active' : '';
      html += '<a href="' + escAttr(sub.route) + '" class="nav-subitem' + actif + '"';
      html += ' data-route="' + escAttr(sub.route) + '">' + escAttr(sub.title) + '</a>';
    });

    html += '</div></div></div>';
    return html;
  }

  /** Ouvrir/fermer un groupe et mémoriser l'état. */
  function basculerGroupe(bouton) {
    var groupe = bouton.closest('.nav-group');
    if (!groupe) return;
    var ouvert = groupe.classList.toggle('is-open');
    bouton.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    try {
      localStorage.setItem('uniocr_nav_' + groupe.dataset.group, ouvert ? '1' : '0');
    } catch (e) { /* stockage indisponible */ }
  }

  /** Le rail (barre réduite en icônes) s'active sous 1024 px. */
  function modeRail() {
    try {
      return window.matchMedia("(max-width: 1024px)").matches;
    } catch (e) {
      return false;
    }
  }

  function tiroir() {
    return document.getElementById("app");
  }

  /**
   * Ouvrir / fermer le tiroir de navigation (mode rail et mobile).
   * Sans cela, un clic sur une icône de groupe ne produisait aucun effet
   * visible : le sous-menu restait masqué par la mise en page compacte.
   */
  function basculerTiroir(ouvrir) {
    var app = tiroir();
    if (!app) return;
    var ouvert = typeof ouvrir === "boolean" ? ouvrir : !app.classList.contains("nav-open");
    app.classList.toggle("nav-open", ouvert);
    var burger = document.getElementById("navBurger");
    if (burger) burger.setAttribute("aria-expanded", ouvert ? "true" : "false");
    var repli = document.getElementById("sidebarCollapse");
    if (repli && modeRail()) {
      repli.setAttribute("aria-label", ouvert ? "Fermer le menu" : "Ouvrir le menu");
    }
  }

  // Un clic sur le titre d'un groupe le déplie ; l'entrée « Vue d'ensemble »
  // reste un lien vers la page du module. En mode rail, le premier clic ouvre
  // aussi le panneau complet.
  document.addEventListener('click', function (ev) {
    var app = tiroir();
    var bouton = ev.target && ev.target.closest ? ev.target.closest('.nav-group-toggle') : null;
    if (bouton) {
      ev.preventDefault();
      if (app && modeRail() && !app.classList.contains('nav-open')) {
        basculerTiroir(true);
      }
      basculerGroupe(bouton);
      return;
    }
    var lien = ev.target && ev.target.closest ? ev.target.closest('.nav-subitem, .nav-item') : null;
    if (lien) {
      if (app && modeRail()) basculerTiroir(false);
      return;
    }
    // Le clic hors du panneau est déjà traité par la coque (`shell.js`),
    // qui ignore le bouton d'ouverture : on ne duplique pas cette logique.
  });

  // Échap referme le panneau, comme tout menu superposé.
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    var app = tiroir();
    if (app && app.classList.contains('nav-open')) basculerTiroir(false);
  });

  // Les entrées du menu sont des liens d'ancre (`href="#…"`) : le routage
  // natif du navigateur suffit. Ce point d'accroche reste explicite pour que
  // l'initialisation ne dépende pas d'un écouteur par lien.
  function attachNavListeners() {
    /* aucune écoute supplémentaire nécessaire */
  }

  // Les anciennes pages « hub » (maritime, douane, finance…) sont des cartes
  // de boutons dont les écrans ne sont pas encore livrés. Plutôt qu'un clic
  // sans effet, on l'annonce clairement à l'utilisateur.
  document.addEventListener('click', function (ev) {
    const bouton = ev.target && ev.target.closest
      ? ev.target.closest('button.btn-block:not([id]):not([data-nav])')
      : null;
    if (!bouton) return;
    const libelle = (bouton.textContent || '').trim().replace(/\s+/g, ' ');
    if (typeof window.toast === 'function') {
      window.toast(`« ${libelle} » — fonction en préparation`, 'info');
    }
  });

  // Délégation : tout élément portant `data-nav="section/…"` navigue, sans
  // gestionnaire en ligne (une valeur d'API ne doit jamais finir dans du JS).
  document.addEventListener('click', function (ev) {
    const el = ev.target && ev.target.closest ? ev.target.closest('[data-nav]') : null;
    if (!el) return;
    ev.preventDefault();
    window.location.hash = '#' + el.getAttribute('data-nav');
  });

  /**
   * Initialiser la navigation
   */
  let initialise = false;

  function initNavigation() {
    if (initialise) return;
    initialise = true;

    window.addEventListener('hashchange', handleHashChange);

    // Le document hérité contient des balises déséquilibrées : le navigateur
    // peut sortir certaines sections de <main> (reparentage par les tableaux
    // malformés). On les replace toutes dans la zone de travail pour que la
    // mise en page (barre latérale + contenu) reste cohérente.
    const zone = document.querySelector("main.workspace");
    if (zone) {
      document.querySelectorAll("section.page").forEach(section => {
        if (section.parentElement !== zone) zone.appendChild(section);
      });
    }

    // Afficher immédiatement le cockpit : sans cela, toutes les sections
    // resteraient visibles les unes sous les autres tant que le hash est vide.
    if (!window.location.hash) {
      history.replaceState(null, '', '#cockpit');
    }
    handleHashChange();

    // Charger les permissions puis (re)construire le menu latéral.
    const rendreMenu = roles => {
      const container = document.getElementById('mainNav');
      if (!container) return;
      container.innerHTML = generateNavHTML(roles || []);
      attachNavListeners();
      updateActiveLinks(window.location.hash || '#cockpit');
    };

    rendreMenu([]);
    loadUserPermissions().then(p => rendreMenu(p.roles || []));
  }

  /**
   * Gérer le changement de hash dans l'URL
   */
  function handleHashChange() {
    const hash = window.location.hash || '#cockpit';
    dom.currentHash = hash;

    // Mettre à jour les liens actifs
    updateActiveLinks(hash);

    // Afficher/masquer les sections de page
    showPageSections(hash);
  }

  /**
   * Mettre à jour les liens actifs dans la navigation
   * @param {string} hash - L'hash actuel
   */
  function updateActiveLinks(hash) {
    hash = hash || window.location.hash || '#cockpit';
    document.querySelectorAll('.nav-item, .nav-subitem').forEach(function (el) {
      el.classList.remove('active');
      el.removeAttribute('aria-current');
    });
    document.querySelectorAll('.nav-group').forEach(function (groupe) {
      groupe.classList.remove('is-current');
    });

    var sectionKey = hash.replace('#', '').split('/')[0];
    var principal = document.querySelector('.nav-item[data-section="' + sectionKey + '"]');
    if (principal) {
      principal.classList.add('active');
      principal.setAttribute('aria-current', 'page');
    }

    var sous = document.querySelector('.nav-subitem[data-route="' + hash + '"]');
    if (sous) {
      sous.classList.add('active');
      sous.setAttribute('aria-current', 'page');
      var groupe = sous.closest('.nav-group');
      if (groupe) {
        groupe.classList.add('is-current', 'is-open');
        var bouton = groupe.querySelector('.nav-group-toggle');
        if (bouton) bouton.setAttribute('aria-expanded', 'true');
      }
    } else {
      var courant = document.querySelector('.nav-group[data-group="' + sectionKey + '"]');
      if (courant) courant.classList.add('is-current');
    }
  }

  /**
   * Afficher/masquer les sections de page correspondantes
   * @param {string} hash - L'hash actuel
   */
  function showPageSections(hash) {
    // Masquer d'abord toutes les sections de page
    document.querySelectorAll('section.page').forEach(section => {
      section.classList.add('hidden');
    });

    // Extraire la clé de section du hash
    const sectionKey = hash.replace('#', '').split('/')[0] || 'cockpit';

    // Mapper les clés de section vers les IDs de page existants
    const pageMapping = {
      'cockpit': 'tab-cockpit',
      'workspace': 'tab-workspace',
      'dossiers': 'tab-dossiers',
      'documents': 'tab-ecran',
      'controle': 'tab-controle',
      'maritime': 'tab-maritime',
      'douane': 'tab-douane',
      'enlevissement': 'tab-enlevissement',
      'finance': 'tab-finance',
      'reports': 'tab-reports',
      'rapports': 'tab-reports',
      'referentiels': 'tab-referentiels',
      'admin': 'tab-admin'
    };

    // Certaines sous-rubriques disposent de leur propre page : on y va
    // directement plutôt que de retomber sur la vue d'ensemble du module.
    const routePages = {
      'documents/import': 'tab-dashboard',
      'documents/ocr': 'tab-ecran',
      'documents/inbox': 'tab-center',
      'documents/classif': 'tab-classif',
      'documents/resultat': 'tab-result',
      'documents/qualite': 'tab-quality',
      'documents/revue': 'tab-review',
      'documents/profils': 'tab-profiles',
      'documents/connecteurs': 'tab-connectors',
      'documents/configuration': 'tab-config',
      'dossiers/parcours': 'tab-dossier',
      'maritime/transit': 'tab-transit',
      'documents/verification': 'tab-validation',
      'documents/archives': 'tab-ged',
      'controle/anomalies': 'tab-anomalies',
      'controle/manquants': 'tab-manquants',
      'maritime/conteneurs': 'tab-conteneurs',
      'maritime/bl': 'tab-bl',
      'maritime/navires': 'tab-navires',
      'maritime/arrivees': 'tab-eta-etd',
      'douane/declarations': 'tab-declarations',
      'douane/tarif': 'tab-nomenclature',
      'douane/mainlevee': 'tab-mainleves',
      'enlevissement/ordres': 'tab-enlevement',
      'enlevissement/planning': 'tab-planification',
      'enlevissement/transporteurs': 'tab-transporteurs',
      'admin/journal': 'tab-journal',
      'admin/utilisateurs': 'tab-ecran',
      'admin/roles': 'tab-ecran',
      'admin/moteurs': 'tab-moteurs',
      'admin/moteurs-ocr': 'tab-moteurs',
      'admin/connecteurs-api': 'tab-connecteurs-api',
      'admin/workflows': 'tab-workflows',
      'admin/sauvegardes': 'tab-sauvegardes',

      /* Écrans métier déclaratifs (`web/ecrans.js`) : une section hôte,
         un rendu par route, alimenté par les routes réelles de l'API. */
      /* Sous-rubriques qui ouvrent une page réellement existante de la coquille :
         on les relie pour supprimer le bandeau « pas encore d'écran dédié ». */
      'dossiers/en-cours': 'tab-ecran',
      'dossiers/clotures': 'tab-ecran',
      'dossiers/bloques': 'tab-ecran',
      'workspace/taches': 'tab-ecran',
      'workspace/en-attente': 'tab-ecran',
      'workspace/alertes': 'tab-ecran',
      'workspace/recents': 'tab-ecran',
      'dossiers/tous': 'tab-dossiers',
      'dossiers/nouveau': 'tab-dossiers',
      'dossiers/clients': 'tab-ecran',
      'workspace/valider': 'tab-validation',
      'referentiels/profiles': 'tab-profiles',

      'controle/documentaire': 'tab-ecran',
      'controle/comparaison': 'tab-ecran',
      'controle/historique': 'tab-ecran',
      'controle/regles': 'tab-ecran',
      'maritime/escales': 'tab-ecran',
      'maritime/voyages': 'tab-ecran',
      'maritime/echeances': 'tab-ecran',
      'douane/controles': 'tab-ecran',
      'douane/liquidation': 'tab-ecran',
      'douane/paiements': 'tab-ecran',
      'douane/autorisations': 'tab-ecran',
      'douane/referentiel': 'tab-ecran',
      'enlevissement/sortie-port': 'tab-ecran',
      'enlevissement/livraison': 'tab-ecran',
      'enlevissement/preuves': 'tab-ecran',
      'enlevissement/suivi': 'tab-ecran',
      'finance/frais-dossier': 'tab-ecran',
      'finance/debours': 'tab-ecran',
      'finance/factures-fournisseurs': 'tab-ecran',
      'finance/facturation': 'tab-ecran',
      'finance/paiements': 'tab-ecran',
      'finance/reconciliation': 'tab-ecran',
      'finance/cloture': 'tab-ecran',
      'rapports/graphes': 'tab-graphiques',
      'rapports/statistiques': 'tab-ecran',
      'rapports/exports': 'tab-ecran',
      'referentiels/clients': 'tab-ecran',
      'referentiels/fournisseurs': 'tab-ecran',
      'referentiels/transporteurs': 'tab-ecran',
      'referentiels/navires': 'tab-ecran',
      'referentiels/ports': 'tab-ecran',
      'referentiels/pays': 'tab-ecran',
      'referentiels/devises': 'tab-ecran',
      'referentiels/types-marchandises': 'tab-ecran',
      'referentiels/tarifs': 'tab-ecran',
      'referentiels/regles-documentaires': 'tab-ecran',
      'referentiels/parametres-metier': 'tab-ecran',
      'referentiels/parametres': 'tab-ecran',
      'referentiels/types-documents': 'tab-ecran',
      'admin/permissions': 'tab-ecran',
      'admin/equipes': 'tab-ecran',
      'admin/referentiels': 'tab-ecran',
      'admin/parametres': 'tab-ecran',
      'admin/parametres-ocr': 'tab-ecran',
      'documents/versions': 'tab-ecran'
    };

    const pageId = routePages[hash.replace('#', '')] || pageMapping[sectionKey];
    if (pageId) {
      // Les sections héritées peuvent être dupliquées : la dernière est la
      // version courante.
      const candidats = document.querySelectorAll(`section.page[id="${pageId}"]`);
      const page = candidats.length ? candidats[candidats.length - 1] : null;
      if (page) {
        page.classList.remove('hidden');
        // Trigger reflow for animation
        void page.offsetWidth;
        page.classList.add('page-enter');
        signalerEcranAbsent(page, hash.replace('#', ''), Boolean(routePages[hash.replace('#', '')]));
      }
    }
  }

  /**
   * Une sous-rubrique sans écran dédié retombe sur la vue d'ensemble de son
   * module : on l'annonce, sans quoi l'utilisateur croit s'être trompé de page.
   */
  function signalerEcranAbsent(page, aiguille, aSaProprePage) {
    document.querySelectorAll('[data-avis-route]').forEach(function (avis) {
      avis.remove();
    });
    if (aSaProprePage) return;
    const sous = SOUS_ROUTES[aiguille];
    if (!sous) return;

    const avis = document.createElement('p');
    avis.className = 'avis-route';
    avis.setAttribute('data-avis-route', aiguille);
    avis.setAttribute('role', 'note');
    avis.textContent = '« ' + sous.titre + ' » n\'a pas encore d\'écran dédié sur ce ' +
      'poste. Les accès ci-dessous mènent aux écrans réellement disponibles pour « ' +
      sous.section + ' ».';
    const entete = page.querySelector('header');
    if (entete) entete.parentNode.insertBefore(avis, entete.nextSibling);
    else page.insertBefore(avis, page.firstChild);
  }

  /**
   * Naviguer vers une section spécifique
   * @param {string} sectionKey - La clé de la section NAV_CONFIG
   */
  function navigateToSection(sectionKey) {
    const config = NAV_CONFIG.find(s => s.key === sectionKey);
    if (config) {
      window.location.hash = config.route;
    }
  }

  // Exposer les fonctions publiques (index.html appelle Navigation.init()).
  window.Navigation = {
    init: initNavigation,
    hasSectionAccess,
    navigateToSection,
    getConfig: () => NAV_CONFIG
  };
})();