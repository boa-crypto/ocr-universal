/**
 * UniOCR — écrans métier déclaratifs
 * ---------------------------------------------------------------------------
 * Les rubriques qui n'avaient pas encore d'écran (finance, douane, enlèvement,
 * référentiels, administration…) partagent le même socle : une liste paginée
 * alimentée par l'API, des filtres, un formulaire de création / modification,
 * des actions contextuelles et un export. Ce fichier porte ce socle **et**
 * le catalogue des écrans ; chaque entrée décrit les colonnes, les champs et
 * les routes réellement appelées.
 *
 * Principes tenus :
 *   - aucune donnée inventée : une liste vide affiche un état vide explicite
 *     avec l'action qui permet de commencer ;
 *   - aucune logique métier ici : le serveur valide, calcule et décide ;
 *   - les écritures passent par les routes existantes et sont tracées côté
 *     serveur (audit), l'interface ne fait que les déclencher.
 */
(function () {
  "use strict";

  /* ==================== 1. Outils ==================== */

  function $(id) { return document.getElementById(id); }

  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function entetes(extra) {
    var h = { Accept: "application/json" };
    var t = jeton();
    if (t) h.Authorization = "Bearer " + t;
    return Object.assign(h, extra || {});
  }

  function lire(url) {
    return fetch(url, { headers: entetes(), credentials: "same-origin" }).then(function (r) {
      if (!r.ok) {
        return r.text().then(function (txt) {
          var message = "HTTP " + r.status;
          try {
            var corps = JSON.parse(txt);
            if (corps && corps.detail) message = String(corps.detail);
          } catch (e) { /* réponse non JSON */ }
          throw new Error(message);
        });
      }
      return r.status === 204 ? null : r.json();
    });
  }

  function ecrire(url, methode, corps) {
    return fetch(url, {
      method: methode,
      headers: entetes({ "Content-Type": "application/json" }),
      credentials: "same-origin",
      body: corps ? JSON.stringify(corps) : undefined
    }).then(function (r) {
      if (!r.ok) {
        return r.text().then(function (txt) {
          var message = "HTTP " + r.status;
          try {
            var rep = JSON.parse(txt);
            if (rep && rep.detail) {
              message = typeof rep.detail === "string" ? rep.detail : JSON.stringify(rep.detail);
            }
          } catch (e) { /* réponse non JSON */ }
          throw new Error(message);
        });
      }
      return r.status === 204 ? null : r.json().catch(function () { return null; });
    });
  }

  function elt(nom, classe, texte) {
    var n = document.createElement(nom);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = String(texte);
    return n;
  }

  function toast(message, type) {
    if (typeof window.toast === "function") window.toast(message, type || "info");
  }

  var MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
              "juil.", "août", "sept.", "oct.", "nov.", "déc."];

  function horodatage(valeur) {
    if (valeur === null || valeur === undefined || valeur === "") return "";
    var d = null;
    if (typeof valeur === "number") {
      d = new Date(valeur > 1e12 ? valeur : valeur * 1000);
    } else {
      d = new Date(String(valeur));
    }
    if (!d || isNaN(d.getTime())) return String(valeur);
    return d.getDate() + " " + MOIS[d.getMonth()] + " " + d.getFullYear();
  }

  function nombre(valeur, devises) {
    var n = Number(valeur);
    if (!isFinite(n)) return String(valeur === undefined || valeur === null ? "" : valeur);
    var texte = n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return devises ? texte + " " + devises : texte;
  }

  /* Lecture d'une clé, y compris imbriquée (`options.engine`). */
  function valeurDe(ligne, cle) {
    if (!ligne || !cle) return undefined;
    if (cle.indexOf(".") === -1) return ligne[cle];
    var morceaux = cle.split(".");
    var courant = ligne;
    for (var i = 0; i < morceaux.length; i += 1) {
      if (courant === null || courant === undefined) return undefined;
      courant = courant[morceaux[i]];
    }
    return courant;
  }

  function texteCellule(ligne, colonne) {
    var valeur = valeurDe(ligne, colonne.cle);
    if (colonne.format === "date") return horodatage(valeur);
    if (colonne.format === "montant") {
      var devise = colonne.devise ? ligne[colonne.devise] : "";
      return valeur === null || valeur === undefined || valeur === "" ? "—" : nombre(valeur, devise);
    }
    if (colonne.format === "progression") {
      if (valeur === null || valeur === undefined || valeur === "") return "—";
      var part = Number(valeur);
      if (!isFinite(part)) return String(valeur);
      if (part > 0 && part <= 1) part *= 100;
      return Math.round(part) + " %";
    }
    if (colonne.format === "liste") {
      if (valeur === null || valeur === undefined) return "—";
      if (Array.isArray(valeur)) {
        return valeur.length ? valeur.join(", ") : "—";
      }
      return String(valeur) || "—";
    }
    if (colonne.format === "nombre") {
      return valeur === null || valeur === undefined || valeur === "" ? "—"
        : Number(valeur).toLocaleString("fr-FR");
    }
    if (colonne.format === "booleen") {
      if (valeur === undefined || valeur === null) return "—";
      return valeur ? "Oui" : "Non";
    }
    if (Array.isArray(valeur)) return valeur.length ? valeur.join(" · ") : "—";
    if (valeur && typeof valeur === "object") {
      var cles = Object.keys(valeur);
      return cles.length ? cles.length + " élément(s)" : "—";
    }
    if (valeur === null || valeur === undefined || valeur === "") return "—";
    return String(valeur);
  }

  /* ==================== 2. Catalogue des écrans ==================== */
  /* Chaque entrée porte : où elle vit, ce qu'elle montre, ce qu'elle écrit. */

  var STATUTS_DOSSIER = [
    { valeur: "en_preparation", libelle: "En préparation" },
    { valeur: "traitement_en_cours", libelle: "Traitement en cours" },
    { valeur: "en_validation", libelle: "En validation" },
    { valeur: "revision_requise", libelle: "Révision requise" },
    { valeur: "incomplet", libelle: "Incomplet" },
    { valeur: "erreur_traitement", libelle: "Erreur de traitement" },
    { valeur: "exporte", libelle: "Exporté" },
    { valeur: "archive", libelle: "Archivé" }
  ];

  /* Champs « Dossier » et « Déclaration » : on choisit un élément existant,
     jamais un identifiant interne recopié à la main. */
  var REGISTRE_DOSSIERS = {
    url: "/api/dossiers", valeur: "id",
    apercu: ["label", "reference", "state_label"], nom: "dossier",
    vide: "Aucun dossier enregistré : créez d'abord un dossier, il sera proposé ici."
  };
  var REGISTRE_DECLARATIONS = {
    url: "/api/declarations", valeur: "declaration_id",
    apercu: ["numero_declaration", "dossier_id", "statut"], nom: "déclaration",
    vide: "Aucune déclaration enregistrée : créez une déclaration dans Douane → Contrôles."
  };

  var ECRANS = {
    /* ---------------- Contrôle & conformité ---------------- */
    "controle/documentaire": {
      section: "Contrôle & conformité",
      titre: "Contrôle documentaire",
      desc: "Lancez le contrôle de cohérence d'un dossier et suivez son verdict. " +
            "Le calcul est fait par le serveur ; l'écran ne fait que le demander.",
      source: { url: "/api/dossiers" },
      id: "id",
      colonnes: [
        { cle: "reference", libelle: "Référence" },
        { cle: "label", libelle: "Dossier" },
        { cle: "client_importateur", libelle: "Client" },
        { cle: "state_label", libelle: "État" },
        { cle: "updated_at", libelle: "Dernière activité", format: "date" }
      ],
      filtres: [{ cle: "state_label", libelle: "État" }],
      actions: [{
        libelle: "Contrôler",
        url: "/api/controle/analyser",
        methode: "POST",
        corps: function (ligne) { return { dossier_id: ligne.id }; },
        succes: "Contrôle lancé sur le dossier"
      }, {
        libelle: "Verdict",
        url: "/api/controle/{id}/statut",
        methode: "GET",
        afficher: true
      }],
      vide: {
        message: "Aucun dossier à contrôler pour le moment.",
        action: { libelle: "Créer un dossier", route: "#dossiers/nouveau" }
      }
    },

    "controle/comparaison": {
      section: "Contrôle & conformité",
      titre: "Comparaison des documents",
      desc: "Dossiers comportant plusieurs extractions : ouvrez la comparaison " +
            "champ par champ pour arbitrer les divergences.",
      source: { url: "/api/dossiers" },
      id: "id",
      colonnes: [
        { cle: "reference", libelle: "Référence" },
        { cle: "label", libelle: "Dossier" },
        { cle: "pieces", libelle: "Pièces", format: "nombre" },
        { cle: "state_label", libelle: "État" },
        { cle: "updated_at", libelle: "Dernière activité", format: "date" }
      ],
      filtreLocal: function (ligne) {
        return Array.isArray(ligne.pieces) && ligne.pieces.length >= 2;
      },
      actions: [{
        libelle: "Comparer",
        route: function (ligne) { return "#dossiers/" + ligne.id + "/ocr"; }
      }],
      vide: {
        message: "Aucun dossier ne réunit encore deux pièces extraites : la " +
                 "comparaison demande au moins deux documents.",
        action: { libelle: "Importer un document", route: "#documents/import" }
      }
    },

    "controle/historique": {
      section: "Contrôle & conformité",
      titre: "Historique des contrôles",
      desc: "Journal des contrôles et analyses réellement exécutés sur le poste.",
      source: { url: "/api/rbac/audit" },
      id: "id",
      colonnes: [
        { cle: "horodatage", libelle: "Date", format: "date" },
        { cle: "action", libelle: "Action" },
        { cle: "acteur", libelle: "Acteur" },
        { cle: "cible", libelle: "Cible" },
        { cle: "details", libelle: "Détail" }
      ],
      filtreLocal: function (ligne) {
        var action = String(ligne.action || "").toLowerCase();
        return action.indexOf("controle") !== -1 || action.indexOf("coherence") !== -1 ||
               action.indexOf("anomalie") !== -1;
      },
      lectureSeule: true,
      vide: {
        message: "Aucun contrôle n'a encore été exécuté sur ce poste.",
        action: { libelle: "Lancer un contrôle", route: "#controle/documentaire" }
      }
    },

    "controle/regles": {
      section: "Contrôle & conformité",
      titre: "Règles de contrôle",
      desc: "Règles appliquées au contrôle documentaire et à la cohérence des dossiers.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/controle/regles", "/api/coherence/regles"],
      source: {
        charger: function () {
          return Promise.all([
            lire("/api/controle/regles").catch(function () { return { regles: [] }; }),
            lire("/api/coherence/regles").catch(function () { return { regles: [] }; })
          ]).then(function (resultats) {
            var lignes = [];
            var premier = resultats[0] || {};
            var second = resultats[1] || {};
            [].concat(premier.regles || premier || []).forEach(function (regle) {
              if (!regle || typeof regle !== "object") return;
              lignes.push(Object.assign({ origine: "Contrôle documentaire" }, regle));
            });
            [].concat(second.regles || second || []).forEach(function (regle) {
              if (!regle || typeof regle !== "object") return;
              lignes.push(Object.assign({ origine: "Cohérence des données" }, regle));
            });
            return lignes;
          });
        }
      },
      id: "nom",
      colonnes: [
        { cle: "origine", libelle: "Famille" },
        { cle: "nom", libelle: "Règle" },
        { cle: "libelle", libelle: "Libellé" },
        { cle: "description", libelle: "Description" },
        { cle: "severite", libelle: "Sévérité" },
        { cle: "actif", libelle: "Active", format: "booleen" }
      ],
      lectureSeule: true,
      vide: { message: "Le serveur n'expose aucune règle de contrôle sur ce poste." }
    },

    /* ---------------- Opérations maritimes ---------------- */
    "maritime/escales": {
      section: "Opérations maritimes",
      titre: "Escales",
      desc: "Navires attendus, port d'escale et échéance, reconstitués depuis les dossiers.",
      source: { url: "/api/dossiers" },
      id: "id",
      colonnes: [
        { cle: "reference", libelle: "Référence" },
        { cle: "navire", libelle: "Navire" },
        { cle: "numero_voyage", libelle: "Voyage" },
        { cle: "port_destination", libelle: "Port" },
        { cle: "eta", libelle: "ETA", format: "date" },
        { cle: "eta_effective", libelle: "Arrivée réelle", format: "date" },
        { cle: "state_label", libelle: "État" }
      ],
      filtreLocal: function (ligne) { return Boolean(ligne.navire || ligne.eta); },
      actions: [{ libelle: "Ouvrir", route: function (l) { return "#dossiers/" + l.id; } }],
      vide: {
        message: "Aucune escale enregistrée : renseignez le navire et l'ETA dans " +
                 "l'espace dossier (onglet Transport maritime).",
        action: { libelle: "Voir les dossiers", route: "#dossiers/tous" }
      }
    },

    "maritime/voyages": {
      section: "Opérations maritimes",
      titre: "Voyages",
      desc: "Expéditions maritimes : navire, ports, ETA, arrivée effective et B/L.",
      source: { url: "/api/expeditions" },
      id: "expedition_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "navire", libelle: "Navire" },
        { cle: "porte_chargement", libelle: "Chargement" },
        { cle: "porte_destination", libelle: "Destination" },
        { cle: "ETA", libelle: "ETA", format: "date" },
        { cle: "arrivee_effective", libelle: "Arrivée réelle", format: "date" },
        { cle: "numero_bl", libelle: "B/L" },
        { cle: "nom_gestionnaire", libelle: "Gestionnaire" },
        { cle: "priorite", libelle: "Priorité" }
      ],
      filtres: [{ cle: "priorite", libelle: "Priorité" }],
      creation: {
        url: "/api/expeditions",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true, registre: REGISTRE_DOSSIERS },
          { cle: "navire", libelle: "Navire" },
          { cle: "porte_chargement", libelle: "Port de chargement" },
          { cle: "porte_destination", libelle: "Port de destination" },
          { cle: "ETA", libelle: "ETA", type: "date" },
          { cle: "numero_bl", libelle: "Connaissement" },
          { cle: "priorite", libelle: "Priorité", type: "select",
            options: ["basse", "normale", "haute", "urgente"] },
          { cle: "observations", libelle: "Observations", type: "textarea" }
        ]
      },
      suppression: { url: "/api/expeditions/{id}" },
      vide: {
        message: "Aucune expédition enregistrée sur ce poste.",
        action: { libelle: "Créer un dossier", route: "#dossiers/nouveau" }
      }
    },

    "maritime/echeances": {
      section: "Opérations maritimes",
      titre: "Échéances maritimes",
      desc: "Dossiers dont une échéance de transport approche ou est dépassée.",
      source: { url: "/api/dossiers" },
      id: "id",
      colonnes: [
        { cle: "reference", libelle: "Référence" },
        { cle: "navire", libelle: "Navire" },
        { cle: "eta", libelle: "ETA", format: "date" },
        { cle: "port_destination", libelle: "Port" },
        { cle: "state_label", libelle: "État" },
        { cle: "priorite", libelle: "Priorité" }
      ],
      filtreLocal: function (ligne) { return Boolean(ligne.eta || ligne.eta_effective); },
      actions: [{ libelle: "Ouvrir", route: function (l) { return "#dossiers/" + l.id; } }],
      vide: {
        message: "Aucune échéance maritime : les dossiers n'ont pas encore d'ETA renseignée."
      }
    },

    /* ---------------- Douane & réglementation ---------------- */
    "douane/controles": {
      section: "Douane & réglementation",
      titre: "Contrôles douaniers",
      desc: "Déclarations déposées et leur avancement : contrôle, validation, mainlevée.",
      source: { url: "/api/declarations" },
      id: "declaration_id",
      colonnes: [
        { cle: "numero_declaration", libelle: "Déclaration" },
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "bureau_douane", libelle: "Bureau" },
        { cle: "date_depot", libelle: "Déposée le", format: "date" },
        { cle: "statut", libelle: "Statut" },
        { cle: "agent_declarant", libelle: "Déclarant" },
        { cle: "mainlevee_obtenue", libelle: "Mainlevée", format: "booleen" },
        { cle: "montant_total", libelle: "Montant", format: "montant" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      creation: {
        url: "/api/declarations",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true, registre: REGISTRE_DOSSIERS },
          { cle: "numero_declaration", libelle: "Numéro de déclaration" },
          { cle: "bureau_douane", libelle: "Bureau de douane" },
          { cle: "date_depot", libelle: "Date de dépôt", type: "date" },
          { cle: "regime_douanier", libelle: "Régime douanier" },
          { cle: "agent_declarant", libelle: "Agent déclarant" },
          { cle: "observations_agent", libelle: "Observations", type: "textarea" }
        ]
      },
      edition: {
        url: "/api/declarations/{id}",
        champs: [
          { cle: "statut", libelle: "Statut", type: "select",
            options: ["en_preparation", "deposee", "en_controle", "validee", "mainlevee", "rejetee"] },
          { cle: "numero_declaration", libelle: "Numéro de déclaration" },
          { cle: "date_validation", libelle: "Date de validation", type: "date" },
          { cle: "observations_douane", libelle: "Observations douane", type: "textarea" }
        ]
      },
      suppression: { url: "/api/declarations/{id}" },
      vide: {
        message: "Aucune déclaration enregistrée : créez-en une depuis un dossier douanier.",
        action: { libelle: "Voir les dossiers", route: "#dossiers/tous" }
      }
    },

    "douane/liquidation": {
      section: "Douane & réglementation",
      titre: "Liquidation",
      desc: "Liquidations douanières : droits, TVA, taxes et total à payer.",
      source: { url: "/api/declarations/liquidation" },
      id: "liquidation_id",
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "declaration_id", libelle: "Déclaration" },
        { cle: "date_liquidation", libelle: "Date", format: "date" },
        { cle: "droits_importation", libelle: "Droits", format: "montant" },
        { cle: "tva", libelle: "TVA", format: "montant" },
        { cle: "total_douane", libelle: "Total douane", format: "montant" },
        { cle: "total_a_payer", libelle: "À payer", format: "montant" },
        { cle: "statut", libelle: "Statut" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      creation: {
        url: "/api/declarations/liquidation",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true, registre: REGISTRE_DOSSIERS },
          { cle: "declaration_id", libelle: "Déclaration", requis: true, registre: REGISTRE_DECLARATIONS },
          { cle: "date_liquidation", libelle: "Date de liquidation", type: "date" },
          { cle: "droits_importation", libelle: "Droits d'importation", type: "number" },
          { cle: "tva", libelle: "TVA", type: "number" },
          { cle: "tpc", libelle: "TPC", type: "number" },
          { cle: "taxes_internes", libelle: "Taxes internes", type: "number" },
          { cle: "total_douane", libelle: "Total douane", type: "number" },
          { cle: "majorations", libelle: "Majorations", type: "number" },
          { cle: "total_a_payer", libelle: "Total à payer", type: "number" },
          { cle: "statut", libelle: "Statut", type: "select",
            options: ["en_attente", "payee", "contestee"] }
        ]
      },
      suppression: { url: "/api/declarations/liquidation/{id}" },
      vide: {
        message: "Aucune liquidation enregistrée.",
        action: { libelle: "Voir les déclarations", route: "#douane/declarations" }
      }
    },

    "douane/paiements": {
      section: "Douane & réglementation",
      titre: "Paiements douaniers",
      desc: "Liquidations restant à régler et leur état de paiement.",
      source: { url: "/api/declarations/liquidation" },
      id: "liquidation_id",
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "date_liquidation", libelle: "Liquidation", format: "date" },
        { cle: "total_a_payer", libelle: "À payer", format: "montant" },
        { cle: "statut", libelle: "Statut" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      actions: [{
        libelle: "Marquer payée",
        url: "/api/declarations/liquidation/{id}",
        methode: "PUT",
        corps: function () { return { statut: "payee" }; },
        confirmation: "Confirmer l'encaissement de cette liquidation ?",
        succes: "Liquidation marquée payée"
      }],
      vide: {
        message: "Aucune liquidation à payer : les paiements apparaissent dès qu'une " +
                 "liquidation est enregistrée.",
        action: { libelle: "Ouvrir la liquidation", route: "#douane/liquidation" }
      }
    },

    "douane/autorisations": {
      section: "Douane & réglementation",
      titre: "Autorisations & certificats",
      desc: "Certificats exigés ou délivrés, par type et par dossier.",
      source: { url: "/api/reglementation/certificats" },
      id: "type_cert",
      colonnes: [
        { cle: "type_cert", libelle: "Certificat" },
        { cle: "libelle", libelle: "Libellé" },
        { cle: "obligatoire", libelle: "Obligatoire", format: "booleen" },
        { cle: "description", libelle: "Description" }
      ],
      lectureSeule: true,
      vide: {
        message: "Aucun certificat déclaré dans le référentiel réglementaire.",
        action: { libelle: "Ouvrir le référentiel", route: "#douane/referentiel" }
      }
    },

    "douane/referentiel": {
      section: "Douane & réglementation",
      titre: "Référentiel réglementaire",
      desc: "Règles réglementaires et nomenclatures appliquées aux déclarations.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/reglementation/chapitres", "/api/reglementation/regles"],
      source: {
        charger: function () {
          return Promise.all([
            lire("/api/reglementation/regles").catch(function () { return []; }),
            lire("/api/reglementation/chapitres").catch(function () { return []; })
          ]).then(function (r) {
            var regles = Array.isArray(r[0]) ? r[0] : (r[0].regles || []);
            var chapitres = Array.isArray(r[1]) ? r[1] : (r[1].chapitres || []);
            return regles.map(function (regle) {
              return Object.assign({ famille: "Règle" }, regle);
            }).concat(chapitres.map(function (chapitre) {
              return Object.assign({ famille: "Chapitre SH" }, chapitre);
            }));
          });
        }
      },
      id: "nom",
      colonnes: [
        { cle: "famille", libelle: "Famille" },
        { cle: "nom", libelle: "Référence" },
        { cle: "libelle", libelle: "Libellé" },
        { cle: "description", libelle: "Description" },
        { cle: "taux", libelle: "Taux", format: "nombre" }
      ],
      lectureSeule: true,
      vide: { message: "Le référentiel réglementaire est vide sur ce poste." }
    },

    /* ---------------- Enlèvement & livraison ---------------- */
    "enlevissement/sortie-port": {
      section: "Enlèvement & livraison",
      titre: "Sortie portuaire",
      desc: "Demandes d'enlèvement prêtes à sortir : mainlevée, BAD et frais portuaires.",
      source: { url: "/api/terminal" },
      id: "enlevement_id",
      colonnes: [
        { cle: "numero_conteneur", libelle: "Conteneur" },
        { cle: "numero_bl", libelle: "B/L" },
        { cle: "statut", libelle: "Statut" },
        { cle: "mainlevee_obtenue", libelle: "Mainlevée", format: "booleen" },
        { cle: "bad_obtenu", libelle: "BAD", format: "booleen" },
        { cle: "frais_portuaires_payes", libelle: "Frais payés", format: "booleen" },
        { cle: "date_planifiee", libelle: "Planifiée le", format: "date" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      actions: [{
        libelle: "Autoriser la sortie",
        url: "/api/terminal/{id}/autoriser_sortie",
        methode: "POST",
        emplacement: "query",
        succes: "Sortie autorisée",
        champs: [
          { cle: "mainlevee_obtenue", libelle: "Mainlevée obtenue", type: "booleen",
            requis: true, valeur: true },
          { cle: "bad_obtenu", libelle: "BAD obtenu", type: "booleen",
            requis: true, valeur: true },
          { cle: "frais_portuaires_payes", libelle: "Frais portuaires payés",
            type: "booleen", requis: true, valeur: true,
            aide: "Le terminal refuse la sortie si l'une des trois conditions manque." },
          { cle: "justificatif_sortie", libelle: "Justificatif", type: "text",
            requis: true, aide: "Référence du justificatif joint au dossier." }
        ]
      }, {
        libelle: "Enregistrer la sortie",
        url: "/api/terminal/{id}/sortie",
        methode: "POST",
        emplacement: "query",
        succes: "Sortie enregistrée",
        champs: [
          { cle: "date_sortie", libelle: "Date de sortie", type: "date",
            requis: true, defaut: "aujourdhui" }
        ]
      }],
      vide: {
        message: "Aucune demande d'enlèvement enregistrée.",
        action: { libelle: "Voir les ordres", route: "#enlevissement/ordres" }
      }
    },

    "enlevissement/livraison": {
      section: "Enlèvement & livraison",
      titre: "Livraisons",
      desc: "Tournées de livraison : démarrage, arrivée et confirmation de réception.",
      source: { url: "/api/transport/livraisons" },
      id: "livraison_id",
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "lieu_livraison", libelle: "Lieu de livraison" },
        { cle: "camion_id", libelle: "Camion" },
        { cle: "date_prevue", libelle: "Prévue", format: "date" },
        { cle: "date_reelle", libelle: "Livrée le", format: "date" },
        { cle: "statut", libelle: "Statut" },
        { cle: "reserves_eventuelles", libelle: "Réserves" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      actions: [{
        libelle: "Démarrer",
        url: "/api/transport/livraisons/{id}/demarrer",
        methode: "POST",
        emplacement: "query",
        succes: "Livraison démarrée",
        champs: [
          { cle: "date_depart", libelle: "Date de départ", type: "date",
            requis: true, defaut: "aujourdhui" }
        ]
      }, {
        libelle: "Arrivée",
        url: "/api/transport/livraisons/{id}/arriver",
        methode: "POST",
        emplacement: "query",
        succes: "Arrivée enregistrée",
        champs: [
          { cle: "date_reelle", libelle: "Date d'arrivée", type: "date",
            requis: true, defaut: "aujourdhui" },
          { cle: "reserves", libelle: "Réserves", type: "text",
            aide: "Laisser vide si la livraison est conforme." }
        ]
      }, {
        libelle: "Confirmer",
        url: "/api/transport/livraisons/{id}/confirmer",
        methode: "POST",
        emplacement: "query",
        succes: "Livraison confirmée",
        champs: [
          { cle: "preuve_signee", libelle: "Preuve signée", type: "booleen",
            requis: true, valeur: true },
          { cle: "date_signature", libelle: "Date de signature", type: "date",
            requis: true, defaut: "aujourdhui" }
        ]
      }],
      vide: {
        message: "Aucune livraison planifiée.",
        action: { libelle: "Ouvrir la planification", route: "#enlevissement/planning" }
      }
    },

    "enlevissement/preuves": {
      section: "Enlèvement & livraison",
      titre: "Preuves de livraison",
      desc: "Livraisons confirmées : la preuve est l'horodatage serveur de la confirmation.",
      source: { url: "/api/transport/livraisons" },
      id: "livraison_id",
      filtreLocal: function (ligne) {
        /* La preuve, c'est la confirmation horodatée par le serveur
           (`preuve_livraison_signee` + `date_signature`). */
        return ligne.preuve_livraison_signee === true ||
               String(ligne.statut || "").toLowerCase() === "confirme";
      },
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "lieu_livraison", libelle: "Lieu de livraison" },
        { cle: "camion_id", libelle: "Camion" },
        { cle: "preuve_livraison_signee", libelle: "Preuve signée", format: "booleen" },
        { cle: "date_signature", libelle: "Signée le", format: "date" },
        { cle: "statut", libelle: "Statut" }
      ],
      lectureSeule: true,
      vide: {
        message: "Aucune livraison confirmée pour le moment.",
        action: { libelle: "Voir les livraisons", route: "#enlevissement/livraison" }
      }
    },

    "enlevissement/suivi": {
      section: "Enlèvement & livraison",
      titre: "Suivi des opérations",
      desc: "Vue consolidée des demandes d'enlèvement et de leur avancement.",
      source: { url: "/api/terminal" },
      id: "enlevement_id",
      colonnes: [
        { cle: "numero_conteneur", libelle: "Conteneur" },
        { cle: "numero_bl", libelle: "B/L" },
        { cle: "date_demande", libelle: "Demande", format: "date" },
        { cle: "date_planifiee", libelle: "Planifiée", format: "date" },
        { cle: "statut", libelle: "Statut" },
        { cle: "chauffeur_nom", libelle: "Chauffeur" },
        { cle: "immatriculation", libelle: "Camion" }
      ],
      filtres: [{ cle: "statut", libelle: "Statut" }],
      vide: { message: "Aucune opération d'enlèvement en cours." }
    },

    /* ---------------- Finance & facturation ---------------- */
    "finance/frais-dossier": {
      section: "Finance & facturation",
      titre: "Frais des dossiers",
      desc: "Frais imputés aux dossiers : catégorie, fournisseur, montant et état de paiement.",
      source: { url: "/api/frais" },
      id: "frais_id",
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "categorie", libelle: "Catégorie" },
        { cle: "fournisseur", libelle: "Fournisseur" },
        { cle: "montant", libelle: "Montant", format: "montant", devise: "devise" },
        { cle: "date", libelle: "Date", format: "date" },
        { cle: "statut_paiement", libelle: "Paiement" },
        { cle: "avance_client", libelle: "Avancé", format: "booleen" }
      ],
      filtres: [
        { cle: "statut_paiement", libelle: "Paiement" },
        { cle: "categorie", libelle: "Catégorie" }
      ],
      creation: {
        url: "/api/frais",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true, registre: REGISTRE_DOSSIERS },
          { cle: "categorie", libelle: "Catégorie" },
          { cle: "fournisseur", libelle: "Fournisseur" },
          { cle: "montant", libelle: "Montant", type: "number", requis: true },
          { cle: "devise", libelle: "Devise", type: "select", options: ["DZD", "EUR", "USD"] },
          { cle: "date", libelle: "Date", type: "date" },
          { cle: "reference_facture", libelle: "Référence facture" },
          { cle: "statut_paiement", libelle: "Paiement", type: "select",
            options: ["en_attente", "paye", "partiel", "litige"] },
          { cle: "avance_client", libelle: "Avancé par le client", type: "checkbox" },
          { cle: "commentaire", libelle: "Commentaire", type: "textarea" }
        ]
      },
      edition: {
        url: "/api/frais/{id}",
        champs: [
          { cle: "categorie", libelle: "Catégorie" },
          { cle: "fournisseur", libelle: "Fournisseur" },
          { cle: "montant", libelle: "Montant", type: "number" },
          { cle: "statut_paiement", libelle: "Paiement", type: "select",
            options: ["en_attente", "paye", "partiel", "litige"] },
          { cle: "commentaire", libelle: "Commentaire", type: "textarea" }
        ]
      },
      suppression: { url: "/api/frais/{id}" },
      vide: {
        message: "Aucun frais enregistré. Les frais s'ajoutent ici ou depuis l'espace " +
                 "dossier (onglet Frais et paiements).",
        action: { libelle: "Voir les dossiers", route: "#dossiers/tous" }
      }
    },

    "finance/debours": {
      section: "Finance & facturation",
      titre: "Débours",
      desc: "Frais avancés pour le compte du client, à refacturer.",
      source: { url: "/api/frais" },
      id: "frais_id",
      filtreLocal: function (ligne) { return ligne.avance_client === true; },
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "categorie", libelle: "Catégorie" },
        { cle: "fournisseur", libelle: "Fournisseur" },
        { cle: "montant", libelle: "Montant", format: "montant", devise: "devise" },
        { cle: "date", libelle: "Date", format: "date" },
        { cle: "statut_paiement", libelle: "Paiement" }
      ],
      vide: {
        message: "Aucun débours : cochez « avancé par le client » sur un frais pour le suivre ici.",
        action: { libelle: "Ouvrir les frais", route: "#finance/frais-dossier" }
      }
    },

    "finance/factures-fournisseurs": {
      section: "Finance & facturation",
      titre: "Factures fournisseurs",
      desc: "Factures reçues des fournisseurs et leur état de règlement.",
      source: { url: "/api/frais/facture" },
      id: "facture_id",
      filtreLocal: function (ligne) { return String(ligne.type_facture || "") === "recue"; },
      colonnes: [
        { cle: "numero_facture", libelle: "N° facture" },
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "date_facture", libelle: "Date", format: "date" },
        { cle: "fournisseur_id", libelle: "Fournisseur" },
        { cle: "montant_ttc", libelle: "Montant TTC", format: "montant", devise: "devise" },
        { cle: "statut_paiement", libelle: "Paiement" }
      ],
      filtres: [{ cle: "statut_paiement", libelle: "Paiement" }],
      creation: {
        url: "/api/frais/facture",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true },
          { cle: "type_facture", libelle: "Type", type: "select", options: ["recue", "emise"] },
          { cle: "numero_facture", libelle: "Numéro", requis: true },
          { cle: "date_facture", libelle: "Date", type: "date" },
          { cle: "fournisseur_id", libelle: "Fournisseur" },
          { cle: "montant_ht", libelle: "Montant HT", type: "number" },
          { cle: "montant_tva", libelle: "TVA", type: "number" },
          { cle: "montant_ttc", libelle: "Montant TTC", type: "number" },
          { cle: "devise", libelle: "Devise", type: "select", options: ["DZD", "EUR", "USD"] }
        ]
      },
      suppression: { url: "/api/frais/facture/{id}" },
      vide: {
        message: "Aucune facture fournisseur enregistrée.",
        action: { libelle: "Enregistrer une facture", actionCreation: true }
      }
    },

    "finance/facturation": {
      section: "Finance & facturation",
      titre: "Facturation client",
      desc: "Factures émises vers les clients et reste à encaisser.",
      source: { url: "/api/frais/facture" },
      id: "facture_id",
      filtreLocal: function (ligne) { return String(ligne.type_facture || "") === "emise"; },
      colonnes: [
        { cle: "numero_facture", libelle: "N° facture" },
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "client_id", libelle: "Client" },
        { cle: "date_facture", libelle: "Date", format: "date" },
        { cle: "montant_ttc", libelle: "Montant TTC", format: "montant", devise: "devise" },
        { cle: "statut_paiement", libelle: "Paiement" }
      ],
      filtres: [{ cle: "statut_paiement", libelle: "Paiement" }],
      creation: {
        url: "/api/frais/facture",
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true },
          { cle: "type_facture", libelle: "Type", type: "select", options: ["emise", "recue"] },
          { cle: "numero_facture", libelle: "Numéro", requis: true },
          { cle: "client_id", libelle: "Client" },
          { cle: "date_facture", libelle: "Date", type: "date" },
          { cle: "montant_ht", libelle: "Montant HT", type: "number" },
          { cle: "montant_tva", libelle: "TVA", type: "number" },
          { cle: "montant_ttc", libelle: "Montant TTC", type: "number" },
          { cle: "devise", libelle: "Devise", type: "select", options: ["DZD", "EUR", "USD"] },
          { cle: "notes", libelle: "Notes", type: "textarea" }
        ]
      },
      edition: {
        url: "/api/frais/facture/{id}",
        champs: [
          { cle: "montant_ttc", libelle: "Montant TTC", type: "number" },
          { cle: "statut_paiement", libelle: "Paiement", type: "select",
            options: ["en_attente", "paye", "partiel", "litige"] },
          { cle: "notes", libelle: "Notes", type: "textarea" }
        ]
      },
      suppression: { url: "/api/frais/facture/{id}" },
      vide: {
        message: "Aucune facture client émise.",
        action: { libelle: "Émettre une facture", actionCreation: true }
      }
    },

    "finance/paiements": {
      section: "Finance & facturation",
      titre: "Paiements",
      desc: "Factures et liquidations restant à régler.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/declarations/liquidation", "/api/frais/facture"],
      source: {
        charger: function () {
          return Promise.all([
            lire("/api/frais/facture").catch(function () { return []; }),
            lire("/api/declarations/liquidation").catch(function () { return []; })
          ]).then(function (r) {
            var factures = (r[0] || []).filter(function (f) {
              return String(f.statut_paiement || "") !== "paye";
            }).map(function (f) {
              return Object.assign({ origine: "Facture", cle: f.facture_id }, f);
            });
            var liquidations = (r[1] || []).filter(function (l) {
              return String(l.statut || "") !== "payee";
            }).map(function (l) {
              return Object.assign({
                origine: "Liquidation douanière",
                cle: l.liquidation_id,
                numero_facture: "Liquidation " + (l.date_liquidation || ""),
                montant_ttc: l.total_a_payer,
                statut_paiement: l.statut
              }, l);
            });
            return factures.concat(liquidations).filter(function (ligne) {
              return ligne.cle;
            });
          });
        }
      },
      id: "cle",
      colonnes: [
        { cle: "origine", libelle: "Origine" },
        { cle: "numero_facture", libelle: "Référence" },
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "montant_ttc", libelle: "Montant", format: "montant" },
        { cle: "statut_paiement", libelle: "État" },
        { cle: "date_facture", libelle: "Date", format: "date" }
      ],
      actions: [{
        libelle: "Marquer payé",
        url: function (ligne) {
          return ligne.origine === "Facture"
            ? "/api/frais/facture/" + ligne.facture_id
            : "/api/declarations/liquidation/" + ligne.liquidation_id;
        },
        methode: "PUT",
        corps: function (ligne) {
          return ligne.origine === "Facture"
            ? { statut_paiement: "paye" }
            : { statut: "payee" };
        },
        confirmation: "Confirmer l'encaissement de cette pièce ?",
        succes: "Paiement enregistré"
      }],
      vide: { message: "Aucun règlement en attente : tout est encaissé sur ce poste." }
    },

    "finance/reconciliation": {
      section: "Finance & facturation",
      titre: "Rapprochement financier",
      desc: "Rapprochez les frais engagés des factures enregistrées sur une " +
            "période. Le calcul est fait par le serveur. Limite connue : aucun " +
            "flux bancaire n'est importé sur ce poste, le rapprochement porte " +
            "donc sur les factures et retournera zéro opération tant que " +
            "l'import bancaire n'est pas branché.",
      source: { url: "/api/frais" },
      id: "frais_id",
      colonnes: [
        { cle: "dossier_id", libelle: "Dossier" },
        { cle: "categorie", libelle: "Catégorie" },
        { cle: "montant", libelle: "Montant", format: "montant", devise: "devise" },
        { cle: "reference_facture", libelle: "Facture" },
        { cle: "statut_paiement", libelle: "Paiement" }
      ],
      filtres: [{ cle: "statut_paiement", libelle: "Paiement" }],
      actions: [{
        libelle: "Lancer le rapprochement",
        url: "/api/frais/rapprochement/auto",
        methode: "POST",
        global: true,
        confirmation: "Lancer le rapprochement automatique des frais et factures ?",
        succes: "Rapprochement exécuté",
        resultat: true,
        /* L'API exige le dossier et la période : l'écran les demande au lieu
           d'envoyer une requête incomplète (422). */
        champs: [
          { cle: "dossier_id", libelle: "Dossier", requis: true,
            aide: "Identifiant du dossier concerné (dos_…)." },
          { cle: "date_debut", libelle: "Début de période", type: "date", requis: true },
          { cle: "date_fin", libelle: "Fin de période", type: "date", requis: true }
        ]
      }],
      vide: {
        message: "Aucun frais à rapprocher pour le moment.",
        action: { libelle: "Ouvrir les frais", route: "#finance/frais-dossier" }
      }
    },

    "finance/cloture": {
      section: "Finance & facturation",
      titre: "Clôture financière",
      desc: "Dossiers dont les frais sont réglés : vérifiez les conditions avant clôture.",
      source: { url: "/api/dossiers" },
      id: "id",
      filtreLocal: function (ligne) {
        return String(ligne.state || "") !== "archive";
      },
      colonnes: [
        { cle: "reference", libelle: "Référence" },
        { cle: "label", libelle: "Dossier" },
        { cle: "client_importateur", libelle: "Client" },
        { cle: "state_label", libelle: "État" },
        { cle: "updated_at", libelle: "Dernière activité", format: "date" }
      ],
      filtres: [{ cle: "state_label", libelle: "État" }],
      actions: [{
        libelle: "Archiver",
        url: "/api/dossiers/{id}/archiver",
        methode: "POST",
        confirmation: "Archiver ce dossier ? Il restera consultable mais sortira des listes actives.",
        succes: "Dossier archivé"
      }],
      vide: {
        message: "Aucun dossier à clôturer.",
        action: { libelle: "Voir les dossiers", route: "#dossiers/tous" }
      }
    },

    /* ---------------- Rapports ---------------- */
    "rapports/statistiques": {
      section: "Rapports & statistiques",
      titre: "Statistiques",
      desc: "Volumes réels du poste : dossiers, documents, extractions et contrôle.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/stats"],
      source: {
        charger: function () {
          return lire("/api/stats").then(function (stats) {
            var lignes = [];
            Object.keys(stats || {}).forEach(function (cle) {
              var valeur = stats[cle];
              if (valeur && typeof valeur === "object" && !Array.isArray(valeur)) return;
              lignes.push({ indicateur: cle, valeur: valeur });
            });
            return lignes;
          });
        }
      },
      id: "indicateur",
      colonnes: [
        { cle: "indicateur", libelle: "Indicateur" },
        { cle: "valeur", libelle: "Valeur" }
      ],
      lectureSeule: true,
      vide: { message: "Le serveur n'expose aucune statistique sur ce poste." }
    },

    "rapports/exports": {
      section: "Rapports & statistiques",
      titre: "Exports",
      desc: "Exportez les documents traités dans les formats produits par le serveur.",
      source: { url: "/api/jobs?limit=200" },
      id: "id",
      filtreLocal: function (ligne) { return ligne.status === "done"; },
      colonnes: [
        { cle: "filename", libelle: "Fichier" },
        { cle: "status", libelle: "État" },
        { cle: "created_at", libelle: "Traité le", format: "date" }
      ],
      actions: [{
        libelle: "Télécharger (JSON)",
        url: "/api/jobs/{id}/export/json",
        methode: "GET",
        telecharger: true
      }, {
        libelle: "Télécharger (CSV)",
        url: "/api/jobs/{id}/export/csv",
        methode: "GET",
        telecharger: true
      }],
      lectureSeule: true,
      vide: {
        message: "Aucun document traité à exporter.",
        action: { libelle: "Importer un document", route: "#documents/import" }
      }
    },

    /* ---------------- Référentiels ---------------- */
    "referentiels/clients": {
      section: "Référentiels & paramètres",
      titre: "Clients",
      desc: "Importateurs et donneurs d'ordre : coordonnées, identifiants fiscaux, contacts.",
      source: { url: "/api/clients" },
      id: "client_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "name", libelle: "Nom" },
        { cle: "legal_name", libelle: "Raison sociale" },
        { cle: "tax_id", libelle: "NIF" },
        { cle: "city", libelle: "Ville" },
        { cle: "country", libelle: "Pays (code ISO à 2 lettres)", longueurMax: 2 },
        { cle: "email", libelle: "Courriel" },
        { cle: "status", libelle: "Statut" }
      ],
      filtres: [{ cle: "status", libelle: "Statut" }],
      actions: [{ libelle: "Dossiers", url: "/api/clients/{id}/dossiers", methode: "GET", afficher: true }],
      creation: {
        url: "/api/clients",
        champs: [
          { cle: "name", libelle: "Nom commercial", requis: true },
          { cle: "legal_name", libelle: "Raison sociale" },
          { cle: "tax_id", libelle: "NIF / identifiant fiscal" },
          { cle: "email", libelle: "Courriel", type: "email" },
          { cle: "phone", libelle: "Téléphone" },
          { cle: "address", libelle: "Adresse", type: "textarea" },
          { cle: "city", libelle: "Ville" },
          { cle: "wilaya", libelle: "Wilaya" },
          { cle: "country", libelle: "Pays (code ISO à 2 lettres)",
            longueurMax: 2, valeur: "DZ", referentiel: "pays",
            aide: "Code ISO 3166-1 alpha-2 : DZ, FR, ES…" },
          { cle: "status", libelle: "Statut", type: "select", options: ["active", "inactive"] }
        ]
      },
      edition: {
        url: "/api/clients/{id}",
        champs: [
          { cle: "name", libelle: "Nom commercial" },
          { cle: "legal_name", libelle: "Raison sociale" },
          { cle: "tax_id", libelle: "NIF / identifiant fiscal" },
          { cle: "email", libelle: "Courriel" },
          { cle: "phone", libelle: "Téléphone" },
          { cle: "city", libelle: "Ville" },
          { cle: "status", libelle: "Statut", type: "select", options: ["active", "inactive"] }
        ]
      },
      suppression: { url: "/api/clients/{id}" },
      vide: {
        message: "Aucun client enregistré. Créez le premier pour rattacher des dossiers.",
        action: { libelle: "Créer un client", actionCreation: true }
      }
    },

    "referentiels/fournisseurs": {
      section: "Référentiels & paramètres",
      titre: "Fournisseurs",
      desc: "Prestataires et fournisseurs étrangers intervenant sur les dossiers.",
      source: { url: "/api/fournisseurs" },
      id: "fournisseur_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "nom", libelle: "Nom" },
        { cle: "nom_commercial", libelle: "Nom commercial" },
        { cle: "pays", libelle: "Pays" },
        { cle: "nif", libelle: "NIF" },
        { cle: "contact", libelle: "Contact" },
        { cle: "telephone", libelle: "Téléphone" }
      ],
      creation: {
        url: "/api/fournisseurs",
        champs: [
          { cle: "nom", libelle: "Nom", requis: true },
          { cle: "nom_commercial", libelle: "Nom commercial", requis: true,
            aide: "Champ obligatoire côté serveur, au même titre que le nom." },
          { cle: "pays", libelle: "Pays (code ISO à 2 lettres)", longueurMax: 2,
            referentiel: "pays",
            aide: "Code ISO 3166-1 alpha-2 : FR, ES, CN…" },
          { cle: "nif", libelle: "NIF / identifiant fiscal" },
          { cle: "rc", libelle: "Registre de commerce" },
          { cle: "contact", libelle: "Personne de contact" },
          { cle: "telephone", libelle: "Téléphone" },
          { cle: "email", libelle: "Courriel", type: "email" },
          { cle: "adresse", libelle: "Adresse", type: "textarea" },
          { cle: "notes", libelle: "Notes", type: "textarea" }
        ]
      },
      edition: {
        url: "/api/fournisseurs/{id}",
        champs: [
          { cle: "nom", libelle: "Nom" },
          { cle: "nom_commercial", libelle: "Nom commercial" },
          { cle: "pays", libelle: "Pays (code ISO à 2 lettres)", longueurMax: 2,
            referentiel: "pays" },
          { cle: "nif", libelle: "NIF / identifiant fiscal" },
          { cle: "rc", libelle: "Registre de commerce" },
          { cle: "contact", libelle: "Personne de contact" },
          { cle: "telephone", libelle: "Téléphone" },
          { cle: "email", libelle: "Courriel", type: "email" },
          { cle: "adresse", libelle: "Adresse", type: "textarea" },
          { cle: "notes", libelle: "Notes", type: "textarea" }
        ]
      },
      suppression: { url: "/api/fournisseurs/{id}" },
      vide: {
        message: "Aucun fournisseur enregistré.",
        action: { libelle: "Créer un fournisseur", actionCreation: true }
      }
    },

    "referentiels/transporteurs": {
      section: "Référentiels & paramètres",
      titre: "Transporteurs",
      desc: "Transporteurs routiers, agréments et contacts d'exploitation.",
      source: { url: "/api/transport/transporteurs" },
      id: "transporteur_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "nom", libelle: "Nom" },
        { cle: "raison_sociale", libelle: "Raison sociale" },
        { cle: "nif", libelle: "NIF" },
        { cle: "telephone", libelle: "Téléphone" },
        { cle: "conducteur_principal", libelle: "Conducteur" },
        { cle: "statut", libelle: "Statut" }
      ],
      creation: {
        url: "/api/transport/transporteurs",
        champs: [
          { cle: "nom", libelle: "Nom", requis: true },
          { cle: "raison_sociale", libelle: "Raison sociale" },
          { cle: "nif", libelle: "NIF" },
          { cle: "telephone", libelle: "Téléphone" },
          { cle: "email", libelle: "Courriel" },
          { cle: "conducteur_principal", libelle: "Conducteur principal" },
          { cle: "statut", libelle: "Statut", type: "select", options: ["actif", "inactif"] }
        ]
      },
      suppression: { url: "/api/transport/transporteurs/{id}" },
      vide: {
        message: "Aucun transporteur enregistré.",
        action: { libelle: "Créer un transporteur", actionCreation: true }
      }
    },

    "referentiels/navires": {
      section: "Référentiels & paramètres",
      titre: "Navires",
      desc: "Flotte référencée : IMO, compagnie, pavillon et type.",
      source: { url: "/api/navires" },
      id: "navire_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "nom", libelle: "Navire" },
        { cle: "numero_imo", libelle: "IMO" },
        { cle: "compagnie", libelle: "Compagnie" },
        { cle: "pays_immatri", libelle: "Pavillon" },
        { cle: "type_navire", libelle: "Type" }
      ],
      creation: {
        url: "/api/navires",
        champs: [
          { cle: "nom", libelle: "Nom du navire", requis: true },
          { cle: "numero_imo", libelle: "Numéro IMO" },
          { cle: "compagnie", libelle: "Compagnie" },
          { cle: "pays_immatri", libelle: "Pavillon", referentiel: "pays" },
          { cle: "type_navire", libelle: "Type" },
          { cle: "notes", libelle: "Notes", type: "textarea" }
        ]
      },
      suppression: { url: "/api/navires/{id}" },
      vide: {
        message: "Aucun navire référencé.",
        action: { libelle: "Référencer un navire", actionCreation: true }
      }
    },

    /* ---------------- Administration & sécurité ---------------- */
    "admin/roles": {
      section: "Administration & sécurité",
      titre: "Rôles et permissions",
      desc: "Rôles livrés avec l'application (non modifiables) et rôles " +
            "personnalisés créés sur ce poste.",
      source: {
        /* Deux sources : signalées pour la mesure, chargées ensemble. */
        sources: ["/api/rbac/utilisateurs", "/api/rbac/roles"],
        charger: function (lire) {
          /* Le catalogue livré (renvoyé avec les utilisateurs) et les rôles
             personnalisés (magasin RBAC). */
          return Promise.all([
            lire("/api/rbac/utilisateurs").catch(function () { return null; }),
            lire("/api/rbac/roles").catch(function () { return []; })
          ]).then(function (reponses) {
            var catalogue = (reponses[0] && reponses[0].roles_disponibles) || [];
            var personnalises = Array.isArray(reponses[1]) ? reponses[1] : [];
            var lignes = catalogue.map(function (nom) {
              return { nom: nom, role_id: "", origine: "livré",
                       description: "Rôle fourni avec l'application",
                       niveau_acces: null, permissions: [] };
            });
            personnalises.forEach(function (role) {
              lignes.push({ nom: role.nom, role_id: role.id, origine: "personnalisé",
                            description: role.description,
                            niveau_acces: role.niveau_acces,
                            permissions: role.permissions || [] });
            });
            return lignes;
          });
        }
      },
      id: "role_id",
      colonnes: [
        { cle: "nom", libelle: "Rôle" },
        { cle: "origine", libelle: "Origine" },
        { cle: "description", libelle: "Description" },
        { cle: "niveau_acces", libelle: "Niveau", format: "nombre" },
        { cle: "permissions", libelle: "Permissions", format: "liste" }
      ],
      filtres: [{ cle: "origine", libelle: "Origine" }],
      creation: {
        url: "/api/rbac/roles",
        champs: [
          { cle: "nom", libelle: "Nom du rôle", requis: true,
            aide: "Identifiant stable, par exemple « chef_escale »." },
          { cle: "description", libelle: "Description" },
          { cle: "niveau_acces", libelle: "Niveau d'accès", type: "number",
            aide: "1 = lecture, 2 = écriture, 3 = administration." },
          { cle: "permissions", libelle: "Permissions", type: "liste",
            aide: "Séparées par des virgules, par exemple « ecriture, export »." }
        ]
      },
      edition: {
        url: "/api/rbac/roles/{id}",
        champs: [
          { cle: "description", libelle: "Description" },
          { cle: "niveau_acces", libelle: "Niveau d'accès", type: "number" },
          { cle: "permissions", libelle: "Permissions", type: "liste" }
        ],
        /* Un rôle livré n'est pas modifiable : le bouton disparaît. */
        masquer: function (ligne) { return !ligne.role_id; }
      },
      suppression: {
        url: "/api/rbac/roles/{id}",
        masquer: function (ligne) { return !ligne.role_id; }
      },
      vide: {
        message: "Le serveur n'annonce aucun rôle : le catalogue est vide.",
        action: { libelle: "Créer un rôle", actionCreation: true }
      }
    },

    "admin/utilisateurs": {
      section: "Administration & sécurité",
      titre: "Utilisateurs",
      desc: "Comptes d'accès : rôles, périmètre de dossiers et jeton personnel. " +
            "Le jeton n'est affiché qu'à la création ou à sa régénération.",
      source: { url: "/api/rbac/utilisateurs" },
      sourceCle: "utilisateurs",
      id: "nom",
      colonnes: [
        { cle: "nom", libelle: "Utilisateur" },
        { cle: "roles", libelle: "Rôles", format: "liste" },
        { cle: "dossiers", libelle: "Dossiers autorisés", format: "liste" },
        { cle: "environnement", libelle: "Jeton d'environnement", format: "booleen" }
      ],
      creation: {
        url: "/api/rbac/utilisateurs",
        champs: [
          { cle: "nom", libelle: "Identifiant", requis: true,
            aide: "Nom unique du compte, par exemple « karim.b »." },
          { cle: "roles", libelle: "Rôles", type: "liste", requis: true,
            aide: "Séparés par des virgules : superviseur, agent_de_transit…" },
          { cle: "dossiers", libelle: "Dossiers autorisés", type: "liste",
            aide: "Vide = aucun cloisonnement par dossier." }
        ],
        succes: function (reponse) {
          if (!reponse || !reponse.jeton) return;
          afficherResultat("Jeton d'accès — affiché une seule fois",
            { utilisateur: reponse.utilisateur && reponse.utilisateur.nom,
              jeton: reponse.jeton,
              note: "Notez-le maintenant : il n'est plus relisible. " +
                    "Perdu, il se régénère mais l'ancien cesse aussitôt de fonctionner." });
        }
      },
      edition: {
        url: "/api/rbac/utilisateurs/{id}",
        champs: [
          { cle: "roles", libelle: "Rôles", type: "liste" },
          { cle: "dossiers", libelle: "Dossiers autorisés", type: "liste" }
        ]
      },
      suppression: { url: "/api/rbac/utilisateurs/{id}" },
      vide: {
        message: "Aucun compte déclaré : le cloisonnement RBAC est inactif sur ce poste. " +
                 "Créez le premier utilisateur pour l'activer.",
        action: { libelle: "Créer un utilisateur", actionCreation: true }
      }
    },

    "admin/permissions": {
      section: "Administration & sécurité",
      titre: "Permissions",
      desc: "Droits unitaires attribuables aux rôles.",
      source: { url: "/api/rbac/permissions" },
      id: "permission_id",
      idAlt: ["id"],
      colonnes: [
        { cle: "nom", libelle: "Permission" },
        { cle: "description", libelle: "Description" },
        { cle: "categorie", libelle: "Famille" }
      ],
      creation: {
        url: "/api/rbac/permissions",
        champs: [
          { cle: "nom", libelle: "Nom", requis: true },
          { cle: "description", libelle: "Description", type: "textarea" },
          { cle: "categorie", libelle: "Famille" }
        ]
      },
      suppression: { url: "/api/rbac/permissions/{id}" },
      vide: {
        message: "Aucune permission déclarée : le serveur applique ses règles par défaut.",
        action: { libelle: "Créer une permission", actionCreation: true }
      }
    },

    "admin/equipes": {
      section: "Administration & sécurité",
      titre: "Équipes",
      desc: "Groupes d'utilisateurs et périmètre de responsabilité.",
      source: { url: "/api/referentiels/equipes" },
      id: "id",
      sourceCle: "entrees",
      colonnes: [
        { cle: "libelle", libelle: "Équipe" },
        { cle: "code", libelle: "Code" },
        { cle: "cree_le", libelle: "Créée le", format: "date" }
      ],
      creation: {
        url: "/api/referentiels/equipes",
        champs: [
          { cle: "libelle", libelle: "Nom de l'équipe", requis: true },
          { cle: "code", libelle: "Code" },
          { cle: "attributs.responsable", libelle: "Responsable" },
          { cle: "attributs.membres", libelle: "Membres (séparés par des virgules)" }
        ]
      },
      suppression: { url: "/api/referentiels/equipes/{id}" },
      vide: {
        message: "Aucune équipe définie. Créez-en une pour regrouper les utilisateurs.",
        action: { libelle: "Créer une équipe", actionCreation: true }
      }
    },

    "admin/referentiels": {
      section: "Administration & sécurité",
      titre: "Catalogue des référentiels",
      desc: "Collections de référence disponibles et leur volume réel.",
      source: { url: "/api/referentiels" },
      sourceCle: "collections",
      id: "nom",
      colonnes: [
        { cle: "titre", libelle: "Référentiel" },
        { cle: "description", libelle: "Rôle" },
        { cle: "total", libelle: "Entrées", format: "nombre" }
      ],
      actions: [{
        libelle: "Ouvrir",
        route: function (ligne) {
          return "#referentiels/" + String(ligne.nom || "").replace(/-complementaires$/, "");
        }
      }],
      lectureSeule: true,
      vide: { message: "Le serveur n'expose aucun référentiel." }
    },

    "admin/parametres": {
      section: "Administration & sécurité",
      titre: "Configuration générale",
      desc: "État réel du chiffrement, de la sécurité et de la traçabilité du poste.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/auth/status", "/api/encryption", "/api/security", "/api/tracabilite/avertissement"],
      source: {
        charger: function () {
          return Promise.all([
            lire("/api/security").catch(function () { return null; }),
            lire("/api/encryption").catch(function () { return null; }),
            lire("/api/tracabilite/avertissement").catch(function () { return null; }),
            lire("/api/auth/status").catch(function () { return null; })
          ]).then(function (r) {
            var lignes = [];
            function ajouter(origine, objet) {
              if (!objet || typeof objet !== "object") return;
              Object.keys(objet).forEach(function (cle) {
                var valeur = objet[cle];
                if (valeur && typeof valeur === "object" && !Array.isArray(valeur)) return;
                lignes.push({
                  origine: origine,
                  parametre: cle,
                  valeur: Array.isArray(valeur) ? valeur.length : valeur
                });
              });
            }
            ajouter("Sécurité", r[0]);
            ajouter("Chiffrement", r[1]);
            ajouter("Traçabilité", r[2]);
            ajouter("Authentification", r[3]);
            return lignes;
          });
        }
      },
      id: "parametre",
      colonnes: [
        { cle: "origine", libelle: "Domaine" },
        { cle: "parametre", libelle: "Paramètre" },
        { cle: "valeur", libelle: "Valeur" }
      ],
      lectureSeule: true,
      vide: { message: "Le serveur n'expose aucun paramètre de sécurité." }
    },

    "admin/parametres-ocr": {
      section: "Administration & sécurité",
      titre: "Paramètres OCR",
      desc: "Surveillance des dossiers scannés et profils d'extraction disponibles.",
      /* Sources interrogées : documentées pour la matrice et les tests. */
      sources: ["/api/profiles/catalog", "/api/watch"],
      source: {
        charger: function () {
          return Promise.all([
            lire("/api/watch").catch(function () { return null; }),
            lire("/api/profiles/catalog").catch(function () { return null; })
          ]).then(function (r) {
            var lignes = [];
            var veille = r[0] || {};
            Object.keys(veille).forEach(function (cle) {
              var valeur = veille[cle];
              if (Array.isArray(valeur)) {
                lignes.push({ domaine: "Surveillance", parametre: cle,
                              valeur: valeur.length + " élément(s)" });
              } else if (!valeur || typeof valeur !== "object") {
                lignes.push({ domaine: "Surveillance", parametre: cle, valeur: valeur });
              }
            });
            var catalog = r[1];
            if (catalog) {
              var profils = Array.isArray(catalog) ? catalog : (catalog.profils || catalog.profiles || []);
              lignes.push({ domaine: "Profils", parametre: "Profils disponibles",
                            valeur: profils.length });
            }
            return lignes;
          });
        }
      },
      id: "parametre",
      colonnes: [
        { cle: "domaine", libelle: "Domaine" },
        { cle: "parametre", libelle: "Paramètre" },
        { cle: "valeur", libelle: "Valeur" }
      ],
      lectureSeule: true,
      vide: { message: "Aucun paramètre OCR exposé par le serveur." }
    },

    "documents/versions": {
      section: "Documents & OCR",
      titre: "Gestion des versions",
      desc: "Reprises d'un même fichier : chaque retraitement crée une version, " +
            "l'original reste conservé.",
      source: { url: "/api/jobs?limit=300" },
      id: "id",
      colonnes: [
        { cle: "filename", libelle: "Fichier" },
        { cle: "file_hash", libelle: "Empreinte" },
        { cle: "attempts", libelle: "Tentatives", format: "nombre" },
        { cle: "status", libelle: "État" },
        { cle: "created_at", libelle: "Créé le", format: "date" }
      ],
      filtres: [{ cle: "status", libelle: "État" }],
      actions: [{
        libelle: "Ouvrir",
        route: function (ligne) { return "#documents/resultat"; },
        ouvrirJob: true
      }],
      lectureSeule: true,
      vide: { message: "Aucun document traité sur ce poste." }
    }
  };

  /* ==================== Documents & OCR ==================== */
  /* L'atelier de capture reste la page historique (`#tab-dashboard`) : on ne
     duplique pas l'import. En revanche la vue d'ensemble et l'extraction
     n'avaient aucun écran — elles retombaient sur le tableau de bord général.
     Ces deux écrans lisent la file de traitement réelle (`GET /api/jobs`). */

  ECRANS["documents"] = {
    section: "Documents & OCR",
    titre: "Vue d'ensemble",
    desc: "Activité réelle du poste : file de traitement, états, moteurs et " +
          "progression. Chaque ligne est un document traité ou en attente.",
    source: { url: "/api/jobs?limit=300" },
    id: "id",
    colonnes: [
      { cle: "filename", libelle: "Fichier" },
      { cle: "status", libelle: "État" },
      { cle: "progress", libelle: "Progression", format: "progression" },
      { cle: "options.engine", libelle: "Moteur" },
      { cle: "created_at", libelle: "Reçu le", format: "date" }
    ],
    filtres: [{ cle: "status", libelle: "État" }],
    actions: [{
      libelle: "Ouvrir dans l'atelier",
      executer: function (ligne) {
        window.location.hash = "#documents/resultat";
        if (window.UniOCRShell && typeof window.UniOCRShell.ouvrirJob === "function") {
          window.UniOCRShell.ouvrirJob(ligne.id);
        }
      }
    }],
    lectureSeule: true,
    vide: {
      message: "Aucun document traité pour l'instant. Importez un document " +
               "depuis l'atelier pour alimenter la file.",
      action: { libelle: "Importer un document", route: "#documents/import" }
    }
  };

  ECRANS["documents/ocr"] = {
    section: "Documents & OCR",
    titre: "Extraction OCR",
    desc: "Documents passés à l'OCR : état, tentatives et moteur utilisé. " +
          "Chaque action interroge le serveur — aucun texte n'est simulé.",
    source: { url: "/api/jobs?limit=300" },
    id: "id",
    colonnes: [
      { cle: "filename", libelle: "Fichier" },
      { cle: "status", libelle: "État" },
      { cle: "attempts", libelle: "Tentatives", format: "nombre" },
      { cle: "options.engine", libelle: "Moteur" },
      { cle: "updated_at", libelle: "Mis à jour", format: "date" }
    ],
    filtres: [{ cle: "status", libelle: "État" }],
    actions: [
      {
        libelle: "Ouvrir le résultat",
        executer: function (ligne) {
          var id = ligne.id || ligne.job_id;
          if (String(ligne.status || "") !== "done") {
            toast("Document non traité : aucun résultat à ouvrir", "info");
            return;
          }
          if (window.UniOCRResultats && window.UniOCRResultats.ouvrir) {
            window.UniOCRResultats.ouvrir(id);
          } else {
            toast("Résultat indisponible", "error");
          }
        }
      },
      {
        libelle: "Texte",
        url: "/api/jobs/{id}/text",
        methode: "GET",
        afficher: true
      },
      {
        libelle: "Résultat",
        url: "/api/jobs/{id}/result",
        methode: "GET",
        afficher: true
      },
      {
        /* Le journal d'audit, filtré sur ce document : d'où vient son état. */
        libelle: "Historique",
        url: "/api/jobs/{id}/historique",
        methode: "GET",
        afficher: true,
        timeline: true,
        enCours: "Lecture de l'historique…"
      },
      {
        libelle: "Relancer",
        url: "/api/jobs/{id}/retry",
        methode: "POST",
        confirmation: "Relancer le traitement de ce document ?",
        succes: "Traitement relancé"
      }
    ],
    lectureSeule: false,
    vide: {
      message: "Aucun document à extraire. Les fichiers importés apparaissent " +
               "ici dès leur mise en file.",
      action: { libelle: "Importer un document", route: "#documents/import" }
    }
  };

    /* ==================== Dossiers et espace de travail ==================== */
  /* Ces écrans remplacent les entrées de menu qui retombaient sur la vue
     d'ensemble de leur module. Ils lisent `GET /api/dossiers` (et les alertes
     du tableau de bord) et filtrent sur les états **réellement présents** dans
     les données : aucune notion de « bloqué » n'est inventée ici, un dossier
     bloqué est un dossier signalé par le contrôle. */

  var COLONNES_DOSSIER = [
    { cle: "reference", libelle: "Référence" },
    { cle: "label", libelle: "Dossier" },
    { cle: "client_importateur", libelle: "Client" },
    { cle: "state_label", libelle: "État" },
    { cle: "gestionnaire", libelle: "Gestionnaire" },
    { cle: "date_ouverture", libelle: "Ouvert le", format: "date" },
    { cle: "priorite", libelle: "Priorité" }
  ];

  function actionOuvrirDossier() {
    return {
      libelle: "Ouvrir",
      executer: function (ligne) {
        if (!ligne.id) return;
        if (window.UniOCRShell && typeof window.UniOCRShell.ouvrirDossier === "function") {
          window.UniOCRShell.ouvrirDossier(ligne.id);
          return;
        }
        window.location.hash = "#dossiers";
      }
    };
  }

  function ecranDossiers(route, options) {
    ECRANS[route] = {
      section: options.section,
      titre: options.titre,
      desc: options.desc,
      source: options.source || { url: "/api/dossiers" },
      filtreLocal: options.filtreLocal,
      id: "id",
      colonnes: (options.colonnes || COLONNES_DOSSIER).concat(options.colonnesSup || []),
      filtres: options.filtres || [],
      actions: options.actions || [actionOuvrirDossier()],
      lectureSeule: true,
      vide: options.vide
    };
    return ECRANS[route];
  }

  function etatDe(ligne) {
    return String((ligne && ligne.state) || "");
  }

  ecranDossiers("dossiers/en-cours", {
    section: "Gestion des dossiers",
    titre: "Dossiers en cours",
    desc: "Dossiers ouverts et en cours de traitement : état, gestionnaire, " +
          "date d'ouverture et priorité. Cliquez sur « Ouvrir » pour travailler " +
          "le dossier dans son espace.",
    filtreLocal: function (ligne) { return etatDe(ligne) === "en_preparation"; },
    vide: {
      message: "Aucun dossier en cours de préparation. Les dossiers créés " +
               "apparaissent ici dès leur ouverture.",
      action: { libelle: "Créer un dossier", route: "#dossiers/nouveau" }
    }
  });

  ecranDossiers("dossiers/bloques", {
    section: "Gestion des dossiers",
    titre: "Dossiers bloqués",
    desc: "Dossiers sur lesquels le contrôle a signalé une anomalie : " +
          "pièces manquantes, incohérence de champs. La liste vient du " +
          "croisement entre les dossiers et les alertes du tableau de bord.",
    source: {
      sources: ["/api/dossiers", "/api/dashboard/alertes"],
      charger: function (lire) {
        return Promise.all([
          lire("/api/dossiers"),
          lire("/api/dashboard/alertes").catch(function () { return { alertes: [] }; })
        ]).then(function (resultats) {
          var dossiers = resultats[0] || [];
          var alertes = (resultats[1] && resultats[1].alertes) || [];
          var parDossier = {};
          alertes.forEach(function (alerte) {
            if (!alerte || !alerte.dossier_id) return;
            parDossier[alerte.dossier_id] = parDossier[alerte.dossier_id] || [];
            parDossier[alerte.dossier_id].push(alerte.titre || alerte.type || "Alerte");
          });
          return dossiers.filter(function (dossier) {
            return Boolean(parDossier[dossier.id]);
          }).map(function (dossier) {
            var copie = Object.assign({}, dossier);
            copie.alertes = parDossier[dossier.id];
            return copie;
          });
        });
      }
    },
    colonnesSup: [{ cle: "alertes", libelle: "Anomalies" }],
    vide: {
      message: "Aucun dossier bloqué : le contrôle n'a signalé aucune anomalie " +
               "sur les dossiers enregistrés."
    }
  });

  ecranDossiers("dossiers/clotures", {
    section: "Gestion des dossiers",
    titre: "Dossiers clôturés",
    desc: "Dossiers archivés après traitement complet. Ils restent " +
          "consultables et exportables.",
    filtreLocal: function (ligne) { return etatDe(ligne) === "archive"; },
    vide: { message: "Aucun dossier clôturé pour le moment." }
  });

  ecranDossiers("workspace/taches", {
    section: "Mon espace de travail",
    titre: "Mes tâches",
    desc: "File de travail : dossiers en révision ou incomplets, c'est-à-dire " +
          "ceux sur lesquels une action est attendue.",
    filtreLocal: function (ligne) {
      var etat = etatDe(ligne);
      return etat === "revision_requise" || etat === "incomplet";
    },
    vide: { message: "Aucune tâche en attente : tous les dossiers sont à jour." }
  });

  ecranDossiers("workspace/en-attente", {
    section: "Mon espace de travail",
    titre: "En attente de pièces",
    desc: "Dossiers ouverts pour lesquels aucune pièce n'a encore été reçue : " +
          "ils attendent les documents du client ou du transitaire.",
    filtreLocal: function (ligne) {
      return etatDe(ligne) === "en_preparation" &&
        (!ligne.pieces || ligne.pieces.length === 0);
    },
    vide: { message: "Aucun dossier en attente de pièces : toutes les pièces " +
                     "attendues ont été reçues." }
  });

  ECRANS["workspace/alertes"] = {
    section: "Mon espace de travail",
    titre: "Mes alertes",
    desc: "Alertes produites par le contrôle des dossiers : pièces manquantes, " +
          "incohérences détectées. Chaque alerte renvoie au dossier concerné.",
    source: { url: "/api/dashboard/alertes" },
    sourceCle: "alertes",
    id: "dossier_id",
    idAlt: ["dossier_id"],
    colonnes: [
      { cle: "niveau", libelle: "Niveau" },
      { cle: "titre", libelle: "Alerte" },
      { cle: "message", libelle: "Détail" },
      { cle: "dossier_id", libelle: "Dossier" }
    ],
    filtres: [{ cle: "niveau", libelle: "Niveau" }],
    actions: [{
      libelle: "Ouvrir le dossier",
      executer: function (ligne) {
        if (window.UniOCRShell && typeof window.UniOCRShell.ouvrirDossier === "function") {
          window.UniOCRShell.ouvrirDossier(ligne.dossier_id);
        }
      }
    }],
    lectureSeule: true,
    vide: { message: "Aucune alerte active : le contrôle n'a rien signalé." }
  };

  ECRANS["workspace/recents"] = {
    section: "Mon espace de travail",
    titre: "Dossiers récents",
    desc: "Les trente derniers dossiers ouverts, du plus récent au plus ancien.",
    source: {
      sources: ["/api/dossiers"],
      charger: function (lire) {
        return lire("/api/dossiers").then(function (dossiers) {
          return (dossiers || []).slice().sort(function (a, b) {
            return Number(b.date_ouverture || 0) - Number(a.date_ouverture || 0);
          }).slice(0, 30);
        });
      }
    },
    id: "id",
    colonnes: COLONNES_DOSSIER,
    actions: [actionOuvrirDossier()],
    lectureSeule: true,
    vide: {
      message: "Aucun dossier ouvert pour le moment.",
      action: { libelle: "Créer un dossier", route: "#dossiers/nouveau" }
    }
  };

    /* Référentiels génériques : une entrée par collection exposée par
     `GET /api/referentiels`. Les champs libres sont saisis dans `attributs`. */
  [
    { route: "referentiels/ports", collection: "ports", titre: "Ports",
      desc: "Ports de chargement, de destination et d'escale.",
      champs: [["pays", "Pays"], ["type", "Type de port"]] },
    { route: "referentiels/pays", collection: "pays", titre: "Pays",
      desc: "Pays d'origine, d'expédition et de destination.",
      champs: [["zone", "Zone géographique"]] },
    { route: "referentiels/devises", collection: "devises", titre: "Devises",
      desc: "Devises utilisées par la facturation et les dossiers.",
      champs: [["symbole", "Symbole"]] },
    { route: "referentiels/types-marchandises", collection: "types-marchandises",
      titre: "Types de marchandises",
      desc: "Natures de marchandise et contraintes déclaratives.",
      champs: [["categorie", "Catégorie"], ["contraintes", "Contraintes"]] },
    { route: "referentiels/tarifs", collection: "tarifs", titre: "Référentiels tarifaires",
      desc: "Grilles de frais appliquées aux dossiers.",
      champs: [["categorie", "Catégorie"], ["montant", "Montant"], ["unite", "Unité"]] },
    { route: "referentiels/regles-documentaires", collection: "regles-documentaires",
      titre: "Règles documentaires",
      desc: "Pièces attendues par profil et conditions d'application.",
      champs: [["profil", "Profil de dossier"], ["pieces", "Pièces attendues"]] },
    { route: "referentiels/parametres-metier", collection: "parametres",
      titre: "Paramètres métier",
      desc: "Valeurs de configuration propres à l'exploitation.",
      champs: [["portee", "Portée"], ["valeur", "Valeur"]] },
    { route: "referentiels/types-documents", collection: "types-documents",
      titre: "Types de documents",
      desc: "Typologie documentaire utilisée par la classification.",
      champs: [["profil", "Profil d'extraction"], ["obligatoire", "Obligatoire (oui/non)"]] }
  ].forEach(function (def) {
    var champsCreation = [
      { cle: "libelle", libelle: "Libellé", requis: true },
      { cle: "code", libelle: "Code" }
    ].concat(def.champs.map(function (paire) {
      return { cle: "attributs." + paire[0], libelle: paire[1] };
    }));
    ECRANS[def.route] = {
      section: "Référentiels & paramètres",
      titre: def.titre,
      desc: def.desc,
      source: { url: "/api/referentiels/" + def.collection },
      sourceCle: "entrees",
      id: "id",
      colonnes: [
        { cle: "libelle", libelle: "Libellé" },
        { cle: "code", libelle: "Code" },
        { cle: "cree_le", libelle: "Créé le", format: "date" }
      ],
      actions: (["ports", "pays", "devises"].indexOf(def.collection) >= 0 ? [{
        /* Données de référence publiques : un poste neuf n'a aucune raison de
           faire ressaisir les ports, pays et devises à la main. L'opération
           est idempotente et ne touche ni dossiers ni montants. */
        libelle: "Charger le jeu de base",
        url: "/api/referentiels/" + def.collection + "/base",
        methode: "POST",
        global: true,
        confirmation: "Ajouter les entrées de référence manquantes ? Les entrées " +
                      "déjà présentes ne sont pas modifiées.",
        succes: "Jeu de base appliqué",
        resultat: true,
        resumer: function (reponse) {
          if (!reponse || typeof reponse.ajoutes !== "number") return "";
          if (!reponse.ajoutes) {
            return "Rien à ajouter : les " + reponse.deja_presents +
                   " entrées de référence sont déjà présentes.";
          }
          return reponse.ajoutes + " entrée" + (reponse.ajoutes > 1 ? "s" : "") +
                 " ajoutée" + (reponse.ajoutes > 1 ? "s" : "") + ", " +
                 reponse.deja_presents + " déjà présente" +
                 (reponse.deja_presents > 1 ? "s" : "") + " — total " +
                 reponse.total + ".";
        }
      }] : []),
      creation: { url: "/api/referentiels/" + def.collection, champs: champsCreation },
      edition: { url: "/api/referentiels/" + def.collection + "/{id}", champs: champsCreation },
      suppression: { url: "/api/referentiels/" + def.collection + "/{id}" },
      vide: {
        message: "Ce référentiel est vide. Ajoutez une première entrée : elle sera " +
                 "disponible dans les formulaires métier.",
        action: { libelle: "Ajouter une entrée", actionCreation: true }
      }
    };
  });

  /* Les paramètres généraux : valeurs réellement lues par le serveur,
     écrites dans `data/parametres.json` (jamais dans la config livrée).
     La modification est validée côté serveur (422 nommant le champ) ; ici on
     n'affiche que ce que le serveur annonce. */
  ECRANS["referentiels/parametres"] = {
    section: "Référentiels & paramètres",
    titre: "Paramètres généraux",
    desc: "Réglages appliqués par le serveur d'extraction. Chaque valeur est " +
          "validée avant écriture et prend effet immédiatement.",
    source: { url: "/api/parametres" },
    sourceCle: "parametres",
    id: "cle",
    colonnes: [
      { cle: "libelle", libelle: "Réglage" },
      { cle: "valeur", libelle: "Valeur" },
      { cle: "etat", libelle: "État" },
      { cle: "defaut", libelle: "Défaut" },
      { cle: "effet", libelle: "Ce que cela change" }
    ],
    filtres: [{ cle: "etat", libelle: "État" }],
    edition: {
      url: "/api/parametres/{id}",
      champs: [
        { cle: "valeur", libelle: "Nouvelle valeur", requis: true,
          aide: "Entier, ou codes de langue séparés par des virgules. " +
                "Le serveur refuse une valeur hors bornes en nommant le réglage." }
      ]
    },
    actions: [{
      libelle: "Rétablir le défaut",
      url: "/api/parametres/{id}",
      methode: "DELETE",
      confirmation: "Revenir à la valeur livrée avec l'application ?",
      succes: "Valeur par défaut rétablie",
      /* Un réglage déjà au défaut n'a rien à rétablir. */
      masquer: function (ligne) { return !ligne.modifie; }
    }],
    vide: {
      message: "Le serveur n'expose aucun réglage modifiable : rien à régler ici.",
      action: { libelle: "Voir la configuration", route: "#admin/parametres" }
    }
  };


  /* Comparaison de périodes : la question n'est pas « combien ? » mais
     « est-ce plus ou moins qu'avant ? ». Chaque ligne porte sa lecture, et une
     période précédente vide est dite — jamais traduite en « +∞ % ». */
  ECRANS["rapports/comparaison"] = {
    section: "Rapports & statistiques",
    titre: "Comparaison de périodes",
    desc: "Deux fenêtres de 30 jours sur les données réelles. Quand la période " +
          "précédente est vide, la ligne le dit au lieu d'afficher une variation " +
          "trompeuse.",
    source: { url: "/api/stats/comparaison?jours=30" },
    sourceCle: "indicateurs",
    id: "id",
    colonnes: [
      { cle: "indicateur", libelle: "Indicateur" },
      { cle: "courant", libelle: "30 derniers jours", format: "nombre" },
      { cle: "precedent", libelle: "30 jours précédents", format: "nombre" },
      { cle: "tendance", libelle: "Tendance" },
      { cle: "lecture", libelle: "Lecture" },
      { cle: "base", libelle: "Date utilisée" }
    ],
    filtres: [{ cle: "tendance", libelle: "Tendance" }],
    lectureSeule: true,
    vide: {
      message: "Aucune activité datée sur les deux périodes : il n'y a rien à " +
               "comparer pour l'instant.",
      action: { libelle: "Voir les statistiques", route: "#rapports/statistiques" }
    }
  };

  /* Le module Dossiers ouvre le même écran Clients que les référentiels
     (création, édition, suppression) au lieu d'une liste vide sans action. */
  if (ECRANS["referentiels/clients"] && !ECRANS["dossiers/clients"]) {
    ECRANS["dossiers/clients"] = ECRANS["referentiels/clients"];
  }

  /* ==================== 3. État et rendu ==================== */

  var etats = {};          // { route: { recherche, page, filtres, tri } }
  var cache = {};          // données par écran
  var moi = null;          // /api/rbac/moi

  function definition(route) { return ECRANS[route] || null; }

  function idDe(ligne, ecran) {
    if (!ligne) return "";
    if (ecran.id && ligne[ecran.id]) return String(ligne[ecran.id]);
    var alternatives = (ecran.idAlt || []).concat(["id"]);
    for (var i = 0; i < alternatives.length; i += 1) {
      if (ligne[alternatives[i]] !== undefined && ligne[alternatives[i]] !== null &&
          ligne[alternatives[i]] !== "") {
        return String(ligne[alternatives[i]]);
      }
    }
    return "";
  }

  function urlRemplie(modele, ligne, ecran) {
    if (typeof modele === "function") return modele(ligne);
    return String(modele).replace("{id}", encodeURIComponent(idDe(ligne, ecran)));
  }

  /* Droits d'écriture : contrat réel de `GET /api/rbac/moi`.
     - `actif: false`  → RBAC non activé (data/rbac.json absent) : accès historique ouvert ;
     - `administrateur`/rôle admin → écriture ;
     - sinon permission explicite `ecriture` ou joker.
     Le serveur re-vérifie systématiquement : l'UI ne fait que masquer. */
  function peutEcrire() {
    if (!moi) return false;
    if (moi.actif === false || moi.rbac_actif === false) return true;
    if (moi.administrateur === true) return true;
    var roles = moi.roles || (moi.role ? [moi.role] : []);
    if (roles.indexOf("administrateur") !== -1 || roles.indexOf("admin") !== -1) return true;
    var droits = moi.permissions || moi.droits || [];
    return droits.indexOf("ecriture") !== -1 || droits.indexOf("*") !== -1;
  }

  function hote() {
    var section = $("tab-ecran");
    if (!section) return null;
    var zone = section.querySelector("#ecranHost");
    if (zone) return zone;
    zone = elt("div");
    zone.id = "ecranHost";
    section.appendChild(zone);
    return zone;
  }

  function squelette(hoteRendu) {
    var bloc = elt("div", "ecran");
    var tete = elt("div", "ecran__head");
    tete.appendChild(elt("div", "ecran__skeleton ecran__skeleton--titre"));
    tete.appendChild(elt("div", "ecran__skeleton ecran__skeleton--ligne"));
    bloc.appendChild(tete);
    var table = elt("div", "ecran__card");
    for (var i = 0; i < 6; i += 1) {
      table.appendChild(elt("div", "ecran__skeleton ecran__skeleton--row"));
    }
    bloc.appendChild(table);
    hoteRendu.textContent = "";
    hoteRendu.appendChild(bloc);
  }

  function erreurRendu(hoteRendu, ecran, message, relancer) {
    var bloc = elt("div", "ecran");
    bloc.appendChild(enteteEcran(ecran, null));
    var carte = elt("div", "ecran__card ecran__card--etat");
    carte.appendChild(elt("div", "ecran__etat-icone", "!"));
    carte.appendChild(elt("h3", "ecran__etat-titre", "Liste indisponible"));
    carte.appendChild(elt("p", "ecran__etat-texte", message));
    var bouton = elt("button", "btn", "Réessayer");
    bouton.type = "button";
    bouton.addEventListener("click", relancer);
    carte.appendChild(bouton);
    bloc.appendChild(carte);
    hoteRendu.textContent = "";
    hoteRendu.appendChild(bloc);
  }

  function enteteEcran(ecran, nombreLignes) {
    var tete = elt("div", "ecran__head");

    var fil = elt("nav", "ecran__fil");
    fil.setAttribute("aria-label", "Fil d'Ariane");
    var racine = elt("a", "ecran__fil-lien", ecran.section);
    racine.href = "#" + ecran.sectionRoute;
    fil.appendChild(racine);
    fil.appendChild(elt("span", "ecran__fil-sep", "›"));
    fil.appendChild(elt("span", "ecran__fil-courant", ecran.titre));
    tete.appendChild(fil);

    var ligne = elt("div", "ecran__head-ligne");
    var titres = elt("div", "ecran__titres");
    titres.appendChild(elt("h1", "ecran__titre", ecran.titre));
    titres.appendChild(elt("p", "ecran__desc", ecran.desc));
    ligne.appendChild(titres);

    var actions = elt("div", "ecran__actions");
    if (ecran.creation && peutEcrire() && !ecran.lectureSeule) {
      var nouveau = elt("button", "btn btn--primaire", "Nouveau");
      nouveau.type = "button";
      nouveau.addEventListener("click", function () { ouvrirFormulaire(ecran, null); });
      actions.appendChild(nouveau);
    }
    if ((ecran.actions || []).some(function (a) { return a.global; }) && peutEcrire()) {
      (ecran.actions || []).filter(function (a) { return a.global; }).forEach(function (action) {
        var bouton = elt("button", "btn", action.libelle);
        bouton.type = "button";
        bouton.addEventListener("click", function () { executerAction(ecran, action, null); });
        actions.appendChild(bouton);
      });
    }
    var exporter = elt("button", "btn ghost", "Exporter CSV");
    exporter.type = "button";
    exporter.addEventListener("click", function () { exporterCsv(ecran); });
    actions.appendChild(exporter);
    ligne.appendChild(actions);
    tete.appendChild(ligne);

    if (nombreLignes !== null && nombreLignes !== undefined) {
      var resume = elt("p", "ecran__resume",
        nombreLignes + " enregistrement" + (nombreLignes > 1 ? "s" : "") +
        " — données du serveur, lecture directe.");
      tete.appendChild(resume);
    }
    return tete;
  }

  function appliquerFiltres(ecran, lignes, etat) {
    var resultat = lignes;
    if (typeof ecran.filtreLocal === "function") {
      resultat = resultat.filter(function (ligne) {
        return ecran.filtreLocal(ligne);
      });
    }
    Object.keys(etat.filtres || {}).forEach(function (cle) {
      var voulu = etat.filtres[cle];
      if (!voulu) return;
      resultat = resultat.filter(function (ligne) {
        var valeur = valeurDe(ligne, cle);
        return String(valeur === undefined || valeur === null ? "" : valeur) === voulu;
      });
    });
    var terme = (etat.recherche || "").trim().toLowerCase();
    if (terme) {
      resultat = resultat.filter(function (ligne) {
        return JSON.stringify(ligne).toLowerCase().indexOf(terme) !== -1;
      });
    }
    if (etat.tri && etat.tri.cle) {
      var cle = etat.tri.cle;
      var sens = etat.tri.sens === "desc" ? -1 : 1;
      resultat = resultat.slice().sort(function (a, b) {
        var va = a[cle];
        var vb = b[cle];
        if (typeof va === "number" && typeof vb === "number") return (va - vb) * sens;
        return String(va === undefined ? "" : va)
          .localeCompare(String(vb === undefined ? "" : vb), "fr") * sens;
      });
    }
    return resultat;
  }

  function valeursFiltre(lignes, cle) {
    var vues = [];
    lignes.forEach(function (ligne) {
      var valeur = valeurDe(ligne, cle);
      if (valeur === undefined || valeur === null || valeur === "") return;
      var texte = String(valeur);
      if (vues.indexOf(texte) === -1) vues.push(texte);
    });
    return vues.sort(function (a, b) { return a.localeCompare(b, "fr"); }).slice(0, 40);
  }

  var PAR_PAGE = 25;

  function rendreListe(ecran, route, lignes) {
    var zone = hote();
    if (!zone) return;
    var etat = etats[route];
    var filtrees = appliquerFiltres(ecran, lignes, etat);
    var total = filtrees.length;
    var pages = Math.max(1, Math.ceil(total / PAR_PAGE));
    if (etat.page > pages) etat.page = pages;
    var debut = (etat.page - 1) * PAR_PAGE;
    var visibles = filtrees.slice(debut, debut + PAR_PAGE);

    var bloc = elt("div", "ecran");
    ecran.sectionRoute = ecran.sectionRoute || route.split("/")[0];
    bloc.appendChild(enteteEcran(ecran, total));

    var carte = elt("div", "ecran__card");

    /* Barre d'outils : recherche + filtres */
    var barre = elt("div", "ecran__toolbar");
    var champ = elt("input", "ecran__recherche");
    champ.type = "search";
    champ.placeholder = "Rechercher dans cette liste…";
    champ.setAttribute("aria-label", "Rechercher dans cette liste");
    champ.value = etat.recherche;
    champ.addEventListener("input", function () {
      etat.recherche = champ.value;
      etat.page = 1;
      rendreListe(ecran, route, lignes);
    });
    barre.appendChild(champ);

    (ecran.filtres || []).forEach(function (filtre) {
      var valeurs = valeursFiltre(lignes, filtre.cle);
      if (!valeurs.length) return;
      var select = elt("select", "ecran__filtre");
      select.setAttribute("aria-label", filtre.libelle);
      var optionTous = elt("option", null, filtre.libelle + " : tous");
      optionTous.value = "";
      select.appendChild(optionTous);
      valeurs.forEach(function (valeur) {
        var option = elt("option", null, valeur);
        option.value = valeur;
        if (etat.filtres[filtre.cle] === valeur) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("change", function () {
        etat.filtres[filtre.cle] = select.value;
        etat.page = 1;
        rendreListe(ecran, route, lignes);
      });
      barre.appendChild(select);
    });

    if (Object.keys(etat.filtres || {}).some(function (cle) { return etat.filtres[cle]; }) ||
        etat.recherche) {
      var effacer = elt("button", "btn ghost sm", "Effacer les filtres");
      effacer.type = "button";
      effacer.addEventListener("click", function () {
        etat.recherche = "";
        etat.filtres = {};
        etat.page = 1;
        rendreListe(ecran, route, lignes);
      });
      barre.appendChild(effacer);
    }
    carte.appendChild(barre);

    if (!total) {
      var vide = elt("div", "ecran__card--etat ecran__etat");
      vide.appendChild(elt("div", "ecran__etat-icone", "∅"));
      var message = (ecran.vide && ecran.vide.message) || "Aucun enregistrement.";
      vide.appendChild(elt("h3", "ecran__etat-titre",
        lignes.length ? "Aucun résultat pour ces filtres" : "Rien à afficher"));
      vide.appendChild(elt("p", "ecran__etat-texte",
        lignes.length ? "Élargissez la recherche ou retirez un filtre." : message));
      var actionVide = ecran.vide && ecran.vide.action;
      if (actionVide) {
        var boutonVide = elt("button", "btn btn--primaire", actionVide.libelle);
        boutonVide.type = "button";
        boutonVide.addEventListener("click", function () {
          if (actionVide.route) window.location.hash = actionVide.route.replace(/^#/, "#");
          else ouvrirFormulaire(ecran, null);
        });
        if (peutEcrire() || actionVide.route) vide.appendChild(boutonVide);
      }
      carte.appendChild(vide);
      bloc.appendChild(carte);
      zone.textContent = "";
      zone.appendChild(bloc);
      return;
    }

    /* Tableau */
    var enveloppe = elt("div", "ecran__tableau");
    var table = elt("table", "table table--compact");
    var thead = elt("thead");
    var trh = elt("tr");
    ecran.colonnes.forEach(function (colonne) {
      var th = elt("th");
      var bouton = elt("button", "ecran__tri", colonne.libelle);
      bouton.type = "button";
      bouton.setAttribute("aria-label", "Trier par " + colonne.libelle);
      if (etat.tri && etat.tri.cle === colonne.cle) {
        bouton.textContent = colonne.libelle + (etat.tri.sens === "desc" ? " ▾" : " ▴");
      }
      bouton.addEventListener("click", function () {
        if (etat.tri && etat.tri.cle === colonne.cle) {
          etat.tri = { cle: colonne.cle, sens: etat.tri.sens === "asc" ? "desc" : "asc" };
        } else {
          etat.tri = { cle: colonne.cle, sens: "asc" };
        }
        rendreListe(ecran, route, lignes);
      });
      th.appendChild(bouton);
      trh.appendChild(th);
    });
    var actionsDispo = (ecran.actions || []).length + (ecran.edition ? 1 : 0) +
                       (ecran.suppression ? 1 : 0);
    if (actionsDispo) trh.appendChild(elt("th", "ecran__th-actions", ""));
    thead.appendChild(trh);
    table.appendChild(thead);

    var tbody = elt("tbody");
    visibles.forEach(function (ligne) {
      var tr = elt("tr");
      ecran.colonnes.forEach(function (colonne) {
        var td = elt("td");
        var texte = texteCellule(ligne, colonne);
        if (colonne.format === "lien-dossier" && ligne.id) {
          var lien = elt("a", null, texte);
          lien.href = "#dossiers/" + ligne.id;
          td.appendChild(lien);
        } else {
          td.textContent = texte;
        }
        tr.appendChild(td);
      });
      if (actionsDispo) {
        var tdActions = elt("td", "ecran__td-actions");
        (ecran.actions || []).forEach(function (action) {
          if (action.global) return;
          if (typeof action.masquer === "function" && action.masquer(ligne)) return;
          var bouton = elt("button", "btn ghost sm", action.libelle);
          bouton.type = "button";
          bouton.addEventListener("click", function () { executerAction(ecran, action, ligne); });
          tdActions.appendChild(bouton);
        });
        var editionPossible = ecran.edition && peutEcrire() &&
          !(typeof ecran.edition.masquer === "function" && ecran.edition.masquer(ligne));
        if (editionPossible) {
          var editer = elt("button", "btn ghost sm", "Modifier");
          editer.type = "button";
          editer.addEventListener("click", function () { ouvrirFormulaire(ecran, ligne); });
          tdActions.appendChild(editer);
        }
        var suppressionPossible = ecran.suppression && peutEcrire() && !ecran.lectureSeule &&
          !(typeof ecran.suppression.masquer === "function" && ecran.suppression.masquer(ligne));
        if (suppressionPossible) {
          var supprimer = elt("button", "btn ghost sm ecran__btn-danger", "Supprimer");
          supprimer.type = "button";
          supprimer.addEventListener("click", function () {
            if (!window.confirm("Supprimer définitivement cet enregistrement ?")) return;
            ecrire(urlRemplie(ecran.suppression.url, ligne, ecran), "DELETE")
              .then(function () {
                toast("Enregistrement supprimé", "success");
                charger(route, true);
              })
              .catch(function (erreur) { toast("Suppression impossible : " + erreur.message, "error"); });
          });
          tdActions.appendChild(supprimer);
        }
        tr.appendChild(tdActions);
      }
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    enveloppe.appendChild(table);
    carte.appendChild(enveloppe);

    /* Pagination */
    var pied = elt("div", "ecran__pagination");
    pied.appendChild(elt("span", "ecran__compteur",
      "1–" + Math.min(total, debut + PAR_PAGE) + " sur " + total));
    if (pages > 1) {
      var precedente = elt("button", "btn ghost sm", "‹ Précédent");
      precedente.type = "button";
      precedente.disabled = etat.page <= 1;
      precedente.addEventListener("click", function () {
        etat.page = Math.max(1, etat.page - 1);
        rendreListe(ecran, route, lignes);
      });
      var suivante = elt("button", "btn ghost sm", "Suivant ›");
      suivante.type = "button";
      suivante.disabled = etat.page >= pages;
      suivante.addEventListener("click", function () {
        etat.page = Math.min(pages, etat.page + 1);
        rendreListe(ecran, route, lignes);
      });
      pied.appendChild(precedente);
      pied.appendChild(elt("span", "ecran__page", "Page " + etat.page + " / " + pages));
      pied.appendChild(suivante);
    }
    carte.appendChild(pied);

    bloc.appendChild(carte);
    zone.textContent = "";
    zone.appendChild(bloc);
    window.__ecranCourant = { ecran: ecran, lignes: filtrees };
  }

  /* ==================== 4. Actions ==================== */

  /* Envoi d'une action au serveur et traitement de la réponse :
     - lecture (`afficher`) → panneau de résultat, sans rechargement ;
     - écriture → rechargement de la liste, puis verdict si demandé ;
     - téléchargement → fichier. */
  function envoyerAction(ecran, action, url, methode, corps) {
    if (action.telecharger) {
      fetch(url, { headers: entetes(), credentials: "same-origin" }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.blob();
      }).then(function (blob) {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = url.split("/").pop() || "export";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
        toast("Export téléchargé", "success");
      }).catch(function (erreur) { toast("Export impossible : " + erreur.message, "error"); });
      return;
    }

    ecrire(url, methode, corps).then(function (reponse) {
      toast(action.succes || "Action exécutée", "success");
      if (action.afficher && action.timeline) {
        var dire = action.enCours || "Lecture…";
        toast(dire, "info");
        lire(url).then(function (reponse) {
          setTimeout(function () { afficherChronologie(action.libelle, reponse); }, 350);
        }).catch(function (erreur) {
          toast(erreur.message || "Lecture impossible", "error");
        });
        return;
      }
      if (action.afficher) {
        /* Action de lecture (texte, résultat, détail) : on affiche la réponse
           et on ne recharge pas la liste, sinon le panneau serait effacé. */
        afficherResultat(action.libelle, reponse,
          action.resumer ? action.resumer(reponse) : "");
        return;
      }
      charger(ecran.__route, true);
      if (action.resultat) {
        /* Action d'écriture qui renvoie un verdict : on l'affiche après le
           rechargement de la liste, sinon le rendu le remplacerait. */
        setTimeout(function () {
          afficherResultat(action.libelle, reponse,
            action.resumer ? action.resumer(reponse) : "");
        }, 450);
      }
    }).catch(function (erreur) {
      toast((action.libelle || "Action") + " : " + erreur.message, "error");
    });
  }

  /* Action paramétrée : l'écran demande les valeurs attendues par l'API
     (par exemple le rapprochement financier, qui exige un dossier et une
     période) avant d'envoyer la requête. */
  function ouvrirDialogueAction(ecran, action, ligne) {
    var voile = elt("div", "ecran__voile");
    var boite = elt("div", "ecran__boite");
    boite.setAttribute("role", "dialog");
    boite.setAttribute("aria-modal", "true");
    boite.setAttribute("aria-label", action.libelle);

    var entete = elt("div", "ecran__boite-head");
    entete.appendChild(elt("h2", "ecran__boite-titre", action.libelle));
    var fermer = elt("button", "icon-btn", "✕");
    fermer.type = "button";
    fermer.setAttribute("aria-label", "Fermer");
    fermer.addEventListener("click", function () { voile.remove(); });
    entete.appendChild(fermer);
    boite.appendChild(entete);

    var form = elt("form", "ecran__form");
    var entrees = {};
    (action.champs || []).forEach(function (champ) {
      var bloc = elt("div", "ecran__champ");
      var label = elt("label", "ecran__label", champ.libelle + (champ.requis ? " *" : ""));
      label.setAttribute("for", "action-" + champ.cle);
      bloc.appendChild(label);

      var controle;
      if (champ.type === "select" || champ.type === "booleen") {
        controle = elt("select", "inp");
        var options = champ.type === "booleen"
          ? [{ valeur: "true", libelle: "Oui" }, { valeur: "false", libelle: "Non" }]
          : (champ.options || []).map(function (option) {
              return { valeur: option, libelle: option };
            });
        if (champ.type !== "booleen") {
          var vide = elt("option", null, "—");
          vide.value = "";
          controle.appendChild(vide);
        }
        options.forEach(function (option) {
          var o = elt("option", null, option.libelle);
          o.value = option.valeur;
          controle.appendChild(o);
        });
      } else {
        controle = elt("input", "inp");
        controle.type = champ.type === "date" ? "date"
          : (champ.type === "number" ? "number" : "text");
      }
      controle.id = "action-" + champ.cle;
      controle.name = champ.cle;
      if (champ.longueurMax) controle.maxLength = champ.longueurMax;
      var defaut = champ.defaut === "aujourdhui"
        ? new Date().toISOString().slice(0, 10)
        : (champ.valeur !== undefined ? champ.valeur : (ligne && ligne[champ.cle]));
      if (typeof defaut === "boolean") defaut = defaut ? "true" : "false";
      controle.value = defaut === null || defaut === undefined ? "" : String(defaut);
      if (champ.requis) controle.setAttribute("aria-required", "true");
      bloc.appendChild(controle);
      var aide = null;
      if (champ.aide) {
        aide = elt("p", "ecran__aide", champ.aide);
        bloc.appendChild(aide);
      }
      if (champ.referentiel) brancherSuggestions(controle, bloc, champ);
      else if (champ.registre) brancherRegistre(controle, bloc, champ);
      form.appendChild(bloc);
      entrees[champ.cle] = { controle: controle, definition: champ, bloc: bloc };
    });

    var erreurs = elt("p", "ecran__erreur");
    erreurs.setAttribute("role", "alert");
    form.appendChild(erreurs);

    var pied = elt("div", "ecran__boite-pied");
    var annuler = elt("button", "btn ghost", "Annuler");
    annuler.type = "button";
    annuler.addEventListener("click", function () { voile.remove(); });
    var valider = elt("button", "btn btn--primaire", action.libelle);
    valider.type = "submit";
    pied.appendChild(annuler);
    pied.appendChild(valider);
    form.appendChild(pied);

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      erreurs.textContent = "";
      var valeurs = {};
      var manquants = [];
      Object.keys(entrees).forEach(function (cle) {
        var entree = entrees[cle];
        var valeur = entree.controle.value.trim();
        if (entree.definition.requis && !valeur) {
          manquants.push(entree.definition.libelle);
          entree.bloc.classList.add("is-invalide");
          return;
        }
        entree.bloc.classList.remove("is-invalide");
        if (entree.definition.type === "number") valeur = Number(valeur);
        valeurs[cle] = valeur;
      });
      if (manquants.length) {
        erreurs.textContent = "Champs obligatoires : " + manquants.join(", ");
        return;
      }
      var url = urlRemplie(action.url, ligne || {}, ecran);
      var corps;
      if (action.emplacement === "query") {
        /* Beaucoup de routes d'écriture attendent des paramètres d'URL
           (FastAPI : scalaires = query string), pas un corps JSON.
           Envoyer un corps produisait un 422 systématique. */
        var paires = [];
        Object.keys(valeurs).forEach(function (cle) {
          var valeur = valeurs[cle];
          if (valeur === "" || valeur === undefined || valeur === null) return;
          paires.push(encodeURIComponent(cle) + "=" + encodeURIComponent(String(valeur)));
        });
        if (paires.length) {
          url += (url.indexOf("?") === -1 ? "?" : "&") + paires.join("&");
        }
        corps = undefined;
      } else {
        corps = action.corps ? action.corps(ligne || {}, valeurs) : valeurs;
      }
      voile.remove();
      envoyerAction(ecran, action, url, action.methode || "POST", corps);
    });

    boite.appendChild(form);
    voile.appendChild(boite);
    voile.addEventListener("click", function (ev) {
      if (ev.target === voile) voile.remove();
    });
    document.body.appendChild(voile);
    var premier = boite.querySelector("input, select");
    if (premier) premier.focus();
  }

  function executerAction(ecran, action, ligne) {
    if (action.confirmation && !window.confirm(action.confirmation)) return;
    if (typeof action.executer === "function") {
      action.executer(ligne || {});
      return;
    }
    if (action.route) {
      window.location.hash = action.route(ligne || {});
      return;
    }
    if (action.champs && action.champs.length) {
      ouvrirDialogueAction(ecran, action, ligne);
      return;
    }
    var url = urlRemplie(action.url, ligne || {}, ecran);
    var methode = action.methode || "POST";
    var corps = action.corps ? action.corps(ligne || {}) : undefined;
    envoyerAction(ecran, action, url, methode, corps);
  }

  /* Chronologie : un historique se lit dans l'ordre, pas en JSON. */
  function afficherChronologie(titre, donnees) {
    var zone = hote();
    if (!zone) return;
    var ancien = zone.querySelector(".ecran__resultat");
    if (ancien) ancien.remove();
    var bloc = elt("div", "ecran__resultat");
    bloc.appendChild(elt("h3", "ecran__resultat-titre",
      titre + (donnees && donnees.total !== undefined ? " — " + donnees.total +
        " événement" + (donnees.total > 1 ? "s" : "") : "")));
    var evenements = (donnees && donnees.evenements) || [];
    if (!evenements.length) {
      bloc.appendChild(elt("p", "chrono-vide",
        (donnees && donnees.vide) ||
        "Aucun événement journalisé pour ce document."));
    } else {
      var liste = elt("ol", "chrono-liste");
      evenements.forEach(function (e) {
        var item = elt("li", "chrono-item");
        item.appendChild(elt("span", "chrono-quand", e.horodatage || ""));
        item.appendChild(elt("span", "chrono-quoi", e.libelle || e.evenement || ""));
        if (e.detail) item.appendChild(elt("span", "chrono-detail", e.detail));
        if (e.acteur) item.appendChild(elt("span", "chrono-detail", "par " + e.acteur));
        liste.appendChild(item);
      });
      bloc.appendChild(liste);
    }
    var fermer = elt("button", "btn ghost sm", "Fermer");
    fermer.type = "button";
    fermer.addEventListener("click", function () { bloc.remove(); });
    bloc.appendChild(fermer);
    zone.insertBefore(bloc, zone.firstChild);
  }

  function afficherResultat(titre, donnees, resume) {
    var zone = hote();
    if (!zone) return;
    var ancien = zone.querySelector(".ecran__resultat");
    if (ancien) ancien.remove();
    var bloc = elt("div", "ecran__resultat");
    bloc.appendChild(elt("h3", "ecran__resultat-titre", titre));
    if (resume) {
      /* Une phrase claire vaut mieux qu'un JSON quand la réponse est simple. */
      bloc.appendChild(elt("p", "ecran__resultat-resume", resume));
    } else {
      var pre = elt("pre", "ecran__resultat-corps");
      pre.textContent = JSON.stringify(donnees, null, 2);
      bloc.appendChild(pre);
    }
    var fermer = elt("button", "btn ghost sm", "Fermer");
    fermer.type = "button";
    fermer.addEventListener("click", function () { bloc.remove(); });
    bloc.appendChild(fermer);
    zone.insertBefore(bloc, zone.firstChild);
  }

  function exporterCsv(ecran) {
    var courant = window.__ecranCourant;
    var lignes = courant && courant.lignes ? courant.lignes : [];
    if (!lignes.length) { toast("Rien à exporter pour le moment", "info"); return; }
    var colonnes = ecran.colonnes;
    var entete = colonnes.map(function (c) { return c.libelle; }).join(";");
    var corps = lignes.map(function (ligne) {
      return colonnes.map(function (c) {
        return '"' + texteCellule(ligne, c).replace(/"/g, '""') + '"';
      }).join(";");
    });
    var blob = new Blob(["\ufeff" + entete + "\n" + corps.join("\n")], {
      type: "text/csv;charset=utf-8"
    });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ecran.titre.toLowerCase().replace(/[^a-z0-9]+/g, "-") + ".csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
  }

  /* ==================== 5. Formulaire ==================== */

  /* Suggestions issues des référentiels.
     Une saisie libre reste possible — un référentiel vide ne doit pas bloquer
     la création d'un dossier — mais l'utilisateur voit immédiatement ce que
     l'exploitation a déjà référencé, et le dit quand la liste est vide. */
  var referentielsCache = {};

  /* Un « registre » est une liste d'objets existants (dossiers, déclarations)
     dont on choisit un élément : l'utilisateur tape un nom, le champ porte
     l'identifiant. Avant, il fallait coller « dos_bc3ee32380d9 » à la main. */
  var registresCache = {};

  function chargerRegistre(registre) {
    var url = registre.url;
    if (registresCache[url]) return registresCache[url];
    registresCache[url] = lire(url).then(function (corps) {
      var lignes = Array.isArray(corps) ? corps
        : ((corps && (corps.items || corps.entrees || corps.dossiers)) || []);
      return lignes.map(function (ligne) {
        var valeur = ligne[registre.valeur];
        var morceaux = (registre.apercu || [registre.valeur]).map(function (cle) {
          var v = ligne[cle];
          return v === null || v === undefined || v === "" ? "" : String(v);
        }).filter(function (v) { return v.length > 0; });
        return { valeur: valeur, texte: morceaux.join(" · ") };
      }).filter(function (o) { return o.valeur; });
    });
    return registresCache[url];
  }

  function brancherRegistre(controle, bloc, champ) {
    var registre = champ.registre;
    var liste = elt("datalist");
    var identifiant = "rg-" + champ.cle.replace(/\./g, "-") + "-" +
      Math.random().toString(36).slice(2, 7);
    liste.id = identifiant;
    controle.setAttribute("list", identifiant);
    controle.setAttribute("autocomplete", "off");
    bloc.appendChild(liste);
    var note = elt("p", "ecran__aide ecran__aide--ref", "Chargement des choix…");
    bloc.appendChild(note);

    chargerRegistre(registre).then(function (options) {
      controle.__valeurs = {};
      options.forEach(function (option) {
        var o = elt("option");
        o.value = option.valeur;
        if (option.texte && option.texte !== option.valeur) o.label = option.texte;
        liste.appendChild(o);
        controle.__valeurs[option.valeur] = option.texte || option.valeur;
      });
      delete registresCache[registre.url];
      if (!options.length) {
        note.textContent = (registre.vide ||
          "Aucun élément disponible pour l'instant.");
      } else {
        note.textContent = options.length + " " + (registre.nom || "élément") +
          (options.length > 1 ? "s" : "") + " proposé" +
          (options.length > 1 ? "s" : "") + " — choisissez dans les suggestions (nom ou référence).";
      }
    }).catch(function () {
      delete registresCache[registre.url];
      note.textContent = "Impossible de charger les choix. Fermez puis rouvrez le formulaire pour réessayer.";
    });
  }

  function suggestionsReferentiel(nom) {
    if (referentielsCache[nom]) return referentielsCache[nom];
    referentielsCache[nom] = lire("/api/referentiels/" + encodeURIComponent(nom))
      .then(function (corps) {
        var entrees = (corps && (corps.entrees || corps.items)) || [];
        return entrees.map(function (e) {
          return {
            valeur: e.code || e.libelle || "",
            libelle: e.libelle || e.code || ""
          };
        }).filter(function (o) { return o.valeur; });
      })
      .catch(function () { return []; });
    return referentielsCache[nom];
  }

  function brancherSuggestions(controle, bloc, champ) {
    var liste = elt("datalist");
    var identifiant = "dl-" + champ.cle.replace(/\./g, "-") + "-" +
      Math.random().toString(36).slice(2, 7);
    liste.id = identifiant;
    controle.setAttribute("list", identifiant);
    controle.setAttribute("autocomplete", "off");
    bloc.appendChild(liste);
    var note = elt("p", "ecran__aide ecran__aide--ref", "");
    bloc.appendChild(note);
    suggestionsReferentiel(champ.referentiel).then(function (options) {
      options.forEach(function (option) {
        var o = elt("option");
        o.value = option.valeur;
        if (option.libelle && option.libelle !== option.valeur) {
          o.label = option.libelle;
        }
        liste.appendChild(o);
      });
      if (!options.length) {
        note.textContent = "Référentiel « " + champ.referentiel + " » vide : " +
          "saisie libre. Ajoutez des entrées dans Référentiels pour les proposer ici.";
      } else {
        note.textContent = options.length + " entrée" +
          (options.length > 1 ? "s" : "") + " proposée" +
          (options.length > 1 ? "s" : "") + " depuis le référentiel « " +
          champ.referentiel + " ».";
      }
    });
  }

  function champValeur(ligne, cle) {
    if (!ligne) return "";
    if (cle.indexOf("attributs.") === 0) {
      var nom = cle.slice("attributs.".length);
      return ligne.attributs && ligne.attributs[nom] !== undefined ? ligne.attributs[nom] : "";
    }
    var valeur = ligne[cle];
    return valeur === undefined || valeur === null ? "" : valeur;
  }

  function ouvrirFormulaire(ecran, ligne) {
    var mode = ligne ? "edition" : "creation";
    var modele = ecran[mode];
    if (!modele) return;
    if (!peutEcrire()) { toast("Votre rôle ne permet pas cette écriture", "error"); return; }

    var voile = elt("div", "ecran__voile");
    var boite = elt("div", "ecran__boite");
    boite.setAttribute("role", "dialog");
    boite.setAttribute("aria-modal", "true");
    boite.setAttribute("aria-label", (mode === "creation" ? "Nouveau — " : "Modifier — ") + ecran.titre);

    var entete = elt("div", "ecran__boite-head");
    entete.appendChild(elt("h2", "ecran__boite-titre",
      (mode === "creation" ? "Nouveau — " : "Modifier — ") + ecran.titre));
    var fermer = elt("button", "icon-btn", "✕");
    fermer.type = "button";
    fermer.setAttribute("aria-label", "Fermer");
    fermer.addEventListener("click", function () { voile.remove(); });
    entete.appendChild(fermer);
    boite.appendChild(entete);

    var form = elt("form", "ecran__form");
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });

    var champs = modele.champs || [];
    var entrees = {};

    champs.forEach(function (champ) {
      var bloc = elt("div", "ecran__champ");
      var label = elt("label", "ecran__label", champ.libelle + (champ.requis ? " *" : ""));
      label.setAttribute("for", "champ-" + champ.cle.replace(/\./g, "-"));
      bloc.appendChild(label);

      var controle;
      if (champ.type === "textarea") {
        controle = elt("textarea", "inp");
        controle.rows = 3;
      } else if (champ.type === "select") {
        controle = elt("select", "inp");
        var vide = elt("option", null, "—");
        vide.value = "";
        controle.appendChild(vide);
        (champ.options || []).forEach(function (option) {
          var o = elt("option", null, option);
          o.value = option;
          controle.appendChild(o);
        });
      } else if (champ.type === "checkbox") {
        controle = elt("input", "ecran__case");
        controle.type = "checkbox";
      } else {
        controle = elt("input", "inp");
        controle.type = champ.type === "number" ? "number"
          : (champ.type === "date" ? "date"
            : (champ.type === "email" ? "email" : "text"));
        if (champ.type === "number") controle.step = "0.01";
      }
      controle.id = "champ-" + champ.cle.replace(/\./g, "-");
      controle.name = champ.cle;
      if (champ.longueurMax) controle.maxLength = champ.longueurMax;
      if (champ.requis) controle.setAttribute("aria-required", "true");

      var valeur = champValeur(ligne, champ.cle);
      if (Array.isArray(valeur)) valeur = valeur.join(", ");
      if (champ.type === "checkbox") controle.checked = Boolean(valeur);
      else controle.value = valeur === null || valeur === undefined ? "" : valeur;

      bloc.appendChild(controle);
      var aide = null;
      if (champ.aide) {
        aide = elt("p", "ecran__aide", champ.aide);
        bloc.appendChild(aide);
      }
      if (champ.referentiel) brancherSuggestions(controle, bloc, champ);
      else if (champ.registre) brancherRegistre(controle, bloc, champ);
      form.appendChild(bloc);
      entrees[champ.cle] = { controle: controle, definition: champ, bloc: bloc };
    });

    var erreurs = elt("p", "ecran__erreur");
    erreurs.setAttribute("role", "alert");
    form.appendChild(erreurs);

    var pied = elt("div", "ecran__boite-pied");
    var annuler = elt("button", "btn ghost", "Annuler");
    annuler.type = "button";
    annuler.addEventListener("click", function () { voile.remove(); });
    var valider = elt("button", "btn btn--primaire",
      mode === "creation" ? "Créer" : "Enregistrer");
    valider.type = "submit";
    pied.appendChild(annuler);
    pied.appendChild(valider);
    form.appendChild(pied);

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      erreurs.textContent = "";
      var corps = {};
      var manquants = [];
      Object.keys(entrees).forEach(function (cle) {
        var entree = entrees[cle];
        var controle = entree.controle;
        var valeur;
        if (entree.definition.type === "checkbox") valeur = controle.checked;
        else if (entree.definition.type === "number") {
          valeur = controle.value === "" ? 0 : Number(controle.value);
        } else valeur = controle.value.trim();

        if (entree.definition.requis && (valeur === "" || valeur === null)) {
          manquants.push(entree.definition.libelle);
          entree.bloc.classList.add("is-invalide");
          return;
        }
        if (entree.definition.registre && valeur &&
            (!controle.__valeurs || !Object.prototype.hasOwnProperty.call(controle.__valeurs, valeur))) {
          manquants.push(entree.definition.libelle + " (choisir dans la liste)");
          entree.bloc.classList.add("is-invalide");
          return;
        }
        entree.bloc.classList.remove("is-invalide");
        if (entree.definition.type === "liste") {
          /* Le serveur attend un tableau (rôles, permissions, dossiers) :
             on découpe la saisie sur les virgules en retirant les vides. */
          valeur = String(valeur).split(",").map(function (v) {
            return v.trim();
          }).filter(function (v) { return v.length > 0; });
          if (entree.definition.requis && !valeur.length) {
            manquants.push(entree.definition.libelle);
            entree.bloc.classList.add("is-invalide");
            return;
          }
        }

        if (cle.indexOf("attributs.") === 0) {
          corps.attributs = corps.attributs || {};
          corps.attributs[cle.slice("attributs.".length)] = valeur;
        } else {
          corps[cle] = valeur;
        }
      });
      if (manquants.length) {
        erreurs.textContent = "Champs obligatoires : " + manquants.join(", ");
        return;
      }

      var url = mode === "edition" ? urlRemplie(modele.url, ligne, ecran) : modele.url;
      var methode = mode === "edition" ? "PUT" : "POST";
      valider.disabled = true;
      ecrire(url, methode, corps).then(function (reponse) {
        toast(mode === "creation" ? "Enregistrement créé" : "Modifications enregistrées", "success");
        voile.remove();
        charger(ecran.__route, true);
        /* Certaines créations renvoient une valeur unique (jeton d'accès) :
           elle n'est plus relisible ensuite, il faut l'afficher tout de suite. */
        if (typeof modele.succes === "function") {
          setTimeout(function () { modele.succes(reponse); }, 500);
        }
      }).catch(function (erreur) {
        valider.disabled = false;
        erreurs.textContent = erreur.message;
      });
    });

    boite.appendChild(form);
    voile.appendChild(boite);
    voile.addEventListener("click", function (ev) {
      if (ev.target === voile) voile.remove();
    });
    document.body.appendChild(voile);
    var premier = boite.querySelector("input, select, textarea");
    if (premier) premier.focus();
  }

  /* ==================== 6. Chargement ==================== */

  function extraireLignes(ecran, donnees) {
    if (ecran.sourceCle && donnees && donnees[ecran.sourceCle]) return donnees[ecran.sourceCle];
    if (Array.isArray(donnees)) return donnees;
    if (donnees && Array.isArray(donnees.items)) return donnees.items;
    if (donnees && Array.isArray(donnees.entrees)) return donnees.entrees;
    if (donnees && Array.isArray(donnees.lignes)) return donnees.lignes;
    return [];
  }

  function charger(route, force) {
    var ecran = definition(route);
    if (!ecran) return;
    ecran.__route = route;
    var zone = hote();
    if (!zone) return;
    if (!etats[route]) etats[route] = { recherche: "", page: 1, filtres: {}, tri: null };
    if (!force && Array.isArray(cache[route])) { rendreListe(ecran, route, cache[route]); return; }

    etats[route].page = 1;
    squelette(zone);

    var promesse;
    if (ecran.source && typeof ecran.source.charger === "function") {
      promesse = ecran.source.charger(lire);
    } else if (ecran.source && ecran.source.url) {
      promesse = lire(ecran.source.url).then(function (donnees) {
        return extraireLignes(ecran, donnees);
      });
    } else {
      promesse = Promise.resolve([]);
    }

    promesse.then(function (lignes) {
      cache[route] = Array.isArray(lignes) ? lignes : [];
      rendreListe(ecran, route, cache[route]);
    }).catch(function (erreur) {
      ecran.sectionRoute = ecran.sectionRoute || route.split("/")[0];
      erreurRendu(zone, ecran, erreur.message || "Erreur réseau",
        function () { charger(route, true); });
    });
  }

  function routeCourante() {
    return (window.location.hash || "").replace(/^#/, "");
  }

  function rafraichir() {
    var route = routeCourante();
    if (!definition(route)) return;
    var section = $("tab-ecran");
    if (section) section.classList.remove("hidden");
    /* Rechargement systématique à l'entrée de l'écran : une création faite
       ailleurs (dossier, frais, référentiel) doit être visible sans recharger
       la page. Le cache ne sert qu'au rendu interne (tri, filtre, page). */
    charger(route, true);
  }

  function demarrer() {
    fetch("/api/rbac/moi", { headers: entetes(), credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (reponse) { moi = reponse; })
      .catch(function () { moi = null; })
      .then(function () {
        window.addEventListener("hashchange", function () { setTimeout(rafraichir, 20); });
        setTimeout(rafraichir, 400);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.UniOCREcrans = {
    ecrans: ECRANS,
    charger: charger,
    routes: function () { return Object.keys(ECRANS); }
  };
})();
