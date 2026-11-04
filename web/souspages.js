/**
 * UniOCR — sous-pages de modules
 * ---------------------------------------------------------------------------
 * Les pages « sous-rubrique » du menu (Conteneurs, B/L, Navires, Déclarations,
 * Anomalies, Clients, Journal d'audit…) n'affichaient qu'un titre. Ce module
 * les remplit avec la liste réelle fournie par l'API : recherche, compteur,
 * pagination, colonnes déduites des données et ouverture du dossier lié.
 *
 * Principes :
 *  - aucune colonne inventée : elles viennent des enregistrements ;
 *  - aucune ligne inventée : une liste vide dit qu'elle est vide ;
 *  - aucune action métier : on lit et on navigue, on ne modifie rien.
 */
(function () {
  "use strict";

  var PAR_PAGE = 25;

  /* page → source réelle */
  var PAGES = {
    "tab-validation": {
      titre: "Extractions à valider",
      url: "/api/dossiers",
      filtre: function (d) { return d.state === "en_validation" || d.state === "revision_requise"; },
      colonnes: ["reference", "label", "client_importateur", "state_label", "updated_at"],
      vide: "Aucun dossier en attente de validation. Les extractions à contrôler apparaîtront ici."
    },
    "tab-anomalies": {
      titre: "Anomalies détectées",
      url: "/api/dashboard/alertes",
      cle: "alertes",
      colonnes: ["niveau", "titre", "message", "dossier_id"],
      vide: "Aucune anomalie active. Les écarts détectés par le contrôle documentaire seront listés ici."
    },
    "tab-manquants": {
      titre: "Documents manquants",
      url: "/api/dashboard/alertes",
      cle: "alertes",
      colonnes: ["dossier_id", "pieces_manquantes", "niveau"],
      filtre: function (a) { return a.type === "pieces_manquantes"; },
      vide: "Aucune pièce manquante signalée sur les dossiers ouverts."
    },
    "tab-conteneurs": {
      titre: "Conteneurs",
      url: "/api/conteneurs",
      vide: "Aucun conteneur enregistré. Les conteneurs se créent depuis l'espace dossier (onglet Transport maritime)."
    },
    "tab-bl": {
      titre: "Connaissements B/L",
      url: "/api/connaissements/bl",
      vide: "Aucun connaissement enregistré. Ils s'ajoutent depuis l'espace dossier (onglet Transport maritime)."
    },
    "tab-navires": {
      titre: "Navires",
      url: "/api/navires",
      vide: "Aucun navire enregistré. Le référentiel se remplit via l'API ou l'espace dossier."
    },
    "tab-expeditions": {
      titre: "Expéditions",
      url: "/api/expeditions",
      vide: "Aucune expédition enregistrée."
    },
    "tab-declarations": {
      titre: "Déclarations",
      url: "/api/declarations",
      vide: "Aucune déclaration enregistrée. Créez-la depuis le module Douane & réglementation."
    },
    "tab-nomenclature": {
      titre: "Nomenclature tarifaire",
      url: "/api/reglementation/codes-sh",
      colonnes: ["code_sh", "libelle", "chapitre"],
      vide: "Aucun code SH chargé dans le référentiel."
    },
    "tab-enlevement": {
      titre: "Demandes d'enlèvement",
      url: "/api/terminal",
      vide: "Aucun ordre d'enlèvement enregistré pour le moment."
    },
    "tab-frais": {
      titre: "Frais",
      url: "/api/frais",
      colonnes: ["dossier_id", "categorie", "montant", "devise", "statut"],
      vide: "Aucun frais enregistré. Les frais se saisissent depuis l'espace dossier (onglet Frais et paiements)."
    },
    "tab-clients": {
      titre: "Clients importateurs",
      url: "/api/clients",
      colonnes: ["name", "legal_name", "city", "status"],
      vide: "Aucun client enregistré."
    },
    "tab-fournisseurs": {
      titre: "Fournisseurs",
      url: "/api/fournisseurs",
      colonnes: ["name", "country", "status"],
      vide: "Aucun fournisseur enregistré."
    },
    "tab-transporteurs": {
      titre: "Transporteurs",
      url: "/api/transport/transporteurs",
      vide: "Aucun transporteur enregistré."
    },
    "tab-journal": {
      titre: "Journal d'audit",
      url: "/api/rbac/audit",
      colonnes: ["horodatage", "action", "acteur", "details"],
      vide: "Aucune entrée d'audit pour le moment."
    },
    "tab-moteurs": {
      titre: "Moteurs OCR",
      url: "/api/engines",
      colonnes: ["name", "kind", "available", "active", "ram_required_mb"],
      vide: "Aucun moteur déclaré par le serveur."
    },
    "tab-connecteurs-api": {
      titre: "Connecteurs API",
      url: "/api/connectors",
      cle: "catalog",
      colonnes: ["nom", "name", "type", "categorie", "externe"],
      vide: "Aucun connecteur dans le catalogue."
    },
    "tab-workflows": {
      titre: "Workflows",
      url: "/api/rbac/workflows",
      vide: "Aucun workflow personnalisé : les transitions par défaut du serveur s'appliquent."
    },
    "tab-sauvegardes": {
      titre: "Sauvegardes",
      url: "/api/backups",
      cle: "sauvegardes",
      colonnes: ["nom", "taille", "cree_le"],
      vide: "Aucune sauvegarde dans le répertoire de l'application."
    },
    "tab-center": {
      titre: "Centre documentaire",
      url: "/api/jobs?limit=200",
      colonnes: ["filename", "status", "stage", "progress", "created_at"],
      vide: "Aucun document traité : le centre documentaire se remplit dès le premier import."
    },
    "tab-ged": {
      titre: "Dossiers archivés",
      url: "/api/dossiers",
      filtre: function (d) { return d.state === "archive"; },
      colonnes: ["reference", "label", "client_importateur", "state_label", "updated_at"],
      vide: "Aucun dossier archivé. L'archivage se fait depuis l'espace dossier, une fois le dossier clos."
    },
    "tab-classif": {
      titre: "Catégories de documents reconnues",
      url: "/api/document-types",
      cle: "categories",
      colonnes: ["label", "profile", "indicators", "active"],
      vide: "Le serveur n'annonce aucune catégorie de document."
    },
    "tab-eta-etd": {
      titre: "Arrivées annoncées",
      url: "/api/dossiers",
      filtre: function (d) { return Boolean(d.eta || d.eta_effective); },
      colonnes: ["reference", "navire", "numero_voyage", "eta_effective", "port_destination", "state_label"],
      vide: "Aucune arrivée annoncée : renseignez l'ETA dans l'espace dossier (onglet Transport maritime)."
    },
    "tab-mainleves": {
      titre: "Mainlevées obtenues",
      url: "/api/terminal",
      filtre: function (t) { return t.mainlevee_obtenue === true; },
      colonnes: ["numero_bl", "numero_conteneur", "date_demande", "statut"],
      vide: "Aucune mainlevée enregistrée. Elle se constate sur la demande d'enlèvement du conteneur."
    },
    "tab-planification": {
      titre: "Enlèvements planifiés",
      url: "/api/terminal",
      filtre: function (t) { return Boolean(t.date_planifiee); },
      colonnes: ["numero_conteneur", "date_planifiee", "statut", "transporteur_id", "chauffeur_nom"],
      vide: "Aucun enlèvement planifié : la date se pose sur la demande d'enlèvement."
    }
  };

  var etats = {}; // mémoire par page : { recherche, page }

  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function lire(url) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(url, { headers: entetes, credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function elt(nom, classe, texte) {
    var n = document.createElement(nom);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = String(texte);
    return n;
  }

  var LIBELLES = {
    code_sh: "Code SH",
    state: "État",
    state_label: "État",
    statut: "Statut",
    dossier_id: "Dossier",
    pieces_manquantes: "Pièces manquantes",
    client_importateur: "Client",
    client: "Client",
    fournisseur: "Fournisseur",
    reference: "Référence",
    reference_bl: "B/L",
    updated_at: "Dernière activité",
    created_at: "Créé le",
    cree_le: "Créé le",
    date_creation: "Créé le",
    label: "Libellé",
    libelle: "Libellé",
    titre: "Titre",
    message: "Message",
    niveau: "Gravité",
    nom: "Nom",
    name: "Nom",
    nombre_colis: "Colis",
    poids_brut: "Poids brut",
    type_document: "Type",
    numero: "Numéro",
    numero_conteneur: "Conteneur",
    navire: "Navire",
    montant: "Montant",
    devise: "Devise",
    nom: "Nom",
    taille: "Taille",
    available: "Disponible",
    active: "Actif",
    kind: "Type",
    ram_required_mb: "RAM requise (Mo)",
    externe: "Externe",
    cree_le: "Créé le",
    filename: "Fichier",
    stage: "Étape",
    progress: "Progression",
    indicators: "Indicateurs",
    numero_bl: "Connaissement",
    numero_conteneur: "Conteneur",
    numero_voyage: "Voyage",
    navire: "Navire",
    eta_effective: "ETA effective",
    port_destination: "Port de destination",
    date_planifiee: "Date planifiée",
    date_demande: "Date de demande",
    mainlevee_obtenue: "Mainlevée",
    transporteur_id: "Transporteur",
    chauffeur_nom: "Chauffeur"
  };

  function libelle(cle) {
    if (LIBELLES[cle]) return LIBELLES[cle];
    return String(cle)
      .replace(/_/g, " ")
      .replace(/\b([a-z])/g, function (m) { return m.toUpperCase(); })
      .replace(/ Id$/, "")
      .replace(/^Id$/, "Identifiant");
  }

  function valeur(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "boolean") return v ? "Oui" : "Non";
    if (typeof v === "number") {
      // Les horodatages du store sont en secondes depuis 2001 ; on n'affiche
      // une date que si la valeur ressemble à un tel horodatage.
      if (v > 946684800 && v < 4102444800 && (v % 1000) !== 0) {
        var d = new Date(v * 1000);
        if (!isNaN(d.getTime())) {
          return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
        }
      }
      return v.toLocaleString("fr-FR");
    }
    if (Array.isArray(v)) return v.length ? v.join(" · ") : "—";
    if (typeof v === "object") {
      var cles = Object.keys(v);
      return cles.length ? cles.length + " champ(s)" : "—";
    }
    return String(v);
  }

  function colonnes(lignes) {
    var vues = [];
    var ignorees = { texte_complet: true, champs_extraits: true, pages: true, history: true };
    lignes.slice(0, 20).forEach(function (ligne) {
      if (!ligne || typeof ligne !== "object") return;
      Object.keys(ligne).forEach(function (cle) {
        if (ignorees[cle] || vues.indexOf(cle) !== -1) return;
        if (ligne[cle] === null || ligne[cle] === undefined || ligne[cle] === "") return;
        vues.push(cle);
      });
    });
    return vues.slice(0, 6);
  }

  function dossierId(ligne) {
    if (!ligne || typeof ligne !== "object") return "";
    if (ligne.dossier_id) return ligne.dossier_id;
    if (typeof ligne.id === "string" && ligne.id.indexOf("dos_") === 0) return ligne.id;
    return "";
  }

  function rendreTableau(hote, pageId, definition, lignes) {
    var etat = etats[pageId] || (etats[pageId] = { recherche: "", page: 1 });

    hote.textContent = "";

    var carte = elt("div", "sp-card");

    var barre = elt("div", "sp-toolbar");
    var recherche = elt("input", "sp-search");
    recherche.type = "search";
    recherche.placeholder = "Filtrer cette liste…";
    recherche.setAttribute("aria-label", "Filtrer la liste");
    recherche.value = etat.recherche;
    barre.appendChild(recherche);
    var compte = elt("span", "sp-count");
    barre.appendChild(compte);
    carte.appendChild(barre);

    var zone = elt("div");
    carte.appendChild(zone);
    hote.appendChild(carte);

    function filtrer() {
      var terme = etat.recherche.trim().toLowerCase();
      if (!terme) return lignes;
      return lignes.filter(function (ligne) {
        if (ligne === null || ligne === undefined) return false;
        if (typeof ligne !== "object") return String(ligne).toLowerCase().indexOf(terme) !== -1;
        return Object.keys(ligne).some(function (cle) {
          return String(valeur(ligne[cle])).toLowerCase().indexOf(terme) !== -1;
        });
      });
    }

    function dessiner() {
      zone.textContent = "";
      var filtrees = filtrer();
      compte.textContent = filtrees.length
        ? filtrees.length + " enregistrement" + (filtrees.length > 1 ? "s" : "")
        : "";

      if (!filtrees.length) {
        zone.appendChild(elt("p", "sp-empty", lignes.length
          ? "Aucun enregistrement ne correspond à ce filtre."
          : definition.vide));
        return;
      }

      var pages = Math.ceil(filtrees.length / PAR_PAGE);
      if (etat.page > pages) etat.page = pages;
      var debut = (etat.page - 1) * PAR_PAGE;
      var visibles = filtrees.slice(debut, debut + PAR_PAGE);

      var simple = typeof visibles[0] !== "object";
      var cols = simple ? ["valeur"]
        : (definition.colonnes || colonnes(visibles)).filter(function (cle) {
          // Une colonne choisie n'apparaît que si au moins une ligne la porte.
          return visibles.some(function (ligne) {
            return ligne && Object.prototype.hasOwnProperty.call(ligne, cle);
          });
        });

      var table = elt("table", "table sp-table");
      var thead = elt("thead");
      var trh = elt("tr");
      cols.forEach(function (cle) {
        var entete = cle === "valeur" ? (definition.entete || "Valeur") : libelle(cle);
        trh.appendChild(elt("th", null, entete));
      });
      trh.appendChild(elt("th", null, ""));
      thead.appendChild(trh);
      table.appendChild(thead);

      var tbody = elt("tbody");
      visibles.forEach(function (ligne) {
        var tr = elt("tr");
        if (simple) {
          tr.appendChild(elt("td", null, String(ligne)));
        } else {
          cols.forEach(function (cle) {
            var td = elt("td", null, valeur(ligne[cle]));
            if (cle === "state" || cle === "statut" || cle === "niveau" || cle === "severity") {
              td.className = "sp-td--statut";
            }
            tr.appendChild(td);
          });
        }
        var actions = elt("td", "sp-td--actions");
        var id = dossierId(ligne);
        if (id) {
          var ouvrir = elt("button", "row-action", "Ouvrir");
          ouvrir.type = "button";
          ouvrir.addEventListener("click", function () {
            if (window.UniOCRShell && window.UniOCRShell.ouvrirDossier) {
              window.UniOCRShell.ouvrirDossier(id);
            }
          });
          actions.appendChild(ouvrir);
        }
        tr.appendChild(actions);
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);

      var scroll = elt("div", "table-wrap");
      scroll.appendChild(table);
      zone.appendChild(scroll);

      if (pages > 1) {
        var pager = elt("div", "ws-pager");
        var precedent = elt("button", "btn ghost sm", "Précédent");
        precedent.type = "button";
        precedent.disabled = etat.page === 1;
        precedent.addEventListener("click", function () {
          etat.page = Math.max(1, etat.page - 1);
          dessiner();
        });
        var suivant = elt("button", "btn ghost sm", "Suivant");
        suivant.type = "button";
        suivant.disabled = etat.page === pages;
        suivant.addEventListener("click", function () {
          etat.page = Math.min(pages, etat.page + 1);
          dessiner();
        });
        pager.appendChild(precedent);
        pager.appendChild(elt("span", "ws-pager__info", "Page " + etat.page + " / " + pages));
        pager.appendChild(suivant);
        zone.appendChild(pager);
      }
    }

    recherche.addEventListener("input", function () {
      etat.recherche = recherche.value;
      etat.page = 1;
      dessiner();
    });

    dessiner();
  }

  function remplir(section) {
    var definition = PAGES[section.id];
    if (!definition) return;
    var marqueur = section.querySelector("[data-sp-page]");
    if (marqueur) return;

    var entete = section.querySelector("header");
    if (!entete) return;

    var hote = elt("div", "sp-host");
    hote.setAttribute("data-sp-page", section.id);
    entete.parentNode.insertBefore(hote, entete.nextSibling);

    // Les tableaux vides hérités ne servent plus : la liste réelle les remplace.
    Array.prototype.slice.call(section.children).forEach(function (enfant) {
      if (enfant === entete || enfant === hote) return;
      if (enfant.classList && (enfant.classList.contains("panel") || enfant.classList.contains("panel-head"))) {
        enfant.hidden = true;
      }
    });

    hote.appendChild(elt("p", "sp-empty", "Chargement…"));

    lire(definition.url).then(function (donnees) {
      var lignes = definition.cle && donnees && !Array.isArray(donnees)
        ? donnees[definition.cle]
        : donnees;
      if (!Array.isArray(lignes)) lignes = [];
      if (definition.filtre) lignes = lignes.filter(definition.filtre);
      rendreTableau(hote, section.id, definition, lignes);
    }).catch(function (erreur) {
      hote.textContent = "";
      hote.appendChild(elt("p", "sp-empty",
        "Liste indisponible (" + (erreur && erreur.message ? erreur.message : "erreur réseau") + ")."));
    });

    var titre = section.querySelector("h1");
    if (titre && !section.querySelector(".sp-sous-titre")) {
      var sous = elt("p", "sp-sous-titre", definition.titre + " — données réelles, lecture seule.");
      entete.appendChild(sous);
    }
  }

  function pageVisible() {
    var section = document.querySelector("section.page:not(.hidden)");
    if (section) remplir(section);
  }

  function demarrer() {
    window.addEventListener("hashchange", function () { setTimeout(pageVisible, 40); });
    setTimeout(pageVisible, 500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.UniOCRSousPages = { pages: PAGES, remplir: remplir };
})();
