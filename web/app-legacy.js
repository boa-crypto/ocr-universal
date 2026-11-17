/* Correctif : le code applicatif appelle api(...) mais seule fetchJson était
   définie, ce qui faisait échouer silencieusement initLangChips() — les puces
   de langue ne se chargeaient donc jamais. On rétablit api comme alias. */
if (typeof api !== "function") {
  var api = function (path, opts) { return fetchJson(path, opts); };
}

/* =================== STATE =================== */
let API = localStorage.getItem("unocr_api") || "";
let currentJob = null, currentResult = null, currentPage = 1, currentFile = null;
let MOI = null;   // identite et droits renvoyés par /api/rbac/moi
let connected = false;

/* Parse d'erreur robuste : l'API renvoie du JSON, un proxy peut renvoyer du texte brut */
async function readError(r) {
  const text = (await r.text().catch(() => "")).trim();
  try {
    const j = JSON.parse(text);
    return j.detail || j.message || text || ("HTTP " + r.status);
  } catch {
    return ("HTTP " + r.status + " — " + (text.slice(0, 120) || "réponse invalide"));
  }
}

function apiUrl(path) { return (API || "") + path; }

/* Jeton d'authentification. Quand data/rbac.json existe, l'API exige un
   jeton ; il est conserve dans localStorage et envoye a chaque appel. Sans
   RBAC actif, rien n'est envoye et l'application se comporte comme avant. */
var JETON = null;
try { JETON = localStorage.getItem("unocr.jeton") || null; } catch (e) { JETON = null; }

function definirJeton(valeur) {
  JETON = valeur ? String(valeur).trim() : null;
  try {
    if (JETON) localStorage.setItem("unocr.jeton", JETON);
    else localStorage.removeItem("unocr.jeton");
  } catch (e) { /* stockage indisponible : le jeton ne survit pas au rechargement */ }
  majEnteteJeton();
}
function entetesJeton(opts) {
  if (!JETON) return opts;
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers, { Authorization: "Bearer " + JETON });
  return opts;
}

async function fetchAuthenticated(path, opts) {
  const r = await fetch(apiUrl(path), entetesJeton(opts));
  if (r.status === 401 && path.indexOf("/api/rbac/moi") !== 0) {
    definirJeton(null);
    demanderJeton();
    throw new Error("Session expirée ou jeton inconnu — reconnexion demandée.");
  }
  return r;
}

async function fetchJson(path, opts) {
  const r = await fetchAuthenticated(path, opts);
  if (!r.ok) throw new Error(await readError(r));
  try { return await r.json(); }
  catch { throw new Error("Réponse illisible du serveur (contenu non-JSON)"); }
}

const PAGE_META = {
  "tab-import": ["Importer un document", "Analyse visuelle et textuelle → données structurées"],
  "tab-docs": ["Documents", "Historique des traitements et suivi des jobs"],
  "tab-result": ["Résultat d'analyse", "Texte, champs, tableaux — reliés au document source"],
  "tab-quality": ["Contrôle qualité", "Confiances, anomalies et cohérence métier"],
  "tab-config": ["Configuration", "Moteurs, langues et profils réellement disponibles"],
  "tab-dashboard": ["Tableau de bord", "Activité et ressources système"],
  "tab-review": ["Révision humaine", "Vérification et correction avant toute transmission"],
  "tab-profiles": ["Profils métier", "Champs, motifs et validateurs réutilisables"],
  "tab-connectors": ["Connecteur Hub", "Transmission vers les systèmes externes, sous contrôle humain"],
  "tab-dossier": ["Parcours documentaire", "Dossier, cohérence entre documents et paquet de données"],
};


