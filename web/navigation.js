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
        { key: 'verification', title: 'Vérification', route: '#documents/verification', icon: 'check-circle' },
        { key: 'archives', title: 'Archives', route: '#documents/archives', icon: 'archive' }
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
        { key: 'history', title: 'Historique contrôles', route: '#controle/historique', icon: 'history' }
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
        { key: 'arrivals', title: 'Suivi arrivées', route: '#maritime/arrivees', icon: 'trending-up' }
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
        { key: 'mainlevee', title: 'Mainlevées', route: '#douane/mainlevee', icon: 'unlock' }
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
        { key: 'proofs', title: 'Preuves de livraison', route: '#enlevissement/preuves', icon: 'check-circle' }
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
        { key: 'settings', title: 'Paramètres', route: '#referentiels/parametres', icon: 'settings' }
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
        { key: 'teams', title: 'Équipes', route: '#admin/equipes', icon: 'user-group' },
        { key: 'settings', title: 'Paramètres généraux', route: '#admin/parametres', icon: 'sliders' },
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
   * Générer le HTML de la navigation principale
   * @param {Array} roles - Les rôles de l'utilisateur
   * @returns {string}
   */
  function generateNavHTML(roles) {
    let html = '';

    // Cockpit - toujours visible (c'est la page d'accueil)
    const cockpit = NAV_CONFIG[0];
    html += generateNavItemHTML(cockpit, roles);

    // Autres sections selon permissions
    for (let i = 1; i < NAV_CONFIG.length; i++) {
      const section = NAV_CONFIG[i];
      if (hasSectionAccess(section.key, roles)) {
        html += generateNavItemHTML(section, roles);
      }
    }

    return html;
  }

  /**
   * Générer un élément de navigation
   * @param {object} section - Configuration de la section
   * @param {Array} roles - Les rôles de l'utilisateur
   * @returns {string}
   */
  function generateNavItemHTML(section, roles) {
    const activeClass = window.location.hash === section.route ? ' active' : '';
    const hasSubitems = section.subitems && section.subitems.length > 0;
    const chevron = hasSubitems ? '<span class="nav-chevron">▾</span>' : '';

    let html = `<a href="#${section.route.replace('#', '')}" class="nav-item${activeClass}" data-section="${section.key}">`;
    html += `<span class="nav-icon">${section.icon}</span>`;
    html += `<span class="nav-label">${section.title}</span>`;
    html += chevron;
    html += '</a>';

    // Sous-items si présents
    if (hasSubitems) {
      html += '<div class="nav-subitems">';
      section.subitems.forEach(sub => {
        const subActive = window.location.hash === sub.route ? ' active' : '';
        html += `<a href="#${sub.route.replace('#', '')}" class="nav-subitem${subActive}" data-route="${sub.route}">`;
        html += `<span class="nav-sublabel">${sub.title}</span>`;
        html += '</a>';
      });
      html += '</div>';
    }

    return html;
  }

  // Les entrées du menu sont des liens d'ancre (`href="#…"`) : le routage
  // natif du navigateur suffit. Ce point d'accroche reste explicite pour que
  // l'initialisation ne dépende pas d'un écouteur par lien.
  function attachNavListeners() {
    /* aucune écoute supplémentaire nécessaire */
  }

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
    // Retirer la classe active de tous les liens
    document.querySelectorAll('.nav-item, .nav-subitem').forEach(el => {
      el.classList.remove('active');
    });

    // Activer le lien principal
    const mainLink = document.querySelector(`.nav-item[data-section="${hash.replace('#', '')}"]`);
    if (mainLink) {
      mainLink.classList.add('active');
    }

    // Activer le lien sous-menu si applicable
    const subLink = document.querySelector(`.nav-subitem[data-route="${hash}"]`);
    if (subLink) {
      subLink.classList.add('active');
      // Activer aussi le parent
      const parent = subLink.closest('.nav-subitems');
      if (parent) {
        const parentItem = parent.previousElementSibling;
        if (parentItem && parentItem.classList.contains('nav-item')) {
          parentItem.classList.add('active');
        }
      }
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
      'documents': 'tab-documents',
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

    const pageId = pageMapping[sectionKey];
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
      }
    }
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