/* =================== NAVIGATION DATA: NEW STRUCTURE PER SPEC =================== */
const NAVIGATION = [
  {
    key: "nav.cockpit",
    title: "COCKPIT",
    icon: "M3 12l2-2m0 0l7-7 7 7-5 5v10",
    subtabs: [
      { key: "tab-cockpit", title: "Cockpit", i18n: "nav.cockpit" }
    ]
  },
  {
    key: "nav.workspace",
    title: "MON ESPACE DE TRAVAIL",
    icon: "M12 3l8 4v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V7zM9 12l2 2 4-4",
    subtabs: [
      { key: "tab-mes-taches", title: "Mes tâches", i18n: "nav.mes-taches" },
      { key: "tab-a-valider", title: "À valider", i18n: "nav.a-valider" },
      { key: "tab-en-attente", title: "En attente", i18n: "nav.en-attente" },
      { key: "tab-mes-alertes", title: "Mes alertes", i18n: "nav.mes-alertes" },
      { key: "tab-dossiers-recents", title: "Mes dossiers récents", i18n: "nav.dossiers-recents" }
    ]
  },
  {
    key: "nav.dossiers",
    title: "GESTION DES DOSSIERS",
    icon: "M3 7h18M3 12h18M3 17h18",
    subtabs: [
      { key: "tab-nouveau-dossier", title: "Nouveau dossier", i18n: "nav.dossiers" },
      { key: "tab-tous", title: "Tous les dossiers", i18n: "nav.transit" },
      { key: "tab-en-cours", title: "Dossiers en cours", i18n: "nav.transit" },
      { key: "tab-bloques", title: "Dossiers bloqués", i18n: "nav.transit" },
      { key: "tab-clotures", title: "Dossiers clôturés", i18n: "nav.transit" },
      { key: "tab-clients", title: "Clients", i18n: "nav.clients" }
    ]
  },
  {
    key: "nav.documents",
    title: "DOCUMENTS & OCR",
    icon: "M4 4h16v5a2 2 0 01-2 2H6a2 2 0 01-2-2zM8 15h8M8 19h5",
    subtabs: [
      { key: "tab-scan-import", title: "Scanner / Importer", i18n: "nav.documents" },
      { key: "tab-boite-reception", title: "Boîte de réception", i18n: "nav.documents" },
      { key: "tab-classif", title: "Classification", i18n: "nav.documents" },
      { key: "tab-ocr", title: "Extraction OCR", i18n: "nav.documents" },
      { key: "tab-validation", title: "Vérification des données", i18n: "nav.documents" },
      { key: "tab-archives", title: "Archives", i18n: "nav.documents" }
    ]
  },
  {
    key: "nav.controle",
    title: "CONTRÔLE & CONFORMITÉ",
    icon: "M12 3l8 4v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V7zM9 12l2 2 4-4",
    subtabs: [
      { key: "tab-doc-ctrl", title: "Contrôle documentaire", i18n: "nav.controles" },
      { key: "tab-comparaison", title: "Comparaison des documents", i18n: "nav.controles" },
      { key: "tab-manquants", title: "Documents manquants", i18n: "nav.controles" },
      { key: "tab-anomalies", title: "Anomalies", i18n: "nav.controles" },
      { key: "tab-historique-controles", title: "Historique des contrôles", i18n: "nav.controles" }
    ]
  },
  {
    key: "nav.operations",
    title: "OPÉRATIONS MARITIMES",
    icon: "M9 7H6a3 3 0 000 6h3M15 17h3a3 3 0 000-6h-3M8 10h8",
    subtabs: [
      { key: "tab-escales", title: "Escales", i18n: "nav.operations" },
      { key: "tab-navires", title: "Navires", i18n: "nav.operations" },
      { key: "tab-voyages", title: "Voyages", i18n: "nav.operations" },
      { key: "tab-bl", title: "Connaissements B/L", i18n: "nav.operations" },
      { key: "tab-conteneurs", title: "Conteneurs", i18n: "nav.operations" },
      { key: "tab-suivi-arrivees", title: "Suivi des arrivées", i18n: "nav.operations" }
    ]
  },
  {
    key: "nav.douane",
    title: "DOUANE & RÉGLEMENTATION",
    icon: "M12 3l8 4v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V7zM9 12l2 2 4-4",
    subtabs: [
      { key: "tab-classement", title: "Classement tarifaire", i18n: "nav.douane" },
      { key: "tab-declarations", title: "Déclarations", i18n: "nav.douane" },
      { key: "tab-controles-douane", title: "Contrôles douaniers", i18n: "nav.douane" },
      { key: "tab-liquidation", title: "Liquidation", i18n: "nav.douane" },
      { key: "tab-paiements", title: "Paiements", i18n: "nav.douane" },
      { key: "tab-mainleves", title: "Mainlevées", i18n: "nav.douane" }
    ]
  },
  {
    key: "nav.enlevement",
    title: "ENLÈVEMENT & LIVRAISON",
    icon: "M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7zM9 13h6M9 16h4",
    subtabs: [
      { key: "tab-ordres-enlevement", title: "Ordres d'enlèvement", i18n: "nav.enlevement" },
      { key: "tab-planification", title: "Planification", i18n: "nav.enlevement" },
      { key: "tab-transporteurs", title: "Transporteurs", i18n: "nav.enlevement" },
      { key: "tab-sortie-portuaire", title: "Sortie portuaire", i18n: "nav.enlevement" },
      { key: "tab-livraison", title: "Livraison", i18n: "nav.enlevement" },
      { key: "tab-preuves-livraison", title: "Preuves de livraison", i18n: "nav.enlevement" }
    ]
  },
  {
    key: "nav.finance",
    title: "FINANCE & FACTURATION",
    icon: "M4 20V10M10 20V4M16 20v-8M22 20H2",
    subtabs: [
      { key: "tab-frais-dossier", title: "Frais du dossier", i18n: "nav.finance" },
      { key: "tab-debours", title: "Débours", i18n: "nav.finance" },
      { key: "tab-factures-fournisseurs", title: "Factures fournisseurs", i18n: "nav.finance" },
      { key: "tab-facturation-client", title: "Facturation client", i18n: "nav.finance" },
      { key: "tab-paiements", title: "Paiements", i18n: "nav.finance" },
      { key: "tab-rapprochement", title: "Rapprochement", i18n: "nav.finance" },
      { key: "tab-cloture-financiere", title: "Clôture financière", i18n: "nav.finance" }
    ]
  },
  {
    key: "nav.rapports",
    title: "RAPPORTS & STATISTIQUES",
    icon: "M3 7h18M3 12h18M3 17h18",
    subtabs: [
      { key: "tab-rapports", title: "Rapports & Statistiques", i18n: "nav.rapports" }
    ]
  },
  {
    key: "nav.referentiels",
    title: "RÉFÉRENTIELS & PARAMÈTRES",
    icon: "M12 3l8 4v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V7zM9 12l2 2 4-4",
    subtabs: [
      { key: "tab-referentiels", title: "Référentiels", i18n: "nav.referentiels" },
      { key: "tab-parametres", title: "Paramètres", i18n: "nav.admin" }
    ]
  },
  {
    key: "nav.admin",
    title: "ADMINISTRATION & SÉCURITÉ",
    icon: "M12 3l8 4v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V7zM9 12l2 2 4-4",
    subtabs: [
      { key: "tab-utilisateurs", title: "Utilisateurs", i18n: "nav.admin" },
      { key: "tab-roles", title: "Rôles et permissions", i18n: "nav.admin" },
      { key: "tab-equipes", title: "Équipes", i18n: "nav.admin" },
      { key: "tab-params-gen", title: "Paramètres généraux", i18n: "nav.admin" },
      { key: "tab-params-ocr", title: "Paramètres OCR", i18n: "nav.admin" },
      { key: "tab-moteurs", title: "Moteurs OCR", i18n: "nav.admin" },
      { key: "tab-connecteurs-api", title: "Connecteurs API", i18n: "nav.admin" },
      { key: "tab-workflows", title: "Workflows", i18n: "nav.admin" },
      { key: "tab-referentiels", title: "Référentiels", i18n: "nav.admin" },
      { key: "tab-journal", title: "Journal d'audit", i18n: "nav.admin" },
      { key: "tab-sauvegardes", title: "Sauvegardes", i18n: "nav.admin" },
      { key: "tab-config-sys", title: "Configuration système", i18n: "nav.admin" }
    ]
  }
];

/* =================== SHOW SUBTAB PAGE =================== */
function showSubtabPage(subtabKey) {
  // Hide all page sections
  document.querySelectorAll("section.page").forEach(s => {
    s.classList.add("hidden");
    s.classList.remove("page-enter");
  });

  // Show the selected page section based on the subtab key
  // Map subtab keys to existing page IDs
  const pageMap = {
    "tab-import": "tab-import",
    "tab-docs": "tab-docs",
    "tab-result": "tab-result",
    "tab-quality": "tab-quality",
    "tab-config": "tab-config",
    "tab-dashboard": "tab-dashboard",
    "tab-review": "tab-review",
    "tab-profiles": "tab-profiles",
    "tab-connectors": "tab-connectors",
    "tab-dossier": "tab-dossier",
    "tab-transit": "tab-transit",
    "tab-utilisateurs": "tab-utilisateurs",
    "tab-roles": "tab-roles",
    "tab-equipes": "tab-equipes",
    "tab-params-gen": "tab-params-gen",
    "tab-params-ocr": "tab-params-ocr",
    "tab-moteurs": "tab-moteurs",
    "tab-connecteurs-api": "tab-connecteurs-api",
    "tab-workflows": "tab-workflows",
    "tab-referentiels": "tab-referentiels",
    "tab-journal": "tab-journal",
    "tab-sauvegardes": "tab-sauvegardes",
    "tab-config-sys": "tab-config-sys",
    "tab-clients": "tab-clients",
    "tab-fournisseurs": "tab-fournisseurs",
    "tab-compagnes": "tab-compagnes",
    "tab-transporteurs": "tab-transporteurs",
    "tab-banques": "tab-banques",
    "tab-prestataires": "tab-prestataires",
    "tab-mandats": "tab-mandats",
    "tab-contacts": "tab-contacts",
    "tab-center": "tab-center",
    "tab-import-2": "tab-import-2",
    "tab-ocr": "tab-ocr",
    "tab-classif": "tab-classif",
    "tab-validation": "tab-validation",
    "tab-controle": "tab-controle",
    "tab-anomalies": "tab-anomalies",
    "tab-manquants": "tab-manquants",
    "tab-ged": "tab-ged",
    "tab-expeditions": "tab-expeditions",
    "tab-navires": "tab-navires",
    "tab-eta-etd": "tab-eta-etd",
    "tab-avis": "tab-avis",
    "tab-bl": "tab-bl",
    "tab-conteneurs": "tab-conteneurs",
    "tab-bad": "tab-bad",
    "tab-frais": "tab-frais",
    "tab-surestaries": "tab-surestaries",
    "tab-declarations": "tab-declarations",
    "tab-decl-en-douane": "tab-decl-en-douane",
    "tab-nomenclature": "tab-nomenclature",
    "tab-recherche": "tab-recherche",
    "tab-regimes": "tab-regimes",
    "tab-valeur": "tab-valeur",
    "tab-droits": "tab-droits",
    "tab-reg-alg": "tab-reg-alg",
    "tab-autorisations": "tab-autorisations",
    "tab-historique": "tab-historique",
    "tab-mainleves": "tab-mainleves",
    "tab-inspection": "tab-inspection",
    "tab-doc-ctrl": "tab-doc-ctrl",
    "tab-conformite": "tab-conformite",
    "tab-phytosan": "tab-phytosan",
    "tab-veterinaire": "tab-veterinaire",
    "tab-analyses": "tab-analyses",
    "tab-certificats": "tab-certificats",
    "tab-decision": "tab-decision",
    "tab-terminal": "tab-terminal",
    "tab-disponibilite": "tab-disponibilite",
    "tab-frais-portuaires": "tab-frais-portuaires",
    "tab-enlevement": "tab-enlevement",
    "tab-planification": "tab-planification",
    "tab-bons-sortie": "tab-bons-sortie",
    "tab-mouvements": "tab-mouvements"
  };

  // Au chargement, activer le premier sous-menu de chaque catégorie
  document.addEventListener("DOMContentLoaded", () => {
    // Pour chaque groupe de navigation, activer le premier sous-menu
    document.querySelectorAll(".nav-group").forEach((group, groupIndex) => {
      const firstSubitem = group.querySelector(".nav-subitem");
      if (firstSubitem) {
        // Remove active from all, add to first
        group.querySelectorAll(".nav-subitem").forEach(b => b.classList.remove("active"));
        firstSubitem.classList.add("active");

        // Show the corresponding page
        const subtabKey = firstSubitem.dataset.subtab;
        showSubtabPage(subtabKey);
      }
    });
  });

  // Repli par convention : la clé de sous-onglet est aussi l'identifiant de
  // section (tab-dossiers, tab-maritime, tab-admin…). Certaines sections
  // héritées apparaissent plusieurs fois : on retient la dernière occurrence,
  // qui est la version courante.
  const pageId = pageMap[subtabKey] || (subtabKey.startsWith("tab-") ? subtabKey : null);
  let pageEl = null;
  if (pageId) {
    const candidats = document.querySelectorAll(`section.page[id="${pageId}"]`);
    pageEl = candidats.length ? candidats[candidats.length - 1] : null;
  }
  if (pageEl) {
    pageEl.classList.remove("hidden");
    void pageEl.offsetWidth; // relance l'animation
    pageEl.classList.add("page-enter");
  }

  // Update page title and subtitle based on meta
  const meta = PAGE_META[pageId];
  if (meta) {
    document.getElementById("pageTitle").textContent = meta[0];
    document.getElementById("pageSub").textContent = meta[1];
  } else {
    // Default title based on subtab key
    const defaultTitles = {
      "tab-import": "Importer un document",
      "tab-dashboard": "Tableau de bord",
      "tab-result": "Résultat d'analyse"
    };
    document.getElementById("pageTitle").textContent = defaultTitles[pageId] || "UniOCR";
    document.getElementById("pageSub").textContent = "";
  }

  // Update active navigation items
  document.querySelectorAll(".nav-item").forEach(b => {
    b.classList.remove("active");
    b.removeAttribute("aria-current");
  });

  // Find and activate the parent group and subitem
  const parentGroup = document.querySelector(`.nav-group[data-group-index]`);
  if (parentGroup) {
    const activeSubitem = parentGroup.querySelector(`.nav-subitem.active`);
    if (activeSubitem) {
      activeSubitem.classList.add("active");
      activeSubitem.setAttribute("aria-current", "page");
    }
  }
}

/* =================== TOGGLE NAVIGATION GROUP =================== */
function toggleNavGroup(groupIndex) {
  const group = document.getElementById(`nav-group-${groupIndex}`);
  if (!group) return;

  const isExpanded = !group.classList.contains("nav-items-collapsed");

  if (isExpanded) {
    group.classList.add("nav-items-collapsed");
    group.previousElementSibling.classList.add("nav-label-collapsed");
  } else {
    group.classList.remove("nav-items-collapsed");
    group.previousElementSibling.classList.remove("nav-label-collapsed");
  }
}

/* =================== INITIALIZE =================== */
document.addEventListener("DOMContentLoaded", () => {
  // Le menu et l'affichage des sections sont gérés par web/navigation.js.
  if (window.Navigation && typeof window.Navigation.init === "function") {
    window.Navigation.init();
  } else if (NAVIGATION[0] && NAVIGATION[0].subtabs[0]) {
    // Repli si le module de navigation n'a pas pu être chargé.
    showSubtabPage(NAVIGATION[0].subtabs[0].key);
  }
});